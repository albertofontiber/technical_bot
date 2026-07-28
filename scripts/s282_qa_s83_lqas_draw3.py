#!/usr/bin/env python
"""s282 QA-s83 — LQAS DRAW 3 (confirmatory, n=59, 0-defect acceptance) over v3 cohort.

Third confirmatory LQAS draw. The frame is the RE-GATED v3 auto-apply cohort
(``evals/s282_qa_s83_result_v3.json``) AFTER the category-plausibility guard removed
the Securiton ``_TD`` ``datasheet`` class (the defect that failed draw 2). Lot =
documents receiving >=1 auto-apply write under v3: doc_type fill OR language-SINGLETON
fill. pm = noop always. language-MULTI is ADVISORY (not a lot write).

Seed history (all declared): draw 1 = seed 282 (v1); draw 2 / re-draw = seed 592 (v2,
FAILED 1/59); draw 3 = seed 593 (this draw). Mersenne-Twister streams from distinct
integer seeds are independent regardless of numeric proximity; 593 = "n=59 · round-3".
Fresh independent draw: prior-draw rows are NOT excluded; coincidental overlap reported.

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

RESULT_V3 = ROOT / "evals/s282_qa_s83_result_v3.json"
RESULT_V2 = ROOT / "evals/s282_qa_s83_result_v2.json"
OUT = ROOT / "evals/s282_qa_s83_lqas_draw3_bundle.json"

LQAS_N = 59
V1_SEED = 282
V2_REDRAW_SEED = 592
DRAW3_SEED = 593   # distinct from 282 and 592; "n=59 · round-3"
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


def chunk_count(sf: str) -> int:
    resp = httpx.get(f"{_BASE}/rest/v1/chunks_v2", headers={**_H, "Prefer": "count=exact"},
                     params={"source_file": f"eq.{sf}", "select": "id", "limit": "1"}, timeout=90)
    resp.raise_for_status()
    return int(resp.headers.get("content-range", "*/0").split("/")[-1])


def in_lot(r: dict[str, Any]) -> bool:
    fp = r.get("fill_plan") or {}
    return bool(fp.get("doc_type_fill")) or bool(fp.get("language_fill_singleton"))


def brand_stratified_sample(lot_rows: list[dict[str, Any]], n: int, seed: int):
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
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    d = json.load(open(RESULT_V3, encoding="utf-8"))
    recs = d["records"]
    v2 = json.load(open(RESULT_V2, encoding="utf-8"))
    v1_sample = set(v2["lqas"]["sample_source_files"])          # seed 282 draw
    v2_sample = set(json.load(open(ROOT / "evals/s282_qa_s83_lqas_redraw_bundle.json",
                                   encoding="utf-8"))["sample_source_files"])  # seed 592 draw

    auto = [r for r in recs if r["write_op"] in ("corroborate_noop", "fill_language_doctype")]
    lot = [r for r in auto if in_lot(r)]
    rec_by_sf = {r["source_file"]: r for r in recs}

    sample_sfs, alloc = brand_stratified_sample(lot, LQAS_N, DRAW3_SEED)
    overlap_v1 = sorted(set(sample_sfs) & v1_sample)
    overlap_v2 = sorted(set(sample_sfs) & v2_sample)

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
            "chunks": chunk_count(sf),
            "in_v1_draw": sf in v1_sample,
            "in_v2_draw": sf in v2_sample,
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
        "v2_redraw_seed": V2_REDRAW_SEED,
        "draw3_seed": DRAW3_SEED,
        "lot_size": len(lot),
        "brand_alloc": alloc,
        "sample_brand_counts": dict(Counter(r["brand"] for r in rows_out)),
        "overlap_with_v1": overlap_v1,
        "n_overlap_v1": len(overlap_v1),
        "overlap_with_v2": overlap_v2,
        "n_overlap_v2": len(overlap_v2),
        "sample_source_files": sample_sfs,
        "rows": rows_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("lot_size:", len(lot))
    print("draw3_seed:", DRAW3_SEED, "(v1:", V1_SEED, "v2-redraw:", V2_REDRAW_SEED, ")")
    print("brand_alloc:", json.dumps(alloc, ensure_ascii=False))
    print("sample_brand_counts:", json.dumps(payload["sample_brand_counts"], ensure_ascii=False))
    print("n_overlap_v1:", len(overlap_v1), "n_overlap_v2:", len(overlap_v2))
    print("overlap_v1:", overlap_v1)
    print("overlap_v2:", overlap_v2)
    print("wrote:", OUT)


if __name__ == "__main__":
    main()
