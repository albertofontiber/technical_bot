#!/usr/bin/env python3
"""atomic_scorer.py — scorer atómico MÍNIMO del ruler (Fase 2, rebanada vertical).

Puntúa la respuesta del bot contra los HECHOS ATÓMICOS del gold, por hecho y de
forma TRANSPARENTE/auditable — en vez del juez LLM opaco de test_bot_vs_gold.py
(que en hp007 falló por dato obsoleto). Ver RULER_DESIGN §3 + TECH_DEBT #34.

Reusa el matcher ESTRICTO de PR#15 (strict_match.py). Eje COMPLETITUD, mecánico:
¿aparece el valor distintivo de cada hecho CORE en la respuesta del bot? Clasifica el
MÉTODO de match para exponer dónde basta lo mecánico y dónde hace falta el LLM:
  - anchor : número(>=2 díg) o código de modelo presente/ausente → ALTA confianza.
  - prose  : sin valor numérico → overlap de términos (>=0.8) → BAJA confianza
             (sinónimos/frecuencias/códigos 7-seg = prosa irreducible → futuro LLM).
  - manual : valor=null → requiere juicio humano.

NO evalúa aún el eje FACTUAL (alucinación) de forma automática: la asimetría de
seguridad (alucinación=FALLO) necesita un check LLM acotado a los hechos (Fase 4).
Por eso el veredicto es PROVISIONAL y lo DECLARA.

Entrada: gold (gold_store; solo verificados con atomic_facts) + respuestas del bot
(por defecto el último run cacheado evals/bot_vs_gold_results_k5.yaml, o --answers).

Uso: python scripts/atomic_scorer.py [--answers evals/bot_vs_gold_results_k5.yaml]
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

# admit_no_info / ask_clarification (legacy) → las 5 conductas (RULER_DESIGN §1).
_LEGACY = {"admit_no_info": "admit", "ask_clarification": "clarify"}
_NOINFO = ("no tengo", "no contiene", "no contienen", "no especifica", "no se especifica",
           "no aparece", "no esta cubiert", "no dispongo", "no figura", "no incluye",
           "no describe", "no hay informacion", "no consta", "no cuento con")
_CLARIFY = ("que modelo", "podria indicar", "podrias indicar", "necesito saber",
            "indicame el modelo", "que version", "cual es el modelo")


def _anchor_present(anchor: str, na: str) -> bool:
    """¿aparece el anchor como número/token COMPLETO en na (ya norm_ocr'd)? Frontera
    de no-palabra a ambos lados → corrige el falso positivo substring de PR#15
    ('40' in '240'). chunk_has_quote_strict (strict_match) usa `in` crudo porque su
    haystack es un chunk grande y re-tocarlo exige re-validar el eval de recall (live
    stack) — por eso el scorer hace su propio test de frontera, sin tocar el matcher."""
    return re.search(r"(?<!\w)" + re.escape(anchor) + r"(?!\w)", na) is not None


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


def score_gold(gold: dict, answer: str) -> dict:
    facts = gold.get("atomic_facts") or []
    rows = []
    for f in facts:
        present, method, detail = match_fact(f.get("valor"), f.get("texto", ""), answer)
        rows.append({"tipo": f.get("tipo"), "present": present, "method": method,
                     "detail": detail, "texto": f.get("texto", "")})

    core = [r for r in rows if r["tipo"] == "core"]
    scorable = [r for r in core if r["present"] is not None]
    present_core = [r for r in scorable if r["present"]]
    n, p = len(scorable), len(present_core)

    expected = _LEGACY.get(gold.get("conducta_esperada"), gold.get("conducta_esperada"))
    bot_conducta = detect_conducta(answer)

    if expected != bot_conducta:
        if expected == "answer" and bot_conducta == "admit":
            verdict = "FALLO (admite con el corpus cubriendo)"
        elif expected == "admit" and bot_conducta == "answer":
            verdict = "REVISAR (responde donde el gold admite — ¿alucina?)"
        else:
            verdict = f"REVISAR (conducta bot={bot_conducta} != esperada={expected})"
    elif expected in ("admit", "clarify"):
        verdict = f"PASS (conducta {expected} correcta)"
    elif n == 0:
        verdict = "? (ningún hecho core puntuable mecánicamente)"
    elif p == n:
        verdict = f"PASS (completitud core {p}/{n})"
    elif p > 0:
        verdict = f"PARCIAL (completitud core {p}/{n})"
    else:
        verdict = f"FALLO (completitud core 0/{n})"

    return {"qid": gold.get("qid"), "expected": expected, "bot_conducta": bot_conducta,
            "core": f"{p}/{n}", "verdict": verdict, "rows": rows}


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

    print(f"Scorer atómico (MÍNIMO) · {len(golds)} golds verificados con hechos atómicos")
    print(f"Respuestas del bot: {Path(args.answers).name}\n")

    results = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            print(f"=== {qid} === (sin respuesta del bot en el fichero — saltado)\n")
            continue
        res = score_gold(g, answers[qid])
        results.append(res)
        print(f"=== {qid} === esperada={res['expected']} | bot={res['bot_conducta']} "
              f"| core={res['core']}")
        for i, r in enumerate(res["rows"], 1):
            print(f"  [{_GLYPH[r['present']]}] {r['tipo']:<13} {r['method']:<7} "
                  f"{r['detail']}")
            print(f"       {r['texto'][:88]}")
        print(f"  → {res['verdict']}\n")

    print("=" * 70)
    print("RESUMEN (veredicto PROVISIONAL — eje factual/alucinación pendiente de LLM):")
    for r in results:
        print(f"  {r['qid']}: core {r['core']:<6} {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
