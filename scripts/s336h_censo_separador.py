#!/usr/bin/env python
"""s336h — ¿cuántos términos del detector puede pegar el separador-espacio?

Nace de un falso positivo concreto: promoviendo `AM-LCD` (s336f), su core
`am[-\\s/.+]*lcd` casa dentro de «Pantalla **FM/AM LCD**» —un manual de radio—
porque el separador admite el espacio y `\\b` se cumple detrás de la barra. Eso
me hizo sacar `AM-LCD` del lote y dejar la pregunta abierta: **¿debe un término
SIN DÍGITOS exigir el separador?**

Esto NO cambia nada: dimensiona la pregunta. Un término es vulnerable a esta
clase sólo si cumple las dos cosas:
  · **multi-segmento** — un solo segmento no tiene separador que aflojar;
  · **sin dígitos** — con dígitos, la adyacencia accidental es muy improbable
    («FM/AM LCD» pasa; «FM/AM 6000» no aparece en prosa técnica).

Y para los vulnerables se mide lo único que decide: **¿el corpus contiene una
aparición del core que NO es el producto?** Sin eso, «podría fallar» es teoría.

Aviso que me hago a mí mismo: el core del detector documenta
«v2.2: '≤3 chars' mataba zxe», o sea que **el umbral de sigla corta ya se probó
en el core y se revirtió** porque mataba productos reales. Mi R19 lo reintrodujo
por la puerta de atrás en `s336e` (bloquea siglas de ≤3 letras). Queda declarado:
esa parte de R19 re-litiga algo que el código ya zanjó, y hay que medirla igual
que esto en vez de darla por buena.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog as C                               # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402
from src.rag import catalog_resolver as cr                     # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
SALIDA = ROOT / "evals/s336h_censo_separador.json"
TABLA = "chunks_v2"


def pagina(tabla: str, params: dict, orden: str = "id") -> list[dict]:
    """`order` explícito + verificación contra `count=exact`: sin eso PostgREST
    no garantiza orden estable entre rangos y la paginación salta filas."""
    out, desde = [], 0
    with httpx.Client(timeout=300) as c:
        r0 = c.get(f"{SB}/{tabla}", headers={**H, "Prefer": "count=exact"},
                   params={**params, "limit": "1"})
        total = int((r0.headers.get("content-range") or "0/0").split("/")[-1] or 0)
        while True:
            r = c.get(f"{SB}/{tabla}", headers={**H, "Range-Unit": "items",
                      "Range": f"{desde}-{desde+999}"},
                      params={**params, "order": orden})
            r.raise_for_status()
            d = r.json()
            out += d
            if len(d) < 1000:
                break
            desde += 1000
    if len(out) != total:
        raise SystemExit(f"paginación incompleta en {tabla}: {len(out)} de {total}")
    return out


def terminos_del_detector(cat) -> dict[str, str]:
    """El MISMO diccionario que construye el detector, no una reimplementación."""
    return cr._resolvable_terms(cat)


def main() -> int:
    cat = cs.load()
    terms = terminos_del_detector(cat)
    fuentes: dict[str, set[str]] = defaultdict(set)
    for f in cat.doc_map:
        for e in f.get("entries", []):
            pid = str(e.get("id"))
            p = cat.products.get(pid) or {}
            if p.get("canonical_model"):
                fuentes[C.normkey(p["canonical_model"])].add(str(f.get("document_id")))

    vulnerables = {}
    for nk, t in terms.items():
        segs = C._segments(C._fold(t))
        if len(segs) > 1 and not any(ch.isdigit() for ch in t):
            vulnerables[nk] = t

    print(f"=== POBLACIÓN ===")
    print(f"  términos en el detector .................... {len(terms)}")
    print(f"  VULNERABLES (multi-segmento y sin dígitos) . {len(vulnerables)}  "
          f"({100*len(vulnerables)//max(len(terms),1)}%)")
    if not vulnerables:
        print("  nada que medir.")
        return 0

    print(f"\nbajando {TABLA} …", flush=True)
    ch = pagina(TABLA, {"select": "id,document_id,content"})
    por_doc = defaultdict(list)
    for x in ch:
        por_doc[str(x.get("document_id"))].append(x.get("content") or "")
    print(f"  {len(ch)} chunks en {len(por_doc)} documentos\n")

    filas = []
    print("=== ¿EL CORPUS TIENE APARICIONES QUE NO SON EL PRODUCTO? ===")
    for nk, t in sorted(vulnerables.items()):
        core = C._core(t)
        if not core:
            continue
        rx = re.compile(rf"\b{core}\b(?!\d)", re.I)
        hits = {d for d, ts in por_doc.items() if any(rx.search(x or "") for x in ts)}
        suyos = fuentes.get(nk, set())
        ajenos = sorted(hits - suyos)
        ejemplos = []
        for d in ajenos[:3]:
            ej = next((x for x in por_doc[d] if rx.search(x or "")), "")
            m = rx.search(ej)
            if m:
                ejemplos.append(ej[max(0, m.start() - 46):m.end() + 46].replace("\n", " ").strip())
        fila = {"termino": t, "normkey": nk, "core": core, "documentos": len(hits),
                "suyos": len(hits & suyos), "ajenos": len(ajenos), "ejemplos": ejemplos}
        filas.append(fila)
        if ajenos:
            print(f"  {t[:26]:28s} {len(hits):3d} docs · ajenos {len(ajenos):3d}")
            for e in ejemplos[:1]:
                print(f"       «{e[:96]}»")

    con_ajenos = [f for f in filas if f["ajenos"]]
    print(f"\n=== RESUMEN ===")
    print(f"  vulnerables medidos ......................... {len(filas)}")
    print(f"  con apariciones AJENAS en el corpus ......... {len(con_ajenos)}")
    print(f"  sin ninguna ................................. {len(filas)-len(con_ajenos)}")
    print("\n  «Ajeno» NO es sinónimo de falso positivo: una tabla de compatibilidad que")
    print("  nombra el producto correctamente también sale ajena. Hay que LEER los ejemplos.")

    SALIDA.write_text(json.dumps(
        {"que_es": ("s336h · dimensiona la pregunta que dejó abierta s336f: ¿debe un término SIN "
                    "DÍGITOS exigir el separador en el detector? Vulnerable = multi-segmento y sin "
                    "dígitos, que es cuando el separador-espacio puede pegar dos palabras ajenas "
                    "(«Pantalla FM/AM LCD» casando el core de `AM-LCD`). NADA aplicado."),
         "aviso": ("el core documenta «v2.2: '≤3 chars' mataba zxe»: el umbral de sigla corta YA se "
                   "probó en el core y se revirtió por matar productos reales. Mi R19 (s336e) lo "
                   "reintrodujo bloqueando siglas de ≤3 letras — queda declarado como pendiente de "
                   "medir, no como regla buena."),
         "n_terminos_detector": len(terms), "n_vulnerables": len(vulnerables),
         "n_con_ajenos": len(con_ajenos), "filas": filas},
        ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
