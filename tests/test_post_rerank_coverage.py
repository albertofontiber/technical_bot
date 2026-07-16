from copy import deepcopy

from src.rag.compatibility_bundle_coverage import (
    LANE as COMPATIBILITY_LANE,
    build_compatibility_bundle,
)
from src.rag.doc_scoped_hyq_coverage import LANE as HYQ_LANE
from src.rag.post_rerank_coverage import (
    _has_substantive_coverage_card,
    append_validated_coverage,
    apply_post_rerank_coverage_with_trace,
    collect_cascaded_structural_coverage,
    coverage_context_content,
    has_exact_served_coverage_receipt,
    is_validated_coverage_chunk,
)
from src.rag.rerank_pool_coverage import LANE as POOL_LANE
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE
from src.rag.structural_neighbor_coverage import CASCADED_LANE as CASCADE_LANE


_COMPATIBILITY_QUERY = (
    "Tengo una central Detnov CAD-150 y un detector Notifier SDX-751; "
    "¿es compatible / puedo montarlo en su lazo?"
)


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
    elif lane == POOL_LANE:
        row["rerank_pool_coverage_validated"] = True
    else:
        row["hyq_navigation_validated"] = True
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
        hyq_enabled=True,
        pool_enabled=True,
        compatibility_enabled=True,
        structural_collector=forbidden,
        hyq_collector=forbidden,
        pool_collector=forbidden,
    )

    assert output is reranked
    assert trace["status"] == "disabled_or_not_applicable"


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
