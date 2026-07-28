#!/usr/bin/env python3
"""s79 — validación del localizador grado-audit sobre ATOMIC_FACTS (no citations-bundle).

Ajuste post-dúo + post-cat007: el unit de localización son los `atomic_facts` (1 hecho, tamaño-chunk),
NO las `citations` (que empaquetan varias tablas -> ningún chunk las contiene enteras -> falso "no
localizada"). Source-tie a los pdfs del gold. Reporta, por hecho: localizado? + score + chunk + los
TOKENS DISTINTIVOS AUSENTES (señal de inferencia/paráfrasis del gold, p.ej. cat007 'failsafe').

$0, read-only. Uso: python scripts/s79_locator_validate.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import re
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.rag.retriever import SUPABASE_URL, SUPABASE_SERVICE_KEY, CHUNKS_TABLE  # noqa: E402
from audit_locator import locate, citation_score, missing_distinctive  # noqa: E402

FIVE = ["cat016", "cat007", "hp001", "hp011", "hp017"]
HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def source_key(s: str) -> str:
    toks = re.findall(r"[A-Za-z0-9]{4,}", s or "")
    toks = [t for t in toks if any(c.isdigit() for c in t)] or toks
    return max(toks, key=len) if toks else ""


def fetch_by_source(key: str, limit: int = 500) -> list[dict]:
    with httpx.Client(timeout=30.0) as c:
        r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=HEADERS,
                  params={"source_file": f"ilike.*{key}*",
                          "select": "id,content,source_file,product_model", "limit": str(limit)})
        r.raise_for_status()
        return r.json()


def gold_sources(g: dict) -> list[str]:
    srcs = list(g.get("pdfs_used") or [])
    for cit in g.get("citations") or []:
        m = cit.get("manual") or cit.get("source_file")
        if m and m not in srcs:
            srcs.append(m)
    return srcs


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    data = yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in data if g.get("qid")}

    n_found = n_total = 0
    infer_flags = []
    pairs = []  # (afirmacion del gold, evidencia del chunk) para el triage de inferencias
    for qid in FIVE:
        g = golds[qid]
        srcs = gold_sources(g)
        # fetch + dedup chunks de todas las fuentes del gold
        seen, chunks = set(), []
        for s in srcs:
            k = source_key(s)
            if not k:
                continue
            for c in fetch_by_source(k):
                if c["id"] not in seen:
                    seen.add(c["id"]); chunks.append(c)
        facts = [f for f in (g.get("atomic_facts") or []) if f.get("texto")]
        print(f"\n{'='*74}\n{qid}: {len(facts)} atomic_facts | {len(chunks)} chunks de {len(srcs)} fuentes")
        for i, f in enumerate(facts):
            texto = f["texto"]
            hits = locate(texto, chunks, gold_sources=srcs, require_source=True)
            n_total += 1
            if hits:
                n_found += 1
                top = hits[0]
                chunk_content = next(c["content"] for c in chunks if c["id"] == top["id"])
                miss = missing_distinctive(texto, chunk_content)
                tag = f"  <-- INFERENCIA? faltan {miss}" if miss else ""
                print(f"  fact[{i}] ({f.get('tipo','')}) score={top['score']} pm={top['product_model']}{tag}")
                if miss:
                    infer_flags.append((qid, i, miss))
                    pairs.append({"qid": qid, "fact_idx": i, "tipo": f.get("tipo"),
                                  "gold_texto": texto, "gold_valor": f.get("valor"),
                                  "missing_tokens": miss, "chunk_id": top["id"],
                                  "chunk_content": chunk_content[:1600]})
            else:
                best = max((citation_score(texto, c.get("content") or "") for c in chunks), default=0)
                print(f"  fact[{i}] ({f.get('tipo','')}): NO localizado (best={best:.2f})  texto={texto[:60]!r}")

    print(f"\n{'='*74}\nRESUMEN: {n_found}/{n_total} atomic_facts localizados")
    print(f"Flags de inferencia/paráfrasis (valor presente, faltan términos del enunciado): {len(infer_flags)}")
    for qid, i, miss in infer_flags:
        print(f"  {qid} fact[{i}]: faltan {miss}")
    import json
    (ROOT / "evals" / "s79_inference_pairs.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nPares (afirmación↔evidencia) para triage -> evals/s79_inference_pairs.json ({len(pairs)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
