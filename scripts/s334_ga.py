#!/usr/bin/env python3
"""s334 — gates GA0/GA1 (v2 §4) sobre la conversación REAL de la tarde.

GA0 (flags off): los turnos de hoy reproducen la conducta actual (la corrección
con marca corrupta NO dispara nada; el estado no se toca tras atajo).
GA1 (flags on):
  (a) fuzzy con typo NO TABULADO («quería decir de morlei» — Sol-1: lo observado
      ya está tabulado, el gate mide el mecanismo con el typo de mañana), matriz
      ASR_AVISOS on/off (Fable-2: con la tabla encendida el caso tabulado KIDE
      lo reescribe la TABLA antes — se mide y se declara el orden de capas).
  (b) R8 + clasificador REAL: atajo simulado (estado refrescado por
      `advance_after_shortcut`) → «Ahora quiero Morley» → el veredicto del
      clasificador con `last_query` FRESCA es la HIPÓTESIS a medir (Sol-5) —
      se estampa, no se presupone. + e2e de la respuesta si CORRECCION.

Uso: python scripts/s334_ga.py [--out evals/s334_ga_result_v1.json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "replace")

FLAGS_S334 = ("F1_CORRECCION_FUZZY", "F1_ESTADO_ATAJOS")
BASE_ON = {"F1_MARCA_CORRECCION": "on", "F1_CORRECCION_LLM": "on",
           "ASR_AVISOS": "on"}


def _set(flags: dict) -> None:
    for k in list(BASE_ON) + list(FLAGS_S334):
        os.environ.pop(k, None)
    os.environ.update(flags)


def _check(cond, etiqueta, detalle, fallos, filas):
    if not cond:
        fallos.append(etiqueta)
    print(f"  [{'PASS' if cond else 'FAIL'}] {etiqueta} {str(detalle)[:110]}")
    filas.append({"check": etiqueta, "ok": bool(cond), "detalle": str(detalle)[:400]})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evals" / "s334_ga_result_v1.json"))
    args = ap.parse_args()

    from datetime import timedelta

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

    def _ws(lq):
        return WorkingState(last_query=lq, last_turn_at=now - timedelta(seconds=60))

    # ── GA0: flags s334 OFF (los s332/s333 quedan como en prod: on)
    print("== GA0 (s334 off)")
    _set(dict(BASE_ON))
    res, _ = resolve_conversational_turn("Quería decir de KIDE.",
                                         _ws("¿Qué centrales ID tienes?"), now)
    _check(res.rationale not in ("brand_correction_fuzzy", "brand_correction_fuzzy_llm"),
           "ga0_fuzzy_apagado_no_dispara", res.rationale, fallos, filas)

    # ── GA1(a): fuzzy ON, typo NO tabulado, matriz ASR
    print("== GA1(a) fuzzy (typo no tabulado + matriz ASR)")
    for asr in ("on", "off"):
        flags = dict(BASE_ON, F1_CORRECCION_FUZZY="on", F1_ESTADO_ATAJOS="on")
        flags["ASR_AVISOS"] = asr
        _set(flags)
        res, _ = resolve_conversational_turn("quería decir de morlei",
                                             _ws("¿Qué centrales de KIDDE tienes?"), now)
        _check(res.rationale == "brand_correction_fuzzy"
               and res.asunciones and res.asunciones[0].kind == "marca_fuzzy"
               and res.asunciones[0].asumido == "Morley",
               f"ga1a_fuzzy_morlei_asr_{asr}",
               f"{res.rationale} · {[a.kind for a in res.asunciones]}", fallos, filas)
    # El caso TABULADO con ASR on: la TABLA gana antes (orden de capas, declarado)
    from src.bot.whisper_vocabulary import corregir_transcripcion_con_asunciones
    _set(dict(BASE_ON, F1_CORRECCION_FUZZY="on"))
    texto, asun = corregir_transcripcion_con_asunciones("Quería decir de KIDE.")
    _check("Kidde" in texto and [a.kind for a in asun] == ["marca_asr"],
           "ga1a_capa_tabla_gana_en_tabulado", texto, fallos, filas)

    # ── GA1(b): R8 + clasificador REAL — la HIPÓTESIS-Morley se MIDE
    print("== GA1(b) R8 + clasificador real (hipótesis a medir)")
    from src.orchestrator.correccion_llm import construir_correccion_fn
    fn = construir_correccion_fn(os.environ.get("ANTHROPIC_API_KEY", ""))
    ws_atajo = advance_after_shortcut(
        WorkingState(), "¿Qué centrales de KIDDE tienes?", "📦 KIDDE — central (36…)", now)
    _check(ws_atajo.last_query == "¿Qué centrales de KIDDE tienes?",
           "ga1b_atajo_refresca_last_query", ws_atajo.last_query, fallos, filas)
    res, _ = resolve_conversational_turn("Ahora quiero Morley", ws_atajo, now,
                                         correccion=fn)
    veredicto = getattr(fn, "ultima", None)
    recibo["hipotesis_morley"] = {
        "rationale": res.rationale, "ultima": veredicto,
        "qfr": res.query_for_retrieval[:200]}
    print(f"  [MEDIDO] hipotesis_morley: rationale={res.rationale} ultima={veredicto}")
    if res.rationale == "brand_correction_llm":
        from src.orchestrator import from_production, run_turn
        from src.orchestrator.telegram_adapter import build_turn_request
        req = build_turn_request(
            query=res.query_for_retrieval, query_for_retrieval=res.query_for_retrieval,
            target_models=res.target_models, available_models=res.available_models,
            update_id=0, chat_id=0, source="harness", transcription=None,
            turn_identity=res.turn_identity)
        turn = run_turn(req, from_production())
        ans = turn.generation["answer"]
        recibo["hipotesis_morley"]["answer"] = ans
        _check("No he encontrado información relevante" not in ans,
               "ga1b_respuesta_morley_no_vacia", ans[:120], fallos, filas)

    for k in list(BASE_ON) + list(FLAGS_S334):
        os.environ.pop(k, None)
    recibo["fallos"] = fallos
    Path(args.out).write_text(json.dumps(recibo, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"\nfallos={len(fallos)} · recibo → {args.out}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
