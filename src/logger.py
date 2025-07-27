"""Logging configuration and utilities."""

import logging
import sys
from datetime import datetime
from typing import Optional
import colorlog

from .constants import LOG_FORMAT, DATE_FORMAT


class CrawlerLogger:
    """Centralized logging configuration for the crawler."""
    
    def __init__(self, name: str = "cursor_crawler", level: str = "INFO", 
                 use_colors: bool = True, log_file: Optional[str] = None):
        """Initialize logger configuration.
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            use_colors: Whether to use colored output
            log_file: Optional log file path
        """
        self.name = name
        self.level = getattr(logging, level.upper())
        self.use_colors = use_colors
        self.log_file = log_file
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Get root logger
        logger = logging.getLogger()
        logger.setLevel(self.level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        
        if self.use_colors and colorlog:
            # Colored formatter for console
            color_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=DATE_FORMAT,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
        else:
            # Standard formatter
            formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
            console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
        # File handler if specified
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(self.level)
            
            file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            
            logger.addHandler(file_handler)
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance.
        
        Args:
            name: Logger name (uses default if None)
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name or self.name)


class ProgressTracker:
    """Tracks and reports progress during crawling."""
    
    def __init__(self, total_expected: Optional[int] = None):
        """Initialize progress tracker.
        
        Args:
            total_expected: Expected total number of items (optional)
        """
        self.total_expected = total_expected
        self.current_count = 0
        self.start_time = datetime.now()
        self.logger = logging.getLogger(__name__)
        
        # Progress reporting intervals
        self.report_interval = 10  # Report every N items
        self.last_report_time = self.start_time
    
    def update(self, increment: int = 1, message: Optional[str] = None):
        """Update progress counter.
        
        Args:
            increment: Amount to increment counter
            message: Optional custom message
        """
        self.current_count += increment
        
        # Check if we should report progress
        if (self.current_count % self.report_interval == 0 or 
            (self.total_expected and self.current_count >= self.total_expected)):
            self._report_progress(message)
    
    def _report_progress(self, custom_message: Optional[str] = None):
        """Report current progress.
        
        Args:
            custom_message: Optional custom message
        """
        now = datetime.now()
        elapsed = (now - self.start_time).total_seconds()
        
        if custom_message:
            message = custom_message
        else:
            if self.total_expected:
                percentage = (self.current_count / self.total_expected) * 100
                message = f"Progress: {self.current_count}/{self.total_expected} ({percentage:.1f}%)"
            else:
                message = f"Progress: {self.current_count} items processed"
        
        # Add timing information
        if elapsed > 0:
            rate = self.current_count / elapsed
            message += f" | Rate: {rate:.2f} items/sec"
        
        message += f" | Elapsed: {elapsed:.1f}s"
        
        self.logger.info(message)
        self.last_report_time = now
    
    def finish(self, final_message: Optional[str] = None):
        """Mark progress as finished and report final statistics.
        
        Args:
            final_message: Optional final message
        """
        end_time = datetime.now()
        total_elapsed = (end_time - self.start_time).total_seconds()
        
        if final_message:
            message = final_message
        else:
            message = f"Completed: {self.current_count} items processed"
        
        message += f" | Total time: {total_elapsed:.1f}s"
        
        if total_elapsed > 0:
            avg_rate = self.current_count / total_elapsed
            message += f" | Average rate: {avg_rate:.2f} items/sec"
        
        self.logger.info(message)


class CrawlReporter:
    """Generates detailed reports about crawling sessions."""
    
    def __init__(self):
        """Initialize crawl reporter."""
        self.logger = logging.getLogger(__name__)
        self.start_time = datetime.now()
    
    def report_start(self, base_url: str, max_pages: Optional[int] = None):
        """Report crawling start.
        
        Args:
            base_url: Base URL being crawled
            max_pages: Maximum pages to crawl (if limited)
        """
        self.logger.info("=" * 60)
        self.logger.info("CURSOR DOCUMENTATION CRAWLER STARTED")
        self.logger.info("=" * 60)
        self.logger.info(f"Base URL: {base_url}")
        self.logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if max_pages:
            self.logger.info(f"Page limit: {max_pages} pages")
        else:
            self.logger.info("Page limit: Unlimited")
        
        self.logger.info("-" * 60)
    
    def report_crawl_stats(self, url_manager, pages_crawled: int):
        """Report crawling statistics.
        
        Args:
            url_manager: URLManager instance
            pages_crawled: Number of pages successfully crawled
        """
        stats = url_manager.get_stats()
        
        self.logger.info("-" * 60)
        self.logger.info("CRAWLING STATISTICS")
        self.logger.info("-" * 60)
        self.logger.info(f"URLs discovered: {stats['total_found']}")
        self.logger.info(f"Pages crawled: {pages_crawled}")
        self.logger.info(f"Pages failed: {stats['failed']}")
        self.logger.info(f"Pages skipped: {stats['skipped']}")
        self.logger.info(f"Duplicate URLs: {stats['duplicates']}")
        self.logger.info(f"Success rate: {stats['success_rate']}%")
    
    def report_content_stats(self, pages):
        """Report content processing statistics.
        
        Args:
            pages: List of processed PageContent objects
        """
        if not pages:
            return
        
        total_words = sum(page.word_count for page in pages)
        total_images = sum(page.image_count for page in pages)
        avg_words = total_words / len(pages) if pages else 0
        
        self.logger.info("-" * 60)
        self.logger.info("CONTENT STATISTICS")
        self.logger.info("-" * 60)
        self.logger.info(f"Total pages processed: {len(pages)}")
        self.logger.info(f"Total words: {total_words:,}")
        self.logger.info(f"Total images: {total_images}")
        self.logger.info(f"Average words per page: {avg_words:.1f}")
        
        # Find longest and shortest pages
        if pages:
            longest_page = max(pages, key=lambda p: p.word_count)
            shortest_page = min(pages, key=lambda p: p.word_count)
            
            self.logger.info(f"Longest page: {longest_page.title} ({longest_page.word_count} words)")
            self.logger.info(f"Shortest page: {shortest_page.title} ({shortest_page.word_count} words)")
    
    def report_pdf_generation(self, output_path: str, success: bool):
        """Report PDF generation results.
        
        Args:
            output_path: Path to generated PDF
            success: Whether PDF generation was successful
        """
        self.logger.info("-" * 60)
        self.logger.info("PDF GENERATION")
        self.logger.info("-" * 60)
        
        if success:
            self.logger.info(f"PDF generated successfully: {output_path}")
            
            # Try to get file size
            try:
                import os
                file_size = os.path.getsize(output_path)
                size_mb = file_size / (1024 * 1024)
                self.logger.info(f"PDF file size: {size_mb:.2f} MB")
            except Exception:
                pass
        else:
            self.logger.error(f"PDF generation failed: {output_path}")
    
    def report_completion(self):
        """Report crawling completion."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        self.logger.info("-" * 60)
        self.logger.info("CRAWLING COMPLETED")
        self.logger.info("-" * 60)
        self.logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Total duration: {total_duration:.1f} seconds")
        
        if total_duration >= 60:
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)
            self.logger.info(f"Duration: {minutes}m {seconds}s")
        
        self.logger.info("=" * 60)
    
    def report_error(self, error: Exception, context: str = ""):
        """Report an error with context.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        self.logger.error("-" * 60)
        self.logger.error("ERROR OCCURRED")
        self.logger.error("-" * 60)
        
        if context:
            self.logger.error(f"Context: {context}")
        
        self.logger.error(f"Error type: {type(error).__name__}")
        self.logger.error(f"Error message: {str(error)}")
        self.logger.error("-" * 60)