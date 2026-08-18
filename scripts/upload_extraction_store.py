# -*- coding: utf-8 -*-
"""s325b — Subir el extraction store a Supabase Storage (bucket `extraction`).

POR QUÉ. El store (`data/extraction/<config>/*.json`) vive SOLO en OneDrive: es lo
último que ata la fase de enunciados y las re-ingestas a tener el PC encendido.
Medido en s325b: `agent_anthropic-sonnet-45` = 1.143 JSON / 353,7 MB · `llm` = 28 / 2,6 MB.
Cada fichero se llama `<sha256-del-PDF>.json`, que es la misma identidad que
`documents.source_pdf_sha256`.

DÓNDE SE CORRE. En una máquina que VEA OneDrive (es decir: en local) y con
SUPABASE_URL + SUPABASE_SERVICE_KEY. Mismo patrón que
`scripts/s315_upload_manuales_storage.py`, del que hereda: dry-run por defecto,
`--aplicar` explícito, reanudable y con recibo.

    python scripts/upload_extraction_store.py "<data-root>"             # dry-run
    python scripts/upload_extraction_store.py "<data-root>" --aplicar
    python scripts/upload_extraction_store.py "<data-root>" --verificar  # no escribe

MANIFIESTO. Cada config sube `_manifest.json` = {nombre: {sha256, bytes, source_path,
sha_pdf}}. Hace tres trabajos: `listar()` del resolutor lee UN objeto en vez de paginar
1.143 (la API pagina de 1.000 en 1.000 y ya estamos por encima); `source_path`/`sha_pdf`
son las cabeceras que `enunciados_pass._build_sha_map` extrae hoy leyendo los 1.143
ficheros, así que el consumidor remoto las obtiene con ese mismo GET; y el `sha256` es
lo que decide qué hay que re-subir.

DECIDIR QUÉ SE SALTA (dúo s325b, hallazgo de Fable): el skip se decide por **sha contra
el manifiesto remoto anterior**, NUNCA por tamaño. Con el criterio de tamaño, un JSON
re-extraído que pesara igual se saltaba pero el manifiesto se regeneraba con el sha
local nuevo — un manifiesto que miente sobre el bucket, y `--verificar` en verde.

El bucket es PRIVADO a propósito: `manuales` es público-por-URL porque son manuales
de fabricante que el bot sirve a los técnicos (s315); el store es contenido DERIVADO
y se lee con la service key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env", override=False)

BUCKET = "extraction"
CONFIGS_POR_DEFECTO = ("agent_anthropic-sonnet-45", "llm")
MANIFIESTO = "_manifest.json"
CABECERA = 600  # bytes: lo que `_build_sha_map` de enunciados_pass lee de cada JSON
RECIBO = REPO / "evals" / "s325b_extraction_upload_v1.json"
PAGINA = 1000


def cabecera_de(datos: bytes) -> dict:
    """`source_path` y `sha_pdf` leídos como los lee `_build_sha_map`."""
    cab = datos[:CABECERA].decode("utf-8", "ignore")
    mm = re.search(r'"source_path":\s*"([^"]+)"', cab)
    ms = re.search(r'"sha256":\s*"([0-9a-f]{16,})"', cab)
    return {"source_path": mm.group(1) if mm else None,
            "sha_pdf": ms.group(1) if ms else None}


def _cliente() -> tuple[str, dict]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        sys.exit("GATE: faltan SUPABASE_URL / SUPABASE_SERVICE_KEY")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}


def listar_remoto(url: str, h: dict, config: str) -> set[str]:
    """Nombres realmente presentes en el bucket (paginado)."""
    nombres: set[str] = set()
    offset = 0
    while True:
        r = httpx.post(
            f"{url}/storage/v1/object/list/{BUCKET}",
            headers=h, timeout=60,
            json={"prefix": f"{config}/", "limit": PAGINA, "offset": offset,
                  "sortBy": {"column": "name", "order": "asc"}},
        )
        r.raise_for_status()
        lote = r.json()
        nombres.update(o["name"] for o in lote)
        if len(lote) < PAGINA:
            return nombres
        offset += PAGINA


def manifiesto_remoto(url: str, h: dict, config: str) -> dict[str, dict]:
    """El manifiesto que hay HOY en el bucket ({} si aún no existe).

    Solo un 404 significa "todavia no hay". Un 500 o una auth caida tratados como {}
    producirian 1.143 falsos DIFIERE en `--verificar` y una re-subida entera en
    `--aplicar`: fail-safe, pero ruidoso y caro (Fable, ronda 2). Mejor parar.
    """
    r = httpx.get(f"{url}/storage/v1/object/{BUCKET}/{config}/{MANIFIESTO}",
                  headers=h, timeout=60)
    if r.status_code == 404:
        return {}
    if r.status_code >= 400:
        sys.exit(f"GATE: el manifiesto de {config} respondio HTTP {r.status_code} — "
                 f"no se puede decidir que subir a ciegas")
    try:
        return json.loads(r.content.decode("utf-8"))
    except json.JSONDecodeError:
        sys.exit(f"GATE: el manifiesto de {config} no es JSON valido")


def subir(url: str, h: dict, clave: str, datos: bytes) -> tuple[bool, str]:
    r = httpx.post(
        f"{url}/storage/v1/object/{BUCKET}/{clave}",
        headers={**h, "Content-Type": "application/json", "x-upsert": "true"},
        content=datos, timeout=180,
    )
    return r.status_code < 300, f"HTTP {r.status_code} {r.text[:120]}"


def procesar(config: str, carpeta: Path, url: str, h: dict, args) -> tuple[dict, int]:
    locales = sorted(p for p in carpeta.glob("*.json") if p.name != MANIFIESTO)
    print(f"\n=== {config}: {len(locales)} ficheros en local ===")
    presentes = listar_remoto(url, h, config)
    previo = manifiesto_remoto(url, h, config)
    manifiesto: dict[str, dict] = {}
    subidos = saltados = sin_cabecera = 0
    fallos = 0  # POR CONFIG (dúo s325b): un fallo aquí no debe bloquear otra config

    for i, p in enumerate(locales, 1):
        datos = p.read_bytes()
        sha = hashlib.sha256(datos).hexdigest()
        cab = cabecera_de(datos)
        # Una cabecera que no aparece en los primeros 600 bytes deja `source_path`
        # a null, y entonces `_build_sha_map` salta ese documento SIN avisar: queda
        # invisible para la resolucion por nombre. Antes era un silencio; ahora se
        # cuenta y se declara en el recibo (Fable, ronda 2).
        if not (cab.get("source_path") and cab.get("sha_pdf")):
            sin_cabecera += 1
        manifiesto[p.name] = {"sha256": sha, "bytes": len(datos), **cab}

        # El objeto cuenta como subido solo si ESTÁ y su sha registrado coincide.
        registrado = (previo.get(p.name) or {}).get("sha256")
        al_dia = p.name in presentes and registrado == sha

        if args.verificar:
            if not al_dia:
                motivo = ("ausente del bucket" if p.name not in presentes
                          else "sin sha en el manifiesto" if not registrado
                          else "sha distinto")
                print(f"  DIFIERE: {p.name} ({motivo})")
                fallos += 1
            elif args.profundo:
                # Sin esto la verificacion es CIRCULAR: compara el sha local con el
                # que declara el propio manifiesto, que se genero de ese mismo local
                # (hallazgo de Sol, ronda 2). Solo bajando el objeto se detecta una
                # corrupcion del bucket con el manifiesto intacto.
                r = httpx.get(f"{url}/storage/v1/object/{BUCKET}/{config}/{p.name}",
                              headers=h, timeout=120)
                real = hashlib.sha256(r.content).hexdigest() if r.status_code < 400 else None
                if real != sha:
                    print(f"  CORRUPTO en el bucket: {p.name} "
                          f"(HTTP {r.status_code}, sha {(real or '?')[:12]} vs {sha[:12]})")
                    fallos += 1
            continue
        if al_dia:
            saltados += 1
            continue
        if not args.aplicar:
            print(f"  [dry-run] subiria {p.name} ({len(datos)} B)")
            subidos += 1
            continue
        ok, detalle = subir(url, h, f"{config}/{p.name}", datos)
        if ok:
            subidos += 1
            if subidos % 100 == 0:
                print(f"  ... {subidos} subidos ({i}/{len(locales)})")
        else:
            fallos += 1
            print(f"  ERROR {p.name}: {detalle}")

    # El manifiesto se REGENERA al final, y SOLO si todo lo de esta config subió: es
    # la foto de lo que el resolutor verá, y una foto parcial haría que `listar()`
    # devolviera un store corto sin que nada avise.
    if args.aplicar and not fallos:
        ok, detalle = subir(url, h, f"{config}/{MANIFIESTO}",
                            json.dumps(manifiesto, ensure_ascii=False, indent=1).encode("utf-8"))
        if not ok:
            fallos += 1
            print(f"  ERROR subiendo el manifiesto: {detalle}")

    # Huérfanos: en el bucket pero ya no en local. NO se borran (el store es
    # acumulativo por decisión), pero se listan en el recibo.
    huerfanos = sorted(presentes - {p.name for p in locales} - {MANIFIESTO})
    print(f"  resumen: {subidos} subidos · {saltados} ya estaban · "
          f"{len(huerfanos)} huerfanos · {fallos} fallos")
    if sin_cabecera:
        print(f"  AVISO: {sin_cabecera} extraccion(es) sin source_path/sha256 en los "
              f"primeros {CABECERA} bytes — invisibles para el mapa doc->sha")
    return {"locales": len(locales), "subidos": subidos, "saltados": saltados,
            "sin_cabecera": sin_cabecera,
            "huerfanos_en_bucket": huerfanos[:50], "huerfanos_total": len(huerfanos),
            "fallos": fallos}, fallos


def main() -> int:
    ap = argparse.ArgumentParser(description="Sube el extraction store al bucket `extraction`")
    ap.add_argument("data_root", help="raíz del corpus (la carpeta OneDrive con data/extraction)")
    ap.add_argument("--config", action="append", default=None,
                    help=f"config a subir (repetible). Por defecto: {', '.join(CONFIGS_POR_DEFECTO)}")
    ap.add_argument("--aplicar", action="store_true", help="escribe de verdad (si no, dry-run)")
    ap.add_argument("--verificar", action="store_true",
                    help="compara local vs MANIFIESTO por SHA; no escribe nada")
    ap.add_argument("--profundo", action="store_true",
                    help="con --verificar: DESCARGA cada objeto y lo hashea (lento: "
                         "354 MB) — es lo unico que detecta un objeto corrupto cuyo "
                         "manifiesto siga intacto")
    args = ap.parse_args()

    configs = tuple(args.config) if args.config else CONFIGS_POR_DEFECTO
    raiz = Path(args.data_root) / "data" / "extraction"
    if not raiz.is_dir():
        sys.exit(f"GATE: no existe {raiz} — ¿data-root correcto? (esto se corre en LOCAL)")

    url, h = _cliente()
    informe = {"generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "modo": "verificar" if args.verificar else ("aplicar" if args.aplicar else "dry-run"),
               "bucket": BUCKET, "configs": {}}
    total_fallos = 0

    for config in configs:
        carpeta = raiz / config
        if not carpeta.is_dir():
            print(f"AVISO: {carpeta} no existe — se salta")
            continue
        informe["configs"][config], fallos = procesar(config, carpeta, url, h, args)
        total_fallos += fallos

    informe["fallos"] = total_fallos
    if args.aplicar or args.verificar:
        RECIBO.parent.mkdir(parents=True, exist_ok=True)
        RECIBO.write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRecibo: {RECIBO.relative_to(REPO)}")

    print(f"\n{'FALLOS: ' + str(total_fallos) if total_fallos else 'sin fallos'}")
    return 1 if total_fallos else 0


if __name__ == "__main__":
    sys.exit(main())
