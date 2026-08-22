# -*- coding: utf-8 -*-
"""Censo de la RE-DIANA que abre el enum ampliado (s339, hallazgo crítico del dúo).

El error que este script existe para no cometer: al ampliar el enum se pensó en
re-correr «lo que quedó ciego», es decir las filas de confianza NO alta. Pero el
daño mayor está en las filas ALTA: bajo un enum de 13 valores, una central de
extinción tenía una respuesta plausible Y CONFIADA (`central`), y un amplificador
de audio otra (`modulo`). No dudaban por falta de evidencia — acertaban DENTRO de
un enum incompleto. Esas filas ya están escritas y servidas.

La re-diana es, por tanto: (no-alta) ∪ (alta cuya evidencia toca una clase nueva).
El segundo conjunto se detecta por REGEX sobre el canónico y la cita ESCRITA —
declarado como cribado grueso, no como juicio: quien decide sigue siendo la
re-pasada con el prompt v3, y luego el gate.

Solo lectura. Uso: python scripts/s339_rediana.py [--marca notifier]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lib_lote_marca as L  # noqa: E402
from src.rag.catalog_store import load  # noqa: E402

# Cribado GRUESO por clase nueva. Se busca sobre canónico + cita escrita; que un
# término aparezca NO significa que la fila cambie de categoría (un «detector de
# gas» casa con extinción y sigue siendo detector; un detector con protección IS
# casa con `intrínseca` y sigue siendo detector). Solo decide a quién se RE-PREGUNTA.
SONDAS = {
    "extincion": r"extinci|extinguish|agente\s+extintor|FM-?200|inergen",
    "audio": r"\bEVAC\b|megafon|altavoz|speaker|voice\s+alarm|VACIE|audio|amplificador",
    "barrera_is": r"zener|intr[íi]nsec|intrinsic",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default="notifier")
    args = ap.parse_args()
    marca = L.normaliza_marca(args.marca)

    pob = L.carga_recibo(L.ruta("poblacion", marca))["detalle"]
    no_alta = [f["id"] for f in pob if f["llm"].get("confianza") != "alta"]

    cat = load()
    vista = L.vista_de(cat, marca)
    sospechosas, por_sonda = [], {}
    for pid, prod in vista.items():
        clas = prod.get("clasificacion") or {}
        if "s336" not in (clas.get("provenance") or ""):
            continue                      # sólo lo que escribió ESTE lote
        blob = f"{prod.get('canonical_model', '')} {clas.get('cita', '')}"
        for clase, rx in SONDAS.items():
            if re.search(rx, blob, re.I):
                sospechosas.append(pid)
                por_sonda.setdefault(clase, []).append(
                    {"id": pid, "categoria_actual": clas.get("categoria"),
                     "cita": (clas.get("cita") or "")[:120]})
                break

    rediana = sorted(set(no_alta) | set(sospechosas))
    out = {
        "que_es": ("re-diana del enum ampliado: (no-alta) ∪ (alta cuya evidencia "
                   "toca una clase nueva). El cribado por regex NO juzga: decide "
                   "a quién se re-pregunta con el prompt v3."),
        "marca": marca,
        "sondas": SONDAS,
        "n_no_alta": len(no_alta),
        "n_alta_sospechosas": len(set(sospechosas)),
        "n_rediana": len(rediana),
        "alta_sospechosas_por_sonda": por_sonda,
        "ids": rediana,
    }
    destino = ROOT / "evals" / (f"s339_rediana_{marca}_v1.json" if marca != "notifier"
                                else "s339_rediana_v1.json")
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{marca}] no-alta {len(no_alta)} + alta-sospechosas "
          f"{len(set(sospechosas))} → re-diana {len(rediana)}")
    for clase, filas in sorted(por_sonda.items()):
        cats = {}
        for f in filas:
            cats[f["categoria_actual"]] = cats.get(f["categoria_actual"], 0) + 1
        print(f"  {clase}: {len(filas)} escritas hoy como {cats}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
