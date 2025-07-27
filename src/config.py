"""Configuration settings for the Cursor documentation crawler."""

from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import os


@dataclass
class Config:
    """Main configuration class for the crawler."""
    
    # Basic settings
    BASE_URL: str = "https://docs.cursor.com/"
    OUTPUT_FILE: str = "cursor_docs.pdf"
    USER_AGENT: str = "Cursor Docs Crawler 1.0"
    
    # Crawling settings
    MAX_PAGES: Optional[int] = None  # None for unlimited, number for test mode
    DELAY_BETWEEN_REQUESTS: float = 1.0
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Content filtering
    EXCLUDED_SELECTORS: List[str] = None
    CONTENT_SELECTORS: List[str] = None
    
    def __post_init__(self):
        """Initialize default values and validate configuration."""
        self._set_default_selectors()
        self._validate_config()
    
    def _set_default_selectors(self):
        """Set default values for selector lists."""
        if self.EXCLUDED_SELECTORS is None:
            self.EXCLUDED_SELECTORS = [
                "nav", "header", "footer", ".sidebar", 
                ".navigation", ".breadcrumb", ".toc",
                ".advertisement", ".promo", ".banner"
            ]
        
        if self.CONTENT_SELECTORS is None:
            self.CONTENT_SELECTORS = [
                "main", ".content", "article", ".documentation",
                ".main-content", "#content"
            ]
    
    def _validate_config(self):
        """Validate configuration values."""
        # Validate URL
        if not self.BASE_URL:
            raise ValueError("BASE_URL cannot be empty")
        
        parsed_url = urlparse(self.BASE_URL)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid BASE_URL: {self.BASE_URL}")
        
        # Validate numeric values
        if self.MAX_PAGES is not None and self.MAX_PAGES <= 0:
            raise ValueError("MAX_PAGES must be positive or None")
        
        if self.DELAY_BETWEEN_REQUESTS < 0:
            raise ValueError("DELAY_BETWEEN_REQUESTS cannot be negative")
        
        if self.REQUEST_TIMEOUT <= 0:
            raise ValueError("REQUEST_TIMEOUT must be positive")
        
        if self.MAX_RETRIES < 0:
            raise ValueError("MAX_RETRIES cannot be negative")
        
        # Validate output file
        if not self.OUTPUT_FILE:
            raise ValueError("OUTPUT_FILE cannot be empty")
        
        if not self.OUTPUT_FILE.endswith('.pdf'):
            raise ValueError("OUTPUT_FILE must have .pdf extension")
        
        # Check if output directory is writable
        output_dir = os.path.dirname(self.OUTPUT_FILE) or '.'
        if not os.access(output_dir, os.W_OK):
            raise ValueError(f"Output directory is not writable: {output_dir}")
    
    @property
    def domain(self) -> str:
        """Get domain from base URL."""
        return urlparse(self.BASE_URL).netloc
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base URL."""
        return urlparse(url).netloc == self.domain


@dataclass
class TestConfig(Config):
    """Test configuration with limited pages."""
    
    MAX_PAGES: int = 5
    TEST_URLS: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self._set_default_test_urls()
        self._validate_test_config()
    
    def _set_default_test_urls(self):
        """Set default test URLs."""
        if self.TEST_URLS is None:
            self.TEST_URLS = [
                "https://docs.cursor.com/",
                "https://docs.cursor.com/getting-started",
                "https://docs.cursor.com/features",
                "https://docs.cursor.com/settings",
                "https://docs.cursor.com/troubleshooting"
            ]
    
    def _validate_test_config(self):
        """Validate test-specific configuration."""
        if not self.TEST_URLS:
            raise ValueError("TEST_URLS cannot be empty")
        
        # Validate each test URL
        for url in self.TEST_URLS:
            if not url:
                raise ValueError("Test URL cannot be empty")
            
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid test URL: {url}")
            
            # Ensure test URLs are from the same domain
            if not self.is_same_domain(url):
                raise ValueError(f"Test URL must be from same domain as BASE_URL: {url}")
        
        # Ensure MAX_PAGES matches or exceeds test URL count
        if len(self.TEST_URLS) > self.MAX_PAGES:
            raise ValueError(f"MAX_PAGES ({self.MAX_PAGES}) should be >= number of TEST_URLS ({len(self.TEST_URLS)})")