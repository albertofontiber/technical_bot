#!/usr/bin/env python3
"""s334d — verifica con CITA las `doc_map_altas` que el dúo r43 llamó fabricadas.

EL HALLAZGO QUE ESTO CIERRA (Sol #2, crítico): el plan s334b añadía 43 filas al
`doc_map` con `role: secondary` y la provenance decía «el manual lo menciona y
sirve como fuente» — pero eso lo yo lo DEDUJE de que el paraguas las traía antes,
sin leer los documentos. Sol lo dijo con precisión: «sin leer esos documentos, el
plan fabrica atestaciones para hacer verde el mismo gate de fuentes que evalúa el
cambio». Tenía razón, y la respuesta no es discutirlo: es leerlos.

QUÉ HACE. Para cada `(producto, documento)` propuesto, busca el canónico del
producto **y todos sus alias** en el texto de ESE documento, con frontera de
palabra (R4). Tres resultados:
  · **VERIFICADA** — hay cita: la atestación es un hecho leído y la fila entra.
  · **SIN CITA** — el documento no lo nombra: la fila SALE. Que el paraguas lo
    trajera antes no lo convierte en fuente de este producto.
  · **SIN TEXTO** — el documento no tiene chunks; no se puede afirmar nada.

NO escribe: produce el veredicto por fila para que el plan se regenere con sólo
las verificadas.

Uso:  python scripts/s334d_verifica_atestaciones.py [--plan X]
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
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
PLAN = ROOT / "evals/s334b_huerfanos_plan.json"
SALIDA = ROOT / "evals/s334d_atestaciones_verificadas.json"
CITA_MAX = 180


def _pag(c: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = c.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        if r.status_code != 200:
            return out
        pag = r.json()
        out += pag
        if len(pag) < 1000:
            return out
        off += 1000


def cita(texto: str, token: str) -> str | None:
    if not texto or not token:
        return None
    m = re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", texto, re.I)
    if not m:
        return None
    a, b = max(0, m.start() - CITA_MAX // 2), min(len(texto), m.end() + CITA_MAX // 2)
    return re.sub(r"\s+", " ", texto[a:b]).strip()


def main() -> int:
    plan_path = Path(sys.argv[sys.argv.index("--plan") + 1]) if "--plan" in sys.argv else PLAN
    plan = json.loads(plan_path.read_text("utf-8"))
    altas = plan.get("doc_map_altas") or []
    if not altas:
        print("el plan no propone doc_map_altas — nada que verificar")
        return 0
    cat = cs.load()
    alias_de = defaultdict(list)
    for a in cat.aliases:
        alias_de[a["id"]].append(a["alias"])

    pares = [(e["id"], row["source_file"], row["document_id"])
             for row in altas for e in row["entries"]]
    docs = sorted({sf for _, sf, _ in pares})
    print(f"atestaciones propuestas: {len(pares)}  ·  documentos a leer: {len(docs)}")

    texto = {}
    with httpx.Client(timeout=120) as c:
        for i, sf in enumerate(docs, 1):
            filas = _pag(c, "chunks_v2", {"select": "content", "source_file": f"eq.{sf}"})
            texto[sf] = " ".join(str(f.get("content") or "") for f in filas)
            if i % 10 == 0:
                print(f"  …{i}/{len(docs)}", flush=True)

    filas_out, n = [], defaultdict(int)
    for pid, sf, did in pares:
        p = cat.products.get(pid)
        tokens = ([p["canonical_model"]] if p else []) + alias_de.get(pid, [])
        cuerpo = texto.get(sf, "")
        encontrada, tok_ok = None, None
        for t in tokens:
            encontrada = cita(cuerpo, t)
            if encontrada:
                tok_ok = t
                break
        if not cuerpo:
            v = "SIN_TEXTO"
        elif encontrada:
            v = "VERIFICADA"
        else:
            v = "SIN_CITA"
        n[v] += 1
        filas_out.append({"id": pid, "source_file": sf, "document_id": did,
                          "veredicto": v, "token": tok_ok, "cita": encontrada,
                          "tokens_probados": len(tokens)})

    print("\n=== ATESTACIONES ===")
    for k in ("VERIFICADA", "SIN_CITA", "SIN_TEXTO"):
        if n[k]:
            print(f"  {k:12s} {n[k]:3d}")
    for f in filas_out:
        if f["veredicto"] != "VERIFICADA":
            print(f"    fuera: {f['id']:28s} ← {f['source_file'][:44]}")

    SALIDA.write_text(json.dumps(
        {"que_es": "Verificación con CITA (R4) de las `doc_map_altas` del plan s334b, tras el "
                   "hallazgo crítico de Sol en r43: estaban DEDUCIDAS de que el paraguas las "
                   "traía, no leídas. NADA aplicado.",
         "resumen": dict(n), "filas": filas_out}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
