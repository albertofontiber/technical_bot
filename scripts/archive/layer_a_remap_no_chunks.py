#!/usr/bin/env python3
"""Re-mapea las 8 hp* SIN relevant_chunks a sus manuales canónicos.

El mapeo original (layer_a_map_pdfs.py) buscaba por filename, que falla para
manuales con código de documento (MPDT-190 = ID3000). Ahora que el fix B5
pobló product_model correctamente en chunks_v2, derivamos los source_files
reales por product_model y los resolvemos a PDFs físicos.

Actualiza evals/gold_layer_a_mapping.json (campo pdf_candidates de las 8).

Uso: python scripts/layer_a_remap_no_chunks.py [--apply]
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
MAPPING = "evals/gold_layer_a_mapping.json"

MANUAL_DIRS = [Path(d) for d in [
    "Manuales_ES", "Manuales_Notifier", "Manuales_Notifier_Privado",
    "Manuales_Morley", "Manuales_Morley_Privado", "Manuales_Morley_Guias", "manuales",
]]

# Producto canónico (imatch en chunks_v2.product_model) + selección de los
# source_files relevantes a CADA pregunta. El imatch por producto trae toda la
# familia/todos los tipos de manual; acotamos por código de manual, variante e
# idioma para no inundar a Opus con PDFs irrelevantes.
#   prefer_codes: prefijos de código de doc preferidos (MP=programación,
#                 MI=instalación, MC=config/usuario, MF=funcionamiento)
#   must: substring que el source_file debe contener (variante específica)
#   exclude: substring que descarta (falsos positivos del imatch)
#   max: nº máximo de PDFs a pasar a Opus
PRODUCTS: dict[str, dict] = {
    "hp005": {"q": "ID3000", "prefer_codes": ["MPDT", "MCDT"], "max": 2},   # programar zona
    "hp008": {"q": "ID3000", "prefer_codes": ["MIDT", "MCDT"], "max": 2},   # detectores compatibles
    "hp007": {"q": "VESDA", "must": "VEP", "max": 2},                        # VESDA-E VEP
    "hp013": {"q": "ADW", "must": "ADW535", "max": 1},                       # ADW535
    "hp015": {"q": "CCD-103", "max": 1},                                     # CCD-103 (único)
    "hp017": {"q": "PEARL", "exclude": "port", "max": 1},                    # PEARL ES (no PT)
    "hp019": {"q": "ASD", "must": "ASD53", "max": 4},                        # serie ASD (no FAAST)
    "hp020": {"q": "INSPIRE", "must": "HOP-138", "exclude": "PT", "max": 2}, # INSPIRE ES
}


def normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def find_pdf(stem: str) -> list[str]:
    target = normalize(stem)
    hits = []
    for base in MANUAL_DIRS:
        if base.exists():
            for p in base.rglob("*.pdf"):
                if target in normalize(p.stem):
                    hits.append(str(p))
    return hits


def main() -> int:
    apply = "--apply" in sys.argv
    c = httpx.Client(timeout=120.0)
    mapping = json.loads(Path(MAPPING).read_text(encoding="utf-8"))

    for qid, cfg in PRODUCTS.items():
        prod = cfg["q"]
        r = c.get(f"{URL}/rest/v1/chunks_v2", headers=H, params={
            "select": "source_file,product_model",
            "product_model": f"imatch.\\y{prod}",
            "limit": "5000"})
        rows = r.json() if r.status_code == 200 else []
        src = Counter(x["source_file"] for x in rows)

        # Filtrar source_files por los criterios de la pregunta
        def keep(sf: str) -> bool:
            if cfg.get("must") and cfg["must"].lower() not in sf.lower():
                return False
            if cfg.get("exclude") and cfg["exclude"].lower() in sf.lower():
                return False
            return True

        candidates = [sf for sf in src if keep(sf)]
        # Priorizar por prefijo de código preferido, luego por nº de chunks
        prefer = cfg.get("prefer_codes", [])
        def rank(sf: str):
            pref_rank = next((i for i, code in enumerate(prefer)
                              if sf.upper().startswith(code)), len(prefer))
            return (pref_rank, -src[sf])
        candidates.sort(key=rank)
        selected = candidates[:cfg.get("max", 2)]

        pdfs: dict[str, list[str]] = {}
        for sf in selected:
            found = find_pdf(sf)
            if found:
                pdfs[sf] = found

        print(f"=== {qid} (producto={prod}) ===")
        print(f"  {len(rows)} chunks en {len(src)} docs; "
              f"{len(candidates)} tras filtro; {len(selected)} seleccionados:")
        for sf in selected:
            ok = "OK" if sf in pdfs else "SIN PDF"
            print(f"    [{ok}] {src[sf]:4} chunks  {sf}")

        if apply:
            mapping[qid]["pdf_candidates"] = pdfs
            mapping[qid]["remapped_via_product_model"] = prod
        print()

    if apply:
        Path(MAPPING).write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Mapping actualizado en {MAPPING}")
    else:
        print("[DRY-RUN] re-ejecuta con --apply para actualizar el mapping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
