#!/usr/bin/env python
"""s282 QA-s83 — LQAS CONFIRMATORY RE-DRAW (n=59, 0-defect acceptance).

Confirmatory LQAS sample over the RE-SCOPED auto-apply cohort (v2):
  - lot = documents receiving >=1 auto-apply write under the re-scoped rule:
    doc_type fill (536) OR language-SINGLETON fill (304). pm = noop always.
    language-MULTI is ADVISORY (excluded from auto-apply) -> not a lot write.
  - The 12 pure-noop auto rows (no doc_type fill, no language-singleton) drop out.

Draw is deterministic, stratified by brand (largest-remainder), NEW seed
(v1 draw used seed 282; this re-draw uses REDRAW_SEED, declared below). Fresh
independent draw: v1 rows are NOT excluded; any coincidental overlap is reported.

READ-ONLY. SELECT-only (PostgREST GET). Zero writes, zero paid model calls.
Emits a verification bundle JSON for manual, content-based adjudication.
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

os.environ["CHUNKS_TABLE"] = "chunks_v2"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import src.config as cfg  # noqa: E402

RESULT_V2 = ROOT / "evals/s282_qa_s83_result_v2.json"
OUT = ROOT / "evals/s282_qa_s83_lqas_redraw_bundle.json"

LQAS_N = 59
V1_SEED = 282
REDRAW_SEED = 592  # distinct from v1 (282); encodes n=59 round-2
CONTENT_CHUNKS = 10
CONTENT_HEAD = 600

_H: dict[str, str] = {}
_BASE = ""


def _init_http() -> None:
    global _H, _BASE
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable")
    _H = {"apikey": cfg.SUPABASE_SERVICE_KEY,
          "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}"}
    _BASE = cfg.SUPABASE_URL.rstrip("/")


def _get(table: str, params: dict[str, str]) -> httpx.Response:
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=_H, params=params, timeout=90)
    resp.raise_for_status()
    return resp


def fetch_content(sf: str) -> list[dict[str, Any]]:
    rows = _get("chunks_v2", {
        "source_file": f"eq.{sf}",
        "select": "page_number,chunk_index,section_title,content",
        "order": "page_number.asc.nullslast,chunk_index.asc",
        "limit": str(CONTENT_CHUNKS),
    }).json()
    out = []
    for r in rows:
        content = str(r.get("content") or "").strip().replace("\n", " ")
        out.append({"page": r.get("page_number"),
                    "section_title": (str(r.get("section_title") or "").strip())[:100],
                    "head": content[:CONTENT_HEAD]})
    return out


def in_lot(r: dict[str, Any]) -> bool:
    fp = r["fill_plan"]
    return bool(fp.get("doc_type_fill")) or bool(fp.get("language_fill_singleton"))


def brand_stratified_sample(lot_rows: list[dict[str, Any]], n: int, seed: int) -> list[str]:
    by_brand: dict[str, list[str]] = {}
    for r in sorted(lot_rows, key=lambda x: x["source_file"]):
        by_brand.setdefault(r["brand"], []).append(r["source_file"])
    total = sum(len(v) for v in by_brand.values())
    raw = {b: n * len(v) / total for b, v in by_brand.items()}
    alloc = {b: int(raw[b]) for b in by_brand}
    rem = n - sum(alloc.values())
    for b, _ in sorted(by_brand.items(),
                       key=lambda kv: (-(raw[kv[0]] - int(raw[kv[0]])), kv[0]))[:rem]:
        alloc[b] += 1
    rng = random.Random(seed)
    picked: list[str] = []
    for b in sorted(by_brand.keys()):
        pool = sorted(by_brand[b])
        k = min(alloc.get(b, 0), len(pool))
        picked += sorted(rng.sample(pool, k)) if k else []
    return sorted(picked), alloc


def main() -> None:
    d = json.load(open(RESULT_V2, encoding="utf-8"))
    recs = d["records"]
    v1_sample = set(d["lqas"]["sample_source_files"])
    auto = [r for r in recs if r["write_op"] in ("corroborate_noop", "fill_language_doctype")]
    lot = [r for r in auto if in_lot(r)]
    rec_by_sf = {r["source_file"]: r for r in recs}

    sample_sfs, alloc = brand_stratified_sample(lot, LQAS_N, REDRAW_SEED)
    overlap = sorted(set(sample_sfs) & v1_sample)

    _init_http()
    rows_out = []
    for sf in sample_sfs:
        r = rec_by_sf[sf]
        fp = r["fill_plan"]
        rows_out.append({
            "source_file": sf,
            "brand": r["brand"],
            "write_op": r["write_op"],
            "doc_level_pm": r.get("doc_level_pm"),
            "s83_primaries": r.get("s83_primaries"),
            "in_v1_draw": sf in v1_sample,
            "fill": {
                "doc_type_fill": fp.get("doc_type_fill"),
                "doc_type_value": fp.get("doc_type_value"),
                "doc_type_differ": fp.get("doc_type_differ"),
                "language_fill_singleton": fp.get("language_fill_singleton"),
                "language_fill_multi_advisory": fp.get("language_fill_multi_advisory"),
                "language_value": fp.get("language_value"),
                "language_contradict": fp.get("language_contradict"),
            },
            "content_sample": fetch_content(sf),
        })

    payload = {
        "n": LQAS_N,
        "v1_seed": V1_SEED,
        "redraw_seed": REDRAW_SEED,
        "lot_size": len(lot),
        "brand_alloc": alloc,
        "sample_brand_counts": dict(Counter(r["brand"] for r in rows_out)),
        "overlap_with_v1": overlap,
        "n_overlap": len(overlap),
        "sample_source_files": sample_sfs,
        "rows": rows_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("lot_size:", len(lot))
    print("redraw_seed:", REDRAW_SEED, "(v1 seed:", V1_SEED, ")")
    print("brand_alloc:", json.dumps(alloc, ensure_ascii=False))
    print("sample_brand_counts:", json.dumps(payload["sample_brand_counts"], ensure_ascii=False))
    print("n_overlap_with_v1:", len(overlap))
    print("overlap:", overlap)
    print("wrote:", OUT)


if __name__ == "__main__":
    main()
