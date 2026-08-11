#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s316g — Gate de JUICIO del lever INTENT_LLM (v2 §1): la cohorte congelada vs Haiku REAL.

Pregunta cero del lever: ¿sabe Haiku distinguir compatibilidad de cambio-de-tema en
esta rama? Si NO, el lever es NO-GO y nada se cablea. Umbral PREDECLARADO en la
cohorte (asimétrico: falsos SWITCH en COMPAT = 0/K — la clase que borra contexto
legítimo; accuracy global >= 0.90). K repeticiones por caso (estabilidad).

El PROMPT de aquí es EL del lever (v2 §4: pregunta + producto en curso con marca
resuelta; sin last_query — minimización). ANTI-GATE-SHOPPING: no se re-tunea contra
la cohorte; revisarlo = cohorte nueva congelada (patrón DEC-126).

Uso:  python scripts/s316g_intent_cohort_gate.py            # corre y estampa recibo
Coste: ~40 casos x K=3 x ~$0.0002 ~= $0.03.
"""
from __future__ import annotations

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

import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.config import ANTHROPIC_API_KEY  # noqa: E402

import os as _os

MODEL = _os.environ.get("INTENT_GATE_MODEL", "claude-haiku-4-5-20251001")

# EL prompt del lever (v2 §4). Decisión única, un token, contexto mínimo.
PROMPT = """Eres el enrutador de un asistente técnico de sistemas contra incendios.
El técnico estaba consultando sobre este producto: {contexto}.
Su siguiente mensaje es: «{q}»

¿El mensaje pregunta por la COMPATIBILIDAD/integración de otra marca CON el producto en
curso (la consulta sigue siendo sobre ese producto), o CAMBIA DE TEMA a la otra marca
(el producto en curso deja de ser el sujeto)?

Responde EXACTAMENTE una palabra: COMPAT o SWITCH."""


def _clasificar(cl, q: str, contexto: str) -> tuple[str | None, int]:
    """El callable del lever, tal cual irá a producción: parser estricto, todo lo
    demás → None (fail-open)."""
    t0 = time.perf_counter()
    try:
        msg = cl.messages.create(
            model=MODEL, max_tokens=4, temperature=0,
            messages=[{"role": "user",
                       "content": PROMPT.format(q=q, contexto=contexto)}])
        raw = "".join(b.text for b in msg.content
                      if getattr(b, "type", "") == "text")
        ms = int((time.perf_counter() - t0) * 1000)
        token = raw.strip().rstrip(".!").upper()
        return (token if token in ("COMPAT", "SWITCH") else None), ms
    except Exception:                            # noqa: BLE001 — fail-open como el lever
        return None, int((time.perf_counter() - t0) * 1000)


def main() -> int:
    import anthropic

    cohorte = yaml.safe_load(
        (ROOT / "evals" / "s316g_intent_cohort_v1.yaml").read_text(encoding="utf-8"))
    casos, k = cohorte["casos"], int(cohorte["k"])
    cl = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    filas, aciertos, falsos_switch, indecisos = [], 0, 0, 0
    lat = []
    for i, c in enumerate(casos, 1):
        votos = []
        for _ in range(k):
            v, ms = _clasificar(cl, c["q"], c["contexto"])
            votos.append(v)
            lat.append(ms)
        ok = all(v == c["esperado"] for v in votos)   # estabilidad: K/K, no mayoría
        aciertos += ok
        fs = c["esperado"] == "COMPAT" and any(v == "SWITCH" for v in votos)
        falsos_switch += fs
        indecisos += sum(1 for v in votos if v is None)
        filas.append({"q": c["q"], "esperado": c["esperado"], "votos": votos,
                      "ok": ok, "falso_switch": fs})
        marca = "OK " if ok else ("FS!" if fs else "X  ")
        print(f"  [{i:2d}/{len(casos)}] {marca} {c['esperado']:6s} votos={votos} {c['q'][:52]}")

    acc = aciertos / len(casos)
    lat.sort()
    p50, p95 = lat[len(lat) // 2], lat[int(len(lat) * 0.95)]
    pasa = (falsos_switch <= cohorte["umbral_falsos_switch_en_compat"]
            and acc >= cohorte["umbral_accuracy"])
    print(f"\naccuracy K/K: {aciertos}/{len(casos)} = {acc:.1%} "
          f"(umbral {cohorte['umbral_accuracy']:.0%})")
    print(f"falsos SWITCH en COMPAT: {falsos_switch} (umbral "
          f"{cohorte['umbral_falsos_switch_en_compat']}) · indecisos: {indecisos}")
    print(f"latencia por llamada: p50 {p50} ms · p95 {p95} ms")
    print(f"\nVEREDICTO DEL GATE: {'GO' if pasa else 'NO-GO'}")

    recibo = {
        "gate": "s316g intent cohort v1", "modelo": MODEL, "k": k,
        "accuracy": round(acc, 4), "aciertos": aciertos, "casos": len(casos),
        "falsos_switch_en_compat": falsos_switch, "indecisos": indecisos,
        "latencia_ms": {"p50": p50, "p95": p95},
        "veredicto": "GO" if pasa else "NO-GO",
        "umbrales_preregistrados": {
            "accuracy": cohorte["umbral_accuracy"],
            "falsos_switch_en_compat": cohorte["umbral_falsos_switch_en_compat"]},
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filas": filas,
    }
    sufijo = "v1" if "haiku" in MODEL else f"v1_{MODEL.split('-')[1]}"
    out = ROOT / "evals" / f"s316g_intent_cohort_result_{sufijo}.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"recibo → {out}")
    return 0 if pasa else 1


if __name__ == "__main__":
    raise SystemExit(main())
