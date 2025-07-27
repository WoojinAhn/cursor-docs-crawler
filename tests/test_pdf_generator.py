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