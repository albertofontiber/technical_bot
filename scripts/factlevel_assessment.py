#!/usr/bin/env python3
"""factlevel_assessment.py (s100) — assessment a nivel-hecho ESTANDARIZADO (spec v3, dúo ×3 spec + ×2 build).

UN entry-point canónico que unifica los instrumentos ad-hoc (s85/s87/s88/s99) que bit-roteaban.
Clasifica cada hecho CORE de cada gold-dev en UNA clase terminal del funnel de PIPELINE.

MIDE LA RUTA EVAL-HARNESS (sin target_models, strict=True, available_models=None) — decisión Alberto
s100: paridad con bvg / DEC-075 / ancho DEC-092b y TODAS las mediciones previas, para re-derivar el
plateau CADUCO de DEC-075 de forma COMPARABLE. La ruta Telegram (target_models + available_models) es
una medición SEPARADA con su propio baseline. Flags = los de la DEMO (Railway). NO es "pipeline
shippeado a secas": es el harness-con-flags-de-demo.

Taxonomía v3 (5 clases terminales + OK; TODOS los facts clasificados), FAMILY-AWARE (fix dúo build #3):
  corpus-gap    — el hecho NO existe servible en el corpus (default = FN-MÍO, anti-FN reforzado)
  retrieval-miss— servible en corpus pero NINGÚN chunk SAME-FAMILY en el pool-50   (sub: within-doc/es-en/model-filter/cross-fam)
  rerank-miss   — chunk-soporte same-family en pool-50 pero NO sobrevive al top-k  (sub: pos-buried/lexical)
  synthesis-miss— servido (post-threshold) pero la respuesta NO lo transmite (sub-motivo LLM CON chunks
                  servidos: omitted/hedged/partial/contradicted/threshold-drop) + STABILITY (rep×2, flip vs structural)
  OK            — servido + transmitido
`lexically_anchorable` = FLAG por-hecho (fix v3, NO gate): los no-anclables (prosa/periodicidades) se clasifican
igual vía juez SEMÁNTICO; solo enruta el corpus-check (léxico vs semántico). meta-ref (valor=puntero: apéndice/
tabla) = único fuera del histograma.

FAMILY-AWARE (fix #3): un chunk-soporte SOLO acredita si es de la MISMA FAMILIA de producto que el gold
(via product_model, reusa retrieval_miss_famtie) — sin esto, un valor que coincide por casualidad en OTRO
producto acredita mal (bug hp018, DEC-075 by_target).

Anti-bit-rot: regenerar SIEMPRE (no cache, no seed DEF). Join hecho↔texto por clave (qid#idx:valor) — ESTABLE
para el orden actual de core_facts() (NO una fact-id global; si core_facts reordena, cambia — declarado).
Freeze-contract leído del ENTORNO, RE-AFIRMADO tras los imports (los módulos legacy hacen load_dotenv override).

Modos:
  python scripts/factlevel_assessment.py smoke [--qids hp007,cat007]   # subset + estimación de coste
  python scripts/factlevel_assessment.py full                          # 39 dev
Salida: evals/s100_factlevel_<mode>.yaml (+ .partial.jsonl resumible) + manifest embebido.
"""
from __future__ import annotations
import os
# ── Freeze-contract: EXPORTAR el flag-set de la DEMO ANTES de importar el pipeline ──
# (confirmado s100 con Alberto vía Railway Variables; valores DEC-sourced "verificado en producción").
DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "ADD",
    "LLM_MAX_TOKENS": "3500",
    "RERANK_TOP_K": "10",
    # defaults de código (ausentes de Railway) — explícitos para que el manifest no mienta:
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800",
    "HYDE_ENABLED": "false",
}


def _assert_demo_flags():
    """Re-afirma los DEMO_FLAGS. CRÍTICO (fix dúo build #2): los módulos legacy que importamos
    (retrieval_miss_judge/synthesis_miss_judge/audit_retrieval_funnel/retrieval_miss_famtie) hacen
    `load_dotenv(override=True)` en import-time → pisan estos flags si el .env local los define.
    ENUNCIADOS/IDENTITY se leen en RUNTIME (retriever.py:1090, catalog_resolver.py:61) → hay que
    re-afirmar DESPUÉS de todos los imports, o el pipeline medido diverge del de la demo."""
    for k, v in DEMO_FLAGS.items():
        os.environ[k] = v


_assert_demo_flags()   # 1º set (antes de importar el pipeline → config.py lee getenv en import)

import sys, json, time, hashlib, argparse, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import httpx
import yaml
from openai import OpenAI
from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=False)   # NO pisar los DEMO_FLAGS
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

from src.rag.retriever import retrieve_chunks
from src.rag.reranker import rerank
from src.rag.generator import generate_answer, RELEVANCE_THRESHOLD
from src.config import (RETRIEVAL_TOP_K, RERANK_TOP_K, LLM_MODEL, LLM_MAX_TOKENS,
                        RERANKER_BACKEND, MERGE_STRATEGY, RERANK_PREVIEW_CHARS, CHUNKS_TABLE)
from scripts.retrieval_miss_judge import (
    judge_fact, supported_ids, core_facts, load_dev,
    THRESH_FIRM, THRESH_BAND, CONTENT_CHARS,
    JUDGE_SYS as SUPPORT_SYS, JUDGE_USER as SUPPORT_USER,
)
from scripts.synthesis_miss_judge import (
    judge_conveyed, JUDGE_SYS as CONVEY_SYS, JUDGE_USER as CONVEY_USER,
)
from scripts.audit_retrieval_funnel import (
    target_servable, fetch_manual_chunks, source_matches_target, doc_tokens, present_fact,
)
from scripts.audit_locator import measurable, fact_match_score, SCORE_FLOOR
from scripts.retrieval_miss_famtie import gold_family, fam_norm, _pm_by_ids, _is_meta_ref

_assert_demo_flags()   # 2º set: RE-AFIRMAR tras los imports (fix #2 — los legacy hicieron override=True)

# Sanity: el pipeline importado DEBE ver el flag-set de la demo, no el default local (fix dúo build2 #1).
# Assertar TODOS los load-bearing (no solo RERANK_TOP_K): un load_dotenv legacy pudo pisar constantes import-time.
assert RERANK_TOP_K == 10, f"RERANK_TOP_K={RERANK_TOP_K} ≠ demo(10) — pipeline fantasma"
assert LLM_MAX_TOKENS == 3500, f"LLM_MAX_TOKENS={LLM_MAX_TOKENS} ≠ demo(3500) — pipeline fantasma"
assert CHUNKS_TABLE == "chunks_v2", f"CHUNKS_TABLE={CHUNKS_TABLE} ≠ demo(chunks_v2) — pipeline fantasma"
# Flags de generación que alteran el prompt en runtime → paridad bvg exige OFF (fix dúo build2 #2).
assert not os.getenv("GENERATOR_INCLUDE_CONTEXT"), "GENERATOR_INCLUDE_CONTEXT ON rompe paridad bvg/DEC-075"
assert not os.getenv("GENERATOR_PROMPT_VARIANT"), "GENERATOR_PROMPT_VARIANT set rompe paridad bvg/DEC-075"

JUDGE_MODEL = "gpt-5.5"
K = 5                       # K-mayoría (Protocolo 4 — nunca single-pass)
K_STAB = 3                  # reps de estabilidad (gated a synth-miss → K menor para acotar coste)
OUT_DIR = ROOT / "evals"
SUPABASE_URL = os.environ["SUPABASE_URL"]
_HEADERS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
            "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
_sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

# Subset de smoke por DEFAULT: 1 gold por clase-de-fallo esperada (barato, valida juez+plomería+coste).
SMOKE_QIDS = ["hp007", "cat007", "hp018", "hp001", "cat005"]

# ── sub-motivo de SÍNTESIS: juez NUEVO que VE los chunks servidos CON IDs (decisión Alberto s100) ──
SUBMOTIVO_SYS = (
    "Eres un evaluador EXPERTO en manuales técnicos de PCI. Un HECHO (un VALOR en una RELACIÓN) llegó "
    "al generador (está en los FRAGMENTOS SERVIDOS) pero la RESPUESTA no lo transmite bien. Diagnostica "
    "POR QUÉ, con rigor literal. Idiomas ES/EN mezclados y OCR imperfecto son normales."
)
SUBMOTIVO_USER = (
    "HECHO: VALOR «{valor}» EN la relación «{texto}».\n\n"
    "FRAGMENTOS SERVIDOS al generador (lo que PUDO ver, cada uno con su ID):\n<<<\n{served}\n>>>\n\n"
    "RESPUESTA del asistente:\n<<<\n{answer}\n>>>\n\n"
    "Clasifica el fallo en UNA categoría:\n"
    "  · omitted     — el valor está COMPLETO en los fragmentos servidos; la respuesta simplemente no lo menciona.\n"
    "  · hedged      — el valor está en los fragmentos; la respuesta se escuda ('el manual no especifica…') pese a tenerlo.\n"
    "  · partial     — los fragmentos servidos NO contienen el valor completo (incompletos para este hecho); "
    "la respuesta no puede transmitirlo porque el dato no llegó entero.\n"
    "  · contradicted— la respuesta afirma un valor DISTINTO / invertido al del hecho.\n"
    'Responde EXCLUSIVAMENTE JSON: {{"submotivo": "omitted|hedged|partial|contradicted", "por_que": "<breve>"}}.'
)
# Presupuesto por-chunk para que TODOS los servidos (top-10) quepan con IDs sin cortar el chunk-soporte:
SUBMOTIVO_CHUNK_CHARS = 3200


def _submotivo_once(valor: str, texto: str, served: str, answer: str) -> str | None:
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for attempt in range(4):
        try:
            resp = oai.chat.completions.create(
                model=JUDGE_MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SUBMOTIVO_SYS},
                          {"role": "user", "content": SUBMOTIVO_USER.format(
                              valor=valor, texto=(texto or "")[:400],
                              served=served, answer=(answer or "")[:6000])}],
            )
            out = json.loads(resp.choices[0].message.content.strip())
            sm = str(out.get("submotivo", "")).strip()
            return sm if sm in {"omitted", "hedged", "partial", "contradicted"} else None
        except Exception:
            time.sleep(2 ** attempt)
    return None


def submotivo_synthesis(valor: str, texto: str, served_chunks: list[dict], answer: str,
                        support_ids: set[str], workers: int = 5) -> dict:
    """K votos → sub-motivo mayoritario. served_chunks = POST-threshold (fresh). Los chunks-soporte
    (support_ids ∩ servidos) van PRIMERO y a contenido más largo → el juez ve el dato para distinguir
    hedged (valor presente, respuesta se escuda) de partial (valor NO llega entero)."""
    ordered = sorted(served_chunks, key=lambda c: c.get("id") not in support_ids)  # soporte primero
    served = "\n\n".join(f"[ID {c.get('id')}]\n{(c.get('content') or '')[:SUBMOTIVO_CHUNK_CHARS]}"
                         for c in ordered)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = [f.result() for f in [pool.submit(_submotivo_once, valor, texto, served, answer)
                                      for _ in range(K)]]
    tally: dict[str, int] = {}
    for v in votes:
        if v:
            tally[v] = tally.get(v, 0) + 1
    if not tally:
        return {"submotivo": "unknown", "votes": {}, "n_fail": K}
    return {"submotivo": max(tally, key=tally.get), "votes": tally, "n_fail": votes.count(None)}


# ── sub-motivos ESTRUCTURALES (baratos, sin LLM) para retrieval/rerank/corpus-gap ──
_ESEN_UNITS = (" v", " a ", " ma", "seg", "min", " hz", " db", "ohm", "kohm")  # unidades es-en frágiles


def _es_en_signal(valor: str) -> bool:
    v = f"{(valor or '').lower()} "
    return any(u in v for u in _ESEN_UNITS)


def submotivo_retrieval(valor: str, texto: str, family_resolved: bool) -> str:
    """within-doc (aguja/coseno sub-suelo) / es-en (valor traducible) / model-filter (identidad, si el
    gold no resolvió familia = zona de identidad — bajo policy=ADD un acierto es coincidencia-de-valor)."""
    if not family_resolved:
        return "model-filter"
    if _es_en_signal(valor):
        return "es-en?"
    return "within-doc"


def submotivo_rerank(best_pool_rank: int, top_k: int) -> str:
    return "pos-buried" if best_pool_rank >= top_k else "lexical-distractor"


def corpus_gap_suspect(best_corpus_score: float, valor: str, sem_truncated: bool = False) -> dict:
    """DEFAULT = FN-MÍO (feedback_corpus_gap, cazado 3×). Marca la sospecha ANTES de aterrizar.
    fix #3: si el corpus-check semántico se truncó (manual > SEM_CORPUS_BOUND), NUNCA aterriza limpio."""
    near_miss = best_corpus_score is not None and best_corpus_score >= (SCORE_FLOOR - 0.15)
    es_en = _es_en_signal(valor)
    return {"suspect_fn_mine": bool(near_miss or es_en or sem_truncated), "best_corpus_score": best_corpus_score,
            "near_miss": bool(near_miss), "es_en_translatable": bool(es_en), "sem_bound_truncated": bool(sem_truncated),
            "nota": "corpus-gap=default FN-MÍO; revisar es-en/OCR/bare/tie + manual-completo antes de aceptar (feedback_corpus_gap)"}


# ── pipeline FIEL a la RUTA HARNESS (paridad bvg): sin target_models, strict, available_models=None ──
def run_pipeline(question: str) -> dict:
    pool = retrieve_chunks(question, top_k=RETRIEVAL_TOP_K)
    topk = rerank(question, pool, top_k=RERANK_TOP_K, strict=True)   # SIN target_models (paridad harness)
    served = [c for c in topk if c.get("similarity", 0) >= RELEVANCE_THRESHOLD]  # lo que VE el generador
    res = generate_answer(question, topk)   # available_models=None (paridad harness, test_bot_vs_gold:107)
    return {"answer": res.get("answer", ""), "pool": pool, "topk": topk, "served": served,
            "topk_ids": [c.get("id") for c in topk], "served_ids": [c.get("id") for c in served],
            "pool_ids": [c.get("id") for c in pool]}


def gen_answer_only(question: str, topk: list[dict]) -> str:
    return generate_answer(question, topk).get("answer", "")


def pool_rank_of(supported: set[str], pool_ids: list[str]) -> int:
    ranks = [i for i, cid in enumerate(pool_ids) if cid in supported]
    return min(ranks) if ranks else 10**6


SEM_CORPUS_BOUND = 40   # chunks del manual a juzgar semánticamente (acotado por coste; subido de 24, fix #3)
def semantic_corpus_present(valor: str, texto: str, manual: list[dict], workers: int) -> tuple[bool, bool]:
    """Para facts NO-anclables-léxicamente que NO están en el pool: ¿el manual objetivo los sirve?
    Juez SEMÁNTICO acotado (present_fact léxico daría FN sobre prosa) → distingue corpus-gap real de
    retrieval-miss sin ceguera léxica (fix v3). Devuelve (present, truncated).
    Fix dúo build2 #3: `fetch_manual_chunks` NO ordena (rebanada arbitraria de DB) → ordenar por
    page_number para cobertura determinista desde el inicio del doc; marcar `truncated` cuando se corta
    (→ el corpus-gap semántico NUNCA aterriza como 'limpio' si no vimos el manual entero — feedback_corpus_gap)."""
    if not manual:
        return False, False
    ordered = sorted(manual, key=lambda c: (c.get("page_number") is None, c.get("page_number") or 0))
    truncated = len(ordered) > SEM_CORPUS_BOUND
    v = judge_fact(valor, texto, ordered[:SEM_CORPUS_BOUND], workers=workers)
    return bool(supported_ids(v, THRESH_FIRM)), truncated


def _pm_map(pool: list[dict]) -> dict:
    """product_model por id para el pool. Usa el campo del chunk si viene; si no, fetch por-id (famtie)."""
    pm = {c.get("id"): c.get("product_model") for c in pool if c.get("id")}
    missing = [cid for cid, v in pm.items() if v in (None, "")]
    if missing:
        pm.update(_pm_by_ids(missing))
    return pm


# ── núcleo: clasificar cada hecho CORE de un gold en su clase terminal (FAMILY-AWARE) ──
def measure_gold(gold: dict, workers: int = 6, do_submotivo: bool = True, do_stability: bool = True) -> dict:
    qid = gold["qid"]
    pipe = run_pipeline(gold["question"])
    served_ids = set(pipe["served_ids"]); topk_ids = set(pipe["topk_ids"])
    pm = _pm_map(pipe["pool"])
    # familia(s) de producto del gold (fix #3): un soporte solo cuenta si es SAME-FAMILY
    prov = gold.get("_provenance") or {}
    fuente = prov.get("fuente", "")
    servable, srv = target_servable(gold)
    targets = srv["target_tokens"]
    gfam = gold_family(doc_tokens(fuente), targets, fuente)
    family_resolved = bool(gfam)
    manual = fetch_manual_chunks(targets) if targets else []

    def same_family(cid: str) -> bool:
        if not family_resolved:       # no se pudo resolver familia → no se puede family-filtrar
            return True               # (fall-back marcado; family_resolved=False lo señala en el output)
        return fam_norm(pm.get(cid, "")) in gfam

    facts_out = []
    hist = {"OK": 0, "synthesis-miss": 0, "rerank-miss": 0, "retrieval-miss": 0,
            "corpus-gap": 0, "meta-ref": 0}
    synth_miss_refs = []   # para el pase de estabilidad (rep×2)
    n_non_anchorable = 0
    for idx, f in enumerate(core_facts(gold)):
        valor = f.get("valor", ""); texto = (f.get("texto") or "").strip()
        key = f"{qid}#{idx}:{valor}"
        if _is_meta_ref(valor):        # el valor es un puntero (apéndice/tabla), no un dato recuperable
            hist["meta-ref"] += 1
            facts_out.append({"key": key, "valor": valor, "clase": "meta-ref"})
            continue

        # fix v3: measurable() = FLAG (no gate). Los jueces SEMÁNTICOS (judge_fact/judge_conveyed)
        # clasifican TODOS los facts (prosa/periodicidades incl.) → comparabilidad con DEC-075.
        anchorable = measurable(valor, texto)
        n_non_anchorable += int(not anchorable)

        # SOPORTE regenerado SIEMPRE (anti-bit-rot) — juez SEMÁNTICO del hecho contra el pool-50 VIVO
        v_pool = judge_fact(valor, texto, pipe["pool"], workers=workers)
        sup = supported_ids(v_pool, THRESH_FIRM)
        sup_fam = {cid for cid in sup if same_family(cid)}      # FAMILY-AWARE (fix #3)
        reaches_gen = bool(sup_fam & served_ids)
        in_topk = bool(sup_fam & topk_ids)
        in_pool = bool(sup_fam)

        entry = {"key": key, "valor": valor, "texto": texto, "lexically_anchorable": anchorable,
                 "family_resolved": family_resolved, "n_support_fam": len(sup_fam),
                 "n_support_raw": len(sup), "reaches_gen": reaches_gen, "in_topk": in_topk, "in_pool": in_pool}

        if reaches_gen:
            conv = judge_conveyed(valor, texto, pipe["answer"], workers=workers)
            entry["conveyed_yes"] = conv["yes"]
            if conv["yes"] >= THRESH_FIRM:
                clase = "OK"
            else:
                clase = "synthesis-miss"
                entry["borderline"] = THRESH_BAND <= conv["yes"] < THRESH_FIRM
                if do_submotivo:
                    entry["submotivo"] = submotivo_synthesis(valor, texto, pipe["served"], pipe["answer"],
                                                             sup_fam & served_ids, workers=workers)
                synth_miss_refs.append(entry)
        elif in_topk:
            clase = "synthesis-miss"     # en top-k pero cayó por RELEVANCE_THRESHOLD (raro, fix H)
            entry["submotivo"] = {"submotivo": "threshold-drop", "nota": "en top-k pero <RELEVANCE_THRESHOLD"}
        elif in_pool:
            clase = "rerank-miss"
            entry["best_pool_rank"] = pool_rank_of(sup_fam, pipe["pool_ids"])
            entry["submotivo"] = submotivo_rerank(entry["best_pool_rank"], RERANK_TOP_K)
        elif sup:
            # servible en el pool pero SOLO cross-familia (sup_raw>0, sup_fam=0): coincidencia de valor
            # en OTRA familia (DEC-091b: '1 A' de ZXAE/ZXEE para ZXe). El dato EXISTE en el corpus → NO
            # es corpus-gap (evita el FN que feedback_corpus_gap avisa): es identidad/model-filter (DEC-074).
            clase = "retrieval-miss"
            entry["cross_family_only"] = True
            entry["best_pool_rank"] = pool_rank_of(sup, pipe["pool_ids"])
            entry["submotivo"] = "model-filter"
        else:
            # NI same-family NI cross-family en el pool → ¿servible en el manual objetivo?
            # anclable → check LÉXICO barato; no-anclable → juez SEMÁNTICO acotado+ordenado (fix v3/#3)
            sem_truncated = False
            if anchorable:
                corpus_present, corpus_score, _ = present_fact(manual, valor, texto, None) if manual else (False, 0.0, set())
            else:
                corpus_present, sem_truncated = semantic_corpus_present(valor, texto, manual, workers)
                corpus_score = None
            entry["corpus_check"] = "lexical" if anchorable else "semantic"
            if corpus_present:
                clase = "retrieval-miss"
                entry["best_corpus_score"] = round(corpus_score, 3) if corpus_score is not None else None
                entry["submotivo"] = submotivo_retrieval(valor, texto, family_resolved)
            else:
                clase = "corpus-gap"
                entry["corpus_gap"] = corpus_gap_suspect(corpus_score, valor, sem_truncated)

        entry["clase"] = clase
        hist[clase] += 1
        facts_out.append(entry)

    # ── STABILITY (absorbe synthesis_stability, gateado a synth-miss): 2ª generación → stable vs flip ──
    if do_stability and synth_miss_refs:
        ans_reps = [gen_answer_only(gold["question"], pipe["topk"]) for _ in range(K_STAB - 1)]
        for e in synth_miss_refs:
            misses = [judge_conveyed(e["valor"], e["texto"], a, workers=workers)["yes"] < THRESH_FIRM
                      for a in ans_reps]
            e["stability"] = "stable-miss" if all(misses) else "flip"   # MISS en todas las reps = estructural

    return {"qid": qid, "question": gold["question"], "answer": pipe["answer"],
            "family_resolved": family_resolved, "gold_families": sorted(gfam),
            "n_non_anchorable": n_non_anchorable,
            "pool_n": len(pipe["pool"]), "served_n": len(pipe["served"]), "topk_n": len(pipe["topk"]),
            "hist": hist, "facts": facts_out}


# ── eje SEPARADO gold/juez: reconstruye el blocker-primario por-gold (fix D, absorbe s87_rootcause) ──
# NO pre-carga el "~10/30 plateau" de DEC-075 (CADUCO) — lo re-deriva. ADVISORY: usa veredictos de un
# bvg PREVIO (no fresco) → orientativo, no zanja (el PASS fresco = eval caro diferido, gate Alberto).
BLOCKER_ORDER = ["corpus-gap", "retrieval-miss", "rerank-miss", "synthesis-miss"]  # más-abajo-primero
def gold_juez_axis(per_gold: list[dict], bvg: dict) -> list[dict]:
    axis = []
    for r in per_gold:
        h = r["hist"]
        n_classified = sum(h[c] for c in h if c != "meta-ref")
        fails = {c: h[c] for c in BLOCKER_ORDER if h[c] > 0}
        primary = None
        if fails:
            mx = max(fails.values())
            for c in BLOCKER_ORDER:
                if fails.get(c) == mx:
                    primary = c; break
        identidad = sum(1 for f in r["facts"]
                        if isinstance(f.get("submotivo"), dict)
                        and f["submotivo"].get("submotivo") == "model-filter"
                        or (isinstance(f.get("submotivo"), str) and f.get("submotivo") == "model-filter"))
        verdict = (bvg.get(r["qid"], {}) or {}).get("veredicto", "?")
        perp = (verdict not in ("PASS", "?")) and primary is None and n_classified > 0
        axis.append({"qid": r["qid"], "verdict": verdict, "n_classified": n_classified,
                     "n_ok": h["OK"], "primary_blocker": primary, "n_identidad_facts": identidad,
                     "family_resolved": r["family_resolved"], "no_pass_perp_pipeline": perp})
    return axis


# ── manifest / freeze-contract ──
def corpus_fingerprint() -> dict:
    for attempt in range(3):     # count=exact sobre 25k filas puede tardar → retry con timeout amplio
        try:
            with httpx.Client(timeout=60.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                          headers={**_HEADERS, "Prefer": "count=exact"}, params={"select": "id", "limit": "1"})
                cnt = r.headers.get("content-range", "*/?").split("/")[-1]
                r2 = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=_HEADERS,
                           params={"select": "created_at", "order": "created_at.desc", "limit": "1"})
                mx = (r2.json() or [{}])[0].get("created_at", "?")
            return {"table": CHUNKS_TABLE, "count": cnt, "max_created_at": mx}
        except Exception as e:
            last = f"{type(e).__name__}"
            time.sleep(2 ** attempt)
    return {"table": CHUNKS_TABLE, "error": last}


def build_manifest() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = "?"
    assert RERANK_TOP_K == 10, f"RERANK_TOP_K={RERANK_TOP_K} ≠ demo(10) — pipeline fantasma (fix A)"
    gic = os.environ.get("GENERATOR_INCLUDE_CONTEXT")     # flag vivo (generator.py:23)
    return {
        "route": "eval-harness (sin target_models, strict, available_models=None) — paridad bvg/DEC-075",
        "git_commit": commit,
        "corpus": corpus_fingerprint(),
        "flags_demo": dict(DEMO_FLAGS),
        "flags_source": "6 overrides Railway DEC-asserted (valores enmascarados en dashboard) + defaults de código",
        "resolved": {"RETRIEVAL_TOP_K": RETRIEVAL_TOP_K, "RERANK_TOP_K": RERANK_TOP_K,
                     "LLM_MAX_TOKENS": LLM_MAX_TOKENS, "LLM_MODEL": LLM_MODEL,
                     "RELEVANCE_THRESHOLD": RELEVANCE_THRESHOLD, "RERANKER_BACKEND": RERANKER_BACKEND,
                     "MERGE_STRATEGY": MERGE_STRATEGY, "RERANK_PREVIEW_CHARS": RERANK_PREVIEW_CHARS,
                     "GENERATOR_INCLUDE_CONTEXT": gic},
        "judge": {"model": JUDGE_MODEL, "K": K, "K_stability": K_STAB,
                  "support_sha": _sha(SUPPORT_SYS + SUPPORT_USER),
                  "conveyed_sha": _sha(CONVEY_SYS + CONVEY_USER),
                  "submotivo_sha": _sha(SUBMOTIVO_SYS + SUBMOTIVO_USER)},
        "similarity_note": "pin de pool NO estampa `similarity` como fiel: stamp plano léxico "
                           "(retriever.py:554) ≠ coseno (fix G).",
        "diversify_tiebreak": "AUSENTE del pipeline (flag muerto, DEC-091 NO-GO) — no en freeze (fix B).",
        "family_aware": "acreditación de soporte SAME-FAMILY vía product_model (fix #3, reusa retrieval_miss_famtie).",
    }


def estimate_cost(n_golds: int, avg_facts: float = 3.2) -> str:
    n_facts = int(n_golds * avg_facts)
    support = n_facts * K * 7            # TODOS los facts (fix v3): ~7 batches (pool-50/BATCH≈7) × K
    conveyed = int(n_facts * 0.7) * K    # los reaches_gen (~70%)
    submotivo = int(n_facts * 0.25) * K
    stability = int(n_facts * 0.25) * (K_STAB - 1) * (1 + K)   # 1 gen + K conveyed por synth-miss
    sem_corpus = int(n_facts * 0.15) * K * 3   # no-anclables-no-en-pool (~15%) × K × 3 batches acotados
    calls = support + conveyed + submotivo + stability + sem_corpus
    usd = calls * 0.004
    return (f"~{n_golds} golds × ~{avg_facts} facts ≈ {n_facts} hechos · ~{calls} llamadas "
            f"(support≈{support}, conveyed≈{conveyed}, submotivo≈{submotivo}, stability≈{stability}, "
            f"sem-corpus≈{sem_corpus}) · ≈ ${usd:.0f}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "full"])
    ap.add_argument("--qids", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-submotivo", action="store_true")
    ap.add_argument("--no-stability", action="store_true")
    args = ap.parse_args()

    dev = {g["qid"]: g for g in load_dev()}
    # Veredictos PASS para el eje gold/juez. ADVISORY: bvg PREVIO (posiblemente pre-ancho/A3) — el eje
    # gold/juez FRESCO necesita el PASS caro sobre el pipeline actual, que el spec DIFIERE (gate Alberto).
    bvg_path = ROOT / "evals" / "bot_vs_gold_results_k5.yaml"
    bvg = {}
    if bvg_path.exists():
        try:
            bvg = {r["qid"]: r for r in yaml.safe_load(bvg_path.read_text(encoding="utf-8"))}
        except Exception:
            bvg = {}

    if args.mode == "smoke":
        qids = [q.strip() for q in args.qids.split(",") if q.strip()] or SMOKE_QIDS
        qids = [q for q in qids if q in dev]
    else:
        qids = sorted(dev)

    print(f"factlevel_assessment · mode={args.mode} · {len(qids)} golds · RUTA HARNESS (sin target_models)")
    print(f"  DEMO flags: RERANK_TOP_K={RERANK_TOP_K} LLM_MAX_TOKENS={LLM_MAX_TOKENS} "
          f"ENUNCIADOS={os.environ.get('ENUNCIADOS_MULTIVECTOR')} "
          f"IDENTITY={os.environ.get('IDENTITY_RESOLVE')}/{os.environ.get('IDENTITY_RESOLVE_POLICY')} CHUNKS={CHUNKS_TABLE}")
    print(f"  coste estimado: {estimate_cost(len(qids))}")
    if bvg:
        print(f"  ⚠ eje gold/juez ADVISORY (veredictos de {bvg_path.name}, bvg previo — no zanja)")
    manifest = build_manifest()
    print(f"  manifest: commit={manifest['git_commit']} corpus={manifest['corpus']}")
    # fix dúo build2 #5: freeze-hash del run → el .partial se auto-invalida si cambió corpus/flags/juez/código
    # (antes era cache ciega → podía MEZCLAR corridas incompatibles, contra "regenerar SIEMPRE").
    freeze_hash = _sha(json.dumps({"c": manifest["git_commit"], "f": manifest["flags_demo"],
                                   "r": manifest["resolved"], "j": manifest["judge"]}, sort_keys=True))

    out_path = OUT_DIR / f"s100_factlevel_{args.mode}.yaml"
    partial = out_path.with_suffix(".partial.jsonl")
    done = {}
    if partial.exists():
        lines = partial.read_text(encoding="utf-8").splitlines()
        head = {}
        try:
            head = json.loads(lines[0]) if lines else {}
        except Exception:
            head = {}
        if head.get("_freeze_hash") == freeze_hash:
            for line in lines[1:]:
                try:
                    r = json.loads(line); done[r["qid"]] = r
                except Exception:
                    continue
            print(f"  resumible: {len(done)} golds ya medidos (freeze-hash coincide)")
        else:
            print(f"  ⚠ .partial DESCARTADO: freeze-hash cambió (corpus/flags/juez/código distintos) → re-mido todo")
            partial.unlink()
    if not partial.exists():
        partial.write_text(json.dumps({"_freeze_hash": freeze_hash}) + "\n", encoding="utf-8")

    per_gold = []
    with partial.open("a", encoding="utf-8") as pf:
        for qid in qids:
            if qid in done:
                per_gold.append(done[qid]); continue
            t0 = time.time()
            r = measure_gold(dev[qid], workers=args.workers,
                             do_submotivo=not args.no_submotivo, do_stability=not args.no_stability)
            pf.write(json.dumps(r, ensure_ascii=False) + "\n"); pf.flush()
            per_gold.append(r)
            h = r["hist"]
            fam = "" if r["family_resolved"] else " ⚠fam?"
            print(f"  [{qid}]{fam} {time.time()-t0:4.0f}s · OK={h['OK']} synth={h['synthesis-miss']} "
                  f"rerank={h['rerank-miss']} retr={h['retrieval-miss']} corpus={h['corpus-gap']} "
                  f"meta={h['meta-ref']} (nonanch={r.get('n_non_anchorable',0)})")

    agg = {k: 0 for k in ("OK", "synthesis-miss", "rerank-miss", "retrieval-miss",
                          "corpus-gap", "meta-ref")}
    for r in per_gold:
        for k2, v in r["hist"].items():
            agg[k2] += v
    axis = gold_juez_axis(per_gold, bvg)
    n_perp = sum(1 for a in axis if a["no_pass_perp_pipeline"])
    n_unresolved = sum(1 for r in per_gold if not r["family_resolved"])
    n_non_anchorable = sum(r.get("n_non_anchorable", 0) for r in per_gold)

    result = {"manifest": manifest, "mode": args.mode, "n_golds": len(per_gold),
              "aggregate_hist": agg, "gold_juez_axis": axis, "gold_juez_advisory": bool(bvg),
              "n_no_pass_perp_pipeline": n_perp, "n_family_unresolved": n_unresolved,
              "n_non_anchorable": n_non_anchorable, "per_gold": per_gold}
    out_path.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print("\n── AGREGADO (hechos a nivel-pipeline, family-aware · TODOS los facts clasificados, fix v3) ──")
    total_c = sum(agg[c] for c in agg if c != "meta-ref")
    for c in ["OK", "synthesis-miss", "rerank-miss", "retrieval-miss", "corpus-gap"]:
        print(f"  {c:16s} {agg[c]:3d}  ({100*agg[c]/max(total_c,1):.0f}% de clasificados)")
    print(f"  {'meta-ref':16s} {agg['meta-ref']:3d} (puntero, fuera del histograma)")
    print(f"  no-anclables-léxicamente: {n_non_anchorable}/{total_c} facts (clasificados vía juez SEMÁNTICO, no filtrados)")
    print(f"  family-unresolved: {n_unresolved} golds (soporte NO family-filtrado ahí)")
    print(f"  eje gold/juez (ADVISORY): {n_perp} golds NO-PASS ⊥ pipeline (DEC-075 caduco, re-derivado)")
    print(f"\n→ {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
