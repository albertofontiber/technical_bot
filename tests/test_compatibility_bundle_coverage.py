from copy import deepcopy

import pytest

from src.rag.compatibility_bundle_coverage import (
    CONTRACT,
    build_compatibility_bundle,
    render_cross_manufacturer_compatibility_refusal,
    validate_compatibility_bundle,
)


QUERY = "¿Puedo conectar el panel HOST-100 con el detector DEV-200; son compatibles?"
GROUPS = [
    {
        "token": "HOST-100",
        "ids": ["maker-a:host-100"],
        "sources": ["host-installation"],
    },
    {
        "token": "DEV-200",
        "ids": ["maker-b:dev-200"],
        "sources": ["device-manual"],
    },
]


def _row(row_id, facet, source, content, *, document_id, extraction, chunk_index):
    return {
        "id": row_id,
        "content": content,
        "source_file": source,
        "document_id": document_id,
        "extraction_sha256": extraction,
        "chunk_index": chunk_index,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": 0,
                "end": len(content),
                "quote": content,
                "facet": facet,
                "exact_source_span_validated": True,
            }
        ],
    }


def _rows():
    return [
        _row(
            "protocol",
            "protocol_scope",
            "device-manual",
            "La familia utiliza el protocolo P-CLIP.",
            document_id="device-document",
            extraction="a" * 64,
            chunk_index=7,
        ),
        _row(
            "roster",
            "supported_device_roster",
            "device-manual",
            "Equipos compatibles: DEV-200 (óptico).",
            document_id="device-document",
            extraction="a" * 64,
            chunk_index=8,
        ),
        _row(
            "topology",
            "loop_topology",
            "host-installation",
            "El lazo del panel es un bucle cerrado con retorno.",
            document_id="host-document",
            extraction="b" * 64,
            chunk_index=3,
        ),
    ]


def test_builds_only_a_complete_relational_three_facet_bundle():
    bundle = build_compatibility_bundle(QUERY, _rows(), GROUPS)

    assert len(bundle) == 3
    assert validate_compatibility_bundle(bundle) is True
    assert {row["compatibility_facet"] for row in bundle} == {
        "protocol_scope",
        "supported_device_roster",
        "loop_topology",
    }
    assert {row["compatibility_bundle_id"] for row in bundle} == {
        bundle[0]["compatibility_bundle_id"]
    }
    assert all(row["compatibility_bundle_contract"] == CONTRACT for row in bundle)
    assert all(row["direct_interoperability_supported"] is False for row in bundle)
    assert {
        row["compatibility_entity_role"] for row in bundle
    } == {"queried_device", "host_system"}


@pytest.mark.parametrize("removed", ["protocol", "roster", "topology"])
def test_missing_any_required_facet_fails_closed(removed):
    rows = [row for row in _rows() if row["id"] != removed]

    with pytest.raises(ValueError, match="exactly three parents"):
        build_compatibility_bundle(QUERY, rows, GROUPS)


def test_unrelated_roster_and_cross_document_protocol_fail_closed():
    unrelated = _rows()
    unrelated[1]["content"] = "Equipos compatibles: OTHER-999."
    unrelated[1]["coverage_cards"][0].update(
        {
            "end": len(unrelated[1]["content"]),
            "quote": unrelated[1]["content"],
        }
    )
    with pytest.raises(ValueError, match="does not name"):
        build_compatibility_bundle(QUERY, unrelated, GROUPS)

    cross_document = _rows()
    cross_document[0]["document_id"] = "another-device-document"
    with pytest.raises(ValueError, match="one governed document"):
        build_compatibility_bundle(QUERY, cross_document, GROUPS)


def test_source_group_overlap_and_receipt_tampering_fail_closed():
    overlap = deepcopy(GROUPS)
    overlap[0]["sources"].append("device-manual")
    with pytest.raises(ValueError, match="overlap"):
        build_compatibility_bundle(QUERY, _rows(), overlap)

    bundle = build_compatibility_bundle(QUERY, _rows(), GROUPS)
    bundle[0]["coverage_cards"][0]["quote"] = "fabricated"
    assert validate_compatibility_bundle(bundle) is False

    marker_tamper = build_compatibility_bundle(QUERY, _rows(), GROUPS)
    marker_tamper[0]["cross_manufacturer"] = False
    assert validate_compatibility_bundle(marker_tamper) is False
    assert render_cross_manufacturer_compatibility_refusal(marker_tamper) is None

    duplicate_parent = _rows()
    duplicate_parent[1]["id"] = duplicate_parent[0]["id"]
    duplicate_parent[1]["coverage_cards"][0]["candidate_id"] = duplicate_parent[0]["id"]
    with pytest.raises(ValueError, match="must be distinct"):
        build_compatibility_bundle(QUERY, duplicate_parent, GROUPS)


def test_cross_manufacturer_renderer_refuses_unsupported_conclusion():
    bundle = build_compatibility_bundle(QUERY, _rows(), GROUPS)

    answer = render_cross_manufacturer_compatibility_refusal(bundle)

    assert answer is not None
    assert "No puedo confirmar la compatibilidad directa" in answer
    assert "no prueban por sí solas" in answer
    assert "HOST-100" not in answer  # no invented relationship beyond exact excerpts
    assert "DEV-200" in answer
    assert "Fuentes: device-manual; host-installation" in answer
