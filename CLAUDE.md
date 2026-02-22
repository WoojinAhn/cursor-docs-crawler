# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A Python web crawler that scrapes the entire Cursor documentation site (cursor.com/docs) using Selenium, cleans the HTML content with BeautifulSoup, and generates a single PDF via WeasyPrint. Designed to produce NotebookLM-ready PDFs.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
# macOS also needs: brew install pango libffi

# Run crawler (full)
python main.py

# Run in test mode (10 representative pages)
python main.py --test

# Run with offline fixtures (no Selenium/network)
python scripts/save_fixtures.py  # One-time: save HTML snapshots
python main.py --test --fixture  # Fast: offline E2E (~6 seconds)

# Generate PDF in a specific language (default: ko)
python main.py --lang en

# Common options
python main.py --output out.pdf --max-pages 20 --delay 2.0 --verbose --log-file crawler.log

# Run all tests
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_url_manager.py

# Run only offline E2E tests (requires fixtures)
python -m pytest tests/test_e2e_offline.py -v

# Run with coverage
python -m pytest tests/ --cov=src

# Lint & format
flake8 src/ tests/
black src/ tests/
```

## Architecture

The pipeline runs in three sequential phases orchestrated by `main.py`:

```
1. Seed + Crawl (seed_from_llms_txt + SeleniumCrawler + URLManager)
   → Fetches cursor.com/llms.txt to seed all official doc URLs (covers BFS-unreachable pages)
   → BFS crawl via headless Chrome, extracts links, builds URL queue
   → Produces List[PageData]

2. Filter (main.py)
   → Removes 404/error pages (title-based), redirect-only duplicates, non-doc endpoints
   → Produces filtered List[PageData]

3. Parse (ContentParser)
   → Strips nav/sidebar/footer, extracts .mdx-content, processes images & YouTube embeds
   → Produces List[PageContent]

4. Generate PDF (PDFGenerator + PageSorter)
   → Sorts pages by URL hierarchy, builds full HTML doc with TOC, renders via WeasyPrint
   → Outputs .pdf file
```

### Key Design Decisions

- **Selenium over requests**: cursor.com/docs uses client-side JS rendering, so Selenium with headless Chrome is required to get rendered HTML.
- **URL deduplication at two levels**: `URLManager` deduplicates during crawl queue management; `PDFGenerator._deduplicate_pages` deduplicates again before PDF generation (handles redirects where original URL != final URL).
- **Redirect tracking**: `SeleniumCrawler` captures `driver.current_url` after page load and stores it as `PageData.final_url`. Both original and final URLs are marked as visited.
- **Locale stripping**: cursor.com auto-redirects to locale-prefixed URLs (e.g. `/ko/docs/...`). `SeleniumCrawler.strip_locale` normalizes these back to canonical `/docs/...` form so deduplication works correctly.
- **Crawler interface**: Both `SeleniumCrawler` and `FixtureCrawler` implement the same `crawl_all() -> List[PageData]` / `close()` interface, making them interchangeable in `main.py`.
- **Content extraction priority**: `ContentParser.extract_main_content` tries selectors in order: `.prose.prose-lg` (current) > `.mdx-content` (legacy) > `main` > `.content` > `article` > various fallbacks > `body`.
- **CSS class stripping order**: Tailwind classes are stripped *after* content extraction — stripping before would remove the `.prose.prose-lg` selector needed for extraction.
- **Protected elements**: Frame elements (`data-name="frame"`) and codebase-indexing images are explicitly protected from removal during HTML cleaning.
- **Fallback PDF**: If WeasyPrint fails on styled HTML, `PDFGenerator` attempts a simplified fallback HTML without custom CSS.
- **Language support**: `--lang` sets Chrome's `Accept-Language` header and `intl.accept_languages` pref, causing cursor.com to serve translated content. Unsupported values silently fall back to `en`. Supported: en, ko, ja, zh, zh-TW, es, fr, pt, ru, tr, id, de.

### Data Flow Models (`src/models.py`)

- `PageData`: Raw crawl output (url, html_content, status_code, links, final_url)
- `PageContent`: Parsed content ready for PDF (url, title, content_html, text_content, images, order_key)
- `CrawlStats`: Session-level statistics

### Page Sorting (`src/page_sorter.py`)

Pages are sorted by URL path hierarchy with priority overrides for common doc pages (getting-started, quickstart, introduction, etc. get sort keys `001_`-`005_`). Root/index pages always sort first (`000_index`).

## CI (GitHub Actions)

`.github/workflows/e2e-test.yml` runs offline E2E tests on every PR (no network needed — uses committed fixtures). A weekly cron (Sun 03:00 UTC) refreshes fixtures from the live site and commits them back. `workflow_dispatch` also available for manual fixture refresh.
