#!/usr/bin/env python3
"""s90_f1a_morley.py — F1a: SLICE VERTICAL Morley del catálogo canónico (contrato F0/DEC-079).

Carga en `data/catalog/` (repo-first, D1):
  1. El GROUND-TRUTH de Alberto (s78/s86, `memory/reference_morley_zx_rp1r.md`) — nivel 1,
     gana siempre: familias ZXe/ZXSe, ZXAE/ZXEE, el homónimo RP1r×4 (prefer:Supra por D7+hp011),
     canonicalizaciones de grafía. candidate=false con provenance gt-*.
  2. La SEMILLA s83 filtrada a docs Morley (extracción dúo cross-árbol) — nivel 2/3:
     productos found_by=both → candidate=false; single → candidate=true; colisión con gt → SKIP
     a cola de QA (el gt gana). Etiquetas-familia/combinadas ("ZX", "X/Y") NO son productos → QA.
  3. doc_map por document_id REAL (SELECT a `documents`; source_file = provenance).

Salida: data/catalog/*.jsonl (vía catalog_store.write_jsonl + validate) +
        evals/s90_f1a_qa_sample.md (skips/conflictos/candidates de alto blast-radius para Alberto).
NADA fuera de branch. Reversible (git).
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import httpx
import catalog_store as cs
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

SEED_IDENT = ROOT / "evals" / "s83_document_identity_final.jsonl"
SEED_MODELS = ROOT / "evals" / "s83_document_models_final.jsonl"
QA_OUT = ROOT / "evals" / "s90_f1a_qa_sample.md"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}

GT = "gt-s78-morley (memory/reference_morley_zx_rp1r.md)"
GT86 = "gt-s86-hp011 (DEC-074b, adjudicación Alberto)"
GT90 = "gt-s90-alberto-qa (adjudicación del packet s90_f1a_qa_propuesta)"

# Tokens ADJUDICADOS como no-producto/ambiguos (P2/P3/P4/P7 del QA s90) — se skipean de la
# semilla (productos Y aliases) con su razón. En forma normalizada (cs.norm_token).
GT90_BLOCKED = {
    "ma100": "P4: 'MA-100' no existe como producto — MIE-MA-100 es código de MANUAL de la HRZ2-8",
    "miema100": "P4: código de manual de la HRZ2-8, no producto",
    "dx2": "P2: abreviatura de DX2e (alias gt)",
    "brh": "P7: 'BRH' ambiguo cross-brand (Morley MI-BRH-PC-I vs Notifier NFXI-BSF-WCH) → fail-open",
    "bgl": "P7: 'BGL' ambiguo cross-brand (Morley MI-BGL-PC-I vs Notifier NFXI-BF-WCS) → fail-open",
    "exp": "P3: 'EXP' ambiguo (Mod.EXP tarjeta / Mod.EXP-060R impresora / MIW-EXP wireless) → fail-open",
    "faastlt": "P7: FAAST LT es FAMILIA multi-marca (reference_faast, clasificación s80) → F1 bulk",
    "dxconnexion": "P5/P7: término-familia → umbrella DXc",
    "dxcconnexion": "P5/P7: término-familia → umbrella DXc",
}
# Docs adjudicados fuera de alcance (no ensucian la cola QA)
GT90_IGNORED_DOCS = {"MIEMU520P": "P8: manual en PORTUGUÉS — no contemplar (docrel PT en F1 bulk)"}


def slug(model: str) -> str:
    s = model.strip().lower()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9._+-]", "", s)
    return s.strip("-.")


def gt_rows() -> tuple[list, list, list, list, list, list]:
    """El ground-truth curado (nivel 1). Devuelve (products, aliases, umbrellas, homonyms,
    relations, doc_map_gt) — doc_map_gt como (source_file_prefix, [(id, role)])."""
    P = lambda i, cm, vb, **kw: {"id": i, "canonical_model": cm, "vendido_bajo": vb,
                                 "estado": "activo", "provenance": GT, "added_by": "f1a-gt", **kw}
    products = [
        # familia ZXe (por lazos 1/2/5); ZX1e sin tag propio en corpus (content en MIE-*-530)
        P("morley:zx1e", "ZX1e", ["Morley-IAS"], familia="ZXe"),
        P("morley:zx2e", "ZX2e", ["Morley-IAS"], familia="ZXe"),
        P("morley:zx5e", "ZX5e", ["Morley-IAS"], familia="ZXe"),
        # familia ZXSe (MIE-MI-600, tagueado unknown en corpus; ZX10Se = 2×ZX5Se en red)
        P("morley:zx1se", "ZX1Se", ["Morley-IAS"], familia="ZXSe"),
        P("morley:zx2se", "ZX2Se", ["Morley-IAS"], familia="ZXSe"),
        P("morley:zx5se", "ZX5Se", ["Morley-IAS"], familia="ZXSe"),
        P("morley:zx10se", "ZX10Se", ["Morley-IAS"], familia="ZXSe"),
        # ZXAE/ZXEE = producto DISTINTO de ZXe (docs MIE-*-310/315)
        P("morley:zxae", "ZXAE", ["Morley-IAS"]),
        P("morley:zxee", "ZXEE", ["Morley-IAS"]),
        P("morley:zxhe", "ZXHE", ["Morley-IAS"]),
        P("morley:zxce", "ZXCE", ["Morley-IAS"]),
        P("morley:mk-zx", "MK-ZX", ["Morley-IAS"]),
        P("morley:zx50", "ZX50", ["Morley-IAS"]),
        # repetidores (A=con teclado, P=sin) y las impresoras de lazo (clase aparte)
        P("morley:zxr50a", "ZXR50A", ["Morley-IAS"]),
        P("morley:zxr50p", "ZXR50P", ["Morley-IAS"]),
        P("morley:zxr5b", "ZXR5B", ["Morley-IAS"]),
        P("morley:zxr4b", "ZXR4B", ["Morley-IAS"]),
        # RP1r ×4 (clasificación Alberto s78 — productos DISTINTOS)
        P("notifier:rp1r-supra", "RP1r-Supra", ["Notifier", "Morley-IAS (VSN-RP1r+)", "ESS"],
          provenance=GT + " + fix s78 (312ch Morley→Notifier)"),
        P("notifier:rp1r", "RP1r", ["Notifier"],
          provenance=GT + " — central de EXTINCIÓN, ≠ Supra (docs MNDT102*)"),
        P("morley:vsn-rp1r", "VSN-RP1r", ["Morley-IAS"],
          provenance=GT + " — central de extinción Morley (MIEMN570*)"),
        P("notifier:opc-rp1r", "OPC-RP1r", ["Notifier"],
          provenance=GT + " — SOFTWARE/pasarela SCADA, no producto físico (MN-DT-959)"),
        # ── adjudicaciones del QA s90 (P4/P3/P7, Alberto) ──
        P("morley:hrz2-8", "HRZ2-8", ["Morley-IAS"], categoria="central convencional 8 zonas",
          provenance=GT90 + " P4: los docs MIE-MA-100_* son manuales de la HRZ2-8 (corpus: MIE-MI-100)"),
        P("morley:mod-exp-060r", "Mod.EXP-060R", ["Morley-IAS"], categoria="impresora de lazo periférico",
          provenance=GT90 + " P3 (corpus: MIE-MP-530 p61, MIE-MI-450)"),
        P("morley:mi-dcmo", "MI-DCMO", ["Morley-IAS"], categoria="módulo de salida de control (serie ZX)",
          provenance=GT90 + " P7 (web Honeywell + corpus: MIE-MI-230, I56-4407 MI-DCMOE)"),
    ]
    A = lambda a, i, t: {"alias": a, "id": i, "tipo": t, "provenance": GT, "added_by": "f1a-gt"}
    aliases = [
        A("ZXr-A", "morley:zxr50a", "variante-tipografica"),
        A("ZXr-P", "morley:zxr50p", "variante-tipografica"),
        A("VSN-RP1r+", "notifier:rp1r-supra", "codigo-comercial"),
        A("VSN-RP1r-PLUS", "notifier:rp1r-supra", "codigo-comercial"),
        A("VSN-RP1r-PLUS2", "notifier:rp1r-supra", "codigo-comercial"),
        A("ESS-RP1r-Supra", "notifier:rp1r-supra", "codigo-comercial"),
    ]
    aliases += [
        {"alias": "DX2", "id": "morley:dx2e", "tipo": "variante-tipografica",
         "provenance": GT90 + " P2 (0 filas propias en DB)", "added_by": "f1a-gt"},
        {"alias": "BRH-PC-I05", "id": "morley:mi-brh-pc-i", "tipo": "codigo-comercial",
         "provenance": GT90 + " P7: ref NUEVA (datasheet, pantallazo Alberto); antigua=MI-BRH-PC-I", "added_by": "f1a-gt"},
        {"alias": "BRS-PC-I05", "id": "morley:mi-brs-pc-i", "tipo": "codigo-comercial",
         "provenance": GT90 + " P7: ref NUEVA (datasheet, pantallazo Alberto); antigua=MI-BRS-PC-I", "added_by": "f1a-gt"},
    ]
    umbrellas = [
        # divergent=true ADJUDICADO: las specs divergen entre variantes (hp018: ZX2e=2 sirenas,
        # ZX5e=4); NOTA: no toda query diverge (hp009 EOL es family-genérico) — la decisión
        # por-query es de F2 (gap EVPI declarado §8); el retrieval expande igual.
        {"termino": "ZXe", "ids": ["morley:zx1e", "morley:zx2e", "morley:zx5e"], "tipo": "familia",
         "divergent": True, "candidate": False, "provenance": GT + " + s79/s80 clarify-vs-diverge",
         "added_by": "f1a-gt"},
        {"termino": "ZXSe", "ids": ["morley:zx1se", "morley:zx2se", "morley:zx5se", "morley:zx10se"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT + " + " + GT90 + " P1: divergent=TRUE adjudicado (lazos 1/1-2/1-5, PSU 4.2 vs 8.6A)",
         "added_by": "f1a-gt"},
        # la etiqueta COMBINADA del corpus (tag de doc, también aparece en queries)
        {"termino": "ZX2e/ZX5e", "ids": ["morley:zx2e", "morley:zx5e"], "tipo": "rango",
         "divergent": True, "candidate": False, "provenance": GT + " (etiqueta combinada corpus)",
         "added_by": "f1a-gt"},
        # ZXR — P6 adjudicado: promover, divergent=true (A=con teclado / P=sin)
        {"termino": "ZXR", "ids": ["morley:zxr50a", "morley:zxr50p"], "tipo": "rango",
         "divergent": True, "candidate": False, "provenance": GT90 + " P6", "added_by": "f1a-gt"},
        # ── P5: los términos-familia que la semilla metía como alias de variantes (adjudicados) ──
        {"termino": "Dimension", "ids": ["morley:dx1e", "morley:dx2e", "morley:dx4e"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5 (1/2/4 lazos)", "added_by": "f1a-gt"},
        {"termino": "serie Dimension", "ids": ["morley:dx1e", "morley:dx2e", "morley:dx4e"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5", "added_by": "f1a-gt"},
        {"termino": "DXc", "ids": ["morley:dxc1", "morley:dxc2", "morley:dxc4"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5 (1/2/4 lazos; el doc de cat020)", "added_by": "f1a-gt"},
        {"termino": "DX Connexion", "ids": ["morley:dxc1", "morley:dxc2", "morley:dxc4"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5", "added_by": "f1a-gt"},
        {"termino": "Vision LT", "ids": ["morley:vsn2-lt", "morley:vsn4-lt", "morley:vsn8-lt", "morley:vsn12-lt"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5 (2/4/8/12 zonas)", "added_by": "f1a-gt"},
        {"termino": "VSN LT", "ids": ["morley:vsn2-lt", "morley:vsn4-lt", "morley:vsn8-lt", "morley:vsn12-lt"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5", "added_by": "f1a-gt"},
        {"termino": "MPS", "ids": ["morley:mps15", "morley:mps25", "morley:mps50"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5 (amperajes)", "added_by": "f1a-gt"},
        {"termino": "Serie MPS", "ids": ["morley:mps15", "morley:mps25", "morley:mps50"],
         "tipo": "familia", "divergent": True, "candidate": False,
         "provenance": GT90 + " P5", "added_by": "f1a-gt"},
        {"termino": "MCP5A", "ids": ["morley:mcp5a-p05", "morley:mcp5a-p06"],
         "tipo": "rango", "divergent": "unknown", "candidate": False,
         "provenance": GT90 + " P5: PULSADOR (D707 MI-MCPA5 + web Honeywell); P05-vs-P06 sin adjudicar → fail-open",
         "added_by": "f1a-gt"},
    ]
    homonyms = [
        # LA clase hp011: 'RP1r' a secas — 4 productos sin relación de familia.
        # D7: prefer donde HAY ground-truth → el gold hp011 (Alberto): RP1r = RP1r-Supra, answer.
        {"termino": "RP1r", "ids": ["notifier:rp1r-supra", "notifier:rp1r",
                                    "morley:vsn-rp1r", "notifier:opc-rp1r"],
         "politica": "prefer:notifier:rp1r-supra", "candidate": False,
         "provenance": GT86, "added_by": "f1a-gt"},
        # 'ZX' a secas — P6 ADJUDICADO por Alberto: CLARIFY ("más seguro que adivinar").
        # Los ids = representantes de cada familia ZX (las opciones del clarify; F2 genera el texto).
        {"termino": "ZX", "ids": ["morley:zx50", "morley:zx2e", "morley:zx2se",
                                  "morley:zxae", "morley:zxhe", "morley:zxce"],
         "politica": "clarify", "candidate": False,
         "provenance": GT90 + " P6: clarify adjudicado (ambiguo entre 6 familias ZX)", "added_by": "f1a-gt"},
    ]
    relations = [
        {"origen": "morley:zx2e", "destino": "morley:zx5e", "tipo": "shared-doc", "provenance": GT + " (MIE-*-530)"},
        {"origen": "morley:zxae", "destino": "morley:zxee", "tipo": "shared-doc", "provenance": GT + " (MIE-*-310)"},
        # P2 (nota Alberto): los SKU de cabina de la serie Dimension = variantes de sus bases
        {"origen": "morley:dx1e-20s", "destino": "morley:dx1e", "tipo": "variant-of", "provenance": GT90 + " P2"},
        {"origen": "morley:dx1e-40m", "destino": "morley:dx1e", "tipo": "variant-of", "provenance": GT90 + " P2"},
        {"origen": "morley:dx2e-40m", "destino": "morley:dx2e", "tipo": "variant-of", "provenance": GT90 + " P2"},
        {"origen": "morley:dx4e-40l", "destino": "morley:dx4e", "tipo": "variant-of", "provenance": GT90 + " P2"},
    ]
    # doc→productos del gt (match por prefijo de source_file en DB)
    doc_map_gt = [
        ("MIE-MI-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary"), ("morley:zx1e", "secondary")]),
        ("MIE-MP-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MU-530", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MP-535", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("MIE-MI-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MP-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MU-310", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MP-315", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MI-600", [("morley:zx1se", "primary"), ("morley:zx2se", "primary"),
                        ("morley:zx5se", "primary"), ("morley:zx10se", "primary")]),
        # MK-ZX = MIE-MC-530, MC-350 (config) — memoria :17 (fix dúo s90: faltaba transcribir)
        ("MIE-MC-530", [("morley:mk-zx", "primary")]),
        ("MIE-MC-350", [("morley:mk-zx", "primary")]),
        ("HLSI-MN-103", [("notifier:rp1r-supra", "primary")]),
        ("HLSI-MA-103", [("notifier:rp1r-supra", "primary")]),
        ("MNDT102", [("notifier:rp1r", "primary")]),
        ("MN-DT-102", [("notifier:rp1r", "primary")]),
        ("MIEMN570", [("morley:vsn-rp1r", "primary")]),
        ("MN-DT-959", [("notifier:opc-rp1r", "primary")]),
        # ── QA s90 (P4/P8, Alberto) ──
        ("MIE-MI-100", [("morley:hrz2-8", "primary")]),          # el doc principal de la central
        ("MIE-MA-100", [("morley:hrz2-8", "primary")]),          # los "MA-100" son manuales de la HRZ2-8
        ("MIE-MU-315", [("morley:zxae", "primary"), ("morley:zxee", "primary")]),
        ("MIE-MU-535", [("morley:zx2e", "primary"), ("morley:zx5e", "primary")]),
        ("DXc_Manual variaciones", [("morley:dxc1", "primary"), ("morley:dxc2", "primary"),
                                    ("morley:dxc4", "primary")]),
    ]
    return products, aliases, umbrellas, homonyms, relations, doc_map_gt


# etiquetas de la semilla que NO son productos (familia/combinada/genérica) → cola de QA.
# Se aplican a canonical_model Y a los ALIASES (fix dúo s90: 'DX'/'VSN'/'Vision' entraban como
# alias de UNA variante = colapso familia→variante por la puerta de atrás, la clase hp018/hp009).
# Tokens en forma NORMALIZADA (norm_token).
NOT_A_PRODUCT_RX = re.compile(r"(/| y | e )", re.IGNORECASE)
GENERIC_LABELS = {"zx", "dx", "vsn", "zxe", "zxse", "dxc", "morley", "morleyias", "vision",
                  "dimension", "connexion", "lite", "plus", "max", "agile", "eco2000"}
# sustantivos descriptivos y estándares de interfaz — no son identidad de producto
GENERIC_WORDS_RX = re.compile(
    r"^(impresora|placa( de lazo)?|gateway|pasarela|tarjeta|central|detector|sirena|panel|"
    r"repetidor|modulo|módulo|fuente|llave( opcional)?|base|zocalo|zócalo|rs-?232|rs-?485|"
    r"printer|loop card|key|power supply)\b", re.IGNORECASE)


def not_a_product(label: str) -> str | None:
    """Motivo por el que la etiqueta NO puede ser producto/alias consumible; None si ok."""
    if NOT_A_PRODUCT_RX.search(label):
        return "combinada/familia (contiene separador)"
    if cs.norm_token(label) in GENERIC_LABELS:
        return "término-familia/marca genérico"
    if GENERIC_WORDS_RX.match(label.strip()):
        return "sustantivo descriptivo / estándar de interfaz"
    return None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ident = [json.loads(l) for l in SEED_IDENT.read_text(encoding="utf-8").splitlines() if l.strip()]
    models_by_src = {r["source_file"]: r for r in
                     (json.loads(l) for l in SEED_MODELS.read_text(encoding="utf-8").splitlines() if l.strip())}
    morley_docs = [r for r in ident if "morley" in (r.get("brand_on_doc") or "").lower()]
    print(f"[semilla] docs Morley: {len(morley_docs)}")

    # ── document_id reales (la clave de doc_map — H2/dúo: no filename) ──
    # documents usa `source_pdf_filename` (con .pdf); la semilla s83 usa el stem sin extensión
    # → se matchea por norm_token del stem.
    with httpx.Client(timeout=60) as c:
        rows, offset = [], 0
        while True:
            page = c.get(f"{SUPABASE_URL}/rest/v1/documents", headers=H,
                         params={"select": "id,source_pdf_filename", "limit": "1000",
                                 "offset": str(offset)}).json()
            assert isinstance(page, list), f"documents SELECT falló: {page}"
            rows.extend(page)
            if len(page) < 1000:
                break
            offset += 1000
    def _stem(fn: str) -> str:
        return re.sub(r"\.pdf$", "", fn or "", flags=re.IGNORECASE)
    docid_by_norm = {cs.norm_token(_stem(r["source_pdf_filename"])): (r["id"], _stem(r["source_pdf_filename"]))
                     for r in rows if r.get("source_pdf_filename")}
    docid_by_src = {}   # source_file(semilla, stem) -> document_id
    for doc in morley_docs:
        hit = docid_by_norm.get(cs.norm_token(doc["source_file"]))
        if hit:
            docid_by_src[doc["source_file"]] = hit[0]
    def find_docids(prefix: str) -> list[tuple[str, str]]:
        """Match DELIMITADO (fix crítico dúo s90): tras el prefijo normalizado, el siguiente
        carácter NO puede ser un dígito — 'MNDT102' matchea MNDT102/MNDT102P/MNDT102I pero
        NO MNDT1020/1025/1026 (que son detectores IDX/FSL/LPX → el greedy fabricaba gt)."""
        p = cs.norm_token(prefix)
        out = []
        for norm, (did, src) in docid_by_norm.items():
            if norm.startswith(p) and not (len(norm) > len(p) and norm[len(p)].isdigit()):
                out.append((did, src))
        return out
    print(f"[DB] documents: {len(rows)} | semilla-Morley matcheados a document_id: {len(docid_by_src)}/{len(morley_docs)}")

    gt_products, gt_aliases, gt_umbrellas, gt_homonyms, gt_relations, doc_map_gt = gt_rows()
    products = {p["id"]: p for p in gt_products}
    reserved = {cs.norm_token(p["canonical_model"]) for p in gt_products}
    reserved |= {cs.norm_token(u["termino"]) for u in gt_umbrellas}
    reserved |= {cs.norm_token(h["termino"]) for h in gt_homonyms}
    # los ALIASES del gt también reservan su token: la semilla NO puede crear un producto
    # cuyo canonical colisione con un alias adjudicado (bug cazado por el smoke: 'ZXr-A'
    # semilla pisaba el alias gt ZXr-A→ZXR50A y ganaba por exact)
    reserved |= {cs.norm_token(a["alias"]) for a in gt_aliases}
    aliases = {cs.norm_token(a["alias"]): a for a in gt_aliases}

    qa: dict[str, list[str]] = defaultdict(list)

    # ── semilla → productos/aliases (nivel 2/3; gt gana; etiquetas-no-producto → QA) ──
    n_seed_prod = n_seed_alias = 0
    for doc in morley_docs:
        for m in (models_by_src.get(doc["source_file"], {}).get("models") or []):
            cm = (m.get("canonical_model") or "").strip()
            if not cm:
                continue
            key = cs.norm_token(cm)
            if key in reserved:
                continue  # el gt ya lo define (ZX2e etc.) — la semilla no lo pisa
            if key in GT90_BLOCKED:
                continue  # adjudicado por Alberto (QA s90) — razón en GT90_BLOCKED (no re-ensucia la cola)
            why = not_a_product(cm)
            if why:
                qa[f"etiqueta-no-producto ({why}) → NO cargada"].append(
                    f"`{cm}` (doc {doc['source_file'][:50]})")
                continue
            pid = f"morley:{slug(cm)}"
            if pid in products:
                if m.get("found_by") == "both" and products[pid].get("candidate"):
                    products[pid]["candidate"] = False   # una mención both promueve
                    products[pid]["provenance"] += f" | promoted:found_by=both ({doc['source_file'][:40]})"
                continue
            products[pid] = {
                "id": pid, "canonical_model": cm, "vendido_bajo": [doc.get("brand_on_doc") or "Morley-IAS"],
                "estado": "activo", "candidate": m.get("found_by") != "both",
                "provenance": f"s83:{doc['source_file'][:60]}", "added_by": "f1a-seed",
            }
            reserved.add(key)
            n_seed_prod += 1
            for al in (m.get("aliases") or []):
                akey = cs.norm_token(al)
                if not akey or akey in reserved or akey in GT90_BLOCKED:
                    continue
                why = not_a_product(al)   # fix dúo: mismos filtros para ALIASES
                if why:
                    qa[f"alias-no-consumible ({why}) → NO cargado (¿umbrella candidate?)"].append(
                        f"alias `{al}`→{pid}")
                    continue
                if akey in aliases:
                    if aliases[akey]["id"] != pid:   # conflicto alias↔alias → QA, no first-wins
                        qa["conflicto alias↔alias (mismo token, productos distintos) → adjudicar"].append(
                            f"`{al}`: {aliases[akey]['id']} vs {pid}")
                    continue
                tipo = "numero-de-parte" if re.search(r"\d{4,}", al) else "nombre-largo"
                aliases[akey] = {"alias": al, "id": pid, "tipo": tipo,
                                 "provenance": f"s83:{doc['source_file'][:60]}", "added_by": "f1a-seed"}
                n_seed_alias += 1
    # ── P7 (QA s90): promociones adjudicadas por Alberto, con categoría/nota de dominio ──
    GT90_PROMOTE = {
        "morley:mk-vsn": "software de configuración (centrales VISION PLUS + comunicador VSN-CRA)",
        "morley:mkdx": "software de configuración (serie Dimension: DX1e/DX2e/DX4e)",
        "morley:mk50": "software de configuración (central ZX50)",
        "morley:mi-brh-pc-i": "base sirena premium (ref nueva BRH-PC-I05; doc D 1150-1 BRH Morley)",
        "morley:mi-brs-pc-i": "base sirena estándar (ref nueva BRS-PC-I05; doc D 1151-1 BRS Morley)",
        "morley:mi-bgl-pc-i": "base sirena/baliza (versión Notifier=NFXI-BF-WCS, F1 bulk)",
        "morley:020-891": "cable/accesorio (web oficial morley-ias.es)",
        "morley:795-072-100": "placa de lazo protocolo MorleyIAS para ZXSe (MIE-MI-600 p15 Tabla 2)",
        "morley:795-068-100": "placa de lazo protocolo System Sensor para ZXSe (MIE-MI-600 p15 Tabla 2)",
        "morley:sib5485": "módulo interfaz RS-485 Ref SIB5485 (MIE-MI-300, ZX50)",
    }
    for pid, cat_note in GT90_PROMOTE.items():
        if pid in products:
            products[pid]["candidate"] = False
            products[pid]["categoria"] = cat_note.split(" (")[0]
            products[pid]["provenance"] += f" | {GT90} P7: {cat_note}"
    # mi-cmo: posible typo/pariente de MI-DCMO (web Honeywell) — queda candidate con nota
    if "morley:mi-cmo" in products:
        products["morley:mi-cmo"]["provenance"] += f" | {GT90} P7: posible alias de MI-DCMO — verificar en F1"

    # pase de reconciliación (la clase DX2/EXP cazada por la puerta): un alias cuyo token
    # coincide con el canonical de OTRO producto = posible mismo-producto-dos-formas → QA
    # (adjudicar merge), NUNCA cargado (exact pisaría el alias en silencio).
    canon_norms = {cs.norm_token(p["canonical_model"]): p["id"] for p in products.values()}
    for akey in list(aliases):
        owner = canon_norms.get(akey)
        if owner and owner != aliases[akey]["id"]:
            a = aliases.pop(akey)
            qa["colisión alias↔canonical (¿mismo producto? adjudicar merge)"].append(
                f"alias `{a['alias']}`→{a['id']} vs canonical de `{owner}`")
    print(f"[semilla] productos nuevos: {n_seed_prod} | aliases: {len(aliases)} | QA-skips: {sum(len(v) for v in qa.values())}")

    # ── doc_map: gt (por prefijo DELIMITADO) + semilla — DEDUPE por document_id (fix dúo s90) ──
    doc_map_by_id: dict[str, dict] = {}
    for prefix, entries in doc_map_gt:
        hits = find_docids(prefix)
        if not hits:
            qa["doc_map gt SIN match en documents (revisar prefijo)"].append(f"`{prefix}`")
            continue
        for did, src in hits:
            if did in doc_map_by_id:   # dos prefijos gt que norman igual (MNDT102/MN-DT-102) → 1 fila
                continue
            doc_map_by_id[did] = {"document_id": did, "source_file": src,
                                  "entries": [{"id": i, "role": r, "scope": "doc", "provenance": GT}
                                              for i, r in entries]}
    # lookup canonical→pid vía NORM contra los productos cargados (fix dúo: el slug divergía —
    # 'ZXR-4B'→slug zxr-4b ∉ products vs gt morley:zxr4b → docs de Alberto caían en silencio)
    pid_by_norm = {cs.norm_token(p["canonical_model"]): p["id"] for p in products.values()}
    pid_by_norm.update({akey: a["id"] for akey, a in aliases.items()})   # canonical+ALIAS (dúo)
    for doc in morley_docs:
        src = doc["source_file"]
        if any(cs.norm_token(src).startswith(cs.norm_token(ig)) for ig in GT90_IGNORED_DOCS):
            continue   # adjudicado fuera de alcance (P8: MIEMU520P = PT)
        if src not in docid_by_src:
            qa["doc de la semilla SIN document_id en DB"].append(f"`{src[:60]}`")
            continue
        did = docid_by_src[src]
        if did in doc_map_by_id:
            continue
        entries = []
        for m in (models_by_src.get(src, {}).get("models") or []):
            cm = m.get("canonical_model") or ""
            pid = pid_by_norm.get(cs.norm_token(cm))
            if pid and not not_a_product(cm):
                entries.append({"id": pid, "role": m.get("role") or "secondary", "scope": "doc",
                                "provenance": f"s83 found_by={m.get('found_by')}"})
        if entries:
            doc_map_by_id[did] = {"document_id": did, "source_file": src, "entries": entries}
        else:
            qa["doc Morley SIN entrada en doc_map (0 productos mapeables) → revisar"].append(f"`{src[:60]}`")
    doc_map = list(doc_map_by_id.values())

    # ── escribir vía la puerta (writes intermedios sin validar; validación del CONJUNTO al final) ──
    cs.write_jsonl("products", sorted(products.values(), key=lambda r: r["id"]), validate_after=False)
    cs.write_jsonl("aliases", sorted(aliases.values(), key=lambda r: cs.norm_token(r["alias"])), validate_after=False)
    cs.write_jsonl("umbrellas", gt_umbrellas, validate_after=False)
    cs.write_jsonl("homonyms", gt_homonyms, validate_after=False)
    cs.write_jsonl("relations", gt_relations, validate_after=False)
    cs.write_jsonl("doc_map", sorted(doc_map, key=lambda r: r["source_file"]), validate_after=False)
    cs.write_jsonl("docrel", [], validate_after=False)
    errs = cs.validate()
    print(f"[validate] {len(errs)} error(es)")
    for e in errs[:20]:
        print("  [ERROR]", e)

    # ── QA-sample para Alberto ──
    n_cand = sum(1 for p in products.values() if p.get("candidate"))
    lines = ["# s90 · F1a — QA-sample del slice Morley (para revisión de Alberto, ~15 min)\n",
             f"products: {len(products)} ({n_cand} candidate) · aliases: {len(aliases)} · "
             f"umbrellas: {len(gt_umbrellas)} · homonyms: {len(gt_homonyms)} · doc_map: {len(doc_map)} docs\n",
             "\n## ⚡ ADJUDICACIÓN QUE DESBLOQUEA (fix dúo: antes estaba mal listada como 'confirmar')",
             "- **`divergent` de ZXSe**: hoy `unknown` → la familia ZXSe está FAIL-OPEN (MIE-MI-600, 'el caso",
             "  de más valor del lado ZX', queda invisible a la resolución hasta que adjudiques). ¿Las respuestas",
             "  divergen entre ZX1Se/ZX2Se/ZX5Se/ZX10Se (→true) o son family-genéricas (→false)? [ ] true [ ] false",
             "\n## Alto blast-radius cargado como ADJUDICADO (gt tuyo — confirma que sigue vigente)",
             "- paraguas `ZXe` → zx1e/zx2e/zx5e (divergent=true) · `ZX2e/ZX5e` → ambos",
             "- homónimo `RP1r` → prefer:notifier:rp1r-supra (D7; gold hp011)",
             "\n## Pendiente de tu QA (candidate=true, NO se consume hasta promoción)"]
    lines.append("- umbrella `ZXR` → zxr50a/zxr50p (de family_scope semilla, sin gt)")
    lines.append("- homónimo `ZX` → clarify (ambiguo entre familias, sin gt)")
    lines.append(f"- {n_cand} productos candidate (found_by=single) — lista en products.jsonl")
    lines.append("\n## Gaps DECLARADOS del slice (no es F1 completa)")
    lines.append("- `docrel.jsonl` VACÍO: los pares language-variant ES/EN y revision-of se pueblan "
                 "en F1 bulk (detección vía languages[] de s83) — el slice no los cubre (dúo s90).")
    lines.append("- Solo docs Morley (114/1170); la normalización free-text completa (592 family_scope) es F1 bulk.")
    for reason, items in qa.items():
        lines.append(f"\n## {reason} ({len(items)})")
        lines.extend(f"- {i}" for i in items[:25])
        if len(items) > 25:
            lines.append(f"- … (+{len(items)-25})")
    QA_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[written] {QA_OUT.name}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
