#!/usr/bin/env python3
"""Exercise S131 M0b negative runtime paths on the disposable database."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from s131_m0b_disposable_gate import (
    BINDING_COLUMNS,
    DATABASE,
    GENERATED,
    GateFailure,
    HOST,
    MATERIALIZATION_ID as BASELINE_ID,
    PORT,
    PSQL,
    ROOT,
    USER,
    psql,
    sql_path,
    text_row,
)


CANDIDATE_SEED1 = ROOT / "evals" / "s131_shadow_binding_manifest_candidate_seed1_v1.json"
CANDIDATE_SEED2 = ROOT / "evals" / "s131_shadow_binding_manifest_candidate_seed2_v1.json"
CANDIDATE_ID = "1852e61c-ac7f-5232-be1c-627ea54f29b5"
CANDIDATE_MANIFEST_SHA256 = "f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089"
CANDIDATE_ROWS_SHA256 = "cdfcbae0cf476bf74cad9712b5a3f32433a9ea73662116e468ec27522c5cbb63"
CANDIDATE_BINDINGS_SHA256 = "aa870ab8a484700656252d0315808ee69076a57edfa5d4c0c128e2dd54a13746"
EXPECTED_BINDINGS = 1068
EXPECTED_CHUNKS = 31226
MISMATCH_SHA256 = "3b6b21ee0838a8a541cd0dfb7f4f6d48f24776f48fd862e30f3d6a54fcb132b8"


def candidate_payload() -> dict[str, Any]:
    seed1 = CANDIDATE_SEED1.read_bytes()
    seed2 = CANDIDATE_SEED2.read_bytes()
    if seed1 != seed2:
        raise GateFailure("candidate seed artifacts are not byte-identical")
    payload = json.loads(seed1)
    if payload.get("status") != "GO" or payload.get("arm") != "candidate":
        raise GateFailure("candidate manifest is not the frozen GO arm")
    if payload.get("generation") != {
        "materialization_id": CANDIDATE_ID,
        "generation_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "expected_chunks_global": EXPECTED_CHUNKS,
    }:
        raise GateFailure("candidate generation tuple drift")
    entries = payload.get("entries", [])
    if len(entries) != EXPECTED_BINDINGS:
        raise GateFailure(f"expected {EXPECTED_BINDINGS} candidate bindings, got {len(entries)}")
    return payload


def candidate_bindings_path(payload: dict[str, Any]) -> Path:
    GENERATED.mkdir(parents=True, exist_ok=True)
    path = GENERATED / "candidate_bindings.tsv"
    path.write_text(
        "\n".join(
            text_row(entry[column] for column in BINDING_COLUMNS)
            for entry in payload["entries"]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def registry_insert(*, manifest_sha256: str = CANDIDATE_MANIFEST_SHA256) -> str:
    manifest = json.dumps(
        {
            "schema": "chunk_materialization_manifest_v1",
            "version": 1,
            "provenance_contract": "s116_section_lineage_v1",
            "arm": "candidate",
            "runtime_fixture": "s131_m0b_synthetic_content",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).replace("'", "''")
    return f"""
INSERT INTO public.chunk_materializations_v1 (
    id, manifest_sha256, manifest, manifest_receipt_sha256,
    rows_manifest_sha256, expected_documents, expected_chunks,
    expected_bindings, bindings_manifest_sha256,
    expected_binding_counts, expected_partition_counts
) VALUES (
    '{CANDIDATE_ID}'::uuid,
    '{manifest_sha256}',
    '{manifest}'::jsonb,
    '{CANDIDATE_MANIFEST_SHA256}',
    '{CANDIDATE_ROWS_SHA256}',
    {EXPECTED_BINDINGS},
    {EXPECTED_CHUNKS},
    {EXPECTED_BINDINGS},
    '{CANDIDATE_BINDINGS_SHA256}',
    '{{
      "bound_active_physical_sha_verified": 405,
      "bound_active_legacy_snapshot_only": 597,
      "bound_nonactive_legacy_snapshot": 8,
      "unbound_snapshot_empty_document": 8,
      "unbound_absent_from_snapshot": 50
    }}'::jsonb,
    '{{
      "development": {{"extractions_total": 998, "bound_active_extractions": 932}},
      "heldout_s130": {{"extractions_total": 70, "bound_active_extractions": 70}}
    }}'::jsonb
)
"""


def assert_candidate_absent() -> None:
    counts = psql(
        "SELECT jsonb_build_array("
        "(SELECT count(*) FROM public.chunk_materializations_v1 "
        f"WHERE id='{CANDIDATE_ID}'::uuid),"
        "(SELECT count(*) FROM public.chunk_document_bindings_v1 "
        f"WHERE materialization_id='{CANDIDATE_ID}'::uuid),"
        "(SELECT count(*) FROM public.chunks_v3 "
        f"WHERE materialization_id='{CANDIDATE_ID}'::uuid));"
    )
    if json.loads(counts) != [0, 0, 0]:
        raise GateFailure(f"candidate residue remains: {counts}")


def stage_table_sql(path: Path) -> str:
    return f"""
CREATE TEMP TABLE s131_candidate_binding_stage (
    materialization_id UUID NOT NULL,
    extraction_sha256 TEXT NOT NULL,
    raw_artifact_sha256 TEXT NOT NULL,
    document_id UUID,
    binding_status TEXT NOT NULL,
    binding_authority TEXT NOT NULL,
    document_status_at_snapshot TEXT,
    source_pdf_identity TEXT,
    source_pdf_identity_status TEXT NOT NULL,
    evaluation_partition TEXT NOT NULL,
    snapshot_binding_ledger_sha256 TEXT NOT NULL,
    heldout_manifest_sha256 TEXT NOT NULL,
    binding_receipt_sha256 TEXT NOT NULL
) ON COMMIT DROP;
\\copy s131_candidate_binding_stage ({', '.join(BINDING_COLUMNS)}) FROM '{sql_path(path)}'
INSERT INTO public.chunk_document_bindings_v1 ({', '.join(BINDING_COLUMNS)})
SELECT {', '.join(BINDING_COLUMNS)} FROM s131_candidate_binding_stage;
"""


def load_candidate(path: Path, defect: str) -> None:
    if defect not in ("valid", "binding_without_chunks", "raw_mismatch", "ineligible_retrieval"):
        raise GateFailure(f"unknown candidate defect {defect!r}")
    assert_candidate_absent()
    if defect == "binding_without_chunks":
        series_end = (
            f"CASE WHEN b.binding_ordinal = 1 THEN {EXPECTED_CHUNKS - EXPECTED_BINDINGS + 1} "
            f"WHEN b.binding_ordinal = {EXPECTED_BINDINGS} THEN -1 ELSE 0 END"
        )
    else:
        series_end = (
            f"CASE WHEN b.binding_ordinal = 1 THEN {EXPECTED_CHUNKS - EXPECTED_BINDINGS} "
            "ELSE 0 END"
        )
    raw_expression = "e.raw_artifact_sha256"
    if defect == "raw_mismatch":
        raw_expression = (
            f"CASE WHEN e.binding_ordinal = 1 AND e.chunk_index = 0 "
            f"THEN '{MISMATCH_SHA256}' ELSE e.raw_artifact_sha256 END"
        )
    retrieval_expression = (
        "CASE WHEN e.retrieval_binding_eligible THEN 'eligible' ELSE 'register_only' END"
    )
    if defect == "ineligible_retrieval":
        retrieval_expression = (
            "CASE WHEN NOT e.retrieval_binding_eligible "
            "AND e.extraction_sha256 = e.first_ineligible_extraction "
            "THEN 'eligible' WHEN e.retrieval_binding_eligible "
            "THEN 'eligible' ELSE 'register_only' END"
        )
    load_sql = f"""
BEGIN;
SET ROLE technical_bot_chunks_v3_shadow_loader;
{registry_insert()};
{stage_table_sql(path)}
WITH ranked_bindings AS (
    SELECT
        b.*,
        b.binding_status IN (
            'bound_active_physical_sha_verified',
            'bound_active_legacy_snapshot_only'
        ) AS retrieval_binding_eligible,
        min(b.extraction_sha256) FILTER (
            WHERE b.binding_status NOT IN (
                'bound_active_physical_sha_verified',
                'bound_active_legacy_snapshot_only'
            )
        ) OVER () AS first_ineligible_extraction,
        row_number() OVER (ORDER BY b.extraction_sha256) AS binding_ordinal
    FROM s131_candidate_binding_stage AS b
), expanded AS (
    SELECT b.*, generated.chunk_index
    FROM ranked_bindings AS b
    CROSS JOIN LATERAL generate_series(0, {series_end}) AS generated(chunk_index)
)
INSERT INTO public.chunks_v3 (
    id, document_id, extraction_sha256, chunk_index, content, language,
    content_type, confidence, product_model, manufacturer, category,
    source_file, page_number, ingest_batch, materialization_id,
    provenance_version, provenance_contract, raw_artifact_sha256,
    chunker_sha256, content_sha256, provenance_payload_sha256,
    source_block_start, source_block_end, section_lineage,
    context_origin, embedding_origin, retrieval_policy_class,
    retrieval_policy_receipt_sha256
)
SELECT
    pg_catalog.md5(
        e.materialization_id::text || ':' || e.extraction_sha256 || ':' || e.chunk_index::text
    )::uuid,
    e.document_id,
    e.extraction_sha256,
    e.chunk_index,
    'alpha s131 m0b candidate ' || e.extraction_sha256 || ' ' || e.chunk_index,
    'es', 'text', 1.0, 'S131-M0B', 'S131_SYNTHETIC', 'contract_fixture',
    'synthetic/' || e.extraction_sha256 || '.json', 1, 's131-m0b',
    e.materialization_id, 1, 's116_section_lineage_v1',
    {raw_expression},
    pg_catalog.repeat('0', 64), e.extraction_sha256, e.raw_artifact_sha256,
    e.chunk_index, e.chunk_index, '[]'::jsonb, 'none', 'none',
    {retrieval_expression},
    e.binding_receipt_sha256
FROM expanded AS e;
RESET ROLE;
COMMIT;
"""
    psql(load_sql)
    counts = json.loads(
        psql(
            "SELECT jsonb_build_array("
            "(SELECT count(*) FROM public.chunk_document_bindings_v1 "
            f"WHERE materialization_id='{CANDIDATE_ID}'::uuid),"
            "(SELECT count(*) FROM public.chunks_v3 "
            f"WHERE materialization_id='{CANDIDATE_ID}'::uuid));"
        )
    )
    if counts != [EXPECTED_BINDINGS, EXPECTED_CHUNKS]:
        raise GateFailure(f"candidate load count mismatch for {defect}: {counts}")


def discard_candidate() -> dict[str, Any]:
    result = psql(
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        f"SELECT public.discard_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid);"
    ).splitlines()[-1]
    payload = json.loads(result)
    if payload.get("removed_bindings") != EXPECTED_BINDINGS:
        raise GateFailure(f"discard binding count mismatch: {payload!r}")
    if payload.get("removed_chunks") != EXPECTED_CHUNKS:
        raise GateFailure(f"discard chunk count mismatch: {payload!r}")
    assert_candidate_absent()
    return payload


def exercise_static_rejections(payload: dict[str, Any]) -> dict[str, Any]:
    first = payload["entries"][0]
    report: dict[str, Any] = {}
    psql(
        "BEGIN; SET ROLE technical_bot_chunks_v3_shadow_loader; "
        + registry_insert(manifest_sha256="0" * 64)
        + "; COMMIT;",
        expected_error="chunk_materializations_v1_s131_shadow_manifest_chk",
    )
    report["wrong_registry_tuple"] = "PASS"
    assert_candidate_absent()

    invalid_binding = dict(first)
    invalid_binding["materialization_id"] = CANDIDATE_ID
    invalid_binding["binding_authority"] = "invalid_crossed_authority"
    values = []
    for column in BINDING_COLUMNS:
        value = invalid_binding[column]
        values.append("NULL" if value is None else "'" + str(value).replace("'", "''") + "'")
    psql(
        "BEGIN; SET ROLE technical_bot_chunks_v3_shadow_loader; "
        + registry_insert()
        + "; INSERT INTO public.chunk_document_bindings_v1 ("
        + ", ".join(BINDING_COLUMNS)
        + ") VALUES ("
        + ", ".join(values)
        + "); COMMIT;",
        expected_error="chunk_document_bindings_v1_truth_table_chk",
    )
    report["crossed_binding_truth_table"] = "PASS"
    assert_candidate_absent()

    missing_extraction = "f" * 64
    psql(
        "BEGIN; SET ROLE technical_bot_chunks_v3_shadow_loader; "
        + registry_insert()
        + "; INSERT INTO public.chunks_v3 ("
        "id, document_id, extraction_sha256, chunk_index, content, language, "
        "content_type, materialization_id, provenance_version, provenance_contract, "
        "raw_artifact_sha256, chunker_sha256, content_sha256, provenance_payload_sha256, "
        "source_block_start, source_block_end, section_lineage, context_origin, "
        "embedding_origin, retrieval_policy_class, retrieval_policy_receipt_sha256"
        ") VALUES ("
        "'ffffffff-ffff-4fff-8fff-ffffffffffff'::uuid, NULL, "
        f"'{missing_extraction}', 0, 'orphan', 'es', 'text', '{CANDIDATE_ID}'::uuid, "
        "1, 's116_section_lineage_v1', "
        f"'{missing_extraction}', repeat('0',64), '{missing_extraction}', "
        f"'{missing_extraction}', 0, 0, '[]'::jsonb, 'none', 'none', "
        f"'register_only', '{missing_extraction}'); COMMIT;",
        expected_error="chunks_v3_s131_binding_fkey",
    )
    report["chunk_without_binding"] = "PASS"
    assert_candidate_absent()
    return report


def validate_expect(error: str) -> None:
    psql(
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        f"SELECT public.validate_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid, "
        f"'{CANDIDATE_ROWS_SHA256}', '{CANDIDATE_BINDINGS_SHA256}');",
        expected_error=error,
    )


def exercise_validator_rejections(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    load_candidate(path, "valid")
    psql(
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        f"SELECT public.validate_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid, "
        f"'{'0' * 64}', '{CANDIDATE_BINDINGS_SHA256}');",
        expected_error="S131 frozen manifest assertion mismatch",
    )
    report["asserted_manifest_mismatch"] = "PASS"

    document_id = next(entry["document_id"] for entry in payload["entries"] if entry["document_id"])
    psql(
        "BEGIN; UPDATE public.documents SET status = "
        "CASE WHEN status = 'active' THEN 'needs_review' ELSE 'active' END "
        f"WHERE id = '{document_id}'::uuid; "
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        f"SELECT public.validate_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid, "
        f"'{CANDIDATE_ROWS_SHA256}', '{CANDIDATE_BINDINGS_SHA256}'); COMMIT;",
        expected_error="S131 document identity or status drift",
    )
    report["document_status_drift"] = "PASS"
    report["valid_loading_discard"] = discard_candidate()

    for defect, expected_error in (
        ("binding_without_chunks", "S131 binding without chunks"),
        ("raw_mismatch", "S131 chunk/binding identity mismatch"),
        ("ineligible_retrieval", "S131 ineligible binding marked for retrieval"),
    ):
        load_candidate(path, defect)
        validate_expect(expected_error)
        report[defect] = {"status": "PASS", "error": expected_error}
        report[f"{defect}_discard"] = discard_candidate()
    return report


def race_command(function_sql: str) -> list[str]:
    return [
        str(PSQL), "-X", "-h", HOST, "-p", PORT, "-U", USER, "-d", DATABASE,
        "-v", "ON_ERROR_STOP=1", "-A", "-t", "-c",
        "SELECT pg_catalog.pg_sleep(0.5); SET ROLE technical_bot_chunks_v3_shadow_loader; "
        + function_sql,
    ]


def exercise_transition_race(path: Path) -> dict[str, Any]:
    load_candidate(path, "valid")
    environment = os.environ.copy()
    environment["PGCLIENTENCODING"] = "UTF8"
    validate = subprocess.Popen(
        race_command(
            f"SELECT public.validate_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid, "
            f"'{CANDIDATE_ROWS_SHA256}', '{CANDIDATE_BINDINGS_SHA256}');"
        ),
        text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=environment,
    )
    discard = subprocess.Popen(
        race_command(f"SELECT public.discard_chunks_v3_shadow_v2('{CANDIDATE_ID}'::uuid);"),
        text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=environment,
    )
    validate_stdout, validate_stderr = validate.communicate(timeout=120)
    discard_stdout, discard_stderr = discard.communicate(timeout=120)
    outcomes = {
        "validate": {
            "returncode": validate.returncode,
            "stdout": validate_stdout.strip(),
            "stderr": validate_stderr.strip(),
        },
        "discard": {
            "returncode": discard.returncode,
            "stdout": discard_stdout.strip(),
            "stderr": discard_stderr.strip(),
        },
    }
    successes = [name for name, result in outcomes.items() if result["returncode"] == 0]
    if len(successes) != 1:
        raise GateFailure(f"validate/discard race did not serialize: {outcomes!r}")
    loser = "discard" if successes[0] == "validate" else "validate"
    if "not loading" not in outcomes[loser]["stderr"] and "requires loading" not in outcomes[loser]["stderr"]:
        raise GateFailure(f"race loser failed for an unexpected reason: {outcomes!r}")
    state = psql(
        "SELECT COALESCE((SELECT state FROM public.chunk_materializations_v1 "
        f"WHERE id='{CANDIDATE_ID}'::uuid), 'absent');"
    )
    expected_state = "validated" if successes[0] == "validate" else "absent"
    if state != expected_state:
        raise GateFailure(f"race terminal state {state!r}, expected {expected_state!r}")
    return {"status": "PASS", "winner": successes[0], "terminal_state": state}


def main() -> int:
    baseline_state = psql(
        "SELECT state FROM public.chunk_materializations_v1 "
        f"WHERE id='{BASELINE_ID}'::uuid;"
    )
    if baseline_state != "validated":
        raise GateFailure("validated baseline is required before negative M0b tests")
    payload = candidate_payload()
    path = candidate_bindings_path(payload)
    report = {
        "instrument": "s131_m0b_negative_gate_v1",
        "static_rejections": exercise_static_rejections(payload),
        "validator_rejections": exercise_validator_rejections(path, payload),
        "transition_race": exercise_transition_race(path),
        "models": 0,
        "network": 0,
        "pgvector_semantics": "NOT_MEASURED_SIGNATURE_SHIM",
        "retrieval_quality": "NOT_MEASURED_SYNTHETIC_CONTENT",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateFailure as error:
        print(json.dumps({"status": "NO_GO", "error": str(error)}, indent=2), file=sys.stderr)
        raise SystemExit(1) from error
