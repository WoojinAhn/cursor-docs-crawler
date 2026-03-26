import pytest
from src.config import Config


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
