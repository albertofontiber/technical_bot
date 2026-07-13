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


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", text or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.casefold().split())


@lru_cache(maxsize=4)
def _load(path_string: str) -> dict:
    path = Path(path_string)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("schema") not in {
        "retrieval_facets_v1",
        "retrieval_facets_v2",
        "retrieval_facets_v3",
    }:
        raise RuntimeError("unsupported retrieval facet schema")
    if payload.get("policy") != "first_match":
        raise RuntimeError("retrieval facet policy must be first_match")
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


def expand_query_facets(query: str, config_path: Path = DEFAULT_CONFIG) -> dict:
    """Return the first matching archetype and up to three search needs."""
    payload = _load(str(config_path.resolve()))
    normalized = _norm(query)
    tokens = re.findall(r"[a-záéíóúñü]+", normalized)
    for archetype in payload["archetypes"]:
        regex_match = any(re.search(pattern, normalized) for pattern in archetype["patterns"])
        stem_match = any(
            token.startswith(prefix)
            for token in tokens
            for prefix in archetype.get("stem_prefixes") or []
        )
        if not (regex_match or stem_match):
            continue
        needs = [
            " ".join(template.format(query=query.strip(" ¿? ")).split())
            for template in archetype["needs"][: payload["max_needs"]]
        ]
        return {"archetype": archetype["id"], "needs": needs}
    return {"archetype": None, "needs": [" ".join(query.strip(" ¿? ").split())]}
