#!/usr/bin/env python3
"""probe_gpt55_determinism.py — micro-test empírico de determinismo de gpt-5.5 (TECH_DEBT #37, DEC-014 paso 1).

Resuelve H2 SIN inferir: ¿gpt-5.5 acepta `temperature=0` o la rechaza? ¿`seed` da reproducibilidad?
¿cuánto varía run-a-run SIN control (= el estado ACTUAL del eje factual del árbitro)?

Reutiliza el prompt REAL del eje factual (`atomic_scorer._FACTUAL_SYS/_USER`) sobre un caso BORDERLINE
(el bot da un rango de temperatura subconjunto del verificado) — justo donde el conteo de contradicciones
wobblea 0↔1, que es el único cruce que cambia el VEREDICTO (`atomic_scorer.py:323`).

Uso: python scripts/probe_gpt55_determinism.py [--model gpt-5.5] [--n 4]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402
from atomic_scorer import _FACTUAL_SYS, _FACTUAL_USER  # noqa: E402  (prompt REAL del eje)

# Caso BORDERLINE: el bot afirma un rango de temperatura DISTINTO (subconjunto) al verificado.
# ¿contradicción (valor distinto) o no (subset / bot conservador)? El prompt dice "ante la duda NO
# marques" -> el modelo wobblea aquí entre 0 y 1 contradicciones. Tensión 24V coincide (no-conflicto).
FACTS = (
    "- El rango de temperatura de funcionamiento es -30 a +60 °C [valor: -30/+60]\n"
    "- La tensión nominal de alimentación es 24 V [valor: 24 V]"
)
ANSWER = (
    "El equipo se alimenta a 24 V. Según el manual, opera en un rango de temperatura de "
    "-20 a +55 °C, adecuado para instalaciones de interior."
)
MESSAGES = [
    {"role": "system", "content": _FACTUAL_SYS},
    {"role": "user", "content": _FACTUAL_USER.format(facts=FACTS, answer=ANSWER)},
]


def _call(client, model, **kw):
    """(ok, texto|err, fingerprint)."""
    try:
        resp = client.chat.completions.create(model=model, messages=MESSAGES, **kw)
        return True, resp.choices[0].message.content.strip(), getattr(resp, "system_fingerprint", None)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


def _n_contra(txt):
    """conteo de contradicciones del JSON (None si no parsea = otra fuente de inestabilidad)."""
    t = txt
    if t.startswith("```"):
        t = t.split("```")[1].lstrip("json").strip()
    try:
        return len(json.loads(t).get("contradicciones", []))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--n", type=int, default=4, help="repeticiones del Test 3 (baseline sin control)")
    ap.add_argument("--rf", action="store_true", help="SOLO el test de response_format (paso 2 DEC-014)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    load_dotenv(ROOT / ".env", override=True)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("[ERROR] sin OPENAI_API_KEY (en .env o env). Abortado.")
        return 1
    client = OpenAI(api_key=key)
    m = args.model

    # Paso 2 (DEC-014): ¿gpt-5.5 acepta response_format? (testear antes de cablear las 3 llamadas)
    if args.rf:
        print(f"== response_format en {m} (json_object) ==")
        ok, out, fp = _call(client, m, response_format={"type": "json_object"})
        valid = _n_contra(out) is not None if ok else False
        print(f"  json_object: {'ACEPTADO' if ok else 'RECHAZADO'} → "
              + (f"JSON_válido={valid} · n_contra={_n_contra(out)}" if ok else out))
        return 0

    rec: dict = {"model": m, "case": "borderline rango -20/+55 vs -30/+60", "tests": {}}
    print(f"Probe determinismo · modelo={m} · caso borderline (conteo wobblea 0↔1)\n")

    # --- Test 1: ¿temperature=0 aceptada por gpt-5.5? (resuelve la alt A) ---
    print("== Test 1: temperature=0 ==")
    ok, out, fp = _call(client, m, temperature=0)
    rec["tests"]["temp0"] = {"accepted": ok, "fingerprint": fp,
                             "n_contra": _n_contra(out) if ok else None, "raw": out}
    print(f"  {'ACEPTADA' if ok else 'RECHAZADA'} → "
          + (f"fp={fp} · n_contra={_n_contra(out)}" if ok else out))

    # --- Test 2: ¿seed da determinismo? (2 calls, seed fijo, input idéntico) ---
    print("\n== Test 2: seed=42 (x2, input idéntico) ==")
    ok1, o1, f1 = _call(client, m, seed=42)
    if not ok1:
        rec["tests"]["seed"] = {"accepted": False, "error": o1}
        print(f"  RECHAZADO → {o1}")
    else:
        ok2, o2, f2 = _call(client, m, seed=42)
        identical = ok2 and o1 == o2
        rec["tests"]["seed"] = {"accepted": True, "identical": identical,
                                "fingerprints": [f1, f2],
                                "n_contra": [_n_contra(o1), _n_contra(o2) if ok2 else None],
                                "raw": [o1, o2]}
        print(f"  fingerprints: {f1} / {f2}")
        print(f"  outputs idénticos: {identical} · n_contra: {_n_contra(o1)} / {_n_contra(o2) if ok2 else 'ERR'}"
              + ("" if identical else "  → seed NO determina"))

    # --- Test 3: SIN params = comportamiento ACTUAL del eje factual (¿existe el ruido?) ---
    print(f"\n== Test 3: SIN params (x{args.n}) = estado actual del árbitro ==")
    runs = []
    for i in range(args.n):
        ok, out, fp = _call(client, m)
        nc = _n_contra(out) if ok else "ERR"
        runs.append({"ok": ok, "n_contra": _n_contra(out) if ok else None, "fp": fp, "raw": out})
        print(f"  run {i + 1}: n_contra={nc} · fp={fp}")
    ncs = [r["n_contra"] for r in runs if r["ok"] and r["n_contra"] is not None]
    distinct_txt = len({r["raw"] for r in runs if r["ok"]})
    crosses_01 = bool(ncs) and (0 in ncs) and any(n >= 1 for n in ncs)
    rec["tests"]["baseline"] = {"n": args.n, "n_contra": ncs, "distinct_outputs": distinct_txt,
                                "verdict_unstable_0to1": crosses_01, "runs": runs}
    print(f"  → outputs distintos: {distinct_txt}/{args.n} · conteos: {ncs}")
    print(f"  → VEREDICTO {'INESTABLE (cruza 0↔1)' if crosses_01 else 'estable en este caso'} "
          f"· conteo-distinto: {len(set(ncs)) > 1 if ncs else 'n/a'}")

    rec["ts"] = datetime.now().isoformat(timespec="seconds")
    out_path = ROOT / "evals" / "probe_gpt55_determinism.json"
    out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[artefacto] raw → {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
