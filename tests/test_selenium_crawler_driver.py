"""Regression: UC Mode must keep Chrome's popup blocker disabled.

SeleniumBase 4.58.0 (released 2026-11-15) dropped --disable-popup-blocking
from UC Mode. crawl_page() calls uc_open_with_reconnect(), which opens the
URL with window.open() and then closes the previous tab. The second open is
popup-blocked, close() quits Chrome, and the rest of the crawl fails with
connection refused on /window/handles. Release run 43727249042 (and the
earlier schedule run 43718323451) therefore produced 1-page PDFs.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.selenium_crawler import SeleniumCrawler, _UC_CHROMIUM_ARGS


def test_uc_driver_disables_popup_blocking(monkeypatch):
    """Driver 생성 시 --disable-popup-blocking 이 UC Chromium args에 남는다."""
    captured = {}

    def fake_driver(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("src.selenium_crawler.Driver", fake_driver)

    SeleniumCrawler(Config(), MagicMock())

    assert captured["uc"] is True
    assert captured["headless"] is True
    assert captured["locale_code"] == "en"
    args = [part.strip() for part in captured["chromium_arg"].split(",")]
    assert "disable-popup-blocking" in args
    assert "disable-popup-blocking" in _UC_CHROMIUM_ARGS.split(",")
