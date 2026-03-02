# Cursor Documentation Crawler

[한국어](README.ko.md) | [English](README.md)

![CI](https://github.com/WoojinAhn/cursor-docs-crawler/actions/workflows/e2e-test.yml/badge.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg) ![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

A Python-based web crawler that extracts all content from the Cursor documentation site (https://cursor.com/docs) and converts it into a single PDF file. This tool generates high-quality PDFs suitable for use as sources in NotebookLM, removing unnecessary UI elements and extracting only the content for optimal readability.

## Key Features

- 🕷️ **Automated Web Crawling**: Automatically discovers and crawls all pages from cursor.com/docs
- 🧹 **Content Refinement**: Removes unnecessary UI elements like sidebars, headers, and footers
- 🖼️ **Image Processing**: Downloads, resizes, and embeds images in PDF
- 🎥 **YouTube Link Conversion**: Converts videos to text links for PDF size optimization
- 📄 **Logical Page Sorting**: Hierarchical page sorting based on URL structure
- 📊 **Detailed Logging**: Tracks crawling progress and statistics
- 🧪 **Test Mode**: Quick testing with 10 representative pages
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
python main.py
```

### Test Mode (10 representative pages)
```bash
python main.py --test
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
| `--output`, `-o` | Output PDF file path | cursor_docs.pdf |
| `--lang`, `-l` | Language for crawling and PDF output | ko |
| `--max-pages`, `-m` | Maximum pages to crawl | Unlimited |
| `--delay`, `-d` | Delay between requests (seconds) | 0.3 |
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
│   ├── selenium_crawler.py # Selenium-based crawler
│   ├── fixture_crawler.py # Fixture-based crawler (offline)
│   ├── content_parser.py  # Content parsing
│   ├── page_sorter.py     # Page sorting
│   ├── pdf_generator.py   # PDF generation
│   └── logger.py          # Logging system
├── tests/                 # Test code
│   ├── test_url_manager.py
│   ├── test_content_parser.py
│   ├── test_pdf_generator.py
│   ├── test_e2e_offline.py # Offline E2E test (fixture-based)
│   └── fixtures/          # Saved HTML snapshots for offline testing
│       ├── manifest.json
│       └── html/
└── .github/workflows/
    └── e2e-test.yml       # CI: PR offline tests + weekly fixture refresh
```

## Site Mapping (Site Structure Discovery) Logic

### Crawling and Link Extraction
- Uses Selenium to load HTML in a real browser environment with JavaScript rendering
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
1. **Starting Point**: Loads `https://cursor.com/docs` in Selenium browser
2. **URL Seeding from llms.txt**: Fetches `cursor.com/llms.txt` to seed all official doc page URLs — ensures pages unreachable via BFS link traversal are still crawled
3. **Link Extraction and Normalization**: Extracts all `<a>` links with BeautifulSoup, applies absolute path/hash removal/domain filtering/file filtering/duplicate removal
4. **Sequential Crawling**: Visits URLs in queue sequentially, repeating the above process to automatically explore the entire site structure

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

| Trigger | What runs | Network needed |
|---------|-----------|:-:|
| Pull request | Offline tests (from committed fixtures) | No |
| `workflow_dispatch` | Offline tests (manual trigger) | No |
| Weekly cron (Sun 03:00 UTC) | Refresh fixtures from live site + commit | Yes |

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

Pre-built PDFs (Korean & English) are available on the [Releases](https://github.com/WoojinAhn/cursor-docs-crawler/releases/latest) page — updated weekly.

Full crawl produces approximately:
- **~114 pages** crawled
- **~75,000 words** extracted
- **~100 images** embedded
- **~16 MB** PDF file
- **~5 minutes** total duration

## Disclaimer

- **Content Copyright**: All documentation content belongs to Anysphere Inc. This tool is provided solely for personal archiving and educational purposes.
- **Terms of Service**: Use of this tool must comply with [cursor.com's Terms of Service](https://cursor.com/terms). Check `cursor.com/robots.txt` before use.
- **Responsible Use**: Set appropriate request delays and avoid placing excessive load on the server.
- **No Warranty**: This tool is provided as-is. The author is not responsible for any issues arising from its use. Users are solely responsible for compliance with applicable laws and terms of service.
- **Structural Dependency**: This tool depends on cursor.com/docs HTML structure and may break if the site changes.
- **Takedown**: If Anysphere Inc. requests removal of any content or generated PDFs, we will comply promptly.