"""
Configuration loader for TOK Product Automation.
Reads environment variables from .env file and provides typed access.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv


# Load .env file from the script's directory or current working directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to cwd
    load_dotenv()


def sanitize_slug(value: str, length: int = 50) -> str:
    """Sanitize a string for use as a URL slug."""
    value = str(value).strip().lower()
    value = value.replace(" ", "-")
    value = value.replace("/", "-")
    value = value.replace(":", "-")
    value = value.replace(".", "-")
    value = value.replace(",", "-")
    value = value.replace(";", "-")
    value = value.replace("!", "-")
    value = value.replace("?", "-")
    value = value.replace("=", "-")
    value = value.replace("_", "-")
    value = value.strip("-")
    value = value[:length]
    return value


class Config:
    """Typed configuration loaded from environment variables."""

    # --- Backend API ---
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8787")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")

    # --- OpenRouter AI ---
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv(
        "OPENROUTER_MODEL", "deepseek/deepseek-v3.2"
    )

    # --- Excel File ---
    EXCEL_FILE: str = os.getenv("EXCEL_FILE", "products.xlsx")
    EXCEL_SHEET: str = os.getenv("EXCEL_SHEET", "Sheet1")

    # --- Image Download ---
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "./downloads")
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

    # --- Processing ---
    PRODUCT_DELAY: int = int(os.getenv("PRODUCT_DELAY", "2"))
    SKIP_AI: bool = os.getenv("SKIP_AI", "false").lower() == "true"
    SKIP_IMAGES: bool = os.getenv("SKIP_IMAGES", "false").lower() == "true"

    # --- Derived / Computed ---
    @property
    def products_api_url(self) -> str:
        """Full URL for the products post endpoint."""
        return f"{self.API_BASE_URL.rstrip('/')}/api/products/post"

    @property
    def upload_image_url(self) -> str:
        """Full URL for the image upload endpoint."""
        return f"{self.API_BASE_URL.rstrip('/')}/api/products/upload/image"

    @property
    def presigned_url_endpoint(self) -> str:
        """Full URL for the presigned URL endpoint."""
        return f"{self.API_BASE_URL.rstrip('/')}/api/products/upload/presigned"

    @property
    def auth_headers(self) -> dict:
        """Authorization headers for admin API calls."""
        return {
            "Authorization": f"Bearer {self.ADMIN_TOKEN}",
            "Content-Type": "application/json",
        }

    def validate(self) -> list[str]:
        """Check that all required config is present. Returns list of errors."""
        errors: list[str] = []

        if not self.ADMIN_TOKEN:
            errors.append(
                "ADMIN_TOKEN is not set. "
                "Get it from the admin panel cookies and set it in .env"
            )

        if not self.OPENROUTER_API_KEY:
            errors.append(
                "OPENROUTER_API_KEY is not set. "
                "Get your key from https://openrouter.ai/keys"
            )

        excel_path = Path(self.EXCEL_FILE)
        if not excel_path.is_absolute():
            excel_path = Path.cwd() / self.EXCEL_FILE
        if not excel_path.exists():
            errors.append(
                f"Excel file not found: {excel_path}. "
                f"Set EXCEL_FILE in .env to the correct path."
            )

        return errors

    @staticmethod
    def format_product_data(
        product: dict, 
        ai_data: dict
    ) -> dict:
        """Format product data for backend API."""
        return {
            "products": {
                "name": product.get("name", ""),
                "slug": sanitize_slug(product.get("name", "")),
                "brand": product.get("brand", ""),
                "brand_slug": sanitize_slug(product.get("brand", "")),
                "card_photo": product.get("card_photo", ""),
                "img": product.get("img", ""),
                "price": product.get("price", "0"),
                "origin_price": product.get("origin_price", ""),
                "category": product.get("category", ""),
                "category_slug": sanitize_slug(product.get("category", "")),
                "skin_type": product.get("skin_type", ""),
                "skin_concern": product.get("skin_concern", ""),
                "origin_country": product.get("origin_country", "korea"),
                "stock": True,
                "expiry_date": product.get("expiry_date", "Upto 2028"),
            },
            "productDetails": {
                "description": ai_data.get("description", ""),
                "key_ingredient": ai_data.get("key_ingredient", ""),
                "how_to_use": ai_data.get("how_to_use", []),
                "benefits": ai_data.get("benefits", []),
                "sizes": ai_data.get("sizes", ["1"]),
                "photos": [product.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")],
            },
        }


# Singleton
config = Config()
