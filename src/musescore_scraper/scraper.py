import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from curl_cffi import requests

_SCORE_ID_PATTERN = re.compile(r"/scores/(\d+)")
_JS_BUNDLE_PATTERN = re.compile(
    r'(?:href|src)=["\'](https://musescore\.com/static/public/build/[^"\']+\.js)["\']'
)
_SECRET_PATTERN = re.compile(r'"([^"]+)"\)\.substr\(0,4\)')
_PAGE_COUNT_PATTERN = re.compile(r"of (\d+) pages")

# Current secret baked into MuseScore's JS bundle: md5(id + type + index + secret)
_FALLBACK_SECRET = "vu"

_PROFILE_DIR = Path.home() / ".cache" / "musescore-scraper" / "browser"
_CHALLENGE_TIMEOUT = 60
_CHUNK = 16
_MAX_PAGES = 500
_DOWNLOAD_WORKERS = 8


class ScrapeError(Exception):
    """Raised when a score cannot be scraped."""


def _extract_score_id(url):
    match = _SCORE_ID_PATTERN.search(url)
    if not match:
        raise ScrapeError(f"Could not extract score ID from URL: {url}")
    return match.group(1)


def _auth_token(score_id, file_type, index, secret):
    raw = f"{score_id}{file_type}{index}{secret}"
    return hashlib.md5(raw.encode()).hexdigest()[:4]


def _extract_page_count(html):
    counts = {int(n) for n in _PAGE_COUNT_PATTERN.findall(html)}
    return max(counts) if counts else None


def _default_browser_registry_dir():
    """Return the browser cache dir where 'patchright install' puts browsers.

    Mirrors the driver's defaultRegistryDirectory computation so the frozen
    (PyInstaller) binary looks in the same place the install put them.
    """
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return str(Path(local) / "ms-playwright")
    if sys.platform == "darwin":
        return str(Path.home() / "Library" / "Caches" / "ms-playwright")
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return str(Path(cache) / "ms-playwright")


def _ensure_browser_registry_dir():
    """Make a frozen app look for Chromium in the real browser cache.

    On a PyInstaller build patchright forces PLAYWRIGHT_BROWSERS_PATH=0, which
    makes it search inside the bundle for a browser that is never shipped
    there. Pointing it back at the installed cache fixes that, unless the user
    has already chosen an explicit location.
    """
    if getattr(sys, "frozen", False) and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _default_browser_registry_dir()


def _load_playwright():
    _ensure_browser_registry_dir()
    try:
        from patchright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on install state
        raise ScrapeError(
            "patchright is not installed. Install dependencies with:\n"
            "  pip install .\n"
            "  patchright install chromium"
        ) from exc
    return sync_playwright


def _launch_context(playwright):
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR),
            channel="chromium",
            headless=False,
            no_viewport=True,
        )
    except Exception as exc:
        missing = "Executable doesn't exist" in str(exc)
        hint = (
            "Run 'patchright install chromium' to download it."
            if missing
            else "A visible desktop session is required; the browser cannot run headless."
        )
        raise ScrapeError(f"Could not launch Chromium: {exc}\n{hint}") from exc


def _wait_for_score_page(page):
    """Block until MuseScore's bot walls are cleared and the score page renders."""
    deadline = time.time() + _CHALLENGE_TIMEOUT
    while time.time() < deadline:
        time.sleep(1.0)
        try:
            title = page.title()
            html = page.content()
        except Exception:
            continue  # page is mid-navigation
        if "just a moment" not in title.lower() and len(html) > 50_000:
            return html
    raise ScrapeError(
        "Timed out waiting for the score page (Cloudflare/DataDome challenge "
        "was not solved). Try again, or open the score once in the browser window."
    )


def _extract_secret(page, html):
    for js_url in _JS_BUNDLE_PATTERN.findall(html):
        try:
            source = page.evaluate("async u => (await fetch(u)).text()", js_url)
        except Exception:
            continue
        match = _SECRET_PATTERN.search(source)
        if match:
            return match.group(1)
    return _FALLBACK_SECRET


_JMUSE_JS = """
async ([scoreId, jobs]) => {
    return await Promise.all(jobs.map(async ([index, token]) => {
        try {
            const res = await fetch(
                `/api/jmuse?id=${scoreId}&type=img&index=${index}`,
                { headers: { Authorization: token } }
            );
            return [index, res.status, await res.text()];
        } catch (e) {
            return [index, 0, ""];
        }
    }));
}
"""


def _parse_jmuse(status, body):
    """Return (status, url). A 200 with an unusable body is reported as
    status 0 so callers can retry instead of mistaking it for the end."""
    if status != 200:
        return status, None
    try:
        info = json.loads(body).get("info") or {}
        url = info.get("url")
    except (ValueError, AttributeError):
        return 0, None
    return (200, url) if url else (0, None)


def _fetch_image_urls(page, score_id, secret, indices, attempts=3):
    """Ask the jmuse API for image URLs, in parallel, from inside the browser.

    MuseScore intermittently answers 200 with an empty body when it is
    throttling; those indices are retried rather than treated as the end.
    """
    resolved = {}
    pending = list(indices)
    for attempt in range(attempts):
        if not pending:
            break
        if attempt:
            time.sleep(2 * attempt)
        jobs = [[i, _auth_token(score_id, "img", i, secret)] for i in pending]
        raw = page.evaluate(_JMUSE_JS, [score_id, jobs])

        retry = []
        for index, status, body in raw:
            index = int(index)
            status, url = _parse_jmuse(int(status), body)
            if status == 0:
                retry.append(index)
            else:
                resolved[index] = (status, url)
        pending = retry

    for index in pending:
        resolved[index] = (0, None)
    return resolved


def _download(url):
    """Return SVG bytes, or None if the object does not exist (end of score)."""
    try:
        response = requests.get(url, impersonate="chrome", timeout=60)
    except Exception:
        return None
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.content


def _download_all(urls):
    with ThreadPoolExecutor(max_workers=_DOWNLOAD_WORKERS) as pool:
        return list(pool.map(_download, urls))


def _is_preview_gated(page, score_id, secret, next_index):
    """Detect scores MuseScore truncates to a preview.

    For an ordinary score the jmuse API mints a URL for *any* index, even one
    far past the end. A refusal at the next index means the score itself is
    gated rather than simply finished.
    """
    results = _fetch_image_urls(page, score_id, secret, [next_index])
    status, _ = results.get(next_index, (0, None))
    return status == 404


def _scrape_pages(page, score_id, secret, page_count):
    """Fetch image URLs and download them, a chunk at a time.

    The jmuse API mints a URL for any index, so it can never signal the end of
    a score. The authoritative bound is a 404 from S3, which means downloading
    must be interleaved with fetching rather than done afterwards.
    """
    pages = []
    while len(pages) < _MAX_PAGES:
        start = len(pages)
        size = _CHUNK
        if page_count:
            remaining = page_count - start
            if remaining <= 0:
                break
            size = min(size, remaining)

        batch = range(start, start + size)
        results = _fetch_image_urls(page, score_id, secret, batch)

        urls = []
        for i in batch:
            status, url = results.get(i, (0, None))
            if status == 200 and url:
                urls.append(url)
                continue
            if status == 0 and not pages:
                raise ScrapeError(
                    "MuseScore is throttling requests (no response for page "
                    f"{i + 1}). Wait a few minutes and try again."
                )
            break
        if not urls:
            break

        finished = len(urls) < size
        for content in _download_all(urls):
            if content is None:
                finished = True
                break
            pages.append(content)
            print(f"  Page {len(pages)}", end="\r", flush=True)
        if finished:
            break

    return pages


def scrape_score_pages(url):
    """Return a list of SVG page images (bytes) for a MuseScore score."""
    score_id = _extract_score_id(url)
    sync_playwright = _load_playwright()

    print(f"Score ID: {score_id}")
    print("Opening browser to clear MuseScore's bot protection...")

    with sync_playwright() as playwright:
        context = _launch_context(playwright)
        try:
            page = context.new_page()
            page.goto(url, timeout=60_000, wait_until="domcontentloaded")
            html = _wait_for_score_page(page)

            page_count = _extract_page_count(html)
            print(f"Pages: {page_count if page_count else 'unknown'}")

            secret = _extract_secret(page, html)
            print(f"Auth secret: {secret}")

            print("Fetching pages...")
            pages = _scrape_pages(page, score_id, secret, page_count)
            gated = bool(pages) and _is_preview_gated(
                page, score_id, secret, len(pages)
            )
        finally:
            context.close()

    if not pages:
        raise ScrapeError("No pages could be downloaded for this score.")

    if gated:
        print(
            f"\nWarning: MuseScore only serves {len(pages)} page(s) of this "
            "score.\nIt is limited to a preview; the full score requires a "
            "paid MuseScore account."
        )
    elif page_count and len(pages) < page_count:
        print(
            f"\nWarning: only got {len(pages)} of {page_count} page(s)."
        )

    print(f"Got {len(pages)} page(s).")
    return pages
