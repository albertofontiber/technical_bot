#!/usr/bin/env python3
"""atomic_scorer.py — scorer atómico del ruler (Fase 2).

Puntúa la respuesta del bot contra los HECHOS ATÓMICOS del gold, por hecho y de
forma TRANSPARENTE/auditable — en vez del juez LLM opaco de test_bot_vs_gold.py
(que en hp007 falló por dato obsoleto). Ver RULER_DESIGN §3 + TECH_DEBT #34.

Eje COMPLETITUD (mecánico, determinista): reusa el matcher ESTRICTO de PR#15
(strict_match.py). ¿aparece el valor distintivo de cada hecho CORE en la respuesta?
Clasifica el MÉTODO para exponer dónde basta lo mecánico y dónde hace falta el LLM:
  - anchor : número(>=2 díg) o código de modelo presente/ausente → ALTA confianza.
  - prose  : sin valor numérico → overlap de términos (>=0.8) → BAJA confianza
             (sinónimos/frecuencias/códigos 7-seg = prosa irreducible).
  - manual : valor=null → requiere juicio humano.

Eje FACTUAL (alucinación) — OPCIONAL (--llm): check cross-model (GPT-5.5) acotado a
los hechos que detecta CONTRADICCIONES (no omisiones ni info extra). Cualquier
contradicción → FALLO (asimetría de seguridad, RULER_DESIGN §3). Sin --llm el eje no
se evalúa y el veredicto se marca PROVISIONAL. Cross-model evita los puntos ciegos
del bot (Sonnet, lección s13) y NO re-lee píxeles → el sesgo 7-seg no aplica aquí
(compara TEXTOS, no displays).

Eje CONDUCTA: heurístico mínimo (answer | admit | clarify) — a endurecer con golds
de conducta (Fase 1/3).

Entrada: gold (gold_store; solo verificados con atomic_facts) + respuestas del bot
(por defecto el último run cacheado evals/bot_vs_gold_results_k5.yaml, o --answers).

Uso:
  python scripts/atomic_scorer.py                 # solo completitud+conducta (offline)
  python scripts/atomic_scorer.py --llm            # + eje factual (GPT-5.5, requiere key)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
import gold_store  # noqa: E402
from strict_match import distinctive, norm, norm_ocr, quote_overlap  # noqa: E402

OVERLAP_PRESENT = 0.8  # umbral de presencia para hechos de prosa (sin valor numérico)
DEFAULT_ANSWERS = ROOT / "evals" / "bot_vs_gold_results_k5.yaml"
FACTUAL_MODEL = "gpt-5.5"  # cross-model (distinto del bot-Sonnet y del gold-Opus)

# admit_no_info / ask_clarification (legacy) → las 5 conductas (RULER_DESIGN §1).
_LEGACY = {"admit_no_info": "admit", "ask_clarification": "clarify"}
_NOINFO = ("no tengo", "no contiene", "no contienen", "no especifica", "no se especifica",
           "no aparece", "no esta cubiert", "no dispongo", "no figura", "no incluye",
           "no describe", "no hay informacion", "no consta", "no cuento con")
_CLARIFY = ("que modelo", "podria indicar", "podrias indicar", "necesito saber",
            "indicame el modelo", "que version", "cual es el modelo")


def _anchor_present(anchor: str, na: str) -> bool:
    """¿aparece el anchor como número/token COMPLETO en na (ya norm_ocr'd)?
    - Numérico (24, +60, 295): frontera de DÍGITO → casa "24" en "24V"/"24 °C" pero NO
      en "240" (corrige el substring de PR#15, '40'∈'240', SIN perder valores con unidad
      pegada — bug cazado por hp003 ">24V", s32).
    - Código de modelo (afp1010): frontera de PALABRA → token completo, no dentro de otro.
    chunk_has_quote_strict (strict_match) conserva el `in` crudo (haystack=chunk grande,
    re-validar recall = live stack) — por eso el scorer hace su propio test, sin tocarlo."""
    bound = r"\d" if re.fullmatch(r"[+\-]?\d[\d.,]*", anchor) else r"\w"
    return re.search(rf"(?<!{bound}){re.escape(anchor)}(?!{bound})", na) is not None


def match_fact(valor, texto: str, answer: str) -> tuple[bool | None, str, str]:
    """(presente?, método, detalle). present=None → no puntuable mecánicamente."""
    na = norm_ocr(answer)
    anchors = distinctive(valor or "")
    if anchors:
        missing = sorted(a for a in anchors if not _anchor_present(a, na))
        return (not missing, "anchor", f"anchors={sorted(anchors)} missing={missing}")
    if valor:
        ov = quote_overlap(valor, answer)
        return (ov >= OVERLAP_PRESENT, "prose", f"overlap={ov:.0%} valor='{valor}'")
    return (None, "manual", "valor=null (requiere juicio humano)")


def detect_conducta(answer: str) -> str:
    """Heurístico (mínimo): answer | admit | clarify desde el texto del bot."""
    a = norm(answer)
    head = a[:300]
    if a.count("?") >= 1 and any(k in head for k in _CLARIFY):
        return "clarify"
    if any(k in head for k in _NOINFO):
        return "admit"
    return "answer"


# --- Eje FACTUAL (alucinación) — check cross-model acotado a los hechos -----------
_FACTUAL_SYS = (
    "Eres un verificador de SEGURIDAD de un bot técnico de sistemas PCI (detección de "
    "incendios). Tu ÚNICA tarea: detectar CONTRADICCIONES entre la RESPUESTA DEL BOT y "
    "una lista de HECHOS VERIFICADOS contra el manual oficial.\n"
    "Una CONTRADICCIÓN = el bot afirma un valor, comportamiento o default que CHOCA con "
    "un hecho verificado (valor distinto, significado opuesto, default equivocado).\n"
    "NO es contradicción: (a) que el bot OMITA un hecho; (b) que el bot añada información "
    "extra que NO está en la lista (puede estar en el manual — NO lo penalices); (c) "
    "diferencias de redacción o sinónimos.\n"
    "El bot puede usar una ETIQUETA o nombre distinto para el mismo parámetro: júzgalo por "
    "el SIGNIFICADO, no por el nombre. Solo cuenta el CHOQUE directo de un dato con un "
    "hecho listado. Ante la duda, NO marques contradicción (preferimos falso-negativo a "
    "falso-positivo en este eje)."
)
_FACTUAL_USER = (
    "HECHOS VERIFICADOS (del manual oficial):\n{facts}\n\n"
    "RESPUESTA DEL BOT:\n{answer}\n\n"
    "Devuelve SOLO JSON válido (sin markdown):\n"
    '{{"contradicciones": [{{"hecho": "<hecho verificado>", '
    '"afirmacion_bot": "<lo que dice el bot>", "por_que": "<por qué chocan>"}}]}}\n'
    'Si no hay ninguna contradicción, devuelve {{"contradicciones": []}}.'
)


def factual_check(facts: list[dict], answer: str, client, model: str) -> tuple[list, str | None]:
    """(contradicciones, error). Lista vacía = sin contradicciones. error!=None =
    no se pudo evaluar (no auto-FALLO; va a REVISAR)."""
    import json
    facts_txt = "\n".join(
        f"- {f.get('texto', '')}" + (f" [valor: {f['valor']}]" if f.get("valor") else "")
        for f in facts)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": _FACTUAL_SYS},
                      {"role": "user", "content": _FACTUAL_USER.format(
                          facts=facts_txt, answer=(answer or "")[:4000])}],
        )
        txt = resp.choices[0].message.content.strip()
    except Exception as e:
        return [], f"llamada LLM falló: {e}"
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        return list(json.loads(txt).get("contradicciones", [])), None
    except Exception as e:
        return [], f"parse error: {e}: {txt[:160]}"


def score_gold(gold: dict, answer: str, contradictions=None, factual_error=None) -> dict:
    facts = gold.get("atomic_facts") or []
    rows = []
    for f in facts:
        present, method, detail = match_fact(f.get("valor"), f.get("texto", ""), answer)
        rows.append({"tipo": f.get("tipo"), "present": present, "method": method,
                     "detail": detail, "texto": f.get("texto", "")})

    core = [r for r in rows if r["tipo"] == "core"]
    scorable = [r for r in core if r["present"] is not None]
    present_core = [r for r in scorable if r["present"]]
    core_manual = [r for r in core if r["present"] is None]  # valor=null → sin puntuar
    n, p = len(scorable), len(present_core)

    expected = _LEGACY.get(gold.get("conducta_esperada"), gold.get("conducta_esperada"))
    bot_conducta = detect_conducta(answer)
    factual_run = contradictions is not None or factual_error is not None

    # Síntesis: la asimetría de seguridad manda (alucinación=FALLO por encima de todo).
    # factual_error y contradictions son mutuamente excluyentes (contrato de
    # factual_check: éxito→([...], None); fallo→([], err)) → el orden no enmascara un FALLO.
    if factual_error:
        verdict = f"REVISAR (eje factual no evaluable: {factual_error})"
    elif contradictions:
        verdict = f"FALLO (alucinación: contradice {len(contradictions)} hecho(s) verificado(s))"
    elif expected != bot_conducta:
        if expected == "answer" and bot_conducta == "admit":
            verdict = "FALLO (admite con el corpus cubriendo)"
        elif expected == "admit" and bot_conducta == "answer":
            verdict = "REVISAR (responde donde el gold admite)"
        else:
            verdict = f"REVISAR (conducta bot={bot_conducta} != esperada={expected})"
    elif expected in ("admit", "clarify"):
        verdict = f"PASS (conducta {expected} correcta)"
    elif n == 0:
        verdict = "? (ningún hecho core puntuable mecánicamente)"
    elif p == n:
        # "sin alucinación" sería over-claim: el gate solo descarta CONTRADICCIONES de
        # hechos LISTADOS, no fabricación fuera de la lista (cross-model review s32, #1).
        verdict = f"PASS (completitud core {p}/{n}" + (", sin contradicción con hechos listados)" if factual_run else ")")
    elif p > 0:
        verdict = f"PARCIAL (completitud core {p}/{n})"
    else:
        verdict = f"FALLO (completitud core 0/{n})"

    # Honestidad del veredicto (cross-model review s32, #2/#4): NO ocultar bajo un "p/n"
    # limpio los core SIN puntuar (manual) ni la dependencia de prosa frágil.
    if expected not in ("admit", "clarify") and not contradictions and not factual_error:
        notes = []
        if core_manual:
            notes.append(f"{len(core_manual)} core SIN puntuar (manual)")
        prose_hits = sum(1 for r in present_core if r["method"] == "prose")
        if prose_hits:
            notes.append(f"{prose_hits}/{p} presentes por prosa (frágil)")
        if notes:
            verdict += "  [" + "; ".join(notes) + "]"

    if not factual_run:
        verdict += "  [PROVISIONAL: eje factual no evaluado — usa --llm]"

    return {"qid": gold.get("qid"), "expected": expected, "bot_conducta": bot_conducta,
            "core": f"{p}/{n}", "verdict": verdict, "rows": rows,
            "contradictions": contradictions or [], "factual_error": factual_error}


_GLYPH = {True: "✓", False: "✗", None: "?"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default=str(DEFAULT_ANSWERS),
                    help="YAML con [{qid, bot_answer}] (default: último run k5 cacheado)")
    ap.add_argument("--qids", default="", help="limitar a qids separados por coma")
    ap.add_argument("--llm", action="store_true",
                    help="evalúa el eje FACTUAL con GPT-5.5 (requiere OPENAI_API_KEY)")
    ap.add_argument("--model", default=FACTUAL_MODEL, help="modelo del eje factual")
    args = ap.parse_args()

    answers = {}
    with open(args.answers, encoding="utf-8") as fh:
        for r in yaml.safe_load(fh) or []:
            if r.get("qid"):
                answers[r["qid"]] = r.get("bot_answer", "")

    golds = [g for g in gold_store.verified() if g.get("atomic_facts")]
    if args.qids:
        want = {q.strip() for q in args.qids.split(",")}
        golds = [g for g in golds if g.get("qid") in want]

    client = None
    if args.llm:
        import os
        from dotenv import load_dotenv
        from openai import OpenAI
        load_dotenv(ROOT / ".env", override=True)
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            print("[ERROR] --llm pero no hay OPENAI_API_KEY (en .env o env). Abortado.")
            return 1
        client = OpenAI(api_key=key)

    eje = "completitud + conducta + FACTUAL(LLM)" if client else "completitud + conducta"
    print(f"Scorer atómico · {len(golds)} golds verificados con hechos atómicos · ejes: {eje}")
    print(f"Respuestas del bot: {Path(args.answers).name}\n")

    results = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            print(f"=== {qid} === (sin respuesta del bot en el fichero — saltado)\n")
            continue
        contradictions, factual_error = (None, None)
        if client:
            contradictions, factual_error = factual_check(
                g.get("atomic_facts") or [], answers[qid], client, args.model)
        res = score_gold(g, answers[qid], contradictions, factual_error)
        results.append(res)
        print(f"=== {qid} === esperada={res['expected']} | bot={res['bot_conducta']} "
              f"| core={res['core']}")
        for r in res["rows"]:
            print(f"  [{_GLYPH[r['present']]}] {r['tipo']:<13} {r['method']:<7} {r['detail']}")
            print(f"       {r['texto'][:88]}")
        if client:
            if res["factual_error"]:
                print(f"  factual: ERROR — {res['factual_error']}")
            elif res["contradictions"]:
                for c in res["contradictions"]:
                    print(f"  ⚠ CONTRADICE: hecho «{str(c.get('hecho'))[:60]}»")
                    print(f"               bot dice «{str(c.get('afirmacion_bot'))[:60]}» — {c.get('por_que')}")
            else:
                print("  factual: sin contradicciones")
        print(f"  → {res['verdict']}\n")

    print("=" * 70)
    suffix = "" if client else " (PROVISIONAL — eje factual pendiente; corre con --llm)"
    print(f"RESUMEN{suffix}:")
    for r in results:
        print(f"  {r['qid']}: core {r['core']:<6} {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
