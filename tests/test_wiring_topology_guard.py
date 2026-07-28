"""Tests del guard C' de topología de cableado (s286, spec v3.1 — fixtures pre-registrados)."""
from __future__ import annotations

import pytest

from src.rag.wiring_topology_guard import (
    _NOTICE,
    apply_wiring_topology_guard,
)


def _chunk(content: str, source_file: str = "MIE-MI-530rv001") -> dict:
    return {"content": content, "source_file": source_file, "page_number": 21}


SIREN_SUPPORT = _chunk(
    "3.4.4 Circuitos de Sirenas: las sirenas se conectan una tras otra a lo largo de la "
    "linea del circuito de sirena, con la resistencia final de linea al final."
)
SIREN_NO_TOPO = _chunk(
    "Cada sirena debera tener un diodo integrado; el circuito de sirenas se polariza en "
    "inverso en reposo para supervisar la linea."
)
OTHER_DOC_TOPO = _chunk(
    "El tablero interface en serie SIB-2048 comunica los anunciadores.", "15037SP"
)


class TestDeteccion:
    def test_asercion_no_soportada_se_retira(self):
        answer = (
            "## Salidas de sirena\n\n"
            "1. **Conecta las sirenas en serie** (una tras otra), sin ramales [F1].\n\n"
            "La RFL de 6K8 va al final del circuito [F1]."
        )
        revised, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "surgical_repair"
        assert "en serie" not in revised
        assert _NOTICE in revised
        assert "RFL de 6K8" in revised  # el bloque correcto sobrevive

    def test_asercion_soportada_pasa(self):
        answer = (
            "## Circuito de sirenas\n\n"
            "Las sirenas se conectan una tras otra a lo largo de la linea [F1]."
        )
        revised, trace = apply_wiring_topology_guard([SIREN_SUPPORT], answer)
        assert trace["action"] == "noop"
        assert revised == answer

    def test_negada_no_dispara(self):
        answer = (
            "## Sirenas\n\n"
            "No conectes las sirenas en serie: cada sirena va sobre el par con su diodo [F1]."
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "noop"

    def test_soporte_cross_doc_no_legitima(self):
        # el termino de topologia vive en OTRO documento (interface en serie, sin stem-sirena)
        answer = "## Sirenas\n\nConecta las sirenas en serie hasta la ultima [F1]."
        _, trace = apply_wiring_topology_guard([OTHER_DOC_TOPO], answer)
        assert trace["action"] == "surgical_repair"

    def test_cadena_de_polaridad_conector_flecha(self):
        answer = (
            "## Salidas de sirena\n\n"
            "Une el terminal - de la primera sirena → + de la siguiente [F1]."
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "surgical_repair"

    def test_fuera_de_scope_intacto(self):
        answer = (
            "## Baterias\n\n"
            "Dos baterias de 12V conectadas en serie suman los 24V del sistema [F1]."
        )
        revised, trace = apply_wiring_topology_guard(
            [_chunk("baterias de 12V en serie", "hp003doc")], answer
        )
        assert trace["action"] == "noop"
        assert revised == answer


class TestFences:
    def test_fence_inventado_se_retira(self):
        answer = (
            "## Sirenas\n\n"
            "```\n+ Salida A --[Sirena 1]--[Sirena 2]--+\n                RFL 6K8\n```"
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] in {"surgical_repair", "fail_closed"}

    def test_fence_verbatim_de_chunk_pasa(self):
        esquema = "+ Salida A ---[diodo]--- RFL"
        answer = f"## Sirenas\n\n```\n{esquema}\n```"
        _, trace = apply_wiring_topology_guard([_chunk(f"esquema: {esquema}")], answer)
        assert trace["action"] == "noop"

    def test_tabla_markdown_exenta(self):
        answer = (
            "## Sirenas\n\n"
            "```\n| Salida | Carga |\n| A | 1 A |\n| B | 1 A |\n```"
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "noop"


class TestHerencia:
    def test_heading_negrita_hereda_stem(self):
        answer = (
            "**Salidas de sirena de placa**\n\n"
            "Conectalas en cadena hasta la ultima y cierra con la RFL [F1]."
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "surgical_repair"

    def test_heading_hermano_corta_la_herencia(self):
        answer = (
            "## Sirenas\n\nRespeta la polaridad [F1].\n\n"
            "## Alimentacion auxiliar\n\nLos equipos se conectan en cadena al bus [F1]."
        )
        _, trace = apply_wiring_topology_guard([SIREN_NO_TOPO], answer)
        assert trace["action"] == "noop"


class TestContrato:
    def test_notice_es_detector_clean(self):
        # la notice en scope-sirena no debe re-disparar el detector (anti auto-flageo)
        answer = f"## Sirenas\n\n{_NOTICE}"
        revised, trace = apply_wiring_topology_guard([], answer)
        assert trace["action"] == "noop"
        assert revised == answer

    def test_fail_closed_si_todo_es_unsafe(self):
        answer = "## Sirenas\n\nConecta las sirenas en serie [F9]."
        revised, trace = apply_wiring_topology_guard([], answer)
        # bloque unico peligroso -> notice; la notice es limpia -> repair basta
        assert trace["action"] == "surgical_repair"
        assert "en serie" not in revised

    def test_tipo_invalido(self):
        with pytest.raises(TypeError):
            apply_wiring_topology_guard([], None)  # type: ignore[arg-type]

    def test_traza_sha(self):
        _, trace = apply_wiring_topology_guard([], "## Otro tema\n\nSin sirenas aqui.")
        assert trace["action"] == "noop"
        assert len(trace["output_answer_sha256"]) == 64


class TestCasoRealTraza:
    def test_run1_de_la_traza_s286(self):
        # extracto literal del run 1 (evals/s286_hp018_trace_v1.jsonl) — el caso que motiva todo
        answer = (
            "## Procedimiento de conexionado\n\n"
            "1. **Conecta las sirenas en serie** (en linea directa, sin ramales), respetando "
            "la polaridad: terminal **+** de la salida al **+** de la primera sirena, el **-** "
            "de esa sirena al **+** de la siguiente, y asi sucesivamente [F3].\n\n"
            "4. **Coloca la Resistencia Final de Linea (RFL) de 6.800 Ω** entre el **+** y "
            "el **-** de la ultima sirena de cada circuito [F3]."
        )
        revised, trace = apply_wiring_topology_guard(
            [SIREN_NO_TOPO, SIREN_NO_TOPO, SIREN_NO_TOPO], answer
        )
        assert trace["action"] == "surgical_repair"
        assert "en serie" not in revised
        assert "de esa sirena al" not in revised
