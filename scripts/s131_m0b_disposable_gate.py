#!/usr/bin/env python3
"""Run the S131 M0b database gate against the disposable local PostgreSQL.

This harness deliberately loads synthetic chunk bodies.  It validates the
frozen extraction/document binding population, relational constraints, RLS,
and the narrow lexical RPC.  It must never be used as evidence for semantic
retrieval quality or pgvector behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tmp" / "s131_m0b_runtime"
PSQL = RUNTIME / "postgresql" / "pgsql" / "bin" / "psql.exe"
BASELINE_SEED1 = ROOT / "evals" / "s131_shadow_binding_manifest_baseline_seed1_v1.json"
BASELINE_SEED2 = ROOT / "evals" / "s131_shadow_binding_manifest_baseline_seed2_v1.json"
GENERATED = RUNTIME / "generated"

HOST = "127.0.0.1"
PORT = "55431"
DATABASE = "s131_m0b"
USER = "postgres"

MATERIALIZATION_ID = "eb426a33-91cb-543e-a0c9-fd615dbc36cb"
MANIFEST_SHA256 = "3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1"
ROWS_MANIFEST_SHA256 = "68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3"
BINDINGS_MANIFEST_SHA256 = "951c6a7615045d770574404cf664385b741bd0097abeebed6a0b6bc1f410f2c1"
EXPECTED_BINDINGS = 1068
EXPECTED_CHUNKS = 31212

BINDING_COLUMNS = (
    "materialization_id",
    "extraction_sha256",
    "raw_artifact_sha256",
    "document_id",
    "binding_status",
    "binding_authority",
    "document_status_at_snapshot",
    "source_pdf_identity",
    "source_pdf_identity_status",
    "evaluation_partition",
    "snapshot_binding_ledger_sha256",
    "heldout_manifest_sha256",
    "binding_receipt_sha256",
)


class GateFailure(RuntimeError):
    """An expected S131 invariant did not hold."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def psql(sql: str, *, expected_error: str | None = None) -> str:
    if not PSQL.is_file():
        raise GateFailure(f"missing disposable psql runtime: {PSQL}")
    environment = os.environ.copy()
    environment["PGCLIENTENCODING"] = "UTF8"
    process = subprocess.run(
        [
            str(PSQL),
            "-X",
            "-h",
            HOST,
            "-p",
            PORT,
            "-U",
            USER,
            "-d",
            DATABASE,
            "-v",
            "ON_ERROR_STOP=1",
            "-A",
            "-t",
        ],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=environment,
        check=False,
    )
    combined = f"{process.stdout}\n{process.stderr}".strip()
    if expected_error is None:
        if process.returncode != 0:
            raise GateFailure(f"psql failed ({process.returncode}):\n{combined}")
        return process.stdout.strip()
    if process.returncode == 0:
        raise GateFailure(f"statement unexpectedly succeeded; wanted {expected_error!r}")
    if expected_error not in combined:
        raise GateFailure(
            f"expected error {expected_error!r} not found in psql output:\n{combined}"
        )
    return combined


def text_row(values: Iterable[object | None]) -> str:
    rendered: list[str] = []
    for value in values:
        if value is None:
            rendered.append(r"\N")
            continue
        cell = str(value)
        if any(character in cell for character in ("\t", "\r", "\n", "\\")):
            raise GateFailure(f"unsafe COPY text cell: {cell!r}")
        rendered.append(cell)
    return "\t".join(rendered)


def load_manifest() -> dict[str, object]:
    seed1_bytes = BASELINE_SEED1.read_bytes()
    seed2_bytes = BASELINE_SEED2.read_bytes()
    if seed1_bytes != seed2_bytes:
        raise GateFailure("baseline seed artifacts are not byte-identical")
    payload = json.loads(seed1_bytes)
    if payload.get("status") != "GO" or payload.get("arm") != "baseline":
        raise GateFailure("baseline binding manifest is not the frozen GO arm")
    generation = payload.get("generation", {})
    population = payload.get("population", {})
    entries = payload.get("entries", [])
    expected = {
        "materialization_id": MATERIALIZATION_ID,
        "generation_manifest_sha256": MANIFEST_SHA256,
        "expected_chunks_global": EXPECTED_CHUNKS,
    }
    if generation != expected:
        raise GateFailure(f"baseline generation tuple drift: {generation!r}")
    if len(entries) != EXPECTED_BINDINGS:
        raise GateFailure(f"expected {EXPECTED_BINDINGS} bindings, got {len(entries)}")
    if population.get("extractions") != EXPECTED_BINDINGS:
        raise GateFailure("population extraction count drift")
    return payload


def write_copy_fixtures(payload: dict[str, object]) -> tuple[Path, Path]:
    entries = payload["entries"]
    assert isinstance(entries, list)
    documents: dict[str, tuple[str, str]] = {}
    for entry in entries:
        assert isinstance(entry, dict)
        document_id = entry["document_id"]
        if document_id is None:
            continue
        identity = (entry["source_pdf_identity"], entry["document_status_at_snapshot"])
        if document_id in documents and documents[document_id] != identity:
            raise GateFailure(f"document identity conflict for {document_id}")
        documents[document_id] = identity
    if len(documents) != 1007:
        raise GateFailure(f"expected 1007 distinct bound documents, got {len(documents)}")

    GENERATED.mkdir(parents=True, exist_ok=True)
    documents_path = GENERATED / "baseline_documents.tsv"
    bindings_path = GENERATED / "baseline_bindings.tsv"
    documents_path.write_text(
        "\n".join(
            text_row((document_id, identity, status))
            for document_id, (identity, status) in sorted(documents.items())
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    bindings_path.write_text(
        "\n".join(text_row(entry[column] for column in BINDING_COLUMNS) for entry in entries)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return documents_path, bindings_path


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "''")


def load_baseline() -> dict[str, object]:
    payload = load_manifest()
    documents_path, bindings_path = write_copy_fixtures(payload)
    existing = psql(
        "SELECT count(*) FROM public.chunk_materializations_v1 "
        f"WHERE id = '{MATERIALIZATION_ID}'::uuid;"
    )
    if existing != "0":
        raise GateFailure("baseline materialization already exists; refusing an implicit reset")

    manifest = json.dumps(
        {
            "schema": "chunk_materialization_manifest_v1",
            "version": 1,
            "provenance_contract": "s116_section_lineage_v1",
            "arm": "baseline",
            "runtime_fixture": "s131_m0b_synthetic_content",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).replace("'", "''")

    load_sql = f"""
BEGIN;
\\copy public.documents (id, source_pdf_sha256, status) FROM '{sql_path(documents_path)}'
SET ROLE technical_bot_chunks_v3_shadow_loader;
INSERT INTO public.chunk_materializations_v1 (
    id, manifest_sha256, manifest, manifest_receipt_sha256,
    rows_manifest_sha256, expected_documents, expected_chunks,
    expected_bindings, bindings_manifest_sha256,
    expected_binding_counts, expected_partition_counts
) VALUES (
    '{MATERIALIZATION_ID}'::uuid,
    '{MANIFEST_SHA256}',
    '{manifest}'::jsonb,
    '{MANIFEST_SHA256}',
    '{ROWS_MANIFEST_SHA256}',
    {EXPECTED_BINDINGS},
    {EXPECTED_CHUNKS},
    {EXPECTED_BINDINGS},
    '{BINDINGS_MANIFEST_SHA256}',
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
);
CREATE TEMP TABLE s131_binding_stage (
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
\\copy s131_binding_stage ({', '.join(BINDING_COLUMNS)}) FROM '{sql_path(bindings_path)}'
INSERT INTO public.chunk_document_bindings_v1 ({', '.join(BINDING_COLUMNS)})
SELECT {', '.join(BINDING_COLUMNS)}
FROM s131_binding_stage;
WITH ranked_bindings AS (
    SELECT
        b.*,
        b.binding_status IN (
            'bound_active_physical_sha_verified',
            'bound_active_legacy_snapshot_only'
        ) AS retrieval_binding_eligible,
        row_number() OVER (ORDER BY b.extraction_sha256) AS binding_ordinal
    FROM s131_binding_stage AS b
    WHERE b.materialization_id = '{MATERIALIZATION_ID}'::uuid
), expanded AS (
    SELECT
        b.*,
        generated.chunk_index
    FROM ranked_bindings AS b
    CROSS JOIN LATERAL generate_series(
        0,
        CASE WHEN b.binding_ordinal = 1
             THEN {EXPECTED_CHUNKS} - {EXPECTED_BINDINGS}
             ELSE 0 END
    ) AS generated(chunk_index)
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
    'alpha s131 m0b synthetic contract row ' || e.extraction_sha256 || ' ' || e.chunk_index,
    'es',
    'text',
    1.0,
    'S131-M0B',
    'S131_SYNTHETIC',
    'contract_fixture',
    'synthetic/' || e.extraction_sha256 || '.json',
    1,
    's131-m0b',
    e.materialization_id,
    1,
    's116_section_lineage_v1',
    e.raw_artifact_sha256,
    pg_catalog.repeat('0', 64),
    e.extraction_sha256,
    e.raw_artifact_sha256,
    e.chunk_index,
    e.chunk_index,
    '[]'::jsonb,
    'none',
    'none',
    CASE WHEN e.retrieval_binding_eligible THEN 'eligible' ELSE 'register_only' END,
    e.binding_receipt_sha256
FROM expanded AS e;
SELECT public.validate_chunks_v3_shadow_v2(
    '{MATERIALIZATION_ID}'::uuid,
    '{ROWS_MANIFEST_SHA256}',
    '{BINDINGS_MANIFEST_SHA256}'
);
RESET ROLE;
COMMIT;
"""
    output = psql(load_sql)
    state = psql(
        "SELECT jsonb_build_object("
        "'state', state, 'bindings', observed_documents, 'chunks', observed_chunks) "
        "FROM public.chunk_materializations_v1 "
        f"WHERE id = '{MATERIALIZATION_ID}'::uuid;"
    )
    result = json.loads(state)
    if result != {
        "state": "validated",
        "bindings": EXPECTED_BINDINGS,
        "chunks": EXPECTED_CHUNKS,
    }:
        raise GateFailure(f"unexpected validated state: {result!r}")
    result["seed1_sha256"] = sha256_file(BASELINE_SEED1)
    result["seed2_sha256"] = sha256_file(BASELINE_SEED2)
    result["loader_output"] = output.splitlines()[-1] if output else ""
    return result


def assert_expected_error(name: str, sql: str, message: str, evidence: dict[str, object]) -> None:
    psql(sql, expected_error=message)
    evidence[name] = {"status": "PASS", "expected_error": message}


def verify_runtime() -> dict[str, object]:
    evidence: dict[str, object] = {}
    runtime = psql(
        "SELECT jsonb_build_object("
        "'server_version', current_setting('server_version'), "
        "'vector_extension_version', (SELECT extversion FROM pg_extension WHERE extname='vector'), "
        "'materialization_state', (SELECT state FROM public.chunk_materializations_v1 "
        f"WHERE id='{MATERIALIZATION_ID}'::uuid), "
        "'bindings', (SELECT count(*) FROM public.chunk_document_bindings_v1 "
        f"WHERE materialization_id='{MATERIALIZATION_ID}'::uuid), "
        "'chunks', (SELECT count(*) FROM public.chunks_v3 "
        f"WHERE materialization_id='{MATERIALIZATION_ID}'::uuid));"
    )
    evidence["runtime"] = json.loads(runtime)
    if evidence["runtime"] != {
        "server_version": "17.10",
        "vector_extension_version": "0.0.0",
        "materialization_state": "validated",
        "bindings": EXPECTED_BINDINGS,
        "chunks": EXPECTED_CHUNKS,
    }:
        raise GateFailure(f"runtime tuple drift: {evidence['runtime']!r}")

    rpc_count = psql(
        "SET ROLE technical_bot_chunks_v3_shadow_runner; "
        "SELECT count(*) FROM public.search_chunks_v3_shadow_text_v2("
        f"'{MATERIALIZATION_ID}'::uuid, 'development', 'alpha', "
        "NULL, NULL, NULL, 10);"
    ).splitlines()[-1]
    if rpc_count != "10":
        raise GateFailure(f"narrow lexical RPC returned {rpc_count!r}, expected 10")
    evidence["runner_narrow_rpc"] = {"status": "PASS", "rows": 10}

    role_rows = psql(
        "SELECT rolname || '|' || rolcanlogin || '|' || rolsuper || '|' || "
        "rolinherit || '|' || rolcreaterole || '|' || rolcreatedb || '|' || "
        "rolreplication || '|' || rolbypassrls "
        "FROM pg_catalog.pg_roles WHERE rolname IN ("
        "'technical_bot_chunks_v3_publisher',"
        "'technical_bot_chunks_v3_shadow_loader',"
        "'technical_bot_chunks_v3_shadow_rpc_owner',"
        "'technical_bot_chunks_v3_shadow_runner') ORDER BY rolname;"
    ).splitlines()
    if len(role_rows) != 4 or any(row.split("|")[1:] != ["false"] * 7 for row in role_rows):
        raise GateFailure(f"shadow role attributes drift: {role_rows!r}")
    evidence["role_attributes"] = {"status": "PASS", "roles": role_rows}

    relation_catalog = psql(
        "SELECT jsonb_object_agg(relname, jsonb_build_object("
        "'owner', pg_catalog.pg_get_userbyid(relowner), "
        "'rls', relrowsecurity, 'kind', relkind)) "
        "FROM pg_catalog.pg_class WHERE relnamespace='public'::regnamespace "
        "AND relname IN ('chunk_materializations_v1','chunk_document_bindings_v1',"
        "'chunks_v3','chunks_v3_shadow_retrieval_eligible_v2');"
    )
    relations = json.loads(relation_catalog)
    expected_relations = {
        "chunk_materializations_v1": {"owner": "postgres", "rls": True, "kind": "r"},
        "chunk_document_bindings_v1": {"owner": "postgres", "rls": True, "kind": "r"},
        "chunks_v3": {"owner": "postgres", "rls": True, "kind": "r"},
        "chunks_v3_shadow_retrieval_eligible_v2": {
            "owner": "technical_bot_chunks_v3_shadow_rpc_owner",
            "rls": False,
            "kind": "v",
        },
    }
    if relations != expected_relations:
        raise GateFailure(f"relation catalog drift: {relations!r}")
    evidence["relation_catalog"] = {"status": "PASS", **relations}

    function_catalog = psql(
        "SELECT jsonb_object_agg(p.proname, jsonb_build_object("
        "'owner', pg_catalog.pg_get_userbyid(p.proowner), "
        "'security_definer', p.prosecdef, 'config', p.proconfig)) "
        "FROM pg_catalog.pg_proc AS p JOIN pg_catalog.pg_namespace AS n "
        "ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname IN ("
        "'validate_chunks_v3_shadow_v2','discard_chunks_v3_shadow_v2',"
        "'search_chunks_v3_shadow_text_v2');"
    )
    functions = json.loads(function_catalog)
    for name in ("validate_chunks_v3_shadow_v2", "discard_chunks_v3_shadow_v2"):
        if functions.get(name) != {
            "owner": "technical_bot_chunks_v3_publisher",
            "security_definer": True,
            "config": ['search_path=""'],
        }:
            raise GateFailure(f"transition function catalog drift: {functions!r}")
    if functions.get("search_chunks_v3_shadow_text_v2") != {
        "owner": "technical_bot_chunks_v3_shadow_rpc_owner",
        "security_definer": True,
        "config": ['search_path=""'],
    }:
        raise GateFailure(f"search function catalog drift: {functions!r}")
    evidence["function_catalog"] = {"status": "PASS", **functions}

    structural_counts = json.loads(
        psql(
            "SELECT jsonb_build_object("
            "'binding_policies', (SELECT count(*) FROM pg_catalog.pg_policies "
            "WHERE schemaname='public' AND tablename='chunk_document_bindings_v1'),"
            "'triggers', (SELECT count(*) FROM pg_catalog.pg_trigger "
            "WHERE tgrelid IN ('public.chunks_v3'::regclass, "
            "'public.chunk_document_bindings_v1'::regclass) AND NOT tgisinternal),"
            "'binding_fk', (SELECT count(*) FROM pg_catalog.pg_constraint "
            "WHERE conname='chunks_v3_s131_binding_fkey'),"
            "'eligible_fts_index', (SELECT count(*) FROM pg_catalog.pg_indexes "
            "WHERE schemaname='public' AND indexname='chunks_v3_s131_fts_eligible_idx'));"
        )
    )
    if structural_counts != {
        "binding_policies": 4,
        "triggers": 3,
        "binding_fk": 1,
        "eligible_fts_index": 1,
    }:
        raise GateFailure(f"catalog structure drift: {structural_counts!r}")
    evidence["catalog_structure"] = {"status": "PASS", **structural_counts}

    assert_expected_error(
        "runner_direct_table_denied",
        "SET ROLE technical_bot_chunks_v3_shadow_runner; SELECT count(*) FROM public.chunks_v3;",
        "permission denied for table chunks_v3",
        evidence,
    )
    for object_name in (
        "chunk_materializations_v1",
        "chunk_document_bindings_v1",
        "chunks_v3_shadow_retrieval_eligible_v2",
        "documents",
    ):
        assert_expected_error(
            f"runner_direct_{object_name}_denied",
            f"SET ROLE technical_bot_chunks_v3_shadow_runner; "
            f"SELECT count(*) FROM public.{object_name};",
            f"permission denied for {'view' if object_name.endswith('_v2') else 'table'} {object_name}",
            evidence,
        )
    assert_expected_error(
        "loader_direct_table_read_denied",
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        "SELECT count(*) FROM public.chunk_document_bindings_v1;",
        "permission denied for table chunk_document_bindings_v1",
        evidence,
    )
    for role in ("anon", "authenticated", "service_role"):
        assert_expected_error(
            f"{role}_rpc_denied",
            f"SET ROLE {role}; SELECT count(*) FROM public.search_chunks_v3_shadow_text_v2("
            f"'{MATERIALIZATION_ID}'::uuid, 'development', 'alpha', NULL, NULL, NULL, 10);",
            "permission denied for function search_chunks_v3_shadow_text_v2",
            evidence,
        )
        assert_expected_error(
            f"{role}_direct_read_denied",
            f"SET ROLE {role}; SELECT count(*) FROM public.chunks_v3;",
            "permission denied for table chunks_v3",
            evidence,
        )
        assert_expected_error(
            f"{role}_insert_denied",
            f"SET ROLE {role}; INSERT INTO public.chunks_v3 DEFAULT VALUES;",
            "permission denied for table chunks_v3",
            evidence,
        )
    assert_expected_error(
        "invalid_partition_rejected",
        "SET ROLE technical_bot_chunks_v3_shadow_runner; "
        "SELECT count(*) FROM public.search_chunks_v3_shadow_text_v2("
        f"'{MATERIALIZATION_ID}'::uuid, 'production', 'alpha', NULL, NULL, NULL, 10);",
        "S131 invalid shadow query",
        evidence,
    )
    assert_expected_error(
        "unvalidated_materialization_rejected",
        "SET ROLE technical_bot_chunks_v3_shadow_runner; "
        "SELECT count(*) FROM public.search_chunks_v3_shadow_text_v2("
        "'00000000-0000-4000-8000-000000000131'::uuid, 'development', "
        "'alpha', NULL, NULL, NULL, 10);",
        "S131 shadow materialization is not validated",
        evidence,
    )
    assert_expected_error(
        "sealed_chunk_update_rejected",
        "UPDATE public.chunks_v3 SET content = content || ' forbidden' "
        f"WHERE materialization_id = '{MATERIALIZATION_ID}'::uuid "
        "AND id = (SELECT id FROM public.chunks_v3 "
        f"WHERE materialization_id = '{MATERIALIZATION_ID}'::uuid "
        "ORDER BY id LIMIT 1);",
        "chunks_v3 rows are append-only",
        evidence,
    )
    assert_expected_error(
        "sealed_binding_update_rejected",
        "UPDATE public.chunk_document_bindings_v1 SET binding_authority = binding_authority "
        f"WHERE materialization_id = '{MATERIALIZATION_ID}'::uuid "
        "AND extraction_sha256 = (SELECT min(extraction_sha256) "
        "FROM public.chunk_document_bindings_v1 "
        f"WHERE materialization_id = '{MATERIALIZATION_ID}'::uuid);",
        "S131 bindings are append-only",
        evidence,
    )
    assert_expected_error(
        "validated_discard_rejected",
        "SET ROLE technical_bot_chunks_v3_shadow_loader; "
        f"SELECT public.discard_chunks_v3_shadow_v2('{MATERIALIZATION_ID}'::uuid);",
        "S131 discard requires loading or failed",
        evidence,
    )

    old_routes = psql(
        "SELECT jsonb_build_object("
        "'match_chunks_v3', to_regprocedure('public.match_chunks_v3(extensions.vector,double precision,integer,text,text,text,uuid)'), "
        "'search_chunks_text_v3', to_regprocedure('public.search_chunks_text_v3(text,text,text,text,integer,uuid)'), "
        "'publish_v1', to_regprocedure('public.publish_chunks_v3_materialization_v1(uuid)'), "
        "'validate_v1', to_regprocedure('public.validate_chunks_v3_materialization_v1(uuid,text)'), "
        "'discard_v1', to_regprocedure('public.discard_chunks_v3_materialization_v1(uuid)'));"
    )
    old_route_values = json.loads(old_routes)
    if any(value is not None for value in old_route_values.values()):
        raise GateFailure(f"antecedent serving routes remain: {old_route_values!r}")
    evidence["antecedent_routes_absent"] = {"status": "PASS", **old_route_values}
    evidence["pgvector_semantics"] = {
        "status": "NOT_MEASURED",
        "reason": "local vector extension is a signature-only shim, not pgvector",
    }
    evidence["semantic_retrieval_quality"] = {
        "status": "NOT_MEASURED",
        "reason": "chunk content is synthetic and only exercises the relational contract",
    }
    return evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("load-baseline", "verify", "full"))
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    report: dict[str, object] = {
        "instrument": "s131_m0b_disposable_gate_v1",
        "database": f"postgresql://{HOST}:{PORT}/{DATABASE}",
    }
    if arguments.command in ("load-baseline", "full"):
        report["load"] = load_baseline()
    if arguments.command in ("verify", "full"):
        report["verification"] = verify_runtime()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateFailure as error:
        print(json.dumps({"status": "NO_GO", "error": str(error)}, indent=2), file=sys.stderr)
        raise SystemExit(1) from error
