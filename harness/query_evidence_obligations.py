"""Product-agnostic extraction of query-scoped exact evidence records.

This module is a deterministic extractive fallback. It selects bounded source
records from chunks that retrieval has already aligned to the query; it never
retrieves, translates, completes, or infers technical values.
"""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from typing import Any


QUERY_EVIDENCE_EXTRACTOR_V1 = "query_evidence_extractor_s142_v1"


@dataclass(frozen=True)
class QueryEvidenceCandidate:
    fragment_number: int
    candidate_id: str
    kind: str
    statement: str
    required_anchors: tuple[str, ...]
    source_start: int
    source_end: int
    semantic_identity: tuple[str, ...]
    score: int
    identity_receipt_sha256: str = ""


_STOPWORDS = {
    "a", "al", "algo", "and", "como", "con", "cual", "cuando", "de", "del",
    "desde", "el", "en", "es", "esta", "este", "for", "how", "la", "las",
    "lo", "los", "me", "of", "para", "por", "que", "se", "si", "the", "to",
    "un", "una", "y", "what", "which", "with",
}

# Bilingual domain concepts are intentionally generic across manufacturers.
# Stems are used only for local relevance, never to synthesize a value.
_CONCEPTS: dict[str, tuple[str, ...]] = {
    "configure": ("configur", "program", "ajust", "seleccion", "select", " set "),
    "connect": ("conect", "cable", "wire", "wiring", "terminal", "borne"),
    "power": ("aliment", "power", "voltage", "tension", "bateri", "battery"),
    "output": ("salida", "output"),
    "input": ("entrada", "input"),
    "alarm": ("alarma", "alarm", "fuego", "fire"),
    "fault": ("averia", "fallo", "fault", "trouble"),
    "reset": ("rearm", "reset", "restablec", "restart"),
    "delay": ("retard", "delay", "temporiz", "timing"),
    "test": ("prueb", "test", "comprob", "verify", "check"),
    "communication": ("comunic", "commun", "network", "red", "wireless", "inalambr"),
    "remote_reporting": ("cra", "arc", "transmission", "transmit", "central receptora"),
    "panel": ("central", "control panel", "panel"),
    "indicator": (" led", "indicador", "indicator", "parpade", "flash"),
    "relay": ("rele", "relay"),
    "resistance": ("resist", "rezistor", "ohm", "impedan", "eol", "fin de linea"),
    "time": ("tiempo", "time", "seg", "second", "minut", "hour"),
    "tone": ("tono", "tone", "acust", "sound"),
    "address": ("direccion", "address"),
    "zone": ("zona", "zone", "loop", "lazo"),
    "maintenance": ("manten", "maintenance", "servicio", "service", "calibr"),
    "safety": ("seguridad", "safety", "warning", "advert", "precauc"),
    "control": ("control", "boton", "button", "switch", "interruptor", "dip"),
    "threshold": ("umbral", "threshold", "limite", "limit", "sensib"),
    "variable": ("variable", "parametro", "parameter"),
    "save_apply": ("guard", "save", "aplic", "apply"),
    "magnet": ("iman", "magnet"),
    "length": ("longitud", "length", "distance", "distancia"),
    "quantity": ("numero", "number", "cantidad", "quantity"),
    "gauge": ("seccion", "gauge", "wire size", "calibre"),
    "polarity": ("positivo", "negative", "negativo", "positive", "polarity", "polaridad"),
    "initiation": ("iniciacion", "initiation"),
    "dip": (" dip", "dip switch", "switchsettings"),
    "current": ("corriente", "current", " ma", " amp"),
    "activation": ("activ", "enable", "encend", "start"),
    "deactivation": ("desactiv", "disable", "apag", "stop"),
    "state": ("estado", "state", "condicion", "condition", "modo", "mode"),
}

_RELATION_SIGNAL = re.compile(
    r"\b(?:must|shall|should|before|after|when|if|unless|set|select|press|connect|"
    r"check|test|configure|adjust|debe|antes|despues|cuando|si|seleccion|pulse|"
    r"conect|comprob|prueb|configur|ajust|permite|requires?|only|solo)\w*\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*(?:%|v|vac|vdc|a|ma|ohm|ω|"
    r"kohm|kω|s|sec|seg|min|hz|°c|ºc|ft|mm|cm|m))?(?!\w)",
    re.IGNORECASE,
)
_NUMERIC_QUERY = re.compile(
    r"\b(?:cuant\w*|cual\w*|valor\w*|tiempo|frecuencia|resistencia|tension|"
    r"corriente|how many|what value|range|rating|delay|voltage|current)\b",
    re.IGNORECASE,
)
_PROCEDURE_QUERY = re.compile(
    r"\b(?:como|configur\w*|conect\w*|program\w*|ajust\w*|prob\w*|comprob\w*|"
    r"how|configure|connect|program|adjust|test|check|reset)\b",
    re.IGNORECASE,
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(value))


def _clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = value.replace("```", "").replace("~~", "")
    return re.sub(r"\s+", " ", value).strip(" |\n")


def _concept_hits(value: str) -> set[str]:
    folded = " " + _fold(value) + " "
    exact_stems = {"arc", "cra", "red"}

    def present(stem: str) -> bool:
        if stem != stem.strip():
            return stem in folded
        needle = re.escape(stem)
        if stem in exact_stems:
            return bool(re.search(rf"(?<![a-z0-9]){needle}(?![a-z0-9])", folded))
        return bool(re.search(rf"(?<![a-z0-9]){needle}[a-z0-9]*", folded))

    return {
        concept
        for concept, stems in _CONCEPTS.items()
        if any(present(stem) for stem in stems)
    }


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in _tokens(query)
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _line_spans(content: str) -> list[tuple[int, int]]:
    spans = []
    for match in re.finditer(r"(?m)^.*(?:\n|$)", content):
        start, end = match.span()
        if end > start and content[start:end].strip():
            spans.append((start, end))
    return spans


def _structural_units(content: str, *, max_chars: int = 2000) -> list[tuple[int, int]]:
    spans: set[tuple[int, int]] = set()
    lines = _line_spans(content)
    for start, end in lines:
        if 20 <= len(content[start:end].strip()) <= max_chars:
            spans.add((start, end))
    for match in re.finditer(r"(?s)(?:^|\n\s*\n)(\s*\S.*?)(?=\n\s*\n|$)", content):
        start, end = match.span(1)
        if 35 <= len(content[start:end].strip()) <= max_chars:
            spans.add((start, end))
        paragraph = content[start:end]
        for sentence in re.finditer(r"[^\n.!?]{25,}(?:[.!?](?=\s|$)|$)", paragraph):
            s, e = start + sentence.start(), start + sentence.end()
            if e - s <= max_chars:
                spans.add((s, e))
    for index in range(len(lines)):
        start = lines[index][0]
        for width in (2, 3, 4):
            if index + width > len(lines):
                continue
            end = lines[index + width - 1][1]
            value = content[start:end]
            if 45 <= len(value.strip()) <= max_chars:
                spans.add((start, end))
    return sorted(spans)


def _is_noise(statement: str) -> bool:
    alnum = sum(char.isalnum() for char in statement)
    if alnum < 12 or alnum / max(len(statement), 1) < 0.22:
        return True
    folded = _fold(statement)
    footer_terms = ("manual de instalacion", "installation manual", "www.")
    if len(statement) < 220 and sum(term in folded for term in footer_terms) >= 2:
        return True
    return False


def _score_unit(
    query: str,
    statement: str,
    *,
    query_concepts: set[str],
    query_terms: set[str],
    section_title: str,
) -> tuple[int, set[str], set[str]]:
    content_concepts = _concept_hits(statement)
    concept_overlap = query_concepts & content_concepts
    content_terms = set(_tokens(statement))
    term_overlap = query_terms & content_terms
    section_overlap = query_terms & set(_tokens(section_title))
    relation = bool(_RELATION_SIGNAL.search(_fold(statement)))
    numbers = _NUMBER.findall(statement)
    score = len(concept_overlap) * 8 + min(len(term_overlap), 8) * 2
    score += min(len(section_overlap), 3) * 2
    score += 3 if relation else 0
    score += 3 if _NUMERIC_QUERY.search(_fold(query)) and numbers else 0
    score += 2 if _PROCEDURE_QUERY.search(_fold(query)) and relation else 0
    score += 1 if statement.lstrip().startswith(("|", "-", "*")) else 0
    if len(statement) > 1100:
        score -= 2
    if len(statement) < 35:
        score -= 3
    return score, concept_overlap, term_overlap


def _surface_anchor(statement: str, concept: str) -> str | None:
    folded = _fold(statement)
    for stem in _CONCEPTS[concept]:
        needle = stem.strip()
        index = folded.find(needle)
        if index >= 0:
            raw = statement[index : index + max(len(needle), 3)]
            return raw.strip()
    return None


def _anchors(
    statement: str, concept_overlap: set[str], term_overlap: set[str]
) -> tuple[str, ...]:
    output = []
    for concept in sorted(concept_overlap):
        surface = _surface_anchor(statement, concept)
        if surface and surface not in output:
            output.append(surface)
    for value in _NUMBER.findall(statement):
        cleaned = re.sub(r"\s+", " ", value).strip()
        if cleaned and cleaned not in output:
            output.append(cleaned)
    for token in sorted(term_overlap, key=lambda value: (-len(value), value)):
        if token not in output:
            output.append(token)
    return tuple(output[:8])


def extract_query_evidence_obligations(
    query: str,
    aligned: list[tuple[int, dict[str, Any]]],
    *,
    max_candidates: int = 5,
) -> list[QueryEvidenceCandidate]:
    query_concepts = _concept_hits(query)
    query_terms = _query_terms(query)
    if not query_concepts or not query_terms:
        return []
    ranked = []
    for fragment_number, chunk in aligned:
        content = str(chunk.get("content") or "")
        if not content:
            continue
        section_title = str(chunk.get("section_title") or "")
        for start, end in _structural_units(content):
            raw = content[start:end]
            statement = _clean(raw)
            if not statement or _is_noise(statement):
                continue
            score, concepts, terms = _score_unit(
                query,
                statement,
                query_concepts=query_concepts,
                query_terms=query_terms,
                section_title=section_title,
            )
            if not concepts or score < 10:
                continue
            if not (
                _RELATION_SIGNAL.search(_fold(statement))
                or _NUMBER.search(statement)
                or len(concepts) >= 2
            ):
                continue
            anchors = _anchors(statement, concepts, terms)
            if len(anchors) < 2:
                continue
            ranked.append(
                (
                    -score,
                    fragment_number,
                    start,
                    end,
                    chunk,
                    statement,
                    concepts,
                    anchors,
                )
            )
    ranked.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    selected: list[tuple[int, int, str, set[str], int]] = []
    output = []
    covered_concepts: set[str] = set()
    for neg_score, fragment_number, start, end, chunk, statement, concepts, anchors in ranked:
        candidate_id = str(chunk.get("id") or "")
        if any(
            prior_fragment == fragment_number
            and prior_id == candidate_id
            and (
                start >= prior_start
                and end <= prior_end
                or max(0, min(end, prior_end) - max(start, prior_start))
                / max(1, end - start)
                >= 0.5
            )
            and concepts <= prior_concepts
            for prior_start, prior_end, prior_id, prior_concepts, prior_fragment in (
                (row[0], row[1], row[2], row[3], row[4]) for row in selected
            )
        ):
            continue
        # After the first two records, require new query coverage or a strong
        # score to prevent source dumping from one long section.
        score = -neg_score
        if len(output) >= 3 and concepts <= covered_concepts and score < 24:
            continue
        semantic = hashlib.sha256(
            f"{candidate_id}:{start}:{end}:{statement}".encode("utf-8")
        ).hexdigest()
        receipt = chunk.get("query_source_identity_attestation") or {}
        output.append(
            QueryEvidenceCandidate(
                fragment_number=fragment_number,
                candidate_id=candidate_id,
                kind="query_scoped_source_record",
                statement=statement,
                required_anchors=anchors,
                source_start=start,
                source_end=end,
                semantic_identity=(semantic,),
                score=score,
                identity_receipt_sha256=str(receipt.get("receipt_sha256") or ""),
            )
        )
        selected.append((start, end, candidate_id, concepts, fragment_number))
        covered_concepts.update(concepts)
        if len(output) >= max_candidates:
            break
    return output
