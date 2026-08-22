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
sys.path.insert(0, str(ROOT / "scripts"))

import lib_lote_marca as L  # noqa: E402

# La provenance NO se escribe a mano: la constante de s336 llevaba incrustados
# los sha del GT y del censo de NOTIFIER, y habría viajado intacta a las filas
# de cualquier otra marca — prometiendo que las juzgó un gold que no las vio.
# `L.provenance` la deriva de los artefactos que de verdad juzgaron la corrida.


def _conteos(cat, marca: str, categoria: str) -> dict:
    props = list(L.vista_de(cat, marca).values())
    clas = [p for p in props if p.get("clasificacion")]
    foco = [p for p in clas
            if p["clasificacion"].get("categoria") == categoria]
    return {"propios": len(props), "clasificados": len(clas),
            "ciegos": len(props) - len(clas), categoria: len(foco)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--marca", default="notifier")
    ap.add_argument("--replay-categoria", default="central",
                    help="categoría con la que se mide el efecto servido")
    args = ap.parse_args()
    marca = L.normaliza_marca(args.marca)
    categoria = args.replay_categoria

    gate_path = L.ruta("gate", marca)
    gate = L.carga_recibo(gate_path)
    if not gate["gate"]["pass"]:
        print("el gate de método NO está en PASS — sin escritura"); return 2
    ele = L.carga_recibo(L.ruta("elegibles", marca))
    censo_path = L.ruta("censo", marca)
    censo = L.carga_recibo(censo_path)
    suelo = censo["suelo_gate_efecto"]["valor"]
    diana_n = censo["total"]

    from src.rag import catalog_store as cs

    cat_antes = cs.load()
    elegibles_ids = [e["id"] for e in ele["detalle"] if e.get("elegible")]
    intrusos = L.candado_de_vista(elegibles_ids, cat_antes, marca)
    if intrusos:
        # Recibos cruzados entre marcas: escribir aquí sería juzgar filas de una
        # marca con el gold y el gate de otra. Se aborta ANTES de tocar nada.
        print(f"CANDADO: {len(intrusos)} elegible(s) NO pertenecen a la vista de "
              f"«{marca}» — recibos cruzados. Nada escrito. Ej: {intrusos[:5]}")
        return 4

    antes = _conteos(cat_antes, marca, categoria)
    filas = [json.loads(l) for l in
             (cs.CATALOG_DIR / cs.FILES["products"])
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    por_id = {r["id"]: r for r in filas}

    prov = L.provenance(marca, gate_path, L.ruta("gt", marca, "yaml"), censo_path)
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
                                 "doc": e["doc_cat"], "provenance": prov}
        if e.get("atributos") and not fila.get("atributos"):
            fila["atributos"] = e["atributos"]
        escritas.append(e["id"])

    if args.dry_run:
        print(f"DRY-RUN: escribiría {len(escritas)} · saltadas {len(saltadas)}")
        return 0
    backup = cs.swap_products_validado(filas)
    despues = _conteos(cs.load(), marca, categoria)

    # replay del filtro con el catálogo NUEVO (suelo pre-registrado)
    from src.bot import telegram_bot as tb
    from src.rag import catalog_resolver
    cat_nuevo = cs.load()
    catalog_resolver.catalogo_cargado = lambda: cat_nuevo  # proceso efímero
    out_filtro = tb._inventario_filtrado(marca, {"categoria": categoria})
    centrales_servidas = (out_filtro or "").count("\n• ") + (out_filtro or "").count("• ", 0, 2)
    # El conteo de arriba parsea el RENDER (lo que de verdad ve el técnico) y
    # por eso se conserva; pero acoplarse al formato de la UI es frágil, así que
    # se contrasta con el conteo sobre el catálogo. Divergencia = instrumento roto.
    en_catalogo = sum(1 for p in L.vista_de(cat_nuevo, marca).values()
                      if (p.get("clasificacion") or {}).get("categoria") == categoria)
    suelo_ok = centrales_servidas >= suelo

    # Cobertura ACUMULADA del lote, no de esta corrida: el writer es
    # incremental, así que `len(escritas)` mide el último empujón (la
    # recuperación del 22-ago dio 50/502 = «PARCIAL» con el lote real ya en
    # 411/502 = PASS). El veredicto debe leer el catálogo, no el delta.
    del_lote = [p for p in L.vista_de(cs.load(), marca).values()
                if "s336" in ((p.get("clasificacion") or {}).get("provenance") or "")]
    cobertura = len(del_lote) / diana_n
    veredicto = "PASS" if cobertura >= 0.60 else "PARCIAL"
    recibo = {
        "que_es": "escritura atómica + efecto (G6)",
        "marca": marca, "replay_categoria": categoria, "provenance": prov,
        "escritas": len(escritas), "saltadas": saltadas,
        "backup": str(backup),
        "antes": antes, "despues": despues,
        "replay_filtro": {
            "servidas": centrales_servidas, "en_catalogo": en_catalogo,
            "instrumento_coherente": centrales_servidas == en_catalogo,
            "suelo_preregistrado": suelo,
            "suelo_ok": suelo_ok,
            "extracto": (out_filtro or "")[:600]},
        "cobertura": {"escritas_esta_corrida": len(escritas),
                      "acumulado_del_lote": len(del_lote), "diana": diana_n,
                      "ratio": round(cobertura, 3), "umbral_pass": 0.60,
                      "nota": "el ratio es ACUMULADO (catálogo), no el delta"},
        "veredicto_lote": veredicto,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = L.ruta_no_destructiva(L.ruta("escritura", marca))
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[{marca}] escritas {len(escritas)} · antes {antes} → después {despues} · "
          f"{categoria} servidas {centrales_servidas} (suelo {suelo}: "
          f"{'OK' if suelo_ok else 'FALLO'}) · cobertura {cobertura:.1%} → "
          f"VEREDICTO {veredicto} · backup {backup}\nrecibo → {out}")
    return 0 if suelo_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
