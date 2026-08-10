# -*- coding: utf-8 -*-
"""s316 — Instrumento de TRANSPORTE conversacional (el prerrequisito de #70).

POR QUÉ EXISTE. Dos diseños de fix para #70 fueron NO-SÓLIDO en la misma tarde porque
ambos habrían pasado sus pruebas sin arreglar nada: el harness MT existente
(`scripts/test_multiturn_vs_gold.py`) llama a `policy.resolve` directamente y jamás
recorre `handle_message`, que es donde vive el fallo. Este fichero conduce el punto de
entrada REAL con el patrón de dobles de `test_f1_activation_wiring` (flags F1 congelados,
$0, sin red) y fija la costura transporte↔estado.

QUÉ FIJA (prescripción convergente del dúo s316 — Sol + sub-agente Opus, regla C):
  · TESTIGO (xfail strict): el fallo orgánico A→B→C de query_logs 9-ago 21:58-21:59Z —
    tras «pasemos a productos Morley…» (catalog_shortcut, return temprano SIN tocar
    estado) el follow-up sigue generando con `contexto: NC-PF2`. HOY ES ROJO: el xfail lo
    documenta; cuando el fix aterrice, el XPASS estricto obliga a retirar el marcador.
  · CONTROL CAUSAL (verde): mismo flujo con el estado limpiado a mano tras B → el rojo
    del testigo es EL BUG, no el doble.
  · CONTROL DE NO-REGRESIÓN (verde): «¿es compatible con Morley?» (marca SERVIDA — el
    dúo cazó que Hochiki era un control vacuo: manufacturer_no_model la corta antes) debe
    CONSERVAR el carry-forward hoy y tras cualquier fix.
  · CENSO de ramas terminales (verde): los `return` de handle_message/handle_voice,
    enumerados por AST. El unit del riesgo es la RAMA TERMINAL, no la ruta de log_query
    (7 de 13 returns responden sin log — una puerta por rutas es ciega a la clase de #70).
    Rama nueva ⇒ este test rompe hasta actualizar el censo CONSCIENTEMENTE, decidiendo
    qué hace esa rama con el estado conversacional.

REGLAS DEL DOBLE: los deciders con DB (`manufacturer_in_db`, `_inventario_fabricante`,
`_handle_catalog`, `asegurar_seudonimo`, `log_query`) se stubean como PRECONDICIONES
DECLARADAS calibradas a producción (Morley SÍ es marca servida); el ENRUTADO no se toca.
`user_data` es un dict real por-USUARIO (semántica PTB verificada, no por-conversación).
Limitación declarada: sin control de reloj — los turnos corren dentro de la ventana F1.
"""

import ast
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator import replay_adapters
from src.orchestrator.conversation_policy import WorkingState

ROOT = Path(__file__).resolve().parent.parent

# El caso orgánico, verbatim de query_logs (9-ago 21:53-21:59Z).
TURNO_A = "¿cuáles son las especificaciones técnicas de la NC-PF2?"
TURNO_B = "pasemos a productos Morley. ¿qué centrales de incendios Morley tienes?"
TURNO_C = 'esto parece incluir muchos más productos que "centrales de incendios"'
CONTROL_COMPAT = "¿es compatible con Morley?"


# --- doble de transporte -----------------------------------------------------
class _Chat:
    def __init__(self):
        self.actions = []

    async def send_action(self, action):
        self.actions.append(action)


class _Message:
    def __init__(self, text=""):
        self.text = text
        self.chat = _Chat()
        self.reply_to_message = None      # _capture_reply_explanation → False (fail-open)
        self.replies = []
        self.photos = []
        self.media_groups = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)

    async def reply_photo(self, **kwargs):
        self.photos.append(kwargs)

    async def reply_media_group(self, media, **_kwargs):
        self.media_groups.append(media)


def _update(text, *, update_id=1, chat_id=42, user_id=7):
    return SimpleNamespace(
        message=_Message(text),
        update_id=update_id,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )


_FIXTURE = [{
    "id": "chunk-1",
    "content": "La central NC-PF2 admite 2 zonas convencionales.",
    "similarity": 0.93,
    "product_model": "NC-PF2",
}]

_INVENTARIO_CANNED = "*Morley*: 142 modelos en 247 documentos (stub calibrado a prod)."


@pytest.fixture
def transporte(monkeypatch):
    """F1 congelado ANTES de tocar el handler (patrón test_f1_activation_wiring:92-93)
    + deciders de DB stubeados como precondiciones + registro de todo lo observable."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.rag.retriever as retriever

    monkeypatch.setattr(bot, "ORCHESTRATOR_PATH", True)
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")

    rec = {"generate_queries": [], "logs": [], "replies": []}
    monkeypatch.setattr(bot, "log_query", lambda **k: rec["logs"].append(k) or True)
    monkeypatch.setattr(bot, "has_consent", lambda _uid: True)
    monkeypatch.setattr(bot, "asegurar_seudonimo", lambda _uid: None)

    # Deciders de enrutado con DB → precondición declarada: Morley ES marca servida.
    monkeypatch.setattr(bot, "manufacturer_in_db", lambda m: "morley" in m.lower())

    async def _inventario_async(update):          # _handle_catalog es async
        await update.message.reply_text(_INVENTARIO_CANNED)

    monkeypatch.setattr(bot, "_handle_catalog", _inventario_async)
    monkeypatch.setattr(bot, "_inventario_fabricante",
                        lambda _m: _INVENTARIO_CANNED)

    # Detección determinista y sin DB (mismo patrón que la fixture F1 vecina).
    detect = lambda q: ["NC-PF2"] if "NC-PF2" in q else []  # noqa: E731
    monkeypatch.setattr(retriever, "extract_product_models", detect)
    monkeypatch.setattr(retriever, "get_category_models", lambda cat: [])
    monkeypatch.setattr(bot, "extract_product_models", detect)

    def _generate(query, chunks, *, available_models=None):
        rec["generate_queries"].append(query)
        return {"answer": "Respuesta técnica canned.", "diagrams": []}

    monkeypatch.setattr(
        orch, "from_production", lambda: replay_adapters(
            retrieved=_FIXTURE, generate=_generate))
    return rec


def _turno(bot, context, texto, n):
    u = _update(texto, update_id=n)
    asyncio.run(bot.handle_message(u, context))
    return u


def _sin_rama_de_error(update, rec, *, espera_generacion):
    """Anti-rojo-inatribuible (dúo): el turno debe haber RESPONDIDO por su rama, no por
    el except de _process_query (que respondería un error y loggearía route='rag')."""
    assert update.message.replies, "el turno no respondió nada"
    for r in update.message.replies:
        assert "error" not in r.lower(), f"rama de error alcanzada: {r[:80]}"
    if espera_generacion:
        assert rec["generate_queries"], "no llegó a generación (¿doble roto?)"


# --- TESTIGO (rojo HOY = #70 documentado; XPASS estricto al aterrizar el fix) -
@pytest.mark.xfail(
    strict=True,
    reason="TECH_DEBT #70: catalog_shortcut retorna sin tocar mt_working_state y el "
           "turno siguiente genera con el producto de la marca ANTERIOR (fallo orgánico "
           "query_logs 9-ago 21:58-21:59Z). Si esto pasa a XPASS, el fix aterrizó: "
           "retira el marcador y promociona el test a contrato.")
def test_testigo_cambio_de_marca_no_arrastra(transporte):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={})
    uA = _turno(bot, context, TURNO_A, 1)
    _sin_rama_de_error(uA, transporte, espera_generacion=True)
    ws = context.user_data.get("mt_working_state")
    assert isinstance(ws, WorkingState) and ws.last_target_models == ("NC-PF2",)

    uB = _turno(bot, context, TURNO_B, 2)
    _sin_rama_de_error(uB, transporte, espera_generacion=False)
    assert transporte["logs"] and \
        transporte["logs"][-1].get("route") == "catalog_shortcut", \
        "el turno B no enrutó por catalog_shortcut: el doble está mal calibrado"

    uC = _turno(bot, context, TURNO_C, 3)
    _sin_rama_de_error(uC, transporte, espera_generacion=True)
    # LO QUE #70 ROMPE: el usuario cambió de marca en B; C no puede generar con el
    # producto Kidde arrastrado.
    assert "NC-PF2" not in transporte["generate_queries"][-1], (
        "el turno C generó con el producto de la marca ANTERIOR: "
        f"{transporte['generate_queries'][-1]!r}")


# --- CONTROL CAUSAL: estado limpiado a mano ⇒ VERDE --------------------------
def test_control_causal_estado_limpio_no_arrastra(transporte):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={})
    _turno(bot, context, TURNO_A, 1)
    _turno(bot, context, TURNO_B, 2)

    # La intervención que el fix de #70 deberá hacer, aplicada A MANO: si con esto el
    # turno C sale limpio, el rojo del testigo es EL BUG, no el doble.
    context.user_data["mt_working_state"] = WorkingState()

    uC = _turno(bot, context, TURNO_C, 3)
    _sin_rama_de_error(uC, transporte, espera_generacion=True)
    assert "NC-PF2" not in transporte["generate_queries"][-1]


# --- CONTROL DE NO-REGRESIÓN: compatibilidad con marca SERVIDA ⇒ carry vivo --
def test_control_compatibilidad_conserva_carry(transporte):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={})
    _turno(bot, context, TURNO_A, 1)

    uc = _turno(bot, context, CONTROL_COMPAT, 2)
    _sin_rama_de_error(uc, transporte, espera_generacion=True)
    # HOY correcto y DEBE seguir correcto tras cualquier fix de #70: una pregunta de
    # compatibilidad no es un cambio de tema — el producto en curso se conserva.
    assert "NC-PF2" in transporte["generate_queries"][-1], (
        "regresión: la pregunta de compatibilidad perdió el carry-forward")


# --- CENSO de ramas terminales (el unit del riesgo, no la ruta) --------------
# 7 de los 13 returns de handle_message responden SIN log_query: una puerta por rutas
# es ciega a esa mitad, y esa clase de rama ES #70. Si este censo rompe, añadiste o
# quitaste una rama terminal: actualiza el número Y decide explícitamente qué hace la
# rama nueva con el estado conversacional (deja el porqué en el commit).
_CENSO_RETURNS = {"handle_message": 13, "handle_voice": 3}


def test_censo_ramas_terminales():
    src = (ROOT / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    visto = {}
    for fn in ast.walk(tree):
        if isinstance(fn, ast.AsyncFunctionDef) and fn.name in _CENSO_RETURNS:
            visto[fn.name] = sum(isinstance(n, ast.Return) for n in ast.walk(fn))
    assert visto == _CENSO_RETURNS, (
        f"ramas terminales cambiaron: {visto} != censo {_CENSO_RETURNS}. "
        "Decide qué hace la rama nueva con mt_working_state y actualiza el censo.")
