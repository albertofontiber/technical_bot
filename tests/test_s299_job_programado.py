"""s299 — la retención programada: UNA implementación de la pasada, y el reloj en la base.

Contrato que se fija aquí:
  · la pasada vive en la BASE (`public.rgpd_retencion_pasada`) y es ÚNICA: el script
    manual y pg_cron ejecutan exactamente el mismo código — dos implementaciones de una
    operación irreversible driftarían, y una de las dos «cumpliría» sin cumplir;
  · el script es un DRIVER: una llamada, commit o rollback — el dry-run es la misma
    pasada revertida (y revierte también el recibo);
  · el reloj es pg_cron: ninguna credencial sale de la base para programar la retención;
  · cuando falta la migración, el script lo dice y sale con 2 en vez de aparentar.

El comportamiento de la función contra Postgres REAL (rol asumido, ventana RLS, recibos,
punto de no retorno) se ejerce en `test_s295_rgpd_integracion_pg.py`.
"""

import json
from pathlib import Path

REPO = Path(__file__).parent.parent
PROPUESTA_S299 = (
    REPO / "supabase" / "migration_proposals"
    / "20260805150000_s299_job_programado_v1.sql"
)


def _sql() -> str:
    return PROPUESTA_S299.read_text(encoding="utf-8")


def _fuente_driver() -> str:
    return (REPO / "scripts" / "rgpd_retencion.py").read_text(encoding="utf-8")


# ------------------------------------------------------------- una sola implementación


def test_la_pasada_vive_en_la_base_y_es_unica():
    """El corazón de s299: las sentencias de la pasada están en la FUNCIÓN, y el script
    ya no lleva ninguna — si alguien re-introduce un UPDATE/DELETE en el driver, vuelve
    la dualidad que esta sesión eliminó y este test lo dice."""
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION public.rgpd_retencion_pasada" in sql
    # El ciclo completo dentro de la función: 3 disociaciones que ESTAMPAN el seudónimo,
    # el borrado del ancla, y el punto de no retorno con visibilidad completa.
    assert sql.count("SET seudonimo = p.seudonimo, telegram_user_id = NULL") == 3
    assert "DELETE FROM public.answer_messages" in sql
    assert "rgpd_quedan_identificados" in sql
    assert "INSERT INTO public.rgpd_recibos" in sql

    fuente = _fuente_driver()
    assert "rgpd_retencion_pasada('manual')" in fuente
    for sentencia in ("UPDATE public.", "DELETE FROM public.", "SET LOCAL ROLE"):
        assert sentencia not in fuente, (
            f"el driver vuelve a llevar `{sentencia}`: la pasada dejaría de ser única"
        )


def test_la_funcion_asume_el_rol_en_el_encabezado():
    """`SET role` a nivel de función: también la ejecución programada corre acotada por
    las políticas RLS del rol. Y el cinturón del tirante: el cuerpo comprueba
    `current_user` por si una edición futura quitara el encabezado."""
    sql = _sql()
    assert "SET role = rgpd_retencion" in sql
    assert "IF current_user <> 'rgpd_retencion'" in sql
    # La combinación con historial de CVE queda prohibida por postcondición.
    assert "NOT prosecdef" in sql


def test_la_ventana_no_se_repite_en_la_funcion():
    """Las sentencias de la pasada NO llevan cota temporal: la ventana la imponen las
    políticas RLS y SOLO ellas (única fuente del plazo). El `corte` de la función es
    informativo — la misma expresión que las políticas, para el recibo."""
    sql = _sql()
    cuerpo = sql.split("$rgpd_pasada$")[1]
    assert "created_at <" not in cuerpo
    assert "now() - interval '24 months'" in cuerpo     # el corte informativo del recibo


def test_el_reloj_es_mensual_y_condicional():
    """pg_cron si está disponible (producción); WARNING si no (contenedor de CI). Y la
    postcondición hace imposible el «verde sin programar»: pg_cron instalado ⇒ el job
    existe con su comando."""
    sql = _sql()
    assert "pg_available_extensions" in sql
    assert "CREATE EXTENSION IF NOT EXISTS pg_cron" in sql
    assert "'rgpd-retencion-mensual'" in sql
    assert "'30 4 1 * *'" in sql                        # mensual, día 1
    assert "SELECT public.rgpd_retencion_pasada(''cron'')" in sql
    assert ("el job mensual no existe, esta inactivo, cambio de "
            "horario/comando, o su username no puede asumir el rol") in sql


def test_los_recibos_estan_blindados_y_el_bot_no_ejecuta_la_pasada():
    sql = _sql()
    assert "CREATE TABLE IF NOT EXISTS public.rgpd_recibos" in sql
    assert "origen IN ('manual', 'cron')" in sql
    assert "REVOKE ALL PRIVILEGES ON TABLE public.rgpd_recibos" in sql
    assert "GRANT INSERT ON TABLE public.rgpd_recibos TO rgpd_retencion" in sql
    # NOMINAL, no solo PUBLIC (dúo s299 + catálogo vivo): los default privileges de
    # Supabase dan EXECUTE a la API entera sobre toda función nueva de `public`.
    assert "REVOKE ALL ON FUNCTION public.rgpd_retencion_pasada(TEXT)" in sql
    assert "REVOKE ALL ON FUNCTION public.rgpd_quedan_identificados(BIGINT)" in sql
    assert sql.count("FROM PUBLIC, anon, authenticated, service_role") >= 3


def test_el_oraculo_aprende_el_ancla_y_el_origen_es_explicito():
    """Los dos hallazgos del dúo con forma de texto en la migración: (a) el punto de no
    retorno mira TAMBIÉN `answer_messages` (chat_id == la persona en privado); (b) el
    origen del recibo no tiene default que estampe 'cron' en una pasada manual."""
    sql = _sql()
    assert "FROM public.answer_messages WHERE telegram_chat_id = p_user" in sql
    assert "DEFAULT 'cron'" not in sql
    # Y el reloj exige membresía SET de quien programa + postcondición sobre username.
    assert "set_option" in sql
    assert "j.active" in sql and "j.schedule = '30 4 1 * *'" in sql


def test_la_propuesta_no_esta_en_el_camino_auto_aplicado():
    assert PROPUESTA_S299.exists()
    assert not list((REPO / "supabase" / "migrations").glob("*s299*"))


def test_la_propuesta_exige_la_cola_completa_y_declara_su_rollback():
    sql = _sql()
    for ancla in ("20260803140000_s295", "20260804120000_s296", "20260805120000_s297",
                  "ROLLBACK", "cron.unschedule"):
        assert ancla in sql


# ------------------------------------------------------------------ el driver


_RECIBO = {
    "corte": "2026-08-05T04:30:00+00:00",
    "origen": "manual",
    "tablas": {
        "query_logs":        {"modo": "nulificar", "tocadas": 2, "ids": ["id-1", "id-2"]},
        "feedback":          {"modo": "nulificar", "tocadas": 0, "ids": []},
        "answer_feedback":   {"modo": "nulificar", "tocadas": 0, "ids": []},
        "answer_messages":   {"modo": "borrar", "tocadas": 1, "ids": ["id-3"]},
        "persona_seudonimo": {"modo": "destruir_vinculo", "tocadas": 0, "ids": []},
    },
}


class _CursorFalso:
    def __init__(self, registro):
        self.registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.registro["sql"].append((sql, params))

    def fetchone(self):
        # psycopg2 des-serializa jsonb a dict con los typecasters por defecto.
        return (dict(_RECIBO),)


class _ConexionFalsa:
    def __init__(self):
        self.registro = {"sql": [], "commit": 0, "rollback": 0}

    def cursor(self):
        return _CursorFalso(self.registro)

    def commit(self):
        self.registro["commit"] += 1

    def rollback(self):
        self.registro["rollback"] += 1


def test_el_dry_run_es_la_misma_pasada_revertida():
    """No se sondea nada: se llama a la función REAL (privilegios, RLS y constraints
    evaluados sobre filas de verdad) y se revierte — el recibo en base incluido."""
    from scripts.rgpd_retencion import ejecutar

    conexion = _ConexionFalsa()
    recibo = ejecutar(False, conexion)

    assert conexion.registro["rollback"] == 1
    assert conexion.registro["commit"] == 0
    assert recibo["tablas"]["query_logs"]["tocadas"] == 2
    assert "persona_seudonimo" in recibo["tablas"]


def test_aplicar_confirma_la_transaccion():
    from scripts.rgpd_retencion import ejecutar

    conexion = _ConexionFalsa()
    ejecutar(True, conexion)

    assert conexion.registro["commit"] == 1
    assert conexion.registro["rollback"] == 0


def test_el_driver_hace_una_sola_llamada():
    """Timeout de sesión + LA llamada. Ni SET LOCAL ROLE (lo asume la función en su
    encabezado) ni sentencia alguna sobre las tablas: el driver no puede driftar de la
    pasada porque no lleva pasada."""
    from scripts.rgpd_retencion import ejecutar

    conexion = _ConexionFalsa()
    ejecutar(False, conexion)

    sentencias = [s for s, _ in conexion.registro["sql"]]
    assert len(sentencias) == 2
    assert sentencias[0].startswith("SET LOCAL statement_timeout")
    assert "rgpd_retencion_pasada('manual')" in sentencias[1]


def test_un_fallo_revierte_y_propaga():
    from scripts.rgpd_retencion import ejecutar

    class _Explota(_ConexionFalsa):
        def cursor(self):
            class _C(_CursorFalso):
                def execute(self, sql, params=None):
                    super().execute(sql, params)
                    if "rgpd_retencion_pasada" in sql:
                        raise RuntimeError("boom")
            return _C(self.registro)

    conexion = _Explota()
    try:
        ejecutar(True, conexion)
    except RuntimeError:
        pass
    else:
        raise AssertionError("el fallo debe propagarse, no tragarse")

    assert conexion.registro["rollback"] == 1
    assert conexion.registro["commit"] == 0


def test_el_diagnostico_conoce_la_migracion_nueva():
    from scripts.rgpd_retencion import _diagnosticar

    diag = _diagnosticar(
        RuntimeError('function public.rgpd_retencion_pasada(unknown) does not exist')
    )
    assert "20260805150000_s299_job_programado_v1.sql" in diag
    # Y las causas anteriores siguen diagnosticándose (la migración s295, los permisos).
    assert "NO EXISTE" in _diagnosticar(RuntimeError('role "rgpd_retencion" does not exist'))


def test_main_escribe_el_recibo_local(monkeypatch, tmp_path, capsys):
    """La copia local del operador: corte + meses + aplicado + tablas, y los ids ANTES
    por stdout (la traza no puede depender de que `open()` funcione)."""
    import sys

    import scripts.rgpd_retencion as job

    destino = tmp_path / "recibo.json"
    monkeypatch.setattr(job, "ejecutar", lambda aplicar, conexion=None: dict(_RECIBO))
    monkeypatch.setattr(sys, "argv",
                        ["rgpd_retencion.py", "--aplicar", "--recibo", str(destino)])

    assert job.main() == 0
    salida = capsys.readouterr().out
    assert "ids query_logs: id-1, id-2" in salida
    escrito = json.loads(destino.read_text(encoding="utf-8"))
    assert escrito["aplicado"] is True
    assert escrito["meses"] == 24
    assert escrito["tablas"]["query_logs"]["ids"] == ["id-1", "id-2"]


def test_el_recibo_local_se_escribe_aunque_solo_caigan_vinculos(monkeypatch, tmp_path):
    """Dúo s299: la pasada que SOLO destruye vínculos toca filas cuyo id no se registra
    a propósito (el id ES la persona). Con `ids` como criterio, esa pasada confirmada e
    irreversible no dejaba recibo local pese a `--recibo`. El criterio es `tocadas`."""
    import sys

    import scripts.rgpd_retencion as job

    solo_vinculos = {
        "corte": "2028-09-01T04:30:00+00:00",
        "origen": "manual",
        "tablas": {
            "query_logs":        {"modo": "nulificar", "tocadas": 0, "ids": []},
            "feedback":          {"modo": "nulificar", "tocadas": 0, "ids": []},
            "answer_feedback":   {"modo": "nulificar", "tocadas": 0, "ids": []},
            "answer_messages":   {"modo": "borrar", "tocadas": 0, "ids": []},
            "persona_seudonimo": {"modo": "destruir_vinculo", "tocadas": 3, "ids": []},
        },
    }
    destino = tmp_path / "recibo.json"
    monkeypatch.setattr(job, "ejecutar", lambda aplicar, conexion=None: solo_vinculos)
    monkeypatch.setattr(sys, "argv",
                        ["rgpd_retencion.py", "--aplicar", "--recibo", str(destino)])

    assert job.main() == 0
    escrito = json.loads(destino.read_text(encoding="utf-8"))
    assert escrito["tablas"]["persona_seudonimo"]["tocadas"] == 3
