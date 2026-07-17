"""Query-bound catalog identity receipts for downstream source consumers.

Retrieval already resolves ambiguous model names through the governed catalog.
This module carries that decision to later stages without asking them to repeat
substring heuristics or silently trust a named sibling product.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


QUERY_SOURCE_IDENTITY_ATTESTATION_V1 = "query_source_identity_attestation_v1"


def _stable_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def query_sha256(query: str) -> str:
    return hashlib.sha256((query or "").encode("utf-8")).hexdigest()


def attach_query_source_identity(
    query: str,
    chunks: list[dict[str, Any]],
    resolution: Mapping[str, Any] | None,
    *,
    catalog_commit: str,
) -> list[dict[str, Any]]:
    """Attach an exact query/source receipt to unambiguous authorized sources.

    A source shared by two independently resolved query entities is deliberately
    left unattested. The ordinary retrieval result remains available; only the
    stronger downstream identity claim fails closed.
    """
    if not chunks or not resolution:
        return chunks
    records = {
        str(row.get("token") or ""): row
        for row in resolution.get("records", [])
        if row.get("expand") and row.get("ids") and row.get("token")
    }
    groups_by_source: dict[str, list[dict[str, Any]]] = {}
    for group in resolution.get("source_groups", []) or []:
        token = str(group.get("token") or "")
        record = records.get(token)
        if record is None or list(group.get("ids") or []) != list(record.get("ids") or []):
            continue
        for source in group.get("sources", []) or []:
            groups_by_source.setdefault(str(source), []).append(
                {
                    "token": token,
                    "via": str(record.get("via") or ""),
                    "policy": str(record.get("politica") or ""),
                    "resolved_ids": list(record.get("ids") or []),
                }
            )

    output: list[dict[str, Any]] = []
    for chunk in chunks:
        source_file = str(chunk.get("source_file") or "")
        matches = groups_by_source.get(source_file, [])
        if len(matches) != 1:
            output.append(chunk)
            continue
        binding = matches[0]
        body = {
            "schema": QUERY_SOURCE_IDENTITY_ATTESTATION_V1,
            "query_sha256": query_sha256(query),
            "source_file": source_file,
            "catalog_commit": str(catalog_commit or "unknown"),
            **binding,
        }
        receipt = {**body, "receipt_sha256": _stable_sha(body)}
        enriched = dict(chunk)
        enriched["query_source_identity_attestation"] = receipt
        output.append(enriched)
    return output


def validated_query_source_identity_sha256(
    query: str, chunk: Mapping[str, Any]
) -> str | None:
    receipt = chunk.get("query_source_identity_attestation")
    if not isinstance(receipt, Mapping):
        return None
    body = {
        "schema": receipt.get("schema"),
        "query_sha256": receipt.get("query_sha256"),
        "source_file": receipt.get("source_file"),
        "catalog_commit": receipt.get("catalog_commit"),
        "token": receipt.get("token"),
        "via": receipt.get("via"),
        "policy": receipt.get("policy"),
        "resolved_ids": receipt.get("resolved_ids"),
    }
    if (
        body["schema"] != QUERY_SOURCE_IDENTITY_ATTESTATION_V1
        or body["query_sha256"] != query_sha256(query)
        or body["source_file"] != str(chunk.get("source_file") or "")
        or not str(body["catalog_commit"] or "").strip()
        or not str(body["token"] or "").strip()
        or not str(body["via"] or "").strip()
        or not isinstance(body["resolved_ids"], list)
        or not body["resolved_ids"]
        or len(set(map(str, body["resolved_ids"]))) != len(body["resolved_ids"])
    ):
        return None
    expected = _stable_sha(body)
    return expected if receipt.get("receipt_sha256") == expected else None
