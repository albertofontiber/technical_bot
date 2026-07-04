"""s95 Piloto D — gates D-G1/D-G2/D-G3/D-G4 (pre-registro evals/s95_redesign_pilots.md v2).

Brazo: IDENTITY_FETCH=llm (selector deep-lookup) · ENUNCIADOS_MULTIVECTOR=off ·
IDENTITY_RESOLVE=on/add (config congelada de la vara). Control = 12 (post-VACUUM s94c).
Set canónico de flips = scripts/t1_gates.py:FLIPS_DEC086 [D1].
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "off"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
os.environ["IDENTITY_FETCH"] = "llm"

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "off"
os.environ["IDENTITY_FETCH"] = "llm"

import yaml  # noqa: E402

from retrieval_miss_famtie import rederive  # noqa: E402
from t1_gates import FLIPS_DEC086  # noqa: E402  [D1] set canónico

CONTROL_MISS = 12
CONTROL_SET = {("cat013", "CLIP"), ("cat016", "autobusqueda"), ("hp001", "2222"),
               ("hp006", "Fallo de Tierra"), ("hp006", "Tierra"), ("hp006", "ISO-X"),
               ("hp011", "05 a 295 seg"), ("hp012", "99 + 99"), ("hp012", "2 lazos / 396"),
               ("hp013", "PWR-R"), ("hp014", "35"), ("hp018", "1 A")}


def main() -> int:
    from src.rag.deep_lookup import STATS
    from src.rag.retriever import retrieve_chunks

    base = yaml.safe_load(open(ROOT / "evals" / "s85_retrieval_miss_DEF.yaml", encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}

    lat: list[float] = []
    triggered = 0
    for res in base["reps"][0]["results"]:
        q = golds[res["qid"]]["question"]
        docs_before = STATS["docs"]
        t0 = time.time()
        pool = retrieve_chunks(q, top_k=50)
        lat.append(time.time() - t0)
        if STATS["docs"] > docs_before:
            triggered += 1
        res["pool_pin"] = [{"id": c.get("id"), "pm": c.get("product_model"),
                            "src": c.get("source_file")} for c in pool]
        res["top5_ids"] = []
    out = ROOT / "evals" / "s95_d_miss_llm.yaml"
    yaml.safe_dump(base, open(out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

    fam = rederive(str(out))
    d_set = {(m["qid"], m["valor"]) for m in fam["misses"]}
    flips = CONTROL_SET - d_set
    nuevas = d_set - CONTROL_SET
    can = flips & FLIPS_DEC086

    lat_sorted = sorted(lat)
    p50 = lat_sorted[len(lat) // 2]
    print(f"CONTROL {CONTROL_MISS} → D(llm) {fam['retrieval_miss_family']}")
    print(f"flips canónicos: {len(can)}/6 {sorted(can)}")
    print(f"flips totales: {sorted(flips)}")
    print(f"nuevas-miss: {sorted(nuevas)}")
    print(f"D-G1 (≤8 y ≥4/6): {'✅' if fam['retrieval_miss_family'] <= 8 and len(can) >= 4 else '❌'}")
    print(f"D-G2 (jitter ±2): {'✅' if len(nuevas) <= 2 else '❌'}")
    print(f"D-G3: {STATS['llm_calls']} llamadas LLM · {STATS['input_tokens']} in / "
          f"{STATS['output_tokens']} out tokens · errores {STATS['errors']} · "
          f"p50 retrieval {p50:.1f}s (39 queries, {triggered} gatilladas)")
    print(f"D-G4 tasa de gatillado (eval-39): {triggered}/39 = {triggered / 39:.0%}")
    json.dump({"miss": fam["retrieval_miss_family"], "flips_canonicos": sorted(can),
               "flips": sorted(flips), "nuevas": sorted(nuevas), "stats": dict(STATS),
               "p50_s": round(p50, 2), "triggered": triggered},
              open(ROOT / "evals" / "s95_d_gates.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
