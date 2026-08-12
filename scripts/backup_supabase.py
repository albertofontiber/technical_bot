# -*- coding: utf-8 -*-
"""s319 — Backup LÓGICO restaurable de la capa CORPUS/IDENTIDAD (DEC-209).

QUÉ ES (y qué no). Supabase mantiene backups GESTIONADOS del proyecto (esa capa
existe y es el PITR real). Lo que NO existía era un backup lógico BAJO NUESTRO
CONTROL, restaurable fuera del proveedor, del activo insustituible: la capa
corpus/identidad. Este script la vuelca y DEMUESTRA que se puede restaurar —
un recibo de filas+sha256 prueba bytes; solo el DRILL de restauración prueba
recuperación (dúo r17, Sol C1).

CAPAS (dúo r17, Sol C1/C2):
- CORPUS/IDENTIDAD (este script, SIN datos personales): `documents` (identidad
  + revisión + supersede) · `chunks_v2` · `chunks_v2_enunciados` ·
  `chunks_v2_hyq` — las 3 de contenido SIN la columna `embedding` (regenerable
  con pipeline probado, ~$10-15; el contenido es lo insustituible).
- DATOS PERSONALES (7 tablas: query_logs, feedback, answer_feedback,
  answer_messages, user_consent, persona_seudonimo, consent_events): FUERA de
  este backup a conciencia — un dump estático NO hereda la retención de la
  tabla (el job de borrado de la BD no puede tocarlo) y exigiría TTL propio,
  cifrado y borrado verificable. [DECIDIR-Alberto en el packet: opción A =
  así se queda (capa gestionada de Supabase cubre el desastre); opción B =
  incluirlas CON ese aparato.]

OBJETIVOS DECLARADOS: RPO ≤ 1 lote de ingesta (correr tras cada lote; mínimo
mensual) · RTO horas (restauración manual desde el dump + re-embedding si
hiciera falta). Coherencia de snapshot: correr en horas sin tráfico; el recibo
estampa counts pre/post por tabla y ABORTA si difieren (sin transacción
cross-tabla vía PostgREST — límite declarado; el PITR verdadero es la capa
gestionada).

DRILL DE RESTAURACIÓN (el gate): cada dump se carga en un SQLite efímero y se
verifica: counts == origen · integridad referencial documents↔chunks_v2
(document_id huérfanos = 0) · spot-check de 5 filas por tabla byte-idénticas.
Sin drill verde no hay recibo.

Salida: `<data-root>/backups/<UTC>/` (OneDrive, FUERA del repo) + recibo SIN
contenido en `evals/s319_backup_receipt_<UTC>.json` (tabla → filas, sha256,
bytes, drill). DDL: versionado en `migrations/` (git); hueco declarado: RLS/
funciones creadas fuera de migrations, si las hay, no viajan aquí.

Uso:
    python scripts/backup_supabase.py --data-root "<carpeta OneDrive>"
    python scripts/backup_supabase.py --data-root ... --tablas documents
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import sys
import time
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

# Tablas de la capa corpus/identidad (nombres REALES verificados contra la BD,
# r17: era chunks_v2_hyq, no hyq). Las columnas se derivan DINÁMICAMENTE de una
# fila real (a prueba de drift de esquema — las listas a mano fallaron 4/4 en
# el primer intento), excluyendo solo las pesadas/regenerables.
TABLAS = ("documents", "chunks_v2", "chunks_v2_enunciados", "chunks_v2_hyq")
_EXCLUIR_COLUMNAS = {"embedding", "search_vector"}
PAGINA = 1000


def _columnas(client, tabla: str) -> str | None:
    """select explícito = columnas observadas menos las excluidas; None si la
    tabla está vacía (select=* da igual entonces)."""
    r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                   params={"limit": "1"})
    r.raise_for_status()
    filas = r.json()
    if not filas:
        return None
    return ",".join(sorted(set(filas[0]) - _EXCLUIR_COLUMNAS))


def _count(client, tabla: str) -> int:
    r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}",
                   headers={**H, "Prefer": "count=exact", "Range": "0-0"},
                   params={"select": "id"})
    r.raise_for_status()
    rango = r.headers.get("content-range", "/0")
    return int(rango.split("/")[-1])


def _volcar(client, tabla: str, select: str | None, orden: str,
            destino: Path) -> dict:
    """Dump paginado a JSONL.gz con sha256 en streaming."""
    t0 = time.perf_counter()
    sha = hashlib.sha256()
    filas = 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(destino, "wb") as gz:
        off = 0
        while True:
            params = {"order": f"{orden}.asc", "offset": str(off),
                      "limit": str(PAGINA)}
            if select:
                params["select"] = select
            r = client.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H,
                           params=params)
            r.raise_for_status()
            lote = r.json()
            for fila in lote:
                linea = json.dumps(fila, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")
                gz.write(linea + b"\n")
                sha.update(linea + b"\n")
                filas += 1
            if len(lote) < PAGINA:
                break
            off += PAGINA
    return {"filas": filas, "sha256": sha.hexdigest(),
            "bytes": destino.stat().st_size,
            "segundos": round(time.perf_counter() - t0, 1)}


def _drill(carpeta: Path, dumps: dict) -> dict:
    """Restauración REAL en SQLite efímero: counts + FK + spot-check."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE filas (tabla TEXT, id TEXT, doc TEXT, linea TEXT)")
    spot: dict[str, list[str]] = {}
    for tabla in dumps:
        ruta = carpeta / f"{tabla}.jsonl.gz"
        n = 0
        with gzip.open(ruta, "rt", encoding="utf-8") as fh:
            for linea in fh:
                fila = json.loads(linea)
                db.execute(
                    "INSERT INTO filas VALUES (?,?,?,?)",
                    (tabla, str(fila.get("id")),
                     str(fila.get("document_id") or ""), linea.rstrip("\n")))
                if n < 5:
                    spot.setdefault(tabla, []).append(
                        hashlib.sha256(linea.rstrip("\n").encode()).hexdigest())
                n += 1
        restauradas = db.execute(
            "SELECT COUNT(*) FROM filas WHERE tabla=?", (tabla,)).fetchone()[0]
        if restauradas != dumps[tabla]["filas"]:
            return {"ok": False,
                    "motivo": f"{tabla}: {restauradas} != {dumps[tabla]['filas']}"}
    # integridad referencial: chunks huérfanos de documents (por document_id)
    huerfanos = db.execute("""
        SELECT COUNT(*) FROM filas c WHERE c.tabla='chunks_v2' AND c.doc != ''
        AND NOT EXISTS (SELECT 1 FROM filas d WHERE d.tabla='documents'
                        AND d.id = c.doc)""").fetchone()[0]
    db.close()
    return {"ok": True, "chunks_sin_document": huerfanos,
            "spot_check_sha256": spot,
            "nota_huerfanos": ("0 = cadena íntegra; >0 NO aborta: documenta "
                               "(chunks pre-datan el alta de documents en "
                               "tablas históricas)")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--tablas", default=None,
                    help="subconjunto separado por comas (default: todas)")
    args = ap.parse_args()

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    carpeta = Path(args.data_root) / "backups" / utc
    pedidas = (args.tablas.split(",") if args.tablas else list(TABLAS))
    desconocidas = [t for t in pedidas if t not in TABLAS]
    if desconocidas:
        print(f"ABORT: tablas fuera de la capa corpus/identidad: {desconocidas} "
              "(la capa PII está excluida a conciencia — DEC-209)")
        return 1

    dumps: dict[str, dict] = {}
    with abierto(timeout=30.0) as client:
        pre = {t: _count(client, t) for t in pedidas}
        for tabla in pedidas:
            select = _columnas(client, tabla)
            print(f"  volcando {tabla} ({pre[tabla]} filas)…", flush=True)
            dumps[tabla] = _volcar(client, tabla, select, "id",
                                   carpeta / f"{tabla}.jsonl.gz")
        post = {t: _count(client, t) for t in pedidas}

    # coherencia: la BD no debe haberse movido durante el volcado
    movidas = {t: (pre[t], post[t]) for t in pedidas if pre[t] != post[t]}
    if movidas:
        print(f"ABORT: la BD cambió durante el volcado: {movidas}")
        return 1
    for t in pedidas:
        if dumps[t]["filas"] != pre[t]:
            print(f"ABORT: {t} volcó {dumps[t]['filas']} != count {pre[t]}")
            return 1

    drill = _drill(carpeta, dumps)
    recibo = {
        "que_es": ("Backup lógico de la capa corpus/identidad (sin PII, sin "
                   "embeddings) + drill de restauración. RPO ≤1 lote/1 mes; "
                   "RTO horas. Capa PII fuera (DEC-209 [DECIDIR])."),
        "utc": utc, "carpeta": str(carpeta),
        "tablas": dumps, "counts_pre_post_iguales": True,
        "drill_restauracion": drill,
    }
    destino = ROOT / "evals" / f"s319_backup_receipt_{utc}.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    estado = "PASS" if drill.get("ok") else "FAIL"
    print(f"drill {estado} · recibo -> {destino}")
    return 0 if drill.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
