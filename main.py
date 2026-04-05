#!/usr/bin/env python3
"""Main application entry point for Cursor documentation crawler."""

import argparse
import logging
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config, TestConfig
from src.url_manager import URLManager
from src.content_parser import ContentParser
from src.pdf_generator import PDFGenerator
from src.logger import CrawlerLogger, CrawlReporter


def seed_from_llms_txt(url_manager, llms_txt_url: str, seed_regex: str,
                       fallback_path: str = None) -> set:
    """Fetch llms.txt and seed URLs matching *seed_regex* into the URL manager.

    Falls back to a local file when the live fetch fails.

    Returns:
        Set of canonical URLs extracted from llms.txt (with .md stripped).
    """
    logger = logging.getLogger(__name__)
    text = None

    # Try live fetch first
    try:
        req = Request(llms_txt_url, headers={"User-Agent": "Cursor Docs Crawler 1.0"})
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            # Validate: must look like llms.txt, not an HTML bot-protection page
            if body.lstrip().startswith("#"):
                text = body
            else:
                logger.warning("llms.txt response is not valid markdown — ignoring")
    except (URLError, OSError) as e:
        logger.warning(f"Failed to fetch llms.txt ({llms_txt_url}): {e}")

    # Fallback to local snapshot
    if text is None and fallback_path:
        fp = Path(fallback_path)
        if fp.is_file():
            logger.info(f"Using local fallback: {fallback_path}")
            print(f"[Seed] Live llms.txt unavailable — using local snapshot")
            text = fp.read_text(encoding="utf-8")

    if text is None:
        logger.warning("No llms.txt available (live or fallback)")
        return set()

    raw_urls = re.findall(seed_regex, text)
    llms_urls = {url.removesuffix(".md") for url in raw_urls}
    seeded = 0
    for clean_url in llms_urls:
        if url_manager.add_url(clean_url):
            seeded += 1
    logger.info(f"Seeded {seeded} URLs from llms.txt (found {len(llms_urls)} entries)")
    print(f"[Seed] Added {seeded} new URLs from llms.txt")
    return llms_urls


def check_llms_coverage(llms_urls: set, crawled_pages, logger) -> list:
    """Compare llms.txt URLs against actually crawled URLs.

    Returns:
        List of llms.txt URLs that were not crawled.
    """
    crawled_urls = set()
    for p in crawled_pages:
        crawled_urls.add(p.url)
        if p.final_url:
            crawled_urls.add(p.final_url)

    missing = sorted(llms_urls - crawled_urls)

    if not missing:
        logger.info(f"[Coverage] llms.txt {len(llms_urls)} URLs — all covered")
        print(f"[Coverage] llms.txt {len(llms_urls)} URLs — all covered")
    else:
        logger.warning(
            f"[Coverage] {len(missing)}/{len(llms_urls)} llms.txt URLs not crawled"
        )
        print(f"[Coverage] {len(missing)}/{len(llms_urls)} llms.txt URLs not crawled:")
        for url in missing:
            print(f"  - {url}")

    return missing


def run_single_scope(args, scope: str, reporter: CrawlReporter,
                     user_provided_output: bool) -> int:
    """Run the full crawl-parse-PDF pipeline for a single scope.

    Args:
        args: Parsed CLI arguments.
        scope: One of "docs" or "help".
        reporter: CrawlReporter instance for statistics.
        user_provided_output: True if the user explicitly set --output.

    Returns:
        0 on success, 1 on failure.
    """
    # Create configuration
    if args.test:
        config = TestConfig()
        print(f"Running in TEST MODE - {len(config.active_test_urls)} specific pages")
    else:
        config = Config()

    # Apply scope
    config.SCOPE = scope
    config.BASE_URL = config.scope_base_url
    config.ALLOWED_PATH_PREFIXES = config.scope_prefixes

    # Determine output file
    if user_provided_output:
        config.OUTPUT_FILE = args.output
    else:
        config.OUTPUT_FILE = config.scope_output_file

    # Override config with command line arguments
    if args.max_pages:
        config.MAX_PAGES = args.max_pages

    if args.delay:
        config.DELAY_BETWEEN_REQUESTS = args.delay

    if args.lang:
        if args.lang in config.SUPPORTED_LANGUAGES:
            config.LANGUAGE = args.lang
        else:
            print(f"[Warning] Unsupported language '{args.lang}', falling back to 'en'")
            config.LANGUAGE = "en"

    crawler = None
    try:
        # Report start
        reporter.report_start(config.BASE_URL, config.MAX_PAGES)

        # Initialize components
        if args.fixture:
            if scope != "docs":
                print(f"[Warning] --fixture only supports docs scope (fixtures are docs-only), skipping '{scope}'")
                return 1
            from src.fixture_crawler import FixtureCrawler
            crawler = FixtureCrawler()
        else:
            url_manager = URLManager(config.BASE_URL, config.MAX_PAGES,
                                     config.ALLOWED_PATH_PREFIXES)

            # In test mode, replace BFS discovery with specific test URLs
            llms_urls = set()
            if args.test and hasattr(config, 'active_test_urls'):
                url_manager.clear()
                for url in config.active_test_urls:
                    url_manager.add_url(url)
            else:
                # Seed URLs from llms.txt to cover pages unreachable via BFS
                fallback = str(Path(__file__).parent / ".github" / "llms-txt-snapshot.txt")
                llms_urls = seed_from_llms_txt(
                    url_manager, config.LLMS_TXT_URL, config.scope_seed_regex,
                    fallback_path=fallback,
                )

            from src.selenium_crawler import SeleniumCrawler
            crawler = SeleniumCrawler(config, url_manager)

        content_parser = ContentParser(config)
        pdf_generator = PDFGenerator(config)

        # Crawl pages
        print("Starting web crawling...")
        crawled_pages = crawler.crawl_all()

        if not crawled_pages:
            print("No pages were successfully crawled!")
            return 1

        # Report crawling statistics
        if not args.fixture:
            reporter.report_crawl_stats(url_manager, len(crawled_pages))

        # Filter out 404 / error pages (Selenium can't detect HTTP status codes)
        _error_title_patterns = ['page could not be found', 'page not found', '404 error']
        crawled_pages = [
            p for p in crawled_pages
            if not any(pat in p.title.lower() for pat in _error_title_patterns)
        ]

        # Filter out redirect-only pages: if a page redirected to a different
        # URL that is also crawled as its own entry, drop the redirect source.
        crawled_urls = {p.url for p in crawled_pages}
        before_redirect_filter = len(crawled_pages)
        crawled_pages = [
            p for p in crawled_pages
            if not p.final_url
            or p.final_url == p.url
            or p.final_url not in crawled_urls
        ]
        redirect_filtered = before_redirect_filter - len(crawled_pages)
        if redirect_filtered:
            print(f"[Filter] Removed {redirect_filtered} redirect-only pages")

        # Check llms.txt coverage (skip in test/fixture mode)
        if not args.fixture and not args.test and llms_urls:
            check_llms_coverage(llms_urls, crawled_pages, logging.getLogger(__name__))

        # Process content
        print("Processing page content...")
        processed_pages = []

        total = len(crawled_pages)
        for idx, page_data in enumerate(crawled_pages, 1):
            print(f"[Main] Parsing page {idx}/{total}: {page_data.url}")
            try:
                page_content = content_parser.parse_page(page_data)
                processed_pages.append(page_content)
            except Exception as e:
                print(f"Error processing page {page_data.url}: {e}")
                continue

        if not processed_pages:
            print("No pages were successfully processed!")
            return 1

        # Report content statistics
        reporter.report_content_stats(processed_pages)

        # Generate PDF
        print(f"Generating PDF: {config.OUTPUT_FILE}")
        pdf_success = pdf_generator.generate_pdf(processed_pages, config.OUTPUT_FILE)

        # Report PDF generation
        reporter.report_pdf_generation(config.OUTPUT_FILE, pdf_success)

        if pdf_success:
            print(f"✅ PDF generated successfully: {config.OUTPUT_FILE}")
            print(f"📄 Total pages: {len(processed_pages)}")

            # Calculate total words and images
            total_words = sum(page.word_count for page in processed_pages)
            total_images = sum(page.image_count for page in processed_pages)

            print(f"📝 Total words: {total_words:,}")
            print(f"🖼️  Total images: {total_images}")

            return 0
        else:
            print("❌ PDF generation failed!")
            return 1

    finally:
        # Clean up crawler
        if crawler is not None:
            try:
                crawler.close()
            except Exception:
                pass


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Cursor Documentation Crawler - Convert cursor.com/docs to PDF"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (limited to 5 pages)"
    )

    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output PDF file path (default: cursor_docs.pdf or cursor_help.pdf depending on scope)"
    )

    parser.add_argument(
        "--max-pages", "-m",
        type=int,
        help="Maximum number of pages to crawl"
    )

    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--log-file",
        help="Log file path (optional)"
    )

    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use saved HTML fixtures instead of live crawling (requires tests/fixtures/)"
    )

    parser.add_argument(
        "--lang", "-l",
        default="ko",
        help="Language for crawling and PDF output (default: ko)"
    )

    parser.add_argument(
        "--scope", "-s",
        choices=["docs", "help", "all"],
        default="docs",
        help="Crawl scope: 'docs' (technical reference), 'help' (user help center), 'all' (both as separate PDFs). Default: docs"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger_setup = CrawlerLogger(
        level=log_level,
        log_file=args.log_file
    )

    # Suppress verbose logging from external libraries
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('seleniumbase').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('weasyprint').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fontTools').setLevel(logging.WARNING)
    logging.getLogger('cssselect2').setLevel(logging.WARNING)
    logging.getLogger('pyphen').setLevel(logging.WARNING)

    # Determine scopes to run
    scopes = ["docs", "help"] if args.scope == "all" else [args.scope]

    # Detect if user explicitly provided --output
    user_provided_output = args.output is not None
    # When running all scopes, ignore user-provided output (each scope uses its own default)
    if args.scope == "all" and user_provided_output:
        print("[Warning] --output is ignored when --scope=all; each scope uses its default filename")
        user_provided_output = False

    # Initialize reporter
    reporter = CrawlReporter()

    exit_code = 0
    try:
        for scope in scopes:
            if len(scopes) > 1:
                print(f"\n{'=' * 60}")
                print(f"  Scope: {scope}")
                print(f"{'=' * 60}\n")

            result = run_single_scope(args, scope, reporter, user_provided_output)
            if result != 0:
                exit_code = 1

    except KeyboardInterrupt:
        print("\n⚠️  Crawling interrupted by user")
        return 1

    except Exception as e:
        reporter.report_error(e, "Main application")
        print(f"❌ Critical Error: {e}")

        # Try to save partial results if any pages were crawled
        try:
            from datetime import datetime
            backup_file = f"backup_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(f"Cursor Documentation Crawl Backup\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Error: {str(e)}\n\n")
            print(f"✅ Backup saved: {backup_file}")
        except Exception as backup_error:
            print(f"⚠️  Could not save backup: {backup_error}")

        return 1

    finally:
        # Report completion
        reporter.report_completion()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
