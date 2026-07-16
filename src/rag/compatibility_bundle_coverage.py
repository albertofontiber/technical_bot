"""Fail-closed, relational evidence bundle for compatibility questions.

Three individually true excerpts do not by themselves establish that two
products interoperate.  This lane admits evidence only when it can bind an
official device roster and its protocol to one governed entity, and loop
topology to the other governed entity.  It never marks cross-manufacturer
interoperability as supported.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import catalog as catalog_text
from .catalog_resolver import resolve_query
from .doc_scoped_hyq_coverage import (
    fetch_document_scoped_rows,
    collect_document_scoped_hyq,
)
from .query_facets import expand_query_facets

ROOT = Path(__file__).resolve().parents[2]
QUERY_CONFIG = ROOT / "config" / "retrieval_facets_compatibility_candidate_v2.yaml"
EVIDENCE_CONFIG = ROOT / "config" / "evidence_coverage_compatibility_candidate_v1.yaml"
LANE = "canonical_compatibility_bundle_coverage_v1"
CONTRACT = "governed_two_entity_three_facet_bundle_v1"
REQUIRED_FACETS = frozenset(
    {"protocol_scope", "supported_device_roster", "loop_topology"}
)
ROLE_BY_FACET = {
    "protocol_scope": "queried_device",
    "supported_device_roster": "queried_device",
    "loop_topology": "host_system",
}
MAX_ROSTER_LINE_CHARS = 1400
MAX_ROSTER_WINDOW_CHARS = 360


def is_compatibility_bundle_query(query: str) -> bool:
    """Identify the narrow two-entity seam without exposing benchmark IDs."""
    plan = expand_query_facets(query, QUERY_CONFIG)
    groups = resolve_query(query).get("source_groups") or []
    return plan.get("archetype") == "compatibility" and len(groups) == 2


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_groups(groups: Any) -> list[dict[str, Any]]:
    if not isinstance(groups, list) or len(groups) != 2:
        raise ValueError("compatibility bundle requires exactly two governed entities")
    canonical = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("invalid source group")
        token = str(group.get("token") or "").strip()
        ids = sorted({str(value).strip() for value in group.get("ids") or [] if str(value).strip()})
        sources = sorted(
            {str(value).strip() for value in group.get("sources") or [] if str(value).strip()}
        )
        if not token or not ids or not sources:
            raise ValueError("incomplete source group")
        canonical.append({"token": token, "ids": ids, "sources": sources})
    canonical.sort(key=lambda row: (row["token"].casefold(), row["ids"], row["sources"]))
    if set(canonical[0]["sources"]) & set(canonical[1]["sources"]):
        raise ValueError("ambiguous source-group overlap")
    return canonical


def _manufacturers(groups: list[dict[str, Any]]) -> set[str]:
    return {
        product_id.split(":", 1)[0]
        for group in groups
        for product_id in group["ids"]
        if ":" in product_id
    }


def is_cross_manufacturer_compatibility_query(query: str) -> bool:
    """Recompute intent and manufacturer namespaces from governed catalog IDs."""
    if not is_compatibility_bundle_query(query):
        return False
    try:
        groups = _canonical_groups(resolve_query(query).get("source_groups") or [])
    except (TypeError, ValueError):
        return False
    return len(_manufacturers(groups)) >= 2


def _group_for_source(source_file: str, groups: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [group for group in groups if source_file in group["sources"]]
    if len(matches) != 1:
        raise ValueError("source does not map to exactly one governed entity")
    return matches[0]


def _token_is_present(token: str, text: str) -> bool:
    core = catalog_text._core(token)
    if not core:
        return False
    return bool(
        re.search(
            rf"\b(?:{core})(?![a-z0-9])",
            catalog_text._fold(text),
        )
    )


def _literal_token_match(token: str, text: str) -> re.Match[str] | None:
    parts = re.findall(r"[A-Za-z0-9]+", token)
    if not parts:
        return None
    pattern = r"(?<![A-Za-z0-9])" + r"[\s._/+-]*".join(
        re.escape(part) for part in parts
    ) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE)


def _augment_roster_entity_receipt(
    rows: list[dict[str, Any]], groups: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Bind a roster heading to the exact line naming the queried device.

    Generic evidence selection may correctly identify a compatibility-table
    heading while its bounded card stops before the relevant model row.  The
    governed entity token authorizes one additional exact line from the same
    immutable parent; no generated text or benchmark ID participates.
    """
    prepared = []
    for original in rows:
        row = dict(original)
        row["coverage_cards"] = [dict(card) for card in original.get("coverage_cards") or []]
        cards, facet = _validated_cards(row)
        if facet != "supported_device_roster":
            prepared.append(row)
            continue
        source, _, _, _ = _row_provenance(row)
        group = _group_for_source(source, groups)
        card_text = "\n".join(str(card["quote"]) for card in cards)
        if _token_is_present(group["token"], card_text):
            prepared.append(row)
            continue
        content = str(row["content"])
        match = _literal_token_match(group["token"], content)
        if match is None:
            prepared.append(row)
            continue
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_break = content.find("\n", match.end())
        line_end = len(content) if line_break < 0 else line_break
        if line_end - line_start > MAX_ROSTER_LINE_CHARS:
            line_start = max(0, match.start() - MAX_ROSTER_WINDOW_CHARS // 2)
            line_end = min(len(content), line_start + MAX_ROSTER_WINDOW_CHARS)
        row["coverage_cards"].append(
            {
                "candidate_id": str(row["id"]),
                "start": line_start,
                "end": line_end,
                "quote": content[line_start:line_end],
                "facet": "supported_device_roster",
                "exact_source_span_validated": True,
                "coverage_derivation": "governed_entity_exact_line_v1",
            }
        )
        prepared.append(row)
    return prepared


def _validated_cards(row: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    content = row.get("content")
    cards = row.get("coverage_cards")
    candidate_id = str(row.get("id") or "")
    if not candidate_id or not isinstance(content, str) or not content:
        raise ValueError("missing parent identity or content")
    if not isinstance(cards, list) or not cards:
        raise ValueError("empty evidence cards")
    facets = set()
    validated = []
    for card in cards:
        if not isinstance(card, dict) or card.get("exact_source_span_validated") is not True:
            raise ValueError("unvalidated evidence card")
        start, end, quote = card.get("start"), card.get("end"), card.get("quote")
        facet = str(card.get("facet") or "")
        if (
            str(card.get("candidate_id") or "") != candidate_id
            or isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or not isinstance(quote, str)
            or not 0 <= start < end <= len(content)
            or content[start:end] != quote
            or facet not in REQUIRED_FACETS
        ):
            raise ValueError("invalid exact evidence receipt")
        facets.add(facet)
        validated.append(card)
    if len(facets) != 1:
        raise ValueError("each bundle parent must attest exactly one required facet")
    return validated, next(iter(facets))


def _row_provenance(row: dict[str, Any]) -> tuple[str, str, str, int]:
    source = str(row.get("source_file") or "").strip()
    document_id = str(row.get("document_id") or "").strip()
    extraction = str(row.get("extraction_sha256") or "").strip()
    chunk_index = row.get("chunk_index")
    if (
        not source
        or not document_id
        or not re.fullmatch(r"[0-9a-f]{64}", extraction)
        or isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index < 0
    ):
        raise ValueError("incomplete immutable parent provenance")
    return source, document_id, extraction, chunk_index


def _relationship(
    rows: list[dict[str, Any]], groups: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("compatibility bundle requires exactly three parents")
    if len({str(row.get("id") or "") for row in rows}) != 3:
        raise ValueError("compatibility bundle parents must be distinct")
    by_facet: dict[str, dict[str, Any]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        cards, facet = _validated_cards(row)
        if facet in by_facet:
            raise ValueError("duplicate required facet")
        source, document_id, extraction, chunk_index = _row_provenance(row)
        group = _group_for_source(source, groups)
        by_facet[facet] = row
        metadata[facet] = {
            "cards": cards,
            "source_file": source,
            "document_id": document_id,
            "extraction_sha256": extraction,
            "chunk_index": chunk_index,
            "source_group": group,
        }
    if set(by_facet) != REQUIRED_FACETS:
        raise ValueError("missing required compatibility facet")

    roster = metadata["supported_device_roster"]
    roster_text = "\n".join(str(card["quote"]) for card in roster["cards"])
    if not _token_is_present(roster["source_group"]["token"], roster_text):
        raise ValueError("device roster does not name the queried governed entity")

    protocol = metadata["protocol_scope"]
    if (
        protocol["source_group"] != roster["source_group"]
        or protocol["document_id"] != roster["document_id"]
        or protocol["extraction_sha256"] != roster["extraction_sha256"]
    ):
        raise ValueError("protocol and roster are not bound to one governed document")

    topology = metadata["loop_topology"]
    if topology["source_group"] == roster["source_group"]:
        raise ValueError("host topology is not isolated from the queried device group")
    provenance_keys = {
        (
            details["document_id"],
            details["extraction_sha256"],
            details["chunk_index"],
        )
        for details in metadata.values()
    }
    if len(provenance_keys) != 3:
        raise ValueError("compatibility bundle parent provenance must be distinct")
    return metadata


def _bundle_payload(
    *,
    rows: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    query_sha256: str,
) -> dict[str, Any]:
    receipts = []
    for facet in sorted(REQUIRED_FACETS):
        row = next(
            candidate
            for candidate in rows
            if facet in {str(card.get("facet") or "") for card in candidate["coverage_cards"]}
        )
        details = metadata[facet]
        receipts.append(
            {
                "facet": facet,
                "role": ROLE_BY_FACET[facet],
                "chunk_id": str(row["id"]),
                "document_id": details["document_id"],
                "source_file": details["source_file"],
                "extraction_sha256": details["extraction_sha256"],
                "chunk_index": details["chunk_index"],
                "source_group": details["source_group"],
                "cards": [
                    {
                        "start": card["start"],
                        "end": card["end"],
                        "quote_sha256": hashlib.sha256(
                            card["quote"].encode("utf-8")
                        ).hexdigest(),
                    }
                    for card in details["cards"]
                ],
            }
        )
    return {
        "contract": CONTRACT,
        "query_sha256": query_sha256,
        "source_groups": groups,
        "rows": receipts,
    }


def build_compatibility_bundle(
    query: str,
    rows: list[dict[str, Any]],
    source_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return three mutually bound rows, or raise ``ValueError`` fail-closed."""
    groups = _canonical_groups(source_groups)
    rows = _augment_roster_entity_receipt(rows, groups)
    metadata = _relationship(rows, groups)
    query_sha256 = hashlib.sha256(query.encode("utf-8")).hexdigest()
    payload = _bundle_payload(
        rows=rows,
        groups=groups,
        metadata=metadata,
        query_sha256=query_sha256,
    )
    bundle_id = _canonical_sha256(payload)
    manufacturers = _manufacturers(groups)
    stamped = []
    for row in rows:
        _, facet = _validated_cards(row)
        details = metadata[facet]
        candidate = dict(row)
        candidate.update(
            {
                "retrieval_lane": LANE,
                "compatibility_bundle_validated": True,
                "local_semantic_validated": True,
                "compatibility_bundle_contract": CONTRACT,
                "compatibility_bundle_id": bundle_id,
                "compatibility_bundle_query_sha256": query_sha256,
                "compatibility_bundle_source_groups": groups,
                "compatibility_source_group": details["source_group"],
                "compatibility_entity_role": ROLE_BY_FACET[facet],
                "compatibility_facet": facet,
                "cross_manufacturer": len(manufacturers) >= 2,
                "direct_interoperability_supported": False,
            }
        )
        stamped.append(candidate)
    return stamped


def validate_compatibility_bundle(rows: list[dict[str, Any]]) -> bool:
    """Recompute all relational and immutable receipts at the serving seam."""
    try:
        if len(rows) != 3:
            return False
        bundle_ids = {str(row.get("compatibility_bundle_id") or "") for row in rows}
        query_hashes = {
            str(row.get("compatibility_bundle_query_sha256") or "") for row in rows
        }
        group_payloads = {
            json.dumps(
                row.get("compatibility_bundle_source_groups"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for row in rows
        }
        if (
            len(bundle_ids) != 1
            or "" in bundle_ids
            or len(query_hashes) != 1
            or not re.fullmatch(r"[0-9a-f]{64}", next(iter(query_hashes)))
            or len(group_payloads) != 1
            or any(row.get("compatibility_bundle_validated") is not True for row in rows)
            or any(row.get("direct_interoperability_supported") is not False for row in rows)
        ):
            return False
        groups = _canonical_groups(rows[0]["compatibility_bundle_source_groups"])
        cross_manufacturer = len(_manufacturers(groups)) >= 2
        metadata = _relationship(rows, groups)
        expected = _canonical_sha256(
            _bundle_payload(
                rows=rows,
                groups=groups,
                metadata=metadata,
                query_sha256=next(iter(query_hashes)),
            )
        )
        if expected != next(iter(bundle_ids)):
            return False
        for row in rows:
            _, facet = _validated_cards(row)
            if (
                row.get("compatibility_bundle_contract") != CONTRACT
                or row.get("compatibility_facet") != facet
                or row.get("compatibility_entity_role") != ROLE_BY_FACET[facet]
                or row.get("compatibility_source_group") != metadata[facet]["source_group"]
                or row.get("cross_manufacturer") is not cross_manufacturer
            ):
                return False
        return True
    except (KeyError, StopIteration, TypeError, ValueError):
        return False


def collect_compatibility_bundle(
    query: str,
    *,
    fetcher=fetch_document_scoped_rows,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Navigate with HYQ, then release only a complete relational bundle."""
    resolution = resolve_query(query)
    source_groups = resolution.get("source_groups") or []
    selected, navigation_trace = collect_document_scoped_hyq(
        query,
        fetcher=fetcher,
        query_facets_path=QUERY_CONFIG,
        evidence_config_path=EVIDENCE_CONFIG,
        append_limit=3,
        entity_stratified=True,
        include_fetch_receipts=True,
    )
    trace = dict(navigation_trace)
    trace.update(
        {
            "lane": LANE,
            "navigation_lane": navigation_trace.get("lane"),
            "required_facets": sorted(REQUIRED_FACETS),
            "relational_contract": CONTRACT,
        }
    )
    try:
        bundle = build_compatibility_bundle(query, selected, source_groups)
    except (KeyError, TypeError, ValueError) as exc:
        trace.update(
            {
                "status": "no_complete_relational_bundle",
                "selected_parent_ids": [],
                "relational_rejection": str(exc),
            }
        )
        return [], trace
    trace.update(
        {
            "status": "selected_complete_relational_bundle",
            "selected_parent_ids": [str(row["id"]) for row in bundle],
            "compatibility_bundle_id": bundle[0]["compatibility_bundle_id"],
            "direct_interoperability_supported": False,
        }
    )
    return bundle, trace


def complete_compatibility_bundle(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find one complete, revalidated bundle in chunks; ambiguity returns none."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in chunks:
        if row.get("retrieval_lane") != LANE:
            continue
        bundle_id = str(row.get("compatibility_bundle_id") or "")
        grouped.setdefault(bundle_id, []).append(row)
    valid = [rows for bundle_id, rows in grouped.items() if bundle_id and validate_compatibility_bundle(rows)]
    return valid[0] if len(valid) == 1 else []


def render_cross_manufacturer_compatibility_refusal(
    chunks: list[dict[str, Any]],
) -> str | None:
    """Render a source-bound refusal when no direct cross-brand proof exists."""
    bundle = complete_compatibility_bundle(chunks)
    if not bundle:
        return None
    try:
        groups = _canonical_groups(bundle[0]["compatibility_bundle_source_groups"])
    except (KeyError, TypeError, ValueError):
        return None
    if len(_manufacturers(groups)) < 2:
        return None
    by_facet = {str(row["compatibility_facet"]): row for row in bundle}
    labels = {
        "loop_topology": "Topología documentada del sistema anfitrión",
        "protocol_scope": "Protocolo documentado del dispositivo",
        "supported_device_roster": "Listado oficial que identifica el dispositivo",
    }
    lines = [
        "No puedo confirmar la compatibilidad directa entre estos equipos: los manuales recuperados no documentan interoperabilidad entre ambos fabricantes.",
        "",
    ]
    for facet in ("loop_topology", "protocol_scope", "supported_device_roster"):
        row = by_facet[facet]
        quotes = " ".join(
            " ".join(str(card["quote"]).split()) for card in row["coverage_cards"]
        )
        lines.append(f"- {labels[facet]}: {quotes}")
    sources = []
    for row in bundle:
        source = str(row.get("source_file") or "")
        if source and source not in sources:
            sources.append(source)
    lines.extend(
        [
            "",
            "Estas especificaciones deben tratarse por separado; no prueban por sí solas que un equipo pueda montarse en el lazo del otro. Verifica la combinación con ambos fabricantes.",
            f"Fuentes: {'; '.join(sources)}",
        ]
    )
    return "\n".join(lines)


def render_incomplete_cross_manufacturer_compatibility_guard() -> str:
    """Safe fallback when the active lane cannot build a complete bundle."""
    return (
        "No puedo confirmar la compatibilidad entre estos equipos: no dispongo de un "
        "conjunto documental completo y vinculado que demuestre interoperabilidad entre "
        "ambos fabricantes. No los conectes basándote solo en similitudes parciales de "
        "protocolo o cableado; verifica la combinación con ambos fabricantes."
    )
