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
#
# Cubre las DOS CAPAS. Al mover el detalle a `_PRIVACY_DETAIL` se quedó fuera del tripwire,
# así que se podía cambiar un destinatario, una finalidad o un plazo manteniendo v5 y sin
# que nadie re-aceptara: el agujero lo abrí yo con el refactor. El contrato es lo que se le
# muestra al técnico, esté en la capa que esté.
HASH_POR_VERSION = {
    "v4": "43e52a3df2e4dfea",              # capa única (antes del aviso en dos capas)
    "v5": "1600bb5d68033a84",
    "v6": "18a139c87ac30a35",              # sha256(capa1 + SEPARADOR + capa2)
    "v7": "d7472689b771c121",              # s296: reconocimiento de aportaciones
}


# Separador literal entre capas: no puede aparecer en el texto y no depende de escapes.
SEPARADOR = "<<<CAPA-2>>>"


def _huella_del_aviso() -> str:
    import hashlib

    import src.bot.telegram_bot as bot

    crudo = bot._CONSENT_TERMS + SEPARADOR + bot._PRIVACY_DETAIL
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ términos


def test_terms_version_es_tripwire():
    """Único pin EXACTO del proyecto. Los otros dos tests de términos (s286, s294)
    comprueban su propio dato + un suelo, para que una subida legítima no rompa tres
    tests a la vez sin señal."""
    assert TERMS_VERSION == "v7"


def test_el_texto_de_los_terminos_esta_atado_a_su_version():
    import src.bot.telegram_bot as bot

    digest = _huella_del_aviso()
    esperado = HASH_POR_VERSION.get(TERMS_VERSION)
    assert esperado is not None, (
        f"TERMS_VERSION={TERMS_VERSION} no tiene hash registrado: añade la entrada con el "
        f"digest de LAS DOS CAPAS que se le muestran al técnico ({digest})."
    )
    assert digest == esperado, (
        f"el aviso cambió (hash {digest}) sin subir TERMS_VERSION (sigue en "
        f"{TERMS_VERSION}). Si el cambio afecta a lo que se le promete al técnico, SUBE la "
        f"versión y añade su entrada — reescribir el hash de {TERMS_VERSION} declararía que "
        f"el texto viejo y el nuevo son el mismo contrato, y nadie re-aceptaría."
    )


def test_la_primera_capa_lleva_lo_imprescindible():
    """Aviso en DOS capas. La primera es lo que hay que saber ANTES de aceptar: qué se
    guarda, cuánto, quién lo ve, que hay terceros fuera de la UE, y el canal de derechos."""
    import src.bot.telegram_bot as bot

    terms = bot._CONSENT_TERMS
    assert "audio original NO se guarda" in terms
    assert "24 meses" in terms
    assert "info@fontiber.com" in terms
    assert "fuera de la UE" in terms
    assert "/privacidad" in terms              # el puente a la segunda capa


def test_la_primera_capa_no_vuelve_a_ser_un_muro():
    """Llegó a 1.803 caracteres y 25 líneas. Un aviso que nadie lee no informa a nadie: el
    detalle se movió a `/privacidad`. Este techo es el que impide que vuelva a crecer sin
    que alguien lo decida."""
    import src.bot.telegram_bot as bot

    assert len(bot._CONSENT_TERMS) <= 1000, (
        f"la aceptación creció a {len(bot._CONSENT_TERMS)} chars: si es detalle, va a "
        f"`_PRIVACY_DETAIL`; si de verdad es imprescindible antes de aceptar, sube el techo "
        f"a conciencia."
    )


def test_la_segunda_capa_declara_a_todos_los_encargados_por_categoria():
    """Los destinatarios se describen por CATEGORÍA con la lista actual («búsqueda en los
    manuales: Voyage AI»), que es lo que pide el RGPD. Así, cambiar de proveedor dentro de
    la misma categoría no altera lo aceptado — y los cinco de la matriz aparecen."""
    import src.bot.telegram_bot as bot

    detalle = bot._PRIVACY_DETAIL
    # Los encargados se leen de la MATRIZ, no de una lista escrita aquí: si mañana se añade
    # uno al documento y no al aviso, este test cae. Con la lista hardcodeada el test era
    # circular — se comprobaba a sí mismo.
    matriz = (REPO / "docs" / "RGPD_RETENCION.md").read_text(encoding="utf-8")
    seccion = matriz.split("## Encargados de tratamiento", 1)[1].split("\n## ", 1)[0]
    encargados = [
        fila.split("|")[1].replace("*", "").strip()
        for fila in seccion.splitlines()
        if fila.startswith("| **")
    ]
    assert len(encargados) >= 5, f"no se pudo leer la tabla de encargados: {encargados}"
    for encargado in encargados:
        assert encargado in detalle, f"el detalle no declara a {encargado} (sí está en la matriz)"
    for categoria in ("Canal de mensajería", "Generación de la respuesta",
                      "Búsqueda en los manuales", "Transcripción de audio",
                      "Almacenamiento", "Ejecución del bot"):
        assert categoria in detalle, f"falta la categoría: {categoria}"
    assert "fuera de la UE" in detalle
    assert "solo su transcripción" in detalle


def test_la_segunda_capa_lleva_lo_que_un_aviso_debe_llevar():
    """Se llamaba «detalle completo» y le faltaban puntos del artículo 13: responsable, base
    jurídica, cómo retirar el consentimiento, reclamación ante la autoridad de control y
    transferencias. Declararlos solo en una matriz interna no informa a nadie."""
    import src.bot.telegram_bot as bot

    detalle = bot._PRIVACY_DETAIL
    for marca in ("*Responsable*", "Fontiber Industrial Partners, S.L.", "B24984759",
                  "28004 Madrid", "*Base jurídica*", "Retirar el consentimiento",
                  "Agencia Española", "Transferencias",
                  # s296: usar el feedback para reconocer o incentivar es una DECISION
                  # sobre la persona. El aviso decia literalmente lo contrario.
                  "Reconocimiento de aportaciones", "la toma una persona"):
        assert marca in detalle, f"el aviso no informa de: {marca}"


def test_las_dos_capas_son_enviables_por_telegram():
    """Ambas se mandan con `parse_mode="Markdown"`: si un `*`, `_` o backtick queda sin
    cerrar, Telegram **rechaza el mensaje entero** y el aviso no llega — el técnico se
    quedaría sin poder leerlo, o sin poder aceptar. No se ve revisando el texto a ojo."""
    import src.bot.telegram_bot as bot

    for nombre, txt in (("_CONSENT_TERMS", bot._CONSENT_TERMS),
                        ("_PRIVACY_DETAIL", bot._PRIVACY_DETAIL)):
        for marca in ("*", "_", "`"):
            assert txt.count(marca) % 2 == 0, (
                f"{nombre} tiene un {marca!r} sin cerrar: Telegram rechazaría el mensaje"
            )
        assert len(txt) <= 4096, f"{nombre} excede el límite de Telegram"


def test_el_aviso_declara_el_nombre_que_se_pide_en_accept():
    """`/accept [tu nombre]` guarda `display_name` en `user_consent`. Se recogía sin
    declararlo en ninguna capa."""
    import src.bot.telegram_bot as bot

    assert "nombre que nos des" in bot._CONSENT_TERMS
    assert "nombre que nos des" in bot._PRIVACY_DETAIL


def test_la_segunda_capa_se_puede_leer_sin_haber_aceptado():
    """Condición para que la primera capa cuente como informada: el detalle tiene que estar
    accesible ANTES de aceptar. Se comprueba que el handler NO consulta el consentimiento."""
    import inspect

    import src.bot.telegram_bot as bot

    cuerpo = inspect.getsource(bot.privacy_command)
    assert "has_consent" not in cuerpo
    assert "_PRIVACY_DETAIL" in cuerpo


def test_privacidad_esta_registrado_y_listado():
    fuente = (REPO / "src" / "bot" / "telegram_bot.py").read_text(encoding="utf-8")
    assert 'CommandHandler("privacidad", privacy_command)' in fuente
    assert "/privacidad - " in fuente          # visible en /help, no un comando oculto


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
        assert "RETURNING" in sql                          # el recibo es parte del trabajo
        assert sql.startswith("DELETE" if obj.modo == "borrar" else "UPDATE")
        if obj.modo == "nulificar":
            # s296: estampa el seudónimo Y retira el identificador en la MISMA sentencia.
            # Separarlas dejaría una ventana en la que la fila no tiene ni lo uno ni lo otro.
            assert "SET seudonimo = p.seudonimo" in sql
            assert f"{obj.columna_id} = NULL" in sql


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
    # Las 4 tablas + la destrucción del vínculo, que es la 5ª entrada del recibo.
    assert len(resultado) == len(OBJETIVOS) + 1
    assert resultado["query_logs"]["tocadas"] == 2
    assert "persona_seudonimo" in resultado


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

    # arranque (SET LOCAL ROLE + statement_timeout + SELECT current_user) + 3 emisiones de
    # código que falte + una sentencia por objetivo + la destrucción del vínculo, y UN solo
    # commit al final.
    assert len(conexion.registro["sql"]) == 3 + 3 + len(OBJETIVOS) + 1
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
        "base jurídica",            # el lever de fondo, declarado como [DECIDIR]
        "interés legítimo",         # la recomendación, no una vaguedad
        "/privacidad",              # el aviso en dos capas
    ):
        assert marca in doc, f"la matriz no declara: {marca}"
