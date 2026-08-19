# -*- coding: utf-8 -*-
"""s324j — `BackendSupabase`, el sello y el validador estricto (puertas 6,
6-bis-lado-python y 11 de `evals/s324i_panel_vercel_propuesta_v9.md`).

El transporte es un doble con la firma de `datos.leer`: la suite corre sin red
(puerta 10) y cada rama del contrato se afirma por ESTRUCTURA (cuántas veces
corre el señuelo), no con un cronómetro — lo único estable en CI.
"""
from __future__ import annotations

import pytest

from dashboard import auth, datos

BARATO = dict(n=2 ** 10, r=2, p=1)


def _leer_con(filas=None, estado=None, detalle=""):
    """Un transporte de mentira que devuelve siempre el mismo Resultado."""
    if estado is None:
        estado = datos.OK if filas else datos.VACIO
    resultado = datos.Resultado(estado, list(filas or []), detalle)

    def leer(recurso, params):
        leer.llamadas.append((recurso, dict(params)))
        return resultado

    leer.llamadas = []
    return leer


@pytest.fixture
def contando_senuelo(monkeypatch):
    """Cuenta las verificaciones contra el SEÑUELO sin tocar las reales."""
    conteo = {"senuelo": 0}
    original = auth.verificar

    def espia(contrasena, registro):
        if registro == auth._SENUELO:
            conteo["senuelo"] += 1
        return original(contrasena, registro)

    monkeypatch.setattr(auth, "verificar", espia)
    return conteo


REGISTRO = auth.hash_contrasena("la buena", **BARATO)


# ------------------------------------------------------------------- puerta 6


def test_existe_y_acierta_sin_senuelo_y_con_sello(contando_senuelo):
    backend = auth.BackendSupabase(leer=_leer_con(
        [{"usuario": "alberto", "registro": REGISTRO}]))
    usuario = backend.autenticar("Alberto", "la buena")
    assert usuario == auth.Usuario("alberto", sello=auth.sello_de_registro(REGISTRO))
    assert contando_senuelo["senuelo"] == 0


def test_existe_y_falla_sin_senuelo(contando_senuelo):
    backend = auth.BackendSupabase(leer=_leer_con(
        [{"usuario": "alberto", "registro": REGISTRO}]))
    assert backend.autenticar("alberto", "la mala") is None
    assert contando_senuelo["senuelo"] == 0


def test_no_existe_o_inactivo_corre_el_senuelo_exactamente_una_vez(contando_senuelo):
    """Ausente e inactivo son LA MISMA respuesta vacía (el filtro `activo` va
    EN la consulta): el código no puede distinguirlos ni por accidente, y el
    coste scrypt se paga igual — sin oráculo de enumeración."""
    backend = auth.BackendSupabase(leer=_leer_con([]))
    assert backend.autenticar("nadie", "lo que sea") is None
    assert contando_senuelo["senuelo"] == 1


def test_nombre_fuera_del_charset_es_inexistente_sin_consulta(contando_senuelo):
    """v9 §5: la entrada se acota ANTES de viajar en un filtro — los caracteres
    que PostgREST trata como estructura no llegan a `usuario=eq.X`."""
    leer = _leer_con([])
    backend = auth.BackendSupabase(leer=leer)
    assert backend.autenticar("come,coma)", "x") is None
    assert leer.llamadas == []                   # sin consulta
    assert contando_senuelo["senuelo"] == 1      # y con señuelo igualmente


@pytest.mark.parametrize("estado,detalle", [
    (datos.ERROR, "no se pudo hablar con Supabase (ConnectError)"),
    (datos.ERROR, "Supabase respondió 401"),
    (datos.ERROR, "Supabase respondió 500"),
    (datos.TABLA_AUSENTE, "panel_usuarios"),
    (datos.SIN_CREDENCIALES, "faltan claves"),
])
def test_cualquier_no_ok_del_transporte_es_identidad_no_disponible(
        contando_senuelo, estado, detalle):
    """La regla simétrica a la del cerrojo (rondas S4-M1/S6-M4): conexión
    imposible, tabla ausente, credenciales ausentes y toda respuesta >= 400
    son LA MISMA cosa — «no puedo comprobarlo» — y NUNCA «credencial mala».
    Sin señuelo: una caída falla igual para todos, antes de tocar credencial
    alguna; no necesita tiempo constante — necesita no mentir."""
    backend = auth.BackendSupabase(leer=_leer_con(estado=estado, detalle=detalle))
    with pytest.raises(auth.IdentidadNoDisponible):
        backend.autenticar("alberto", "la buena")
    assert contando_senuelo["senuelo"] == 0


def test_la_consulta_lleva_el_filtro_activo_y_el_select_minimo():
    leer = _leer_con([{"usuario": "alberto", "registro": REGISTRO}])
    auth.BackendSupabase(leer=leer).autenticar("alberto", "la buena")
    _, params = leer.llamadas[0]
    assert params["activo"] == "is.true"
    assert params["select"] == "usuario,registro"
    assert params["usuario"] == "eq.alberto"
    assert params["limit"] == "1"


# ------------------------------------------------------------------ el sello


def test_sello_vigente_none_y_no_disponible():
    con_fila = auth.BackendSupabase(leer=_leer_con(
        [{"usuario": "alberto", "registro": REGISTRO}]))
    assert con_fila.sello("alberto") == auth.sello_de_registro(REGISTRO)

    vacio = auth.BackendSupabase(leer=_leer_con([]))
    assert vacio.sello("alberto") is None        # revocado/ausente → fuera

    caido = auth.BackendSupabase(leer=_leer_con(estado=datos.ERROR))
    with pytest.raises(auth.IdentidadNoDisponible):
        caido.sello("alberto")                   # 503, sin matar la cookie


def test_el_sello_cambia_exactamente_con_el_registro():
    otro = auth.hash_contrasena("otra contraseña", **BARATO)
    assert auth.sello_de_registro(REGISTRO) != auth.sello_de_registro(otro)
    assert auth.sello_de_registro(REGISTRO) == auth.sello_de_registro(REGISTRO)


def test_el_sello_es_b64url_de_16_bytes_sin_relleno():
    """Un solo contrato de truncado en todo el diseño (rondas F4-m2/F6-m4):
    16 bytes → 22 caracteres base64url, sin `=` y sin `+`/`/`."""
    sello = auth.sello_de_registro(REGISTRO)
    assert len(sello) == 22
    assert "=" not in sello and "+" not in sello and "/" not in sello


# ----------------------------------------------------------------- puerta 11


def test_el_registro_canonico_pasa_el_estricto():
    auth.validar_registro_estricto(REGISTRO)     # no lanza


@pytest.mark.parametrize("romper", [
    # sal de 1 byte: LEGIBLE por _partir y jamás verificaría — el usuario
    # inalcanzable de S3-M3.
    lambda r: _con_sal_y_clave(r, sal_b=b"x", clave_b=None),
    # hash de 8 bytes:
    lambda r: _con_sal_y_clave(r, sal_b=None, clave_b=b"12345678"),
    # parámetro extra que _partir ignoraría en silencio:
    lambda r: r.replace("$n=", "$extra=9,n="),
    # contraseña en claro (ni siquiera es un registro):
    lambda r: "mi-contraseña-en-claro",
])
def test_lo_legible_pero_no_canonico_se_rechaza(romper):
    with pytest.raises(auth.RegistroInvalido):
        auth.validar_registro_estricto(romper(REGISTRO))


def _con_sal_y_clave(registro, *, sal_b, clave_b):
    alg, params, sal, clave = registro.split("$")
    if sal_b is not None:
        sal = auth._b64(sal_b)
    if clave_b is not None:
        clave = auth._b64(clave_b)
    return "$".join([alg, params, sal, clave])
