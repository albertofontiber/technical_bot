#!/usr/bin/env python3
"""s294_citation_gap.py — lista de adquisición de corpus DIRIGIDA POR CITAS ($0).

Subproducto de la medición del lever B: al clasificar las remisiones del corpus
aparecieron referencias gobernadas a documentos **que no tenemos ingestados**. Cada una
es una petición explícita del propio fabricante («consulte el manual X»), así que
priorizarlas por número de citas da una lista de adquisición basada en evidencia, no en
intuición — insumo directo para el objetivo de 30+ fabricantes y para el Excel de
inventario.

Método: barrido determinista (`order=id`) de TODO el corpus; por cada verbo de remisión,
se extrae el código de documento de su ventana y se comprueba contra los `source_file`
REALES. Los que no casan son candidatos a hueco de corpus. NO se afirma que falten: un
código puede no casar por formato del nombre de fichero — por eso el recibo emite la
cita literal, para que la adjudique una persona.

Uso: python scripts/s294_citation_gap.py [limite]
Salida: evals/s294_citation_gap_v1.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
TABLE = os.environ["CHUNKS_TABLE"]

RX_REMISION = re.compile(
    r"\b(?:consulte|consultar|v[eé]ase|ver\s+(?:el|la|los|las)|refer\s+to|see\s+(?:the)?|"
    r"rem[ií]tase)\b",
    re.IGNORECASE,
)
RX_DOCCODE = re.compile(
    r"\b([0-9]{3,}[-–][0-9]{3,}[-–]?[A-Z0-9]*|[A-Z]{2,4}-[A-Z]{2,3}-?[0-9]{2,}[A-Z]*|[0-9]{7,})\b"
)
WINDOW = 220
# Apriete de precisión: entre el verbo de remisión y el código debe haber una palabra
# que declare que se cita un DOCUMENTO. Sin esto, el código del pie de página del propio
# manual entraba como destino cuando el verbo remitía a una sección o figura
# («Véase la Sección 4.1.4 … PK-ID3000»), inflando la lista ~2x.
RX_DOC_CUE = re.compile(
    r"\b(?:manual|gu[ií]a|documento|instrucciones|hoja|ficha|ref\.?|referencia|"
    r"part\s*(?:no|number)|p/n|datasheet|catalog[oa]?)\b",
    re.IGNORECASE,
)
MAX_GAP = 100      # chars entre el verbo y el código


def norm(text: str) -> str:
    """Normaliza para comparar códigos con nombres de fichero: el corpus escribe
    `MIDT155` donde el manual cita `MI-DT-155`.  Sin esto, 160 documentos PRESENTES
    salían como ausentes (cazado en s294 antes de publicar la lista)."""
    return re.sub(r"[^0-9a-z]", "", (text or "").lower())


def sb_get(**params) -> list[dict]:
    with httpx.Client(timeout=120.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers={"apikey": SUPABASE_SERVICE_KEY,
                     "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    known: set[str] = set()
    offset = 0
    while True:
        page = sb_get(select="source_file", order="source_file", limit="1000",
                      offset=str(offset))
        if not page:
            break
        known.update(str(r.get("source_file") or "") for r in page)
        if len(page) < 1000:
            break
        offset += len(page)
    known = {f for f in known if f}
    known_norm = {norm(f) for f in known}

    citas: dict[str, list[dict]] = defaultdict(list)
    citantes: dict[str, Counter] = defaultdict(Counter)
    n_chunks = 0
    offset = 0
    while n_chunks < LIMIT:
        page = sb_get(select="id,source_file,page_number,manufacturer,content",
                      order="id", limit="1000", offset=str(offset))
        if not page:
            break
        for row in page:
            n_chunks += 1
            flat = re.sub(r"\s+", " ", str(row.get("content") or ""))
            for match in RX_REMISION.finditer(flat):
                window = flat[match.start(): match.start() + WINDOW]
                for code_match in RX_DOCCODE.finditer(window):
                    if code_match.start() > MAX_GAP:
                        break
                    if not RX_DOC_CUE.search(window[: code_match.start()]):
                        continue
                    code = code_match.group(1)
                    code_n = norm(code)
                    if len(code_n) < 5:
                        break                       # demasiado corto para identificar
                    if any(code_n in f for f in known_norm):
                        break                       # lo tenemos: no es hueco
                    if code_n in norm(str(row.get("source_file") or "")):
                        break                       # auto-referencia
                    citas[code].append({
                        "citado_por": row.get("source_file"),
                        "page_number": row.get("page_number"),
                        "manufacturer": row.get("manufacturer"),
                        "cita": window[:170],
                    })
                    citantes[code][str(row.get("manufacturer") or "?")] += 1
                    break
        if len(page) < 1000:
            break
        offset += len(page)

    ranked = sorted(citas.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    out = {
        "probe": "s294_citation_gap_v1",
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                  capture_output=True).stdout.decode().strip(),
        "n_chunks_barridos": n_chunks,
        "n_source_files_en_corpus": len(known),
        "n_documentos_citados_y_ausentes": len(ranked),
        "n_citas_totales": sum(len(v) for v in citas.values()),
        "nota": "candidatos, NO confirmados: un código puede no casar por formato del "
                "nombre de fichero. La cita literal va incluida para adjudicación humana.",
        "ranking": [
            {
                "codigo": code,
                "n_citas": len(rows),
                "fabricantes_citantes": dict(citantes[code]),
                "citado_por": sorted({str(r["citado_por"]) for r in rows})[:4],
                "ejemplo": rows[0]["cita"],
            }
            for code, rows in ranked
        ],
    }
    path = os.path.join(os.getcwd(), "evals", "s294_citation_gap_v1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps({k: out[k] for k in
                      ["n_chunks_barridos", "n_documentos_citados_y_ausentes",
                       "n_citas_totales"]}, ensure_ascii=False))
    for row in out["ranking"][:15]:
        print(f"  {row['n_citas']:3d}× {row['codigo']:22s} {list(row['fabricantes_citantes'])[:2]}")


if __name__ == "__main__":
    main()
