"""Regression tests for WIRING_INTENT + reranker chunk summary.

These cover the 20 abril 2026 fix for the diagram-attachment bug. Three
problems compounded:

1. The reranker had no visibility into chunks' has_diagram flag.
2. It had no wiring-aware prompt.
3. Even when a diagram_search was added, it returned off-topic diagrams
   (e.g. 'Bloqueo de Memoria' for a sirena-conexionado query), which the
   reranker correctly dropped as irrelevant.

Fix stack: expose [DIAGRAMA DISPONIBLE] in the reranker prompt, add a
WIRING_INTENT prompt hint, and narrow diagram_search to
content_type='wiring' for wiring-intent queries so the diagrams are
BOTH on-topic AND present.

Live validation on hp018 confirmed: diagram attached + PASS.
"""
import pytest

from src.rag.reranker import WIRING_INTENT


@pytest.mark.parametrize("query,should_match", [
    # --- Wiring / installation phrasings from the eval set ---
    ("¿Cómo se conecta un módulo de aislamiento en un lazo ID2000?", True),
    ("¿Cuál es el conexionado correcto de una sirena convencional?", True),
    ("¿Cómo se conectan las baterías de 24V en la CAD-150?", True),
    ("Conexionado de sirena en Morley ZXe zona 1", True),
    ("¿Cómo se cablea la VESDA?", True),
    ("¿Dónde se conecta el cable de tierra?", True),
    ("Instalación del módulo aislador", True),
    ("Diagrama de bornes del panel", True),
    ("Esquema de conexión de detectores", True),
    ("Montaje del pulsador manual", True),

    # --- Conjugations — must catch all forms of 'conectar' ---
    ("El detector se conecta al lazo", True),     # conecta
    ("Los módulos se conectan en serie", True),   # conectan
    ("Ya está conectado", True),                  # conectado
    ("Instalar el sistema", True),                # instalar
    ("Instalación del equipo", True),             # instalación
    ("Cableamos la zona hoy", True),              # cableamos

    # --- Queries that should NOT match (not about wiring) ---
    ("¿Cómo programo el retardo de alarma?", False),
    ("¿Cuál es el consumo en reposo?", False),
    ("¿Qué temperatura soporta el detector?", False),
    ("¿Cómo entro al menú de programación?", False),
    ("Mi central da error al arrancar", False),
    ("¿Cuántos lazos direccionables soporta?", False),   # 'lazos' alone is not wiring intent
    ("¿Qué detectores son compatibles?", False),
])
def test_wiring_intent(query, should_match):
    got = bool(WIRING_INTENT.search(query))
    assert got == should_match, f"Query {query!r} — expected match={should_match}, got={got}"


def test_wiring_intent_respects_word_boundary():
    # 'cable' is wiring, but 'cablegrama' (telegram) should not trigger —
    # \b prevents partial-word match on 'cable'.
    # Note: 'cablea\w*' DOES match 'cableado', 'cablear', but 'cable\b'
    # requires word boundary, so 'cablegrama' doesn't match it.
    # However 'cablea\w*' would match 'cablegrama' only if it started with 'cablea'
    # — and 'cablegrama' starts with 'cable' then 'grama', so it doesn't match
    # 'cablea\w*'.
    assert WIRING_INTENT.search("cableado") is not None
    assert WIRING_INTENT.search("cablegrama") is None
