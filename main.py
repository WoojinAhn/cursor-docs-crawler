#!/usr/bin/env python3
"""Main application entry point for Cursor documentation crawler."""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config, TestConfig
from src.url_manager import URLManager
from src.content_parser import ContentParser
from src.pdf_generator import PDFGenerator
from src.logger import CrawlerLogger, CrawlReporter


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Cursor Documentation Crawler - Convert docs.cursor.com to PDF"
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
    

    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger_setup = CrawlerLogger(
        level=log_level,
        log_file=args.log_file
    )
    
    # Suppress verbose logging from external libraries
    import logging
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
        print("Running in TEST MODE - limited to 5 pages")
    else:
        config = Config()
    
    # Override config with command line arguments
    if args.output:
        config.OUTPUT_FILE = args.output
    
    if args.max_pages:
        config.MAX_PAGES = args.max_pages
    
    if args.delay:
        config.DELAY_BETWEEN_REQUESTS = args.delay
    
    # Initialize reporter
    reporter = CrawlReporter()
    
    try:
        # Report start
        reporter.report_start(config.BASE_URL, config.MAX_PAGES)
        
        # Initialize components
        url_manager = URLManager(config.BASE_URL, config.MAX_PAGES)
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
        reporter.report_crawl_stats(url_manager, len(crawled_pages))
        
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
        except:
            pass
        
        # Report completion
        reporter.report_completion()


if __name__ == "__main__":
    sys.exit(main())