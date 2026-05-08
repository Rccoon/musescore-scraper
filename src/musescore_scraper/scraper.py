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


def _extract_score_id(url):
    match = _SCORE_ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"Could not extract score ID from URL: {url}")
    return match.group(1)


def _create_session(referer=None):
    # Use the latest version of Chrome impersonation
    session = requests.Session(impersonate="chrome124") 
    
    headers = {
        "authority": "musescore.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    if referer:
        headers["Referer"] = referer
        headers["sec-fetch-site"] = "same-origin"

    session.headers.update(headers)
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


def scrape_svg_urls(url):
    return _try_api_strategy(url)
