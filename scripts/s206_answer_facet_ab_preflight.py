#!/usr/bin/env python3
"""Build the zero-provider-call S206 causal A/B manifest."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
RESIDUAL = ROOT / "evals/s163_synthesis_residual_audit_v1.json"
S141 = ROOT / "evals/s141_source_bound_technical_obligations_v1.json"
SOURCE_COHORT = ROOT / "evals/s173_single_source_omission_cohort_v1.json"
PREREG = ROOT / "evals/s206_answer_facet_ledger_prereg_v1.yaml"
OUT = ROOT / "evals/s206_answer_facet_ab_preflight_v1.json"

TARGETS = ("cat018", "hp002", "hp011", "hp017")
GOLD_GUARDRAILS = ("cat019", "hp005")
FAULT_CANARY = "s147_src_05"
CALL_ORDER = (
    ("control", 1),
    ("treatment", 1),
    ("treatment", 2),
    ("control", 2),
)

ENV_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "LLM_MAX_TOKENS": "3500",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_INCLUDE_CONTEXT": "0",
    "ANSWER_OBLIGATION_PLANNER": "guided",
    "POST_RERANK_COVERAGE": "on",
    "STRUCTURAL_NEIGHBOR_COVERAGE": "on",
    "CANONICAL_HYQ_COVERAGE": "on",
    "RERANK_POOL_COVERAGE": "on",
    "STRUCTURAL_CASCADE_COVERAGE": "on",
    "LOGICAL_RECORD_COVERAGE": "on",
}

IMPLEMENTATION_FILES = (
    "config/answer_facets_v1.yaml",
    "config/retrieval_facets_v4.yaml",
    "src/rag/answer_facets.py",
    "src/rag/generator.py",
    "src/rag/query_facets.py",
    "src/rag/answer_planner.py",
    "src/rag/technical_obligations.py",
    "scripts/atomic_scorer.py",
    "scripts/s141_source_bound_technical_obligations.py",
    "scripts/s206_answer_facet_ledger_gate.py",
    "scripts/s206_answer_facet_ab_preflight.py",
    "scripts/s206_run_answer_facet_ab.py",
    "scripts/s206_score_answer_facet_ab.py",
    "scripts/s206_semantic_result_review.py",
    "evals/s206_answer_facet_ledger_design_v1.md",
    "evals/s206_answer_facet_ledger_prereg_v1.yaml",
    "evals/s206_corrected_duo_adjudication_v1.yaml",
    "evals/s206_semantic_result_review_contract_v1.yaml",
)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _source_canary() -> dict[str, Any]:
    source = json.loads(SOURCE_COHORT.read_text(encoding="utf-8"))
    item = next(row for row in source["items"] if row["item_id"] == FAULT_CANARY)
    original = str(item["question"]).strip()
    question = f"En el {item['product_model']}, {original[0].lower()}{original[1:]}"
    chunk = {
        "id": item["chunk_id"],
        "content": item["excerpt"],
        "context": "",
        "product_model": item["product_model"],
        "manufacturer": item["manufacturer"],
        "source_file": item["source_file"],
        "page_number": item["page_number"],
        "section_title": item["section_title"],
        "content_type": "table",
        "document_id": item["document_id"],
        "similarity": 1.0,
        "_channel": "S206_FROZEN_NON_TARGET_CANARY",
    }
    facts = [
        {
            "key": "s147_src_05#columns",
            "texto": "La tabla muestra Fecha/Hora, Evento, Panel, Zona, Dispositivo y Detalles",
            "valor": "Fecha Hora Evento Panel Zona Dispositivo Detalles",
        },
        {
            "key": "s147_src_05#device",
            "texto": "La fila de dispositivo identifica 01:01:003 Detector 2",
            "valor": "01:01:003 Detector 2",
        },
        {
            "key": "s147_src_05#panel_marker",
            "texto": "El marcador de panel cambia de forma intermitente durante la avería",
            "valor": "marcador panel intermitente averia",
        },
        {
            "key": "s147_src_05#fault_filter",
            "texto": "El filtro de fallos muestra la relación de elementos en avería",
            "valor": "filtro fallos elementos averia",
        },
    ]
    return {
        "qid": FAULT_CANARY,
        "role": "protected_fault_canary",
        "question": question,
        "question_transform": "prefix_en_el_product_model_lowercase_original_initial",
        "original_question_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "context": [chunk],
        "facts": facts,
        "source_excerpt_sha256": item["excerpt_sha256"],
    }


def build_cohort() -> list[dict[str, Any]]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen = {str(row["qid"]): row for row in freeze["rows"]}
    rows: list[dict[str, Any]] = []
    for qid in (*TARGETS, *GOLD_GUARDRAILS):
        source = frozen[qid]
        facts = []
        if qid in GOLD_GUARDRAILS:
            facts = [
                deepcopy(fact)
                for fact in source["facts"]
                if fact.get("baseline_class") == "OK"
            ]
        rows.append(
            {
                "qid": qid,
                "role": "target" if qid in TARGETS else "protected_gold_guardrail",
                "question": source["question"],
                "context": source["context"],
                "facts": facts,
                "serving_context_sha256": source["serving_context_sha256"],
            }
        )
    rows.append(_source_canary())
    return rows


class _CaptureMessages:
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self.sink = sink

    def create(self, **kwargs):
        self.sink.append(deepcopy(kwargs))
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="PREFLIGHT_CAPTURE_ONLY [F1]")],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
        )


def capture_envelope(generator_module, row: dict[str, Any], arm: str) -> dict[str, Any]:
    os.environ["ANSWER_FACET_LEDGER"] = "on" if arm == "treatment" else "off"
    captured: list[dict[str, Any]] = []
    original = generator_module.anthropic.Anthropic
    generator_module.anthropic.Anthropic = lambda **_: SimpleNamespace(
        messages=_CaptureMessages(captured)
    )
    try:
        generator_module.generate_answer(row["question"], deepcopy(row["context"]))
    finally:
        generator_module.anthropic.Anthropic = original
    if len(captured) != 1:
        raise RuntimeError(f"expected one captured envelope for {row['qid']} {arm}")
    envelope = captured[0]
    return {
        "sha256": stable_sha(envelope),
        "model": envelope["model"],
        "max_tokens": envelope["max_tokens"],
        "temperature": envelope["temperature"],
        "system_sha256": hashlib.sha256(envelope["system"].encode("utf-8")).hexdigest(),
        "user_message_sha256": hashlib.sha256(
            envelope["messages"][0]["content"].encode("utf-8")
        ).hexdigest(),
        "serialized_bytes": len(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ),
    }


def main() -> int:
    os.environ.update(ENV_FLAGS)
    os.environ["ANSWER_FACET_LEDGER"] = "off"
    from src.rag import generator
    from src.rag.answer_facets import render_answer_facet_ledger

    cohort = build_cohort()
    manifest = []
    for row in cohort:
        envelopes = {
            arm: capture_envelope(generator, row, arm)
            for arm in ("control", "treatment")
        }
        os.environ["ANSWER_FACET_LEDGER"] = "on"
        ledger_active = bool(render_answer_facet_ledger(row["question"]))
        manifest.append(
            {
                **row,
                "context_sha256": stable_sha(row["context"]),
                "context_rows": len(row["context"]),
                "ledger_active": ledger_active,
                "request_envelopes": envelopes,
                "call_order": [f"{arm}_{rep}" for arm, rep in CALL_ORDER],
            }
        )

    generic_ambiguous = "Después de resetear el panel no vuelve a normal; ¿qué compruebo?"
    ho006 = "Tras una alarma en la central NC, ¿cómo se rearma y cómo se anula una zona en avería?"
    os.environ["ANSWER_FACET_LEDGER"] = "on"
    ambiguity = {
        "generic_ambiguous_reset": {
            "question_sha256": hashlib.sha256(generic_ambiguous.encode("utf-8")).hexdigest(),
            "ledger_active": bool(render_answer_facet_ledger(generic_ambiguous)),
        },
        "ho006": {
            "question_sha256": hashlib.sha256(ho006.encode("utf-8")).hexdigest(),
            "ledger_active": bool(render_answer_facet_ledger(ho006)),
        },
    }
    implementation = [
        {"path": path, "sha256": file_sha(ROOT / path)} for path in IMPLEMENTATION_FILES
    ]
    inputs = [
        {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha(path)}
        for path in (FREEZE, RESIDUAL, S141, SOURCE_COHORT, PREREG)
    ]
    checks = {
        "seven_paid_questions": len(manifest) == 7,
        "four_targets": sum(row["role"] == "target" for row in manifest) == 4,
        "all_paid_questions_receive_treatment_ledger": all(
            row["ledger_active"] for row in manifest
        ),
        "control_and_treatment_differ_only_in_system": all(
            row["request_envelopes"]["control"]["user_message_sha256"]
            == row["request_envelopes"]["treatment"]["user_message_sha256"]
            and row["request_envelopes"]["control"]["model"]
            == row["request_envelopes"]["treatment"]["model"]
            and row["request_envelopes"]["control"]["max_tokens"]
            == row["request_envelopes"]["treatment"]["max_tokens"]
            and row["request_envelopes"]["control"]["temperature"]
            == row["request_envelopes"]["treatment"]["temperature"]
            and row["request_envelopes"]["control"]["system_sha256"]
            != row["request_envelopes"]["treatment"]["system_sha256"]
            for row in manifest
        ),
        "ambiguity_negatives_inert": not any(
            item["ledger_active"] for item in ambiguity.values()
        ),
        "exact_28_call_plan": len(manifest) * len(CALL_ORDER) == 28,
        "all_files_hashed": all(row["sha256"] for row in (*implementation, *inputs)),
    }
    body = {
        "schema": "s206_answer_facet_ab_preflight_v1",
        "status": "GO_ZERO_CALL_PREFLIGHT" if all(checks.values()) else "NO_GO",
        "flags": ENV_FLAGS,
        "inputs": inputs,
        "implementation": implementation,
        "call_order": [f"{arm}_{rep}" for arm, rep in CALL_ORDER],
        "paid_calls": 28,
        "rows": manifest,
        "zero_call_ambiguity_negatives": ambiguity,
        "checks": checks,
        "cost": {"model_calls": 0, "network_calls": 0, "usd": 0},
    }
    payload = {**body, "result_sha256": stable_sha(body)}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": checks}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
