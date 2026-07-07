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
    bad = 0
    for line in HYQ.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue
        for q in r.get("questions") or []:
            q = (q or "").strip()
            if len(q) < 15:          # ruido/fragmentos
                continue
            questions.append(q)
            chunk_ids.append(r["chunk_id"])
            srcs.append(r.get("source_file") or "")
    print(f"{len(questions)} preguntas de {len(set(chunk_ids))} chunks ({bad} líneas malas skip)")

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
