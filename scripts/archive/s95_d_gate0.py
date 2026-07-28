"""s95 Piloto D — GATE-0 recall-safe ($0, sin LLM). Pre-registro: evals/s95_redesign_pilots.md v2 [D3].

Para cada qid con hechos en retrieval-miss: (a) ¿el resolver adjudica el doc-aguja
(allowed_sources)?; (b) ¿la página-aguja (citations del gold) existe en el outline
que verá el selector LLM (headings + tablas por página del extraction store, ±1 por
el drift store↔DB)? Si el outline no contiene la página-aguja, el LLM nunca la verá
→ arreglar ANTES de gastar. Criterio: 8/8 en los qids con doc-target adjudicado.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "add")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402
import yaml  # noqa: E402

from s94_f1_generate import item_text, store_pages  # noqa: E402
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402

_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

MISS_QIDS = ["cat013", "cat016", "hp001", "hp006", "hp011", "hp012", "hp013", "hp014", "hp018"]


def sha_for_doc(source_file: str) -> str | None:
    with httpx.Client(timeout=10.0) as c:
        r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                  params={"select": "extraction_sha256",
                          "source_file": f"eq.{source_file}",
                          "extraction_sha256": "not.is.null", "limit": "1"})
        rows = r.json() if r.status_code in (200, 206) else []
    return rows[0]["extraction_sha256"] if rows else None


def outline_for_page(pages: list, idx: int) -> str:
    """Línea de outline de UNA página del store: headings + tablas (título/1ª fila)."""
    if idx < 0 or idx >= len(pages):
        return ""
    parts: list[str] = []
    for it in (pages[idx].get("items") or []):
        t = it.get("type")
        if t == "heading":
            txt = item_text(it).strip().replace("\n", " ")[:90]
            if txt:
                parts.append(txt)
        elif t == "table":
            rows = it.get("rows") or []
            head = " | ".join(str(x) for x in (rows[0] if rows else [])[:6])[:110]
            parts.append(f"[tabla] {head}" if head else "[tabla]")
    return " · ".join(parts)


def main() -> int:
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}
    from src.rag.catalog_resolver import resolve_for_retrieval

    ok = fail = 0
    for qid in MISS_QIDS:
        g = golds[qid]
        _models, res = resolve_for_retrieval(g["question"], [])
        res = res or {}
        allowed = set(res.get("allowed_sources") or [])
        cits = g.get("citations") or []
        # doc-aguja + páginas-aguja desde las citations del gold
        needle: dict[str, set[int]] = {}
        for c in cits:
            doc = c.get("source_file") or c.get("pdf") or c.get("doc") or ""
            page = c.get("page") or c.get("page_number")
            if doc and page:
                needle.setdefault(str(doc).replace(".pdf", ""), set()).add(int(page))
        if not needle:
            for d in (g.get("pdfs_used") or []):
                needle.setdefault(str(d).replace(".pdf", ""), set())
        for doc, pgs in needle.items():
            in_resolver = doc in allowed
            sha = sha_for_doc(doc)
            pages = store_pages(sha) if sha else []
            page_hits = []
            for p in sorted(pgs):
                # drift ±1: la página DB p ≈ índices store {p-2, p-1, p}
                lines = [outline_for_page(pages, i) for i in (p - 2, p - 1, p)]
                page_hits.append((p, any(ln for ln in lines)))
            all_pages_ok = all(h for _, h in page_hits) if page_hits else bool(pages)
            status = "OK " if (in_resolver and all_pages_ok and sha) else "FAIL"
            if status == "OK ":
                ok += 1
            else:
                fail += 1
            print(f"[{status}] {qid} · {doc[:44]:44s} resolver={'sí' if in_resolver else 'NO'} "
                  f"sha={'sí' if sha else 'NO'} páginas={[(p, 'sí' if h else 'NO') for p, h in page_hits] or '(doc-level)'}")
    print(f"\nGATE-0: {ok} OK · {fail} FAIL (criterio pre-registrado: docs-target adjudicados = 8/8)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
