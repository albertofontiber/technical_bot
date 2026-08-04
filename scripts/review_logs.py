"""
Export Telegram bot query logs + feedback for eval curation.

Pulls rows from `query_logs`, `feedback`, and `user_consent` in Supabase,
joins them, and writes a single CSV/XLSX file ready to review in Excel.
Also prints a short summary (counts by source, by bot_version, top users).

Usage:
    python -m scripts.review_logs                          # last 30 days, CSV
    python -m scripts.review_logs --since 2026-04-27       # from a specific date
    python -m scripts.review_logs --format xlsx            # write Excel
    python -m scripts.review_logs --user-id 12345          # filter to one user
    python -m scripts.review_logs --version abc1234        # filter to one bot_version
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}


def _fetch_table(
    table: str,
    *,
    since_iso: str | None = None,
    extra_filters: dict[str, str] | None = None,
    select: str = "*",
    order: str = "created_at.desc",
) -> list[dict]:
    """Fetch rows from a Supabase table, paginating with offset/limit."""
    rows: list[dict] = []
    page_size = 1000
    offset = 0

    while True:
        params: dict[str, str] = {"select": select, "order": order, "limit": str(page_size), "offset": str(offset)}
        if since_iso:
            params["created_at"] = f"gte.{since_iso}"
        if extra_filters:
            for k, v in extra_filters.items():
                params[k] = v

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers=_HEADERS,
                params=params,
            )
            resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def _attach_tap_verdicts(
    queries_df: pd.DataFrame,
    answer_feedback_df: pd.DataFrame,
) -> pd.DataFrame:
    """Attach 👍/👎 tap verdicts (answer_feedback, s286) by EXACT FK join on
    query_logs.id — unlike the free-text `feedback` table, which predates the
    FK and keeps the fuzzy startswith match below. One verdict per (query,
    user) is guaranteed by the table's UNIQUE pair; a multi-user query joins
    as a comma-separated list."""
    queries_df = queries_df.copy()
    if answer_feedback_df.empty or "id" not in queries_df.columns:
        queries_df["tap_verdict"] = None
        return queries_df

    verdicts = (
        answer_feedback_df.groupby("query_log_id")["verdict"]
        .apply(",".join)
        .rename("tap_verdict")
    )
    queries_df = queries_df.merge(
        verdicts, left_on="id", right_index=True, how="left"
    )
    return queries_df


def _match_feedback_to_queries(
    queries_df: pd.DataFrame,
    feedback_df: pd.DataFrame,
) -> pd.DataFrame:
    """Attach feedback to its matching query row by (user_id, previous_query) match.

    Best-effort: feedback rows store the first 500 chars of the query they
    correct. We match against query_logs by (telegram_user_id, query startswith
    previous_query). On ambiguity, keep the most recent matching query.
    """
    if feedback_df.empty:
        queries_df["feedback_text"] = None
        return queries_df

    queries_df = queries_df.copy()
    queries_df["feedback_text"] = None

    for _, fb in feedback_df.iterrows():
        prev_q = fb.get("previous_query") or ""
        if not prev_q:
            continue
        mask = (
            (queries_df["telegram_user_id"] == fb["telegram_user_id"])
            & (queries_df["query"].str.startswith(prev_q[:200], na=False))
        )
        candidates = queries_df[mask]
        if candidates.empty:
            continue
        # Pick the most recent matching query (queries_df is sorted desc by created_at)
        idx = candidates.index[0]
        queries_df.at[idx, "feedback_text"] = fb["feedback_text"]

    return queries_df


def _seudonimizar(df: pd.DataFrame, correspondencias: dict) -> pd.DataFrame:
    """Cambia identificadores por el código estable ANTES de que nada llegue al disco.

    Se hace en un único punto, y no confiando en que cada sitio se acuerde de excluir las
    columnas: lo que no se puede olvidar es lo que ya no está en la tabla.

    DOS FUENTES, y hacen falta las dos:
      · `query_logs.seudonimo` — solo tiene valor en filas YA disociadas por la retención;
        ahí el identificador ya no existe, así que es la única fuente posible.
      · `persona_seudonimo` — para todo lo demás, que es TODO hasta 2028.

    Usar solo la primera (como hacía la versión anterior) dejaba a todos los técnicos
    colapsados bajo el mismo literal «(sin código)» y destruía la agrupación justo en el
    periodo en que hace falta: el de ahora. No se veía porque la columna existe y el
    código «funcionaba» — el fallo estaba en de dónde venía el dato.
    """
    if df.empty:
        return df
    salida = df.copy()
    if "seudonimo" not in salida.columns:
        salida["seudonimo"] = None

    if "telegram_user_id" in salida.columns:
        desde_tabla = salida["telegram_user_id"].map(
            lambda uid: correspondencias.get(uid) if pd.notna(uid) else None
        )
        # La columna estampada manda: en una fila disociada es lo único que queda.
        salida["seudonimo"] = salida["seudonimo"].fillna(desde_tabla)

    salida["seudonimo"] = salida["seudonimo"].fillna("(sin código)")
    return salida.drop(columns=[c for c in ("telegram_user_id", "display_name")
                                if c in salida.columns])


def _print_summary(df: pd.DataFrame) -> None:
    if df.empty:
        print("\n(no rows in selected range)")
        return

    print(f"\n=== Summary ({len(df)} queries) ===")
    print(f"Date range: {df['created_at'].min()} → {df['created_at'].max()}")

    if "source" in df.columns:
        print("\nBy source:")
        print(df["source"].value_counts().to_string())

    if "bot_version" in df.columns:
        print("\nBy bot_version:")
        print(df["bot_version"].fillna("(missing)").value_counts().to_string())

    if "feedback_text" in df.columns:
        with_fb = df["feedback_text"].notna().sum()
        print(f"\nQueries with feedback: {with_fb} / {len(df)} ({100*with_fb/len(df):.1f}%)")

    if "seudonimo" in df.columns:
        # Se agrupa por el código, no por el nombre: para saber «cuánta actividad hay y
        # cómo se reparte» no hace falta saber de quién es cada bloque.
        print("\nActividad por persona (seudónimo):")
        top = (
            df.groupby(df["seudonimo"].fillna("(sin código)"))
            .size()
            .sort_values(ascending=False)
            .head(10)
        )
        print(top.to_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO date (YYYY-MM-DD). Default: 30 days ago.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path. Default: data/eval/logs_export_<timestamp>.<format>",
    )
    parser.add_argument("--format", choices=["csv", "xlsx"], default="csv")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--version", type=str, default=None, help="Filter by bot_version")
    args = parser.parse_args()

    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=30)
    since_iso = since_dt.isoformat()

    logger.info(f"Fetching query_logs since {since_iso}...")
    extra: dict[str, str] = {}
    if args.user_id is not None:
        extra["telegram_user_id"] = f"eq.{args.user_id}"
    if args.version:
        extra["bot_version"] = f"eq.{args.version}"
    queries = _fetch_table("query_logs", since_iso=since_iso, extra_filters=extra or None)
    logger.info(f"  → {len(queries)} query rows")

    logger.info(f"Fetching feedback since {since_iso}...")
    fb_extra = {"telegram_user_id": f"eq.{args.user_id}"} if args.user_id is not None else None
    feedback = _fetch_table("feedback", since_iso=since_iso, extra_filters=fb_extra)
    logger.info(f"  → {len(feedback)} feedback rows")

    logger.info(f"Fetching answer_feedback since {since_iso}...")
    answer_feedback = _fetch_table(
        "answer_feedback", since_iso=since_iso, extra_filters=fb_extra
    )
    logger.info(f"  → {len(answer_feedback)} answer_feedback rows")

    # s296: ya NO se trae `user_consent`. Se traia solo para pegar el nombre del tecnico
    # al export -- exactamente el dato que ahora no debe salir. Traer dato personal para
    # despues descartarlo es peor que no traerlo: basta un descuido para que se cuele.
    queries_df = pd.DataFrame(queries)
    feedback_df = pd.DataFrame(feedback)

    if queries_df.empty:
        print("No query rows in selected range.")
        return

    # Attach feedback
    queries_df = _match_feedback_to_queries(queries_df, feedback_df)
    queries_df = _attach_tap_verdicts(queries_df, pd.DataFrame(answer_feedback))

    # s296 — EL FICHERO NO SALE CON IDENTIFICADORES. Este export acaba en el disco de
    # alguien: fuera de la base, fuera de la matriz de retención y fuera del alcance de una
    # petición de borrado. Se sustituyen `telegram_user_id` y `display_name` por el
    # SEUDÓNIMO estable, que agrupa igual de bien («estas 40 preguntas son de la misma
    # persona») sin decir quién es. Es el mismo código que el job estampa a los 24 meses,
    # así que un export de hoy y la base de dentro de tres años siguen cruzándose.
    # La correspondencia se trae de su tabla: es la unica fuente para las filas que aun
    # NO han vencido, que hoy son todas.
    correspondencias = {
        fila["telegram_user_id"]: fila["seudonimo"]
        for fila in _fetch_table("persona_seudonimo",
                                 select="telegram_user_id,seudonimo", order="created_at")
    }
    logger.info(f"  -> {len(correspondencias)} seudonimos")
    queries_df = _seudonimizar(queries_df, correspondencias)

    # Reorder columns for review readability
    front = [
        "created_at", "seudonimo", "source", "query",
        "transcription", "response", "product_models", "category",
        "chunks_used", "response_length", "response_time_ms",
        "bot_version", "feedback_text", "tap_verdict",
    ]
    cols = [c for c in front if c in queries_df.columns] + [
        c for c in queries_df.columns if c not in front
    ]
    queries_df = queries_df[cols]

    # Resolve output path
    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(__file__).parent.parent / "data" / "eval"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"logs_export_{ts}.{args.format}"

    if args.format == "csv":
        queries_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        queries_df.to_excel(out_path, index=False, sheet_name="query_logs")

    logger.info(f"Wrote {out_path}")
    _print_summary(queries_df)


if __name__ == "__main__":
    main()
