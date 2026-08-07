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
    "listado de detectores de aritech",
    "¿qué documentación de Notifier tienes?",
    "what Securiton products do you have?",          # EN mínimo (Sol s307)
    "list of Notifier panels",
])
def test_la_intencion_de_inventario_casa(q):
    assert bot._intencion_inventario(q)


def test_la_variante_con_nombre_de_marca_casa():
    """«catálogo de securiton» no lleva sustantivo de inventario — casa por la
    variante dinámica con el nombre del fabricante."""
    assert not bot._ENUM_FABRICANTE.search("catálogo de securiton")
    assert bot._intencion_inventario("catálogo de securiton", "securiton")


@pytest.mark.parametrize("q", [
    "tengo un problema con mi central notifier",     # avería ≠ inventario
    "¿qué central de notifier me recomiendas?",      # recomendación ≠ inventario
    "la central de securiton no arma la zona 3",
    "cómo conecto el detector de kidde",
    # Los 6 casos de COLISIÓN del dúo (H2: la v1 los desviaba TODOS al listado —
    # «lista de eventos/averías» es vocabulario nuclear de la UI de centrales):
    "¿cómo veo la lista de averías en la central Notifier?",
    "la central Morley muestra avería en la lista de eventos",
    "cómo borro la lista de eventos de la central kidde",
    "¿qué centrales Notifier tienen salida de relé?",         # specs, no inventario
    "¿qué información hay sobre el conexionado de la central Detnov?",
    "¿qué central de la gama Morley me recomiendas para 4 lazos?",
    # Y los 2 de Sol:
    "¿qué centrales Notifier tienen el fallo 77?",
    "la lista de zonas de mi central Notifier",
])
def test_averias_recomendaciones_y_specs_NO_casan(q):
    assert not bot._intencion_inventario(q, "notifier")


# ------------------------------------------------------------- la respuesta y su caché


@pytest.fixture(autouse=True)
def _cache_limpia():
    bot._inventario_cache.clear()
    yield
    bot._inventario_cache.clear()


def test_el_inventario_lista_TODO_lo_que_devuelve_la_fuente(monkeypatch):
    """El defecto era una enumeración parcial presentada como completa: la respuesta
    debe llevar CADA referencia de la fuente — incluidas las que el RAG se dejó."""
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda _m: [("ASD535", 1), ("ASD531", 1), ("ADW535", 1)])
    texto = bot._inventario_fabricante("securiton")
    assert "*ASD535*" in texto and "*ASD531*" in texto and "*ADW535*" in texto
    assert "3 referencias" in texto


def test_el_mensaje_queda_acotado_bajo_el_limite_de_telegram(monkeypatch):
    """Dúo H1: el inventario de Notifier medía 4.377 chars > 4.096 → BadRequest sin
    handler = el técnico recibía NADA. La cota es por CONSTRUCCIÓN: con 300
    referencias el texto cabe y el resto se resume en «…y N más»."""
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda _m: [(f"MODELO-{i:03d}", 2) for i in range(300)])
    texto = bot._inventario_fabricante("notifier")
    assert len(texto) < 4000
    assert "referencias más" in texto


def test_los_metacaracteres_de_markdown_se_sirven_planos(monkeypatch):
    """Sol s307: un `_` o `*` suelto en un product_model rompe el parse_mode
    Markdown de Telegram → BadRequest."""
    monkeypatch.setattr(bot, "get_products_by_manufacturer",
                        lambda _m: [("40_40L*", 1)])
    texto = bot._inventario_fabricante("x")
    assert "40_40L" not in texto and "40 40L" in texto


def test_tras_un_fallo_hay_backoff_no_un_timeout_por_turno(monkeypatch):
    """Dúo H5: httpx síncrono en handler async — con la DB caída, SIN backoff cada
    consulta pagaba el timeout entero bloqueando el event loop."""
    llamadas = {"n": 0}

    def fake(_m):
        llamadas["n"] += 1
        raise RuntimeError("db caida")

    monkeypatch.setattr(bot, "get_products_by_manufacturer", fake)
    monkeypatch.setattr(bot, "_inventario_falla_ts", 0.0)
    assert bot._inventario_fabricante("securiton") is None
    assert bot._inventario_fabricante("securiton") is None   # dentro del backoff
    assert llamadas["n"] == 1                                # NO paga 2o timeout


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
    monkeypatch.setattr(bot, "_inventario_falla_ts", 0.0)
    assert bot._inventario_fabricante("securiton") is None   # fail-open → RAG
    monkeypatch.setattr(bot, "_inventario_falla_ts", 0.0)    # backoff vencido
    assert bot._inventario_fabricante("securiton") is not None  # reintenta
    bot._inventario_fabricante("securiton")
    assert llamadas["n"] == 2                                # y el éxito se cachea


def test_marca_fuera_del_regex_se_resuelve_contra_la_db(monkeypatch):
    """Dúo F2: «¿qué productos de Xtralis tienes?» reproducía el fallo Securiton —
    Xtralis no está en _MANUFACTURER_NAMES. La resolución va contra la lista REAL."""
    monkeypatch.setattr(bot, "_marcas_db_cache",
                        ["Xtralis", "Argus Security", "System Sensor", "LDA audioTech"])
    assert bot._marca_en_consulta("¿qué productos de Xtralis tienes?") == "Xtralis"
    assert bot._marca_en_consulta("productos de argus") == "Argus Security"
    assert bot._marca_en_consulta("productos de lda") is None   # 3 chars: fuera (#67)
    assert bot._marca_en_consulta("no menciona marca alguna") is None


# ------------------------------------------------- la fuente: curado × activo, ordenado


class _Resp:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


def test_fuente_curada_activos_por_document_id_y_paginacion(monkeypatch):
    """Cuatro contratos contra un fake de la API REST:
    (a) el cruce va por DOCUMENT_ID — la clave del serving; el dúo (F1) cazó a la v1
        cruzando por nombre de fichero: los lotes s55 nombran distinto en cada lado y
        SEIS marcas devolvían inventario vacío en silencio;
    (b) document_id NULL = legacy → se CONSERVA (regla de _filter_by_document_status);
    (c) doc no-activo excluido; unknown no se lista;
    (d) la paginación usa page=1000 EXACTO y sigue mientras la página venga LLENA —
        Sol cazó que con page=5000 el cap de PostgREST (1000) hacía len<page SIEMPRE
        y el barrido cortaba tras la primera página."""
    peticiones = []
    pagina_llena = [{"source_file": "DOC_A", "product_model": "ASD535",
                     "document_id": "D1"}] * 1000

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
                return _Resp([{"id": "D1"}, {"id": "D2"}])
            if int(params.get("offset", 0)) == 0:
                return _Resp(pagina_llena)              # página LLENA → debe seguir
            return _Resp([
                {"source_file": "DOC_B", "product_model": "LEGACY-PM",
                 "document_id": None},                   # legacy: se conserva
                {"source_file": "DOC_C", "product_model": "FANTASMA",
                 "document_id": "D_RETIRADO"},           # no activo: fuera
                {"source_file": "DOC_D", "product_model": "unknown",
                 "document_id": "D2"},                   # unknown: fuera
            ])

    monkeypatch.setattr(retriever.httpx, "Client", _Cliente)
    productos = retriever.get_products_by_manufacturer("securiton")

    assert ("ASD535", 1) in productos and ("LEGACY-PM", 1) in productos
    assert all(pm not in ("FANTASMA", "unknown") for pm, _ in productos)
    barridos = [p for u, p in peticiones if "/documents" not in u]
    assert len(barridos) == 2                           # siguió tras la página llena
    assert all(p.get("order") == "id.asc" and p.get("limit") == "1000"
               for p in barridos)


def test_dec059_intacto_el_fallthrough_de_modelo_no_se_toca():
    """La rama modelo+fabricante sigue cayendo a RAG (DEC-059, medido s77): la ruta
    nueva vive SOLO en la rama sin-modelo. Se ancla inspeccionando el fuente."""
    import inspect
    fuente = inspect.getsource(bot)
    # el inventario se sirve únicamente tras comprobar que NO hay modelo en la query
    idx_enum = fuente.index("_intencion_inventario(query, mentioned_manufacturer)")
    idx_rama_sin_modelo = fuente.index("# No model code, just a manufacturer name mentioned")
    assert idx_enum > idx_rama_sin_modelo
    # y el paso 5-bis (marcas fuera del regex) también exige no-modelo antes de servir
    assert "not extract_product_models(query)" in fuente
