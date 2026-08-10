# -*- coding: utf-8 -*-
"""s315 (punto 6b, Alberto): subir el corpus de PDFs a Supabase Storage y enlazarlo.

POR QUÉ. El backfill v1 solo cubre los docs con URL de portal (Casmar, 76/1.243).
Alberto quiere link para TODO el corpus: los PDFs históricos viven en OneDrive sin
URL pública. Ruta decidida: bucket `manuales` de Supabase Storage (creado en s315,
público, 100MB/fichero, solo application/pdf — mismo patrón que `manual-images`
del álbum de diagramas) → subir los PDFs → poblar `documents.source_url` con la
URL pública del objeto. La leyenda (`SOURCE_LEGEND_LINKS`) los sirve con `#page=N`
sin tocar más código.

DÓNDE SE CORRE. En una máquina que VEA los PDFs (OneDrive) y tenga SUPABASE_URL +
SUPABASE_SERVICE_KEY (el .env local). El entorno remoto no ve OneDrive.

    python scripts/s315_upload_manuales_storage.py "C:\\...\\Manuales_*"   # dry-run
    python scripts/s315_upload_manuales_storage.py "C:\\...\\Manuales_*" --aplicar

QUÉ HACE por cada PDF encontrado (recursivo, glob de directorios):
  1. sha256 del fichero → busca `documents.source_pdf_sha256` (identidad de
     CONTENIDO; los ficheros sin fila en documents se listan y se saltan).
  2. Sube a `manuales/<manufacturer>/<nombre saneado>` (skip si el objeto ya
     existe — reanudable).
  3. `source_url` = URL pública del objeto, SOLO si estaba NULL (los links de
     portal existentes, p.ej. Casmar, se conservan: --pisar-portal para
     sustituirlos también por la copia propia).
Recibo: evals/s315_storage_upload_v1.json (solo con --aplicar, tras confirmar).

Nota de alcance: los manuales son documentación oficial de fabricante que se
redistribuye a los técnicos propios vía bot; el bucket es público-por-URL (sin
listado). Si a futuro se quiere GCP u otra CDN, el seam es esta misma columna.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time
import unicodedata
from urllib.parse import quote

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIBO = os.path.join(REPO, "evals", "s315_storage_upload_v1.json")
BUCKET = "manuales"
FETCH_CAP = 10_000


_MAX_REINTENTOS = 5


def _con_reintento(fn, etiqueta: str):
    """Ejecuta `fn` reintentando ante caídas de TRANSPORTE (no de estado HTTP).

    (s316c) La red de Alberto es inestable y la subida murió en el PRIMER fichero con
    `httpx.ReadError` (WinError 10054), dejando 0/1008. HEAD/POST/PATCH aquí son
    idempotentes (el objeto se sobreescribe igual y el PATCH fija el mismo valor), así
    que reintentar es seguro por construcción.
    """
    import httpx as _hx
    for intento in range(_MAX_REINTENTOS):
        try:
            return fn()
        except _hx.TransportError as exc:
            if intento == _MAX_REINTENTOS - 1:
                raise
            espera = 2 ** intento
            print(f"  transporte caído en {etiqueta} ({type(exc).__name__}); "
                  f"reintento {intento + 1}/{_MAX_REINTENTOS - 1} en {espera}s", flush=True)
            time.sleep(espera)


def _sano(nombre: str) -> str:
    """Nombre de objeto seguro: ASCII, sin espacios ni caracteres raros."""
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() or c in "._-" else "_" for c in s)
    return s or "documento.pdf"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> int:
    try:  # consola Windows cp1252 vs los → ↔ del informe (convención del repo)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("raices", nargs="+",
                    help="directorios o globs con los PDFs (p.ej. ...\\Manuales_*)")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--pisar-portal", action="store_true",
                    help="sustituir también las URLs de portal existentes por la copia propia")
    args = ap.parse_args()

    import httpx

    sys.path.insert(0, REPO)
    from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

    pdfs: list[str] = []
    for raiz in args.raices:
        for d in glob.glob(raiz):
            if os.path.isfile(d) and d.lower().endswith(".pdf"):
                pdfs.append(d)
            else:
                for base, _dirs, files in os.walk(d):
                    pdfs.extend(os.path.join(base, f) for f in files
                                if f.lower().endswith(".pdf"))
    pdfs = sorted(set(pdfs))
    print(f"PDFs locales encontrados: {len(pdfs)}")

    headers = {"apikey": SUPABASE_SERVICE_KEY,
               "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    with httpx.Client(base_url=SUPABASE_URL, headers=headers, timeout=120) as client:
        # (s316) PAGINACIÓN REAL. La v1 pedía `limit=10000` y comprobaba
        # `len(docs) >= FETCH_CAP`, pero PostgREST capa en 1.000 filas POR SERVIDOR:
        # con 1.243 documentos devolvía 1.000, la guarda (1.000 < 10.000) no
        # disparaba y los 243 restantes quedaban INVISIBLES → sus PDFs se
        # clasificaban como «sin fila por sha» y el --aplicar los habría SALTADO,
        # dejando su source_url sin poblar. Misma clase de truncamiento silencioso
        # que el dúo s315 ya corrigió en hyq_lote_pipeline (#5).
        docs = []
        offset = 0
        while True:
            resp = client.get(
                "/rest/v1/documents",
                headers={"Range": f"{offset}-{offset + 999}"},
                params={"select": "id,source_pdf_sha256,source_pdf_filename,"
                                  "manufacturer,source_url",
                        "source_pdf_sha256": "not.is.null", "order": "id.asc"},
            )
            resp.raise_for_status()
            pagina = resp.json()
            docs.extend(pagina)
            if len(pagina) < 1000:
                break
            offset += 1000
            if offset >= FETCH_CAP:
                raise SystemExit(f"documents superó el cap ({FETCH_CAP}): revisar")
        print(f"documents con sha leídos: {len(docs)}")
        por_sha = {d["source_pdf_sha256"]: d for d in docs}
        # Fallback por NOMBRE para el diagnóstico de los sin-fila: 159/1.243 docs
        # llevan sha placeholder ('backfill:…', TECH_DEBT #4 Phase 3 sin hacer) y
        # jamás casan por contenido. El nombre NO decide nada operativo (identidad
        # = sha); solo clasifica el informe.
        por_nombre = {}
        for d in docs:
            por_nombre.setdefault(str(d.get("source_pdf_filename") or "").lower(), d)

        plan, sin_fila, ya_enlazados = [], [], 0
        vistos: set[str] = set()
        for path in pdfs:
            sha = _sha256(path)
            if sha in vistos:
                continue  # duplicado local (mismo contenido en 2 carpetas)
            vistos.add(sha)
            d = por_sha.get(sha)
            if d is None:
                nombre = os.path.basename(path)
                hom = por_nombre.get(nombre.lower())
                if hom is None:
                    clase = "AUSENTE_DEL_CORPUS"
                elif str(hom.get("source_pdf_sha256", "")).startswith("backfill:"):
                    clase = "EN_CORPUS_SHA_PLACEHOLDER"
                else:
                    clase = "EN_CORPUS_BYTES_DISTINTOS"  # ¿revisión/copia distinta? (#4)
                sin_fila.append({"fichero": nombre, "sha256": sha, "path": path,
                                 "clase": clase,
                                 "doc_homonimo": hom.get("id") if hom else None})
                continue
            if d.get("source_url") and not args.pisar_portal:
                ya_enlazados += 1
                continue
            mfr = _sano(str(d.get("manufacturer") or "otros"))
            objeto = f"{mfr}/{_sano(os.path.basename(path))}"
            plan.append({"id": d["id"], "sha256": sha, "path": path,
                         "objeto": objeto, "doc": d.get("source_pdf_filename")})

        clases = {}
        for s in sin_fila:
            clases[s["clase"]] = clases.get(s["clase"], 0) + 1
        print(f"a subir+enlazar: {len(plan)} · ya con URL (se conservan): {ya_enlazados} "
              f"· PDFs sin fila por sha: {len(sin_fila)} {clases}")
        diag = os.path.join(REPO, "evals", "s315_storage_sinfila_diagnostico_v1.json")
        json.dump({"nota": ("clasificación por NOMBRE, solo informativa; identidad=sha. "
                            "AUSENTE_DEL_CORPUS = candidato a ingesta; "
                            "EN_CORPUS_SHA_PLACEHOLDER = doc ya ingestado con sha falso "
                            "(#4 Phase 3); EN_CORPUS_BYTES_DISTINTOS = posible revisión (#4)"),
                   "sin_fila": sin_fila}, open(diag, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"diagnóstico sin-fila -> {diag}")

        if not args.aplicar:
            print("(dry-run; --aplicar para subir y enlazar)")
            return 0

        confirmadas = []
        fallos: list[dict] = []
        try:
            for n, c in enumerate(plan, 1):
                # skip-si-existe = reanudable (HEAD del objeto público)
                pub = f"/storage/v1/object/public/{BUCKET}/{quote(c['objeto'])}"
                try:
                    existe = _con_reintento(
                        lambda: client.head(pub), f"HEAD {c['objeto']}"
                    ).status_code == 200
                    if not existe:
                        with open(c["path"], "rb") as fh:
                            datos = fh.read()
                        up = _con_reintento(
                            lambda: client.post(
                                f"/storage/v1/object/{BUCKET}/{quote(c['objeto'])}",
                                content=datos,
                                headers={"Content-Type": "application/pdf"},
                            ), f"POST {c['objeto']}")
                        if up.status_code not in (200, 201):
                            print(f"  FALLO subida {c['objeto']}: {up.status_code} "
                                  f"{up.text[:120]}", flush=True)
                            fallos.append({"objeto": c["objeto"],
                                           "status": up.status_code})
                            continue
                    url = f"{SUPABASE_URL}{pub}"
                    params = {"id": f"eq.{c['id']}"}
                    if not args.pisar_portal:
                        params["source_url"] = "is.null"
                    pr = _con_reintento(
                        lambda: client.patch("/rest/v1/documents", params=params,
                                             json={"source_url": url},
                                             headers={"Prefer": "return=minimal"}),
                        f"PATCH {c['doc']}")
                    pr.raise_for_status()
                    confirmadas.append({"id": c["id"], "doc": c["doc"], "url": url})
                except Exception as exc:                       # noqa: BLE001
                    # (s316c) un fichero que agota reintentos NO tumba el lote: se anota
                    # y se sigue. Con red inestable, abortar en el primero significaba
                    # 0/1008 subidos — medido.
                    print(f"  ERROR {c['objeto']}: {type(exc).__name__}", flush=True)
                    fallos.append({"objeto": c["objeto"], "error": type(exc).__name__})
                if n % 50 == 0:
                    print(f"  {n}/{len(plan)} · ok={len(confirmadas)} "
                          f"fallos={len(fallos)}", flush=True)
        finally:
            recibo = {
                "motivo": "s315 punto 6b: corpus completo con link (Supabase Storage, bucket manuales)",
                "reversible": ("UPDATE documents SET source_url=NULL WHERE id IN (ids de 'cambios'); "
                               "los objetos del bucket se pueden borrar aparte"),
                "planificadas": len(plan),
                "cambios": confirmadas,
            }
            json.dump(recibo, open(RECIBO, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"SUBIDAS+ENLAZADAS: {len(confirmadas)}/{len(plan)} · recibo -> {RECIBO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
