"""
Full Product Automation Pipeline
Extracts name/price from Excel, searches Google Images, downloads, uploads, generates AI data, and saves to database.
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import requests

# Import modules
from excel_reader import read_excel
from google_image_search import search_google_image, download_images
from ai_service import generate_product_details
from config import config, sanitize_slug
from tui_automation import format_product_data, upload_image_to_backend, _detect_category


def run_full_automation(excel_file: Path, sheet_name: str = "Sheet"):
    """
    Run the complete automation pipeline for products from an Excel file.
    
    Args:
        excel_file: Path to the Excel file
        sheet_name: Sheet name to read from
        
    Returns:
        dict: Summary of results
    """
    print("\n" + "=" * 60)
    print("  FULL PRODUCT AUTOMATION PIPELINE")
    print("=" * 60)
    
    # Load environment
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
    
    # Read Excel
    print(f"\n[1/5] Reading Excel: {excel_file}")
    try:
        products = read_excel(str(excel_file), sheet_name)
        print(f"[OK] Found {len(products)} products")
    except Exception as e:
        print(f"[ERROR] Failed to read Excel: {e}")
        return {"success": 0, "failed": 0, "error": str(e)}
    
    if not products:
        print("[ERROR] No valid products found")
        return {"success": 0, "failed": 0, "error": "No products"}
    
    # Login
    print("\n[2/5] Logging in...")
    from tui_automation import AutoLogin
    auto_login = AutoLogin("monirhasnan@gmail.com")
    auto_login.request_otp()
    otp = input("Enter OTP from email: ").strip()
    
    if not auto_login.login(otp):
        print("[ERROR] Login failed")
        return {"success": 0, "failed": 0, "error": "Login failed"}
    
    config.auth_headers.update({"Authorization": f"Bearer {auto_login.access_token}"})
    print("[OK] Login successful")
    
    # Process products
    print("\n[3/5] Processing products...")
    success_count = 0
    failed_products = []
    
    for i, product in enumerate(products, 1):
        print(f"\n  [{i}/{len(products)}] {product.name}")
        print(f"  Price: {product.price}")
        
        # Step 1: Search Google Images
        print("  Searching Google Images...")
        if not config.SKIP_IMAGES:
            image_urls = search_google_image(product.name, max_results=1)
            
            if image_urls:
                print(f"  Found {len(image_urls)} image(s)")
                
                # Create prefix with product name and price
                prefix = f"{product.name}_{str(product.price)}"
                downloaded = download_images(
                    image_urls,
                    Path(config.DOWNLOAD_DIR),
                    prefix=prefix,
                )
                
                if downloaded:
                    # Upload to backend
                    public_url = upload_image_to_backend(downloaded[0], config.auth_headers)
                    if public_url:
                        print(f"  [OK] Uploaded: {public_url}")
                        product.data["card_photo"] = public_url
                        product.data["img"] = public_url
                    else:
                        print("  [WARN] Upload failed, using default")
                        product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                        product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                else:
                    print("  [WARN] Download failed")
                    product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                    product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            else:
                print("  [WARN] No images found")
                product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        else:
            print("  SKIP images")
            product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        
        # Step 2: Generate AI data
        print("  Generating AI data...")
        if not config.SKIP_AI:
            try:
                ai_data = generate_product_details(product.name)
                print("  [OK] AI data generated")
            except Exception as e:
                print(f"  [ERROR] AI failed: {e}")
                failed_products.append({
                    "name": product.name,
                    "price": product.price,
                    "error": "AI generation failed"
                })
                continue
        else:
            ai_data = {
                "origin_country": product.origin_country,
                "stock": True,
                "expiry_date": "Upto 2028",
            }
        
        # Step 3: Format and post to backend
        print("  Posting to backend...")
        product_data = format_product_data(product, ai_data)
        
        posted = False
        for attempt in range(1, 5):
            try:
                response = requests.post(
                    config.products_api_url,
                    headers=config.auth_headers,
                    json=product_data,
                    timeout=30,
                )
                
                if response.status_code in [200, 201]:
                    print(f"  [OK] Posted (Attempt {attempt})")
                    success_count += 1
                    posted = True
                    break
                else:
                    try:
                        err_body = response.json()
                    except:
                        err_body = response.text[:300]
                    
                    error_msg = str(err_body).lower()
                    is_slug_error = ("slug" in error_msg and ("unique" in error_msg or "constraint" in error_msg or "already exists" in error_msg)) or \
                                    ("unique constraint failed" in error_msg and "products.slug" in error_msg) or \
                                    (response.status_code == 500 and "unique" in error_msg and "slug" in error_msg)
                    
                    if is_slug_error and attempt < 4:
                        import random
                        suffix = f"-{random.randint(100, 999)}"
                        new_slug = product_data["products"]["slug"][:255 - len(suffix)] + suffix
                        print(f"  [WARN] Slug conflict, retrying with: {new_slug}")
                        product_data["products"]["slug"] = new_slug
                        time.sleep(1)
                        continue
                    
                    print(f"  [ERROR] HTTP {response.status_code}: {err_body}")
                    failed_products.append({
                        "name": product.name,
                        "price": product.price,
                        "error": f"HTTP {response.status_code}"
                    })
                    break
            except Exception as e:
                print(f"  [ERROR] {e}")
                failed_products.append({
                    "name": product.name,
                    "price": product.price,
                    "error": str(e)
                })
                break
        
        # Delay between products
        time.sleep(config.PRODUCT_DELAY)
    
    # Save failed products
    if failed_products:
        output_file = Path(__file__).parent / "failed_products.json"
        with open(output_file, "w", encoding="utf-8") as f:
            import json
            json.dump(failed_products, f, indent=2, ensure_ascii=False)
        print(f"\n[!] Saved {len(failed_products)} failed products to: {output_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total:      {len(products)}")
    print(f"  Success:    {success_count}")
    print(f"  Failed:     {len(failed_products)}")
    
    return {
        "success": success_count,
        "failed": len(failed_products),
        "total": len(products)
    }


def main():
    """Main entry point."""
    excel_file = Path("TOK-CERAVE-CETAPHIL.xlsx")
    if not excel_file.exists():
        excel_file = Path(__file__).parent / "TOK-CERAVE-CETAPHIL.xlsx"
    
    if not excel_file.exists():
        print(f"[ERROR] Excel file not found: {excel_file}")
        print("Please set EXCEL_FILE in .env or place the file in this directory")
        sys.exit(1)
    
    result = run_full_automation(excel_file)
    
    sys.exit(0 if result["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
