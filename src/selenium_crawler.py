import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .models import PageData

class SeleniumCrawler:
    def __init__(self, config, url_manager):
        self.config = config
        self.url_manager = url_manager
        self.logger = logging.getLogger(__name__)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def crawl_page(self, url: str):
        self.logger.info(f"[Selenium] Crawling: {url}")
        print(f"[Selenium] Crawling: {url}")
        try:
            self.driver.get(url)
            time.sleep(self.config.DELAY_BETWEEN_REQUESTS)  # JS 렌더링 대기
            
            # 리다이렉트 추적: 실제 최종 URL 확인
            final_url = self.driver.current_url
            if final_url != url:
                self.logger.info(f"[Selenium] Redirect detected: {url} -> {final_url}")
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string if soup.title and soup.title.string else ""
            # 링크 추출 (정규화된 URL로)
            links = self.extract_links(soup, url)
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
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        from urllib.parse import urljoin
        
        links = []
        
        # Find all anchor tags with href
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            if not href:
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Check if we should crawl this URL
            if self.url_manager.should_crawl(absolute_url):
                links.append(absolute_url)
        
        self.logger.debug(f"[Selenium] Extracted {len(links)} valid links from {base_url}")
        return links

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