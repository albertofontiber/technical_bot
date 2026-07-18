#!/usr/bin/env python3
"""Build the frozen S217 multi-source Kidde gold packet before model output."""
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
PIXEL_RECEIPTS_PATH = ROOT / "evals/s217_pixel_inspection_receipts_v1.json"
SELECTION_RECEIPT_PATH = (
    ROOT / "evals/s217_kidde_external_selection_receipt_v1.json"
)
PACKET_PATH = ROOT / "evals/s217_kidde_external_cohort_packet_v1.json"
PRIOR_PACKETS = tuple(
    [
        ROOT / f"evals/s{stage}_kidde_visual_canary_packet_v1.json"
        for stage in (203, 204, 205)
    ]
    + [
        ROOT / "evals/s207_decomposed_planner_holdout_packet_v1.json",
        ROOT / "evals/s208_multipage_planner_holdout_packet_v1.json",
        ROOT / "evals/s209_fresh_planner_holdout_packet_v1.json",
        ROOT / "evals/s214_kidde_multisource_gold_packet_v1.json",
    ]
)


ITEMS: tuple[dict[str, Any], ...] = (
    {
        "canary_id": "kidde_2xa_installation_operation_boundaries",
        "product": "Kidde 2X-A installation and operation workflows",
        "stratum": "multi_document_procedure_prerequisites",
        "topic": (
            "separacion precisa entre requisitos y conexiones de instalacion "
            "y las acciones operativas ante alarma o averia, incluyendo "
            "advertencias, resistencias, limites, orden y condiciones"
        ),
        "distinct_sources_min": 2,
        "cross_source_facts_min": 1,
        "known_conflicts": [],
        "sources": [
            {
                "source_pdf": "00-3280-507-4009-03_r003_2x-a_series_quick_installation_guide_es.pdf",
                "pages": [1, 2],
                "image_names": ["qi_es_p1.png", "qi_es_p2.png"],
            },
            {
                "source_pdf": "00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide_es.pdf",
                "pages": [1, 2],
                "image_names": ["qo_es_p1.png", "qo_es_p2.png"],
            },
        ],
    },
    {
        "canary_id": "kidde_2xaf2_variant_relational_matrix",
        "product": "Kidde 2X-AF2-FB, 2X-AF2-FB-S and 2X-AF2-SCFB panels",
        "stratum": "multi_document_variant_matrix",
        "topic": (
            "matriz relacional de interfaz, controles de bomberos, caja, lazos, "
            "salidas, bateria, dimensiones y limites de la variante escandinava, "
            "sin inferir recomendaciones a partir de especificaciones"
        ),
        "distinct_sources_min": 3,
        "cross_source_facts_min": 1,
        "known_conflicts": [
            {
                "source_pdf": "2x-af2-fb-s-161721-es.pdf",
                "field": "battery_capacity",
                "conflict": (
                    "page 2 lists a general capacity of 2 x 12 V / 18 Ah but "
                    "the supported batteries in the enclosure as 2 x 12 V / 7.2 Ah"
                ),
                "required_handling": (
                    "state both scoped rows if battery capacity is used; do not "
                    "collapse them into one value"
                ),
            }
        ],
        "sources": [
            {"source_pdf": "2x-af2-fb-161721-es.pdf", "pages": [1, 2],
             "image_names": ["af2_fb_p1.png", "af2_fb_p2.png"]},
            {"source_pdf": "2x-af2-fb-s-161721-es.pdf", "pages": [1, 2],
             "image_names": ["af2_fbs_p1.png", "af2_fbs_p2.png"]},
            {"source_pdf": "2x-af2-scfb-161721-es.pdf", "pages": [1, 2],
             "image_names": ["af2_scfb_p1.png", "af2_scfb_p2.png"]},
        ],
    },
    {
        "canary_id": "kidde_excellence_loop_device_roles",
        "product": "Kidde KE-DP3120W detector and KE-AS3115R-WMIP sounder/VAD",
        "stratum": "multi_document_architectural_roles",
        "topic": (
            "diferenciacion arquitectonica entre deteccion y notificacion en "
            "dos dispositivos Excellence, conservando funciones, alimentacion, "
            "aislamiento, base compartida, limites ambientales y valores propios"
        ),
        "distinct_sources_min": 2,
        "cross_source_facts_min": 1,
        "known_conflicts": [],
        "sources": [
            {"source_pdf": "ke-dp3120w-161721-es.pdf", "pages": [1, 3],
             "image_names": ["fresh_dp3120_p1.png", "fresh_dp3120_p3.png"]},
            {"source_pdf": "ke-as3115r-wmip-161721-es.pdf", "pages": [1, 2],
             "image_names": ["as3115_p1.png", "as3115_p2.png"]},
        ],
    },
    {
        "canary_id": "kidde_nc_panel_relational_matrix",
        "product": "Kidde NC-PF4 and NC-PF8-SC conventional panels",
        "stratum": "multi_document_qualified_panel_comparison",
        "topic": (
            "comparacion exacta de zonas, dispositivos por zona, interfaz "
            "escandinava, red, salidas, bateria, dimensiones y cargas entre "
            "NC-PF4 y NC-PF8-SC, manteniendo cada valor ligado a su modelo"
        ),
        "distinct_sources_min": 2,
        "cross_source_facts_min": 1,
        "known_conflicts": [],
        "sources": [
            {"source_pdf": "nc-pf4-161721-es.pdf", "pages": [1, 2],
             "image_names": ["nc_pf4_p1.png", "nc_pf4_p2.png"]},
            {"source_pdf": "nc-pf8-sc-161721-es.pdf", "pages": [1, 2],
             "image_names": ["nc_pf8sc_p1.png", "nc_pf8sc_p2.png"]},
        ],
    },
)


VISUAL_ANCHORS: dict[str, list[str]] = {
    "qi_es_p1.png": ["electrocution and ESD warnings", "mounting steps and insert variants"],
    "qi_es_p2.png": ["Class A loop limits", "15 kohm termination and installer password"],
    "qo_es_p1.png": ["alarm-versus-fault indicators", "alarm location/source/verification steps"],
    "qo_es_p2.png": ["sounder activation and evacuation", "fault silence prerequisite and reactivation"],
    "af2_fb_p1.png": ["2X-AF2-FB title", "fire brigade controls and expandable loops"],
    "af2_fb_p2.png": ["four-loop maximum", "large cabinet, eight sounder outputs and 18 Ah"],
    "af2_fbs_p1.png": ["2X-AF2-FB-S small-cabinet title", "fire brigade controls"],
    "af2_fbs_p2.png": ["two-loop maximum", "small cabinet and distinct battery rows"],
    "af2_scfb_p1.png": ["2X-AF2-SCFB title", "integrated Scandinavian interface"],
    "af2_scfb_p2.png": ["without fire brigade controls row", "four loops and 18 Ah"],
    "fresh_dp3120_p1.png": ["KE-DP3120W detector role", "dual optical detection and remote indicator"],
    "fresh_dp3120_p3.png": ["coverage/height/current rows", "negative-line isolator and base"],
    "as3115_p1.png": ["KE-AS3115R-WMIP notification role", "shared first-fix base and battery assist"],
    "as3115_p2.png": ["sound/VAD/current rows", "weatherproof limits and negative-line isolator"],
    "nc_pf4_p1.png": ["NC-PF4 four-zone title", "devices, supervised outputs and options"],
    "nc_pf4_p2.png": ["four zones/network limits", "7.2 Ah, dimensions and load rows"],
    "nc_pf8sc_p1.png": ["NC-PF8-SC eight-zone Scandinavian-key title", "output expansion"],
    "nc_pf8sc_p2.png": ["eight zones/network limits", "battery, dimensions and load rows"],
}


def freeze_receipts() -> None:
    """Persist the human-inspected selection and pixel receipts exactly once."""
    existing = [
        path.relative_to(ROOT).as_posix()
        for path in (SELECTION_RECEIPT_PATH, PIXEL_RECEIPTS_PATH)
        if path.exists()
    ]
    if existing:
        raise FileExistsError(f"S217 freeze artifacts already exist: {existing}")
    selected = [
        {
            "canary_id": item["canary_id"],
            "stratum": item["stratum"],
            "topic": item["topic"],
            "source_pdfs": [source["source_pdf"] for source in item["sources"]],
            "selection_reason": (
                "fresh external Kidde source identity with relational, qualified, "
                "or conditional multi-document evidence"
            ),
        }
        for item in ITEMS
    ]
    write_json(
        SELECTION_RECEIPT_PATH,
        {
            "schema": "s217_kidde_external_selection_receipt_v1",
            "status": "CANDIDATES_SELECTED_BEFORE_MODEL_OUTPUT",
            "selection_method": "fresh_external_source_identity_before_model_or_bot_output",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "selected": selected,
        },
    )
    receipts: list[dict[str, Any]] = []
    for item in ITEMS:
        for source in item["sources"]:
            for page, image_name in zip(
                source["pages"], source["image_names"], strict=True
            ):
                image_rel = f"evals/s217_kidde_external_pages_v1/{image_name}"
                image_path = ROOT / image_rel
                data = image_path.read_bytes()
                with Image.open(image_path) as image:
                    width, height = image.size
                receipts.append(
                    {
                        "canary_id": item["canary_id"],
                        "source_pdf": source["source_pdf"],
                        "page": page,
                        "image": image_rel,
                        "image_sha256": sha256_bytes(data),
                        "image_bytes": len(data),
                        "width_px": width,
                        "height_px": height,
                        "status": "PASS_VISUALLY_INSPECTED_AT_ORIGINAL_RESOLUTION",
                        "visible_anchors": VISUAL_ANCHORS[image_name],
                    }
                )
    if len(receipts) != len(VISUAL_ANCHORS):
        raise ValueError("S217 visual-anchor coverage mismatch")
    write_json(
        PIXEL_RECEIPTS_PATH,
        {
            "schema": "s217_pixel_inspection_receipts_v1",
            "status": "COMPLETE_BEFORE_PACKET_FREEZE",
            "inspection_method": "200dpi_full_page_original_resolution_visual_review",
            "receipts": receipts,
        },
    )

def _find_extraction(
    extraction_root: Path, source_pdf: str
) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in extraction_root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        source_name = Path(
            str(payload.get("source_path") or "").replace("\\", "/")
        ).name
        if source_name.casefold() == source_pdf.casefold():
            matches.append((path, payload))
    if len(matches) != 1:
        raise ValueError(f"expected one extraction for {source_pdf}, found {len(matches)}")
    return matches[0]


def _all_source_names() -> set[str]:
    return {
        source["source_pdf"]
        for item in ITEMS
        for source in item["sources"]
    }


def _assert_no_historical_identity_overlap() -> dict[str, str]:
    dependencies: dict[str, str] = {}
    for path in PRIOR_PACKETS:
        raw = path.read_text(encoding="utf-8")
        folded = raw.casefold()
        overlap = sorted(
            name for name in _all_source_names() if name.casefold() in folded
        )
        if overlap:
            raise ValueError(
                f"S217 source identity appears anywhere in {path.name}: {overlap}"
            )
        dependencies[path.relative_to(ROOT).as_posix()] = sha256_bytes(path.read_bytes())
    official_raw = GOLD_PATH.read_text(encoding="utf-8")
    official_folded = official_raw.casefold()
    official_overlap = sorted(
        name for name in _all_source_names() if name.casefold() in official_folded
    )
    if official_overlap:
        raise ValueError(f"S217 source identity appears in official gold: {official_overlap}")
    return dependencies


def build(pdf_root: Path, extraction_root: Path) -> dict[str, Any]:
    prior_dependencies = _assert_no_historical_identity_overlap()
    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(gold_rows, list):
        raise ValueError("gold ledger must be a list")
    hyq_rows = [
        json.loads(line)
        for line in HYQ_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    selection = json.loads(SELECTION_RECEIPT_PATH.read_text(encoding="utf-8"))
    if selection.get("status") != "CANDIDATES_SELECTED_BEFORE_MODEL_OUTPUT":
        raise ValueError("S217 selection receipt is not frozen")
    if {row["canary_id"] for row in selection.get("selected") or []} != {
        item["canary_id"] for item in ITEMS
    }:
        raise ValueError("S217 selection receipt coverage mismatch")

    pixels = json.loads(PIXEL_RECEIPTS_PATH.read_text(encoding="utf-8"))
    if pixels.get("status") != "COMPLETE_BEFORE_PACKET_FREEZE":
        raise ValueError("S217 pixel inspection is incomplete")
    receipt_by_key = {
        (row["canary_id"], row["source_pdf"], int(row["page"])): row
        for row in pixels.get("receipts") or []
    }
    expected_keys = {
        (item["canary_id"], source["source_pdf"], page)
        for item in ITEMS
        for source in item["sources"]
        for page in source["pages"]
    }
    if set(receipt_by_key) != expected_keys:
        raise ValueError("S217 pixel receipt source-page coverage mismatch")

    extraction_dependencies: dict[str, str] = {}
    items: list[dict[str, Any]] = []
    selected_stems = {Path(name).stem.casefold() for name in _all_source_names()}
    source_hyq_coverage: list[dict[str, Any]] = []
    for row in hyq_rows:
        if str(row.get("source_file") or "").casefold() not in selected_stems:
            continue
        for index, question in enumerate(row.get("questions") or [], 1):
            if isinstance(question, str) and question.strip():
                source_hyq_coverage.append(
                    {
                        "qid": f"hyq:{row['chunk_id']}:{index}",
                        "question": question,
                        "atomic_fact_texts": [],
                        "kind": "retriever_augmentation_not_test_gold",
                        "source_file": row["source_file"],
                        "page": int(row["page_number"]),
                    }
                )

    for spec in ITEMS:
        item = {key: value for key, value in spec.items() if key != "sources"}
        item["sources"] = []
        item["rendered_pages"] = []
        item["evidence_units"] = []
        for source_index, source_spec in enumerate(spec["sources"], 1):
            source_pdf = source_spec["source_pdf"]
            source_path = pdf_root / source_pdf
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            extraction_path, extraction = _find_extraction(extraction_root, source_pdf)
            source_sha = sha256_bytes(source_path.read_bytes())
            if extraction.get("sha256") != source_sha:
                raise ValueError(f"PDF/extraction SHA drift: {source_pdf}")
            extraction_dependencies[str(extraction_path)] = sha256_bytes(
                extraction_path.read_bytes()
            )
            pages_by_number = {
                int(page["page"]): page for page in extraction["result"]["pages"]
            }
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
            for page, image_name in zip(
                source_spec["pages"], source_spec["image_names"], strict=True
            ):
                page_payload = pages_by_number.get(page)
                if not page_payload:
                    raise ValueError(f"missing extracted page {page}: {source_pdf}")
                markdown = str(page_payload.get("md") or "")
                if not markdown.strip():
                    raise ValueError(f"empty extracted page {page}: {source_pdf}")
                receipt = receipt_by_key[(spec["canary_id"], source_pdf, page)]
                expected_image = f"evals/s217_kidde_external_pages_v1/{image_name}"
                if receipt["image"] != expected_image:
                    raise ValueError("S217 pixel image identity drift")
                image_path = ROOT / expected_image
                if sha256_bytes(image_path.read_bytes()) != receipt["image_sha256"]:
                    raise ValueError("S217 pixel image SHA drift")
                rendered = {
                    "source_pdf": source_pdf,
                    "page": page,
                    "image": expected_image,
                    "image_sha256": receipt["image_sha256"],
                    "image_bytes": receipt["image_bytes"],
                    "width_px": receipt["width_px"],
                    "height_px": receipt["height_px"],
                    "dpi": 200,
                    "visual_inspection": {
                        "status": receipt["status"],
                        "visible_anchors": receipt["visible_anchors"],
                        "receipt_path": PIXEL_RECEIPTS_PATH.relative_to(ROOT).as_posix(),
                    },
                }
                item["rendered_pages"].append(rendered)
                source_row["pages"].append(
                    {
                        "page": page,
                        "markdown_sha256": sha256_bytes(markdown.encode("utf-8")),
                        "markdown_chars": len(markdown),
                    }
                )
                unit_rows = atomic_evidence_unit_rows(
                    markdown,
                    f"{spec['canary_id']}_s{source_index}",
                    page,
                )
                for unit in unit_rows:
                    unit["source_pdf"] = source_pdf
                    unit["page"] = page
                    item["evidence_units"].append(unit)
            item["sources"].append(source_row)
        if len({unit["unit_id"] for unit in item["evidence_units"]}) != len(
            item["evidence_units"]
        ):
            raise ValueError(f"duplicate evidence-unit IDs: {spec['canary_id']}")
        items.append(item)

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

    packet: dict[str, Any] = {
        "schema": "s217_kidde_external_cohort_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_AUTHORSHIP",
        "selection": {
            "method": "fresh_external_source_identity_multidocument_pixel_cohort_v1",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "retrieval_calls": 0,
            "database_calls": 0,
            "candidate_items": len(items),
            "distinct_source_pdfs": len(_all_source_names()),
            "source_overlap_with_s203_s215": 0,
            "source_overlap_with_official_gold": 0,
            "minimum_pixel_gold_items": 3,
            "minimum_support_validated_items": 3,
            "semantic_novelty_requires_frontier_pass": True,
            "external_validation_claimed": False,
            "source_independent_validation_claimed": False,
            "official_fact_credit": 0,
            "closed_lines_not_reopened": [
                "s203_through_s209_questions_and_sources",
                "s213_same_cohort_retry_or_tuning",
                "chunks_v3_wholesale",
            ],
        },
        "existing_gold_coverage": official_coverage + source_hyq_coverage,
        "official_gold_question_count": len(official_coverage),
        "selected_source_hyq_question_count": len(source_hyq_coverage),
        "items": items,
        "generation_contract": {
            "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "independent": {"model": "claude-fable-5"},
            "pixel_only_authorship_and_cross_review": True,
            "principal_gold_author": "gpt-5.6-sol",
            "both_authors_must_be_independently_sufficient": True,
            "fable_must_pass_principal_candidate": True,
            "sol_counterpart_review_is_material_disagreement_probe": True,
            "item_level_fail_closed": True,
            "same_item_retry": False,
            "candidate_merge_or_repair": False,
        },
        "support_contract": {
            "principal_mapper": "gpt-5.6-sol",
            "independent_reviewer": "claude-fable-5",
            "mapping": "all_minimal_source_page_exact_unit_sets_v1",
            "item_level_fail_closed": True,
        },
        "execution_contract": {
            "frontier_generation_calls": 8,
            "frontier_review_calls_max": 8,
            "frontier_support_calls_max": 8,
            "frontier_paid_calls_max": 24,
            "provider_retries": 0,
            "target_calls": 0,
            "production": False,
        },
        "dependencies": {
            GOLD_PATH.relative_to(ROOT).as_posix(): sha256_bytes(GOLD_PATH.read_bytes()),
            HYQ_PATH.relative_to(ROOT).as_posix(): sha256_bytes(HYQ_PATH.read_bytes()),
            PIXEL_RECEIPTS_PATH.relative_to(ROOT).as_posix(): sha256_bytes(
                PIXEL_RECEIPTS_PATH.read_bytes()
            ),
            SELECTION_RECEIPT_PATH.relative_to(ROOT).as_posix(): sha256_bytes(
                SELECTION_RECEIPT_PATH.read_bytes()
            ),
            **prior_dependencies,
            **extraction_dependencies,
        },
    }
    packet["packet_sha256"] = stable_sha(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path)
    parser.add_argument("--extraction-root", type=Path)
    parser.add_argument("--freeze-receipts", action="store_true")
    args = parser.parse_args()
    if args.freeze_receipts:
        freeze_receipts()
        print(json.dumps({"status": "S217_SELECTION_AND_PIXELS_FROZEN", "paid_calls": 0}, indent=2))
        return 0
    if args.pdf_root is None or args.extraction_root is None:
        parser.error("--pdf-root and --extraction-root are required to build the packet")
    packet = build(args.pdf_root.resolve(), args.extraction_root.resolve())
    write_json(PACKET_PATH, packet)
    print(
        json.dumps(
            {
                "status": packet["status"],
                "packet_sha256": packet["packet_sha256"],
                "items": len(packet["items"]),
                "sources": packet["selection"]["distinct_source_pdfs"],
                "pages": sum(len(item["rendered_pages"]) for item in packet["items"]),
                "evidence_units": sum(len(item["evidence_units"]) for item in packet["items"]),
                "source_hyq_questions": packet["selected_source_hyq_question_count"],
                "paid_calls": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())








