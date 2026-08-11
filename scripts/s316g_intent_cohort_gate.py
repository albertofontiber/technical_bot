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

# EL prompt es EL DEL MÓDULO SERVIDO (una sola fuente — el prompt que se midió es el
# que sirve; duplicarlo aquí sería el drift exacto que el dúo lleva cazando toda la
# sesión). parse_decision también se importa: el parser medido es el servido.
from src.orchestrator.intent_llm import PROMPT, parse_decision  # noqa: E402

def _clasificar(fn, q: str, contexto: str) -> tuple[str | None, int]:
    """PARIDAD TOTAL con lo servido (Fable r11): el callable ES construir_intent_fn —
    mismo cliente (timeout 6 s, max_retries=0), mismo prompt, mismo parser. El gate
    mide la config que sirve, no una gemela."""
    from types import SimpleNamespace

    ws = SimpleNamespace(last_target_models=(), _contexto=contexto)
    t0 = time.perf_counter()
    d = fn(q, ws)
    ms = fn.ultima["ms"] if getattr(fn, "ultima", None) else \
        int((time.perf_counter() - t0) * 1000)
    return ({"compat": "COMPAT", "switch": "SWITCH"}.get(d)), ms


def main() -> int:
    ruta_cohorte = ROOT / "evals" / "s316g_intent_cohort_v1.yaml"
    crudo = ruta_cohorte.read_text(encoding="utf-8")
    cohorte = yaml.safe_load(crudo)
    casos, k = cohorte["casos"], int(cohorte["k"])
    version = str(cohorte.get("version", "1"))
    from src.orchestrator.intent_llm import PROMPT as _P, construir_intent_fn

    fn = construir_intent_fn(ANTHROPIC_API_KEY, model=MODEL)
    # el contexto del caso sustituye al derivado del estado (los casos ya traen
    # "MODELO (Marca)" congelado): se parchea contexto_del_estado por el literal
    import src.orchestrator.intent_llm as _il
    _ctx_orig = _il.contexto_del_estado
    _il.contexto_del_estado = lambda ws: getattr(ws, "_contexto", "desconocido")

    filas, aciertos, falsos_switch, indecisos = [], 0, 0, 0
    lat = []
    for i, c in enumerate(casos, 1):
        votos = []
        for _ in range(k):
            v, ms = _clasificar(fn, c["q"], c["contexto"])
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

    import hashlib as _hl
    import subprocess as _sp
    try:
        commit = _sp.check_output(["git", "rev-parse", "--short", "HEAD"],
                                  cwd=str(ROOT), text=True).strip()
    except Exception:                            # noqa: BLE001
        commit = "desconocido"
    recibo = {
        "gate": f"s316g intent cohort v{version}", "modelo": MODEL, "k": k,
        "freeze": {"cohorte_sha256": _hl.sha256(crudo.encode("utf-8")).hexdigest()[:16],
                   "prompt_sha256": _hl.sha256(_P.encode("utf-8")).hexdigest()[:16],
                   "commit": commit,
                   "paridad": "construir_intent_fn servido (timeout 6s, max_retries=0)"},
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
    sufijo = f"v{version.replace('.', '_')}_{MODEL.split('-')[1]}"
    out = ROOT / "evals" / f"s316g_intent_cohort_result_{sufijo}.json"
    _il.contexto_del_estado = _ctx_orig
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"recibo → {out}")
    return 0 if pasa else 1


if __name__ == "__main__":
    raise SystemExit(main())
