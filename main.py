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


def seed_from_llms_txt(url_manager, llms_txt_url: str) -> int:
    """Fetch llms.txt and seed all /docs/* URLs into the URL manager.

    llms.txt lists every official doc page as markdown links with .md suffix.
    We strip the .md to get the actual page URL.

    Returns:
        Number of URLs successfully seeded.
    """
    logger = logging.getLogger(__name__)
    try:
        req = Request(llms_txt_url, headers={"User-Agent": "Cursor Docs Crawler 1.0"})
        with urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
    except (URLError, OSError) as e:
        logger.warning(f"Failed to fetch llms.txt ({llms_txt_url}): {e}")
        return 0

    # Extract URLs: pattern like https://cursor.com/docs/....md
    urls = re.findall(r'https://cursor\.com/docs[^\s)]+\.md', text)
    seeded = 0
    for url in urls:
        clean_url = url.removesuffix(".md")
        if url_manager.add_url(clean_url):
            seeded += 1
    logger.info(f"Seeded {seeded} URLs from llms.txt (found {len(urls)} entries)")
    print(f"[Seed] Added {seeded} new URLs from llms.txt")
    return seeded


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
        default="cursor_docs.pdf",
        help="Output PDF file path (default: cursor_docs.pdf)"
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

    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger_setup = CrawlerLogger(
        level=log_level,
        log_file=args.log_file
    )
    
    # Suppress verbose logging from external libraries
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('weasyprint').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fontTools').setLevel(logging.WARNING)
    logging.getLogger('cssselect2').setLevel(logging.WARNING)
    logging.getLogger('pyphen').setLevel(logging.WARNING)
    
    # Create configuration
    if args.test:
        config = TestConfig()
        print(f"Running in TEST MODE - {len(config.TEST_URLS)} specific pages")
    else:
        config = Config()
    
    # Override config with command line arguments
    if args.output:
        config.OUTPUT_FILE = args.output
    
    if args.max_pages:
        config.MAX_PAGES = args.max_pages
    
    if args.delay:
        config.DELAY_BETWEEN_REQUESTS = args.delay

    if args.lang:
        config.LANGUAGE = args.lang

    # Initialize reporter
    reporter = CrawlReporter()
    
    try:
        # Report start
        reporter.report_start(config.BASE_URL, config.MAX_PAGES)
        
        # Initialize components
        if args.fixture:
            from src.fixture_crawler import FixtureCrawler
            crawler = FixtureCrawler()
        else:
            url_manager = URLManager(config.BASE_URL, config.MAX_PAGES,
                                     config.ALLOWED_PATH_PREFIXES)

            # In test mode, replace BFS discovery with specific test URLs
            if args.test and hasattr(config, 'TEST_URLS'):
                url_manager.clear()
                for url in config.TEST_URLS:
                    url_manager.add_url(url)
            else:
                # Seed URLs from llms.txt to cover pages unreachable via BFS
                seed_from_llms_txt(url_manager, config.LLMS_TXT_URL)

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
    
    except KeyboardInterrupt:
        print("\n⚠️  Crawling interrupted by user")
        return 1
    
    except Exception as e:
        reporter.report_error(e, "Main application")
        print(f"❌ Critical Error: {e}")
        
        # Try to save partial results if any pages were crawled
        try:
            if 'crawled_pages' in locals() and crawled_pages:
                print(f"💾 Attempting to save {len(crawled_pages)} crawled pages as backup...")
                
                from datetime import datetime
                # Create simple backup file
                backup_file = f"backup_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"Cursor Documentation Crawl Backup\n")
                    f.write(f"Generated: {datetime.now()}\n")
                    f.write(f"Error: {str(e)}\n")
                    f.write(f"Pages crawled: {len(crawled_pages)}\n\n")
                    
                    for i, page in enumerate(crawled_pages, 1):
                        f.write(f"=== Page {i}: {page.title} ===\n")
                        f.write(f"URL: {page.url}\n")
                        f.write(f"Status: {page.status_code}\n")
                        f.write(f"Content length: {len(page.html_content)}\n")
                        f.write(f"Links found: {len(page.links)}\n\n")
                
                print(f"✅ Backup saved: {backup_file}")
                
        except Exception as backup_error:
            print(f"⚠️  Could not save backup: {backup_error}")
        
        return 1
    
    finally:
        # Clean up
        try:
            crawler.close()
        except Exception:
            pass
        
        # Report completion
        reporter.report_completion()


if __name__ == "__main__":
    sys.exit(main())