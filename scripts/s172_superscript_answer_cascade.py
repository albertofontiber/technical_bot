"""Replay the frozen cat007 answer on S162's PDF-bound derived evidence."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ROOT / "evals/s113_full_contexts_freeze_v1.json"
ANSWER = ROOT / "evals/s161_table_preamble_answer_probe_receipts_v1.json"
OVERLAY = ROOT / "evals/s162_numeric_superscript_overlay_packet_v2.json"
OUT = ROOT / "evals/s172_superscript_answer_cascade_v2.json"

EXPECTED = {
    CONTEXTS: "22f2026df5e5df65eb20470a56234b92bdec070ae2836304a7b9391006bf488d",
    ANSWER: "e194a37c0035ed584561cc1afd2e9f3456729415dabdacdf07059603bdb2f95e",
    OVERLAY: "10c21ffd466711b933885593c56cadfe35bc01c9c99075784c918a13222036e7",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def source_key(value: str) -> str:
    value = re.sub(r"(?i)\.pdf$", "", value.strip())
    return re.sub(r"[^a-z0-9]+", "", fold(value))


def complete_token_matches(text: str, token: str) -> list[re.Match[str]]:
    return list(re.finditer(rf"(?<!\d){re.escape(token)}(?!\d)", text))


def supports_exact_exponent(text: str) -> bool:
    return bool(
        re.search(
            r"(?:10\s*<sup>\s*5\s*</sup>|10\s*\^\s*5|10⁵)[\s|*]{0,40}operations?",
            text,
            re.IGNORECASE,
        )
    )


def main() -> None:
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"frozen input drift: {path.name}: {actual}")

    freeze = json.loads(CONTEXTS.read_text(encoding="utf-8"))
    context_row = next(row for row in freeze["rows"] if row["qid"] == "cat007")
    contexts = [dict(row) for row in context_row["context"]]
    answer_receipt = json.loads(ANSWER.read_text(encoding="utf-8"))
    answer = answer_receipt["answer"]
    if hashlib.sha256(answer.encode("utf-8")).hexdigest() != answer_receipt["answer_sha256"]:
        raise ValueError("S161 answer hash mismatch")

    life_claim = re.search(
        r"Vida\s+[úu]til[^\n]{0,80}(?:10⁵|10\s*\^\s*5)[^\n]{0,80}",
        answer,
        re.IGNORECASE,
    )
    if life_claim is None:
        raise ValueError("frozen answer does not contain the target life claim")
    citations = sorted({int(value) for value in re.findall(r"\[F(\d+)\]", life_claim.group(0))})
    if citations != [1, 4]:
        raise ValueError(f"unexpected target citations: {citations}")

    packet = json.loads(OVERLAY.read_text(encoding="utf-8"))
    documents = [*packet["target"], *packet["independent"]]
    receipt_by_source_page: dict[tuple[str, int], list[dict]] = {}
    document_meta: dict[tuple[str, int], dict] = {}
    for document in documents:
        for applied in document["applied"]:
            key = (source_key(document["source_file"]), int(applied["page_number"]))
            receipt_by_source_page.setdefault(key, []).append(applied)
            document_meta[key] = {
                "source_file": document["source_file"],
                "extraction_sha256": document["extraction_sha256"],
                "target_document": bool(document["target_document"]),
            }

    derived_contexts: list[dict] = []
    applied_rows: list[dict] = []
    for fragment_number, context in enumerate(contexts, start=1):
        updated = dict(context)
        original = str(context.get("content") or "")
        derived = original
        key = (source_key(str(context.get("source_file") or "")), int(context.get("page_number") or 0))
        for receipt in receipt_by_source_page.get(key, []):
            token = str(receipt["original_token"])
            matches = complete_token_matches(derived, token)
            if len(matches) != 1:
                continue
            anchors = [fold(value) for value in receipt["matched_anchors"]]
            if sum(anchor in fold(derived) for anchor in anchors) < 2:
                continue
            match = matches[0]
            derived = derived[: match.start()] + receipt["derived_token"] + derived[match.end() :]
            applied_rows.append(
                {
                    "fragment_number": fragment_number,
                    "context_id": context["id"],
                    **document_meta[key],
                    "page_number": key[1],
                    "original_token": token,
                    "derived_token": receipt["derived_token"],
                    "matched_anchors": receipt["matched_anchors"],
                    "pdf_sha256_matches_extraction": (
                        receipt["pdf_sha256"] == document_meta[key]["extraction_sha256"]
                    ),
                    "original_content_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                    "derived_content_sha256": hashlib.sha256(derived.encode("utf-8")).hexdigest(),
                }
            )
        updated["content"] = derived
        derived_contexts.append(updated)

    cited_baseline = [contexts[number - 1]["content"] for number in citations]
    cited_derived = [derived_contexts[number - 1]["content"] for number in citations]
    baseline_support = sum(supports_exact_exponent(text) for text in cited_baseline)
    derived_support = sum(supports_exact_exponent(text) for text in cited_derived)
    cited_applications = [row for row in applied_rows if row["fragment_number"] in citations]
    target_sources = sum(row["target_document"] for row in cited_applications)
    independent_sources = sum(not row["target_document"] for row in cited_applications)

    unchanged_rows = sum(
        before["content"] == after["content"]
        for before, after in zip(contexts, derived_contexts)
    )
    changed_rows = len(contexts) - unchanged_rows
    checks = {
        "answer_sha_matches": True,
        "answer_states_10_power_5_operations": True,
        "target_citations_exact": citations == [1, 4],
        "baseline_exact_exponent_support_zero": baseline_support == 0,
        "derived_exact_exponent_support_two": derived_support == 2,
        "two_cited_receipts_applied": len(cited_applications) == 2,
        "target_source_present": target_sources >= 1,
        "independent_source_present": independent_sources >= 1,
        "all_pdf_hashes_bound": all(row["pdf_sha256_matches_extraction"] for row in cited_applications),
        "only_receipted_context_rows_changed": changed_rows == len(applied_rows) == 2,
        "raw_records_unchanged": bool(packet["summary"]["raw_records_unchanged"]),
        "no_failures_in_overlay_packet": not packet["failures"],
    }
    passed = all(checks.values())
    result = {
        "instrument": "s172_superscript_answer_cascade_v2",
        "status": "LOCAL_ANSWER_CASCADE_GO" if passed else "LOCAL_ANSWER_CASCADE_NO_GO",
        "target": {
            "qid": "cat007",
            "fact_key": "cat007#4:10^5",
            "immutable_answer_sha256": answer_receipt["answer_sha256"],
            "claim_excerpt": life_claim.group(0),
            "citations": citations,
        },
        "checks": checks,
        "evidence": {
            "baseline_exact_exponent_supporting_citations": baseline_support,
            "derived_exact_exponent_supporting_citations": derived_support,
            "target_sources": target_sources,
            "independent_sources": independent_sources,
            "context_rows": len(contexts),
            "changed_context_rows": changed_rows,
            "applied": cited_applications,
            "baseline_context_manifest_sha256": canonical_hash(contexts),
            "derived_context_manifest_sha256": canonical_hash(derived_contexts),
        },
        "stage_transition": {
            "from": "document-extraction-hold",
            "to": "OK" if passed else "document-extraction-hold",
            "diagnostic_fact_credit": 1 if passed else 0,
            "production_credit": 0,
        },
        "candidate_funnel": {
            "denominator": 157,
            "OK": 141 if passed else 140,
            "synthesis-miss": 12,
            "retrieval-miss": 4,
            "document-extraction-hold": 0 if passed else 1,
            "ok_rate_percent": round((141 if passed else 140) / 157 * 100, 2),
            "gap_to_95_percent": 9 if passed else 10,
        },
        "limitations": {
            "local_candidate_only": True,
            "chunks_v2_mutated": False,
            "production_or_deployment": False,
            "official_atomic_kpi": None,
            "answer_regenerated": False,
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "usd": 0,
        },
    }
    result["result_sha256"] = canonical_hash(result)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
