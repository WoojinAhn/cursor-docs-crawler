"""Page sorting utilities for organizing documentation pages."""

import logging
from typing import List
from urllib.parse import urlparse

from .models import PageContent


class PageSorter:
    """Handles sorting of pages for logical PDF organization."""
    
    def __init__(self):
        """Initialize page sorter."""
        self.logger = logging.getLogger(__name__)
    
    def sort_pages(self, pages: List[PageContent]) -> List[PageContent]:
        """Sort pages in logical order for PDF generation.
        
        Args:
            pages: List of PageContent objects
            
        Returns:
            Sorted list of PageContent objects
        """
        self.logger.info(f"Sorting {len(pages)} pages")
        
        # Generate order keys for all pages
        for page in pages:
            if not page.order_key:
                page.order_key = self.generate_order_key(page.url)
        
        # Sort by order key
        sorted_pages = sorted(pages, key=lambda p: p.order_key)
        
        self.logger.info("Pages sorted successfully")
        self._log_sort_order(sorted_pages)
        
        return sorted_pages
    
    def generate_order_key(self, url: str) -> str:
        """Generate sorting key based on URL structure.
        
        Args:
            url: Page URL
            
        Returns:
            Sorting key string
        """
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path.strip('/')
            
            # Handle root/index pages - highest priority
            if not path or path in ['index', 'index.html', 'home']:
                return '000_index'
            
            # Handle common important pages
            priority_pages = {
                'getting-started': '001_getting_started',
                'quickstart': '001_quickstart', 
                'introduction': '002_introduction',
                'overview': '003_overview',
                'installation': '004_installation',
                'setup': '005_setup',
            }
            
            if path in priority_pages:
                return priority_pages[path]
            
            # Split path into parts
            parts = path.split('/')
            
            # Clean and process each part
            order_parts = []
            for i, part in enumerate(parts):
                # Clean up part
                clean_part = self._clean_path_part(part)
                
                # Add depth prefix and cleaned part
                order_parts.append(f"{i:03d}_{clean_part}")
            
            # Join parts to create hierarchical key
            order_key = '_'.join(order_parts)
            
            self.logger.debug(f"Generated order key '{order_key}' for URL: {url}")
            return order_key
            
        except Exception as e:
            self.logger.warning(f"Error generating order key for {url}: {e}")
            # Fallback to simple alphabetical
            return f"999_{url}"
    
    def _clean_path_part(self, part: str) -> str:
        """Clean and normalize a path part for sorting.
        
        Args:
            part: Path part to clean
            
        Returns:
            Cleaned path part
        """
        if not part:
            return 'empty'
        
        # Remove file extensions
        clean_part = part.replace('.html', '').replace('.htm', '')
        
        # Replace special characters with underscores
        clean_part = clean_part.replace('-', '_').replace('.', '_')
        
        # Handle numeric prefixes (common in documentation)
        if clean_part and clean_part[0].isdigit():
            # Extract number and text parts
            num_part = ''
            text_part = clean_part
            
            for i, char in enumerate(clean_part):
                if not char.isdigit() and char != '_':
                    num_part = clean_part[:i].rstrip('_')
                    text_part = clean_part[i:].lstrip('_')
                    break
            
            if num_part:
                # Pad number for proper sorting
                try:
                    num = int(num_part)
                    clean_part = f"{num:03d}_{text_part}" if text_part else f"{num:03d}"
                except ValueError:
                    pass
        
        # Ensure it's not empty
        return clean_part or 'unnamed'
    
    def _log_sort_order(self, sorted_pages: List[PageContent]) -> None:
        """Log the final sort order for debugging.
        
        Args:
            sorted_pages: Sorted list of pages
        """
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Final page sort order:")
            for i, page in enumerate(sorted_pages[:20]):  # Log first 20 pages
                self.logger.debug(f"  {i+1:2d}. {page.order_key} -> {page.title} ({page.url})")
            
            if len(sorted_pages) > 20:
                self.logger.debug(f"  ... and {len(sorted_pages) - 20} more pages")
    
    def group_pages_by_section(self, pages: List[PageContent]) -> dict:
        """Group pages by their top-level section.
        
        Args:
            pages: List of PageContent objects
            
        Returns:
            Dictionary mapping section names to lists of pages
        """
        sections = {}
        
        for page in pages:
            try:
                parsed_url = urlparse(page.url)
                path = parsed_url.path.strip('/')
                
                if not path:
                    section = 'Home'
                else:
                    # Get first path component as section
                    section = path.split('/')[0].replace('-', ' ').replace('_', ' ').title()
                
                if section not in sections:
                    sections[section] = []
                
                sections[section].append(page)
                
            except Exception as e:
                self.logger.warning(f"Error grouping page {page.url}: {e}")
                # Add to 'Other' section
                if 'Other' not in sections:
                    sections['Other'] = []
                sections['Other'].append(page)
        
        # Sort pages within each section
        for section_name in sections:
            sections[section_name] = sorted(sections[section_name], key=lambda p: p.order_key)
        
        self.logger.info(f"Grouped pages into {len(sections)} sections: {list(sections.keys())}")
        return sections