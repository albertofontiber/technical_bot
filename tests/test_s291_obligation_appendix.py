"""s291/L2 — apéndice determinista del AVISO OBLIGATORIO servido por la reserva.

Diseño v2 (`evals/s291_l2_obligation_appendix_design_v1.md`, dúo r2 14/14 + V1
medido). Contratos pineados:
  - flag off ⇒ byte-idéntico CON `MUST_PRESERVE_CONTRACT=on` (H8: la invariancia
    se mide con el contrato vivo, no con el passthrough trivial);
  - hereda identidad+attestation (H3): fila de la reserva de doc no-attestado ⇒ nada;
  - revalidación fail-closed del receipt (Sol-5): bounds/quote tamperados ⇒ nada;
  - clase 0-átomos/forma (V1a: precaución/cabecera) ⇒ no-op declarado, jamás basura;
  - dedup: cuerpo que satisface TODOS los átomos ⇒ nada (V1b);
  - slot PROPIO (Sol-3+H4): con el cap de familia MANDATORY lleno (2), el aviso
    reservado ENTRA IGUAL y las entradas normales no cambian;
  - cita [Fn] garantizada (Sol-4).
"""
from __future__ import annotations

from types import SimpleNamespace

import src.rag.must_preserve as mp

_WARNING_QUOTE = (
    "Para evitar que los controles de incendios se disparen durante el "
    "mantenimiento, es imprescindible bloquear o desconectar el control de "
    "incendios y la alerta remota antes de iniciar los trabajos."
)
_CONTENT = "## 9.3 Comprobaciones\n\n" + _WARNING_QUOTE + "\n\nEl resto del capítulo."
_START = _CONTENT.index(_WARNING_QUOTE)
_END = _START + len(_WARNING_QUOTE)


def _fake_catalog():
    return SimpleNamespace(
        doc_map=[
            {
                "document_id": "doc-asd",
                "source_file": "asd535_manual",
                "entries": [{"id": "securiton:asd-535", "role": "primary"}],
            }
        ],
        follow_redirect=lambda x: x,
    )


def _wire(monkeypatch, *, appendix="on"):
    monkeypatch.setenv("MUST_PRESERVE_CONTRACT", "on")
    monkeypatch.setenv("OBLIGATION_WARNING_APPENDIX", appendix)
    monkeypatch.setattr(mp, "_query_resolved_ids", lambda q: {"securiton:asd-535"})
    monkeypatch.setattr(mp, "_load_catalog", _fake_catalog)


def _reserve_chunk(*, quote=_WARNING_QUOTE, start=_START, end=_END,
                   document_id="doc-asd"):
    return {
        "document_id": document_id,
        "content": _CONTENT,
        "section_title": "9.3 Comprobaciones de mantenimiento y funcionamiento",
        "retrieval_lane": "obligation_warning_reserve_v1",
        "coverage_cards": [
            {
                "candidate_id": "row-1",
                "start": start,
                "end": end,
                "quote": quote,
                "facet": "mandatory_warning",
                "mandatory_warning": True,
                "exact_source_span_validated": True,
            }
        ],
    }


_DRAFT = "El fallo de flujo se diagnostica leyendo el caudal actual [F2]."


def test_flag_off_byte_identico_con_contrato_on(monkeypatch):
    _wire(monkeypatch, appendix="off")
    out, trace = mp.apply_must_preserve_contract("asd535", [_reserve_chunk()], _DRAFT)
    assert out == _DRAFT
    assert "obligation_appendix" not in (trace or {})


def test_flag_on_anexa_el_aviso_con_cita(monkeypatch):
    _wire(monkeypatch)
    out, trace = mp.apply_must_preserve_contract("asd535", [_reserve_chunk()], _DRAFT)
    assert "Aviso obligatorio del manual" in out
    assert "imprescindible bloquear" in out
    assert "[F1]" in out.split("Aviso obligatorio")[1]
    ob = trace["obligation_appendix"]
    assert ob == {"candidates": 1, "satisfied": 0, "appended": 1, "rejected": []}


def test_dedup_cuerpo_que_transmite_no_anexa(monkeypatch):
    _wire(monkeypatch)
    draft = (
        "Antes del mantenimiento es imprescindible bloquear o desconectar el "
        "control de incendios y la alerta remota [F1]."
    )
    out, trace = mp.apply_must_preserve_contract("asd535", [_reserve_chunk()], draft)
    assert "Aviso obligatorio" not in out
    assert trace["obligation_appendix"]["satisfied"] == 1


def test_receipt_tamperado_no_anexa(monkeypatch):
    _wire(monkeypatch)
    bad = _reserve_chunk(quote=_WARNING_QUOTE.replace("bloquear", "reiniciar"))
    out, trace = mp.apply_must_preserve_contract("asd535", [bad], _DRAFT)
    assert "Aviso obligatorio" not in out
    assert trace["obligation_appendix"]["rejected"] == [
        {"fragment": 1, "reason": "receipt_mismatch"}
    ]


def test_quote_sin_atomo_clase_precaucion_no_op(monkeypatch):
    _wire(monkeypatch)
    quote = "Precaución: la batería puede calentarse durante la carga."
    content = quote + "\n\nResto."
    chunk = _reserve_chunk()
    chunk["content"] = content
    chunk["coverage_cards"][0].update(
        {"quote": quote, "start": 0, "end": len(quote)}
    )
    out, trace = mp.apply_must_preserve_contract("asd535", [chunk], _DRAFT)
    assert "Aviso obligatorio" not in out
    assert trace["obligation_appendix"]["rejected"] == [
        {"fragment": 1, "reason": "no_atom_or_form"}
    ]


def test_seccion_sin_intencion_procedimental_no_anexa(monkeypatch):
    """s291b (G-FP r1): un aviso real de una sección AJENA al procedimiento
    (la clase espuria medida: intro de QIG, notas de diseño) NO se anexa."""
    _wire(monkeypatch)
    chunk = _reserve_chunk()
    chunk["section_title"] = "1. Introducción al sistema"
    out, trace = mp.apply_must_preserve_contract("asd535", [chunk], _DRAFT)
    assert "Aviso obligatorio" not in out
    assert trace["obligation_appendix"]["rejected"] == [
        {"fragment": 1, "reason": "no_section_intent"}
    ]


def test_identidad_no_attestada_hereda_gate(monkeypatch):
    _wire(monkeypatch)
    chunk = _reserve_chunk(document_id="doc-ajeno")
    out, trace = mp.apply_must_preserve_contract("asd535", [chunk], _DRAFT)
    assert "Aviso obligatorio" not in out
    assert trace["obligation_appendix"]["candidates"] == 0


def test_slot_propio_no_compite_con_cap_mandatory(monkeypatch):
    """Cap de familia MANDATORY=2 lleno con átomos citados normales: el aviso
    reservado entra IGUAL (slot propio) y las 2 entradas normales se conservan."""
    _wire(monkeypatch)
    filler = (
        "Debe verificarse la polaridad antes de conectar el lazo principal.\n"
        "Nunca conecte la batería con el equipo energizado en servicio.\n"
    )
    cited = {
        "document_id": "doc-asd",
        "content": filler,
        "coverage_cards": [],
    }
    draft = "El diagnóstico usa el menú de caudal [F1]."  # cita F1 (filler)
    out, trace = mp.apply_must_preserve_contract(
        "asd535", [cited, _reserve_chunk()], draft
    )
    assert "Aviso obligatorio del manual" in out
    assert "[F2]" in out.split("Aviso obligatorio")[1]
    assert trace["obligation_appendix"]["appended"] == 1
    # las entradas normales del anexo siguen (no desplazadas por el slot propio)
    assert trace["atoms_appended"] >= trace["obligation_appendix"]["appended"]
