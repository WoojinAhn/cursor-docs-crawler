"""Tests for SeleniumCrawler._inline_images_as_base64.

This is the defense layer that bypasses Vercel's image-fetch blocking by
running fetch() inside the browser's authenticated session and rewriting
<img src> attributes to base64 data URIs before page_source is captured.

We do not start a real browser; we instantiate the crawler with __new__ and
inject a stub driver.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.selenium_crawler import SeleniumCrawler


def _make_crawler():
    """Build a SeleniumCrawler without invoking __init__ (which spawns Chrome)."""
    crawler = SeleniumCrawler.__new__(SeleniumCrawler)
    crawler.driver = MagicMock()
    crawler.logger = logging.getLogger("test.inline_images")
    return crawler


def test_inline_images_success_logs_count(caplog):
    """fetch가 N개 이미지를 변환했을 때 로그에 그 수가 남는다."""
    crawler = _make_crawler()
    # The injected JS resolves with the count of converted images
    crawler.driver.execute_async_script.return_value = 3

    with caplog.at_level(logging.DEBUG, logger="test.inline_images"):
        crawler._inline_images_as_base64()

    crawler.driver.execute_async_script.assert_called_once()
    script_arg = crawler.driver.execute_async_script.call_args[0][0]
    # Sanity-check the script targets non-data <img> elements
    assert 'img[src]:not([src^="data:"])' in script_arg
    assert "fetch(img.src)" in script_arg
    # Debug log records the inlined count
    assert any("Inlined 3 images" in r.message for r in caplog.records)


def test_inline_images_no_images_does_not_log_count(caplog):
    """이미지가 없는 페이지에서는 변환 카운트 로그가 발생하지 않는다."""
    crawler = _make_crawler()
    # Script callback returns 0 when document has no <img> elements
    crawler.driver.execute_async_script.return_value = 0

    with caplog.at_level(logging.DEBUG, logger="test.inline_images"):
        crawler._inline_images_as_base64()

    crawler.driver.execute_async_script.assert_called_once()
    # No "Inlined N images" message when count is falsy
    assert not any("Inlined" in r.message for r in caplog.records)


def test_inline_images_swallows_driver_exception(caplog):
    """driver 호출이 예외를 던져도 크롤이 중단되지 않고 warning만 남긴다."""
    crawler = _make_crawler()
    crawler.driver.execute_async_script.side_effect = RuntimeError(
        "JavascriptException: fetch failed"
    )

    with caplog.at_level(logging.WARNING, logger="test.inline_images"):
        # Must not raise — the bot-defense layer is best-effort
        crawler._inline_images_as_base64()

    assert any(
        "Image inlining failed" in r.message for r in caplog.records
    )


def test_inline_images_handles_none_result(caplog):
    """driver 결과가 None(예: 비동기 콜백 미호출 후 timeout 처리)이어도 안전하다."""
    crawler = _make_crawler()
    crawler.driver.execute_async_script.return_value = None

    with caplog.at_level(logging.DEBUG, logger="test.inline_images"):
        crawler._inline_images_as_base64()

    # No crash, no "Inlined" log because result is falsy
    assert not any("Inlined" in r.message for r in caplog.records)
