# -*- coding: utf-8 -*-
"""s326 — el gate ACL/contrato de la migración 021 (patrón test_s324j_migraciones_acl).

Se fija el TEXTO de la migración, no una intención: el texto es lo que Alberto
aplica en el SQL Editor. Las puertas:
  · la tabla derivada lleva RLS ENABLE+FORCE y REVOKE total antes de conceder;
  · las OCHO vistas nacen con security_invoker y con anon/authenticated
    revocados (una vista del panel legible por anon = el panel entero filtrado);
  · el contrato de aplicación de la 016/019 se respeta: NI BEGIN NI COMMIT
    dentro del fichero, y NOTIFY pgrst al final;
  · la vista fila-a-fila NO expone `response` (el Explorador enseña la
    PREGUNTA — adjudicación (a) — no las respuestas) y excluye las filas error.

El cruce taxonomía-YAML ↔ CHECK y payload ↔ GRANT INSERT vive en
test_s326_clasificacion.py, al lado del código que escribe.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
M021 = (RAIZ / "migrations" / "021_query_clasificacion.sql").read_text("utf-8")
C021 = re.sub(r"\s+", " ", M021)

VISTAS = (
    "bot_tipologia_semanal",
    "bot_clasificacion_cobertura",
    "bot_marcas_semanal",
    "bot_modelos_semanal",
    "bot_feedback_tipologia_semanal",
    "bot_preguntas_por_usuario_semanal",
    "bot_marcas_sin_corpus_semanal",
    "bot_explorador_v1",
)


def _sin_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def test_sin_begin_ni_commit_propios():
    """Lección de la 016 (dos fallos REALES en producción): el fichero se aplica
    entero con un aplicador transaccional y no lleva control de transacción."""
    limpio = _sin_comentarios(M021)
    assert not re.search(r"^\s*BEGIN\s*;", limpio, re.MULTILINE | re.IGNORECASE)
    assert not re.search(r"^\s*COMMIT\s*;", limpio, re.MULTILINE | re.IGNORECASE)


def test_la_tabla_lleva_rls_force_y_revoke_total():
    assert "ALTER TABLE public.query_clasificacion ENABLE ROW LEVEL SECURITY" in C021
    assert "ALTER TABLE public.query_clasificacion FORCE ROW LEVEL SECURITY" in C021
    assert ("REVOKE ALL PRIVILEGES ON TABLE public.query_clasificacion "
            "FROM PUBLIC, anon, authenticated, service_role") in C021


def test_las_concesiones_son_enumeradas_y_solo_a_service_role():
    assert "GRANT SELECT ON TABLE public.query_clasificacion TO service_role" in C021
    assert re.search(r"GRANT INSERT \([^)]+\) ON public\.query_clasificacion "
                     r"TO service_role", C021)
    assert re.search(r"GRANT UPDATE \([^)]+\) ON public\.query_clasificacion "
                     r"TO service_role", C021)
    # nadie más recibe nada sobre la tabla
    assert not re.search(r"GRANT [^;]*query_clasificacion[^;]*TO (anon|authenticated)",
                         C021)


def test_update_no_concede_la_clave_primaria():
    """Re-clasificar sobrescribe CONTENIDO; mover una clasificación a otra
    pregunta (UPDATE del PK) no es una operación que exista."""
    update = re.search(r"GRANT UPDATE \(([^)]+)\)", C021)
    assert "query_log_id" not in {c.strip() for c in update.group(1).split(",")}


def test_las_ocho_vistas_nacen_con_security_invoker():
    for vista in VISTAS:
        assert (f"CREATE OR REPLACE VIEW public.{vista} "
                f"WITH (security_invoker = true)") in C021, vista


def test_las_ocho_vistas_quedan_revocadas_y_concedidas_de_una_vez():
    revoke = re.search(r"REVOKE ALL PRIVILEGES ON ([^;]+?) FROM PUBLIC, anon, "
                       r"authenticated;", C021)
    grant = re.search(r"GRANT SELECT ON ((?:public\.bot_[^;]+?)) TO service_role;",
                      C021)
    assert revoke and grant
    for vista in VISTAS:
        assert f"public.{vista}" in revoke.group(1), f"{vista} sin REVOKE"
        assert f"public.{vista}" in grant.group(1), f"{vista} sin GRANT"


def test_el_explorador_no_expone_response_y_excluye_error():
    cuerpo = re.search(
        r"CREATE OR REPLACE VIEW public\.bot_explorador_v1.*?;", C021).group(0)
    assert "ql.response_length" in cuerpo
    assert not re.search(r"ql\.response\b(?!_length)", cuerpo), (
        "bot_explorador_v1 no expone la respuesta: para leer respuestas está "
        "la base, no el panel")
    assert "ql.source <> 'error'" in cuerpo


def test_cascade_y_postcondiciones_y_recarga():
    assert "REFERENCES public.query_logs(id) ON DELETE CASCADE" in C021
    assert "NOTIFY pgrst, 'reload schema';" in C021
    assert "has_column_privilege" in C021          # la 021 se auto-comprueba
    assert "relrowsecurity AND relforcerowsecurity" in C021
    # preflight: exige la cola previa con el motivo escrito
    assert "016_allowlist_invitaciones.sql" in C021
    assert "rolbypassrls" in C021


def test_el_alias_sale_de_la_nota_y_jamas_del_id():
    """Adjudicación de Alberto (s326): el alias humano es `bot_allowlist.nota`.
    Y el TRINQUETE del hallazgo Sol r1: fuera de la pestaña de Acceso, ninguna
    vista del panel correlaciona un identificador directo con conteos ni con
    prosa — el fallback del histórico es una etiqueta fija, sin id."""
    assert C021.count("COALESCE(ba.nota, 'sin alta (histórico)')") == 2
    assert "'sin alta · id '" not in C021
    assert "|| ql.telegram_user_id" not in C021
    # el id puede aparecer en JOINs/WHERE (correlacionar filas), nunca en el
    # SELECT de una vista (exponerlo): ninguna línea `ql.telegram_user_id AS`.
    assert not re.search(r"ql\.telegram_user_id\s+AS", C021)
