#!/usr/bin/env python3
"""t1_gates.py — gates G1-G2 de T1 (plan s94b): reproducción + no-regresión.

Los surrogates de T1 ya están en DB (batch enunciados-v1:T1:p1, parent_id set). El flag
ENUNCIADOS_MULTIVECTOR controla si el RPC los incluye + el swap los sustituye por su padre.

- CONTROL (flag off): surrogates excluidos = estado pre-inserción → famtie debe = baseline
  s92 (12). Si difiere → el invariante de no-servicio LEAKea (los surrogates se sirven).
- TREATMENT (flag on): swap surrogate→padre → famtie debe BAJAR reproduciendo los flips.

G1 (duro, reproducción): >=4 de los 6 flips de DEC-086 reproducen → famtie <=8. Los 6:
  hp006 'Fallo de Tierra', hp012 '99 + 99', hp012 '2 lazos / 396', hp013 'PWR-R',
  hp014 '35', hp018 '1 A'.
G2 (no-regresión): ninguna nueva-miss fuera de ±2 vs el control.

Uso: python scripts/t1_gates.py
Salida: evals/t1_gates.json + YAMLs de cada pin.
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml

from retrieval_miss_famtie import rederive

POOL_K = 50
BASE = ROOT / "evals" / "s85_retrieval_miss_DEF.yaml"
FLIPS_DEC086 = {("hp006", "Fallo de Tierra"), ("hp012", "99 + 99"),
                ("hp012", "2 lazos / 396"), ("hp013", "PWR-R"),
                ("hp014", "35"), ("hp018", "1 A")}


def regen_and_famtie(tag: str, multivector: str) -> dict:
    os.environ["IDENTITY_RESOLVE"] = "on"
    os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
    os.environ["ENUNCIADOS_MULTIVECTOR"] = multivector
    # invalidar módulos que capturan el flag al import
    for m in ("src.rag.retriever", "src.rag.catalog_resolver"):
        sys.modules.pop(m, None)
    from src.rag import catalog_resolver
    from src.rag.retriever import retrieve_chunks
    stamp = catalog_resolver.catalog_commit()
    d = yaml.safe_load(open(BASE, encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}
    for res in d["reps"][0]["results"]:
        pool = retrieve_chunks(golds[res["qid"]]["question"], top_k=POOL_K)
        res["pool_pin"] = [{"id": c.get("id"), "pm": c.get("product_model"),
                            "src": c.get("source_file")} for c in pool]
        res["top5_ids"] = []
    d["t1_manifest"] = {"tag": tag, "multivector": multivector, "catalog_commit": stamp}
    out = ROOT / "evals" / f"t1_miss_{tag}.yaml"
    yaml.safe_dump(d, open(out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    fam = rederive(str(out))
    misses = {(m["qid"], m["valor"]) for m in fam["misses"]}
    print(f"[{tag}] flag={multivector} · retrieval-miss = {fam['retrieval_miss_family']}")
    return {"tag": tag, "multivector": multivector,
            "miss": fam["retrieval_miss_family"], "misses": sorted(misses)}


def main() -> int:
    control = regen_and_famtie("control", "off")
    treat = regen_and_famtie("multivector", "on")
    ctrl_m = {tuple(x) for x in control["misses"]}
    treat_m = {tuple(x) for x in treat["misses"]}
    flips = ctrl_m - treat_m                       # miss en control, resuelto en treatment
    flips_dec086 = flips & FLIPS_DEC086
    nuevas = treat_m - ctrl_m                       # nuevas-miss (regresión)
    g1 = len(flips_dec086) >= 4
    g2 = len(nuevas) <= 2
    out = {"control_miss": control["miss"], "multivector_miss": treat["miss"],
           "flips_total": sorted(flips), "flips_dec086": sorted(flips_dec086),
           "nuevas_miss": sorted(nuevas),
           "G1_reproduccion": {"pasa": g1, "criterio": ">=4/6 flips DEC-086",
                               "reproducidos": len(flips_dec086)},
           "G2_no_regresion": {"pasa": g2, "criterio": "nuevas-miss <=2",
                               "nuevas": len(nuevas)}}
    json.dump(out, open(ROOT / "evals" / "t1_gates.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nCONTROL {control['miss']} → MULTIVECTOR {treat['miss']}")
    print(f"flips DEC-086 reproducidos: {len(flips_dec086)}/6 {sorted(flips_dec086)}")
    print(f"flips totales (incl. nuevos hechos): {sorted(flips)}")
    print(f"nuevas-miss (regresión): {sorted(nuevas)}")
    print(f"\nG1 reproducción (>=4/6): {'✅ PASA' if g1 else '❌ FALLA'}")
    print(f"G2 no-regresión (<=2 nuevas): {'✅ PASA' if g2 else '❌ FALLA'}")
    return 0 if (g1 and g2) else 1


if __name__ == "__main__":
    sys.exit(main())
