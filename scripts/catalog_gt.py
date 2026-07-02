#!/usr/bin/env python3
"""catalog_gt.py — GROUND-TRUTHS adjudicados del catálogo canónico (nivel-1) + brand_map.

Concentra TODO el gt que consume el loader bulk (s91_f1_bulk.py): la transcripción FIEL de
las memorias/adjudicaciones de Alberto. Cada bloque cita su fuente. La lección del dúo s90
(H5: gt mal transcrito) manda: transcribir la fuente, no interpretarla.

Fuentes:
- Morley ZX/RP1r: memory/reference_morley_zx_rp1r.md + QA s90 (P1-P8, packet adjudicado)
- FAAST: memory/reference_faast.md + backfill s80 (DEC-062, D3 pragmático manufacturer=Notifier)
- CAD-150: memory/reference_detnov_cad150.md (familia por nº de lazos; CAD-150R DISTINTO)
"""
from __future__ import annotations

GT78 = "gt-s78-morley (memory/reference_morley_zx_rp1r.md)"
GT86 = "gt-s86-hp011 (DEC-074b, adjudicación Alberto)"
GT90 = "gt-s90-alberto-qa (adjudicación del packet s90_f1a_qa_propuesta)"
GTFAAST = "gt-faast (memory/reference_faast.md + backfill s80/DEC-062)"
GTCAD = "gt-detnov-cad150 (memory/reference_detnov_cad150.md, ground-truth Alberto)"

# ───────────────────────── brand_map: forma-en-doc → namespace ─────────────────────────
# tier: 'mecanico' (tipográfico, sin juicio) · 'adjudicado' (gt/decisión previa) ·
#       'candidate' (juicio pendiente → los docs cargan con productos candidate)
# Los GRUPO_BRANDS no mapean directo: se resuelven por CONTEXTO (productos del doc) o quedan
# 'unresolved' (todo candidate).
BRAND_MAP: dict[str, tuple[str, str]] = {
    # notifier
    "Notifier": ("notifier", "mecanico"), "NOTIFIER": ("notifier", "mecanico"),
    "Notifier by Honeywell": ("notifier", "mecanico"),
    "Notifier (by Honeywell)": ("notifier", "mecanico"),
    "Pearl": ("notifier", "adjudicado"),        # central Notifier (golds cat001/cat005)
    "Mini Vista": ("notifier", "candidate"),    # panel Notifier probable — QA
    # morley
    "Morley": ("morley", "mecanico"), "Morley IAS": ("morley", "mecanico"),
    "Morley-IAS": ("morley", "mecanico"), "MORLEY-IAS": ("morley", "mecanico"),
    "MorleyIAS": ("morley", "mecanico"),
    "Morley IAS (by Honeywell)": ("morley", "mecanico"),
    "Morley IAS Fire Systems": ("morley", "mecanico"),
    "Morley IAS Fire Systems by Honeywell": ("morley", "mecanico"),
    "Morley IAS by Honeywell": ("morley", "mecanico"),
    "Morley-IAS by Honeywell": ("morley", "mecanico"),
    "Vision": ("morley", "adjudicado"), "VISION": ("morley", "adjudicado"),
    "vision": ("morley", "adjudicado"),         # la serie VSN/Vision es de Morley (gt slice)
    "Connexion": ("morley", "adjudicado"),      # la serie DXc/Connexion es de Morley (QA s90 P5)
    # kidde / aritech / edwards (firesecurityproducts, DEC-035)
    "Kidde": ("kidde", "mecanico"), "Kidde Commercial": ("kidde", "mecanico"),
    "Kidde Global Solutions": ("kidde", "mecanico"),
    "Aritech": ("aritech", "mecanico"), "Edwards": ("edwards", "mecanico"),
    # xtralis (VESDA/ICAM; AirSense=Stratos adquirida por Xtralis → candidate)
    "Xtralis": ("xtralis", "mecanico"), "VESDA": ("xtralis", "mecanico"),
    "VESDA by Xtralis": ("xtralis", "mecanico"), "VESDA-E (Xtralis)": ("xtralis", "mecanico"),
    "Xtralis VESDA": ("xtralis", "mecanico"), "ICAM by Xtralis": ("xtralis", "mecanico"),
    "Xtralis / FAAST FLEX": ("xtralis", "mecanico"),
    "AirSense": ("xtralis", "candidate"),
    # system sensor / securiton / detnov
    "System Sensor": ("systemsensor", "mecanico"),
    "Securiton": ("securiton", "mecanico"),     # marca APARTE, Detnov la vende (s78)
    "Detnov": ("detnov", "mecanico"), "detnov": ("detnov", "mecanico"),
    "edelnov": ("detnov", "candidate"),         # typo probable — QA
    # resto de marcas
    "Argus Security": ("argus", "mecanico"), "KAC": ("kac", "mecanico"),
    "LDA": ("lda", "mecanico"), "LDA audioTech": ("lda", "mecanico"),
    "Sensitron": ("sensitron", "mecanico"), "FIDEGAS": ("fidegas", "mecanico"),
    "Spectrex": ("spectrex", "mecanico"), "Spectrex (SharpEye)": ("spectrex", "mecanico"),
    "Spectrex SharpEye": ("spectrex", "mecanico"),
    "Pepperl+Fuchs": ("pepperl-fuchs", "mecanico"),
    "Menvier CSA": ("menvier", "mecanico"),
    "Firebeam": ("firebeam", "mecanico"), "thefirebeam": ("firebeam", "mecanico"),
    "PATROL": ("patrol", "mecanico"), "PYRA": ("pyra", "mecanico"),
    "Hosiden Besson": ("hosiden", "mecanico"),
    "STI (Safety Technology International)": ("sti", "mecanico"),
    "Signaline": ("signaline", "mecanico"), "SENSE-WARE": ("sense-ware", "mecanico"),
    "Testifire": ("testifire", "mecanico"), "Testifire (detectortesters)": ("testifire", "mecanico"),
    "Venitem": ("venitem", "mecanico"), "e2S (European Safety Systems Ltd.)": ("e2s", "mecanico"),
    "Pfannenberg": ("pfannenberg", "mecanico"),
    "Zellweger Analytics / Zareba": ("zareba", "candidate"),
    "FAAST": ("notifier", "candidate"),         # FAAST=familia multi-marca; docs sueltos → QA
    # ruido de extracción → candidate/QA
    "Nuvathings": ("unresolved", "candidate"), "M.ZONA": ("unresolved", "candidate"),
    "fvt": ("unresolved", "candidate"),
}
# Marcas de GRUPO/distribuidor → resolución CONTEXTUAL (por los productos del doc)
GRUPO_BRANDS = {"Honeywell", "Honeywell Life Safety Iberia", "unknown", "(vacio)", "",
                "Notifier / Morley", "Honeywell Life Safety Iberia / Morley-IAS by Honeywell",
                "Morley IAS (by Honeywell)"}

# Tokens ADJUDICADOS no-producto/ambiguos (QA s90 P2/P3/P4/P7) — norm_token → razón
GT90_BLOCKED = {
    "ma100": "P4: MIE-MA-100 es código de MANUAL de la HRZ2-8",
    "miema100": "P4: código de manual de la HRZ2-8",
    "dx2": "P2: abreviatura de DX2e (alias gt)",
    "brh": "P7: ambiguo cross-brand (Morley MI-BRH-PC-I vs Notifier NFXI-BSF-WCH)",
    "bgl": "P7: ambiguo cross-brand (Morley MI-BGL-PC-I vs Notifier NFXI-BF-WCS)",
    "exp": "P3: ambiguo (Mod.EXP / Mod.EXP-060R / MIW-EXP)",
    "faastlt": "P7: FAAST LT es FAMILIA multi-marca (reference_faast)",
    "dxconnexion": "P5: término-familia → umbrella DXc",
    "dxcconnexion": "P5: término-familia → umbrella DXc",
    "faast": "familia multi-marca (FLEX/XM/XT/LT) → umbrella candidate",
}
GT90_IGNORED_DOCS = {"MIEMU520P": "P8: manual PT — no contemplar (docrel en F1)"}


def _p(i, cm, vb, prov, **kw):
    return {"id": i, "canonical_model": cm, "vendido_bajo": vb, "estado": "activo",
            "provenance": prov, "added_by": "f1-gt", **kw}


def gt_products() -> list[dict]:
    return [
        # ── Morley ZX (gt s78 + QA s90) ──
        _p("morley:zx1e", "ZX1e", ["Morley-IAS"], GT78, familia="ZXe"),
        _p("morley:zx2e", "ZX2e", ["Morley-IAS"], GT78, familia="ZXe"),
        _p("morley:zx5e", "ZX5e", ["Morley-IAS"], GT78, familia="ZXe"),
        _p("morley:zx1se", "ZX1Se", ["Morley-IAS"], GT78, familia="ZXSe"),
        _p("morley:zx2se", "ZX2Se", ["Morley-IAS"], GT78, familia="ZXSe"),
        _p("morley:zx5se", "ZX5Se", ["Morley-IAS"], GT78, familia="ZXSe"),
        _p("morley:zx10se", "ZX10Se", ["Morley-IAS"], GT78 + " (2×ZX5Se en red)", familia="ZXSe"),
        _p("morley:zxae", "ZXAE", ["Morley-IAS"], GT78),
        _p("morley:zxee", "ZXEE", ["Morley-IAS"], GT78),
        _p("morley:zxhe", "ZXHE", ["Morley-IAS"], GT78),
        _p("morley:zxce", "ZXCE", ["Morley-IAS"], GT78),
        _p("morley:mk-zx", "MK-ZX", ["Morley-IAS"], GT78, categoria="software de configuración"),
        _p("morley:zx50", "ZX50", ["Morley-IAS"], GT78),
        _p("morley:zxr50a", "ZXR50A", ["Morley-IAS"], GT78, categoria="repetidor (con teclado)"),
        _p("morley:zxr50p", "ZXR50P", ["Morley-IAS"], GT78, categoria="repetidor (sin teclado)"),
        _p("morley:zxr5b", "ZXR5B", ["Morley-IAS"], GT78, categoria="impresora de lazo periférico"),
        _p("morley:zxr4b", "ZXR4B", ["Morley-IAS"], GT78, categoria="impresora de lazo periférico"),
        # RP1r ×4 (gt s78)
        _p("notifier:rp1r-supra", "RP1r-Supra", ["Notifier", "Morley-IAS (VSN-RP1r+)", "ESS"],
           GT78 + " + fix s78 (312ch Morley→Notifier)"),
        _p("notifier:rp1r", "RP1r", ["Notifier"], GT78 + " — central de EXTINCIÓN ≠ Supra (MNDT102*)"),
        _p("morley:vsn-rp1r", "VSN-RP1r", ["Morley-IAS"], GT78 + " — extinción Morley (MIEMN570*)"),
        _p("notifier:opc-rp1r", "OPC-RP1r", ["Notifier"], GT78 + " — SOFTWARE/pasarela SCADA (MN-DT-959)"),
        # QA s90 (P3/P4/P7)
        _p("morley:hrz2-8", "HRZ2-8", ["Morley-IAS"], GT90 + " P4 (MIE-MI-100; los MA-100 son sus manuales)",
           categoria="central convencional 8 zonas"),
        _p("morley:mod-exp-060r", "Mod.EXP-060R", ["Morley-IAS"], GT90 + " P3 (MIE-MP-530 p61)",
           categoria="impresora de lazo periférico"),
        _p("morley:mi-dcmo", "MI-DCMO", ["Morley-IAS"], GT90 + " P7 (I56-4407, MIE-MI-230)",
           categoria="módulo de salida de control (serie ZX)"),
        # ── FAAST LT-200 (gt s78/s80: OEM System Sensor; manufacturer=Notifier pragmático D3;
        #    los standalone/addressable APLICAN a Morley Y Notifier — transcripción FIEL de
        #    reference_faast.md L13-16, con los sufijos -HS que la 1ª transcripción perdió) ──
        # standalone/autónomos (doc I56-6574):
        _p("notifier:fl0111e-hs", "FL0111E-HS", ["Notifier", "Morley-IAS"], GTFAAST + " — standalone (I56-6574)",
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        _p("notifier:fl0112e-hs", "FL0112E-HS", ["Notifier", "Morley-IAS"], GTFAAST,
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        _p("notifier:fl0122e-hs", "FL0122E-HS", ["Notifier", "Morley-IAS"], GTFAAST,
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        # addressable/direccionables (doc I56-6575, EN/ES mismo doc):
        _p("notifier:fl2011ei-hs", "FL2011EI-HS", ["Notifier", "Morley-IAS"], GTFAAST + " — addressable (I56-6575)",
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        _p("notifier:fl2012ei-hs", "FL2012EI-HS", ["Notifier", "Morley-IAS"], GTFAAST,
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        _p("notifier:fl2022ei-hs", "FL2022EI-HS", ["Notifier", "Morley-IAS"], GTFAAST,
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        # addressable marca-Notifier EXCLUSIVA (docs I56-6577 + I56-3947):
        _p("notifier:nfxi-asd11-hs", "NFXI-ASD11-HS", ["Notifier"], GTFAAST + " — EXCLUSIVA Notifier (6577/3947)",
           familia="FAAST LT-200", oem_manufacturer_marca="System Sensor"),
        _p("notifier:nfxi-asd12-hs", "NFXI-ASD12-HS", ["Notifier"], GTFAAST, familia="FAAST LT-200",
           oem_manufacturer_marca="System Sensor"),
        _p("notifier:nfxi-asd22-hs", "NFXI-ASD22-HS", ["Notifier"], GTFAAST, familia="FAAST LT-200",
           oem_manufacturer_marca="System Sensor"),
        # Pearl — central Notifier (los golds píxel-verificados cat001/cat005 la usan; el brand
        # 'Pearl' del doc 997-670 ya mapea a notifier). Promoción gt para que resuelva exact.
        _p("notifier:pearl", "Pearl", ["Notifier"],
           "gt-golds (cat001 píxel-verificado; docs 997-669/670/671-005-3)", categoria="central analógica"),
        # ── Detnov CAD-150 (gt Alberto: familia por nº de lazos; CAD-150R DISTINTO) ──
        _p("detnov:cad-150-1", "CAD-150-1", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150-2", "CAD-150-2", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150-2-mb", "CAD-150-2-MB", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150-4", "CAD-150-4", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150-8", "CAD-150-8", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150-8-plus", "CAD-150-8-PLUS", ["Detnov"], GTCAD, familia="CAD-150"),
        _p("detnov:cad-150r", "CAD-150R", ["Detnov"], GTCAD + " — producto DISTINTO (manual 55315501, ¿repetidor?)"),
    ]


def gt_aliases() -> list[dict]:
    A = lambda a, i, t, prov: {"alias": a, "id": i, "tipo": t, "provenance": prov, "added_by": "f1-gt"}
    return [
        A("ZXr-A", "morley:zxr50a", "variante-tipografica", GT78),
        A("ZXr-P", "morley:zxr50p", "variante-tipografica", GT78),
        A("VSN-RP1r+", "notifier:rp1r-supra", "codigo-comercial", GT78),
        A("VSN-RP1r-PLUS", "notifier:rp1r-supra", "codigo-comercial", GT78),
        A("VSN-RP1r-PLUS2", "notifier:rp1r-supra", "codigo-comercial", GT78),
        A("ESS-RP1r-Supra", "notifier:rp1r-supra", "codigo-comercial", GT78),
        A("DX2", "morley:dx2e", "variante-tipografica", GT90 + " P2"),
        # formas cortas FAAST (el path de usuario bare "NFXI-ASD11" y las compat-lists "FL2011EI")
        A("NFXI-ASD11", "notifier:nfxi-asd11-hs", "variante-tipografica", GTFAAST),
        A("NFXI-ASD12", "notifier:nfxi-asd12-hs", "variante-tipografica", GTFAAST),
        A("NFXI-ASD22", "notifier:nfxi-asd22-hs", "variante-tipografica", GTFAAST),
        A("FL0111E", "notifier:fl0111e-hs", "variante-tipografica", GTFAAST),
        A("FL0112E", "notifier:fl0112e-hs", "variante-tipografica", GTFAAST),
        A("FL0122E", "notifier:fl0122e-hs", "variante-tipografica", GTFAAST),
        A("FL2011EI", "notifier:fl2011ei-hs", "variante-tipografica", GTFAAST),
        A("FL2012EI", "notifier:fl2012ei-hs", "variante-tipografica", GTFAAST),
        A("FL2022EI", "notifier:fl2022ei-hs", "variante-tipografica", GTFAAST),
        A("BRH-PC-I05", "morley:mi-brh-pc-i", "codigo-comercial", GT90 + " P7 (ref nueva, pantallazo)"),
        A("BRS-PC-I05", "morley:mi-brs-pc-i", "codigo-comercial", GT90 + " P7 (ref nueva, pantallazo)"),
    ]


def gt_umbrellas() -> list[dict]:
    U = lambda t, ids, tipo, div, prov, cand=False: {
        "termino": t, "ids": ids, "tipo": tipo, "divergent": div, "candidate": cand,
        "provenance": prov, "added_by": "f1-gt"}
    ZXE = ["morley:zx1e", "morley:zx2e", "morley:zx5e"]
    ZXSE = ["morley:zx1se", "morley:zx2se", "morley:zx5se", "morley:zx10se"]
    DX = ["morley:dx1e", "morley:dx2e", "morley:dx4e"]
    DXC = ["morley:dxc1", "morley:dxc2", "morley:dxc4"]
    VLT = ["morley:vsn2-lt", "morley:vsn4-lt", "morley:vsn8-lt", "morley:vsn12-lt"]
    MPS = ["morley:mps15", "morley:mps25", "morley:mps50"]
    CAD = ["detnov:cad-150-1", "detnov:cad-150-2", "detnov:cad-150-2-mb",
           "detnov:cad-150-4", "detnov:cad-150-8", "detnov:cad-150-8-plus"]
    FLT = ["notifier:fl0111e-hs", "notifier:fl0112e-hs", "notifier:fl0122e-hs",
           "notifier:fl2011ei-hs", "notifier:fl2012ei-hs", "notifier:fl2022ei-hs",
           "notifier:nfxi-asd11-hs", "notifier:nfxi-asd12-hs", "notifier:nfxi-asd22-hs"]
    return [
        U("ZXe", ZXE, "familia", True, GT78 + " + s79/s80"),
        U("ZXSe", ZXSE, "familia", True, GT78 + " + " + GT90 + " P1 (lazos 1/1-2/1-5, PSU 4.2/8.6A)"),
        U("ZX2e/ZX5e", ["morley:zx2e", "morley:zx5e"], "rango", True, GT78),
        U("ZXR", ["morley:zxr50a", "morley:zxr50p"], "rango", True, GT90 + " P6"),
        U("Dimension", DX, "familia", True, GT90 + " P5"),
        U("serie Dimension", DX, "familia", True, GT90 + " P5"),
        U("DXc", DXC, "familia", True, GT90 + " P5"),
        U("DX Connexion", DXC, "familia", True, GT90 + " P5"),
        U("Vision LT", VLT, "familia", True, GT90 + " P5"),
        U("VSN LT", VLT, "familia", True, GT90 + " P5"),
        U("MPS", MPS, "familia", True, GT90 + " P5"),
        U("Serie MPS", MPS, "familia", True, GT90 + " P5"),
        U("MCP5A", ["morley:mcp5a-p05", "morley:mcp5a-p06"], "rango", "unknown",
          GT90 + " P5: PULSADOR; P05-vs-P06 sin adjudicar"),
        # FAAST/CAD-150 (gt memorias)
        U("FAAST LT-200", FLT, "serie", "unknown", GTFAAST + " — los 9 modelos (standalone 6574 + "
          "addressable 6575 + NFXI 6577); divergent sin adjudicar (cat007: specs relé/sirena "
          "idénticos en las 3 sub-series → mucho común; standalone tiene PREALARMA, addressable LAZO); QA"),
        U("CAD-150", CAD, "familia", True, GTCAD + " — variantes por nº de lazos"),
    ]


def gt_homonyms() -> list[dict]:
    return [
        {"termino": "RP1r", "ids": ["notifier:rp1r-supra", "notifier:rp1r",
                                    "morley:vsn-rp1r", "notifier:opc-rp1r"],
         "politica": "prefer:notifier:rp1r-supra", "candidate": False,
         "provenance": GT86, "added_by": "f1-gt"},
        {"termino": "ZX", "ids": ["morley:zx50", "morley:zx2e", "morley:zx2se",
                                  "morley:zxae", "morley:zxhe", "morley:zxce"],
         "politica": "clarify", "candidate": False,
         "provenance": GT90 + " P6: clarify adjudicado", "added_by": "f1-gt"},
    ]


def gt_relations() -> list[dict]:
    R = lambda o, d, t, prov: {"origen": o, "destino": d, "tipo": t, "provenance": prov}
    return [
        R("morley:zx2e", "morley:zx5e", "shared-doc", GT78 + " (MIE-*-530)"),
        R("morley:zxae", "morley:zxee", "shared-doc", GT78 + " (MIE-*-310)"),
        R("morley:dx1e-20s", "morley:dx1e", "variant-of", GT90 + " P2"),
        R("morley:dx1e-40m", "morley:dx1e", "variant-of", GT90 + " P2"),
        R("morley:dx2e-40m", "morley:dx2e", "variant-of", GT90 + " P2"),
        R("morley:dx4e-40l", "morley:dx4e", "variant-of", GT90 + " P2"),
        R("notifier:nfxi-asd11-hs", "notifier:nfxi-asd12-hs", "shared-doc", GTFAAST + " (6577/3947)"),
        R("notifier:fl0111e-hs", "notifier:fl0112e-hs", "shared-doc", GTFAAST + " (6574)"),
        R("notifier:fl2011ei-hs", "notifier:fl2012ei-hs", "shared-doc", GTFAAST + " (6575)"),
    ]


def gt_doc_map() -> list[tuple[str, list[tuple[str, str]]]]:
    """(prefijo-de-source_file DELIMITADO, [(id, role)]). Transcripción fiel de los mapas."""
    return [
        # Morley (gt s78 + QA s90)
        ("MIE-MI-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary"), ("morley:zx1e", "secondary")]),
        ("MIE-MP-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MU-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MP-535", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MU-535", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MI-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MP-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MU-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MP-315", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MU-315", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MI-600", [("morley:zx1se", "primary"), ("morley:zx2se", "primary"),
                        ("morley:zx5se", "primary"), ("morley:zx10se", "primary")]),
        ("MIE-MC-530", [("morley:mk-zx", "primary")]),
        ("MIE-MC-350", [("morley:mk-zx", "primary")]),
        ("MIE-MI-100", [("morley:hrz2-8", "primary")]),
        ("MIE-MA-100", [("morley:hrz2-8", "primary")]),
        ("HLSI-MN-103", [("notifier:rp1r-supra", "primary")]),
        ("HLSI-MA-103", [("notifier:rp1r-supra", "primary")]),
        ("MNDT102", [("notifier:rp1r", "primary")]),
        ("MN-DT-102", [("notifier:rp1r", "primary")]),
        ("MIEMN570", [("morley:vsn-rp1r", "primary")]),
        ("MN-DT-959", [("notifier:opc-rp1r", "primary")]),
        ("DXc_Manual variaciones", [("morley:dxc1", "primary"), ("morley:dxc2", "primary"),
                                    ("morley:dxc4", "primary")]),
        # Detnov CAD-150 (gt: 55315013/55315008 cubren la familia por-página → doc-level v0)
        ("55315013", [(f"detnov:cad-150-{v}", "primary") for v in ("1", "2", "2-mb", "4", "8", "8-plus")]),
        ("55315008", [(f"detnov:cad-150-{v}", "primary") for v in ("1", "2", "2-mb", "4", "8", "8-plus")]),
        ("55315501", [("detnov:cad-150r", "primary")]),
        # FAAST LT-200 (gt: cada doc → su sub-serie; reference_faast L13-16)
        ("I56-6574", [("notifier:fl0111e-hs", "primary"), ("notifier:fl0112e-hs", "primary"),
                      ("notifier:fl0122e-hs", "primary")]),
        ("I56-6575", [("notifier:fl2011ei-hs", "primary"), ("notifier:fl2012ei-hs", "primary"),
                      ("notifier:fl2022ei-hs", "primary")]),
        ("I56-6577", [("notifier:nfxi-asd11-hs", "primary"), ("notifier:nfxi-asd12-hs", "primary"),
                      ("notifier:nfxi-asd22-hs", "primary")]),
        ("I56-3947", [("notifier:nfxi-asd11-hs", "primary"), ("notifier:nfxi-asd12-hs", "primary"),
                      ("notifier:nfxi-asd22-hs", "primary")]),
    ]


# P7 (QA s90): promociones adjudicadas — pid → categoría/nota
GT90_PROMOTE = {
    "morley:mk-vsn": "software de configuración (VISION PLUS + VSN-CRA)",
    "morley:mkdx": "software de configuración (Dimension DX1e/DX2e/DX4e)",
    "morley:mk50": "software de configuración (ZX50)",
    "morley:mi-brh-pc-i": "base sirena premium (ref nueva BRH-PC-I05)",
    "morley:mi-brs-pc-i": "base sirena estándar (ref nueva BRS-PC-I05)",
    "morley:mi-bgl-pc-i": "base sirena/baliza (versión Notifier=NFXI-BF-WCS)",
    "morley:020-891": "cable/accesorio (web oficial)",
    "morley:795-072-100": "placa de lazo protocolo MorleyIAS (ZXSe, MIE-MI-600 p15)",
    "morley:795-068-100": "placa de lazo protocolo System Sensor (ZXSe, MIE-MI-600 p15)",
    "morley:sib5485": "módulo interfaz RS-485 (MIE-MI-300)",
}
