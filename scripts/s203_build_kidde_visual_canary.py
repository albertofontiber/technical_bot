#!/usr/bin/env python3
"""Build the frozen, pixel-addressed Kidde gold-authoring canary.

The source PDFs remain outside git.  The packet binds their exact bytes and the
versioned 200 dpi page renders used by both frontier models.  Selection is
source/topic based and occurs before either model is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import fitz
import yaml


ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "evals" / "gold_answers_v1.yaml"
PACKET_PATH = ROOT / "evals" / "s203_kidde_visual_canary_packet_v1.json"
IMAGE_ROOT = ROOT / "evals" / "s203_kidde_visual_pages_v1"


CANARY = (
    {
        "canary_id": "kidde_heat_class",
        "product": "Kidde Excellence KE-DT3101W-HAB / KE-DT3001W-HAB",
        "stratum": "configuration_table",
        "topic": "ajustes de sensibilidad, clase térmica, valor por defecto y umbrales de respuesta",
        "source_pdf": "3102986-ml_r002_excellence_series_intelligent_addressable_class_a-b_heat_detector_installation_sheet.pdf",
        "pages": [6, 7, 8],
        "focus_pages": [7],
        "product_manuals": [
            "3102986-ml_r002_excellence_series_intelligent_addressable_class_a-b_heat_detector_installation_sheet.pdf",
            "ke-dt3001w-hab-161721-es.pdf",
        ],
        "discovery_tokens": ["3102986", "ke-dt3101w-hab", "ke-dt3001w-hab"],
        "known_models_without_separate_local_datasheet": ["KE-DT3101W-HAB"],
        "prior_artifact_history": [
            "s114 selected the document for a held-out procedure bundle",
            "s200 used the English page-1 description, not the Spanish page-7 sensitivity tables",
        ],
    },
    {
        "canary_id": "kidde_single_output_test",
        "product": "Kidde Excellence KE-IO3101 / KE-IO3001",
        "stratum": "multi_page_procedure",
        "topic": "prueba manual del relé de salida, transición de LED y condiciones de salida de la prueba",
        "source_pdf": "3103062-ml_r003_excellence_series_addressable_single_output_module_installation_sheet.pdf",
        "pages": [7, 8, 9, 10],
        "focus_pages": [8, 9],
        "product_manuals": [
            "3103062-ml_r003_excellence_series_addressable_single_output_module_installation_sheet.pdf",
            "ke-io3101-161721-es.pdf",
        ],
        "discovery_tokens": ["3103062", "ke-io3101", "ke-io3001"],
        "known_models_without_separate_local_datasheet": ["KE-IO3001"],
        "prior_artifact_history": [
            "s116 near-duplicate inventory mentioned the file path only",
            "s197 used the English page-1 product description, not the Spanish pages 8-9 relay test",
        ],
    },
    {
        "canary_id": "kidde_multi_io_modes",
        "product": "Kidde Excellence KE-IO3122 / KE-IO3144 / KE-IO3044",
        "stratum": "mode_comparison_table",
        "topic": "comparación de modos de entrada normal y de dos estados: resistencias, umbrales y compatibilidad EN 54-13",
        "source_pdf": "3103063-ml_r003_excellence_series_addressable_two-four_input-output_module_installation_sheet.pdf",
        "pages": [10, 11, 12, 13],
        "focus_pages": [10, 11],
        "product_manuals": [
            "3103063-ml_r003_excellence_series_addressable_two-four_input-output_module_installation_sheet.pdf",
            "ke-io3122-161721-es.pdf",
            "ke-io3144-161721-es.pdf",
        ],
        "discovery_tokens": ["3103063", "ke-io3122", "ke-io3144", "ke-io3044"],
        "known_models_without_separate_local_datasheet": ["KE-IO3044"],
        "prior_artifact_history": [
            "s116 near-duplicate inventory mentioned the file path only",
            "s159 used an English mechanical-specification table",
            "s195 used the English multi-channel test procedure, not the Spanish pages 10-11 input-mode tables",
        ],
    },
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_sha(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)


def all_pdf_refs(row: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in row.get("pdfs_used") or []:
        refs.add(Path(str(value)).name.lower())
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            refs.add(Path(str(citation["pdf"])).name.lower())
    return refs


def pdf_ref_paths(row: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in row.get("pdfs_used") or []:
        refs.add(str(value).replace("\\", "/"))
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            refs.add(str(citation["pdf"]).replace("\\", "/"))
    return refs


def render_page(doc: fitz.Document, page_number: int, output: Path) -> dict[str, Any]:
    page = doc.load_page(page_number - 1)
    pixmap = page.get_pixmap(dpi=200, alpha=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output)
    data = output.read_bytes()
    return {
        "page": page_number,
        "image": output.relative_to(ROOT).as_posix(),
        "image_sha256": sha256_bytes(data),
        "image_bytes": len(data),
        "width_px": pixmap.width,
        "height_px": pixmap.height,
        "dpi": 200,
        "extracted_text": page.get_text("text"),
    }


def build(pdf_root: Path) -> dict[str, Any]:
    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(gold_rows, list):
        raise ValueError("gold_answers_v1.yaml must contain a list")

    existing_refs = set().union(*(all_pdf_refs(row) for row in gold_rows))
    selected_names = {str(row["source_pdf"]).lower() for row in CANARY}
    overlap = sorted(selected_names & existing_refs)
    if overlap:
        raise ValueError(f"selected source PDF already used by a gold: {overlap}")

    workspace_root = pdf_root.parent
    referenced_hashes: dict[str, list[str]] = {}
    unresolved_refs: list[str] = []
    local_pdf_by_name: dict[str, list[Path]] = {}
    for manual_root in workspace_root.glob("Manuales*"):
        if not manual_root.is_dir():
            continue
        for path in manual_root.rglob("*.pdf"):
            local_pdf_by_name.setdefault(path.name.lower(), []).append(path)
    all_ref_paths = set().union(*(pdf_ref_paths(row) for row in gold_rows))
    for ref in sorted(all_ref_paths):
        direct = workspace_root / Path(ref)
        paths = [direct] if direct.is_file() else local_pdf_by_name.get(
            Path(ref).name.lower(), []
        )
        if not paths:
            unresolved_refs.append(ref)
            continue
        for path in paths:
            resolved_ref = path.relative_to(workspace_root).as_posix()
            referenced_hashes.setdefault(sha256_bytes(path.read_bytes()), []).append(
                f"{ref} -> {resolved_ref}"
            )

    manual_inventory: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    for spec in CANARY:
        discovered = sorted(
            path.name
            for path in pdf_root.glob("*.pdf")
            if any(token.lower() in path.name.lower() for token in spec["discovery_tokens"])
        )
        if set(discovered) != set(spec["product_manuals"]):
            raise ValueError(
                f"product-manual discovery drift for {spec['canary_id']}: {discovered}"
            )
        for filename in spec["product_manuals"]:
            if filename in manual_inventory:
                continue
            path = pdf_root / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            with fitz.open(path) as doc:
                manual_inventory[filename] = {
                    "path": f"Manuales_Kidde/{filename}",
                    "sha256": sha256_bytes(path.read_bytes()),
                    "bytes": path.stat().st_size,
                    "page_count": doc.page_count,
                }

        source_path = pdf_root / str(spec["source_pdf"])
        renders = []
        with fitz.open(source_path) as doc:
            for page_number in spec["pages"]:
                if not 1 <= page_number <= doc.page_count:
                    raise ValueError(f"page {page_number} outside {source_path.name}")
                image_name = f"{spec['canary_id']}_p{page_number}_200dpi.png"
                renders.append(
                    render_page(doc, page_number, IMAGE_ROOT / image_name)
                )

        item = dict(spec)
        item["source"] = manual_inventory[str(spec["source_pdf"])]
        item["discovered_product_manuals"] = discovered
        item["rendered_pages"] = renders
        items.append(item)

    existing_questions = [
        {"qid": str(row.get("qid")), "question": str(row.get("question"))}
        for row in gold_rows
        if row.get("qid") and row.get("question")
    ]
    existing_gold_coverage = [
        {
            "qid": str(row["qid"]),
            "question": str(row["question"]),
            "atomic_fact_texts": [
                str(fact.get("texto") or fact.get("text") or "")
                for fact in row.get("atomic_facts") or []
                if isinstance(fact, dict)
            ],
        }
        for row in gold_rows
        if row.get("qid") and row.get("question")
    ]
    # Some Kidde-branded 2X-A golds cite legacy Aritech paths, so source-root
    # matching alone undercounts the existing semantic coverage.
    kidde_rows = [row for row in gold_rows if "kidde" in str(row).lower()]
    packet: dict[str, Any] = {
        "schema": "s203_kidde_visual_canary_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_CALLS",
        "selection": {
            "method": "source_first_pre_model_stratified_canary",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "selected_items": len(items),
            "selected_source_overlap_with_existing_gold": overlap,
            "selected_source_sha_overlap_with_resolved_existing_gold": sorted(
                {
                    manual_inventory[str(item["source_pdf"])]["sha256"]
                    for item in CANARY
                }
                & set(referenced_hashes)
            ),
            "existing_gold_question_count": len(existing_questions),
            "existing_kidde_gold_qids": sorted(str(row["qid"]) for row in kidde_rows),
            "selection_axes": [
                "configuration_table",
                "multi_page_procedure",
                "mode_comparison_table",
            ],
        },
        "existing_questions": existing_questions,
        "existing_gold_coverage": existing_gold_coverage,
        "existing_gold_resolved_source_hash_count": len(referenced_hashes),
        "existing_gold_unresolved_source_refs": unresolved_refs,
        "kidde_pdf_universe_count": len(list(pdf_root.glob("*.pdf"))),
        "manual_inventory": manual_inventory,
        "items": items,
        "generation_contract": {
            "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "independent": {"model": "claude-fable-5"},
            "pixel_only_frontier_input": True,
            "independent_generation_before_cross_review": True,
            "final_gold_precedence": "sol_candidate_only_if_fable_pixel_review_passes",
            "fable_candidate_must_pass_sol_pixel_review": True,
            "merge_candidates": False,
            "same_item_retry": False,
        },
    }
    packet["packet_sha256"] = stable_sha(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path, required=True)
    args = parser.parse_args()
    packet = build(args.pdf_root.resolve())
    PACKET_PATH.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "packet": PACKET_PATH.relative_to(ROOT).as_posix(),
                "packet_sha256": packet["packet_sha256"],
                "items": len(packet["items"]),
                "images": sum(len(row["rendered_pages"]) for row in packet["items"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
