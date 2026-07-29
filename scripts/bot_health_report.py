"""
Bot health digest (s286 telemetría — canonical health output).

Reads query_logs via the Supabase REST API and prints the health summary the
SQL views (bot_health_daily/semanal) expose, PLUS the env-driven dogfooding
segmentation that a SQL view cannot carry: INTERNAL_TELEGRAM_IDS (csv of
Telegram user ids, e.g. Alberto's) are excluded from adoption metrics and
reported separately. The views stay unsegmented on purpose — single source
for the exclusion list (s286 dúo r2).

Declared metric semantics (s286 brief v2):
  · "consultas RAG respondidas" — NOT total adoption: pre-pipeline routes
    (greeting/catalog/clarify/F1-direct) don't log today; category='direct'
    rows are excluded so the metric stays honest if BOT_DIRECT_LOGGING ever
    turns on.
  · % no-info is a HEURISTIC (prefix family over free LLM prose).
  · latency percentiles are PIPELINE latency (measured before Telegram send).

Usage:
    python -m scripts.bot_health_report                # last 7 days
    python -m scripts.bot_health_report --days 30
    python -m scripts.bot_health_report --all          # full history
"""

import argparse
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}

_NO_INFO_PREFIXES = ("no tengo información", "no dispongo")
_TRANSPORT_FALLBACK_PREFIX = "No he podido generar una respuesta completa"


def internal_ids() -> set[int]:
    """Parse INTERNAL_TELEGRAM_IDS (csv). Non-numeric entries are ignored."""
    raw = os.getenv("INTERNAL_TELEGRAM_IDS", "")
    ids: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            ids.add(int(token))
    return ids


def fetch_rows(since_iso: str | None) -> list[dict]:
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    select = (
        "telegram_user_id,source,category,response,response_time_ms,"
        "bot_version,created_at"
    )
    while True:
        params = {
            "select": select,
            "order": "created_at.desc",
            "limit": str(page_size),
            "offset": str(offset),
        }
        if since_iso:
            params["created_at"] = f"gte.{since_iso}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/query_logs",
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


def is_rag_query(row: dict) -> bool:
    return row.get("source") != "error" and row.get("category") != "direct"


def is_no_info(row: dict) -> bool:
    response = (row.get("response") or "").lower()
    return response.startswith(_NO_INFO_PREFIXES)


def summarize(rows: list[dict], internal: set[int]) -> dict:
    """Compute the digest over already-fetched rows (pure; unit-tested)."""
    rag = [r for r in rows if is_rag_query(r)]
    rag_external = [r for r in rag if r.get("telegram_user_id") not in internal]
    rag_internal_n = len(rag) - len(rag_external)
    latencies = sorted(
        r["response_time_ms"] for r in rag if r.get("response_time_ms") is not None
    )
    external_users = {
        r.get("telegram_user_id") for r in rag_external if r.get("telegram_user_id")
    }
    by_version: dict[str, int] = {}
    for r in rag:
        version = r.get("bot_version") or "(sin versión)"
        by_version[version] = by_version.get(version, 0) + 1
    percentile = (
        lambda q: statistics.quantiles(latencies, n=100)[q - 1]
        if len(latencies) >= 2
        else (latencies[0] if latencies else None)
    )
    return {
        "consultas_rag": len(rag),
        "consultas_rag_tecnicos": len(rag_external),
        "consultas_rag_internas": rag_internal_n,
        "tecnicos_unicos": len(external_users),
        "latencia_pipeline_p50_ms": percentile(50),
        "latencia_pipeline_p95_ms": percentile(95),
        "latencia_n": len(latencies),
        "no_info_heuristica": sum(1 for r in rag if is_no_info(r)),
        "errores_transporte": sum(
            1
            for r in rows
            if (r.get("response") or "").startswith(_TRANSPORT_FALLBACK_PREFIX)
        ),
        "filas_error": sum(1 for r in rows if r.get("source") == "error"),
        "por_bot_version": by_version,
    }


def print_digest(summary: dict, *, label: str, internal: set[int]) -> None:
    n = summary["consultas_rag"]
    print(f"\n=== Salud del bot — {label} ===")
    print(
        f"Consultas RAG respondidas: {n} "
        f"(técnicos: {summary['consultas_rag_tecnicos']} · "
        f"internas/dogfooding: {summary['consultas_rag_internas']})"
    )
    print(
        f"Técnicos únicos (excl. {len(internal)} ids internos): "
        f"{summary['tecnicos_unicos']}"
    )
    p50, p95 = summary["latencia_pipeline_p50_ms"], summary["latencia_pipeline_p95_ms"]
    p50_s = f"{p50:.0f}" if p50 is not None else "—"
    p95_s = f"{p95:.0f}" if p95 is not None else "—"
    print(
        f"Latencia de PIPELINE (pre-envío Telegram) p50/p95: {p50_s}/{p95_s} ms "
        f"(n={summary['latencia_n']}"
        + (" — n bajo, ruidoso" if summary["latencia_n"] < 30 else "")
        + ")"
    )
    print(
        f"No-info (HEURÍSTICA de prefijos): {summary['no_info_heuristica']}/{n}"
        + (f" ({summary['no_info_heuristica'] / n:.0%})" if n else "")
    )
    print(f"Errores de transporte (fallback fijo): {summary['errores_transporte']}")
    print(f"Filas source='error' (BOT_ERROR_LOGGING): {summary['filas_error']}")
    if summary["por_bot_version"]:
        print("Por bot_version:")
        for version, count in sorted(
            summary["por_bot_version"].items(), key=lambda kv: -kv[1]
        ):
            print(f"  {version}: {count}")
    print(
        "\nNota: los turnos pre-pipeline (saludo/catálogo/clarify/F1-directo) NO "
        "loguean hoy — esto NO es adopción total."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Digest de salud del bot (s286)")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--all", action="store_true", help="histórico completo")
    args = parser.parse_args()

    if args.all:
        since_iso, label = None, "histórico completo"
    else:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        since_iso, label = since.isoformat(), f"últimos {args.days} días"

    internal = internal_ids()
    rows = fetch_rows(since_iso)
    print_digest(summarize(rows, internal), label=label, internal=internal)


if __name__ == "__main__":
    main()
