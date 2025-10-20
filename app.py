import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
from selenium.webdriver.common.by import By
import requests
import tempfile
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from PyPDF2 import PdfMerger



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

def download_svgs_and_combine_to_pdf(svg_urls, output_pdf="combined.pdf"):
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
            from reportlab.lib.pagesizes import letter

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
    # chrome_options.add_argument("--headless")  # Uncomment for headless operation
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    svg_sources = set()

    try:
        driver.get(url)

        time.sleep(1.5)  # Wait for initial content to load
      
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
            time.sleep(1.4)

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
            download_svgs_and_combine_to_pdf(svg_sources)
        else:
            print("No SVG images found.")

if __name__ == "__main__":
    main()