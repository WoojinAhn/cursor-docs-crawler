"""Content parser for cleaning and extracting documentation content."""

import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag, NavigableString

from .config import Config
from .models import PageData, PageContent


class ContentParser:
    """Parser for cleaning HTML content and extracting main documentation."""
    
    def __init__(self, config: Config):
        """Initialize content parser.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def parse_page(self, page_data: PageData) -> PageContent:
        """Parse page data into clean content.
        
        Args:
            page_data: Raw page data from crawler
            
        Returns:
            PageContent object with cleaned content
        """
        self.logger.info(f"[Parser] Parsing content for: {page_data.url}")
        
        try:
            soup = BeautifulSoup(page_data.html_content, 'html.parser')
            
            # Remove unwanted elements
            cleaned_soup = self.remove_unwanted_elements(soup)
            
            # Extract main content
            main_content = self.extract_main_content(cleaned_soup)
            
            # Process images
            processed_content = self.process_images(main_content)
            
            # Process YouTube links
            final_content = self.process_youtube_links(processed_content)
            
            # Extract text content
            text_content = self._extract_text_content(final_content)
            
            # Extract image URLs
            image_urls = self._extract_image_urls(final_content)
            
            # Create page content
            page_content = PageContent(
                url=page_data.url,
                title=page_data.title,
                content_html=str(final_content),
                text_content=text_content,
                images=image_urls,
                final_url=page_data.final_url
            )
            
            self.logger.debug(
                f"Parsed {page_data.url}: {page_content.word_count} words, "
                f"{page_content.image_count} images"
            )
            
            return page_content
            
        except Exception as e:
            self.logger.error(f"Error parsing {page_data.url}: {e}")
            # Try to extract basic content as fallback
            try:
                basic_soup = BeautifulSoup(page_data.html_content, 'html.parser')
                basic_text = basic_soup.get_text(strip=True)[:1000]  # First 1000 chars
                basic_title = page_data.title or "Error Page"
                
                return PageContent(
                    url=page_data.url,
                    title=basic_title,
                    content_html=f"<p>Content parsing failed. Raw text preview:</p><pre>{basic_text}</pre>",
                    text_content=basic_text,
                    images=[]
                )
            except:
                # Ultimate fallback
                return PageContent(
                    url=page_data.url,
                    title=page_data.title or "Error Page",
                    content_html=f"<p>Error parsing content: {str(e)}</p>",
                    text_content=f"Error parsing content: {str(e)}",
                    images=[]
                )
    
    def _is_protected_element(self, element: Tag) -> bool:
        """Check if element should be protected from removal.
        
        Args:
            element: BeautifulSoup element to check
            
        Returns:
            True if element should be protected
        """
        # Protect frame elements
        if element.get('data-name') == 'frame':
            self.logger.debug(f"🛡️ Protecting frame element with data-name='frame'")
            return True
        
        # Protect elements containing codebase-indexing images
        if element.find('img', src=lambda s: s and 'codebase-indexing' in s):
            self.logger.debug(f"🛡️ Protecting element containing codebase-indexing image")
            return True
        
        # Protect parent elements of frame elements
        if element.find('[data-name="frame"]'):
            self.logger.debug(f"🛡️ Protecting parent of frame element")
            return True
        
        return False

    def remove_unwanted_elements(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove unwanted UI elements from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Cleaned BeautifulSoup object
        """
        # Remove elements by selector
        for selector in self.config.EXCLUDED_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove additional navigation and UI elements specific to docs.cursor.com
        additional_selectors = [
            # Note: Excluding [data-testid] to preserve data-name="frame" elements
            '.sidebar',
            '.navigation',
            '.nav-menu',
            '.menu',
            '.header-nav',
            '.footer-nav',
            '.breadcrumb',
            '.pagination',
            '.search-box',
            '.search-form',
            '[role="navigation"]',
            '[role="banner"]',
            '[role="complementary"]',
            '[aria-label*="navigation"]',
            '[aria-label*="menu"]',
            '.docs-sidebar',
            '.docs-nav',
            '.table-of-contents',
            '.toc',
            # Cursor-specific elements (Nextra framework)
            '.nextra-sidebar',
            '.nextra-nav',
            '.nextra-toc',
            '.nextra-breadcrumb',
            '.nx-',  # Nextra prefix
            '[class*="nextra"]',  # Any class containing nextra
            '[class*="sidebar"]',  # Any class containing sidebar
            '[class*="navigation"]',  # Any class containing navigation
            '[class*="menu"]',  # Any class containing menu
            # Common documentation framework elements
            '.docusaurus-',
            '.gitbook-',
            '.vuepress-',
            # Generic UI elements that are NOT frame elements
            '[aria-hidden="true"]:not([data-name="frame"])',  # Hidden decorative elements but not frames
            '.sr-only',  # Screen reader only elements
            '.visually-hidden',
        ]
        
        for selector in additional_selectors:
            for element in soup.select(selector):
                # Double-check: Protect frame elements that contain documentation images
                if element.get('data-name') == 'frame':
                    self.logger.debug(f"🛡️ Protecting frame element with data-name='frame'")
                    continue
                # Also protect elements that contain codebase-indexing images
                if element.find('img', src=lambda s: s and 'codebase-indexing' in s):
                    self.logger.info(f"🛡️ Protecting element containing codebase-indexing image")
                    continue
                element.decompose()
        
        # Remove specific unwanted elements
        unwanted_elements = [
            # Scripts and styles
            'script', 'style', 'noscript',
            # Forms and inputs
            'form', 'input', 'select', 'textarea',
            # Comments
            '<!--',
        ]
        
        for tag_name in unwanted_elements:
            if tag_name == '<!--':
                # Remove HTML comments
                for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                    comment.extract()
            else:
                for element in soup.find_all(tag_name):
                    element.decompose()
        
        # Remove buttons but protect those containing documentation images
        for button in soup.find_all('button'):
            # Protect buttons that contain codebase-indexing images or are in frame elements
            if (button.find('img', src=lambda s: s and 'codebase-indexing' in s) or
                button.find_parent(attrs={'data-name': 'frame'})):
                self.logger.info(f"🛡️ Protecting button containing documentation image")
                continue
            button.decompose()
        
        # Remove elements with specific attributes
        unwanted_attrs = [
            {'class': re.compile(r'.*ad.*|.*banner.*|.*promo.*', re.I)},
            {'id': re.compile(r'.*ad.*|.*banner.*|.*promo.*', re.I)},
            {'role': 'banner'},
            {'role': 'navigation'},
            {'role': 'complementary'},
        ]
        
        for attrs in unwanted_attrs:
            for element in soup.find_all(attrs=attrs):
                element.decompose()
        
        # Remove empty elements
        self._remove_empty_elements(soup)
        
        # Remove navigation text patterns
        self._remove_navigation_text(soup)
        
        return soup
    
    def extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract main content area from HTML.
        
        Args:
            soup: Cleaned BeautifulSoup object
            
        Returns:
            BeautifulSoup object with main content
        """
        # Special handling for installation page to preserve codebase-indexing.png
        if soup.find('img', src=lambda s: s and 'codebase-indexing.png' in s):
            self.logger.info("🔍 Found codebase-indexing.png - preserving entire content")
            # Create a copy of the soup to avoid modifying the original
            return soup
        
        # Try to find main content using selectors
        for selector in self.config.CONTENT_SELECTORS:
            main_element = soup.select_one(selector)
            if main_element:
                self.logger.debug(f"Found main content using selector: {selector}")
                # Create new soup with just the main content
                new_soup = BeautifulSoup('', 'html.parser')
                new_soup.append(main_element.extract())
                return new_soup
        
        # Fallback: try to find content by common patterns
        content_candidates = [
            # First check for frame elements (documentation images)
            soup.find('div', attrs={'data-name': 'frame'}),
            soup.find('div', class_='frame'),
            # Then check for standard content elements
            soup.find('div', class_=re.compile(r'.*content.*|.*main.*|.*article.*', re.I)),
            soup.find('section', class_=re.compile(r'.*content.*|.*main.*', re.I)),
            soup.find('div', id=re.compile(r'.*content.*|.*main.*', re.I)),
        ]
        
        for candidate in content_candidates:
            if candidate and self._has_substantial_content(candidate):
                self.logger.debug("Found main content using fallback pattern")
                new_soup = BeautifulSoup('', 'html.parser')
                new_soup.append(candidate.extract())
                return new_soup
        
        # Last resort: use body content
        body = soup.find('body')
        if body:
            self.logger.debug("Using body content as fallback")
            return soup
        
        # If all else fails, return the soup as-is
        self.logger.warning("Could not identify main content area")
        return soup
    
    def process_images(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Process images in the content.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup object with processed images
        """
        for img in soup.find_all('img'):
            try:
                # Get image source
                src = img.get('src', '')
                if not src:
                    img.decompose()
                    continue
                
                # Debug: Log all images being processed
                self.logger.debug(f"🔍 Processing image: {src} (alt: {img.get('alt', 'No alt')})")
                
                # Skip small icons and UI elements
                if self._is_ui_icon(img, src):
                    self.logger.debug(f"❌ Removing UI icon: {src} (alt: {img.get('alt', 'No alt')})")
                    img.decompose()
                    continue
                else:
                    self.logger.debug(f"✅ Keeping image: {src} (alt: {img.get('alt', 'No alt')})")
                
                # Debug: Log kept images
                if 'codebase-indexing' in src:
                    self.logger.info(f"🎯 KEEPING codebase-indexing image: {src} (alt: {img.get('alt', 'No alt')})")
                
                # Convert relative URLs to absolute
                if src.startswith('/'):
                    src = f"https://{self.config.domain}{src}"
                elif not src.startswith(('http://', 'https://')):
                    src = f"https://{self.config.domain}/{src.lstrip('/')}"
                
                # Update src attribute
                img['src'] = src
                
                # Add alt text if missing
                if not img.get('alt'):
                    img['alt'] = 'Documentation Image'
                
                # Add loading attribute for better performance
                img['loading'] = 'lazy'
                
                # Set reasonable max width and enhance documentation images
                if 'codebase-indexing' in src or 'screenshot' in src or img.get('alt', '').lower().find('indicator') >= 0:
                    # Special handling for documentation images
                    img['style'] = 'width: 80%; height: auto; margin: 20px auto; display: block; border: 1px solid #ccc;'
                    self.logger.info(f"🎯 Enhanced styling for documentation image: {src}")
                elif not img.get('style'):
                    img['style'] = 'max-width: 100%; height: auto;'
                
                self.logger.info(f"Keeping meaningful image: {src} (alt: {img.get('alt', 'No alt')})")
                
            except Exception as e:
                self.logger.warning(f"Error processing image {img.get('src', '')}: {e}")
                # Replace with placeholder text
                placeholder = soup.new_tag('p')
                placeholder.string = f"[Image: {img.get('alt', 'Unable to load')}]"
                img.replace_with(placeholder)
        
        return soup
    
    def _is_ui_icon(self, img: Tag, src: str) -> bool:
        """Check if image is a UI icon that should be removed.
        
        Args:
            img: Image element
            src: Image source URL
            
        Returns:
            True if image is a UI icon
        """
        # First check if this is clearly a documentation image
        if self._is_documentation_image(img, src):
            return False
        
        # Check image dimensions - only remove very small images
        width = img.get('width')
        height = img.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                if w <= 24 and h <= 24:  # Very small icons only
                    return True
            except (ValueError, TypeError):
                pass
        
        # Check CSS classes for icon indicators
        css_classes = img.get('class', [])
        if isinstance(css_classes, str):
            css_classes = css_classes.split()
        
        # Only remove if explicitly marked as icon
        explicit_icon_patterns = ['icon', 'favicon']
        for class_name in css_classes:
            if any(pattern in class_name.lower() for pattern in explicit_icon_patterns):
                return True
        
        # Check src URL for explicit icon patterns - be more specific about logos
        src_lower = src.lower()
        explicit_icon_url_patterns = [
            'favicon', '/icons/', 'icon.', 
            'app-logo.svg',  # Specific app logo pattern
            'data:image/svg+xml'  # Inline SVG icons
        ]
        
        for pattern in explicit_icon_url_patterns:
            if pattern in src_lower:
                return True
        
        # Check alt text for explicit icon indicators
        alt_text = img.get('alt', '').lower()
        if alt_text in ['icon', 'favicon']:
            return True
        
        return False
    
    def _is_documentation_image(self, img: Tag, src: str) -> bool:
        """Check if image is a documentation image that should be kept.
        
        Args:
            img: Image element
            src: Image source URL
            
        Returns:
            True if image is documentation content
        """
        # Priority check: codebase-indexing images are always documentation
        if 'codebase-indexing' in src.lower():
            self.logger.info(f"🎯 Identified codebase-indexing as documentation image: {src}")
            return True
        
        # Check if image is within a frame element (high priority)
        if img.find_parent(attrs={'data-name': 'frame'}):
            self.logger.info(f"🎯 Image in frame element - treating as documentation: {src}")
            return True
        
        # Check for meaningful alt text
        alt_text = img.get('alt', '').strip()
        if alt_text and len(alt_text) > 10:  # Meaningful description
            self.logger.info(f"🎯 Image with meaningful alt text - treating as documentation: {src} (alt: {alt_text})")
            return True
        
        # Check for documentation image URLs (but exclude specific logos)
        src_lower = src.lower()
        
        # Exclude specific logo patterns only
        if 'app-logo.svg' in src_lower:
            return False
        
        doc_image_patterns = [
            'mintlify.s3',  # Mintlify documentation images
            '/images/',
            '/screenshots/',
            '/docs/',
            '/assets/',
            'documentation',
            'tutorial',
            'guide',
            'example',
            'get-started'  # Add get-started pattern for installation images
        ]
        
        for pattern in doc_image_patterns:
            if pattern in src_lower:
                self.logger.info(f"🎯 Image matches documentation pattern '{pattern}': {src}")
                return True
        
        # Check image size - documentation images are usually larger
        width = img.get('width')
        height = img.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                if w > 100 or h > 100:  # Larger images are likely content
                    return True
            except (ValueError, TypeError):
                pass
        
        # Check parent context for content areas
        parent = img.parent
        while parent and parent.name != 'body':
            parent_classes = parent.get('class', [])
            if isinstance(parent_classes, str):
                parent_classes = parent_classes.split()
            
            content_patterns = ['content', 'article', 'main', 'documentation', 'frame']
            for class_name in parent_classes:
                if any(pattern in class_name.lower() for pattern in content_patterns):
                    return True
            
            parent = parent.parent
        
        return False
    
    def process_youtube_links(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Process YouTube videos and convert to links.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            BeautifulSoup object with YouTube videos converted to links
        """
        # Process iframe embeds
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if any(pattern in src for pattern in ['youtube.com', 'youtu.be']):
                # Extract video ID and create link
                video_link = self._create_youtube_link(src, soup)
                if video_link:
                    iframe.replace_with(video_link)
        
        # Process direct YouTube links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(pattern in href for pattern in ['youtube.com', 'youtu.be']):
                # Enhance the link text
                if not link.get_text().strip():
                    link.string = f"YouTube Video: {href}"
                else:
                    link.string = f"🎥 {link.get_text().strip()}"
        
        return soup
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Clean text content
        """
        # Get text and clean it up
        text = soup.get_text(separator=' ', strip=True)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _extract_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of image URLs
        """
        image_urls = []
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and src not in image_urls:
                image_urls.append(src)
        
        return image_urls
    
    def _has_substantial_content(self, element: Tag) -> bool:
        """Check if element has substantial content.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            True if element has substantial content
        """
        if not element:
            return False
        
        text = element.get_text(strip=True)
        
        # Check text length
        if len(text) < 100:
            return False
        
        # Check for content indicators
        content_indicators = ['h1', 'h2', 'h3', 'p', 'article', 'section']
        has_structure = any(element.find(tag) for tag in content_indicators)
        
        return has_structure
    
    def _remove_empty_elements(self, soup: BeautifulSoup) -> None:
        """Remove empty elements from soup.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Elements that should be removed if empty
        removable_if_empty = ['p', 'div', 'span', 'section', 'article', 'aside']
        
        for tag_name in removable_if_empty:
            for element in soup.find_all(tag_name):
                if not element.get_text(strip=True) and not element.find_all(['img', 'video', 'audio', 'iframe']):
                    element.decompose()
    
    def _create_youtube_link(self, src: str, soup: BeautifulSoup) -> Optional[Tag]:
        """Create a YouTube link from iframe src.
        
        Args:
            src: iframe src URL
            soup: BeautifulSoup object for creating new elements
            
        Returns:
            New link element or None
        """
        try:
            # Extract video ID from various YouTube URL formats
            video_id = None
            
            if 'youtube.com/embed/' in src:
                video_id = src.split('youtube.com/embed/')[-1].split('?')[0]
            elif 'youtube.com/watch?v=' in src:
                video_id = src.split('v=')[-1].split('&')[0]
            elif 'youtu.be/' in src:
                video_id = src.split('youtu.be/')[-1].split('?')[0]
            
            if video_id:
                # Create link element
                link = soup.new_tag('a', href=f"https://www.youtube.com/watch?v={video_id}")
                link.string = f"🎥 YouTube Video: https://www.youtube.com/watch?v={video_id}"
                
                # Wrap in paragraph for better formatting
                paragraph = soup.new_tag('p')
                paragraph.append(link)
                
                return paragraph
        
        except Exception as e:
            self.logger.warning(f"Error creating YouTube link from {src}: {e}")
        
        return None    
    
    def _remove_navigation_text(self, soup: BeautifulSoup) -> None:
        """Remove navigation text patterns that commonly appear in sidebars.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Common navigation text patterns to remove
        nav_text_patterns = [
            'Get started', 'Getting Started', 'get started',
            'Changelog', 'changelog', 'CHANGELOG',
            'Concepts', 'concepts', 'CONCEPTS',
            'Models', 'models', 'MODELS',
            'Cursor Documentation', 'Documentation',
            'Guides', 'guides', 'GUIDES',
            'Downloads', 'downloads', 'DOWNLOADS',
            'Tools', 'tools', 'TOOLS',
            'Forum', 'forum', 'FORUM',
            'Support', 'support', 'SUPPORT',
            'API Reference', 'Reference', 'API',
            'Quick Start', 'Quickstart', 'quickstart',
            'Installation', 'Install',
            'Configuration', 'Config',
            'Troubleshooting', 'FAQ',
            'Examples', 'Tutorials',
            'Community', 'Blog',
            'About', 'Contact',
            'Privacy', 'Terms',
            'Search', 'Menu', 'Navigation'
        ]
        
        # Remove elements that contain only navigation text
        for element in soup.find_all(['div', 'span', 'p', 'li', 'a']):
            text = element.get_text(strip=True)
            
            # Skip if element has substantial content (more than just nav text)
            if len(text) > 100:
                continue
            
            # Check if text matches navigation patterns
            if text in nav_text_patterns:
                self.logger.debug(f"Removing navigation text: {text}")
                element.decompose()
                continue
            
            # Check for navigation text that appears as standalone items
            words = text.split()
            if len(words) <= 3 and any(word in nav_text_patterns for word in words):
                self.logger.debug(f"Removing short navigation text: {text}")
                element.decompose()
                continue
        
        # Remove elements that contain multiple navigation items (like menu lists)
        for element in soup.find_all(['ul', 'ol', 'nav']):
            text = element.get_text(strip=True)
            nav_matches = sum(1 for pattern in nav_text_patterns if pattern.lower() in text.lower())
            
            # If more than 3 navigation patterns are found, likely a navigation menu
            if nav_matches >= 3 and len(text) < 500:  # Not too long to avoid removing real content
                self.logger.debug(f"Removing navigation menu with {nav_matches} nav items")
                element.decompose()