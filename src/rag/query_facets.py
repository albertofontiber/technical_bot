"""Deterministic query facets for document-scoped technical retrieval.

The expander is intentionally not wired into production retrieval yet. It is a
pure, auditable candidate generator whose vocabulary lives in versioned config.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/retrieval_facets_v1.yaml"

# s279 seccion 3 [SEAM-DELEGADO]: the validator is shared, so the schema
# whitelist is split by capability.  Every schema up to v4 is first-match ONLY
# (its consumers select exactly one archetype); the document-local v5 schema is
# the single one allowed to declare bounded multi-match, and it may only be
# consumed through the explicit ``multi_match=True`` mode below.
FIRST_MATCH_SCHEMAS = (
    "retrieval_facets_v1",
    "retrieval_facets_v2",
    "retrieval_facets_v3",
    "retrieval_facets_v4",
)
MULTI_MATCH_SCHEMA = "retrieval_facets_v5_document_local"
MULTI_MATCH_MAX = 2


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.casefold().split())


@lru_cache(maxsize=4)
def _load(path_string: str) -> dict:
    path = Path(path_string)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = payload.get("schema")
    if schema not in {*FIRST_MATCH_SCHEMAS, MULTI_MATCH_SCHEMA}:
        raise RuntimeError("unsupported retrieval facet schema")
    if payload.get("policy") != "first_match":
        raise RuntimeError("retrieval facet policy must be first_match")
    # Policy check conditioned by schema (s279 seccion 3): ``multi_match`` is
    # exclusive to the document-local v5 schema and its bound is pinned here,
    # never free in config.
    if schema == MULTI_MATCH_SCHEMA:
        multi_match = payload.get("multi_match")
        if (
            not isinstance(multi_match, dict)
            or multi_match.get("enabled") is not True
            or isinstance(multi_match.get("max"), bool)
            or not isinstance(multi_match.get("max"), int)
            or multi_match.get("max") != MULTI_MATCH_MAX
        ):
            raise RuntimeError(
                "document-local facet schema requires multi_match"
                " {enabled: true, max: 2}"
            )
    elif "multi_match" in payload:
        raise RuntimeError(
            "multi_match is exclusive to the document-local facet schema"
        )
    max_needs = payload.get("max_needs")
    if not isinstance(max_needs, int) or not 1 <= max_needs <= 4:
        raise RuntimeError("retrieval facet max_needs must be 1..4")
    ids = set()
    for archetype in payload.get("archetypes") or []:
        archetype_id = archetype.get("id")
        patterns = archetype.get("patterns")
        needs = archetype.get("needs")
        stem_prefixes = archetype.get("stem_prefixes") or []
        if not isinstance(archetype_id, str) or archetype_id in ids:
            raise RuntimeError("retrieval facet ids must be unique strings")
        if not isinstance(patterns, list) or not patterns:
            raise RuntimeError(f"retrieval facet {archetype_id} lacks patterns")
        if not isinstance(stem_prefixes, list) or any(
            not isinstance(stem, str)
            or not re.fullmatch(r"[a-záéíóúñü]{4,}", stem)
            or re.search(r"\d", stem)
            for stem in stem_prefixes
        ):
            raise RuntimeError(f"retrieval facet {archetype_id} has invalid stem prefixes")
        if not isinstance(needs, list) or not 1 <= len(needs) <= max_needs:
            raise RuntimeError(f"retrieval facet {archetype_id} has invalid needs")
        for pattern in patterns:
            re.compile(pattern)
        for template in needs:
            if not isinstance(template, str) or template.count("{query}") != 1:
                raise RuntimeError(f"retrieval facet {archetype_id} has invalid template")
            # The versioned ontology may add technical vocabulary, but never hidden
            # product codes or values. Numeric constraints must come from the query.
            if re.search(r"\d", template.replace("{query}", "")):
                raise RuntimeError(f"retrieval facet {archetype_id} injects numeric tokens")
        ids.add(archetype_id)
    return payload


def expand_query_facets(
    query: str, config_path: Path = DEFAULT_CONFIG, *, multi_match: bool = False
) -> dict:
    """Return the first matching archetype and up to three search needs.

    Default mode is first-match (byte-identical to every pre-v5 consumer).
    ``multi_match=True`` is the explicit document-local v5 mode (s279 seccion
    3): declaration order is preserved, the FIRST match stays the primary
    archetype, and at most ``multi_match.max`` archetypes contribute needs.
    Mode and schema must agree in both directions, so a first-match consumer
    can never silently load a multi-match config nor the reverse.
    """
    payload = _load(str(config_path.resolve()))
    config_multi_match = "multi_match" in payload
    if multi_match and not config_multi_match:
        raise RuntimeError("multi_match mode requires a multi_match facet schema")
    if config_multi_match and not multi_match:
        raise RuntimeError(
            "first_match consumers cannot load a multi_match facet schema"
        )
    normalized = _norm(query)
    tokens = re.findall(r"[a-záéíóúñü]+", normalized)
    cleaned = " ".join(query.strip(" ¿? ").split())
    matched: list[dict] = []
    for archetype in payload["archetypes"]:
        regex_match = any(re.search(pattern, normalized) for pattern in archetype["patterns"])
        stem_match = any(
            token.startswith(prefix)
            for token in tokens
            for prefix in archetype.get("stem_prefixes") or []
        )
        if not (regex_match or stem_match):
            continue
        matched.append(archetype)
        if not multi_match or len(matched) == payload["multi_match"]["max"]:
            break
    if not matched:
        plan = {"archetype": None, "needs": [cleaned]}
        if multi_match:
            plan["archetypes"] = []
        return plan
    needs = [
        " ".join(template.format(query=cleaned).split())
        for archetype in matched
        for template in archetype["needs"][: payload["max_needs"]]
    ]
    plan = {"archetype": matched[0]["id"], "needs": needs}
    if multi_match:
        plan["archetypes"] = [archetype["id"] for archetype in matched]
    return plan
