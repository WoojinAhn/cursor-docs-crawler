# Cursor Documentation Crawler

[한국어](README.ko.md) | [English](README.md)

![CI](https://github.com/WoojinAhn/cursor-docs-crawler/actions/workflows/e2e-test.yml/badge.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg) ![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

Cursor 문서 사이트(https://cursor.com/docs)의 모든 콘텐츠를 크롤링하여 단일 PDF 파일로 변환하는 Python 기반 시스템입니다. NotebookLM의 출처로 사용할 수 있는 고품질 PDF를 생성하며, 불필요한 UI 요소를 제거하고 콘텐츠만 추출하여 가독성을 최적화합니다.

## 주요 기능

- 🕷️ **자동 웹 크롤링**: cursor.com/docs의 모든 페이지를 자동으로 발견하고 크롤링
- 🧹 **콘텐츠 정제**: 사이드바, 헤더, 푸터 등 불필요한 UI 요소 제거
- 🖼️ **이미지 처리**: 이미지 다운로드, 크기 조정 및 PDF 포함
- 🎥 **YouTube 링크 변환**: 비디오를 텍스트 링크로 변환하여 PDF 크기 최적화
- 📄 **논리적 페이지 정렬**: URL 구조 기반 계층적 페이지 정렬
- 📊 **상세한 로깅**: 크롤링 진행 상황 및 통계 추적
- 🧪 **테스트 모드**: 대표 페이지 10개로 빠른 테스트 가능
- ⚡ **에러 복구**: 네트워크 오류, 메모리 부족 등 다양한 에러 상황 처리

## 설치

### 1. 저장소 클론
```bash
git clone https://github.com/WoojinAhn/cursor-docs-crawler.git
cd cursor-docs-crawler
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. WeasyPrint 의존성 설치
WeasyPrint는 시스템 레벨 의존성이 필요합니다:

**macOS:**
```bash
brew install pango libffi
```

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**Windows:**
WeasyPrint 공식 문서를 참조하세요: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows

## 사용법

### 기본 사용법
```bash
python main.py
```

### 테스트 모드 (10개 대표 페이지)
```bash
python main.py --test
```

### 오프라인 테스트 모드 (저장된 HTML fixture 사용)
```bash
# 먼저 라이브 사이트에서 fixture 저장 (Selenium 필요)
python scripts/save_fixtures.py

# 이후 오프라인 실행 — 네트워크/Selenium 불필요
python main.py --test --fixture
```

### 고급 옵션
```bash
# 출력 파일 지정
python main.py --output my_cursor_docs.pdf

# 영어 PDF 생성
python main.py --lang en

# 최대 페이지 수 제한
python main.py --max-pages 20

# 요청 간 지연 시간 조정 (초)
python main.py --delay 2.0

# 상세 로깅 활성화
python main.py --verbose

# 로그 파일 저장
python main.py --log-file crawler.log

# 모든 옵션 조합
python main.py --lang en --output cursor_docs_en.pdf --verbose --log-file test.log
```

### 명령행 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--test` | 테스트 모드 (10개 대표 페이지) | False |
| `--fixture` | 저장된 HTML fixture 사용 (오프라인, Selenium 불필요) | False |
| `--output`, `-o` | 출력 PDF 파일 경로 | cursor_docs.pdf |
| `--lang`, `-l` | 크롤링 및 PDF 출력 언어 | ko |
| `--max-pages`, `-m` | 최대 크롤링 페이지 수 | 무제한 |
| `--delay`, `-d` | 요청 간 지연 시간 (초) | 0.3 |
| `--verbose`, `-v` | 상세 로깅 활성화 | False |
| `--log-file` | 로그 파일 경로 | None |

### 지원 언어

`--lang` 옵션은 cursor.com이 제공하는 언어를 선택합니다. cursor.com/docs에서 제공하는 언어만 사용 가능하며, 번역 품질과 커버리지는 전적으로 Cursor 측에 의존합니다.

| 코드 | 언어 | 코드 | 언어 |
|------|------|------|------|
| `en` | English | `fr` | Fran&ccedil;ais |
| `ko` | 한국어 | `pt` | Portugu&ecirc;s |
| `ja` | 日本語 | `ru` | Русский |
| `zh` | 简体中文 | `tr` | T&uuml;rk&ccedil;e |
| `zh-TW` | 繁體中文 | `id` | Bahasa Indonesia |
| `es` | Espa&ntilde;ol | `de` | Deutsch |

## 프로젝트 구조

```
cursor-docs-crawler/
├── main.py                 # 메인 실행 파일
├── requirements.txt        # Python 의존성
├── README.md              # 영어 문서
├── README.ko.md           # 한국어 문서
├── scripts/               # 유틸리티 스크립트
│   └── save_fixtures.py   # 라이브 크롤링에서 HTML fixture 저장
├── src/                   # 소스 코드
│   ├── __init__.py
│   ├── config.py          # 설정 클래스
│   ├── constants.py       # 상수 정의
│   ├── models.py          # 데이터 모델
│   ├── url_manager.py     # URL 관리
│   ├── selenium_crawler.py # Selenium 기반 크롤러
│   ├── fixture_crawler.py # Fixture 기반 크롤러 (오프라인)
│   ├── content_parser.py  # 콘텐츠 파싱
│   ├── page_sorter.py     # 페이지 정렬
│   ├── pdf_generator.py   # PDF 생성
│   └── logger.py          # 로깅 시스템
├── tests/                 # 테스트 코드
│   ├── test_url_manager.py
│   ├── test_content_parser.py
│   ├── test_pdf_generator.py
│   ├── test_e2e_offline.py # 오프라인 E2E 테스트 (fixture 기반)
│   └── fixtures/          # 오프라인 테스트용 저장된 HTML 스냅샷
│       ├── manifest.json
│       └── html/
└── .github/workflows/
    └── e2e-test.yml       # CI: PR 오프라인 테스트 + 주간 fixture 갱신
```

## 사이트 매핑(사이트 구조 탐색) 로직 상세

### 크롤링 및 링크 추출
- Selenium을 이용해 실제 브라우저 환경에서 JS까지 렌더링된 HTML을 가져옵니다.
- BeautifulSoup으로 HTML을 파싱하여 `<a href=...>` 형태의 모든 링크를 추출합니다.
- 추출된 링크는 다음과 같이 처리됩니다:
  1. **정규화**: 상대경로/해시/쿼리 등은 절대경로로 변환, fragment(해시)는 제거
  2. **도메인 & 경로 필터링**: cursor.com/docs 경로 외의 링크는 무시
  3. **파일/리소스 필터링**: .jpg, .png, .pdf 등 문서가 아닌 리소스는 무시
  4. **로케일 제거**: 자동 삽입되는 로케일 접두사(/ko/, /en/)를 제거하여 정규 URL 유지
  5. **중복 제거**: 이미 방문했거나 큐에 있는 URL은 추가하지 않음
  6. **페이지 수 제한**: 최대 크롤링 페이지 수를 초과하면 큐에 추가하지 않음
- 이 과정을 통해 사이트 전체의 논리적 구조(페이지 간 연결)를 자동으로 매핑합니다.

### 크롤링/파싱/진행 로그
- 크롤링 시작 시: `[Selenium] Crawling: <URL>` (콘솔 및 로그에 info 레벨로 출력)
- 파싱 시작 시: `[Main] Parsing page n/총개수: <URL>` (콘솔에 출력)
- 파서 내부: `[Parser] Parsing content for: <URL>` (info 레벨)
- PDF 생성, 에러, 통계 등도 단계별로 명확하게 출력되어 진행 상황을 실시간으로 확인할 수 있습니다.

## 작동 원리 (최신)

### 1. 크롤링 및 사이트 매핑 단계
1. **시작점 설정**: `https://cursor.com/docs`을 시작점으로 Selenium 브라우저에서 로딩
2. **llms.txt 시딩**: `cursor.com/llms.txt`를 파싱하여 모든 공식 문서 URL을 큐에 추가 — BFS 링크 탐색으로 도달할 수 없는 페이지도 크롤링
3. **링크 추출 및 정규화**: BeautifulSoup으로 모든 `<a>` 링크를 추출, 절대경로/해시제거/도메인필터/파일필터/중복제거
4. **순차 크롤링**: 큐에 쌓인 URL을 순차적으로 방문하며, 위 과정을 반복하여 사이트 전체 구조를 자동으로 탐색

### 2. 콘텐츠 처리 단계
1. **HTML 파싱**: BeautifulSoup으로 HTML 구조 분석
2. **불필요 요소 제거**: 네비게이션, 사이드바, 푸터 등 제거
3. **메인 콘텐츠 추출**: 실제 문서 내용만 추출
4. **이미지 처리**: 의미 있는 이미지만 남기고, 경로 정규화 및 스타일 적용
5. **YouTube 변환**: 비디오 임베드를 텍스트 링크로 변환

### 3. PDF 생성 단계
1. **페이지 정렬**: URL 구조 기반 논리적 순서 정렬
2. **HTML 생성**: 전체 문서를 단일 HTML로 결합
3. **스타일 적용**: PDF 최적화된 CSS 스타일 적용
4. **PDF 변환**: WeasyPrint를 사용한 고품질 PDF 생성

## 예시 로그
```
[Selenium] Crawling: https://cursor.com/docs/get-started/quickstart
[Main] Parsing page 3/120: https://cursor.com/docs/get-started/quickstart
[Parser] Parsing content for: https://cursor.com/docs/get-started/quickstart
```

## 설정 옵션

### 기본 설정 (src/config.py)
```python
class Config:
    BASE_URL = "https://cursor.com/docs"
    OUTPUT_FILE = "cursor_docs.pdf"
    MAX_PAGES = None  # 무제한
    DELAY_BETWEEN_REQUESTS = 0.3
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
```

### 테스트 설정
```python
class TestConfig(Config):
    MAX_PAGES = 10
    # 10개 대표 페이지: text, tables, images, code, mixed
```

## 테스트 실행

```bash
# 모든 테스트 실행 (fixture가 있으면 오프라인 E2E 포함)
python -m pytest tests/

# 특정 테스트 파일 실행
python -m pytest tests/test_url_manager.py

# 오프라인 E2E 테스트만 실행
python -m pytest tests/test_e2e_offline.py -v

# 커버리지와 함께 테스트 실행
python -m pytest tests/ --cov=src
```

### 오프라인 E2E 테스트

Selenium이나 네트워크 없이 파싱→PDF 전체 파이프라인을 검증하는 fixture 기반 E2E 테스트 시스템입니다.

```bash
# 1. 라이브 사이트에서 HTML fixture 저장 (최초 1회 또는 갱신 시)
python scripts/save_fixtures.py

# 2. 오프라인 E2E 테스트 실행 (~6초, 네트워크 불필요)
python -m pytest tests/test_e2e_offline.py -v
```

**CI 통합 (GitHub Actions):**

| 트리거 | 실행 내용 | 네트워크 필요 |
|--------|-----------|:-:|
| Pull Request | 오프라인 테스트 (커밋된 fixture 사용) | 아니오 |
| `workflow_dispatch` | 오프라인 테스트 (수동 트리거) | 아니오 |
| 주간 cron (일요일 03:00 UTC) | 라이브 사이트에서 fixture 갱신 + 커밋 | 예 |

## 에러 처리

시스템은 다양한 에러 상황을 자동으로 처리합니다:

- **네트워크 에러**: 자동 재시도 (최대 3회)
- **메모리 부족**: 가비지 컬렉션 및 배치 크기 조정
- **디스크 공간 부족**: 임시 파일 정리
- **PDF 생성 실패**: 간소화된 폴백 PDF 생성
- **콘텐츠 파싱 실패**: 기본 텍스트 추출로 폴백

## 성능 최적화

### 메모리 사용량 최적화
- 페이지별 순차 처리로 메모리 사용량 제한
- 이미지 크기 자동 조정 (최대 800x600)
- 가비지 컬렉션 자동 실행

### 네트워크 최적화
- 요청 간 지연 시간으로 서버 부하 방지
- Keep-Alive 연결 사용
- 적절한 User-Agent 설정

### PDF 최적화
- 이미지 품질 조정 (85% JPEG 품질)
- 폰트 최적화
- 페이지 레이아웃 최적화

## 문제 해결

### 일반적인 문제

**1. WeasyPrint 설치 오류**
```bash
# macOS
brew install pango libffi

# Ubuntu
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
```

**2. 메모리 부족 오류**
```bash
# 페이지 수 제한
python main.py --max-pages 50

# 더 긴 지연 시간 설정
python main.py --delay 2.0
```

**3. 네트워크 타임아웃**
- 안정적인 인터넷 연결 확인
- 방화벽 설정 확인
- VPN 사용 시 비활성화 시도

**4. PDF 생성 실패**
- 디스크 공간 확인 (최소 1GB 권장)
- 출력 디렉토리 쓰기 권한 확인
- 폴백 PDF가 생성되는지 확인

### 로그 분석

상세한 로그를 통해 문제를 진단할 수 있습니다:

```bash
# 상세 로그와 함께 실행
python main.py --verbose --log-file debug.log

# 로그 파일 확인
tail -f debug.log
```

## 기여하기

1. 이슈 리포트: 버그나 개선 사항을 GitHub Issues에 등록
2. 풀 리퀘스트: 코드 개선이나 새 기능 추가
3. 테스트: 새로운 테스트 케이스 추가
4. 문서화: README나 코드 주석 개선

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# 코드 포매팅
black src/ tests/

# 린팅
flake8 src/ tests/

# 테스트 실행
pytest tests/ --cov=src
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 지원

- 이슈 리포트: [GitHub Issues](https://github.com/WoojinAhn/cursor-docs-crawler/issues)
- 문서: 이 README 파일
- 예제: `tests/` 디렉토리의 테스트 코드

## 출력 예시

📄 **[샘플 PDF 다운로드 (영문, ~14 MB)](https://drive.google.com/file/d/1RYaQBs3LLHIzCfA7LCkqqQzpLyJbqyy6/view?usp=sharing)**
*2026-02-23 생성 — 114페이지, 83,684단어, 103개 이미지*

전체 크롤 시 대략적인 결과:
- **~114 페이지** 크롤링
- **~75,000 단어** 추출
- **~100개 이미지** 포함
- **~16 MB** PDF 파일
- **~5분** 총 소요 시간

## 면책 조항

- **콘텐츠 저작권**: 모든 문서 콘텐츠의 저작권은 Anysphere Inc.에 있습니다. 이 도구는 개인 아카이빙 및 교육 목적으로만 제공됩니다.
- **이용 약관**: [cursor.com 이용 약관](https://cursor.com/terms)을 준수하여 사용해야 합니다. 사용 전 `cursor.com/robots.txt`를 확인하세요.
- **책임감 있는 사용**: 적절한 요청 간격을 설정하고 서버에 과도한 부하를 주지 마세요.
- **무보증**: 이 도구는 있는 그대로 제공됩니다. 사용으로 인해 발생하는 문제에 대해 작성자는 책임지지 않습니다. 관련 법률 및 이용 약관 준수에 대한 책임은 전적으로 사용자에게 있습니다.
- **구조 의존성**: 이 도구는 cursor.com/docs의 HTML 구조에 의존하며, 사이트 구조가 변경되면 동작하지 않을 수 있습니다.