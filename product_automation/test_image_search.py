"""
Test script for image search and download via Playwright + Google Images.

Usage:
    python test_image_search.py                         # Run all test products
    python test_image_search.py --query "COSRX Snail Mucin essence"
    python test_image_search.py --save                  # Download images to disk
    python test_image_search.py --save --save-dir ./test_images
    python test_image_search.py --max-results 3
    python test_image_search.py --verbose
"""

import sys
import time
import argparse
import traceback
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from google_image_search import search_google_image, download_images
except ImportError as e:
    print(f"[IMPORT ERROR] {e}")
    sys.exit(1)


TEST_PRODUCTS = [
    "CeraVe Moisturizing Cream skincare",
    "Cetaphil Gentle Skin Cleanser skincare",
    "The Ordinary Niacinamide 10% Zinc 1% serum",
    "Moisturizing Cream skincare",
    "Vitamin C Brightening Cream skincare",
    "Sunscreen SPF 50 skincare",
    "COSRX Snail Mucin 96% Power Repairing Essence",
    "Some By Mi Centella Asiatica Toner",
    "TIRTIR Milk Skin Toner",
]

MIN_IMAGE_BYTES = 1_000


def validate_url(url: str, timeout: int = 10) -> tuple[bool, int]:
    # Base64 data URLs are valid by definition
    if url.startswith("data:image"):
        try:
            import base64
            header, b64data = url.split(",", 1)
            data = base64.b64decode(b64data)
            return len(data) >= MIN_IMAGE_BYTES, len(data)
        except Exception:
            return False, 0

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        size = int(r.headers.get("content-length", 0))
        if r.status_code == 200 and size >= MIN_IMAGE_BYTES:
            return True, size
        r2 = requests.get(url, headers=headers, timeout=timeout, stream=True)
        chunk = b""
        for c in r2.iter_content(chunk_size=MIN_IMAGE_BYTES * 2):
            chunk += c
            if len(chunk) >= MIN_IMAGE_BYTES:
                break
        r2.close()
        return len(chunk) >= MIN_IMAGE_BYTES, len(chunk)
    except Exception:
        return False, 0


W = 62

def hr(char="="):
    print(char * W)


def short_url(url: str, max_len: int = 65) -> str:
    p = urlparse(url)
    s = f"{p.netloc}{p.path}"
    return s[:max_len] + "..." if len(s) > max_len else s


def format_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} MB"


def run_test(query: str, max_results: int, do_save: bool, save_dir: Path, verbose: bool) -> dict:
    result = {
        "query": query,
        "urls": [],
        "elapsed": 0.0,
        "download_ok": None,
        "download_size": 0,
        "saved_files": [],
        "error": None,
    }
    t0 = time.time()
    try:
        urls = search_google_image(query, max_results=max_results)
        result["elapsed"] = time.time() - t0
        result["urls"] = urls or []

        if result["urls"]:
            ok, size = validate_url(result["urls"][0])
            result["download_ok"] = ok
            result["download_size"] = size

            if do_save:
                saved = download_images(
                    result["urls"],
                    save_dir,
                    prefix=query.replace(" ", "_")[:40],
                )
                result["saved_files"] = [str(p) for p in saved]

    except Exception as e:
        result["elapsed"] = time.time() - t0
        result["error"] = str(e)
        if verbose:
            traceback.print_exc()

    return result


def print_result(result: dict, verbose: bool):
    urls    = result["urls"]
    elapsed = result["elapsed"]
    error   = result["error"]
    dl_ok   = result["download_ok"]
    dl_size = result["download_size"]
    saved   = result["saved_files"]

    if error:
        icon, label = "FAIL", f"ERROR - {error}"
    elif not urls:
        icon, label = "MISS", "no images returned"
    elif dl_ok is False:
        icon, label = "DEAD", f"URL not downloadable ({format_size(dl_size)})"
    elif saved:
        sizes = ", ".join(format_size(Path(f).stat().st_size) for f in saved)
        icon, label = "OK", f"{len(urls)} url(s), {len(saved)} saved [{sizes}]  [{elapsed:.1f}s]"
    elif dl_ok is True:
        icon, label = "OK", f"{len(urls)} image(s), {format_size(dl_size)}  [{elapsed:.1f}s]"
    else:
        icon, label = "OK", f"{len(urls)} image(s)  [{elapsed:.1f}s]"

    print(f"  {icon} {label}")

    show = urls if verbose else urls[:2]
    for i, url in enumerate(show):
        print(f"    [{i+1}] {url if verbose else short_url(url)}")
    if not verbose and len(urls) > 2:
        print(f"    ... +{len(urls) - 2} more")

    for f in saved:
        p = Path(f)
        print(f"         saved: {p.name} ({format_size(p.stat().st_size)})")


def print_summary(results: list[dict]):
    hr()
    print("  SUMMARY")
    hr("-")

    total  = len(results)
    ok     = sum(1 for r in results if r["urls"] and not r["error"] and r["download_ok"] is not False)
    miss   = sum(1 for r in results if not r["urls"] and not r["error"])
    dead   = sum(1 for r in results if r["download_ok"] is False)
    errors = sum(1 for r in results if r["error"])
    saved  = sum(len(r["saved_files"]) for r in results)

    print(f"  Total     : {total}")
    print(f"  [OK]      : {ok}")
    print(f"  [MISS]    : {miss}")
    if dead:   print(f"  [DEAD]    : {dead}")
    if errors: print(f"  [FAIL]    : {errors}")
    if saved:  print(f"  Downloaded: {saved} file(s)")

    pct    = ok / total * 100 if total else 0
    filled = int(pct / 100 * 30)
    bar    = "#" * filled + "-" * (30 - filled)
    print(f"\n  Hit rate  [{bar}]  {pct:.0f}%")

    hr()
    verdict = "PASS" if miss == 0 and errors == 0 else "NEEDS ATTENTION"
    print(f"  Verdict: {verdict}")
    hr()


def main():
    parser = argparse.ArgumentParser(description="Test image search and download via Playwright + Google")
    parser.add_argument("--query",       type=str,            help="Single query to test")
    parser.add_argument("--max-results", type=int, default=1, help="Images per query (default: 1)")
    parser.add_argument("--save",        action="store_true", help="Download images to disk")
    parser.add_argument("--save-dir",    type=str, default="./test_downloads", help="Output directory for saved images")
    parser.add_argument("--verbose",     action="store_true", help="Print full URLs + tracebacks")
    args = parser.parse_args()

    queries = [args.query] if args.query else TEST_PRODUCTS
    save_dir = Path(args.save_dir)

    hr()
    print("  TOK - Image Search Test (Playwright + Google)")
    hr("-")
    print(f"  Queries     : {len(queries)}")
    print(f"  Max results : {args.max_results}")
    print(f"  Save to disk: {'yes -> ' + str(save_dir) if args.save else 'no'}")
    hr()

    all_results = []

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] {query}")
        hr("-")
        result = run_test(query, args.max_results, args.save, save_dir, args.verbose)
        print_result(result, args.verbose)
        all_results.append(result)

        if i < len(queries):
            time.sleep(1.5)

    print_summary(all_results)


if __name__ == "__main__":
    main()
