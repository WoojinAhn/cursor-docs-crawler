"""Tests for CLI options and Config validation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, resolve_language
from src.pdf_generator import PDFGenerator
from src.models import PageContent


# --- Config defaults ---


def test_config_defaults():
    """Config() 기본값이 기대한 값과 일치한다."""
    config = Config()
    assert config.BASE_URL == "https://cursor.com/docs"
    assert config.OUTPUT_FILE == "cursor_docs.pdf"
    assert config.LANGUAGE == "en"
    assert config.DELAY_BETWEEN_REQUESTS == 0.3
    assert config.MAX_PAGES is None
    assert config.ALLOWED_PATH_PREFIXES == ["/docs/"]
    assert config.LLMS_TXT_URL == "https://cursor.com/llms.txt"


def test_config_supported_languages():
    """SUPPORTED_LANGUAGES는 영어만 포함한다."""
    config = Config()
    assert config.SUPPORTED_LANGUAGES == ("en",)


# --- Config validation ---


def test_config_invalid_base_url():
    """BASE_URL이 빈 문자열이면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="BASE_URL"):
        Config(BASE_URL="")


def test_config_invalid_max_pages():
    """MAX_PAGES가 음수이면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="MAX_PAGES"):
        Config(MAX_PAGES=-1)


def test_config_invalid_delay():
    """DELAY_BETWEEN_REQUESTS가 음수이면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="DELAY_BETWEEN_REQUESTS"):
        Config(DELAY_BETWEEN_REQUESTS=-1)


def test_config_invalid_output():
    """OUTPUT_FILE이 빈 문자열이면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="OUTPUT_FILE"):
        Config(OUTPUT_FILE="")


def test_config_invalid_output_ext():
    """OUTPUT_FILE이 .pdf 확장자가 아니면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="OUTPUT_FILE"):
        Config(OUTPUT_FILE="out.txt")


# --- --lang validation (main.py logic) ---


def test_lang_supported_value():
    """지원되는 언어 코드는 그대로 반환된다."""
    assert resolve_language("en") == "en"


def test_lang_unsupported_fallback_to_en():
    """지원되지 않는 언어 코드는 'en'으로 fallback된다."""
    assert resolve_language("ko") == "en"
    assert resolve_language("ja") == "en"
    assert resolve_language("xx") == "en"


def test_lang_default_is_en():
    """--lang 미지정 시 기본값은 'en'이다."""
    import main

    source = Path(main.__file__).read_text(encoding="utf-8")
    assert 'default="en"' in source
    assert resolve_language("en") == "en"


# --- PDF lang attribute ---


def test_pdf_html_lang_en():
    """기본 LANGUAGE가 'en'일 때 생성된 HTML에 <html lang="en">가 포함된다."""
    config = Config()
    pdf_gen = PDFGenerator(config)

    page = PageContent(
        url="https://cursor.com/docs/test",
        title="Test",
        content_html="<p>Hello</p>",
        text_content="Hello",
    )
    html = pdf_gen._create_html_document([page])
    assert '<html lang="en">' in html
    assert '<html lang="ko">' not in html
