#!/usr/bin/env python3
"""Cohorte v3 del clasificador de utilidad visual (S269) — selección LOCAL.

Selecciona del dump del bridge (``evals/s269_visual_assets_bridge_dump_v1.jsonl``)
una cohorte BALANCEADA de 80 activos:

    * 40 "expected_technical": páginas medias/altas de manuales
      (page_index >= 5 — donde viven esquemas, tablas y procedimientos);
    * 40 "expected_control": page_index 1-2 (portadas / índice / legal
      probables — los controles que a S191 le faltaron).

Mandato S191 (evals/s191_visual_utility_classifier_gate_v2.yaml,
``next_if_resumed``): cohorte INDEPENDIENTE balanceada en controles ANTES de
etiquetar nada. Por eso:

    * se EXCLUYEN los 60 activos de la cohorte S191 v1 por
      (document_id, page_number);
    * el muestreo es determinista (seed fija, score sha256) y estratificado
      por fabricante (round-robin breadth-first, mismo espíritu que
      ``scripts/s191_freeze_visual_utility_cohort.py``);
    * 0 llamadas a modelo, 0 GETs a storage, 0 escrituras a DB: este script
      lee SOLO ficheros locales.

El trigger del gate se pre-registra ALINEADO a la composición en
``evals/s269_visual_utility_cohort_v3_prereg.yaml`` (positivos esperados
35-55% de 80 → banda [28, 44]) — el fallo estructural de S191 fue un rango
[10, 30] desalineado con una cohorte 48/60 técnica.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DUMP = ROOT / "evals" / "s269_visual_assets_bridge_dump_v1.jsonl"
DEFAULT_EXCLUDE = ROOT / "evals" / "s191_visual_utility_cohort_v1.json"
DEFAULT_OUTPUT = ROOT / "evals" / "s269_visual_utility_cohort_v3.json"

SEED = "s269_visual_utility_v3"
PER_GROUP = 40
CONTROL_MAX_PAGE = 2   # page_index 1-2 (1-based): portada / índice / legal
TECHNICAL_MIN_PAGE = 5  # páginas medias/altas; 3-4 = zona buffer excluida


def _stable_score(row: dict[str, Any]) -> str:
    value = f"{SEED}|{row['document_id']}|{row['page_number']}|{row['group']}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def choose_balanced_group(
    candidates: list[dict[str, Any]], need: int = PER_GROUP
) -> list[dict[str, Any]]:
    """Round-robin determinista por fabricante (breadth-first)."""
    by_manufacturer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_manufacturer[row["manufacturer"]].append(row)
    for rows in by_manufacturer.values():
        rows.sort(key=_stable_score)
    manufacturers = sorted(
        by_manufacturer, key=lambda name: (-len(by_manufacturer[name]), name)
    )
    selected: list[dict[str, Any]] = []
    cursor = {name: 0 for name in manufacturers}
    while len(selected) < need:
        progressed = False
        for name in manufacturers:
            if len(selected) >= need:
                break
            index = cursor[name]
            if index < len(by_manufacturer[name]):
                selected.append(by_manufacturer[name][index])
                cursor[name] = index + 1
                progressed = True
        if not progressed:
            raise RuntimeError(
                f"Candidatos insuficientes: se necesitan {need}, hay {len(selected)}"
            )
    return selected


def build_cohort(
    dump_path: Path, exclude_path: Path
) -> dict[str, Any]:
    excluded: set[tuple[str, int]] = set()
    exclude_payload = json.loads(exclude_path.read_text(encoding="utf-8"))
    for row in exclude_payload["rows"]:
        excluded.add((str(row["document_id"]), int(row["page_number"])))
    if len(excluded) != len(exclude_payload["rows"]):
        raise RuntimeError("Cohorte de exclusión con páginas duplicadas")

    control_pool: list[dict[str, Any]] = []
    technical_pool: list[dict[str, Any]] = []
    dump_rows = 0
    for line in dump_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        dump_rows += 1
        page = int(record["page_index"])
        key = (str(record["document_id"]), page)
        if key in excluded:
            continue
        candidate = {
            "document_id": str(record["document_id"]),
            "page_number": page,
            "source_file_sha256": record["bridge"]["source_file_sha256"],
            "diagram_url_sha256": record["asset_sha256"],
            "storage_url": record["storage_url"],
            "manufacturer": record["bridge"]["manufacturer"],
            "source_file": record["bridge"]["source_file"],
        }
        if page <= CONTROL_MAX_PAGE:
            candidate["group"] = "expected_control"
            control_pool.append(candidate)
        elif page >= TECHNICAL_MIN_PAGE:
            candidate["group"] = "expected_technical"
            technical_pool.append(candidate)

    cohort = choose_balanced_group(control_pool) + choose_balanced_group(
        technical_pool
    )
    for index, row in enumerate(cohort, 1):
        row["item_id"] = f"s269_visual_{index:03d}"

    overlap = {
        (row["document_id"], row["page_number"]) for row in cohort
    } & excluded
    if overlap:
        raise RuntimeError(f"Solape con la cohorte S191 v1: {sorted(overlap)[:5]}")

    canonical = json.dumps(cohort, sort_keys=True, separators=(",", ":"))
    return {
        "instrument": "s269_visual_utility_cohort_v3",
        "status": "FROZEN_BEFORE_LABELING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "inputs": {
            "bridge_dump": str(dump_path.relative_to(ROOT)).replace("\\", "/"),
            "bridge_dump_rows": dump_rows,
            "excluded_cohort": str(exclude_path.relative_to(ROOT)).replace("\\", "/"),
            "excluded_pages": len(excluded),
        },
        "selection": {
            "items": len(cohort),
            "per_group": dict(Counter(row["group"] for row in cohort)),
            "group_rules": {
                "expected_control": f"page_index <= {CONTROL_MAX_PAGE}",
                "expected_technical": f"page_index >= {TECHNICAL_MIN_PAGE}",
                "buffer_excluded": f"page_index 3-{TECHNICAL_MIN_PAGE - 1}",
            },
            "pool_sizes": {
                "expected_control": len(control_pool),
                "expected_technical": len(technical_pool),
            },
            "per_manufacturer": dict(
                sorted(Counter(row["manufacturer"] for row in cohort).items())
            ),
            "distinct_manufacturers": len(
                {row["manufacturer"] for row in cohort}
            ),
            "cohort_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        },
        "rows": cohort,
        "authorization": {
            "database_reads": False,
            "storage_gets": 0,
            "database_writes": False,
            "production_changes": False,
            "model_calls": 0,
            "usd": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    parser.add_argument("--exclude", type=Path, default=DEFAULT_EXCLUDE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_cohort(args.dump, args.exclude)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["selection"], indent=2, ensure_ascii=False))
    print(f"cohort: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
