# Cursor Documentation Crawler

[한국어](README.ko.md) | [English](README.md)

![CI](https://github.com/WoojinAhn/cursor-docs-crawler/actions/workflows/e2e-test.yml/badge.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg) ![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

A Python-based web crawler that extracts content from the Cursor documentation site (https://cursor.com/docs and https://cursor.com/help) and converts it into PDF files. This tool generates high-quality PDFs suitable for use as sources in NotebookLM, removing unnecessary UI elements and extracting only the content for optimal readability.

### Why Two Separate PDFs?

In March 2026, Cursor restructured their documentation into two distinct sections:

- **`/docs/`** — Technical reference: architecture, API specs, token pricing, configuration details
- **`/help/`** — User help center: how-to guides, troubleshooting FAQs, account management

These serve fundamentally different purposes (reference vs. support), and mixing them in a single PDF degrades NotebookLM source quality — the same topic appears twice with different tones, confusing retrieval. The `--scope` option lets you generate each as a separate, focused PDF.

## Key Features

- 🕷️ **Automated Web Crawling**: Automatically discovers and crawls all pages from cursor.com/docs and cursor.com/help
- 📑 **Scope Selection**: Generate docs (technical reference), help (user guide), or both as separate PDFs
- 🧹 **Content Refinement**: Removes unnecessary UI elements like sidebars, headers, and footers
- 🖼️ **Image Processing**: Downloads, resizes, and embeds images in PDF
- 🎥 **YouTube Link Conversion**: Converts videos to text links for PDF size optimization
- 📄 **Logical Page Sorting**: Hierarchical page sorting based on URL structure
- 📊 **Detailed Logging**: Tracks crawling progress and statistics
- 🧪 **Test Mode**: Quick testing with 10 representative pages
- 🔍 **llms.txt Coverage Validation**: Post-crawl check flags any pages listed in llms.txt but not crawled
- ⚡ **Error Recovery**: Handles various error scenarios including network failures and memory issues

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/WoojinAhn/cursor-docs-crawler.git
cd cursor-docs-crawler
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install WeasyPrint Dependencies
WeasyPrint requires system-level dependencies:

**macOS:**
```bash
brew install pango libffi
```

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**Windows:**
Refer to the official WeasyPrint documentation: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows

## Usage

### Basic Usage
```bash
# Generate docs PDF (default)
python main.py

# Generate help center PDF
python main.py --scope help

# Generate both PDFs (cursor_docs.pdf + cursor_help.pdf)
python main.py --scope all
```

### Test Mode (10 representative pages)
```bash
python main.py --test
python main.py --test --scope help
```

### Offline Test Mode (using saved HTML fixtures)
```bash
# First, save fixtures from live site (requires Selenium)
python scripts/save_fixtures.py

# Then run offline — no network or Selenium needed
python main.py --test --fixture
```

### Advanced Options
```bash
# Specify output file
python main.py --output my_cursor_docs.pdf

# Generate PDF in English
python main.py --lang en

# Limit maximum pages
python main.py --max-pages 20

# Adjust delay between requests (seconds)
python main.py --delay 2.0

# Enable verbose logging
python main.py --verbose

# Save logs to file
python main.py --log-file crawler.log

# Combine all options
python main.py --lang en --output cursor_docs_en.pdf --verbose --log-file test.log
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--test` | Test mode (10 representative pages) | False |
| `--fixture` | Use saved HTML fixtures (offline, no Selenium) | False |
| `--scope`, `-s` | Crawl scope: `docs`, `help`, or `all` | docs |
| `--output`, `-o` | Output PDF file path | Per scope |
| `--lang`, `-l` | Language for crawling and PDF output | ko |
| `--max-pages`, `-m` | Maximum pages to crawl | Unlimited |
| `--delay`, `-d` | Delay between requests (seconds) | 1.0 |
| `--verbose`, `-v` | Enable verbose logging | False |
| `--log-file` | Log file path | None |

### Supported Languages

The `--lang` option controls which language cursor.com serves. Only languages provided by cursor.com/docs are available — translation quality and coverage depend entirely on Cursor's site.

| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | English | `fr` | Fran&ccedil;ais |
| `ko` | 한국어 | `pt` | Portugu&ecirc;s |
| `ja` | 日本語 | `ru` | Русский |
| `zh` | 简体中文 | `tr` | T&uuml;rk&ccedil;e |
| `zh-TW` | 繁體中文 | `id` | Bahasa Indonesia |
| `es` | Espa&ntilde;ol | `de` | Deutsch |

## Project Structure

```
cursor-docs-crawler/
├── main.py                 # Main execution file
├── requirements.txt        # Python dependencies
├── README.md              # This file (English)
├── README.ko.md           # Korean documentation
├── scripts/               # Utility scripts
│   └── save_fixtures.py   # Save HTML fixtures from live crawl
├── src/                   # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration class
│   ├── constants.py       # Constants definition
│   ├── models.py          # Data models
│   ├── url_manager.py     # URL management
│   ├── selenium_crawler.py # Web crawler (SeleniumBase UC Mode)
│   ├── fixture_crawler.py # Fixture-based crawler (offline)
│   ├── content_parser.py  # Content parsing
│   ├── page_sorter.py     # Page sorting
│   ├── pdf_generator.py   # PDF generation
│   └── logger.py          # Logging system
├── tests/                 # Test code
│   ├── test_url_manager.py
│   ├── test_content_parser.py
│   ├── test_pdf_generator.py
│   ├── test_scope.py      # Scope configuration and seed regex tests
│   ├── test_e2e_offline.py # Offline E2E test (fixture-based)
│   └── fixtures/          # Saved HTML snapshots for offline testing
│       ├── manifest.json
│       └── html/
└── .github/workflows/
    ├── e2e-test.yml           # CI: PR offline tests + weekly fixture refresh
    ├── detect-docs-change.yml # CI: daily llms.txt change detection → triggers release
    └── release-pdf.yml        # CI: generate PDFs and create GitHub Release
```

## Site Mapping (Site Structure Discovery) Logic

### Crawling and Link Extraction
- Uses SeleniumBase (UC Mode) to load HTML in a real browser environment with JavaScript rendering
- Parses HTML with BeautifulSoup to extract all `<a href=...>` links
- Processes extracted links as follows:
  1. **Normalization**: Converts relative paths/hashes/queries to absolute paths, removes fragments
  2. **Domain & Path Filtering**: Only follows links under cursor.com/docs path
  3. **File/Resource Filtering**: Ignores non-document resources like .jpg, .png, .pdf
  4. **Locale Stripping**: Removes auto-inserted locale prefixes (/ko/, /en/) for canonical URLs
  5. **Duplicate Removal**: Doesn't add URLs already visited or in queue
  6. **Page Limit**: Doesn't add URLs if maximum crawl limit is exceeded
- This process automatically maps the entire site's logical structure (page connections)

### Crawling/Parsing/Progress Logs
- Crawling start: `[Selenium] Crawling: <URL>` (output to console and logs at info level)
- Parsing start: `[Main] Parsing page n/total: <URL>` (output to console)
- Parser internal: `[Parser] Parsing content for: <URL>` (info level)
- PDF generation, errors, statistics are also clearly output at each stage for real-time progress monitoring

## How It Works (Latest)

### 1. Crawling and Site Mapping Phase
1. **Scope Selection**: Determines target section (`/docs/`, `/help/`, or both) based on `--scope` option
2. **URL Seeding from llms.txt**: Fetches `cursor.com/llms.txt` to seed all official page URLs — ensures pages unreachable via BFS link traversal are still crawled
3. **BFS Crawling**: Loads pages via SeleniumBase UC Mode (JS rendering required for Next.js SPA), extracts links, builds URL queue
4. **Link Normalization**: Absolute path conversion, fragment removal, locale stripping (`/ko/docs/...` → `/docs/...`), domain/file filtering, deduplication
5. **Coverage Validation**: After crawl, checks all llms.txt URLs were actually crawled — flags any gaps

### 2. Content Processing Phase
1. **HTML Parsing**: Analyzes HTML structure with BeautifulSoup
2. **Unnecessary Element Removal**: Removes navigation, sidebars, footers, etc.
3. **Main Content Extraction**: Extracts only actual document content
4. **Image Processing**: Keeps meaningful images, normalizes paths and applies styles
5. **YouTube Conversion**: Converts video embeds to text links

### 3. PDF Generation Phase
1. **Page Sorting**: Logical ordering based on URL structure
2. **HTML Generation**: Combines all documents into single HTML
3. **Style Application**: Applies PDF-optimized CSS styles
4. **PDF Conversion**: Generates high-quality PDF using WeasyPrint

## Example Logs
```
[Selenium] Crawling: https://cursor.com/docs/get-started/quickstart
[Main] Parsing page 3/120: https://cursor.com/docs/get-started/quickstart
[Parser] Parsing content for: https://cursor.com/docs/get-started/quickstart
```

## Configuration Options

### Basic Configuration (src/config.py)
```python
class Config:
    SCOPE = "docs"  # "docs", "help" — controls target section
    BASE_URL = "https://cursor.com/docs"
    OUTPUT_FILE = "cursor_docs.pdf"
    MAX_PAGES = None  # Unlimited
    DELAY_BETWEEN_REQUESTS = 0.3
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
```

### Test Configuration
```python
class TestConfig(Config):
    MAX_PAGES = 10
    # 10 representative pages: text, tables, images, code, mixed
```

## Running Tests

```bash
# Run all tests (includes offline E2E if fixtures exist)
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_url_manager.py

# Run only offline E2E tests
python -m pytest tests/test_e2e_offline.py -v

# Run tests with coverage
python -m pytest tests/ --cov=src
```

### Offline E2E Testing

The project includes a fixture-based E2E test system that runs the full parse→PDF pipeline without Selenium or network access.

```bash
# 1. Save HTML fixtures from live site (one-time, or to refresh)
python scripts/save_fixtures.py

# 2. Run offline E2E tests (~6 seconds, no network needed)
python -m pytest tests/test_e2e_offline.py -v
```

**CI Integration (GitHub Actions):**

| Workflow | Trigger | What runs | Network needed |
|----------|---------|-----------|:-:|
| **E2E Test** | Pull request | Offline tests (from committed fixtures) | No |
| **E2E Test** | Weekly cron (Sun 03:00 UTC) | Refresh fixtures from live site + commit | Yes |
| **Detect Docs Change** | Daily cron (00:00 UTC) | Fetch llms.txt, compare with snapshot, trigger release if changed | Yes |
| **Release PDF** | Weekly cron (Sun 06:00 UTC) or auto-triggered by change detection | Generate 4 PDFs (docs+help × ko+en), create GitHub Release | Yes |

## Error Handling

The system automatically handles various error scenarios:

- **Network Errors**: Automatic retry (up to 3 times)
- **Memory Issues**: Garbage collection and batch size adjustment
- **Disk Space Issues**: Temporary file cleanup
- **PDF Generation Failure**: Simplified fallback PDF generation
- **Content Parsing Failure**: Fallback to basic text extraction

## Performance Optimization

### Memory Usage Optimization
- Sequential page processing to limit memory usage
- Automatic image resizing (max 800x600)
- Automatic garbage collection

### Network Optimization
- Delay between requests to prevent server overload
- Keep-Alive connection usage
- Appropriate User-Agent settings

### PDF Optimization
- Image quality adjustment (85% JPEG quality)
- Font optimization
- Page layout optimization

## Troubleshooting

### Common Issues

**1. WeasyPrint Installation Error**
```bash
# macOS
brew install pango libffi

# Ubuntu
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
```

**2. Memory Issues**
```bash
# Limit page count
python main.py --max-pages 50

# Set longer delay
python main.py --delay 2.0
```

**3. Network Timeout**
- Check stable internet connection
- Verify firewall settings
- Try disabling VPN

**4. PDF Generation Failure**
- Check disk space (minimum 1GB recommended)
- Verify write permissions for output directory
- Check if fallback PDF is generated

### Log Analysis

You can diagnose issues through detailed logs:

```bash
# Run with detailed logging
python main.py --verbose --log-file debug.log

# Check log file
tail -f debug.log
```

## Contributing

1. **Issue Reports**: Report bugs or improvements via GitHub Issues
2. **Pull Requests**: Add code improvements or new features
3. **Testing**: Add new test cases
4. **Documentation**: Improve README or code comments

### Development Environment Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Run tests
pytest tests/ --cov=src
```

## License

This project is distributed under the MIT License.

## Support

- **Issue Reports**: [GitHub Issues](https://github.com/WoojinAhn/cursor-docs-crawler/issues)
- **Documentation**: This README file
- **Examples**: Test code in the `tests/` directory

## Download PDF

Pre-built PDFs are available on the [Releases](https://github.com/WoojinAhn/cursor-docs-crawler/releases/latest) page — updated weekly.

Each release includes 4 PDFs (docs + help, in Korean & English).

### Latest Stats (2026-03-26)

| Scope | Pages | Words | Images | Size | Description |
|-------|-------|-------|--------|------|-------------|
| `docs` | 83 | 70,097 | 45 | ~8 MB | Technical reference |
| `help` | 62 | 12,965 | 0 | ~2 MB | User guide & troubleshooting |

- **Total generation time**: ~6 minutes (both scopes, single language)

## Disclaimer

- **Content Copyright**: All documentation content belongs to Anysphere Inc. This tool is provided solely for personal archiving and educational purposes.
- **Terms of Service**: Use of this tool must comply with [cursor.com's Terms of Service](https://cursor.com/terms). The `cursor.com/robots.txt` allows crawling of `/docs/` and `/help/` paths.
- **Responsible Use**: This tool crawls only publicly available documentation pages at a respectful rate with delays between requests. It does not access authenticated endpoints, private data, or internal APIs.
- **No Warranty**: This tool is provided as-is. The author is not responsible for any issues arising from its use. Users are solely responsible for compliance with applicable laws and terms of service.
- **Structural Dependency**: This tool depends on cursor.com/docs HTML structure and may break if the site changes.
- **Takedown**: If Anysphere Inc. requests removal of any content or generated PDFs, we will comply promptly.