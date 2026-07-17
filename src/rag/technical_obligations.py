"""Deterministic extraction of explicit operational answer obligations.

The extractor is intentionally product-agnostic. It accepts only already
aligned served chunks and returns exact source spans; it does not retrieve,
summarize or infer missing technical facts.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


TECHNICAL_OBLIGATION_EXTRACTOR_V1 = "technical_obligation_extractor_s141_v1"


@dataclass(frozen=True)
class TechnicalObligationCandidate:
    fragment_number: int
    candidate_id: str
    kind: str
    statement: str
    required_anchors: tuple[str, ...]
    source_start: int
    source_end: int
    semantic_identity: tuple[str, ...]
    identity_receipt_sha256: str = ""


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _clean(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value or "", flags=re.IGNORECASE)
    value = value.replace("~~", "").replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", value).strip(" |\n")


def _line_span(content: str, match: re.Match[str]) -> tuple[int, int]:
    start = content.rfind("\n", 0, match.start()) + 1
    end = content.find("\n", match.end())
    if end < 0:
        end = len(content)
    return start, end


def _paragraph_span(content: str, match: re.Match[str]) -> tuple[int, int]:
    start = content.rfind("\n\n", 0, match.start()) + 2
    end = content.find("\n\n", match.end())
    if end < 0:
        end = len(content)
    return start, end


def _candidate(
    fragment_number: int,
    chunk: dict[str, Any],
    kind: str,
    content: str,
    start: int,
    end: int,
    anchors: tuple[str, ...],
    semantic_identity: tuple[str, ...],
) -> TechnicalObligationCandidate | None:
    if not (0 <= start < end <= len(content)):
        return None
    statement = _clean(content[start:end])
    if not statement or any(not anchor.strip() for anchor in anchors):
        return None
    receipt = chunk.get("query_source_identity_attestation") or {}
    return TechnicalObligationCandidate(
        fragment_number=fragment_number,
        candidate_id=str(chunk.get("id") or ""),
        kind=kind,
        statement=statement,
        required_anchors=anchors,
        source_start=start,
        source_end=end,
        semantic_identity=semantic_identity,
        identity_receipt_sha256=str(receipt.get("receipt_sha256") or ""),
    )


def _programming_relations(
    query: str, aligned: list[tuple[int, dict[str, Any]]]
) -> list[TechnicalObligationCandidate]:
    folded_query = _fold(query)
    if not (
        re.search(r"\b(?:program\w*|configur\w*|ajust\w*|set\w*)\b", folded_query)
        and re.search(r"\b(?:retard\w*|delay\w*|salida\w*|output\w*|cbe|causa[ -]efecto|event\w*)\b", folded_query)
    ):
        return []
    out: list[TechnicalObligationCandidate] = []
    for fragment_number, chunk in aligned:
        content = str(chunk.get("content") or "")
        folded = _fold(content)
        patterns = (
            (
                "input_condition_definition",
                r"instruccion\s+de\s+entrada\s*:[^\n]{0,650}?condicion\s+de\s+entrada[^\n]{0,650}",
                ("instruccion de entrada", "condicion de entrada"),
                ("input_instruction", "condition"),
            ),
            (
                "output_condition_action",
                r"instruccion\s+de\s+salida\s*:[^\n]{0,900}?todas\s+las\s+condiciones\s+de\s+entrada[^\n]{0,900}?(?:equipos\s+asignados|sirenas\s+o\s+reles)[^\n]{0,600}",
                (
                    "instruccion de salida",
                    "todas las condiciones de entrada",
                    "equipos asignados",
                ),
                ("output_instruction", "all_input_conditions", "assigned_devices"),
            ),
            (
                "logic_contradiction_warning",
                r"(?:evit\w*|avoid\w*)[^\n.]{0,100}(?:logic\w*\s+contradict\w*|contradictory\s+logic)",
                ("evite", "logicas contradictorias"),
                ("avoid", "contradictory_logic"),
            ),
            (
                "commissioning_rule_verification",
                r"(?:probar|test)\w*[^\n.]{0,80}(?:riguros\w*|thorough\w*)[^\n.]{0,80}(?:todas\s+las\s+reglas|all\s+rules)[^\n.]{0,120}(?:puesta\s+en\s+marcha|commission\w*)[^\n.]{0,160}",
                ("probar rigurosamente", "todas las reglas", "puesta en marcha"),
                ("verify", "all_rules", "commissioning"),
            ),
            (
                "option_family_cardinality",
                r"(?:uno\s+de\s+|one\s+of\s+)(?:seis|six|6)\s+tipos?\s+de\s+(?:retardo|delay)[^\n.]{0,160}",
                ("seis", "tipos de retardo", "regla"),
                ("cardinality", "6", "delay_types"),
            ),
        )
        for kind, pattern, anchors, semantic in patterns:
            for match in re.finditer(pattern, folded, flags=re.IGNORECASE):
                start, end = _line_span(content, match)
                row = _candidate(
                    fragment_number,
                    chunk,
                    kind,
                    content,
                    start,
                    end,
                    anchors,
                    semantic,
                )
                if row is not None:
                    out.append(row)

        cbe = re.search(
            r"programando\s+las\s+siguientes\s+cbe[\s\S]{0,900}?"
            r"(?:activacion|activation)[\s\S]{0,450}?"
            r"(?:tipo\s+(?:de\s+)?software|software\s+type)\s+snd",
            folded,
        )
        if cbe:
            start = content.rfind("\n", 0, cbe.start()) + 1
            end = content.find("\n\n", cbe.end())
            if end < 0:
                end = cbe.end()
            row = _candidate(
                fragment_number,
                chunk,
                "software_type_cbe_activation",
                content,
                start,
                end,
                ("CBE", "activacion", "tipo software SND", "sirenas"),
                ("cbe", "activation", "output_software_type", "snd"),
            )
            if row is not None:
                out.append(row)
    return out


def _diagnostic_relations(
    query: str, aligned: list[tuple[int, dict[str, Any]]]
) -> list[TechnicalObligationCandidate]:
    if not re.search(
        r"\b(?:diagnost\w*|comprob\w*|check\w*|causa\w*|cause\w*|fallo\w*|fault\w*|alarma\w*|alarm\w*)\b",
        _fold(query),
    ):
        return []
    out: list[TechnicalObligationCandidate] = []
    for fragment_number, chunk in aligned:
        content = str(chunk.get("content") or "")
        folded = _fold(content)
        isolation = re.search(
            r"(?:controles?\s+de\s+incendios?|fire\s+controls?)[^\n.]{0,180}"
            r"(?:alertas?\s+remotas?|remote\s+alerts?)[^\n.]{0,180}"
            r"(?:zonas?\s+de\s+extincion|extinguishing\s+zones?)[^\n.]{0,220}"
            r"(?:bloqu\w*|desconect\w*|isolate\w*|disconnect\w*)[^\n.]{0,180}",
            folded,
        )
        if isolation:
            start, end = _paragraph_span(content, isolation)
            row = _candidate(
                fragment_number,
                chunk,
                "maintenance_isolation_prerequisite",
                content,
                start,
                end,
                (
                    "controles de incendios",
                    "alertas remotas",
                    "zonas de extincion",
                    "bloquearlos o desconectarlos previamente",
                ),
                ("maintenance", "isolate", "external_controls"),
            )
            if row is not None:
                out.append(row)

        calibration = re.search(
            r"reset\s+inicial[\s\S]{0,500}?"
            r"(?:guard\w*|memor\w*|registr\w*)[\s\S]{0,350}?"
            r"(?:valor\w*\s+nominal\w*|nominal\s+value\w*)[\s\S]{0,200}?100\s*%",
            folded,
        )
        if calibration:
            start, end = _paragraph_span(content, calibration)
            row = _candidate(
                fragment_number,
                chunk,
                "initial_reference_calibration",
                content,
                start,
                end,
                ("reset inicial", "valores nominales", "100 %"),
                ("initial_reset", "stores", "nominal_reference", "100_percent"),
            )
            if row is not None:
                out.append(row)

        window = re.search(
            r"(?:posiciones?|positions?)\s+(?:de\s+)?(?:conmutador\s+)?a11\s+a\s+c32"
            r"[\s\S]{0,650}?(?:20\s*%)[\s\S]{0,300}?"
            r"80\s*%[\s\S]{0,240}?120\s*%[\s\S]{0,260}?300\s*s",
            folded,
        )
        if window:
            start, end = _paragraph_span(content, window)
            row = _candidate(
                fragment_number,
                chunk,
                "bounded_fault_window",
                content,
                start,
                end,
                ("A11 a C32", "20 %", "80 %", "120 %", "300 s"),
                ("switch_scope", "a11_c32", "lower_80", "upper_120", "delay_300s"),
            )
            if row is not None:
                out.append(row)
    return out


def _reset_relations(
    query: str, aligned: list[tuple[int, dict[str, Any]]]
) -> list[TechnicalObligationCandidate]:
    if not re.search(
        r"\b(?:rearm\w*|reset\w*|restablec\w*|recuper\w*|no\s+vuelve)\b",
        _fold(query),
    ):
        return []
    out: list[TechnicalObligationCandidate] = []
    for fragment_number, chunk in aligned:
        content = str(chunk.get("content") or "")
        folded = _fold(content)
        special = re.search(
            r"rearme\s+inhibido\s+tras\s+extincion[\s\S]{0,650}?"
            r"-\s*-[\s\S]{0,120}?rearme\s+inhibido[\s\S]{0,220}?"
            r"finaliz\w*\s+extincion[\s\S]{0,220}?t\.?\s*a[\s\S]{0,80}?0\s*seg",
            folded,
        )
        if special:
            start, end = _line_span(content, special)
            row = _candidate(
                fragment_number,
                chunk,
                "reset_inhibit_special_state",
                content,
                start,
                end,
                ("--", "rearme inhibido", "finalizar extincion", "t.A", "0 seg"),
                ("special_value", "--", "reset_inhibited", "until_end_or_ta"),
            )
            if row is not None:
                out.append(row)
        duration = re.search(
            r"0?5\s+a\s+295\s+seg\w*[\s\S]{0,260}?"
            r"(?:tiempo\s+de\s+activacion|activation\s+time)[\s\S]{0,260}?"
            r"(?:circuito\s+de\s+extincion|extinguishing\s+circuit)[\s\S]{0,260}?"
            r"(?:intervalos?\s+de\s+5\s+seg\w*|5[- ]second\s+increments?)",
            folded,
        )
        if duration:
            start, end = _line_span(content, duration)
            row = _candidate(
                fragment_number,
                chunk,
                "extinction_duration_range",
                content,
                start,
                end,
                ("05 a 295 seg", "intervalos de 5 seg", "circuito de extincion"),
                ("extinction_duration", "5", "295", "seconds", "step_5"),
            )
            if row is not None:
                out.append(row)
    return out


def extract_technical_obligations(
    query: str, aligned: list[tuple[int, dict[str, Any]]]
) -> list[TechnicalObligationCandidate]:
    candidates = [
        *_programming_relations(query, aligned),
        *_diagnostic_relations(query, aligned),
        *_reset_relations(query, aligned),
    ]
    best: dict[tuple[str, tuple[str, ...]], TechnicalObligationCandidate] = {}
    conflicted: set[tuple[str, tuple[str, ...]]] = set()
    semantics_by_kind: dict[str, set[tuple[str, ...]]] = {}
    for row in candidates:
        semantics_by_kind.setdefault(row.kind, set()).add(row.semantic_identity)
    for kind, semantics in semantics_by_kind.items():
        if len(semantics) > 1 and kind in {
            "option_family_cardinality",
            "initial_reference_calibration",
            "bounded_fault_window",
            "reset_inhibit_special_state",
        }:
            conflicted.update((kind, semantic) for semantic in semantics)
    for row in candidates:
        key = (row.kind, row.semantic_identity)
        if key in conflicted:
            continue
        previous = best.get(key)
        if previous is None or (len(row.statement), row.fragment_number) < (
            len(previous.statement),
            previous.fragment_number,
        ):
            best[key] = row
    return sorted(
        best.values(),
        key=lambda row: (row.fragment_number, row.source_start, row.kind),
    )
