from pathlib import Path
from os import PathLike
import tempfile

from curl_cffi import requests
from PyPDF2 import PdfMerger
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg


def _download_svg(url, session=None):
    if session is None:
        session = requests.Session(impersonate="chrome")
    response = session.get(url)
    response.raise_for_status()
    return response.content


def _svg_to_pdf(svg_bytes, svg_path, pdf_path):
    svg_path.write_bytes(svg_bytes)

    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        raise ValueError(f"Failed to parse SVG: {svg_path.name}")
    pdf_canvas = canvas.Canvas(str(pdf_path), pagesize=(drawing.width, drawing.height))
    renderPDF.draw(drawing, pdf_canvas, 0, 0)
    pdf_canvas.showPage()
    pdf_canvas.save()


def combine_svgs_to_pdf(svg_sources, output_pdf: str | PathLike = "combined.pdf"):
    """Convert each SVG to a PDF page and merge into one file.

    Each item may be raw SVG bytes (already downloaded) or a URL to fetch.
    """
    pdf_paths = []

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)

        for idx, source in enumerate(svg_sources):
            svg_path = tempdir / f"page_{idx}.svg"
            pdf_path = tempdir / f"page_{idx}.pdf"

            svg_bytes = source if isinstance(source, bytes) else _download_svg(source)
            _svg_to_pdf(svg_bytes, svg_path, pdf_path)
            pdf_paths.append(pdf_path)

        merger = PdfMerger()
        for path in pdf_paths:
            merger.append(str(path))
        merger.write(str(output_pdf))
        merger.close()

    print(f"Combined PDF saved as {output_pdf}")
