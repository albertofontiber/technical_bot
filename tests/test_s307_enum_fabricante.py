"""s307 — las preguntas de INVENTARIO se responden mirando el inventario (2º fallo orgánico).

Origen: «¿qué productos de Securiton tienes?» (7-ago, 👎 de Alberto con motivo) cayó al
RAG por rigidez de `_CATALOG_PATTERNS` («productos» y «tienes» adyacentes) y el generador
presentó su ventana de 10 chunks como si fuera el inventario — faltaron ASD531 y ASD535
(242 chunks, el doc más grande de la marca).

Contratos:
  · la intención es ESTRECHA: interrogativo + sustantivo de inventario + verbo de posesión
    (o palabra-de-lista) — una avería que mencione «central» NO se convierte en listado;
  · el inventario viene de chunks CURADOS × docs ACTIVOS (documents.product_model está
    stale post-H0 — TECH_DEBT #65 — y NO es fuente);
  · paginación con `order=id.asc` SIEMPRE (lección s304, aquí anclada como test);
  · fail-open: cualquier fallo → RAG de siempre; el fallo no se cachea;
  · DEC-059 intacto: el fall-through medido de preguntas DE MODELO no se toca — esta
    ruta cubre preguntas DE INVENTARIO, población que DEC-059 no midió.
"""
from __future__ import annotations

import pytest

import src.bot.telegram_bot as bot
import src.rag.retriever as retriever


# ------------------------------------------------------------------ la intención


@pytest.mark.parametrize("q", [
    "¿qué productos de Securiton tienes?",          # la consulta orgánica LITERAL
    "que modelos de kidde teneis",
    "¿cuáles equipos de Morley hay?",
    "catálogo de securiton",
    "listado de detectores de aritech",
    "¿qué documentación de Notifier tienes?",
])
def test_la_intencion_de_inventario_casa(q):
    assert bot._ENUM_FABRICANTE.search(q)


@pytest.mark.parametrize("q", [
    "tengo un problema con mi central notifier",     # avería ≠ inventario
    "¿qué central de notifier me recomiendas?",      # recomendación ≠ inventario
    "la central de securiton no arma la zona 3",
    "cómo conecto el detector de kidde",
])
def test_averias_y_recomendaciones_NO_casan(q):
    assert not bot._ENUM_FABRICANTE.search(q)


# ------------------------------------------------------------- la respuesta y su caché


@pytest.fixture(autouse=True)
def _cache_limpia():
    bot._inventario_cache.clear()
    yield
    bot._inventario_cache.clear()


def test_el_inventario_lista_TODO_lo_que_devuelve_la_fuente(monkeypatch):
    """El defecto era una enumeración parcial presentada como completa: la respuesta
    debe llevar CADA modelo de la fuente — incluidos los que el RAG se dejó."""
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda _m: [("ASD535", 1), ("ASD531", 1), ("ADW535", 1)])
    texto = bot._inventario_fabricante("securiton")
    assert "*ASD535*" in texto and "*ASD531*" in texto and "*ADW535*" in texto
    assert "3 modelos" in texto


def test_sin_datos_devuelve_None_y_cae_al_RAG(monkeypatch):
    monkeypatch.setattr(bot, "get_products_by_manufacturer", lambda _m: [])
    assert bot._inventario_fabricante("securiton") is None


def test_el_fallo_no_se_cachea_y_el_exito_si(monkeypatch):
    llamadas = {"n": 0}

    def fake(_m):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise RuntimeError("db caida")
        return [("ASD535", 1)]

    monkeypatch.setattr(bot, "get_products_by_manufacturer", fake)
    assert bot._inventario_fabricante("securiton") is None   # fail-open → RAG
    assert bot._inventario_fabricante("securiton") is not None  # reintenta
    bot._inventario_fabricante("securiton")
    assert llamadas["n"] == 2                                # y el éxito se cachea


# ------------------------------------------------- la fuente: curado × activo, ordenado


class _Resp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


def test_fuente_curada_activos_y_paginacion_ordenada(monkeypatch):
    """Tres contratos en uno, contra un fake de la API REST:
    (a) el barrido de chunks lleva `order=id.asc` — la lección s304 como test;
    (b) un doc NO-activo se excluye del inventario aunque tenga chunks;
    (c) `unknown` no se lista."""
    peticiones = []

    class _Cliente:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None, params=None):
            peticiones.append((url, dict(params or {})))
            if "/documents" in url:
                return _Resp([{"source_pdf_filename": "DOC_A"},
                              {"source_pdf_filename": "DOC_B"}])
            return _Resp([
                {"source_file": "DOC_A", "product_model": "ASD535"},
                {"source_file": "DOC_B", "product_model": "unknown"},
                {"source_file": "DOC_RETIRADO", "product_model": "FANTASMA"},
            ])

    monkeypatch.setattr(retriever.httpx, "Client", _Cliente)
    productos = retriever.get_products_by_manufacturer("securiton")

    assert productos == [("ASD535", 1)]                  # activo sí; retirado y unknown no
    barridos = [p for u, p in peticiones if "/documents" not in u]
    assert barridos and all(p.get("order") == "id.asc" for p in barridos)


def test_dec059_intacto_el_fallthrough_de_modelo_no_se_toca():
    """La rama modelo+fabricante sigue cayendo a RAG (DEC-059, medido s77): la ruta
    nueva vive SOLO en la rama sin-modelo. Se ancla inspeccionando el fuente."""
    import inspect
    fuente = inspect.getsource(bot)
    # el inventario se sirve únicamente tras comprobar que NO hay modelo en la query
    idx_enum = fuente.index("_ENUM_FABRICANTE.search(query)")
    idx_rama_sin_modelo = fuente.index("# No model code, just a manufacturer name mentioned")
    assert idx_enum > idx_rama_sin_modelo
