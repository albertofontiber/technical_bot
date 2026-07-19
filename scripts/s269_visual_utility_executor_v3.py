#!/usr/bin/env python3
"""Ejecutor v3 del clasificador de utilidad visual (cohorte S269, contrato Luna S191).

Hereda el contrato COMPLETO del ejecutor S191 v2 (``s191_visual_utility_executor_luna.py``):
mismo modelo ``gpt-5.6-luna``, ``reasoning_effort: none``, mismo SYSTEM/prompt, mismo
structured-output y misma validación estricta (``parse_labels``/``is_positive``), mismos
batches de 10. Cambia SOLO lo pineado a v1:

    * cohorte: ``evals/s269_visual_utility_cohort_v3.json`` (80 items, 40/40);
    * recibos: ``evals/s269_visual_utility_labels_v3.json``;
    * banda pre-registrada [28, 44] positivos (prereg v3) — se LEE del prereg y se
      cross-checkea contra la constante congelada aquí: si alguien movió la banda,
      el ejecutor ABORTA (la banda no se mueve tras ver labels);
    * ``max_retries=0`` explícito en el cliente OpenAI (no-retry, contrato S191);
    * recibos binarios congelados EN EJECUCIÓN (la cohorte v3 se seleccionó sin
      fetch): sha256 del binario + bytes por item, en el recibo.

Modos:
    (default)                     preflight: lista items, valida cohorte+banda y
                                  estima coste con precios Luna $1/$6 por Mtok
                                  (por-item medido en S191 v2). 0 llamadas, 0 red.
    --execute --env-file <ruta>   ejecución PAGADA (requiere OPENAI_API_KEY en el
                                  env-file). Emite band_pass PRELIMINAR en el
                                  recibo — el gate v3 completo exige además el
                                  spot-check manual (prereg v3); band_pass NO es GO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.s191_visual_utility_executor import (
        BATCH_SIZE,
        SYSTEM,
        _thumbnail,
        is_positive,
        parse_labels,
    )
    from scripts.s191_visual_utility_executor_luna import (
        INPUT_USD_PER_MILLION,
        MODEL,
        OUTPUT_USD_PER_MILLION,
        _input_content,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from s191_visual_utility_executor import (
        BATCH_SIZE,
        SYSTEM,
        _thumbnail,
        is_positive,
        parse_labels,
    )
    from s191_visual_utility_executor_luna import (
        INPUT_USD_PER_MILLION,
        MODEL,
        OUTPUT_USD_PER_MILLION,
        _input_content,
    )

assert SYSTEM  # contrato heredado: el prompt vive en el ejecutor S191, no aquí

ROOT = Path(__file__).resolve().parent.parent
COHORT_PATH = ROOT / "evals" / "s269_visual_utility_cohort_v3.json"
PREREG_PATH = ROOT / "evals" / "s269_visual_utility_cohort_v3_prereg.yaml"
S191_RECEIPTS_PATH = ROOT / "evals" / "s191_visual_utility_luna_receipts_v2.json"
LABELS_PATH = ROOT / "evals" / "s269_visual_utility_labels_v3.json"
PARTIAL_PATH = ROOT / "evals" / "s269_visual_utility_labels_v3.partial.jsonl"

COHORT_ITEMS = 80
# Banda CONGELADA del prereg v3 (35-55% de 80). No se mueve tras ver labels.
FROZEN_POSITIVE_BAND = (28, 44)
BUDGET_MAX_USD = 2.0
# Fallback medido (S191 v2: 15.390 in / 4.150 out por 60 items) si faltara el
# fichero de recibos S191 para la estimación por-item.
FALLBACK_PER_ITEM_TOKENS = (256.5, 69.2)


def load_cohort(cohort_path: Path = COHORT_PATH) -> dict[str, Any]:
    """Carga la cohorte v3 y verifica su contrato + integridad (sha canónico)."""
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    rows = cohort["rows"]
    if len(rows) != COHORT_ITEMS or cohort["status"] != "FROZEN_BEFORE_LABELING":
        raise RuntimeError("unexpected cohort contract")
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recomputed != cohort["selection"]["cohort_sha256"]:
        raise RuntimeError("cohort_sha256 mismatch: la cohorte fue alterada")
    return cohort


def preregistered_band(prereg_path: Path = PREREG_PATH) -> tuple[int, int]:
    """Lee la banda del prereg y la cross-checkea contra la constante congelada.

    Anti-tamper de doble anclaje: si el YAML fue editado tras el freeze (o esta
    constante se tocara), banda-fichero != banda-código → ABORT. Así el veredicto
    band_pass nunca puede calcularse contra una banda movida.
    """
    text = prereg_path.read_text(encoding="utf-8")
    match = re.search(
        r"^\s*preregistered_positive_range:\s*\[(\d+),\s*(\d+)\]", text, re.MULTILINE
    )
    if not match:
        raise RuntimeError("prereg v3 sin preregistered_positive_range parseable")
    band = (int(match.group(1)), int(match.group(2)))
    if band != FROZEN_POSITIVE_BAND:
        raise RuntimeError(
            f"banda del prereg {band} != banda congelada {FROZEN_POSITIVE_BAND} — "
            "la banda no se mueve tras el freeze (anti-overfit S191/S269)"
        )
    return band


def estimate_cost_usd(
    items: int = COHORT_ITEMS, s191_receipts_path: Path = S191_RECEIPTS_PATH
) -> dict[str, Any]:
    """Estimación con precios Luna ($1/$6 por Mtok) y por-item MEDIDO en S191 v2."""
    if s191_receipts_path.exists():
        receipts = json.loads(s191_receipts_path.read_text(encoding="utf-8"))
        batches = receipts["batches"]
        labeled = sum(len(batch["labels"]) for batch in batches)
        per_item_input = sum(b["usage"]["input_tokens"] for b in batches) / labeled
        per_item_output = sum(b["usage"]["output_tokens"] for b in batches) / labeled
        basis = "s191_luna_receipts_v2_measured"
    else:
        per_item_input, per_item_output = FALLBACK_PER_ITEM_TOKENS
        basis = "fallback_constants_from_s191_v2"
    estimated_input = per_item_input * items
    estimated_output = per_item_output * items
    cost = (
        estimated_input * INPUT_USD_PER_MILLION
        + estimated_output * OUTPUT_USD_PER_MILLION
    ) / 1_000_000
    return {
        "basis": basis,
        "pricing_usd_per_million_tokens": {
            "input": INPUT_USD_PER_MILLION,
            "output": OUTPUT_USD_PER_MILLION,
        },
        "per_item_tokens": {
            "input": round(per_item_input, 2),
            "output": round(per_item_output, 2),
        },
        "estimated_tokens": {
            "input": round(estimated_input),
            "output": round(estimated_output),
        },
        "estimated_cost_usd": round(cost, 5),
        "budget_max_usd": BUDGET_MAX_USD,
    }


def preflight(
    cohort_path: Path = COHORT_PATH,
    prereg_path: Path = PREREG_PATH,
    s191_receipts_path: Path = S191_RECEIPTS_PATH,
) -> dict[str, Any]:
    """Plan de ejecución SIN red y SIN llamadas: valida, lista y estima."""
    cohort = load_cohort(cohort_path)
    band = preregistered_band(prereg_path)
    rows = cohort["rows"]
    batches = [rows[offset : offset + BATCH_SIZE] for offset in range(0, len(rows), BATCH_SIZE)]
    return {
        "instrument": "s269_visual_utility_executor_v3_preflight",
        "model": MODEL,
        "reasoning_effort": "none",
        "max_retries": 0,
        "cohort_sha256": cohort["selection"]["cohort_sha256"],
        "items": len(rows),
        "per_group": dict(Counter(row["group"] for row in rows)),
        "distinct_manufacturers": len({row["manufacturer"] for row in rows}),
        "batches": len(batches),
        "batch_size": BATCH_SIZE,
        "preregistered_positive_band": list(band),
        "estimate": estimate_cost_usd(len(rows), s191_receipts_path),
        "paid_calls_made": 0,
        "items_preview": [
            {
                "item_id": row["item_id"],
                "group": row["group"],
                "manufacturer": row["manufacturer"],
                "page_number": row["page_number"],
            }
            for row in rows
        ],
    }


def _fetch_binary(http: Any, row: dict[str, Any]) -> bytes:
    """Descarga el binario del asset verificando el recibo de URL de la cohorte.

    La cohorte v3 congeló sha256(storage_url) (=diagram_url_sha256 del bridge,
    verificado tolerancia-0 contra S190); el binario no se descargó al freeze,
    así que su sha se congela AQUÍ, en el recibo de ejecución (prereg v3:
    refreeze_asset_sha256_and_semantic_payload_sha_before_labeling).
    """
    url = row["storage_url"]
    if hashlib.sha256(url.encode("utf-8")).hexdigest() != row["diagram_url_sha256"]:
        raise RuntimeError(f"URL receipt mismatch for {row['item_id']}")
    response = http.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.content


def execute(env_file: Path) -> int:
    import httpx
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(env_file, override=True)
    plan = preflight()
    cohort = load_cohort()
    band = preregistered_band()
    rows = cohort["rows"]
    print(json.dumps({k: v for k, v in plan.items() if k != "items_preview"}, indent=2))

    import os

    openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    receipts: list[dict[str, Any]] = []
    all_labels: list[dict[str, Any]] = []
    PARTIAL_PATH.unlink(missing_ok=True)
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE

    with httpx.Client() as http:
        for batch_index, offset in enumerate(range(0, len(rows), BATCH_SIZE), 1):
            batch = rows[offset : offset + BATCH_SIZE]
            images = [_fetch_binary(http, row) for row in batch]
            binary_receipts = [
                {
                    "item_id": row["item_id"],
                    "asset_sha256": hashlib.sha256(binary).hexdigest(),
                    "asset_bytes": len(binary),
                }
                for row, binary in zip(batch, images, strict=True)
            ]
            expected_ids = [row["item_id"] for row in batch]
            response = openai.responses.create(
                model=MODEL,
                reasoning={"effort": "none"},
                max_output_tokens=1800,
                input=[{"role": "user", "content": _input_content(batch, images)}],
            )
            raw_text = response.output_text
            labels = parse_labels(raw_text, expected_ids)
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            cost = (
                usage["input_tokens"] * INPUT_USD_PER_MILLION
                + usage["output_tokens"] * OUTPUT_USD_PER_MILLION
            ) / 1_000_000
            receipt = {
                "batch": batch_index,
                "response_id": response.id,
                "model": response.model,
                "status": response.status,
                "usage": usage,
                "cost_usd": round(cost, 8),
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "binary_receipts": binary_receipts,
                "labels": labels,
            }
            receipts.append(receipt)
            all_labels.extend(labels)
            with PARTIAL_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            print(
                f"batch {batch_index}/{total_batches}: labels={len(labels)} "
                f"positives={sum(is_positive(label) for label in labels)} cost=${cost:.4f}",
                flush=True,
            )

    total_cost = round(sum(receipt["cost_usd"] for receipt in receipts), 8)
    positives = [label["item_id"] for label in all_labels if is_positive(label)]
    complete = (
        len(all_labels) == len(rows)
        and len({label["item_id"] for label in all_labels}) == len(rows)
    )
    band_pass = complete and band[0] <= len(positives) <= band[1] and total_cost < BUDGET_MAX_USD
    group_by_item = {row["item_id"]: row["group"] for row in rows}
    positives_by_group = dict(
        Counter(group_by_item[item_id] for item_id in positives)
    )
    result = {
        "instrument": "s269_visual_utility_labels_v3",
        # PRELIMINAR a propósito: el gate v3 completo (prereg) exige además el
        # spot-check manual 5+5 con cero portada/marketing servida.
        "status": (
            "BAND_PASS_PRELIMINARY_SPOT_CHECK_PENDING"
            if band_pass
            else "BAND_OUT_OF_RANGE_NO_GO"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "reasoning_effort": "none",
        "cohort": {
            "path": "evals/s269_visual_utility_cohort_v3.json",
            "cohort_sha256": cohort["selection"]["cohort_sha256"],
            "items": len(rows),
        },
        "prereg": {
            "path": "evals/s269_visual_utility_cohort_v3_prereg.yaml",
            "preregistered_positive_range": list(band),
            "band_source": "parsed_from_prereg_and_matched_frozen_constant",
        },
        "measurement": {
            "valid_labels": len(all_labels),
            "unique_items": len({label["item_id"] for label in all_labels}),
            "positives": len(positives),
            "positive_item_ids": positives,
            "positives_by_group": positives_by_group,
            "by_utility": dict(
                Counter(label["technical_utility"] for label in all_labels)
            ),
            "by_role": dict(Counter(label["visual_role"] for label in all_labels)),
            "band_pass": band_pass,
        },
        "labels": all_labels,
        "batches": receipts,
        "cost": {"luna_usd": total_cost, "calls": len(receipts), "retries": 0},
        "authorization": {
            "frontier_calls": 0,
            "database_writes": 0,
            "production": False,
        },
    }
    LABELS_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    PARTIAL_PATH.unlink(missing_ok=True)
    print(json.dumps(result["measurement"], indent=2, ensure_ascii=False))
    print(f"labels: {LABELS_PATH}")
    return 0 if band_pass else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecución PAGADA (default: preflight sin llamadas).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Ruta al .env con OPENAI_API_KEY (obligatorio con --execute).",
    )
    args = parser.parse_args()
    if args.execute:
        if args.env_file is None:
            print("ABORT: --execute requiere --env-file <ruta>.", file=sys.stderr)
            return 2
        return execute(args.env_file)
    plan = preflight()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print(
        f"preflight OK: {plan['items']} items, {plan['batches']} batches, "
        f"~${plan['estimate']['estimated_cost_usd']} -- 0 llamadas hechas. "
        "Ejecutar con: --execute --env-file <ruta>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
