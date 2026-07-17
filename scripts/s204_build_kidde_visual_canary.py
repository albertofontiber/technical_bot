#!/usr/bin/env python3
"""Build the frozen S204 pixel-addressed Kidde gold canary."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import sha256_bytes, stable_sha, write_json  # noqa: E402


GOLD_PATH = ROOT / "evals" / "gold_answers_v1.yaml"
HYQ_PATH = ROOT / "evals" / "s99_hyq_generated.jsonl"
PACKET_PATH = ROOT / "evals" / "s204_kidde_visual_canary_packet_v1.json"
IMAGE_ROOT = ROOT / "evals" / "s204_kidde_visual_pages_v1"


CANARY = (
    {
        "canary_id": "kidde_base_class_a_terminals",
        "product": "Kidde Excellence KE-DB3010W / KE-DB3010B standard mounting base",
        "stratum": "wiring_diagram_and_terminal_table",
        "topic": (
            "topología visual de cableado Clase A entre dos bases y la central, "
            "incluida la correspondencia A/B, polaridad y terminales"
        ),
        "source_pdf": (
            "3102987-ml_r003_excellence_series_standard_mounting_base_"
            "installation_sheet.pdf"
        ),
        "pages": [1, 4],
        "focus_pages": [1, 4],
        "product_manuals": [
            (
                "3102987-ml_r003_excellence_series_standard_mounting_base_"
                "installation_sheet.pdf"
            ),
            "ke-db3010w-161721-es.pdf",
        ],
        "discovery_tokens": ["3102987", "ke-db3010w-"],
        "prior_artifact_history": [
            "s116/s134 inventory mentions only; no authored question or source unit",
            "pages 1 and 4 and the Class A terminal-map predicate are new",
        ],
    },
    {
        "canary_id": "kidde_indoor_dip_examples",
        "product": "Kidde Excellence intelligent addressable indoor notification devices",
        "stratum": "visual_switch_configuration",
        "topic": (
            "lectura visual de las posiciones DIP exactas para las direcciones "
            "008 y 112, valores activados y regla de suma"
        ),
        "source_pdf": (
            "3103072-ml_r004_excellence_series_intelligent_addressable_indoor_"
            "notification_device_installation_sheet.pdf"
        ),
        "pages": [12],
        "focus_pages": [12],
        "product_manuals": [
            (
                "3103072-ml_r004_excellence_series_intelligent_addressable_"
                "indoor_notification_device_installation_sheet.pdf"
            ),
            "ke-as3115r-wm-161721-es.pdf",
        ],
        "discovery_tokens": ["3103072", "ke-as3115r-wm-"],
        "prior_artifact_history": [
            "s116/s134 inventory mentions only; no authored question or source unit",
            "the exact visual DIP patterns 008/112 on page 12 are new",
        ],
    },
    {
        "canary_id": "kidde_deep_accessory_slots",
        "product": "Kidde Excellence KE-DBA-AUXW deep accessory",
        "stratum": "visual_component_identification",
        "topic": (
            "distinción visual de la ranura de etiqueta de dirección y la ranura "
            "de pestaña de bloqueo, más la colocación previa de la etiqueta"
        ),
        "source_pdf": (
            "3103013-ml_r002_ke-dba-auxw_deep_accessory_for_standard_mounting_"
            "base_installation_sheet.pdf"
        ),
        "pages": [1, 3],
        "focus_pages": [1, 3],
        "product_manuals": [
            (
                "3103013-ml_r002_ke-dba-auxw_deep_accessory_for_standard_"
                "mounting_base_installation_sheet.pdf"
            ),
            "ke-dba-auxw-161721-es.pdf",
        ],
        "discovery_tokens": ["3103013", "ke-dba-auxw-"],
        "prior_artifact_history": [
            "s116/s134 inventory mentions only; no authored question or source unit",
            "the visual slot distinction across pages 1 and 3 is new",
        ],
    },
)


def _pdf_names(row: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for value in row.get("pdfs_used") or []:
        names.add(Path(str(value)).name.lower())
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            names.add(Path(str(citation["pdf"])).name.lower())
    return names


def _pdf_refs(row: dict[str, Any]) -> set[str]:
    refs = {str(value).replace("\\", "/") for value in row.get("pdfs_used") or []}
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            refs.add(str(citation["pdf"]).replace("\\", "/"))
    return refs


def _render_page(
    document: fitz.Document, page_number: int, output: Path
) -> dict[str, Any]:
    page = document.load_page(page_number - 1)
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
    }


def build(pdf_root: Path) -> dict[str, Any]:
    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(gold_rows, list):
        raise ValueError("gold_answers_v1.yaml must contain a list")

    selected_names = {str(row["source_pdf"]).lower() for row in CANARY}
    existing_names = set().union(*(_pdf_names(row) for row in gold_rows))
    basename_overlap = sorted(selected_names & existing_names)
    if basename_overlap:
        raise ValueError(f"selected source already used by a gold: {basename_overlap}")

    workspace_root = pdf_root.parent
    local_pdf_by_name: dict[str, list[Path]] = {}
    for manual_root in workspace_root.glob("Manuales*"):
        if manual_root.is_dir():
            for path in manual_root.rglob("*.pdf"):
                local_pdf_by_name.setdefault(path.name.lower(), []).append(path)
    resolved_hashes: dict[str, list[str]] = {}
    unresolved_refs: list[str] = []
    all_refs = set().union(*(_pdf_refs(row) for row in gold_rows))
    for ref in sorted(all_refs):
        direct = workspace_root / Path(ref)
        paths = [direct] if direct.is_file() else local_pdf_by_name.get(
            Path(ref).name.lower(), []
        )
        if not paths:
            unresolved_refs.append(ref)
            continue
        for path in paths:
            resolved_hashes.setdefault(sha256_bytes(path.read_bytes()), []).append(ref)

    inventory: dict[str, dict[str, Any]] = {}
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
            if filename in inventory:
                continue
            path = pdf_root / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            with fitz.open(path) as document:
                inventory[filename] = {
                    "path": f"Manuales_Kidde/{filename}",
                    "sha256": sha256_bytes(path.read_bytes()),
                    "bytes": path.stat().st_size,
                    "page_count": document.page_count,
                }

        source_path = pdf_root / str(spec["source_pdf"])
        rendered_pages = []
        with fitz.open(source_path) as document:
            for page_number in spec["pages"]:
                if not 1 <= page_number <= document.page_count:
                    raise ValueError(f"page {page_number} outside {source_path.name}")
                filename = f"{spec['canary_id']}_p{page_number}_200dpi.png"
                rendered_pages.append(
                    _render_page(document, page_number, IMAGE_ROOT / filename)
                )
        item = dict(spec)
        item["source"] = inventory[str(spec["source_pdf"])]
        item["discovered_product_manuals"] = discovered
        item["rendered_pages"] = rendered_pages
        items.append(item)

    selected_hashes = {
        inventory[str(item["source_pdf"])]["sha256"] for item in CANARY
    }
    sha_overlap = sorted(selected_hashes & set(resolved_hashes))
    if sha_overlap:
        raise ValueError(f"selected source bytes already used by a gold: {sha_overlap}")

    existing_coverage = [
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
    selected_stems = {
        Path(str(item["source_pdf"])).stem.lower() for item in CANARY
    }
    hyq_coverage: list[dict[str, Any]] = []
    for line in HYQ_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("source_file", "")).lower() not in selected_stems:
            continue
        for index, question in enumerate(row.get("questions") or [], 1):
            if isinstance(question, str) and question.strip():
                hyq_coverage.append(
                    {
                        "qid": f"hyq:{row['chunk_id']}:{index}",
                        "question": question,
                        "atomic_fact_texts": [],
                        "kind": "retriever_augmentation_not_test_gold",
                    }
                )
    combined_coverage = existing_coverage + hyq_coverage
    packet: dict[str, Any] = {
        "schema": "s204_kidde_visual_canary_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_CALLS",
        "selection": {
            "method": "fresh_source_unit_pre_model_stratified_canary",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "selected_items": len(items),
            "selected_source_overlap_with_existing_gold": basename_overlap,
            "selected_source_sha_overlap_with_resolved_existing_gold": sha_overlap,
            "existing_gold_question_count": len(existing_coverage),
            "selection_axes": [item["stratum"] for item in CANARY],
            "excluded_closed_cohort": "s203",
        },
        "existing_gold_coverage": combined_coverage,
        "existing_gold_question_count": len(existing_coverage),
        "selected_source_hyq_question_count": len(hyq_coverage),
        "existing_gold_resolved_source_hash_count": len(resolved_hashes),
        "existing_gold_unresolved_source_refs": unresolved_refs,
        "kidde_pdf_universe_count": len(list(pdf_root.glob("*.pdf"))),
        "manual_inventory": inventory,
        "items": items,
        "generation_contract": {
            "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "independent": {"model": "claude-fable-5"},
            "pixel_only_frontier_input": True,
            "independent_generation_before_cross_review": True,
            "final_gold_precedence": (
                "sol_candidate_only_if_both_directions_pass_for_the_whole_cohort"
            ),
            "merge_candidates": False,
            "same_item_retry": False,
            "application_inference_without_explicit_pixel_support": "forbidden",
            "nonblocking_notes_invalidate_pass": False,
        },
    }
    packet["packet_sha256"] = stable_sha(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path, required=True)
    args = parser.parse_args()
    packet = build(args.pdf_root.resolve())
    write_json(PACKET_PATH, packet)
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
