# -*- coding: utf-8 -*-
"""Contenido de una página extraída — con guarda de MARKDOWN DEGENERADO (s324d, TECH_DEBT #87).

**Por qué existe este módulo.** Los tres consumidores del JSON de LlamaParse (`chunk.py`,
`contextualize.py`, `language.py`) hacían `p.get("md") or p.get("text") or ""`. Ese `or` solo cae a
`text` cuando `md` es VACÍO — no cuando es DEGENERADO. Caso confirmado el 17-ago sobre
`HLSI-TI-007_VSN-4REL` (re-parse con la misma config del corpus, `parse_page_with_agent` +
`anthropic-sonnet-4.5`, job 1b73eb2d):

    md   = "\\n\\n**Honeywell Life Safety Iberia**"      →   34 chars
    text = el documento entero                          → 3708 chars

El corpus se quedó con 47 chars de un documento cuyo PDF tiene 2.246 chars de texto NATIVO (el
procedimiento de configuración del VSN-4REL: puente PROG, tecla Z1, combinaciones Z1/Z2/Z3, cables
de 40 cm y 6 cm). No era un PDF escaneado ni un problema de OCR: el texto estaba en el MISMO JSON,
en el campo de al lado, y el `or` lo tapó.

**La guarda.** Se usa `text` en lugar de `md` sólo cuando el markdown es degenerado de forma
INEQUÍVOCA: relativamente diminuto (`< RATIO_DEGENERADO`) **y** con una pérdida absoluta grande
(`≥ PERDIDA_ABSOLUTA_MIN` chars). Los dos umbrales juntos, y no cada uno por su lado, son lo que
hace improbable el falso positivo: un markdown legítimamente más corto que el texto plano (el agente
limpia cabeceras/pies repetidos) pierde decenas de chars, no miles.

**Dónde vive la guarda y por qué.** El saneamiento se aplica UNA vez en el orquestador
(`pipeline.process_file`, sobre el `record` completo) y no dentro de los tres consumidores, por dos
razones: (1) `src/reingest/chunk.py` está PINEADO POR SHA en un freeze-contract activo de CI
(`evals/s132_ci_evidence_contract_v1.yaml` → `s130_chunker_utf8_lf`; el pre-registro s130 congela el
chunker como instrumento) — tocarlo rompe el contrato y ese guardarraíl hizo bien en pararme; (2)
normalizar la ENTRADA es responsabilidad del orquestador, no de cada consumidor: así los tres ven la
misma página saneada y no hay tres sitios donde el arreglo se pueda olvidar.

**Alcance REAL de la guarda (dúo r35 — no son «tres consumidores», son cuatro y medio):**
- `pipeline.process_file` → saneado (idioma, chunking, contextualización ven la página buena).
- `rag/deep_lookup._item_text` (SERVING, brazo `fetch_mode()=="llm"`) → usa esta misma guarda desde
  r35 (lo cazó Fable): construye el outline leyendo el store crudo, así que sin ella el selector LLM
  seguiría ciego justo en los documentos que la guarda rescata.
- `reingest/chunk_provenance.materialize_raw_record` → **NO saneado, a propósito**: su contrato es
  reproducir determinísticamente lo que el chunker CONGELADO ve del artefacto CRUDO (lo usan sólo
  los scripts de auditoría s117/s135, nunca la ingesta). Sanear ahí rompería la reproducibilidad de
  esos experimentos. Si alguna vez se materializa PARA INGESTAR, hay que sanear antes.

**Gap declarado (s324d):** el store de extracción del corpus (966 JSON de mayo) NO está en este
checkout ni en el OneDrive de esta máquina (busqué: sólo hay 2 JSON locales), así que estos umbrales
NO se calibraron contra la distribución real de `len(md)/len(text)` — se eligieron conservadores, y
la guarda falla hacia el comportamiento ACTUAL (usar `md`). El dúo r35 pidió correr `auditar_paginas`
sobre el store real ANTES de mergear; **no se pudo, y queda como condición pendiente** (TECH_DEBT
#87): con el store delante son minutos y $0.
"""
from __future__ import annotations

import re as _re

# Un markdown que mide menos de esta fracción del texto plano es sospechoso...
RATIO_DEGENERADO = 0.25
# ...y sólo se sustituye si además la pérdida absoluta es grande (evita falsos positivos en páginas
# cortas: portadas, hojas de un párrafo, separadores).
PERDIDA_ABSOLUTA_MIN = 500

# (dúo r35, Fable) Tercera condición, contra la clase de falso positivo que ni Sol ni yo habíamos
# acotado: una página de TABLA o DIAGRAMA puede tener un `md` legítimamente compacto (la tabla
# renderizada) frente a un `text` largo y disperso (etiquetas posicionales sueltas) — ahí sustituir
# EMPEORA el contenido. Un markdown con ESTRUCTURA (tabla, lista, heading, cita) es producto real
# del agente y no se toca, mida lo que mida. El `md` de TI-007 (`**Honeywell Life Safety Iberia**`)
# no tiene ninguna: es una cabecera suelta, que es la firma del colapso.
_ESTRUCTURA_MD = _re.compile(r"^\s{0,3}(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>\s|```)", _re.M)


def md_tiene_estructura(md: str) -> bool:
    """¿El markdown trae estructura (heading, lista, tabla, cita, bloque de código)?"""
    return bool(_ESTRUCTURA_MD.search(md or ""))


def page_content(page: dict) -> str:
    """Contenido de UNA página del JSON de extracción, con la guarda de md degenerado."""
    md = (page.get("md") or "")
    text = (page.get("text") or "")
    if not md.strip():
        return text
    if not text.strip():
        return md
    if _degenerado(md, text):
        return text
    return md


def _degenerado(md: str, text: str) -> bool:
    """Criterio ÚNICO de degeneración. `page_content`, `page_content_degradada`, `auditar_paginas` y
    `sanear_record` lo comparten a propósito: en r35 Sol cazó que yo tenía dos criterios distintos
    (el helper caía a `text` con un `md` de sólo whitespace, pero el saneamiento cableado NO lo
    sustituía — y `"\n\n"` es *truthy* para los consumidores, así que la página se perdía igual)."""
    if not md.strip():
        return bool(text.strip())
    if not text.strip():
        return False
    if md_tiene_estructura(md):
        return False
    return len(md) < RATIO_DEGENERADO * len(text) and (len(text) - len(md)) >= PERDIDA_ABSOLUTA_MIN


def page_content_degradada(page: dict) -> bool:
    """¿Esta página activa la guarda? MISMO criterio que `page_content` (r35)."""
    return _degenerado(page.get("md") or "", page.get("text") or "")


def motivo_degeneracion(page: dict) -> str | None:
    """Por qué se sanea esta página (para la traza; `None` si no se sanea)."""
    md, text = (page.get("md") or ""), (page.get("text") or "")
    if not _degenerado(md, text):
        return None
    return "md_vacio_o_whitespace" if not md.strip() else "md_colapsado_sin_estructura"


def auditar_paginas(pages: list[dict]) -> dict:
    """Censo de la guarda sobre un documento extraído: qué páginas la activan, por qué motivo y
    cuánto texto se habría perdido sin ella. Va al registro de estado del pipeline — un fallback
    silencioso es justo lo que dejó a TI-007 en 47 chars sin que nadie se enterara."""
    afectadas, chars_rescatados = [], 0
    for p in pages or []:
        motivo = motivo_degeneracion(p)
        if motivo:
            md_n, text_n = len(p.get("md") or ""), len(p.get("text") or "")
            afectadas.append({"page": p.get("page"), "md_chars": md_n, "text_chars": text_n,
                              "motivo": motivo})
            chars_rescatados += text_n - md_n
    return {"paginas_con_md_degenerado": afectadas,
            "n_paginas_afectadas": len(afectadas),
            "chars_rescatados": chars_rescatados}


def sanear_record(record: dict) -> tuple[dict, dict]:
    """Devuelve `(record_saneado, auditoría)`: una COPIA del registro de extracción en la que cada
    página con markdown degenerado lleva su `text` en el campo `md`, más el censo de lo rescatado.

    Copia superficial dirigida (no `deepcopy`: los JSON de extracción pesan): se clonan sólo el dict
    raíz, `result` y las páginas afectadas. El original no se toca — quien lo re-lea (o el store en
    disco) sigue viendo lo que devolvió LlamaParse.
    """
    result = record.get("result") or {}
    pages = result.get("pages") or []
    auditoria = auditar_paginas(pages)
    if not auditoria["n_paginas_afectadas"]:
        return record, auditoria
    nuevas = []
    for p in pages:
        motivo = motivo_degeneracion(p)
        if motivo:
            q = dict(p)
            q["md"] = page_content(p)                       # criterio ÚNICO, no una copia de la regla
            q["md_degenerado_sustituido_por_text"] = True   # traza en el propio objeto
            q["md_degenerado_motivo"] = motivo
            nuevas.append(q)
        else:
            nuevas.append(p)
    nuevo_result = dict(result)
    nuevo_result["pages"] = nuevas
    nuevo_record = dict(record)
    nuevo_record["result"] = nuevo_result
    return nuevo_record, auditoria
