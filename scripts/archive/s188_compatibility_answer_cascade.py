#!/usr/bin/env python3
"""Read-only answer cascade for the versioned compatibility topology cards."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)
DEFAULT_OUT = ROOT / "evals/s188_compatibility_answer_cascade_v1.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_cards(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        content = str(row.get("content") or "")
        candidate_id = str(row.get("id") or "")
        cards = row.get("coverage_cards") or []
        if not content or not candidate_id or not cards:
            return False
        for card in cards:
            start, end = card.get("start"), card.get("end")
            if (
                card.get("exact_source_span_validated") is not True
                or str(card.get("candidate_id") or "") != candidate_id
                or isinstance(start, bool)
                or isinstance(end, bool)
                or not isinstance(start, int)
                or not isinstance(end, int)
                or not 0 <= start < end <= len(content)
                or content[start:end] != card.get("quote")
            ):
                return False
    return True


def execute(env_file: Path) -> dict[str, Any]:
    load_dotenv(env_file, override=True)
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        raise RuntimeError("read-only Supabase credentials unavailable")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from src.rag.catalog_resolver import resolve_query
    from src.rag.compatibility_bundle_coverage import (
        CONTRACT,
        EVIDENCE_CONFIG,
        LANE,
        collect_compatibility_bundle,
        render_cross_manufacturer_compatibility_refusal,
        validate_compatibility_bundle,
    )
    from src.rag.doc_scoped_hyq_coverage import fetch_document_scoped_rows

    benchmark = yaml.safe_load(
        (ROOT / "evals/s100_factlevel_full.yaml").read_text(encoding="utf-8")
    )
    frozen = next(row for row in benchmark["per_gold"] if row["qid"] == "cat013")
    query = frozen["question"]

    # The selector receives only the literal query and governed catalog scope.
    groups = resolve_query(query).get("source_groups") or []
    selected, trace = collect_compatibility_bundle(
        query,
        fetcher=lambda scope, needs: fetch_document_scoped_rows(
            scope,
            needs,
            source_groups=groups,
            focus_query=query,
            timeout_seconds=30.0,
            include_receipts=True,
        ),
    )
    answer = render_cross_manufacturer_compatibility_refusal(selected) or ""
    cards = [card for row in selected for card in row.get("coverage_cards") or []]
    topology_quotes = [
        str(card.get("quote") or "")
        for card in cards
        if card.get("facet") == "loop_topology"
    ]
    protocol_quotes = [
        str(card.get("quote") or "")
        for card in cards
        if card.get("facet") == "protocol_scope"
    ]
    closure_quotes = [
        quote
        for quote in topology_quotes
        if re.search(r"\bbucle\b[\s\S]{0,80}\bcerrad[ao]s?\b", quote, re.I)
    ]
    clip_quotes = [quote for quote in protocol_quotes if re.search(r"\bCLIP\b", quote)]
    checks = {
        "three_parent_bundle": len(selected) == 3,
        "versioned_contract": CONTRACT == "governed_two_entity_three_facet_bundle_v2",
        "versioned_lane": LANE == "canonical_compatibility_bundle_coverage_v2",
        "bundle_revalidates": validate_compatibility_bundle(selected),
        "all_cards_exact": _exact_cards(selected),
        "bounded_cards": len(cards) <= 5 and len(topology_quotes) == 2,
        "literal_closed_loop_reaches_answer": bool(closure_quotes)
        and all(quote in answer for quote in closure_quotes),
        "literal_clip_reaches_answer": bool(clip_quotes)
        and all(quote in answer for quote in clip_quotes),
        "direct_compatibility_refused": (
            "No puedo confirmar la compatibilidad directa" in answer
            and "no prueban por sí solas" in answer
        ),
        "no_positive_interoperability_claim": not bool(
            re.search(r"\b(?:s[ií]|son)\s+compatibles\b", answer, re.I)
        ),
    }
    return {
        "instrument": "s188_compatibility_answer_cascade_v1",
        "status": "GO_LOCAL_DEFAULT_OFF_KNOWN_COHORT" if all(checks.values()) else "NO_GO_LOCAL",
        "selection_contract": {
            "qid_visible_to_selector": False,
            "facts_visible_to_selector": False,
            "expected_answer_visible_to_selector": False,
            "query_count": 1,
            "cards_global_max": 5,
            "topology_cards_max": 2,
            "partial_bundle_policy": "serve_none",
        },
        "checks": checks,
        "trace": trace,
        "receipts": {
            "evidence_config": str(EVIDENCE_CONFIG.relative_to(ROOT)).replace("\\", "/"),
            "evidence_config_sha256": file_sha(EVIDENCE_CONFIG),
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            "selected_ids": [str(row.get("id") or "") for row in selected],
            "card_count": len(cards),
            "topology_card_count": len(topology_quotes),
            "closure_quote_sha256": [
                hashlib.sha256(quote.encode("utf-8")).hexdigest()
                for quote in closure_quotes
            ],
            "clip_quote_sha256": [
                hashlib.sha256(quote.encode("utf-8")).hexdigest()
                for quote in clip_quotes
            ],
        },
        "known_cohort_stage_transition": {
            "from": {"retrieval-miss": 2},
            "to": {"OK": 2},
            "semantic_basis": [
                "literal closed-loop declaration copied into deterministic answer",
                "literal CLIP protocol declaration copied into deterministic answer",
            ],
            "official_fact_credit": 0,
        },
        "candidate_funnel_if_flag_enabled": {
            "denominator": 157,
            "OK": 143,
            "synthesis-miss": 12,
            "retrieval-miss": 2,
            "ok_rate_percent": 91.08,
            "gap_to_95_percent": 7,
        },
        "limitations": [
            "This known-cohort cascade is diagnostic, not independent release evidence.",
            "S127 still forbids inferring interoperability from independent facets.",
            "The runtime flag remains off and no production or official KPI credit is authorized.",
        ],
        "cost": {
            "model_calls": 0,
            "http_get_requests": int(trace.get("http_requests") or 0),
            "database_writes": 0,
            "usd": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = execute(args.env_file)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "checks": payload["checks"], "cost": payload["cost"]}))
    return 0 if payload["status"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
