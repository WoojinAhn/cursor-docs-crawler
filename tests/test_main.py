"""Tests for main.py: seed_from_llms_txt and redirect filter logic."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import seed_from_llms_txt
from src.config import Config
from src.url_manager import URLManager
from src.models import PageData

_DOCS_SEED_REGEX = Config._SCOPE_MAP["docs"]["seed_regex"]


def _mock_urlopen_response(body: str):
    """Build a context-manager mock for urlopen returning *body*."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = body.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# --- seed_from_llms_txt ---

def _make_url_manager():
    return URLManager("https://cursor.com/docs", allowed_path_prefixes=["/docs/"])


def test_seed_from_llms_txt_success():
    """llms.txt에서 URL을 파싱하여 시딩한다."""
    mgr = _make_url_manager()
    llms_txt = (
        "# Cursor Docs\n"
        "- [Quickstart](https://cursor.com/docs/get-started/quickstart.md)\n"
        "- [Models](https://cursor.com/docs/models.md)\n"
    )
    mock_resp = MagicMock()
    mock_resp.read.return_value = llms_txt.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("main.urlopen", return_value=mock_resp):
        seeded = seed_from_llms_txt(mgr, "https://cursor.com/llms.txt", _DOCS_SEED_REGEX)

    # Returns the set of canonical URLs from llms.txt
    assert isinstance(seeded, set)
    assert len(seeded) == 2
    assert "https://cursor.com/docs/get-started/quickstart" in seeded
    assert "https://cursor.com/docs/models" in seeded


def test_seed_from_llms_txt_strips_md_suffix():
    """.md 접미사를 제거하여 실제 페이지 URL로 변환한다."""
    mgr = _make_url_manager()
    llms_txt = "# Docs\n- [Page](https://cursor.com/docs/plugins.md)\n"
    mock_resp = MagicMock()
    mock_resp.read.return_value = llms_txt.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("main.urlopen", return_value=mock_resp):
        seed_from_llms_txt(mgr, "https://cursor.com/llms.txt", _DOCS_SEED_REGEX)

    # Should have added https://cursor.com/docs/plugins (without .md)
    assert "https://cursor.com/docs/plugins" in mgr._queued_urls


def test_seed_from_llms_txt_network_error():
    """네트워크 오류 시 0을 반환하고 크래시하지 않는다."""
    mgr = _make_url_manager()

    with patch("main.urlopen", side_effect=URLError("Connection refused")):
        seeded = seed_from_llms_txt(mgr, "https://cursor.com/llms.txt", _DOCS_SEED_REGEX)

    assert seeded == set()


def test_seed_from_llms_txt_uses_fallback_on_network_error(tmp_path):
    """네트워크 실패 + fallback 파일 존재 시 캐시에서 시딩한다."""
    mgr = _make_url_manager()
    fallback = tmp_path / "llms-txt-snapshot.txt"
    fallback.write_text(
        "# Cursor Docs\n"
        "- [Quickstart](https://cursor.com/docs/quickstart.md)\n"
        "- [Models](https://cursor.com/docs/models.md)\n",
        encoding="utf-8",
    )

    with patch("main.urlopen", side_effect=URLError("dns failure")):
        seeded = seed_from_llms_txt(
            mgr,
            "https://cursor.com/llms.txt",
            _DOCS_SEED_REGEX,
            fallback_path=str(fallback),
        )

    assert "https://cursor.com/docs/quickstart" in seeded
    assert "https://cursor.com/docs/models" in seeded
    # URLs are added to the manager queue
    assert "https://cursor.com/docs/quickstart" in mgr._queued_urls


def test_seed_from_llms_txt_no_fallback_returns_empty(tmp_path):
    """네트워크 실패 + fallback 파일 부재 시 빈 셋을 반환한다."""
    mgr = _make_url_manager()
    missing = tmp_path / "does-not-exist.txt"

    with patch("main.urlopen", side_effect=URLError("offline")):
        seeded = seed_from_llms_txt(
            mgr,
            "https://cursor.com/llms.txt",
            _DOCS_SEED_REGEX,
            fallback_path=str(missing),
        )

    assert seeded == set()


def test_seed_from_llms_txt_rejects_html_response_uses_fallback(tmp_path):
    """봇 차단 HTML 응답은 거부하고 fallback을 사용한다."""
    mgr = _make_url_manager()
    fallback = tmp_path / "llms-txt-snapshot.txt"
    fallback.write_text(
        "# Cursor Docs\n- [Page](https://cursor.com/docs/cached.md)\n",
        encoding="utf-8",
    )

    html_body = (
        "<html><head><title>Just a moment...</title></head>"
        "<body>Verifying you are human</body></html>"
    )
    mock_resp = _mock_urlopen_response(html_body)

    with patch("main.urlopen", return_value=mock_resp):
        seeded = seed_from_llms_txt(
            mgr,
            "https://cursor.com/llms.txt",
            _DOCS_SEED_REGEX,
            fallback_path=str(fallback),
        )

    # HTML body must not be parsed as llms.txt
    assert seeded == {"https://cursor.com/docs/cached"}


def test_seed_from_llms_txt_rejects_html_response_no_fallback():
    """봇 차단 HTML 응답 + fallback 없음 → 빈 셋."""
    mgr = _make_url_manager()
    html_body = "<!DOCTYPE html><html><body>blocked</body></html>"
    mock_resp = _mock_urlopen_response(html_body)

    with patch("main.urlopen", return_value=mock_resp):
        seeded = seed_from_llms_txt(
            mgr, "https://cursor.com/llms.txt", _DOCS_SEED_REGEX
        )

    assert seeded == set()


def test_seed_from_llms_txt_accepts_markdown_with_leading_whitespace():
    """선행 공백/개행이 있어도 '#'으로 시작하면 유효한 llms.txt로 인정한다."""
    mgr = _make_url_manager()
    body = "\n  \n# Cursor Docs\n- [Page](https://cursor.com/docs/api.md)\n"
    mock_resp = _mock_urlopen_response(body)

    with patch("main.urlopen", return_value=mock_resp):
        seeded = seed_from_llms_txt(
            mgr, "https://cursor.com/llms.txt", _DOCS_SEED_REGEX
        )

    assert "https://cursor.com/docs/api" in seeded


# --- redirect filter logic ---

def _make_page(url, final_url=None):
    return PageData(
        url=url,
        title="Test",
        html_content="<html><body>content</body></html>",
        status_code=200,
        final_url=final_url,
    )


def _apply_redirect_filter(pages):
    """Reproduce the redirect filter logic from main.py."""
    crawled_urls = {p.url for p in pages}
    return [
        p for p in pages
        if not p.final_url
        or p.final_url == p.url
        or p.final_url not in crawled_urls
    ]


def test_redirect_filter_keeps_no_final_url():
    """final_url이 없는 페이지는 유지한다."""
    pages = [_make_page("https://cursor.com/docs/a", final_url=None)]
    result = _apply_redirect_filter(pages)
    assert len(result) == 1


def test_redirect_filter_keeps_same_url():
    """final_url == url인 페이지(리다이렉트 없음)는 유지한다."""
    url = "https://cursor.com/docs/overview"
    pages = [_make_page(url, final_url=url)]
    result = _apply_redirect_filter(pages)
    assert len(result) == 1


def test_redirect_filter_removes_redirect_with_target_crawled():
    """리다이렉트 대상이 독립적으로 크롤된 경우, 리다이렉트 소스를 제거한다."""
    target = "https://cursor.com/docs/overview"
    redirect_source = "https://cursor.com/docs/agent/chat/tabs"
    pages = [
        _make_page(target, final_url=target),
        _make_page(redirect_source, final_url=target),
    ]
    result = _apply_redirect_filter(pages)
    assert len(result) == 1
    assert result[0].url == target


def test_redirect_filter_keeps_redirect_without_target():
    """리다이렉트 대상이 별도로 크롤되지 않은 경우, 페이지를 유지한다."""
    pages = [
        _make_page(
            "https://cursor.com/docs/old-page",
            final_url="https://cursor.com/docs/new-page",
        )
    ]
    result = _apply_redirect_filter(pages)
    assert len(result) == 1
