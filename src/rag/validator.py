"""Cross-model grounding validator.

Post-generation audit of the Sonnet answer by a DIFFERENT model (Opus) to
detect factual claims not supported by the retrieved chunks. Sesión 11
iteración H showed that same-model validation (Sonnet validating Sonnet)
regressed judge PASS by sharing the generator's blind spots — eco cámara.
Using a different model family breaks that coupling.

Output is machine-readable JSON so the caller can react:
  - 0 unsupported claims → ship answer as-is.
  - 1..N unsupported → retry generator with the specific feedback (the
    feedback comes from Opus, not from Sonnet, so it's not self-referential).
  - N+ unsupported → fall back to an honest admit_no_info to avoid shipping
    a contaminated answer.

The validator does NOT generate a replacement answer — only an audit — to
avoid introducing hallucinations in the validation step itself.
"""

from __future__ import annotations

import json
import logging
import re

import anthropic

from ..config import ANTHROPIC_API_KEY, VALIDATOR_MODEL, VALIDATOR_MAX_TOKENS

logger = logging.getLogger(__name__)


AUDIT_PROMPT = """Eres un auditor de calidad estricto. Revisas la respuesta de un asistente técnico (que usa fragmentos de manuales PCI como fuente única) y detectas AFIRMACIONES NO SOPORTADAS por los fragmentos.

PREGUNTA DEL TÉCNICO:
{question}

FRAGMENTOS DISPONIBLES (única fuente de verdad):
{chunks}

RESPUESTA DEL ASISTENTE:
{answer}

REGLAS DEL AUDIT:
1. Una afirmación factual es: un valor numérico (voltaje, corriente, longitud, tiempo, capacidad, rango), un nombre de sección/página/figura, un nombre de terminal/borne/LED/tecla/menú, un nombre de producto/modelo/software/herramienta, una referencia a norma (EN54, UNE, RIPCI…), o un paso/procedimiento concreto.
2. Una afirmación está SOPORTADA si aparece (literalmente o por paráfrasis directa) en cualquiera de los fragmentos. Los marcadores `[F<n>]` del asistente indican de qué fragmento dice haberla sacado; verifica si el dato aparece en ese fragmento o en otro (paráfrasis cuenta).
3. Una afirmación NO está soportada si:
   - el valor numérico concreto no aparece en ningún fragmento,
   - o el nombre de sección/producto/norma no aparece en ningún fragmento,
   - o el procedimiento inventa pasos que los fragmentos no describen.
4. IGNORA las afirmaciones generales sin datos concretos ("debe verificarse con el fabricante", "consulta el manual físico", "esta guía no describe X"). Solo te importa el contenido factual concreto.
5. IGNORA los marcadores `[F<n>]` como tales — no son afirmaciones, son citas.
6. IGNORA la línea "Fuente:" al final (citación obligatoria del nombre del manual; no es una afirmación técnica).
7. IGNORA sugerencias de follow-up del tipo "También puedo ayudarte con X, Y, Z" — son propuestas de temas, no afirmaciones factuales.

Para cada afirmación NO SOPORTADA, extrae:
  - claim: la afirmación exacta tal como aparece en la respuesta (cita literal breve, ≤120 chars).
  - reason: por qué no está soportada (valor inventado / sección inventada / norma inventada / procedimiento inventado / producto no mencionado en fragmentos / otro).

Si la respuesta es del tipo "no tengo este manual" sin datos inventados, `unsupported` va vacío.
Si el asistente extiende un admit con datos inventados ("no tengo el manual, pero puedes usar UNE-EN 12845"), la norma añadida cuenta como no soportada.

Responde ÚNICAMENTE con JSON en este formato:
{{
  "unsupported": [
    {{"claim": "...", "reason": "..."}},
    ...
  ]
}}

Si no encuentras afirmaciones no soportadas: {{"unsupported": []}}"""


# Answer patterns that DON'T warrant validation (would waste Opus calls).
_ADMIT_PATTERNS = [
    r"no he encontrado información",
    r"no tengo (información|ese dato|el manual|documentación)",
    r"no dispongo de (información|documentación)",
    r"no está (?:incluido|cubierto) en",
    r"no cuento con",
]
_ADMIT_REGEX = re.compile("|".join(_ADMIT_PATTERNS), re.IGNORECASE)

# Heuristic: factual content worth validating.
# ≥3 numeric values with units, OR ≥3 citation markers [F<n>], OR length > 800.
_NUMERIC_WITH_UNIT = re.compile(
    r"\d[\d.,]*\s*"
    r"(?:V|Vdc|VDC|Vac|VAC|mA|A|W|Ω|ohm|ohmios|kΩ|MΩ|"
    r"m|km|mm|cm|"
    r"s|seg|segundos|min|minutos|h|horas|ms|"
    r"°C|ºC|K|"
    r"Hz|kHz|MHz|"
    r"F|µF|uF|nF|pF|"
    r"dB|dBA|"
    r"kg|g|"
    r"%|"
    r"puntos|zonas|lazos|bucles|dispositivos|detectores)",
    re.IGNORECASE,
)
_CITATION_MARKER = re.compile(r"\[F\d+\]")


def warrants_validation(answer: str) -> bool:
    """Decide whether the answer is worth sending to the validator.

    Skip for:
      - Short answers (< 200 chars): not enough to hallucinate meaningfully.
      - Pure admit_no_info: no factual claims to validate.
      - Low factual density: few numbers, few citations, short length.

    Validate when the answer has enough factual surface that invention is
    a real risk.
    """
    if len(answer) < 200:
        return False

    # Pure admit (short, no factual add-ons) — skip.
    if len(answer) < 400 and _ADMIT_REGEX.search(answer):
        return False

    numeric_hits = len(_NUMERIC_WITH_UNIT.findall(answer))
    citation_hits = len(_CITATION_MARKER.findall(answer))

    if numeric_hits >= 3:
        return True
    if citation_hits >= 3:
        return True
    if len(answer) > 800:
        return True

    return False


def audit_grounding(
    question: str,
    chunks: list[dict],
    answer: str,
) -> dict:
    """Audit the answer's grounding against the chunks. Returns dict with
    key 'unsupported': list of {claim, reason} entries. Empty list means
    the answer is clean.

    Never raises: on any failure (API error, malformed JSON, etc.) returns
    {"unsupported": [], "error": "..."} so the caller defaults to pass-through.
    """
    if not chunks:
        # No chunks → generator would have returned a scripted fallback.
        return {"unsupported": []}

    try:
        chunks_block = _format_chunks_for_audit(chunks)
        prompt = AUDIT_PROMPT.format(
            question=question,
            chunks=chunks_block,
            answer=answer,
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=VALIDATOR_MODEL,
            max_tokens=VALIDATOR_MAX_TOKENS,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Opus may wrap JSON in ```json fences, preface with prose, or append
        # commentary. Strip code fences, then use raw_decode() which tolerates
        # trailing content (fixes "Extra data" JSONDecodeError seen in smoke
        # test when Opus emitted JSON followed by a free-form note).
        candidate = raw
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
        if fence:
            candidate = fence.group(1)
        else:
            # Skip any prose before the first `{`.
            brace_idx = candidate.find("{")
            if brace_idx == -1:
                logger.warning("Validator returned non-JSON: %r", raw[:200])
                return {"unsupported": [], "error": "no_json"}
            candidate = candidate[brace_idx:]

        try:
            parsed, _end = json.JSONDecoder().raw_decode(candidate)
        except json.JSONDecodeError as e:
            logger.warning("Validator JSON decode failed: %s | raw=%r", e, raw[:200])
            return {"unsupported": [], "error": "bad_json"}
        unsupported = parsed.get("unsupported", [])
        if not isinstance(unsupported, list):
            logger.warning("Validator 'unsupported' not a list: %r", unsupported)
            return {"unsupported": [], "error": "bad_shape"}

        # Sanitize: keep only well-formed entries.
        clean = []
        for entry in unsupported:
            if isinstance(entry, dict) and entry.get("claim"):
                clean.append({
                    "claim": str(entry["claim"])[:200],
                    "reason": str(entry.get("reason", ""))[:200],
                })
        return {"unsupported": clean}

    except Exception as e:  # noqa: BLE001 — validator is best-effort
        logger.warning("Validator failed: %s", e)
        return {"unsupported": [], "error": str(e)[:200]}


def _format_chunks_for_audit(chunks: list[dict]) -> str:
    """Render chunks with the same [Fragmento N] numbering the generator
    uses, so the validator can verify [F<n>] markers against the right chunk.
    Content truncated at 2000 chars (same as judge after calibration)."""
    lines = []
    for i, c in enumerate(chunks[:8]):
        product = c.get("product_model", "?")
        section = c.get("section_title") or ""
        content = (c.get("content") or "")[:2000]
        header = f"[Fragmento {i + 1} | Producto: {product} | Sección: {section}]"
        lines.append(f"{header}\n{content}")
    return "\n\n---\n\n".join(lines)


def build_retry_feedback(unsupported: list[dict]) -> str:
    """Build a text snippet to inject into the generator's retry message,
    listing the specific claims Opus flagged. This goes INTO the user-side
    retry prompt so the generator sees concrete corrections, not vague
    'try harder' feedback.
    """
    if not unsupported:
        return ""
    lines = ["Un auditor externo detectó estas afirmaciones NO soportadas por los fragmentos:"]
    for i, entry in enumerate(unsupported, 1):
        lines.append(f"{i}. \"{entry['claim']}\" — {entry['reason']}")
    lines.append(
        "\nReescribe la respuesta ELIMINANDO esas afirmaciones concretas. "
        "Si eran el núcleo de la respuesta, admite honestamente que el manual "
        "no especifica ese dato. Mantén todo lo demás que SÍ está soportado."
    )
    return "\n".join(lines)
