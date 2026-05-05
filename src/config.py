"""Configuration settings for the Cursor documentation crawler."""

from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import os


@dataclass
class Config:
    """Main configuration class for the crawler."""

    _SCOPE_MAP = {
        "docs": {
            "prefixes": ["/docs/"],
            "seed_regex": r'https://cursor\.com/docs[^\s)]*\.md',
            "output_file": "cursor_docs.pdf",
            "base_url": "https://cursor.com/docs",
        },
        "help": {
            "prefixes": ["/help/"],
            "seed_regex": r'https://cursor\.com/help[^\s)]*\.md',
            "output_file": "cursor_help.pdf",
            "base_url": "https://cursor.com/help",
        },
    }

    # Scope selection
    SCOPE: str = "docs"

    # Basic settings
    BASE_URL: str = "https://cursor.com/docs"
    OUTPUT_FILE: str = "cursor_docs.pdf"
    USER_AGENT: str = "Cursor Docs Crawler 1.0"

    # Allowed path prefixes for crawling (URLs must start with one of these)
    ALLOWED_PATH_PREFIXES: List[str] = None

    # Seed URL source: llms.txt lists all official doc pages
    LLMS_TXT_URL: str = "https://cursor.com/llms.txt"

    # Language for crawling and PDF output (e.g., "ko", "en", "ja")
    SUPPORTED_LANGUAGES: tuple = (
        "en", "ko", "ja", "zh", "zh-TW", "es", "fr", "pt", "ru", "tr", "id", "de",
    )
    LANGUAGE: str = "ko"

    # Crawling settings
    MAX_PAGES: Optional[int] = None  # None for unlimited, number for test mode
    DELAY_BETWEEN_REQUESTS: float = 0.3
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
                ".prose.prose-lg",  # cursor.com/docs (current)
                ".mdx-content",     # legacy (docs.cursor.com)
                "main", ".content", "article", ".documentation",
                ".main-content", "#content"
            ]

        if self.ALLOWED_PATH_PREFIXES is None:
            self.ALLOWED_PATH_PREFIXES = ["/docs/"]

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

    def _get_scope_settings(self) -> dict:
        """Get settings for the current scope, raising ValueError if invalid."""
        if self.SCOPE not in self._SCOPE_MAP:
            raise ValueError(
                f"Unknown scope '{self.SCOPE}'. "
                f"Valid scopes: {list(self._SCOPE_MAP.keys())}"
            )
        return self._SCOPE_MAP[self.SCOPE]

    @property
    def scope_prefixes(self) -> List[str]:
        """Get URL path prefixes for the current scope."""
        return self._get_scope_settings()["prefixes"]

    @property
    def scope_seed_regex(self) -> str:
        """Get seed URL regex pattern for the current scope."""
        return self._get_scope_settings()["seed_regex"]

    @property
    def scope_output_file(self) -> str:
        """Get default output filename for the current scope."""
        return self._get_scope_settings()["output_file"]

    @property
    def scope_base_url(self) -> str:
        """Get base URL for the current scope."""
        return self._get_scope_settings()["base_url"]

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

    MAX_PAGES: int = 10
    TEST_URLS: List[str] = None
    HELP_TEST_URLS: List[str] = None

    def __post_init__(self):
        super().__post_init__()
        self._set_default_test_urls()
        self._set_default_help_test_urls()
        self._validate_test_config()

    def _set_default_test_urls(self):
        """Set default test URLs.

        Pages are chosen to cover distinct content types:
        text, tables, images, code blocks, and mixed layouts.
        """
        if self.TEST_URLS is None:
            self.TEST_URLS = [
                "https://cursor.com/docs",                          # root/index
                "https://cursor.com/docs/models-and-pricing",       # table (was /models → redirect)
                "https://cursor.com/docs/account/teams/pricing",    # table (was /account/pricing → moved)
                "https://cursor.com/docs/agent/overview",            # images (screenshots)
                "https://cursor.com/docs/tab/overview",              # images (dark/light)
                "https://cursor.com/docs/cli/overview",              # code blocks
                "https://cursor.com/docs/api",                       # code + JSON
                "https://cursor.com/docs/agent/security",            # mixed (table+code+text)
                "https://cursor.com/docs/rules",                     # mixed (was /context/rules → moved)
                "https://cursor.com/docs/enterprise",                # new enterprise page
            ]

    def _set_default_help_test_urls(self):
        """Set default test URLs for help scope."""
        if self.HELP_TEST_URLS is None:
            self.HELP_TEST_URLS = [
                "https://cursor.com/help/getting-started/install",
                "https://cursor.com/help/ai-features/agent",
                "https://cursor.com/help/ai-features/tab",
                "https://cursor.com/help/customization/rules",
                "https://cursor.com/help/customization/mcp",
                "https://cursor.com/help/models-and-usage/available-models",
                "https://cursor.com/help/account-and-billing/pricing",
                "https://cursor.com/help/security-and-privacy/privacy",
                "https://cursor.com/help/troubleshooting/agent-issues",
                "https://cursor.com/help/integrations/git",
            ]

    @property
    def active_test_urls(self) -> List[str]:
        """Return test URLs appropriate for the current scope."""
        if self.SCOPE == "help":
            return self.HELP_TEST_URLS
        return self.TEST_URLS

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
