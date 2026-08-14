# -*- coding: utf-8 -*-
"""s316e — Fase A del rediseño (DEC-200): EQUIVALENCIA por ruta de `handle_message`.

CONTRATO DE LA FASE A: la extracción de `plan_turn` es MECÁNICA — misma respuesta,
misma ruta de log, mismos efectos (typing, seudónimo), mismo fall-through. Estos tests
se escribieron ANTES del refactor y salieron VERDES contra el código de hoy: fijan la
conducta actual como espec. Si el refactor los rompe, el refactor está mal — no al revés.

Cubre las rutas del censo (v3): cortesía ×3 (sin log — promesa del aviso v7), catálogo,
mismatch, marca_no_servida (con y sin modelo), inventario (servido Y su fallback a RAG),
5-bis dinámico (Xtralis), feedback, conversacional, y los pre-pasos declarados
(consentimiento; vacío). El fallback del inventario es la parte fina: hoy cae al CHECK
de feedback y luego a RAG — no directo a RAG.
"""

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.orchestrator import replay_adapters

from test_s316_transport_state_instrument import _update  # noqa: F401 (dobles compartidos)


_FIXTURE = [{"id": "c1", "content": "La tensión del lazo es 24 V CC.",
             "similarity": 0.9, "product_model": "CAD-250"}]


@pytest.fixture
def eq(monkeypatch):
    """Dobles calibrados: Morley/Detnov/Xtralis servidas; CAD-250 es de Detnov;
    Hochiki NO servida. Registra logs, seudónimos y generación."""
    import src.bot.telegram_bot as bot
    import src.orchestrator as orch
    import src.rag.retriever as retriever

    # s319 PR-C: ORCHESTRATOR_PATH retirado — la ruta orquestador es incondicional
    monkeypatch.setenv("CONVERSATION_POLICY", "impl")

    rec = {"logs": [], "seud": [], "gen": [], "catalogo": 0, "feedback": [],
           "inventario_de": []}
    monkeypatch.setattr(bot, "log_query",
                        lambda **k: rec["logs"].append(k) or True)
    monkeypatch.setattr(bot, "has_consent", lambda _u: True)
    monkeypatch.setattr(bot, "asegurar_seudonimo", lambda u: rec["seud"].append(u))

    servidas = ["Detnov", "Morley", "Xtralis", "Notifier"]
    monkeypatch.setattr(bot, "manufacturer_in_db",
                        lambda m: m.lower() in {s.lower() for s in servidas})
    monkeypatch.setattr(bot, "get_available_manufacturers", lambda: list(servidas))
    monkeypatch.setattr(bot, "lookup_model_manufacturer",
                        lambda m: "Detnov" if m.upper() == "CAD-250" else None)
    monkeypatch.setattr(bot, "_fabricantes_resumen", lambda: ("Detnov y Morley", 2))
    # la caché global del 5-bis no debe arrastrar estado entre tests
    monkeypatch.setattr(bot, "_marcas_db_cache", None)

    async def _catalogo(update):
        rec["catalogo"] += 1
        await update.message.reply_text("CATALOGO-STUB")

    monkeypatch.setattr(bot, "_handle_catalog", _catalogo)

    inventario_respuesta = {"valor": "*Inventario stub*"}

    def _inventario(marca, filtros=None):
        # (s322 #76) el despachador pasa los filtros TIPADOS del plan; el
        # instrumento los registra para poder assertarlos por caso.
        rec["inventario_de"].append(marca)
        rec.setdefault("inventario_filtros", []).append(filtros)
        return inventario_respuesta["valor"]

    monkeypatch.setattr(bot, "_inventario_fabricante", _inventario)

    async def _feedback(update, context, q):
        rec["feedback"].append(q)
        await update.message.reply_text("FEEDBACK-STUB")

    monkeypatch.setattr(bot, "_handle_feedback", _feedback)

    det = lambda q: ["CAD-250"] if "CAD-250" in q else (  # noqa: E731
        ["XR-100"] if "XR-100" in q else [])
    monkeypatch.setattr(bot, "extract_product_models", det)
    monkeypatch.setattr(retriever, "extract_product_models", det)
    monkeypatch.setattr(retriever, "get_category_models", lambda c: [])

    def _generate(query, chunks, *, available_models=None):
        rec["gen"].append(query)
        return {"answer": "Respuesta.", "diagrams": []}

    monkeypatch.setattr(orch, "from_production",
                        lambda: replay_adapters(retrieved=_FIXTURE, generate=_generate))
    rec["inventario_respuesta"] = inventario_respuesta
    return rec


def _turno(texto, rec=None, user_data=None):
    import src.bot.telegram_bot as bot

    context = SimpleNamespace(user_data=user_data if user_data is not None else {})
    u = _update(texto)
    asyncio.run(bot.handle_message(u, context))
    return u


def _rutas(rec):
    return [l.get("route") for l in rec["logs"]]


def _atajos(rec):
    """Solo las rutas de ATAJO: los turnos RAG también loggean (dentro de
    _process_query, sin kwarg de ruta) y no cuentan como atajo."""
    return [r for r in _rutas(rec) if r is not None]


# --- cortesía: responde, NO loggea (promesa del aviso v7) ---------------------
@pytest.mark.parametrize("texto,fragmento", [
    ("hola", "¡Hola! 👋"),
    ("gracias", "De nada 👍"),
    ("adiós", "¡Hasta luego!"),
])
def test_cortesia_responde_sin_log(eq, texto, fragmento):
    u = _turno(texto)
    assert any(fragmento in r for r in u.message.replies)
    assert eq["logs"] == [] and eq["seud"] == []


def test_saludo_incluye_fabricantes_dinamicos(eq):
    u = _turno("hola")
    assert "Detnov y Morley" in u.message.replies[0]


# --- catálogo global ----------------------------------------------------------
def test_catalogo_typing_log_sin_response_y_seudonimo(eq):
    u = _turno("¿qué fabricantes tienes?")
    assert eq["catalogo"] == 1 and "CATALOGO-STUB" in u.message.replies
    assert u.message.chat.actions == ["typing"]
    assert _rutas(eq) == ["catalog_shortcut"]
    assert "response" not in eq["logs"][0]        # la métrica es consulta+ruta, sin texto
    assert eq["seud"] == [7]


# --- paso 5: modelo + marca ---------------------------------------------------
def test_mismatch_responde_con_marca_real(eq):
    u = _turno("¿el CAD-250 es de Morley?")
    assert any("El *CAD-250* es un producto de *Detnov*" in r for r in u.message.replies)
    assert _rutas(eq) == ["manufacturer_mismatch"]
    assert eq["logs"][0]["response"].startswith("El *CAD-250*")
    assert eq["seud"] == [7] and eq["gen"] == []


def test_misma_marca_cae_a_rag(eq):
    u = _turno("¿el CAD-250 de Detnov admite 8 zonas?")
    assert eq["logs"] == [] or _rutas(eq) != ["manufacturer_mismatch"]
    assert len(eq["gen"]) == 1                    # llegó a generación (conversacional)
    assert u.message.chat.actions == ["typing"]


def test_modelo_desconocido_marca_no_servida(eq):
    u = _turno("¿el XR-100 de Hochiki qué alcance tiene?")
    assert any("No dispongo de manuales de _Hochiki_" in r for r in u.message.replies)
    assert any("*Detnov*" in r for r in u.message.replies)   # lista de servidas
    assert _rutas(eq) == ["manufacturer_no_model"] and eq["gen"] == []


def test_modelo_desconocido_marca_servida_cae_a_rag(eq):
    _turno("¿el XR-100 de Morley qué alcance tiene?")
    assert _atajos(eq) == [] and len(eq["gen"]) == 1  # índice desincronizado → RAG


# --- paso 5: marca sin modelo -------------------------------------------------
def test_marca_no_servida_sin_modelo(eq):
    u = _turno("¿trabajas con equipos Hochiki?")
    assert any("No dispongo de manuales de _Hochiki_" in r for r in u.message.replies)
    assert _rutas(eq) == ["manufacturer_no_model"]


def test_inventario_servido(eq):
    u = _turno("¿qué centrales de incendios Morley tienes?")
    assert "*Inventario stub*" in u.message.replies
    assert eq["inventario_de"] == ["Morley"]
    assert _rutas(eq) == ["catalog_shortcut"]
    assert eq["logs"][0]["response"] == "*Inventario stub*"


def test_inventario_fallback_cae_a_rag_no_directo(eq):
    eq["inventario_respuesta"]["valor"] = None    # inventario indisponible → fail-open
    _turno("¿qué centrales de incendios Morley tienes?")
    assert eq["inventario_de"] == ["Morley"]      # se INTENTÓ
    assert _atajos(eq) == [] and len(eq["gen"]) == 1  # y cayó a RAG sin log de atajo


def test_marca_servida_sin_intencion_cae_a_rag(eq):
    _turno("una duda sobre Morley y el rearme del lazo")
    assert _atajos(eq) == [] and len(eq["gen"]) == 1


# --- 5-bis: marca fuera del regex, resuelta contra la DB ----------------------
def test_5bis_inventario_xtralis(eq):
    u = _turno("¿qué productos de Xtralis tienes?")
    assert "*Inventario stub*" in u.message.replies
    assert eq["inventario_de"] == ["Xtralis"]
    assert _rutas(eq) == ["catalog_shortcut"]


# --- feedback -----------------------------------------------------------------
def test_feedback_va_a_su_handler_sin_log_query(eq):
    _turno("la respuesta es incorrecta, el manual dice otra cosa")
    assert len(eq["feedback"]) == 1
    assert eq["logs"] == [] and eq["gen"] == []


# --- conversacional + pre-pasos ----------------------------------------------
def test_conversacional_typing_y_generacion(eq):
    u = _turno("¿cuál es la tensión nominal del lazo?")
    assert len(eq["gen"]) == 1
    assert u.message.chat.actions == ["typing"]


def test_sin_consentimiento_corta_antes_de_todo(eq, monkeypatch):
    import src.bot.telegram_bot as bot

    monkeypatch.setattr(bot, "has_consent", lambda _u: False)
    u = _turno("hola")
    assert len(u.message.replies) == 1 and "/accept" in u.message.replies[0]
    assert eq["logs"] == [] and eq["gen"] == []


def test_vacio_no_responde(eq):
    u = _turno("   ")
    assert u.message.replies == [] and eq["logs"] == []


# --- orden de la cascada: catálogo gana a marca -------------------------------
def test_orden_catalogo_antes_que_marca(eq):
    _turno("¿qué productos tienes de Notifier?")
    # _CATALOG_PATTERNS exige sustantivo+verbo adyacentes («productos tienes») — aquí
    # NO casa («productos tienes de…» sí casa: adyacencia se cumple) → catálogo.
    assert eq["catalogo"] == 1
    assert _rutas(eq) == ["catalog_shortcut"]


# --- (Sol r8 M3) el PLAN emite INVALIDAR sobre snapshots PRE-guardia ----------
# En fase A la guardia -1 limpia el estado ANTES de que el plan corra, así que en
# integración el plan siempre ve estado vacío y su transición es vacua (enmascarada,
# declarado en v3 §5). Estos tests alimentan el plan DIRECTAMENTE con el snapshot
# pre-guardia: son el único sitio donde la lógica portada se ejercita hasta que la
# fase B la haga load-bearing.
def test_plan_emite_invalidar_pre_guardia(eq):
    import src.bot.telegram_bot as bot
    from src.orchestrator import turn_plan as tp

    texto = "pasemos a productos Morley. ¿qué centrales de incendios Morley tienes?"
    estado = ("NC-PF2",)                     # el snapshot que la guardia habría visto
    meta = tp.Meta()
    hechos = bot._resolver_hechos(tp.plan_turn_hechos(texto, estado, meta))
    plan = tp.plan_turn(texto, estado, meta, hechos)
    assert plan.transicion == tp.INVALIDAR
    assert (plan.transicion_marca or "").lower() == "morley"


def test_plan_preserva_en_reply_pre_guardia(eq):
    import src.bot.telegram_bot as bot
    from src.orchestrator import turn_plan as tp

    texto = "pasemos a productos Morley. ¿qué centrales de incendios Morley tienes?"
    meta = tp.Meta(es_reply=True)            # un reply JAMÁS invalida (s316b, pagada)
    hechos = bot._resolver_hechos(tp.plan_turn_hechos(texto, ("NC-PF2",), meta))
    plan = tp.plan_turn(texto, ("NC-PF2",), meta, hechos)
    assert plan.transicion == tp.PRESERVAR


def test_plan_preserva_misma_marca_pre_guardia(eq):
    import src.bot.telegram_bot as bot
    from src.orchestrator import turn_plan as tp

    texto = "pasemos a Kidde"               # NC-PF2 ES Kidde (catálogo real, offline)
    meta = tp.Meta()
    hechos = bot._resolver_hechos(tp.plan_turn_hechos(texto, ("NC-PF2",), meta))
    plan = tp.plan_turn(texto, ("NC-PF2",), meta, hechos)
    assert plan.transicion == tp.PRESERVAR


# --- (Sol r8 C2) typing y log_consulta son LOAD-BEARING, no decorativos ------
def test_despachador_consulta_los_campos_del_plan(eq):
    import src.bot.telegram_bot as bot
    from src.orchestrator.turn_plan import TurnPlan

    from test_s316_transport_state_instrument import _update

    # un plan de catálogo con typing y log APAGADOS: si el despachador los
    # re-codificara por ruta (decorativos), esto loggearía y enviaría typing.
    plan = TurnPlan(ruta="catalogo", log_consulta=False, typing=False)
    u = _update("da igual el texto: el despachador no lo examina")
    context = SimpleNamespace(user_data={})
    asyncio.run(bot._ejecutar_plan(u, context, 7, "consulta", plan))
    assert eq["catalogo"] == 1               # la ruta se ejecutó
    assert u.message.chat.actions == []      # sin typing: el campo manda
    assert eq["logs"] == [] and eq["seud"] == []   # sin log: el campo manda


# --- (Sol r8) los args de un Hecho son tokens VALIDADOS, no texto libre -------
def test_hecho_rechaza_texto_libre():
    import pytest as _pytest

    from src.orchestrator.turn_plan import Hecho

    with _pytest.raises(ValueError):
        Hecho("tipo_inventado", "x")
    with _pytest.raises(ValueError):
        Hecho("marca_servida", "un texto de usuario colado como si fuera un token de marca que claramente no lo es")
    with _pytest.raises(ValueError):
        # (Sol fase-B M3) el vector REAL: frase corta que pasaba el tope de 64 chars
        Hecho("marca_servida", "pasemos a Morley")
    Hecho("marca_servida", "System Sensor")      # 2 palabras: marca legitima, pasa


# --- (Fable r-build, M2) el test de MECANICIDAD que el docstring declaraba ----
def test_resolver_hechos_es_mecanico_por_ast():
    """`_resolver_hechos` no puede examinar el texto del usuario ni tomar decisiones
    propias: solo despacha por `h.tipo` y llama a las TRES funciones declaradas del
    contrato (más la caché). Si mañana alguien le cuela un `if "pasemos" in ...` o una
    llamada nueva, esto rompe — el shell deja de ser mecánico y hay que volver al plan."""
    import ast
    import inspect

    import src.bot.telegram_bot as bot

    arbol = ast.parse(inspect.getsource(bot._resolver_hechos))
    fn = arbol.body[0]
    # (1) su única entrada es la lista de hechos — sin texto, update ni context
    assert [a.arg for a in fn.args.args] == ["necesita"]
    # (2) whitelist de llamadas: el contrato completo, y nada más
    # (fase B, Fable menor) el léxico va vía _lexico_marcas_cacheado — la ÚNICA
    # implementación del patrón cache-fetch-failopen; el resolver ya no toca
    # get_available_manufacturers directamente.
    permitidas = {"lookup_model_manufacturer", "manufacturer_in_db",
                  "_lexico_marcas_cacheado", "sorted", "bool"}
    llamadas = {n.func.id for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert llamadas <= permitidas, f"llamadas fuera del contrato: {llamadas - permitidas}"
    # (3) ningún literal de cadena que huela a lógica sobre texto de usuario: los
    # únicos strings permitidos son los TIPOS de hecho del contrato
    tipos = {"marca_de_modelo", "marca_servida", "lexico_marcas"}
    cuerpo_sin_docstring = fn.body[1:] if (
        fn.body and isinstance(fn.body[0], ast.Expr)
        and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    literales = {n.value for stmt in cuerpo_sin_docstring for n in ast.walk(stmt)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert literales <= tipos, f"strings fuera del vocabulario de hechos: {literales - tipos}"


def test_resolver_no_paga_marca_servida_si_el_modelo_resolvio(eq):
    """(Fable r-build, M1) El short-circuit histórico, ahora como dependencia DECLARADA:
    un turno modelo+marca cuyo lookup resuelve NO toca `manufacturer_in_db` — ni paga
    su roundtrip ni hereda su superficie de fallo."""
    import src.bot.telegram_bot as bot
    from src.orchestrator.turn_plan import Hecho

    toques = {"n": 0}
    real_in_db = bot.manufacturer_in_db

    def _espia(m):
        toques["n"] += 1
        return real_in_db(m)

    import pytest as _pytest
    mp = _pytest.MonkeyPatch()
    try:
        mp.setattr(bot, "manufacturer_in_db", _espia)
        hechos = bot._resolver_hechos(frozenset({
            Hecho("marca_de_modelo", "CAD-250"),      # resuelve → Detnov (stub)
            Hecho("marca_servida", "morley"),
        }))
        assert hechos[Hecho("marca_de_modelo", "CAD-250")] == "Detnov"
        assert toques["n"] == 0, "pagó manufacturer_in_db con el lookup YA resuelto"
        assert Hecho("marca_servida", "morley") not in hechos
    finally:
        mp.undo()


# --- FASE B: rollback (régimen stub) con el estado ÚNICO ----------------------
def test_rollback_stub_conserva_carry_forward(eq, monkeypatch):
    """CONVERSATION_POLICY=stub EXPLÍCITO es el rollback documentado desde s319
    PR-C (el default graduó a impl — quitar la var ya no baja al stub). Fase B
    retiró las claves legacy: el carry-forward stub lee/escribe
    `mt_working_state` vía `transicion_basica`. Este flujo A→B es el que ANTES
    quedaba muerto en silencio (crítico convergente de la ronda 6)."""
    import src.bot.telegram_bot as bot

    monkeypatch.setenv("CONVERSATION_POLICY", "stub")   # régimen stub explícito
    context = SimpleNamespace(user_data={})
    _turno("¿cuáles son las especificaciones técnicas de la CAD-250?",
           user_data=context.user_data)
    ws = context.user_data.get("mt_working_state")
    assert ws is not None and ws.last_target_models == ("CAD-250",), \
        "transicion_basica no escribió el estado único tras el turno RAG"
    assert ws.last_turn_at is not None

    # La señal OBSERVABLE del carry en el régimen legacy no es la query de generación
    # (eso fue el fix e2e de F1, deliberadamente NO retro-portado): es el paso 1c —
    # una consulta corta+vaga CLARIFICA sin contexto y va a RAG con él.
    #
    # (Fable fase-B CRÍTICO) La v1 usaba «¿tensión?», que NO está en PCI_TERMS: iba a
    # RAG con o sin contexto y el testigo daba verde SIN carry — vacuo justo en la
    # garantía que el gate invoca. Ahora: término que SÍ gatea («sirena») + CONTROL de
    # no-vacuidad (sin contexto DEBE clarificar) para que el verde sea atribuible.
    ctx_control = SimpleNamespace(user_data={})
    u_control = _turno("¿sirena?", user_data=ctx_control.user_data)
    assert any("necesito saber el modelo" in r for r in u_control.message.replies), (
        "CONTROL vacuo: la consulta vaga sin contexto no clarificó — el término no "
        "gatea el paso 1c y este testigo no probaría nada")
    assert len(eq["gen"]) == 1                     # el control NO generó

    u = _turno("¿sirena?", user_data=context.user_data)
    assert len(eq["gen"]) == 2, (
        "el carry-forward stub no arrastró: la consulta vaga clarificó en vez de "
        f"ir a RAG con el contexto ({u.message.replies!r})")
    assert not any("necesito saber el modelo" in r for r in u.message.replies)


def test_transicion_basica_reproduce_el_quirk_legacy():
    """(Fable r7 · v3 punto 6) El quirk se REPRODUCE, no se arregla: un turno RAG sin
    modelos refresca la ventana (last_turn_at) conservando los modelos previos — un
    contexto expirado puede resucitar, como en el legacy. F1 lo arregló en SU régimen;
    el rollback promete fidelidad, quirk incluido."""
    from datetime import datetime, timedelta, timezone

    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.turn_plan import transicion_basica

    hace_2h = datetime.now(timezone.utc) - timedelta(hours=2)
    expirado = WorkingState(last_target_models=("NC-PF2",), last_query="q0",
                            last_turn_at=hace_2h)
    ahora = datetime.now(timezone.utc)
    ws = transicion_basica(expirado, [], "¿seguro?", "resp", ahora)
    assert ws.last_target_models == ("NC-PF2",)      # modelos PRESERVADOS
    assert ws.last_turn_at == ahora                  # ventana REFRESCADA (el quirk)
    ws2 = transicion_basica(ws, ["CAD-250"], "q2", "r2", ahora)
    assert ws2.last_target_models == ("CAD-250",)    # con modelos: se sustituyen
