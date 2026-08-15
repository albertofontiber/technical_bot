# -*- coding: utf-8 -*-
"""s323 fase C — CLI del gate de identidad corpus↔catálogo.

La LÓGICA vive en `src/rag/identidad_gate.py` porque es de producción: la ingesta
la ejecuta en cada corrida. El contrato de imports del repo
(`tests/test_import_contract.py`) prohíbe que `src/` importe de `scripts/` — y
tenía razón: el primer cableado de la fase C lo violaba y el test lo cazó.

Uso:
    python scripts/gate_identidad_corpus.py            # verifica (exit != 0 si hay NUEVAS)
    python scripts/gate_identidad_corpus.py --sellar   # regenera el manifiesto (DELIBERADO)
    python scripts/gate_identidad_corpus.py --json     # salida para máquinas
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.rag.identidad_gate import MANIFIESTO, evaluar, sellar  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sellar", action="store_true",
                    help="regenera el manifiesto de excepciones (acto DELIBERADO)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.sellar:
        n = sellar()
        print(f"manifiesto sellado con {n} excepciones preexistentes -> {MANIFIESTO}")
        return 0

    v = evaluar()
    if args.json:
        print(json.dumps({"violaciones": v["por_invariante"], "nuevas": v["nuevas"]},
                         ensure_ascii=False))
        return 1 if v["detalle_nuevas"] else 0

    print("GATE de identidad corpus<->catalogo")
    for inv, n in v["por_invariante"].items():
        n_nuevas = sum(1 for f in v["detalle_nuevas"] if f["invariante"] == inv)
        print(f"  {inv:<28} {n:>4} total - {n_nuevas:>3} NUEVAS")
    if v["detalle_nuevas"]:
        print("")
        print("VIOLACIONES NUEVAS (no estan en el manifiesto):")
        for f in v["detalle_nuevas"][:20]:
            print(f"   {json.dumps(f, ensure_ascii=False)[:120]}")
    if v.get("manifiesto_stale"):
        print("")
        print(f"aviso: {len(v['excepciones_resueltas'])} excepciones del manifiesto "
              f"YA NO aplican - re-sella con --sellar")
    return 1 if v["detalle_nuevas"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
