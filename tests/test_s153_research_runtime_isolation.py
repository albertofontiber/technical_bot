from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_generator_keeps_the_stable_s122_contract():
    generator = (ROOT / "src/rag/generator.py").read_text(encoding="utf-8")
    assert "ANSWER_PLANNER_CONTRACT_S122" in generator
    assert "ANSWER_PLANNER_CONTRACT_S141" not in generator


def test_retriever_does_not_attach_the_closed_s141_identity_path():
    retriever = (ROOT / "src/rag/retriever.py").read_text(encoding="utf-8")
    assert "attach_query_source_identity" not in retriever


def test_answer_obligation_planner_remains_default_off():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ANSWER_OBLIGATION_PLANNER=off" in example

