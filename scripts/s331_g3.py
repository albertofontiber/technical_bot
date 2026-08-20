#!/usr/bin/env python3
"""s331 G3 (v6 §4, patrón DEC-162e) — A/B de CONDUCTA con N reps por brazo sobre
los dos turnos decisivos leídos en G1:

  · KIDDE-T3 (carry con identidad): «Programación principalmente.» tras
    «Sobre la 2X-AF1-FBS.» — la clase amnésica del incidente.
  · MIXTO-C1 (A resuelve familia + mención de puerta 1): «La EMA1224B4RW-XQ me
    da fallo de tierra.» — el reconocimiento visible.

Checks DETERMINISTAS por respuesta (frases amnésicas prohibidas / reconocimiento
exigido) + todas las respuestas guardadas verbatim para lectura (DEC-092b). El
veredicto formal es del conteo determinista; la lectura arbitra artefactos.

Uso: python scripts/s331_g3.py [--reps 6] [--out evals/s331_g3_v1.json]
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

ON_FLAGS = {"F1_RESOLVE_GOVERNED": "on", "F1_MENTION_PRECEDENCE": "on",
            "GENERATOR_NO_REASK": "on", "IDENTITY_FETCH": "on"}
S331_KEYS = tuple(ON_FLAGS)

# Frases de la CLASE AMNÉSICA (el incidente + la plantilla determinista):
AMNESIA = [
    r"qué variante exacta",
    r"modelo concreto que estás usando",
    r"mira la etiqueta del panel",
    r"¿qué modelo exacto estás programando\?",
]
RECONOCE_MENCION = r"EMA1224B4RW-XQ"


def _set_arm(on: bool) -> None:
    for k in S331_KEYS:
        os.environ.pop(k, None)
    if on:
        os.environ.update(ON_FLAGS)


def _gen(query: str, ws):
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
    return turn.generation["answer"], ws2


def _caso_kidde(_rep: int) -> str:
    from src.orchestrator.conversation_policy import WorkingState
    _, ws = _gen("Sobre la 2X-AF1-FBS.", WorkingState())
    answer, _ = _gen("Programación principalmente.", ws)
    return answer


def _caso_mixto(_rep: int) -> str:
    from src.orchestrator.conversation_policy import WorkingState
    answer, _ = _gen("La EMA1224B4RW-XQ me da fallo de tierra.", WorkingState())
    return answer


def _amnesica(answer: str) -> str | None:
    low = answer.lower()
    for pat in AMNESIA:
        if re.search(pat.lower(), low):
            return pat
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "evals" / "s331_g3_v1.json"))
    args = ap.parse_args()

    from src.rag import catalog_resolver as CR
    receipt = {"manifest": {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True).stdout.strip(),
        "reps": args.reps, "on_flags": ON_FLAGS},
        "casos": {}}

    for caso, fn, check in (
        ("kidde_t3", _caso_kidde, "amnesia"),
        ("mixto_c1", _caso_mixto, "reconoce"),
    ):
        receipt["casos"][caso] = {}
        for arm in ("off", "on"):
            _set_arm(arm == "on")
            CR.refresh_presence()
            reps = []
            for i in range(args.reps):
                ans = fn(i)
                if check == "amnesia":
                    hit = _amnesica(ans)
                    ok = hit is None
                    det = hit or ""
                else:
                    ok = bool(re.search(RECONOCE_MENCION, ans))
                    det = "reconoce" if ok else "NO reconoce la mención"
                reps.append({"ok": ok, "detalle": det, "answer": ans})
                print(f"[{caso}/{arm}] rep{i}: {'PASS' if ok else 'FAIL'} {det[:60]}")
            receipt["casos"][caso][arm] = {
                "pass": sum(r["ok"] for r in reps), "n": len(reps), "reps": reps}

    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    on_k = receipt["casos"]["kidde_t3"]["on"]
    off_k = receipt["casos"]["kidde_t3"]["off"]
    on_m = receipt["casos"]["mixto_c1"]["on"]
    print(f"\nkidde_t3 sin-amnesia: OFF {off_k['pass']}/{off_k['n']} → "
          f"ON {on_k['pass']}/{on_k['n']}")
    print(f"mixto_c1 reconoce: ON {on_m['pass']}/{on_m['n']}")
    print(f"recibo → {args.out}")
    return 0 if on_k["pass"] == on_k["n"] and on_m["pass"] == on_m["n"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
