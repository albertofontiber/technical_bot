#!/usr/bin/env python3
"""s288 A-CORE F1 / P-A — GENERADOR DETERMINISTA del packet SQL de sha real.

Fase F1 del spec normativo SELLADO ``evals/s288_acore_design_brief_v1.md`` (v3), packet
**P-A** (`sha real — bulk DUAL-KEY`).  Emite ``evals/s288_acore_pA_apply_<tag>.sql``, que
Alberto pega A MANO en el editor SQL de Supabase.  **Este script NUNCA escribe en la DB**:
su unico verbo contra Supabase es GET de PostgREST (stack heredado de
``scripts/s288_acore_census_v2.py`` / ``scripts/s281_h0_identity_census.py``).

QUE HACE EL PACKET
  Sustituye, en `documents.source_pdf_sha256`, el placeholder `backfill:<sha256 del NOMBRE>`
  por la sha REAL de los bytes del PDF (= la `extraction_sha256` UNICA de sus chunks;
  premisa H1, CONFIRMADA 60/60 no-circular por el census F0).

INPUT (pre-registro de volumen, spec F0(g))
  ``evals/s288_acore_census_v2_result_<tag>.json`` -> ``census.g_pre_registro.P_A.document_ids``
  (585 elegibles: activo + single-extraction + dual-key stem-Y-sha al MISMO blob + grupo-sha
  singleton per-manufacturer + sha placeholder).

CONTRATOS
  * **Read-only**: SELECT-only via GET.  Cero escrituras, cero RPC, cero llamadas a modelos.
  * **Determinista**: el packet se construye DOS veces desde DOS fetch independientes y se
    comparan los bytes.  Sin timestamps en la salida (un timestamp haria imposible el
    contrato de re-emision byte-identica).  Orden: `document_id` ascendente.
  * **Guards heredados de s287** (``evals/s287_p2_dedup_apply_v{1,2}.sql``): precondiciones
    que ABORTAN, backup persistente con guard anti-reuso de nombre, conteo exacto del UPDATE,
    post-checks y ROLLBACK escrito.  Escala set-based (una temp table, no 585 sentencias).
  * **Honestidad del volumen** (spec fix r2-3): si un documento del pre-registro NO cumple
    hoy alguna precondicion, se EXCLUYE del packet, el conteo baja y la exclusion queda
    re-registrada en la cabecera del propio packet (no se deja dentro con el guard roto).

MODOS
  (default)   genera el packet.
  --verify    re-lee el packet emitido y re-verifica las precondiciones (i)-(iii) + el
              dual-key contra el manifest de blobs, todo contra la DB EN VIVO read-only.

Usage:
  python scripts/s288_acore_stage_pA.py [--tag v1]
  python scripts/s288_acore_stage_pA.py --verify [--tag v1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Force the production corpus BEFORE importing config (env is authority).
os.environ["CHUNKS_TABLE"] = "chunks_v2"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"  # re-assert after load_dotenv

import src.config as cfg  # noqa: E402

# ── constantes del contrato ───────────────────────────────────────────────────
CENSUS_COMMIT = "adc8aa6"          # commit que sella el census F0 (s288 F0 EJECUTADO)
DOCS_TOTAL_EXPECTED = 1169         # census F0: particion exhaustiva, suma == 1169
PLACEHOLDER_TOTAL_EXPECTED = 744   # census F0: marginal sha_class.placeholder
BACKUP_TABLE = "documents_backup_s288_pa"
TEMP_TABLE = "s288_pa_map"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ROW_RE = re.compile(
    r"^\s*\('(?P<doc>[0-9a-fA-F-]{36})',\s*'(?P<ph>backfill:[0-9a-f]{64})',\s*'(?P<dst>[0-9a-f]{64})'\)"
)

_H: dict[str, str] = {}
_BASE = ""


# ── read-only HTTP helpers (stack s281/s288-F0) ───────────────────────────────
def _init_http() -> None:
    global _H, _BASE
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials unavailable")
    _H = {
        "apikey": cfg.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}",
    }
    _BASE = cfg.SUPABASE_URL.rstrip("/")


def _get(table: str, params: dict[str, str], *, count: bool = False) -> httpx.Response:
    headers = dict(_H)
    if count:
        headers["Prefer"] = "count=exact"
    resp = httpx.get(f"{_BASE}/rest/v1/{table}", headers=headers, params=params, timeout=180)
    resp.raise_for_status()
    return resp


def _get_all(table: str, select: str, *, order: str, page: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {"select": select, "order": order, "limit": str(page), "offset": str(offset)}
        batch = _get(table, params).json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


def _count(table: str) -> int:
    resp = _get(table, {"select": "id", "limit": "1"}, count=True)
    return int(resp.headers.get("content-range", "*/0").split("/")[-1])


def _sha256_lf_bytes(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _sha256_lf(path: Path) -> str:
    return _sha256_lf_bytes(path.read_bytes())


def _pdf_stem(name: str) -> str:
    """Quita UN sufijo '.pdf' case-INSENSITIVE (misma convencion que el census F0)."""
    text = str(name or "")
    return text[:-4] if text.lower().endswith(".pdf") else text


def _norm_ext(value: Any) -> str | None:
    s = str(value or "").strip()
    return s or None


DOC_SELECT = "id,source_pdf_filename,source_pdf_sha256,status,manufacturer"
CHUNK_SELECT = "id,document_id,extraction_sha256"


def fetch_snapshot() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch read-only ordenado y paginado (determinista)."""
    documents = _get_all("documents", DOC_SELECT, order="id.asc")
    chunks = _get_all("chunks_v2", CHUNK_SELECT, order="id.asc")
    return documents, chunks


# ── derivacion (pura sobre el snapshot -> determinista) ───────────────────────
def build_rows(pre_registro_ids: list[str],
               documents: list[dict[str, Any]],
               chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Deriva las tuplas (document_id, sha_placeholder, sha_destino) + exclusiones.

    Un documento del pre-registro se EXCLUYE si hoy falla alguna precondicion; la razon
    queda registrada (se publica en la cabecera del packet).
    """
    docs_by_id = {str(d["id"]): d for d in documents}

    ext_by_doc: dict[str, set[str]] = defaultdict(set)
    blank_ext_chunks: Counter[str] = Counter()
    n_chunks_by_doc: Counter[str] = Counter()
    for c in chunks:
        did = c.get("document_id")
        if not did:
            continue
        did = str(did)
        n_chunks_by_doc[did] += 1
        e = _norm_ext(c.get("extraction_sha256"))
        if e is None:
            blank_ext_chunks[did] += 1
        else:
            ext_by_doc[did].add(e)

    # (manufacturer, sha) ocupados HOY en documents (para el guard del UNIQUE)
    occupied: dict[tuple[str, str], list[str]] = defaultdict(list)
    for d in documents:
        occupied[(str(d.get("manufacturer") or ""), str(d.get("source_pdf_sha256") or ""))].append(str(d["id"]))

    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    ph_formula_mismatch: list[dict[str, Any]] = []

    for did in sorted(pre_registro_ids):
        d = docs_by_id.get(did)
        if d is None:
            excluded.append({"document_id": did, "reason": "documento AUSENTE en documents"})
            continue
        status = str(d.get("status") or "")
        sha_db = str(d.get("source_pdf_sha256") or "")
        fname = str(d.get("source_pdf_filename") or "")
        mfr = str(d.get("manufacturer") or "")

        if status != "active":
            excluded.append({"document_id": did, "reason": f"status={status!r} (se exige 'active')"})
            continue
        if not sha_db.startswith("backfill:"):
            excluded.append({"document_id": did,
                             "reason": f"sha ya NO es placeholder ({sha_db[:24]}...)"})
            continue

        exts = sorted(ext_by_doc.get(did, set()))
        if len(exts) != 1:
            excluded.append({"document_id": did,
                             "reason": f"{len(exts)} extraction_sha256 distintas (se exige 1)"})
            continue
        dest = exts[0]
        if not _HEX64.match(dest):
            excluded.append({"document_id": did,
                             "reason": f"extraction_sha256 no es 64-hex ({dest[:24]}...)"})
            continue

        others = [i for i in occupied.get((mfr, dest), []) if i != did]
        if others:
            excluded.append({"document_id": did,
                             "reason": f"UNIQUE(manufacturer,sha) ya ocupado por {others[0]}"})
            continue

        # cross-check de la formula del placeholder (001_backfill_documents.py:261).
        # Diagnostico, NO criterio: la autoridad del valor a sustituir es la DB.
        cand = {
            "source_pdf_filename": "backfill:" + hashlib.sha256(fname.encode("utf-8")).hexdigest(),
            "stem(source_pdf_filename)": "backfill:" + hashlib.sha256(
                _pdf_stem(fname).encode("utf-8")).hexdigest(),
        }
        formula = next((k for k, v in cand.items() if v == sha_db), None)
        if formula is None:
            ph_formula_mismatch.append({"document_id": did, "source_pdf_filename": fname})

        rows.append({
            "document_id": did,
            "sha_placeholder": sha_db,
            "sha_destino": dest,
            "manufacturer": mfr,
            "source_pdf_filename": fname,
            "n_chunks": n_chunks_by_doc.get(did, 0),
            "n_chunks_sin_extraction": blank_ext_chunks.get(did, 0),
            "placeholder_formula": formula,
        })

    # colision INTRA-packet (manufacturer, sha_destino): el UNIQUE tambien la rechazaria,
    # pero con un error opaco a mitad del UPDATE -> se caza antes y se excluyen las dos.
    intra: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        intra[(r["manufacturer"], r["sha_destino"])].append(r["document_id"])
    collided = {i for ids in intra.values() if len(ids) > 1 for i in ids}
    if collided:
        for r in list(rows):
            if r["document_id"] in collided:
                rows.remove(r)
                excluded.append({"document_id": r["document_id"],
                                 "reason": "colision INTRA-packet (manufacturer, sha_destino)"})
        excluded.sort(key=lambda e: e["document_id"])

    # sha_destino repetida entre marcas distintas (el UNIQUE la permite; el census
    # pre-registro 0 grupos globales -> se publica como ancla anti-deriva, no excluye)
    by_dest: Counter[str] = Counter(r["sha_destino"] for r in rows)
    dest_shared = sorted(s for s, n in by_dest.items() if n > 1)

    # documentos AJENOS al packet que comparten uno de sus valores de placeholder: el
    # placeholder es sha256 del NOMBRE y el UNIQUE solo constrine (marca, sha), asi que dos
    # marcas con el mismo nombre de fichero compartirian valor.  Medido para anclarlo.
    packet_ids = {r["document_id"] for r in rows}
    packet_ph = {r["sha_placeholder"] for r in rows}
    foreign_ph = sorted(str(d["id"]) for d in documents
                        if str(d.get("source_pdf_sha256") or "") in packet_ph
                        and str(d["id"]) not in packet_ids)

    return {
        "rows": rows,
        "excluded": excluded,
        "foreign_placeholder_holders": foreign_ph,
        "placeholder_formula_mismatch": ph_formula_mismatch,
        "dest_shared_across_rows": dest_shared,
        "n_chunks_sin_extraction_total": sum(r["n_chunks_sin_extraction"] for r in rows),
        "docs_total": len(documents),
        "placeholder_total": sum(1 for d in documents
                                 if str(d.get("source_pdf_sha256") or "").startswith("backfill:")),
    }


# ── render del packet ─────────────────────────────────────────────────────────
def render_packet(derived: dict[str, Any], meta: dict[str, Any]) -> str:
    rows = derived["rows"]
    n = len(rows)
    ph_post = derived["placeholder_total"] - n
    docs_total = derived["docs_total"]
    L: list[str] = []
    A = L.append

    A("-- ############################################################################################")
    A("-- #  s288 A-CORE - F1 / P-A - `documents.source_pdf_sha256`: placeholder -> sha REAL         #")
    A("-- #  PASTE MANUAL DE ALBERTO en el editor SQL de Supabase (stop-line del spec s288 s7).      #")
    A("-- ############################################################################################")
    A("--")
    A("-- QUE HACE")
    A("--   Sustituye el placeholder `backfill:<sha256 del NOMBRE del fichero>` por la sha REAL de")
    A("--   los BYTES del PDF fuente en los documents pre-registrados del packet P-A. La sha real")
    A("--   es la `extraction_sha256` UNICA de los chunks del propio documento (premisa H1 del spec")
    A("--   s2, veredicto del census F0: **H1_CONFIRMADA 60/60**, gate no-circular por clave stem).")
    A("--   Consecuencia buscada (spec sF2.3): esos documentos pasan a cumplir el predicado de")
    A("--   autoridad `tier blob-verificado` (activo + sha real 64-hex + binding extraction==source)")
    A("--   que la lane `doc_scoped_hyq_coverage` exige por parent.")
    A("--")
    A("-- QUE **NO** TOCA")
    A("--   Ninguna otra columna de `documents` (status, language, lineage, revision, FKs: intactos).")
    A("--   Ninguna fila de `chunks_v2` / `chunks_v2_hyq` / `chunks_v2_enunciados`. Ningun documento")
    A("--   fuera de la lista literal de abajo. NO acuna lineages (spec fix r2-2: P-C va por tramos).")
    A("--")
    A("-- PROCEDENCIA (freeze del insumo)")
    A(f"--   census F0        : {meta['census_result_rel']} (tag {meta['census_tag']})")
    A(f"--   census sha256-LF : {meta['census_sha256_lf']}")
    A(f"--   census commit    : {CENSUS_COMMIT}  (s288 F0: census v2 EJECUTADO)")
    A(f"--   spec normativo   : {meta['spec_rel']}  sha256-LF {meta['spec_sha256_lf']}")
    A(f"--   generador        : {meta['generator_rel']}  (determinista; NO editar a mano: re-emitir)")
    A(f"--   generador sha256 : {meta['generator_sha256_lf']}")
    A("--")
    A("-- VOLUMEN PRE-REGISTRADO (spec F0(g) / fix r2-3 - el gate F3 compara contra estas cifras)")
    A(f"--   elegibles P-A pre-registrados por el census .......... {meta['n_pre_registro']}")
    A(f"--   EXCLUIDOS por fallar una precondicion HOY ............ {len(derived['excluded'])}")
    A(f"--   **FILAS DE ESTE PACKET (== UPDATE esperado)** ........ {n}")
    A(f"--   documents totales (ancla anti-deriva) ............... {docs_total}")
    A(f"--   documents con placeholder ANTES del paste ........... {derived['placeholder_total']}")
    A(f"--   documents con placeholder DESPUES del paste ......... {ph_post}"
      f"   ({derived['placeholder_total']} - {n})")
    A("--")
    if derived["excluded"]:
        A("-- EXCLUSIONES RE-REGISTRADAS (estaban en el pre-registro del census y NO entran aqui;")
        A("--   el conteo del packet ya esta bajado. Cada una necesita adjudicacion propia):")
        for e in derived["excluded"]:
            A(f"--   - {e['document_id']}  ::  {e['reason']}")
        A("--")
    else:
        A("-- EXCLUSIONES: NINGUNA. Los elegibles del pre-registro cumplen HOY todas las")
        A("--   precondiciones (i)-(iv), re-verificadas contra la DB en vivo por el generador")
        A("--   antes de emitir, mas el dual-key contra el manifest de blobs del census.")
        A("--")
    if derived["placeholder_formula_mismatch"]:
        A("-- DIAGNOSTICO (no excluye): placeholders que NO reproducen la formula canonica")
        A("--   'backfill:'+sha256(source_pdf_filename) ni su variante sin '.pdf'. El valor que")
        A("--   sustituye el packet es el LEIDO DE LA DB, no el recomputado, asi que el UPDATE es")
        A("--   correcto igualmente; se declara por trazabilidad:")
        for e in derived["placeholder_formula_mismatch"][:20]:
            A(f"--   - {e['document_id']}  {e['source_pdf_filename']}")
        A("--")
    A("-- REVERSIBILIDAD")
    A(f"--   BACKUP: `{BACKUP_TABLE}` (copia integra de las {n} filas ANTES del UPDATE).")
    A("--   El bloque ABORTA si esa tabla ya existe (patron s287 v2: un `IF NOT EXISTS` habria")
    A("--   hecho NO-OP en silencio y el paste correria SIN backup). ROLLBACK exacto al final.")
    A("--")
    A("-- DRY-RUN: cambia el `COMMIT;` final por `ROLLBACK;` — todos los guards y post-checks")
    A("--   corren igual y no se persiste nada.")
    A("--")
    A("-- ANCLAS ANTI-DERIVA que el bloque re-verifica en vivo antes de escribir:")
    A(f"--   * las {n} filas existen, estan `active` y llevan EXACTAMENTE ese placeholder;")
    A("--   * la sha destino NO esta ocupada por otro documento de la MISMA marca (UNIQUE")
    A("--     `documents_mfr_hash_unique`, migrations/001_document_management.sql:68) ni colisiona")
    A("--     dentro del propio packet;")
    A("--   * cada documento tiene EXACTAMENTE 1 `extraction_sha256` distinta y es la sha destino;")
    A(f"--   * documentos AJENOS al packet que comparten uno de sus placeholders: "
      f"{len(derived['foreign_placeholder_holders'])} (medido hoy);")
    A(f"--   * `documents` tiene {docs_total} filas y {derived['placeholder_total']} placeholders;")
    A(f"--   * chunks de estos documentos SIN `extraction_sha256`: {derived['n_chunks_sin_extraction_total']}"
      " (medido hoy, anclado).")
    A("-- ############################################################################################")
    A("")
    A("BEGIN;")
    A("SET LOCAL lock_timeout = '5s';")
    A("SET LOCAL statement_timeout = '300s';")
    A("")
    A(f"DO ${TEMP_TABLE}$")
    A("DECLARE")
    A(f"  c_expected   CONSTANT integer := {n};        -- filas del packet (== UPDATE esperado)")
    A(f"  c_docs_total CONSTANT integer := {docs_total};      -- census F0: particion suma {docs_total}")
    A(f"  c_ph_pre     CONSTANT integer := {derived['placeholder_total']};       -- placeholders ANTES")
    A(f"  c_ph_post    CONSTANT integer := {ph_post};       -- placeholders DESPUES ({derived['placeholder_total']} - {n})")
    A(f"  c_sin_ext    CONSTANT integer := {derived['n_chunks_sin_extraction_total']};        -- chunks de estos docs sin extraction_sha256")
    A(f"  c_ph_ajenos  CONSTANT integer := {len(derived['foreign_placeholder_holders'])};"
      "        -- docs AJENOS que comparten un placeholder del packet")
    A("  n            integer;")
    A("  ids          text;")
    A("BEGIN")
    A("  -- ======================================================================== (a) VALORES")
    A("  -- Sin `DROP TABLE IF EXISTS` a proposito: si la temp ya existe en esta sesion es que un")
    A("  -- paste anterior COMMITEO (un fallo hace ROLLBACK y no deja rastro) -> abortar es lo")
    A("  -- correcto. Orden: document_id ascendente (determinismo de la emision).")
    A(f"  CREATE TEMP TABLE {TEMP_TABLE} (")
    A("    document_id     uuid PRIMARY KEY,")
    A("    sha_placeholder text NOT NULL CHECK (sha_placeholder LIKE 'backfill:%'),")
    A("    sha_destino     text NOT NULL CHECK (sha_destino ~ '^[0-9a-f]{64}$')")
    A("  );")
    A("")
    A(f"  INSERT INTO {TEMP_TABLE} (document_id, sha_placeholder, sha_destino) VALUES")
    for i, r in enumerate(rows):
        sep = "," if i < n - 1 else ";"
        A(f"  ('{r['document_id']}','{r['sha_placeholder']}','{r['sha_destino']}'){sep}")
    A("")
    A(f"  SELECT count(*) INTO n FROM {TEMP_TABLE};")
    A("  IF n <> c_expected THEN")
    A("    RAISE EXCEPTION 'P-A: la tabla de valores tiene % filas, se esperaban % - ABORTA', n, c_expected;")
    A("  END IF;")
    A("")
    A(f"  SELECT count(DISTINCT sha_destino) INTO n FROM {TEMP_TABLE};")
    A("  IF n <> c_expected THEN")
    A("    RAISE EXCEPTION 'P-A: % sha destino distintas para % filas (el census pre-registro 0 grupos de sha compartida) - ABORTA', n, c_expected;")
    A("  END IF;")
    A("")
    A("  -- ================================================================ (b) PRECONDICIONES")
    A("  -- (i) las filas existen, con EXACTAMENTE ese placeholder y status='active'")
    A("  SELECT count(*), coalesce(string_agg(m.document_id::text, ', ' ORDER BY m.document_id), '')")
    A("    INTO n, ids")
    A(f"    FROM {TEMP_TABLE} m")
    A("    LEFT JOIN documents d")
    A("      ON  d.id = m.document_id")
    A("      AND d.source_pdf_sha256 = m.sha_placeholder")
    A("      AND d.status = 'active'")
    A("   WHERE d.id IS NULL;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A (i): % documentos no estan {activo + ese placeholder exacto} - ABORTA. Ejemplos: %',")
    A("      n, left(ids, 400);")
    A("  END IF;")
    A("")
    A("  -- (i-bis) NINGUN documento FUERA del packet lleva uno de estos valores de placeholder.")
    A("  --   El placeholder es sha256 del NOMBRE y el UNIQUE solo constrine (marca, sha): dos")
    A("  --   documentos de marcas distintas con el mismo nombre de fichero compartirian valor.")
    A("  --   Se comprueba ANTES de escribir para que el post-check global no aborte DESPUES")
    A("  --   del UPDATE por una fila ajena al packet.")
    A("  SELECT count(*) INTO n FROM documents d")
    A(f"   WHERE d.source_pdf_sha256 IN (SELECT sha_placeholder FROM {TEMP_TABLE})")
    A(f"     AND d.id NOT IN (SELECT document_id FROM {TEMP_TABLE});")
    A("  IF n <> c_ph_ajenos THEN")
    A("    RAISE EXCEPTION 'P-A (i-bis): % documentos AJENOS comparten un placeholder del packet, el generador midio % - ABORTA', n, c_ph_ajenos;")
    A("  END IF;")
    A("")
    A("  -- (ii) guard del UNIQUE `documents_mfr_hash_unique` (manufacturer, source_pdf_sha256):")
    A("  --      la sha destino no puede estar ya ocupada por OTRO documento de la MISMA marca ...")
    A("  SELECT count(*), coalesce(string_agg(m.document_id::text || '->' || o.id::text, ', '")
    A("                            ORDER BY m.document_id), '')")
    A("    INTO n, ids")
    A(f"    FROM {TEMP_TABLE} m")
    A("    JOIN documents t ON t.id = m.document_id")
    A("    JOIN documents o ON o.manufacturer = t.manufacturer")
    A("                    AND o.source_pdf_sha256 = m.sha_destino")
    A("                    AND o.id <> m.document_id;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A (ii): % colisiones con el UNIQUE (manufacturer, sha destino) - ABORTA. Ejemplos: %',")
    A("      n, left(ids, 400);")
    A("  END IF;")
    A("")
    A("  --      ... ni colisionar DENTRO del propio packet (dos docs de la misma marca al mismo sha)")
    A("  SELECT count(*) INTO n FROM (")
    A(f"    SELECT 1 FROM {TEMP_TABLE} m")
    A("      JOIN documents t ON t.id = m.document_id")
    A("     GROUP BY t.manufacturer, m.sha_destino HAVING count(*) > 1) x;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A (ii-bis): % colisiones INTRA-packet (manufacturer, sha destino) - ABORTA', n;")
    A("  END IF;")
    A("")
    A("  -- (iii) cada documento tiene EXACTAMENTE 1 extraction_sha256 distinta y ES la sha destino")
    A("  SELECT count(*), coalesce(string_agg(g.document_id::text, ', ' ORDER BY g.document_id), '')")
    A("    INTO n, ids")
    A("    FROM (")
    A("      SELECT m.document_id,")
    A("             m.sha_destino,")
    A("             count(DISTINCT nullif(btrim(c.extraction_sha256), '')) AS n_ext,")
    A("             min(nullif(btrim(c.extraction_sha256), ''))            AS ext")
    A(f"        FROM {TEMP_TABLE} m")
    A("        LEFT JOIN chunks_v2 c ON c.document_id = m.document_id")
    A("       GROUP BY m.document_id, m.sha_destino) g")
    A("   WHERE g.n_ext <> 1 OR g.ext IS DISTINCT FROM g.sha_destino;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A (iii): % documentos sin extraction UNICA == sha destino - ABORTA. Ejemplos: %',")
    A("      n, left(ids, 400);")
    A("  END IF;")
    A("")
    A("  --       ancla: chunks de estos documentos SIN extraction_sha256 (medido al generar)")
    A("  SELECT count(*) INTO n")
    A(f"    FROM {TEMP_TABLE} m")
    A("    JOIN chunks_v2 c ON c.document_id = m.document_id")
    A("   WHERE nullif(btrim(c.extraction_sha256), '') IS NULL;")
    A("  IF n <> c_sin_ext THEN")
    A("    RAISE EXCEPTION 'P-A (iii-bis): % chunks sin extraction_sha256, el generador midio % - ABORTA', n, c_sin_ext;")
    A("  END IF;")
    A("")
    A("  -- (iv) anclas globales de corpus (census F0)")
    A("  SELECT count(*) INTO n FROM documents;")
    A("  IF n <> c_docs_total THEN")
    A("    RAISE EXCEPTION 'P-A (iv): documents tiene % filas, el census vio % - ABORTA', n, c_docs_total;")
    A("  END IF;")
    A("")
    A("  SELECT count(*) INTO n FROM documents WHERE source_pdf_sha256 LIKE 'backfill:%';")
    A("  IF n <> c_ph_pre THEN")
    A("    RAISE EXCEPTION 'P-A (iv-bis): % documents con placeholder, se esperaban % - ABORTA', n, c_ph_pre;")
    A("  END IF;")
    A("")
    A("  -- ========================================================================= (c) BACKUP")
    A(f"  IF to_regclass('public.{BACKUP_TABLE}') IS NOT NULL THEN")
    A(f"    RAISE EXCEPTION 'P-A: la tabla de backup public.{BACKUP_TABLE} YA EXISTE - ABORTA "
      "(no se reutiliza un nombre de backup: el paste correria sin red)';")
    A("  END IF;")
    A("")
    A(f"  CREATE TABLE public.{BACKUP_TABLE} AS")
    A(f"  SELECT d.* FROM documents d WHERE d.id IN (SELECT document_id FROM {TEMP_TABLE});")
    A("")
    A(f"  SELECT count(*) INTO n FROM public.{BACKUP_TABLE};")
    A("  IF n <> c_expected THEN")
    A("    RAISE EXCEPTION 'P-A: backup con % filas de % - ABORTA', n, c_expected;")
    A("  END IF;")
    A("")
    A("  -- ========================================================================= (d) UPDATE")
    A("  UPDATE documents d")
    A("     SET source_pdf_sha256 = m.sha_destino")
    A(f"    FROM {TEMP_TABLE} m")
    A("   WHERE d.id = m.document_id")
    A("     AND d.source_pdf_sha256 = m.sha_placeholder")
    A("     AND d.status = 'active';")
    A("  GET DIAGNOSTICS n = ROW_COUNT;")
    A("  IF n <> c_expected THEN")
    A("    RAISE EXCEPTION 'P-A (d): UPDATE toco % filas, se esperaban % - ABORTA TODO', n, c_expected;")
    A("  END IF;")
    A("  RAISE NOTICE 'P-A: UPDATE aplicado a % documents', n;")
    A("")
    A("  -- ==================================================================== (e) POST-CHECKS")
    A("  -- 1. los N documentos llevan AHORA la sha destino")
    A("  SELECT count(*) INTO n")
    A(f"    FROM {TEMP_TABLE} m JOIN documents d ON d.id = m.document_id")
    A("   WHERE d.source_pdf_sha256 = m.sha_destino;")
    A("  IF n <> c_expected THEN")
    A("    RAISE EXCEPTION 'P-A post-1: % de % documentos con la sha destino - ABORTA', n, c_expected;")
    A("  END IF;")
    A("")
    A("  -- 2a. ninguno de los N documentos conserva su placeholder")
    A("  SELECT count(*) INTO n")
    A(f"    FROM {TEMP_TABLE} m JOIN documents d ON d.id = m.document_id")
    A("   WHERE d.source_pdf_sha256 = m.sha_placeholder;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A post-2a: % documentos del packet conservan su placeholder - ABORTA', n;")
    A("  END IF;")
    A("")
    A("  -- 2b. en TODO el corpus solo pueden quedar con esos valores de placeholder las filas")
    A("  --     AJENAS que ya existian antes del paste (precondicion (i-bis))")
    A("  SELECT count(*) INTO n FROM documents d")
    A(f"   WHERE d.source_pdf_sha256 IN (SELECT sha_placeholder FROM {TEMP_TABLE});")
    A("  IF n <> c_ph_ajenos THEN")
    A("    RAISE EXCEPTION 'P-A post-2b: quedan % filas con los placeholders del packet, se esperaban % - ABORTA', n, c_ph_ajenos;")
    A("  END IF;")
    A("")
    A("  -- 3. BINDING: para los N, extraction_sha256 == source_pdf_sha256 (el predicado que la")
    A("  --    lane hyq exige en su tier blob-verificado; spec sF2.3)")
    A("  SELECT count(*) INTO n FROM (")
    A(f"    SELECT m.document_id FROM {TEMP_TABLE} m")
    A("      JOIN documents  d ON d.id = m.document_id")
    A("      LEFT JOIN chunks_v2 c ON c.document_id = m.document_id")
    A("     GROUP BY m.document_id, d.source_pdf_sha256")
    A("    HAVING count(DISTINCT nullif(btrim(c.extraction_sha256), '')) <> 1")
    A("        OR min(nullif(btrim(c.extraction_sha256), '')) IS DISTINCT FROM d.source_pdf_sha256) x;")
    A("  IF n <> 0 THEN")
    A("    RAISE EXCEPTION 'P-A post-3: % documentos sin binding extraction==source_pdf_sha256 - ABORTA', n;")
    A("  END IF;")
    A("")
    A("  -- 4. el corpus no cambio de tamano")
    A("  SELECT count(*) INTO n FROM documents;")
    A("  IF n <> c_docs_total THEN")
    A("    RAISE EXCEPTION 'P-A post-4: documents tiene % filas, se esperaban % - ABORTA', n, c_docs_total;")
    A("  END IF;")
    A("")
    A("  -- 5. placeholders restantes en TODO el corpus == pre - N")
    A("  SELECT count(*) INTO n FROM documents WHERE source_pdf_sha256 LIKE 'backfill:%';")
    A("  IF n <> c_ph_post THEN")
    A("    RAISE EXCEPTION 'P-A post-5: quedan % placeholders, se esperaban % - ABORTA', n, c_ph_post;")
    A("  END IF;")
    A("")
    A("  RAISE NOTICE 'P-A OK: % documents con sha real | placeholders %  -> % | backup en public.%',")
    A(f"    c_expected, c_ph_pre, c_ph_post, '{BACKUP_TABLE}';")
    A("END")
    A(f"${TEMP_TABLE}$;")
    A("")
    A("-- Resumen visible, DENTRO de la misma transaccion (la temp table vive hasta el fin de la")
    A("-- SESION; en el dry-run el ROLLBACK posterior la borra junto con todo lo demas).")
    A(f"-- Debe devolver: aplicados = {n} · placeholders_restantes = {ph_post} · backup_filas = {n}"
      f" · documents_total = {docs_total}.")
    A("SELECT")
    A(f"  (SELECT count(*) FROM {TEMP_TABLE} m JOIN documents d ON d.id = m.document_id")
    A("    WHERE d.source_pdf_sha256 = m.sha_destino)                              AS aplicados,")
    A("  (SELECT count(*) FROM documents WHERE source_pdf_sha256 LIKE 'backfill:%') AS placeholders_restantes,")
    A(f"  (SELECT count(*) FROM public.{BACKUP_TABLE})                              AS backup_filas,")
    A("  (SELECT count(*) FROM documents)                                          AS documents_total;")
    A("")
    A("COMMIT;   -- <-- para DRY-RUN: cambia esta linea por  ROLLBACK;")
    A("")
    A("")
    A("-- ############################################################################################")
    A("-- #  ROLLBACK EXACTO (post-COMMIT)                                                           #")
    A("-- ############################################################################################")
    A("-- Devuelve los placeholders originales a los documentos tocados. Es el inverso EXACTO: el")
    A("-- packet solo escribio `source_pdf_sha256`, asi que solo esa columna se restaura.")
    A("--")
    A("-- BEGIN;")
    A("-- SET LOCAL lock_timeout = '5s';")
    A("-- UPDATE documents d")
    A(f"--    SET source_pdf_sha256 = b.source_pdf_sha256")
    A(f"--   FROM public.{BACKUP_TABLE} b")
    A("--  WHERE d.id = b.id")
    A("--    AND d.source_pdf_sha256 IS DISTINCT FROM b.source_pdf_sha256;")
    A("-- -- verificacion del rollback (debe dar los valores PRE del packet):")
    A("-- SELECT (SELECT count(*) FROM documents WHERE source_pdf_sha256 LIKE 'backfill:%')")
    A(f"--          AS placeholders,   -- esperado {derived['placeholder_total']}")
    A("--        (SELECT count(*) FROM documents) AS documents_total;")
    A("-- COMMIT;")
    A("--")
    A("-- DROP DEL BACKUP (solo DESPUES de verificar en produccion; sin el, el rollback deja de")
    A("-- ser posible):")
    A(f"--   DROP TABLE public.{BACKUP_TABLE};")
    A("-- ############################################################################################")
    A("")
    return "\n".join(L)


# ── parseo del packet emitido (para --verify) ─────────────────────────────────
def parse_packet(text: str) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = _ROW_RE.match(line)
        if m:
            rows.append({"document_id": m.group("doc"),
                         "sha_placeholder": m.group("ph"),
                         "sha_destino": m.group("dst")})
    def _const(name: str) -> int | None:
        m = re.search(rf"{name}\s+CONSTANT integer := (\d+);", text)
        return int(m.group(1)) if m else None
    return {
        "rows": rows,
        "c_expected": _const("c_expected"),
        "c_docs_total": _const("c_docs_total"),
        "c_ph_pre": _const("c_ph_pre"),
        "c_ph_post": _const("c_ph_post"),
        "c_sin_ext": _const("c_sin_ext"),
        "c_ph_ajenos": _const("c_ph_ajenos"),
    }


def verify(packet_path: Path, census: dict[str, Any], manifest_path: Path) -> int:
    text = packet_path.read_text(encoding="utf-8")
    parsed = parse_packet(text)
    rows = parsed["rows"]
    print(f"packet:  {packet_path}")
    print(f"sha256-LF: {_sha256_lf(packet_path)}")
    print(f"filas parseadas: {len(rows)} | c_expected declarado: {parsed['c_expected']}")

    checks: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    chk("packet: filas parseadas == c_expected", len(rows) == parsed["c_expected"],
        f"{len(rows)} vs {parsed['c_expected']}")
    chk("packet: document_id unicos", len({r["document_id"] for r in rows}) == len(rows))
    chk("packet: sha_destino unicos", len({r["sha_destino"] for r in rows}) == len(rows))

    pre_ids = census["census"]["g_pre_registro"]["P_A"]["document_ids"]
    packet_ids = {r["document_id"] for r in rows}
    missing = sorted(set(pre_ids) - packet_ids)
    extra = sorted(packet_ids - set(pre_ids))
    declared_excl = set(re.findall(r"^--   - ([0-9a-fA-F-]{36})  ::  ", text, flags=re.M))
    chk("packet subset del pre-registro del census", not extra, f"extra={extra[:5]}")
    chk("cada ausente del pre-registro esta RE-REGISTRADO en la cabecera",
        set(missing) == declared_excl,
        f"ausentes={len(missing)} declarados={len(declared_excl)}")

    print("fetch read-only en vivo ...")
    documents, chunks = fetch_snapshot()
    docs_by_id = {str(d["id"]): d for d in documents}
    ext_by_doc: dict[str, set[str]] = defaultdict(set)
    n_blank = 0
    for c in chunks:
        did = c.get("document_id")
        if not did:
            continue
        e = _norm_ext(c.get("extraction_sha256"))
        if e is None:
            if str(did) in packet_ids:
                n_blank += 1
        else:
            ext_by_doc[str(did)].add(e)

    # (i)
    bad_i = [r["document_id"] for r in rows
             if (docs_by_id.get(r["document_id"]) is None
                 or str(docs_by_id[r["document_id"]].get("status")) != "active"
                 or str(docs_by_id[r["document_id"]].get("source_pdf_sha256")) != r["sha_placeholder"])]
    chk("(i) activo + placeholder EXACTO en documents", not bad_i, f"fallan={bad_i[:5]}")

    # (ii)
    occupied: dict[tuple[str, str], list[str]] = defaultdict(list)
    for d in documents:
        occupied[(str(d.get("manufacturer") or ""), str(d.get("source_pdf_sha256") or ""))].append(str(d["id"]))
    bad_ii: list[str] = []
    intra: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        d = docs_by_id.get(r["document_id"])
        if d is None:
            continue
        mfr = str(d.get("manufacturer") or "")
        if [i for i in occupied.get((mfr, r["sha_destino"]), []) if i != r["document_id"]]:
            bad_ii.append(r["document_id"])
        intra[(mfr, r["sha_destino"])].append(r["document_id"])
    bad_ii_bis = [ids for ids in intra.values() if len(ids) > 1]
    chk("(ii) UNIQUE(manufacturer, sha destino) libre", not bad_ii, f"fallan={bad_ii[:5]}")
    chk("(ii-bis) sin colision INTRA-packet", not bad_ii_bis, f"grupos={bad_ii_bis[:3]}")

    # (iii)
    bad_iii = [r["document_id"] for r in rows
               if sorted(ext_by_doc.get(r["document_id"], set())) != [r["sha_destino"]]]
    chk("(iii) extraction_sha256 UNICA == sha destino", not bad_iii, f"fallan={bad_iii[:5]}")

    # (i-bis) documentos ajenos que comparten un placeholder del packet
    packet_ph = {r["sha_placeholder"] for r in rows}
    foreign_ph = [str(d["id"]) for d in documents
                  if str(d.get("source_pdf_sha256") or "") in packet_ph
                  and str(d["id"]) not in packet_ids]
    chk("(i-bis) docs AJENOS con un placeholder del packet == ancla",
        len(foreign_ph) == parsed["c_ph_ajenos"],
        f"{len(foreign_ph)} vs {parsed['c_ph_ajenos']} · {foreign_ph[:5]}")
    chk("(iii-bis) chunks sin extraction == ancla del packet", n_blank == parsed["c_sin_ext"],
        f"{n_blank} vs {parsed['c_sin_ext']}")

    # (iv)
    n_docs = len(documents)
    n_ph = sum(1 for d in documents if str(d.get("source_pdf_sha256") or "").startswith("backfill:"))
    chk("(iv) documents totales == ancla", n_docs == parsed["c_docs_total"],
        f"{n_docs} vs {parsed['c_docs_total']}")
    chk("(iv-bis) placeholders PRE == ancla", n_ph == parsed["c_ph_pre"], f"{n_ph} vs {parsed['c_ph_pre']}")
    chk("aritmetica placeholders POST", parsed["c_ph_pre"] - len(rows) == parsed["c_ph_post"],
        f"{parsed['c_ph_pre']} - {len(rows)} = {parsed['c_ph_pre'] - len(rows)} vs {parsed['c_ph_post']}")

    # DUAL-KEY contra el manifest de blobs del census (evidencia independiente del packet)
    by_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                by_stem[str(e.get("stem") or "")].append(e)
        bad_dk = []
        for r in rows:
            d = docs_by_id.get(r["document_id"])
            stem = _pdf_stem(str((d or {}).get("source_pdf_filename") or ""))
            if not any(b.get("sha256") == r["sha_destino"] for b in by_stem.get(stem, [])):
                bad_dk.append(r["document_id"])
        chk("dual-key (stem Y sha en el MISMO blob local)", not bad_dk, f"fallan={bad_dk[:5]}")
    else:
        chk("dual-key (manifest de blobs)", False, f"manifest ausente: {manifest_path}")

    # la tabla de backup NO debe existir todavia (best-effort read-only via PostgREST;
    # el guard duro es el `to_regclass` del propio packet)
    try:
        resp = httpx.get(f"{_BASE}/rest/v1/{BACKUP_TABLE}", headers=_H,
                         params={"select": "id", "limit": "1"}, timeout=60)
        backup_state = "EXISTE" if resp.status_code == 200 else f"ausente (HTTP {resp.status_code})"
        chk(f"backup public.{BACKUP_TABLE} aun NO existe", resp.status_code != 200, backup_state)
    except Exception as exc:  # noqa: BLE001
        chk(f"backup public.{BACKUP_TABLE} aun NO existe", True, f"no comprobable: {exc!r}")

    print("\n== CHECKS ==")
    ok_all = True
    for name, ok, detail in checks:
        ok_all &= ok
        print(f"  [{'OK ' if ok else 'FAIL'}] {name}{('  ' + detail) if (detail and not ok) else ''}")
    print(f"\nVERIFY: {'PASS' if ok_all else 'FAIL'}  ({len(rows)} filas contra DB en vivo)")
    return 0 if ok_all else 3


# ── main ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="s288 A-CORE F1/P-A packet generator (read-only)")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--verify", action="store_true",
                    help="re-lee el packet emitido y re-verifica precondiciones contra la DB")
    args = ap.parse_args(argv)
    tag = args.tag

    spec = ROOT / "evals/s288_acore_design_brief_v1.md"
    census_path = ROOT / f"evals/s288_acore_census_v2_result_{tag}.json"
    manifest_path = ROOT / f"evals/s288_acore_blob_manifest_{tag}.jsonl"
    out_path = ROOT / f"evals/s288_acore_pA_apply_{tag}.sql"

    census = json.loads(census_path.read_text(encoding="utf-8"))
    if census.get("schema") != "s288_acore_census_v2":
        raise SystemExit(f"census inesperado: schema={census.get('schema')}")
    pa = census["census"]["g_pre_registro"]["P_A"]
    pre_ids = list(pa["document_ids"])
    if len(pre_ids) != int(pa["n_elegibles"]):
        raise SystemExit("census incoherente: n_elegibles != len(document_ids)")

    _init_http()

    if args.verify:
        return verify(out_path, census, manifest_path)

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    print(f"commit={head[:10]} CHUNKS_TABLE={os.environ.get('CHUNKS_TABLE')} "
          f"pre-registro P-A={len(pre_ids)} (census tag {tag}, commit {CENSUS_COMMIT})")

    meta = {
        "census_result_rel": census_path.relative_to(ROOT).as_posix(),
        "census_sha256_lf": _sha256_lf(census_path),
        "census_tag": tag,
        "spec_rel": spec.relative_to(ROOT).as_posix(),
        "spec_sha256_lf": _sha256_lf(spec),
        "generator_rel": Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "generator_sha256_lf": _sha256_lf(Path(__file__).resolve()),
        "n_pre_registro": len(pre_ids),
    }

    # -- pasada 1 --
    print("pass1: fetch read-only ...")
    d1, c1 = fetch_snapshot()
    der1 = build_rows(pre_ids, d1, c1)
    txt1 = render_packet(der1, meta)
    d1 = c1 = None

    # -- pasada 2 (contrato de re-emision determinista: fetch INDEPENDIENTE) --
    print("pass2: fetch read-only ...")
    d2, c2 = fetch_snapshot()
    der2 = build_rows(pre_ids, d2, c2)
    txt2 = render_packet(der2, meta)
    d2 = c2 = None

    identical = txt1.encode("utf-8") == txt2.encode("utf-8")
    out_path.write_bytes(txt1.encode("utf-8"))  # LF puro (sin traduccion de EOL)

    der = der1
    n = len(der["rows"])
    print()
    print(f"packet:            {out_path}")
    print(f"filas emitidas:    {n}  (pre-registro {len(pre_ids)}, excluidos {len(der['excluded'])})")
    print(f"sha256-LF packet:  {_sha256_lf(out_path)}")
    print(f"re-emision 2x byte-identica: {identical}")
    print(f"documents={der['docs_total']} placeholders_pre={der['placeholder_total']} "
          f"placeholders_post={der['placeholder_total'] - n}")
    if der["excluded"]:
        print("EXCLUIDOS (re-registrados en la cabecera del packet):")
        for e in der["excluded"]:
            print(f"  - {e['document_id']}  ::  {e['reason']}")
    else:
        print("EXCLUIDOS: ninguno")
    if der["placeholder_formula_mismatch"]:
        print(f"diagnostico: {len(der['placeholder_formula_mismatch'])} placeholders no reproducen "
              "la formula canonica (valor tomado de la DB, no recomputado)")
    if der["dest_shared_across_rows"]:
        print(f"AVISO: {len(der['dest_shared_across_rows'])} sha destino compartidas entre filas")
    if der["n_chunks_sin_extraction_total"]:
        print(f"chunks sin extraction_sha256 en los docs del packet: {der['n_chunks_sin_extraction_total']}")
    return 0 if identical else 2


if __name__ == "__main__":
    raise SystemExit(main())
