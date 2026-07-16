"""Experimental shadow-only coverage for missing procedural prerequisites.

This module is deliberately unreachable from the serving path.  It receives
only the user query, already-served rows and a bounded candidate universe.  It
does not receive QIDs, expected facts, gold receipts or answer text.

The rules are conservative and evidence-bearing:

* follow an explicit intra-document section reference only when the referenced
  section repeats a task term from the reference window;
* add an access/unlock prerequisite only when the requested task appears after
  that prerequisite in the source;
* complete a quantified licensed-loop prerequisite only when one source row
  establishes the same capability anchor, loop and licence relationship.

Every appended row carries an immutable source-span receipt.  A rule match is
retrieval-stage evidence only; it is never a semantic-validation or OK claim.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from src.rag.catalog import normkey

LANE = "procedure_bundle_coverage_v2_shadow"
MAX_SELECTED = 1
MAX_CARD_CHARS = 720
MAX_CARDS_PER_ROW = 2

_SECTION_REFERENCE = re.compile(
    r"\b(?:cap(?:[ií]tulo)?\.?|secci[oó]n|section|chapter)\s*"
    r"(\d+(?:\.\d+)+)\b",
    re.I,
)
_PROCEDURAL_QUERY = re.compile(
    r"\b(?:como|how|anad(?:ir|e|ing)\w*|add(?:ed|ing)?|alta|"
    r"configur(?:ar|e|ing|ation)|program(?:ar|e|ming)|"
    r"diagnostic(?:ar|a|e|ing)|comprob(?:ar|acion)|check(?:ing)?|leer|read)\b",
    re.I,
)
_ACCESS_UNLOCK = re.compile(
    r"(?:nivel|level)\s*3[\s\S]{0,700}(?:desbloq\w*\s+(?:la\s+)?memoria|"
    r"unlock\w*\s+(?:the\s+)?memory)|"
    r"(?:desbloq\w*\s+(?:la\s+)?memoria|unlock\w*\s+(?:the\s+)?memory)"
    r"[\s\S]{0,700}(?:nivel|level)\s*3",
    re.I,
)
_LICENSED_LOOP = re.compile(
    r"(?:licen[cs]ia|licen[cs]e)[\s\S]{0,180}"
    r"(?:cada\s+(?:circuito\s+de\s+)?lazo|each\s+loop(?:\s+circuit)?|"
    r"each[\s\S]{0,50}?loop(?:\s+circuit)?|per[\s\S]{0,50}?loop(?:\s+circuit)?)|"
    r"(?:cada\s+(?:circuito\s+de\s+)?lazo|each\s+loop(?:\s+circuit)?|"
    r"each[\s\S]{0,50}?loop(?:\s+circuit)?|per[\s\S]{0,50}?loop(?:\s+circuit)?)"
    r"[\s\S]{0,180}(?:licen[cs]ia|licen[cs]e)",
    re.I,
)
_LOOP = re.compile(r"\b(?:lazo|loop)\w*\b", re.I)
_LICENSE = re.compile(r"\blicen[cs]\w*\b", re.I)
_LOOP_CAPABILITY_BEFORE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z][A-Z0-9-]{2,11})\s+"
    r"(?:circuito\s+de\s+)?(?:lazo|loop)\b"
)
_LOOP_CAPABILITY_AFTER = re.compile(
    r"\b(?:lazo|loop)(?:\s+de)?\s+([A-Z][A-Z0-9-]{2,11})(?![A-Za-z0-9])"
)
_STRUCTURED_VALUE = re.compile(r"\b[A-Z]{1,4}\d{1,4}\b")
_HEX64 = re.compile(r"[0-9a-fA-F]{64}")
_OPERATIONAL = re.compile(
    r"\b(?:puls\w*|press\w*|seleccion\w*|select\w*|valor\w*|value\w*|"
    r"posici[oó]n|position|paso|step|proced\w*)\b",
    re.I,
)
_REFERENCE_QUERY_STOP = {
    "como", "cual", "donde", "cuando", "panel", "central", "detector",
    "sistema", "manual", "configuracion", "configurar", "rango", "valor",
    "funcionamiento", "probable", "equipo", "equipos", "nuevo", "inicial",
    "puesta", "marcha", "what", "which", "where", "when", "with", "from",
    "this", "that", "does", "into", "after", "before", "read", "check",
}
_CAPABILITY_STOP = {"LEVEL", "PANEL", "SYSTEM", "MANUAL", "EQUIPO", "LAZO"}


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _manufacturer(row: dict[str, Any]) -> str:
    return _fold(row.get("manufacturer"))


def _model_variants(value: object) -> set[str]:
    """Conservative exact aliases, including compact ``E10/E15`` notation."""
    raw = str(value or "").strip()
    if not raw:
        return set()
    variants = {normkey(raw)}
    parts = [part.strip() for part in raw.split("/") if part.strip()]
    if len(parts) == 2:
        left_words = parts[0].split()
        right_words = parts[1].split()
        if left_words and right_words:
            prefix = " ".join(left_words[:-1])
            variants.add(normkey(parts[0]))
            variants.add(normkey(f"{prefix} {parts[1]}".strip()))
    return {variant for variant in variants if variant}


def _product_compatible(candidate: dict[str, Any], seeds: list[dict[str, Any]]) -> bool:
    """Fail closed: same explicit manufacturer and exact canonical model alias."""
    candidate_manufacturer = _manufacturer(candidate)
    candidate_models = _model_variants(candidate.get("product_model"))
    if not candidate_manufacturer or not candidate_models:
        return False
    for seed in seeds:
        if _manufacturer(seed) != candidate_manufacturer:
            continue
        if candidate_models & _model_variants(seed.get("product_model")):
            return True
    return False


def _identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("document_id") or ""),
        str(row.get("extraction_sha256") or ""),
        _fold(row.get("source_file")),
    )


def _same_document(candidate: dict[str, Any], seeds: list[dict[str, Any]]) -> bool:
    candidate_identity = _identity(candidate)
    for seed in seeds:
        seed_identity = _identity(seed)
        if candidate_identity[0] and seed_identity[0]:
            if candidate_identity[0] == seed_identity[0]:
                return True
            continue
        if candidate_identity[1] and seed_identity[1]:
            if candidate_identity[1] == seed_identity[1]:
                return True
            continue
        if (
            not candidate_identity[0]
            and not candidate_identity[1]
            and not seed_identity[0]
            and not seed_identity[1]
            and candidate_identity[2]
            and candidate_identity[2] == seed_identity[2]
        ):
            return True
    return False


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_span_card(
    row: dict[str, Any], start: int, end: int, facet: str
) -> dict[str, Any]:
    content = str(row.get("content") or "")
    if not content:
        raise ValueError("coverage candidate has no content")
    start = max(0, start)
    end = min(len(content), max(start, end))
    if end - start > MAX_CARD_CHARS:
        end = start + MAX_CARD_CHARS
    quote = content[start:end]
    return {
        "candidate_id": str(row.get("id") or ""),
        "document_id": str(row.get("document_id") or ""),
        "extraction_sha256": str(row.get("extraction_sha256") or ""),
        "content_sha256": _sha256(content),
        "quote_sha256": _sha256(quote),
        "start": start,
        "end": end,
        "quote": quote,
        "facet": facet,
        "receipt_type": "immutable_exact_source_span",
    }


def _exact_card(row: dict[str, Any], match: re.Match[str] | None, facet: str) -> dict:
    content = str(row.get("content") or "")
    if not content:
        raise ValueError("coverage candidate has no content")
    if match is None:
        start, end = 0, min(len(content), MAX_CARD_CHARS)
    else:
        center_start, center_end = match.span()
        match_middle = (center_start + center_end) // 2
        start = max(0, match_middle - MAX_CARD_CHARS // 2)
        end = min(len(content), start + MAX_CARD_CHARS)
        start = max(0, end - MAX_CARD_CHARS)
    return _source_span_card(row, start, end, facet)


def _aligned_table_cards(
    row: dict[str, Any], anchors: set[str], facet: str
) -> list[dict[str, Any]]:
    """Return up to two atomic table rows with distinct structured values."""
    content = str(row.get("content") or "")
    cards: list[dict[str, Any]] = []
    seen_values: set[str] = set()
    offset = 0
    for line in content.splitlines(keepends=True):
        line_without_break = line.rstrip("\r\n")
        line_terms = set(_fold(line_without_break).split())
        values = set(_STRUCTURED_VALUE.findall(line_without_break))
        new_values = values - seen_values
        if (
            line_without_break.count("|") >= 3
            and bool(anchors & line_terms)
            and bool(new_values)
            and len(line_without_break) <= MAX_CARD_CHARS
        ):
            cards.append(
                _source_span_card(
                    row, offset, offset + len(line_without_break), facet
                )
            )
            seen_values.update(values)
            if len(cards) >= MAX_CARDS_PER_ROW:
                break
        offset += len(line)
    return cards


def verify_source_span_receipt(row: dict[str, Any], card: dict[str, Any]) -> bool:
    """Verify provenance, hashes and exact bounds independently of rule matching."""
    content = str(row.get("content") or "")
    start, end = card.get("start"), card.get("end")
    return bool(
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start <= end <= len(content)
        and end - start <= MAX_CARD_CHARS
        and bool(str(row.get("id") or ""))
        and bool(str(row.get("document_id") or ""))
        and bool(_HEX64.fullmatch(str(row.get("extraction_sha256") or "")))
        and str(row.get("id") or "") == card.get("candidate_id")
        and str(row.get("document_id") or "") == card.get("document_id")
        and str(row.get("extraction_sha256") or "") == card.get("extraction_sha256")
        and _sha256(content) == card.get("content_sha256")
        and content[start:end] == card.get("quote")
        and _sha256(content[start:end]) == card.get("quote_sha256")
    )


def _query_terms(query: str) -> set[str]:
    return {
        token for token in _fold(query).split()
        if len(token) >= 4 and token not in _REFERENCE_QUERY_STOP
    }


def _section_refs(query: str, seeds: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Map each explicit reference to query-aligned terms in its source window."""
    refs: dict[str, set[str]] = {}
    query_terms = _query_terms(query)
    for seed in seeds:
        content = str(seed.get("content") or "")
        for match in _SECTION_REFERENCE.finditer(content):
            window = content[max(0, match.start() - 180):match.end() + 180]
            window_terms = set(_fold(window).split())
            aligned = query_terms & window_terms
            if aligned:
                refs.setdefault(match.group(1), set()).update(aligned)
    return refs


def _loop_capability_anchors(text: str) -> set[str]:
    """Discover only anchors grammatically attached to ``loop/lazo``."""
    anchors = {
        match.group(1).upper()
        for pattern in (_LOOP_CAPABILITY_BEFORE, _LOOP_CAPABILITY_AFTER)
        for match in pattern.finditer(text)
    }
    return {
        anchor for anchor in anchors
        if anchor not in _CAPABILITY_STOP and any(char.isalpha() for char in anchor)
    }


def _licensed_loop_anchors(query: str, served: list[dict[str, Any]]) -> set[str]:
    established: set[str] = set()
    query_anchors = _loop_capability_anchors(query)
    for seed in served:
        content = str(seed.get("content") or "")
        loops = list(_LOOP.finditer(content))
        licences = list(_LICENSE.finditer(content))
        for loop in loops:
            for licence in licences:
                if abs(loop.start() - licence.start()) > 260:
                    continue
                start = max(0, min(loop.start(), licence.start()) - 100)
                end = min(len(content), max(loop.end(), licence.end()) + 100)
                relation_anchors = _loop_capability_anchors(content[start:end])
                if query_anchors:
                    relation_anchors &= query_anchors
                established.update(relation_anchors)
    return established


def _task_term_after(query: str, content: str, start: int) -> bool:
    tail_terms = set(_fold(content[start:start + 1400]).split())
    return bool(_query_terms(query) & tail_terms)


def select_procedure_bundle_coverage(
    query: str,
    served: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trace = {
        "lane": LANE,
        "input_candidates": len(candidates),
        "product_scoped_candidates": 0,
        "section_references": [],
        "potential_facets": [],
        "selected_ids": [],
        "selected_facets": [],
        "model_calls": 0,
        "database_writes": 0,
        "shadow_only": True,
    }
    if not query.strip() or not served:
        trace["reason"] = "empty_query_or_context"
        return [], trace
    seen = {str(row.get("id") or "") for row in served}
    scoped = [
        row for row in candidates
        if str(row.get("id") or "") not in seen and _product_compatible(row, served)
    ]
    trace["product_scoped_candidates"] = len(scoped)
    procedural = bool(_PROCEDURAL_QUERY.search(_fold(query)))
    refs = _section_refs(query, served) if procedural else {}
    trace["section_references"] = sorted(refs)
    licensed_anchors = _licensed_loop_anchors(query, served)

    ranked: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    potential_facets: set[str] = set()
    for row in scoped:
        content = str(row.get("content") or "")
        folded_content = _fold(content)
        section = str(row.get("section_title") or row.get("section_path") or "")
        facet = ""
        priority = 99
        match: re.Match[str] | None = None
        referenced_number = next(
            (
                ref for ref in refs
                if re.match(rf"^\s*{re.escape(ref)}(?:\D|$)", section)
                and _same_document(row, served)
            ),
            None,
        )
        if referenced_number:
            potential_facets.add("explicit_intra_document_reference")
        referenced = next(
            (
                ref for ref, anchors in refs.items()
                if re.match(rf"^\s*{re.escape(ref)}(?:\D|$)", section)
                and bool(anchors & set(folded_content.split()))
            ),
            None,
        )
        if referenced and _same_document(row, served):
            facet = "explicit_intra_document_reference"
            priority = 0
            match = _OPERATIONAL.search(content)
        access = _ACCESS_UNLOCK.search(content)
        if procedural and access and _same_document(row, served):
            potential_facets.add("procedural_access_prerequisite")
        if (
            procedural
            and access
            and _same_document(row, served)
            and _task_term_after(query, content, access.end())
            and priority > 1
        ):
            facet = "procedural_access_prerequisite"
            priority = 1
            match = access
        licence = _LICENSED_LOOP.search(content)
        candidate_anchors = (
            _loop_capability_anchors(
                content[max(0, licence.start() - 100):min(len(content), licence.end() + 100)]
            )
            if licence
            else set()
        )
        if licensed_anchors and licence:
            potential_facets.add("quantified_licensed_loop_prerequisite")
        if licensed_anchors & candidate_anchors and licence and priority > 2:
            facet = "quantified_licensed_loop_prerequisite"
            priority = 2
            match = licence
        if not facet:
            continue
        operational_hits = len(_OPERATIONAL.findall(content))
        cards = (
            _aligned_table_cards(row, refs[referenced], facet)
            if referenced and facet == "explicit_intra_document_reference"
            else []
        )
        if not cards:
            cards = [_exact_card(row, match, facet)]
        enriched = dict(row)
        enriched.update(
            {
                "retrieval_lane": LANE,
                "procedure_bundle_rule_match": True,
                "procedure_bundle_shadow_only": True,
                "procedure_bundle_facet": facet,
                "coverage_cards": cards,
            }
        )
        ranked.append(((priority, -operational_hits, str(row.get("id") or "")), enriched))

    ranked.sort(key=lambda item: item[0])
    selected = [row for _, row in ranked[:MAX_SELECTED]]
    trace["selected_ids"] = [str(row.get("id") or "") for row in selected]
    trace["selected_facets"] = [row["procedure_bundle_facet"] for row in selected]
    trace["potential_facets"] = sorted(potential_facets)
    trace["reason"] = "selected" if selected else "no_conservative_procedure_bundle_candidate"
    return selected, trace
