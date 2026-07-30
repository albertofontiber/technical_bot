#!/usr/bin/env python3
"""s287_p0_reclassify.py — gate P0 (S5/DEC-096c): re-clasificación de hp018#1 SIN regenerar.

Los dos runs full v3 (0729/0730) clasificaron hp018#1 ('6K8') como rerank-miss con
`support_l1_killed` = los chunks que el juez semántico ACREDITÓ y el guard L1 mató por
falta de puente de prefijo kilo ('6k8' ∉ content que escribe «RFL (6800Ω)»). Este script
re-adjudica SOLO esos chunks con el guard ARREGLADO (kilo_prefix_bridge, audit_locator
v3.1) contra su content REAL (sonda httpx GET a chunks_v2, credenciales .env, read-only).

Condición Sol-1 (anti valor-coincidencia, DEC-091b): la literalidad de la respuesta
(«RFL de 6.800 Ω (6k8)») NO acredita — pudo venir de los PRIMOS (ZXSe/ZX50/DXc portan los
mismos valores). hp018#1 SOLO deja de ser miss si el puente recupera una fila SERVIDA de
la familia CORRECTA (gold_families=ZXE). El veredicto se emite por-run y global.

$0 en modelos: los votos semánticos YA existen (los killed ⊂ sup del run); aquí solo se
re-corre el predicado léxico determinista. Salida: evals/s287_p0_reclasificacion_v1.json.

Uso:  python scripts/s287_p0_reclassify.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "evals").is_dir() and (ROOT / "scripts").is_dir(), f"cwd no es la raíz: {ROOT}"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import httpx  # noqa: E402
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from audit_locator import (  # noqa: E402
    SCORE_FLOOR,
    _representation_context_overlap,
    _unit_quantities,
    collapsed_superscript_bridge,
    decimal_notation_bridge,
    fact_match_score,
    kilo_prefix_bridge,
    support_l1_guard_allows,
)
from retrieval_miss_famtie import fam_norm  # noqa: E402

RUNS = (
    "evals/s100_factlevel_full_v3_20260729.yaml",
    "evals/s100_factlevel_full_v3_20260730.yaml",
)
QID = "hp018"
FACT_PREFIX = "hp018#1:"
OUT_PATH = ROOT / "evals" / "s287_p0_reclasificacion_v1.json"

SUPABASE_URL = os.environ["SUPABASE_URL"]
_HEADERS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
            "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
CHUNKS_TABLE = os.environ.get("CHUNKS_TABLE", "chunks_v2") or "chunks_v2"


def fetch_chunks(ids: list[str]) -> dict[str, dict]:
    q = ",".join(f'"{cid}"' for cid in ids)
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=_HEADERS,
        params={"select": "id,product_model,source_file,page_number,content",
                "id": f"in.({q})"},
        timeout=30,
    )
    r.raise_for_status()
    return {row["id"]: row for row in r.json()}


def guard_before(valor: str, texto: str, content: str, same_family: bool) -> bool:
    """Reproducción del guard PRE-fix con las primitivas intactas (decimal/superscript,
    sin kilo): es el predicado exacto de support_l1_guard_allows v3.0."""
    score = fact_match_score(valor, texto, content)
    if score is not None and score >= SCORE_FLOOR - 0.15:
        return True
    quantities_complete = _unit_quantities(valor) <= _unit_quantities(content)
    # NOTA declarada: _unit_quantities ya es la versión v3.1 (canonicaliza kilo). Para el
    # veredicto before/after lo que discrimina es el PUENTE (decimal/superscript vs +kilo);
    # en v3.0 required_quantities('6K8') era ∅ (vacuo) → el término no bloqueaba.
    return bool(
        same_family
        and quantities_complete
        and _representation_context_overlap(texto, content)
        and (decimal_notation_bridge(valor, content)
             or collapsed_superscript_bridge(valor, content))
    )


def reclassify_run(run_path: str) -> dict:
    data = yaml.safe_load(Path(run_path).read_text(encoding="utf-8"))
    gold = next(g for g in data["per_gold"] if g.get("qid") == QID)
    fact = next(f for f in gold["facts"] if str(f.get("key", "")).startswith(FACT_PREFIX))
    served_ids = set(gold.get("served_ids") or [])
    topk_ids = set(gold.get("topk_ids") or [])
    gold_families = {str(f_).upper() for f_ in (gold.get("gold_families") or [])}
    killed = list(fact.get("support_l1_killed") or [])
    valor, texto = fact["valor"], fact.get("texto") or ""

    rows = fetch_chunks(killed)
    adjudications = []
    accrediting = []
    for cid in killed:
        row = rows.get(cid)
        if row is None:
            adjudications.append({"id": cid, "error": "chunk no encontrado en DB"})
            continue
        content = row.get("content") or ""
        same_family = fam_norm(row.get("product_model")) in gold_families
        before = guard_before(valor, texto, content, same_family)
        after = support_l1_guard_allows(valor, texto, content, same_family=same_family)
        adj = {
            "id": cid,
            "product_model": row.get("product_model"),
            "source_file": row.get("source_file"),
            "page_number": row.get("page_number"),
            "same_family": same_family,
            "served": cid in served_ids,
            "in_topk": cid in topk_ids,
            "fact_match_score": fact_match_score(valor, texto, content),
            "quantities_value": sorted(_unit_quantities(valor)),
            "quantities_complete": _unit_quantities(valor) <= _unit_quantities(content),
            "bridges": {
                "decimal": decimal_notation_bridge(valor, content),
                "superscript": collapsed_superscript_bridge(valor, content),
                "kilo": kilo_prefix_bridge(valor, content),
            },
            "guard_before_v30": before,
            "guard_after_v31": after,
        }
        adjudications.append(adj)
        # Sol-1: SOLO acredita una fila SERVIDA + SAME-FAMILY que el guard nuevo
        # recupera y el viejo mataba.
        if after and not before and same_family and cid in served_ids:
            accrediting.append(adj)

    reclassified = bool(accrediting)
    return {
        "run": run_path,
        "fact_key": fact["key"],
        "before": {
            "clase": fact.get("clase"),
            "submotivo": fact.get("submotivo"),
            "in_topk": fact.get("in_topk"),
            "n_support_served": fact.get("n_support_served"),
            "best_pool_rank": fact.get("best_pool_rank"),
            "support_l1_killed": killed,
        },
        "after": {
            "adjudications": adjudications,
            "accrediting_rows": [a["id"] for a in accrediting],
            "n_support_served_recovered": len(accrediting),
        },
        "verdict": {
            "reclassified": reclassified,
            "clase_after": "deja-de-ser-miss (soporte servido same-family recuperado; "
                           "OK definitivo lo estampa el re-baseline v3.1)"
                           if reclassified else fact.get("clase"),
        },
    }


def main() -> None:
    runs = [reclassify_run(rp) for rp in RUNS]
    both = all(r["verdict"]["reclassified"] for r in runs)
    result = {
        "instrument": "audit_locator v3.1 (kilo_prefix_bridge, s287 P0)",
        "gate": "S5/DEC-096c — re-clasificación sin regenerar",
        "sol1_condition": "la literalidad de la respuesta NO acredita (DEC-091b, primos con "
                          "el mismo valor); acredita SOLO fila SERVIDA same-family "
                          "recuperada por el puente",
        "runs": runs,
        "global_verdict": {
            "hp018#1_reclassified_both_runs": both,
            "nota": ("hp018#1 deja de ser miss ESTABLE-N2 (misma fila acreditante en ambos "
                     "runs)" if both else
                     "NO reclasifica en ambos runs — hp018#1 sigue contando como miss"),
        },
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"escrito {OUT_PATH}")
    for r in runs:
        v = r["verdict"]
        print(f"  {r['run']}: reclassified={v['reclassified']} "
              f"accrediting={r['after']['accrediting_rows']}")
    print(f"  GLOBAL: hp018#1_reclassified_both_runs={both}")


if __name__ == "__main__":
    main()
