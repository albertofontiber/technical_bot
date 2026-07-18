from __future__ import annotations

import pytest

from src.rag.relation_complete_highlights import (
    HighlightLimitError,
    build_relation_complete_highlights,
    reconstruct_highlight_content,
    render_inline_highlights,
    strip_inline_highlights,
    validate_request_highlight_count,
)


def _build(source: str):
    return build_relation_complete_highlights(
        source, fragment_number=2, candidate_id="synthetic-es-en"
    )


def test_numeric_range_unit_and_step_stay_in_one_atom() -> None:
    source = "El retardo se programa de 05 a 295 segundos, en pasos de 5 segundos."
    atoms = _build(source)
    assert any(source in atom.content for atom in atoms)
    assert any("numeric_bundle" in atom.reason_labels for atom in atoms)


def test_condition_action_and_target_stay_in_one_atom() -> None:
    source = (
        "When all input conditions are true, the output activates the assigned "
        "equipment until the reset condition occurs."
    )
    atoms = _build(source)
    assert any(source in atom.content for atom in atoms)
    assert any("condition_dependency" in atom.reason_labels for atom in atoms)


def test_table_row_is_bound_to_its_header() -> None:
    source = (
        "| Mode | Lower | Upper |\n"
        "| --- | ---: | ---: |\n"
        "| Fault | 80 % | 120 % |\n"
    )
    atoms = _build(source)
    matches = [atom for atom in atoms if "| Fault | 80 % | 120 % |" in atom.content]
    assert len(matches) == 1
    assert "| Mode | Lower | Upper |" in matches[0].content
    assert len(matches[0].source_spans) == 2


def test_list_members_are_bound_to_parent_heading() -> None:
    source = (
        "## Required checks\n\n"
        "- Verify the alarm output.\n"
        "- Test the remote warning.\n"
    )
    atoms = _build(source)
    assert any(
        "## Required checks" in atom.content
        and "Verify the alarm output" in atom.content
        and len(atom.source_spans) == 2
        for atom in atoms
    )


def test_span_identity_and_reconstruction_preserve_unicode_codepoints() -> None:
    source = "Precaución: debe comprobarse una tensión de 24 V antes del ensayo."
    first = _build(source)
    second = _build(source)
    assert first == second
    assert all(reconstruct_highlight_content(source, atom) == atom.content for atom in first)
    assert any("mandatory_safety_verification" in atom.reason_labels for atom in first)


def test_inline_renderer_changes_only_markers() -> None:
    source = (
        "When the pressure exceeds 10 bar, isolate the output.\n\n"
        "Ordinary explanatory prose remains unchanged."
    )
    rendered = render_inline_highlights(source, _build(source))
    assert "<s245 ids=" in rendered
    assert strip_inline_highlights(rendered) == source


def test_plain_narrative_without_technical_form_has_no_atoms() -> None:
    assert _build("The room is quiet and the corridor is clear.") == []


def test_fragment_limit_fails_closed_instead_of_truncating() -> None:
    source = "\n\n".join(
        f"When input {index} is active, output {index} must operate at {index + 1} V."
        for index in range(49)
    )
    with pytest.raises(HighlightLimitError):
        _build(source)


def test_request_limit_fails_closed() -> None:
    one = _build("When input is active, the output must operate at 24 V.")
    with pytest.raises(HighlightLimitError):
        validate_request_highlight_count([one] * 97)

