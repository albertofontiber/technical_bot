# -*- coding: utf-8 -*-
"""s324b — PLAN del lote §0.C (E1: «candidates → ALTA», 32 filas del draft) tal como lo REVISÓ Alberto
el 16-ago (aceptado salvo sus 10 notas, consolidadas en `s320_e1_packet_adjudicacion_v2.md`). Solo
lectura: cada alta se verifica contra el TEXTO COMPLETO del documento (token exacto + cita verbatim);
lo que no verifica cae a `no_aplicar`.

Notas de Alberto incorporadas:
  · `aritech:2x-a` → NO producto: PARAGUAS «2X-A» (familia; miembros por regla) — adjudicado 2×
    (s323 437ee3f + 16-ago «aplica a todos los modelos de la serie 2x-A»); el negativo sintético
    «2 x a» del gate queda declarado; medido en tráfico real (query_logs): 0 disparos.
  · `morley:dxc-connexion` → NO producto: la FAQ → doc_map dxc1/dxc2/dxc4 (familia; paraguas DXc gt).
  · `kidde:ke-dm3110r-kit` duplicado en el draft → una sola alta.
  · `morley:vision-supra` (hoja de tarjetas de idiomas) → BAJA del documento (Alberto confirma) → sin alta.
  · `notifier:clss-configuration-tool` (doc PT ya retirado) → SOFTWARE, alta desde el doc ES si verifica.
  · `notifier:id2net` desde MADT190P_01_C (PT) → BAJA del PT; alta como SOFTWARE desde MADT190_01 (ES).
  · Spectrex: canonical `S40/40M`, `S40/40R`, `S40/40U`, `S40/40UB` (con la S) + alias `40/40x`.
Salida: evals/s324b_lote_0c_plan_v1.json
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, norm_token
from scripts.s324_lib import doc, texto, n_token, ventana, cita_ok, consultas_reales

ADDED_BY = "s324b-0c"
PROV = "s324b §0.C revisado por Alberto 16-ago-2026 (aceptado salvo notas consolidadas en s320_e1_packet_adjudicacion_v2.md) — {detalle}"
P = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
U = {u["termino"]: u for u in _read_jsonl(CATALOG_DIR / "umbrellas.jsonl")}
CANON = {}
for _pid, _p in P.items():
    CANON.setdefault(norm_token(_p.get("canonical_model") or ""), _pid)


def consumible(pid):
    p = P.get(pid); return bool(p) and p.get("estado") == "activo" and not p.get("candidate")


def cat_de(pid):
    return ((P.get(pid) or {}).get("clasificacion") or {}).get("categoria")


X2A = sorted(pid for pid in P if pid.startswith("kidde:2x-a") and consumible(pid) and cat_de(pid) in {"central", "repetidor"})
DXC = ["morley:dxc1", "morley:dxc2", "morley:dxc4"]

# filas del draft: (id_draft, canonical a escribir, doc, notas) — None en canonical = seguir el draft
OVERRIDES = {
    "aritech:2x-a": ("PARAGUAS", None),
    "morley:dxc-connexion": ("DOCMAP_FAMILIA", DXC),
    "morley:vision-supra": ("BAJA_DOC", "30012012  TARJETAS IDIOMAS VISION SUPRA rev A"),
    "spectrex:40-40m": ("RENOMBRAR", [("spectrex:s40-40m", "S40/40M", ["40/40M"])]),
    "spectrex:40-40r": ("RENOMBRAR", [("spectrex:s40-40r", "S40/40R", ["40/40R"])]),
    "spectrex:40-40u": ("RENOMBRAR", [("spectrex:s40-40u", "S40/40U", ["40/40U"]), ("spectrex:s40-40ub", "S40/40UB", ["40/40UB"])]),
    # la ficha (D 1147-1 BRH) dice NFXI-BSF-WCH; el corpus (AM-8200/8100/8200N/G, 997-669) escribe NFXI-BSF-WC (5+ docs) → grafía verificada
    "notifier:nfxi-bsf-wch": ("RENOMBRAR", [("notifier:nfxi-bsf-wc", "NFXI-BSF-WC", [])]),
}
SOFTWARE = {"notifier:id2net", "notifier:clss-configuration-tool"}
DOC_SUSTITUTO = {"4188-1124-PT issue 4_01-2026_To.pdf": "4188-1124-ES issue 6_01-2026_To",   # PT retirado → ES
                 "MADT190P_01_C": "MADT190_01",                                                # PT → baja; ES sustenta
                 "D 1147-1 BRH Notifier": "AM-8200 Manual Instalacion"}                        # la ficha dice NFXI-BSF-WCH pero el texto no lo nombra; sí la tabla de absorciones del AM-8200
SIN_DOC_MAP = {"notifier:nfxi-bsf-wch"}  # (clave = id del draft)   # sustentado por una tabla de dispositivos de un manual de central: alta sí, doc_map no (el manual no es SOBRE la base)

plan = {"que_es": __doc__.strip().splitlines()[0], "utc": None, "doc_map_altas": [], "doc_map_modificaciones": [],
        "products_altas": [], "products_confirmar": [], "products_retirar": [], "aliases_quitar": [], "aliases_altas": [],
        "umbrellas_altas": [], "retags_db": [], "bajas_documentos": [], "no_aplicar": [], "avisos": [],
        "adjudicados_por_alberto_para_el_gate": {}}


def entrada(d, ids, cita, detalle, verif):
    return {"document_id": d["id"], "source_file": d["source_pdf_filename"],
            "entries": [{"id": i, "role": "primary", "scope": "doc", "provenance": PROV.format(detalle=detalle)} for i in ids],
            "reglas": ["§0.C"], "citas": [cita], "verificaciones": [verif]}


def main():
    tri = json.loads((ROOT / "evals/s322g_e1_candidatos_triage_v1.json").read_text(encoding="utf-8"))
    filas = tri["seccion_0a_alta_en_bloque"]
    creados = {}
    with abierto(timeout=60.0) as c:
        for f in filas:
            pid, cm, dn = f["id"], f["canonical_model"], f["documento"]["source_pdf_filename"]
            mfr, llm = f["documento"]["manufacturer"], f["llm"] or {}
            ov = OVERRIDES.get(pid)
            if ov and ov[0] == "PARAGUAS":
                continue   # se añade abajo
            if ov and ov[0] == "DOCMAP_FAMILIA":
                d = doc(c, dn); txt = texto(c, d["id"])
                cita = llm.get("cita") or ""
                plan["doc_map_altas"].append(entrada(d, ov[1], cita, "Alberto: «aquí aplicará a todos los modelos de la familia dxc-connexion» → FAQ atesta a la familia DXc (serie × central), no se crea producto",
                                                     {"cita_full_text": cita_ok(txt, cita), "tokens_en_doc": {i: n_token(txt, P[i]["canonical_model"]) for i in ov[1]}}))
                continue
            if ov and ov[0] == "BAJA_DOC":
                plan["bajas_documentos"].append({"doc": ov[1], "motivo": "Alberto (16-ago): «baja, confirmo» — hoja de tarjetas de idiomas Vision Supra (rev A)", "sin_alta": pid})
                continue
            targets = ov[1] if (ov and ov[0] == "RENOMBRAR") else [(pid, cm, [])]
            dn_real = DOC_SUSTITUTO.get(dn, dn)
            if dn_real != dn:
                plan["avisos"].append({"que": pid, "aviso": f"doc del draft {dn!r} es PT retirado/a retirar → se sustenta en el ES {dn_real!r}"})
            d = doc(c, dn_real)
            if not d or d["status"] != "active":
                plan["no_aplicar"].append({"que": pid, "motivo": f"doc {dn_real!r} no localizado o no activo"}); continue
            txt = texto(c, d["id"])
            for tid, tcm, alias in targets:
                n = n_token(txt, tcm); cita = ventana(txt, tcm)
                if n == 0 or not cita:
                    plan["no_aplicar"].append({"que": tid, "motivo": f"{tcm!r} NO aparece como token exacto en {dn_real!r} (sin cita propia no hay alta)"}); continue
                existente = CANON.get(norm_token(tcm)) or (tid if tid in P else None) or creados.get(norm_token(tcm))
                if existente:
                    pe = P.get(existente)
                    if pe and pe.get("estado") == "activo" and pe.get("candidate"):
                        plan["products_confirmar"].append({"id": existente, "canonical_model": pe["canonical_model"], "doc": d["source_pdf_filename"], "document_id": d["id"], "n_token": n, "cita": cita,
                                                           "provenance_add": PROV.format(detalle=f"nombrado como sujeto en {d['source_pdf_filename']} ({n} chunks); cita: «{cita}»")})
                    plan["doc_map_altas"].append(entrada(d, [existente], cita, f"documento que nombra {tcm} ({n} chunks); id existente", {"token_exacto": n}))
                    continue
                marca = ["Kidde Commercial"] if ("KIDDE COMMERCIAL" in txt.upper() and mfr in ("Kidde", "Aritech")) else [mfr]
                row = {"id": tid, "canonical_model": tcm, "estado": "activo", "candidate": False, "vendido_bajo": marca,
                       "added_by": ADDED_BY, "provenance": PROV.format(detalle=f"cita verificada full-text en {d['source_pdf_filename']} ({n} chunks con el token)")}
                if pid in SOFTWARE:
                    row["clasificacion"] = {"categoria": "software", "cita": cita, "provenance": "s324b Alberto 16-ago: «no es un modelo, es un software»; precedente MK-VSN/MK-ZX/MK50/MKDX, OPC-RP1r"}
                plan["products_altas"].append({"row": row, "doc": d["source_pdf_filename"], "document_id": d["id"], "cita": cita, "n_token": n, "regla": "§0.C"})
                creados[norm_token(tcm)] = tid
                for a in alias:
                    plan["aliases_altas"].append({"alias": a, "id": tid, "tipo": "variante-tipografica", "added_by": ADDED_BY,
                                                  "provenance": PROV.format(detalle=f"grafía sin la S usada en las etiquetas del corpus y en los golds «SharpEye 40/40»; canonical con S por Alberto")})
                if pid not in SIN_DOC_MAP:
                    plan["doc_map_altas"].append(entrada(d, [tid], cita, f"documento que sustenta el alta de {tcm}", {"token_exacto": n}))
                else:
                    plan["avisos"].append({"que": tid, "aviso": f"alta sustentada por la tabla de dispositivos de {d['source_pdf_filename']!r} (su propio doc, la ficha BRH, no lo nombra en el texto): sin doc_map"})
        # paraguas 2X-A (adjudicado 2×) — con la medida en tráfico real
        reales = consultas_reales(c)
        import re as _re
        core = _re.compile(r"(?<![a-z0-9])2[-\s/.+]*x[-\s/.+]*a(?![a-z0-9])", _re.I)
        hits = [q for q in reales if core.search(q)]
        plan["umbrellas_altas"].append({"termino": "2X-A", "tipo": "familia", "ids": X2A, "divergent": True, "candidate": False, "added_by": ADDED_BY,
                                        "provenance": "Alberto s323 (437ee3f: alta de la FAMILIA 2X-A) + 16-ago («aplica a todos los modelos de la serie 2x-A»); miembros por regla prefijo 2X-A × {central, repetidor}; tráfico real: %d/%d consultas disparan el core «2·x·a»" % (len(hits), len(reales))})
        plan["adjudicados_por_alberto_para_el_gate"]["2X-A"] = {"motivo": "adjudicado 2 veces por Alberto; el negativo sintético «2 x a» del gate se declara como aviso; tráfico real %d/%d disparos" % (len(hits), len(reales)), "hits_reales": hits[:10]}
        # baja del PT MADT190P_01_C (hermano ES MADT190_01)
        plan["bajas_documentos"].append({"doc": "MADT190P_01_C", "motivo": "Alberto (16-ago): «Doc en PT, eliminaría porque MADT190_01 es la versión en español»; misma clase que los 6 PT retirados", "hermano_es": "MADT190_01"})
    # merge doc_map por document_id
    fusion = {}
    for e in plan["doc_map_altas"]:
        f = fusion.setdefault(e["document_id"], {"document_id": e["document_id"], "source_file": e["source_file"], "entries": [], "reglas": [], "citas": [], "verificaciones": []})
        vistos = {x["id"] for x in f["entries"]}
        f["entries"] += [x for x in e["entries"] if x["id"] not in vistos and not vistos.add(x["id"])]
        f["reglas"] += e["reglas"]; f["citas"] += e["citas"]; f["verificaciones"] += e["verificaciones"]
    plan["doc_map_altas"] = list(fusion.values())
    plan["utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
    out = ROOT / "evals/s324b_lote_0c_plan_v1.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(plan["resumen"], ensure_ascii=False))
    for a in plan["products_altas"]:
        print("  ALTA", a["row"]["id"], "|", a["row"]["canonical_model"], "| n", a["n_token"], "|", a["doc"][:40], "|", a["cita"][:70])
    for x in plan["no_aplicar"]: print("  NO:", x)
    for x in plan["avisos"]: print("  AVISO:", x)
    print("  paraguas 2X-A:", len(X2A), "ids ·", plan["adjudicados_por_alberto_para_el_gate"]["2X-A"]["motivo"])
    print("plan:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
