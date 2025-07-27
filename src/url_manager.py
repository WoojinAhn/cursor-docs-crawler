"""URL management system for the Cursor documentation crawler."""

from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import logging
from collections import deque

from .config import Config


class URLManager:
    """Manages URLs for crawling with deduplication and filtering."""
    
    def __init__(self, base_url: str, max_pages: Optional[int] = None):
        """Initialize URL manager.
        
        Args:
            base_url: Base URL for crawling
            max_pages: Maximum number of pages to crawl (None for unlimited)
        """
        self.base_url = base_url.rstrip('/')
        self.max_pages = max_pages
        
        # URL storage
        self._urls_to_visit: deque = deque()
        self._visited_urls: Set[str] = set()
        self._failed_urls: Set[str] = set()
        self._skipped_urls: Set[str] = set()
        
        # Statistics
        self._stats = {
            'total_found': 0,
            'visited': 0,
            'failed': 0,
            'skipped': 0,
            'duplicates': 0
        }
        
        # Domain for filtering
        self.domain = urlparse(self.base_url).netloc
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Add initial URL
        self.add_url(self.base_url)
    
    def add_url(self, url: str) -> bool:
        """Add URL to crawling queue.
        
        Args:
            url: URL to add
            
        Returns:
            True if URL was added, False if skipped
        """
        if not url:
            return False
        
        # Normalize URL
        normalized_url = self._normalize_url(url)
        
        # Check if we should crawl this URL
        if not self.should_crawl(normalized_url):
            return False
        
        # Check for duplicates
        if normalized_url in self._visited_urls or normalized_url in [u for u in self._urls_to_visit]:
            self._stats['duplicates'] += 1
            self.logger.debug(f"Duplicate URL skipped: {normalized_url}")
            return False
        
        # Check page limit
        if self.max_pages and self._stats['total_found'] >= self.max_pages:
            self._skipped_urls.add(normalized_url)
            self._stats['skipped'] += 1
            self.logger.debug(f"Page limit reached, URL skipped: {normalized_url}")
            return False
        
        # Add to queue
        self._urls_to_visit.append(normalized_url)
        self._stats['total_found'] += 1
        self.logger.debug(f"URL added to queue: {normalized_url}")
        return True
    
    def get_next_url(self) -> Optional[str]:
        """Get next URL to crawl.
        
        Returns:
            Next URL or None if queue is empty
        """
        if not self._urls_to_visit:
            return None
        
        url = self._urls_to_visit.popleft()
        return url
    
    def mark_visited(self, url: str) -> None:
        """Mark URL as visited.
        
        Args:
            url: URL that was visited
        """
        normalized_url = self._normalize_url(url)
        self._visited_urls.add(normalized_url)
        self._stats['visited'] += 1
        self.logger.debug(f"URL marked as visited: {normalized_url}")
    
    def mark_failed(self, url: str) -> None:
        """Mark URL as failed.
        
        Args:
            url: URL that failed to crawl
        """
        normalized_url = self._normalize_url(url)
        self._failed_urls.add(normalized_url)
        self._stats['failed'] += 1
        self.logger.warning(f"URL marked as failed: {normalized_url}")
    
    def is_visited(self, url: str) -> bool:
        """Check if URL has been visited.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL was visited
        """
        normalized_url = self._normalize_url(url)
        return normalized_url in self._visited_urls
    
    def should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL should be crawled
        """
        if not url:
            return False
        
        try:
            parsed_url = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
            
            # Must be same domain
            if parsed_url.netloc != self.domain:
                return False
            
            # Skip hash-only links
            if parsed_url.fragment and not parsed_url.path:
                return False
            
            # Skip common file extensions that aren't HTML
            path = parsed_url.path.lower()
            skip_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.zip']
            if any(path.endswith(ext) for ext in skip_extensions):
                return False
            
            # Skip common non-content paths
            skip_paths = ['/api/', '/admin/', '/login/', '/logout/', '/search/']
            if any(skip_path in path for skip_path in skip_paths):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking URL {url}: {e}")
            return False
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url:
            return url
        
        # Convert relative URLs to absolute
        if url.startswith('/'):
            url = urljoin(self.base_url, url)
        elif not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        # Parse and rebuild URL to normalize
        parsed = urlparse(url)
        
        # Remove fragment (hash)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Add query if present
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        # Remove trailing slash except for root
        if normalized.endswith('/') and len(parsed.path) > 1:
            normalized = normalized.rstrip('/')
        
        return normalized
    
    def get_stats(self) -> Dict[str, int]:
        """Get crawling statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_found': self._stats['total_found'],
            'visited': self._stats['visited'],
            'failed': self._stats['failed'],
            'skipped': self._stats['skipped'],
            'duplicates': self._stats['duplicates'],
            'remaining': len(self._urls_to_visit),
            'success_rate': round((self._stats['visited'] / max(self._stats['total_found'], 1)) * 100, 2)
        }
    
    def has_urls(self) -> bool:
        """Check if there are URLs to crawl.
        
        Returns:
            True if there are URLs in queue
        """
        return len(self._urls_to_visit) > 0
    
    def get_visited_urls(self) -> List[str]:
        """Get list of visited URLs.
        
        Returns:
            List of visited URLs
        """
        return list(self._visited_urls)
    
    def get_failed_urls(self) -> List[str]:
        """Get list of failed URLs.
        
        Returns:
            List of failed URLs
        """
        return list(self._failed_urls)
    
    def clear(self) -> None:
        """Clear all URLs and statistics."""
        self._urls_to_visit.clear()
        self._visited_urls.clear()
        self._failed_urls.clear()
        self._skipped_urls.clear()
        self._stats = {
            'total_found': 0,
            'visited': 0,
            'failed': 0,
            'skipped': 0,
            'duplicates': 0
        }
        self.logger.info("URL manager cleared")