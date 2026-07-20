#!/usr/bin/env python3
"""S274 (DEC-134): BANKING determinista de la conversión certificada del bloque C/D
sobre el funnel banked s272 (patrón S272/DEC-131: aritmética pura sobre insumos
SHA-pineados, $0, cero llamadas a modelo, cero red).

Proyección: 145 OK / 7 synth / 2 retr / 154 (evals/s272_banked_funnel_v1.json)
  + obl_0d6a30948dfd  (probe #4 A-C1: merged_warning_block 3/3 ON vs 0/3 en A0,
                       pareado mismo-día; idéntico en A-ALL-det y A-ALL; 0 protegidas
                       caídas / 0 conflictos / 0 anclas perdidas / retrieval-invariante
                       PASS / 0 diagramas-por-anexo — evals/s274_probeCD_result_v1.json;
                       P3 smoke vivo con la config candidata 5/5 monotónicos, 0 espurios)
  → **146 OK / 6 synth / 2 retr / 154 (94,81%)** — quedan +5 para 151 (98%).

Banking bajo la regla Sol-C1 (solo lo DESPLEGABLE): la conversión exige el PAR
`COVERAGE_MANDATORY_CALLOUT=on + MP_MANDATORY_VERB_TRIGGER=on` en prod (declarado
config de SHIP candidata; MUST_PRESERVE_CONTRACT ya on desde DEC-131). Estado vivo:
PENDIENTE de la activación del par en Railway — recibo vivo query_logs al encender
(patrón DEC-131); hasta entonces el crédito es certificación det-only + smoke.

Los 6 synth restantes quedan EXHAUSTOS en la familia mecanismo-de-anexo (qué fix se
probó y cómo murió, por id) — el camino a 151 exige OTRA familia (DEC-134).

Salida: ``evals/s274_banked_funnel_v1.json``.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import write_json  # noqa: E402

BASELINE = ROOT / "evals/s272_banked_funnel_v1.json"
PROBE_RESULT = ROOT / "evals/s274_probeCD_result_v1.json"
P1_GATE = ROOT / "evals/s274_stage1_v9_gate_v1.yaml"
SMOKE = ROOT / "evals/s270_etapa3_smoke_result_v1.json"
OUTPUT = ROOT / "evals/s274_banked_funnel_v1.json"

# SHA-256 de bytes LF-normalizados (checkout Windows/autocrlf); el pin FALLA ante drift.
PINNED_SHA256_LF = {
    "evals/s272_banked_funnel_v1.json": (
        "4ddb6f8eba71766cf6c0c1abd0ac9fda1fa5476f2a5430c3da023f64f24502db"
    ),
    "evals/s274_probeCD_result_v1.json": (
        "5d15a51749e7062cea8e92610adea8593729f7b05e587d8021fc14d45028be1f"
    ),
    "evals/s274_stage1_v9_gate_v1.yaml": (
        "b1d0ea6088164bc8871e7733a7cf089dd9c565a548a1fa5894e6acec0eb0f6b8"
    ),
    "evals/s270_etapa3_smoke_result_v1.json": (
        "d212018855da4f9a9ab481cd84e1364dbb4631ac3b10b22d780f85eaf1771fdd"
    ),
}

BANKED = "obl_0d6a30948dfd"
SHIP_PAIR = ("COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER")

# Los 6 synth restantes con su estado EXHAUSTO-en-esta-familia (qué fix se probó
# en s274 y cómo murió; evidencia: gate P1 v9 + probe #4 + funnel N=3 + prereg v2.2).
RESIDUAL_EXHAUSTED = {
    "obl_2f5d79e354b9": {
        "qid": "hp011", "clase": "uncited_scope",
        "fix_probado": "C2 MP_SERVED_BINDING (binding servidos-no-citados, umbral reforzado >=3)",
        "como_murio": (
            "NO-GO en P1 v9 ANTES del probe: served_uncited_clean_fp=24/105 en "
            "población fresca seed-277 (26 anexos de HERMANOS genuinos / 1 target, "
            "verificado por-fila) — la clase seed-270 re-medida FALLA incluso con "
            "el umbral reforzado; DEC-127 reforzado, el brazo A-C2 quedó SKIP"
        ),
    },
    "obl_7bba8d03d496": {
        "qid": "cat018", "clase": "binding_tension",
        "fix_probado": "D2 MP_DISTINCTIVE_TOKEN (bind con 1 token propio distintivo)",
        "como_murio": (
            "P1 GO (FP=0, re-clase seed-271=0, positivo 26/26) pero A-D2 y A-ALL "
            "0/3 en el probe #4: la ventana de cita real de cat018 no contiene el "
            "token distintivo — el fix es correcto y no convierte esta diana"
        ),
    },
    "obl_a5d9fa1f9253": {
        "qid": "hp002", "clase": "composites_hybrid_gap",
        "fix_probado": (
            "D1c MP_STEM_BINDING (plural es/en) + D1b F-RELATION híbrido"
        ),
        "como_murio": (
            "P1 GO ambos (stem 51/57; shape F-RELATION 45/45) pero A-D1c, "
            "A-D1b-hyb y A-ALL 0/3: Haiku no propone la cláusula del qualifier "
            "bajo el prompt con F-RELATION (ya 0/3 en el funnel N=3 — sin familia "
            "que encaje el qualifier semántico) y el stem solo no alcanza"
        ),
    },
    "obl_015f9b9aaa3a": {
        "qid": "cat018", "clase": "composites_hybrid_gap",
        "fix_probado": "D1a MP_DEFLINE_EQ (separador '=' en deflines) + híbrido",
        "como_murio": (
            "P1 GO (defline_eq 14/14, FP=0) pero A-D1a y A-ALL 0/3: el shape del "
            "bundle TONE ya existe con el flag y su ventana [F8] no comparte "
            "tokens propios (predicho BAJA en el prereg; binding a nivel "
            "fragmento rechazado con métrica seed-270 y NO propuesto)"
        ),
    },
    "obl_b2043cd4379b": {
        "qid": "hp017", "clase": "composites_hybrid_gap+serving_view",
        "fix_probado": "C1 card de callout + D1b F-RELATION híbrido",
        "como_murio": (
            "corrección v2.2 CONFIRMADA en el probe: la card C1 es de léxico "
            "MANDATORY y el span de b2043 («Instrucción de entrada») es "
            "DEFINICIONAL sin gatillo — sigue fuera de la vista servida incluso "
            "con C1 on; A-C1/A-ALL 0/3"
        ),
    },
    "obl_7aa723717412": {
        "qid": "hp017", "clase": "composites_hybrid_gap",
        "fix_probado": "D1b F-RELATION (defhead) híbrido",
        "como_murio": (
            "P1 GO (defhead 17/18) pero A-D1b-hyb y A-ALL 0/3: su ventana [F12] "
            "no comparte tokens propios con la cláusula definicional — el binding "
            "no llega aunque el shape exista (predicho baja-media)"
        ),
    },
}


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_pins() -> dict[str, str]:
    seen: dict[str, str] = {}
    for rel, expected in PINNED_SHA256_LF.items():
        actual = _sha256_lf(ROOT / rel)
        if actual != expected:
            raise ValueError(
                f"SHA drift en insumo pineado {rel}: esperado {expected}, actual {actual}"
            )
        seen[rel] = actual
    return seen


def build_projection() -> dict[str, Any]:
    pins = verify_pins()
    baseline_doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    probe = json.loads(PROBE_RESULT.read_text(encoding="utf-8"))
    p1 = yaml.safe_load(P1_GATE.read_text(encoding="utf-8"))
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))

    baseline = baseline_doc["banked_funnel"]
    if (
        baseline["denominator"], baseline["ok"],
        baseline["synthesis_miss"], baseline["retrieval_miss"],
    ) != (154, 145, 7, 2):
        raise ValueError(f"baseline s272 fuera de contrato: {baseline}")
    remaining_prev = {
        oid for ids in baseline_doc["remaining_synthesis_miss_by_class"].values()
        for oid in ids
    }
    if len(remaining_prev) != 7 or BANKED not in remaining_prev:
        raise ValueError("los 7 synth restantes de s272 no contienen la banked")
    if set(RESIDUAL_EXHAUSTED) != remaining_prev - {BANKED}:
        raise ValueError("la partición banked+exhaustos no reconstruye los 7 de s272")

    # Gate P1 v9: el PAR de la conversión en GO; C2 NO-GO registrado.
    verdicts = p1["verdict_by_fix"]
    for flag in SHIP_PAIR:
        if verdicts.get(flag) != "GO":
            raise ValueError(f"gate P1: {flag} no está en GO")
    if verdicts.get("MP_SERVED_BINDING") != "NO_GO":
        raise ValueError("gate P1: se esperaba MP_SERVED_BINDING NO_GO (C2)")

    # Probe #4: conversión certificada + 0 daño + banking desplegable.
    if probe.get("schema") != "s274_probeCD_result_v1" or probe["probe_number"] != 4:
        raise ValueError("result del probe #4 con schema inesperado")
    agg = probe["aggregate"]
    if agg["banking"]["det_only_bankable"] != [BANKED]:
        raise ValueError(
            f"det_only_bankable != [{BANKED}]: {agg['banking']['det_only_bankable']}"
        )
    if agg["banking"]["hybrid_only_requires_ship_decision"]:
        raise ValueError("conversiones hybrid-only inesperadas")
    if agg["stop_rule_hits"]:
        raise ValueError(f"stop-rule disparado: {agg['stop_rule_hits']}")
    ac1 = agg["per_arm"]["A-C1"]
    cand = ac1["candidates"][BANKED]
    if not (
        cand["check"] == "merged_warning_block"
        and cand["arm_on"] == 3 and cand["a0_on"] == 0
        and cand["stable_conversion"]
    ):
        raise ValueError(f"conversión 0d6a no certificada en A-C1: {cand}")
    for arm, rep in agg["per_arm"].items():
        if rep.get("status") != "measured" or arm == "A0":
            continue
        if not rep["damage_gates"]["pass"]:
            raise ValueError(f"gate de daño rojo en {arm}")
    if not ac1["retrieval_invariant"]["pass"]:
        raise ValueError("retrieval-invariante de A-C1 no pasa")
    if float(probe["actual_cost_usd"]) > 6.0:
        raise ValueError("coste del probe sobre el techo")

    # P3: smoke vivo con la config candidata — 5/5 monotónicos, 0 espurios.
    if smoke.get("monotonicity_violations") or smoke.get("appendix_fired"):
        raise ValueError("smoke P3 con violaciones/espurios")
    if len(smoke["rows"]) != 5 or not all(r["monotonic"] for r in smoke["rows"]):
        raise ValueError("smoke P3 sin 5/5 monotónicos")

    ok = baseline["ok"] + 1
    synth = baseline["synthesis_miss"] - 1
    retrieval = baseline["retrieval_miss"]
    denominator = baseline["denominator"]
    if ok + synth + retrieval != denominator:
        raise ValueError("la aritmética del funnel banked no cierra")
    if (ok, synth, retrieval, denominator) != (146, 6, 2, 154):
        raise ValueError(
            f"proyección fuera de contrato: {ok}/{synth}/{retrieval}/{denominator}"
        )
    ok_pct = round(100.0 * ok / denominator, 2)
    required_ok = 151  # ceil(0.98 * 154), herencia DEC-125/131

    return {
        "schema": "s274_banked_funnel_v1",
        "date": "2026-07-20",
        "dec": "DEC-134",
        "generated_by": "scripts/s274_bank_conversions.py",
        "authority": (
            "evals/s272_banked_funnel_v1.json (DEC-131) + gate P1 v9 por-fix + "
            "probe #4 pareado con brazos de ablación + smoke vivo P3 con la config "
            "candidata"
        ),
        "inputs_sha256_lf_normalized": pins,
        "baseline_funnel": {
            **{k: baseline[k] for k in (
                "denominator", "ok", "synthesis_miss", "retrieval_miss", "ok_pct"
            )},
            "provenance": "DEC-131 (funnel banked, s272)",
        },
        "conversions_banked": [{
            "obligation_id": BANKED,
            "qid": "hp017",
            "certificacion": (
                "probe #4 A-C1 (par C1: card de callout + verb-trigger): "
                "merged_warning_block 3/3 ON vs 0/3 A0, pareado mismo-día K=3; "
                "idéntico en A-ALL-det (lo shippeable sin Haiku) y A-ALL; 0 "
                "protegidas caídas / 0 conflictos nuevos / anclas +0/−0 / "
                "retrieval-invariante PASS / 0 diagramas-por-anexo — "
                "evals/s274_probeCD_result_v1.json ($0.604 ≤ $6)"
            ),
            "estado_vivo": (
                "PENDIENTE de activación del par en Railway (config de SHIP "
                "candidata; runbook 1 línea) — recibo vivo query_logs al encender "
                "(patrón DEC-131). El smoke P3 con la config candidata ya corrió "
                "limpio: 5/5 monotónicos, 0 apéndices espurios ($0.6412)."
            ),
            "requires_prod_flags": list(SHIP_PAIR) + ["MUST_PRESERVE_CONTRACT (ya on, DEC-131)"],
        }],
        "ship_config_candidate": {
            "flags_on": list(SHIP_PAIR),
            "flags_off": [
                "MP_SERVED_BINDING (NO-GO P1)", "MP_DEFLINE_EQ", "MP_HYBRID_DETECT",
                "MP_STEM_BINDING", "MP_DISTINCTIVE_TOKEN",
            ],
            "runbook": (
                "Railway → variables: COVERAGE_MANDATORY_CALLOUT=on y "
                "MP_MANDATORY_VERB_TRIGGER=on (MUST_PRESERVE_CONTRACT ya on) → "
                "1 pregunta de smoke → rollback = quitar las 2 variables."
            ),
        },
        "banked_funnel": {
            "denominator": denominator,
            "ok": ok,
            "synthesis_miss": synth,
            "retrieval_miss": retrieval,
            "ok_pct": ok_pct,
        },
        "remaining_synthesis_exhausted_in_annex_family": RESIDUAL_EXHAUSTED,
        "strategic_declaration": (
            "La familia mecanismo-de-anexo (detect→bind→attest→render con sus 7 "
            "fixes flag-gated) queda EXHAUSTA para los 6 residuales: cada uno tuvo "
            "su fix construido, gateado en población fresca y medido en el probe "
            "#4 sin conversión (o muerto en P1 con métrica). El camino a 151 exige "
            "OTRA familia — opciones para Alberto: (a) adjudicación gold round-2 "
            "con lente source-contract; (b) expansión de la serving-view más allá "
            "de callouts (clase C1 generalizada); (c) eval orgánico como árbitro "
            "de si los 6 importan en uso real."
        ),
        "facts_moved_to_ok": 1,
        "official_atomic_kpi": None,
        "official_atomic_kpi_note": (
            "Los 77 legacy carries siguen (S205); sin KPI atómico oficial hasta cerrarlos."
        ),
        "target": {
            "declared": "98% de 154 = 151 → +5",
            "target_pct": 0.98,
            "required_ok": required_ok,
            "conversions_needed": required_ok - ok,
        },
    }


def main() -> int:
    report = build_projection()
    write_json(OUTPUT, report)
    funnel = report["banked_funnel"]
    print(
        f"OK {funnel['ok']} / synth {funnel['synthesis_miss']} / retr "
        f"{funnel['retrieval_miss']} / den {funnel['denominator']} "
        f"({funnel['ok_pct']}%) -- objetivo 98% de 154 = "
        f"{report['target']['required_ok']} -> +{report['target']['conversions_needed']}"
    )
    print(f"escrito: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
