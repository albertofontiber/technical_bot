# -*- coding: utf-8 -*-
"""s318/#71 — SONDA v2 del frame legal_disclaimer: el CAMINO REAL, no el regex.

v1 aplicaba solo `_LEGAL_DISCLAIMER_RX` y vendía «frases que desaparecerían»
(Sol r16 C1: FALSO — el contrato exige cuantificador+compuesto+forma+
aplicabilidad antes del frame). v2 ejecuta `_universal_obligations` (la función
gateada real) por chunk con PREGUNTA-ORÁCULO de máxima aplicabilidad (los
tokens de la propia cláusula — patrón oráculo DEC-173): lo que sale con flag
OFF y no con ON es EXACTAMENTE lo que el frame quita en el mejor caso para
entrar. Invariante verificado: 0 obligaciones NO-legales cambiadas.

Denominador honesto (Sol M5/Fable F4): solo documentos ACTIVOS de `documents`.
Sección MIXTAS (Sol C2): removidas que además llevan deber operativo embebido
(instalar/usar/mantener/probar/conforme al manual) — a ojos de Alberto.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402
from src.rag import evidence_contract as ec  # noqa: E402
from src.rag.catalog import _fold  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

_OPERATIVO_RX = re.compile(
    r"instal|\buso\b|\busar\b|utiliza|manten|prob(ar|ada|ado)|verific"
    r"|conforme (al|a las?) (manual|instruccion)|puesta en marcha")


def _norm_doc(nombre: str) -> str:
    return re.sub(r"\.pdf$", "", (nombre or "").strip().lower())


def _activos(client) -> set[str]:
    fuera: set[str] = set()
    off = 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                       params={"select": "source_pdf_filename",
                               "status": "eq.active", "order": "id.asc",
                               "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        filas = r.json()
        fuera.update(_norm_doc(f.get("source_pdf_filename")) for f in filas)
        if len(filas) < 1000:
            return fuera
        off += 1000


censo = json.loads((ROOT / "evals" / "s318_disclaimer_census_v1.json")
                   .read_text(encoding="utf-8"))
docs_censo = list(censo["por_documento"].keys())

flag_original = os.environ.get("EC_LEGAL_DISCLAIMER_SKIP")
resultado: dict[str, dict] = {}
mixtas: list[dict] = []
invariante_roto: list[dict] = []
n_removidas = 0

with abierto(timeout=30.0) as client:
    activos = _activos(client)
    docs = [d for d in docs_censo if _norm_doc(d) in activos]
    for sf in docs:
        r = client.get(
            f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
            params={"select": "content,chunk_index",
                    "source_file": f"eq.{sf}",
                    "or": "(content.ilike.*responsab*,content.ilike.*liab*"
                          ",content.ilike.*in no event*)",
                    "limit": "10"})
        r.raise_for_status()
        for fila in r.json():
            contenido = fila.get("content") or ""
            card = {"source_file": sf, "page_number": None}
            views = [(0, card, contenido)]
            # pregunta-oráculo: tokens de contenido de las frases con RX
            oraculo: set[str] = set()
            for s, e in ec._sentence_spans(contenido):
                if ec._LEGAL_DISCLAIMER_RX.search(_fold(contenido[s:e])):
                    oraculo |= set(ec._content_tokens(contenido[s:e]))
            if not oraculo:
                continue
            os.environ["EC_LEGAL_DISCLAIMER_SKIP"] = ""
            off_obs = ec._universal_obligations(oraculo, views)
            os.environ["EC_LEGAL_DISCLAIMER_SKIP"] = "on"
            on_obs = ec._universal_obligations(oraculo, views)
            spans_on = {o["span_text"] for o in on_obs}
            for o in off_obs:
                span = o["span_text"]
                if span in spans_on:
                    continue
                es_legal = bool(ec._LEGAL_DISCLAIMER_RX.search(_fold(span)))
                registro = {"doc": sf, "chunk_index": fila.get("chunk_index"),
                            "aplicable_con_oraculo": o["applicable"],
                            "frase": span}
                if not es_legal:
                    invariante_roto.append(registro)
                    continue
                n_removidas += 1
                resultado.setdefault(sf, {"removidas": []})["removidas"].append(
                    {"frase": span, "aplicable": o["applicable"]})
                if _OPERATIVO_RX.search(_fold(span)):
                    mixtas.append(registro)

if flag_original is None:
    os.environ.pop("EC_LEGAL_DISCLAIMER_SKIP", None)
else:
    os.environ["EC_LEGAL_DISCLAIMER_SKIP"] = flag_original

out = {
    "que_es": ("Sonda v2 (r16): removidas REALES de _universal_obligations "
               "bajo pregunta-oráculo de máxima aplicabilidad, solo docs "
               "ACTIVOS. Flag OFF no cambia nada."),
    "docs_censo": len(docs_censo),
    "docs_censo_activos": len(docs),
    "docs_con_removidas": len(resultado),
    "obligaciones_legales_removidas": n_removidas,
    "invariante_no_legales_cambiadas": len(invariante_roto),
    "invariante_detalle": invariante_roto,
    "mixtas_con_deber_operativo": len(mixtas),
    "mixtas_detalle": mixtas,
    "por_documento": resultado,
}
path = ROOT / "evals" / "s318_disclaimer_probe_v2.json"
path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"censo {len(docs_censo)} docs · activos {len(docs)} · "
      f"con removidas {len(resultado)} · legales removidas {n_removidas} · "
      f"NO-legales cambiadas {len(invariante_roto)} · mixtas {len(mixtas)}")
print(f"recibo -> {path}")
