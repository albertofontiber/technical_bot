"""
PDF Parser for Detnov fire protection manuals.
Extracts text blocks with structure (headings, sections) and images from PDFs using PyMuPDF.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class TextBlock:
    """A block of text extracted from a PDF page."""
    text: str
    page_number: int
    block_index: int
    font_size: float = 0.0
    is_bold: bool = False
    bbox: tuple = ()  # (x0, y0, x1, y1)


@dataclass
class ImageBlock:
    """An image extracted from a PDF page."""
    image_bytes: bytes
    page_number: int
    image_index: int
    width: int = 0
    height: int = 0
    bbox: tuple = ()
    ext: str = "png"


@dataclass
class PageContent:
    """All content from a single PDF page."""
    page_number: int
    text_blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    full_text: str = ""
    table_text: str = ""    # Text extracted by pdfplumber (tables)
    vision_text: str = ""   # Text extracted by Claude Vision (fallback)


@dataclass
class ParsedDocument:
    """A fully parsed PDF document."""
    file_path: str
    file_name: str
    total_pages: int
    pages: list[PageContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tables_enriched: int = 0   # Pages enriched with pdfplumber
    vision_enriched: int = 0   # Pages enriched with Claude Vision


def extract_text_blocks(page: fitz.Page) -> list[TextBlock]:
    """Extract text blocks from a page with font information."""
    blocks = []
    block_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    for block_idx, block in enumerate(block_dict.get("blocks", [])):
        if block.get("type") != 0:  # type 0 = text
            continue

        block_text_parts = []
        max_font_size = 0.0
        has_bold = False

        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    line_text += span["text"]
                    font_size = span.get("size", 0)
                    if font_size > max_font_size:
                        max_font_size = font_size
                    font_name = span.get("font", "").lower()
                    if "bold" in font_name or "negrita" in font_name:
                        has_bold = True

            if line_text.strip():
                block_text_parts.append(line_text.strip())

        full_text = "\n".join(block_text_parts)
        if full_text.strip():
            blocks.append(TextBlock(
                text=full_text,
                page_number=page.number + 1,
                block_index=block_idx,
                font_size=max_font_size,
                is_bold=has_bold,
                bbox=tuple(block.get("bbox", ())),
            ))

    return blocks


def extract_images(page: fitz.Page, min_size: int = 100) -> list[ImageBlock]:
    """Extract images from a page, filtering out tiny decorative images."""
    images = []
    image_list = page.get_images(full=True)

    for img_idx, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            base_image = page.parent.extract_image(xref)
            if not base_image:
                continue

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            # Skip tiny images (logos, icons, bullets)
            if width < min_size or height < min_size:
                continue

            images.append(ImageBlock(
                image_bytes=base_image["image"],
                page_number=page.number + 1,
                image_index=img_idx,
                width=width,
                height=height,
                ext=base_image.get("ext", "png"),
            ))
        except Exception:
            continue

    return images


def parse_pdf(file_path: str | Path) -> ParsedDocument:
    """Parse a PDF file and extract all text blocks and images."""
    file_path = Path(file_path).resolve()
    doc = fitz.open(str(file_path))
    try:
        parsed = ParsedDocument(
            file_path=str(file_path),
            file_name=file_path.stem,
            total_pages=len(doc),
            metadata=dict(doc.metadata) if doc.metadata else {},
        )

        for page in doc:
            text_blocks = extract_text_blocks(page)
            images = extract_images(page)
            full_text = page.get_text("text")

            parsed.pages.append(PageContent(
                page_number=page.number + 1,
                text_blocks=text_blocks,
                images=images,
                full_text=full_text,
            ))

        return parsed
    finally:
        doc.close()


def get_page_combined_text(page: PageContent) -> str:
    """Get combined text from all extraction methods for a page."""
    parts = []
    if page.full_text.strip():
        parts.append(page.full_text.strip())
    if page.table_text.strip():
        parts.append(f"\n[TABLA EXTRAÍDA]\n{page.table_text.strip()}")
    if page.vision_text.strip():
        parts.append(f"\n[CONTENIDO VISUAL]\n{page.vision_text.strip()}")
    return "\n\n".join(parts)


def get_document_text(parsed: ParsedDocument) -> str:
    """Get the full text of a parsed document."""
    return "\n\n".join(
        get_page_combined_text(page) for page in parsed.pages
        if get_page_combined_text(page).strip()
    )


def enrich_with_tables(parsed: ParsedDocument) -> int:
    """Enrich parsed document pages with pdfplumber table extraction.

    Returns number of pages enriched.
    """
    from .table_extractor import extract_tables_all_pages

    table_results = extract_tables_all_pages(parsed.file_path)
    enriched = 0
    for page in parsed.pages:
        if page.page_number in table_results:
            table_text = table_results[page.page_number]
            # Only add if pdfplumber found content not already in full_text
            if table_text and not _text_already_captured(table_text, page.full_text):
                page.table_text = table_text
                enriched += 1
    parsed.tables_enriched = enriched
    return enriched


def enrich_with_vision(
    parsed: ParsedDocument,
    page_numbers: list[int] | None = None,
) -> int:
    """Enrich specific pages with Claude Vision extraction.

    Args:
        parsed: The parsed document.
        page_numbers: Specific pages to process. If None, auto-detects candidates.

    Returns number of pages enriched.
    """
    from .vision_describer import (
        describe_page_with_vision, should_use_vision, page_has_large_images,
    )

    if page_numbers is None:
        # Auto-detect candidates
        page_numbers = []

        # Document-level check: is this a fully-rasterized scan?
        # PyMuPDF + pdfplumber may not detect "large images" on such PDFs
        # because every page is one big background image, and image bbox
        # detection can miss that. Falling back: if the document yields
        # essentially zero extractable text across all pages, force Vision
        # on every page.
        total_text = sum(
            len((p.full_text or "").strip()) + len((p.table_text or "").strip())
            for p in parsed.pages
        )
        avg_per_page = total_text / max(1, len(parsed.pages))
        is_scanned_doc = len(parsed.pages) > 0 and avg_per_page < 50

        if is_scanned_doc:
            page_numbers = [p.page_number for p in parsed.pages]
        else:
            for page in parsed.pages:
                if should_use_vision(
                    page.full_text, page.table_text,
                    page_has_large_images(page),
                    num_images=len(page.images),
                ):
                    page_numbers.append(page.page_number)

    enriched = 0
    for page in parsed.pages:
        if page.page_number in page_numbers:
            vision_text = describe_page_with_vision(
                parsed.file_path, page.page_number,
            )
            if vision_text:
                page.vision_text = vision_text
                enriched += 1
    parsed.vision_enriched = enriched
    return enriched


def _text_already_captured(new_text: str, existing_text: str) -> bool:
    """Check if the new text is substantially already in the existing text.
    Avoids duplicating content that PyMuPDF already extracted.
    """
    if not new_text or not existing_text:
        return False
    # Check if >70% of new text words are already in existing text
    new_words = set(new_text.lower().split())
    existing_words = set(existing_text.lower().split())
    if not new_words:
        return True
    overlap = len(new_words & existing_words) / len(new_words)
    return overlap > 0.7


def detect_section_headers(parsed: ParsedDocument) -> list[dict]:
    """Detect section headers based on font size and formatting patterns.

    Returns list of dicts with keys: text, page_number, level, font_size
    """
    # First pass: collect all font sizes to determine hierarchy
    all_sizes = set()
    for page in parsed.pages:
        for block in page.text_blocks:
            if block.font_size > 0:
                all_sizes.add(round(block.font_size, 1))

    if not all_sizes:
        return []

    # Sort sizes descending — larger fonts = higher-level headers
    sorted_sizes = sorted(all_sizes, reverse=True)
    body_size = sorted_sizes[-1] if len(sorted_sizes) > 1 else sorted_sizes[0]

    # Section number pattern: "1.", "1.1", "1.1.1", "PASO 1:", etc.
    section_pattern = re.compile(
        r"^(\d+\.[\d.]*\s*[-–]?\s*[A-ZÁÉÍÓÚa-záéíóú].+|PASO\s+\d+|ANEXO\s+\d+|APÉNDICE)",
        re.IGNORECASE
    )

    # Determine a threshold: headers are typically > body_size + 2pt
    header_size_threshold = body_size + 2

    headers = []
    for page in parsed.pages:
        for block in page.text_blocks:
            text = block.text.strip()
            # Skip empty, too long, or single-char/number-only blocks
            if not text or len(text) > 200 or len(text) < 3:
                continue
            # Skip page numbers, "ESP", and similar noise
            if re.match(r"^(ESP|FRA|GBR|ITA|\d{1,3})$", text):
                continue

            is_header = False
            level = 3  # default: subsection

            # Check by numbered section pattern (most reliable signal)
            if section_pattern.match(text):
                is_header = True
                first_token = text.split()[0].rstrip(".-–")
                dots = first_token.count(".")
                level = min(dots + 1, 4) if dots > 0 else 1

            # Check by significantly larger font size (title-level headers only)
            elif block.font_size >= header_size_threshold and block.is_bold:
                is_header = True
                size_rank = sorted_sizes.index(round(block.font_size, 1))
                level = min(size_rank + 1, 4)

            if is_header:
                headers.append({
                    "text": text,
                    "page_number": block.page_number,
                    "level": level,
                    "font_size": block.font_size,
                })

    return headers


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <pdf_path>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Parsing: {path}")
    parsed = parse_pdf(path)
    print(f"Pages: {parsed.total_pages}")
    print(f"Total text blocks: {sum(len(p.text_blocks) for p in parsed.pages)}")
    print(f"Total images: {sum(len(p.images) for p in parsed.pages)}")

    headers = detect_section_headers(parsed)
    print(f"\nDetected {len(headers)} section headers:")
    for h in headers[:30]:
        indent = "  " * (h["level"] - 1)
        print(f"  {indent}[L{h['level']}] p.{h['page_number']}: {h['text'][:80]}")
