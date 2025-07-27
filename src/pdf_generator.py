"""PDF generation system for creating documentation PDF."""

import logging
import os
from typing import List
from datetime import datetime
import weasyprint
from weasyprint import HTML, CSS

from .config import Config
from .models import PageContent
from .page_sorter import PageSorter


class PDFGenerator:
    """Generates PDF from processed page content."""
    
    def __init__(self, config: Config):
        """Initialize PDF generator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.page_sorter = PageSorter()
    
    def generate_pdf(self, pages: List[PageContent], output_path: str) -> bool:
        """Generate PDF from page content.
        
        Args:
            pages: List of PageContent objects
            output_path: Path to save PDF
            
        Returns:
            True if PDF generated successfully
        """
        try:
            self.logger.info(f"Generating PDF with {len(pages)} pages")
            
            # Deduplicate pages by URL
            pages = self._deduplicate_pages(pages)
            
            # Sort pages
            sorted_pages = self.page_sorter.sort_pages(pages)
            
            # Create HTML content
            html_content = self._create_html_document(sorted_pages)
            
            # Create CSS styles
            css_content = self._create_css_styles()
            
            # Generate PDF
            html_doc = HTML(string=html_content)
            css_doc = CSS(string=css_content)
            
            # Create output directory if needed
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create directory if path has a directory component
                os.makedirs(output_dir, exist_ok=True)
            
            # Generate PDF
            html_doc.write_pdf(output_path, stylesheets=[css_doc])
            
            self.logger.info(f"PDF generated successfully: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            
            # Try to create a simple fallback PDF
            try:
                self.logger.info("Attempting to create fallback PDF with basic content")
                fallback_html = self._create_fallback_html(sorted_pages, str(e))
                
                html_doc = HTML(string=fallback_html)
                html_doc.write_pdf(output_path)
                
                self.logger.warning(f"Fallback PDF generated: {output_path}")
                return True
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback PDF generation also failed: {fallback_error}")
                return False
    
    def _deduplicate_pages(self, pages: List[PageContent]) -> List[PageContent]:
        """Remove duplicate pages by URL (keep first occurrence)."""
        seen = set()
        deduped = []
        for page in pages:
            # Use final_url if available, otherwise use url
            check_url = page.final_url if page.final_url else page.url
            if check_url not in seen:
                deduped.append(page)
                seen.add(check_url)
        return deduped
    
    def _create_html_document(self, pages: List[PageContent]) -> str:
        """Create complete HTML document from pages.
        
        Args:
            pages: Sorted list of PageContent objects
            
        Returns:
            Complete HTML document string
        """
        # Create table of contents
        toc = self._create_table_of_contents(pages)
        
        # Create page content
        page_content = self._create_page_content(pages)
        
        # Combine into full document
        html_doc = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cursor Documentation</title>
</head>
<body>
    <div class="cover-page">
        <h1>Cursor Documentation</h1>
        <p class="subtitle">Complete Documentation Export</p>
        <p class="date">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p class="source">Source: {self.config.BASE_URL}</p>
        <p class="stats">Total Pages: {len(pages)}</p>
    </div>
    
    <div class="page-break"></div>
    
    <div class="table-of-contents">
        <h1>Table of Contents</h1>
        {toc}
    </div>
    
    <div class="page-break"></div>
    
    <div class="content">
        {page_content}
    </div>
</body>
</html>
"""
        return html_doc
    
    def _create_table_of_contents(self, pages: List[PageContent]) -> str:
        """Create table of contents HTML.
        
        Args:
            pages: List of PageContent objects
            
        Returns:
            Table of contents HTML
        """
        toc_items = []
        
        for i, page in enumerate(pages, 1):
            # Create safe anchor ID
            anchor_id = f"page-{i}"
            
            # Determine indentation level based on URL depth
            url_depth = len([p for p in page.url.split('/') if p]) - 2  # Subtract domain parts
            indent_class = f"toc-level-{min(url_depth, 3)}"  # Max 3 levels
            
            toc_item = f"""
            <div class="toc-item {indent_class}">
                <a href="#{anchor_id}">{page.title}</a>
                <span class="toc-url">{page.url}</span>
            </div>
            """
            toc_items.append(toc_item)
        
        return '\n'.join(toc_items)
    
    def _create_page_content(self, pages: List[PageContent]) -> str:
        """Create main content HTML from pages.
        
        Args:
            pages: List of PageContent objects
            
        Returns:
            Main content HTML
        """
        content_parts = []
        
        for i, page in enumerate(pages, 1):
            anchor_id = f"page-{i}"
            
            # Clean and process page content
            processed_content = self._process_page_html(page.content_html)
            
            page_html = f"""
            <div class="page-section" id="{anchor_id}">
                <div class="page-header">
                    <h1 class="page-title">{page.title}</h1>
                    <p class="page-url">{page.url}</p>
                </div>
                
                <div class="page-content">
                    {processed_content}
                </div>
                
                <div class="page-footer">
                    <hr>
                    <p class="page-stats">
                        Words: {page.word_count} | Images: {page.image_count}
                    </p>
                </div>
            </div>
            
            <div class="page-break"></div>
            """
            
            content_parts.append(page_html)
        
        return '\n'.join(content_parts)
    
    def _process_page_html(self, html_content: str) -> str:
        """Process and clean page HTML for PDF.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Processed HTML content
        """
        if not html_content:
            return "<p>No content available</p>"
        
        # Basic HTML cleaning for PDF
        # Remove any remaining script tags
        html_content = html_content.replace('<script', '<!--script').replace('</script>', '</script-->')
        
        # Ensure all images have proper attributes
        html_content = html_content.replace('<img ', '<img loading="lazy" ')
        
        return html_content
    
    def _create_css_styles(self) -> str:
        """Create CSS styles for PDF.
        
        Returns:
            CSS styles string
        """
        css = """
        @page {
            size: A4;
            margin: 2cm;
            
            @top-center {
                content: "Cursor Documentation";
                font-size: 10pt;
                color: #666;
            }
            
            @bottom-center {
                content: counter(page);
                font-size: 10pt;
                color: #666;
            }
        }
        
        /* Cover page */
        .cover-page {
            text-align: center;
            padding: 4cm 0;
            page-break-after: always;
        }
        
        .cover-page h1 {
            font-size: 36pt;
            color: #2c3e50;
            margin-bottom: 1cm;
        }
        
        .cover-page .subtitle {
            font-size: 18pt;
            color: #7f8c8d;
            margin-bottom: 2cm;
        }
        
        .cover-page .date,
        .cover-page .source,
        .cover-page .stats {
            font-size: 12pt;
            color: #95a5a6;
            margin: 0.5cm 0;
        }
        
        /* Table of contents */
        .table-of-contents {
            page-break-after: always;
        }
        
        .table-of-contents h1 {
            font-size: 24pt;
            color: #2c3e50;
            margin-bottom: 1cm;
            border-bottom: 2pt solid #3498db;
            padding-bottom: 0.5cm;
        }
        
        .toc-item {
            margin: 0.3cm 0;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }
        
        .toc-item a {
            color: #2980b9;
            text-decoration: none;
            font-weight: bold;
        }
        
        .toc-item a:hover {
            text-decoration: underline;
        }
        
        .toc-url {
            font-size: 9pt;
            color: #7f8c8d;
            font-family: monospace;
        }
        
        .toc-level-0 {
            font-size: 12pt;
            margin-left: 0;
        }
        
        .toc-level-1 {
            font-size: 11pt;
            margin-left: 1cm;
        }
        
        .toc-level-2 {
            font-size: 10pt;
            margin-left: 2cm;
        }
        
        .toc-level-3 {
            font-size: 9pt;
            margin-left: 3cm;
        }
        
        /* Page breaks */
        .page-break {
            page-break-before: always;
        }
        
        /* Page sections */
        .page-section {
            margin-bottom: 2cm;
        }
        
        .page-header {
            border-bottom: 1pt solid #bdc3c7;
            padding-bottom: 0.5cm;
            margin-bottom: 1cm;
        }
        
        .page-title {
            font-size: 20pt;
            color: #2c3e50;
            margin: 0 0 0.3cm 0;
        }
        
        .page-url {
            font-size: 10pt;
            color: #7f8c8d;
            font-family: monospace;
            margin: 0;
        }
        
        .page-content {
            line-height: 1.6;
            font-size: 11pt;
        }
        
        .page-footer {
            margin-top: 1cm;
            padding-top: 0.5cm;
            border-top: 1pt solid #ecf0f1;
        }
        
        .page-stats {
            font-size: 9pt;
            color: #95a5a6;
            text-align: right;
            margin: 0;
        }
        
        /* Content styling */
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            color: #2c3e50;
            line-height: 1.6;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 1cm;
            margin-bottom: 0.5cm;
        }
        
        h1 { font-size: 18pt; }
        h2 { font-size: 16pt; }
        h3 { font-size: 14pt; }
        h4 { font-size: 12pt; }
        h5 { font-size: 11pt; }
        h6 { font-size: 10pt; }
        
        p {
            margin: 0.5cm 0;
            text-align: justify;
        }
        
        /* Code styling */
        code {
            font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
            background-color: #f8f9fa;
            padding: 0.1cm 0.2cm;
            border-radius: 0.1cm;
            font-size: 10pt;
        }
        
        pre {
            font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
            background-color: #f8f9fa;
            padding: 0.5cm;
            border-radius: 0.2cm;
            border-left: 3pt solid #3498db;
            overflow-x: auto;
            font-size: 9pt;
            line-height: 1.4;
        }
        
        pre code {
            background: none;
            padding: 0;
        }
        
        /* Lists */
        ul, ol {
            margin: 0.5cm 0;
            padding-left: 1cm;
        }
        
        li {
            margin: 0.2cm 0;
        }
        
        /* Links */
        a {
            color: #2980b9;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* Images */
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0.5cm auto;
            border: 1pt solid #bdc3c7;
            border-radius: 0.2cm;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.5cm 0;
        }
        
        th, td {
            border: 1pt solid #bdc3c7;
            padding: 0.3cm;
            text-align: left;
        }
        
        th {
            background-color: #ecf0f1;
            font-weight: bold;
        }
        
        /* YouTube links */
        .youtube-video {
            background-color: #fff3cd;
            border: 1pt solid #ffeaa7;
            border-radius: 0.2cm;
            padding: 0.5cm;
            margin: 0.5cm 0;
        }
        
        .youtube-link {
            font-weight: bold;
            color: #e74c3c;
        }
        
        /* Blockquotes */
        blockquote {
            border-left: 3pt solid #3498db;
            margin: 0.5cm 0;
            padding-left: 1cm;
            font-style: italic;
            color: #7f8c8d;
        }
        """
        
        return css
    
    def _create_fallback_html(self, pages: List[PageContent], error_message: str) -> str:
        """Create simple fallback HTML when main PDF generation fails.
        
        Args:
            pages: List of PageContent objects
            error_message: Error that caused fallback
            
        Returns:
            Simple HTML document string
        """
        page_summaries = []
        
        for i, page in enumerate(pages, 1):
            # Create simple page summary
            summary = f"""
            <div style="margin-bottom: 2cm; padding: 1cm; border: 1px solid #ccc;">
                <h2>{i}. {page.title}</h2>
                <p><strong>URL:</strong> {page.url}</p>
                <p><strong>Word Count:</strong> {page.word_count}</p>
                <p><strong>Images:</strong> {page.image_count}</p>
                <div style="margin-top: 1cm;">
                    <h3>Full Content:</h3>
                    <div style="white-space: pre-wrap;">{page.content_html}</div>
                </div>
            </div>
            """
            page_summaries.append(summary)
        
        fallback_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cursor Documentation (Fallback)</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2cm; line-height: 1.6; }}
        .error-notice {{ background: #ffebee; border: 1px solid #f44336; padding: 1cm; margin-bottom: 2cm; }}
        .error-notice h2 {{ color: #d32f2f; margin-top: 0; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5cm; }}
        h2 {{ color: #34495e; }}
        h3 {{ color: #7f8c8d; }}
    </style>
</head>
<body>
    <h1>Cursor Documentation (Fallback Version)</h1>
    
    <div class="error-notice">
        <h2>⚠️ Generation Error</h2>
        <p>The full PDF generation encountered an error. This is a simplified fallback version.</p>
        <p><strong>Error:</strong> {error_message}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Document Summary</h2>
    <ul>
        <li><strong>Total Pages:</strong> {len(pages)}</li>
        <li><strong>Source:</strong> {self.config.BASE_URL}</li>
        <li><strong>Total Words:</strong> {sum(p.word_count for p in pages):,}</li>
        <li><strong>Total Images:</strong> {sum(p.image_count for p in pages)}</li>
    </ul>
    
    <h2>Page Contents</h2>
    {''.join(page_summaries)}
    
    <div style="margin-top: 3cm; padding-top: 1cm; border-top: 1px solid #ccc; text-align: center; color: #7f8c8d;">
        <p>This fallback PDF was generated due to an error in the main generation process.</p>
        <p>For the full-featured PDF, please resolve the error and try again.</p>
    </div>
</body>
</html>
"""
        return fallback_html