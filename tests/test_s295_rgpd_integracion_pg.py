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

DSN = os.environ.get("RGPD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN,
    reason="requiere RGPD_TEST_DATABASE_URL (Postgres desechable); en CI lo da el workflow",
)

# Esquema mínimo con lo que la retención toca: mismas columnas, mismas constraints, mismas
# FK con CASCADE. No se copia el esquema entero — se copia lo que gobierna el invariante.
ESQUEMA = """
DROP TABLE IF EXISTS answer_messages, answer_feedback, feedback, query_logs, user_consent, persona_seudonimo, consent_events CASCADE;
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


def test_el_job_completo_contra_postgres_real(base, monkeypatch):
    """`ejecutar()` de punta a punta: asume el rol, comprueba `current_user`, recorre las 4
    tablas en una transacción y revierte. Con filas de verdad, no con una conexión falsa."""
    from datetime import datetime, timezone

    import scripts.rgpd_retencion as job
    from scripts.rgpd_retencion import OBJETIVOS

    conexion, vieja, nueva = base
    limite = job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc))
    resultado = job.ejecutar(limite, aplicar=False, conexion=conexion)

    assert resultado["query_logs"]["ids"] == [vieja]
    assert resultado["answer_messages"]["tocadas"] == 1
    # Las 4 tablas de datos sí tocan algo; `persona_seudonimo` NO debe tocar nada aquí,
    # porque a esa persona le queda una consulta reciente identificada y su código todavía
    # hace falta. Exigir >=1 a todas las entradas era exigir justo lo contrario.
    assert all(resultado[o.tabla]["tocadas"] >= 1 for o in OBJETIVOS)
    assert resultado["persona_seudonimo"]["tocadas"] == 0

    with conexion.cursor() as cur:            # dry-run ⇒ nada persistido
        cur.execute("SELECT telegram_user_id FROM query_logs WHERE id = %s", (vieja,))
        assert cur.fetchone()[0] == 111
    conexion.rollback()


def test_el_job_aborta_si_el_rol_no_se_asumio(base, monkeypatch):
    """`SET LOCAL ROLE` fuera de transacción es un NO-OP con warning. Si eso pasara, el job
    correría como operador (owner + BYPASSRLS) y la ventana no estaría garantizada por nada.
    Se simula neutralizando el SET y comprobando que aborta en vez de seguir."""
    from datetime import datetime, timezone

    import scripts.rgpd_retencion as job

    conexion, _, _ = base

    class _Envoltorio:
        def __init__(self, real):
            self._real = real

        def cursor(self):
            real_cur = self._real.cursor()

            class _C:
                def __enter__(_s): return _s
                def __exit__(_s, *e): return False
                def execute(_s, sql, params=None):
                    if sql.strip().upper().startswith("SET LOCAL ROLE"):
                        return                      # el NO-OP silencioso
                    real_cur.execute(sql, params)
                def fetchone(_s): return real_cur.fetchone()
                def fetchall(_s): return real_cur.fetchall()
            return _C()

        def commit(self): self._real.commit()
        def rollback(self): self._real.rollback()

    limite = job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc))
    with pytest.raises(RuntimeError, match="SET LOCAL ROLE no surtio efecto"):
        job.ejecutar(limite, aplicar=True, conexion=_Envoltorio(conexion))
    conexion.rollback()


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
    from datetime import datetime, timezone

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

    job.ejecutar(job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc)),
                 aplicar=True, conexion=conexion)

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
    from datetime import datetime, timezone

    import scripts.rgpd_retencion as job

    conexion, _, nueva = base
    job.ejecutar(job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc)),
                 aplicar=True, conexion=conexion)

    with conexion.cursor() as cur:
        # Le queda la consulta reciente ⇒ la correspondencia SIGUE viva.
        cur.execute("SELECT count(*) FROM persona_seudonimo WHERE telegram_user_id = 111")
        assert cur.fetchone()[0] == 1

        # Se retira lo último identificado y se vuelve a pasar: ahora sí se destruye.
        cur.execute("DELETE FROM query_logs WHERE id = %s", (nueva,))
    conexion.commit()

    job.ejecutar(job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc)),
                 aplicar=True, conexion=conexion)
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
    from datetime import datetime, timezone

    import scripts.rgpd_retencion as job

    conexion, vieja, _ = base
    with conexion.cursor() as cur:
        # Se simula exactamente ese caso: se le quita el código a alguien con filas vencidas.
        cur.execute("DELETE FROM persona_seudonimo WHERE telegram_user_id = 111")
    conexion.commit()

    resultado = job.ejecutar(job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc)),
                             aplicar=True, conexion=conexion)

    assert resultado["query_logs"]["tocadas"] >= 1, "se saltó a alguien sin código"
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
