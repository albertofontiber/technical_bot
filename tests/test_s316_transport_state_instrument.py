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
    """Despacha un turno como PTB en fase B: SOLO handle_message (la guardia de
    grupo -1 se retiro; la invalidacion es la transicion del plan, aplicada por el
    escritor unico DENTRO de handle_message antes de ejecutar la ruta)."""
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


# --- TESTIGO 2 del fall-through: RETIRADO (s317b, mandato de DEC-204) --------
# Vivió aquí como xfail(strict) documentando la causa (2) de #70: «¿y en Morley
# cómo se hace el reset?» arrastraba el producto anterior. El mecanismo que lo
# arregla (lever INTENT_LLM, DEC-203→205) está EN PRODUCCIÓN desde el 12-ago
# (INTENT_LLM='on' en Railway, VERIFICADO vía API por servicio). Con flag OFF la
# conducta legacy sigue siendo el arrastre — deliberado (byte-idéntico como
# rollback) — así que el testigo ya no puede «avisar por XPASS»: su relevo vivo
# es test_lever_intent_atraviesa_el_pegamento_del_handler (flag ON ⇒ el switch
# suelta el carry y la traza lo registra) + el espejo flag-off.


# --- PEGAMENTO DEL LEVER (s316h, Sol r12 C1): flag→seam→política→traza→log ---
def test_lever_intent_atraviesa_el_pegamento_del_handler(transporte, monkeypatch):
    """El e2e real-API (scripts/s316h_intent_e2e.py) NO conduce handle_message; ESTE
    test fija el pegamento en CI: con INTENT_LLM=on, el seam se construye por su
    cableado real (constructor stubeado — el clasificador es lo ÚNICO doblado), la
    política invoca el clasificador en el fall-through, y la fila persistida vía
    log_query lleva rag_trace.intent con la decisión. La clase «el gate mide un
    camino que el serving salta» (r11) no puede volver sin poner esto en rojo."""
    import src.bot.telegram_bot as bot
    import src.orchestrator.intent_llm as intent_llm
    from src.rag.runtime_trace import validate_rag_serving_trace

    monkeypatch.setenv("INTENT_LLM", "on")
    monkeypatch.setattr(bot, "_INTENT_FN_CELL", {})
    llamadas = {"n": 0}

    def _clasificador_stub(q, ws):
        llamadas["n"] += 1
        return "switch"

    monkeypatch.setattr(intent_llm, "construir_intent_fn",
                        lambda *_a, **_k: _clasificador_stub)

    context = SimpleNamespace(user_data={})
    uA = _turno(bot, context, TURNO_A, 1)
    _sin_rama_de_error(uA, transporte, espera_generacion=True)
    # Turno A: flag ON pero la política no llegó a la rama ambigua ⇒ el seam
    # existe sin invocar y la traza lo dice (not_invoked, sin decisión fantasma).
    traza_a = transporte["logs"][-1].get("rag_trace")
    assert traza_a and traza_a["intent"] == {
        "status": "not_invoked", "decision": "none", "latency_ms": 0}

    uB = _turno(bot, context, "¿y en Morley cómo se hace el reset?", 2)
    _sin_rama_de_error(uB, transporte, espera_generacion=True)
    assert llamadas["n"] == 1, "la política no invocó el clasificador (pegamento roto)"
    # La decisión switch DEBE soltar el carry (esto es #70 etapa 2 con el flag ON;
    # el testigo XFAIL de arriba documenta que con OFF sigue arrastrando).
    assert "NC-PF2" not in transporte["generate_queries"][-1], (
        "switch del clasificador y aun así generó con el producto anterior")
    traza_b = transporte["logs"][-1].get("rag_trace")
    assert traza_b is not None, "la fila RAG no llevó rag_trace"
    assert traza_b["intent"]["status"] == "invoked"
    assert traza_b["intent"]["decision"] == "switch"
    assert isinstance(traza_b["intent"]["latency_ms"], int)
    # Y la traza que el handler construyó pasa el validador del sink tal cual.
    assert validate_rag_serving_trace(traza_b) == traza_b


def test_flag_off_la_traza_dice_off_explicito(transporte, monkeypatch):
    """Espejo $0 del pegamento: sin flag, la fila RAG lleva intent.status=off
    EXPLÍCITO (estampado por el serving), nunca not_wired — la distinción M1."""
    import src.bot.telegram_bot as bot

    monkeypatch.delenv("INTENT_LLM", raising=False)
    context = SimpleNamespace(user_data={})
    uA = _turno(bot, context, TURNO_A, 1)
    _sin_rama_de_error(uA, transporte, espera_generacion=True)
    traza = transporte["logs"][-1].get("rag_trace")
    assert traza and traza["intent"] == {
        "status": "off", "decision": "none", "latency_ms": 0}


# --- CONTROL: la guardia NO se traga un "cambio" a la MISMA marca ------------
# (dúo s316, Sol M2) La v1 de este control usaba «¿qué más centrales Kidde tienes?»,
# que NO casa `_ENUM_FABRICANTE` ⇒ `_marca_destino` devolvía None y el test quedaba
# verde SIN llegar nunca a la comparación de fabricante. Era vacuo: pasaba aunque se
# borrara la extensión de identidad. Aquí la frase SÍ resuelve destino, así que la
# única razón de no limpiar es la comparación Kidde==Kidde.
def test_control_misma_marca_ejerce_la_comparacion():
    """(Sol s316b M2 heredado) La frase DEBE resolver destino — si no, el control es
    vacuo — y la unica razon de no invalidar es la comparacion Kidde==Kidde."""
    from src.orchestrator import turn_plan as tp

    lex = ["Kidde", "Morley", "Detnov"]
    assert (tp.marca_destino("pasemos a Kidde", lex) or "").lower() == "kidde", \
        "precondicion: la frase debe resolver destino, o el control vuelve a ser vacuo"
    transicion, _ = tp._decidir_transicion("pasemos a Kidde", ("NC-PF2",),
                                           tp.Meta(), lex)
    assert transicion == tp.PRESERVAR, "invalido con la MISMA marca (NC-PF2 es Kidde)"


def test_plan_invalida_con_marca_distinta_y_reset_completo():
    """Espejo: marca DISTINTA => INVALIDAR; y el escritor unico aplica el reset
    COMPLETO (is_empty: un last_query residual haria que el turno siguiente
    contestara "Ha pasado un rato" siendo mentira)."""
    import src.bot.telegram_bot as bot
    from src.orchestrator import turn_plan as tp

    transicion, marca = tp._decidir_transicion(
        "pasemos a Morley", ("NC-PF2",), tp.Meta(), ["Kidde", "Morley"])
    assert transicion == tp.INVALIDAR and (marca or "").lower() == "morley"

    user_data = {"mt_working_state": WorkingState(last_target_models=("NC-PF2",),
                                                  last_query=TURNO_A)}
    bot._aplicar_estado(user_data, WorkingState())
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
def test_precision_el_predicado_calla(consulta):
    from src.orchestrator import turn_plan as tp
    assert tp.marca_destino(consulta, list(_MARCAS_CONGELADAS)) is None, (
        f"FALSO POSITIVO: se borraria contexto legitimo en {consulta!r}")


@pytest.mark.parametrize("consulta,esperada", _DEBEN_DISPARAR)
def test_recall_el_predicado_dispara(consulta, esperada):
    from src.orchestrator import turn_plan as tp
    got = tp.marca_destino(consulta, list(_MARCAS_CONGELADAS))
    assert (got or "").lower() == esperada.lower(), f"{consulta!r} -> {got!r}"


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
def test_un_solo_escritor_de_estado_por_ast():
    """Invariante de fase B (v3): la escritura de `mt_working_state` con clave LITERAL
    vive solo en `_aplicar_estado`. Cazado: Assign (incl. tuplas), AnnAssign, AugAssign,
    Delete, y .update()/.setdefault() con la clave como literal — en telegram_bot Y
    turn_plan. LÍMITE DECLARADO (Fable fase-B): una escritura con la clave en variable
    o un alias del dict escaparían; el invariante es el choke-point sintáctico + las
    fuentes declaradas, no una prueba total. Claves legacy RETIRADAS."""
    fuentes = [(ROOT / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8"),
               (ROOT / "src" / "orchestrator" / "turn_plan.py").read_text(encoding="utf-8")]
    src = fuentes[0]
    tree = ast.parse("\n\n".join(fuentes))
    fuera_del_escritor = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if fn.name == "_aplicar_estado":
            continue
        for n in ast.walk(fn):
            # (Sol fase-B M4) no solo Assign: tambien AnnAssign/AugAssign sobre la
            # clave, y llamadas .update()/.setdefault() que la traigan como literal.
            tgts = []
            if isinstance(n, ast.Assign):
                for tg in n.targets:            # incluye tuplas: a, ud[k] = ...
                    tgts.extend(tg.elts if isinstance(tg, ast.Tuple) else [tg])
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign)):
                tgts = [n.target]
            elif isinstance(n, ast.Delete):
                tgts = list(n.targets)
            for tgt in tgts:
                if (isinstance(tgt, ast.Subscript)
                        and isinstance(tgt.slice, ast.Constant)
                        and tgt.slice.value == "mt_working_state"):
                    fuera_del_escritor.append(fn.name)
            if (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("update", "setdefault")):
                literales = {c.value for c in ast.walk(n)
                             if isinstance(c, ast.Constant) and isinstance(c.value, str)}
                if "mt_working_state" in literales:
                    fuera_del_escritor.append(fn.name)
    assert not fuera_del_escritor, (
        f"mt_working_state se escribe fuera del escritor unico: {fuera_del_escritor}")
    assert '"last_detected_models"' not in src and "'last_detected_models'" not in src
    assert '"last_query_time"' not in src and "'last_query_time'" not in src


def test_los_replies_no_invalidan():
    """Un reply es feedback (#60 5b), no un cambio de tema. Dos capas: el predicado
    PRESERVA con es_reply (unit) y handle_message construye es_reply del
    reply_to_message real (contrato de wiring por fuente)."""
    import inspect

    import src.bot.telegram_bot as bot
    from src.orchestrator import turn_plan as tp

    transicion, _ = tp._decidir_transicion(
        "pasemos a productos Morley", ("NC-PF2",), tp.Meta(es_reply=True),
        ["Kidde", "Morley"])
    assert transicion == tp.PRESERVAR, "un reply invalido contexto"
    fuente = inspect.getsource(bot.handle_message)
    assert "es_reply=update.message.reply_to_message is not None" in fuente


def test_la_voz_tambien_invoca_la_guardia():
    """`handle_voice` NO pasa por `handle_message`, así que el TypeHandler de grupo -1
    no ve su texto: solo existe tras el ASR. La llamada explícita es el único punto que
    cubre la voz — si desaparece, un cambio de marca DICHO en voz alta no invalidaría
    contexto. Contrato de fuente (patrón `test_privacidad_esta_registrado_y_listado`):
    el doble del instrumento solo conduce texto (gap declarado)."""
    import inspect

    import src.bot.telegram_bot as bot

    cuerpo = inspect.getsource(bot.handle_voice)
    assert "_decidir_transicion" in cuerpo, (
        "handle_voice dejo de decidir la invalidacion: la voz queda sin cobertura de #70")
    assert "_aplicar_estado" in cuerpo, "la voz no aplica por el escritor unico"
    assert cuerpo.index("_decidir_transicion") < cuerpo.index("_process_query"), (
        "la invalidacion debe decidirse ANTES de procesar la consulta")


def test_camino_caliente_no_pide_lexico(monkeypatch):
    """La restriccion PAGADA de s316c, en su forma de fase B: sin frase de switch ni
    pre-gate de inventario, NI el plan pide el hecho `lexico_marcas` NI el core
    perezoso toca el proveedor (0,54 s de httpx frio por mensaje era el coste)."""
    from src.orchestrator import turn_plan as tp

    llamadas = {"n": 0}

    def _espia():
        llamadas["n"] += 1
        return ["Morley", "Kidde"]

    for q in ("¿cuál es la tensión del lazo?", "no me funciona el rearme",
              "gracias", "¿cómo silencio la sirena?"):
        necesita = tp.plan_turn_hechos(q, ("CAD-250",), tp.Meta())
        assert tp.Hecho("lexico_marcas") not in necesita, f"pidio lexico para {q!r}"
        tp.marca_destino(q, _espia)
    assert llamadas["n"] == 0, (
        f"se pagaron {llamadas['n']} llamada(s) a DB en el camino caliente")


# --- CENSO de ramas terminales (el unit del riesgo, no la ruta) --------------
# Si este censo rompe, añadiste o quitaste una rama terminal: actualiza el número Y
# decide explícitamente qué hace la rama nueva con el estado conversacional (deja el
# porqué en el commit).
#
# HISTORIA DEL CENSO — s316b: handle_message tenía 13 returns y 7 respondían sin
# log_query (la clase de rama que ES #70). s316e (fase A DEC-200): la cascada entera
# vive en turn_plan.plan_turn y las ramas terminales de RESPUESTA se concentran en el
# despachador _ejecutar_plan (8: inventario, cortesía ×3, catálogo, mismatch,
# no_servida, mismatch/feedback); handle_message conserva solo los PRE-PASOS
# declarados (vacío, consentimiento, reply-capture). Una ruta nueva ya no puede
# nacer como if suelto: nace como ruta del plan, con su decisión de log y estado.
_CENSO_RETURNS = {"handle_message": 3, "handle_voice": 3, "_ejecutar_plan": 8}


def test_ventanas_iguales_en_ambos_regimenes():
    """(v3 punto 6, Sol fase-B m6) El carry-forward stub y el de F1 miden la MISMA
    ventana: el literal local de _process_query no puede derivar de WINDOW_SECONDS."""
    import inspect
    import re as _re

    import src.bot.telegram_bot as bot
    from src.orchestrator.conversation_policy_impl import WINDOW_SECONDS

    fuente = inspect.getsource(bot._process_query)
    m = _re.search(r"SESSION_TIMEOUT = (\d+)", fuente)
    assert m, "SESSION_TIMEOUT ya no es un literal localizable: actualiza este test"
    assert int(m.group(1)) == WINDOW_SECONDS == 3600


def test_censo_ramas_terminales():
    src = (ROOT / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    visto = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef))                 and fn.name in _CENSO_RETURNS:
            visto[fn.name] = sum(isinstance(n, ast.Return) for n in ast.walk(fn))
    assert visto == _CENSO_RETURNS, (
        f"ramas terminales cambiaron: {visto} != censo {_CENSO_RETURNS}. "
        "Decide qué hace la rama nueva con mt_working_state y actualiza el censo.")
