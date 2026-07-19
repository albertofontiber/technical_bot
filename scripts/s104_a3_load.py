#!/usr/bin/env python3
"""s104_a3_load.py — loader A3 generalizado: dumps del pase R2 → `chunks_v2_enunciados`.

Único camino de ESCRITURA del pase corpus-wide (s104 X1: enunciados_pass.py ya no inserta —
genera a dump; este loader carga SOLO en la tabla separada de la arquitectura validada
DEC-089). Basado en s95_pilot_a_load (que cargó T1): receta de embedding PINEADA [D8] =
f"{context}\\n\\n{content}" si hay context, si no content; embed(texts, "document") Voyage
en batches de 100; insert batched con bisección anti-poison.

Idempotencia POR BATCH: --replace borra las filas del ingest_batch de cada dump antes de
insertar (rollback selectivo por vintage/tranche intacto); sin --replace, salta ids ya
presentes (resumable). El campo `chaff` del dump NO se carga (no es columna; queda en el
dump para el filtro post-G0). Tras cargas grandes: VACUUM (fantasmas HNSW, DEC-088) —
recordatorio impreso.

Uso: python scripts/s104_a3_load.py --dumps evals/enunciados_dump_T3.jsonl [más...] [--replace] [--dry]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=False)
import httpx  # noqa: E402
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402
from src.reingest.embed import embed  # noqa: E402

TABLE = "chunks_v2_enunciados"
HEADERS = {"apikey": SUPABASE_SERVICE_KEY,
           "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
           "Content-Type": "application/json"}
INSERT_BATCH = 500
COLS = ["id", "content", "context", "parent_id", "ingest_batch", "source_file",
        "page_number", "product_model", "manufacturer", "section_title", "doc_type",
        "content_type", "chunk_index", "document_id", "language", "extraction_sha256"]


def _existing_ids(client: httpx.Client) -> set:
    ids: set = set()
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


def _insert_rows(client: httpx.Client, rows: list, poison: list) -> int:
    if not rows:
        return 0
    r = client.post(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                    headers={**HEADERS, "Prefer": "return=minimal"}, json=rows)
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) == 1:
        poison.append({"id": rows[0]["id"], "status": r.status_code, "body": r.text[:300]})
        return 0
    mid = len(rows) // 2
    return _insert_rows(client, rows[:mid], poison) + _insert_rows(client, rows[mid:], poison)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", nargs="+", required=True)
    ap.add_argument("--replace", action="store_true",
                    help="DELETE por ingest_batch de cada dump antes de insertar")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--skip-chaff", action="store_true",
                    help="no cargar filas marcadas chaff en el dump (decisión post-G0)")
    # (s273 Sol-C1) recarga ACOTADA: filtro por doc + batch-tag propio + validación ledger
    # + manifest de ids (la exclusión prod-neutral de Sol-C2b). Sin estos flags el loader
    # es byte-idéntico al histórico.
    ap.add_argument("--only-source-files", nargs="+", default=None,
                    help="(s273) cargar SOLO filas cuyo source_file esté en esta lista")
    ap.add_argument("--rewrite-batch-tag", default=None,
                    help="(s273) reescribir ingest_batch de TODAS las filas cargadas "
                         "(p.ej. enunciados-v1:T2Q1:h1) — rollback selectivo por tag exacto")
    ap.add_argument("--ledger-check", action="store_true",
                    help="(s273) validar extraction_sha256 de cada doc filtrado contra "
                         "evals/enunciados_ledger.json (aborta si no casa)")
    ap.add_argument("--ids-out", default=None,
                    help="(s273) escribir manifest JSON {batch, ids} con los ids a cargar "
                         "(consumido por la exclusión flag-off del retriever)")
    a = ap.parse_args()
    rows: list = []
    for d in a.dumps:
        for line in open(d, encoding="utf-8"):
            row = json.loads(line)
            if a.skip_chaff and row.get("chaff"):
                continue
            if a.only_source_files and row.get("source_file") not in a.only_source_files:
                continue
            rows.append(row)
    if a.only_source_files:
        missing = set(a.only_source_files) - {r.get("source_file") for r in rows}
        if missing:
            print(f"ABORT: --only-source-files sin filas en los dumps: {sorted(missing)}")
            return 1
    if a.ledger_check:
        ledger = json.load(open(ROOT / "evals" / "enunciados_ledger.json", encoding="utf-8"))
        by_doc: dict = {}
        for r in rows:
            by_doc.setdefault(r.get("source_file"), set()).add(r.get("extraction_sha256"))
        for doc, shas in sorted(by_doc.items()):
            entry = (ledger.get("docs") or {}).get(doc)
            if not entry or shas != {entry.get("sha")}:
                print(f"ABORT ledger-check: {doc} → dump {sorted(shas)} vs ledger "
                      f"{entry.get('sha') if entry else 'AUSENTE'}")
                return 1
        print(f"ledger-check OK: {len(by_doc)} docs, sha exacto")
    if a.rewrite_batch_tag:
        for r in rows:
            r["ingest_batch"] = a.rewrite_batch_tag
    batches = Counter(r.get("ingest_batch") for r in rows)
    print(f"dumps: {len(a.dumps)} · filas: {len(rows)} · batches: {dict(batches)}")
    if a.replace:
        print(f"delete-scope (--replace): ingest_batch eq {sorted(batches)} "
              f"{'(DRY: no se borra)' if a.dry else ''}")
    if a.ids_out:
        manifest = {"batch": a.rewrite_batch_tag or sorted(batches),
                    "n": len(rows), "ids": sorted(r["id"] for r in rows)}
        Path(a.ids_out).write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        print(f"ids-out: {a.ids_out} ({len(rows)} ids)")
    with httpx.Client(timeout=120.0) as client:
        if a.replace and not a.dry:
            for b in batches:
                client.delete(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=HEADERS,
                              params={"ingest_batch": f"eq.{b}"}).raise_for_status()
            print("batches previos borrados (--replace)")
            done: set = set()
        else:
            done = _existing_ids(client)
        pending = [r for r in rows if r["id"] not in done]
        print(f"ya presentes: {len(done)} · pendientes: {len(pending)}")
        if a.dry or not pending:
            return 0
        poison: list = []
        inserted = 0
        for i in range(0, len(pending), INSERT_BATCH):
            chunk = pending[i:i + INSERT_BATCH]
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
            plog = ROOT / "evals" / "s104_a3_load_poison.jsonl"
            with plog.open("a", encoding="utf-8") as f:
                for p in poison:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
            print(f"⚠ {len(poison)} filas envenenadas → {plog}")
        print(f"TOTAL insertados: {inserted}")
        print("RECORDATORIO: tras cargas/re-runs grandes → VACUUM chunks_v2_enunciados "
              "(fantasmas HNSW, DEC-088) y SIEMPRE antes del gate final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
