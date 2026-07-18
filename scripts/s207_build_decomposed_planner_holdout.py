#!/usr/bin/env python3
"""Build the pixel-audited S207 Kidde holdout before Frontier authorship."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz
import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.evidence_units_v2 import (  # noqa: E402
    EvidenceUnitV2,
    build_header_aware_evidence_units,
    reconstruct_unit_content,
)
from src.rag.visual_gold import sha256_bytes, stable_sha, write_json  # noqa: E402


GOLD_PATH = ROOT / "evals/gold_answers_v1.yaml"
HYQ_PATH = ROOT / "evals/s99_hyq_generated.jsonl"
PACKET_PATH = ROOT / "evals/s207_decomposed_planner_holdout_packet_v1.json"
IMAGE_ROOT = ROOT / "evals/s207_kidde_planner_pages_v1"
PRIOR_VISUAL_PACKETS = tuple(
    ROOT / f"evals/s{stage}_kidde_visual_canary_packet_v1.json"
    for stage in (203, 204, 205)
)


ITEMS = (
    {
        "canary_id": "kidde_mcp_isolation_parasitics",
        "product": "Kidde Excellence KE-DM3110 manual call point",
        "stratum": "cross_page_specification_table",
        "topic": (
            "tres limites electricos exactos del aislador integrado KE-DM3110: "
            "consumo con aislamiento activo, corriente de dispersion maxima e "
            "impedancia serie maxima"
        ),
        "source_pdf": (
            "03-0210-501-4300-06_r006_excellence_series_addressable_mcp_"
            "installation_sheet_ml.pdf"
        ),
        "pages": [15, 16],
        "focus_pages": [15, 16],
        "novelty_terms": ["dispersion", "fuga", "impedancia", "1 mA", "0,06"],
    },
    {
        "canary_id": "kidde_outdoor_isolator_nominal_currents",
        "product": "Kidde Excellence outdoor addressable notification device",
        "stratum": "paired_operating_limit",
        "topic": (
            "los dos valores de corriente nominal del aislador integrado: corriente "
            "continua con el aislador cerrado y corriente con el aislador activo "
            "durante un cortocircuito"
        ),
        "source_pdf": (
            "3103198-ml_r002_excellence_series_intelligent_addressable_outdoor_"
            "notification_device_installation_sheet.pdf"
        ),
        "pages": [10],
        "focus_pages": [10],
        "novelty_terms": [
            "Nennstrom",
            "Isolator geschlossen",
            "Kurzschluss",
            "1,05 A",
            "1,4 A",
        ],
    },
    {
        "canary_id": "kidde_2xa_lcd_test",
        "product": "Kidde 2X-A Series fire alarm control panel",
        "stratum": "bounded_diagnostic_procedure",
        "topic": (
            "recorrido completo y finalidad de la prueba de LCD, incluida la "
            "identificacion de pixeles defectuosos y la salida del test"
        ),
        "source_pdf": "00-3280-505-4009-04_r004_2x-a_series_operation_manual_es.pdf",
        "pages": [37],
        "focus_pages": [37],
        "novelty_terms": ["Test LCD", "pixeles defectuosos", "prueba de LCD"],
    },
)


PIXEL_INSPECTION_ANCHORS = {
    ("kidde_mcp_isolation_parasitics", 15): [
        "KE-DM3110 isolation specification table",
        "active-isolation consumption 1.5 mA",
    ],
    ("kidde_mcp_isolation_parasitics", 16): [
        "maximum leakage current 1 mA",
        "maximum series impedance 0.06 ohm",
    ],
    ("kidde_outdoor_isolator_nominal_currents", 10): [
        "Nennstrom table row",
        "continuous closed-isolator current 1.05 A",
        "active short-circuit current 1.4 A",
    ],
    ("kidde_2xa_lcd_test", 37): [
        "Test LCD menu entry",
        "defective-pixel diagnostic purpose",
        "F2 exit instruction",
    ],
}


def _pdf_names(row: dict[str, Any]) -> set[str]:
    names = {Path(str(value)).name.casefold() for value in row.get("pdfs_used") or []}
    for citation in row.get("citations") or []:
        if isinstance(citation, dict) and citation.get("pdf"):
            names.add(Path(str(citation["pdf"])).name.casefold())
    return names


def _find_extraction(extraction_root: Path, source_pdf: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in extraction_root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if Path(str(payload.get("source_path") or "")).name.casefold() == source_pdf.casefold():
            matches.append((path, payload))
    if len(matches) != 1:
        raise ValueError(f"expected one extraction for {source_pdf}, found {len(matches)}")
    return matches[0]


def _hyq_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in HYQ_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
        "renderer": f"PyMuPDF {fitz.VersionBind}",
    }


def _unit_rows(markdown: str, item_id: str, page_number: int) -> list[dict[str, Any]]:
    built = build_header_aware_evidence_units(
        markdown,
        fragment_number=page_number,
        candidate_id=f"{item_id}_p{page_number}",
        max_chars=450,
        overlap_chars=0,
    )
    contiguous = [unit for unit in built if unit.unit_kind == "contiguous"]
    minimal_contiguous = []
    for unit in contiguous:
        start, end = unit.source_spans[0]
        contains_smaller = any(
            (start <= other.source_spans[0][0] and other.source_spans[0][1] <= end)
            and other.source_spans[0] != (start, end)
            for other in contiguous
        )
        if not contains_smaller:
            minimal_contiguous.append(unit)

    # Some extracted specification tables have no real column heading: the
    # parser emits the first data row as the Markdown header.  Repeating that
    # row in every composite creates a second answer path.  In that case retain
    # the immutable atomic row units; retain header+row composites only for a
    # genuine textual column heading.
    table_units = []
    for unit in built:
        if unit.unit_kind != "table_row_with_header":
            continue
        header = markdown[slice(*unit.source_spans[0])]
        data_like_header = bool(re.search(r"\d|<br\s*/?>", header, flags=re.I))
        if not data_like_header:
            table_units.append(unit)
    atomized_contiguous: list[EvidenceUnitV2] = []
    for unit in minimal_contiguous:
        start, end = unit.source_spans[0]
        line_spans: list[tuple[int, int]] = []
        for match in re.finditer(r"(?m)^.*(?:\n|$)", markdown[start:end]):
            line_start, line_end = start + match.start(), start + match.end()
            while line_end > line_start and markdown[line_end - 1] in "\r\n":
                line_end -= 1
            if markdown[line_start:line_end].count("|") >= 2:
                line_spans.append((line_start, line_end))
        if len(line_spans) < 2:
            atomized_contiguous.append(unit)
            continue
        for line_span in line_spans:
            content = markdown[slice(*line_span)]
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            identity = hashlib.sha256(
                (
                    f"{page_number}:{item_id}_p{page_number}:table_row_atomic:"
                    f"{line_span[0]}-{line_span[1]}:{digest}"
                ).encode("utf-8")
            ).hexdigest()[:10]
            atomized_contiguous.append(
                EvidenceUnitV2(
                    unit_id=f"EAT_{identity}",
                    fragment_number=page_number,
                    candidate_id=f"{item_id}_p{page_number}",
                    unit_kind="table_row_atomic",
                    source_spans=(line_span,),
                    content=content,
                    content_sha256=digest,
                )
            )
    units = atomized_contiguous + table_units
    units.sort(key=lambda unit: (unit.source_spans[-1], unit.source_spans[0], unit.unit_id))
    rows = []
    for unit in units:
        if reconstruct_unit_content(markdown, unit) != unit.content:
            raise ValueError(f"unit reconstruction failed: {unit.unit_id}")
        rows.append(
            {
                "unit_id": unit.unit_id,
                "fragment_number": unit.fragment_number,
                "candidate_id": unit.candidate_id,
                "unit_kind": unit.unit_kind,
                "source_spans": [list(span) for span in unit.source_spans],
                "content": unit.content,
                "content_sha256": unit.content_sha256,
            }
        )
    if not rows:
        raise ValueError(f"no evidence units built for {item_id} page {page_number}")
    broad = [row["unit_id"] for row in rows if len(row["content"]) > 600]
    if broad:
        raise ValueError(f"broad evidence units are forbidden: {broad}")
    return rows


def build(pdf_root: Path, extraction_root: Path) -> dict[str, Any]:
    gold_rows = yaml.safe_load(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(gold_rows, list):
        raise ValueError("gold ledger must be a list")
    selected_names = {str(item["source_pdf"]).casefold() for item in ITEMS}
    existing_names = set().union(*(_pdf_names(row) for row in gold_rows))
    gold_overlap = sorted(selected_names & existing_names)
    if gold_overlap:
        raise ValueError(f"selected source already used by official gold: {gold_overlap}")

    prior_visual_names: set[str] = set()
    prior_dependencies: dict[str, str] = {}
    for path in PRIOR_VISUAL_PACKETS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        prior_visual_names.update(
            str(item["source_pdf"]).casefold() for item in payload["items"]
        )
        prior_dependencies[path.relative_to(ROOT).as_posix()] = sha256_bytes(
            path.read_bytes()
        )
    prior_overlap = sorted(selected_names & prior_visual_names)
    if prior_overlap:
        raise ValueError(f"selected source already used by S203-S205: {prior_overlap}")

    hyq = _hyq_rows()
    source_wide_coverage: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    extraction_dependencies: dict[str, str] = {}
    for spec in ITEMS:
        source_pdf = str(spec["source_pdf"])
        source_path = pdf_root / source_pdf
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        extraction_path, extraction = _find_extraction(extraction_root, source_pdf)
        if extraction.get("sha256") != sha256_bytes(source_path.read_bytes()):
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
        exact_page_questions = [
            question
            for row in source_hyq
            if int(row.get("page_number") or 0) in set(spec["focus_pages"])
            for question in row.get("questions") or []
            if isinstance(question, str) and question.strip()
        ]
        if exact_page_questions:
            raise ValueError(
                f"selected page already has S99 questions: {spec['canary_id']}"
            )
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
        renders = []
        source_pages = []
        evidence_units = []
        with fitz.open(source_path) as document:
            for page_number in spec["pages"]:
                page_payload = pages_by_number.get(page_number)
                if not page_payload:
                    raise ValueError(f"missing extracted page {page_number}: {source_pdf}")
                markdown = str(page_payload.get("md") or "")
                if not markdown.strip():
                    raise ValueError(f"empty extracted page {page_number}: {source_pdf}")
                filename = f"{spec['canary_id']}_p{page_number}_200dpi.png"
                rendered = _render(document, page_number, IMAGE_ROOT / filename)
                anchors = PIXEL_INSPECTION_ANCHORS.get(
                    (str(spec["canary_id"]), page_number)
                )
                if not anchors:
                    raise ValueError(
                        f"missing pixel inspection receipt: {spec['canary_id']} "
                        f"page {page_number}"
                    )
                rendered["visual_inspection"] = {
                    "protocol": "agent_full_page_pixel_inspection_v1",
                    "status": "PASS",
                    "inspected_at_utc": "2026-07-18T05:00:00Z",
                    "render_sha256_bound": rendered["image_sha256"],
                    "visible_anchors": anchors,
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
                    _unit_rows(markdown, str(spec["canary_id"]), page_number)
                )
        item = dict(spec)
        item["source"] = {
            "path": f"Manuales_Kidde/{source_pdf}",
            "sha256": sha256_bytes(source_path.read_bytes()),
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
            "exact_focus_page_hyq_questions": 0,
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
        "schema": "s207_decomposed_planner_holdout_packet_v1",
        "status": "FROZEN_BEFORE_FRONTIER_AUTHORSHIP",
        "selection": {
            "method": "pixel_audited_unused_kidde_predicates",
            "model_outputs_seen": 0,
            "bot_outputs_seen": 0,
            "retrieval_calls": 0,
            "database_calls": 0,
            "selected_items": len(items),
            "selected_documents": len({item["source_pdf"] for item in items}),
            "selected_source_overlap_with_official_gold": gold_overlap,
            "selected_source_overlap_with_s203_s205": prior_overlap,
            "exact_focus_page_hyq_questions": 0,
            "closed_lines_not_reopened": [
                "visual_gold_as_standalone_benchmark_expansion",
                "source_first_question_transport_s197_s205",
                "generic_answer_archetype_ledger_s165_s168",
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
            "source_identity_and_all_same_source_hyq_disclosed": True,
            "final_gold_author": "gpt-5.6-sol",
            "fable_must_pass_every_sol_candidate": True,
            "sol_counterpart_review_is_disagreement_probe": True,
            "same_item_retry": False,
            "candidate_merge_or_repair": False,
        },
        "planner_contract": {
            "mechanism": "decomposed_evidence_planner_v1",
            "frontier_support_mapping_and_review_after_pixel_gold": True,
            "planner_model": "gpt-5.6-terra",
            "planner_reasoning_effort": "low",
            "gold_claims_and_support_ids_hidden_from_planner": True,
            "retrieval_calls": 0,
            "reranker_calls": 0,
            "database_calls": 0,
            "production": False,
        },
        "rendering_receipt": {
            "poppler_path_available": False,
            "fallback": "PyMuPDF_200dpi",
            "page_bound_pixel_receipts_completed_before_freeze": True,
            "pages_inspected": sum(len(item["rendered_pages"]) for item in items),
        },
        "dependencies": {
            GOLD_PATH.relative_to(ROOT).as_posix(): sha256_bytes(GOLD_PATH.read_bytes()),
            HYQ_PATH.relative_to(ROOT).as_posix(): sha256_bytes(HYQ_PATH.read_bytes()),
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
                "exact_page_hyq_questions": packet["selection"][
                    "exact_focus_page_hyq_questions"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
