# -*- coding: utf-8 -*-
"""s324f — La autenticación del panel por dentro: hash, cerrojo y sesión.

Todo lo de aquí es OFFLINE y determinista: `dashboard.auth` y `dashboard.sesion`
son hojas puras (biblioteca estándar y nada más), así que se prueban enteras sin
red, sin Supabase y sin servidor. Es a propósito — la puerta de un panel con
datos personales dentro no puede depender de un entorno para poder verificarse.

Los parámetros de scrypt viajan DENTRO del registro, así que estos tests usan
`n=1024` (el mínimo aceptado) y corren en milisegundos sin tocar los de
producción, que son `n=32768`.
"""
from __future__ import annotations

import time

import pytest

from dashboard import auth, sesion

BARATO = {"n": 1024, "r": 8, "p": 1}
SECRETO = b"secreto-de-pruebas-con-longitud-mas-que-suficiente"


# -------------------------------------------------------------------- el hash


def test_la_contrasena_correcta_verifica_y_la_mala_no():
    registro = auth.hash_contrasena("tres palabras al azar", **BARATO)
    assert auth.verificar("tres palabras al azar", registro)
    assert not auth.verificar("tres palabras al azaR", registro)
    assert not auth.verificar("", registro)


def test_dos_registros_de_la_misma_contrasena_son_distintos():
    """La sal es aleatoria: dos personas con la misma contraseña no comparten
    hash, y una tabla robada no delata que la comparten."""
    uno = auth.hash_contrasena("misma", **BARATO)
    otro = auth.hash_contrasena("misma", **BARATO)
    assert uno != otro
    assert auth.verificar("misma", uno) and auth.verificar("misma", otro)


def test_el_registro_no_contiene_la_contrasena():
    registro = auth.hash_contrasena("clave-secreta-larguisima", **BARATO)
    assert "clave-secreta-larguisima" not in registro
    assert registro.startswith("scrypt$n=1024,r=8,p=1$")


def test_los_parametros_viajan_en_el_registro():
    """Subir el coste mañana no puede invalidar los hashes de hoy."""
    viejo = auth.hash_contrasena("x", n=1024, r=8, p=1)
    nuevo = auth.hash_contrasena("x", n=2048, r=8, p=1)
    assert auth.verificar("x", viejo) and auth.verificar("x", nuevo)


@pytest.mark.parametrize("basura", [
    "", "   ", "no-es-un-registro", "scrypt$n=1024$sal",
    "bcrypt$n=1024,r=8,p=1$c2Fs$aGFzaA", "scrypt$n=abc,r=8,p=1$c2Fs$aGFzaA",
    "scrypt$n=1024,r=8,p=1$$", "scrypt$n=1024,r=8,p=1$!!!$!!!",
])
def test_un_registro_corrupto_es_un_no_rotundo_y_no_una_excepcion(basura):
    """Un valor mal pegado en Railway tiene que impedir entrar, no tumbar el
    panel con una traza que además enseñe la forma del registro."""
    assert auth.verificar("lo que sea", basura) is False


def test_un_registro_hostil_no_puede_pedir_memoria_infinita():
    """`n` enorme en la variable de entorno = petición de gigabytes en el primer
    intento de login. Se acota lo que se acepta LEER, no sólo lo que se genera."""
    hostil = "scrypt$n=1073741824,r=32,p=1$c2Fsc2Fsc2Fsc2Fs$aGFzaGhhc2g"
    assert auth.verificar("x", hostil) is False
    with pytest.raises(auth.RegistroInvalido):
        auth.hash_contrasena("x", n=2 ** 30, r=32, p=1)


def test_n_tiene_que_ser_potencia_de_dos():
    with pytest.raises(auth.RegistroInvalido):
        auth.hash_contrasena("x", n=3000, r=8, p=1)


# ---------------------------------------------------------- el backend v1


def test_parsear_usuarios_admite_varias_personas():
    uno = auth.hash_contrasena("a", **BARATO)
    otro = auth.hash_contrasena("b", **BARATO)
    crudo = f"Alberto:{uno};autor:{otro}"
    usuarios = auth.parsear_usuarios(crudo)
    assert set(usuarios) == {"alberto", "autor"}      # normalizados a minúsculas
    assert usuarios["alberto"] == uno


def test_el_separador_no_es_la_coma():
    """La coma vive DENTRO del registro (`n=1024,r=8,p=1`): partir por ella
    trocearía cada hash por la mitad. Este test es el que fija esa decisión."""
    registro = auth.hash_contrasena("a", **BARATO)
    assert "," in registro
    usuarios = auth.parsear_usuarios(f"ana:{registro}")
    assert usuarios["ana"] == registro
    assert auth.verificar("a", usuarios["ana"])


def test_parsear_usuarios_admite_saltos_de_linea():
    uno = auth.hash_contrasena("a", **BARATO)
    assert set(auth.parsear_usuarios(f"ana:{uno}\n\nluis:{uno}")) == {"ana", "luis"}


def test_backend_de_entorno(monkeypatch):
    registro = auth.hash_contrasena("la buena", **BARATO)
    monkeypatch.setenv(auth.VARIABLE_USUARIOS, f"alberto:{registro}")
    backend = auth.BackendEntorno()
    # (s324j) `Usuario` lleva ahora el sello de su credencial — derivado del
    # registro, así que se conoce de antemano y la igualdad sigue siendo exacta.
    esperado = auth.Usuario("alberto", sello=auth.sello_de_registro(registro))
    assert backend.autenticar("alberto", "la buena") == esperado
    assert backend.autenticar("ALBERTO", "la buena") == esperado
    assert backend.autenticar("alberto", "la mala") is None
    assert backend.autenticar("nadie", "la buena") is None
    # Y la revalidación por petición, con la misma fuente:
    assert backend.sello("alberto") == esperado.sello
    assert backend.sello("nadie") is None


def test_el_backend_se_puede_sustituir():
    """DEC-231 §3: el día que sepamos qué es el login del war room, se cambia
    esto y no se toca ni una ruta. (s324j: el contrato pide también `sello` —
    un backend sin revalidación por petición ya no es un backend del panel.)"""

    class Guerra:
        def autenticar(self, usuario, contrasena):
            if contrasena == "sso":
                return auth.Usuario("del-war-room", sello="sello-sso")
            return None

        def sello(self, nombre):
            return "sello-sso" if nombre == "del-war-room" else None

    anterior = auth.usar_backend(Guerra())
    try:
        assert auth.autenticar("quien sea", "sso").nombre == "del-war-room"
        assert auth.autenticar("quien sea", "otra") is None
    finally:
        auth.usar_backend(anterior)


@pytest.mark.parametrize("valor", [
    "", "   ", "sin-dos-puntos", "alberto:mi-contraseña-en-claro",
])
def test_validar_configuracion_aborta_el_arranque(monkeypatch, valor):
    monkeypatch.setenv(auth.VARIABLE_USUARIOS, valor)
    with pytest.raises(RuntimeError):
        auth.validar_configuracion()


def test_validar_configuracion_pasa_con_un_registro_bueno(monkeypatch):
    registro = auth.hash_contrasena("x", **BARATO)
    monkeypatch.setenv(auth.VARIABLE_USUARIOS, f"alberto:{registro}")
    auth.validar_configuracion()


# ------------------------------------------------------------------ cerrojo


def test_el_cerrojo_deja_pasar_los_primeros_fallos_y_luego_cierra():
    cerrojo = auth.Cerrojo()
    claves = auth.claves_de("alberto", "1.2.3.4")
    for _ in range(auth.FALLOS_LIBRES):
        cerrojo.fallo(claves, 100.0)
        assert cerrojo.bloqueado(claves, 100.0) == 0.0
    cerrojo.fallo(claves, 100.0)
    assert cerrojo.bloqueado(claves, 100.0) == pytest.approx(auth.BLOQUEO_BASE_S)


def test_el_bloqueo_dobla_y_tiene_techo():
    cerrojo = auth.Cerrojo()
    claves = auth.claves_de("alberto", "1.2.3.4")
    for _ in range(auth.FALLOS_LIBRES + 2):
        cerrojo.fallo(claves, 0.0)
    assert cerrojo.bloqueado(claves, 0.0) == pytest.approx(
        auth.BLOQUEO_BASE_S * 2)
    for _ in range(30):
        cerrojo.fallo(claves, 0.0)
    assert cerrojo.bloqueado(claves, 0.0) == auth.BLOQUEO_MAX_S


def test_el_bloqueo_caduca_solo():
    cerrojo = auth.Cerrojo()
    claves = auth.claves_de("alberto", "1.2.3.4")
    for _ in range(auth.FALLOS_LIBRES + 1):
        cerrojo.fallo(claves, 0.0)
    assert cerrojo.bloqueado(claves, auth.BLOQUEO_BASE_S + 1) == 0.0


def test_un_acierto_limpia_el_historial():
    cerrojo = auth.Cerrojo()
    claves = auth.claves_de("alberto", "1.2.3.4")
    for _ in range(auth.FALLOS_LIBRES + 1):
        cerrojo.fallo(claves, 0.0)
    cerrojo.acierto(claves)
    assert cerrojo.bloqueado(claves, 0.0) == 0.0


def test_el_cerrojo_cuenta_por_usuario_Y_por_ip():
    """Sólo por IP → un botnet entra probando. Sólo por usuario → cualquiera
    deja fuera a Alberto. Van los dos, y basta uno cerrado para cerrar."""
    cerrojo = auth.Cerrojo()
    for ip in range(auth.FALLOS_LIBRES + 1):
        cerrojo.fallo(auth.claves_de("alberto", f"10.0.0.{ip}"), 0.0)
    # IP nueva, pero el usuario ya acumuló fallos: sigue cerrado.
    assert cerrojo.bloqueado(auth.claves_de("alberto", "10.0.0.99"), 0.0) > 0
    # Y otro usuario desde una IP limpia no paga por ello.
    assert cerrojo.bloqueado(auth.claves_de("otra", "10.0.0.99"), 0.0) == 0.0


def test_el_cerrojo_no_crece_sin_limite():
    """Es una estructura alimentada desde fuera por cualquiera: misma disciplina
    que la caché de la puerta del bot (`access.CACHE_MAX_ENTRADAS`)."""
    cerrojo = auth.Cerrojo()
    for i in range(auth.CERROJO_MAX_ENTRADAS + 500):
        cerrojo.fallo((f"ip:{i}",), float(i))
    assert len(cerrojo._tabla) <= auth.CERROJO_MAX_ENTRADAS


# ------------------------------------------------------------------- sesión


def test_una_sesion_recien_firmada_se_verifica():
    payload = sesion.nueva("alberto")
    cookie = sesion.firmar(payload, SECRETO)
    leido = sesion.verificar(cookie, SECRETO)
    assert leido["u"] == "alberto"
    assert leido["csrf"] == payload["csrf"]


def test_una_sesion_caducada_no_vale():
    payload = sesion.nueva("alberto", ahora=time.time() - 10_000, duracion=60)
    assert sesion.verificar(sesion.firmar(payload, SECRETO), SECRETO) is None


def test_el_plazo_lo_manda_el_servidor_no_el_navegador():
    """Quien roba la cookie la reenvía cuando quiera: el `Max-Age` es una
    cortesía y el único plazo real es el firmado dentro."""
    payload = sesion.nueva("alberto", ahora=1000.0, duracion=3600)
    cookie = sesion.firmar(payload, SECRETO)
    assert sesion.verificar(cookie, SECRETO, ahora=1500.0) is not None
    assert sesion.verificar(cookie, SECRETO, ahora=5000.0) is None


@pytest.mark.parametrize("estropear", [
    lambda c: c[:-1],                                   # firma recortada
    lambda c: c.split(".")[0],                          # sin firma
    lambda c: "." + c.split(".")[1],                    # sin cuerpo
    lambda c: c.replace(".", "!"),                      # sin separador
    lambda c: "x" + c,                                  # cuerpo tocado
    lambda c: "",
    lambda c: None,
])
def test_una_cookie_manipulada_no_vale(estropear):
    cookie = sesion.firmar(sesion.nueva("alberto"), SECRETO)
    assert sesion.verificar(estropear(cookie), SECRETO) is None


def test_una_cookie_de_otro_secreto_no_vale():
    cookie = sesion.firmar(sesion.nueva("intruso"), b"otro-secreto-larguisimo-xx")
    assert sesion.verificar(cookie, SECRETO) is None


def test_rotar_el_secreto_cierra_todas_las_sesiones():
    """El botón de pánico de una cookie robada, y el motivo por el que se puede
    prescindir de una tabla de sesiones."""
    cookie = sesion.firmar(sesion.nueva("alberto"), SECRETO)
    assert sesion.verificar(cookie, SECRETO) is not None
    assert sesion.verificar(cookie, b"secreto-nuevo-tras-la-rotacion-xxxxx") is None


def test_una_cookie_enorme_se_descarta_antes_de_mirarla():
    assert sesion.verificar("a" * (sesion.COOKIE_MAX_CHARS + 1), SECRETO) is None


@pytest.mark.parametrize("payload", [
    {"exp": 9e12, "csrf": "x"},                      # sin usuario
    {"u": "", "exp": 9e12, "csrf": "x"},
    {"u": "a", "csrf": "x"},                         # sin caducidad
    {"u": "a", "exp": "mañana", "csrf": "x"},        # caducidad no numérica
    {"u": "a", "exp": True, "csrf": "x"},            # bool NO es un plazo
    {"u": "a", "exp": 9e12},                         # sin csrf
])
def test_un_payload_incompleto_no_vale_aunque_la_firma_sea_buena(payload):
    """Firmado por nosotros pero mal formado: se rechaza igual. Si no, un fallo
    de programación aguas arriba se convertiría en una sesión sin caducidad."""
    assert sesion.verificar(sesion.firmar(payload, SECRETO), SECRETO) is None


def test_csrf_valido_solo_con_el_token_de_esa_sesion():
    una = sesion.nueva("alberto")
    otra = sesion.nueva("alberto")
    assert sesion.csrf_valido(una, una["csrf"])
    assert not sesion.csrf_valido(una, otra["csrf"])
    assert not sesion.csrf_valido(una, "")
    assert not sesion.csrf_valido(una, None)
    assert not sesion.csrf_valido({}, "loquesea")


def test_csrf_no_ascii_es_falso_no_excepcion():
    """Tanda 1 del 2º frontera: `compare_digest` sobre `str` exige ASCII y
    LANZA con cualquier otro carácter — y el token enviado viene del
    formulario (utf-8 con errors="replace"). Un csrf no-ASCII debe ser el 403
    de siempre (False), jamás un TypeError que rompa el despacho."""
    una = sesion.nueva("alberto")
    assert sesion.csrf_valido(una, "café-\ufffd") is False   # sin lanzar
    assert sesion.csrf_valido(una, una["csrf"])               # el bueno sigue OK


def test_la_cookie_sale_endurecida():
    cabecera = sesion.cabecera_cookie("valor", max_age=3600)
    for atributo in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/"):
        assert atributo in cabecera
    assert "Max-Age=0" in sesion.cabecera_borrado()


def test_leer_cookie_encuentra_la_nuestra_entre_otras():
    cabecera = f"otra=1; {sesion.NOMBRE_COOKIE}=abc.def; tercera=2"
    assert sesion.leer_cookie(cabecera) == "abc.def"
    assert sesion.leer_cookie("otra=1") is None
    assert sesion.leer_cookie(None) is None


def test_el_secreto_corto_se_rechaza(monkeypatch):
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, "corto")
    with pytest.raises(RuntimeError, match="demasiado corto"):
        sesion.secreto()
    monkeypatch.delenv(sesion.VARIABLE_SECRETO)
    with pytest.raises(RuntimeError):
        sesion.secreto()


def test_duracion_configurable_con_defecto_sano(monkeypatch):
    monkeypatch.setenv(sesion.VARIABLE_DURACION, "2")
    assert sesion.duracion_s() == 7200
    for malo in ("cero", "-1", "0", "999"):
        monkeypatch.setenv(sesion.VARIABLE_DURACION, malo)
        assert sesion.duracion_s() == sesion.DURACION_DEFECTO_S
