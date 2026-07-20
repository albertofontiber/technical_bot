#!/usr/bin/env python3
"""S274 P2 — probe CONSOLIDADO C+D con brazos de ablación (el probe #4, ÚNICO;
prereg ejecutable: evals/s274_bloquesCD_prereg_v2.yaml §P2 — leer ANTES de tocar esto).

Brazos EXACTOS del prereg (Sol-M3, atribución por brazo; Sol-C1 banking solo-desplegable):

  A0         OFF-base: 7 flags s274 off, MUST_PRESERVE_CONTRACT=on (estado prod
             DEC-131). hp017 con GENERACIÓN FRESCA K=3 (base pareada de C1);
             cat018/hp002/hp011 apply-side sobre los borradores OFF ALMACENADOS del
             probe v3 (evals/s270_etapa2_probe_v3_replicas_v1.jsonl, SHA-pineados).
  A-C1       COVERAGE_MANDATORY_CALLOUT + MP_MANDATORY_VERB_TRIGGER (PAR DECLARADO:
             la conversión 0d6a exige ambos; atribución interna vía good_form
             por-átomo en el trace). hp017 K=3 generación fresca PAREADA mismo-día
             con A0 (la card cambia la VISTA servida ⇒ cambia la generación).
  A-C2       MP_SERVED_BINDING (obl_2f5d, hp011) apply-side.
  A-D1a      MP_DEFLINE_EQ (cat018) apply-side.
  A-D1b-det  = A0 (la familia F-RELATION no tiene brazo det; se declara para la
             resta — alias, 0 filas nuevas).
  A-D1b-hyb  MP_HYBRID_DETECT: apply-side con Haiku SOLO en cat018/hp002/hp017
             (≤2 llamadas/respuesta = presupuesto de PROD, lo desplegable).
  A-D1c      MP_STEM_BINDING (hp002) apply-side.
  A-D2       MP_DISTINCTIVE_TOKEN (cat018, obl_7bba) apply-side.
  A-ALL-det  todos los flags MENOS MP_HYBRID_DETECT (lo shippeable sin Haiku);
             hp017 REUSA los borradores frescos de A-C1.
  A-ALL      todos los flags (híbrido runtime incluido); hp017 reusa A-C1.

Cada brazo procesa los 4 qids ×K=3 (los gates transversales — protegidas, 0
conflictos, anclas s104+s105, diagramas — necesitan la matriz completa); la
generación fresca existe SOLO donde el prereg la exige (hp017 en A0/A-C1).

Scoring: matcher determinista NFKD s163 (scripts/s270_etapa2_probe.score_answer —
el MISMO instrumento del probe v3: obligaciones s235 + conflictos + citas +
merged_warning_block + disclosure opción-1 DEC-128, sin cambios). 0 juez.

Gates por brazo (prereg §P2.gates): conversión estable ≥2/3 por candidato vs A0 ·
protegidas estables-en-A0 no caen · 0 conflictos nuevos · anclas per-fact pareadas
(pérdida estable = STOP; STOP duro en la unión s104+s105; ganancias del anexo se
REPORTAN etiquetadas — el anexo es monotónico por diseño) · retrieval-invariante en
A-C1 (ids/orden/contenido del contexto idénticos OFF/ON; la card cambia la VISTA,
no el pool) · VISUAL_ASSETS_REGISTRY=off PINEADO ⇒ el anexo no puede introducir
diagramas (se asserta por fila); result["diagrams"] se versiona POR BRAZO y el
delta OFF/ON del modelo se reporta etiquetado como informativo (Sol-M5).

Stop-rule: STOP en cualquier gate de daño ⇒ el fix causante queda CERRADO sin
re-run (no hay probe #5); las conversiones de fixes limpios se conservan.
Banking (Sol-C1): solo lo DESPLEGABLE — det-only bancable con A-ALL-det;
conversiones que exijan el híbrido, solo si MP_HYBRID_DETECT se decide shippear.

Preflight por defecto (0 llamadas pagadas, 0 DB); ``--execute --env-file <ruta>``
para pagar (techo $6; checkpoint resumible por brazo×gold×réplica; no-retry).
La ejecución exige el gate P1 (evals/s274_stage1_v9_gate_v1.yaml): un fix NO-GO en
P1 no entra al probe (su brazo se SALTA y en los brazos A-ALL* su flag se retira).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s270_etapa2_probe as base  # noqa: E402

PREREG = ROOT / "evals/s274_bloquesCD_prereg_v2.yaml"
P1_GATE = ROOT / "evals/s274_stage1_v9_gate_v1.yaml"
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
STORED_DRAFTS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
FACTLEVEL = ROOT / "evals/s100_factlevel_full.yaml"
REPLICAS = ROOT / "evals/s274_probeCD_replicas_v1.jsonl"
OUT = ROOT / "evals/s274_probeCD_result_v1.json"
RESULT_SCHEMA = "s274_probeCD_result_v1"
RUNNER_FILE = Path(__file__)

QIDS = base.QIDS                      # ("cat018", "hp002", "hp011", "hp017")
REPLICATES = base.REPLICATES          # (1, 2, 3)
STABLE_MIN = base.STABLE_MIN          # >=2/3
COST_CEILING_USD = 6.00               # prereg v2 §P2
HYBRID_PRICE_IN = 1.0                 # USD/MTok Haiku 4.5
HYBRID_PRICE_OUT = 5.0
HYBRID_EST_IN_TOKENS = 2200           # por llamada (cota del preflight v3)
HYBRID_EST_OUT_TOKENS = 1500
PROBE_NUMBER = 4

ALL_FLAGS = (
    "COVERAGE_MANDATORY_CALLOUT", "MP_SERVED_BINDING", "MP_DEFLINE_EQ",
    "MP_HYBRID_DETECT", "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
    "MP_MANDATORY_VERB_TRIGGER",
)
C1_PAIR = ("COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER")
HYBRID_QIDS = ("cat018", "hp002", "hp017")   # prereg: A-D1b-hyb sin hp011
FRESH_QID = "hp017"

# Brazos EXACTOS del prereg v2 §P2.arms (orden de ejecución = orden declarado).
ARMS: dict[str, dict[str, Any]] = {
    "A0": {"flags": (), "fresh": (FRESH_QID,)},
    "A-C1": {"flags": C1_PAIR, "fresh": (FRESH_QID,), "pair_declared": True},
    "A-C2": {"flags": ("MP_SERVED_BINDING",)},
    "A-D1a": {"flags": ("MP_DEFLINE_EQ",)},
    "A-D1b-det": {"alias_of": "A0"},
    "A-D1b-hyb": {"flags": ("MP_HYBRID_DETECT",), "hybrid": True},
    "A-D1c": {"flags": ("MP_STEM_BINDING",)},
    "A-D2": {"flags": ("MP_DISTINCTIVE_TOKEN",)},
    "A-ALL-det": {
        "flags": tuple(f for f in ALL_FLAGS if f != "MP_HYBRID_DETECT"),
        "reuse_fresh_from": "A-C1",
    },
    "A-ALL": {"flags": ALL_FLAGS, "hybrid": True, "reuse_fresh_from": "A-C1"},
}
ARM_ORDER = (
    "A0", "A-C1", "A-C2", "A-D1a", "A-D1b-det", "A-D1b-hyb", "A-D1c", "A-D2",
    "A-ALL-det", "A-ALL",
)
# Fix de P1 que gatea cada brazo (NO-GO en P1 → el brazo se salta / el flag se
# retira de los brazos A-ALL*). A-C1 exige el PAR entero.
ARM_P1_FIXES = {
    "A-C1": C1_PAIR,
    "A-C2": ("MP_SERVED_BINDING",),
    "A-D1a": ("MP_DEFLINE_EQ",),
    "A-D1b-hyb": ("MP_HYBRID_DETECT",),
    "A-D1c": ("MP_STEM_BINDING",),
    "A-D2": ("MP_DISTINCTIVE_TOKEN",),
}

# Candidatos (los 7 synth restantes, DEC-127/131) con su check del matcher.
CANDIDATES = (
    ("obl_0d6a30948dfd", "hp017", "merged_warning_block"),
    ("obl_7bba8d03d496", "cat018", "matcher"),
    ("obl_2f5d79e354b9", "hp011", "matcher"),
    ("obl_a5d9fa1f9253", "hp002", "matcher"),
    ("obl_b2043cd4379b", "hp017", "matcher"),
    ("obl_7aa723717412", "hp017", "matcher"),
    ("obl_015f9b9aaa3a", "cat018", "matcher"),
)
PROTECTED_IDS = base.EXPECTED_PROTECTED
# STOP duro: unión de las anclas perdidas en los DOS NO-GO históricos (s104+s105)
STOP_ANCHOR_KEYS = (
    "hp005#2:misma zona o subzona", "hp006#2:ISO-X", "hp006#0:Fallo de Tierra",
)

# Flags de generación: los del probe v3 + VISUAL_ASSETS_REGISTRY=off PINEADO
# (Sol-M5: el anexo no puede introducir diagramas — estructural, se asserta).
GENERATION_ENV = dict(base.GENERATION_ENV) | {"VISUAL_ASSETS_REGISTRY": "off"}


# ─────────────────────────── helpers puros ───────────────────────────

def anchor_norm(s: str) -> str:
    """Ancla léxica determinista (patrón s163/s103): NFKD-fold + colapso."""
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def arm_effective_flags(arm: str, p1_verdicts: dict[str, str] | None) -> tuple:
    """Flags efectivos del brazo tras aplicar el gate P1 por-fix: en brazos de un
    solo fix, un NO-GO lo mata entero (skip); en A-ALL* se RETIRA solo el flag
    muerto (prereg: un NO-GO mata SOLO su fix)."""
    spec = ARMS[arm]
    flags = tuple(spec.get("flags") or ())
    if p1_verdicts is None:
        return flags
    return tuple(f for f in flags if p1_verdicts.get(f) == "GO")


def arm_skipped_by_p1(arm: str, p1_verdicts: dict[str, str] | None) -> bool:
    if p1_verdicts is None or arm not in ARM_P1_FIXES:
        return False
    return any(p1_verdicts.get(f) != "GO" for f in ARM_P1_FIXES[arm])


def checkpoint_key(arm: str, qid: str, replicate: int) -> str:
    return f"{arm}|{qid}|r{replicate}"


def appended_tail(off_answer: str, on_answer: str) -> str:
    """El anexo introducido por apply (monotónico): on = off.rstrip() + tail."""
    head = (off_answer or "").rstrip()
    if not (on_answer or "").startswith(head):
        raise RuntimeError("S274 P2 monotonía rota: on_answer no extiende el borrador")
    return on_answer[len(head):]


def assert_no_new_diagrams(off_answer: str, on_answer: str) -> None:
    """El anexo jamás introduce diagramas (VISUAL_ASSETS_REGISTRY=off pineado +
    el marcador del modelo no puede aparecer en el tail del anexo)."""
    tail = appended_tail(off_answer, on_answer)
    if "DIAGRAMAS_RELEVANTES" in tail:
        raise RuntimeError("S274 P2 el anexo introdujo un marcador de diagramas")


def stable_count(values: list[bool]) -> int:
    return sum(1 for v in values if v)


def load_anchor_facts() -> dict[str, dict[str, str]]:
    """{qid: {fact_key: valor_normalizado}} de los facts lexically_anchorable."""
    import yaml

    payload = yaml.safe_load(FACTLEVEL.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for gold in payload["per_gold"]:
        qid = str(gold["qid"])
        if qid not in QIDS:
            continue
        facts = {}
        for fact in gold.get("facts") or []:
            if not fact.get("lexically_anchorable"):
                continue
            valor = anchor_norm(str(fact.get("valor") or ""))
            if len(valor) < 2:
                continue
            facts[str(fact["key"])] = valor
        out[qid] = facts
    return out


def anchors_in_answer(answer: str, facts: dict[str, str]) -> dict[str, bool]:
    blob = anchor_norm(answer)
    return {key: valor in blob for key, valor in facts.items()}


# ─────────────────────────── prereg / P1 gate ───────────────────────────

def load_prereg() -> dict[str, Any]:
    import yaml

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("schema") != "s274_bloquesCD_prereg_v2":
        raise RuntimeError("S274 P2 prereg v2 no encontrado")
    if prereg.get("status") != "preregistered_p0_built_flagoff":
        raise RuntimeError("S274 P2 prereg con status inesperado")
    p2 = next(ph for ph in prereg["phases"] if ph["id"] == "P2")
    if float(p2["cost_ceiling_usd"]) != COST_CEILING_USD:
        raise RuntimeError("S274 P2 techo de coste ≠ prereg")
    declared = set(p2["arms"])
    if declared != set(ARMS):
        raise RuntimeError(
            f"S274 P2 brazos ≠ prereg: {sorted(declared ^ set(ARMS))}"
        )
    return prereg


def verify_pins(prereg: dict[str, Any]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for rel, expected in prereg["frozen_inputs_sha256_lf"].items():
        actual = base.normalized_sha(ROOT / rel)
        if actual != expected:
            raise RuntimeError(f"S274 P2 drift de insumo congelado: {rel}")
        verified[rel] = actual
    return verified


def load_p1_verdicts(required: bool) -> dict[str, str] | None:
    import yaml

    if not P1_GATE.exists():
        if required:
            raise RuntimeError(
                "S274 P2 exige el gate P1 (evals/s274_stage1_v9_gate_v1.yaml) — "
                "corre scripts/s274_mutation_harness_v9.py primero"
            )
        return None
    gate = yaml.safe_load(P1_GATE.read_text(encoding="utf-8"))
    if gate.get("schema") != "s274_stage1_v9_gate_v1":
        raise RuntimeError("S274 P2 gate P1 con schema inesperado")
    verdicts = dict(gate.get("verdict_by_fix") or {})
    if set(verdicts) != set(ALL_FLAGS):
        raise RuntimeError("S274 P2 gate P1 sin veredicto para los 7 flags")
    return verdicts


# ─────────────────────────── contexto / entorno por brazo ───────────────────────────

def export_generation_env() -> None:
    os.environ.update(GENERATION_ENV)
    for flag in ALL_FLAGS:
        os.environ.pop(flag, None)


def _assert_visual_assets_off() -> None:
    from src import config

    if os.environ.get("VISUAL_ASSETS_REGISTRY") != "off":
        raise RuntimeError("S274 P2 VISUAL_ASSETS_REGISTRY debe estar pineado off")
    if config.VISUAL_ASSETS_REGISTRY:
        raise RuntimeError(
            "S274 P2 config.VISUAL_ASSETS_REGISTRY activo (import antes del pin)"
        )


class arm_env:
    """Flags s274 del brazo (+ MUST_PRESERVE_CONTRACT opcional) con restauración."""

    def __init__(self, flags: tuple, contract_on: bool = False) -> None:
        self.flags = flags
        self.contract_on = contract_on
        self._prev: dict[str, str | None] = {}

    def __enter__(self) -> "arm_env":
        keys = list(ALL_FLAGS) + ["MUST_PRESERVE_CONTRACT"]
        self._prev = {k: os.environ.get(k) for k in keys}
        for flag in ALL_FLAGS:
            os.environ.pop(flag, None)
        for flag in self.flags:
            os.environ[flag] = "on"
        os.environ["MUST_PRESERVE_CONTRACT"] = "on" if self.contract_on else "off"
        return self

    def __exit__(self, *exc: Any) -> None:
        for key, val in self._prev.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def enrich_callout_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """C1: deriva ``mandatory_callout_cards`` (campo PROPIO, receipt propio) sobre
    los chunks de coverage validados del contexto CONGELADO. No cambia ids, orden
    ni content (retrieval-invariante por construcción — se verifica aparte)."""
    from src.rag import post_rerank_coverage as prc

    out: list[dict[str, Any]] = []
    for chunk in chunks:
        if prc.is_validated_coverage_chunk(chunk):
            cards = prc._build_mandatory_callout_cards(chunk)
            if cards:
                chunk = dict(chunk)
                chunk["mandatory_callout_cards"] = cards
        out.append(chunk)
    return out


def arm_context(qid: str, chunks: list[dict[str, Any]], flags: tuple) -> list[dict]:
    if "COVERAGE_MANDATORY_CALLOUT" in flags:
        return enrich_callout_chunks(chunks)
    return chunks


def retrieval_invariant_report(
    base_chunks: list[dict[str, Any]], arm_chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Gate A-C1: ids/orden/contenido idénticos (la card cambia la VISTA, no el
    pool); el ÚNICO delta permitido es el campo propio mandatory_callout_cards."""
    ids_base = [str(c.get("id") or "") for c in base_chunks]
    ids_arm = [str(c.get("id") or "") for c in arm_chunks]
    content_equal = all(
        a.get("content") == b.get("content")
        for a, b in zip(base_chunks, arm_chunks)
    )
    extra_fields = sorted({
        k for a, b in zip(base_chunks, arm_chunks)
        for k in set(b) - set(a)
    })
    ok = (
        ids_base == ids_arm and content_equal
        and extra_fields in ([], ["mandatory_callout_cards"])
    )
    return {
        "ids_identical": ids_base == ids_arm,
        "content_identical": content_equal,
        "extra_fields": extra_fields,
        "pass": ok,
    }


# ─────────────────────────── ejecución por fila ───────────────────────────

def load_stored_drafts() -> dict[tuple[str, int], dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for line in STORED_DRAFTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[(str(row["qid"]), int(row["replicate"]))] = row
    missing = [
        (q, r) for q in QIDS for r in REPLICATES if (q, r) not in rows
    ]
    if missing:
        raise RuntimeError(f"S274 P2 faltan borradores almacenados: {missing}")
    return rows


def hybrid_cost_usd(hybrid_usage: dict[str, Any]) -> float:
    return (
        (hybrid_usage.get("input_tokens", 0) or 0) * HYBRID_PRICE_IN
        + (hybrid_usage.get("output_tokens", 0) or 0) * HYBRID_PRICE_OUT
    ) / 1_000_000


def apply_arm_to_draft(
    arm: str,
    qid: str,
    question: str,
    chunks: list[dict[str, Any]],
    draft: str,
    flags: tuple,
) -> tuple[str, dict[str, Any] | None]:
    """apply_must_preserve_contract con los flags del brazo. En brazos híbridos,
    hp011 corre determinista (prereg: A-D1b-hyb = cat018/hp002/hp017 con Haiku)."""
    from src.rag import must_preserve as mp

    effective = flags
    if "MP_HYBRID_DETECT" in flags and qid not in HYBRID_QIDS:
        effective = tuple(f for f in flags if f != "MP_HYBRID_DETECT")
    with arm_env(effective, contract_on=True):
        on_answer, trace = mp.apply_must_preserve_contract(question, chunks, draft)
    assert_no_new_diagrams(draft, on_answer)
    return on_answer, trace


def generate_fresh_draft(
    qid: str, question: str, chunks: list[dict[str, Any]], flags: tuple
) -> dict[str, Any]:
    """Generación fresca (solo hp017 en A0/A-C1): flags de VISTA del brazo activos
    durante la generación (C1 cambia el contexto servido), contrato OFF (el apply
    del brazo corre aparte, mismo patrón pareado del probe v3)."""
    from src.rag import generator

    with arm_env(flags, contract_on=False):
        result = generator.generate_answer(question, chunks)
    if result.get("stop_reason") != "end_turn":
        raise RuntimeError(
            f"S274 P2 {qid} stop_reason={result.get('stop_reason')!r} "
            "(contrato: end_turn; la réplica no se persiste ni se re-llama)"
        )
    return result


def run_row(
    arm: str,
    qid: str,
    replicate: int,
    rows: dict[str, dict[str, Any]],
    stored: dict[tuple[str, int], dict[str, Any]],
    fresh_bank: dict[tuple[str, str, int], dict[str, Any]],
) -> dict[str, Any]:
    spec = ARMS[arm]
    flags = tuple(spec.get("_effective_flags", spec.get("flags") or ()))
    if "MP_HYBRID_DETECT" in flags and qid not in HYBRID_QIDS:
        # prereg: A-D1b-hyb/A-ALL con Haiku SOLO en cat018/hp002/hp017
        flags = tuple(f for f in flags if f != "MP_HYBRID_DETECT")
    question = rows[qid]["question"]
    base_chunks = base.served_chunks(rows[qid]["context"])
    chunks = arm_context(qid, base_chunks, flags)
    row: dict[str, Any] = {
        "arm": arm,
        "qid": qid,
        "replicate": replicate,
        "flags": sorted(flags),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cost_usd": 0.0,
    }
    fresh_qids = spec.get("fresh") or ()
    reuse_from = spec.get("reuse_fresh_from")
    if reuse_from is not None and "COVERAGE_MANDATORY_CALLOUT" not in flags:
        # si el par C1 murió en P1, la base fresca correcta es la vista OFF (A0)
        reuse_from = "A0"
    if qid in fresh_qids:
        result = generate_fresh_draft(qid, question, chunks, flags)
        draft = str(result["answer"])
        input_tokens = int(result.get("input_tokens") or 0)
        output_tokens = int(result.get("output_tokens") or 0)
        row.update({
            "draft_source": "fresh",
            "diagrams": list(result.get("diagrams") or []),
            "usage": {"input_tokens": input_tokens,
                      "output_tokens": output_tokens},
            "cost_usd": round(base.cost_usd(input_tokens, output_tokens), 8),
        })
    elif reuse_from is not None and qid == FRESH_QID:
        source = fresh_bank.get((reuse_from, qid, replicate))
        if source is None:
            raise RuntimeError(
                f"S274 P2 {arm} reusa hp017 de {reuse_from} y no está en el "
                "checkpoint — el orden de brazos es el declarado"
            )
        draft = str(source["off_answer"])
        row.update({
            "draft_source": f"reused_{reuse_from}",
            "diagrams": list(source.get("diagrams") or []),
        })
    else:
        draft = str(stored[(qid, replicate)]["off_answer"])
        row["draft_source"] = "stored_v3"
    on_answer, trace = apply_arm_to_draft(
        arm, qid, question, chunks, draft, flags
    )
    row.update({
        "off_answer": draft,
        "on_answer": on_answer,
        "must_preserve_trace": trace,
    })
    if trace and trace.get("hybrid"):
        usage = dict(trace["hybrid"].get("usage") or {})
        row["hybrid_usage"] = usage
        row["cost_usd"] = round(row["cost_usd"] + hybrid_cost_usd(usage), 8)
    if arm == "A-C1" and qid == FRESH_QID:
        row["retrieval_invariant"] = retrieval_invariant_report(
            base_chunks, chunks
        )
    return row


# ─────────────────────────── scoring y agregación ───────────────────────────

def score_rows(
    raw_rows: list[dict[str, Any]], items: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    scored = []
    for row in raw_rows:
        item = items[row["qid"]]
        scored.append({
            **row,
            "off_score": base.score_answer(row["off_answer"], item),
            "on_score": base.score_answer(row["on_answer"], item),
        })
    return scored


def candidate_covered(score_row: dict[str, Any], oblid: str, check: str) -> bool:
    if check == "merged_warning_block":
        return bool(score_row.get("merged_warning_block_covered"))
    return oblid in set(score_row.get("covered_obligation_ids") or [])


def aggregate(
    scored: list[dict[str, Any]],
    items: dict[str, dict[str, Any]],
    anchor_facts: dict[str, dict[str, str]],
    p1_verdicts: dict[str, str] | None,
    actual_cost: float,
) -> dict[str, Any]:
    """Agregación por brazo vs la base A0 (pareada): conversiones estables ≥2/3,
    protegidas, conflictos nuevos, anclas per-fact, diagramas. Pura (testeable)."""
    by_arm: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in scored:
        by_arm.setdefault(row["arm"], {}).setdefault(row["qid"], []).append(row)
    if "A0" not in by_arm:
        raise RuntimeError("S274 P2 falta el brazo base A0")
    for arm, per_qid in by_arm.items():
        for qid in QIDS:
            if len(per_qid.get(qid) or []) != len(REPLICATES):
                raise RuntimeError(f"S274 P2 faltan réplicas de {arm}:{qid}")

    def on_counts(arm: str, qid: str, pred) -> int:
        return stable_count([pred(r["on_score"]) for r in by_arm[arm][qid]])

    def anchors_stable(arm: str, qid: str) -> dict[str, bool]:
        facts = anchor_facts.get(qid) or {}
        runs = [
            anchors_in_answer(r["on_answer"], facts) for r in by_arm[arm][qid]
        ]
        return {
            key: sum(1 for run in runs if run.get(key)) >= STABLE_MIN
            for key in facts
        }

    def diagrams_stable(arm: str, qid: str) -> list[str]:
        runs = [
            {str(d) for d in (r.get("diagrams") or [])} for r in by_arm[arm][qid]
        ]
        universe = set().union(*runs) if runs else set()
        return sorted(
            d for d in universe
            if sum(1 for run in runs if d in run) >= STABLE_MIN
        )

    protected_base = {
        oblid: on_counts(
            "A0", qid,
            lambda s, o=oblid: o in set(s.get("covered_obligation_ids") or []),
        )
        for oblid, qid in (
            (o, q) for o in sorted(PROTECTED_IDS)
            for q in QIDS
            if any(
                str(ob["obligation_id"]) == o for ob in items[q]["obligations"]
            )
        )
    }
    conflict_ids = {
        str(c["conflict_id"]): qid
        for qid in QIDS for c in items[qid]["conflicts"]
    }
    obl_qid = {
        str(o["obligation_id"]): qid
        for qid in QIDS for o in items[qid]["obligations"]
    }

    arms_report: dict[str, Any] = {}
    stop_hits: list[dict[str, Any]] = []
    for arm in ARM_ORDER:
        if arm not in by_arm:
            arms_report[arm] = {
                "status": (
                    "alias_of_A0" if ARMS[arm].get("alias_of") == "A0"
                    else "skipped"
                ),
            }
            continue
        report: dict[str, Any] = {"status": "measured"}
        # conversiones por candidato vs A0
        conv: dict[str, Any] = {}
        for oblid, qid, check in CANDIDATES:
            on_n = on_counts(
                arm, qid, lambda s, o=oblid, c=check: candidate_covered(s, o, c)
            )
            base_n = on_counts(
                "A0", qid, lambda s, o=oblid, c=check: candidate_covered(s, o, c)
            )
            conv[oblid] = {
                "qid": qid, "check": check,
                "arm_on": on_n, "a0_on": base_n,
                "stable_conversion": (
                    arm != "A0" and on_n >= STABLE_MIN
                    and (len(REPLICATES) - base_n) >= STABLE_MIN
                ),
            }
        report["candidates"] = conv
        report["stable_conversions"] = sorted(
            o for o, d in conv.items() if d["stable_conversion"]
        )
        if arm != "A0":
            # protegidas estables-en-A0 no caen
            fallen = []
            for oblid, base_n in protected_base.items():
                if base_n < STABLE_MIN:
                    continue
                qid = obl_qid[oblid]
                arm_n = on_counts(
                    arm, qid,
                    lambda s, o=oblid: o in set(
                        s.get("covered_obligation_ids") or []
                    ),
                )
                if (len(REPLICATES) - arm_n) >= STABLE_MIN:
                    fallen.append(oblid)
            report["protected_fallen"] = sorted(fallen)
            # conflictos nuevos estables
            new_conflicts = []
            for cid, qid in sorted(conflict_ids.items()):
                arm_n = on_counts(
                    arm, qid,
                    lambda s, c=cid: c in set(s.get("unsafe_conflict_ids") or []),
                )
                base_n = on_counts(
                    "A0", qid,
                    lambda s, c=cid: c in set(s.get("unsafe_conflict_ids") or []),
                )
                if arm_n >= STABLE_MIN and (len(REPLICATES) - base_n) >= STABLE_MIN:
                    new_conflicts.append(cid)
            report["new_stable_conflicts"] = new_conflicts
            # anclas per-fact pareadas
            anchors: dict[str, Any] = {}
            lost_all: list[str] = []
            gained_all: list[str] = []
            for qid in QIDS:
                a0_stable = anchors_stable("A0", qid)
                arm_stable = anchors_stable(arm, qid)
                lost = sorted(
                    k for k, v in a0_stable.items() if v and not arm_stable.get(k)
                )
                gained = sorted(
                    k for k, v in arm_stable.items() if v and not a0_stable.get(k)
                )
                anchors[qid] = {"lost": lost, "gained": gained}
                lost_all += lost
                gained_all += gained
            hard = sorted(set(lost_all) & set(STOP_ANCHOR_KEYS))
            report["anchors"] = {
                "per_qid": anchors,
                "lost": sorted(lost_all),
                "gained_reported_informative": sorted(gained_all),
                "stop_hard_union_s104_s105": hard,
            }
            # diagramas versionados por brazo (delta informativo, Sol-M5)
            report["diagrams"] = {
                qid: diagrams_stable(arm, qid) for qid in QIDS
            }
            if any(r.get("draft_source") == "fresh" for q in QIDS
                   for r in by_arm[arm][q]):
                report["diagrams_delta_vs_A0_informative"] = {
                    qid: {
                        "a0": diagrams_stable("A0", qid),
                        "arm": diagrams_stable(arm, qid),
                    }
                    for qid in (FRESH_QID,)
                }
            if arm == "A-C1":
                inv = [
                    r.get("retrieval_invariant") for q in (FRESH_QID,)
                    for r in by_arm[arm][q] if r.get("retrieval_invariant")
                ]
                report["retrieval_invariant"] = {
                    "rows": inv,
                    "pass": bool(inv) and all(i["pass"] for i in inv),
                }
            damage = bool(
                report["protected_fallen"] or report["new_stable_conflicts"]
                or report["anchors"]["lost"]
                or (arm == "A-C1"
                    and not report["retrieval_invariant"]["pass"])
            )
            report["damage_gates"] = {
                "protected": not report["protected_fallen"],
                "new_conflicts": not report["new_stable_conflicts"],
                "anchors_lost": not report["anchors"]["lost"],
                **({"retrieval_invariant":
                    report["retrieval_invariant"]["pass"]}
                   if arm == "A-C1" else {}),
                "pass": not damage,
            }
            if damage:
                stop_hits.append({
                    "arm": arm,
                    "fixes_closed": sorted(
                        ARM_P1_FIXES.get(arm, ARMS[arm].get("flags") or ())
                    ),
                })
        arms_report[arm] = report

    hybrid_conversions = sorted(
        set(arms_report.get("A-ALL", {}).get("stable_conversions") or [])
        - set(arms_report.get("A-ALL-det", {}).get("stable_conversions") or [])
    )
    return {
        "per_arm": arms_report,
        "p1_verdicts": p1_verdicts,
        "protected_base_a0": protected_base,
        "stop_rule_hits": stop_hits,
        "banking": {
            "rule": "Sol-C1: solo lo DESPLEGABLE se bankea",
            "det_only_bankable": sorted(
                arms_report.get("A-ALL-det", {}).get("stable_conversions") or []
            ),
            "hybrid_only_requires_ship_decision": hybrid_conversions,
        },
        "actual_cost_usd": round(actual_cost, 6),
        "cost_below_ceiling": actual_cost <= COST_CEILING_USD,
    }


# ─────────────────────────── checkpoint / coste ───────────────────────────

def load_checkpoint() -> dict[str, dict[str, Any]]:
    done: dict[str, dict[str, Any]] = {}
    if REPLICAS.exists():
        for line in REPLICAS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done[checkpoint_key(row["arm"], row["qid"], int(row["replicate"]))] = row
    return done


def append_checkpoint(row: dict[str, Any]) -> None:
    with open(REPLICAS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def estimate_fresh_cost(rows: dict[str, dict[str, Any]], qid: str) -> float:
    """Coste estimado de UNA generación fresca del qid (patrón base.estimate_cost)."""
    from src.rag.generator import _assemble_system
    from src.rag.post_rerank_coverage import coverage_context_content

    row = rows[qid]
    system_chars = len(_assemble_system(row["question"]))
    context_chars = sum(
        len(coverage_context_content(c) or "") + 220 for c in row["context"]
    )
    input_tokens = int(
        (system_chars + context_chars + len(row["question"]) + 400)
        / base.CHARS_PER_TOKEN
    )
    return base.cost_usd(input_tokens, base.EXPECTED_MAX_TOKENS)


def per_arm_cost_estimate(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fresh_call = estimate_fresh_cost(rows, FRESH_QID)
    hybrid_calls = len(HYBRID_QIDS) * len(REPLICATES) * 2  # ≤2 llamadas/respuesta
    hybrid_cost = hybrid_calls * (
        HYBRID_EST_IN_TOKENS * HYBRID_PRICE_IN
        + HYBRID_EST_OUT_TOKENS * HYBRID_PRICE_OUT
    ) / 1_000_000
    per_arm = {
        "A0": {"paid_calls": len(REPLICATES),
               "est_usd": round(fresh_call * len(REPLICATES), 4)},
        "A-C1": {"paid_calls": len(REPLICATES),
                 # la card añade ≤600 chars/chunk de coverage — margen 5%
                 "est_usd": round(fresh_call * len(REPLICATES) * 1.05, 4)},
        "A-C2": {"paid_calls": 0, "est_usd": 0.0},
        "A-D1a": {"paid_calls": 0, "est_usd": 0.0},
        "A-D1b-det": {"paid_calls": 0, "est_usd": 0.0, "alias_of": "A0"},
        "A-D1b-hyb": {"paid_calls": hybrid_calls,
                      "est_usd": round(hybrid_cost, 4),
                      "haiku_calls_max": hybrid_calls},
        "A-D1c": {"paid_calls": 0, "est_usd": 0.0},
        "A-D2": {"paid_calls": 0, "est_usd": 0.0},
        "A-ALL-det": {"paid_calls": 0, "est_usd": 0.0,
                      "reuses_fresh_from": "A-C1"},
        "A-ALL": {"paid_calls": hybrid_calls,
                  "est_usd": round(hybrid_cost, 4),
                  "haiku_calls_max": hybrid_calls,
                  "reuses_fresh_from": "A-C1"},
    }
    total = round(sum(a["est_usd"] for a in per_arm.values()), 4)
    if total > COST_CEILING_USD:
        raise RuntimeError(
            f"S274 P2 estimación {total} USD supera el techo {COST_CEILING_USD}"
        )
    return {"per_arm": per_arm, "total_usd": total,
            "ceiling_usd": COST_CEILING_USD}


# ─────────────────────────── preflight / execute ───────────────────────────

def preflight(p1_required: bool = False) -> dict[str, Any]:
    prereg = load_prereg()
    pins = verify_pins(prereg)
    _assert_visual_assets_off()
    rows = base.load_freeze_rows()
    items = base.load_score_items()
    base._assert_pipeline_config()
    protected = base.protected_set(items)
    parity = base.assert_filter_parity(rows)
    stored = load_stored_drafts()
    anchor_facts = load_anchor_facts()
    p1 = load_p1_verdicts(required=p1_required)
    estimate = per_arm_cost_estimate(rows)
    plan = {}
    for arm in ARM_ORDER:
        if ARMS[arm].get("alias_of"):
            plan[arm] = {"status": "alias_of_A0"}
        elif arm_skipped_by_p1(arm, p1):
            plan[arm] = {"status": "skipped_no_go_p1",
                         "fixes": list(ARM_P1_FIXES[arm])}
        else:
            plan[arm] = {
                "status": "planned",
                "flags_effective": sorted(arm_effective_flags(arm, p1)),
            }
    return {
        "status": "PREFLIGHT_PASS",
        "probe_number": PROBE_NUMBER,
        "prereg": PREREG.relative_to(ROOT).as_posix(),
        "runner_sha256_lf": base.normalized_sha(RUNNER_FILE),
        "p1_gate": (
            {"present": p1 is not None, "verdict_by_fix": p1}
            if p1 is not None else {"present": False,
                                    "note": "P1 pendiente — la ejecución lo exige"}
        ),
        "arms_plan": plan,
        "paid_calls_planned": {
            "sonnet_fresh": 2 * len(REPLICATES),
            "haiku_max": 2 * len(HYBRID_QIDS) * len(REPLICATES) * 2,
        },
        "paid_calls_made_now": 0,
        "database_reads": 0,
        "database_writes": 0,
        "filter_parity_rows": parity,
        "stored_drafts_rows": len(stored),
        "anchor_facts": {q: sorted(f) for q, f in anchor_facts.items()},
        "protected_set": sorted(protected),
        "visual_assets_registry": "off_pinned",
        "gates": {
            "conversion_stable_min": f"{STABLE_MIN}/{len(REPLICATES)}",
            "protected_regressions_max": 0,
            "new_conflicts_max": 0,
            "anchors_lost_max": 0,
            "stop_hard_anchor_union_s104_s105": list(STOP_ANCHOR_KEYS),
            "cost_ceiling_usd": COST_CEILING_USD,
        },
        "estimated_cost": estimate,
        "frozen_inputs_verified": len(pins),
    }


def execute(env_file: Path) -> int:
    if OUT.exists():
        raise RuntimeError("S274 P2 el result ya existe — no se re-corre (no-retry)")
    prereg = load_prereg()
    pins = verify_pins(prereg)
    _assert_visual_assets_off()
    rows = base.load_freeze_rows()
    items = base.load_score_items()
    base._assert_pipeline_config()
    protected = base.protected_set(items)
    base.assert_filter_parity(rows)
    stored = load_stored_drafts()
    anchor_facts = load_anchor_facts()
    p1 = load_p1_verdicts(required=True)

    from dotenv import dotenv_values

    key = (
        (dotenv_values(env_file).get("ANTHROPIC_API_KEY") or "")
        or os.getenv("ANTHROPIC_API_KEY", "")
    ).strip()
    if not key:
        raise RuntimeError("S274 P2 ANTHROPIC_API_KEY ausente")
    os.environ["ANTHROPIC_API_KEY"] = key
    from src import config
    from src.rag import generator as gen_mod

    config.ANTHROPIC_API_KEY = key
    gen_mod.ANTHROPIC_API_KEY = key
    base._patch_no_retry()

    estimate = per_arm_cost_estimate(rows)
    fresh_upper = estimate["per_arm"]["A-C1"]["est_usd"] / len(REPLICATES)
    done = load_checkpoint()
    actual_cost = sum(float(r.get("cost_usd") or 0.0) for r in done.values())
    fresh_bank: dict[tuple[str, str, int], dict[str, Any]] = {
        (r["arm"], r["qid"], int(r["replicate"])): r
        for r in done.values() if r.get("draft_source") == "fresh"
    }
    measured_arms: list[str] = []
    for arm in ARM_ORDER:
        spec = ARMS[arm]
        if spec.get("alias_of"):
            continue
        if arm_skipped_by_p1(arm, p1):
            print(f"  {arm}: SKIP (fix NO-GO en P1)")
            continue
        spec["_effective_flags"] = arm_effective_flags(arm, p1)
        measured_arms.append(arm)
        for qid in QIDS:
            for replicate in REPLICATES:
                ckey = checkpoint_key(arm, qid, replicate)
                if ckey in done:
                    continue
                paid = qid in (spec.get("fresh") or ()) or (
                    spec.get("hybrid") and qid in HYBRID_QIDS
                )
                if paid and actual_cost + fresh_upper > COST_CEILING_USD:
                    raise RuntimeError(
                        f"S274 P2 techo de coste alcanzado ({actual_cost:.4f})"
                    )
                row = run_row(arm, qid, replicate, rows, stored, fresh_bank)
                append_checkpoint(row)
                done[ckey] = row
                if row.get("draft_source") == "fresh":
                    fresh_bank[(arm, qid, replicate)] = row
                actual_cost += float(row.get("cost_usd") or 0.0)
                print(f"  {arm}:{qid}:r{replicate} ok — acum {actual_cost:.4f} USD")

    raw = [
        done[checkpoint_key(arm, qid, rep)]
        for arm in measured_arms for qid in QIDS for rep in REPLICATES
    ]
    scored = score_rows(raw, items)
    verdictos = aggregate(scored, items, anchor_facts, p1, actual_cost)
    write_result(pins, scored, verdictos, protected, actual_cost)
    print(json.dumps(
        {
            "stop_rule_hits": verdictos["stop_rule_hits"],
            "banking": verdictos["banking"],
            "actual_cost_usd": verdictos["actual_cost_usd"],
            "result": OUT.relative_to(ROOT).as_posix(),
        },
        indent=2, ensure_ascii=False,
    ))
    return 0


def write_result(
    pins: dict[str, str],
    scored: list[dict[str, Any]],
    verdictos: dict[str, Any],
    protected: dict[str, str],
    actual_cost: float,
) -> None:
    from src.rag.visual_gold import sealed_artifact, write_json

    per_row = [
        {
            "arm": r["arm"], "qid": r["qid"], "replicate": r["replicate"],
            "flags": r["flags"], "draft_source": r["draft_source"],
            "off_score": r["off_score"], "on_score": r["on_score"],
            "diagrams": r.get("diagrams"),
            "must_preserve_trace": r.get("must_preserve_trace"),
            "hybrid_usage": r.get("hybrid_usage"),
            "retrieval_invariant": r.get("retrieval_invariant"),
            "cost_usd": r.get("cost_usd"),
        }
        for r in scored
    ]
    body = {
        "prereg": PREREG.relative_to(ROOT).as_posix(),
        "probe_number": PROBE_NUMBER,
        "runner_sha256_lf": base.normalized_sha(RUNNER_FILE),
        "design": {
            "paired_baseline_arm": "A0",
            "replicates": len(REPLICATES),
            "arms": {a: sorted(ARMS[a].get("flags") or ()) for a in ARM_ORDER},
            "hybrid_qids": list(HYBRID_QIDS),
            "fresh_generation": {"A0": [FRESH_QID], "A-C1": [FRESH_QID]},
            "visual_assets_registry": "off_pinned",
            "model": base.EXPECTED_MODEL,
            "temperature": 0,
        },
        "frozen_inputs_sha256_lf": pins,
        "protected_set": {o: protected[o] for o in sorted(protected)},
        "per_row": per_row,
        "aggregate": verdictos,
        "actual_cost_usd": round(actual_cost, 6),
        "replicas_jsonl": REPLICAS.relative_to(ROOT).as_posix(),
        "database_reads": 0,
        "database_writes": 0,
    }
    write_json(OUT, sealed_artifact(RESULT_SCHEMA, body))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=base.DEFAULT_ENV)
    args = parser.parse_args()

    export_generation_env()  # ANTES de importar el pipeline (load_dotenv override=False)
    if not args.execute:
        report = preflight(p1_required=False)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    report = preflight(p1_required=True)
    print(json.dumps(
        {"preflight": report["status"],
         "estimated_cost": report["estimated_cost"]}, indent=2,
    ))
    return execute(args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
