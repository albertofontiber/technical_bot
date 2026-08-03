"""s295 — retención RGPD: términos v4 + job de disociación sobre el rol dedicado.

Contrato que se fija aquí:
  · los términos declaran lo que REALMENTE pasa con los datos, y el texto está atado a
    `TERMS_VERSION` por un mapa de hashes (no por buena voluntad);
  · el job **no usa la clave del bot**: asume `rgpd_retencion` con `SET LOCAL ROLE`, para
    no abrirle superficie permanente a un proceso encendido 24/7;
  · el dry-run **ejecuta de verdad y revierte** — verifica el efecto, no el privilegio;
  · las 4 tablas van en UNA transacción: no existe la ejecución parcial;
  · cuando no puede cumplir, lo dice y sale con 2, en vez de aparentarlo;
  · la matriz declara sus pendientes en vez de disimularlos.
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.logging_db import TERMS_VERSION

REPO = Path(__file__).parent.parent
PROPUESTA = (
    REPO / "supabase" / "migration_proposals"
    / "20260803140000_s295_rgpd_rol_retencion_v2.sql"
)

# Ata TEXTO <-> VERSION. Un mapa (y no un único hash suelto) es lo que impide la evasión
# «edito el texto y actualizo el digest dejando la versión quieta»: reescribir la entrada
# de una versión ya publicada declara que dos textos distintos son el mismo contrato.
HASH_POR_VERSION = {
    "v4": "43e52a3df2e4dfea",
    "v5": "0e25de92dcc9f7db",
}


# ------------------------------------------------------------------ términos


def test_terms_version_es_tripwire():
    """Único pin EXACTO del proyecto. Los otros dos tests de términos (s286, s294)
    comprueban su propio dato + un suelo, para que una subida legítima no rompa tres
    tests a la vez sin señal."""
    assert TERMS_VERSION == "v5"


def test_el_texto_de_los_terminos_esta_atado_a_su_version():
    import src.bot.telegram_bot as bot

    digest = hashlib.sha256(bot._CONSENT_TERMS.encode("utf-8")).hexdigest()[:16]
    esperado = HASH_POR_VERSION.get(TERMS_VERSION)
    assert esperado is not None, (
        f"TERMS_VERSION={TERMS_VERSION} no tiene hash registrado: añade la entrada con el "
        f"digest del texto que se le muestra al técnico ({digest})."
    )
    assert digest == esperado, (
        f"_CONSENT_TERMS cambió (hash {digest}) sin subir TERMS_VERSION (sigue en "
        f"{TERMS_VERSION}). Si el cambio afecta a lo que se le promete al técnico, SUBE la "
        f"versión y añade su entrada — reescribir el hash de {TERMS_VERSION} declararía que "
        f"el texto viejo y el nuevo son el mismo contrato, y nadie re-aceptaría."
    )


def test_los_terminos_no_declaran_guardar_el_audio():
    """Se declaraba guardar el «audio original» y NO se guarda — declarar de más es tan
    incorrecto como declarar de menos."""
    import src.bot.telegram_bot as bot

    assert "audio original NO se guarda" in bot._CONSENT_TERMS
    assert "solo su transcripción" in bot._CONSENT_TERMS


def test_los_terminos_declaran_plazo_canal_y_transporte():
    """Telegram transporta TODO. Decir «no se comparten con nadie más» sin nombrarlo era
    declarar de menos."""
    import src.bot.telegram_bot as bot

    terms = bot._CONSENT_TERMS
    assert "24 meses" in terms
    assert "info@fontiber.com" in terms
    assert "viaja por *Telegram*" in terms     # el transporte, no solo «tu ID de Telegram»
    # Los cinco encargados que la matriz lista tienen que estar TAMBIEN aqui: declarar de
    # menos ante quien consiente es el mismo defecto que declarar de mas.
    for encargado in ("Anthropic", "Voyage AI", "OpenAI", "Supabase", "Railway"):
        assert encargado in terms, f"los terminos no declaran a {encargado}"
    assert "fuera de la UE" in terms           # la transferencia internacional


def test_el_audio_se_borra_tras_transcribir():
    """La afirmación de los términos se sostiene en el código, no en mi palabra: el
    `unlink` va en un `finally`, así que cubre también el fallo de la transcripción."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    ini = fuente.index("tmp_path")
    assert "finally" in fuente[ini : fuente.index("unlink(missing_ok=True)", ini)]


def test_la_pregunta_no_va_al_log_del_proceso():
    """El log del worker vive en Railway, fuera de la matriz y de cualquier supresión a
    petición. La pregunta es texto libre del técnico: puede identificar."""
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    assert "Error processing query '{query}'" not in fuente
    assert "Error processing query (len=%d)" in fuente


# ------------------------------------------------------------------ el corte


def test_corte_en_meses_de_calendario_con_reloj_inyectable():
    from scripts.rgpd_retencion import corte

    limite = corte(24, ahora=datetime(2028, 3, 31, tzinfo=timezone.utc))
    assert (limite.year, limite.month, limite.day) == (2026, 3, 31)   # no 720 días


def test_corte_recorta_el_dia_cuando_el_mes_destino_es_mas_corto():
    from scripts.rgpd_retencion import corte

    limite = corte(1, ahora=datetime(2028, 3, 31, tzinfo=timezone.utc))
    assert (limite.year, limite.month, limite.day) == (2028, 2, 29)   # bisiesto; nunca 31


def test_no_hay_flag_que_pueda_contradecir_la_politica():
    """La ventana la fija la POLITICA RLS. Un `--meses` mentiría en las dos direcciones:
    uno mayor terminaría «con éxito» dejando filas vencidas sin tratar, uno menor anunciaría
    un corte que la base filtra en silencio."""
    import scripts.rgpd_retencion as job

    acciones = {a.dest for a in job._construir_parser()._actions}
    assert "meses" not in acciones
    assert job.VENTANA_MESES == 24


def test_el_parser_real_tiene_el_default_en_dry_run():
    """Se interroga el parser DEL SCRIPT, no uno paralelo construido en el test."""
    import scripts.rgpd_retencion as job

    args = job._construir_parser().parse_args([])
    assert args.aplicar is False
    assert args.recibo is None


# ------------------------------------------------------------------ el alcance


def test_los_objetivos_cubren_el_ciclo_completo_no_solo_el_padre():
    """Disociar solo `query_logs` no anonimiza: las hijas conservan el identificador y se
    unen por `query_log_id`; el CASCADE de sus FK solo actúa al BORRAR el padre."""
    from scripts.rgpd_retencion import OBJETIVOS

    assert {o.tabla: o.modo for o in OBJETIVOS} == {
        "query_logs": "nulificar",
        "feedback": "nulificar",
        "answer_feedback": "nulificar",
        "answer_messages": "borrar",     # mapeo operativo caduco: se borra, no se disocia
    }


def test_cada_sentencia_acota_por_fecha_y_devuelve_recibo():
    from scripts.rgpd_retencion import OBJETIVOS

    for obj in OBJETIVOS:
        sql = obj.sentencia()
        assert f"{obj.columna_fecha} < %s" in sql          # nunca sin cota temporal
        assert f"{obj.columna_id} IS NOT NULL" in sql      # idempotente
        assert sql.rstrip().endswith("RETURNING id")       # el recibo es parte del trabajo
        assert sql.startswith("DELETE" if obj.modo == "borrar" else "UPDATE")


# ------------------------------------------------------------------ la ejecución


class _CursorFalso:
    def __init__(self, registro):
        self.registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.registro["sql"].append((sql, params))

    def fetchall(self):
        return [("id-1",), ("id-2",)]

    def fetchone(self):
        # El job comprueba `current_user` tras asumir el rol: la conexión falsa responde
        # como si lo hubiera asumido. El caso contrario tiene su propio test contra
        # Postgres real (`test_el_job_aborta_si_el_rol_no_se_asumio`).
        from scripts.rgpd_retencion import ROL
        return (ROL,)


class _ConexionFalsa:
    def __init__(self):
        self.registro = {"sql": [], "commit": 0, "rollback": 0}

    def cursor(self):
        return _CursorFalso(self.registro)

    def commit(self):
        self.registro["commit"] += 1

    def rollback(self):
        self.registro["rollback"] += 1


def test_el_dry_run_ejecuta_de_verdad_y_revierte():
    """La diferencia con la versión anterior: no se sondea un conjunto vacío, se ejecutan
    las sentencias REALES y se hace ROLLBACK. Así privilegios y constraints quedan
    evaluados sobre filas de verdad — el falso OK de `answer_feedback` (columna NOT NULL)
    no puede repetirse."""
    from scripts.rgpd_retencion import OBJETIVOS, ejecutar

    conexion = _ConexionFalsa()
    resultado = ejecutar(datetime(2028, 1, 1, tzinfo=timezone.utc), False, conexion)

    assert conexion.registro["rollback"] == 1
    assert conexion.registro["commit"] == 0
    assert len(resultado) == len(OBJETIVOS)
    assert resultado["query_logs"]["tocadas"] == 2


def test_aplicar_confirma_la_transaccion():
    from scripts.rgpd_retencion import ejecutar

    conexion = _ConexionFalsa()
    ejecutar(datetime(2028, 1, 1, tzinfo=timezone.utc), True, conexion)

    assert conexion.registro["commit"] == 1
    assert conexion.registro["rollback"] == 0


def test_asume_el_rol_acotado_antes_de_tocar_nada():
    """Sin `SET LOCAL ROLE` correría con los privilegios del operador y podría exceder su
    mandato. Tiene que ser la PRIMERA sentencia."""
    from scripts.rgpd_retencion import ROL, ejecutar

    conexion = _ConexionFalsa()
    ejecutar(datetime(2028, 1, 1, tzinfo=timezone.utc), False, conexion)

    primera = conexion.registro["sql"][0][0]
    assert primera.strip().upper().startswith("SET LOCAL ROLE")
    assert ROL in primera


def test_las_cuatro_tablas_van_en_una_sola_transaccion():
    """Atomicidad: o se hace todo o no se hace nada. Es lo que elimina de raíz la
    ejecución parcial e irreversible (un commit por tabla dejaría `query_logs` disociado
    y el resto intacto: ni cumple ni se puede repetir limpio)."""
    from scripts.rgpd_retencion import OBJETIVOS, ejecutar

    conexion = _ConexionFalsa()
    ejecutar(datetime(2028, 1, 1, tzinfo=timezone.utc), True, conexion)

    # arranque (SET LOCAL ROLE + statement_timeout + SELECT current_user) + una sentencia
    # por objetivo, y UN solo commit al final.
    assert len(conexion.registro["sql"]) == 3 + len(OBJETIVOS)
    assert conexion.registro["commit"] == 1


def test_un_fallo_a_mitad_revierte_y_propaga():
    from scripts.rgpd_retencion import ejecutar

    class _Explota(_ConexionFalsa):
        def cursor(self):
            class _C(_CursorFalso):
                def execute(self, sql, params=None):
                    super().execute(sql, params)
                    if "answer_feedback" in sql:
                        raise RuntimeError("boom")
            return _C(self.registro)

    conexion = _Explota()
    try:
        ejecutar(datetime(2028, 1, 1, tzinfo=timezone.utc), True, conexion)
    except RuntimeError:
        pass
    else:
        raise AssertionError("el fallo debe propagarse, no tragarse")

    assert conexion.registro["rollback"] == 1
    assert conexion.registro["commit"] == 0


def test_el_job_no_usa_la_clave_del_bot():
    """El eje entero del diseño: `service_role` es la identidad del worker de Railway
    encendido 24/7. Si este script volviera a usarla, el rol dedicado no serviría de nada."""
    fuente = (REPO / "scripts" / "rgpd_retencion.py").read_text(encoding="utf-8")
    assert "SUPABASE_SERVICE_KEY" not in fuente
    assert "DATABASE_URL" in fuente


def test_sin_el_rol_lo_dice_y_sale_con_dos(monkeypatch, capsys):
    """Un job de retención que no puede ejecutarse APARENTA cumplimiento, que es peor que
    no tenerlo."""
    import scripts.rgpd_retencion as job

    def _falla(*a, **k):
        raise RuntimeError('role "rgpd_retencion" does not exist')

    monkeypatch.setattr(job, "ejecutar", _falla)
    monkeypatch.setattr(sys, "argv", ["rgpd_retencion.py", "--aplicar"])

    assert job.main() == 2
    salida = capsys.readouterr().out
    assert "NO PUEDE CUMPLIR LA RETENCION" in salida
    assert "20260803140000_s295_rgpd_rol_retencion_v2.sql" in salida   # dice qué falta


def test_el_diagnostico_distingue_las_causas():
    from scripts.rgpd_retencion import _diagnosticar

    assert "NO EXISTE" in _diagnosticar(RuntimeError('role "rgpd_retencion" does not exist'))
    assert "privilegios" in _diagnosticar(RuntimeError("permission denied for table x"))
    assert "DROP NOT NULL" in _diagnosticar(
        RuntimeError('null value violates not-null constraint')
    )


# ------------------------------------------------------------------ la propuesta


def test_la_propuesta_no_esta_en_el_camino_auto_aplicado():
    assert PROPUESTA.exists()
    assert not list((REPO / "supabase" / "migrations").glob("*s295*"))


def test_la_propuesta_crea_un_rol_acotado_y_no_toca_service_role():
    sql = PROPUESTA.read_text(encoding="utf-8")
    assert "CREATE ROLE rgpd_retencion" in sql
    assert "NOLOGIN NOINHERIT" in sql and "NOBYPASSRLS" in sql
    assert "GRANT rgpd_retencion TO postgres WITH INHERIT FALSE" in sql
    # Nunca a `authenticator`: esto NO se ejerce por HTTP, y no darle ese camino es parte
    # del punto.
    assert "GRANT rgpd_retencion TO authenticator" not in sql
    # El hardening de julio queda EXACTAMENTE como estaba, y hay postcondición que lo ancla.
    assert "TO service_role" not in sql
    assert "el hardening" in sql and "EXACTAMENTE como estaba" in sql


def test_la_propuesta_concede_columnas_y_no_deja_leer_el_contenido():
    sql = PROPUESTA.read_text(encoding="utf-8")
    assert "GRANT UPDATE (telegram_user_id) ON public.query_logs" in sql
    assert "GRANT UPDATE ON public.query_logs" not in sql        # nunca la tabla entera
    assert "no debe poder LEER query_logs" in sql                # postcondición


def test_la_ventana_de_24_meses_vive_en_la_base():
    """Lo que convierte el plazo en invariante del motor: aunque el script se equivoque,
    la política RLS del rol no le deja tocar una fila reciente."""
    sql = PROPUESTA.read_text(encoding="utf-8")
    assert sql.count("CREATE POLICY rgpd_retencion_ventana") == 4      # las 4 tablas
    assert sql.count("created_at < now() - interval '24 months'") >= 4


def test_la_propuesta_declara_su_rollback_y_su_limite():
    sql = PROPUESTA.read_text(encoding="utf-8")
    assert "ROLLBACK" in sql
    assert "NO EJECUTAR" in sql                                   # banner de propuesta
    assert "deja de ser posible tras la primera ejecucion real" in sql.replace("ó", "o")


# ------------------------------------------------------------------ la matriz


def test_la_matriz_declara_lo_que_de_verdad_pasa():
    crudo = (REPO / "docs" / "RGPD_RETENCION.md").read_text(encoding="utf-8").lower()
    # El markdown parte frases por el ancho de línea: se normalizan los espacios para que
    # el test compruebe el CONTENIDO y no dónde cayó el salto.
    doc = " ".join(crudo.replace("*", " ").replace(">", " ").split())
    for marca in (
        "24 meses",
        "info@fontiber.com",
        "eu-north-1",
        "no se almacena",           # el audio
        "asumido firmado",          # los DPA son ASUNCIÓN declarada, no hecho
        "seudonimización",          # NO se llama anonimización a lo que no lo es
        "answer_messages",          # la hija que conserva el chat_id
        "review_logs.py",           # el export a disco, fuera de Supabase
        "telegram",                 # el transporte también es encargado
        "railway",                  # los logs del worker
        "no desbloquea",            # el gate de `convo` sigue cerrado
    ):
        assert marca in doc, f"la matriz no declara: {marca}"
