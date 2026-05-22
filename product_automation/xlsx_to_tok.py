"""
Import products from a scraped xlsx (name, price, origin_price, image_url, product_url).
Downloads images from URLs, uploads to R2, generates AI details, posts to backend.
"""

import os
import sys
import time
import random
import json
import requests
from pathlib import Path
from typing import Any

import openpyxl
from dotenv import load_dotenv

from tui_automation import (
    PRODUCTION_API_BASE,
    PRODUCTION_ADMIN_API,
    AutoLogin,
    upload_image_to_backend,
    format_product_data,
    _extract_brand,
    _detect_category,
    print_header,
    print_success,
    print_error,
    print_progress,
    get_user_input,
)
from ai_service import generate_product_details
from config import config


def read_scraped_xlsx(filepath: str) -> list[dict[str, Any]]:
    """Read a scraped xlsx with columns: name, price, origin_price, image_url, product_url."""
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    products = []
    for row in rows[1:]:
        if not any(cell for cell in row):
            continue
        item = {}
        for col_idx, h in enumerate(headers):
            if col_idx < len(row):
                val = row[col_idx]
                item[h] = str(val).strip() if val is not None else ""
        if item.get("name") and item.get("price"):
            products.append(item)
    wb.close()
    return products


def download_image_from_url(image_url: str, output_dir: Path, filename: str) -> Path | None:
    """Download an image from a URL and save to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    for e in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if e in image_url.lower():
            ext = e
            break
    out_path = output_dir / f"{filename}{ext}"
    try:
        r = requests.get(image_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }, stream=True)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
    except Exception as e:
        print(f"    Download failed: {e}")
    return None


def process_xlsx_products(xlsx_path: str, auth_headers: dict, skip_ai: bool = False) -> dict:
    """Process all products in the xlsx: download, upload, AI, post."""
    products = read_scraped_xlsx(xlsx_path)
    if not products:
        print_error("No products found in xlsx")
        return {"total": 0, "success": 0, "failed": 0}

    print(f"  Found {len(products)} product(s)")
    success_count = 0
    failed_count = 0
    failed_list = []
    download_dir = Path(config.DOWNLOAD_DIR)

    for i, prod in enumerate(products, 1):
        name = prod.get("name", "")
        price = prod.get("price", "0")
        image_url = prod.get("image_url", "")
        origin_price = prod.get("origin_price", "")

        print_progress(i, len(products), f"Processing: {name}")

        # 1. Download image from URL
        img_path = None
        if image_url and not config.SKIP_IMAGES:
            print(f"  Downloading image...")
            prefix = f"{name}_{price}".replace("/", "-").replace("\\", "-").replace(":", "-")[:80]
            img_path = download_image_from_url(image_url, download_dir, prefix)
            if img_path:
                print(f"    Saved: {img_path.name}")
            else:
                print(f"    Failed to download from: {image_url[:80]}")

        # 2. Upload to backend
        card_photo = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
        if img_path and not config.SKIP_IMAGES:
            public_url = upload_image_to_backend(img_path, auth_headers)
            if public_url:
                card_photo = public_url
                print(f"    Uploaded: {public_url}")
            else:
                print("    Upload failed, using default logo")

        prod["card_photo"] = card_photo
        prod["img"] = card_photo

        # 3. Generate AI data
        if not skip_ai and not config.SKIP_AI:
            print("  Generating AI data...")
            try:
                ai_data = generate_product_details(name)
            except Exception as e:
                print(f"    AI failed: {e}")
                failed_list.append({"name": name, "price": price, "error": str(e)})
                failed_count += 1
                continue
        else:
            ai_data = {
                "origin_country": "korea",
                "stock": True,
                "expiry_date": "Upto 2028",
                "description": f"High-quality {name} for premium skincare.",
                "key_ingredient": "Premium ingredients",
                "how_to_use": ["Cleanse skin", "Apply product", "Massage gently"],
                "benefits": ["Provides hydration", "Improves skin texture", "Enhances glow", "Protects skin"],
                "skin_type": "All",
                "skin_concern": "All",
                "sizes": ["1"],
            }

        # 4. Post to backend
        print("  Posting to backend...")
        prod_obj = type("ProdObj", (), {
            "name": name,
            "price": price,
            "origin_price": origin_price,
            "brand": "",
            "category": "",
            "skin_type": None,
            "skin_concern": None,
            "origin_country": "korea",
            "data": prod,
        })()

        product_data = format_product_data(prod_obj, ai_data)
        original_slug = product_data["products"]["slug"]
        posted = False

        for attempt in range(1, 5):
            try:
                resp = requests.post(
                    config.products_api_url,
                    headers=auth_headers,
                    json=product_data,
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    print(f"    OK Posted (attempt {attempt})")
                    success_count += 1
                    posted = True
                    break
                else:
                    err_body = ""
                    try:
                        err_body = str(resp.json()).lower()
                    except:
                        err_body = resp.text[:300].lower()
                    is_slug = "slug" in err_body and ("unique" in err_body or "constraint" in err_body)
                    if is_slug and attempt < 4:
                        suffix = f"-{random.randint(100, 999)}"
                        product_data["products"]["slug"] = original_slug[:255 - len(suffix)] + suffix
                        print(f"    Slug conflict, retry {attempt + 1}/4")
                        time.sleep(1)
                        continue
                    print(f"    Failed (HTTP {resp.status_code}): {err_body[:200]}")
                    break
            except Exception as e:
                print(f"    Error: {e}")
                break

        if not posted:
            failed_count += 1
            failed_list.append({"name": name, "price": price, "error": "post failed"})

        time.sleep(config.PRODUCT_DELAY)

    if failed_list:
        fail_path = Path(__file__).parent / "failed_products.json"
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failed_list, f, indent=2, ensure_ascii=False)
        print(f"\n  Saved {len(failed_list)} failures to: {fail_path}")

    return {"total": len(products), "success": success_count, "failed": failed_count}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import scraped xlsx products to TOK")
    parser.add_argument("--file", "-f", default=None, help="Path to the scraped xlsx file")
    args = parser.parse_args()

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    print_header("Scraped XLSX to TOK")

    if not args.file:
        parser.print_help()
        sys.exit(1)
    xlsx_path = Path(args.file)
    if not xlsx_path.exists():
        print_error(f"File not found: {xlsx_path}")
        sys.exit(1)

    print(f"  Source: {xlsx_path}")

    # Login
    auto_login = AutoLogin(os.getenv("EMAIL_FOR_OTP", "monirhasnan@gmail.com"))
    while True:
        auto_login.request_otp()
        time.sleep(2)
        otp = get_user_input("Enter OTP from email:", "")
        if not otp or len(otp) < 4:
            print_error("Invalid OTP")
            continue
        if auto_login.login(otp):
            break
        retry = get_user_input("Retry? (y/n):", "y")
        if retry and retry.lower() != "y":
            sys.exit(1)

    auth_headers = {
        "Authorization": f"Bearer {auto_login.access_token}",
        "Content-Type": "application/json",
    }

    skip_ai = os.getenv("SKIP_AI", "false").lower() == "true"
    result = process_xlsx_products(str(xlsx_path), auth_headers, skip_ai)

    print_header("Summary")
    print(f"  Total:  {result['total']}")
    print(f"  OK:     {result['success']}")
    print(f"  Failed: {result['failed']}")


if __name__ == "__main__":
    main()
