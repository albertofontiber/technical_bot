#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s317 — Censo de revisión sobre el corpus REAL (#73, validación del gate).

Dos preguntas: (1) ¿cuántos documentos activos emiten señal de edición legible
(cobertura del extractor sobre nombres reales, no inventados)? (2) ¿qué PARES
de documentos activos comparten (base, formato) con revisiones DISTINTAS?
Cada par es una superseded-pair YA VIVA (clase #4), censo adjudicable por
Alberto.

FRAMING HONESTO (dúo r13): (a) la puerta v1 solo habría evitado un par si las
revisiones llegaron en lotes DISTINTOS y la vieja DESPUÉS — la v1.1 añade el
cruce intra-lote y la dirección vieja-primero sigue viva por diseño (SUPERSEDE
procede; la cadena #4 es quien retira a la vieja); (b) este censo solo ve pares
DENTRO de una familia de señal — un par con nomenclaturas de familias DISTINTAS
es invisible (par conocido: MI Casmar 202502 ↔ bcn-3100017 r002, DEC-192);
(c) «0 colisiones falsas» = entre las DETECTADAS, verificadas a mano — no hay
oráculo de exhaustividad.

$0 y read-only. Recibo → evals/s317_revision_census_v1.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.ingestion.supabase_client import SupabaseHTTP  # noqa: E402
from src.reingest.revision_gate import senales_de_filename  # noqa: E402


def documents_activos(sb: SupabaseHTTP) -> list[dict]:
    filas, off, pagina = [], 0, 1000
    while True:
        lote = sb.fetch_rows("documents",
                             select="id,source_pdf_filename,manufacturer",
                             filters={"status": "eq.active", "order": "id.asc",
                                      "offset": str(off)}, limit=pagina)
        filas.extend(lote)
        if len(lote) < pagina:
            return filas
        off += pagina


def main() -> int:
    sb = SupabaseHTTP()
    filas = documents_activos(sb)
    print(f"documents activos: {len(filas)} (paginado)")

    por_clave: dict[tuple[str, str], list[tuple[tuple, str, str]]] = defaultdict(list)
    con_senal = 0
    for fila in filas:
        fn = fila.get("source_pdf_filename") or ""
        senales = senales_de_filename(fn)
        if senales:
            con_senal += 1
        for s in senales:
            por_clave[(s.base, s.formato)].append(
                (s.rev, fn, fila.get("manufacturer") or "?"))

    pares = []
    for (base, formato), docs in sorted(por_clave.items()):
        revs = {d[0] for d in docs}
        if len(revs) < 2:
            continue
        comparables = {len(r) for r in revs}
        docs_orden = sorted(docs, key=lambda d: d[0])
        pares.append({
            "base": base, "formato": formato,
            "comparable": len(comparables) == 1,
            "docs": [{"rev": ".".join(map(str, r)), "file": f, "mfr": m}
                     for r, f, m in docs_orden],
        })

    print(f"con señal de edición legible: {con_senal}/{len(filas)} "
          f"({con_senal / max(len(filas), 1):.0%})")
    print(f"claves (base, formato) con >1 revisión ACTIVA: {len(pares)}")
    for p in pares:
        marca = "PAR" if p["comparable"] else "PAR?"
        print(f"  [{marca}] {p['formato']:9s} «{p['base'][:60]}»")
        for d in p["docs"]:
            print(f"        rev {d['rev']:>8s}  {d['file']}")

    recibo = {
        "censo": "s317 revision gate sobre corpus real (#73)",
        "documents_activos": len(filas),
        "con_senal": con_senal,
        "pares_multirevision_activos": pares,
    }
    out = ROOT / "evals" / "s317_revision_census_v1.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"recibo → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
