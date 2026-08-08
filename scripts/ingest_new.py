#!/usr/bin/env python3
"""Alta de manuales NUEVOS por lote — driver de las etapas A2+B para un canal (frente 7).

Qué cierra: el pipeline de re-ingesta NO crea filas en `documents` (las altas
históricas fueron backfills post-hoc, ver notes de s65 en la propia tabla) y
`resolve_document_id` solo ENLAZA filas existentes. Este driver hace el ciclo
completo para PDFs nuevos ya colocados en su carpeta de canal:

    GATES  → integridad PDF, exclusión de tipos (certificados/homologaciones),
             sidecar obligatorio (identidad autoritativa), dedup por SHA-256
             contra store + documents
    DRY    → informe de qué se ingestaría + coste estimado (LlamaParse/página);
             0 API de pago y 0 escrituras (sí consulta Supabase para el dedup)
             — es el modo por DEFECTO
    COMMIT → A2 extracción LlamaParse → alta de la fila `documents` (con sha
             real; ANTES de indexar, para que el enlace por sha funcione) →
             B completo (contextualize+embed+index) → verificación en DB

Convenciones (mismas que el corpus vivo):
  - El corpus master vive en la carpeta OneDrive (data-root); el código corre
    desde el checkout. Los paths que se escriben en el store son ABSOLUTOS para
    que el sidecar (Capa B) resuelva la carpeta real del canal.
  - Canal = carpeta `Manuales_<canal>` declarada en config/portal.yaml; la
    identidad sale de su `_metadata.json` (equipo del PIM), fail-closed aquí
    (sin entrada de sidecar NO se ingesta — el fallo-abierto del B5 es para el
    corpus legado, no para altas nuevas).

Uso:
    python scripts/ingest_new.py --canal Kidde --data-root "<carpeta OneDrive>"
    python scripts/ingest_new.py --canal Kidde --data-root ... --commit
    (opcional) --solo "MI_KIDDE_*.pdf" para acotar el lote por glob

El recibo JSON queda en <data-root>/logs/ingest_new_<UTC>_<canal>.json.
Tras un commit exitoso: el corpus CAMBIA → la siguiente fila del assessment
debe anotar el corpus nuevo (freeze per-eval, DEC-023/071e).
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

# Imports del pipeline vivo (chdir al ROOT del código como efecto de import; los
# paths de datos son absolutos, así que es inocuo).
from src.reingest.extract import llamaparse_extract, CREDITS_PER_PAGE  # noqa: E402
from src.reingest.pipeline import process_file, DEFAULT_CONFIG  # noqa: E402
from src.reingest.metadata import detect_document_metadata  # noqa: E402
from src.reingest import sidecar  # noqa: E402
from src.ingestion.supabase_client import SupabaseHTTP  # noqa: E402

EXTRACT_MODE = "parse_page_with_agent"
EXTRACT_MODEL = "anthropic-sonnet-4.5"  # config_slug() → agent_anthropic-sonnet-45

# Tipos que NO se ingestan (certificados / homologaciones / declaraciones).
# Prefijos (taxonomía Casmar/portal, espejo del cruce s314) + palabras; la
# primera defensa es no descargarlos. La exclusión SIEMPRE se lista, nunca es
# silenciosa. (Dúo s314, Sol: los prefijos CE_/C_/DOP_ faltaban; el substring
# "_doc_" era sobre-inclusivo y se retira — "c_" cubre los C_*_DoC.)
_EXCLUIR_PREFIJOS = ("h_dop", "h_cpr", "h_ce", "ce_", "c_", "dop_")
_EXCLUIR_TOKENS = ("declaracion", "declaration", "certificado", "certificate",
                   "homologacion", "incert")


def _tipo_excluido(filename_lower: str) -> bool:
    return (filename_lower.startswith(_EXCLUIR_PREFIJOS)
            or any(tok in filename_lower for tok in _EXCLUIR_TOKENS))


# tipo del sidecar → doc_type canónico de `documents`. El regex de B5
# (_detect_doc_type) no reconoce la nomenclatura del portal (MI_/G_INST_/HD_…)
# y metadata.py está sha-pineada por recibos s116/s117 (pre-flight s314) → el
# mapeo vive AQUÍ y solo alimenta la fila de documents; el doc_type de los
# chunks queda como lo deje B5 (NULL para estos nombres — igual que el corpus
# existente; limitación declarada, no silenciosa).
_TIPO_SIDECAR_A_DOC_TYPE = {
    "manual instalación": "instalacion", "manual instalacion": "instalacion",
    "manual usuario": "usuario", "manual programación": "programacion",
    "manual programacion": "programacion", "guía instalación": "instalacion",
    "guia instalacion": "instalacion", "guía uso": "usuario", "guia uso": "usuario",
    "guía rápida": "guia_rapida", "guia rapida": "guia_rapida",
    "datasheet": "datasheet", "nota técnica": "comunicacion_tecnica",
    "nota tecnica": "comunicacion_tecnica",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _document_family(filename: str) -> str:
    """Normalización de familia: filename sin extensión, separadores → espacios,
    minúsculas, y SIN los tokens de fecha (AAAAMM) ni el hash de media del CMS
    (sufijo hex de 4) — el contrato de `documents.document_family` ignora
    rev/fecha para que las revisiones del mismo manual compartan familia
    (dúo s314, Sol; migrations/001_document_management.sql)."""
    base = os.path.splitext(filename)[0].lower()
    for sep in ("-", "_", ".", "  "):
        base = base.replace(sep, " ")
    tokens = base.split()
    if tokens and re.fullmatch(r"[0-9a-f]{4}", tokens[-1]):
        tokens = tokens[:-1]  # hash de media del CMS (Akeneo)
    tokens = [t for t in tokens if not re.fullmatch(r"20\d{4}|20\d{2}", t)]
    return " ".join(tokens)


def _paginas(path: Path) -> int | None:
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            return doc.page_count
    except Exception:
        return None


def gates(canal: str, data_root: Path, solo: str | None) -> tuple[list[dict], list[dict]]:
    """Valida el lote y devuelve (candidatos, excluidos). Fail-closed en todo lo
    que compromete identidad o dinero; las exclusiones de tipo se LISTAN."""
    carpeta = data_root / f"Manuales_{canal}"
    if not carpeta.is_dir():
        raise SystemExit(f"GATE: no existe {carpeta} — ¿data-root correcto? El corpus vive en OneDrive.")

    canales = (sidecar._config().get("channels", []) or [])
    if canal not in canales:
        raise SystemExit(f"GATE: canal {canal!r} no declarado en config/portal.yaml (canales: {canales})")

    sidecar.reload()
    indice = sidecar._sidecar_index(str(carpeta))
    if not indice:
        raise SystemExit(f"GATE: {carpeta / '_metadata.json'} ausente o vacío — la identidad del lote es obligatoria.")

    store = data_root / "data" / "extraction" / DEFAULT_CONFIG
    if not store.is_dir():
        raise SystemExit(f"GATE: no existe el store {store} — ¿data-root correcto?")

    sb = SupabaseHTTP()
    candidatos, excluidos = [], []
    pdfs = sorted(p for p in carpeta.glob("*.pdf"))
    if solo:
        pdfs = [p for p in pdfs if fnmatch.fnmatch(p.name.lower(), solo.lower())]
    for pdf in pdfs:
        fn = pdf.name
        low = fn.lower()
        registro = {"file": fn}
        if _tipo_excluido(low):
            excluidos.append({**registro, "motivo": "tipo excluido (certificado/homologación)"})
            continue
        if pdf.stat().st_size < 1024:
            excluidos.append({**registro, "motivo": f"tamaño sospechoso ({pdf.stat().st_size} B)"})
            continue
        paginas = _paginas(pdf)
        if not paginas:
            excluidos.append({**registro, "motivo": "PDF ilegible (PyMuPDF no lo abre)"})
            continue
        sha = sha256_file(pdf)

        # «Hecho» = chunks INDEXADOS para este sha (el estado final), no la mera
        # presencia de estados intermedios: si el proceso murió tras extraer o
        # tras el alta, el doc debe seguir siendo candidato y REANUDAR las fases
        # que falten (crítico del dúo s314: el criterio anterior — sha en store /
        # en documents ⇒ excluido — dejaba altas a medias irreanudables).
        chunks = sb.fetch_rows("chunks_v2", select="id",
                               filters={"extraction_sha256": f"eq.{sha}"}, limit=1)
        if chunks:
            excluidos.append({**registro, "motivo": "ya indexado (chunks_v2 por sha)", "sha256": sha})
            continue
        entrada = indice.get(low)
        if entrada is None:
            excluidos.append({**registro, "motivo": "SIN entrada en _metadata.json (identidad) — añadirla antes de ingestar"})
            continue
        extraido = (store / f"{sha}.json").exists()
        documentado = bool(sb.fetch_rows("documents", select="id",
                                         filters={"source_pdf_sha256": f"eq.{sha}"}, limit=1))
        candidatos.append({"file": fn, "path": str(pdf), "sha256": sha,
                           "paginas": paginas, "equipo": entrada.get("equipo"),
                           "tipo_sidecar": entrada.get("tipo"),
                           "reanuda": {"extraido": extraido, "documentado": documentado}})
    return candidatos, excluidos


def informe_dry(candidatos: list[dict]) -> list[dict]:
    """B1-B5 en memoria por candidato (sin extracción todavía no hay record del
    store, así que el dry aquí es identidad + coste; el B-dry por chunks corre
    en el commit, entre extracción e indexación)."""
    total_pag = sum(c["paginas"] for c in candidatos)
    creditos = total_pag * CREDITS_PER_PAGE[EXTRACT_MODE]
    print(f"\n— DRY-RUN: {len(candidatos)} PDFs nuevos, ~{total_pag} páginas")
    print(f"  Coste extracción estimado: ~{creditos} créditos LlamaParse (~${creditos * 1.25 / 1000:.2f})")
    for c in candidatos:
        print(f"  · {c['file']}  ({c['paginas']} pág, equipo={c['equipo']})")
    return candidatos


def ejecutar(canal: str, data_root: Path, candidatos: list[dict], nota: str) -> list[dict]:
    key = os.getenv("LLAMAPARSE_API_KEY")
    for var in ("LLAMAPARSE_API_KEY", "VOYAGE_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.getenv(var):
            raise SystemExit(f"GATE: falta {var} en .env para el commit.")

    store = data_root / "data" / "extraction" / DEFAULT_CONFIG
    sb = SupabaseHTTP()
    resultados = []
    for i, c in enumerate(candidatos, 1):
        fn, sha, path = c["file"], c["sha256"], c["path"]
        print(f"\n[{i}/{len(candidatos)}] {fn}")

        # A2 — extracción al store canónico (source_path ABSOLUTO → sidecar OK).
        out = store / f"{sha}.json"
        if not out.exists():
            t0 = time.time()
            job_id, resultado = llamaparse_extract(path, key, EXTRACT_MODE, EXTRACT_MODEL)
            record = {"sha256": sha, "source_path": path, "manufacturer": None,
                      "pages": c["paginas"], "mode": EXTRACT_MODE, "model": EXTRACT_MODEL,
                      "job_id": job_id,
                      "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "result": resultado}
            tmp = str(out) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
            os.replace(tmp, str(out))
            print(f"  extracción OK ({time.time() - t0:.0f}s)")
        else:
            with open(out, encoding="utf-8") as f:
                record = json.load(f)
            print("  extracción ya en store")
        with open(out, encoding="utf-8") as f:
            record = json.load(f)

        # B-dry en memoria → identidad + nº de chunks esperado.
        dry = process_file(record, None, dry_run=True)
        if dry["status"] != "dry_run":
            resultados.append({"file": fn, "sha256": sha, "status": f"NO-INDEXABLE: {dry['status']}"})
            print(f"  ✗ no indexable ({dry['status']}) — fila de documents NO creada")
            continue
        kept = dry.pop("_chunks")
        muestra = " ".join(ch.content for ch in kept[:4])
        meta = detect_document_metadata(path, muestra)
        if not meta.manufacturer:
            resultados.append({"file": fn, "sha256": sha, "status": "SIN-FABRICANTE (revisar sidecar/overrides)"})
            print("  ✗ fabricante no resuelto — NO se ingesta (identidad es fail-closed)")
            continue

        # Alta en documents ANTES de indexar (resolve_document_id enlaza por sha).
        # doc_type: el tipo del sidecar manda (B5 no reconoce la nomenclatura del
        # portal); su regex queda de fallback.
        doc_type = (_TIPO_SIDECAR_A_DOC_TYPE.get((c.get("tipo_sidecar") or "").strip().lower())
                    or meta.doc_type)
        filas = sb.fetch_rows("documents", select="id",
                              filters={"source_pdf_sha256": f"eq.{sha}"}, limit=2)
        if not filas:
            sb.insert_rows("documents", [{
                "document_family": _document_family(fn),
                "language": dry.get("language"),
                "doc_type": doc_type,
                "manufacturer": meta.manufacturer,
                "product_model": meta.product_model,
                "source_pdf_filename": fn,
                "source_pdf_sha256": sha,
                "status": "active",
                "notes": nota,
            }])
            print(f"  documents ← {meta.manufacturer} / {meta.product_model} / {doc_type}")
        else:
            print("  documents: fila ya existente (reanudación) — se reutiliza")

        # B completo (contextualize + embed + dedup + index; enlaza por sha).
        real = process_file(record, sb, dry_run=False)
        resultados.append({"file": fn, "sha256": sha, "status": real["status"],
                           "chunks": real.get("indexed"), "document_id": real.get("document_id"),
                           "manufacturer": meta.manufacturer, "product_model": meta.product_model})
        print(f"  indexado: {real.get('indexed')} chunks (document_id={real.get('document_id')})")

    # Verificación en DB: cada sha con chunks > 0 y document_id enlazado.
    print("\n— VERIFICACIÓN EN DB —")
    fallos = 0
    for r in resultados:
        if "chunks" not in r:
            fallos += 1
            print(f"  ✗ {r['file']}: {r['status']}")
            continue
        filas = sb.fetch_rows("chunks_v2", select="id,document_id",
                              filters={"extraction_sha256": f"eq.{r['sha256']}"}, limit=1)
        enlazado = bool(filas and filas[0].get("document_id"))
        ok = bool(filas) and (r.get("chunks") or 0) > 0 and enlazado
        fallos += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {r['file']}: {r.get('chunks')} chunks, enlazado={enlazado}")
    return resultados, fallos


def main() -> None:
    ap = argparse.ArgumentParser(description="Alta de manuales nuevos (A2+B) por canal")
    ap.add_argument("--canal", required=True, help="canal del portal (carpeta Manuales_<canal>)")
    ap.add_argument("--data-root", required=True,
                    help="raíz del corpus (carpeta OneDrive con Manuales_* y data/extraction)")
    ap.add_argument("--solo", default=None, help="glob para acotar el lote (p.ej. 'MI_KIDDE_*.pdf')")
    ap.add_argument("--commit", action="store_true",
                    help="ejecuta de verdad (extrae, alta en documents, indexa); sin él = dry-run")
    ap.add_argument("--nota", default=None,
                    help="nota para las filas nuevas de documents (procedencia del lote)")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    candidatos, excluidos = gates(args.canal, data_root, args.solo)

    print(f"Canal {args.canal}: {len(candidatos)} candidatos nuevos, {len(excluidos)} excluidos")
    for e in excluidos:
        print(f"  – {e['file']}: {e['motivo']}")
    if not candidatos:
        raise SystemExit("Nada nuevo que ingestar (0 candidatos tras gates).")

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    nota = args.nota or f"ingest_new {stamp} canal {args.canal}"

    if not args.commit:
        informe_dry(candidatos)
        recibo = {"modo": "dry-run", "canal": args.canal, "stamp": stamp,
                  "candidatos": candidatos, "excluidos": excluidos}
    else:
        resultados, fallos = ejecutar(args.canal, data_root, candidatos, nota)
        recibo = {"modo": "commit", "canal": args.canal, "stamp": stamp, "nota": nota,
                  "fallos_verificacion": fallos,
                  "resultados": resultados, "excluidos": excluidos}
        print("\nRecordatorios post-lote: (1) actualizar data/Inventario_Manuales.xlsx "
              "(scripts/update_inventario.py --data-root <corpus>); (2) el corpus "
              "cambió → anotarlo en la próxima fila del assessment; (3) sonda de "
              "alcanzabilidad de los docs nuevos.")

    logs = data_root / "logs"
    logs.mkdir(exist_ok=True)
    ruta = logs / f"ingest_new_{stamp}_{args.canal}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(recibo, f, ensure_ascii=False, indent=1)
    print(f"\nRecibo: {ruta}")
    if args.commit and fallos:
        # Un lote con documentos sin chunks o sin enlace NO es un éxito: salida
        # ruidosa para que ninguna automatización lo dé por bueno (dúo s314).
        raise SystemExit(f"{fallos} documento(s) con problema — lote NO limpio (recibo: {ruta})")


if __name__ == "__main__":
    main()
