# -*- coding: utf-8 -*-
"""s321 E3 — Censo del re-tag F3a (solo lectura).

Contrato (IDENTITY_CATALOG_CONTRACT §F3, plan v2 r20): F3a re-taguea SOLO
documentos MONO-PRODUCTO (una entrada primary/doc en doc_map, documento
activo); multi-producto = multi-valor o paraguas, JAMÁS colapsado (censado
aquí, fuera del alcance F3a); F3b por-página sigue gated out-of-scope.

Qué mide: para cada doc mono-producto, ¿el `product_model` de sus chunks
coincide (normkey) con el `canonical_model` del producto adjudicado? El
mismatch es la lista de trabajo del re-tag — con el pm actual, el canónico, y
el conteo de chunks afectados. Recibo compacto + detalle aparte (lección r21).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag.catalog_store import load as cargar_catalogo  # noqa: E402
# (r24 Sol M4) la coherencia se mide con LA normalización del FILTRO — el
# regex imatch del retriever (normkey tira la «/» que el filtro conserva:
# ID/3000 vs ID-3000 serían «coherentes» pero irrecuperables).
from src.rag.retriever import model_to_imatch_pattern  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def _paginado(client, tabla: str, params: dict) -> list[dict]:
    filas, off = [], 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                       params={**params, "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < 1000:
            return filas
        off += 1000


cat = cargar_catalogo(ROOT / "data" / "catalog")
productos = cat.products          # dict id → producto (verificado)

with abierto(timeout=30.0) as client:
    docs = {d["id"]: d for d in _paginado(client, "documents", {
        "select": "id,source_pdf_filename,product_model,manufacturer,status",
        "status": "eq.active", "order": "id.asc"})}
    chunks = _paginado(client, "chunks_v2", {
        "select": "document_id,product_model", "order": "id.asc"})

chunks_por_doc: dict[str, Counter] = {}
for c in chunks:
    did = c.get("document_id")
    if did:
        chunks_por_doc.setdefault(did, Counter())[
            (c.get("product_model") or "").strip()] += 1

import re as _re  # noqa: E402

def _consumible(pid: str) -> tuple[str | None, str]:
    """(r24 Sol C1/Fable C1) La puerta del catálogo, no una re-implementación
    a medias: sigue redirects, veta candidate/unresolved/ausente."""
    if pid.startswith("unresolved:"):
        return None, "unresolved"
    pid = cat.follow_redirect(pid)
    prod = productos.get(pid)
    if prod is None:
        return None, "producto-ausente"
    if prod.get("candidate"):
        return None, "candidate"
    return pid, "ok"


# Contabilidad TOTAL (r24 Fable M3): cada entrada de doc_map cae en EXACTAMENTE
# un bucket y la suma se asserta contra len(doc_map).
mono, multi, sin_chunks, ya_coherentes = [], [], [], []
inactivo_stale, sin_primary, no_consumible = [], [], []
for dm in cat.doc_map:
    did = dm.get("document_id")
    doc = docs.get(did)
    fila = {"document_id": did, "source_file": dm.get("source_file")}
    if doc is None:
        inactivo_stale.append(fila)
        continue
    entries = [e for e in (dm.get("entries") or [])
               if e.get("role") == "primary" and e.get("scope") == "doc"]
    if len(entries) == 0:
        sin_primary.append(fila)
        continue
    if len(entries) > 1:
        multi.append({**fila, "n_entries": len(entries)})
        continue
    pid, motivo = _consumible(entries[0]["id"])
    if pid is None:
        no_consumible.append({**fila, "id": entries[0]["id"],
                              "motivo": motivo})
        continue
    prod = productos[pid]
    canonico = prod.get("canonical_model") or ""
    pms = chunks_por_doc.get(did)
    if not pms:
        sin_chunks.append({**fila, "id": pid})
        continue
    # coherencia = el pm del chunk MATCHEA el patrón imatch del canónico
    # (la semántica exacta del model-filter de retrieval; el patrón es
    # sabor-Postgres — \y = frontera de palabra — traducido a \b para el
    # motor local SIN cambiar la semántica)
    patron = _re.compile(
        model_to_imatch_pattern(canonico).replace(r"\y", r"\b"),
        _re.IGNORECASE)
    mismatches = {pm: n for pm, n in pms.items()
                  if not patron.search(pm or "")}
    if not mismatches:
        ya_coherentes.append(did)
        continue
    # (r24 Fable C1) partición por PROVENANCE leída de la entry, evidenciada
    prov = str(entries[0].get("provenance") or "")
    lote = "derivado" if "s320-e1" in prov else "adjudicado"
    mono.append({**fila, "producto": pid, "canonical_model": canonico,
                 "pm_doc": doc.get("product_model"), "lote": lote,
                 "provenance": prov,
                 "chunks_total": sum(pms.values()),
                 "chunks_mismatch": sum(mismatches.values()),
                 "pms_mismatch": dict(sorted(mismatches.items(),
                                             key=lambda kv: -kv[1])[:6])})

suma = (len(mono) + len(ya_coherentes) + len(multi) + len(sin_chunks)
        + len(inactivo_stale) + len(sin_primary) + len(no_consumible))
assert suma == len(cat.doc_map), f"contabilidad rota: {suma} != {len(cat.doc_map)}"

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
lotes = Counter(m["lote"] for m in mono)
compacto = {
    "que_es": ("E3 censo F3a v2 (r24): docs MONO-producto activos con producto "
               "CONSUMIBLE cuyo pm de chunks no matchea el patrón imatch del "
               "canonical_model (la semántica del filtro). Contabilidad total "
               "assertada; partición por provenance leída de las entries."),
    "utc": utc,
    "doc_map_entradas": len(cat.doc_map),
    "buckets": {
        "mono_con_mismatch": len(mono),
        "mono_ya_coherentes": len(ya_coherentes),
        "multi_producto_fuera_f3a": len(multi),
        "mono_sin_chunks": len(sin_chunks),
        "inactivo_o_stale": len(inactivo_stale),
        "sin_entry_primary_doc": len(sin_primary),
        "producto_no_consumible": len(no_consumible),
    },
    "suma_verificada": suma,
    "chunks_afectados": sum(m["chunks_mismatch"] for m in mono),
    "mismatch_por_lote": dict(lotes),
    "muestras_mismatch": mono[:10],
    "no_consumible_detalle": no_consumible,
    "detalle_completo": "evals/s321_e3_censo_v2_detalle.json",
}
(ROOT / "evals" / "s321_e3_censo_v2_detalle.json").write_text(
    json.dumps({"mono_mismatch": mono, "multi": multi,
                "sin_chunks": sin_chunks, "inactivo_stale": inactivo_stale,
                "sin_primary": sin_primary}, ensure_ascii=False, indent=1),
    encoding="utf-8")
(ROOT / "evals" / "s321_e3_censo_v2.json").write_text(
    json.dumps(compacto, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"doc_map {len(cat.doc_map)} = {compacto['buckets']} (suma {suma}) · "
      f"chunks afectados {compacto['chunks_afectados']} · "
      f"lotes {dict(lotes)}")
print("recibo -> evals/s321_e3_censo_v2.json")
