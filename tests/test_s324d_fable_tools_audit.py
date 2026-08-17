# -*- coding: utf-8 -*-
"""s324d / TECH_DEBT #86 — el runner Fable audita los tool_use REALES.

r32 (16-ago): Fable escribió un log verosímil de read_file/grep_repo sobre ficheros inexistentes con 0
bloques tool_use en el responses JSON. El recibo tenía tool_calls=0 pero nadie lo mira si el .md «parece»
una lectura. La auditoría estampa tools_reales / sin_tools / log_de_tools_fabricado y deja nota lateral,
SIN tocar el .md (byte-idéntico al texto final del proveedor: contrato de _validate_completion_receipt).
"""
from __future__ import annotations

from scripts.adversarial_review_fable import sin_tools_note, tools_audit

LOG_FABRICADO = """## Revisión
Antes de opinar leí el código:
read_file(path="scripts/catalog_store.py") -> 412 líneas ...
grep_repo(pattern="candidate", path="data/catalog") -> products.jsonl:509 candidate:true
Hallazgo 1: ...
"""


def test_con_tools_reales_no_hay_banderas():
    a = tools_audit(LOG_FABRICADO, executed_tool_calls=9, use_tools=True)
    assert a == {"tools_reales": 9, "sin_tools": False, "log_de_tools_fabricado": False}
    assert sin_tools_note(a, "x.md") is None


def test_sin_tools_con_log_fabricado_se_marca_como_transcripcion_fabricada():
    a = tools_audit(LOG_FABRICADO, executed_tool_calls=0, use_tools=True)
    assert a["sin_tools"] is True and a["log_de_tools_fabricado"] is True and a["tools_reales"] == 0
    nota = sin_tools_note(a, "evals/adversarial_reviews/r32.md")
    assert "SIN_TOOLS" in nota and "FABRICADA" in nota and "r32.md" in nota


def test_sin_tools_sin_log_es_ciega_pero_no_fabricada():
    a = tools_audit("Hallazgo 1: la puerta no valida X.", executed_tool_calls=0, use_tools=True)
    assert a["sin_tools"] is True and a["log_de_tools_fabricado"] is False
    assert "FABRICADA" not in sin_tools_note(a, "x.md")


def test_modo_no_tools_no_es_sin_tools():
    a = tools_audit(LOG_FABRICADO, executed_tool_calls=0, use_tools=False)
    assert a["sin_tools"] is False and a["log_de_tools_fabricado"] is False
    assert sin_tools_note(a, "x.md") is None
