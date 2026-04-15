"""
Complete ingestion pipeline for Detnov PCI manuals.
Orchestrates: PDF parsing → language filtering → chunking → image extraction → embedding → Supabase upload.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from ..config import MANUALS_DIR, IMAGES_DIR
from .pdf_parser import parse_pdf, enrich_with_tables, enrich_with_vision
from .language_filter import filter_spanish_pages, detect_language_sections
from .chunker import chunk_document, Chunk
from .image_extractor import extract_diagram_pages, save_page_images
from .embedder import embed_texts
from .supabase_client import SupabaseHTTP, get_supabase
from .translator import translate_text, should_translate
from .document_registry import register_document, RegisterResult


def check_source_exists(supabase: SupabaseHTTP, source_file: str) -> int:
    """Check if a source file already has chunks in the database.

    Returns the number of existing chunks for this source file.
    """
    import httpx
    headers = {
        "apikey": supabase.service_key,
        "Authorization": f"Bearer {supabase.service_key}",
    }
    resp = supabase.client.get(
        f"{supabase.url}/rest/v1/chunks",
        headers=headers,
        params={
            "source_file": f"eq.{source_file}",
            "select": "id",
            "limit": "1",
        },
    )
    resp.raise_for_status()
    return len(resp.json())


def find_all_pdfs(base_dir: str | Path = MANUALS_DIR) -> list[Path]:
    """Find all PDF files recursively in the manuals directory."""
    base = Path(base_dir)
    pdfs = sorted(base.rglob("*.pdf"))
    return pdfs


def upload_images_to_supabase(
    supabase: SupabaseHTTP,
    image_paths: dict[int, str],
    product_model: str,
    source_file: str,
) -> dict[int, str]:
    """Upload extracted images to Supabase Storage.

    Returns dict mapping page_number -> public URL.
    """
    bucket = "manual-images"
    urls = {}

    for page_num, local_path in image_paths.items():
        local = Path(local_path)
        if not local.exists():
            continue

        storage_path = f"{product_model}/{local.name}"
        try:
            with open(local, "rb") as f:
                supabase.upload_file(bucket, storage_path, f.read())
            url = supabase.get_public_url(bucket, storage_path)
            urls[page_num] = url
        except Exception as e:
            logger.warning(f"Failed to upload {local.name}: {e}")

    return urls


def insert_chunks_to_supabase(
    supabase: SupabaseHTTP,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    image_urls: dict[int, str],
    document_id: str | None = None,
):
    """Insert chunks with embeddings into the Supabase chunks table.

    Args:
        document_id: FK to the `documents` row this batch belongs to. If None,
            chunks are inserted without a document link (legacy/pre-Phase 1
            behavior). New ingestions should always pass a real UUID.
    """
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        diagram_url = None
        if chunk.has_diagram and chunk.diagram_pages:
            for dp in chunk.diagram_pages:
                if dp in image_urls:
                    diagram_url = image_urls[dp]
                    break

        # Sanitize content: remove null bytes that cause Supabase 400 errors
        content = chunk.content.replace("\x00", "")

        row = {
            "content": content,
            "embedding": embedding,
            "product_model": chunk.product_model,
            "category": chunk.category,
            "section_title": chunk.section_title,
            "content_type": chunk.content_type,
            "manufacturer": chunk.manufacturer,
            "protocol": chunk.protocol or None,
            "doc_type": chunk.doc_type or None,
            "has_diagram": chunk.has_diagram,
            "diagram_url": diagram_url,
            "source_file": chunk.source_file,
            "page_number": chunk.start_page,
        }
        if document_id:
            row["document_id"] = document_id
        rows.append(row)

    # Insert in batches
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            supabase.insert_rows("chunks", batch)
        except Exception as e:
            logger.error(f"Batch insert {i}-{i+batch_size} failed: {e}")
            for row in batch:
                try:
                    supabase.insert_rows("chunks", [row])
                except Exception as e2:
                    logger.error(f"Single insert failed (model={row.get('product_model')}): {e2}")


def ingest_single_pdf(
    pdf_path: str | Path,
    supabase=None,
    save_images: bool = True,
    upload_to_supabase: bool = True,
    dry_run: bool = False,
    use_vision: bool = False,
    translate_en: bool = False,
) -> list[Chunk]:
    """Process a single PDF through the full ingestion pipeline.

    Args:
        pdf_path: Path to the PDF file.
        supabase: Supabase client (optional if dry_run).
        save_images: Whether to extract and save diagram images.
        upload_to_supabase: Whether to upload to Supabase.
        dry_run: If True, only parse and chunk without uploading.
        use_vision: If True, use Claude Vision for pages with unextracted content.

    Returns:
        List of chunks generated from this PDF.
    """
    pdf_path = Path(pdf_path)
    logger.info(f"{'='*60}")
    logger.info(f"Processing: {pdf_path.name}")

    # Step 0: Check for duplicates (skip if source_file already in DB)
    if not dry_run and supabase:
        existing = check_source_exists(supabase, pdf_path.stem)
        if existing > 0:
            logger.warning(f"  SKIPPED: {pdf_path.name} already has chunks in DB. "
                           f"Use re_ingest.py to replace, or delete existing chunks first.")
            return []

    # Step 1: Parse PDF
    logger.info("  1. Parsing PDF...")
    parsed = parse_pdf(pdf_path)
    logger.info(f"     Pages: {parsed.total_pages}, "
                f"Text blocks: {sum(len(p.text_blocks) for p in parsed.pages)}, "
                f"Images: {sum(len(p.images) for p in parsed.pages)}")

    # Step 1b: Enrich with pdfplumber tables
    logger.info("  1b. Extracting tables (pdfplumber)...")
    tables_count = enrich_with_tables(parsed)
    logger.info(f"      Pages with new table data: {tables_count}")

    # Step 1c: Enrich with Claude Vision (fallback for unextracted content)
    if use_vision:
        logger.info("  1c. Vision fallback (Claude Vision)...")
        vision_count = enrich_with_vision(parsed)
        logger.info(f"      Pages processed with Vision: {vision_count}")

    # Step 2: Filter Spanish pages
    logger.info("  2. Filtering Spanish content...")
    sections = detect_language_sections(parsed)
    for s in sections:
        logger.info(f"     [{s.language}] pages {s.start_page}-{s.end_page}")
    spanish_pages = filter_spanish_pages(parsed)
    logger.info(f"     Spanish pages: {len(spanish_pages)} / {parsed.total_pages}")

    if not spanish_pages:
        if translate_en:
            # Step 2b: Translate English pages to Spanish
            logger.info("  2b. Translating EN → ES (Claude Sonnet)...")
            translated_count = 0
            for page in parsed.pages:
                if page.full_text and should_translate(page.full_text):
                    page.full_text = translate_text(page.full_text)
                    translated_count += 1
                if page.table_text and should_translate(page.table_text):
                    page.table_text = translate_text(page.table_text)
                if page.vision_text and should_translate(page.vision_text):
                    page.vision_text = translate_text(page.vision_text)
            logger.info(f"      Translated {translated_count} / {parsed.total_pages} pages")
            spanish_pages = parsed.pages
        else:
            logger.warning("No Spanish pages detected, using all pages")
            spanish_pages = parsed.pages

    # Step 3: Chunk document
    logger.info("  3. Chunking document...")
    chunks = chunk_document(parsed, spanish_pages)
    logger.info(f"     Chunks: {len(chunks)}")
    if chunks:
        c0 = chunks[0]
        logger.info(f"     Product model: {c0.product_model}")
        logger.info(f"     Manufacturer: {c0.manufacturer}")
        logger.info(f"     Category: {c0.category}")
        logger.info(f"     Protocol: {c0.protocol or '(not detected)'}")
        logger.info(f"     Doc type: {c0.doc_type or '(not detected)'}")
        types = {}
        for c in chunks:
            types[c.content_type] = types.get(c.content_type, 0) + 1
        logger.info(f"     Content types: {types}")
        diag_count = sum(1 for c in chunks if c.has_diagram)
        logger.info(f"     Chunks with diagrams: {diag_count}")

    if dry_run:
        logger.info("  [DRY RUN] Skipping image extraction and upload.")
        return chunks

    # Step 3b: Register document (document-management refactor, Phase 3)
    # Compute content hash, parse revision, decide supersede action, get document_id.
    document_id: str | None = None
    if chunks and supabase:
        logger.info("  3b. Registering document...")
        first_pages_text = ""
        if parsed.pages:
            first_pages_text = "\n".join(
                (p.full_text or "") + "\n" + (p.table_text or "")
                for p in parsed.pages[:2]
            )
        try:
            reg: RegisterResult = register_document(
                supabase,
                pdf_path=pdf_path,
                manufacturer=chunks[0].manufacturer,
                product_model=chunks[0].product_model,
                first_pages_text=first_pages_text,
            )
            document_id = reg.document_id
            logger.info(
                f"     document_id={document_id[:8]} action={reg.action} "
                f"rev={reg.revision_info.revision or '(none)'} "
                f"date={reg.revision_info.revision_date or '(none)'} "
                f"lang={reg.revision_info.language or '(none)'} "
                f"type={reg.revision_info.doc_type or '(none)'}"
            )
            if reg.action == "needs_review":
                logger.warning(f"     ⚠ NEEDS_REVIEW — human must resolve supersede chain")
            elif reg.action == "superseded_previous":
                logger.info(f"     ↑ This doc supersedes prior active revision(s)")
            elif reg.action == "superseded_self":
                logger.info(f"     ↓ This doc is OLDER than current active — inserted as superseded")
        except Exception as e:
            logger.error(f"     document_registry failed: {e}")
            logger.error(f"     Falling back to chunk insert without document_id")

    # Step 4: Extract diagram images
    image_urls = {}
    if save_images and chunks:
        logger.info("  4. Extracting diagram images...")
        diag_pages = extract_diagram_pages(parsed, spanish_pages)
        if diag_pages:
            saved = save_page_images(
                pdf_path, diag_pages, IMAGES_DIR,
                product_model=chunks[0].product_model,
            )
            logger.info(f"     Saved {len(saved)} diagram images locally")

            # Upload to Supabase Storage
            if upload_to_supabase and supabase:
                logger.info("  4b. Uploading images to Supabase Storage...")
                image_urls = upload_images_to_supabase(
                    supabase, saved, chunks[0].product_model, parsed.file_name,
                )
                logger.info(f"      Uploaded {len(image_urls)} images")

    # Step 5: Generate embeddings
    if upload_to_supabase:
        logger.info("  5. Generating embeddings...")
        texts = [c.content for c in chunks]
        embeddings = embed_texts(texts)
        logger.info(f"     Generated {len(embeddings)} embeddings")

        # Step 6: Insert into Supabase
        if supabase:
            logger.info("  6. Inserting into Supabase...")
            insert_chunks_to_supabase(
                supabase, chunks, embeddings, image_urls, document_id=document_id,
            )
            logger.info(
                f"     Inserted {len(chunks)} chunks"
                + (f" (document_id={document_id[:8]})" if document_id else " (no document_id)")
            )

    return chunks


def ingest_all(
    base_dir: str | Path = MANUALS_DIR,
    dry_run: bool = False,
    use_vision: bool = False,
    translate_en: bool = False,
):
    """Run the full ingestion pipeline on all PDFs in the manuals directory."""
    pdfs = find_all_pdfs(base_dir)
    logger.info(f"Found {len(pdfs)} PDF files to process")
    if use_vision:
        logger.info("Claude Vision ENABLED for unextracted content")
    if translate_en:
        logger.info("Translation EN→ES ENABLED for English-only documents")

    supabase = None
    if not dry_run:
        supabase = get_supabase()

    total_chunks = 0
    errors = []

    for i, pdf_path in enumerate(pdfs):
        try:
            logger.info(f"[{i+1}/{len(pdfs)}] {pdf_path.name}")
            chunks = ingest_single_pdf(
                pdf_path,
                supabase=supabase,
                dry_run=dry_run,
                use_vision=use_vision,
                translate_en=translate_en,
            )
            total_chunks += len(chunks)
        except Exception as e:
            logger.error(f"ERROR processing {pdf_path.name}: {e}")
            errors.append((pdf_path.name, str(e)))

    logger.info(f"{'='*60}")
    logger.info(f"INGESTION COMPLETE")
    logger.info(f"PDFs processed: {len(pdfs) - len(errors)} / {len(pdfs)}")
    logger.info(f"Total chunks: {total_chunks}")
    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for name, err in errors:
            logger.error(f"  - {name}: {err}")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    use_vision = "--use-vision" in sys.argv
    if dry_run:
        print("DRY RUN MODE - no uploads will be performed")
    if use_vision:
        print("VISION MODE - Claude Vision enabled for unextracted content")

    ingest_all(dry_run=dry_run, use_vision=use_vision)
