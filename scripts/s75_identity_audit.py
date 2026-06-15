#!/usr/bin/env python3
"""s75_identity_audit.py — AUDIT read-only de la RAÍZ DE DATOS de identidad (DEC-054 / TECH_DEBT #49).

Gate/audit-PRIMERO (Protocolo 4; DEC-005/019): Alberto eligió "audit-first, luego
decidir" para s75. El objetivo es MEDIR, no especular, las dos dimensiones que la
decisión build/defer/pivote del detector necesita:

  PARTE 1 — ESCALA del problema de datos en chunks_v2 (lo que justifica el detector
            como prep-de-escala F2):
     A) pm COMPUESTO (etiqueta multi-modelo literal: 'AM2020/AFP1010', 'ID50/60',
        'ZX2e/ZX5e') — docs/chunks/fabricantes afectados.
     B) MIS-ATRIBUCIÓN proxy (la firma de cat013): docs cuyo source_pdf_filename
        nombra un modelo que NO está en su product_model asignado → el filtro de
        retrieval (_filter_to_query_models, substring) los expulsa en la query de
        ese modelo. Raíz: _detect_model elige el modelo más-frecuente/prefijo
        (metadata.py:109-118), no el real.
     C) METADATA-INCONSISTENCY (mismo producto, N etiquetas): cores normalizados
        con ≥2 labels crudas distintas (ID200/ID-200, Pearl/PEARL). NO config-fixable.

  PARTE 2 — PALANCA EVAL real del detector (el cruce decisivo). Clasifica los golds
     de retrieval (s71 track2 diag) por el FIX que de verdad los mueve, separando:
       - lever1_pool_starvation     (broad-fallback/frontier/diversify → Lever 1)
       - config_seam_identity       (e-series, Brazo A YA construido — NO el detector)
       - detector_mis_attribution   (la raíz de datos: solo cat013, y Lever-1-gated)
       - keyword / rerank / gen / corpus  (otros)
     → tally del NET attribuible al DETECTOR (hipótesis: ≈0, confirma DEC-054).

Todo read-only. Salida: evals/s75_identity_audit.yaml + resumen por consola.
Uso:    python scripts/s75_identity_audit.py
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))

from src.reingest.manufacturer_registry import GENERIC_MODEL_RE  # noqa: E402
from src.rag.series_registry import normalize_model  # noqa: E402
from src.rag import catalog as _catalog  # noqa: E402  (árbitro catalog-first, DEC-054)

URL = os.environ["SUPABASE_URL"]
H = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
     "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

OUT = ROOT / "evals" / "s75_identity_audit.yaml"
CHUNKS_TABLE = "chunks_v2"

# Separadores que delatan un pm compuesto literal (dos modelos en una etiqueta).
_COMPOSITE_SEP = re.compile(r"[/+&]|,\s|\s,| y | & ", re.IGNORECASE)

# Códigos de DOCUMENTO del editor (Notifier/Morley "_DT_" = Documentación Técnica:
# MNDT/MPDT/MADT/MIDT/MCDT/MFDT/MUDT/TIDT/TGDT-###). El catálogo los heredó como
# pseudo-modelos (circularidad DEC-054); se excluyen para aislar mis-atribución REAL.
_DOC_CODE = re.compile(r"^[mt][a-z]{0,2}dt\d")


def is_doc_code(token: str) -> bool:
    nk = normalize_model(token)
    return bool(_DOC_CODE.match(nk)) or len(nk) < 3


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def fetch_all(table: str, select: str, page: int = 1000) -> list[dict]:
    rows, offset = [], 0
    with httpx.Client(timeout=60.0) as c:
        while True:
            r = c.get(f"{URL}/rest/v1/{table}", headers=H,
                      params={"select": select, "limit": str(page), "offset": str(offset)})
            r.raise_for_status()
            batch = r.json()
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page


def model_tokens(text: str) -> list[str]:
    """Modelos detectados en `text` con el MISMO regex que la ingesta (_detect_model)."""
    out = [f"{m[0]}-{m[1]}{m[2]}" for m in GENERIC_MODEL_RE.findall((text or "").upper())]
    # dedup preservando orden
    seen, uniq = set(), []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def is_composite_pm(pm: str) -> bool:
    """Etiqueta multi-modelo literal: separador explícito o ≥2 tokens-modelo distintos."""
    if not pm:
        return False
    if _COMPOSITE_SEP.search(pm):
        return True
    toks = model_tokens(pm)
    # ≥2 cores normalizados distintos en la MISMA etiqueta (p.ej. 'AM2020 AFP1010')
    return len({normalize_model(t) for t in toks}) >= 2


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("1) documents (identidad a nivel-doc)…")
    docs = fetch_all("documents",
                     "id,source_pdf_filename,manufacturer,product_model,document_family,status")
    print(f"   {len(docs)} docs")

    print("2) chunks (product_model a nivel-chunk + conteo)…")
    chunks = fetch_all(CHUNKS_TABLE, "id,document_id,product_model,manufacturer,source_file")
    print(f"   {len(chunks)} chunks")

    chunks_by_doc: dict[str, int] = Counter(c.get("document_id") for c in chunks)

    # ---- PARTE 1A: pm COMPUESTO ------------------------------------------------
    print("3) Parte 1A — pm compuesto…")
    comp_docs, comp_by_mfr, comp_examples = [], Counter(), []
    comp_chunks = 0
    for d in docs:
        pm = d.get("product_model") or ""
        if is_composite_pm(pm):
            mfr = d.get("manufacturer") or "?"
            nch = chunks_by_doc.get(d["id"], 0)
            comp_docs.append(d["id"])
            comp_by_mfr[mfr] += 1
            comp_chunks += nch
            if len(comp_examples) < 40:
                comp_examples.append({"mfr": mfr, "pm": pm,
                                      "file": d.get("source_pdf_filename"), "n_chunks": nch})
    # también a nivel-chunk (por si el pm-compuesto vive en chunks de docs no contados)
    comp_chunk_pms = Counter(c.get("product_model") for c in chunks
                             if is_composite_pm(c.get("product_model") or ""))

    # ---- PARTE 1B: MIS-ATRIBUCIÓN proxy (firma cat013) -------------------------
    # DOS pasadas: (raw) regex genérico = SOBRE-CUENTA porque parsea códigos de
    # manual (MNDT-430) como modelos; (refined) usa el EXTRACTOR DE CATÁLOGO
    # (catalog-first, DEC-054) que solo reconoce modelos reales → descarta los
    # códigos de documento. El número de titular es el REFINED.
    cat_ok = _catalog.catalog_available()
    print(f"4) Parte 1B — mis-atribución (catálogo disponible={cat_ok})…")
    misattr, misattr_by_mfr = [], Counter()          # raw (regex, contaminado)
    misattr_chunks = 0
    ref, ref_by_mfr = [], Counter()                  # refined (catálogo)
    ref_chunks = 0
    for d in docs:
        pm = d.get("product_model") or ""
        fname = d.get("source_pdf_filename") or ""
        if not pm or not fname:
            continue
        pm_norm = normalize_model(pm)
        mfr = d.get("manufacturer") or "?"
        nch = chunks_by_doc.get(d["id"], 0)

        # (raw) regex genérico
        ftoks = model_tokens(fname)
        if ftoks and not any(normalize_model(t) in pm_norm or pm_norm in normalize_model(t)
                             for t in ftoks):
            misattr_by_mfr[mfr] += 1
            misattr_chunks += nch
            misattr.append({"mfr": mfr, "pm_asignado": pm,
                            "file": fname, "tokens_en_filename": ftoks, "n_chunks": nch})

        # (refined) modelos RECONOCIDOS por el catálogo, EXCLUYENDO códigos de documento
        if cat_ok:
            cat_models = [m for m in _catalog.extract_models(fname.replace("_", " "))
                          if not is_doc_code(m)]
            uncovered = [m for m in cat_models
                         if normalize_model(m) not in pm_norm and pm_norm not in normalize_model(m)]
            if uncovered:
                ref_by_mfr[mfr] += 1
                ref_chunks += nch
                ref.append({"mfr": mfr, "pm_asignado": pm, "file": fname,
                            "modelos_catalogo_en_filename": uncovered, "n_chunks": nch})

    # ---- PARTE 1C: METADATA-INCONSISTENCY (mismo core, N labels) ---------------
    print("5) Parte 1C — metadata-inconsistency (mismo core normalizado, ≥2 labels)…")
    labels_by_core: dict[tuple[str, str], set[str]] = defaultdict(set)
    for d in docs:
        pm = d.get("product_model") or ""
        if not pm:
            continue
        labels_by_core[(d.get("manufacturer") or "?", normalize_model(pm))].add(pm)
    inconsist = [{"mfr": mfr, "core": core, "labels": sorted(labs)}
                 for (mfr, core), labs in labels_by_core.items()
                 if len(labs) >= 2 and core]
    inconsist.sort(key=lambda x: (-len(x["labels"]), x["mfr"]))

    # ---- PARTE 2: cruce eval (el tally decisivo) ------------------------------
    # Clasificación per-gold del FIX que de verdad mueve cada NO-PASS de retrieval.
    # Fuente: s71_track2_retrieval_diag.yaml (donde_muere) + correcciones verificadas:
    #   - hp009/hp018: el fix es CONFIG (e-series en morley.yaml, Brazo A) — NO el detector. [DEC-053/055, morley.yaml verificado s75]
    #   - cat013: donde_muere=model-filter PERO s72 verify-first = los chunks SDX-751 no
    #     entran al pool (broad-fallback capado a 5) → bloqueado en Lever 1; el pm-rescue
    #     (detector-adjacent) solo cobra DESPUÉS de Lever 1. [DEC-052/053]
    print("6) Parte 2 — cruce eval (palanca real del detector)…")
    GOLD_FIX = {
        # lever1_pool_starvation: el chunk no entra al pool (broad-fallback/frontier/diversify)
        "cat016": ("lever1_pool_starvation", "keyword order+limit; donde_muere=merge, not in pool50"),
        "hp013":  ("lever1_pool_starvation", "broad-fallback 5→50; merge, not in pool50"),
        "hp008":  ("lever1_pool_starvation", "broad-fallback 5→50; s74 gate-0 STRONG"),
        "hp002":  ("lever1_pool_starvation", "broad-fallback 5→50 (frontier k>50); s74 gate-0 STRONG"),
        "cat001": ("lever1_pool_starvation", "diversify supplement; merge"),
        "cat007": ("lever1_pool_starvation", "broad-fallback 5→50; stamps-dedup"),
        "hp001":  ("lever1_pool_starvation", "diversify within-doc; frontier k>50"),
        "hp011":  ("lever1_pool_starvation", "vector deepening 51-80; frontier k>50"),
        "cat017": ("lever1_pool_starvation", "vector-floor; stamps-dedup-pisa (merge)"),
        # config_seam_identity: arreglado por config (e-series), Brazo A YA construido — NO el detector
        "hp009":  ("config_seam_identity", "alias ZXe→[ZX2e,ZX5e] en morley.yaml (Brazo A, DEC-053); compound w/ pool starvation"),
        "hp018":  ("config_seam_identity", "series: e-series en morley.yaml (Brazo A, DEC-053)"),
        # detector_mis_attribution: LA raíz de datos del detector — pero Lever-1-gated
        "cat013": ("detector_mis_attribution_lever1_gated",
                   "SDX-751→LOCAL-360 mis-attribution; pm-rescue NO-OP hasta Lever 1 (s72 verify, DEC-052/053)"),
        # otros mecanismos (no el detector, no lever1 puro)
        "hp006":  ("keyword", "keyword-strip de tokens de identidad antes del cap [:3] (Lever C, diferido)"),
        "hp003":  ("rerank", "RERANK_PREVIEW_CHARS 800→2400 (Lever 1 batch 2c)"),
        "hp017":  ("corpus_gap", "section-sibling rescue (TECH_DEBT #48)"),
        "cat008": ("generation", "conflicto entre 2 fuentes servidas; NO retrieval-fixable"),
        "cat021": ("diversify", "variant-aware diversify (diferido)"),
    }
    bucket_tally = Counter(v[0] for v in GOLD_FIX.values())
    detector_net = [g for g, v in GOLD_FIX.items()
                    if v[0].startswith("detector_mis_attribution")]

    out = {
        "meta": {
            "at": _now(), "git": _git(), "corpus": CHUNKS_TABLE,
            "proposito": "audit-first DEC-054: medir escala (parte 1) y palanca eval (parte 2) "
                         "del detector de identidad ANTES de decidir build/defer/pivote",
            "metodo": {
                "pm_compuesto": "separador literal [/+&,] o ≥2 cores-modelo distintos (GENERIC_MODEL_RE) en la etiqueta",
                "mis_atribucion": "filename nombra ≥1 token-modelo cuyo core NO está en el product_model asignado (firma cat013, como el filtro substring)",
                "metadata_inconsistency": "mismo core normalize_model(pm) con ≥2 labels crudas distintas",
                "parte2": "clasificación per-gold del fix real (s71 track2 + correcciones verificadas hp009/hp018=config, cat013=lever1-gated)",
            },
            "totales": {"documents": len(docs), "chunks": len(chunks)},
        },
        "parte1_escala": {
            "A_pm_compuesto": {
                "n_docs": len(comp_docs),
                "n_chunks": comp_chunks,
                "por_fabricante": dict(comp_by_mfr.most_common()),
                "pms_compuestos_distintos_nivel_chunk": len(comp_chunk_pms),
                "ejemplos": comp_examples,
            },
            "B_mis_atribucion": {
                "refined_catalog_first": {
                    "n_docs": len(ref),
                    "n_chunks": ref_chunks,
                    "por_fabricante": dict(ref_by_mfr.most_common()),
                    "nota": "titular: filename nombra un modelo RECONOCIDO por el catálogo (587) ausente del product_model — firma cat013 (SDX-751). Catalog-first (DEC-054), no el índice.",
                    "ejemplos": ref[:60],
                },
                "raw_regex_CONTAMINADO": {
                    "n_docs": len(misattr),
                    "n_chunks": misattr_chunks,
                    "por_fabricante": dict(misattr_by_mfr.most_common()),
                    "nota": "SOBRE-CUENTA: el regex genérico parsea códigos de manual (MNDT-430, MPDT-280) como modelos. NO usar como cifra de escala — solo referencia.",
                },
            },
            "C_metadata_inconsistency": {
                "n_clusters": len(inconsist),
                "ejemplos": inconsist[:60],
            },
        },
        "parte2_palanca_eval": {
            "buckets": dict(bucket_tally),
            "detector_net_golds": detector_net,
            "lectura": (
                "NET atribuible al DETECTOR de datos = los golds en "
                "'detector_mis_attribution_*'. hp009/hp018 son CONFIG (Brazo A, ya construido), "
                "no el detector. cat013 (el único mis-attribution) está Lever-1-gated. "
                "→ confirma DEC-054: ~0 de los retrieval-miss; el detector es ORTOGONAL "
                "a la inanición del pool (= Lever 1)."
            ),
            "per_gold": {g: {"bucket": v[0], "nota": v[1]} for g, v in sorted(GOLD_FIX.items())},
        },
    }
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=120),
                   encoding="utf-8")

    print(f"\nOK → {OUT.name}")
    p1 = out["parte1_escala"]
    print(f"  1A pm-compuesto:        {p1['A_pm_compuesto']['n_docs']} docs / "
          f"{p1['A_pm_compuesto']['n_chunks']} chunks / {len(comp_by_mfr)} fabricantes")
    print(f"  1B mis-atrib REFINED:   {len(ref)} docs / {ref_chunks} chunks / "
          f"{len(ref_by_mfr)} fabricantes  (raw contaminado={len(misattr)})")
    print(f"  1C metadata-inconsist:  {p1['C_metadata_inconsistency']['n_clusters']} clusters")
    print(f"  2  buckets eval:        {dict(bucket_tally)}")
    print(f"     DETECTOR net golds:  {detector_net}  (hp009/hp018=config; cat013=lever1-gated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
