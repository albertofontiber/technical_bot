"""s283 P1 — STRUCK_OCR_CONTEXT: aplicar la política de tachado-OCR adjudicada del
Evidence Contract TAMBIÉN al contexto servido al generador, flag-gated y por línea.

Cubre:
  (a) módulo LEAF `struck_ocr` (paridad con la política que el EC re-importa);
  (b) `apply_struck_ocr_context` POR LÍNEA (no blob — el corte queda contenido en
      la línea del artefacto; las hermanas quedan intactas);
  (c) el CASO REAL del chunk 475a8f18 (F13 hp011): la superficie que el writer ve
      ON vs OFF;
  (d) el seam del generador: flag off = byte-inerte sobre el contexto servido; on =
      normaliza; fail-fast en valor no reconocido.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.rag.generator as gen
from src.rag import evidence_contract as ec
from src.rag import struck_ocr


# Chunk 475a8f18 p63 (HLSI-MN-103, F13 hp011) VERBATIM del served-dump s283. Una
# ÚNICA línea física (tabla markdown); los `&#xA;` son entidades, no saltos reales.
_F13_CONTENT = (
    '| \\[LCD display showing "r.i"] | Rearme inhibido tras extinción | '
    "De acuerdo con la norma UNE-EN 12094-1:2004, apartado 4.12.2, debe existir "
    "un intervalo de tiempo programable, entre 0 y 30 minutos, desde que la "
    "central notifica el estado de ACTIVADO hasta que permite su rearme."
    "~~- -~~\tRearme inhibido hasta finalizar extinción o cuando agotado tiempo "
    "configurado en parámetro ~~t.Fi~~ (~~t.A~~ → 0 seg.)&#xA;"
    "00\tRearme permitido en cualquier momento (por defecto)&#xA;"
    "De 01 a 30\tRearme inhibido durante intervalo definido (expresado en minutos) |"
)


def _card(content: str, *, source_file="manual-x.pdf", page=5, **extra) -> dict:
    row = {
        "content": content,
        "source_file": source_file,
        "page_number": page,
        "similarity": 0.9,
        "product_model": "RP1r",
        "section_title": "Funcionamiento",
        "content_type": "manual",
    }
    row.update(extra)
    return row


# ───────────────────────── (a) módulo LEAF + paridad EC ─────────────────────────

def test_extraction_is_behavior_identical_to_the_evidence_contract():
    # el EC re-importa la MISMA función (identidad de objeto) → sus tests siguen
    # ejerciendo exactamente esta política vía `_display_span`.
    assert ec._apply_struck_ocr is struck_ocr.apply_struck_ocr
    assert ec._STRUCK_RX is struck_ocr._STRUCK_RX


def test_struck_symbols_only_are_kept_letters_cut():
    # tachado de SÓLO símbolos → conserva contenido (marcador es formato)
    assert struck_ocr.apply_struck_ocr("valor ~~- -~~ fin") == "valor - - fin"
    # PRIMER tachado CON letras → corta el display a partir de ahí
    assert struck_ocr.apply_struck_ocr("param ~~t.Fi~~ (~~t.A~~)") == "param"


def test_no_struck_markers_is_identity():
    assert struck_ocr.apply_struck_ocr("sin nada") == "sin nada"
    assert struck_ocr.apply_struck_ocr_context("uno\ndos\n") == "uno\ndos\n"


# ───────────────────── (b) por-línea, no blob (hermanas intactas) ─────────────────────

def test_context_normalizes_per_line_not_whole_blob():
    text = (
        "linea uno sin nada\n"
        "clave ~~t.Fi~~ dato del display\n"
        "linea tres intacta\n"
        "linea cuatro con 00 valor"
    )
    result = struck_ocr.apply_struck_ocr_context(text)
    lines = result.split("\n")
    assert len(lines) == 4
    assert lines[0] == "linea uno sin nada"          # intacta
    assert lines[1] == "clave"                        # cortada en el tachado-con-letras
    assert lines[2] == "linea tres intacta"           # intacta (blob la habría tirado)
    assert lines[3] == "linea cuatro con 00 valor"    # intacta (blob la habría tirado)
    assert "t.Fi" not in result
    # contraste explícito: el blob entero SÍ truncaría todo lo posterior
    blob = struck_ocr.apply_struck_ocr(text)
    assert "linea tres intacta" not in blob
    assert "linea cuatro con 00 valor" not in blob


# ───────────────────── (c) el caso REAL F13 (chunk 475a8f18) ─────────────────────

def test_real_f13_chunk_surface_on():
    on = struck_ocr.apply_struck_ocr_context(_F13_CONTENT)
    # desaparece el tachado-OCR-con-letras y todo marcador ~~
    assert "~~" not in on
    assert "t.Fi" not in on
    assert "t.A" not in on
    assert "0 seg." not in on
    # se conservan la superficie ANTES del corte
    assert 'r.i' in on            # celda del display LCD (antes de cualquier tachado-con-letras)
    assert "4.12.2" in on         # apartado correcto
    assert "- -" in on            # el tachado de SÓLO símbolos se conserva como formato
    # COLATERAL MEDIDO: la política corta a fin de LÍNEA física; como F13 es una
    # sola línea, caen también las alternativas 00 / De 01 a 30 que van DESPUÉS.
    assert "Rearme permitido en cualquier momento" not in on
    assert "De 01 a 30" not in on
    assert on.endswith("parámetro")


def test_real_f13_chunk_off_is_untouched():
    # OFF = el texto crudo, con los tachados y las alternativas intactos
    assert "~~t.Fi~~" in _F13_CONTENT
    assert "Rearme permitido en cualquier momento" in _F13_CONTENT


# ───────────────────────── (d) seam del generador ─────────────────────────

class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._text)],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
        )


def _fake_anthropic(monkeypatch, text):
    fake = _FakeMessages(text)
    monkeypatch.setattr(
        gen.anthropic, "Anthropic",
        lambda api_key=None: SimpleNamespace(messages=fake),
    )
    return fake


def _served_context(monkeypatch, cards, answer="Respuesta [F1].", query="q") -> str:
    fake = _fake_anthropic(monkeypatch, answer)
    gen.generate_answer(query, [dict(c) for c in cards])
    return fake.calls[0]["messages"][0]["content"]


def test_generator_seam_flag_off_serves_struck_markers_verbatim(monkeypatch):
    monkeypatch.delenv("STRUCK_OCR_CONTEXT", raising=False)
    ctx = _served_context(
        monkeypatch, [_card(_F13_CONTENT, source_file="HLSI-MN-103.pdf", page=63)]
    )
    # byte-inerte: el writer ve el tachado y las alternativas crudas
    assert "~~t.Fi~~" in ctx
    assert "Rearme permitido en cualquier momento" in ctx


def test_generator_seam_flag_on_normalizes_served_context(monkeypatch):
    monkeypatch.setenv("STRUCK_OCR_CONTEXT", "on")
    ctx = _served_context(
        monkeypatch, [_card(_F13_CONTENT, source_file="HLSI-MN-103.pdf", page=63)]
    )
    assert "~~" not in ctx
    assert "t.Fi" not in ctx
    assert "r.i" in ctx           # display cell preservada
    assert "4.12.2" in ctx        # apartado correcto preservado
    assert "Rearme permitido en cualquier momento" not in ctx  # colateral medido


def test_generator_seam_flag_on_leaves_struck_free_content_identical(monkeypatch):
    monkeypatch.setenv("STRUCK_OCR_CONTEXT", "on")
    plain = "Rearme de la central: pulse la tecla Rearme.\nNivel 2 de acceso requerido."
    ctx = _served_context(monkeypatch, [_card(plain, source_file="ctrl.pdf", page=1)])
    assert plain in ctx


def test_generator_seam_flag_fail_fast_on_bad_value(monkeypatch):
    monkeypatch.setenv("STRUCK_OCR_CONTEXT", "bogus")
    _fake_anthropic(monkeypatch, "x")
    with pytest.raises(RuntimeError):
        gen.generate_answer("q", [_card("hola")])
