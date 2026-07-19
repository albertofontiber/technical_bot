#!/usr/bin/env python3
"""Probe S271 ($0, GET-only): cobertura de PDFs locales para el backfill visual.

Para las páginas de ``chunks_v2`` SIN activo en ``document_visual_assets``
(el 69% del corpus visual), localiza el PDF fuente local bajo MANUALS_DIR
(default ``./Manuales_ES``; se pueden pasar varias raíces) y lo VINCULA
criptográficamente: un PDF solo cuenta como localizado-verificado si su
sha256 == ``chunks_v2.extraction_sha256`` (que ES el sha256 del PDF fuente,
migración 006 / ``src/reingest/extraction_derivation.py``). El match por
nombre sin sha es un estado aparte (``name_only_sha_mismatch``) y NO entra
en el worklist de render.

Salida: ``evals/s271_pdf_coverage_v1.json`` con documentos/páginas cubribles
vs PDFs no localizados (lista explícita) + el worklist por documento (páginas
sin asset, ruta local, sha verificado) que consume
``scripts/s271_render_backfill.py``.

Contrato duro: 0 escrituras a DB/Storage; 0 llamadas a modelos. Solo GET a
Supabase REST y lectura de ficheros locales.

Uso (desde un checkout con la carpeta de manuales):
  python scripts/s271_pdf_coverage_probe.py                       # MANUALS_DIR o ./Manuales_ES
  python scripts/s271_pdf_coverage_probe.py --manuals-root Manuales_ES \
      --manuals-root Manuales_Notifier ...
  python scripts/s271_pdf_coverage_probe.py --all-manuales        # + hermanas Manuales_*
  python scripts/s271_pdf_coverage_probe.py --hash-all            # índice sha completo
                                                                  # (caza PDFs renombrados)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = ROOT / ".env"
DEFAULT_OUTPUT = ROOT / "evals" / "s271_pdf_coverage_v1.json"
# Cache de hashes (ruta+size+mtime → sha256) para re-runs baratos. Vive en
# logs/ (gitignored): es un artefacto local, no fuente.
DEFAULT_HASH_CACHE = ROOT / "logs" / "s271_pdf_sha_cache.json"

CHUNKS_TABLE = "chunks_v2"
ASSETS_TABLE = "document_visual_assets"
PAGE_SIZE = 1_000


# ---------------------------------------------------------------------------
# Supabase GET-only
# ---------------------------------------------------------------------------

def _headers(env_path: Path) -> tuple[str, dict[str, str]]:
    load_dotenv(env_path, override=True)
    base_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    return base_url, {"apikey": service_key, "Authorization": f"Bearer {service_key}"}


def _stream_rows(
    client: httpx.Client,
    *,
    url: str,
    headers: dict[str, str],
    select: str,
) -> list[dict[str, Any]]:
    """Keyset-pagination por id (mismo patrón que el audit S190). Solo GET."""
    rows: list[dict[str, Any]] = []
    last_id: str | None = None
    while True:
        params = {"select": f"id,{select}", "limit": str(PAGE_SIZE), "order": "id.asc"}
        if last_id is not None:
            params["id"] = f"gt.{last_id}"
        response = client.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        page = response.json()
        if not page:
            return rows
        rows.extend(page)
        last_id = page[-1]["id"]
        if len(page) < PAGE_SIZE:
            return rows


# ---------------------------------------------------------------------------
# Localización de PDFs
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Nombre comparable: sin .pdf, casefold, separadores colapsados a '_'."""
    stem = name.strip()
    if stem.casefold().endswith(".pdf"):
        stem = stem[:-4]
    return re.sub(r"[\s_\-]+", "_", stem.strip().casefold())


def loose_name(name: str) -> str:
    """Variante laxa: solo [a-z0-9] (caza renombrados por espacios/guiones)."""
    return re.sub(r"[^a-z0-9]+", "", normalize_name(name))


def scan_pdfs(roots: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    pdfs: list[Path] = []
    for root in roots:
        if not root.is_dir():
            print(f"AVISO: raíz de manuales inexistente: {root}", file=sys.stderr)
            continue
        for path in sorted(root.rglob("*.pdf")):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                pdfs.append(resolved)
    return pdfs


class HashCache:
    """sha256 por (ruta, size, mtime_ns) persistido en JSON."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, dict[str, Any]] = {}
        self.dirty = False
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = {}

    def sha256(self, pdf: Path) -> str:
        stat = pdf.stat()
        key = str(pdf)
        entry = self.data.get(key)
        if (
            entry
            and entry.get("size") == stat.st_size
            and entry.get("mtime_ns") == stat.st_mtime_ns
        ):
            return entry["sha256"]
        digest = hashlib.sha256()
        with pdf.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        value = digest.hexdigest()
        self.data[key] = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": value,
        }
        self.dirty = True
        return value

    def save(self) -> None:
        if not self.dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8"
        )


def locate_documents(
    documents: list[dict[str, Any]],
    pdfs: list[Path],
    cache: HashCache,
    hash_all: bool,
) -> None:
    """Anota cada doc (in-place) con status / pdf_path / pdf_sha256.

    Estados:
      * ``located_sha_verified``   sha256(pdf) == extraction_sha256 (BIND real);
      * ``name_only_sha_mismatch`` hay candidato(s) por nombre pero ningún sha
        cuadra (otra revisión del manual → NO renderizable);
      * ``not_found``              sin candidato.
    """
    strict_index: dict[str, list[Path]] = defaultdict(list)
    loose_index: dict[str, list[Path]] = defaultdict(list)
    for pdf in pdfs:
        strict_index[normalize_name(pdf.name)].append(pdf)
        loose_index[loose_name(pdf.name)].append(pdf)

    sha_index: dict[str, Path] = {}
    if hash_all:
        for number, pdf in enumerate(pdfs, 1):
            sha_index.setdefault(cache.sha256(pdf), pdf)
            if number % 200 == 0:
                print(f"hash-all: {number}/{len(pdfs)} PDFs", flush=True)
        cache.save()

    for doc in documents:
        expected_sha = doc["extraction_sha256"]
        if not expected_sha:
            # >1 extraction_sha256 para el mismo document_id: sin bind único
            # posible — se declara, no se adivina.
            doc["status"] = "ambiguous_extraction"
            continue
        source_file = doc["source_file"]
        candidates = list(strict_index.get(normalize_name(source_file), []))
        for path in loose_index.get(loose_name(source_file), []):
            if path not in candidates:
                candidates.append(path)

        verified: Path | None = None
        candidate_receipts: list[dict[str, str]] = []
        for path in candidates:
            sha = cache.sha256(path)
            candidate_receipts.append({"path": str(path), "sha256": sha})
            if sha == expected_sha and verified is None:
                verified = path
        if verified is None and expected_sha in sha_index:
            verified = sha_index[expected_sha]  # renombrado: cazado por sha

        if verified is not None:
            doc["status"] = "located_sha_verified"
            doc["pdf_path"] = str(verified)
            doc["pdf_sha256"] = expected_sha
        elif candidates:
            doc["status"] = "name_only_sha_mismatch"
            doc["candidates"] = candidate_receipts
        else:
            doc["status"] = "not_found"
    cache.save()


def pdf_page_counts(documents: list[dict[str, Any]]) -> None:
    """page_count real del PDF verificado (fitz) para acotar páginas cubribles."""
    import fitz  # PyMuPDF — ya en el stack de ingesta

    for doc in documents:
        if doc.get("status") != "located_sha_verified":
            continue
        try:
            with fitz.open(doc["pdf_path"]) as pdf:
                doc["pdf_page_count"] = pdf.page_count
        except Exception as error:
            doc["status"] = "pdf_unreadable"
            doc["error"] = f"{type(error).__name__}: {error}"


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------

def build_documents(
    chunk_rows: list[dict[str, Any]], asset_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    covered = {(str(r["document_id"]), int(r["page_index"])) for r in asset_rows}
    by_doc: dict[str, dict[str, Any]] = {}
    for row in chunk_rows:
        document_id = str(row.get("document_id") or "")
        page_number = row.get("page_number")
        source_file = str(row.get("source_file") or "").strip()
        if not document_id or not isinstance(page_number, int) or not source_file:
            continue  # mismos filtros de consumo que el bridge S190/S269
        doc = by_doc.setdefault(
            document_id,
            {
                "document_id": document_id,
                "source_files": set(),
                "manufacturers": set(),
                "extraction_sha256s": set(),
                "pages": set(),
            },
        )
        doc["source_files"].add(source_file)
        doc["manufacturers"].add(
            str(row.get("manufacturer") or "unknown").strip() or "unknown"
        )
        extraction = str(row.get("extraction_sha256") or "").strip()
        if extraction:
            doc["extraction_sha256s"].add(extraction)
        doc["pages"].add(page_number)

    documents: list[dict[str, Any]] = []
    totals = {
        "document_pages": 0,
        "pages_with_asset": 0,
        "pages_without_asset": 0,
    }
    for document_id in sorted(by_doc):
        raw = by_doc[document_id]
        pages = sorted(raw["pages"])
        uncovered = [p for p in pages if (document_id, p) not in covered]
        totals["document_pages"] += len(pages)
        totals["pages_with_asset"] += len(pages) - len(uncovered)
        totals["pages_without_asset"] += len(uncovered)
        documents.append(
            {
                "document_id": document_id,
                "source_file": sorted(raw["source_files"])[0],
                "source_files_distinct": len(raw["source_files"]),
                "manufacturer": sorted(raw["manufacturers"])[0],
                "extraction_sha256": (
                    sorted(raw["extraction_sha256s"])[0]
                    if len(raw["extraction_sha256s"]) == 1
                    else None
                ),
                "extraction_sha256_distinct": len(raw["extraction_sha256s"]),
                "pages_total": len(pages),
                "pages_uncovered": len(uncovered),
                "uncovered_pages": uncovered,
            }
        )
    return documents, totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument(
        "--manuals-root",
        type=Path,
        action="append",
        default=None,
        help="Raíz de manuales (repetible). Default: $MANUALS_DIR o ./Manuales_ES",
    )
    parser.add_argument(
        "--all-manuales",
        action="store_true",
        help="Añade todas las carpetas hermanas Manuales_* de cada raíz dada.",
    )
    parser.add_argument("--hash-all", action="store_true",
                        help="Índice sha256 de TODOS los PDFs (caza renombrados).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--hash-cache", type=Path, default=DEFAULT_HASH_CACHE)
    args = parser.parse_args()

    roots = args.manuals_root or [
        Path(os.environ.get("MANUALS_DIR") or "Manuales_ES")
    ]
    if args.all_manuales:
        extended: list[Path] = []
        for root in roots:
            parent = root.resolve().parent
            for sibling in sorted(parent.glob("Manuales_*")):
                if sibling.is_dir() and sibling not in extended:
                    extended.append(sibling)
            if root.resolve() not in [p.resolve() for p in extended]:
                extended.append(root)
        roots = extended

    base_url, headers = _headers(args.env)
    with httpx.Client() as client:
        print("snapshot GET-only: chunks_v2 ...", flush=True)
        chunk_rows = _stream_rows(
            client,
            url=f"{base_url}/rest/v1/{CHUNKS_TABLE}",
            headers=headers,
            select="document_id,page_number,source_file,manufacturer,extraction_sha256",
        )
        print(f"  chunks_v2: {len(chunk_rows)} filas", flush=True)
        asset_rows = _stream_rows(
            client,
            url=f"{base_url}/rest/v1/{ASSETS_TABLE}",
            headers=headers,
            select="document_id,page_index",
        )
        print(f"  {ASSETS_TABLE}: {len(asset_rows)} filas", flush=True)

    documents, totals = build_documents(chunk_rows, asset_rows)
    need = [doc for doc in documents if doc["pages_uncovered"] > 0]

    pdfs = scan_pdfs(roots)
    print(f"PDFs locales bajo {len(roots)} raíz(es): {len(pdfs)}", flush=True)
    cache = HashCache(args.hash_cache)
    locate_documents(need, pdfs, cache, hash_all=args.hash_all)
    pdf_page_counts(need)

    # Páginas cubribles = sin asset ∧ doc sha-verificado ∧ dentro del rango
    # real del PDF (una página fuera de rango señala paginación divergente y
    # NO se renderiza a ciegas).
    coverage = Counter()
    renderable_by_manufacturer: Counter = Counter()
    for doc in need:
        status = doc.get("status", "not_found")
        coverage[f"documents_{status}"] += 1
        if status == "located_sha_verified":
            page_count = doc.get("pdf_page_count", 0)
            uncovered = doc.pop("uncovered_pages")  # = renderable si está en rango
            in_range = [p for p in uncovered if 1 <= p <= page_count]
            doc["renderable_pages"] = in_range
            doc["pages_out_of_pdf_range"] = len(uncovered) - len(in_range)
            coverage["pages_renderable"] += len(in_range)
            coverage["pages_out_of_pdf_range"] += doc["pages_out_of_pdf_range"]
            renderable_by_manufacturer[doc["manufacturer"]] += len(in_range)
        else:
            coverage[f"pages_blocked_{status}"] += len(doc["uncovered_pages"])

    payload = {
        "instrument": "s271_pdf_coverage_probe_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "writes": 0,
            "paid_model_calls": 0,
            "verification": "sha256(pdf_local) == chunks_v2.extraction_sha256",
        },
        "inputs": {
            "chunks_table": CHUNKS_TABLE,
            "assets_table": ASSETS_TABLE,
            "manuals_roots": [str(r) for r in roots],
            "local_pdfs_scanned": len(pdfs),
            "hash_all": args.hash_all,
        },
        "totals": {
            "chunks_v2_rows": len(chunk_rows),
            "documents": len(documents),
            "documents_with_uncovered_pages": len(need),
            **totals,
        },
        "coverage": dict(sorted(coverage.items())),
        "renderable_pages_by_manufacturer": dict(
            sorted(renderable_by_manufacturer.items())
        ),
        "not_found": sorted(
            (
                {
                    "document_id": d["document_id"],
                    "source_file": d["source_file"],
                    "manufacturer": d["manufacturer"],
                    "pages_uncovered": d["pages_uncovered"],
                }
                for d in need
                if d.get("status") == "not_found"
            ),
            key=lambda row: (row["manufacturer"].casefold(), row["source_file"].casefold()),
        ),
        "name_only_sha_mismatch": sorted(
            (
                {
                    "document_id": d["document_id"],
                    "source_file": d["source_file"],
                    "manufacturer": d["manufacturer"],
                    "expected_sha256": d["extraction_sha256"],
                    "candidates": d.get("candidates", []),
                    "pages_uncovered": d["pages_uncovered"],
                }
                for d in need
                if d.get("status") == "name_only_sha_mismatch"
            ),
            key=lambda row: (row["manufacturer"].casefold(), row["source_file"].casefold()),
        ),
        "documents": need,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"totals": payload["totals"], "coverage": payload["coverage"]},
                     indent=2, ensure_ascii=False))
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
