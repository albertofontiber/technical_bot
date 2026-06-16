#!/usr/bin/env python3
"""s78 pre-pasos del Thread 2 (bar anti-trampa de Alberto): diagnosticar ANTES de construir.

cat022 (PASS-control que REGRESA con preview-2400, factcov 1->0 en s74 gate0): ¿el fix sirve PEOR
(veta), o es un bug latente que el reshuffle del rerank SURFACEA (no veta, es 2º objetivo)? Se traza
el top-5 @800 vs @2400 y qué chunk desplaza a la cita de cat022.

cat007 (Paso 0b: 0 citas en el pool-50, PERO s71 decía "diversify expulsa Tabla3 rank#1/2"):
¿recall real (el chunk no entra) o artefacto de strict-match (el chunk está, la cita no machea
literal)? Se mira pool flags-off vs LEVER1_BROAD_FALLBACK, match strict vs loose, y existencia en corpus.

reach != PASS. Modal n=3 para el dado del reranker. Read-only.
Uso: python scripts/s78_prechecks.py
"""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
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
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import src.rag.retriever as rt  # noqa: E402
import src.rag.reranker as rk  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from src.config import RETRIEVAL_TOP_K, RERANK_TOP_K, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from strict_match import chunk_has_quote_strict  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
golds = {g["qid"]: g for g in yaml.safe_load((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8")) if g.get("qid")}


def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
def loose(content, quote):
    c, q = norm(content), norm(quote); frag = q[:50]
    return len(frag) >= 12 and frag in c
def short(c): return f"{(c.get('product_model') or '?')}|{(c.get('source_file') or '?')[:32]}|p{c.get('page_number')}"
def set_flags(**kw):
    for f in ("LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER", "LEVER2_IDENTITY", "LEVER2_PM_RESCUE"):
        os.environ.pop(f, None)
    for f, v in kw.items():
        if v: os.environ[f] = "on"


def quote_pos(pool, quote, matcher):
    return [i for i, c in enumerate(pool) if matcher(c.get("content") or "", quote)]


def modal_top5(question, pool, prev, n=3):
    rk.RERANK_PREVIEW_CHARS = prev
    if len(pool) <= RERANK_TOP_K:
        return pool, True
    import hashlib
    def ch(c): return hashlib.sha1((c.get("content") or "").encode()).hexdigest()[:10]
    runs = []
    for _ in range(n):
        t5 = rerank(question, list(pool), top_k=RERANK_TOP_K, strict=True)
        runs.append((tuple(ch(c) for c in t5), t5))
    modal = Counter(r[0] for r in runs).most_common(1)[0][0]
    t5 = next(t for k, t in runs if k == modal)
    return t5, len({r[0] for r in runs}) == 1


def main():
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

    # ---------- cat007: recall vs artefacto ----------
    print("=" * 90, "\n### PRE-CHECK cat007 — recall real o artefacto de strict-match\n", "=" * 90)
    g = golds["cat007"]; quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
    print(f"Q: {g['question'][:120]}")
    for tag, kw in [("flags-OFF (prod)", {}), ("LEVER1_BROAD_FALLBACK", {"LEVER1_BROAD_FALLBACK": True})]:
        set_flags(**kw)
        pool = rt.retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        print(f"\n[{tag}] pool={len(pool)}")
        for i, q in enumerate(quotes):
            ps, pl = quote_pos(pool, q, chunk_has_quote_strict), quote_pos(pool, q, loose)
            print(f"  cita{i+1}: strict@{ps or '—'}  loose@{pl or '—'}   «{q[:70]}»")
    # ¿existe en corpus? (content loose por fragmento)
    set_flags()
    for i, q in enumerate(quotes):
        frag = q[:40]
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H, timeout=30,
                      params={"content": f"ilike.*{frag}*", "select": "product_model,manufacturer,source_file", "limit": "5"})
        rows = r.json() if r.status_code == 200 else []
        print(f"  cita{i+1} en corpus (ilike frag): {len(rows)} hits -> {[(x.get('product_model'),(x.get('source_file') or '')[:28]) for x in rows[:3]]}")

    # ---------- cat022: ¿la regresión veta? ----------
    print("\n" + "=" * 90, "\n### PRE-CHECK cat022 — ¿preview-2400 sirve PEOR (veta) o surfacea bug latente?\n", "=" * 90)
    g = golds["cat022"]; quotes = [c["quote"] for c in (g.get("citations") or []) if c.get("quote")]
    print(f"Q: {g['question'][:120]}\ncitas={len(quotes)}: {[q[:60] for q in quotes]}")
    set_flags()  # prod
    pool = rt.retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
    pos = {i: quote_pos(pool, q, chunk_has_quote_strict) for i, q in enumerate(quotes)}
    print(f"pool={len(pool)}  cita-chunk en pool @ranks: {pos}")
    for prev in (800, 2400):
        t5, stable = modal_top5(g["question"], pool, prev)
        served = [i for i, q in enumerate(quotes) if any(chunk_has_quote_strict(c.get('content') or '', q) for c in t5)]
        print(f"\n[preview={prev}] {'estable' if stable else 'DADO'}  citas servidas en top-5: {served or 'NINGUNA'}")
        for j, c in enumerate(t5):
            mark = "  <-- cita" if any(chunk_has_quote_strict(c.get('content') or '', q) for q in quotes) else ""
            print(f"   top5[{j}] {short(c)}{mark}")
    print("\n(interpretación: si @2400 la cita-chunk SIGUE en el pool pero sale del top-5 desplazada por "
          "chunks del MISMO producto/tema = reshuffle del rerank; si entra contenido AJENO/peor = sirve peor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
