"""s324e — manejo de errores del bot: taxonomía + red de seguridad + insights.

Contratos que se fijan aquí:
  · la taxonomía clasifica por CAUSA, y los nombres nominales que usa están
    pinados contra las excepciones REALES de los CINCO orígenes que llegan al
    serving — httpx, telegram, anthropic, openai (Whisper) y voyageai (rerank,
    con nombres propios) — así que si un `pip install -U` mueve una clase, cae
    la suite y no producción;
  · lo desconocido cae en `bug` (residual honesto), nunca en «datos ausentes»;
  · cada clase dice algo DISTINTO al técnico, y solo manda reintentar cuando
    reintentar puede funcionar;
  · lo que se persiste va sin secretos: URLs, tokens y la propia consulta se
    redactan antes de tocar la base;
  · el manejador NO LANZA NUNCA — incluido el caso en que falla él mismo;
  · el registro de la red global es INCONDICIONAL (un flag no puede dejar al
    bot sin red de seguridad);
  · sin consentimiento no se guarda el texto de la consulta, ni siquiera al
    fallar.

Todo sin red: la taxonomía es pura y el resto se ejerce con dobles.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest
import telegram.error as tg_error

from src.bot import error_taxonomy as tax

REPO = Path(__file__).parent.parent


# ------------------------------------------------------- clasificación (real)


def _respuesta(status: int) -> httpx.Response:
    return httpx.Response(
        status, request=httpx.Request("POST", "https://api.anthropic.com/v1/m")
    )


@pytest.mark.parametrize(
    "exc, clase_esperada",
    [
        # --- red hacia los datos (Supabase habla REST por httpx) -------------
        (httpx.ReadTimeout("timeout"), tax.RED_DATOS),
        (httpx.ConnectError("conn refused"), tax.RED_DATOS),
        (httpx.PoolTimeout("pool"), tax.RED_DATOS),
        (httpx.RemoteProtocolError("server disconnected"), tax.RED_DATOS),
        (
            httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://x.supabase.co/rest/v1/t"),
                response=_respuesta(503),
            ),
            tax.RED_DATOS,
        ),
        # --- proveedor LLM: saturación ≠ credencial ≠ fallo real -------------
        (
            anthropic.RateLimitError("rate", response=_respuesta(429), body=None),
            tax.LLM_SATURADO,
        ),
        (
            anthropic.APIStatusError("overloaded", response=_respuesta(529),
                                     body=None),
            tax.LLM_SATURADO,
        ),
        (
            anthropic.AuthenticationError("bad key", response=_respuesta(401),
                                          body=None),
            tax.LLM_FALLO,
        ),
        (
            anthropic.InternalServerError("500", response=_respuesta(500),
                                          body=None),
            tax.LLM_FALLO,
        ),
        (
            anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com/v1/m")
            ),
            tax.LLM_FALLO,
        ),
        (
            anthropic.BadRequestError("too many tokens", response=_respuesta(400),
                                      body=None),
            tax.LLM_FALLO,
        ),
        # --- transporte de Telegram ------------------------------------------
        (tg_error.BadRequest("Message is too long"), tax.TRANSPORTE_TELEGRAM),
        (tg_error.BadRequest("Can't parse entities"), tax.TRANSPORTE_TELEGRAM),
        (tg_error.RetryAfter(5), tax.TRANSPORTE_TELEGRAM),
        (tg_error.TimedOut(), tax.TRANSPORTE_TELEGRAM),
        (tg_error.NetworkError("boom"), tax.TRANSPORTE_TELEGRAM),
        (tg_error.Forbidden("bot was blocked by the user"),
         tax.TRANSPORTE_TELEGRAM),
        (tg_error.InvalidToken(), tax.TRANSPORTE_TELEGRAM),
        # --- señal explícita --------------------------------------------------
        (tax.DatosAusentes("no hay manual para eso"), tax.DATOS_AUSENTES),
        # --- residual: defecto NUESTRO ---------------------------------------
        (KeyError("chunk_index"), tax.BUG),
        (AttributeError("'NoneType' object has no attribute 'text'"), tax.BUG),
        (TypeError("unsupported operand"), tax.BUG),
        (ValueError("bad literal"), tax.BUG),
        (ZeroDivisionError("division by zero"), tax.BUG),
        (OSError("disk full"), tax.BUG),
    ],
)
def test_clasificacion_contra_excepciones_reales(exc, clase_esperada):
    """Las excepciones son REALES, construidas con los SDK instalados: esto es
    lo que cierra el agujero de clasificar por nombre en vez de por isinstance
    (si `anthropic` renombra `RateLimitError`, este test cae)."""
    assert tax.clasificar(exc).clase == clase_esperada


def test_4xx_de_supabase_es_bug_nuestro_no_fallo_de_red():
    """Un 400/404 de PostgREST es una petición MAL FORMADA por nosotros.
    Contarlo como «fallo de red» escondería un defecto propio tras un
    transitorio — y encima le diría al técnico que reintente, que no arregla
    nada."""
    exc = httpx.HTTPStatusError(
        "bad request",
        request=httpx.Request("POST", "https://x.supabase.co/rest/v1/t"),
        response=_respuesta(400),
    )
    decision = tax.clasificar(exc)
    assert decision.clase == tax.BUG
    assert decision.reintentable is False


@pytest.mark.parametrize(
    "codigo, reintentable_esperado",
    [(400, False), (402, False), (404, False), (422, False), (409, False),
     (500, True), (502, True), (503, True)],
)
def test_un_4xx_del_proveedor_nunca_manda_reintentar(codigo, reintentable_esperado):
    """r37. El SDK lanza `APIStatusError` BASE cuando no tiene subclase para ese
    código (402, 451…), y esa base estaba en el conjunto «reintentable» POR
    NOMBRE: a un error determinista se le decía «vuelve a intentarlo». Ahora el
    código HTTP manda sobre el nombre.

    (Precisión sobre el hallazgo: `BadRequestError` 400 ya se clasificaba bien
    —tiene nombre propio y `clasificar` retorna en la primera entrada del MRO—;
    el agujero real era la base sin subclase. Se cubren ambos.)"""
    exc = anthropic.APIStatusError("x", response=_respuesta(codigo), body=None)
    decision = tax.clasificar(exc)
    assert decision.reintentable is reintentable_esperado
    assert decision.clase in (tax.LLM_FALLO, tax.LLM_SATURADO)


def test_bad_request_del_proveedor_no_manda_reintentar():
    """El caso que el dúo citó: comprobando `reintentable`, no solo la clase."""
    decision = tax.clasificar(
        anthropic.BadRequestError("too many tokens", response=_respuesta(400),
                                  body=None)
    )
    assert decision.clase == tax.LLM_FALLO
    assert decision.reintentable is False
    assert "vuelve a intentarlo" not in decision.mensaje.lower()


def test_credencial_rechazada_es_critica_y_no_reintentable():
    """Sistémico: afecta a TODOS. Mandar reintentar sería mentir."""
    decision = tax.clasificar(
        anthropic.AuthenticationError("bad key", response=_respuesta(401),
                                      body=None)
    )
    assert decision.severidad == "critico"
    assert decision.reintentable is False


def test_bot_bloqueado_no_es_entregable():
    """Si el técnico bloqueó al bot no hay a quién avisar: intentarlo solo
    genera otro error. La decisión lo dice explícitamente."""
    decision = tax.clasificar(tg_error.Forbidden("bot was blocked by the user"))
    assert decision.entregable is False
    assert tax.texto_para_usuario(decision, "abcd1234") == ""


def test_los_otros_dos_proveedores_tambien_estan_pinados():
    """r37: la guarda contra renombres cubría httpx/telegram/anthropic y dejaba
    fuera a OpenAI (Whisper, `telegram_bot.py:914`) y a Voyage (rerank por SDK,
    `rag/reranker.py:195`) — ambos EN SERVING, y `openai` además sin pin
    superior en requirements. Voyage usa nombres PROPIOS (`ServerError`,
    `ServiceUnavailableError`) que no existen en los otros SDK."""
    import openai
    import voyageai.error as ve

    casos = [
        (openai.RateLimitError("r", response=_respuesta(429), body=None),
         tax.LLM_SATURADO, True),
        (openai.AuthenticationError("a", response=_respuesta(401), body=None),
         tax.LLM_FALLO, False),
        (openai.APITimeoutError(
            request=httpx.Request("POST", "https://api.openai.com/v1/x")),
         tax.LLM_FALLO, True),
        (openai.BadRequestError("b", response=_respuesta(400), body=None),
         tax.LLM_FALLO, False),
        (ve.ServerError("boom"), tax.LLM_FALLO, True),
        (ve.ServiceUnavailableError("busy"), tax.LLM_SATURADO, True),
        (ve.RateLimitError("rl"), tax.LLM_SATURADO, True),
        (ve.AuthenticationError("auth"), tax.LLM_FALLO, False),
        # Sin nombre conocido: cae al no-reintentable de la clase, no a `bug`.
        (ve.InvalidRequestError("bad"), tax.LLM_FALLO, False),
    ]
    for exc, clase, reintentable in casos:
        decision = tax.clasificar(exc)
        assert decision.clase == clase, f"{type(exc).__name__} -> {decision.clase}"
        assert decision.reintentable is reintentable, type(exc).__name__


def test_lo_desconocido_nunca_se_disfraza_de_dato_ausente():
    """El error de diseño que se evita: mapear KeyError/TypeError a «datos
    ausentes» hace desaparecer de las métricas la única clase que exige
    arreglar código."""
    for exc in (KeyError("x"), IndexError("y"), RuntimeError("z")):
        assert tax.clasificar(exc).clase != tax.DATOS_AUSENTES
        assert tax.clasificar(exc).clase == tax.BUG


def test_clasificar_es_total_y_no_lanza():
    class Rara(Exception):
        @property
        def status_code(self):
            raise RuntimeError("accessor roto")

    assert tax.clasificar(None).clase == tax.BUG
    assert tax.clasificar(Rara()).clase == tax.BUG


def test_la_taxonomia_no_importa_ningun_sdk():
    """Hoja PURA: si importara telegram/anthropic/openai, un SDK que
    reestructure sus excepciones tumbaría el worker EN EL IMPORT — es decir, el
    mecanismo contra el silencio sería lo que apaga el bot."""
    fuente = (REPO / "src" / "bot" / "error_taxonomy.py").read_text(
        encoding="utf-8"
    )
    codigo = "\n".join(
        linea for linea in fuente.splitlines()
        if not linea.lstrip().startswith("#")
    )
    for prohibido in ("import telegram", "import anthropic", "import openai",
                      "import httpx", "import os"):
        assert not re.search(rf"^\s*{prohibido}\b", codigo, re.M), (
            f"error_taxonomy importa {prohibido!r}: deja de ser hoja pura"
        )


# --------------------------------------------------------------- los mensajes


def test_cada_clase_dice_algo_distinto():
    """El fallo que se cierra: hoy TODO error decía la misma frase."""
    mensajes = {
        clase: tax._MENSAJES[clase].mensaje for clase in tax.CLASES
    }
    assert len(set(mensajes.values())) == len(tax.CLASES), (
        f"dos clases comparten mensaje: {mensajes}"
    )


def _todas_las_decisiones() -> list[tax.Decision]:
    """TODAS las decisiones del módulo, no solo la tabla base: las variantes
    (crítica, bot bloqueado, las de Telegram, la del 5xx del proveedor) también
    llegan al técnico y también tienen que cumplir los invariantes."""
    vistas: list[tax.Decision] = []
    for valor in vars(tax).values():
        if isinstance(valor, tax.Decision):
            vistas.append(valor)
        elif isinstance(valor, dict):
            vistas.extend(v for v in valor.values() if isinstance(v, tax.Decision))
    # r37: la del 5xx del proveedor (`_LLM_NO_RESPONDE`) ya NO se construye en
    # línea dentro de `clasificar` — es constante de módulo, así que la recoge
    # el barrido de arriba. Se comprueba que sigue siendo alcanzable para que
    # nadie la devuelva a una función y se salga de los invariantes sin ruido.
    assert tax.clasificar(
        anthropic.InternalServerError("500", response=_respuesta(500), body=None)
    ) in vistas, "la decisión del 5xx no está entre las constantes del módulo"
    assert len(vistas) >= len(tax.CLASES) + 4, "faltan variantes por revisar"
    return vistas


def test_solo_manda_reintentar_cuando_reintentar_puede_funcionar():
    """Un bug determinista falla siempre igual: decirle «inténtalo de nuevo» es
    hacerle perder el tiempo al técnico. Se comprueba sobre TODAS las
    decisiones, incluidas las variantes."""
    for decision in _todas_las_decisiones():
        invita = any(
            marca in decision.mensaje.lower()
            for marca in ("repite la pregunta", "vuelve a enviarme",
                          "vuelve a intentarlo", "inténtalo de nuevo",
                          "espera unos segundos")
        )
        assert invita == decision.reintentable, (
            f"{decision.clase}/{decision.severidad}: "
            f"reintentable={decision.reintentable} pero el mensaje "
            f"{'invita' if invita else 'no invita'} a reintentar: "
            f"{decision.mensaje!r}"
        )


def test_toda_decision_entregable_tiene_mensaje_y_severidad_valida():
    for decision in _todas_las_decisiones():
        assert decision.clase in tax.CLASES
        assert decision.severidad in tax.SEVERIDADES
        assert bool(decision.mensaje.strip()) == decision.entregable, (
            f"{decision.clase}: entregable={decision.entregable} con mensaje "
            f"{decision.mensaje!r}"
        )


def test_ningun_mensaje_culpa_al_tecnico():
    for clase in tax.CLASES:
        texto = tax._MENSAJES[clase].mensaje.lower()
        for reproche in ("mal formulada", "pregunta incorrecta", "has escrito",
                         "tu culpa", "no has", "deberías haber"):
            assert reproche not in texto, f"{clase} reprocha: {texto!r}"


def test_los_mensajes_caben_en_telegram_y_van_en_plano():
    """Van sin `parse_mode`: un mensaje de error rechazado por un metacarácter
    devolvería el silencio que esto existe para cerrar."""
    for clase in tax.CLASES:
        assert len(tax.texto_para_usuario(tax._MENSAJES[clase], "ab12cd34")) < 400


def test_el_codigo_solo_aparece_donde_sirve():
    """Con código = «llama a soporte con esto». En un transitorio (espera y
    repite) un código es ruido que hace parecer roto lo que no lo está."""
    assert tax._MENSAJES[tax.BUG].con_codigo is True
    assert tax._MENSAJES[tax.RED_DATOS].con_codigo is False
    texto = tax.texto_para_usuario(tax._MENSAJES[tax.BUG], "ab12cd34")
    assert texto.endswith("ab12cd34")
    assert "ab12cd34" not in tax.texto_para_usuario(
        tax._MENSAJES[tax.RED_DATOS], "ab12cd34"
    )


def test_el_sufijo_de_etapa_se_anexa_sin_tocar_la_tabla_de_clases():
    texto = tax.texto_para_usuario(
        tax._MENSAJES[tax.BUG], "ab12cd34", "Escríbeme la pregunta."
    )
    assert texto.endswith("Escríbeme la pregunta.")
    assert "ab12cd34" in texto


def test_el_vocabulario_del_codigo_y_el_de_la_migracion_coinciden():
    """El CHECK de `bot_errors` y `CLASES` son el MISMO vocabulario: si divergen,
    la base rechaza filas en producción y el error se pierde justo cuando más
    falta hace."""
    sql = (REPO / "migrations" / "015_bot_errores.sql").read_text(
        encoding="utf-8"
    )
    bloque = sql.split("clase TEXT NOT NULL CHECK (clase IN (", 1)[1].split("))", 1)[0]
    en_sql = set(re.findall(r"'([a-z_]+)'", bloque))
    assert en_sql == set(tax.CLASES), (
        f"CHECK de la migración {sorted(en_sql)} ≠ CLASES {sorted(tax.CLASES)}"
    )
    severidades = sql.split("severidad TEXT NOT NULL CHECK (severidad IN (", 1)[1]
    assert set(re.findall(r"'([a-z]+)'", severidades.split("))", 1)[0])) == set(
        tax.SEVERIDADES
    )


# ---------------------------------------------------------------- redacción


def test_redaccion_quita_el_token_del_bot():
    """El riesgo que s286 citó para prohibir `str(exc)` en las filas de error:
    una URL de la API de Telegram lleva el token del bot dentro."""
    crudo = (
        "HTTPStatusError: 401 for url "
        "https://api.telegram.org/bot123456789:AAH8kQ2zLmN0pQrStUvWxYz1234567890abc/sendMessage"
    )
    limpio = tax.redactar(crudo)
    assert "api.telegram.org" not in limpio
    assert "AAH8kQ2zLmN0pQrStUvWxYz" not in limpio
    assert "[url]" in limpio


def test_redaccion_quita_claves_e_identificadores_largos():
    limpio = tax.redactar(
        "invalid api key sk-ant-api03-QQQQWWWWEEEERRRRTTTTYYYY for user 987654321"
    )
    assert "sk-ant-api03" not in limpio
    assert "987654321" not in limpio
    assert "[token]" in limpio and "[num]" in limpio


def test_redaccion_descarta_el_mensaje_si_reproduce_la_consulta():
    """Un `ValueError` que hace eco de la entrada metería el texto libre del
    técnico en una columna que no está pensada para él. No se recorta: se tira."""
    consulta = "cuantos lazos admite la central CAD-250 de Detnov"
    limpio = tax.redactar(f"ValueError: no puedo procesar {consulta}",
                          prohibido=consulta)
    assert "CAD-250" not in limpio
    assert "omitido" in limpio


def test_redaccion_admite_VARIOS_textos_prohibidos():
    """r37: en voz conviven la transcripción CRUDA y la normalizada, y la
    excepción puede hacer eco de cualquiera. Comprobar solo una dejaba la otra
    sin defensa."""
    crudo = "cuantos lazos admite la ce a de dos cincuenta"
    normalizado = "cuantos lazos admite la CAD-250"
    for eco in (crudo, normalizado):
        limpio = tax.redactar(f"ValueError: {eco}", prohibido=[crudo, normalizado])
        assert "omitido" in limpio, f"no se detectó el eco de {eco!r}"


def test_redaccion_no_se_dispara_por_una_palabra_suelta():
    """Un umbral corto haría desaparecer mensajes útiles por una coincidencia
    casual (un modelo de equipo que aparece en ambos textos)."""
    limpio = tax.redactar("KeyError: pagina", prohibido="CAD-250")
    assert limpio == "KeyError: pagina"


def test_redaccion_trunca_y_normaliza():
    limpio = tax.redactar("a" * 5 + "\n\n   " + "b" * 5000)
    assert len(limpio) <= tax.MAX_MENSAJE
    assert "\n" not in limpio


def test_redaccion_tolera_una_excepcion_ilegible():
    class Ilegible(Exception):
        def __str__(self):
            raise RuntimeError("ni str funciona")

    assert tax.redactar(Ilegible()) == "(mensaje ilegible)"


# ------------------------------------------------------------------- origen


def _excepcion_desde(ruta: str, linea: int = 3) -> BaseException:
    """Excepción cuyo traceback pasa por un frame con `ruta` como fichero.

    Se compila código con ese nombre de fichero en vez de tocar `src/`: así el
    test ejercita la lógica de rutas REAL (absoluta con separadores de Windows,
    recorte desde el ancla) sin depender del modo de fallo de otro módulo.
    """
    codigo = compile("\n" * (linea - 1) + "raise KeyError('chunk_index')",
                     ruta, "exec")
    try:
        exec(codigo, {})
    except KeyError as exc:
        return exc
    raise AssertionError("el código compilado no lanzó")


def test_origen_es_el_frame_nuestro_mas_profundo_y_relativo():
    """La ruta ABSOLUTA lleva el directorio de usuario del worker (dato
    personal) y los frames de librería son ruido para agrupar por módulo."""
    exc = _excepcion_desde(r"C:\dev\technical_bot\src\rag\generator.py", 939)
    origen = tax.origen(exc)
    assert origen == "src/rag/generator.py:939"
    assert "Users" not in origen and "dev" not in origen


def test_origen_ignora_los_frames_de_libreria():
    """Si el fallo nace entero fuera de nuestro código no se inventa un origen:
    `(sin origen)` es una respuesta honesta y agrupable."""
    exc = _excepcion_desde(
        r"C:\Users\Admin\AppData\Local\site-packages\httpx\_client.py", 12
    )
    assert tax.origen(exc) is None


def test_origen_se_queda_con_el_ancla_mas_a_la_derecha():
    """Un checkout dentro de una carpeta llamada `src` no debe truncar la ruta
    por el ancla equivocada."""
    exc = _excepcion_desde("/home/src/proyecto/src/logging_db.py", 210)
    assert tax.origen(exc) == "src/logging_db.py:210"


def test_origen_de_una_excepcion_sin_traza_es_none():
    assert tax.origen(KeyError("nunca lanzada")) is None
    assert tax.origen(None) is None


def test_describir_es_total():
    try:
        raise httpx.ReadTimeout("boom")
    except httpx.ReadTimeout as exc:
        inc = tax.describir(exc, etapa="process_query", consulta="hola")
    assert inc.clase == tax.RED_DATOS
    assert inc.tipo_excepcion == "ReadTimeout"
    assert inc.etapa == "process_query"
    assert len(inc.codigo) == 8
    inc_vacia = tax.describir(None, etapa="")
    assert inc_vacia.clase == tax.BUG and inc_vacia.etapa == "desconocida"


# ---------------------------------------------------------- el handler del bot


@pytest.fixture()
def bot_module():
    import src.bot.telegram_bot as bot

    return bot


def _update_falso(texto: str | None = "cuantos lazos tiene la CAD-250",
                  fallo_al_responder: Exception | None = None):
    """Doble de `Update` con lo justo: autor, mensaje y envío instrumentado."""
    enviados: list[str] = []

    async def _reply_text(texto_enviado, **kwargs):
        if fallo_al_responder is not None:
            raise fallo_al_responder
        enviados.append(texto_enviado)
        return MagicMock(message_id=1)

    update = MagicMock()
    update.effective_user.id = 4242
    update.effective_message.reply_text = _reply_text
    update.effective_message.text = texto
    # Explícito: un MagicMock inventa cualquier atributo, y `callback_query`
    # auto-creado (truthy) haría pasar por callback a un mensaje normal.
    update.callback_query = None
    return update, enviados


@pytest.fixture()
def bot_aislado(bot_module, monkeypatch):
    """Bot con la persistencia y el consentimiento bajo control, flags ON."""
    escrituras: dict[str, list] = {"query": [], "error": []}
    monkeypatch.setenv("BOT_ERROR_LOGGING", "on")
    monkeypatch.setenv("BOT_ERROR_REPLY", "on")
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: True)
    monkeypatch.setattr(
        bot_module, "log_query",
        lambda **kw: escrituras["query"].append(kw) or True,
    )
    monkeypatch.setattr(
        bot_module, "log_bot_error",
        lambda **kw: escrituras["error"].append(kw) or True,
    )
    return bot_module, escrituras


def test_el_tecnico_recibe_un_mensaje_de_la_clase_correcta(bot_aislado):
    bot, _ = bot_aislado
    update, enviados = _update_falso()
    asyncio.run(
        bot._reportar_error(update, httpx.ReadTimeout("x"), etapa="process_query")
    )
    assert len(enviados) == 1
    assert enviados[0] == tax._MENSAJES[tax.RED_DATOS].mensaje


def test_un_bug_y_un_timeout_no_dicen_lo_mismo(bot_aislado):
    """La regresión que este trabajo repara: el mensaje genérico único."""
    bot, _ = bot_aislado
    u1, e1 = _update_falso()
    u2, e2 = _update_falso()
    asyncio.run(bot._reportar_error(u1, httpx.ReadTimeout("x"), etapa="p"))
    asyncio.run(bot._reportar_error(u2, KeyError("y"), etapa="p"))
    assert e1[0] != e2[0]


def test_la_incidencia_se_persiste_con_lo_necesario_para_aprender(bot_aislado):
    bot, escrituras = bot_aislado
    update, _ = _update_falso()
    exc = _excepcion_desde(r"C:\dev\technical_bot\src\rag\generator.py", 939)
    codigo = asyncio.run(
        bot._reportar_error(update, exc, etapa="process_query",
                            query="cuantos lazos tiene la CAD-250")
    )
    fila = escrituras["error"][0]
    assert fila["codigo"] == codigo
    assert fila["clase"] == tax.BUG
    assert fila["severidad"] == "grave"
    assert fila["tipo_excepcion"] == "KeyError"
    assert fila["etapa"] == "process_query"
    assert fila["origen"] == "src/rag/generator.py:939"
    assert fila["usuario_avisado"] is True
    assert fila["reintentable"] is False
    # La CONSULTA no viaja en la incidencia: va en la fila padre gobernada.
    assert "query" not in fila and "telegram_user_id" not in fila
    padre = escrituras["query"][0]
    assert padre["source"] == "error"
    assert padre["query"] == "cuantos lazos tiene la CAD-250"
    assert padre["telegram_user_id"] == 4242
    assert fila["query_log_id"] == padre["query_log_id"]


def test_la_transcripcion_no_se_cuela_en_el_registro(bot_aislado):
    """r37, CRÍTICO de privacidad. `handle_voice` llamaba a `_reportar_error`
    SIN `query`, así que `redactar` corría con `prohibido=None` y la defensa
    contra eco no se ejecutaba: una excepción que arrastrase la transcripción
    la guardaba en `mensaje_corto` y además con `query_log_id=NULL` — fuera del
    CASCADE y de cualquier supresión atribuible."""
    bot, escrituras = bot_aislado
    transcripcion = "revisar la central de la obra de Fulano en Aranjuez"
    normalizada = "revisar la central de la obra de Fulano en ARANJUEZ-1"
    update, _ = _update_falso()
    asyncio.run(
        bot._reportar_error(
            update, ValueError(f"no puedo procesar {transcripcion}"),
            etapa="handle_voice", query=[transcripcion, normalizada],
        )
    )
    fila = escrituras["error"][0]
    assert transcripcion not in (fila["mensaje_corto"] or "")
    assert "Fulano" not in (fila["mensaje_corto"] or "")
    assert "omitido" in fila["mensaje_corto"]
    # Y la incidencia queda ENLAZADA: es lo que la mete en el CASCADE.
    assert fila["query_log_id"] is not None
    # Lo canónico guardado es la forma MÁS PROCESADA (la última conocida).
    assert escrituras["query"][0]["query"] == normalizada


def test_el_reporte_acepta_texto_suelto_o_secuencia(bot_aislado):
    bot, escrituras = bot_aislado
    update, _ = _update_falso()
    asyncio.run(bot._reportar_error(update, KeyError("x"), etapa="g",
                                    query="una sola cadena"))
    assert escrituras["query"][0]["query"] == "una sola cadena"


def test_normalizar_consulta_es_total():
    import src.bot.telegram_bot as bot

    assert bot._normalizar_consulta(None) == (None, ())
    assert bot._normalizar_consulta("  hola  ") == ("hola", ("hola",))
    assert bot._normalizar_consulta("") == (None, ())
    assert bot._normalizar_consulta(["a", "", None, "b"]) == ("b", ("a", "b"))
    assert bot._normalizar_consulta([]) == (None, ())
    assert bot._normalizar_consulta(42) == (None, ())      # ni siquiera iterable


def test_sin_consentimiento_no_se_guarda_la_consulta(bot_module, monkeypatch):
    """La red global alcanza `/start` de quien AÚN NO ha aceptado: sin este
    gate sería la primera vía del bot para escribir su texto."""
    escrituras: dict[str, list] = {"query": [], "error": []}
    monkeypatch.setenv("BOT_ERROR_LOGGING", "on")
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: False)
    monkeypatch.setattr(
        bot_module, "log_query", lambda **kw: escrituras["query"].append(kw) or True
    )
    monkeypatch.setattr(
        bot_module, "log_bot_error",
        lambda **kw: escrituras["error"].append(kw) or True,
    )
    update, _ = _update_falso()
    asyncio.run(
        bot_module._reportar_error(update, KeyError("x"), etapa="global",
                                   query="mi pregunta con datos")
    )
    assert escrituras["query"] == []                     # nada personal escrito
    assert len(escrituras["error"]) == 1                 # pero el fallo se cuenta
    assert escrituras["error"][0]["query_log_id"] is None


def test_si_la_fila_padre_no_se_confirma_la_incidencia_va_suelta(
    bot_module, monkeypatch
):
    """Una FK colgante rompe el borrado RGPD; perder el enlace no. Misma
    política que el teclado de feedback (s286)."""
    filas: list = []
    monkeypatch.setenv("BOT_ERROR_LOGGING", "on")
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: True)
    monkeypatch.setattr(bot_module, "log_query", lambda **kw: False)
    monkeypatch.setattr(bot_module, "log_bot_error",
                        lambda **kw: filas.append(kw) or True)
    update, _ = _update_falso()
    asyncio.run(
        bot_module._reportar_error(update, KeyError("x"), etapa="global",
                                   query="una pregunta")
    )
    assert filas[0]["query_log_id"] is None


def test_usuario_avisado_es_falso_si_el_envio_falla(bot_aislado):
    """La métrica del piloto: `usuario_avisado=False` es exactamente el
    silencio que hay que perseguir."""
    bot, escrituras = bot_aislado
    update, _ = _update_falso(fallo_al_responder=tg_error.TimedOut())
    asyncio.run(bot._reportar_error(update, KeyError("x"), etapa="global"))
    assert escrituras["error"][0]["usuario_avisado"] is False


def test_al_bot_bloqueado_no_se_le_intenta_escribir(bot_aislado):
    bot, escrituras = bot_aislado
    update, enviados = _update_falso()
    asyncio.run(
        bot._reportar_error(update, tg_error.Forbidden("blocked"), etapa="global")
    )
    assert enviados == []
    assert escrituras["error"][0]["usuario_avisado"] is False


# ---------------------------------------- el manejador de errores NO puede caer


def test_el_manejador_no_lanza_si_falla_el_envio(bot_aislado):
    bot, _ = bot_aislado
    update, _ = _update_falso(fallo_al_responder=RuntimeError("transporte roto"))
    codigo = asyncio.run(bot._reportar_error(update, KeyError("x"), etapa="g"))
    assert len(codigo) == 8


def test_el_manejador_no_lanza_si_falla_la_persistencia(bot_module, monkeypatch):
    monkeypatch.setenv("BOT_ERROR_LOGGING", "on")
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: True)

    def _explota(**kw):
        raise ConnectionError("supabase caido")

    monkeypatch.setattr(bot_module, "log_query", _explota)
    monkeypatch.setattr(bot_module, "log_bot_error", _explota)
    update, enviados = _update_falso()
    asyncio.run(bot_module._reportar_error(update, KeyError("x"), etapa="g"))
    assert len(enviados) == 1          # y el técnico SÍ recibió su mensaje


def test_el_registro_no_bloquea_el_bucle_de_eventos(bot_aislado, monkeypatch):
    """Escenario que más importa: Supabase caído ⇒ TODOS los turnos fallan. Si
    el registro (hasta 3 peticiones × 10 s de timeout) corriera en el bucle, el
    bot quedaría mudo para todos mientras registra el error de uno."""
    bot, _ = bot_aislado
    hilos: list = []
    import threading

    def _anota(**kw):
        hilos.append(threading.current_thread().name)
        return True

    monkeypatch.setattr(bot, "log_bot_error", _anota)
    monkeypatch.setattr(bot, "log_query", _anota)

    async def _escenario():
        update, _ = _update_falso()
        await bot._reportar_error(update, KeyError("x"), etapa="g",
                                  query="una pregunta")
        return threading.current_thread().name

    principal = asyncio.run(_escenario())
    assert hilos and all(h != principal for h in hilos), (
        f"el registro corrió en el hilo del bucle ({principal})"
    )


def test_el_manejador_no_lanza_si_falla_el_manejador(bot_module, monkeypatch):
    """El caso límite: revienta la propia clasificación. Un manejador de errores
    que puede caer no es un manejador de errores — en PTB una excepción escapada
    de aquí devuelve al técnico al silencio."""
    def _explota(*a, **kw):
        raise RuntimeError("la taxonomia se rompio")

    monkeypatch.setattr(bot_module.error_taxonomy, "clasificar", _explota)
    update, _ = _update_falso()
    codigo = asyncio.run(bot_module._reportar_error(update, KeyError("x"),
                                                    etapa="g"))
    assert codigo == "????????"        # degradado, pero SIN propagar


def test_el_manejador_tolera_un_update_que_no_es_update(bot_aislado):
    """PTB entrega al error handler el objeto que provocó el fallo, y no
    siempre es un `Update` (p. ej. un job de la JobQueue)."""
    bot, escrituras = bot_aislado
    asyncio.run(bot._reportar_error(object(), KeyError("x"), etapa="job"))
    assert escrituras["error"][0]["usuario_avisado"] is False


def test_el_error_handler_global_extrae_la_consulta_del_update(bot_aislado):
    bot, escrituras = bot_aislado
    update, enviados = _update_falso(texto="  pregunta con espacios  ")
    context = MagicMock()
    context.error = KeyError("x")
    asyncio.run(bot.error_handler(update, context))
    assert escrituras["query"][0]["query"] == "pregunta con espacios"
    assert len(enviados) == 1


def test_en_un_callback_no_se_confunde_el_mensaje_del_bot_con_una_consulta(
    bot_aislado
):
    """En una pulsación de 👍/👎, `effective_message` es el mensaje del PROPIO
    BOT. Tomarlo como consulta llenaría el top-5 de «preguntas que fallan» con
    texto nuestro — y guardaría en `query_logs.query` algo que nadie escribió."""
    bot, escrituras = bot_aislado
    update, _ = _update_falso(texto="La CAD-250 admite hasta 2 lazos. [fuente]")
    update.callback_query = MagicMock()
    context = MagicMock()
    context.error = KeyError("x")
    asyncio.run(bot.error_handler(update, context))
    assert escrituras["query"] == []
    assert escrituras["error"][0]["query_log_id"] is None


def test_el_conflict_se_registra_ANTES_de_parar(bot_aislado):
    """r37: el `Conflict` retornaba antes del punto único, así que el fallo más
    grave que el bot sabe detectar era el único invisible en los insights."""
    bot, escrituras = bot_aislado
    update, _ = _update_falso()
    parados: list = []
    context = MagicMock()
    context.error = tg_error.Conflict("terminated by other getUpdates request")
    context.application.stop_running = lambda: parados.append(True)
    asyncio.run(bot.error_handler(update, context))
    assert parados == [True], "la instancia NO paró"
    fila = escrituras["error"][0]
    assert fila["clase"] == tax.TRANSPORTE_TELEGRAM
    assert fila["severidad"] == "critico"
    assert fila["etapa"] == "conflict_instancia"


def test_el_conflict_para_aunque_el_registro_reviente(bot_module, monkeypatch):
    """El registro no puede impedir la parada: si Supabase se cuelga, la
    instancia duplicada tiene que morir igual o las sesiones siguen partidas."""
    monkeypatch.setenv("BOT_ERROR_LOGGING", "on")
    monkeypatch.setattr(bot_module, "has_consent", lambda uid: True)

    async def _revienta(*a, **kw):
        raise RuntimeError("registro roto")

    monkeypatch.setattr(bot_module, "_reportar_error", _revienta)
    parados: list = []
    update, _ = _update_falso()
    context = MagicMock()
    context.error = tg_error.Conflict("terminated by other getUpdates request")
    context.application.stop_running = lambda: parados.append(True)
    with pytest.raises(RuntimeError):
        asyncio.run(bot_module.error_handler(update, context))
    assert parados == [True], "el fallo del registro impidió la parada"


def test_el_error_handler_global_sin_excepcion_no_cae(bot_aislado):
    bot, escrituras = bot_aislado
    update, _ = _update_falso()
    context = MagicMock()
    context.error = None
    asyncio.run(bot.error_handler(update, context))
    assert escrituras["error"][0]["clase"] == tax.BUG


# ------------------------------------------------------------------- cableado


def test_la_red_global_esta_registrada_e_incondicional():
    """Una red de seguridad detrás de un flag no es una red de seguridad: la
    conducta que sustituye es el SILENCIO. Mismo criterio (y misma guarda) que
    el CallbackQueryHandler de s286."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    assert "app.add_error_handler(error_handler)" in fuente
    cuerpo = fuente[fuente.index("def run_bot"):]
    linea = next(
        l for l in cuerpo.splitlines() if "add_error_handler" in l
    )
    assert linea.startswith("    app.add_error_handler("), (
        "el registro está anidado (¿dentro de un if?): debe ser incondicional"
    )


def test_los_dos_flags_tienen_el_default_que_les_toca(bot_module, monkeypatch):
    monkeypatch.delenv("BOT_ERROR_LOGGING", raising=False)
    monkeypatch.delenv("BOT_ERROR_REPLY", raising=False)
    # El registro nace OFF (escribe datos); el aviso nace ON (sustituye silencio).
    assert bot_module._error_logging_enabled() is False
    assert bot_module._error_reply_enabled() is True
    monkeypatch.setenv("BOT_ERROR_REPLY", "off")
    assert bot_module._error_reply_enabled() is False


def test_con_el_kill_switch_apagado_no_se_avisa_pero_si_se_registra(
    bot_aislado, monkeypatch
):
    bot, escrituras = bot_aislado
    monkeypatch.setenv("BOT_ERROR_REPLY", "off")
    update, enviados = _update_falso()
    asyncio.run(bot._reportar_error(update, KeyError("x"), etapa="g"))
    assert enviados == []
    assert escrituras["error"][0]["usuario_avisado"] is False


def test_la_consulta_sigue_sin_ir_al_log_del_proceso(bot_aislado, caplog):
    """s295 sigue vigente con el mecanismo nuevo: los logs de Railway están
    fuera de la matriz de retención y de cualquier supresión a petición."""
    bot, _ = bot_aislado
    update, _ = _update_falso()
    secreto = "instalacion de la obra de Fulano en Aranjuez"
    with caplog.at_level("WARNING"):
        asyncio.run(
            bot._reportar_error(update, KeyError("x"), etapa="g", query=secreto)
        )
    assert secreto not in caplog.text
    assert "len_q=%d" in "".join(r.msg for r in caplog.records if isinstance(r.msg, str)) \
        or "len_q" in caplog.text


def test_la_ruta_de_voz_ya_no_escribe_la_excepcion_cruda_en_el_log():
    """Regresión de s324e: `logger.error(f"...: {e}")` metía el texto crudo de
    la excepción (que puede arrastrar la transcripción) en el log del worker."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    assert 'logger.error(f"Error processing voice message: {e}")' not in fuente
    assert 'etapa="handle_voice"' in fuente


# ------------------------------------------------------- persistencia (REST)


class _RespuestaFalsa:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class _ClienteFalso:
    """Doble del `httpx.Client` que el shim de `http_pool` construye con
    HTTP_POOL=off (lo fija `conftest.py` para toda la suite)."""

    def __init__(self, respuesta: _RespuestaFalsa, revienta: bool = False):
        self.respuesta = respuesta
        self.revienta = revienta
        self.llamadas: list[dict] = []

    def __call__(self, *a, **kw):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None, params=None):
        if self.revienta:
            raise ConnectionError("boom")
        self.llamadas.append({"url": url, "json": json, "headers": headers})
        return self.respuesta


@pytest.fixture()
def logging_db():
    import src.logging_db as modulo

    modulo._bot_errors_missing_warning_emitted = False
    return modulo


def _campos():
    return {
        "codigo": "ab12cd34",
        "clase": "bug",
        "severidad": "grave",
        "tipo_excepcion": "KeyError",
        "etapa": "process_query",
        "origen": "src/rag/generator.py:939",
        "mensaje_corto": "KeyError: chunk_index",
        "usuario_avisado": True,
        "reintentable": False,
    }


def test_log_bot_error_escribe_en_bot_errors(logging_db, monkeypatch):
    fake = _ClienteFalso(_RespuestaFalsa(201))
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert logging_db.log_bot_error(**_campos(), query_log_id="uuid-1") is True
    fila = fake.llamadas[0]
    assert fila["url"].endswith("/rest/v1/bot_errors")
    # INVARIANTE del diseño: esta tabla NO recibe dato personal.
    assert "telegram_user_id" not in fila["json"]
    assert "query" not in fila["json"]
    assert fila["json"]["query_log_id"] == "uuid-1"


def test_log_bot_error_omite_el_enlace_cuando_no_lo_hay(logging_db, monkeypatch):
    fake = _ClienteFalso(_RespuestaFalsa(201))
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert logging_db.log_bot_error(**_campos()) is True
    assert "query_log_id" not in fake.llamadas[0]["json"]


def test_tabla_ausente_degrada_y_avisa_una_sola_vez(logging_db, monkeypatch,
                                                    caplog):
    """`main` auto-despliega y las migraciones las aplica Alberto a mano: la
    tabla ausente es un estado ESPERADO (precedente: `rag_trace` faltó desde
    julio). Debe degradar sin ruido repetido, no romper."""
    fake = _ClienteFalso(
        _RespuestaFalsa(404, {"code": "PGRST205",
                              "message": "Could not find the table"})
    )
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    with caplog.at_level("WARNING"):
        assert logging_db.log_bot_error(**_campos()) is False
        assert logging_db.log_bot_error(**_campos()) is False
    assert caplog.text.count("migrations/015_bot_errores.sql") == 1


def test_un_400_de_verdad_no_se_confunde_con_tabla_ausente(logging_db,
                                                           monkeypatch, caplog):
    """Un rechazo por CHECK (clase fuera del vocabulario) es un defecto del
    emisor y debe verse, no colarse como «falta la migración»."""
    fake = _ClienteFalso(
        _RespuestaFalsa(400, {"code": "23514", "message": "check constraint"})
    )
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    with caplog.at_level("WARNING"):
        assert logging_db.log_bot_error(**_campos()) is False
    assert "migrations/015" not in caplog.text
    assert "Failed to log bot error: 400" in caplog.text


def test_log_bot_error_es_fail_open_ante_un_fallo_de_transporte(logging_db,
                                                                monkeypatch):
    fake = _ClienteFalso(_RespuestaFalsa(201), revienta=True)
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    assert logging_db.log_bot_error(**_campos()) is False


def test_log_bot_error_no_vuelca_el_cuerpo_de_la_respuesta(logging_db,
                                                           monkeypatch, caplog):
    """Esta ruta corre justo cuando algo ya ha ido mal: no es el momento de
    ampliar lo que se escribe (el cuerpo de PostgREST reproduce la fila)."""
    fake = _ClienteFalso(_RespuestaFalsa(500, {"message": "detalle sensible"}))
    monkeypatch.setattr(logging_db.httpx, "Client", fake)
    with caplog.at_level("WARNING"):
        logging_db.log_bot_error(**_campos())
    assert "detalle sensible" not in caplog.text


# ------------------------------------------------------------------- insights


def _inc(**kw):
    base = {
        "codigo": "ab12cd34",
        "clase": "bug",
        "severidad": "grave",
        "reintentable": False,
        "tipo_excepcion": "KeyError",
        "etapa": "process_query",
        "origen": "src/rag/generator.py:939",
        "mensaje_corto": "KeyError: chunk_index",
        "usuario_avisado": True,
        "bot_version": "abc1234",
        "created_at": "2026-08-17T10:00:00Z",
        "query_logs": {"query": "cuantos lazos tiene la CAD-250",
                       "telegram_user_id": 7},
    }
    base.update(kw)
    return base


def test_insights_con_la_tabla_vacia_no_revienta():
    """Requisito explícito: debe funcionar aunque no haya ni una fila."""
    from scripts.s324e_bot_errores_insights import agregar

    resumen = agregar([], [], top=5)
    assert resumen["n_incidencias"] == 0
    assert resumen["top_preguntas"] == []
    assert resumen["por_clase"] == {}


def test_insights_agrupa_por_clase_modulo_y_dia():
    from scripts.s324e_bot_errores_insights import agregar

    filas = [
        _inc(),
        _inc(clase="red_datos", origen="src/logging_db.py:210",
             created_at="2026-08-16T09:00:00Z"),
        _inc(clase="red_datos", origen="src/logging_db.py:210"),
    ]
    resumen = agregar(filas, [], top=5)
    assert resumen["por_clase"] == {"red_datos": 2, "bug": 1}
    assert resumen["por_origen"]["src/logging_db.py:210"] == 2
    assert resumen["por_dia"] == {"2026-08-16": 1, "2026-08-17": 2}


def test_insights_saca_las_preguntas_que_mas_fallan_normalizadas():
    from scripts.s324e_bot_errores_insights import agregar

    filas = [
        _inc(query_logs={"query": "Cuantos  LAZOS tiene la CAD-250",
                         "telegram_user_id": 7}),
        _inc(query_logs={"query": "cuantos lazos tiene la cad-250",
                         "telegram_user_id": 8}),
        _inc(query_logs={"query": "otra cosa", "telegram_user_id": 7}),
        _inc(query_logs=None),
    ]
    resumen = agregar(filas, [], top=5)
    assert resumen["top_preguntas"][0] == ("cuantos lazos tiene la cad-250", 2)
    assert resumen["tecnicos_afectados"] == 2


def test_insights_cuenta_el_silencio():
    from scripts.s324e_bot_errores_insights import agregar

    resumen = agregar([_inc(usuario_avisado=False), _inc()], [], top=5)
    assert resumen["sin_avisar"] == 1


def test_insights_no_inventa_clase_para_las_filas_heredadas():
    """Las filas de s286 no tienen clase. Asignarles una inventaría justo el
    dato que justifica la tabla nueva."""
    from scripts.s324e_bot_errores_insights import agregar

    resumen = agregar([], [{"query": "una pregunta",
                            "response": "TimeoutError@process_query",
                            "telegram_user_id": 3,
                            "created_at": "2026-08-17T10:00:00Z"}], top=5)
    assert resumen["n_heredadas"] == 1
    assert resumen["por_clase"] == {}
    assert resumen["heredadas_por_tipo"] == {"TimeoutError@process_query": 1}


def test_el_informe_no_revienta_en_una_consola_cp1252(capsys):
    """Cazado en el SMOKE real contra Supabase: la consola de Windows abre en
    cp1252 y el `print` de un emoji reventaba con UnicodeEncodeError — un
    informe de errores que falla al imprimirse. Los símbolos PROPIOS del
    informe deben ser codificables; para lo que no controlamos (las preguntas
    de los técnicos) el cinturón es `_consola_tolerante`."""
    from scripts.s324e_bot_errores_insights import agregar, imprimir

    resumen = agregar([_inc(usuario_avisado=False)], [], top=5)
    imprimir(resumen, label="últimos 7 días", tabla_ausente=False, top=5)
    imprimir(resumen, label="últimos 7 días", tabla_ausente=True, top=5)
    salida = capsys.readouterr().out
    salida.encode("cp1252", errors="strict")     # no lanza ⇒ contrato cumplido
    assert "migrations/015_bot_errores.sql" in salida


def test_la_consola_tolerante_no_lanza_aunque_no_se_pueda_reconfigurar():
    from scripts.s324e_bot_errores_insights import _consola_tolerante

    _consola_tolerante()      # bajo pytest stdout está capturado: debe tragar


def test_insights_tolera_filas_incompletas():
    from scripts.s324e_bot_errores_insights import agregar

    resumen = agregar([{}, {"clase": None}], [{}], top=5)
    assert resumen["n_incidencias"] == 2
    assert resumen["por_clase"]["(sin clase)"] == 2
