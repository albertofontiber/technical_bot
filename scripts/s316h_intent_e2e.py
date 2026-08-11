#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s316h — Gate 2 del flip de INTENT_LLM (DEC-203b): e2e del CAMINO SERVIDO, con recibo.

Qué prueba (mecánica de transporte, NO juicio — el juicio quedó zanjado en el gate
v1.1 con GO adjudicado; ANTI-GATE-SHOPPING: los canarios son casos de la cohorte
CONGELADA y su acierto se REGISTRA como informativo, jamás como criterio de PASS):

  0. off           — flag ausente ⇒ seam None + telemetría "off" (byte-inerte).
  1. frio          — celda de proceso vacía ⇒ primera llamada REAL construye el
                     cliente y paga el TLS; se mide esa latencia fría.
  2. caliente      — 4 llamadas más con el MISMO cliente de proceso (paridad con
                     producción: un proceso Railway vive días).
  3. timeout       — cliente real con timeout minúsculo ⇒ fail-open YA (sin la cola
                     de retries de ~19 s que max_retries=0 eliminó — Fable r11).
  4. key_mala      — credencial inválida ⇒ fail-open, sin excepción al técnico.
  5. construccion  — construir_intent_fn revienta (inyección declarada) ⇒ centinela
                     False, telemetría construction_failed, conducta OFF.

En TODOS los legs la composición es LA SERVIDA (lección r11 — paridad, no un símil):
`_intent_seam` de telegram_bot (el código del handler) + `resolve_conversational_turn`
real (con `rewrite` CENTINELA — el handler siempre pasa rewrite; Fable r12 M2 cazó que
omitirlo divergía la firma) + `asyncio.to_thread` + `build_rag_serving_trace` /
`validate_rag_serving_trace` (gate 1) sobre la telemetría que el turno produjo.

LÍMITE DECLARADO (Sol r12 C1): este script NO conduce `handle_message`. El pegamento
del handler (flag→seam→política→build site→log_query) queda gateado EN CI por
`tests/test_s316_transport_state_instrument.py::test_lever_intent_atraviesa_el_pegamento_del_handler`
(+ su espejo flag-off) — este script cubre lo que CI no puede: la red real.

Uso:   python scripts/s316h_intent_e2e.py
Coste: ~5 llamadas reales a Sonnet ≈ $0.01.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

os.environ["INTENT_LLM"] = ""          # arranque limpio; cada leg fija lo suyo

from src.config import ANTHROPIC_API_KEY  # noqa: E402
import src.bot.telegram_bot as bot  # noqa: E402
import src.orchestrator.intent_llm as intent_llm  # noqa: E402
from src.orchestrator.conversation_policy import WorkingState  # noqa: E402
from src.orchestrator.conversation_policy_impl import (  # noqa: E402
    resolve_conversational_turn,
)
from src.rag.runtime_trace import (  # noqa: E402
    build_rag_serving_trace,
    validate_rag_serving_trace,
)

# Canarios de la cohorte CONGELADA v1.1 (evals/s316g_intent_cohort_v1.yaml), verbatim.
_CANARIOS = [
    {"q": "¿es compatible con equipos Morley?", "estado": ("CAD-250",), "congelado": "compat"},
    {"q": "¿admite detectores Apollo?", "estado": ("CAD-250",), "congelado": "compat"},
    {"q": "¿y en Morley cómo se hace el reset?", "estado": ("NC-PF2",), "congelado": "switch"},
    {"q": "háblame de las centrales de Notifier", "estado": ("CAD-250",), "congelado": "switch"},
    {"q": "los Detnov me dan problemas, mejor dime cómo va el de Morley",
     "estado": ("CAD-250",), "congelado": "switch"},   # el caso mixto de Sol r11
]


def _ws(modelos: tuple, now: datetime) -> WorkingState:
    return WorkingState(last_target_models=modelos, last_query="consulta previa",
                        last_turn_at=now)


# (Fable r12 M2) El handler SIEMPRE pasa rewrite; omitirlo aquí divergía la firma
# del resolve servido. Centinela: mantiene la paridad de firma y REGISTRA si algún
# leg lo invoca (ninguno debería — los canarios son carry/switch, no rewrite).
_REWRITE_INVOCADO = {"n": 0}


def _rewrite_centinela(q_anaforica, _ws_arg):
    _REWRITE_INVOCADO["n"] += 1
    return q_anaforica


def _turno_servido(query: str, modelos: tuple) -> dict:
    """UN turno con la composición del handler: seam + resolve en to_thread + traza."""
    obs: dict = {}
    wrapper = bot._intent_seam(obs)
    now = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    if wrapper is not None:
        resolution, _estado = asyncio.run(asyncio.to_thread(
            resolve_conversational_turn, query, _ws(modelos, now), now,
            rewrite=_rewrite_centinela, intent=wrapper))
    else:
        resolution, _estado = resolve_conversational_turn(
            query, _ws(modelos, now), now, rewrite=_rewrite_centinela)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    trace = build_rag_serving_trace(
        coverage_trace={}, served_chunks=[], must_preserve_trace=None,
        must_preserve_outcome=None, release_policy={"profile": "legacy"},
        transport_parts=1, intent_obs=obs)
    return {
        "obs": obs, "elapsed_ms": elapsed_ms,
        "route": resolution.route.value, "rationale": resolution.rationale,
        "target_models": list(resolution.target_models or ()),
        "trace_valida": validate_rag_serving_trace(trace) == trace,
        "trace_intent": trace["intent"],
    }


def _leg(nombre: str, criterios: list, filas=None, **extra) -> dict:
    fallos = [c for c, ok in criterios if not ok]
    leg = {"leg": nombre, "pass": not fallos,
           "criterios": [c for c, _ in criterios], "fallos": fallos, **extra}
    if filas is not None:
        leg["filas"] = filas
    estado = "PASS" if leg["pass"] else "FAIL"
    print(f"  [{estado}] {nombre}" + (f" — fallos: {fallos}" if fallos else ""))
    return leg


def main() -> int:
    legs = []
    print("s316h — e2e del camino servido de INTENT_LLM (gate 2 del flip)\n")

    # --- leg 0: flag OFF -----------------------------------------------------
    os.environ["INTENT_LLM"] = ""
    obs_off: dict = {}
    seam_off = bot._intent_seam(obs_off)
    t_off = _turno_servido("¿y en Morley cómo se hace el reset?", ("NC-PF2",))
    legs.append(_leg("off", [
        ("seam None con flag OFF", seam_off is None),
        ("telemetria off", obs_off == {"status": "off", "decision": "none",
                                       "latency_ms": 0}),
        ("resolucion sin lever (rationale sin _llm)",
         not t_off["rationale"].endswith("_llm")),
        ("traza off valida", t_off["trace_valida"]
         and t_off["trace_intent"]["status"] == "off"),
    ]))

    # --- legs 1-2: frio + caliente (cliente REAL de proceso) -----------------
    os.environ["INTENT_LLM"] = "on"
    bot._INTENT_FN_CELL.clear()                    # proceso recién arrancado
    filas = []
    for i, c in enumerate(_CANARIOS):
        t = _turno_servido(c["q"], c["estado"])
        filas.append({
            "q": c["q"], "frio": i == 0,
            "decision": t["obs"].get("decision"),
            "latency_ms": t["obs"].get("latency_ms"),
            "turno_ms": t["elapsed_ms"], "route": t["route"],
            "rationale": t["rationale"], "trace_valida": t["trace_valida"],
            "coincide_congelado": t["obs"].get("decision") == c["congelado"],
        })
    fria, calientes = filas[0], filas[1:]

    # El rationale servido de carry lleva el prefijo de ruta
    # ("carry_forward:brand_compat_confirmed_llm"); el de switch va pelado.
    # Lo cazó la primera corrida de este e2e — el símil habría pasado.
    def _coherente(f):
        if f["decision"] == "switch":
            return f["route"] == "standalone" and \
                f["rationale"].endswith("new_brand_topic_switch_llm")
        if f["decision"] == "compat":
            return f["route"] == "carry_forward" and \
                f["rationale"].endswith("brand_compat_confirmed_llm")
        return False

    # (Sol r12 M2) Atestación de config SERVIDA: el fn que el seam construyó en el
    # leg frío — por su cableado real, no inyectado — debe llevar exactamente la
    # config de producción. Sin esto, el leg timeout (cliente alterado declarado)
    # no probaría nada sobre el default servido.
    config_servida = getattr(bot._INTENT_FN_CELL.get("fn"), "config", None)
    config_esperada = {"model": intent_llm.INTENT_MODEL,
                       "timeout_s": 6.0, "max_retries": 0}
    legs.append(_leg("frio", [
        ("invocado", fria["decision"] in ("compat", "switch", "fail_open")),
        ("respuesta real del API (no fail_open)",
         fria["decision"] in ("compat", "switch")),
        ("decision coherente con la resolucion", _coherente(fria)),
        ("config servida atestada (timeout 6 s, max_retries 0)",
         config_servida == config_esperada),
        ("traza valida", fria["trace_valida"]),
    ], filas=[fria], config_servida=config_servida))
    lat = sorted(f["latency_ms"] for f in calientes)
    legs.append(_leg("caliente", [
        ("4/4 con respuesta real del API",
         all(f["decision"] in ("compat", "switch") for f in calientes)),
        ("4/4 decision coherente con la resolucion",
         all(_coherente(f) for f in calientes)),
        ("4/4 traza valida", all(f["trace_valida"] for f in calientes)),
    ], filas=calientes,
       latencia_ms={"fria": fria["latency_ms"], "caliente_p50": lat[len(lat) // 2],
                    "caliente_max": lat[-1]}))

    # --- leg 3: timeout ⇒ fail-open sin cola de retries ----------------------
    # INYECCIÓN DECLARADA (Sol r12 M2): constructor REAL con timeout minúsculo,
    # primado en la celda. Prueba la CONDUCTA al vencer el timeout; que el default
    # servido es 6 s lo atesta el criterio de config del leg frío.
    fn_timeout = intent_llm.construir_intent_fn(ANTHROPIC_API_KEY, timeout_s=0.05)
    bot._INTENT_FN_CELL["fn"] = fn_timeout
    t_to = _turno_servido("¿y en Morley cómo se hace el reset?", ("NC-PF2",))
    legs.append(_leg("timeout", [
        ("fail-open (rationale failopen)",
         t_to["rationale"].endswith("brand_compat_failopen_llm")),
        ("carry preservado (conducta de hoy)",
         t_to["route"] == "carry_forward"
         and t_to["target_models"] == ["NC-PF2"]),
        ("telemetria fail_open", t_to["obs"]["decision"] == "fail_open"),
        ("sin cola de retries (turno < 3 s; con max_retries=2 eran ~19 s)",
         t_to["elapsed_ms"] < 3000),
        ("traza valida", t_to["trace_valida"]),
    ], turno_ms=t_to["elapsed_ms"],
       config_inyectada=getattr(fn_timeout, "config", None)))

    # --- leg 4: credencial invalida ⇒ fail-open, sin excepcion ---------------
    bot._INTENT_FN_CELL["fn"] = intent_llm.construir_intent_fn(
        "sk-ant-api03-invalida-e2e")
    t_key = _turno_servido("¿y en Morley cómo se hace el reset?", ("NC-PF2",))
    legs.append(_leg("key_mala", [
        ("fail-open (rationale failopen)",
         t_key["rationale"].endswith("brand_compat_failopen_llm")),
        ("carry preservado", t_key["route"] == "carry_forward"),
        ("telemetria fail_open", t_key["obs"]["decision"] == "fail_open"),
        ("rapido (turno < 10 s)", t_key["elapsed_ms"] < 10_000),
        ("traza valida", t_key["trace_valida"]),
    ], turno_ms=t_key["elapsed_ms"]))

    # --- leg 5: construccion fallida (inyeccion declarada) -------------------
    bot._INTENT_FN_CELL.clear()
    _orig = intent_llm.construir_intent_fn

    def _revienta(*_a, **_k):
        raise RuntimeError("inyeccion e2e: construccion imposible")

    intent_llm.construir_intent_fn = _revienta
    try:
        t_con = _turno_servido("¿y en Morley cómo se hace el reset?", ("NC-PF2",))
    finally:
        intent_llm.construir_intent_fn = _orig
    legs.append(_leg("construccion", [
        ("telemetria construction_failed",
         t_con["obs"]["status"] == "construction_failed"),
        ("centinela False en la celda (no reintenta en caliente)",
         bot._INTENT_FN_CELL.get("fn") is False),
        ("conducta OFF (carry failopen)",
         t_con["rationale"].endswith("brand_compat_failopen_llm")
         and t_con["route"] == "carry_forward"),
        ("traza valida", t_con["trace_valida"]
         and t_con["trace_intent"]["status"] == "construction_failed"),
    ]))
    bot._INTENT_FN_CELL.clear()

    # --- recibo --------------------------------------------------------------
    # (Sol r12 C2 + Fable r12 F3) PROVENIENCIA: el commit solo identifica los bytes
    # ejecutados si el arbol esta limpio; con arbol sucio, los sha256 de los
    # artefactos son el ancla real. El recibo final se genera SOBRE EL COMMIT.
    import hashlib
    import subprocess
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                         cwd=str(ROOT), text=True).strip()
        sucio = subprocess.check_output(["git", "status", "--porcelain"],
                                        cwd=str(ROOT), text=True).strip()
        git_estado = f"dirty ({len(sucio.splitlines())} paths)" if sucio else "clean"
    except Exception:                              # noqa: BLE001
        commit, git_estado = "desconocido", "desconocido"
    artefactos = [
        "scripts/s316h_intent_e2e.py", "src/bot/telegram_bot.py",
        "src/rag/runtime_trace.py", "src/orchestrator/intent_llm.py",
        "src/orchestrator/conversation_policy_impl.py",
        "src/orchestrator/conversation_policy.py",
    ]
    artefactos_sha256 = {
        rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16]
        for rel in artefactos
    }
    todo_pass = all(leg["pass"] for leg in legs)
    coinciden = sum(1 for f in filas if f["coincide_congelado"])
    recibo = {
        "gate": "s316h intent e2e servido v1 (gate 2 del flip, DEC-203b)",
        "modelo": intent_llm.INTENT_MODEL,
        "composicion": "_intent_seam (telegram_bot) + resolve_conversational_turn"
                       " (rewrite centinela) + asyncio.to_thread"
                       " + build/validate_rag_serving_trace",
        "pegamento_handler_gateado_en_ci":
            "tests/test_s316_transport_state_instrument.py::"
            "test_lever_intent_atraviesa_el_pegamento_del_handler (Sol r12 C1)",
        "criterio_pass": "SOLO mecanica de transporte; el acierto de canarios es"
                         " informativo (el juicio quedo zanjado en el gate v1.1)",
        "commit": commit,
        "git_estado": git_estado,
        "artefactos_sha256": artefactos_sha256,
        "rewrite_centinela_invocaciones": _REWRITE_INVOCADO["n"],
        "veredicto": "PASS" if todo_pass else "FAIL",
        "canarios_coinciden_con_cohorte": f"{coinciden}/{len(filas)} (informativo)",
        "legs": legs,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = ROOT / "evals" / "s316h_intent_e2e_result_v1.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nVEREDICTO: {recibo['veredicto']} · canarios {coinciden}/{len(filas)}"
          f" (informativo)\nrecibo → {out}")
    return 0 if todo_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
