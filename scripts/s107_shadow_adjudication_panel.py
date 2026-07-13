#!/usr/bin/env python3
"""Local no-cache panel for source-visible R2 shadow adjudication.

Operations launches the process. It projects only ``query, created_at`` from
``query_logs``, joins redacted events in memory, closes the database connection,
and binds only to localhost. The browser receives raw query/manual text with
``Cache-Control: no-store``; the only file written is the redacted label receipt.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.s107_shadow_adjudication_join import (
    CRITICAL_REASONS,
    AdjudicationCase,
    JoinResult,
    build_redacted_receipt,
    hmac_sha256_utf8_exact,
    join_shadow_events_in_memory,
)


def _load_events(path: Path) -> list[dict]:
    events: list[dict] = []
    marker = "structural_neighbor_shadow "
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if marker in line:
            line = line.split(marker, 1)[1]
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid event JSON on line {line_number}") from exc
        if payload.get("schema") == "structural_neighbor_shadow_event_v1":
            events.append(payload)
    if not events:
        raise ValueError("no structural-neighbor events found")
    return events


def _load_minimum_projections(database_url: str, events: list[dict]) -> tuple[list[dict], list[dict]]:
    selected_ids = sorted(
        {
            chunk_id
            for event in events
            for chunk_id in (event.get("selected_ids") or [])
            if isinstance(chunk_id, str) and chunk_id
        }
    )
    connection = psycopg2.connect(
        database_url,
        connect_timeout=20,
        application_name="s107_shadow_adjudication_projection",
    )
    connection.set_session(readonly=True, autocommit=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute(
                "SELECT query, created_at FROM public.query_logs ORDER BY created_at, id"
            )
            query_rows = [
                {"query": row[0], "created_at": row[1].isoformat() if row[1] else None}
                for row in cursor.fetchall()
            ]
            if selected_ids:
                cursor.execute(
                    """
                    SELECT id, content, source_file, page_number, section_title,
                           document_id, extraction_sha256, language
                      FROM public.chunks_v2
                     WHERE id = ANY(%s::uuid[])
                    """,
                    (selected_ids,),
                )
                chunk_rows = [
                    {
                        "id": str(row[0]),
                        "content": row[1],
                        "source_file": row[2],
                        "page_number": row[3],
                        "section_title": row[4],
                        "document_id": str(row[5]) if row[5] else None,
                        "extraction_sha256": row[6],
                        "language": row[7],
                    }
                    for row in cursor.fetchall()
                ]
            else:
                chunk_rows = []
        connection.rollback()
    finally:
        connection.close()
    return query_rows, chunk_rows


def _synthetic_result() -> JoinResult:
    secret = "s107-synthetic-panel-secret-longer-than-32-chars"
    query = "¿Qué tensión admite el lazo?"
    chunk_id = "00000000-0000-0000-0000-000000000001"
    event = {
        "schema": "structural_neighbor_shadow_event_v1",
        "event_id": "synthetic-event-1",
        "query_hmac_sha256": hmac_sha256_utf8_exact(secret, query),
        "sampling_hmac_key_version": "v1",
        "selected_ids": [chunk_id],
    }
    return join_shadow_events_in_memory(
        [event],
        query_rows=[{"query": query, "created_at": "2026-07-13T00:00:00Z"}],
        chunk_rows=[
            {
                "id": chunk_id,
                "content": "Tensión nominal del lazo: 24 Vcc.",
                "source_file": "synthetic-manual.pdf",
                "page_number": 7,
                "section_title": "Lazo",
                "document_id": "synthetic-doc",
                "extraction_sha256": "a" * 64,
                "language": "es",
            }
        ],
        hmac_secret=secret,
        hmac_key_version="v1",
    )


class _PanelState:
    def __init__(self, result: JoinResult, output: Path):
        if result.promotion_blocked:
            raise RuntimeError("join blockers must be resolved before manual adjudication")
        self.result = result
        self.output = output
        self.decisions: dict[str, dict] = {}
        self.lock = threading.Lock()

    def next_case(self) -> AdjudicationCase | None:
        return next(
            (case for case in self.result.cases if case.event_id not in self.decisions),
            None,
        )


def _handler_factory(state: _PanelState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "S107LocalAdjudication/1"

        def log_message(self, _format: str, *_args) -> None:
            return

        def _send(self, status: int, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/":
                self._send(404, "Not found")
                return
            with state.lock:
                case = state.next_case()
            if case is None:
                self._send(200, "<h1>Adjudicación terminada</h1><p>El recibo redacted está escrito.</p>")
                return
            anchor_html = []
            reason_options = "".join(
                f'<option value="{html.escape(reason)}">{html.escape(reason)}</option>'
                for reason in sorted(CRITICAL_REASONS)
            )
            for index, anchor in enumerate(case.anchors):
                source = f"{anchor.source_file or 'unknown'} · p. {anchor.page_number or '?'}"
                anchor_html.append(
                    f"<fieldset><legend>{html.escape(source)}</legend>"
                    f"<pre>{html.escape(anchor.content)}</pre>"
                    f'<label><input required type="radio" name="relevant_{index}" value="yes">relevante</label>'
                    f'<label><input required type="radio" name="relevant_{index}" value="no">no relevante</label>'
                    f'<select name="reason_{index}"><option value="">sin falso positivo crítico</option>{reason_options}</select>'
                    f'<input type="hidden" name="anchor_{index}" value="{html.escape(anchor.id)}"></fieldset>'
                )
            body = (
                "<h1>R2 source-visible review</h1>"
                f"<p>Consulta única; ocurrencias: {case.query_occurrences}</p>"
                f"<blockquote>{html.escape(case.query)}</blockquote>"
                '<form method="post" action="/label">'
                f'<input type="hidden" name="event_id" value="{html.escape(case.event_id)}">'
                + "".join(anchor_html)
                + '<button type="submit">Guardar etiqueta redacted</button></form>'
            )
            self._send(200, body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/label":
                self._send(404, "Not found")
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 32_768:
                self._send(400, "Invalid form")
                return
            form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            event_id = (form.get("event_id") or [""])[0]
            case = next((item for item in state.result.cases if item.event_id == event_id), None)
            if case is None:
                self._send(400, "Unknown event")
                return
            labels = []
            try:
                for index, anchor in enumerate(case.anchors):
                    if (form.get(f"anchor_{index}") or [""])[0] != anchor.id:
                        raise ValueError("anchor identity mismatch")
                    answer = (form.get(f"relevant_{index}") or [""])[0]
                    if answer not in {"yes", "no"}:
                        raise ValueError("missing relevance label")
                    reason = (form.get(f"reason_{index}") or [""])[0] or None
                    if reason is not None and reason not in CRITICAL_REASONS:
                        raise ValueError("invalid critical reason")
                    if answer == "yes" and reason is not None:
                        raise ValueError("a relevant anchor cannot have a critical reason")
                    labels.append(
                        {"id": anchor.id, "relevant": answer == "yes", "critical_reason": reason}
                    )
                decision = {"event_id": event_id, "anchors": labels}
                with state.lock:
                    state.decisions[event_id] = decision
                    if state.next_case() is None:
                        receipt = build_redacted_receipt(
                            state.result, list(state.decisions.values())
                        )
                        state.output.parent.mkdir(parents=True, exist_ok=True)
                        state.output.write_text(
                            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
            except (TypeError, ValueError) as exc:
                self._send(400, html.escape(str(exc)))
                return
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--synthetic-smoke", action="store_true")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("panel may bind only to localhost")
    if not 1024 <= args.port <= 65535:
        raise SystemExit("port must be between 1024 and 65535")

    if args.synthetic_smoke:
        result = _synthetic_result()
        output = args.output or ROOT / "tmp/s107_shadow_panel_synthetic_receipt.json"
    else:
        if args.events is None or args.output is None:
            raise SystemExit("--events and --output are required")
        load_dotenv(ROOT / ".env")
        database_url = os.environ.get("DATABASE_URL", "")
        secret = os.environ.get("STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY", "")
        key_version = os.environ.get("STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION", "")
        if not database_url or len(secret) < 32 or not key_version:
            raise SystemExit("database URL and deployment HMAC secret/version are required")
        events = _load_events(args.events)
        query_rows, chunk_rows = _load_minimum_projections(database_url, events)
        result = join_shadow_events_in_memory(
            events,
            query_rows=query_rows,
            chunk_rows=chunk_rows,
            hmac_secret=secret,
            hmac_key_version=key_version,
        )
        output = args.output

    state = _PanelState(result, output.resolve())
    server = ThreadingHTTPServer((args.host, args.port), _handler_factory(state))
    print(
        json.dumps(
            {
                "status": "local_panel_ready",
                "url": f"http://{args.host}:{args.port}/",
                "joinable_cases": len(result.cases),
                "promotion_blocked": result.promotion_blocked,
                "output": str(output.resolve()),
                "raw_material_persisted": False,
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
