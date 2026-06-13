"""s69 — test de PARIDAD del lever de generación (diseño v3.1 §2.1, corrección cross-model).

El aislamiento del refactor del flag NO se prueba con output del LLM (no-determinista,
DEC-015) sino a nivel de CONSTRUCCIÓN-DEL-PROMPT, $0 y determinista: con
GENERATOR_PROMPT_VARIANT=base el `system` ensamblado debe ser BYTE-IDÉNTICO a SYSTEM_PROMPT
(prueba que el refactor es inerte en base); con fidelity, == SYSTEM_PROMPT + _FIDELITY_BLOCK.
"""
import os

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.rag.generator import _assemble_system, SYSTEM_PROMPT, _FIDELITY_BLOCK  # noqa: E402


def test_base_es_byte_identico_a_system_prompt(monkeypatch):
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "base")
    assert _assemble_system() == SYSTEM_PROMPT


def test_default_sin_env_es_base(monkeypatch):
    monkeypatch.delenv("GENERATOR_PROMPT_VARIANT", raising=False)
    assert _assemble_system() == SYSTEM_PROMPT          # default INERTE = prod


def test_fidelity_anade_el_bloque(monkeypatch):
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "fidelity")
    out = _assemble_system()
    assert out == SYSTEM_PROMPT + _FIDELITY_BLOCK
    assert out.startswith(SYSTEM_PROMPT)                # base intacto como prefijo
    assert "COMPLETITUD FIEL" in out
    assert len(out) > len(SYSTEM_PROMPT)


def test_base_no_contiene_el_bloque(monkeypatch):
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "base")
    assert "COMPLETITUD FIEL" not in _assemble_system()


def test_variante_desconocida_cae_a_base(monkeypatch):
    # cualquier valor != "fidelity" → base (fail-safe: no rompe prod ante typo)
    monkeypatch.setenv("GENERATOR_PROMPT_VARIANT", "xxx")
    assert _assemble_system() == SYSTEM_PROMPT


def test_runtime_toggle(monkeypatch):
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
