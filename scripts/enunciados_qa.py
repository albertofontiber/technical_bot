#!/usr/bin/env python3
"""enunciados_qa.py — QA GENERALIZADO por-enunciado (T0-3, plan s94b v2 / dúo F4).

A diferencia del QA del piloto (keyed a hechos-objetivo conocidos), este opera sin
valor-objetivo — es el gate del PASE corpus:

(a) FIDELIDAD: todo token numérico/código del enunciado (fuera de la whitelist de
    metadata inyectada: pm/manufacturer/source_file del padre) existe en la región fuente.
(b) ANTI-MISPAIRING A NIVEL DE FILA (dúo s94b F4 — el v2 del piloto era nivel-página):
    para CADA token-valor del enunciado debe existir UNA MISMA fila/línea fuente que
    contenga el token Y ≥1 discriminador del enunciado. Para tablas con `rows`, la
    "fila extendida" = fila + cabecera (rows[0]) — los discriminadores viven en la
    cabecera, no en la celda.
(c) COBERTURA (por doc/página): páginas-con-tabla cubiertas por ≥1 enunciado / total —
    el QA-rate mide fidelidad de lo GENERADO; esto mide lo que FALTA (dúo respuesta-B).

Modo calibración (--calibrate): corre (a)+(b) sobre los 368 candidatos del PILOTO y
verifica que (1) la tasa de pass reproduce ~la del piloto y (2) las 2 alucinaciones
REALES conocidas siguen cazadas. Es el gate de validez del instrumento antes de T1.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

_STOP = {"de", "la", "el", "en", "del", "los", "las", "un", "una", "por", "para", "con",
         "es", "se", "que", "central", "panel", "manual", "seccion", "tabla", "pagina",
         "sistema", "the", "and", "for", "with"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ]+", " ", s)).strip()


def tokens_valor(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9./+-]{1,}", _norm(text))
            if any(ch.isdigit() for ch in t)}


def discriminadores(text: str) -> list:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", _norm(text))
            if w not in _STOP and not any(ch.isdigit() for ch in w)]


def region_filas(items: list) -> list[str]:
    """Líneas de texto + filas-extendidas (fila+cabecera) de los items de una región."""
    filas = []
    for it in items:
        md = it.get("md") or it.get("text") or it.get("value") or ""
        filas.extend(ln for ln in md.splitlines() if ln.strip())
        rows = it.get("rows") or []
        if rows:
            head = " ".join(str(h) for h in rows[0])
            for row in rows[1:]:
                filas.append(head + " | " + " | ".join(str(c) for c in row))
    return filas


def qa_statement(text: str, items: list, whitelist_meta: str = "") -> tuple[bool, str]:
    """(a) fidelidad + (b) anti-mispairing fila-nivel. Devuelve (pass, motivo)."""
    filas = region_filas(items)
    filas_norm = [_norm(f) for f in filas]
    src_norm = " \n ".join(filas_norm)
    wl = tokens_valor(whitelist_meta)
    vals = tokens_valor(text) - wl
    for t in sorted(vals):
        if not re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", src_norm):
            return False, f"(a) token '{t}' no existe en la región"
    disc = discriminadores(text)
    for t in sorted(vals):
        pat = re.compile(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])")
        lineas_t = [f for f in filas_norm if pat.search(f)]
        if lineas_t and disc and not any(any(d in f for d in disc) for f in lineas_t):
            return False, f"(b) valor '{t}' sin discriminador en su fila fuente"
    return True, ""


def cobertura_pagina(items: list, statements: list[str]) -> float | None:
    """% de items-tabla de la página con ≥1 enunciado que referencia algún valor suyo."""
    tablas = [it for it in items if it.get("rows")]
    if not tablas:
        return None
    stmt_tokens = set().union(*(tokens_valor(s) for s in statements)) if statements else set()
    cubiertas = 0
    for it in tablas:
        vals_tabla = tokens_valor(" ".join(" ".join(str(c) for c in row)
                                           for row in (it.get("rows") or [])))
        if vals_tabla & stmt_tokens:
            cubiertas += 1
    return cubiertas / len(tablas)


def calibrate() -> int:
    from s94_f1_generate import store_pages
    import httpx
    from dotenv import load_dotenv
    load_dotenv(".env", override=False)
    from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
    d = json.load(open("evals/s94_f1_candidates.json", encoding="utf-8"))
    pids = sorted({c["parent_id"] for c in d["candidatos"]})
    meta = {}
    H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    for i in range(0, len(pids), 40):
        q = ",".join(f'"{x}"' for x in pids[i:i + 40])
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=H,
                      params={"select": "id,product_model,manufacturer,source_file",
                              "id": f"in.({q})"}, timeout=30)
        for x in r.json():
            meta[x["id"]] = x
    stats = {}
    conocidas_v2 = [(c["qid"], c["text"][:60]) for c in d["candidatos"]
                    if not c["qa_pass"] and c["qa_motivo"].startswith("token")]
    cazadas, nuevos_flags = 0, []
    for c in d["candidatos"]:
        pages = store_pages(c["anchor"]["sha"])
        pidx = c["anchor"]["page_idx"]
        items = pages[pidx].get("items", []) if pidx < len(pages) and isinstance(pages[pidx], dict) else []
        m = meta.get(c["parent_id"]) or {}
        wl = " ".join(str(m.get(k) or "") for k in ("product_model", "manufacturer", "source_file"))
        ok, motivo = qa_statement(c["text"], items, wl)
        s = stats.setdefault(c["arm"], [0, 0])
        s[0] += 1
        if not ok:
            s[1] += 1
            if not c["qa_pass"]:
                cazadas += 1
            elif len(nuevos_flags) < 8:
                nuevos_flags.append((c["arm"], c["qid"], motivo, c["text"][:70]))
    print("calibración QA-generalizado sobre los 368 del piloto:")
    for arm, (n, fail) in sorted(stats.items()):
        print(f"  {arm}: pass {n-fail}/{n} ({100*(n-fail)/n:.1f}%)")
    print(f"  alucinaciones conocidas del piloto (v2): {len(conocidas_v2)} → cazadas por el generalizado: {cazadas}")
    print("  nuevos flags (muestra):")
    for f in nuevos_flags:
        print(f"    {f[0]} [{f[1]}] {f[2][:50]} :: {f[3]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(calibrate() if "--calibrate" in sys.argv else 0)
