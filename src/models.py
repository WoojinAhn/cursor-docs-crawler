"""Data models for the Cursor documentation crawler."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class PageData:
    """Raw page data from web crawling."""
    
    url: str
    title: str
    html_content: str
    status_code: int
    crawled_at: datetime = field(default_factory=datetime.now)
    links: List[str] = field(default_factory=list)
    final_url: Optional[str] = None  # Final URL after redirects
    
    def __post_init__(self):
        """Validate the page data after initialization."""
        if not self.url:
            raise ValueError("URL cannot be empty")
        
        if not self.html_content and self.status_code == 200:
            raise ValueError("HTML content cannot be empty for successful requests")
        
        # Normalize URL
        self.url = self.url.rstrip('/')
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        return urlparse(self.url).netloc
    
    @property
    def path(self) -> str:
        """Extract path from URL."""
        return urlparse(self.url).path
    
    def is_valid(self) -> bool:
        """Check if the page data is valid."""
        return (
            bool(self.url) and 
            self.status_code == 200 and 
            bool(self.html_content.strip())
        )


@dataclass
class PageContent:
    """Processed page content ready for PDF generation."""
    
    url: str
    title: str
    content_html: str
    text_content: str
    images: List[str] = field(default_factory=list)
    order_key: str = ""
    final_url: Optional[str] = None  # Final URL after redirects
    
    def __post_init__(self):
        """Generate order key and validate content."""
        if not self.order_key:
            self.order_key = self._generate_order_key()
        
        if not self.title:
            self.title = self._extract_title_from_url()
    
    def _generate_order_key(self) -> str:
        """Generate sorting key based on URL structure."""
        path = urlparse(self.url).path.strip('/')
        
        # Handle root/index pages
        if not path or path in ['index', 'index.html']:
            return '000_index'
        
        # Split path and create hierarchical key
        parts = path.split('/')
        order_parts = []
        
        for i, part in enumerate(parts):
            # Clean up part (remove file extensions, special chars)
            clean_part = part.replace('.html', '').replace('-', '_')
            order_parts.append(f"{i:03d}_{clean_part}")
        
        return '_'.join(order_parts)
    
    def _extract_title_from_url(self) -> str:
        """Extract a readable title from URL if title is missing."""
        path = urlparse(self.url).path.strip('/')
        if not path:
            return "Home"
        
        # Get last part of path and make it readable
        last_part = path.split('/')[-1]
        title = last_part.replace('-', ' ').replace('_', ' ')
        return title.title()
    
    @property
    def word_count(self) -> int:
        """Count words in text content."""
        return len(self.text_content.split()) if self.text_content else 0
    
    @property
    def image_count(self) -> int:
        """Count number of images."""
        return len(self.images)
    
    def is_valid(self) -> bool:
        """Check if the page content is valid."""
        return (
            bool(self.url) and 
            bool(self.title) and 
            (bool(self.content_html) or bool(self.text_content))
        )


@dataclass
class CrawlStats:
    """Statistics for crawling session."""
    
    total_pages_found: int = 0
    pages_crawled: int = 0
    pages_failed: int = 0
    pages_skipped: int = 0
    total_images: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize start time if not provided."""
        if self.start_time is None:
            self.start_time = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate crawling duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_pages_found == 0:
            return 0.0
        return (self.pages_crawled / self.total_pages_found) * 100
    
    def finish(self):
        """Mark crawling as finished."""
        self.end_time = datetime.now()
    
    def add_page_found(self):
        """Increment pages found counter."""
        self.total_pages_found += 1
    
    def add_page_crawled(self):
        """Increment pages crawled counter."""
        self.pages_crawled += 1
    
    def add_page_failed(self):
        """Increment pages failed counter."""
        self.pages_failed += 1
    
    def add_page_skipped(self):
        """Increment pages skipped counter."""
        self.pages_skipped += 1
    
    def add_images(self, count: int):
        """Add to total images count."""
        self.total_images += count
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        return {
            'total_pages_found': self.total_pages_found,
            'pages_crawled': self.pages_crawled,
            'pages_failed': self.pages_failed,
            'pages_skipped': self.pages_skipped,
            'total_images': self.total_images,
            'success_rate': round(self.success_rate, 2),
            'duration_seconds': self.duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }