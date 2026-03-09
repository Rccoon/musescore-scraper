from pathlib import Path

from musescore_scraper.converter import combine_svgs_to_pdf
from musescore_scraper.scraper import scrape_svg_urls

OUTPUT_DIR = Path("output")


def main():
    while True:
        try:
            print("Enter file name (without .pdf):")
            filename = input(">>> ").strip()
            if filename.lower() in ("exit", "quit"):
                break
            if not filename:
                print("Invalid file name. Try again.")
                continue

            print("Enter MuseScore URL (type 'exit' or Ctrl-C to quit):")
            url = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if url.lower() in ("exit", "quit"):
            break
        if not url:
            continue

        svg_urls = scrape_svg_urls(url)

        if not svg_urls:
            print("No SVG images found.")
            continue

        OUTPUT_DIR.mkdir(exist_ok=True)
        output_pdf = OUTPUT_DIR / f"{filename}.pdf"
        combine_svgs_to_pdf(svg_urls, output_pdf=output_pdf)


if __name__ == "__main__":
    main()
