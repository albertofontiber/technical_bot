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

DSN = os.environ.get("RGPD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN,
    reason="requiere RGPD_TEST_DATABASE_URL (Postgres desechable); en CI lo da el workflow",
)

# Esquema mínimo con lo que la retención toca: mismas columnas, mismas constraints, mismas
# FK con CASCADE. No se copia el esquema entero — se copia lo que gobierna el invariante.
ESQUEMA = """
DROP TABLE IF EXISTS answer_messages, answer_feedback, feedback, query_logs, user_consent CASCADE;
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
        # La PROPUESTA, tal cual: si no ejecuta o alguna postcondición falla, esto revienta.
        cur.execute(PROPUESTA.read_text(encoding="utf-8"))

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

    conexion, vieja, nueva = base
    limite = job.corte(job.VENTANA_MESES, ahora=datetime.now(timezone.utc))
    resultado = job.ejecutar(limite, aplicar=False, conexion=conexion)

    assert resultado["query_logs"]["ids"] == [vieja]
    assert resultado["answer_messages"]["tocadas"] == 1
    assert all(f["tocadas"] >= 1 for f in resultado.values())

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
