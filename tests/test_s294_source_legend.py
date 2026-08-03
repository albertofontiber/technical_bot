"""s294 — leyenda de referencias: `[F<n>]` → manual · sección · página.

El defecto que cierra lo cazó Alberto USANDO el bot: la respuesta cita `[F10]` y la
línea «Fuente:» final solo nombra el manual, así que la correspondencia nunca se emite
aunque el generador la tenga (sirve cada fragmento con cabecera `[Fragmento N | … |
Manual: …]`). El técnico lee `[F10]` y no sabe a qué apunta.

Contrato que se fija aquí:
  · determinista y post-generación (0 llamadas de modelo);
  · orden ASCENDENTE por nº de fragmento (el lector busca «F10», no «la más citada» —
    al revés que el adjunto de páginas, que ordena por relevancia);
  · solo lista fragmentos CITADOS en el texto FINAL (una cita que el conflict-guard
    borró no puede aparecer en la leyenda);
  · flag default off ⇒ byte-idéntico;
  · fail-open: si la leyenda revienta, la respuesta no se toca;
  · se añade la ÚLTIMA, después del adjunto de páginas: introduce más ocurrencias de
    `[F<n>]` y contarlas como citas del técnico falsearía el orden de relevancia.
"""

import pytest

from src.rag.source_legend import (
    LEGEND_HEADER,
    append_source_legend,
    build_source_legend,
    source_legend_enabled,
)


def _chunk(manual, section=None, page=None):
    return {
        "source_file": manual,
        "section_title": section,
        "page_number": page,
        "document_id": "doc-1",
    }


CHUNKS = [
    _chunk("Manual_CAD-171-MI-716-es", "6.1 Acceso como administrador", 25),
    _chunk("Manual_CAD-171-MI-716-es", "6.3 Ajustes", 26),
    _chunk("Datasheet_CAD-171-DS-736-es", None, None),
]


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("SOURCE_LEGEND", raising=False)
    assert source_legend_enabled() is False
    monkeypatch.setenv("SOURCE_LEGEND", "on")
    assert source_legend_enabled() is True


def test_mapea_cada_cita_a_manual_seccion_y_pagina():
    answer = "Entra como admin [F1] y ve a AJUSTES > AVANZADO [F2]."
    legend = build_source_legend(answer, CHUNKS)
    assert legend.startswith(LEGEND_HEADER)
    lineas = legend.splitlines()[1:]
    assert lineas == [
        "[F1] Manual_CAD-171-MI-716-es · 6.1 Acceso como administrador · p. 25",
        "[F2] Manual_CAD-171-MI-716-es · 6.3 Ajustes · p. 26",
    ]


def test_orden_ascendente_no_por_relevancia():
    """El lector busca «F10»; el adjunto de páginas sí ordena por relevancia."""
    answer = "primero [F2] [F2] [F2] y luego [F1]"
    lineas = build_source_legend(answer, CHUNKS).splitlines()[1:]
    assert lineas[0].startswith("[F1]")


def test_sin_seccion_ni_pagina_no_inventa():
    lineas = build_source_legend("ver [F3]", CHUNKS).splitlines()[1:]
    assert lineas == ["[F3] Datasheet_CAD-171-DS-736-es"]


def test_dedup_de_citas_repetidas():
    lineas = build_source_legend("[F1] y otra vez [F1]", CHUNKS).splitlines()[1:]
    assert len(lineas) == 1


def test_sin_citas_no_hay_leyenda():
    assert build_source_legend("respuesta sin citas", CHUNKS) == ""


def test_cita_fuera_de_rango_se_ignora():
    """Un [F99] alucinado no puede reventar ni inventar una fuente."""
    legend = build_source_legend("segun [F99] y [F1]", CHUNKS)
    assert "[F99]" not in legend
    assert "[F1]" in legend


def test_cap_declarado_no_silencioso():
    chunks = [_chunk(f"Manual_{i}", None, i) for i in range(1, 21)]
    answer = " ".join(f"[F{i}]" for i in range(1, 21))
    legend = build_source_legend(answer, chunks, max_entries=5)
    assert "[F5]" in legend and "[F6]" not in legend
    assert "+15 referencias más" in legend        # el recorte se DICE


def test_append_no_toca_la_respuesta_sin_citas():
    result = {"answer": "sin citas"}
    append_source_legend(result, CHUNKS)
    assert result["answer"] == "sin citas"


def test_append_anade_al_final():
    result = {"answer": "usa [F1] para entrar"}
    append_source_legend(result, CHUNKS)
    assert result["answer"].startswith("usa [F1] para entrar")
    assert LEGEND_HEADER in result["answer"]


def test_append_fail_open(monkeypatch):
    """Un fallo de presentación jamás puede tumbar la respuesta técnica."""
    import src.rag.source_legend as mod

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "build_source_legend", boom)
    result = {"answer": "respuesta [F1]"}
    mod.append_source_legend(result, CHUNKS)
    assert result["answer"] == "respuesta [F1]"


def test_no_falsea_el_orden_del_adjunto_de_paginas():
    """La leyenda va DESPUÉS del adjunto: sus [F<n>] no deben contar como citas.

    Se verifica el efecto real: contar citas sobre la respuesta CON leyenda cambiaría
    el ranking de páginas — por eso el generador la añade la última.
    """
    from src.rag.visual_assets import cited_fragments_ranked

    answer = "solo [F2] importa"
    antes = cited_fragments_ranked(answer, CHUNKS)
    result = {"answer": answer}
    append_source_legend(result, CHUNKS)
    despues = cited_fragments_ranked(result["answer"], CHUNKS)
    assert antes != despues, (
        "si esto deja de ser cierto, la leyenda ya no altera el conteo y el orden de "
        "llamada podría relajarse; hasta entonces debe ir la ÚLTIMA"
    )
