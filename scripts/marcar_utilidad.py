#!/usr/bin/env python3
"""marcar_utilidad.py — el camino de escritura de la marca de utilidad (s301).

La marca (`utilidad`: corrigio | gold | corpus | ninguna) es el dato en que se apoyaría
un bonus por feedback valioso. Por diseño (s296/s297) el BOT no puede escribirla — ni
INSERT ni UPDATE de esas columnas para `service_role` — pero hasta s301 NADIE podía:
no existía herramienta, solo SQL a mano. Este script es el camino del OPERADOR.

Cómo: conexión DIRECTA (`DATABASE_URL`, el patrón de `rgpd_retencion.py`) — el operador
es `postgres`, dueño de las tablas; los grants de columna acotan al bot, no a él. La
coherencia la impone la BASE (CHECK `(utilidad IS NULL) = (utilidad_revisada_at IS NULL)`):
este script siempre estampa marca + fecha juntas.

Uso:
  python scripts/marcar_utilidad.py                     # lista lo pendiente de revisar
  python scripts/marcar_utilidad.py --marcar answer_feedback <id> corrigio
  python scripts/marcar_utilidad.py --marcar feedback <id> ninguna

La taxonomía es la del CHECK de la base (s296): `corrigio` (destapó un fallo que se
corrigió) · `gold` (produjo un caso de eval) · `corpus` (señaló contenido que faltaba) ·
`ninguna` (revisado sin consecuencia). NULL = sin revisar, y NO es lo mismo que ninguna.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

TABLAS = ("answer_feedback", "feedback")
UTILIDADES = ("corrigio", "gold", "corpus", "ninguna")


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--marcar", nargs=3, metavar=("TABLA", "ID", "UTILIDAD"), default=None,
        help=f"estampa la marca: TABLA∈{TABLAS}, UTILIDAD∈{UTILIDADES}",
    )
    return parser


def _conectar():
    import psycopg2                                    # noqa: PLC0415 — dependencia de ops

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "Falta DATABASE_URL: la marca se escribe por conexión de OPERADOR — el bot "
            "no puede escribirla por diseño, y este script no usa su clave."
        )
    return psycopg2.connect(dsn, connect_timeout=15)


def listar(conexion) -> int:
    """Lo pendiente: 👎 y feedback espontáneo sin marca. El operador VE la prosa —
    es quien decide si llevó a algo; la prosa no sale de la pantalla."""
    pendientes = 0
    with conexion.cursor() as cur:
        cur.execute(
            "SELECT id, created_at::date, verdict, reason_class, left(comment, 200) "
            "  FROM public.answer_feedback WHERE utilidad IS NULL "
            "   AND (verdict = 'down' OR comment IS NOT NULL) "
            " ORDER BY created_at"
        )
        filas = cur.fetchall()
        print(f"— answer_feedback sin revisar: {len(filas)}")
        for fila in filas:
            id_, fecha, verdict, reason, comment = fila
            print(f"  {id_}  {fecha}  {verdict:<4} motivo={reason or '-'} "
                  f"comentario={comment or '-'}")
        pendientes += len(filas)

        cur.execute(
            "SELECT id, created_at::date, left(feedback_text, 200) "
            "  FROM public.feedback WHERE utilidad IS NULL ORDER BY created_at"
        )
        filas = cur.fetchall()
        print(f"— feedback (canal espontáneo) sin revisar: {len(filas)}")
        for id_, fecha, texto in filas:
            print(f"  {id_}  {fecha}  {texto or '-'}")
        pendientes += len(filas)
    conexion.rollback()                                # solo lectura: sin rastro
    print(f"\npendientes: {pendientes}")
    print("marcar: python scripts/marcar_utilidad.py --marcar <tabla> <id> <utilidad>")
    return 0


def marcar(conexion, tabla: str, fila_id: str, utilidad: str) -> int:
    if tabla not in TABLAS:
        raise SystemExit(f"tabla {tabla!r} no admitida (∈ {TABLAS})")
    if utilidad not in UTILIDADES:
        raise SystemExit(f"utilidad {utilidad!r} fuera de la taxonomía (∈ {UTILIDADES})")
    with conexion.cursor() as cur:
        # Marca + fecha JUNTAS (el CHECK de coherencia de la base lo exige) y solo si
        # estaba sin revisar: re-marcar pide decisión explícita, no un tropiezo.
        cur.execute(
            f"UPDATE public.{tabla} "
            f"   SET utilidad = %s, utilidad_revisada_at = now() "
            f" WHERE id = %s AND utilidad IS NULL RETURNING id",
            (utilidad, fila_id),
        )
        tocada = cur.fetchone()
    if tocada is None:
        conexion.rollback()
        raise SystemExit(
            f"no se marcó nada: id {fila_id} no existe en {tabla} o YA estaba revisado "
            f"(re-marcar exige ponerlo a NULL antes, a conciencia)."
        )
    conexion.commit()
    print(f"marcado: {tabla} {fila_id} → {utilidad}")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = _construir_parser().parse_args()
    conexion = _conectar()
    try:
        if args.marcar:
            tabla, fila_id, utilidad = args.marcar
            return marcar(conexion, tabla, fila_id, utilidad)
        return listar(conexion)
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())
