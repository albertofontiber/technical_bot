"""s297 — libro de eventos de consentimiento + feedback resistente a FK colgante.

Contrato:
  · aceptar escribe DOS cosas: el estado (`user_consent`, lo que `has_consent` lee) y el
    EVENTO (`consent_events`, la evidencia que nada pisa);
  · si el libro falla, el técnico entra igual (fail-open declarado) — pero con aviso;
  · un feedback cuyo enlace quedó colgando (su consulta se borró entre medias) sobrevive
    SUELTO en vez de perderse entero — y solo ante el rechazo definitivo de FK (23503),
    nunca ante un timeout, porque el primer POST pudo haberse confirmado.
"""

import json

import httpx
import pytest

import src.logging_db as logging_db
from src.logging_db import TERMS_VERSION, _fk_rejected, log_feedback, set_consent


class _Respuesta:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class _ClienteFalso:
    """Captura cada POST y responde según un guion por URL (en orden de llamada)."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.posts: list[tuple[str, dict]] = []

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None):
        self.posts.append((url, json))
        return self.guion.pop(0) if self.guion else _Respuesta()


@pytest.fixture(autouse=True)
def _cache_limpia():
    logging_db._consent_cache.clear()
    logging_db._consent_cache_misses.clear()
    yield
    logging_db._consent_cache.clear()
    logging_db._consent_cache_misses.clear()


# ------------------------------------------------------------------ el libro


def test_aceptar_escribe_estado_y_evento(monkeypatch):
    cliente = _ClienteFalso([_Respuesta(201), _Respuesta(201)])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert set_consent(111, display_name="Paco") is True
    assert len(cliente.posts) == 2
    url_estado, _ = cliente.posts[0]
    url_evento, cuerpo_evento = cliente.posts[1]
    assert "user_consent" in url_estado
    assert "consent_events" in url_evento
    assert cuerpo_evento == {
        "telegram_user_id": 111,
        "terms_version": TERMS_VERSION,
        "evento": "accepted",
    }


def test_si_el_libro_falla_el_tecnico_entra_igual(monkeypatch, caplog):
    """Fail-open DECLARADO: bloquear la entrada porque falló la evidencia sería
    desproporcionado. Pero tiene que avisar — una divergencia silenciosa entre estado y
    libro convertiría la evidencia en mentira por omisión."""
    cliente = _ClienteFalso([_Respuesta(201), _Respuesta(404)])   # el libro no existe aún
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert set_consent(111) is True                    # el estado manda
    assert 111 in logging_db._consent_cache
    assert any("SIN evento en el libro" in r.message for r in caplog.records)


def test_si_el_estado_falla_no_se_escribe_evento(monkeypatch):
    """El evento evidencia una aceptación CONSUMADA. Si el estado falló, el bot pide
    reintentar: evidenciar una aceptación que no surtió efecto sería mentir al revés."""
    cliente = _ClienteFalso([_Respuesta(500)])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert set_consent(111) is False
    assert len(cliente.posts) == 1                     # nunca llegó al libro


# ------------------------------------------------------------------ FK colgante


def test_fk_rejected_solo_ante_23503():
    assert _fk_rejected(_Respuesta(409, {"code": "23503", "message": "fk"})) is True
    assert _fk_rejected(_Respuesta(409, {"code": "23505"})) is False    # unique ≠ FK
    assert _fk_rejected(_Respuesta(500, {"code": "23503"})) is False    # no definitivo
    assert _fk_rejected(_Respuesta(409, {})) is False


def test_feedback_con_enlace_colgante_sobrevive_suelto(monkeypatch, caplog):
    """El gap de s296: la consulta padre se borra entre capturar `last_query_log_id` y el
    POST ⇒ la FK rechazaba la fila ENTERA y el feedback moría. Ahora reintenta sin enlace."""
    cliente = _ClienteFalso([
        _Respuesta(409, {"code": "23503", "message": "violates foreign key"}),
        _Respuesta(201),
    ])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    log_feedback(111, "la respuesta estaba mal",
                 previous_query="pregunta borrada", previous_response="respuesta borrada",
                 query_log_id="uuid-borrado")

    assert len(cliente.posts) == 2
    _, primero = cliente.posts[0]
    _, reintento = cliente.posts[1]
    assert primero["query_log_id"] == "uuid-borrado"
    assert "query_log_id" not in reintento             # suelto, como antes de s296
    # Y SIN las copias (dúo): si el padre desapareció por una supresión, las copias SON el
    # dato recién borrado — reinsertarlas re-materializaría lo suprimido, fuera de cascada.
    assert "previous_query" not in reintento
    assert "previous_response" not in reintento
    assert reintento["feedback_text"] == "la respuesta estaba mal"   # el mensaje NUEVO sí
    assert any("SIN enlace" in r.message for r in caplog.records)


def test_sin_enlace_no_hay_reintento(monkeypatch):
    """Un fallo cualquiera sin `query_log_id` en la fila no debe duplicar el POST."""
    cliente = _ClienteFalso([_Respuesta(409, {"code": "23503"})])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    log_feedback(111, "texto")                          # sin query_log_id
    assert len(cliente.posts) == 1


def test_un_timeout_no_se_reintenta(monkeypatch):
    """El primer POST pudo haberse confirmado: reintentar duplicaría el feedback. Solo el
    rechazo DEFINITIVO de FK (atómico) es seguro de reintentar."""

    class _Explota(_ClienteFalso):
        def post(self, url, headers=None, json=None):
            self.posts.append((url, json))
            raise httpx.TimeoutException("timeout")

    cliente = _Explota([])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    log_feedback(111, "texto", query_log_id="uuid")     # no revienta (fire-and-forget)
    assert len(cliente.posts) == 1


def test_si_el_libro_lanza_excepcion_el_tecnico_entra_igual(monkeypatch, caplog):
    """El dúo cazó que el fail-open solo cubría errores HTTP: una excepción de TRANSPORTE
    en el POST del evento, con el estado YA commiteado, devolvía False — el bot pedía
    reintentar un consentimiento ya dado y el usuario quedaba atascado en la caché de
    misses. El POST del evento vive ahora en su propio try."""

    class _EstadoOkEventoExplota(_ClienteFalso):
        def post(self, url, headers=None, json=None):
            self.posts.append((url, json))
            if "consent_events" in url:
                raise httpx.ConnectError("red caida")
            return _Respuesta(201)

    cliente = _EstadoOkEventoExplota([])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)
    logging_db._consent_cache_misses.add(111)          # estaba como miss (escribió antes)

    assert set_consent(111) is True                    # el estado manda: entra
    assert 111 in logging_db._consent_cache
    assert 111 not in logging_db._consent_cache_misses # y NO queda atascado
    assert any("transporte" in r.message for r in caplog.records)


def test_la_cache_de_consentimiento_expira():
    """El dúo cazó que un usuario REVOCADO seguía entrando hasta reiniciar el worker: la
    caché era un set sin expiración. Con TTL, la revocación surte efecto sin reinicio."""
    import time as _time

    from src.logging_db import has_consent

    logging_db._consent_cache[999] = _time.monotonic() + 60      # vigente
    assert has_consent(999) is True

    logging_db._consent_cache[999] = _time.monotonic() - 1       # caducada
    # Sin red no puede reconfirmar: lo que importa es que NO responde True desde la caché.
    assert has_consent(999) is False
