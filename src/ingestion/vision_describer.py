"""
Vision-based page describer using Claude Vision.
Fallback for pages where PyMuPDF and pdfplumber cannot extract table/diagram content.
Renders the page as an image and sends to Claude to describe structured content.
"""

import base64
import io
from pathlib import Path

import fitz  # PyMuPDF

from ..config import ANTHROPIC_API_KEY


def _get_client():
    from anthropic import Anthropic
    return Anthropic(api_key=ANTHROPIC_API_KEY)


VISION_PROMPT = """Eres un experto en sistemas de protección contra incendios (PCI).
Analiza esta página de un manual técnico y extrae TODO el contenido textual que ves.

Reglas:
- Si hay una TABLA, extrae TODAS las filas y columnas en formato estructurado:
  Columna1 | Columna2 | Columna3
  ---
  valor1 | valor2 | valor3
- Si hay un DIAGRAMA de conexionado, describe las conexiones, bornes, y señales.
- Si hay ESPECIFICACIONES técnicas, lista cada parámetro con su valor.
- NO describas el aspecto visual (colores, layout). Solo extrae la INFORMACIÓN técnica.
- Mantén los nombres técnicos exactos (modelos, códigos, unidades).
- Responde SOLO con el contenido extraído, sin introducciones ni comentarios."""


def render_page_to_image(pdf_path: str | Path, page_number: int, dpi: int = 200) -> bytes:
    """Render a PDF page as a JPEG image.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.
        dpi: Resolution for rendering.

    Returns:
        JPEG image bytes.
    """
    pdf_path = Path(pdf_path).resolve()
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_number - 1]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        return img_bytes
    finally:
        doc.close()


def describe_page_with_vision(
    pdf_path: str | Path,
    page_number: int,
    dpi: int = 200,
) -> str:
    """Send a page image to Claude Vision and get structured text extraction.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.
        dpi: Resolution for rendering.

    Returns:
        Extracted text content from Claude Vision, or empty string on failure.
    """
    try:
        img_bytes = render_page_to_image(pdf_path, page_number, dpi)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": VISION_PROMPT,
                    },
                ],
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Vision error on page {page_number}: {e}")
        return ""


def should_use_vision(
    page_text: str,
    table_text: str,
    has_large_images: bool,
    num_images: int = 0,
    min_text_threshold: int = 200,
) -> bool:
    """Determine if a page should be processed with Claude Vision.

    Heuristic: page has significant image content but insufficient text
    extracted by PyMuPDF + pdfplumber. Also catches pages with multiple
    images where the text might be introductory but tables/diagrams are
    rendered as graphics.

    Args:
        page_text: Text extracted by PyMuPDF.
        table_text: Text extracted by pdfplumber.
        has_large_images: Whether the page has large images (>200x200px).
        num_images: Number of images on the page.
        min_text_threshold: Minimum chars to consider text sufficient.

    Returns:
        True if Vision should be used on this page.
    """
    if not has_large_images:
        return False

    combined_text = (page_text or "") + (table_text or "")
    clean_text = " ".join(combined_text.split())
    text_len = len(clean_text)

    # Case 1: Very little text extracted — clearly needs Vision
    if text_len < min_text_threshold:
        return True

    # Case 2: Multiple images with moderate text — likely has graphical
    # tables/diagrams that weren't extracted as text (e.g., LED status tables)
    if num_images >= 2 and text_len < 1000:
        return True

    return False


def page_has_large_images(page_content) -> bool:
    """Check if a PageContent has images covering significant area.

    Uses bbox info from images to estimate coverage.
    """
    if not page_content.images:
        return False

    # If page has any image > 200x200 pixels, consider it significant
    for img in page_content.images:
        if img.width > 200 and img.height > 200:
            return True
    return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m src.ingestion.vision_describer <pdf_path> <page_number>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_num = int(sys.argv[2])
    print(f"Describing page {page_num} of {pdf_path} with Claude Vision...")
    text = describe_page_with_vision(pdf_path, page_num)
    if text:
        print(text)
    else:
        print("No content extracted.")
