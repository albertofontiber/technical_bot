#!/usr/bin/env python3
"""S270 Etapa 2 (DEC-122/125/126) — probe ÚNICO del contrato must-preserve a los 4 targets.

Contrato congelado en ``evals/s270_etapa2_probe_prereg_v1.yaml`` (leer ANTES de tocar esto):
contextos CONGELADOS s113 (sin retrieval, 0 DB), generador de prod (claude-sonnet-4-6,
temperature 0, flags demo del harness), K=3 réplicas PAREADAS (una generación por réplica con
``MUST_PRESERVE_CONTRACT=off``; brazo ON = ``apply_must_preserve_contract`` determinista sobre
el MISMO borrador — la lección S242 de inestabilidad de réplica no contamina la atribución),
scoring con el matcher determinista del answer_planner (el MISMO instrumento de la foto
143/157) + los checks nuevos pre-declarados (disclosure obl_872c, merge-carrier obl_0d6a),
attestation REAL (si bloquea, se reporta ``attestation_blocked``; no se puentea), techo $6,
no-retry (max_retries=0; el checkpoint jsonl hace el re-run RESUMIBLE, nunca retry de
llamadas completadas).

Preflight por defecto (0 llamadas pagadas, 0 DB); ``--execute --env-file <ruta>`` para pagar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREREG = ROOT / "evals/s270_etapa2_probe_prereg_v1.yaml"
FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
SCORE_PACKET = ROOT / "evals/s235_direct_clause_bound_score_packet_v1.json"
REPLICAS = ROOT / "evals/s270_etapa2_probe_replicas_v1.jsonl"
OUT = ROOT / "evals/s270_etapa2_probe_result_v1.json"
DEFAULT_ENV = Path(
    r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\.env"
)

QIDS = ("cat018", "hp002", "hp011", "hp017")
REPLICATES = (1, 2, 3)
STABLE_MIN = 2  # ">=2/3" del prereg
EXPECTED_MODEL = "claude-sonnet-4-6"
EXPECTED_MAX_TOKENS = 3500
PRICING_PER_MTOK = {"input": 3.0, "output": 15.0}
COST_CEILING_USD = 6.0
CHARS_PER_TOKEN = 3.0  # estimación conservadora (ES real ~3.5-4)

# Flags de generación del prereg. src/config.py hace load_dotenv(override=False):
# el entorno del proceso es autoritativo → exportar ANTES de importar el pipeline basta.
GENERATION_ENV = {
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "GENERATOR_SELECTION_BLOCK": "on",
    "ANSWER_OBLIGATION_PLANNER": "off",
    "GENERATOR_INCLUDE_CONTEXT": "",
    "MUST_PRESERVE_CONTRACT": "off",
    "LLM_MAX_TOKENS": str(EXPECTED_MAX_TOKENS),
}

# ── población adjudicada (DEC-125; prereg §gate_eligible) ──
MERGED_ID = "obl_0d6a30948dfd"          # carrier del merge de warnings
MERGE_COMPONENT_IDS = ("obl_16637b935bd4", "obl_0d6a30948dfd")
DISCLOSURE_ID = "obl_872c35fb41d7"      # re-specced a DISCLOSURE
STRETCH_ID = "obl_2f5d79e354b9"         # hp011 selection-loss — jamás cuenta en el gate
STRETCH_FRAGMENT = 13                    # F13 servido-no-citado (s243)
DEMOTED_IDS = ("obl_07eee3300535", "obl_161564ff41bf")
GATE_ELIGIBLE = (
    ("obl_7bba8d03d496", "cat018", "matcher"),
    ("obl_015f9b9aaa3a", "cat018", "matcher"),
    ("obl_b6f6211be439", "hp002", "matcher"),
    ("obl_a5d9fa1f9253", "hp002", "matcher"),
    ("obl_b2043cd4379b", "hp017", "matcher"),
    ("obl_7aa723717412", "hp017", "matcher"),
    (MERGED_ID, "hp017", "merged_warning_block"),
    (DISCLOSURE_ID, "hp017", "disclosure_respec"),
)
EXPECTED_PROTECTED = frozenset(
    {"obl_05482a6b3f0e", "obl_0db2b9f2842a", "obl_5784f16b1a11"}
)

# ── check de disclosure (obl_872c; prereg §disclosure_respec, pre-declarado) ──
_DELAY_NOUN_RX = re.compile(r"tipos?\s+de\s+retardo|delay\s+types?")
_SIX_RX = re.compile(r"\b(?:seis|six|6)\b")
_SEVEN_RX = re.compile(r"\b(?:siete|seven|7)\b")
_DISCLOSURE_FORMULA_RX = re.compile(
    r"la prosa dice|la tabla (?:recoge|enumera|lista|indica)|discrepan\w*|"
    r"inconsistencia|inconsistente|no coincide"
)
_DISCLOSURE_WINDOW = 600


def export_generation_env() -> None:
    os.environ.update(GENERATION_ENV)


def normalized_sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


# ─────────────────────────── prereg / artefactos congelados ───────────────────────────

def load_prereg() -> dict[str, Any]:
    import yaml

    prereg = yaml.safe_load(PREREG.read_text(encoding="utf-8"))
    if prereg.get("status") != "FROZEN_BEFORE_PAID_EXECUTION":
        raise RuntimeError("S270 prereg no está congelado")
    return prereg


def verify_pins(prereg: dict[str, Any]) -> dict[str, str]:
    """Pins LF-normalizados de los insumos congelados: drift → fail-fast."""
    verified: dict[str, str] = {}
    for rel, expected in prereg["frozen_inputs_sha256_lf_normalized"].items():
        actual = normalized_sha(ROOT / rel)
        if actual != expected:
            raise RuntimeError(f"S270 drift de insumo congelado: {rel}")
        verified[rel] = actual
    return verified


def runner_pin_status(prereg: dict[str, Any]) -> str:
    expected = prereg["runner_sha256_lf_normalized"]["scripts/s270_etapa2_probe.py"]
    if expected == "PENDING_STAMP_BEFORE_EXECUTE":
        return "PENDING"
    return "MATCH" if normalized_sha(Path(__file__)) == expected else "DRIFT"


def _sealed(path: Path) -> dict[str, Any]:
    from src.rag.visual_gold import stable_sha

    value = json.loads(path.read_text(encoding="utf-8"))
    body = dict(value)
    expected = body.pop("result_sha256", None)
    if not expected or stable_sha(body) != expected:
        raise ValueError(f"sealed artifact drift: {path.name}")
    return value


def load_freeze_rows() -> dict[str, dict[str, Any]]:
    data = json.loads(FREEZE.read_text(encoding="utf-8"))
    rows = {r["qid"]: r for r in data["rows"] if r["qid"] in QIDS}
    if set(rows) != set(QIDS):
        raise RuntimeError("S270 freeze s113 no contiene los 4 targets")
    total = sum(len(rows[q]["context"]) for q in QIDS)
    if total != 51:
        raise RuntimeError(f"S270 población de chunks {total} != 51")
    for qid in QIDS:
        if len(rows[qid]["context"]) != rows[qid]["context_rows"]:
            raise RuntimeError(f"S270 context_rows inconsistente en {qid}")
    return rows


def load_score_items() -> dict[str, dict[str, Any]]:
    packet = _sealed(SCORE_PACKET)
    if packet.get("status") != "SEALED_SCORE_ONLY_OPEN_AFTER_GENERATION":
        raise RuntimeError("S270 score packet s235 con status inesperado")
    return {str(item["qid"]): item for item in packet["items"]}


# ─────────────────────────── forma servida (paridad generator) ───────────────────────────

def served_chunks(
    context: list[dict[str, Any]],
    *,
    validator: Callable[[dict], bool] | None = None,
    threshold: float | None = None,
    compatibility_lane: str | None = None,
) -> list[dict[str, Any]]:
    """El MISMO filtro de relevancia de generate_answer sobre las filas del freeze
    (sin lane de compatibilidad: se asserta su ausencia — los 51 rows son prefijo
    congelado + coverage validada). Los parámetros inyectables existen para los tests."""
    if validator is None or threshold is None or compatibility_lane is None:
        from src.rag.generator import COMPATIBILITY_LANE, RELEVANCE_THRESHOLD
        from src.rag.post_rerank_coverage import is_validated_coverage_chunk

        validator = validator or is_validated_coverage_chunk
        threshold = RELEVANCE_THRESHOLD if threshold is None else threshold
        compatibility_lane = compatibility_lane or COMPATIBILITY_LANE
    for row in context:
        if row.get("retrieval_lane") == compatibility_lane:
            raise RuntimeError("S270 fila de lane de compatibilidad inesperada en el freeze")
    return [
        row for row in context
        if (row.get("similarity", 0) or 0) >= threshold or validator(row)
    ]


def assert_filter_parity(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    """El filtro debe ser IDENTIDAD sobre el freeze (lo servido == lo congelado);
    si dropea una fila, el probe no reproduce el contexto s113 → fail-fast."""
    out: dict[str, int] = {}
    for qid in QIDS:
        context = rows[qid]["context"]
        kept = served_chunks(context)
        if len(kept) != len(context):
            raise RuntimeError(
                f"S270 filtro de relevancia dropea filas del freeze en {qid}: "
                f"{len(kept)}/{len(context)}"
            )
        out[qid] = len(kept)
    return out


# ─────────────────────────── scoring determinista ───────────────────────────

def _fold(text: str) -> str:
    from src.rag.catalog import _fold as fold

    return fold(text)


def frozen_obligations(item: dict[str, Any]):
    from src.rag.answer_planner import AnswerObligation

    return [
        AnswerObligation(**{**row, "required_anchors": tuple(row["required_anchors"])})
        for row in item["obligations"]
    ]


def frozen_conflicts(item: dict[str, Any]):
    from src.rag.answer_planner import (
        AnswerConflict,
        AnswerConflictEvidence,
    )

    output = []
    for row in item["conflicts"]:
        evidence = tuple(
            AnswerConflictEvidence(**evidence_row) for evidence_row in row["evidence"]
        )
        output.append(
            AnswerConflict(
                conflict_id=row["conflict_id"],
                kind=row["kind"],
                product_scope=row["product_scope"],
                operation=row["operation"],
                values=tuple(row["values"]),
                evidence=evidence,
            )
        )
    return output


def _value_near_noun(folded: str, value_rx: re.Pattern) -> bool:
    for m in value_rx.finditer(folded):
        start = max(0, m.start() - _DISCLOSURE_WINDOW)
        end = min(len(folded), m.end() + _DISCLOSURE_WINDOW)
        if _DELAY_NOUN_RX.search(folded[start:end]):
            return True
    return False


def disclosure_covered(answer: str) -> bool:
    """Spec DEC-125 fila 8 (prereg §disclosure_respec): AMBOS valores del conflicto
    seis/7 co-localizados con el sustantivo de tipos-de-retardo + fórmula de disclosure."""
    from src.rag.must_preserve import _disclosure_present

    folded = _fold(answer or "")
    both_values = _value_near_noun(folded, _SIX_RX) and _value_near_noun(
        folded, _SEVEN_RX
    )
    formula = _disclosure_present(folded) or bool(
        _DISCLOSURE_FORMULA_RX.search(folded)
    )
    return both_values and formula


def merged_carrier_covered(answer: str, item: dict[str, Any]) -> bool:
    """Merge DEC-125 (filas 11/12): la obligación de bloque-warning se cubre ssi AMBAS
    componentes pasan el matcher (diseño: evitar lógicas contradictorias + verificación
    rigurosa en puesta en marcha)."""
    from src.rag.answer_planner import obligation_covered

    rows = {o.obligation_id: o for o in frozen_obligations(item)}
    return all(
        obligation_covered(answer, rows[oblid]) for oblid in MERGE_COMPONENT_IDS
    )


def score_answer(answer: str, item: dict[str, Any]) -> dict[str, Any]:
    """Instrumento de la foto: matcher por obligación (20 filas s235) + conflictos +
    citas inválidas + checks nuevos + diagnóstico de cardinalidad (riesgo fila 8)."""
    from src.rag.answer_planner import (
        _declared_cardinality_consistent,
        validate_answer_conflicts,
        validate_answer_plan,
    )
    from src.rag.omission_correction import invalid_citations

    plan = validate_answer_plan(answer, frozen_obligations(item))
    covered = {str(r["obligation_id"]) for r in plan["rows"] if r["covered"]}
    unsafe = {
        str(r["conflict_id"])
        for r in validate_answer_conflicts(answer, frozen_conflicts(item))["unsafe"]
    }
    row: dict[str, Any] = {
        "covered_obligation_ids": sorted(covered),
        "unsafe_conflict_ids": sorted(unsafe),
        "invalid_citations": invalid_citations(answer, int(item["fragment_count"])),
    }
    if str(item["qid"]) == "hp017":
        row["merged_warning_block_covered"] = merged_carrier_covered(answer, item)
        row["disclosure_covered"] = disclosure_covered(answer)
        # diagnóstico (no gate) — nota de riesgo DEC-125 fila 8
        row["cardinality_consistent_6"] = _declared_cardinality_consistent(answer, 6)
    return row


def eligible_coverage(score_row: dict[str, Any], qid: str) -> dict[str, bool]:
    """Cobertura de las 8 gate-eligible para UNA respuesta ya puntuada."""
    covered = set(score_row["covered_obligation_ids"])
    out: dict[str, bool] = {}
    for oblid, obl_qid, check in GATE_ELIGIBLE:
        if obl_qid != qid:
            continue
        if check == "merged_warning_block":
            out[oblid] = bool(score_row.get("merged_warning_block_covered"))
        elif check == "disclosure_respec":
            out[oblid] = bool(score_row.get("disclosure_covered"))
        else:
            out[oblid] = oblid in covered
    return out


def protected_set(items: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Obligaciones cubiertas por las canonical_answer s235 (baseline de la foto),
    calculadas con el matcher pineado; debe COINCIDIR con el set esperado del prereg."""
    protected: dict[str, str] = {}
    for qid in QIDS:
        item = items[qid]
        row = score_answer(item["canonical_answer"], item)
        for oblid in row["covered_obligation_ids"]:
            protected[oblid] = qid
    if frozenset(protected) != EXPECTED_PROTECTED:
        raise RuntimeError(
            f"S270 drift del set protegido: {sorted(protected)} != "
            f"{sorted(EXPECTED_PROTECTED)}"
        )
    return protected


# ─────────────────────────── agregación y gate ───────────────────────────

def _stable(count_true: int, total: int) -> bool:
    return count_true >= STABLE_MIN and total == len(REPLICATES)


def aggregate(
    replica_rows: list[dict[str, Any]],
    items: dict[str, dict[str, Any]],
    protected: dict[str, str],
    actual_cost: float,
) -> dict[str, Any]:
    """Conversiones/regresiones/conflictos ESTABLES según el prereg (>=2/3) sobre las
    réplicas pareadas ya puntuadas. Puro: testeable sin red."""
    by_qid: dict[str, list[dict[str, Any]]] = {qid: [] for qid in QIDS}
    for row in replica_rows:
        by_qid[row["qid"]].append(row)
    for qid in QIDS:
        if len(by_qid[qid]) != len(REPLICATES):
            raise RuntimeError(f"S270 faltan réplicas de {qid}")

    conversions: list[str] = []
    eligible_detail: dict[str, Any] = {}
    for oblid, qid, check in GATE_ELIGIBLE:
        on_count = sum(
            1 for r in by_qid[qid] if eligible_coverage(r["on_score"], qid)[oblid]
        )
        off_count = sum(
            1 for r in by_qid[qid] if eligible_coverage(r["off_score"], qid)[oblid]
        )
        stable_conv = _stable(on_count, len(by_qid[qid])) and (
            len(by_qid[qid]) - off_count
        ) >= STABLE_MIN
        eligible_detail[oblid] = {
            "qid": qid, "check": check,
            "on_covered": on_count, "off_covered": off_count,
            "stable_conversion": stable_conv,
        }
        if stable_conv:
            conversions.append(oblid)

    regressions: list[str] = []
    regression_detail: dict[str, Any] = {}
    nonprotected_losses: list[str] = []
    all_matcher_ids = {
        str(o["obligation_id"]): qid
        for qid in QIDS for o in items[qid]["obligations"]
    }
    for oblid, qid in all_matcher_ids.items():
        off_count = sum(
            1 for r in by_qid[qid]
            if oblid in r["off_score"]["covered_obligation_ids"]
        )
        on_count = sum(
            1 for r in by_qid[qid]
            if oblid in r["on_score"]["covered_obligation_ids"]
        )
        lost = off_count >= STABLE_MIN and (len(by_qid[qid]) - on_count) >= STABLE_MIN
        if not lost:
            continue
        if oblid in protected:
            regressions.append(oblid)
            regression_detail[oblid] = {
                "qid": qid, "off_covered": off_count, "on_covered": on_count,
            }
        else:
            nonprotected_losses.append(oblid)

    new_conflicts: list[str] = []
    conflict_flags: list[dict[str, Any]] = []
    conflict_ids = {
        str(c["conflict_id"]) for qid in QIDS for c in items[qid]["conflicts"]
    }
    for cid in sorted(conflict_ids):
        new_count = 0
        for qid in QIDS:
            for r in by_qid[qid]:
                on_unsafe = cid in r["on_score"]["unsafe_conflict_ids"]
                off_unsafe = cid in r["off_score"]["unsafe_conflict_ids"]
                if on_unsafe and not off_unsafe:
                    new_count += 1
                if on_unsafe or off_unsafe:
                    conflict_flags.append(
                        {
                            "conflict_id": cid, "qid": qid,
                            "replicate": r["replicate"],
                            "arm_off_unsafe": off_unsafe, "arm_on_unsafe": on_unsafe,
                        }
                    )
        if new_count >= STABLE_MIN:
            new_conflicts.append(cid)

    stretch_on = sum(
        1 for r in by_qid["hp011"]
        if STRETCH_ID in r["on_score"]["covered_obligation_ids"]
    )
    stretch_off = sum(
        1 for r in by_qid["hp011"]
        if STRETCH_ID in r["off_score"]["covered_obligation_ids"]
    )
    demoted_report = {}
    for oblid in DEMOTED_IDS:
        qid = all_matcher_ids.get(oblid)
        if qid is None:
            continue
        demoted_report[oblid] = {
            "off_covered": sum(
                1 for r in by_qid[qid]
                if oblid in r["off_score"]["covered_obligation_ids"]
            ),
            "on_covered": sum(
                1 for r in by_qid[qid]
                if oblid in r["on_score"]["covered_obligation_ids"]
            ),
        }

    checks = {
        "stable_conversions_at_least_1": len(conversions) >= 1,
        "protected_regressions_zero": not regressions,
        "new_conflicts_zero": not new_conflicts,
        "cost_below_ceiling": actual_cost <= COST_CEILING_USD,
    }
    requires_human_read = bool(regressions or new_conflicts or conflict_flags)
    verdict = "GO" if all(checks.values()) else "NO_GO"
    return {
        "eligible_detail": eligible_detail,
        "stable_conversions": sorted(conversions),
        "stable_protected_regressions": sorted(regressions),
        "regression_detail": regression_detail,
        "nonprotected_stable_losses": sorted(nonprotected_losses),
        "new_stable_conflicts": sorted(new_conflicts),
        "conflict_flags_for_human_read": conflict_flags,
        "stretch": {
            "obligation_id": STRETCH_ID,
            "on_covered": stretch_on, "off_covered": stretch_off,
            "counts_toward_gate": False,
        },
        "demoted_reporting_only": demoted_report,
        "checks": checks,
        "gate_verdict": verdict,
        "requires_human_read": requires_human_read,
        "human_read_note": (
            "DEC-092b: regresiones/conflictos flagged NO se declaran reales sin "
            "leer las respuestas (evals/s270_etapa2_probe_replicas_v1.jsonl)."
            if requires_human_read else ""
        ),
    }


# ─────────────────────────── coste ───────────────────────────

def cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * PRICING_PER_MTOK["input"]
        + output_tokens * PRICING_PER_MTOK["output"]
    ) / 1_000_000


def estimate_cost(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Estimación de preflight SIN llamadas: chars del prompt reconstruido / 3.0 como
    tokens de input (conservador) y el tope 3500 como output, por llamada."""
    from src.rag.generator import _assemble_system
    from src.rag.post_rerank_coverage import coverage_context_content

    total = 0.0
    per_q: dict[str, float] = {}
    for qid in QIDS:
        row = rows[qid]
        system_chars = len(_assemble_system(row["question"]))
        context_chars = sum(
            len(coverage_context_content(c) or "") + 220 for c in row["context"]
        )
        input_tokens = int(
            (system_chars + context_chars + len(row["question"]) + 400)
            / CHARS_PER_TOKEN
        )
        call = cost_usd(input_tokens, EXPECTED_MAX_TOKENS)
        per_q[qid] = round(call * len(REPLICATES), 6)
        total += call * len(REPLICATES)
    if total > COST_CEILING_USD:
        raise RuntimeError(
            f"S270 estimación {total:.4f} USD supera el techo {COST_CEILING_USD}"
        )
    return {"per_qid_usd": per_q, "total_usd": round(total, 6)}


# ─────────────────────────── attestation / trace ───────────────────────────

def attestation_report(
    question: str, chunks: list[dict[str, Any]], off_answer: str
) -> dict[str, Any]:
    """Attestation REAL por fragmento citado (mismo código del mecanismo, sin bypass) +
    visibilidad del F13 del stretch (servido-no-citado)."""
    from src.rag import must_preserve as mp

    resolved = sorted(mp._query_resolved_ids(question))
    catalog = mp._load_catalog()
    cited = sorted(mp.cited_fragment_numbers(off_answer))
    per_fragment = {}
    for idx in cited:
        if not 1 <= idx <= len(chunks):
            continue
        per_fragment[str(idx)] = bool(
            mp.attest_identity(chunks[idx - 1].get("document_id"), resolved, catalog)
        )
    blocked = bool(resolved) and bool(per_fragment) and not any(per_fragment.values())
    report = {
        "identity_resolved_ids": resolved,
        "identity_resolved": bool(resolved),
        "cited_fragments": cited,
        "attested_by_fragment": per_fragment,
        "attestation_blocked": (not resolved) or blocked,
    }
    if len(chunks) >= STRETCH_FRAGMENT:
        f13 = chunks[STRETCH_FRAGMENT - 1]
        report["stretch_f13"] = {
            "cited": STRETCH_FRAGMENT in cited,
            "attested": bool(
                mp.attest_identity(f13.get("document_id"), resolved, catalog)
            ),
            "binding_not_reached": STRETCH_FRAGMENT not in cited,
        }
    return report


# ─────────────────────────── ejecución ───────────────────────────

def _load_checkpoint() -> dict[tuple[str, int], dict[str, Any]]:
    done: dict[tuple[str, int], dict[str, Any]] = {}
    if REPLICAS.exists():
        for line in REPLICAS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done[(str(row["qid"]), int(row["replicate"]))] = row
    return done


def _append_checkpoint(row: dict[str, Any]) -> None:
    with open(REPLICAS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _patch_no_retry() -> None:
    """max_retries=0 (no-retry del prereg) sin tocar prod: el generador construye
    ``anthropic.Anthropic(api_key=...)`` — se envuelve el constructor en este proceso."""
    import anthropic

    from src.rag import generator as gen_mod

    base = anthropic.Anthropic

    class _NoRetryAnthropic(base):  # type: ignore[misc,valid-type]
        def __init__(self, **kwargs: Any) -> None:
            kwargs["max_retries"] = 0
            super().__init__(**kwargs)

    gen_mod.anthropic.Anthropic = _NoRetryAnthropic


def _assert_pipeline_config() -> None:
    from src import config

    if config.LLM_MODEL != EXPECTED_MODEL:
        raise RuntimeError(
            f"S270 LLM_MODEL={config.LLM_MODEL!r} != prod {EXPECTED_MODEL!r}"
        )
    if config.LLM_MAX_TOKENS != EXPECTED_MAX_TOKENS:
        raise RuntimeError(
            f"S270 LLM_MAX_TOKENS={config.LLM_MAX_TOKENS} != {EXPECTED_MAX_TOKENS} "
            "(¿.env local pisó el flag antes del import?)"
        )
    for key, value in GENERATION_ENV.items():
        if os.environ.get(key, "") != value:
            raise RuntimeError(f"S270 flag {key} alterado tras el import")


def run_replicate(
    qid: str, question: str, chunks: list[dict[str, Any]], replicate: int
) -> dict[str, Any]:
    from src.rag import generator, must_preserve

    if os.environ.get("MUST_PRESERVE_CONTRACT") != "off":
        raise RuntimeError("S270 la generación debe correr con el contrato OFF")
    result = generator.generate_answer(question, chunks)
    if result.get("stop_reason") != "end_turn":
        raise RuntimeError(
            f"S270 {qid}:r{replicate} stop_reason={result.get('stop_reason')!r} "
            "(contrato: end_turn; la réplica no se persiste ni se re-llama)"
        )
    off_answer = str(result["answer"])
    os.environ["MUST_PRESERVE_CONTRACT"] = "on"
    try:
        on_answer, trace = must_preserve.apply_must_preserve_contract(
            question, chunks, off_answer
        )
    finally:
        os.environ["MUST_PRESERVE_CONTRACT"] = "off"
    input_tokens = int(result.get("input_tokens") or 0)
    output_tokens = int(result.get("output_tokens") or 0)
    return {
        "qid": qid,
        "replicate": replicate,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": EXPECTED_MODEL,
        "stop_reason": result.get("stop_reason"),
        "off_answer": off_answer,
        "on_answer": on_answer,
        "must_preserve_trace": trace,
        "attestation": attestation_report(question, chunks, off_answer),
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        "cost_usd": round(cost_usd(input_tokens, output_tokens), 8),
    }


def score_replica_rows(
    raw_rows: list[dict[str, Any]], items: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    scored = []
    for row in raw_rows:
        item = items[row["qid"]]
        scored.append(
            {
                **row,
                "off_score": score_answer(row["off_answer"], item),
                "on_score": score_answer(row["on_answer"], item),
            }
        )
    return scored


def execute(
    prereg: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    protected: dict[str, str],
    pins: dict[str, str],
    env_file: Path,
) -> int:
    if OUT.exists():
        raise RuntimeError("S270 el result ya existe — no se re-corre (no-retry)")
    if runner_pin_status(prereg) != "MATCH":
        raise RuntimeError(
            "S270 runner sin pin MATCH en el prereg — estampar antes de --execute"
        )
    from dotenv import dotenv_values

    key = (
        (dotenv_values(env_file).get("ANTHROPIC_API_KEY") or "")
        or os.getenv("ANTHROPIC_API_KEY", "")
    ).strip()
    if not key:
        raise RuntimeError("S270 ANTHROPIC_API_KEY ausente")
    os.environ["ANTHROPIC_API_KEY"] = key
    # generator liga ANTHROPIC_API_KEY a IMPORT-time (from ..config import ...):
    # re-apuntar el binding del módulo, no solo config (belt-and-braces).
    from src import config
    from src.rag import generator as gen_mod

    config.ANTHROPIC_API_KEY = key
    gen_mod.ANTHROPIC_API_KEY = key
    _assert_pipeline_config()
    _patch_no_retry()

    done = _load_checkpoint()
    actual_cost = sum(r.get("cost_usd", 0.0) for r in done.values())
    estimate = estimate_cost(rows)
    per_call_upper = max(estimate["per_qid_usd"][q] / len(REPLICATES) for q in QIDS)
    for qid in QIDS:
        question = rows[qid]["question"]
        chunks = served_chunks(rows[qid]["context"])
        for replicate in REPLICATES:
            if (qid, replicate) in done:
                continue
            if actual_cost + per_call_upper > COST_CEILING_USD:
                raise RuntimeError(
                    f"S270 techo de coste alcanzado ({actual_cost:.4f} USD)"
                )
            row = run_replicate(qid, question, chunks, replicate)
            _append_checkpoint(row)
            done[(qid, replicate)] = row
            actual_cost += row["cost_usd"]
            print(
                f"  {qid}:r{replicate} ok — in={row['usage']['input_tokens']} "
                f"out={row['usage']['output_tokens']} coste acum {actual_cost:.4f} USD"
            )

    raw_rows = [done[(qid, rep)] for qid in QIDS for rep in REPLICATES]
    scored = score_replica_rows(raw_rows, items)
    verdictos = aggregate(scored, items, protected, actual_cost)
    write_result(prereg, pins, scored, verdictos, protected, actual_cost)
    print(json.dumps(
        {
            "status": verdictos["gate_verdict"],
            "stable_conversions": verdictos["stable_conversions"],
            "stable_protected_regressions": verdictos["stable_protected_regressions"],
            "new_stable_conflicts": verdictos["new_stable_conflicts"],
            "requires_human_read": verdictos["requires_human_read"],
            "actual_cost_usd": round(actual_cost, 6),
            "result": str(OUT.relative_to(ROOT)),
        },
        indent=2, ensure_ascii=False,
    ))
    return 0 if verdictos["gate_verdict"] == "GO" else 2


def write_result(
    prereg: dict[str, Any],
    pins: dict[str, str],
    scored: list[dict[str, Any]],
    verdictos: dict[str, Any],
    protected: dict[str, str],
    actual_cost: float,
) -> None:
    from src.rag.visual_gold import sealed_artifact, write_json

    per_replica = [
        {
            "qid": r["qid"],
            "replicate": r["replicate"],
            "off_score": r["off_score"],
            "on_score": r["on_score"],
            "must_preserve_trace": r["must_preserve_trace"],
            "attestation": r["attestation"],
            "usage": r["usage"],
            "cost_usd": r["cost_usd"],
        }
        for r in scored
    ]
    body = {
        "status": verdictos["gate_verdict"],
        "prereg": str(PREREG.relative_to(ROOT)),
        "design": {
            "paired": True,
            "replicates": len(REPLICATES),
            "arms": ["MUST_PRESERVE_CONTRACT=off", "MUST_PRESERVE_CONTRACT=on"],
            "model": EXPECTED_MODEL,
            "max_tokens": EXPECTED_MAX_TOKENS,
            "temperature": 0,
        },
        "frozen_inputs_sha256_lf_normalized": pins,
        "protected_set": {oblid: protected[oblid] for oblid in sorted(protected)},
        "per_replica": per_replica,
        "aggregate": verdictos,
        "actual_cost_usd": round(actual_cost, 6),
        "replicas_jsonl": str(REPLICAS.relative_to(ROOT)),
        "database_reads": 0,
        "database_writes": 0,
    }
    write_json(OUT, sealed_artifact("s270_etapa2_probe_result_v1", body))


# ─────────────────────────── preflight / main ───────────────────────────

def preflight(
    prereg: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    protected: dict[str, str],
) -> dict[str, Any]:
    from src.rag import must_preserve as mp

    parity = assert_filter_parity(rows)
    estimate = estimate_cost(rows)
    identity = {
        qid: sorted(mp._query_resolved_ids(rows[qid]["question"])) for qid in QIDS
    }
    return {
        "status": "PREFLIGHT_PASS",
        "runner_pin": runner_pin_status(prereg),
        "questions": len(QIDS),
        "replicates": len(REPLICATES),
        "paid_calls_planned": len(QIDS) * len(REPLICATES),
        "paid_calls_made_now": 0,
        "database_reads": 0,
        "database_writes": 0,
        "filter_parity_rows": parity,
        "identity_resolution": identity,
        "protected_set": sorted(protected),
        "gate": {
            "stable_conversions_min": 1,
            "protected_regressions_max": 0,
            "new_conflicts_max": 0,
            "cost_ceiling_usd": COST_CEILING_USD,
        },
        "estimated_cost": estimate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()

    export_generation_env()  # ANTES de importar el pipeline (config load_dotenv override=False)
    prereg = load_prereg()
    pins = verify_pins(prereg)
    rows = load_freeze_rows()
    items = load_score_items()
    _assert_pipeline_config()
    protected = protected_set(items)

    report = preflight(prereg, rows, items, protected)
    if not args.execute:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(json.dumps({"preflight": report["status"],
                      "estimated_cost": report["estimated_cost"]}, indent=2))
    return execute(prereg, rows, items, protected, pins, args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
