import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_jmuse_images(url):
    """
    Uses Selenium to find the div with id 'jmuse-scroller-component', scrolls through its inner divs,
    and scrapes the src attribute of any <img> tag found inside each inner div.

    Args:
        url (str): The URL of the page to scrape.

    Returns:
        List[str]: List of image src URLs scraped from the jmuse-scroller-component divs.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    image_sources = []

    try:
        driver.get(url)
        time.sleep(3)  # Wait for JS to load; adjust as needed

        scroller = driver.find_element(By.ID, "jmuse-scroller-component")
        inner_divs = scroller.find_elements(By.XPATH, "./div")
        actions = ActionChains(driver)

        for div in inner_divs:
            # Scroll div into view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", div)
            time.sleep(1)  # Wait for image to load

            try:
                img = div.find_element(By.TAG_NAME, "img")
                src = img.get_attribute("src")
                if src:
                    image_sources.append(src)
            except Exception:
                pass  # No image found in this div

        return image_sources
    finally:
        driver.quit()

def main():
    print("Enter musescore url (type 'exit' or Ctrl-C to quit).")
    while True:
        try:
            cmd = input(">>> ")  # prompt
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        
        cmd = cmd.strip()
        if cmd.lower() in ("exit", "quit"):
            break
        
        if not cmd:
            continue
        
        image_sources = scrape_jmuse_images(cmd)
        if image_sources:
            print(image_sources)

if __name__ == "__main__":
    main()