from __future__ import annotations

import hashlib
import subprocess

import pytest

from scripts import s131_build_shadow_binding_manifest as audit


GATE = audit.ROOT / "evals/s131_shadow_binding_manifest_gate_v1.yaml"
EXTRACTION = "a" * 64
DOCUMENT = "00000000-0000-0000-0000-000000000001"

# Commit that sealed the gate together with the executed seed manifests
# ("s131: validate chunks v3 shadow database contract"; the gate records no
# commit id). The pinned hashes are physical blob bytes, so byte-identity is
# asserted against the sealed git blobs, not a CRLF-smudging checkout
# (DEC-147: version, do not relax).
SEED_SEAL_COMMIT = "e60c853faceb18e9ba869c7ed431260b37580da4"


def _sealed_bytes(relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{SEED_SEAL_COMMIT}:{relative}"],
        cwd=audit.ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"sealed blob missing: {relative}"
    return completed.stdout


@pytest.fixture(scope="module")
def real_payloads() -> dict[str, dict]:
    gate = audit.load_yaml(GATE)
    return {
        arm: audit.load_json(
            audit.ROOT / gate["determinism"][arm]["seed1"]["path"]
        )
        for arm in ("baseline", "candidate")
    }


def test_real_frozen_population_is_exact(real_payloads: dict[str, dict]) -> None:
    expected_statuses = {
        "bound_active_legacy_snapshot_only": 597,
        "bound_active_physical_sha_verified": 405,
        "bound_nonactive_legacy_snapshot": 8,
        "unbound_absent_from_snapshot": 50,
        "unbound_snapshot_empty_document": 8,
    }
    expected_partitions = {
        "development": {"extractions_total": 998, "bound_active_extractions": 932},
        "heldout_s130": {"extractions_total": 70, "bound_active_extractions": 70},
    }
    for payload in real_payloads.values():
        assert payload["status"] == "GO"
        assert payload["population"]["extractions"] == 1068
        assert payload["population"]["binding_statuses"] == expected_statuses
        assert payload["population"]["partitions"] == expected_partitions
        assert payload["population"]["distinct_bound_documents"] == 1007
        assert payload["population"]["distinct_active_bound_documents"] == 999
        assert all(payload["checks"].values())


def test_executed_manifests_are_byte_identical_and_gate_pins_exact_arms() -> None:
    """DEC-147: determinism was proven over the seed bytes sealed at
    SEED_SEAL_COMMIT; the assertion targets those blobs so the seal detects
    history tampering instead of failing on checkout normalization."""
    gate = audit.load_yaml(GATE)
    expected = {
        "baseline": "951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1",
        "candidate": "aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746",
    }
    for arm, expected_sha in expected.items():
        seed1 = _sealed_bytes(gate["determinism"][arm]["seed1"]["path"])
        seed2 = _sealed_bytes(gate["determinism"][arm]["seed2"]["path"])
        assert seed1 == seed2
        assert hashlib.sha256(seed1).hexdigest() == expected_sha
        assert hashlib.sha256(seed2).hexdigest() == expected_sha
        assert gate["exact_registry_arms"][arm]["bindings_manifest_sha256"] == expected_sha


def test_arm_identity_is_bound_into_every_receipt(real_payloads: dict[str, dict]) -> None:
    baseline = real_payloads["baseline"]
    candidate = real_payloads["candidate"]
    assert baseline["generation"]["materialization_id"] != candidate["generation"]["materialization_id"]
    assert baseline["manifests"]["entries_sha256"] != candidate["manifests"]["entries_sha256"]
    assert baseline["manifests"]["raw_descriptors_sha256"] == candidate["manifests"]["raw_descriptors_sha256"]
    for payload in (baseline, candidate):
        for row in payload["entries"]:
            core = {key: value for key, value in row.items() if key != "binding_receipt_sha256"}
            assert row["materialization_id"] == payload["generation"]["materialization_id"]
            assert row["binding_receipt_sha256"] == audit.canonical_sha(core)


def test_heldout_is_identity_only_and_all_active(real_payloads: dict[str, dict]) -> None:
    rows = real_payloads["candidate"]["entries"]
    heldout = [row for row in rows if row["evaluation_partition"] == "heldout_s130"]
    assert len(heldout) == 70
    assert {row["binding_status"] for row in heldout} <= audit._BOUND_ACTIVE
    forbidden = {"content", "context", "question", "answer", "gold"}
    assert all(not (set(row) & forbidden) for row in rows)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("b" * 64, "known_physical"),
        ("backfill:" + "b" * 64, "synthetic_backfill"),
        ("legacy-id", "unknown"),
        (None, "unknown"),
    ],
)
def test_source_pdf_identity_status(value: str | None, expected: str) -> None:
    assert audit.source_pdf_identity_status(value) == expected


def _snapshot(*, source: str = EXTRACTION, status: str = "active", documents=None) -> dict:
    return {
        "documents": {
            DOCUMENT: {
                "id": DOCUMENT,
                "status": status,
                "source_pdf_sha256": source,
            }
        },
        "extraction_to_documents": {
            EXTRACTION: {DOCUMENT} if documents is None else documents,
        },
    }


def _m25(*, terminal: str = "primary_unique_active_pdf_sha") -> dict:
    return {
        EXTRACTION: {
            "extraction_sha256": EXTRACTION,
            "terminal": terminal,
            "document_id": DOCUMENT if terminal == "primary_unique_active_pdf_sha" else None,
            "matching_document_count": 1 if terminal == "primary_unique_active_pdf_sha" else 0,
            "status": "active" if terminal == "primary_unique_active_pdf_sha" else None,
        }
    }


def test_exact_physical_binding_requires_all_exact_receipts() -> None:
    row = audit._classify_binding(EXTRACTION, snapshot=_snapshot(), m25=_m25())
    assert row == {
        "document_id": DOCUMENT,
        "binding_status": "bound_active_physical_sha_verified",
        "binding_authority": "m25_exact_active_and_snapshot_reciprocal",
        "document_status_at_snapshot": "active",
        "source_pdf_identity": EXTRACTION,
        "source_pdf_identity_status": "known_physical",
    }


def test_legacy_binding_does_not_elevate_pdf_identity() -> None:
    source = "backfill:" + "b" * 64
    row = audit._classify_binding(
        EXTRACTION,
        snapshot=_snapshot(source=source),
        m25=_m25(terminal="primary_absent_pdf_sha"),
    )
    assert row["binding_status"] == "bound_active_legacy_snapshot_only"
    assert row["binding_authority"] == "legacy_snapshot_reciprocal_shadow_only"
    assert row["source_pdf_identity"] == source
    assert row["source_pdf_identity_status"] == "synthetic_backfill"


def test_contradictory_exact_active_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="contradictory exact-active"):
        audit._classify_binding(
            EXTRACTION,
            snapshot=_snapshot(source="b" * 64),
            m25=_m25(),
        )


def test_nonreciprocal_or_unknown_status_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="non-reciprocal"):
        audit._classify_binding(
            EXTRACTION,
            snapshot=_snapshot(documents={DOCUMENT, "00000000-0000-0000-0000-000000000002"}),
            m25=_m25(),
        )
    with pytest.raises(RuntimeError, match="unsupported bound document status"):
        audit._classify_binding(
            EXTRACTION,
            snapshot=_snapshot(status="retired"),
            m25=_m25(terminal="primary_non_active_pdf_sha"),
        )


def test_unbound_states_never_invent_document_or_pdf() -> None:
    for documents, expected in (
        (set(), "unbound_absent_from_snapshot"),
        ({""}, "unbound_snapshot_empty_document"),
    ):
        row = audit._classify_binding(
            EXTRACTION,
            snapshot=_snapshot(documents=documents),
            m25=_m25(terminal="primary_absent_pdf_sha"),
        )
        assert row["binding_status"] == expected
        assert row["document_id"] is None
        assert row["source_pdf_identity"] is None
        assert row["source_pdf_identity_status"] == "unknown"
