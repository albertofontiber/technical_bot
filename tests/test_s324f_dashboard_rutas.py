# -*- coding: utf-8 -*-
"""s324f — El panel por fuera: la puerta, el CSRF, las cabeceras y el render.

LO QUE ESTE FICHERO PRUEBA DE VERDAD, y por qué merece la pena decirlo: se
ejercita la aplicación ASGI ENTERA —la misma función que servirá uvicorn en
Railway— en proceso y sin socket. No hay red de ningún tipo: Supabase entra por
un doble que devuelve filas de mentira, así que estos tests corren en un entorno
limpio, sin claves y sin instalar un servidor.

Los cuatro invariantes que no se pueden romper sin que este fichero se ponga
rojo:
  1. NINGUNA ruta responde contenido sin sesión (ni una de métricas, ni un
     ping): sin cookie válida sólo hay redirección a la entrada;
  2. toda escritura exige origen propio Y token CSRF de ESA sesión;
  3. la clave de servicio de Supabase no aparece en ninguna respuesta —
     ni en el cuerpo ni en una cabecera;
  4. si Supabase no contesta, la página sigue saliendo y DICE que no contesta,
     en vez de un 500 con traza.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import pytest

from dashboard import app as panel
from dashboard import auth, datos, gestion, sesion

SECRETO = "secreto-de-pruebas-con-longitud-mas-que-suficiente"
CLAVE_SERVICIO = "CLAVE-DE-SERVICIO-QUE-NO-DEBE-SALIR-JAMAS"
ANFITRION = "panel.pruebas"


# --------------------------------------------------------------- cliente ASGI


@dataclass
class Respuesta:
    estado: int
    cabeceras: list
    cuerpo: bytes

    @property
    def texto(self) -> str:
        return self.cuerpo.decode("utf-8")

    def cabecera(self, nombre: str) -> str | None:
        for clave, valor in self.cabeceras:
            if clave == nombre.lower():
                return valor
        return None

    def todas(self, nombre: str) -> list:
        return [v for k, v in self.cabeceras if k == nombre.lower()]


class Cliente:
    """Habla ASGI directamente con `panel.app`. Sin httpx y sin socket."""

    def __init__(self, cookie: str | None = None) -> None:
        self.cookie = cookie

    def _pedir(self, metodo, ruta, *, cuerpo=b"", cabeceras=None,
               consulta="") -> Respuesta:
        cab = {"host": ANFITRION}
        if metodo == "POST":
            cab["content-type"] = "application/x-www-form-urlencoded"
            cab["origin"] = f"https://{ANFITRION}"
        if self.cookie:
            cab["cookie"] = f"{sesion.NOMBRE_COOKIE}={self.cookie}"
        cab.update(cabeceras or {})
        cab = {k: v for k, v in cab.items() if v is not None}

        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": metodo, "path": ruta, "raw_path": ruta.encode(),
            "query_string": consulta.encode(), "root_path": "", "scheme": "https",
            "client": ("203.0.113.9", 51234), "server": (ANFITRION, 443),
            "headers": [(k.encode("latin-1"), str(v).encode("latin-1"))
                        for k, v in cab.items()],
        }
        salida = []

        async def receive():
            return {"type": "http.request", "body": cuerpo, "more_body": False}

        async def send(mensaje):
            salida.append(mensaje)

        asyncio.run(panel.app(scope, receive, send))
        inicio = salida[0]
        cabeceras_salida = [(k.decode("latin-1").lower(), v.decode("latin-1"))
                            for k, v in inicio["headers"]]
        return Respuesta(inicio["status"], cabeceras_salida,
                         b"".join(m.get("body", b"") for m in salida[1:]))

    def get(self, ruta, *, consulta="", cabeceras=None) -> Respuesta:
        return self._pedir("GET", ruta, consulta=consulta, cabeceras=cabeceras)

    def post(self, ruta, campos: dict | None = None, *,
             cabeceras=None, cuerpo=None) -> Respuesta:
        import urllib.parse
        if cuerpo is None:
            cuerpo = urllib.parse.urlencode(campos or {}).encode("utf-8")
        return self._pedir("POST", ruta, cuerpo=cuerpo, cabeceras=cabeceras)


# ------------------------------------------------------------------- dobles

FILAS = {
    "bot_health_daily": [
        {"dia": "2026-08-17", "bot_version": "s324e", "consultas_rag": 12,
         "usuarios_unicos": 3, "latencia_pipeline_p50_ms": 21000,
         "latencia_pipeline_p95_ms": 41000, "no_info_heuristica": 1,
         "errores_transporte": 0, "filas_error": 2},
        {"dia": "2026-08-16", "bot_version": "s324e", "consultas_rag": 7,
         "usuarios_unicos": 2, "latencia_pipeline_p50_ms": 19000,
         "latencia_pipeline_p95_ms": 38000, "no_info_heuristica": 0,
         "errores_transporte": 0, "filas_error": 0},
    ],
    "bot_health_semanal": [
        {"semana": "2026-08-10", "consultas_rag": 41, "usuarios_unicos": 4,
         "latencia_pipeline_p50_ms": 20000, "latencia_pipeline_p95_ms": 39000,
         "no_info_heuristica": 3, "filas_error": 2},
    ],
    "bot_uso_por_canal": [
        {"semana": "2026-08-10", "canal": "rag", "consultas": 39, "personas": 4},
        {"semana": "2026-08-10", "canal": "clarify", "consultas": 2, "personas": 1},
    ],
    "bot_feedback_semanal": [
        {"semana": "2026-08-10", "votos_up": 5, "votos_down": 2,
         "votos_down_con_motivo": 2, "votos_con_comentario": 1,
         "marcados_utiles": 1, "feedback_libre": 0},
    ],
    "bot_motivos_negativos": [
        {"semana": "2026-08-10", "motivo": "info", "votos": 2},
    ],
    "salud_canal_retrieval_v1": [
        {"dia": "2026-08-17", "turnos_rag": 12, "turnos_con_medida": 12,
         "pct_turnos_degradados": 8.3, "turnos_degradados": 1,
         "fallos_vector": 0, "fallos_enunciados": 1, "fallos_hyq_table": 0,
         "fallos_hyq_hydrate": 0},
    ],
    "salud_latencia_etapas_v1": [
        {"dia": "2026-08-17", "turnos_rag": 12, "turnos_con_medida": 12,
         "total_p50_ms": 21000, "total_p95_ms": 41000,
         "total_p50_ms_medidos": 21000, "retrieve_p50_ms": 3000,
         "rerank_p50_ms": 2000, "coverage_p50_ms": 1000,
         "generate_p50_ms": 14000, "resto_p50_ms": 1000},
    ],
    "bot_allowlist": [
        {"telegram_user_id": 111222333, "nota": "Juan Pérez, DG de Acme",
         "origen": "invitacion", "alta_por": "panel:alberto",
         "alta_at": "2026-08-17T09:00:00Z", "revocado_at": None,
         "revocado_por": None, "motivo_revocacion": None},
        {"telegram_user_id": 444555666, "nota": "Antiguo piloto",
         "origen": "manual", "alta_por": "cli:alberto",
         "alta_at": "2026-07-01T09:00:00Z",
         "revocado_at": "2026-08-01T09:00:00Z", "revocado_por": "cli:alberto",
         "motivo_revocacion": "fin"},
    ],
    "bot_invitaciones": [
        {"id": "3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8", "nota": "Ana, DG de Beta",
         "creada_por": "panel:alberto", "creada_at": "2026-08-17T08:00:00Z",
         "expira_at": "2099-01-01T00:00:00Z", "canjeada_at": None,
         "canjeada_por": None, "revocada_at": None},
        {"id": "9c8b7a6d-5e4f-4a3b-9c8d-7e6f5a4b3c2d", "nota": "Luis, DG de Gamma",
         "creada_por": "cli:alberto", "creada_at": "2026-08-15T08:00:00Z",
         "expira_at": "2026-08-16T00:00:00Z", "canjeada_at":
             "2026-08-15T10:00:00Z", "canjeada_por": 111222333,
         "revocada_at": None},
    ],
    "bot_errors": [
        {"codigo": "E1", "clase": "red", "severidad": "aviso",
         "reintentable": True, "tipo_excepcion": "ReadTimeout",
         "etapa": "generate", "origen": "src/rag/answer.py:120",
         "mensaje_corto": "timeout", "usuario_avisado": True,
         "bot_version": "s324e", "created_at": "2026-08-17T10:00:00Z",
         "query_logs": {"query": "¿Cuántos lazos tiene la CAD-150?",
                        "telegram_user_id": 111222333}},
    ],
    "query_logs": [
        {"query": "sensor de humo direccionable", "response": "ValueError@rerank",
         "telegram_user_id": 111222333, "created_at": "2026-08-10T10:00:00Z"},
    ],
}


def _leer_doble(recurso, params):
    filas = FILAS.get(recurso)
    if filas is None:
        return datos.Resultado(datos.TABLA_AUSENTE, detalle=recurso)
    return datos.Resultado(datos.OK if filas else datos.VACIO, list(filas))


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Todo el mundo con el mismo suelo: secreto puesto, Supabase fingido, y la
    clave de servicio con un valor CENTINELA que ninguna respuesta puede tener."""
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, SECRETO)
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "PCI_Soporte_tecnico_bot")
    monkeypatch.setattr(datos, "SUPABASE_SERVICE_KEY", CLAVE_SERVICIO)
    monkeypatch.setattr(datos, "SUPABASE_URL", "https://proyecto.supabase.co")
    monkeypatch.setattr(gestion, "SUPABASE_SERVICE_KEY", CLAVE_SERVICIO)
    monkeypatch.setattr(gestion, "SUPABASE_URL", "https://proyecto.supabase.co")
    monkeypatch.setattr(datos, "leer", _leer_doble)
    panel._cerrojo.reiniciar()
    yield
    panel._cerrojo.reiniciar()


@pytest.fixture
def usuario(monkeypatch):
    """Un backend de autenticación de mentira: la interfaz enchufable de
    DEC-231 §3 usada para lo que existe — sustituir el backend sin tocar rutas."""

    class Doble:
        def autenticar(self, usuario, contrasena):
            if usuario.strip().lower() == "alberto" and contrasena == "correcta":
                return auth.Usuario(nombre="alberto")
            return None

    anterior = auth.usar_backend(Doble())
    yield
    auth.usar_backend(anterior)


def _sesion_valida(nombre="alberto", **kwargs) -> str:
    payload = sesion.nueva(nombre, **kwargs)
    return sesion.firmar(payload, SECRETO.encode("utf-8"))


def _con_sesion(nombre="alberto") -> tuple[Cliente, str]:
    payload = sesion.nueva(nombre)
    cookie = sesion.firmar(payload, SECRETO.encode("utf-8"))
    return Cliente(cookie), payload["csrf"]


RUTAS_PROTEGIDAS = [c for c in panel.RUTAS if c not in panel.RUTAS_PUBLICAS]


def _sin_nonce(respuesta: Respuesta) -> str:
    """El cuerpo con el nonce de la CSP normalizado, para poder comparar dos
    respuestas que sólo pueden diferir en eso."""
    import re
    return re.sub(r'nonce="[^"]+"', 'nonce="N"', respuesta.texto)


# ------------------------------------------------------------------- la puerta


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_ninguna_ruta_responde_sin_sesion(metodo, ruta):
    """EL invariante. Se recorre la tabla de rutas real, no una lista escrita a
    mano: una ruta nueva que alguien añada sin sesión entra sola en este test."""
    cliente = Cliente()
    respuesta = (cliente.get(ruta) if metodo == "GET"
                 else cliente.post(ruta, {}))
    assert respuesta.estado == 303, f"{metodo} {ruta} no redirige a la entrada"
    assert respuesta.cabecera("location") == "/entrar"
    assert respuesta.cuerpo == b""


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_sin_sesion_no_se_filtra_ningun_dato(metodo, ruta):
    cliente = Cliente()
    respuesta = (cliente.get(ruta) if metodo == "GET"
                 else cliente.post(ruta, {}))
    texto = respuesta.texto + str(respuesta.cabeceras)
    for rastro in ("Juan Pérez", "111222333", "Ana, DG de Beta", "lazos"):
        assert rastro not in texto


def test_la_entrada_es_lo_unico_publico():
    respuesta = Cliente().get("/entrar")
    assert respuesta.estado == 200
    assert 'name="usuario"' in respuesta.texto
    assert "111222333" not in respuesta.texto


def test_ruta_desconocida_es_404_sin_pistas():
    respuesta = Cliente().get("/admin.php")
    assert respuesta.estado == 404
    assert "Juan" not in respuesta.texto


# ------------------------------------------------------------------ el login


def test_login_correcto_abre_sesion_con_cookie_endurecida(usuario):
    respuesta = Cliente().post("/entrar",
                               {"usuario": "alberto", "contrasena": "correcta"})
    assert respuesta.estado == 303
    assert respuesta.cabecera("location") == "/"
    cookie = respuesta.cabecera("set-cookie")
    assert cookie.startswith(f"{sesion.NOMBRE_COOKIE}=")
    for atributo in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/", "Max-Age="):
        assert atributo in cookie


def test_login_malo_no_distingue_usuario_inexistente(usuario):
    mala = Cliente().post("/entrar",
                          {"usuario": "alberto", "contrasena": "otra"})
    fantasma = Cliente().post("/entrar",
                              {"usuario": "nadie", "contrasena": "otra"})
    assert mala.estado == fantasma.estado == 401
    assert "Usuario o contraseña incorrectos" in mala.texto
    # Byte a byte, salvo el nonce de la CSP (que es distinto por respuesta a
    # propósito): la respuesta no puede decir si el usuario existe.
    assert _sin_nonce(mala) == _sin_nonce(fantasma)
    assert mala.cabecera("set-cookie") is None


def test_fuerza_bruta_acaba_bloqueando(usuario):
    cliente = Cliente()
    for _ in range(auth.FALLOS_LIBRES + 1):
        assert cliente.post("/entrar", {"usuario": "alberto",
                                        "contrasena": "mala"}).estado == 401
    bloqueada = cliente.post("/entrar", {"usuario": "alberto",
                                         "contrasena": "correcta"})
    assert bloqueada.estado == 429
    assert "Demasiados intentos" in bloqueada.texto
    # Y el bloqueo tapa incluso la contraseña BUENA: si no, el cerrojo sólo
    # estorbaría a quien se equivoca y no al que prueba.
    assert bloqueada.cabecera("set-cookie") is None


def test_salir_borra_la_cookie():
    cliente, csrf = _con_sesion()
    respuesta = cliente.post("/salir", {"csrf": csrf})
    assert respuesta.estado == 303
    assert "Max-Age=0" in respuesta.cabecera("set-cookie")


# ------------------------------------------------------------------- sesión


def test_sesion_caducada_no_entra():
    cookie = _sesion_valida(ahora=time.time() - 100_000, duracion=3600)
    assert Cliente(cookie).get("/").estado == 303


def test_sesion_manipulada_no_entra():
    cookie = _sesion_valida()
    cuerpo, _, firma = cookie.partition(".")
    falsa = f"{cuerpo[:-2]}XY.{firma}"
    assert Cliente(falsa).get("/").estado == 303


def test_cookie_de_otro_secreto_no_entra():
    payload = sesion.nueva("intruso")
    cookie = sesion.firmar(payload, b"otro-secreto-completamente-distinto-x")
    assert Cliente(cookie).get("/").estado == 303


# ---------------------------------------------------------------------- CSRF


ESCRITURAS = [
    ("/acceso/invitar", {"nota": "Test", "dias": "2"}),
    ("/acceso/anular-invitacion",
     {"invitacion_id": "3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8"}),
    ("/acceso/revocar", {"telegram_user_id": "111222333"}),
    ("/salir", {}),
]


@pytest.mark.parametrize("ruta,campos", ESCRITURAS)
def test_escritura_sin_csrf_es_403(ruta, campos):
    cliente, _ = _con_sesion()
    assert cliente.post(ruta, campos).estado == 403


@pytest.mark.parametrize("ruta,campos", ESCRITURAS)
def test_escritura_con_csrf_de_otra_sesion_es_403(ruta, campos):
    cliente, _ = _con_sesion()
    _, csrf_ajeno = _con_sesion("otro")
    assert cliente.post(ruta, {**campos, "csrf": csrf_ajeno}).estado == 403


@pytest.mark.parametrize("ruta,campos", ESCRITURAS)
def test_escritura_desde_otro_origen_es_403(ruta, campos):
    cliente, csrf = _con_sesion()
    respuesta = cliente.post(ruta, {**campos, "csrf": csrf},
                             cabeceras={"origin": "https://malo.example"})
    assert respuesta.estado == 403


def test_login_desde_otro_origen_es_403(usuario):
    """El formulario de entrada no puede llevar token de sesión (todavía no hay
    sesión), así que el control de origen es EL que cubre el login CSRF."""
    respuesta = Cliente().post("/entrar",
                               {"usuario": "alberto", "contrasena": "correcta"},
                               cabeceras={"origin": "https://malo.example"})
    assert respuesta.estado == 403
    assert respuesta.cabecera("set-cookie") is None


def test_post_sin_origen_ni_referer_es_403():
    cliente, csrf = _con_sesion()
    respuesta = cliente.post("/salir", {"csrf": csrf},
                             cabeceras={"origin": None, "referer": None})
    assert respuesta.estado == 403


# ------------------------------------------------------------------ escrituras


def test_invitar_muestra_el_enlace_una_vez_y_nunca_en_la_url(monkeypatch):
    creada = []

    def escribir_doble(metodo, tabla, *, params=None, json=None):
        creada.append((metodo, tabla, json))
        return datos.OK, [{"id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                           **(json or {})}], ""

    monkeypatch.setattr(gestion, "_escribir", escribir_doble)
    cliente, csrf = _con_sesion()
    respuesta = cliente.post("/acceso/invitar",
                             {"csrf": csrf, "nota": "Ana, DG de Beta",
                              "dias": "2"})
    assert respuesta.estado == 200
    assert "https://t.me/PCI_Soporte_tecnico_bot?start=" in respuesta.texto
    # El enlace no viaja en una redirección: no hay Location que pueda acabar en
    # el historial del navegador o en el log de un proxy.
    assert respuesta.cabecera("location") is None
    # Y a la base va la HUELLA, nunca el token.
    _, tabla, enviado = creada[0]
    assert tabla == "bot_invitaciones"
    assert len(enviado["token_hash"]) == 64
    assert "start=" not in str(enviado)


def test_invitar_sin_nota_no_escribe_nada(monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("no se puede escribir sin nota")

    monkeypatch.setattr(gestion, "_escribir", prohibido)
    cliente, csrf = _con_sesion()
    respuesta = cliente.post("/acceso/invitar",
                             {"csrf": csrf, "nota": "  ", "dias": "2"})
    assert respuesta.estado == 200
    assert "para quién es" in respuesta.texto


def test_revocar_acceso_avisa_de_las_invitaciones_pendientes(monkeypatch):
    monkeypatch.setattr(
        gestion, "_escribir",
        lambda *a, **k: (datos.OK, [{"nota": "Juan Pérez, DG de Acme"}], ""))
    cliente, csrf = _con_sesion()
    respuesta = cliente.post("/acceso/revocar",
                             {"csrf": csrf, "telegram_user_id": "111222333"})
    assert respuesta.estado == 200
    assert "Acceso revocado" in respuesta.texto
    assert "PENDIENTES" in respuesta.texto


# ------------------------------------------------------------------ el render


@pytest.mark.parametrize("ruta,esperado", [
    ("/", "Salud del panel"),
    ("/acceso", "Quién puede usar el bot"),
    ("/metricas", "Dónde se va el tiempo"),
    ("/errores", "Las preguntas que más fallan"),
])
def test_cada_pagina_se_pinta_con_datos_dobles(ruta, esperado):
    cliente, _ = _con_sesion()
    respuesta = cliente.get(ruta)
    assert respuesta.estado == 200
    assert esperado in respuesta.texto


def test_las_siete_vistas_aparecen_en_metricas():
    cliente, _ = _con_sesion()
    texto = cliente.get("/metricas").texto
    for vista in datos.VISTAS:
        assert vista.clave in texto, f"falta {vista.clave}"


def test_texto_de_persona_va_escapado(monkeypatch):
    """Una nota con HTML dentro se PINTA, no se ejecuta. Es el camino por el que
    entra texto de fuera: la nota la escribe una persona."""
    filas = dict(FILAS)
    filas["bot_allowlist"] = [{
        "telegram_user_id": 1, "nota": "<script>alert(1)</script>",
        "origen": "manual", "alta_por": "x", "alta_at": "2026-08-17T09:00:00Z",
        "revocado_at": None,
    }]
    monkeypatch.setattr(
        datos, "leer",
        lambda recurso, params: datos.Resultado(
            datos.OK, list(filas.get(recurso, []))) if filas.get(recurso)
        else datos.Resultado(datos.TABLA_AUSENTE, detalle=recurso))
    cliente, _ = _con_sesion()
    texto = cliente.get("/acceso").texto
    assert "<script>alert(1)</script>" not in texto
    assert "&lt;script&gt;" in texto


def test_la_pregunta_de_un_tecnico_se_recorta():
    cliente, _ = _con_sesion()
    texto = cliente.get("/errores").texto
    assert "Texto escrito por técnicos" in texto


# --------------------------------------------------------------- degradación


def test_supabase_caido_no_tumba_ninguna_pagina(monkeypatch):
    monkeypatch.setattr(
        datos, "leer",
        lambda recurso, params: datos.Resultado(
            datos.ERROR, detalle="no se pudo hablar con Supabase (ConnectError)"))
    cliente, _ = _con_sesion()
    for ruta in ("/", "/acceso", "/metricas", "/errores"):
        respuesta = cliente.get(ruta)
        assert respuesta.estado == 200, ruta
        assert "No se puede leer" in respuesta.texto or \
               "No se pudo leer" in respuesta.texto, ruta


def test_migracion_sin_aplicar_se_dice_con_su_nombre(monkeypatch):
    monkeypatch.setattr(
        datos, "leer",
        lambda recurso, params: datos.Resultado(datos.TABLA_AUSENTE,
                                                detalle=recurso))
    cliente, _ = _con_sesion()
    assert "016_allowlist_invitaciones.sql" in cliente.get("/acceso").texto


def test_vista_vacia_no_es_un_fallo(monkeypatch):
    monkeypatch.setattr(
        datos, "leer",
        lambda recurso, params: datos.Resultado(datos.VACIO, []))
    cliente, _ = _con_sesion()
    respuesta = cliente.get("/metricas")
    assert respuesta.estado == 200
    assert "No es un fallo" in respuesta.texto


# ------------------------------------------------------------- las cabeceras


TODAS_LAS_RESPUESTAS = [
    ("publica", lambda: Cliente().get("/entrar")),
    ("redireccion", lambda: Cliente().get("/")),
    ("404", lambda: Cliente().get("/no-existe")),
    ("pagina", lambda: _con_sesion()[0].get("/")),
    ("403", lambda: _con_sesion()[0].post("/salir", {})),
]


@pytest.mark.parametrize("nombre,hacer", TODAS_LAS_RESPUESTAS)
def test_cabeceras_de_seguridad_en_toda_respuesta(nombre, hacer):
    respuesta = hacer()
    csp = respuesta.cabecera("content-security-policy")
    assert csp and "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert respuesta.cabecera("x-content-type-options") == "nosniff"
    # (s324f, tras probarlo en un navegador de verdad) `same-origin`, no
    # `no-referrer`: con `no-referrer` el panel se quedaba sin `Referer` en sus
    # PROPIOS formularios y el control de origen rechazaba el login legítimo con
    # un 403. Frente a terceros protege igual —la URL no sale del panel—; hacia
    # dentro devuelve la señal que su propia defensa necesitaba.
    assert respuesta.cabecera("referrer-policy") == "same-origin"
    assert "no-store" in respuesta.cabecera("cache-control")
    assert respuesta.cabecera("strict-transport-security")


def test_la_csp_no_permite_javascript_ni_estilos_sueltos():
    respuesta = _con_sesion()[0].get("/")
    csp = respuesta.cabecera("content-security-policy")
    assert "unsafe-inline" not in csp
    assert "script-src" not in csp          # lo cubre default-src 'none'
    # El <style> del documento va con el nonce de ESTA respuesta.
    nonce = csp.split("style-src 'nonce-")[1].split("'")[0]
    assert f'<style nonce="{nonce}">' in respuesta.texto


def test_sin_atributos_style_en_el_html():
    """Un `style="..."` obligaría a abrir la CSP con `unsafe-inline`. Las barras
    de los gráficos llevan la geometría en atributos SVG justamente por esto."""
    cliente, _ = _con_sesion()
    for ruta in ("/", "/acceso", "/metricas", "/errores"):
        assert 'style="' not in cliente.get(ruta).texto, ruta


# ------------------------------------------------------------------ el secreto


def _todas_las_respuestas_del_panel(cliente, csrf):
    yield cliente.get("/")
    yield cliente.get("/acceso")
    yield cliente.get("/metricas")
    yield cliente.get("/errores")
    yield cliente.get("/errores", consulta="dias=30")
    yield cliente.get("/entrar")
    yield cliente.get("/no-existe")
    yield cliente.post("/acceso/invitar", {"csrf": csrf, "nota": "x", "dias": "2"})
    yield cliente.post("/acceso/revocar",
                       {"csrf": csrf, "telegram_user_id": "111222333"})


def test_la_clave_de_servicio_no_sale_en_ninguna_respuesta(monkeypatch):
    """El requisito no negociable, convertido en trinquete: si alguien pinta un
    volcado de diagnóstico con las cabeceras dentro, este test se pone rojo."""
    monkeypatch.setattr(
        gestion, "_escribir",
        lambda *a, **k: (datos.ERROR, [], "Supabase respondió 500"))
    cliente, csrf = _con_sesion()
    for respuesta in _todas_las_respuestas_del_panel(cliente, csrf):
        completo = respuesta.texto + str(respuesta.cabeceras)
        assert CLAVE_SERVICIO not in completo
        assert "supabase.co" not in completo


def test_un_fallo_inesperado_no_ensena_la_traza(monkeypatch):
    def revienta(*args, **kwargs):
        raise RuntimeError("secreto interno en el mensaje")

    # Se sustituye la ENTRADA de la tabla de rutas, no el nombre del módulo: el
    # diccionario guarda la función que había al importar.
    monkeypatch.setitem(panel.RUTAS, ("GET", "/"), revienta)
    cliente, _ = _con_sesion()
    respuesta = cliente.get("/")
    assert respuesta.estado == 500
    assert "secreto interno" not in respuesta.texto
    assert "Traceback" not in respuesta.texto


# --------------------------------------------------------- higiene del ASGI


def test_cuerpo_gigante_se_rechaza():
    cliente, _ = _con_sesion()
    respuesta = cliente.post("/salir", cuerpo=b"x" * (panel.CUERPO_MAX_BYTES + 10))
    assert respuesta.estado == 413


def test_tipo_de_envio_no_admitido():
    cliente, _ = _con_sesion()
    respuesta = cliente.post("/salir", {},
                             cabeceras={"content-type": "application/json"})
    assert respuesta.estado == 415


def test_head_no_devuelve_cuerpo():
    cliente, _ = _con_sesion()
    respuesta = cliente._pedir("HEAD", "/entrar")
    assert respuesta.estado == 200
    assert respuesta.cuerpo == b""


def test_ip_de_cliente_toma_el_ultimo_salto():
    """El cerrojo por IP se apoya en esto: con un solo proxy de confianza
    delante, el valor bueno es el ÚLTIMO, no el primero (que lo escribe quien
    quiera)."""
    cabeceras = {"x-forwarded-for": "1.2.3.4, 198.51.100.7"}
    assert panel._ip_cliente(cabeceras, "10.0.0.1") == "198.51.100.7"
    assert panel._ip_cliente({}, "10.0.0.1") == "10.0.0.1"


def test_el_arranque_falla_sin_secreto(monkeypatch):
    monkeypatch.delenv(sesion.VARIABLE_SECRETO, raising=False)
    with pytest.raises(RuntimeError, match="DASHBOARD_SECRET"):
        panel.comprobar_arranque()


# ───────────── s324f · el control de origen NO puede rechazar un login legítimo
#
# Cazado abriendo el panel en un navegador real: el POST del formulario propio
# se quedaba sin `Origin` (normal en same-origin) y sin `Referer` (lo suprimía
# la propia cabecera `Referrer-Policy: no-referrer` del panel), así que moría en
# su propia defensa con un 403 que no explicaba nada. Ningún test lo veía porque
# todos mandaban `Origin` a mano.

import pytest as _pytest


@_pytest.mark.parametrize("cabeceras, pasa, caso", [
    ({"sec-fetch-site": "same-origin"}, True,  "formulario del propio panel"),
    ({"sec-fetch-site": "none"},        True,  "URL tecleada a mano"),
    ({"sec-fetch-site": "cross-site",
      "origin": "https://malo.example"}, False, "ATAQUE desde otro sitio"),
    ({"sec-fetch-site": "same-site"},   False, "subdominio vecino"),
    ({"origin": "http://panel.local"},  True,  "navegador viejo, con Origin"),
    ({"referer": "http://panel.local/entrar"}, True, "navegador viejo, con Referer"),
    ({},                                False, "cliente sin ninguna señal"),
])
def test_mismo_origen_cubre_el_navegador_real(cabeceras, pasa, caso):
    from dashboard.app import Peticion, _mismo_origen

    peticion = Peticion(
        metodo="POST", ruta="/entrar", consulta={},
        cabeceras={"host": "panel.local", **cabeceras},
        cuerpo=b"", ip="1.2.3.4",
    )
    assert _mismo_origen(peticion) is pasa, caso


def test_sec_fetch_site_manda_sobre_un_origin_falsificado():
    """`Sec-Fetch-Site` la escribe el NAVEGADOR y no se puede falsear desde otro
    sitio; `Origin` sí lo controla quien monta la petición. Si dicen cosas
    distintas, gana la que no se puede mentir."""
    from dashboard.app import Peticion, _mismo_origen

    peticion = Peticion(
        metodo="POST", ruta="/entrar", consulta={},
        cabeceras={"host": "panel.local", "sec-fetch-site": "cross-site",
                   "origin": "http://panel.local"},
        cuerpo=b"", ip="1.2.3.4",
    )
    assert _mismo_origen(peticion) is False
