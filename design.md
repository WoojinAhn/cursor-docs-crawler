# Design Document

## Overview

Cursor 문서 크롤링 시스템은 Python 기반의 웹 크롤러로, docs.cursor.com의 모든 콘텐츠를 수집하여 단일 PDF로 변환합니다. 시스템은 모듈화된 아키텍처를 사용하여 크롤링, 콘텐츠 처리, PDF 생성을 분리하고, 테스트 모드를 지원하여 빠른 개발과 검증을 가능하게 합니다.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Crawler   │───▶│ Content Parser  │───▶│  PDF Generator  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  URL Manager    │    │ Content Filter  │    │ Image Processor │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Logger       │    │   Config        │    │   File Utils    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Configuration Manager
```python
class Config:
    BASE_URL: str = "https://docs.cursor.com/"
    MAX_PAGES: int = None  # None for unlimited, number for test mode
    OUTPUT_FILE: str = "cursor_docs.pdf"
    DELAY_BETWEEN_REQUESTS: float = 1.0
    USER_AGENT: str = "Cursor Docs Crawler 1.0"
    EXCLUDED_SELECTORS: List[str] = [
        "nav", "header", "footer", ".sidebar", 
        ".navigation", ".breadcrumb", ".toc"
    ]
    CONTENT_SELECTORS: List[str] = [
        "main", ".content", "article", ".documentation"
    ]
```

### 2. URL Manager
```python
class URLManager:
    def __init__(self, base_url: str, max_pages: int = None)
    def add_url(self, url: str) -> bool
    def get_next_url(self) -> Optional[str]
    def is_visited(self, url: str) -> bool
    def mark_visited(self, url: str) -> None
    def get_stats(self) -> Dict[str, int]
    def should_crawl(self, url: str) -> bool
```

### 3. Web Crawler
```python
class WebCrawler:
    def __init__(self, config: Config, url_manager: URLManager)
    def crawl_page(self, url: str) -> Optional[PageData]
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]
    def crawl_all(self) -> List[PageData]
```

### 4. Content Parser
```python
class ContentParser:
    def __init__(self, config: Config)
    def parse_page(self, html: str, url: str) -> PageContent
    def remove_unwanted_elements(self, soup: BeautifulSoup) -> BeautifulSoup
    def extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup
    def process_images(self, soup: BeautifulSoup) -> BeautifulSoup
    def process_youtube_links(self, soup: BeautifulSoup) -> BeautifulSoup
```

### 5. PDF Generator
```python
class PDFGenerator:
    def __init__(self, config: Config)
    def generate_pdf(self, pages: List[PageContent], output_path: str) -> None
    def sort_pages(self, pages: List[PageContent]) -> List[PageContent]
    def create_table_of_contents(self, pages: List[PageContent]) -> str
    def convert_html_to_pdf_content(self, html: str) -> str
```

### 6. Image Processor
```python
class ImageProcessor:
    def __init__(self, config: Config)
    def download_image(self, url: str) -> Optional[bytes]
    def resize_image(self, image_data: bytes, max_width: int = 800) -> bytes
    def convert_to_base64(self, image_data: bytes) -> str
```

## Data Models

### PageData
```python
@dataclass
class PageData:
    url: str
    title: str
    html_content: str
    status_code: int
    crawled_at: datetime
    links: List[str]
```

### PageContent
```python
@dataclass
class PageContent:
    url: str
    title: str
    content_html: str
    text_content: str
    images: List[str]
    order_key: str  # For sorting based on URL structure
```

## Error Handling

### 1. Network Errors
- HTTP 요청 실패 시 재시도 로직 (최대 3회)
- 타임아웃 설정 (30초)
- Rate limiting 준수

### 2. Parsing Errors
- 잘못된 HTML 구조 처리
- 이미지 다운로드 실패 시 대체 텍스트 사용
- 콘텐츠 추출 실패 시 원본 HTML 사용

### 3. PDF Generation Errors
- 폰트 로딩 실패 시 기본 폰트 사용
- 이미지 변환 실패 시 링크로 대체
- 메모리 부족 시 배치 처리

### 4. File System Errors
- 디스크 공간 부족 검사
- 권한 오류 처리
- 임시 파일 정리

## Testing Strategy

### 1. Unit Tests
- 각 컴포넌트별 독립적 테스트
- Mock 객체를 사용한 외부 의존성 격리
- 에러 케이스 테스트

### 2. Integration Tests
- 전체 크롤링 파이프라인 테스트
- 실제 웹사이트 대신 로컬 테스트 서버 사용
- PDF 생성 결과 검증

### 3. Test Mode Implementation
```python
class TestConfig(Config):
    MAX_PAGES: int = 5  # 테스트용 제한
    BASE_URL: str = "https://docs.cursor.com/"
    TEST_URLS: List[str] = [
        "https://docs.cursor.com/",
        "https://docs.cursor.com/getting-started",
        "https://docs.cursor.com/features",
        "https://docs.cursor.com/settings",
        "https://docs.cursor.com/troubleshooting"
    ]
```

### 4. Performance Tests
- 메모리 사용량 모니터링
- 크롤링 속도 측정
- PDF 생성 시간 측정

## Implementation Details

### 1. URL Sorting Algorithm
```python
def generate_order_key(url: str) -> str:
    """URL을 기반으로 정렬 키 생성"""
    path = urlparse(url).path.strip('/')
    if not path or path == 'index':
        return '000_index'
    
    parts = path.split('/')
    # 깊이별로 정렬 키 생성
    order_parts = []
    for i, part in enumerate(parts):
        order_parts.append(f"{i:03d}_{part}")
    
    return '_'.join(order_parts)
```

### 2. Content Extraction Strategy
- BeautifulSoup을 사용한 HTML 파싱
- CSS 선택자 기반 불필요 요소 제거
- 메인 콘텐츠 영역 자동 감지
- 마크다운 스타일 텍스트 정규화

### 3. PDF Generation Approach
- WeasyPrint 또는 ReportLab 사용
- HTML to PDF 변환
- 목차 자동 생성
- 페이지 번호 및 헤더/푸터 추가

### 4. Concurrency Strategy
- 순차적 크롤링 (서버 부하 방지)
- 이미지 다운로드는 병렬 처리
- 적절한 지연 시간 설정

## Dependencies

### Core Libraries
- `requests`: HTTP 요청
- `beautifulsoup4`: HTML 파싱
- `weasyprint`: PDF 생성
- `Pillow`: 이미지 처리
- `urllib3`: URL 처리

### Development Libraries
- `pytest`: 테스트 프레임워크
- `pytest-mock`: Mock 객체
- `black`: 코드 포매팅
- `flake8`: 린팅

### Optional Libraries
- `tqdm`: 진행률 표시
- `colorlog`: 컬러 로깅
- `click`: CLI 인터페이스