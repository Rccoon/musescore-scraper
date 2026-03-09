import os

from musescore_scraper.converter import combine_svgs_to_pdf
from musescore_scraper.scraper import scrape_jmuse_svgs

OUTPUT_DIR = os.path.join(".", "output")


def main():
    """Interactive CLI loop for scraping MuseScore scores to PDF."""
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
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_pdf = os.path.join(OUTPUT_DIR, f"{filename}.pdf")
            combine_svgs_to_pdf(svg_sources, output_pdf=output_pdf)
        else:
            print("No SVG images found.")


if __name__ == "__main__":
    main()
