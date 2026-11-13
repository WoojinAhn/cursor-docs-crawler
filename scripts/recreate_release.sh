#!/usr/bin/env bash
# Publish TAG, replacing a release created earlier the same day.
#
# Deleting the remote tag can leave it in the local clone (the changelog
# step used to fetch it). `gh release create` then aborts with:
#   tag <name> exists locally but has not been pushed ... specify `--target`
# Drop the local tag and pin --target to the commit this run checked out.
# Tag deletion is not always visible to the Releases API immediately, so a
# 422 on create is retried.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: recreate_release.sh TAG TITLE NOTES_FILE [assets...]" >&2
  exit 2
fi

TAG="$1"
TITLE="$2"
NOTES_FILE="$3"
shift 3

if [ -z "${GITHUB_SHA:-}" ]; then
  echo "GITHUB_SHA is required" >&2
  exit 2
fi

release_create_with_retry() {
  local attempt delay log_file
  delay="${RELEASE_CREATE_RETRY_DELAY:-2}"
  for attempt in 1 2 3 4 5; do
    log_file="$(mktemp)"
    if gh release create "$TAG" \
      --target "$GITHUB_SHA" \
      --title "$TITLE" \
      --notes-file "$NOTES_FILE" \
      "$@" >"$log_file" 2>&1; then
      cat "$log_file"
      rm -f "$log_file"
      return 0
    fi
    cat "$log_file" >&2
    if ! grep -q "422" "$log_file"; then
      rm -f "$log_file"
      return 1
    fi
    rm -f "$log_file"
    if [ "$attempt" -eq 5 ]; then
      echo "gh release create still returned 422 after ${attempt} attempts" >&2
      return 1
    fi
    echo "gh release create returned 422 (attempt ${attempt}/5); retrying" >&2
    sleep "$delay"
  done
}

# Keep delete errors visible. A missing release is not fatal: the tag may
# already have been removed, and create below publishes a new one.
gh release delete "$TAG" --yes --cleanup-tag || true
GIT_TERMINAL_PROMPT=0 git push --delete origin "$TAG" 2>/dev/null || true
git tag -d "$TAG" 2>/dev/null || true

release_create_with_retry "$@"
