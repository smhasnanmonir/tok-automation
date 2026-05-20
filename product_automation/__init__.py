"""
TOK Product Automation

Automated system for:
1. Reading product data from Excel
2. Searching Google Images for product photos
3. Downloading images with Playwright
4. Generating product details with AI (OpenRouter)
5. Posting products to TOK backend
"""

from .product_automation import main as cli_main
from .excel_reader import ProductRow, read_excel
from .google_image_search import search_google_image, download_images
from .ai_service import generate_product_details
from .config import config, sanitize_slug, Config
from .tui_automation import main as tui_main

__all__ = [
    "cli_main",
    "tui_main",
    "ProductRow",
    "read_excel",
    "search_google_image",
    "download_images",
    "generate_product_details",
    "config",
    "sanitize_slug",
    "Config",
]
