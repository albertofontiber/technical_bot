# -*- coding: utf-8 -*-
"""s323 — Pasada de COHERENCIA nombre-de-fichero <-> cita <-> ids asignados.

Nace del caso que Alberto adjudico: `ds_kidde_2x_at_fr_s_202602_es_904a` venia entre
las 38 LIMPIAS con cita «Modelo: Central Kidde NC-PF» y los 6 ids de las NC-PF — pero
el fichero es la ficha del repetidor 2X-AT-FR-S. La cita existia en el corpus... en
OTRO documento, y arrastro consigo la asignacion.

El criterio automatico no puede cazar eso (veredicto alto + cita verificada), pero una
comprobacion mecanica si: si el NOMBRE del fichero contiene un modelo del catalogo y
ese modelo NO esta entre los ids asignados, hay discrepancia. No decide nada: señala.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl


def nk(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


products = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
# modelos ordenados de mas largo a mas corto: gana el match mas especifico
modelos = sorted(((nk(r.get("canonical_model") or ""), pid)
                  for pid, r in products.items()
                  if r.get("estado") == "activo" and len(nk(r.get("canonical_model") or "")) >= 5),
                 key=lambda x: -len(x[0]))

v3 = json.loads((ROOT / "evals" / "s323_tierb_v3_serie_x_categoria.json").read_text(encoding="utf-8"))
discrepancias, ok = [], 0
for f in v3["limpias"]:
    nombre = nk(f["documento"])
    ids = f.get("ids_por_serie_x_categoria") or f["ids_originales"]
    ids_nk = {nk(products[i]["canonical_model"]) for i in ids if i in products}
    # que modelos del catalogo aparecen en el NOMBRE del fichero
    en_nombre, usados = [], ""
    for m, pid in modelos:
        if m in nombre and m not in usados:
            en_nombre.append((m, pid))
            usados += m
    if not en_nombre:
        ok += 1
        continue
    coincide = any(m in ids_nk for m, _ in en_nombre)
    if coincide:
        ok += 1
    else:
        discrepancias.append({
            "documento": f["documento"],
            "modelo_en_el_NOMBRE": [{"modelo": products[p]["canonical_model"], "id": p}
                                    for _, p in en_nombre[:3]],
            "ids_ASIGNADOS": ids,
            "cita": f["cita"][:110]})

salida = {"que_es": __doc__.strip().splitlines()[0],
          "analizadas": len(v3["limpias"]), "coherentes": ok,
          "discrepancias": discrepancias}
(ROOT / "evals" / "s323_coherencia_nombre_cita_v1.json").write_text(
    json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"analizadas {len(v3['limpias'])} · coherentes {ok} · DISCREPANCIAS {len(discrepancias)}")
for d in discrepancias:
    print(f"\n  {d['documento'][:56]}")
    print(f"     nombre sugiere: {', '.join(m['modelo'] for m in d['modelo_en_el_NOMBRE'])}")
    print(f"     asignado:       {', '.join(d['ids_ASIGNADOS'][:4])}")
    print(f"     cita: «{d['cita'][:80]}»")
