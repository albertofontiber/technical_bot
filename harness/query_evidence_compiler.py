"""Query-conditioned, source-extractive evidence plans with exact compilation.

The module deliberately separates three responsibilities:

* an economic model may propose atomic claims, but every claim must bind to an
  exact span of an already-served chunk;
* a planner may select only opaque evidence IDs;
* the compiler renders every selected span deterministically.

No product, manufacturer, benchmark question, expected value, or target fact is
encoded here.  Invalid model claims are dropped rather than repaired
semantically; the original chunk bytes remain the only source of rendered text.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .query_evidence_obligations import extract_query_evidence_obligations


QUERY_EVIDENCE_COMPILER_V1 = "query_evidence_compiler_s210_v1"
FACETS = (
    "direct_answer",
    "procedure",
    "configuration",
    "prerequisite_safety",
    "threshold_default",
    "diagnostic",
    "exception_warning",
    "verification",
)
MAX_MODEL_CLAIMS_PER_CHUNK = 16
MAX_PRIMARY_IDS = 12
MAX_ADDITIONAL_IDS = 6


def portable_file_sha(path: Path) -> str:
    """Hash UTF-8 text canonically across LF/CRLF checkouts; preserve binaries."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        canonical = raw
    else:
        canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
MAX_COMPILED_IDS = 16
MAX_COMPILED_CHARS = 12_000


@dataclass(frozen=True)
class EvidenceCandidate:
    evidence_id: str
    origin: str
    facet: str
    claim_text: str
    exact_quote: str
    fragment_number: int
    candidate_id: str
    source_start: int
    source_end: int
    quote_sha256: str

    def public_payload(self) -> dict[str, Any]:
        """Return the bounded content the ID planner is allowed to inspect."""
        return {
            "evidence_id": self.evidence_id,
            "origin": self.origin,
            "facet": self.facet,
            "claim_text": self.claim_text,
            "exact_quote": self.exact_quote,
            "fragment_number": self.fragment_number,
        }


def stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def claim_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["claims"],
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["facet", "claim_text", "exact_quote"],
                    "properties": {
                        "facet": {"type": "string", "enum": list(FACETS)},
                        "claim_text": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 700,
                        },
                        "exact_quote": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1500,
                        },
                    },
                },
            }
        },
    }


def plan_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evidence_ids"],
        "properties": {
            "evidence_ids": {"type": "array", "items": {"type": "string"}}
        },
    }


def verification_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "missing_facets", "additional_evidence_ids"],
        "properties": {
            "status": {"type": "string", "enum": ["COMPLETE", "INCOMPLETE"]},
            "missing_facets": {"type": "array", "items": {"type": "string"}},
            "additional_evidence_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }


def _validate_schema(value: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise ValueError(f"{label} schema violation: {errors[0].message}")


def _repair_quote(source: str, quote: str) -> tuple[str, int, int, bool] | None:
    start = source.find(quote)
    if start >= 0:
        return quote, start, start + len(quote), False
    tokens = re.findall(r"\S+", quote)
    if not tokens:
        return None
    matches = list(re.finditer(r"\s+".join(re.escape(token) for token in tokens), source))
    if len(matches) != 1:
        return None
    match = matches[0]
    return source[match.start() : match.end()], match.start(), match.end(), True


def _identity(
    *,
    fragment_number: int,
    candidate_id: str,
    source_start: int,
    source_end: int,
    quote_sha256: str,
) -> str:
    material = (
        f"{fragment_number}:{candidate_id}:{source_start}:{source_end}:{quote_sha256}"
    )
    return "QE_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def validate_claim_response(
    value: dict[str, Any],
    *,
    chunk: dict[str, Any],
    fragment_number: int,
) -> tuple[list[EvidenceCandidate], dict[str, int]]:
    """Bind proposed claims to exact chunk spans and drop only invalid rows."""
    _validate_schema(value, claim_schema(), "claim")
    raw_claims = value["claims"]
    if len(raw_claims) > MAX_MODEL_CLAIMS_PER_CHUNK:
        raise ValueError("claim count exceeds the per-chunk bound")
    source = str(chunk.get("content") or "")
    candidate_id = str(chunk.get("id") or chunk.get("candidate_id") or "").strip()
    if not source or not candidate_id or fragment_number < 1:
        raise ValueError("claim source identity is incomplete")

    output: list[EvidenceCandidate] = []
    repairs = drops = duplicates = 0
    seen: set[tuple[int, int]] = set()
    for raw in raw_claims:
        repaired = _repair_quote(source, raw["exact_quote"])
        claim_text = raw["claim_text"].strip()
        if repaired is None or not claim_text:
            drops += 1
            continue
        quote, start, end, changed = repaired
        if (start, end) in seen:
            duplicates += 1
            continue
        seen.add((start, end))
        quote_sha = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        output.append(
            EvidenceCandidate(
                evidence_id=_identity(
                    fragment_number=fragment_number,
                    candidate_id=candidate_id,
                    source_start=start,
                    source_end=end,
                    quote_sha256=quote_sha,
                ),
                origin="model_exact_claim",
                facet=raw["facet"],
                claim_text=claim_text,
                exact_quote=quote,
                fragment_number=fragment_number,
                candidate_id=candidate_id,
                source_start=start,
                source_end=end,
                quote_sha256=quote_sha,
            )
        )
        repairs += int(changed)
    return output, {
        "whitespace_only_repairs": repairs,
        "invalid_quote_drops": drops,
        "duplicate_span_drops": duplicates,
    }


def deterministic_fallback_candidates(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    max_candidates: int = 12,
) -> list[EvidenceCandidate]:
    """Build a bounded, model-free safety net from generic query/source overlap."""
    aligned = list(enumerate(chunks, 1))
    rows = extract_query_evidence_obligations(
        query, aligned, max_candidates=max_candidates
    )
    output: list[EvidenceCandidate] = []
    for row in rows:
        chunk = chunks[row.fragment_number - 1]
        source = str(chunk.get("content") or "")
        quote = source[row.source_start : row.source_end]
        candidate_id = str(chunk.get("id") or chunk.get("candidate_id") or "").strip()
        if not quote or not candidate_id:
            continue
        quote_sha = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        output.append(
            EvidenceCandidate(
                evidence_id=_identity(
                    fragment_number=row.fragment_number,
                    candidate_id=candidate_id,
                    source_start=row.source_start,
                    source_end=row.source_end,
                    quote_sha256=quote_sha,
                ),
                origin="deterministic_query_fallback",
                facet="direct_answer",
                claim_text=row.statement,
                exact_quote=quote,
                fragment_number=row.fragment_number,
                candidate_id=candidate_id,
                source_start=row.source_start,
                source_end=row.source_end,
                quote_sha256=quote_sha,
            )
        )
    return output


def merge_candidate_pool(
    model_claims: Iterable[EvidenceCandidate],
    fallback: Iterable[EvidenceCandidate],
) -> list[EvidenceCandidate]:
    """Prefer concise model-bound claims when both lanes bind the same span."""
    output: list[EvidenceCandidate] = []
    seen_ids: set[str] = set()
    for row in (*tuple(model_claims), *tuple(fallback)):
        if row.evidence_id in seen_ids:
            continue
        seen_ids.add(row.evidence_id)
        output.append(row)
    return output


def planner_payload(question: str, candidates: list[EvidenceCandidate]) -> str:
    return json.dumps(
        {
            "question": question,
            "evidence_candidates": [row.public_payload() for row in candidates],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def verifier_payload(
    question: str,
    candidates: list[EvidenceCandidate],
    selected_ids: Iterable[str],
) -> str:
    return json.dumps(
        {
            "question": question,
            "selected_evidence_ids": list(selected_ids),
            "evidence_candidates": [row.public_payload() for row in candidates],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_plan(
    value: dict[str, Any], candidates: list[EvidenceCandidate]
) -> tuple[str, ...]:
    _validate_schema(value, plan_schema(), "plan")
    ids = value["evidence_ids"]
    known = {row.evidence_id for row in candidates}
    if not 1 <= len(ids) <= MAX_PRIMARY_IDS:
        raise ValueError("primary evidence ID count violation")
    if len(ids) != len(set(ids)) or not set(ids).issubset(known):
        raise ValueError("primary plan contains duplicate or unknown IDs")
    return tuple(ids)


def validate_verification(
    value: dict[str, Any],
    candidates: list[EvidenceCandidate],
    primary_ids: Iterable[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    _validate_schema(value, verification_schema(), "verification")
    primary = tuple(primary_ids)
    primary_set = set(primary)
    ids = value["additional_evidence_ids"]
    facets = tuple(str(item).strip() for item in value["missing_facets"] if str(item).strip())
    known = {row.evidence_id for row in candidates}
    if len(ids) > MAX_ADDITIONAL_IDS:
        raise ValueError("additional evidence ID count violation")
    if len(ids) != len(set(ids)) or not set(ids).issubset(known) or set(ids) & primary_set:
        raise ValueError("verification contains duplicate, selected, or unknown IDs")
    if value["status"] == "COMPLETE" and (facets or ids):
        raise ValueError("complete verification cannot contain omissions")
    if value["status"] == "INCOMPLETE" and (not facets or not ids):
        raise ValueError("incomplete verification must identify facets and additions")
    if len(primary) + len(ids) > MAX_COMPILED_IDS:
        raise ValueError("verified evidence exceeds the compiled ID bound")
    return value["status"], facets, tuple(ids)


def compile_evidence_appendix(
    candidates: list[EvidenceCandidate], selected_ids: Iterable[str]
) -> tuple[str, list[dict[str, Any]]]:
    """Render every selected source span once and return an audit receipt."""
    by_id = {row.evidence_id: row for row in candidates}
    ordered_ids = tuple(selected_ids)
    if not ordered_ids or len(ordered_ids) > MAX_COMPILED_IDS:
        raise ValueError("compiled evidence ID count violation")
    if len(ordered_ids) != len(set(ordered_ids)) or not set(ordered_ids).issubset(by_id):
        raise ValueError("compiled evidence contains duplicate or unknown IDs")

    blocks: list[str] = []
    receipts: list[dict[str, Any]] = []
    for evidence_id in ordered_ids:
        row = by_id[evidence_id]
        marker = f"[F{row.fragment_number}]"
        quote = row.exact_quote.strip()
        blocks.append(f"- {marker} {quote} {marker}")
        receipts.append(asdict(row))
    appendix = (
        "### Evidencia adicional verificada\n\n"
        "Los siguientes puntos proceden literalmente de los fragmentos servidos y "
        "completan la respuesta anterior:\n\n"
        + "\n\n".join(blocks)
    )
    if len(appendix) > MAX_COMPILED_CHARS:
        raise ValueError("compiled evidence exceeds the character bound")
    return appendix, receipts


def append_to_answer(base_answer: str, appendix: str) -> str:
    if not base_answer.strip() or not appendix.strip():
        raise ValueError("base answer and appendix must be non-empty")
    return base_answer.rstrip() + "\n\n---\n\n" + appendix.strip()
