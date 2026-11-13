"""Workflow helpers for the Release PDF job.

These cover the two failures that kept the scheduled release red:
the Ubuntu 26.04 gdk-pixbuf package rename, and same-day `gh release create`
aborting because the changelog fetch left today's tag in the local clone.
"""

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = ROOT / "scripts" / "install_weasyprint_deps.sh"
RELEASE_SCRIPT = ROOT / "scripts" / "recreate_release.sh"


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _apt_cache(bin_dir: Path, available: set[str]) -> None:
    names = " ".join(sorted(available))
    _write_executable(
        bin_dir / "apt-cache",
        f"""#!/usr/bin/env bash
available=" {names} "
for arg in "$@"; do
  case "$available" in
    *" $arg "*) exit 0 ;;
  esac
done
exit 100
""",
    )


def _print_gdk(tmp_path: Path, available: set[str]) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _apt_cache(bin_dir, available)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--print-gdk"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def test_gdk_pixbuf_prefers_ubuntu_26_name(tmp_path):
    """Ubuntu 24.04+ publishes libgdk-pixbuf-2.0-0; that is the package to install."""
    assert _print_gdk(tmp_path, {"libgdk-pixbuf-2.0-0", "libgdk-pixbuf2.0-0"}) == (
        "libgdk-pixbuf-2.0-0"
    )


def test_gdk_pixbuf_falls_back_when_only_old_name_exists(tmp_path):
    """Older images only have the transitional package name."""
    assert _print_gdk(tmp_path, {"libgdk-pixbuf2.0-0"}) == "libgdk-pixbuf2.0-0"


def test_gdk_pixbuf_falls_back_when_neither_name_is_indexed(tmp_path):
    """An empty apt cache still names a concrete package for the install error."""
    assert _print_gdk(tmp_path, set()) == "libgdk-pixbuf2.0-0"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README").write_text("hi\n")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "init")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "HEAD")
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    return repo, sha


def _fake_gh(bin_dir: Path, log_path: Path) -> None:
    _write_executable(
        bin_dir / "gh",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{log_path}"
if [ "$1" = "release" ] && [ "$2" = "delete" ]; then
  # A missing same-day release is not fatal; the script must keep going.
  exit 1
fi
if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )


def _run_release(repo: Path, bin_dir: Path, sha: str, tag: str) -> str:
    notes = repo / "notes.md"
    notes.write_text("release notes\n")
    asset = repo / "cursor_docs_en.pdf"
    asset.write_bytes(b"%PDF-1.4\n")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_SHA"] = sha
    subprocess.run(
        [
            "bash",
            str(RELEASE_SCRIPT),
            tag,
            "Cursor Docs PDF - 2026-09-27",
            str(notes),
            str(asset),
        ],
        cwd=repo,
        check=True,
        env=env,
    )
    return (repo / "gh.log").read_text()


def test_same_day_rerun_drops_local_tag_and_pins_target(tmp_path):
    """Pin --target to the afternoon commit, not the morning tag's commit."""
    repo, first_sha = _init_repo(tmp_path)
    tag = "docs-2026-09-27"
    _git(repo, "tag", tag)
    _git(repo, "push", "origin", tag)
    (repo / "README").write_text("afternoon\n")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "afternoon crawl")
    _git(repo, "push", "origin", "HEAD")
    second_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    assert first_sha != second_sha
    assert _git(repo, "rev-parse", tag).stdout.strip() == first_sha

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = repo / "gh.log"
    _fake_gh(bin_dir, log_path)

    log = _run_release(repo, bin_dir, second_sha, tag)

    assert _git(repo, "tag", "-l", tag).stdout.strip() == ""
    remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert remote.stdout.strip() == ""
    delete_line, create_line = log.strip().splitlines()
    assert delete_line == f"release delete {tag} --yes --cleanup-tag"
    assert f"release create {tag} --target {second_sha} " in create_line
    assert first_sha not in create_line
    assert "--notes-file" in create_line
    assert "cursor_docs_en.pdf" in create_line


def test_first_release_of_the_day_still_targets_github_sha(tmp_path):
    """A day with no existing tag still publishes against the checked-out commit."""
    repo, sha = _init_repo(tmp_path)
    tag = "docs-2026-11-01"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_gh(bin_dir, repo / "gh.log")

    log = _run_release(repo, bin_dir, sha, tag)

    assert f"--target {sha}" in log
    assert _git(repo, "tag", "-l", tag).stdout.strip() == ""


def test_recreate_release_requires_github_sha(tmp_path):
    repo, _sha = _init_repo(tmp_path)
    notes = repo / "notes.md"
    notes.write_text("notes\n")
    env = os.environ.copy()
    env.pop("GITHUB_SHA", None)
    result = subprocess.run(
        ["bash", str(RELEASE_SCRIPT), "docs-2026-09-27", "title", str(notes)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 2
    assert "GITHUB_SHA is required" in result.stderr


PREV_TAG_SCRIPT = ROOT / "scripts" / "previous_release_tag.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "release-pdf.yml"


def _gh_release_list(bin_dir: Path, tags: list[str], fail: bool = False) -> None:
    body = "\n".join(tags)
    status = "1" if fail else "0"
    _write_executable(
        bin_dir / "gh",
        f"""#!/usr/bin/env bash
if [ "$1" = "release" ] && [ "$2" = "list" ]; then
  printf '%s\\n' "{body}"
  exit {status}
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )


def _previous_tag(
    tmp_path: Path, today: str, tags: list[str], fail: bool = False
) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _gh_release_list(bin_dir, tags, fail=fail)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        ["bash", str(PREV_TAG_SCRIPT), today],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def test_previous_release_tag_skips_today(tmp_path):
    """A same-day rerun compares against the prior release, not itself."""
    tags = [f"docs-2026-09-{day:02d}" for day in range(27, 16, -1)]
    chosen = _previous_tag(tmp_path, "docs-2026-09-27", tags)
    assert chosen == "docs-2026-09-26"


def test_previous_release_tag_is_empty_when_only_today_exists(tmp_path):
    assert _previous_tag(tmp_path, "docs-2026-09-27", ["docs-2026-09-27"]) == ""


def test_previous_release_tag_uses_newest_when_today_is_absent(tmp_path):
    chosen = _previous_tag(
        tmp_path,
        "docs-2026-09-27",
        ["docs-2026-09-26", "docs-2026-09-25"],
    )
    assert chosen == "docs-2026-09-26"


def test_previous_release_tag_is_empty_when_gh_fails(tmp_path):
    assert _previous_tag(tmp_path, "docs-2026-09-27", [], fail=True) == ""


def test_zero_change_count_is_a_single_zero():
    """`grep -c` already prints 0; `|| echo 0` used to append a second 0."""
    broken = r"""
set -eo pipefail
ADDED=""
ADDED_COUNT=$(echo "$ADDED" | grep -c . || echo "0")
printf '%s' "$ADDED_COUNT"
"""
    fixed = r"""
set -eo pipefail
ADDED=""
REMOVED="https://cursor.com/docs/agent/overview"
ADDED_COUNT=$(echo "$ADDED" | grep -c . || true)
REMOVED_COUNT=$(echo "$REMOVED" | grep -c . || true)
printf 'added=%s\nremoved=%s\n' "$ADDED_COUNT" "$REMOVED_COUNT"
"""
    broken_out = subprocess.run(
        ["bash", "-c", broken], check=True, capture_output=True, text=True
    )
    fixed_out = subprocess.run(
        ["bash", "-c", fixed], check=True, capture_output=True, text=True
    )
    assert broken_out.stdout == "0\n0"
    assert fixed_out.stdout == "added=0\nremoved=1\n"
    workflow = WORKFLOW.read_text()
    assert 'grep -c . || echo "0"' not in workflow
    assert "grep -c . || true" in workflow
    assert "group: release-pdf" in workflow
    assert "cancel-in-progress: false" in workflow


def _run_release_with_gh(repo, bin_dir, sha, tag, gh_body):
    _write_executable(bin_dir / "gh", gh_body)
    notes = repo / "notes.md"
    notes.write_text("release notes\n")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GITHUB_SHA"] = sha
    env["RELEASE_CREATE_RETRY_DELAY"] = "0"
    return subprocess.run(
        [
            "bash",
            str(RELEASE_SCRIPT),
            tag,
            "Cursor Docs PDF - 2026-09-27",
            str(notes),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_release_create_retries_422_then_succeeds(tmp_path):
    repo, sha = _init_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = repo / "gh.log"
    state = tmp_path / "creates"
    tag = "docs-2026-09-27"
    result = _run_release_with_gh(
        repo,
        bin_dir,
        sha,
        tag,
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{log_path}"
if [ "$1" = "release" ] && [ "$2" = "delete" ]; then
  exit 1
fi
if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  count=0
  if [ -f "{state}" ]; then count=$(cat "{state}"); fi
  count=$((count + 1))
  printf '%s' "$count" > "{state}"
  if [ "$count" -eq 1 ]; then
    echo "HTTP 422: Validation Failed" >&2
    exit 1
  fi
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )
    assert result.returncode == 0, result.stderr
    creates = [
        line
        for line in log_path.read_text().splitlines()
        if line.startswith("release create")
    ]
    assert len(creates) == 2
    assert all(f"--target {sha} " in line for line in creates)


def test_release_create_does_not_retry_other_errors(tmp_path):
    repo, sha = _init_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = repo / "gh.log"
    result = _run_release_with_gh(
        repo,
        bin_dir,
        sha,
        "docs-2026-09-27",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{log_path}"
if [ "$1" = "release" ] && [ "$2" = "delete" ]; then
  exit 1
fi
if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  echo "authentication required" >&2
  exit 1
fi
exit 1
""",
    )
    assert result.returncode != 0
    creates = [
        line
        for line in log_path.read_text().splitlines()
        if line.startswith("release create")
    ]
    assert creates == [line for line in creates if f"--target {sha} " in line]
    assert len(creates) == 1
