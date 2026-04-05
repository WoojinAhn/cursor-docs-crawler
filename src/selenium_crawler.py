import re
import time
import logging
from urllib.parse import urljoin, urlparse

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .models import PageData

# Locale prefixes that Cursor auto-inserts (e.g. /ko/, /en/, /ja/)
_LOCALE_RE = re.compile(r'^/[a-z]{2}(?=/)')


class SeleniumCrawler:
    def __init__(self, config, url_manager):
        self.config = config
        self.url_manager = url_manager
        self.logger = logging.getLogger(__name__)
        self.driver = Driver(uc=True, headless=True, locale_code=config.LANGUAGE)

    @staticmethod
    def strip_locale(url: str) -> str:
        """Remove locale prefix from URL path (e.g. /ko/docs/... -> /docs/...).

        cursor.com auto-redirects to a locale-prefixed URL based on browser
        language. We strip it so all URLs are stored in a canonical form.
        """
        parsed = urlparse(url)
        new_path = _LOCALE_RE.sub('', parsed.path)
        if new_path == parsed.path:
            return url
        return parsed._replace(path=new_path).geturl()

    def crawl_page(self, url: str):
        self.logger.info(f"[Selenium] Crawling: {url}")
        print(f"[Selenium] Crawling: {url}")
        try:
            self.driver.uc_open_with_reconnect(url, reconnect_time=4)

            # Wait for JS rendering (Next.js SPA needs time to hydrate)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href]"))
                )
            except Exception:
                self.logger.debug(f"[Selenium] Timed out waiting for links on {url}")

            # Track redirect: check actual final URL
            raw_final_url = self.driver.current_url
            final_url = self.strip_locale(raw_final_url)
            if final_url != url:
                self.logger.info(f"[Selenium] Redirect detected: {url} -> {final_url}")

            title = self.driver.title or ""
            self._inline_images_as_base64()
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            links = self.extract_links(soup, final_url)
            return PageData(
                url=url,
                title=title,
                html_content=html,
                status_code=200,
                links=links,
                final_url=final_url
            )
        except Exception as e:
            self.logger.error(f"[Selenium] Error crawling {url}: {e}")
            return None

    def extract_links(self, soup: BeautifulSoup, base_url: str):
        """Extract and normalize links from HTML content.

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links (should be the
                      final URL after any redirects)

        Returns:
            List of absolute URLs
        """
        links = []

        for link in soup.find_all('a', href=True):
            href = link['href'].strip()

            if not href or href.startswith(('#', 'mailto:', 'javascript:')):
                continue

            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)

            # Strip locale prefix for canonical form
            absolute_url = self.strip_locale(absolute_url)

            # Check if we should crawl this URL
            if self.url_manager.should_crawl(absolute_url):
                links.append(absolute_url)

        self.logger.debug(f"[Selenium] Extracted {len(links)} valid links from {base_url}")
        return links

    def _inline_images_as_base64(self):
        """Convert all <img src="http..."> to base64 data URIs via browser fetch.

        Uses the browser's authenticated session so Vercel bot protection
        doesn't block image requests.
        """
        try:
            result = self.driver.execute_async_script('''
                const callback = arguments[arguments.length - 1];
                const imgs = document.querySelectorAll('img[src]:not([src^="data:"])');
                let converted = 0;
                if (imgs.length === 0) { callback(0); return; }

                async function run() {
                    for (const img of imgs) {
                        try {
                            const resp = await fetch(img.src);
                            if (!resp.ok) continue;
                            const blob = await resp.blob();
                            const dataUri = await new Promise(resolve => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                            img.src = dataUri;
                            converted++;
                        } catch(e) {}
                    }
                    return converted;
                }
                run().then(callback);
            ''')
            if result:
                self.logger.debug(f"[Selenium] Inlined {result} images as base64")
        except Exception as e:
            self.logger.warning(f"[Selenium] Image inlining failed: {e}")

    def crawl_all(self):
        self.logger.info("[Selenium] Starting crawl process")
        crawled_pages = []
        while self.url_manager.has_urls():
            if self.config.MAX_PAGES and len(crawled_pages) >= self.config.MAX_PAGES:
                self.logger.info(f"[Selenium] Reached page limit: {self.config.MAX_PAGES}")
                break
            url = self.url_manager.get_next_url()
            if not url:
                break
            if crawled_pages:
                time.sleep(self.config.DELAY_BETWEEN_REQUESTS)
            page_data = self.crawl_page(url)
            if page_data and page_data.is_valid():
                crawled_pages.append(page_data)
                # Mark both original and final URL as visited
                self.url_manager.mark_visited(url)
                if page_data.final_url and page_data.final_url != url:
                    self.url_manager.mark_visited(page_data.final_url)
                for link in page_data.links:
                    self.url_manager.add_url(link)
        return crawled_pages

    def close(self):
        self.driver.quit()
