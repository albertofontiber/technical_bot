#!/usr/bin/env python3
"""Filtro determinista de contenido-informativo para el SERVING visual (S271c).

Motivo (gate del resto NO-PASS 56/60): el clasificador de imagen (Luna v4)
marca useful páginas SIN contenido informativo real — plantillas de log EN
BLANCO y frontmatter — porque estructuralmente PARECEN tablas/procedimientos.
Este filtro es la barandilla estructural del serving (mismo principio que el
guard del apéndice de texto): una página servible debe tener contenido real.

Señales (deterministas, declaradas A PRIORI — anti-overfit: nada se tunea
sobre los 60 items observados del gate; los umbrales son fijos y el filtro
corre sobre TODO el serving-set):
  S1 blank_table_template — la página tiene una REJILLA real de celdas de
     datos vacías (>=6 celdas de datos, CERO informativas) y su texto fuera
     de tabla es mínimo (<200 alfanuméricos): plantilla para rellenar a
     mano, no información. El mínimo de 6 celdas existe porque LlamaParse a
     veces vuelca árboles/ventanas de UI como "tablas" con 2-3 celdas
     vacías sueltas — eso no es una plantilla (FP verificado en dry-run).
  S2 low_density — el texto de la página en chunks_v2 tiene <120
     alfanuméricos Y el render corrobora página casi vacía: bytes/píxel del
     JPEG < 0.05 (una página sin tinta comprime a casi nada; una tabla
     densa no baja de ~0.08). La corroboración de imagen es OBLIGATORIA:
     el texto-por-página de chunks_v2 tiene falsos vacíos de extracción
     (página densa cuyo contenido cayó en el chunk de otra página — FP
     verificado en dry-run; clase feedback_corpus_gap). Sin stats del
     render (assets legacy del bridge sin width/height/bytes) S2 NO se
     evalúa (fail-open declarado). EXENTA la role 'wiring': un esquema es
     gráfico-primero.
  Declarado NO cubierto: prosa genérica sin figura (texto denso real; sin
  mirar la imagen no es separable) — residual que mide el re-gate.
  Los 2 FPs usados para endurecer las señales salieron del PROPIO dry-run
  (verify-first sobre degradados), NO de los 60 items del gate resto v1.

Nota sobre must_preserve: su lógica de celdas (bundle/defline) clasifica si
un NÚMERO es dato de celda — no detecta plantillas vacías; no aplica directo.
Aquí el analizador de tablas markdown es propio y mínimo.

Fuente del texto: chunks_v2 (GET-only) por (document_id, page_number) ==
(document_id, page_index) del asset (join del contrato S190). Página servible
sin chunks = anomalía: se REPORTA y NO se degrada (fail-open declarado).

Modos:
  (default, dry-run)  GET + análisis local; escribe el reporte
      evals/s271_content_filter_report_v1.json y el payload de degradación
      evals/s271_content_filter_degrade_v1.jsonl. 0 escrituras a DB.
  --execute --env RUTA  aplica la degradación (upsert merge-duplicates:
      technical_utility='not_useful', classifier_contract='s271_content_filter_v1',
      receipt con las señales y el estado previo). LO CORRE EL ORQUESTADOR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT / ".env"
REPORT_PATH = ROOT / "evals" / "s271_content_filter_report_v1.json"
DEGRADE_PATH = ROOT / "evals" / "s271_content_filter_degrade_v1.jsonl"

TARGET_TABLE = "document_visual_assets"
CHUNKS_TABLE = "chunks_v2"
SERVABLE_ROLES = ("wiring", "table", "procedure", "ui")
FILTER_CONTRACT = "s271_content_filter_v1"
PAGE_SIZE = 1_000
LOAD_BATCH = 500

# Umbrales A PRIORI (fijos; no ajustados sobre los 60 items del gate resto v1).
MIN_TOTAL_ALNUM = 120        # S2: por debajo, la página casi no tiene texto
MAX_NON_TABLE_ALNUM_S1 = 200  # S1: una plantilla no lleva prosa sustancial
MIN_BLANK_DATA_CELLS_S1 = 6   # S1: rejilla real (>=~2 filas x 3 cols), no celdas sueltas
MAX_BYTES_PER_PIXEL_S2 = 0.05  # S2: JPEG casi sin tinta (denso ~0.08-0.15)
DENSITY_EXEMPT_ROLES = ("wiring",)  # gráfico-primero: el texto no mide su valor
RENDER_DIR = ROOT / "data" / "s271_renders"  # manifests locales (bytes/px del render)

# Fila separadora markdown: solo estructura Y al menos un guion/=. Una fila
# de celdas VACÍAS (solo espacios y pipes) NO es separador: es dato en blanco
# — exactamente lo que una plantilla de log tiene que contar como celdas.
_SEPARATOR_LINE = re.compile(r"^(?=.*[-=])[\s|:\-=]+$")


def _alnum(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum())


def _row_cells(row: str) -> list[str]:
    """Celdas de una fila markdown; descarta solo los segmentos exteriores
    VACÍOS (pipes de borde), no celdas reales."""
    parts = row.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return parts


def analyze_page_text(texts: list[str]) -> dict[str, int | bool]:
    """Métricas deterministas del texto de una página (chunks deduplicados)."""
    seen: set[str] = set()
    total_alnum = 0
    non_table_alnum = 0
    data_cells = 0
    informative_data_cells = 0
    has_table = False
    for text in texts:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if digest in seen:  # ventanas de chunking duplican contenido de página
            continue
        seen.add(digest)
        total_alnum += _alnum(text)
        lines = text.splitlines()
        run: list[str] = []
        for line in lines + [""]:  # sentinel para cerrar el último run
            if line.count("|") >= 2:
                run.append(line)
                continue
            if run:
                rows = [l for l in run if not _SEPARATOR_LINE.match(l)]
                cells_per_row = [_row_cells(row) for row in rows]
                if len(run) >= 2 and any(len(c) >= 2 for c in cells_per_row):
                    has_table = True
                    for row_cells in cells_per_row[1:]:  # fila 0 = cabecera
                        for cell in row_cells:
                            data_cells += 1
                            if any(ch.isalnum() for ch in cell):
                                informative_data_cells += 1
                else:
                    non_table_alnum += sum(_alnum(l) for l in run)
                run = []
            if line.strip():
                non_table_alnum += _alnum(line)
    return {
        "total_alnum": total_alnum,
        "non_table_alnum": non_table_alnum,
        "has_table": has_table,
        "data_cells": data_cells,
        "informative_data_cells": informative_data_cells,
    }


def page_signals(
    metrics: dict[str, Any],
    visual_role: str,
    render_stats: dict[str, Any] | None = None,
) -> list[str]:
    """Señales de no-informativo (vocabulario cerrado, orden estable).

    ``render_stats`` = {bytes, width, height} del render (manifest local);
    sin él, S2 no es evaluable (fail-open declarado — los legacy del bridge
    no traen stats).
    """
    signals = []
    if (
        metrics["has_table"]
        and metrics["data_cells"] >= MIN_BLANK_DATA_CELLS_S1
        and metrics["informative_data_cells"] == 0
        and metrics["non_table_alnum"] < MAX_NON_TABLE_ALNUM_S1
    ):
        signals.append("blank_table_template")
    if (
        metrics["total_alnum"] < MIN_TOTAL_ALNUM
        and visual_role not in DENSITY_EXEMPT_ROLES
        and render_stats is not None
        and render_stats.get("bytes")
        and render_stats.get("width")
        and render_stats.get("height")
        and (
            render_stats["bytes"] / (render_stats["width"] * render_stats["height"])
            < MAX_BYTES_PER_PIXEL_S2
        )
    ):
        signals.append("low_density")
    return signals


# ---------------------------------------------------------------------------
# GET-only: serving-set + texto por página
# ---------------------------------------------------------------------------

def _headers(env_path: Path) -> tuple[str, dict[str, str]]:
    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    return base_url, {"apikey": key, "Authorization": f"Bearer {key}"}


def _stream(client, url, headers, select, filters=None):
    last_id = None
    while True:
        params = {"select": f"id,{select}", "limit": str(PAGE_SIZE), "order": "id.asc"}
        params.update(filters or {})
        if last_id is not None:
            params["id"] = f"gt.{last_id}"
        response = client.get(url, headers=headers, params=params, timeout=120)
        response.raise_for_status()
        page = response.json()
        if not page:
            return
        yield from page
        last_id = page[-1]["id"]
        if len(page) < PAGE_SIZE:
            return


def fetch_serving_rows(client, base_url, headers) -> list[dict[str, Any]]:
    select = (
        "document_id,page_index,page_label,asset_sha256,storage_url,media_type,"
        "width,height,asset_scope,visual_role,technical_utility,"
        "classifier_contract,source_extraction_sha256"
    )
    rows = list(
        _stream(
            client,
            f"{base_url}/rest/v1/{TARGET_TABLE}",
            headers,
            select,
            filters={
                "technical_utility": "eq.useful",
                "visual_role": f"in.({','.join(SERVABLE_ROLES)})",
            },
        )
    )
    return rows


def fetch_page_metrics(
    client, base_url, headers, pages_needed: set[tuple[str, int]]
) -> dict[tuple[str, int], dict[str, Any]]:
    """Streaming de chunks_v2 (25k filas) agregando SOLO las páginas servidas."""
    texts: dict[tuple[str, int], list[str]] = {}
    observed = 0
    for row in _stream(
        client,
        f"{base_url}/rest/v1/{CHUNKS_TABLE}",
        headers,
        "document_id,page_number,content",
    ):
        observed += 1
        if observed % 5000 == 0:
            print(f"  chunks_v2: {observed} filas...", flush=True)
        key = (str(row.get("document_id") or ""), row.get("page_number"))
        if not key[0] or not isinstance(key[1], int) or key not in pages_needed:
            continue
        texts.setdefault(key, []).append(str(row.get("content") or ""))
    print(f"  chunks_v2: {observed} filas totales", flush=True)
    return {key: analyze_page_text(value) for key, value in texts.items()}


# ---------------------------------------------------------------------------
# Dry-run / execute
# ---------------------------------------------------------------------------

def load_render_stats(
    render_dir: Path = RENDER_DIR,
) -> dict[tuple[str, int, str], dict[str, Any]]:
    """bytes/width/height por asset desde los manifests locales del backfill."""
    stats: dict[tuple[str, int, str], dict[str, Any]] = {}
    if not render_dir.exists():
        return stats
    for tramo in sorted(p for p in render_dir.iterdir() if p.is_dir()):
        manifest = tramo / "manifest.jsonl"
        if not manifest.exists():
            continue
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (str(row["document_id"]), int(row["page_index"]), row["asset_sha256"])
            stats[key] = {
                "bytes": row.get("bytes"),
                "width": row.get("width"),
                "height": row.get("height"),
            }
    return stats


def run_filter(env_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base_url, headers = _headers(env_path)
    with httpx.Client() as client:
        print("GET serving-set...", flush=True)
        serving = fetch_serving_rows(client, base_url, headers)
        print(f"  serving: {len(serving)} filas", flush=True)
        pages = {(str(r["document_id"]), int(r["page_index"])) for r in serving}
        print("GET texto de páginas (chunks_v2)...", flush=True)
        metrics_by_page = fetch_page_metrics(client, base_url, headers, pages)
    render_stats = load_render_stats()
    print(f"  render stats locales: {len(render_stats)} assets", flush=True)

    degraded: list[dict[str, Any]] = []
    counts: Counter = Counter()
    text_low_bpp: list[float] = []
    no_text = 0
    for row in serving:
        cohort = row.get("classifier_contract") or "sin_contrato"
        counts[f"serving_{cohort}"] += 1
        key = (str(row["document_id"]), int(row["page_index"]))
        metrics = metrics_by_page.get(key)
        if metrics is None:
            no_text += 1  # anomalía: se reporta, NO se degrada (fail-open)
            continue
        stats = render_stats.get(
            (str(row["document_id"]), int(row["page_index"]), row["asset_sha256"])
        )
        if metrics["total_alnum"] < MIN_TOTAL_ALNUM:
            counts["text_low_pages"] += 1
            if stats and stats.get("bytes") and stats.get("width") and stats.get("height"):
                text_low_bpp.append(
                    round(stats["bytes"] / (stats["width"] * stats["height"]), 4)
                )
            else:
                counts["s2_skipped_no_render_stats"] += 1
        signals = page_signals(metrics, row["visual_role"], stats)
        if not signals:
            continue
        counts["degraded_total"] += 1
        counts[f"degraded_{cohort}"] += 1
        counts[f"degraded_role_{row['visual_role']}"] += 1
        for signal in signals:
            counts[f"signal_{signal}"] += 1
        degraded.append(
            {
                **{k: row[k] for k in row if k != "id"},
                "filter_signals": signals,
                "filter_metrics": metrics,
                "previous_technical_utility": row["technical_utility"],
                "previous_classifier_contract": row["classifier_contract"],
            }
        )

    report = {
        "instrument": "s271_content_filter_report_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "config": {
            "signals": ["blank_table_template", "low_density"],
            "min_total_alnum": MIN_TOTAL_ALNUM,
            "max_non_table_alnum_s1": MAX_NON_TABLE_ALNUM_S1,
            "min_blank_data_cells_s1": MIN_BLANK_DATA_CELLS_S1,
            "max_bytes_per_pixel_s2": MAX_BYTES_PER_PIXEL_S2,
            "density_exempt_roles": list(DENSITY_EXEMPT_ROLES),
            "declared_not_covered": "prosa genérica sin figura (residual del re-gate)",
            "anti_overfit": "umbrales fijados a priori; el filtro corre sobre "
            "TODO el serving-set; cero excepciones por item; los 60 items del "
            "gate resto v1 no se consultaron para fijar umbrales (los 2 FPs "
            "que endurecieron S1/S2 salieron del propio dry-run, verify-first)",
            "text_source": "chunks_v2 (document_id, page_number) — GET-only",
            "render_stats_source": "data/s271_renders/*/manifest.jsonl (local)",
        },
        "serving_total": len(serving),
        "pages_without_text_fail_open": no_text,
        "text_low_bpp_distribution": {
            "n": len(text_low_bpp),
            "below_threshold": sum(
                1 for b in text_low_bpp if b < MAX_BYTES_PER_PIXEL_S2
            ),
            "min": min(text_low_bpp) if text_low_bpp else None,
            "median": (
                sorted(text_low_bpp)[len(text_low_bpp) // 2] if text_low_bpp else None
            ),
            "max": max(text_low_bpp) if text_low_bpp else None,
        },
        "counts": dict(sorted(counts.items())),
        "degrade_payload": str(DEGRADE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sample_degraded": [
            {
                "document_id": d["document_id"],
                "page_index": d["page_index"],
                "visual_role": d["visual_role"],
                "signals": d["filter_signals"],
                "metrics": d["filter_metrics"],
                "storage_url": d["storage_url"],
            }
            for d in degraded[:20]
        ],
    }
    return report, degraded


def write_outputs(report: dict[str, Any], degraded: list[dict[str, Any]]) -> None:
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with DEGRADE_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in degraded:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"reporte: {REPORT_PATH}")
    print(f"payload de degradación: {DEGRADE_PATH} ({len(degraded)} filas)")


def execute(env_path: Path) -> int:
    """Aplica la degradación (LO CORRE EL ORQUESTADOR). Upsert idempotente."""
    if not DEGRADE_PATH.exists():
        print("ABORT: falta el payload del dry-run.", file=sys.stderr)
        return 2
    degraded = [
        json.loads(line)
        for line in DEGRADE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    base_url, headers = _headers(env_path)
    table_columns = (
        "document_id", "page_index", "page_label", "asset_sha256", "storage_url",
        "media_type", "width", "height", "asset_scope", "visual_role",
        "technical_utility", "classifier_contract", "classifier_receipt",
        "source_extraction_sha256",
    )
    payloads = []
    for row in degraded:
        payload = {k: row.get(k) for k in table_columns}
        payload["technical_utility"] = "not_useful"
        payload["classifier_contract"] = FILTER_CONTRACT
        payload["classifier_receipt"] = {
            "instrument": "s271_content_filter_v1",
            "signals": row["filter_signals"],
            "metrics": row["filter_metrics"],
            "previous_technical_utility": row["previous_technical_utility"],
            "previous_classifier_contract": row["previous_classifier_contract"],
            "degrade_payload": str(DEGRADE_PATH.relative_to(ROOT)).replace("\\", "/"),
        }
        payloads.append(payload)
    post_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    applied = 0
    with httpx.Client(timeout=120) as client:
        before = _count_servable(client, base_url, headers)
        for start in range(0, len(payloads), LOAD_BATCH):
            batch = payloads[start : start + LOAD_BATCH]
            response = client.post(
                f"{base_url}/rest/v1/{TARGET_TABLE}",
                headers=post_headers,
                params={"on_conflict": "document_id,page_index,asset_sha256"},
                json=batch,
            )
            response.raise_for_status()
            applied += len(batch)
            print(f"execute: {applied}/{len(payloads)}", flush=True)
        after = _count_servable(client, base_url, headers)
        filtered = _count_contract(client, base_url, headers)
    print(
        f"execute: servibles {before} -> {after} (esperado {before - len(payloads)}); "
        f"filas {FILTER_CONTRACT}: {filtered} (esperado {len(payloads)})"
    )
    if after != before - len(payloads) or filtered != len(payloads):
        print("ABORT: counts post-execute no cuadran.", file=sys.stderr)
        return 1
    return 0


def _count_servable(client, base_url, headers) -> int:
    response = client.head(
        f"{base_url}/rest/v1/{TARGET_TABLE}",
        headers={**headers, "Prefer": "count=exact"},
        params={
            "technical_utility": "eq.useful",
            "visual_role": f"in.({','.join(SERVABLE_ROLES)})",
            "limit": "1",
        },
    )
    response.raise_for_status()
    return int(response.headers["content-range"].rsplit("/", 1)[1])


def _count_contract(client, base_url, headers) -> int:
    response = client.head(
        f"{base_url}/rest/v1/{TARGET_TABLE}",
        headers={**headers, "Prefer": "count=exact"},
        params={"classifier_contract": f"eq.{FILTER_CONTRACT}", "limit": "1"},
    )
    response.raise_for_status()
    return int(response.headers["content-range"].rsplit("/", 1)[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Aplica la degradación a la tabla (SOLO el orquestador).",
    )
    args = parser.parse_args()
    if args.execute:
        return execute(args.env)
    report, degraded = run_filter(args.env)
    write_outputs(report, degraded)
    print(
        json.dumps(
            {k: report[k] for k in ("serving_total", "pages_without_text_fail_open", "counts")},
            indent=2,
            ensure_ascii=False,
        )
    )
    print("dry-run: 0 escrituras a DB. Aplicar con: --execute --env <ruta>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
