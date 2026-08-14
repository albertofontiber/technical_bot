# -*- coding: utf-8 -*-
"""s321 E4 (DEC-215) — El clarify-por-divergencia lee el CATÁLOGO gobernado.

Gates del dúo r26: (Sol M2) el gate MT no assertaba bytes → aquí el TEXTO
EXACTO del clarify pre/post migración; casos positivos Y negativos del eje;
(Fable) variantes DERIVADAS de miembros (jamás re-declaradas ni fallback
hardcoded); guard hp009 (divergent:true SIN eje disparado JAMÁS clarifica —
la lección DEC-082); fail-open declarado.
"""
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import src.orchestrator.conversation_policy_impl as impl  # noqa: E402
from src.orchestrator.conversation_policy import PolicyRoute, WorkingState  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_specs():
    impl._clarify_specs_cache = None
    yield
    impl._clarify_specs_cache = None


def _resolver(query, models=("ZXE",)):
    ws = WorkingState(
        last_target_models=tuple(models),
        last_turn_at=datetime.now(timezone.utc),
    )
    pol = impl.DeterministicConversationPolicy()
    return pol.resolve(query=query, turn_models=(), available_models=None,
                       working_state=ws, now=datetime.now(timezone.utc))


def test_specs_derivan_del_catalogo():
    specs = impl._clarify_specs()
    assert set(specs) >= {"ZXE", "ZXSE"}
    assert specs["ZXE"]["variantes"] == "1/2/5"
    assert specs["ZXSE"]["variantes"] == "1/2/5/10"
    assert "cuántos lazos" in specs["ZXE"]["eje"]


def test_texto_exacto_del_clarify_zxe():
    """El BYTE-snapshot del seed (Sol M2: el gold guardaba solo no-vacío)."""
    r = _resolver("¿cuántos lazos tiene la ZXe?")
    assert r.route is PolicyRoute.CLARIFY
    assert r.clarify_question == (
        "La ZXE tiene variantes por número de lazos (1/2/5) y ese dato "
        "cambia entre ellas. ¿Con qué variante estás trabajando?")


def test_texto_exacto_del_clarify_zxse():
    r = _resolver("¿cuántas zonas soporta la ZXSe?", models=("ZXSE",))
    assert r.route is PolicyRoute.CLARIFY
    assert "(1/2/5/10)" in r.clarify_question


def test_negativo_eje_no_disparado_responde_generico():
    """Pregunta de familia FUERA del eje → jamás clarify (guard hp009/DEC-082:
    divergent:true por sí solo NUNCA dispara)."""
    r = _resolver("¿qué resistencia de fin de línea lleva la ZXe?")
    assert r.route is not PolicyRoute.CLARIFY


def test_negativo_modelo_no_familia():
    r = _resolver("¿cuántos lazos tiene la CAD-150?", models=("CAD-150",))
    assert r.route is not PolicyRoute.CLARIFY


def test_variantes_derivadas_no_hardcoded():
    """(Fable r26) sin re-declaración ni fallback: prefijo/sufijo común fuera."""
    assert impl._variantes_de_miembros(["ZX1e", "ZX2e", "ZX5e"]) == "1/2/5"
    assert impl._variantes_de_miembros(
        ["ZX1Se", "ZX2Se", "ZX5Se", "ZX10Se"]) == "1/2/5/10"
    # degeneración → canónicos completos, jamás una lista inventada
    assert impl._variantes_de_miembros(["A", "A"]) == "A/A"
    assert impl._variantes_de_miembros([]) == ""


def test_fail_open_sin_catalogo(monkeypatch):
    """Catálogo no cargable → familia sin clarify (divergencia DECLARADA con
    el seed, con warning) — nunca una excepción en el turno."""
    impl._clarify_specs_cache = None
    monkeypatch.setattr(
        "src.rag.catalog_resolver.catalogo_cargado",
        lambda: (_ for _ in ()).throw(RuntimeError("catálogo roto")))
    assert impl._clarify_specs() == {}
    r = _resolver("¿cuántos lazos tiene la ZXe?")
    assert r.route is not PolicyRoute.CLARIFY


def test_el_seed_esta_retirado():
    assert not hasattr(impl, "FAMILY_REGISTRY")
    assert not hasattr(impl, "_FamilySpec")
    assert "FAMILY_REGISTRY" not in impl.__all__
