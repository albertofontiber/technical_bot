#!/usr/bin/env python3
"""s333 — Gate de JUICIO del clasificador CORRECCION/NUEVO (v2 §5) sobre la
cohorte congelada, con la regla K PINNADA en el YAML (voto dañino falla
negativas; mayoría ≥2/3 pasa positivas; None cuenta NUEVO) + verificación de la
GUARDA Fable-1 contra `resolve()` entero.

Brazos: Sonnet (el pin de ship) SIEMPRE; `--haiku` añade el brazo INFORMATIVO
(v2 §3: sin herencia del «NO-GO» de otra métrica; si Sonnet PASS, shipa Sonnet).

Uso: python scripts/s333_correccion_gate.py [--haiku] [--out evals/s333_gate_result_v1.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import yaml  # noqa: E402

HAIKU_MODEL = "claude-haiku-4-5-20251001"


def _correr_brazo(modelo: str, cohorte: dict, api_key: str) -> dict:
    from src.orchestrator.correccion_llm import construir_correccion_fn

    fn = construir_correccion_fn(api_key, model=modelo)
    k = int(cohorte["k"])
    # La regla pinnada («mayoría >=2/3») está escrita para k=3; una cohorte
    # futura con otro k debe re-pinnarla, no heredar `>= 2` en silencio.
    assert k == 3, f"regla K pinnada para k=3; cohorte trae k={k}"
    lat: list[int] = []

    def _votos(caso) -> list[str]:
        out = []
        for _ in range(k):
            d = fn(caso["q"], caso["last_query"], caso["marca"])
            lat.append((fn.ultima or {}).get("ms", 0))
            out.append(d if d in ("correccion", "nuevo") else "nuevo")  # None⇒NUEVO
        return out

    filas, pos_pass, falsas = [], 0, 0
    for i, c in enumerate(cohorte["positivas"], 1):
        v = _votos(c)
        ok = sum(x == "correccion" for x in v) >= 2       # mayoría pinnada
        pos_pass += ok
        filas.append({"tipo": "positiva", "q": c["q"], "votos": v, "ok": ok})
        print(f"  [P{i:2d}] {'OK ' if ok else 'X  '} votos={v} {c['q'][:48]}")
    for i, c in enumerate(cohorte["negativas"], 1):
        v = _votos(c)
        falsa = any(x == "correccion" for x in v)          # voto dañino pinnado
        falsas += falsa
        filas.append({"tipo": "negativa", "q": c["q"], "votos": v,
                      "falsa_correccion": falsa})
        print(f"  [N{i:2d}] {'FC!' if falsa else 'OK '} votos={v} {c['q'][:48]}")

    lat.sort()
    p50 = lat[len(lat) // 2] if lat else 0
    p95 = lat[int(len(lat) * 0.95)] if lat else 0
    pasa = (falsas <= int(cohorte["umbral_falsas_correccion"])
            and pos_pass >= int(cohorte["umbral_positivas_pass"]))
    return {"modelo": modelo, "positivas_pass": pos_pass,
            "positivas_n": len(cohorte["positivas"]),
            "falsas_correccion": falsas,
            "negativas_n": len(cohorte["negativas"]),
            "latencia_ms": {"p50": p50, "p95": p95},
            "veredicto": "GO" if pasa else "NO-GO", "filas": filas,
            "config_atestada": fn.config}


def _guarda_model_token(cohorte: dict) -> list[dict]:
    """Las 2 negativas de clase Fable-1: corren contra resolve() ENTERO con una
    fn que EXPLOTA si el clasificador llega a invocarse."""
    from datetime import timedelta

    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.conversation_policy_impl import resolve_conversational_turn

    def _bomba(q, lq, m):  # noqa: ARG001
        raise AssertionError("la guarda model-token NO filtró — el LLM se invocó")

    now = datetime.now(timezone.utc)
    out = []
    for c in cohorte["guarda_model_token"]:
        ws = WorkingState(last_query=c["last_query"],
                          last_turn_at=now - timedelta(seconds=60))
        res, _ = resolve_conversational_turn(c["q"], ws, now, correccion=_bomba)
        ok = res.rationale == c["esperado_rationale"]
        out.append({"q": c["q"], "rationale": res.rationale, "ok": ok})
        print(f"  [G] {'OK ' if ok else 'X  '} {c['q'][:44]} → {res.rationale}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--haiku", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evals" / "s333_gate_result_v1.json"))
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        print("ANTHROPIC_API_KEY ausente"); return 2

    crudo = (ROOT / "evals" / "s333_correccion_cohort_v1.yaml").read_text(encoding="utf-8")
    cohorte = yaml.safe_load(crudo)
    from src.orchestrator.correccion_llm import CORRECCION_MODEL, PROMPT

    # El flag NO gobierna el gate (mide el módulo directamente); la guarda usa la
    # rama real, así que se enciende SOLO para ese bloque.
    print(f"== brazo Sonnet ({CORRECCION_MODEL})")
    brazos = [_correr_brazo(CORRECCION_MODEL, cohorte, api_key)]
    if args.haiku:
        print(f"== brazo Haiku INFORMATIVO ({HAIKU_MODEL})")
        brazos.append(_correr_brazo(HAIKU_MODEL, cohorte, api_key))

    print("== guarda model-token (resolve() entero, fn-bomba)")
    os.environ["F1_MARCA_CORRECCION"] = "on"
    os.environ["F1_CORRECCION_LLM"] = "on"
    guarda = _guarda_model_token(cohorte)
    for k in ("F1_MARCA_CORRECCION", "F1_CORRECCION_LLM"):
        os.environ.pop(k, None)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    recibo = {
        "gate": "s333 correccion cohort v1",
        "freeze": {"cohorte_sha256": hashlib.sha256(crudo.encode()).hexdigest()[:16],
                   "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest()[:16],
                   "commit": commit,
                   "regla_k": "negativa falla con CUALQUIER voto CORRECCION; "
                              "positiva pasa con mayoria >=2/3; None=NUEVO"},
        "umbrales_preregistrados": {
            "falsas_correccion": cohorte["umbral_falsas_correccion"],
            "positivas_pass": cohorte["umbral_positivas_pass"]},
        "brazos": brazos, "guarda_model_token": guarda,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    Path(args.out).write_text(json.dumps(recibo, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    sonnet = brazos[0]
    guarda_ok = all(g["ok"] for g in guarda)
    print(f"\nSonnet: {sonnet['veredicto']} (positivas {sonnet['positivas_pass']}/"
          f"{sonnet['positivas_n']}, falsas {sonnet['falsas_correccion']}) · "
          f"guarda: {'OK' if guarda_ok else 'FALLO'} · recibo → {args.out}")
    return 0 if sonnet["veredicto"] == "GO" and guarda_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
