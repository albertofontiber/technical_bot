#!/usr/bin/env python3
"""S269 Etapa 1 — cohorte estructural pos/neg CONGELADA (build determinista, $0, GET-only).

Construye la población INDEPENDIENTE de la validación del detector must-preserve
(src/rag/must_preserve.py; diseño evals/s269_synthesis_portfolio_design_v1.md §1):

  1. Inventario de EXCLUSIONES versionado: docs ya empaquetados (S194/S197/S198/S199/S200),
     cohortes S147/S173, S186, TODO doc referenciado por golds (dev + held-out que se
     encuentre), artefactos target-adjacentes (s163/s235/s242/s243/s261/s269-triage) y los
     PDFs visuales S203-S205. Los packets se extraen ESTRUCTURALMENTE (items +
     target_equivalence_exclusion + selected_identities), el resto por text-scan contra el
     inventario del corpus. Guard anti-blast: si la exclusión supera el 70% del corpus se
     aborta (señal de que un fichero embebía el inventario elegible completo).
  2. Muestreo determinista (seed=269) de ~30 docs frescos estratificado por fabricante
     desde chunks_v2 (REST paginado, patrón src/rag/retriever.py), ~120 fragmentos:
     ~80 candidatos-positivos (pre-screen POR FAMILIA con los detectores, ~20/familia)
     + ~40 negativos (20 detector-silenciosos + 20 por AZAR PURO para estimar FN del
     pre-screen).

ANTI-CIRCULARIDAD (explícito, dúo-Sol C2): el pre-screen con el propio detector solo
SELECCIONA candidatos; el GOLD lo ponen etiquetadores modelo independientes (Luna + Haiku,
prompts distintos, ven SOLO el fragmento) — el gate mide al detector contra ese gold. Los
20 negativos de azar puro NO son anti-detector: permiten estimar el FN del pre-screen.

Sin flags: el script es 100% lectura (GET/SELECT) y escritura LOCAL de artefactos.
Outputs: evals/s269_structural_cohort_v1.jsonl + evals/s269_structural_cohort_prereg_v1.yaml
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola Windows cp1252

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag import must_preserve as mp  # noqa: E402

EVALS = ROOT / "evals"
COHORT_PATH = EVALS / "s269_structural_cohort_v1.jsonl"
PREREG_PATH = EVALS / "s269_structural_cohort_prereg_v1.yaml"

SEED = 269
TARGET_DOCS = 30
MAX_DOCS = 60                 # extensión determinista si algún bucket no se llena
POSITIVES_PER_FAMILY = 20
NEGATIVES_SCREENED = 20
NEGATIVES_RANDOM_PURE = 20
PER_DOC_FAMILY_CAP = 4        # anti-dominancia de un solo doc en un bucket
MIN_FRAGMENT_CHARS = 200
MAX_EXCLUSION_FRACTION = 0.70

FAMILIES = list(mp.FAMILIES)

# ── ficheros de exclusión ──────────────────────────────────────────────────────
# Packets fuente (extracción ESTRUCTURAL: items/target_equivalence/selected_identities;
# NO text-scan — s198+ embeben un resumen del inventario elegible completo).
STRUCTURED_PACKETS = [
    "evals/s194_fresh_source_packet_v1.json",
    "evals/s197_fresh_source_packet_v1.json",
    "evals/s198_fresh_source_packet_v2.json",
    "evals/s199_restored_margin_source_packet_v1.json",
    "evals/s200_final_balanced_source_packet_v1.json",
]
# Text-scan contra el inventario del corpus (document_id + source_file como substring).
TEXTSCAN_FILES = [
    # cohortes S147 / S173 / S186
    "evals/s147_fresh_source_packet_v1.json",
    "evals/s147_fresh_obligation_cohort_v1.json",
    "evals/s173_single_source_omission_cohort_v1.json",
    "evals/s186_relation_store_v1.json",
    "evals/s186_relation_extraction_receipts_v1.json",
    "evals/s186_relation_selector_receipts_v1.json",
    # golds dev + mapping (cubre los docs de los 4 targets sin leer su contenido a mano)
    "evals/gold_answers_v1.yaml",
    "evals/gold_layer_a_mapping.json",
    # artefactos target-adjacentes (fragmentos servidos de los 4 targets)
    "evals/s163_synthesis_residual_audit_v1.json",
    "evals/s235_direct_clause_bound_score_packet_v1.json",
    "evals/s242_direct_clause_bound_ab_result_v1.json",
    "evals/s243_synthesis_miss_causal_taxonomy_v1.yaml",
    "evals/s261_synthesis_checkpoint_v1.yaml",
    "evals/s269_triage_12misses_v1.yaml",
    # canaries visuales S203-S205 (PDFs visuales)
    "evals/s203_kidde_visual_canary_packet_v1.json",
    "evals/s204_kidde_visual_canary_packet_v1.json",
    "evals/s205_kidde_visual_canary_packet_v1.json",
    "evals/s205_kidde_visual_gold_v1.json",
]
HELDOUT_GLOB_RX = re.compile(r"hold.?out|held.?out", re.IGNORECASE)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _headers() -> dict[str, str]:
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _get_paginated(client: httpx.Client, table: str, params: dict) -> list[dict]:
    """GET paginado (PostgREST capa a 1000 filas; patrón retriever.py)."""
    base = os.environ["SUPABASE_URL"].rstrip("/")
    rows: list[dict] = []
    offset = 0
    while True:
        page = dict(params)
        page["limit"] = "1000"
        page["offset"] = str(offset)
        resp = client.get(f"{base}/rest/v1/{table}", headers=_headers(), params=page)
        resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


# ── inventario del corpus ──────────────────────────────────────────────────────

def fetch_corpus_docs(client: httpx.Client, table: str) -> dict[str, dict]:
    """document_id -> {source_file, manufacturer, chunk_count} desde chunks_v2 (servibles)."""
    rows = _get_paginated(
        client, table,
        {"select": "document_id,source_file,manufacturer", "parent_id": "is.null",
         "order": "id.asc"},
    )
    docs: dict[str, dict] = {}
    for r in rows:
        did = r.get("document_id")
        if not did:
            continue
        rec = docs.setdefault(
            did,
            {"source_file": r.get("source_file") or "",
             "manufacturer": r.get("manufacturer") or "unknown", "chunk_count": 0},
        )
        rec["chunk_count"] += 1
    return docs


# ── exclusiones ────────────────────────────────────────────────────────────────

def _walk_collect(node, out_ids: set[str], out_files: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("document_id", "doc_id") and isinstance(value, str):
                out_ids.add(value)
            elif key in ("source_file", "source_pdf_filename") and isinstance(value, str):
                out_files.add(value)
            else:
                _walk_collect(value, out_ids, out_files)
    elif isinstance(node, list):
        for item in node:
            _walk_collect(item, out_ids, out_files)


def collect_structured_packet(path: Path) -> tuple[set[str], set[str]]:
    """Extrae SOLO las secciones empaquetadas de un source-packet (no el inventario)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    ids: set[str] = set()
    files: set[str] = set()
    for section in ("items",):
        _walk_collect(data.get(section) or [], ids, files)
    teq = data.get("target_equivalence_exclusion") or {}
    _walk_collect(teq, ids, files)
    inventory = data.get("eligible_inventory") or {}
    _walk_collect(inventory.get("selected_identities") or [], ids, files)
    return ids, files


def build_exclusions(corpus: dict[str, dict]) -> tuple[set[str], list[dict]]:
    """Devuelve (document_ids excluidos, manifest por fichero para el prereg)."""
    norm_sf = {
        did: (rec["source_file"] or "").lower().removesuffix(".pdf")
        for did, rec in corpus.items()
    }
    excluded: set[str] = set()
    manifest: list[dict] = []

    def _apply(ids: set[str], files: set[str], origin: str, path: Path) -> None:
        files_norm = {f.lower().removesuffix(".pdf") for f in files if f}
        hit = {did for did in corpus if did in ids}
        hit |= {did for did, sf in norm_sf.items() if sf and sf in files_norm}
        excluded.update(hit)
        manifest.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "method": origin,
            "sha256": sha256_file(path),
            "referenced_document_ids": len(ids),
            "referenced_source_files": len(files),
            "corpus_docs_matched": len(hit),
        })

    for rel in STRUCTURED_PACKETS:
        path = ROOT / rel
        if not path.exists():
            manifest.append({"path": rel, "method": "structured_packet",
                             "status": "MISSING"})
            continue
        ids, files = collect_structured_packet(path)
        _apply(ids, files, "structured_packet", path)

    heldout_files = sorted(
        p for p in EVALS.iterdir()
        if p.is_file() and HELDOUT_GLOB_RX.search(p.name)
    )
    textscan_paths = [ROOT / rel for rel in TEXTSCAN_FILES] + heldout_files
    seen: set[Path] = set()
    for path in textscan_paths:
        if path in seen:
            continue
        seen.add(path)
        if not path.exists():
            manifest.append({
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "method": "text_scan", "status": "MISSING",
            })
            continue
        blob = path.read_text(encoding="utf-8", errors="replace").lower()
        hit = {did for did in corpus if did.lower() in blob}
        hit |= {did for did, sf in norm_sf.items() if sf and sf in blob}
        excluded.update(hit)
        manifest.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "method": "text_scan",
            "sha256": sha256_file(path),
            "corpus_docs_matched": len(hit),
        })

    # directorios de páginas visuales S203-S205 (nombres de fichero → source pdf)
    for rel in ("evals/s203_kidde_visual_pages_v1", "evals/s204_kidde_visual_pages_v1",
                "evals/s205_kidde_visual_pages_v1"):
        d = ROOT / rel
        if not d.is_dir():
            continue
        blob = "\n".join(p.name for p in d.iterdir()).lower()
        hit = {did for did, sf in norm_sf.items() if sf and sf in blob}
        excluded.update(hit)
        manifest.append({"path": rel, "method": "dir_listing_scan",
                         "corpus_docs_matched": len(hit)})

    fraction = len(excluded) / max(1, len(corpus))
    if fraction > MAX_EXCLUSION_FRACTION:
        raise RuntimeError(
            f"exclusión {fraction:.0%} > {MAX_EXCLUSION_FRACTION:.0%} del corpus — "
            "un fichero de exclusión embebe el inventario completo; revisar manifest"
        )
    return excluded, manifest


# ── muestreo ───────────────────────────────────────────────────────────────────

def stratified_doc_order(eligible: dict[str, dict], rng: random.Random) -> list[str]:
    """Orden round-robin por fabricante (barajado seeded dentro de cada estrato)."""
    strata: dict[str, list[str]] = {}
    for did, rec in eligible.items():
        strata.setdefault(rec["manufacturer"], []).append(did)
    order: list[str] = []
    keys = sorted(strata)
    for mfr in keys:
        strata[mfr].sort(key=lambda d: (eligible[d]["source_file"], d))
        rng.shuffle(strata[mfr])
    idx = 0
    while any(strata[m] for m in keys):
        mfr = keys[idx % len(keys)]
        if strata[mfr]:
            order.append(strata[mfr].pop(0))
        idx += 1
    return order


def fetch_doc_fragments(client: httpx.Client, table: str, document_id: str) -> list[dict]:
    rows = _get_paginated(
        client, table,
        {"select": "id,document_id,source_file,manufacturer,content",
         "document_id": f"eq.{document_id}", "parent_id": "is.null",
         "order": "id.asc"},
    )
    return [r for r in rows if len((r.get("content") or "").strip()) >= MIN_FRAGMENT_CHARS]


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    table = os.environ.get("CHUNKS_TABLE", "chunks_v2")
    rng = random.Random(SEED)

    with httpx.Client(timeout=30.0) as client:
        print("Inventario del corpus (chunks_v2, GET paginado)...")
        corpus = fetch_corpus_docs(client, table)
        print(f"  docs servibles: {len(corpus)}")

        print("Inventario de exclusiones...")
        excluded, exclusion_manifest = build_exclusions(corpus)
        eligible = {d: r for d, r in corpus.items() if d not in excluded}
        print(f"  excluidos: {len(excluded)} | elegibles (reserva fresca): {len(eligible)}")

        doc_order = stratified_doc_order(eligible, rng)

        pools: dict[str, list[dict]] = {f: [] for f in FAMILIES}
        silent_pool: list[dict] = []
        all_fragments: list[dict] = []
        per_doc_family: dict[tuple[str, str], int] = {}
        docs_used: list[str] = []

        def buckets_full() -> bool:
            return all(len(pools[f]) >= POSITIVES_PER_FAMILY for f in FAMILIES) and \
                len(silent_pool) >= NEGATIVES_SCREENED + NEGATIVES_RANDOM_PURE

        for did in doc_order:
            if len(docs_used) >= MAX_DOCS or (
                len(docs_used) >= TARGET_DOCS and buckets_full()
            ):
                break
            fragments = fetch_doc_fragments(client, table, did)
            if not fragments:
                continue
            docs_used.append(did)
            for frag in fragments:
                atoms = mp.detect_atoms(frag["content"])
                fired = sorted({a["family"] for a in atoms})
                record = {
                    "fragment_id": frag["id"],
                    "document_id": did,
                    "source_file": frag.get("source_file") or "",
                    "fabricante": eligible[did]["manufacturer"],
                    "texto": frag["content"],
                    "detector_families_fired": fired,
                    "sha256": sha256_text(frag["content"]),
                }
                all_fragments.append(record)
                if not fired:
                    silent_pool.append(record)
                    continue
                for fam in fired:
                    key = (did, fam)
                    if per_doc_family.get(key, 0) >= PER_DOC_FAMILY_CAP:
                        continue
                    per_doc_family[key] = per_doc_family.get(key, 0) + 1
                    pools[fam].append(record)

    # selección determinista de buckets (un fragmento pertenece a UN solo bucket)
    chosen: dict[str, dict] = {}
    composition: dict[str, int] = {}

    def take(pool: list[dict], n: int, bucket: str) -> None:
        pool = [r for r in pool if r["fragment_id"] not in chosen]
        rng.shuffle(pool)
        picked = pool[:n]
        for r in picked:
            row = dict(r)
            row["bucket"] = bucket
            row["familia_candidata"] = bucket if bucket in FAMILIES else "negative"
            chosen[r["fragment_id"]] = row
        composition[bucket] = len(picked)

    for fam in FAMILIES:
        take(pools[fam], POSITIVES_PER_FAMILY, fam)
    take(silent_pool, NEGATIVES_SCREENED, "negative_screened")
    take(all_fragments, NEGATIVES_RANDOM_PURE, "random_pure")

    rows = sorted(chosen.values(), key=lambda r: (r["bucket"], r["fragment_id"]))
    with COHORT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    cohort_sha = sha256_file(COHORT_PATH)

    # estimación de coste del etiquetado dual (para el presupuesto del prereg)
    total_chars = sum(len(r["texto"]) for r in rows)
    est_tokens_in = int(total_chars / 4) + 700 * len(rows)   # prompt+fragmento por item
    est_tokens_out = 350 * len(rows)
    cost_luna = est_tokens_in / 1e6 * 1.0 + est_tokens_out / 1e6 * 6.0
    cost_haiku = est_tokens_in / 1e6 * 1.0 + est_tokens_out / 1e6 * 5.0
    cost_arbiter_worst = est_tokens_in / 1e6 * 3.0 + est_tokens_out / 1e6 * 15.0
    est_cost = round(cost_luna + cost_haiku + cost_arbiter_worst, 2)

    prereg = {
        "schema": "s269_structural_cohort_prereg_v1",
        "status": "FROZEN_BEFORE_LABELING",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "design_ref": "evals/s269_synthesis_portfolio_design_v1.md §1 (v2 dúo-adjudicado)",
        "taxonomy_ref": "evals/s243_synthesis_miss_causal_taxonomy_v1.yaml",
        "detector_module": "src/rag/must_preserve.py",
        "seed": SEED,
        "chunks_table": table,
        "anti_circularity": (
            "El pre-screen con el detector solo SELECCIONA candidatos; el GOLD lo ponen "
            "etiquetadores modelo independientes (Luna + Haiku, prompts distintos) que ven "
            "SOLO el fragmento crudo — nunca el output del detector ni el bucket. El gate "
            "mide al detector contra ese gold. Los 20 negativos de azar puro NO son "
            "anti-detector: se muestrean de toda la población restante sin filtro, para "
            "poder estimar el FN del pre-screen (dúo-Sol C2: el detector JAMÁS etiqueta "
            "su propio gold)."
        ),
        "population": {
            "corpus_docs_servibles": len(corpus),
            "excluded_docs": len(excluded),
            "eligible_docs": len(eligible),
            "docs_sampled": len(docs_used),
            "fragments_screened": len(all_fragments),
            "min_fragment_chars": MIN_FRAGMENT_CHARS,
            "per_doc_family_cap": PER_DOC_FAMILY_CAP,
            "target_docs": TARGET_DOCS,
            "max_docs_extension": MAX_DOCS,
            "stratification": "round-robin por fabricante, shuffle seeded por estrato",
        },
        "composition": composition,
        "exclusion_manifest": exclusion_manifest,
        "excluded_document_ids": sorted(excluded),
        "gates_por_familia": {
            fam: {"recall_min": 0.80, "precision_min": 0.95}
            for fam in FAMILIES
        },
        "gate_negativos": {
            "fp_on_gold_negative_fragments": 0,
            "definition": (
                "0 disparos del detector (cualquier familia) sobre fragmentos de los "
                "buckets negative_screened y random_pure cuyo gold final sea negativo "
                "en todas las familias"
            ),
        },
        "labeling_protocol": {
            "labeler_a": {"provider": "openai", "model": "gpt-5.6-luna"},
            "labeler_b": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
            "prompts": "independientes y distintos; ven SOLO el fragmento crudo",
            "disagreement": (
                "árbitro claude-sonnet-4-6 (tercera opinión independiente, mayoría) "
                "o descarte declarado del ítem"
            ),
            "budget_usd_max": 6.0,
            "estimated_cost_usd": est_cost,
            "no_retry": True,
            "runner": "scripts/s269_label_structural_cohort.py (preflight default; "
                      "--execute gasta)",
        },
        "gate_runner": "scripts/s269_stage1_gate.py (determinista, $0)",
        "cohort_artifact": {
            "path": "evals/s269_structural_cohort_v1.jsonl",
            "rows": len(rows),
            "sha256": cohort_sha,
        },
    }
    PREREG_PATH.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )

    print(f"\nCohorte congelada: {COHORT_PATH.relative_to(ROOT)} ({len(rows)} filas)")
    print(f"Prereg: {PREREG_PATH.relative_to(ROOT)}")
    print(f"Composición: {composition}")
    print(f"Docs muestreados: {len(docs_used)} | coste etiquetado estimado: ${est_cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
