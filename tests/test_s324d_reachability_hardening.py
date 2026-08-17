# -*- coding: utf-8 -*-
"""s324d / TECH_DEBT #89 — endurecimiento de la sonda de alcanzabilidad: la lógica nueva es PURA y se
prueba sin entorno (misma razón que `reachability_verdict`: un guard que no corre en CI no guarda nada).

Los cinco defectos del agente de medición (16-ago) y qué ancla cada test:
  1. recibo FULL pineado al 1-ago → `elegir_receipt` elige el más reciente por fecha del nombre; explícito manda.
  2. `appendix` elegía la primera línea que casaba el regex sin comprobar cobertura, partía «etiqueta: definición»
     y descartaba etiquetas cortas → `elegir_span` no parte por «:», exige los tokens del valor y extiende
     hasta 2 líneas; si nada cubre, lo dice (`cubre.ok=False`) en vez de fabricar un oráculo incompleto.
  3. `SystemExit` tardío tiraba las reps juzgadas → una rep NO construible es una fila (span None) que el
     veredicto trata como sin prueba de entrega (INCONCLUYENTE), y el probe escribe recibo PARCIAL (no testeable
     aquí sin entorno; anclado por el contrato de `veredicto_de`).
  4. coste ausente → `usage_meter.cost_of` suma por modelo con precio declarado y NO inventa el desconocido.
  5. carrier ya servido → `carriers_ya_servidos` lo declara.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import reachability_verdict as RV  # noqa: E402
from scripts import usage_meter as UM  # noqa: E402


# ── 2 · guard de cobertura del span ──────────────────────────────────────────────────────────
PEARL = [{"content": ("Programación de causa-efecto.\n"
                      "Las reglas constan de dos partes, como se explica a continuación:\n"
                      "* Instrucción de entrada: esta parte de la regla es una condición de entrada, como una alarma.\n"
                      "* Instrucción de salida: esta parte de la regla solo puede procesarse si...")}]


def test_no_parte_por_dos_puntos_ni_descarta_etiquetas_cortas():
    """hp017#1: la etiqueta «* Instrucción de entrada:» quedaba fuera (split en «:» + len>25) → «no construible»
    con el carrier SERVIDO. Ahora la línea entera es el span y cubre el valor."""
    r = RV.elegir_span(PEARL, r"Instrucci[oó]n de entrada", "instrucción de entrada")
    assert r["span"].startswith("* Instrucción de entrada: esta parte")
    assert r["cubre"]["ok"] is True and r["fragment_number"] == 1 and r["extendido"] is False


def test_extiende_a_la_linea_siguiente_cuando_el_hecho_ocupa_dos_frases():
    """cat016#1 / hp009#0: un span de UNA frase no cubre un hecho de dos. Se extiende (≤2 líneas)."""
    ch = [{"content": ("El lazo analógico se cablea en bucle cerrado.\n"
                       "Inicio Lazo +/- OUT hacia el primer equipo. Retorno +/- al panel.\n"
                       "No lleva resistencia de fin de línea.")}]
    r = RV.elegir_span(ch, r"bucle cerrado", "Retorno")
    assert r["cubre"]["ok"] is True and r["extendido"] is True and "Retorno" in r["span"]


def test_si_nada_cubre_lo_declara_en_vez_de_fabricar_el_oraculo():
    ch = [{"content": "No lleva resistencia de fin de línea. Fin del capítulo."}]
    r = RV.elegir_span(ch, r"resistencia de fin", "Retorno")
    assert r["span"] is not None and r["cubre"]["ok"] is False and r["cubre"]["ausentes"] == ["retorno"]
    r2 = RV.elegir_span(ch, r"NO EXISTE", "Retorno")
    assert r2["span"] is None and r2["candidatos_probados"] == 0


def test_span_cubre_normaliza_acentos_y_caja():
    assert RV.span_cubre("En el MENU zona se asigna; en el menu ELEMENTO se nombra", "menú ZONA + ELEMENTO")["ok"]
    assert not RV.span_cubre("En el menú ZONA se asigna", "menú ZONA + ELEMENTO")["ok"]
    assert RV.span_cubre("05 a 295 seg", "05 a 295 seg")["ok"]


# ── 3 · una rep no construible es INCONCLUYENTE, no un NO ni un crash ────────────────────────
def test_rep_no_construible_no_produce_negativo():
    cfg = {"mode": "appendix", "inject": [], "span_grep": "x"}
    reps = [{"rep": 0, "base_yes": 0, "oracle_yes": 0, "span": None, "no_construible": "no cubre"}]
    reps[0]["prueba_entrega"] = RV.prueba_de_entrega(cfg, reps[0])
    v = RV.veredicto_de(reps, 4, cobertura_ok=True)
    assert v["veredicto"] == "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA" and v["reps_sin_prueba_de_entrega"] == [0]


def test_una_rep_firme_sigue_dando_alcanzable_aunque_otra_no_sea_construible():
    cfg = {"mode": "appendix", "inject": [], "span_grep": "x"}
    reps = [{"rep": 0, "base_yes": 0, "oracle_yes": 0, "span": None, "no_construible": "no cubre"},
            {"rep": 1, "base_yes": 0, "oracle_yes": 5, "span": "Retorno +/- al panel"}]
    for r in reps:
        r["prueba_entrega"] = RV.prueba_de_entrega(cfg, r)
    assert RV.veredicto_de(reps, 4)["veredicto"] == "ALCANZABLE"


# ── 5 · carrier ya servido ───────────────────────────────────────────────────────────────────
def test_carriers_ya_servidos_declara_los_prefijos_presentes_en_la_base():
    assert RV.carriers_ya_servidos(["d27b1a1b-69cd", "aaaa-1"], ["d27b1a1b", "bbbbbbbb"]) == ["d27b1a1b"]
    assert RV.carriers_ya_servidos([], ["d27b1a1b"]) == []


# ── 1 · recibo FULL vigente ──────────────────────────────────────────────────────────────────
def test_elegir_receipt_toma_el_mas_reciente_y_excluye_invalidos():
    paths = ["evals/s100_factlevel_full_v32_full_20260801.yaml",
             "evals\\s100_factlevel_full_v3_20260816.yaml",
             "evals/s100_factlevel_full_v2_INVALIDO_quota.yaml",
             "evals/s100_factlevel_full.yaml"]
    assert RV.elegir_receipt(paths).endswith("s100_factlevel_full_v3_20260816.yaml")
    assert RV.elegir_receipt(paths, explicito="evals/otro.yaml") == "evals/otro.yaml"
    with pytest.raises(ValueError):
        RV.elegir_receipt(["evals/s100_factlevel_full.yaml"])


# ── 4 · coste ────────────────────────────────────────────────────────────────────────────────
def test_cost_of_suma_por_modelo_y_no_inventa_precios():
    summary = {"n_calls": 3, "by_model_phase": [
        {"model": "gpt-5.5", "phase": "judge", "calls": 2, "in": 1_000_000, "out": 100_000, "cache_read": 0, "cache_write": 0},
        {"model": "modelo-x", "phase": "turn", "calls": 1, "in": 500, "out": 50, "cache_read": 0, "cache_write": 0},
    ]}
    c = UM.cost_of(summary)
    assert c["usd_total"] == 8.0            # 1M·5 + 0.1M·30
    assert c["by_model"]["modelo-x"]["usd"] is None and c["by_model"]["modelo-x"]["price"] == "DESCONOCIDO"
    assert c["usd_incluye_modelo_sin_precio"] is True


def test_usage_meter_agrega_por_modelo_y_fase_sin_instalar_sdk():
    m = UM.UsageMeter()
    m.phase = "judge"
    m._add("openai", "gpt-5.5", 100, 10, 0, 0, 0.1)
    m._add("openai", "gpt-5.5", 100, 10, 0, 0, 0.1)
    m.phase = "turn"
    m._add("anthropic", "claude-sonnet-4-6", 1000, 200, 0, 0, 0.5)
    s = m.summary()
    assert s["n_calls"] == 3
    assert {(a["model"], a["phase"], a["calls"]) for a in s["by_model_phase"]} == {("gpt-5.5", "judge", 2), ("claude-sonnet-4-6", "turn", 1)}
    assert m.summary(since=2)["n_calls"] == 1
