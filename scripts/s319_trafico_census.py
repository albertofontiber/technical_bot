# -*- coding: utf-8 -*-
"""s319 — Censo de PRIMER TRÁFICO real (punto 4 del paquete de apertura).

Construido HOY contra datos casi vacíos para que el día que haya DGs externos
sea apretar un botón. Lee `query_logs` (+ join manual a `answer_feedback` —
dúo r17, Sol M-👎: los 👎 con texto viven ahí, no en query_logs) y produce la
distribución que los 39 golds no pueden dar: qué preguntan, por qué ruta sale,
cuánto tarda por etapa, qué decide el intent, y qué valora mal la gente.

REGLA DE REDACCIÓN (para que «recibo sin PII» sea VERDAD, no prosa):
- `telegram_user_id`/`seudonimo` JAMÁS cruzan al recibo: uid → sha256[:12]
  (agrupable, no identificable sin la BD).
- Los TEXTOS (query/response/comment) NO van al recibo por defecto — solo
  longitudes, rutas, timings, decisiones y agregados. `--con-texto` los vuelca
  a un fichero LOCAL aparte en data-root (fuera del repo), comentarios
  truncados a 200 chars, para la sesión de análisis con Alberto.

Uso:
    python scripts/s319_trafico_census.py --desde 2026-08-01
    python scripts/s319_trafico_census.py --desde 2026-08-01 --con-texto --data-root "..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def _uid_hash(valor) -> str:
    return hashlib.sha256(str(valor or "").encode()).hexdigest()[:12]


def _paginado(client, tabla: str, params: dict) -> list[dict]:
    filas, off = [], 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                       params={**params, "offset": str(off), "limit": "1000"})
        r.raise_for_status()
        lote = r.json()
        filas.extend(lote)
        if len(lote) < 1000:
            return filas
        off += 1000


def _mediana(xs: list) -> float | None:
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return xs[len(xs) // 2] if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", required=True, help="fecha ISO (created_at >=)")
    ap.add_argument("--con-texto", action="store_true")
    ap.add_argument("--data-root", default=None,
                    help="requerido con --con-texto (el texto va FUERA del repo)")
    args = ap.parse_args()
    if args.con_texto and not args.data_root:
        print("ABORT: --con-texto exige --data-root (los textos no van al repo)")
        return 1

    with abierto(timeout=30.0) as client:
        logs = _paginado(client, "query_logs", {
            "select": ("id,created_at,route,source,response_time_ms,"
                       "response_length,chunks_used,rag_trace,telegram_user_id,"
                       "query,category,product_models"),
            "created_at": f"gte.{args.desde}", "order": "created_at.asc"})
        fb = _paginado(client, "answer_feedback", {
            "select": ("query_log_id,utilidad,verdict,reason_class,comment,"
                       "created_at,telegram_user_id"),
            "created_at": f"gte.{args.desde}", "order": "created_at.asc"})

    fb_por_log: dict[str, list[dict]] = defaultdict(list)
    for f in fb:
        fb_por_log[str(f.get("query_log_id"))].append(f)

    rutas = Counter()
    fuentes = Counter()
    usuarios = Counter()
    por_dia = Counter()
    intent = Counter()
    timings = defaultdict(list)
    latencias = []
    negativos = []
    textos_locales = []
    for row in logs:
        rutas[row.get("route") or "?"] += 1
        fuentes[row.get("source") or "?"] += 1
        usuarios[_uid_hash(row.get("telegram_user_id"))] += 1
        por_dia[str(row.get("created_at") or "")[:10]] += 1
        if isinstance(row.get("response_time_ms"), int):
            latencias.append(row["response_time_ms"])
        trace = row.get("rag_trace") or {}
        if isinstance(trace, dict):
            sec = trace.get("intent") or {}
            if sec.get("status"):
                intent[f"{sec['status']}:{sec.get('decision')}"] += 1
            tm = trace.get("timings") or {}
            if tm.get("measured"):
                for etapa in ("retrieve_ms", "rerank_ms", "coverage_ms",
                              "generate_ms"):
                    timings[etapa].append(tm.get(etapa))
        for f in fb_por_log.get(str(row.get("id")), []):
            if f.get("utilidad") is False or f.get("verdict") == "incorrecta":
                negativos.append({
                    "dia": str(f.get("created_at") or "")[:10],
                    "uid": _uid_hash(f.get("telegram_user_id")),
                    "ruta": row.get("route"),
                    "reason_class": f.get("reason_class"),
                    "query_len": len(row.get("query") or ""),
                    "con_comentario": bool(f.get("comment")),
                })
        if args.con_texto:
            textos_locales.append({
                "dia": str(row.get("created_at") or "")[:10],
                "uid": _uid_hash(row.get("telegram_user_id")),
                "ruta": row.get("route"),
                "query": row.get("query"),
                "comentarios_fb": [
                    (f.get("comment") or "")[:200]
                    for f in fb_por_log.get(str(row.get("id")), [])
                    if f.get("comment")],
            })

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("Censo de tráfico real desde --desde. Sin PII: uid=hash12, "
                   "sin textos (van a data-root con --con-texto)."),
        "desde": args.desde, "utc": utc,
        "consultas": len(logs),
        "usuarios_distintos": len(usuarios),
        "consultas_por_usuario_hash": dict(usuarios.most_common(20)),
        "por_dia": dict(sorted(por_dia.items())),
        "por_ruta": dict(rutas), "por_fuente": dict(fuentes),
        "latencia_ms": {"mediana": _mediana(latencias),
                        "n": len(latencias)},
        "timings_mediana_ms": {k: _mediana(v) for k, v in timings.items()},
        "intent": dict(intent),
        "feedback": {"total": len(fb), "negativos": len(negativos),
                     "detalle_negativos": negativos},
    }
    destino = ROOT / "evals" / f"s319_trafico_census_{utc}.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"consultas {len(logs)} · usuarios {len(usuarios)} · "
          f"feedback {len(fb)} ({len(negativos)} neg) · recibo -> {destino}")
    if args.con_texto:
        local = Path(args.data_root) / "trafico" / f"textos_{utc}.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(json.dumps(textos_locales, ensure_ascii=False,
                                    indent=1), encoding="utf-8")
        print(f"textos (LOCAL, fuera del repo) -> {local}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
