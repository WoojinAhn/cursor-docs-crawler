"""Fixture-based crawler that loads saved HTML instead of using Selenium.

Provides the same interface as SeleniumCrawler (crawl_all / close) so it
can be used as a drop-in replacement for offline testing.
"""

import json
import logging
from pathlib import Path
from typing import List

from .models import PageData

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


class FixtureCrawler:
    """Load pre-saved HTML fixtures as PageData objects."""

    def __init__(self, fixture_dir: str = None):
        self.fixture_dir = Path(fixture_dir) if fixture_dir else DEFAULT_FIXTURE_DIR
        self.logger = logging.getLogger(__name__)

    def crawl_all(self) -> List[PageData]:
        """Load all fixtures from manifest and return as PageData list."""
        manifest_path = self.fixture_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Fixture manifest not found: {manifest_path}\n"
                "Run 'python scripts/save_fixtures.py' to create fixtures."
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        html_dir = self.fixture_dir / "html"
        pages = []

        for entry in manifest:
            html_path = html_dir / entry["filename"]
            if not html_path.exists():
                self.logger.warning(f"Fixture HTML missing: {html_path}")
                continue

            html_content = html_path.read_text(encoding="utf-8")
            page = PageData(
                url=entry["url"],
                title=entry["title"],
                html_content=html_content,
                status_code=200,
                links=entry.get("links", []),
                final_url=entry.get("final_url"),
            )
            pages.append(page)
            self.logger.info(f"[Fixture] Loaded: {entry['url']}")

        print(f"[Fixture] Loaded {len(pages)} pages from {self.fixture_dir}")
        return pages

    def close(self):
        """No-op (no browser to close)."""
        pass
