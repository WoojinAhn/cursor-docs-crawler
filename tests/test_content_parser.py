import pytest
from src.config import Config
from src.content_parser import ContentParser
from src.models import PageData

def test_parse_page_basic():
    parser = ContentParser(Config())
    html = '''<html><body><main><h1>Title</h1><p>Content</p><img src="/img.png"></main></body></html>'''
    page = PageData(url="https://test.com", title="Test", html_content=html, status_code=200)
    result = parser.parse_page(page)
    assert "Title" in result.content_html
    assert result.word_count > 0
    assert result.image_count == 1

def test_parse_page_fallback():
    parser = ContentParser(Config())
    # BeautifulSoup이 파싱할 수 없는 이상한 HTML로 Exception 유발
    invalid_html = "<html><body><script>alert('test')</script><div>Content</div></body></html>"
    # script 태그가 제거되어야 하는데, 일부러 이상한 구조로 만들어서 파싱 중 문제 발생시키기
    page = PageData(url="https://test.com", title="Test", html_content=invalid_html, status_code=200)
    result = parser.parse_page(page)
    # 정상적으로 파싱되어야 함 (script 태그 제거됨)
    assert "Content" in result.content_html
    assert "script" not in result.content_html.lower() 