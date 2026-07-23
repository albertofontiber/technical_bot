from __future__ import annotations

import inspect
import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import s260_run_evidence_claim_ir as runner
from scripts.s260_run_evidence_claim_ir import render_answer, validate_claim_ir


ROOT = Path(__file__).resolve().parents[1]

# Commit that sealed the prereg's git-canonical frozen-input hashes
# ("Normalize S260 frozen text hashes"; the prereg records no commit id).
# The pins describe those blobs — src/rag/answer_planner.py legitimately
# evolved afterwards, so the assertion targets the sealed blobs (DEC-147:
# version, do not relax).
PREREG_SEAL_COMMIT = "9d966b6550929e5d15c6cd3eed40c90ee62a9b61"


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


def _sealed_git_canonical_text_sha256(relative: str) -> str:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{PREREG_SEAL_COMMIT}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"sealed blob missing: {relative}"
    return hashlib.sha256(completed.stdout.replace(b"\r\n", b"\n")).hexdigest()


def test_prereg_frozen_inputs_match_git_canonical_text_bytes() -> None:
    """DEC-147: the pins are matched against the blobs sealed at
    PREREG_SEAL_COMMIT, so the seal detects history tampering instead of
    failing on legitimate later development of the frozen inputs."""
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
            actual = _sealed_git_canonical_text_sha256(spec["path"])
            assert actual == spec["sha256"], spec["path"]
