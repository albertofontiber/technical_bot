import json
from copy import deepcopy

import pytest

from src.rag import post_rerank_coverage as post_rerank
from src.rag.compatibility_bundle_coverage import (
    LANE as COMPATIBILITY_LANE,
    build_compatibility_bundle,
)
from src.rag.doc_scoped_hyq_coverage import LANE as HYQ_LANE
from src.rag.document_local_coverage import (
    LANE as DOCUMENT_LOCAL_LANE,
    VALIDATION as DOCUMENT_LOCAL_VALIDATION,
)
from src.rag.post_rerank_coverage import (
    DOCUMENT_LOCAL_PREFIX_ANCHOR,
    DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR,
    DOCUMENT_LOCAL_STRUCTURAL_ANCHOR,
    _document_local_anchor_rows,
    _document_local_source_contract_rows,
    _has_substantive_coverage_card,
    append_validated_coverage,
    apply_post_rerank_coverage_with_trace,
    collect_cascaded_structural_coverage,
    collect_table_preamble_closure,
    coverage_context_content,
    has_exact_served_coverage_receipt,
    is_validated_coverage_chunk,
)
from src.rag.rerank_pool_coverage import LANE as POOL_LANE
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE
from src.rag.structural_neighbor_coverage import CASCADED_LANE as CASCADE_LANE
from src.rag.table_preamble_closure import LANE as TABLE_PREAMBLE_LANE


_COMPATIBILITY_QUERY = (
    "Tengo una central Detnov CAD-150 y un detector Notifier SDX-751; "
    "¿es compatible / puedo montarlo en su lazo?"
)
_RP1R_QUERY = "conectar el RP1r al software de gestion"


def _compatibility_bundle():
    groups = [
        {
            "token": "CAD-150",
            "ids": ["detnov:cad-150-8"],
            "sources": ["cad-install"],
        },
        {
            "token": "SDX-751",
            "ids": ["notifier:sdx-751"],
            "sources": ["notifier-manual"],
        },
    ]
    specs = [
        ("protocol", "protocol_scope", "notifier-manual", "Protocolo CLIP.", "notifier-doc", "a" * 64, 5),
        ("roster", "supported_device_roster", "notifier-manual", "Compatible: SDX-751.", "notifier-doc", "a" * 64, 6),
        ("topology", "loop_topology", "cad-install", "Lazo cerrado con retorno.", "cad-doc", "b" * 64, 2),
    ]
    rows = []
    for row_id, facet, source, content, document, extraction, index in specs:
        rows.append(
            {
                "id": row_id,
                "content": content,
                "source_file": source,
                "document_id": document,
                "extraction_sha256": extraction,
                "chunk_index": index,
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
        )
    return build_compatibility_bundle(_COMPATIBILITY_QUERY, rows, groups)


def _candidate(row_id="coverage", *, lane=STRUCTURAL_LANE):
    content = "La resistencia máxima del lazo es 35 ohmios."
    start = content.index("resistencia")
    end = len(content) - 1
    row = {
        "id": row_id,
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": lane,
        "local_semantic_validated": True,
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "start": start,
                "end": end,
                "quote": content[start:end],
                "facet": "loop_resistance",
                "exact_source_span_validated": True,
            }
        ],
    }
    if lane in {STRUCTURAL_LANE, CASCADE_LANE}:
        row["structural_neighbor_validated"] = True
    elif lane == TABLE_PREAMBLE_LANE:
        row["table_preamble_validated"] = True
    elif lane == POOL_LANE:
        row["rerank_pool_coverage_validated"] = True
    else:
        row["hyq_navigation_validated"] = True
    return row


def _with_exact_blob(
    row: dict,
    *,
    document_id: str = "active-document",
    extraction_sha256: str = "a" * 64,
    source_file: str = "manual.pdf",
) -> dict:
    exact = deepcopy(row)
    exact.update(
        {
            "document_id": document_id,
            "extraction_sha256": extraction_sha256,
            "source_file": source_file,
        }
    )
    return exact


def _source_contract_row(index: int = 1) -> dict:
    return {
        "document_id": f"00000000-0000-4000-8000-{index:012d}",
        "extraction_sha256": f"{index:064x}",
        "source_file": f"manual-{index}.pdf",
        "document_family": f"manual family {index}",
        "language": "es",
        "doc_type": "usuario",
        "manufacturer": "Fabricante",
        "product_model": f"Panel-{index}",
    }


def _install_source_contract_registry(
    monkeypatch,
    tmp_path,
    *,
    contracts: list[dict],
    resolved_documents: list[dict] | None = None,
    scope_owners: dict[tuple[str, str], frozenset[str]] | None = None,
    schema: str = "document_local_source_contracts_v1",
    max_scopes_per_query: int = 2,
):
    registry = tmp_path / "document_local_source_contracts.yaml"
    registry.write_text(
        json.dumps(
            {
                "schema": schema,
                "max_scopes_per_query": max_scopes_per_query,
                "contracts": contracts,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        post_rerank,
        "DOCUMENT_LOCAL_SOURCE_CONTRACT_CONFIG",
        registry,
    )
    monkeypatch.setattr(
        post_rerank,
        "resolve_query",
        lambda _query: {
            "resolved_documents": (
                resolved_documents if resolved_documents is not None else []
            )
        },
    )
    if scope_owners is None:
        scope_owners = {
            (contract["document_id"], contract["source_file"]): frozenset(
                {"test:product"}
            )
            for contract in contracts
        }
    monkeypatch.setattr(
        post_rerank,
        "governed_catalog_scope_owners",
        lambda: dict(scope_owners),
    )
    return registry


def _document_local_candidate(row_id="document-local"):
    row = _candidate(row_id, lane=STRUCTURAL_LANE)
    content = (
        "| Parametro | Valor |\n"
        "| --- | --- |\n"
        "| Rearme | t.A; 00 libre; 01 a 30 minutos de inhibicion. |\n"
        "\nFuera de registro."
    )
    start = content.index("| Rearme")
    end = content.index("00 libre") + len("00 libre")
    row.update(
        {
            "content": content,
            "coverage_cards": [
                {
                    "candidate_id": row_id,
                    "start": start,
                    "end": end,
                    "quote": content[start:end],
                    "facet": "timing_state",
                    "exact_source_span_validated": True,
                }
            ],
            "retrieval_lane": DOCUMENT_LOCAL_LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": DOCUMENT_LOCAL_VALIDATION,
            "document_id": "active-document",
            "document_revision_lineage_id": (
                "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
            ),
            "extraction_sha256": "a" * 64,
            "duplicate_of": None,
            "document_local_authority_document_id": "active-document",
            "document_local_authority_extraction_sha256": "a" * 64,
            "document_local_authority_source_file": "manual.pdf",
            "document_local_authority_revision_lineage_id": (
                "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
            ),
            "document_family": "manual panel",
            "language": "es",
            "doc_type": "usuario",
            "manufacturer": "Fabricante",
            "product_model": "Panel-X",
            "document_local_authority_document_family": "manual panel",
            "document_local_authority_language": "es",
            "document_local_authority_doc_type": "usuario",
            "document_local_authority_manufacturer": "Fabricante",
            "document_local_authority_product_model": "Panel-X",
        }
    )
    row.pop("structural_neighbor_validated")
    return row


def test_master_off_is_bit_inert_and_does_not_call_lanes():
    reranked = [{"id": "base", "content": "base"}]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled lane was called")

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=False,
        structural_enabled=True,
        table_preamble_enabled=True,
        hyq_enabled=True,
        pool_enabled=True,
        document_local_enabled=True,
        compatibility_enabled=True,
        structural_collector=forbidden,
        table_preamble_collector=forbidden,
        hyq_collector=forbidden,
        pool_collector=forbidden,
        document_local_collector=forbidden,
    )

    assert output is reranked
    assert trace["status"] == "disabled_or_not_applicable"


def test_document_local_flag_off_does_not_touch_resolver_or_registry(monkeypatch):
    reranked = [{"id": "base", "content": "base"}]

    class ExplodingRegistry:
        def read_text(self, *_args, **_kwargs):
            raise AssertionError("disabled document-local read its registry")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("disabled document-local touched its resolver or I/O")

    monkeypatch.setattr(
        post_rerank,
        "DOCUMENT_LOCAL_SOURCE_CONTRACT_CONFIG",
        ExplodingRegistry(),
    )
    monkeypatch.setattr(post_rerank, "resolve_query", forbidden)

    output, trace = apply_post_rerank_coverage_with_trace(
        "RP1r",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=forbidden,
    )

    assert output is reranked
    assert trace["status"] == "disabled_or_not_applicable"
    assert trace["lanes"] == []


def test_rp1r_governed_source_contract_generates_one_exact_blob_anchor():
    anchors, overflow = _document_local_source_contract_rows(_RP1R_QUERY)

    assert overflow is False
    assert len(anchors) == 1
    assert anchors[0]["document_id"] == "494e71be-873b-48c1-adb3-a21a122da111"
    assert anchors[0]["source_file"] == "HLSI-MN-103_RP1r-Supra_lr"
    assert anchors[0]["extraction_sha256"] == (
        "914ceacf8395729f73876cb9e397a8cb3154d70ba67903b6e055f2b4398be573"
    )
    assert anchors[0]["document_local_anchor_route"] == (
        DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
    )


def test_document_local_governed_contract_bypasses_structural_prerequisite():
    reranked = [{"id": "base", "content": "base"}]
    document_local = _document_local_candidate()
    observed = {}

    def document_local_collector(_query, anchors, covered):
        observed["anchors"] = deepcopy(anchors)
        observed["covered"] = [row["id"] for row in covered]
        return [document_local], {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "selected",
            "selected_ids": [document_local["id"]],
            "http_requests": 1,
            "model_calls": 0,
            "database_writes": 0,
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        _RP1R_QUERY,
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=document_local_collector,
    )

    assert [row["id"] for row in output] == ["base", "document-local"]
    assert observed["covered"] == ["base"]
    assert len(observed["anchors"]) == 1
    assert observed["anchors"][0]["document_local_anchor_route"] == (
        DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
    )
    assert observed["anchors"][0]["document_id"] == (
        "494e71be-873b-48c1-adb3-a21a122da111"
    )
    assert trace["protected_prefix_equal"] is True
    assert [lane["lane"] for lane in trace["lanes"]] == [DOCUMENT_LOCAL_LANE]


def test_document_local_lane_runs_only_after_a_served_structural_anchor():
    reranked = [{"id": "base", "content": "base"}]
    structural = _with_exact_blob(_candidate("anchor"))
    document_local = _document_local_candidate()
    observed = {}

    def structural_collector(_query, _reranked):
        return [structural], {"lane": STRUCTURAL_LANE, "status": "selected"}

    def document_local_collector(_query, anchors, covered):
        observed["anchors"] = [row["id"] for row in anchors]
        observed["anchor_routes"] = [
            row["document_local_anchor_route"] for row in anchors
        ]
        observed["covered"] = [row["id"] for row in covered]
        return [document_local], {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "selected",
            "selected_ids": [document_local["id"]],
            "http_requests": 2,
            "model_calls": 0,
            "database_writes": 0,
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=True,
        structural_enabled=True,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        structural_collector=structural_collector,
        document_local_collector=document_local_collector,
    )

    assert [row["id"] for row in output] == ["base", "anchor", "document-local"]
    assert observed == {
        "anchors": ["anchor"],
        "anchor_routes": [DOCUMENT_LOCAL_STRUCTURAL_ANCHOR],
        "covered": ["base", "anchor"],
    }
    assert trace["protected_prefix_equal"] is True
    assert [lane["lane"] for lane in trace["lanes"]] == [
        STRUCTURAL_LANE,
        DOCUMENT_LOCAL_LANE,
    ]


def test_document_local_already_served_winner_preserves_prefix_without_duplicate():
    reranked = [
        _with_exact_blob({"id": "already-served", "content": "target"})
    ]
    structural = _candidate("anchor")

    def structural_collector(_query, _reranked):
        return [structural], {"lane": STRUCTURAL_LANE, "status": "selected"}

    def document_local_collector(_query, anchors, covered):
        assert [row["id"] for row in anchors] == ["already-served"]
        assert anchors[0]["document_local_anchor_route"] == (
            DOCUMENT_LOCAL_PREFIX_ANCHOR
        )
        assert [row["id"] for row in covered] == ["already-served", "anchor"]
        return [], {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "best_candidate_already_covered",
            "selected_ids": [],
            "satisfied_ids": ["already-served"],
            "satisfaction_route": "already_served",
            "http_requests": 1,
            "model_calls": 0,
            "database_writes": 0,
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=True,
        structural_enabled=True,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        structural_collector=structural_collector,
        document_local_collector=document_local_collector,
    )

    assert output[0] is reranked[0]
    assert [row["id"] for row in output].count("already-served") == 1
    assert trace["protected_prefix_equal"] is True
    assert trace["lanes"][1]["satisfied_ids"] == ["already-served"]
    assert "already-served" not in trace["appended_ids"]


def test_document_local_anchor_fallback_keeps_prefix_order_dedupe_and_cap_two():
    reranked = [
        _with_exact_blob(
            {"id": "rank-1-invalid", "content": "invalid"},
            extraction_sha256="not-a-sha",
        ),
        _with_exact_blob(
            {"id": "rank-2", "content": "first"},
            document_id="legacy-document",
            extraction_sha256="b" * 64,
            source_file="legacy.pdf",
        ),
        _with_exact_blob(
            {"id": "rank-3", "content": "second"},
            document_id="governed-document",
            extraction_sha256="c" * 64,
            source_file="governed.pdf",
        ),
        _with_exact_blob(
            {"id": "rank-10-duplicate", "content": "duplicate"},
            document_id="governed-document",
            extraction_sha256="c" * 64,
            source_file="governed.pdf",
        ),
        _with_exact_blob(
            {"id": "rank-11-over-cap", "content": "third"},
            document_id="third-document",
            extraction_sha256="d" * 64,
            source_file="third.pdf",
        ),
    ]
    original_prefix = deepcopy(reranked)
    structural = [
        _with_exact_blob(
            _candidate("structural-over-cap"),
            document_id="structural-document",
            extraction_sha256="e" * 64,
            source_file="structural.pdf",
        )
    ]

    anchors = _document_local_anchor_rows(reranked, structural)

    assert [row["id"] for row in anchors] == ["rank-2", "rank-3"]
    assert [row["document_local_anchor_route"] for row in anchors] == [
        DOCUMENT_LOCAL_PREFIX_ANCHOR,
        DOCUMENT_LOCAL_PREFIX_ANCHOR,
    ]
    assert all(row["document_local_anchor_scopes_truncated"] for row in anchors)
    assert reranked == original_prefix
    assert all("document_local_anchor_route" not in row for row in reranked)


def test_document_local_anchor_rows_fill_remaining_slot_from_structural_append():
    prefix = _with_exact_blob(
        {"id": "prefix", "content": "prefix"},
        document_id="prefix-document",
        extraction_sha256="f" * 64,
        source_file="prefix.pdf",
    )
    duplicate = _with_exact_blob(
        _candidate("structural-duplicate"),
        document_id="prefix-document",
        extraction_sha256="f" * 64,
        source_file="prefix.pdf",
    )
    structural_fill = _with_exact_blob(
        _candidate("structural-fill"),
        document_id="structural-document",
        extraction_sha256="1" * 64,
        source_file="structural.pdf",
    )

    anchors = _document_local_anchor_rows(
        [prefix],
        [duplicate, structural_fill],
    )

    assert [row["id"] for row in anchors] == ["prefix", "structural-fill"]
    assert [row["document_local_anchor_route"] for row in anchors] == [
        DOCUMENT_LOCAL_PREFIX_ANCHOR,
        DOCUMENT_LOCAL_STRUCTURAL_ANCHOR,
    ]
    assert not any(row["document_local_anchor_scopes_truncated"] for row in anchors)


def test_document_local_governed_contract_is_exclusive_of_prefix_and_structural():
    prefix = _with_exact_blob(
        {"id": "prefix", "content": "prefix"},
        document_id="prefix-document",
        extraction_sha256="a" * 64,
        source_file="prefix.pdf",
    )
    structural = _with_exact_blob(
        _candidate("structural"),
        document_id="structural-document",
        extraction_sha256="b" * 64,
        source_file="structural.pdf",
    )
    source_contract = _source_contract_row(3)

    anchors = _document_local_anchor_rows(
        [prefix],
        [structural],
        [source_contract],
    )

    assert [row["document_id"] for row in anchors] == [
        source_contract["document_id"]
    ]
    assert [row["document_local_anchor_route"] for row in anchors] == [
        DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
    ]
    assert prefix["document_id"] not in {row["document_id"] for row in anchors}
    assert structural["document_id"] not in {
        row["document_id"] for row in anchors
    }


def test_non_target_query_without_governed_resolution_skips_contract_and_io(
    monkeypatch,
    tmp_path,
):
    reranked = [{"id": "base", "content": "base"}]
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=[_source_contract_row()],
        resolved_documents=[],
    )
    anchors, overflow = _document_local_source_contract_rows(
        "pregunta no target"
    )
    assert anchors == []
    assert overflow is False

    def forbidden(*_args, **_kwargs):
        raise AssertionError("document-local I/O ran without an anchor")

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta no target",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=forbidden,
    )

    assert output is reranked
    assert trace["lanes"] == [
        {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "skipped_no_served_structural_anchor",
            "selected_ids": [],
            "http_requests": 0,
            "model_calls": 0,
            "database_writes": 0,
        }
    ]


@pytest.mark.parametrize("registry_case", ["invalid", "ambiguous"])
def test_document_local_invalid_or_ambiguous_registry_fails_closed(
    monkeypatch,
    tmp_path,
    registry_case,
):
    contract = _source_contract_row()
    contracts = [contract]
    schema = "invalid_schema"
    if registry_case == "ambiguous":
        conflicting_contract = deepcopy(contract)
        conflicting_contract["extraction_sha256"] = "f" * 64
        contracts = [contract, conflicting_contract]
        schema = "document_local_source_contracts_v1"
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=contracts,
        resolved_documents=[
            {
                "document_id": contract["document_id"],
                "source_file": contract["source_file"],
            }
        ],
        schema=schema,
    )
    reranked = [{"id": "base", "content": "base"}]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("invalid registry reached document-local I/O")

    output, trace = apply_post_rerank_coverage_with_trace(
        "Panel-1",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=forbidden,
    )

    assert output is reranked
    assert trace["lanes"] == [
        {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "error",
            "error_type": "RuntimeError",
        }
    ]


def test_document_local_source_contract_orphan_scope_fails_before_resolution(
    monkeypatch,
    tmp_path,
):
    contract = _source_contract_row()
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=[contract],
        resolved_documents=[],
        scope_owners={},
    )

    def forbidden(_query):
        raise AssertionError("orphan registry reached query resolution")

    monkeypatch.setattr(post_rerank, "resolve_query", forbidden)

    with pytest.raises(
        RuntimeError,
        match="orphan document-local source-contract scope",
    ):
        _document_local_source_contract_rows("Panel-1")


def test_document_local_registry_rejects_three_contracts_for_same_owner(
    monkeypatch,
    tmp_path,
):
    contracts = [_source_contract_row(index) for index in range(1, 4)]
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=contracts,
        resolved_documents=[],
    )

    def forbidden(_query):
        raise AssertionError("product-overflow registry reached query resolution")

    monkeypatch.setattr(post_rerank, "resolve_query", forbidden)

    with pytest.raises(
        RuntimeError,
        match="document-local source-contract product overflow",
    ):
        _document_local_source_contract_rows("Paneles")


def test_document_local_source_contract_limit_accepts_two_before_io(
    monkeypatch,
    tmp_path,
):
    contracts = [_source_contract_row(index) for index in range(1, 3)]
    resolved_documents = [
        {
            "document_id": contract["document_id"],
            "source_file": contract["source_file"],
        }
        for contract in contracts
    ]
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=contracts,
        resolved_documents=resolved_documents,
    )
    anchors, overflow = _document_local_source_contract_rows("Paneles")
    assert overflow is False
    assert [row["document_id"] for row in anchors] == [
        contract["document_id"] for contract in contracts
    ]
    assert all(
        row["document_local_anchor_route"]
        == DOCUMENT_LOCAL_SOURCE_CONTRACT_ANCHOR
        for row in anchors
    )
    observed = {}

    def document_local_collector(_query, received_anchors, covered):
        observed["document_ids"] = [
            row["document_id"] for row in received_anchors
        ]
        observed["covered"] = [row["id"] for row in covered]
        return [], {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "no_validated_source_span",
            "selected_ids": [],
            "http_requests": 1,
            "model_calls": 0,
            "database_writes": 0,
        }

    reranked = [{"id": "base", "content": "base"}]
    output, trace = apply_post_rerank_coverage_with_trace(
        "Paneles",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=document_local_collector,
    )

    assert output is reranked
    assert observed == {
        "document_ids": [contract["document_id"] for contract in contracts],
        "covered": ["base"],
    }
    assert trace["lanes"][0]["http_requests"] == 1


def test_document_local_source_contract_overflow_fails_closed_before_io(
    monkeypatch,
    tmp_path,
):
    contracts = [_source_contract_row(index) for index in range(1, 4)]
    resolved_documents = [
        {
            "document_id": contract["document_id"],
            "source_file": contract["source_file"],
        }
        for contract in contracts
    ]
    scope_owners = {
        (contract["document_id"], contract["source_file"]): frozenset(
            {f"test:product:{index}"}
        )
        for index, contract in enumerate(contracts, 1)
    }
    _install_source_contract_registry(
        monkeypatch,
        tmp_path,
        contracts=contracts,
        resolved_documents=resolved_documents,
        scope_owners=scope_owners,
    )
    anchors, overflow = _document_local_source_contract_rows("Paneles")
    assert anchors == []
    assert overflow is True
    reranked = [{"id": "base", "content": "base"}]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("overflow reached document-local I/O")

    output, trace = apply_post_rerank_coverage_with_trace(
        "Paneles",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        document_local_collector=forbidden,
    )

    assert output is reranked
    assert trace["lanes"] == [
        {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "source_scope_overflow",
            "selected_ids": [],
            "satisfied_ids": [],
            "satisfaction_route": None,
            "http_requests": 0,
            "model_calls": 0,
            "database_writes": 0,
            "overflow": True,
        }
    ]


def test_compatibility_flag_off_is_inert_and_does_not_call_bundle_lane():
    reranked = [{"id": "base", "content": "base"}]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("default-off compatibility lane was called")

    output, trace = apply_post_rerank_coverage_with_trace(
        _COMPATIBILITY_QUERY,
        reranked,
        enabled=True,
        structural_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        compatibility_enabled=False,
        compatibility_collector=forbidden,
    )

    assert output is reranked
    assert trace["status"] == "disabled_or_not_applicable"


def test_complete_compatibility_bundle_appends_three_and_protects_prefix():
    reranked = [{"id": "base", "content": "base", "similarity": 0.9}]
    snapshot = deepcopy(reranked)
    calls = []

    def collector(query):
        calls.append(query)
        return _compatibility_bundle(), {
            "lane": COMPATIBILITY_LANE,
            "status": "selected_complete_relational_bundle",
        }

    def forbidden_hyq(*_args, **_kwargs):
        raise AssertionError("another lane must not bypass an applicable bundle gate")

    output, trace = apply_post_rerank_coverage_with_trace(
        _COMPATIBILITY_QUERY,
        reranked,
        retrieval_pool=[{"id": "pool-source"}],
        enabled=True,
        structural_enabled=True,
        hyq_enabled=True,
        pool_enabled=True,
        cascade_enabled=True,
        compatibility_enabled=True,
        compatibility_collector=collector,
        structural_collector=forbidden_hyq,
        hyq_collector=forbidden_hyq,
        pool_collector=forbidden_hyq,
        cascade_collector=forbidden_hyq,
    )

    assert calls == [_COMPATIBILITY_QUERY]
    assert reranked == snapshot
    assert output[:1] == snapshot
    assert len(output) == 4
    assert {row["retrieval_lane"] for row in output[1:]} == {COMPATIBILITY_LANE}
    assert all(is_validated_coverage_chunk(row) for row in output[1:])
    assert trace["protected_prefix_equal"] is True


def test_partial_compatibility_bundle_appends_nothing():
    reranked = [{"id": "base", "content": "base"}]
    partial = _compatibility_bundle()[:2]

    output, trace = apply_post_rerank_coverage_with_trace(
        _COMPATIBILITY_QUERY,
        reranked,
        enabled=True,
        structural_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        compatibility_enabled=True,
        compatibility_collector=lambda _query: (
            partial,
            {"lane": COMPATIBILITY_LANE, "status": "partial"},
        ),
    )

    assert output is reranked
    assert trace["status"] == "no_append"


def test_compatibility_bundle_is_atomic_against_prefix_duplicates_and_other_lanes():
    bundle = _compatibility_bundle()
    duplicate_prefix = [{"id": bundle[0]["id"], "content": "already reranked"}]
    assert append_validated_coverage(duplicate_prefix, bundle) is duplicate_prefix

    other_lane = [_candidate("structural-1"), _candidate("structural-2")]
    output = append_validated_coverage([], [*other_lane, *bundle])
    compatibility_rows = [
        row for row in output if row.get("retrieval_lane") == COMPATIBILITY_LANE
    ]
    assert len(compatibility_rows) == 3
    assert [row["id"] for row in output[:3]] == [row["id"] for row in bundle]


def test_append_preserves_prefix_and_attests_exact_real_source_span():
    reranked = [{"id": "base", "content": "base", "similarity": 0.9}]
    snapshot = deepcopy(reranked)

    output = append_validated_coverage(reranked, [_candidate()])

    assert reranked == snapshot
    assert output[:1] == snapshot
    assert output[0] is reranked[0]
    assert output[1]["coverage_validated"] is True
    assert output[1]["post_rerank_coverage_rank"] == 1
    assert is_validated_coverage_chunk(output[1]) is True


def test_table_preamble_lane_appends_only_its_exact_card_and_protects_prefix():
    reranked = [{"id": "base", "content": "base", "similarity": 0.9}]
    snapshot = deepcopy(reranked)
    content = (
        "Installation instructions.\n\n"
        "### Table 2: Wiring\n"
        "(Note: CH2 only exists on two-channel models)"
    )
    start = content.index("### Table 2")
    candidate = {
        "id": "preamble",
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": TABLE_PREAMBLE_LANE,
        "local_semantic_validated": True,
        "table_preamble_validated": True,
        "coverage_cards": [
            {
                "candidate_id": "preamble",
                "start": start,
                "end": len(content),
                "quote": content[start:],
                "facet": "table_preamble",
                "exact_source_span_validated": True,
            }
        ],
    }

    output = append_validated_coverage(reranked, [candidate])

    assert reranked == snapshot
    assert output[:1] == snapshot
    assert is_validated_coverage_chunk(output[1]) is True
    assert coverage_context_content(output[1]) == content[start:]
    assert "Installation instructions" not in coverage_context_content(output[1])


def test_table_preamble_collector_uses_bounded_exact_neighbor_read():
    seed = {
        "id": "table",
        "document_id": "doc",
        "extraction_sha256": "a" * 64,
        "chunk_index": 10,
        "section_title": "Table 2: Wiring",
        "content": "| A | B |\n| --- | --- |\n| 1 | 2 |",
    }
    predecessor = {
        "id": "preamble",
        "document_id": "doc",
        "extraction_sha256": "a" * 64,
        "chunk_index": 9,
        "section_title": "Table 2: Wiring",
        "source_file": "manual.pdf",
        "content": "### Table 2: Wiring\nNote",
    }
    observed = {}

    def fetcher(seeds, **kwargs):
        observed.update(kwargs)
        return seeds, [predecessor], {"http_requests": 2}

    selected, trace = collect_table_preamble_closure(
        "ignored relevance query", [seed], fetcher=fetcher
    )

    assert [row["id"] for row in selected] == ["preamble"]
    assert selected[0]["table_preamble_validated"] is True
    assert observed == {
        "max_gap": 1,
        "max_candidates": 64,
        "max_http_requests": 12,
        "timeout_seconds": 2.0,
    }
    assert trace["http_requests"] == 2


def test_table_preamble_collector_deduplicates_byte_identical_preambles():
    seeds = []
    predecessors = []
    for ordinal in range(2):
        document_id = f"doc-{ordinal}"
        seeds.append(
            {
                "id": f"table-{ordinal}",
                "document_id": document_id,
                "extraction_sha256": "a" * 64,
                "chunk_index": 10,
                "section_title": "Table 2: Wiring",
                "content": "| A | B |\n| --- | --- |\n| 1 | 2 |",
            }
        )
        predecessors.append(
            {
                "id": f"preamble-{ordinal}",
                "document_id": document_id,
                "extraction_sha256": "a" * 64,
                "chunk_index": 9,
                "section_title": "Table 2: Wiring",
                "source_file": f"manual-{ordinal}.pdf",
                "content": "### Table 2: Wiring\nSame note",
            }
        )

    selected, trace = collect_table_preamble_closure(
        "ignored",
        seeds,
        fetcher=lambda hydrated, **_kwargs: (
            hydrated,
            predecessors,
            {"http_requests": 2},
        ),
    )

    assert [row["id"] for row in selected] == ["preamble-0"]
    assert trace["duplicate_exact_preambles_rejected"] == 1


def test_rejects_tampered_span_unknown_lane_and_duplicate_parent():
    reranked = [{"id": "base", "content": "base"}]
    tampered = _candidate("tampered")
    tampered["coverage_cards"][0]["quote"] = "dato inventado"
    unknown = _candidate("unknown")
    unknown["retrieval_lane"] = "qid_specific_patch"
    duplicate = _candidate("base", lane=HYQ_LANE)

    assert append_validated_coverage(reranked, [tampered, unknown, duplicate]) is reranked


def test_generator_boundary_rejects_forged_attestation_without_lane_receipt():
    candidate = _candidate("forged", lane=HYQ_LANE)
    candidate.pop("hyq_navigation_validated")
    candidate.update({"coverage_validated": True, "post_rerank_coverage": True})

    assert is_validated_coverage_chunk(candidate) is False


def test_coverage_context_is_bounded_to_attested_exact_source_spans():
    content = "cabecera irrelevante\n\nDato de salida validado.\n\ncola irrelevante"
    quote = "Dato de salida validado."
    start = content.index(quote)
    candidate = {
        "id": "pool",
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": POOL_LANE,
        "local_semantic_validated": True,
        "rerank_pool_coverage_validated": True,
        "coverage_cards": [
            {
                "candidate_id": "pool",
                "start": start,
                "end": start + len(quote),
                "quote": quote,
                "facet": "output_action",
                "exact_source_span_validated": True,
            }
        ],
    }
    served = append_validated_coverage([], [candidate])[0]

    assert coverage_context_content(served) == quote
    assert served["content"] == content


def test_structural_coverage_context_uses_the_same_exact_excerpt_boundary():
    candidate = _candidate("structural-excerpt", lane=STRUCTURAL_LANE)
    served = append_validated_coverage([], [candidate])[0]
    card = candidate["coverage_cards"][0]

    assert coverage_context_content(served) == card["quote"]
    assert served["content"] == candidate["content"]


def test_coverage_context_finishes_a_bounded_markdown_table_row():
    content = (
        "| Parametro | Significado |\n"
        "| --- | --- |\n"
        "| r.I | Rearme inhibido: -- hasta finalizar; 00 permitido siempre "
        "(por defecto); 01 a 30 intervalo en minutos |\n"
        "\nOtra opcion no relacionada."
    )
    start = content.index("| r.I")
    clipped_end = content.index("hasta") + len("hasta")
    candidate = {
        "id": "table-row",
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": POOL_LANE,
        "local_semantic_validated": True,
        "rerank_pool_coverage_validated": True,
        "coverage_cards": [
            {
                "candidate_id": "table-row",
                "start": start,
                "end": clipped_end,
                "quote": content[start:clipped_end],
                "facet": "timing_state",
                "exact_source_span_validated": True,
            }
        ],
    }
    served = append_validated_coverage([], [candidate])[0]

    assert coverage_context_content(served) == content[start:clipped_end]
    assert has_exact_served_coverage_receipt(served) is True
    excerpt = coverage_context_content(served, logical_record_expansion=True)
    assert "00 permitido siempre (por defecto)" in excerpt
    assert "01 a 30 intervalo en minutos" in excerpt
    assert "Otra opcion no relacionada" not in excerpt


def test_coverage_context_does_not_expand_an_oversized_table_row():
    content = "| Parametro | " + ("x" * 1500) + " |"
    start = content.index("x")
    end = start + 80
    candidate = {
        "id": "oversized-row",
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": POOL_LANE,
        "local_semantic_validated": True,
        "rerank_pool_coverage_validated": True,
        "coverage_cards": [
            {
                "candidate_id": "oversized-row",
                "start": start,
                "end": end,
                "quote": content[start:end],
                "facet": "timing_state",
                "exact_source_span_validated": True,
            }
        ],
    }
    served = append_validated_coverage([], [candidate])[0]

    assert (
        coverage_context_content(served, logical_record_expansion=True)
        == content[start:end]
    )


def test_tampered_logical_record_receipt_is_rejected():
    candidate = _candidate("served-tamper", lane=POOL_LANE)
    served = append_validated_coverage([], [candidate])[0]
    served_card = served["served_coverage_cards"][0]
    served_card.update(
        {
            "start": 0,
            "end": 2,
            "quote": served["content"][:2],
        }
    )
    original_quote = served["coverage_cards"][0]["quote"]

    assert has_exact_served_coverage_receipt(served) is False
    assert is_validated_coverage_chunk(served) is True
    assert (
        coverage_context_content(served, logical_record_expansion=True)
        == original_quote
    )


def test_single_line_heading_with_a_field_value_is_substantive():
    candidate = {
        "coverage_cards": [
            {"quote": "## Longitud máxima del lazo: 2000 m"}
        ]
    }

    assert _has_substantive_coverage_card(candidate) is True


def test_lane_failure_is_fail_open_and_other_lane_can_still_append():
    reranked = [{"id": "base", "content": "base"}]

    def broken(_query, _reranked):
        raise TimeoutError("bounded read timed out")

    def hyq(_query):
        return [_candidate("hyq", lane=HYQ_LANE)], {"lane": HYQ_LANE, "status": "selected"}

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        enabled=True,
        structural_enabled=True,
        hyq_enabled=True,
        structural_collector=broken,
        hyq_collector=hyq,
    )

    assert [row["id"] for row in output] == ["base", "hyq"]
    assert trace["protected_prefix_equal"] is True
    assert trace["model_calls"] == 0
    assert trace["database_writes"] == 0
    assert trace["lanes"][0]["status"] == "error"


def test_structural_cascade_runs_after_pool_and_only_sees_pool_seeds():
    reranked = [{"id": "base", "content": "base"}]
    pool_candidate = _candidate("pool", lane=POOL_LANE)
    cascaded = _candidate("neighbor", lane=CASCADE_LANE)
    observed = []

    def pool_collector(_query, _pool, _context):
        return [pool_candidate], {"lane": POOL_LANE, "status": "selected"}

    def cascade_collector(_query, seeds):
        observed.extend(row["id"] for row in seeds)
        return [cascaded], {"lane": CASCADE_LANE, "status": "selected"}

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        retrieval_pool=[{"id": "source"}],
        enabled=True,
        structural_enabled=False,
        hyq_enabled=False,
        pool_enabled=True,
        cascade_enabled=True,
        pool_collector=pool_collector,
        cascade_collector=cascade_collector,
    )

    assert observed == ["pool"]
    assert [row["id"] for row in output] == ["base", "pool", "neighbor"]
    assert trace["protected_prefix_equal"] is True


def test_structural_cascade_has_separate_immediate_neighbor_budget():
    observed = {}
    seed = {
        "id": "pool",
        "document_id": "document",
        "extraction_sha256": "a" * 64,
        "chunk_index": 10,
    }

    def fetcher(seeds, **kwargs):
        observed.update(kwargs)
        return seeds, [], {"http_requests": 1}

    selected, trace = collect_cascaded_structural_coverage(
        "pregunta", [seed], fetcher=fetcher
    )

    assert selected == []
    assert trace["status"] == "no_validated_source_span"
    assert observed["max_gap"] == 1
    assert observed["max_candidates"] == 64
    assert observed["max_http_requests"] == 4


def test_structural_cascade_rejects_adjacent_index_across_distant_pages():
    seed = {
        "id": "pool",
        "document_id": "document",
        "extraction_sha256": "a" * 64,
        "chunk_index": 10,
        "page_number": 10,
    }
    distant_page = {
        "id": "neighbor",
        "document_id": "document",
        "extraction_sha256": "a" * 64,
        "chunk_index": 11,
        "page_number": 12,
        "language": "es",
        "content": "Inicio de lazo, retorno y terminales de cableado.",
    }

    def fetcher(seeds, **_kwargs):
        return seeds, [distant_page], {"http_requests": 1}

    selected, trace = collect_cascaded_structural_coverage(
        "resistencia final de línea del lazo", [seed], fetcher=fetcher
    )

    assert selected == []
    assert trace["page_local_candidates"] == 0


def test_structural_cascade_rejects_heading_only_evidence_card():
    seed = {
        "id": "pool",
        "document_id": "document",
        "extraction_sha256": "a" * 64,
        "chunk_index": 10,
        "page_number": 10,
    }
    heading_only = {
        "id": "neighbor",
        "document_id": "document",
        "extraction_sha256": "a" * 64,
        "chunk_index": 11,
        "page_number": 10,
        "language": "es",
        "source_file": "manual.pdf",
        "product_model": "modelo",
        "content": "### Tabla 2: Designaciones de los terminales de cableado",
    }

    def fetcher(seeds, **_kwargs):
        return seeds, [heading_only], {"http_requests": 1}

    selected, trace = collect_cascaded_structural_coverage(
        "¿Qué terminales de cableado tiene el lazo?", [seed], fetcher=fetcher
    )

    assert selected == []
    assert trace["non_substantive_selected_rejected"] == 1


def test_structural_cascade_skips_reads_when_append_budget_is_already_full():
    reranked = [{"id": "base", "content": "base"}]

    def structural_collector(_query, _reranked):
        return [
            _candidate("structural-1"),
            _candidate("structural-2"),
        ], {"lane": STRUCTURAL_LANE, "status": "selected"}

    def hyq_collector(_query):
        return [
            _candidate("hyq-1", lane=HYQ_LANE),
            _candidate("hyq-2", lane=HYQ_LANE),
        ], {"lane": HYQ_LANE, "status": "selected"}

    def pool_collector(_query, _pool, _context):
        return [_candidate("pool", lane=POOL_LANE)], {
            "lane": POOL_LANE,
            "status": "selected",
        }

    def forbidden_cascade(*_args, **_kwargs):
        raise AssertionError("cascade performed a read with no append capacity")

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        retrieval_pool=[{"id": "source"}],
        enabled=True,
        structural_enabled=True,
        hyq_enabled=True,
        pool_enabled=True,
        cascade_enabled=True,
        structural_collector=structural_collector,
        hyq_collector=hyq_collector,
        pool_collector=pool_collector,
        cascade_collector=forbidden_cascade,
    )

    assert len(output) - len(reranked) == 4
    assert trace["lanes"][-1]["status"] == "skipped_no_append_capacity"
    assert trace["lanes"][-1]["http_requests"] == 0


def test_structural_cascade_only_seeds_from_pool_rows_that_will_be_served():
    reranked = [{"id": "base", "content": "base"}]
    observed = []

    def structural_collector(_query, _reranked):
        return [_candidate("structural")], {
            "lane": STRUCTURAL_LANE,
            "status": "selected",
        }

    def pool_collector(_query, _pool, _context):
        return [
            _candidate("pool-served", lane=POOL_LANE),
            _candidate("pool-served-2", lane=POOL_LANE),
            _candidate("pool-lane-overflow", lane=POOL_LANE),
        ], {"lane": POOL_LANE, "status": "selected"}

    def cascade_collector(_query, seeds):
        observed.extend(row["id"] for row in seeds)
        return [], {"lane": CASCADE_LANE, "status": "no_validated_source_span"}

    output, _trace = apply_post_rerank_coverage_with_trace(
        "pregunta",
        reranked,
        retrieval_pool=[{"id": "source"}],
        enabled=True,
        structural_enabled=True,
        hyq_enabled=False,
        pool_enabled=True,
        cascade_enabled=True,
        structural_collector=structural_collector,
        pool_collector=pool_collector,
        cascade_collector=cascade_collector,
    )

    assert [row["id"] for row in output[1:]] == [
        "structural",
        "pool-served",
        "pool-served-2",
    ]
    assert observed == ["pool-served", "pool-served-2"]
