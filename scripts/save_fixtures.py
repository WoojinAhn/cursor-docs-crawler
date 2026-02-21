#!/usr/bin/env python3
"""Save HTML fixtures from live crawl for offline E2E testing.

Crawls TestConfig.TEST_URLS via Selenium and saves the raw HTML + metadata
to tests/fixtures/ so that offline tests can run without network access.

Usage:
    python scripts/save_fixtures.py
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.config import TestConfig
from src.url_manager import URLManager
from src.selenium_crawler import SeleniumCrawler

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"
HTML_DIR = FIXTURE_DIR / "html"


def url_to_filename(url: str) -> str:
    """Convert URL to a safe filename.

    https://cursor.com/docs/get-started/concepts -> docs__get-started__concepts.html
    """
    path = re.sub(r"^https?://[^/]+/", "", url).strip("/")
    safe = path.replace("/", "__")
    return f"{safe}.html"


def main():
    config = TestConfig()
    print(f"Saving fixtures for {len(config.TEST_URLS)} URLs...")

    # Setup Selenium crawler
    url_manager = URLManager(config.BASE_URL, config.MAX_PAGES,
                             config.ALLOWED_PATH_PREFIXES)
    crawler = SeleniumCrawler(config, url_manager)

    manifest = []
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    try:
        for i, url in enumerate(config.TEST_URLS, 1):
            print(f"[{i}/{len(config.TEST_URLS)}] Crawling: {url}")
            page_data = crawler.crawl_page(url)

            if not page_data or not page_data.is_valid():
                print(f"  SKIP (invalid): {url}")
                continue

            # Save HTML file
            filename = url_to_filename(url)
            html_path = HTML_DIR / filename
            html_path.write_text(page_data.html_content, encoding="utf-8")

            # Add to manifest
            manifest.append({
                "url": page_data.url,
                "title": page_data.title,
                "filename": filename,
                "links": page_data.links,
                "final_url": page_data.final_url,
                "saved_at": datetime.now().isoformat(),
            })
            print(f"  Saved: {filename} ({len(page_data.html_content):,} bytes)")

            if i < len(config.TEST_URLS):
                time.sleep(config.DELAY_BETWEEN_REQUESTS)
    finally:
        crawler.close()

    # Write manifest
    manifest_path = FIXTURE_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nDone: {len(manifest)} fixtures saved to {FIXTURE_DIR}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
