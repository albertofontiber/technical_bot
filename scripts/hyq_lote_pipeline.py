#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hyq por LOTE (s315/#68): generar → embeber → cargar SOLO los docs de un lote nuevo.

POR QUÉ. El camino corpus-wide (s102) asume un vintage ÚNICO global: `s101_hyq_embed`
re-embebe TODO el jsonl y el loader `s102_hyq_load` ABORTA si la tabla contiene filas de
otro `ingest_batch`. Un lote de ingesta nuevo (p.ej. Casmar s314, 1.091 chunks con 0 hyq)
no puede entrar por ahí sin re-cargar 70k filas. Este pipeline crea un vintage POR LOTE:
jsonl + npz propios y `ingest_batch=hyq-v1-<sha16 del npz del lote>`, con las MISMAS
piezas pineadas del canal:
  · PROMPT + few-shot no-circular importados de `s99_hyq_generate` (congelados);
  · criterios de parse importados de `s101_hyq_embed.parse_questions(jsonl_path)`
    (keep-FIRST, cap 4/chunk, dedup, len>=15, exclusión MIE-MI-310);
  · receta de embedding `s101_hyq_embed.embed_questions` (voyage-4-large, doc, L2);
  · inserción `s102_hyq_load._insert_rows` (on_conflict ignore-duplicates, bisección).
Diferencias DELIBERADAS con el loader global, declaradas:
  · NO aborta por filas de otros batches (append es el propósito) y NO ofrece --wipe;
  · dedup CROSS-VINTAGE: antes de insertar, descarta preguntas cuyo texto normalizado
    ya existe en la tabla (el parse global deduplicaba corpus-wide; un lote no ve a los
    demás — sin esto, duplicados casi-idénticos competirían por slots del pool);
  · verificación por `ingest_batch` del lote (no por count global) + smoke self-hit.
Modelo de generación PINEADO al vintage del corpus hyq (sonnet-4-6, run s102) — el
LLM_MODEL vivo del bot (Opus 5 desde s308) NO se hereda: cambiarlo sería mezclar
generadores sin medir. Override consciente: --model.

Uso (máquina con claves; dry-run por defecto):
  python scripts/hyq_lote_pipeline.py --docs evals/derive_lote_<t>_docs.txt --tag <t>
  python scripts/hyq_lote_pipeline.py --docs ... --tag <t> --aplicar
Fases resumibles: el jsonl del lote acumula (resume por done-set), el npz se regenera
del jsonl (barato a escala lote), la carga es idempotente por UNIQUE(chunk_id,question).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from s99_hyq_generate import PROMPT, _docs_and_fewshot  # noqa: E402  (congelados)
from s101_hyq_embed import embed_questions, parse_questions  # noqa: E402
from s102_hyq_load import (  # noqa: E402
    HEADERS, INSERT_BATCH, TABLE, _existing_pairs, _insert_rows,
)
from src.config import ANTHROPIC_API_KEY, SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

# Vintage del corpus hyq vivo (run s102): NO heredar LLM_MODEL (hoy Opus 5).
HYQ_GEN_MODEL = "claude-sonnet-4-6"
MAX_ERRORES_SEGUIDOS = 20   # fail-fast del corpus-wide, heredado
COSTE_POR_CHUNK_USD = 0.004


def _norm_q(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def _chunks_del_lote(client: httpx.Client, docs: list[str]) -> list[dict]:
    filas: list[dict] = []
    for doc in docs:
        r = client.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=HEADERS,
                       params={"select": "id,content,product_model,manufacturer,"
                                         "source_file,page_number",
                               "source_file": f"eq.{doc}",
                               "order": "page_number.asc", "limit": "2000"})
        r.raise_for_status()
        filas.extend(r.json())
    return filas


def fase_generar(client: httpx.Client, docs: list[str], jsonl: Path,
                 model: str, aplicar: bool) -> int:
    chunks = _chunks_del_lote(client, docs)
    done: set[str] = set()
    if jsonl.exists():
        for ln in jsonl.read_text(encoding="utf-8-sig").splitlines():
            try:
                done.add(json.loads(ln)["chunk_id"])
            except Exception:
                pass
    pend = [c for c in chunks
            if c["id"] not in done and len((c.get("content") or "").strip()) >= 40]
    print(f"[generar] chunks del lote: {len(chunks)} · ya en jsonl: {len(done)} "
          f"· pendientes: {len(pend)} · coste ≈ ${len(pend) * COSTE_POR_CHUNK_USD:.2f} "
          f"({model})")
    if not aplicar or not pend:
        return 0

    import anthropic
    cl = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    # paridad exacta con s102_hyq_corpuswide:93-124 (mismo prompt, mismo parser, mismo
    # registro — incluida la sustitución de pm vacío ANTES de escribir, como el corpus)
    _docs, fewshot = _docs_and_fewshot()
    fewshot_txt = "\n".join(f"- {q}" for q in fewshot)
    temp_kw = {} if re.search(r"-5|fable|mythos", model) else {"temperature": 0}
    errores_seguidos = 0
    with jsonl.open("a", encoding="utf-8") as fh:
        for i, c in enumerate(pend):
            prod = c.get("product_model") or "el equipo del manual"
            content = (c.get("content") or "")[:2000]
            try:
                msg = cl.messages.create(
                    model=model, max_tokens=300, **temp_kw,
                    messages=[{"role": "user", "content": PROMPT.format(
                        producto=prod, fewshot=fewshot_txt, content=content)}])
                raw = "".join(b.text for b in msg.content
                              if getattr(b, "type", "") == "text").strip()
                errores_seguidos = 0
            except Exception as exc:
                # error de API NO se escribe (S4 dúo s102): reintenta en el próximo run
                errores_seguidos += 1
                print(f"  ERROR chunk {c['id'][:8]}: {type(exc).__name__} "
                      f"({errores_seguidos}/{MAX_ERRORES_SEGUIDOS})")
                if errores_seguidos >= MAX_ERRORES_SEGUIDOS:
                    raise SystemExit("demasiados errores seguidos — abortado (resume OK)")
                time.sleep(2)
                continue
            qs = [q.strip("-• ").strip() for q in raw.splitlines()
                  if q.strip() and "NONE" not in q]
            fh.write(json.dumps({
                "chunk_id": c["id"], "source_file": c.get("source_file"),
                "page_number": c.get("page_number"), "product_model": prod,
                "manufacturer": c.get("manufacturer"),
                "questions": qs, "origin": "synthetic",
            }, ensure_ascii=False) + "\n")
            if i % 50 == 0:
                fh.flush()
                print(f"  {i}/{len(pend)}", flush=True)
    return 0


def fase_embeber(jsonl: Path, npz: Path, aplicar: bool) -> int:
    questions, chunk_ids, srcs, st = parse_questions(jsonl)
    print(f"[embeber] parse del lote: {len(questions)} preguntas / "
          f"{len(set(chunk_ids))} chunks ({st})")
    if not aplicar:
        return 0
    arr = embed_questions(questions)
    np.savez_compressed(npz, embeddings=arr, chunk_ids=np.array(chunk_ids),
                        sources=np.array(srcs),
                        questions=np.array(questions, dtype=object))
    print(f"  → {npz.name}: {arr.shape}")
    return 0


def fase_cargar(client: httpx.Client, jsonl: Path, npz: Path, aplicar: bool) -> int:
    questions, chunk_ids, srcs, _st = parse_questions(jsonl)
    d = np.load(npz, allow_pickle=True)
    if [str(x) for x in d["questions"]] != questions or \
       [str(x) for x in d["chunk_ids"]] != chunk_ids:
        print("❌ npz del lote DESALINEADO con su jsonl — re-corre la fase de embed")
        return 1
    embs = d["embeddings"].astype(np.float32)
    batch_tag = f"hyq-v1-{hashlib.sha256(npz.read_bytes()).hexdigest()[:16]}"
    print(f"[cargar] npz alineado {embs.shape} · ingest_batch={batch_tag} (APPEND)")

    # dedup CROSS-VINTAGE contra TODO lo existente (pares exactos + texto normalizado)
    existentes = _existing_pairs(client)
    textos_existentes = {_norm_q(q) for _cid, q in existentes}
    meta: dict[str, dict] = {}
    for ln in jsonl.read_text(encoding="utf-8-sig").splitlines():
        try:
            r = json.loads(ln)
            meta.setdefault(r["chunk_id"], {
                "page_number": r.get("page_number"),
                "product_model": r.get("product_model"),
                "origin": r.get("origin") or "synthetic"})
        except Exception:
            continue
    pend, dup_cross = [], 0
    for i in range(len(questions)):
        if (chunk_ids[i], questions[i]) in existentes:
            continue
        if _norm_q(questions[i]) in textos_existentes:
            dup_cross += 1
            continue
        pend.append(i)
    print(f"  pendientes: {len(pend)} · dup-cross-vintage descartadas: {dup_cross}")
    if not aplicar or not pend:
        return 0

    poison: list[dict] = []
    posted = 0
    for b in range(0, len(pend), INSERT_BATCH):
        payload = []
        for i in pend[b:b + INSERT_BATCH]:
            m = meta.get(chunk_ids[i], {})
            payload.append({
                "chunk_id": chunk_ids[i], "question": questions[i],
                "embedding": [round(float(x), 8) for x in embs[i]],
                "source_file": srcs[i] or None,
                "page_number": m.get("page_number"),
                "product_model": m.get("product_model"),
                "origin": m.get("origin"), "ingest_batch": batch_tag,
            })
        posted += _insert_rows(client, payload, poison)
    print(f"  insertadas: {posted} · poison: {len(poison)}")

    # verificación por BATCH del lote + smoke self-hit (Protocolo 1)
    r = client.get(f"{SUPABASE_URL}/rest/v1/{TABLE}",
                   headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                   params={"select": "id", "ingest_batch": f"eq.{batch_tag}"})
    n_batch = int((r.headers.get("content-range") or "/0").split("/")[-1])
    ok_count = n_batch == len(pend) and not poison
    print(f"  filas del batch en tabla: {n_batch} / esperadas {len(pend)} "
          f"→ {'✅' if ok_count else '❌'}")
    smoke_ok = True
    for j in (0, len(pend) // 2, len(pend) - 1):
        i = pend[j]
        rr = client.post(f"{SUPABASE_URL}/rest/v1/rpc/match_hyq", headers=HEADERS,
                         json={"query_embedding": [float(x) for x in embs[i]],
                               "match_threshold": 0.45, "match_count": 5})
        rr.raise_for_status()
        hits = rr.json()
        hit = any(h["chunk_id"] == chunk_ids[i] and h["similarity"] > 0.99
                  for h in hits)
        smoke_ok &= hit
        print(f"  smoke self-hit: {'✅' if hit else '❌'}")
    print("  ⚠ recuerda VACUUM tras cargas grandes (fantasmas HNSW, DEC-088)")
    return 0 if (ok_count and smoke_ok) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="fichero con un source_file por línea")
    ap.add_argument("--tag", required=True, help="nombre del lote (p.ej. casmar314)")
    ap.add_argument("--model", default=HYQ_GEN_MODEL)
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--fase", choices=["generar", "embeber", "cargar", "todo"],
                    default="todo")
    a = ap.parse_args()
    docs = [ln.strip() for ln in open(a.docs, encoding="utf-8") if ln.strip()]
    jsonl = ROOT / "evals" / f"hyq_lote_{a.tag}.jsonl"
    npz = ROOT / "evals" / f"hyq_lote_{a.tag}_embeddings.npz"
    with httpx.Client(timeout=180.0) as client:
        if a.fase in ("generar", "todo"):
            rc = fase_generar(client, docs, jsonl, a.model, a.aplicar)
            if rc:
                return rc
        if a.fase in ("embeber", "todo"):
            rc = fase_embeber(jsonl, npz, a.aplicar)
            if rc:
                return rc
        if a.fase in ("cargar", "todo"):
            return fase_cargar(client, jsonl, npz, a.aplicar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
