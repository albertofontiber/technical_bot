#!/usr/bin/env python3
"""Run the eval set in evals/baseline_v1.yaml against the live RAG stack.

Pipeline per question (mirrors what telegram_bot.py does, minus UI):
  1. retrieve_chunks(query) — vector + keyword search
  2. rerank_chunks(query, chunks) — Claude relevance reranking
  3. generate_answer(query, reranked) — Claude final answer + diagrams

Scoring (heuristic v1 — a human pass is still needed for trust):
  - expected_behavior:
      answer              → answer doesn't predominantly ask back / admit ignorance
      ask_clarification   → answer contains a clarifying question
      admit_no_info       → answer says "no tengo / no dispongo / no encuentro"
  - expected_keywords    → every keyword must appear (substring, lowercased)
  - forbidden_keywords   → none may appear
  - expected_has_diagram → len(diagrams) > 0 must match
  - expected_sources     → (loose) at least one source_file in citations

Usage:
  python scripts/run_eval.py                       # full eval, default YAML
  python scripts/run_eval.py --input path/to.yaml
  python scripts/run_eval.py --only hp001,am003    # run a subset
  python scripts/run_eval.py --categories happy_path,not_in_db
  python scripts/run_eval.py --dry-run             # skip LLM calls; only print plan

Output:
  logs/eval_<timestamp>.json — full results per question + aggregate scores
  stdout                     — human-readable summary grouped by category
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Note: the stdout re-wrap and .env bootstrap run only in __main__ so this
# module can be imported for unit-testing the scoring helpers without
# side effects (closing pytest's captured stdout, requiring env vars, etc.).
try:
    import yaml  # noqa: E402
except ImportError:  # pragma: no cover — only hit when yaml is missing at runtime
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Scoring heuristics
# ---------------------------------------------------------------------------
# Phrases that signal the bot is asking back (clarification)
_CLARIFY_PATTERNS = re.compile(
    r"(¿[^?]*(modelo|fabricante|cuál|qué|cual|que)[^?]*\?|"
    r"¿puedes (confirmar|indicar|especificar|aclarar|dar)|"
    r"necesito saber|dime el modelo|cuál (de los|de las)|"
    r"¿te refieres a|¿cuál de ([^?]+)\?)",
    re.IGNORECASE,
)

# Phrases that signal "I don't have that manual".
# Intentionally broad — if the bot makes any honest admission of not having
# the source material, that should count as admit_no_info regardless of the
# exact wording. Captured patterns (all case-insensitive):
#   - "no tengo (información|datos|manual(es)?|documentación|referencia) sobre/de/para/del"
#   - "no tengo (este|ese|el|la|esa) (manual|documentación|información|referencia)"
#   - "no dispongo de (información|manual|datos|documentación)"
#   - "no (encuentro|localizo|hallo) (información|manual|datos|documentación)"
#   - "no (está|aparece|figura) en (mi|la) (base|biblioteca|bd|documentación|base de datos)"
#   - "no figura en (los|mis) manuales"
#   - "no (puedo|tengo) (información|datos) sobre (este|ese|la|el) (producto|modelo|central|fabricante)"
#   - "no (es|está) (un fabricante|un modelo)? ?(incluido|cubierto|presente) en"
#   - "no cuento con (información|manual|documentación|datos)"
#   - "registrar(é|emos)? (este|el) (producto|modelo|fabricante)"
_NO_INFO_PATTERNS = re.compile(
    r"("
    r"no tengo (información|datos|manual(?:es)?|documentación|documentos|referencia|registro) (sobre|de|del|de la|para|acerca)|"
    r"no tengo (este|ese|el|la|esa) (manual|documentación|información|referencia)|"
    r"no dispongo de (información|manual|datos|documentación)|"
    r"no (encuentro|localizo|hallo) (información|manual|datos|documentación)|"
    r"no (está|aparece|figura) en (mi|la) (base|biblioteca|bd|documentación|base de datos)|"
    r"no figura en (los|mis) manuales|"
    r"no (puedo|tengo) (información|datos) sobre (este|ese|la|el) (producto|modelo|central|fabricante)|"
    r"no (es|está) (un fabricante |un modelo )?(incluido|cubierto|presente) en|"
    r"no cuento con (información|manual|documentación|datos)|"
    r"registrar(é|emos)? (este|el) (producto|modelo|fabricante)"
    r")",
    re.IGNORECASE,
)


# Signals that a response is a SUBSTANTIVE answer even when it carries a
# no-info caveat at the top. Discovered 20 abril 2026 auditing hp003, hp014,
# hp018: the bot opens with a hedge ("No dispongo de documentación específica
# del modelo exacto") and then delivers 5 numbered steps starting with
# imperative verbs + a Fuente: citation.
#
# The criteria below were iterated against the full eval log to avoid
# false positives: numbered lists of clarifying questions, numbered lists of
# infinitives like "1. Consultar el portal" (honest admissions with next
# steps), and product-code digits like "DBD-70A" do NOT count as procedural
# or technical evidence.

# Imperative Spanish verbs that the bot uses at the start of procedural steps.
# Must be imperative (acción concreta), not infinitive or question. These are
# the ones the generator actually produces per its system prompt.
_IMPERATIVE_VERBS = (
    r'(?:Conecta|Verifica|Instala|Identifica|Pulsa|Desconecta|Retira|'
    r'Comprueba|Sustituye|Configura|Ajusta|Coloca|Localiza|Inserta|'
    r'Mide|Prueba|Asegúrate|Accede|Selecciona|Presiona|Presióna|'
    r'Mantén|Revisa|Limpia|Reemplaza|Abre|Cierra|Activa|Desactiva|'
    r'Introduce|Guarda|Confirma|Cambia|Monta|Desmonta|Apaga|Enciende)'
)

# A real procedural step begins with a number ≥ 2, optional bold markers,
# then an imperative verb. Step 1 alone isn't enough (could be preamble);
# step ≥ 2 suggests a real multi-step procedure.
_PROCEDURAL_PATTERN = re.compile(
    # \b at the end prevents prefix matches (e.g. 'Revisa' matching 'Revisar').
    rf'(?mi)^\s*[2-9]\.\s+(?:\*\*)?{_IMPERATIVE_VERBS}\b'
)

# 'Fuente:' / 'Fuentes:' line — system prompt requires this for any real
# answer. Anchored to start-of-line; accepts optional markdown-bold markers
# because the generator renders it as '**Fuente:**' in ~30% of responses.
_CITATION_PATTERN = re.compile(r'(?im)^\s*\*{0,2}Fuentes?\s*:?\*{0,2}\s*\S')

# Minimum answer length to be considered substantive.
_SUBSTANTIVE_MIN_LEN = 600

# Too many '?'-terminated sentences means the response is primarily asking
# back, not answering — even if it also contains a procedure or citation.
# Empirical threshold from the baseline run: responses with ≥ 3 questions
# are overwhelmingly ask_clarification (mc005, am002-6, hp013, etc.); those
# with ≤ 2 are answer-with-follow-up (hp018, hp003).
_MAX_QUESTIONS_FOR_ANSWER = 2


def _count_questions(answer: str) -> int:
    return answer.count('?')


def is_substantive_answer(answer: str) -> bool:
    """True when the response delivers actionable content even with caveats.

    Requires length + imperative-verb procedure + citation, AND the response
    must not be dominated by clarifying questions. A pure no-info admission
    (even if long) fails the procedure+citation test; a clarification block
    (many '?'s) fails the question-count test.
    """
    if len(answer) < _SUBSTANTIVE_MIN_LEN:
        return False
    if _count_questions(answer) > _MAX_QUESTIONS_FOR_ANSWER:
        return False
    # BOTH procedure AND citation required — this is the conservative AND
    # (not OR) so that honest no-info responses that cite the empty corpus
    # or list alternative resources don't slip through as 'answer'.
    return bool(_PROCEDURAL_PATTERN.search(answer)) and bool(_CITATION_PATTERN.search(answer))


def classify_behavior(answer: str) -> str:
    """Classify the bot's response style from text.

    Returns one of: 'answer', 'ask_clarification', 'admit_no_info'.

    Priority: a substantive answer (procedure / values / citation, long
    enough) wins over a no-info match. Only short or purely-hedge responses
    fall through to the no-info / clarify detectors. Prevents false
    admit_no_info flags when the bot delivers a full answer after a caveat.
    """
    if is_substantive_answer(answer):
        return "answer"
    if _NO_INFO_PATTERNS.search(answer):
        return "admit_no_info"
    if _CLARIFY_PATTERNS.search(answer):
        return "ask_clarification"
    return "answer"


def score_keywords(answer: str, expected: list[str]) -> tuple[int, int, list[str]]:
    """Return (hits, total, missing). Substring match, lowercased.

    Entries with '|' are treated as OR: 'manual|documentación' counts as hit
    if either alternative appears in the answer. Use to accept legitimate
    synonyms (ex: bot may say 'documentación' instead of 'manual') without
    inflating the expected_keywords list.
    """
    if not expected:
        return 0, 0, []
    a = answer.lower()
    missing: list[str] = []
    for kw in expected:
        alternatives = [alt.strip() for alt in kw.lower().split("|") if alt.strip()]
        if not any(alt in a for alt in alternatives):
            missing.append(kw)
    return len(expected) - len(missing), len(expected), missing


def score_forbidden(answer: str, forbidden: list[str]) -> list[str]:
    """Return list of forbidden keywords that DID appear (violations)."""
    if not forbidden:
        return []
    a = answer.lower()
    return [kw for kw in forbidden if kw.lower() in a]


def score_sources(citations_text: str, expected: list[str]) -> int:
    """Number of expected source substrings that appear in citations. 0 if none expected."""
    if not expected or not citations_text:
        return 0
    c = citations_text.lower()
    return sum(1 for s in expected if s.lower() in c)


# ---------------------------------------------------------------------------
# LLM-as-judge scoring (20 abril 2026)
# ---------------------------------------------------------------------------
# Keyword-match scoring is brittle: the bot can answer correctly using a
# synonym the YAML author didn't anticipate (Ω vs ohm, 'anular' vs 'aislar').
# Calibrating keyword lists requires PCI domain expertise we don't have
# in-house during M&A. The industry-standard alternative is LLM-as-judge:
# a second LLM reads (question, retrieved_chunks, bot_answer) and judges
# whether the answer is faithful to the chunks, relevant to the question,
# helpful to a technician, and appropriately honest when info is missing.
#
# Judge output is ADDITIVE to keyword scoring — both are computed and
# stored per question, so we can compare judge agreement with keyword
# PASS on a small human-verified gold subset.

JUDGE_MODEL = "claude-sonnet-4-6"  # different from LLM_MODEL is ideal; we only have Claude
JUDGE_MAX_TOKENS = 800

JUDGE_PROMPT = """Eres el evaluador de un chatbot técnico que ayuda a técnicos de protección contra incendios (PCI). Tu trabajo es juzgar UNA respuesta del bot contra los fragmentos de manual que tenía disponibles.

PREGUNTA DEL TÉCNICO:
{question}

CONDUCTA ESPERADA: {expected_behavior}
- 'answer' → el bot debe responder directamente porque tiene información suficiente.
- 'ask_clarification' → la pregunta es ambigua; el bot debe pedir UN detalle concreto antes de responder.
- 'admit_no_info' → el producto/fabricante no está cubierto; el bot debe decir "no tengo este manual" sin inventar.

FRAGMENTOS RECUPERADOS (las ÚNICAS fuentes a las que el bot tenía acceso):
{chunks}

RESPUESTA DEL BOT:
{answer}

Evalúa CINCO criterios, cada uno con true/false, y un veredicto overall_pass.

1. faithful: ¿TODAS las afirmaciones técnicas concretas (valores, procedimientos, nombres de terminales, etc.) están soportadas por los fragmentos? Una afirmación no soportada = false, aunque suene correcta.
2. relevant: ¿la respuesta aborda lo que el técnico preguntó, o se desvía a otro tema?
3. helpful: ¿el técnico puede ACTUAR con esta respuesta, o es un "no sé" vacío cuando sí había info disponible en los fragmentos?
4. honest: ¿el bot admite cuando falta información, o inventa para disimular? Si había info en los fragmentos y la ignora, también es deshonesto.
5. behavior_match: ¿la conducta observada del bot coincide con la esperada arriba?

overall_pass = (faithful AND relevant AND helpful AND honest AND behavior_match)

Responde ÚNICAMENTE con un JSON en este formato:
{{
  "faithful": true|false,
  "relevant": true|false,
  "helpful": true|false,
  "honest": true|false,
  "behavior_match": true|false,
  "overall_pass": true|false,
  "rationale": "una o dos frases explicando el juicio"
}}"""


def _format_chunks_for_judge(chunks_used: list[dict], full_chunks: list[dict] | None = None) -> str:
    """Render chunks compactly for the judge prompt.

    Prefers full_chunks (with content) if passed — chunks_used only has
    metadata (source_file, product_model, similarity). For the per-question
    trace we'd need to re-run retrieval to get content; cheaper path is
    to pass the run_single reranked list forward when available.
    """
    src = full_chunks if full_chunks else chunks_used
    if not src:
        return "(ningún fragmento recuperado)"
    lines = []
    for i, c in enumerate(src[:6]):
        pm = c.get("product_model", "?")
        sf = c.get("source_file", "?")
        sec = c.get("section_title") or ""
        content = c.get("content", "")
        # Keep preview bounded — judge doesn't need full content, just enough
        # to verify claims against.
        preview = content[:500] if content else "(sin contenido almacenado)"
        lines.append(
            f"[Fragmento {i+1}] Producto: {pm} | Sección: {sec[:60]} | Fuente: {sf}\n{preview}"
        )
    return "\n\n".join(lines)


def score_llm_judge(
    question: dict,
    answer: str,
    chunks_for_judge: list[dict],
) -> dict:
    """Ask Claude (as judge) to evaluate the bot's answer on 5 criteria.

    Returns dict with faithful/relevant/helpful/honest/behavior_match/overall_pass/rationale.
    On error, returns a dict with 'judge_error' populated; callers should not
    treat that as either PASS or FAIL — it's a measurement failure.
    """
    import anthropic  # local import so --dry-run doesn't require the SDK
    import os

    prompt = JUDGE_PROMPT.format(
        question=question.get("question", ""),
        expected_behavior=question.get("expected_behavior", "answer"),
        chunks=_format_chunks_for_judge(chunks_for_judge),
        answer=answer,
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=JUDGE_MAX_TOKENS,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        verdict = json.loads(raw)
        # Defensive: ensure all expected keys, default to False if missing
        return {
            "faithful": bool(verdict.get("faithful", False)),
            "relevant": bool(verdict.get("relevant", False)),
            "helpful": bool(verdict.get("helpful", False)),
            "honest": bool(verdict.get("honest", False)),
            "behavior_match": bool(verdict.get("behavior_match", False)),
            "overall_pass": bool(verdict.get("overall_pass", False)),
            "rationale": str(verdict.get("rationale", ""))[:500],
        }
    except Exception as e:
        return {
            "judge_error": f"{type(e).__name__}: {e}",
            "faithful": None, "relevant": None, "helpful": None,
            "honest": None, "behavior_match": None, "overall_pass": None,
            "rationale": None,
        }


def score_question(q: dict, result: dict, run_judge: bool = False) -> dict:
    """Compute per-criterion scores for a single question.

    Returns dict with per-criterion booleans + overall pass/fail. When
    ``run_judge=True``, also invokes the LLM-as-judge and stores its
    verdict under key ``judge``.  The judge PASS is INFORMATIONAL in the
    returned dict (does not affect ``pass``) until we have a calibrated
    gold subset to trust it — compare both and iterate.
    """
    answer = result.get("answer", "")
    diagrams = result.get("diagrams", [])

    # Behavior
    observed_behavior = classify_behavior(answer)
    behavior_ok = observed_behavior == q.get("expected_behavior", "answer")

    # Keywords
    kw_hits, kw_total, kw_missing = score_keywords(answer, q.get("expected_keywords") or [])
    keywords_ok = kw_total == 0 or kw_missing == []

    # Forbidden
    violations = score_forbidden(answer, q.get("forbidden_keywords") or [])
    forbidden_ok = violations == []

    # Diagram presence
    expected_has_diag = q.get("expected_has_diagram")
    has_diag = len(diagrams) > 0
    if expected_has_diag is None:
        diagram_ok = True  # don't care
    else:
        diagram_ok = bool(expected_has_diag) == has_diag

    # Sources (loose, for info)
    citations_text = "\n".join(c.get("source_file", "") for c in result.get("chunks_used", []))
    src_hits = score_sources(citations_text, q.get("expected_sources") or [])

    # Overall pass: behavior + keywords + forbidden (diagram is informational)
    overall_pass = behavior_ok and keywords_ok and forbidden_ok

    out = {
        "observed_behavior": observed_behavior,
        "behavior_ok": behavior_ok,
        "keywords": {"hits": kw_hits, "total": kw_total, "missing": kw_missing, "ok": keywords_ok},
        "forbidden_violations": violations,
        "forbidden_ok": forbidden_ok,
        "has_diagram": has_diag,
        "diagram_ok": diagram_ok,
        "source_hits": src_hits,
        "pass": overall_pass,
    }

    if run_judge:
        # Pass the richer chunk list if run_single stored one; fall back to
        # the truncated chunks_used metadata otherwise.
        chunks_for_judge = result.get("chunks_full") or result.get("chunks_used") or []
        out["judge"] = score_llm_judge(q, answer, chunks_for_judge)

    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_single(q: dict, dry_run: bool = False) -> dict:
    """Execute the full retrieve → rerank → generate pipeline for one question."""
    if dry_run:
        return {
            "answer": "[dry-run — no LLM call]",
            "diagrams": [],
            "chunks_used": [],
            "timing": {"retrieve": 0, "rerank": 0, "generate": 0, "total": 0},
            "dry_run": True,
        }

    # Import lazily so --dry-run doesn't require full env vars
    from src.rag.retriever import (
        retrieve_chunks, extract_product_models, get_category_models,
    )
    from src.rag.reranker import rerank_chunks
    from src.rag.generator import generate_answer

    query = q["question"]
    t0 = time.time()
    chunks = retrieve_chunks(query)
    t_ret = time.time() - t0

    t0 = time.time()
    target_models = extract_product_models(query)
    reranked = rerank_chunks(query, chunks, target_models=target_models or None)
    t_rer = time.time() - t0

    t0 = time.time()
    # Best-effort: pass available_models for the detected category if any model hit
    available_models = None
    if target_models:
        # heuristic — category from first chunk if any, else skip
        cat = chunks[0].get("category") if chunks else None
        if cat:
            try:
                available_models = get_category_models(cat)
            except Exception:
                available_models = None
    gen = generate_answer(query, reranked, available_models=available_models)
    t_gen = time.time() - t0

    # had_relevant_chunks: did the retriever+reranker deliver at least one
    # chunk whose product_model loosely matches a detected target model?
    # Signal for TECH_DEBT #11b: lets us distinguish "retriever found
    # nothing" from "retriever found the right chunks but generator
    # admitted no-info anyway".
    n_relevant = 0
    if target_models:
        targets_lc = [m.lower() for m in target_models]
        for c in reranked:
            pm = (c.get("product_model") or "").lower()
            if not pm:
                continue
            if any(t in pm or pm in t for t in targets_lc):
                n_relevant += 1

    # chunks_full carries the reranked chunks WITH content for the LLM-as-judge
    # step downstream (scored ex-post in score_question). Not written to the
    # persisted JSON to keep logs compact — callers can opt in by setting
    # include_full_chunks_in_report=True when invoking main().
    chunks_full = [
        {"source_file": c.get("source_file"),
         "page_number": c.get("page_number"),
         "product_model": c.get("product_model"),
         "section_title": c.get("section_title"),
         "content_type": c.get("content_type"),
         "similarity": c.get("similarity"),
         "content": c.get("content", ""),
         "has_diagram": bool(c.get("has_diagram")),
        }
        for c in reranked
    ]

    return {
        "answer": gen.get("answer", ""),
        "diagrams": gen.get("diagrams", []),
        "chunks_used": [
            {"source_file": c.get("source_file"), "page": c.get("page_number"),
             "product_model": c.get("product_model"),
             "similarity": c.get("similarity")}
            for c in reranked[:6]
        ],
        "chunks_full": chunks_full,  # for judge; stripped from persisted JSON
        "target_models_detected": target_models,
        "n_chunks_retrieved": len(chunks),
        "n_chunks_reranked": len(reranked),
        "n_relevant_chunks_post_rerank": n_relevant,
        "had_relevant_chunks": n_relevant > 0,
        "timing": {
            "retrieve": round(t_ret, 2),
            "rerank": round(t_rer, 2),
            "generate": round(t_gen, 2),
            "total": round(t_ret + t_rer + t_gen, 2),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="evals/baseline_v1.yaml",
                    help="Path to the eval YAML")
    ap.add_argument("--only", default=None,
                    help="Comma-separated list of question ids to run (e.g. hp001,am003)")
    ap.add_argument("--categories", default=None,
                    help="Comma-separated list of categories to run")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip LLM calls; only print the plan")
    ap.add_argument("--judge", action="store_true",
                    help="Run LLM-as-judge on every answer in addition to "
                         "keyword scoring. Adds ~$0.02-0.05 per question.")
    ap.add_argument("--output-dir", default="logs",
                    help="Where to write the JSON report")
    args = ap.parse_args()

    yaml_path = ROOT / args.input
    if not yaml_path.exists():
        print(f"ERROR: eval file not found: {yaml_path}")
        return 1
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])

    # Filter
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        questions = [q for q in questions if q["id"] in wanted]
    if args.categories:
        cats = {s.strip() for s in args.categories.split(",") if s.strip()}
        questions = [q for q in questions if q.get("category") in cats]

    print(f"Loaded {len(questions)} question(s) from {yaml_path.name}")
    print(f"Mode: {'DRY-RUN (no LLM)' if args.dry_run else 'LIVE'}")
    print()

    results: list[dict] = []
    t_start = time.time()
    for i, q in enumerate(questions, 1):
        qid = q.get("id", f"q{i}")
        cat = q.get("category", "?")
        qtext = q.get("question", "")[:70]
        print(f"[{i}/{len(questions)}] {qid} ({cat})  {qtext}...")

        try:
            exec_result = run_single(q, dry_run=args.dry_run)
            if not args.dry_run:
                score = score_question(q, exec_result, run_judge=args.judge)
            else:
                score = {"pass": None, "dry_run": True}
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            traceback.print_exc(limit=2)
            exec_result = {"error": str(e), "type": type(e).__name__}
            score = {"pass": False, "error": True}

        status = (
            "DRY" if args.dry_run else
            ("PASS" if score.get("pass") else "FAIL")
        )
        judge_str = ""
        if args.judge and score.get("judge"):
            j = score["judge"]
            if j.get("judge_error"):
                judge_str = f" | judge=ERR"
            else:
                jp = j.get("overall_pass")
                judge_str = f" | judge={'PASS' if jp else 'FAIL'}"
        print(f"    {status}{judge_str}  "
              f"(behavior_expected={q.get('expected_behavior')} "
              f"observed={score.get('observed_behavior','?')} | "
              f"keywords={score.get('keywords',{}).get('hits','?')}/"
              f"{score.get('keywords',{}).get('total','?')} | "
              f"diag_ok={score.get('diagram_ok','?')} | "
              f"time={exec_result.get('timing',{}).get('total','?')}s)")

        if not args.dry_run and not score.get("pass") and not score.get("error"):
            kw_missing = score.get("keywords", {}).get("missing", [])
            if kw_missing:
                print(f"    missing keywords: {kw_missing}")
            vios = score.get("forbidden_violations", [])
            if vios:
                print(f"    forbidden hit:    {vios}")
            if args.judge and score.get("judge", {}).get("rationale"):
                print(f"    judge: {score['judge']['rationale']}")

        # Strip chunks_full before persisting — it's only needed by the judge
        # during scoring and bloats the JSON report unnecessarily.
        exec_result.pop("chunks_full", None)
        results.append({"question": q, "result": exec_result, "score": score})

    elapsed = time.time() - t_start

    # Aggregate scores
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total elapsed: {elapsed:.1f}s")
    if args.dry_run:
        print("(dry run — no pass/fail scoring)")
    else:
        by_cat: dict[str, dict[str, int]] = {}
        for r in results:
            c = r["question"].get("category", "?")
            bucket = by_cat.setdefault(c, {"pass": 0, "fail": 0, "error": 0})
            if r["score"].get("error"):
                bucket["error"] += 1
            elif r["score"].get("pass"):
                bucket["pass"] += 1
            else:
                bucket["fail"] += 1
        print()
        print(f"{'category':<22s} {'pass':>6s} {'fail':>6s} {'err':>6s}  rate")
        print("-" * 50)
        total_p = total_f = total_e = 0
        for cat in sorted(by_cat):
            p, f, e = by_cat[cat]["pass"], by_cat[cat]["fail"], by_cat[cat]["error"]
            total_p, total_f, total_e = total_p + p, total_f + f, total_e + e
            t = p + f + e
            rate = f"{100*p/t:.0f}%" if t else "-"
            print(f"{cat:<22s} {p:>6d} {f:>6d} {e:>6d}  {rate:>4s}")
        print("-" * 50)
        t = total_p + total_f + total_e
        rate = f"{100*total_p/t:.0f}%" if t else "-"
        print(f"{'TOTAL':<22s} {total_p:>6d} {total_f:>6d} {total_e:>6d}  {rate:>4s}")

        # Judge aggregate (informational — does not alter PASS)
        if args.judge:
            jp = jf = je = 0
            agree = disagree = 0
            for r in results:
                j = r["score"].get("judge") or {}
                if j.get("judge_error"):
                    je += 1
                elif j.get("overall_pass"):
                    jp += 1
                else:
                    jf += 1
                if j.get("overall_pass") is not None:
                    kw_pass = bool(r["score"].get("pass"))
                    if bool(j.get("overall_pass")) == kw_pass:
                        agree += 1
                    else:
                        disagree += 1
            print()
            print(f"LLM judge: PASS={jp}  FAIL={jf}  ERR={je}")
            total_rated = agree + disagree
            if total_rated:
                print(f"Judge vs keyword scoring: agree={agree}/{total_rated} "
                      f"({100*agree/total_rated:.0f}%)")

    # Write JSON
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_{ts}.json"
    out_path.write_text(
        json.dumps({
            "timestamp_utc": ts, "input": str(args.input),
            "dry_run": args.dry_run, "elapsed_s": round(elapsed, 1),
            "results": results,
        }, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print()
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    # Runtime bootstrap — only when invoked as a script. Keeps the module
    # importable from pytest without closing stdout or forcing env vars.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(ROOT / ".env", override=True)
    if yaml is None:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)
    sys.exit(main())
