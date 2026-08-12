# -*- coding: utf-8 -*-
"""s320 E0 — Censo FRESCO de datos del elefante (plan v2, dúo r20).

El plan lo exige ANTES de dimensionar nada (Fable F4: E0 fija, E1 consume):
1. Cobertura de doc_map sobre los documents ACTIVOS de hoy (post-Kidde s314).
2. pm genérico/familia SIN umbral (el censo s315 cortaba en >=3 menciones).
3. chunks unknown post-s314 (el «1» de DEC-161 era pre-lote).
4. candidates del catálogo por estado/familia (la cifra ~630 era de s99b).
5. Frescura del snapshot model_catalog.json vs corpus (Fable F5: el detector
   de producción vive de él; regenerado ~18-jul, PRE-Kidde).

Solo lectura. Recibo → evals/s320_e0_censo_v1.json.
"""
from __future__ import annotations

import json
import re
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

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
CAT = ROOT / "data" / "catalog"


def _jsonl(nombre: str) -> list[dict]:
    return [json.loads(l) for l in (CAT / nombre).read_text(encoding="utf-8")
            .splitlines() if l.strip()]


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


def _norm(s: str) -> str:
    return re.sub(r"\.pdf$", "", (s or "").strip().lower())


with abierto(timeout=30.0) as client:
    docs = _paginado(client, "documents", {
        "select": "id,source_pdf_filename,product_model,manufacturer,status",
        "status": "eq.active", "order": "id.asc"})
    chunks_pm = _paginado(client, "chunks_v2", {
        "select": "product_model,source_file", "order": "id.asc"})

# 1) cobertura doc_map
doc_map = _jsonl("doc_map.jsonl")
mapeados = {_norm(e.get("doc") or e.get("source_file") or "") for e in doc_map}
activos = {_norm(d["source_pdf_filename"]): d for d in docs}
sin_entrada = sorted(set(activos) - mapeados)
por_marca_sin = Counter(activos[f].get("manufacturer") or "?" for f in sin_entrada)

# 2) pm genérico/familia sin umbral (heurística declarada: pm sin dígito
#    O pm que es prefijo-familia de >=2 pm distintos del corpus)
pms_docs = Counter((d.get("product_model") or "").strip() for d in docs)
sin_digito = sorted(pm for pm in pms_docs if pm and not re.search(r"\d", pm))

# 3) unknown post-s314
unknown_chunks = sum(1 for c in chunks_pm
                     if (c.get("product_model") or "").strip().lower()
                     in ("unknown", ""))
unknown_files = sorted({c["source_file"] for c in chunks_pm
                        if (c.get("product_model") or "").strip().lower()
                        in ("unknown", "")})

# 4) candidates del catálogo (esquema REAL verificado: campo booleano
#    `candidate` + `estado`; el primer run del censo usó `status` inexistente
#    y dio 0 — regla C sobre el propio instrumento)
productos = _jsonl("products.jsonl")
estados = Counter(str(p.get("estado")) for p in productos)
candidates = [p for p in productos if p.get("candidate")]
cand_por_marca = Counter((p.get("id") or ":").split(":")[0]
                         for p in candidates)

# 5) frescura del snapshot del detector (esquema real: {build, excluded, models})
snapshot = json.loads((ROOT / "data" / "model_catalog.json")
                      .read_text(encoding="utf-8"))
modelos_snapshot = {str(m.get("model") if isinstance(m, dict) else m)
                    for m in snapshot.get("models", [])}
pms_corpus = {pm for pm in pms_docs if pm}
solo_corpus = sorted(pms_corpus - {str(m) for m in modelos_snapshot})[:200]

utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
recibo = {
    "que_es": "E0 del elefante (plan v2): las cifras frescas que E1-E3 consumen.",
    "utc": utc,
    "docs_activos": len(docs),
    "chunks_totales": len(chunks_pm),
    "doc_map": {"entradas": len(doc_map),
                "activos_sin_entrada": len(sin_entrada),
                "sin_entrada_por_marca": dict(por_marca_sin.most_common()),
                "sin_entrada_lista": sin_entrada},
    "pm_generico": {"pms_distintos_docs": len(pms_docs),
                    "sin_digito": sin_digito},
    "unknown": {"chunks": unknown_chunks, "source_files": unknown_files},
    "candidates": {"por_estado": dict(estados),
                   "candidates_total": len(candidates),
                   "por_marca": dict(cand_por_marca.most_common())},
    "snapshot_detector": {"modelos": len(modelos_snapshot),
                          "pms_corpus_fuera_del_snapshot_muestra": solo_corpus},
}
destino = ROOT / "evals" / "s320_e0_censo_v1.json"
destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
print(f"activos {len(docs)} · doc_map {len(doc_map)} entradas · "
      f"sin entrada {len(sin_entrada)} · pm sin dígito {len(sin_digito)} · "
      f"unknown {unknown_chunks} chunks/{len(unknown_files)} files · "
      f"candidates {len(candidates)} · snapshot {len(modelos_snapshot)} modelos")
print(f"recibo -> {destino}")
