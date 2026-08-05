"""s295 — la retención RGPD ejercida contra un PostgreSQL REAL.

Por qué existe este fichero: el resto de tests de s295 usan una conexión falsa, así que
prueban que se emiten las sentencias correctas — no que la base haga lo que decimos. Y lo
que decimos es fuerte: que las políticas RLS convierten la ventana de 24 meses en un
invariante del motor, que el rol no puede leer contenido, y que la retención no se puede
deshacer sola. Nada de eso se puede afirmar leyendo SQL (lección #60 de esta misma sesión:
verificar el EFECTO, no el código).

Aquí se levanta el esquema mínimo, se aplica la propuesta ENTERA tal cual está en el fichero
—si la propuesta no ejecuta, esto falla— y se comprueba el comportamiento con filas de
verdad: unas vencidas y otras recientes.

Se salta si no hay `RGPD_TEST_DATABASE_URL`. En CI lo provee un contenedor desechable
(`.github/workflows/s295-rgpd-retencion-pg.yml`), mismo patrón que el gate de pgvector.
NUNCA apuntar esta variable a producción: el fichero CREA y DESTRUYE objetos.
"""

import os
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
PROPUESTA = (
    REPO / "supabase" / "migration_proposals"
    / "20260803140000_s295_rgpd_rol_retencion_v2.sql"
)
PROPUESTA_S296 = (
    REPO / "supabase" / "migration_proposals"
    / "20260804120000_s296_seudonimo_y_calidad_v1.sql"
)
PROPUESTA_S297 = (
    REPO / "supabase" / "migration_proposals"
    / "20260805120000_s297_ledger_consentimiento_v1.sql"
)
PROPUESTA_S299 = (
    REPO / "supabase" / "migration_proposals"
    / "20260805150000_s299_job_programado_v1.sql"
)

DSN = os.environ.get("RGPD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN,
    reason="requiere RGPD_TEST_DATABASE_URL (Postgres desechable); en CI lo da el workflow",
)

# Esquema mínimo con lo que la retención toca: mismas columnas, mismas constraints, mismas
# FK con CASCADE. No se copia el esquema entero — se copia lo que gobierna el invariante.
ESQUEMA = """
DROP TABLE IF EXISTS answer_messages, answer_feedback, feedback, query_logs, user_consent, persona_seudonimo, consent_events, rgpd_recibos CASCADE;
DROP FUNCTION IF EXISTS public.rgpd_retencion_pasada(TEXT);
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    query TEXT NOT NULL,
    transcription TEXT,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_user_id BIGINT,
    feedback_text TEXT,
    -- Las copias que `log_feedback` escribe en prod: el GRANT de COLUMNA de s297 las
    -- referencia, así que el fixture debe tenerlas o la migración revienta aquí y no en
    -- producción (lo cazó el CI: el esquema mínimo se había quedado más mínimo que el real).
    previous_query TEXT,
    previous_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE answer_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    verdict TEXT NOT NULL,
    comment TEXT,
    reason_class TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (query_log_id, telegram_user_id)
);
CREATE TABLE answer_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT NOT NULL,
    telegram_message_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (telegram_chat_id, telegram_message_id)
);
-- `user_consent` no la toca la retención, pero SÍ la comprueba la postcondición que ancla
-- que `service_role` sigue exactamente como estaba (su UPDATE ahí es legítimo: la
-- re-aceptación). Sin ella el fixture estaría midiendo un mundo más pequeño que el real.
CREATE TABLE user_consent (
    telegram_user_id BIGINT PRIMARY KEY,
    display_name TEXT,
    terms_version TEXT NOT NULL,
    accepted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    END IF;
    -- Los roles anonimos de Supabase. El fixture NO los creaba, asi que el CI no podia
    -- cazar que una tabla nueva naciera accesible para ellos -- que es justo el riesgo de
    -- `persona_seudonimo`, la tabla que vincula codigo y persona.
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
END $$;
GRANT SELECT, INSERT ON query_logs, feedback, answer_messages TO service_role;
GRANT SELECT, INSERT, UPDATE ON answer_feedback, user_consent TO service_role;
"""


def _conectar():
    import psycopg2
    return psycopg2.connect(DSN, connect_timeout=15)


@pytest.fixture()
def base():
    """Esquema + propuesta aplicada + filas vencidas y recientes."""
    conexion = _conectar()
    conexion.autocommit = True
    with conexion.cursor() as cur:
        # ORDEN IMPORTANTE: primero las tablas (su DROP se lleva triggers y ACLs), y solo
        # despues el rol. Al reves, `DROP ROLE` falla con «objects depend on it» — que es
        # exactamente lo que le pasaria a alguien aplicando el rollback declarado en la
        # propuesta, y por eso alli tambien se usa `DROP OWNED BY`.
        cur.execute(ESQUEMA)
        cur.execute("""
            DO $limpieza$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rgpd_retencion') THEN
                    DROP OWNED BY rgpd_retencion;   -- privilegios y politicas que queden
                    DROP ROLE rgpd_retencion;
                END IF;
            END $limpieza$;
        """)
        # Se reproduce el comportamiento de Supabase: por defecto concede TODO sobre las
        # tablas nuevas de `public` a los roles anonimos. Sin esto, la tabla del vinculo
        # nace limpia en el test y el REVOKE de la migracion no probaria nada.
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT ALL ON TABLES TO anon, authenticated;")

        # Las PROPUESTAS, tal cual y EN ORDEN: si alguna no ejecuta o falla una
        # postcondición, esto revienta.
        cur.execute(PROPUESTA.read_text(encoding="utf-8"))
        cur.execute(PROPUESTA_S296.read_text(encoding="utf-8"))
        # Material para el BACKFILL de s297: una aceptación viva y una revocada, escritas
        # ANTES de aplicar la migración — así su reconstrucción tiene qué reconstruir.
        cur.execute(
            "INSERT INTO user_consent (telegram_user_id, terms_version, accepted_at) "
            "VALUES (111, 'v7', now() - interval '3 months')")
        cur.execute(
            "INSERT INTO user_consent (telegram_user_id, terms_version, accepted_at, revoked_at) "
            "VALUES (555, 'v6', now() - interval '8 months', now() - interval '2 months')")
        cur.execute(PROPUESTA_S297.read_text(encoding="utf-8"))
        # s299: la pasada única + recibos + reloj. En este contenedor pg_cron NO está
        # disponible ⇒ el bloque 3 corre su rama WARNING (gap declarado en la migración);
        # la FUNCIÓN — lo irreversible — se ejerce entera aquí abajo.
        cur.execute(PROPUESTA_S299.read_text(encoding="utf-8"))

        vieja = str(uuid.uuid4())
        nueva = str(uuid.uuid4())
        for qid, edad in ((vieja, "30 months"), (nueva, "1 month")):
            cur.execute(
                "INSERT INTO query_logs (id, telegram_user_id, query, created_at) "
                "VALUES (%s, 111, 'pregunta', now() - interval %s)", (qid, edad))
            cur.execute(
                "INSERT INTO answer_feedback "
                "(query_log_id, telegram_user_id, verdict, comment, created_at) "
                "VALUES (%s, 111, 'down', 'fallo X', now() - interval %s)", (qid, edad))
            cur.execute(
                "INSERT INTO answer_messages "
                "(query_log_id, telegram_chat_id, telegram_message_id, created_at) "
                "VALUES (%s, 111, %s, now() - interval %s)",
                (qid, abs(hash(qid)) % 100000, edad))
        cur.execute(
            "INSERT INTO feedback (telegram_user_id, feedback_text, created_at) "
            "VALUES (111, 'texto', now() - interval '30 months')")
    conexion.autocommit = False
    yield conexion, vieja, nueva
    conexion.close()


def _como_rol(conexion):
    cur = conexion.cursor()
    cur.execute("SET LOCAL ROLE rgpd_retencion;")
    return cur


# ------------------------------------------------------------------ el invariante


def test_la_propuesta_aplica_y_sus_postcondiciones_pasan(base):
    """El fixture ya ejecutó la propuesta entera. Que llegue aquí ES el test: sus ~8
    postcondiciones (RLS forzada, privilegios exactos, políticas con su predicado, fechas
    NOT NULL, trigger armado) se han evaluado contra un motor de verdad."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname='rgpd_retencion'")
        bypassrls, canlogin = cur.fetchone()
    assert bypassrls is False and canlogin is False


def test_el_rol_no_ve_las_filas_recientes(base):
    """El corazón del diseño: la ventana como invariante del motor. No es que el script
    filtre bien — es que la base no le enseña las filas nuevas."""
    conexion, vieja, nueva = base
    cur = _como_rol(conexion)
    cur.execute("SELECT id FROM query_logs")
    visibles = {str(f[0]) for f in cur.fetchall()}
    conexion.rollback()
    assert vieja in visibles
    assert nueva not in visibles


def test_el_rol_no_puede_tocar_una_fila_reciente_ni_forzandolo(base):
    """Se le pide explícitamente que dispare contra la fila nueva. La RLS lo deja en 0."""
    conexion, _, nueva = base
    cur = _como_rol(conexion)
    cur.execute("UPDATE query_logs SET telegram_user_id = NULL WHERE id = %s", (nueva,))
    tocadas = cur.rowcount
    conexion.rollback()
    assert tocadas == 0

    with conexion.cursor() as verif:          # y sigue identificada
        verif.execute("SELECT telegram_user_id FROM query_logs WHERE id = %s", (nueva,))
        assert verif.fetchone()[0] == 111
    conexion.rollback()


def test_el_rol_si_disocia_las_vencidas(base):
    conexion, vieja, _ = base
    cur = _como_rol(conexion)
    cur.execute("UPDATE query_logs SET telegram_user_id = NULL "
                "WHERE created_at < now() - interval '24 months' "
                "AND telegram_user_id IS NOT NULL RETURNING id")
    assert [str(f[0]) for f in cur.fetchall()] == [vieja]
    conexion.rollback()


def test_el_rol_no_puede_leer_el_contenido(base):
    """Un job de cumplimiento no tiene por qué ver la pregunta ni el comentario."""
    import psycopg2
    conexion, _, _ = base
    for sentencia in ("SELECT query FROM query_logs",
                      "SELECT comment FROM answer_feedback"):
        cur = _como_rol(conexion)
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(sentencia)
        conexion.rollback()


def test_el_rol_no_puede_insertar_ni_borrar_donde_no_debe(base):
    import psycopg2
    conexion, vieja, _ = base
    cur = _como_rol(conexion)
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("DELETE FROM query_logs WHERE id = %s", (vieja,))
    conexion.rollback()

    cur = _como_rol(conexion)
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("INSERT INTO feedback (telegram_user_id) VALUES (9)")
    conexion.rollback()


def test_el_rol_si_borra_las_anclas_vencidas(base):
    conexion, _, nueva = base
    cur = _como_rol(conexion)
    cur.execute("DELETE FROM answer_messages RETURNING id")
    borradas = cur.rowcount
    conexion.rollback()
    assert borradas == 1                      # la vencida; la reciente ni se ve


# ------------------------------------------------------------------ no deshacerse sola


def test_la_retencion_no_se_puede_deshacer_con_un_teclado_antiguo(base):
    """Tras disociar, la fila de `query_logs` SIGUE existiendo, así que un botón 👍/👎 de
    hace dos años todavía lleva su `query_log_id`. Sin el trigger, ese voto insertaría un
    `telegram_user_id` y re-identificaría la consulta otros 24 meses."""
    import psycopg2
    conexion, vieja, _ = base
    with conexion.cursor() as cur:            # como operador: disocia y CONFIRMA
        cur.execute("UPDATE query_logs SET telegram_user_id = NULL WHERE id = %s", (vieja,))
    conexion.commit()

    with conexion.cursor() as cur:
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute(
                "INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict) "
                "VALUES (%s, 222, 'up')", (vieja,))
    conexion.rollback()


def test_el_voto_sigue_funcionando_en_una_consulta_no_disociada(base):
    """El trigger no puede romper el caso normal."""
    conexion, _, nueva = base
    with conexion.cursor() as cur:
        cur.execute(
            "INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict) "
            "VALUES (%s, 222, 'up') RETURNING id", (nueva,))
        assert cur.fetchone()[0] is not None
    conexion.rollback()


# ------------------------------------------------------------------ el job de verdad


def test_el_job_completo_contra_postgres_real(base):
    """`ejecutar()` de punta a punta: el driver llama a la ÚNICA implementación
    (`rgpd_retencion_pasada`, la misma que ejecuta pg_cron), que asume el rol en su
    encabezado, recorre el ciclo en una transacción — y sin `--aplicar` se revierte TODO,
    el recibo en base incluido. Con filas de verdad, no con una conexión falsa."""
    import scripts.rgpd_retencion as job

    conexion, vieja, nueva = base
    recibo = job.ejecutar(aplicar=False, conexion=conexion)

    tablas = recibo["tablas"]
    assert tablas["query_logs"]["ids"] == [vieja]
    assert tablas["answer_messages"]["tocadas"] == 1
    # Las 4 tablas de datos sí tocan algo; `persona_seudonimo` NO debe tocar nada aquí,
    # porque a esa persona le queda una consulta reciente identificada y su código todavía
    # hace falta. Exigir >=1 a todas las entradas era exigir justo lo contrario.
    assert all(tablas[t]["tocadas"] >= 1 for t in
               ("query_logs", "feedback", "answer_feedback", "answer_messages"))
    assert tablas["persona_seudonimo"]["tocadas"] == 0

    with conexion.cursor() as cur:            # dry-run ⇒ nada persistido
        cur.execute("SELECT telegram_user_id FROM query_logs WHERE id = %s", (vieja,))
        assert cur.fetchone()[0] == 111
        cur.execute("SELECT count(*) FROM rgpd_recibos")
        assert cur.fetchone()[0] == 0          # el recibo se revierte con la pasada
    conexion.rollback()


def test_la_pasada_aborta_si_pierde_el_set_role(base):
    """El cinturón del tirante, ejercido de verdad: se le quita a la función el `SET role`
    del encabezado (lo que haría una edición descuidada) y la pasada tiene que ABORTAR —
    sin el rol asumido correría como el operador (owner + BYPASSRLS) y la ventana de 24
    meses no la garantizaría NADA. El fallo más grave posible aquí, y silencioso."""
    import psycopg2

    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("ALTER FUNCTION public.rgpd_retencion_pasada(TEXT) RESET role;")
        with pytest.raises(psycopg2.errors.RaiseException,
                           match="debe correr como rgpd_retencion"):
            cur.execute("SELECT public.rgpd_retencion_pasada('manual');")
    conexion.rollback()                        # revierte también el RESET: queda armado


# ------------------------------------------------------------------ el rollback declarado


def test_el_rollback_de_la_propuesta_funciona(base):
    """La propuesta declara su rollback; declararlo sin probarlo es media promesa. En
    particular: `REVOKE ALL ON TABLE` debe llevarse también los ACL de COLUMNA, o el
    `DROP ROLE` fallaría por dependencias."""
    conexion, _, _ = base
    conexion.autocommit = True
    with conexion.cursor() as cur:
        for tabla in ("query_logs", "feedback", "answer_feedback", "answer_messages"):
            cur.execute(f"DROP POLICY IF EXISTS rgpd_retencion_ventana ON public.{tabla};")
        cur.execute("DROP TRIGGER IF EXISTS rgpd_no_reidentificar ON public.answer_feedback;")
        # `DROP OWNED BY` es lo que retira TODOS los privilegios que le quedan, incluidos los
        # de COLUMNA y el USAGE del esquema. Con solo REVOKE, el `DROP ROLE` falla con
        # «objects depend on it» — verificado, no supuesto.
        cur.execute("DROP OWNED BY rgpd_retencion;")
        cur.execute("REVOKE rgpd_retencion FROM postgres;")
        cur.execute("DROP ROLE rgpd_retencion;")
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='rgpd_retencion'")
        assert cur.fetchone() is None
    conexion.autocommit = False


# ------------------------------------------------------------------ s296: el seudónimo


def test_el_corpus_sigue_agrupado_tras_la_retencion(base):
    """LO QUE ALBERTO PIDIÓ, comprobado de punta a punta: que al vencer el plazo no se
    pierdan las preguntas de un buen técnico *como conjunto*.

    Con NULL quedarían sueltas — sabrías qué se preguntó, no que lo preguntó la misma
    persona. Con el seudónimo, el corpus sobrevive agrupado y el vínculo con la persona
    desaparece. Este test es el que distingue una cosa de la otra."""
    import scripts.rgpd_retencion as job

    conexion, vieja, nueva = base
    with conexion.cursor() as cur:
        # Una SEGUNDA consulta vencida de la misma persona: la propiedad que importa es que
        # las dos acaben bajo el MISMO código. Con NULL acabarían indistinguibles de las de
        # cualquier otro.
        cur.execute(
            "INSERT INTO query_logs (telegram_user_id, query, created_at) "
            "VALUES (111, 'otra pregunta suya', now() - interval '30 months') RETURNING id")
        otra_vieja = str(cur.fetchone()[0])
    conexion.commit()

    job.ejecutar(aplicar=True, conexion=conexion)

    with conexion.cursor() as cur:
        cur.execute("SELECT telegram_user_id, seudonimo FROM query_logs WHERE id = ANY(%s::uuid[])",
                    ([vieja, otra_vieja],))
        filas = cur.fetchall()
        assert len(filas) == 2
        assert all(identificador is None for identificador, _ in filas)   # no se sabe QUIÉN
        codigos = {str(seudonimo) for _, seudonimo in filas}
        assert len(codigos) == 1 and None not in codigos   # ...pero sí que fue el MISMO

        # La reciente sigue intacta: la ventana la impone la base.
        cur.execute("SELECT telegram_user_id FROM query_logs WHERE id = %s", (nueva,))
        assert cur.fetchone()[0] == 111
    conexion.commit()


def test_el_vinculo_se_destruye_solo_cuando_no_queda_nada_identificado(base):
    """El borrado de la correspondencia es el punto de no retorno, así que no puede ir
    antes de tiempo: mientras a esa persona le queden filas recientes, su código todavía
    hace falta para estamparlas cuando les toque."""
    import scripts.rgpd_retencion as job

    conexion, _, nueva = base
    job.ejecutar(aplicar=True, conexion=conexion)

    with conexion.cursor() as cur:
        # Le queda la consulta reciente ⇒ la correspondencia SIGUE viva.
        cur.execute("SELECT count(*) FROM persona_seudonimo WHERE telegram_user_id = 111")
        assert cur.fetchone()[0] == 1

        # Se retira lo último identificado y se vuelve a pasar: ahora sí se destruye.
        cur.execute("DELETE FROM query_logs WHERE id = %s", (nueva,))
    conexion.commit()

    job.ejecutar(aplicar=True, conexion=conexion)
    with conexion.cursor() as cur:
        cur.execute("SELECT count(*) FROM persona_seudonimo WHERE telegram_user_id = 111")
        assert cur.fetchone()[0] == 0                     # irreversible a partir de aquí
    conexion.commit()


def test_el_bot_no_puede_escribir_la_marca_de_utilidad(base):
    """La marca es el dato en que se apoyaría un bonus, y el técnico habla precisamente por
    el canal del bot. Que `service_role` no pueda escribirla no es un detalle: es lo que
    impide que el interesado influya en su propia valoración."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT has_column_privilege('service_role', 'public.answer_feedback',"
                    " 'utilidad', 'UPDATE')")
        assert cur.fetchone()[0] is False
    conexion.rollback()


def test_el_voto_sigue_funcionando_como_service_role(base):
    """No basta mirar flags de privilegio: el fallo de esta clase solo aparece EJECUTANDO
    (precedente s294 — un `merge-duplicates` daba 403 real sobre una tabla que «tenía» los
    permisos). Aquí se ejerce el upsert 👍→👎 asumiendo el rol del bot."""
    conexion, _, nueva = base
    with conexion.cursor() as cur:
        cur.execute("SET LOCAL ROLE service_role;")
        cur.execute(
            "INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict) "
            "VALUES (%s, 777, 'up') "
            "ON CONFLICT (query_log_id, telegram_user_id) DO UPDATE "
            "SET verdict = EXCLUDED.verdict", (nueva,))
        cur.execute(
            "INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict) "
            "VALUES (%s, 777, 'down') "
            "ON CONFLICT (query_log_id, telegram_user_id) DO UPDATE "
            "SET verdict = EXCLUDED.verdict", (nueva,))
        cur.execute("SELECT verdict FROM answer_feedback "
                    " WHERE query_log_id = %s AND telegram_user_id = 777", (nueva,))
        assert cur.fetchone()[0] == "down"          # el toggle sigue vivo
    conexion.rollback()


def test_la_marca_se_puede_poner_en_feedback_de_una_consulta_YA_disociada(base):
    """El caso que el trigger bloqueaba: el feedback MÁS ANTIGUO —el que ha tenido tiempo de
    demostrar que sirvió— cuelga de consultas ya disociadas. Si marcar su utilidad saltara
    el trigger, sería imposible reconocer justo lo que se quiere reconocer."""
    conexion, vieja, _ = base
    with conexion.cursor() as cur:
        cur.execute("UPDATE query_logs SET telegram_user_id = NULL WHERE id = %s", (vieja,))
        cur.execute("UPDATE answer_feedback SET utilidad = 'corrigio', "
                    "utilidad_revisada_at = now() WHERE query_log_id = %s RETURNING id",
                    (vieja,))
        assert cur.fetchone() is not None
    conexion.rollback()


def test_el_bot_no_puede_cambiar_un_seudonimo(base):
    """Un código que cambia deja de agrupar — que es justo lo que se quiere conservar."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        for privilegio in ("UPDATE", "DELETE"):
            cur.execute("SELECT has_table_privilege('service_role',"
                        " 'public.persona_seudonimo', %s)", (privilegio,))
            assert cur.fetchone()[0] is False, f"service_role no debe tener {privilegio}"
    conexion.rollback()


def test_user_consent_conserva_la_aceptacion_de_cada_version(base):
    """Antes el upsert iba por persona y machacaba: no se podía demostrar que alguien
    aceptó la v3 en su día. Ahora convive una fila por versión, cada una con su fecha."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        for version in ("v6", "v7"):
            cur.execute(
                "INSERT INTO user_consent (telegram_user_id, terms_version, accepted_at) "
                "VALUES (111, %s, now()) "
                "ON CONFLICT (telegram_user_id, terms_version) DO UPDATE "
                "SET accepted_at = EXCLUDED.accepted_at", (version,))
        cur.execute("SELECT count(*) FROM user_consent WHERE telegram_user_id = 111")
        assert cur.fetchone()[0] == 2          # la v6 sobrevive a la aceptación de la v7
    conexion.rollback()


def test_el_feedback_ya_cascadea(base):
    """La tabla guardaba copias sueltas del texto y un borrado no la alcanzaba."""
    conexion, vieja, _ = base
    with conexion.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (telegram_user_id, feedback_text, query_log_id) "
            "VALUES (111, 'esto está mal', %s)", (vieja,))
        cur.execute("DELETE FROM query_logs WHERE id = %s", (vieja,))
        cur.execute("SELECT count(*) FROM feedback WHERE query_log_id = %s", (vieja,))
        assert cur.fetchone()[0] == 0          # se fue con su consulta
    conexion.rollback()


def test_nadie_se_queda_fuera_de_la_retencion_por_no_tener_codigo(base):
    """El fallo que destapó el CI: la emisión del código en `/accept` es fail-open, así que
    puede haber gente sin código. Sin código, el `UPDATE ... FROM persona_seudonimo` no
    casaría sus filas — conservarían el identificador PARA SIEMPRE y el recibo diría
    «0 tocadas» sin que nada chirriara. El job tiene que emitir el que falte."""
    import scripts.rgpd_retencion as job

    conexion, vieja, _ = base
    with conexion.cursor() as cur:
        # Se simula exactamente ese caso: se le quita el código a alguien con filas vencidas.
        cur.execute("DELETE FROM persona_seudonimo WHERE telegram_user_id = 111")
    conexion.commit()

    recibo = job.ejecutar(aplicar=True, conexion=conexion)

    assert recibo["tablas"]["query_logs"]["tocadas"] >= 1, "se saltó a alguien sin código"
    with conexion.cursor() as cur:
        cur.execute("SELECT telegram_user_id, seudonimo FROM query_logs WHERE id = %s",
                    (vieja,))
        identificador, seudonimo = cur.fetchone()
        assert identificador is None            # disociada de verdad
        assert seudonimo is not None            # y agrupada bajo un código recién emitido
    conexion.commit()


def test_la_tabla_del_vinculo_no_nace_accesible_para_roles_anonimos(base):
    """`persona_seudonimo` vincula código y persona: es la pieza más sensible del diseño.
    Supabase concede TODO por defecto sobre las tablas nuevas de `public` a `anon` y
    `authenticated`, así que una tabla creada sin REVOKE explícito nace expuesta. La RLS lo
    taparía, pero el patrón del repo es REVOKE **y** RLS — y aquí el fixture reproduce la
    concesión por defecto, así que este test falla de verdad si el REVOKE desaparece."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        for rol in ("anon", "authenticated"):
            for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                cur.execute("SELECT has_table_privilege(%s, 'public.persona_seudonimo', %s)",
                            (rol, privilegio))
                assert cur.fetchone()[0] is False, f"{rol} tiene {privilegio}"
    conexion.rollback()


# ------------------------------------------------------------------ s297: el libro


def test_el_backfill_reconstruye_lo_que_sobrevivio(base):
    """El upsert antiguo destruyó el histórico: el libro arranca con lo único que quedó —
    el estado actual — sin fingir más. Una aceptación viva ⇒ un evento; una revocada ⇒ dos
    (accepted + revoked), cada uno con su fecha real."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT evento FROM consent_events WHERE telegram_user_id = 111")
        assert [f[0] for f in cur.fetchall()] == ["accepted"]
        cur.execute("SELECT evento FROM consent_events WHERE telegram_user_id = 555 "
                    "ORDER BY created_at")
        assert [f[0] for f in cur.fetchall()] == ["accepted", "revoked"]
    conexion.rollback()


def test_el_libro_es_de_solo_insercion_para_el_bot(base):
    """La evidencia editable no es evidencia. Se EJECUTA como service_role (no se miran
    flags: esa clase de fallo solo aparece ejecutando — precedente s294)."""
    import psycopg2
    conexion, _, _ = base

    with conexion.cursor() as cur:                     # INSERT sí: es su función
        cur.execute("SET LOCAL ROLE service_role;")
        cur.execute("INSERT INTO consent_events (telegram_user_id, terms_version, evento) "
                    "VALUES (111, 'v7', 'accepted')")
    conexion.rollback()

    for sentencia in (
        "UPDATE consent_events SET evento = 'revoked' WHERE telegram_user_id = 111",
        "DELETE FROM consent_events WHERE telegram_user_id = 111",
    ):
        with conexion.cursor() as cur:
            cur.execute("SET LOCAL ROLE service_role;")
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(sentencia)
        conexion.rollback()


def test_reaceptar_no_pisa_la_evidencia(base):
    """El defecto que motivó el libro: re-aceptar la misma versión refresca el ESTADO
    (correcto) pero antes destruía la traza. Ahora cada aceptación es un evento nuevo."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SET LOCAL ROLE service_role;")
        for _ in range(2):                             # el técnico re-acepta la v7
            cur.execute("INSERT INTO consent_events (telegram_user_id, terms_version, evento) "
                        "VALUES (111, 'v7', 'accepted')")
        cur.execute("SELECT count(*) FROM consent_events "
                    " WHERE telegram_user_id = 111 AND evento = 'accepted'")
        assert cur.fetchone()[0] == 3                  # backfill + 2 re-aceptaciones
    conexion.rollback()


def test_los_roles_anonimos_no_ven_el_libro(base):
    conexion, _, _ = base
    with conexion.cursor() as cur:
        for rol in ("anon", "authenticated"):
            for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                cur.execute("SELECT has_table_privilege(%s, 'public.consent_events', %s)",
                            (rol, privilegio))
                assert cur.fetchone()[0] is False, f"{rol} tiene {privilegio}"
    conexion.rollback()


def test_la_marca_del_canal_espontaneo_existe_y_el_bot_no_puede_escribirla(base):
    """El canal espontáneo (`feedback`) es por donde llega parte del feedback más valioso
    y no tenía dónde marcarse. Y la marca —el dato que sostendría un bonus— tiene que ser
    inalcanzable desde el canal por el que habla el interesado, también aquí."""
    import psycopg2
    conexion, _, _ = base
    with conexion.cursor() as cur:
        # El operador (postgres) SÍ puede marcar.
        cur.execute("UPDATE feedback SET utilidad = 'corpus', utilidad_revisada_at = now() "
                    " WHERE telegram_user_id = 111 RETURNING id")
        assert cur.fetchone() is not None
        # Un valor fuera de la taxonomía revienta.
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute("UPDATE feedback SET utilidad = 'genial' WHERE telegram_user_id = 111")
    conexion.rollback()

    with conexion.cursor() as cur:                     # el bot, ejecutando de verdad: no
        cur.execute("SET LOCAL ROLE service_role;")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("UPDATE feedback SET utilidad = 'corrigio' WHERE telegram_user_id = 111")
    conexion.rollback()


def test_la_migracion_s297_se_puede_reejecutar_sin_corromper_el_libro(base):
    """S1 del dúo, el crítico: sin guarda, re-ejecutar la migración (operador inseguro de
    «¿la apliqué?») re-insertaba el backfill entero — COMMIT limpio, libro afirmando dos
    aceptaciones donde hubo una, y la postcondición de >= tragándoselo. Aquí se re-ejecuta
    DE VERDAD y se exige que el libro quede idéntico."""
    conexion, _, _ = base
    conexion.autocommit = True
    with conexion.cursor() as cur:
        cur.execute("SELECT count(*) FROM consent_events")
        antes = cur.fetchone()[0]
        cur.execute(PROPUESTA_S297.read_text(encoding="utf-8"))     # segunda pasada
        cur.execute("SELECT count(*) FROM consent_events")
        despues = cur.fetchone()[0]
    conexion.autocommit = False
    assert despues == antes, "la re-ejecución duplicó evidencia"


def test_los_eventos_reconstruidos_se_distinguen_de_los_presenciados(base):
    """Un evento del backfill no es un evento presenciado: el libro lo dice (`origen`),
    para no fingir un histórico que el upsert antiguo destruyó."""
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT DISTINCT origen FROM consent_events")
        assert {f[0] for f in cur.fetchall()} == {"backfill"}       # solo backfill aún
        cur.execute("SET LOCAL ROLE service_role;")
        cur.execute("INSERT INTO consent_events (telegram_user_id, terms_version, evento) "
                    "VALUES (111, 'v7', 'accepted')")
        cur.execute("SELECT origen FROM consent_events "
                    " WHERE telegram_user_id = 111 ORDER BY created_at DESC LIMIT 1")
        assert cur.fetchone()[0] == "runtime"                       # el default distingue
    conexion.rollback()


def test_el_bot_no_puede_INSERTAR_la_marca(base):
    """C1 del cross-model: el UPDATE estaba cerrado pero el INSERT de tabla cubría toda
    columna — el bot podía insertar una fila nueva con `utilidad` ya puesta. Se ejerce de
    verdad como service_role, en las DOS tablas."""
    import psycopg2
    conexion, vieja, _ = base

    with conexion.cursor() as cur:                     # la escritura NORMAL sigue viva
        cur.execute("SET LOCAL ROLE service_role;")
        cur.execute("INSERT INTO feedback (telegram_user_id, feedback_text) "
                    "VALUES (222, 'feedback normal')")
    conexion.rollback()

    for sentencia in (
        "INSERT INTO feedback (telegram_user_id, feedback_text, utilidad, "
        " utilidad_revisada_at) VALUES (222, 'tramposo', 'corrigio', now())",
        f"INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict, utilidad, "
        f" utilidad_revisada_at) VALUES ('{vieja}', 999, 'up', 'gold', now())",
    ):
        with conexion.cursor() as cur:
            cur.execute("SET LOCAL ROLE service_role;")
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(sentencia)
        conexion.rollback()


def test_la_marca_exige_fecha_de_revision_y_viceversa(base):
    """M6 del cross-model: NULL≠ninguna no estaba gobernado — cabía una marca sin fecha o
    una fecha sin marca, y la semántica «auditable» quedaba contradictoria."""
    import psycopg2
    conexion, vieja, _ = base
    for sentencia in (
        "UPDATE feedback SET utilidad = 'corpus' WHERE telegram_user_id = 111",   # sin fecha
        "UPDATE feedback SET utilidad_revisada_at = now() WHERE telegram_user_id = 111",
    ):
        with conexion.cursor() as cur:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(sentencia)
        conexion.rollback()


# ------------------------------------------------------------------ s299: la pasada


def test_la_pasada_confirmada_deja_recibo_en_la_base(base):
    """Una ejecución programada no tiene a nadie mirando stdout: la evidencia es la fila
    de `rgpd_recibos`, escrita por la MISMA transacción de la pasada. Y la pasada corre
    COMO el rol — si el `SET role` del encabezado no surtiera efecto, su primera
    comprobación habría abortado y este test no vería recibo."""
    conexion, vieja, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT public.rgpd_retencion_pasada('cron');")
        recibo = cur.fetchone()[0]
    conexion.commit()

    assert recibo["tablas"]["query_logs"]["ids"] == [vieja]
    with conexion.cursor() as cur:
        cur.execute("SELECT origen, corte, resultado FROM rgpd_recibos")
        filas = cur.fetchall()
        assert len(filas) == 1
        origen, corte, resultado = filas[0]
        assert origen == "cron"
        assert corte is not None
        assert resultado["query_logs"]["tocadas"] == 1
    conexion.commit()


def test_el_bot_no_puede_ejecutar_la_pasada(base):
    """Dos capas: sin EXECUTE no se entra (esta), y sin membresía SET en el rol el
    `SET role` de la entrada fallaría igualmente. Se ejerce, no se mira el flag."""
    import psycopg2
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SET LOCAL ROLE service_role;")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT public.rgpd_retencion_pasada('cron');")
    conexion.rollback()


def test_los_recibos_no_se_pueden_editar_ni_ver_desde_los_roles_acotados(base):
    """Un recibo editable no es un recibo: el rol de retención SOLO inserta (lo hace la
    pasada por él), y el bot ni los ve. La lectura es del operador."""
    import psycopg2
    conexion, _, _ = base
    with conexion.cursor() as cur:
        cur.execute("SELECT public.rgpd_retencion_pasada('manual');")
    conexion.commit()

    for rol, sentencia in (
        ("rgpd_retencion", "UPDATE rgpd_recibos SET origen = 'cron'"),
        ("rgpd_retencion", "DELETE FROM rgpd_recibos"),
        ("rgpd_retencion", "SELECT resultado FROM rgpd_recibos"),
        ("service_role", "SELECT resultado FROM rgpd_recibos"),
        ("service_role", "INSERT INTO rgpd_recibos (origen, corte, resultado) "
                         "VALUES ('manual', now(), '{}'::jsonb)"),
    ):
        with conexion.cursor() as cur:
            cur.execute(f"SET LOCAL ROLE {rol};")
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(sentencia)
        conexion.rollback()


def test_el_recibo_del_vinculo_destruido_no_registra_a_la_persona(base):
    """El punto de no retorno queda CONTADO, no identificado: `tocadas` sí, ids NO — en
    esa tabla el id ES la persona, y un recibo que lo registrara conservaría el vínculo
    que la pasada acaba de destruir."""
    conexion, _, nueva = base
    with conexion.cursor() as cur:             # sin filas recientes, el vínculo cae hoy
        cur.execute("DELETE FROM query_logs WHERE id = %s", (nueva,))
    conexion.commit()
    with conexion.cursor() as cur:
        cur.execute("SELECT public.rgpd_retencion_pasada('cron');")
    conexion.commit()

    with conexion.cursor() as cur:
        cur.execute("SELECT resultado -> 'persona_seudonimo' FROM rgpd_recibos")
        entrada = cur.fetchone()[0]
        assert entrada["tocadas"] == 1
        assert entrada["ids"] == []
        cur.execute("SELECT count(*) FROM persona_seudonimo")
        assert cur.fetchone()[0] == 0          # irreversible, y contado sin identificar
    conexion.commit()


# ------------------------------------------------------- s298: bootstrap re-ejecutable


def _bloque_frontera() -> str:
    """El bloque del bootstrap entre los marcadores RGPD-BOUNDARY. Extraído por marcadores
    EXPLÍCITOS (no por heurística) para que mover el bloque no rompa el test en silencio."""
    bootstrap = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    # Unicidad ANTES de extraer: un marcador duplicado (p.ej. citado en un comentario)
    # haria que .index() cogiera el primero y se extrajera un span equivocado en silencio.
    assert bootstrap.count(">>> RGPD-BOUNDARY-BEGIN <<<") == 1
    assert bootstrap.count(">>> RGPD-BOUNDARY-END <<<") == 1
    ini = bootstrap.index(">>> RGPD-BOUNDARY-BEGIN <<<")
    fin = bootstrap.index("-- >>> RGPD-BOUNDARY-END <<<")
    return bootstrap[bootstrap.index("\n", ini) + 1 : fin]


def test_reejecutar_el_bootstrap_no_deshace_las_garantias(base):
    """LA CLASE s296, cerrada con mecanismo y no con procedimiento: la versión anterior del
    bloque frontera re-concedía a service_role el INSERT/UPDATE de TABLA — re-correr el
    bootstrap deshacía la protección de la marca EN SILENCIO. Aquí se ejecuta el bloque
    REAL del fichero, tras la cola completa, y se exige que todo sobreviva."""
    import psycopg2
    conexion, _, nueva = base
    conexion.autocommit = True
    with conexion.cursor() as cur:
        cur.execute(_bloque_frontera())        # sus postcondiciones internas ya verifican
    conexion.autocommit = False

    # Y además se EJERCE, no solo se consulta el catálogo:
    with conexion.cursor() as cur:             # la marca sigue fuera del alcance del bot
        cur.execute("SET LOCAL ROLE service_role;")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("UPDATE answer_feedback SET utilidad = 'gold', "
                        "utilidad_revisada_at = now() WHERE query_log_id = %s", (nueva,))
    conexion.rollback()

    with conexion.cursor() as cur:             # el voto sigue funcionando
        cur.execute("SET LOCAL ROLE service_role;")
        cur.execute("INSERT INTO answer_feedback (query_log_id, telegram_user_id, verdict) "
                    "VALUES (%s, 888, 'up') "
                    "ON CONFLICT (query_log_id, telegram_user_id) DO UPDATE "
                    "SET verdict = EXCLUDED.verdict", (nueva,))
        # ...y el motivo y el comentario del 👎 (los PATCH de reason/comment), y el
        # feedback espontáneo con su enlace — TODOS los write-paths del bot, no solo el
        # voto (dúo s298: una column-list recortada pasaba el catálogo con CI verde).
        cur.execute("UPDATE answer_feedback SET reason_class = 'wrong', comment = 'mal' "
                    " WHERE query_log_id = %s AND telegram_user_id = 888", (nueva,))
        cur.execute("INSERT INTO feedback (telegram_user_id, feedback_text, query_log_id) "
                    "VALUES (888, 'feedback tras re-bootstrap', %s)", (nueva,))
        cur.execute("INSERT INTO user_consent (telegram_user_id, terms_version) "
                    "VALUES (888, 'v7') "
                    "ON CONFLICT (telegram_user_id, terms_version) DO UPDATE "
                    "SET accepted_at = now()")
    conexion.rollback()

    with conexion.cursor() as cur:             # y el libro sigue siendo de solo inserción
        cur.execute("SET LOCAL ROLE service_role;")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM consent_events")
    conexion.rollback()

    with conexion.cursor() as cur:             # s299: la pasada sigue siendo del operador
        cur.execute("SELECT public.rgpd_retencion_pasada('manual');")
    conexion.rollback()

    with conexion.cursor() as cur:             # ...y los recibos, invisibles para el bot
        cur.execute("SET LOCAL ROLE service_role;")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT resultado FROM rgpd_recibos")
    conexion.rollback()


def test_el_bloque_frontera_tiene_sus_marcadores():
    """Si alguien borra o renombra los marcadores, la extracción falla AQUÍ con un mensaje
    claro, no en el test de arriba con un index error críptico."""
    bootstrap = (REPO / "supabase_schema.sql").read_text(encoding="utf-8")
    assert ">>> RGPD-BOUNDARY-BEGIN <<<" in bootstrap
    assert ">>> RGPD-BOUNDARY-END <<<" in bootstrap
