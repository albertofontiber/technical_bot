#!/usr/bin/env python3
"""s65_capab.py — Runner del ciclo CAPA B de TECH_DEBT #43 (higiene de identidad).

PRE-REGISTRO: evals/_s65_capab_design.md (v2, post-dúo: sub-agente 13/13
confirmados 0 FP + cross-model GPT-5.5 7/7 — tally adversarial_review_log.jsonl
ts 2026-06-12T14:47:20). Este script EJECUTA el diseño, no lo define.

Fases:
  --phase inventory  Read-only. RE-MIDE y CONGELA las poblaciones (F11/X5):
                     A1 backfill B7 (consenso+unanimidad+cross-check, F6/X2),
                     A2 mismatch doc↔chunks, A3 revision basura, A4 clasificación
                     B6 (excluyendo docs que A1 enlaza, F1), A5 unknown dirigido.
                     → evals/s65_capab_inventory.yaml (números + curación)
                     → evals/s65_capab_plan.yaml (mutaciones EXACTAS a autorizar)
  --phase before     Pools wide (top_k=50) de los 39 dev con embed-cache propio;
                     marca golds esperados-afectados (sources del plan en pool);
                     snapshot de _get_all_known_manufacturers (F9b).
  --phase apply      Ejecuta el PLAN congelado (no recalcula). Orden F1:
                     A1-casados → A1-inserts → A1-links → ASSERT recompute B6 ==
                     planificado → A4 → A3 → A2 → A5. Cada step con before-values
                     por fila (F3/X4) → evals/s65_apply_log.yaml.
  --phase after      Pools con el MISMO cache → firma EN ORDEN DEL POOL (F10),
                     clasificación identico/orden/composicion + convergencia
                     anti-dado-de-red + decisión pre-declarada para entradas
                     (F9a) + ASSERT invariante (ningún doc inactivo con chunks
                     v2) + fingerprint lifecycle → evals/s65_capab_report.yaml.
  --phase smoke      Path real: 2X-A (cita r005), CAD-201, control Notifier,
                     catálogo de fabricantes (F8).
  --phase rollback   reversed(steps) con before-values (FK: links a NULL antes
                     de DELETE de filas nuevas).

Solo `apply` muta (requiere autorización explícita de Alberto — DEC-045 patrón).
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import json
import re
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", str(ROOT / "evals" / "s65_embed_cache.json"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# .get para que importar la LÓGICA PURA en tests no exija .env (las fases I/O
# fallan en la primera llamada si faltan credenciales — fail-fast suficiente).
URL = os.environ.get("SUPABASE_URL", "")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
EVALS = ROOT / "evals"

F_INVENTORY = EVALS / "s65_capab_inventory.yaml"
F_PLAN = EVALS / "s65_capab_plan.yaml"
F_BEFORE = EVALS / "s65_pools_before.json"
F_AFTER = EVALS / "s65_pools_after.json"
F_APPLY = EVALS / "s65_apply_log.yaml"
F_REPORT = EVALS / "s65_capab_report.yaml"

# Lista CERRADA de valores de revisión basura (audit s65 B3 — 11 valores, 80 docs).
REV_GARBAGE_VALUES = [
    "Rev ia", "Rev iamente", "Rev ias", "Rev iatura", "Rev iaturas",
    "Rev io", "Rev isa", "Rev isar", "Rev ise", "Rev istas", "Rev isto",
]

# Marcas de terceros (audit s62/s65 B1) para cross-check del consenso (F6).
THIRD_PARTY_KEYWORDS = {
    "Pfannenberg": ["pfannenberg", "pa5", "pa 5", "pa20", "pa 20", "ds10", "ds 10"],
    "Spectrex": ["spectrex", "sharpeye", "sharp eye"],
    "Sensitron": ["sensitron", "sgmcb", "smart3", "smart 3"],
    "Honeywell": ["fs24x", "fire sentry"],
}

# Carpetas locales donde pueden vivir los PDF de los lotes (sha-check + canal).
LOCAL_MANUAL_DIRS = sorted(ROOT.glob("Manuales_*"))


# ============================================================================
# LÓGICA PURA (testeable sin red)
# ============================================================================

def parse_revision(source_file: str) -> str | None:
    """Revisión desde el filename — SOLO patrones verificados del lote s55
    (diseño A1; anti-greedy: la basura B3 nació de un parser codicioso).
      00-3280-501-4009-05_r005_2x-a_... → 'r005'
      sds0098es_solo_a10_iss_2.1        → 'iss 2.1'
    """
    m = re.search(r"_r(\d{3})_", source_file)
    if m:
        return f"r{m.group(1)}"
    m = re.search(r"_iss_(\d+(?:\.\d+)?)$", source_file) or \
        re.search(r"_iss_(\d+(?:\.\d+)?)[_.]", source_file)
    if m:
        return f"iss {m.group(1)}"
    return None


def consensus(values: list[str | None]) -> tuple[str | None, bool]:
    """(moda, unánime) sobre valores no-vacíos. Sin valores → (None, False)."""
    vals = [v for v in values if v]
    if not vals:
        return None, False
    cnt = Counter(vals)
    moda, _ = cnt.most_common(1)[0]
    return moda, len(cnt) == 1


def keyword_brand(filename: str) -> str | None:
    """Marca de tercero sugerida por el filename (cross-check F6), o None."""
    fn = (filename or "").lower()
    for brand, kws in THIRD_PARTY_KEYWORDS.items():
        if any(k in fn for k in kws):
            return brand
    return None


def norm_fname(s: str | None) -> str:
    s = (s or "").lower().strip()
    return s[:-4] if s.endswith(".pdf") else s


_PT_SUFFIX = re.compile(r"[A-Z]{2,5}DT\d{2,4}P(?:[_.]|$| )")   # MNDT250P, MFDT180P…
_FR_HINT = re.compile(r"manuel|_fr\b|\bfr\b", re.IGNORECASE)


def propose_b6(filename: str, chunks_in_old: int, dup_of: str | None) -> tuple[str, str]:
    """(status_propuesto, causa) para un doc sin chunks v2 (diseño A4, X3).

    retired SOLO con señal fuerte (duplicado-fantasma / descarte de política de
    idiomas verificable en el filename); el resto → needs_review (cola humana).
    """
    if chunks_in_old == 0 and dup_of:
        return "retired", f"duplicado-fantasma de {dup_of} (0 chunks en ambas tablas)"
    if chunks_in_old == 0:
        return "needs_review", "sin contenido en ninguna tabla (gap de ingesta / chunks borrados)"
    fn = filename or ""
    if _PT_SUFFIX.search(fn):
        return "retired", "no migrado a v2: portugués (sufijo P, política de idiomas)"
    if _FR_HINT.search(fn) and "manuel" in fn.lower():
        return "retired", "no migrado a v2: francés (política de idiomas)"
    return "needs_review", "contenido solo en tabla vieja — candidato a re-ingesta (cola punto 3)"


def mismatch_direction(doc_manu: str | None, chunks_moda: str | None,
                       unanime: bool, filename: str) -> tuple[str, str]:
    """(direccion, evidencia) para un mismatch documents↔chunks (diseño A2).

    'documents': la fila vieja pierde (default — backfill filename-heurístico).
    'chunks'   : los chunks están mal (excepción curada — keyword del filename
                 apoya al doc, p.ej. MAD565 es Detnov aunque chunks digan Spectrex).
    'curation' : sin evidencia suficiente — a tabla de curación.
    """
    kb = keyword_brand(filename)
    if kb and chunks_moda and kb.lower() == chunks_moda.lower():
        return "documents", f"filename apoya a chunks ({kb})"
    if kb and doc_manu and kb.lower() == doc_manu.lower():
        return "curation", f"filename apoya al DOC ({kb}) contra chunks — revisar"
    # Sin keyword de tercero: heurística por familia de código de filename
    fn = (filename or "").lower()
    detnov_code = re.search(r"\bm[a-z]d-?\d{3}|\bmi-\d{3}|\bcad-?\d{3}", fn)
    if detnov_code and doc_manu == "Detnov" and chunks_moda != "Detnov":
        return "curation", f"código Detnov en filename ({detnov_code.group(0)}) contra chunks — revisar"
    if not unanime:
        return "curation", "chunks no unánimes"
    return "documents", "default: backfill viejo pierde vs identidad data-driven de chunks"


# ============================================================================
# I/O helpers
# ============================================================================

def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def get(table: str, params: dict) -> list[dict]:
    r = httpx.get(f"{URL}/rest/v1/{table}", headers=H, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def get_paged(table: str, select: str, extra: dict | None = None) -> list[dict]:
    rows, offset = [], 0
    while True:
        params = {"select": select, "limit": "1000", "offset": str(offset)}
        if extra:
            params.update(extra)
        batch = get(table, params)
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        offset += 1000


def count_exact(table: str, filters: dict) -> int:
    params = {"select": "id", "limit": "1"}
    params.update(filters)
    r = httpx.get(f"{URL}/rest/v1/{table}",
                  headers={**H, "Prefer": "count=exact", "Range-Unit": "items",
                           "Range": "0-0"},
                  params=params, timeout=60)
    r.raise_for_status()
    cr = r.headers.get("content-range", "")
    return int(cr.split("/")[-1]) if "/" in cr else -1


def patch(table: str, filters: dict, body: dict) -> list[dict]:
    r = httpx.patch(f"{URL}/rest/v1/{table}",
                    headers={**H, "Prefer": "return=representation"},
                    params=filters, json=body, timeout=120)
    r.raise_for_status()
    return r.json()


def post(table: str, body: dict) -> list[dict]:
    r = httpx.post(f"{URL}/rest/v1/{table}",
                   headers={**H, "Prefer": "return=representation"},
                   json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def delete(table: str, filters: dict) -> None:
    r = httpx.delete(f"{URL}/rest/v1/{table}", headers=H, params=filters, timeout=60)
    r.raise_for_status()


def find_local_pdf(source_file: str) -> Path | None:
    for d in LOCAL_MANUAL_DIRS:
        p = d / f"{source_file}.pdf"
        if p.exists():
            return p
        hits = list(d.rglob(f"{source_file}.pdf"))
        if hits:
            return hits[0]
    return None


# ============================================================================
# inventory (read-only; congela poblaciones + plan)
# ============================================================================

def phase_inventory() -> int:
    inv: dict = {"ts": _now(), "git": _git(), "read_only": True}
    plan: dict = {"ts": _now(), "git": _git(),
                  "design": "evals/_s65_capab_design.md (v2)"}

    print("[1/6] dumps…")
    docs = get_paged("documents",
                     "id,source_pdf_filename,source_pdf_sha256,manufacturer,"
                     "product_model,revision,revision_date,language,document_family,"
                     "doc_type,status,notes")
    chunks = get_paged("chunks_v2",
                       "id,source_file,document_id,extraction_sha256,manufacturer,"
                       "product_model,language,doc_type")
    docs_by_id = {d["id"]: d for d in docs}
    inv["documents_total"] = len(docs)
    inv["chunks_total"] = len(chunks)

    # ---------------- A1: huérfanos B7 -------------------------------------
    print("[2/6] A1 backfill B7…")
    orphans = [c for c in chunks if not c["document_id"]]
    by_src: dict[str, list[dict]] = defaultdict(list)
    for c in orphans:
        by_src[c["source_file"]].append(c)

    # sanity F5: ¿algún sha de huérfano vive también en chunks YA enlazados?
    orphan_shas = {c["extraction_sha256"] for c in orphans}
    linked_shas = {c["extraction_sha256"] for c in chunks if c["document_id"]}
    sha_overlap = sorted(orphan_shas & linked_shas)
    inv["A1_sha_overlap_orphan_vs_linked"] = sha_overlap  # esperado []

    doc_by_norm_fname: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        doc_by_norm_fname[norm_fname(d["source_pdf_filename"])].append(d)
    doc_by_sha: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        sha = d.get("source_pdf_sha256") or ""
        if sha and not sha.startswith("backfill:"):
            doc_by_sha[sha].append(d)

    a1_link_existing, a1_insert, a1_curation = [], [], []
    for src in sorted(by_src):
        cs = by_src[src]
        sha = cs[0]["extraction_sha256"]
        manu, manu_unanime = consensus([c["manufacturer"] for c in cs])
        model, model_unanime = consensus([c["product_model"] for c in cs])
        kb = keyword_brand(src)
        local = find_local_pdf(src)
        rec = {
            "source_file": src, "n_chunks": len(cs), "extraction_sha256": sha,
            "manufacturer_moda": manu, "manufacturer_unanime": manu_unanime,
            "product_model_moda": model, "product_model_unanime": model_unanime,
            "keyword_brand": kb,
            "local_pdf": str(local.relative_to(ROOT)) if local else None,
            "revision_parsed": parse_revision(src),
        }
        # pre-casado F4: sha primero, luego filename (norm ±.pdf)
        sha_hits = doc_by_sha.get(sha, [])
        fname_hits = doc_by_norm_fname.get(norm_fname(src), [])
        if sha_hits:
            rec["match"] = {"by": "sha", "doc_id": sha_hits[0]["id"],
                            "n": len(sha_hits)}
            (a1_link_existing if len(sha_hits) == 1 else a1_curation).append(rec)
        elif fname_hits:
            rec["match"] = {"by": "filename", "doc_id": fname_hits[0]["id"],
                            "n": len(fname_hits),
                            "doc_sha_placeholder": (fname_hits[0].get("source_pdf_sha256")
                                                    or "").startswith("backfill:")}
            (a1_link_existing if len(fname_hits) == 1 else a1_curation).append(rec)
        elif not manu or not manu_unanime or (kb and kb.lower() != (manu or "").lower()):
            # NOT NULL manufacturer / no unánime / cross-check discrepante → curación
            rec["curation_reason"] = ("manufacturer NULL en chunks" if not manu else
                                      "no unánime" if not manu_unanime else
                                      f"keyword filename={kb} ≠ chunks={manu}")
            a1_curation.append(rec)
        else:
            a1_insert.append(rec)

    inv["A1_link_existing"] = a1_link_existing
    inv["A1_insert_n"] = len(a1_insert)
    inv["A1_curation"] = a1_curation
    inv["A1_residual_esperado"] = {
        "sources": len(a1_curation),
        "chunks": sum(r["n_chunks"] for r in a1_curation),
        "nota": "F13: sin curación resuelta quedan huérfanos (manufacturer NOT NULL)",
    }

    # ---------------- A2: mismatch doc↔chunks ------------------------------
    print("[3/6] A2 mismatch…")
    link: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        if c["document_id"]:
            link[c["document_id"]].append(c)
    a2 = []
    for did, cs in link.items():
        d = docs_by_id.get(did)
        if not d:
            continue
        moda, unanime = consensus([c["manufacturer"] for c in cs])
        if moda and d["manufacturer"] != moda:
            direction, evidence = mismatch_direction(
                d["manufacturer"], moda, unanime, d["source_pdf_filename"])
            model_moda, model_unanime = consensus([c["product_model"] for c in cs])
            a2.append({
                "doc_id": did, "filename": d["source_pdf_filename"],
                "doc_manufacturer": d["manufacturer"], "chunks_moda": moda,
                "chunks_unanime": unanime, "n_chunks": len(cs),
                "direction": direction, "evidence": evidence,
                "doc_model": d["product_model"],
                "chunks_model_moda": model_moda if model_unanime else None,
            })
    a2.sort(key=lambda r: (r["direction"], r["doc_manufacturer"] or "",
                           r["chunks_moda"] or ""))
    inv["A2_mismatch_total"] = len(a2)
    inv["A2_by_direction"] = dict(Counter(r["direction"] for r in a2))
    inv["A2_rows"] = a2

    # ---------------- A3: revision basura ----------------------------------
    print("[4/6] A3 revision…")
    a3 = [{"doc_id": d["id"], "filename": d["source_pdf_filename"],
           "revision": d["revision"]}
          for d in docs if d["revision"] in REV_GARBAGE_VALUES]
    inv["A3_total"] = len(a3)
    inv["A3_values"] = dict(Counter(r["revision"] for r in a3))

    # ---------------- A4: B6 (excluyendo docs que A1 enlaza — F1) ----------
    print("[5/6] A4 clasificación B6 (cross-check tabla vieja)…")
    linked_ids = {c["document_id"] for c in chunks if c["document_id"]}
    a1_linked_doc_ids = {r["match"]["doc_id"] for r in a1_link_existing}
    no_chunks = [d for d in docs
                 if d["id"] not in linked_ids and d["id"] not in a1_linked_doc_ids
                 and d["status"] == "active"]
    # duplicados de identidad: mismo norm_fname con otra fila
    a4 = []
    for i, d in enumerate(no_chunks):
        n_old = count_exact("chunks", {"document_id": f"eq.{d['id']}"})
        dups = [x for x in doc_by_norm_fname.get(norm_fname(d["source_pdf_filename"]), [])
                if x["id"] != d["id"]]
        dup_of = dups[0]["id"] if dups else None
        status, causa = propose_b6(d["source_pdf_filename"], n_old, dup_of)
        a4.append({"doc_id": d["id"], "filename": d["source_pdf_filename"],
                   "manufacturer": d["manufacturer"], "chunks_in_old": n_old,
                   "dup_of": dup_of, "status_propuesto": status, "causa": causa})
        if (i + 1) % 25 == 0:
            print(f"      {i + 1}/{len(no_chunks)}")
    inv["A4_total"] = len(a4)
    inv["A4_by_status"] = dict(Counter(r["status_propuesto"] for r in a4))
    inv["A4_rows"] = a4
    inv["A4_excluded_by_A1"] = sorted(a1_linked_doc_ids)

    # ---------------- A5: unknown dirigido en chunks ------------------------
    print("[6/6] A5 unknown dirigido…")
    unk = [c for c in chunks
           if c["document_id"] and (c["product_model"] or "").lower() in ("unknown", "")]
    a5_by_src = defaultdict(list)
    for c in unk:
        a5_by_src[c["source_file"]].append(c)
    a5 = [{"source_file": s, "n_chunks": len(cs),
           "manufacturer": consensus([c["manufacturer"] for c in cs])[0],
           "propuesta": "queda unknown (sin evidencia inequívoca en filename)"}
          for s, cs in sorted(a5_by_src.items())]
    inv["A5_sources"] = a5
    inv["A5_nota"] = ("diseño A5: solo modelo INEQUÍVOCO en filename y fuera de "
                      "pools — por defecto todo queda unknown honesto; cambios "
                      "puntuales requieren entrada explícita en el plan")

    F_INVENTORY.write_text(yaml.safe_dump(inv, allow_unicode=True, sort_keys=False,
                                          width=110), encoding="utf-8")

    # ---------------- PLAN (mutaciones exactas) -----------------------------
    plan["A1_link_existing"] = [
        {"doc_id": r["match"]["doc_id"], "source_file": r["source_file"],
         "extraction_sha256": r["extraction_sha256"], "expected_chunks": r["n_chunks"],
         "update_doc_sha_to_real": bool(r["match"].get("doc_sha_placeholder"))}
        for r in a1_link_existing]
    plan["A1_insert"] = [
        {"source_file": r["source_file"], "extraction_sha256": r["extraction_sha256"],
         "expected_chunks": r["n_chunks"],
         "row": {
             "document_family": norm_fname(r["source_file"]).replace("_", " ").replace("-", " "),
             "revision": r["revision_parsed"], "revision_date": None,
             "language": None, "doc_type": None,
             "manufacturer": r["manufacturer_moda"],
             "product_model": (r["product_model_moda"]
                               if r["product_model_unanime"] and r["product_model_moda"]
                               else "unknown"),
             "source_pdf_filename": r["source_file"] + ".pdf",
             "source_pdf_sha256": r["extraction_sha256"],
             "status": "active",
             "notes": "s65 capaB: backfill identidad lote s55/s58 (el pipeline de "
                      "ingesta no crea filas en documents; identidad = consenso de "
                      "chunks cross-checked, diseño v2 A1).",
         }} for r in a1_insert]
    plan["A1_curation_pendiente"] = [
        {"source_file": r["source_file"], "n_chunks": r["n_chunks"],
         "razon": r.get("curation_reason") or "match ambiguo",
         "manufacturer_moda": r["manufacturer_moda"], "keyword_brand": r["keyword_brand"],
         "local_pdf": r["local_pdf"]} for r in a1_curation]
    plan["A2_update_documents"] = [
        {"doc_id": r["doc_id"], "filename": r["filename"],
         "set": {"manufacturer": r["chunks_moda"],
                 **({"product_model": r["chunks_model_moda"]}
                    if (r["doc_model"] or "").lower() in ("unknown", "") and r["chunks_model_moda"]
                    else {})},
         "evidence": r["evidence"]}
        for r in a2 if r["direction"] == "documents"]
    plan["A2_curation_pendiente"] = [r for r in a2 if r["direction"] == "curation"]
    plan["A2_update_chunks_excepciones"] = []  # se puebla tras curación (gated precheck)
    plan["A3_revision_null"] = {"values": REV_GARBAGE_VALUES,
                                "doc_ids": [r["doc_id"] for r in a3]}
    plan["A4_status"] = [
        {"doc_id": r["doc_id"], "filename": r["filename"],
         "set_status": r["status_propuesto"],
         "append_note": f"s65 capaB A4: {r['causa']}"}
        for r in a4]
    plan["A5_update_chunks"] = []  # por defecto vacío (unknown honesto)
    F_PLAN.write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False,
                                     width=110), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"A1: enlazar {len(a1_link_existing)} | insertar {len(a1_insert)} | "
          f"curación {len(a1_curation)} (residual {inv['A1_residual_esperado']['chunks']} chunks)")
    print(f"    sha_overlap huérfanos×enlazados: {len(sha_overlap)} (esperado 0)")
    print(f"A2: mismatch {len(a2)} → {inv['A2_by_direction']}")
    print(f"A3: {len(a3)} docs basura en {len(inv['A3_values'])} valores")
    print(f"A4: {len(a4)} docs → {inv['A4_by_status']} (excluidos por A1: {len(a1_linked_doc_ids)})")
    print(f"A5: {len(a5)} sources quedan unknown (por defecto)")
    print(f"→ {F_INVENTORY}\n→ {F_PLAN}")
    return 0


# ============================================================================
# pools (before / after) — firma EN ORDEN DEL POOL (F10)
# ============================================================================

def _light(c: dict) -> dict:
    return {"id": c.get("id"), "source_file": c.get("source_file"),
            "product_model": c.get("product_model"),
            "document_id": c.get("document_id"),
            "similarity": c.get("similarity")}


def _run_pools() -> dict[str, list[dict]]:
    import gold_store
    from src.rag.retriever import retrieve_chunks
    golds = {g["qid"]: g for g in gold_store.dev()}
    pools = {}
    for qid in sorted(golds):
        pools[qid] = retrieve_chunks(golds[qid]["question"], top_k=50)
        print(f"  {qid}: n={len(pools[qid])}")
    return pools


def _known_manufacturers_snapshot() -> list[str]:
    """Diagnóstico F9b: la lista que alimenta _diversify_by_manufacturer."""
    try:
        from src.rag.retriever import _get_all_known_manufacturers
        return list(_get_all_known_manufacturers())
    except Exception as e:
        return [f"ERROR: {e}"]


def _plan_sources() -> set[str]:
    """Sources cuyo cambio puede tocar pools (A1 enlaces/inserts + A2-chunks + A5)."""
    if not F_PLAN.exists():
        sys.exit("falta s65_capab_plan.yaml — corre --phase inventory primero")
    plan = yaml.safe_load(F_PLAN.read_text(encoding="utf-8"))
    src = {r["source_file"] for r in plan.get("A1_link_existing", [])}
    src |= {r["source_file"] for r in plan.get("A1_insert", [])}
    src |= {r.get("source_file") for r in plan.get("A2_update_chunks_excepciones", [])
            if r.get("source_file")}
    src |= {r.get("source_file") for r in plan.get("A5_update_chunks", [])
            if r.get("source_file")}
    return src


def phase_before() -> int:
    print(f"pools BEFORE | git={_git()} | cache={os.environ['EMBED_CACHE_PATH']}")
    sources = _plan_sources()
    pools = _run_pools()
    afectados = {}
    for qid, pool in pools.items():
        hits = sorted({c.get("source_file") for c in pool
                       if c.get("source_file") in sources})
        if hits:
            afectados[qid] = hits
    data = {
        "ts": _now(), "git": _git(), "phase": "before",
        "known_manufacturers": _known_manufacturers_snapshot(),
        "afectados_esperados": afectados,
        "pools": {qid: {"n": len(p),
                        "firma": [[c.get("source_file"), c.get("id")] for c in p],
                        "pool": [_light(c) for c in p]} for qid, p in pools.items()},
    }
    F_BEFORE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"afectados esperados: {json.dumps(afectados, indent=1, ensure_ascii=False)}")
    print(f"known_manufacturers: {len(data['known_manufacturers'])}")
    print(f"→ {F_BEFORE}")
    return 0


# ============================================================================
# apply — ejecuta el PLAN congelado (orden F1; before-values F3/X4)
# ============================================================================

def phase_apply() -> int:
    if F_APPLY.exists():
        sys.exit(f"{F_APPLY} ya existe — apply ya corrió (usa rollback primero).")
    if not F_PLAN.exists():
        sys.exit("falta s65_capab_plan.yaml — corre --phase inventory primero")
    plan = yaml.safe_load(F_PLAN.read_text(encoding="utf-8"))
    log: dict = {"ts": _now(), "git": _git(), "plan_ts": plan["ts"], "steps": []}

    def step(name: str, detail: dict) -> None:
        log["steps"].append({"step": name, **detail})
        print(f"  ✓ {name}: {json.dumps(detail, ensure_ascii=False)[:150]}")

    def _save(result: str) -> None:
        log["result"] = result
        F_APPLY.write_text(yaml.safe_dump(log, allow_unicode=True, sort_keys=False,
                                          width=110), encoding="utf-8")

    try:
        # ---- A1a: enlazar a filas EXISTENTES --------------------------------
        for r in plan.get("A1_link_existing", []):
            if r.get("update_doc_sha_to_real"):
                before = get("documents", {"select": "id,source_pdf_sha256",
                                           "id": f"eq.{r['doc_id']}"})[0]
                patch("documents", {"id": f"eq.{r['doc_id']}", "select": "id"},
                      {"source_pdf_sha256": r["extraction_sha256"]})
                step("doc_sha_real", {"doc_id": r["doc_id"],
                                      "before": before["source_pdf_sha256"]})
            rows = patch("chunks_v2",
                         {"extraction_sha256": f"eq.{r['extraction_sha256']}",
                          "document_id": "is.null", "select": "id"},
                         {"document_id": r["doc_id"]})
            assert len(rows) == r["expected_chunks"], \
                f"{r['source_file']}: {len(rows)} != {r['expected_chunks']}"
            step("link_existing", {"doc_id": r["doc_id"],
                                   "extraction_sha256": r["extraction_sha256"],
                                   "n": len(rows)})

        # ---- A1b: INSERT filas nuevas + enlace ------------------------------
        for r in plan.get("A1_insert", []):
            new_id = str(uuid.uuid4())
            created = post("documents", {"id": new_id, **r["row"]})
            assert len(created) == 1 and created[0]["id"] == new_id, created
            back = get("documents", {"select": "id,status,manufacturer",
                                     "id": f"eq.{new_id}"})
            assert back and back[0]["status"] == "active", back
            step("insert_doc", {"id": new_id, "source_file": r["source_file"]})
            rows = patch("chunks_v2",
                         {"extraction_sha256": f"eq.{r['extraction_sha256']}",
                          "document_id": "is.null", "select": "id"},
                         {"document_id": new_id})
            assert len(rows) == r["expected_chunks"], \
                f"{r['source_file']}: {len(rows)} != {r['expected_chunks']}"
            step("link_new", {"document_id": new_id,
                              "extraction_sha256": r["extraction_sha256"],
                              "n": len(rows)})
            # Curación A1 (canal "Otros"): chunks con manufacturer NULL ganan
            # la marca curada (gated por precheck — diseño §3.3).
            if r.get("set_chunks_manufacturer"):
                rows = patch("chunks_v2",
                             {"extraction_sha256": f"eq.{r['extraction_sha256']}",
                              "manufacturer": "is.null", "select": "id"},
                             {"manufacturer": r["set_chunks_manufacturer"]})
                step("a1_chunks_manufacturer",
                     {"extraction_sha256": r["extraction_sha256"], "n": len(rows),
                      "to": r["set_chunks_manufacturer"], "before": None})

        # ---- ASSERT F1: la población B6 recomputada == la planificada -------
        linked_now = set()
        offset = 0
        while True:
            page = get("chunks_v2", {"select": "document_id",
                                     "document_id": "not.is.null",
                                     "limit": "1000", "offset": str(offset)})
            linked_now |= {x["document_id"] for x in page}
            if len(page) < 1000:
                break
            offset += 1000
        planned_a4 = {r["doc_id"] for r in plan.get("A4_status", [])}
        bad = planned_a4 & linked_now
        assert not bad, f"F1 VIOLADO: {len(bad)} docs de A4 tienen chunks v2: {sorted(bad)[:5]}"
        step("assert_b6_recompute", {"a4_planificados": len(planned_a4),
                                     "con_chunks_v2": 0})

        # ---- A4: status (before-values por fila) ----------------------------
        for r in plan.get("A4_status", []):
            before = get("documents", {"select": "id,status,notes",
                                       "id": f"eq.{r['doc_id']}"})[0]
            new_notes = ((before.get("notes") or "").rstrip()
                         + (" | " if before.get("notes") else "") + r["append_note"])
            rows = patch("documents", {"id": f"eq.{r['doc_id']}", "select": "id,status"},
                         {"status": r["set_status"], "notes": new_notes})
            assert len(rows) == 1 and rows[0]["status"] == r["set_status"], rows
            step("a4_status", {"doc_id": r["doc_id"], "to": r["set_status"],
                               "before_status": before["status"],
                               "before_notes": before.get("notes")})

        # ---- A3: revision basura → NULL --------------------------------------
        for r in plan.get("A3_revision_null", {}).get("doc_ids", []):
            before = get("documents", {"select": "id,revision", "id": f"eq.{r}"})[0]
            rows = patch("documents", {"id": f"eq.{r}", "select": "id"},
                         {"revision": None})
            assert len(rows) == 1, rows
            step("a3_revision_null", {"doc_id": r, "before_revision": before["revision"]})

        # ---- A2: documents.manufacturer (+model si unknown) ------------------
        for r in plan.get("A2_update_documents", []):
            before = get("documents", {"select": "id,manufacturer,product_model",
                                       "id": f"eq.{r['doc_id']}"})[0]
            rows = patch("documents", {"id": f"eq.{r['doc_id']}", "select": "id,manufacturer"},
                         r["set"])
            assert len(rows) == 1 and rows[0]["manufacturer"] == r["set"]["manufacturer"], rows
            step("a2_documents", {"doc_id": r["doc_id"], "set": r["set"],
                                  "before": {"manufacturer": before["manufacturer"],
                                             "product_model": before["product_model"]}})

        # ---- A2-chunks excepciones / A5 (vacíos salvo curación explícita) ---
        for r in plan.get("A2_update_chunks_excepciones", []):
            before_rows = get("chunks_v2", {"select": "id,manufacturer",
                                            "source_file": f"eq.{r['source_file']}",
                                            "limit": "1000"})
            rows = patch("chunks_v2", {"source_file": f"eq.{r['source_file']}",
                                       "select": "id"},
                         {"manufacturer": r["set_manufacturer"]})
            step("a2_chunks", {"source_file": r["source_file"], "n": len(rows),
                               "before_manufacturer": before_rows[0]["manufacturer"]
                               if before_rows else None,
                               "to": r["set_manufacturer"]})
        for r in plan.get("A5_update_chunks", []):
            before_rows = get("chunks_v2", {"select": "id,product_model",
                                            "source_file": f"eq.{r['source_file']}",
                                            "limit": "1000"})
            rows = patch("chunks_v2", {"source_file": f"eq.{r['source_file']}",
                                       "select": "id"},
                         {"product_model": r["set_product_model"]})
            step("a5_chunks", {"source_file": r["source_file"], "n": len(rows),
                               "before_product_model": before_rows[0]["product_model"]
                               if before_rows else None,
                               "to": r["set_product_model"]})

        # ---- INVARIANTE del ciclo (scoped a s65): ningún doc QUE ESTE PLAN
        # marcó inactivo (A4 = docs sin contenido) tiene chunks v2. Los
        # inactivos PRE-existentes (3 superseded s64 + 5 needs_review Morley)
        # tienen chunks v2 POR CONTRATO — la exclusión del #46 es en runtime,
        # no des-enlace (1ª versión global de este assert = falso STOP, 12-jun).
        viol = []
        for r in plan.get("A4_status", []):
            if count_exact("chunks_v2", {"document_id": f"eq.{r['doc_id']}"}) > 0:
                viol.append(r["doc_id"])
        assert not viol, f"INVARIANTE VIOLADO: docs de A4 con chunks v2: {viol}"
        step("assert_invariante", {"docs_a4": len(plan.get("A4_status", [])),
                                   "con_chunks_v2": 0})

        _save("OK")
    except Exception as e:
        _save(f"FAILED: {type(e).__name__}: {e}")
        print(f"\nAPPLY FALLÓ — log parcial en {F_APPLY}; --phase rollback deshace.")
        raise

    print(f"apply OK → {F_APPLY}")
    return 0


# ============================================================================
# after — comparación + veredicto
# ============================================================================

def phase_after() -> int:
    if not F_BEFORE.exists():
        sys.exit("falta s65_pools_before.json — corre --phase before primero")
    before = json.loads(F_BEFORE.read_text(encoding="utf-8"))
    sources = _plan_sources()

    print(f"pools AFTER | git={_git()} | cache={os.environ['EMBED_CACHE_PATH']}")
    pools = _run_pools()
    known_after = _known_manufacturers_snapshot()

    import gold_store
    from src.rag.retriever import retrieve_chunks
    golds = {g["qid"]: g for g in gold_store.dev()}

    def firma(pool: list[dict]) -> list[list]:
        return [[c.get("source_file"), c.get("id")] for c in pool]

    afectados_esperados = set(before["afectados_esperados"].keys())
    reclasificados, clasificacion = {}, {}
    for qid in sorted(pools):
        f_b, f_a = before["pools"][qid]["firma"], firma(pools[qid])
        if f_a == f_b:
            clasificacion[qid] = "identico"
            continue
        # convergencia anti-dado-de-red (patrón s64): re-run
        p2 = retrieve_chunks(golds[qid]["question"], top_k=50)
        if firma(p2) == f_b:
            pools[qid] = p2
            reclasificados[qid] = "dado-de-red (re-run convergió a before)"
            clasificacion[qid] = "identico"
            continue
        pools[qid] = p2
        f_a = firma(p2)
        ids_b, ids_a = {tuple(x) for x in f_b}, {tuple(x) for x in f_a}
        clasificacion[qid] = "orden_cambiado" if ids_b == ids_a else "composicion_cambiada"

    data = {
        "ts": _now(), "git": _git(), "phase": "after",
        "known_manufacturers": known_after,
        "reclasificados": reclasificados,
        "pools": {qid: {"n": len(p), "firma": firma(p),
                        "pool": [_light(c) for c in p]} for qid, p in pools.items()},
    }
    F_AFTER.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    verdict: dict = {"ts": _now(), "git": _git(),
                     "design": "evals/_s65_capab_design.md (v2)", "criterios": {}}

    # C-IDENT: no-afectados idénticos en firma (orden incluido, F10)
    c_viol = {}
    for qid, cls in clasificacion.items():
        if cls == "identico" or qid in afectados_esperados:
            continue
        f_b = before["pools"][qid]["firma"]
        f_a = data["pools"][qid]["firma"]
        in_new = [x for x in {tuple(t) for t in f_a} - {tuple(t) for t in f_b}]
        entradas_de_sources_plan = [x for x in in_new if x[0] in sources]
        c_viol[qid] = {
            "clase": cls,
            "entraron": len(in_new), "salieron": len({tuple(t) for t in f_b}
                                                     - {tuple(t) for t in f_a}),
            "entradas_de_sources_del_plan": len(entradas_de_sources_plan),
            "decision_predeclarada": ("explicar chunk a chunk (F9a-i; GRIS-Alberto si "
                                      "toca top-N servido de PASS-control)"
                                      if entradas_de_sources_plan and
                                      len(entradas_de_sources_plan) == len(in_new)
                                      else "STOP instrumento (F9a-ii)"),
        }
    verdict["criterios"]["C_no_afectados_identicos"] = {
        "pass": not c_viol, "violaciones": c_viol,
        "reclasificados_dado_red": reclasificados}

    # afectados esperados: diff para revisión
    diff_af = {}
    for qid in sorted(afectados_esperados):
        f_b = before["pools"][qid]["firma"]
        f_a = data["pools"][qid]["firma"]
        diff_af[qid] = {"clase": clasificacion[qid],
                        "before_n": len(f_b), "after_n": len(f_a),
                        "sources_esperados": before["afectados_esperados"][qid]}
    verdict["afectados_diff"] = diff_af

    # diagnóstico F9b
    verdict["known_manufacturers_diff"] = {
        "before": before.get("known_manufacturers"),
        "after": known_after,
        "igual": before.get("known_manufacturers") == known_after,
    }

    # invariante (scoped a s65: docs A4 sin chunks v2 — los inactivos
    # pre-existentes tienen chunks POR CONTRATO #46) + fingerprint
    plan = yaml.safe_load(F_PLAN.read_text(encoding="utf-8"))
    viol = [r["doc_id"] for r in plan.get("A4_status", [])
            if count_exact("chunks_v2", {"document_id": f"eq.{r['doc_id']}"}) > 0]
    verdict["invariante_a4_sin_chunks_v2"] = {"pass": not viol, "violaciones": viol}

    all_status: list[str] = []
    offset = 0
    while True:
        page = get("documents", {"select": "status", "limit": "1000", "offset": str(offset)})
        all_status.extend(r["status"] for r in page)
        if len(page) < 1000:
            break
        offset += 1000
    n_orphan = count_exact("chunks_v2", {"document_id": "is.null"})
    verdict["fingerprint"] = {"documents_status": dict(Counter(all_status)),
                              "chunks_orphan_restantes": n_orphan}

    all_pass = (verdict["criterios"]["C_no_afectados_identicos"]["pass"]
                and verdict["invariante_a4_sin_chunks_v2"]["pass"])
    verdict["verdict"] = ("GO (no-afectados idénticos + invariante; revisar diff de "
                          "afectados esperados)" if all_pass else
                          "REVISAR — violaciones con decisión pre-declarada arriba")
    F_REPORT.write_text(yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False,
                                       width=110), encoding="utf-8")
    print(yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False, width=110))
    print(f"→ {F_REPORT}")
    return 0 if all_pass else 1


# ============================================================================
# smoke — path real (diseño §2.4)
# ============================================================================

SMOKE_QUERIES = [
    ("aritech_2xa", "¿Cómo conecto las sirenas en una central 2X-A de Aritech?"),
    ("cad201", "¿Cómo accedo al menú de programación de la central CAD-201?"),
    ("control_notifier", "¿Qué pasos sigo para anular un detector en una central AM-8200?"),
]


def phase_smoke() -> int:
    from src.rag.retriever import retrieve_chunks, get_available_manufacturers
    from src.rag.generator import generate_answer

    print("=== catálogo de fabricantes (F8) ===")
    mfrs = get_available_manufacturers()
    print(f"  {len(mfrs)}: {', '.join(mfrs)}")

    for tag, q in SMOKE_QUERIES:
        print(f"\n=== smoke {tag}: {q}")
        chunks = retrieve_chunks(q, top_k=50)
        top = chunks[:5]
        for c in top:
            print(f"  - {c.get('source_file')} | model={c.get('product_model')} "
                  f"| doc={str(c.get('document_id'))[:8]} | rev={c.get('document_revision')}")
        result = generate_answer(q, top)
        answer = result.get("answer") if isinstance(result, dict) else str(result)
        print(f"  → {answer[:400]}")
    return 0


# ============================================================================
# rollback — reversed(steps) + before-values (F3/X4)
# ============================================================================

def phase_rollback() -> int:
    if not F_APPLY.exists():
        sys.exit("no hay s65_apply_log.yaml — nada que deshacer")
    log = yaml.safe_load(F_APPLY.read_text(encoding="utf-8"))
    for s in reversed(log.get("steps", [])):
        name = s["step"]
        if name in ("assert_b6_recompute", "assert_invariante"):
            continue
        if name == "a5_chunks":
            patch("chunks_v2", {"source_file": f"eq.{s['source_file']}", "select": "id"},
                  {"product_model": s["before_product_model"]})
        elif name == "a2_chunks":
            patch("chunks_v2", {"source_file": f"eq.{s['source_file']}", "select": "id"},
                  {"manufacturer": s["before_manufacturer"]})
        elif name == "a2_documents":
            patch("documents", {"id": f"eq.{s['doc_id']}", "select": "id"}, s["before"])
        elif name == "a3_revision_null":
            patch("documents", {"id": f"eq.{s['doc_id']}", "select": "id"},
                  {"revision": s["before_revision"]})
        elif name == "a4_status":
            patch("documents", {"id": f"eq.{s['doc_id']}", "select": "id"},
                  {"status": s["before_status"], "notes": s["before_notes"]})
        elif name == "a1_chunks_manufacturer":
            patch("chunks_v2", {"extraction_sha256": f"eq.{s['extraction_sha256']}",
                                "manufacturer": f"eq.{s['to']}", "select": "id"},
                  {"manufacturer": s["before"]})
        elif name == "link_new":
            patch("chunks_v2", {"extraction_sha256": f"eq.{s['extraction_sha256']}",
                                "document_id": f"eq.{s['document_id']}", "select": "id"},
                  {"document_id": None})
        elif name == "insert_doc":
            delete("documents", {"id": f"eq.{s['id']}"})
        elif name == "link_existing":
            patch("chunks_v2", {"extraction_sha256": f"eq.{s['extraction_sha256']}",
                                "document_id": f"eq.{s['doc_id']}", "select": "id"},
                  {"document_id": None})
        elif name == "doc_sha_real":
            patch("documents", {"id": f"eq.{s['doc_id']}", "select": "id"},
                  {"source_pdf_sha256": s["before"]})
        print(f"  ✓ undo {name}")
    F_APPLY.rename(F_APPLY.with_suffix(".rolledback.yaml"))
    print("rollback completo — apply_log renombrado .rolledback.yaml")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["inventory", "before", "apply", "after", "smoke", "rollback"])
    args = ap.parse_args()
    return {"inventory": phase_inventory, "before": phase_before,
            "apply": phase_apply, "after": phase_after, "smoke": phase_smoke,
            "rollback": phase_rollback}[args.phase]()


if __name__ == "__main__":
    sys.exit(main())
