# -*- coding: utf-8 -*-
"""s336 B4b — verificación FULL-TEXT + completitud de CAPACIDAD (v3 §1.4-1.5).

Sol-2 (crítico r1): la cita ÍNTEGRA de cada campo se verifica contra el TEXTO
COMPLETO de los docs del producto (con espacios normalizados — los joins de
chunks driftean whitespace); el doc que la contiene queda ATRIBUIDO
(`clasificacion.doc` / `atributos.*.doc`). Sin full-text → fuera del write.

Sol2-1 (crítico r2): la divergencia NO OBSERVADA no puede escribirse como
fusión — TODOS los docs del producto se barren (regex) buscando menciones de
lazos/zonas. Si un doc menciona capacidad y ninguna entrada verificada se le
atribuye, o si las entradas verificadas divergen en max, la CAPACIDAD ENTERA
va a packet (la categoría sigue siendo escribible). Conservador a propósito.

#76b: `alcance` {eje: idioma_doc} se deriva MECÁNICAMENTE de marcadores del
source_file; sin marcador → se omite (jamás se inventa).

Uso: python scripts/s336_capacidad_y_fulltext.py --poblacion evals/s336_poblacion_v1.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

_RX_CAP = re.compile(
    r"\b\d{1,2}\s*(?:lazos?|loops?|bucles?|zonas?|zones?)\b", re.IGNORECASE)
_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "")).strip().lower()


_texto_cache: dict[str, str] = {}


def _texto(c, sf: str) -> str:
    if sf not in _texto_cache:
        filas, offset = [], 0
        while True:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "chunk_index,content",
                              "source_file": f"eq.{sf}",
                              "order": "chunk_index.asc",
                              "limit": "100", "offset": str(offset)})
            r.raise_for_status()
            lote = r.json()
            filas.extend(lote)
            if len(lote) < 100:
                break
            offset += 100
        _texto_cache[sf] = _norm("\n".join((x.get("content") or "")
                                           for x in filas))
    return _texto_cache[sf]


def _doc_de(c, docs, cita) -> str | None:
    frag = _norm(cita)
    if not frag:
        return None
    for sf in docs:
        if frag in _texto(c, sf):
            return sf
    return None


def _alcance_de(sf: str) -> dict | None:
    s = sf.lower()
    if re.search(r"(_|-|\b)(es|sp|esp)(\b|_|-|\.)|espanol|_spa", s):
        return {"eje": "idioma_doc", "valor": "es"}
    if re.search(r"(_|-|\b)(en|eng)(\b|_|-|\.)|english", s):
        return {"eje": "idioma_doc", "valor": "en"}
    if re.search(r"(_|-|\b)ml(\b|_|-|\.)", s):
        return {"eje": "idioma_doc", "valor": "ml"}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poblacion", default=str(
        ROOT / "evals" / "s336_poblacion_v1.json"))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    pob = json.loads(Path(args.poblacion).read_text(encoding="utf-8"))
    out = args.out or str(ROOT / "evals" / "s336_elegibles_v1.json")

    filas_out, stats = [], {"alta": 0, "elegible_cat": 0, "cat_sin_fulltext": 0,
                            "capacidad_escrita": 0, "capacidad_a_packet": 0}
    with abierto(timeout=45.0) as c:
        for f in pob["detalle"]:
            v = f["llm"]
            if v.get("confianza") != "alta":
                continue
            stats["alta"] += 1
            docs = f["docs"]
            doc_cat = _doc_de(c, docs, v.get("categoria_cita"))
            fila = {"id": f["id"], "canonical": f["canonical"], "docs": docs,
                    "categoria": v.get("categoria"),
                    "categoria_cita": v.get("categoria_cita"),
                    "doc_cat": doc_cat, "elegible": bool(doc_cat),
                    "atributos": {}, "capacidad_packet": None}
            if not doc_cat:
                stats["cat_sin_fulltext"] += 1
                filas_out.append(fila)
                continue
            stats["elegible_cat"] += 1
            if v.get("tecnologia") and v.get("tecnologia") != "null":
                doc_t = _doc_de(c, docs, v.get("tecnologia_cita"))
                if doc_t:
                    fila["atributos"]["tecnologia"] = [{
                        "valor": v["tecnologia"],
                        "cita": str(v.get("tecnologia_cita"))[:200],
                        "doc": doc_t}]
            # ── capacidad: verificación + COMPLETITUD (Sol2-1) ──────────────
            entradas = []
            for lz in (v.get("lazos") or []):
                doc_l = _doc_de(c, docs, lz.get("cita"))
                if doc_l and isinstance(lz.get("max", lz.get("base")), int):
                    e = {"max": lz.get("max", lz.get("base")),
                         "cita": str(lz.get("cita"))[:200], "doc": doc_l}
                    if isinstance(lz.get("base"), int):
                        e["base"] = lz["base"]
                    al = _alcance_de(doc_l)
                    if al:
                        e["alcance"] = al
                    entradas.append(e)
            docs_con_mencion = {sf for sf in docs if _RX_CAP.search(_texto(c, sf))}
            docs_atribuidos = {e["doc"] for e in entradas}
            maxes = {e["max"] for e in entradas}
            if entradas:
                incompleto = bool(docs_con_mencion - docs_atribuidos)
                divergente = len(maxes) > 1
                if incompleto or divergente:
                    fila["capacidad_packet"] = {
                        "motivo": ("divergencia de max entre fuentes" if divergente
                                   else "docs con mención de capacidad sin entrada atribuida"),
                        "entradas": entradas,
                        "docs_con_mencion": sorted(docs_con_mencion),
                        "docs_atribuidos": sorted(docs_atribuidos)}
                    stats["capacidad_a_packet"] += 1
                else:
                    fila["atributos"]["lazos"] = entradas
                    stats["capacidad_escrita"] += 1
            elif docs_con_mencion and v.get("categoria") in ("central", "repetidor"):
                fila["capacidad_packet"] = {
                    "motivo": "capacidad mencionada en docs y NO extraída",
                    "docs_con_mencion": sorted(docs_con_mencion)}
                stats["capacidad_a_packet"] += 1
            filas_out.append(fila)

    recibo = {"que_es": ("s336 elegibles de escritura: alta + cita FULL-TEXT "
                         "atribuida a doc; capacidad solo COMPLETA y NO divergente"),
              "stats": stats,
              "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "detalle": filas_out}
    Path(out).write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"stats={stats} · recibo → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
