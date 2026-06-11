#!/usr/bin/env python3
"""s62_audit43.py — AUDIT read-only de identidad de variantes / near-duplicados (TECH_DEBT #43).

Dimensiona ANTES de contratar (Protocolo 4; DEC-042: el gate s61 midió que ediciones
casi idénticas conviviendo monopolizan el top-5 de un reranker de pares). Nivel de
análisis = DOCUMENTO (la unidad del contrato de supersesión), no chunk.

Qué hace (todo read-only):
  1. Baja `documents` (metadata: product_model, manufacturer, revision, status,
     document_family, supersedes_id/superseded_by_id — el ESQUEMA de supersesión ya
     existe, está sin poblar) y los chunks de chunks_v2 (id, document_id, content).
  2. Firma de contenido por doc: shingles de 8 palabras sobre el content concatenado
     normalizado (norm_ocr), cap de muestreo declarado; idioma por heurística de
     stopwords (la columna language está vacía en 974/1065 — heurística DECLARADA).
  3. Pares near-dup DENTRO de cada fabricante (bloques): Jaccard de shingle-sets.
     Umbrales = LENTE DE INVENTARIO, no knob: clusters reportados a 0.7 Y 0.9
     (union-find por umbral), pares sueltos desde 0.5.
  4. Clasifica cada cluster en buckets:
       B1 revisión-pura      mismo modelo + mismo idioma (candidato a supersesión)
       B2 hermanas-de-serie  modelo DISTINTO + mismo idioma (identidad series/applies_to)
       B4 dup-exacto         mismo sha256 del PDF o shingle-set idéntico
     B3 variantes-de-mercado (mismo modelo, idioma DISTINTO) NO sale de shingles
     (traducciones no comparten n-gramas) → se detecta por METADATA aparte.
  5. Cruce con el eval: golds del gate s61 (`evals/s61_gate_pools.json`) cuyo pool
     contiene ≥2 docs del mismo cluster (la condición que mordió en cat012).

Salida: evals/s62_audit43.yaml + resumen por consola.
Uso:    python scripts/s62_audit43.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from strict_match import norm_ocr  # noqa: E402

URL = os.environ["SUPABASE_URL"]
H = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
     "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

OUT = ROOT / "evals" / "s62_audit43.yaml"
POOLS_S61 = ROOT / "evals" / "s61_gate_pools.json"
CHUNKS_TABLE = "chunks_v2"

SHINGLE_W = 8          # palabras por shingle
SHINGLE_CAP = 4000     # muestreo determinista de shingles por doc (hash mod)
PAIR_FLOOR = 0.5       # pares reportados desde aquí
THRESHOLDS = (0.7, 0.9)

# Heurística de idioma (DECLARADA): stopwords distintivas; gana el mayor conteo.
_LANG_MARKERS = {
    "es": {"el", "la", "los", "las", "que", "para", "una", "con", "del", "más"},
    "en": {"the", "and", "with", "for", "this", "that", "from", "are", "not"},
    "de": {"der", "die", "das", "und", "nicht", "für", "mit", "ist"},
    "fr": {"le", "les", "des", "est", "pour", "dans", "une", "avec"},
    "it": {"il", "che", "per", "della", "sono", "con", "una", "non"},
    "pt": {"não", "uma", "para", "como", "dos", "mais", "ser"},
}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def fetch_all(table: str, select: str, page: int = 1000) -> list[dict]:
    rows, offset = [], 0
    with httpx.Client(timeout=60.0) as c:
        while True:
            r = c.get(f"{URL}/rest/v1/{table}", headers=H,
                      params={"select": select, "limit": str(page), "offset": str(offset)})
            r.raise_for_status()
            batch = r.json()
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page


def detect_lang(text: str) -> str:
    toks = Counter(re.findall(r"[a-záéíóúñüäöß]+", text[:30000].lower()))
    scores = {lang: sum(toks[w] for w in ws) for lang, ws in _LANG_MARKERS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 5 else "??"


def shingles(text: str) -> frozenset[int]:
    # crc32 (estable entre procesos — hash() varía con PYTHONHASHSEED y rompería
    # la reproducibilidad del artefacto); muestreo determinista por valor.
    import zlib
    words = norm_ocr(text).split()
    out = set()
    for i in range(len(words) - SHINGLE_W + 1):
        out.add(zlib.crc32(" ".join(words[i:i + SHINGLE_W]).encode("utf-8")))
    if len(out) > SHINGLE_CAP:
        out = set(sorted(out)[:SHINGLE_CAP])
    return frozenset(out)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class UnionFind:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def norm_model(m: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (m or "").lower())


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("1) documents…")
    docs = fetch_all("documents",
                     "id,source_pdf_filename,source_pdf_sha256,manufacturer,product_model,"
                     "doc_type,language,revision,revision_date,status,document_family,"
                     "supersedes_id,superseded_by_id")
    by_id = {d["id"]: d for d in docs}
    print(f"   {len(docs)} docs | document_family poblada: "
          f"{sum(1 for d in docs if d.get('document_family'))} | supersedes poblada: "
          f"{sum(1 for d in docs if d.get('supersedes_id') or d.get('superseded_by_id'))}")

    print("2) chunks (content por doc)…")
    chunks = fetch_all(CHUNKS_TABLE, "id,document_id,content", page=1000)
    text_by_doc: dict[str, list[str]] = defaultdict(list)
    for c in chunks:
        if c.get("document_id"):
            text_by_doc[c["document_id"]].append(c.get("content") or "")
    docs_con_chunks = [d for d in docs if d["id"] in text_by_doc]
    print(f"   {len(chunks)} chunks | docs con chunks: {len(docs_con_chunks)} "
          f"(documents sin chunks: {len(docs) - len(docs_con_chunks)})")

    print("3) firmas (shingles + idioma heurístico)…")
    sig, lang = {}, {}
    for d in docs_con_chunks:
        full = "\n".join(text_by_doc[d["id"]])
        sig[d["id"]] = shingles(full)
        lang[d["id"]] = (d.get("language") or detect_lang(full))

    print("4) pares near-dup por fabricante…")
    by_manu = defaultdict(list)
    for d in docs_con_chunks:
        by_manu[d.get("manufacturer") or "?"].append(d["id"])
    pairs = []
    for manu, ids in sorted(by_manu.items()):
        for a, b in combinations(ids, 2):
            j = jaccard(sig[a], sig[b])
            if j >= PAIR_FLOOR:
                pairs.append((round(j, 3), a, b))
    pairs.sort(reverse=True)
    print(f"   pares J>={PAIR_FLOOR}: {len(pairs)}")

    def describe(did: str) -> dict:
        d = by_id[did]
        return {"file": d.get("source_pdf_filename"), "model": d.get("product_model"),
                "rev": d.get("revision"), "lang": lang.get(did, "?"),
                "n_chunks": len(text_by_doc.get(did, []))}

    resultado_umbral = {}
    for th in THRESHOLDS:
        uf = UnionFind()
        for j, a, b in pairs:
            if j >= th:
                uf.union(a, b)
        groups = defaultdict(list)
        for did in {x for j, a, b in pairs if j >= th for x in (a, b)}:
            groups[uf.find(did)].append(did)
        clusters = []
        b_count = Counter()
        for members in groups.values():
            if len(members) < 2:
                continue
            models = {norm_model(by_id[m].get("product_model")) for m in members}
            langs = {lang.get(m, "?") for m in members}
            shas = {by_id[m].get("source_pdf_sha256") for m in members}
            sigs = {sig[m] for m in members}
            if len(shas) < len(members) or len(sigs) == 1:
                bucket = "B4-dup-exacto"
            elif len(langs) > 1:
                bucket = "B3-mezcla-idioma(revisar)"   # shingles no deberían juntar idiomas
            elif len(models) == 1:
                bucket = "B1-revision-pura"
            else:
                bucket = "B2-hermanas-serie"
            b_count[bucket] += 1
            js = [j for j, a, b in pairs if j >= th and uf.find(a) == uf.find(members[0])]
            clusters.append({
                "bucket": bucket, "n_docs": len(members),
                "jaccard_min": min(js) if js else None,
                "docs": [describe(m) for m in sorted(members)],
            })
        clusters.sort(key=lambda c: (c["bucket"], -c["n_docs"]))
        resultado_umbral[f"jaccard_{th}"] = {
            "n_clusters": len(clusters), "buckets": dict(b_count), "clusters": clusters}

    print("5) B3 variantes-de-mercado por METADATA (mismo modelo, idioma distinto)…")
    b3 = []
    by_model = defaultdict(list)
    for d in docs_con_chunks:
        nm = norm_model(d.get("product_model"))
        if nm:
            by_model[(d.get("manufacturer"), nm)].append(d["id"])
    for (manu, nm), ids in sorted(by_model.items()):
        langs_here = {lang.get(i, "?") for i in ids}
        if len(ids) >= 2 and len(langs_here - {"??"}) > 1:
            b3.append({"manufacturer": manu, "model_norm": nm,
                       "langs": sorted(langs_here),
                       "docs": [describe(i) for i in sorted(ids)]})

    print("6) cruce con pools del gate s61…")
    cruce = []
    if POOLS_S61.exists():
        pools = json.loads(POOLS_S61.read_text(encoding="utf-8"))
        # clusters al umbral bajo (0.7) como referencia de riesgo
        uf = UnionFind()
        for j, a, b in pairs:
            if j >= THRESHOLDS[0]:
                uf.union(a, b)
        for qid in sorted(pools):
            if qid == "meta":
                continue
            doc_ids = [c.get("document_id") for c in pools[qid]["pool"] if c.get("document_id")]
            roots = Counter(uf.find(d) for d in doc_ids if d in sig)
            multi = {r: n for r, n in roots.items()
                     if n >= 2 and any(j >= THRESHOLDS[0] and uf.find(a) == r
                                       for j, a, b in pairs)}
            if multi:
                cruce.append({"qid": qid,
                              "clusters_en_pool": [
                                  {"n_docs_del_cluster_en_pool": n,
                                   "ejemplo": describe(next(d for d in doc_ids
                                                            if d in sig and uf.find(d) == r))}
                                  for r, n in sorted(multi.items(), key=lambda x: -x[1])]})

    out = {
        "meta": {
            "at": _now(), "git": _git(), "corpus": CHUNKS_TABLE,
            "metodo": {
                "nivel": "documento", "shingle_palabras": SHINGLE_W,
                "shingle_cap_muestreo": SHINGLE_CAP, "pair_floor": PAIR_FLOOR,
                "umbrales_lente": list(THRESHOLDS),
                "bloques": "por fabricante",
                "idioma": "columna si existe; si no, heurística stopwords (DECLARADA)",
                "B3_por_metadata": "las traducciones no comparten shingles → B3 se detecta por metadata, no por contenido",
            },
            "esquema_supersesion_existente": {
                "columnas": ["status", "revision", "revision_date", "document_family",
                              "supersedes_id", "superseded_by_id"],
                "document_family_poblada": sum(1 for d in docs if d.get("document_family")),
                "supersedes_poblada": sum(1 for d in docs
                                          if d.get("supersedes_id") or d.get("superseded_by_id")),
                "revision_poblada": sum(1 for d in docs if d.get("revision")),
                "revision_date_poblada": sum(1 for d in docs if d.get("revision_date")),
                "status_dist": dict(Counter(d.get("status") for d in docs)),
            },
            "totales": {"documents": len(docs), "docs_con_chunks": len(docs_con_chunks),
                        "docs_sin_chunks": len(docs) - len(docs_con_chunks),
                        "chunks": len(chunks)},
        },
        "near_dups_contenido": resultado_umbral,
        "b3_variantes_mercado_metadata": {"n_grupos": len(b3), "grupos": b3},
        "cruce_eval_pools_s61": {"n_golds_afectados": len(cruce), "golds": cruce},
    }
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110),
                   encoding="utf-8")
    print(f"\nOK → {OUT.name}")
    for th in THRESHOLDS:
        r = out["near_dups_contenido"][f"jaccard_{th}"]
        print(f"  J>={th}: {r['n_clusters']} clusters {r['buckets']}")
    print(f"  B3 (metadata): {len(b3)} grupos | golds con cluster en pool: {len(cruce)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
