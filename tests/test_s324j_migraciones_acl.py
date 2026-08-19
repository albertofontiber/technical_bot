# -*- coding: utf-8 -*-
"""s324j — El gate ACL de las migraciones del panel (puertas 9, 9-bis y 6-bis
de `evals/s324i_panel_vercel_propuesta_v9.md`).

Mismo estilo que `test_s277_p1_document_local_snapshot_v2_acl.py`: se fija el
TEXTO de las migraciones, no una intención. El texto es lo que Alberto aplica
en el SQL Editor; si alguien lo relaja —o añade una tabla al panel sin su
frontera— la suite se pone roja ANTES del despliegue. (El EFECTO — lo que la
base HACE — lo afirma `test_s324j_panel_pg.py` contra un Postgres real: puerta
4. Los dos gates son capas, no redundancia.)

La puerta 9-bis existe por un agujero REAL: r41 (s324f) firmó la anulación en
`nota` sin que la 016 concediera `UPDATE (nota)` — el PATCH moría con 42501 en
producción y NINGÚN test sin red podía verlo (hallazgo S-C1 del dúo, DEC-239).
Aquí se cruza cada columna que el panel, el CLI y el cuerpo de `panel_puerta`
escriben con los GRANT de las migraciones, para que esa clase no vuelva a
entrar en silencio.
"""
from __future__ import annotations

import re
from pathlib import Path

from dashboard import auth

RAIZ = Path(__file__).resolve().parent.parent
M016 = (RAIZ / "migrations" / "016_allowlist_invitaciones.sql").read_text("utf-8")
M019 = (RAIZ / "migrations" / "019_panel_usuarios_cerrojo.sql").read_text("utf-8")
M020 = (RAIZ / "migrations" / "020_invitaciones_op.sql").read_text("utf-8")


def _compacta(texto: str) -> str:
    """Espacios normalizados, para afirmar sentencias multilínea."""
    return re.sub(r"\s+", " ", texto)


C019 = _compacta(M019)
C020 = _compacta(M020)


# ------------------------------------------------------------------- puerta 9


def test_las_dos_tablas_nuevas_llevan_rls_force_y_revoke():
    for tabla in ("panel_usuarios", "panel_intentos"):
        assert f"ALTER TABLE public.{tabla} ENABLE ROW LEVEL SECURITY" in C019
        assert f"ALTER TABLE public.{tabla} FORCE ROW LEVEL SECURITY" in C019
        assert (f"REVOKE ALL PRIVILEGES ON TABLE public.{tabla} "
                f"FROM PUBLIC, anon, authenticated, service_role") in C019


def test_panel_usuarios_solo_concede_lo_enumerado():
    assert ("GRANT SELECT (usuario, registro, activo) "
            "ON public.panel_usuarios TO service_role") in C019
    assert ("GRANT INSERT (usuario, registro, activo, alta_por) "
            "ON public.panel_usuarios TO service_role") in C019
    assert ("GRANT UPDATE (registro, activo, revocado_en, revocado_por) "
            "ON public.panel_usuarios TO service_role") in C019
    # Sin DELETE (baja lógica) y sin GRANT de escritura sobre la auditoría:
    assert "GRANT DELETE ON public.panel_usuarios" not in C019
    assert not re.search(r"GRANT UPDATE \([^)]*\balta_por\b", C019)
    assert not re.search(r"GRANT (UPDATE|INSERT) \([^)]*\bcreado_en\b", C019)


def test_panel_intentos_los_cuatro_grant_y_los_del_rol_de_retencion():
    assert "GRANT SELECT ON public.panel_intentos TO service_role" in C019
    assert ("GRANT INSERT (clave, fallos, ultimo) "
            "ON public.panel_intentos TO service_role") in C019
    assert ("GRANT UPDATE (fallos, ultimo) "
            "ON public.panel_intentos TO service_role") in C019
    assert "GRANT DELETE ON public.panel_intentos TO service_role" in C019
    assert ("GRANT SELECT (clave, ultimo) "
            "ON public.panel_intentos TO rgpd_retencion") in C019
    assert "GRANT DELETE ON public.panel_intentos TO rgpd_retencion" in C019
    assert ("CREATE POLICY rgpd_retencion_ventana ON public.panel_intentos "
            "TO rgpd_retencion USING (ultimo < now() - interval '24 hours')") in C019


def test_las_funciones_llevan_su_revoke_y_su_grant_exacto():
    firma = "public.panel_puerta(text[], int, numeric, numeric, numeric, int)"
    assert f"REVOKE ALL ON FUNCTION {firma} FROM PUBLIC, anon, authenticated" in C019
    assert f"GRANT EXECUTE ON FUNCTION {firma} TO service_role" in C019
    # La hermana: REVOKE NOMINAL, service_role incluido — nadie la ejecuta por
    # la API (rondas S4-M3/F4-M1: la clase s296 exacta).
    assert ("REVOKE ALL ON FUNCTION public.panel_retencion_pasada(TEXT) "
            "FROM PUBLIC, anon, authenticated, service_role") in C019
    assert "GRANT EXECUTE ON FUNCTION public.panel_retencion_pasada" not in C019


def test_panel_puerta_es_invoker_con_search_path_vacio_y_lock_timeout():
    assert "SECURITY INVOKER" in M019
    assert "SET search_path = ''" in M019
    assert "lock_timeout" in M019
    assert "pg_advisory_xact_lock(hashtext('panel_intentos'))" in M019
    # SIEMPRE upsert, nunca UPDATE a secas (ronda S6-M2):
    assert "ON CONFLICT (clave) DO UPDATE" in C019
    assert "SET fallos = public.panel_intentos.fallos + 1" in C019


def test_la_hermana_corre_como_el_rol_con_cinturon_y_ventana_asertada():
    assert "SET role = rgpd_retencion" in M019
    assert "current_user <> 'rgpd_retencion'" in M019
    assert "rgpd_retencion_ventana" in M019
    assert "'panel-retencion-diaria'" in M019
    assert "'45 4 * * *'" in M019          # DIARIO (ronda S5-M1), no mensual


def test_la_020_lleva_op_revocada_por_check_y_sus_grant():
    assert ("ADD COLUMN op TEXT NOT NULL UNIQUE "
            "DEFAULT gen_random_uuid()::text") in C020
    # Tanda 3 del 2º frontera: longitud Y charset en la base (antes el charset
    # vivía solo en el regex del panel).
    assert "CHECK (op ~ '^[A-Za-z0-9_-]{8,64}$')" in C020
    assert "ADD COLUMN revocada_por TEXT" in C020
    assert "SET revocada_por = '(anterior a la 020)'" in C020
    assert "bot_invitaciones_revocacion_completa" in C020
    assert "GRANT INSERT (op) ON public.bot_invitaciones TO service_role" in C020
    assert ("GRANT UPDATE (revocada_por) "
            "ON public.bot_invitaciones TO service_role") in C020
    # El cierre estructural NO es conceder la nota (ronda S2-M4):
    assert "GRANT UPDATE (nota)" not in C020


def test_ambas_llevan_notify_pgrst_y_el_contrato_de_aplicacion():
    for texto in (M019, M020):
        assert "NOTIFY pgrst, 'reload schema';" in texto
        # El contrato de aplicación (ronda S5-C1 / lección 016): fichero entero
        # con aplicador transaccional, y SIN BEGIN/COMMIT propios.
        assert "CONTRATO DE APLICACIÓN" in texto
        assert "--single-transaction" in texto
        assert not re.search(r"^\s*BEGIN\s*;", texto, re.MULTILINE)
        assert not re.search(r"^\s*COMMIT\s*;", texto, re.MULTILINE)


def test_el_preflight_exige_la_cola_s295_s299():
    assert "rgpd_retencion" in M019.split("FASE A")[0]
    assert "rgpd_recibos" in M019.split("FASE A")[0]


# --------------------------------------------------------------- puerta 9-bis
#
# Toda columna que se ESCRIBE tiene su GRANT. Los payloads se enumeran aquí, al
# lado de los greps — si `gestion.py` o el CLI ganan una columna nueva, este
# test obliga a tocar la migración (o a mirar por qué no).


def _columnas_update_concedidas(texto_migraciones: str, tabla: str) -> set:
    columnas: set = set()
    for m in re.finditer(
            rf"GRANT UPDATE \(([^)]+)\) ON public\.{tabla} TO service_role",
            texto_migraciones):
        columnas |= {c.strip() for c in m.group(1).split(",")}
    return columnas


def _columnas_insert_concedidas(texto_migraciones: str, tabla: str) -> set:
    columnas: set = set()
    for m in re.finditer(
            rf"GRANT INSERT \(([^)]+)\) ON (?:TABLE )?public\.{tabla} TO service_role",
            texto_migraciones):
        columnas |= {c.strip() for c in m.group(1).split(",")}
    return columnas


TODO_EL_SQL = _compacta(M016) + " " + C019 + " " + C020

#: Lo que el PANEL escribe (gestion.py) — copiado de sus payloads, no inferido.
PAYLOAD_INSERT_INVITACION = {"token_hash", "nota", "creada_por", "expira_at", "op"}
PAYLOAD_PATCH_ANULAR = {"revocada_at", "revocada_por"}
PAYLOAD_PATCH_REVOCAR_ACCESO = {"revocado_at", "revocado_por", "motivo_revocacion"}
#: Lo que el CLI escribe de más (s324e_invitaciones.py cmd_revocar_invitacion).
PAYLOAD_CLI_ANULAR = {"revocada_at", "revocada_por"}
#: Lo que el cuerpo de `panel_puerta` escribe (INVOKER ⇒ ejerce estos GRANT).
PAYLOAD_RPC_PANEL_INTENTOS = {"clave", "fallos", "ultimo"}
#: Lo que el script de usuarios escribe.
PAYLOAD_SCRIPT_ALTA = {"usuario", "registro", "activo", "alta_por"}
PAYLOAD_SCRIPT_REVOCAR = {"activo", "revocado_en", "revocado_por"}


def test_toda_columna_escrita_tiene_su_grant():
    assert PAYLOAD_INSERT_INVITACION <= _columnas_insert_concedidas(
        TODO_EL_SQL, "bot_invitaciones"), "INSERT de invitar sin GRANT completo"
    assert PAYLOAD_PATCH_ANULAR <= _columnas_update_concedidas(
        TODO_EL_SQL, "bot_invitaciones"), (
        "el PATCH de anular escribe columnas sin GRANT — la clase S-C1")
    assert PAYLOAD_CLI_ANULAR <= _columnas_update_concedidas(
        TODO_EL_SQL, "bot_invitaciones")
    assert PAYLOAD_PATCH_REVOCAR_ACCESO <= _columnas_update_concedidas(
        TODO_EL_SQL, "bot_allowlist")
    assert PAYLOAD_RPC_PANEL_INTENTOS <= _columnas_insert_concedidas(
        TODO_EL_SQL, "panel_intentos")
    assert {"fallos", "ultimo"} <= _columnas_update_concedidas(
        TODO_EL_SQL, "panel_intentos")
    assert PAYLOAD_SCRIPT_ALTA <= _columnas_insert_concedidas(
        TODO_EL_SQL, "panel_usuarios")
    assert PAYLOAD_SCRIPT_REVOCAR <= _columnas_update_concedidas(
        TODO_EL_SQL, "panel_usuarios")


def test_los_payloads_enumerados_no_han_derivado_del_codigo():
    """El espejo de la 9-bis: si el código cambia sus payloads y nadie toca la
    enumeración de arriba, esto lo dice. Greps sobre el fuente, frágiles a
    propósito — un payload nuevo DEBE pasar por aquí."""
    gestion_src = (RAIZ / "dashboard" / "gestion.py").read_text("utf-8")
    for columna in PAYLOAD_INSERT_INVITACION:
        assert f'"{columna}"' in gestion_src
    assert '"revocada_por": f"panel:{por}"' in gestion_src
    assert "_nota_con_firma" not in gestion_src, (
        "la firma-en-nota de r41 volvió — estaba rota (42501) y la 020 la "
        "sustituyó por revocada_por")
    cli_src = (RAIZ / "scripts" / "s324e_invitaciones.py").read_text("utf-8")
    assert '"revocada_at": "is.null"' in cli_src
    assert '"canjeada_at": "is.null"' in cli_src
    script_src = (RAIZ / "scripts" / "s324j_panel_usuario.py").read_text("utf-8")
    assert "return=minimal" in script_src        # S6-M3
    assert "validar_registro_estricto" in script_src


# --------------------------------------------------------------- puerta 6-bis
#
# El charset vive duplicado por necesidad (regex SQL en el CHECK, regex Python
# en auth): esta puerta impide que diverjan, con una tabla de casos compartida.

CASOS_CHARSET = [
    ("alberto", True),
    ("ana.perez@fontiber.com", True),
    ("dg-acme_2", True),
    ("a" * 64, True),
    ("", False),
    ("a" * 65, False),
    ("Alberto", False),                  # mayúsculas: la normalización va antes
    ("con espacio", False),
    ("come,coma", False),                # estructura de filtros PostgREST
    ("paren(tesis)", False),
    ("emoji😀", False),
]


def test_el_check_sql_y_el_guard_python_aceptan_y_rechazan_igual():
    m = re.search(r"usuario ~ '([^']+)'", M019)
    assert m, "el CHECK de charset de panel_usuarios no está en la 019"
    regex_sql = re.compile(m.group(1))
    for nombre, esperado in CASOS_CHARSET:
        assert bool(regex_sql.fullmatch(nombre)) is esperado, (nombre, "SQL")
        assert auth.usuario_admisible(nombre) is esperado, (nombre, "Python")
