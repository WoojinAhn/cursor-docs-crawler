"""Offline E2E test using saved HTML fixtures.

Runs the full pipeline (parse → PDF) without Selenium or network access.
Requires fixtures to exist — run `python scripts/save_fixtures.py` first.
"""

import os
import tempfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

pytestmark = pytest.mark.skipif(
    not MANIFEST_PATH.exists(),
    reason="HTML fixtures not found. Run: python scripts/save_fixtures.py",
)


def test_fixture_loading():
    """FixtureCrawler loads all fixture pages as valid PageData."""
    from src.fixture_crawler import FixtureCrawler

    crawler = FixtureCrawler(str(FIXTURE_DIR))
    pages = crawler.crawl_all()

    assert len(pages) > 0, "No pages loaded from fixtures"
    for page in pages:
        assert page.is_valid(), f"Invalid page: {page.url}"
        assert len(page.html_content) > 0


def test_e2e_parse():
    """ContentParser produces valid PageContent from every fixture."""
    from src.config import Config
    from src.content_parser import ContentParser
    from src.fixture_crawler import FixtureCrawler

    crawler = FixtureCrawler(str(FIXTURE_DIR))
    pages = crawler.crawl_all()
    parser = ContentParser(Config())

    processed = []
    for page in pages:
        content = parser.parse_page(page)
        processed.append(content)

    assert len(processed) == len(pages)
    for content in processed:
        assert content.is_valid(), f"Invalid content: {content.url}"
        assert content.word_count > 0, f"Empty content: {content.url}"


def test_e2e_pdf_generation():
    """Full pipeline: fixtures → parse → PDF file."""
    from src.config import Config
    from src.content_parser import ContentParser
    from src.fixture_crawler import FixtureCrawler
    from src.pdf_generator import PDFGenerator

    crawler = FixtureCrawler(str(FIXTURE_DIR))
    pages = crawler.crawl_all()

    config = Config()
    parser = ContentParser(config)
    processed = [parser.parse_page(p) for p in pages]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test_output.pdf")
        config.OUTPUT_FILE = output_path
        generator = PDFGenerator(config)
        success = generator.generate_pdf(processed, output_path)

        assert success, "PDF generation failed"
        assert os.path.exists(output_path), "PDF file not created"
        assert os.path.getsize(output_path) > 0, "PDF file is empty"
