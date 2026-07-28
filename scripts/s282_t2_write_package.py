#!/usr/bin/env python3
"""s282 T2 — WRITE PACKAGE generator (sealed, NOT applied).

Emits the sealed application package for the s83 identity backfill over ``documents``
(Tramo 2): fills only ``doc_type`` and ``language`` (SINGLETON) on documents whose DB
value is NULL. ``product_model``/``manufacturer`` are NEVER written. Consumes the FROZEN,
deterministic v3 cohort (``evals/s282_qa_s83_result_v3.json``; guard 2x byte-identical,
records-sha ``2c6bac68...``).

Fixes the dúo finding ``PAQUETE-ESCRITURA-NO-SELLADO``
(``evals/s282_t2_apply_duo_r1_adjudication_v1.yaml``):
  * per-row manifest {document_id (mapping FROZEN NOW + verified 1:1), source_file,
    doc_type, language SCALAR}, with a DB before-image snapshot per row;
  * sealed shas: manifest content-sha + result_v3 records-sha + corpus fingerprint sha +
    commit HEAD + s83 model/identity shas (fix ``PROVENANCE-NO-SELLADA``);
  * SQL: staging VALUES from the manifest + UPDATE ... FROM staging JOIN by id, NULL-only
    guards, declared expected counts, RETURNING captured as before-image, post-apply
    verification block, and a rollback generated from the before-image.

STOP contract: if ANY lot row maps to 0 or >1 ACTIVE documents, or a singleton language is
not length-1, or a lot row has no doc_type value, the script ABORTS (exit 2) and writes
nothing — per the adjudication (mapping must be a clean 1:1 freeze).

READ-ONLY / SELECT-only (documents + chunks_v2). Zero writes, zero paid model calls.
NO commits. Outputs restricted to this lane's territory (evals/s282_t2_*).

Usage:
  python scripts/s282_t2_write_package.py     # emit manifest_v1.json + apply_v1.sql ($0)
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# reuse the v1 instrument's read-only HTTP stack + helpers.
_spec = importlib.util.spec_from_file_location(
    "s282_qa_s83_instrument", ROOT / "scripts/s282_qa_s83_instrument.py")
inst = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
_spec.loader.exec_module(inst)                         # type: ignore[union-attr]
import src.rag.document_local_coverage as dlc          # noqa: E402  (canonical_blob_stem)

V3_RESULT = ROOT / "evals/s282_qa_s83_result_v3.json"
V1_RESULT = ROOT / "evals/s282_qa_s83_result_v1.json"
MANIFEST = ROOT / "evals/s282_t2_manifest_v1.json"
SQL_OUT = ROOT / "evals/s282_t2_apply_v1.sql"

AUTO_APPLY = {"corroborate_noop", "fill_language_doctype"}
EXPECTED_CORPUS_SHA = "aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d"
EXPECTED_RECORDS_SHA = "2c6bac681ad89001"  # v3 guard 2x-byte-identical records-sha (prefix)


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _fail(msg: str) -> None:
    print(f"STOP: {msg}", file=sys.stderr)
    sys.exit(2)


def in_lot(r: dict[str, Any]) -> bool:
    fp = r.get("fill_plan") or {}
    return r["write_op"] in AUTO_APPLY and bool(
        fp.get("doc_type_fill") or fp.get("language_fill_singleton"))


def build_active_map(lot_sfs: list[str]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Live SELECT reconstruction of source_file -> single ACTIVE document (frozen now).

    Mirrors the instrument's resolution exactly: chunk_map ∪ stem, docmap fallback,
    restrict to status=='active'. Requires EXACTLY 1 active doc per lot source_file.
    """
    documents = inst._get_all("documents", inst.DOC_SELECT, order="id.asc")
    chunks = inst._get_all("chunks_v2", "source_file,document_id", order="id.asc")
    chunk_map = inst._chunk_srcfile_to_docids(chunks)
    docmap_rows = [json.loads(l) for l in (inst.CATALOG_DIR / "doc_map.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    docmap: dict[str, list[str]] = {}
    for r in docmap_rows:
        sf, did = r.get("source_file"), r.get("document_id")
        if sf and did:
            docmap.setdefault(str(sf), []).append(str(did))
    doc_index = {str(d["id"]): d for d in documents}

    def active_ids(sf: str) -> list[str]:
        ids = set(chunk_map.get(sf, set())) | set(chunk_map.get(dlc.canonical_blob_stem(sf), set()))
        if not ids:
            ids |= set(docmap.get(sf, [])) | set(docmap.get(dlc.canonical_blob_stem(sf), []))
        docs = [doc_index[d] for d in ids if d in doc_index]
        return sorted(str(d["id"]) for d in docs if str(d.get("status")) == "active")

    mapping: dict[str, str] = {}
    zero, multi = [], []
    for sf in lot_sfs:
        aids = active_ids(sf)
        if len(aids) == 0:
            zero.append(sf)
        elif len(aids) > 1:
            multi.append((sf, aids))
        else:
            mapping[sf] = aids[0]
    if zero or multi:
        _fail(f"mapping NOT 1:1 — zero-active={len(zero)} multi-active={len(multi)}; "
              f"zero={zero[:10]} multi={multi[:10]}")
    return mapping, doc_index


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    v3 = json.loads(V3_RESULT.read_text(encoding="utf-8"))
    records = v3["records"]

    # --- seal: recompute the v3 records-sha and assert it matches the frozen deterministic value.
    records_sha = inst._stable_sha256(records)
    if not records_sha.startswith(EXPECTED_RECORDS_SHA):
        _fail(f"v3 records-sha {records_sha[:16]} != frozen {EXPECTED_RECORDS_SHA} — cohort drifted")

    lot = [r for r in records if in_lot(r)]
    lot.sort(key=lambda r: r["source_file"])

    # --- per-axis assertions (STOP on any structural surprise).
    for r in lot:
        fp = r["fill_plan"]
        if not fp.get("doc_type_fill") or fp.get("doc_type_value") in (None, ""):
            _fail(f"lot row {r['source_file']} has no doc_type value (expected doc_type_fill)")
        if fp.get("language_fill_singleton"):
            lv = fp.get("language_value") or []
            if len(lv) != 1:
                _fail(f"lot row {r['source_file']} singleton language_value not length-1: {lv}")

    # --- live init + freeze contract + corpus fingerprint (provenance seal).
    inst._init_http()
    contract = inst.freeze_contract()
    fp_corpus = inst.corpus_fingerprint()
    if fp_corpus["sha256"] != EXPECTED_CORPUS_SHA:
        _fail(f"corpus fingerprint {fp_corpus['sha256'][:16]} != v3 frame {EXPECTED_CORPUS_SHA[:16]} — drift")

    lot_sfs = [r["source_file"] for r in lot]
    mapping, doc_index = build_active_map(lot_sfs)

    # --- optional cross-check vs frozen v1 active_document_ids (belt-and-suspenders).
    v1_mismatch = 0
    try:
        v1 = json.loads(V1_RESULT.read_text(encoding="utf-8"))
        v1recs = v1.get("deterministic", {}).get("records") or v1.get("records") or []
        v1map = {r["source_file"]: r for r in v1recs}
        for sf, did in mapping.items():
            vr = v1map.get(sf)
            aid = (vr or {}).get("document", {}).get("active_document_ids")
            if aid is not None and aid != [did]:
                v1_mismatch += 1
    except Exception:
        v1_mismatch = -1  # v1 not available / different schema; declared, not fatal

    # --- build the manifest rows (deterministic order by source_file).
    rows_out: list[dict[str, Any]] = []
    n_dt = n_lang = 0
    for r in lot:
        fp = r["fill_plan"]
        sf = r["source_file"]
        did = mapping[sf]
        doc = doc_index[did]
        dtv = fp["doc_type_value"]
        lang_scalar = fp["language_value"][0] if fp.get("language_fill_singleton") else None
        db_dt = doc.get("doc_type")
        db_lang = doc.get("language")
        if db_dt in (None, ""):
            n_dt += 1
        if lang_scalar is not None and db_lang in (None, ""):
            n_lang += 1
        rows_out.append({
            "source_file": sf,
            "document_id": did,
            "brand": r.get("brand"),
            "doc_type": dtv,                     # always written (doc_type_fill)
            "language": lang_scalar,             # scalar; None => not written (multi/advisory)
            "db_state_at_freeze": {"doc_type": db_dt, "language": db_lang},  # snapshot; live NULL-guard is authority
        })

    manifest_core = {
        "schema": "s282_t2_manifest_v1",
        "authority": "DEVELOPMENT_QA_READ_ONLY_SELECT_ONLY_ZERO_WRITES_ZERO_PAID_MODEL",
        "inherits": "evals/s282_qa_s83_result_v3.json (frozen deterministic cohort)",
        "write_axes": ["doc_type", "language(singleton)"],
        "never_written": ["product_model", "manufacturer", "language(multi/advisory)"],
        "n_rows": len(rows_out),
        "n_doc_type_writes_expected": n_dt,
        "n_language_writes_expected": n_lang,
        "mapping": {
            "method": "source_file -> chunks_v2.document_id (∪ stem, docmap fallback), status=='active'",
            "frozen_1to1_verified": True,
            "v1_active_id_cross_check_mismatches": v1_mismatch,
        },
        "provenance": {
            "commit_head": contract["commit_head"],
            "worktree_dirty": contract["worktree_dirty"],
            "worktree_dirty_note": ("worktree_dirty refleja artefactos FUERA de los insumos del "
                                    "paquete (log/ficheros de la revisión adversarial + salidas de "
                                    "esta lane); los INSUMOS están sellados por sha: records-sha v3 + "
                                    "corpus-sha + s83 model/identity sha)"),
            "generated_utc": contract["generated_utc"],
            "result_v3_records_sha256": records_sha,
            "corpus_fingerprint_sha256": fp_corpus["sha256"],
            "corpus_counts": {"chunks_v2": fp_corpus["chunks_v2"]["count"],
                              "documents": fp_corpus["documents"]["count"]},
            "s83_models_sha256_lf": contract["s83_models"]["sha256_lf"],
            "s83_identity_sha256_lf": contract["s83_identity"]["sha256_lf"],
            "catalog_doc_map_sha256_lf": contract["catalog_doc_map"]["sha256_lf"],
        },
        "rows": rows_out,
    }
    # Deterministic content-sha: hash the manifest EXCLUDING the volatile generated_utc
    # (and the self-referential sha) so a re-run over the frozen cohort reproduces it exactly.
    hashable = json.loads(json.dumps(manifest_core))
    hashable["provenance"].pop("generated_utc", None)
    manifest_content_sha = inst._stable_sha256(hashable)
    manifest = {**manifest_core, "manifest_content_sha256": manifest_content_sha}

    with io.open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    # --- emit the SQL package (LF newlines so the reported sha matches the file bytes).
    sql = build_sql(rows_out, manifest, n_dt, n_lang)
    SQL_OUT.write_text(sql, encoding="utf-8", newline="\n")
    sql_sha = _sha256_text(sql)

    print(f"lot_rows={len(rows_out)} doc_type_writes={n_dt} language_writes={n_lang}")
    print(f"mapping 1:1 OK (v1 cross-check mismatches={v1_mismatch})")
    print(f"records_sha={records_sha[:16]} corpus_sha={fp_corpus['sha256'][:16]} "
          f"commit={contract['commit_head'][:10]} dirty={contract['worktree_dirty']}")
    print(f"manifest_content_sha={manifest_content_sha[:16]}")
    print(f"brand_dist={dict(Counter(r['brand'] for r in rows_out))}")
    print(f"manifest: {MANIFEST}")
    print(f"sql: {SQL_OUT} (sha256={sql_sha[:16]})")
    return 0


def build_sql(rows: list[dict[str, Any]], manifest: dict[str, Any], n_dt: int, n_lang: int) -> str:
    prov = manifest["provenance"]
    L: list[str] = []
    A = L.append
    A("-- s282 T2-apply — backfill de identidad s83 sobre `documents` (doc_type + language).")
    A("-- GENERADO por scripts/s282_t2_write_package.py desde evals/s282_t2_manifest_v1.json.")
    A("-- NO APLICADO por esta lane. Aplicar SOLO tras la firma de Alberto (attestation v2).")
    A("--")
    A("-- PROVENANCE (sellada):")
    A(f"--   commit_head            = {prov['commit_head']}")
    A(f"--   result_v3 records-sha  = {prov['result_v3_records_sha256']}")
    A(f"--   corpus fingerprint sha = {prov['corpus_fingerprint_sha256']}")
    A(f"--   manifest content-sha   = {manifest['manifest_content_sha256']}")
    A(f"--   s83 models / identity  = {prov['s83_models_sha256_lf'][:16]} / {prov['s83_identity_sha256_lf'][:16]}")
    A("--")
    A("-- CONTRATO: fill-only NULL-guard, reversible. `product_model`/`manufacturer` JAMÁS se tocan.")
    A(f"-- Recuentos ESPERADOS (frame congelado): {len(rows)} filas UPDATE · "
      f"{n_dt} doc_type set · {n_lang} language set · 0 overwrites.")
    A("-- Dry-run: cambia el COMMIT final por ROLLBACK (todos los guards corren, nada persiste).")
    A("")
    A("BEGIN;")
    A("")
    A("CREATE TEMP TABLE t2_staging (")
    A("  document_id uuid PRIMARY KEY,")
    A("  source_file text NOT NULL,")
    A("  doc_type    text,   -- siempre presente en este lote (todas fill doc_type)")
    A("  language    text    -- NULL salvo los singleton (multi/advisory NO se escribe)")
    A(") ON COMMIT DROP;")
    A("")
    A("INSERT INTO t2_staging (document_id, source_file, doc_type, language) VALUES")
    vals = []
    for r in rows:
        did = inst._sql_lit(r["document_id"])
        sf = inst._sql_lit(r["source_file"])
        dt = inst._sql_lit(r["doc_type"]) if r["doc_type"] is not None else "NULL"
        lg = inst._sql_lit(r["language"]) if r["language"] is not None else "NULL"
        vals.append(f"  ({did}, {sf}, {dt}, {lg})")
    A(",\n".join(vals) + ";")
    A("")
    A("-- Guard 1: la staging debe tener el nº de filas esperado.")
    A("DO $$ BEGIN")
    A(f"  IF (SELECT count(*) FROM t2_staging) <> {len(rows)} THEN")
    A(f"    RAISE EXCEPTION 'staging count % <> {len(rows)}', (SELECT count(*) FROM t2_staging);")
    A("  END IF;")
    A("END $$;")
    A("")
    A("-- Guard 2: todo document_id existe y está 'active' (aún sin escribir).")
    A("DO $$ DECLARE n_missing int; n_inactive int; BEGIN")
    A("  SELECT count(*) INTO n_missing FROM t2_staging s")
    A("    LEFT JOIN documents d ON d.id = s.document_id WHERE d.id IS NULL;")
    A("  SELECT count(*) INTO n_inactive FROM t2_staging s")
    A("    JOIN documents d ON d.id = s.document_id WHERE d.status <> 'active';")
    A("  IF n_missing  <> 0 THEN RAISE EXCEPTION '% document_id inexistentes', n_missing; END IF;")
    A("  IF n_inactive <> 0 THEN RAISE EXCEPTION '% document_id no active', n_inactive; END IF;")
    A("END $$;")
    A("")
    A("-- Captura del before-image + UPDATE fill-only en una sola sentencia atómica.")
    A("CREATE TEMP TABLE t2_apply_audit (")
    A("  document_id uuid, source_file text,")
    A("  old_doc_type text, new_doc_type text,")
    A("  old_language text, new_language text")
    A(") ON COMMIT DROP;")
    A("")
    A("WITH before AS (")
    A("  SELECT d.id, d.doc_type AS old_doc_type, d.language AS old_language")
    A("  FROM documents d JOIN t2_staging s ON d.id = s.document_id")
    A("  WHERE d.doc_type IS NULL OR d.language IS NULL")
    A("),")
    A("upd AS (")
    A("  UPDATE documents d SET")
    A("    doc_type = COALESCE(d.doc_type, s.doc_type),   -- fill-only; nunca overwrite")
    A("    language = COALESCE(d.language, s.language)     -- SOLO singleton; multi = NULL en staging")
    A("  FROM t2_staging s")
    A("  WHERE d.id = s.document_id")
    A("    AND (d.doc_type IS NULL OR d.language IS NULL)")
    A("  RETURNING d.id, s.source_file, d.doc_type AS new_doc_type, d.language AS new_language")
    A(")")
    A("INSERT INTO t2_apply_audit (document_id, source_file, old_doc_type, new_doc_type, old_language, new_language)")
    A("SELECT u.id, u.source_file, b.old_doc_type, u.new_doc_type, b.old_language, u.new_language")
    A("FROM upd u JOIN before b ON b.id = u.id;")
    A("")
    A("-- Verificación post-apply (aborta la transacción si algo no cuadra).")
    A("DO $$ DECLARE n_upd int; n_dt int; n_lang int; n_overwrite int; BEGIN")
    A("  SELECT count(*) INTO n_upd  FROM t2_apply_audit;")
    A("  SELECT count(*) INTO n_dt   FROM t2_apply_audit WHERE old_doc_type IS NULL AND new_doc_type IS NOT NULL;")
    A("  SELECT count(*) INTO n_lang FROM t2_apply_audit WHERE old_language IS NULL AND new_language IS NOT NULL;")
    A("  SELECT count(*) INTO n_overwrite FROM t2_apply_audit")
    A("    WHERE (old_doc_type IS NOT NULL AND old_doc_type IS DISTINCT FROM new_doc_type)")
    A("       OR (old_language IS NOT NULL AND old_language IS DISTINCT FROM new_language);")
    A("  RAISE NOTICE 'T2-apply: updated=% doc_type_set=% language_set=% overwrites=%',")
    A("               n_upd, n_dt, n_lang, n_overwrite;")
    A(f"  IF n_upd       <> {len(rows)} THEN RAISE EXCEPTION 'updated % <> {len(rows)}', n_upd; END IF;")
    A(f"  IF n_dt        <> {n_dt} THEN RAISE EXCEPTION 'doc_type_set % <> {n_dt}', n_dt; END IF;")
    A(f"  IF n_lang      <> {n_lang} THEN RAISE EXCEPTION 'language_set % <> {n_lang}', n_lang; END IF;")
    A("  IF n_overwrite <> 0 THEN RAISE EXCEPTION 'overwrite detectado (%): fill-only violado', n_overwrite; END IF;")
    A("END $$;")
    A("")
    A("-- Before-image completa (GUARDAR esta salida para el rollback post-COMMIT):")
    A("SELECT document_id, source_file, old_doc_type, new_doc_type, old_language, new_language")
    A("FROM t2_apply_audit ORDER BY source_file;")
    A("")
    A("-- ROLLBACK generado del before-image (revierte SOLO los ejes que estaban NULL y se rellenaron).")
    A("-- Opción A (misma transacción, antes del COMMIT): descomenta para deshacer in situ.")
    A("--   UPDATE documents d SET doc_type = NULL")
    A("--     FROM t2_apply_audit a WHERE d.id = a.document_id AND a.old_doc_type IS NULL;")
    A("--   UPDATE documents d SET language = NULL")
    A("--     FROM t2_apply_audit a WHERE d.id = a.document_id AND a.old_language IS NULL;")
    A("-- Opción B (post-COMMIT): recrea t2_apply_audit desde la salida GUARDADA del SELECT de arriba,")
    A("--   y ejecuta las dos sentencias UPDATE ... FROM t2_apply_audit de la Opción A.")
    A("")
    A("COMMIT;   -- <-- Alberto: cambiar a ROLLBACK para dry-run (verifica sin persistir).")
    A("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
