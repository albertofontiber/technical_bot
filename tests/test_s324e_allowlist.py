# -*- coding: utf-8 -*-
"""s324e — CONTROL DE ACCESO al piloto: allowlist + invitación de un solo uso.

Contratos que se fijan aquí:
  · la puerta DENIEGA por defecto y solo abre con un sí de la base, de la caché
    fresca o del bootstrap declarado en el entorno;
  · el fail-closed tiene UN matiz y solo uno: con Supabase caído sigue entrando
    quien ya estaba confirmado (y solo durante una ventana acotada), y NO entra
    nadie nuevo;
  · la invitación es de UN SOLO USO de verdad — incluidas dos personas pulsando
    el mismo enlace a la vez, que es donde un `SELECT`+`UPDATE` se rompe;
  · el token en claro no llega ni a la capa de persistencia ni a la base;
  · la puerta es UNA PUERTA: vive en el grupo -1 y nada puede colarse delante;
  · y no deja escapar excepciones, porque en PTB una excepción escapada de un
    handler de grupo -1 hace que el update SIGA a los demás grupos — o sea, un
    fallo de la puerta la abriría (semántica PINADA abajo contra PTB real).

Todo sin red y sin DB: la decisión es pura y el canje se ejerce contra un
PostgREST de mentira que aplica los filtros DE VERDAD, así que el test cae si
alguien quita una condición del canje.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import pytest

from src.bot import access

ROOT = Path(__file__).resolve().parent.parent
FUENTE_BOT = ROOT / "src" / "bot" / "telegram_bot.py"

DG = 9001
OTRO_DG = 9002
ALBERTO = 7777


@pytest.fixture(autouse=True)
def _puerta_limpia(monkeypatch):
    """Cada test arranca con la puerta encendida, sin caché y sin bootstrap.
    Encendida porque lo que se mide es su conducta; que el DEFAULT sea `off` lo
    comprueba su propio test."""
    monkeypatch.setenv("BOT_ALLOWLIST", "on")
    monkeypatch.delenv("BOT_ALLOWLIST_BOOTSTRAP", raising=False)
    monkeypatch.delenv("BOT_DAILY_LIMIT", raising=False)
    access.reiniciar_cache()
    yield
    access.reiniciar_cache()


def _responde(estado):
    """Una base que siempre contesta lo mismo, contando las veces."""
    llamadas = []

    def consultar(user_id):
        llamadas.append(user_id)
        return estado

    consultar.llamadas = llamadas
    return consultar


# ═══════════════════════════════════════════════════════════════════════════
# 1 · La decisión: permitir, denegar, y el fail-closed con matiz
# ═══════════════════════════════════════════════════════════════════════════


def test_la_puerta_permite_a_quien_esta_en_la_allowlist():
    veredicto = access.decidir(DG, _responde(access.AUTORIZADO))
    assert veredicto.permitido
    assert veredicto.origen == "db"


def test_la_puerta_deniega_a_quien_no_esta_y_el_mensaje_no_parece_un_error():
    veredicto = access.decidir(DG, _responde(access.DESCONOCIDO))
    assert not veredicto.permitido
    texto = veredicto.mensaje.lower()
    # El encargo pide un mensaje «claro y sobrio, que no parezca un error». Se
    # comprueba lo que se puede comprobar: que dice lo que es (piloto por
    # invitación), que da una salida concreta, y que NO usa el vocabulario de
    # avería ni culpa a quien escribe.
    assert "invitación" in texto or "invitacion" in texto
    assert "info@fontiber.com" in texto
    for palabra in ("error", "fallo", "no autorizado", "denegado", "prohibido"):
        assert palabra not in texto, f"suena a avería o a reproche: {palabra!r}"


def test_el_default_de_la_puerta_es_apagado(monkeypatch):
    """El interruptor maestro nace OFF: `main` auto-despliega y las migraciones
    las aplica Alberto a mano, así que el commit que trae la puerta NO puede
    cerrar el bot antes de que exista la tabla."""
    monkeypatch.delenv("BOT_ALLOWLIST", raising=False)
    assert access.acceso_activo() is False


def test_bootstrap_entra_sin_base_y_sin_cache(monkeypatch):
    """Alberto no se queda fuera al desplegar — ni siquiera con la migración sin
    aplicar y Supabase caído. Y es una VARIABLE declarada, no un `if id == …`."""
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", f"{ALBERTO}, 4242")

    base_caida = _responde(access.INDETERMINADO)
    veredicto = access.decidir(ALBERTO, base_caida)

    assert veredicto.permitido
    assert veredicto.origen == "bootstrap"
    assert base_caida.llamadas == [], "el bootstrap no debe depender de la base"
    assert access.decidir(4242, base_caida).permitido
    assert not access.decidir(DG, base_caida).permitido


def test_bootstrap_ignora_basura_sin_reventar(monkeypatch):
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", " 7777 ,,x, -3, 0,4242 ")
    assert access.ids_bootstrap() == frozenset({7777, 4242})


def test_fail_closed_con_matiz_el_conocido_sigue_y_el_nuevo_no():
    """EL requisito: con Supabase caído, quien ya estaba confirmado sigue
    usando el bot; nadie nuevo entra."""
    sana = _responde(access.AUTORIZADO)
    assert access.decidir(DG, sana, ahora=1000.0).permitido      # confirmado

    caida = _responde(access.INDETERMINADO)
    # Pasado el TTL fresco: hay que re-preguntar, y la base no contesta.
    degradado = access.decidir(DG, caida, ahora=1000.0 + access.TTL_FRESCO_S + 1)
    assert degradado.permitido
    assert degradado.origen == "cache_degradada"

    nuevo = access.decidir(OTRO_DG, caida, ahora=1000.0 + access.TTL_FRESCO_S + 1)
    assert not nuevo.permitido, "una caída de Supabase NO puede dejar entrar a nadie nuevo"
    assert nuevo.mensaje == access.MENSAJE_INDETERMINADO


def test_la_gracia_degradada_esta_acotada_y_no_se_renueva_con_el_uso():
    """Sin cota, una caída larga mantendría vivo indefinidamente a un revocado.
    Y el matiz del matiz: la ventana se cuenta desde la última confirmación REAL
    de la base, no desde el último mensaje — si se renovara al usar, el tope no
    llegaría nunca."""
    t0 = 500.0
    assert access.decidir(DG, _responde(access.AUTORIZADO), ahora=t0).permitido

    caida = _responde(access.INDETERMINADO)
    # Uso continuado durante la caída: NO renueva la confirmación. Se recorre la
    # ventana entera en pasos, que es justo el patrón que la rompería si
    # `confirmado_en` se refrescara en la rama degradada.
    paso = access.GRACIA_DEGRADADA_S / 10
    for salto in range(1, 10):
        assert access.decidir(DG, caida, ahora=t0 + salto * paso).permitido

    fuera = access.decidir(DG, caida, ahora=t0 + access.GRACIA_DEGRADADA_S + 1)
    assert not fuera.permitido, "la gracia se renovó con el uso: nunca caducaría"


def test_una_revocacion_surte_efecto_al_caducar_el_ttl():
    """«Usuario revocado con sesión en curso»: el peor caso es el TTL de la
    caché, sin reiniciar el worker — el mismo plazo que el runbook ya promete
    para la revocación del consentimiento."""
    assert access.decidir(DG, _responde(access.AUTORIZADO), ahora=0.0).permitido

    revocado = _responde(access.DESCONOCIDO)
    assert access.decidir(DG, revocado, ahora=access.TTL_FRESCO_S - 1).permitido
    assert not access.decidir(DG, revocado, ahora=access.TTL_FRESCO_S + 1).permitido
    assert access.TTL_FRESCO_S <= 600, "el techo de la revocación no puede crecer"


def test_el_no_caduca_pronto_para_que_un_alta_desde_el_script_se_vea():
    """El alta la puede hacer el script desde OTRO proceso. Si el NO durase lo
    mismo que el SÍ, un DG recién dado de alta rebotaría 10 minutos."""
    assert access.TTL_NEGATIVO_S <= 60
    base = _responde(access.DESCONOCIDO)
    assert not access.decidir(DG, base, ahora=0.0).permitido
    access.decidir(DG, base, ahora=10.0)
    assert base.llamadas == [DG], "el NO no se está cacheando: un roundtrip por mensaje"
    access.decidir(DG, base, ahora=access.TTL_NEGATIVO_S + 1)
    assert base.llamadas == [DG, DG]


@pytest.mark.parametrize("respuesta", ["", "si", "AUTORIZADO", None, True, 1])
def test_un_estado_que_no_reconocemos_jamas_abre_la_puerta(respuesta):
    """Un typo en el llamante no puede convertirse en un permiso."""
    assert not access.decidir(DG, lambda _uid: respuesta).permitido


def test_una_consulta_que_lanza_no_abre_la_puerta():
    def explota(_uid):
        raise RuntimeError("supabase caído")

    veredicto = access.decidir(DG, explota)
    assert not veredicto.permitido
    assert veredicto.mensaje == access.MENSAJE_INDETERMINADO


def test_un_update_sin_autor_se_deniega_en_silencio():
    """Post de canal o mensaje de servicio: no hay a quién autorizar ni a quién
    contestar. Se deniega sin mensaje, no se adivina un id."""
    veredicto = access.decidir(0, _responde(access.AUTORIZADO))
    assert not veredicto.permitido
    assert veredicto.mensaje == ""
    assert not access.decidir(None, _responde(access.AUTORIZADO)).permitido


def test_la_cache_va_keyed_por_persona():
    """Red line del piloto multi-DG (auditoría §P1): nada de estado de proceso
    compartido entre personas."""
    access.decidir(DG, _responde(access.AUTORIZADO))
    assert set(access._cache) == {DG}
    assert not access.decidir(OTRO_DG, _responde(access.DESCONOCIDO)).permitido
    assert access._cache[DG].permitido and not access._cache[OTRO_DG].permitido


# ═══════════════════════════════════════════════════════════════════════════
# 2 · El tope diario
# ═══════════════════════════════════════════════════════════════════════════


def test_el_tope_diario_deja_pasar_hasta_el_limite_y_luego_avisa():
    for i in range(3):
        assert access.consumir_cuota(DG, limite=3, dia="2026-08-17").permitido, i
    agotado = access.consumir_cuota(DG, limite=3, dia="2026-08-17")
    assert not agotado.permitido
    assert agotado.motivo == "tope_diario"
    # El usuario tiene que entender qué le pasa: qué ha ocurrido, que no está
    # roto, y cuándo vuelve.
    assert "3 consultas" in agotado.mensaje
    assert "mañana" in agotado.mensaje.lower()
    assert "no es un fallo" in agotado.mensaje.lower()


def test_el_tope_se_reinicia_al_cambiar_de_dia():
    access.consumir_cuota(DG, limite=1, dia="2026-08-17")
    assert not access.consumir_cuota(DG, limite=1, dia="2026-08-17").permitido
    assert access.consumir_cuota(DG, limite=1, dia="2026-08-18").permitido


def test_el_tope_es_por_persona():
    access.consumir_cuota(DG, limite=1, dia="d")
    assert not access.consumir_cuota(DG, limite=1, dia="d").permitido
    assert access.consumir_cuota(OTRO_DG, limite=1, dia="d").permitido


def test_el_tope_se_puede_desactivar_sin_deploy():
    for _ in range(50):
        assert access.consumir_cuota(DG, limite=0, dia="d").permitido


def test_el_default_del_tope_es_sensato_y_un_valor_roto_no_lo_desactiva(monkeypatch):
    monkeypatch.delenv("BOT_DAILY_LIMIT", raising=False)
    assert access.limite_diario() == 30
    monkeypatch.setenv("BOT_DAILY_LIMIT", "muchas")
    assert access.limite_diario() == 30, "un typo en Railway no puede quitar el tope"
    monkeypatch.setenv("BOT_DAILY_LIMIT", "5")
    assert access.limite_diario() == 5


def test_el_contador_no_crece_con_los_dias():
    """Memoria acotada por nº de personas, no por tiempo."""
    for dia in range(40):
        access.consumir_cuota(DG, limite=5, dia=f"2026-09-{dia:02d}")
    assert len(access._uso) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 3 · El token y el enlace
# ═══════════════════════════════════════════════════════════════════════════


def test_el_token_cabe_en_el_deep_link_de_telegram():
    """Telegram acota el payload de `?start=` a 64 caracteres del alfabeto
    base64url. Un token que no quepa produce un enlace que no funciona."""
    for _ in range(50):
        token = access.token_nuevo()
        assert len(token) <= access.LONGITUD_PAYLOAD_MAX
        assert access.es_payload_plausible(token)
        assert set(token) <= set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )


def test_los_tokens_no_se_repiten_y_salen_de_secrets():
    assert len({access.token_nuevo() for _ in range(500)}) == 500
    fuente = (ROOT / "src" / "bot" / "access.py").read_text(encoding="utf-8")
    assert "import secrets" in fuente
    assert "import random" not in fuente, (
        "`random` es un Mersenne Twister reproducible: con unas cuantas salidas "
        "se predice la siguiente, y aquí la siguiente salida es una llave"
    )


@pytest.mark.parametrize("basura", ["", "x", "hola", "a" * 65, "tok en", None,
                                    123, "abc$def" + "x" * 20])
def test_un_payload_implausible_ni_se_consulta(basura):
    assert not access.es_payload_plausible(basura)


def test_el_enlace_tiene_la_forma_que_telegram_entiende():
    enlace = access.enlace_invitacion("@PCI_Soporte_tecnico_bot", "TOKEN")
    assert enlace == "https://t.me/PCI_Soporte_tecnico_bot?start=TOKEN"


def test_el_hash_es_estable_y_no_reversible_por_forma():
    token = access.token_nuevo()
    assert access.hash_token(token) == access.hash_token(token)
    assert len(access.hash_token(token)) == 64
    assert token not in access.hash_token(token)


# ═══════════════════════════════════════════════════════════════════════════
# 4 · El canje, contra un PostgREST de mentira que SÍ aplica los filtros
# ═══════════════════════════════════════════════════════════════════════════


def _iso(momento):
    return momento.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class _Respuesta:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.content = b"[]" if payload is not None else b""
        self.text = ""

    def json(self):
        if self._payload is None:
            raise ValueError("sin cuerpo")
        return self._payload


class SupabaseFalso:
    """PostgREST de mentira con lo que IMPORTA: los filtros de la URL se aplican
    de VERDAD sobre las filas en memoria.

    Por qué así y no un mock que devuelve lo que le pidan: lo que hay que probar
    del canje no es que llame a la base, es QUÉ CONDICIONES le manda. Con un
    mock tonto, quitar `canjeada_at=is.null` del PATCH dejaría los tests verdes
    y la invitación pasaría a ser reutilizable. Aquí, quitarla los pone rojos.

    Fidelidad declarada: las fechas se comparan como CADENAS (los valores de los
    tests están separados por años, así que el orden lexicográfico coincide con
    el cronológico); la base real compara `timestamptz`.
    """

    def __init__(self):
        self.invitaciones: list[dict] = []
        self.allowlist: list[dict] = []
        self.tablas_ausentes: set[str] = set()
        self.fallo_en_alta = False
        self.fallo_en_devolucion = False
        self.vistos: list[str] = []          # todo lo que ha viajado, en crudo

    # -- utilidades ------------------------------------------------------
    def _tabla(self, url):
        return url.split("/rest/v1/")[1].split("?")[0]

    def _filas(self, tabla):
        return self.invitaciones if tabla == "bot_invitaciones" else self.allowlist

    def _casa(self, fila, params):
        for clave, valor in (params or {}).items():
            if clave in ("select", "limit", "order", "offset", "on_conflict"):
                continue
            valor = str(valor)
            actual = fila.get(clave)
            if valor == "is.null":
                if actual is not None:
                    return False
            elif valor.startswith("eq."):
                if str(actual) != valor[3:]:
                    return False
            elif valor.startswith("gt."):
                if actual is None or str(actual) <= valor[3:]:
                    return False
            else:                                   # pragma: no cover - guardia
                raise AssertionError(f"filtro no soportado por el doble: {valor}")
        return True

    # -- el "cliente" ----------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *_excepcion):
        return False

    def get(self, url, headers=None, params=None):
        tabla = self._tabla(url)
        self.vistos.append(f"GET {url} {params}")
        if tabla in self.tablas_ausentes:
            return _Respuesta(404, {"code": "PGRST205"})
        return _Respuesta(200, [f for f in self._filas(tabla)
                                if self._casa(f, params)])

    def patch(self, url, headers=None, params=None, json=None):
        tabla = self._tabla(url)
        self.vistos.append(f"PATCH {url} {params} {json}")
        if tabla in self.tablas_ausentes:
            return _Respuesta(404, {"code": "PGRST205"})
        if self.fallo_en_devolucion and (json or {}).get("canjeada_at") is None:
            return _Respuesta(500, {"code": "XX000"})
        tocadas = []
        for fila in self._filas(tabla):
            if self._casa(fila, params):
                fila.update(json or {})
                tocadas.append(dict(fila))
        return _Respuesta(200, tocadas)

    @staticmethod
    def _viola_check(tabla: str, fila: dict) -> str | None:
        """Los CHECK de la 016 que el código puede romper, aplicados de VERDAD.

        Sin esto el doble aceptaría filas que Postgres rechaza y los tests
        dirían que funciona algo que en producción daría 400 — que es
        exactamente el fallo que el dúo encontró en la re-admisión (se ponía
        `revocado_at=NULL` conservando `revocado_por`).
        """
        if tabla == "bot_allowlist":
            if (fila.get("revocado_at") is None) != (fila.get("revocado_por") is None):
                return "bot_allowlist_revocacion_completa"
        if tabla == "bot_invitaciones":
            if (fila.get("canjeada_at") is None) != (fila.get("canjeada_por") is None):
                return "bot_invitaciones_canje_completo"
        return None

    def post(self, url, headers=None, params=None, json=None):
        tabla = self._tabla(url)
        self.vistos.append(f"POST {url} {json}")
        if tabla in self.tablas_ausentes:
            return _Respuesta(404, {"code": "PGRST205"})
        if self.fallo_en_alta and tabla == "bot_allowlist":
            return _Respuesta(500, {"code": "XX000"})
        filas = self._filas(tabla)
        clave = "telegram_user_id" if tabla == "bot_allowlist" else "id"
        for fila in filas:
            if fila.get(clave) == (json or {}).get(clave):
                fusionada = {**fila, **(json or {})}         # merge-duplicates
                roto = self._viola_check(tabla, fusionada)
                if roto:
                    return _Respuesta(400, {"code": "23514", "message": roto})
                fila.update(json)
                return _Respuesta(201, [dict(fila)])
        roto = self._viola_check(tabla, json or {})
        if roto:
            return _Respuesta(400, {"code": "23514", "message": roto})
        filas.append(dict(json or {}))
        return _Respuesta(201, [dict(json or {})])


@pytest.fixture
def supabase(monkeypatch):
    import src.logging_db as logging_db

    falso = SupabaseFalso()
    monkeypatch.setattr(logging_db, "abierto", lambda **_k: falso)
    monkeypatch.setattr(logging_db, "SUPABASE_URL", "https://x.supabase.co")
    return falso


def _invitar(falso, token, *, nota="Juan Perez, DG de Acme", dias=7,
             revocada=False, id_="inv-1"):
    falso.invitaciones.append({
        "id": id_,
        "token_hash": access.hash_token(token),
        "nota": nota,
        "creada_por": "alberto",
        "expira_at": _iso(datetime.now(timezone.utc) + timedelta(days=dias)),
        "canjeada_at": None,
        "canjeada_por": None,
        "revocada_at": _iso(datetime.now(timezone.utc)) if revocada else None,
    })


def _canjear(token, user_id):
    from src.logging_db import canjear_invitacion

    return canjear_invitacion(token_hash=access.hash_token(token),
                              telegram_user_id=user_id)


def test_el_canje_da_de_alta_con_la_traza_de_quien_invito(supabase):
    token = access.token_nuevo()
    _invitar(supabase, token)

    assert _canjear(token, DG).estado == access.CANJE_OK

    alta = supabase.allowlist[0]
    assert alta["telegram_user_id"] == DG
    assert alta["origen"] == "invitacion"
    assert alta["alta_por"] == "alberto", "quién dio de alta a quién"
    assert alta["invitacion_id"] == "inv-1"
    assert alta["nota"] == "Juan Perez, DG de Acme"
    assert alta["alta_at"], "cuándo"
    # Y en la invitación queda QUIÉN la usó — que puede no ser la persona de la
    # nota si el enlace se reenvió. Ése es justo el dato que lo hace visible.
    assert supabase.invitaciones[0]["canjeada_por"] == DG


def test_la_invitacion_es_de_un_solo_uso(supabase):
    token = access.token_nuevo()
    _invitar(supabase, token)

    assert _canjear(token, DG).estado == access.CANJE_OK
    assert _canjear(token, OTRO_DG).estado == access.CANJE_INVALIDA
    assert [f["telegram_user_id"] for f in supabase.allowlist] == [DG]


def test_dos_personas_pulsan_el_mismo_enlace_a_la_vez_y_solo_entra_una(supabase):
    """La carrera. El canje es UN update condicional, así que la segunda
    escritura re-evalúa su WHERE sobre la fila ya canjeada y afecta a 0 filas.
    El doble reproduce esa semántica; lo que este test protege de verdad es que
    el código siga mandando la condición (un `SELECT`+`UPDATE` la perdería)."""
    token = access.token_nuevo()
    _invitar(supabase, token)

    resultados = [_canjear(token, DG).estado, _canjear(token, OTRO_DG).estado]

    assert resultados.count(access.CANJE_OK) == 1
    assert resultados.count(access.CANJE_INVALIDA) == 1
    assert len(supabase.allowlist) == 1

    patches = [v for v in supabase.vistos if v.startswith("PATCH")]
    assert "'canjeada_at': 'is.null'" in patches[0], (
        "el canje dejó de ser condicional: sin `canjeada_at=is.null` en el "
        "PATCH, dos personas a la vez entran las dos"
    )


def test_una_invitacion_caducada_no_se_canjea(supabase):
    token = access.token_nuevo()
    _invitar(supabase, token, dias=-1)
    assert _canjear(token, DG).estado == access.CANJE_INVALIDA
    assert supabase.allowlist == []


def test_una_invitacion_anulada_no_se_canjea(supabase):
    token = access.token_nuevo()
    _invitar(supabase, token, revocada=True)
    assert _canjear(token, DG).estado == access.CANJE_INVALIDA


def test_un_token_inventado_no_canjea_nada(supabase):
    _invitar(supabase, access.token_nuevo())
    assert _canjear(access.token_nuevo(), DG).estado == access.CANJE_INVALIDA


def test_si_el_alta_falla_la_invitacion_se_devuelve_a_pendiente(supabase):
    """Los dos pasos no comparten transacción: si el alta falla, la invitación
    NO se queda quemada — se devuelve y la persona puede reintentar con el mismo
    enlace."""
    token = access.token_nuevo()
    _invitar(supabase, token)
    supabase.fallo_en_alta = True

    assert _canjear(token, DG).estado == access.CANJE_INDETERMINADO
    assert supabase.invitaciones[0]["canjeada_at"] is None
    assert supabase.invitaciones[0]["canjeada_por"] is None

    supabase.fallo_en_alta = False
    assert _canjear(token, DG).estado == access.CANJE_OK


def test_si_tambien_falla_la_devolucion_se_dice_indeterminado_no_ok(supabase):
    """El peor caso declarado: la invitación queda quemada sin alta. Lo que NO
    puede pasar es que se responda `ok` y el DG crea que tiene acceso."""
    token = access.token_nuevo()
    _invitar(supabase, token)
    supabase.fallo_en_alta = True
    supabase.fallo_en_devolucion = True

    assert _canjear(token, DG).estado == access.CANJE_INDETERMINADO
    assert supabase.allowlist == []


def test_la_tabla_ausente_es_indeterminado_y_nunca_desconocido(supabase):
    """Una migración sin aplicar NO es una respuesta sobre esta persona. Con esa
    lectura, quien ya estaba dentro sigue entrando por caché y nadie nuevo entra
    — en vez de cerrarle la puerta a todo el mundo por un despliegue a medias."""
    from src.logging_db import allowlist_estado

    supabase.tablas_ausentes = {"bot_allowlist", "bot_invitaciones"}
    assert allowlist_estado(DG) == access.INDETERMINADO
    assert _canjear(access.token_nuevo(), DG).estado == access.CANJE_INDETERMINADO


def test_el_estado_de_la_allowlist_distingue_los_tres_casos(supabase):
    from src.logging_db import allowlist_estado

    supabase.allowlist.append({"telegram_user_id": DG, "revocado_at": None})
    supabase.allowlist.append({"telegram_user_id": OTRO_DG,
                               "revocado_at": _iso(datetime.now(timezone.utc))})

    assert allowlist_estado(DG) == access.AUTORIZADO
    assert allowlist_estado(OTRO_DG) == access.DESCONOCIDO, "un revocado no entra"
    assert allowlist_estado(12345) == access.DESCONOCIDO


def test_un_error_de_red_al_consultar_es_indeterminado(supabase, monkeypatch):
    import src.logging_db as logging_db

    def explota(**_k):
        raise RuntimeError("conexión rota")

    monkeypatch.setattr(logging_db, "abierto", explota)
    assert logging_db.allowlist_estado(DG) == access.INDETERMINADO
    assert _canjear("x" * 32, DG).estado == access.CANJE_INDETERMINADO


def test_el_token_en_claro_no_llega_a_la_persistencia_ni_a_la_base(supabase):
    """La capa de persistencia recibe el SHA-256, nunca el token. Se comprueba
    por conducta (nada de lo que viaja contiene el token) y por firma."""
    import src.logging_db as logging_db

    token = access.token_nuevo()
    _invitar(supabase, token)
    assert _canjear(token, DG).estado == access.CANJE_OK

    for viajado in supabase.vistos:
        assert token not in viajado, "el token en claro viajó a la base"
    firma = inspect.signature(logging_db.canjear_invitacion)
    assert "token_hash" in firma.parameters
    assert "token" not in firma.parameters


def test_vocabulario_pinado_entre_capas(supabase):
    """`access` es dueño del vocabulario y `logging_db` devuelve las MISMAS
    cadenas sin importarlas (la matriz de imports prohíbe `raiz → bot`). Este
    test es lo que impide que deriven en silencio."""
    from src.logging_db import allowlist_estado

    supabase.allowlist.append({"telegram_user_id": DG, "revocado_at": None})
    assert allowlist_estado(DG) in access.ESTADOS
    assert allowlist_estado(999) in access.ESTADOS
    supabase.tablas_ausentes = {"bot_allowlist"}
    assert allowlist_estado(DG) in access.ESTADOS

    token = access.token_nuevo()
    supabase.tablas_ausentes = set()
    _invitar(supabase, token)
    assert _canjear(token, DG).estado in access.CANJES
    assert _canjear(token, DG).estado in access.CANJES


def test_logging_db_no_importa_el_paquete_bot():
    """La matriz de `test_import_contract` ya lo prohíbe en general; aquí se
    ancla el caso concreto, porque la tentación de `from .bot.access import
    AUTORIZADO` es real cada vez que alguien toca este par de ficheros."""
    fuente = (ROOT / "src" / "logging_db.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            assert "bot" not in (nodo.module or "").split("."), \
                f"logging_db importa del paquete bot: {nodo.module}"


# ═══════════════════════════════════════════════════════════════════════════
# 5 · La puerta ES una puerta (grupo -1), y no se abre al romperse
# ═══════════════════════════════════════════════════════════════════════════


class _Mensaje:
    def __init__(self, texto=None, voice=None):
        self.text = texto
        self.voice = voice
        self.audio = None
        self.chat = SimpleNamespace(id=DG)
        self.reply_to_message = None
        self.respuestas = []

    async def reply_text(self, texto, **_kwargs):
        self.respuestas.append(texto)


def _update(texto=None, *, user_id=DG, voice=None, tipo_chat="private"):
    """Un update de chat PRIVADO por defecto: es la única forma que la puerta
    admite desde el crítico 2 del dúo, y la forma real del piloto."""
    mensaje = _Mensaje(texto, voice)
    return SimpleNamespace(
        message=mensaje, effective_message=mensaje, update_id=1,
        effective_user=SimpleNamespace(id=user_id, full_name="Marta Ruiz",
                                       first_name="Marta", username="martaruiz"),
        effective_chat=SimpleNamespace(id=user_id, type=tipo_chat),
        callback_query=None,
    )


@pytest.fixture
def bot_con_puerta(monkeypatch):
    """El bot real con la consulta de allowlist doblada."""
    import src.bot.telegram_bot as bot

    estado = {"valor": access.DESCONOCIDO}
    monkeypatch.setattr(bot, "allowlist_estado", lambda _uid: estado["valor"])
    return bot, estado


def _pasa_la_puerta(bot, update, context=None):
    """True si la puerta deja seguir; False si la para."""
    from telegram.ext import ApplicationHandlerStop

    try:
        asyncio.run(bot.access_gate(update, context or SimpleNamespace()))
    except ApplicationHandlerStop:
        return False
    return True


def test_la_puerta_para_el_update_de_un_desconocido(bot_con_puerta):
    bot, estado = bot_con_puerta
    estado["valor"] = access.DESCONOCIDO
    update = _update("¿cómo configuro la CAD-250?")

    assert _pasa_la_puerta(bot, update) is False
    assert update.message.respuestas, "no se le dijo nada: eso es el silencio"
    assert "invitación" in update.message.respuestas[0]


def test_la_puerta_deja_pasar_al_autorizado(bot_con_puerta):
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    update = _update("¿cómo configuro la CAD-250?")

    assert _pasa_la_puerta(bot, update) is True
    assert update.message.respuestas == []


def test_la_puerta_apagada_es_inerte(bot_con_puerta, monkeypatch):
    """Default `off` = el bot de HOY, exacto: ni consulta la base ni contesta."""
    bot, estado = bot_con_puerta
    monkeypatch.setenv("BOT_ALLOWLIST", "off")
    monkeypatch.setattr(bot, "allowlist_estado",
                        lambda _uid: pytest.fail("consultó con la puerta apagada"))
    update = _update("hola")

    assert _pasa_la_puerta(bot, update) is True
    assert update.message.respuestas == []


def test_la_puerta_aplica_el_tope_diario_al_autorizado(bot_con_puerta, monkeypatch):
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    monkeypatch.setenv("BOT_DAILY_LIMIT", "2")

    assert _pasa_la_puerta(bot, _update("una")) is True
    assert _pasa_la_puerta(bot, _update("dos")) is True
    agotado = _update("tres")
    assert _pasa_la_puerta(bot, agotado) is False
    assert "límite de 2 consultas" in agotado.message.respuestas[0]


def test_los_comandos_y_los_botones_no_gastan_cupo(bot_con_puerta, monkeypatch):
    """`/help` no cuesta modelo, y penalizar un 👍/👎 sería el incentivo
    contrario. Un audio SÍ cuenta: paga transcripción antes que nada."""
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    monkeypatch.setenv("BOT_DAILY_LIMIT", "1")

    assert _pasa_la_puerta(bot, _update("/help")) is True
    callback = SimpleNamespace(
        message=None, effective_message=None, update_id=2,
        effective_user=SimpleNamespace(id=DG),
        effective_chat=SimpleNamespace(id=DG, type="private"),
        callback_query=SimpleNamespace(),
    )
    assert _pasa_la_puerta(bot, callback) is True
    assert access.consumo_actual(DG) == 0

    assert _pasa_la_puerta(bot, _update(None, voice=object())) is True
    assert access.consumo_actual(DG) == 1


def test_la_puerta_no_deja_escapar_excepciones(bot_con_puerta, monkeypatch):
    """FAIL-CLOSED ante un defecto propio. Si la puerta lanza, PTB manda el
    fallo a `process_error` y CONTINÚA con el grupo 0 (ver el test de abajo):
    romperse abriría la puerta. Además el fallo pasa por el punto ÚNICO."""
    bot, _estado = bot_con_puerta
    reportados = []

    def explota(*_a, **_k):
        raise RuntimeError("defecto en la puerta")

    async def _reportar(update, exc, **kwargs):
        reportados.append((type(exc).__name__, kwargs.get("etapa")))
        return "cod"

    monkeypatch.setattr(access, "decidir", explota)
    monkeypatch.setattr(bot, "_reportar_error", _reportar)

    assert _pasa_la_puerta(bot, _update("hola")) is False, \
        "un fallo interno dejó pasar el update: la puerta se abre al romperse"
    assert reportados == [("RuntimeError", "puerta_acceso")]


def test_ptb_no_para_el_update_cuando_un_handler_lanza():
    """LA SEMÁNTICA QUE JUSTIFICA EL TEST DE ARRIBA, medida contra PTB real.

    `Application.process_update` solo corta el recorrido de grupos si se lanza
    `ApplicationHandlerStop` o si un error handler lo relanza. Con una excepción
    normal, `process_error` devuelve False y el bucle SIGUE con el grupo 0. Si
    algún día PTB cambiara esto, este test cae y avisa de que el cinturón de la
    puerta ya no es necesario (o de que hace falta otro)."""
    import datetime as dt

    from telegram import Chat, Message, Update, User
    from telegram.ext import ApplicationBuilder, TypeHandler

    app = ApplicationBuilder().token("123456:AAA-BBB_ccc").build()
    # Se marca inicializada a mano: lo que se mide es el BUCLE de despacho, y
    # `initialize()` haría `get_me()` contra la red.
    app._initialized = True

    llegadas = []

    async def puerta_rota(_update, _context):
        raise RuntimeError("defecto")

    async def handler_de_verdad(_update, _context):
        llegadas.append("grupo 0")

    app.add_handler(TypeHandler(Update, puerta_rota), group=-1)
    app.add_handler(TypeHandler(Update, handler_de_verdad), group=0)

    usuario = User(id=DG, first_name="DG", is_bot=False)
    mensaje = Message(message_id=1, date=dt.datetime.now(dt.timezone.utc),
                      chat=Chat(id=DG, type="private"), from_user=usuario,
                      text="hola")
    asyncio.run(app.process_update(Update(update_id=1, message=mensaje)))

    assert llegadas == ["grupo 0"], (
        "PTB ya NO deja pasar el update cuando el handler de grupo -1 lanza: "
        "revisa el cinturón de `access_gate` (puede sobrar, o hacer falta otro)"
    )


def test_la_puerta_va_primero_y_nada_puede_colarse_delante():
    """La puerta es UNA puerta, no un `if` repetido en cada handler: se registra
    como `TypeHandler` en el grupo -1 y PTB evalúa los grupos de menor a mayor.
    Este test impide las dos formas de romperlo: quitarla, o registrar otro
    handler en un grupo aún menor."""
    import src.bot.telegram_bot as bot

    arbol = ast.parse(inspect.getsource(bot.run_bot).lstrip())
    registros = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if getattr(nodo.func, "attr", "") != "add_handler":
            continue
        grupo = 0
        for kw in nodo.keywords:
            if kw.arg == "group":
                grupo = ast.literal_eval(kw.value)
        tipo = getattr(nodo.args[0].func, "id", "") if nodo.args and \
            isinstance(nodo.args[0], ast.Call) else ""
        registros.append((grupo, tipo))

    puertas = [g for g, tipo in registros if tipo == "TypeHandler"]
    assert puertas == [-1], f"la puerta no está en el grupo -1: {registros}"
    assert min(g for g, _t in registros) == -1, (
        f"hay un handler por delante de la puerta: {registros}"
    )


def test_las_exenciones_de_la_puerta_son_exactamente_dos():
    """`/start` (es el único que recibe el token de la invitación) y
    `/privacidad` (leer el aviso antes de aceptar es lo que hace informada la
    aceptación). Cualquier otra exención tiene que discutirse, no colarse."""
    import src.bot.telegram_bot as bot

    assert set(bot.COMANDOS_SIN_PUERTA) == {"/start", "/privacidad"}


def test_el_comando_se_normaliza_como_lo_manda_telegram():
    import src.bot.telegram_bot as bot

    assert bot._comando_de(_update("/start AbC-123")) == "/start"
    assert bot._comando_de(_update("/privacidad@PCI_bot")) == "/privacidad"
    assert bot._comando_de(_update("/START")) == "/start"
    assert bot._comando_de(_update("hola")) is None


# ═══════════════════════════════════════════════════════════════════════════
# 6 · `/start`: el canje, y el orden puerta → consentimiento
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def start(monkeypatch):
    """`/start` real con sus dependencias dobladas. Devuelve el registro de lo
    observable."""
    import src.bot.telegram_bot as bot

    rec = {"canjes": [], "consentimientos": [], "estado": access.DESCONOCIDO,
           "canje": access.CANJE_OK}

    monkeypatch.setattr(bot, "allowlist_estado", lambda _uid: rec["estado"])
    monkeypatch.setattr(bot, "has_consent", lambda _uid: False)
    monkeypatch.setattr(bot, "set_consent",
                        lambda uid, **k: rec["consentimientos"].append(uid))
    monkeypatch.setattr(bot, "_fabricantes_resumen", lambda: ("*Notifier*", 30))

    def _canjear(*, token_hash, telegram_user_id):
        from src.logging_db import ResultadoCanje

        rec["canjes"].append((token_hash, telegram_user_id))
        return ResultadoCanje(rec["canje"], nota="Juan Perez, DG de Acme",
                              creada_por="alberto", invitacion_id="inv-1")

    monkeypatch.setattr(bot, "canjear_invitacion", _canjear)
    return bot, rec


def _start(bot, update, args):
    asyncio.run(start_command_con_args(bot, update, args))


async def start_command_con_args(bot, update, args):
    await bot.start_command(update, SimpleNamespace(args=args))


def test_start_canjea_la_invitacion_y_luego_pide_el_consentimiento(start):
    """El flujo del DG, entero: pulsa el enlace → queda dado de alta → el bot le
    enseña los términos. El consentimiento sigue siendo obligatorio: la puerta
    NO lo sustituye."""
    bot, rec = start
    token = access.token_nuevo()
    update = _update("/start")

    _start(bot, update, [token])

    assert rec["canjes"] == [(access.hash_token(token), DG)]
    assert access.MENSAJE_INVITACION_ACEPTADA in update.message.respuestas[0]
    assert "/accept" in update.message.respuestas[1], \
        "tras el canje hay que pedir el consentimiento, no dar acceso directo"
    # Y queda cacheado como autorizado: sin esto rebotaría contra su propia
    # invitación hasta que caducara el negativo.
    assert access.decidir(DG, _responde(access.INDETERMINADO)).permitido


def test_start_sin_invitacion_solo_enseña_la_puerta(start):
    bot, rec = start
    update = _update("/start")

    _start(bot, update, [])

    assert rec["canjes"] == [], "no había token: no hay nada que consultar"
    assert update.message.respuestas == [access.MENSAJE_NO_AUTORIZADO]


def test_start_con_basura_no_consulta_la_base(start):
    bot, rec = start
    update = _update("/start")

    _start(bot, update, ["hola"])

    assert rec["canjes"] == []
    assert update.message.respuestas == [access.MENSAJE_NO_AUTORIZADO]


def test_una_invitacion_no_valida_lo_dice_sin_confirmar_que_existio(start):
    bot, rec = start
    rec["canje"] = access.CANJE_INVALIDA
    update = _update("/start")

    _start(bot, update, [access.token_nuevo()])

    respuesta = update.message.respuestas[0]
    assert respuesta == access.MENSAJE_INVITACION_NO_VALIDA
    # Caducada / usada / anulada / inexistente se cuentan igual: distinguirlas
    # confirmaría que ese token fue válido alguna vez.
    assert "caduc" in respuesta and "usa" in respuesta


def test_start_de_un_autorizado_no_quema_la_invitacion_de_otro(start):
    """Alguien que ya está dentro pulsa un enlace que le reenviaron: se le da la
    bienvenida y el enlace sigue vivo para su destinatario."""
    bot, rec = start
    rec["estado"] = access.AUTORIZADO
    update = _update("/start")

    _start(bot, update, [access.token_nuevo()])

    assert rec["canjes"] == [], "quemó una invitación ajena"
    assert "/accept" in update.message.respuestas[0]


def test_con_la_base_caida_no_se_intenta_canjear(start):
    """Gastar el enlace sin poder confirmar el alta dejaría al DG sin invitación
    y sin acceso."""
    bot, rec = start
    rec["estado"] = access.INDETERMINADO
    update = _update("/start")

    _start(bot, update, [access.token_nuevo()])

    assert rec["canjes"] == []
    assert update.message.respuestas == [access.MENSAJE_INDETERMINADO]


def test_el_orden_es_puerta_y_luego_consentimiento(start):
    """MINIMIZACIÓN: quien no está invitado no llega a los términos, así que no
    se guarda su nombre ni su id en `user_consent` — una tabla cuyo plazo sigue
    siendo un [DECIDIR] en la matriz RGPD."""
    bot, rec = start
    update = _update("/start")

    _start(bot, update, [])

    assert rec["consentimientos"] == []
    assert all("/accept" not in r for r in update.message.respuestas), \
        "a un no invitado se le enseñaron los términos"


def test_privacidad_se_puede_leer_sin_estar_invitado(start):
    """La promesa de s295 no la puede romper un control de acceso: el aviso es
    público y no contiene dato personal de nadie."""
    bot, _rec = start
    update = _update("/privacidad")

    assert _pasa_la_puerta(bot, update) is True
    asyncio.run(bot.privacy_command(update, SimpleNamespace()))
    assert "Responsable" in update.message.respuestas[0]


# ═══════════════════════════════════════════════════════════════════════════
# 7 · Gobernanza: lo que la migración y los docs tienen que decir
# ═══════════════════════════════════════════════════════════════════════════


def test_la_migracion_016_existe_y_no_guarda_el_token_en_claro():
    sql = (ROOT / "migrations" / "016_allowlist_invitaciones.sql").read_text(
        encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS bot_allowlist" in sql
    assert "CREATE TABLE IF NOT EXISTS bot_invitaciones" in sql
    assert "token_hash" in sql
    # Ninguna columna llamada `token` a secas: el token en claro no tiene dónde
    # vivir en la base.
    assert "\n    token TEXT" not in sql
    # La baja es lógica y el borrado no se concede a nadie.
    assert "revocado_at" in sql
    assert "GRANT DELETE" not in sql.upper()
    # RLS como el resto de tablas del bot.
    for tabla in ("bot_allowlist", "bot_invitaciones"):
        assert f"ALTER TABLE public.{tabla} FORCE ROW LEVEL SECURITY" in sql


def test_la_migracion_016_no_se_declara_aplicada():
    sql = (ROOT / "migrations" / "016_allowlist_invitaciones.sql").read_text(
        encoding="utf-8")
    assert "NO APLICADA" in sql, (
        "la 016 la aplica Alberto a mano, como la 015: el fichero tiene que "
        "decirlo en la cabecera"
    )


def test_las_dos_tablas_estan_en_la_matriz_rgpd():
    """`telegram_user_id` es dato personal. Una tabla que lo guarda y no está en
    la matriz es exactamente el agujero que la matriz existe para cerrar."""
    matriz = (ROOT / "docs" / "RGPD_RETENCION.md").read_text(encoding="utf-8")
    assert "bot_allowlist" in matriz
    assert "bot_invitaciones" in matriz


def test_las_tres_flags_estan_registradas():
    """Un `getenv` sin registrar pone roja la suite (s311/L2b); esto lo ancla
    aquí también para que se lea junto al resto del mecanismo."""
    from src.flags import REGISTRO

    for nombre in ("BOT_ALLOWLIST", "BOT_ALLOWLIST_BOOTSTRAP", "BOT_DAILY_LIMIT"):
        assert nombre in REGISTRO, f"{nombre} sin registrar en src/flags.py"
        assert REGISTRO[nombre]["lectores"] == ("src/bot/access.py",)


# ═══════════════════════════════════════════════════════════════════════════
# 8 · Los dos CRÍTICOS del dúo, y los refuerzos que pidió Alberto
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("valor", ["onn", "ON!", "sí ", "enabled", "tru", "  ",
                                   "yes please", "0n"])
def test_una_errata_en_la_variable_CIERRA_la_puerta_no_la_abre(valor, monkeypatch):
    """CRÍTICO 1. `BOT_ALLOWLIST=onn` dejaba el piloto ABIERTO a internet en
    silencio: el parser antiguo listaba los valores de encendido y todo lo demás
    caía en «apagado». Un control de acceso no puede degradar a fail-open por una
    errata de una tecla. Ahora solo un OFF RECONOCIBLE lo apaga."""
    monkeypatch.setenv("BOT_ALLOWLIST", valor)
    assert access.acceso_activo() is True, (
        f"{valor!r} apaga la puerta: una errata deja el bot abierto"
    )


@pytest.mark.parametrize("valor", ["off", "OFF", " off ", "0", "false", "no"])
def test_solo_un_apagado_explicito_apaga_la_puerta(valor, monkeypatch):
    monkeypatch.setenv("BOT_ALLOWLIST", valor)
    assert access.acceso_activo() is False


@pytest.mark.parametrize("valor", ["on", "ON", "1", "true", "yes", "si"])
def test_los_encendidos_reconocidos_siguen_encendiendo(valor, monkeypatch):
    monkeypatch.setenv("BOT_ALLOWLIST", valor)
    assert access.acceso_activo() is True


def test_el_arranque_se_niega_con_una_variable_mal_escrita(monkeypatch):
    """La otra mitad del crítico 1: cerrar es la conducta segura, pero cerrar EN
    SILENCIO deja a Alberto preguntándose por qué nadie entra. El fail-fast pone
    el valor mal escrito en el mensaje y tumba el deploy, que es donde se ve."""
    monkeypatch.setenv("BOT_ALLOWLIST", "onn")
    with pytest.raises(RuntimeError, match="BOT_ALLOWLIST"):
        access.validar_configuracion()

    monkeypatch.setenv("BOT_ALLOWLIST", "on")
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", "7777, alberto")
    with pytest.raises(RuntimeError, match="BOOTSTRAP"):
        access.validar_configuracion()

    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", "7777,4242")
    monkeypatch.setenv("BOT_DAILY_LIMIT", "treinta")
    with pytest.raises(RuntimeError, match="BOT_DAILY_LIMIT"):
        access.validar_configuracion()

    monkeypatch.setenv("BOT_DAILY_LIMIT", "30")
    access.validar_configuracion()                       # configuración sana


def test_run_bot_valida_la_configuracion_antes_de_arrancar():
    import inspect

    import src.bot.telegram_bot as bot

    fuente = inspect.getsource(bot.run_bot)
    assert "access.validar_configuracion()" in fuente
    assert fuente.index("validar_configuracion") < fuente.index("run_polling")


@pytest.mark.parametrize("tipo", ["group", "supergroup", "channel", None, "",
                                  "PRIVATE_ISH", 7])
def test_la_puerta_bloquea_todo_lo_que_no_sea_chat_privado(tipo, bot_con_puerta):
    """CRÍTICO 2. La puerta autorizaba al REMITENTE y nunca miraba DÓNDE se
    publicaría la respuesta: un DG autorizado podía meter el bot en un grupo y
    sus respuestas las leían participantes no invitados — justo lo que el red
    line del dueño prohíbe. Era una nota operativa; ahora es un control."""
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO              # autorizado y aun así NO
    u = _update("¿cómo configuro la CAD-250?")
    u.effective_chat = SimpleNamespace(id=-100123, type=tipo)

    assert _pasa_la_puerta(bot, u) is False
    assert access.MENSAJE_SOLO_PRIVADO in u.message.respuestas


def test_en_privado_el_autorizado_sigue_pasando(bot_con_puerta):
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    u = _update("¿cómo configuro la CAD-250?")
    u.effective_chat = SimpleNamespace(id=DG, type="private")
    assert _pasa_la_puerta(bot, u) is True


def test_start_en_un_grupo_no_canjea_la_invitacion(bot_con_puerta):
    """El chat se comprueba ANTES de la exención de `/start`: si no, un
    `/start <token>` tecleado en un grupo canjearía la invitación desde ahí."""
    bot, _estado = bot_con_puerta
    u = _update("/start AbCdEfGhIjKlMnOpQrStUvWxYz012345")
    u.effective_chat = SimpleNamespace(id=-100123, type="supergroup")
    assert _pasa_la_puerta(bot, u) is False


def test_al_grupo_se_le_avisa_una_vez_y_luego_se_calla(bot_con_puerta):
    """Repetir el aviso en cada mensaje sería ruido para ellos y envíos para
    nosotros; pero parar, se para siempre."""
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    avisos = 0
    for i in range(5):
        u = _update(f"mensaje {i}")
        u.effective_chat = SimpleNamespace(id=-100123, type="group")
        assert _pasa_la_puerta(bot, u) is False, "dejó de parar el grupo"
        avisos += len(u.message.respuestas)
    assert avisos == 1, f"se avisó {avisos} veces al mismo grupo"

    otro = _update("hola")
    otro.effective_chat = SimpleNamespace(id=-100999, type="group")
    _pasa_la_puerta(bot, otro)
    assert otro.message.respuestas, "un grupo NUEVO sí debe recibir su aviso"


def test_el_ciclo_completo_alta_revocacion_nueva_invitacion_alta(supabase):
    """MEDIO 3. La propuesta afirmaba que una invitación nueva devuelve el acceso
    a un revocado, y NO era cierto: se ponía `revocado_at=NULL` conservando
    `revocado_por`, lo que viola el CHECK `bot_allowlist_revocacion_completa` y
    hacía fallar el upsert entero. El doble ya aplica ese CHECK, así que este
    test caía antes del arreglo."""
    primera = access.token_nuevo()
    _invitar(supabase, primera, id_="inv-1")
    assert _canjear(primera, DG).estado == access.CANJE_OK

    # el operador revoca (lo que hace `revocar-acceso`)
    supabase.allowlist[0].update({
        "revocado_at": _iso(datetime.now(timezone.utc)),
        "revocado_por": "alberto",
        "motivo_revocacion": "fin del piloto",
    })

    segunda = access.token_nuevo()
    _invitar(supabase, segunda, id_="inv-2")
    assert _canjear(segunda, DG).estado == access.CANJE_OK, (
        "la re-admisión falla: el upsert rompe el CHECK de revocación"
    )
    fila = supabase.allowlist[0]
    assert fila["revocado_at"] is None and fila["revocado_por"] is None
    assert fila["motivo_revocacion"] is None
    assert fila["invitacion_id"] == "inv-2"


def test_un_canje_perdido_en_vuelo_libera_la_invitacion(supabase, monkeypatch):
    """MEDIO 4. Si el PATCH se confirma y se pierde la respuesta, la invitación
    quedaba quemada sin alta mientras al DG se le decía «reintenta con el mismo
    enlace». Ahora se libera best-effort por (token_hash, canjeada_por)."""
    import src.logging_db as logging_db

    token = access.token_nuevo()
    _invitar(supabase, token)

    real = supabase.patch
    llamadas = {"n": 0}

    def patch_que_se_corta(url, **kw):
        llamadas["n"] += 1
        respuesta = real(url, **kw)          # el UPDATE SÍ se aplica...
        if llamadas["n"] == 1:
            raise RuntimeError("conexión perdida tras confirmar")  # ...y se pierde
        return respuesta

    monkeypatch.setattr(supabase, "patch", patch_que_se_corta)
    assert _canjear(token, DG).estado == access.CANJE_INDETERMINADO

    invitacion = supabase.invitaciones[0]
    assert invitacion["canjeada_at"] is None, (
        "la invitación quedó quemada: el DG no puede reintentar y nadie lo sabe"
    )
    assert invitacion["canjeada_por"] is None


def test_la_liberacion_no_puede_robar_un_canje_ajeno(supabase, monkeypatch):
    """La liberación filtra por `canjeada_por`: si quien la tiene es OTRO, no se
    toca. Sin ese filtro, un fallo de transporte de una persona liberaría la
    invitación que otra acaba de ganar."""
    token = access.token_nuevo()
    _invitar(supabase, token)
    assert _canjear(token, DG).estado == access.CANJE_OK      # DG la gana

    real = supabase.patch

    def patch_que_se_corta(url, **kw):
        real(url, **kw)
        raise RuntimeError("conexión perdida")

    monkeypatch.setattr(supabase, "patch", patch_que_se_corta)
    _canjear(token, OTRO_DG)                                  # OTRO lo intenta

    assert supabase.invitaciones[0]["canjeada_por"] == DG, (
        "la liberación de OTRO soltó el canje que DG ya tenía"
    )


def test_el_mensaje_del_canje_incierto_es_verdad_en_los_dos_casos(start):
    """No puede prometer que reintentar funcionará: si el canje se confirmó, el
    enlace ya no vale. El texto tiene que cubrir ambas ramas."""
    bot, rec = start
    rec["canje"] = access.CANJE_INDETERMINADO
    u = _update("/start")
    _start(bot, u, [access.token_nuevo()])

    texto = u.message.respuestas[0]
    assert texto == access.MENSAJE_CANJE_INCIERTO
    assert "vuelve a pulsar" in texto.lower()
    assert "ya no es válido" in texto.lower() or "no es válido" in texto.lower()


def test_el_id_de_telegram_no_se_escribe_en_el_log_del_proceso():
    """MEDIO 5. Los logs de Railway están fuera de la matriz de retención y de
    cualquier supresión a petición (s295 ya sacó de ahí el texto de la consulta).
    El identificador tampoco puede vivir ahí."""
    import inspect

    import src.bot.telegram_bot as bot

    for funcion in (bot._canjear_invitacion, bot.access_gate, bot._avisar_canje):
        fuente = inspect.getsource(funcion)
        for linea in fuente.split("\n"):
            if "logger." not in linea:
                continue
            assert "user_id" not in linea, (
                f"identificador en el log del proceso: {linea.strip()}"
            )


def test_la_caducidad_por_defecto_son_dos_dias_y_el_maximo_siete():
    """REFUERZO 1 (Alberto): acorta la ventana en la que un enlace olvidado en un
    chat sigue vivo. Y el máximo hace verdadera la frase «se acota»: antes
    `--dias` aceptaba cualquier entero."""
    assert access.DIAS_CADUCIDAD_DEFECTO == 2
    assert access.DIAS_CADUCIDAD_MAX == 7

    import scripts.s324e_invitaciones as inv

    args = inv.construir_parser().parse_args(["generar", "--nota", "X"])
    assert args.dias == 2
    for malo in ("8", "365", "0", "-1"):
        with pytest.raises(SystemExit):
            inv.construir_parser().parse_args(
                ["generar", "--nota", "X", "--dias", malo])
    assert inv.construir_parser().parse_args(
        ["generar", "--nota", "X", "--dias", "7"]).dias == 7


def test_la_cota_de_caducidad_tambien_esta_en_la_base():
    """El script no es el único cliente posible de la tabla: la cota que de
    verdad garantiza la frase es el CHECK."""
    sql = (ROOT / "migrations" / "016_allowlist_invitaciones.sql").read_text(
        encoding="utf-8")
    assert "bot_invitaciones_caducidad_acotada" in sql
    assert "interval '7 days'" in sql


def test_el_aviso_de_canje_enfrenta_para_quien_era_con_quien_lo_canjeo():
    """REFUERZO 2. Es lo que convierte un reenvío en detectable en minutos."""
    texto = access.texto_aviso_canje(
        nota="Juan Pérez, DG de Acme", nombre="Marta Ruiz",
        alias="martaruiz", telegram_user_id=987654321,
    )
    assert "Juan Pérez, DG de Acme" in texto          # para quién era
    assert "Marta Ruiz" in texto and "@martaruiz" in texto   # quién lo canjeó
    assert "987654321" in texto                       # con qué revocar
    assert "revocar-acceso 987654321" in texto


def test_el_aviso_de_canje_llega_a_quien_administra(start, monkeypatch):
    bot, rec = start
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", f"{ALBERTO},4242")
    enviados = []

    class _Bot:
        async def send_message(self, chat_id, text, **_k):
            enviados.append((chat_id, text))

    contexto = SimpleNamespace(args=[access.token_nuevo()], bot=_Bot())
    u = _update("/start")
    asyncio.run(bot.start_command(u, contexto))

    assert [c for c, _t in enviados] == [4242, ALBERTO]
    assert "Invitación canjeada" in enviados[0][1]
    assert "Juan Perez, DG de Acme" in enviados[0][1]


def test_sin_administradores_configurados_el_alta_se_hace_igual(start):
    """Un aviso no puede ser un requisito para dar de alta."""
    bot, rec = start
    contexto = SimpleNamespace(args=[access.token_nuevo()], bot=None)
    u = _update("/start")
    asyncio.run(bot.start_command(u, contexto))
    assert access.MENSAJE_INVITACION_ACEPTADA in u.message.respuestas[0]
    assert "/accept" in u.message.respuestas[1]


def test_si_el_aviso_falla_el_alta_sigue_y_pasa_por_el_punto_unico(
        start, monkeypatch):
    bot, rec = start
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", str(ALBERTO))
    reportados = []

    async def _reportar(update, exc, **kwargs):
        reportados.append((update, type(exc).__name__, kwargs.get("etapa")))
        return "cod"

    monkeypatch.setattr(bot, "_reportar_error", _reportar)

    class _BotRoto:
        async def send_message(self, **_k):
            raise RuntimeError("Telegram dice que no")

    u = _update("/start")
    asyncio.run(bot.start_command(
        u, SimpleNamespace(args=[access.token_nuevo()], bot=_BotRoto())))

    assert access.MENSAJE_INVITACION_ACEPTADA in u.message.respuestas[0], \
        "un aviso fallido rompió el canje"
    assert "/accept" in u.message.respuestas[1]
    assert reportados and reportados[0][2] == "aviso_canje"
    # `update=None`: la incidencia se registra pero al DG NO se le contesta nada
    # — su alta fue bien y el fallo no es suyo.
    assert reportados[0][0] is None


def test_la_peor_latencia_de_una_revocacion_es_la_declarada():
    """REFUERZO 3, medido. Dos números, porque son dos casos:
      · base sana  → el TTL de la caché (10 min);
      · base caída → el TTL + la gracia degradada.
    El informe decía «≤10 min» a secas y se dejaba el segundo, que era 24 h."""
    t0 = 0.0
    assert access.decidir(DG, _responde(access.AUTORIZADO), ahora=t0).permitido

    revocado = _responde(access.DESCONOCIDO)
    assert access.decidir(DG, revocado, ahora=599.0).permitido
    assert not access.decidir(DG, revocado, ahora=601.0).permitido
    assert access.TTL_FRESCO_S == 600, "cambió la latencia con base sana"

    access.reiniciar_cache()
    assert access.decidir(DG, _responde(access.AUTORIZADO), ahora=t0).permitido
    caida = _responde(access.INDETERMINADO)
    assert access.decidir(DG, caida, ahora=3599.0).permitido
    assert not access.decidir(DG, caida, ahora=3601.0).permitido
    assert access.GRACIA_DEGRADADA_S == 3600, (
        "cambió la peor latencia de revocación: actualiza el informe, el script "
        "y DG_DEPLOYMENT — los tres la citan"
    )


def test_un_turno_en_curso_termina_pero_el_siguiente_ya_no_pasa(bot_con_puerta):
    """«Revocado con turno en curso»: la puerta decide POR UPDATE. El turno que
    ya pasó termina (no se puede des-enviar una respuesta); el corte llega en el
    mensaje siguiente, no a mitad del que se está respondiendo."""
    bot, estado = bot_con_puerta
    estado["valor"] = access.AUTORIZADO
    assert _pasa_la_puerta(bot, _update("pregunta larga")) is True

    estado["valor"] = access.DESCONOCIDO              # revocado a mitad
    access.reiniciar_cache()                          # + el TTL ya vencido
    siguiente = _update("¿y el consumo?")
    assert _pasa_la_puerta(bot, siguiente) is False
    assert siguiente.message.respuestas


def test_la_revocacion_no_alcanza_a_los_ids_de_bootstrap(monkeypatch):
    """Trampa declarada: `revocar-acceso` escribe en la base, y el bootstrap no
    pasa por la base. El script lo avisa; aquí se ancla la conducta."""
    monkeypatch.setenv("BOT_ALLOWLIST_BOOTSTRAP", str(ALBERTO))
    revocado_en_base = _responde(access.DESCONOCIDO)
    assert access.decidir(ALBERTO, revocado_en_base).permitido
    assert revocado_en_base.llamadas == []


def test_access_es_una_hoja_pura():
    """Sin I/O, sin red y sin SDK: es lo que permite probar la puerta entera sin
    Supabase (mismo contrato que `error_taxonomy`)."""
    fuente = (ROOT / "src" / "bot" / "access.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    prohibidos = {"httpx", "telegram", "anthropic", "openai", "supabase",
                  "requests", "voyageai"}
    assert not (importados & prohibidos), (
        f"`access` dejó de ser una hoja pura: importa {importados & prohibidos}"
    )
