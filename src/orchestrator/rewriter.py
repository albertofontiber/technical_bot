"""Economical source-bound rewriter for Phase-1 multi-turn (S281 / MT-1a).

The deterministic router (``conversation_policy_impl``) only calls a rewriter on
the NARROW slice it cannot resolve by re-attaching the last product: a turn whose
anaphora points at prior CONTENT (``"¿y ese aviso cómo se borra?"`` — the antecedent
is the *Earth Fault* notice, not just the model). For that slice this module turns
the follow-up into a STANDALONE retrieval query, source-bound to the working state,
preserving technical codes verbatim.

Two prompt variants (design v2 §1.5, A/B authorised by Alberto):

  * ``REWRITE_PROMPT_FONTIBER``   — our prompt: source-bound, preserve technical
    tokens VERBATIM, keep the original language, output = only the standalone
    question. This is the production default.
  * ``REWRITE_PROMPT_CONDENSE_LC`` — the canonical LangChain condense-question
    prompt, faithfully translated to Spanish, for the authorised A/B.

DETERMINISTIC POST-VALIDATION (fail-closed). After the LLM answers, the rewriter
runs a $0 deterministic check: every technical token of the RAW turn (numbers,
hyphen/kΩ/V/A codes, and any ``NON_PRODUCT_CODES`` present) plus every resolved
target model must survive VERBATIM in the rewrite, and the length must be
reasonable. If the check fails the rewriter returns ``None`` — the caller then
falls back to ``carry_forward`` (the LLM call is $-already-spent but the conduct is
safe; the failure is traced). This is exactly the S99b / DEC-092 trap (a rewrite
that mutated ``RS-485`` / ``6,8 kΩ`` away) turned into a mechanical guard.

NO REAL API CALLS IN THIS LANE. The Anthropic client is injected (``client=``);
tests pass a fake. The real ``--e2e`` run (paid, Sonnet) is the orchestrator's job.
The client pattern mirrors ``src/rag/generator.py``
(``anthropic.Anthropic(...).messages.create(...)`` → ``response.content[0].text``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from .conversation_policy import NON_PRODUCT_CODES, WorkingState

logger = logging.getLogger(__name__)

# Tier frozen for the eval (MT-1b vara §1: rewriter = Sonnet). The exact model
# string is a parameter so the orchestrator pins it at the paid --e2e run; the
# default follows the lane brief. NOTE (drift, surfaced in the lane report): the
# repo generator uses ``config.LLM_MODEL`` = "claude-sonnet-4-6" and the current
# Sonnet id is "claude-sonnet-5"; no call happens in this lane, so the default is
# informational only — the paid run selects the live id.
DEFAULT_REWRITER_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 256


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
REWRITE_PROMPT_FONTIBER = """\
Eres un reformulador de preguntas para un asistente técnico de PCI (protección \
contra incendios). Recibes el historial de una conversación y la última pregunta \
de un técnico, que puede depender del contexto anterior (pronombres, elipsis o \
referencias como "ese aviso" o "esa entrada").

Tu ÚNICA tarea es reescribir la última pregunta como una pregunta AUTÓNOMA, que \
se entienda sin el historial, para usarla como consulta de recuperación.

REGLAS ESTRICTAS:
1. NO respondas la pregunta. Devuelve SOLO la pregunta reformulada, sin preámbulo \
   ni explicación.
2. Conserva el idioma original de la pregunta (normalmente español).
3. Preserva VERBATIM todos los códigos técnicos, modelos, números, unidades y \
   referencias (p.ej. CAD-250, M710, MI-DMMI, RS-485, 24V, 6,8 kΩ, "Earth Fault"). \
   NUNCA los traduzcas, normalices ni alteres.
4. Inlina el antecedente al que se refiere la pregunta (el producto o el contenido \
   previo) tomándolo EXCLUSIVAMENTE del historial. No inventes modelos, datos ni \
   hechos que no estén en el historial.
5. Si la última pregunta ya es autónoma, devuélvela tal cual.
6. Sé conciso: una sola pregunta."""


# Canonical LangChain CONDENSE_QUESTION_PROMPT, faithfully translated to Spanish.
# (Original EN: "Given the following conversation and a follow up question,
# rephrase the follow up question to be a standalone question, in its original
# language.\n\nChat History:\n{chat_history}\nFollow Up Input: {question}\n
# Standalone question:")
REWRITE_PROMPT_CONDENSE_LC = """\
Dada la siguiente conversación y una pregunta de seguimiento, reformula la \
pregunta de seguimiento para que sea una pregunta autónoma, en su idioma original.

Historial de conversación:
{chat_history}
Entrada de seguimiento: {question}
Pregunta autónoma:"""


# ---------------------------------------------------------------------------
# Working state -> chat history
# ---------------------------------------------------------------------------
def _render_chat_history(ws: WorkingState) -> str:
    """A compact, source-bound transcript for the rewriter. Only the durable
    working state is used — never the previous BOT text as evidence (design §1.5
    re-ground rule); ``last_answer_excerpt`` is included as CONTEXT for anaphora
    resolution, not as a source of facts."""
    lines: list[str] = []
    if ws.last_target_models:
        lines.append(f"Producto(s) en contexto: {', '.join(ws.last_target_models)}")
    if ws.last_query:
        lines.append(f"Usuario: {ws.last_query}")
    if ws.last_answer_excerpt:
        lines.append(f"Asistente: {ws.last_answer_excerpt}")
    return "\n".join(lines) if lines else "(sin historial)"


def _build_request(
    variant: str, query: str, ws: WorkingState
) -> tuple[str | None, str]:
    """Return ``(system, user_text)`` for the given prompt variant."""
    history = _render_chat_history(ws)
    if variant == "condense_lc":
        # The LC prompt is a single self-contained block (no separate system).
        user = REWRITE_PROMPT_CONDENSE_LC.format(chat_history=history, question=query)
        return None, user
    if variant == "fontiber":
        user = (
            f"Historial de la conversación:\n{history}\n\n"
            f"Pregunta de seguimiento: {query}\n\nPregunta autónoma:"
        )
        return REWRITE_PROMPT_FONTIBER, user
    raise ValueError(f"prompt_variant desconocido: {variant!r} (usa 'fontiber'|'condense_lc')")


# ---------------------------------------------------------------------------
# Deterministic post-validation (fail-closed) — the $0 guard
# ---------------------------------------------------------------------------
# Technical tokens that must never be mutated by a rewrite. Order in the
# alternation is longest-first so hyphenated codes win over their digit tails.
_TECH_TOKEN_RE = re.compile(
    r"[A-Za-zÀ-ÿ0-9]+(?:[-/][A-Za-zÀ-ÿ0-9]+)+"     # CAD-250, MI-DMMI, RS-485, M710/MI-DMMI
    r"|\d+(?:[.,]\d+)?\s*(?:kΩ|Ω|kV|mA|Ah|V|A|W|Hz)"  # 24V, 6,8 kΩ, 500mA
    r"|\d+[.,]\d+"                                    # 6,8
    r"|[A-Za-zÀ-ÿ]*\d[A-Za-zÀ-ÿ0-9]*"               # M710, RS485, 485, IP54
)

# A rewrite longer than this is treated as a preamble/answer leak, not a question.
_MAX_ABS_LEN = 400
_MAX_LEN_FACTOR = 6  # relative to the raw turn


def _required_tokens(raw_turn: str, ws: WorkingState) -> list[str]:
    """The verbatim tokens the rewrite MUST preserve: technical tokens of the raw
    turn + any NON_PRODUCT_CODES present + the resolved target models (the rewrite
    exists to inline them, so dropping them is a broken rewrite)."""
    required: list[str] = []
    seen: set[str] = set()

    def _add(tok: str) -> None:
        if tok and tok not in seen:
            seen.add(tok)
            required.append(tok)

    for m in _TECH_TOKEN_RE.finditer(raw_turn):
        _add(m.group(0))
    low = raw_turn.lower()
    for code in NON_PRODUCT_CODES:
        if code.lower() in low:
            # Preserve the surface form as it appears in the raw turn.
            idx = low.find(code.lower())
            _add(raw_turn[idx: idx + len(code)])
    for model in ws.last_target_models:
        if model not in NON_PRODUCT_CODES:
            _add(model)
    return required


def validate_rewrite(
    raw_turn: str, ws: WorkingState, rewrite_text: str | None
) -> tuple[bool, str]:
    """Deterministic fail-closed check. Returns ``(ok, reason)``."""
    if rewrite_text is None:
        return False, "rewrite_is_none"
    text = rewrite_text.strip()
    if not text:
        return False, "empty"
    max_len = max(_MAX_ABS_LEN, _MAX_LEN_FACTOR * len(raw_turn))
    if len(text) > max_len:
        return False, f"too_long({len(text)}>{max_len})"
    missing = [tok for tok in _required_tokens(raw_turn, ws) if tok not in text]
    if missing:
        return False, f"dropped_tokens={missing}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
# The rewriter returned matches ``RewriteFn = Callable[[str, WorkingState], str]``
# but may return ``None`` when post-validation fails (the caller falls back to
# carry_forward). Runtime-typed here as ``str | None``.
RewriteFn = Callable[[str, WorkingState], "str | None"]


@dataclass(frozen=True)
class _Rewriter:
    """Callable wrapper: build request -> call injected client -> validate."""

    client: Any
    prompt_variant: str
    model: str
    max_tokens: int
    temperature: float = 0.0  # reproducibility (mirrors src/rag/generator.py)

    def __call__(self, query: str, working_state: WorkingState) -> str | None:
        system, user_text = _build_request(self.prompt_variant, query, working_state)
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user_text}],
        }
        if system is not None:
            request["system"] = system
        try:
            response = self.client.messages.create(**request)
            raw = response.content[0].text
        except Exception as exc:  # network / API / shape — fail closed, never crash the turn
            logger.warning("rewriter call failed (%s); falling back to carry_forward", exc)
            return None
        ok, reason = validate_rewrite(query, working_state, raw)
        if not ok:
            logger.info("rewrite rejected by post-validation (%s); fallback to carry_forward", reason)
            return None
        return raw.strip()


def make_rewriter(
    client: Any = None,
    prompt_variant: str = "fontiber",
    model: str = DEFAULT_REWRITER_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> RewriteFn:
    """Build the economical source-bound rewriter (a ``RewriteFn``).

    ``client`` is an Anthropic client (``anthropic.Anthropic``). When ``None`` a
    real client is constructed lazily on first use with the repo's key
    (``config.ANTHROPIC_API_KEY``) — that path is ONLY exercised by the paid
    ``--e2e`` run, never in this lane's tests (which inject a fake client).
    ``prompt_variant`` is ``'fontiber'`` (default) or ``'condense_lc'`` (A/B).
    """
    if prompt_variant not in ("fontiber", "condense_lc"):
        raise ValueError(f"prompt_variant desconocido: {prompt_variant!r}")

    if client is None:
        # Lazy: no client is built until the rewriter is actually called (paid run).
        class _LazyClient:
            _real: Any = None

            @property
            def messages(self) -> Any:
                if _LazyClient._real is None:
                    import anthropic  # local import; not needed for the $0 lane

                    from ..config import ANTHROPIC_API_KEY

                    _LazyClient._real = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                return _LazyClient._real.messages

        client = _LazyClient()

    return _Rewriter(
        client=client,
        prompt_variant=prompt_variant,
        model=model,
        max_tokens=max_tokens,
    )


__all__ = [
    "REWRITE_PROMPT_FONTIBER",
    "REWRITE_PROMPT_CONDENSE_LC",
    "DEFAULT_REWRITER_MODEL",
    "make_rewriter",
    "validate_rewrite",
    "RewriteFn",
]
