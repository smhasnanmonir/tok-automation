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


def sanitize_slug(value: str, length: int = 255) -> str:
    """Sanitize a string for use as a URL slug.
    Output matches Zod regex: ^[a-z0-9]+(?:-[a-z0-9]+)*$
    """
    value = str(value).strip().lower()
    # Replace common separators with hyphens
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
    # Remove any character that isn't a-z, 0-9, or hyphen
    value = re.sub(r'[^a-z0-9-]', '', value)
    # Collapse consecutive hyphens into a single hyphen
    value = re.sub(r'-{2,}', '-', value)
    # Strip leading/trailing hyphens
    value = value.strip("-")
    value = value[:length]
    # Ensure we don't end with a trailing hyphen after truncation
    value = value.strip("-")
    return value if value else "product"


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
    IMAGE_SEARCH_REGION: str = os.getenv("IMAGE_SEARCH_REGION", "us-en")


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
        def clean_list(val, default_list):
            if not val:
                return default_list
            if isinstance(val, list):
                res = [str(v).strip() for v in val if str(v).strip()]
                return res if res else default_list
            if isinstance(val, str):
                res = [v.strip() for v in val.split(",") if v.strip()]
                return res if res else default_list
            return default_list

        sizes = clean_list(ai_data.get("sizes"), ["1"])
        how_to_use = clean_list(ai_data.get("how_to_use"), ["Cleanse skin", "Apply product", "Massage gently"])
        benefits = clean_list(ai_data.get("benefits"), ["Provides hydration", "Improves skin texture"])

        p_name = product.get("name", "Product")
        description = ai_data.get("description")
        if not description or len(str(description).strip()) < 10:
            description = f"High-quality {p_name} for premium skincare, designed to hydrate and revitalize."
        else:
            description = str(description).strip()

        key_ingredient = ai_data.get("key_ingredient")
        if not key_ingredient or not str(key_ingredient).strip():
            key_ingredient = "Premium ingredients"
        else:
            key_ingredient = str(key_ingredient).strip()

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
                "description": description,
                "key_ingredient": key_ingredient,
                "how_to_use": how_to_use,
                "benefits": benefits,
                "sizes": sizes,
                "photos": [product.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")],
            },
        }


# Singleton
config = Config()
