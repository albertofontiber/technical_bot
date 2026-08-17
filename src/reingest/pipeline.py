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
from .index import index_chunks, resolver_documento
from .page_content import sanear_record
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

# (s324d, TECH_DEBT #87) Un documento que sale de la ingesta con menos texto que esto casi nunca es
# un documento corto legítimo: es una extracción que falló y NADIE se entera (HLSI-TI-007_VSN-4REL
# vivió en el corpus con 47 chars mientras su PDF tenía 2.246 de texto nativo). No BLOQUEA — hay
# hojas de 1 párrafo legítimas —: lo DECLARA en el registro de estado y en el log.
UMBRAL_TEXTO_ESCASO = 300
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

    # (s324d #87) Guarda de markdown DEGENERADO: se sanea el registro UNA vez, aquí, antes de que
    # ningún consumidor lo lea (B2 idioma, B3/B4 chunking, B7 contextualización ven lo mismo). Un
    # fallback silencioso es lo que dejó a TI-007 en 47 chars con 3.708 en el campo `text`.
    record, auditoria_md = sanear_record(record)
    if auditoria_md["n_paginas_afectadas"]:
        logger.warning("md DEGENERADO en %s: %d página(s) saneadas, %d chars rescatados del campo `text`",
                       source_path, auditoria_md["n_paginas_afectadas"], auditoria_md["chars_rescatados"])

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

    # (s324d #87) Aviso de texto escaso: no bloquea, DECLARA.
    chars_totales = sum(len(c.content or "") for c in kept)
    texto_escaso = chars_totales < UMBRAL_TEXTO_ESCASO
    if texto_escaso:
        logger.warning("TEXTO ESCASO en %s: %d chars en %d chunk(s) (< %d). Revisa la extracción "
                       "antes de dar el documento por ingestado.",
                       source_path, chars_totales, len(kept), UMBRAL_TEXTO_ESCASO)
    extra = {"chars": chars_totales, "texto_escaso": texto_escaso, "md_degenerado": auditoria_md}

    if dry_run:
        return {"status": "dry_run", "chunks": len(kept),
                "flow_diagram": flow, "manufacturer": meta.manufacturer,
                "product_model": meta.product_model, "language": prof.dominant,
                "source_path": source_path, "_chunks": kept, **extra}

    # s323 fase B (duo r33, Fable): resolver ANTES de B7/B8. La resolucion solo
    # necesita sha + metadata de B5 — resolverla despues hacia pagar
    # contextualizacion (Haiku) y embeddings (Voyage) de un documento que luego
    # no se indexa, y RE-pagarlos en cada reintento.
    resolucion = resolver_documento(supabase, sha, meta.source_file or "",
                                    manufacturer=meta.manufacturer)
    if not resolucion.enlazable:
        logger.warning("indexacion OMITIDA para %s: %s (%s)",
                       meta.source_file, resolucion.estado.value,
                       resolucion.detalle)
        return {"status": "sin_indexar", "motivo": resolucion.estado.value,
                "detalle": resolucion.detalle, "chunks": len(kept), "indexed": 0,
                "duplicates": 0, "flow_diagram": flow,
                "document_id": None, "source_path": source_path}

    # B7 — contextual retrieval.
    contextualize_document(full_document_text(record), kept)

    # B8 — embedding.
    embed_chunks(kept)

    # B6 — dedup semántico no destructivo.
    n_dup = mark_duplicates(kept)

    # B8 — indexación en chunks_v2.
    # s323 fase B (dúo r32): la resolución es TIPADA y se PARA antes de indexar
    # si no hay exactamente una fila ACTIVA. Indexar igualmente haría una de dos
    # cosas malas: crear chunks huérfanos (#81) o ligarlos a un documento
    # retirado, que el retrieval DESCARTA. Y como `index_chunks` borra antes de
    # insertar, seguir adelante destruiría además las filas buenas.
    doc_id = resolucion.document_id
    n_indexed = index_chunks(kept, extraction_sha256=sha,
                             document_id=doc_id, supabase=supabase)

    return {"status": "done", "chunks": len(kept), "indexed": n_indexed,
            "duplicates": n_dup, "flow_diagram": flow,
            "document_id": doc_id, "source_path": source_path, **extra}


def run(config: str, limit: int, dry_run: bool, reset: bool,
        gate=None) -> None:
    store = os.path.join(STORE_ROOT, config)
    # GUARDAS (s301): salir con codigo != 0 cuando el paso NO puede correr — un
    # "return" con exit 0 aparenta ejecucion (clase manifiesto-vacio: el corpus y el
    # store viven en la carpeta OneDrive; desde el checkout de C:\dev esto esta vacio).
    if not os.path.isdir(store):
        raise SystemExit(f"No existe el store {store} — ¿config correcta? ¿cwd con corpus?")

    files = sorted(p for p in glob.glob(os.path.join(store, "*.json"))
                   if _SHA_RE.match(os.path.basename(p)))
    if not files:
        raise SystemExit(
            f"Store {store} VACIO: 0 extracciones. ¿Ejecutando desde el checkout sin "
            f"corpus? El store vive en la carpeta OneDrive del proyecto."
        )
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
        elif status == "sin_indexar":
            # s323 (duo r33): NO es un vacio. Se persiste el motivo TIPADO — si
            # solo se guardara el status, la distincion por la que se hizo todo
            # el cambio moriria en un log efimero y un ERROR de red se agregaria
            # como "vacio" en el resumen.
            state["files"][sha] = {"status": status,
                                   "motivo": result.get("motivo"),
                                   "detalle": result.get("detalle")}
            counts["sin_indexar"] = counts.get("sin_indexar", 0) + 1
            logger.warning("[%d/%d] SIN INDEXAR %s -> %s (%s)", i + 1, len(files),
                           sha[:12], result.get("motivo"), result.get("detalle"))
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
    print(f"  sin indexar:    {counts.get('sin_indexar', 0)}  (identidad no resuelta)")
    print(f"  fallos:         {counts['failed']}")
    # s323 fase C (critico 2 del suplente): el gate se INYECTA. `reingest` no
    # puede importar `rag` (contrato de imports) y este `run` es un write-path
    # real, asi que la dependencia entra por parametro: quien orquesta pasa el
    # gate y aqui se EJECUTA siempre que se haya escrito algo. Sin inyeccion no
    # se ejecuta — y por eso `main()` (la CLI directa) se niega a correr sin el.
    if gate is not None and not dry_run:
        try:
            veredicto = gate()
        except Exception as e:                                # noqa: BLE001
            # Fable M2: "no evaluado" tenia semantica propia en UN solo
            # write-path. Aqui corria sin try/except y una excepcion daba
            # traceback generico en vez del codigo 4 acordado.
            logger.error("gate de identidad NO evaluado: %s", e)
            raise SystemExit(4) from e
        print(f"  gate identidad: {'OK' if veredicto['ok'] else 'VIOLACIONES NUEVAS'}"
              f"  ({veredicto['nuevas']} nuevas / {veredicto['total']} totales)")
        if veredicto.get("manifiesto_stale"):
            print(f"  aviso: {len(veredicto['excepciones_resueltas'])} excepciones del "
                  f"manifiesto ya no aplican - re-sella con --sellar")
        if not veredicto["ok"]:
            logger.error("GATE DE IDENTIDAD: %d violaciones NUEVAS -> %s",
                         veredicto["nuevas"], veredicto["detalle_nuevas"][:3])
            raise SystemExit(3)

    # (el gate NO se importa aqui: se inyecta. El contrato de
    # imports prohibe `reingest -> rag` (tests/test_import_contract.py) y el gate
    # necesita el catalogo, que vive en rag. Se cablea en la CAPA DE SCRIPTS, que
    # es quien orquesta: `scripts/ingest_new.py` (driver real de altas) y
    # cualquier runner de este pipeline. La arquitectura manda sobre mi prisa.
    print(f"  tiempo:         {elapsed:.0f}s")
    if dry_run:
        print(f"  muestra:        {DRYRUN_SAMPLE}")
    else:
        print(f"  estado:         {STATE_FILE}")
        print(f"  register-list:  {REGISTER_FILE}")


def main() -> None:
    """CLI directa. s323 fase C (critico 2): ejecutar el pipeline por aqui era un
    write-path SIN el gate de identidad — el agujero que decia haber cerrado. Esta
    entrada ya no indexa: redirige al runner gobernado, que inyecta el gate."""
    raise SystemExit(
        "Esta entrada ya no indexa (s323 fase C): escribir sin el gate de identidad "
        "es como entraron #80/#81.\n"
        "Usa el runner gobernado:  python scripts/reingest_run.py --config ... \n"
        "(o llama a run(..., gate=...) inyectando el gate explicitamente).")


# (s323 fase C, Fable M4): `_main_legacy()` ELIMINADO. Llamaba a run() SIN
# gate: el bypass del critico 2 quedaba a una linea de distancia, sin test
# que impidiera re-cablearlo. El unico camino que escribe lleva el gate.

if __name__ == "__main__":
    main()
