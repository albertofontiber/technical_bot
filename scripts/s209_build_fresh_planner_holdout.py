#!/usr/bin/env python3
"""Build the frozen S209 fresh-predicate planner holdout before model output."""
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

from src.rag.holdout_evidence import atomic_evidence_unit_rows  # noqa: E402
from src.rag.visual_gold import sha256_bytes, stable_sha, write_json  # noqa: E402


GOLD_PATH = ROOT / "evals/gold_answers_v1.yaml"
HYQ_PATH = ROOT / "evals/s99_hyq_generated.jsonl"
PACKET_PATH = ROOT / "evals/s209_fresh_planner_holdout_packet_v1.json"
PIXEL_RECEIPTS_PATH = ROOT / "evals/s209_pixel_inspection_receipts_v1.json"
SELECTION_RECEIPT_PATH = (
    ROOT / "evals/s209_kidde_predicate_selection_receipt_v1.json"
)
IMAGE_ROOT = ROOT / "evals/s209_kidde_planner_pages_v1"
PRIOR_PACKETS = tuple(
    [
        ROOT / f"evals/s{stage}_kidde_visual_canary_packet_v1.json"
        for stage in (203, 204, 205)
    ]
    + [
        ROOT / "evals/s207_decomposed_planner_holdout_packet_v1.json",
        ROOT / "evals/s208_multipage_planner_holdout_packet_v1.json",
    ]
)


ITEMS = (
    {
        "canary_id": "kidde_dp3020_detection_discrimination",
        "product": "Kidde Excellence KE-DP3020W dual optical smoke detector",
        "stratum": "genuine_cross_page_mechanism_and_specification",
        "topic": (
            "mecanismo de discriminacion de falsas alarmas del KE-DP3020W: "
            "combinacion optica y angular visible, principio de dispersion, "
            "supervision y rango de sensibilidad de particulas"
        ),
        "source_pdf": "ke-dp3020w-161721-es.pdf",
        "pages": [1, 2],
        "focus_pages": [1, 2],
        "cross_page_facts_min": 1,
        "novelty_terms": [
            "longitudes de onda opticas duales",
            "multiples angulos",
            "hacia adelante y hacia atras",
            "0.1 a 0.25 dB/m",
        ],
    },
    {
        "canary_id": "kidde_nc_maintenance_schedule",
        "product": "Kidde NC Series conventional fire alarm control panel",
        "stratum": "bounded_prerequisite_and_periodic_procedure",
        "topic": (
            "prerrequisito antes de pruebas y obligaciones trimestrales, "
            "anuales y de limpieza de la central NC"
        ),
        "source_pdf": (
            "bcn-3100018-es_r002_nc_series_fire_alarm_control_panel_"
            "operation_manual.pdf"
        ),
        "pages": [36],
        "focus_pages": [36],
        "cross_page_facts_min": 0,
        "novelty_terms": [
            "al menos un dispositivo por zona",
            "todos los dispositivos del sistema",
            "voltaje de las baterias",
            "productos que contengan disolventes",
        ],
    },
)


PIXEL_INSPECTION_ANCHORS = {
    ("kidde_dp3020_detection_discrimination", 1): [
        "dual optical wavelengths and multiple detection angles",
        "particle-size discrimination between real alarm sources and nuisance dust or steam",
        "details list for noise, steam and dust discrimination",
    ],
    ("kidde_dp3020_detection_discrimination", 2): [
        "forward and backward optical light-scattering principle",
        "selectable sensitivity and 0.1 to 0.25 dB/m plus or minus 20 percent particle-sensitivity range",
        "alarm-threshold, contamination-level and fault supervision",
    ],
    ("kidde_nc_maintenance_schedule", 36): [
        "pre-test fire-routing disable-or-notify prerequisite",
        "quarterly one-device-per-zone, panel-event, power-supply and battery-voltage checks",
        "annual all-device and electrical-connection checks plus cleaning restrictions",
    ],
}


def _pdf_names(row: dict[str, Any]) -> set[str]:
    names = {Path(str(value)).name.casefold() for value in row.get("pdfs_used") or []}
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            names.add(Path(str(citation["pdf"])).name.casefold())
    return names


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


def _render(document: fitz.Document, page_number: int, output: Path) -> dict[str, Any]:
    pixmap = document.load_page(page_number - 1).get_pixmap(dpi=200, alpha=False)
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
        "renderer": f"PyMuPDF {fitz.VersionBind}",
    }


def build(pdf_root: Path, extraction_root: Path) -> dict[str, Any]:
    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(gold_rows, list):
        raise ValueError("gold ledger must be a list")
    hyq = [
        json.loads(line)
        for line in HYQ_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected_names = {str(item["source_pdf"]).casefold() for item in ITEMS}
    official_names = set().union(*(_pdf_names(row) for row in gold_rows))
    official_overlap = sorted(selected_names & official_names)

    prior_names: set[str] = set()
    prior_dependencies: dict[str, str] = {}
    for path in PRIOR_PACKETS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        prior_names.update(
            str(item["source_pdf"]).casefold() for item in payload["items"]
        )
        prior_dependencies[path.relative_to(ROOT).as_posix()] = sha256_bytes(
            path.read_bytes()
        )
    prior_overlap = sorted(selected_names & prior_names)
    if prior_overlap:
        raise ValueError(f"S209 may not reuse prior visual cohorts: {prior_overlap}")

    pixel_receipts = json.loads(PIXEL_RECEIPTS_PATH.read_text(encoding="utf-8"))
    if pixel_receipts.get("status") != "COMPLETE_BEFORE_PACKET_FREEZE":
        raise ValueError("S209 pixel inspection receipts are not complete")
    inspection_by_key = {
        (row["canary_id"], int(row["page"])): row
        for row in pixel_receipts.get("receipts") or []
    }
    expected_inspections = {
        (str(item["canary_id"]), int(page))
        for item in ITEMS
        for page in item["pages"]
    }
    if set(inspection_by_key) != expected_inspections:
        raise ValueError("S209 pixel inspection receipt coverage mismatch")

    selection_receipt = json.loads(
        SELECTION_RECEIPT_PATH.read_text(encoding="utf-8")
    )
    if selection_receipt.get("status") != "CANDIDATES_SELECTED_BEFORE_MODEL_OUTPUT":
        raise ValueError("S209 predicate selection receipt is not frozen")
    if {row["canary_id"] for row in selection_receipt.get("selected") or []} != {
        str(item["canary_id"]) for item in ITEMS
    }:
        raise ValueError("S209 predicate selection receipt coverage mismatch")

    source_wide_coverage: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    extraction_dependencies: dict[str, str] = {}
    for spec in ITEMS:
        source_pdf = str(spec["source_pdf"])
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
        stem = Path(source_pdf).stem.casefold()
        source_hyq = [
            row for row in hyq if str(row.get("source_file") or "").casefold() == stem
        ]
        exact_questions = [
            question
            for row in source_hyq
            if int(row.get("page_number") or 0) in set(spec["focus_pages"])
            for question in row.get("questions") or []
            if isinstance(question, str) and question.strip()
        ]
        for row in source_hyq:
            for index, question in enumerate(row.get("questions") or [], 1):
                if isinstance(question, str) and question.strip():
                    source_wide_coverage.append(
                        {
                            "qid": f"hyq:{row['chunk_id']}:{index}",
                            "question": question,
                            "atomic_fact_texts": [],
                            "kind": "retriever_augmentation_not_test_gold",
                            "source_file": row["source_file"],
                            "page": int(row["page_number"]),
                        }
                    )

        renders: list[dict[str, Any]] = []
        source_pages: list[dict[str, Any]] = []
        evidence_units: list[dict[str, Any]] = []
        with fitz.open(source_path) as document:
            for page_number in spec["pages"]:
                page_payload = pages_by_number.get(page_number)
                if not page_payload:
                    raise ValueError(f"missing extracted page {page_number}: {source_pdf}")
                markdown = str(page_payload.get("md") or "")
                if not markdown.strip():
                    raise ValueError(f"empty extracted page {page_number}: {source_pdf}")
                rendered = _render(
                    document,
                    page_number,
                    IMAGE_ROOT / f"{spec['canary_id']}_p{page_number}_200dpi.png",
                )
                receipt = inspection_by_key[(str(spec["canary_id"]), page_number)]
                anchors = PIXEL_INSPECTION_ANCHORS[
                    (str(spec["canary_id"]), page_number)
                ]
                if (
                    receipt["status"] != "PASS"
                    or receipt["image"] != rendered["image"]
                    or receipt["image_sha256"] != rendered["image_sha256"]
                    or receipt["visible_anchors"] != anchors
                ):
                    raise ValueError("S209 pixel inspection receipt drift")
                rendered["visual_inspection"] = {
                    "protocol": "agent_full_page_pixel_inspection_v1",
                    "status": "PASS",
                    "inspected_at_utc": pixel_receipts["inspected_at_utc"],
                    "render_sha256_bound": rendered["image_sha256"],
                    "visible_anchors": anchors,
                    "receipt_path": PIXEL_RECEIPTS_PATH.relative_to(ROOT).as_posix(),
                }
                renders.append(rendered)
                source_pages.append(
                    {
                        "page": page_number,
                        "markdown_sha256": sha256_bytes(markdown.encode("utf-8")),
                        "markdown_chars": len(markdown),
                    }
                )
                evidence_units.extend(
                    atomic_evidence_unit_rows(
                        markdown, str(spec["canary_id"]), page_number
                    )
                )
        item = dict(spec)
        item["source"] = {
            "path": f"Manuales_Kidde/{source_pdf}",
            "sha256": source_sha,
            "bytes": source_path.stat().st_size,
        }
        item["extraction"] = {
            "path": str(extraction_path),
            "sha256": sha256_bytes(extraction_path.read_bytes()),
            "model": extraction.get("model"),
        }
        item["source_pages"] = source_pages
        item["rendered_pages"] = renders
        item["evidence_units"] = evidence_units
        item["novelty_receipt"] = {
            "same_source_hyq_rows": len(source_hyq),
            "same_source_hyq_questions": sum(
                len(row.get("questions") or []) for row in source_hyq
            ),
            "exact_focus_page_hyq_questions": exact_questions,
            "exact_page_presence_is_not_used_as_semantic_novelty": True,
            "source_identity_disclosed_to_frontier": True,
            "semantic_duplicate_veto": True,
        }
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
        "schema": "s209_fresh_planner_holdout_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_AUTHORSHIP",
        "selection": {
            "method": "pixel_audited_source_overlapping_fresh_predicate_candidates",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "retrieval_calls": 0,
            "database_calls": 0,
            "selected_items": len(items),
            "selected_documents": len({item["source_pdf"] for item in items}),
            "selected_source_overlap_with_official_gold": official_overlap,
            "selected_source_overlap_with_prior_visual_cohorts": prior_overlap,
            "external_validation_claimed": False,
            "source_independent_validation_claimed": False,
            "new_predicate_validation_claimed": False,
            "new_predicate_candidate_claimed": True,
            "semantic_novelty_requires_frontier_pass": True,
            "genuine_cross_page_items": sum(
                item["cross_page_facts_min"] > 0 for item in items
            ),
            "closed_lines_not_reopened": [
                "s208_same_cohort_retry_or_reinterpretation",
                "chunks_v3_wholesale",
                "answer_facet_ledger_s206",
            ],
        },
        "existing_gold_coverage": official_coverage + source_wide_coverage,
        "official_gold_question_count": len(official_coverage),
        "selected_source_hyq_question_count": len(source_wide_coverage),
        "items": items,
        "generation_contract": {
            "principal": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "independent": {"model": "claude-fable-5"},
            "pixel_only_authorship_and_cross_review": True,
            "multi_page_fact_schema": "explicit_citations_v3",
            "final_gold_author": "gpt-5.6-sol",
            "fable_must_pass_every_sol_candidate": True,
            "sol_counterpart_review_is_disagreement_probe": True,
            "same_item_retry": False,
            "candidate_merge_or_repair": False,
        },
        "support_contract": {
            "mapping": "exact_page_sets_and_all_minimal_equivalents_v3",
            "independent_review": "explicit_blocking_issues_and_notes_v4",
            "mapped_page_set_must_equal_declared_citation_page_set": True,
            "notes_cannot_change_verdict": True,
        },
        "planner_contract": {
            "mechanism": "decomposed_evidence_planner_v1_with_multipage_support_v3",
            "planner_model": "gpt-5.6-terra",
            "planner_reasoning_effort": "low",
            "gold_claims_and_support_ids_hidden_from_planner": True,
            "retrieval_calls": 0,
            "reranker_calls": 0,
            "database_calls": 0,
            "production": False,
        },
        "rendering_receipt": {
            "renderer": f"PyMuPDF_{fitz.VersionBind}_200dpi",
            "page_bound_pixel_receipts_completed_before_freeze": True,
            "pages_inspected": sum(len(item["rendered_pages"]) for item in items),
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
            "src/rag/planner_support_review.py": sha256_bytes(
                (ROOT / "src/rag/planner_support_review.py").read_bytes()
            ),
            **prior_dependencies,
            **extraction_dependencies,
        },
    }
    packet["packet_sha256"] = stable_sha(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--extraction-root", type=Path, required=True)
    args = parser.parse_args()
    packet = build(args.pdf_root.resolve(), args.extraction_root.resolve())
    write_json(PACKET_PATH, packet)
    print(
        json.dumps(
            {
                "status": packet["status"],
                "packet_sha256": packet["packet_sha256"],
                "items": len(packet["items"]),
                "pages": sum(len(item["rendered_pages"]) for item in packet["items"]),
                "evidence_units": sum(
                    len(item["evidence_units"]) for item in packet["items"]
                ),
                "cross_page_items": packet["selection"]["genuine_cross_page_items"],
                "official_source_overlaps": len(
                    packet["selection"]["selected_source_overlap_with_official_gold"]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
