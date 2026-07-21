#!/usr/bin/env python3
"""Deterministic, offline scorer for the S277 C1 P1 release gate.

The scorer deliberately has no model or network fallback.  Deterministic positive
evidence may PASS, explicit damage may FAIL, plausible paraphrase is REVIEW, and
contract/context drift is INSTRUMENT_ERROR.  REVIEW is blocking until a separate,
hash-bound human adjudication is supplied by the P1 finalizer.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = "s277_c1_p1_scorer_v1"
ADJUDICATION_SCHEMA = "s277_c1_p1_adjudication_v1"
FINAL_SCHEMA = "s277_c1_p1_final_v1"
CONTRACT_SCHEMA = "s277_c1_p1_fact_contract_v1"
REPLICA_SCHEMA = "s277_c1_p1_replica_receipt_v1"
EXPECTED_CONTRACT_ID = "S277-C1-P1-PROTECTED-PACKET-V1"
EXPECTED_CONTRACT_PAYLOAD_SHA256 = (
    "e6972b24b3c71ba78e585d820c8002ed46d9424b219a1227430fc73619564ab0"
)
EXPECTED_CONTRACT_SHA256_LF = (
    "3ac742b067ff8cc56332328eb5c8819ac1077e9b7efe10f838247940d0b6ca32"
)

PASS = "PASS"
FAIL = "FAIL"
REVIEW = "REVIEW"
INSTRUMENT_ERROR = "INSTRUMENT_ERROR"
_STATUS_ORDER = {PASS: 0, REVIEW: 1, FAIL: 2, INSTRUMENT_ERROR: 3}

TARGET_ID = "d27b1a1b-69cd-4318-a459-f3c86eb757ba"
TARGET_QID = "hp017"
TARGET_OBLIGATION_IDS = ("obl_16637b935bd4", "obl_0d6a30948dfd")
MENU_CONFLICT_ID = "conf_26f63590494f"
STORED_CONTROL_SCHEMA = "s277_c1_p1_stored_control_score_v1"
STORED_CONTROL_PATH = ROOT / "evals/s274_probeCD_replicas_v1.jsonl"
STORED_CONTROL_SHA256_LF = (
    "92d2fb0b60a1845d998e0fcb8b91b103d724be42cfe467e6c815f51fab3de835"
)
STORED_CONTROL_ARM = "A-C1"
STORED_CONTROL_ANSWER_FIELD = "on_answer"
STORED_CONTROL_REPLICATES = (1, 2, 3)
STORED_CONTROL_HOLD = "HOLD_PREPAID_KNOWN_CONFLICT_RISK"

P1_QIDS = (
    "cat001",
    "cat017",
    "cat018",
    "cat019",
    "hp002",
    "hp003",
    "hp005",
    "hp011",
    "hp012",
    "hp013",
    "hp014",
    "hp017",
    "hp018",
)
P1_REPLICA_KEYS = (
    "hp017:r1",
    "hp017:r2",
    "hp017:r3",
    "cat001:r1",
    "cat001:r2",
    "cat017:r1",
    "cat017:r2",
    "cat018:r1",
    "cat018:r2",
    "cat019:r1",
    "cat019:r2",
    "hp002:r1",
    "hp002:r2",
    "hp003:r1",
    "hp003:r2",
    "hp005:r1",
    "hp005:r2",
    "hp011:r1",
    "hp011:r2",
    "hp012:r1",
    "hp012:r2",
    "hp013:r1",
    "hp013:r2",
    "hp014:r1",
    "hp014:r2",
    "hp018:r1",
    "hp018:r2",
)

_FACT_ALGORITHMS = frozenset(
    {
        "protected_fact_surface_v1",
        "hp011_rearme_inhibido_v1",
        "hp017_delay_disclosure_v1",
    }
)
_GUARD_ALGORITHMS = frozenset({"hp013_safety_guard_v1"})
_CONFLICT_ALGORITHMS = frozenset({"hp017_menu_conflict_v1"})
_TARGET_ALGORITHMS = frozenset({"hp017_compound_warning_exact_v1"})
_BINDING_LEVELS = frozenset({"gold_verified_page", "accepted_exact_span"})
_SCORE_BINDING_FIELDS = frozenset(
    {
        "run_result_sha256",
        "prereg_sha256",
        "fact_contract_sha256_lf",
        "fact_contract_payload_sha256",
        "replica_manifest_sha256",
    }
)

_EXACT_CITATION_RE = re.compile(r"\[F([1-9]\d*)\]")
_BRACKET_RE = re.compile(r"\[[^\]\r\n]*\]")
_CITATION_LIKE_RE = re.compile(r"^\[\s*[fF]")
_CITATION_GROUP_RE = re.compile(r"(?:\[F[1-9]\d*\](?:\s*[,;]?\s*))+" )
_ALNUM_RE = re.compile(r"[a-z0-9]", re.IGNORECASE)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ONLY_DECORATION_RE = re.compile(r"^[\s>*_`~#|:;,.()\[\]{}\-–—]*$")


class ScorerInstrumentError(ValueError):
    """The scorer cannot attribute a result to the candidate safely."""


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    reasons: tuple[str, ...] = ()
    evidence: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "check_id": self.check_id,
            "status": self.status,
            "reasons": list(self.reasons),
        }
        if self.evidence is not None:
            row["evidence"] = dict(self.evidence)
        return row


def _result(
    check_id: str,
    status: str,
    *reasons: str,
    evidence: Mapping[str, Any] | None = None,
) -> CheckResult:
    if status not in _STATUS_ORDER:
        raise ScorerInstrumentError(f"unknown scorer status: {status!r}")
    return CheckResult(check_id, status, tuple(reasons), evidence)


def _combine(check_id: str, rows: Iterable[CheckResult]) -> CheckResult:
    materialized = list(rows)
    if not materialized:
        return _result(check_id, PASS)
    status = max(materialized, key=lambda row: _STATUS_ORDER[row.status]).status
    reasons = tuple(
        f"{row.check_id}:{reason}"
        for row in materialized
        if row.status != PASS
        for reason in (row.reasons or (row.status,))
    )
    return _result(
        check_id,
        status,
        *reasons,
        evidence={"checks": [row.to_dict() for row in materialized]},
    )


def _sha256_lf_text(value: str) -> str:
    return hashlib.sha256(value.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _normalized_text_sha256(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scorer_sha256() -> str:
    return hashlib.sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _surface_normalize(value: str) -> str:
    folded = _fold(value)
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def _normalise_with_map(value: str) -> tuple[str, list[int]]:
    """Return scorer normalization plus a map back to source character indexes."""
    output: list[str] = []
    offsets: list[int] = []
    pending_space = False
    for source_index, source_char in enumerate(value or ""):
        # Markdown decoration is presentation, not source wording.
        if source_char in "*_>`~":
            continue
        decomposed = unicodedata.normalize("NFKD", source_char)
        for char in decomposed:
            if unicodedata.combining(char):
                continue
            for folded in char.casefold():
                if folded.isspace():
                    pending_space = bool(output)
                    continue
                if pending_space:
                    output.append(" ")
                    offsets.append(source_index)
                    pending_space = False
                output.append(folded)
                offsets.append(source_index)
    while output and output[-1] == " ":
        output.pop()
        offsets.pop()
    return "".join(output), offsets


def _find_normalized_spans(haystack: str, needle: str) -> list[tuple[int, int]]:
    normalized_haystack, offsets = _normalise_with_map(haystack)
    normalized_needle, _ = _normalise_with_map(needle)
    normalized_needle = normalized_needle.strip()
    if not normalized_needle or not offsets:
        return []
    spans: list[tuple[int, int]] = []
    cursor = 0
    while True:
        start = normalized_haystack.find(normalized_needle, cursor)
        if start < 0:
            break
        end = start + len(normalized_needle)
        before = normalized_haystack[start - 1] if start else " "
        after = normalized_haystack[end] if end < len(normalized_haystack) else " "
        if not (before.isalnum() and normalized_needle[0].isalnum()) and not (
            after.isalnum() and normalized_needle[-1].isalnum()
        ):
            spans.append((offsets[start], offsets[end - 1] + 1))
        cursor = start + 1
    return spans


def _chunk_id(chunk: Mapping[str, Any]) -> str:
    row_id = str(chunk.get("id") or chunk.get("chunk_id") or "").strip()
    alternate = str(chunk.get("chunk_id") or "").strip()
    if row_id and alternate and row_id != alternate:
        raise ScorerInstrumentError("served chunk id/chunk_id disagree")
    return row_id


def _context_identity_errors(served_context: Any) -> list[str]:
    if not isinstance(served_context, list) or not served_context:
        return ["served_context must be a non-empty list"]
    seen: set[str] = set()
    errors: list[str] = []
    for index, chunk in enumerate(served_context, start=1):
        if not isinstance(chunk, dict):
            errors.append(f"F{index} is not an object")
            continue
        try:
            row_id = _chunk_id(chunk)
        except ScorerInstrumentError as exc:
            errors.append(f"F{index}: {exc}")
            continue
        if not row_id:
            errors.append(f"F{index} has no stable chunk identity")
        elif row_id in seen:
            errors.append(f"duplicate served chunk identity {row_id}")
        seen.add(row_id)
        if not isinstance(chunk.get("content"), str) or not chunk.get("content"):
            errors.append(f"F{index} has no content")
        if not str(chunk.get("source_file") or "").strip():
            errors.append(f"F{index} has no source_file")
        page = chunk.get("page_number")
        if page is not None and (isinstance(page, bool) or not isinstance(page, int) or page < 0):
            errors.append(f"F{index} has invalid page_number")
    return errors


def validate_global_citations(answer: Any, served_context: Any) -> CheckResult:
    """Validate every citation-looking marker and every cited context identity."""
    if not isinstance(answer, str):
        return _result("global_citations", INSTRUMENT_ERROR, "answer is not a string")
    identity_errors = _context_identity_errors(served_context)
    if identity_errors:
        return _result(
            "global_citations",
            INSTRUMENT_ERROR,
            *identity_errors,
        )

    exact = list(_EXACT_CITATION_RE.finditer(answer))
    exact_ranges = {(match.start(), match.end()) for match in exact}
    malformed: list[dict[str, Any]] = []
    bracket_ranges: set[tuple[int, int]] = set()
    for token in _BRACKET_RE.finditer(answer):
        bracket_ranges.add((token.start(), token.end()))
        if _CITATION_LIKE_RE.match(token.group()) and (
            token.start(), token.end()
        ) not in exact_ranges:
            malformed.append(
                {"text": token.group(), "start": token.start(), "end": token.end()}
            )
    # Catch an unterminated marker such as ``[F12``.
    for marker in re.finditer(r"\[\s*[fF](?=\s*\d|\s*\])", answer):
        if not any(start <= marker.start() < end for start, end in bracket_ranges):
            malformed.append(
                {"text": answer[marker.start() : marker.start() + 16], "start": marker.start()}
            )

    fragment_count = len(served_context)
    out_of_range = sorted(
        {
            int(match.group(1))
            for match in exact
            if not 1 <= int(match.group(1)) <= fragment_count
        }
    )
    if malformed or out_of_range:
        return _result(
            "global_citations",
            FAIL,
            *(tuple(["malformed citation marker"] if malformed else ())
              + tuple(["citation outside served context"] if out_of_range else ())),
            evidence={
                "fragment_count": fragment_count,
                "citations": [int(match.group(1)) for match in exact],
                "malformed": malformed,
                "out_of_range": out_of_range,
            },
        )

    cited_fragments = sorted({int(match.group(1)) for match in exact})
    for fragment in cited_fragments:
        chunk = served_context[fragment - 1]
        if not _chunk_id(chunk) or not str(chunk.get("source_file") or "").strip():
            return _result(
                "global_citations",
                INSTRUMENT_ERROR,
                f"F{fragment} lacks citation identity",
            )
    return _result(
        "global_citations",
        PASS,
        evidence={
            "fragment_count": fragment_count,
            "citation_count": len(exact),
            "cited_fragments": cited_fragments,
        },
    )


def parse_local_citation_units(answer: str) -> list[dict[str, Any]]:
    """Bind each exact citation group to its immediately preceding local claim.

    This parser is intentionally structural.  It does not infer entailment; it merely
    exposes bounded claim/citation units for fact-specific scorers.
    """
    if not isinstance(answer, str):
        raise ScorerInstrumentError("answer is not a string")
    units: list[dict[str, Any]] = []
    for group in _CITATION_GROUP_RE.finditer(answer):
        prefix = answer[: group.start()]
        paragraph_start = max(prefix.rfind("\n\n"), prefix.rfind("\r\n\r\n"))
        paragraph_start = 0 if paragraph_start < 0 else paragraph_start + 2
        line_start = prefix.rfind("\n") + 1
        claim_start = max(paragraph_start, line_start)
        claim = answer[claim_start : group.start()]
        # If a citation is on a separate marker-only line, bind it to the previous line.
        if not _ALNUM_RE.search(claim):
            prior = answer[:claim_start].rstrip("\r\n")
            previous_line_start = prior.rfind("\n") + 1
            claim_start = max(paragraph_start, previous_line_start)
            claim = answer[claim_start : group.start()]
        units.append(
            {
                "start": claim_start,
                "end": group.end(),
                "claim_start": claim_start,
                "claim_end": group.start(),
                "claim_text": claim,
                "citation_start": group.start(),
                "citation_end": group.end(),
                "citations": [
                    int(value) for value in _EXACT_CITATION_RE.findall(group.group())
                ],
            }
        )
    return units


def _citation_group_after(answer: str, end: int, max_gap: int = 96) -> list[int]:
    tail = answer[end : end + max_gap]
    match = re.match(r"[\s>*_`~:;,.()\-–—]*((?:\[F[1-9]\d*\](?:\s*[,;]?\s*))+)", tail)
    if not match:
        return []
    return [int(value) for value in _EXACT_CITATION_RE.findall(match.group(1))]


def _forms(row: Mapping[str, Any]) -> tuple[list[list[str]], list[str]]:
    forms = row.get("surface_forms")
    if not isinstance(forms, dict):
        raise ScorerInstrumentError("surface_forms must be an object")
    if forms.get("normalization") not in {None, "nfkd_casefold_alnum_ws"}:
        raise ScorerInstrumentError("unknown surface normalization")
    groups = forms.get("required_all_groups")
    forbidden = forms.get("forbidden_any", [])
    if not isinstance(groups, list) or not groups:
        raise ScorerInstrumentError("required_all_groups must be a non-empty list")
    clean_groups: list[list[str]] = []
    for group in groups:
        if not isinstance(group, list) or not group or not all(
            isinstance(value, str) and _normalise_with_map(value)[0].strip()
            for value in group
        ):
            raise ScorerInstrumentError("invalid required surface group")
        clean_groups.append(list(group))
    if not isinstance(forbidden, list) or not all(
        isinstance(value, str) and _normalise_with_map(value)[0].strip()
        for value in forbidden
    ):
        raise ScorerInstrumentError("invalid forbidden surface list")
    return clean_groups, list(forbidden)


def _surface_hits(answer: str, surfaces: Sequence[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for surface in surfaces:
        spans = _find_normalized_spans(answer, surface)
        if spans:
            hits.append({"surface": surface, "spans": spans})
    return hits


def _manual_equal(left: Any, right: Any) -> bool:
    left_folded = _surface_normalize(Path(str(left or "")).stem)
    right_folded = _surface_normalize(Path(str(right or "")).stem)
    return bool(left_folded and right_folded and left_folded == right_folded)


def _source_refs(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    refs = row.get("source_refs")
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, dict) for ref in refs):
        raise ScorerInstrumentError("source_refs must be a non-empty object list")
    return refs


def _validate_source_ref_contract(ref: Mapping[str, Any], label: str) -> None:
    content_sha256 = str(ref.get("content_sha256") or "").strip()
    quote_sha256 = str(ref.get("quote_sha256") or "").strip()
    quote_text = ref.get("quote_text")
    if content_sha256 and not _HEX64_RE.fullmatch(content_sha256):
        raise ScorerInstrumentError(f"invalid content hash for {label}")
    if quote_sha256 or quote_text is not None:
        if not isinstance(quote_text, str) or not quote_text.strip():
            raise ScorerInstrumentError(f"quote text/hash pair is incomplete for {label}")
        if not _HEX64_RE.fullmatch(quote_sha256):
            raise ScorerInstrumentError(f"invalid quote hash for {label}")
        if _normalized_text_sha256(quote_text) != quote_sha256:
            raise ScorerInstrumentError(f"quote hash drift for {label}")


def _ref_match(chunk: Mapping[str, Any], ref: Mapping[str, Any]) -> str:
    """Match physical identity *and* preregistered evidence, never page alone."""
    expected_id = str(
        ref.get("chunk_id") or ref.get("candidate_id") or ref.get("id") or ""
    ).strip()
    actual_id = _chunk_id(chunk)
    if expected_id and actual_id != expected_id:
        return FAIL

    expected_file = ref.get("source_file") or ref.get("manual_id") or ref.get("manual")
    actual_file = chunk.get("source_file")
    if expected_file and actual_file and not _manual_equal(expected_file, actual_file):
        return FAIL
    if expected_file and not actual_file:
        return REVIEW

    expected_page = ref.get("page_number", ref.get("page"))
    actual_page = chunk.get("page_number")
    if expected_page is not None and actual_page is not None and int(expected_page) != int(actual_page):
        return FAIL
    if expected_page is not None and actual_page is None:
        return REVIEW

    expected_document = str(ref.get("document_id") or "").strip()
    actual_document = str(chunk.get("document_id") or "").strip()
    if expected_document and actual_document and expected_document != actual_document:
        return FAIL
    if expected_document and not actual_document:
        return REVIEW

    for field in ("product_model", "manufacturer"):
        expected = _surface_normalize(str(ref.get(field) or ""))
        actual = _surface_normalize(str(chunk.get(field) or ""))
        if expected and actual and expected != actual:
            return FAIL
        if expected and not actual:
            return REVIEW

    content = chunk.get("content")
    if not isinstance(content, str) or not content:
        return INSTRUMENT_ERROR
    expected_content_sha256 = str(ref.get("content_sha256") or "").strip()
    if expected_content_sha256:
        if not _HEX64_RE.fullmatch(expected_content_sha256):
            return INSTRUMENT_ERROR
        return (
            PASS
            if hashlib.sha256(content.encode("utf-8")).hexdigest()
            == expected_content_sha256
            else INSTRUMENT_ERROR
        )

    quote_text = ref.get("quote_text")
    quote_sha256 = str(ref.get("quote_sha256") or "").strip()
    if quote_text is None and not quote_sha256:
        return REVIEW
    if not isinstance(quote_text, str) or not quote_text.strip():
        return INSTRUMENT_ERROR
    if not _HEX64_RE.fullmatch(quote_sha256):
        return INSTRUMENT_ERROR
    if _normalized_text_sha256(quote_text) != quote_sha256:
        return INSTRUMENT_ERROR
    normalized_quote = _surface_normalize(quote_text)
    normalized_content = _surface_normalize(content)
    if not normalized_quote:
        return INSTRUMENT_ERROR
    return PASS if normalized_quote in normalized_content else REVIEW


def _validate_exact_binding(chunk: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    start = row.get("source_start")
    end = row.get("source_end")
    expected_hash = str(row.get("source_span_sha256") or "")
    if not isinstance(start, int) or not isinstance(end, int) or not expected_hash:
        return INSTRUMENT_ERROR
    content = chunk.get("content")
    if not isinstance(content, str) or not 0 <= start < end <= len(content):
        return INSTRUMENT_ERROR
    return PASS if _sha256_lf_text(content[start:end]) == expected_hash else INSTRUMENT_ERROR


def _accredit_citations(
    fragments: Sequence[int],
    served_context: Sequence[Mapping[str, Any]],
    row: Mapping[str, Any],
    *,
    exact_texts: Sequence[str] = (),
) -> CheckResult:
    check_id = f"citation:{row.get('fact_id') or row.get('guard_id') or row.get('target_id') or 'row'}"
    if not fragments:
        return _result(check_id, REVIEW, "required local citation absent")
    try:
        refs = _source_refs(row)
    except ScorerInstrumentError as exc:
        return _result(check_id, INSTRUMENT_ERROR, str(exc))

    statuses: list[str] = []
    details: list[dict[str, Any]] = []
    for fragment in fragments:
        if not 1 <= fragment <= len(served_context):
            return _result(check_id, FAIL, f"F{fragment} is outside context")
        chunk = served_context[fragment - 1]
        ref_statuses = [_ref_match(chunk, ref) for ref in refs]
        if PASS in ref_statuses:
            status = PASS
        elif INSTRUMENT_ERROR in ref_statuses:
            status = INSTRUMENT_ERROR
        elif REVIEW in ref_statuses:
            status = REVIEW
        else:
            # For the hp017 target, a duplicated citation can pass only with the same
            # exact evidence and product/revision identity.  It may never be waved
            # through merely because the cited fragment exists.
            status = FAIL
            if exact_texts and all(
                _find_normalized_spans(str(chunk.get("content") or ""), text)
                for text in exact_texts
            ):
                target_identity = row.get("target_identity") or {}
                same_file = _manual_equal(
                    target_identity.get("source_file"), chunk.get("source_file")
                )
                same_product = _surface_normalize(
                    str(target_identity.get("product_model") or "")
                ) == _surface_normalize(str(chunk.get("product_model") or ""))
                if same_file and same_product:
                    status = PASS
                elif same_file and not chunk.get("product_model"):
                    status = REVIEW
        statuses.append(status)
        details.append(
            {"fragment": fragment, "chunk_id": _chunk_id(chunk), "status": status}
        )

    status = max(statuses, key=lambda value: _STATUS_ORDER[value])
    reason = {
        PASS: (),
        REVIEW: ("citation evidence identity is incomplete or undecidable",),
        FAIL: ("citation is not accredited for the local claim",),
        INSTRUMENT_ERROR: ("citation evidence binding drifted",),
    }[status]
    return _result(check_id, status, *reason, evidence={"citations": details})


def _surface_group_citations(
    answer: str,
    group_hits: Sequence[Sequence[dict[str, Any]]],
) -> list[int]:
    """Find one cited local unit that binds every required semantic group.

    Gathering an amount from one bullet and its subject from an unrelated bullet
    would create a false positive, even if both bullets happen to cite the same page.
    Multi-unit facts therefore require an explicit future algorithm; v1 never infers
    a relation by unioning disconnected surface hits.
    """
    units = parse_local_citation_units(answer)
    for unit in units:
        if not unit["citations"]:
            continue
        if all(
            any(
                unit["claim_start"] <= start
                and end <= unit["claim_end"]
                for hit in hits
                for start, end in hit["spans"]
            )
            for hits in group_hits
        ):
            return list(dict.fromkeys(unit["citations"]))
    return []


def _canonical_statement_citations(
    answer: str,
    fact: Mapping[str, Any],
) -> list[int]:
    """Return citations only for a whole local claim equal to the gold statement."""
    statement = fact.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        raise ScorerInstrumentError("protected fact has no canonical statement")
    canonical = _surface_normalize(statement)
    if not canonical:
        raise ScorerInstrumentError("protected fact canonical statement is empty")
    for unit in parse_local_citation_units(answer):
        if unit["citations"] and _surface_normalize(unit["claim_text"]) == canonical:
            return list(dict.fromkeys(unit["citations"]))
    return []


def _generic_fact_score(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    fact: Mapping[str, Any],
) -> CheckResult:
    fact_id = str(fact.get("fact_id") or "")
    check_id = f"fact:{fact_id or 'missing-id'}"
    try:
        groups, forbidden = _forms(fact)
    except ScorerInstrumentError as exc:
        return _result(check_id, INSTRUMENT_ERROR, str(exc))

    forbidden_hits = _surface_hits(answer, forbidden)
    if forbidden_hits:
        return _result(
            check_id,
            FAIL,
            "forbidden protected-fact surface asserted",
            evidence={"forbidden_hits": forbidden_hits},
        )

    hits_by_group = [_surface_hits(answer, group) for group in groups]
    missing = [index for index, hits in enumerate(hits_by_group) if not hits]
    try:
        fragments = _canonical_statement_citations(answer, fact)
    except ScorerInstrumentError as exc:
        return _result(check_id, INSTRUMENT_ERROR, str(exc))
    if not fragments:
        reason = (
            "deterministic surfaces missing; paraphrase requires blind review"
            if missing
            else "surface-complete claim is not the exact canonical statement"
        )
        return _result(
            check_id,
            REVIEW,
            reason,
            evidence={
                "required_group_hits": hits_by_group,
                "missing_required_group_indexes": missing,
            },
        )
    citation = _accredit_citations(fragments, served_context, fact)
    if citation.status != PASS:
        return _result(
            check_id,
            citation.status,
            *(citation.reasons or ("fact citation did not pass",)),
            evidence={
                "required_group_hits": hits_by_group,
                "citation": citation.to_dict(),
            },
        )

    if fact.get("binding_level") == "accepted_exact_span":
        cited_chunks = [served_context[index - 1] for index in fragments]
        bindings = [_validate_exact_binding(chunk, fact) for chunk in cited_chunks]
        if not bindings or any(status == INSTRUMENT_ERROR for status in bindings):
            return _result(
                check_id,
                INSTRUMENT_ERROR,
                "accepted exact source span drifted",
            )
    return _result(
        check_id,
        PASS,
        evidence={
            "required_group_hits": hits_by_group,
            "local_citations": fragments,
            "canonical_statement_exact": True,
        },
    )


_HP011_CANONICAL_RE = re.compile(r"(?<![a-z0-9])r\s*[.]\s*i(?![a-z0-9])", re.IGNORECASE)
_HP011_OCR_ALIAS_RE = re.compile(r"(?<![a-z0-9])r\s*[.]\s*1(?![a-z0-9])", re.IGNORECASE)
_HP011_TA_RE = re.compile(r"(?<![a-z0-9])t\s*[.]\s*a(?![a-z0-9])", re.IGNORECASE)
_HP011_TFI_RE = re.compile(r"(?<![a-z0-9])t\s*[.]\s*fi(?![a-z0-9])", re.IGNORECASE)
_HP011_ALIAS_DISCLOSURE_RE = re.compile(
    r"\b(?:alias|ocr|ambig\w*|represent\w*|se\s+muestra|se\s+lee|pantalla|display)\b",
    re.IGNORECASE,
)


def _score_hp011(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    fact: Mapping[str, Any],
) -> CheckResult:
    check_id = f"fact:{fact.get('fact_id') or 'hp011'}"
    has_special = "--" in answer
    if has_special and _HP011_TFI_RE.search(answer):
        return _result(check_id, FAIL, "t.Fi is forbidden inside the -- state")
    if has_special and not _HP011_TA_RE.search(answer):
        return _result(check_id, FAIL, "the -- state omits mandatory t.A")

    canonical = bool(_HP011_CANONICAL_RE.search(answer))
    alias = bool(_HP011_OCR_ALIAS_RE.search(answer))
    disclosed = bool(_HP011_ALIAS_DISCLOSURE_RE.search(answer))
    if alias and not canonical and not disclosed:
        return _result(
            check_id,
            REVIEW,
            "r.1 appears alone without canonical r.I/r.i or ambiguity disclosure",
        )
    generic = _generic_fact_score(answer, served_context, fact)
    if generic.status == PASS:
        evidence = dict(generic.evidence or {})
        evidence.update(
            {
                "canonical_identifier_present": canonical,
                "ocr_alias_present": alias,
                "identifier_omission_allowed": not canonical and not alias,
                "special_state_present": has_special,
                "t.A_present": bool(_HP011_TA_RE.search(answer)),
            }
        )
        return _result(check_id, PASS, evidence=evidence)
    return generic


def _score_hp017_disclosure(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    fact: Mapping[str, Any],
) -> CheckResult:
    check_id = f"fact:{fact.get('fact_id') or 'hp017-disclosure'}"
    try:
        from scripts.s270_etapa2_probe import disclosure_covered

        covered = disclosure_covered(answer)
    except Exception as exc:  # the frozen production scorer itself drifted
        return _result(check_id, INSTRUMENT_ERROR, f"disclosure scorer failed: {type(exc).__name__}")
    if not covered:
        relevant = bool(
            re.search(r"\b(?:seis|6)\b", _fold(answer))
            or re.search(r"\b(?:retardo|delay)\b", _fold(answer))
        )
        return _result(
            check_id,
            REVIEW if relevant else FAIL,
            "DEC-128 delay-type disclosure is not deterministically complete",
        )
    return _generic_fact_score(answer, served_context, fact)


def score_protected_fact(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    fact: Mapping[str, Any],
) -> CheckResult:
    algorithm = fact.get("algorithm")
    if algorithm not in _FACT_ALGORITHMS:
        return _result(
            f"fact:{fact.get('fact_id') or 'unknown'}",
            INSTRUMENT_ERROR,
            f"unknown fact algorithm {algorithm!r}",
        )
    if algorithm == "hp011_rearme_inhibido_v1":
        return _score_hp011(answer, served_context, fact)
    if algorithm == "hp017_delay_disclosure_v1":
        return _score_hp017_disclosure(answer, served_context, fact)
    return _generic_fact_score(answer, served_context, fact)


_HP013_PROCEDURE_RE = re.compile(
    r"\b(?:retir\w*|desconect\w*|extraig\w*|sustitu\w*|cambi\w*)\b[^.\n]{0,120}"
    r"\b(?:bateria|battery)\b",
    re.IGNORECASE,
)
_HP013_GUARANTEE_RE = re.compile(
    r"\b(?:queda\s+garantiz\w*|se\s+garantiza|pued\w*\s+asegurar|"
    r"es\s+segur[oa]|sin\s+riesgo|no\s+(?:se\s+)?perder\w*)\b"
    r"[^.\n]{0,140}\bconfigur\w*\b|\bconfigur\w*\b[^.\n]{0,140}"
    r"\b(?:se\s+conserva(?:ra)?|queda\s+intacta|no\s+(?:se\s+)?pierde)\b",
    re.IGNORECASE,
)
_HP013_NO_DOC_RE = re.compile(
    r"\b(?:manual|documentacion)\b[^.\n]{0,100}\b(?:no|sin)\b[^.\n]{0,80}"
    r"\b(?:procedimiento|instrucciones?|documenta\w*)\b|"
    r"\bno\s+(?:esta|se\s+encuentra)\s+documentad\w*\b",
    re.IGNORECASE,
)
_HP013_HEDGE_RE = re.compile(
    r"\b(?:cabe\s+esperar|deberia|en\s+principio|probablemente|previsiblemente|"
    r"no\s+garantiza|pero|aunque|sin\s+embargo|no\s+esta\s+documentad\w*)\b",
    re.IGNORECASE,
)


def score_hp013_guard(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    guard: Mapping[str, Any],
) -> CheckResult:
    check_id = f"guard:{guard.get('guard_id') or 'hp013'}"
    if guard.get("algorithm") != "hp013_safety_guard_v1":
        return _result(check_id, INSTRUMENT_ERROR, "unknown hp013 guard algorithm")
    try:
        groups, forbidden = _forms(guard)
    except ScorerInstrumentError as exc:
        return _result(check_id, INSTRUMENT_ERROR, str(exc))

    forbidden_hits = _surface_hits(answer, forbidden)
    categorical = bool(_HP013_GUARANTEE_RE.search(answer))
    no_documented_procedure = bool(_HP013_NO_DOC_RE.search(_fold(answer)))
    if forbidden_hits or categorical:
        return _result(
            check_id,
            FAIL,
            "answer invents a safe procedure or guarantees configuration preservation",
            evidence={"forbidden_hits": forbidden_hits, "categorical_guarantee": categorical},
        )

    eeprom = bool(re.search(r"\beeprom\b|\bno\s+volatil\b", _fold(answer)))
    if eeprom and not _HP013_HEDGE_RE.search(_fold(answer)):
        return _result(
            check_id,
            FAIL,
            "EEPROM/non-volatility is presented without the required caveat",
        )

    hits_by_group = [_surface_hits(answer, group) for group in groups]
    if not no_documented_procedure or any(not hits for hits in hits_by_group):
        # A procedural-looking answer without the no-documentation boundary is more
        # dangerous than mere silence, but still goes to blind review unless a
        # categorical forbidden claim was detected above.
        return _result(
            check_id,
            REVIEW,
            "hp013 safety boundary is absent or not deterministically complete",
            evidence={
                "procedure_language": bool(_HP013_PROCEDURE_RE.search(answer)),
                "no_documented_procedure": no_documented_procedure,
            },
        )

    fragments = _surface_group_citations(answer, hits_by_group)
    citation = _accredit_citations(fragments, served_context, guard)
    if citation.status != PASS:
        return _result(check_id, citation.status, *(citation.reasons or (citation.status,)))
    return _result(
        check_id,
        REVIEW,
        "safety wording requires blind semantic review",
        evidence={
            "machine_safety_precheck": PASS,
            "no_documented_procedure": True,
            "eeprom_mentioned": eeprom,
            "hedged_if_eeprom": not eeprom or bool(_HP013_HEDGE_RE.search(_fold(answer))),
            "local_citations": fragments,
        },
    )


def score_known_hp017_menu_conflict(
    answer: str, conflict: Mapping[str, Any]
) -> CheckResult:
    check_id = f"conflict:{conflict.get('conflict_id') or MENU_CONFLICT_ID}"
    if conflict.get("algorithm") != "hp017_menu_conflict_v1":
        return _result(check_id, INSTRUMENT_ERROR, "unknown hp017 conflict algorithm")
    if conflict.get("conflict_id") != MENU_CONFLICT_ID:
        return _result(check_id, INSTRUMENT_ERROR, "unexpected hp017 conflict identity")
    try:
        from src.rag.answer_planner import (
            AnswerConflict,
            AnswerConflictEvidence,
            validate_answer_conflicts,
        )

        evidence = tuple(
            AnswerConflictEvidence(
                fragment_number=index,
                candidate_id=f"contract-side-{index}",
                product_scope="Pearl",
                source_file=str(side.get("source_file") or "contract"),
                document_revision=str(side.get("document_revision") or "contract"),
                value=str(side.get("value") or value),
                statement=str(side.get("statement") or "contract evidence"),
                source_start=0,
                source_end=1,
            )
            for index, (side, value) in enumerate(
                zip(
                    conflict.get("source_sides") or ({}, {}),
                    ("7", "8"),
                ),
                start=1,
            )
        )
        frozen = AnswerConflict(
            conflict_id=MENU_CONFLICT_ID,
            kind="menu_path_disagreement",
            product_scope="Pearl",
            operation="cause_effect_menu_path",
            values=("7", "8"),
            evidence=evidence,
        )
        row = validate_answer_conflicts(answer, [frozen])["rows"][0]
    except Exception as exc:
        return _result(
            check_id,
            INSTRUMENT_ERROR,
            f"production conflict validator failed: {type(exc).__name__}",
        )

    if not row["safe"]:
        return _result(
            check_id,
            FAIL,
            "flat or directive menu number is unsafe under the known 7-vs-8 conflict",
            evidence={
                "asserted_values": row["asserted_values"],
                "directive_values": row["directive_values"],
                "disclosed": row["disclosed"],
            },
        )
    return _result(
        check_id,
        PASS,
        evidence={
            "asserted_values": row["asserted_values"],
            "disclosed": row["disclosed"],
        },
    )


def _stored_control_error(reason: str, *, source_hash: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": STORED_CONTROL_SCHEMA,
        "status": INSTRUMENT_ERROR,
        "decision": "HOLD_INSTRUMENT_ERROR",
        "scope": "HISTORICAL_CONFLICT_ONLY",
        "candidate_runtime_measured": False,
        "paid_model_calls": 0,
        "network_calls": 0,
        "reasons": [reason],
    }
    if source_hash is not None:
        result["source_sha256_lf"] = source_hash
    return result


def score_stored_controls(
    replicas_path: Path | str = STORED_CONTROL_PATH,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-score the sealed A-C1 hp017 prior without measuring the candidate.

    This deliberately scores only the registered 7-vs-8 menu conflict.  The
    historical rows do not carry the P1 physical receipts or its exact protected
    packet, so this function can emit a prepaid HOLD but can never PASS (or FAIL)
    the unmeasured candidate runtime.
    """

    path = Path(replicas_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _stored_control_error(f"stored control is unreadable: {type(exc).__name__}")
    source_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if source_hash != STORED_CONTROL_SHA256_LF:
        return _stored_control_error(
            "stored control artifact hash drifted",
            source_hash=source_hash,
        )

    try:
        text = raw.decode("utf-8")
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _stored_control_error(
            f"stored control cannot be parsed: {type(exc).__name__}",
            source_hash=source_hash,
        )
    if len(rows) != 96 or not all(isinstance(row, dict) for row in rows):
        return _stored_control_error(
            "stored control population is not the sealed 96-row matrix",
            source_hash=source_hash,
        )

    try:
        if contract is None:
            effective_contract = load_fact_contract(
                ROOT / "evals/s277_c1_p1_fact_contract_v1.json"
            )
        else:
            validate_fact_contract(contract)
            effective_contract = contract
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ScorerInstrumentError) as exc:
        return _stored_control_error(
            f"fact contract cannot be validated: {type(exc).__name__}: {exc}",
            source_hash=source_hash,
        )
    conflicts = [
        row
        for row in effective_contract.get("registered_conflicts", [])
        if isinstance(row, dict) and row.get("conflict_id") == MENU_CONFLICT_ID
    ]
    if len(conflicts) != 1:
        return _stored_control_error(
            "registered hp017 conflict is absent or duplicated",
            source_hash=source_hash,
        )
    conflict = conflicts[0]

    selected = [
        row
        for row in rows
        if row.get("arm") == STORED_CONTROL_ARM and row.get("qid") == TARGET_QID
    ]
    try:
        selected.sort(key=lambda row: int(row.get("replicate")))
    except (TypeError, ValueError):
        return _stored_control_error(
            "stored control replicate identifiers are invalid",
            source_hash=source_hash,
        )
    if tuple(row.get("replicate") for row in selected) != STORED_CONTROL_REPLICATES:
        return _stored_control_error(
            "stored A-C1 hp017 population is not exactly r1/r2/r3",
            source_hash=source_hash,
        )

    per_replica: list[dict[str, Any]] = []
    for row in selected:
        answer = row.get(STORED_CONTROL_ANSWER_FIELD)
        if not isinstance(answer, str) or not answer.strip():
            return _stored_control_error(
                f"stored hp017:r{row.get('replicate')} answer is absent",
                source_hash=source_hash,
            )
        check = score_known_hp017_menu_conflict(answer, conflict)
        if check.status == INSTRUMENT_ERROR:
            return _stored_control_error(
                f"conflict scorer failed for hp017:r{row.get('replicate')}",
                source_hash=source_hash,
            )
        per_replica.append(
            {
                "replica_key": f"hp017:r{row['replicate']}",
                "answer_sha256_lf": _sha256_lf_text(answer),
                "conflict_status": check.status,
                "conflict_check": check.to_dict(),
            }
        )

    conflict_failures = sum(row["conflict_status"] == FAIL for row in per_replica)
    confirmed = conflict_failures == len(STORED_CONTROL_REPLICATES)
    return {
        "schema_version": STORED_CONTROL_SCHEMA,
        # REVIEW means blocking evidence about a historical prior.  It is not a
        # score of the candidate, which remains explicitly unmeasured.
        "status": REVIEW,
        "decision": (
            STORED_CONTROL_HOLD
            if confirmed
            else "HOLD_STORED_CONTROL_NOT_AUTHORITATIVE"
        ),
        "scope": "HISTORICAL_CONFLICT_ONLY",
        "candidate_runtime_measured": False,
        "candidate_status": None,
        "source_artifact": "evals/s274_probeCD_replicas_v1.jsonl",
        "source_sha256_lf": source_hash,
        "historical_arm": STORED_CONTROL_ARM,
        "historical_answer_field": STORED_CONTROL_ANSWER_FIELD,
        "conflict_id": MENU_CONFLICT_ID,
        "replica_count": len(per_replica),
        "conflict_failures": conflict_failures,
        "confirmed_3_of_3": confirmed,
        "replicas": per_replica,
        "paid_model_calls": 0,
        "network_calls": 0,
        "claim": None,
        "limitations": [
            "conflict-only re-score of already generated historical A-C1 answers",
            "no P1 physical contract or candidate runtime was measured",
            "this result can never establish candidate PASS or candidate FAIL",
        ],
    }


def _bind_hp017_context(
    served_context: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    protected_prefix_rows: int | None = None,
) -> CheckResult:
    """Resolve and re-attest the target dynamically; never assume ``F12``.

    A target already selected by the reranker is served as the complete,
    immutable source chunk. A target recovered after rerank is instead a
    bounded coverage view and therefore still requires its exact callout
    receipt. Both routes share the identity, content-hash, source-span,
    answer, and citation checks below.
    """
    check_id = "hp017_context_binding"
    if target.get("algorithm") != "hp017_compound_warning_exact_v1":
        return _result(check_id, INSTRUMENT_ERROR, "unknown hp017 target algorithm")
    expected_id = str(
        (target.get("target_identity") or {}).get("candidate_id")
        or target.get("target_id")
        or ""
    )
    if expected_id != TARGET_ID:
        return _result(check_id, INSTRUMENT_ERROR, "target candidate identity drifted")
    matches = [
        (index, chunk)
        for index, chunk in enumerate(served_context, start=1)
        if _chunk_id(chunk) == TARGET_ID
    ]
    if len(matches) != 1:
        return _result(
            check_id,
            INSTRUMENT_ERROR,
            f"expected exactly one target chunk, observed {len(matches)}",
        )
    fragment, chunk = matches[0]
    if protected_prefix_rows is not None and (
        isinstance(protected_prefix_rows, bool)
        or not isinstance(protected_prefix_rows, int)
        or not 0 <= protected_prefix_rows <= len(served_context)
    ):
        return _result(
            check_id,
            INSTRUMENT_ERROR,
            "protected prefix row count is invalid",
        )
    delivery_route = (
        "protected_prefix_full_source"
        if protected_prefix_rows is not None and fragment <= protected_prefix_rows
        else "coverage_append"
    )

    identity = target.get("target_identity")
    if not isinstance(identity, dict):
        return _result(check_id, INSTRUMENT_ERROR, "target_identity is missing")
    identity_fields = (
        ("document_id", "document_id"),
        ("source_file", "source_file"),
        ("page_number", "page_number"),
        ("product_model", "product_model"),
    )
    for expected_key, actual_key in identity_fields:
        expected = identity.get(expected_key)
        if expected in (None, ""):
            continue
        actual = chunk.get(actual_key)
        if actual in (None, ""):
            return _result(
                check_id,
                INSTRUMENT_ERROR,
                f"target context lacks {actual_key}",
            )
        equal = (
            int(expected) == int(actual)
            if expected_key == "page_number"
            else _surface_normalize(str(expected)) == _surface_normalize(str(actual))
        )
        if not equal:
            return _result(check_id, INSTRUMENT_ERROR, f"target {actual_key} drifted")

    expected_content_hash = str(identity.get("content_sha256") or "")
    if expected_content_hash and _sha256_lf_text(str(chunk.get("content") or "")) != expected_content_hash:
        return _result(check_id, INSTRUMENT_ERROR, "target content hash drifted")

    content = str(chunk.get("content") or "")
    if delivery_route == "coverage_append":
        try:
            from src.rag.post_rerank_coverage import has_exact_mandatory_callout_receipt

            receipt_ok = has_exact_mandatory_callout_receipt(dict(chunk))
        except Exception as exc:
            return _result(
                check_id,
                INSTRUMENT_ERROR,
                f"mandatory callout revalidation failed: {type(exc).__name__}",
            )
        cards = chunk.get("mandatory_callout_cards")
        if not receipt_ok or not isinstance(cards, list) or len(cards) != 1:
            return _result(
                check_id,
                INSTRUMENT_ERROR,
                "appended target mandatory callout card/receipt drifted",
            )
        card = cards[0]
        if (
            not isinstance(card, dict)
            or card.get("exact_source_span_validated") is not True
        ):
            return _result(
                check_id,
                INSTRUMENT_ERROR,
                "appended target callout lacks exact span receipt",
            )
        card_start, card_end = card.get("start"), card.get("end")
    else:
        # The surrounding coverage-lineage check proves this row is byte-equal
        # to the protected rerank prefix. Its entire immutable content is the
        # serving boundary, so an append-only coverage receipt is inapplicable.
        card_start, card_end = 0, len(content)

    clauses = target.get("clauses")
    if not isinstance(clauses, list) or len(clauses) != 2:
        return _result(check_id, INSTRUMENT_ERROR, "target must contain exactly two clauses")
    derived: list[dict[str, Any]] = []
    for clause in clauses:
        if not isinstance(clause, dict):
            return _result(check_id, INSTRUMENT_ERROR, "target clause is not an object")
        start, end = clause.get("source_start"), clause.get("source_end")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(content):
            return _result(check_id, INSTRUMENT_ERROR, "target clause span is invalid")
        if not isinstance(card_start, int) or not isinstance(card_end, int) or not (
            card_start <= start < end <= card_end
        ):
            return _result(check_id, INSTRUMENT_ERROR, "target clause is outside callout card")
        source_span = content[start:end]
        if _sha256_lf_text(source_span) != clause.get("source_span_sha256"):
            return _result(check_id, INSTRUMENT_ERROR, "target clause source hash drifted")
        exact_text = str(clause.get("exact_text") or "")
        if not _find_normalized_spans(source_span, exact_text):
            return _result(check_id, INSTRUMENT_ERROR, "target exact text is not its source span")
        derived.append(
            {
                "obligation_id": clause.get("obligation_id"),
                "exact_text": exact_text,
                "source_start": start,
                "source_end": end,
            }
        )

    return _result(
        check_id,
        PASS,
        evidence={
            "target_fragment": fragment,
            "target_chunk_id": TARGET_ID,
            "delivery_route": delivery_route,
            "derived_clauses": derived,
            "callout_start": card_start,
            "callout_end": card_end,
        },
    )


def bind_hp017_context(
    served_context: Sequence[Mapping[str, Any]], target: Mapping[str, Any]
) -> CheckResult:
    """Strict public binding for the append route.

    The prefix exception is private to ``score_hp017_case`` and is activated
    only after that scorer proves the three-stage byte-equal lineage.
    """
    return _bind_hp017_context(served_context, target)


def _exact_warning_unit_citations(
    answer: str,
    exact_texts: Sequence[str],
) -> list[list[int]]:
    """Bind warnings only when each whole cited claim is exact source wording."""
    normalized = [_surface_normalize(text) for text in exact_texts]
    combined = " ".join(normalized)
    citations: list[list[int]] = [[] for _ in exact_texts]
    for group in _CITATION_GROUP_RE.finditer(answer):
        prefix = answer[: group.start()]
        paragraph_start = max(prefix.rfind("\n\n"), prefix.rfind("\r\n\r\n"))
        paragraph_start = 0 if paragraph_start < 0 else paragraph_start + 2
        paragraph_claim = answer[paragraph_start : group.start()]
        if _surface_normalize(paragraph_claim) == combined:
            bound = [int(value) for value in _EXACT_CITATION_RE.findall(group.group())]
            if bound:
                return [list(dict.fromkeys(bound)) for _ in exact_texts]
    for unit in parse_local_citation_units(answer):
        observed = _surface_normalize(unit["claim_text"])
        bound = list(dict.fromkeys(unit["citations"]))
        if not bound:
            continue
        if observed == combined:
            return [bound for _ in exact_texts]
        for index, expected in enumerate(normalized):
            if observed == expected and not citations[index]:
                citations[index] = bound
    return citations


def _score_hp017_warning_block(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    protected_prefix_rows: int | None = None,
) -> CheckResult:
    binding = _bind_hp017_context(
        served_context,
        target,
        protected_prefix_rows=protected_prefix_rows,
    )
    if binding.status != PASS:
        return binding
    evidence = dict(binding.evidence or {})
    target_fragment = int(evidence["target_fragment"])
    derived = evidence["derived_clauses"]
    clause_spans: list[tuple[int, int]] = []
    missing: list[str] = []
    for clause in derived:
        spans = _find_normalized_spans(answer, clause["exact_text"])
        if not spans:
            missing.append(str(clause["obligation_id"]))
        else:
            clause_spans.append(spans[0])
    if missing:
        folded_answer = _surface_normalize(answer)
        plausible_paraphrase = {
            "obl_16637b935bd4": bool(
                re.search(r"\b(?:contradict\w*|incompatib\w*)\b", folded_answer)
                and re.search(r"\b(?:reglas?|logic\w*)\b", folded_answer)
            ),
            "obl_0d6a30948dfd": bool(
                re.search(r"\b(?:probar|verificar|comprobar|ensayar)\b", folded_answer)
                and re.search(r"\b(?:puesta en marcha|comision\w*)\b", folded_answer)
                and re.search(r"\breglas?\b", folded_answer)
            ),
        }
        relevant = all(plausible_paraphrase.get(obligation_id, False) for obligation_id in missing)
        return _result(
            "hp017_warning_block",
            REVIEW if relevant else FAIL,
            "one or both exact warning clauses are absent",
            evidence={"missing_obligation_ids": missing},
        )

    exact_texts = [str(row["exact_text"]) for row in derived]
    citations_by_clause = _exact_warning_unit_citations(answer, exact_texts)
    if any(not citations for citations in citations_by_clause):
        return _result(
            "hp017_warning_block",
            FAIL,
            "each warning must be an exact complete local citation unit",
            evidence={"citations_by_clause": citations_by_clause},
        )
    for fragments in citations_by_clause:
        if target_fragment not in fragments:
            return _result(
                "hp017_warning_block",
                FAIL,
                "local warning citation does not include the dynamic target fragment",
                evidence={"target_fragment": target_fragment, "observed": fragments},
            )
        citation = _accredit_citations(
            fragments,
            served_context,
            {**dict(target), "source_refs": [dict(target.get("target_identity") or {}, chunk_id=TARGET_ID)]},
            exact_texts=exact_texts,
        )
        if citation.status != PASS:
            return _result(
                "hp017_warning_block",
                citation.status,
                *(citation.reasons or (citation.status,)),
                evidence={"citation": citation.to_dict()},
            )

    stripped = answer
    for clause in exact_texts:
        for start, end in reversed(_find_normalized_spans(stripped, clause)):
            stripped = stripped[:start] + stripped[end:]
    stripped = _EXACT_CITATION_RE.sub("", stripped)
    stripped = re.sub(r"[\s>*_`~#|:;,.()\[\]{}\-–—]+", " ", stripped).strip()
    if len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", stripped)) < 40:
        return _result(
            "hp017_warning_block",
            FAIL,
            "answer is reduced to the warning block",
        )

    return _result(
        "hp017_warning_block",
        PASS,
        evidence={
            "target_fragment": target_fragment,
            "clause_obligation_ids": [row["obligation_id"] for row in derived],
            "citations_by_clause": citations_by_clause,
            "technical_nonwarning_chars": len(stripped),
        },
    )


def score_hp017_warning_block(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> CheckResult:
    """Strict public warning score for a receipted coverage append."""
    return _score_hp017_warning_block(answer, served_context, target)


def score_hp017_base_facts(
    answer: str,
    served_context: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
) -> CheckResult:
    return _combine(
        "hp017_base_facts",
        [score_protected_fact(answer, served_context, fact) for fact in facts],
    )


def score_hp017_case(
    replica: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> CheckResult:
    answer = str(replica.get("answer") or "")
    context = replica.get("served_context")
    if not isinstance(context, list):
        return _result("hp017_case", INSTRUMENT_ERROR, "served_context is absent")
    facts = [
        fact for fact in contract.get("protected_facts", []) if fact.get("qid") == TARGET_QID
    ]
    conflicts = [
        row
        for row in contract.get("registered_conflicts", [])
        if row.get("qid") == TARGET_QID
    ]
    if len(facts) != 3 or len(conflicts) != 1:
        return _result(
            "hp017_case",
            INSTRUMENT_ERROR,
            "hp017 contract must contain three base facts and one conflict",
        )

    target = contract.get("c1_target")
    if not isinstance(target, dict):
        return _result("hp017_case", INSTRUMENT_ERROR, "c1_target is absent")
    structural_output: Any = None
    full_source_prefix_rows: int | None = None
    coverage = replica.get("coverage")
    if not isinstance(coverage, dict):
        coverage_check = _result("hp017_coverage", INSTRUMENT_ERROR, "coverage trace absent")
    else:
        rerank = replica.get("rerank")
        rerank_prefix = rerank.get("prefix") if isinstance(rerank, dict) else None
        structural = replica.get("structural_fetch")
        structural_output = (
            structural.get("output") if isinstance(structural, dict) else None
        )
        output_context = coverage.get("output_context")
        if (
            coverage.get("status") != "evaluated"
            or not isinstance(rerank_prefix, list)
            or not isinstance(structural_output, list)
            or not isinstance(output_context, list)
        ):
            coverage_check = _result(
                "hp017_coverage",
                INSTRUMENT_ERROR,
                "coverage lineage is absent or not evaluated",
            )
        elif structural_output != rerank_prefix:
            coverage_check = _result(
                "hp017_coverage",
                FAIL,
                "structural prefix differs from the canonical rerank prefix",
            )
        elif output_context[: len(structural_output)] != structural_output:
            coverage_check = _result(
                "hp017_coverage",
                FAIL,
                "coverage changed the protected structural prefix",
            )
        else:
            prefix_ids = [
                str(row.get("id") or "") if isinstance(row, dict) else ""
                for row in structural_output
            ]
            appended_ids = [
                str(row.get("id") or "") if isinstance(row, dict) else ""
                for row in output_context[len(structural_output) :]
            ]
            all_ids = [*prefix_ids, *appended_ids]
            if any(not value for value in all_ids) or len(set(all_ids)) != len(all_ids):
                coverage_check = _result(
                    "hp017_coverage",
                    FAIL,
                    "coverage lineage contains a missing or duplicate identity",
                )
            elif TARGET_ID in prefix_ids:
                full_source_prefix_rows = len(structural_output)
                coverage_check = _result(
                    "hp017_coverage",
                    PASS,
                    evidence={
                        "delivery_route": "protected_prefix_full_source",
                        "target_fragment": prefix_ids.index(TARGET_ID) + 1,
                        "derived_appended_ids": appended_ids,
                    },
                )
            elif TARGET_ID in appended_ids:
                coverage_check = _result(
                    "hp017_coverage",
                    PASS,
                    evidence={
                        "delivery_route": "coverage_append",
                        "target_fragment": len(prefix_ids)
                        + appended_ids.index(TARGET_ID)
                        + 1,
                        "derived_appended_ids": appended_ids,
                    },
                )
            else:
                coverage_check = _result(
                    "hp017_coverage",
                    FAIL,
                    "target is absent from both lawful delivery routes",
                )

    must_preserve = replica.get("must_preserve")
    if not isinstance(must_preserve, dict):
        mp_check = _result("hp017_must_preserve_trace", INSTRUMENT_ERROR, "trace absent")
    elif must_preserve.get("status") in {"error", "invalid", "not_evaluated"}:
        mp_check = _result("hp017_must_preserve_trace", FAIL, "must-preserve trace failed")
    else:
        mp_check = _result("hp017_must_preserve_trace", PASS)

    return _combine(
        "hp017_case",
        (
            coverage_check,
            mp_check,
            score_hp017_base_facts(answer, context, facts),
            _score_hp017_warning_block(
                answer,
                context,
                target,
                protected_prefix_rows=full_source_prefix_rows,
            ),
            score_known_hp017_menu_conflict(answer, conflicts[0]),
        ),
    )


def _validate_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ScorerInstrumentError(f"{label} must be a non-empty string")


def validate_fact_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise ScorerInstrumentError("fact contract must be an object")
    if contract.get("schema_version") != CONTRACT_SCHEMA:
        raise ScorerInstrumentError("fact contract schema drift")
    if contract.get("contract_id") != EXPECTED_CONTRACT_ID:
        raise ScorerInstrumentError("fact contract identity drift")
    population = contract.get("population")
    if not isinstance(population, dict):
        raise ScorerInstrumentError("population is missing")
    if tuple(population.get("qids") or ()) != P1_QIDS:
        raise ScorerInstrumentError("P1 QID population/order drift")
    if population.get("expected_base_fact_count") != 43:
        raise ScorerInstrumentError("protected base count must be 43")

    facts = contract.get("protected_facts")
    if not isinstance(facts, list) or len(facts) != 43:
        raise ScorerInstrumentError("protected_facts must contain exactly 43 rows")
    fact_ids: set[str] = set()
    observed_counts = {qid: 0 for qid in P1_QIDS}
    for fact in facts:
        if not isinstance(fact, dict):
            raise ScorerInstrumentError("protected fact is not an object")
        fact_id = str(fact.get("fact_id") or "")
        _validate_string(fact_id, "fact_id")
        if fact_id in fact_ids:
            raise ScorerInstrumentError(f"duplicate fact_id: {fact_id}")
        fact_ids.add(fact_id)
        qid = fact.get("qid")
        if qid not in observed_counts:
            raise ScorerInstrumentError(f"unknown fact QID: {qid!r}")
        observed_counts[qid] += 1
        if fact.get("algorithm") not in _FACT_ALGORITHMS:
            raise ScorerInstrumentError(f"unknown fact algorithm for {fact_id}")
        _forms(fact)
        for ref in _source_refs(fact):
            _validate_source_ref_contract(ref, fact_id)
        if fact.get("binding_level") not in _BINDING_LEVELS:
            raise ScorerInstrumentError(f"invalid binding_level for {fact_id}")
        statement = fact.get("statement")
        _validate_string(statement, f"statement for {fact_id}")
        if fact.get("statement_sha256") != _sha256_lf_text(statement):
            raise ScorerInstrumentError(f"statement hash drift for {fact_id}")

    expected_counts = population.get("per_qid_base_counts")
    if expected_counts != observed_counts:
        raise ScorerInstrumentError("per-QID protected fact counts drifted")

    guards = contract.get("question_guards")
    if not isinstance(guards, list) or not guards:
        raise ScorerInstrumentError("question_guards are missing")
    guard_ids: set[str] = set()
    for guard in guards:
        if not isinstance(guard, dict) or guard.get("algorithm") not in _GUARD_ALGORITHMS:
            raise ScorerInstrumentError("unknown question guard")
        guard_id = str(guard.get("guard_id") or "")
        _validate_string(guard_id, "guard_id")
        if guard_id in guard_ids:
            raise ScorerInstrumentError(f"duplicate guard_id: {guard_id}")
        guard_ids.add(guard_id)
        _forms(guard)
        for ref in _source_refs(guard):
            _validate_source_ref_contract(ref, guard_id)
    if not any(guard.get("qid") == "hp013" for guard in guards):
        raise ScorerInstrumentError("hp013 safety guard is absent")

    conflicts = contract.get("registered_conflicts")
    if not isinstance(conflicts, list) or len(conflicts) != 1:
        raise ScorerInstrumentError("exactly one registered conflict is required")
    conflict = conflicts[0]
    if (
        not isinstance(conflict, dict)
        or conflict.get("conflict_id") != MENU_CONFLICT_ID
        or conflict.get("algorithm") not in _CONFLICT_ALGORITHMS
    ):
        raise ScorerInstrumentError("registered hp017 conflict drifted")

    target = contract.get("c1_target")
    if not isinstance(target, dict) or target.get("algorithm") not in _TARGET_ALGORITHMS:
        raise ScorerInstrumentError("C1 target is missing or unknown")
    if target.get("target_id") != TARGET_ID or target.get("qid") != TARGET_QID:
        raise ScorerInstrumentError("C1 target identity/QID drifted")
    if tuple(target.get("compound_obligation_ids") or ()) != TARGET_OBLIGATION_IDS:
        raise ScorerInstrumentError("C1 compound obligation IDs drifted")
    clauses = target.get("clauses")
    if not isinstance(clauses, list) or tuple(
        clause.get("obligation_id") for clause in clauses if isinstance(clause, dict)
    ) != TARGET_OBLIGATION_IDS:
        raise ScorerInstrumentError("C1 target clause order/identity drifted")

    declared_payload = contract.get("payload_sha256")
    computed_payload = _canonical_sha256(
        {key: value for key, value in contract.items() if key != "payload_sha256"}
    )
    if (
        declared_payload != computed_payload
        or declared_payload != EXPECTED_CONTRACT_PAYLOAD_SHA256
    ):
        raise ScorerInstrumentError("preregistered fact contract payload drift")


def load_fact_contract(path: str | Path) -> dict[str, Any]:
    try:
        contract = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScorerInstrumentError(f"cannot load fact contract: {type(exc).__name__}") from exc
    validate_fact_contract(contract)
    return contract


def _leaf_check_rows(check: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    nested = (check.get("evidence") or {}).get("checks") if isinstance(
        check.get("evidence"), dict
    ) else None
    if isinstance(nested, list) and nested and all(isinstance(row, dict) for row in nested):
        leaves: list[Mapping[str, Any]] = []
        for row in nested:
            leaves.extend(_leaf_check_rows(row))
        return leaves
    return [check]


def _review_items(
    *,
    replica_key: str,
    answer_sha256: str,
    context_sha256: str,
    contract_id: Any,
    contract_sha256: str,
    checks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for top_level in checks:
        for check in _leaf_check_rows(top_level):
            if check.get("status") != REVIEW:
                continue
            check_id = str(check.get("check_id") or "")
            if not check_id:
                raise ScorerInstrumentError("REVIEW check lacks check_id")
            review_key = f"{replica_key}:{check_id}"
            if review_key in seen:
                raise ScorerInstrumentError(f"duplicate review key: {review_key}")
            seen.add(review_key)
            binding_payload = {
                "schema_version": SCHEMA_VERSION,
                "scorer_sha256": scorer_sha256(),
                "contract_id": contract_id,
                "contract_sha256": contract_sha256,
                "replica_key": replica_key,
                "answer_sha256": answer_sha256,
                "context_sha256": context_sha256,
                "check": check,
            }
            items.append(
                {
                    "review_key": review_key,
                    "replica_key": replica_key,
                    "check_id": check_id,
                    "answer_sha256": answer_sha256,
                    "context_sha256": context_sha256,
                    "contract_sha256": contract_sha256,
                    "scorer_sha256": binding_payload["scorer_sha256"],
                    "binding_sha256": _canonical_sha256(binding_payload),
                    "check": dict(check),
                }
            )
    return items


def score_replica(replica: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Score one persisted physical response; never calls a provider."""
    try:
        validate_fact_contract(contract)
    except ScorerInstrumentError as exc:
        row = _result("contract", INSTRUMENT_ERROR, str(exc))
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "replica_key": replica.get("replica_key") if isinstance(replica, dict) else None,
            "status": INSTRUMENT_ERROR,
            "checks": [row.to_dict()],
        }
    if not isinstance(replica, dict):
        row = _result("replica", INSTRUMENT_ERROR, "replica receipt is not an object")
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "status": row.status,
            "checks": [row.to_dict()],
        }

    replica_key = str(replica.get("replica_key") or "")
    qid = str(replica.get("qid") or "")
    replica_id = str(replica.get("replica_id") or "")
    expected_key = f"{qid}:{replica_id}"
    checks: list[CheckResult] = []
    if replica.get("schema") != REPLICA_SCHEMA:
        checks.append(_result("replica_schema", INSTRUMENT_ERROR, "replica schema drift"))
    if replica_key != expected_key or replica_key not in P1_REPLICA_KEYS:
        checks.append(_result("replica_identity", INSTRUMENT_ERROR, "replica key/QID drift"))

    answer = replica.get("answer")
    if not isinstance(answer, str):
        checks.append(_result("answer", INSTRUMENT_ERROR, "answer is not a string"))
        answer = ""
    elif not answer.strip():
        checks.append(_result("answer", FAIL, "empty or invisible answer"))
    else:
        checks.append(_result("answer", PASS))

    context = replica.get("served_context")
    citations = validate_global_citations(answer, context)
    checks.append(citations)

    provider = replica.get("provider")
    if not isinstance(provider, dict) or "stop_reason" not in provider:
        checks.append(_result("provider_stop", INSTRUMENT_ERROR, "provider stop receipt absent"))
    elif provider.get("stop_reason") != "end_turn":
        checks.append(
            _result(
                "provider_stop",
                FAIL,
                f"provider stop_reason={provider.get('stop_reason')!r}, expected end_turn",
            )
        )
    else:
        checks.append(_result("provider_stop", PASS))

    if citations.status not in {INSTRUMENT_ERROR} and isinstance(context, list) and answer.strip():
        if qid == TARGET_QID:
            checks.append(score_hp017_case(replica, contract))
        else:
            facts = [fact for fact in contract["protected_facts"] if fact.get("qid") == qid]
            checks.extend(score_protected_fact(answer, context, fact) for fact in facts)
            guards = [guard for guard in contract["question_guards"] if guard.get("qid") == qid]
            for guard in guards:
                if guard.get("algorithm") == "hp013_safety_guard_v1":
                    checks.append(score_hp013_guard(answer, context, guard))
                else:
                    checks.append(
                        _result(
                            f"guard:{guard.get('guard_id')}",
                            INSTRUMENT_ERROR,
                            "unknown guard algorithm",
                        )
                    )

    combined = _combine("replica", checks)
    answer_hash = _sha256_lf_text(answer)
    context_hash = _canonical_sha256(context) if isinstance(context, list) else ""
    contract_hash = _canonical_sha256(contract)
    check_rows = [row.to_dict() for row in checks]
    result = {
        "schema_version": SCHEMA_VERSION,
        "scorer_sha256": scorer_sha256(),
        "contract_id": contract.get("contract_id"),
        "contract_sha256": contract_hash,
        "replica_key": replica_key,
        "qid": qid,
        "replica_id": replica_id,
        "answer_sha256": answer_hash,
        "context_sha256": context_hash,
        "status": combined.status,
        "checks": check_rows,
    }
    result["review_items"] = _review_items(
        replica_key=replica_key,
        answer_sha256=answer_hash,
        context_sha256=context_hash,
        contract_id=contract.get("contract_id"),
        contract_sha256=contract_hash,
        checks=check_rows,
    )
    return result


def _validated_score_bindings(
    bindings: Mapping[str, Any] | None,
    contract: Mapping[str, Any],
) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(bindings, Mapping):
        return None, "authoritative run/prereg/contract bindings are absent"
    if set(bindings) != _SCORE_BINDING_FIELDS:
        return None, "authoritative score binding field population drift"
    normalized = {key: str(bindings.get(key) or "") for key in _SCORE_BINDING_FIELDS}
    if any(not _HEX64_RE.fullmatch(value) for value in normalized.values()):
        return None, "authoritative score binding contains a non-canonical hash"
    if normalized["fact_contract_sha256_lf"] != EXPECTED_CONTRACT_SHA256_LF:
        return None, "fact contract LF hash is not the preregistered authority"
    if (
        normalized["fact_contract_payload_sha256"]
        != contract.get("payload_sha256")
        or normalized["fact_contract_payload_sha256"]
        != EXPECTED_CONTRACT_PAYLOAD_SHA256
    ):
        return None, "fact contract payload is not bound to the score"
    return normalized, None


def score_run(
    replicas: Any,
    contract: Mapping[str, Any],
    *,
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        validate_fact_contract(contract)
    except ScorerInstrumentError as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": [str(exc)],
            "replicas": [],
        }
    if not isinstance(replicas, list):
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["replicas must be a list"],
            "replicas": [],
        }
    observed_order = [
        row.get("replica_key") if isinstance(row, dict) else None for row in replicas
    ]
    if tuple(observed_order) != P1_REPLICA_KEYS:
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "contract_id": contract.get("contract_id"),
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["27-replica population/order drift"],
            "observed_replica_keys": observed_order,
            "replicas": [],
        }

    score_bindings, binding_error = _validated_score_bindings(bindings, contract)
    if binding_error is not None:
        return {
            "schema_version": SCHEMA_VERSION,
            "scorer_sha256": scorer_sha256(),
            "contract_id": contract.get("contract_id"),
            "contract_sha256": _canonical_sha256(contract),
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": [binding_error],
            "replicas": [],
        }

    rows = [score_replica(replica, contract) for replica in replicas]
    status = max((row["status"] for row in rows), key=lambda value: _STATUS_ORDER[value])
    decision = {
        PASS: "PASS",
        REVIEW: "HOLD_REVIEW_REQUIRED",
        FAIL: "NO_GO",
        INSTRUMENT_ERROR: "HOLD_INSTRUMENT_ERROR",
    }[status]
    result = {
        "schema_version": SCHEMA_VERSION,
        "scorer_sha256": scorer_sha256(),
        "contract_id": contract.get("contract_id"),
        "contract_sha256": _canonical_sha256(contract),
        "score_bindings": score_bindings,
        "run_result_sha256": score_bindings["run_result_sha256"],
        "prereg_sha256": score_bindings["prereg_sha256"],
        "fact_contract_sha256_lf": score_bindings["fact_contract_sha256_lf"],
        "fact_contract_payload_sha256": score_bindings[
            "fact_contract_payload_sha256"
        ],
        "replica_manifest_sha256": score_bindings["replica_manifest_sha256"],
        "replicas_sha256": _canonical_sha256(replicas),
        "status": status,
        "decision": decision,
        "claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS" if status == PASS else None,
        "replica_count": len(rows),
        "status_counts": {
            key: sum(row["status"] == key for row in rows)
            for key in (PASS, FAIL, REVIEW, INSTRUMENT_ERROR)
        },
        "replicas": rows,
        "review_items": [
            item for row in rows for item in row.get("review_items", [])
        ],
    }
    return result


def adjudication_template(score_result: Mapping[str, Any]) -> dict[str, Any]:
    """Create a non-decisional, hash-bound template for blind human review."""
    if not isinstance(score_result, dict) or score_result.get("schema_version") != SCHEMA_VERSION:
        raise ScorerInstrumentError("score result schema drift")
    if score_result.get("scorer_sha256") != scorer_sha256():
        raise ScorerInstrumentError("score result was produced by another scorer build")
    reviews = score_result.get("review_items")
    if not isinstance(reviews, list):
        raise ScorerInstrumentError("score result has no review_items list")
    return {
        "schema_version": ADJUDICATION_SCHEMA,
        "scorer_sha256": scorer_sha256(),
        "score_result_sha256": _canonical_sha256(score_result),
        "blind_review_required": True,
        "rows": [
            {
                "review_key": item["review_key"],
                "binding_sha256": item["binding_sha256"],
                "decision": None,
                "reviewer": None,
                "reviewed_at": None,
                "blind": True,
                "rationale": None,
            }
            for item in reviews
        ],
    }


def finalize_score(
    score_result: Any,
    adjudication: Mapping[str, Any] | None = None,
    *,
    replicas: Any = None,
    contract: Mapping[str, Any] | None = None,
    bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve REVIEW rows only; FAIL/INSTRUMENT_ERROR are immutable.

    The finalizer cannot change the fact contract or algorithm after observing an
    answer.  Every human decision is tied to the exact scorer, score payload,
    answer, context, contract and leaf check through ``binding_sha256``.
    """
    if replicas is None or contract is None:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["authoritative persisted inputs are required for finalization"],
        }
    if isinstance(replicas, list):
        authoritative_score = score_run(replicas, contract, bindings=bindings)
    elif isinstance(replicas, dict):
        # Single-replica mode exists only for deterministic scorer/adjudication
        # mutation tests.  Release finalization always supplies the 27-row list.
        if bindings is not None:
            return {
                "schema_version": FINAL_SCHEMA,
                "status": INSTRUMENT_ERROR,
                "decision": "HOLD_INSTRUMENT_ERROR",
                "reasons": ["single-replica finalization cannot carry run bindings"],
            }
        authoritative_score = score_replica(replicas, contract)
    else:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["authoritative persisted replica population is invalid"],
        }
    if not isinstance(score_result, dict) or score_result.get("schema_version") != SCHEMA_VERSION:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["score result schema drift"],
        }
    authoritative_hash = _canonical_sha256(authoritative_score)
    if _canonical_sha256(score_result) != authoritative_hash:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "authoritative_score_sha256": authoritative_hash,
            "reasons": [
                "persisted score does not equal deterministic rescore of authoritative inputs"
            ],
        }
    if score_result.get("scorer_sha256") != scorer_sha256():
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["score result scorer hash drift"],
        }
    original_status = score_result.get("status")
    if original_status not in _STATUS_ORDER:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": ["score result has an unknown status"],
        }

    score_hash = _canonical_sha256(score_result)
    immutable_decision = {
        FAIL: "NO_GO",
        INSTRUMENT_ERROR: "HOLD_INSTRUMENT_ERROR",
    }
    if original_status in immutable_decision:
        if adjudication is not None:
            return {
                "schema_version": FINAL_SCHEMA,
                "status": INSTRUMENT_ERROR,
                "decision": "HOLD_INSTRUMENT_ERROR",
                "score_result_sha256": score_hash,
                "reasons": ["adjudication may not target FAIL or INSTRUMENT_ERROR"],
            }
        return {
            "schema_version": FINAL_SCHEMA,
            "status": original_status,
            "decision": immutable_decision[original_status],
            "score_result_sha256": score_hash,
            "adjudication_applied": False,
            "row_resolutions": [],
        }

    reviews = score_result.get("review_items")
    if not isinstance(reviews, list):
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "score_result_sha256": score_hash,
            "reasons": ["score result has no review_items list"],
        }
    if original_status == PASS:
        if reviews or adjudication is not None:
            return {
                "schema_version": FINAL_SCHEMA,
                "status": INSTRUMENT_ERROR,
                "decision": "HOLD_INSTRUMENT_ERROR",
                "score_result_sha256": score_hash,
                "reasons": ["PASS result cannot be adjudicated"],
            }
        return {
            "schema_version": FINAL_SCHEMA,
            "status": PASS,
            "decision": "PASS",
            "score_result_sha256": score_hash,
            "adjudication_applied": False,
            "row_resolutions": [],
            "claim": score_result.get("claim"),
        }
    if not reviews:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "score_result_sha256": score_hash,
            "reasons": ["REVIEW status has no bound review rows"],
        }
    if adjudication is None:
        return {
            "schema_version": FINAL_SCHEMA,
            "status": REVIEW,
            "decision": "HOLD_REVIEW_REQUIRED",
            "score_result_sha256": score_hash,
            "adjudication_applied": False,
            "pending_review_keys": [item["review_key"] for item in reviews],
            "row_resolutions": [],
        }

    if (
        adjudication.get("schema_version") != ADJUDICATION_SCHEMA
        or adjudication.get("scorer_sha256") != scorer_sha256()
        or adjudication.get("score_result_sha256") != score_hash
        or adjudication.get("blind_review_required") is not True
    ):
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "score_result_sha256": score_hash,
            "reasons": ["adjudication envelope/hash drift"],
        }
    adjudication_rows = adjudication.get("rows")
    if not isinstance(adjudication_rows, list):
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "score_result_sha256": score_hash,
            "reasons": ["adjudication rows are missing"],
        }
    expected = {item["review_key"]: item for item in reviews}
    observed: dict[str, Mapping[str, Any]] = {}
    for row in adjudication_rows:
        if not isinstance(row, dict):
            observed = {}
            break
        review_key = str(row.get("review_key") or "")
        if review_key in observed:
            observed = {}
            break
        observed[review_key] = row
    if set(observed) != set(expected):
        return {
            "schema_version": FINAL_SCHEMA,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "score_result_sha256": score_hash,
            "reasons": ["adjudication review-key population drift"],
        }

    resolutions: list[dict[str, Any]] = []
    for review_key, item in expected.items():
        row = observed[review_key]
        if row.get("binding_sha256") != item.get("binding_sha256"):
            return {
                "schema_version": FINAL_SCHEMA,
                "status": INSTRUMENT_ERROR,
                "decision": "HOLD_INSTRUMENT_ERROR",
                "score_result_sha256": score_hash,
                "reasons": [f"adjudication binding drift for {review_key}"],
            }
        decision = row.get("decision")
        if decision not in {"ADJUDICATED_PASS", "ADJUDICATED_FAIL"}:
            return {
                "schema_version": FINAL_SCHEMA,
                "status": REVIEW,
                "decision": "HOLD_REVIEW_REQUIRED",
                "score_result_sha256": score_hash,
                "reasons": [f"review decision missing for {review_key}"],
            }
        if (
            row.get("blind") is not True
            or not isinstance(row.get("reviewer"), str)
            or not row["reviewer"].strip()
            or not isinstance(row.get("reviewed_at"), str)
            or not row["reviewed_at"].strip()
            or not isinstance(row.get("rationale"), str)
            or not row["rationale"].strip()
        ):
            return {
                "schema_version": FINAL_SCHEMA,
                "status": INSTRUMENT_ERROR,
                "decision": "HOLD_INSTRUMENT_ERROR",
                "score_result_sha256": score_hash,
                "reasons": [f"incomplete blind adjudication metadata for {review_key}"],
            }
        resolutions.append(
            {
                "review_key": review_key,
                "binding_sha256": item["binding_sha256"],
                "decision": decision,
                "reviewer": row["reviewer"],
                "reviewed_at": row["reviewed_at"],
                "rationale": row["rationale"],
            }
        )

    any_fail = any(row["decision"] == "ADJUDICATED_FAIL" for row in resolutions)
    final_status = FAIL if any_fail else PASS
    return {
        "schema_version": FINAL_SCHEMA,
        "status": final_status,
        "decision": "NO_GO" if any_fail else "PASS",
        "score_result_sha256": score_hash,
        "adjudication_sha256": _canonical_sha256(adjudication),
        "adjudication_applied": True,
        "row_resolutions": resolutions,
        "claim": (
            score_result.get("claim")
            if not any_fail
            else None
        ),
    }


def _input_replicas(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("replicas"), list):
        return payload["replicas"]
    if isinstance(payload, dict):
        return [payload]
    raise ScorerInstrumentError("input must be a replica object/list or contain replicas[]")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        contract = load_fact_contract(args.contract)
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        replicas = _input_replicas(payload)
        result = (
            score_replica(replicas[0], contract)
            if len(replicas) == 1
            else score_run(replicas, contract)
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ScorerInstrumentError) as exc:
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": INSTRUMENT_ERROR,
            "decision": "HOLD_INSTRUMENT_ERROR",
            "reasons": [f"{type(exc).__name__}: {exc}"],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return {PASS: 0, REVIEW: 2, FAIL: 1, INSTRUMENT_ERROR: 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
