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
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.ingestion.page_content import (  # noqa: E402
    auditar_paginas,
    md_tiene_estructura,
    motivo_degeneracion,
    page_content,
    page_content_degradada,
    sanear_record,
)

# El caso REAL, byte a byte: página 1 de TI-007 tal como la devolvió LlamaParse (job 1b73eb2d).
# (dúo r35, Sol+Fable: antes era `"X" * 3708` y el rótulo «caso real» estaba sobre-afirmado —
# validaba los umbrales, no el contenido.)
with open(os.path.join(ROOT, "tests", "fixtures", "s324d_ti007_llamaparse_page1.json"),
          encoding="utf-8") as _fh:
    _FIXTURE = json.load(_fh)
TI007 = {"page": _FIXTURE["page"], "md": _FIXTURE["md"], "text": _FIXTURE["text"]}


def test_el_caso_real_de_ti007_recupera_el_texto():
    """Con el JSON REAL del job: md = la cabecera, text = el documento con el procedimiento."""
    assert len(TI007["md"]) == 34 and len(TI007["text"]) == 3708
    out = page_content(TI007)
    assert out == TI007["text"]
    # y lo rescatado es el CONTENIDO técnico, no un relleno sintético
    for aguja in ("PROG", "Z1", "VSN-4REL", "40 cm"):
        assert aguja in out
    assert page_content_degradada(TI007) is True
    assert motivo_degeneracion(TI007) == "md_colapsado_sin_estructura"


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


# ── dúo r35: los agujeros que Sol y Fable cazaron ────────────────────────────────────────────
def test_md_de_solo_whitespace_se_sanea_en_la_RUTA_CABLEADA():
    """CRÍTICO de Sol: `page_content` caía a `text` con un md de sólo whitespace, pero `sanear_record`
    NO sustituía (usaba otro criterio) y un md de whitespace es *truthy* para los consumidores ⇒ la
    página se perdía igual. Ahora el criterio es ÚNICO y la ruta cableada lo cubre."""
    p = {"page": 1, "md": "\n\n   ", "text": "B" * 3000}
    assert motivo_degeneracion(p) == "md_vacio_o_whitespace"
    saneado, aud = sanear_record({"sha256": "x", "result": {"pages": [p]}})
    assert saneado["result"]["pages"][0]["md"] == p["text"]
    assert aud["n_paginas_afectadas"] == 1


def test_un_markdown_CON_ESTRUCTURA_nunca_se_sustituye_aunque_sea_corto():
    """Fable: una página de TABLA o DIAGRAMA tiene md compacto legítimo y text largo y disperso;
    sustituir ahí EMPEORA el contenido."""
    tabla = {"md": "| Modelo | Zonas |\n|---|---|\n| CAD-150 | 2 |", "text": "X" * 6000}
    lista = {"md": "- Primer paso\n- Segundo paso", "text": "X" * 6000}
    heading = {"md": "# Instalación", "text": "X" * 6000}
    cita = {"md": "> Aviso importante", "text": "X" * 6000}
    for p in (tabla, lista, heading, cita):
        assert md_tiene_estructura(p["md"]) is True
        assert motivo_degeneracion(p) is None and page_content(p) == p["md"]
    assert md_tiene_estructura(TI007["md"]) is False       # la cabecera suelta NO es estructura


def test_la_auditoria_viaja_en_TODOS_los_caminos_de_salida_del_pipeline():
    """Sol y Fable coincidieron: `register_only`, `empty`, `empty_after_language` y `sin_indexar`
    perdían la auditoría, y son justo donde acaba un documento con la extracción rota."""
    from src.reingest import pipeline
    src = inspect.getsource(pipeline.process_file)
    for camino in ('"status": "register_only"', '"status": "empty"',
                   '"status": "empty_after_language"', '"status": "sin_indexar"'):
        i = src.index(camino)
        cola = src[i:i + 400]
        assert "**audit" in cola or "**extra" in cola, f"{camino} pierde la auditoría"
    # y el estado persistido la conserva
    run_src = inspect.getsource(pipeline.run)
    assert run_src.count("_traza_extraccion(result)") >= 4


def test_la_traza_persistida_solo_declara_lo_que_paso():
    from src.reingest.pipeline import _traza_extraccion
    assert _traza_extraccion({"md_degenerado": {"n_paginas_afectadas": 0, "chars_rescatados": 0}}) == {}
    t = _traza_extraccion({"md_degenerado": {"n_paginas_afectadas": 2, "chars_rescatados": 5000},
                           "texto_escaso": True, "chars": 47})
    assert t["md_degenerado"] == {"paginas": 2, "chars_rescatados": 5000}
    assert t["texto_escaso"] == {"chars": 47}


def test_el_cuarto_consumidor_de_serving_usa_la_misma_guarda():
    """Fable: `deep_lookup._item_text` (brazo `fetch_mode()=="llm"`) leía el store crudo con el mismo
    `or`, así que el outline del selector LLM seguía ciego en los docs que la ingesta rescata."""
    from src.rag.deep_lookup import _item_text
    assert _item_text(TI007) == TI007["text"]
    assert _item_text({"value": "solo value"}) == "solo value"
    assert _item_text({"md": "| a | b |", "text": "X" * 9000}) == "| a | b |"
