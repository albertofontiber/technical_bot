"""s301 — «dashboard» sin app: los grifos de la telemetría ya construida (frente 6).

Contrato que se fija aquí:
  · cada respuesta del bot lleva RUTA (`route`) — los shortcuts ya no son invisibles
    en query_logs (#31), y el log de un shortcut jamás toca la respuesta (fire-and-forget);
  · el despliegue no puede romper el log: si el código llega ANTES que la migración
    s301, `log_query` reintenta SIN la columna (misma clase que el fallback de rag_trace)
    — perder el log Y el teclado de feedback por una carrera de deploy era el riesgo;
  · el export deja de tirar el PORQUÉ del voto negativo: `reason_class` y `comment`
    viajan junto al veredicto (hasta hoy, cero herramientas los leían);
  · la migración crea las vistas AGREGADAS (sin ids ni prosa) con security_invoker,
    y la marca de utilidad tiene por fin un camino de escritura (de OPERADOR, no del bot).
"""

import json
from pathlib import Path

import pandas as pd

import src.logging_db as logging_db
from src.logging_db import log_query

REPO = Path(__file__).parent.parent
MIGRACION = (
    REPO / "supabase" / "migration_proposals"
    / "20260806150000_s301_observabilidad_v1.sql"
)


class _Respuesta:
    """Habla el formato PostgREST real: el detector estricto exige `code` + json()."""

    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


def _falta_columna(nombre):
    return _Respuesta(400, {
        "code": "PGRST204",
        "message": f"Could not find the '{nombre}' column of 'query_logs' in the schema cache",
    })


class _ClienteFalso:
    def __init__(self, guion=None):
        self.guion = list(guion or [])
        self.posts: list[dict] = []

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, headers=None, json=None):
        self.posts.append(json)
        return self.guion.pop(0) if self.guion else _Respuesta()


# ------------------------------------------------------------------ la ruta


def test_log_query_lleva_la_ruta(monkeypatch):
    cliente = _ClienteFalso()
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert log_query(telegram_user_id=1, query="hola", route="greeting") is True
    assert cliente.posts[0]["route"] == "greeting"

    log_query(telegram_user_id=1, query="¿bornes del sensor?")
    assert cliente.posts[1]["route"] == "rag"          # el default es el pipeline


def test_si_la_columna_no_existe_el_log_no_se_pierde(monkeypatch):
    """La carrera de deploy: main auto-despliega y la migración la aplica Alberto a
    mano. Sin el fallback, CADA log fallaría — y con él el teclado de feedback
    (query_logged=False). Se reintenta sin la columna y se avisa una vez."""
    logging_db._route_compatibility_warning_emitted = False
    cliente = _ClienteFalso([_falta_columna("route"), _Respuesta(201)])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert log_query(telegram_user_id=1, query="hola", route="catalog_shortcut") is True
    assert len(cliente.posts) == 2
    assert "route" in cliente.posts[0]
    assert "route" not in cliente.posts[1]             # el reintento va sin la columna


def test_con_las_dos_columnas_ausentes_el_log_sobrevive(monkeypatch):
    """El caso REAL de producción (dúo s301): `rag_trace` tampoco existe — su migración
    de julio nunca se aplicó. Los manejadores de un solo tiro perdían el log cuando el
    400 nombraba la otra columna primero; el fallback componible itera."""
    from tests.test_rag_runtime_trace import _minimal_valid_trace

    cliente = _ClienteFalso([
        _falta_columna("rag_trace"), _falta_columna("route"), _Respuesta(201),
    ])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert log_query(telegram_user_id=1, query="q", route="rag",
                     rag_trace=_minimal_valid_trace()) is True
    assert len(cliente.posts) == 3
    assert "rag_trace" in cliente.posts[0] and "route" in cliente.posts[0]
    assert "rag_trace" not in cliente.posts[1] and "route" in cliente.posts[1]
    assert "rag_trace" not in cliente.posts[2] and "route" not in cliente.posts[2]


def test_la_violacion_del_CHECK_de_route_falla_ruidosa(monkeypatch):
    """H2 del dúo — el patrón de la casa: el fallback que protege el log NO puede
    comerse la ruta. Una violación del CHECK (23514, cuyo texto CONTIENE 'route' vía
    `query_logs_route_check`) es un bug del emisor: debe fallar, no colarse como fila
    sin ruta que `bot_uso_por_canal` cuenta como 'rag' en silencio."""
    cliente = _ClienteFalso([_Respuesta(400, {
        "code": "23514",
        "message": 'new row violates check constraint "query_logs_route_check"',
    })])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert log_query(telegram_user_id=1, query="x", route="rag") is False
    assert len(cliente.posts) == 1                     # SIN strip, SIN reintento


def test_un_400_ajeno_no_dispara_el_fallback(monkeypatch):
    cliente = _ClienteFalso([_Respuesta(400, {
        "code": "23502", "message": "null value in column query",
    })])
    monkeypatch.setattr(logging_db.httpx, "Client", cliente)

    assert log_query(telegram_user_id=1, query="x", route="rag") is False
    assert len(cliente.posts) == 1                     # sin reintento a ciegas


def test_las_consultas_loggean_su_ruta_y_la_cortesia_NO():
    """Anclado en el FUENTE (idioma del repo para ramas de transporte difíciles de
    ejercer sin Telegram). Dos contratos a la vez:

    (a) toda respuesta a una CONSULTA lleva ruta — incluidos los dos clarify que el
        dúo cazó respondiendo sin log;
    (b) la CORTESÍA no se registra: el aviso v7 lo promete literalmente («Los saludos
        y las despedidas no se registran») y la LIA usa esa minimización como
        argumento — loggearla fue el hallazgo CRÍTICO del cross-model s301."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    for ruta in ("catalog_shortcut", "manufacturer_mismatch",
                 "manufacturer_no_model", "clarify", "decline"):
        assert f'"{ruta}"' in fuente, f"consulta sin log de ruta: {ruta}"
    assert fuente.count('route="manufacturer_no_model"') == 2   # con y sin modelo
    for cortesia in ("greeting", "thanks", "bye"):
        assert f'route="{cortesia}"' not in fuente, (
            f"la cortesía {cortesia} se está loggeando: el aviso v7 promete que NO"
        )
    # Y la promesa sigue en el aviso (si un aviso futuro la quita, este test se
    # revisa JUNTO con la versión de términos, no en silencio).
    assert "Los saludos y las despedidas no se registran" in fuente


def test_los_shortcuts_loggeados_aseguran_el_seudonimo():
    """H7 del dúo: las rutas que SÍ escriben filas identificadas emiten el código —
    sin esto, un usuario solo-shortcuts exportaba como «(sin código)» hasta su
    primera consulta RAG."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    # 1 catalog + 1 mismatch + 2 no_model + el call-site original del camino RAG.
    assert fuente.count("asegurar_seudonimo(user_id)") >= 4


# ------------------------------------------------------------------ el export


def test_el_export_lleva_el_porque_del_voto():
    """El gap que motivó el frente: la prosa del 👎 (ForceReply, s294) y su motivo
    existían en la base y NINGUNA herramienta los leía."""
    from scripts.review_logs import _attach_tap_verdicts

    queries = pd.DataFrame([{"id": "q1", "query": "una"}, {"id": "q2", "query": "otra"}])
    votos = pd.DataFrame([
        {"query_log_id": "q1", "verdict": "down", "reason_class": "wrong",
         "comment": "la ruta del menú no es esa"},
        {"query_log_id": "q2", "verdict": "up", "reason_class": None, "comment": None},
    ])
    salida = _attach_tap_verdicts(queries, votos)

    fila = salida[salida["id"] == "q1"].iloc[0]
    assert fila["tap_verdict"] == "down"
    assert fila["tap_reason"] == "wrong"
    assert fila["tap_comment"] == "la ruta del menú no es esa"
    fila2 = salida[salida["id"] == "q2"].iloc[0]
    assert fila2["tap_verdict"] == "up"
    assert pd.isna(fila2["tap_reason"]) and pd.isna(fila2["tap_comment"])


def test_el_export_sin_votos_mantiene_las_columnas():
    from scripts.review_logs import _attach_tap_verdicts

    salida = _attach_tap_verdicts(pd.DataFrame([{"id": "q1"}]), pd.DataFrame())
    for col in ("tap_verdict", "tap_reason", "tap_comment"):
        assert col in salida.columns


# ------------------------------------------------------------------ la migración


def _sql() -> str:
    return MIGRACION.read_text(encoding="utf-8")


def test_la_migracion_crea_la_taxonomia_y_las_vistas():
    sql = _sql()
    assert "ADD COLUMN IF NOT EXISTS route" in sql
    for ruta in ("'rag'", "'catalog_shortcut'", "'clarify'", "'decline'",
                 "'manufacturer_mismatch'", "'manufacturer_no_model'",
                 "'greeting'", "'thanks'", "'bye'"):
        assert ruta in sql, f"taxonomía sin {ruta}"
    assert "RESERVADOS" in sql                          # la cortesía no se emite hoy
    for vista in ("bot_health_daily", "bot_health_semanal", "bot_feedback_semanal",
                  "bot_motivos_negativos", "bot_uso_por_canal"):
        assert f"CREATE OR REPLACE VIEW public.{vista}" in sql, f"falta la vista {vista}"
    # Sin security_invoker, una vista sobre query_logs perfora la RLS (lee como owner).
    assert sql.count("security_invoker = true") == 5
    # H1 del dúo: las CINCO en el REVOKE/GRANT (en entorno fresco, las 2 de salud
    # nacen aquí con los default privileges de la API y la postcondición abortaría).
    seccion_grants = sql.split("REVOKE ALL PRIVILEGES", 1)[1]
    for vista in ("bot_health_daily", "bot_health_semanal", "bot_feedback_semanal",
                  "bot_motivos_negativos", "bot_uso_por_canal"):
        assert vista in seccion_grants.split("GRANT SELECT")[0], f"{vista} sin REVOKE"
    # Y2 del dúo: sin el filtro de ruta, los shortcuts contaminan consultas_rag y
    # hunden los percentiles de latencia con ceros.
    assert sql.count("COALESCE(route, 'rag') = 'rag'") >= 8


def test_las_vistas_nuevas_no_exponen_ids_ni_prosa():
    """Agregados PUROS: la prosa se CUENTA (`con_comentario`), no se muestra — su canal
    es el export seudonimizado. El único id que tocan es para COUNT(DISTINCT)."""
    sql = _sql()
    nuevas = sql.split("3. Las vistas nuevas", 1)[1].split("4. Postcondiciones", 1)[0]
    assert "left(" not in nuevas.lower()
    assert "comment)" not in nuevas.replace("COUNT(*) FILTER (WHERE comment IS NOT NULL", "")
    for columna_cruda in ("SELECT telegram_user_id", "SELECT comment",
                          "SELECT feedback_text", "SELECT query"):
        assert columna_cruda not in nuevas


def test_bootstrap_y_migracion_convergen():
    """El bootstrap es el estado FINAL (DEC-180): la columna y las 3 vistas nuevas
    tienen que estar en los dos ficheros."""
    bootstrap = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS route" in bootstrap
    assert "query_logs_route_check" in bootstrap
    for vista in ("bot_feedback_semanal", "bot_motivos_negativos", "bot_uso_por_canal"):
        assert f"CREATE OR REPLACE VIEW {vista}" in bootstrap


# ------------------------------------------------------------------ la marca


def test_marcar_utilidad_estampa_marca_y_fecha_juntas():
    """El CHECK de coherencia de la base exige (utilidad IS NULL) = (fecha IS NULL):
    el camino de escritura del operador SIEMPRE las estampa juntas, y solo sobre
    filas sin revisar."""
    fuente = (REPO / "scripts" / "marcar_utilidad.py").read_text(encoding="utf-8")
    assert "SET utilidad = %s, utilidad_revisada_at = now()" in fuente
    assert "AND utilidad IS NULL" in fuente            # re-marcar exige decisión explícita
    assert "SUPABASE_SERVICE_KEY" not in fuente        # jamás la clave del bot
    assert "DATABASE_URL" in fuente


def test_la_taxonomia_del_operador_es_la_de_la_base():
    import scripts.marcar_utilidad as herramienta

    assert herramienta.UTILIDADES == ("corrigio", "gold", "corpus", "ninguna")
    assert herramienta.TABLAS == ("answer_feedback", "feedback")


# ------------------------------------------------------------------ las guardas


def test_las_guardas_de_ingesta_cortan_el_vacio():
    """El corpus vive SOLO en la carpeta OneDrive; desde el checkout de C:\\dev el
    inventario producía un manifiesto VACÍO con exit 0 y todo aguas abajo «funcionaba»
    sobre nada. Las tres etapas cortan ahora con SystemExit."""
    for fichero, ancla in (
        ("src/reingest/inventory.py", "inventario VACÍO"),
        ("src/reingest/extract.py", "está VACÍO: 0 entradas"),
        ("src/reingest/pipeline.py", "VACIO: 0 extracciones"),
    ):
        fuente = (REPO / fichero).read_text(encoding="utf-8")
        assert ancla in fuente, f"{fichero} sin guarda"
        assert "SystemExit" in fuente


def test_el_gold_gate_esta_en_ci():
    """El docstring de gold_store afirmaba que CI lo corría — y era falso."""
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python scripts/gold_store.py validate" in ci
