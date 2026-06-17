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
import datetime
import re
import subprocess
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
sys.path.insert(0, str(ROOT / "scripts"))  # audit_locator hace `from strict_match import ...` (bare)

from src.config import CHUNKS_IS_V2, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.retriever import retrieve_chunks, extract_product_models  # noqa: E402
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402
from src.rag.hyde import HYDE_ENABLED  # noqa: E402
from scripts.strict_match import norm_ocr, distinctive, anchor_present, chunk_has_quote_strict  # noqa: E402
# s81/DEC-061: el AUDIT usa el predicado limpio de audit_locator (fact_match_score). Las funciones
# LEGACY (fact_probe/_chunk_has/present_in con el matcher viejo) se conservan abajo SOLO para
# bvg_kmajority.sufficiency_for (su fix es separado, fuera de scope de DEC-061 que arregla ESTE funnel).
from scripts.audit_locator import fact_match_score, measurable, SCORE_FLOOR  # noqa: E402

GOLD = ROOT / "evals" / "gold_answers_v1.yaml"  # lee directo + exclude_heldout (embargo; TECH_DEBT #42 cerrado s57)
# s81/DEC-061(iv): veredictos canónicos k5 (los 30 dev NO-PASS) — antes _s45 (17 golds, desfasado).
# Define el UNIVERSO del audit (NO-PASS) + anota veredicto/conducta_bot por gold.
BVG = ROOT / "evals" / "bot_vs_gold_results_k5.yaml"
OUT = ROOT / "evals" / "dec003_retrieval_funnel.yaml"

RETRIEVE_K = 50   # s45: pool-50 (retrieve-wide RETRIEVAL_TOP_K=50, shipped s44). Antes 15
                  # = medía un pipeline que ya no existe (bug cazado por el dúo s45).
RERANK_K = 5
RERANK_RUNS = 1   # s81/FIX B (DEC-061(iii) + dúo r3): el reranker de PROD es temp=0 → DETERMINISTA
                  # (jitter nulo verificado, dúo r3) → K=1 basta. La decisión PRIMARIA (in-pool) es
                  # rerank-INDEPENDIENTE igualmente. Configurable si aparece jitter (>1 → re-ver flags top5).

# s81/FIX C (DEC-061(iv)): el universo del audit = dev NO-PASS de la corrida k5 (BVG). PASS excluido.
NO_PASS = {"PARCIAL", "FALLO"}


def _git_commit() -> str | None:
    """SHA corto del commit actual (reproducibilidad del gate); None si falla."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


# --- predicado LEGACY (solo bvg_kmajority.sufficiency_for; pre-existente, NO tocar comportamiento) ---
# DEC-061 arregla el AUDIT (este funnel, abajo), NO el diagnóstico sufficiency_for de bvg_kmajority.
# Para no romper ese consumidor, se conserva el matcher viejo bajo sus nombres originales.
_GENERIC = {"1 a", "1a", "2", "3", "0", "00", "no", "si"}  # valores demasiado debiles


def fact_probe(valor: str, texto: str) -> tuple[str, object, str]:
    """[LEGACY bvg_kmajority] (kind, probe, strength). El audit s81 NO usa esto (usa fact_match_score)."""
    v = (valor or "").strip()
    if v:
        anchors = distinctive(v)
        if anchors:
            has_model = any(re.search(r"[a-z]", a) for a in anchors)
            has_long_num = any(len(re.sub(r"\D", "", a)) >= 3 for a in anchors)
            strength = "fuerte" if (has_model or has_long_num or len(anchors) >= 2) else "debil"
            return "anchors", anchors, strength
        nv = norm_ocr(v)
        strong_code = (bool(re.search(r"\d", nv)) and bool(re.search(r"[a-z]", nv))
                       and len(re.sub(r"[^a-z0-9]", "", nv)) >= 3 and nv not in _GENERIC)
        strength = "fuerte" if strong_code else "debil"
        return "quote", v, strength
    return "quote", texto or "", "debil"


def _chunk_has(content: str, kind: str, probe) -> bool:
    """[LEGACY bvg_kmajority] matcher viejo (chunk_has_quote_strict en el path quote)."""
    if kind == "anchors":
        nc = norm_ocr(content or "")
        return all(anchor_present(a, nc) for a in probe)
    return chunk_has_quote_strict(content or "", str(probe))


def present_in(chunks: list[dict], kind: str, probe) -> bool:
    """[LEGACY bvg_kmajority]"""
    return any(_chunk_has(c.get("content") or "", kind, probe) for c in chunks)


# --- predicado del AUDIT (s81, DEC-061: limpio, portado de audit_locator) ----------------------
# Matchea el ENUNCIADO (texto) vía audit_locator.fact_match_score; la CONFIANZA del bucket sale del
# SCORE del match (no a priori). Hechos no-medibles los segrega el caller (measurable) ANTES.


def present_fact(chunks: list[dict], valor: str, texto: str, targets=None):
    """Devuelve (present: bool, best_score: float, sources: set). EXIGE el valor (fact_match_score).
    best_score = mejor score sobre TODOS los chunks atados (no solo ≥FLOOR) → cuantifica near-misses:
    un CORPUS-GAP con best=0.54 es casi-match (riesgo FN, crít dúo r3) vs best=0.1 (ausencia real).
    Source-tie FAIL-OPEN: si `targets`, solo cuenta chunks cuya fuente machea el gold (mata el FP
    'chunk de OTRO manual'); si targets vacío, NO ata (fuentes descriptivas hp010)."""
    tie = bool(targets)
    best, srcs = 0.0, set()
    for c in chunks:
        if tie and not source_matches_target(c.get("source_file") or "", targets):
            continue
        s = fact_match_score(valor, texto, c.get("content") or "")
        if s is None:
            continue
        best = max(best, s)
        if s >= SCORE_FLOOR:
            srcs.add(c.get("source_file") or "")
    return (best >= SCORE_FLOOR), best, srcs


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
    # citations puede ser lista de dicts {manual,quote} (esquema v2) o de strings (golds legacy) — robusto a ambos.
    cits = " ".join((c.get("manual", "") if isinstance(c, dict) else str(c))
                    for c in (gold.get("citations") or []))
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
    ap.add_argument("--all", action="store_true", help="incluir también los PASS (default: solo NO-PASS k5)")
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
        from scripts.gold_store import exclude_heldout  # noqa: E402
        by_qid = {x["qid"]: x for x in exclude_heldout(yaml.safe_load(GOLD.read_text(encoding="utf-8")))}
        if args.dump not in by_qid:
            sys.exit(f"{args.dump}: no existe o está EMBARGADO (held-out — el diagnóstico de "
                     "retrieval sobre held-out lo expone; RULER §8 / TECH_DEBT #42)")
        g = by_qid[args.dump]
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

    from scripts.gold_store import exclude_heldout  # noqa: E402
    golds = {g["qid"]: g for g in exclude_heldout(yaml.safe_load(GOLD.read_text(encoding="utf-8")))}
    bvg = {r["qid"]: r for r in yaml.safe_load(BVG.read_text(encoding="utf-8"))}

    if args.qids:
        qids = [q.strip() for q in args.qids.split(",") if q.strip()]
    else:
        qids = [q for q in sorted(golds)
                if args.all or bvg.get(q, {}).get("veredicto") in NO_PASS]

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
        # FIX B (dúo r3): el reranker de PROD es temp=0 → determinista (jitter nulo verificado); K=1.
        # La membresía del pool-50 es estable intra-corrida → la decisión PRIMARIA (in-pool) no usa el rerank.
        top5_runs = [_rerank(q, pool, target_models=models if args.target_models else None)
                     for _ in range(RERANK_RUNS)]
        top5 = top5_runs[0]  # K=1 → el único run; usado consistentemente para facts + flags de fuente

        pool_src = [c.get("source_file") for c in pool]
        top_src = [c.get("source_file") for c in top5]

        servable, srv = target_servable(g)
        targets = srv["target_tokens"]
        # Fuente PRIMARIA (solo _provenance.fuente) vs targets (fuente + citations + pdfs_used, que
        # incluyen CORROBORADORES). Distinguirlas expone el FP 'corroborador enmascara primario'
        # (crít dúo r2: hp018 recupera MI-310 corroborador, NO MI-530 primario, y el agregado mentía).
        primary_tokens = doc_tokens((g.get("_provenance") or {}).get("fuente", ""))
        # Servibilidad A NIVEL DE HECHO (cierra critico GPT-5.5): chunks del manual objetivo.
        # Fallback a las fuentes recuperadas si no hay tokens (hp010: nombres DXc descriptivos).
        fetch_tokens = targets or sorted({s for s in pool_src if s})
        manual_chunks = fetch_manual_chunks(fetch_tokens)
        tgt_in_pool = any(source_matches_target(s or "", targets) for s in pool_src)
        tgt_in_top5 = any(source_matches_target(s or "", targets) for s in top_src)
        primary_in_pool = bool(primary_tokens) and any(source_matches_target(s or "", primary_tokens) for s in pool_src)
        primary_in_top5 = bool(primary_tokens) and any(source_matches_target(s or "", primary_tokens) for s in top_src)

        facts_out = []
        buckets = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
        buckets_firme = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
        n_unmeasurable = n_rerank_unstable = n_borderline = 0
        for f in g.get("atomic_facts") or []:
            if f.get("tipo") != "core" or f.get("estado") != "presente":
                continue  # ausente-probado = legitimamente no en corpus (admit)
            valor = f.get("valor", "")
            texto = (f.get("texto") or "").strip()
            if not measurable(valor, texto):  # valor no-verificable léxicamente → NO bucketizar (ni falso CORPUS-GAP ni falso SINTESIS)
                n_unmeasurable += 1
                facts_out.append({"valor": valor, "medible": False, "bucket": None})
                continue
            votes = [present_fact(t5, valor, texto, targets)[0] for t5 in top5_runs]
            n_yes = sum(1 for v in votes if v)
            in_top5 = n_yes > RERANK_RUNS / 2
            unstable = 0 < n_yes < RERANK_RUNS  # K=1 → siempre False (reranker temp=0)
            n_rerank_unstable += int(unstable)
            in_pool, pool_score, _ = present_fact(pool, valor, texto, targets)
            corpus_present, corpus_score, _ = present_fact(manual_chunks, valor, texto, None)  # ya pre-filtrado; sin tie (evita FN, dúo r2)
            in_corpus = in_pool or corpus_present
            bucket = classify(in_top5, in_pool, in_corpus)
            best_score = max(pool_score, corpus_score)
            # CONFIANZA del bucket = SCORE del match (no a priori). borderline = cerca del FLOOR
            # (el bucket podría flipear). CORPUS-GAP no es borderline-por-score (su riesgo es FN, aparte).
            borderline = bucket != "CORPUS-GAP" and SCORE_FLOOR <= best_score < 0.70
            buckets[bucket] += 1
            if not borderline:
                buckets_firme[bucket] += 1
            n_borderline += int(borderline)
            facts_out.append({
                "valor": valor, "medible": True, "bucket": bucket,
                "in_top5": in_top5, "in_pool50": in_pool, "in_manual_corpus": in_corpus,
                "best_score": round(best_score, 3), "borderline": borderline,
                "rerank_unstable": unstable,
            })

        bvg_row = bvg.get(qid, {})
        n_medible = len(facts_out) - n_unmeasurable
        primary_not_retrieved = bool(primary_tokens) and not primary_in_pool
        rec = {
            "qid": qid,
            "veredicto_k5": bvg_row.get("veredicto"),
            "conducta_esperada": g.get("conducta_esperada"),
            "conducta_bot_k5": bvg_row.get("conducta_bot"),
            "n_core_medible": n_medible,
            "n_no_medible": n_unmeasurable,
            "n_borderline": n_borderline,
            "n_rerank_unstable": n_rerank_unstable,
            "buckets": buckets,
            "buckets_firme": buckets_firme,
            "target_servable": servable,
            "target_in_pool50": tgt_in_pool,
            "target_in_top5": tgt_in_top5,
            "primary_in_pool50": primary_in_pool,
            "primary_in_top5": primary_in_top5,
            "primary_not_retrieved": primary_not_retrieved,
            "target_tokens": targets,
            "primary_tokens": primary_tokens,
            "corpus_counts": srv["corpus_counts"],
            "top5_sources": top_src,
            "pool50_sources": pool_src,
            "facts": facts_out,
        }
        results.append(rec)

        b = buckets
        tags = []
        if primary_not_retrieved:
            tags.append("PRIMARIO-NO-RECUPERADO")
        if n_medible and not tgt_in_top5:
            tags.append("TARGET-NO-TOP5" + ("" if tgt_in_pool else "-NI-POOL"))
        flag = ("  <<" + " | ".join(tags) + ">>") if tags else ""
        print(f"=== {qid} [{rec['veredicto_k5']}] esp={rec['conducta_esperada']} "
              f"-> bot={rec['conducta_bot_k5']} ===")
        print(f"  core-medible={n_medible} (+{n_unmeasurable} no-medible) | SINTESIS={b['SINTESIS']} "
              f"RERANK-MISS={b['RERANK-MISS']} RETRIEVAL={b['RETRIEVAL']} CORPUS-GAP={b['CORPUS-GAP']}"
              f" | borderline={n_borderline} rerank-inest={n_rerank_unstable}")
        print(f"  servible={servable} | target pool={tgt_in_pool} top5={tgt_in_top5}"
              f" | PRIMARIO pool={primary_in_pool} top5={primary_in_top5}{flag}")
        print(f"  top5_src={sorted(set(s for s in top_src if s))}")
        print()

    # F0#1 (DEC-019): estampar la config EN el output → el gate es reproducible/auditable.
    meta = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "chunks_table": os.environ.get("CHUNKS_TABLE"),
        "hyde_enabled": HYDE_ENABLED,
        "retrieve_k": RETRIEVE_K,
        "rerank_k": RERANK_K,
        "rerank_runs": RERANK_RUNS,
        "reranker": args.reranker,
        "rerank_target_models": bool(args.target_models),
        "gold_file": GOLD.name,
        "bvg_file": BVG.name,
        "matcher": "audit_locator.fact_match_score (citation_score + anchor_present; s81/DEC-061)",
        "freeze_note": "PARCIAL (DEC-021§F): estampados chunks_table/hyde/retrieve_k/rerank_k/rerank_runs/git_commit. "
                       "NO estampados: corpus fingerprint, versión embeddings/retriever, orden-de-empates → "
                       "reproducibilidad LIMITADA. La membresía del pool es estable intra-corrida (dúo #9 symdiff=∅); "
                       "el orden de empates jitterea pero no afecta la decisión primaria (in-pool).",
        "n_qids": len(qids),
        "qids": qids,
    }
    out_path.write_text(yaml.safe_dump({"meta": meta, "results": results},
                                       allow_unicode=True, sort_keys=False), encoding="utf-8")

    # Resumen agregado — la DECISIÓN se lee del histograma FIRME (matches NO-borderline); banda =
    # [FIRME, ALL] = sensibilidad a matches cerca del FLOOR. Las demás incertidumbres van APARTE
    # (no-medibles, CORPUS-GAP=riesgo FN, rerank-inestables, PRIMARIO-no-recuperado).
    print("=" * 70)
    agg = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
    aggf = {"SINTESIS": 0, "RERANK-MISS": 0, "RETRIEVAL": 0, "CORPUS-GAP": 0}
    for r in results:
        for k in agg:
            agg[k] += r["buckets"][k]
            aggf[k] += r["buckets_firme"][k]
    tot_no_medible = sum(r["n_no_medible"] for r in results)
    tot_unstable = sum(r["n_rerank_unstable"] for r in results)
    tot_border = sum(r["n_borderline"] for r in results)
    prim_miss = [r["qid"] for r in results if r["primary_not_retrieved"]]
    print(f"HISTOGRAMA por cuello — FIRME (decisor):     {aggf}")
    print(f"                        ALL (cota superior): {agg}")
    print(f"  banda (FIRME→ALL) = {tot_border} matches borderline (score en [{SCORE_FLOOR}, 0.70)).")
    print(f"  incertidumbre APARTE: {tot_no_medible} no-medibles léxicamente | "
          f"{agg['CORPUS-GAP']} CORPUS-GAP (riesgo FN es-en/OCR → verificar a mano) | "
          f"{tot_unstable} rerank-inestables.")
    print(f"  PRIMARIO-NO-RECUPERADO ({len(prim_miss)}/{len(results)}): {prim_miss}")
    print("\nPor pregunta [FIRME: top5/rerank/retr/gap] | prim_pool | flags:")
    for r in results:
        bf = r["buckets_firme"]
        tags = []
        if r["primary_not_retrieved"]:
            tags.append("PRIM-NO-POOL")
        if not r["target_in_top5"]:
            tags.append("tgt-no-top5")
        print(f"  {r['qid']} [{r['veredicto_k5']}] esp={r['conducta_esperada']}: "
              f"{bf['SINTESIS']}/{bf['RERANK-MISS']}/{bf['RETRIEVAL']}/{bf['CORPUS-GAP']} "
              f"| prim_pool={r['primary_in_pool50']} | {' '.join(tags)}")
    print(f"\nDetalle: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
