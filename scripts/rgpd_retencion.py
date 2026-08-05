#!/usr/bin/env python3
"""rgpd_retencion.py — retención de 24 meses por DISOCIACIÓN, sobre el rol dedicado.

Principio (matriz `docs/RGPD_RETENCION.md`, decisión de Alberto): el valor del histórico
está en el CONTENIDO (pregunta, respuesta, explicación de un fallo = material de
evaluación y candidatos a gold), **no en quién preguntó**. Así que el plazo no termina en
un `DELETE` sino retirando el identificador.

Con el nombre correcto: **SEUDONIMIZACIÓN, no anonimización** (Considerando 26). El texto
libre de un técnico puede contener un nombre, una empresa o una obra, y eso no lo arregla
quitar columnas.

═══════════════════════════════════════════════════════════════════════════════
CÓMO SE EJECUTA — y por qué así

Conexión DIRECTA (`DATABASE_URL`) + `SET LOCAL ROLE rgpd_retencion`, **no** PostgREST con
la clave de servicio. Motivo: `service_role` es la identidad del bot, el worker de Railway
encendido 24/7; darle UPDATE/DELETE le abriría superficie permanente por un privilegio que
se ejerce una vez cada varios meses. El rol dedicado es NOLOGIN y sus credenciales no viven
en el entorno del bot. Patrón ya usado aquí para `p1_readonly`.

Eso además arregla tres cosas de raíz, no con parches:

1. **El dry-run verifica el EFECTO.** Ejecuta las sentencias REALES dentro de una
   transacción y hace `ROLLBACK`. Devuelve el número exacto de filas que se tocarían, con
   los privilegios y las constraints ya evaluados sobre filas de verdad. La versión sobre
   PostgREST solo podía sondear el privilegio con un conjunto vacío — y daba un falso OK
   en `answer_feedback`, cuya columna era `NOT NULL`.
2. **Atomicidad.** Las cuatro tablas van en UNA transacción: o se hace todo o no se hace
   nada. Desaparece la posibilidad de una ejecución parcial e irreversible.
3. **La ventana de 24 meses la impone la BASE**, no este script: las políticas RLS del rol
   acotan lo que puede tocar a `created_at < now() - interval '24 months'`. Por eso NO hay
   flag `--meses`: cualquier valor que contradijera la política mentiría — uno mayor
   terminaría «con éxito» dejando filas vencidas sin tratar, y uno menor anunciaría un corte
   que la base filtra en silencio. El plazo se cambia por migración.

   Alcance honesto del invariante: rige **para quien actúa como el rol**. No ata a
   `postgres` (owner + BYPASSRLS) ni a `service_role`. Por eso lo primero que hace la
   transacción es comprobar `current_user`: un `SET LOCAL ROLE` fuera de transacción es un
   NO-OP con warning, y sin esa comprobación todo correría como el operador.

**Por defecto NO escribe**: sin `--aplicar` hace la pasada completa y revierte.
═══════════════════════════════════════════════════════════════════════════════

REQUIERE la cola de migraciones s295 → s296 → s297 (`supabase/migration_proposals/`),
APLICADA en producción el 5-ago-2026. En un entorno donde falte, el script lo dice y sale
con código 2 en vez de aparentar cumplimiento.

FUERA DE ALCANCE, con dueño declarado en la matriz: `user_consent`, los exports a disco de
`scripts/review_logs.py`, y el extracto de recibos versionado en git.

Uso:
  python scripts/rgpd_retencion.py                 # dry-run (ejecuta y revierte)
  python scripts/rgpd_retencion.py --aplicar       # confirma
  python scripts/rgpd_retencion.py --aplicar --recibo evals/rgpd_2028.json

EJECUCION MANUAL por diseño. Programarlo exigiría una credencial durable con membresía en
`rgpd_retencion`, y hoy el rol solo se concede a `postgres` ⇒ un scheduler tendría que
guardar un `DATABASE_URL` de operador, **más potente** que el `service_role` que se evitó
tocar. Si algún día se programa, hace falta un rol runner LOGIN acotado: decisión aparte,
declarada en `docs/RGPD_RETENCION.md`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

ROL = "rgpd_retencion"
# Debe coincidir con el `interval '24 months'` de las politicas RLS. Si divergen, la base
# manda y este valor solo afectaria al mensaje: por eso no es configurable.
VENTANA_MESES = 24


class Objetivo(NamedTuple):
    tabla: str
    columna_fecha: str
    columna_id: str
    modo: str            # "nulificar" | "borrar"

    def sentencia(self) -> str:
        """SQL parametrizada por la fecha de corte, devolviendo el id de cada fila tocada."""
        if self.modo == "borrar":
            return (
                f"DELETE FROM public.{self.tabla} "
                f"WHERE {self.columna_fecha} < %s AND {self.columna_id} IS NOT NULL "
                f"RETURNING id"
            )
        # s296: NO se pone a NULL. Se ESTAMPA el seudónimo y luego se retira el
        # identificador, en la misma sentencia. Con NULL el corpus de un técnico quedaría
        # desperdigado —200 preguntas sueltas sin saber que son de la misma persona— y ese
        # agrupamiento es justo lo que da valor al histórico. El código se copia ANTES de
        # borrar la correspondencia (ver `destruir_correspondencias`), que es el orden que
        # hace la operación irreversible sin perder la agrupación.
        return (
            f"UPDATE public.{self.tabla} AS t "
            f"   SET seudonimo = p.seudonimo, {self.columna_id} = NULL "
            f"  FROM public.persona_seudonimo AS p "
            f" WHERE p.telegram_user_id = t.{self.columna_id} "
            f"   AND t.{self.columna_fecha} < %s AND t.{self.columna_id} IS NOT NULL "
            f"RETURNING t.id"
        )


# El ciclo COMPLETO, no solo la tabla padre: disociar `query_logs` y dejar el identificador
# en las hijas no anonimiza nada — se unen por `query_log_id`, y el ON DELETE CASCADE de sus
# FK solo actúa al BORRAR el padre.
OBJETIVOS = (
    Objetivo("query_logs", "created_at", "telegram_user_id", "nulificar"),
    Objetivo("feedback", "created_at", "telegram_user_id", "nulificar"),
    Objetivo("answer_feedback", "created_at", "telegram_user_id", "nulificar"),
    # Mapeo operativo mensaje->consulta: a 24 meses su valor analítico es CERO y carga
    # `telegram_chat_id` (== user_id en chat privado) ⇒ se borra, no se disocia.
    Objetivo("answer_messages", "created_at", "telegram_chat_id", "borrar"),
)


def corte(meses: int, ahora: datetime | None = None) -> datetime:
    """Fecha de corte en meses de CALENDARIO. `ahora` inyectable para testear.

    No se usa `timedelta(days=30 * meses)`: 24×30 = 720 días adelanta el corte ~10 días
    sobre los 24 meses que el técnico acepta en los términos. En una operación
    irreversible de cumplimiento, disociar antes de tiempo también es incumplir.
    """
    base = ahora or datetime.now(timezone.utc)
    total = (base.year * 12 + base.month - 1) - meses
    anio, mes = divmod(total, 12)
    mes += 1
    dia = min(base.day, _dias_del_mes(anio, mes))   # el 31 no existe en todos los meses
    return base.replace(year=anio, month=mes, day=dia)


def _dias_del_mes(anio: int, mes: int) -> int:
    siguiente = datetime(anio + (mes == 12), (mes % 12) + 1, 1, tzinfo=timezone.utc)
    return (siguiente - timedelta(days=1)).day


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
        help="Fichero JSON con constancia DURABLE de que filas se tocaron. "
             "Sin el, los ids solo salen por stdout, que no es un recibo.",
    )
    return parser


def ejecutar(limite: datetime, aplicar: bool, conexion=None) -> dict:
    """Pasada completa en UNA transacción, asumiendo el rol dedicado.

    `aplicar=False` ⇒ `ROLLBACK`: se ha ejecutado todo de verdad (privilegios y
    constraints evaluados sobre filas reales) y no queda rastro.
    """
    import psycopg2                                    # noqa: PLC0415 — dependencia de ops

    dsn = os.environ.get("DATABASE_URL")
    if not dsn and conexion is None:
        raise RuntimeError(
            "Falta DATABASE_URL. Este job NO usa la clave de servicio a proposito: el "
            "privilegio vive en el rol dedicado `rgpd_retencion`, que se asume desde una "
            "conexion de operador."
        )

    propia = conexion is None
    conexion = conexion or psycopg2.connect(dsn, connect_timeout=15)
    resultado: dict[str, dict] = {}
    try:
        with conexion.cursor() as cur:
            # Todo lo que sigue corre con los privilegios del rol acotado, no con los del
            # operador: el job no puede exceder su mandato ni por accidente.
            # `SET LOCAL` fuera de una transaccion es un NO-OP con WARNING, no un error:
            # en ese caso todo correria como el operador (`postgres`: owner + BYPASSRLS) y
            # ni la RLS ni los grants de columna gobernarian nada. El fallo mas grave
            # posible aqui, y silencioso. Por eso se COMPRUEBA, no se supone.
            cur.execute(f"SET LOCAL ROLE {ROL};")
            cur.execute("SET LOCAL statement_timeout = '120s';")
            cur.execute("SELECT current_user;")
            efectivo = cur.fetchone()[0]
            if efectivo != ROL:
                raise RuntimeError(
                    f"SET LOCAL ROLE no surtio efecto: current_user={efectivo!r}, se "
                    f"esperaba {ROL!r}. Sin el rol asumido este job correria con los "
                    f"privilegios del operador y la ventana de 24 meses NO estaria "
                    f"garantizada por la base. Abortado sin tocar nada."
                )
            # Antes de nada: EMITIR el código que falte. La emisión en `/accept` es
            # fail-open, así que puede haber gente sin código — y sin código el
            # `UPDATE ... FROM persona_seudonimo` no casaría sus filas: conservarían el
            # identificador PARA SIEMPRE y el recibo diría «0 tocadas» sin chirriar. La RLS
            # solo deja ver filas vencidas, así que esto alcanza exactamente a quien toca.
            for tabla, columna in (("query_logs", "telegram_user_id"),
                                   ("feedback", "telegram_user_id"),
                                   ("answer_feedback", "telegram_user_id")):
                cur.execute(
                    f"INSERT INTO public.persona_seudonimo (telegram_user_id) "
                    f"SELECT DISTINCT {columna} FROM public.{tabla} "
                    f" WHERE {columna} IS NOT NULL AND created_at < %s "
                    f"ON CONFLICT (telegram_user_id) DO NOTHING",
                    (limite,),
                )

            for obj in OBJETIVOS:
                cur.execute(obj.sentencia(), (limite,))
                ids = [str(fila[0]) for fila in cur.fetchall()]
                resultado[obj.tabla] = {"modo": obj.modo, "tocadas": len(ids), "ids": ids}

            # EL PUNTO DE NO RETORNO, y va el ÚLTIMO a propósito: mientras la
            # correspondencia existe, todo lo anterior es reversible. Se borra solo la de
            # quien ya no tiene NINGUNA fila identificada — si a alguien le quedan
            # consultas recientes, su código sigue haciendo falta para estamparlas cuando
            # les toque. Y va dentro de la misma transacción: o se estampa el código y se
            # destruye el vínculo, o no pasa ninguna de las dos cosas.
            # La condición NO se consulta a mano: la política de ventana solo enseña filas
            # vencidas a este rol, así que un `NOT EXISTS` desde aquí daría verdadero
            # también para quien tiene filas RECIENTES identificadas — y destruiría su
            # vínculo antes de tiempo, partiendo su corpus en dos códigos. La función corre
            # con visibilidad completa y devuelve solo un booleano.
            cur.execute(
                "DELETE FROM public.persona_seudonimo p "
                " WHERE NOT public.rgpd_quedan_identificados(p.telegram_user_id) "
                "RETURNING telegram_user_id"
            )
            destruidas = [str(fila[0]) for fila in cur.fetchall()]
            resultado["persona_seudonimo"] = {
                "modo": "destruir_vinculo",
                "tocadas": len(destruidas),
                "ids": [],          # el id ES el identificador de la persona: NO se registra
            }
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
    return resultado


def _diagnosticar(error: Exception) -> str:
    """Traduce el fallo al hueco real, en vez de dejar un traceback críptico."""
    texto = str(error)
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
            "(punto 4 de la propuesta)."
        )
    return f"Fallo no previsto: {type(error).__name__}: {texto.strip()[:200]}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = _construir_parser().parse_args()

    limite = corte(VENTANA_MESES)
    print(f"retencion: {VENTANA_MESES} meses de calendario · corte: {limite.isoformat()}")
    print("   (la ventana REAL la impone la politica RLS del rol; esto es el mismo valor)")
    print(f"rol: {ROL} (via SET LOCAL ROLE; NO se usa la clave del bot)")
    print(f"modo: {'APLICAR (commit)' if args.aplicar else 'dry-run (ejecuta y revierte)'}\n")

    try:
        resultado = ejecutar(limite, args.aplicar)
    except Exception as e:                                  # noqa: BLE001
        print("NO PUEDE CUMPLIR LA RETENCION -- no se ha escrito NADA (transaccion revertida).")
        print("   " + _diagnosticar(e))
        print(
            "\nUn job de retencion que no puede ejecutarse APARENTA cumplimiento, que es\n"
            "peor que no tenerlo: por eso esto es exit 2 y no un aviso de refilon."
        )
        return 2

    for tabla, fila in resultado.items():
        print(f"  {tabla:19s} {fila['modo']:17s} tocadas={fila['tocadas']:5d}")
    # Los ids salen por stdout ANTES que nada mas: si el recibo en fichero fallase, la traza
    # de una operacion irreversible no puede depender de que `open()` funcione.
    for tabla, fila in resultado.items():
        if fila["ids"]:
            print(f"    ids {tabla}: {', '.join(fila['ids'])}")

    print(
        "\nALCANCE Y LIMITE. Cubre el ciclo de las 4 tablas de arriba, en UNA transaccion.\n"
        "Aun asi es SEUDONIMIZACION, no anonimizacion: el texto libre (pregunta,\n"
        "transcripcion, comentario del voto) puede identificar, y eso no lo arregla quitar\n"
        "columnas. Fuera de alcance, con dueno declarado en docs/RGPD_RETENCION.md:\n"
        "`user_consent`, los exports a disco de scripts/review_logs.py, y el extracto de\n"
        "recibos versionado en git.\n"
        "La ventana de 24 meses la impone la POLITICA RLS del rol, no este script."
    )

    if args.recibo and any(f["ids"] for f in resultado.values()):
        with open(args.recibo, "w", encoding="utf-8") as fh:
            json.dump(
                {"corte": limite.isoformat(), "meses": VENTANA_MESES,
                 "aplicado": args.aplicar, "tablas": resultado},
                fh, ensure_ascii=False, indent=2,
            )
        print(f"\nrecibo durable escrito en {args.recibo}")

    print("\n" + json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
