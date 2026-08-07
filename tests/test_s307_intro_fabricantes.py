"""s307 — la intro del bot dice la verdad sobre el corpus (y la sigue diciendo sola).

Origen: pantallazo de Alberto del /accept — «Tengo información de los manuales de
Notifier, Morley y Detnov», con 30 fabricantes reales en `documents` activos. El fix
NO es otra constante (caducaría en el fabricante 31): la lista se deriva de la base
una vez por proceso, con fallback estático si la base no responde.

Contratos:
  · caché por proceso — el éxito se cachea, el FALLO no (el siguiente saludo reintenta);
  · fail-open — un hiccup de la base jamás rompe un saludo;
  · el texto LEGAL (`_CONSENT_TERMS`, TERMS v7) queda ESTÁTICO a propósito: es lo que
    la gente aceptó; su línea de marcas viaja en el bump a v8 (base jurídica), no antes.
"""
from __future__ import annotations

import pytest

import src.bot.telegram_bot as bot


@pytest.fixture(autouse=True)
def _cache_limpia():
    bot._fabricantes_cache = None
    yield
    bot._fabricantes_cache = None


def _con_marcas(monkeypatch, marcas):
    llamadas = {"n": 0}

    def fake():
        llamadas["n"] += 1
        return marcas

    monkeypatch.setattr(bot, "get_manufacturers_by_docs", fake)
    return llamadas


def test_resumen_top5_y_mas(monkeypatch):
    _con_marcas(monkeypatch, [(f"M{i}", 100 - i) for i in range(30)])
    linea, n = bot._fabricantes_resumen()
    assert n == 30
    assert linea == "*M0*, *M1*, *M2*, *M3*, *M4* y más"


def test_resumen_pocas_marcas_sin_coletilla(monkeypatch):
    _con_marcas(monkeypatch, [("Notifier", 400), ("Detnov", 60)])
    linea, n = bot._fabricantes_resumen()
    assert n == 2
    assert linea == "*Notifier*, *Detnov*"


def test_el_exito_se_cachea_una_llamada_por_proceso(monkeypatch):
    llamadas = _con_marcas(monkeypatch, [("Notifier", 400)])
    bot._fabricantes_resumen()
    bot._fabricantes_resumen()
    bot._fabricantes_resumen()
    assert llamadas["n"] == 1


def test_el_fallo_NO_se_cachea_y_cae_al_fallback(monkeypatch):
    """Un hiccup no puede congelar el texto genérico para el resto del proceso."""
    llamadas = {"n": 0}

    def fake():
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise RuntimeError("db caida")
        return [("Notifier", 400)]

    monkeypatch.setattr(bot, "get_manufacturers_by_docs", fake)
    linea, n = bot._fabricantes_resumen()
    assert n is None and "Notifier" in linea            # fallback estático
    linea2, n2 = bot._fabricantes_resumen()             # reintenta y se recupera
    assert n2 == 1 and llamadas["n"] == 2


def test_welcome_lleva_el_numero_cuando_hay_medida(monkeypatch):
    _con_marcas(monkeypatch, [(f"M{i}", 10) for i in range(30)])
    texto = bot._welcome_text()
    assert "*30 fabricantes*" in texto
    assert "Notifier, Morley y Detnov" not in texto     # la lista vieja no vuelve


def test_welcome_sin_db_usa_el_fallback_sin_numero(monkeypatch):
    def fake():
        raise RuntimeError("db caida")

    monkeypatch.setattr(bot, "get_manufacturers_by_docs", fake)
    texto = bot._welcome_text()
    assert "fabricantes*" not in texto                  # sin número inventado
    assert "*Notifier*" in texto                        # pero sí marcas reales


def test_el_texto_legal_sigue_estatico_v7():
    """`_CONSENT_TERMS` es lo que la gente ACEPTÓ: nada puede entrar ahí sin bump de
    versión. Pin por HASH del texto completo (Sol s307: la subcadena no pinna byte-
    identidad). Si falla: o alguien tocó el texto legal SIN bump a v8 — revertir — o
    es el bump deliberado: actualizar hash Y TERMS_VERSION juntos."""
    import hashlib
    assert hashlib.sha256(bot._CONSENT_TERMS.encode("utf-8")).hexdigest() == (
        "bb0f14908ec788b97dac332bb165d4fd2e8f0b5f16272fb920e258217b67ea3a")
