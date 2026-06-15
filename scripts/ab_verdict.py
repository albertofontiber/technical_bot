#!/usr/bin/env python3
"""Capa de VEREDICTO compartida de los A/B (s73 — paga la deuda del patrón que el workflow
adversarial marcó: la tabla SHIP/ROLLBACK/GRIS estaba copiada LITERAL en s59_ab_verdict /
s67_ab / s69_ab, sin función compartida ni tests, y ya driftó). Fuente única de:
  - MARGEN_GANANCIA: una ganancia cuenta solo con PASS >= margen (guardia s61 §7 / s67_ab:78);
  - classify_pair: clasificación per-gold del delta base→tratamiento (flip-pass / regresión / neutral);
  - global_verdict: la tabla de los A/B de N golds (d_net…, transfiere s67_ab:298-302);
  - small_n_verdict: el árbol de decisión n-pequeño (s73: 2 movers — pre-registrado por el workflow).

`aggregate()` y `ORDER` se IMPORTAN de bvg_kmajority (NO se re-implementan — fuente única de la
K-mayoría; la duplicación de ORDER en s59 era justo la deuda). Tests: tests/test_ab_verdict.py.

NOTA de migración (deuda parcial pagada): s73 usa este módulo; s59/s67/s69 siguen con su copia
literal hasta un refactor incremental seguro (no se reescriben aquí para no desestabilizar
verdicts que ya corrieron). El módulo + tests EXISTEN y son la fuente para nuevos A/B.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bvg_kmajority import ORDER, aggregate  # noqa: E402  (fuente única K-mayoría)

MARGEN_GANANCIA = 4  # una ganancia cuenta en Δ_net solo con PASS >= 4/5 (s61 §7 / s67_ab.py:78)

assert "PASS" in ORDER, "ORDER importado de bvg no contiene PASS — ¿cambió el contrato?"


def classify_pair(base_votes: list[str], treat_votes: list[str],
                  margin: int = MARGEN_GANANCIA) -> dict:
    """Clasifica el delta per-gold base→tratamiento sobre los votos K-mayoría. Devuelve
    {base, treat, delta} con delta ∈:
      'flip-pass'            : base no-PASS, treat modal PASS con >= margin votos PASS (ganancia que cuenta);
      'flip-pass-sin-margen' : base no-PASS, treat modal PASS pero < margin (NO cuenta — guardia s61);
      'regresion-de-pass'    : base modal PASS, treat no-PASS (pérdida dura);
      'neutral'              : sin cambio de PASS-status (incluye mejoras intra-no-PASS, p.ej. FALLO→PARCIAL).
    """
    b, t = aggregate(base_votes), aggregate(treat_votes)
    b_pass = b["veredicto"] == "PASS"
    t_pass = t["veredicto"] == "PASS"
    if t_pass and not b_pass:
        # margen calibrado sobre K runs VÁLIDOS: un voto '?' (juez-error) NO relaja el 4/5
        # (anti-sesgo-pro-ship, dúo s73). flip cuenta solo si los K son válidos Y PASS>=margen.
        full_valid = t.get("n_valid", 0) == len(treat_votes)
        delta = ("flip-pass" if (full_valid and t["votes"].get("PASS", 0) >= margin)
                 else "flip-pass-sin-margen")
    elif b_pass and not t_pass:
        delta = "regresion-de-pass"
    else:
        delta = "neutral"
    return {"base": b, "treat": t, "delta": delta}


def global_verdict(m: dict) -> dict:
    """Tabla de decisión de los A/B de N golds (transfiere LITERAL s67_ab:298-302). `m` =
    métricas agregadas: d_net, f_base, f_post, d_inest, control_caidas(list), caidas_r1(list),
    conducta_reg(list). SHIP Δ_net>=+2 ∧ control<=1 ∧ F_post<=F_base ∧ Δ_inest<=+1 · ROLLBACK
    regla-1 / control>1 / F↑ / Δ_net<0 / conducta>=2 / inest>+3 · resto GRIS."""
    rollback = (bool(m.get("caidas_r1")) or len(m.get("control_caidas", [])) > 1
                or m["f_post"] > m["f_base"] or m["d_net"] < 0
                or len(m.get("conducta_reg", [])) >= 2 or m["d_inest"] > 3)
    ship = (not rollback and m["d_net"] >= 2 and len(m.get("control_caidas", [])) <= 1
            and m["f_post"] <= m["f_base"] and m["d_inest"] <= 1)
    return {"veredicto": "ROLLBACK" if rollback else ("SHIP" if ship else "GRIS")}


def small_n_verdict(movers: list[dict], *, factcov_no_cae: bool, control_intacto: bool) -> dict:
    """Árbol de decisión n-pequeño (s73, 2 movers; pre-registrado por el workflow adversarial).
    `movers` = lista de resultados de classify_pair() (uno por mover). Reglas:
      - cualquier 'regresion-de-pass' en un mover     → ROLLBACK (STOP duro);
      - control (los 37 no-movers) NO intacto         → ROLLBACK;
      - >=1 'flip-pass' (CON margen) ∧ ningún mover regresa ∧ factcov no cae ∧ control intacto
                                                       → SHIP-CANDIDATO;
      - resto (sube a PARCIAL, o flip sin margen, o factcov cae) → GRIS (decide Alberto).

    NO hay 'SHIP' automático (dúo s73): el techo de la decisión automática es SHIP-CANDIDATO. El
    2º eje (no-invención) NO es auto-certificable → lo confirma el HUMANO sobre los diagnósticos
    del juez + el prod-smoke antes de encender el flag (regla F). El JUEZ arbitra la mejora (el
    PASS-flip); factcov solo CORROBORA completitud — factcov↑ sin flip = GRIS, nunca candidato.
    UMBRAL n=2: 1-de-2 flips basta para CANDIDATO (el otro no debe regresar) — decisión declarada;
    si solo 1 de 2 mejora, Alberto decide si un éxito parcial del Brazo A justifica el ship."""
    deltas = [mv["delta"] for mv in movers]
    if any(d == "regresion-de-pass" for d in deltas):
        return {"veredicto": "ROLLBACK", "motivo": "un mover regresa de PASS (STOP)"}
    if not control_intacto:
        return {"veredicto": "ROLLBACK", "motivo": "control (37 no-movers) regresó"}
    n_flip = sum(1 for d in deltas if d == "flip-pass")
    if n_flip >= 1 and factcov_no_cae:
        return {"veredicto": "SHIP-CANDIDATO",
                "motivo": (f"{n_flip}/{len(movers)} flip(s) FALLO→PASS con margen, 0 regresión, "
                           "factcov no cae. PENDIENTE 2º eje (no-invención: diagnósticos del juez) "
                           "+ prod-smoke → decide Alberto")}
    return {"veredicto": "GRIS",
            "motivo": "sin flip a PASS con margen (o factcov cae) → decide Alberto"}
