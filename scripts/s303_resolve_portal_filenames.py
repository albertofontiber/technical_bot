"""s303 — resuelve título→nombre de fichero real de los enlaces del catálogo de portales.

Lee `data/catalog_portales/s303_portales_notifier_morley_v1.json` y, para cada enlace
único, obtiene el nombre de fichero real de la cabecera `Content-Disposition`.

REGLAS DE CADENCIA (runbook docs/CORPUS_NOTIFIER_MORLEY.md §2 — WAF de Akamai):
  - estrictamente secuencial, 3 s entre peticiones
  - HEAD si el servidor devuelve Content-Disposition en HEAD; si no, GET con stream y
    abortar en cuanto lleguen las cabeceras (NO se descargan los PDF)
  - 3× 403 seguidos -> pausa de 10 min y reanudar; si vuelve a bloquear -> abortar
  - progreso incremental a disco tras cada petición

Uso:
    python scripts/s303_resolve_portal_filenames.py [--limit N] [--probe]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog_portales" / "s303_portales_notifier_morley_v1.json"
OUT = ROOT / "data" / "catalog_portales" / "s303_resolved_filenames_v1.json"

DELAY = 3.0
MAX_403_STREAK = 3
COOLDOWN = 600  # 10 min
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def fix_mojibake(s: str | None) -> str | None:
    """Cabeceras HTTP = latin-1 (RFC 9110), pero el portal manda UTF-8:
    'programación' llega como 'programacioÌ\\x81n'. Se repara el round-trip."""
    if not s or all(ord(c) < 128 for c in s):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_content_disposition(cd: str | None) -> str | None:
    cd = fix_mojibake(cd)
    if not cd:
        return None
    # filename*=UTF-8''...
    for part in cd.split(";"):
        part = part.strip()
        if part.lower().startswith("filename*="):
            val = part.split("=", 1)[1].strip()
            if "''" in val:
                val = val.split("''", 1)[1]
            return urllib.parse.unquote(val).strip('"')
    for part in cd.split(";"):
        part = part.strip()
        if part.lower().startswith("filename="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


def cd_size(cd: str | None) -> str | None:
    if not cd:
        return None
    for part in cd.split(";"):
        part = part.strip()
        if part.lower().startswith("size="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


def filename_from_url(final_url: str) -> str | None:
    """Morley redirige el enlace ZOO al fichero estático: el nombre está en la URL final."""
    path = urllib.parse.urlparse(final_url).path
    base = urllib.parse.unquote(path.rsplit("/", 1)[-1])
    if base.lower().endswith((".pdf", ".zip", ".doc", ".docx", ".exe", ".rar")):
        return base
    return None


def _pack(r, method: str, src: str, fn: str | None, extra: dict | None = None) -> dict:
    out = {
        "status": r.status_code,
        "filename": fn,
        "filename_source": src,
        "method": method,
        "content_type": r.headers.get("Content-Type"),
        "content_length": r.headers.get("Content-Length"),
        "cd_size": cd_size(r.headers.get("Content-Disposition")),
        "final_url": r.url,
    }
    if extra:
        out.update(extra)
    return out


def resolve_one(sess: requests.Session, url: str, referer: str) -> dict:
    """Devuelve {status, filename, filename_source, method, ...}.

    Dos formas de resolver, ambas sin descargar el PDF:
      - Notifier: el enlace ZOO responde 200 con `Content-Disposition: attachment; filename=...`
      - Morley:   el enlace ZOO REDIRIGE al fichero estático -> el nombre está en la URL final
    """
    headers = {"Referer": referer}
    head_err = None
    # 1) HEAD (suficiente en los dos portales)
    try:
        r = sess.head(url, headers=headers, allow_redirects=True, timeout=30)
        if r.status_code == 403:
            return {"status": 403, "filename": None, "method": "HEAD", "error": "403 (WAF)"}
        if r.status_code == 200:
            fn = parse_content_disposition(r.headers.get("Content-Disposition"))
            if fn:
                return _pack(r, "HEAD", "content-disposition", fn)
            fn = filename_from_url(r.url)
            if fn:
                return _pack(r, "HEAD", "redirect-url", fn)
        head_err = f"HEAD status={r.status_code} sin nombre"
    except Exception as exc:  # noqa: BLE001
        head_err = f"HEAD {type(exc).__name__}: {exc}"

    # 2) GET stream, abortar tras cabeceras (fallback)
    try:
        r = sess.get(url, headers=headers, allow_redirects=True, timeout=30, stream=True)
        fn = parse_content_disposition(r.headers.get("Content-Disposition")) or filename_from_url(
            r.url
        )
        src = "content-disposition" if r.headers.get("Content-Disposition") else "redirect-url"
        out = _pack(r, "GET", src if fn else None, fn, {"head_note": head_err})
        r.close()
        if not fn:
            out["error"] = "403 (WAF)" if r.status_code == 403 else "sin nombre de fichero"
        return out
    except Exception as exc:  # noqa: BLE001
        return {
            "status": None,
            "filename": None,
            "method": "GET",
            "error": f"{type(exc).__name__}: {exc}",
            "head_note": head_err,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--probe", action="store_true", help="3 peticiones de prueba, no guarda")
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    # url -> primera entrada que la usa (para referer/site)
    order: list[str] = []
    meta: dict[str, dict] = {}
    for i, e in enumerate(catalog):
        for u in e.get("links") or []:
            if u not in meta:
                meta[u] = {"site": e["site"], "cat": e["cat"], "title": e["title"], "idx": i}
                order.append(u)

    done: dict[str, dict] = {}
    if OUT.exists() and not args.probe:
        done = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"[resume] {len(done)} ya resueltos", flush=True)

    todo = [u for u in order if u not in done]
    if args.probe:
        todo = order[:3]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[start] {len(todo)} enlaces pendientes de {len(order)} únicos", flush=True)

    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": UA,
            "Accept": "*/*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
    )

    streak403 = 0
    cooldowns_used = 0
    t0 = time.time()
    for n, url in enumerate(todo, 1):
        m = meta[url]
        referer = f"https://www.{'notifier' if m['site']=='notifier' else 'morley-ias'}.es/"
        res = resolve_one(sess, url, referer)
        res["site"] = m["site"]
        res["cat"] = m["cat"]
        res["title"] = m["title"]
        res["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        done[url] = res

        if res.get("status") == 403:
            streak403 += 1
        elif res.get("status") == 200:
            streak403 = 0

        if n % 10 == 0 or res.get("status") != 200:
            el = time.time() - t0
            print(
                f"[{n}/{len(todo)}] {res.get('status')} {res.get('method')} "
                f"{(res.get('filename') or res.get('error') or '')[:60]} "
                f"| {el/60:.1f}min",
                flush=True,
            )

        if not args.probe and (n % 5 == 0 or n == len(todo)):
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")

        if streak403 >= MAX_403_STREAK:
            if cooldowns_used >= 1:
                print(
                    f"[ABORT] 2º bloqueo del WAF tras {n} peticiones. "
                    f"Resueltos totales: {sum(1 for v in done.values() if v.get('filename'))}",
                    flush=True,
                )
                OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
                return 2
            cooldowns_used += 1
            print(f"[WAF] 3× 403 seguidos en n={n} -> cooldown 10 min", flush=True)
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(COOLDOWN)
            streak403 = 0
            continue

        if n < len(todo):
            time.sleep(DELAY)

    if not args.probe:
        OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in done.values() if v.get("filename"))
    print(f"[done] {ok}/{len(done)} con nombre de fichero. {(time.time()-t0)/60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
