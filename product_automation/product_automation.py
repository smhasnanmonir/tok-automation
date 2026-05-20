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
import random
import traceback
import requests
from pathlib import Path
from datetime import datetime
from typing import Any

from excel_reader import ProductRow, read_excel
from google_image_search import search_google_image, download_images
from ai_service import generate_product_details, AIError
from config import config, sanitize_slug



def upload_image_to_backend(filepath: Path, auth_headers: dict) -> str | None:
    """
    Upload a local image file to the backend product upload API.

    Args:
        filepath: Path to the local image file
        auth_headers: Authorization headers

    Returns:
        The public URL of the uploaded image, or None if failed
    """
    print(f"  📤 Uploading image {filepath.name} to backend...")
    try:
        url = config.upload_image_url
        with open(filepath, "rb") as f:
            files = {"file": (filepath.name, f, "image/jpeg")}
            # Remove Content-Type from headers so requests can generate the boundary automatically
            headers = {k: v for k, v in auth_headers.items() if k.lower() != "content-type"}
            response = requests.post(url, headers=headers, files=files, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("success") and "data" in result and "url" in result["data"]:
                public_url = result["data"]["url"]
                print(f"    ✓ Image uploaded successfully: {public_url}")
                return public_url
            else:
                print(f"    ⚠ Upload response did not indicate success: {result}")
    except Exception as e:
        print(f"    ⚠ Image upload to backend failed: {e}")
    return None


def format_product_data(product: ProductRow, ai_data: dict[str, Any]) -> dict:
    """
    Format product data for the backend API.
    """
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

    description = ai_data.get("description")
    if not description or len(str(description).strip()) < 10:
        description = f"High-quality {product.name} for premium skincare, designed to hydrate and revitalize."
    else:
        description = str(description).strip()

    key_ingredient = ai_data.get("key_ingredient")
    if not key_ingredient or not str(key_ingredient).strip():
        key_ingredient = "Premium ingredients"
    else:
        key_ingredient = str(key_ingredient).strip()

    return {
        "products": {
            "name": product.name,
            "slug": sanitize_slug(product.name),
            "brand": product.brand,
            "brand_slug": sanitize_slug(product.brand),
            "card_photo": product.data.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg"),
            "img": product.data.get("img", "https://cdn.tokbd.shop/logo/tok-logo.jpg"),
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
            "description": description,
            "key_ingredient": key_ingredient,
            "how_to_use": how_to_use,
            "benefits": benefits,
            "sizes": sizes,
            "photos": [product.data.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")],
        },
    }


def process_product(product: ProductRow) -> tuple[dict | None, bool]:
    """
    Process a single product:
    1. Search Google for images
    2. Download and upload images to R2 via the backend
    3. Generate AI data
    4. Format and return product data

    Returns:
        Tuple of (product_data, success)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {product.name}")
    print(f"{'='*60}")

    # Step 1: Search Google for images
    if not config.SKIP_IMAGES:
        query_parts = [product.brand, product.name]
        if product.category:
            query_parts.append(product.category)
        search_query = " ".join(p for p in query_parts if p)
        print(f"\n🔍 Searching images for: {search_query}")
        image_urls = search_google_image(search_query, max_results=1)

        if image_urls:
            print(f"  Found {len(image_urls)} image(s)")
            # Download the first image
            downloaded = download_images(
                image_urls,
                Path(config.DOWNLOAD_DIR),
                prefix=product.name,
            )
            if downloaded:
                # Upload the image to backend and get the public R2 URL
                public_url = upload_image_to_backend(downloaded[0], config.auth_headers)
                if public_url:
                    product.data["card_photo"] = public_url
                    product.data["img"] = public_url
                    print(f"  ✓ Downloaded and uploaded successfully to: {public_url}")
                else:
                    print("  ⚠ Failed to upload image to backend, falling back to default logo")
                    product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                    product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            else:
                print("  ✗ Failed to download any image")
                product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        else:
            print("  ⚠ No images found, skipping image download")
            product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
    else:
        print("\n⏭ Skipping image search (SKIP_IMAGES is true)")
        product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"

    # Step 2: Generate AI data
    if not config.SKIP_AI:
        print(f"\n🤖 Generating product details with AI...")
        try:
            ai_data = generate_product_details(product.name)
            print(f"  ✓ AI data generated successfully")
            return format_product_data(product, ai_data), True
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
            }), True
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
        return format_product_data(product, default_data), True


def post_product(product_data: dict) -> bool:
    """
    Post product to the backend API.

    Args:
        product_data: Formatted product data (from format_product_data)

    Returns:
        True if successful, False otherwise
    """
    print(f"\n📤 Posting product to backend...")

    original_slug = product_data["products"]["slug"]
    
    for attempt in range(1, 5):  # Try up to 4 times (original + 3 retries)
        try:
            response = requests.post(
                config.products_api_url,
                headers=config.auth_headers,
                json=product_data,
                timeout=30,
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"  ✓ Product posted successfully (Attempt {attempt})")
                print(f"    Status: {result.get('message', 'OK')}")
                print(f"    Response: {result}")
                return True

            # If not 200/201, let's check if it's a slug duplicate issue
            error_msg = ""
            status_code = response.status_code
            try:
                error_data = response.json()
                error_msg = str(error_data).lower()
            except:
                error_msg = response.text.lower()

            # Check if it looks like a slug/unique constraint error
            is_slug_error = ("slug" in error_msg and ("unique" in error_msg or "constraint" in error_msg or "already exists" in error_msg)) or \
                            ("unique constraint failed" in error_msg and "products.slug" in error_msg) or \
                            (status_code == 500 and "unique" in error_msg and "slug" in error_msg)
            
            if is_slug_error and attempt < 4:
                suffix = f"-{random.randint(100, 999)}"
                new_slug = original_slug[:255 - len(suffix)] + suffix
                print(f"  ⚠ Slug conflict detected for '{product_data['products']['slug']}'. Retrying with new slug: '{new_slug}' (Attempt {attempt + 1}/4)")
                product_data["products"]["slug"] = new_slug
                time.sleep(1)
                continue
            
            print(f"  ⚠ Failed to post product (HTTP {status_code}): {error_msg}")
            return False

        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Failed to post product on attempt {attempt}: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"    Error details: {error_data}")
                except:
                    print(f"    Status code: {e.response.status_code}")
            
                error_msg = ""
                try:
                    error_msg = str(e.response.json()).lower()
                except:
                    error_msg = e.response.text.lower()
                
                is_slug_error = ("slug" in error_msg and ("unique" in error_msg or "constraint" in error_msg or "already exists" in error_msg)) or \
                                ("unique constraint failed" in error_msg and "products.slug" in error_msg)
                
                if is_slug_error and attempt < 4:
                    suffix = f"-{random.randint(100, 999)}"
                    new_slug = original_slug[:255 - len(suffix)] + suffix
                    print(f"  ⚠ Slug conflict detected. Retrying with new slug: '{new_slug}' (Attempt {attempt + 1}/4)")
                    product_data["products"]["slug"] = new_slug
                    time.sleep(1)
                    continue
            return False
        except Exception as e:
            print(f"  ⚠ Unexpected error posting product on attempt {attempt}: {e}")
            traceback.print_exc()
            return False
            
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
    errors = config.validate()
    if errors:
        print("\n❌ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Read Excel file
    products = read_excel(config.EXCEL_FILE, config.EXCEL_SHEET)

    if not products:
        print("\n⚠ No valid products found in Excel file.")
        print(f"  File: {config.EXCEL_FILE}")
        print(f"  Sheet: {config.EXCEL_SHEET}")
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

            if product_data is None or not success:
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
                time.sleep(config.PRODUCT_DELAY)

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
