#!/usr/bin/env python3
"""validate_s29_burial.py — DEC-005: ¿es el bug de merge plano de s29 (+ product_model
mal atribuido) el mecanismo del clúster 'manual equivocado'? ¿lo mitiga HyDE-ON?

Para cada pregunta, con HyDE OFF y ON, separa:
  - METADATA-MISLABEL : el product_model del manual objetivo != el modelo detectado en la
                        query (p.ej. Config-ES de PEARL etiquetado 'AC-220') -> el boosting
                        por modelo (keyword/diversify) NO lo alcanza.
  - BURIAL (bug s29)   : el manual objetivo SÍ aparece en vector amplio (top-50) pero NO en
                        el pool-15 real -> sus chunks vectoriales quedan ENTERRADOS bajo los
                        scores PLANOS por-path (0.65-0.85) del merge hibrido.
  - RECALL-MISS        : ni en vector top-50 -> recall genuino (embedding/chunking, mas hondo).
  - OK                 : el manual objetivo llega al pool-15 (su problema, si lo hay, es
                        within-doc / pagina, no acceso del manual).

HyDE se controla por monkeypatch de retriever.HYDE_ENABLED + se embebe la hipotesis a mano
para el vector amplio (replica lo que retrieve_chunks haria).

Uso: python scripts/validate_s29_burial.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import re
import sys
from collections import Counter
from pathlib import Path
import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
sys.path.insert(0, str(ROOT))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import src.rag.retriever as R  # noqa: E402
from src.rag.retriever import (extract_product_models, vector_search,  # noqa: E402
                               retrieve_chunks)
from src.ingestion.embedder import embed_query  # noqa: E402
from src.rag.hyde import generate_hypothetical_document  # noqa: E402

URL = os.environ["SUPABASE_URL"]; KEY = os.environ["SUPABASE_SERVICE_KEY"]
HDR = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
GOLD = {g["qid"]: g for g in yaml.safe_load((ROOT / "evals/gold_answers_v1.yaml").read_text("utf-8"))}

CLUSTER = ["hp017", "hp005", "hp008", "hp011", "hp018"]  # 'manual equivocado'
WITHIN = ["hp006", "hp019"]                               # within-doc (contraste)

_TOK = re.compile(r"[A-Za-z0-9]{2,}(?:[-_][A-Za-z0-9]+)*")


def target_tokens(g: dict) -> list[str]:
    prov = g.get("_provenance") or {}
    txt = " ".join([prov.get("fuente", ""),
                    " ".join(c.get("manual", "") for c in (g.get("citations") or [])),
                    " ".join(g.get("pdfs_used") or [])])
    txt = re.sub(r"\([^)]*\)", " ", txt)
    out, seen = [], set()
    for m in _TOK.findall(txt):
        if len(m) >= 5 and re.search(r"\d", m) and m.lower() not in seen:
            seen.add(m.lower()); out.append(m)
    return out[:6]


def _nid(s: str) -> str:
    return re.sub(r"[-_ .]", "", (s or "").lower())


def matches(src: str, toks: list[str]) -> bool:
    s = _nid(src)
    return any(len(_nid(t)) >= 5 and (_nid(t) in s or s in _nid(t)) for t in toks)


def product_models_for(toks: list[str]) -> dict:
    pm = Counter()
    for t in toks:
        try:
            rows = httpx.get(f"{URL}/rest/v1/chunks_v2", headers=HDR,
                             params={"select": "product_model", "source_file": f"ilike.*{t}*",
                                     "limit": "400"}, timeout=30).json()
            for r in rows:
                pm[r.get("product_model") or "∅"] += 1
        except Exception:
            pass
    return dict(pm)


def run(qid: str, hyde: bool) -> dict:
    g = GOLD[qid]; q = g["question"]
    R.HYDE_ENABLED = hyde
    models = extract_product_models(q)
    toks = target_tokens(g)
    pm = product_models_for(toks)
    # modelo detectado presente en el product_model del manual objetivo?
    det = {_nid(m) for m in models}
    mislabel = bool(pm) and not any(any(d in _nid(k) for d in det) for k in pm if k != "∅")

    pool = retrieve_chunks(q, top_k=15)
    pool_src = [c.get("source_file") for c in pool]
    in_pool = any(matches(s or "", toks) for s in pool_src)

    emb_text = generate_hypothetical_document(q) if hyde else q
    emb = embed_query(emb_text)
    wide = vector_search(q, top_k=50, precomputed_embedding=emb)
    wide_hits = [(i, c.get("source_file"), round(c.get("similarity", 0), 3))
                 for i, c in enumerate(wide) if matches(c.get("source_file") or "", toks)]
    in_wide = bool(wide_hits)

    if in_pool:
        cls = "OK (manual llega al pool)"
    elif mislabel and in_wide:
        cls = "METADATA-MISLABEL + BURIAL"
    elif mislabel:
        cls = "METADATA-MISLABEL"
    elif in_wide:
        cls = "BURIAL (bug s29)"
    else:
        cls = "RECALL-MISS"
    return {"qid": qid, "hyde": hyde, "models": models, "target_tokens": toks,
            "target_product_model": pm, "mislabel": mislabel,
            "in_pool15": in_pool, "in_widevec50": in_wide,
            "wide_rank_sim": wide_hits[:3], "clasificacion": cls}


def main() -> int:
    rows = []
    for group, qids in (("CLÚSTER manual-equivocado", CLUSTER), ("WITHIN-DOC (contraste)", WITHIN)):
        print(f"\n########## {group} ##########")
        for qid in qids:
            print(f"\n=== {qid}: {GOLD[qid]['question'][:70]} ===")
            for hyde in (False, True):
                r = run(qid, hyde)
                rows.append(r)
                tag = "HyDE-ON " if hyde else "HyDE-OFF"
                print(f"  [{tag}] {r['clasificacion']}")
                print(f"           models={r['models']} | target_pm={r['target_product_model']}")
                print(f"           in_pool15={r['in_pool15']} in_widevec50={r['in_widevec50']} "
                      f"wide={r['wide_rank_sim']}")
    (ROOT / "evals/dec005_burial_validation.yaml").write_text(
        yaml.safe_dump(rows, allow_unicode=True, sort_keys=False), "utf-8")
    print("\n" + "=" * 60)
    print("RESUMEN (clasificación por pregunta, OFF→ON):")
    by = {}
    for r in rows:
        by.setdefault(r["qid"], {})[r["hyde"]] = r["clasificacion"]
    for qid, d in by.items():
        print(f"  {qid}: OFF={d.get(False)}  |  ON={d.get(True)}")
    print("\nDetalle: evals/dec005_burial_validation.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
