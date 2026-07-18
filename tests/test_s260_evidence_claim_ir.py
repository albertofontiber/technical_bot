from __future__ import annotations

import inspect
import hashlib
from pathlib import Path

import pytest
import yaml

from scripts import s260_run_evidence_claim_ir as runner
from scripts.s260_run_evidence_claim_ir import render_answer, validate_claim_ir


ROOT = Path(__file__).resolve().parents[1]


def test_validate_and_render_claim_ir_derives_citations() -> None:
    claims = validate_claim_ir(
        {
            "claims": [
                {
                    "text": "El rango permitido es de 5 a 295 segundos, en pasos de 5 segundos.",
                    "fragment_numbers": [2],
                },
                {
                    "text": "Antes del mantenimiento se deben aislar los controles remotos.",
                    "fragment_numbers": [1, 3],
                },
            ]
        },
        fragment_count=3,
    )
    answer = render_answer(
        claims,
        [
            {"source_file": "manual-a", "page_number": 1},
            {"source_file": "manual-a", "page_number": 2},
            {"source_file": "manual-b", "page_number": 8},
        ],
    )
    assert "pasos de 5 segundos. [F2]" in answer
    assert "[F1] [F3]" in answer
    assert answer.count("El rango permitido") == 1


@pytest.mark.parametrize(
    "value",
    [
        {"claims": []},
        {"claims": [{"text": "Muy corta", "fragment_numbers": [1]}]},
        {
            "claims": [
                {
                    "text": "Una relación completa que contiene una cita inventada [F1].",
                    "fragment_numbers": [1],
                }
            ]
        },
        {
            "claims": [
                {
                    "text": "Una relación completa y suficientemente larga para validar.",
                    "fragment_numbers": [2],
                }
            ]
        },
    ],
)
def test_validate_claim_ir_fails_closed(value: dict) -> None:
    with pytest.raises(ValueError):
        validate_claim_ir(value, fragment_count=1)


def test_validate_claim_ir_rejects_duplicate_claims() -> None:
    text = "La verificación debe realizarse durante la puesta en marcha del sistema."
    with pytest.raises(ValueError, match="duplicate"):
        validate_claim_ir(
            {
                "claims": [
                    {"text": text, "fragment_numbers": [1]},
                    {"text": text.upper(), "fragment_numbers": [1]},
                ]
            },
            fragment_count=1,
        )


def test_generation_runner_does_not_name_or_import_score_content() -> None:
    source = inspect.getsource(runner)
    assert "s235_direct_clause_bound_score_packet_v1.json" not in source
    assert "frozen_obligations" not in source
    assert "frozen_conflicts" not in source


def _git_canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_prereg_frozen_inputs_match_git_canonical_text_bytes() -> None:
    prereg = yaml.safe_load(
        (ROOT / "evals/s260_evidence_claim_ir_prereg_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    for group in (
        "frozen_generation_inputs",
        "frozen_scoring_inputs",
    ):
        for spec in prereg[group].values():
            actual = _git_canonical_text_sha256(ROOT / spec["path"])
            assert actual == spec["sha256"], spec["path"]
