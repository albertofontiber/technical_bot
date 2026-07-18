#!/usr/bin/env python3
"""Freeze the fresh S230 pixel cohort before any model output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.holdout_evidence import atomic_evidence_unit_rows  # noqa: E402
from src.rag.visual_gold import sha256_bytes, stable_sha, write_json  # noqa: E402


GOLD_PATH = ROOT / "evals/gold_answers_v1.yaml"
HYQ_PATH = ROOT / "evals/s99_hyq_generated.jsonl"
SELECTION_PATH = ROOT / "evals/s230_kidde_fresh_selection_receipt_v1.json"
PIXEL_PATH = ROOT / "evals/s230_kidde_fresh_pixel_receipts_v1.json"
PACKET_PATH = ROOT / "evals/s230_kidde_fresh_clause_bound_packet_v1.json"
STAGES_TO_EXCLUDE = (203, 204, 205, 207, 208, 209, 214, 215, 217)


ITEMS: tuple[dict[str, Any], ...] = (
    {
        "canary_id": "kidde_2xa_class_a_to_class_b_loop_tradeoffs",
        "product": "Kidde 2X-A addressable control panels",
        "stratum": "cross_document_topology_constraints",
        "topic": (
            "compare the Class A quick-install loop with the Class B manual "
            "alternative across EN 54-13 status, device ceiling, supervision and "
            "terminal geometry, keeping every qualification scoped to its class"
        ),
        "distinct_sources_min": 2,
        "cross_source_facts_min": 1,
        "known_conflicts": [],
        "sources": [
            {
                "source_pdf": "00-3280-507-4003-03_r003_2x-a_series_quick_installation_guide_en.pdf",
                "pages": [2],
                "image_names": ["2xa_quick_install_p2_200dpi.png"],
            },
            {
                "source_pdf": "00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0.pdf",
                "pages": [41],
                "image_names": ["2xa_install_p41_200dpi.png"],
            },
        ],
    },
    {
        "canary_id": "kidde_2xa_battery_configuration_and_location",
        "product": "Kidde 2X-A control-panel batteries",
        "stratum": "same_document_distant_page_constraint_join",
        "topic": (
            "join battery type configuration requirements with the internal or "
            "external installation location matrix for 4 A, 6 A and 10 A power "
            "supplies without generalizing a capacity to an unsupported cabinet"
        ),
        "distinct_sources_min": 1,
        "cross_source_facts_min": 0,
        "known_conflicts": [],
        "sources": [
            {
                "source_pdf": "00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0.pdf",
                "pages": [34, 36],
                "image_names": [
                    "2xa_install_p34_200dpi.png",
                    "2xa_install_p36_200dpi.png",
                ],
            },
        ],
    },
    {
        "canary_id": "kidde_2xa_output_termination_by_compliance_class",
        "product": "Kidde 2X-A configurable outputs",
        "stratum": "same_document_adjacent_page_conditional_join",
        "topic": (
            "relate output supervision and termination to typical Class B versus "
            "EN 54-13 Class A installation, including unused-output configuration "
            "and the model-dependent count of configurable outputs"
        ),
        "distinct_sources_min": 1,
        "cross_source_facts_min": 0,
        "known_conflicts": [],
        "sources": [
            {
                "source_pdf": "00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0.pdf",
                "pages": [43, 44],
                "image_names": [
                    "2xa_install_p43_200dpi.png",
                    "2xa_install_p44_200dpi.png",
                ],
            },
        ],
    },
)


VISUAL_ANCHORS: dict[str, list[str]] = {
    "2xa_quick_install_p2_200dpi.png": [
        "Class A open-and-short supervision",
        "unused Class A A-to-B termination",
        "Class A ceiling of 128 devices",
    ],
    "2xa_install_p41_200dpi.png": [
        "Class B does not comply with EN 54-13",
        "Class B ceiling of 32 devices",
        "A or B connectors but not both and short-circuit supervision",
    ],
    "2xa_install_p34_200dpi.png": [
        "battery-type configuration differs for 4 A or 6 A versus 10 A PSU",
        "compatible battery table scoped by PSU",
    ],
    "2xa_install_p36_200dpi.png": [
        "battery installation location matrix by cabinet and capacity",
        "external boxes restricted to large-cabinet 10 A variants",
    ],
    "2xa_install_p43_200dpi.png": [
        "Class B 15 kohm and Class A 4.7 kohm output termination",
        "unused outputs require 15 kohm and Class B configuration",
    ],
    "2xa_install_p44_200dpi.png": [
        "Class A and Class B configurable output counts by panel topology",
        "sounder is the default configurable-output setting",
    ],
}


def _source_names() -> set[str]:
    return {
        source["source_pdf"]
        for item in ITEMS
        for source in item["sources"]
    }


def _prior_artifacts() -> list[Path]:
    paths: list[Path] = []
    for stage in STAGES_TO_EXCLUDE:
        paths.extend(
            path
            for path in (ROOT / "evals").glob(f"s{stage}_*")
            if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml", ".md"}
        )
    return sorted(set(paths))


def _assert_fresh_source_identity() -> dict[str, str]:
    names = _source_names()
    dependencies: dict[str, str] = {}
    for path in _prior_artifacts():
        raw = path.read_text(encoding="utf-8", errors="replace").casefold()
        overlap = sorted(name for name in names if name.casefold() in raw)
        if overlap:
            raise ValueError(f"S230 source identity already appears in {path.name}: {overlap}")
        dependencies[path.relative_to(ROOT).as_posix()] = sha256_bytes(path.read_bytes())
    gold_raw = GOLD_PATH.read_text(encoding="utf-8").casefold()
    overlap = sorted(name for name in names if name.casefold() in gold_raw)
    if overlap:
        raise ValueError(f"S230 source identity appears in official gold: {overlap}")
    return dependencies


def freeze_receipts() -> None:
    existing = [path.name for path in (SELECTION_PATH, PIXEL_PATH) if path.exists()]
    if existing:
        raise FileExistsError(f"S230 receipt already exists: {existing}")
    _assert_fresh_source_identity()
    write_json(
        SELECTION_PATH,
        {
            "schema": "s230_kidde_fresh_selection_receipt_v1",
            "status": "FROZEN_BEFORE_MODEL_OR_BOT_OUTPUT",
            "selection_method": "source_identity_exclusion_then_human_pixel_geometry",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "items": [
                {
                    "canary_id": item["canary_id"],
                    "stratum": item["stratum"],
                    "source_pdfs": [source["source_pdf"] for source in item["sources"]],
                    "topic": item["topic"],
                }
                for item in ITEMS
            ],
        },
    )
    rows: list[dict[str, Any]] = []
    for item in ITEMS:
        for source in item["sources"]:
            for page, image_name in zip(source["pages"], source["image_names"], strict=True):
                image_rel = f"evals/s230_kidde_fresh_pages_v1/{image_name}"
                image_path = ROOT / image_rel
                data = image_path.read_bytes()
                with Image.open(image_path) as image:
                    width, height = image.size
                rows.append(
                    {
                        "canary_id": item["canary_id"],
                        "source_pdf": source["source_pdf"],
                        "page": page,
                        "image": image_rel,
                        "image_sha256": sha256_bytes(data),
                        "image_bytes": len(data),
                        "width_px": width,
                        "height_px": height,
                        "dpi": 200,
                        "status": "PASS_VISUALLY_INSPECTED_AT_ORIGINAL_RESOLUTION",
                        "visible_anchors": VISUAL_ANCHORS[image_name],
                    }
                )
    if len(rows) != len(VISUAL_ANCHORS):
        raise ValueError("S230 pixel receipt coverage mismatch")
    write_json(
        PIXEL_PATH,
        {
            "schema": "s230_kidde_fresh_pixel_receipts_v1",
            "status": "COMPLETE_BEFORE_FRONTIER_OUTPUT",
            "inspection_method": "200dpi_full_page_original_resolution_visual_review",
            "receipts": rows,
        },
    )


def _find_extraction(extraction_root: Path, source_pdf: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in extraction_root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        source_name = Path(str(payload.get("source_path") or "").replace("\\", "/")).name
        if source_name.casefold() == source_pdf.casefold():
            matches.append((path, payload))
    if len(matches) != 1:
        raise ValueError(f"expected one extraction for {source_pdf}, found {len(matches)}")
    return matches[0]


def build(pdf_root: Path, extraction_root: Path) -> dict[str, Any]:
    if not SELECTION_PATH.exists() or not PIXEL_PATH.exists():
        raise RuntimeError("freeze receipts before building S230")
    prior_dependencies = _assert_fresh_source_identity()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    pixels = json.loads(PIXEL_PATH.read_text(encoding="utf-8"))
    if selection.get("status") != "FROZEN_BEFORE_MODEL_OR_BOT_OUTPUT":
        raise ValueError("S230 selection is not frozen")
    if pixels.get("status") != "COMPLETE_BEFORE_FRONTIER_OUTPUT":
        raise ValueError("S230 pixel inspection is incomplete")
    receipts = {
        (row["canary_id"], row["source_pdf"], int(row["page"])): row
        for row in pixels["receipts"]
    }
    items: list[dict[str, Any]] = []
    extraction_dependencies: dict[str, str] = {}
    for spec in ITEMS:
        item = {key: value for key, value in spec.items() if key != "sources"}
        item.update({"sources": [], "rendered_pages": [], "evidence_units": []})
        for source_index, source_spec in enumerate(spec["sources"], 1):
            source_pdf = source_spec["source_pdf"]
            source_path = pdf_root / source_pdf
            extraction_path, extraction = _find_extraction(extraction_root, source_pdf)
            source_sha = sha256_bytes(source_path.read_bytes())
            if extraction.get("sha256") != source_sha:
                raise ValueError(f"PDF/extraction SHA drift: {source_pdf}")
            extraction_dependencies[str(extraction_path)] = sha256_bytes(extraction_path.read_bytes())
            pages_by_number = {int(page["page"]): page for page in extraction["result"]["pages"]}
            source_row = {
                "source_pdf": source_pdf,
                "path": f"Manuales_Kidde/{source_pdf}",
                "sha256": source_sha,
                "bytes": source_path.stat().st_size,
                "extraction": {
                    "path": str(extraction_path),
                    "sha256": sha256_bytes(extraction_path.read_bytes()),
                    "model": extraction.get("model"),
                },
                "pages": [],
            }
            for page, image_name in zip(source_spec["pages"], source_spec["image_names"], strict=True):
                page_payload = pages_by_number.get(page)
                markdown = str((page_payload or {}).get("md") or "")
                if not markdown.strip():
                    raise ValueError(f"empty extracted page {page}: {source_pdf}")
                receipt = receipts[(spec["canary_id"], source_pdf, page)]
                image_path = ROOT / receipt["image"]
                if sha256_bytes(image_path.read_bytes()) != receipt["image_sha256"]:
                    raise ValueError(f"pixel hash drift: {receipt['image']}")
                item["rendered_pages"].append(
                    {
                        "source_pdf": source_pdf,
                        "page": page,
                        "image": receipt["image"],
                        "image_sha256": receipt["image_sha256"],
                        "image_bytes": receipt["image_bytes"],
                        "width_px": receipt["width_px"],
                        "height_px": receipt["height_px"],
                        "dpi": 200,
                        "visual_inspection": {
                            "status": receipt["status"],
                            "visible_anchors": receipt["visible_anchors"],
                            "receipt_path": PIXEL_PATH.relative_to(ROOT).as_posix(),
                        },
                    }
                )
                source_row["pages"].append(
                    {
                        "page": page,
                        "markdown_sha256": sha256_bytes(markdown.encode("utf-8")),
                        "markdown_chars": len(markdown),
                    }
                )
                units = atomic_evidence_unit_rows(
                    markdown, f"{spec['canary_id']}_s{source_index}", page
                )
                for unit in units:
                    unit.update({"source_pdf": source_pdf, "page": page})
                    item["evidence_units"].append(unit)
            item["sources"].append(source_row)
        if len({unit["unit_id"] for unit in item["evidence_units"]}) != len(item["evidence_units"]):
            raise ValueError(f"duplicate evidence unit IDs: {spec['canary_id']}")
        items.append(item)

    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    official_coverage = [
        {
            "qid": str(row["qid"]),
            "question": str(row["question"]),
            "atomic_fact_texts": [
                str(fact.get("texto") or fact.get("text") or "")
                for fact in row.get("atomic_facts") or []
                if isinstance(fact, dict)
            ],
            "kind": "official_gold",
        }
        for row in gold_rows
        if row.get("qid") and row.get("question")
    ]
    selected_stems = {Path(name).stem.casefold() for name in _source_names()}
    hyq_coverage: list[dict[str, Any]] = []
    for line in HYQ_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("source_file") or "").casefold() not in selected_stems:
            continue
        for index, question in enumerate(row.get("questions") or [], 1):
            if isinstance(question, str) and question.strip():
                hyq_coverage.append(
                    {
                        "qid": f"hyq:{row['chunk_id']}:{index}",
                        "question": question,
                        "atomic_fact_texts": [],
                        "kind": "retriever_augmentation_not_test_gold",
                        "source_file": row["source_file"],
                        "page": int(row["page_number"]),
                    }
                )

    packet: dict[str, Any] = {
        "schema": "s230_kidde_fresh_clause_bound_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_AUTHORSHIP",
        "selection": {
            "method": "unused_source_identity_then_pixel_multidocument_geometry_v1",
            "candidate_items": len(items),
            "distinct_source_pdfs": len(_source_names()),
            "rendered_pages": len(VISUAL_ANCHORS),
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "target_calls": 0,
            "source_identity_overlap_with_s203_s217": 0,
            "source_identity_overlap_with_official_gold": 0,
        },
        "items": items,
        "existing_gold_coverage": official_coverage + hyq_coverage,
        "generation_contract": {
            "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "independent": {"model": "claude-fable-5", "effort": "xhigh"},
            "pixel_only_authorship_and_cross_review": True,
            "one_item_per_call": True,
            "strict_provider_structured_output": True,
            "per_call_receipt_before_semantic_validation": True,
            "same_item_retry": False,
            "candidate_merge_or_repair": False,
        },
        "execution_contract": {
            "frontier_generation_calls": 6,
            "frontier_reciprocal_review_calls_max": 6,
            "frontier_support_calls_max": 6,
            "frontier_paid_calls_max": 18,
            "provider_retries": 0,
            "target_calls": 0,
            "production": False,
        },
        "dependencies": {
            GOLD_PATH.relative_to(ROOT).as_posix(): sha256_bytes(GOLD_PATH.read_bytes()),
            HYQ_PATH.relative_to(ROOT).as_posix(): sha256_bytes(HYQ_PATH.read_bytes()),
            SELECTION_PATH.relative_to(ROOT).as_posix(): sha256_bytes(SELECTION_PATH.read_bytes()),
            PIXEL_PATH.relative_to(ROOT).as_posix(): sha256_bytes(PIXEL_PATH.read_bytes()),
            **prior_dependencies,
            **extraction_dependencies,
        },
    }
    packet["packet_sha256"] = stable_sha(packet)
    write_json(PACKET_PATH, packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--extraction-root", type=Path, required=True)
    parser.add_argument("--freeze-receipts", action="store_true")
    args = parser.parse_args()
    if args.freeze_receipts:
        freeze_receipts()
    packet = build(args.pdf_root, args.extraction_root)
    print(
        json.dumps(
            {
                "status": packet["status"],
                "items": len(packet["items"]),
                "sources": packet["selection"]["distinct_source_pdfs"],
                "pages": packet["selection"]["rendered_pages"],
                "packet_sha256": packet["packet_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
