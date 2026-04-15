"""
Re-embed all chunks with enriched text (prepend metadata to content).
This improves vector search accuracy by giving the embedding model
context about the product, category, and section.

Usage:
    py -3.14 -X utf8 scripts/re_embed.py [--dry-run]
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.embedder import embed_texts


def build_enriched_text(chunk: dict) -> str:
    """Build enriched text for embedding by prepending metadata context.

    Example output:
        Fabricante: Detnov | Producto: CAD-250 | Categoría: Detección analógica | Sección: Conexión de baterías | Tipo: procedure
        PASO 1: Coloque las dos baterías dentro de la central...
    """
    parts = ["Fabricante: Detnov"]

    product = chunk.get("product_model", "")
    if product and product != "unknown":
        parts.append(f"Producto: {product}")

    category = chunk.get("category", "")
    if category:
        parts.append(f"Categoría: {category}")

    section = chunk.get("section_title", "")
    if section:
        # Clean section title (first line only, max 100 chars)
        clean_section = section.strip().split("\n")[0][:100]
        parts.append(f"Sección: {clean_section}")

    content_type = chunk.get("content_type", "")
    if content_type:
        type_labels = {
            "procedure": "procedimiento",
            "specification": "especificaciones técnicas",
            "troubleshooting": "resolución de problemas",
            "wiring": "conexionado y esquemas",
            "general": "información general",
        }
        parts.append(f"Tipo: {type_labels.get(content_type, content_type)}")

    header = " | ".join(parts)
    content = chunk.get("content", "")

    return f"{header}\n{content}"


def fetch_all_chunks() -> list[dict]:
    """Fetch all chunks from Supabase (without embeddings, to save bandwidth)."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "count=exact",
    }

    all_chunks = []
    offset = 0
    batch_size = 500

    while True:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/chunks",
            headers=headers,
            params={
                "select": "id,content,product_model,category,section_title,content_type",
                "order": "created_at.asc",
                "offset": str(offset),
                "limit": str(batch_size),
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        all_chunks.extend(batch)
        offset += len(batch)
        print(f"  Fetched {len(all_chunks)} chunks...")

        if len(batch) < batch_size:
            break

    return all_chunks


def update_embedding(chunk_id: str, embedding: list[float]):
    """Update a single chunk's embedding in Supabase."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    resp = httpx.patch(
        f"{SUPABASE_URL}/rest/v1/chunks?id=eq.{chunk_id}",
        headers=headers,
        json={"embedding": embedding},
        timeout=30.0,
    )
    resp.raise_for_status()


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("RE-EMBEDDING CHUNKS WITH ENRICHED TEXT")
    print("=" * 60)

    # Step 1: Fetch all chunks
    print("\n1. Fetching all chunks from Supabase...")
    chunks = fetch_all_chunks()
    print(f"   Total chunks: {len(chunks)}")

    # Step 2: Build enriched texts
    print("\n2. Building enriched texts...")
    enriched_texts = []
    for chunk in chunks:
        enriched = build_enriched_text(chunk)
        enriched_texts.append(enriched)

    # Show a few examples
    print("\n   Examples:")
    for i in [0, len(chunks) // 2, -1]:
        print(f"   [{i}] {enriched_texts[i][:120]}...")

    if dry_run:
        print(f"\n[DRY RUN] Would re-embed {len(chunks)} chunks. Exiting.")
        return

    # Step 3: Generate new embeddings in batches
    print(f"\n3. Generating {len(chunks)} new embeddings...")
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(enriched_texts), batch_size):
        batch = enriched_texts[i:i + batch_size]
        batch_embeddings = embed_texts(batch, batch_size=batch_size)
        all_embeddings.extend(batch_embeddings)
        print(f"   Embedded {len(all_embeddings)} / {len(chunks)}")

    # Step 4: Update embeddings in Supabase
    print(f"\n4. Updating embeddings in Supabase...")
    errors = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
        try:
            update_embedding(chunk["id"], embedding)
        except Exception as e:
            print(f"   Error updating chunk {chunk['id']}: {e}")
            errors += 1

        if (i + 1) % 200 == 0:
            print(f"   Updated {i + 1} / {len(chunks)}")

    print(f"\n{'=' * 60}")
    print(f"RE-EMBEDDING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Chunks updated: {len(chunks) - errors} / {len(chunks)}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
