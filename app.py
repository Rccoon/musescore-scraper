import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import tempfile
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from PyPDF2 import PdfMerger
import re

def extract_score(s):
    match = re.search(r'score_(\d+)', s)
    return int(match.group(1)) if match else float('inf')  # Use inf if score_n is missing


def download_svg_with_headers(svg_url, referer_url=None, cookies=None):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    if referer_url:
        headers["Referer"] = referer_url
    response = requests.get(svg_url, headers=headers, cookies=cookies)
    response.raise_for_status()
    return response.content

def combine_svgs_to_pdf(svg_urls, output_pdf="combined.pdf"):
    # Reverse the list as requested
    svg_urls = list(reversed(svg_urls))
    temp_pdf_files = []

    with tempfile.TemporaryDirectory() as tempdir:
        for idx, svg_url in enumerate(svg_urls):
            # Download SVG
            response = download_svg_with_headers(svg_url=svg_url)

            # Save SVG content to a temporary file
            svg_path = os.path.join(tempdir, f"page_{idx}.svg")
            with open(svg_path, "wb") as f:
                f.write(response)

            # Convert SVG to PDF using svglib and reportlab
            pdf_path = os.path.join(tempdir, f"page_{idx}.pdf")
            drawing = svg2rlg(svg_path)
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(pdf_path, pagesize=(drawing.width, drawing.height))
            renderPDF.draw(drawing, c, 0, 0)
            c.showPage()
            c.save()
            temp_pdf_files.append(pdf_path)

        # Merge PDFs
        merger = PdfMerger()
        for pdf_file in temp_pdf_files:
            merger.append(pdf_file)
        merger.write(output_pdf)
        merger.close()
        print(f"Combined PDF saved as {output_pdf}")

def scrape_jmuse_svgs(url):
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--headless=new")  # Use headless=new for modern headless mode
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_size(1920,1080)
    svg_sources = set()
    try:
        driver.get(url)

        time.sleep(3)  # Wait for initial content to load
      
        scroller = driver.find_element(By.ID, "jmuse-scroller-component")

        # Try clicking the scroller immediately
        scroller.click()

        last_height = -1
        same_count = 0
        max_same = 8

        # Begin scrolling and collecting SVGs as soon as possible
        while True:
            imgs = scroller.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src")
                if src and "svg" in src.lower():
                    svg_sources.add(src)

            scroller.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.6)

            current_height = driver.execute_script("return arguments[0].scrollTop", scroller)
            if current_height == last_height:
                same_count += 1
                if same_count >= max_same:
                    break
            else:
                same_count = 0
            last_height = current_height

        sources =  list(svg_sources)
        sorted_arr = sorted(sources, key=extract_score, reverse=True)

        return sorted_arr
    finally:
        driver.quit()

def main():
    print("Enter file name (without .pdf):")
    while True:
        try:
            filename = input(">>> ").strip()
            if filename.lower() in ("exit", "quit"):
                print("Exiting.")
                break
            if not filename:
                print("Invalid file name. Try again.")
                continue

            print("Enter musescore url (type 'exit' or Ctrl-C to quit).")
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
            # Ensure Scores directory exists
            os.makedirs("./Scores", exist_ok=True)
            output_pdf = os.path.join("Scores", f"{filename}.pdf")
            combine_svgs_to_pdf(svg_sources, output_pdf=output_pdf)
        else:
            print("No SVG images found.")

if __name__ == "__main__":
    main()