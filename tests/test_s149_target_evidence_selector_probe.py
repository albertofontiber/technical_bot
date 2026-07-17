from __future__ import annotations

from types import SimpleNamespace

from scripts.s149_target_evidence_selector_probe import relation_anchors_covered


def _selected(candidate_id: str, content: str):
    return SimpleNamespace(unit=SimpleNamespace(candidate_id=candidate_id, content=content))


def test_relation_anchor_coverage_is_source_scoped_and_accent_insensitive() -> None:
    obligation = SimpleNamespace(
        candidate_id="source-a",
        required_anchors=("activación", "tipo software SND"),
    )
    assert relation_anchors_covered(
        obligation,
        (
            _selected("source-a", "La ACTIVACION se configura aquí."),
            _selected("source-a", "Use el tipo software SND."),
        ),
    )
    assert not relation_anchors_covered(
        obligation,
        (
            _selected("source-a", "La activación se configura aquí."),
            _selected("source-b", "Use el tipo software SND."),
        ),
    )
