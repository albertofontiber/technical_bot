#!/usr/bin/env python3
"""Reclassify the exact S126 upstream/rest residuals from frozen local evidence."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.catalog_resolver import resolve_query

PREREG = ROOT / "evals" / "s126_upstream_residual_audit_prereg_v1.yaml"
OUTPUT = ROOT / "evals" / "s126_upstream_residual_audit_v1.json"

EVIDENCE_IDS = {
    "cat017#2:licencia CLIP por lazo": {
        "5bb83899-9d94-4fdd-8d42-24a670a036c5": ("licencia", "cada circuito de lazo", "clip"),
    },
    "hp010#1:Nivel 3": {
        "155a90fe-8c3f-484e-a617-7637fe29b547": ("nivel 3", "desbloquear", "memoria"),
    },
    "cat008#3:1/2/3/4 lazo; 6-7 entrada A": {
        "9cfb5d22-1082-4903-896b-efe36d5f4567": ("lazo in", "lazo out", "entrada a"),
        "33f0ef2f-8e6d-4720-b28b-0a5b7612cd6c": ("t1 salida", "t3 entrada"),
    },
    "cat013#1:CLIP": {
        "cfcdc8f7-bdaf-412f-a85e-0ffb76878d99": ("clip",),
        "11d96526-d627-4305-8cae-e6852af1b20b": ("sdx-751",),
    },
    "cat013#0:bucle cerrado": {
        "b6602d5a-dbb5-4e2e-8814-1ac3ce066896": ("bucle", "cerrad"),
    },
    "hp011#2:05 a 295 seg": {
        "2d45a70a-5202-442e-af84-c3a176c2178d": ("05", "295"),
        "2ed6b240-f5c3-4dcf-a426-9ca8376e6363": ("05", "295", "t.a"),
    },
    "hp011#3:enclavadas": {
        "c8924d59-a9ce-4379-a3b7-57058ff86a82": ("todas las aver", "enclavadas", "rearme manual"),
    },
}

RECLASSIFICATIONS = {
    "cat017#2:licencia CLIP por lazo": (
        "retrieval-miss",
        "Decisive quantified licence evidence exists in the corpus but is absent from the frozen served context.",
    ),
    "hp010#1:Nivel 3": (
        "retrieval-miss",
        "Decisive access-prerequisite evidence exists in the corpus but is absent from the frozen served context.",
    ),
    "cat008#3:1/2/3/4 lazo; 6-7 entrada A": (
        "source-contract-hold",
        "The frozen context contains conflicting terminal direction assignments; this is not safe bot-improvement credit.",
    ),
    "cat013#1:CLIP": (
        "retrieval-miss",
        "CLIP and SDX-751 evidence exists in MIDT190; the accepted S97 secondary binding is now ported, but the frozen served context predates it and lacks that evidence.",
    ),
    "cat013#0:bucle cerrado": (
        "retrieval-miss",
        "Exact CAD-150 closed-loop evidence exists in the corpus but is absent from the frozen served context.",
    ),
    "hp011#2:05 a 295 seg": (
        "synthesis-miss",
        "The frozen context already serves the structural 05-295 timing row under RP1r-Supra; the answer omitted the range.",
    ),
    "hp011#3:enclavadas": (
        "synthesis-miss",
        "The decisive latched-fault rule is already in the frozen served context and current identity policy resolves RP1r to RP1r-Supra.",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_prereg() -> dict[str, Any]:
    return yaml.safe_load(PREREG.read_text(encoding="utf-8"))


def verified_path(receipt: dict[str, Any], label: str) -> Path:
    path = ROOT / receipt["path"]
    if not path.is_file() or sha256(path) != receipt["sha256"]:
        raise ValueError(f"frozen {label} mismatch")
    return path


def bridge_claims(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    found: dict[str, dict[str, Any]] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            claim_id = value.get("claim_id")
            if isinstance(claim_id, str):
                found.setdefault(claim_id, value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return found


def frozen_contexts(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["qid"]: row["context"] for row in payload["rows"]}


def snapshot_evidence(path: Path) -> dict[str, dict[str, Any]]:
    wanted = {chunk_id for ids in EVIDENCE_IDS.values() for chunk_id in ids}
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") == "chunk" and row.get("id") in wanted:
                rows[row["id"]] = row
    missing = sorted(wanted - rows.keys())
    if missing:
        raise ValueError(f"decisive snapshot rows missing: {missing}")
    for fact_key, expected_rows in EVIDENCE_IDS.items():
        for chunk_id, terms in expected_rows.items():
            content = str(rows[chunk_id].get("content") or "").casefold()
            if not all(term.casefold() in content for term in terms):
                raise ValueError(f"decisive terms missing for {fact_key} in {chunk_id}")
    return rows


def doc_binding_has(source_file: str, product_id: str) -> bool:
    for line in (ROOT / "data" / "catalog" / "doc_map.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_file") != source_file:
            continue
        return any(entry.get("id") == product_id for entry in row.get("entries") or [])
    return False


def build_payload() -> dict[str, Any]:
    prereg = load_prereg()
    frozen = prereg["frozen_inputs"]
    bridge_path = verified_path(frozen["atomic_bridge"], "atomic bridge")
    contexts_path = verified_path(frozen["frozen_contexts"], "frozen contexts")
    snapshot_path = verified_path(frozen["corpus_snapshot"], "corpus snapshot")
    verified_path(frozen["reconciled_bridge"], "reconciled bridge")

    indexed_claims = bridge_claims(bridge_path)
    contexts = frozen_contexts(contexts_path)
    evidence = snapshot_evidence(snapshot_path)
    prereg_claims = prereg["population"]["claims"]
    if len(prereg_claims) != prereg["population"]["exact_count"]:
        raise ValueError("preregistered population count mismatch")

    rp1r = resolve_query(
        "En la Morley RP1r, despues de descargar la extincion el sistema no vuelve a estado normal tras resetear. Que comprobar?"
    )
    rp1r_record = next(record for record in rp1r["records"] if record["token"].casefold() == "rp1r")
    rp1r_contract_ok = (
        rp1r_record.get("politica") == "prefer:notifier:rp1r-supra"
        and rp1r_record.get("ids") == ["notifier:rp1r-supra"]
        and "RP1r-Supra" in rp1r["add_models"]
    )
    if not rp1r_contract_ok:
        raise ValueError("RP1r governed identity no longer resolves to RP1r-Supra")

    rows = []
    for claim in prereg_claims:
        bridge = indexed_claims.get(claim["claim_id"])
        if not bridge or bridge.get("parent_fact_sha256") != claim["parent_fact_sha256"]:
            raise ValueError(f"claim identity mismatch: {claim['claim_id']}")
        fact_key = claim["fact_key"]
        qid = fact_key.split("#", 1)[0]
        served_ids = {str(row.get("id") or "") for row in contexts[qid]}
        decisive_ids = set(EVIDENCE_IDS[fact_key])
        decisive_served = sorted(decisive_ids & served_ids)
        stage, reason = RECLASSIFICATIONS[fact_key]
        rows.append(
            {
                **claim,
                "reconciled_stage": stage,
                "reason": reason,
                "decisive_evidence": [
                    {
                        "chunk_id": chunk_id,
                        "document_id": evidence[chunk_id].get("document_id"),
                        "source_file": evidence[chunk_id].get("source_file"),
                        "page_number": evidence[chunk_id].get("page_number"),
                        "product_model": evidence[chunk_id].get("product_model"),
                        "content_sha256": hashlib.sha256(
                            str(evidence[chunk_id].get("content") or "").encode("utf-8")
                        ).hexdigest(),
                        "served_in_frozen_context": chunk_id in served_ids,
                    }
                    for chunk_id in sorted(decisive_ids)
                ],
                "decisive_served_ids": decisive_served,
                "bot_improvement_credit": 0,
            }
        )

    row_by_key = {row["fact_key"]: row for row in rows}
    if row_by_key["hp011#3:enclavadas"]["decisive_served_ids"] != [
        "c8924d59-a9ce-4379-a3b7-57058ff86a82"
    ]:
        raise ValueError("hp011 latched-fault synthesis boundary not reproduced")
    if row_by_key["hp011#2:05 a 295 seg"]["decisive_served_ids"] != [
        "2d45a70a-5202-442e-af84-c3a176c2178d"
    ]:
        raise ValueError("hp011 timing-range synthesis boundary not reproduced")
    if any(
        row_by_key[key]["decisive_served_ids"]
        for key in (
            "cat017#2:licencia CLIP por lazo",
            "hp010#1:Nivel 3",
            "cat013#0:bucle cerrado",
            "cat013#1:CLIP",
        )
    ):
        raise ValueError("retrieval boundary no longer matches the frozen context")

    stage_hist = dict(sorted(Counter(row["reconciled_stage"] for row in rows).items()))
    prior_hist = Counter({"OK": 111, "rest": 5, "retrieval-miss": 2,
                          "synthesis-miss": 12, "synthesis-not-measured": 27})
    projected = prior_hist.copy()
    projected.subtract({"rest": 5, "retrieval-miss": 2})
    projected.update(stage_hist)
    projected = +projected

    return {
        "schema_version": "s126_upstream_residual_audit_v1",
        "instrument": "s126_audit_upstream_residuals",
        "status": "LOCAL_ROOT_CAUSE_AUDIT_COMPLETE",
        "population": {
            "exact_count": len(rows),
            "prior_buckets": prereg["population"]["prior_buckets"],
            "reconciled_stage_histogram": stage_hist,
            "rows": rows,
        },
        "identity_and_metadata_findings": {
            "rp1r_governed_resolution": {
                "valid": rp1r_contract_ok,
                "policy": rp1r_record["politica"],
                "resolved_ids": rp1r_record["ids"],
                "allowed_sources_count": len(rp1r["allowed_sources"]),
            },
            "midt190_has_sdx751_secondary_binding": doc_binding_has("MIDT190", "notifier:sdx-751"),
            "midt190_binding_consequence": (
                "accepted_s97_binding_ported_after_frozen_context" if doc_binding_has("MIDT190", "notifier:sdx-751")
                else "governed secondary-document binding gap"
            ),
        },
        "provisional_reconciled_diagnostic": {
            "content_denominator": sum(projected.values()),
            "stage_histogram": dict(sorted(projected.items())),
            "rest_count": projected.get("rest", 0),
            "facts_moved_to_ok_due_to_bot_change": 0,
            "official_atomic_kpi": None,
        },
        "mechanism_routing": {
            "procedure_prerequisite_coverage": [
                "cat017#2:licencia CLIP por lazo",
                "hp010#1:Nivel 3",
            ],
            "governed_identity_or_secondary_binding": [
                "cat013#0:bucle cerrado",
                "cat013#1:CLIP",
            ],
            "synthesis_after_upstream_reconciliation": [
                "hp011#2:05 a 295 seg",
                "hp011#3:enclavadas",
            ],
            "source_contract_review_not_bot_tuning": [
                "cat008#3:1/2/3/4 lazo; 6-7 entrada A"
            ],
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
        },
    }


def main() -> int:
    payload = build_payload()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["provisional_reconciled_diagnostic"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
