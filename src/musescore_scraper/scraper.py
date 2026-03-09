import hashlib
import re

from curl_cffi import requests

_MUSESCORE_API = "https://musescore.com/api/jmuse"
_FALLBACK_SECRET = "9654,4e"

_JS_BUNDLE_PATTERN = re.compile(
    r'(?:href|src)=["\']'
    r"(https://musescore\.com/static/public/build/musescore.*?(?:_es6)?/20[^\"']+\.js)"
    r'["\']'
)
_SECRET_PATTERN = re.compile(r'"([^"]+)"\)\.substr\(0,4\)')
_SCORE_ID_PATTERN = re.compile(r"/scores/(\d+)")
_PAGE_COUNT_PATTERN = re.compile(r'pages(?:&quot;|"):(\d+)')
_IMG_URL_PATTERN = re.compile(r"score_\d+\.(svg|png)")


def _extract_score_id(url):
    match = _SCORE_ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"Could not extract score ID from URL: {url}")
    return match.group(1)


def _create_session(referer=None):
    session = requests.Session(impersonate="chrome")
    if referer:
        session.headers["Referer"] = referer
    return session


def _fetch_page_html(session, score_url):
    try:
        response = session.get(score_url, timeout=10)
    except Exception:
        return None

    if response.status_code != 200:
        return None

    html = response.text
    if "just a moment" in html.lower():
        return None

    return html


def _extract_page_count(html):
    match = _PAGE_COUNT_PATTERN.search(html)
    if match:
        return int(match.group(1))
    return None


def _extract_secret_from_html(session, html):
    for js_url in _JS_BUNDLE_PATTERN.findall(html):
        try:
            js_response = session.get(js_url, timeout=10)
            js_response.raise_for_status()
            match = _SECRET_PATTERN.search(js_response.text)
            if match:
                return match.group(1)
        except Exception:
            continue

    return None


def _auth_token(score_id, file_type, index, secret):
    raw = f"{score_id}{file_type}{index}{secret}"
    return hashlib.md5(raw.encode()).hexdigest()[:4]


def _fetch_image_url(session, score_id, index, secret, referer):
    token = _auth_token(score_id, "img", index, secret)
    try:
        response = session.get(
            _MUSESCORE_API,
            params={"id": score_id, "type": "img", "index": index},
            headers={"Authorization": token, "Referer": referer},
            timeout=10,
        )
    except Exception:
        return None

    if response.status_code in (403, 404):
        return None

    response.raise_for_status()
    data = response.json()
    info = data.get("info")
    if isinstance(info, dict):
        return info.get("url")
    return None


def _try_api_strategy(url):
    score_id = _extract_score_id(url)
    session = _create_session(referer=url)

    print(f"Score ID: {score_id}")
    print("Trying API strategy...")

    html = _fetch_page_html(session, url)
    if not html:
        print("Could not fetch score page (Cloudflare blocked).")
        return []

    page_count = _extract_page_count(html)
    if not page_count:
        print("Could not determine page count from HTML.")
        return []

    print(f"Pages: {page_count}")

    secret = _extract_secret_from_html(session, html)
    if secret:
        print("Found auth secret from JS bundle.")
    else:
        print("Could not extract secret, using fallback.")
        secret = _FALLBACK_SECRET

    print("Fetching page URLs...")
    image_urls = []

    for index in range(page_count):
        img_url = _fetch_image_url(session, score_id, index, secret, url)

        if img_url is None and index == 0 and secret != _FALLBACK_SECRET:
            print("Extracted secret failed, retrying with fallback...")
            secret = _FALLBACK_SECRET
            img_url = _fetch_image_url(session, score_id, index, secret, url)

        if img_url is None:
            print(f"  Page {index + 1}: failed")
            break

        image_urls.append(img_url)
        print(f"  Page {index + 1}/{page_count}")

    return image_urls


def _try_browser_strategy(url):
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync

    score_id = _extract_score_id(url)
    print(f"Score ID: {score_id}")
    print("Launching browser...")

    captured_api_urls = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        stealth_sync(page)

        def handle_response(response):
            resp_url = response.url
            if "/api/jmuse" in resp_url and response.status == 200:
                try:
                    data = response.json()
                    info = data.get("info")
                    if isinstance(info, dict) and info.get("url"):
                        idx_match = re.search(r"index=(\d+)", resp_url)
                        idx = int(idx_match.group(1)) if idx_match else -1
                        captured_api_urls[idx] = info["url"]
                except Exception:
                    pass

            if _IMG_URL_PATTERN.search(resp_url) and response.status == 200:
                idx_match = re.search(r"score_(\d+)\.", resp_url)
                if idx_match:
                    idx = int(idx_match.group(1))
                    if idx not in captured_api_urls:
                        captured_api_urls[idx] = resp_url

        page.on("response", handle_response)

        print("Loading score page (solving Cloudflare)...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        _wait_for_cloudflare(page)

        print("Page loaded. Scrolling to load all pages...")
        _scroll_to_load_all_pages(page)

        page.wait_for_timeout(3000)

        browser.close()

    image_urls = [captured_api_urls[idx] for idx in sorted(captured_api_urls)]
    return image_urls


def _wait_for_cloudflare(page, timeout_ms=30000):
    try:
        page.wait_for_selector(
            "#jmuse-scroller-component, img[src*=score_0]",
            timeout=timeout_ms,
        )
        print("Cloudflare challenge passed.")
    except Exception:
        if "challenge" in page.content().lower():
            print("Cloudflare challenge detected, waiting longer...")
            try:
                page.wait_for_selector(
                    "#jmuse-scroller-component, img[src*=score_0]",
                    timeout=timeout_ms,
                )
                print("Cloudflare challenge passed.")
            except Exception:
                print("Warning: Could not confirm Cloudflare was solved.")
        else:
            print("Page loaded (no Cloudflare challenge detected).")


def _scroll_to_load_all_pages(page):
    scroller = page.query_selector("#jmuse-scroller-component")
    if not scroller:
        print("Warning: Could not find score scroller element.")
        return

    children = scroller.query_selector_all(":scope > div")
    page_count = max(len(children) - 3, 1)
    print(f"  Detected {page_count} pages.")

    for i in range(page_count):
        child_divs = scroller.query_selector_all(":scope > div")
        if i < len(child_divs):
            child_divs[i].scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            print(f"  Page {i + 1}/{page_count}")

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)


def scrape_svg_urls(url):
    image_urls = _try_api_strategy(url)

    if image_urls:
        print(f"API strategy succeeded. Found {len(image_urls)} pages.")
        return image_urls

    print("API strategy returned no results. Falling back to browser...")
    image_urls = _try_browser_strategy(url)

    if image_urls:
        print(f"Browser strategy succeeded. Found {len(image_urls)} pages.")
    else:
        print("Both strategies failed. No pages found.")

    return image_urls
