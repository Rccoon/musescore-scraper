import argparse
from pathlib import Path

from musescore_scraper import __version__
from musescore_scraper.converter import combine_svgs_to_pdf
from musescore_scraper.scraper import scrape_svg_urls
from musescore_scraper.utils import is_valid_musescore_url


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download MuseScore sheet music as PDFs"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="output directory (default: current directory)",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving PDFs to: {output_dir}\n")

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

        output_pdf = output_dir / f"{filename}.pdf"

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
