"""s295 — retención RGPD: términos + la propuesta del rol dedicado + la matriz.

Contrato que se fija aquí:
  · los términos declaran lo que REALMENTE pasa con los datos, y el texto está atado a
    `TERMS_VERSION` por un mapa de hashes (no por buena voluntad);
  · el job **no usa la clave del bot**. Desde s299 la pasada es UNA función en la base
    (`rgpd_retencion_pasada`, la misma que ejecuta pg_cron) y el script es su driver —
    los tests del driver y de la migración s299 viven en `test_s299_job_programado.py`;
  · cuando no puede cumplir, lo dice y sale con 2, en vez de aparentarlo;
  · la matriz declara sus pendientes en vez de disimularlos.
"""

import hashlib
import sys
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
    "v7": "d9b4b91872b3e569",              # s296: reconocimiento de aportaciones
    # s324f: apertura del piloto a Directores Generales. Cuatro cambios, todos en lo
    # que se le PROMETE al técnico, y por eso sube la versión en vez de reescribirse
    # el hash de v7: (1) se anuncia como versión en desarrollo y se advierte de que no
    # sustituye al manual ni al criterio de un técnico cualificado — el bloque va
    # ANTES del de datos porque es el que protege a quien vaya a usar una respuesta en
    # una instalación real; (2) «Notifier, Morley y Detnov» → «una treintena de
    # fabricantes» (el v7 se quedó corto: 30 en corpus, y una lista cerrada caduca);
    # (3) Fontiber es el responsable AUNQUE el usuario trabaje en otra empresa del
    # grupo, que es el caso de los DGs que entran ahora; (4) el reconocimiento de
    # aportaciones aplica a todo el mundo, y la retirada del consentimiento se explica
    # en las dos capas.
    "v8": "69e913f8583a614a",
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
    assert TERMS_VERSION == "v8"


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
    que alguien lo decida.

    (s324f) Techo 1000 → 1400, subido a conciencia como el propio test pedía, y por dos
    decisiones de producto de Alberto que van en la capa 1 precisamente porque hay que
    leerlas ANTES de aceptar:
      · la advertencia de que el sistema está EN DESARROLLO y **no sustituye al manual
        oficial ni al criterio de un técnico cualificado** — es lo que protege a quien
        vaya a usar una respuesta en una instalación real, y esconderla en `/privacidad`
        sería esconder justo lo importante;
      · que el responsable es Fontiber **aunque el usuario trabaje en otra empresa del
        grupo**, que es la situación de los DGs que entran con el piloto.
    Todo lo que no era promesa se recortó antes de tocar el techo. Sigue muy por debajo
    de los 1.803 que motivaron este test.
    """
    import src.bot.telegram_bot as bot

    assert len(bot._CONSENT_TERMS) <= 1400, (
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


# ------------------------------------------------------------------ el driver
# (El corte ya no se calcula en Python: lo devuelve la base — la MISMA expresión que las
# políticas RLS — así que los tests de calendario murieron con el código que probaban.)


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


# ------------------------------------------------------------------ la ejecución
# (Los tests de la pasada — dry-run que revierte, atomicidad, emisión de códigos, punto
# de no retorno — viven donde vive la pasada: `test_s299_job_programado.py` para el
# driver y `test_s295_rgpd_integracion_pg.py` para la función contra Postgres real.)


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
    # s298: la cola esta APLICADA en produccion (5-ago) -- el banner cambio de proposito:
    # ya no avisa "no ejecutar" sino que declara el estado y que re-ejecutar es seguro.
    assert "APLICADA EN PRODUCCI" in sql
    assert "IDEMPOTENTE" in sql
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


# ------------------------------------------------------------------ el export


def test_el_export_agrupa_por_codigo_DESDE_HOY():
    """El fallo que cazó el dúo: `_seudonimizar` leía el código de `query_logs.seudonimo`,
    que SOLO se rellena al vencer el plazo. Hasta 2028 todas las filas caían en el mismo
    literal «(sin código)» — es decir, la agrupación que justifica todo esto no existía
    justo en el periodo en que hace falta. No se veía porque la columna existe y el código
    «funcionaba»: el fallo estaba en de dónde venía el dato."""
    import pandas as pd

    from scripts.review_logs import _seudonimizar

    correspondencias = {111: "codigo-A", 222: "codigo-B"}
    df = pd.DataFrame([
        {"telegram_user_id": 111, "query": "una", "seudonimo": None},
        {"telegram_user_id": 111, "query": "otra", "seudonimo": None},
        {"telegram_user_id": 222, "query": "de otro", "seudonimo": None},
        # Fila YA disociada: no tiene identificador, y su código es lo único que queda.
        {"telegram_user_id": None, "query": "vieja", "seudonimo": "codigo-A"},
    ])
    salida = _seudonimizar(df, correspondencias)

    assert "telegram_user_id" not in salida.columns     # el identificador NO sale al disco
    assert "display_name" not in salida.columns
    codigos = list(salida["seudonimo"])
    assert codigos == ["codigo-A", "codigo-A", "codigo-B", "codigo-A"]
    # Lo que Alberto pidió: las tres del mismo técnico agrupan, incluida la ya disociada.
    assert codigos.count("codigo-A") == 3


def test_el_export_nunca_deja_pasar_un_identificador_sin_codigo():
    """Ante la duda, no sale: una persona sin correspondencia se marca, no se filtra."""
    import pandas as pd

    from scripts.review_logs import _seudonimizar

    salida = _seudonimizar(
        pd.DataFrame([{"telegram_user_id": 999, "display_name": "Fulano", "query": "x"}]),
        {},
    )
    assert "telegram_user_id" not in salida.columns
    assert "display_name" not in salida.columns
    assert salida["seudonimo"].iloc[0] == "(sin código)"
