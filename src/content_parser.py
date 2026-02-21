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
            
            # Extract main content (must happen before class stripping)
            main_content = self.extract_main_content(cleaned_soup)

            # Now safe to strip Tailwind classes and CSS custom properties
            self._clean_styles_for_pdf(main_content)

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
            except Exception:
                # Ultimate fallback
                return PageContent(
                    url=page_data.url,
                    title=page_data.title or "Error Page",
                    content_html=f"<p>Error parsing content: {str(e)}</p>",
                    text_content=f"Error parsing content: {str(e)}",
                    images=[]
                )
    
    def _should_protect(self, element: Tag, content_el: Optional[Tag] = None) -> bool:
        """Check if element should be protected from removal.

        Centralised guard so every removal strategy uses the same rules.
        """
        if element.name in ('html', 'body'):
            return True
        if content_el and (element is content_el
                          or content_el in element.parents
                          or element in content_el.parents):
            return True
        if element.get('data-name') == 'frame':
            return True
        if element.find('img', src=lambda s: s and 'codebase-indexing' in s):
            return True
        if element.find_parent(attrs={'data-name': 'frame'}):
            return True
        return False

    # ------------------------------------------------------------------
    # remove_unwanted_elements – delegates to focused helpers
    # ------------------------------------------------------------------

    _ADDITIONAL_SELECTORS = [
        '.sidebar', '.navigation', '.nav-menu',
        '.header-nav', '.footer-nav', '.breadcrumb',
        '.pagination', '.search-box', '.search-form',
        '[role="navigation"]', '[role="banner"]', '[role="complementary"]',
        '[aria-label*="navigation"]', '[aria-label*="menu"]',
        '.docs-sidebar', '.docs-nav', '.table-of-contents',
        '.sr-only', '.visually-hidden',
    ]

    # Word-boundary patterns to avoid false positives on Tailwind classes
    # (e.g. "leading-relaxed" contains "ad" but is NOT ad-related).
    _AD_PATTERN = re.compile(
        r'\bad(?:s|vert(?:isement|ising)?)?\b|\bbanner\b|\bpromo(?:tion)?\b', re.I,
    )

    _UNWANTED_ATTRS = [
        {'class': _AD_PATTERN},
        {'id': _AD_PATTERN},
        {'role': 'banner'},
        {'role': 'navigation'},
        {'role': 'complementary'},
    ]

    def remove_unwanted_elements(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove unwanted UI elements from HTML."""
        content_el = self._find_content_element(soup)
        self._remove_by_selectors(soup, content_el)
        self._remove_by_tags(soup, content_el)
        self._remove_by_attrs(soup, content_el)
        # NOTE: _clean_styles_for_pdf is called AFTER extract_main_content
        # in parse_page, because it strips class attrs needed by CSS selectors.
        self._remove_empty_table_columns(soup)
        self._remove_empty_elements(soup)
        self._remove_navigation_text(soup, content_el)
        return soup

    def _find_content_element(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main content element to protect during cleanup."""
        for sel in self.config.CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                return el
        return None

    def _remove_by_selectors(self, soup: BeautifulSoup, content_el: Optional[Tag]) -> None:
        """Remove elements matched by CSS selectors."""
        for selector in self.config.EXCLUDED_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        for selector in self._ADDITIONAL_SELECTORS:
            for element in soup.select(selector):
                if self._should_protect(element, content_el):
                    continue
                element.decompose()

    def _remove_by_tags(self, soup: BeautifulSoup, content_el: Optional[Tag]) -> None:
        """Remove unwanted tags (scripts, styles, forms, buttons)."""
        for tag_name in ('script', 'style', 'noscript', 'form', 'input',
                         'select', 'textarea', 'svg'):
            for element in soup.find_all(tag_name):
                element.decompose()

        # HTML comments
        for comment in soup.find_all(
            string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')
        ):
            comment.extract()

        # UI aria-labels that should NOT become visible text
        _ui_labels = {'open image in full screen', 'copy code', 'copy',
                      'close', 'toggle', 'menu', 'expand', 'collapse',
                      'additional model information'}

        # Buttons: unwrap to keep text; convert data aria-labels to text
        for button in soup.find_all('button'):
            if not button.get_text(strip=True) and button.get('aria-label'):
                label = button['aria-label'].strip()
                if label.lower() in _ui_labels:
                    # Rescue <img> elements before destroying the button
                    for img in button.find_all('img'):
                        button.insert_before(img.extract())
                    button.decompose()
                    continue
                span = soup.new_tag('span')
                span.string = label
                # Add line break before span if inside a table cell with siblings
                if button.find_parent(['td', 'th']):
                    prev_el = button.find_previous_sibling()
                    if prev_el is not None:
                        button.insert_before(soup.new_tag('br'))
                button.replace_with(span)
            else:
                button.unwrap()

    _CSS_VAR_RE = re.compile(r'[^;]*var\(--[^)]+\)[^;]*;?')
    _CSS_PROP_RE = re.compile(r'--[\w-]+:[^;]+;?')

    def _clean_styles_for_pdf(self, soup: BeautifulSoup) -> None:
        """Strip Tailwind CSS classes and CSS custom properties for PDF."""
        for el in soup.find_all(True):
            # Remove all class attributes – PDF uses its own CSS
            if el.get('class'):
                del el['class']

            # Clean inline styles: remove CSS custom properties and var() refs
            style = el.get('style', '')
            if style and ('--' in style or 'var(' in style):
                style = self._CSS_VAR_RE.sub('', style)
                style = self._CSS_PROP_RE.sub('', style)
                style = style.strip().strip(';').strip()
                if style:
                    el['style'] = style
                else:
                    del el['style']

    def _remove_empty_table_columns(self, soup: BeautifulSoup) -> None:
        """Remove table columns where all body cells are empty."""
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if not rows:
                continue
            # Separate header rows from body rows
            body_rows = [r for r in rows
                         if r.find('td') and r.find_parent('thead') is None]
            if not body_rows:
                continue
            num_cols = max(len(row.find_all(['th', 'td'])) for row in rows)
            for col_idx in range(num_cols - 1, -1, -1):
                # Check only body rows – header text alone doesn't justify a column
                all_body_empty = True
                for row in body_rows:
                    cells = row.find_all(['th', 'td'])
                    if col_idx < len(cells):
                        if cells[col_idx].get_text(strip=True):
                            all_body_empty = False
                            break
                if all_body_empty:
                    for row in rows:
                        cells = row.find_all(['th', 'td'])
                        if col_idx < len(cells):
                            cells[col_idx].decompose()

    def _remove_by_attrs(self, soup: BeautifulSoup, content_el: Optional[Tag]) -> None:
        """Remove elements matched by attribute patterns (ads, banners, roles)."""
        for attrs in self._UNWANTED_ATTRS:
            for element in soup.find_all(attrs=attrs):
                if element.name in ('html', 'body'):
                    continue
                # Protect content area and its ancestors (O(depth) check)
                if content_el and (element is content_el
                                   or content_el in element.parents
                                   or element in content_el.parents):
                    continue
                element.decompose()
    
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
            else:
                self.logger.debug(f"Selector '{selector}' not found")
        
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
        """Process images in the content."""
        seen_srcs = set()

        for img in soup.find_all('img'):
            try:
                src = img.get('src', '')
                if not src:
                    img.decompose()
                    continue

                # Remove UI icons
                if self._is_ui_icon(img, src):
                    self.logger.debug(f"Removing UI icon: {src}")
                    img.decompose()
                    continue

                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = f"https:{src}"
                elif src.startswith('/'):
                    src = f"https://{self.config.domain}{src}"
                elif not src.startswith(('http://', 'https://')):
                    src = f"https://{self.config.domain}/{src.lstrip('/')}"
                img['src'] = src

                # Deduplicate dark/light theme variants
                dedup_key = (src.replace('-dark.', '-light.')
                                .replace('-dark@', '-light@'))
                if dedup_key in seen_srcs:
                    img.decompose()
                    continue
                seen_srcs.add(dedup_key)

                # Add alt text if missing
                if not img.get('alt'):
                    img['alt'] = 'Documentation Image'

                # Replace site-specific styles with PDF-appropriate styling
                img['style'] = 'max-width: 100%; height: auto;'
                img['loading'] = 'lazy'

                self.logger.debug(f"Keeping image: {src}")

            except Exception as e:
                self.logger.warning(f"Error processing image {img.get('src', '')}: {e}")
                placeholder = soup.new_tag('p')
                placeholder.string = f"[Image: {img.get('alt', 'Unable to load')}]"
                img.replace_with(placeholder)

        return soup
    
    def _is_ui_icon(self, img: Tag, src: str) -> bool:
        """Check if image is a UI icon that should be removed."""
        # Dimension check FIRST – small images are icons regardless of path
        width = img.get('width')
        height = img.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                if w <= 32 and h <= 32:
                    return True
            except (ValueError, TypeError):
                pass

        # Then check if this is a documentation image
        if self._is_documentation_image(img, src):
            return False

        src_lower = src.lower()

        # SVG files without large dimensions are likely icons
        if src_lower.endswith('.svg'):
            return True

        # Explicit icon URL patterns
        icon_url_patterns = [
            'favicon', '/icons/', 'icon.',
            'app-logo.svg', 'data:image/svg+xml',
            '/providers/', '/logos/',
        ]
        if any(p in src_lower for p in icon_url_patterns):
            return True

        # CSS class check
        css_classes = img.get('class', [])
        if isinstance(css_classes, str):
            css_classes = css_classes.split()
        if any('icon' in c.lower() or 'favicon' in c.lower() for c in css_classes):
            return True

        # Alt text check
        alt_text = img.get('alt', '').lower()
        if alt_text in ['icon', 'favicon']:
            return True

        return False
    
    def _is_documentation_image(self, img: Tag, src: str) -> bool:
        """Check if image is a documentation image that should be kept."""
        src_lower = src.lower()

        # Priority: codebase-indexing images are always documentation
        if 'codebase-indexing' in src_lower:
            return True

        # Frame elements contain documentation images
        if img.find_parent(attrs={'data-name': 'frame'}):
            return True

        # Exclude known icon/logo paths early
        icon_paths = ['/providers/', '/logos/', '/icons/', 'app-logo']
        if any(p in src_lower for p in icon_paths):
            return False

        # Large dimensions → documentation
        width = img.get('width')
        height = img.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                if w > 100 or h > 100:
                    return True
            except (ValueError, TypeError):
                pass

        # Raster image in a doc-like path → documentation
        doc_path_patterns = [
            '/screenshots/', '/images/', '/docs/',
            '/assets/', 'mintlify.s3', 'get-started',
        ]
        is_raster = any(src_lower.endswith(ext) for ext in
                        ('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        if is_raster and any(p in src_lower for p in doc_path_patterns):
            return True

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
    
    def _remove_navigation_text(self, soup: BeautifulSoup,
                                content_el: Optional[Tag] = None) -> None:
        """Remove navigation text patterns that commonly appear in sidebars.

        Args:
            soup: BeautifulSoup object to clean
            content_el: Main content element to protect
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

            # Protect elements inside the main content area
            if content_el and (element is content_el
                               or content_el in element.parents):
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