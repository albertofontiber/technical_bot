"""
Image extractor for Detnov manuals.
Extracts diagram images from PDF pages, saves them locally,
and prepares them for upload to Supabase Storage.
"""

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from PIL import Image

from .pdf_parser import ParsedDocument, PageContent


def render_page_as_image(
    pdf_path: str | Path,
    page_number: int,
    dpi: int = 200,
    max_width: int = 1200,
) -> bytes:
    """Render a specific PDF page as a JPEG image.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-indexed page number.
        dpi: Resolution for rendering.
        max_width: Maximum width in pixels (height scales proportionally).

    Returns:
        JPEG image bytes.
    """
    import fitz

    pdf_path = Path(pdf_path).resolve()
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_number - 1]  # 0-indexed
        zoom = dpi / 72  # 72 is the default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
    finally:
        doc.close()

    # Resize if too wide
    img = Image.open(io.BytesIO(img_bytes))
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # Convert to JPEG for smaller file size
    output = io.BytesIO()
    img = img.convert("RGB")
    img.save(output, format="JPEG", quality=80, optimize=True)
    return output.getvalue()


def extract_diagram_pages(
    parsed: ParsedDocument,
    spanish_pages: list[PageContent],
    min_image_area: int = 50000,
) -> list[int]:
    """Identify pages that contain significant diagrams worth extracting.

    Filters out pages where images are too small (logos, icons).

    Args:
        parsed: The parsed document.
        spanish_pages: List of Spanish-only pages.
        min_image_area: Minimum pixel area to consider an image a diagram.

    Returns:
        List of page numbers with diagrams.
    """
    spanish_page_nums = {p.page_number for p in spanish_pages}
    diagram_pages = []

    for page in parsed.pages:
        if page.page_number not in spanish_page_nums:
            continue

        for img in page.images:
            area = img.width * img.height
            if area >= min_image_area:
                diagram_pages.append(page.page_number)
                break  # One significant image is enough

    return diagram_pages


def save_page_images(
    pdf_path: str | Path,
    pages: list[int],
    output_dir: str | Path,
    product_model: str = "unknown",
    dpi: int = 200,
    max_width: int = 1200,
) -> dict[int, str]:
    """Render and save diagram pages as images.

    Args:
        pdf_path: Path to the PDF file.
        pages: List of page numbers to render.
        output_dir: Directory to save images.
        product_model: Product model for filename prefix.
        dpi: Rendering resolution.
        max_width: Maximum image width.

    Returns:
        Dict mapping page_number -> saved file path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_name = Path(pdf_path).stem
    saved = {}

    for page_num in pages:
        try:
            img_bytes = render_page_as_image(pdf_path, page_num, dpi, max_width)

            filename = f"{product_model}_{pdf_name}_p{page_num:03d}.jpg"
            # Sanitize filename
            filename = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
            filepath = output_dir / filename

            filepath.write_bytes(img_bytes)
            saved[page_num] = str(filepath)
        except Exception as e:
            logger.warning(f"Failed to render page {page_num}: {e}")

    return saved


if __name__ == "__main__":
    import sys
    from .pdf_parser import parse_pdf
    from .language_filter import filter_spanish_pages

    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.image_extractor <pdf_path>")
        sys.exit(1)

    parsed = parse_pdf(sys.argv[1])
    spanish = filter_spanish_pages(parsed)
    diag_pages = extract_diagram_pages(parsed, spanish)

    print(f"Document: {parsed.file_name}")
    print(f"Diagram pages: {len(diag_pages)} / {len(spanish)} Spanish pages")
    print(f"Pages with diagrams: {diag_pages[:20]}...")

    if diag_pages:
        saved = save_page_images(
            sys.argv[1], diag_pages[:3], "./extracted_images",
            product_model="test",
        )
        for pn, path in saved.items():
            print(f"  Saved page {pn}: {path}")
