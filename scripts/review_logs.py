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

    if "display_name" in df.columns:
        print("\nTop users:")
        top = (
            df.assign(name=df["display_name"].fillna(df["telegram_user_id"].astype(str)))
            .groupby("name")
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

    logger.info("Fetching user_consent...")
    consent = _fetch_table(
        "user_consent",
        select="telegram_user_id,display_name,terms_version,accepted_at",
        order="accepted_at.desc",
    )
    logger.info(f"  → {len(consent)} consent rows")

    queries_df = pd.DataFrame(queries)
    feedback_df = pd.DataFrame(feedback)
    consent_df = pd.DataFrame(consent)

    if queries_df.empty:
        print("No query rows in selected range.")
        return

    # Join display_name from user_consent
    if not consent_df.empty:
        names = consent_df[["telegram_user_id", "display_name"]].drop_duplicates(
            subset=["telegram_user_id"], keep="first"
        )
        queries_df = queries_df.merge(names, on="telegram_user_id", how="left")
    else:
        queries_df["display_name"] = None

    # Attach feedback
    queries_df = _match_feedback_to_queries(queries_df, feedback_df)

    # Reorder columns for review readability
    front = [
        "created_at", "display_name", "telegram_user_id", "source", "query",
        "transcription", "response", "product_models", "category",
        "chunks_used", "response_length", "response_time_ms",
        "bot_version", "feedback_text",
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
