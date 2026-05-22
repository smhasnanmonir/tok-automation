"""
TUI (Text User Interface) for TOK Product Automation
Features:
- Auto-login by sending OTP request to monirhasnan@gmail.com
- OTP input screen
- Excel file selection
- Google Images search & download (MechanicalSoup)
- AI-generated product details (OpenRouter)
- Product posting with image upload to backend (R2)
"""

import sys
import os
import re
import time
import base64
import io
import random
import json
from pathlib import Path
from typing import Optional

import aiohttp
import requests
from dotenv import load_dotenv

# Production URLs
PRODUCTION_API_BASE = "https://backend.tokbd.com"
PRODUCTION_ADMIN_API = "https://admin.tokbd.com"

# R2 bucket for image uploads
R2_BUCKET = "tokbd"
R2_REGION = "auto"

# Import modules
from excel_reader import read_excel
from google_image_search import search_google_image, download_images
from ai_service import generate_product_details
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
    print(f"  [TUI] Uploading image {filepath.name} to backend...")
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
                print(f"  [TUI] ✓ Image uploaded successfully: {public_url}")
                return public_url
            else:
                print(f"  [TUI] ⚠ Upload response did not indicate success: {result}")
    except Exception as e:
        print(f"  [TUI] ⚠ Image upload to backend failed: {e}")
    return None


def _extract_brand(product_name: str) -> str:
    """Extract likely brand name from the first word of a product name."""
    parts = product_name.strip().split()
    if parts:
        return parts[0]
    return "Unknown"


def _detect_category(product_name: str) -> str:
    """Detect product category from product name."""
    name_lower = product_name.lower()
    
    # Toners
    if any(kw in name_lower for kw in ['toner', 'mist', 'essence mist', 'setting spray']):
        return "Toner"
    
    # Serums
    if any(kw in name_lower for kw in ['serum', 'ampoule', 'ampoule serum', 'concentrate']):
        return "Serum"
    
    # Creams
    if any(kw in name_lower for kw in ['cream', 'balm', 'barrier cream', 'moisturizer']):
        return "Cream"
    
    # Cleansers
    if any(kw in name_lower for kw in ['cleanser', 'foam', 'gel cleanser', 'wash', 'cleansing']):
        return "Cleanser"
    
    # Oils
    if any(kw in name_lower for kw in ['oil', 'face oil', 'serum oil']):
        return "Oil"
    
    # Sunscreens
    if any(kw in name_lower for kw in ['sunscreen', 'spf', 'sun block', 'sun blocker']):
        return "Sunscreen"
    
    # Masks
    if any(kw in name_lower for kw in ['mask', 'sheet mask', 'sleeping mask']):
        return "Mask"
    
    # Sprays
    if any(kw in name_lower for kw in ['spray', 'setting spray', 'mist']):
        return "Spray"
    
    # Pads
    if any(kw in name_lower for kw in ['pad', 'exfoliating pad', 'toner pad']):
        return "Pad"
    
    # Lip products
    if any(kw in name_lower for kw in ['lip', 'balm', 'gloss', 'stick']):
        return "Lip Care"
    
    # Eye products
    if any(kw in name_lower for kw in ['eye', 'cream', 'serum', 'gels', 'balm']):
        return "Eye Care"
    
    # Exfoliants
    if any(kw in name_lower for kw in ['exfoliat', 'scrub', 'peel', 'acid']):
        return "Exfoliant"
    
    # Masks
    if any(kw in name_lower for kw in ['mask', 'sheet', 'clay mask']):
        return "Mask"
    
    # Default to Skincare
    return "Skincare"


def format_product_data(product, ai_data: dict) -> dict:
    """Format product data for backend API. Accepts ProductRow or dict."""
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

    p_name = product.name if hasattr(product, 'name') else product.get("name", "Product")
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

    if hasattr(product, 'name'):
        p = product
        # Derive brand/category: use product fields, then AI data, then extract from name
        brand = p.brand or ai_data.get("brand", "") or _extract_brand(p.name)
        category = p.category or ai_data.get("category", "") or _detect_category(p.name)
        skin_type = p.skin_type or ai_data.get("skin_type", "All") or "All"
        skin_concern = p.skin_concern or ai_data.get("skin_concern", "All") or "All"
        # Handle skin_type/skin_concern that may be lists from AI
        if isinstance(skin_type, list):
            skin_type = ", ".join(skin_type)
        if isinstance(skin_concern, list):
            skin_concern = ", ".join(skin_concern)
        card_photo = p.data.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")
        img = p.data.get("img", "https://cdn.tokbd.shop/logo/tok-logo.jpg")
        return {
            "products": {
                "name": p.name,
                "slug": sanitize_slug(p.name),
                "brand": brand,
                "brand_slug": sanitize_slug(brand),
                "card_photo": card_photo,
                "img": img,
                "price": p.price,
                "origin_price": p.origin_price,
                "category": category,
                "category_slug": sanitize_slug(category),
                "skin_type": skin_type,
                "skin_concern": skin_concern,
                "origin_country": p.origin_country or ai_data.get("origin_country", "korea") or "korea",
                "stock": True,
                "expiry_date": p.data.get("expiry_date", ai_data.get("expiry_date", "Upto 2028")),
            },
            "productDetails": {
                "description": description,
                "key_ingredient": key_ingredient,
                "how_to_use": how_to_use,
                "benefits": benefits,
                "sizes": sizes,
                "photos": [card_photo],
            },
        }
    else:
        brand = product.get("brand", "") or ai_data.get("brand", "") or _extract_brand(product.get("name", ""))
        category = product.get("category", "") or ai_data.get("category", "") or _detect_category(product.get("name", ""))
        skin_type = product.get("skin_type", "") or ai_data.get("skin_type", "All") or "All"
        skin_concern = product.get("skin_concern", "") or ai_data.get("skin_concern", "All") or "All"
        if isinstance(skin_type, list):
            skin_type = ", ".join(skin_type)
        if isinstance(skin_concern, list):
            skin_concern = ", ".join(skin_concern)
        card_photo = product.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")
        return {
            "products": {
                "name": product.get("name", ""),
                "slug": sanitize_slug(product.get("name", "")),
                "brand": brand,
                "brand_slug": sanitize_slug(brand),
                "card_photo": card_photo,
                "img": product.get("img", card_photo),
                "price": product.get("price", "0"),
                "origin_price": product.get("origin_price", ""),
                "category": category,
                "category_slug": sanitize_slug(category),
                "skin_type": skin_type,
                "skin_concern": skin_concern,
                "origin_country": product.get("origin_country", ai_data.get("origin_country", "korea")) or "korea",
                "stock": True,
                "expiry_date": product.get("expiry_date", ai_data.get("expiry_date", "Upto 2028")),
            },
            "productDetails": {
                "description": description,
                "key_ingredient": key_ingredient,
                "how_to_use": how_to_use,
                "benefits": benefits,
                "sizes": sizes,
                "photos": [card_photo],
            },
        }


def print_header(title: str):
    """Print a styled header."""
    print("\n" + "=" * 60)
    print(f"  {title}".center(60))
    print("=" * 60)


def print_error(message: str):
    """Print an error message."""
    print(f"\n[!] {message}")


def print_success(message: str):
    """Print a success message."""
    print(f"\n[+] {message}")


def print_progress(current: int, total: int, message: str = ""):
    """Print progress bar."""
    if message:
        print(f"  {message}")
    bar_len = 40
    filled = int((current / total) * bar_len)
    bar = "=" * filled + "-" * (bar_len - filled)
    print(f"  [{bar}] {current}/{total}")


def get_user_input(prompt: str, default: Optional[str] = None) -> Optional[str]:
    """Get user input with default value."""
    if default:
        print(f"  {prompt} [{default}]")
    else:
        print(f"  {prompt}")
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None


class ProductAutomationUI:
    """Main TUI for product automation."""

    def __init__(self):
        self.auto_login = AutoLogin("monirhasnan@gmail.com")
        self.access_token: Optional[str] = None
        self.excel_file: Optional[Path] = None
        self.products: list = []
        self.success_count = 0
        self.failed_count = 0
        self.failed_products: list[dict] = []

    def show_welcome(self):
        """Display welcome message."""
        print_header("TOK Product Automation")
        print("""
This tool automates product creation with:
  1. Auto-login (OTP to monirhasnan@gmail.com)
  2. Google Images search & download (Playwright)
  3. AI-generated product details (OpenRouter)
  4. Backend product posting

Production URLs:
  - Backend: https://backend.tokbd.com
  - Admin: https://admin.tokbd.com
        """)

    def show_config_screen(self):
        """Display configuration options."""
        print_header("Configuration")
        print(f"""
Configuration Options:
  - Email (for OTP): monirhasnan@gmail.com
  - Excel File: (browse to select)
  - Skip Images: {config.SKIP_IMAGES}
  - Skip AI: {config.SKIP_AI}
  - Product Delay: {config.PRODUCT_DELAY} seconds
  - Image Search Region: {config.IMAGE_SEARCH_REGION}
        """)

    def show_region_selection(self):
        """Allow user to select the image search region/location."""
        print_header("Image Search Location/Region")
        print(f"Current Region: {config.IMAGE_SEARCH_REGION}")
        print("\nSelect a region/location for product image search:")
        print("  1. United States (us-en) [Default]")
        print("  2. Bangladesh (bd-en)")
        print("  3. India (in-en)")
        print("  4. Worldwide (wt-wt)")
        print("  5. Enter custom region code (e.g. gb-en, ca-en)")
        print("  Press Enter to keep current")
        
        choice = get_user_input("Enter choice (1-5):", "")
        if choice == "1":
            config.IMAGE_SEARCH_REGION = "us-en"
            self.save_region_to_env("us-en")
            print_success("Region set to: United States (us-en)")
        elif choice == "2":
            config.IMAGE_SEARCH_REGION = "bd-en"
            self.save_region_to_env("bd-en")
            print_success("Region set to: Bangladesh (bd-en)")
        elif choice == "3":
            config.IMAGE_SEARCH_REGION = "in-en"
            self.save_region_to_env("in-en")
            print_success("Region set to: India (in-en)")
        elif choice == "4":
            config.IMAGE_SEARCH_REGION = "wt-wt"
            self.save_region_to_env("wt-wt")
            print_success("Region set to: Worldwide (wt-wt)")
        elif choice == "5":
            custom = get_user_input("Enter custom region code:", config.IMAGE_SEARCH_REGION)
            if custom:
                custom_clean = custom.strip().lower()
                config.IMAGE_SEARCH_REGION = custom_clean
                self.save_region_to_env(custom_clean)
                print_success(f"Region set to: {config.IMAGE_SEARCH_REGION}")
        else:
            print(f"Keeping current region: {config.IMAGE_SEARCH_REGION}")

    def save_region_to_env(self, region: str):
        """Save the selected image search region to the .env file."""
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            env_path = Path.cwd() / ".env"
        
        if env_path.exists():
            try:
                content = env_path.read_text(encoding="utf-8")
                if "IMAGE_SEARCH_REGION=" in content:
                    content = re.sub(r"IMAGE_SEARCH_REGION=.*", f"IMAGE_SEARCH_REGION={region}", content)
                else:
                    content = content.rstrip() + f"\n\n# Region/Location for image searches (e.g. us-en, bd-en, wt-wt)\nIMAGE_SEARCH_REGION={region}\n"
                env_path.write_text(content, encoding="utf-8")
            except Exception as e:
                print(f"  [!] Failed to save region to .env: {e}")

    def show_excel_selection(self):
        """Select Excel file - auto-detect from .env or look for TOK-CERAVE-CETAPHIL.xlsx"""
        print_header("Select Excel File")
        
        # Read EXCEL_FILE from .env
        excel_file_name = os.getenv("EXCEL_FILE", "TOK-CERAVE-CETAPHIL.xlsx")
        excel_file = Path(excel_file_name)
        if not excel_file.exists():
            excel_file = Path(__file__).parent / excel_file_name
        
        if excel_file.exists():
            print(f"\n[OK] Found Excel file: {excel_file.name}")
            self.excel_file = excel_file
        else:
            print(f"\n[!] Excel file not found at: {excel_file}")
            print("    Please set EXCEL_FILE in .env or place the file in this directory")

    def show_login_screen(self):
        """Display login screen with OTP input."""
        print_header("Admin Login")
        
        while True:
            # Request OTP
            self.auto_login.request_otp()
            
            print("\n  WAIT for OTP email...")
            time.sleep(2)
            
            otp = get_user_input("Enter OTP from email:", "")
            
            if not otp or len(otp) < 4:
                print_error("Invalid OTP format (must be 4-8 characters)")
                continue
            
            if self.auto_login.login(otp):
                print_success("Login successful!")
                break
            else:
                print_error("Login failed. Try again with a new OTP.")
                retry = get_user_input("Retry with new OTP? (y/n):", "y")
                if retry and retry.lower() != "y":
                    print("  Exiting login flow.")
                    return

    def show_products_screen(self):
        """Display and process products."""
        print_header("Processing Products")

        if not self.excel_file or not self.excel_file.exists():
            print_error("No Excel file selected")
            return

        try:
            print(f"  Reading Excel: {self.excel_file}")
            sheet_name = os.getenv("EXCEL_SHEET", "Sheet")
            self.products = read_excel(str(self.excel_file), sheet_name)
            print(f"[OK] Found {len(self.products)} products")
            print(f"  [INFO] Note: Optional columns will be filled by AI")
        except Exception as e:
            print_error(f"Failed to read Excel: {e}")
            return

        if not self.products:
            print_error("No valid products found")
            return

    def run_automation(self):
        """Run the full automation process."""
        print_header("Running Automation")

        for i, product in enumerate(self.products, 1):
            print_progress(i, len(self.products), f"Processing: {product.name}")

            # Step 1: Search Google Images
            if not config.SKIP_IMAGES:
                print("\n  Searching Google Images...")
                image_urls = search_google_image(product.name, max_results=1)

                if image_urls:
                    print(f"  Found {len(image_urls)} image(s)")
                    
                    # Extract name and price from the clicked thumbnail
                    product_name = product.name
                    product_price = str(product.price) if product.price else "0"
                    
                    downloaded = download_images(
                        image_urls,
                        Path(config.DOWNLOAD_DIR),
                        prefix=f"{product_name}_{product_price}",
                    )
                    if downloaded:
                        # Upload to backend
                        public_url = upload_image_to_backend(downloaded[0], config.auth_headers)
                        if public_url:
                            product.data["card_photo"] = public_url
                            product.data["img"] = public_url
                            print(f"  OK Downloaded and uploaded: {public_url}")
                        else:
                            print("  WARNING: Failed to upload image, using default logo")
                            product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                            product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                    else:
                        print("  FAILED to download image")
                        product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                        product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                else:
                    print("  WARNING: No images found")
                    product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                    product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
            else:
                print("  SKIP images (SKIP_IMAGES=true)")
                product.data["card_photo"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"
                product.data["img"] = "https://cdn.tokbd.shop/logo/tok-logo.jpg"

            # Step 2: Generate AI data
            if not config.SKIP_AI:
                print("\n  Generating AI data...")
                try:
                    ai_data = generate_product_details(product.name)
                    print(f"  OK AI data generated")
                except Exception as e:
                    print(f"  WARNING AI failed: {e}")
                    print("  WARNING Skipping this product")
                    continue
            else:
                print("  SKIP AI (SKIP_AI=true)")

            # Step 3: Post to backend
            print("\n  Posting to backend...")
            product_data = format_product_data(product, ai_data if not config.SKIP_AI else {
                "origin_country": product.origin_country,
                "stock": True,
                "expiry_date": "Upto 2028",
                "description": f"High-quality {product.name}",
                "key_ingredient": "Premium",
                "how_to_use": ["Cleanse", "Apply", "Massage"],
                "benefits": ["Hydrates", "Brightens", "Protects"],
                "skin_type": "All",
                "skin_concern": "All",
                "sizes": ["1"],
            })

            original_slug = product_data["products"]["slug"]
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
                        print(f"  ✓ OK Posted successfully (Attempt {attempt})")
                        self.success_count += 1
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
                            suffix = f"-{random.randint(100, 999)}"
                            new_slug = original_slug[:255 - len(suffix)] + suffix
                            print(f"  ⚠ Slug conflict detected for '{product_data['products']['slug']}'. Retrying with new slug: '{new_slug}' (Attempt {attempt + 1}/4)")
                            product_data["products"]["slug"] = new_slug
                            time.sleep(1)
                            continue
                        
                        print(f"  FAILED (HTTP {response.status_code}): {err_body}")
                        self.failed_count += 1
                        break
                except Exception as e:
                    is_slug_error = False
                    if hasattr(e, "response") and getattr(e, "response") is not None:
                        try:
                            err_body = getattr(e, "response").json()
                        except:
                            err_body = getattr(e, "response").text[:300]
                        error_msg = str(err_body).lower()
                        is_slug_error = ("slug" in error_msg and ("unique" in error_msg or "constraint" in error_msg or "already exists" in error_msg)) or \
                                        ("unique constraint failed" in error_msg and "products.slug" in error_msg)
                    
                    if is_slug_error and attempt < 4:
                        suffix = f"-{random.randint(100, 999)}"
                        new_slug = original_slug[:255 - len(suffix)] + suffix
                        print(f"  ⚠ Slug conflict detected. Retrying with new slug: '{new_slug}' (Attempt {attempt + 1}/4)")
                        product_data["products"]["slug"] = new_slug
                        time.sleep(1)
                        continue
                        
                    print(f"  FAILED: {e}")
                    self.failed_count += 1
                    break

            # Delay between products
            time.sleep(config.PRODUCT_DELAY)

            # Track failed products
            if not posted:
                self.failed_products.append({
                    "name": product.name,
                    "price": product.price,
                    "error": f"Failed after {attempt} attempts"
                })

        # Summary
        self.show_summary()
        self.save_failed_products()

    def save_failed_products(self):
        """Save failed products to a JSON file."""
        if not self.failed_products:
            return
        
        output_file = Path(__file__).parent / "failed_products.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.failed_products, f, indent=2, ensure_ascii=False)
            print(f"\n[!] Saved {len(self.failed_products)} failed products to: {output_file}")
        except Exception as e:
            print(f"\n[!] Failed to save failed products: {e}")

    def show_summary(self):
        """Display final summary."""
        print_header("Processing Complete")
        print(f"  Total: {len(self.products)}")
        print(f"  Success: {self.success_count}")
        print(f"  Failed: {self.failed_count}")
        print(f"  Ended: {time.strftime('%Y-%m-%d %H:%M:%S')}")


class AutoLogin:
    """Handles automatic login with OTP."""

    def __init__(self, email: str = "monirhasnan@gmail.com"):
        self.email = email
        self.otp: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def request_otp(self) -> None:
        """Send OTP request to the specified email."""
        url = f"{PRODUCTION_API_BASE}/api/auth/request-otp"
        payload = {
            "email": self.email,
        }
        headers = {
            "X-Client-Type": "mobile",
            "Content-Type": "application/json"
        }
        
        print(f"\n[+] Sending OTP request to: {self.email}")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                print(f"[+] OTP sent! Check your email inbox.")
            elif response.status_code == 429:
                data = response.json()
                retry_after = data.get("retryAfter", 60)
                print(f"[!] Rate limited. Wait {retry_after}s before requesting again.")
            else:
                print(f"[!] Failed to send OTP (Status: {response.status_code}): {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"[!] Network error: {e}")

    def login(self, otp: str) -> bool:
        """Login with OTP and return access token."""
        url = f"{PRODUCTION_API_BASE}/api/auth/login"
        payload = {
            "email": self.email,
            "otp": otp,
        }
        headers = {
            "X-Client-Type": "mobile",
            "Content-Type": "application/json"
        }
        
        print(f"\n[+] Logging in with OTP: {otp[:4]}***")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 429:
                data = response.json()
                retry_after = data.get("retryAfter", 60)
                print(f"[!] Rate limited. Need to wait {retry_after} seconds before trying again.")
                return False
            if response.status_code not in [200, 201]:
                print(f"[!] Login failed (Status: {response.status_code})")
                print(f"    Response: {response.text}")
                return False
            
            data = response.json()
            
            # Extract tokens from response
            if "accessToken" in data:
                self.access_token = data["accessToken"]
            if "refreshToken" in data:
                self.refresh_token = data["refreshToken"]
            
            print(f"[+] Login successful!")
            if self.access_token:
                print(f"[+] Access Token: {self.access_token[:20]}...")
                # Store token in config so it's used for API calls
                config.ADMIN_TOKEN = self.access_token
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[!] Login failed: {e}")
            return False
        except Exception as e:
            print(f"[!] Error during login: {e}")
            return False


def main():
    """Main entry point."""
    # Load environment
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    # Run UI
    ui = ProductAutomationUI()
    ui.show_welcome()
    ui.show_config_screen()
    ui.show_excel_selection()
    ui.show_region_selection()
    
    # User must login manually (OTP will be sent to monirhasnan@gmail.com)
    ui.show_login_screen()
    
    # Show products
    ui.show_products_screen()
    
    # Run automation
    ui.run_automation()


if __name__ == "__main__":
    main()
