# -*- coding: utf-8 -*-
"""s324c — PLAN de los lotes §0.D (candidates → RETIRAR, 17) y §0.E (pm sucio, 3) del packet E1 tal como los
REVISÓ Alberto el 16-ago (notas en `s320_e1_packet_adjudicacion_v2.md` bajo cada fila). Solo lectura.

§0.D: los 17 ids del draft son ARTEFACTOS → no se crean (nada que escribir). Lo que Alberto añadió:
  · 4 documentos a retirar (ETDT312, ETDT314, MADT742, MNDT1202) — ya aplicados (`s324_retirar_docs.py --lote s324c`).
  · Manual-de-Usuario-S3-2 → «Modelo S/3-2»; Manual-de-Usuario-S3-IR-y-S-2-IR → «Modelos S/3-IR y S/2-IR» (Fidegas):
    ALTA de los 3 sensores (título verificado) + doc_map + retag del pm sucio «EL-11».
  · TG-Cuales-son-los-requisitos-del-PC → «TG es el software»: R2 sobre `notifier:tg` (candidate) → CONFIRMAR como
    software (nombrado como sujeto en la FAQ y en Tg-Honeywell_Tecnico), alias «TG-HONEYWELL», doc_map de la FAQ y de
    TG-Honeywell_Usuario/Introduccion → notifier:tg (sustituye a `unresolved:tg-honeywell`, candidate); retag pm «DE-80» → «TG».
    OJO: «TG» = 2 letras → el gate léxico (gold + tráfico real) decide.
  · MADT731_06 → HSSD-2 (Alberto, con URL notifier.es/hssd-2): doc_map → notifier:laserstar-hssd-2 (= Stratos HSSD-2);
    retag pm «MADT-731» → «LaserStar-HSSD-2».
  · MADT015_01 (¿FS2?), MNDT600 (¿SMART3 GD3/GD2?), MNDT701 (software Triple IR): el texto no nombra el modelo →
    PENDIENTES con dato (ver `preguntas_alberto`), sin escritura.
§0.E: «asd in rail…» → BAJA (aplicada) · «compatibilidad-entre-equipos-notifier-y-morley» → MANTENER (nada que escribir;
    su respuesta ya es servible por retrieval) · «d686 ema1224b4r_w ns4r» → Alberto: «aplica a EMA1224B4R/W»: ALTA
    `notifier:ema1224b4r-w` (título verificado) + doc_map + retag pm «EN-54-3» → «EMA1224B4R/W».
Salida: evals/s324c_lote_0de_plan_v1.json
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, norm_token
from scripts.s324_lib import doc, texto, n_token, ventana, cita_ok

ADDED_BY = "s324c-0de"
PROV = "s324c §0.D/§0.E revisados por Alberto 16-ago-2026 (notas en s320_e1_packet_adjudicacion_v2.md) — {detalle}"
P = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
DM = {r["source_file"].lower(): r for r in _read_jsonl(CATALOG_DIR / "doc_map.jsonl")}
plan = {"que_es": __doc__.strip().splitlines()[0], "utc": None, "doc_map_altas": [], "doc_map_modificaciones": [],
        "products_altas": [], "products_confirmar": [], "products_retirar": [], "aliases_quitar": [], "aliases_altas": [],
        "umbrellas_altas": [], "retags_db": [], "no_aplicar": [], "avisos": [], "preguntas_alberto": [],
        "adjudicados_por_alberto_para_el_gate": {}}


def entrada(d, ids, cita, detalle, verif, regla):
    return {"document_id": d["id"], "source_file": d["source_pdf_filename"],
            "entries": [{"id": i, "role": "primary", "scope": "doc", "provenance": PROV.format(detalle=detalle)} for i in ids],
            "reglas": [regla], "citas": [cita], "verificaciones": [verif]}


def main():
    with abierto(timeout=60.0) as c:
        # ── Fidegas S/3-2 · S/3-IR · S/2-IR (R4: título del manual) ──
        for pid, cm, dn in [("fidegas:s3-2", "S/3-2", "Manual-de-Usuario-S3-2"),
                            ("fidegas:s3-ir", "S/3-IR", "Manual-de-Usuario-S3-IR-y-S-2-IR"),
                            ("fidegas:s2-ir", "S/2-IR", "Manual-de-Usuario-S3-IR-y-S-2-IR")]:
            d = doc(c, dn); txt = texto(c, d["id"]); n = n_token(txt, cm); cita = ventana(txt, cm)
            if not n or pid in P:
                plan["no_aplicar"].append({"que": pid, "motivo": "sin token o ya existe"}); continue
            plan["products_altas"].append({"row": {"id": pid, "canonical_model": cm, "estado": "activo", "candidate": False, "vendido_bajo": ["Fidegas"],
                                                   "familia": "S/x sensores remotos", "added_by": ADDED_BY,
                                                   "provenance": PROV.format(detalle=f"Alberto §0.D: «Modelo(s) {cm}»; título verificado full-text en {dn} ({n} chunks)")},
                                           "doc": dn, "document_id": d["id"], "cita": cita, "n_token": n, "regla": "§0.D+R4"})
            plan["doc_map_altas"].append(entrada(d, [pid], cita, f"documento que sustenta el alta de {cm} (Alberto §0.D)", {"token_exacto": n}, "§0.D+R4"))
        for dn, prev, nuevo in [("Manual-de-Usuario-S3-2", "EL-11", "S/3-2"), ("Manual-de-Usuario-S3-IR-y-S-2-IR", "EL-11", "S/3-IR/S/2-IR")]:
            d = doc(c, dn)
            plan["retags_db"].append({"document_id": d["id"], "source_file": dn, "pm_prev": prev, "pm_nuevo": nuevo, "documents_pm_actual": d["product_model"],
                                      "motivo": "pm sucio EL-11 (fecha «el 11/2018») → modelo(s) del título (Alberto §0.D)"})
        # ── EMA1224B4R/W (§0.E, Alberto: «aplica a EMA1224B4R/W») ──
        d = doc(c, "d686 ema1224b4r_w ns4r"); txt = texto(c, d["id"]); cm = "EMA1224B4R/W"; n = n_token(txt, cm); cita = ventana(txt, cm)
        if n and "notifier:ema1224b4r-w" not in P:
            plan["products_altas"].append({"row": {"id": "notifier:ema1224b4r-w", "canonical_model": cm, "estado": "activo", "candidate": False, "vendido_bajo": [d["manufacturer"]],
                                                   "added_by": ADDED_BY, "provenance": PROV.format(detalle=f"Alberto §0.E: «aplica a EMA1224B4R/W» (sirena de pared KAC); título verificado en {d['source_pdf_filename']} ({n} chunks)")},
                                           "doc": d["source_pdf_filename"], "document_id": d["id"], "cita": cita, "n_token": n, "regla": "§0.E"})
            plan["doc_map_altas"].append(entrada(d, ["notifier:ema1224b4r-w"], cita, "documento que sustenta el alta (Alberto §0.E)", {"token_exacto": n}, "§0.E"))
            plan["retags_db"].append({"document_id": d["id"], "source_file": d["source_pdf_filename"], "pm_prev": "EN-54-3", "pm_nuevo": cm, "documents_pm_actual": d["product_model"],
                                      "motivo": "pm sucio EN-54-3 (norma) → modelo del título (Alberto §0.E)"})
        else:
            plan["no_aplicar"].append({"que": "notifier:ema1224b4r-w", "motivo": f"token n={n} o ya existe"})
        # ── TG = software (Alberto §0.D) — R2 sobre notifier:tg (candidate) ──
        faq = doc(c, "TG-Cuales-son-los-requisitos-del-PC-para-el-programa.pdf"); tf = texto(c, faq["id"])
        tec = doc(c, "Tg-Honeywell_Tecnico"); tt = texto(c, tec["id"])
        n_faq, n_tec = n_token(tf, "TG"), n_token(tt, "TG")
        cita_tg = ventana(tf, "TG")
        p = P.get("notifier:tg")
        if p and p.get("candidate") and n_faq and n_tec:
            plan["products_confirmar"].append({"id": "notifier:tg", "canonical_model": "TG", "doc": faq["source_pdf_filename"], "document_id": faq["id"], "n_token": n_faq, "cita": cita_tg,
                                               "provenance_add": PROV.format(detalle=f"Alberto §0.D: «TG es el software»; sujeto de la FAQ «TG - requisitos del PC» ({n_faq}) y de Tg-Honeywell_Tecnico ({n_tec} chunks); R2 (modelo/producto concreto de software)")})
            plan["clasificacion_confirmados"] = {"notifier:tg": {"categoria": "software", "cita": cita_tg, "provenance": "s324c Alberto §0.D: TG = software gráfico (TG-HONEYWELL)"}}
            plan["aliases_altas"].append({"alias": "TG-HONEYWELL", "id": "notifier:tg", "tipo": "nombre-largo", "added_by": ADDED_BY,
                                          "provenance": PROV.format(detalle="nombre completo del software en la FAQ y en los manuales TG-Honeywell_*; unresolved:tg-honeywell (candidate) queda como fila candidate sin efecto")})
            plan["doc_map_altas"].append(entrada(faq, ["notifier:tg"], cita_tg, "FAQ sobre el software TG (Alberto §0.D)", {"token_exacto": n_faq}, "§0.D+R2"))
            plan["retags_db"].append({"document_id": faq["id"], "source_file": faq["source_pdf_filename"], "pm_prev": "DE-80", "pm_nuevo": "TG", "documents_pm_actual": faq["product_model"],
                                      "motivo": "pm sucio DE-80 («de 80 …») → TG (Alberto §0.D)"})
            for sf in ("TG-Honeywell_Usuario", "Tg-Honeywell_Introduccion"):
                r = DM.get(sf.lower())
                if r:
                    ids = [e["id"] for e in r["entries"]]
                    nuevas = ["notifier:tg" if i == "unresolved:tg-honeywell" else i for i in ids]
                    if nuevas != ids:
                        plan["doc_map_modificaciones"].append({"document_id": r["document_id"], "source_file": r["source_file"], "entries_prev": ids, "entries_nuevas": nuevas,
                                                               "regla": "R2", "detalle": "unresolved:tg-honeywell (candidate) → notifier:tg (confirmado como software; alias TG-HONEYWELL)"})
        else:
            plan["no_aplicar"].append({"que": "notifier:tg", "motivo": f"no candidate o sin token (faq {n_faq}, tecnico {n_tec})"})
        # ── MADT731_06 → HSSD-2 (Alberto, URL) ──
        d = doc(c, "MADT731_06"); txt = texto(c, d["id"])
        plan["doc_map_altas"].append(entrada(d, ["notifier:laserstar-hssd-2"], ventana(txt, "AirSense") or "", "Alberto §0.D: «Pertenece al modelo HSSD-2» (mismo doc en notifier.es/…/category/hssd-2) — guía de aplicación de puntos de muestreo capilares AirSense; el texto no nombra el modelo: atestación por adjudicación explícita con URL", {"cita_full_text": None, "adjudicacion_explicita": True}, "§0.D+adjudicación"))
        plan["retags_db"].append({"document_id": d["id"], "source_file": "MADT731_06", "pm_prev": "MADT-731", "pm_nuevo": "LaserStar-HSSD-2", "documents_pm_actual": d["product_model"],
                                  "motivo": "pm = código del documento → modelo adjudicado por Alberto (HSSD-2 = LaserStar-HSSD-2 en catálogo)"})
        # ── preguntas con dato ──
        plan["preguntas_alberto"] = [
            {"doc": "MADT015_01", "tu_nota": "¿serie FS (FS2-1/2/4) por el esquema de bornes?", "dato": "el texto NO nombra el modelo (guía rápida de instalación de una central convencional: zonas, 230 V, detectores System Sensor, código 997-502). Sus hermanas YA están mapeadas: MADT015_02 → notifier:nfs8rel y MADT015_03 → notifier:nfs-2-8 ⇒ lo probable es NFS2-8, no FS2. FS2-1/2/4 no existen en catálogo (solo `notifier:fs-2` candidate).", "propuesta": "atestar MADT015_01 → notifier:nfs-2-8 si confirmas; si insistes en FS2, hace falta alta sin evidencia textual (no recomendable)."},
            {"doc": "MNDT600", "tu_nota": "detectores de gas SMART (Sensitron): Smart3 GD3 y SMART3 GD2 (butano) — ¿tenemos el documento?", "dato": "el texto es genérico («Notas generales para la calibración… de los detectores de gas», 16 chunks) y no nombra modelos; en el corpus NO aparece «SMART3 GD3/GD2» con esa grafía, pero SÍ la familia SMART 3 (SMART 3 EXPLOSIVOS/TOXICOS/3G ZONA 2, MNDT646 SMART3G) y en catálogo `notifier:smart3g-d3` (SMART3G-D3, confirmado; ¿= GD3?), sin GD2/D2.", "propuesta": "atestar MNDT600 a la FAMILIA SMART 3 (paraguas nuevo con los miembros SMART 3 CC/CD/CC-CD/3G/3G-C3/3G-D/3G-D3; 4 son candidates) si lo confirmas; y añadir «Smart3 GD3»→SMART3G-D3 como alias si me confirmas que son el mismo."},
            {"doc": "MNDT701.pdf", "tu_nota": "software para los detectores de llama Triple IR (IR3)", "dato": "«Guía de usuario — Software del detector de llamas Triple IR — SPECTRONIX (sharpEye)»; el software no tiene nombre propio en el texto y la familia SharpEye 20/20 (IR3) NO está en el catálogo (su fila spectrex:20-20i cayó por R6: fuente retirada).", "propuesta": "queda sin atestar hasta que exista el id de la familia SharpEye 20/20 (o me digas el modelo concreto)."},
        ]
    plan["utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
    out = ROOT / "evals/s324c_lote_0de_plan_v1.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(plan["resumen"], ensure_ascii=False))
    for a in plan["products_altas"]: print("  ALTA", a["row"]["id"], "| n", a["n_token"], "|", a["cita"][:80])
    for cf in plan["products_confirmar"]: print("  CONFIRMAR", cf["id"], "|", cf["cita"][:80])
    for x in plan["no_aplicar"]: print("  NO:", x)
    print("plan:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
