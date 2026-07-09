#!/usr/bin/env python3
"""s102_hyq_load.py — carga corpus-wide del índice question-side (hyq) a `chunks_v2_hyq`.

Ship D2 (Alberto OK; piloto GO DEC-095; diseño en `evals/s102_plan_autonomo.md`; migración 013).
Fuente = el npz corpus-wide producido por `scripts/s101_hyq_embed.py` (MISMO script y criterios
PINEADOS del piloto: keep-first por chunk_id, cap 4/chunk, dedup global, len>=15, exclusión
MIE-MI-310) + metadata (page/pm/origin) del jsonl. pm=unknown NO se excluye (decisión del plan:
la barra 0.45 filtra; se re-evalúa en el gate).

GUARDA DE VINTAGE: el loader re-corre `parse_questions()` y exige identidad EXACTA con el npz —
un npz stale (vintage piloto) o un jsonl movido aborta ANTES de tocar la DB.

Idempotente/resumable: UNIQUE(chunk_id,question) + `on_conflict=ignore-duplicates` → re-correr
solo inserta lo que falte (0 re-embedding: el npz es el checkpoint). Bisección anti-poison
(patrón s95_pilot_a_load). Verificación final: count == universo + smoke self-hit del RPC.

GUARDA DE VINTAGE DB (fix cross-model s102): cada fila lleva `ingest_batch=hyq-v1-<sha16-npz>`;
si la tabla contiene filas de OTRO batch, el loader ABORTA (ignore-duplicates NO actualiza filas
stale — mezclar vintages sería silencioso). `--wipe` borra los batches hyq-* y recarga limpio.

Uso: python scripts/s102_hyq_load.py [--dry] [--wipe]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from s101_hyq_embed import HYQ, OUT as NPZ, parse_questions  # noqa: E402
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

TABLE = "chunks_v2_hyq"
HEADERS = {"apikey": SUPABASE_SERVICE_KEY,
           "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
           "Content-Type": "application/json"}
INSERT_BATCH = 200          # 200 filas × 1024 floats ≈ 4 MB/request


def _meta_by_chunk() -> dict[str, dict]:
    """page_number/product_model/origin por chunk_id — keep-FIRST (mismo criterio que el parse)."""
    meta: dict[str, dict] = {}
    for line in HYQ.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        cid = r.get("chunk_id")
        if cid and cid not in meta:
            meta[cid] = {"page_number": r.get("page_number"),
                         "product_model": r.get("product_model"),
                         "origin": r.get("origin") or "synthetic"}
    return meta


def _table_count(client: httpx.Client) -> int:
    r = client.get(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                   headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                   params={"select": "id"})
    # (fix dúo s102 #4) tabla ausente/URL mala = fail-FAST, no "0 filas" silencioso (que
    # acabaría en bisección de 70k filas contra un 404 y 70k entradas poison).
    if r.status_code not in (200, 206):
        raise RuntimeError(f"GET {TABLE} → {r.status_code} — ¿migración 013 aplicada? ¿URL/key?"
                           f" body: {r.text[:200]}")
    cr = r.headers.get("content-range") or "/0"
    return int(cr.split("/")[-1])


def _existing_pairs(client: httpx.Client) -> set[tuple[str, str]]:
    """(chunk_id, question) ya en tabla — para reanudar sin re-postear todo (los conflicts
    son gratis pero el payload de 76k filas no)."""
    # (fix dúo s102 #5) paginar a 1000: Supabase capa max-rows=1000 aunque el Range pida
    # 10k (verificado en vivo por el sub-agente) — el patrón s95 de 10k rompía el resume.
    pairs: set[tuple[str, str]] = set()
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                       headers={**HEADERS, "Range": f"{offset}-{offset + 999}"},
                       params={"select": "chunk_id,question", "order": "id.asc"})
        if r.status_code not in (200, 206) or not r.json():
            break
        batch = r.json()
        pairs.update((row["chunk_id"], row["question"]) for row in batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return pairs


def _insert_rows(client: httpx.Client, rows: list[dict], poison: list[dict]) -> int:
    """POST batched con on_conflict=ignore-duplicates; en fallo, bisección (patrón s95)."""
    if not rows:
        return 0
    r = client.post(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                    headers={**HEADERS,
                             "Prefer": "resolution=ignore-duplicates,return=minimal"},
                    params={"on_conflict": "chunk_id,question"},
                    json=rows)
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) == 1:
        poison.append({"chunk_id": rows[0]["chunk_id"], "q": rows[0]["question"][:80],
                       "status": r.status_code, "body": r.text[:300]})
        return 0
    mid = len(rows) // 2
    return (_insert_rows(client, rows[:mid], poison)
            + _insert_rows(client, rows[mid:], poison))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    dry = "--dry" in sys.argv
    wipe = "--wipe" in sys.argv

    questions, chunk_ids, srcs, st = parse_questions()
    print(f"universo parse: {len(questions)} preguntas / {len(set(chunk_ids))} chunks ({st})")

    d = np.load(NPZ, allow_pickle=True)
    npz_q = [str(x) for x in d["questions"]]
    npz_cid = [str(x) for x in d["chunk_ids"]]
    embs = d["embeddings"].astype(np.float32)
    # GUARDA DE VINTAGE npz↔parse (fail-fast, lección s96-H3): identidad EXACTA. Un npz del
    # piloto (subset) o un jsonl editado después del embed NO puede cargar filas desalineadas.
    if npz_q != questions or npz_cid != chunk_ids:
        print(f"❌ npz DESALINEADO con el parse del jsonl (npz={len(npz_q)} vs parse={len(questions)})."
              f"\n   Re-corre `python scripts/s101_hyq_embed.py` (re-embebe el universo actual) y relanza.")
        return 1
    batch_tag = f"hyq-v1-{hashlib.sha256(NPZ.read_bytes()).hexdigest()[:16]}"
    print(f"npz alineado: {embs.shape} · ingest_batch={batch_tag}")

    meta = _meta_by_chunk()
    with httpx.Client(timeout=180.0) as client:
        if wipe and not dry:
            client.delete(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=HEADERS,
                          params={"ingest_batch": "like.hyq-*"}).raise_for_status()
            print("tabla vaciada (--wipe, batches hyq-*)")
        # GUARDA DE VINTAGE DB↔npz (fix cross-model): filas de OTRO batch = mezcla silenciosa
        # (ignore-duplicates jamás las actualizaría) → abortar y pedir --wipe.
        r = client.get(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                       headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                       params={"select": "id", "ingest_batch": f"neq.{batch_tag}"})
        if r.status_code not in (200, 206):     # (fix dúo #4) 404 aquí = tabla sin crear
            raise RuntimeError(f"GET {TABLE} → {r.status_code} — ¿migración 013 aplicada? "
                               f"body: {r.text[:200]}")
        n_other = int((r.headers.get("content-range") or "/0").split("/")[-1])
        if n_other:
            print(f"❌ la tabla contiene {n_other} filas de OTRO ingest_batch (vintage distinto)."
                  f"\n   Re-corre con --wipe para recargar limpio con el npz actual.")
            return 1
        n0 = _table_count(client)
        print(f"tabla {TABLE}: {n0} filas ya presentes (todas del batch actual)")
        done = _existing_pairs(client) if n0 else set()
        pending = [i for i in range(len(questions))
                   if (chunk_ids[i], questions[i]) not in done]
        print(f"pendientes: {len(pending)}")
        if dry or not pending:
            return 0

        poison: list[dict] = []
        posted = 0
        for b in range(0, len(pending), INSERT_BATCH):
            idxs = pending[b:b + INSERT_BATCH]
            payload = []
            for i in idxs:
                m = meta.get(chunk_ids[i], {})
                payload.append({
                    "chunk_id": chunk_ids[i],
                    "question": questions[i],
                    # float32 ≈ 7 dígitos significativos y pgvector almacena float4 →
                    # round(8) es sin pérdida efectiva y reduce el payload ~40%
                    "embedding": [round(float(x), 8) for x in embs[i]],
                    "source_file": srcs[i] or None,
                    "page_number": m.get("page_number"),
                    "product_model": m.get("product_model"),
                    "origin": m.get("origin"),
                    "ingest_batch": batch_tag,
                })
            posted += _insert_rows(client, payload, poison)
            if (b // INSERT_BATCH) % 20 == 0 or b + INSERT_BATCH >= len(pending):
                print(f"  {min(b + INSERT_BATCH, len(pending))}/{len(pending)} "
                      f"(posted {posted}, poison {len(poison)})", flush=True)

        if poison:
            plog = ROOT / "evals" / "s102_hyq_load_poison.jsonl"
            with plog.open("a", encoding="utf-8") as f:
                for p in poison:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
            print(f"⚠ {len(poison)} filas envenenadas → {plog}")

        # ── verificación EN EL MISMO RUN (Protocolo 1) ──
        n1 = _table_count(client)
        ok_count = n1 == len(questions)
        print(f"count final: {n1} / universo {len(questions)} → {'✅' if ok_count else '❌ MISMATCH'}")
        # smoke self-hit: la pregunta i debe recuperar SU chunk padre vía el RPC con sim≈1
        smoke_ok = True
        for i in (0, len(questions) // 2, len(questions) - 1):
            r = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_hyq", headers=HEADERS,
                            json={"query_embedding": [float(x) for x in embs[i]],
                                  "match_threshold": 0.45, "match_count": 5})
            r.raise_for_status()
            hits = r.json()
            hit = any(h["chunk_id"] == chunk_ids[i] and h["similarity"] > 0.99 for h in hits)
            smoke_ok &= hit
            print(f"  smoke self-hit #{i}: {'✅' if hit else '❌'} "
                  f"(top={hits[0]['similarity']:.4f} · {len(hits)} hits)" if hits
                  else f"  smoke self-hit #{i}: ❌ 0 hits")
        print(f"\nLOAD {'✅ COMPLETO' if ok_count and smoke_ok and not poison else '⚠ REVISAR'}")
        return 0 if (ok_count and smoke_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
