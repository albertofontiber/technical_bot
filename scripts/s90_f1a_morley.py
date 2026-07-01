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
    umbrellas = [
        # divergent=true ADJUDICADO: las specs divergen entre variantes (hp018: ZX2e=2 sirenas,
        # ZX5e=4); NOTA: no toda query diverge (hp009 EOL es family-genérico) — la decisión
        # por-query es de F2 (gap EVPI declarado §8); el retrieval expande igual.
        {"termino": "ZXe", "ids": ["morley:zx1e", "morley:zx2e", "morley:zx5e"], "tipo": "familia",
         "divergent": True, "candidate": False, "provenance": GT + " + s79/s80 clarify-vs-diverge",
         "added_by": "f1a-gt"},
        {"termino": "ZXSe", "ids": ["morley:zx1se", "morley:zx2se", "morley:zx5se", "morley:zx10se"],
         "tipo": "familia", "divergent": "unknown", "candidate": False,
         "provenance": GT + " (MIE-MI-600, aplicabilidad por-sección)", "added_by": "f1a-gt"},
        # la etiqueta COMBINADA del corpus (tag de doc, también aparece en queries)
        {"termino": "ZX2e/ZX5e", "ids": ["morley:zx2e", "morley:zx5e"], "tipo": "rango",
         "divergent": True, "candidate": False, "provenance": GT + " (etiqueta combinada corpus)",
         "added_by": "f1a-gt"},
        # ZXR genérico: razonable pero NO adjudicado explícitamente → candidate (QA)
        {"termino": "ZXR", "ids": ["morley:zxr50a", "morley:zxr50p"], "tipo": "rango",
         "divergent": "unknown", "candidate": True, "provenance": "semilla family_scope 'ZXR (repetidores)'",
         "added_by": "f1a-seed"},
    ]
    homonyms = [
        # LA clase hp011: 'RP1r' a secas — 4 productos sin relación de familia.
        # D7: prefer donde HAY ground-truth → el gold hp011 (Alberto): RP1r = RP1r-Supra, answer.
        {"termino": "RP1r", "ids": ["notifier:rp1r-supra", "notifier:rp1r",
                                    "morley:vsn-rp1r", "notifier:opc-rp1r"],
         "politica": "prefer:notifier:rp1r-supra", "candidate": False,
         "provenance": GT86, "added_by": "f1a-gt"},
        # 'ZX' a secas: ambiguo entre familias (ZX50/ZXe/ZXSe/ZXAE...) — SIN adjudicar → candidate
        # (bloquea el exact de 'ZX' → fail-open, mejor que resolver mal).
        {"termino": "ZX", "ids": ["morley:zx50", "morley:zx2e", "morley:zxae", "morley:zx2se"],
         "politica": "clarify", "candidate": True,
         "provenance": "semilla family_scope 'ZX'/'ZX / ZXe' (ambiguo, sin gt)", "added_by": "f1a-seed"},
    ]
    relations = [
        {"origen": "morley:zx2e", "destino": "morley:zx5e", "tipo": "shared-doc", "provenance": GT + " (MIE-*-530)"},
        {"origen": "morley:zxae", "destino": "morley:zxee", "tipo": "shared-doc", "provenance": GT + " (MIE-*-310)"},
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
        ("HLSI-MN-103", [("notifier:rp1r-supra", "primary")]),
        ("HLSI-MA-103", [("notifier:rp1r-supra", "primary")]),
        ("MNDT102", [("notifier:rp1r", "primary")]),
        ("MN-DT-102", [("notifier:rp1r", "primary")]),
        ("MIEMN570", [("morley:vsn-rp1r", "primary")]),
        ("MN-DT-959", [("notifier:opc-rp1r", "primary")]),
    ]
    return products, aliases, umbrellas, homonyms, relations, doc_map_gt


# etiquetas de la semilla que NO son productos (familia/combinada/genérica) → cola de QA
NOT_A_PRODUCT_RX = re.compile(r"(/| y | e )", re.IGNORECASE)
GENERIC_LABELS = {"zx", "dx", "vsn", "zxe", "zxse", "dxc", "morley", "morley-ias"}


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
        p = cs.norm_token(prefix)
        return [(did, src) for norm, (did, src) in docid_by_norm.items() if norm.startswith(p)]
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
            if NOT_A_PRODUCT_RX.search(cm) or key in GENERIC_LABELS:
                qa["etiqueta-no-producto (familia/combinada) → NO cargada"].append(
                    f"`{cm}` (doc {doc['source_file'][:50]})")
                continue
            pid = f"morley:{slug(cm)}"
            if pid in products:
                if m.get("found_by") == "both":
                    products[pid]["candidate"] = False   # una mención both promueve
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
                if not akey or akey in reserved or akey in aliases:
                    continue
                tipo = "numero-de-parte" if re.search(r"\d{4,}", al) else "nombre-largo"
                aliases[akey] = {"alias": al, "id": pid, "tipo": tipo,
                                 "provenance": f"s83:{doc['source_file'][:60]}", "added_by": "f1a-seed"}
                n_seed_alias += 1
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

    # ── doc_map: gt (por prefijo) + semilla (docs Morley restantes con primary claro) ──
    doc_map, mapped = [], set()
    for prefix, entries in doc_map_gt:
        hits = find_docids(prefix)
        if not hits:
            qa["doc_map gt SIN match en documents (revisar prefijo)"].append(f"`{prefix}`")
            continue
        for did, src in hits:
            doc_map.append({"document_id": did, "source_file": src,
                            "entries": [{"id": i, "role": r, "scope": "doc", "provenance": GT}
                                        for i, r in entries]})
            mapped.add(src)
    for doc in morley_docs:
        src = doc["source_file"]
        if src in mapped or src not in docid_by_src:
            if src not in docid_by_src:
                qa["doc de la semilla SIN document_id en DB"].append(f"`{src[:60]}`")
            continue
        entries = []
        for m in (models_by_src.get(src, {}).get("models") or []):
            pid = f"morley:{slug(m.get('canonical_model') or '')}"
            if pid in products and not NOT_A_PRODUCT_RX.search(m.get("canonical_model") or ""):
                entries.append({"id": pid, "role": m.get("role") or "secondary", "scope": "doc",
                                "provenance": f"s83 found_by={m.get('found_by')}"})
        if entries:
            doc_map.append({"document_id": docid_by_src[src], "source_file": src, "entries": entries})

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
             "\n## Alto blast-radius cargado como ADJUDICADO (gt tuyo — confirma que sigue vigente)",
             "- paraguas `ZXe` → zx1e/zx2e/zx5e (divergent=true) · `ZXSe` → los 4 Se (unknown) · `ZX2e/ZX5e` → ambos",
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
