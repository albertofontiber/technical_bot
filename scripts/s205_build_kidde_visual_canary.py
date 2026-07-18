#!/usr/bin/env python3
"""Build the fresh S205 principal-gold visual canary."""
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
PACKET_PATH = ROOT / "evals" / "s205_kidde_visual_canary_packet_v1.json"
IMAGE_ROOT = ROOT / "evals" / "s205_kidde_visual_pages_v1"


TOUCH_MANUALS = [
    "00-3280-508-4109-06_r006_2x-at_series_quick_start_guide_es.pdf",
    "00-3280-508-4209-02_r002_2x-at_series_quick_operation_guide_es.pdf",
    "2x-at-f2-161721-es.pdf",
    "2x-at-f2-fb-161721-es.pdf",
    "2x-at-f2-fb-p-161721-es.pdf",
    "2x-at-f2-fb-s-161721-es.pdf",
    "2x-at-f2-p-161721-es.pdf",
    "2x-at-f2-s-161721-es.pdf",
]

CANARY = (
    {
        "canary_id": "kidde_kuwait_pcb_callouts",
        "product": "Kidde 2X-A Kuwait large cabinet with 6 A power supply",
        "stratum": "dense_numbered_hardware_diagram",
        "topic": (
            "identificación visual de los conectores Ethernet, USB A/B, COM0/1/2, "
            "batería, fuente y usuario mediante las llamadas numeradas de la PCB"
        ),
        "source_pdf": "3103267-en_r001_2x-a_series_kuwait_marketplace_manual.pdf",
        "pages": [10],
        "focus_pages": [10],
        "product_manuals": [
            "3103267-en_r001_2x-a_series_kuwait_marketplace_manual.pdf"
        ],
        "discovery_tokens": ["3103267"],
        "prior_artifact_history": [
            "S99 has no question for page 10",
            "no S194-S204 authored or reviewed this source/page/predicate",
        ],
    },
    {
        "canary_id": "kidde_touchscreen_regions",
        "product": "Kidde 2X-AT touchscreen control panel",
        "stratum": "annotated_user_interface_diagram",
        "topic": (
            "correspondencia visual de las tres regiones numeradas de la pantalla "
            "táctil en reposo con sus funciones"
        ),
        "source_pdf": TOUCH_MANUALS[0],
        "pages": [11],
        "focus_pages": [11],
        "product_manuals": TOUCH_MANUALS,
        "discovery_tokens": ["2x-at"],
        "prior_artifact_history": [
            "S99 has no question for page 11",
            "no S194-S204 authored or reviewed this source/page/predicate",
        ],
    },
    {
        "canary_id": "kidde_900_is_barriers",
        "product": "Kidde 2X-A / ZP2-A 900 Series protocol compatibility list",
        "stratum": "dense_compatibility_table",
        "topic": (
            "modelos exactos y función de las tres barreras convencionales "
            "intrínsecamente seguras listadas en la tabla de compatibilidad"
        ),
        "source_pdf": (
            "bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_"
            "panel_compatibility_list_900_series_protocol.pdf"
        ),
        "pages": [5],
        "focus_pages": [5],
        "product_manuals": [
            "bcn-3100035-en_r006_2x-a_series_addressable_control_panel_compatibility_list_0.pdf",
            (
                "bcn-3100036-en_r002_2x-a_and_zp2-a_series_addressable_control_"
                "panel_compatibility_list_900_series_protocol.pdf"
            ),
        ],
        "discovery_tokens": ["bcn-3100035", "bcn-3100036"],
        "prior_artifact_history": [
            "S99 has no question for page 5",
            "existing ho003 covers Excellence detector compatibility, not these 900-protocol IS barriers",
        ],
    },
)


def _pdf_names(row: dict[str, Any]) -> set[str]:
    names = {Path(str(value)).name.lower() for value in row.get("pdfs_used") or []}
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


def _render(document: fitz.Document, page_number: int, output: Path) -> dict[str, Any]:
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
        raise ValueError("gold ledger must be a list")
    selected_names = {str(item["source_pdf"]).lower() for item in CANARY}
    existing_names = set().union(*(_pdf_names(row) for row in gold_rows))
    basename_overlap = sorted(selected_names & existing_names)
    if basename_overlap:
        raise ValueError(f"selected source already used by gold: {basename_overlap}")

    workspace_root = pdf_root.parent
    local_by_name: dict[str, list[Path]] = {}
    for manual_root in workspace_root.glob("Manuales*"):
        if manual_root.is_dir():
            for path in manual_root.rglob("*.pdf"):
                local_by_name.setdefault(path.name.lower(), []).append(path)
    resolved_hashes: set[str] = set()
    unresolved_refs: list[str] = []
    for ref in sorted(set().union(*(_pdf_refs(row) for row in gold_rows))):
        direct = workspace_root / Path(ref)
        paths = [direct] if direct.is_file() else local_by_name.get(
            Path(ref).name.lower(), []
        )
        if not paths:
            unresolved_refs.append(ref)
        else:
            resolved_hashes.update(sha256_bytes(path.read_bytes()) for path in paths)

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
            with fitz.open(path) as document:
                inventory[filename] = {
                    "path": f"Manuales_Kidde/{filename}",
                    "sha256": sha256_bytes(path.read_bytes()),
                    "bytes": path.stat().st_size,
                    "page_count": document.page_count,
                }
        source_path = pdf_root / str(spec["source_pdf"])
        renders = []
        with fitz.open(source_path) as document:
            for page_number in spec["pages"]:
                filename = f"{spec['canary_id']}_p{page_number}_200dpi.png"
                renders.append(_render(document, page_number, IMAGE_ROOT / filename))
        item = dict(spec)
        item["source"] = inventory[str(spec["source_pdf"])]
        item["discovered_product_manuals"] = discovered
        item["rendered_pages"] = renders
        items.append(item)

    selected_hashes = {
        inventory[str(item["source_pdf"])]["sha256"] for item in CANARY
    }
    sha_overlap = sorted(selected_hashes & resolved_hashes)
    if sha_overlap:
        raise ValueError(f"selected source bytes already used by gold: {sha_overlap}")

    gold_coverage = [
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
    stems = {Path(str(item["source_pdf"])).stem.lower() for item in CANARY}
    hyq_coverage = []
    for line in HYQ_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("source_file", "")).lower() not in stems:
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

    packet: dict[str, Any] = {
        "schema": "s205_kidde_visual_canary_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_CALLS",
        "selection": {
            "method": "principal_gate_fresh_visual_source_units",
            "geometry_frozen_in_prior_commit": "af6de65",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "selected_items": len(items),
            "selected_source_overlap_with_existing_gold": basename_overlap,
            "selected_source_sha_overlap_with_resolved_existing_gold": sha_overlap,
            "excluded_closed_cohorts": ["s203", "s204"],
            "selection_axes": [item["stratum"] for item in CANARY],
        },
        "existing_gold_coverage": gold_coverage + hyq_coverage,
        "existing_gold_question_count": len(gold_coverage),
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
            "final_gold_author": "gpt-5.6-sol",
            "principal_publication_review": "fable_must_pass_every_sol_candidate",
            "counterpart_role": "blind_material_disagreement_probe_not_publication_candidate",
            "counterpart_gate": "topic_aligned_and_zero_material_disagreement",
            "merge_candidates": False,
            "same_item_retry": False,
            "application_inference_without_explicit_pixel_support": "forbidden",
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
                "packet_sha256": packet["packet_sha256"],
                "items": len(packet["items"]),
                "images": sum(len(item["rendered_pages"]) for item in packet["items"]),
                "hyq_screened": packet["selected_source_hyq_question_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
