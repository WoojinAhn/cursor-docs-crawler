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

# Run in test mode (5-page limit)
python main.py --test

# Common options
python main.py --output out.pdf --max-pages 20 --delay 2.0 --verbose --log-file crawler.log

# Run all tests
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_url_manager.py

# Run with coverage
python -m pytest tests/ --cov=src

# Lint & format
flake8 src/ tests/
black src/ tests/
```

## Architecture

The pipeline runs in three sequential phases orchestrated by `main.py`:

```
1. Crawl (SeleniumCrawler + URLManager)
   → BFS crawl via headless Chrome, extracts links, builds URL queue
   → Produces List[PageData]

2. Parse (ContentParser)
   → Strips nav/sidebar/footer, extracts .mdx-content, processes images & YouTube embeds
   → Produces List[PageContent]

3. Generate PDF (PDFGenerator + PageSorter)
   → Sorts pages by URL hierarchy, builds full HTML doc with TOC, renders via WeasyPrint
   → Outputs .pdf file
```

### Key Design Decisions

- **Selenium over requests**: cursor.com/docs uses client-side JS rendering, so Selenium with headless Chrome is required to get rendered HTML.
- **URL deduplication at two levels**: `URLManager` deduplicates during crawl queue management; `PDFGenerator._deduplicate_pages` deduplicates again before PDF generation (handles redirects where original URL != final URL).
- **Redirect tracking**: `SeleniumCrawler` captures `driver.current_url` after page load and stores it as `PageData.final_url`. Both original and final URLs are marked as visited.
- **Content extraction priority**: `ContentParser.extract_main_content` tries selectors in order: `.prose.prose-lg` (current) > `.mdx-content` (legacy) > `main` > `.content` > `article` > various fallbacks > `body`.
- **Protected elements**: Frame elements (`data-name="frame"`) and codebase-indexing images are explicitly protected from removal during HTML cleaning.
- **Fallback PDF**: If WeasyPrint fails on styled HTML, `PDFGenerator` attempts a simplified fallback HTML without custom CSS.

### Data Flow Models (`src/models.py`)

- `PageData`: Raw crawl output (url, html_content, status_code, links, final_url)
- `PageContent`: Parsed content ready for PDF (url, title, content_html, text_content, images, order_key)
- `CrawlStats`: Session-level statistics

### Page Sorting (`src/page_sorter.py`)

Pages are sorted by URL path hierarchy with priority overrides for common doc pages (getting-started, quickstart, introduction, etc. get sort keys `001_`-`005_`). Root/index pages always sort first (`000_index`).
