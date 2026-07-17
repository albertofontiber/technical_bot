#!/usr/bin/env python3
"""One-query, GET-only S126 relational compatibility-bundle probe."""
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
OUTPUT = ROOT / "evals" / "s126_compatibility_bundle_probe_v2.json"
QUERY_CONFIG = ROOT / "config" / "retrieval_facets_compatibility_candidate_v2.yaml"
EVIDENCE_CONFIG = ROOT / "config" / "evidence_coverage_compatibility_candidate_v2.yaml"
REQUIRED_TARGETS = {
    "loop_topology": "b6602d5a-dbb5-4e2e-8814-1ac3ce066896",
    "protocol_scope": "cfcdc8f7-bdaf-412f-a85e-0ffb76878d99",
    "supported_device_roster": "11d96526-d627-4305-8cae-e6852af1b20b",
}
REQUIRED_FACETS = frozenset(REQUIRED_TARGETS)
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_receipt(row: dict[str, Any]) -> dict[str, Any]:
    content = row.get("content")
    cards = row.get("coverage_cards")
    candidate_id = str(row.get("id") or "")
    exact = isinstance(content, str) and bool(content) and isinstance(cards, list) and bool(cards)
    card_receipts = []
    if exact:
        for card in cards:
            start, end, quote = card.get("start"), card.get("end"), card.get("quote")
            card_exact = (
                card.get("exact_source_span_validated") is True
                and str(card.get("candidate_id") or "") == candidate_id
                and not isinstance(start, bool)
                and not isinstance(end, bool)
                and isinstance(start, int)
                and isinstance(end, int)
                and isinstance(quote, str)
                and 0 <= start < end <= len(content)
                and content[start:end] == quote
            )
            exact = exact and card_exact
            card_receipts.append(
                {
                    "facet": str(card.get("facet") or ""),
                    "start": start,
                    "end": end,
                    "quote_sha256": (
                        hashlib.sha256(quote.encode("utf-8")).hexdigest()
                        if isinstance(quote, str) else None
                    ),
                    "exact": card_exact,
                }
            )
    extraction = str(row.get("extraction_sha256") or "")
    chunk_index = row.get("chunk_index")
    provenance_complete = (
        bool(str(row.get("document_id") or ""))
        and bool(str(row.get("source_file") or ""))
        and bool(_SHA256.fullmatch(extraction))
        and not isinstance(chunk_index, bool)
        and isinstance(chunk_index, int)
        and chunk_index >= 0
        and isinstance(row.get("compatibility_source_group"), dict)
    )
    return {
        "chunk_id": candidate_id,
        "document_id": str(row.get("document_id") or ""),
        "source_file": str(row.get("source_file") or ""),
        "page_number": row.get("page_number"),
        "extraction_sha256": extraction,
        "chunk_index": chunk_index,
        "source_group": row.get("compatibility_source_group"),
        "entity_role": row.get("compatibility_entity_role"),
        "facet": row.get("compatibility_facet"),
        "cards": card_receipts,
        "exact_source_receipts": exact,
        "provenance_complete": provenance_complete,
        "content_sha256": (
            hashlib.sha256(content.encode("utf-8")).hexdigest()
            if isinstance(content, str) else None
        ),
    }


def run_probe(*, collector=None) -> dict[str, Any]:
    from src.rag.compatibility_bundle_coverage import (
        LANE,
        validate_compatibility_bundle,
    )
    from src.rag.post_rerank_coverage import (
        append_validated_coverage,
        is_validated_coverage_chunk,
    )

    benchmark = yaml.safe_load(
        (ROOT / "evals" / "s100_factlevel_full.yaml").read_text(encoding="utf-8")
    )
    query = next(row["question"] for row in benchmark["per_gold"] if row["qid"] == "cat013")
    if collector is None:
        from src.rag.compatibility_bundle_coverage import collect_compatibility_bundle
        from src.rag.doc_scoped_hyq_coverage import fetch_document_scoped_rows
        from src.rag.catalog_resolver import resolve_query

        def collector(value):
            source_groups = resolve_query(value).get("source_groups") or []
            return collect_compatibility_bundle(
                value,
                fetcher=lambda scope, needs: fetch_document_scoped_rows(
                    scope,
                    needs,
                    source_groups=source_groups,
                    focus_query=value,
                    timeout_seconds=30.0,
                    include_receipts=True,
                ),
            )
    selected, trace = collector(query)
    protected_prefix = [
        {
            "id": "s126-protected-prefix-sentinel",
            "content": "immutable established reranker output",
            "similarity": 1.0,
        }
    ]
    served = append_validated_coverage(protected_prefix, selected)
    served_bundle = served[len(protected_prefix):]
    downstream_answer = None
    if len(served_bundle) == 3:
        # The safety renderer is upstream of provider construction. If that
        # invariant regresses, this probe must fail before spending a token.
        import src.rag.generator as generator

        original_anthropic = generator.anthropic.Anthropic

        def forbidden_provider(*_args, **_kwargs):
            raise AssertionError("compatibility refusal attempted a model call")

        generator.anthropic.Anthropic = forbidden_provider
        try:
            downstream_answer = generator.generate_answer(query, served)
        finally:
            generator.anthropic.Anthropic = original_anthropic
    selected_ids = {str(row.get("id") or "") for row in selected}
    receipts = [_exact_receipt(row) for row in selected]
    selected_facets = {str(row.get("compatibility_facet") or "") for row in selected}
    fetch_receipts = trace.get("fetch_receipts") or {}
    fetch_fingerprints_complete = (
        isinstance(fetch_receipts, dict)
        and all(
            bool(_SHA256.fullmatch(str(fetch_receipts.get(key) or "")))
            for key in (
                "hyq_rows_sha256",
                "selected_parent_ids_sha256",
                "hydrated_parents_sha256",
            )
        )
    )
    recovered = {
        "cat013#0:bucle cerrado": (
            REQUIRED_TARGETS["loop_topology"] in selected_ids
        ),
        # CLIP is credited only when the protocol excerpt and the official row
        # naming the queried detector survive together in one validated bundle.
        "cat013#1:CLIP": (
            REQUIRED_TARGETS["protocol_scope"] in selected_ids
            and REQUIRED_TARGETS["supported_device_roster"] in selected_ids
        ),
    }
    checks = {
        "canonical_scope_bounded": 0 < int(trace.get("scope_rows") or 0) <= 32,
        "exact_three_facet_bundle": (
            len(selected) == 3 and selected_facets == REQUIRED_FACETS
        ),
        "no_hyq_prose_served": trace.get("served_hyq_prose") is False,
        "all_receipts_exact_and_provenanced": bool(receipts) and all(
            row["exact_source_receipts"] and row["provenance_complete"]
            for row in receipts
        ),
        "relational_bundle_revalidated": validate_compatibility_bundle(selected),
        "corpus_and_hyq_fingerprinted": fetch_fingerprints_complete,
        "both_decisive_claims_recovered": all(recovered.values()),
        "unsupported_interoperability_not_asserted": bool(selected) and all(
            row.get("direct_interoperability_supported") is False for row in selected
        ),
        "serving_appends_exactly_three": (
            len(served_bundle) == 3
            and all(row.get("retrieval_lane") == LANE for row in served_bundle)
            and all(is_validated_coverage_chunk(row) for row in served_bundle)
        ),
        "protected_prefix_byte_equal": served[: len(protected_prefix)] == protected_prefix,
        "downstream_source_bound_refusal_without_model": (
            isinstance(downstream_answer, dict)
            and downstream_answer.get("answer_policy")
            == "source_bound_cross_manufacturer_refusal_v1"
            and downstream_answer.get("input_tokens") is None
            and "No puedo confirmar la compatibilidad directa"
            in str(downstream_answer.get("answer") or "")
        ),
    }
    return {
        "instrument": "s126_compatibility_bundle_probe_v2",
        "status": (
            "GO_READ_ONLY_RELATIONAL_BUNDLE"
            if all(checks.values()) else "NO_GO_READ_ONLY_RELATIONAL_BUNDLE"
        ),
        "selection_contract": {
            "query_count": 1,
            "qid_visible_to_selector": False,
            "fact_keys_visible_to_selector": False,
            "target_chunk_ids_visible_to_selector": False,
            "canonical_document_scope": True,
            "entity_stratified_navigation": True,
            "required_facets": sorted(REQUIRED_FACETS),
            "exact_appends": 3,
            "partial_bundle_policy": "serve_none",
        },
        "config_receipts": {
            "query_config_sha256": _sha(QUERY_CONFIG),
            "evidence_config_sha256": _sha(EVIDENCE_CONFIG),
        },
        "implementation_receipts": {
            "catalog_resolver_sha256": _sha(ROOT / "src" / "rag" / "catalog_resolver.py"),
            "doc_scoped_hyq_coverage_sha256": _sha(
                ROOT / "src" / "rag" / "doc_scoped_hyq_coverage.py"
            ),
            "compatibility_bundle_coverage_sha256": _sha(
                ROOT / "src" / "rag" / "compatibility_bundle_coverage.py"
            ),
            "post_rerank_coverage_sha256": _sha(
                ROOT / "src" / "rag" / "post_rerank_coverage.py"
            ),
            "generator_sha256": _sha(ROOT / "src" / "rag" / "generator.py"),
            "catalog_doc_map_sha256": _sha(ROOT / "data" / "catalog" / "doc_map.jsonl"),
        },
        "checks": checks,
        "recovered_claims": recovered,
        "trace": trace,
        "selected_receipts": receipts,
        "serving_receipt": {
            "protected_prefix_ids": [row["id"] for row in protected_prefix],
            "served_bundle_ids": [str(row.get("id") or "") for row in served_bundle],
            "answer_policy": (
                downstream_answer.get("answer_policy")
                if isinstance(downstream_answer, dict) else None
            ),
        },
        "cost": {
            "model_calls": 0,
            "http_get_requests": int(trace.get("http_requests") or 0),
            "database_writes": 0,
        },
        "credit": {
            "retrieval_stage_recoveries": sum(recovered.values()),
            "facts_moved_to_ok": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
        raise RuntimeError("read-only Supabase credentials unavailable")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    payload = run_probe()
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": payload["status"],
        "checks": payload["checks"],
        "cost": payload["cost"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"].startswith("GO_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
