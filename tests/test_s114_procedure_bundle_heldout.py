import hashlib
import json
from pathlib import Path

from scripts.s114_procedure_bundle_section_challenge import build_payload
from src.rag.procedure_bundle_coverage import select_procedure_bundle_coverage


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_initial_cross_manufacturer_heldout_is_replayable_and_honestly_inconclusive():
    freeze_path = ROOT / "evals/s114_procedure_bundle_heldout_freeze_v1.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    replay = json.loads(
        (ROOT / "evals/s114_procedure_bundle_heldout_replay_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["freeze_sha256"] == _sha256(freeze_path)
    assert replay["gate"]["questions"] == 24
    assert replay["gate"]["manufacturers"] == 12
    assert replay["gate"]["database_get_requests"] == 23
    assert replay["gate"]["database_writes"] == replay["gate"]["model_calls"] == 0
    assert replay["gate"]["questions_with_appends"] == 0
    assert not any(replay["gate"]["potential_questions_by_facet"].values())
    assert replay["gate"]["adjudication_status"].endswith("APPLICABILITY_INCONCLUSIVE")

    sources = freeze["source_rows"]
    scopes = freeze["candidate_scopes"]
    for row in replay["rows"]:
        key = f"{row['manufacturer']}\u241f{row['product_model']}"
        selected, trace = select_procedure_bundle_coverage(
            row["question"], [sources[row["served_id"]]], scopes[key]
        )
        assert [str(item["id"]) for item in selected] == row["selected_ids"]
        assert trace["potential_facets"] == row["trace"]["potential_facets"]


def test_section_challenge_recomputes_complete_frozen_payload():
    frozen = json.loads(
        (ROOT / "evals/s114_procedure_bundle_section_challenge_v1.json").read_text(
            encoding="utf-8"
        )
    )
    recomputed = build_payload()
    for payload in (recomputed, frozen):
        payload["gate"].pop("max_selector_runtime_ms")
        for row in payload["rows"]:
            row.pop("selector_runtime_ms")
    assert recomputed == frozen
    gate = frozen["gate"]
    assert gate["source_reference_questions"] == 28
    assert gate["manufacturers"] == 5
    assert gate["potential_explicit_reference_questions"] == 11
    assert gate["selected_explicit_reference_questions"] == 10
    assert gate["all_source_span_receipts_verified"]
    assert gate["database_get_requests"] == gate["database_writes"] == 0
    assert gate["model_calls"] == 0
