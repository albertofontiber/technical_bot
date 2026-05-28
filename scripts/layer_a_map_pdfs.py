#!/usr/bin/env python3
"""Capa A sub-paso 1 — mapeo hp* -> PDFs.

Para cada pregunta del set (N=19, hp016 removida):
  - Si tiene relevant_chunks en gate_relevant_chunks.json: resolver source_files
    a paths reales de PDF + las page_numbers a usar como hint.
  - Si no tiene relevant_chunks: identificar producto/fabricante por keywords
    en la pregunta del baseline_v1.yaml + buscar PDF(s) candidatos en
    Manuales_*/ por similitud de filename con el modelo/fabricante.

Output: evals/gold_layer_a_mapping.json
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(".")
BASELINE = Path("evals/baseline_v1.yaml")
GATE = Path("evals/gate_relevant_chunks.json")
OUTPUT = Path("evals/gold_layer_a_mapping.json")
REMOVED = {"hp016"}

MANUAL_DIRS = [
    Path("Manuales_ES"),
    Path("Manuales_Notifier"),
    Path("Manuales_Notifier_Privado"),
    Path("Manuales_Morley"),
    Path("Manuales_Morley_Privado"),
    Path("Manuales_Morley_Guias"),
    Path("manuales"),
]


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()


def find_pdf_by_stem(stem: str) -> list[Path]:
    """Busca PDFs cuyo nombre contiene `stem` (case/accent-insensitive)."""
    target = normalize(stem)
    hits: list[Path] = []
    for base in MANUAL_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.pdf"):
            if target in normalize(p.stem):
                hits.append(p)
    return hits


MODEL_HINTS = {
    "hp005": ("Notifier ID3000", ["ID3000", "ID 3000"]),
    "hp007": ("VESDA-E VEP", ["VESDA", "VEP"]),
    "hp008": ("Notifier ID3000 compatibilidad detectores", ["ID3000", "ID 3000"]),
    "hp013": ("Detnov ADW535", ["ADW535", "ADW-535", "ADW 535"]),
    "hp015": ("Detnov CCD-103", ["CCD-103", "CCD103", "CCD 103"]),
    "hp017": ("Notifier PEARL", ["PEARL", "Pearl"]),
    "hp019": ("Detnov ASD (familia: ASD535, ASD532, etc.)", ["ASD535", "ASD532", "ASD-535"]),
    "hp020": ("Notifier INSPIRE", ["INSPIRE", "Inspire"]),
}


def main() -> int:
    baseline = yaml.safe_load(BASELINE.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    gate_qs = gate["questions"]

    by_id = {q["id"]: q for q in baseline["questions"] if q["id"].startswith("hp")}

    mapping: dict[str, dict] = {}

    for qid in sorted(by_id):
        if qid in REMOVED:
            continue

        q = by_id[qid]
        gq = gate_qs.get(qid, {})
        relevant = gq.get("relevant_chunks", []) or []

        entry: dict = {
            "question": q["question"],
            "expected_behavior_yaml": q.get("expected_behavior", "answer"),
            "question_type": q.get("question_type", "?"),
            "has_relevant_chunks": bool(relevant),
        }

        if relevant:
            # Recolectar source_file + page_number de cada relevant_chunk
            by_source: dict[str, set[int]] = {}
            for c in relevant:
                sf = c["source_file"]
                pn = c.get("page_number")
                by_source.setdefault(sf, set())
                if isinstance(pn, int):
                    by_source[sf].add(pn)

            sources_resolved = []
            for sf, pages in by_source.items():
                pdfs = find_pdf_by_stem(sf)
                sources_resolved.append({
                    "source_file_in_chunks": sf,
                    "page_numbers": sorted(pages),
                    "pdf_paths_found": [str(p) for p in pdfs],
                    "n_pdfs_found": len(pdfs),
                })
            entry["sources"] = sources_resolved

        else:
            # Sin relevant_chunks -> resolver por hints
            hint = MODEL_HINTS.get(qid)
            entry["product_hint"] = hint[0] if hint else "?"
            entry["keyword_hints"] = hint[1] if hint else []
            candidates: dict[str, list[str]] = {}
            if hint:
                for kw in hint[1]:
                    pdfs = find_pdf_by_stem(kw)
                    candidates[kw] = [str(p) for p in pdfs]
            entry["pdf_candidates"] = candidates

        mapping[qid] = entry

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Resumen en stdout
    with_chunks = [k for k, v in mapping.items() if v["has_relevant_chunks"]]
    without_chunks = [k for k, v in mapping.items() if not v["has_relevant_chunks"]]
    missing_pdfs = []
    for qid, v in mapping.items():
        if v["has_relevant_chunks"]:
            for s in v["sources"]:
                if s["n_pdfs_found"] == 0:
                    missing_pdfs.append((qid, s["source_file_in_chunks"]))
        else:
            cands = v.get("pdf_candidates", {})
            if not any(cands.values()):
                missing_pdfs.append((qid, v.get("product_hint", "?")))

    print(f"Total mapeadas: {len(mapping)}")
    print(f"  con relevant_chunks: {len(with_chunks)} -> {with_chunks}")
    print(f"  sin relevant_chunks: {len(without_chunks)} -> {without_chunks}")
    print(f"  PDFs no resueltos: {len(missing_pdfs)}")
    for qid, sf in missing_pdfs:
        print(f"    {qid}: {sf}")
    print(f"\nOutput: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
