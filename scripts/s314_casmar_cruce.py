# -*- coding: utf-8 -*-
"""Cruce Casmar-Kidde vs corpus: qué tipos de doc ofrece Casmar que no tenemos.

Unidad de cruce = (SKU, tipo). Los docs de familia (p.ej. MI_KIDDE_NC_PFx) se
deduplican por URL y cuentan para todos los SKUs bajo los que aparecen.
Excluidos por regla de Alberto: certificados/homologaciones (H_DOP_/H_CPR_/C_*).
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\dev\technical_bot")
from dotenv import load_dotenv
load_dotenv(r"C:\dev\technical_bot\.env")
import httpx

SCRATCH = os.environ.get("S314_WORKDIR", os.getcwd())  # artefactos del harvest (JSONs/staging)
h = json.loads(io.open(os.path.join(SCRATCH, "casmar_kidde_harvest.json"), encoding="utf-8").read())

# ---- clasificacion por prefijo/nombre de fichero ----
def clasificar(nombre):
    low = nombre.lower()
    # homologaciones / certificados / declaraciones (regla de Alberto: fuera)
    if low.startswith(("h_dop", "h_cpr", "h_ce", "ce_", "c_", "dop_")) or "incert" in low:
        return "EXCLUIDO-homologacion"
    if low.startswith("mi_"):
        return "manual-instalacion"
    if low.startswith(("mu_", "m_uso")):
        return "manual-usuario"
    if low.startswith("mp_"):
        return "manual-programacion"
    if low.startswith("g_inst"):
        return "guia-instalacion"
    if low.startswith(("g_uso", "g_usu")):
        return "guia-uso"
    if low.startswith(("ds_", "hd_")):
        return "datasheet"
    if low.startswith(("qg_", "gr_")) or "gu__a_r__pida" in low or "guia_rapida" in low:
        return "guia-rapida"
    if low.startswith(("tg_", "nt_")):
        return "nota-tecnica"
    if "installation_sheet" in low or "installation_manual" in low:
        return "manual-instalacion"
    if "operation_manual" in low or "user" in low:
        return "manual-usuario"
    return "otro"


INCLUIBLES = {"manual-instalacion", "manual-usuario", "manual-programacion",
              "guia-instalacion", "guia-uso", "guia-rapida", "nota-tecnica", "datasheet"}

# ---- corpus actual: docs Kidde + tipos por product_model ----
U = os.environ["SUPABASE_URL"].rstrip("/")
K = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}
corpus = []
offset = 0
while True:
    r = httpx.get(f"{U}/rest/v1/documents", params={
        "select": "product_model,doc_type,source_pdf_filename,manufacturer",
        "status": "eq.active",
        "order": "id.asc", "limit": "1000", "offset": str(offset)}, headers=H, timeout=60)
    r.raise_for_status()
    lote = r.json()
    corpus.extend(lote)
    if len(lote) < 1000:
        break
    offset += 1000
print(f"corpus total (todas las marcas): {len(corpus)} docs activos")
corpus_por_pm = defaultdict(set)
for d in corpus:
    # pm puede ser lista-con-barras (convencion 'AM2020/AFP1010'; s314): cada
    # variante es una clave — sin el split, los docs recien ingestados con pm
    # de familia aparecian como gaps de si mismos.
    for pm in (d.get("product_model") or "?").upper().split("/"):
        corpus_por_pm[pm.strip()].add(d.get("doc_type") or "sin-tipo")

# corpus doc_type -> categorias del cruce que CUBRE (un doc 'instalacion' cubre
# tambien la guia de instalacion; el driver pliega guias en instalacion/usuario)
_MAPA_CORPUS_MULTI = {
    "instalacion": {"manual-instalacion", "guia-instalacion"},
    "datasheet": {"datasheet"},
    "hoja_datos": {"datasheet"},
    "usuario": {"manual-usuario", "guia-uso"},
    "operacion": {"manual-usuario", "guia-uso"},
    "programacion": {"manual-programacion"},
    "guia_rapida": {"guia-rapida"},
    "comunicacion_tecnica": {"nota-tecnica"},
}

# ---- inventario Casmar por URL unica ----
por_url = {}
for sku, urls in h["docs"].items():
    for u in urls:
        nombre = u.rsplit("/", 1)[-1]
        e = por_url.setdefault(u, {"nombre": nombre, "tipo": clasificar(nombre), "skus": []})
        e["skus"].append(sku)

incluibles = {u: e for u, e in por_url.items() if e["tipo"] in INCLUIBLES}
excluidos = {u: e for u, e in por_url.items() if e["tipo"].startswith("EXCLUIDO")}
otros = {u: e for u, e in por_url.items() if e["tipo"] == "otro"}

print(f"PDFs unicos en Casmar (Kidde): {len(por_url)}")
print(f"  incluibles: {len(incluibles)} | excluidos (homolog/cert): {len(excluidos)} | sin clasificar: {len(otros)}")
if otros:
    print("  SIN CLASIFICAR (revisar a mano):")
    for u, e in sorted(otros.items()):
        print(f"    {e['nombre']}  (skus: {', '.join(sorted(set(e['skus']))[:4])})")

# ---- cruce: para cada PDF incluible, ¿tenemos ese TIPO para alguno de sus SKUs? ----
gaps, cubiertos = [], []
for u, e in sorted(incluibles.items(), key=lambda kv: kv[1]["nombre"]):
    skus = sorted(set(e["skus"]))
    tipos_corpus = set()
    for s in skus:
        for t in corpus_por_pm.get(s.upper(), set()):
            tipos_corpus |= _MAPA_CORPUS_MULTI.get(t, {t})
    # familia NC: el corpus taguea la serie algorítmica como "NC" — NO cubre NC-PFx
    if e["tipo"] in tipos_corpus:
        cubiertos.append((e["nombre"], e["tipo"], skus))
    else:
        gaps.append({"url": u, "nombre": e["nombre"], "tipo": e["tipo"], "skus": skus,
                     "tipos_en_corpus": sorted(tipos_corpus)})

print(f"\n=== GAPS (tipo no presente en corpus para sus SKUs): {len(gaps)} ===")
for g in gaps:
    print(f"  {g['tipo']:<20} {g['nombre']}")
    print(f"      skus: {', '.join(g['skus'][:8])}{' ...' if len(g['skus'])>8 else ''} | corpus tiene: {g['tipos_en_corpus'] or '(nada)'}")

print(f"\n=== YA CUBIERTOS (mismo tipo ya en corpus): {len(cubiertos)} ===")
for nombre, tipo, skus in cubiertos:
    print(f"  {tipo:<20} {nombre}  ({', '.join(skus[:4])})")

io.open(os.path.join(SCRATCH, "casmar_kidde_cruce.json"), "w", encoding="utf-8").write(
    json.dumps({"gaps": gaps,
                "cubiertos": [{"nombre": n, "tipo": t, "skus": s} for n, t, s in cubiertos],
                "excluidos": [{"nombre": e["nombre"], "tipo": e["tipo"]} for e in excluidos.values()],
                "sin_clasificar": [{"nombre": e["nombre"], "skus": sorted(set(e["skus"]))} for e in otros.values()]},
               ensure_ascii=False, indent=1))
print("\n-> casmar_kidde_cruce.json")
