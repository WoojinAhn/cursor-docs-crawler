import re

import pytest
from src.config import Config, TestConfig
from src.pdf_generator import PDFGenerator
from src.models import PageContent


class TestScopeConfig:
    def test_default_scope_is_docs(self):
        config = Config()
        assert config.SCOPE == "docs"

    def test_docs_scope_prefixes(self):
        config = Config()
        config.SCOPE = "docs"
        assert config.scope_prefixes == ["/docs/"]

    def test_help_scope_prefixes(self):
        config = Config()
        config.SCOPE = "help"
        assert config.scope_prefixes == ["/help/"]

    def test_docs_scope_seed_regex(self):
        config = Config()
        config.SCOPE = "docs"
        assert "/docs" in config.scope_seed_regex

    def test_help_scope_seed_regex(self):
        config = Config()
        config.SCOPE = "help"
        assert "/help" in config.scope_seed_regex

    def test_docs_scope_output_file(self):
        config = Config()
        config.SCOPE = "docs"
        assert config.scope_output_file == "cursor_docs.pdf"

    def test_help_scope_output_file(self):
        config = Config()
        config.SCOPE = "help"
        assert config.scope_output_file == "cursor_help.pdf"

    def test_docs_scope_base_url(self):
        config = Config()
        config.SCOPE = "docs"
        assert config.scope_base_url == "https://cursor.com/docs"

    def test_help_scope_base_url(self):
        config = Config()
        config.SCOPE = "help"
        assert config.scope_base_url == "https://cursor.com/help"

    def test_invalid_scope_raises(self):
        config = Config()
        config.SCOPE = "invalid"
        with pytest.raises(ValueError):
            _ = config.scope_prefixes


SAMPLE_LLMS_TXT = """
# Cursor Docs
- [Docs](https://cursor.com/docs.md)
- [Agent](https://cursor.com/docs/agent/overview.md)
- [Rules](https://cursor.com/docs/rules.md)
# Help
- [Install](https://cursor.com/help/getting-started/install.md)
- [Agent Issues](https://cursor.com/help/troubleshooting/agent-issues.md)
# Other
- [Changelog](https://cursor.com/changelog.md)
"""


class TestSeedRegex:
    def test_docs_regex_matches_only_docs(self):
        config = Config()
        config.SCOPE = "docs"
        matches = re.findall(config.scope_seed_regex, SAMPLE_LLMS_TXT)
        urls = [u.removesuffix(".md") for u in matches]
        assert "https://cursor.com/docs" in urls
        assert "https://cursor.com/docs/agent/overview" in urls
        assert all("/help/" not in u for u in urls)

    def test_help_regex_matches_only_help(self):
        config = Config()
        config.SCOPE = "help"
        matches = re.findall(config.scope_seed_regex, SAMPLE_LLMS_TXT)
        urls = [u.removesuffix(".md") for u in matches]
        assert "https://cursor.com/help/getting-started/install" in urls
        assert all("/docs/" not in u for u in urls)


class TestHelpTestConfig:
    def test_help_scope_test_urls(self):
        config = TestConfig()
        config.SCOPE = "help"
        urls = config.active_test_urls
        assert len(urls) == 10
        assert all("cursor.com/help/" in u for u in urls)

    def test_docs_scope_test_urls_unchanged(self):
        config = TestConfig()
        config.SCOPE = "docs"
        urls = config.active_test_urls
        assert len(urls) == 10
        assert all("cursor.com/docs" in u for u in urls)

    def test_stale_urls_fixed(self):
        config = TestConfig()
        # These old URLs should no longer be in the defaults
        for url in config.TEST_URLS:
            assert "get-started/concepts" not in url
            assert url != "https://cursor.com/docs/models"
            assert "context/rules" not in url


class TestPDFScopeTitle:
    def test_docs_scope_title(self):
        config = Config()
        config.SCOPE = "docs"
        gen = PDFGenerator(config)
        pages = [PageContent(
            url="https://cursor.com/docs/test",
            title="Test",
            content_html="<p>test</p>",
            text_content="test",
        )]
        html = gen._create_html_document(pages)
        assert "Cursor Documentation" in html
        assert "Technical Reference" in html

    def test_help_scope_title(self):
        config = Config()
        config.SCOPE = "help"
        gen = PDFGenerator(config)
        pages = [PageContent(
            url="https://cursor.com/help/test",
            title="Test",
            content_html="<p>test</p>",
            text_content="test",
        )]
        html = gen._create_html_document(pages)
        assert "Cursor Help Center" in html
        assert "User Guide" in html
