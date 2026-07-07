#!/usr/bin/env python3
"""s101_hyq_embed.py — embebe las preguntas hipotéticas (hyq) a un cache .npz para el seam offline.

Piloto hyq (prereg `evals/s99_hyq_pilot_prereg.md`, dúo-endurecido s99): las preguntas generadas
(`evals/s99_hyq_generated.jsonl`) se embeben UNA vez (Voyage, doc-side — question↔question asimétrico
con la query real) y el seam `HYQ_PILOT_FILE` del retriever hace cos in-process. 0 escrituras en DB.

Salida: evals/s101_hyq_embeddings.npz (ids paralelos: chunk_id por pregunta) + resumen.
Coste: ~11-12k embeddings Voyage ≈ céntimos. Resumible (skip si el npz ya tiene la pregunta... simple:
re-embebe todo — es barato y evita estado).
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

import numpy as np
import voyageai

HYQ = ROOT / "evals" / "s99_hyq_generated.jsonl"
OUT = ROOT / "evals" / "s101_hyq_embeddings.npz"
MODEL = "voyage-4-large"          # el MISMO del corpus chunks_v2 (paridad de espacio)
BATCH = 128


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    questions, chunk_ids, srcs = [], [], []
    bad = n_dup = n_capped = n_dupchunk = n_excl = 0
    CAP_PER_CHUNK = 4                # prereg: "2-4 preguntas por chunk" — el parser del generador no capaba (fix dúo s101)
    # H2 (dúo s101): MIE-MI-310 = ZXAE/ZXEE, el doc del que hp009 fue DES-anclado (pdfs_used stale) —
    # sus preguntas invadirían el pool de hp009 con la familia equivocada → FUERA del índice.
    EXCLUDE_SRC = ("MIE-MI-310",)
    seen_global: set[str] = set()    # dedup GLOBAL normalizado (duplicados compiten por slots del pool)
    seen_chunks: set[str] = set()    # H1 (dúo s101): el jsonl s99 tiene 2 registros/chunk → keep-FIRST por chunk_id
    kept_by_chunk: dict[str, int] = {}
    for line in HYQ.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue
        cid = r["chunk_id"]
        src = r.get("source_file") or ""
        if any(x in src for x in EXCLUDE_SRC):
            n_excl += 1
            continue
        if cid in seen_chunks:       # registro DUPLICADO del mismo chunk (re-generación s99) → skip entero
            n_dupchunk += 1
            continue
        seen_chunks.add(cid)
        for q in r.get("questions") or []:
            q = (q or "").strip()
            if len(q) < 15:          # ruido/fragmentos
                continue
            norm = " ".join(q.lower().split())
            if norm in seen_global:
                n_dup += 1
                continue
            if kept_by_chunk.get(cid, 0) >= CAP_PER_CHUNK:   # cap por CHUNK_ID, no por línea
                n_capped += 1
                continue
            seen_global.add(norm)
            kept_by_chunk[cid] = kept_by_chunk.get(cid, 0) + 1
            questions.append(q)
            chunk_ids.append(cid)
            srcs.append(src)
    print(f"{len(questions)} preguntas de {len(set(chunk_ids))} chunks "
          f"({bad} malas, {n_dupchunk} registros-dup-chunk, {n_dup} dups-texto, "
          f"{n_capped} sobre-cap, {n_excl} excluidos MI-310)")

    vo = voyageai.Client()          # VOYAGE_API_KEY del entorno
    embs = []
    for i in range(0, len(questions), BATCH):
        res = vo.embed(questions[i:i + BATCH], model=MODEL, input_type="document")
        embs.extend(res.embeddings)
        if (i // BATCH) % 10 == 0:
            print(f"  {i + len(res.embeddings)}/{len(questions)}…", flush=True)
    arr = np.asarray(embs, dtype=np.float32)
    # normalizar para cos = dot (Voyage ya normaliza, pero garantizarlo es barato)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms
    np.savez_compressed(OUT, embeddings=arr,
                        chunk_ids=np.array(chunk_ids), sources=np.array(srcs),
                        questions=np.array(questions, dtype=object))
    print(f"→ {OUT.name}: {arr.shape} ({arr.nbytes / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
