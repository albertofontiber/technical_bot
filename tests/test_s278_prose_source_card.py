"""s278 §4 — prose source card (flag ``PROSE_SOURCE_CARD``, default off).

Contratos verificados (diseño ``evals/s278_vnext_design_v2.md`` §4 + handoff
``docs/HANDOFF_P1_B92FF51_2026-07-22.md`` §8.4):

  - flag off => byte-inerte (ni claves nuevas en filas ni en traces);
  - card de prosa servida con attestation COMPLETA sobre un fixture espejo de
    cat019 (span sintético [2699, 3008), oración completa verbatim), incluida
    la identidad de blob canónica documento ``<stem>.pdf`` vs chunk ``<stem>``;
  - tampering de CADA campo de la attestation => no-servir (receipt False);
  - bounds fuera del contenido => no-servir;
  - doc rechazado por el RPC snapshot v2 => receipt con el motivo exacto
    (``blocked_<reason>``) y NINGUNA card — fail-closed visible, no silencioso;
  - la clase ``markdown_pipe_row_v1`` queda byte-exacta con la prosa off Y on
    (clases independientes);
  - cero identificadores de eval en el módulo de runtime (grep).
"""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from typing import Any

import pytest

from src.rag import document_local_coverage as document_local
from src.rag.document_local_coverage import (
    LANE,
    MAX_PROSE_SOURCE_CARD_CHARS,
    PROSE_SOURCE_CARD_CLASS,
    PROSE_SOURCE_CARD_KIND,
    VALIDATION,
    build_prose_source_cards,
    collect_document_local_coverage,
    has_exact_prose_source_card_receipt,
    select_document_local_coverage,
)
from src.rag.post_rerank_coverage import (
    append_validated_coverage,
    coverage_context_content,
)


ACTIVE_SHA = "b" * 64
ACTIVE_DOCUMENT = "doc-active"
LINEAGE_ID = "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429"
# Espejo del mismatch CONFIRMADO de cat019 (handoff §8.4): documents lleva
# '<stem>.pdf' mientras chunks/doc_map llevan '<stem>' — nombres SINTÉTICOS.
CHUNK_BLOB = "manual-configuracion-panel-es-2026-c"
DOCUMENT_BLOB = CHUNK_BLOB + ".pdf"
PROSE_START = 2699
PROSE_END = 3008
QUESTION = (
    "Sobre que elementos actuan las maniobras configuradas al activarse "
    "la alarma del panel?"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prose_content() -> str:
    """Content whose only governed sentence occupies exactly [2699, 3008)."""
    lead = "x" * (PROSE_START - 2) + ".\n"
    head = "Estas maniobras actuaran "
    tail = " sirenas o modulos de control."
    filler = "y" * (PROSE_END - PROSE_START - len(head) - len(tail))
    sentence = head + filler + tail
    assert len(lead) == PROSE_START
    assert len(sentence) == PROSE_END - PROSE_START
    content = lead + sentence + " Cola posterior fuera del span."
    assert content[PROSE_START:PROSE_END] == sentence
    return content


def _prose_candidate(row_id: str = "prose-target") -> dict[str, Any]:
    content = _prose_content()
    card_start = content.index("sirenas o modulos")
    card_end = card_start + len("sirenas o modulos de control")
    return {
        "id": row_id,
        "document_id": ACTIVE_DOCUMENT,
        "extraction_sha256": ACTIVE_SHA,
        "chunk_index": 12,
        "content": content,
        "context": "",
        "section_title": "Maniobras",
        "document_family": "manual configuracion panel",
        "product_model": "Panel-Z",
        "language": "es",
        "source_file": CHUNK_BLOB,
        "page_number": 10,
        "duplicate_of": None,
        "manufacturer": "Fabricante Panel",
        "doc_type": "configuracion",
        "document_status": "active",
        "document_revision": "v.01",
        "document_revision_lineage_id": LINEAGE_ID,
        "document_local_candidate_rank": 0,
        "document_local_authority_document_id": ACTIVE_DOCUMENT,
        "document_local_authority_extraction_sha256": ACTIVE_SHA,
        "document_local_authority_source_file": DOCUMENT_BLOB,
        "document_local_authority_revision_lineage_id": LINEAGE_ID,
        "document_local_authority_document_family": "manual configuracion panel",
        "document_local_authority_language": "es",
        "document_local_authority_doc_type": "configuracion",
        "document_local_authority_manufacturer": "Fabricante Panel",
        "document_local_authority_product_model": "Panel-Z",
        "coverage_cards": [
            {
                "candidate_id": row_id,
                "candidate_rank": 1,
                "start": card_start,
                "end": card_end,
                "quote": content[card_start:card_end],
                "facet": "actuacion",
                "exact_source_span_validated": True,
            }
        ],
        "coverage_card_facets": ["actuacion"],
        "local_semantic_validated": True,
    }


def _authority() -> dict[str, str]:
    return {
        "document_id": ACTIVE_DOCUMENT,
        "revision_lineage_id": LINEAGE_ID,
        "extraction_sha256": ACTIVE_SHA,
        "source_file": DOCUMENT_BLOB,
        "language": "es",
        "revision": "v.01",
    }


def _stub_ranker(
    monkeypatch: pytest.MonkeyPatch, winner: dict[str, Any]
) -> None:
    monkeypatch.setattr(
        document_local,
        "select_rerank_pool_coverage",
        lambda _query, _candidates, _context, **_kwargs: (
            [copy.deepcopy(winner)],
            {"eligible_rows": 1, "catalog_scope_applied": False},
        ),
    )


def _served_row(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    candidate = _prose_candidate()
    _stub_ranker(monkeypatch, candidate)
    selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )
    assert trace["status"] == "selected"
    assert len(selected) == 1
    return selected[0]


# ---------------------------------------------------------------------------
# Flag off => byte-inerte.
# ---------------------------------------------------------------------------


def test_flag_off_select_is_byte_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROSE_SOURCE_CARD", raising=False)
    candidate = _prose_candidate()
    _stub_ranker(monkeypatch, candidate)

    selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )

    assert [row["id"] for row in selected] == ["prose-target"]
    assert selected[0]["document_local_coverage_validation"] == VALIDATION
    assert selected[0]["retrieval_lane"] == LANE
    dumped = json.dumps((selected, trace), sort_keys=True, default=str)
    assert "prose_source_card" not in dumped


def test_flag_off_collect_blocked_trace_is_byte_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROSE_SOURCE_CARD", raising=False)
    blocked = {
        "status": "unverified_document_lineage",
        "authority_rejections": ["unverified_document_lineage"],
        "http_requests": 1,
    }

    rows, trace = collect_document_local_coverage(
        QUESTION,
        [],
        [],
        fetcher=lambda *_args, **_kwargs: ([], [], copy.deepcopy(blocked)),
    )

    assert rows == []
    assert trace == blocked


# ---------------------------------------------------------------------------
# Card servida con attestation completa (espejo sintético de cat019).
# ---------------------------------------------------------------------------


def test_prose_card_served_with_complete_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served = _served_row(monkeypatch)
    content = served["content"]
    quote = content[PROSE_START:PROSE_END]

    assert served["prose_source_cards"] == [
        {
            "candidate_id": "prose-target",
            "card_class": PROSE_SOURCE_CARD_CLASS,
            "record_kind": PROSE_SOURCE_CARD_KIND,
            "document_id": ACTIVE_DOCUMENT,
            "extraction_sha256": ACTIVE_SHA,
            "source_file": CHUNK_BLOB,
            "content_sha256": _sha(content),
            "start": PROSE_START,
            "end": PROSE_END,
            "quote": quote,
            "quote_sha256": _sha(quote),
            "sentence_complete_validated": True,
            "local_semantic_validated": True,
            "exact_source_span_validated": True,
        }
    ]
    # Oración COMPLETA verbatim: el card del selector era un fragmento y el
    # span servido se expande a los límites exactos de la oración.
    assert quote.startswith("Estas maniobras actuaran")
    assert quote.endswith("sirenas o modulos de control.")
    assert has_exact_prose_source_card_receipt(served) is True


def test_select_trace_declares_prose_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    candidate = _prose_candidate()
    _stub_ranker(monkeypatch, candidate)

    _selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )

    assert trace["prose_source_card"]["status"] == "selected"
    assert trace["prose_source_card"]["cards"] == 1
    assert trace["prose_source_card"]["record_kind"] == PROSE_SOURCE_CARD_KIND
    assert trace["prose_source_card"]["spans"] == [[PROSE_START, PROSE_END]]


def test_collect_serves_prose_card_through_canonical_blob_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contrato PYTHON del flujo collect→select con fetcher STUB (s278 dúo r2,
    Sol#1): el RPC v2 real rechazaría hoy este par de blobs en SQL — el path
    SQL canónico es la propuesta v3 en supabase/migration_proposals/."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    candidate = _prose_candidate()
    _stub_ranker(monkeypatch, candidate)
    fetched = {"status": "fetched", "http_requests": 1}

    rows, trace = collect_document_local_coverage(
        QUESTION,
        [],
        [],
        fetcher=lambda *_args, **_kwargs: (
            [copy.deepcopy(candidate)],
            [_authority()],
            copy.deepcopy(fetched),
        ),
    )

    # La autoridad lleva '<stem>.pdf' (documents) y el chunk '<stem>'
    # (chunks/doc_map): solo la comparación canónica única los empareja.
    assert [row["id"] for row in rows] == ["prose-target"]
    assert has_exact_prose_source_card_receipt(rows[0]) is True
    assert trace["prose_source_card"]["status"] == "selected"


# ---------------------------------------------------------------------------
# Tampering de cada campo de la attestation => no-servir.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_id", "otro-chunk"),
        ("card_class", "mandatory_callout"),
        ("record_kind", "markdown_pipe_row_v1"),
        ("document_id", "otro-doc"),
        ("extraction_sha256", "c" * 64),
        ("source_file", "otro-manual"),
        ("content_sha256", "0" * 64),
        ("start", PROSE_START + 1),
        ("end", PROSE_END - 1),
        ("quote", "texto inventado."),
        ("quote_sha256", "0" * 64),
        ("sentence_complete_validated", False),
        ("local_semantic_validated", False),
        ("exact_source_span_validated", False),
    ],
)
def test_tampered_attestation_field_is_never_served(
    monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    served = _served_row(monkeypatch)
    assert has_exact_prose_source_card_receipt(served) is True

    served["prose_source_cards"][0][field] = value

    assert has_exact_prose_source_card_receipt(served) is False


def test_tampered_parent_content_is_never_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served = _served_row(monkeypatch)

    served["content"] = served["content"][:-1] + "z"

    assert has_exact_prose_source_card_receipt(served) is False


def test_tampered_selector_card_is_never_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served = _served_row(monkeypatch)

    served["coverage_cards"][0]["end"] += 1

    assert has_exact_prose_source_card_receipt(served) is False


def test_tampered_chunk_identity_is_never_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served = _served_row(monkeypatch)

    served["document_local_authority_source_file"] = "otro-doc.pdf"

    assert has_exact_prose_source_card_receipt(served) is False


# ---------------------------------------------------------------------------
# Bounds fuera del contenido => no-servir.
# ---------------------------------------------------------------------------


def test_bounds_outside_content_are_never_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served = _served_row(monkeypatch)

    served["prose_source_cards"][0]["end"] = len(served["content"]) + 5

    assert has_exact_prose_source_card_receipt(served) is False


def test_builder_fails_closed_on_out_of_content_selector_bounds() -> None:
    candidate = _prose_candidate()
    candidate["coverage_cards"][0]["end"] = len(candidate["content"]) + 1

    assert build_prose_source_cards(candidate) == []


def test_oversized_sentence_is_omitted_never_clipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    candidate = _prose_candidate()
    content = "z" * (MAX_PROSE_SOURCE_CARD_CHARS + 100) + " control final."
    candidate["content"] = content
    candidate["coverage_cards"] = [
        {
            "candidate_id": candidate["id"],
            "candidate_rank": 1,
            "start": 0,
            "end": 10,
            "quote": content[0:10],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        }
    ]
    _stub_ranker(monkeypatch, candidate)

    selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )

    assert len(selected) == 1
    assert "prose_source_cards" not in selected[0]
    assert trace["prose_source_card"] == {
        "status": "no_complete_sentence_span",
        "cards": 0,
    }


# ---------------------------------------------------------------------------
# Doc rechazado por el RPC snapshot v2 => bloqueo VISIBLE con el motivo exacto.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reason",
    [
        "unverified_document_lineage",
        "ambiguous_document_identity",
        "active_revision_not_bound_to_anchor_blob",
    ],
)
def test_snapshot_rejected_document_blocks_visibly_with_exact_reason(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    blocked = {
        "status": reason,
        "authority_rejections": [reason],
        "http_requests": 1,
    }

    rows, trace = collect_document_local_coverage(
        QUESTION,
        [],
        [],
        fetcher=lambda *_args, **_kwargs: ([], [], copy.deepcopy(blocked)),
    )

    assert rows == []
    assert trace["prose_source_card"] == {
        "status": f"blocked_{reason}",
        "snapshot_rejections": [reason],
        "cards": 0,
    }
    # El resto del trace de lectura queda intacto (motivo NO silenciado).
    assert trace["status"] == reason
    assert trace["authority_rejections"] == [reason]


def test_non_snapshot_empty_fetch_declares_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """not_applicable queda SOLO para el path sin autoridad ni rechazo (aquí:
    sin plan de query, cero identificadores).  s278 dúo r2 (Fable#3): con
    autoridad presente y par de blob canónico-no-estricto el receipt declara
    blocked_blob_identity_drift_requires_rpc_v3 — ver el test de drift."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    empty = {"status": "no_bounded_query_plan", "http_requests": 0}

    rows, trace = collect_document_local_coverage(
        QUESTION,
        [],
        [],
        fetcher=lambda *_args, **_kwargs: ([], [], copy.deepcopy(empty)),
    )

    assert rows == []
    assert trace["prose_source_card"] == {
        "status": "not_applicable",
        "cards": 0,
    }


# ---------------------------------------------------------------------------
# Clases independientes: markdown_pipe_row_v1 byte-exacto con la prosa off Y on.
# ---------------------------------------------------------------------------


def _pipe_row_candidate() -> dict[str, Any]:
    content = (
        "| Parametro | Significado |\n"
        "| --- | --- |\n"
        "| r.I | Rearme inhibido: 00 libre; 01 a 30 minutos. |\n"
        "\nCola no relacionada."
    )
    start = content.index("| r.I")
    end = content.index("00 libre") + len("00 libre")
    row = _prose_candidate("pipe-target")
    row.update(
        {
            "content": content,
            # Clase de fila: nombres de blob IDÉNTICOS (caso servible hoy).
            "source_file": "manual-pipe",
            "document_local_authority_source_file": "manual-pipe",
            "coverage_cards": [
                {
                    "candidate_id": "pipe-target",
                    "candidate_rank": 1,
                    "start": start,
                    "end": end,
                    "quote": content[start:end],
                    "facet": "actuacion",
                    "exact_source_span_validated": True,
                }
            ],
            "retrieval_lane": LANE,
            "document_local_coverage_validated": True,
            "document_local_coverage_validation": VALIDATION,
            "document_local_coverage_rank": 1,
        }
    )
    return row


def test_markdown_pipe_row_class_byte_identical_with_prose_off_and_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    views: dict[str, tuple[str, str]] = {}
    for mode in ("off", "on"):
        monkeypatch.setenv("PROSE_SOURCE_CARD", mode)
        served_rows = append_validated_coverage(
            [], [copy.deepcopy(_pipe_row_candidate())]
        )
        assert len(served_rows) == 1
        served = served_rows[0]
        assert "prose_source_cards" not in served
        views[mode] = (
            json.dumps(served["served_coverage_cards"], sort_keys=True),
            coverage_context_content(served),
        )

    assert views["off"] == views["on"]
    assert '"record_kind": "markdown_pipe_row_v1"' in views["on"][0]
    assert views["on"][1] == "| r.I | Rearme inhibido: 00 libre; 01 a 30 minutos. |"


# ---------------------------------------------------------------------------
# Nunca lookup por identificadores de eval en el módulo de runtime.
# ---------------------------------------------------------------------------


def test_runtime_module_never_uses_eval_identifiers() -> None:
    source = inspect.getsource(document_local).casefold()
    for forbidden in (
        "qid",
        "cat017",
        "cat019",
        "hp0",
        "f68f2d40",
        "b7633e98",
        "348c4ec1",
        "80e1b7d2",
        "hop-138",
        "cad-250",
    ):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# s278 duo r2 — fixes adjudicados (Sol 3 + Fable 5).
# ---------------------------------------------------------------------------


def test_pipe_table_that_fails_pipe_class_is_never_served_as_prose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fable#2 (CRITICO, probe reproducido): un span sobre DOS data-rows hace
    fallar la clase pipe; la clase de prosa NO puede rescatarlo sirviendo la
    fila truncada — verificación POSITIVA de prosa-idad."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    candidate = _prose_candidate("pipe-as-prose")
    content = (
        "| Parametro | Significado |\n"
        "| --- | --- |\n"
        "| r.I | Rearme inhibido hasta finalizar la extincion. |\n"
        "| t.A | Temporizador de aviso en minutos. |\n"
    )
    start = content.index("| r.I")
    end = content.index("Temporizador") + len("Temporizador")
    candidate["content"] = content
    candidate["coverage_cards"] = [
        {
            "candidate_id": "pipe-as-prose",
            "candidate_rank": 1,
            "start": start,
            "end": end,
            "quote": content[start:end],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        }
    ]

    assert build_prose_source_cards(candidate) == []

    _stub_ranker(monkeypatch, candidate)
    selected, trace = select_document_local_coverage(
        QUESTION, [candidate], [], [_authority()]
    )

    assert len(selected) == 1
    assert "prose_source_cards" not in selected[0]
    assert trace["prose_source_card"] == {
        "status": "no_complete_sentence_span",
        "cards": 0,
    }


def test_hard_wrapped_sentence_fragments_are_never_served() -> None:
    """Sol#2: sentence_complete_validated se VALIDA de verdad — fragmentos de
    una oración partida por hard-wrap (línea sin puntuación terminal y su
    continuación) no se sirven; fail-closed, sin rebajar el campo."""
    candidate = _prose_candidate("hard-wrap")
    content = (
        "Este parrafo tecnico viene cortado por un hard\n"
        "wrap y la continuacion de la oracion termina aqui."
    )
    fragment_1 = content.index("cortado")
    fragment_2 = content.index("continuacion")
    candidate["content"] = content
    candidate["coverage_cards"] = [
        {
            "candidate_id": "hard-wrap",
            "candidate_rank": 1,
            "start": fragment_1,
            "end": fragment_1 + len("cortado"),
            "quote": content[fragment_1 : fragment_1 + len("cortado")],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        },
        {
            "candidate_id": "hard-wrap",
            "candidate_rank": 2,
            "start": fragment_2,
            "end": fragment_2 + len("continuacion"),
            "quote": content[fragment_2 : fragment_2 + len("continuacion")],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        },
    ]

    assert build_prose_source_cards(candidate) == []


def test_semicolon_terminal_span_is_never_served() -> None:
    """Sol#2: ';' separa cláusulas, no oraciones — un segmento terminado en
    ';' no valida como oración completa."""
    candidate = _prose_candidate("semicolon")
    content = "Primera clausula del parrafo tecnico; segunda clausula sin punto"
    start = content.index("Primera")
    candidate["content"] = content
    candidate["coverage_cards"] = [
        {
            "candidate_id": "semicolon",
            "candidate_rank": 1,
            "start": start,
            "end": start + len("Primera clausula"),
            "quote": content[start : start + len("Primera clausula")],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        }
    ]

    assert build_prose_source_cards(candidate) == []


def test_decisive_alignment_card_group_wins_over_positional() -> None:
    """Sol#3: con varias cards, el grupo de oraciones que contiene la card
    DECISIVA de alineación (facet query_alignment) manda sobre el primer
    grupo posicional; empate/resto por posición."""
    candidate = _prose_candidate("decisive")
    content = (
        "La primera oracion queda al principio del parrafo. "
        "La oracion decisiva con la respuesta alineada esta despues."
    )
    second_start = content.index("La oracion decisiva")
    candidate["content"] = content
    candidate["coverage_cards"] = [
        {
            "candidate_id": "decisive",
            "candidate_rank": 1,
            "start": content.index("primera oracion"),
            "end": content.index("principio"),
            "quote": content[
                content.index("primera oracion") : content.index("principio")
            ],
            "facet": "actuacion",
            "exact_source_span_validated": True,
        },
        {
            "candidate_id": "decisive",
            "candidate_rank": 2,
            "start": content.index("respuesta alineada"),
            "end": content.index("respuesta alineada") + len("respuesta"),
            "quote": content[
                content.index("respuesta alineada") : content.index(
                    "respuesta alineada"
                )
                + len("respuesta")
            ],
            "facet": "query_alignment",
            "exact_source_span_validated": True,
        },
    ]

    cards = build_prose_source_cards(candidate)

    assert len(cards) == 1
    assert cards[0]["start"] == second_start
    assert cards[0]["quote"] == (
        "La oracion decisiva con la respuesta alineada esta despues."
    )


def test_authority_with_zero_candidates_declares_blob_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fable#3: autoridad presente + candidatos vacíos + par de blob que
    empareja canónico pero NO estricto => el receipt declara el drift visible
    (antes quedaba misatribuido a not_applicable/no_fts_candidates)."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    fetched = {"status": "no_fts_candidates", "http_requests": 1}
    anchor = {"document_id": ACTIVE_DOCUMENT, "source_file": CHUNK_BLOB}

    rows, trace = collect_document_local_coverage(
        QUESTION,
        [anchor],
        [],
        fetcher=lambda *_args, **_kwargs: (
            [],
            [_authority()],
            copy.deepcopy(fetched),
        ),
    )

    assert rows == []
    assert trace["prose_source_card"] == {
        "status": "blocked_blob_identity_drift_requires_rpc_v3",
        "blob_identity_drift": [
            {
                "document_id": ACTIVE_DOCUMENT,
                "documents_blob": DOCUMENT_BLOB,
                "chunks_blob": CHUNK_BLOB,
            }
        ],
        "cards": 0,
    }


# ---------------------------------------------------------------------------
# Fable#4 — la card SOLO en el path complementario, probado con el SELECTOR
# real (select_rerank_pool_coverage sin monkeypatch).
# ---------------------------------------------------------------------------


def _real_selector_row(row_id: str, content: str) -> dict[str, Any]:
    """Fila SIN coverage_cards: las produce el selector real."""
    row = _prose_candidate(row_id)
    row.pop("coverage_cards")
    row.pop("coverage_card_facets")
    row.pop("local_semantic_validated")
    row["content"] = content
    return row


def test_real_selector_attaches_prose_card_only_in_complementary_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    query = (
        "Las maniobras actuaran sobre salidas programadas, "
        "sirenas o modulos de control?"
    )
    content = (
        "Introduccion breve del capitulo.\n"
        "Estas maniobras actuaran sobre las salidas programadas del circuito, "
        "sirenas o modulos de control. Cola posterior fuera del span."
    )

    selected, trace = select_document_local_coverage(
        query, [_real_selector_row("prose-real", content)], [], [_authority()]
    )

    assert [row["id"] for row in selected] == ["prose-real"]
    assert trace["prose_source_card"]["status"] == "selected"
    cards = selected[0]["prose_source_cards"]
    assert len(cards) == 1
    # La ventana real de alineación cubre las tres oraciones cortas: el span
    # servido son oraciones COMPLETAS verbatim que incluyen la decisiva.
    assert "sirenas o modulos de control." in cards[0]["quote"]
    assert cards[0]["quote"].endswith(".")
    assert has_exact_prose_source_card_receipt(selected[0]) is True


def test_real_selector_does_not_attach_prose_to_pipe_derivable_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fable#4: ganador cuya clase de fila markdown ES derivable (card real de
    alineación intersecando solo separador+data-row) => sin card de prosa y
    estado explícito.  Layout calibrado para que la ventana de alineación del
    selector real (stride 180) caiga tras el encabezado."""
    monkeypatch.setenv("PROSE_SOURCE_CARD", "on")
    query = (
        "La carcasa exterior beige incorpora la junta estanca del "
        "prensaestopas trasero?"
    )
    data_row = (
        "| Carcasa | La carcasa exterior beige incorpora la junta estanca "
        "del prensaestopas trasero. |"
    )
    content = (
        "z" * 310 + ".\n"
        "| Campo | Detalle |\n"
        "| --- | --- |\n"
        + data_row + "\n"
        + "\n" * 120
    )

    selected, trace = select_document_local_coverage(
        query, [_real_selector_row("pipe-real", content)], [], [_authority()]
    )

    assert [row["id"] for row in selected] == ["pipe-real"]
    assert "prose_source_cards" not in selected[0]
    assert trace["prose_source_card"] == {
        "status": "not_applicable_markdown_pipe_row_class",
        "cards": 0,
    }
    facets = [
        str(card.get("facet") or "")
        for card in selected[0]["coverage_cards"]
    ]
    assert facets == ["query_alignment"]
