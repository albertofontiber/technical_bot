# -*- coding: utf-8 -*-
"""s336 B5 — WRITER atómico + EFECTO (v3 §1.6 + §0.2-0.3).

Precondición DURA: el gate de método en PASS (lee su recibo; sin PASS no hay
escritura — anti-gate-shopping). Escribe SOLO los elegibles (alta + cita
full-text atribuida) vía `swap_products_validado` (shadow completo → backup →
os.replace). `clasificacion.doc` SIEMPRE (Sol2-2); capacidad solo la completa
y no divergente (Sol2-1). Filas ya clasificadas JAMÁS se tocan.

Efecto (G6): before/after de la vista Notifier (clasificados/ciegos) + replay
del filtro de centrales con el SUELO pre-registrado en el censo (=11) +
veredicto del LOTE: PASS si escritos ≥60% de la diana (502), si no PARCIAL —
declarado, jamás éxito vacío (Sol-4).

Uso: python scripts/s336_writer.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROV = ("s336 método s322b (pasada fable-5 + repesca dirigida + full-text + "
        "completitud de capacidad); gate evals/s336_gate_result_v1.json; "
        "GT c8bb02620b4ade74; censo 37cc4aa409ab484f")


def _conteos(cat) -> dict:
    from src.bot.telegram_bot import _productos_marca
    props = _productos_marca(cat, "notifier")
    clas = [p for p in props if p.get("clasificacion")]
    centrales = [p for p in clas
                 if p["clasificacion"].get("categoria") == "central"]
    return {"propios": len(props), "clasificados": len(clas),
            "ciegos": len(props) - len(clas), "centrales": len(centrales)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gate = json.loads((ROOT / "evals" / "s336_gate_result_v1.json")
                      .read_text(encoding="utf-8"))
    if not gate["gate"]["pass"]:
        print("el gate de método NO está en PASS — sin escritura"); return 2
    ele = json.loads((ROOT / "evals" / "s336_elegibles_v1.json")
                     .read_text(encoding="utf-8"))
    censo = json.loads((ROOT / "evals" / "s336_censo_diana_v1.json")
                       .read_text(encoding="utf-8"))
    suelo = censo["suelo_gate_efecto"]["valor"]
    diana_n = censo["total"]

    from src.rag import catalog_store as cs

    antes = _conteos(cs.load())
    filas = [json.loads(l) for l in
             (cs.CATALOG_DIR / cs.FILES["products"])
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    por_id = {r["id"]: r for r in filas}

    escritas, saltadas = [], []
    for e in ele["detalle"]:
        if not e.get("elegible"):
            continue
        fila = por_id.get(e["id"])
        if fila is None or fila.get("clasificacion"):
            saltadas.append({"id": e["id"], "motivo": "ausente o ya clasificada"})
            continue
        fila["clasificacion"] = {"categoria": e["categoria"],
                                 "cita": str(e["categoria_cita"])[:200],
                                 "doc": e["doc_cat"], "provenance": PROV}
        if e.get("atributos") and not fila.get("atributos"):
            fila["atributos"] = e["atributos"]
        escritas.append(e["id"])

    if args.dry_run:
        print(f"DRY-RUN: escribiría {len(escritas)} · saltadas {len(saltadas)}")
        return 0
    backup = cs.swap_products_validado(filas)
    despues = _conteos(cs.load())

    # replay del filtro con el catálogo NUEVO (suelo pre-registrado)
    from src.bot import telegram_bot as tb
    from src.rag import catalog_resolver
    cat_nuevo = cs.load()
    catalog_resolver.catalogo_cargado = lambda: cat_nuevo  # proceso efímero
    out_filtro = tb._inventario_filtrado("notifier", {"categoria": "central"})
    centrales_servidas = (out_filtro or "").count("\n• ") + (out_filtro or "").count("• ", 0, 2)
    suelo_ok = centrales_servidas >= suelo

    cobertura = len(escritas) / diana_n
    veredicto = "PASS" if cobertura >= 0.60 else "PARCIAL"
    recibo = {
        "que_es": "s336 escritura atómica + efecto (G6)",
        "escritas": len(escritas), "saltadas": saltadas,
        "backup": str(backup),
        "antes": antes, "despues": despues,
        "replay_filtro_centrales": {
            "servidas": centrales_servidas, "suelo_preregistrado": suelo,
            "suelo_ok": suelo_ok,
            "extracto": (out_filtro or "")[:600]},
        "cobertura": {"escritas": len(escritas), "diana": diana_n,
                      "ratio": round(cobertura, 3), "umbral_pass": 0.60},
        "veredicto_lote": veredicto,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = ROOT / "evals" / "s336_escritura_result_v1.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"escritas {len(escritas)} · antes {antes} → después {despues} · "
          f"centrales servidas {centrales_servidas} (suelo {suelo}: "
          f"{'OK' if suelo_ok else 'FALLO'}) · cobertura {cobertura:.1%} → "
          f"VEREDICTO {veredicto} · backup {backup}\nrecibo → {out}")
    return 0 if suelo_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
