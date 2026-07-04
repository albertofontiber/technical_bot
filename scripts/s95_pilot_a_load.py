"""s95 Piloto A — cargar el dump T1 en chunks_v2_enunciados (tabla separada, migración 011).

Pre-registro: evals/s95_redesign_pilots.md v2. Receta de embedding PINEADA [D8] = la del
pase T1 (enunciados_pass.py:229-233): f"{context}\n\n{content}" si hay context, si no
content; embed(texts, "document") (Voyage, batches de 100). Insert batched con bisección
anti-poison (patrón T1). Idempotente: --wipe borra la tabla antes; sin --wipe, salta ids
ya presentes (resumable).

Uso:  python scripts/s95_pilot_a_load.py [--wipe] [--dry]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402
from src.reingest.embed import embed  # noqa: E402

DUMP = ROOT / "evals" / "t1_surrogates_dump.jsonl"
TABLE = "chunks_v2_enunciados"
HEADERS = {"apikey": SUPABASE_SERVICE_KEY,
           "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
           "Content-Type": "application/json"}
INSERT_BATCH = 500

# columnas de la tabla 011 (el dump trae exactamente estos campos + embedding aparte)
COLS = ["id", "content", "context", "parent_id", "ingest_batch", "source_file",
        "page_number", "product_model", "manufacturer", "section_title", "doc_type",
        "content_type", "chunk_index", "document_id", "language", "extraction_sha256"]


def _existing_ids(client: httpx.Client) -> set[str]:
    ids: set[str] = set()
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                       headers={**HEADERS, "Range": f"{offset}-{offset + 9999}"},
                       params={"select": "id", "order": "id.asc"})
        if r.status_code not in (200, 206) or not r.json():
            break
        batch = r.json()
        ids.update(row["id"] for row in batch)
        if len(batch) < 10000:
            break
        offset += 10000
    return ids


def _insert_rows(client: httpx.Client, rows: list[dict], poison: list[dict]) -> int:
    """POST batched; en fallo, bisección hasta la fila envenenada (patrón T1)."""
    if not rows:
        return 0
    r = client.post(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                    headers={**HEADERS, "Prefer": "return=minimal"},
                    json=rows)
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) == 1:
        poison.append({"id": rows[0]["id"], "status": r.status_code,
                       "body": r.text[:300]})
        return 0
    mid = len(rows) // 2
    return (_insert_rows(client, rows[:mid], poison)
            + _insert_rows(client, rows[mid:], poison))


def main() -> int:
    wipe = "--wipe" in sys.argv
    dry = "--dry" in sys.argv
    rows = [json.loads(line) for line in DUMP.open(encoding="utf-8")]
    print(f"dump: {len(rows)} enunciados")

    with httpx.Client(timeout=120.0) as client:
        if wipe and not dry:
            client.delete(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                          headers=HEADERS,
                          params={"ingest_batch": "like.enunciados-v1*"}).raise_for_status()
            print("tabla vaciada (--wipe)")
        done = set() if wipe else _existing_ids(client)
        pending = [r for r in rows if r["id"] not in done]
        print(f"ya presentes: {len(done)} · pendientes: {len(pending)}")
        if dry or not pending:
            return 0

        poison: list[dict] = []
        inserted = 0
        for i in range(0, len(pending), INSERT_BATCH):
            chunk = pending[i:i + INSERT_BATCH]
            # receta pineada [D8] — idéntica al pase T1
            texts = [(f"{r['context']}\n\n{r['content']}" if r.get("context")
                      else r["content"]) for r in chunk]
            embs = []
            for j in range(0, len(texts), 100):
                embs.extend(embed(texts[j:j + 100], "document"))
            payload = []
            for r, e in zip(chunk, embs):
                row = {k: r.get(k) for k in COLS}
                row["content"] = (row["content"] or "").replace(chr(0), "")[:8000]
                row["embedding"] = e
                payload.append(row)
            inserted += _insert_rows(client, payload, poison)
            print(f"  {min(i + INSERT_BATCH, len(pending))}/{len(pending)} "
                  f"(insertados {inserted}, poison {len(poison)})", flush=True)

        if poison:
            plog = ROOT / "evals" / "s95_pilot_a_poison.jsonl"
            with plog.open("a", encoding="utf-8") as f:
                for p in poison:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
            print(f"⚠ {len(poison)} filas envenenadas → {plog}")
        print(f"TOTAL insertados: {inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
