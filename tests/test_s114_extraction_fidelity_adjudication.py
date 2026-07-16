from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_s114_extraction_decision_is_bounded_by_measured_prevalence():
    data = yaml.safe_load(
        (ROOT / "evals/s114_extraction_fidelity_adjudication_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert data["corpus_snapshot"]["rows"] == 25090
    collapsed = data["findings"]["collapsed_scientific_notation"]
    assert collapsed["candidate_rows"] == 8
    assert collapsed["manufacturers"] == 1
    assert data["decision"]["full_extractor_rebuild"] == "NO_GO_INSUFFICIENT_LEVERAGE"
    assert data["decision"]["targeted_fidelity_gate"] == "GO_FOR_DESIGN_AND_SHADOW"
