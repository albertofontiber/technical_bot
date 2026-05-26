#!/usr/bin/env python3
"""Cross-valida los juicios de relevancia de Sonnet con Opus (BP del judge v2
Capa B: "Un LLM distinto del generador, fiabilidad por independencia").

Toma evals/gate_relevant_chunks.json (output de identify_relevant_chunks.py
con Sonnet) y, para una muestra estratificada, llama a Opus con el MISMO
prompt y los MISMOS chunks. Compara verdicts.

Sampling:
  - 100% de Sonnet-positives → precision check (estos crean el gold).
  - 100% de negatives para las preguntas no_relevant_in_candidates → estas
    son las más sospechosas de falso negativo sistémico.
  - 30% random de negatives del resto → recall check con CI razonable.

Métrica: raw agreement % + Cohen's kappa por pregunta y global. Kappa es
crítico — con clases muy desbalanceadas (~96% negatives), raw % infla la
señal; kappa descuenta el agreement por azar.

Output:
  - evals/gate_validation_results.json — datos crudos, todo opus_verdict + agreements
  - evals/gate_validation_disagreements.md — solo donde discrepan, side-by-side
    con espacio para tu decisión humana.

Coste estimado: ~2100 calls Opus × ~650 tokens × ~$0.013 = ~$25-30.

Uso:
    python scripts/cross_validate_relevance.py
    python scripts/cross_validate_relevance.py --limit 3   # prueba
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from src.config import ANTHROPIC_API_KEY
from src.ingestion.supabase_client import SupabaseHTTP
from scripts.identify_relevant_chunks import (
    fetch_candidates, _PROMPT, MAX_CHUNK_CHARS, DEFAULT_MAX_CANDIDATES,
)

from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("cross_validate")

INPUT = "evals/gate_relevant_chunks.json"
OUTPUT_JSON = "evals/gate_validation_results.json"
OUTPUT_MD = "evals/gate_validation_disagreements.md"

OPUS_MODEL = "claude-opus-4-6"  # probado en producción (VALIDATOR_MODEL del bot)
WORKERS = 6  # Opus algo más lento que Sonnet — reducir para no saturar rate limits
NEGATIVE_SAMPLE_RATE = 0.30

# Las 8 preguntas answer-type donde Sonnet rechazó TODOS los candidatos.
# Más sospechosas de falso negativo sistémico — validar 100% de negatives.
FULL_NEGATIVE_QUESTIONS = {
    "hp005", "hp007", "hp008", "hp016", "hp017", "hp018", "hp020", "cm002",
}


@dataclass
class Validation:
    qid: str
    question: str
    chunk: dict
    sonnet_verdict: bool      # True = SI
    sonnet_text: str
    opus_verdict: bool | None = None
    opus_text: str | None = None


def judge_with_opus(client: Anthropic, question: str,
                    chunk: dict) -> tuple[bool, str]:
    """Mismo prompt que Sonnet, distinto modelo."""
    prompt = _PROMPT.format(
        question=question,
        source_file=chunk.get("source_file") or "",
        section_path=chunk.get("section_path") or "",
        page=chunk.get("page_number") or "?",
        content=(chunk.get("content") or "")[:MAX_CHUNK_CHARS],
    )
    resp = client.messages.create(
        model=OPUS_MODEL, max_tokens=200, temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    first_line = text.split("\n", 1)[0]
    is_yes = first_line.strip().upper().startswith(("SÍ", "SI", "YES"))
    return is_yes, text


def cohens_kappa(a: int, b: int, c: int, d: int) -> float | None:
    """Cohen's kappa desde matriz de confusión.
    a = both YES; b = S YES O NO; c = S NO O YES; d = both NO.
    Honest agreement quitando el componente esperable por azar.
    """
    n = a + b + c + d
    if n == 0:
        return None
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


def kappa_label(k: float | None) -> str:
    if k is None:
        return "N/A"
    if k >= 0.81: return "casi perfecta"
    if k >= 0.61: return "sustancial"
    if k >= 0.41: return "moderada"
    if k >= 0.21: return "razonable"
    if k >= 0.0:  return "leve"
    return "negativa (¡peor que azar!)"


def build_validations(sonnet_data: dict, sb: SupabaseHTTP,
                      max_candidates: int) -> list[Validation]:
    """Construye la lista de validations a juzgar por Opus según el sampling."""
    out: list[Validation] = []
    for qid, qd in sonnet_data["questions"].items():
        if qd["candidates_count"] == 0:
            continue  # nada que validar (no_candidates)
        question = qd["question"]
        models = qd.get("models_detected") or []

        # Re-fetch candidatos para esta pregunta (mismo fetch_candidates que
        # usó Sonnet, así obtenemos el set completo con full chunk_ids).
        candidates = fetch_candidates(sb, models, max_candidates)
        short_to_chunk = {c["id"][:12]: c for c in candidates}

        positives: list[Validation] = []
        negatives: list[Validation] = []
        for dj in qd.get("debug_judgments", []):
            chunk = short_to_chunk.get(dj["chunk_id"])
            if not chunk:
                continue
            v = Validation(qid=qid, question=question, chunk=chunk,
                           sonnet_verdict=(dj["verdict"] == "SI"),
                           sonnet_text=dj["sonnet_text"])
            if v.sonnet_verdict:
                positives.append(v)
            else:
                negatives.append(v)

        # 100% positives — son los que crean el gold (precision crítica)
        out.extend(positives)

        # Negatives según política de sampling
        if qid in FULL_NEGATIVE_QUESTIONS:
            out.extend(negatives)
        else:
            rng = random.Random(qid)  # determinista por qid → reproducible
            sample_n = max(1, int(len(negatives) * NEGATIVE_SAMPLE_RATE)) \
                if negatives else 0
            sample_n = min(sample_n, len(negatives))
            out.extend(rng.sample(negatives, sample_n))

    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="procesa solo las primeras N preguntas (prueba)")
    args = ap.parse_args()

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY no presente en .env")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    sb = SupabaseHTTP()

    with open(INPUT, encoding="utf-8") as f:
        sonnet_data = json.load(f)

    if args.limit:
        sonnet_data["questions"] = dict(
            list(sonnet_data["questions"].items())[:args.limit])

    logger.info("Construyendo lista de validations...")
    validations = build_validations(sonnet_data, sb, DEFAULT_MAX_CANDIDATES)
    logger.info("Total validations Opus: %d (de %d juicios totales Sonnet)",
                len(validations),
                sum(len(qd.get("debug_judgments", []))
                    for qd in sonnet_data["questions"].values()))

    # Lanzar Opus en paralelo
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        future_to_v = {pool.submit(judge_with_opus, client, v.question, v.chunk): v
                       for v in validations}
        for fut in as_completed(future_to_v):
            v = future_to_v[fut]
            try:
                v.opus_verdict, v.opus_text = fut.result()
            except Exception as e:
                logger.warning("Opus falló para %s chunk %s: %s",
                               v.qid, v.chunk["id"][:8], e)
                v.opus_verdict = None
                v.opus_text = f"ERROR: {e}"
            done += 1
            if done % 100 == 0:
                logger.info("  %d/%d Opus calls done (%.0fs elapsed)",
                            done, len(validations), time.time() - t0)

    # Agregar por pregunta
    per_q = defaultdict(lambda: {"a": 0, "b": 0, "c": 0, "d": 0, "errors": 0})
    global_counts = {"a": 0, "b": 0, "c": 0, "d": 0, "errors": 0}
    disagreements = []
    for v in validations:
        if v.opus_verdict is None:
            per_q[v.qid]["errors"] += 1
            global_counts["errors"] += 1
            continue
        if v.sonnet_verdict and v.opus_verdict:
            cell = "a"
        elif v.sonnet_verdict and not v.opus_verdict:
            cell = "b"
            disagreements.append(v)
        elif not v.sonnet_verdict and v.opus_verdict:
            cell = "c"
            disagreements.append(v)
        else:
            cell = "d"
        per_q[v.qid][cell] += 1
        global_counts[cell] += 1

    # Métricas
    g_a, g_b, g_c, g_d = global_counts["a"], global_counts["b"], global_counts["c"], global_counts["d"]
    g_n = g_a + g_b + g_c + g_d
    g_agree = (g_a + g_d) / g_n if g_n else 0
    g_kappa = cohens_kappa(g_a, g_b, g_c, g_d)

    # Resultados JSON
    results = {
        "version": "1.0",
        "model_judge_a": sonnet_data.get("model", "claude-sonnet-4-6"),
        "model_judge_b": OPUS_MODEL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_sonnet_md5": hashlib.md5(open(INPUT, "rb").read()).hexdigest(),
        "stats": {
            "validations": len(validations),
            "errors": global_counts["errors"],
            "elapsed_s": round(time.time() - t0, 1),
            "global": {
                "both_yes": g_a, "sonnet_yes_opus_no": g_b,
                "sonnet_no_opus_yes": g_c, "both_no": g_d,
                "raw_agreement": round(g_agree, 4),
                "cohens_kappa": round(g_kappa, 4) if g_kappa is not None else None,
                "kappa_interpretation": kappa_label(g_kappa),
                "n_disagreements": len(disagreements),
            },
        },
        "per_question": {},
        "validations": [],
    }
    for qid, c in per_q.items():
        n = c["a"] + c["b"] + c["c"] + c["d"]
        k = cohens_kappa(c["a"], c["b"], c["c"], c["d"])
        results["per_question"][qid] = {
            "both_yes": c["a"], "sonnet_yes_opus_no": c["b"],
            "sonnet_no_opus_yes": c["c"], "both_no": c["d"],
            "errors": c["errors"],
            "raw_agreement": round((c["a"] + c["d"]) / n, 4) if n else None,
            "cohens_kappa": round(k, 4) if k is not None else None,
        }
    for v in validations:
        results["validations"].append({
            "qid": v.qid,
            "chunk_id": v.chunk["id"],
            "section_path": v.chunk.get("section_path"),
            "source_file": v.chunk.get("source_file"),
            "page": v.chunk.get("page_number"),
            "sonnet_verdict": v.sonnet_verdict,
            "opus_verdict": v.opus_verdict,
            "agree": v.opus_verdict == v.sonnet_verdict if v.opus_verdict is not None else None,
        })
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    # Markdown legible para revisión humana
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Disagreements Sonnet ↔ Opus\n\n")
        f.write(f"**Agreement global:** {g_agree:.1%} · **Cohen's κ:** "
                f"{g_kappa:.3f} ({kappa_label(g_kappa)}) · "
                f"**Disagreements:** {len(disagreements)} / {g_n}\n\n")
        f.write("Para cada caso: revisa la cita y marca tu decisión "
                "(SI/NO/duda) en el slot.\n\n")
        f.write("---\n\n")
        for v in disagreements:
            f.write(f"## {v.qid} · chunk `{v.chunk['id'][:12]}`\n\n")
            f.write(f"**Pregunta:** {v.question}\n\n")
            f.write(f"**Chunk** (`{v.chunk.get('source_file','?')}` pag "
                    f"{v.chunk.get('page_number','?')} · {v.chunk.get('section_path','?')}):\n\n")
            # Mostrar el mismo cap que vieron los jueces (MAX_CHUNK_CHARS=4000),
            # no 1500 — el truncado a 1500 dejaba la revisión humana con menos
            # info que los LLMs (gap silencioso detectado en hp003).
            content = (v.chunk.get("content") or "")[:MAX_CHUNK_CHARS]
            f.write(f"```\n{content}\n```\n\n")
            f.write("| Juez | Verdict | Razón |\n|---|---|---|\n")
            f.write(f"| Sonnet | **{'SÍ' if v.sonnet_verdict else 'NO'}** | "
                    f"{v.sonnet_text[:200].replace(chr(10), ' ')} |\n")
            f.write(f"| Opus   | **{'SÍ' if v.opus_verdict else 'NO'}** | "
                    f"{(v.opus_text or '')[:200].replace(chr(10), ' ')} |\n\n")
            f.write("**Tu decisión:** _____ (SI / NO / mantengo Sonnet / mantengo Opus)\n\n")
            f.write("---\n\n")

    print()
    print("=" * 60)
    print("CROSS-VALIDATION SONNET ↔ OPUS")
    print(f"  validations:        {len(validations)}")
    print(f"  errors:             {global_counts['errors']}")
    print(f"  agreement:          {g_agree:.1%}")
    print(f"  Cohen's κ:          {g_kappa:.3f} ({kappa_label(g_kappa)})")
    print(f"  disagreements:      {len(disagreements)}")
    print(f"  tiempo:             {time.time() - t0:.0f}s")
    print(f"  output:             {OUTPUT_JSON}")
    print(f"  para revisión:      {OUTPUT_MD}")


if __name__ == "__main__":
    main()
