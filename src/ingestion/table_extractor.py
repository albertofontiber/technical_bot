"""
Table extractor using pdfplumber.
Complements PyMuPDF by extracting structured tables that PyMuPDF misses
(tables with borders, grid lines, or cell structure).
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_tables_from_page(pdf_path: str | Path, page_number: int) -> str:
    """Extract tables from a specific page using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.
        page_number: 1-based page number.

    Returns:
        Formatted text of all tables found on the page, or empty string.
    """
    pdf_path = Path(pdf_path).resolve()
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                return ""
            page = pdf.pages[page_number - 1]
            return _extract_page_tables(page)
    except Exception as e:
        logger.warning(f"pdfplumber error on page {page_number}: {e}")
        return ""


def extract_tables_all_pages(pdf_path: str | Path) -> dict[int, str]:
    """Extract tables from all pages of a PDF.

    Returns:
        Dict mapping 1-based page_number -> formatted table text.
        Only includes pages that have tables.
    """
    pdf_path = Path(pdf_path).resolve()
    results = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                table_text = _extract_page_tables(page)
                if table_text:
                    results[page_num] = table_text
    except Exception as e:
        logger.warning(f"pdfplumber error opening {pdf_path.name}: {e}")
    return results


def _extract_page_tables(page) -> str:
    """Extract and format all tables from a pdfplumber page object."""
    tables = page.extract_tables(
        table_settings={
            "vertical_strategy": "lines_strict",
            "horizontal_strategy": "lines_strict",
            "snap_tolerance": 5,
        }
    )

    if not tables:
        # Retry with relaxed settings for tables with partial borders
        tables = page.extract_tables(
            table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 5,
            }
        )

    if not tables:
        # Final attempt: text-based detection for borderless tables
        tables = page.extract_tables(
            table_settings={
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 5,
                "min_words_vertical": 2,
                "min_words_horizontal": 2,
            }
        )

    if not tables:
        return ""

    formatted_parts = []
    for table in tables:
        formatted = _format_table(table)
        if formatted:
            formatted_parts.append(formatted)

    return "\n\n".join(formatted_parts)


def _format_table(table: list[list[str | None]]) -> str:
    """Format a pdfplumber table as readable text.

    Uses "Header: Value" format for simple 2-column tables,
    and pipe-separated format for wider tables.
    """
    if not table or len(table) < 2:
        return ""

    # Clean cells: replace None with empty string, strip whitespace
    cleaned = []
    for row in table:
        cleaned_row = [
            (cell.strip().replace("\n", " ") if cell else "")
            for cell in row
        ]
        # Skip completely empty rows
        if any(cleaned_row):
            cleaned.append(cleaned_row)

    if len(cleaned) < 2:
        return ""

    # Determine if first row is a header (often bold or distinct)
    header = cleaned[0]
    data_rows = cleaned[1:]

    # Format based on column count
    num_cols = len(header)

    if num_cols == 2 and all(row[0] for row in data_rows[:3]):
        # 2-column table: "Key: Value" format
        lines = []
        if header[0] and header[1]:
            lines.append(f"[{header[0]} | {header[1]}]")
        for row in data_rows:
            key = row[0] if len(row) > 0 else ""
            val = row[1] if len(row) > 1 else ""
            if key or val:
                lines.append(f"  {key}: {val}")
        return "\n".join(lines)

    else:
        # Multi-column table: pipe-separated format
        lines = []
        # Header row
        lines.append(" | ".join(h for h in header))
        lines.append("-" * 40)
        # Data rows
        for row in data_rows:
            # Pad row to match header length
            padded = row + [""] * (num_cols - len(row))
            lines.append(" | ".join(padded[:num_cols]))
        return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.table_extractor <pdf_path> [page_number]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if len(sys.argv) > 2:
        page_num = int(sys.argv[2])
        print(f"Extracting tables from page {page_num} of {pdf_path}")
        text = extract_tables_from_page(pdf_path, page_num)
        if text:
            print(text)
        else:
            print("No tables found on this page.")
    else:
        print(f"Extracting tables from all pages of {pdf_path}")
        results = extract_tables_all_pages(pdf_path)
        print(f"Found tables on {len(results)} pages")
        for page_num, text in sorted(results.items()):
            print(f"\n--- Page {page_num} ---")
            print(text[:500])
            if len(text) > 500:
                print(f"... ({len(text)} chars total)")
