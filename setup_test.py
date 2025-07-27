#!/usr/bin/env python3
"""Simple setup test to verify basic functionality without external dependencies."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    try:
        from src.config import Config, TestConfig
        print("✅ Config modules imported successfully")
        
        from src.models import PageData, PageContent, CrawlStats
        print("✅ Model classes imported successfully")
        
        from src.constants import LOG_FORMAT, YOUTUBE_PATTERNS
        print("✅ Constants imported successfully")
        
        # Test basic functionality without external dependencies
        config = Config()
        test_config = TestConfig()
        
        print(f"✅ Config initialized - Base URL: {config.BASE_URL}")
        print(f"✅ Test config initialized - Max pages: {test_config.MAX_PAGES}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_models():
    """Test basic model functionality."""
    print("\nTesting data models...")
    
    try:
        from src.models import PageData, PageContent, CrawlStats
        from datetime import datetime
        
        # Test PageData
        page_data = PageData(
            url="https://docs.cursor.com/test",
            title="Test Page",
            html_content="<html><body>Test</body></html>",
            status_code=200
        )
        
        assert page_data.is_valid()
        assert page_data.domain == "docs.cursor.com"
        print("✅ PageData model working correctly")
        
        # Test PageContent
        page_content = PageContent(
            url="https://docs.cursor.com/test",
            title="Test Page",
            content_html="<h1>Test</h1><p>Content</p>",
            text_content="Test Content"
        )
        
        assert page_content.is_valid()
        assert page_content.word_count == 2
        assert page_content.order_key is not None
        print("✅ PageContent model working correctly")
        
        # Test CrawlStats
        stats = CrawlStats()
        stats.add_page_found()
        stats.add_page_crawled()
        
        assert stats.total_pages_found == 1
        assert stats.pages_crawled == 1
        assert stats.success_rate == 100.0
        print("✅ CrawlStats model working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test error: {e}")
        return False

def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    try:
        from src.config import Config, TestConfig
        
        # Test valid config
        config = Config()
        assert config.BASE_URL == "https://docs.cursor.com/"
        assert config.OUTPUT_FILE.endswith('.pdf')
        print("✅ Basic config validation working")
        
        # Test test config
        test_config = TestConfig()
        assert test_config.MAX_PAGES == 5
        assert len(test_config.TEST_URLS) == 5
        print("✅ Test config validation working")
        
        # Test domain extraction
        assert config.domain == "docs.cursor.com"
        assert config.is_same_domain("https://docs.cursor.com/page")
        assert not config.is_same_domain("https://example.com/page")
        print("✅ Domain validation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Config validation error: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "src/__init__.py",
        "src/config.py",
        "src/models.py",
        "src/constants.py",
        "src/url_manager.py",
        "src/selenium_crawler.py",
        "src/content_parser.py",
        "src/page_sorter.py",
        "src/pdf_generator.py",
        "src/logger.py",
        "src/error_handler.py",
        "tests/__init__.py",
        "tests/test_models.py",
        "tests/test_url_manager.py",
        "tests/test_content_parser.py",
        "tests/test_integration.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files present")
        return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("CURSOR DOCUMENTATION CRAWLER - SETUP TEST")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_imports,
        test_models,
        test_config_validation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! The basic setup is working correctly.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run in test mode: python main.py --test")
        print("3. Run full crawl: python main.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())