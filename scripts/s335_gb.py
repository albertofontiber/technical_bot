#!/usr/bin/env python3
"""s335 — gates GB1/GB2 (evals/s335_propuesta_v2.md §4).

GB1 (plan PURO, sin red): la gramática v2 con flag ON sirve las formas
desiderativas/imperativas y el punto terminal de Whisper; con OFF el plan es el
de hoy; los 6 negativos técnicos siguen al RAG en los dos regímenes.

GB2 (pieza B, con clasificador REAL y RAG real):
  (a) atajo simulado (R8) → «Y ahora quiero ver las de Morley.» NO la traga el
      atajo (sin sustantivo) y la guardia PRESERVA (models=() tras R8);
  (b) cruce `_SWITCH_FRASE` (dúo s335 Fable-3, MEDIDO no presumido): con modelos
      BINDEADOS la guardia INVALIDA → el estado muere ANTES de resolve y el
      clasificador queda SIN población (sin last_query) — la población real del
      cue anafórico son los estados con models=() (R8/frescos);
  (c) resolve con el clasificador REAL sobre el estado R8 → brand_correction_llm
      + override reconstruida (la fila obligatoria p15, medida END-TO-END);
  (d) RAG real sobre la override → contenido Morley no-vacío y sin cross-brand.
      LIMITACIÓN DECLARADA (Sol-1): la respuesta es síntesis RAG, NO el listado
      gobernado — lista potencialmente parcial (clase s307); el listado completo
      llega por pieza A cuando el usuario formula la petición entera.

Uso: python scripts/s335_gb.py [--out evals/s335_gb_result_v1.json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "replace")

BASE_ON = {"F1_MARCA_CORRECCION": "on", "F1_CORRECCION_LLM": "on",
           "ASR_AVISOS": "on", "F1_CORRECCION_FUZZY": "on",
           "F1_ESTADO_ATAJOS": "on"}


def _check(cond, etiqueta, detalle, fallos, filas):
    if not cond:
        fallos.append(etiqueta)
    print(f"  [{'PASS' if cond else 'FAIL'}] {etiqueta} {str(detalle)[:110]}")
    filas.append({"check": etiqueta, "ok": bool(cond), "detalle": str(detalle)[:400]})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evals" / "s335_gb_result_v1.json"))
    args = ap.parse_args()

    from src.orchestrator import turn_plan as tp
    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.conversation_policy_impl import (
        advance_after_shortcut,
        resolve_conversational_turn,
    )

    now = datetime.now(timezone.utc)
    fallos: list[str] = []
    filas: list[dict] = []
    recibo = {"manifest": {
        "ts": now.isoformat(timespec="seconds"),
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True).stdout.strip()},
        "filas": filas}

    def _plan(texto, marca, fraseos, estado=()):
        meta = tp.Meta(inventario_fraseos=fraseos)
        return tp.plan_turn(texto, estado, meta,
                            {tp.Hecho("marca_servida", marca): True})

    # ── GB1: plan puro
    print("== GB1 (plan puro, flag on/off)")
    POS = [("Quiero ver las centrales de Morley.", "Morley"),
           ("dime qué centrales de Morley tienes.", "Morley"),
           ("I want to see Morley panels", "Morley"),
           ("show me Morley panels", "Morley"),
           ("I want to see Morley catalogs", "Morley")]
    for q, marca in POS:
        _check(_plan(q, marca, True).ruta == "inventario",
               f"gb1_on_inventario: {q[:40]}", _plan(q, marca, True).ruta,
               fallos, filas)
    _check(_plan(POS[0][0], "Morley", False).ruta == "conversacional",
           "gb1_off_no_cambio", _plan(POS[0][0], "Morley", False).ruta,
           fallos, filas)
    NEG = ["quiero saber qué centrales Morley tienen salida de relé",
           "quiero saber si las centrales de Morley soportan lazos redundantes",
           "necesito ver el esquema de conexión de la central de Morley",
           "dime qué centrales de Morley tienen certificación EN 54",
           "muéstrame cómo configurar las centrales de Morley",
           "quiero ver las centrales de Morley conectadas en red"]
    for q in NEG:
        rutas = {_plan(q, "Morley", f).ruta for f in (False, True)}
        _check(rutas == {"conversacional"}, f"gb1_negativo_rag: {q[:44]}",
               rutas, fallos, filas)
    for f in (False, True):
        _check(_plan("¿Qué centrales de KIDDE tienes?", "KIDDE", f).ruta
               == "inventario", f"gb1_replay_t1_fraseos_{f}", "", fallos, filas)

    # ── GB2: pieza B end-to-end
    print("== GB2 (R8 → clasificador REAL → RAG)")
    for k, v in BASE_ON.items():
        os.environ[k] = v
    T2 = "Y ahora quiero ver las de Morley."
    ws_atajo = advance_after_shortcut(
        WorkingState(), "¿Qué centrales de KIDDE tienes?",
        "📦 KIDDE — centrales (listado)", now - timedelta(seconds=60))

    # (a) el atajo NO traga la anafórica; la guardia PRESERVA con models=()
    for f in (False, True):
        p = _plan(T2, "Morley", f, estado=tuple(ws_atajo.last_target_models))
        _check(p.ruta == "conversacional" and p.transicion == tp.PRESERVAR,
               f"gb2a_anaforica_a_cascada_fraseos_{f}",
               f"{p.ruta}/{p.transicion}", fallos, filas)

    # (b) cruce _SWITCH_FRASE MEDIDO: con modelos bindeados, INVALIDAR mata el
    # estado antes de resolve → clasificador sin población (conducta de HOY,
    # independiente del flag — se estampa el hecho, no se presume).
    p_bind = tp.plan_turn(T2, ("NC-PF2",), tp.Meta(inventario_fraseos=True),
                          {tp.Hecho("marca_servida", "Morley"): True})
    _check(p_bind.transicion == tp.INVALIDAR
           and p_bind.transicion_marca == "Morley",
           "gb2b_cruce_switch_frase_con_modelos",
           f"{p_bind.transicion}/{p_bind.transicion_marca}", fallos, filas)
    recibo["cruce_switch_frase"] = {
        "con_modelos_bindeados": "INVALIDAR → estado muerto antes de resolve → "
                                 "clasificador SIN población (sin last_query)",
        "con_estado_r8_models_vacios": "PRESERVAR → last_query viva → clasificador "
                                       "EN población (la vía del caso fabef50b)"}

    # (c) resolve con clasificador REAL (fila obligatoria p15, end-to-end)
    from src.orchestrator.correccion_llm import construir_correccion_fn
    fn = construir_correccion_fn(os.environ.get("ANTHROPIC_API_KEY", ""))
    res, _ = resolve_conversational_turn(T2, ws_atajo, now, correccion=fn)
    veredicto = getattr(fn, "ultima", None)
    recibo["clasificador_e2e"] = {"rationale": res.rationale, "ultima": veredicto,
                                  "qfr": res.query_for_retrieval[:200]}
    _check(res.rationale == "brand_correction_llm",
           "gb2c_clasificador_correccion", f"{res.rationale} · {veredicto}",
           fallos, filas)

    # (d) RAG real sobre la override — barra: Morley no-vacío, sin cross-brand.
    if res.rationale == "brand_correction_llm":
        from src.orchestrator import from_production, run_turn
        from src.orchestrator.telegram_adapter import build_turn_request
        req = build_turn_request(
            query=res.query_for_retrieval,
            query_for_retrieval=res.query_for_retrieval,
            target_models=res.target_models,
            available_models=res.available_models,
            update_id=0, chat_id=0, source="harness", transcription=None,
            turn_identity=res.turn_identity)
        turn = run_turn(req, from_production())
        ans = turn.generation["answer"]
        recibo["respuesta_morley"] = ans
        _check("No he encontrado información relevante" not in ans
               and "morley" in ans.lower(),
               "gb2d_respuesta_morley_no_vacia", ans[:120], fallos, filas)
        _check("kidde" not in ans.lower(), "gb2d_sin_cross_brand",
               "kidde ausente" if "kidde" not in ans.lower() else "KIDDE EN LA RESPUESTA",
               fallos, filas)
    recibo["limitacion_declarada"] = (
        "La respuesta de (d) es síntesis RAG sobre la override — NO el listado "
        "gobernado del atajo (inalcanzable desde F1, oráculo s333): lista "
        "potencialmente PARCIAL (clase s307). La vía gobernada y completa es la "
        "pieza A (INVENTARIO_FRASEOS) cuando la petición se formula entera.")

    for k in BASE_ON:
        os.environ.pop(k, None)
    recibo["fallos"] = fallos
    Path(args.out).write_text(json.dumps(recibo, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"\nfallos={len(fallos)} · recibo → {args.out}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
