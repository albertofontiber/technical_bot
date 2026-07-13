"""Deterministic source-derived windows for reranking long technical chunks."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

_STOP = {
    "de", "del", "la", "las", "el", "los", "un", "una", "y", "o", "en", "por",
    "para", "como", "con", "que", "se", "al", "es", "su", "the", "and", "for", "of",
    "to", "a", "como", "cual", "cuales",
}


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in value if not unicodedata.combining(char)).casefold()


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", _norm(text))
        if len(token) >= 2 and token not in _STOP
    ]


def _candidate_windows(content: str, max_chars: int) -> list[tuple[int, int, str]]:
    if not content:
        return [(0, 0, "")]
    spans = []
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", content, flags=re.DOTALL):
        start, end = match.span()
        text = content[start:end]
        if len(text) <= max_chars:
            spans.append((start, end, text))
            continue
        stride = max(1, max_chars // 2)
        cursor = 0
        while cursor < len(text):
            local_end = min(len(text), cursor + max_chars)
            if local_end < len(text):
                boundary = text.rfind(" ", cursor + max_chars // 2, local_end)
                if boundary > cursor:
                    local_end = boundary
            fragment = text[cursor:local_end].strip()
            if fragment:
                local_start = text.find(fragment, cursor, local_end + 1)
                spans.append((start + local_start, start + local_start + len(fragment), fragment))
            if local_end >= len(text):
                break
            cursor = max(cursor + stride, local_end - max_chars // 4)
    return spans or [(0, min(len(content), max_chars), content[:max_chars])]


def _score(text: str, query_terms: Counter, hint_terms: Counter) -> float:
    terms = Counter(_tokens(text))
    score = 0.0
    for token, frequency in query_terms.items():
        score += min(terms[token], frequency) * (1.0 + math.log1p(len(token)))
    for token, frequency in hint_terms.items():
        score += min(terms[token], frequency) * 2.0 * (1.0 + math.log1p(len(token)))
    return score


def best_evidence_window(
    query: str,
    content: str,
    *,
    navigation_hint: str | None = None,
    max_chars: int = 800,
) -> dict:
    """Return the best exact substring of ``content`` for relevance judgement.

    ``navigation_hint`` may be a matched retrieval surrogate, but the returned
    text is always copied from the parent source chunk.  No generated text is
    exposed to the downstream reranker as evidence.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    query_terms = Counter(_tokens(query))
    hint_terms = Counter(_tokens(navigation_hint or ""))
    candidates = _candidate_windows(content or "", max_chars)
    scored = [(_score(text, query_terms, hint_terms), start, end, text) for start, end, text in candidates]
    score, start, end, text = min(scored, key=lambda item: (-item[0], item[1], item[2]))
    return {
        "text": text,
        "start": start,
        "end": end,
        "score": round(score, 6),
        "used_navigation_hint": bool(navigation_hint),
    }


def build_rerank_preview(
    query: str,
    content: str,
    *,
    navigation_hint: str | None = None,
    head_chars: int = 800,
    evidence_chars: int = 400,
) -> dict:
    """Preserve the historical head and add one bounded source-only span.

    The extra span is included only when it starts outside the historical head.
    This keeps existing head evidence intact while exposing a late region that
    caused the navigation hit.  The returned preview is diagnostic metadata;
    callers still return the full parent chunk to synthesis.
    """
    if head_chars <= 0 or evidence_chars <= 0:
        raise ValueError("head_chars and evidence_chars must be positive")
    content = content or ""
    head = content[:head_chars]
    evidence = best_evidence_window(
        query,
        content,
        navigation_hint=navigation_hint,
        max_chars=evidence_chars,
    )
    appended = evidence["start"] >= head_chars and bool(evidence["text"])
    preview = head
    if appended:
        preview += "\n\n[SPAN FUENTE NAVEGADO]\n" + evidence["text"]
    return {
        "text": preview,
        "head_chars": min(len(content), head_chars),
        "evidence": evidence,
        "evidence_appended": appended,
        "source_only": head in content and (not appended or evidence["text"] in content),
    }
