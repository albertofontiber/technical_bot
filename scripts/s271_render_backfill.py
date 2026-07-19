#!/usr/bin/env python3
"""Pipeline S271 por tramos: render→upload→load→classify→gate del backfill visual.

Cubre el 69% de páginas de ``chunks_v2`` SIN activo visual (worklist =
``evals/s271_pdf_coverage_v1.json``, solo documentos ``located_sha_verified``:
sha256(PDF local) == ``chunks_v2.extraction_sha256``). Prereg del presupuesto:
``evals/s271_render_backfill_prereg_v1.yaml``.

TRAMOS (pre-declarados, deterministas): worklist ordenado por (fabricante,
source_file, document_id); el PILOTO ``t00-piloto`` son los primeros documentos
hasta acumular >=500 páginas (corte en frontera de documento); el resto es un
tramo por fabricante (``tNN-<slug>``). STOP obligatorio tras el piloto: gate
(``--gate-sample`` + spot-check del orquestador) ANTES de seguir con ``resto``.

Fases (todas con checkpoint resumible; sin ``--execute`` NADA escribe fuera del
disco local):
  (sin flags)        plan: tramos + estimaciones (0 escrituras, 0 llamadas).
  --write-prereg     emite el prereg YAML con el presupuesto declarado.
  --render --tramo T          render local PyMuPDF 170dpi JPEG q80 (NO storage).
  --upload --tramo T --execute  sube a Supabase Storage (bucket/patrón legacy:
                     ``manual-images/{slug}/{slug}_{stem}_pNNN.jpg``); sha256
                     del binario verificado tras subir; x-upsert=false (un
                     conflicto NUNCA pisa un objeto existente).
  --load --tramo T --execute    INSERT idempotente a document_visual_assets
                     (technical_utility='uncertain': JAMÁS se sirve sin gate).
  --classify --tramo T [--execute --env-file RUTA]   clasificador heredado v4
                     (gpt-5.6-luna, contrato v3/v1, batches 10, no-retry,
                     stop-line $12). Sin --execute: preflight sin coste.
  --apply-labels --execute      upsert de labels a la tabla (merge-duplicates).
  --gate-sample [--download-dir D]  muestra fresca 60 del serving-set NUEVO
                     (seed 271, patrón v4) para el spot-check del orquestador.

``--tramo`` acepta un id (``t00-piloto``) o ``resto`` (todos menos el piloto).
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
from urllib.parse import quote

try:
    from scripts.s191_visual_utility_executor import (
        BATCH_SIZE,
        SERVABLE_ROLES,
        parse_labels,
    )
    from scripts.s191_visual_utility_executor_luna import (
        INPUT_USD_PER_MILLION,
        MODEL,
        OUTPUT_USD_PER_MILLION,
        _input_content,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from s191_visual_utility_executor import (  # type: ignore
        BATCH_SIZE,
        SERVABLE_ROLES,
        parse_labels,
    )
    from s191_visual_utility_executor_luna import (  # type: ignore
        INPUT_USD_PER_MILLION,
        MODEL,
        OUTPUT_USD_PER_MILLION,
        _input_content,
    )

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT / ".env"
COVERAGE_PATH = ROOT / "evals" / "s271_pdf_coverage_v1.json"
PREREG_PATH = ROOT / "evals" / "s271_render_backfill_prereg_v1.yaml"
RENDER_DIR = ROOT / "data" / "s271_renders"  # data/* está gitignored (artefacto)
LABELS_PATH = ROOT / "evals" / "s271_visual_utility_labels_v1.jsonl"
LABEL_RECEIPTS_PATH = ROOT / "evals" / "s271_visual_utility_labels_v1.receipts.jsonl"
LABEL_FAILURES_PATH = ROOT / "evals" / "s271_visual_utility_labels_v1.failures.jsonl"
GATE_SAMPLE_PATH = ROOT / "evals" / "s271_visual_utility_gate_sample.json"
V4_RECEIPTS_PATH = ROOT / "evals" / "s269_visual_utility_labels_v4_full.receipts.jsonl"

TARGET_TABLE = "document_visual_assets"
STORAGE_BUCKET = "manual-images"  # mismo bucket que los assets legacy
RENDER_DPI = 170
JPEG_QUALITY = 80
PILOT_TRAMO_ID = "t00-piloto"
PILOT_MIN_PAGES = 500
LOAD_BATCH = 500
BUDGET_STOP_USD = 12.0  # techo duro de clasificación (estimado ~$7.7)
# Medido en el muestreo S271 (n=20, 170dpi q80): ~255 KB/página.
MEASURED_JPEG_BYTES_PER_PAGE = 255 * 1024
# Fallback si faltara el recibo v4 ($0.05445/80 items medido en v3).
FALLBACK_PER_ITEM_USD = 0.000680625
CLASSIFIER_CONTRACT = "s271_visual_utility_v1"
GATE_SAMPLE_N = 60
GATE_SAMPLE_SEED = "271"


# ---------------------------------------------------------------------------
# Worklist y tramos (deterministas, pre-declarados)
# ---------------------------------------------------------------------------

def slugify(value: str) -> str:
    """Solo [a-z0-9._-]: URL-safe sin encoding (legacy usa espacios; aquí no)."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "unknown"


def storage_path(
    manufacturer: str, source_file: str, page_index: int, document_id: str
) -> str:
    """Patrón legacy + discriminador de revisión (S271b):
    ``{prefix}/{prefix}_{stem}_{docid8}_pNNN.jpg`` en manual-images.

    Legacy: ``unknown/unknown_HLSI-MI-580I_p001.jpg`` (prefix = carpeta de
    producto o 'unknown'). S271: prefix = slug del fabricante y pNNN =
    page_number de chunks_v2. ``docid8`` (primeros 8 del document_id) es
    OBLIGATORIO desde S271b: el mismo source_file puede existir bajo DOS
    document_ids (revisiones v04/v07 que s107 separó — caso real
    HLSI-MN-103_RP1r-Supra_lr) y sin discriminador los nombres COLISIONAN
    (50 pares en t11-notifier; cada render pisaba al otro → sha mismatch →
    fail-closed en upload). El esquema nuevo aplica a renders NUEVOS y a los
    colisionados saneados; los items viejos no colisionados conservan su
    nombre (el manifest es la fuente, no esta función).
    """
    prefix = slugify(manufacturer).lower()
    stem = source_file.strip()
    if stem.casefold().endswith(".pdf"):
        stem = stem[:-4]
    docid8 = slugify(str(document_id))[:8].lower()
    return f"{prefix}/{prefix}_{slugify(stem)}_{docid8}_p{page_index:03d}.jpg"


def item_id_for(document_id: str, page_index: int) -> str:
    """Id estable e independiente del orden/resume (clave del checkpoint)."""
    digest = hashlib.sha256(f"{document_id}|{page_index}".encode("utf-8")).hexdigest()
    return f"s271_{digest[:12]}"


def load_worklist(coverage_path: Path = COVERAGE_PATH) -> list[dict[str, Any]]:
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    docs = [
        doc
        for doc in coverage["documents"]
        if doc.get("status") == "located_sha_verified" and doc.get("renderable_pages")
    ]
    docs.sort(
        key=lambda d: (
            d["manufacturer"].casefold(),
            d["source_file"].casefold(),
            d["document_id"],
        )
    )
    return docs


def build_tramos(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Piloto = primeros docs hasta >=500 páginas (corte en frontera de doc);
    resto = un tramo por fabricante, en orden alfabético."""
    tramos: dict[str, list[dict[str, Any]]] = {PILOT_TRAMO_ID: []}
    pilot_pages = 0
    rest: list[dict[str, Any]] = []
    for doc in docs:
        if pilot_pages < PILOT_MIN_PAGES:
            tramos[PILOT_TRAMO_ID].append(doc)
            pilot_pages += len(doc["renderable_pages"])
        else:
            rest.append(doc)
    manufacturers = sorted(
        {doc["manufacturer"] for doc in rest}, key=lambda m: m.casefold()
    )
    for index, manufacturer in enumerate(manufacturers, start=1):
        tramo_id = f"t{index:02d}-{slugify(manufacturer).lower()}"
        tramos[tramo_id] = [d for d in rest if d["manufacturer"] == manufacturer]
    return tramos


def select_tramos(
    tramos: dict[str, list[dict[str, Any]]], selector: str
) -> dict[str, list[dict[str, Any]]]:
    if selector == "resto":
        return {tid: docs for tid, docs in tramos.items() if tid != PILOT_TRAMO_ID}
    if selector not in tramos:
        raise SystemExit(
            f"ABORT: tramo desconocido {selector!r}. Válidos: "
            f"{', '.join(tramos)} o 'resto'."
        )
    return {selector: tramos[selector]}


def tramo_pages(docs: list[dict[str, Any]]) -> int:
    return sum(len(doc["renderable_pages"]) for doc in docs)


# ---------------------------------------------------------------------------
# Checkpoints JSONL (patrón v4: append-only, tolerante a última línea rota)
# ---------------------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                continue  # append truncado por crash: el resume lo repite
            raise
    return rows


def latest_by_item(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Dedupe de un checkpoint append-only: la ÚLTIMA fila por item_id manda."""
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[row["item_id"]] = row
    return result


def receipt_is_current(
    receipt: dict[str, Any], row: dict[str, Any] | None
) -> bool:
    """Un receipt de upload solo vale si es EXACTAMENTE el binario y la ruta
    de la fila vigente del manifest (resume sha-aware, S271b): un receipt
    obsoleto tras un re-render/saneo no cuenta como subido."""
    return (
        row is not None
        and bool(receipt.get("verified"))
        and receipt.get("asset_sha256") == row["asset_sha256"]
        and receipt.get("storage_path") == row["storage_path"]
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def tramo_dir(tramo_id: str, render_dir: Path = RENDER_DIR) -> Path:
    return render_dir / tramo_id


def manifest_path(tramo_id: str, render_dir: Path = RENDER_DIR) -> Path:
    return tramo_dir(tramo_id, render_dir) / "manifest.jsonl"


def upload_receipts_path(tramo_id: str, render_dir: Path = RENDER_DIR) -> Path:
    return tramo_dir(tramo_id, render_dir) / "upload_receipts.jsonl"


def sha256_bytes(binary: bytes) -> str:
    return hashlib.sha256(binary).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Fase RENDER (local, $0, sin red)
# ---------------------------------------------------------------------------

def render_tramo(
    tramo_id: str,
    docs: list[dict[str, Any]],
    render_dir: Path = RENDER_DIR,
) -> dict[str, int]:
    import fitz  # PyMuPDF — mismo stack que la ingesta

    # Silenciar el ruido no-fatal de MuPDF en stderr (p.ej. "No common
    # ancestor in structure tree" en PDFs con árbol de estructura roto: la
    # página se renderiza igualmente; el fallo REAL se detecta por excepción).
    fitz.TOOLS.mupdf_display_errors(False)

    out_dir = tramo_dir(tramo_id, render_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_path(tramo_id, render_dir)
    done: dict[tuple[str, int], dict[str, Any]] = {}
    for row in read_jsonl(manifest_file):
        done[(row["document_id"], row["page_index"])] = row

    stats = Counter(rendered=0, resumed=0, failed_docs=0)
    for doc in docs:
        pending = [
            page
            for page in doc["renderable_pages"]
            if not _render_done(done.get((doc["document_id"], page)), out_dir)
        ]
        stats["resumed"] += len(doc["renderable_pages"]) - len(pending)
        if not pending:
            continue
        pdf_path = Path(doc["pdf_path"])
        if not pdf_path.is_file():
            print(f"  FAIL {doc['source_file']}: PDF no encontrado", file=sys.stderr)
            stats["failed_docs"] += 1
            continue
        # BIND criptográfico antes de renderizar: el PDF local debe seguir
        # siendo EXACTAMENTE la extracción de chunks_v2.
        actual_sha = sha256_file(pdf_path)
        if actual_sha != doc["pdf_sha256"]:
            print(
                f"  FAIL {doc['source_file']}: sha256 del PDF cambió "
                f"({actual_sha[:12]} != {doc['pdf_sha256'][:12]})",
                file=sys.stderr,
            )
            stats["failed_docs"] += 1
            continue
        with fitz.open(pdf_path) as pdf:
            for page_index in pending:
                pix = pdf.load_page(page_index - 1).get_pixmap(dpi=RENDER_DPI)
                binary = pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
                path = storage_path(
                    doc["manufacturer"],
                    doc["source_file"],
                    page_index,
                    doc["document_id"],
                )
                local_file = out_dir / Path(path).name
                local_file.write_bytes(binary)
                row = {
                    "tramo": tramo_id,
                    "item_id": item_id_for(doc["document_id"], page_index),
                    "document_id": doc["document_id"],
                    "page_index": page_index,
                    "source_file": doc["source_file"],
                    "manufacturer": doc["manufacturer"],
                    "pdf_sha256": doc["pdf_sha256"],
                    "storage_bucket": STORAGE_BUCKET,
                    "storage_path": path,
                    "local_file": local_file.name,
                    "asset_sha256": sha256_bytes(binary),
                    "bytes": len(binary),
                    "width": pix.width,
                    "height": pix.height,
                    "media_type": "image/jpeg",
                    "render": {"dpi": RENDER_DPI, "jpeg_quality": JPEG_QUALITY},
                    "rendered_at": datetime.now(timezone.utc).isoformat(),
                }
                append_jsonl(manifest_file, row)
                stats["rendered"] += 1
    print(
        f"render {tramo_id}: {stats['rendered']} nuevas, {stats['resumed']} ya "
        f"hechas, {stats['failed_docs']} docs fallidos -> {manifest_file}"
    )
    return dict(stats)


def _render_done(row: dict[str, Any] | None, out_dir: Path) -> bool:
    if row is None:
        return False
    local = out_dir / row["local_file"]
    return local.is_file() and sha256_file(local) == row["asset_sha256"]


# ---------------------------------------------------------------------------
# Fase FIX-COLLISIONS (saneador local; NO toca DB/Storage)
# ---------------------------------------------------------------------------

COLLISION_REPORT_PATH = ROOT / "evals" / "s271_collision_fix_report_v1.json"


def fix_collisions(
    render_dir: Path = RENDER_DIR,
    coverage_path: Path = COVERAGE_PATH,
    report_path: Path = COLLISION_REPORT_PATH,
) -> int:
    """Sanea GLOBALMENTE (todos los tramos) las colisiones de nombre S271b.

    Causa: el esquema viejo ``{slug}_{stem}_pNNN.jpg`` colisiona cuando el
    mismo source_file existe bajo DOS document_ids (revisiones separadas en
    s107) — cada render pisa al otro → sha mismatch → fail-closed en upload.

    Acciones (solo disco local; 0 escrituras a DB/Storage):
      1. dedupe de cada manifest (última fila por item_id manda);
      2. detección global: storage_path reclamado por >1 item_id, o fila cuyo
         fichero local falta o no cuadra con su sha;
      3. borra los ficheros afectados y RE-RENDERIZA esos items con el esquema
         nuevo (docid8); los items no afectados conservan su nombre viejo;
      4. reescribe cada manifest (1 fila válida por item; sha verificado por
         fila contra el fichero en disco);
      5. si un item afectado ya estaba SUBIDO con la MISMA ruta que conserva,
         lo marca en ``reupload_marked.jsonl`` (el upload usará x-upsert=true
         SOLO para ellos); si su ruta cambió, el re-upload es normal y el
         objeto viejo queda listado como huérfano (limpiarlo es decisión del
         orquestador — este saneador no borra nada remoto).
    """
    import fitz

    fitz.TOOLS.mupdf_display_errors(False)
    docs_by_id = {doc["document_id"]: doc for doc in load_worklist(coverage_path)}

    # 1-2. dedupe + detección global de colisiones / filas corruptas.
    tramo_rows: dict[str, dict[str, dict[str, Any]]] = {}
    owners_by_path: dict[str, set[str]] = {}
    for tdir in sorted(p for p in render_dir.iterdir() if p.is_dir()):
        rows = latest_by_item(read_jsonl(tdir / "manifest.jsonl"))
        if not rows:
            continue
        tramo_rows[tdir.name] = rows
        for row in rows.values():
            owners_by_path.setdefault(row["storage_path"], set()).add(row["item_id"])
    collided_paths = {p for p, owners in owners_by_path.items() if len(owners) > 1}

    report: dict[str, Any] = {
        "instrument": "s271_collision_fix_report_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cause": "esquema de nombres sin document_id: mismo source_file bajo "
        "dos document_ids (revisiones s107) colisiona; fix = docid8 en el "
        "nombre (storage_path S271b)",
        "collided_paths": len(collided_paths),
        "tramos": {},
        "reupload_marked": [],
        "orphaned_storage_objects": [],
        "unfixable": [],
    }

    for tramo_id, rows in tramo_rows.items():
        out_dir = render_dir / tramo_id
        duplicate_lines = len(read_jsonl(out_dir / "manifest.jsonl")) - len(rows)
        receipts = read_jsonl(out_dir / "upload_receipts.jsonl")
        receipt_by_item = {r["item_id"]: r for r in receipts if r.get("verified")}

        fix_items = []
        for row in rows.values():
            local = out_dir / row["local_file"]
            broken = (
                row["storage_path"] in collided_paths
                or not local.is_file()
                or sha256_file(local) != row["asset_sha256"]
            )
            if broken:
                fix_items.append(row)
        if not fix_items and not duplicate_lines:
            continue

        # 3. borrar ficheros afectados y re-renderizar con el esquema nuevo.
        for row in fix_items:
            (out_dir / row["local_file"]).unlink(missing_ok=True)
        fixed, unfixable = 0, []
        by_doc: dict[str, list[dict[str, Any]]] = {}
        for row in fix_items:
            by_doc.setdefault(row["document_id"], []).append(row)
        for document_id, doc_rows in sorted(by_doc.items()):
            doc = docs_by_id.get(document_id)
            pdf_path = Path(doc["pdf_path"]) if doc else None
            if (
                doc is None
                or not pdf_path.is_file()
                or sha256_file(pdf_path) != doc["pdf_sha256"]
            ):
                for row in doc_rows:
                    unfixable.append(row["item_id"])
                    rows.pop(row["item_id"], None)  # --render lo re-creará
                continue
            with fitz.open(pdf_path) as pdf:
                for row in sorted(doc_rows, key=lambda r: r["page_index"]):
                    page_index = row["page_index"]
                    pix = pdf.load_page(page_index - 1).get_pixmap(dpi=RENDER_DPI)
                    binary = pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
                    path = storage_path(
                        doc["manufacturer"],
                        doc["source_file"],
                        page_index,
                        document_id,
                    )
                    local_file = out_dir / Path(path).name
                    local_file.write_bytes(binary)
                    new_row = {
                        **row,
                        "storage_path": path,
                        "local_file": local_file.name,
                        "asset_sha256": sha256_bytes(binary),
                        "bytes": len(binary),
                        "width": pix.width,
                        "height": pix.height,
                        "rendered_at": datetime.now(timezone.utc).isoformat(),
                        "fixed_by": "s271_fix_collisions",
                    }
                    rows[row["item_id"]] = new_row
                    fixed += 1

                    # 5. estado de upload del item saneado.
                    receipt = receipt_by_item.get(row["item_id"])
                    if receipt is not None and not receipt_is_current(
                        receipt, new_row
                    ):
                        entry = {
                            "tramo": tramo_id,
                            "item_id": row["item_id"],
                            "old_storage_path": receipt["storage_path"],
                            "new_storage_path": path,
                        }
                        if receipt["storage_path"] == path:
                            append_jsonl(
                                out_dir / "reupload_marked.jsonl",
                                {
                                    "item_id": row["item_id"],
                                    "reason": "objeto subido con binario "
                                    "obsoleto en la MISMA ruta",
                                    "at": datetime.now(timezone.utc).isoformat(),
                                },
                            )
                            report["reupload_marked"].append(entry)
                        else:
                            report["orphaned_storage_objects"].append(entry)

        # 4. reescritura atómica del manifest deduplicado, sha por fila.
        ordered = sorted(
            rows.values(), key=lambda r: (r["document_id"], r["page_index"])
        )
        for row in ordered:
            local = out_dir / row["local_file"]
            if sha256_file(local) != row["asset_sha256"]:
                raise RuntimeError(
                    f"post-fix: sha no cuadra para {row['item_id']} en {tramo_id}"
                )
        tmp = out_dir / "manifest.jsonl.tmp"
        with tmp.open("w", encoding="utf-8") as handle:
            for row in ordered:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp.replace(out_dir / "manifest.jsonl")

        report["unfixable"].extend(unfixable)
        report["tramos"][tramo_id] = {
            "duplicate_lines_removed": duplicate_lines,
            "items_fixed": fixed,
            "items_unfixable": len(unfixable),
            "rows_after": len(ordered),
        }
        print(
            f"fix-collisions {tramo_id}: {fixed} saneados, {duplicate_lines} "
            f"líneas duplicadas fuera, {len(unfixable)} imposibles, "
            f"{len(ordered)} filas finales"
        )

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"fix-collisions: {report['collided_paths']} paths colisionados; "
        f"{len(report['reupload_marked'])} marcados para re-upload con upsert; "
        f"reporte -> {report_path}"
    )
    return 0 if not report["unfixable"] else 1


# ---------------------------------------------------------------------------
# Fase UPLOAD (Supabase Storage; escrituras SOLO con --execute)
# ---------------------------------------------------------------------------

def _supabase(env_path: Path) -> tuple[str, dict[str, str]]:
    from dotenv import load_dotenv

    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    return base_url, {"apikey": key, "Authorization": f"Bearer {key}"}


def public_url(base_url: str, path: str) -> str:
    return f"{base_url}/storage/v1/object/public/{STORAGE_BUCKET}/{path}"


def upload_tramo(
    tramo_id: str,
    *,
    execute: bool,
    env_path: Path = DEFAULT_ENV,
    render_dir: Path = RENDER_DIR,
) -> int:
    import httpx

    manifest = latest_by_item(read_jsonl(manifest_path(tramo_id, render_dir)))
    receipts_file = upload_receipts_path(tramo_id, render_dir)
    # Resume sha-aware: solo cuenta como subido un receipt del binario y la
    # ruta VIGENTES (un re-render/saneo invalida el receipt viejo solo).
    uploaded = {
        r["item_id"]
        for r in read_jsonl(receipts_file)
        if receipt_is_current(r, manifest.get(r["item_id"]))
    }
    # Items marcados por --fix-collisions para RE-SUBIR pisando el objeto
    # existente (x-upsert=true SOLO para ellos, declarado en el receipt).
    marked = {
        m["item_id"]
        for m in read_jsonl(tramo_dir(tramo_id, render_dir) / "reupload_marked.jsonl")
    }
    pending = [
        row for row in manifest.values() if row["item_id"] not in uploaded
    ]
    total_bytes = sum(row["bytes"] for row in pending)
    print(
        f"upload {tramo_id}: {len(manifest)} en manifest, {len(uploaded)} ya "
        f"subidas, {len(pending)} pendientes (~{total_bytes / 1e6:.1f} MB, "
        f"{len(marked & {r['item_id'] for r in pending})} marcadas para re-upload con upsert)"
    )
    if not execute:
        print("preflight (sin --execute): 0 escrituras a Storage.")
        return 0
    if not pending:
        return 0

    base_url, headers = _supabase(env_path)
    out_dir = tramo_dir(tramo_id, render_dir)
    conflicts = 0
    with httpx.Client(timeout=120) as client:
        for number, row in enumerate(pending, 1):
            binary = (out_dir / row["local_file"]).read_bytes()
            if sha256_bytes(binary) != row["asset_sha256"]:
                raise RuntimeError(f"render corrupto en disco: {row['item_id']}")
            quoted = quote(row["storage_path"])
            use_upsert = row["item_id"] in marked
            response = client.post(
                f"{base_url}/storage/v1/object/{STORAGE_BUCKET}/{quoted}",
                headers={
                    **headers,
                    "Content-Type": "image/jpeg",
                    # JAMÁS pisar un objeto existente — salvo los items
                    # explícitamente marcados por --fix-collisions (su objeto
                    # viejo es un binario equivocado que hay que reemplazar).
                    "x-upsert": "true" if use_upsert else "false",
                },
                content=binary,
            )
            reused = False
            if response.status_code in (400, 409) and "exist" in response.text.lower():
                # Objeto ya existente: solo se acepta si es EL MISMO binario.
                existing = client.get(public_url(base_url, quoted))
                if (
                    existing.status_code == 200
                    and sha256_bytes(existing.content) == row["asset_sha256"]
                ):
                    reused = True
                else:
                    conflicts += 1
                    append_jsonl(
                        tramo_dir(tramo_id, render_dir) / "upload_conflicts.jsonl",
                        {
                            "item_id": row["item_id"],
                            "storage_path": row["storage_path"],
                            "error": "objeto existente con binario DISTINTO",
                            "at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    print(
                        f"  CONFLICT {row['storage_path']}: existe con otro "
                        "binario — NO se pisa",
                        file=sys.stderr,
                    )
                    continue
            elif response.status_code != 200:
                response.raise_for_status()

            # Verificación post-subida: el público devuelve EXACTAMENTE el sha.
            check = client.get(public_url(base_url, quoted))
            check.raise_for_status()
            if sha256_bytes(check.content) != row["asset_sha256"]:
                raise RuntimeError(
                    f"sha post-upload no cuadra para {row['item_id']}"
                )
            append_jsonl(
                receipts_file,
                {
                    "item_id": row["item_id"],
                    "document_id": row["document_id"],
                    "page_index": row["page_index"],
                    "storage_path": row["storage_path"],
                    "storage_url": public_url(base_url, row["storage_path"]),
                    "asset_sha256": row["asset_sha256"],
                    "bytes": row["bytes"],
                    "reused_existing": reused,
                    "reuploaded_with_upsert": use_upsert,
                    "verified": True,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            if number % 50 == 0 or number == len(pending):
                print(f"  upload: {number}/{len(pending)}", flush=True)
    print(f"upload {tramo_id}: {len(pending) - conflicts} OK, {conflicts} conflictos")
    return 1 if conflicts else 0


# ---------------------------------------------------------------------------
# Fase LOAD (INSERT idempotente a document_visual_assets; --execute)
# ---------------------------------------------------------------------------

def _load_payloads(
    tramo_id: str, render_dir: Path = RENDER_DIR
) -> list[dict[str, Any]]:
    manifest = latest_by_item(read_jsonl(manifest_path(tramo_id, render_dir)))
    payloads = []
    seen: set[str] = set()
    for receipt in read_jsonl(upload_receipts_path(tramo_id, render_dir)):
        row = manifest.get(receipt["item_id"])
        # Solo receipts del binario/ruta VIGENTES (un receipt obsoleto tras un
        # saneo emparejaría el sha nuevo con la URL vieja — jamás).
        if not receipt_is_current(receipt, row) or receipt["item_id"] in seen:
            continue
        seen.add(receipt["item_id"])
        payloads.append(
            {
                "document_id": row["document_id"],
                "page_index": row["page_index"],
                "page_label": None,
                "asset_sha256": row["asset_sha256"],  # sha REAL del binario
                "storage_url": receipt["storage_url"],
                "media_type": row["media_type"],
                "width": row["width"],
                "height": row["height"],
                "asset_scope": "page_render",
                "visual_role": None,  # lo puebla --classify / --apply-labels
                "technical_utility": "uncertain",  # JAMÁS se sirve sin gate
                "classifier_contract": None,
                "classifier_receipt": None,
                "source_extraction_sha256": row["pdf_sha256"],
            }
        )
    return payloads


def load_tramo(
    tramo_id: str,
    *,
    execute: bool,
    env_path: Path = DEFAULT_ENV,
    render_dir: Path = RENDER_DIR,
) -> int:
    import httpx

    payloads = _load_payloads(tramo_id, render_dir)
    print(f"load {tramo_id}: {len(payloads)} filas subidas+verificadas listas para INSERT")
    if not execute:
        print("preflight (sin --execute): 0 escrituras a la tabla.")
        return 0
    if not payloads:
        return 0
    base_url, headers = _supabase(env_path)
    post_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    inserted = 0
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(payloads), LOAD_BATCH):
            batch = payloads[start : start + LOAD_BATCH]
            response = client.post(
                f"{base_url}/rest/v1/{TARGET_TABLE}",
                headers=post_headers,
                params={"on_conflict": "document_id,page_index,asset_sha256"},
                json=batch,
            )
            response.raise_for_status()
            inserted += len(batch)
            print(f"  load: {inserted}/{len(payloads)}", flush=True)
        # Verificación post-carga: cada clave del tramo debe existir en tabla.
        sample = payloads[:: max(1, len(payloads) // 5)][:5]
        for row in sample:
            check = client.get(
                f"{base_url}/rest/v1/{TARGET_TABLE}",
                headers=headers,
                params={
                    "select": "asset_sha256,technical_utility",
                    "document_id": f"eq.{row['document_id']}",
                    "page_index": f"eq.{row['page_index']}",
                    "asset_sha256": f"eq.{row['asset_sha256']}",
                },
            )
            check.raise_for_status()
            if not check.json():
                raise RuntimeError(
                    f"post-load: fila ausente {row['document_id']}/{row['page_index']}"
                )
    append_jsonl(
        tramo_dir(tramo_id, render_dir) / "load_receipts.jsonl",
        {
            "tramo": tramo_id,
            "rows_sent": len(payloads),
            "at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"load {tramo_id}: OK ({len(payloads)} filas, idempotente)")
    return 0


# ---------------------------------------------------------------------------
# Fase CLASSIFY (contrato heredado v4; pagada SOLO con --execute)
# ---------------------------------------------------------------------------

def measured_per_item_usd(receipts_path: Path = V4_RECEIPTS_PATH) -> tuple[float, str]:
    """Coste por item MEDIDO en el run v4 completo (recibos por batch)."""
    if receipts_path.exists():
        cost = 0.0
        items = 0
        for row in read_jsonl(receipts_path):
            cost += row.get("cost_usd", 0.0)
            items += len(row.get("item_ids", []))
        if items:
            return cost / items, f"v4_receipts_measured_n{items}"
    return FALLBACK_PER_ITEM_USD, "fallback_constant_from_v3"


def classify_items(
    tramo_ids: list[str], render_dir: Path = RENDER_DIR
) -> list[dict[str, Any]]:
    """Items clasificables = subidas verificadas de los tramos pedidos."""
    items: list[dict[str, Any]] = []
    for tramo_id in tramo_ids:
        manifest = latest_by_item(read_jsonl(manifest_path(tramo_id, render_dir)))
        seen: set[str] = set()
        for receipt in read_jsonl(upload_receipts_path(tramo_id, render_dir)):
            row = manifest.get(receipt["item_id"])
            if not receipt_is_current(receipt, row) or receipt["item_id"] in seen:
                continue
            seen.add(receipt["item_id"])
            items.append(
                {
                    "item_id": row["item_id"],
                    "tramo": tramo_id,
                    "document_id": row["document_id"],
                    "page_index": row["page_index"],
                    "source_file": row["source_file"],
                    "manufacturer": row["manufacturer"],
                    "storage_url": receipt["storage_url"],
                    "asset_sha256": row["asset_sha256"],
                    "local_file": str(tramo_dir(tramo_id, render_dir) / row["local_file"]),
                }
            )
    items.sort(key=lambda i: (i["manufacturer"].casefold(), i["source_file"].casefold(), i["page_index"]))
    return items


def classify_preflight(tramo_ids: list[str], render_dir: Path = RENDER_DIR) -> dict[str, Any]:
    items = classify_items(tramo_ids, render_dir)
    done = {row["item_id"] for row in read_jsonl(LABELS_PATH)}
    pending = [item for item in items if item["item_id"] not in done]
    per_item, basis = measured_per_item_usd()
    return {
        "instrument": "s271_render_backfill_classify_preflight",
        "preregistration": str(PREREG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "model": MODEL,
        "reasoning_effort": "none",
        "classifier_contract": CLASSIFIER_CONTRACT,
        "tramos": tramo_ids,
        "items_total": len(items),
        "items_done": len(done & {i["item_id"] for i in items}),
        "items_pending": len(pending),
        "batch_size": BATCH_SIZE,
        "batches_pending": (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE,
        "estimate": {
            "basis": basis,
            "per_item_usd": round(per_item, 8),
            "pending_cost_usd": round(per_item * len(pending), 3),
            "budget_stop_usd": BUDGET_STOP_USD,
        },
        "paid_calls_made": 0,
    }


def _item_binary(item: dict[str, Any], http: Any) -> bytes:
    """Binario del render con verificación sha: local primero, storage después."""
    local = Path(item["local_file"])
    if local.is_file():
        binary = local.read_bytes()
        if sha256_bytes(binary) == item["asset_sha256"]:
            return binary
    response = http.get(item["storage_url"], timeout=60, follow_redirects=True)
    response.raise_for_status()
    binary = response.content
    if sha256_bytes(binary) != item["asset_sha256"]:
        raise RuntimeError(f"binary receipt mismatch for {item['item_id']}")
    return binary


def classify_execute(
    tramo_ids: list[str], env_file: Path, render_dir: Path = RENDER_DIR
) -> int:
    import httpx
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(env_file, override=True)
    plan = classify_preflight(tramo_ids, render_dir)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    items = classify_items(tramo_ids, render_dir)
    done = {row["item_id"] for row in read_jsonl(LABELS_PATH)}
    pending = [item for item in items if item["item_id"] not in done]
    if not pending:
        print("nada pendiente: etiquetado del tramo completo.")
        return 0

    openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    run_cost = 0.0
    failed_batches = 0
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
    with httpx.Client() as http:
        for batch_index, offset in enumerate(range(0, len(pending), BATCH_SIZE), 1):
            if run_cost > BUDGET_STOP_USD:
                print(
                    f"STOP-LINE: ${run_cost:.4f} > ${BUDGET_STOP_USD} — abortando "
                    "(resumible).",
                    file=sys.stderr,
                )
                break
            batch = pending[offset : offset + BATCH_SIZE]
            expected_ids = [item["item_id"] for item in batch]
            try:
                images = [_item_binary(item, http) for item in batch]
                response = openai.responses.create(
                    model=MODEL,
                    reasoning={"effort": "none"},
                    max_output_tokens=1800,
                    input=[{"role": "user", "content": _input_content(batch, images)}],
                )
                labels = parse_labels(response.output_text, expected_ids)
            except Exception as error:  # no-retry: registrar y CONTINUAR
                failed_batches += 1
                append_jsonl(
                    LABEL_FAILURES_PATH,
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "item_ids": expected_ids,
                        "error_type": type(error).__name__,
                        "error": str(error)[:500],
                    },
                )
                print(
                    f"batch {batch_index}/{total_batches}: FAIL "
                    f"({type(error).__name__}) — continuo",
                    flush=True,
                )
                continue
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            cost = (
                usage["input_tokens"] * INPUT_USD_PER_MILLION
                + usage["output_tokens"] * OUTPUT_USD_PER_MILLION
            ) / 1_000_000
            run_cost += cost
            for item, label in zip(batch, labels, strict=True):
                append_jsonl(
                    LABELS_PATH,
                    {
                        **label,
                        "tramo": item["tramo"],
                        "document_id": item["document_id"],
                        "page_index": item["page_index"],
                        "source_file": item["source_file"],
                        "manufacturer": item["manufacturer"],
                        "asset_sha256": item["asset_sha256"],
                        "response_id": response.id,
                    },
                )
            append_jsonl(
                LABEL_RECEIPTS_PATH,
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "response_id": response.id,
                    "model": response.model,
                    "item_ids": expected_ids,
                    "usage": usage,
                    "cost_usd": round(cost, 8),
                },
            )
            if batch_index % 10 == 0 or batch_index == total_batches:
                print(
                    f"batch {batch_index}/{total_batches}: run_cost=${run_cost:.4f}",
                    flush=True,
                )
    print(f"classify: coste del run ${run_cost:.4f}, batches fallidos={failed_batches}")
    return 0 if failed_batches == 0 else 1


# ---------------------------------------------------------------------------
# Fase APPLY-LABELS (upsert a la tabla; --execute)
# ---------------------------------------------------------------------------

def apply_labels(
    *, execute: bool, env_path: Path = DEFAULT_ENV, render_dir: Path = RENDER_DIR
) -> int:
    import httpx

    labels = read_jsonl(LABELS_PATH)
    by_id: dict[str, dict[str, Any]] = {row["item_id"]: row for row in labels}
    manifests: dict[str, dict[str, Any]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    if render_dir.exists():
        for tramo in sorted(p for p in render_dir.iterdir() if p.is_dir()):
            for row in read_jsonl(tramo / "manifest.jsonl"):
                manifests[row["item_id"]] = row
            for row in read_jsonl(tramo / "upload_receipts.jsonl"):
                if row.get("verified"):
                    receipts[row["item_id"]] = row

    payloads: list[dict[str, Any]] = []
    expected_servable = 0
    for item_id, label in sorted(by_id.items()):
        manifest_row = manifests.get(item_id)
        receipt = receipts.get(item_id)
        if manifest_row is None or receipt is None:
            print(f"ABORT: label sin manifest/upload verificado: {item_id}", file=sys.stderr)
            return 2
        if label["asset_sha256"] != manifest_row["asset_sha256"]:
            print(f"ABORT: sha del label no cuadra con manifest: {item_id}", file=sys.stderr)
            return 2
        row = {
            "document_id": manifest_row["document_id"],
            "page_index": manifest_row["page_index"],
            "page_label": None,
            "asset_sha256": manifest_row["asset_sha256"],
            "storage_url": receipt["storage_url"],
            "media_type": manifest_row["media_type"],
            "width": manifest_row["width"],
            "height": manifest_row["height"],
            "asset_scope": "page_render",
            "visual_role": label["visual_role"],
            "technical_utility": label["technical_utility"],
            "classifier_contract": CLASSIFIER_CONTRACT,
            "classifier_receipt": {
                "instrument": "s271_render_backfill",
                "labels_file": str(LABELS_PATH.relative_to(ROOT)).replace("\\", "/"),
                "preregistration": str(PREREG_PATH.relative_to(ROOT)).replace("\\", "/"),
                "model": MODEL,
                "item_id": item_id,
                "response_id": label.get("response_id"),
                "confidence": label.get("confidence"),
                "has_legible_technical_visual": label.get("has_legible_technical_visual"),
                "reason": label.get("reason"),
                "binary_asset_sha256": label["asset_sha256"],
            },
            "source_extraction_sha256": manifest_row["pdf_sha256"],
        }
        if (
            row["technical_utility"] == "useful"
            and row["visual_role"] in SERVABLE_ROLES
        ):
            expected_servable += 1
        payloads.append(row)

    print(
        f"apply-labels: {len(payloads)} labels listos "
        f"({expected_servable} servibles esperados)"
    )
    if not execute:
        print("preflight (sin --execute): 0 escrituras a la tabla.")
        return 0
    if not payloads:
        return 0
    base_url, headers = _supabase(env_path)
    post_headers = {
        **headers,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    applied = 0
    with httpx.Client(timeout=60) as client:
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
            print(f"  apply-labels: {applied}/{len(payloads)}", flush=True)
        # Verificación: servibles del contrato s271 en tabla == esperados.
        check = client.head(
            f"{base_url}/rest/v1/{TARGET_TABLE}",
            headers={**headers, "Prefer": "count=exact"},
            params={
                "technical_utility": "eq.useful",
                "visual_role": f"in.({','.join(sorted(SERVABLE_ROLES))})",
                "classifier_contract": f"eq.{CLASSIFIER_CONTRACT}",
                "limit": "1",
            },
        )
        check.raise_for_status()
        servable = int(check.headers["content-range"].rsplit("/", 1)[1])
    print(f"apply-labels: servibles s271 en tabla={servable} / esperados={expected_servable}")
    if servable != expected_servable:
        print("ABORT: count servible no cuadra.", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# GATE SAMPLE (patrón v4: muestra fresca congelada para spot-check humano)
# ---------------------------------------------------------------------------

def gate_sample_rows(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serving = [
        label
        for label in labels
        if label["technical_utility"] == "useful"
        and label["visual_role"] in SERVABLE_ROLES
    ]

    def score(label: dict[str, Any]) -> str:
        value = f"{GATE_SAMPLE_SEED}|{label['document_id']}|{label['page_index']}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    return sorted(serving, key=score)[:GATE_SAMPLE_N]


def gate_sample(
    download_dir: Path | None,
    render_dir: Path = RENDER_DIR,
    exclude_tramos: tuple[str, ...] = (),
    out_path: Path = GATE_SAMPLE_PATH,
) -> int:
    """Congela la muestra del gate. ``exclude_tramos`` sirve para el gate del
    'resto': muestra FRESCA solo del serving-set no-piloto (prereg S271)."""
    labels = [
        row
        for row in read_jsonl(LABELS_PATH)
        if row.get("tramo") not in set(exclude_tramos)
    ]
    if not labels:
        print("ABORT: no hay labels s271 aún (corre --classify primero).", file=sys.stderr)
        return 2
    receipts: dict[str, dict[str, Any]] = {}
    if render_dir.exists():
        for tramo in sorted(p for p in render_dir.iterdir() if p.is_dir()):
            for row in read_jsonl(tramo / "upload_receipts.jsonl"):
                receipts[row["item_id"]] = row
    sample = gate_sample_rows(labels)
    rows = []
    for index, label in enumerate(sample, 1):
        receipt = receipts.get(label["item_id"], {})
        rows.append(
            {
                "sample_id": f"s271_gate_{index:02d}",
                "item_id": label["item_id"],
                "tramo": label.get("tramo"),
                "document_id": label["document_id"],
                "page_index": label["page_index"],
                "source_file": label["source_file"],
                "manufacturer": label["manufacturer"],
                "storage_url": receipt.get("storage_url"),
                "asset_sha256": label["asset_sha256"],
                "prediction": {
                    "technical_utility": label["technical_utility"],
                    "visual_role": label["visual_role"],
                    "confidence": label["confidence"],
                    "reason": label["reason"],
                },
                "orchestrator_verdict": None,  # lo rellena el spot-check humano
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    payload = {
        "instrument": "s271_visual_utility_gate_sample",
        "status": "FROZEN_FOR_HUMAN_SPOT_CHECK",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": str(PREREG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "seed": GATE_SAMPLE_SEED,
        "n": len(rows),
        "excluded_tramos": sorted(exclude_tramos),
        "labels_total": len(labels),
        "serving_set_total": sum(
            1
            for l in labels
            if l["technical_utility"] == "useful" and l["visual_role"] in SERVABLE_ROLES
        ),
        "criteria": {"precision_gte": 0.95, "zero_cover_or_marketing": True},
        "sample_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "rows": rows,
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"gate sample: {len(rows)} items -> {out_path}")
    if download_dir is not None:
        import httpx

        download_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client() as http:
            for row in rows:
                response = http.get(row["storage_url"], timeout=60, follow_redirects=True)
                response.raise_for_status()
                if sha256_bytes(response.content) != row["asset_sha256"]:
                    raise RuntimeError(f"binary receipt mismatch for {row['item_id']}")
                name = f"{row['sample_id']}_{row['prediction']['visual_role']}.jpg"
                (download_dir / name).write_bytes(response.content)
        print(f"renders: {len(rows)} descargados en {download_dir}")
    return 0


# ---------------------------------------------------------------------------
# PLAN + PREREG
# ---------------------------------------------------------------------------

def build_plan() -> dict[str, Any]:
    docs = load_worklist()
    tramos = build_tramos(docs)
    per_item, basis = measured_per_item_usd()
    total_pages = sum(tramo_pages(d) for d in tramos.values())
    rows = []
    for tramo_id, tramo_docs in tramos.items():
        pages = tramo_pages(tramo_docs)
        rows.append(
            {
                "tramo": tramo_id,
                "manufacturers": sorted(
                    {d["manufacturer"] for d in tramo_docs}, key=str.casefold
                ),
                "documents": len(tramo_docs),
                "pages": pages,
                "storage_estimate_mb": round(pages * MEASURED_JPEG_BYTES_PER_PAGE / 1e6, 1),
                "classify_estimate_usd": round(pages * per_item, 3),
            }
        )
    return {
        "instrument": "s271_render_backfill_plan",
        "worklist": str(COVERAGE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "render": {"dpi": RENDER_DPI, "jpeg_quality": JPEG_QUALITY},
        "storage": {
            "bucket": STORAGE_BUCKET,
            "path_pattern": "{manufacturer_slug}/{manufacturer_slug}_{stem}_pNNN.jpg",
        },
        "pilot": {
            "tramo": PILOT_TRAMO_ID,
            "min_pages": PILOT_MIN_PAGES,
            "stop_for_gate": "OBLIGATORIO antes de 'resto' (gate-sample + spot-check)",
        },
        "totals": {
            "documents": len(docs),
            "pages": total_pages,
            "storage_estimate_gb": round(
                total_pages * MEASURED_JPEG_BYTES_PER_PAGE / 1e9, 2
            ),
            "classify_estimate_usd": round(total_pages * per_item, 2),
            "classify_budget_stop_usd": BUDGET_STOP_USD,
            "per_item_usd_basis": basis,
        },
        "tramos": rows,
    }


def write_prereg(plan: dict[str, Any]) -> None:
    """Prereg YAML del presupuesto (emitido, legible, sin dependencia de yaml)."""
    lines = [
        "# Preregistro S271 — render backfill visual por tramos (generado por",
        "# scripts/s271_render_backfill.py --write-prereg; NO editar a mano).",
        "instrument: s271_render_backfill_prereg_v1",
        f"created_at: '{datetime.now(timezone.utc).isoformat()}'",
        f"worklist: {plan['worklist']}",
        "decision: 'Alberto S271: procesar el 69% de paginas de chunks_v2 sin asset legacy'",
        "render:",
        f"  dpi: {RENDER_DPI}",
        f"  jpeg_quality: {JPEG_QUALITY}",
        "  cost_usd: 0  # local, sin llamadas",
        "storage:",
        f"  bucket: {STORAGE_BUCKET}",
        "  path_pattern: '{manufacturer_slug}/{manufacturer_slug}_{stem}_pNNN.jpg'",
        "  upsert: false  # un conflicto JAMAS pisa un objeto existente",
        f"  estimate_gb: {plan['totals']['storage_estimate_gb']}",
        "  quota_note: 'CONSIDERACION PARA ALBERTO: ~2-3 GB nuevos en Supabase",
        "    Storage (medido 255 KB/pagina, n=20). Verificar cuota del proyecto",
        "    antes del tramo resto; el piloto (~0.13 GB) es inocuo.'",
        "classification:",
        f"  model: {MODEL}",
        "  contract: contrato heredado v4 (v3/v1, reasoning none, batches 10, no-retry)",
        f"  classifier_contract: {CLASSIFIER_CONTRACT}",
        f"  per_item_usd_basis: {plan['totals']['per_item_usd_basis']}",
        f"  estimate_usd: {plan['totals']['classify_estimate_usd']}",
        f"  budget_stop_usd: {BUDGET_STOP_USD}  # techo duro",
        "load:",
        "  table: document_visual_assets",
        "  technical_utility: uncertain  # JAMAS se sirve sin clasificar+gate",
        "  idempotent: on_conflict=document_id,page_index,asset_sha256",
        "pilot:",
        f"  tramo: {PILOT_TRAMO_ID}",
        f"  min_pages: {PILOT_MIN_PAGES}",
        "  stop_for_gate: obligatorio  # gate-sample 60 + spot-check antes del resto",
        "gate:",
        f"  sample_n: {GATE_SAMPLE_N}",
        f"  seed: '{GATE_SAMPLE_SEED}'",
        "  criteria: {precision_gte: 0.95, zero_cover_or_marketing: true}",
        f"totals: {{documents: {plan['totals']['documents']}, pages: {plan['totals']['pages']}}}",
        "tramos:",
    ]
    for row in plan["tramos"]:
        lines.append(
            f"  - {{tramo: {row['tramo']}, documents: {row['documents']}, "
            f"pages: {row['pages']}, storage_mb: {row['storage_estimate_mb']}, "
            f"classify_usd: {row['classify_estimate_usd']}}}"
        )
    PREREG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"prereg: {PREREG_PATH}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--apply-labels", action="store_true")
    parser.add_argument("--gate-sample", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument(
        "--fix-collisions",
        action="store_true",
        help="Saneador global S271b (solo disco local): dedupe de manifests, "
        "re-render de items colisionados/corruptos con el esquema docid8, "
        "marcado de re-uploads.",
    )
    parser.add_argument("--tramo", type=str, default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--env-file", type=Path, default=None,
                        help="Env con OPENAI_API_KEY para --classify --execute")
    parser.add_argument("--download-dir", type=Path, default=None)
    parser.add_argument(
        "--gate-exclude-tramo",
        action="append",
        default=None,
        metavar="TRAMO",
        help="--gate-sample: excluye labels de estos tramos (gate FRESCO del "
        "resto sin re-muestrear el piloto).",
    )
    parser.add_argument(
        "--gate-out",
        type=Path,
        default=GATE_SAMPLE_PATH,
        help="--gate-sample: ruta de salida (para no pisar el gate del piloto).",
    )
    args = parser.parse_args()

    phases = [
        args.render, args.upload, args.load, args.classify,
        args.apply_labels, args.gate_sample, args.write_prereg,
        args.fix_collisions,
    ]
    if sum(phases) > 1:
        print("ABORT: una fase por invocación.", file=sys.stderr)
        return 2

    if args.fix_collisions:
        return fix_collisions()
    if args.write_prereg:
        plan = build_plan()
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        write_prereg(plan)
        return 0
    if args.gate_sample:
        return gate_sample(
            args.download_dir,
            exclude_tramos=tuple(args.gate_exclude_tramo or ()),
            out_path=args.gate_out,
        )
    if args.apply_labels:
        return apply_labels(execute=args.execute, env_path=args.env)

    if args.render or args.upload or args.load or args.classify:
        if not args.tramo:
            print("ABORT: la fase requiere --tramo <id|resto>.", file=sys.stderr)
            return 2
        tramos = select_tramos(build_tramos(load_worklist()), args.tramo)
        if args.render:
            for tramo_id, docs in tramos.items():
                render_tramo(tramo_id, docs)
            return 0
        if args.upload:
            status = 0
            for tramo_id in tramos:
                status |= upload_tramo(tramo_id, execute=args.execute, env_path=args.env)
            return status
        if args.load:
            status = 0
            for tramo_id in tramos:
                status |= load_tramo(tramo_id, execute=args.execute, env_path=args.env)
            return status
        if args.classify:
            if args.execute:
                if args.env_file is None:
                    print("ABORT: --classify --execute requiere --env-file.", file=sys.stderr)
                    return 2
                return classify_execute(list(tramos), args.env_file)
            print(json.dumps(classify_preflight(list(tramos)), indent=2, ensure_ascii=False))
            print("preflight OK — 0 llamadas hechas. El --execute lo corre el orquestador.")
            return 0

    plan = build_plan()
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
