#!/usr/bin/env python3
"""s287_facet_gates.py — GATES deterministas ($0) del lever de FACETA (DEC-164b).

El lever es SOLO config: arquetipo `variant_differentiation` AL FINAL de
`config/retrieval_facets_v3.yaml` + su gemela en
`config/evidence_coverage_facets_v4.yaml` (STRICT_ALIGNED_CONFIG).  Este
instrumento NO llama a ningun modelo (rerank/juez/generador = 0 llamadas) y NO
escribe en la base de datos.

Los DOS brazos son los DOS ESTADOS de config, no una hipotesis:
  pre  = los blobs de PRE_LEVER_COMMIT (el estado sin arquetipo nuevo)
  post = el arbol de trabajo (este build)

s287 V1: el brazo `pre` estaba anclado a `git HEAD`, que era el estado sin
arquetipo cuando se corrio v1.  Al COMMITEAR el lever (7f2a251) HEAD dejo de ser
el pre-lever y el gate (a) empezo a medir un diff VACIO contra si mismo (STOP
espureo).  El ancla pasa a un COMMIT FIJO — el padre del commit que introdujo el
arquetipo — para que el diff pre-registrado {cat005, cat022} siga significando lo
mismo y el artefacto sea reproducible aunque HEAD siga avanzando.

GATE (a)  expand_query_facets sobre las 39 queries dev de gold_answers_v1.yaml:
          el diff pre->post debe ser EXACTAMENTE {cat005, cat022} (ENMIENDA
          post-STOP sellada en el brief: cat005 es miembro genuino de la clase,
          el pre-registro original la habia dejado sin contar).  Cualquier
          TERCERA query que cambie de arquetipo = STOP (el script sale != 0 y no
          sigue).
GATE (b)  probe de lane en las DOS queries de la clase por la via determinista
          disponible: el probe de pool de P1 no cruza coverage, asi que se llama
          directamente `select_structural_neighbors` con seeds = topk_ids del run
          v3 (evals/s100_factlevel_full_v3_20260729.yaml) y los vecinos
          same-doc/same-blob dentro de max_gap traidos con el SQL del replay s108
          (reutilizado, no duplicado).
          (b.1) cat022 = DIANA: pre no selecciona nada y post SI selecciona
                anclas, y esas anclas son celdas IR.
          (b.2) cat005 = CONTROL PROTEGIDO (hoy 6/6 OK, appended_n=0): se
                registra QUE selecciona, si selecciona.  Si no selecciona nada,
                el control queda intacto.  Si selecciona, cada ancla debe
                aprobar el `required_any` discriminativo [bit, incorporada] y
                su contenido queda volcado entero en el artefacto para
                adjudicacion (ruido generico apendizado = STOP del lever).
                FIX post-STOP-b2: `version` salio del `required_any` (sigue en
                `terms`) por homografo de edicion-de-norma; con eso el unico
                candidato de cat005 (declaracion UE de conformidad) ya no pasa
                el fail-closed y el control queda en 0 anclas.
GATE (b-serving)  s287 V1 cierre 3 (H4) — el gate (b) de arriba mide SELECCION,
          no SERVIDO: era exactamente el hueco que dejo pasar el fallo real (la
          lane seleccionaba anclas de cat022 y NO apendizaba porque las cards se
          fabrican con evidence_coverage_facets_v2.yaml, que no tenia el
          arquetipo => coverage_cards vacias => `_attest` rechaza).  Este gate
          re-juega la RUTA DE SERVING COMPLETA con el cableado de PRODUCCION:
            collect_structural_coverage (defaults reales: v4 match + v2 cards)
              -> append_validated_coverage -> _attest -> coverage_context_content
          El unico seam inyectado es el `fetcher` (devuelve las filas ya traidas
          por el SQL del replay s108: 0 HTTP extra, 0 llamadas a modelo).
            (b.1) cat022 = DIANA: apendiza >=1 fila cuya VISTA SERVIDA (lo que
                  el generador veria) contiene los valores de banda en micrones.
            (b.2) cat005 = CONTROL: sigue con 0 appends.
          TRES brazos sobre la misma ruta: `pre_lever` (sin arquetipo en ninguna
          config), `head_without_card_twin` (arquetipo en v3+v4 pero NO en v2 =
          reproduce el fallo medido: SELECCIONA 2 anclas y apendiza 0) y `post`
          (este build).  El brazo del medio es el que hace CAUSAL el cierre 1.

GATE (c)  centinelas: expand_query_facets de hp009/hp011/hp012/cat012/cat010/
          cat017/hp018 sin cambio.

Salida: evals/s287_facet_gates_v2.json
Uso:    python scripts/s287_facet_gates.py
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any
from unittest import mock

import psycopg2
import yaml
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from s108_structural_retrieval_replay import _fetch_neighbors, _hydrate  # noqa: E402
from src.rag import post_rerank_coverage  # noqa: E402
from src.rag.post_rerank_coverage import (  # noqa: E402
    append_validated_coverage,
    collect_structural_coverage,
    coverage_context_content,
    is_validated_coverage_chunk,
)
from src.rag.query_facets import expand_query_facets  # noqa: E402
from src.rag.structural_neighbor_coverage import (  # noqa: E402
    DEFAULT_CONFIG,
    select_structural_neighbors,
)

GOLDS = ROOT / "evals/gold_answers_v1.yaml"
RUN_V3 = ROOT / "evals/s100_factlevel_full_v3_20260729.yaml"
OUT = ROOT / "evals/s287_facet_gates_v2.json"

# Padre de 7f2a251 («s287: lever de faceta variant_differentiation COMPLETO»),
# el ultimo arbol SIN el arquetipo `variant_differentiation` en ninguna config.
# Es un ANCLA FIJA a proposito: `HEAD` deja de ser el pre-lever en cuanto el
# lever se commitea, y el gate empezaria a medirse contra si mismo.
PRE_LEVER_COMMIT = "0791a3199609fac2a0e92b7ca100de9d95d39d17"

QUERY_FACETS_REL = "config/retrieval_facets_v3.yaml"
EVIDENCE_FACETS_REL = "config/evidence_coverage_facets_v4.yaml"
# s287 V1 cierre 1: el CARD-config de la lane structural
# (structural_neighbor_coverage.py:190).  Entra al brazo `pre` porque es
# EXACTAMENTE el fichero cuya ausencia de arquetipo mataba el append.
EVIDENCE_CARDS_REL = "config/evidence_coverage_facets_v2.yaml"

TARGET_QID = "cat022"
# ENMIENDA post-STOP sellada en evals/s287_facet_lever_design_brief_v1.md:
# cat005 (Fidegas CS4, «...en que se diferencian las versiones digital y
# analogica?») es MIEMBRO de la clase, no un falso positivo del trigger.  Entra
# como CONTROL PROTEGIDO: hoy 6/6 OK con appended_n=0, asi que cualquier
# regresion ahi mata el lever.  El trigger ES natural se CONSERVA (mutilarlo
# seria overfit al gold diana).
CONTROL_QID = "cat005"
# [F2 re-sellado] Diff esperado PRE-REGISTRADO: {cat005, cat022}.
PRE_REGISTERED_CHANGED_QIDS = {TARGET_QID, CONTROL_QID}
PROBE_QIDS = (TARGET_QID, CONTROL_QID)
NEW_ARCHETYPE = "variant_differentiation"
SENTINELS = ("hp009", "hp011", "hp012", "cat012", "cat010", "cat017", "hp018")
# Celdas IR candidatas declaradas en el spec (prefijos de chunk id).
EXPECTED_ANCHOR_PREFIXES = ("74cc9f95", "c94d2270", "36ca37d0", "a6eae6a1")
# `required_any` discriminativo de la faceta gemela `variant_attribute_matrix`
# en evidence_coverage_facets_v4.yaml.  Se re-declara aqui A PROPOSITO: si
# alguien lo relaja en config, el gate lo caza en vez de heredarlo.
# FIX post-STOP-b2: `version` FUERA (homografo de edicion-de-norma; permanece en
# `terms`, solo pierde el poder de sostener sola el fail-closed).
CONTROL_REQUIRED_ANY = ("bit", "incorporada")
NEW_EVIDENCE_FACET_ID = "variant_attribute_matrix"

# ── Adjudicacion del gate (b.2) ─────────────────────────────────────────────
# El criterio «ruido generico» NO tiene separador determinista honesto, asi que
# cuando el control SELECCIONA algo la llamada se hace A MANO leyendo el
# contenido completo que este mismo instrumento vuelca, y queda ESCRITA aqui
# (auditable, no dependiente de la lectura de un turno).  Esta anclada por id: si
# la seleccion cambia, la adjudicacion se marca STALE y el gate para pidiendo
# re-adjudicacion en vez de reutilizar una llamada vieja.
#
# FIX post-STOP-b2 aplicado: cat005 ya NO selecciona ninguna ancla, asi que el
# dict vive VACIO a proposito.  Si la lane volviera a seleccionar algo para el
# control, caeria en `unadjudicated_anchor_ids` => STOP (no hay adjudicacion
# heredada que lo tape).
CONTROL_ADJUDICATIONS: dict[str, dict[str, Any]] = {}

# Traza historica de la adjudicacion que MOTIVO el fix.  Fuera del dict vivo a
# proposito (el chequeo `stale` compara CONTROL_ADJUDICATIONS contra la seleccion
# real; dejarla dentro seria un STOP permanente por una llamada ya resuelta).
RETIRED_CONTROL_ADJUDICATIONS = {
    "38b894d1-3e44-4c0a-a90e-8c216db7ae8e": {
        "verdict": "GENERIC_NOISE",
        "retired_by": "fix_post_stop_b2_version_out_of_required_any",
        "page": 13,
        "what_it_is": (
            "Pagina de DECLARACION UE DE CONFORMIDAD del sensor remoto Fidegas "
            "S/3-2 (normas EN/UNE, organismo notificado, certificado AENOR). No "
            "es una celda de comparativa por-variante."
        ),
        "why_it_matched": (
            "term_hits = [descripcion, sensor, version]: `descripcion` viene de "
            "«DESCRIPCION DEL PRODUCTO», `sensor` de «Sensor remoto de gas» y "
            "`version` de «con respecto a la version EN 60079-0:2009» — la "
            "EDICION DE UNA NORMA, no una variante de producto. El "
            "`required_any` se aprobaba con ese unico `version` homografo."
        ),
        "consequence": (
            "La lane apendizaria ruido normativo a cat005, que hoy es 6/6 OK con "
            "appended_n=0 => STOP del lever por el contrato del control "
            "protegido."
        ),
        "resolution": (
            "`version` fuera del `required_any` de variant_attribute_matrix "
            "(permanece en `terms`): el ancla deja de pasar el fail-closed y el "
            "control vuelve a 0 anclas, sin anti-patrones ni exclusiones por id."
        ),
    },
}

# Mapa de arquetipos pre-registrado A MANO antes de tocar los yaml (cross-check
# independiente del blob de HEAD: si los dos no coinciden, el baseline miente).
PRE_REGISTERED_ARCHETYPES = {
    "hp001": None,
    "hp002": "fault_reset_recovery",
    "hp003": "connect_install_wire",
    "hp004": None,
    "hp005": "program_delay_cause_effect",
    "hp006": None,
    "hp007": None,
    "hp008": "compatibility",
    "hp009": None,
    "hp010": None,
    "hp011": "fault_reset_recovery",
    "hp012": "capacity_quantity",
    "hp013": "replace_without_loss",
    "hp014": "connect_install_wire",
    "hp015": None,
    "hp017": "program_delay_cause_effect",
    "hp018": "connect_install_wire",
    "hp019": None,
    "hp020": None,
    "cat001": "connect_install_wire",
    "cat005": None,
    "cat007": None,
    "cat008": "connect_install_wire",
    "cat009": None,
    "cat010": None,
    "cat011": None,
    "cat012": "battery_sizing",
    "cat013": "compatibility",
    "cat014": None,
    "cat015": None,
    "cat016": None,
    "cat017": "connect_install_wire",
    "cat018": "program_delay_cause_effect",
    "cat019": "program_delay_cause_effect",
    "cat020": None,
    "cat021": None,
    "cat022": None,
    "cat023": None,
    "cat024": None,
}


def _sha256_lf(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _blob(revision: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"blob unavailable: {revision}:{relative}")
    return completed.stdout


def dev_questions() -> list[dict[str, Any]]:
    rows = yaml.safe_load(GOLDS.read_text(encoding="utf-8"))
    return [row for row in rows if row.get("split") == "dev"]


def archetype_map(questions: list[dict[str, Any]], facets: Path) -> dict[str, Any]:
    return {
        row["qid"]: expand_query_facets(row["question"], config_path=facets)["archetype"]
        for row in questions
    }


def _matching_patterns(question: str, facets: Path, archetype_id: str) -> list[str]:
    """Que patron exacto dispara — para que un STOP sea accionable, no opaco."""
    from src.rag.query_facets import _load, _norm

    payload = _load(str(Path(facets).resolve()))
    archetype = next(
        (row for row in payload["archetypes"] if row["id"] == archetype_id), None
    )
    if archetype is None:
        return []
    normalized = _norm(question)
    return [
        pattern
        for pattern in archetype["patterns"]
        if re.search(pattern, normalized)
    ]


def gate_a(questions: list[dict[str, Any]], pre: Path, post: Path) -> dict[str, Any]:
    before = archetype_map(questions, pre)
    after = archetype_map(questions, post)
    by_qid = {row["qid"]: row["question"] for row in questions}
    changed = {
        qid: {
            "pre": before[qid],
            "post": after[qid],
            "question": by_qid[qid],
            "matched_patterns": _matching_patterns(by_qid[qid], post, NEW_ARCHETYPE),
        }
        for qid in before
        if before[qid] != after[qid]
    }
    return {
        "gate": (
            "(a) expand_query_facets x39 — diff EXACTO vs pre-registro "
            "re-sellado {cat005, cat022}"
        ),
        "queries": len(questions),
        "pre_archetypes": before,
        "post_archetypes": after,
        "changed": changed,
        "changed_qids": sorted(changed),
        "pre_registered_changed_qids": sorted(PRE_REGISTERED_CHANGED_QIDS),
        "pre_lever_baseline_equals_hand_preregistration": (
            before == PRE_REGISTERED_ARCHETYPES
        ),
        "target_post_archetype": after.get(TARGET_QID),
        "verdict": (
            "PASS"
            if set(changed) == PRE_REGISTERED_CHANGED_QIDS
            and before == PRE_REGISTERED_ARCHETYPES
            and after.get(TARGET_QID) == NEW_ARCHETYPE
            else "STOP"
        ),
    }


def gate_c(questions: list[dict[str, Any]], pre: Path, post: Path) -> dict[str, Any]:
    before = archetype_map(questions, pre)
    after = archetype_map(questions, post)
    rows = {
        qid: {
            "pre": before[qid],
            "post": after[qid],
            "unchanged": before[qid] == after[qid],
        }
        for qid in SENTINELS
    }
    return {
        "gate": "(c) centinelas — expand_query_facets sin cambio",
        "sentinels": rows,
        "verdict": "PASS" if all(row["unchanged"] for row in rows.values()) else "STOP",
    }


def _anchor_receipt(row: dict[str, Any]) -> dict[str, Any]:
    content = row.get("content") or ""
    return {
        "id": str(row["id"]),
        "chunk_index": row["chunk_index"],
        "gap": row["structural_neighbor_gap"],
        "rank": row["structural_neighbor_rank"],
        "page_number": row["page_number"],
        "source_file": row["source_file"],
        "product_model": row["product_model"],
        "language": row["language"],
        "query_score": row["structural_neighbor_query_score"],
        "facets": row["structural_neighbor_facets"],
        "coverage_card_facets": row["coverage_card_facets"],
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_chars": len(content),
        "content": content,
    }


def _probe_arms(
    question: str,
    seeds: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    arms: dict[str, dict[str, Path]],
) -> dict[str, dict[str, Any]]:
    results = {}
    for arm, paths in arms.items():
        selected, trace = select_structural_neighbors(
            question,
            seeds,
            candidates,
            query_facets_path=paths["query_facets"],
            evidence_match_config_path=paths["evidence_facets"],
            # Las cards NO mueven la seleccion (el ranking usa el match-config),
            # pero el brazo debe volcar SUS cards: `coverage_card_facets: []` en
            # el brazo pre es la firma exacta del fallo que cierra el cierre 1.
            evidence_card_config_path=paths["evidence_cards"],
        )
        results[arm] = {
            "trace": trace,
            "selected": [_anchor_receipt(row) for row in selected],
        }
    return results


def _required_any_report(anchor: dict[str, Any]) -> dict[str, Any]:
    """Que termino discriminativo sostiene un ancla — el criterio, explicito."""
    required = set(CONTROL_REQUIRED_ANY)
    facets = anchor.get("facets") or []
    per_facet = [
        {
            "facet": item["facet"],
            "term_hits": item["term_hits"],
            "required_any_hits": sorted(required.intersection(item["term_hits"])),
        }
        for item in facets
    ]
    return {
        "id": anchor["id"],
        "facets": per_facet,
        "satisfies_required_any": any(
            item["facet"] == NEW_EVIDENCE_FACET_ID and item["required_any_hits"]
            for item in per_facet
        ),
    }


def gate_b_target(probe: dict[str, Any]) -> dict[str, Any]:
    """(b.1) cat022 = DIANA: pre no apendiza, post apendiza celdas IR."""
    results = probe["arms"]
    post_ids = [row["id"] for row in results["post"]["selected"]]
    matched_expected = sorted(
        prefix
        for prefix in EXPECTED_ANCHOR_PREFIXES
        if any(chunk_id.startswith(prefix) for chunk_id in post_ids)
    )
    return {
        "role": "target",
        "qid": probe["qid"],
        "question": probe["question"],
        "run_v3_hist": probe["run_v3_hist"],
        "run_v3_appended_n": probe["run_v3_appended_n"],
        "seed_ids": probe["seed_ids"],
        "candidate_rows_fetched": probe["candidate_rows_fetched"],
        "pre": results["pre"],
        "post": results["post"],
        "pre_selected_ids": [row["id"] for row in results["pre"]["selected"]],
        "post_selected_ids": post_ids,
        "expected_anchor_prefixes": list(EXPECTED_ANCHOR_PREFIXES),
        "post_selected_matching_expected_prefixes": matched_expected,
        "verdict": (
            "PASS"
            if not results["pre"]["selected"]
            and post_ids
            and results["post"]["trace"]["archetype"] == NEW_ARCHETYPE
            and matched_expected
            else "STOP"
        ),
    }


def gate_b_control(probe: dict[str, Any]) -> dict[str, Any]:
    """(b.2) cat005 = CONTROL PROTEGIDO: hoy 6/6 OK con appended_n=0.

    No selecionar nada = control intacto.  Selecionar = admisible SOLO si cada
    ancla aprueba el `required_any` discriminativo; el contenido entero se
    vuelca para adjudicar si es celda de comparativa por-variante o prosa
    generica (ruido apendizado sobre un 6/6 = STOP del lever).
    """
    results = probe["arms"]
    post_anchors = results["post"]["selected"]
    post_ids = [row["id"] for row in post_anchors]
    reports = [_required_any_report(anchor) for anchor in post_anchors]
    all_satisfy = all(row["satisfies_required_any"] for row in reports)
    mechanical = (
        "PASS"
        if not results["pre"]["selected"] and (not post_ids or all_satisfy)
        else "STOP"
    )
    adjudications = {
        chunk_id: CONTROL_ADJUDICATIONS.get(chunk_id) for chunk_id in post_ids
    }
    unadjudicated = sorted(
        chunk_id for chunk_id, call in adjudications.items() if call is None
    )
    stale = sorted(set(CONTROL_ADJUDICATIONS) - set(post_ids))
    noise = sorted(
        chunk_id
        for chunk_id, call in adjudications.items()
        if call and call["verdict"] == "GENERIC_NOISE"
    )
    return {
        "role": "protected_control",
        "qid": probe["qid"],
        "question": probe["question"],
        "run_v3_hist": probe["run_v3_hist"],
        "run_v3_appended_n": probe["run_v3_appended_n"],
        "seed_ids": probe["seed_ids"],
        "candidate_rows_fetched": probe["candidate_rows_fetched"],
        "pre": results["pre"],
        "post": results["post"],
        "pre_selected_ids": [row["id"] for row in results["pre"]["selected"]],
        "post_selected_ids": post_ids,
        "post_selected_n": len(post_ids),
        "control_untouched": not post_ids,
        "required_any_declared": list(CONTROL_REQUIRED_ANY),
        "required_any_reports": reports,
        "all_anchors_satisfy_required_any": all_satisfy,
        "mechanical_verdict": mechanical,
        "adjudication_required": bool(post_ids),
        "adjudications": adjudications,
        "unadjudicated_anchor_ids": unadjudicated,
        "stale_adjudication_ids": stale,
        "generic_noise_anchor_ids": noise,
        "retired_adjudications": RETIRED_CONTROL_ADJUDICATIONS,
        # El veredicto del control NO es solo el mecanico: el `required_any`
        # puede aprobarse por vocabulario que no es comparativa (fue el caso del
        # homografo `version`, ya fuera del discriminativo).  La adjudicacion
        # manda, y un ancla sin adjudicar tambien para el gate.
        "verdict": (
            "PASS"
            if mechanical == "PASS"
            and not noise
            and not unadjudicated
            and not stale
            else "STOP"
        ),
        "verdict_basis": (
            "mechanical_and_adjudicated"
            if post_ids
            else "control_untouched_no_append"
        ),
    }


def gate_b(probes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    target = gate_b_target(probes[TARGET_QID])
    control = gate_b_control(probes[CONTROL_QID])
    return {
        "gate": (
            "(b) probe de lane en las 2 queries de la clase (cat022 diana + "
            "cat005 control protegido) — select_structural_neighbors con "
            "seeds=topk_ids del run v3 y vecinos same-doc/same-blob (SQL del "
            "replay s108); 0 llamadas a modelo, 0 escrituras"
        ),
        "probes": {TARGET_QID: target, CONTROL_QID: control},
        "verdict": (
            "PASS" if target["verdict"] == control["verdict"] == "PASS" else "STOP"
        ),
    }


# ── GATE (b-serving): la RUTA DE SERVING completa (H4) ──────────────────────
# Magnitud en micrones PRE-REGISTRADA como criterio de «el span sirve el valor»:
# digito (con decimal opcional) + espacio opcional + `μ`/`u` + `m`, sobre el
# texto NFKD-normalizado (asi el MICRO SIGN `µ` U+00B5 y la mu griega `μ` U+03BC
# son el mismo caracter y no hacen falta dos ramas).  Es un criterio de FORMA
# —no contiene ningun valor del gold— y por eso puede vivir en el instrumento.
_MICRON_VALUE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:μ|u)m\b", re.IGNORECASE)


def _micron_values(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text or "")
    return [match.group(0) for match in _MICRON_VALUE.finditer(normalized)]


def _served_receipt(row: dict[str, Any]) -> dict[str, Any]:
    """Que veria EL GENERADOR de esta fila — no que selecciono el selector."""
    # Vista conservadora: SIN expansion de fila logica (el flag
    # LOGICAL_RECORD_COVERAGE solo puede AGRANDAR spans, nunca encogerlos, asi
    # que un micron visible aqui lo esta tambien con el flag on).
    served = coverage_context_content(row, logical_record_expansion=False)
    expanded = coverage_context_content(row, logical_record_expansion=True)
    return {
        "id": str(row["id"]),
        "retrieval_lane": row.get("retrieval_lane"),
        "page_number": row.get("page_number"),
        "source_file": row.get("source_file"),
        "product_model": row.get("product_model"),
        "post_rerank_coverage_contract": row.get("post_rerank_coverage_contract"),
        "coverage_validated": row.get("coverage_validated"),
        "is_validated_coverage_chunk": is_validated_coverage_chunk(row),
        "parent_content_chars": len(str(row.get("content") or "")),
        "coverage_cards": [
            {
                "facet": card.get("facet"),
                "start": card.get("start"),
                "end": card.get("end"),
                "quote": card.get("quote"),
            }
            for card in row.get("coverage_cards") or []
        ],
        "served_view": served,
        "served_view_chars": len(served),
        "served_view_logical_record_expanded": expanded,
        "micron_values_served": _micron_values(served),
    }


def _serving_route(
    question: str,
    seeds: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    selector=None,
) -> dict[str, Any]:
    """collect -> attest -> append -> serve, con el cableado de PRODUCCION.

    ``collect_structural_coverage`` se llama SIN tocar sus configs: usa los
    defaults de ``select_structural_neighbors`` (v4 match + v2 cards), que es
    justo el par que sirve en runtime.  El unico seam inyectado es el
    ``fetcher`` (0 HTTP: devuelve las filas que ya trajo el SQL del replay).
    Los brazos de BASELINE inyectan ademas un selector parcializado con los
    blobs del commit correspondiente; el brazo `post` no parchea NADA.
    """

    def fetcher(served_chunks, **kwargs):
        del served_chunks, kwargs
        return (
            list(seeds),
            list(candidates),
            {"http_requests": 0, "rows_read": len(candidates)},
        )

    if selector is None:
        selected, lane_trace = collect_structural_coverage(
            question, seeds, fetcher=fetcher
        )
    else:
        with mock.patch.object(
            post_rerank_coverage, "select_structural_neighbors", selector
        ):
            selected, lane_trace = collect_structural_coverage(
                question, seeds, fetcher=fetcher
            )
    served = append_validated_coverage(seeds, selected)
    appended = served[len(seeds):]
    receipts = [_served_receipt(row) for row in appended]
    return {
        "lane_trace": lane_trace,
        "collected_ids": [str(row["id"]) for row in selected],
        "protected_prefix_rows": len(seeds),
        "protected_prefix_intact": served[: len(seeds)] == seeds,
        "appended_n": len(appended),
        "appended_ids": [receipt["id"] for receipt in receipts],
        "appended": receipts,
        "micron_values_served": sorted(
            {value for receipt in receipts for value in receipt["micron_values_served"]}
        ),
    }


def gate_b_serving(
    probes: dict[str, dict[str, Any]],
    pre_paths: dict[str, Path],
    head_paths: dict[str, Path],
) -> dict[str, Any]:
    def selector(paths: dict[str, Path]):
        return functools.partial(
            select_structural_neighbors,
            query_facets_path=paths["query_facets"],
            evidence_match_config_path=paths["evidence_facets"],
            evidence_card_config_path=paths["evidence_cards"],
        )

    arms: dict[str, dict[str, Any]] = {}
    for qid, probe in probes.items():
        arms[qid] = {
            # pre-lever: sin arquetipo en NINGUNA config => ni siquiera selecciona.
            "pre_lever": _serving_route(
                probe["question"],
                probe["seeds"],
                probe["candidates"],
                selector=selector(pre_paths),
            ),
            # HEAD: arquetipo en v3+v4 pero NO en v2 => reproduce el FALLO EXACTO
            # medido en el smoke (selecciona anclas y apendiza 0 porque las cards
            # salen vacias).  Es el brazo que hace CAUSAL al cierre 1.
            "head_without_card_twin": _serving_route(
                probe["question"],
                probe["seeds"],
                probe["candidates"],
                selector=selector(head_paths),
            ),
            "post": _serving_route(
                probe["question"], probe["seeds"], probe["candidates"]
            ),
        }
    target = arms[TARGET_QID]
    control = arms[CONTROL_QID]
    target_verdict = (
        "PASS"
        if target["pre_lever"]["appended_n"] == 0
        # El fallo reproducido: SELECCIONA y NO apendiza.
        and target["head_without_card_twin"]["collected_ids"]
        and target["head_without_card_twin"]["appended_n"] == 0
        and target["post"]["appended_n"] > 0
        and target["post"]["micron_values_served"]
        and target["post"]["protected_prefix_intact"]
        and all(
            receipt["is_validated_coverage_chunk"]
            for receipt in target["post"]["appended"]
        )
        else "STOP"
    )
    control_verdict = (
        "PASS"
        if control["pre_lever"]["appended_n"]
        == control["head_without_card_twin"]["appended_n"]
        == control["post"]["appended_n"]
        == 0
        and control["post"]["protected_prefix_intact"]
        else "STOP"
    )
    return {
        "gate": (
            "(b-serving) RUTA DE SERVING completa — collect_structural_coverage "
            "(defaults de produccion: v4 match + v2 cards) -> _attest -> "
            "append_validated_coverage -> coverage_context_content; fetcher "
            "inyectado con las filas ya traidas (0 HTTP, 0 llamadas a modelo)"
        ),
        "runtime_modifiers": {
            "LOGICAL_RECORD_COVERAGE_env": os.environ.get(
                "LOGICAL_RECORD_COVERAGE", "unset"
            ),
            "verdict_uses_unexpanded_view": True,
            "mandatory_callout_enabled": (
                post_rerank_coverage._mandatory_callout_enabled()
            ),
        },
        "micron_value_pattern": _MICRON_VALUE.pattern,
        "arms": arms,
        "target": {
            "qid": TARGET_QID,
            "pre_lever_appended_n": target["pre_lever"]["appended_n"],
            "head_selected_n": len(
                target["head_without_card_twin"]["collected_ids"]
            ),
            "head_appended_n": target["head_without_card_twin"]["appended_n"],
            "post_appended_n": target["post"]["appended_n"],
            "post_appended_ids": target["post"]["appended_ids"],
            "micron_values_served": target["post"]["micron_values_served"],
            "verdict": target_verdict,
        },
        "control": {
            "qid": CONTROL_QID,
            "pre_lever_appended_n": control["pre_lever"]["appended_n"],
            "head_appended_n": control["head_without_card_twin"]["appended_n"],
            "post_appended_n": control["post"]["appended_n"],
            "verdict": control_verdict,
        },
        "verdict": "PASS" if target_verdict == control_verdict == "PASS" else "STOP",
    }


def h9_serving_block_reconciliation(workspace: Path) -> dict[str, Any]:
    """s287 V1 cierre 4 — H9 decia «bloque serving muerto que nadie lee».

    VERIFICADO CONTRA EL CODIGO (Protocolo 1 aplicado al claim del dueto): el
    bloque SI se lee y es hard-fail en structural_neighbor_coverage.py:138-142.
    Se prueba aqui MUTANDO una copia y comprobando que el loader revienta => el
    yaml NO se toca (contrato vivo) y lo que se corrige es el spec.
    """
    from src.rag.structural_neighbor_coverage import _load

    probes: dict[str, Any] = {}
    mutations = {
        "serving_enabled_true": lambda data: data["serving"].update({"enabled": True}),
        "coverage_validated_field_allowed_true": lambda data: data["serving"].update(
            {"coverage_validated_field_allowed": True}
        ),
        "serving_block_removed": lambda data: data.pop("serving"),
    }
    for index, (name, mutate) in enumerate(mutations.items()):
        data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        mutate(data)
        path = workspace / f"h9_{index}_structural_neighbor_coverage_v1.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        try:
            _load(str(path.resolve()))
            probes[name] = {"loader": "ACCEPTED", "error": None}
        except RuntimeError as error:
            probes[name] = {"loader": "REJECTED", "error": str(error)}
    read_by_code = all(row["loader"] == "REJECTED" for row in probes.values())
    return {
        "hypothesis": "H9: bloque `serving` del yaml de la lane = contrato-mentira que ningun codigo lee",
        "verified_at": "src/rag/structural_neighbor_coverage.py:138-142",
        "mutation_probes": probes,
        "read_by_code": read_by_code,
        "verdict": "H9_FALSIFIED" if read_by_code else "H9_CONFIRMED",
        "action_taken": (
            "config/structural_neighbor_coverage_v1.yaml NO se toca (contrato "
            "vivo: cualquiera de las 3 mutaciones mata la lane). Lo corregido es "
            "el SPEC (evals/s287_tres_vias_design_brief_v1.md, bloque de "
            "reconciliacion V1-4)."
        )
        if read_by_code
        else "pendiente: actualizar el comentario del yaml",
        "semantics": (
            "El bloque NO significa «la lane no se sirve» (se sirve: el flag "
            "STRUCTURAL_NEIGHBOR_COVERAGE lo gobierna el release profile). "
            "Significa que ESTE SELECTOR jamas estampa `coverage_validated` por "
            "su cuenta — la atestacion la pone `_attest` aguas abajo. El "
            "contrato es correcto; lo que inducia a error era leerlo como estado "
            "de la lane."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)

    questions = dev_questions()
    if len(questions) != 39:
        raise RuntimeError(f"expected 39 dev golds, found {len(questions)}")

    with tempfile.TemporaryDirectory(prefix="s287_facet_gates_") as workspace:
        baseline = Path(workspace)
        pre_paths = {}
        head_paths = {}
        blobs = {}
        for key, relative in (
            ("query_facets", QUERY_FACETS_REL),
            ("evidence_facets", EVIDENCE_FACETS_REL),
            ("evidence_cards", EVIDENCE_CARDS_REL),
        ):
            pre_data = _blob(PRE_LEVER_COMMIT, relative)
            head_data = _blob("HEAD", relative)
            pre_path = baseline / f"pre_{Path(relative).name}"
            head_path = baseline / f"head_{Path(relative).name}"
            pre_path.write_bytes(pre_data)
            head_path.write_bytes(head_data)
            pre_paths[key] = pre_path
            head_paths[key] = head_path
            blobs[relative] = {
                "pre_lever_sha256_lf": _sha256_lf(pre_data),
                "head_sha256_lf": _sha256_lf(head_data),
                "worktree_sha256_lf": _sha256_lf((ROOT / relative).read_bytes()),
            }
        post_paths = {
            "query_facets": ROOT / QUERY_FACETS_REL,
            "evidence_facets": ROOT / EVIDENCE_FACETS_REL,
            "evidence_cards": ROOT / EVIDENCE_CARDS_REL,
        }
        arms = {"pre": pre_paths, "post": post_paths}

        result_a = gate_a(questions, pre_paths["query_facets"], post_paths["query_facets"])
        result_c = gate_c(questions, pre_paths["query_facets"], post_paths["query_facets"])
        if result_a["verdict"] != "PASS":
            payload = {
                "instrument": "s287_facet_gates_v2",
                "model_calls": 0,
                "database_writes": 0,
                "config_blobs": blobs,
                "gate_a": result_a,
                "gate_b": {"verdict": "NOT_RUN", "reason": "gate_a STOP"},
                "gate_b_serving": {"verdict": "NOT_RUN", "reason": "gate_a STOP"},
                "gate_c": result_c,
                "verdict": "STOP",
            }
            args.out.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({"gate_a": result_a["verdict"], "stop": True}, indent=1))
            return 1

        run = yaml.safe_load(RUN_V3.read_text(encoding="utf-8"))
        golds = {
            qid: next(row for row in run["per_gold"] if row["qid"] == qid)
            for qid in PROBE_QIDS
        }
        lane_config = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        seed_ids = {
            qid: [
                str(value) for value in gold["topk_ids"][: lane_config["max_seeds"]]
            ]
            for qid, gold in golds.items()
        }

        connection = psycopg2.connect(
            os.environ["DATABASE_URL"],
            connect_timeout=20,
            application_name="s287_facet_gates_readonly",
        )
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        fetched: dict[str, dict[str, Any]] = {}
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='3s'"
            )
            cursor.execute(
                "SELECT (SELECT count(*) FROM public.chunks_v2) AS chunks, "
                "(SELECT count(*) FROM public.documents) AS documents"
            )
            snapshot = dict(cursor.fetchone())
            for qid in PROBE_QIDS:
                hydrated = _hydrate(cursor, seed_ids[qid])
                fetched[qid] = {
                    "seeds": [hydrated[chunk_id] for chunk_id in seed_ids[qid]],
                    "candidates": _fetch_neighbors(
                        cursor, seed_ids[qid], lane_config["max_gap"]
                    ),
                }
        connection.rollback()
        connection.close()

        probes = {
            qid: {
                "qid": qid,
                "question": golds[qid]["question"],
                "run_v3_hist": golds[qid].get("hist"),
                "run_v3_appended_n": golds[qid].get("appended_n"),
                "seed_ids": seed_ids[qid],
                "candidate_rows_fetched": len(fetched[qid]["candidates"]),
                "seeds": fetched[qid]["seeds"],
                "candidates": fetched[qid]["candidates"],
                "arms": _probe_arms(
                    golds[qid]["question"],
                    fetched[qid]["seeds"],
                    fetched[qid]["candidates"],
                    arms,
                ),
            }
            for qid in PROBE_QIDS
        }
        result_b = gate_b(probes)
        result_b_serving = gate_b_serving(probes, pre_paths, head_paths)

        payload = {
            "instrument": "s287_facet_gates_v2",
            "scope": {
                "model_calls": 0,
                "database_writes": 0,
                "lane_code_touched": False,
                "golds_touched": False,
                "read_only_database": True,
            },
            "config_blobs": blobs,
            "pre_lever_commit": PRE_LEVER_COMMIT,
            "lane_config": {
                "path": DEFAULT_CONFIG.relative_to(ROOT).as_posix(),
                "max_seeds": lane_config["max_seeds"],
                "max_gap": lane_config["max_gap"],
                "max_anchors": lane_config["max_anchors"],
                "sha256_lf": _sha256_lf(DEFAULT_CONFIG.read_bytes()),
            },
            "database_snapshot": snapshot,
            "seed_source": {
                "artifact": RUN_V3.relative_to(ROOT).as_posix(),
                "qids": list(PROBE_QIDS),
                "field": "topk_ids",
            },
            "amendment": {
                "id": "s287_facet_F2_resealed",
                "pre_registration_before": [TARGET_QID],
                "pre_registration_after": sorted(PRE_REGISTERED_CHANGED_QIDS),
                "reason": (
                    "cat005 es miembro genuino de la clase (comparativa de "
                    "variantes); el pre-registro original la dejo sin contar. "
                    "El trigger ES natural se conserva (anti-overfit) y cat005 "
                    "entra como CONTROL PROTEGIDO."
                ),
                "declared_in": (
                    "evals/s287_facet_lever_design_brief_v1.md "
                    "(bloque ENMIENDA post-STOP)"
                ),
                "rejected_alternative": (
                    "mutilar los triggers F4 para forzar el diff a {cat022}"
                ),
            },
            "fix": {
                "id": "s287_facet_fix_post_stop_b2",
                "change": (
                    "config/evidence_coverage_facets_v4.yaml :: "
                    "variant_attribute_matrix.required_any "
                    "[bit, incorporada, version] -> [bit, incorporada]"
                ),
                "version_still_in_terms": True,
                "reason": (
                    "`version` es homografo: en una declaracion UE de "
                    "conformidad casa con la EDICION DE UNA NORMA («respecto a "
                    "la version EN 60079-0:2009») y sostenia sola el "
                    "fail-closed sobre texto normativo (STOP del control "
                    "cat005). Solo pierde el poder de VETO; sigue contando "
                    "para min_distinct_terms."
                ),
                "declared_in": (
                    "evals/s287_facet_lever_design_brief_v1.md "
                    "(bloque FIX post-STOP-b2)"
                ),
                "rejected_alternatives": [
                    "quitar `version` tambien de `terms` (pierde vocabulario "
                    "real de la clase sin ganar nada)",
                    "negative-lookahead contra `EN 6xxxx`/«norma» (anti-patron "
                    "que codifica un documento; el validador prohibe digitos)",
                    "min_distinct_terms 3 global (toca los 5 arquetipos "
                    "pre-lever sellados y NO cerraba el leak: el texto "
                    "normativo casaba 3 terminos)",
                ],
            },
            "h9_serving_block_reconciliation": h9_serving_block_reconciliation(
                baseline
            ),
            "gate_a": result_a,
            "gate_b": result_b,
            "gate_b_serving": result_b_serving,
            "gate_c": result_c,
            "verdict": (
                "PASS"
                if result_a["verdict"]
                == result_b["verdict"]
                == result_b_serving["verdict"]
                == result_c["verdict"]
                == "PASS"
                else "STOP"
            ),
            "limitations": [
                "Gates deterministas: NO miden PASS ni sintesis (0 llamadas a modelo).",
                "La lane sigue shadow-only (serving.enabled=false); esto no cambia OK oficial.",
                "El brazo pre usa los blobs de PRE_LEVER_COMMIT (0791a319, padre de "
                "7f2a251), no un checkout limpio del repo. Ancla FIJA: con `HEAD` el "
                "gate (a) se mediria contra si mismo en cuanto el lever se commitea.",
                "El gate (b.2) es mecanico + ADJUDICADO a mano: el `required_any` es "
                "vocabulario, no semantica, asi que la llamada de «ruido generico» la "
                "hace una persona sobre el contenido volcado y queda anclada por id en "
                "CONTROL_ADJUDICATIONS (vacio tras el fix: cat005 selecciona 0).",
                "El gate (b-serving) cruza attest/append/serve con el fetcher inyectado: "
                "prueba que la fila LLEGA al generador con el valor en el span, NO que "
                "el generador lo use (eso es sintesis => smoke pagado).",
                "El gate (b-serving) juzga sobre la vista SIN expansion de fila logica "
                "(conservadora): LOGICAL_RECORD_COVERAGE solo puede agrandar spans.",
                "El gate (b.1) exige que ALGUNA ancla sea celda IR pre-declarada, no "
                "que TODAS lo sean: revisar el volcado de cada ancla. GAP ABIERTO "
                "declarado: el rank-2 de cat022 (255948d3, «# Tablas» de MNDT723_40-40U) "
                "sigue pasando el discriminativo por una frase de comparativa GENUINA en "
                "su cola («S40/40UB ... Prueba incorporada (BIT)»); es un chunk MIXTO de "
                "un manual hermano, y filtrarlo pide un criterio de pureza-de-chunk "
                "(TOC-ness) o de doc-matching = otro lever, no este.",
            ],
        }
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n",
        encoding="utf-8",
    )
    target = result_b["probes"][TARGET_QID]
    control = result_b["probes"][CONTROL_QID]
    print(
        json.dumps(
            {
                "gate_a": result_a["verdict"],
                "gate_a_changed": result_a["changed_qids"],
                "gate_b": result_b["verdict"],
                "gate_b_target": {
                    "qid": TARGET_QID,
                    "verdict": target["verdict"],
                    "pre_selected": target["pre_selected_ids"],
                    "post_selected": target["post_selected_ids"],
                    "expected_prefix_hits": target[
                        "post_selected_matching_expected_prefixes"
                    ],
                },
                "gate_b_control": {
                    "qid": CONTROL_QID,
                    "verdict": control["verdict"],
                    "mechanical_verdict": control["mechanical_verdict"],
                    "pre_selected": control["pre_selected_ids"],
                    "post_selected": control["post_selected_ids"],
                    "control_untouched": control["control_untouched"],
                    "all_anchors_satisfy_required_any": control[
                        "all_anchors_satisfy_required_any"
                    ],
                    "generic_noise_anchor_ids": control["generic_noise_anchor_ids"],
                    "unadjudicated_anchor_ids": control["unadjudicated_anchor_ids"],
                    "stale_adjudication_ids": control["stale_adjudication_ids"],
                },
                "gate_b_serving": result_b_serving["verdict"],
                "gate_b_serving_target": result_b_serving["target"],
                "gate_b_serving_control": result_b_serving["control"],
                "gate_c": result_c["verdict"],
                "verdict": payload["verdict"],
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
