"""Tests for main.py: seed_from_llms_txt and redirect filter logic."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import seed_from_llms_txt
from src.url_manager import URLManager
from src.models import PageData


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
        seeded = seed_from_llms_txt(mgr, "https://cursor.com/llms.txt")

    # docs (initial seed) + quickstart + models = 3 total, but 2 new
    assert seeded == 2


def test_seed_from_llms_txt_strips_md_suffix():
    """.md 접미사를 제거하여 실제 페이지 URL로 변환한다."""
    mgr = _make_url_manager()
    llms_txt = "- [Page](https://cursor.com/docs/plugins.md)\n"
    mock_resp = MagicMock()
    mock_resp.read.return_value = llms_txt.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("main.urlopen", return_value=mock_resp):
        seed_from_llms_txt(mgr, "https://cursor.com/llms.txt")

    # Should have added https://cursor.com/docs/plugins (without .md)
    assert "https://cursor.com/docs/plugins" in mgr._queued_urls


def test_seed_from_llms_txt_network_error():
    """네트워크 오류 시 0을 반환하고 크래시하지 않는다."""
    mgr = _make_url_manager()

    with patch("main.urlopen", side_effect=URLError("Connection refused")):
        seeded = seed_from_llms_txt(mgr, "https://cursor.com/llms.txt")

    assert seeded == 0


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
