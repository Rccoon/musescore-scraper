import shutil
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from musescore_scraper.utils import extract_score

# Browser binary candidates in order of preference.
_CHROME_CANDIDATES = ("google-chrome-stable", "google-chrome")
_CHROMIUM_CANDIDATES = ("chromium", "chromium-browser")


def _detect_browser():
    """Detect whether Chrome or Chromium is installed.

    Returns a tuple of (binary_path, chrome_type) where chrome_type is
    a ChromeType enum value for webdriver-manager.

    Raises RuntimeError if neither is found.
    """
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


def scrape_jmuse_svgs(url):
    """Scrape SVG image URLs from a MuseScore score page.

    Launches a headless Chrome/Chromium browser, navigates to the given URL,
    scrolls through the score to collect all SVG image URLs, and
    returns them sorted by score page number.
    """
    browser_path, chrome_type = _detect_browser()

    chrome_options = Options()
    chrome_options.binary_location = browser_path
    chrome_options.page_load_strategy = "eager"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=chrome_type).install()),
        options=chrome_options,
    )
    driver.set_window_size(1920, 1080)
    svg_sources = set()

    try:
        driver.get(url)
        time.sleep(3)

        scroller = driver.find_element(By.ID, "jmuse-scroller-component")
        scroller.click()

        last_height = -1
        same_count = 0
        max_same = 8

        while True:
            imgs = scroller.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src")
                if src and "svg" in src.lower():
                    svg_sources.add(src)

            scroller.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.6)

            current_height = driver.execute_script(
                "return arguments[0].scrollTop", scroller
            )
            if current_height == last_height:
                same_count += 1
                if same_count >= max_same:
                    break
            else:
                same_count = 0
            last_height = current_height

        sources = list(svg_sources)
        sorted_arr = sorted(sources, key=extract_score, reverse=True)
        return sorted_arr
    finally:
        driver.quit()
