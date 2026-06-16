#!/usr/bin/env python3
"""s78 — smoke post-backfill por el HANDLER real (lección #40): verifica el VALOR del Backfill A.
Mockea solo has_consent(True) + _process_query (recorder) para aislar la decisión del gate."""
from __future__ import annotations
import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
import asyncio, sys, types
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
for f in ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "LEVER1_BROAD_FALLBACK", "LEVER1_KEYWORD_ORDER"):
    os.environ.pop(f, None)
sys.path.insert(0, str(ROOT))
import src.bot.telegram_bot as tb  # noqa: E402

_C = {"p": False}
class _Chat:
    async def send_action(self, *a, **k): pass
class _Msg:
    def __init__(s, t): s.text = t; s.replies = []; s.chat = _Chat()
    async def reply_text(s, t, **k): s.replies.append(t)
class _U:
    id = 999
class _Up:
    def __init__(s, t): s.message = _Msg(t); s.effective_user = _U()
async def _fake(update, context, query, *a, **k): _C["p"] = True

def classify(u):
    if _C["p"]: return "FALL_THROUGH"
    t = " ".join(u.message.replies)
    if "No tengo información sobre el modelo" in t: return "REFUSE_model_not_found"
    if "es un producto de" in t or " no de " in t: return "REFUSE_A_mismatch"
    if "No dispongo de manuales de" in t: return "REFUSE_manufacturer_absent"
    return f"OTHER: {t[:50]}"

CASES = [
    ("Notifier RP1r-Supra (FIX1: era mismatch-refuse)", "En la central Notifier RP1r-Supra, ¿cómo se resetea tras una descarga de extinción?", "FALL_THROUGH"),
    ("Morley VSN-RP1r (control, correcto)", "¿Cómo se programa un retardo en la central Morley VSN-RP1r?", "FALL_THROUGH"),
    ("Notifier FAAST LT-200 (FIX2 contexto)", "En el detector Notifier FAAST LT-200, ¿qué relés tiene?", "FALL_THROUGH"),
    ("Siemens ausente (no-regresión)", "¿Cómo configuro la central de incendios Siemens FC724?", "REFUSE_manufacturer_absent"),
]

def main():
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
    tb.has_consent = lambda uid: True
    tb._process_query = _fake
    ctx = types.SimpleNamespace(user_data={})
    print("=== s78 smoke post-backfill (handle_message real) ===")
    ok = 0
    for label, q, exp in CASES:
        _C["p"] = False
        u = _Up(q)
        asyncio.run(tb.handle_message(u, ctx))
        got = classify(u)
        m = "OK " if got == exp else "XX "
        ok += got == exp
        print(f"{m}{label:48} esperado={exp:26} got={got}")
        if got != exp and u.message.replies: print(f"      reply: {u.message.replies[0][:90]}")
    print(f"\n{ok}/{len(CASES)}")
    return 0 if ok == len(CASES) else 1

if __name__ == "__main__":
    sys.exit(main())
