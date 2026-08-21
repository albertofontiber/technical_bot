"""s332 B4 — la RED: rama F1 de corrección de marca (`F1_MARCA_CORRECCION`).

Nivel 2 de la arquitectura v2 §1: la tabla ASR (nivel 1) PREVIENE las confusiones
tabuladas ya en T1; esta rama RECUPERA las que aún no lo están («me refería a
Kidde» después de que el bot respondiera de otra marca) reconstruyendo la pregunta
ORIGINAL, dejando la asunción VISIBLE y sin tocar el estado con la meta-frase.

El contrato que fijan estos casos —escrito ANTES de cablear, GC2 de la v2 §8:
  · flag off ⇒ conducta de hoy byte-idéntica (`new_brand_no_state`, sin asunciones);
  · la regla es de PLANTILLA CERRADA: dispara «{cue} [artículo] {marca}» y NADA más,
    así que «no me refería a Kidde» (negación) y «me refería a Kidde, ¿y el lazo?»
    (sustancia extra) NO disparan — por construcción, no por léxico de stopwords;
  · precedencia por ORDEN: un modelo explícito bindea antes (rama A) y la rama ni se
    evalúa; sin `last_query` o fuera de ventana, statu quo;
  · `state_query_override` (Sol-3): la base del rebuild es la pregunta ORIGINAL, de
    modo que una SEGUNDA corrección encadenada reconstruye desde ELLA;
  · fail-fast del enum del flag y fail-open del léxico (la cascada sigue).
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import src.orchestrator.conversation_policy_impl as impl
from src.orchestrator.conversation_policy import PolicyRoute, WorkingState
from src.orchestrator.conversation_policy_impl import (
    advance_working_state,
    correction_enabled,
    resolve_conversational_turn,
)

NOW = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)
PREGUNTA_BASE = "¿Qué centrales BQide tienes?"


@pytest.fixture(autouse=True)
def _flags_aislados(monkeypatch):
    """Brazo limpio: el único lever de este fichero es `F1_MARCA_CORRECCION`."""
    for var in ("F1_MARCA_CORRECCION", "F1_MENTION_PRECEDENCE",
                "F1_RESOLVE_GOVERNED", "IDENTITY_RESOLVE"):
        monkeypatch.delenv(var, raising=False)
    yield


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("F1_MARCA_CORRECCION", "on")
    yield


def _ws(**kw) -> WorkingState:
    """Estado de la mañana-Kidde: la pregunta quedó guardada, SIN modelos (el turno
    corrupto no bindeó ninguno — es justo la clase que la red recupera)."""
    base = dict(last_query=PREGUNTA_BASE, last_turn_at=NOW - timedelta(seconds=60))
    base.update(kw)
    return WorkingState(**base)


def _mirror():
    """El espejo MT-1b cargado como módulo (lock-step de la transición, G0-f')."""
    spec = importlib.util.spec_from_file_location(
        "mt_harness_s332", Path(__file__).resolve().parent.parent
        / "scripts" / "test_multiturn_vs_gold.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────── 1 · dispara y declara la asunción
def test_correccion_reconstruye_la_pregunta_original(flag_on):
    res, _ = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    assert res.route is PolicyRoute.STANDALONE
    assert res.rationale == "brand_correction_rebuild"
    assert PREGUNTA_BASE in res.query_for_retrieval
    assert "la marca es Kidde" in res.query_for_retrieval
    assert res.target_models == ()
    assert len(res.asunciones) == 1
    asuncion = res.asunciones[0]
    assert asuncion.kind == "marca_corregida"
    assert asuncion.modo == "reescrito"
    assert asuncion.asumido == "Kidde"          # grafía superficial del usuario
    assert res.state_query_override == PREGUNTA_BASE


# ─────────────────────────── 2 · flag OFF = conducta de HOY, byte-idéntica
def test_flag_off_conducta_de_hoy():
    res, _ = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.query_for_retrieval == "me refería a Kidde"
    assert res.asunciones == ()
    assert res.state_query_override is None


# ─────────────────────────── 3-4 · la plantilla admite caso, puntuación y artículo
def test_mayuscula_y_punto_final_disparan(flag_on):
    res, _ = resolve_conversational_turn("Me refería a Kidde.", _ws(), NOW)
    assert res.rationale == "brand_correction_rebuild"
    assert res.asunciones[0].asumido == "Kidde"


def test_articulo_opcional_dispara(flag_on):
    res, _ = resolve_conversational_turn("me refería a la Kidde", _ws(), NOW)
    assert res.rationale == "brand_correction_rebuild"
    assert "la marca es Kidde" in res.query_for_retrieval


# ─────────────────────────── 5-6 · lo que la plantilla EXCLUYE por construcción
def test_negacion_no_dispara(flag_on):
    # El ancla `^` no admite el «no» previo: «no me refería a Kidde» NO es la
    # corrección «la marca es Kidde» (dice lo contrario).
    res, _ = resolve_conversational_turn("no me refería a Kidde", _ws(), NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


def test_sustancia_extra_no_dispara(flag_on):
    res, _ = resolve_conversational_turn("me refería a Kidde, ¿y el lazo?", _ws(), NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


# ─────────────────────────── 7 · precedencia: el modelo explícito gana (rama A)
def test_modelo_explicito_bindea_por_a(flag_on):
    # La rama de corrección ni se evalúa: A retorna antes con `real` no vacío.
    res, _ = resolve_conversational_turn("me refería a la ID3002", _ws(), NOW)
    assert res.rationale == "explicit_product"
    assert res.target_models == ("ID-3002",)
    assert res.asunciones == ()
    assert res.state_query_override is None


# ─────────────────────────── 8-9 · sin base o fuera de ventana ⇒ statu quo
def test_sin_last_query_no_dispara(flag_on):
    res, _ = resolve_conversational_turn("me refería a Kidde", _ws(last_query=None), NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


def test_fuera_de_ventana_no_dispara(flag_on):
    ws = _ws(last_turn_at=NOW - timedelta(hours=2))
    res, _ = resolve_conversational_turn("me refería a Kidde", ws, NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


# ─────────────────────────── 10 · el léxico es ES/EN (R6)
def test_cue_en_ingles_dispara(flag_on):
    res, _ = resolve_conversational_turn("i meant Kidde", _ws(), NOW)
    assert res.rationale == "brand_correction_rebuild"
    assert "la marca es Kidde" in res.query_for_retrieval


# ─────────────────────────── 11 · la transición guarda la BASE, no la meta-frase
def test_transicion_guarda_la_pregunta_base(flag_on):
    res, ws2 = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    assert ws2.last_query == PREGUNTA_BASE
    assert ws2.last_target_models == ()
    assert ws2.last_turn_at == NOW
    # Y la función de transición, invocada directamente, hace lo mismo (es ELLA la
    # que consume el override — el seam solo la llama).
    ws3 = advance_working_state(_ws(), res, "me refería a Kidde", None, NOW, None)
    assert ws3.last_query == PREGUNTA_BASE


def test_espejo_mt_consume_el_override_igual(flag_on):
    """Lock-step: prod y eval no pueden divergir en la transición (G0-f')."""
    res, ws2 = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    ws_mt = _mirror().update_working_state(
        _ws(), res, "me refería a Kidde", None, NOW, None)
    assert ws_mt.last_query == ws2.last_query == PREGUNTA_BASE


# ─────────────────────────── 12 · encadenado: la base sobrevive a la 2ª corrección
def test_segunda_correccion_reconstruye_desde_la_misma_base(flag_on):
    _, ws2 = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    despues = NOW + timedelta(minutes=1)
    res2, ws3 = resolve_conversational_turn("me refería a Notifier", ws2, despues)
    assert res2.rationale == "brand_correction_rebuild"
    assert PREGUNTA_BASE in res2.query_for_retrieval
    assert "la marca es Notifier" in res2.query_for_retrieval
    assert "Kidde" not in res2.query_for_retrieval      # ni la meta-frase ni la anotada
    assert res2.state_query_override == PREGUNTA_BASE
    assert ws3.last_query == PREGUNTA_BASE


# ─────────────────────────── R2 (§7): marca IGUAL a la del estado ⇒ rebuild
def test_marca_igual_a_la_del_estado_reconstruye_igual(flag_on):
    """Riesgo R2 declarado: el cue con la marca que YA se estaba sirviendo produce
    un rebuild REDUNDANTE pero correcto — y VISIBLE (el sufijo enseña la base)."""
    ws = WorkingState(last_target_models=("CAD-150",),
                      last_query="¿Cuántas zonas tiene la CAD-150?",
                      last_turn_at=NOW - timedelta(minutes=5))
    res, _ = resolve_conversational_turn("me refería a Detnov", ws, NOW)
    assert res.rationale == "brand_correction_rebuild"
    assert res.query_for_retrieval == (
        "¿Cuántas zonas tiene la CAD-150? (el usuario corrige: la marca es Detnov)")
    assert res.target_models == ()


# ─────────────────────────── 13 · enum del flag CERRADO (fail-fast ruidoso)
def test_flag_valor_raro_revienta(monkeypatch):
    monkeypatch.setenv("F1_MARCA_CORRECCION", "1")
    with pytest.raises(RuntimeError, match="F1_MARCA_CORRECCION"):
        correction_enabled()


def test_flag_valor_raro_revienta_tambien_en_el_turno(monkeypatch):
    # Un typo en Railway NO puede degradar en silencio a la conducta de hoy.
    monkeypatch.setenv("F1_MARCA_CORRECCION", "1")
    with pytest.raises(RuntimeError, match="F1_MARCA_CORRECCION"):
        resolve_conversational_turn("me refería a Kidde", _ws(), NOW)


@pytest.mark.parametrize("raw,esperado", [("", False), ("off", False), ("on", True)])
def test_flag_enum_reconocido(monkeypatch, raw, esperado):
    if raw:
        monkeypatch.setenv("F1_MARCA_CORRECCION", raw)
    assert correction_enabled() is esperado


# ─────────────────────────── 14 · léxico ilegible ⇒ fail-open (la cascada sigue)
def test_lexico_ilegible_no_dispara_y_la_cascada_sigue(flag_on, monkeypatch, tmp_path):
    monkeypatch.setattr(impl, "_CORRECTION_LEXICON_PATH", tmp_path / "no_existe.yaml")
    monkeypatch.setattr(impl, "_correction_cache", None)   # se restaura al salir
    assert impl._correction_lexicon() == ()
    res, _ = resolve_conversational_turn("me refería a Kidde", _ws(), NOW)
    assert res.rationale == "new_brand_no_state"
    assert res.asunciones == ()


# ─────────────────────────── gobernanza del léxico versionado
def test_lexico_gobernado_carga_los_cues_declarados():
    cues = impl._correction_lexicon()
    assert "me refería a" in cues and "me referia a" in cues
    assert "i meant" in cues and "i was referring to" in cues
    assert all(c == c.lower().strip() for c in cues)
    assert len(cues) == len(set(cues))
    assert "me refiero era" not in cues      # errata de la spec: NO entra
