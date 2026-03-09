import os
import tempfile

import requests
from PyPDF2 import PdfMerger
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg


def download_svg_with_headers(svg_url, referer_url=None, cookies=None):
    """Download an SVG file from a URL with browser-like headers."""
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
    """Download SVGs, convert each to a PDF page, and merge into one PDF.

    The SVG URL list is reversed to correct the collection order from
    the scraper (which collects them in reverse scroll order).
    """
    svg_urls = list(reversed(svg_urls))
    temp_pdf_files = []

    with tempfile.TemporaryDirectory() as tempdir:
        for idx, svg_url in enumerate(svg_urls):
            response = download_svg_with_headers(svg_url=svg_url)

            svg_path = os.path.join(tempdir, f"page_{idx}.svg")
            with open(svg_path, "wb") as f:
                f.write(response)

            pdf_path = os.path.join(tempdir, f"page_{idx}.pdf")
            drawing = svg2rlg(svg_path)

            c = canvas.Canvas(pdf_path, pagesize=(drawing.width, drawing.height))
            renderPDF.draw(drawing, c, 0, 0)
            c.showPage()
            c.save()
            temp_pdf_files.append(pdf_path)

        merger = PdfMerger()
        for pdf_file in temp_pdf_files:
            merger.append(pdf_file)
        merger.write(output_pdf)
        merger.close()
        print(f"Combined PDF saved as {output_pdf}")
