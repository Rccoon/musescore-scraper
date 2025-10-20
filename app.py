import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def scrape_jmuse_svgs(url):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Uncomment for headless operation
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()  # <--- This line maximizes the window to full screen
    svg_sources = set()
    try:
        driver.get(url)
        time.sleep(0.7)  # Shorter initial wait

        scroller = driver.find_element(By.ID, "jmuse-scroller-component")

        last_height = -1
        same_count = 0
        max_same = 8  # Number of unchanged scrolls before assuming we're done

        # First, scroll by a small amount (simulate a slight arrow down)
        scroller.click()
        scroller.send_keys(Keys.ARROW_DOWN)
        time.sleep(1.0)  # Give time for new image to load

        while True:
            # Collect SVGs currently visible
            imgs = scroller.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src")
                if src and "svg" in src.lower():
                    svg_sources.add(src)

            # Scroll the scroller by sending PAGE_DOWN
            scroller.send_keys(Keys.PAGE_DOWN)
            time.sleep(1.4)  # Longer wait after each scroll for lazy-loading

            # Check if we've reached the bottom by looking at scrollTop
            current_height = driver.execute_script("return arguments[0].scrollTop", scroller)
            if current_height == last_height:
                same_count += 1
                if same_count >= max_same:
                    break
            else:
                same_count = 0
            last_height = current_height

        return list(svg_sources)
    finally:
        driver.quit()

def main():
    print("Enter musescore url (type 'exit' or Ctrl-C to quit).")
    while True:
        try:
            cmd = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if cmd.lower() in ("exit", "quit"):
            break
        if not cmd:
            continue

        svg_sources = scrape_jmuse_svgs(cmd)
        if svg_sources:
            print(svg_sources)
        else:
            print("No SVG images found.")

if __name__ == "__main__":
    main()