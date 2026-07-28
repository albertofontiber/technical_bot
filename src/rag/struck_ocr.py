"""Política de TACHADO-OCR adjudicada (feedback_7segment) como módulo LEAF.

``apply_struck_ocr`` es la función que el Evidence Contract (``evidence_contract.py``)
ya usaba en ``_display_span`` para no re-afirmar una transliteración 7-segmentos
dudosa. Se movió aquí VERBATIM (cero cambio de comportamiento — los tests del EC
siguen verdes: el EC la re-importa con su nombre histórico ``_apply_struck_ocr``)
para que el seam de contexto servido al generador (flag ``STRUCK_OCR_CONTEXT``,
``generator.py``) aplique EXACTAMENTE la misma política SIN importar el módulo
pesado del contrato — cuyo propio contrato de seam exige NO importarse con su flag
off (``test_flag_off_seam_is_byte_inert_and_never_imports_the_module``). Este
módulo sólo depende de ``re``.

Política (adjudicada s722/1222, ``feedback_7segment``): un tachado de SÓLO
símbolos/dígitos conserva su contenido (el marcador es formato); el PRIMER tachado
CON letras corta el display — superficie que la propia extracción marcó como NO
fiable. Jamás re-afirmar una transliteración dudosa.
"""
from __future__ import annotations

import re

_STRUCK_RX = re.compile(r"~~(.*?)~~")
_LETTER_RX = re.compile(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]")


def apply_struck_ocr(text: str) -> str:
    """Segmentos TACHADOS por la extracción (``~~…~~``): un tachado de solo
    símbolos/dígitos conserva su contenido (el marcador es formato); el PRIMER
    tachado CON letras corta el display — es superficie que la propia extracción
    marcó como no fiable (feedback_7segment: jamás re-afirmar una transliteración
    dudosa; el hash del receipt sigue anclando el span original y el riesgo viaja
    declarado en ``seven_segment_risk``)."""
    if "~~" not in text:
        return text
    parts: list[str] = []
    pos: int | None = 0
    for m in _STRUCK_RX.finditer(text):
        if _LETTER_RX.search(m.group(1)):
            parts.append(text[pos:m.start()])
            pos = None
            break
        parts.append(text[pos:m.start()] + m.group(1))
        pos = m.end()
    if pos is not None:
        parts.append(text[pos:])
    return "".join(parts).strip()


def apply_struck_ocr_context(text: str) -> str:
    """Aplica ``apply_struck_ocr`` POR LÍNEA FÍSICA del contexto servido — la MISMA
    granularidad con la que el Evidence Contract lo aplica (a un span/línea de
    obligación en ``_display_span``), NUNCA a un chunk multilínea entero: aplicado
    al blob completo, el primer tachado-con-letras de CUALQUIER línea truncaría
    todo lo que sigue en el resto del chunk. Por línea, el corte queda contenido en
    la línea que trae el artefacto.

    Byte-preservador salvo en las líneas con ``~~``: una línea sin ``~~`` se
    devuelve idéntica (early-out de ``apply_struck_ocr``), y ``"\\n".join(split)``
    reconstruye el separador exacto. Las líneas con ``~~`` heredan el ``.strip()``
    de la política del EC (adjudicado)."""
    if "~~" not in text:
        return text
    return "\n".join(apply_struck_ocr(line) for line in text.split("\n"))
