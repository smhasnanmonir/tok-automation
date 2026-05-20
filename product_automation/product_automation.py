"""
Main automation script for TOK Product Automation.
This script:
1. Reads product data from an Excel file
2. Searches Google for product images
3. Downloads the images
4. Generates product details using AI (OpenRouter)
5. Posts the product to the backend

Usage:
    python product_automation.py              # CLI mode
    python tui_automation.py                  # TUI mode with auto-login
"""

import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any

from excel_reader import ProductRow, read_excel
from google_image_search import search_google_image, download_images
from ai_service import generate_product_details, AIError
from config import config


def sanitize_slug(value: str, length: int = 50) -> str:
    """
    Sanitize a string for use as a URL slug.
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters
    - Truncate to max length
    """
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


def format_product_data(product: ProductRow, ai_data: dict[str, Any]) -> dict:
    """
    Format product data for the backend API.
    """
    return {
        "products": {
            "name": product.name,
            "slug": sanitize_slug(product.name),
            "brand": product.brand,
            "brand_slug": sanitize_slug(product.brand),
            "card_photo": "",  # Will be set after image download
            "img": "",  # Will be set after image download
            "price": product.price,
            "origin_price": product.origin_price,
            "category": product.category,
            "category_slug": sanitize_slug(product.category),
            "skin_type": product.skin_type,
            "skin_concern": product.skin_concern,
            "origin_country": product.origin_country,
            "stock": True,
            "expiry_date": product.data.get("expiry_date", "Upto 2028"),
        },
        "productDetails": {
            "description": ai_data.get("description", ""),
            "key_ingredient": ai_data.get("key_ingredient", ""),
            "how_to_use": ai_data.get("how_to_use", []),
            "benefits": ai_data.get("benefits", []),
            "sizes": ai_data.get("sizes", ["1"]),
            "photos": [product.data.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")],
        },
    }


def process_product(product: ProductRow) -> tuple[dict | None, bool]:
    """
    Process a single product:
    1. Search Google for images
    2. Download images
    3. Generate AI data
    4. Format and return product data

    Returns:
        Tuple of (product_data, success)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {product.name}")
    print(f"{'='*60}")

    # Step 1: Search Google for images
    if not config.config.SKIP_IMAGES:
        print(f"\n🔍 Searching Google Images for: {product.name}")
        image_urls = search_google_image(product.name, max_results=1)

        if image_urls:
            print(f"  Found {len(image_urls)} image(s)")
            # Download the first image
            downloaded = download_images(
                image_urls,
                Path(config.config.DOWNLOAD_DIR),
                prefix=product.name,
            )
            if downloaded:
                product.data["card_photo"] = str(downloaded[0])
                print(f"  ✓ Downloaded: {downloaded[0].name}")
            else:
                print("  ✗ Failed to download any image")
        else:
            print("  ⚠ No images found, skipping image download")
            product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
    else:
        print("\n⏭ Skipping image search (SKIP_IMAGES is true)")
        product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"

    # Step 2: Generate AI data
    if not config.config.SKIP_AI:
        print(f"\n🤖 Generating product details with AI...")
        try:
            ai_data = generate_product_details(product.name)
            print(f"  ✓ AI data generated successfully")
        except AIError as e:
            print(f"  ⚠ AI generation failed: {e}")
            # Return default data if AI fails
            return format_product_data(product, {
                "origin_country": product.origin_country,
                "stock": True,
                "expiry_date": "Upto 2028",
                "description": f"High-quality {product.name} offering premium skincare benefits.",
                "key_ingredient": "Premium ingredients",
                "how_to_use": ["Cleanse skin", "Apply product", "Massage gently"],
                "benefits": ["Hydrates skin", "Improves texture", "Enhances glow"],
                "skin_type": "All",
                "skin_concern": "All",
                "sizes": ["1"],
            })
        except Exception as e:
            print(f"  ⚠ Unexpected error during AI generation: {e}")
            traceback.print_exc()
            return None, False
    else:
        print("\n⏭ Skipping AI generation (SKIP_AI is true)")
        default_data = {
            "origin_country": product.origin_country,
            "stock": True,
            "expiry_date": "Upto 2028",
            "description": f"High-quality {product.name} offering premium skincare benefits.",
            "key_ingredient": "Premium ingredients",
            "how_to_use": ["Cleanse skin", "Apply product", "Massage gently"],
            "benefits": ["Hydrates skin", "Improves texture", "Enhances glow"],
            "skin_type": "All",
            "skin_concern": "All",
            "sizes": ["1"],
        }
        return format_product_data(product, default_data)

    return None, False


def post_product(product_data: dict) -> bool:
    """
    Post product to the backend API.

    Args:
        product_data: Formatted product data (from format_product_data)

    Returns:
        True if successful, False otherwise
    """
    print(f"\n📤 Posting product to backend...")

    try:
        response = requests.post(
            config.config.products_api_url,
            headers=config.config.auth_headers,
            json=product_data,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        print(f"  ✓ Product posted successfully")
        print(f"    Status: {result.get('message', 'OK')}")

        # Log the response
        print(f"    Response: {result}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Failed to post product: {e}")
        if hasattr(e, "response"):
            try:
                error_data = e.response.json()
                print(f"    Error details: {error_data}")
            except:
                print(f"    Status code: {e.response.status_code}")
        return False
    except Exception as e:
        print(f"  ⚠ Unexpected error posting product: {e}")
        traceback.print_exc()
        return False


def main():
    """
    Main entry point for the automation script.
    """
    print("="*60)
    print("TOK Product Automation")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    # Check configuration
    errors = config.config.validate()
    if errors:
        print("\n❌ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Read Excel file
    products = read_excel(config.config.EXCEL_FILE, config.config.EXCEL_SHEET)

    if not products:
        print("\n⚠ No valid products found in Excel file.")
        print(f"  File: {config.config.EXCEL_FILE}")
        print(f"  Sheet: {config.config.EXCEL_SHEET}")
        sys.exit(1)

    print(f"\n📊 Found {len(products)} product(s) to process")

    # Process each product
    success_count = 0
    failed_count = 0

    for i, product in enumerate(products, start=1):
        print(f"\n[{i}/{len(products)}] Processing product")

        try:
            # Process the product
            product_data, success = process_product(product)

            if product_data is None:
                print(f"  ✗ Skipped: No product data generated")
                failed_count += 1
                continue

            # Post to backend
            if post_product(product_data):
                success_count += 1
            else:
                failed_count += 1

            # Wait before next product
            if i < len(products):
                time.sleep(config.config.PRODUCT_DELAY)

        except Exception as e:
            print(f"  ✗ Error processing product: {e}")
            traceback.print_exc()
            failed_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Processing Complete")
    print(f"{'='*60}")
    print(f"Total products: {len(products)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Completed at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
