#!/usr/bin/env python3
"""Freeze exact M2/M2.5 strict cohort membership without authorizing reuse."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from scripts import s117_m2_legacy_reuse_analysis as m2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s117_m26_cohort_freezer_prereg_v1.yaml"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _iter_hashed_paths(value: Any):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from _iter_hashed_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_hashed_paths(child)


def preflight(
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    projected_snapshot: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if prereg_path.resolve() != DEFAULT_PREREG.resolve():
        raise RuntimeError("M2.6 cohort freezer prereg path mismatch")
    prereg = yaml.safe_load(prereg_path.read_text(encoding="utf-8"))
    if (
        prereg.get("instrument") != "s117_m26_cohort_freezer_prereg_v1"
        or prereg.get("status") != "frozen_before_cohort_capture"
    ):
        raise RuntimeError("M2.6 cohort freezer prereg drift")
    for item in _iter_hashed_paths(prereg.get("frozen_inputs", {})):
        path = (ROOT / item["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("M2.6 frozen input escapes workspace") from exc
        if _sha_file(path) != item["sha256"]:
            raise RuntimeError(f"M2.6 frozen input drift: {item['path']}")

    selected = prereg["selected_paths"]
    if source_snapshot.resolve() != (ROOT / selected["source_snapshot"]).resolve():
        raise RuntimeError("M2.6 source snapshot path mismatch")
    if projected_snapshot.resolve() != (
        ROOT / selected["projected_snapshot"]
    ).resolve():
        raise RuntimeError("M2.6 projected snapshot path mismatch")
    m2_state = m2.preflight(ROOT / selected["m2_prereg"], store, sidecar_root)
    return prereg, m2_state


def _strict_pairs(
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    local_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    docs_by_sha: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        docs_by_sha[document.get("source_pdf_sha256")].append(document)
    chunks_by_extraction: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        if chunk.get("parent_id") is None:
            chunks_by_extraction[chunk.get("extraction_sha256")].append(chunk)

    context_manifest = hashlib.sha256()
    embedding_manifest = hashlib.sha256()
    membership: dict[str, str] = {}
    for local in local_rows:
        if local.get("preterminal") is not None:
            continue
        matching_docs = docs_by_sha.get(local["extraction_sha256"], [])
        if (
            len(matching_docs) != 1
            or not m2._SHA256.fullmatch(
                matching_docs[0].get("source_pdf_sha256") or ""
            )
            or matching_docs[0].get("status") != "active"
        ):
            continue
        extraction_candidates = chunks_by_extraction.get(
            local["extraction_sha256"], []
        )
        content_candidates = [
            donor
            for donor in extraction_candidates
            if donor.get("content") == local["content"]
        ]
        structure_candidates = [
            donor
            for donor in content_candidates
            if m2._structure_matches(local, donor)
        ]
        metadata_candidates = [
            donor
            for donor in structure_candidates
            if m2._metadata_matches(local, donor)
        ]
        if len(metadata_candidates) != 1:
            continue
        donor = metadata_candidates[0]
        context = donor.get("context")
        if not isinstance(context, str) or not context.strip():
            continue
        if (
            donor.get("embedding_present") is not True
            or donor.get("embedding_dimensions") != m2.embed.EMBED_DIMENSIONS
        ):
            continue
        local_id = local["id"]
        if local_id in membership:
            raise RuntimeError("duplicate local row in strict membership")
        membership[local_id] = donor["id"]
        context_receipt = {
            "id": local_id,
            "context_sha256": _sha_bytes(context.encode("utf-8")),
            "context_input_sha256": local["context_input_sha256"],
        }
        context_manifest.update(_canonical(context_receipt) + b"\n")
        embedding_receipt = {
            "id": local_id,
            **m2._embedding_receipt(context, local["content"]),
        }
        embedding_manifest.update(_canonical(embedding_receipt) + b"\n")
    return {
        "membership": membership,
        "legacy_context_manifest_sha256": context_manifest.hexdigest(),
        "legacy_embedding_manifest_sha256": embedding_manifest.hexdigest(),
    }


def _membership_rows(membership: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    for local_id, donor_id in sorted(membership.items()):
        core = {"local_row_id": local_id, "donor_chunk_id": donor_id}
        rows.append({**core, "pair_receipt_sha256": _sha_bytes(_canonical(core))})
    return rows


def _membership_manifest(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical(row) + b"\n")
    return digest.hexdigest()


def run_freezer(
    *,
    prereg_path: Path,
    store: Path,
    sidecar_root: Path,
    source_snapshot: Path,
    projected_snapshot: Path,
) -> dict[str, Any]:
    prereg, m2_state = preflight(
        prereg_path,
        store,
        sidecar_root,
        source_snapshot,
        projected_snapshot,
    )
    s117_result_path = ROOT / m2_state["prereg"]["frozen_inputs"][
        "s117_development_result"
    ]["path"]
    local_rows, local_receipt = m2.build_local_population(
        m2_state["record_files"],
        s117_result_path,
        m2_state["prereg"]["frozen_inputs"]["chunker"]["sha256"],
        sidecar_root,
    )
    if local_receipt["rows"] != 31212:
        raise RuntimeError("M2.6 local population drift")

    _, source_documents, source_chunks, source_receipt = m2.read_snapshot(
        source_snapshot
    )
    _, projected_documents, projected_chunks, projected_receipt = m2.read_snapshot(
        projected_snapshot
    )
    if _canonical(source_chunks) != _canonical(projected_chunks):
        raise RuntimeError("M2.6 projected chunks drift from source")

    baseline = _strict_pairs(source_documents, source_chunks, local_rows)
    projected = _strict_pairs(projected_documents, projected_chunks, local_rows)
    baseline_membership = baseline.pop("membership")
    projected_membership = projected.pop("membership")
    baseline_ids = set(baseline_membership)
    projected_ids = set(projected_membership)
    if not baseline_ids < projected_ids:
        raise RuntimeError("M2.6 baseline is not a proper projected subset")
    if any(
        projected_membership[local_id] != donor_id
        for local_id, donor_id in baseline_membership.items()
    ):
        raise RuntimeError("M2.6 preexisting donor membership changed")
    new_membership = {
        local_id: projected_membership[local_id]
        for local_id in sorted(projected_ids - baseline_ids)
    }

    expected = prereg["expected_cohorts"]
    m2_result = json.loads(
        (ROOT / prereg["selected_paths"]["m2_result"]).read_text(encoding="utf-8")
    )
    m25_result = json.loads(
        (ROOT / prereg["selected_paths"]["m25_result"]).read_text(encoding="utf-8")
    )
    expected_legacy = {
        "baseline_context": m2_result["reuse_receipts"][
            "strict_context_manifest_sha256"
        ],
        "baseline_embedding": m2_result["reuse_receipts"][
            "strict_embedding_input_manifest_sha256"
        ],
        "projected_context": m25_result["projection"]["reuse_receipts"][
            "strict_context_manifest_sha256"
        ],
        "projected_embedding": m25_result["projection"]["reuse_receipts"][
            "strict_embedding_input_manifest_sha256"
        ],
    }
    observed_legacy = {
        "baseline_context": baseline["legacy_context_manifest_sha256"],
        "baseline_embedding": baseline["legacy_embedding_manifest_sha256"],
        "projected_context": projected["legacy_context_manifest_sha256"],
        "projected_embedding": projected["legacy_embedding_manifest_sha256"],
    }

    memberships = {
        "baseline_strict": _membership_rows(baseline_membership),
        "projected_strict": _membership_rows(projected_membership),
        "new_m25_strict": _membership_rows(new_membership),
    }
    counts = {name: len(rows) for name, rows in memberships.items()}
    manifests = {
        name: _membership_manifest(rows) for name, rows in memberships.items()
    }
    checks = {
        "local_population_exact": local_receipt["rows"] == 31212,
        "source_projected_chunks_identical": _canonical(source_chunks)
        == _canonical(projected_chunks),
        "legacy_replay_manifests_exact": observed_legacy == expected_legacy,
        "cohort_counts_exact": counts == expected,
        "baseline_proper_subset": baseline_ids < projected_ids,
        "preexisting_donor_pairs_invariant": all(
            projected_membership[local_id] == donor_id
            for local_id, donor_id in baseline_membership.items()
        ),
        "baseline_new_disjoint": baseline_ids.isdisjoint(new_membership),
        "baseline_new_union_projected": baseline_ids | set(new_membership)
        == projected_ids,
        "membership_local_ids_unique": all(
            len(rows) == len({row["local_row_id"] for row in rows})
            for rows in memberships.values()
        ),
        "no_reuse_authorized": True,
    }
    result = {
        "instrument": "s117_m26_legacy_cohort_freeze_v1",
        "status": "GO" if all(checks.values()) else "NO_GO",
        "source_snapshot": source_receipt,
        "projected_snapshot": projected_receipt,
        "local": local_receipt,
        "legacy_replay_manifests": {
            "expected": expected_legacy,
            "observed": observed_legacy,
        },
        "cohorts": {
            name: {
                "count": counts[name],
                "membership_pair_manifest_sha256": manifests[name],
                "rows": rows,
            }
            for name, rows in memberships.items()
        },
        "checks": checks,
        "claim": {
            "membership_only": True,
            "authorized_context_rows": 0,
            "authorized_embedding_rows": 0,
            "M3": "BLOCKED",
        },
        "cost": {
            "database_reads": 0,
            "database_writes": 0,
            "model_calls": 0,
            "vector_payloads": 0,
        },
        "dependencies": {
            "prereg_sha256": _sha_file(prereg_path),
            "runner_sha256": _sha_file(Path(__file__)),
        },
    }
    logical = _canonical(result)
    result["determinism"] = {"logical_payload_sha256": _sha_bytes(logical)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--projected-snapshot", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_freezer(
        prereg_path=args.prereg,
        store=args.store,
        sidecar_root=args.sidecar_root,
        source_snapshot=args.source_snapshot,
        projected_snapshot=args.projected_snapshot,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, allow_nan=False, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "cohorts": {
                    key: {"count": value["count"], "manifest": value["membership_pair_manifest_sha256"]}
                    for key, value in result["cohorts"].items()
                },
                "checks": result["checks"],
                "cost": result["cost"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
