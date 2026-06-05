#!/usr/bin/env python3
"""audit_retrieval_funnel.py — DEC-003: ¿retrieval-miss o sintesis-incompleta?

Para cada pregunta del ruler, reproduce el embudo de retrieval del bot con
HyDE-OFF (como el A/B de s34) y localiza, hecho atomico CORE a hecho, en que
etapa del embudo esta (o no) el dato del gold:

  corpus (chunks_v2)  --retrieve(50)-->  pool50  --rerank(5)-->  top5  --> generador

Clasificacion por hecho CORE (estado=presente):
  - SINTESIS    : el valor esta en top5 (el generador lo VIO) -> si el bot no lo
                  uso, el cuello es GENERACION.
  - RERANK-MISS : esta en pool50 pero el reranker lo dejo fuera del top5 ->
                  cuello = reranker / separar generate_top_k.
  - RETRIEVAL   : NO esta en pool50, pero el manual SI es servible en chunks_v2
                  -> cuello = retrieval (HyDE/BM25/embeddings/filtro de modelo).
  - CORPUS-GAP  : el manual objetivo no esta en chunks_v2 -> cuello = extraccion (#10).

El matcher es el ESTRICTO de PR#15 (strict_match): valores distintivos (numeros
>=2 digitos, codigos) OCR-normalizados; prosa pura -> overlap. Transparente: se
registran los anchors usados.

NO regenera la respuesta del bot (eso ya vive en evals/bot_vs_gold_results_k5_*).
Solo mide el embudo de retrieval, que es lo que decide el lever (DEC-003).

Uso:
  python scripts/audit_retrieval_funnel.py            # los 18 (PARCIAL+FALLO)
  python scripts/audit_retrieval_funnel.py --all      # los 19 (incl. hp013 PASS)
  python scripts/audit_retrieval_funnel.py --qids hp017,hp018
Salida: evals/dec003_retrieval_funnel.yaml + tabla por consola.
"""
from __future__ import annotations

import os
# chunks_v2 + HyDE OFF ANTES de importar config/retriever (leen el env al cargar).
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import re
import sys
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))

from src.config import CHUNKS_IS_V2, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.retriever import retrieve_chunks, extract_product_models  # noqa: E402
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402
from src.rag.hyde import HYDE_ENABLED  # noqa: E402
from scripts.strict_match import norm_ocr, distinctive, chunk_has_quote_strict, anchor_present  # noqa: E402

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"
# Veredictos de la corrida HyDE-OFF @ pool-50 de s45 (solo ANOTACION; los BUCKETS son la senal).
BVG = ROOT / "evals" / "_s45_results_k50_hydeOFF.yaml"
OUT = ROOT / "evals" / "dec003_retrieval_funnel.yaml"

RETRIEVE_K = 50   # s45: pool-50 (retrieve-wide RETRIEVAL_TOP_K=50, shipped s44). Antes 15
                  # = medía un pipeline que ya no existe (bug cazado por el dúo s45).
RERANK_K = 5

# El unico PASS estable (B y A). Los 18 restantes = universo a auditar (DEC-003).
STABLE_PASS = {"hp013"}


# --- anchors -----------------------------------------------------------------
# El anchor sale del VALOR (identificador distintivo del hecho, RULER_DESIGN §3),
# NO del texto: el texto lleva REFERENCIAS de cita ("(MIDT170)", "(50253SP 2-44)",
# "(cap A5.3)") que NO son contenido del manual -> exigirlas en un chunk daba
# falsos negativos (hp006 pedia midt170/50253/-44 dentro del chunk).
_GENERIC = {"1 a", "1a", "2", "3", "0", "00", "no", "si"}  # valores demasiado debiles


def fact_probe(valor: str, texto: str) -> tuple[str, object, str]:
    """Devuelve (kind, probe, strength).

    kind='anchors' -> set de numeros>=2dig/codigos (de VALOR); todos en un chunk.
    kind='quote'   -> substring/overlap del valor (prosa o codigo corto tipo 6K8).
    strength='fuerte' (numero>=2dig/codigo/codigo-corto>=3 alnum) | 'debil' (prosa
       generica). La conclusion se apoya en los fuertes; los debiles se reportan.
    """
    v = (valor or "").strip()
    if v:
        anchors = distinctive(v)
        if anchors:
            # FUERTE solo si hay codigo de modelo, o un numero >=3 digitos, o >=2
            # anchors distintos. Un SOLO numero de 2 digitos ('10','25','80',...)
            # matchea espuriamente cualquier chunk con ese numero -> DEBIL (cazado
            # por el revisor adversarial: inflaba SINTESIS y deflactaba RETRIEVAL).
            has_model = any(re.search(r"[a-z]", a) for a in anchors)
            has_long_num = any(len(re.sub(r"\D", "", a)) >= 3 for a in anchors)
            strength = "fuerte" if (has_model or has_long_num or len(anchors) >= 2) else "debil"
            return "anchors", anchors, strength
        nv = norm_ocr(v)
        # codigo corto alfanumerico con letra+digito (6K8, JP2, ISO-X, TB1-3, 7.6.1) -> fuerte
        strong_code = (bool(re.search(r"\d", nv)) and bool(re.search(r"[a-z]", nv))
                       and len(re.sub(r"[^a-z0-9]", "", nv)) >= 3 and nv not in _GENERIC)
        strength = "fuerte" if strong_code else "debil"
        return "quote", v, strength
    return "quote", texto or "", "debil"


def _chunk_has(content: str, kind: str, probe) -> bool:
    """¿UN chunk concreto contiene el dato? (per-chunk, no blob agregado).

    Per-chunk es la semantica correcta ('el chunk que contiene el dato'): exigir
    TODOS los anchors en el MISMO chunk evita el falso positivo de ensamblar el
    dato a partir de numeros de chunks distintos (hp019: '-30' de una nota + '+60'
    del rango de la TUBERIA, sin que ningun chunk tenga el spec del DETECTOR)."""
    if kind == "anchors":
        nc = norm_ocr(content or "")
        return all(anchor_present(a, nc) for a in probe)
    return chunk_has_quote_strict(content or "", str(probe))


def present_in(chunks: list[dict], kind: str, probe) -> bool:
    return any(_chunk_has(c.get("content") or "", kind, probe) for c in chunks)


# --- target manual (servabilidad) -------------------------------------------
_DOC_TOKEN = re.compile(r"[A-Za-z0-9]{2,}(?:[-_][A-Za-z0-9]+)*")


def doc_tokens(*texts: str) -> list[str]:
    """Tokens identificadores de documento (contienen digito, len>=5)."""
    toks: list[str] = []
    seen: set[str] = set()
    for t in texts:
        if not t:
            continue
        # corta parentesis y extensiones
        t = re.sub(r"\([^)]*\)", " ", t)
        for m in _DOC_TOKEN.findall(t):
            if len(m) >= 5 and re.search(r"\d", m) and m.lower() not in {"en54", "en-54"}:
                k = m.lower()
                if k not in seen:
                    seen.add(k)
                    toks.append(m)
    return toks


def _normid(s: str) -> str:
    return re.sub(r"[-_ .]", "", (s or "").lower())


def source_matches_target(source_file: str, targets: list[str]) -> bool:
    sf = _normid(source_file)
    for t in targets:
        nt = _normid(t)
        if len(nt) >= 5 and (nt in sf or sf in nt):
            return True
    return False


_HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def corpus_count_for_token(token: str) -> int:
    """Cuenta chunks en chunks_v2 cuyo source_file contiene el token (servabilidad)."""
    try:
        with httpx.Client(timeout=15.0) as c:
            r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                      headers={**_HEADERS, "Prefer": "count=exact", "Range": "0-0"},
                      params={"select": "id", "source_file": f"ilike.*{token}*"})
        cr = r.headers.get("content-range", "*/0")
        return int(cr.split("/")[-1]) if "/" in cr else 0
    except Exception:
        return -1


def target_servable(gold: dict) -> tuple[bool, dict]:
    prov = gold.get("_provenance") or {}
    fuente = prov.get("fuente", "")
    cits = " ".join(c.get("manual", "") for c in (gold.get("citations") or []))
    targets = doc_tokens(fuente, cits, " ".join(gold.get("pdfs_used") or []))
    counts = {}
    for t in targets[:6]:
        counts[t] = corpus_count_for_token(t)
    servable = any(v > 0 for v in counts.values())
    return servable, {"target_tokens": targets, "corpus_counts": counts}


def fetch_manual_chunks(tokens: list[str], limit: int = 600) -> list[dict]:
    """Trae TODOS los chunks de chunks_v2 cuyo source_file contiene alguno de los
    tokens del manual objetivo. Sirve para la servibilidad A NIVEL DE HECHO: si el
    anchor NO aparece en NINGUN chunk del manual, el dato se perdio en
    extraccion/chunking (#10), no es un mero ranking-miss (cierra el critico de GPT-5.5:
    'RETRIEVAL no prueba que el hecho este en el corpus, solo que el manual existe')."""
    out: list[dict] = []
    seen: set[str] = set()
    for t in tokens[:6]:
        try:
            with httpx.Client(timeout=20.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                          headers=_HEADERS,
                          params={"select": "id,content,source_file,page_number",
                                  "source_file": f"ilike.*{t}*", "limit": str(limit)})
            if r.status_code in (200, 206):
                for row in r.json():
                    if row.get("id") not in seen:
                        seen.add(row.get("id"))
                        out.append(row)
        except Exception:
            continue
    return out


# --- main --------------------------------------------------------------------
def classify(in_top5: bool, in_pool50: bool, in_manual_corpus: bool) -> str:
    if in_top5:
        return "SINTESIS"
    if in_pool50:
        return "RERANK-MISS"
    if in_manual_corpus:
        return "RETRIEVAL"   # servable a nivel de HECHO, el ranker no lo sube
    return "CORPUS-GAP"      # el anchor no esta en NINGUN chunk del manual -> extraccion/#10


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="incluir hp013 (PASS)")
    ap.add_argument("--qids", default="", help="csv de qids concretos")
    ap.add_argument("--dump", default="", help="qid: volcar contenido de chunks (validacion)")
    ap.add_argument("--grep", default="", help="con --dump: resaltar este substring (OCR-norm)")
    ap.add_argument("--target-models", action="store_true",
                    help="pasa target_models al reranker (replica el bot de Telegram, "
                         "no el harness test_bot_vs_gold). Default: como el A/B (sin).")
    ap.add_argument("--reranker", choices=["llm", "voyage"], default="llm",
                    help="reranker A/B (Track A): llm=prod actual | voyage=cross-encoder Voyage")
    args = ap.parse_args()

    def _rerank(query, pool, target_models=None):
        # A/B Track A: el cross-encoder Voyage NO toma target_models (la priorizacion
        # de modelo es guarda aguas arriba en el retriever, no del reranker).
        if args.reranker == "voyage":
            return rerank_chunks_voyage(query, pool, top_k=RERANK_K)
        return rerank_chunks(query, pool, top_k=RERANK_K, target_models=target_models)

    if args.dump:
        g = {x["qid"]: x for x in yaml.safe_load(GOLD.read_text(encoding="utf-8"))}[args.dump]
        pool = retrieve_chunks(g["question"], top_k=RETRIEVE_K)
        top5 = _rerank(g["question"], pool)
        top_ids = {id(c) for c in top5}
        needle = norm_ocr(args.grep) if args.grep else None
        print(f"DUMP {args.dump}: {g['question']}\n")
        for i, c in enumerate(pool):
            tag = "TOP5" if id(c) in top_ids else "pool"
            cont = c.get("content") or ""
            hit = "  <<HIT>>" if (needle and needle in norm_ocr(cont)) else ""
            print(f"[{i:2d}|{tag}] {c.get('source_file')} p{c.get('page_number')} "
                  f"sect='{(c.get('section_title') or '')[:50]}'{hit}")
            print("    " + " ".join(cont.split())[:400] + "\n")
        return 0

    assert CHUNKS_IS_V2, "CHUNKS_TABLE debe ser chunks_v2"
    assert not HYDE_ENABLED, "HYDE debe estar OFF"

    golds = {g["qid"]: g for g in yaml.safe_load(GOLD.read_text(encoding="utf-8"))}
    bvg = {r["qid"]: r for r in yaml.safe_load(BVG.read_text(encoding="utf-8"))}

    if args.qids:
        qids = [q.strip() for q in args.qids.split(",") if q.strip()]
    else:
        qids = [q for q in sorted(golds) if args.all or q not in STABLE_PASS]

    variant = ("tgtmodels" if args.target_models else "noTgt") + f"_{args.reranker}"
    out_path = OUT.with_name(f"dec003_retrieval_funnel_{variant}.yaml")
    print(f"chunks_v2 | HyDE OFF | retrieve={RETRIEVE_K} rerank={RERANK_K} | reranker={args.reranker} | "
          f"rerank target_models={'SI (replica Telegram)' if args.target_models else 'NO (como A/B)'} | "
          f"{len(qids)} preguntas\n")

    results = []
    for qid in qids:
        g = golds[qid]
        q = g["question"]
        models = extract_product_models(q)
        pool = retrieve_chunks(q, top_k=RETRIEVE_K)
        top5 = _rerank(q, pool, target_models=models if args.target_models else None)

        pool_src = [c.get("source_file") for c in pool]
        top_src = [c.get("source_file") for c in top5]

        servable, srv = target_servable(g)
        targets = srv["target_tokens"]
        # Servibilidad A NIVEL DE HECHO (cierra critico GPT-5.5): chunks del manual objetivo.
        # Fallback a las fuentes recuperadas si no hay tokens (hp010: nombres DXc descriptivos).
        fetch_tokens = targets or sorted({s for s in pool_src if s})
        manual_chunks = fetch_manual_chunks(fetch_tokens)
        tgt_in_pool = any(source_matches_target(s or "", targets) for s in pool_src)
        tgt_in_top5 = any(source_matches_target(s or "", targets) for s in top_src)

        facts_out = []
        buckets = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
        buckets_fuerte = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
        for f in g.get("atomic_facts") or []:
            if f.get("tipo") != "core":
                continue
            if f.get("estado") != "presente":
                continue  # ausente-probado = legitimamente no en corpus (admit)
            kind, probe, strength = fact_probe(f.get("valor", ""), f.get("texto", ""))
            in_top5 = present_in(top5, kind, probe)
            in_pool = present_in(pool, kind, probe)
            in_corpus = in_pool or present_in(manual_chunks, kind, probe)
            bucket = classify(in_top5, in_pool, in_corpus)
            buckets[bucket] += 1
            if strength == "fuerte":
                buckets_fuerte[bucket] += 1
            facts_out.append({
                "valor": f.get("valor"),
                "probe": sorted(probe) if kind == "anchors" else f"~{probe}",
                "strength": strength,
                "in_top5": in_top5,
                "in_pool50": in_pool,
                "in_manual_corpus": in_corpus,
                "bucket": bucket,
            })

        bvg_row = bvg.get(qid, {})
        rec = {
            "qid": qid,
            "veredicto_B": bvg_row.get("veredicto"),
            "conducta_esperada": g.get("conducta_esperada"),
            "conducta_bot_B": bvg_row.get("conducta_bot"),
            "n_core_presente": len(facts_out),
            "buckets": buckets,
            "buckets_fuerte": buckets_fuerte,
            "target_servable": servable,
            "target_in_pool50": tgt_in_pool,
            "target_in_top5": tgt_in_top5,
            "target_tokens": targets,
            "corpus_counts": srv["corpus_counts"],
            "top5_sources": top_src,
            "pool50_sources": pool_src,
            "facts": facts_out,
        }
        results.append(rec)

        b = buckets
        flag = "" if (tgt_in_top5 or not facts_out) else ("  <<TARGET NO EN TOP5" + ("" if tgt_in_pool else " NI POOL50") + ">>")
        print(f"=== {qid} [{rec['veredicto_B']}] esp={rec['conducta_esperada']} "
              f"-> bot={rec['conducta_bot_B']} ===")
        print(f"  core-presente={len(facts_out)} | SINTESIS={b['SINTESIS']} "
              f"RERANK-MISS={b['RERANK-MISS']} RETRIEVAL={b['RETRIEVAL']} CORPUS-GAP={b['CORPUS-GAP']}")
        print(f"  target servible={servable} en_pool50={tgt_in_pool} en_top5={tgt_in_top5}{flag}")
        print(f"  top5_src={sorted(set(s for s in top_src if s))}")
        print()

    out_path.write_text(yaml.safe_dump(results, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # Resumen agregado
    print("=" * 70)
    agg = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
    for r in results:
        for k, v in r["buckets"].items():
            agg[k] += v
    aggf = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
    for r in results:
        for k, v in r["buckets_fuerte"].items():
            aggf[k] += v
    print(f"HECHOS CORE-PRESENTE por cuello (todos):   {agg}")
    print(f"HECHOS CORE-PRESENTE por cuello (FUERTES): {aggf}")
    print("\nPor pregunta [fuertes: top5/rerank/retr/gap] + manual objetivo:")
    for r in results:
        bf = r["buckets_fuerte"]
        tag = "TARGET-MANUAL-MISS" if not r["target_in_pool50"] else (
            "target-en-pool-no-top5" if not r["target_in_top5"] else "")
        print(f"  {r['qid']} [{r['veredicto_B']}] esp={r['conducta_esperada']}: "
              f"{bf['SINTESIS']}/{bf['RERANK-MISS']}/{bf['RETRIEVAL']}/{bf['CORPUS-GAP']}  {tag}")
    print(f"\nDetalle: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
