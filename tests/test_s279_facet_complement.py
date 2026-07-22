"""s279 compuerta 2 — vía complementaria por-faceta (DOCUMENT_LOCAL_SELECTION_V2).

Fixtures sintéticos al estilo de ``tests/test_post_rerank_coverage.py`` /
``tests/test_s278_obligation_reserve.py``.  Sin red/DB/LLM (todo stub).  La vía
CAMBIA SELECCIÓN, no clases: la fila sirve por las clases existentes (pipe-row si
derivable; si no, prose_source_card).  Contratos pineados:

  - gate A7 (grupo de 2 términos excluido del gate y del orden);
  - orden A4 con cada tiebreak forzado (grado asc -> índice asc; y dentro del
    grupo terms_hit desc -> densidad asc -> chunk_index asc -> source_file asc ->
    id asc), candidato multi-grupo asignado al PRIMER grupo del orden;
  - attest A3: tampering de CADA campo + vista-con-fila-omitida => inválida;
  - enum A9: own | reused | skipped_no_uncovered_group | skipped_no_plan |
    skipped_scope_overflow | skipped_no_anchors;
  - flag off => byte-inerte (composición idéntica, sin lane por-faceta);
  - presupuesto PROPIO (vista 4+reserve llena AÚN sirve 1; budget consumido no);
  - convivencia con la reserve (A8: la reserve puede subir el grado y desactivar
    la vía);
  - control hp009 family-generic (no dispara).
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from src.rag import post_rerank_coverage as post_rerank
from src.rag.document_local_coverage import (
    LANE as DOCUMENT_LOCAL_LANE,
    VALIDATION as DOCUMENT_LOCAL_VALIDATION,
)
from src.rag.post_rerank_coverage import (
    N_FACET,
    _append_facet_complement,
    _attest_facet_complement,
    _facet_best_window,
    _facet_complement_row,
    _facet_gate_and_select,
    _facet_need_group_grade,
    _facet_served_view_sha256,
    _resolve_facet_complement_source,
    apply_post_rerank_coverage_with_trace,
    coverage_context_content,
    is_validated_coverage_chunk,
)
from src.rag.structural_neighbor_coverage import LANE as STRUCTURAL_LANE


ACTIVE_SHA = "a" * 64
ACTIVE_DOCUMENT = "active-document"
LINEAGE_ID = "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
GROUP_A = ["alfa", "beta", "gamma", "delta"]  # 4 términos
GROUP_C = ["sigma", "omega", "theta"]  # 3 términos
GROUP_2 = ["kappa", "lambda"]  # 2 términos (excluido del gate/orden)


def _plain(row_id: str, content: str, *, chunk_index: int = 5, source_file="manual"):
    return {
        "id": row_id,
        "content": content,
        "source_file": source_file,
        "chunk_index": chunk_index,
    }


def _plan(need_groups: list[list[str]], sha: str = "plansha") -> dict[str, Any]:
    return {"need_groups": [list(group) for group in need_groups], "sha256": sha}


# ---------------------------------------------------------------------------
# Ventana / grado (la regla de 360 chars reusada del pool selector).
# ---------------------------------------------------------------------------


def test_best_window_counts_distinct_group_terms():
    window = _facet_best_window("alfa beta gamma del sistema", GROUP_A)
    assert window is not None
    assert window["terms_hit"] == 3
    assert set(window["hits"]) == {"alfa", "beta", "gamma"}


def test_grade_is_max_distinct_terms_over_served_rows():
    served = [
        _plain("r1", "solo alfa aqui"),
        _plain("r2", "alfa beta juntos"),
        _plain("r3", "texto sin terminos utiles"),
    ]
    assert _facet_need_group_grade(served, GROUP_A) == 2


# ---------------------------------------------------------------------------
# Gate A7 — grupo de 2 términos excluido; >=1 grupo descubierto con >=3 términos.
# ---------------------------------------------------------------------------


def test_gate_two_term_group_is_excluded():
    served = [_plain("base", "contenido base neutro")]
    # Único grupo descubierto es de 2 términos -> excluido -> gate NO pasa.
    selection, status, grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_2]), [_plain("cand", "kappa lambda presentes")]
    )
    assert selection is None
    assert status == "skipped_no_uncovered_group"


def test_gate_passes_with_uncovered_three_term_group():
    served = [_plain("base", "contenido base neutro")]
    pool = [_plain("cand", "sigma omega theta en el candidato")]
    selection, status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_C]), pool
    )
    assert status == "ok"
    assert selection is not None
    assert selection["group_index"] == 0
    assert selection["candidate"]["id"] == "cand"


def test_gate_covered_group_does_not_pass():
    # El grupo ya está cubierto (grado>=N_FACET) por una fila servida.
    served = [_plain("base", "sigma omega theta ya servidos")]
    pool = [_plain("cand", "sigma omega theta candidato")]
    selection, status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_C]), pool
    )
    assert selection is None
    assert status == "skipped_no_uncovered_group"


# ---------------------------------------------------------------------------
# Orden A4 — cada tiebreak forzado.
# ---------------------------------------------------------------------------


def test_group_order_grade_asc_beats_index():
    # Grupo índice 0 (C) con grado 1; grupo índice 1 (A) con grado 0.
    # Orden entre grupos: grado asc => A (índice 1) va PRIMERO pese al índice.
    served = [_plain("base", "solo sigma presente aqui")]  # grade C=1, A=0
    candidate = _plain("multi", "sigma omega theta alfa beta gamma")
    selection, status, grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_C, GROUP_A]), [candidate]
    )
    assert status == "ok"
    assert grades == [1, 0]
    # multi-grupo asignado al PRIMER grupo del orden (A, índice 1).
    assert selection["group_index"] == 1


def test_group_order_index_asc_breaks_grade_tie():
    served = [_plain("base", "neutro")]
    # Dos grupos de 3 términos, ambos grado 0 -> índice asc.
    group_x = ["uno", "dos", "tres"]
    group_y = ["seis", "siete", "ocho"]
    candidate = _plain("cand", "uno dos tres seis siete ocho")
    selection, _status, grades, _groups = _facet_gate_and_select(
        served, [], _plan([group_x, group_y]), [candidate]
    )
    assert grades == [0, 0]
    assert selection["group_index"] == 0


def test_within_group_terms_hit_desc():
    served = [_plain("base", "neutro")]
    pool = [
        _plain("hit3", "alfa beta gamma"),
        _plain("hit4", "alfa beta gamma delta"),
    ]
    selection, _status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_A]), pool
    )
    assert selection["candidate"]["id"] == "hit4"
    assert selection["window"]["terms_hit"] == 4


def test_within_group_density_asc_breaks_terms_hit_tie():
    served = [_plain("base", "neutro")]
    spread = "alfa " + "x " * 40 + "beta " + "y " * 40 + "gamma"
    tight = "alfa beta gamma"
    pool = [
        _plain("spread", spread),
        _plain("tight", tight),
    ]
    selection, _status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_A]), pool
    )
    assert selection["candidate"]["id"] == "tight"


def test_within_group_chunk_index_then_source_then_id():
    served = [_plain("base", "neutro")]
    body = "alfa beta gamma"
    pool = [
        _plain("z-id", body, chunk_index=9, source_file="m"),
        _plain("a-id", body, chunk_index=9, source_file="m"),
        _plain("early", body, chunk_index=2, source_file="m"),
    ]
    selection, _status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_A]), pool
    )
    # chunk_index asc gana primero.
    assert selection["candidate"]["id"] == "early"

    # Empate en chunk_index -> source_file asc -> id asc.
    tie = [
        _plain("b-id", body, chunk_index=2, source_file="n"),
        _plain("a-id", body, chunk_index=2, source_file="m"),
        _plain("c-id", body, chunk_index=2, source_file="m"),
    ]
    selection2, _s, _g, _gr = _facet_gate_and_select(
        served, [], _plan([GROUP_A]), tie
    )
    # source_file "m" < "n"; entre "m" gana id "a-id".
    assert selection2["candidate"]["id"] == "a-id"


def test_multi_group_candidate_assigned_to_first_ordered_group():
    served = [_plain("base", "neutro")]  # ambos grupos grado 0
    candidate = _plain("multi", "sigma omega theta alfa beta gamma")
    # Orden por grado asc (0,0) -> índice asc: grupo 0 (C) primero.
    selection, _status, _grades, _groups = _facet_gate_and_select(
        served, [], _plan([GROUP_C, GROUP_A]), [candidate]
    )
    assert selection["group_index"] == 0
    assert set(selection["window"]["hits"]) == {"sigma", "omega", "theta"}


# ---------------------------------------------------------------------------
# Fila document-local cruda (identidad de autoridad ya estampada por el RPC).
# ---------------------------------------------------------------------------


def _dl_candidate(
    row_id: str, content: str, *, chunk_index: int = 7, source_file: str = "manual"
) -> dict[str, Any]:
    return {
        "id": row_id,
        "content": content,
        "chunk_index": chunk_index,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
        "source_file": source_file,
        "duplicate_of": None,
        "document_status": "active",
        "document_revision": "v.01",
        "document_revision_lineage_id": LINEAGE_ID,
        "document_family": "manual panel",
        "language": "es",
        "doc_type": "usuario",
        "manufacturer": "Fabricante",
        "product_model": "Panel-X",
        "document_local_authority_document_id": ACTIVE_DOCUMENT,
        "document_local_authority_extraction_sha256": ACTIVE_SHA,
        "document_local_authority_source_file": source_file,
        "document_local_authority_revision_lineage_id": LINEAGE_ID,
        "document_local_authority_document_family": "manual panel",
        "document_local_authority_language": "es",
        "document_local_authority_doc_type": "usuario",
        "document_local_authority_manufacturer": "Fabricante",
        "document_local_authority_product_model": "Panel-X",
    }


_PROSE_SENTENCE = "Estas maniobras actuan sobre alfa beta gamma del sistema."


def _served_facet_row(monkeypatch, *, served=None, plan=None):
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    served = served if served is not None else [_plain("base", "contenido base neutro")]
    plan = plan if plan is not None else _plan([GROUP_A], sha="plansha-prose")
    candidate = _dl_candidate("facet-target", _PROSE_SENTENCE)
    selection, status, _grades, _groups = _facet_gate_and_select(
        served, [], plan, [candidate]
    )
    assert status == "ok", status
    attested = _facet_complement_row(
        selection, served, plan_sha256=str(plan["sha256"])
    )
    assert attested is not None
    return attested, served, plan


# ---------------------------------------------------------------------------
# Serving por las CLASES EXISTENTES (prosa) + validación de la fila.
# ---------------------------------------------------------------------------


def test_facet_row_serves_as_prose_source_card(monkeypatch):
    attested, _served, _plan_used = _served_facet_row(monkeypatch)

    assert attested["retrieval_lane"] == DOCUMENT_LOCAL_LANE
    assert attested["document_local_coverage_validation"] == DOCUMENT_LOCAL_VALIDATION
    assert attested["facet_complement_validated"] is True
    # NUNCA se estampa local_semantic_validated en la FILA.
    assert "local_semantic_validated" not in attested
    # Sirve por la clase existente de prosa (oración completa verbatim).
    assert attested["post_rerank_coverage_contract"] == (
        "exact_source_bounded_prose_sentence_span_v1"
    )
    assert is_validated_coverage_chunk(attested) is True
    assert coverage_context_content(attested) == _PROSE_SENTENCE


def test_pipe_class_content_fails_closed_without_prose(monkeypatch):
    """Una ventana de 360 chars sobre una tabla toca encabezado+datos (dos
    filas de datos) => clase pipe NO derivable; sin prosa-idad positiva la fila
    NO se sirve (fail-closed) — la vía nunca inventa una clase."""
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    content = (
        "| Campo | Detalle |\n"
        "| --- | --- |\n"
        "| Estado | alfa beta gamma en la fila de datos. |\n"
    )
    candidate = _dl_candidate("pipe-target", content)
    served = [_plain("base", "contenido base neutro")]
    plan = _plan([GROUP_A], sha="plansha-pipe")
    selection, status, _g, _gr = _facet_gate_and_select(served, [], plan, [candidate])
    assert status == "ok"
    attested = _facet_complement_row(selection, served, plan_sha256=str(plan["sha256"]))
    assert attested is None


# ---------------------------------------------------------------------------
# Attest A3 — tampering de CADA campo + vista-con-fila-omitida => inválida.
# ---------------------------------------------------------------------------


def test_valid_attestation_passes(monkeypatch):
    attested, served, plan = _served_facet_row(monkeypatch)
    assert _attest_facet_complement(attested, served, plan) is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("facet_complement_plan_sha256", "otro-sha"),
        ("facet_complement_need_group_index", 3),
        ("facet_complement_need_group_terms", ["alfa", "beta", "zeta"]),
        ("facet_complement_window_bounds", [0, 3]),
        ("facet_complement_quote_sha256", "0" * 64),
        ("facet_complement_served_view_sha256", "0" * 64),
        ("facet_complement_validated", False),
    ],
)
def test_tampered_attestation_field_is_invalid(monkeypatch, field, value):
    attested, served, plan = _served_facet_row(monkeypatch)
    assert _attest_facet_complement(attested, served, plan) is True

    attested[field] = value

    assert _attest_facet_complement(attested, served, plan) is False


def test_tampered_candidate_content_is_invalid(monkeypatch):
    attested, served, plan = _served_facet_row(monkeypatch)
    attested["content"] = attested["content"].replace("gamma", "zzzzz")
    assert _attest_facet_complement(attested, served, plan) is False


def test_omitting_a_served_row_invalidates_attestation(monkeypatch):
    served = [
        _plain("base", "contenido base neutro"),
        _plain("extra", "otra fila servida neutra"),
    ]
    attested, _served, plan = _served_facet_row(monkeypatch, served=served)
    assert _attest_facet_complement(attested, served, plan) is True

    # La vista real omite una fila servida => sha del conjunto cambia => inválida.
    assert _attest_facet_complement(attested, served[:1], plan) is False


def test_served_view_that_now_covers_the_group_invalidates(monkeypatch):
    attested, served, plan = _served_facet_row(monkeypatch)
    # Una vista donde el grupo YA está cubierto (grado>=N_FACET) => no-cobertura
    # falla aunque el sha se recompute sobre esa vista.
    covering = served + [_plain("cover", "alfa beta gamma ya cubiertos")]
    assert _attest_facet_complement(attested, covering, plan) is False


# ---------------------------------------------------------------------------
# Enum A9 — los 6 valores de facet_fetch.
# ---------------------------------------------------------------------------


_ANCHOR = {
    "document_id": ACTIVE_DOCUMENT,
    "extraction_sha256": ACTIVE_SHA,
    "source_file": "manual",
    "document_local_anchor_route": "governed_source_contract",
    "manufacturer": "Fabricante",
    "product_model": "Panel-X",
}


def test_a9_reused_from_cache():
    cache = {"candidates": [_plain("c", "x")], "plan": _plan([GROUP_A])}
    source = _resolve_facet_complement_source("q", [], [], cache)
    assert source["facet_fetch"] == "reused"
    assert source["plan_rederived"] is False
    assert source["candidate_pool"] == cache["candidates"]


def test_a9_skipped_scope_overflow(monkeypatch):
    monkeypatch.setattr(
        post_rerank, "_document_local_source_contract_rows", lambda _q: ([], True)
    )
    source = _resolve_facet_complement_source("q", [], [], {})
    assert source["facet_fetch"] == "skipped_scope_overflow"
    assert source["plan_rederived"] is True


def test_a9_skipped_no_anchors(monkeypatch):
    monkeypatch.setattr(
        post_rerank, "_document_local_source_contract_rows", lambda _q: ([], False)
    )
    # served sin filas estructurales servidas => sin anchors.
    source = _resolve_facet_complement_source("q", [{"id": "base"}], [{"id": "base"}], {})
    assert source["facet_fetch"] == "skipped_no_anchors"


def test_a9_skipped_no_plan(monkeypatch):
    from src.rag import document_local_coverage

    monkeypatch.setattr(
        post_rerank,
        "_document_local_source_contract_rows",
        lambda _q: ([copy.deepcopy(_ANCHOR)], False),
    )
    monkeypatch.setattr(
        document_local_coverage, "build_document_local_query_plan", lambda *_a: None
    )
    source = _resolve_facet_complement_source("q", [], [], {})
    assert source["facet_fetch"] == "skipped_no_plan"
    assert source["plan_rederived"] is True


def test_a9_skipped_no_uncovered_group(monkeypatch):
    from src.rag import document_local_coverage

    monkeypatch.setattr(
        post_rerank,
        "_document_local_source_contract_rows",
        lambda _q: ([copy.deepcopy(_ANCHOR)], False),
    )
    # Plan con solo un grupo de 2 términos -> gate no puede pasar.
    monkeypatch.setattr(
        document_local_coverage,
        "build_document_local_query_plan",
        lambda *_a: _plan([GROUP_2]),
    )
    source = _resolve_facet_complement_source("q", [], [_plain("b", "neutro")], {})
    assert source["facet_fetch"] == "skipped_no_uncovered_group"
    assert source["plan_rederived"] is True


def test_a9_own_fetch(monkeypatch):
    from src.rag import document_local_coverage

    monkeypatch.setattr(
        post_rerank,
        "_document_local_source_contract_rows",
        lambda _q: ([copy.deepcopy(_ANCHOR)], False),
    )
    monkeypatch.setattr(
        document_local_coverage,
        "build_document_local_query_plan",
        lambda *_a: _plan([GROUP_A], sha="own-sha"),
    )
    own_pool = [_dl_candidate("own-cand", _PROSE_SENTENCE)]
    calls = {"n": 0}

    def fake_fetch(_query, _anchors):
        calls["n"] += 1
        return own_pool, [], {"http_requests": 1}

    monkeypatch.setattr(
        document_local_coverage, "fetch_document_local_candidates", fake_fetch
    )
    source = _resolve_facet_complement_source("q", [], [_plain("b", "neutro")], {})
    assert source["facet_fetch"] == "own"
    assert source["plan_rederived"] is True
    assert source["candidate_pool"] == own_pool
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# Presupuesto PROPIO (A8) + convivencia con la reserve.
# ---------------------------------------------------------------------------


def test_budget_serves_even_with_a_full_view(monkeypatch):
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    # Vista de 4 (cap global) + 1 (reserve) llena; ninguna cubre el grupo.
    served = [_plain(f"served-{i}", "fila servida neutra") for i in range(5)]
    plan = _plan([GROUP_A], sha="budget-sha")
    pool = [_dl_candidate("facet", _PROSE_SENTENCE)]

    output, trace = _append_facet_complement(
        served,
        [],
        plan=plan,
        candidate_pool=pool,
        facet_fetch="own",
        plan_rederived=True,
    )

    assert len(output) == len(served) + 1
    assert output[-1]["facet_complement_validated"] is True
    assert trace["status"] == "selected"
    assert trace["selected_ids"] == ["facet"]


def test_budget_consumed_does_not_serve_again(monkeypatch):
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    already = {"id": "prev-facet", "content": "x", "facet_complement_validated": True}
    served = [_plain("base", "neutro"), already]
    plan = _plan([GROUP_A])
    pool = [_dl_candidate("facet", _PROSE_SENTENCE)]

    output, trace = _append_facet_complement(
        served, [], plan=plan, candidate_pool=pool, facet_fetch="own", plan_rederived=True
    )

    assert output == served
    assert trace["status"] == "facet_budget_consumed"


def test_reserve_row_can_raise_grade_and_disable_via(monkeypatch):
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    plan = _plan([GROUP_A], sha="reserve-sha")
    pool = [_dl_candidate("facet", _PROSE_SENTENCE)]

    # Sin la fila reserve -> el grupo está descubierto -> la vía sirve.
    base_view = [_plain("base", "contenido base neutro")]
    served_out, trace_out = _append_facet_complement(
        base_view, [], plan=plan, candidate_pool=pool, facet_fetch="own", plan_rederived=True
    )
    assert trace_out["status"] == "selected"

    # Con una fila reserve que cubre alfa/beta/gamma -> grado>=N_FACET -> gate no
    # pasa -> la vía NO sirve (A8: ve la vista final, reserve incluida).
    with_reserve = base_view + [_plain("reserve", "alfa beta gamma del aviso")]
    served2, trace2 = _append_facet_complement(
        with_reserve, [], plan=plan, candidate_pool=pool, facet_fetch="own", plan_rederived=True
    )
    assert served2 == with_reserve
    assert trace2["status"] == "skipped_no_uncovered_group"


# ---------------------------------------------------------------------------
# Control hp009 — family-generic (no dispara: sin grupo descubierto de >=3).
# ---------------------------------------------------------------------------


def test_hp009_control_does_not_fire(monkeypatch):
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    # Espejo del control hp009: la información pedida ya está en la vista servida
    # (grupo cubierto) -> la vía por-faceta no debe disparar.
    served = [_plain("eol", "sigma omega theta ya en la vista servida")]
    plan = _plan([GROUP_C], sha="hp009-sha")
    pool = [_dl_candidate("cand", "sigma omega theta candidato")]

    output, trace = _append_facet_complement(
        served, [], plan=plan, candidate_pool=pool, facet_fetch="own", plan_rederived=True
    )

    assert output == served
    assert trace["status"] == "skipped_no_uncovered_group"


# ---------------------------------------------------------------------------
# Flag off => byte-inerte (composición idéntica, sin lane por-faceta).
# ---------------------------------------------------------------------------


def _structural_candidate(row_id="anchor"):
    content = "La resistencia máxima del lazo es 35 ohmios."
    start = content.index("resistencia")
    end = len(content) - 1
    return {
        "id": row_id,
        "content": content,
        "source_file": "manual.pdf",
        "retrieval_lane": STRUCTURAL_LANE,
        "structural_neighbor_validated": True,
        "local_semantic_validated": True,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
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


def test_flag_off_is_byte_inert_no_facet_lane(monkeypatch):
    monkeypatch.delenv("DOCUMENT_LOCAL_SELECTION_V2", raising=False)
    reranked = [{"id": "base", "content": "base"}]

    def structural_collector(_query, _reranked):
        return [_structural_candidate()], {
            "lane": STRUCTURAL_LANE,
            "status": "selected",
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta alfa beta gamma",
        reranked,
        enabled=True,
        structural_enabled=True,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
        obligation_reserve_enabled=False,
        structural_collector=structural_collector,
    )

    assert all(lane.get("conduct") != "facet_complement" for lane in trace["lanes"])
    assert all(
        "facet_complement_validated" not in row for row in output
    )
    assert output[0] == reranked[0]


def test_flag_on_adds_a_facet_lane_trace(monkeypatch):
    # Bajo el flag, con lane saltado y sin anchors, la vía deja su lane VISIBLE
    # (skipped_no_anchors) sin tocar la composición.
    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    reranked = [{"id": "base", "content": "base"}]

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta neutra",
        reranked,
        enabled=True,
        structural_enabled=False,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=False,
        cascade_enabled=False,
        compatibility_enabled=False,
        obligation_reserve_enabled=False,
    )

    facet_lanes = [
        lane for lane in trace["lanes"] if lane.get("conduct") == "facet_complement"
    ]
    assert len(facet_lanes) == 1
    assert facet_lanes[0]["facet_fetch"] == "skipped_no_anchors"
    assert output == reranked


def test_served_view_sha_is_order_independent():
    view_a = [_plain("x", "uno"), _plain("y", "dos")]
    view_b = [_plain("y", "dos"), _plain("x", "uno")]
    assert _facet_served_view_sha256(view_a) == _facet_served_view_sha256(view_b)


# ---------------------------------------------------------------------------
# Integración — captura del pool del lane (A2 reused) end-to-end por apply.
# ---------------------------------------------------------------------------


def test_lane_run_reuses_cached_pool_end_to_end(monkeypatch):
    from src.rag import document_local_coverage

    monkeypatch.setenv("DOCUMENT_LOCAL_SELECTION_V2", "on")
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    reranked = [{"id": "base", "content": "base"}]

    def structural_collector(_query, _reranked):
        return [_structural_candidate("anchor")], {
            "lane": STRUCTURAL_LANE,
            "status": "selected",
        }

    reused_candidate = _dl_candidate("reused-cand", _PROSE_SENTENCE)

    def fake_fetch(_query, _anchors, **_kwargs):
        return [copy.deepcopy(reused_candidate)], [], {"http_requests": 1}

    monkeypatch.setattr(
        document_local_coverage, "fetch_document_local_candidates", fake_fetch
    )
    monkeypatch.setattr(
        document_local_coverage,
        "build_document_local_query_plan",
        lambda *_a: _plan([GROUP_A], sha="reused-e2e"),
    )

    # El collector del lane EXPONE el seam ``fetcher`` (como el default real):
    # la vía inyecta un capturing fetcher que puebla el caché SIN duplicar RPC.
    def document_local_collector(query, anchors, covered, *, fetcher):
        fetcher(query, anchors)
        return [], {
            "lane": DOCUMENT_LOCAL_LANE,
            "status": "no_query_aligned_candidate",
            "selected_ids": [],
            "http_requests": 1,
            "model_calls": 0,
            "database_writes": 0,
        }

    output, trace = apply_post_rerank_coverage_with_trace(
        "pregunta alfa beta gamma",
        reranked,
        enabled=True,
        structural_enabled=True,
        table_preamble_enabled=False,
        hyq_enabled=False,
        pool_enabled=False,
        document_local_enabled=True,
        cascade_enabled=False,
        compatibility_enabled=False,
        obligation_reserve_enabled=False,
        structural_collector=structural_collector,
        document_local_collector=document_local_collector,
    )

    facet_lanes = [
        lane for lane in trace["lanes"] if lane.get("conduct") == "facet_complement"
    ]
    assert len(facet_lanes) == 1
    assert facet_lanes[0]["facet_fetch"] == "reused"
    assert facet_lanes[0]["facet_plan_rederived"] is False
    assert facet_lanes[0]["status"] == "selected"
    assert output[-1]["id"] == "reused-cand"
    assert output[-1]["facet_complement_validated"] is True
    assert trace["protected_prefix_equal"] is True
