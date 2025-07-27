"""Constants used throughout the application."""

# HTTP Status Codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500

# File Extensions
PDF_EXTENSION = ".pdf"
HTML_EXTENSION = ".html"

# URL Patterns
YOUTUBE_PATTERNS = [
    "youtube.com/watch",
    "youtube.com/embed",
    "youtu.be/",
    "youtube-nocookie.com"
]

# Content Types
SUPPORTED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png", 
    "image/gif",
    "image/webp",
    "image/svg+xml"
]

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# PDF Settings
DEFAULT_PDF_MARGIN = "1in"
DEFAULT_FONT_SIZE = "12pt"
CODE_FONT_FAMILY = "monospace"
DEFAULT_FONT_FAMILY = "serif"

# Image Processing
MAX_IMAGE_WIDTH = 800
MAX_IMAGE_HEIGHT = 600
IMAGE_QUALITY = 85