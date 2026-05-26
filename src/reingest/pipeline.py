"""Orquestador de la Etapa B del pipeline de re-ingesta (PLAN_RAG_2026 Fase 1).

Recorre el store de extracción (data/extraction/<config>/) y, por cada documento,
ejecuta la cadena B1-B8:

    B2  política de idiomas   profile_document → index | register_only
    B3/B4 chunking            chunk_document (headers + tamaño, flowcharts)
    B1  idioma por chunk      detect_language; descarta chunks fr/it/pt/de
    B5  metadata              detect_document_metadata + apply_metadata
    B7  contextual retrieval  contextualize_document (Haiku + prompt caching)
    B8  embedding             embed_chunks (Voyage @1024)
    B6  dedup semántico       mark_duplicates (no destructivo)
    B8  indexación            index_chunks → chunks_v2

Re-ejecutable: el estado por archivo (logs/reingest_pipeline_state.json) permite
reanudar un run multi-día — los archivos ya hechos se saltan. La indexación es
idempotente (delete-then-insert por extraction_sha256).

Modos:
    python -m src.reingest.pipeline               # run completo
    python -m src.reingest.pipeline --dry-run     # B1-B5 sin gastar API
    python -m src.reingest.pipeline --limit 10    # primeros N (pruebas)
    python -m src.reingest.pipeline --reset       # ignora el estado previo

--dry-run no necesita las claves de Voyage/Anthropic: trocea, detecta idioma y
metadata, y vuelca una muestra a logs/reingest_dryrun_sample.json para inspección.
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from .language import detect_language, profile_document
from .chunk import chunk_document
from .metadata import detect_document_metadata, apply_metadata
from .contextualize import contextualize_document, full_document_text
from .embed import embed_chunks
from .dedup import mark_duplicates
from .index import index_chunks, resolve_document_id
from ..ingestion.supabase_client import SupabaseHTTP

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reingest.pipeline")

STORE_ROOT = "data/extraction"
DEFAULT_CONFIG = "agent_anthropic-sonnet-45"
STATE_FILE = "logs/reingest_pipeline_state.json"
REGISTER_FILE = "logs/reingest_registered.json"
DRYRUN_SAMPLE = "logs/reingest_dryrun_sample.json"

# Chunks afirmativamente detectados en estos idiomas se descartan (política B2).
# 'es'/'en' se indexan; 'unknown' (tabla/diagrama sin prosa) se conserva y
# hereda el idioma dominante del documento.
_DROP_LANGUAGES = {"fr", "it", "pt", "de"}
_SHA_RE = re.compile(r"^[0-9a-f]{64}\.json$")


def _load_json(path: str, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _save_json(path: str, data) -> None:
    """Escritura atómica con reintentos ante bloqueo transitorio del archivo.

    En Windows / OneDrive sync, `os.replace` puede dar PermissionError si el
    destino está bloqueado momentáneamente por el sincronizador o por otro
    proceso que abrió el JSON para leerlo. Reintentamos con backoff corto.
    Antes el pipeline crasheaba al doc ~99 por esta carrera.
    """
    tmp = path + ".tmp"
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last_exc = e
            time.sleep(0.2 * (attempt + 1))  # 0.2, 0.4, 0.6, 0.8, 1.0 s
    raise last_exc


def process_file(record: dict, supabase: SupabaseHTTP | None,
                 dry_run: bool) -> dict:
    """Ejecuta B1-B8 sobre un documento extraído. Devuelve el registro de estado."""
    sha = record["sha256"]
    source_path = record.get("source_path", "")

    # B2 — política de idiomas a nivel de documento.
    prof = profile_document(record)
    if prof.verdict == "register_only":
        return {"status": "register_only", "language": prof.dominant,
                "source_path": source_path}

    # B3/B4 — chunking estructural + marca de flowcharts.
    chunks = chunk_document(record)
    if not chunks:
        return {"status": "empty", "source_path": source_path}

    # B1 — idioma por chunk + filtro de política.
    for ch in chunks:
        ch.language = detect_language(ch.content)
    kept = [c for c in chunks if c.language not in _DROP_LANGUAGES]
    for c in kept:
        if c.language == "unknown":
            c.language = prof.dominant  # tabla/diagrama: hereda del documento
    for idx, c in enumerate(kept):       # re-numerar tras el filtro
        c.chunk_index = idx
    if not kept:
        return {"status": "empty_after_language", "source_path": source_path}

    # B5 — metadata.
    sample = " ".join(c.content for c in kept[:4])
    meta = detect_document_metadata(source_path, sample)
    apply_metadata(kept, meta)

    flow = sum(1 for c in kept if c.is_flow_diagram)

    if dry_run:
        return {"status": "dry_run", "chunks": len(kept),
                "flow_diagram": flow, "manufacturer": meta.manufacturer,
                "product_model": meta.product_model, "language": prof.dominant,
                "source_path": source_path, "_chunks": kept}

    # B7 — contextual retrieval.
    contextualize_document(full_document_text(record), kept)

    # B8 — embedding.
    embed_chunks(kept)

    # B6 — dedup semántico no destructivo.
    n_dup = mark_duplicates(kept)

    # B8 — indexación en chunks_v2.
    doc_id = resolve_document_id(supabase, sha, meta.source_file or "")
    n_indexed = index_chunks(kept, extraction_sha256=sha,
                             document_id=doc_id, supabase=supabase)

    return {"status": "done", "chunks": len(kept), "indexed": n_indexed,
            "duplicates": n_dup, "flow_diagram": flow,
            "document_id": doc_id, "source_path": source_path}


def run(config: str, limit: int, dry_run: bool, reset: bool) -> None:
    store = os.path.join(STORE_ROOT, config)
    if not os.path.isdir(store):
        logger.error("No existe el store %s — ¿config correcta?", store)
        return

    files = sorted(p for p in glob.glob(os.path.join(store, "*.json"))
                   if _SHA_RE.match(os.path.basename(p)))
    if limit:
        files = files[:limit]
    logger.info("Store %s — %d archivos de extracción", store, len(files))

    state = {"config": config, "files": {}} if reset else \
        _load_json(STATE_FILE, {"config": config, "files": {}})
    registered = [] if reset else _load_json(REGISTER_FILE, [])
    supabase = None if dry_run else SupabaseHTTP()

    counts = {"done": 0, "register_only": 0, "skipped": 0,
              "failed": 0, "empty": 0}
    dry_samples = []
    t0 = time.time()

    for i, path in enumerate(files):
        sha = os.path.basename(path)[:-5]
        prev = state["files"].get(sha)
        if prev and prev.get("status") in ("done", "register_only") and not dry_run:
            counts["skipped"] += 1
            continue

        try:
            record = _load_json(path, None)
            result = process_file(record, supabase, dry_run)
        except Exception as e:
            logger.exception("FALLO en %s", sha[:12])
            state["files"][sha] = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
            counts["failed"] += 1
            _save_json(STATE_FILE, state)
            continue

        status = result["status"]
        if status == "dry_run":
            chs = result.pop("_chunks")
            counts["done"] += 1
            if len(dry_samples) < 8:
                dry_samples.append({
                    "source_path": result["source_path"],
                    "manufacturer": result["manufacturer"],
                    "product_model": result["product_model"],
                    "n_chunks": result["chunks"],
                    "sample_chunks": [
                        {"section_path": c.section_path, "page": c.page_number,
                         "language": c.language, "content_type": c.content_type,
                         "is_flow_diagram": c.is_flow_diagram,
                         "chars": len(c.content),
                         "preview": c.content[:240]}
                        for c in chs[:6]
                    ],
                })
            logger.info("[%d/%d] dry-run %s -> %d chunks (%d flowchart)",
                        i + 1, len(files), sha[:12], result["chunks"],
                        result["flow_diagram"])
        elif status == "register_only":
            registered.append({"sha256": sha, **result})
            state["files"][sha] = {"status": "register_only",
                                   "language": result["language"]}
            counts["register_only"] += 1
            logger.info("[%d/%d] register-only %s (idioma %s)",
                        i + 1, len(files), sha[:12], result["language"])
        elif status == "done":
            state["files"][sha] = {"status": "done", "chunks": result["chunks"],
                                   "indexed": result["indexed"],
                                   "duplicates": result["duplicates"],
                                   "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            counts["done"] += 1
            logger.info("[%d/%d] OK %s -> %d chunks indexados (%d dup, %d flowchart)",
                        i + 1, len(files), sha[:12], result["indexed"],
                        result["duplicates"], result["flow_diagram"])
        else:  # empty / empty_after_language
            state["files"][sha] = {"status": status}
            counts["empty"] += 1

        if not dry_run:
            _save_json(STATE_FILE, state)
            _save_json(REGISTER_FILE, registered)

    if dry_run and dry_samples:
        _save_json(DRYRUN_SAMPLE, dry_samples)

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"ETAPA B — {'DRY-RUN' if dry_run else 'INDEXACIÓN'}  ({config})")
    print(f"  procesados:     {counts['done']}")
    print(f"  register-only:  {counts['register_only']}")
    print(f"  ya estaban:     {counts['skipped']}")
    print(f"  vacíos:         {counts['empty']}")
    print(f"  fallos:         {counts['failed']}")
    print(f"  tiempo:         {elapsed:.0f}s")
    if dry_run:
        print(f"  muestra:        {DRYRUN_SAMPLE}")
    else:
        print(f"  estado:         {STATE_FILE}")
        print(f"  register-list:  {REGISTER_FILE}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Etapa B — indexación del corpus re-ingestado")
    ap.add_argument("--config", default=DEFAULT_CONFIG,
                    help="subcarpeta del store de extracción a procesar")
    ap.add_argument("--limit", type=int, default=0,
                    help="procesa como máximo N archivos (0 = todos)")
    ap.add_argument("--dry-run", action="store_true",
                    help="B1-B5 sin contextualizar/embeber/indexar — no gasta API")
    ap.add_argument("--reset", action="store_true",
                    help="ignora el estado previo y re-procesa todo")
    args = ap.parse_args()
    run(args.config, args.limit, args.dry_run, args.reset)


if __name__ == "__main__":
    main()
