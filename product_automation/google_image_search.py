"""
Product Image Search and Download.
Uses Google Images via Playwright with persistent Chrome session.
Extracts base64-encoded images directly from the page.
"""

import os
import re
import time
import atexit
import base64
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests as req


class BrowserManager:
    """Manages one persistent Chrome session for Google Images."""

    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None

    def get_page(self):
        if not self.context:
            from playwright.sync_api import sync_playwright

            print("  [Browser] Starting persistent Chrome session...")
            self.playwright = sync_playwright().start()

            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir="chrome_profile",
                headless=False,
                channel="chrome",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = self.context.new_page()

        return self.page

    def close(self):
        try:
            if self.context:
                print("  [Browser] Closing browser...")
                self.context.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.context = None
        self.playwright = None
        self.page = None


_browser_manager = BrowserManager()
atexit.register(_browser_manager.close)


def search_google_image(
    query: str,
    max_results: int = 1,
    timeout: int = 60000,
) -> list[str]:
    """
    Search for product images using Google Images via Playwright.
    Extracts base64-encoded images directly from the page.
    Returns a list of decoded image data (as base64 strings for now).
    """
    print(f"  [Google] Searching images for: {query}")

    page = _browser_manager.get_page()
    page.set_default_timeout(timeout)

    try:
        encoded_query = quote(query, safe='')
        search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"

        page.goto(search_url, wait_until="networkidle", timeout=timeout)

        # If user needs to sign in, wait for them
        if "signin" in page.url.lower() or "consent" in page.url.lower():
            print("  [Google] Sign-in or consent page detected. Waiting for user to complete...")
            page.wait_for_url("**/search?**tbm=isch**", timeout=120000)

        if "sorry" in page.url:
            print("  [Google] CAPTCHA page detected. Please complete the CAPTCHA in the browser window.")
            page.wait_for_url("**/search?**tbm=isch**", timeout=120000)

        time.sleep(2)

        for _ in range(3):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(0.5)

        # Extract base64 images from the page
        images = page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('img').forEach(img => {
                    const src = img.getAttribute('src') || '';
                    if (src.startsWith('data:image')) {
                        const w = img.naturalWidth || img.width;
                        const h = img.naturalHeight || img.height;
                        if (w > 100 && h > 100) {
                            results.push({
                                dataUrl: src,
                                width: w,
                                height: h,
                            });
                        }
                    }
                });
                // Sort by size (largest first)
                results.sort((a, b) => (b.width * b.height) - (a.width * a.height));
                return results;
            }
        """)

        if images:
            print(f"  [Google] Found {len(images)} image(s)")
            # Return data URLs (base64-encoded) - download function will decode them
            return [img['dataUrl'] for img in images[:max_results]]

        print("  [Google] No images found")
        return []

    except Exception as e:
        print(f"  [Google] Search error: {e}")
        return []


def close_browser() -> None:
    """Explicitly close the persistent browser session."""
    _browser_manager.close()


def download_image(url: str, output_dir: Path, filename: str | None = None) -> Path | None:
    """Download an image from a URL or decode a base64 data URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ext = ".jpg"
        filename = f"{timestamp}_{url.split('/')[-1].split('?')[0]}{ext}"
    output_path = output_dir / filename

    # Handle base64 data URLs
    if url.startswith("data:image"):
        try:
            # Parse data URL: data:image/jpeg;base64,/9j/4AAQ...
            header, b64data = url.split(",", 1)
            # Determine extension from header
            ext = ".jpg"
            if "png" in header.lower():
                ext = ".png"
            elif "webp" in header.lower():
                ext = ".webp"

            data = base64.b64decode(b64data)
            if len(data) > 1000:
                # Update filename with correct extension
                output_path = output_path.with_suffix(ext)
                with open(output_path, "wb") as f:
                    f.write(data)
                return output_path
        except Exception as e:
            print(f"  Decode failed: {e}")
        return None

    # Regular HTTP URL
    try:
        r = req.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if r.status_code == 200 and len(r.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return output_path
        else:
            print(f"  Download issue: status={r.status_code}, size={len(r.content)} bytes")
    except Exception as e:
        print(f"  Download failed: {e}")
    return None


def download_images(image_urls: list[str], output_dir: Path, prefix: str = "product") -> list[Path]:
    """Download multiple images from URLs."""
    downloaded: list[Path] = []
    for i, url in enumerate(image_urls):
        print(f"  Downloading image {i + 1}/{len(image_urls)}")
        path = download_image(url, output_dir, f"{prefix}_{i}.jpg")
        if path:
            downloaded.append(path)
            print(f"  Saved: {path.name}")
    return downloaded
