#!/usr/bin/env python3
"""Reconcile S125 atomic claims against exact S113 frozen answers."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
ADJUDICATION_PATH = ROOT / "evals" / "s125_m1_answer_replay_adjudication_v1.yaml"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(raw.encode("utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _frozen_file(receipt: dict[str, Any], label: str) -> Path:
    path = (ROOT / receipt["path"]).resolve()
    if not path.is_file() or file_sha256(path) != receipt["sha256"]:
        raise ValueError(f"frozen {label} mismatch")
    return path


def build_replay(adjudication: dict[str, Any], contract: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    contract_receipt = adjudication["frozen_inputs"]["migration_contract"]
    if contract.get("payload_sha256") != contract_receipt.get("payload_sha256"):
        raise ValueError("migration contract payload mismatch")

    claims = contract.get("claims") or []
    claim_by_id = {row.get("migration_id"): row for row in claims}
    if None in claim_by_id or len(claim_by_id) != len(claims):
        raise ValueError("contract claim ids are not unique")
    answer_by_qid = {row.get("qid"): row for row in answers.get("rows") or []}
    qid_receipts = adjudication.get("qid_receipts") or {}
    expected_qids = {row["qid"] for row in claims}
    if set(qid_receipts) != expected_qids:
        raise ValueError("qid adjudication coverage is not exact")

    core_overrides = adjudication.get("core_overrides") or {}
    supplementary = adjudication.get("supplementary_claims") or {}
    if any(claim_id not in claim_by_id for claim_id in [*core_overrides, *supplementary]):
        raise ValueError("adjudication references an unknown claim")
    expected_supplementary = {
        row["migration_id"] for row in claims if row["tipo"] == "supplementary"
    }
    if set(supplementary) != expected_supplementary:
        raise ValueError("supplementary adjudication coverage is not exact")

    rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = claim["migration_id"]
        qid = claim["qid"]
        receipt = qid_receipts[qid]
        answer_row = answer_by_qid.get(qid)
        if answer_row is None or bool(answer_row.get("executed")) != receipt["executed"]:
            raise ValueError(f"answer execution receipt mismatch: {qid}")
        if answer_row.get("answer_sha256") != receipt.get("answer_sha256"):
            raise ValueError(f"answer hash receipt mismatch: {qid}")
        if receipt["executed"]:
            answer = answer_row.get("answer")
            if not isinstance(answer, str) or sha256_bytes(answer.encode("utf-8")) != receipt["answer_sha256"]:
                raise ValueError(f"answer bytes do not match receipt: {qid}")
        elif answer_row.get("answer") is not None:
            raise ValueError(f"unexecuted answer must be null: {qid}")

        if claim["tipo"] == "core":
            decision = core_overrides.get(claim_id)
            if decision is None:
                coverage = receipt.get("core_default")
                rationale = receipt.get("rationale")
            else:
                coverage = decision.get("coverage")
                rationale = decision.get("rationale")
            if coverage not in {"synthesis_covered", "synthesis_not_covered", "synthesis_not_measured"}:
                raise ValueError(f"invalid or absent core coverage: {claim_id}")
            if coverage == "synthesis_not_measured" and receipt["executed"]:
                raise ValueError(f"executed answer cannot be unmeasured: {claim_id}")
            if coverage != "synthesis_not_measured" and not receipt["executed"]:
                raise ValueError(f"unexecuted answer cannot be scored: {claim_id}")
            stage_bucket = {
                "synthesis_covered": "OK",
                "synthesis_not_covered": "synthesis-miss",
                "synthesis_not_measured": "synthesis-not-measured",
            }[coverage]
            content_eligible = True
        else:
            decision = supplementary[claim_id]
            coverage = decision.get("coverage")
            rationale = decision.get("rationale")
            if coverage not in {"synthesis_covered", "synthesis_not_covered", "synthesis_not_measured"}:
                raise ValueError(f"invalid supplementary coverage: {claim_id}")
            if coverage == "synthesis_not_measured" and receipt["executed"]:
                raise ValueError(f"executed supplementary answer cannot be unmeasured: {claim_id}")
            if coverage != "synthesis_not_measured" and not receipt["executed"]:
                raise ValueError(f"unexecuted supplementary answer cannot be scored: {claim_id}")
            stage_bucket = {
                "synthesis_covered": "supplementary-covered",
                "synthesis_not_covered": "supplementary-not-covered",
                "synthesis_not_measured": "supplementary-not-measured",
            }[coverage]
            content_eligible = False
        if not str(rationale or "").strip():
            raise ValueError(f"missing replay rationale: {claim_id}")

        rows.append({
            "migration_id": claim_id,
            "qid": qid,
            "parent_fact_key": claim["parent_fact_key"],
            "tipo": claim["tipo"],
            "content_eligible": content_eligible,
            "retrieval_status": "pass",
            "rerank_status": "pass",
            "synthesis_coverage": coverage,
            "stage_bucket": stage_bucket,
            "rationale": rationale,
            "answer_executed": receipt["executed"],
            "answer_sha256": receipt.get("answer_sha256"),
            "source_context_ids": [binding["context_id"] for binding in claim["source_bindings"]],
        })

    core_rows = [row for row in rows if row["content_eligible"]]
    supplementary_rows = [row for row in rows if not row["content_eligible"]]
    core_hist = dict(sorted(Counter(row["stage_bucket"] for row in core_rows).items()))
    supp_hist = dict(sorted(Counter(row["stage_bucket"] for row in supplementary_rows).items()))
    parent_outcomes: list[dict[str, Any]] = []
    for parent in contract.get("parents") or []:
        child_rows = [row for row in core_rows if row["parent_fact_key"] == parent["parent_fact_key"]]
        if parent["disposition"] == "merge_duplicate":
            replacement_rows = [row for row in core_rows if row["migration_id"] in parent["replaced_by"]]
            rollup = replacement_rows[0]["stage_bucket"] if replacement_rows else "invalid"
        elif not child_rows:
            rollup = "not-content-scored"
        elif any(row["stage_bucket"] == "synthesis-not-measured" for row in child_rows):
            rollup = "synthesis-not-measured"
        elif any(row["stage_bucket"] != "OK" for row in child_rows):
            rollup = "synthesis-miss"
        else:
            rollup = "OK"
        parent_outcomes.append({
            "parent_fact_key": parent["parent_fact_key"],
            "qid": parent["qid"],
            "legacy_stage_bucket": parent["legacy_stage_bucket"],
            "migrated_parent_rollup": rollup,
            "core_child_ids": [row["migration_id"] for row in child_rows],
        })

    result: dict[str, Any] = {
        "schema_version": "s125_m1_known_hold_answer_replay_v1",
        "instrument": "s125_replay_m1_known_hold_answers",
        "status": "LOCAL_FROZEN_REPLAY_COMPLETE_NO_EXTERNAL_CALLS",
        "authority": {
            "adjudication": str(ADJUDICATION_PATH.relative_to(ROOT)).replace("\\", "/"),
            "adjudication_sha256": file_sha256(ADJUDICATION_PATH),
            "migration_contract_sha256": contract_receipt["sha256"],
            "migration_contract_payload_sha256": contract_receipt["payload_sha256"],
            "frozen_answers_sha256": adjudication["frozen_inputs"]["frozen_answers"]["sha256"],
        },
        "summary": {
            "content_claim_count": len(core_rows),
            "supplementary_claim_count": len(supplementary_rows),
            "content_stage_histogram": core_hist,
            "supplementary_stage_histogram": supp_hist,
            "retrieval_pass": sum(row["retrieval_status"] == "pass" for row in core_rows),
            "rerank_pass": sum(row["rerank_status"] == "pass" for row in core_rows),
            "answer_executed_qids": sum(receipt["executed"] for receipt in qid_receipts.values()),
            "answer_unexecuted_qids": sum(not receipt["executed"] for receipt in qid_receipts.values()),
            "model_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
        "parent_outcomes": parent_outcomes,
        "rows": rows,
        "limitations": [
            "The 16 unmeasured core claims require a fresh bounded answer probe before synthesis classification.",
            "This is a migrated-cohort diagnostic and not an official whole-benchmark atomic KPI.",
        ],
    }
    result["payload_sha256"] = canonical_sha256(result)
    return result


def build_from_files() -> dict[str, Any]:
    adjudication = load_yaml(ADJUDICATION_PATH)
    contract_path = _frozen_file(adjudication["frozen_inputs"]["migration_contract"], "contract")
    answers_path = _frozen_file(adjudication["frozen_inputs"]["frozen_answers"], "answers")
    return build_replay(adjudication, load_json(contract_path), load_json(answers_path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "s125_m1_known_hold_answer_replay_v1.json",
    )
    args = parser.parse_args()
    result = build_from_files()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    print(f"payload_sha256={result['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
