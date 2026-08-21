#!/usr/bin/env python3
"""s332 — gates GC0/GC1/GC3 (v2 §8) sobre la mañana REAL del 21-ago.

GC0 (flags off): conducta servida byte-idéntica — el normalizador de voz no toca
BQide/ID (la fila death-knob sigue corrigiendo, conducta de hoy) y «me refería a
Kidde» cae en `new_brand_no_state` (la plantilla vacía del incidente).
GC1 (flags on): BQide reescrito+asunción · ID intacto+aviso · «id» minúscula y
ID3000 sin disparar · corrección → `brand_correction_rebuild` con la pregunta
anterior dentro y respuesta e2e SOLO-Kidde no-vacía.
GC3: estabilidad ON del par (N reps), respuestas guardadas verbatim (DEC-092b).

Matiz de instrumento DECLARADO: las líneas 🏷/ℹ️ de la confirmación y el sufijo
son capa bot (unit-tests propios); aquí se mide normalizador+cascada+e2e.

Uso: python scripts/s332_gc.py [--reps 4] [--out evals/s332_gc_v1.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "replace")

FLAGS = ("ASR_AVISOS", "F1_MARCA_CORRECCION")

# La conversación real (query_logs 21-ago 07:45-48Z) + controles del homógrafo:
VOZ_BQIDE = "¿Qué centrales BQide tienes?"
VOZ_ID = "¿Qué centrales ID tienes?"
VOZ_ID2 = "¿Qué centrales de la marca ID tienes?"
CTRL_ID_MIN = "id al menú de configuración del panel"
CTRL_ID3000 = "la ID3000 está en fallo de tierra"
CORRECCION = "me refería a Kidde"

PLANTILLA_VACIA = "No he encontrado información relevante"


def _flags(on: bool) -> None:
    for k in FLAGS:
        os.environ.pop(k, None)
    if on:
        os.environ.update({k: "on" for k in FLAGS})


def _norm(texto: str):
    from src.bot.voice_query_normalization import normalize_voice_query
    r = normalize_voice_query(texto)
    return {
        "raw": r.raw,
        "normalized": r.normalized,
        "asunciones": [
            {"kind": a.kind, "modo": a.modo, "detectado": a.detectado,
             "asumido": a.asumido}
            for a in getattr(r, "asunciones", ())
        ],
    }


def _resolver(query: str, ws):
    from src.orchestrator.conversation_policy_impl import (
        advance_working_state,
        resolve_conversational_turn,
    )
    now = datetime.now(timezone.utc)
    res, ws2 = resolve_conversational_turn(query, ws, now)
    ws3 = advance_working_state(ws2, res, query, "(gate)", now, res.available_models)
    return res, ws3


def _e2e(query: str, ws):
    from src.orchestrator import from_production, run_turn
    from src.orchestrator.conversation_policy_impl import (
        advance_working_state,
        resolve_conversational_turn,
    )
    from src.orchestrator.telegram_adapter import build_turn_request
    now = datetime.now(timezone.utc)
    res, ws2 = resolve_conversational_turn(query, ws, now)
    req = build_turn_request(
        query=res.query_for_retrieval, query_for_retrieval=res.query_for_retrieval,
        target_models=res.target_models, available_models=res.available_models,
        update_id=0, chat_id=0, source="harness", transcription=None,
        turn_identity=res.turn_identity,
    )
    turn = run_turn(req, from_production())
    answer = turn.generation["answer"]
    ws3 = advance_working_state(ws2, res, query, answer[:500], now,
                                res.available_models)
    return res, answer, ws3


def _check(cond: bool, etiqueta: str, detalle: str, fallos: list) -> dict:
    if not cond:
        fallos.append(etiqueta)
    print(f"  [{'PASS' if cond else 'FAIL'}] {etiqueta} {detalle[:100]}")
    return {"check": etiqueta, "ok": cond, "detalle": detalle[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "evals" / "s332_gc_v1.json"))
    args = ap.parse_args()

    from src.orchestrator.conversation_policy import WorkingState

    recibo: dict = {"manifest": {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True).stdout.strip(),
        "reps": args.reps, "flags": list(FLAGS)},
        "gc0": [], "gc1": [], "gc3": {}}
    fallos: list[str] = []

    # ---------- GC0: flags OFF = conducta de hoy ----------
    print("== GC0 (off)")
    _flags(False)
    for q in (VOZ_BQIDE, VOZ_ID, VOZ_ID2, CTRL_ID_MIN, CTRL_ID3000):
        n = _norm(q)
        recibo["gc0"].append(_check(
            n["normalized"] == q and not n["asunciones"],
            f"gc0_norm_intacto:{q[:24]}", n["normalized"], fallos))
    n = _norm("la central death knob no arma")
    recibo["gc0"].append(_check(
        "Detnov" in n["normalized"] and not n["asunciones"],
        "gc0_deathknob_sigue_corrigiendo_muda", n["normalized"], fallos))
    _, ws = _resolver(VOZ_BQIDE, WorkingState())
    res, _ = _resolver(CORRECCION, ws)
    recibo["gc0"].append(_check(
        res.rationale == "new_brand_no_state",
        "gc0_correccion_statu_quo", res.rationale or "", fallos))

    # ---------- GC1: flags ON ----------
    print("== GC1 (on)")
    _flags(True)
    n = _norm(VOZ_BQIDE)
    recibo["gc1"].append(_check(
        "Kidde" in n["normalized"]
        and [a["modo"] for a in n["asunciones"]] == ["reescrito"],
        "gc1_bqide_reescrito_con_asuncion", json.dumps(n, ensure_ascii=False),
        fallos))
    for q in (VOZ_ID, VOZ_ID2):
        n = _norm(q)
        recibo["gc1"].append(_check(
            n["normalized"] == q
            and [a["modo"] for a in n["asunciones"]] == ["aviso"],
            f"gc1_id_intacto_con_aviso:{q[:24]}",
            json.dumps(n, ensure_ascii=False), fallos))
    for q in (CTRL_ID_MIN, CTRL_ID3000):
        n = _norm(q)
        recibo["gc1"].append(_check(
            n["normalized"] == q and not n["asunciones"],
            f"gc1_control_sin_disparo:{q[:24]}", n["normalized"], fallos))
    _, ws = _resolver(VOZ_BQIDE, WorkingState())
    res, answer, _ = _e2e(CORRECCION, ws)
    recibo["gc1"].append(_check(
        res.rationale == "brand_correction_rebuild"
        and VOZ_BQIDE in res.query_for_retrieval
        and "Kidde" in res.query_for_retrieval,
        "gc1_correccion_rebuild", res.query_for_retrieval, fallos))
    sin_plantilla = PLANTILLA_VACIA not in answer
    sin_crossbrand = not re.search(r"\bID3000\b|\bID3002\b|Notifier|Morley|Detnov",
                                   answer)
    recibo["gc1"].append(_check(
        sin_plantilla and sin_crossbrand,
        "gc1_respuesta_kidde_no_vacia_sin_crossbrand", answer[:200], fallos))
    recibo["gc1"].append({"answer_verbatim": answer})

    # ---------- GC3: estabilidad ON (N reps, respuestas guardadas) ----------
    print(f"== GC3 (on, reps={args.reps})")
    reps = []
    for i in range(args.reps):
        _, ws = _resolver(VOZ_BQIDE, WorkingState())
        res, answer, _ = _e2e(CORRECCION, ws)
        ok = (res.rationale == "brand_correction_rebuild"
              and PLANTILLA_VACIA not in answer)
        reps.append({"rep": i, "ok": ok, "rationale": res.rationale,
                     "answer": answer})
        print(f"  rep{i}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            fallos.append(f"gc3_rep{i}")
    recibo["gc3"] = {"pass": sum(r["ok"] for r in reps), "n": len(reps),
                     "reps": reps}

    recibo["fallos"] = fallos
    Path(args.out).write_text(json.dumps(recibo, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"\nfallos={len(fallos)} → {args.out}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
