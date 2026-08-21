#!/usr/bin/env python3
"""s334 — POBLACIÓN de la sonda multimodal: candidates cuyo nombre la extracción PERDIÓ.

LA HIPÓTESIS QUE SE VA A MEDIR (de Alberto, 21-ago): «Gemini parece que hace mejor
la detección de modelos cuando le he subido documentos en pdf sin nombres de
modelos». Y su segunda observación: los candidates con 0 menciones «pueden ser
esquemas de montaje o cableado que sí pueden ser útiles».

Las dos son la MISMA cosa, y el caso `MAD-491` lo demuestra: su manual está en el
corpus, el texto extraído dice «MÓDULO AISLADOR Y ZÓCALO AISLADOR» y «REF:
55349102» —la referencia del documento— y el resto son marcadores `[Diagram: …]`.
El modelo real sólo sobrevive en el NOMBRE DEL FICHERO. O sea que «0 menciones»
no mide si el producto existe: mide **si la extracción de texto conservó su
nombre**. Y donde no lo conservó es exactamente donde una lectura de la PÁGINA
podría recuperarlo.

QUÉ SELECCIONA ESTE SCRIPT. Los candidates que cumplen las tres:
  1. tienen un documento que los atesta (`doc_map`),
  2. su token NO aparece en el texto de ESE documento (la pérdida),
  3. ese documento tiene alguna página renderizada en `document_visual_assets`
     (16.343 páginas, DEC-123) — sin imagen no hay nada que leer.

El (2) es por DOCUMENTO, no por corpus: un token puede aparecer en otro manual y
seguir estando perdido en el suyo, que es lo que importa para esta sonda.

NO decide nada ni escribe en el catálogo: sólo produce la lista y su recibo.

Uso:  python scripts/s334_sonda_multimodal_poblacion.py [--salida evals/....json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
SALIDA = ROOT / "evals/s334_sonda_multimodal_poblacion_v1.json"


def _norm(s: str) -> str:
    """Comparación tolerante: sin separadores ni caja. `MAD-491` ≡ `MAD 491` ≡
    `mad491`. Es deliberadamente laxa — para DECIDIR que el nombre se perdió hay
    que ser lo más generoso posible con que esté presente."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _paginado(cliente: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = cliente.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        r.raise_for_status()
        pagina = r.json()
        out += pagina
        if len(pagina) < 1000:
            return out
        off += 1000


def main() -> int:
    prod = [json.loads(l) for l in (ROOT / "data/catalog/products.jsonl")
            .read_text("utf-8").splitlines() if l.strip()]
    cand = {p["id"]: p for p in prod
            if p.get("candidate") and p.get("estado") == "activo"}
    doc_map = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
               .read_text("utf-8").splitlines() if l.strip()]

    # candidate -> [(source_file, document_id)]
    fuentes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fila in doc_map:
        sf = str(fila.get("source_file") or "")
        did = str(fila.get("document_id") or "")
        for e in fila.get("entries", []):
            if e.get("id") in cand:
                fuentes[e["id"]].append((sf, did))

    con_fuente = {k: v for k, v in fuentes.items() if v}
    print(f"candidates activos: {len(cand)} · con documento: {len(con_fuente)}")

    with httpx.Client(timeout=90) as c:
        # 1) el texto de cada documento implicado, UNA vez
        docs = sorted({sf for v in con_fuente.values() for sf, _ in v})
        print(f"documentos implicados: {len(docs)} — leyendo su texto…")
        texto: dict[str, str] = {}
        for i, sf in enumerate(docs, 1):
            filas = _paginado(c, "chunks_v2",
                              {"select": "content", "source_file": f"eq.{sf}"})
            texto[sf] = _norm(" ".join(str(f.get("content") or "") for f in filas))
            if i % 50 == 0:
                print(f"  …{i}/{len(docs)}", flush=True)

        # 2) las páginas renderizadas que existen, por document_id
        print("leyendo el registro de páginas renderizadas…")
        assets = _paginado(c, "document_visual_assets",
                           {"select": "document_id,page_index,visual_role,"
                                      "technical_utility,storage_url,media_type"})
        por_doc: dict[str, list[dict]] = defaultdict(list)
        for a in assets:
            por_doc[str(a.get("document_id"))].append(a)
        for v in por_doc.values():
            v.sort(key=lambda a: a.get("page_index") or 0)
        print(f"  {len(assets)} páginas en {len(por_doc)} documentos")

    perdidos, presentes, sin_imagen, controles = [], 0, [], []
    for pid, lista in sorted(con_fuente.items()):
        tok = _norm(cand[pid]["canonical_model"])
        if not tok:
            continue
        # ¿está el token en el texto de ALGUNO de sus documentos?
        if any(tok in texto.get(sf, "") for sf, _ in lista):
            presentes += 1
            # GRUPO DE CONTROL: el token SÍ está en el texto, así que sabemos que
            # el documento nombra el modelo. Si los lectores fallan también aquí,
            # un fallo en los perdidos no dice nada del multimodal — dice que el
            # instrumento no sirve. Sin este control la sonda no es interpretable.
            for sf, did in lista:
                ps = por_doc.get(did, [])
                if ps and len(controles) < 20:
                    controles.append({
                        "id": pid, "canonico": cand[pid]["canonical_model"],
                        "source_file": sf, "document_id": did, "n_paginas": len(ps),
                        "paginas": [{"page_index": q.get("page_index"),
                                     "visual_role": q.get("visual_role"),
                                     "technical_utility": q.get("technical_utility"),
                                     "storage_url": q.get("storage_url"),
                                     "media_type": q.get("media_type")} for q in ps[:2]],
                    })
                    break
            continue
        # perdido: ¿hay página renderizada de alguno de sus documentos?
        paginas = [(sf, did, por_doc.get(did, [])) for sf, did in lista]
        con_img = [(sf, did, ps) for sf, did, ps in paginas if ps]
        if not con_img:
            sin_imagen.append({"id": pid, "canonico": cand[pid]["canonical_model"],
                               "docs": [sf for sf, _ in lista]})
            continue
        sf, did, ps = con_img[0]
        perdidos.append({
            "id": pid,
            "canonico": cand[pid]["canonical_model"],
            "source_file": sf,
            "document_id": did,
            "n_paginas": len(ps),
            # la PORTADA es donde suele vivir el nombre; se guarda también la
            # segunda por si la primera es una tapa sin datos
            "paginas": [{"page_index": p.get("page_index"),
                         "visual_role": p.get("visual_role"),
                         "technical_utility": p.get("technical_utility"),
                         "storage_url": p.get("storage_url"),
                         "media_type": p.get("media_type")} for p in ps[:2]],
        })

    total = presentes + len(perdidos) + len(sin_imagen)
    print(f"\n=== POBLACIÓN DE LA SONDA ===")
    print(f"  candidates con documento ..................... {total}")
    print(f"  su token SÍ está en el texto del documento ... {presentes} "
          f"({presentes * 100 // max(1, total)}%)")
    print(f"  token PERDIDO y CON página renderizada ....... {len(perdidos)} "
          f"({len(perdidos) * 100 // max(1, total)}%)  ← la sonda")
    print(f"  token perdido y SIN página renderizada ....... {len(sin_imagen)} "
          f"({len(sin_imagen) * 100 // max(1, total)}%)  ← no medible")

    roles = defaultdict(int)
    for p in perdidos:
        roles[p["paginas"][0]["visual_role"]] += 1
    print(f"\n  rol de la primera página de los medibles: {dict(roles)}")
    print(f"  GRUPO DE CONTROL (token SÍ en el texto, con imagen): {len(controles)}")

    salida = {
        "que_es": "Población de la sonda multimodal s334: candidates cuyo token "
                  "NO aparece en el texto de su propio documento y cuyo documento "
                  "SÍ tiene página renderizada. NADA aplicado.",
        "hipotesis": "Una lectura de la PÁGINA recupera nombres de modelo que la "
                     "extracción de texto perdió (Alberto, 21-ago).",
        "resumen": {"con_documento": total, "token_presente": presentes,
                    "perdido_medible": len(perdidos),
                    "perdido_sin_imagen": len(sin_imagen),
                    "controles": len(controles),
                    "roles_primera_pagina": dict(roles)},
        "medibles": perdidos,
        "controles": controles,
        "no_medibles_sin_imagen": sin_imagen,
    }
    destino = Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else SALIDA
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
