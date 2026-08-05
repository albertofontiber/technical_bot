#!/usr/bin/env python3
"""rgpd_retencion.py — retención de 24 meses por DISOCIACIÓN: el driver manual.

Principio (matriz `docs/RGPD_RETENCION.md`, decisión de Alberto): el valor del histórico
está en el CONTENIDO (pregunta, respuesta, explicación de un fallo = material de
evaluación y candidatos a gold), **no en quién preguntó**. Así que el plazo no termina en
un `DELETE` sino retirando el identificador.

Con el nombre correcto: **SEUDONIMIZACIÓN, no anonimización** (Considerando 26). El texto
libre de un técnico puede contener un nombre, una empresa o una obra, y eso no lo arregla
quitar columnas.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE EJECUTA — y por qué así

**La pasada vive en la BASE, no aquí** (s299): `public.rgpd_retencion_pasada()` es la
ÚNICA implementación — la misma que ejecuta pg_cron cada mes (`rgpd-retencion-mensual`).
Este script es el driver manual de ESA función: conexión DIRECTA (`DATABASE_URL`) +
`SELECT public.rgpd_retencion_pasada('manual')`, **no** PostgREST con la clave de
servicio. Dos implementaciones de una operación irreversible driftarían; una sola no
puede contradecirse a sí misma.

Las garantías, y DÓNDE vive cada una:

1. **La ventana de 24 meses la impone la BASE**: las políticas RLS del rol
   `rgpd_retencion` acotan lo que la pasada puede tocar a
   `created_at < now() - interval '24 months'`. La función asume el rol en su ENCABEZADO
   (`SET role`) y ABORTA si no quedó asumido — ni un bug ni un parámetro pueden tocar
   una fila reciente. Por eso NO hay flag `--meses`: el plazo se cambia por migración.
2. **El dry-run verifica el EFECTO.** Sin `--aplicar`, la misma llamada corre DE VERDAD
   (privilegios y constraints evaluados sobre filas reales) y se hace `ROLLBACK` — que
   revierte también el recibo: toda fila persistida en `rgpd_recibos` corresponde a una
   pasada confirmada.
3. **Atomicidad.** La pasada entera es una función en UNA transacción: o todo o nada.

**Por defecto NO escribe**: sin `--aplicar` hace la pasada completa y revierte.
═══════════════════════════════════════════════════════════════════════════════

REQUIERE la cola de migraciones s295 → s296 → s297 → s299 (`supabase/migration_proposals/`).
En un entorno donde falte algo, el script lo dice y sale con código 2 en vez de aparentar
cumplimiento.

FUERA DE ALCANCE, con dueño declarado en la matriz: `user_consent`/`consent_events`
(plazo pendiente de decidir con el asesor), los exports a disco de
`scripts/review_logs.py` (desde s296 llevan solo el seudónimo), y el extracto de recibos
versionado en git.

Uso:
  python scripts/rgpd_retencion.py                 # dry-run (ejecuta y revierte)
  python scripts/rgpd_retencion.py --aplicar       # confirma
  python scripts/rgpd_retencion.py --aplicar --recibo evals/rgpd_2028.json

La ejecución PROGRAMADA no pasa por aquí: pg_cron llama a la función directamente, dentro
de la base, y deja su recibo en `public.rgpd_recibos`. Ninguna credencial sale de la base
para programarla — ese fue el motivo de elegir pg_cron (s299) frente a un cron externo,
que habría exigido guardar fuera un `DATABASE_URL` de operador, más potente que el
`service_role` que s295 evitó tocar.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

ROL = "rgpd_retencion"
# Solo para MENSAJES y el recibo a fichero. La ventana real la imponen las politicas RLS
# del rol, y el corte que se imprime viene de la BASE (lo devuelve la funcion): si esto
# divergiera, mandaria la politica y este numero solo estaria mal en un print.
VENTANA_MESES = 24


def _construir_parser() -> argparse.ArgumentParser:
    """Extraído para que el test interrogue ESTE parser y no uno paralelo."""
    parser = argparse.ArgumentParser(description=__doc__)
    # NO hay `--meses`: la ventana la fija la POLITICA RLS del rol (24 meses). Un flag que
    # pudiera contradecirla mentiria en las dos direcciones -- `--meses 30` terminaria "con
    # exito" dejando sin tratar filas vencidas de 24 a 30 meses, y `--meses 1` anunciaria un
    # corte que la base filtra en silencio. El plazo es una decision gobernada: se cambia por
    # migracion, no por linea de comandos.
    parser.add_argument(
        "--aplicar", action="store_true",
        help="CONFIRMA la transaccion. Sin el flag se ejecuta igual y se revierte.",
    )
    parser.add_argument(
        "--recibo", default=None,
        help="Fichero JSON con constancia DURABLE de que filas se tocaron. Las pasadas "
             "CONFIRMADAS dejan ademas su recibo en public.rgpd_recibos (dentro de la "
             "base); este fichero es la copia local del operador.",
    )
    return parser


def ejecutar(aplicar: bool, conexion=None) -> dict:
    """UNA llamada a la única implementación (`public.rgpd_retencion_pasada`, s299).

    `aplicar=False` ⇒ `ROLLBACK`: la pasada ha corrido de verdad (privilegios, RLS y
    constraints evaluados sobre filas reales) y no queda rastro — tampoco el recibo en
    `rgpd_recibos`, que la función escribe dentro de la misma transacción.

    El rol NO se asume aquí: lo asume la función en su encabezado (`SET role`) y su
    primera comprobación aborta si no surtió efecto. Mover esa guarda a la base es lo que
    la hace valer también para la ejecución programada, que no pasa por este script.
    """
    import psycopg2                                    # noqa: PLC0415 — dependencia de ops

    dsn = os.environ.get("DATABASE_URL")
    if not dsn and conexion is None:
        raise RuntimeError(
            "Falta DATABASE_URL. Este job NO usa la clave de servicio a proposito: el "
            "privilegio vive en el rol dedicado `rgpd_retencion`, que la funcion de la "
            "pasada asume desde una conexion de operador."
        )

    propia = conexion is None
    conexion = conexion or psycopg2.connect(dsn, connect_timeout=15)
    try:
        with conexion.cursor() as cur:
            # `SET LOCAL` es de la transaccion del driver; acota la sentencia siguiente
            # (la pasada entera es UNA sentencia). En el reloj de pg_cron no aplica y no
            # hace falta: a esta escala la pasada es de milisegundos.
            cur.execute("SET LOCAL statement_timeout = '120s';")
            cur.execute("SELECT public.rgpd_retencion_pasada('manual');")
            crudo = cur.fetchone()[0]
        recibo = crudo if isinstance(crudo, dict) else json.loads(crudo)
        if aplicar:
            conexion.commit()
        else:
            conexion.rollback()
    except Exception:
        conexion.rollback()
        raise
    finally:
        if propia:
            conexion.close()
    return recibo


def _diagnosticar(error: Exception) -> str:
    """Traduce el fallo al hueco real, en vez de dejar un traceback críptico."""
    texto = str(error)
    if "rgpd_retencion_pasada" in texto and (
        "does not exist" in texto or "no existe" in texto
    ):
        return (
            "La funcion de la pasada NO EXISTE. La retencion no es ejecutable aqui:\n"
            "   aplica supabase/migration_proposals/"
            "20260805150000_s299_job_programado_v1.sql\n"
            "   (la unica implementacion de la pasada + los recibos + el reloj pg_cron)."
        )
    if ROL in texto and ("does not exist" in texto or "no existe" in texto):
        return (
            f"El rol `{ROL}` NO EXISTE. La retencion no es ejecutable todavia:\n"
            "   aplica supabase/migration_proposals/"
            "20260803140000_s295_rgpd_rol_retencion_v2.sql\n"
            "   (crea el rol acotado; NO toca service_role ni el hardening de julio)."
        )
    if "permission denied" in texto or "denegado" in texto:
        return f"Al rol `{ROL}` le faltan privilegios: {texto.strip()[:200]}"
    if "null value" in texto and "not-null" in texto:
        return (
            "Falta el `DROP NOT NULL` de answer_feedback.telegram_user_id "
            "(punto 4 de la propuesta s295)."
        )
    return f"Fallo no previsto: {type(error).__name__}: {texto.strip()[:200]}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = _construir_parser().parse_args()

    print(f"retencion: {VENTANA_MESES} meses de calendario (la ventana la impone la "
          f"politica RLS del rol; el corte exacto lo devuelve la base)")
    print(f"pasada: public.rgpd_retencion_pasada (unica implementacion; corre como {ROL})")
    print(f"modo: {'APLICAR (commit)' if args.aplicar else 'dry-run (ejecuta y revierte)'}\n")

    try:
        recibo = ejecutar(args.aplicar)
    except Exception as e:                                  # noqa: BLE001
        print("NO PUEDE CUMPLIR LA RETENCION -- no se ha escrito NADA (transaccion revertida).")
        print("   " + _diagnosticar(e))
        print(
            "\nUn job de retencion que no puede ejecutarse APARENTA cumplimiento, que es\n"
            "peor que no tenerlo: por eso esto es exit 2 y no un aviso de refilon."
        )
        return 2

    tablas = recibo["tablas"]
    print(f"corte (informado por la base): {recibo['corte']}")
    for tabla, fila in tablas.items():
        print(f"  {tabla:19s} {fila['modo']:17s} tocadas={fila['tocadas']:5d}")
    # Los ids salen por stdout ANTES que nada mas: si el recibo en fichero fallase, la traza
    # de una operacion irreversible no puede depender de que `open()` funcione. (La pasada
    # confirmada deja ademas su recibo DENTRO de la base, en public.rgpd_recibos.)
    for tabla, fila in tablas.items():
        if fila["ids"]:
            print(f"    ids {tabla}: {', '.join(fila['ids'])}")

    print(
        "\nALCANCE Y LIMITE. Cubre el ciclo de las 4 tablas + la destruccion del vinculo,\n"
        "en UNA transaccion. Aun asi es SEUDONIMIZACION, no anonimizacion: el texto libre\n"
        "(pregunta, transcripcion, comentario del voto) puede identificar, y eso no lo\n"
        "arregla quitar columnas. Fuera de alcance, con dueno declarado en\n"
        "docs/RGPD_RETENCION.md: `user_consent`/`consent_events`, los exports a disco de\n"
        "scripts/review_logs.py, y el extracto de recibos versionado en git.\n"
        "La ventana de 24 meses la impone la POLITICA RLS del rol, no este script."
    )

    # Por `tocadas` y no por `ids`: una pasada que SOLO destruye vínculos toca filas cuyo
    # id no se registra a propósito (el id ES la persona) — con `ids` como criterio, esa
    # pasada confirmada e irreversible no dejaría recibo local pese a pedirlo (dúo s299).
    if args.recibo and any(f["tocadas"] for f in tablas.values()):
        with open(args.recibo, "w", encoding="utf-8") as fh:
            json.dump(
                {"corte": recibo["corte"], "meses": VENTANA_MESES,
                 "aplicado": args.aplicar, "tablas": tablas},
                fh, ensure_ascii=False, indent=2,
            )
        print(f"\nrecibo durable escrito en {args.recibo}")

    print("\n" + json.dumps(recibo, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
