"""S115 shadow-only exact coverage for explicit manual reference edges.

The selector is intentionally unreachable from runtime serving.  It resolves a
numbered reference to a strongly identified, contiguous section cluster and
serves only exact evidence atoms that add a query-bound signature.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/reference_edge_contract_v4.yaml"
LANE = "reference_edge_coverage_s115_shadow"
_HEX64 = re.compile(r"[0-9a-fA-F]{64}")
_NUMBERED_HEADING = re.compile(
    r"(?im)^[ \t]*#{1,6}[ \t]*(\d+(?:\.\d+)+)(?:[ \t]|$)"
)


@dataclass(frozen=True)
class ReferenceEdge:
    section: str
    subsection: str | None
    start: int
    end: int
    clause: str
    clause_start: int
    clause_end: int
    query_aligned: bool


@dataclass(frozen=True)
class Unit:
    start: int
    end: int
    quote: str


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if payload.get("schema") != "reference_edge_contract_v4":
        raise RuntimeError("unsupported reference-edge contract")
    limits = payload.get("limits") or {}
    required_limits = {
        "reference_clause_radius_chars": (40, 400),
        "heading_search_chars": (40, 400),
        "section_cluster_max_chunk_distance": (0, 4),
        "max_cards": (1, 2),
        "max_card_chars": (100, 720),
        "min_query_object_hits": (1, 4),
        "min_purpose_or_attribute_hits": (1, 4),
    }
    for key, (low, high) in required_limits.items():
        value = limits.get(key)
        if not isinstance(value, int) or not low <= value <= high:
            raise RuntimeError(f"invalid reference-edge limit: {key}")
    for section, keys in {
        "reference": ("pattern", "heading_pattern_template", "subsection_pattern_template"),
        "toc_rejection": ("dot_leader_pattern", "numbered_entry_pattern"),
        "intents": ("quantitative", "identity", "diagnostic", "procedure"),
        "signals": (
            "numeric_value_unit",
            "structured_code",
            "mapping_separator",
            "action",
            "diagnostic_relation",
        ),
    }.items():
        for key in keys:
            re.compile(str(payload[section][key]))
    return payload


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _distinctive_tokens(value: object) -> tuple[str, ...]:
    """The single byte-stable token normalizer required by the frozen design."""
    config = _contract()["normalization"]
    minimum = int(config["min_token_chars"])
    generic = set(config["generic_tokens"])
    prefixes = tuple(config["action_prefixes"])
    return tuple(
        dict.fromkeys(
            token
            for token in _fold(value).split()
            if len(token) >= minimum
            and token not in generic
            and not token.startswith(prefixes)
        )
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strong_identity(row: dict[str, Any]) -> tuple[str, str] | None:
    document_id = str(row.get("document_id") or "")
    extraction = str(row.get("extraction_sha256") or "")
    if not document_id or not _HEX64.fullmatch(extraction):
        return None
    return document_id, extraction.lower()


def _section_value(row: dict[str, Any]) -> str:
    return str(row.get("section_title") or row.get("section_path") or "")


def _section_key(row: dict[str, Any]) -> str:
    return _fold(_section_value(row))


def _chunk_index(row: dict[str, Any]) -> int | None:
    value = row.get("chunk_index")
    return value if isinstance(value, int) else None


def _reference_edges(query: str, row: dict[str, Any]) -> list[ReferenceEdge]:
    content = str(row.get("content") or "")
    pattern = re.compile(_contract()["reference"]["pattern"])
    radius = _contract()["limits"]["reference_clause_radius_chars"]
    edges = []
    for match in pattern.finditer(content):
        lower = max(0, match.start() - radius)
        upper = min(len(content), match.end() + radius)
        before = content[lower:match.start()]
        after = content[match.end():upper]
        before_delimiters = [before.rfind(char) for char in ("\n", ".", ";", "?", "!")]
        clause_start = lower + max(before_delimiters) + 1
        after_positions = [position for char in ("\n", ".", ";", "?", "!") if (position := after.find(char)) >= 0]
        clause_end = match.end() + (min(after_positions) + 1 if after_positions else len(after))
        clause = content[clause_start:clause_end].strip()
        query_aligned = bool(
            set(_distinctive_tokens(query)) & set(_distinctive_tokens(clause))
        )
        edges.append(
            ReferenceEdge(
                section=match.group(1),
                subsection=match.group(2),
                start=match.start(),
                end=match.end(),
                clause=clause,
                clause_start=clause_start,
                clause_end=clause_end,
                query_aligned=query_aligned,
            )
        )
    return edges


def _section_starts_with(row: dict[str, Any], section: str) -> bool:
    return bool(re.match(rf"^[ \t]*{re.escape(section)}(?:\D|$)", _section_value(row)))


def _heading_match(row: dict[str, Any], section: str) -> re.Match[str] | None:
    limit = _contract()["limits"]["heading_search_chars"]
    template = _contract()["reference"]["heading_pattern_template"]
    pattern = re.compile(template.replace("{section}", re.escape(section)))
    return pattern.search(str(row.get("content") or "")[:limit])


def _is_toc(row: dict[str, Any]) -> bool:
    content = str(row.get("content") or "")
    toc = _contract()["toc_rejection"]
    numbered = re.compile(toc["numbered_entry_pattern"])
    return len(numbered.findall(content)) >= int(toc["reject_when_numbered_entries_at_least"])


def _receipt(
    row: dict[str, Any], start: int, end: int, *, receipt_type: str, facet: str
) -> dict[str, Any]:
    content = str(row.get("content") or "")
    if not (0 <= start <= end <= len(content)):
        raise ValueError("invalid source span")
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
        "receipt_type": receipt_type,
    }


def verify_reference_edge_receipt(row: dict[str, Any], receipt: dict[str, Any]) -> bool:
    content = str(row.get("content") or "")
    identity = _strong_identity(row)
    start, end = receipt.get("start"), receipt.get("end")
    return bool(
        identity
        and str(row.get("id") or "")
        and isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= len(content)
        and receipt.get("receipt_type")
        in {"immutable_reference_evidence_span", "immutable_section_anchor_span"}
        and receipt.get("facet")
        == (
            "exact_reference_edge"
            if receipt.get("receipt_type") == "immutable_reference_evidence_span"
            else "section_anchor"
        )
        and str(row.get("id")) == receipt.get("candidate_id")
        and identity[0] == receipt.get("document_id")
        and identity[1] == str(receipt.get("extraction_sha256") or "").lower()
        and _sha256(content) == receipt.get("content_sha256")
        and content[start:end] == receipt.get("quote")
        and _sha256(content[start:end]) == receipt.get("quote_sha256")
    )


def _cluster_anchor(
    evidence: dict[str, Any], section: str, universe: list[dict[str, Any]]
) -> tuple[tuple[dict[str, Any], re.Match[str]] | None, str]:
    identity = _strong_identity(evidence)
    evidence_index = _chunk_index(evidence)
    if identity is None or evidence_index is None:
        return None, "no_strong_identity_or_chunk_index"
    key = _section_key(evidence)
    distance = _contract()["limits"]["section_cluster_max_chunk_distance"]
    cluster = [
        row
        for row in universe
        if _strong_identity(row) == identity
        and _section_key(row) == key
        and _chunk_index(row) is not None
        and abs(_chunk_index(row) - evidence_index) <= distance
    ]
    anchors = []
    toc_anchors = 0
    for row in cluster:
        heading = _heading_match(row, section)
        if heading:
            if _is_toc(row):
                toc_anchors += 1
            else:
                anchors.append((row, heading))
    if len(anchors) != 1:
        return None, "toc_anchor" if toc_anchors and not anchors else "no_unique_body_anchor"
    anchor, heading = anchors[0]
    anchor_index = _chunk_index(anchor)
    low, high = sorted((anchor_index, evidence_index))
    for row in universe:
        if _strong_identity(row) != identity:
            continue
        row_index = _chunk_index(row)
        if row_index is None or not low < row_index < high:
            continue
        for incompatible in _NUMBERED_HEADING.finditer(str(row.get("content") or "")):
            if incompatible.group(1) != section:
                return None, "incompatible_intervening_heading"
    return (anchor, heading), "resolved"


def _bounded_units(content: str, start: int, end: int) -> list[Unit]:
    maximum = _contract()["limits"]["max_card_chars"]
    segment = content[start:end]
    units: list[Unit] = []
    structural_patterns = (
        re.compile(r"(?m)^[ \t]*\|[^\n]+\|[ \t]*$"),
        re.compile(r"(?m)^[ \t]*(?:[-*•]|\d+[.)])[ \t]+[^\n]+$"),
    )
    seen: set[tuple[int, int]] = set()
    occupied: list[tuple[int, int]] = []

    def append_span(absolute_start: int, absolute_end: int) -> None:
        raw = content[absolute_start:absolute_end]
        leading = len(raw) - len(raw.lstrip("\r\n"))
        trailing = len(raw) - len(raw.rstrip("\r\n"))
        absolute_start += leading
        absolute_end -= trailing
        if absolute_start >= absolute_end:
            return
        spans = [(absolute_start, absolute_end)]
        if absolute_end - absolute_start > maximum:
            spans = []
            line_start = absolute_start
            block_start = absolute_start
            block_end = absolute_start
            for line in content[absolute_start:absolute_end].splitlines(keepends=True):
                line_end = line_start + len(line)
                if line_end - line_start > maximum:
                    if block_end > block_start:
                        spans.append((block_start, block_end))
                    block_start = block_end = line_end
                    line_start = line_end
                    continue
                if block_end > block_start and line_end - block_start > maximum:
                    spans.append((block_start, block_end))
                    block_start = line_start
                block_end = line_end
                line_start = line_end
            if block_end > block_start:
                spans.append((block_start, block_end))
        for unit_start, unit_end in spans:
            quote = content[unit_start:unit_end].rstrip("\r\n")
            unit_end = unit_start + len(quote)
            if (
                unit_start >= unit_end
                or (unit_start, unit_end) in seen
                or len(re.sub(r"\s+", "", quote)) < 40
                or len(quote) > maximum
            ):
                continue
            seen.add((unit_start, unit_end))
            units.append(Unit(unit_start, unit_end, quote))

    for pattern in structural_patterns:
        for match in pattern.finditer(segment):
            local_start, local_end = match.span()
            absolute = (start + local_start, start + local_end)
            occupied.append(absolute)
            append_span(*absolute)

    paragraph = re.compile(r"(?s)(?:^|\n\s*\n)([^\n].*?)(?=\n\s*\n|$)")
    for match in paragraph.finditer(segment):
        local_start, local_end = match.span(1)
        absolute = (start + local_start, start + local_end)
        if any(absolute[0] < high and low < absolute[1] for low, high in occupied):
            continue
        append_span(*absolute)
    return sorted(units, key=lambda unit: (unit.start, unit.end))


def _atomic_units(row: dict[str, Any], edge: ReferenceEdge) -> list[Unit]:
    content = str(row.get("content") or "")
    start = 0
    end = len(content)
    headings = list(_NUMBERED_HEADING.finditer(content))
    exact_headings = [match for match in headings if match.group(1) == edge.section]
    if exact_headings:
        start = exact_headings[0].end()
    for heading in headings:
        if heading.start() >= start and heading.group(1) != edge.section:
            end = heading.start()
            break
    if start >= end:
        return []
    if edge.subsection:
        template = _contract()["reference"]["subsection_pattern_template"]
        marker = re.compile(template.replace("{marker}", re.escape(edge.subsection)))
        match = marker.search(content, start, end)
        if not match:
            return []
        next_marker = re.search(
            r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?\([a-z0-9]+\)",
            content[match.end():end],
        )
        end = match.end() + next_marker.start() if next_marker else end
        return _bounded_units(content, match.start(), end)
    return _bounded_units(content, start, end)


def _intents(query: str) -> tuple[str, ...]:
    patterns = _contract()["intents"]
    return tuple(name for name, pattern in patterns.items() if re.search(pattern, query))


def _action_family(value: str) -> str:
    folded = _fold(value)
    families = (
        (("puls", "pres", "press"), "press"),
        (("selec", "select"), "select"),
        (("introdu", "enter"), "enter"),
        (("conect", "connect"), "connect"),
        (("configur", "configure"), "configure"),
        (("ajust", "adjust"), "adjust"),
        (("cambi", "change"), "change"),
        (("retir", "remove"), "remove"),
        (("reinstal", "reinstall"), "reinstall"),
        (("util", "use"), "use"),
    )
    for prefixes, family in families:
        if folded.startswith(prefixes):
            return family
    return folded


def _signals(unit: Unit, intents: tuple[str, ...]) -> list[tuple[str, str]]:
    config = _contract()["signals"]
    quote = unit.quote
    signals: list[tuple[str, str]] = []
    numeric = re.findall(config["numeric_value_unit"], quote)
    codes = re.findall(config["structured_code"], quote)
    mapping = bool(re.search(config["mapping_separator"], quote))
    actions = re.findall(config["action"], quote)
    diagnostic = re.findall(config["diagnostic_relation"], quote)
    table_cells = (
        [cell.strip() for cell in quote.strip().strip("|").split("|") if cell.strip()]
        if quote.strip().startswith("|") and quote.strip().endswith("|")
        else []
    )
    normalized_codes = sorted(set(code.upper() for code in codes))
    normalized_numeric = sorted(set(_fold(value) for value in numeric))
    descriptive_cells = [
        cell
        for cell in table_cells
        if _distinctive_tokens(cell)
        and not all(token.upper() in normalized_codes for token in cell.split())
    ]
    if "quantitative" in intents:
        signals.extend(("numeric", _fold(value)) for value in numeric)
    identity_pair = (mapping and len(normalized_codes) >= 2) or (
        len(table_cells) >= 2 and bool(normalized_codes) and bool(descriptive_cells)
    )
    if "identity" in intents and identity_pair:
        signals.append(("mapping", "|".join(normalized_codes)))
    if "diagnostic" in intents:
        diagnostic_table_pair = (
            len(table_cells) >= 2 and bool(normalized_codes) and bool(descriptive_cells)
        )
        if diagnostic_table_pair:
            signals.append(("diagnostic_mapping", "|".join(normalized_codes)))
        if diagnostic and (normalized_codes or normalized_numeric):
            observable = "|".join([*normalized_codes, *normalized_numeric])
            signals.extend(
                ("diagnostic_relation", f"{_fold(value)}|{observable}")
                for value in diagnostic
            )
    if "procedure" in intents:
        signals.extend(
            ("procedure_action", _action_family(value)) for value in actions
        )
        if len(table_cells) >= 2 and actions:
            signals.extend(("procedure_code", code) for code in normalized_codes)
            signals.extend(
                ("procedure_value", value) for value in normalized_numeric
            )
    return list(dict.fromkeys(signals))


def _atoms(
    unit: Unit,
    *,
    query_tokens: set[str],
    purpose_tokens: set[str],
    section_tokens: set[str],
    intents: tuple[str, ...],
) -> list[tuple[tuple[Any, ...], tuple[int, int, int, int]]]:
    unit_tokens = set(_distinctive_tokens(unit.quote))
    object_hits = sorted(query_tokens & unit_tokens)
    attribute_hits = sorted((purpose_tokens | section_tokens) & unit_tokens)
    limits = _contract()["limits"]
    identity_title_binding = "identity" in intents and bool(section_tokens & unit_tokens)
    if (
        len(object_hits) < limits["min_query_object_hits"]
        and not identity_title_binding
    ):
        return []
    if len(attribute_hits) < limits["min_purpose_or_attribute_hits"]:
        return []
    output = []
    for signal_kind, signal in _signals(unit, intents):
        intent = signal_kind.split("_", 1)[0]
        signature = (intent, signal_kind, signal)
        score = (1, len(object_hits), len(attribute_hits), 1)
        output.append((signature, score))
    return output


def _source_signatures(
    query: str, edge: ReferenceEdge, served: list[dict[str, Any]]
) -> set[tuple[Any, ...]]:
    query_tokens = set(_distinctive_tokens(query))
    purpose_tokens = query_tokens | set(_distinctive_tokens(edge.clause))
    intents = _intents(query)
    signatures = set()
    for row in served:
        for unit in _bounded_units(str(row.get("content") or ""), 0, len(str(row.get("content") or ""))):
            for signature, _ in _atoms(
                unit,
                query_tokens=query_tokens,
                purpose_tokens=purpose_tokens,
                section_tokens=set(),
                intents=intents,
            ):
                signatures.add(signature)
    return signatures


def _hydrate_served_provenance(
    served: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    """Hydrate only an exact ID/document/content twin; otherwise fail closed."""
    by_id = {str(row.get("id") or ""): row for row in candidates if row.get("id")}
    hydrated = []
    count = 0
    for seed in served:
        twin = by_id.get(str(seed.get("id") or ""))
        if (
            twin is not None
            and _strong_identity(twin) is not None
            and str(seed.get("document_id") or "") == str(twin.get("document_id") or "")
            and str(seed.get("content") or "") == str(twin.get("content") or "")
        ):
            hydrated.append(twin)
            count += int(_strong_identity(seed) is None)
        else:
            hydrated.append(seed)
    return hydrated, count


def select_reference_edge_coverage(
    query: str,
    served: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trace: dict[str, Any] = {
        "lane": LANE,
        "shadow_only": True,
        "input_candidates": len(candidates),
        "reference_edges": 0,
        "eligible_clusters": 0,
        "potential_reference_edges": 0,
        "terminal_reasons": {},
        "candidate_rejection_counts": {},
        "edge_traces": [],
        "potential_not_selected_edge_indexes": [],
        "selected_ids": [],
        "model_calls": 0,
        "database_writes": 0,
        "served_provenance_hydrated": 0,
    }
    if not query.strip() or not served:
        trace["reason"] = "empty_query_or_context"
        return [], trace
    canonical_served, hydrated_count = _hydrate_served_provenance(served, candidates)
    trace["served_provenance_hydrated"] = hydrated_count
    universe_by_id = {
        str(row.get("id") or f"anonymous-{index}"): row
        for index, row in enumerate([*canonical_served, *candidates])
    }
    universe = list(universe_by_id.values())
    served_ids = {str(row.get("id") or "") for row in served}
    scored_rows: list[
        tuple[int, tuple[int, int, int, int], dict[str, Any], int]
    ] = []

    def finish_trace() -> None:
        edge_traces = trace["edge_traces"]
        trace["potential_reference_edges"] = sum(
            bool(item["potential_candidate_ids"]) for item in edge_traces
        )
        trace["potential_not_selected_edge_indexes"] = [
            item["edge_index"]
            for item in edge_traces
            if item["potential_candidate_ids"] and item["terminal_reason"] != "selected"
        ]
        terminal: dict[str, int] = {}
        rejected: dict[str, int] = {}
        for item in edge_traces:
            reason = item["terminal_reason"]
            terminal[reason] = terminal.get(reason, 0) + 1
            for candidate in item["candidate_traces"]:
                candidate_reason = candidate["reason"]
                rejected[candidate_reason] = rejected.get(candidate_reason, 0) + 1
        trace["terminal_reasons"] = terminal
        trace["candidate_rejection_counts"] = rejected

    for source in canonical_served:
        edges = _reference_edges(query, source)
        trace["reference_edges"] += len(edges)
        for edge in edges:
            edge_index = len(trace["edge_traces"])
            edge_trace: dict[str, Any] = {
                "edge_index": edge_index,
                "source_id": str(source.get("id") or ""),
                "section": edge.section,
                "subsection": edge.subsection,
                "source_start": edge.start,
                "source_end": edge.end,
                "alignment_tier": "query_aligned" if edge.query_aligned else "generic",
                "potential_candidate_ids": [],
                "candidate_traces": [],
                "edge_winner_id": None,
                "edge_score": None,
                "terminal_reason": "unresolved",
            }
            trace["edge_traces"].append(edge_trace)
            source_signatures = _source_signatures(query, edge, canonical_served)
            edge_rows: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
            exact_rows = [
                row
                for row in candidates
                if str(row.get("id") or "") not in served_ids
                and _section_starts_with(row, edge.section)
            ]
            if not exact_rows:
                edge_trace["terminal_reason"] = "no_exact_section_candidate"
                continue
            for row in exact_rows:
                row_id = str(row.get("id") or "")
                if _strong_identity(row) != _strong_identity(source) or _strong_identity(row) is None:
                    edge_trace["candidate_traces"].append(
                        {"candidate_id": row_id, "reason": "strong_identity_mismatch"}
                    )
                    continue
                edge_trace["potential_candidate_ids"].append(row_id)
                resolved, cluster_reason = _cluster_anchor(row, edge.section, universe)
                if resolved is None:
                    edge_trace["candidate_traces"].append(
                        {"candidate_id": row_id, "reason": cluster_reason}
                    )
                    continue
                anchor, heading = resolved
                trace["eligible_clusters"] += 1
                query_tokens = set(_distinctive_tokens(query))
                purpose_tokens = set(_distinctive_tokens(edge.clause))
                section_tokens = set(_distinctive_tokens(_section_value(row)))
                if not edge.query_aligned and not (query_tokens & section_tokens):
                    edge_trace["candidate_traces"].append(
                        {
                            "candidate_id": row_id,
                            "reason": "generic_section_not_query_bound",
                        }
                    )
                    continue
                intents = _intents(query)
                ranked_units = []
                units = _atomic_units(row, edge)
                if not units:
                    edge_trace["candidate_traces"].append(
                        {"candidate_id": row_id, "reason": "no_bounded_atomic_unit"}
                    )
                    continue
                atom_count = 0
                novel_signatures: set[tuple[Any, ...]] = set()
                for unit in units:
                    atom_rows = _atoms(
                        unit,
                        query_tokens=query_tokens,
                        purpose_tokens=purpose_tokens,
                        section_tokens=section_tokens,
                        intents=intents,
                    )
                    atom_count += len(atom_rows)
                    novel = [item for item in atom_rows if item[0] not in source_signatures]
                    if not novel:
                        continue
                    base_score = max(score for _, score in novel)
                    best_score = (*base_score[:3], len({signature for signature, _ in novel}))
                    signatures = tuple(signature for signature, _ in novel)
                    novel_signatures.update(signatures)
                    ranked_units.append((best_score, unit, signatures))
                if not ranked_units:
                    edge_trace["candidate_traces"].append(
                        {
                            "candidate_id": row_id,
                            "reason": "no_novel_atom" if atom_count else "no_bound_contract_atom",
                        }
                    )
                    continue
                ranked_units.sort(key=lambda item: (tuple(-value for value in item[0]), item[1].start))
                cards = []
                seen_signals = set()
                for score, unit, signatures in ranked_units:
                    new_signals = {
                        (signature[1], signature[2]) for signature in signatures
                    } - seen_signals
                    if not new_signals:
                        continue
                    cards.append(
                        _receipt(
                            row,
                            unit.start,
                            unit.end,
                            receipt_type="immutable_reference_evidence_span",
                            facet="exact_reference_edge",
                        )
                    )
                    seen_signals.update(new_signals)
                    if len(cards) >= _contract()["limits"]["max_cards"]:
                        break
                if not cards:
                    edge_trace["candidate_traces"].append(
                        {"candidate_id": row_id, "reason": "no_distinct_card_signal"}
                    )
                    continue
                anchor_receipt = _receipt(
                    anchor,
                    heading.start(),
                    heading.end(),
                    receipt_type="immutable_section_anchor_span",
                    facet="section_anchor",
                )
                enriched = dict(row)
                enriched.update(
                    {
                        "retrieval_lane": LANE,
                        "reference_edge_rule_match": True,
                        "reference_edge_shadow_only": True,
                        "reference_edge": {
                            "section": edge.section,
                            "subsection": edge.subsection,
                            "source_start": edge.start,
                            "source_end": edge.end,
                            "source_clause": edge.clause,
                        },
                        "section_anchor_receipt": anchor_receipt,
                        "coverage_cards": cards,
                    }
                )
                row_score = (
                    1,
                    max(item[0][1] for item in ranked_units),
                    max(item[0][2] for item in ranked_units),
                    len(novel_signatures),
                )
                edge_trace["candidate_traces"].append(
                    {"candidate_id": row_id, "reason": "eligible_novel_evidence"}
                )
                edge_rows.append((row_score, enriched))
            if not edge_rows:
                if not edge_trace["potential_candidate_ids"]:
                    edge_trace["terminal_reason"] = "no_strong_identity_match"
                else:
                    reasons = {
                        item["reason"]
                        for item in edge_trace["candidate_traces"]
                        if item["candidate_id"] in edge_trace["potential_candidate_ids"]
                    }
                    edge_trace["terminal_reason"] = (
                        next(iter(reasons)) if len(reasons) == 1 else "no_selectable_candidate"
                    )
                continue
            top_score = max(score for score, _ in edge_rows)
            winners = [row for score, row in edge_rows if score == top_score]
            if len(winners) != 1:
                edge_trace["terminal_reason"] = "semantic_tie"
                continue
            edge_trace["edge_winner_id"] = str(winners[0].get("id") or "")
            edge_trace["edge_score"] = list(top_score)
            edge_trace["terminal_reason"] = "edge_winner"
            scored_rows.append((int(edge.query_aligned), top_score, winners[0], edge_index))

    if not scored_rows:
        finish_trace()
        trace["reason"] = "no_bound_novel_reference_evidence"
        return [], trace
    top_tier = max(tier for tier, _, _, _ in scored_rows)
    top_score = max(
        score for tier, score, _, _ in scored_rows if tier == top_tier
    )
    winners = [
        (row, edge_index)
        for tier, score, row, edge_index in scored_rows
        if tier == top_tier and score == top_score
    ]
    if len({str(row.get("id") or "") for row, _ in winners}) != 1:
        for _, edge_index in winners:
            trace["edge_traces"][edge_index]["terminal_reason"] = "global_semantic_tie"
        for _, _, _, edge_index in scored_rows:
            if trace["edge_traces"][edge_index]["terminal_reason"] == "edge_winner":
                trace["edge_traces"][edge_index]["terminal_reason"] = "superseded_by_higher_score"
        finish_trace()
        trace["reason"] = "semantic_tie"
        return [], trace
    selected = [winners[0][0]]
    selected_id = str(selected[0].get("id") or "")
    for tier, score, row, edge_index in scored_rows:
        trace["edge_traces"][edge_index]["terminal_reason"] = (
            "selected"
            if tier == top_tier
            and score == top_score
            and str(row.get("id") or "") == selected_id
            else "superseded_by_higher_score"
        )
    trace["selected_ids"] = [str(selected[0].get("id") or "")]
    trace["reason"] = "selected"
    finish_trace()
    return selected, trace
