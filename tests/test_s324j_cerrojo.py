# -*- coding: utf-8 -*-
"""s324j — El cerrojo contar-al-admitir: el doble en memoria fija la semántica
y el distribuido se prueba con transportes inyectados, sin red (puertas 4 y 5
de `evals/s324i_panel_vercel_propuesta_v9.md`; la concurrencia REAL de
Postgres la ejercita `test_s324j_panel_pg.py` en su contenedor).
"""
from __future__ import annotations

import re

import httpx
import pytest

from dashboard import auth, cerrojo, sesion

SECRETO = "secreto-de-pruebas-con-longitud-mas-que-suficiente"


# ------------------------------------------------- admitir, el doble en memoria


def test_admitir_reproduce_la_tabla_secuencial_del_cerrojo_de_hoy():
    """La tabla de casos de la puerta 4 — la MISMA que va como comentario-
    contrato en el SQL de `panel_puerta`: para intentos uno detrás de otro,
    contar-al-admitir produce exactamente los mismos bloqueos que el par
    `bloqueado`+`fallo` de siempre (el intento k ve fallos=k−1)."""
    c = auth.Cerrojo()
    claves = ("u:alberto", "ip:1.2.3.4")
    # Los primeros FALLOS_LIBRES+1 intentos entran (fallos previos 0..4):
    for _ in range(auth.FALLOS_LIBRES + 1):
        assert c.admitir(claves, ahora=100.0) == 0.0
    # El sexto se bloquea, con el primer castigo (base) contado desde `ultimo`:
    espera = c.admitir(claves, ahora=100.0)
    assert espera == pytest.approx(auth.BLOQUEO_BASE_S)
    # ...bloqueado NO incrementa: la espera no crece por reintentar.
    assert c.admitir(claves, ahora=100.0) == pytest.approx(espera)
    # Y decae sola:
    assert c.admitir(claves, ahora=100.0 + auth.BLOQUEO_BASE_S + 1) == 0.0


def test_admitir_acota_el_rebanyo_n_llamadas_admiten_como_mucho_libres_mas_uno():
    """(a) de la puerta 4: N llamadas «concurrentes» (mismo instante, sin
    acierto entre medias) admiten ≤ FALLOS_LIBRES+1 — la semántica que el
    umbral prometía y que «comprobar→scrypt→registrar» no daba."""
    c = auth.Cerrojo()
    claves = ("u:alberto",)
    admitidas = sum(1 for _ in range(50) if c.admitir(claves, ahora=5.0) == 0.0)
    assert admitidas == auth.FALLOS_LIBRES + 1


def test_el_acierto_limpia_con_los_fallos_del_atacante_dentro_y_es_heredado():
    """(c) de la puerta 4 (ronda S-M1): la semántica DOCUMENTADA, afirmada para
    que nadie la «arregle» sin decidirlo — el login bueno del legítimo limpia
    la clave `u:` CON los fallos del atacante dentro (auth.py `acierto`, de
    siempre), y la clave `ip:` del atacante, que es suya, sobrevive."""
    c = auth.Cerrojo()
    atacante = ("u:alberto", "ip:6.6.6.6")
    legitimo = ("u:alberto", "ip:9.9.9.9")
    for _ in range(3):
        assert c.admitir(atacante, ahora=10.0) == 0.0
    assert c.admitir(legitimo, ahora=10.0) == 0.0     # el legítimo entra...
    c.acierto(legitimo)                               # ...y limpia SUS claves
    # La clave compartida u: quedó limpia (heredado, documentado):
    assert c.espera("u:alberto", 10.0) == 0.0
    # La ip: del atacante conserva sus fallos:
    assert c._tabla["ip:6.6.6.6"].fallos == 3


# --------------------------------------------- las claves que salen a la tabla


@pytest.fixture
def con_secreto(monkeypatch):
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, SECRETO)


def test_puerta_5_ni_el_usuario_ni_la_ip_salen_en_claro(con_secreto):
    claves = auth.claves_de("alberto", "203.0.113.9")
    seudonimas = cerrojo.claves_seudonimas(claves)
    for clave in seudonimas:
        assert re.fullmatch(r"^(u|ip):[A-Za-z0-9_-]+$", clave)
        assert "alberto" not in clave
        assert "203.0.113.9" not in clave


def test_la_mitad_ip_esta_apagada_hasta_medir_xff(con_secreto):
    """Ronda F5-M1: con la IP compartida del proxy (o '?') y el MAX sobre
    claves, 5 fallos de un atacante serían un 429 GLOBAL. Hasta fijar la regla
    de XFF, la clave ip: NI CUENTA NI BLOQUEA."""
    assert cerrojo.INCLUIR_CLAVE_IP is False
    seudonimas = cerrojo.claves_seudonimas(auth.claves_de("alberto", "1.2.3.4"))
    assert len(seudonimas) == 1
    assert seudonimas[0].startswith("u:")


def test_el_seudonimo_es_estable_y_distinto_por_identificador(con_secreto):
    a1 = cerrojo.claves_seudonimas(("u:alberto",))
    a2 = cerrojo.claves_seudonimas(("u:alberto",))
    b = cerrojo.claves_seudonimas(("u:beatriz",))
    assert a1 == a2
    assert a1 != b


def test_rotar_el_secreto_rota_las_claves(monkeypatch):
    """El precio del acoplamiento, declarado (ronda F-m3): rotar el secreto de
    firma huérfana las filas — contadores frescos. Aquí solo se afirma el
    MECANISMO (K deriva del secreto)."""
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, SECRETO)
    antes = cerrojo.claves_seudonimas(("u:alberto",))
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, "otro-secreto-largo-largo-largo-x")
    despues = cerrojo.claves_seudonimas(("u:alberto",))
    assert antes != despues


# ------------------------------------------------- CerrojoSupabase, sin red


class _Resp:
    def __init__(self, status_code, cuerpo="0"):
        self.status_code = status_code
        self._cuerpo = cuerpo
        self.content = cuerpo.encode()

    def json(self):
        import json
        return json.loads(self._cuerpo)


@pytest.fixture
def credenciales(monkeypatch):
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, SECRETO)
    monkeypatch.setattr(cerrojo, "SUPABASE_URL", "https://proyecto.supabase.co")
    monkeypatch.setattr(cerrojo, "SUPABASE_SERVICE_KEY", "clave-servicio")


def test_admitir_llama_a_la_rpc_con_las_constantes_de_auth(credenciales):
    visto = {}

    def rpc(payload):
        visto.update(payload)
        return _Resp(200, "0")

    c = cerrojo.CerrojoSupabase(rpc=rpc, delete=lambda p: _Resp(204, ""))
    assert c.admitir(auth.claves_de("alberto", "1.2.3.4")) == 0.0
    assert visto["libres"] == auth.FALLOS_LIBRES
    assert visto["base_s"] == auth.BLOQUEO_BASE_S
    assert visto["max_s"] == auth.BLOQUEO_MAX_S
    assert visto["retencion_s"] == auth.CERROJO_RETENCION_S
    assert visto["cap"] == auth.CERROJO_MAX_ENTRADAS
    assert all(k.startswith("u:") for k in visto["claves"])      # ip: apagada


def test_una_espera_devuelta_jamas_se_ignora(credenciales):
    c = cerrojo.CerrojoSupabase(rpc=lambda p: _Resp(200, "87.5"),
                                delete=lambda p: _Resp(204, ""))
    assert c.admitir(("u:x",)) == 87.5


def test_fallo_de_conexion_es_fail_open_con_log(credenciales, caplog):
    """La frontera «¿se pudo HABLAR?» (rondas S4-M1/F2-M2): PostgREST no llegó
    a responder → el intento se permite (scrypt sigue siendo el suelo) y cada
    ocurrencia deja log a nivel ERROR — no invisible."""
    def rpc(payload):
        raise httpx.ConnectError("boom")

    c = cerrojo.CerrojoSupabase(rpc=rpc, delete=lambda p: _Resp(204, ""))
    import logging
    with caplog.at_level(logging.ERROR, logger="dashboard.cerrojo"):
        assert c.admitir(("u:x",)) == 0.0
    assert any("fail-open" in r.message for r in caplog.records)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
def test_cualquier_respuesta_4xx_5xx_es_configuracion_y_cierra(credenciales, status):
    """PostgREST HABLÓ y algo está mal de forma reproducible (función sin
    migrar, firma, ACL, SQL): CerrojoNoDisponible → 503, nunca fail-open
    silencioso e indefinido (el hallazgo F2-M2/S3-M1)."""
    c = cerrojo.CerrojoSupabase(rpc=lambda p: _Resp(status, "{}"),
                                delete=lambda p: _Resp(204, ""))
    with pytest.raises(cerrojo.CerrojoNoDisponible):
        c.admitir(("u:x",))


def test_sin_credenciales_tambien_cierra(monkeypatch):
    monkeypatch.setenv(sesion.VARIABLE_SECRETO, SECRETO)
    monkeypatch.setattr(cerrojo, "SUPABASE_URL", "")
    monkeypatch.setattr(cerrojo, "SUPABASE_SERVICE_KEY", "")
    c = cerrojo.CerrojoSupabase(rpc=lambda p: _Resp(200, "0"),
                                delete=lambda p: _Resp(204, ""))
    with pytest.raises(cerrojo.CerrojoNoDisponible):
        c.admitir(("u:x",))


def test_acierto_borra_por_las_claves_seudonimas_y_no_revienta(credenciales, caplog):
    borrado = {}

    def delete(params):
        borrado.update(params)
        return _Resp(204, "")

    c = cerrojo.CerrojoSupabase(rpc=lambda p: _Resp(200, "0"), delete=delete)
    claves = auth.claves_de("alberto", "1.2.3.4")
    c.acierto(claves)
    assert borrado["clave"].startswith("in.(u:")
    assert "alberto" not in borrado["clave"]
    # Y si el DELETE falla, el login bueno NO se bloquea — log y a seguir:
    def delete_roto(params):
        raise httpx.ConnectError("boom")
    c2 = cerrojo.CerrojoSupabase(rpc=lambda p: _Resp(200, "0"), delete=delete_roto)
    import logging
    with caplog.at_level(logging.ERROR, logger="dashboard.cerrojo"):
        c2.acierto(claves)                       # no lanza
    assert any("acierto" in r.message for r in caplog.records)


def test_la_sonda_prueba_extremo_a_extremo_sin_tocar_contadores(credenciales):
    """v9 §3.5: `panel_puerta` con claves VACÍAS — si la función no está
    migrada (≥400), el arranque aborta con el motivo escrito."""
    llamadas = []

    def rpc(payload):
        llamadas.append(payload)
        return _Resp(200, "0")

    anterior = cerrojo.usar_cerrojo(cerrojo.CerrojoSupabase(
        rpc=rpc, delete=lambda p: _Resp(204, "")))
    try:
        cerrojo.sonda()
        assert llamadas[0]["claves"] == []
    finally:
        cerrojo.usar_cerrojo(anterior)

    anterior = cerrojo.usar_cerrojo(cerrojo.CerrojoSupabase(
        rpc=lambda p: _Resp(404, "{}"), delete=lambda p: _Resp(204, "")))
    try:
        with pytest.raises(RuntimeError, match="019"):
            cerrojo.sonda()
    finally:
        cerrojo.usar_cerrojo(anterior)


def test_con_el_cerrojo_de_memoria_la_sonda_no_hace_nada():
    anterior = cerrojo.usar_cerrojo(auth.Cerrojo())
    try:
        cerrojo.sonda()                          # no lanza, no necesita red
    finally:
        cerrojo.usar_cerrojo(anterior)
