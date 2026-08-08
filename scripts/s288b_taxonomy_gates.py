#!/usr/bin/env python3
"""s288b — gates deterministas ($0) del lever de ONTOLOGÍA de la lane hyq.

Spec sellado: ``evals/s288_taxonomy_lever_design_brief_v1.md`` (v3, §3 build + §4
gates).  El lever cambia el PAR de configs de ``doc_scoped_hyq_coverage``
(retrieval_facets_v1 -> v4 en el match, evidence_coverage_facets_v4 -> v5 en las
cards) y añade la barrera espejo de alineación query↔card; NINGUNA config se
edita — la inertness por BYTES es el gate 5.

Modos (``python scripts/s288b_taxonomy_gates.py [modo] [--skip-suite]``):

  all (default) | gate0 | gate1 | gate2 | gate2b | gate3 | gate4 | gate5

Todo es GET-only y sin endpoint de modelo.  Los golds se leen SIEMPRE por la
puerta ``scripts.gold_store.verified()`` (nunca el YAML crudo: contiene held-out
embargados; ``verified()`` los excluye por defecto — DEC-023).

Salidas: ``evals/s288b_taxonomy_gates_v1.json`` (+ ``evals/s288b_gate0_receipt_v1.json``
para el receipt del gate 0) y un resumen legible por stdout.  Exit 1 si algún gate
falla — los gates NO se relajan.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

os.environ["CHUNKS_TABLE"] = "chunks_v2"
load_dotenv(ROOT / ".env", override=False)
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import httpx  # noqa: E402

import src.config as cfg  # noqa: E402
from scripts.gold_store import verified  # noqa: E402
from src.rag.doc_scoped_hyq_coverage import (  # noqa: E402
    MIN_QUERY_ALIGNED_CARD_TERMS,
    QUERY_FACETS_CONFIG,
    collect_document_scoped_hyq,
)
from src.rag.evidence_coverage import POOL_COMPLEMENT_CONFIG  # noqa: E402
from src.rag.query_facets import DEFAULT_CONFIG as FACETS_V1  # noqa: E402
from src.rag.query_facets import expand_query_facets  # noqa: E402

GATES_OUT = ROOT / "evals" / "s288b_taxonomy_gates_v1.json"
GATE0_OUT = ROOT / "evals" / "s288b_gate0_receipt_v1.json"

# ─────────────────────────── contratos pre-registrados ───────────────────────────
# §2 del brief, REGENERADA con los nombres EXACTOS del runtime (el brief abrevia
# `fault_reset` / `connect_install` / `program_delay`).  Cualquier desviación = STOP.
EXPECTED_DIFF: dict[str, tuple[str | None, str | None]] = {
    "cat010": (None, "intrinsic_safety"),
    "hp013": (None, "replace_without_loss"),
    "cat007": ("fault_reset_recovery", "loop_eol_topology"),
    "cat008": ("connect_install_wire", "loop_eol_topology"),
    "cat009": ("connect_install_wire", "loop_eol_topology"),
    "cat013": ("connect_install_wire", "compatibility"),
    "hp008": (None, "compatibility"),
    "hp002": (None, "fault_reset_recovery"),
    "hp009": (None, "loop_eol_topology"),
    "cat023": ("program_delay_cause_effect", None),
}
EXPECTED_UNCHANGED = 29
EXPECTED_DEV_GOLDS = 39

# Gate 0: la diana cat010 y sus DOS documentos resueltos (F3/§1 del brief).
GATE0_DOCUMENTS = {
    "2b694083-5b21-4f1a-a29b-565072860fb8": {
        "label": "IS5001-F_IS-mA1_EN",
        "expected_hyq_rows": 48,
        "expected_hyq_rows_live_parent": 16,
    },
    "a6b9dc84-af6d-4957-a403-4b4c2136557b": {
        "label": "manual IS MA1",
        "expected_hyq_rows": 49,
        "expected_hyq_rows_live_parent": 49,
    },
}
_REAL_SHA256 = re.compile(r"[0-9a-f]{64}")

# Gate 2: sintéticos NEGATIVOS de over-trigger — ninguno puede capturar
# ``intrinsic_safety`` (la ontología nueva no puede robar preguntas de consumo /
# dimensionado de baterías).
GATE2_NEGATIVES = (
    "¿cuál es el consumo por lazo?",
    "¿qué batería de 12 Ah necesito?",
)
GATE2_FORBIDDEN_ARCHETYPE = "intrinsic_safety"
# Caso-SOMBRA: conducta HEREDADA de v4 (las lanes hermanas ya viven con ella).
# Se DOCUMENTA, no es STOP de este lever.
GATE2_SHADOW = ("¿cómo se cambia el retardo de sirenas?", "replace_without_loss")

# Gate 3: valores de seguridad intrínseca en las quotes servidas.
IS_VALUE_PATTERNS = {
    "entity_parameter_symbol": re.compile(r"\b[UIPCL]i\b"),
    "supply_or_voltage_word": re.compile(
        r"(aliment\w*|tensi[oó]n|voltaj\w*|voltage|supply|corriente|current)",
        re.IGNORECASE,
    ),
}
GATE3_QID = "cat010"

# Gate 5: las 7 configs de facets que el lever declara byte-INTACTAS (§0 del brief).
INERT_CONFIGS = (
    "config/retrieval_facets_v1.yaml",
    "config/retrieval_facets_v2.yaml",
    "config/retrieval_facets_v3.yaml",
    "config/retrieval_facets_v4.yaml",
    "config/evidence_coverage_facets_v2.yaml",
    "config/evidence_coverage_facets_v4.yaml",
    "config/evidence_coverage_facets_v5.yaml",
)


# ──────────────────────────────── utilidades ────────────────────────────────
def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()


def _headers(count: bool = False) -> dict[str, str]:
    headers = {
        "apikey": cfg.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {cfg.SUPABASE_SERVICE_KEY}",
    }
    if count:
        headers["Prefer"] = "count=exact"
    return headers


def _get(path: str, params: dict[str, str], *, count: bool = False):
    """GET read-only contra PostgREST; devuelve (payload, total, url_efectiva)."""
    url = f"{cfg.SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    response = httpx.get(url, headers=_headers(count), params=params, timeout=30)
    response.raise_for_status()
    total = None
    content_range = response.headers.get("content-range")
    if content_range and "/" in content_range:
        # Sin ``Prefer: count=exact`` PostgREST devuelve ``.../*``.
        raw_total = content_range.split("/")[1]
        total = int(raw_total) if raw_total.isdigit() else None
    return response.json(), total, str(response.request.url)


def _corpus_fingerprint() -> dict[str, Any]:
    """Conteos del corpus vivo, estampados con los gates (freeze §4)."""
    fingerprint: dict[str, Any] = {}
    for name, table, params in (
        ("documents", "documents", {"select": "id", "limit": "1"}),
        ("documents_placeholder_sha", "documents",
         {"select": "id", "source_pdf_sha256": "like.backfill:*", "limit": "1"}),
        ("chunks_v2", "chunks_v2", {"select": "id", "limit": "1"}),
        ("chunks_v2_hyq", "chunks_v2_hyq", {"select": "chunk_id", "limit": "1"}),
    ):
        try:
            _, total, _ = _get(table, params, count=True)
            fingerprint[name] = total
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            fingerprint[name] = f"error: {type(exc).__name__}"
    return fingerprint


def _golds() -> list[dict[str, Any]]:
    golds = verified()  # held-out EMBARGADO por la puerta (DEC-023)
    return sorted(golds, key=lambda gold: str(gold.get("qid")))


def _assignment(golds: list[dict[str, Any]]) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {}
    for gold in golds:
        question = str(gold.get("question") or "")
        out[str(gold.get("qid"))] = {
            "v1": expand_query_facets(question).get("archetype"),
            "v4": expand_query_facets(question, QUERY_FACETS_CONFIG).get("archetype"),
        }
    return out


# ─────────────────────────────────── gates ───────────────────────────────────
def gate0() -> dict[str, Any]:
    """Re-ejecuta la verificación de surrogates de cat010 y SELLA el receipt."""
    queries: list[dict[str, Any]] = []
    documents: dict[str, Any] = {}
    failures: list[str] = []

    document_ids = sorted(GATE0_DOCUMENTS)
    in_filter = 'in.("' + '","'.join(document_ids) + '")'
    params = {
        "select": "id,status,source_pdf_sha256,document_family,product_model",
        "id": in_filter,
        "order": "id.asc",
    }
    rows, _, url = _get("documents", params)
    queries.append({"purpose": "documents_authority", "table": "documents",
                    "params": params, "url": url, "rows": rows})
    by_id = {str(row.get("id")): row for row in rows}
    for document_id, expected in GATE0_DOCUMENTS.items():
        row = by_id.get(document_id)
        record: dict[str, Any] = {"label": expected["label"]}
        if row is None:
            failures.append(f"gate0: documento ausente {document_id}")
            documents[document_id] = {**record, "present": False}
            continue
        sha = str(row.get("source_pdf_sha256") or "").strip().casefold()
        record.update({
            "present": True,
            "status": row.get("status"),
            "source_pdf_sha256": sha,
            "sha_is_real_64hex": bool(_REAL_SHA256.fullmatch(sha)),
            "document_family": row.get("document_family"),
            "product_model": row.get("product_model"),
        })
        if record["status"] != "active":
            failures.append(f"gate0: {document_id} status={record['status']}")
        if not record["sha_is_real_64hex"]:
            failures.append(f"gate0: {document_id} sha no real ({sha[:24]}…)")
        for label, extra in (
            ("hyq_rows", {}),
            ("hyq_rows_live_parent", {"chunks_v2.duplicate_of": "is.null"}),
        ):
            count_params = {
                "select": "chunk_id,chunks_v2!inner(document_id,duplicate_of)",
                "chunks_v2.document_id": f"eq.{document_id}",
                "limit": "1",
                **extra,
            }
            _, total, count_url = _get("chunks_v2_hyq", count_params, count=True)
            queries.append({"purpose": f"{label}:{document_id}",
                            "table": "chunks_v2_hyq", "params": count_params,
                            "url": count_url, "count": total})
            record[label] = total
            expected_count = expected[f"expected_{label}"]
            record[f"expected_{label}"] = expected_count
            if total != expected_count:
                failures.append(
                    f"gate0: {document_id} {label}={total} (esperado {expected_count})"
                )
        documents[document_id] = record

    receipt = {
        "receipt": "s288b_gate0_cat010_surrogates_v1",
        "commit": _git("rev-parse", "HEAD"),
        "read_only": True,
        "documents": documents,
        "queries": queries,
        "failures": failures,
        "pass": not failures,
    }
    GATE0_OUT.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "gate": 0,
        "name": "surrogates de cat010 (receipt sellado)",
        "pass": not failures,
        "failures": failures,
        "receipt_path": GATE0_OUT.relative_to(ROOT).as_posix(),
        "documents": documents,
    }


def gate1(assignment: dict[str, dict[str, str | None]]) -> dict[str, Any]:
    """El diff v1->v4 sobre los 39 dev == la tabla §2 EXACTA."""
    observed = {
        qid: (values["v1"], values["v4"])
        for qid, values in assignment.items()
        if values["v1"] != values["v4"]
    }
    unchanged = len(assignment) - len(observed)
    failures: list[str] = []
    if len(assignment) != EXPECTED_DEV_GOLDS:
        failures.append(
            f"gate1: {len(assignment)} golds dev (esperados {EXPECTED_DEV_GOLDS})"
        )
    for qid in sorted(set(observed) | set(EXPECTED_DIFF)):
        want = EXPECTED_DIFF.get(qid)
        got = observed.get(qid)
        if want != got:
            failures.append(f"gate1: {qid} esperado {want} · observado {got}")
    if unchanged != EXPECTED_UNCHANGED:
        failures.append(
            f"gate1: {unchanged} sin cambio (esperados {EXPECTED_UNCHANGED})"
        )
    return {
        "gate": 1,
        "name": "diff de asignación v1->v4 == tabla §2",
        "pass": not failures,
        "failures": failures,
        "dev_golds": len(assignment),
        "changed": len(observed),
        "unchanged": unchanged,
        "observed_diff": {qid: list(pair) for qid, pair in sorted(observed.items())},
    }


def gate2() -> dict[str, Any]:
    """Sintéticos negativos + caso-sombra heredado (documentado, no-STOP)."""
    negatives = []
    failures: list[str] = []
    for query in GATE2_NEGATIVES:
        archetype = expand_query_facets(query, QUERY_FACETS_CONFIG).get("archetype")
        negatives.append({"query": query, "archetype_v4": archetype})
        if archetype == GATE2_FORBIDDEN_ARCHETYPE:
            failures.append(f"gate2: «{query}» captura {GATE2_FORBIDDEN_ARCHETYPE}")
    shadow_query, shadow_expected = GATE2_SHADOW
    shadow_archetype = expand_query_facets(
        shadow_query, QUERY_FACETS_CONFIG
    ).get("archetype")
    return {
        "gate": 2,
        "name": "sintéticos negativos (over-trigger) + caso-sombra",
        "pass": not failures,
        "failures": failures,
        "negatives": negatives,
        "shadow_case": {
            "query": shadow_query,
            "archetype_v4": shadow_archetype,
            "documented_expectation": shadow_expected,
            "matches_documented": shadow_archetype == shadow_expected,
            "verdict": "HEREDADO de v4 — declarado, no-STOP de este lever",
        },
    }


def _card_view(card: dict[str, Any]) -> dict[str, Any]:
    # La quote se guarda ENTERA (una card está acotada por ``window_chars``: 360
    # caracteres en v5).  Truncarla aquí haría que el gate 3 buscara los valores
    # IS sobre un recorte propio y confundiera "no está" con "no lo miré".
    return {
        "facet": card.get("facet"),
        "query_term_hits": list(card.get("query_term_hits") or []),
        "facet_term_hits": list(card.get("facet_term_hits") or []),
        "quote": str(card.get("quote") or ""),
    }


def gate2b(
    golds: list[dict[str, Any]], assignment: dict[str, dict[str, str | None]]
) -> dict[str, Any]:
    """Sweep de CARDS sobre los 39: ningún parent servido sin card query-alineada.

    Secuencial y acotado: solo entran las queries con arquetipo v4 no-None
    (~20), cada una ≤6 GET (MAX_HTTP_REQUESTS de la lane).  $0, sin modelo.
    """
    question_by_qid = {str(g.get("qid")): str(g.get("question") or "") for g in golds}
    per_query: dict[str, Any] = {}
    failures: list[str] = []
    counterfactual = {"ge1": 0, "ge2": 0, "ge3": 0, "ge6": 0, "served": 0}
    for qid in sorted(question_by_qid):
        if assignment[qid]["v4"] is None:
            continue
        query = question_by_qid[qid]
        try:
            rows, trace = collect_document_scoped_hyq(
                query, include_fetch_receipts=True
            )
        except (RuntimeError, TimeoutError, httpx.HTTPError) as exc:
            failures.append(f"gate2b: {qid} lane error {type(exc).__name__}: {exc}")
            per_query[qid] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        rejected_by_reason: dict[str, int] = {}
        for entry in trace.get("parents_rejected") or []:
            reason = str(entry.get("reason"))
            rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1
        served = []
        for row in rows:
            cards = row.get("coverage_cards") or []
            hit_counts = [len(card.get("query_term_hits") or []) for card in cards]
            best = max(hit_counts, default=0)
            counterfactual["served"] += 1
            for threshold, key in ((1, "ge1"), (2, "ge2"), (3, "ge3"), (6, "ge6")):
                if best >= threshold:
                    counterfactual[key] += 1
            if best < MIN_QUERY_ALIGNED_CARD_TERMS:
                failures.append(
                    f"gate2b: {qid} sirve {row.get('id')} sin card query-alineada"
                )
            served.append({
                "id": str(row.get("id") or ""),
                "source_file": str(row.get("source_file") or ""),
                "page_number": row.get("page_number"),
                "facets": row.get("coverage_card_facets") or [],
                "max_query_term_hits": best,
                "cards": [_card_view(card) for card in cards],
            })
        receipts = trace.get("fetch_receipts") or {}
        per_query[qid] = {
            "archetype_v4": assignment[qid]["v4"],
            "status": trace.get("status"),
            "served": len(served),
            "rejected": sum(rejected_by_reason.values()),
            "rejected_by_reason": rejected_by_reason,
            "http_requests": trace.get("http_requests"),
            "hyq_rows": trace.get("hyq_rows"),
            "scope_document_ids": trace.get("scope_document_ids"),
            # Freeze del probe (Sol-3): fingerprint de las FILAS consumidas, no
            # de conteos — dos corpus distintos con el mismo conteo no colisionan.
            "fetch_fingerprints": {
                key: receipts.get(key)
                for key in (
                    "hyq_rows_sha256",
                    "selected_parent_ids_sha256",
                    "hydrated_parents_sha256",
                )
            },
            "served_parents": served,
        }
    return {
        "gate": "2b",
        "name": "sweep de cards — ningún parent servido sin card query-alineada",
        "pass": not failures,
        "failures": failures,
        "queries_entered": len(per_query),
        "barrier_threshold": MIN_QUERY_ALIGNED_CARD_TERMS,
        # Contrafactual informativo: cuántos parents servidos sobrevivirían a un
        # umbral más alto sobre la MISMA métrica (query_term_hits).
        "counterfactual_thresholds": counterfactual,
        "per_query": per_query,
    }


def gate3(
    golds: list[dict[str, Any]], sweep: dict[str, Any] | None
) -> dict[str, Any]:
    """Probe de MECANISMO de cat010: entra + sirve + las quotes traen valores IS."""
    question = next(
        (str(g.get("question") or "") for g in golds if str(g.get("qid")) == GATE3_QID),
        "",
    )
    record = (sweep or {}).get("per_query", {}).get(GATE3_QID)
    if record is None or "error" in record:
        rows, trace = collect_document_scoped_hyq(question, include_fetch_receipts=True)
        record = {
            "archetype_v4": expand_query_facets(
                question, QUERY_FACETS_CONFIG
            ).get("archetype"),
            "status": trace.get("status"),
            "served": len(rows),
            "served_parents": [
                {
                    "id": str(row.get("id") or ""),
                    "source_file": str(row.get("source_file") or ""),
                    "page_number": row.get("page_number"),
                    "facets": row.get("coverage_card_facets") or [],
                    "cards": [
                        _card_view(card) for card in (row.get("coverage_cards") or [])
                    ],
                }
                for row in rows
            ],
        }
    failures: list[str] = []
    if record.get("archetype_v4") != "intrinsic_safety":
        failures.append(
            f"gate3: cat010 entra como {record.get('archetype_v4')} (esperado intrinsic_safety)"
        )
    if not record.get("served"):
        failures.append(f"gate3: cat010 no sirve parents (status={record.get('status')})")
    matches: dict[str, list[str]] = {name: [] for name in IS_VALUE_PATTERNS}
    for parent in record.get("served_parents") or []:
        for card in parent.get("cards") or []:
            quote = str(card.get("quote") or "")
            for name, pattern in IS_VALUE_PATTERNS.items():
                found = pattern.findall(quote)
                if found:
                    matches[name].extend(
                        sorted({m if isinstance(m, str) else m[0] for m in found})
                    )
    is_values_present = any(matches.values())
    return {
        "gate": 3,
        "name": "probe de mecanismo cat010 (entra · sirve · valores IS en la quote)",
        # El gate mide MECANISMO; la ausencia de valor con parents servidos NO se
        # atribuye a «corpus» sino a la clase de recorte de vista (excerpt).
        "pass": not failures,
        "failures": failures,
        "question": question,
        "archetype_v4": record.get("archetype_v4"),
        "status": record.get("status"),
        "served": record.get("served"),
        "is_values_present": is_values_present,
        "is_value_matches": {name: sorted(set(values)) for name, values in matches.items()},
        "attribution_if_no_value": (
            "clase excerpt (append_view_truncated-like) — NUNCA corpus"
            if not is_values_present
            else "n/a"
        ),
        "served_parents": record.get("served_parents"),
    }


def gate4(
    assignment: dict[str, dict[str, str | None]], sweep: dict[str, Any]
) -> dict[str, Any]:
    """El sweep de ENTRADA a la lane == la tabla §2."""
    entering_v4 = {qid for qid, values in assignment.items() if values["v4"] is not None}
    entering_v1 = {qid for qid, values in assignment.items() if values["v1"] is not None}
    invoked = {qid for qid in (sweep.get("per_query") or {})}
    expected_gained = {
        qid for qid, (before, after) in EXPECTED_DIFF.items()
        if before is None and after is not None
    }
    expected_lost = {
        qid for qid, (before, after) in EXPECTED_DIFF.items()
        if before is not None and after is None
    }
    gained = entering_v4 - entering_v1
    lost = entering_v1 - entering_v4
    failures: list[str] = []
    if invoked != entering_v4:
        failures.append(
            f"gate4: invocadas {sorted(invoked)} != entrantes v4 {sorted(entering_v4)}"
        )
    if gained != expected_gained:
        failures.append(
            f"gate4: ganan entrada {sorted(gained)} (esperado {sorted(expected_gained)})"
        )
    if lost != expected_lost:
        failures.append(
            f"gate4: pierden entrada {sorted(lost)} (esperado {sorted(expected_lost)})"
        )
    return {
        "gate": 4,
        "name": "sweep de entrada a la lane == tabla §2",
        "pass": not failures,
        "failures": failures,
        "entering_v1": sorted(entering_v1),
        "entering_v4": sorted(entering_v4),
        "gained_entry": sorted(gained),
        "lost_entry": sorted(lost),
    }


def gate5(skip_suite: bool = False) -> dict[str, Any]:
    """Inertness por BYTES de las 7 configs + suite completa."""
    failures: list[str] = []
    configs: dict[str, Any] = {}
    for relative in INERT_CONFIGS:
        working = (ROOT / relative).read_bytes()
        head = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
        ).stdout
        # ``core.autocrlf=true`` en este checkout: el árbol de trabajo lleva CRLF
        # y el blob de HEAD LF, así que un sha256 crudo contra crudo compararía
        # el FILTRO de checkout, no el contenido.  Se comparan las tres señales
        # sobre el MISMO plano: sha256 normalizado a LF, id de blob de git (que
        # aplica el filtro clean en los dos lados) y el propio dirty-check.
        head_sha = hashlib.sha256(head).hexdigest()
        worktree_sha = hashlib.sha256(working).hexdigest()
        normalized_sha = hashlib.sha256(
            working.replace(b"\r\n", b"\n")
        ).hexdigest()
        blob_worktree = _git("hash-object", relative)
        blob_head = _git("rev-parse", f"HEAD:{relative}")
        dirty = _git("status", "--porcelain", "--", relative)
        identical = (
            normalized_sha == head_sha
            and blob_worktree == blob_head
            and not dirty
        )
        configs[relative] = {
            "sha256_head_blob": head_sha,
            "sha256_worktree_raw": worktree_sha,
            "sha256_worktree_normalized_lf": normalized_sha,
            "git_blob_worktree": blob_worktree,
            "git_blob_head": blob_head,
            "git_status_porcelain": dirty,
            "identical": identical,
        }
        if not identical:
            failures.append(f"gate5: {relative} cambió de bytes")
    suite: dict[str, Any] = {"run": not skip_suite}
    if not skip_suite:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        tail = [line for line in completed.stdout.strip().splitlines() if line.strip()]
        suite.update({
            "returncode": completed.returncode,
            "summary": tail[-1] if tail else "",
            "failed_lines": [line for line in tail if line.startswith("FAILED")],
        })
        if completed.returncode != 0:
            failures.append(f"gate5: pytest returncode={completed.returncode}")
    return {
        "gate": 5,
        "name": "inertness por bytes de las 7 configs + suite completa",
        "pass": not failures,
        "failures": failures,
        "configs": configs,
        "suite": suite,
        "pointers": {
            "hyq_match_config": QUERY_FACETS_CONFIG.relative_to(ROOT).as_posix(),
            "hyq_card_config": POOL_COMPLEMENT_CONFIG.relative_to(ROOT).as_posix(),
            "facets_v1_default_unchanged": FACETS_V1.relative_to(ROOT).as_posix(),
        },
    }


# ──────────────────────────────────── main ────────────────────────────────────
def main(argv: list[str]) -> int:
    mode = next((arg for arg in argv if not arg.startswith("--")), "all")
    skip_suite = "--skip-suite" in argv
    golds = _golds()
    assignment = _assignment(golds)
    results: list[dict[str, Any]] = []
    sweep: dict[str, Any] | None = None

    if mode in {"all", "gate0"}:
        results.append(gate0())
    if mode in {"all", "gate1"}:
        results.append(gate1(assignment))
    if mode in {"all", "gate2"}:
        results.append(gate2())
    if mode in {"all", "gate2b", "gate3", "gate4"}:
        sweep = gate2b(golds, assignment)
        if mode in {"all", "gate2b"}:
            results.append(sweep)
    if mode in {"all", "gate3"}:
        results.append(gate3(golds, sweep))
    if mode in {"all", "gate4"}:
        results.append(gate4(assignment, sweep or {}))
    if mode in {"all", "gate5"}:
        results.append(gate5(skip_suite=skip_suite))

    payload = {
        "gates": "s288b_taxonomy_lever_v3",
        "mode": mode,
        "commit": _git("rev-parse", "HEAD"),
        "corpus_fingerprint": _corpus_fingerprint() if mode == "all" else None,
        "dev_golds": len(golds),
        "barrier": {
            "constant": "MIN_QUERY_ALIGNED_CARD_TERMS",
            "value": MIN_QUERY_ALIGNED_CARD_TERMS,
            "mirror_of": "pool_selection.MIN_ALIGNMENT_TERMS = 6 "
                         "(pool_selection.py post-L2c, aplicado en _query_card "
                         "e impuesto en :341-342)",
        },
        "results": results,
    }
    if mode == "all":
        GATES_OUT.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(f"=== s288b gates (modo {mode}) — commit {payload['commit'][:8]} ===")
    for result in results:
        status = "PASS" if result["pass"] else "FAIL"
        print(f"[gate {result['gate']}] {status} — {result['name']}")
        for failure in result["failures"]:
            print(f"    ! {failure}")
    failed = [result for result in results if not result["pass"]]
    if mode == "all":
        print(f"\n-> {GATES_OUT.relative_to(ROOT).as_posix()}")
    print(f"\n{len(results) - len(failed)}/{len(results)} gates en PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
