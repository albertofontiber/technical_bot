#!/usr/bin/env python3
"""s287 P2 — CENSUS read-only de near-duplicados a nivel DOCUMENTO (spec v2-P2/v3-FINAL-P2).

Raíz corpus-side de la pieza 2 de etapa 2: materializar la relación canónica
documento→documento ANTES de tocar el pool (Sol-6), vía census→staging→PASTE de Alberto.
NO escribe en DB. NO toca código del pipeline. Genera 3 artefactos:
  - evals/s287_p2_dedup_census_v1.json              (pares + métricas + SPAN-DIFF por chunk)
  - evals/s287_p2_dedup_adjudicacion_packet_v1.md   (packet de adjudicación para Alberto)
  - evals/s287_p2_dedup_apply_v1.sql                (staging + UPDATE, paste tras adjudicación)

MAQUINARIA: reusa la del audit s62 (`scripts/s62_audit43.py`, DECISIONS.md:909) — shingles
de 8 palabras (crc32 sobre `norm_ocr`) + Jaccard. TRES desviaciones DECLARADAS, todas
obligadas por el gate de SPAN-DIFF de Sol-6 (el census DECIDE supresiones; s62 solo
dimensionaba inventario):
  (D1) SIN cap de muestreo (s62: `SHINGLE_CAP=4000` bottom-k) → conjuntos EXACTOS.
  (D2) SIN blocking por fabricante (s62 solo comparaba dentro de cada `manufacturer`).
       El par SEMILLA cruza fabricante (`European Safety Systems` vs `Detnov`) → el
       blocking de s62 era estructuralmente CIEGO a esta clase.
  (D3) El span-diff se mide a nivel PALABRA, no contando chunks-gemelos. HALLAZGO DE
       CALIBRACIÓN (medido, ver meta.metodo.calibracion): el criterio literal del brief
       («>=60% de los chunks con Jaccard>=0.85 contra algún chunk del otro») NO detecta
       el par semilla — los dos docs son re-extracciones DISTINTAS del mismo PDF (15 vs
       18 chunks, fronteras desplazadas + ruido OCR), así que el Jaccard chunk↔chunk se
       diluye por CORTE, no por contenido (mejor-gemelo real: 0.63..0.83 en pasajes
       idénticos). Un shingle de 8 palabras muere con UNA palabra distinta; contar
       shingles perdidos sobre-estima la divergencia. Contar PALABRAS cubiertas no.

CRITERIO (dos etapas):
 1. BLOCKING de candidatos, doc-level, UNIÓN de 4 nets (corpus-wide, sin blocking por
    fabricante/título). Varios nets porque ninguno solo es robusto a la vez al ruido OCR
    y a la asimetría de tamaño:
      N1 contención de shingles  |sh(A)∩sh(B)|/min(...)  >= 0.35
      N2 contención de tokens    |tok(A)∩tok(B)|/min(...) >= 0.80
      N3 contención de tokens RAROS (df <= 5% de los docs) >= 0.55
      N4 mismo `source_pdf_sha256`
    Contención y no Jaccard: Jaccard penaliza la asimetría de tamaño y perdería el caso
    subset (doc chico contenido en grande).
 2. SPAN-DIFF a nivel PALABRA (el GATE de Sol-6), en AMBAS direcciones. Para cada chunk c
    contra el doc entero D del otro lado:
      - se marca CUBIERTA toda palabra que participe en >=1 shingle presente en sh(D)
      - `covered_word_frac` = palabras cubiertas / palabras totales
      - `uncovered_spans`   = rachas MAXIMALES de palabras NO cubiertas de >= 25 palabras
        (con su texto, para que la adjudicación sea legible)
      - `best_twin`         = argmax Jaccard(sh(c), sh(c')) sobre los chunks c' de D
    Clase: TWIN (covered>=0.92 y NINGUNA racha >=25 palabras) · PARTIAL · UNIQUE
    (covered<0.50) · SHORT (<8 palabras: no shingleable). SOLO los TWIN con puntero
    válido (best_twin Jaccard >= 0.60) se proponen; TODO lo demás NUNCA se suprime.

POLÍTICA DE REPRESENTANTE — se computan DOS y se declara la divergencia (Protocolo 2):
  (a) `policy_literal` = la del spec v2-P2: idiomas distintos → KEEP-BOTH; mismo idioma →
      MÁS spans únicos gana; empate → más reciente (revision_date → revision →
      ingested_at). NUNCA «gana ES» (el dedup del pipeline, `src/reingest/dedup.py:
      _preference`, sí prefiere ES: en cat010 la aguja está en el doc EN → esa política
      habría suprimido la aguja).
  (b) `recommended` = REFINAMIENTO propuesto: primero AUTO-SOPORTE DE METADATA (¿aparecen
      `manufacturer`/`product_model` del doc en su PROPIO contenido?), luego más spans
      únicos, luego recencia. MOTIVO: como los spans UNIQUE/PARTIAL nunca se suprimen, el
      criterio «más spans únicos» NO protege contenido — ya lo protege el gate de
      span-diff. Lo único que decide el representante es de QUÉ doc sale la CITA del
      contenido compartido; un doc cuya atribución no está soportada por su propio texto
      es mal representante (riesgo: citar el fabricante equivocado). RIESGO DECLARADO del
      refinamiento: el auto-soporte es una heurística de substring — un `manufacturer`
      correcto que simplemente no se imprime en el manual puntúa 0 (falso negativo). Por
      eso NO se aplica solo: los pares donde (a) y (b) DIVERGEN van marcados
      `ADJUDICAR` en el packet y su SQL sale comentado por-fila.

Uso:  python scripts/s287_p2_dedup_census.py [--cache DIR] [--no-fetch]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
import time
import zlib
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from strict_match import norm_ocr  # noqa: E402

URL = os.environ["SUPABASE_URL"]
H = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
     "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}

CHUNKS_TABLE = "chunks_v2"
OUT_JSON = ROOT / "evals" / "s287_p2_dedup_census_v1.json"
OUT_MD = ROOT / "evals" / "s287_p2_dedup_adjudicacion_packet_v1.md"
OUT_SQL = ROOT / "evals" / "s287_p2_dedup_apply_v1.sql"

SHINGLE_W = 8
NET_SHINGLE_CONT = 0.35
NET_TOKEN_CONT = 0.80
NET_RARE_CONT = 0.55
RARE_DF_FRAC = 0.05
MIN_UNIQUE_SPAN_WORDS = 25     # racha de palabras NO cubiertas que ya es "span único"
TWIN_COVERED_FRAC = 0.92
UNIQUE_COVERED_FRAC = 0.50
POINTER_MIN_J = 0.60           # Jaccard mínimo del gemelo para que el puntero sea honesto
PAIR_QUALIFY = 0.60            # covered_word_frac del doc en >=1 dirección
BRIEF_STRICT_TWIN_J = 0.85     # criterio LITERAL del brief (se reporta para calibración)

SEED_PAIR = ("2b694083-5b21-4f1a-a29b-565072860fb8",   # IS5001-F_IS-mA1_EN
             "a6b9dc84-af6d-4957-a403-4b4c2136557b")   # manual IS MA1
SEED_GOLD = "cat010"


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
    with httpx.Client(timeout=120.0) as c:
        while True:
            params = {"select": select, "limit": str(page), "offset": str(offset),
                      "order": "id.asc"}
            for attempt in range(4):
                try:
                    r = c.get(f"{URL}/rest/v1/{table}", headers=H, params=params)
                    r.raise_for_status()
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(2 * (attempt + 1))
            batch = r.json()
            rows.extend(batch)
            print(f"   {table}: {len(rows)}", end="\r")
            if len(batch) < page:
                print()
                return rows
            offset += page


def sh_words(words: list[str], w: int = SHINGLE_W) -> frozenset[int]:
    """Shingles EXACTOS (sin cap — D1). crc32 es estable entre procesos (hash() varía con
    PYTHONHASHSEED y rompería la reproducibilidad del artefacto)."""
    return frozenset(zlib.crc32(" ".join(words[i:i + w]).encode("utf-8"))
                     for i in range(len(words) - w + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def containment(a: frozenset, b: frozenset) -> float:
    m = min(len(a), len(b))
    return len(a & b) / m if m else 0.0


def coverage_map(words: list[str], other_sig: frozenset[int],
                 w: int = SHINGLE_W) -> bytearray:
    """Marca CUBIERTA toda palabra que participe en >=1 shingle presente en other_sig."""
    n = len(words)
    cov = bytearray(n)
    for i in range(n - w + 1):
        if zlib.crc32(" ".join(words[i:i + w]).encode("utf-8")) in other_sig:
            for j in range(i, i + w):
                cov[j] = 1
    return cov


def uncovered_spans(cov: bytearray, words: list[str],
                    minlen: int = MIN_UNIQUE_SPAN_WORDS) -> list[dict]:
    out, run = [], 0
    for i, v in enumerate(cov):
        if v:
            if run >= minlen:
                out.append((i - run, run))
            run = 0
        else:
            run += 1
    if run >= minlen:
        out.append((len(cov) - run, run))
    return [{"start_word": s, "n_words": ln,
             "text": " ".join(words[s:s + min(ln, 40)]) + ("…" if ln > 40 else "")}
            for s, ln in out]


def _tok(s: str | None) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", norm_ocr(s or "")) if len(t) >= 2]


def metadata_self_support(value: str | None, doc_text: str) -> dict:
    toks = _tok(value)
    if not toks or (value or "").strip().lower() in ("unknown", "n/a", ""):
        return {"value": value, "tokens": toks, "hits": 0, "supported": False,
                "nota": "vacío/'unknown' → no auto-soportado por definición"}
    hits = [t for t in toks if t in doc_text]
    return {"value": value, "tokens": toks, "hits": len(hits),
            "supported": len(hits) == len(toks),
            "missing": [t for t in toks if t not in doc_text]}


def rev_key(d: dict) -> tuple:
    return (d.get("revision_date") or "", d.get("revision") or "", d.get("ingested_at") or "")


_TRIVIAL_PM = {"", "unknown", "n/a", "na", "none", "null", "generico", "generic",
               "desconocido", "varios"}


def nm_manu(v: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (v or "").lower())


def pm_set(*values: str | None) -> set[str]:
    """Conjunto NORMALIZADO de modelos de un doc (los pm multi-modelo vienen como
    'ESTELA-1 / ESTELA-2'). Los valores triviales ('unknown', vacío) se descartan:
    un doc sin identidad de producto NO puede sostener el veredicto hermana-de-serie."""
    out: set[str] = set()
    for v in values:
        for part in re.split(r"[/,;+]| y ", (v or "")):
            k = re.sub(r"[^a-z0-9]", "", part.lower())
            if k and part.strip().lower() not in _TRIVIAL_PM and len(k) >= 2:
                out.add(k)
    return out


def md5(s: str | None) -> str | None:
    return hashlib.md5(s.encode("utf-8")).hexdigest() if s is not None else None


# ----------------------------------------------------------------------------- main
def main() -> int:  # noqa: C901
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()

    cache_f = Path(args.cache) / "corpus_cache.pkl" if args.cache else None
    if cache_f and cache_f.exists():
        print(f"1) cache → {cache_f}")
        blob = pickle.load(open(cache_f, "rb"))
        docs, chunks = blob["docs"], blob["chunks"]
    elif args.no_fetch:
        raise SystemExit("--no-fetch sin cache válido")
    else:
        print("1) documents…")
        docs = fetch_all("documents",
                         "id,source_pdf_filename,source_pdf_sha256,manufacturer,product_model,"
                         "doc_type,language,revision,revision_date,status,document_family,"
                         "revision_lineage_id,supersedes_id,superseded_by_id,ingested_at")
        print("2) chunks…")
        chunks = fetch_all(CHUNKS_TABLE,
                           "id,document_id,source_file,content,language,product_model,"
                           "manufacturer,page_number,chunk_index,duplicate_of,"
                           "extraction_sha256,section_title,section_path,content_type,"
                           "doc_type,parent_id")
        if cache_f:
            cache_f.parent.mkdir(parents=True, exist_ok=True)
            pickle.dump({"docs": docs, "chunks": chunks}, open(cache_f, "wb"), protocol=4)
    by_id = {d["id"]: d for d in docs}
    print(f"   documents={len(docs)} chunks={len(chunks)}")

    # ---- universo SERVIDO: status='active' (_filter_by_document_status, retriever.py:2801
    #      tira todo status != 'active') + duplicate_of IS NULL (retriever.py:635/687)
    status_dist = dict(Counter(d.get("status") for d in docs))
    active_ch = [c for c in chunks if c["duplicate_of"] is None]
    orphan_ch = [c for c in active_ch if not c.get("document_id")]
    ch_by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in active_ch:
        did = c.get("document_id")
        if did and by_id.get(did, {}).get("status") == "active":
            ch_by_doc[did].append(c)
    for cs in ch_by_doc.values():
        cs.sort(key=lambda x: (x.get("chunk_index") if x.get("chunk_index") is not None else 0,
                               x["id"]))
    universe = sorted(ch_by_doc)
    n_univ_chunks = sum(len(v) for v in ch_by_doc.values())
    print(f"3) universo servido: {len(universe)} docs activos · {n_univ_chunks} chunks | "
          f"huérfanos(document_id NULL) {len(orphan_ch)} | status {status_dist}")

    # ---- firmas doc-level
    t0 = time.time()
    doc_words, doc_sig, doc_tok, doc_text = {}, {}, {}, {}
    ch_words: dict[str, list[str]] = {}
    for did in universe:
        ws_all: list[str] = []
        for c in ch_by_doc[did]:
            w = norm_ocr(c.get("content") or "").split()
            ch_words[c["id"]] = w
            ws_all += w
        doc_words[did] = ws_all
        doc_text[did] = " ".join(ws_all)
        doc_sig[did] = sh_words(ws_all)
        doc_tok[did] = frozenset(ws_all)
    df = Counter()
    for did in universe:
        df.update(doc_tok[did])
    rare_max = RARE_DF_FRAC * len(universe)
    doc_rare = {did: frozenset(t for t in doc_tok[did] if df[t] <= rare_max)
                for did in universe}
    print(f"4) firmas: {time.time() - t0:.0f}s · shingles {sum(len(s) for s in doc_sig.values())}")

    # ---- BLOCKING: unión de nets, corpus-wide all-pairs
    t0 = time.time()
    nets: dict[str, set] = {"N1_shingle_cont": set(), "N2_token_cont": set(),
                            "N3_rare_token_cont": set(), "N4_same_sha256": set()}
    by_sha = defaultdict(list)
    for did in universe:
        s = by_id[did].get("source_pdf_sha256")
        if s:
            by_sha[s].append(did)
    for s, ids in by_sha.items():
        if len(ids) > 1:
            for a, b in combinations(sorted(ids), 2):
                nets["N4_same_sha256"].add((a, b))
    net_vals: dict[tuple, dict] = {}
    for a, b in combinations(universe, 2):
        c1 = containment(doc_sig[a], doc_sig[b])
        c2 = containment(doc_tok[a], doc_tok[b])
        c3 = containment(doc_rare[a], doc_rare[b])
        hit = False
        if c1 >= NET_SHINGLE_CONT:
            nets["N1_shingle_cont"].add((a, b)); hit = True
        if c2 >= NET_TOKEN_CONT:
            nets["N2_token_cont"].add((a, b)); hit = True
        if c3 >= NET_RARE_CONT:
            nets["N3_rare_token_cont"].add((a, b)); hit = True
        if hit or (a, b) in nets["N4_same_sha256"]:
            net_vals[(a, b)] = {"shingle_cont": round(c1, 4), "token_cont": round(c2, 4),
                                "rare_token_cont": round(c3, 4)}
    cands = sorted(set().union(*nets.values()))
    n_pairs_total = len(universe) * (len(universe) - 1) // 2
    print(f"5) blocking all-pairs {n_pairs_total} en {time.time() - t0:.0f}s → "
          f"{len(cands)} candidatos | " +
          " ".join(f"{k}={len(v)}" for k, v in nets.items()))

    # ---- SPAN-DIFF a nivel palabra
    t0 = time.time()
    ch_sig: dict[str, frozenset[int]] = {}

    def csig(cid: str) -> frozenset[int]:
        if cid not in ch_sig:
            ch_sig[cid] = sh_words(ch_words[cid])
        return ch_sig[cid]

    def side(self_id: str, other_id: str) -> dict:
        other_sig = doc_sig[other_id]
        other_chunks = ch_by_doc[other_id]
        rows, cls = [], Counter()
        cov_words = tot_words = 0
        for c in ch_by_doc[self_id]:
            w = ch_words[c["id"]]
            s = csig(c["id"])
            if len(w) < SHINGLE_W:
                klass, cf, sp = "SHORT", None, []
                bt, btj = None, 0.0
            else:
                cov = coverage_map(w, other_sig)
                cf = sum(cov) / len(cov)
                sp = uncovered_spans(cov, w)
                cov_words += sum(cov); tot_words += len(cov)
                bt, btj = None, -1.0
                for c2 in other_chunks:
                    j = jaccard(s, csig(c2["id"]))
                    if j > btj:
                        bt, btj = c2["id"], j
                btj = max(btj, 0.0)
                if cf >= TWIN_COVERED_FRAC and not sp:
                    klass = "TWIN" if btj >= POINTER_MIN_J else "COVERED_NO_TWIN"
                elif cf < UNIQUE_COVERED_FRAC:
                    klass = "UNIQUE"
                else:
                    klass = "PARTIAL"
            cls[klass] += 1
            rows.append({
                "chunk_id": c["id"], "chunk_index": c.get("chunk_index"),
                "page": c.get("page_number"), "n_words": len(w),
                "section_title": c.get("section_title"),
                "covered_word_frac": round(cf, 4) if cf is not None else None,
                "n_uncovered_spans": len(sp),
                "max_uncovered_span_words": max((x["n_words"] for x in sp), default=0),
                "uncovered_spans": sp,
                "best_twin_chunk_id": bt, "best_twin_jaccard": round(btj, 4),
                "brief_strict_twin_j085": btj >= BRIEF_STRICT_TWIN_J,
                "class": klass,
            })
        d = by_id[self_id]
        langs = Counter(c.get("language") for c in ch_by_doc[self_id] if c.get("language"))
        n = len(rows) or 1
        ms = {"manufacturer": metadata_self_support(d.get("manufacturer"), doc_text[self_id]),
              "product_model": metadata_self_support(d.get("product_model"), doc_text[self_id])}
        return {
            "document_id": self_id, "source_pdf_filename": d.get("source_pdf_filename"),
            "manufacturer": d.get("manufacturer"), "product_model": d.get("product_model"),
            "chunk_product_models": dict(Counter(c.get("product_model")
                                                 for c in ch_by_doc[self_id])),
            "doc_language": d.get("language"),
            "chunk_language_majority": langs.most_common(1)[0][0] if langs else None,
            "chunk_languages": dict(langs),
            "revision": d.get("revision"), "revision_date": d.get("revision_date"),
            "ingested_at": d.get("ingested_at"), "status": d.get("status"),
            "sha256": d.get("source_pdf_sha256"), "document_family": d.get("document_family"),
            "pages": sorted({c.get("page_number") for c in ch_by_doc[self_id]
                             if c.get("page_number") is not None}),
            "n_chunks_active": len(rows), "n_words_doc": len(doc_words[self_id]),
            "classes": dict(cls),
            "covered_word_frac_doc": round(cov_words / tot_words, 4) if tot_words else 0.0,
            "n_unique_spans_total": sum(r["n_uncovered_spans"] for r in rows),
            "n_unique_words_total": sum(x["n_words"] for r in rows
                                        for x in r["uncovered_spans"]),
            "frac_chunks_twin": round(cls["TWIN"] / n, 4),
            "frac_chunks_unique": round(cls["UNIQUE"] / n, 4),
            "metadata_self_support": ms,
            "metadata_support_score": (2 if ms["manufacturer"]["supported"] else 0)
                                      + (1 if ms["product_model"]["supported"] else 0),
            "brief_strict_frac_twin_j085": round(
                sum(1 for r in rows if r["brief_strict_twin_j085"]) / n, 4),
            "spans": rows,
        }

    pairs = []
    for a, b in cands:
        A, B = side(a, b), side(b, a)
        qual = max(A["covered_word_frac_doc"], B["covered_word_frac_doc"]) >= PAIR_QUALIFY
        pairs.append({
            "pair_id": f"{a[:8]}__{b[:8]}",
            "nets": {k: (a, b) in v for k, v in nets.items()},
            "net_values": net_vals.get((a, b), {}),
            "doc_jaccard_shingles": round(jaccard(doc_sig[a], doc_sig[b]), 4),
            "qualifies_near_dup": qual,
            "is_seed_pair": a in SEED_PAIR and b in SEED_PAIR,
            "brief_strict_criterion_met": max(A["brief_strict_frac_twin_j085"],
                                              B["brief_strict_frac_twin_j085"]) >= PAIR_QUALIFY,
            "side_a": A, "side_b": B,
        })
    print(f"6) span-diff de {len(pairs)} pares en {time.time() - t0:.0f}s | "
          f"cualifican {sum(1 for p in pairs if p['qualifies_near_dup'])} | "
          f"criterio literal del brief "
          f"{sum(1 for p in pairs if p['brief_strict_criterion_met'])}")

    # ---- políticas de representante + propuesta de marcas
    def pick(A, B, mode):
        """Devuelve (representante, suprimido, motivo)."""
        if mode == "literal":
            ua, ub = A["n_unique_spans_total"], B["n_unique_spans_total"]
            if ua != ub:
                return ((A, B, f"más spans únicos ({ua} vs {ub})") if ua > ub
                        else (B, A, f"más spans únicos ({ub} vs {ua})"))
        else:
            sa, sb = A["metadata_support_score"], B["metadata_support_score"]
            if sa != sb:
                return ((A, B, f"metadata auto-soportada ({sa}/3 vs {sb}/3)") if sa > sb
                        else (B, A, f"metadata auto-soportada ({sb}/3 vs {sa}/3)"))
            ua, ub = A["n_unique_spans_total"], B["n_unique_spans_total"]
            if ua != ub:
                return ((A, B, f"empate metadata → más spans únicos ({ua} vs {ub})") if ua > ub
                        else (B, A, f"empate metadata → más spans únicos ({ub} vs {ua})"))
        ka, kb = rev_key(by_id[A["document_id"]]), rev_key(by_id[B["document_id"]])
        if ka != kb:
            return ((A, B, "empate → más reciente (revision_date/revision/ingested_at)")
                    if ka > kb else
                    (B, A, "empate → más reciente (revision_date/revision/ingested_at)"))
        return ((A, B, "empate total → desempate estable por document_id (ARBITRARIO)")
                if A["document_id"] < B["document_id"] else
                (B, A, "empate total → desempate estable por document_id (ARBITRARIO)"))

    def sides_of_pair(p: dict, did: str) -> dict:
        """El lado del par correspondiente a `did` — es su span-diff CONTRA el otro doc del
        par, que es exactamente lo que hace falta para orientar la supresión."""
        return p["side_a"] if p["side_a"]["document_id"] == did else p["side_b"]

    def marks_for(sup_side: dict) -> list[dict]:
        """Marcas propuestas = SOLO los chunks TWIN del lado suprimido, con su puntero."""
        return [{"chunk_id": r["chunk_id"],
                 "canonical_chunk_id": r["best_twin_chunk_id"],
                 "covered_word_frac": r["covered_word_frac"],
                 "twin_jaccard": r["best_twin_jaccard"],
                 "max_uncovered_span_words": r["max_uncovered_span_words"],
                 "chunk_index": r["chunk_index"], "page": r["page"]}
                for r in sup_side["spans"]
                if r["class"] == "TWIN" and r["best_twin_chunk_id"] is not None]

    def preserved(sup_side: dict) -> dict:
        return {k: [{"chunk_id": r["chunk_id"], "chunk_index": r["chunk_index"],
                     "page": r["page"], "covered_word_frac": r["covered_word_frac"],
                     "max_uncovered_span_words": r["max_uncovered_span_words"]}
                    for r in sup_side["spans"] if r["class"] == k]
                for k in ("UNIQUE", "PARTIAL", "COVERED_NO_TWIN", "SHORT")
                if any(r["class"] == k for r in sup_side["spans"])}

    for p in pairs:
        A, B = p["side_a"], p["side_b"]
        la = A["chunk_language_majority"] or A["doc_language"]
        lb = B["chunk_language_majority"] or B["doc_language"]
        ma = pm_set(A["product_model"], *A["chunk_product_models"].keys())
        mb = pm_set(B["product_model"], *B["chunk_product_models"].keys())
        ma_doc, mb_doc = pm_set(A["product_model"]), pm_set(B["product_model"])
        dec: dict = {"languages": [la, lb],
                     "product_identity": {
                         "models_a_doc": sorted(ma_doc), "models_b_doc": sorted(mb_doc),
                         "models_a_all": sorted(ma), "models_b_all": sorted(mb),
                         "doc_level_intersect": sorted(ma_doc & mb_doc),
                         "any_side_trivial_doc_pm": not ma_doc or not mb_doc}}
        if not p["qualifies_near_dup"]:
            dec.update(verdict="NO-QUALIFY", reason=(
                f"covered_word_frac máx {max(A['covered_word_frac_doc'], B['covered_word_frac_doc']):.2f}"
                f" < {PAIR_QUALIFY} — solape parcial (boilerplate/serie hermana), no "
                "near-dup de documento"))
        elif la and lb and la != lb:
            dec.update(verdict="KEEP-BOTH-LANG", reason=(
                f"idiomas distintos ({la} vs {lb}) — variante de mercado, no redundancia: "
                "NUNCA suprimir (política language-aware; NUNCA «gana ES»)"))
        elif (nm_manu(A["manufacturer"]) and nm_manu(B["manufacturer"])
              and nm_manu(A["manufacturer"]) != nm_manu(B["manufacturer"])
              and A["metadata_self_support"]["manufacturer"]["supported"]
              and B["metadata_self_support"]["manufacturer"]["supported"]):
            dec.update(verdict="KEEP-BOTH-BRAND", reason=(
                f"REBADGE OEM LEGÍTIMO: fabricantes distintos ({A['manufacturer']} vs "
                f"{B['manufacturer']}) y CADA doc imprime su PROPIO fabricante en su "
                "contenido → son los dos manuales de marca del mismo producto OEM, no una "
                "redundancia. Marcar `duplicate_of` borraría la atribución de marca que el "
                "técnico necesita (tiene un panel Morley, no un Notifier) y colapsaría "
                "distinciones que Alberto ya adjudicó en s78/s80 (RP1r-Supra=Notifier vs "
                "VSN-RP1r=Morley). Clase del workstream de IDENTIDAD (D1/D3), no de dedup."))
        elif ma_doc and mb_doc and not (ma_doc & mb_doc):
            dec.update(verdict="KEEP-BOTH-SERIE", reason=(
                f"HERMANAS DE SERIE: los dos docs tienen product_model NO trivial y "
                f"DISJUNTO ({sorted(ma_doc)} vs {sorted(mb_doc)}) → son documentos de "
                "PRODUCTOS DISTINTOS que comparten plantilla. El texto compartido no es "
                "redundancia: la identidad del doc ES la carga útil. Suprimir aquí es "
                "exactamente el daño DEC-091b (servir el manual del modelo equivocado). "
                "Para esta clase el lever correcto es el dedup-EN-POOL (fallback), no "
                "`duplicate_of`."))
        else:
            rep_l, sup_l, why_l = pick(A, B, "literal")
            rep_r, sup_r, why_r = pick(A, B, "recommended")
            diverge = rep_l["document_id"] != rep_r["document_id"]
            rep, sup, why = rep_r, sup_r, why_r
            marks = marks_for(sup)
            same_brand = nm_manu(A["manufacturer"]) == nm_manu(B["manufacturer"])
            cov_max = max(A["covered_word_frac_doc"], B["covered_word_frac_doc"])
            cov_min = min(A["covered_word_frac_doc"], B["covered_word_frac_doc"])
            if same_brand and cov_min >= 0.90:
                tier = "T1-DOC-IDENTICO"
            elif same_brand:
                tier = "T2-MISMA-MARCA"
            else:
                tier = "T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA"
            dec.update(
                verdict="SUPPRESS-COVERED", tier=tier, same_brand=same_brand,
                coverage_min=cov_min, coverage_max=cov_max,
                representative=rep["document_id"], suppressed=sup["document_id"],
                reason=why,
                policy_literal={"representative": rep_l["document_id"], "reason": why_l},
                policy_recommended={"representative": rep_r["document_id"], "reason": why_r},
                policies_diverge=diverge,
                adjudicar=True,   # NINGÚN par entra vivo: ver meta.metodo.gate_de_adjudicacion
                proposed_marks=marks, n_proposed_marks=len(marks),
                preserved_in_suppressed=preserved(sup),
                representative_keeps_everything=True,
            )
            if diverge:
                dec["divergencia"] = (
                    f"la política LITERAL del spec conservaría {rep_l['source_pdf_filename']!r} "
                    f"({why_l}); el REFINAMIENTO conserva {rep_r['source_pdf_filename']!r} "
                    f"({why_r}). Como los spans únicos NUNCA se suprimen, el conteo de spans "
                    "únicos no protege contenido — sí decide la CITA. ADJUDICAR.")
        p["decision"] = dec

    # ---- POST-PASS de CONSISTENCIA DE CLUSTER (bug cazado por la pre-validación de guards):
    #      las decisiones POR PAR no son globalmente consistentes. Con >2 docs near-dup
    #      aparecen CADENAS y hasta CICLOS (medido: MIE-MI-470→480→490→470, y NRX-OPT
    #      representante en un par y suprimido en otro) → un chunk sería a la vez marcado y
    #      canónico de otro, que es justo lo que aborta el guard 3e del paste.
    #      Fix estructural: en cada COMPONENTE CONEXO se elige UN representante y solo los
    #      pares que lo contienen conservan propuesta, orientados hacia él.
    par: dict[str, str] = {}

    def _find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def _union(a, b):
        par[_find(a)] = _find(b)

    sc_pairs = [p for p in pairs if p["decision"]["verdict"] == "SUPPRESS-COVERED"]
    for p in sc_pairs:
        _union(p["side_a"]["document_id"], p["side_b"]["document_id"])
    comp: dict[str, list] = defaultdict(list)
    for p in sc_pairs:
        comp[_find(p["side_a"]["document_id"])].append(p)

    cluster_report = []
    for root, ps in comp.items():
        sides: dict[str, dict] = {}
        for p in ps:
            for s in (p["side_a"], p["side_b"]):
                prev = sides.get(s["document_id"])
                if prev is None or s["n_unique_spans_total"] > prev["n_unique_spans_total"]:
                    sides[s["document_id"]] = s
        if len(sides) <= 2:
            for p in ps:
                p["decision"]["cluster"] = {"size": len(sides), "representative":
                                            p["decision"]["representative"],
                                            "reoriented": False}
            continue
        # elección de representante del CLUSTER (mismo orden que el refinamiento)
        rep_id = max(sides, key=lambda d: (sides[d]["metadata_support_score"],
                                           sides[d]["n_unique_spans_total"],
                                           rev_key(by_id[d]), d))
        entry = {"size": len(sides), "docs": sorted(sides),
                 "representative": rep_id,
                 "representative_file": by_id[rep_id].get("source_pdf_filename"),
                 "pares": [], "reorientados": 0, "sin_propuesta": 0}
        for p in ps:
            d = p["decision"]
            ids = (p["side_a"]["document_id"], p["side_b"]["document_id"])
            if rep_id not in ids:
                d["proposed_marks"], d["n_proposed_marks"] = [], 0
                d["cluster_note"] = (
                    f"CLUSTER de {len(sides)} docs: el representante del cluster es "
                    f"{by_id[rep_id].get('source_pdf_filename')!r} y este par no lo contiene "
                    "→ propuesta RETIRADA para no crear cadenas de duplicados (guard 3e). "
                    "La redundancia de estos dos docs se resuelve por sus pares con el "
                    "representante del cluster.")
                entry["sin_propuesta"] += 1
            else:
                other = ids[0] if ids[1] == rep_id else ids[1]
                if d["representative"] != rep_id:
                    new_sup = sides_of_pair(p, other)
                    d["representative"], d["suppressed"] = rep_id, other
                    d["proposed_marks"] = marks_for(new_sup)
                    d["n_proposed_marks"] = len(d["proposed_marks"])
                    d["preserved_in_suppressed"] = preserved(new_sup)
                    d["reason"] = (
                        f"REORIENTADO por consistencia de cluster: el representante del "
                        f"cluster de {len(sides)} docs es "
                        f"{by_id[rep_id].get('source_pdf_filename')!r} "
                        f"(metadata {sides[rep_id]['metadata_support_score']}/3, "
                        f"{sides[rep_id]['n_unique_spans_total']} spans únicos). "
                        f"Original por-par: {d['reason']}")
                    entry["reorientados"] += 1
            d["cluster"] = {"size": len(sides), "representative": rep_id,
                            "reoriented": d["representative"] == rep_id
                            and rep_id != d["policy_recommended"]["representative"]}
            entry["pares"].append({"pair_id": p["pair_id"],
                                   "n_proposed_marks": d["n_proposed_marks"],
                                   "representative": d["representative"]})
        cluster_report.append(entry)

    # ---- ASSERT de consistencia global (lo que la pre-validación cazó a mano)
    all_marks = [(m["chunk_id"], m["canonical_chunk_id"])
                 for p in pairs for m in p["decision"].get("proposed_marks", [])]
    marked_ids = [x for x, _ in all_marks]
    canon_ids = {y for _, y in all_marks}
    dupes = [k for k, v in Counter(marked_ids).items() if v > 1]
    chain = sorted(set(marked_ids) & canon_ids)
    if dupes:
        raise SystemExit(f"BUG: {len(dupes)} chunk_id repetidos en las propuestas "
                         f"(violaría la PK de staging): {dupes[:5]}")
    if chain:
        raise SystemExit(f"BUG: {len(chain)} chunks son a la vez marcados y canónicos "
                         f"(cadena de duplicados — guard 3e abortaría): {chain[:5]}")
    print(f"6b) consistencia global OK: {len(all_marks)} marcas, 0 repetidas, 0 cadenas | "
          f"clusters >2 docs: {len(cluster_report)}")

    # ---- satélites (fuga potencial de un duplicate_of NUEVO)
    proposed = [(m, p) for p in pairs for m in p["decision"].get("proposed_marks", [])]
    proposed_ids = [m["chunk_id"] for m, _ in proposed]
    sat = {"n_proposed_chunk_marks": len(proposed_ids),
           "enunciados_rows_on_proposed": 0, "hyq_rows_on_proposed": 0,
           "enunciados_ids": []}
    if proposed_ids:
        with httpx.Client(timeout=60.0) as c:
            for i in range(0, len(proposed_ids), 50):
                b = ",".join(proposed_ids[i:i + 50])
                r = c.get(f"{URL}/rest/v1/chunks_v2_enunciados", headers=H,
                          params={"select": "id,parent_id", "parent_id": f"in.({b})"})
                if r.status_code == 200:
                    sat["enunciados_rows_on_proposed"] += len(r.json())
                    sat["enunciados_ids"] += [x["id"] for x in r.json()]
                r = c.get(f"{URL}/rest/v1/chunks_v2_hyq", headers=H,
                          params={"select": "id", "chunk_id": f"in.({b})"})
                if r.status_code == 200:
                    sat["hyq_rows_on_proposed"] += len(r.json())
    sat["nota"] = (
        "hyq: GUARDADO client-side (retriever.py:1095-1098, fix s286 fuga-hyq) → las filas "
        "pueden quedarse: no resucitan contenido retirado. enunciados: el RPC 012 "
        "`match_chunks_v2_enunciados` NO filtra por el `duplicate_of` del padre "
        "(migrations/012_enunciados_rpc_filters.sql, WHERE sin duplicate_of) — el comentario "
        "de retriever.py:1097 («el canal de enunciados sí filtra en SQL») es INEXACTO. "
        "Verificado read-only: 0 filas de enunciados sobre una muestra de 300 chunks ya "
        "marcados y 0 sobre los chunks propuestos → la tabla se pobló EXCLUYENDO duplicados "
        "(scripts/enunciados_pass.py:107 filtra duplicate_of=is.null). Eso es una propiedad "
        "del POBLADO, no una garantía del SERVICIO: el paste lleva un guard que ABORTA si "
        "alguna marca propuesta tuviera filas de enunciados.")

    # ---------------------------------------------------------------- orden + JSON
    _VORD = {"SUPPRESS-COVERED": 0, "KEEP-BOTH-LANG": 1, "KEEP-BOTH-BRAND": 2,
             "KEEP-BOTH-SERIE": 3, "NO-QUALIFY": 4}

    def order_key(p):
        return (0 if p["is_seed_pair"] else 1,
                _VORD[p["decision"]["verdict"]],
                -max(p["side_a"]["covered_word_frac_doc"],
                     p["side_b"]["covered_word_frac_doc"]))
    pairs.sort(key=order_key)

    # compactación DECLARADA del artefacto (los pares accionables van completos):
    #   SUPPRESS-COVERED / KEEP-BOTH-LANG → completo
    #   KEEP-BOTH-SERIE                   → filas por chunk SIN el texto de los spans
    #   NO-QUALIFY                        → solo métricas doc-level
    slim = []
    for p in pairs:
        v = p["decision"]["verdict"]
        if v in ("SUPPRESS-COVERED", "KEEP-BOTH-LANG", "KEEP-BOTH-BRAND"):
            slim.append(p)
            continue
        q = {k: val for k, val in p.items() if k not in ("side_a", "side_b")}
        for k in ("side_a", "side_b"):
            if v == "NO-QUALIFY":
                q[k] = {kk: vv for kk, vv in p[k].items() if kk != "spans"}
            else:
                q[k] = {kk: vv for kk, vv in p[k].items() if kk != "spans"}
                q[k]["spans"] = [{kk: vv for kk, vv in r.items() if kk != "uncovered_spans"}
                                 for r in p[k]["spans"]]
        slim.append(q)

    out = {
        "meta": {
            "at": _now(), "git": _git(), "branch": "claude/s282-h0t2-qa",
            "corpus": CHUNKS_TABLE, "read_only": True,
            "spec": "evals/s287_etapa2_design_brief_v1.md (v2-P2 + v3-FINAL-P2)",
            "generador": "scripts/s287_p2_dedup_census.py",
            "alcance_declarado": {
                "nivel": "DOCUMENTO (par de document_id) · SPAN-DIFF POR CHUNK (gate Sol-6)",
                "cobertura": "CORPUS-WIDE all-pairs sobre el universo servido — SIN "
                             "blocking por fabricante ni por título (el par semilla cruza "
                             "fabricante: s62 no podía verlo)",
                "universo_servido": {
                    "docs_status_active_con_chunks_activos": len(universe),
                    "chunks_en_universo": n_univ_chunks,
                    "pares_evaluados_en_blocking": n_pairs_total,
                    "documents_totales": len(docs), "chunks_totales": len(chunks),
                    "status_dist_documents": status_dist,
                },
                "exclusiones": [
                    f"docs con status != 'active' ({len(docs) - status_dist.get('active', 0)}): "
                    "_filter_by_document_status (retriever.py:2801) los tira → no compiten "
                    "por slots del pool",
                    f"chunks con duplicate_of NOT NULL ({len(chunks) - len(active_ch)}): ya "
                    "retirados del pool (retriever.py:635/687)",
                    f"chunks activos con document_id NULL ({len(orphan_ch)}): sin doc padre, "
                    "no pueden formar par de documentos",
                ],
                "residual_de_recall_DECLARADO":
                    "el blocking es una UNIÓN de 4 nets con floors, no una garantía. NO "
                    "existe net barato con cota dura frente a un criterio de cobertura de "
                    "PALABRAS (una palabra puede estar cubierta por un único shingle "
                    "compartido). Margen observado en el par semilla: N1 0.797 / N2 0.923 / "
                    "N3 0.907 contra floors 0.35/0.80/0.55 → holgura amplia. Clase que "
                    "podría escapar: dos docs con el mismo contenido pero divergencia OCR "
                    "tan alta que ni shingles ni tokens raros pasen el floor.",
            },
            "metodo": {
                "maquinaria": "reuso del audit s62 (scripts/s62_audit43.py, DECISIONS.md:909): "
                              "shingles de 8 palabras crc32 sobre norm_ocr + Jaccard",
                "desviaciones_declaradas_vs_s62": {
                    "D1_sin_cap": "s62 usa SHINGLE_CAP=4000 (bottom-k, lente de inventario); "
                                  "el span-diff DECIDE supresiones → conjuntos exactos",
                    "D2_sin_blocking_por_fabricante": "s62 solo comparaba dentro de cada "
                        "manufacturer; el par semilla cruza fabricante (European Safety "
                        "Systems vs Detnov) → s62 era ciego a esta clase",
                    "D3_span_diff_a_nivel_palabra": "no se cuentan chunks-gemelos: se marca "
                        "cubierta cada PALABRA que participe en un shingle compartido",
                },
                "blocking_nets": {
                    "N1_shingle_cont": NET_SHINGLE_CONT, "N2_token_cont": NET_TOKEN_CONT,
                    "N3_rare_token_cont": NET_RARE_CONT,
                    "N3_rare_def": f"tokens con document-frequency <= {RARE_DF_FRAC:.0%} de los docs",
                    "N4_same_sha256": True,
                    "por_que_contencion": "Jaccard penaliza la asimetría de tamaño y "
                                          "perdería el caso subset",
                    "conteos": {k: len(v) for k, v in nets.items()},
                },
                "span_diff": {
                    "covered_word_frac": "palabras que participan en >=1 shingle presente en "
                        "el doc ENTERO del otro lado / palabras totales del chunk",
                    "min_unique_span_words": MIN_UNIQUE_SPAN_WORDS,
                    "clases": {
                        "TWIN": f"covered>={TWIN_COVERED_FRAC} Y ninguna racha no cubierta "
                                f">={MIN_UNIQUE_SPAN_WORDS} palabras Y best_twin "
                                f"Jaccard>={POINTER_MIN_J} → ÚNICA clase proponible",
                        "COVERED_NO_TWIN": "cubierto pero sin gemelo puntual (re-chunkeo) → "
                                           "no hay FK honesta para duplicate_of → NO se propone",
                        "PARTIAL": f"covered en [{UNIQUE_COVERED_FRAC}, {TWIN_COVERED_FRAC}) "
                                   "o con racha única → NUNCA se suprime",
                        "UNIQUE": f"covered<{UNIQUE_COVERED_FRAC} → NUNCA se suprime",
                        "SHORT": f"<{SHINGLE_W} palabras, no shingleable → NUNCA se suprime",
                    },
                },
                "cualificacion_par": f"covered_word_frac del doc >= {PAIR_QUALIFY} en >=1 dirección",
                "calibracion": {
                    "criterio_literal_del_brief": f">=60% de los chunks con best-twin "
                        f"Jaccard >= {BRIEF_STRICT_TWIN_J}",
                    "campo": "brief_strict_frac_twin_j085 (por lado) / "
                             "brief_strict_criterion_met (por par)",
                    "HALLAZGO": "el criterio literal NO detecta el par SEMILLA (0.20/0.17 "
                        "frente al 0.60 exigido) aunque el par es un near-dup REAL "
                        "(covered_word_frac 0.89/0.72). Causa medida: los dos docs son "
                        "re-extracciones DISTINTAS del mismo PDF (15 vs 18 chunks) → el "
                        "Jaccard chunk↔chunk se diluye por desplazamiento de FRONTERAS y "
                        "por ruido OCR (p.ej. 't4135oc' vs 't4135°c'), no por contenido. "
                        "Un shingle de 8 palabras muere con UNA palabra distinta.",
                },
                "discriminador_de_identidad_de_producto": {
                    "regla": "si los DOS docs tienen `product_model` NO trivial y DISJUNTO "
                             "(normalizado, multi-modelo partido por / , ; +) → "
                             "KEEP-BOTH-SERIE, sin propuesta",
                    "por_que_es_NECESARIO": "medido en esta misma corrida: sin el "
                        "discriminador, 168 de los 226 pares que cualifican por cobertura "
                        "son HERMANAS DE SERIE (Aritech 2X-AT-F2/-S/-FB/-P, Kilsen "
                        "KE-IO3122/KE-IO3144, NC-PF2/NC-PF4, NAS-10/NAS-20, "
                        "AutoSAT-10/-20, SG200-IS/SG350-IS, FHSD8310/FHSD8330…): "
                        "datasheets del MISMO fabricante con plantilla común y 0.90+ de "
                        "cobertura mutua. Marcarlos `duplicate_of` haría que el bot sirviera "
                        "el manual del MODELO EQUIVOCADO = el daño exacto de DEC-091b. La "
                        "identidad del documento es la carga útil, no solo su texto.",
                    "residual_DECLARADO": "un duplicado REAL cuyos dos docs recibieron "
                        "etiquetas de modelo distintas (ambas no triviales) cae en "
                        "KEEP-BOTH-SERIE y se PIERDE. El par semilla se salva porque el doc "
                        "B tiene `product_model='unknown'`; si hubiera heredado su pm de "
                        "chunk ('VIA-28V', que es un artefacto de parseo de la frase «via "
                        "28V 93mA») el discriminador lo habría clasificado hermana-de-serie. "
                        "Mitigación ofrecida, NO automática: los KEEP-BOTH-SERIE van "
                        "ordenados por cobertura en el packet para que el ojo humano pase "
                        "por los más sospechosos.",
                    "lever_correcto_para_esa_clase": "dedup-EN-POOL (el fallback que el spec "
                        "v2-P2 deja explícitamente NO construido aquí): limita cuántos "
                        "slots se lleva un cluster sin borrar identidad.",
                },
                "politica_representante": {
                    "literal_spec_v2P2": "idiomas distintos → KEEP-BOTH; mismo idioma → más "
                        "spans únicos → empate: más reciente (revision_date → revision → "
                        "ingested_at)",
                    "refinamiento_propuesto": "primero AUTO-SOPORTE DE METADATA (¿aparecen "
                        "manufacturer/product_model del doc en su propio contenido?), luego "
                        "más spans únicos, luego recencia. Motivo: los spans únicos NUNCA se "
                        "suprimen (el gate ya los protege) → el conteo de spans únicos no "
                        "protege contenido; lo único que decide el representante es de QUÉ "
                        "doc sale la CITA del contenido compartido.",
                    "riesgo_del_refinamiento": "el auto-soporte es heurística de substring: "
                        "un manufacturer correcto que no se imprime en el manual puntúa 0 "
                        "(falso negativo) → los pares donde las dos políticas DIVERGEN van "
                        "marcados ADJUDICAR y su SQL sale COMENTADO por-fila",
                    "NUNCA_gana_es": "src/reingest/dedup.py:_preference (dedup del pipeline) "
                        "sí prefiere ES. En cat010 la aguja está en el doc EN → esa política "
                        "habría suprimido la aguja. Aquí NO se usa.",
                    "invariante": "solo se proponen chunks TWIN con puntero válido; "
                                  "UNIQUE/PARTIAL/COVERED_NO_TWIN/SHORT NUNCA se suprimen",
                },
                "consistencia_de_cluster": {
                    "problema": "las decisiones POR PAR no son globalmente consistentes: con "
                        ">2 docs near-dup encadenados aparecen CADENAS y CICLOS (medido: "
                        "MIE-MI-470→480→490→470 es un ciclo; NRX-OPT salía representante en "
                        "un par y suprimido en otro) → un chunk quedaría a la vez marcado y "
                        "canónico de otro, que es justo lo que aborta el guard 3e del paste.",
                    "como_se_detecto": "NO por revisión: por una pre-validación read-only de "
                        "los guards del paste contra la DB viva, que reportó 5 chunks en "
                        "cadena. El generador lleva ahora un assert que aborta si vuelve a "
                        "pasar (repetidos o cadenas).",
                    "fix": "componentes conexos sobre los pares SUPPRESS-COVERED; en cada "
                        "componente de >2 docs se elige UN representante (metadata "
                        "auto-soportada → spans únicos → recencia) y solo los pares que lo "
                        "contienen conservan propuesta, orientados hacia él; el resto se "
                        "queda sin propuesta.",
                    "clusters_de_mas_de_2_docs": cluster_report,
                },
                "gate_de_adjudicacion": {
                    "regla": "NINGÚN par entra vivo en el SQL: todas las filas salen "
                             "COMENTADAS con una casilla [ ] APROBAR por par",
                    "por_que": "el census midió que cada clase de candidato arrastra un "
                        "riesgo de IDENTIDAD que el umbral no resuelve: variantes "
                        "intrínsecamente-seguras (SG100 vs SG100-IS, SG200/SG350), "
                        "manual-vs-datasheet del mismo producto (MNDT1070 vs MFDT1070; "
                        "2X-A installation vs operation), módulos hermanos que comparten "
                        "un pm heredado o 'unknown' (MIE-MI-470/480/490; NRX-SMT3 vs "
                        "NRX-OPT con pm='B501RF' que es la BASE común), y rebadges OEM "
                        "Notifier/Morley. Un umbral no distingue esas clases; la "
                        "adjudicación sí. Esto ES el hallazgo, no una precaución genérica.",
                    "tiers": {
                        "T1-DOC-IDENTICO": "misma marca y cobertura >= 0.90 en AMBAS "
                                           "direcciones (el caso más fuerte)",
                        "T2-MISMA-MARCA": "misma marca, cobertura asimétrica o menor",
                        "T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA": "fabricantes distintos y al "
                            "menos uno NO auto-soportado por el contenido del propio doc. "
                            "Aquí vive el par SEMILLA (Detnov no aparece en su propio "
                            "texto). OJO: también caen aquí rebadges probablemente "
                            "legítimos cuya marca simplemente no se imprime en el manual "
                            "(FS8/MS8) → la casilla por par es el control.",
                    },
                },
                "artefacto_compacto": "los pares NO-QUALIFY viajan sin el detalle por chunk "
                                      "(`spans`) para que el JSON sea usable; sus métricas "
                                      "doc-level y conteos de clase sí van completos",
            },
            "satelites": sat,
            "totales": {
                "candidatos_blocking": len(cands),
                "pares_que_cualifican": sum(1 for p in pairs if p["qualifies_near_dup"]),
                "veredictos": dict(Counter(p["decision"]["verdict"] for p in pairs)),
                "pares_con_politicas_divergentes": sum(
                    1 for p in pairs if p["decision"].get("policies_diverge")),
                "tiers_de_los_pares_con_propuesta": dict(Counter(
                    p["decision"]["tier"] for p in pairs
                    if p["decision"]["verdict"] == "SUPPRESS-COVERED"
                    and p["decision"]["proposed_marks"])),
                "pares_con_propuesta": sum(
                    1 for p in pairs if p["decision"].get("proposed_marks")),
                "marcas_duplicate_of_propuestas": len(proposed_ids),
                "marcas_vivas_en_el_sql": 0,
            },
            "seed": {"pair": list(SEED_PAIR), "gold": SEED_GOLD},
        },
        "pairs": slim,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                        encoding="utf-8")
    print(f"7) → {OUT_JSON.relative_to(ROOT)} ({OUT_JSON.stat().st_size / 1024:.0f} KB)")

    # ---------------------------------------------------------------- SQL de staging
    chunk_content = {c["id"]: c.get("content") for c in chunks}
    blocks, n_rows, n_pairs_sql = [], 0, 0
    for p in pairs:
        d = p["decision"]
        if d["verdict"] != "SUPPRESS-COVERED" or not d["proposed_marks"]:
            continue
        rep, sup = d["representative"], d["suppressed"]
        R, S = by_id[rep], by_id[sup]
        pres = d.get("preserved_in_suppressed", {})
        n_pairs_sql += 1
        hdr = [
            "-- " + "─" * 96,
            f"-- PAR {n_pairs_sql}: {p['pair_id']}   [{d['tier']}]"
            + ("   *** PAR SEMILLA (cat010) ***" if p["is_seed_pair"] else ""),
            f"--   CONSERVA  {R.get('source_pdf_filename')!r}  "
            f"(manu={R.get('manufacturer')!r} pm={R.get('product_model')!r})",
            f"--   SUPRIME   {d['n_proposed_marks']} de {p['side_a']['n_chunks_active'] if sup == p['side_a']['document_id'] else p['side_b']['n_chunks_active']}"
            f" chunks de {S.get('source_pdf_filename')!r}  "
            f"(manu={S.get('manufacturer')!r} pm={S.get('product_model')!r})",
            f"--   PRESERVA  " + (", ".join(f"{k}={len(v)}" for k, v in pres.items())
                                  or "(nada más en el doc suprimido)"),
            f"--   cobertura {d['coverage_min']:.2f}/{d['coverage_max']:.2f} · motivo del "
            f"representante: {d['reason']}",
        ]
        if d.get("policies_diverge"):
            hdr.append("--   !! POLÍTICAS DIVERGENTES: la literal del spec conservaría "
                       f"{by_id[d['policy_literal']['representative']].get('source_pdf_filename')!r}"
                       f" ({d['policy_literal']['reason']})")
        hdr.append("--   [ ] APROBAR ESTE PAR  →  descomenta las filas de abajo "
                   "(quita el '-- ' inicial)")
        rows = []
        for m in d["proposed_marks"]:
            rows.append(
                f"--   ('{m['chunk_id']}','{m['canonical_chunk_id']}','{sup}','{rep}',"
                f"{m['covered_word_frac']},{m['twin_jaccard']},"
                f"{m['max_uncovered_span_words']},'{md5(chunk_content[m['chunk_id']])}',"
                f"'{p['pair_id']}'),")
            n_rows += 1
        blocks.append("\n".join(hdr + rows))
    values_block = "\n".join(blocks) if blocks else "--   (sin propuestas)"
    tier_counts = Counter(p["decision"]["tier"] for p in pairs
                          if p["decision"]["verdict"] == "SUPPRESS-COVERED"
                          and p["decision"]["proposed_marks"])
    sql = f"""-- s287 P2 — dedup a nivel DOCUMENTO: marca `duplicate_of` de los chunks GEMELOS
-- del doc no-representante. GENERADO read-only por scripts/s287_p2_dedup_census.py.
-- Spec: evals/s287_etapa2_design_brief_v1.md (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF Sol-6).
-- Census: evals/s287_p2_dedup_census_v1.json
-- Packet: evals/s287_p2_dedup_adjudicacion_packet_v1.md  ← LÉELO ANTES DE APROBAR NADA
--
-- ###########################################################################################
-- #  TODAS las filas salen COMENTADAS, A PROPÓSITO. Ningún par entra vivo.                  #
-- #  El census midió que CADA clase de candidato arrastra un riesgo de IDENTIDAD que solo   #
-- #  la adjudicación resuelve (variantes -IS, manual-vs-datasheet, módulos hermanos con     #
-- #  pm='unknown', rebadges OEM Notifier/Morley). APROBAR UN PAR = quitar el '-- ' inicial  #
-- #  de las filas de su bloque. No hay que tocar comas: la fila SENTINELA cierra el VALUES. #
-- ###########################################################################################
--
-- INVARIANTE del gate SPAN-DIFF (re-verificado en SQL, guard 3f): solo se marcan chunks de
-- clase TWIN — >= {TWIN_COVERED_FRAC} de sus palabras cubiertas por el doc representante,
-- NINGUNA racha no cubierta de >= {MIN_UNIQUE_SPAN_WORDS} palabras, y gemelo con
-- Jaccard >= {POINTER_MIN_J}. Los chunks UNIQUE / PARTIAL / COVERED_NO_TWIN / SHORT NO se
-- tocan: siguen sirviéndose desde el doc "suprimido" (la supresión es POR CHUNK, no por doc).
--
-- Propuestas: {n_rows} marcas en {n_pairs_sql} pares · tiers {dict(tier_counts)}
-- Dry-run: cambia COMMIT por ROLLBACK.

BEGIN;

-- 1. STAGING (scratch; el paste la crea y la puebla — no hay carga previa)
DROP TABLE IF EXISTS _s287_dedup_staging;
CREATE TABLE _s287_dedup_staging (
  chunk_id                 uuid PRIMARY KEY,
  canonical_chunk_id       uuid NOT NULL,
  doc_suppressed           uuid NOT NULL,
  doc_representative       uuid NOT NULL,
  covered_word_frac        numeric NOT NULL,
  twin_jaccard             numeric NOT NULL,
  max_uncovered_span_words int NOT NULL,
  md5_content_before       text NOT NULL,
  pair_id                  text NOT NULL
);

-- Cada fila real termina en coma y la última fila del VALUES es la SENTINELA (sin coma) →
-- puedes descomentar CUALQUIER subconjunto de bloques sin tocar comas.
INSERT INTO _s287_dedup_staging
 (chunk_id, canonical_chunk_id, doc_suppressed, doc_representative,
  covered_word_frac, twin_jaccard, max_uncovered_span_words, md5_content_before, pair_id)
VALUES
{values_block}
  ('00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',
   '00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',
   0, 0, 0, '', '__SENTINELA__');
-- La fila SENTINELA existe solo para que el INSERT sea sintácticamente válido cuando TODAS
-- las filas reales están comentadas. Se borra aquí; si no aprobaste ningún par, la staging
-- queda vacía y el guard 3 aborta la transacción (nada se aplica).
DELETE FROM _s287_dedup_staging WHERE pair_id = '__SENTINELA__';

-- 2. BACKUP (persistente, para rollback post-COMMIT)
CREATE TABLE IF NOT EXISTS _s287_dedup_backup AS
SELECT c.id, c.duplicate_of, md5(c.content) AS md5_content, now() AS backed_at
FROM {CHUNKS_TABLE} c
WHERE c.id IN (SELECT chunk_id FROM _s287_dedup_staging);

-- 3. GUARDS previos (cualquiera aborta TODO)
DO $$
DECLARE n int; m int;
BEGIN
  SELECT count(*) INTO n FROM _s287_dedup_staging;
  IF n = 0 THEN RAISE EXCEPTION 'staging vacía — nada que aplicar (adjudica y descomenta)'; END IF;

  -- 3a. anti-deriva: el contenido de cada chunk es el que vio el census
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN {CHUNKS_TABLE} c ON c.id = s.chunk_id
   WHERE md5(c.content) <> s.md5_content_before;
  IF m > 0 THEN RAISE EXCEPTION 'DERIVA: % chunks cambiaron de contenido desde el census', m; END IF;

  -- 3b. ninguno estaba ya marcado
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN {CHUNKS_TABLE} c ON c.id = s.chunk_id
   WHERE c.duplicate_of IS NOT NULL;
  IF m > 0 THEN RAISE EXCEPTION '% chunks ya tenían duplicate_of', m; END IF;

  -- 3c. el canónico existe, vive en el doc REPRESENTANTE y NO está marcado (sin cadenas)
  SELECT count(*) INTO m FROM _s287_dedup_staging s
    LEFT JOIN {CHUNKS_TABLE} c ON c.id = s.canonical_chunk_id
   WHERE c.id IS NULL OR c.duplicate_of IS NOT NULL OR c.document_id <> s.doc_representative;
  IF m > 0 THEN RAISE EXCEPTION '% punteros canónicos inválidos (inexistente, ya duplicado, o fuera del representante)', m; END IF;

  -- 3d. el chunk a marcar vive en el doc SUPRIMIDO
  SELECT count(*) INTO m FROM _s287_dedup_staging s JOIN {CHUNKS_TABLE} c ON c.id = s.chunk_id
   WHERE c.document_id <> s.doc_suppressed;
  IF m > 0 THEN RAISE EXCEPTION '% chunks no pertenecen al doc que se suprime', m; END IF;

  -- 3e. ningún chunk es a la vez marcado y canónico de otro
  SELECT count(*) INTO m FROM _s287_dedup_staging a
    JOIN _s287_dedup_staging b ON a.chunk_id = b.canonical_chunk_id;
  IF m > 0 THEN RAISE EXCEPTION 'cadena de duplicados detectada (% filas)', m; END IF;

  -- 3f. el invariante del gate viaja en los datos y se re-verifica aquí
  SELECT count(*) INTO m FROM _s287_dedup_staging
   WHERE covered_word_frac < {TWIN_COVERED_FRAC}
      OR max_uncovered_span_words >= {MIN_UNIQUE_SPAN_WORDS}
      OR twin_jaccard < {POINTER_MIN_J};
  IF m > 0 THEN RAISE EXCEPTION 'GATE SPAN-DIFF violado en % filas — ABORTA', m; END IF;

  -- 3g. FUGA de satélites: el RPC de enunciados NO filtra por duplicate_of del padre
  --     (migrations/012_enunciados_rpc_filters.sql) → si hubiera filas, marcarlas aquí
  --     dejaría contenido retirado servible por el canal multivector.
  SELECT count(*) INTO m FROM chunks_v2_enunciados e
   WHERE e.parent_id IN (SELECT chunk_id FROM _s287_dedup_staging);
  IF m > 0 THEN RAISE EXCEPTION 'FUGA enunciados: % filas cuelgan de chunks a marcar — trátalas antes', m; END IF;
  -- (hyq NO necesita tratamiento: retriever.py:1095-1098 ya lo guarda client-side)
END $$;

-- 4. UPDATE atómico
WITH upd AS (
  UPDATE {CHUNKS_TABLE} c
     SET duplicate_of = s.canonical_chunk_id
    FROM _s287_dedup_staging s
   WHERE c.id = s.chunk_id
     AND c.duplicate_of IS NULL
     AND md5(c.content) = s.md5_content_before
  RETURNING c.id
)
SELECT count(*) AS updated INTO TEMP tmp_s287_updated FROM upd;

DO $$
DECLARE n int; e int;
BEGIN
  SELECT updated INTO n FROM tmp_s287_updated;
  SELECT count(*) INTO e FROM _s287_dedup_staging;
  IF n <> e THEN RAISE EXCEPTION 'updated % <> staging % — ABORTA TODO', n, e; END IF;
END $$;

SELECT (SELECT count(*) FROM _s287_dedup_staging) AS staged,
       (SELECT updated FROM tmp_s287_updated)     AS updated,
       (SELECT count(*) FROM _s287_dedup_backup)  AS backed_up;

-- ROLLBACK post-COMMIT:
--   UPDATE {CHUNKS_TABLE} c SET duplicate_of = b.duplicate_of
--     FROM _s287_dedup_backup b WHERE c.id = b.id;

COMMIT;   -- <-- para dry-run: ROLLBACK
"""
    OUT_SQL.write_text(sql, encoding="utf-8", newline="\n")
    print(f"8) → {OUT_SQL.relative_to(ROOT)} ({n_rows} marcas propuestas en "
          f"{n_pairs_sql} pares, TODAS comentadas · tiers {dict(tier_counts)})")

    # ---------------------------------------------------------------- PACKET de adjudicación
    def fn(did):
        return by_id[did].get("source_pdf_filename") or did[:8]

    def sideof(p, did):
        return p["side_a"] if p["side_a"]["document_id"] == did else p["side_b"]

    props = [p for p in pairs if p["decision"].get("proposed_marks")]
    seed = next((p for p in pairs if p["is_seed_pair"]), None)
    L: list[str] = []
    A_ = L.append
    A_("# s287 P2 — PACKET DE ADJUDICACIÓN: near-duplicados a nivel DOCUMENTO")
    A_("")
    A_(f"Generado read-only por `scripts/s287_p2_dedup_census.py` · {_now()} · git `{_git()}` · "
       "rama `claude/s282-h0t2-qa`. **Cero escrituras a DB.**")
    A_("Spec: `evals/s287_etapa2_design_brief_v1.md` (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF "
       "de Sol-6). Datos: `evals/s287_p2_dedup_census_v1.json`. Paste: "
       "`evals/s287_p2_dedup_apply_v1.sql`.")
    A_("")
    A_("## Qué decidir y cómo")
    A_("")
    A_("El census propone marcar `duplicate_of` **chunk a chunk** (no doc a doc): de un par de "
       "documentos casi idénticos se retira del pool SOLO los chunks del no-representante cuyo "
       "contenido está **íntegramente** en el representante. Todo lo demás sigue sirviéndose.")
    A_("")
    A_(f"- **{len(props)} pares** con propuesta · **{len(proposed_ids)} marcas** de chunk.")
    A_("- **Ninguna fila entra viva.** En el `.sql` todas están comentadas con una casilla "
       "`[ ] APROBAR ESTE PAR`. Aprobar = quitar el `-- ` inicial de las filas de ese bloque "
       "(no hay que tocar comas).")
    A_("- Si no apruebas nada y pegas el SQL igualmente, el guard 3 aborta la transacción y no "
       "se aplica nada.")
    A_("")
    A_("### El invariante que protege el corpus (gate de Sol-6)")
    A_("")
    A_(f"Un chunk solo se propone si (a) ≥ **{TWIN_COVERED_FRAC:.0%} de sus palabras** están "
       f"cubiertas por el documento representante, (b) **ninguna racha de ≥ "
       f"{MIN_UNIQUE_SPAN_WORDS} palabras** queda sin cubrir, y (c) existe un chunk gemelo "
       f"concreto con Jaccard ≥ {POINTER_MIN_J} al que apuntar. Los chunks `UNIQUE`, "
       "`PARTIAL`, `COVERED_NO_TWIN` y `SHORT` **nunca** se proponen — un near-dup a nivel "
       "documento puede perfectamente tener spans propios, y el par semilla lo demuestra.")
    A_("")

    # ---- SEMILLA
    if seed:
        d = seed["decision"]
        rep, sup = d["representative"], d["suppressed"]
        R, S = sideof(seed, rep), sideof(seed, sup)
        A_("---")
        A_("")
        A_("## 1. PAR SEMILLA (cat010) — análisis completo")
        A_("")
        A_(f"`{seed['pair_id']}` · tier **{d['tier']}** · cobertura de palabras "
           f"{d['coverage_min']:.2f} / {d['coverage_max']:.2f}")
        A_("")
        A_("| | doc A (recomendado CONSERVAR) | doc B (recomendado SUPRIMIR-parcial) |")
        A_("|---|---|---|")
        A_(f"| `source_pdf_filename` | `{R['source_pdf_filename']}` | `{S['source_pdf_filename']}` |")
        A_(f"| `document_id` | `{R['document_id']}` | `{S['document_id']}` |")
        A_(f"| `manufacturer` | **{R['manufacturer']}** | **{S['manufacturer']}** |")
        A_(f"| `product_model` (doc) | {R['product_model']} | {S['product_model']} |")
        A_(f"| `product_model` (chunks) | {list(R['chunk_product_models'])} | {list(S['chunk_product_models'])} |")
        A_(f"| idioma (mayoría de chunks) | {R['chunk_language_majority']} | {S['chunk_language_majority']} |")
        A_(f"| chunks activos | {R['n_chunks_active']} | {S['n_chunks_active']} |")
        A_(f"| páginas | {R['pages']} | {S['pages']} |")
        A_(f"| `revision` / `revision_date` | {R['revision']} / {R['revision_date']} | {S['revision']} / {S['revision_date']} |")
        A_(f"| `ingested_at` | {R['ingested_at']} | {S['ingested_at']} |")
        A_(f"| palabras cubiertas por el otro doc | **{R['covered_word_frac_doc']:.1%}** | **{S['covered_word_frac_doc']:.1%}** |")
        A_(f"| clases de span | {R['classes']} | {S['classes']} |")
        A_("")
        A_("### 1.1 Qué son estos dos documentos")
        A_("")
        A_("Son **dos extracciones distintas del MISMO manual de e2S** (el sounder ATEX "
           "IS-mA1). Lo prueba el contenido, no la metadata: los dos textos contienen "
           "`european safety systems` y `e2s`, los dos contienen `is-ma1`, y los pares de "
           "chunks gemelos llegan a Jaccard **1.000**.")
        A_("")
        A_("### 1.2 La metadata de B está MAL (verificado contra su propio texto)")
        A_("")
        A_(f"- `{S['source_pdf_filename']}` está atribuido a **{S['manufacturer']}**, y la "
           f"cadena `detnov` **no aparece en su propio contenido** "
           f"(`metadata_self_support.manufacturer.supported = "
           f"{S['metadata_self_support']['manufacturer']['supported']}`). Su texto dice "
           "`european safety systems ltd. impress house, mansell road, acton, london w37qh`.")
        A_(f"- Su `product_model` es `{S['product_model']}` a nivel doc y "
           f"`{list(S['chunk_product_models'])}` a nivel chunk. **`VIA-28V` es un artefacto "
           "de parseo**: viene de la frase del manual «a 24V dc supply **via 28V** 93mA "
           "resistive ATEX ... Zener Barriers». No es un modelo.")
        A_(f"- `{R['source_pdf_filename']}` está atribuido a **{R['manufacturer']}**, y sus "
           "tres tokens SÍ aparecen en su contenido. Su pm de chunk es `IS-mA1` (correcto).")
        A_("")
        A_("### 1.3 Por qué NO se puede suprimir B entero (el gate de Sol-6 mordiendo)")
        A_("")
        A_(f"El PDF de B tiene **{len(S['pages'])} páginas** frente a {len(R['pages'])} de A. "
           "Sus páginas finales son contenido **ausente de A**:")
        A_("")
        uq = [r for r in S["spans"] if r["class"] == "UNIQUE"]
        for r in sorted(uq, key=lambda x: -(x["max_uncovered_span_words"])):
            A_(f"- chunk `{r['chunk_id'][:8]}` (idx {r['chunk_index']}, p{r['page']}, "
               f"{r['n_words']} palabras): cubierto solo al **{r['covered_word_frac']:.1%}**, "
               f"racha única de **{r['max_uncovered_span_words']} palabras**.")
            if r["uncovered_spans"]:
                A_(f"  > {r['uncovered_spans'][0]['text'][:230]}")
        A_("")
        A_("Es el **control drawing / schedule drawing ATEX** con los *entity parameters* "
           "(`Ui = 28V`, `Ii = 93mA`…) y las condiciones de instalación con barrera Zener. "
           "Eso es **exactamente el territorio de los hechos de cat010** — y solo existe en B. "
           "Suprimir B entero habría borrado contenido servible relevante para el propio gold "
           "que motivó esta pieza. Los 4 chunks van marcados `UNIQUE` → **no se tocan**.")
        A_("")
        A_("### 1.4 Las dos políticas de representante DIVERGEN aquí")
        A_("")
        A_(f"- **Literal del spec v2-P2** (más spans únicos gana): conservaría "
           f"`{fn(d['policy_literal']['representative'])}` — {d['policy_literal']['reason']}.")
        A_(f"- **Refinamiento propuesto** (auto-soporte de metadata primero): conserva "
           f"`{fn(d['policy_recommended']['representative'])}` — {d['policy_recommended']['reason']}.")
        A_("")
        A_("**Recomiendo el refinamiento, y creo que el criterio literal está mal para este "
           "problema.** Razón: los spans únicos **nunca se suprimen** — ya los protege el "
           "gate. Así que «más spans únicos» no protege ningún contenido; lo único que decide "
           "el representante es **de qué documento sale la CITA** del contenido compartido. "
           "Con el criterio literal, el bot respondería los hechos de cat010 citando "
           f"`{fn(d['policy_literal']['representative'])}` atribuido a **Detnov** para un "
           "producto de e2S. Con el refinamiento, cita el manual correcto y las páginas "
           "únicas de B siguen disponibles.")
        A_("")
        A_("**Riesgo del refinamiento, declarado:** el auto-soporte es una heurística de "
           "substring. Un `manufacturer` correcto que simplemente no se imprime en el manual "
           "puntúa 0 (falso negativo) — por eso no se aplica solo y todos los pares "
           "divergentes van a tu casilla.")
        A_("")
        A_("### 1.5 Efecto esperado sobre el pool de cat010")
        A_("")
        A_(f"Se retirarían **{d['n_proposed_marks']} de {S['n_chunks_active']}** chunks de B "
           "(los gemelos), liberando los slots que el diagnóstico midió comidos por el doc "
           "gemelo, y quedarían servibles los "
           f"{sum(len(v) for v in d.get('preserved_in_suppressed', {}).values())} restantes "
           f"({', '.join(f'{k}={len(v)}' for k, v in d.get('preserved_in_suppressed', {}).items())}) "
           "más los 15 de A. **No medido aquí**: el efecto en el pool/composición es el gate "
           "de la pieza (probe de cat010 + sweep-39), no una promesa de este census.")
        A_("")

    # ---- resumen global
    A_("---")
    A_("")
    A_("## 2. Alcance del census y qué NO se toca")
    A_("")
    A_(f"- Universo servido: **{len(universe)} documentos** `status='active'` con chunks "
       f"`duplicate_of IS NULL` ({n_univ_chunks} chunks). Excluidos y por qué: en "
       "`meta.alcance_declarado.exclusiones` del JSON.")
    A_(f"- **CORPUS-WIDE all-pairs: {n_pairs_total} pares evaluados**, sin blocking por "
       "fabricante ni por título. Esto era obligatorio: el par semilla **cruza fabricante** "
       "(European Safety Systems vs Detnov), así que el audit s62 —que solo comparaba dentro "
       "de cada `manufacturer`— era estructuralmente incapaz de verlo.")
    A_(f"- {len(cands)} candidatos tras el blocking (unión de 4 nets) → "
       f"{sum(1 for p in pairs if p['qualifies_near_dup'])} cualifican como near-dup de "
       "documento.")
    A_("")
    A_("| veredicto | pares | qué significa |")
    A_("|---|---|---|")
    vc = Counter(p["decision"]["verdict"] for p in pairs)
    A_(f"| `SUPPRESS-COVERED` | {vc['SUPPRESS-COVERED']} | candidatos reales de dedup "
       f"({len(props)} con marcas concretas) |")
    A_(f"| `KEEP-BOTH-LANG` | {vc['KEEP-BOTH-LANG']} | idiomas distintos → variante de "
       "mercado, NUNCA suprimir |")
    A_(f"| `KEEP-BOTH-BRAND` | {vc['KEEP-BOTH-BRAND']} | rebadge OEM legítimo (cada doc "
       "imprime su propia marca) → workstream de identidad D1/D3, no dedup |")
    A_(f"| `KEEP-BOTH-SERIE` | {vc['KEEP-BOTH-SERIE']} | hermanas de serie (modelos distintos, "
       "plantilla común) → suprimir aquí es el daño DEC-091b |")
    A_(f"| `NO-QUALIFY` | {vc['NO-QUALIFY']} | solape parcial (boilerplate), no near-dup |")
    A_("")
    A_("### 2.1 El hallazgo que cambia la pieza: la mayoría de los near-dups NO son dedupables")
    A_("")
    A_(f"De los {sum(1 for p in pairs if p['qualifies_near_dup'])} pares que cualifican por "
       f"cobertura de contenido, **{vc['KEEP-BOTH-SERIE']} son hermanas de serie** — "
       "datasheets del mismo fabricante con plantilla común y 0.90+ de cobertura mutua "
       "(Aritech `2X-AT-F2`/`-S`/`-FB`/`-P`, Kilsen `KE-IO3122`/`KE-IO3144`, "
       "`NC-PF2`/`NC-PF4`, `NAS-10`/`NAS-20`, `AutoSAT-10`/`-20`, `SG200-IS`/`SG350-IS`, "
       "`FHSD8310`/`FHSD8330`…). Marcarlas `duplicate_of` haría que el bot sirviera el manual "
       "del **modelo equivocado**: el daño exacto de DEC-091b. Para esa clase el lever "
       "correcto es el **dedup-EN-POOL** (el fallback que el spec deja explícitamente no "
       "construido aquí), que limita slots sin borrar identidad.")
    A_("")
    A_(f"Y **{vc['KEEP-BOTH-BRAND']} son rebadges OEM Notifier↔Morley** con las dos marcas "
       "impresas en sus propios textos (`MNDT102`/`MIEMN570` para RP1r, `MIDT015`/"
       "`MIE-MI-100` para NFS2-8…). Deduplicarlos colapsaría distinciones que ya adjudicaste "
       "en s78/s80 (RP1r-Supra=Notifier vs VSN-RP1r=Morley).")
    A_("")

    # ---- tabla de adjudicación
    A_("---")
    A_("")
    A_("## 3. Pares a adjudicar (los que tienen propuesta)")
    A_("")
    A_("Ordenados: semilla primero, luego por nº de marcas. `div` = las dos políticas de "
       "representante discrepan.")
    A_("")
    A_("| # | par | tier | div | CONSERVA | SUPRIME (marcas/total) | PRESERVA | cob. | motivo |")
    A_("|---|---|---|---|---|---|---|---|---|")
    for i, p in enumerate(props, 1):
        d = p["decision"]
        S = sideof(p, d["suppressed"])
        pres = ", ".join(f"{k}={len(v)}" for k, v in d.get("preserved_in_suppressed", {}).items())
        A_(f"| {i}{' **SEMILLA**' if p['is_seed_pair'] else ''} | `{p['pair_id']}` | "
           f"{d['tier'].split('-')[0]} | {'SÍ' if d['policies_diverge'] else ''} | "
           f"`{fn(d['representative'])}` ({sideof(p, d['representative'])['manufacturer']}) | "
           f"`{fn(d['suppressed'])}` ({S['manufacturer']}) {d['n_proposed_marks']}/"
           f"{S['n_chunks_active']} | {pres or '—'} | "
           f"{d['coverage_min']:.2f}/{d['coverage_max']:.2f} | {d['reason']} |")
    A_("")
    A_("### 3.1 Clases de falso positivo que YA vi en esta tabla (mira antes de aprobar)")
    A_("")
    A_("El census no las puede separar por umbral; por eso todo va comentado:")
    A_("")
    A_("- **Variante intrínsecamente segura vs estándar**: `SG100` vs `SG100-IS`, `SG200` vs "
       "`SG200-IS`, `SG350` vs `SG350-IS` (Argus). Productos DISTINTOS con manual casi igual.")
    A_("- **Manual vs datasheet/ficha del mismo producto**: `MNDT1070` vs `MFDT1070` "
       "(LTS-240), `MNDT516` vs `MNDT516_PL4_ESP-PORT`, `2x-a_series_installation` vs "
       "`2x-a_series_operation`. Documentos distintos por FUNCIÓN.")
    A_("- **Módulos hermanos con `pm` heredado o `unknown`**: `MIE-MI-470`/`480`/`490` "
       "(Morley), `NRX-SMT3` vs `NRX-OPT` (los dos con `pm='B501RF'`, que es la BASE común, "
       "no el detector), `D 1148-1 BRS` vs `D 1147-1 BRH` (los dos `pm='B501AP'`). El "
       "discriminador de serie no los pilla porque su `pm` no distingue.")
    A_("- **Duplicados de verdad, casi seguros**: `TIDT089_copia` vs `TIDT089`, el FAQ DXc "
       "`Averia-de-resistencia-de-baterias` duplicado con el título reordenado, y "
       "`Con-que-Sistema-Operativo-es-compatible-el-programa-…` repetido.")
    A_("")

    # ---- gaps
    A_("---")
    A_("")
    A_("## 4. Gaps y riesgos declarados")
    A_("")
    A_("1. **El criterio literal del brief no funciona** (hallazgo de calibración). "
       f"«≥60% de los chunks con Jaccard ≥ {BRIEF_STRICT_TWIN_J} contra algún chunk del otro» "
       f"da {seed['side_a']['brief_strict_frac_twin_j085']:.2f}/"
       f"{seed['side_b']['brief_strict_frac_twin_j085']:.2f} en el par semilla — no lo "
       "detecta, siendo un near-dup real. Causa medida: son re-extracciones distintas del "
       "mismo PDF (15 vs 18 chunks), el Jaccard chunk↔chunk se diluye por **desplazamiento "
       "de fronteras** y ruido OCR (`t4135oc` vs `t4135°c`), no por contenido; un shingle de "
       "8 palabras muere con UNA palabra distinta. Por eso el census mide cobertura de "
       "**palabras** contra el documento entero. Solo 1 par del corpus pasa el criterio "
       "literal.")
    A_("2. **Recall del blocking: sin cota dura.** No existe net barato con garantía frente a "
       "un criterio de cobertura de palabras. Se usa la unión de 4 nets; el margen del par "
       "semilla es amplio (N1 0.797 / N2 0.923 / N3 0.907 sobre floors 0.35 / 0.80 / 0.55). "
       "Clase que podría escapar: dos docs con el mismo contenido y divergencia OCR tan alta "
       "que ningún net pase el floor.")
    A_("3. **Residual del discriminador de serie.** Un duplicado real cuyos dos docs tengan "
       "etiquetas de modelo distintas y no triviales cae en `KEEP-BOTH-SERIE` y se pierde. El "
       "par semilla se salva solo porque B tiene `pm='unknown'`; si hubiera heredado su `pm` "
       "de chunk (`VIA-28V`, el artefacto de parseo) lo habría clasificado hermana-de-serie.")
    A_("4. **Fuga de satélites al marcar `duplicate_of` (encontrada de paso).** El RPC "
       "`match_chunks_v2_enunciados` (`migrations/012_enunciados_rpc_filters.sql`) **no filtra "
       "por el `duplicate_of` del padre**, así que el comentario de `retriever.py:1097` («el "
       "canal de enunciados sí filtra en SQL») es inexacto. Hoy es inerte: "
       f"`chunks_v2_enunciados` tiene **0 filas** colgando de los "
       f"{len(proposed_ids)} chunks propuestos (y 0 sobre una muestra de 300 chunks ya "
       "marcados) porque la tabla se pobló excluyendo duplicados "
       "(`scripts/enunciados_pass.py:107`). Eso es una propiedad del **poblado**, no del "
       "**servicio** → el paste lleva el guard 3g que ABORTA si alguna marca tuviera filas de "
       f"enunciados. `hyq` sí tiene filas ({sat['hyq_rows_on_proposed']} sobre los chunks "
       "propuestos) pero está guardado client-side (`retriever.py:1095-1098`, fix s286) → no "
       "resucita contenido.")
    if cluster_report:
        A_("5. **Consistencia de cluster (bug cazado y arreglado durante el census).** Las "
           "decisiones por par no son globalmente consistentes: con >2 documentos near-dup "
           "encadenados salían CADENAS y hasta un CICLO "
           "(`MIE-MI-470`→`480`→`490`→`470`), y `NRX-OPT` aparecía como representante en un "
           "par y como suprimido en otro → 5 chunks habrían quedado a la vez marcados y "
           "canónicos, abortando el guard 3e. Lo detectó una **pre-validación read-only de "
           "los guards del paste contra la DB viva**, no una revisión a ojo. Arreglado: se "
           "elige UN representante por componente conexo y solo los pares que lo contienen "
           "conservan propuesta. Componentes afectados:")
        for e in cluster_report:
            A_(f"   - {e['size']} docs → representante `{e['representative_file']}` · "
               f"{e['reorientados']} par(es) reorientado(s), {e['sin_propuesta']} sin "
               "propuesta.")
        A_("   El generador lleva ahora un `assert` que aborta si reaparecen chunk_ids "
           "repetidos o cadenas.")
    A_("6. **Nada medido en pool/eval.** Este artefacto es un census + propuesta. El delta "
       "(probe de composición del pool de cat010 + sweep-39 de no-regresión) es el gate de la "
       "pieza y no se ha corrido aquí.")
    A_("7. **`duplicate_of` no es reversible-gratis a nivel semántico**: el UPDATE sí es "
       "reversible (backup + rollback documentado), pero el chunk retirado deja de competir "
       "en TODOS los canales, no solo en el pool donde molestaba.")
    A_("")
    A_("---")
    A_("")
    A_("## 5. Cómo aplicar")
    A_("")
    A_("1. Lee la tabla §3 y marca las casillas `[ ] APROBAR ESTE PAR` que quieras en "
       "`evals/s287_p2_dedup_apply_v1.sql`, descomentando las filas de esos bloques.")
    A_("2. Pega el SQL con `COMMIT` cambiado por `ROLLBACK` (dry-run): verás `staged` / "
       "`updated` / `backed_up` y saltará cualquier guard.")
    A_("3. Si cuadra, pégalo con `COMMIT`.")
    A_("4. Rollback post-COMMIT (está al pie del `.sql`): "
       "`UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of FROM _s287_dedup_backup b "
       "WHERE c.id = b.id;`")
    A_("")
    A_("Guards del paste: anti-deriva md5 por chunk · ninguno ya marcado · puntero canónico "
       "existente, no-duplicado y dentro del representante · el chunk marcado pertenece al "
       "doc suprimido · sin cadenas de duplicados · **re-verificación en SQL del invariante "
       "span-diff** · sin filas de enunciados colgando · `updated == staged` o aborta.")
    A_("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"9) → {OUT_MD.relative_to(ROOT)} ({OUT_MD.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
