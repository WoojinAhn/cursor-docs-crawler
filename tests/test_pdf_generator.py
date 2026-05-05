import os
import tempfile
from src.config import Config
from src.pdf_generator import PDFGenerator
from src.models import PageContent


def test_generate_pdf_success():
    pdf_gen = PDFGenerator(Config())
    page = PageContent(url="https://test.com", title="Test", content_html="<h1>Test</h1>", text_content="Test")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        path = tmp.name
    try:
        assert pdf_gen.generate_pdf([page], path)
        assert os.path.exists(path)
    finally:
        os.unlink(path)


def test_deduplicate_pages():
    pdf_gen = PDFGenerator(Config())
    page1 = PageContent(url="https://test.com", title="A", content_html="", text_content="")
    page2 = PageContent(url="https://test.com", title="A", content_html="", text_content="")
    deduped = pdf_gen._deduplicate_pages([page1, page2])
    assert len(deduped) == 1


def test_generate_pdf_fallback_when_sort_fails(monkeypatch):
    """sort_pages()에서 예외 발생 시 fallback PDF가 생성되어야 한다 (NameError 아님)."""
    pdf_gen = PDFGenerator(Config())
    page = PageContent(url="https://test.com", title="Test", content_html="<h1>Test</h1>", text_content="Test")

    # page_sorter.sort_pages가 예외를 던지도록 패치
    def _raise(_pages):
        raise RuntimeError("sort failed")
    monkeypatch.setattr(pdf_gen.page_sorter, "sort_pages", _raise)

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        path = tmp.name
    try:
        result = pdf_gen.generate_pdf([page], path)
        # fallback PDF가 생성되어야 함 (NameError로 크래시하지 않음)
        assert result is True
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)
