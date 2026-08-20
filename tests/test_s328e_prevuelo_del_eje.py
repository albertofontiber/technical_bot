# -*- coding: utf-8 -*-
"""s328e — El PRE-VUELO del eje: la única puerta por la que un prompt llega a los datos.

POR QUÉ EXISTE ESTA PUERTA. El eje `es_pregunta` es la decisión más cara del
clasificador: un `false` equivocado saca el mensaje de TODO el análisis y no
deja rastro (un error de categoría, en cambio, lo pone en la barra de al lado y
se ve). Y esa conducta **la sostiene el prompt, no el código** — «qué productos
Detnov tienes», sin signos, la decide el LLM, porque la regla dura mira el signo
FINAL, que es la adjudicación literal de Alberto.

Consecuencia incómoda: **no hay test que pueda proteger eso**, porque un test
con un LLM de mentira no mide al modelo. Lo que SÍ se puede testear —y es lo que
hace este fichero— es el ARNÉS: que la sonda distingue, que la huella detecta un
prompt cambiado, y que una regresión **aborta sin escribir nada**.

La medición contra el modelo de verdad vive aparte, con su recibo:
`evals/s328c_sonda_sin_signos_v1.md` y `evals/sonda_eje_ultima_pasada.json`.
"""
from __future__ import annotations

import json

import pytest

from src import clasificacion


def _llm_que_dice(es_pregunta: bool, categoria: str = "otros"):
    def _responder(_prompt: str) -> str:
        return json.dumps({"categoria": categoria, "marcas": [],
                           "es_pregunta": es_pregunta})
    return _responder


def _llm_correcto():
    """Contesta como debe: pregunta si el texto pide algo, no si no."""
    piden = set(clasificacion.SONDA_EJE_PREGUNTAS)

    def _responder(prompt: str) -> str:
        pide = any(caso in prompt for caso in piden)
        return json.dumps({"categoria": "catalogo_especificaciones" if pide
                           else "otros", "marcas": [], "es_pregunta": pide})
    return _responder


@pytest.fixture()
def taxonomia():
    return clasificacion.cargar_taxonomia()


# ------------------------------------------------------------------ la sonda


def test_la_sonda_pasa_con_un_clasificador_que_acierta(taxonomia):
    resultado = clasificacion.correr_sonda_eje(_llm_correcto(), taxonomia)
    assert resultado["pasa"] is True
    assert resultado["preguntas_reconocidas"] == resultado["preguntas_totales"]
    assert resultado["controles_limpios"] == resultado["controles_totales"]


def test_la_sonda_CAZA_el_eje_regresado(taxonomia):
    """El fallo que importa: el modelo deja de ver como preguntas las que no
    llevan signos. Es invisible en producción —los mensajes simplemente
    desaparecen del análisis— y esto es lo que lo hace visible."""
    resultado = clasificacion.correr_sonda_eje(_llm_que_dice(False), taxonomia)
    assert resultado["pasa"] is False
    assert resultado["preguntas_reconocidas"] == 0
    assert len(resultado["no_reconocidas"]) == len(clasificacion.SONDA_EJE_PREGUNTAS)


def test_la_sonda_NO_se_contenta_con_decir_pregunta_a_todo(taxonomia):
    """El control del control. Sin los cuatro casos negativos, un clasificador
    que contestara «pregunta» siempre sacaría 8/8 y parecería perfecto."""
    resultado = clasificacion.correr_sonda_eje(_llm_que_dice(True), taxonomia)
    assert resultado["pasa"] is False
    assert resultado["preguntas_reconocidas"] == resultado["preguntas_totales"]
    assert len(resultado["falsos_positivos"]) == len(
        clasificacion.SONDA_EJE_NO_PREGUNTAS)


def test_una_respuesta_que_el_parser_RECHAZA_cuenta_como_fallo(taxonomia):
    """No se ignora: la fila se quedaría pendiente y el eje no se habría
    medido. Un silencio no es un aprobado."""
    resultado = clasificacion.correr_sonda_eje(lambda _p: "no soy JSON", taxonomia)
    assert resultado["pasa"] is False
    assert resultado["preguntas_reconocidas"] == 0


# ------------------------------------------------------------------ la huella


def test_la_huella_cambia_si_cambia_una_DESCRIPCION(taxonomia):
    """La huella es mejor señal que `version` del YAML, y este test dice por
    qué: el contrato «tocar una descripción obliga a subir version» es una
    convención que nadie impide saltarse. La huella no se puede saltar."""
    original = clasificacion.huella_prompt(taxonomia)
    retocada = clasificacion.Taxonomia(
        version=taxonomia.version,      # `ids` es propiedad derivada de aquí
        categorias=tuple((cid, desc + " (retoque)") if i == 0 else (cid, desc)
                         for i, (cid, desc) in enumerate(taxonomia.categorias)),
    )
    assert clasificacion.huella_prompt(retocada) != original
    assert retocada.version == taxonomia.version      # la versión NO se tocó


def test_la_huella_NO_cambia_si_no_cambia_nada(taxonomia):
    assert (clasificacion.huella_prompt(taxonomia)
            == clasificacion.huella_prompt(clasificacion.cargar_taxonomia()))


# ------------------------------------------------- el pre-vuelo dentro del job


def test_una_regresion_ABORTA_el_job_sin_escribir_nada(monkeypatch, tmp_path):
    """Lo que de verdad protege esto. Si la sonda falla, `correr_pendientes`
    ni se llama: no se escribe una sola fila con un prompt que rompe el eje."""
    from scripts import clasificar_preguntas as job

    monkeypatch.setattr(job, "_HUELLA", tmp_path / "huella.json")
    monkeypatch.setattr(job, "construir_llm", lambda *a, **k: _llm_que_dice(False))
    llamado = []
    monkeypatch.setattr(job, "correr_pendientes",
                        lambda *a, **k: llamado.append(True))

    seguir, apunte = job._prevuelo_del_eje("clave-de-mentira", "modelo", False)
    assert seguir is False
    assert apunte["estado"] == "REGRESION"
    assert not llamado                       # no se llegó a clasificar nada
    assert not (tmp_path / "huella.json").exists()   # ni se apuntó un aprobado


def test_al_pasar_se_APUNTA_la_huella_y_la_siguiente_no_re_mide(monkeypatch, tmp_path):
    from scripts import clasificar_preguntas as job

    huella = tmp_path / "huella.json"
    monkeypatch.setattr(job, "_HUELLA", huella)
    corridas = []

    def _sonda(llm, taxonomia):
        corridas.append(True)
        return clasificacion.correr_sonda_eje(_llm_correcto(), taxonomia)

    monkeypatch.setattr(job, "construir_llm", lambda *a, **k: _llm_correcto())
    monkeypatch.setattr(job, "correr_sonda_eje", _sonda)

    seguir, apunte = job._prevuelo_del_eje("clave", "modelo", False)
    assert seguir is True and apunte["estado"] == "pasa"
    assert huella.exists() and len(corridas) == 1

    seguir, apunte = job._prevuelo_del_eje("clave", "modelo", False)
    assert seguir is True and apunte["estado"] == "sin_cambios"
    assert len(corridas) == 1                # NO se volvió a gastar en el LLM


def test_sin_clave_de_anthropic_no_hay_prompt_que_medir(monkeypatch, tmp_path):
    """Sin LLM el eje lo decide solo la regla dura, que es código y tiene sus
    propios tests. Medir un prompt que no se va a usar sería teatro."""
    from scripts import clasificar_preguntas as job

    monkeypatch.setattr(job, "_HUELLA", tmp_path / "huella.json")
    seguir, apunte = job._prevuelo_del_eje("", "modelo", False)
    assert seguir is True and apunte["estado"] == "no_aplica_sin_llm"


def test_la_bandera_de_escape_existe_pero_DEJA_HUELLA(monkeypatch, tmp_path):
    """`--sin-sonda` tiene que existir —el criterio puede cambiar a propósito y
    entonces la sonda estorba— pero no puede ser silenciosa: el recibo dice que
    se escribió con un prompt sin medir."""
    from scripts import clasificar_preguntas as job

    monkeypatch.setattr(job, "_HUELLA", tmp_path / "huella.json")
    seguir, apunte = job._prevuelo_del_eje("clave", "modelo", True)
    assert seguir is True
    assert apunte["estado"] == "OMITIDA_por_bandera"
    assert "huella_prompt" in apunte
