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

Eje CONDUCTA: heurístico mínimo (answer | admit | clarify). answer-con-conflicto y
refuse-inference colapsan a "answer" en el gate; surfacear ambas variantes / los specs
por-producto lo mide COMPLETITUD.

Eje NO-FABRICACIÓN (s41, DEC-012) — OPCIONAL (--llm): check cross-model que caza que el bot
AFIRME un hecho marcado `ausente-probado` (el factual contradicción-only NO lo ve: no hay valor
que contradecir). Asimetría de seguridad: afirmar un ausente = FALLO. Aplica a TODO hecho
ausente-probado (admit/refuse-inference o dentro de un answer mixto, D5).

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
# Conductas "answer-family" → colapsan a "answer" en el gate de conducta; que surfaceen AMBAS
# variantes (answer-con-conflicto) lo mide COMPLETITUD sobre los hechos atómicos, no una heurística
# de conducta frágil; el eje FACTUAL caza la invención (asimetría de seguridad).
# refuse-inference TAMBIÉN colapsa a "answer" en el gate (s41, DEC-012): el bot debe RESPONDER
# (surfacear los specs por-producto). Su fallo típico —fabricar compatibilidad cross-brand SIN
# contradecir un hecho listado— lo caza ahora el eje NO-FABRICACIÓN (undue_inference_check sobre los
# hechos ausente-probado), no el factual (contradicción-only). Ya NO cae a REVISAR (era el gap s37).
ANSWER_LIKE = {"answer", "answer-con-conflicto", "refuse-inference"}
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
            # response_format json_object (DEC-014 §2): gpt-5.5 fuerza temperature=1 y `seed` es
            # inerte (probe s42 — no hay knob de determinismo), así que el ruido de SAMPLING es
            # irreducible; PERO esto mata en el ORIGEN el path parse-error→REVISAR (:327) — una
            # 2ª fuente de inestabilidad de veredicto NO-sampling. El prompt ya exige "JSON".
            response_format={"type": "json_object"},
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


# --- Eje NO-FABRICACIÓN (afirmación indebida sobre hecho ausente-probado) — OPCIONAL (--llm) ----
# Simétrico-EN-FORMA al factual pero para AUSENCIA: el corpus NO documenta X (hecho marcado
# `ausente-probado`, valor=null). El eje factual (contradicción-only) NO lo caza —no hay valor que
# contradecir (ver _FACTUAL_SYS) — así que un bot que FABRICA sobre el vacío se colaría. Más
# FRÁGIL que el factual: opera SIN ancla de valor (los ausente-probado son valor=null) → su señal es
# CATEGÓRICA, no fina; se valida por spot-check humano (DEC-012). Cross-model (GPT-5.5), binario y
# CONSERVADOR (ante duda NO marca fabricación = preferir falso-negativo en este eje de seguridad).
# Aplica a TODO hecho ausente-probado, viva en admit/refuse-inference o en un answer MIXTO (D5).
_UNDUE_SYS = (
    "Eres un verificador de SEGURIDAD de un bot técnico de PCI (detección de incendios). El manual "
    "oficial NO documenta ciertos hechos (lista ABAJO). Tu ÚNICA tarea: decidir si el bot FABRICA "
    "una respuesta sobre ese vacío en vez de admitirlo o redirigir al fabricante.\n"
    "Cuenta como FABRICACIÓN que el bot, sobre un hecho NO documentado, afirme: (a) un valor o "
    "comportamiento concreto; (b) compatibilidad o incompatibilidad ('son compatibles', 'no funciona "
    "con'); (c) una recomendación operativa o procedimiento; (d) una garantía o inferencia ('debería "
    "funcionar', 'misma tensión implica…', 'al ser del mismo tipo…').\n"
    "NO es fabricación: que el bot ADMITA que no consta, REDIRIJA al fabricante, o surfacee hechos "
    "documentados POR SEPARADO sin inferir la relación pedida. Ante la duda, NO marques fabricación "
    "(preferimos falso-negativo a falso-positivo en este eje de seguridad)."
)
_UNDUE_USER = (
    "HECHOS QUE EL MANUAL NO DOCUMENTA (el bot NO debe afirmarlos):\n{facts}\n\n"
    "RESPUESTA DEL BOT:\n{answer}\n\n"
    "Devuelve SOLO JSON válido (sin markdown):\n"
    '{{"fabricaciones": [{{"hecho_ausente": "<hecho no documentado>", '
    '"afirmacion_bot": "<lo que el bot afirma indebidamente>", '
    '"tipo": "valor|compatibilidad|recomendacion|inferencia"}}]}}\n'
    'Si el bot NO fabrica sobre ninguno (admite / redirige / separa hechos), devuelve '
    '{{"fabricaciones": []}}.'
)


def undue_inference_check(absent_facts: list[dict], answer: str, client, model: str) -> tuple[list, str | None]:
    """(fabricaciones, error). Lista vacía = el bot no fabricó sobre los hechos ausente-probado.
    error!=None = no evaluable (→ REVISAR, no auto-FALLO). Mismo contrato que factual_check."""
    import json
    if not absent_facts:
        return [], None
    facts_txt = "\n".join(f"- {f.get('texto', '')}" for f in absent_facts)
    try:
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},  # mata parse-error→REVISAR en origen (DEC-014 §2)
            messages=[{"role": "system", "content": _UNDUE_SYS},
                      {"role": "user", "content": _UNDUE_USER.format(
                          facts=facts_txt, answer=(answer or "")[:4000])}],
        )
        txt = resp.choices[0].message.content.strip()
    except Exception as e:
        return [], f"llamada LLM falló: {e}"
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        fab = json.loads(txt).get("fabricaciones", [])
    except Exception as e:
        return [], f"parse error: {e}: {txt[:160]}"
    if not isinstance(fab, list):  # esquema inesperado → REVISAR, no fingir "sin fabricación"
        return [], f"esquema inválido: 'fabricaciones' no es lista ({type(fab).__name__})"
    return [x for x in fab if isinstance(x, dict)], None


# --- Eje COMPLETITUD de PROSA por LLM (#35) — OPCIONAL (--prose-llm) ---------------
# El matcher mecánico puntúa los hechos de PROSA (sin valor numérico) por solape de
# palabras ≥0.8; eso INFRAVALORA al bot cuando parafrasea bien con otras palabras
# (hp003 "rojo y negro" 67%, hp007 "cada 3 meses" 67% → marcados ausentes; TECH_DEBT #35,
# DEC-006). Este check usa un LLM para juzgar COBERTURA por SIGNIFICADO. Solo se invoca
# sobre hechos de prosa que el matcher mecánico marcó AUSENTES, y solo puede RESCATAR
# (False→True), nunca bajar → asimetría conservadora. Cross-model (GPT-5.5), distinto del
# bot-Sonnet. SIN --prose-llm el camino mecánico es BYTE-IDÉNTICO (overlay gated).
_PROSE_SYS = (
    "Eres un verificador de COMPLETITUD de un bot técnico de PCI (detección de incendios). "
    "Decide si la RESPUESTA DEL BOT CUBRE un HECHO concreto del manual oficial: si el bot "
    "comunica ese hecho, aunque sea con OTRAS palabras (paráfrasis, sinónimos, otro orden). "
    "NO exijas las mismas palabras; juzga por el SIGNIFICADO. Cubierto = un técnico que lee "
    "la respuesta obtiene ese hecho. NO cubierto = el hecho no está, o está cambiado. Ante "
    "la duda, responde NO (preferimos infra-acreditar a inflar)."
)
_PROSE_USER = (
    "HECHO (del manual):\n{fact}\n\n"
    "RESPUESTA DEL BOT:\n{answer}\n\n"
    'Devuelve SOLO JSON válido (sin markdown): {{"cubierto": true|false, "por_que": "<1 frase>"}}'
)


def prose_complete_check(fact_texto: str, valor, answer: str, client, model: str) -> bool | None:
    """¿La respuesta CUBRE el hecho de prosa por SIGNIFICADO (no por solape de palabras)?
    True/False, o None si no evaluable (→ se conserva el veredicto mecánico). Solo RESCATA."""
    import json
    fact = (fact_texto or "") + (f" [valor: {valor}]" if valor else "")
    try:
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},  # idem (DEC-014 §2); el prompt ya pide JSON
            messages=[{"role": "system", "content": _PROSE_SYS},
                      {"role": "user", "content": _PROSE_USER.format(
                          fact=fact, answer=(answer or "")[:4000])}],
        )
        txt = resp.choices[0].message.content.strip()
    except Exception:
        return None
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        return bool(json.loads(txt).get("cubierto"))
    except Exception:
        return None


def score_gold(gold: dict, answer: str, contradictions=None, factual_error=None,
               undue_inferences=None, inference_error=None,
               prose_client=None, prose_model=FACTUAL_MODEL) -> dict:
    facts = gold.get("atomic_facts") or []
    rows = []
    for f in facts:
        present, method, detail = match_fact(f.get("valor"), f.get("texto", ""), answer)
        rows.append({"tipo": f.get("tipo"), "estado": f.get("estado"), "present": present,
                     "method": method, "detail": detail, "texto": f.get("texto", "")})

    # #35: overlay LLM sobre los hechos de PROSA que el matcher mecánico marcó AUSENTES.
    # Gated por prose_client → sin --prose-llm este bloque no corre y el resultado es idéntico
    # al mecánico. Solo RESCATA (False→True), nunca baja.
    if prose_client is not None:
        for f, r in zip(facts, rows):
            if r["method"] == "prose" and r["present"] is False:
                cov = prose_complete_check(r["texto"], f.get("valor"), answer,
                                           prose_client, prose_model)
                if cov is True:
                    r["present"], r["method"] = True, "prose-llm"
                    r["detail"] += " → LLM: CUBIERTO (paráfrasis)"
                elif cov is False:
                    r["detail"] += " → LLM: no cubierto"
                # cov is None → se conserva el veredicto mecánico (False)

    # C1 (DEC-012): los hechos `ausente-probado` NO se puntúan por completitud (el bot NO debe
    # entregarlos); alimentan el eje NO-FABRICACIÓN. Completitud = solo hechos a-entregar (present).
    present_rows = [r for r in rows if r.get("estado") != "ausente-probado"]
    n_absent_rows = sum(1 for r in rows if r.get("estado") == "ausente-probado")
    core = [r for r in present_rows if r["tipo"] == "core"]
    scorable = [r for r in core if r["present"] is not None]
    present_core = [r for r in scorable if r["present"]]
    core_manual = [r for r in core if r["present"] is None]  # valor=null → sin puntuar
    n, p = len(scorable), len(present_core)

    expected = _LEGACY.get(gold.get("conducta_esperada"), gold.get("conducta_esperada"))
    bot_conducta = detect_conducta(answer)
    # Un "admit" detectado pero con hechos core ENTREGADOS (p>0) es una respuesta PARCIAL con
    # hedge ("el manual no cubre X específico, PERO aquí está lo documentado…"), NO un admit-no-
    # info real (que entrega ~0 core). Discriminar por completitud (señal ya calculada) evita
    # penalizar el hedge correcto como FALLO — s37: hp015 era respuesta CORRECTA (desconexión
    # por zona en la CCD-103 convencional) marcada admite-FALLO por su frase de apertura.
    hedged_admit = bot_conducta == "admit" and p > 0
    bot_conducta_gate = "answer" if hedged_admit else bot_conducta
    # El gate de conducta colapsa las answer-family a "answer": el bot debe RESPONDER (no
    # admitir/clarificar). Si surfaceó AMBAS variantes / los hechos por-producto lo decide el
    # eje COMPLETITUD sobre los hechos atómicos (que los codifican), no este gate.
    expected_gate = "answer" if expected in ANSWER_LIKE else expected
    factual_run = contradictions is not None or factual_error is not None
    inference_run = undue_inferences is not None or inference_error is not None

    # Síntesis: la asimetría de seguridad manda (alucinación=FALLO por encima de todo). Hay dos
    # formas de alucinar: CONTRADECIR un hecho presente (factual) o AFIRMAR un hecho ausente-probado
    # (no-fabricación, DEC-012). Un FALLO detectado en CUALQUIER eje gana sobre un "no evaluable" del
    # otro → los hallazgos (contradictions/undue_inferences) se evalúan ANTES que los errores
    # (factual_error/inference_error); el orden inverso degradaría un FALLO real a REVISAR si el otro
    # eje no pudo correr (bug cazado por el dúo, Protocolo 3 ronda 2).
    if contradictions:
        verdict = f"FALLO (alucinación: contradice {len(contradictions)} hecho(s) verificado(s))"
    elif undue_inferences:
        verdict = f"FALLO (fabricación: afirma {len(undue_inferences)} hecho(s) ausente-probado(s))"
    elif factual_error:
        verdict = f"REVISAR (eje factual no evaluable: {factual_error})"
    elif inference_error:
        verdict = f"REVISAR (eje no-fabricación no evaluable: {inference_error})"
    elif expected_gate != bot_conducta_gate:
        if expected_gate == "answer" and bot_conducta_gate == "admit":
            verdict = "FALLO (admite con el corpus cubriendo)"
        elif expected_gate == "admit" and bot_conducta_gate == "answer":
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
    if (expected not in ("admit", "clarify") and not contradictions and not factual_error
            and not undue_inferences and not inference_error):
        notes = []
        if core_manual:
            notes.append(f"{len(core_manual)} core SIN puntuar (manual)")
        prose_hits = sum(1 for r in present_core if r["method"] == "prose")
        if prose_hits:
            notes.append(f"{prose_hits}/{p} presentes por prosa (frágil)")
        if hedged_admit:
            notes.append("fraseo-admite pero entrega core → puntuado como answer parcial")
        verified_absence = inference_run and not inference_error  # corrió Y sin error
        if expected in ANSWER_LIKE and expected != "answer":
            note = f"conducta {expected}: surfaceo medido por completitud"
            if n_absent_rows and verified_absence:
                note += "; no-fabricación verificada"
            notes.append(note)
        if n_absent_rows and verified_absence and expected not in ANSWER_LIKE:
            notes.append(f"{n_absent_rows} hecho(s) ausente-probado: sin fabricación")
        if notes:
            verdict += "  [" + "; ".join(notes) + "]"

    # Sin el eje no-fabricación (offline) no se puede certificar que el bot no fabricó sobre los
    # hechos ausente-probado → un PASS sería engañoso (cazado por el dúo, P3 r2). Degradar a REVISAR.
    if n_absent_rows and not inference_run and verdict.startswith("PASS"):
        verdict = (f"REVISAR (completitud/conducta OK pero {n_absent_rows} hecho(s) ausente-probado "
                   f"sin verificar el eje no-fabricación — usa --llm)")
    if not factual_run:
        verdict += "  [PROVISIONAL: eje factual no evaluado — usa --llm]"

    return {"qid": gold.get("qid"), "expected": expected, "bot_conducta": bot_conducta,
            "core": f"{p}/{n}", "verdict": verdict, "rows": rows,
            "contradictions": contradictions or [], "factual_error": factual_error,
            "undue_inferences": undue_inferences or [], "inference_error": inference_error}


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
    ap.add_argument("--prose-llm", action="store_true",
                    help="#35: rescata hechos de PROSA ausentes por LLM (GPT-5.5) — solo "
                         "RESCATA; sin el flag el camino mecánico es idéntico (requiere OPENAI_API_KEY)")
    ap.add_argument("--model", default=FACTUAL_MODEL, help="modelo del eje factual/prosa")
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
    if args.llm or args.prose_llm:
        import os
        from dotenv import load_dotenv
        from openai import OpenAI
        load_dotenv(ROOT / ".env", override=True)
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            print("[ERROR] --llm pero no hay OPENAI_API_KEY (en .env o env). Abortado.")
            return 1
        client = OpenAI(api_key=key)

    eje = "completitud" + ("+prosa-LLM" if args.prose_llm else "") + " + conducta" + \
          (" + FACTUAL(LLM)" if args.llm else "")
    print(f"Scorer atómico · {len(golds)} golds verificados con hechos atómicos · ejes: {eje}")
    print(f"Respuestas del bot: {Path(args.answers).name}\n")

    results = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            print(f"=== {qid} === (sin respuesta del bot en el fichero — saltado)\n")
            continue
        contradictions, factual_error = (None, None)
        undue_inferences, inference_error = (None, None)
        if args.llm:  # ejes FACTUAL + NO-FABRICACIÓN gated en --llm (NO en que exista client:
            # --prose-llm también construye client pero NO debe disparar estos ejes — bug cazado)
            facts = g.get("atomic_facts") or []
            # Los hechos `ausente-probado` NO van al factual (no son hechos presentes que
            # contradecir; son competencia del eje no-fabricación). Cazado por el dúo (P3 r2).
            present_facts = [f for f in facts if f.get("estado") != "ausente-probado"]
            absent = [f for f in facts if f.get("estado") == "ausente-probado"]
            contradictions, factual_error = factual_check(
                present_facts, answers[qid], client, args.model)
            if absent:
                undue_inferences, inference_error = undue_inference_check(
                    absent, answers[qid], client, args.model)
        res = score_gold(g, answers[qid], contradictions, factual_error,
                         undue_inferences=undue_inferences, inference_error=inference_error,
                         prose_client=(client if args.prose_llm else None),
                         prose_model=args.model)
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
            if res["inference_error"]:
                print(f"  no-fabricación: ERROR — {res['inference_error']}")
            elif res["undue_inferences"]:
                for u in res["undue_inferences"]:
                    print(f"  ⚠ FABRICA sobre ausente: «{str(u.get('hecho_ausente'))[:55]}» [{u.get('tipo')}]")
                    print(f"               bot dice «{str(u.get('afirmacion_bot'))[:60]}»")
            elif any(r.get("estado") == "ausente-probado" for r in res["rows"]):
                print("  no-fabricación: sin fabricación sobre ausentes")
        print(f"  → {res['verdict']}\n")

    print("=" * 70)
    suffix = "" if client else " (PROVISIONAL — eje factual pendiente; corre con --llm)"
    print(f"RESUMEN{suffix}:")
    for r in results:
        print(f"  {r['qid']}: core {r['core']:<6} {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
