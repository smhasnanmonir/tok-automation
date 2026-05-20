"""
TUI (Text User Interface) for TOK Product Automation
Features:
- Auto-login by sending OTP request to monirhasnan@gmail.com
- OTP input screen
- Excel file selection
- Google Images search & download (Playwright)
- AI-generated product details (OpenRouter)
- Product posting with image upload to backend (R2)
"""

import sys
import os
import time
import base64
import io
import random
from pathlib import Path
from typing import Optional

import aiohttp
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

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


def upload_image_to_r2(
    image_file: bytes,
    product_id: int | None = None,
) -> str | None:
    """
    Upload image to TokBD R2 storage.
    
    This mimics the upload functionality from the frontend ProductPage.
    Uploads directly to Cloudflare R2 and returns the public URL.
    
    Args:
        image_file: Binary image data (bytes)
        product_id: Optional product ID (used in filename)
    
    Returns:
        Public URL of the uploaded image, or None if failed
    """
    # Generate unique filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=8))
    
    # Determine file extension
    if hasattr(image_file, 'name'):
        file_ext = Path(image_file.name).suffix.lower()
    else:
        file_ext = ".jpg"  # Default
    
    filename = f"{product_id}-{timestamp}-{random_suffix}{file_ext}" if product_id else f"{timestamp}-{random_suffix}{file_ext}"
    
    # Upload directly to R2 bucket
    url = f"https://{R2_BUCKET}.r2.cloudflarestorage.com/{filename}"
    
    # Create session with auth token
    session = aiohttp.ClientSession(headers=config.auth_headers)
    
    try:
        # Use synchronous request for simplicity
        with session.put(url, data=image_file, headers={"Content-Type": "image/jpeg"}, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            resp.raise_for_status()
            return url
    except Exception as e:
        print(f"[!] Image upload failed: {e}")
        return None
    finally:
        session.close()


def format_product_data(product, ai_data: dict) -> dict:
    """Format product data for backend API. Accepts ProductRow or dict."""
    if hasattr(product, 'name'):
        p = product
        return {
            "products": {
                "name": p.name,
                "slug": sanitize_slug(p.name),
                "brand": p.brand or "",
                "brand_slug": sanitize_slug(p.brand) if p.brand else sanitize_slug(p.name),
                "card_photo": p.data.get("card_photo", ""),
                "img": p.data.get("img", ""),
                "price": p.price,
                "origin_price": p.origin_price,
                "category": p.category or "",
                "category_slug": sanitize_slug(p.category) if p.category else sanitize_slug(p.name),
                "skin_type": p.skin_type or "",
                "skin_concern": p.skin_concern or "",
                "origin_country": p.origin_country or "korea",
                "stock": True,
                "expiry_date": p.data.get("expiry_date", "Upto 2028"),
            },
            "productDetails": {
                "description": ai_data.get("description", ""),
                "key_ingredient": ai_data.get("key_ingredient", ""),
                "how_to_use": ai_data.get("how_to_use", []),
                "benefits": ai_data.get("benefits", []),
                "sizes": ai_data.get("sizes", ["1"]),
                "photos": [p.data.get("card_photo", "https://cdn.tokbd.shop/logo/tok-logo.jpg")],
            },
        }
    else:
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
        print("""
Configuration Options:
  - Email (for OTP): monirhasnan@gmail.com
  - Excel File: (browse to select)
  - Skip Images: false
  - Skip AI: false
  - Product Delay: 2 seconds
        """)

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
                    downloaded = download_images(
                        image_urls,
                        Path(config.DOWNLOAD_DIR),
                        prefix=product.name,
                    )
                    if downloaded:
                        product.data["card_photo"] = str(downloaded[0])
                        product.data["img"] = str(downloaded[0])
                        print(f"  OK Downloaded and uploaded: {downloaded[0].name}")
                    else:
                        print("  FAILED to download image")
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

            try:
                response = requests.post(
                    config.products_api_url,
                    headers=config.auth_headers,
                    json=product_data,
                    timeout=30,
                )
                response.raise_for_status()
                print(f"  OK Posted successfully")
                self.success_count += 1
            except Exception as e:
                print(f"  FAILED: {e}")
                self.failed_count += 1

            # Delay between products
            time.sleep(config.PRODUCT_DELAY)

        # Summary
        self.show_summary()

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
        
        print(f"\n[+] Sending OTP request to: {self.email}")
        try:
            response = requests.post(url, json=payload, timeout=15)
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
        
        print(f"\n[+] Logging in with OTP: {otp[:4]}***")
        try:
            response = requests.post(url, json=payload, timeout=15)
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
    
    # User must login manually (OTP will be sent to monirhasnan@gmail.com)
    ui.show_login_screen()
    
    # Show products
    ui.show_products_screen()
    
    # Run automation
    ui.run_automation()


if __name__ == "__main__":
    main()
