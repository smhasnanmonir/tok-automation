"""
Product Image Search and Download.
Uses Google Images via Playwright with persistent Chrome session.
Clicks thumbnails to open side panel, then captures full-size preview via screenshot.
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

            self.context.on("page", self._block_popups)

            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = self.context.new_page()

        return self.page

    def _block_popups(self, new_page):
        try:
            new_page.close()
        except Exception:
            pass

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


def _capture_panel_image(page, max_wait=15) -> str | None:
    """Capture full-size image from Google's side panel, excluding overlays."""
    # Block Google's UI overlays before capture
    page.evaluate("""
        () => {
            // Hide the 'Search inside image' overlay
            const overlay = document.querySelector('.UWuvyf, .ig2Tkd, .LkIdQb, .RsW3Ke, .RMagM, .KlOMXb, .MjJqGe, .cd29Sd, .kM7Sgc');
            if (overlay) overlay.style.display = 'none';
            
            // Hide any other Google UI elements that might overlay the image
            document.querySelectorAll('[aria-label*="Search inside"], [role="img"], .iLgTbf, .lScUbc, .sjVJQd').forEach(el => {
                el.style.display = 'none';
            });
        }
    """)
    
    for attempt in range(max_wait):
        # Use multiple selectors to find the actual image in the side panel
        selectors = [
            "img.sFlh5c",
            "img[data-width]",
            "img[jsname]",
            "img[loading='lazy']",
            ".Uo74Nc img",
            ".gDS4q img",
        ]
        
        for selector in selectors:
            panel_img = page.query_selector(selector)
            if panel_img:
                # Verify it's a real image with reasonable dimensions
                box = panel_img.bounding_box()
                if box and box["width"] > 80 and box["height"] > 80:
                    png_bytes = panel_img.screenshot(type="png")
                    if png_bytes and len(png_bytes) > 5000:
                        b64 = base64.b64encode(png_bytes).decode("ascii")
                        return f"data:image/png;base64,{b64}"
                time.sleep(0.5)
        time.sleep(1)
    return None


def search_google_image(
    query: str,
    max_results: int = 1,
    timeout: int = 60000,
) -> list[str]:
    """
    Search for product images using Google Images via Playwright.
    Clicks each thumbnail, waits for the side panel to load the larger preview,
    then captures it via element screenshot. Returns base64 data URLs.
    """
    print(f"  [Google] Searching images for: {query}")

    page = _browser_manager.get_page()
    page.set_default_timeout(timeout)

    try:
        encoded_query = quote(query, safe='')
        search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"

        page.goto(search_url, wait_until="networkidle", timeout=timeout)

        if "signin" in page.url.lower() or "consent" in page.url.lower():
            print("  [Google] Sign-in or consent page detected. Waiting for user to complete...")
            page.wait_for_url("**/search?**tbm=isch**", timeout=120000)

        if "sorry" in page.url:
            print("  [Google] CAPTCHA page detected. Please complete the CAPTCHA in the browser window.")
            page.wait_for_url("**/search?**tbm=isch**", timeout=120000)

        time.sleep(2)

        thumb_count = page.evaluate("""
            () => {
                const containers = document.querySelectorAll(
                    'div.ivg-i, div.isv-r, div.bRMDJf, div.Maos1G, div.qC74K'
                );
                const els = [];
                containers.forEach(c => {
                    const img = c.querySelector('img');
                    if (img) els.push(img);
                });
                return els.length;
            }
        """)
        print(f"  [Google] Found {thumb_count} result thumbnail(s)")

        image_data_list: list[str] = []
        to_process = min(max_results, thumb_count)

        for idx in range(to_process):
            print(f"  [Google] Clicking thumbnail {idx + 1}/{to_process}...")

            # Get the image elements and click directly
            clicked_img = page.evaluate(
                """(idx) => {
                    const containers = document.querySelectorAll(
                        'div.ivg-i, div.isv-r, div.bRMDJf, div.Maos1G, div.qC74K'
                    );
                    const els = [];
                    containers.forEach(c => {
                        const img = c.querySelector('img');
                        if (img) els.push(img);
                    });
                    if (idx < els.length) {
                        els[idx].click();
                        return els[idx];
                    }
                    return null;
                }""",
                idx
            )

            if not clicked_img:
                print(f"  [Google] Could not find thumbnail {idx + 1}")
                continue

            print(f"  [Google] Clicked thumbnail {idx + 1}")
            time.sleep(3)

            data_url = _capture_panel_image(page)

            if data_url:
                size_kb = len(base64.b64decode(data_url.split(",", 1)[1])) / 1024
                print(f"  [Google] Captured image {idx + 1} ({size_kb:.0f} KB)")
                image_data_list.append(data_url)
            else:
                print(f"  [Google] Panel image did not load for thumbnail {idx + 1}")

            if idx < to_process - 1:
                page.keyboard.press("Escape")
                time.sleep(1)

        if image_data_list:
            return image_data_list

        print("  [Google] No full-size images found")
        return []

    except Exception as e:
        print(f"  [Google] Search error: {e}")
        return []


def close_browser() -> None:
    _browser_manager.close()


def _ext_from_data_url(data_url: str) -> str:
    if "image/png" in data_url[:30]:
        return ".png"
    if "image/webp" in data_url[:30]:
        return ".webp"
    return ".jpg"


def _ext_from_url(url: str, content_type: str = "") -> str:
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
    if content_type in ext_map:
        return ext_map[content_type]
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ext
    return ".jpg"


def download_image(url: str, output_dir: Path, filename: str | None = None) -> Path | None:
    """Download an image from a URL or decode a base64 data URL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if url.startswith("data:image"):
        try:
            header, b64data = url.split(",", 1)
            ext = _ext_from_data_url(header)
            if not filename:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"img_{timestamp}{ext}"
            output_path = output_dir / filename
            output_path = output_path.with_suffix(ext)

            data = base64.b64decode(b64data)
            if len(data) > 1000:
                with open(output_path, "wb") as f:
                    f.write(data)
                return output_path
        except Exception as e:
            print(f"  Decode failed: {e}")
        return None

    if not filename:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ext = _ext_from_url(url)
        filename = f"img_{timestamp}{ext}"
    output_path = output_dir / filename

    try:
        r = req.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1000:
            content_type = r.headers.get("content-type", "")
            ext = _ext_from_url(url, content_type)
            output_path = output_path.with_suffix(ext)
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
        path = download_image(url, output_dir, f"{prefix}_{i}.png")
        if path:
            downloaded.append(path)
            print(f"  Saved: {path.name}")
    return downloaded
