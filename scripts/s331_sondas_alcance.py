# -*- coding: utf-8 -*-
"""s331 — SONDAS de alcance para las dos decisiones que Alberto pidió MEDIR (20-ago).

No aplica nada: genera planes-sonda y los deja listos para el dry-run del writer
(`scripts/s324_lote_firmado_writer.py --plan <sonda>`), que es quien mide el radio de explosión.

  MNDT600 (doc genérico de calibración de detectores de gas — Sensitron/SMART):
    A  solo los SMART CONFIRMADOS (3 ids no-candidate)      → doc_map puro, sin tocar el detector
    B  familia SMART completa (promueve 8 candidates)       → confirmar = activar alias
    C  toda la gama de DETECTORES de gas de la casa          → B + sensores/detectores Sensitron-HLSI

  MNDT701 (software del detector Triple IR — SharpEye/Spectrex):
    D  solo la familia IR³ (S20/20MI, S20/20SI, 20/20I)     → 3 altas + doc_map de sus manuales
    E  serie 20/20 completa (9 modelos)                     → D + R/U/UB/L/LB/ML

Cada alta lleva su cita VERIFICADA full-text (token exacto con fronteras, contado sobre chunks_v2).

Uso:  python scripts/s331_sondas_alcance.py            # escribe evals/s331_sonda_{A..E}_plan_v1.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

# ── serie 20/20 SharpEye: modelo → (doc que lo documenta, tipo, es_ir3) ────────────────
SERIE_2020 = [
    ("S20/20MI", "MNDT696",     "Triple IR (IR³)",      True,  ["20/20MI"]),
    ("S20/20SI", "MNDT694",     "Triple IR (IR³)",      True,  ["20/20SI"]),
    ("20/20I",   "MNDT700 C",   "Triple IR (IR³)",      True,  []),
    ("20/20R",   "MNDT713",     "IR único espectro",    False, []),
    ("20/20U",   "MNDT710 B",   "UV",                   False, []),
    ("20/20UB",  "MNDT710 B",   "UV",                   False, []),
    ("20/20L",   "MNDT720",     "UV/IR",                False, []),
    ("20/20LB",  "MNDT720",     "UV/IR",                False, []),
    ("20/20ML",  "manual-spectrex-sharpeye-20-20ml-user-manual", "UV/IR Mini", False, []),
]
DOCMAP_EXTRA_2020 = [("MADT696_01", ["S20/20MI"])]      # hoja de configuración del mismo detector
SOFTWARE_2020 = ("MNDT701", "Triple IR")                 # el software → familia IR³

# ── gas: los tres alcances ────────────────────────────────────────────────────────────
SMART_CONFIRMADOS = ["notifier:smart3g-c3", "notifier:smart3g-d3", "sensitron:smart-2"]
SMART_CANDIDATES = ["notifier:smart-1", "notifier:smart-3-cc", "notifier:smart-3-cc-cd",
                    "notifier:smart-3-cd", "notifier:smart-3g", "notifier:smart3g-d",
                    "notifier:smart4", "sensitron:smart-2-twin"]
# Gama de DETECTORES/sensores de gas de la casa (Sensitron vía HLSI). Se EXCLUYEN a propósito las
# centrales y el software (MULTISCAN++S1, NFG-8/16REL, Securnet Plus, PL4/ST.PL4+: son centrales o
# unidades de control), porque el documento habla de la instalación y calibración del SENSOR.
GAS_DETECTORES_EXTRA = ["notifier:sentox-4", "notifier:sentox-idi+", "notifier:lisa-2",
                        "notifier:lisa-2-eex-d", "notifier:lisa-2-eex-na", "notifier:vgs-ad",
                        "notifier:vgs-du", "notifier:vgs-exp", "notifier:s264o2gp",
                        "notifier:s317amdp", "notifier:s613amfp"]
DOC_GAS = "MNDT600"


def _get(c, path, **params):
    r = c.get(f"{SB}/rest/v1/{path}", headers=HS, params=params)
    r.raise_for_status()
    return r.json()


def doc_por_nombre(c, prefijo: str) -> dict | None:
    rows = _get(c, "documents", select="id,document_family,product_model,manufacturer,status")
    cand = [d for d in rows if d["status"] == "active" and d["document_family"].startswith(prefijo)]
    return cand[0] if len(cand) == 1 else (cand[0] if cand else None)


def cita_token(c, document_id: str, token: str) -> tuple[int, str]:
    """Cuenta chunks con el token EXACTO (fronteras no alfanuméricas) y devuelve una cita."""
    rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])")
    chunks = _get(c, "chunks_v2", select="chunk_index,content", document_id=f"eq.{document_id}",
                  order="chunk_index")
    n, cita = 0, ""
    for ch in chunks:
        m = rx.search(ch["content"] or "")
        if m:
            n += 1
            if not cita:
                ini = max(0, m.start() - 90)
                cita = re.sub(r"\s+", " ", ch["content"][ini:m.end() + 90]).strip()
    return n, cita


def id_spectrex(modelo: str) -> str:
    return "spectrex:" + modelo.lower().replace("/", "-").replace(" ", "-")


def main() -> int:
    salidas = {}
    with abierto(timeout=60.0) as c:
        # ── D / E: altas de la serie 20/20 con cita verificada ──
        altas, aliases, docmap, sin_cita = [], [], [], []
        docs_cache: dict[str, dict] = {}
        for modelo, doc_pref, tipo, es_ir3, grafias_alias in SERIE_2020:
            d = docs_cache.get(doc_pref) or doc_por_nombre(c, doc_pref)
            if not d:
                sin_cita.append({"modelo": modelo, "motivo": f"documento {doc_pref} no encontrado"})
                continue
            docs_cache[doc_pref] = d
            n, cita = cita_token(c, d["id"], modelo)
            if not n:
                sin_cita.append({"modelo": modelo, "doc": doc_pref, "motivo": "0 chunks con el token exacto"})
                continue
            pid = id_spectrex(modelo)
            altas.append({
                "row": {"id": pid, "canonical_model": modelo, "estado": "activo", "candidate": False,
                        "vendido_bajo": ["Spectrex", "Notifier"], "added_by": "s331-sonda",
                        "provenance": f"s331 SONDA (medición para Alberto) — serie 20/20 SharpEye, {tipo}; "
                                      f"cita verificada full-text en {d['document_family']} ({n} chunks con el token exacto)"},
                "doc": d["document_family"], "document_id": d["id"], "cita": cita[:220], "n_token": n,
                "regla": "alta con cita propia (serie 20/20)", "tipo": tipo, "ir3": es_ir3})
            docmap.append({"document_id": d["id"], "source_file": d["document_family"],
                           "entries": [{"id": pid, "role": "primary", "scope": "doc",
                                        "provenance": f"s331 SONDA — manual del propio modelo ({n} chunks con el token)"}]})
            for g in grafias_alias:
                ng, _ = cita_token(c, d["id"], g)
                otro = doc_por_nombre(c, "MADT696_01") if g == "20/20MI" else None
                n_otro = cita_token(c, otro["id"], g)[0] if otro else 0
                aliases.append({"alias": g, "id": pid, "tipo": "variante-tipografica",
                                "added_by": "s331-sonda",
                                "provenance": f"s331 SONDA — grafía sin la S atestada en el corpus "
                                              f"({ng} chunks en {d['document_family']}"
                                              + (f", {n_otro} en {otro['document_family']}" if otro else "") + ")"})
        # doc_map extra (hoja de configuración) + el software → familia IR³
        for pref, modelos in DOCMAP_EXTRA_2020:
            d = doc_por_nombre(c, pref)
            if d:
                docmap.append({"document_id": d["id"], "source_file": d["document_family"],
                               "entries": [{"id": id_spectrex(m), "role": "primary", "scope": "doc",
                                            "provenance": f"s331 SONDA — hoja de configuración del detector {m}"}
                                           for m in modelos]})
        ir3 = [a["row"]["id"] for a in altas if a["ir3"]]
        d_sw = doc_por_nombre(c, SOFTWARE_2020[0])
        docmap_sw = []
        if d_sw:
            docmap_sw.append({"document_id": d_sw["id"], "source_file": d_sw["document_family"],
                              "entries": [{"id": pid, "role": "primary", "scope": "doc",
                                           "provenance": "s331 SONDA — guía del software del detector de llamas Triple IR "
                                                         "(«El software permite comunicarse con hasta 64 detectores IR3»); "
                                                         "la familia IR³ del corpus son estos 3 modelos"}
                                          for pid in ir3]})

        ids_ir3 = set(ir3)
        base = {"products_confirmar": [], "products_retirar": [], "aliases_quitar": [],
                "umbrellas_altas": [], "doc_map_modificaciones": [], "retags_db": []}
        salidas["D"] = {**base,
                        "que_es": "s331 SONDA D — MNDT701: SOLO la familia IR³ (S20/20MI, S20/20SI, 20/20I). "
                                  "Altas con cita propia + doc_map de sus manuales + el software a la familia. NO se aplica.",
                        "products_altas": [a for a in altas if a["ir3"]],
                        "aliases_altas": [x for x in aliases if x["id"] in ids_ir3],
                        "doc_map_altas": [r for r in docmap if all(e["id"] in ids_ir3 for e in r["entries"])] + docmap_sw}
        salidas["E"] = {**base,
                        "que_es": "s331 SONDA E — MNDT701: serie 20/20 COMPLETA (9 modelos). "
                                  "Altas con cita propia + doc_map de sus manuales + el software a la familia IR³. NO se aplica.",
                        "products_altas": altas, "aliases_altas": aliases,
                        "doc_map_altas": docmap + docmap_sw}

        # ── A / B / C: doc_map de MNDT600 a la gama de gas ──
        dgas = doc_por_nombre(c, DOC_GAS)
        cat = json.loads("[]")
        prods = {}
        for line in (ROOT / "data/catalog/products.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                prods[r["id"]] = r

        def fila_docmap(ids: list[str], nota: str) -> list[dict]:
            return [{"document_id": dgas["id"], "source_file": dgas["document_family"],
                     "entries": [{"id": i, "role": "primary", "scope": "doc",
                                  "provenance": f"s331 SONDA — {nota}; el doc imprime la familia en su contenido "
                                                "(portada: «smart GASDETECTOR»/«sensitron») y las células «S1096/2096… "
                                                "S1097.2097…»; adjudicación de Alberto: «aplica a los detectores de gas smart (sensitron)»"}
                                 for i in ids]}]

        def confirmar(ids: list[str]) -> list[dict]:
            out = []
            for i in ids:
                p = prods.get(i)
                if not p or not p.get("candidate"):
                    continue
                out.append({"id": i, "canonical_model": p["canonical_model"], "doc": DOC_GAS,
                            "document_id": dgas["id"], "n_token": 0, "cita": "(sonda: no se verifica cita aquí)",
                            "provenance_add": "s331 SONDA — promoción medida para la decisión de alcance de Alberto (NO aplicada)"})
            return out

        salidas["A"] = {**base, "products_altas": [], "aliases_altas": [],
                        "que_es": "s331 SONDA A — MNDT600 → SOLO los SMART ya confirmados (3 ids no-candidate). "
                                  "doc_map puro: no toca productos ni alias. NO se aplica.",
                        "doc_map_altas": fila_docmap(SMART_CONFIRMADOS, "alcance A: SMART confirmados")}
        idsB = SMART_CONFIRMADOS + SMART_CANDIDATES
        salidas["B"] = {**base, "products_altas": [], "aliases_altas": [],
                        "products_confirmar": confirmar(SMART_CANDIDATES),
                        "que_es": "s331 SONDA B — MNDT600 → familia SMART COMPLETA (11 ids; promueve 8 candidates). NO se aplica.",
                        "doc_map_altas": fila_docmap(idsB, "alcance B: familia SMART completa")}
        idsC = idsB + GAS_DETECTORES_EXTRA
        salidas["C"] = {**base, "products_altas": [], "aliases_altas": [],
                        "products_confirmar": confirmar(SMART_CANDIDATES + GAS_DETECTORES_EXTRA),
                        "que_es": "s331 SONDA C — MNDT600 → toda la gama de DETECTORES de gas de la casa "
                                  "(SMART + SENTOX/LISA/VGS/S264/S317/S613). Excluye centrales y software a propósito. NO se aplica.",
                        "doc_map_altas": fila_docmap(idsC, "alcance C: gama de detectores de gas")}

    for k, plan in salidas.items():
        plan["utc"] = "20260820T000000Z"
        plan["no_aplicar"] = [{"tema": "TODO este plan", "estado": "es una SONDA de medición; la decisión de alcance es de Alberto"}]
        out = ROOT / "evals" / f"s331_sonda_{k}_plan_v1.json"
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{k}: altas {len(plan['products_altas'])} · confirmar {len(plan['products_confirmar'])} · "
              f"alias {len(plan.get('aliases_altas', []))} · doc_map {len(plan['doc_map_altas'])} → {out.name}")
    if sin_cita:
        print("SIN CITA (no entran):", json.dumps(sin_cita, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
