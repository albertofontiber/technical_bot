"""Fail-closed extraction of structured numerical technical claims.

This is an unserved local prototype. It binds entity, attribute, comparison
operator, value or range, unit and qualifiers inside one source clause. For
Markdown tables it additionally binds the row, column and header. Unsupported
or ambiguous structures return no claims; they never authorize retrieval or
post-rerank coverage.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/structured_numeric_claims_v2.yaml"


@dataclass(frozen=True)
class NumericClaim:
    entity_id: str
    attribute: str
    operator: str
    value: str | None
    lower_value: str | None
    upper_value: str | None
    unit: str
    qualifiers: tuple[str, ...]
    clause: str
    start: int
    end: int
    source_kind: str
    binding: str
    header: str | None
    table_row: int | None
    table_column: int | None

    def canonical_tuple(self) -> tuple:
        return (
            _fold(self.entity_id),
            self.attribute,
            self.operator,
            self.value,
            self.lower_value,
            self.upper_value,
            self.unit,
            self.qualifiers,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fold(text: str) -> str:
    value = (text or "").replace("Âµ", "u").replace("Î¼", "u")
    value = value.replace("Î©", " omega ").replace("Ω", " omega ")
    value = value.replace("µ", "u").replace("μ", "u")
    value = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in value if not unicodedata.combining(char)
    ).casefold()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def _normalize_entity(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(text))


def _normalize_value(raw: str) -> str | None:
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None
    normalized = format(value.normalize(), "f")
    return "0" if normalized in {"-0", ""} else normalized


@lru_cache(maxsize=4)
def _load(path_string: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path_string).read_text(encoding="utf-8"))
    if payload.get("schema") != "structured_numeric_claims_v2":
        raise RuntimeError("unsupported structured claim schema")
    if not payload.get("attributes") or not payload.get("units"):
        raise RuntimeError("structured claim config is incomplete")
    if set(payload.get("supported_languages") or []) != {"es", "en"}:
        raise RuntimeError("structured claim language contract is incomplete")
    return payload


def _model_mentions(text: str) -> set[str]:
    mentions = set()
    for token in re.findall(
        r"\b(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)"
        r"[A-Za-z0-9-]{3,}\b",
        text,
    ):
        folded = _normalize_entity(token)
        # IEC-style resistor notation (for example 6K8) is a value, not a model.
        if re.fullmatch(r"\d+[kmr]\d+", folded):
            continue
        mentions.add(folded)
    return mentions


def _entity_safe(text: str, entity_id: str, *, require_mention: bool) -> bool:
    canonical_entity = _normalize_entity(entity_id)
    if not canonical_entity:
        return False
    mentions = _model_mentions(text)
    if require_mention and canonical_entity not in mentions:
        return False
    return not mentions or canonical_entity in mentions


def _attribute_matches(tokens: list[str], spec: dict[str, Any]) -> bool:
    return all(
        any(any(token.startswith(stem) for token in tokens) for stem in group)
        for group in spec["term_groups"]
    )


def _matching_attributes(text: str, payload: dict[str, Any]) -> list[str]:
    tokens = _tokens(text)
    return [
        attribute
        for attribute, spec in payload["attributes"].items()
        if _attribute_matches(tokens, spec)
    ]


def _phrase_present(text: str, phrase: str) -> bool:
    folded_phrase = _fold(phrase).strip()
    if not folded_phrase:
        return False
    pattern = re.escape(folded_phrase).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text))


def _operator(clause_folded: str, operators: dict[str, list[str]]) -> str | None:
    bounded_hits = [
        name
        for name in ("maximum", "minimum")
        if any(_phrase_present(clause_folded, phrase) for phrase in operators.get(name, []))
    ]
    if len(bounded_hits) == 1:
        return bounded_hits[0]
    if bounded_hits:
        return None
    return (
        "exact"
        if any(
            _phrase_present(clause_folded, phrase)
            for phrase in operators.get("exact", [])
        )
        else None
    )


def _unit_contract(payload: dict[str, Any]) -> tuple[dict[str, str], str]:
    alias_to_unit = {
        _fold(alias).strip(): unit
        for unit, aliases in payload["units"].items()
        for alias in aliases
    }
    alias_pattern = "|".join(
        re.escape(alias) for alias in sorted(alias_to_unit, key=len, reverse=True)
    )
    return alias_to_unit, alias_pattern


def _range_pattern(payload: dict[str, Any], alias_pattern: str) -> re.Pattern[str]:
    connectors = "|".join(
        re.escape(_fold(value).strip()).replace(r"\ ", r"\s+")
        for value in sorted(payload["range_connectors"], key=len, reverse=True)
    )
    number = r"\d+(?:[.,]\d+)?"
    return re.compile(
        rf"(?<![a-z0-9])(?P<lower>{number})\s*"
        rf"(?P<lower_unit>{alias_pattern})?\s*"
        rf"(?P<connector>{connectors})\s*"
        rf"(?P<upper>{number})\s*"
        rf"(?P<upper_unit>{alias_pattern})?(?![a-z0-9])"
    )


def _value_unit_pattern(alias_pattern: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![a-z0-9])(?P<value>\d+(?:[.,]\d+)?)\s*"
        rf"(?P<unit>{alias_pattern})(?![a-z0-9])"
    )


def _qualifiers(clause_folded: str, payload: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        name
        for name, phrases in payload.get("qualifiers", {}).items()
        if any(_phrase_present(clause_folded, phrase) for phrase in phrases)
    )


def _ambiguous_unbound_numbers(clause_folded: str, alias_pattern: str) -> bool:
    return bool(
        re.search(
            rf"\d+(?:[.,]\d+)?\s*(?:/|\bo\b|\bor\b)\s*"
            rf"\d+(?:[.,]\d+)?\s*(?:{alias_pattern})(?![a-z0-9])",
            clause_folded,
        )
    )


def _claims_from_semantic_clause(
    semantic_text: str,
    *,
    evidence_clause: str,
    entity_id: str,
    payload: dict[str, Any],
    start: int,
    end: int,
    source_kind: str,
    binding: str,
    header: str | None = None,
    table_row: int | None = None,
    table_column: int | None = None,
    require_entity_mention: bool = False,
) -> list[NumericClaim]:
    folded = _fold(semantic_text)
    if not _entity_safe(semantic_text, entity_id, require_mention=require_entity_mention):
        return []
    attributes = _matching_attributes(folded, payload)
    if not attributes:
        return []
    alias_to_unit, alias_pattern = _unit_contract(payload)
    qualifiers = _qualifiers(folded, payload)
    range_re = _range_pattern(payload, alias_pattern)
    range_matches = list(range_re.finditer(folded))
    claims: list[NumericClaim] = []

    if range_matches:
        if len(range_matches) != 1:
            return []
        match = range_matches[0]
        if not any(
            _phrase_present(folded, phrase)
            for phrase in payload["operators"].get("range", [])
        ):
            return []
        lower = _normalize_value(match.group("lower"))
        upper = _normalize_value(match.group("upper"))
        lower_unit = match.group("lower_unit")
        upper_unit = match.group("upper_unit")
        units = {
            alias_to_unit[_fold(raw).strip()]
            for raw in (lower_unit, upper_unit)
            if raw
        }
        if lower is None or upper is None or len(units) != 1:
            return []
        if Decimal(lower) > Decimal(upper):
            return []
        unit = next(iter(units))
        for attribute in attributes:
            if unit not in payload["attributes"][attribute]["units"]:
                continue
            claims.append(
                NumericClaim(
                    entity_id=entity_id,
                    attribute=attribute,
                    operator="range_inclusive",
                    value=None,
                    lower_value=lower,
                    upper_value=upper,
                    unit=unit,
                    qualifiers=qualifiers,
                    clause=evidence_clause,
                    start=start,
                    end=end,
                    source_kind=source_kind,
                    binding=binding,
                    header=header,
                    table_row=table_row,
                    table_column=table_column,
                )
            )
        return claims

    operator = _operator(folded, payload["operators"])
    if operator is None or _ambiguous_unbound_numbers(folded, alias_pattern):
        return []
    value_unit_re = _value_unit_pattern(alias_pattern)
    value_units = []
    for match in value_unit_re.finditer(folded):
        value = _normalize_value(match.group("value"))
        unit = alias_to_unit[_fold(match.group("unit")).strip()]
        if value is not None:
            value_units.append((value, unit))
    for attribute in attributes:
        compatible = [
            pair
            for pair in value_units
            if pair[1] in payload["attributes"][attribute]["units"]
        ]
        if len(compatible) != 1:
            continue
        claims.append(
            NumericClaim(
                entity_id=entity_id,
                attribute=attribute,
                operator=operator,
                value=compatible[0][0],
                lower_value=None,
                upper_value=None,
                unit=compatible[0][1],
                qualifiers=qualifiers,
                clause=evidence_clause,
                start=start,
                end=end,
                source_kind=source_kind,
                binding=binding,
                header=header,
                table_row=table_row,
                table_column=table_column,
            )
        )
    return claims


def _markdown_blocks(text: str) -> list[list[tuple[int, str]]]:
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        if raw.strip().startswith("|") and raw.count("|") >= 3:
            current.append((offset, raw))
        elif current:
            blocks.append(current)
            current = []
        offset += len(line)
    if current:
        blocks.append(current)
    return blocks


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _row_claims(
    cells: list[str],
    *,
    raw_row: str,
    row_start: int,
    row_index: int,
    entity_id: str,
    payload: dict[str, Any],
) -> list[NumericClaim]:
    attributes_by_cell = [_matching_attributes(cell, payload) for cell in cells]
    _alias_to_unit, alias_pattern = _unit_contract(payload)
    range_re = _range_pattern(payload, alias_pattern)
    range_cells = [
        index
        for index, cell in enumerate(cells)
        if range_re.search(_fold(cell))
        and any(
            _phrase_present(_fold(cell), phrase)
            for phrase in payload["operators"].get("range", [])
        )
    ]
    numeric_cells = [
        index
        for index, cell in enumerate(cells)
        if re.search(r"\d", cell) and any(
            _phrase_present(_fold(cell), alias)
            for aliases in payload["units"].values()
            for alias in aliases
        )
    ]
    attribute_cells = [index for index, values in enumerate(attributes_by_cell) if values]
    if len(attribute_cells) != 1:
        return []
    # A key/value row may describe an independent step size in the attribute
    # cell (for example "range 5..295 s" plus "5 s increments"). A unique
    # structurally marked range remains bound to its own cell; exact claims
    # still require exactly one numeric cell.
    if len(range_cells) == 1:
        numeric_index = range_cells[0]
    elif not range_cells and len(numeric_cells) == 1:
        numeric_index = numeric_cells[0]
    else:
        return []
    attribute_index = attribute_cells[0]
    semantic = (
        cells[numeric_index]
        if numeric_index == attribute_index
        else f"{cells[attribute_index]} {cells[numeric_index]}"
    )
    return _claims_from_semantic_clause(
        semantic,
        evidence_clause=raw_row,
        entity_id=entity_id,
        payload=payload,
        start=row_start,
        end=row_start + len(raw_row),
        source_kind="markdown_table",
        binding=f"table[row={row_index},key_value]",
        header=cells[attribute_index],
        table_row=row_index,
        table_column=numeric_index,
    )


def _table_claims(
    text: str,
    *,
    entity_id: str,
    payload: dict[str, Any],
) -> list[NumericClaim]:
    claims: list[NumericClaim] = []
    max_columns = int(payload["table"]["max_columns"])
    max_rows = int(payload["table"]["max_rows"])
    entity_headers = {_fold(value).strip() for value in payload["table"]["entity_headers"]}
    canonical_entity = _normalize_entity(entity_id)
    for block in _markdown_blocks(text):
        if len(block) < 2 or len(block) > max_rows:
            continue
        rows = [_cells(line) for _, line in block]
        widths = {len(row) for row in rows}
        if len(widths) != 1 or not widths or next(iter(widths)) > max_columns:
            continue
        separators = [index for index, row in enumerate(rows) if _separator_row(row)]
        if separators != [1]:
            continue
        headers = rows[0]
        header_is_data = any(re.search(r"\d", cell) for cell in headers)
        if header_is_data:
            claims.extend(
                _row_claims(
                    headers,
                    raw_row=block[0][1],
                    row_start=block[0][0],
                    row_index=0,
                    entity_id=entity_id,
                    payload=payload,
                )
            )
            data_rows = list(enumerate(rows[2:], start=2))
            for row_index, row in data_rows:
                claims.extend(
                    _row_claims(
                        row,
                        raw_row=block[row_index][1],
                        row_start=block[row_index][0],
                        row_index=row_index,
                        entity_id=entity_id,
                        payload=payload,
                    )
                )
            continue

        entity_columns = [
            index
            for index, header in enumerate(headers)
            if _fold(header).strip() in entity_headers
        ]
        if len(entity_columns) > 1:
            continue
        entity_column = entity_columns[0] if entity_columns else None
        for row_index, row in enumerate(rows[2:], start=2):
            if [_fold(cell).strip() for cell in row] == [
                _fold(cell).strip() for cell in headers
            ]:
                continue
            if entity_column is not None:
                if _normalize_entity(row[entity_column]) != canonical_entity:
                    continue
            for column_index, (header, cell) in enumerate(zip(headers, row)):
                if column_index == entity_column or not re.search(r"\d", cell):
                    continue
                semantic = f"{header} {cell}"
                raw_row = block[row_index][1]
                claims.extend(
                    _claims_from_semantic_clause(
                        semantic,
                        evidence_clause=raw_row,
                        entity_id=entity_id,
                        payload=payload,
                        start=block[row_index][0],
                        end=block[row_index][0] + len(raw_row),
                        source_kind="markdown_table",
                        binding=f"table[row={row_index},column={column_index}]",
                        header=header,
                        table_row=row_index,
                        table_column=column_index,
                    )
                )
    return claims


def _prose_claims(
    text: str,
    *,
    entity_id: str,
    payload: dict[str, Any],
    require_entity_mention: bool,
) -> list[NumericClaim]:
    folded_full = _fold(text)
    claims: list[NumericClaim] = []
    clause_spans: list[tuple[int, int]] = []
    clause_start = 0
    for index, char in enumerate(folded_full):
        decimal_point = (
            char == "."
            and index > 0
            and index + 1 < len(folded_full)
            and folded_full[index - 1].isdigit()
            and folded_full[index + 1].isdigit()
        )
        if char in {";", "\n"} or (char == "." and not decimal_point):
            clause_spans.append((clause_start, index))
            clause_start = index + 1
    clause_spans.append((clause_start, len(folded_full)))
    for raw_start, raw_end in clause_spans:
        raw_clause = folded_full[raw_start:raw_end]
        semantic = raw_clause.strip()
        if not semantic:
            continue
        start = raw_start + len(raw_clause) - len(raw_clause.lstrip())
        end = raw_end - len(raw_clause) + len(raw_clause.rstrip())
        claims.extend(
            _claims_from_semantic_clause(
                semantic,
                evidence_clause=text[start:end],
                entity_id=entity_id,
                payload=payload,
                start=start,
                end=end,
                source_kind="prose",
                binding="single_clause",
                require_entity_mention=require_entity_mention,
            )
        )
    return claims


def extract_numeric_claims(
    text: str,
    *,
    entity_id: str,
    config_path: Path = DEFAULT_CONFIG,
    require_entity_mention: bool = False,
) -> list[NumericClaim]:
    """Extract only structurally bound claims; reject unsupported ambiguity."""
    payload = _load(str(config_path.resolve()))
    if not text or not entity_id or "```mermaid" in text:
        return []
    blocks = _markdown_blocks(text)
    if blocks:
        return _table_claims(text, entity_id=entity_id, payload=payload)
    if re.search(r"</?(?:table|tr|td|th)\b", text, flags=re.IGNORECASE):
        return []
    return _prose_claims(
        text,
        entity_id=entity_id,
        payload=payload,
        require_entity_mention=require_entity_mention,
    )


def claim_supported(
    statement: str,
    source: str,
    *,
    entity_id: str,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Match an entity-explicit obligation to independent structured source claims."""
    statement_claims = extract_numeric_claims(
        statement,
        entity_id=entity_id,
        config_path=config_path,
        require_entity_mention=True,
    )
    source_claims = extract_numeric_claims(
        source,
        entity_id=entity_id,
        config_path=config_path,
    )
    matches = [
        (left, right)
        for left in statement_claims
        for right in source_claims
        if left.canonical_tuple() == right.canonical_tuple()
    ]
    return {
        "supported": len(statement_claims) == 1 and bool(matches),
        "statement_claims": [claim.to_dict() for claim in statement_claims],
        "source_claims": [claim.to_dict() for claim in source_claims],
        "matching_claims": len(matches),
        "contract": "entity_attribute_operator_value_or_range_unit_qualifiers_table_binding_v2",
    }
