from pathlib import Path

from musescore_scraper.converter import combine_svgs_to_pdf
from musescore_scraper.scraper import scrape_svg_urls
from musescore_scraper.utils import is_valid_musescore_url

OUTPUT_DIR = Path("output")


def main():
    while True:
        try:
            print("Enter MuseScore URL (type 'exit' or Ctrl-C to quit):")
            url = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if url.lower() in ("exit", "quit"):
            break
        if not url:
            continue

        if not is_valid_musescore_url(url):
            print("Invalid MuseScore URL. Expected format:")
            print("  https://musescore.com/user/<id>/scores/<id>")
            continue

        try:
            print("Enter file name (without .pdf):")
            filename = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not filename:
            print("Invalid file name. Try again.")
            continue

        try:
            image_urls = scrape_svg_urls(url)
        except Exception as e:
            print(f"\nError fetching score: {e}")
            continue

        if not image_urls:
            print("No pages found for this score.")
            continue

        OUTPUT_DIR.mkdir(exist_ok=True)
        output_pdf = OUTPUT_DIR / f"{filename}.pdf"

        try:
            combine_svgs_to_pdf(image_urls, output_pdf=output_pdf)
        except Exception as e:
            print(f"\nError creating PDF: {e}")

        try:
            again = input("\nDownload another? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if again not in ("y", "yes"):
            break


if __name__ == "__main__":
    main()
