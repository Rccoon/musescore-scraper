import shutil
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from musescore_scraper.utils import extract_score_page

_CHROME_CANDIDATES = ("google-chrome-stable", "google-chrome")
_CHROMIUM_CANDIDATES = ("chromium", "chromium-browser")

INITIAL_LOAD_DELAY = 3
SCROLL_DELAY = 0.6
MAX_SCROLL_STALLS = 8


def _detect_browser():
    for name in _CHROME_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path, ChromeType.GOOGLE

    for name in _CHROMIUM_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path, ChromeType.CHROMIUM

    raise RuntimeError(
        "Neither Google Chrome nor Chromium was found. "
        "Install one of the following:\n"
        "  Arch:          sudo pacman -S chromium\n"
        "  Debian/Ubuntu: sudo apt install chromium-browser\n"
        "  Fedora:        sudo dnf install chromium\n"
        "  Or install Google Chrome from https://www.google.com/chrome/"
    )


def _create_driver():
    browser_path, chrome_type = _detect_browser()

    options = Options()
    options.binary_location = browser_path
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=chrome_type).install()),
        options=options,
    )
    driver.set_window_size(1920, 1080)
    return driver


def _collect_svg_urls(scroller):
    urls = set()
    for img in scroller.find_elements(By.TAG_NAME, "img"):
        src = img.get_attribute("src")
        if src and "svg" in src.lower():
            urls.add(src)
    return urls


def _scroll_and_collect(driver, scroller):
    svg_urls = set()
    last_scroll_pos = -1
    stall_count = 0

    while True:
        svg_urls |= _collect_svg_urls(scroller)

        scroller.send_keys(Keys.PAGE_DOWN)
        time.sleep(SCROLL_DELAY)

        current_pos = driver.execute_script("return arguments[0].scrollTop", scroller)
        if current_pos == last_scroll_pos:
            stall_count += 1
            if stall_count >= MAX_SCROLL_STALLS:
                break
        else:
            stall_count = 0
        last_scroll_pos = current_pos

    return svg_urls


def scrape_svg_urls(url):
    """Scrape all SVG page URLs from a MuseScore score page, in page order."""
    driver = _create_driver()

    try:
        driver.get(url)
        time.sleep(INITIAL_LOAD_DELAY)

        scroller = driver.find_element(By.ID, "jmuse-scroller-component")
        scroller.click()

        svg_urls = _scroll_and_collect(driver, scroller)
        return sorted(svg_urls, key=extract_score_page)
    finally:
        driver.quit()
