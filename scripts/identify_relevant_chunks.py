#!/usr/bin/env python3
"""B.2 del Bloque B del GATE — identifica los chunks de chunks_v2 que SÍ
contienen la respuesta para cada pregunta del eval, usando Sonnet como juez de
relevancia atómica (un chunk a la vez, temp=0).

Por qué Sonnet y no Voyage:
  Usar Voyage para identificar "qué chunk es relevante" sesgaría el GATE — el
  evaluador y el evaluado usarían la misma vara. Sonnet es un modelo distinto,
  tarea distinta (juicio de relevancia, no embedding). Salvedad: el blurb
  contextual de los chunks lo escribió Haiku; Sonnet juzgando es separación
  suficiente (modelos distintos, tareas distintas).

Por qué NO PDFs originales:
  Si Sonnet leyera los PDFs estaríamos haciendo Capa A (gold answers desde
  fuente). Esta tarea es más acotada: dado un chunk concreto, ¿contiene la
  respuesta? Mantenerse en chunks evita scope creep hacia Capa A (deferida).

Cobertura:
  - 19 preguntas answer-type → identifica chunks relevantes (el denominador
    del recall del GATE).
  - 17 preguntas admit_no_info → check "free value": si Sonnet encuentra
    chunks que parecen responder, flag para revisión post-SWAP (señal de
    recalibración mal hecha como hp006).
  - 16 ask_clarification → NO se procesan (no aplica el concepto de "chunk
    relevante"; el bot debe pedir aclaración).

Output: evals/gate_relevant_chunks.json — persistido para que el GATE lo lea
como verdad fundamental. One-shot — no se vuelve a pagar Sonnet en cada
ejecución del GATE.

Uso:
    python scripts/identify_relevant_chunks.py
    python scripts/identify_relevant_chunks.py --limit 5    # prueba
    python scripts/identify_relevant_chunks.py --max-candidates 15
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

import httpx
import yaml

from src.config import ANTHROPIC_API_KEY
from src.ingestion.supabase_client import SupabaseHTTP
from src.rag.retriever import extract_product_models

from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("identify_relevant_chunks")

EVAL_YAML = "evals/baseline_v1.yaml"
OUTPUT = "evals/gate_relevant_chunks.json"
MODEL = "claude-sonnet-4-6"
MAX_CHUNK_CHARS = 4000   # cap del contenido del chunk al prompt
DEFAULT_MAX_CANDIDATES = 300  # safety cap (el manual más grande del corpus ronda ~290)
DEFAULT_WORKERS = 8  # concurrencia para las llamadas a Sonnet (rate limit Anthropic)

_PROMPT = """Estás juzgando si un fragmento de un manual técnico de PCI \
(protección contra incendios) contiene información relevante para responder \
una pregunta concreta.

Pregunta del técnico:
<pregunta>
{question}
</pregunta>

Fragmento de manual:
<fragmento source_file="{source_file}" section_path="{section_path}" page={page}>
{content}
</fragmento>

¿Este fragmento contiene información relevante para responder la pregunta?

Reglas:
- Responde SÍ solo si el fragmento contiene datos, instrucciones o información \
que respondan parcial o totalmente la pregunta. Mencionar el producto sin \
responder NO cuenta.
- Responde NO si el fragmento es solo metadata (índice, copyright, portada), \
o trata de un tema adyacente sin responder.

Formato OBLIGATORIO de respuesta — primera línea SÍ o NO, después una cita \
literal corta (10-30 palabras) si SÍ; si NO, una frase breve explicando por qué.

Ejemplo SÍ:
SÍ
"La resistencia de fin de línea es de 6,8 kΩ ±5%"

Ejemplo NO:
NO
Solo menciona el producto en el pie de página, no responde la pregunta.
"""


def md5(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_eval(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["questions"]


_STOPWORDS_ES = {"que", "como", "una", "uno", "del", "con", "para", "por",
                 "los", "las", "qué", "cómo", "cuál", "cuáles", "donde",
                 "está", "hay", "puede", "debe", "ser", "muy", "más",
                 "según", "este", "esta", "estos", "estas", "sobre", "entre"}


def detect_product_models(q: dict) -> list[str]:
    """Modelos a buscar — expected_sources si está; texto de la pregunta si no."""
    sources = q.get("expected_sources") or []
    if sources:
        return [s for s in sources if s]
    return extract_product_models(q["question"])


def extract_search_keywords(q: dict) -> list[str]:
    """Tokens léxicos para pre-filtrar candidatos vía FTS.

    Para preguntas answer-type: usa expected_keywords del YAML (curados humano,
    son las palabras que la respuesta debería contener). Splits `|` en alternativas.

    Para admit_no_info: los expected_keywords ahí describen el LENGUAJE del
    "no sé" del bot, no el contenido — extraemos del texto de la pregunta.
    """
    behavior = q.get("expected_behavior")
    out: list[str] = []
    if behavior == "answer":
        for kw in q.get("expected_keywords") or []:
            for alt in str(kw).split("|"):
                alt = alt.strip()
                if len(alt) >= 4:
                    out.append(alt)
    if not out:
        # Extraer del texto de la pregunta (nouns/términos largos)
        words = re.findall(r"\b[A-Za-zÁÉÍÓÚáéíóúñÑ]{5,}\b", q["question"].lower())
        out = [w for w in words if w not in _STOPWORDS_ES]
    # Dedupe preservando orden, cap a 8
    seen = set()
    deduped = []
    for w in out:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            deduped.append(w)
    return deduped[:8]


def fetch_candidates(sb: SupabaseHTTP, models: list[str],
                     max_n: int) -> list[dict]:
    """TODOS los chunks de los products mencionados (brute-force, paginado).

    Decisión: NO pre-filtrar por keywords. El pre-filtro léxico podía perder el
    chunk relevante si el corpus usaba términos distintos a los keywords
    curados, y PostgREST sin RPC no garantiza orden por relevancia. Para una
    creación one-shot de gold standard, el coste extra de Sonnet (~$15 total)
    compra rigor: Sonnet ve todo lo del producto y nadie filtra primero.

    Cap a max_n por seguridad (300 cubre el manual más grande del corpus).
    Pagina porque PostgREST default es 1000/req, suficiente para casi todo, pero
    docs con >1000 chunks (no esperado) requerirían múltiples páginas.
    """
    if not models:
        return []
    H = {"apikey": sb.service_key, "Authorization": f"Bearer {sb.service_key}"}
    select_cols = ("id,source_file,product_model,section_path,page_number,"
                   "content,duplicate_of")
    candidates: list[dict] = []
    seen_ids: set[str] = set()

    def _add(rows):
        for row in rows:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                candidates.append(row)

    for model in models:
        if len(candidates) >= max_n:
            break
        pattern = re.escape(model).replace(r"\-", r"[- ]?")
        try:
            r = httpx.get(f"{sb.url}/rest/v1/chunks_v2", headers=H, params={
                "select": select_cols,
                "product_model": f"imatch.{pattern}",
                "duplicate_of": "is.null",
                "order": "chunk_index.asc",
                "limit": str(max_n),
            }, timeout=30)
            r.raise_for_status()
            _add(r.json())
        except Exception as e:
            logger.warning("fetch model %s falló: %s", model, e)

    # Fallback 1: si ningún model resolvió, intentar por source_file ilike
    if not candidates and models:
        for model in models:
            try:
                r = httpx.get(f"{sb.url}/rest/v1/chunks_v2", headers=H, params={
                    "select": select_cols,
                    "source_file": f"ilike.*{model}*",
                    "duplicate_of": "is.null",
                    "limit": str(max_n),
                }, timeout=30)
                r.raise_for_status()
                _add(r.json())
            except Exception as e:
                logger.warning("source_file fetch %s falló: %s", model, e)

    # Fallback 2: content ilike. Aceptable SOLO en B.2 (gold creation) porque
    # Sonnet juzga relevancia chunk-a-chunk después — el ruido lo filtra el
    # juez, no entra al GATE. En el retriever de producción NO sería aceptable
    # (Voyage no tiene esa segunda pasada de filtrado).
    # Cubre modelos que viven en content pero no en filename: ZXe/ZXSe (chunks
    # de accesorios de Morley); AM2020/AFP1010 (paneles citados en MADT/MIDT).
    if not candidates and models:
        for model in models:
            try:
                r = httpx.get(f"{sb.url}/rest/v1/chunks_v2", headers=H, params={
                    "select": select_cols,
                    "content": f"ilike.*{model}*",
                    "duplicate_of": "is.null",
                    "limit": str(max_n),
                }, timeout=30)
                r.raise_for_status()
                _add(r.json())
            except Exception as e:
                logger.warning("content fetch %s falló: %s", model, e)

    return candidates[:max_n]


def judge_relevance(client: Anthropic, question: str, chunk: dict) -> tuple[bool, str, str]:
    """Sonnet juzga si el chunk responde la pregunta.
    Devuelve (relevante, cita, raw_response) — raw_response para debug."""
    prompt = _PROMPT.format(
        question=question,
        source_file=chunk.get("source_file") or "",
        section_path=chunk.get("section_path") or "",
        page=chunk.get("page_number") or "?",
        content=(chunk.get("content") or "")[:MAX_CHUNK_CHARS],
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=200, temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    first_line, _, rest = text.partition("\n")
    is_yes = first_line.strip().upper().startswith(("SÍ", "SI", "YES"))
    citation = rest.strip().strip('"').strip()
    return is_yes, citation, text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="procesa N preguntas (0 = todas)")
    ap.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES,
                    help="máx candidatos a juzgar por pregunta (cap de seguridad)")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                    help="threads concurrentes para Sonnet")
    ap.add_argument("--ids", default="",
                    help="lista de IDs separadas por coma — procesa solo esas, "
                         "merge con JSON previo (preserva el resto)")
    args = ap.parse_args()

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY no presente en .env")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    sb = SupabaseHTTP()

    questions = load_eval(EVAL_YAML)
    # Procesamos answer-type y admit_no_info; saltamos ask_clarification
    to_process = [q for q in questions
                  if q["expected_behavior"] in ("answer", "admit_no_info")]
    if args.ids:
        want = set(s.strip() for s in args.ids.split(","))
        to_process = [q for q in to_process if q["id"] in want]
    if args.limit:
        to_process = to_process[:args.limit]

    logger.info("preguntas a procesar: %d (de %d totales; %d ask_clarification ignoradas)",
                len(to_process), len(questions),
                sum(1 for q in questions if q["expected_behavior"] == "ask_clarification"))

    # Si --ids: cargar JSON previo y preservar las preguntas no afectadas
    if args.ids and os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as f:
            result = json.load(f)
        result["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result["eval_yaml_md5"] = md5(EVAL_YAML)
        # Limpiar las stats de las afectadas (se recomputan)
        for k in ("no_candidates", "admit_no_info_suspicious"):
            result["stats"][k] = [qid for qid in result["stats"].get(k, [])
                                  if qid not in {q["id"] for q in to_process}]
        result["stats"]["sonnet_calls"] = result["stats"].get("sonnet_calls", 0)
    else:
        result = {
            "version": "1.0",
            "eval_yaml_md5": md5(EVAL_YAML),
            "model": MODEL,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "max_candidates_per_question": args.max_candidates,
            "stats": {
                "total_processed": len(to_process),
                "answer_questions": sum(1 for q in to_process if q["expected_behavior"] == "answer"),
                "admit_no_info_questions": sum(1 for q in to_process if q["expected_behavior"] == "admit_no_info"),
                "no_candidates": [],
                "admit_no_info_suspicious": [],
                "sonnet_calls": 0,
            },
            "questions": {},
        }

    t0 = time.time()
    sonnet_calls = 0

    for i, q in enumerate(to_process):
        qid = q["id"]
        behavior = q["expected_behavior"]
        models = detect_product_models(q)
        candidates = fetch_candidates(sb, models, args.max_candidates)

        if not candidates:
            logger.warning("[%d/%d] %s (%s) — SIN CANDIDATOS (models=%s)",
                           i + 1, len(to_process), qid, behavior, models)
            result["stats"]["no_candidates"].append(qid)
            result["questions"][qid] = {
                "expected_behavior": behavior,
                "question": q["question"],
                "models_detected": models,
                "candidates_count": 0,
                "relevant_chunks": [],
                "verdict": "no_candidates",
            }
            continue

        relevant: list[dict] = []
        debug_judgments: list[dict] = []
        # Sonnet en paralelo — cada chunk es una decisión independiente.
        # 8 workers respeta rate limit Anthropic (Tier 4 da 4000 RPM, sobra).
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_to_chunk = {
                pool.submit(judge_relevance, client, q["question"], cand): cand
                for cand in candidates
            }
            for fut in as_completed(future_to_chunk):
                cand = future_to_chunk[fut]
                try:
                    is_rel, cite, raw = fut.result()
                    sonnet_calls += 1
                except Exception as e:
                    logger.warning("Sonnet falló %s chunk %s: %s",
                                   qid, cand["id"][:8], e)
                    continue
                debug_judgments.append({
                    "chunk_id": cand["id"][:12],
                    "section": (cand.get("section_path") or "")[:60],
                    "verdict": "SI" if is_rel else "NO",
                    "sonnet_text": raw[:200],
                })
                if is_rel:
                    relevant.append({
                        "id": cand["id"],
                        "source_file": cand.get("source_file"),
                        "section_path": cand.get("section_path"),
                        "page_number": cand.get("page_number"),
                        "citation": cite[:300],
                    })

        # Flags
        if behavior == "admit_no_info" and relevant:
            result["stats"]["admit_no_info_suspicious"].append(qid)
            verdict = "admit_no_info_suspicious"
        elif behavior == "admit_no_info":
            verdict = "admit_no_info_clean"
        elif relevant:
            verdict = "relevant_found"
        else:
            verdict = "no_relevant_in_candidates"

        result["questions"][qid] = {
            "expected_behavior": behavior,
            "question": q["question"],
            "models_detected": models,
            "candidates_count": len(candidates),
            "relevant_chunks": relevant,
            "verdict": verdict,
            "debug_judgments": debug_judgments,
        }

        logger.info("[%d/%d] %s (%s) — %d candidatos, %d relevantes [%s]",
                    i + 1, len(to_process), qid, behavior,
                    len(candidates), len(relevant), verdict)

    result["stats"]["sonnet_calls"] = sonnet_calls
    result["stats"]["elapsed_s"] = round(time.time() - t0, 1)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print()
    print("=" * 60)
    print(f"B.2 IDENTIFY RELEVANT CHUNKS")
    print(f"  preguntas procesadas:       {len(to_process)}")
    print(f"  llamadas Sonnet:            {sonnet_calls}")
    print(f"  sin candidatos:             {len(result['stats']['no_candidates'])}  "
          f"{result['stats']['no_candidates']}")
    print(f"  admit_no_info SOSPECHOSAS:  {len(result['stats']['admit_no_info_suspicious'])}  "
          f"{result['stats']['admit_no_info_suspicious']}")
    print(f"  tiempo:                     {result['stats']['elapsed_s']}s")
    print(f"  output:                     {OUTPUT}")


if __name__ == "__main__":
    main()
