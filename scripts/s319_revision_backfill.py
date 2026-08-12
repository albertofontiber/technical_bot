# -*- coding: utf-8 -*-
"""s319 — Backfill de la señal de revisión en `documents` (avance PARCIAL de #4).

La puerta #73 (DEC-205) protege HACIA ADELANTE: persiste la señal de edición en
`documents.revision` al ingestar. Los ~1.069 docs previos tienen la columna
NULL → el índice de la puerta solo los ve por filename en cada lote. Este
backfill escribe la señal FILENAME-ONLY con la MISMA maquinaria de la puerta
(`senales_de_filename` + `serializar_senal` — una sola fuente de verdad).

ALCANCE v1 (dúo r17, Sol M-fuente): SOLO filename. El pase de portadas queda
detrás de un gate de equivalencia muestral (la portada del store de extracción
es OTRA fuente que la PyMuPDF de la puerta — sin gate, 1.000+ PATCHes desde
fuente no validada). Y esto es avance PARCIAL de #4 (Sol M-#4): NO rederiva
`document_family` ni construye cadenas — el censo de colisiones que emite
alimenta el packet de adjudicación, los cambios de `status` son de Alberto.

Reversible: solo escribe donde revision IS NULL; el rollback es re-anular
exactamente los ids del recibo.

Uso:
    python scripts/s319_revision_backfill.py            # dry-run + recibo
    python scripts/s319_revision_backfill.py --aplicar  # PATCHes reales
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.reingest.revision_gate import (  # noqa: E402
    indice_de_senales,
    senales_de_filename,
    serializar_senal,
)

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
     "Content-Type": "application/json"}


def _fecha_de(senal) -> str | None:
    if senal.formato not in ("fecha", "iss_fecha"):
        return None
    y, m = senal.rev[0], senal.rev[1]
    d = senal.rev[2] if len(senal.rev) > 2 else 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    filas: list[dict] = []
    with abierto(timeout=30.0) as client:
        off = 0
        while True:
            r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                           params={"select": "id,source_pdf_filename,revision,status",
                                   "status": "eq.active",
                                   "order": "id.asc", "offset": str(off),
                                   "limit": "1000"})
            r.raise_for_status()
            lote = r.json()
            filas.extend(lote)
            if len(lote) < 1000:
                break
            off += 1000

        plan: list[dict] = []
        pares_senal = []
        for fila in filas:
            fn = fila.get("source_pdf_filename") or ""
            senales = senales_de_filename(fn)
            for s in senales:
                pares_senal.append((s, fn))
            if fila.get("revision") is not None or not senales:
                continue
            # la señal a persistir: la primera de filename (misma elección que
            # la puerta cuando el veredicto no cruza con nadie)
            s = senales[0]
            plan.append({"id": fila["id"], "file": fn,
                         "revision": serializar_senal(s),
                         "revision_date": _fecha_de(s)})

        aplicadas = 0
        if args.aplicar:
            for p in plan:
                r = client.patch(
                    f"{SUPABASE_URL}/rest/v1/documents",
                    headers={**H, "Prefer": "return=minimal"},
                    params={"id": f"eq.{p['id']}"},
                    json={"revision": p["revision"],
                          "revision_date": p["revision_date"]})
                r.raise_for_status()
                aplicadas += 1

    # censo de colisiones RESULTANTE (con el índice completo ya poblado):
    # >1 revisión comparable para la misma (base, formato) = candidata a cadena
    indice = indice_de_senales(pares_senal)
    colisiones = []
    for (base, formato), entrada in sorted(indice.items()):
        por_aridad: dict[int, list] = {}
        for rev, fn in entrada.revisiones:
            por_aridad.setdefault(len(rev), []).append((rev, fn))
        for aridad, revs in por_aridad.items():
            unicas = sorted({r for r, _ in revs})
            if len(unicas) > 1:
                colisiones.append({
                    "base": base, "formato": formato,
                    "revisiones": [{"rev": ".".join(map(str, r)), "file": fn}
                                   for r, fn in sorted(revs)]})

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("Backfill FILENAME-ONLY de documents.revision (avance "
                   "parcial de #4; portadas tras gate de equivalencia; "
                   "cambios de status = adjudicación)."),
        "modo": "aplicar" if args.aplicar else "dry-run",
        "docs_activos": len(filas),
        "con_revision_previa": sum(1 for f in filas if f.get("revision")),
        "backfill_planificado": len(plan),
        "backfill_aplicado": aplicadas,
        "sin_senal_filename": (len(filas)
                               - sum(1 for f in filas if f.get("revision"))
                               - len(plan)),
        "colisiones_para_adjudicar": colisiones,
        "plan": plan,
    }
    destino = ROOT / "evals" / f"s319_revision_backfill_{recibo['modo']}_{utc}.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"{recibo['modo']}: {len(plan)} planificadas · {aplicadas} aplicadas · "
          f"{len(colisiones)} colisiones para adjudicar · "
          f"{recibo['sin_senal_filename']} sin señal de filename")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
