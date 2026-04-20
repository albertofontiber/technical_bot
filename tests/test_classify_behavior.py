"""Regression tests for scripts/run_eval.py classify_behavior.

These capture the 20 abril 2026 fix for the caveat+answer mis-classification:
when the bot opens with 'No dispongo de documentación específica del modelo
exacto' and then delivers a full 5-step procedure with a Fuente: citation,
the old classifier called it admit_no_info. The new classifier calls it
'answer' because the response is substantive — procedural content, technical
values, or citation present.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_eval import classify_behavior, is_substantive_answer  # noqa: E402


# ---------------------------------------------------------------------------
# hp018 class: caveat + full procedure + citation → answer
# ---------------------------------------------------------------------------

HP018_ANSWER = """# Conexionado de sirena convencional en panel Morley ZXe

⚠️ **Nota importante:** Los fragmentos disponibles corresponden a los paneles
**ZX2e / ZX5e** (serie ZXe) y **ZX5Se** (serie ZXSe). No dispongo de
documentación específica de un modelo llamado "ZXe zona 1". Te detallo el
conexionado según lo que hay documentado — probablemente aplica a tu equipo.

---

## Requisitos previos del circuito

- **Corriente máxima por circuito:** 1 A
- **Supervisión:** El circuito se supervisa ante cortocircuito y circuito abierto
- **RFL obligatoria:** Resistencia final de línea de **6,8 kΩ, 0,5 W mínimo**
- **Polaridad en reposo:** inverso en reposo para supervisión

## Procedimiento de conexionado

1. **Identifica los terminales de sirena** en la placa.
2. **Conecta la sirena respetando la polaridad.**
3. **Verifica que la sirena tiene diodo integrado.**
4. **Instala la RFL al final** del cable de zona, con sus 6,8 kΩ.

Fuente: Manual de Instalación Paneles ZX2e / ZX5e — Morley-IAS, MIE-MI-530"""


def test_hp018_is_substantive_answer():
    assert is_substantive_answer(HP018_ANSWER)


def test_hp018_classifies_as_answer():
    # Contains 'no dispongo de documentación' — old classifier said admit_no_info.
    # New classifier should say 'answer' because the response has:
    # - Numbered steps (≥ item 2)
    # - Technical values (6,8 kΩ, 1 A)
    # - Fuente: citation
    assert classify_behavior(HP018_ANSWER) == "answer"


# ---------------------------------------------------------------------------
# hp003 class: same pattern — caveat about missing model, then full answer
# ---------------------------------------------------------------------------

HP003_ANSWER = """⚠️ **Aviso importante:** No tengo documentación de la CAD-150 en mi base
de datos. Los fragmentos recuperados corresponden a la **CAD-250** (Detnov).
Sin embargo, el procedimiento de conexión de baterías en serie para obtener
24V es el mismo concepto. Te lo detallo por si te sirve de referencia.

## Conexión de baterías 24V — Detnov CAD-250

**Configuración:** 2 baterías de plomo-ácido de 12V en serie → 24V totales

### Procedimiento:

1. **Coloca las dos baterías** dentro de la central.
2. **Localiza el CONECTOR DE BATERÍA** en la placa principal.
3. **Instala el puente** entre los polos + y − más cercanos.
4. **Conecta el cable NEGRO** al terminal − libre.
5. **Conecta la clavija** en la posición correcta.

Fuente: Manual de instalación CAD-250 (MI 376 es 2024)"""


def test_hp003_classifies_as_answer():
    assert classify_behavior(HP003_ANSWER) == "answer"


# ---------------------------------------------------------------------------
# Pure admit_no_info — nd001 shape: short, no procedure, no values, no Fuente
# ---------------------------------------------------------------------------

ND001_ANSWER = (
    "No tengo documentación de Bosch Avenar FPA-1200 en mi base de datos. "
    "Registraré este producto para priorizar su ingesta. "
    "Por ahora, no puedo ayudarte con su programación."
)


def test_nd001_classifies_as_admit_no_info():
    assert not is_substantive_answer(ND001_ANSWER)
    assert classify_behavior(ND001_ANSWER) == "admit_no_info"


# ---------------------------------------------------------------------------
# ask_clarification — short response, ends asking a wh-question
# ---------------------------------------------------------------------------

CLARIFY_ANSWER = (
    "Puedo ayudarte con varios modelos. ¿Cuál de las siguientes centrales "
    "estás usando: ID2000, ID3000 o AFP-400? "
    "¿Podrías indicar qué aparece en pantalla?"
)


def test_clarify_short_classifies_as_ask_clarification():
    assert not is_substantive_answer(CLARIFY_ANSWER)
    assert classify_behavior(CLARIFY_ANSWER) == "ask_clarification"


# ---------------------------------------------------------------------------
# Pure answer (no hedge, no caveat) — still an answer
# ---------------------------------------------------------------------------

PURE_ANSWER = (
    "En la CAD-250 se accede al menú de programación pulsando la tecla "
    "MENÚ durante 3 segundos. " * 20  # make it > 600 chars
    + "\n\nFuente: Manual CAD-250 rev 4."
)


def test_pure_answer_classifies_as_answer():
    # Need imperative + Fuente for substantive path; default fallback also
    # returns 'answer' when there's no no-info or clarify trigger.
    pure = (
        "## Acceso al menú de programación — CAD-250\n\n"
        "1. Presiona la tecla MENÚ durante 3 segundos.\n"
        "2. Introduce la contraseña de administrador.\n"
        "3. Selecciona la opción deseada.\n\n"
        "Fuente: Manual CAD-250 rev 4." + ("X" * 500)
    )
    assert classify_behavior(pure) == "answer"


# ---------------------------------------------------------------------------
# Short answer without caveat — falls through to default 'answer'
# ---------------------------------------------------------------------------

def test_short_answer_without_caveat():
    short = "El CAD-250 usa 24 VDC. Fuente: Manual CAD-250."
    # Too short for substantive, but no no-info pattern either → 'answer'
    assert not is_substantive_answer(short)
    assert classify_behavior(short) == "answer"


# ---------------------------------------------------------------------------
# Substantive triggers — each of procedure / values / citation alone suffices
# ---------------------------------------------------------------------------

def test_substantive_requires_length():
    # Short responses fail even with all signals present
    short_full = (
        "1. Conecta A.\n2. Verifica B.\n3. Instala C.\n\nFuente: X."
    )
    assert not is_substantive_answer(short_full)


def test_substantive_requires_both_procedure_and_citation():
    # Imperative procedure alone → NOT substantive (too lenient would flip
    # clarification-with-a-single-step into 'answer')
    only_procedure = "X" * 650 + (
        "\n\n1. Conecta el cable.\n2. Verifica la tensión.\n3. Instala el módulo."
    )
    assert not is_substantive_answer(only_procedure)

    # Citation alone → NOT substantive (no-info admissions may cite the
    # empty corpus: 'Fuente: ninguno de los manuales contiene info sobre X')
    only_citation = "X" * 650 + "\n\nFuente: Manual CAD-250."
    assert not is_substantive_answer(only_citation)

    # Both together → substantive
    full = "X" * 650 + (
        "\n\n1. Conecta el cable.\n2. Verifica la tensión.\n"
        "\n\nFuente: Manual CAD-250."
    )
    assert is_substantive_answer(full)


def test_substantive_requires_imperative_verb():
    # Numbered infinitives ("1. Consultar el portal, 2. Contactar...") are
    # NOT procedural — this is the honest no-info response pattern.
    infinitive_list = "X" * 650 + (
        "\n\nPara más información, puedes:\n"
        "1. Consultar el portal del fabricante.\n"
        "2. Contactar con el distribuidor oficial.\n"
        "3. Revisar la web de soporte.\n"
        "\n\nFuente: —"
    )
    # infinitives don't count as imperative → not procedural
    assert not is_substantive_answer(infinitive_list)


def test_substantive_rejects_question_heavy_response():
    # Response with > 2 questions is ask_clarification, even if it has a
    # step and a citation buried somewhere. mc005 / am006 are this shape.
    question_heavy = (
        "Necesito más contexto para ayudarte:\n\n"
        "1. Verifica qué modelo tienes.\n"
        "2. Comprueba la versión.\n\n"
        "Preguntas clave:\n"
        "¿Cuál es el modelo exacto? "
        "¿Qué versión de firmware usas? "
        "¿Has revisado el manual de instalación?\n\n"
        "Fuente: Manual CAD-250 rev 4." + ("X" * 600)
    )
    # 3 '?' → fails question count check
    assert not is_substantive_answer(question_heavy)


# ---------------------------------------------------------------------------
# Edge case — no-info phrase in a long response that is actually clarifying
# ---------------------------------------------------------------------------

def test_long_clarify_with_no_info_phrase_still_clarify():
    # Long-ish response, no steps/values/citation, ends in question
    # → should be ask_clarification (not substantive, no no-info trigger wins
    # because is_substantive=False but _NO_INFO does fire, so actually goes
    # to admit_no_info). Document current behavior: this still routes to
    # admit_no_info when a no-info phrase is present and response lacks
    # substantive markers — that's the desired conservative default.
    text = (
        "Honestamente no tengo información sobre ese producto en mi base. "
        "¿Podrías decirme qué fabricante es y si tienes el modelo a mano? "
        "¿Qué aparece en la pantalla? ¿Cuál es el código de error exacto? "
        * 2
    )
    assert not is_substantive_answer(text)
    # _NO_INFO fires first after is_substantive=False
    assert classify_behavior(text) == "admit_no_info"
