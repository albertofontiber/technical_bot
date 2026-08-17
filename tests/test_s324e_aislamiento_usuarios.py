# -*- coding: utf-8 -*-
"""s324e — AISLAMIENTO ENTRE USUARIOS: el red line del piloto multi-DG, anclado.

RED LINE (Alberto, piloto con varios Directores Generales A LA VEZ): «cada DG tiene su
sesión del chatbot y son independientes; un usuario debe ver sólo aquello por lo que
pregunta». El feedback agregado SÍ bebe de todos — eso es agregado y está bien.

POR QUÉ ESTE FICHERO. Hoy el aislamiento descansa en dos promesas NO verificadas en la
suite: (1) que `context.user_data` de PTB está particionado por usuario, y (2) que todo
lo que vive a nivel PROCESO (cachés de módulo, la celda del clasificador de intención)
depende del CORPUS y no del técnico. Una promesa del framework no es un contrato: si
mañana alguien mete una caché con la clave equivocada, nada se pone rojo. Aquí se
convierte en contrato EJECUTABLE.

QUÉ FIJA, y contra qué pregunta del encargo responde cada bloque:

  (1) ¿Puede el contenido de la conversación de un usuario aparecer en la respuesta de
      otro? — `test_ptb_particiona_user_data_por_usuario` (el contrato del framework,
      medido sobre PTB real y offline), `test_turnos_entrelazados_no_se_cruzan` (A→B→A→B
      por `handle_message` REAL) y `test_dos_turnos_concurrentes_de_verdad_no_se_cruzan`
      (los dos turnos EN VUELO a la vez, sincronizados con una barrera en el hilo de
      generación — el aislamiento no depende de que PTB serialice).
      Más el flanco proceso: `test_censo_de_estado_de_proceso`,
      `test_cache_de_inventario_no_se_clava_al_usuario`,
      `test_celda_del_clasificador_es_compartida_pero_no_filtra` y
      `test_el_camino_servido_no_lee_fn_ultima`.

  (2) ¿Qué pasa con `user_data` en un reinicio? — `test_sin_persistencia_configurada` +
      `test_reinicio_pierde_contexto_pero_no_filtra`. NO es fuga: es PÉRDIDA de contexto,
      y la política degrada preguntando el modelo, no adivinándolo.

  (3) Concurrencia real — `test_los_updates_se_procesan_de_uno_en_uno` fija la
      configuración de HOY (PTB serializa: `max_concurrent_updates == 1`) y el test
      concurrente de arriba prueba que el aislamiento aguanta IGUAL si mañana se
      enciende. El día que alguien llame a `.concurrent_updates(...)`, el primero se
      pone rojo y obliga a decidirlo conscientemente.

  (4) Doble instancia — CERRADO en la misma sesión: `error_handler` PARA el proceso ante
      `Conflict` (409) en lugar de dejar que PTB reintente para siempre mientras Telegram
      reparte los updates. `test_hay_guarda_de_instancia_unica` pasó de testigo `xfail` a
      test vivo. Auditoría: `evals/s324e_aislamiento_usuarios_auditoria_v1.md` §P4.

REGLAS DE LOS DOBLES (mismas que `test_s316_transport_state_instrument`): $0, sin red y
sin DB. Lo que se dobla son las PRECONDICIONES (consentimiento, marcas servidas,
detección de modelos, adapters de serving); el ENRUTADO y el estado NO se tocan — son
justo lo que se está midiendo. La lista de fabricantes se congela para que el veredicto
no dependa del entorno (local con credenciales vs CI sin ellas).

NO se duplica el invariante del escritor único: vive en
`tests/test_s316_transport_state_instrument.py::test_un_solo_escritor_de_estado_por_ast`
y aquí solo se ancla que ese guardián sigue existiendo, más lo que aquel NO cubre (que
`_aplicar_estado` escribe en el dict que RECIBE y no en estado de proceso).
"""

import ast
import asyncio
import importlib
import os
import threading
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator import replay_adapters
from src.orchestrator.conversation_policy import WorkingState

ROOT = Path(__file__).resolve().parent.parent
FUENTE_BOT = ROOT / "src" / "bot" / "telegram_bot.py"

# Dos DG del piloto, cada uno con su producto. Los tokens son DISTINGUIBLES a
# propósito: cualquier cruce se ve en la aserción, no hay que inferirlo.
DG_A = 9001
DG_B = 9002
PREGUNTA_A = "¿cuáles son las especificaciones técnicas de la NC-PF2?"
PREGUNTA_B = "¿cómo se configura la CAD-250?"
SEGUIMIENTO = "¿y cuál es su consumo?"
MODELOS = ("NC-PF2", "CAD-250")

# Congelada: `_lexico_marcas_cacheado` consulta la DB viva y sin esto el resultado
# depende del entorno (misma lección que `_MARCAS_CONGELADAS` en s316).
_MARCAS = ["Notifier", "Morley", "Kidde", "Detnov", "Xtralis"]


# --- dobles de transporte (patrón s316) --------------------------------------
class _Chat:
    def __init__(self, chat_id):
        self.id = chat_id
        self.actions = []

    async def send_action(self, action):
        self.actions.append(action)


class _Message:
    def __init__(self, text, chat_id):
        self.text = text
        self.chat = _Chat(chat_id)
        self.reply_to_message = None
        self.replies = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)

    async def reply_photo(self, **_kwargs):
        pass

    async def reply_media_group(self, media, **_kwargs):
        pass


def _update(text, *, user_id, update_id):
    """Un update por DG. `chat_id == user_id`: chat privado 1:1, que es la forma
    del piloto (ver la nota sobre chats de grupo en la auditoría)."""
    return SimpleNamespace(
        message=_Message(text, user_id),
        update_id=update_id,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=user_id),
    )


_FIXTURE = [{
    "id": "chunk-1",
    "content": "Contenido tecnico del manual (corpus compartido, igual para todos).",
    "similarity": 0.93,
    "product_model": "NC-PF2",
}]


@pytest.fixture
def serving(monkeypatch):
    """Camino de serving REAL con las precondiciones dobladas. Devuelve el registro
    de lo observable: cada llamada a generación con su query servida."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.orchestrator.rewriter as rewriter
    import src.rag.retriever as retriever

    monkeypatch.setenv("CONVERSATION_POLICY", "impl")
    monkeypatch.delenv("INTENT_LLM", raising=False)

    rec = {"generate": [], "logs": []}
    monkeypatch.setattr(bot, "log_query", lambda **k: rec["logs"].append(k) or True)
    monkeypatch.setattr(bot, "has_consent", lambda _uid: True)
    monkeypatch.setattr(bot, "asegurar_seudonimo", lambda _uid: None)
    monkeypatch.setattr(bot, "stamp_answer_messages", lambda *a, **k: None)
    monkeypatch.setattr(bot, "manufacturer_in_db", lambda m: m.strip().lower() in
                        {x.lower() for x in _MARCAS})
    monkeypatch.setattr(bot, "get_available_manufacturers", lambda: list(_MARCAS))
    monkeypatch.setattr(bot, "_marcas_db_cache", None)
    # Seguro de red: el rewriter construye un cliente real de Anthropic. Ninguna
    # ruta de estos tests debería llegar (carry-forward no reescribe), pero si una
    # llegara, el test debe FALLAR ruidoso, no gastar dinero.
    monkeypatch.setattr(rewriter, "make_rewriter",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("ruta REWRITE inesperada: habría red")))

    detect = lambda q: [m for m in MODELOS if m in q]        # noqa: E731
    monkeypatch.setattr(retriever, "extract_product_models", detect)
    monkeypatch.setattr(retriever, "get_category_models", lambda _cat: [])
    monkeypatch.setattr(bot, "extract_product_models", detect)

    def _generate(query, chunks, *, available_models=None):
        rec["generate"].append(query)
        return {"answer": f"Respuesta canned para: {query}", "diagrams": []}

    monkeypatch.setattr(orch, "from_production",
                        lambda: replay_adapters(retrieved=_FIXTURE, generate=_generate))
    yield rec
    bot._marcas_db_cache = None                              # no contaminar vecinos


def _contexto():
    """Lo que PTB entrega a un handler: un `user_data` PROPIO por usuario (la
    partición la verifica `test_ptb_particiona_user_data_por_usuario`)."""
    return SimpleNamespace(user_data={})


def _turno(bot, context, texto, *, user_id, n):
    u = _update(texto, user_id=user_id, update_id=n)
    asyncio.run(bot.handle_message(u, context))
    assert u.message.replies, f"el turno {texto!r} no respondió nada"
    for r in u.message.replies:
        assert "ha ocurrido un error" not in r.lower(), \
            f"rama de error alcanzada (rojo inatribuible): {r[:90]}"
    return u


# ═══════════════════════════════════════════════════════════════════════════════
# (1) ¿Puede la conversación de un usuario aparecer en la respuesta de otro?
# ═══════════════════════════════════════════════════════════════════════════════

def test_ptb_particiona_user_data_por_usuario():
    """EL contrato del framework, MEDIDO en vez de asumido (PTB 22.x, sin red).

    `context.user_data` lo indexa PTB por `user.id`: dos DG obtienen dos dicts
    DISTINTOS, y escribir en el de uno no aparece en el del otro. Se ancla también
    el corolario que sí importa para el piloto: la clave es el USUARIO, no el chat
    — un mismo DG conserva su sesión aunque escriba desde otro chat, y dos DG en el
    mismo chat NO comparten estado.
    """
    import datetime as _dt

    from telegram import Chat, Message, Update, User
    from telegram.ext import ApplicationBuilder, CallbackContext

    app = ApplicationBuilder().token("123456:AAA-BBB_ccc").build()

    def _real_update(user_id, chat_id, n):
        usuario = User(id=user_id, first_name=f"DG{user_id}", is_bot=False)
        chat = Chat(id=chat_id, type="private")
        msg = Message(message_id=n, date=_dt.datetime.now(_dt.timezone.utc),
                      chat=chat, from_user=usuario, text="hola")
        return Update(update_id=n, message=msg)

    ctx_a = CallbackContext.from_update(_real_update(DG_A, DG_A, 1), app)
    ctx_b = CallbackContext.from_update(_real_update(DG_B, DG_B, 2), app)

    ctx_a.user_data["mt_working_state"] = "SECRETO_DE_A"
    assert ctx_a.user_data is not ctx_b.user_data
    assert ctx_b.user_data == {}, f"el DG B ve estado del A: {ctx_b.user_data}"
    assert ctx_a.chat_data is not ctx_b.chat_data
    assert set(app.user_data) == {DG_A, DG_B}, \
        "PTB dejó de indexar user_data por user.id: revisa TODO este fichero"

    # Mismo usuario, otro chat => MISMO user_data (la sesión sigue al DG).
    ctx_a_otro_chat = CallbackContext.from_update(_real_update(DG_A, 55555, 3), app)
    assert ctx_a_otro_chat.user_data is ctx_a.user_data


def test_turnos_entrelazados_no_se_cruzan(serving):
    """A→B→A→B por `handle_message` REAL: el seguimiento anafórico de cada DG se
    resuelve contra SU producto, y ni la query servida a generación ni el estado ni
    el clúster de feedback llevan nada del otro."""
    import src.bot.telegram_bot as bot

    ctx_a, ctx_b = _contexto(), _contexto()

    _turno(bot, ctx_a, PREGUNTA_A, user_id=DG_A, n=1)
    _turno(bot, ctx_b, PREGUNTA_B, user_id=DG_B, n=2)
    ua = _turno(bot, ctx_a, SEGUIMIENTO, user_id=DG_A, n=3)
    ub = _turno(bot, ctx_b, SEGUIMIENTO, user_id=DG_B, n=4)

    servidas = serving["generate"]
    assert len(servidas) == 4, f"no llegaron los 4 turnos a generación: {servidas}"

    # El carry-forward de cada DG resuelve a SU producto.
    assert "NC-PF2" in servidas[2] and "CAD-250" not in servidas[2], \
        f"el seguimiento del DG A se contaminó: {servidas[2]!r}"
    assert "CAD-250" in servidas[3] and "NC-PF2" not in servidas[3], \
        f"el seguimiento del DG B se contaminó: {servidas[3]!r}"

    # Y la RESPUESTA que cada uno recibe no contiene el producto del otro.
    assert all("CAD-250" not in r for r in ua.message.replies), ua.message.replies
    assert all("NC-PF2" not in r for r in ub.message.replies), ub.message.replies

    # Estado conversacional y clúster de feedback: cada uno el suyo.
    ws_a = ctx_a.user_data["mt_working_state"]
    ws_b = ctx_b.user_data["mt_working_state"]
    assert ws_a.last_target_models == ("NC-PF2",)
    assert ws_b.last_target_models == ("CAD-250",)
    assert ws_a is not ws_b
    assert "CAD-250" not in (ctx_a.user_data["last_response"] or "")
    assert "NC-PF2" not in (ctx_b.user_data["last_response"] or "")
    assert ctx_a.user_data["last_query_log_id"] != ctx_b.user_data["last_query_log_id"]

    # Y las filas de telemetría llevan cada una SU autor (el agregado sí bebe de
    # todos — eso es lo permitido — pero la atribución no puede mezclarse).
    rag = [f for f in serving["logs"] if f.get("source") == "text"]
    por_usuario = {f["telegram_user_id"]: f["query"] for f in rag}
    assert set(por_usuario) == {DG_A, DG_B}


def test_dos_turnos_concurrentes_de_verdad_no_se_cruzan(serving):
    """EL test que no depende de que PTB serialice: los dos turnos EN VUELO A LA VEZ.

    Una barrera dentro de `generate` retiene a los DOS hilos de `asyncio.to_thread`
    hasta que ambos han entrado — así el solapamiento está GARANTIZADO, no es una
    carrera que a veces ocurre. Si algún estado del turno viviera a nivel proceso
    (una variable de módulo escrita en caliente, un atributo de función compartido),
    aquí es donde se pisaría.
    """
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch

    barrera = threading.Barrier(2)
    fallo = {}

    def _generate(query, chunks, *, available_models=None):
        try:
            barrera.wait(timeout=20)          # ambos turnos, dentro, a la vez
        except threading.BrokenBarrierError:  # pragma: no cover — diagnóstico
            fallo["barrera"] = query
        return {"answer": f"Respuesta canned para: {query}", "diagrams": []}

    orch_from_production = lambda: replay_adapters(   # noqa: E731
        retrieved=_FIXTURE, generate=_generate)

    ctx_a, ctx_b = _contexto(), _contexto()
    ua = _update(PREGUNTA_A, user_id=DG_A, update_id=11)
    ub = _update(PREGUNTA_B, user_id=DG_B, update_id=12)

    async def _ambos():
        return await asyncio.gather(bot.handle_message(ua, ctx_a),
                                    bot.handle_message(ub, ctx_b))

    original = orch.from_production
    orch.from_production = orch_from_production
    try:
        asyncio.run(_ambos())
    finally:
        orch.from_production = original

    assert not fallo, ("los dos turnos no llegaron a generación a la vez: la prueba "
                       "de concurrencia no se ejerció")

    respuesta_a = "\n".join(ua.message.replies)
    respuesta_b = "\n".join(ub.message.replies)
    assert "NC-PF2" in respuesta_a and "CAD-250" not in respuesta_a, respuesta_a
    assert "CAD-250" in respuesta_b and "NC-PF2" not in respuesta_b, respuesta_b
    assert ctx_a.user_data["mt_working_state"].last_target_models == ("NC-PF2",)
    assert ctx_b.user_data["mt_working_state"].last_target_models == ("CAD-250",)


# ═══════════════════════════════════════════════════════════════════════════════
# Estado de PROCESO: censo cerrado + clave y valor independientes del usuario
# ═══════════════════════════════════════════════════════════════════════════════

# Estado a nivel PROCESO de `telegram_bot` (compartido por TODOS los DG). Cada
# entrada declara POR QUÉ es seguro. Si añades uno, este censo se pone rojo: decide
# entonces si su CLAVE o su VALOR dependen del usuario — si alguno lo hace, es una
# fuga entre DG, no una caché.
_CENSO_ESTADO_DE_PROCESO = {
    "_fabricantes_cache": "resumen de marcas del CORPUS (documents activos)",
    "_inventario_cache": "inventario por marca+filtros, del CATÁLOGO gobernado",
    "_inventario_falla_ts": "backoff tras un fallo de DB; un float, sin contenido",
    "_marcas_db_cache": "lista de fabricantes con documentos en la DB",
    "_INTENT_FN_CELL": "el CLIENTE del clasificador (una construcción por proceso)",
}


_MUTADORES = {"update", "setdefault", "append", "extend", "add", "pop",
              "clear", "insert", "discard", "popitem", "remove"}


def test_censo_de_estado_de_proceso():
    """Censo CERRADO del estado compartido entre DG. Cubre los dos modos de tenerlo:
    contenedores de módulo que alguien MUTA en caliente, y nombres rebindeados con
    `global`. Un literal de módulo que nadie escribe (`_CATEGORIA_PLURAL`, los textos
    de decline) es dato constante, no estado: no entra."""
    arbol = ast.parse(FUENTE_BOT.read_text(encoding="utf-8"))

    contenedores = set()
    for nodo in arbol.body:                         # SOLO ámbito de módulo
        objetivos, valor = [], None
        if isinstance(nodo, ast.Assign):
            objetivos, valor = nodo.targets, nodo.value
        elif isinstance(nodo, ast.AnnAssign) and nodo.value is not None:
            objetivos, valor = [nodo.target], nodo.value
        if valor is None:
            continue
        es_contenedor = isinstance(valor, (ast.Dict, ast.List, ast.Set,
                                           ast.DictComp, ast.ListComp, ast.SetComp))
        if isinstance(valor, ast.Call) and isinstance(valor.func, ast.Name):
            es_contenedor = es_contenedor or valor.func.id in {"dict", "list", "set"}
        if es_contenedor:
            contenedores |= {t.id for t in objetivos if isinstance(t, ast.Name)}

    # ¿Cuáles de esos contenedores se ESCRIBEN en algún sitio?
    mutados = set()
    for nodo in ast.walk(arbol):
        destinos = []
        if isinstance(nodo, ast.Assign):
            destinos = list(nodo.targets)
        elif isinstance(nodo, (ast.AugAssign, ast.AnnAssign)):
            destinos = [nodo.target]
        elif isinstance(nodo, ast.Delete):
            destinos = list(nodo.targets)
        for destino in destinos:
            if isinstance(destino, ast.Subscript) and isinstance(destino.value, ast.Name):
                mutados.add(destino.value.id)
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in _MUTADORES
                and isinstance(nodo.func.value, ast.Name)):
            mutados.add(nodo.func.value.id)

    rebindeados = {n for nodo in ast.walk(arbol) if isinstance(nodo, ast.Global)
                   for n in nodo.names}

    visto = (contenedores & mutados) | rebindeados
    esperado = set(_CENSO_ESTADO_DE_PROCESO)
    assert visto == esperado, (
        f"el estado de PROCESO del bot cambió: sobran {sorted(visto - esperado)}, "
        f"faltan {sorted(esperado - visto)}. Toda entrada nueva se comparte entre "
        "TODOS los DG del piloto: declara aquí por qué su CLAVE y su VALOR no "
        "dependen del usuario, o el red line de aislamiento se rompe en silencio.")


def test_cache_de_inventario_no_se_clava_al_usuario(monkeypatch):
    """La caché de inventario es la única de módulo con clave COMPUESTA. Se prueban
    las dos mitades: la CLAVE no lleva al usuario (dos DG preguntando lo mismo
    producen UNA entrada) y el VALOR tampoco (reciben el mismo texto). Y el filtro
    SÍ entra en la clave — sin eso, el DG que preguntó «centrales de 4 lazos» y el
    que preguntó el inventario entero se servirían la respuesta del otro."""
    import src.bot.telegram_bot as bot

    monkeypatch.setattr(bot, "_inventario_cache", {})
    monkeypatch.setattr(bot, "_inventario_agrupado", lambda _n: None)
    monkeypatch.setattr(bot, "_inventario_filtrado",
                        lambda _n, f: f"vista filtrada {sorted(f.items())}")
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda _n: [("NC-PF2", 2), ("CAD-250", 1)])

    # Mismo fabricante, dos DG distintos: UNA entrada, MISMO valor.
    r_a = bot._inventario_fabricante("Morley")
    r_b = bot._inventario_fabricante("Morley")
    assert r_a == r_b
    assert list(bot._inventario_cache) == ["morley"], bot._inventario_cache

    # El filtro forma parte de la clave: dos vistas distintas, dos entradas.
    bot._inventario_fabricante("Morley", {"lazos": 4})
    claves = set(bot._inventario_cache)
    assert len(claves) == 2, claves
    assert all("morley" in k for k in claves)
    # Ninguna clave puede contener el identificador de un DG.
    assert all(str(DG_A) not in k and str(DG_B) not in k for k in claves)


def test_celda_del_clasificador_es_compartida_pero_no_filtra(serving, monkeypatch):
    """`_INTENT_FN_CELL` es la ÚNICA pieza compartida que un turno TOCA en caliente:
    guarda el cliente del clasificador (uno por proceso, sin lock, `last-write-wins`
    declarado). Lo que se fija aquí es que lo compartido es el CLIENTE y no la
    CONVERSACIÓN: cada invocación recibe la query y el estado de SU DG, y la celda
    no gana claves por usuario."""
    import src.bot.telegram_bot as bot
    import src.orchestrator.intent_llm as intent_llm

    monkeypatch.setenv("INTENT_LLM", "on")
    monkeypatch.setattr(bot, "_INTENT_FN_CELL", {})
    vistos = []

    def _clasificador(query, ws):
        vistos.append((query, tuple(getattr(ws, "last_target_models", ()) or ())))
        return "compat"

    monkeypatch.setattr(intent_llm, "construir_intent_fn",
                        lambda *_a, **_k: _clasificador)

    ctx_a, ctx_b = _contexto(), _contexto()
    _turno(bot, ctx_a, PREGUNTA_A, user_id=DG_A, n=1)
    _turno(bot, ctx_b, PREGUNTA_B, user_id=DG_B, n=2)
    # Rama ambigua (marca sin modelo) => la política invoca al clasificador.
    ambigua = "¿y en Morley cómo se hace el reset?"
    _turno(bot, ctx_a, ambigua, user_id=DG_A, n=3)
    _turno(bot, ctx_b, ambigua, user_id=DG_B, n=4)

    assert len(vistos) == 2, f"el clasificador no se invocó una vez por DG: {vistos}"
    assert vistos[0] == (ambigua, ("NC-PF2",)), vistos[0]
    assert vistos[1] == (ambigua, ("CAD-250",)), vistos[1]
    # La celda comparte el CLIENTE, no una entrada por usuario.
    assert list(bot._INTENT_FN_CELL) == ["fn"], bot._INTENT_FN_CELL


def test_el_camino_servido_no_lee_fn_ultima():
    """`intent_llm` deja la última decisión en `fn.ultima` — un atributo de FUNCIÓN,
    o sea estado de PROCESO escrito en cada turno. Con dos DG a la vez, leerlo tras
    el resolve devolvería la decisión del otro. Se sacó del camino servido (queda
    para el gate de juicio, que es secuencial); esto lo FIJA por AST sobre todos los
    módulos que un turno atraviesa — comentarios y docstrings no cuentan."""
    servidos = [FUENTE_BOT]
    servidos += [p for p in (ROOT / "src" / "orchestrator").glob("*.py")
                 if p.name != "intent_llm.py"]          # su dueño: ahí se ESCRIBE
    servidos += list((ROOT / "src" / "rag").glob("*.py"))

    lecturas = []
    for ruta in servidos:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Attribute) and nodo.attr == "ultima"
                    and isinstance(nodo.ctx, ast.Load)):
                lecturas.append(f"{ruta.name}:{nodo.lineno}")
    assert not lecturas, (
        f"el camino servido volvió a leer `.ultima` en {lecturas}: es estado de "
        "proceso escrito por turno — con dos DG concurrentes devuelve la decisión "
        "del OTRO. La telemetría por turno es el dict `intent_obs` del handler.")


# ═══════════════════════════════════════════════════════════════════════════════
# Escritor único del estado (sin duplicar el invariante canónico)
# ═══════════════════════════════════════════════════════════════════════════════

def test_el_invariante_del_escritor_unico_sigue_vigilado():
    """NO se duplica: el invariante AST vive en s316. Aquí solo se ancla que ese
    guardián existe — si alguien lo borra, el aislamiento pierde su choke-point y
    este puntero se pone rojo."""
    modulo = importlib.import_module("tests.test_s316_transport_state_instrument")
    assert callable(getattr(modulo, "test_un_solo_escritor_de_estado_por_ast", None)), (
        "desapareció test_un_solo_escritor_de_estado_por_ast: el punto único de "
        "escritura de mt_working_state se quedó sin guardián.")


def test_el_escritor_unico_escribe_en_el_dict_que_recibe():
    """Lo que el invariante AST de s316 NO cubre: que el escritor no toque estado de
    proceso. Escribe en el dict RECIBIDO (el `user_data` del DG), no en un global ni
    en un argumento por defecto mutable — y no salpica al de al lado."""
    import inspect

    import src.bot.telegram_bot as bot

    fuente = inspect.getsource(bot._aplicar_estado)
    assert "global" not in fuente, "el escritor único tocó estado de proceso"
    assert all(p.default is inspect.Parameter.empty
               for p in inspect.signature(bot._aplicar_estado).parameters.values()), \
        "el escritor único ganó un argumento por defecto (riesgo de mutable compartido)"

    ud_a, ud_b = {}, {}
    bot._aplicar_estado(ud_a, WorkingState(last_target_models=("NC-PF2",)))
    assert ud_a["mt_working_state"].last_target_models == ("NC-PF2",)
    assert ud_b == {}, f"el escritor salpicó al user_data del otro DG: {ud_b}"


# ═══════════════════════════════════════════════════════════════════════════════
# (2) Reinicio del worker: pérdida de contexto, NO fuga
# ═══════════════════════════════════════════════════════════════════════════════

def test_sin_persistencia_configurada():
    """`run_bot` no cablea `persistence`: `user_data` es memoria PURA. Es una
    DECISIÓN (la persistencia durable está gateada por DDL/RGPD), y se ancla para
    que nadie la cambie sin querer — el día que se cablee, el estado conversacional
    de los DG pasa a estar en disco y eso es una decisión de gobernanza, no un
    detalle de implementación."""
    import inspect

    from telegram.ext import ApplicationBuilder

    import src.bot.telegram_bot as bot

    assert ".persistence(" not in inspect.getsource(bot.run_bot)
    app = ApplicationBuilder().token("123456:AAA-BBB_ccc").build()
    assert app.persistence is None


def test_reinicio_pierde_contexto_pero_no_filtra(serving):
    """Un redeploy de Railway a mitad de conversación: el proceso arranca con
    `user_data` VACÍO. Efecto exacto — el DG pierde el hilo, NO se le sirve el de
    otro: la política degrada PREGUNTANDO el modelo ($0, sin pipeline), nunca
    adivinándolo. Lo que se pierde es el carry-forward y el ancla del feedback
    espontáneo; el ancla por reply sobrevive (vive en `answer_messages`, en DB)."""
    import src.bot.telegram_bot as bot

    ctx = _contexto()
    _turno(bot, ctx, PREGUNTA_A, user_id=DG_A, n=1)
    assert ctx.user_data["mt_working_state"].last_target_models == ("NC-PF2",)

    ctx_tras_reinicio = _contexto()               # el worker volvió: memoria a cero
    antes = len(serving["generate"])
    u = _turno(bot, ctx_tras_reinicio, SEGUIMIENTO, user_id=DG_A, n=2)

    assert len(serving["generate"]) == antes, \
        "un seguimiento huérfano entró al pipeline: debe resolverse a $0"
    assert len(u.message.replies) == 1
    assert "modelo" in u.message.replies[0].lower(), u.message.replies[0]
    assert "NC-PF2" not in u.message.replies[0]
    assert ctx_tras_reinicio.user_data["mt_working_state"].last_target_models == ()


# ═══════════════════════════════════════════════════════════════════════════════
# (3) Concurrencia: la configuración de HOY, declarada
# ═══════════════════════════════════════════════════════════════════════════════

def test_los_updates_se_procesan_de_uno_en_uno():
    """CONTRATO DECLARADO, no supuesto: `run_bot` no llama a `.concurrent_updates()`,
    así que PTB usa `SimpleUpdateProcessor(max_concurrent_updates=1)` y despacha los
    updates de UNO EN UNO (`__update_fetcher` los AWAITA en vez de crear tarea).

    Consecuencia doble, y las dos importan para el piloto: (a) hoy dos turnos de dos
    DG no pueden solaparse — capa extra de aislamiento; (b) un turno RAG largo bloquea
    a los demás DG mientras dura (head-of-line). Si alguien enciende la concurrencia
    para arreglar (b), este test se pone rojo y obliga a decidirlo con los ojos
    abiertos — el aislamiento sigue probado por
    `test_dos_turnos_concurrentes_de_verdad_no_se_cruzan`, que ya corre solapado."""
    import inspect

    from telegram.ext import ApplicationBuilder

    import src.bot.telegram_bot as bot

    assert "concurrent_updates" not in inspect.getsource(bot.run_bot)
    app = ApplicationBuilder().token("123456:AAA-BBB_ccc").build()
    assert app._update_processor.max_concurrent_updates == 1


# ═══════════════════════════════════════════════════════════════════════════════
# (4) Doble instancia: TESTIGO del hueco (xfail strict)
# ═══════════════════════════════════════════════════════════════════════════════

def _hay_guarda_de_instancia_unica() -> bool:
    """¿Existe HOY alguna guarda contra una segunda instancia? Se acepta cualquiera
    de las dos formas razonables, para no prescribir el mecanismo:

      (a) reactiva — un `telegram.error.Conflict` que llega a la red global PARA la
          aplicación (`Application.stop_running`), en vez de seguir repartiendo
          updates entre las dos instancias; o
      (b) preventiva — `run_bot` invoca una guarda de arranque (lock por token en
          la DB) ANTES de `run_polling`.
    """
    import inspect

    import src.bot.telegram_bot as bot

    fuente_run_bot = inspect.getsource(bot.run_bot)
    arbol = ast.parse(fuente_run_bot.lstrip())
    llamadas_previas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            nombre = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", "")
            if nombre == "run_polling":
                break
            llamadas_previas.append(nombre.lower())
    if any(t in n for n in llamadas_previas
           for t in ("instancia", "single", "lock", "unica", "exclusi")):
        return True                                            # (b) preventiva

    from telegram.error import Conflict

    parada = {"n": 0}
    aplicacion = SimpleNamespace(stop_running=lambda: parada.__setitem__("n", 1))
    contexto = SimpleNamespace(error=Conflict("terminated by other getUpdates request"),
                               application=aplicacion, bot_data={}, user_data=None,
                               chat_data=None)
    asyncio.run(bot.error_handler(None, contexto))
    return parada["n"] == 1                                    # (a) reactiva


# (s324e, MISMA SESIÓN) El hueco se CERRÓ: `error_handler` para el proceso ante `Conflict`
# en vez de dejar que PTB reintente indefinidamente. El `xfail(strict)` que atestiguaba el
# agujero se retiró aquí — que es exactamente lo que el trinquete estricto obliga a hacer
# cuando el arreglo aterriza (un XPASS estricto es un fallo de suite a propósito).
def test_hay_guarda_de_instancia_unica():
    assert _hay_guarda_de_instancia_unica(), (
        "no hay guarda de instancia única: ni parada explícita ante Conflict ni lock "
        "de arranque. Dos instancias vivas parten la sesión de un DG en dos procesos.")
