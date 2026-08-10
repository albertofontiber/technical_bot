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
    """Despacha un turno REPLICANDO el orden de grupos de python-telegram-bot.

    En producción `run_bot` registra `brand_switch_guard` como `TypeHandler` en
    **grupo -1** y `handle_message` en el grupo 0 por defecto; PTB ejecuta los grupos
    en orden. El instrumento no levanta una `Application`, así que replica ese orden
    a mano. `test_guardia_registrada_en_grupo_menos_uno` fija que el registro real
    sigue siendo ese — si alguien mueve el grupo, este doble deja de ser fiel y ese
    test lo canta.
    """
    u = _update(texto, update_id=n)
    asyncio.run(bot.brand_switch_guard(u, context))     # grupo -1
    asyncio.run(bot.handle_message(u, context))         # grupo 0
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


# --- TESTIGO 2: el fall-through, causa (2) — SIGUE ROJO (etapa 2) ------------
@pytest.mark.xfail(
    strict=True,
    reason="TECH_DEBT #70 causa (2), NO cubierta por la etapa 1: «¿y en Morley cómo se "
           "hace el reset?» no declara switch ni pide inventario, así que la guardia no "
           "dispara; el turno llega a F1 y la política lo clasifica "
           "brand_compatibility_in_window (conversation_policy_impl:398-403) → arrastra. "
           "Arreglarlo toca el clasificador, que tiene contrato congelado y gate MT "
           "propio (DEC-154). XPASS ⇒ la etapa 2 aterrizó: retira el marcador.")
def test_testigo_fallthrough_marca_sin_switch_explicito(transporte):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={})
    _turno(bot, context, TURNO_A, 1)

    uB = _turno(bot, context, "¿y en Morley cómo se hace el reset?", 2)
    _sin_rama_de_error(uB, transporte, espera_generacion=True)
    assert "NC-PF2" not in transporte["generate_queries"][-1], (
        "el fall-through generó con el producto de la marca ANTERIOR: "
        f"{transporte['generate_queries'][-1]!r}")


# --- CONTROL: la guardia NO se traga un "cambio" a la MISMA marca ------------
# (dúo s316, Sol M2) La v1 de este control usaba «¿qué más centrales Kidde tienes?»,
# que NO casa `_ENUM_FABRICANTE` ⇒ `_marca_destino` devolvía None y el test quedaba
# verde SIN llegar nunca a la comparación de fabricante. Era vacuo: pasaba aunque se
# borrara la extensión de identidad. Aquí la frase SÍ resuelve destino, así que la
# única razón de no limpiar es la comparación Kidde==Kidde.
def test_control_misma_marca_ejerce_la_comparacion(transporte):
    import src.bot.telegram_bot as bot

    assert (bot._marca_destino("pasemos a Kidde") or "").lower() == "kidde", \
        "precondición: la frase debe resolver destino, o el control vuelve a ser vacuo"

    user_data = {"mt_working_state": WorkingState(last_target_models=("NC-PF2",),
                                                  last_query=TURNO_A)}
    invalidada = bot._invalidar_si_cambio_de_marca(user_data, "pasemos a Kidde")
    assert invalidada is None, "la guardia invalidó con la MISMA marca (NC-PF2 es Kidde)"
    assert user_data["mt_working_state"].last_target_models == ("NC-PF2",)


def test_guardia_invalida_con_marca_distinta_unit(transporte):
    """Espejo del anterior: misma frase, marca DISTINTA ⇒ sí invalida."""
    import src.bot.telegram_bot as bot

    user_data = {"mt_working_state": WorkingState(last_target_models=("NC-PF2",),
                                                  last_query=TURNO_A),
                 "last_detected_models": ["NC-PF2"]}
    invalidada = bot._invalidar_si_cambio_de_marca(user_data, "pasemos a Morley")
    assert (invalidada or "").lower() == "morley"
    assert user_data["mt_working_state"].last_target_models == ()
    # rollback-safe: el régimen legacy también queda limpio (si mañana se quita
    # CONVERSATION_POLICY de Railway, #70 no revive con la guardia puesta).
    assert "last_detected_models" not in user_data
    # reset COMPLETO: last_query residual haría is_empty False y el turno siguiente
    # contestaría «Ha pasado un rato» siendo mentira.
    assert user_data["mt_working_state"].is_empty


# --- PRECISIÓN: la guardia NO puede disparar con vocabulario del dominio -----
# Batería del sub-agente s316 (medida end-to-end: con la v1 el bot pasaba de contestar
# a pedir modelo). El daño de un FALSO POSITIVO es peor que el del bug: rompe un turno
# que funcionaba. Por eso la guardia se calibra precisión-primero.
_NO_DEBEN_DISPARAR = [
    "y ahora la central de fuego no rearma, ¿cómo la reseteo?",
    "¿y ahora cómo se rearma después de un fuego?",
    "ahora con el detector de fuego en alarma, ¿cómo silencio la sirena?",
    "ahora el panel de fuego marca avería de tierra",
    "pasa a modo prueba y dime si el fuego se simula",
    "vamos a ver si es compatible con detectores Morley",   # muletilla, no switch
    "vamos a ver, ¿es compatible con Morley?",
    "¿es compatible con Morley?",
    "¿y en Morley cómo se hace el reset?",                  # etapa 2, no la guardia
    "¿qué productos tienes?",
]

_DEBEN_DISPARAR = [
    ("pasemos a productos Morley. ¿qué centrales de incendios Morley tienes?", "Morley"),
    ("pasemos de Kidde a Morley", "Morley"),                # posicional: destino, no origen
    ("pasemos a Xtralis", "Xtralis"),                       # marca solo-DB (fallo Securiton)
    ("pasemos a Securiton", "Securiton"),
    ("ahora con productos Morley", "Morley"),               # palabra intermedia
    ("¿qué centrales de incendios Morley tienes?", "Morley"),
]


# Lista de marcas CONGELADA para precisión/recall: `_marca_en_consulta` consulta la DB
# viva, así que sin esto el resultado depende del entorno — en CI (sin credenciales) la
# resolución devolvía None y «pasemos a Xtralis» no disparaba, mientras en local sí.
# Un instrumento cuyo veredicto cambia con el entorno no es un instrumento. Se fija el
# vocabulario REAL de producción (30 marcas, verificado hoy contra la DB).
_MARCAS_CONGELADAS = [
    "Notifier", "Morley", "Kidde", "Detnov", "Aritech", "System Sensor", "Xtralis",
    "Spectrex", "Pfannenberg", "Argus Security", "LDA audioTech", "Securiton",
    "Fidegas", "Pepperl-Fuchs", "Edwards", "Sensitron", "Honeywell", "LGM Products",
    "Avotec", "European Safety Systems", "Zellweger Analytics", "KAC", "FUEGO",
    "OGGIONI", "SenseWare", "Sound Alert", "COELBO", "Testifire", "Venitem",
    "Hosiden Besson",
]


@pytest.fixture
def marcas_congeladas(monkeypatch):
    """Congela la lista de fabricantes: sin DB, determinista, igual en local y en CI."""
    import src.bot.telegram_bot as bot
    monkeypatch.setattr(bot, "get_available_manufacturers",
                        lambda: list(_MARCAS_CONGELADAS))
    monkeypatch.setattr(bot, "_marcas_db_cache", None)
    yield
    bot._marcas_db_cache = None          # no contaminar tests vecinos


@pytest.mark.parametrize("consulta", _NO_DEBEN_DISPARAR)
def test_precision_la_guardia_calla(consulta, marcas_congeladas):
    import src.bot.telegram_bot as bot
    assert bot._marca_destino(consulta) is None, (
        f"FALSO POSITIVO: la guardia borraría contexto legítimo en {consulta!r}")


@pytest.mark.parametrize("consulta,esperada", _DEBEN_DISPARAR)
def test_recall_la_guardia_dispara(consulta, esperada, marcas_congeladas):
    import src.bot.telegram_bot as bot
    got = bot._marca_destino(consulta)
    assert (got or "").lower() == esperada.lower(), f"{consulta!r} → {got!r}"


def _colisiones(bot, marcas):
    return {m for m in marcas
            if m.lower() in bot._VOCABULARIO_DOMINIO
            and m.lower() not in bot._MARCAS_AMBIGUAS}


def test_ninguna_marca_colisiona_con_el_dominio_SIEMPRE():
    """LA parte estructural: una lista negra se pudre, un detector no. Corre SIEMPRE
    —también en CI sin credenciales— sobre el vocabulario congelado, que es el que la
    guardia va a ver en producción. (La v1 solo corría con DB y se SALTABA en CI:
    la pieza que yo llamaba estructural era inerte justo donde debía proteger.)"""
    import src.bot.telegram_bot as bot

    colisiones = _colisiones(bot, _MARCAS_CONGELADAS)
    assert not colisiones, (
        f"marcas que colisionan con vocabulario del dominio: {sorted(colisiones)}. "
        "Decláralas en _MARCAS_AMBIGUAS o la guardia borrará contexto al nombrarlas.")


def test_la_lista_congelada_no_ha_derivado_de_la_DB():
    """Tripwire de deriva: si el corpus gana un fabricante, la lista congelada deja de
    representar producción y hay que actualizarla CONSCIENTEMENTE — que es cuando se
    ejecuta el detector de arriba sobre el nombre nuevo. Requiere credenciales; en CI
    se salta, y por eso el detector NO depende de este test."""
    import src.bot.telegram_bot as bot

    try:
        vivas = bot.get_available_manufacturers() or []
    except Exception:                                  # noqa: BLE001
        pytest.skip("sin acceso a la lista de fabricantes")
    if not vivas:
        pytest.skip("lista de fabricantes vacía")

    nuevas = {m for m in vivas} - set(_MARCAS_CONGELADAS)
    faltan = set(_MARCAS_CONGELADAS) - {m for m in vivas}
    assert not nuevas and not faltan, (
        f"la lista congelada derivó de la DB — nuevas: {sorted(nuevas)}, "
        f"desaparecidas: {sorted(faltan)}. Actualiza _MARCAS_CONGELADAS y comprueba que "
        "ninguna nueva colisiona con el vocabulario del dominio.")


# --- CONTRATO DE CABLEADO: la guardia vive en el grupo -1 --------------------
def test_guardia_registrada_en_grupo_menos_uno():
    """El doble de `_turno` replica el orden de grupos de PTB; si el registro real
    cambia de grupo (o desaparece), el doble deja de ser fiel y esto lo canta."""
    src = (ROOT / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    # (dúo s316, sub-agente) Acotado a run_bot: la v1 walkeaba el MÓDULO entero y
    # pasaba con el registro en código muerto.
    run_bot = next((n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "run_bot"), None)
    assert run_bot is not None, "run_bot no existe"
    encontrada = False
    for node in ast.walk(run_bot):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", None) == "add_handler"):
            continue
        arg0 = node.args[0] if node.args else None
        if not (isinstance(arg0, ast.Call)
                and getattr(arg0.func, "id", None) == "TypeHandler"):
            continue
        if any(getattr(a, "id", None) == "brand_switch_guard" for a in arg0.args):
            # -1 llega al AST como UnaryOp(USub, Constant(1)), no como Constant(-1)
            crudo = [k.value for k in node.keywords if k.arg == "group"]
            assert crudo, "TypeHandler(brand_switch_guard) sin `group=`"
            g = crudo[0]
            valor = (-g.operand.value if isinstance(g, ast.UnaryOp)
                     else getattr(g, "value", None))
            assert valor == -1, f"la guardia está en el grupo {valor}, no en -1"
            encontrada = True
    assert encontrada, "brand_switch_guard NO está registrada como TypeHandler en run_bot"


def test_guardia_ignora_los_replies_de_feedback():
    """Un reply es feedback (#60 punto 5b), no un cambio de tema: la guardia debe
    dejarlo pasar intacto para `_capture_reply_explanation`."""
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data={
        "mt_working_state": WorkingState(last_target_models=("NC-PF2",),
                                         last_query=TURNO_A)})
    u = _update("pasemos a productos Morley", update_id=9)
    u.message.reply_to_message = SimpleNamespace(message_id=123,
                                                 chat=SimpleNamespace(id=42))
    asyncio.run(bot.brand_switch_guard(u, context))
    assert context.user_data["mt_working_state"].last_target_models == ("NC-PF2",), (
        "la guardia borró contexto en un mensaje de FEEDBACK")


def test_la_voz_tambien_invoca_la_guardia():
    """`handle_voice` NO pasa por `handle_message`, así que el TypeHandler de grupo -1
    no ve su texto: solo existe tras el ASR. La llamada explícita es el único punto que
    cubre la voz — si desaparece, un cambio de marca DICHO en voz alta no invalidaría
    contexto. Contrato de fuente (patrón `test_privacidad_esta_registrado_y_listado`):
    el doble del instrumento solo conduce texto (gap declarado)."""
    import inspect

    import src.bot.telegram_bot as bot

    cuerpo = inspect.getsource(bot.handle_voice)
    assert "_invalidar_si_cambio_de_marca" in cuerpo, (
        "handle_voice dejó de invocar la guardia: la voz queda sin cobertura de #70")
    assert cuerpo.index("_invalidar_si_cambio_de_marca") < cuerpo.index("_process_query"), (
        "la guardia debe invalidar ANTES de procesar la consulta")


def test_guardia_no_paga_db_en_el_camino_caliente(monkeypatch):
    """Sin frase de switch ni pre-gate de inventario, la guardia NO puede llamar a
    `get_available_manufacturers` (httpx síncrono paginado dentro de un handler async
    del grupo -1: 0,54 s en frío tras cada restart, en CADA mensaje)."""
    import src.bot.telegram_bot as bot

    llamadas = {"n": 0}

    def _espia():
        llamadas["n"] += 1
        return ["Morley", "Kidde"]

    monkeypatch.setattr(bot, "get_available_manufacturers", _espia)
    for q in ("¿cuál es la tensión del lazo?", "no me funciona el rearme",
              "gracias", "¿cómo silencio la sirena?"):
        bot._marca_destino(q)
    assert llamadas["n"] == 0, (
        f"la guardia pagó {llamadas['n']} llamada(s) a DB en el camino caliente")


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
