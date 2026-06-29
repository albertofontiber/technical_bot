#!/usr/bin/env python3
"""s83_sample_measure.py — mide la TASA DE ADJUDICACION real del dúo sobre una muestra ALEATORIA
de ~40 docs del corpus (no los 15 pilot hand-picked-dificiles). Responde la Q3 de Alberto:
¿que % de los 1014 tendra que revisar? Clasifica cada doc:
  agree    = covered sets identicos -> auto-acepto.
  superset = uno ⊆ otro (sobre/sub-inclusion) -> mayormente auto bajo recall-favoring.
  conflict = ninguno ⊆ otro (desacuerdo genuino) -> REVISION humana.
Reusa el extractor v4 (s83_pilot_extract_duo). Resumable. Read-only sobre la DB. Coste ~$10-13.
"""
from __future__ import annotations
import json
import random
import sys
from collections import Counter
from pathlib import Path

import httpx
from anthropic import Anthropic
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import s83_pilot_extract_duo as P  # noqa: E402  (reusa SYS/SCHEMA/call_opus/call_gpt/fetch_content/covered_set)
from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY  # noqa: E402

N = 40
SEED = 42
OUT = ROOT / "evals" / "s83_sample_extraction.jsonl"
PILOT_SF = {sf for sf, _ in P.PILOT}


def all_source_files():
    sfs = set()
    off = 0
    while True:
        r = httpx.get(P.CH, headers=P.H, params={
            "select": "source_file", "limit": "1000", "offset": str(off)}, timeout=120)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for x in rows:
            if x.get("source_file"):
                sfs.add(x["source_file"])
        if len(rows) < 1000:
            break
        off += 1000
    return sorted(sfs)


def classify(o, g):
    if o is None or g is None:
        return "error"
    if o == g:
        return "agree"
    if o <= g or g <= o:
        return "superset"
    return "conflict"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    allsf = all_source_files()
    pool = [s for s in allsf if s not in PILOT_SF]
    random.seed(SEED)
    sample = random.sample(pool, min(N, len(pool)))
    print(f"corpus distinct source_files: {len(allsf)} | pool (excl 15 pilot): {len(pool)} "
          f"| muestra: {len(sample)} (seed {SEED})", flush=True)
    done = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["source_file"]] = r
    a_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    o_client = OpenAI(api_key=OPENAI_API_KEY)
    ti_o = to_o = ti_g = to_g = 0
    results = []
    for i, sf in enumerate(sample, 1):
        if sf in done:
            print(f"[{i}/{len(sample)}] SKIP {sf[:46]}", flush=True)
            results.append(done[sf])
            continue
        print(f"[{i}/{len(sample)}] {sf[:52]}", flush=True)
        try:
            content, cur_tag, cur_mfr, sha, n, trimmed = P.fetch_content(sf)
        except Exception as e:
            print(f"  !! fetch fallo ({str(e)[:80]}); reintentable", flush=True)
            continue
        if not content:
            print("  !! sin contenido", flush=True)
            continue
        opus_res, (oi, oo) = P.call_opus(a_client, sf, content)
        gpt_res, (gi, go) = P.call_gpt(o_client, sf, content)
        ti_o += oi; to_o += oo; ti_g += gi; to_g += go
        oe = opus_res.get("_error") if isinstance(opus_res, dict) else None
        ge = gpt_res.get("_error") if isinstance(gpt_res, dict) else None
        if oe or ge:
            print(f"  !! error modelo (opus={bool(oe)} gpt={bool(ge)}); reintentable", flush=True)
            continue
        os_set, gs_set = P.covered_set(opus_res), P.covered_set(gpt_res)
        cls = classify(os_set, gs_set)
        rec = {
            "source_file": sf, "n_chunks": n, "current_tag": cur_tag,
            "opus_covered": sorted(os_set) if os_set is not None else None,
            "gpt_covered": sorted(gs_set) if gs_set is not None else None,
            "class": cls,
            "source_quality_opus": opus_res.get("source_quality"),
            "n_relations_opus": len(opus_res.get("relations", [])),
        }
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        results.append(rec)
        print(f"  Opus={rec['opus_covered']} GPT={rec['gpt_covered']} [{cls}]", flush=True)

    c = Counter(r["class"] for r in results)
    nd = len(results) or 1
    opus_cost = ti_o / 1e6 * 5 + to_o / 1e6 * 25
    auto = c.get("agree", 0) + c.get("superset", 0)
    rev = c.get("conflict", 0)
    print("\n===== TASA DE ADJUDICACION (muestra aleatoria del corpus) =====", flush=True)
    print(f"docs medidos: {len(results)}", flush=True)
    for k in ("agree", "superset", "conflict", "error"):
        if c.get(k):
            print(f"  {k:9}: {c.get(k,0):2}  ({100*c.get(k,0)/nd:.0f}%)", flush=True)
    print(f"-> AUTO-aceptable (agree+superset): {auto} ({100*auto/nd:.0f}%)", flush=True)
    print(f"-> REVISION humana (conflict): {rev} ({100*rev/nd:.0f}%)  => extrapolado a 1014: ~{round(1014*rev/nd)} docs", flush=True)
    print(f"tokens Opus {ti_o}/{to_o} (~${opus_cost:.2f}); GPT {ti_g}/{to_g}", flush=True)
    print(f"-> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
