"""
Google Image Search and Download using Playwright.
Downloads product images from Google Images search results.
"""

import os
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config import config


def wait_for_captcha(page) -> None:
    """Detect CAPTCHA and wait for user to solve it manually."""
    try:
        content = page.content().lower()
        has_captcha = any(word in content for word in [
            "captcha", "recaptcha", "unusual traffic", "are you a robot",
            "i'm not a robot", "verify you're human", "not a robot",
        ])
        has_captcha_url = "google.com/sorry/" in page.url.lower()

        if has_captcha or has_captcha_url:
            print("\n  [!!] CAPTCHA DETECTED! Google is blocking the request.")
            print("  [!!] The browser window is open and waiting for you.")
            print("  [!!] Please solve the CAPTCHA in the browser window.")
            print("  [!!] After solving, come back here and press Enter to continue...")
            input("  > Press Enter after solving CAPTCHA...")
            time.sleep(2)
            # Check again recursively if there's another CAPTCHA
            new_content = page.content().lower()
            if any(word in new_content for word in ["captcha", "recaptcha", "unusual traffic"]):
                print("  [!!] CAPTCHA still detected. Please try again...")
                wait_for_captcha(page)
    except Exception:
        pass


def search_google_image(
    query: str,
    max_results: int = 3,
    timeout: int = 30000,
) -> list[str]:
    """
    Search for images on Google Images and extract URLs.

    Args:
        query: The search query (product name)
        max_results: Maximum number of image URLs to return
        timeout: Timeout in milliseconds

    Returns:
        List of image URLs
    """
    from urllib.parse import quote_plus
    search_url = f"https://www.google.com/search?tbm=isch&q={quote_plus(query)}"

    image_urls: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.set_default_timeout(timeout)

        try:
            page.goto(search_url, wait_until="networkidle", timeout=timeout)
            time.sleep(2)

            # Check for CAPTCHA and pause if needed
            wait_for_captcha(page)

            # After CAPTCHA, wait for the page to fully reload
            time.sleep(3)
            page.wait_for_load_state("networkidle", timeout=10000)

            # Scroll to trigger lazy-loaded images
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.5)

            # Wait a moment for images to load after scrolling
            time.sleep(2)

            # Click on image thumbnails to get full-size URLs
            # First try: click the first few image elements
            clicked_any = False
            for attempt in range(3):
                try:
                    thumbnails = page.query_selector_all("img.rg_i.Q4LuWd")
                    if len(thumbnails) == 0:
                        thumbnails = page.query_selector_all("img[src*='data:image']")
                    if len(thumbnails) == 0:
                        thumbnails = page.query_selector_all("img")
                    for thumb in thumbnails[:3]:
                        try:
                            thumb.click()
                            time.sleep(1)
                            clicked_any = True
                        except:
                            pass
                    if clicked_any:
                        break
                except:
                    time.sleep(1)

            # Extract image URLs using multiple strategies
            urls = page.evaluate("""
                () => {
                    const urls = new Set();
                    // Strategy 1: direct src attributes
                    document.querySelectorAll('img').forEach(img => {
                        const src = img.getAttribute('src') || img.getAttribute('data-src');
                        if (src && src.startsWith('http') && !src.includes('google') && !src.includes('gstatic')) {
                            urls.add(src);
                        }
                    });
                    // Strategy 2: look for the actual image URL in the lightbox/modal
                    document.querySelectorAll('a[href*="imgurl="]').forEach(a => {
                        const match = a.href.match(/imgurl=([^&]+)/);
                        if (match) urls.add(decodeURIComponent(match[1]));
                    });
                    // Strategy 3: check for high-res images in the page
                    document.querySelectorAll('[srcset]').forEach(el => {
                        const src = el.getAttribute('src');
                        if (src && src.startsWith('http') && !src.includes('google')) urls.add(src);
                    });
                    return Array.from(urls).slice(0, 10);
                }
            """)

            if urls:
                image_urls = [u for u in urls if u.startswith("http") and "gstatic.com" not in u]
                image_urls = image_urls[:max_results]
                if image_urls:
                    print(f"  Found {len(image_urls)} image(s)")

        except PlaywrightTimeout:
            print("  Search timed out, using placeholder")
        except Exception as e:
            print(f"  Search error: {e}")
        finally:
            try:
                browser.close()
            except:
                pass

    return image_urls


def download_image(url: str, output_dir: Path, filename: str | None = None) -> Path | None:
    """
    Download an image from a URL to the specified directory using requests.
    """
    import requests as req

    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ext = ".jpg"
        filename = f"{timestamp}_{url.split('/')[-1].split('?')[0]}{ext}"

    output_path = output_dir / filename

    try:
        r = req.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return output_path
    except Exception as e:
        print(f"  Download failed: {e}")

    return None


def download_images(image_urls: list[str], output_dir: Path, prefix: str = "product") -> list[Path]:
    """
    Download multiple images from URLs.
    """
    downloaded: list[Path] = []

    for i, url in enumerate(image_urls):
        print(f"  Downloading image {i + 1}/{len(image_urls)}")
        path = download_image(url, output_dir, f"{prefix}_{i}.jpg")
        if path:
            downloaded.append(path)
            print(f"  Saved: {path.name}")

    return downloaded
