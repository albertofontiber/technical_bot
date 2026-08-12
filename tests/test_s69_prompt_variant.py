"""s69 — test de PARIDAD del lever de generación (diseño v3.1 §2.1, corrección cross-model).

El aislamiento del refactor del flag NO se prueba con output del LLM (no-determinista,
DEC-015) sino a nivel de CONSTRUCCIÓN-DEL-PROMPT, $0 y determinista.

s319 (graduación, DEC-210): el DEFAULT dejó de ser el mundo legacy — sin env, el
prompt es fidelity + followups-off + anti-invención-on (= producción verificada en
Railway). El mundo legacy sigue construible con env EXPLÍCITO y su byte-identidad
histórica se sigue assertando — la graduación cambia el default, no borra la vuelta.
"""
import os

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.rag.generator import (  # noqa: E402
    _ANTI_DIAGRAM_BLOCK,
    _FIDELITY_BLOCK,
    _FOLLOWUP_BLOCK,
    _assemble_system,
    SYSTEM_PROMPT,
)


@pytest.fixture
def mundo_legacy(monkeypatch):
    """El mundo pre-graduación, ahora por env EXPLÍCITO."""
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "base")
    monkeypatch.setenv("GENERATOR_FOLLOWUPS", "on")
    monkeypatch.setenv("ANTI_DIAGRAM_INVENTION", "off")
    monkeypatch.setenv("GENERATOR_DIRECT_FIRST", "off")


@pytest.fixture
def sin_env(monkeypatch):
    for flag in ("GENERATOR_PROMPT_VARIANT", "GENERATOR_FOLLOWUPS",
                 "ANTI_DIAGRAM_INVENTION", "GENERATOR_DIRECT_FIRST"):
        monkeypatch.delenv(flag, raising=False)


def test_legacy_explicito_es_byte_identico_a_system_prompt(mundo_legacy):
    assert _assemble_system() == SYSTEM_PROMPT


def test_default_sin_env_es_la_conducta_ship(sin_env):
    # s319: default = fidelity + followups-off + anti-invención-on (producción)
    esperado = ((SYSTEM_PROMPT + _FIDELITY_BLOCK).replace(_FOLLOWUP_BLOCK, "")
                + _ANTI_DIAGRAM_BLOCK)
    assert _assemble_system() == esperado


def test_default_sin_env_lleva_fidelity_y_guardas(sin_env):
    out = _assemble_system()
    assert "COMPLETITUD FIEL" in out
    assert _ANTI_DIAGRAM_BLOCK in out
    assert _FOLLOWUP_BLOCK not in out


def test_fidelity_anade_el_bloque(mundo_legacy, monkeypatch):
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "fidelity")
    out = _assemble_system()
    assert out == SYSTEM_PROMPT + _FIDELITY_BLOCK
    assert out.startswith(SYSTEM_PROMPT)                # base intacto como prefijo
    assert "COMPLETITUD FIEL" in out
    assert len(out) > len(SYSTEM_PROMPT)


def test_base_no_contiene_el_bloque(mundo_legacy):
    assert "COMPLETITUD FIEL" not in _assemble_system()


def test_variante_desconocida_cae_a_base(mundo_legacy, monkeypatch):
    # cualquier valor != "fidelity" → base (fail-safe: no rompe prod ante typo)
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "xxx")
    assert _assemble_system() == SYSTEM_PROMPT


def test_runtime_toggle(mundo_legacy, monkeypatch):
    # el variant se lee en runtime (no import-time) → togglear el A/B en un proceso
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "fidelity")
    a = _assemble_system()
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "base")
    b = _assemble_system()
    assert a != b and b == SYSTEM_PROMPT


def test_bloque_no_rompe_anti_invencion(monkeypatch):
    # la guarda de fidelidad debe coexistir con CERO INVENCIÓN, no contradecirla
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "fidelity")
    out = _assemble_system()
    assert "CERO INVENCIÓN" in out                       # la regla crítica sigue presente
    assert "NUNCA autoriza inventar" in out              # la guarda lo refuerza
