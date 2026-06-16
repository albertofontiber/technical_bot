#!/usr/bin/env python3
"""s77 HANDLER SMOKE — verifica el routing del gate de Option D por el HANDLER REAL (lección #40).

La lección #40 (la más cara del proyecto): el smoke de un ship DEBE entrar por `handle_message`
completo, NO por `retrieve_chunks` (el eval bypasea los gates pre-retrieval → shippeé un NO-OP en
s73). Esto llama el `handle_message` REAL (telegram_bot.py:248) y verifica la decisión del gate en
AMBAS direcciones. Se mockea SOLO `has_consent` (True) y `_process_query` (recorder) para AISLAR la
decisión del gate — el comportamiento del RAG en fall-through ya se midió en s77_fallthrough_measure.

Aserciones:
  - 6 catalog-miss (marca correcta, lookup=None)      → FALL-THROUGH (Option D; antes: hard-refuse).
  - marca GENUINAMENTE ausente (Siemens)              → REFUSE (no se rompe el fallo opuesto).
  - mismatch RP1r (hp011, CUT_A_mismatch)             → REFUSE-mismatch (rama NO tocada).
  - control marca+modelo correctos (Notifier AFP-400) → FALL-THROUGH (sin cambio).
  - saludo                                            → greeting (sin cambio).
  - NINGUNA query debe producir ya "No tengo información sobre el modelo X" (mensaje eliminado).
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"

import asyncio
import sys
import types
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["LEVER2_IDENTITY"] = "off"
os.environ["LEVER2_PM_RESCUE"] = "off"
sys.path.insert(0, str(ROOT))

import src.bot.telegram_bot as tb  # noqa: E402

_CALLED = {"process": False}


class _Chat:
    async def send_action(self, *a, **k):
        pass


class _Msg:
    def __init__(self, text):
        self.text = text
        self.replies = []
        self.chat = _Chat()

    async def reply_text(self, txt, **kw):
        self.replies.append(txt)


class _User:
    id = 999999


class _Update:
    def __init__(self, text):
        self.message = _Msg(text)
        self.effective_user = _User()


async def _fake_process(update, context, query, *a, **k):
    _CALLED["process"] = True


def classify(update: _Update) -> str:
    if _CALLED["process"]:
        return "FALL_THROUGH"
    txt = " ".join(update.message.replies)
    if "No tengo información sobre el modelo" in txt:
        return "REFUSE_model_not_found(OLD!)"  # NO debería aparecer tras Option D
    if "No dispongo de manuales de" in txt:
        return "REFUSE_manufacturer_absent"
    if "es un producto de" in txt or " no de " in txt:
        return "REFUSE_A_mismatch"
    if "¡Hola!" in txt:
        return "greeting"
    if not txt:
        return "NO_REPLY"
    return f"OTHER_REPLY: {txt[:60]}"


CASES = [
    # (etiqueta, query, esperado)
    ("cat013 CAD-150", "Tengo una central Detnov CAD-150 y me ha sobrado un detector Notifier SDX-751; ¿es compatible?", "FALL_THROUGH"),
    ("cat016 CAD-150", "En la Detnov CAD-150, ¿cómo se da de alta un detector nuevo en el lazo?", "FALL_THROUGH"),
    ("hp003 CAD-150", "¿Cómo se conectan las baterías de 24V en la Detnov CAD-150?", "FALL_THROUGH"),
    ("hp009 ZXe", "¿Cuál es la resistencia de fin de línea para los lazos de la central Morley ZXe?", "FALL_THROUGH"),
    ("hp018 ZXe", "¿Cómo se conecta una sirena convencional en las salidas de la Morley ZXe?", "FALL_THROUGH"),
    ("cat021 40-40", "Necesito un detector de llama SharpEye «40/40» (Spectrex) para una instalación; ¿qué modelo pido?", "FALL_THROUGH"),
    ("ABSENT Siemens", "¿Cómo se programa la central de incendios Siemens Cerberus FC724?", "REFUSE_manufacturer_absent"),
    ("hp011 RP1r mismatch", "En la Morley RP1r, después de descargar la extinción el sistema no vuelve a normal tras resetear. ¿Qué comprobar?", "REFUSE_A_mismatch"),
    ("CONTROL AFP-400", "La Notifier AFP-400 muestra el aviso 'Tierra'. ¿Qué significa?", "FALL_THROUGH"),
    ("greeting", "hola", "greeting"),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    tb.has_consent = lambda uid: True
    tb._process_query = _fake_process

    ctx = types.SimpleNamespace(user_data={})
    print("=== s77 HANDLER SMOKE (handle_message real, gate routing) ===\n")
    ok = 0
    for label, q, expected in CASES:
        _CALLED["process"] = False
        upd = _Update(q)
        asyncio.run(tb.handle_message(upd, ctx))
        got = classify(upd)
        match = got == expected
        ok += match
        mark = "OK " if match else "XX "
        print(f"{mark} {label:22} esperado={expected:28} got={got}")
        if not match and upd.message.replies:
            print(f"      reply: {upd.message.replies[0][:90]}")
    print(f"\n{ok}/{len(CASES)} casos correctos")
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
