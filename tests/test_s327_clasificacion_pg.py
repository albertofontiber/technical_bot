# -*- coding: utf-8 -*-
"""s327 — la cola 021→024 contra un Postgres REAL (cierra TECH_DEBT #91).

Por qué existe: los tests de estas migraciones fijaban su TEXTO con regex, no su
EFECTO. La deuda #91 se abrió anoche declarando el gap y poniendo un trigger —
«la próxima migración que toque `query_clasificacion` o sus vistas»— y la 023 lo
disparó el mismo día. Declarar un gap y luego pisar su trigger sin resolverlo es
justo lo que el registro de deuda existe para impedir (lo cazó el dúo, s327).

Qué afirma, y por qué cada cosa:
  · el TRINQUETE de la ACL: `service_role` escribe las columnas concedidas y NO
    puede tocar la PK — ese permiso exacto ya mordió una vez (el upsert de
    PostgREST murió con 42501 en el backfill de s326), así que se prueba que la
    base lo impide de verdad, no que la migración lo diga;
  · el CASCADE: borrar la consulta se lleva su clasificación — es la mitad
    silenciosa del procedimiento de supresión RGPD;
  · el CHECK vigente == los ids del YAML, leídos de `pg_constraint` (no del
    fichero): es el contrato YAML↔SQL comprobado contra la base;
  · las vistas de análisis EXCLUYEN las no-preguntas, incluidos los VOTOS (el
    defecto que la 024 arregla), con control negativo: si se quitara el filtro,
    los números cambiarían.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.clasificacion import cargar_taxonomia
from tests.test_s295_rgpd_integracion_pg import base  # noqa: F401

REPO = Path(__file__).parent.parent
MIGRACIONES = [REPO / "migrations" / n for n in (
    "021_query_clasificacion.sql",
    "022_taxonomia_v2.sql",
    "023_es_pregunta.sql",
    "024_votos_solo_de_preguntas.sql",
)]

DSN = os.environ.get("RGPD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN,
    reason="requiere RGPD_TEST_DATABASE_URL (Postgres desechable); en CI lo da el workflow",
)


@pytest.fixture()
def clasificacion(base):  # noqa: F811
    """El arnés s295 + lo que la cola 021→024 necesita y aquel no traía."""
    conexion, _, _ = base
    conexion.autocommit = True
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS query_clasificacion CASCADE;")
        cur.execute("DROP TABLE IF EXISTS documents CASCADE;")
        cur.execute("DROP TABLE IF EXISTS bot_allowlist, bot_invitaciones CASCADE;")
        # Columnas de `query_logs` que el fixture mínimo no trae y las vistas sí
        # usan. Se añaden aquí y no se tocan las migraciones: el arnés se parece
        # a producción, no al revés.
        for columna, tipo in (("source", "TEXT DEFAULT 'text'"),
                              ("route", "TEXT"),
                              ("product_models", "TEXT[]"),
                              ("response_length", "INTEGER DEFAULT 0")):
            cur.execute(f"ALTER TABLE query_logs ADD COLUMN IF NOT EXISTS "
                        f"{columna} {tipo};")
        cur.execute("CREATE TABLE documents (id UUID PRIMARY KEY DEFAULT "
                    "gen_random_uuid(), manufacturer TEXT NOT NULL, "
                    "status TEXT DEFAULT 'active');")
        cur.execute((REPO / "migrations" / "016_allowlist_invitaciones.sql")
                    .read_text("utf-8"))
        for migracion in MIGRACIONES:
            cur.execute(migracion.read_text("utf-8"))
        # El arnés `base` siembra sus propias filas (las vencidas y recientes
        # que miden los tests de retención). Aquí estorban: estas aserciones
        # cuentan filas, así que la siembra tiene que ser la NUESTRA y nada más.
        # Lo cazó el propio gate al correr por primera vez (contaba 3 donde
        # esperaba 1) — que es exactamente para lo que sirve correrlo.
        cur.execute("DELETE FROM query_logs;")
    conexion.autocommit = False
    yield conexion
    conexion.close()


def _sembrar(cur, *, es_pregunta: bool, verdict: str | None = None,
             categoria: str = "catalogo_especificaciones",
             marcas: str = "{Detnov}") -> str:
    cur.execute("INSERT INTO query_logs (telegram_user_id, query, source) "
                "VALUES (7, 'da igual', 'text') RETURNING id;")
    qid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO query_clasificacion (query_log_id, categoria, es_pregunta,"
        " taxonomia_version, marcas, modelos, marcas_libres, origen) "
        "VALUES (%s, %s, %s, 1, %s::text[], '{}'::text[], '{hochiki}'::text[],"
        " 'regla');", (qid, categoria, es_pregunta, marcas))
    if verdict:
        cur.execute("INSERT INTO answer_feedback (query_log_id, "
                    "telegram_user_id, verdict) VALUES (%s, 7, %s);",
                    (qid, verdict))
    return qid


# ------------------------------------------------------------------- la ACL


def test_service_role_escribe_lo_concedido_y_nada_mas(clasificacion):
    """El trinquete que ya mordió: la PK NO se re-escribe. Si alguien concede
    `UPDATE (query_log_id)` para «arreglar» un upsert, esto se pone rojo."""
    with clasificacion.cursor() as cur:
        for columna in ("categoria", "es_pregunta", "taxonomia_version",
                        "marcas", "modelos", "marcas_libres", "origen",
                        "modelo_llm", "clasificado_at"):
            cur.execute("SELECT has_column_privilege('service_role', "
                        "'public.query_clasificacion', %s, 'INSERT');", (columna,))
            assert cur.fetchone()[0] is True, columna
        cur.execute("SELECT has_column_privilege('service_role', "
                    "'public.query_clasificacion', 'query_log_id', 'UPDATE');")
        assert cur.fetchone()[0] is False, (
            "service_role puede UPDATE de la PK: el upsert de PostgREST "
            "volvería a ser posible y una clasificación podría mudarse de "
            "pregunta")


def test_anon_y_authenticated_no_ven_ni_la_tabla_ni_las_vistas(clasificacion):
    vistas = ("query_clasificacion", "bot_tipologia_semanal",
              "bot_marcas_semanal", "bot_modelos_semanal",
              "bot_feedback_tipologia_semanal",
              "bot_preguntas_por_usuario_semanal",
              "bot_marcas_sin_corpus_semanal", "bot_clasificacion_cobertura",
              "bot_explorador_v1", "bot_no_preguntas_v1")
    with clasificacion.cursor() as cur:
        for rol in ("anon", "authenticated"):
            for objeto in vistas:
                cur.execute("SELECT has_table_privilege(%s, %s, 'SELECT');",
                            (rol, f"public.{objeto}"))
                assert cur.fetchone()[0] is False, f"{rol} lee {objeto}"


def test_rls_enable_y_force(clasificacion):
    with clasificacion.cursor() as cur:
        cur.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'public.query_clasificacion'::regclass;")
        assert cur.fetchone() == (True, True)


# ------------------------------------------------------------------ el dato


def test_la_supresion_rgpd_se_lleva_la_clasificacion(clasificacion):
    """CASCADE: `DELETE FROM query_logs WHERE telegram_user_id = X` —el
    procedimiento documentado— tiene que alcanzar esta tabla sin pasos extra."""
    with clasificacion.cursor() as cur:
        _sembrar(cur, es_pregunta=True)
        cur.execute("SELECT count(*) FROM query_clasificacion;")
        assert cur.fetchone()[0] == 1
        cur.execute("DELETE FROM query_logs WHERE telegram_user_id = 7;")
        cur.execute("SELECT count(*) FROM query_clasificacion;")
        assert cur.fetchone()[0] == 0


def test_el_check_vigente_en_la_base_es_la_taxonomia_del_yaml(clasificacion):
    """El contrato YAML↔SQL, leído de `pg_constraint` y no del fichero."""
    taxonomia = cargar_taxonomia()
    with clasificacion.cursor() as cur:
        cur.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'public.query_clasificacion'::regclass "
                    "AND conname = 'query_clasificacion_categoria_check';")
        definicion = cur.fetchone()[0]
    for id_valido in taxonomia.ids:
        assert f"'{id_valido}'" in definicion, id_valido
    for retirado in ("no_es_pregunta", "especificaciones",
                     "catalogo_documentacion", "instalacion_cableado"):
        assert f"'{retirado}'" not in definicion, retirado


def test_la_base_rechaza_una_categoria_fuera_de_la_taxonomia(clasificacion):
    import psycopg2
    with clasificacion.cursor() as cur:
        cur.execute("INSERT INTO query_logs (telegram_user_id, query) "
                    "VALUES (7, 'x') RETURNING id;")
        qid = cur.fetchone()[0]
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "INSERT INTO query_clasificacion (query_log_id, categoria, "
                "es_pregunta, taxonomia_version, origen) "
                "VALUES (%s, 'inventada', true, 1, 'regla');", (qid,))
    clasificacion.rollback()


def test_es_pregunta_es_obligatoria(clasificacion):
    import psycopg2
    with clasificacion.cursor() as cur:
        cur.execute("INSERT INTO query_logs (telegram_user_id, query) "
                    "VALUES (7, 'x') RETURNING id;")
        qid = cur.fetchone()[0]
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cur.execute(
                "INSERT INTO query_clasificacion (query_log_id, categoria, "
                "taxonomia_version, origen) "
                "VALUES (%s, 'otros', 1, 'regla');", (qid,))
    clasificacion.rollback()


# --------------------------------------- el eje, medido en las vistas reales


def test_las_vistas_de_analisis_excluyen_las_no_preguntas(clasificacion):
    """Siembra pareada: una pregunta y una no-pregunta, idénticas en todo lo
    demás. Las vistas de análisis tienen que contar UNA."""
    with clasificacion.cursor() as cur:
        _sembrar(cur, es_pregunta=True)
        _sembrar(cur, es_pregunta=False)
        for vista, columna in (("bot_tipologia_semanal", "consultas"),
                               ("bot_marcas_semanal", "consultas"),
                               ("bot_marcas_sin_corpus_semanal", "menciones")):
            cur.execute(f"SELECT COALESCE(sum({columna}), 0) FROM {vista};")
            assert cur.fetchone()[0] == 1, vista
        # …y el control negativo: sobre la MISMA siembra, contar sin el filtro
        # da 2. Si la aserción de arriba pasara por casualidad (p. ej. porque la
        # siembra no llegó), esto lo delata.
        cur.execute("SELECT count(*) FROM query_clasificacion;")
        assert cur.fetchone()[0] == 2
    clasificacion.rollback()


def test_los_votos_de_una_no_pregunta_no_cuentan(clasificacion):
    """El defecto que arregla la 024: `bot_preguntas_por_usuario_semanal`
    filtraba `consultas` pero NO los votos, así que el feedback dado sobre un
    «ok, entendido» entraba en una tabla titulada «preguntas por persona»."""
    with clasificacion.cursor() as cur:
        _sembrar(cur, es_pregunta=True, verdict="up")
        _sembrar(cur, es_pregunta=False, verdict="down")
        cur.execute("SELECT sum(consultas), sum(votos_up), sum(votos_down), "
                    "sum(otros_mensajes) FROM bot_preguntas_por_usuario_semanal;")
        consultas, arriba, abajo, otros = cur.fetchone()
        assert (consultas, arriba, abajo, otros) == (1, 1, 0, 1), (
            "el 👎 de la no-pregunta se coló en la vista de preguntas")
    clasificacion.rollback()


def test_la_vista_de_no_preguntas_ensena_solo_lo_que_no_pide_nada(clasificacion):
    with clasificacion.cursor() as cur:
        _sembrar(cur, es_pregunta=True)
        _sembrar(cur, es_pregunta=False)
        cur.execute("SELECT count(*) FROM bot_no_preguntas_v1;")
        assert cur.fetchone()[0] == 1
    clasificacion.rollback()


def test_una_fila_sin_clasificar_cuenta_como_pregunta(clasificacion):
    """«Ante la duda, pregunta» (adjudicación de Alberto) también en SQL: la
    fila que el job aún no ha tocado no puede desaparecer del análisis."""
    with clasificacion.cursor() as cur:
        cur.execute("INSERT INTO query_logs (telegram_user_id, query, source) "
                    "VALUES (7, 'sin clasificar todavía', 'text');")
        cur.execute("SELECT sum(consultas), sum(otros_mensajes) "
                    "FROM bot_preguntas_por_usuario_semanal;")
        assert cur.fetchone() == (1, 0)
    clasificacion.rollback()
