#!/usr/bin/env python3
"""factlevel_assessment.py (s100 · instrumento v3.0 s286e) — assessment a nivel-hecho ESTANDARIZADO.

UN entry-point canónico que unifica los instrumentos ad-hoc (s85/s87/s88/s99) que bit-roteaban.
Clasifica cada hecho CORE de cada gold-dev en UNA clase terminal del funnel de PIPELINE.

RUTA (v3.0, s286e — CAMBIO DE RUTA, serie nueva): la medición CRUZA EL SEAM DE SERVING
(`src.rag.serving_pipeline.execute_rag_turn`), la MISMA función que `scripts/test_bot_vs_gold.py`
y que el handler de Telegram — espejo FUNCIONAL de bvg:run_bot con dos deltas declarados (captura
del pool + los jueces). Hasta v2.2 llamaba retrieve/rerank/generate DIRECTO y por tanto era CIEGA
a las filas que las lanes de coverage apendizan DESPUÉS del rerank: cualquier lever de lane era
invisible en la medición. Sigue siendo la ruta EVAL-HARNESS (sin target_models, rerank strict,
available_models=None) para conservar la paridad con bvg/DEC-075; la ruta Telegram
(target_models + available_models) es una medición SEPARADA con su propio baseline. Flags = los
de la DEMO (Railway), con el flag-set COMPLETO del seam pineado (ver DEMO_FLAGS).

VISTA SERVIDA: `served` NO es "topk sobre el umbral" — es `admitted_evidence_rows()` IMPORTADO de
`src/rag/generator.py` (fuente única, r2-4). El soporte se parte en dos ejes (cláusula 19):
`sup_pool` (pool-50) alimenta in_pool/in_topk/pool_rank y las clases upstream; `sup_served` (la
vista del generador — las filas de coverage validadas se juzgan sobre `coverage_context_content`,
los excerpts que el modelo VE) alimenta reaches_gen y el conveyed-check.

Taxonomía v3 (5 clases terminales + OK; TODOS los facts clasificados), FAMILY-AWARE (fix dúo build #3):
  corpus-gap    — el hecho NO existe servible en el corpus (default = FN-MÍO, anti-FN reforzado)
  retrieval-miss— servible en corpus pero NINGÚN chunk SAME-FAMILY en el pool-50   (sub: within-doc/es-en/model-filter/cross-fam)
  rerank-miss   — chunk-soporte same-family en pool-50 pero NO sobrevive al top-k  (sub: pos-buried/lexical)
  synthesis-miss— servido pero la respuesta NO lo transmite (sub-motivo LLM CON chunks servidos:
                  omitted/hedged/partial/contradicted/threshold-drop/append_view_truncated)
                  + STABILITY (rep×2 sobre la composición SERVIDA, flip vs structural)
  OK            — servido + transmitido
`append_view_truncated` (s286e) = el valor está en el content de una fila apendizada y servida pero
FUERA de sus excerpts: gap de EXCERPT de lane, ni retrieval ni síntesis-LLM. Es SUB-MOTIVO (las 5
clases terminales quedan intactas; precedente exacto: threshold-drop) y NO prevalece sobre
rerank-miss. Golds cuyo coverage erroreó tras retry: `coverage_degraded`, fuera del histograma.
`lexically_anchorable` = FLAG por-hecho (fix v3, NO gate): los no-anclables (prosa/periodicidades) se clasifican
igual vía juez SEMÁNTICO; solo enruta el corpus-check (léxico vs semántico). meta-ref (valor=puntero: apéndice/
tabla) = único fuera del histograma.

FAMILY-AWARE (fix #3): un chunk-soporte SOLO acredita si es de la MISMA FAMILIA de producto que el gold
(via product_model, reusa retrieval_miss_famtie) — sin esto, un valor que coincide por casualidad en OTRO
producto acredita mal (bug hp018, DEC-075 by_target).

Anti-bit-rot: regenerar SIEMPRE (no cache, no seed DEF). Join hecho↔texto por clave (qid#idx:valor) — ESTABLE
para el orden actual de core_facts() (NO una fact-id global; si core_facts reordena, cambia — declarado).
Freeze-contract leído del ENTORNO, RE-AFIRMADO tras los imports (los módulos legacy hacen load_dotenv override).
El `pipe_sha` del freeze-hash es el CLOSURE DE IMPORTS del seam (AST, orden estable) + sus configs
versionadas — no una lista a mano: una lane nueva o un dirty-tree en coverage invalidan el `.partial` solos.

Modos:
  python scripts/factlevel_assessment.py smoke [--qids hp007,cat007]   # subset + estimación de coste
  python scripts/factlevel_assessment.py full                          # 39 dev
Salida: evals/s100_factlevel_<mode>_<tag>.yaml (+ .partial.jsonl resumible) + manifest embebido.
(s286c: tag SIEMPRE — env FACTLEVEL_OUTPUT_TAG — para no pisar el histórico congelado; s286e: el
default lleva la versión del instrumento, `v3_<fecha>`, para no colisionar con los fulls v2.2.)
La fila del scoreboard publica además n(via_coverage_append), n(append_view_truncated) y
n(coverage_degraded) — los campos que reconcilian esta serie con las etapas del mapa.
"""
from __future__ import annotations
import os
# ── Freeze-contract: EXPORTAR el flag-set de la DEMO ANTES de importar el pipeline ──
# (confirmado s100 con Alberto vía Railway Variables; valores DEC-sourced "verificado en producción").
DEMO_FLAGS = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "IDENTITY_RESOLVE": "on",
    # s286b (staleness cazada por ALBERTO): el set llevaba congelado desde el 10-jul y NO
    # medía la release C1 (PR#184: coverage_c1_v4 + identity REPLACE + must-preserve) que
    # produjo la foto banked 146/154 (DEC-131/134) — el full del 29-jul corrió PRE-C1 y sus
    # retr=10/rerank=8 no son comparables con esa foto. Desde s286b el set espeja la SHIP
    # CONFIG del baseline v4 (scripts/s286_baseline_v4_launcher.sh) = la config del OBJETIVO
    # FALLO→0/PARCIAL≤10. Cambia el freeze-hash (partials pre-s286b no comparables).
    "IDENTITY_RESOLVE_POLICY": "replace",
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4",
    "MUST_PRESERVE_CONTRACT": "on",
    "VISUAL_ASSETS_REGISTRY": "on",
    "ANTI_DIAGRAM_INVENTION": "on",
    "WIRING_TOPOLOGY_GUARD": "on",
    "GENERATOR_DIRECT_FIRST": "on",
    "GENERATOR_FOLLOWUPS": "off",
    "VISUAL_ASSETS_LISTING_GATE": "on",
    "LLM_MAX_TOKENS": "3500",
    "RERANK_TOP_K": "10",
    # defaults de código (ausentes de Railway) — explícitos para que el manifest no mienta:
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800",
    "HYDE_ENABLED": "false",
    # seams de PILOTO vivos en el código (s101) — PINEADOS a off: un env sucio no puede
    # contaminar una medición "demo" (crít cross-model s101b).
    "DIVERSIFY_TIEBREAK": "off",
    "HYQ_PILOT_FILE": "",
    # s102/DEC-098: fidelity SHIPPEADO a Railway (Alberto confirmó var + redeploy 8-jul) →
    # la "demo" que este instrumento mide lo lleva ON. Cambia el freeze-hash (correcto: los
    # partials pre-ship no son comparables).
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    # s102/DEC-099: canal hyq SHIPPEADO (PR#115 merged 9-jul; flip cat016 verificado en
    # query_logs de prod, bot_version=d355867) → la demo lo lleva ON. Cambia el freeze-hash.
    "HYQ_TABLE": "on",
    # s103b/DEC-101: landing v3.1 (código, entra con el merge PR#116) + bloque de selección
    # CODE-GATED shippeados (Alberto confirmó merge + var en Railway 10-jul) → la demo lo
    # lleva ON. Cambia el freeze-hash. CAVEAT declarado para la fila v3 del scoreboard: el
    # bucket in-pool gana +10 de ancho mecánico donde el canal dispara (pool ≤ top_k+cuota).
    "GENERATOR_SELECTION_BLOCK": "on",
    # ── s286e (r2-1): el flag-set COMPLETO del seam de coverage ─────────────────
    # Los 7 flags-hoja que `post_rerank_coverage` consulta y que NO son
    # profile-owned se resuelven del ENTORNO, no del perfil. Sin pinearlos, un
    # .env sucio mediría OTRA stack de lanes bajo la etiqueta "demo". Todos
    # "off" = el ship de Railway (ausentes/TARGET_OFF) y lo único que
    # `validate_release_contract` admite junto a coverage_c1_v4.
    "TABLE_PREAMBLE_CLOSURE": "off",
    "CANONICAL_HYQ_COVERAGE": "off",
    "COMPATIBILITY_BUNDLE_COVERAGE": "off",
    "RERANK_POOL_COVERAGE": "off",
    "STRUCTURAL_CASCADE_COVERAGE": "off",
    "LOGICAL_RECORD_COVERAGE": "off",
    "EVIDENCE_DERIVATION_OVERLAY": "off",
    # s286e (m6): la ruta v3 cruza el seam, que SIEMPRE llama al observer de
    # shadow. Pineado off para que un .env sucio no lo active en medición.
    "STRUCTURAL_NEIGHBOR_SHADOW": "off",
    # s289 (dúo r3, S3=A2): los 2 fixes de orden/fallback de etapa 2 son
    # flags-hoja del MISMO seam — pineados off (= ship). El runner de gates los
    # pone ON vía override DECLARADO post-_assert_demo_flags y el freeze-hash
    # del brazo estampa el flag-set efectivo.
    "FACET_COMPLEMENT_FALLBACK": "off",
    "OBLIGATION_RESERVE_ORDERED": "off",
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

import ast, copy, sys, re, json, time, hashlib, argparse, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import httpx
import yaml
import anthropic
from openai import OpenAI
from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=False)   # NO pisar los DEMO_FLAGS
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

from src.rag.retriever import retrieve_chunks
from src.rag.reranker import rerank
from src.rag.generator import (
    generate_answer, admitted_evidence_rows, RELEVANCE_THRESHOLD,
)
from src.rag.post_rerank_coverage import coverage_context_content
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn
from src.rag.structural_neighbor_shadow import observe_structural_neighbor_shadow
from src.config import (RETRIEVAL_TOP_K, RERANK_TOP_K, LLM_MODEL, LLM_MAX_TOKENS,
                        RERANKER_BACKEND, MERGE_STRATEGY, RERANK_PREVIEW_CHARS, CHUNKS_TABLE,
                        COVERAGE_RELEASE_POLICY, validate_config)
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
from scripts.audit_locator import (
    SCORE_FLOOR,
    fact_match_score,
    measurable,
    support_candidate_priority,
    support_l1_guard_allows,
)
from scripts.retrieval_miss_famtie import gold_family, fam_norm, _pm_by_ids, _is_meta_ref
from scripts.toc_heuristic import is_toc_page

_assert_demo_flags()   # 2º set: RE-AFIRMAR tras los imports (fix #2 — los legacy hicieron override=True)

# Sanity: el pipeline importado DEBE ver el flag-set de la demo, no el default local (fix dúo build2 #1).
# Assertar TODOS los load-bearing (no solo RERANK_TOP_K): `src.config` hace load_dotenv(override=True) EN
# IMPORT → si el .env local pisa una constante import-time, re-fijar os.environ después NO la corrige.
assert RERANK_TOP_K == 10, f"RERANK_TOP_K={RERANK_TOP_K} ≠ demo(10) — pipeline fantasma"
assert LLM_MAX_TOKENS == 3500, f"LLM_MAX_TOKENS={LLM_MAX_TOKENS} ≠ demo(3500) — pipeline fantasma"
assert CHUNKS_TABLE == "chunks_v2", f"CHUNKS_TABLE={CHUNKS_TABLE} ≠ demo(chunks_v2) — pipeline fantasma"
assert RERANKER_BACKEND == "llm", f"RERANKER_BACKEND={RERANKER_BACKEND} ≠ demo(llm) — pipeline fantasma"
assert MERGE_STRATEGY == "stamps", f"MERGE_STRATEGY={MERGE_STRATEGY} ≠ demo(stamps) — pipeline fantasma"
assert RERANK_PREVIEW_CHARS == 800, f"RERANK_PREVIEW_CHARS={RERANK_PREVIEW_CHARS} ≠ demo(800) — pipeline fantasma"
from src.config import CHUNKS_IS_V2 as _isv2  # noqa: E402
from src.rag.hyde import HYDE_ENABLED as _hyde_on  # noqa: E402
assert not _hyde_on, "HYDE_ENABLED=true ≠ demo(off) — pipeline fantasma"
# Flags de generación que alteran el prompt en runtime → paridad bvg exige OFF (fix dúo build2 #2).
assert not os.getenv("GENERATOR_INCLUDE_CONTEXT"), "GENERATOR_INCLUDE_CONTEXT ON rompe paridad bvg/DEC-075"
assert os.getenv("GENERATOR_PROMPT_VARIANT") == "fidelity", \
    "GENERATOR_PROMPT_VARIANT≠fidelity ≠ demo (DEC-098: shippeado 8-jul; si se revierte en Railway, actualizar DEMO_FLAGS)"
# DEC-099: el canal hyq de la demo va ON — guard seam-a-código (patrón s102): el flag es
# IMPORT-time (HYQ_TABLE_ON) y el dispatcher debe CONSULTARLO (un revert en Railway sin
# actualizar DEMO_FLAGS, o un env sucio, mediría una demo fantasma).
import inspect as _inspect  # noqa: E402
from src.rag import retriever as _rt_guard  # noqa: E402
assert _rt_guard.HYQ_TABLE_ON is True, \
    "HYQ_TABLE≠on ≠ demo (DEC-099: shippeado 9-jul; si se revierte en Railway, actualizar DEMO_FLAGS)"
assert "HYQ_TABLE_ON" in _inspect.getsource(_rt_guard.vector_search), \
    "vector_search NO consulta HYQ_TABLE_ON — seam no cableado"

JUDGE_MODEL = "gpt-5.5"
JUDGE2_MODEL = "claude-opus-4-8"   # dual-judge (s100, suite de aceptación n=5 fakes/6 OK + 5 flips regla-C;
                                   # artefacto evals/s100_dualjudge_validation.txt; spot-check de flips = protocolo del run)
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
                              served=served, answer=(answer or "")[:CONVEY21_ANSWER_CAP])}],
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
# s286e: la ruta v2.2 llamaba retrieve/rerank/generate DIRECTO y era CIEGA a las filas que las lanes de
# coverage apendizan DESPUÉS del rerank (el seam de serving). Desde v3 cruza `execute_rag_turn` — la
# MISMA función que bvg (test_bot_vs_gold.py:170-183) y que el handler de Telegram.
_CAPTURED_POOL: list[dict] = []   # objeto de captura MODULE-LEVEL (ver `_capture_retrieve`)


def _capture_retrieve(query: str, top_k: int) -> list[dict]:
    """Adapter de retrieve que GUARDA el pool ordenado que ve el seam.

    `execute_rag_turn` devuelve conteos, no el pool: sin esta captura habría que
    re-recuperar fuera del run y eso rompe la identidad de la medición (el retrieve
    no es idéntico entre llamadas). Es MODULE-LEVEL a propósito: el seam-guard AST
    camina el cuerpo de `run_pipeline` y un closure anidado ahí lo rompería."""
    pool = retrieve_chunks(query, top_k=top_k)
    _CAPTURED_POOL.clear()
    _CAPTURED_POOL.extend(copy.deepcopy(pool))   # deepcopy: el seam muta/deepcopyea aguas abajo
    return pool


def _eval_strict_rerank(query: str, chunks: list[dict], **kwargs):
    """Reranker ESTRICTO en evaluación (patrón bvg, test_bot_vs_gold.py:159-160): una avería
    de eval no debe confundirse con el fail-open de disponibilidad de producción."""
    return rerank(query, chunks, strict=True, **kwargs)


def _lane_by_appended_id(coverage_trace: dict, appended: list[dict]) -> dict:
    """lane de cada fila apendizada: la traza de lane la declara en `selected_ids`;
    la propia fila la lleva en `retrieval_lane` (fallback para lanes sin traza de ids)."""
    lanes: dict[str, str | None] = {}
    for lane_trace in (coverage_trace.get("lanes") or []):
        if not isinstance(lane_trace, dict):
            continue
        for cid in (lane_trace.get("selected_ids") or []):
            lanes.setdefault(str(cid), lane_trace.get("lane"))
    for row in appended:
        lanes.setdefault(str(row.get("id") or ""), row.get("retrieval_lane"))
    return lanes


def run_pipeline(question: str) -> dict:
    """UN turno servido completo cruzando el seam (retrieve → rerank → coverage → generate).

    Fail-open de coverage (cláusulas 4+18): `status=="error"` → retry 1× sobre el ÚNICO
    call-site del seam; si persiste, el gold se devuelve con `coverage_degraded=True` y
    queda fuera del histograma (nada se promedia en silencio)."""
    pipeline: dict = {}
    for attempt in range(2):
        pipeline = execute_rag_turn(
            query=question,
            query_for_retrieval=question,
            target_models=None,                  # paridad harness/bvg
            available_models=None,               # paridad harness/bvg
            retrieval_top_k=RETRIEVAL_TOP_K,
            rerank_top_k=RERANK_TOP_K,
            adapters=RagServingAdapters(
                retrieve=_capture_retrieve,
                rerank=_eval_strict_rerank,
                observe_structural_shadow=observe_structural_neighbor_shadow,
                generate=generate_answer,
            ),
        )
        if (pipeline.get("coverage_trace") or {}).get("status") != "error":
            break

    trace = pipeline.get("coverage_trace") or {}
    chunks = pipeline["chunks"]                       # prefijo protegido + appends de coverage
    n_prefix = pipeline["reranked_rows"]
    topk = chunks[:n_prefix]                          # garantía de prefijo del seam (r2-5)
    appended = chunks[n_prefix:]
    pool = list(_CAPTURED_POOL)
    served = admitted_evidence_rows(chunks)           # la VISTA del generador (fuente única)
    return {"answer": (pipeline.get("generation") or {}).get("answer", ""),
            "pool": pool, "topk": topk, "served": served, "chunks": chunks, "appended": appended,
            "topk_ids": [c.get("id") for c in topk], "served_ids": [c.get("id") for c in served],
            "pool_ids": [c.get("id") for c in pool],
            "appended_ids": [str(c.get("id") or "") for c in appended],
            "appended_lane": _lane_by_appended_id(trace, appended),
            "coverage_status": trace.get("status"),
            "coverage_degraded": trace.get("status") == "error"}


def gen_answer_only(question: str, served_composition: list[dict]) -> str:
    """Regenera la respuesta sobre una composición YA servida (reps de estabilidad).
    El insumo es `pipeline["chunks"]` — prefijo + appends — no el topk (cláusula 6)."""
    return generate_answer(question, served_composition).get("answer", "")


def served_view(chunk: dict) -> dict:
    """La fila TAL COMO la ve el generador: una fila de coverage VALIDADA se sirve como
    excerpts acotados (`coverage_context_content`), no como su content completo."""
    view = dict(chunk)
    view["content"] = coverage_context_content(chunk)
    return view


def pool_rank_of(supported: set[str], pool_ids: list[str]) -> int:
    ranks = [i for i, cid in enumerate(pool_ids) if cid in supported]
    return min(ranks) if ranks else 10**6


# ── JUEZ conveyed v2.1 (s102, L3 del mapa Fase-2): cap de answer 12k (con ancho-10 las respuestas
# llegan a ~7k y el cap 6k del juez legacy TRUNCABA lo juzgado — falso miss del tramo final, medido
# cat017) + rúbrica explícita de morfología/cuantificadores (relation-slip: 'by Event/Events',
# 'requiere licencia' vs 'una por lazo'). MISMO esquema JSON; sha propio en manifest (cambio declarado).
CONVEY21_USER = (
    "HECHO a verificar:\n"
    "  · VALOR: «{valor}»\n"
    "  · RELACIÓN (de qué trata el hecho): {texto}\n\n"
    "RESPUESTA del asistente:\n<<<\n{answer}\n>>>\n\n"
    "¿La RESPUESTA AFIRMA o IMPLICA DIRECTAMENTE el HECHO — es decir, transmite el VALOR «{valor}» "
    "EN esa RELACIÓN? Admite traducción ES↔EN, paráfrasis, OCR imperfecto y VARIACIÓN MORFOLÓGICA "
    "(singular/plural, mayúsculas, 'Event/Events', notación con/sin puntos). PERO los CUANTIFICADORES "
    "materiales cuentan: si el hecho dice 'una licencia POR CADA lazo' y la respuesta solo dice "
    "'requiere licencia' sin la cardinalidad, NO está transmitido. Marca 'no' si: el valor no aparece, "
    "aparece en OTRA relación/condición/componente, la respuesta se escuda o afirma un valor DISTINTO. "
    "Ante la duda, 'no'.\n"
    'Responde EXCLUSIVAMENTE JSON: {{"afirmado": true|false}}.'
)
CONVEY21_ANSWER_CAP = 12000

# Versión del INSTRUMENTO (F4 cross-model s102: cada cambio de juez/clasificador rompe la
# comparabilidad del scoreboard y debe quedar declarado EN el artefacto, no solo en el doc).
# v2   = dual-judge (GPT-5.5 K=5 → Opus K=5) en conveyed + soporte-targeted
# v2.1 = juez conveyed cap 12k + rúbrica morfología/cuantificadores + umbral proporcional
# v2.2 = H4: kill de anclas-TOC en el crédito de soporte L1 (re-adjudicable por la red dual)
# v3.0 = s286e: la medición cruza el SEAM de serving (execute_rag_turn) en vez de llamar
#        retrieve/rerank/generate directo → las filas apendizadas por las lanes de coverage
#        dejan de ser invisibles. Serie NUEVA: una fila v3 y una v2.2 del mismo día son FOTOS
#        DISTINTAS (composición servida distinta + rerank no determinista), NO el delta causal
#        del seam. La reconciliación entre etapas usa n(via_coverage_append).
# v3.1 = s287 P0: kilo-bridge en audit_locator (6K8↔6,8kΩ↔6800Ω — canonicalización kilo en
#        _unit_quantities + puente en support_candidate_priority/guard L1). Cierra S5 de
#        DEC-096c: el guard ya no mata soporte servido same-family por re-grafía del prefijo
#        kilo (hp018#1). Solo acredita fila SERVIDA de la familia correcta (Sol-1/DEC-091b).
INSTRUMENT_VERSION = "v3.1"


def _conveyed21_once(valor: str, texto: str, answer: str) -> int | None:
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for attempt in range(4):
        try:
            resp = oai.chat.completions.create(
                model=JUDGE_MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": CONVEY_SYS},
                          {"role": "user", "content": CONVEY21_USER.format(
                              valor=valor, texto=(texto or "")[:600],
                              answer=(answer or "")[:CONVEY21_ANSWER_CAP])}])
            out = json.loads(resp.choices[0].message.content.strip())
            af = out.get("afirmado")
            if isinstance(af, bool):
                return 1 if af else 0
            raise ValueError(f"afirmado no-bool: {af!r}")
        except Exception:
            time.sleep(2 ** attempt)
    return None


def judge_conveyed21(valor: str, texto: str, answer: str, workers: int = 6) -> dict:
    """Primario conveyed v2.1 (GPT-5.5 K=5, cap 12k, rúbrica morfología+cuantificadores)."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = [f.result() for f in [pool.submit(_conveyed21_once, valor, texto, answer) for _ in range(K)]]
    valid = [v for v in votes if v is not None]
    return {"yes": sum(valid), "n_fail": votes.count(None)}


# ── DUAL-JUDGE de conveyed (s100): 2º juez Opus 4.8 SOLO sobre los MISS del primario ──
# Motivación (verificado s100): GPT-5.5 single dio ~5-7 FN/16 synth-miss (valor LITERAL en la respuesta
# y conveyed=0, p.ej. hp006 'MPS-400', hp013 'EEPROM', hp018 '4 salidas'). Validación balanceada:
# Opus flipea 5/16 a conveyed, coincide-miss en 11, 0 FP sobre valores perturbados-falsos (5/5 rechaza),
# 6/6 en OK-reales. Regla de adjudicación: synthesis-miss REQUIERE CONSENSO (ambos jueces < firme);
# Opus≥4 → 'judge-disagreement' (cuenta OK, flagged y listado aparte — trazable, no silencioso).
# El eje de SOPORTE (judge_fact) y el de INVENCIÓN no se tocan. MISMO prompt congelado (sha en manifest).
def _judge2_once(valor: str, texto: str, answer: str) -> int | None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    for attempt in range(4):
        try:
            m = client.messages.create(
                model=JUDGE2_MODEL, max_tokens=200, system=CONVEY_SYS,
                messages=[{"role": "user", "content": CONVEY21_USER.format(
                    valor=valor, texto=(texto or "")[:600],
                    answer=(answer or "")[:CONVEY21_ANSWER_CAP])}])   # paridad de prompt/cap con el primario v2.1
            t = m.content[0].text.strip()
            j = re.search(r"\{.*\}", t, re.S)
            if not j:                                   # H2 (dúo): sin JSON = fallo, NO voto "no"
                raise ValueError("respuesta sin JSON")
            out = json.loads(j.group(0))
            af = out.get("afirmado")
            if isinstance(af, bool):                    # H3 (dúo): solo bool real; string truthy era voto-YES falso
                return 1 if af else 0
            if isinstance(af, str) and af.strip().lower() in ("true", "si", "sí", "yes"):
                return 1
            if isinstance(af, str) and af.strip().lower() in ("false", "no"):
                return 0
            raise ValueError(f"afirmado no-bool: {af!r}")
        except Exception:
            time.sleep(2 ** attempt)
    return None


def judge_conveyed_dual(valor: str, texto: str, answer: str, workers: int = 5) -> dict:
    """K votos del 2º juez (Opus). Se llama SOLO cuando el primario (GPT-5.5) dio miss.
    NOTA (s102): prompt v2.1 compartido con el primario — la suite s100 validó el prompt v1;
    v2.1 = cambio declarado, la salvaguarda es el spot-check regla-C de flips (protocolo del doc).
    C2 (cross-model s102): con fallos parciales, el umbral es PROPORCIONAL a los votos válidos
    (yes >= ceil(4/5·n_valid)) — un hipo de API no decide clase terminal; n_valid<K queda flagged."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = [f.result() for f in [pool.submit(_judge2_once, valor, texto, answer) for _ in range(K)]]
    valid = [v for v in votes if v is not None]
    n_valid = len(valid)
    import math
    thresh = math.ceil(THRESH_FIRM * n_valid / K) if n_valid else THRESH_FIRM
    return {"yes": sum(valid), "n_fail": votes.count(None), "n_valid": n_valid,
            "firm": bool(n_valid and sum(valid) >= thresh)}


# ── DUAL-SOPORTE targeted (s101): 2º juez Opus sobre el eje de SOPORTE, solo cuando sup=∅ ──
# Evidencia (s101, workflow 7 adjudicadores + 21 refuters): 6/7 facts "retrieval-miss" con candidato
# léxico en pool eran FN del juez de soporte (el chunk SÍ afirma el hecho en SU relación; 0/18 votos de
# refutación). Targeted = solo los candidatos LÉXICOS del pool (fact_match>=FLOOR, típicamente 1-3
# chunks → 1 batch × K Opus, barato). MISMO prompt congelado del juez de soporte. Regla espejo del dual
# de conveyed: acreditar requiere >=4/5 votos válidos; el flip queda flagged (support_judge_disagreement).
# Residual declarado: soporte parafraseado NO-léxico con sup=∅ sigue single-judge (clase no demostrada).
SUPPORT_BATCH_CAP = 8

def _support2_once(valor: str, texto: str, batch: list[dict]) -> set[str] | None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    chunk_txt = "\n\n".join(f"[ID: {c['id']}]\n{(c.get('content') or '')[:CONTENT_CHARS]}" for c in batch)
    valid_ids = {c["id"] for c in batch}
    for attempt in range(4):
        try:
            m = client.messages.create(
                model=JUDGE2_MODEL, max_tokens=400, system=SUPPORT_SYS,
                messages=[{"role": "user", "content": SUPPORT_USER.format(
                    valor=valor, texto=(texto or "")[:400], chunks=chunk_txt)}])
            t = m.content[0].text.strip()
            j = re.search(r"\{.*\}", t, re.S)
            if not j:
                raise ValueError("respuesta sin JSON")
            out = json.loads(j.group(0))
            ids = out.get("supported_ids")
            if not isinstance(ids, list):
                raise ValueError(f"supported_ids no-lista: {ids!r}")
            return {str(i) for i in ids} & valid_ids
        except Exception:
            time.sleep(2 ** attempt)
    return None


def judge_support_dual(valor: str, texto: str, candidates: list[dict], workers: int = 5) -> dict:
    """K votos Opus sobre los candidatos léxicos (YA ordenados por score por el caller).
    Devuelve ids con votos>=THRESH_FIRM. n_valid==0 = fallo TOTAL (el caller flaggea error, H3)."""
    batch = candidates[:SUPPORT_BATCH_CAP]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = [f.result() for f in [pool.submit(_support2_once, valor, texto, batch) for _ in range(K)]]
    valid = [v for v in votes if v is not None]
    import math
    n_valid = len(valid)
    thresh = math.ceil(THRESH_FIRM * n_valid / K) if n_valid else THRESH_FIRM   # C2: proporcional
    tally: dict[str, int] = {}
    for vs in valid:
        for cid in vs:
            tally[cid] = tally.get(cid, 0) + 1
    sup2 = {cid for cid, n in tally.items() if n >= thresh}
    return {"sup": sup2, "votes": tally, "n_fail": votes.count(None), "n_valid": n_valid}


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


def _pm_map(rows: list[dict]) -> dict:
    """product_model por id. Usa el campo del chunk si viene; si no, fetch por-id (famtie).
    s286e/B1: se alimenta del pool ∪ las filas APENDIZADAS — sin los appends, `same_family`
    no podría decidir sobre una fila que sí llegó al generador."""
    pm = {c.get("id"): c.get("product_model") for c in rows if c.get("id")}
    missing = [cid for cid, v in pm.items() if v in (None, "")]
    if missing:
        pm.update(_pm_by_ids(missing))
    return pm


# ── SPLIT de sets de soporte (s286e, cláusula 19) ──────────────────────────────
# `sup_pool`   = soporte sobre el pool-50 → alimenta in_pool/in_topk/pool_rank y TODAS las
#                clases upstream (semántica INTACTA respecto de v2.2).
# `sup_served` = soporte sobre la VISTA SERVIDA → alimenta reaches_gen y el conveyed-check.
def support_over_served(valor: str, texto: str, pipe: dict, sup_pool: set,
                        workers: int) -> tuple[set, dict]:
    """Soporte sobre lo que el generador realmente VE.

    Las filas cuya vista servida es BYTE-IDÉNTICA a la ya juzgada en el pool heredan su
    veredicto: re-juzgar el mismo texto solo añadiría ruido de juez (un hecho podría estar
    "en pool" y no "servido" por azar) y coste. Se juzga fresco lo que DIFIERE: los appends
    de coverage, servidos como excerpts acotados."""
    pool_content = {str(c.get("id") or ""): (c.get("content") or "") for c in pipe["pool"]}
    inherited: set = set()
    fresh: list[dict] = []
    for row in pipe["served"]:
        cid = str(row.get("id") or "")
        view = served_view(row)
        if cid in pool_content and (view.get("content") or "") == pool_content[cid]:
            if cid in sup_pool:
                inherited.add(cid)
        else:
            fresh.append(view)
    res = judge_fact(valor, texto, fresh, workers=workers) if fresh else {}
    return inherited | supported_ids(res, THRESH_FIRM), res


def support_over_append_content(valor: str, texto: str, pipe: dict, workers: int) -> tuple[set, dict]:
    """¿El valor vive en el CONTENT de una fila apendizada aunque NO en sus excerpts servidos?
    Ese delta es `append_view_truncated` (gap de EXCERPT de lane). Solo se juzga cuando la vista
    difiere del content: si coinciden no hay truncamiento posible y el pase se ahorra."""
    rows = [c for c in pipe["appended"]
            if (coverage_context_content(c) or "") != (c.get("content") or "")]
    if not rows:
        return set(), {}
    res = judge_fact(valor, texto, rows, workers=workers)
    return supported_ids(res, THRESH_FIRM), res


# ── núcleo: clasificar cada hecho CORE de un gold en su clase terminal (FAMILY-AWARE) ──
def measure_gold(gold: dict, workers: int = 6, do_submotivo: bool = True, do_stability: bool = True) -> dict:
    qid = gold["qid"]
    pipe = run_pipeline(gold["question"])
    served_ids = set(pipe["served_ids"]); topk_ids = set(pipe["topk_ids"])
    appended_ids = set(pipe["appended_ids"])
    served_appended_ids = appended_ids & served_ids
    pm = _pm_map(pipe["pool"] + pipe["appended"])   # B1: los appends también necesitan familia
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
        by_id_pool = {c.get("id"): c for c in pipe["pool"]}
        # FAIL-FAST del PRIMARIO (incidente s101: la cuota OpenAI murió a MITAD del full → 77 rescates
        # Opus + 25 falsos corpus-gap = run inválido en silencio). Si el juez primario está MUERTO
        # (0 votos válidos y >K/2 fallos), ABORTAR — el espejo de H4b aplicado al primario.
        if not v_pool.get("votes") and v_pool.get("n_fail", 0) > (K * 2):
            raise RuntimeError(f"{qid}/{valor[:20]}: juez primario (GPT-5.5) MUERTO "
                               f"({v_pool.get('n_fail')} fallos, 0 votos) — run abortado, partial limpio")
        sup = supported_ids(v_pool, THRESH_FIRM)
        # L1 (s102, diagnóstico Fase-2: ~10/21 "synthesis-miss" eran chunks servidos ACREDITADOS que NO
        # portan el valor — TOC/colisiones léxicas): para hechos ANCLABLES, un chunk acreditado solo
        # cuenta si ADEMÁS porta el anchor (fact_match >= FLOOR-0.15, slack anti-FN). Los no-anclables
        # conservan el crédito semántico (no hay anchor que exigir — residual declarado).
        l1_killed: set = set()
        toc_killed: set = set()
        if anchorable and sup:
            keep = set()
            for cid in sup:
                _content = (by_id_pool.get(cid) or {}).get("content") or ""
                if not support_l1_guard_allows(
                    valor,
                    texto,
                    _content,
                    same_family=bool(family_resolved and same_family(cid)),
                ):
                    continue
                # H4 cerrado (s102): un ÍNDICE acreditado no es soporte por defecto — sus títulos
                # matchean el anchor sin portar el contenido (inflaba synthesis-miss). Va al MISMO
                # canal de kills re-adjudicables: un título de TOC sí puede soportar hechos
                # nominales ("Importar archivo de licencia (.bin)") y esos los decide la red dual.
                if is_toc_page(_content):
                    toc_killed.add(cid)
                    continue
                keep.add(cid)
            l1_killed = sup - keep      # incluye los TOC-kills (mismo rescate Opus + regla H1b)
            sup = keep
            # H1 (dúo s102): el anchor léxico NO reconoce variantes de notación ("6.800 Ω" ≠ '6K8') →
            # si L1 VACIÓ el soporte, Opus re-adjudica LOS CHUNKS MATADOS ("¿porta el valor en otra
            # notación?") — nunca aterrizar corpus/retrieval-limpio por un kill de notación.
            if not sup and l1_killed:
                killed_chunks = [by_id_pool[cid] for cid in l1_killed if by_id_pool.get(cid)]
                d1 = judge_support_dual(valor, texto, killed_chunks, workers=workers)
                if d1["sup"]:
                    sup = d1["sup"]
                    entry_l1_override = True
                else:
                    entry_l1_override = False
            else:
                entry_l1_override = None
        else:
            entry_l1_override = None
        # C3 (cross-model s101b): degradación PARCIAL del primario (un batch entero murió pero otros
        # votaron) → el hecho puede caer como falso miss SIN abortar. Flag por-fact visible.
        support_degraded = v_pool.get("n_fail", 0) >= K
        sup_fam = {cid for cid in sup if same_family(cid)}      # FAMILY-AWARE (fix #3)
        entry_support_flip = None
        if not sup_fam and anchorable:
            # DUAL-SOPORTE targeted (s101): SIN soporte same-family + candidato léxico en pool → Opus
            # adjudica (FN demostrado 6/7). Trigger sobre sup_fam (crít cross-model: sobre sup raw perdía
            # el caso "GPT acredita solo cross-family"). Candidatos ORDENADOS por score, cap declarado.
            candidate_scored = []
            for candidate in pipe["pool"]:
                priority = support_candidate_priority(
                    valor,
                    texto,
                    candidate.get("content") or "",
                    bool(family_resolved and same_family(candidate.get("id"))),
                )
                if priority is not None:
                    candidate_scored.append((priority, candidate))
            candidate_scored.sort(key=lambda item: item[0], reverse=True)
            lex = [candidate for _, candidate in candidate_scored]
            if lex:
                d2 = judge_support_dual(valor, texto, lex, workers=workers)
                truncated = len(lex) > SUPPORT_BATCH_CAP
                if d2["n_valid"] == 0:
                    # H3 (dúo): fallo TOTAL del 2º juez ≠ "agreed_none" — flag de ERROR visible
                    entry_support_flip = {"support_judge2_error": True,
                                          "support_judge2_n_fail": d2["n_fail"],
                                          "support_candidates_truncated": truncated}
                elif d2["sup"]:
                    sup = sup | d2["sup"]                        # UNIÓN (no reemplazo: sup podía tener cross-family)
                    sup_fam = {cid for cid in sup if same_family(cid)}
                    entry_support_flip = {"support_judge_disagreement": True,
                                          "support_judge2_votes": d2["votes"],
                                          "support_judge2_n_fail": d2["n_fail"],
                                          "support_candidates_truncated": truncated}
                else:
                    entry_support_flip = {"support_judge2_agreed_none": True,
                                          "support_judge2_n_fail": d2["n_fail"],
                                          "support_candidates_truncated": truncated}
        # SEÑALES UPSTREAM: sobre el pool-50 puro (semántica v2.2 INTACTA).
        in_topk = bool(sup_fam & topk_ids)
        in_pool = bool(sup_fam)
        # SEÑAL SERVIDA (s286e/cláusula 19): sobre la VISTA del generador — un hecho cuyo
        # ÚNICO soporte llega por una fila apendizada por coverage ya NO es invisible.
        sup_served, v_served = support_over_served(valor, texto, pipe, sup, workers=workers)
        sup_served_fam = {cid for cid in sup_served if same_family(cid)}
        served_support = sup_served_fam & served_ids
        reaches_gen = bool(served_support)
        via_coverage_append = bool(served_support) and served_support <= served_appended_ids

        entry = {"key": key, "valor": valor, "texto": texto, "lexically_anchorable": anchorable,
                 "family_resolved": family_resolved, "n_support_fam": len(sup_fam),
                 "n_support_raw": len(sup), "n_support_served": len(sup_served_fam),
                 "reaches_gen": reaches_gen, "in_topk": in_topk, "in_pool": in_pool}
        if via_coverage_append:
            entry["via_coverage_append"] = True
            entry["append_lanes"] = sorted(
                {str(pipe["appended_lane"].get(cid) or "?") for cid in served_support})
        if v_served.get("n_fail"):
            entry["served_support_votes_missing"] = v_served["n_fail"]
        if l1_killed:                                # H2: los kills de L1 VISIBLES (pre/post + ids)
            entry["support_l1_killed"] = sorted(l1_killed)[:6]
            entry["support_l1_override"] = entry_l1_override   # True=Opus restauró; False=confirmó kill
        if toc_killed:                               # H4: subconjunto matado por ser página de índice
            entry["support_toc_killed"] = sorted(toc_killed)[:6]
        if support_degraded:
            entry["support_judge_degraded"] = True   # >=K fallos del primario en este hecho — clase con FN-riesgo
        elif v_pool.get("n_fail", 0) and not reaches_gen:
            # M3 (cross-model s102): fallos PARCIALES del soporte + el hecho cae miss-side → el batch
            # del chunk-portador pudo quedar matemáticamente sin quorum. Flag visible (mitigado por
            # L1-crosscheck + dual-soporte targeted, pero NUNCA silencioso).
            entry["support_votes_missing"] = v_pool["n_fail"]
        if entry_support_flip:
            entry.update(entry_support_flip)

        if reaches_gen:
            conv = judge_conveyed21(valor, texto, pipe["answer"], workers=workers)
            if conv.get("n_fail", 0) >= K:      # primario muerto también en conveyed → abortar
                raise RuntimeError(f"{qid}/{valor[:20]}: juez conveyed primario MUERTO ({conv['n_fail']}/{K} fallos)")
            entry["conveyed_yes"] = conv["yes"]
            if conv["yes"] >= THRESH_FIRM:
                clase = "OK"
            else:
                # DUAL-JUDGE (s100): el miss del primario NO basta — Opus 4.8 adjudica.
                dual = judge_conveyed_dual(valor, texto, pipe["answer"], workers=workers)
                entry["conveyed_yes_judge2"] = dual["yes"]
                entry["judge2_n_fail"] = dual["n_fail"]
                if dual["n_valid"] == 0:              # H4b (dúo): fallo TOTAL del 2º juez = degradación
                    entry["judge2_error"] = True      # a pre-dual → flag VISIBLE, nunca silencioso
                elif dual["n_valid"] < K:
                    entry["judge2_partial"] = dual["n_valid"]   # C2: votos incompletos, umbral proporcional
                if dual.get("firm"):
                    clase = "OK"                      # desacuerdo resuelto a conveyed — flagged, no silencioso
                    entry["judge_disagreement"] = True
                else:
                    clase = "synthesis-miss"          # CONSENSO de miss (o borderline del 2º juez)
                    entry["borderline"] = THRESH_BAND <= max(conv["yes"], dual["yes"]) < THRESH_FIRM
                    if do_submotivo:
                        # el juez de sub-motivo debe ver EXACTAMENTE lo servido (excerpts en las
                        # filas de coverage), no el content completo del padre.
                        entry["submotivo"] = submotivo_synthesis(
                            valor, texto, [served_view(c) for c in pipe["served"]],
                            pipe["answer"], served_support, workers=workers)
                    synth_miss_refs.append(entry)
        elif in_topk:
            clase = "synthesis-miss"     # en top-k pero cayó por RELEVANCE_THRESHOLD (raro, fix H)
            entry["submotivo"] = {"submotivo": "threshold-drop", "nota": "en top-k pero <RELEVANCE_THRESHOLD"}
        elif in_pool:
            clase = "rerank-miss"        # r2-3: la señal UPSTREAM manda sobre append_view_truncated
            entry["best_pool_rank"] = pool_rank_of(sup_fam, pipe["pool_ids"])
            entry["submotivo"] = submotivo_rerank(entry["best_pool_rank"], RERANK_TOP_K)
        elif (append_truncated := (
                {cid for cid in support_over_append_content(valor, texto, pipe, workers)[0]
                 if same_family(cid)} & served_appended_ids)):
            # s286e/r2-3: el valor SÍ está en una fila que coverage apendizó y que se sirvió,
            # pero fuera de las cards que el generador ve → gap de EXCERPT de lane (ni retrieval
            # ni síntesis-LLM). SUB-MOTIVO de synthesis-miss (precedente exacto: threshold-drop,
            # que también vive ahí aunque el generador no viera el valor). Las 5 clases
            # terminales quedan INTACTAS; sin esta traza la campaña apuntaría al lever equivocado.
            clase = "synthesis-miss"
            entry["submotivo"] = {
                "submotivo": "append_view_truncated",
                "nota": "valor en el content del append servido pero fuera de coverage_context_content",
                "chunk_ids": sorted(append_truncated)[:6],
                "lanes": sorted({str(pipe["appended_lane"].get(cid) or "?")
                                 for cid in append_truncated})}
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
                if l1_killed:                        # H1b: aterrizaje post-L1-kill JAMÁS es "limpio"
                    entry["corpus_gap"]["suspect_fn_mine"] = True
                    entry["corpus_gap"]["l1_killed_support"] = True

        entry["clase"] = clase
        hist[clase] += 1
        facts_out.append(entry)

    # ── STABILITY (absorbe synthesis_stability, gateado a synth-miss dual-confirmado) ──
    # fix dúo dual-judge #4: las reps se adjudican con el MISMO árbitro dual (GPT → si miss, Opus),
    # no GPT-solo — si no, "stable-miss" significaría "estable para GPT", no estable bajo el instrumento.
    if do_stability and synth_miss_refs:
        # s286e/cláusula 6: las reps regeneran desde la COMPOSICIÓN SERVIDA (prefijo + appends
        # del turno primario), no desde el topk — si no, la estabilidad se mediría sobre una
        # composición que el generador nunca vio.
        ans_reps = [gen_answer_only(gold["question"], pipe["chunks"]) for _ in range(K_STAB - 1)]
        def _rep_is_miss(valor, texto, ans):
            if judge_conveyed21(valor, texto, ans, workers=workers)["yes"] >= THRESH_FIRM:
                return False
            d = judge_conveyed_dual(valor, texto, ans, workers=workers)
            return not d.get("firm")                  # misma regla proporcional que la clasificación (C2)
        for e in synth_miss_refs:
            misses = [_rep_is_miss(e["valor"], e["texto"], a) for a in ans_reps]
            e["stability"] = "stable-miss" if all(misses) else "flip"   # MISS en todas las reps = estructural

    return {"qid": qid, "question": gold["question"], "answer": pipe["answer"],
            "family_resolved": family_resolved, "gold_families": sorted(gfam),
            "n_non_anchorable": n_non_anchorable,
            "pool_n": len(pipe["pool"]), "served_n": len(pipe["served"]), "topk_n": len(pipe["topk"]),
            "appended_n": len(pipe["appended"]),
            # SA3 (dúo s102/L4): PERSISTIR la composición servida — el rerank es no-determinista a
            # temp=0 (DEC-096b) y sin estos ids una composición-que-falla no es replayable (el fork
            # serving-vs-prompt de cat021 quedó indecidible por no tenerlos). Provenance pura.
            "topk_ids": [c.get("id") for c in pipe["topk"]],
            "served_ids": [c.get("id") for c in pipe["served"]],
            # s286e: traza del seam — qué apendizó coverage, por qué lane, y si la lane erroreó.
            "appended_ids": pipe["appended_ids"],
            "appended_lane": pipe["appended_lane"],
            "coverage_status": pipe["coverage_status"],
            "coverage_degraded": pipe["coverage_degraded"],
            "hist": hist, "facts": facts_out}


# ── eje SEPARADO gold/juez: reconstruye el blocker-primario por-gold (fix D, absorbe s87_rootcause) ──
# NO pre-carga el "~10/30 plateau" de DEC-075 (CADUCO) — lo re-deriva. ADVISORY: usa veredictos de un
# bvg PREVIO (no fresco) → orientativo, no zanja (el PASS fresco = eval caro diferido, gate Alberto).
BLOCKER_ORDER = ["corpus-gap", "retrieval-miss", "rerank-miss", "synthesis-miss"]  # más-abajo-primero
def gold_juez_axis(per_gold: list[dict], bvg: dict) -> list[dict]:
    axis = []
    for r in per_gold:
        if r.get("coverage_degraded"):
            # M3/cláusula 4: coverage erroreó tras el retry → el gold NO alimenta ninguna
            # inferencia (ni blocker-primario ni radio). Estampado, contado aparte, excluido.
            continue
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


# ── freeze-contract del CÓDIGO: closure de imports del seam (s286e/r2-2) ──────────────
# v2.2 hasheaba una lista A MANO (retriever/reranker/generator) y era ciega a coverage:
# un árbol sucio en post_rerank/lanes reutilizaba un `.partial` incompatible (clase s101b).
# El closure se DERIVA de los imports (AST, sin ejecutar) desde las raíces del seam, así que
# una lane nueva entra sola.
# Raíces = el seam + el perfil de release + los CUATRO adapters que este script inyecta
# (retriever/reranker/generator/shadow: el trío que v2.2 ya hasheaba NO se pierde).
_SEAM_ROOTS = ("src/rag/serving_pipeline.py", "src/rag/post_rerank_coverage.py",
               "src/release_profiles.py", "src/rag/retriever.py", "src/rag/reranker.py",
               "src/rag/generator.py", "src/rag/structural_neighbor_shadow.py")
_ASSET_SUFFIXES = (".yaml", ".yml", ".json", ".jsonl")


def _module_relpath(dotted: str) -> str | None:
    parts = dotted.split(".")
    for candidate in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
        if (ROOT / candidate).is_file():
            return candidate
    return None


def _imported_modules(relative: str, tree: ast.AST) -> list[str]:
    """Módulos LOCALES importados por un fichero (absolutos `src.*` y relativos `.x`)."""
    package = relative.rsplit("/", 1)[0].replace("/", ".")
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                       # relativo: sube `level-1` paquetes
                base_parts = package.split(".")
                base = ".".join(base_parts[: len(base_parts) - (node.level - 1)] or base_parts)
            else:
                base = ""
            module = ".".join(p for p in (base, node.module or "") if p)
            if module:
                found.append(module)
            found.extend(".".join(p for p in (module, alias.name) if p) for alias in node.names)
    return found


def seam_code_closure() -> list[str]:
    """Ficheros de código alcanzables desde el seam, en orden ESTABLE (sorted)."""
    seen: set[str] = set()
    pending = list(_SEAM_ROOTS)
    while pending:
        relative = pending.pop()
        if relative in seen or not (ROOT / relative).is_file():
            continue
        seen.add(relative)
        try:
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8", errors="replace"),
                             filename=relative)
        except SyntaxError:
            continue
        for dotted in _imported_modules(relative, tree):
            resolved = _module_relpath(dotted)
            if resolved and resolved not in seen:
                pending.append(resolved)
    return sorted(seen)


def seam_config_assets(modules: list[str]) -> list[str]:
    """Configs versionadas que ese código consume (los `config/*.yaml` de las lanes).
    Se derivan de los literales de ruta del propio código — no de una lista a mano."""
    assets: set[str] = set()
    for relative in modules:
        try:
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8", errors="replace"),
                             filename=relative)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            literal = node.value.strip().replace("\\", "/")
            if not literal or literal.startswith("/") or ".." in literal:
                continue
            # Docstrings también son ast.Constant str: con saltos de línea o longitud
            # no-de-ruta, stat() revienta en Linux (ENAMETOOLONG; Windows lo ignora).
            if "\n" in literal or len(literal) > 200:
                continue
            for candidate in (literal, f"config/{literal}"):
                path = ROOT / candidate
                if candidate.endswith(_ASSET_SUFFIXES) and path.is_file():
                    assets.add(candidate)
                    break
                if path.is_dir() and str(path).startswith(str(ROOT / "config")):
                    assets.update(
                        str(child.relative_to(ROOT)).replace("\\", "/")
                        for child in sorted(path.rglob("*"))
                        if child.is_file() and child.name.endswith(_ASSET_SUFFIXES)
                    )
                    break
    return sorted(assets)


def pipeline_fingerprint() -> dict:
    """sha del closure de código + assets del seam (entra en el freeze-hash del run)."""
    modules = seam_code_closure()
    assets = seam_config_assets(modules)
    blob = "".join((ROOT / relative).read_text(encoding="utf-8", errors="replace")
                   for relative in [*modules, *assets])
    return {"sha": _sha(blob), "n_modules": len(modules), "n_assets": len(assets),
            "modules": modules, "assets": assets}


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
        "route": "eval-harness CRUZANDO EL SEAM (execute_rag_turn; sin target_models, rerank strict, "
                 "available_models=None) — espejo funcional de bvg/test_bot_vs_gold:run_bot (s286e/v3)",
        "instrument_version": INSTRUMENT_VERSION,
        "git_commit": commit,
        "release_profile": COVERAGE_RELEASE_POLICY.profile,
        "corpus": corpus_fingerprint(),
        "pipeline_closure": pipeline_fingerprint(),
        "flags_demo": dict(DEMO_FLAGS),
        "flags_source": "6 overrides Railway DEC-asserted (valores enmascarados en dashboard) + defaults de código "
                        "+ los 7 flags-hoja del seam y STRUCTURAL_NEIGHBOR_SHADOW pineados off (s286e/r2-1)",
        "resolved": {"RETRIEVAL_TOP_K": RETRIEVAL_TOP_K, "RERANK_TOP_K": RERANK_TOP_K,
                     "LLM_MAX_TOKENS": LLM_MAX_TOKENS, "LLM_MODEL": LLM_MODEL,
                     "RELEVANCE_THRESHOLD": RELEVANCE_THRESHOLD, "RERANKER_BACKEND": RERANKER_BACKEND,
                     "MERGE_STRATEGY": MERGE_STRATEGY, "RERANK_PREVIEW_CHARS": RERANK_PREVIEW_CHARS,
                     "GENERATOR_INCLUDE_CONTEXT": gic},
        "judge": {"model": JUDGE_MODEL, "K": K, "K_stability": K_STAB,
                  "judge2_model": JUDGE2_MODEL,
                  "judge2_rule": "dual-consensus: synthesis-miss requiere miss de AMBOS; Opus>=4/5 => OK flagged judge_disagreement (suite s100: 5 flips FN, 0 FP fakes)",
                  "support_dual_rule": f"targeted-lexical (s101): sup_fam=∅ + fact_match>=SCORE_FLOOR({SCORE_FLOOR}) en pool => Opus K={K} re-juzga candidatos ordenados por score cap {SUPPORT_BATCH_CAP} (truncation flagged); flip=UNION flagged support_judge_disagreement (evidencia: evals/s101_inpool_adjudication.json 6/7 supports, 0/18 refuters). Residual no-léxico sigue single",
                  "support_sha": _sha(SUPPORT_SYS + SUPPORT_USER),
                  "conveyed_sha": _sha(CONVEY_SYS + CONVEY21_USER) + f"-v2.1cap{CONVEY21_ANSWER_CAP}",
                  "support_l1_rule": f"anchorable: crédito solo si fact_match>=FLOOR-0.15 en el chunk acreditado (anti TOC/colisión, s102-L1)",
                  "submotivo_sha": _sha(SUBMOTIVO_SYS + SUBMOTIVO_USER)},
        "similarity_note": "pin de pool NO estampa `similarity` como fiel: stamp plano léxico "
                           "(retriever.py:554) ≠ coseno (fix G).",
        "diversify_tiebreak": "flag VIVO en el código (portado s101 para la re-medición) pero PINEADO "
                              "off en DEMO_FLAGS; NO-GO definitivo s101 (tripwire con ambos anchos) — jamás a demo.",
        "hyq_pilot": "seam VIVO (s101) pineado '' (off); piloto GO del mecanismo, ship gated (D2 Alberto).",
        "family_aware": "acreditación de soporte SAME-FAMILY vía product_model (fix #3, reusa retrieval_miss_famtie).",
        "support_split": "s286e/cláusula 19: sup_pool (pool-50) alimenta in_pool/in_topk/pool_rank y las "
                         "clases upstream; sup_served (vista del generador, coverage_context_content en las "
                         "filas de coverage validadas) alimenta reaches_gen y el conveyed-check.",
        "served_view": "admitted_evidence_rows() importado de src/rag/generator.py — MISMA función que el "
                       "generador usa (r2-4: fuente única, cero espejo que pueda derivar).",
        "series_note": "v3 = SERIE NUEVA. Un v3 y un v2.2 del mismo día son fotos distintas (composición "
                       "servida distinta + rerank no determinista), NO la medición causal del seam.",
    }


def estimate_cost(n_golds: int, avg_facts: float = 3.2) -> str:
    n_facts = int(n_golds * avg_facts)
    support = n_facts * K * 7            # TODOS los facts (fix v3): ~7 batches (pool-50/BATCH≈7) × K
    conveyed = int(n_facts * 0.7) * K    # los reaches_gen (~70%)
    submotivo = int(n_facts * 0.25) * K
    stability = int(n_facts * 0.25) * (K_STAB - 1) * (1 + K)   # 1 gen + K conveyed por synth-miss
    sem_corpus = int(n_facts * 0.15) * K * 3   # no-anclables-no-en-pool (~15%) × K × 3 batches acotados
    judge2 = int(n_facts * 0.3) * K            # dual-judge Opus: K por cada miss del primario (~30%)
    support2 = int(n_facts * 0.12) * K         # dual-soporte Opus: K por fact sin soporte same-family (~12%)
    # s286e: el eje SERVIDO (cláusula 19). Solo se juzga fresco lo que difiere del pool = los
    # appends de coverage (<=4 filas => 1 batch × K), y solo donde alguna lane apendizó (~50%).
    # El pase de content-completo del append (append_view_truncated) está gateado a los facts que
    # llegan a esa rama (~10%). Ambos son marginales frente al pase de pool (7 batches × K).
    served_support = int(n_facts * 0.5) * K
    append_full = int(n_facts * 0.1) * K
    calls = (support + conveyed + submotivo + stability + sem_corpus + judge2 + support2
             + served_support + append_full)
    usd = calls * 0.004
    return (f"~{n_golds} golds × ~{avg_facts} facts ≈ {n_facts} hechos · ~{calls} llamadas "
            f"(support≈{support}, served-support≈{served_support}, conveyed≈{conveyed}, "
            f"judge2≈{judge2}, submotivo≈{submotivo}, stability≈{stability}, "
            f"sem-corpus≈{sem_corpus}, append-full≈{append_full}) · ≈ ${usd:.0f}")


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

    # ESPEJO del paso de validación del contrato de release de bvg (test_bot_vs_gold.py:236-237):
    # medir con un contrato de release inválido (perfil sin lane, lane-hoja encendida contra
    # coverage_c1_v4, identity ≠ replace) produciría una foto de OTRA stack. Fail-fast, no warning.
    validate_config(require_telegram=False, production=True)
    assert _isv2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"

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

    print(f"factlevel_assessment {INSTRUMENT_VERSION} · mode={args.mode} · {len(qids)} golds · "
          f"RUTA HARNESS CRUZANDO EL SEAM (execute_rag_turn, sin target_models) · "
          f"profile={COVERAGE_RELEASE_POLICY.profile}")
    print(f"  DEMO flags: RERANK_TOP_K={RERANK_TOP_K} LLM_MAX_TOKENS={LLM_MAX_TOKENS} "
          f"ENUNCIADOS={os.environ.get('ENUNCIADOS_MULTIVECTOR')} "
          f"IDENTITY={os.environ.get('IDENTITY_RESOLVE')}/{os.environ.get('IDENTITY_RESOLVE_POLICY')} CHUNKS={CHUNKS_TABLE}")
    print(f"  coste estimado: {estimate_cost(len(qids))}")
    if bvg:
        print(f"  ⚠ eje gold/juez ADVISORY (veredictos de {bvg_path.name}, bvg previo — no zanja)")
    manifest = build_manifest()
    print(f"  manifest: commit={manifest['git_commit']} corpus={manifest['corpus']}")
    # fix dúo build2 #5 + dúo dual-judge #1: freeze-hash del run → el .partial se auto-invalida si cambió
    # CUALQUIERA de corpus/flags/juez/código (el corpus INCLUIDO: sin él, un fix de chunks con el mismo
    # commit reusaría un partial incompatible — justo el caso hp011).
    gold_sha = _sha((ROOT / "evals" / "gold_answers_v1.yaml").read_text(encoding="utf-8", errors="replace"))
    # árbol sucio: ancla el código de ESTE script + el del PIPELINE que se mide (crít cross-model s101b:
    # un cambio en retriever/reranker/generator con el mismo commit reutilizaría un partial incompatible).
    # s286e/r2-2: ya NO es una lista a mano — es el CLOSURE DE IMPORTS del seam + sus configs.
    pipe_sha = manifest["pipeline_closure"]["sha"]
    script_sha = _sha(Path(__file__).read_text(encoding="utf-8", errors="replace"))
    freeze_hash = _sha(json.dumps({"c": manifest["git_commit"], "f": manifest["flags_demo"],
                                   "r": manifest["resolved"], "j": manifest["judge"],
                                   "corpus": manifest["corpus"],
                                   "golds": gold_sha, "script": script_sha,
                                   "pipeline": pipe_sha,
                                   "cli": {"submotivo": not args.no_submotivo,      # M4: los flags CLI
                                           "stability": not args.no_stability}}, sort_keys=True))
    if "error" in manifest["corpus"]:
        print("  ⚠ corpus fingerprint FALLÓ — el freeze-hash no ancla el corpus este run")

    # s286c: el path histórico s100_factlevel_full.yaml es INSUMO CONGELADO (sha-pineado)
    # del linaje s108/s112/s201 — sobrescribirlo rompió CI. Runs nuevos SIEMPRE con tag
    # (default = fecha) para no pisar artefactos consumidos; el histórico no se toca.
    # s286e/m10: el tag lleva la VERSIÓN del instrumento — un v3 y un v2.2 del mismo día son
    # series distintas y no pueden colisionar en el mismo fichero.
    output_tag = os.getenv("FACTLEVEL_OUTPUT_TAG") or f"v3_{time.strftime('%Y%m%d')}"
    out_path = OUT_DIR / f"s100_factlevel_{args.mode}_{output_tag}.yaml"
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
            deg = " ⚠coverage_degraded" if r.get("coverage_degraded") else ""
            app = f" +{r.get('appended_n', 0)}app" if r.get("appended_n") else ""
            print(f"  [{qid}]{fam}{deg}{app} {time.time()-t0:4.0f}s · OK={h['OK']} synth={h['synthesis-miss']} "
                  f"rerank={h['rerank-miss']} retr={h['retrieval-miss']} corpus={h['corpus-gap']} "
                  f"meta={h['meta-ref']} (nonanch={r.get('n_non_anchorable',0)})")

    # cláusula 4: los golds con coverage degradado NO entran en el histograma — contador propio.
    scored_golds = [r for r in per_gold if not r.get("coverage_degraded")]
    degraded_golds = [r["qid"] for r in per_gold if r.get("coverage_degraded")]
    agg = {k: 0 for k in ("OK", "synthesis-miss", "rerank-miss", "retrieval-miss",
                          "corpus-gap", "meta-ref")}
    for r in scored_golds:
        for k2, v in r["hist"].items():
            agg[k2] += v
    # s286e: los dos contadores que reconcilian las etapas del mapa (r2-3).
    n_via_append = sum(1 for r in scored_golds for f in r["facts"] if f.get("via_coverage_append"))
    n_append_truncated = sum(1 for r in scored_golds for f in r["facts"]
                             if isinstance(f.get("submotivo"), dict)
                             and f["submotivo"].get("submotivo") == "append_view_truncated")
    n_appended_rows = sum(r.get("appended_n", 0) for r in scored_golds)
    axis = gold_juez_axis(per_gold, bvg)
    n_perp = sum(1 for a in axis if a["no_pass_perp_pipeline"])
    # denominadores COHERENTES con el histograma (los degradados no entran en ninguno)
    n_unresolved = sum(1 for r in scored_golds if not r["family_resolved"])
    n_non_anchorable = sum(r.get("n_non_anchorable", 0) for r in scored_golds)
    judge_flips = [(r["qid"], f["valor"]) for r in per_gold for f in r["facts"]
                   if f.get("judge_disagreement")]
    n_judge2_err = sum(1 for r in per_gold for f in r["facts"]
                       if f.get("judge2_error") or f.get("support_judge2_error"))
    n_judge2_fails = sum(f.get("judge2_n_fail", 0) + f.get("support_judge2_n_fail", 0)
                         for r in per_gold for f in r["facts"])
    support_flips = [(r["qid"], f["valor"]) for r in per_gold for f in r["facts"]
                     if f.get("support_judge_disagreement")]

    result = {"instrument": INSTRUMENT_VERSION,
              "manifest": manifest, "mode": args.mode, "n_golds": len(per_gold),
              "n_golds_scored": len(scored_golds),
              "aggregate_hist": agg, "gold_juez_axis": axis, "gold_juez_advisory": bool(bvg),
              "n_no_pass_perp_pipeline": n_perp, "n_family_unresolved": n_unresolved,
              "n_non_anchorable": n_non_anchorable,
              # s286e: la traza del seam publicada en la fila del scoreboard
              "n_via_coverage_append": n_via_append,
              "n_append_view_truncated": n_append_truncated,
              "n_coverage_appended_rows": n_appended_rows,
              "n_coverage_degraded": len(degraded_golds),
              "coverage_degraded_qids": degraded_golds,
              "judge_disagreements": [{"qid": q, "valor": v} for q, v in judge_flips],
              "support_disagreements": [{"qid": q, "valor": v} for q, v in support_flips],
              "per_gold": per_gold}
    out_path.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print("\n── AGREGADO (hechos a nivel-pipeline, family-aware · TODOS los facts clasificados, fix v3) ──")
    total_c = sum(agg[c] for c in agg if c != "meta-ref")
    for c in ["OK", "synthesis-miss", "rerank-miss", "retrieval-miss", "corpus-gap"]:
        print(f"  {c:16s} {agg[c]:3d}  ({100*agg[c]/max(total_c,1):.0f}% de clasificados)")
    print(f"  {'meta-ref':16s} {agg['meta-ref']:3d} (puntero, fuera del histograma)")
    print(f"  no-anclables-léxicamente: {n_non_anchorable}/{total_c} facts (clasificados vía juez SEMÁNTICO, no filtrados)")
    # ── s286e: lo que la ruta v2.2 NO podía ver ──
    print(f"  via_coverage_append:    {n_via_append:3d} facts cuyo ÚNICO soporte servido llega por una "
          f"fila apendizada por coverage ({n_appended_rows} filas apendizadas en total)")
    print(f"  append_view_truncated:  {n_append_truncated:3d} facts con el valor en el content del append "
          f"pero FUERA de sus excerpts servidos (sub-motivo de synthesis-miss; lever de EXCERPT de lane)")
    print(f"  coverage_degraded:      {len(degraded_golds):3d} golds excluidos del histograma "
          f"(coverage erroreó tras retry): {degraded_golds}")
    print(f"  family-unresolved: {n_unresolved} golds (soporte NO family-filtrado ahí)")
    print(f"  dual-judge: {len(judge_flips)} desacuerdos resueltos a OK (GPT-miss/Opus-conveyed): "
          f"{[f'{q}:{str(v)[:18]}' for q, v in judge_flips]}")
    print(f"  dual-soporte: {len(support_flips)} flips (sup=∅→Opus acredita candidato léxico): "
          f"{[f'{q}:{str(v)[:18]}' for q, v in support_flips]}")
    if n_judge2_err or n_judge2_fails:
        print(f"  ⚠ judge2: {n_judge2_err} facts con fallo TOTAL (degradación a pre-dual) · "
              f"{n_judge2_fails} votos fallidos en total — si es alto, revisar API/modelo ANTES de fiarse del synth-miss")
    # comparabilidad v1: synth-miss_v1-equivalente = synth-miss_v2 + judge_disagreements (H1 dúo)
    print(f"  flips-dual listados para spot-check regla-C (juez v2.1: la equivalencia-v1 YA no se reconstruye — rúbrica cambió)")
    print(f"  eje gold/juez (ADVISORY): {n_perp} golds NO-PASS ⊥ pipeline (DEC-075 caduco, re-derivado)")
    print(f"\n→ {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
