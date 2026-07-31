"""s289 — fixes quirúrgicos de etapa 2 (dúo r3; evals/s289_etapa2_order_fixes_design_v1.md).

Fix A (`FACET_COMPLEMENT_FALLBACK`): fallback de attestation en la vía
por-faceta — un candidato inservible-por-clase en el puesto 1 del orden total
ya no apaga la vía (clase cat017#4: f2a64128 tóxico vs b7633e98 atestable).

Fix B (`OBLIGATION_RESERVE_ORDERED`): filtros de clase POR-GRUPO en
`_warning_span` (grupo-tabla, marcador-huérfano) + orden determinista
callout-blockquote-first en la reserva (clase hp002#4: changelog rank-2 vs
aviso real p.121 rank-22).

Contratos pineados en AMBOS: flag off = byte-idéntico al comportamiento previo
(firma de `_facet_gate_and_select` preservada; `_warning_span` default sin
filtros; first-match de la reserva intacto); presupuestos q=1 intactos.
"""
from __future__ import annotations

from typing import Any

from src.rag import post_rerank_coverage as post_rerank
from src.rag.post_rerank_coverage import (
    _append_facet_complement,
    _facet_gate_and_select,
    _facet_gate_and_select_all,
)
from src.rag.rerank_pool_coverage import (
    OBLIGATION_WARNING_LANE,
    _group_has_residual_content,
    _is_blockquote_span,
    _is_table_group,
    _warning_span,
    select_obligation_warning_reserve,
)

# ---------------------------------------------------------------------------
# Fixtures Fix A (estilo test_s279_facet_complement).
# ---------------------------------------------------------------------------

ACTIVE_SHA = "a" * 64
ACTIVE_DOCUMENT = "active-document"
LINEAGE_ID = "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
GROUP_A = ["alfa", "beta", "gamma", "delta"]


def _plain(row_id: str, content: str) -> dict[str, Any]:
    return {"id": row_id, "content": content, "source_file": "manual",
            "chunk_index": 5}


def _plan(need_groups: list[list[str]], sha: str = "plansha") -> dict[str, Any]:
    return {"need_groups": [list(g) for g in need_groups], "sha256": sha}


def _dl_candidate(row_id: str, content: str, *, chunk_index: int = 7) -> dict[str, Any]:
    return {
        "id": row_id,
        "content": content,
        "chunk_index": chunk_index,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
        "source_file": "manual",
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
        "document_local_authority_source_file": "manual",
        "document_local_authority_revision_lineage_id": LINEAGE_ID,
        "document_local_authority_document_family": "manual panel",
        "document_local_authority_language": "es",
        "document_local_authority_doc_type": "usuario",
        "document_local_authority_manufacturer": "Fabricante",
        "document_local_authority_product_model": "Panel-X",
    }


# Tóxico-por-clase (calca test_pipe_class_content_fails_closed_without_prose):
# la ventana toca encabezado+datos => pipe NO derivable; la prosa tampoco (no
# es oración de prosa).  Ventana DENSA => gana el puesto 1 del bucket, como
# f2a64128 en cat017 (density 45 < 148).
_TOXIC_TABLE = (
    "| Campo | Detalle |\n"
    "| --- | --- |\n"
    "| Estado | alfa beta gamma en fila. |\n"
)
# Atestable por la clase de prosa; términos más dispersos => density mayor =>
# puesto 2 del MISMO bucket, como b7633e98.
_ATTESTABLE_PROSE = (
    "Estas maniobras actuan sobre alfa con beta y despues gamma del sistema."
)


def _facet_fixture():
    served = [_plain("base", "contenido base neutro")]
    plan = _plan([GROUP_A], sha="plansha-s289")
    pool = [
        _dl_candidate("toxic-first", _TOXIC_TABLE, chunk_index=3),
        _dl_candidate("attestable-second", _ATTESTABLE_PROSE, chunk_index=9),
    ]
    return served, plan, pool


def _append_facet(served, plan, pool):
    return _append_facet_complement(
        served, [], plan=plan, candidate_pool=pool,
        facet_fetch="reused", plan_rederived=False,
    )


# ---------------------------------------------------------------------------
# Fix A — firma preservada y orden total.
# ---------------------------------------------------------------------------


def test_gate_and_select_first_of_all_matches_single(monkeypatch):
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    served, plan, pool = _facet_fixture()
    selections, status_all, grades_all, groups_all = _facet_gate_and_select_all(
        served, [], plan, pool
    )
    selection, status, grades, groups = _facet_gate_and_select(served, [], plan, pool)
    assert status == status_all == "ok"
    assert grades == grades_all and groups == groups_all
    assert selection == selections[0]
    # Orden del bucket: el denso (tabla) primero, el atestable segundo.
    assert [s["candidate"]["id"] for s in selections] == [
        "toxic-first", "attestable-second",
    ]


def test_gate_and_select_all_empty_statuses():
    served = [_plain("base", "alfa beta gamma delta ya cubiertos aqui mismo.")]
    plan = _plan([GROUP_A])
    selections, status, _g, _gr = _facet_gate_and_select_all(served, [], plan, [])
    assert selections == [] and status == "skipped_no_uncovered_group"
    served = [_plain("base", "contenido base neutro")]
    selections, status, _g, _gr = _facet_gate_and_select_all(served, [], plan, [])
    assert selections == [] and status == "no_eligible_candidate"


def test_flag_off_first_toxic_kills_the_lane(monkeypatch):
    """Byte-igual al comportamiento previo: un solo intento, vía muerta."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    monkeypatch.delenv("FACET_COMPLEMENT_FALLBACK", raising=False)
    served, plan, pool = _facet_fixture()
    out, trace = _append_facet(served, plan, pool)
    assert out == served
    assert trace["status"] == "facet_attestation_failed"
    assert "facet_attempts" not in trace


def test_flag_on_falls_back_to_the_attestable_candidate(monkeypatch):
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    monkeypatch.setenv("FACET_COMPLEMENT_FALLBACK", "on")
    served, plan, pool = _facet_fixture()
    out, trace = _append_facet(served, plan, pool)
    assert trace["status"] == "selected"
    assert trace["selected_ids"] == ["attestable-second"]
    assert len(out) == len(served) + 1  # presupuesto q=1 intacto
    assert out[-1]["facet_complement_validated"] is True
    assert trace["facet_attempts"] == [
        {"id": "toxic-first", "group_index": 0, "outcome": "attestation_failed"},
        {"id": "attestable-second", "group_index": 0, "outcome": "attested"},
    ]


def test_flag_on_all_failing_reports_attempts(monkeypatch):
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    monkeypatch.setenv("FACET_COMPLEMENT_FALLBACK", "on")
    served = [_plain("base", "contenido base neutro")]
    plan = _plan([GROUP_A])
    pool = [_dl_candidate("toxic-only", _TOXIC_TABLE)]
    out, trace = _append_facet(served, plan, pool)
    assert out == served
    assert trace["status"] == "facet_attestation_failed"
    assert [a["outcome"] for a in trace["facet_attempts"]] == ["attestation_failed"]


def test_flag_on_budget_already_consumed_short_circuits(monkeypatch):
    monkeypatch.setenv("FACET_COMPLEMENT_FALLBACK", "on")
    served = [dict(_plain("prev", "x"), facet_complement_validated=True)]
    plan = _plan([GROUP_A])
    out, trace = _append_facet(served, plan, [_dl_candidate("c", _ATTESTABLE_PROSE)])
    assert out == served
    assert trace["status"] == "facet_budget_consumed"


# ---------------------------------------------------------------------------
# Fixtures Fix B.
# ---------------------------------------------------------------------------

_PROCEDURAL_QUERY = (
    "El aspirador ASD535 da una alarma de flujo bajo intermitente; "
    "¿cuál es la causa más probable y cómo se diagnostica?"
)
_SERVED_SOURCE = "asd535-manual.pdf"

_CHANGELOG_TABLE = (
    "| Capitulo | x | Detalle | Motivo |\n"
    "| --- | --- | --- | --- |\n"
    "| 9.4.3 | c | Advertencia insertada antes del texto y adaptacion. | Rectificacion |\n"
)
_ORPHAN_MARKER = (
    "> **Peligro**\n>\n"
    "El equipo funciona con normalidad si el personal lo maneja bien.\n"
)
_REAL_CALLOUT = (
    "> ADVERTENCIA: antes de iniciar los trabajos de mantenimiento deben\n"
    "> bloquearse los controles de incendio y las alertas remotas.\n"
)
_INCIDENTAL_PROSE = (
    "La descripcion contiene la informacion imprescindible para garantizar "
    "el correcto funcionamiento del equipo."
)


def _served_base(row_id="base"):
    return {"id": row_id, "content": "Puesta en marcha del equipo.",
            "source_file": _SERVED_SOURCE, "similarity": 0.9}


def _pool_row(row_id, content):
    return {"id": row_id, "content": content, "source_file": _SERVED_SOURCE,
            "section_title": "Seccion", "page_number": 10}


def _reserve(pool, query=_PROCEDURAL_QUERY):
    return select_obligation_warning_reserve(query, pool, [_served_base()])


# ---------------------------------------------------------------------------
# Fix B — filtros de clase por-grupo.
# ---------------------------------------------------------------------------


def test_default_warning_span_still_returns_the_table_group():
    """`filtered` default False = byte-idéntico: la fila de tabla GANA."""
    span = _warning_span(_CHANGELOG_TABLE)
    assert span is not None
    start, end, _t = span
    assert _is_table_group(_CHANGELOG_TABLE[start:end]) is True


def test_filtered_span_skips_table_and_orphan_groups():
    assert _warning_span(_CHANGELOG_TABLE, filtered=True) is None
    assert _warning_span(_ORPHAN_MARKER, filtered=True) is None
    span = _warning_span(_REAL_CALLOUT, filtered=True)
    assert span is not None


def test_filtered_span_advances_to_a_later_clean_group_same_chunk():
    """A3 (dúo r3): el primer-grupo-FP no entierra el callout real del chunk."""
    content = (
        _ORPHAN_MARKER
        + "\nTexto neutral que separa los bloques del capitulo.\n\n"
        + "ADVERTENCIA: deben bloquearse los controles de incendio antes de "
        + "iniciar el mantenimiento."
    )
    assert _warning_span(content) is not None
    start_u, _e, _t = _warning_span(content)
    span_f = _warning_span(content, filtered=True)
    assert span_f is not None
    start_f, end_f, triggers = span_f
    assert start_f > start_u  # saltó el marcador huérfano
    assert "bloquearse los controles" in content[start_f:end_f]


def test_group_class_helpers():
    assert _is_table_group("> | a | Advertencia b |\n> | c | d |") is True
    assert _is_table_group(_REAL_CALLOUT) is False
    assert _group_has_residual_content("> **Peligro**") is False
    assert _group_has_residual_content("**De vital importancia**") is False
    assert _group_has_residual_content(_REAL_CALLOUT) is True
    # Compuesto: retirar componentes deja el resto de la cláusula.
    assert _group_has_residual_content(
        "Debe purgarse el conducto antes de arrancar."
    ) is True
    assert _is_blockquote_span(_REAL_CALLOUT) is True
    assert _is_blockquote_span(_INCIDENTAL_PROSE) is False


# ---------------------------------------------------------------------------
# Fix B — selector: off byte-idéntico; on = orden determinista.
# ---------------------------------------------------------------------------


def test_flag_off_first_match_serves_the_changelog(monkeypatch):
    monkeypatch.delenv("OBLIGATION_RESERVE_ORDERED", raising=False)
    rows, trace = _reserve([
        _pool_row("changelog", _CHANGELOG_TABLE),
        _pool_row("real-warning", _REAL_CALLOUT),
    ])
    assert trace["status"] == "selected"
    assert [r["id"] for r in rows] == ["changelog"]
    assert "reserve_ranked_ids" not in trace and "reserve_discards" not in trace


def test_flag_on_blockquote_beats_earlier_prose(monkeypatch):
    monkeypatch.setenv("OBLIGATION_RESERVE_ORDERED", "on")
    rows, trace = _reserve([
        _pool_row("incidental", _INCIDENTAL_PROSE),
        _pool_row("real-warning", _REAL_CALLOUT),
    ])
    assert trace["status"] == "selected"
    assert [r["id"] for r in rows] == ["real-warning"]
    assert rows[0]["retrieval_lane"] == OBLIGATION_WARNING_LANE
    assert rows[0]["obligation_warning_pool_rank"] == 1
    assert trace["reserve_ranked_ids"] == ["real-warning", "incidental"]


def test_flag_on_filters_discard_the_changelog_with_trace(monkeypatch):
    monkeypatch.setenv("OBLIGATION_RESERVE_ORDERED", "on")
    rows, trace = _reserve([
        _pool_row("changelog", _CHANGELOG_TABLE),
        _pool_row("real-warning", _REAL_CALLOUT),
    ])
    assert [r["id"] for r in rows] == ["real-warning"]
    assert trace["reserve_discards"] == [
        {"pool_rank": 0, "id": "changelog", "filter": "all_groups_filtered"}
    ]


def test_flag_on_without_blockquote_degrades_to_pool_rank(monkeypatch):
    monkeypatch.setenv("OBLIGATION_RESERVE_ORDERED", "on")
    rows, _trace = _reserve([
        _pool_row("prose-a", _INCIDENTAL_PROSE),
        _pool_row("prose-b", "Es obligatorio revisar el filtro cada mes."),
    ])
    assert [r["id"] for r in rows] == ["prose-a"]


def test_flag_on_budget_still_one_row(monkeypatch):
    monkeypatch.setenv("OBLIGATION_RESERVE_ORDERED", "on")
    rows, _trace = _reserve([
        _pool_row("w1", _REAL_CALLOUT),
        _pool_row("w2", "> ATENCION: nunca desconecte el lazo con tension.\n"),
    ])
    assert len(rows) == 1


def test_flag_on_all_filtered_is_a_clean_no_op(monkeypatch):
    monkeypatch.setenv("OBLIGATION_RESERVE_ORDERED", "on")
    rows, trace = _reserve([_pool_row("changelog", _CHANGELOG_TABLE)])
    assert rows == []
    assert trace["status"] == "no_warning_in_served_scope"
    assert trace["reserve_discards"][0]["id"] == "changelog"
