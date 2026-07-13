import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from s108_doc_scoped_hyq_replay import (  # noqa: E402
    PARENT_LIMIT,
    select_document_diverse_parents,
)


def test_document_scoped_hyq_parent_selection_is_bounded_and_source_diverse():
    rows = [
        {
            "chunk_id": f"a-{index}",
            "source_file": "manual-a",
            "page_number": index,
            "question": f"capacidad total lazos dispositivos variante {index}",
        }
        for index in range(8)
    ] + [
        {
            "chunk_id": "b-1",
            "source_file": "manual-b",
            "page_number": 1,
            "question": "capacidad total lazos dispositivos alternativa",
        }
    ]

    selected, scores = select_document_diverse_parents(
        ["capacidad total lazos dispositivos"], rows
    )

    assert "b-1" in selected
    assert len(selected) <= PARENT_LIMIT
    assert {row["source_file"] for row in scores[:2]} == {"manual-a", "manual-b"}


def test_document_scoped_hyq_selection_returns_no_parent_without_positive_signal():
    selected, _ = select_document_diverse_parents(
        ["capacidad lazos"],
        [
            {
                "chunk_id": "noise",
                "source_file": "manual-a",
                "page_number": 1,
                "question": "mantenimiento bateria",
            }
        ],
    )
    assert selected == []
