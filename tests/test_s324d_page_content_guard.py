# -*- coding: utf-8 -*-
"""s324d / TECH_DEBT #87 — la ingesta no puede volver a quedarse con un markdown DEGENERADO.

El defecto (confirmado el 17-ago sobre `HLSI-TI-007_VSN-4REL`, re-parse con la config real del corpus
`parse_page_with_agent` + `anthropic-sonnet-4.5`): LlamaParse devolvió `md` = 34 chars y `text` = 3.708
chars en el MISMO JSON; los tres consumidores hacían `p.get("md") or p.get("text")`, que solo cae a
`text` si `md` es vacío, y el corpus se quedó con 47 chars de un PDF con 2.246 chars de texto NATIVO.
No era OCR: el texto estaba en el campo de al lado.

Lo que ancla este fichero:
  1. la guarda dispara con el caso REAL de TI-007 y devuelve el texto, no la cabecera;
  2. NO dispara cuando el markdown es legítimamente algo más corto que el texto plano (el agente limpia
     cabeceras/pies) — ni en páginas cortas, donde la pérdida absoluta es pequeña;
  3. se mantiene el comportamiento previo en los casos que ya funcionaban (md vacío → text; text vacío → md);
  4. la auditoría declara las páginas afectadas y los chars rescatados (un fallback silencioso es lo que
     dejó a TI-007 en 47 chars sin que nadie se enterara);
  5. el saneamiento vive en el ORQUESTADOR (`pipeline.process_file` llama a `sanear_record` ANTES de B2/B3/B7):
     los tres consumidores siguen intactos —`chunk.py` está pineado por sha en el freeze-contract de CI
     (s130/s132) y ese guardarraíl paró mi primer intento de tocarlo—, y el saneamiento no muta el registro
     original ni el store en disco.
"""
from __future__ import annotations

import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.reingest.page_content import (  # noqa: E402
    auditar_paginas,
    page_content,
    page_content_degradada,
    sanear_record,
)

# El caso real, con las cifras del job 1b73eb2d.
TI007 = {"page": 1, "md": "\n\n**Honeywell Life Safety Iberia**", "text": "X" * 3708}


def test_el_caso_real_de_ti007_recupera_el_texto():
    assert len(TI007["md"]) == 34
    out = page_content(TI007)
    assert out == TI007["text"] and len(out) == 3708
    assert page_content_degradada(TI007) is True


def test_no_dispara_con_un_markdown_legitimamente_mas_corto():
    """El agente limpia cabeceras/pies: md algo más corto que text es NORMAL, no degenerado."""
    p = {"md": "A" * 4000, "text": "B" * 4600}          # ratio 0.87
    assert page_content(p) == p["md"] and page_content_degradada(p) is False
    p2 = {"md": "A" * 1200, "text": "B" * 4000}         # ratio 0.30 — sospechoso pero no inequívoco
    assert page_content(p2) == p2["md"]


def test_no_dispara_en_paginas_cortas_aunque_el_ratio_sea_pequeno():
    """Portada/separador: ratio ínfimo pero la pérdida absoluta es pequeña ⇒ no se toca."""
    p = {"md": "# Portada", "text": "Portada del manual, edición 2024. " * 10}   # ~340 chars
    assert len(p["text"]) - len(p["md"]) < 500
    assert page_content(p) == p["md"] and page_content_degradada(p) is False


def test_conserva_el_comportamiento_previo_en_los_casos_que_ya_funcionaban():
    assert page_content({"md": "", "text": "contenido"}) == "contenido"
    assert page_content({"md": "   ", "text": "contenido"}) == "contenido"
    assert page_content({"md": "contenido"}) == "contenido"
    assert page_content({"md": "contenido", "text": ""}) == "contenido"
    assert page_content({}) == ""
    assert page_content({"md": None, "text": None}) == ""


def test_la_auditoria_declara_paginas_afectadas_y_chars_rescatados():
    sanas = [{"page": 2, "md": "A" * 2000, "text": "B" * 2100}]
    a = auditar_paginas([TI007] + sanas)
    assert a["n_paginas_afectadas"] == 1
    assert a["paginas_con_md_degenerado"][0]["page"] == 1
    assert a["chars_rescatados"] == 3708 - 34
    assert auditar_paginas([])["n_paginas_afectadas"] == 0
    assert auditar_paginas(sanas)["chars_rescatados"] == 0


def test_sanear_record_sustituye_la_pagina_y_no_muta_el_original():
    original = {"sha256": "abc", "result": {"pages": [dict(TI007), {"page": 2, "md": "A" * 2000, "text": "B" * 2100}]}}
    saneado, auditoria = sanear_record(original)
    assert saneado is not original
    assert saneado["result"]["pages"][0]["md"] == TI007["text"]           # rescatado
    assert saneado["result"]["pages"][0]["md_degenerado_sustituido_por_text"] is True
    assert saneado["result"]["pages"][1] is original["result"]["pages"][1]  # página sana: sin copia
    assert original["result"]["pages"][0]["md"] == TI007["md"]           # el original NO se toca
    assert auditoria["chars_rescatados"] == 3708 - 34


def test_sanear_record_es_inerte_cuando_no_hay_nada_degenerado():
    original = {"sha256": "abc", "result": {"pages": [{"page": 1, "md": "A" * 2000, "text": "B" * 2100}]}}
    saneado, auditoria = sanear_record(original)
    assert saneado is original and auditoria["n_paginas_afectadas"] == 0
    vacio, aud = sanear_record({"sha256": "x"})
    assert vacio == {"sha256": "x"} and aud["n_paginas_afectadas"] == 0


def test_el_pipeline_sanea_ANTES_de_leer_el_record_y_no_toca_el_chunker_congelado():
    """El saneamiento ocurre en `process_file` antes de B2/B3/B7; `chunk.py` está pineado por sha en
    `evals/s132_ci_evidence_contract_v1.yaml` (freeze del pre-registro s130) y NO se modifica."""
    from src.reingest import chunk, contextualize, language, pipeline
    src = inspect.getsource(pipeline.process_file)
    assert "sanear_record(record)" in src
    assert src.index("sanear_record(record)") < src.index("profile_document(record)") < src.index("chunk_document(record)")
    for mod in (chunk, contextualize, language):                       # intactos: siguen con su `or`
        assert 'p.get("md") or p.get("text")' in inspect.getsource(mod)
