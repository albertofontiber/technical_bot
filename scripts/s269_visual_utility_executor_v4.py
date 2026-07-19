#!/usr/bin/env python3
"""Ejecutor v4: clasificacion FULL-BRIDGE de utilidad visual (S269, prereg v4).

Clasifica las 5.096 paginas del bridge (``evals/s269_visual_assets_bridge_dump_v1.jsonl``)
con el contrato heredado v3/v1 (gpt-5.6-luna, reasoning none, mismo SYSTEM/prompt,
misma validacion estricta, batches de 10, precios $1/$6 por Mtok). Preregistro:
``evals/s269_visual_utility_v4_prereg.yaml`` — el gate ya NO es de banda: es el gate
de SERVICIO del contrato S190 (spot-check humano de 60 predicted-useful frescos,
precision >=0.95, cero cover/marketing).

Contrato de ejecucion:
    * checkpoint POR BATCH resumible: ``evals/s269_visual_utility_labels_v4_full.jsonl``
      ES el checkpoint (una linea por item; re-correr salta lo ya etiquetado);
    * no-retry por batch (``max_retries=0`` en el cliente y 0 reintentos propios):
      un batch fallido se registra en ``...failures.jsonl`` y se CONTINUA con el
      siguiente; un re-run posterior lo reintenta de forma natural (resume);
    * stop-line de presupuesto: aborta si el coste acumulado del run supera
      ``BUDGET_STOP_USD``;
    * recibos: sha256(url) verificado contra el dump ANTES del fetch; sha256 del
      binario estampado por item; usage/coste por batch en ``...receipts.jsonl``.

Modos:
    (default)                     preflight sin gasto: valida dump, cuenta pendientes
                                  (resume-aware) y estima coste (0 llamadas, 0 red).
    --execute --env-file <ruta>   ejecucion PAGADA (OPENAI_API_KEY en el env-file).
    --gate-sample                 tras completar el etiquetado: congela la muestra de
                                  60 del serving-set (seed 269, excluye los 80 de v3)
                                  para el spot-check del orquestador. 0 llamadas.
                                  ``--download-dir <dir>`` descarga los renders (GET).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.s191_visual_utility_executor import (
        BATCH_SIZE,
        SERVABLE_ROLES,
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
        SERVABLE_ROLES,
        is_positive,
        parse_labels,
    )
    from s191_visual_utility_executor_luna import (
        INPUT_USD_PER_MILLION,
        MODEL,
        OUTPUT_USD_PER_MILLION,
        _input_content,
    )


ROOT = Path(__file__).resolve().parent.parent
DUMP_PATH = ROOT / "evals" / "s269_visual_assets_bridge_dump_v1.jsonl"
DUMP_MANIFEST_PATH = ROOT / "evals" / "s269_visual_assets_bridge_dump_v1.manifest.json"
V3_COHORT_PATH = ROOT / "evals" / "s269_visual_utility_cohort_v3.json"
V3_LABELS_PATH = ROOT / "evals" / "s269_visual_utility_labels_v3.json"
LABELS_PATH = ROOT / "evals" / "s269_visual_utility_labels_v4_full.jsonl"
RECEIPTS_PATH = ROOT / "evals" / "s269_visual_utility_labels_v4_full.receipts.jsonl"
FAILURES_PATH = ROOT / "evals" / "s269_visual_utility_labels_v4_full.failures.jsonl"
RUN_SUMMARY_PATH = ROOT / "evals" / "s269_visual_utility_v4_run_summary.json"
GATE_SAMPLE_PATH = ROOT / "evals" / "s269_visual_utility_v4_gate_sample.json"

EXPECTED_ITEMS = 5096
GATE_SAMPLE_N = 60
GATE_SAMPLE_SEED = "269"
BUDGET_STOP_USD = 5.0
# Fallback medido en v3 ($0.05445 / 80 items) si faltara el recibo v3.
FALLBACK_PER_ITEM_USD = 0.000680625


def load_items(dump_path: Path = DUMP_PATH) -> list[dict[str, Any]]:
    """Items del bridge en el orden determinista del dump, con item_id estable."""
    items: list[dict[str, Any]] = []
    for line in dump_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        items.append(
            {
                "item_id": f"s269v4_{len(items) + 1:04d}",
                "document_id": record["document_id"],
                "page_index": record["page_index"],
                "storage_url": record["storage_url"],
                "storage_url_sha256": record["asset_sha256"],  # sha de la URL (dump v1)
                "source_file": record["bridge"]["source_file"],
                "manufacturer": record["bridge"]["manufacturer"],
            }
        )
    if len(items) != EXPECTED_ITEMS:
        raise RuntimeError(f"dump con {len(items)} filas != {EXPECTED_ITEMS}")
    manifest = json.loads(DUMP_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["rows"] != EXPECTED_ITEMS:
        raise RuntimeError("manifest del dump no cuadra con el prereg v4")
    return items


def read_label_lines(labels_path: Path = LABELS_PATH) -> list[dict[str, Any]]:
    """Lee el checkpoint tolerando UNA linea final malformada (crash mid-append).

    Dedupe por item_id conservando la ULTIMA aparicion (un item re-etiquetado
    tras un resume no duplica el universo).
    """
    if not labels_path.exists():
        return []
    lines = [
        line for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    by_id: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                continue  # append truncado por crash: el resume lo re-etiqueta
            raise
        by_id[row["item_id"]] = row
    return list(by_id.values())


def done_item_ids(labels_path: Path = LABELS_PATH) -> set[str]:
    return {row["item_id"] for row in read_label_lines(labels_path)}


def per_item_cost_usd(v3_labels_path: Path = V3_LABELS_PATH) -> tuple[float, str]:
    if v3_labels_path.exists():
        data = json.loads(v3_labels_path.read_text(encoding="utf-8"))
        labeled = data["measurement"]["valid_labels"]
        return data["cost"]["luna_usd"] / labeled, "v3_labels_measured"
    return FALLBACK_PER_ITEM_USD, "fallback_constant_from_v3"


def v3_cohort_pages(cohort_path: Path = V3_COHORT_PATH) -> set[tuple[str, int]]:
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    return {(str(row["document_id"]), int(row["page_number"])) for row in cohort["rows"]}


def preflight() -> dict[str, Any]:
    """Plan sin red y sin llamadas: valida, cuenta pendientes y estima coste."""
    items = load_items()
    done = done_item_ids()
    pending = [item for item in items if item["item_id"] not in done]
    per_item, basis = per_item_cost_usd()
    return {
        "instrument": "s269_visual_utility_executor_v4_preflight",
        "preregistration": "evals/s269_visual_utility_v4_prereg.yaml",
        "model": MODEL,
        "reasoning_effort": "none",
        "max_retries": 0,
        "items_total": len(items),
        "items_done": len(done),
        "items_pending": len(pending),
        "batch_size": BATCH_SIZE,
        "batches_pending": (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE,
        "estimate": {
            "basis": basis,
            "per_item_usd": round(per_item, 8),
            "pending_cost_usd": round(per_item * len(pending), 3),
            "full_bridge_cost_usd": round(per_item * len(items), 3),
            "budget_stop_usd": BUDGET_STOP_USD,
        },
        "gate_sample": {
            "n": GATE_SAMPLE_N,
            "seed": GATE_SAMPLE_SEED,
            "population": "useful AND visual_role in "
            + str(sorted(SERVABLE_ROLES)),
            "excluded_v3_pages": len(v3_cohort_pages()),
        },
        "paid_calls_made": 0,
    }


def _fetch_binary(http: Any, item: dict[str, Any]) -> bytes:
    url = item["storage_url"]
    if hashlib.sha256(url.encode("utf-8")).hexdigest() != item["storage_url_sha256"]:
        raise RuntimeError(f"URL receipt mismatch for {item['item_id']}")
    response = http.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.content


def execute(env_file: Path) -> int:
    import os

    import httpx
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(env_file, override=True)
    plan = preflight()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    items = load_items()
    done = done_item_ids()
    pending = [item for item in items if item["item_id"] not in done]
    if not pending:
        print("nada pendiente: etiquetado completo.")
        return 0

    openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    run_cost = 0.0
    labeled_this_run = 0
    failed_batches = 0
    started_at = datetime.now(timezone.utc).isoformat()
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    with httpx.Client() as http:
        for batch_index, offset in enumerate(range(0, len(pending), BATCH_SIZE), 1):
            if run_cost > BUDGET_STOP_USD:
                print(
                    f"STOP-LINE: coste acumulado ${run_cost:.4f} > "
                    f"${BUDGET_STOP_USD} — abortando (resumible).",
                    file=sys.stderr,
                )
                break
            batch = pending[offset : offset + BATCH_SIZE]
            expected_ids = [item["item_id"] for item in batch]
            try:
                images = [_fetch_binary(http, item) for item in batch]
                binary_shas = [
                    hashlib.sha256(binary).hexdigest() for binary in images
                ]
                response = openai.responses.create(
                    model=MODEL,
                    reasoning={"effort": "none"},
                    max_output_tokens=1800,
                    input=[{"role": "user", "content": _input_content(batch, images)}],
                )
                raw_text = response.output_text
                labels = parse_labels(raw_text, expected_ids)
            except Exception as error:  # no-retry: registrar y CONTINUAR
                failed_batches += 1
                with FAILURES_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "at": datetime.now(timezone.utc).isoformat(),
                                "item_ids": expected_ids,
                                "error_type": type(error).__name__,
                                "error": str(error)[:500],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                print(
                    f"batch {batch_index}/{total_batches}: FAIL "
                    f"({type(error).__name__}) — continuo con el siguiente",
                    flush=True,
                )
                continue

            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            cost = (
                usage["input_tokens"] * INPUT_USD_PER_MILLION
                + usage["output_tokens"] * OUTPUT_USD_PER_MILLION
            ) / 1_000_000
            run_cost += cost
            with LABELS_PATH.open("a", encoding="utf-8") as handle:
                for item, label, binary_sha in zip(
                    batch, labels, binary_shas, strict=True
                ):
                    handle.write(
                        json.dumps(
                            {
                                **label,
                                "document_id": item["document_id"],
                                "page_index": item["page_index"],
                                "source_file": item["source_file"],
                                "manufacturer": item["manufacturer"],
                                "storage_url_sha256": item["storage_url_sha256"],
                                "asset_sha256": binary_sha,
                                "response_id": response.id,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            with RECEIPTS_PATH.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "at": datetime.now(timezone.utc).isoformat(),
                            "response_id": response.id,
                            "model": response.model,
                            "status": response.status,
                            "item_ids": expected_ids,
                            "usage": usage,
                            "cost_usd": round(cost, 8),
                            "raw_text_sha256": hashlib.sha256(
                                raw_text.encode("utf-8")
                            ).hexdigest(),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            labeled_this_run += len(labels)
            if batch_index % 10 == 0 or batch_index == total_batches:
                print(
                    f"batch {batch_index}/{total_batches}: "
                    f"labeled={labeled_this_run} run_cost=${run_cost:.4f}",
                    flush=True,
                )

    all_labels = read_label_lines()
    done_after = {row["item_id"] for row in all_labels}
    summary = {
        "instrument": "s269_visual_utility_v4_run_summary",
        "run_started_at": started_at,
        "run_finished_at": datetime.now(timezone.utc).isoformat(),
        "labeled_this_run": labeled_this_run,
        "run_cost_usd": round(run_cost, 5),
        "failed_batches_this_run": failed_batches,
        "items_done_total": len(done_after),
        "items_pending_total": EXPECTED_ITEMS - len(done_after),
        "by_utility": dict(Counter(l["technical_utility"] for l in all_labels)),
        "by_role": dict(Counter(l["visual_role"] for l in all_labels)),
        "strict_positives_total": sum(is_positive(l) for l in all_labels),
        "serving_set_total": sum(
            1
            for l in all_labels
            if l["technical_utility"] == "useful"
            and l["visual_role"] in SERVABLE_ROLES
        ),
    }
    RUN_SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    complete = summary["items_pending_total"] == 0 and failed_batches == 0
    return 0 if complete else 1


def gate_sample_rows(all_labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Muestra determinista del serving-set (prereg v4): seed 269, sin los 80 de v3."""
    excluded = v3_cohort_pages()
    serving = [
        label
        for label in all_labels
        if label["technical_utility"] == "useful"
        and label["visual_role"] in SERVABLE_ROLES
        and (str(label["document_id"]), int(label["page_index"])) not in excluded
    ]

    def score(label: dict[str, Any]) -> str:
        value = f"{GATE_SAMPLE_SEED}|{label['document_id']}|{label['page_index']}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    return sorted(serving, key=score)[:GATE_SAMPLE_N]


def gate_sample(download_dir: Path | None) -> int:
    all_labels = read_label_lines()
    if len({label["item_id"] for label in all_labels}) != EXPECTED_ITEMS:
        print(
            f"ABORT: etiquetado incompleto ({len(all_labels)}/{EXPECTED_ITEMS}) — "
            "la muestra del gate se congela SOLO con el bridge completo.",
            file=sys.stderr,
        )
        return 2
    sample = gate_sample_rows(all_labels)
    items = {item["item_id"]: item for item in load_items()}
    rows = []
    for index, label in enumerate(sample, 1):
        source = items[label["item_id"]]
        rows.append(
            {
                "sample_id": f"s269v4_gate_{index:02d}",
                "item_id": label["item_id"],
                "document_id": label["document_id"],
                "page_index": label["page_index"],
                "source_file": label["source_file"],
                "manufacturer": label["manufacturer"],
                "storage_url": source["storage_url"],
                "asset_sha256": label["asset_sha256"],
                "prediction": {
                    "technical_utility": label["technical_utility"],
                    "visual_role": label["visual_role"],
                    "confidence": label["confidence"],
                    "reason": label["reason"],
                },
                "orchestrator_verdict": None,  # lo rellena el spot-check humano
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    payload = {
        "instrument": "s269_visual_utility_v4_gate_sample",
        "status": "FROZEN_FOR_HUMAN_SPOT_CHECK",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": "evals/s269_visual_utility_v4_prereg.yaml",
        "seed": GATE_SAMPLE_SEED,
        "n": len(rows),
        "criteria": {
            "precision_gte": 0.95,
            "zero_cover_or_marketing": True,
        },
        "sample_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "rows": rows,
    }
    GATE_SAMPLE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"gate sample: {len(rows)} items -> {GATE_SAMPLE_PATH}")
    if download_dir is not None:
        import httpx

        download_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client() as http:
            for row in rows:
                response = http.get(
                    row["storage_url"], timeout=60, follow_redirects=True
                )
                response.raise_for_status()
                if (
                    hashlib.sha256(response.content).hexdigest()
                    != row["asset_sha256"]
                ):
                    raise RuntimeError(
                        f"binary receipt mismatch for {row['item_id']}"
                    )
                name = (
                    f"{row['sample_id']}_{row['prediction']['visual_role']}.jpg"
                )
                (download_dir / name).write_bytes(response.content)
        print(f"renders: {len(rows)} descargados en {download_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--gate-sample", action="store_true")
    parser.add_argument("--download-dir", type=Path, default=None)
    args = parser.parse_args()
    if args.execute and args.gate_sample:
        print("ABORT: --execute y --gate-sample son modos distintos.", file=sys.stderr)
        return 2
    if args.execute:
        if args.env_file is None:
            print("ABORT: --execute requiere --env-file <ruta>.", file=sys.stderr)
            return 2
        return execute(args.env_file)
    if args.gate_sample:
        return gate_sample(args.download_dir)
    plan = preflight()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print(
        f"preflight OK: {plan['items_pending']} pendientes de "
        f"{plan['items_total']}, ~${plan['estimate']['pending_cost_usd']} -- "
        "0 llamadas hechas. Ejecutar con: --execute --env-file <ruta>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
