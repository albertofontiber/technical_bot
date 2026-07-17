#!/usr/bin/env python3
"""Replay S161's immutable answer over both governed source repairs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.s161_table_preamble_answer_probe import score_answer
from scripts.s172_superscript_answer_cascade import supports_exact_exponent
from src.reingest.extraction_derivation import (
    derive_numeric_superscripts,
    validate_derivation,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
)
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
ANSWER = ROOT / "evals/s161_table_preamble_answer_probe_receipts_v1.json"
PREAMBLE = ROOT / "evals/s160_target_table_preamble_probe_v3.json"
DERIVATION_GATE = ROOT / "evals/s177_governed_derivation_shadow_v1.json"
OUT = ROOT / "evals/s178_combined_source_contract_replay_v1.json"
QID = "cat007"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _source_key(value: str) -> str:
    value = re.sub(r"(?i)\.pdf$", "", value.strip())
    return re.sub(r"[^a-z0-9]+", "", _fold(value))


def _complete_matches(text: str, token: str) -> list[re.Match[str]]:
    return list(re.finditer(rf"(?<!\d){re.escape(token)}(?!\d)", text))


def _source_index(project: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads(
        (project / "logs/reingest_manifest.json").read_text(encoding="utf-8")
    )["files"]
    index: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    for row in rows:
        path = Path(str(row["canonical_path"]))
        key = _source_key(path.name)
        if key in index and index[key]["sha256"] != row["sha256"]:
            ambiguous.add(key)
        index[key] = row
    for key in ambiguous:
        index.pop(key, None)
    return index


def _derive_documents(
    contexts: list[dict[str, Any]], project: Path
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    store = project / "data/extraction/agent_anthropic-sonnet-45"
    index = _source_index(project)
    derived: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for context in contexts:
        key = _source_key(str(context.get("source_file") or ""))
        if not key or key in derived:
            continue
        source = index.get(key)
        if source is None:
            continue
        raw = (store / f"{source['sha256']}.json").read_bytes()
        pdf = Path(source["canonical_path"])
        if not pdf.is_absolute():
            pdf = project / pdf
        envelope = derive_numeric_superscripts(raw, pdf)
        integrity = validate_derivation(envelope, source_raw=raw, pdf_path=pdf)
        if integrity:
            failures.extend(f"{source['sha256']}:{item}" for item in integrity)
            continue
        derived[key] = envelope.manifest
    return derived, failures


def _apply_receipts(
    contexts: list[dict[str, Any]], manifests: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    for fragment, context in enumerate(contexts, 1):
        updated = dict(context)
        original = str(context.get("content") or "")
        content = original
        key = _source_key(str(context.get("source_file") or ""))
        page = int(context.get("page_number") or 0)
        for receipt in manifests.get(key, {}).get("receipts", []):
            if int(receipt["page_number"]) != page:
                continue
            matches = _complete_matches(content, str(receipt["original_token"]))
            anchors = {_fold(str(value)) for value in receipt["matched_anchors"]}
            if len(matches) != 1 or sum(anchor in _fold(content) for anchor in anchors) < 2:
                continue
            match = matches[0]
            content = (
                content[: match.start()]
                + str(receipt["derived_token"])
                + content[match.end() :]
            )
            applied.append(
                {
                    "fragment": fragment,
                    "context_id": context["id"],
                    "source_file": context.get("source_file"),
                    "page_number": page,
                    "original_token": receipt["original_token"],
                    "derived_token": receipt["derived_token"],
                }
            )
        updated["content"] = content
        output.append(updated)
    return output, applied


def build(project: Path) -> dict[str, Any]:
    derivation_gate = json.loads(DERIVATION_GATE.read_text(encoding="utf-8"))
    if derivation_gate.get("status") != "LOCAL_GO":
        raise RuntimeError("S177 derivation gate is not GO")
    freeze = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    row = next(item for item in freeze["rows"] if item["qid"] == QID)
    baseline = [dict(item) for item in row["context"]]
    preamble = json.loads(PREAMBLE.read_text(encoding="utf-8"))
    combined = [
        *baseline,
        {
            "id": preamble["predecessor_id"],
            "content": preamble["preamble"],
            "source_file": baseline[4]["source_file"],
            "page_number": baseline[4]["page_number"],
        },
    ]
    manifests, integrity_failures = _derive_documents(combined, project)
    derived, applied = _apply_receipts(combined, manifests)

    answer_receipt = json.loads(ANSWER.read_text(encoding="utf-8"))
    answer = str(answer_receipt["answer"])
    answer_hash_ok = _sha(answer.encode("utf-8")) == answer_receipt["answer_sha256"]
    scoring = score_answer(
        answer,
        [str(item["id"]) for item in derived],
        [str(item["content"]) for item in derived],
    )
    life_claim = re.search(
        r"Vida\s+\S*til[^\n]{0,100}(?:10\u2075|10\s*\^\s*5)[^\n]{0,100}",
        answer,
        re.IGNORECASE,
    )
    life_citations = (
        sorted({int(value) for value in re.findall(r"\[F(\d+)\]", life_claim.group(0))})
        if life_claim
        else []
    )
    life_support = sum(
        supports_exact_exponent(derived[index - 1]["content"])
        for index in life_citations
        if 1 <= index <= len(derived)
    )
    changed = [
        index + 1
        for index, (before, after) in enumerate(zip(combined, derived))
        if before["content"] != after["content"]
    ]
    checks = {
        "immutable_answer_hash": answer_hash_ok,
        "protected_prefix_equal": combined[:11] == baseline,
        "exact_preamble_appended_once": (
            len(combined) == 12
            and combined[-1]["id"] == preamble["predecessor_id"]
            and _sha(combined[-1]["content"].encode("utf-8"))
            == preamble["preamble_sha256"]
        ),
        "source_contract_claims_five_of_five": scoring["recovered_covered"] == 5,
        "protected_claims_four_of_four": scoring["protected_covered"] == 4,
        "relay_life_exact_citations": life_citations == [1, 4],
        "relay_life_two_exact_supports": life_support == 2,
        "invalid_citations_zero": not scoring["invalid_citations"],
        "only_two_receipted_contexts_changed": changed == [1, 4] and len(applied) == 2,
        "derivation_integrity_failures_zero": not integrity_failures,
    }
    body = {
        "instrument": "s178_combined_source_contract_replay_v1",
        "status": "LOCAL_COMBINED_GO" if all(checks.values()) else "LOCAL_COMBINED_NO_GO",
        "checks": checks,
        "evidence": {
            "served_rows": len(derived),
            "changed_fragments": changed,
            "applied_receipts": applied,
            "recovered_source_contract_claims": scoring["recovered_covered"],
            "protected_claims": scoring["protected_covered"],
            "relay_life_supporting_citations": life_support,
            "invalid_citations": scoring["invalid_citations"],
            "answer_sha256": answer_receipt["answer_sha256"],
        },
        "decision": {
            "table_preamble_runtime_candidate": "LOCAL_GO" if all(checks.values()) else "NO_GO",
            "numeric_derivation_contract": "LOCAL_GO" if all(checks.values()) else "NO_GO",
            "double_count_fact_credit": 0,
            "candidate_funnel": {
                "denominator": 157,
                "OK": 141,
                "synthesis-miss": 12,
                "retrieval-miss": 4,
                "document-extraction-hold": 0,
            },
            "production_or_deployment": False,
            "next": "persist_one_document_level_derivation_receipt_and_shadow_reindex_only_affected_documents",
        },
        "constraints": {
            "model_calls": 0,
            "network_calls": 0,
            "database_calls": 0,
            "chunks_v2_writes": 0,
            "usd": 0,
        },
    }
    return {**body, "result_sha256": _sha(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(args.project)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], **result["checks"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "LOCAL_COMBINED_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
