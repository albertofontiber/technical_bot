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
import re
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
from src.extraction_store import publicar_al_bucket  # noqa: E402
from src.reingest.pipeline import process_file, DEFAULT_CONFIG  # noqa: E402
from src.reingest.metadata import detect_document_metadata  # noqa: E402
from src.reingest import sidecar  # noqa: E402
from src.reingest.revision_gate import (  # noqa: E402
    BLOQUEADO as _REV_BLOQUEADO,
    SIN_SENAL as _REV_SIN_SENAL,
    cruzar as _rev_cruzar,
    indice_corpus as _rev_indice,
    indice_de_senales as _rev_indice_lote,
    senales_documento as _rev_senales,
    serializar_senal as _rev_serializar,
)
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


def _pdf_info(path: Path) -> tuple[int | None, str]:
    """(nº páginas, texto de la PORTADA). La portada alimenta la puerta de
    revisión (#73): el caso real s316d solo era detectable por la primera
    página (INS570-3). Fallo de lectura ⇒ (None, '') — el gate de integridad
    ya excluye el PDF ilegible."""
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            portada = doc[0].get_text() if doc.page_count else ""
            return doc.page_count, portada or ""
    except Exception:
        return None, ""


def _documents_activos(sb: SupabaseHTTP) -> list[dict]:
    """`documents` activos COMPLETO, paginado. PostgREST corta a 1000 filas en
    SILENCIO (la clase #72) y `documents` ya supera las mil: una página perdida
    aquí = un supersede invisible = la puerta mentiría en verde."""
    filas: list[dict] = []
    off, pagina = 0, 1000
    while True:
        lote = sb.fetch_rows(
            "documents", select="source_pdf_filename,language,revision",
            filters={"status": "eq.active", "order": "id.asc",
                     "offset": str(off)},
            limit=pagina)
        filas.extend(lote)
        if len(lote) < pagina:
            return filas
        off += pagina


def _fecha_de_senal(senal) -> str | None:
    """`documents.revision_date` cuando la señal ES una fecha (AAAAMM del
    portal → día 1; ISS ddMMMyy → día exacto)."""
    if senal is None or senal.formato not in ("fecha", "iss_fecha"):
        return None
    y, m = senal.rev[0], senal.rev[1]
    d = senal.rev[2] if len(senal.rev) > 2 else 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def gates(canal: str, data_root: Path, solo: str | None,
          ignorar_revision: str | None = None) -> tuple[list[dict], list[dict]]:
    """Valida el lote y devuelve (candidatos, excluidos). Fail-closed en todo lo
    que compromete identidad o dinero; las exclusiones de tipo se LISTAN.
    `ignorar_revision`: glob de override CONSCIENTE de la puerta #73 (None=off,
    '*'=todo el lote); el uso queda AUDITADO en candidato y recibo."""
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
    # Índice de revisión (#73): UNA pasada paginada sobre documents activos.
    indice_rev = _rev_indice(_documents_activos(sb))
    candidatos, excluidos = [], []
    pre_candidatos: list[dict] = []   # 1ª pasada; la puerta #73 cruza en la 2ª
    vistos_lote: dict[str, str] = {}  # sha -> filename (dedup INTRA-lote, dúo s314)
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
        paginas, portada = _pdf_info(pdf)
        if not paginas:
            excluidos.append({**registro, "motivo": "PDF ilegible (PyMuPDF no lo abre)"})
            continue
        sha = sha256_file(pdf)
        if sha in vistos_lote:
            excluidos.append({**registro, "motivo": f"DUP intra-lote (idéntico a {vistos_lote[sha]})",
                              "sha256": sha})
            continue
        vistos_lote[sha] = fn

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
        pre_candidatos.append({"file": fn, "path": str(pdf), "sha256": sha,
                               "paginas": paginas, "equipo": entrada.get("equipo"),
                               "tipo_sidecar": entrada.get("tipo"),
                               "_senales": _rev_senales(fn, portada)})

    # Puerta de REVISIÓN (#73), SEGUNDA pasada: el sha prueba bytes, no
    # información — una revisión ANTIGUA se BLOQUEA aquí (s316d: 2 de 2
    # candidatos «nuevos» eran revisiones viejas). Doble cruce: contra el
    # CORPUS (igualdad bloquea — contrato >=) y contra el RESTO DEL LOTE
    # (r13 Sol C1/Fable F2: dos revisiones del mismo manual llegando juntas
    # pasaban las dos; ahí la igualdad degrada a revisión-a-mano).
    senales_lote = [c.pop("_senales") for c in pre_candidatos]
    for i, c in enumerate(pre_candidatos):
        fn, sha = c["file"], c["sha256"]
        senales = senales_lote[i]
        veredicto = _rev_cruzar(senales, indice_rev)
        if veredicto.resultado != _REV_BLOQUEADO:
            otros = [(s, pre_candidatos[j]["file"])
                     for j in range(len(pre_candidatos)) if j != i
                     for s in senales_lote[j]]
            v_lote = _rev_cruzar(senales, _rev_indice_lote(otros),
                                 igualdad_bloquea=False)
            if v_lote.resultado != _REV_SIN_SENAL:
                v_lote = type(v_lote)(v_lote.resultado,
                                      f"INTRA-LOTE: {v_lote.motivo}",
                                      v_lote.contra, v_lote.senal)
                if v_lote.resultado == _REV_BLOQUEADO or \
                        veredicto.resultado == _REV_SIN_SENAL:
                    veredicto = v_lote
        ignorada = bool(
            veredicto.resultado == _REV_BLOQUEADO and ignorar_revision
            and fnmatch.fnmatch(fn.lower(), ignorar_revision.lower()))
        if veredicto.resultado == _REV_BLOQUEADO and not ignorada:
            excluidos.append({**{"file": fn}, "sha256": sha,
                              "motivo": (f"REVISIÓN supersedida — {veredicto.motivo} "
                                         f"(vigente: {veredicto.contra}); override "
                                         "consciente: --ignorar-revision")})
            continue
        if ignorada:
            print(f"  ⚠ OVERRIDE de revisión ({fn}): {veredicto.motivo} — "
                  f"ingesta ADJUDICADA pese a {veredicto.contra}")
        senal_p = veredicto.senal or (senales[0] if senales else None)
        c["revision"] = {"resultado": veredicto.resultado,
                         "motivo": veredicto.motivo,
                         "contra": veredicto.contra,
                         "ignorada": ignorada,
                         "senal": _rev_serializar(senal_p) if senal_p else None,
                         "fecha": _fecha_de_senal(senal_p)}
        extraido = (store / f"{sha}.json").exists()
        documentado = bool(sb.fetch_rows("documents", select="id",
                                         filters={"source_pdf_sha256": f"eq.{sha}"}, limit=1))
        c["reanuda"] = {"extraido": extraido, "documentado": documentado}
        candidatos.append(c)
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
        rev = c.get("revision") or {}
        if rev.get("resultado") == _REV_SIN_SENAL:
            print("      revisión: edición NO verificable (sin señal legible) — "
                  "comparar portada a mano si el título suena a existente")
        elif rev.get("resultado"):
            print(f"      revisión: {rev['resultado']} — {rev['motivo']}")
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
        # try/except POR DOCUMENTO (dúo s314): una excepción (Voyage 500, PDF
        # raro…) no aborta el lote ni se traga el recibo; el doc queda FALLO en
        # el recibo y, gracias a los gates reanudables, el siguiente run lo
        # retoma en la fase que le falte.
        try:
            _ingesta_doc(c, store, sb, key, nota, resultados)
        except Exception as e:
            resultados.append({"file": fn, "sha256": sha,
                               "status": f"FALLO: {type(e).__name__}: {e}"})
            print(f"  ✗ FALLO {type(e).__name__}: {e}")


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


def _patch_chunks_doc_type(sha: str, doc_type: str) -> int:
    """doc_type en los CHUNKS por PATCH post-index. B5 no reconoce la
    nomenclatura del portal y metadata.py está sha-pineada por recibos
    s116/s117 (pre-flight s314) → el fix vive aquí. Devuelve filas tocadas."""
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/chunks_v2"
    k = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
    import httpx
    r = httpx.patch(url, params={"extraction_sha256": f"eq.{sha}"},
                    headers={"apikey": k, "Authorization": f"Bearer {k}",
                             "Prefer": "return=headers-only, count=exact"},
                    json={"doc_type": doc_type}, timeout=60)
    r.raise_for_status()
    rango = r.headers.get("content-range", "")
    try:
        return int(rango.rsplit("/", 1)[-1]) if "/" in rango else -1
    except ValueError:
        return -1


def _ingesta_doc(c: dict, store: Path, sb: SupabaseHTTP, key: str, nota: str,
                 resultados: list[dict]) -> None:
    fn, sha, path = c["file"], c["sha256"], c["path"]

    # A2 — extracción al store canónico (source_path ABSOLUTO → sidecar OK).
    out = store / f"{sha}.json"
    if not out.exists():
        # TOCTOU (dúo s314): en OneDrive el fichero puede cambiar entre el gate
        # y la extracción — recomputar y abortar este doc si el sha difiere.
        if sha256_file(Path(path)) != sha:
            raise RuntimeError("el PDF cambió entre gates y extracción (sha distinto) — re-corre")
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
        print("  extracción ya en store (reanudación)")

    # s325b — PUERTA de consistencia: aquí se ESCRIBE en el store, así que aquí se
    # publica al bucket `extraction`. Sin esto, el store de la nube derivaría del de
    # OneDrive en cuanto alguien se olvidase de re-subir, y una sesión cloud leería un
    # corpus viejo sin saberlo.
    # Va FUERA del `if`: al reanudar, el fichero ya está en disco pero puede no estar
    # en el bucket —justo el caso de la ejecución anterior que falló—, y saltarlo
    # dejaba la puerta sin reintento (medio de Sol, ronda 2). La publicación es
    # idempotente (upsert + manifiesto por nombre), así que republicar no cuesta nada.
    # FAIL-OPEN a propósito: la extracción YA está en disco y es lo que vale; un fallo
    # de red no debe tumbar una ingesta que cuesta dinero. Queda DECLARADO en el
    # RECIBO del documento —no solo por consola— y `--verificar` lo caza después.
    publicacion = None
    try:
        publicar_al_bucket(out)
        print("  publicada en el bucket `extraction`")
    except Exception as e:
        publicacion = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"  AVISO: no se pudo publicar en el bucket ({e}) — "
              f"corre `upload_extraction_store.py --aplicar` al terminar")
    with open(out, encoding="utf-8") as f:
        record = json.load(f)

    # B-dry en memoria → identidad + nº de chunks esperado.
    dry = process_file(record, None, dry_run=True)
    if dry["status"] != "dry_run":
        resultados.append({"file": fn, "sha256": sha, "status": f"NO-INDEXABLE: {dry['status']}",
                           "publicacion_fallida": publicacion})
        print(f"  ✗ no indexable ({dry['status']}) — fila de documents NO creada")
        return
    kept = dry.pop("_chunks")
    muestra = " ".join(ch.content for ch in kept[:4])
    meta = detect_document_metadata(path, muestra)
    if not meta.manufacturer:
        resultados.append({"file": fn, "sha256": sha,
                           "status": "SIN-FABRICANTE (revisar sidecar/overrides)",
                           "publicacion_fallida": publicacion})
        print("  ✗ fabricante no resuelto — NO se ingesta (identidad es fail-closed)")
        return

    # Alta en documents ANTES de indexar (resolve_document_id enlaza por sha).
    # doc_type: el tipo del sidecar manda (B5 no reconoce la nomenclatura del
    # portal); su regex queda de fallback.
    doc_type = (_TIPO_SIDECAR_A_DOC_TYPE.get((c.get("tipo_sidecar") or "").strip().lower())
                or meta.doc_type)
    filas = sb.fetch_rows("documents", select="id",
                          filters={"source_pdf_sha256": f"eq.{sha}"}, limit=2)
    if not filas:
        # (#73, Sol r13 C2) La señal de edición SE PERSISTE en las columnas que
        # migrations/001 diseñó para esto (hoy siempre NULL): sin ella, una
        # revisión solo-detectable-por-portada quedaría INVISIBLE para la
        # puerta en lotes futuros (el índice relee documents).
        rev = c.get("revision") or {}
        sb.insert_rows("documents", [{
            "document_family": _document_family(fn),
            "language": dry.get("language"),
            "doc_type": doc_type,
            "manufacturer": meta.manufacturer,
            "product_model": meta.product_model,
            "source_pdf_filename": fn,
            "source_pdf_sha256": sha,
            "status": "active",
            "revision": rev.get("senal"),
            "revision_date": rev.get("fecha"),
            "notes": nota,
        }])
        print(f"  documents ← {meta.manufacturer} / {meta.product_model} / {doc_type}")
    else:
        print("  documents: fila ya existente (reanudación) — se reutiliza")

    # B completo (contextualize + embed + dedup + index; enlaza por sha).
    real = process_file(record, sb, dry_run=False)
    parcheados = _patch_chunks_doc_type(sha, doc_type) if doc_type else 0
    resultados.append({"file": fn, "sha256": sha, "status": real["status"],
                       "chunks": real.get("indexed"), "document_id": real.get("document_id"),
                       "doc_type": doc_type, "chunks_doc_type": parcheados,
                       "manufacturer": meta.manufacturer, "product_model": meta.product_model,
                       # (#73, Sol r13 M5) el veredicto de revisión — y si hubo
                       # override — queda AUDITADO en el recibo de commit.
                       "revision": c.get("revision"),
                       # s325b: el fail-open de la puerta al bucket, en el RECIBO
                       "publicacion_fallida": publicacion})
    print(f"  indexado: {real.get('indexed')} chunks (document_id={real.get('document_id')}, "
          f"doc_type→{parcheados} chunks)")


def _evaluar_gate_identidad() -> dict:
    """Evalua el gate y DEVUELVE el veredicto (no aborta): el llamador lo mete en
    el recibo y corta despues, para que la traza sobreviva al corte.

    "No he podido evaluar" NO es "todo bien" (critico de Sol r34): se marca con
    `no_evaluado` y tambien corta.
    """
    try:
        from src.rag.identidad_gate import evaluar
        v = evaluar()
    except Exception as e:                                    # noqa: BLE001
        print(f"  gate identidad: NO EVALUADO ({type(e).__name__}: {e})")
        return {"ok": False, "no_evaluado": f"{type(e).__name__}: {e}",
                "nuevas": None, "total": None}
    print(f"  gate identidad: {'OK' if v['ok'] else 'VIOLACIONES NUEVAS'} "
          f"({v['nuevas']} nuevas / {v['total']} totales)")
    if v.get("manifiesto_stale"):
        print(f"  aviso: {len(v['excepciones_resueltas'])} excepciones del "
              f"manifiesto ya no aplican - re-sella con --sellar")
    return v


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
    ap.add_argument("--ignorar-revision", nargs="?", const="*", default=None,
                    metavar="GLOB",
                    help="override CONSCIENTE de la puerta de revisión (#73): ingesta "
                         "aunque el corpus tenga revisión >= — sin valor aplica a todo "
                         "el lote; con GLOB solo a los ficheros que casen (adjudicación "
                         "por fichero). El uso queda auditado en el recibo")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    candidatos, excluidos = gates(args.canal, data_root, args.solo,
                                  ignorar_revision=args.ignorar_revision)

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
                  "ignorar_revision": args.ignorar_revision,
                  "resultados": resultados, "excluidos": excluidos}
        print("\nRecordatorios post-lote: (1) actualizar data/Inventario_Manuales.xlsx "
              "(scripts/update_inventario.py --data-root <corpus>); (2) el corpus "
              "cambió → anotarlo en la próxima fila del assessment; (3) sonda de "
              "alcanzabilidad de los docs nuevos; (4) fase DERIVADOS OBLIGATORIA "
              "(#68, s315): scripts/derive_channels_lote.py --since <hoy> --tag "
              "<lote> — sin ella los docs nuevos quedan fuera de los canales "
              "enunciados/hyq vivos en producción.")

    # s323 fase C (Fable M1): el veredicto del gate se EVALUA aqui y viaja DENTRO
    # del recibo. El cierre anterior salvo el recibo pero le quito el veredicto:
    # la traza existia y no contenia lo unico que importaba saber.
    veredicto_gate = None
    if args.commit:
        veredicto_gate = _evaluar_gate_identidad()
        recibo["gate_identidad"] = veredicto_gate

    logs = data_root / "logs"
    logs.mkdir(exist_ok=True)
    ruta = logs / f"ingest_new_{stamp}_{args.canal}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(recibo, f, ensure_ascii=False, indent=1)
    print(f"\nRecibo: {ruta}")

    # s325b (Fable, ronda 2): el fail-open de la publicacion al bucket no puede
    # quedarse solo en el recibo — «que alguien lo lea» es justo el mecanismo de
    # acordarse que la puerta unica venia a eliminar. Se dice EN LA CARA al final,
    # con el comando exacto. No corta el lote: la ingesta en si fue correcta y la
    # extraccion esta en disco; lo que falta es la copia de la nube.
    sin_publicar = [r for r in recibo.get("resultados", []) if r.get("publicacion_fallida")]
    if sin_publicar:
        print(f"\n{'=' * 60}\nATENCION: {len(sin_publicar)} extraccion(es) NO se "
              f"publicaron en el bucket `extraction` — el store de la nube esta "
              f"DESFASADO respecto a este disco.\n  Arreglo: python "
              f"scripts/upload_extraction_store.py \"{data_root}\" --aplicar\n{'=' * 60}")

    # el corte va DESPUES de persistir: primero la traza, luego el veredicto.
    if veredicto_gate is not None and not veredicto_gate.get("ok", True):
        raise SystemExit(
            f"GATE DE IDENTIDAD: {veredicto_gate['nuevas']} violaciones NUEVAS "
            f"(recibo: {ruta})")
    if veredicto_gate is not None and veredicto_gate.get("no_evaluado"):
        raise SystemExit(
            f"GATE DE IDENTIDAD NO EVALUADO ({veredicto_gate['no_evaluado']}) — "
            f"'no he podido comprobar' NO es 'todo bien' (recibo: {ruta})")

    if args.commit and fallos:
        # Un lote con documentos sin chunks o sin enlace NO es un éxito: salida
        # ruidosa para que ninguna automatización lo dé por bueno (dúo s314).
        raise SystemExit(f"{fallos} documento(s) con problema — lote NO limpio (recibo: {ruta})")


if __name__ == "__main__":
    main()
