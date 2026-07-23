#!/usr/bin/env python3
"""Explicit, zero-model, GET-only C1 reachability probe against live Supabase.

This complements (and is intentionally separate from) the offline assembly
gate. It proves that the current corpus and PostgREST permissions let the real
bounded neighbor fetcher and selector append hp017's warning-bearing chunk.
It does not call a generator and cannot authorize synthesis quality by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
FREEZE_SHA256 = "556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498"
TARGET_ID = "d27b1a1b-69cd-4318-a459-f3c86eb757ba"
PROBE_STATUS = "PASS_C1_LIVE_NEIGHBOR_FETCH_FROM_FROZEN_PREFIX_READ_ONLY"
MANIFEST_SCHEMA = "s277_c1_live_neighbor_fetch_runtime_manifest_v1"

# Exact repository inputs that can affect this probe's active structural-only
# path. Disabled coverage lanes are deliberately absent. Keeping this list
# explicit makes a historical receipt fail closed when selector, attestation,
# fetch, profile resolution, or one of their active configs changes.
EFFECTIVE_RUNTIME_INPUTS = (
    "scripts/s277_c1_live_reachability_probe.py",
    "src/config.py",
    "src/release_profiles.py",
    "src/rag/serving_pipeline.py",
    "src/rag/coverage_runtime.py",
    "src/rag/post_rerank_coverage.py",
    "src/rag/structural_neighbor_shadow.py",
    "src/rag/structural_neighbor_coverage.py",
    "src/rag/evidence_coverage.py",
    "src/rag/evidence_window.py",
    "src/rag/query_facets.py",
    "src/rag/structured_claims.py",
    "src/rag/toc_detection.py",
    "src/rag/mp_lexicon.py",
    "src/rag/catalog.py",
    "config/structural_neighbor_coverage_v1.yaml",
    "config/retrieval_facets_v3.yaml",
    "config/evidence_coverage_facets_v4.yaml",
    "config/evidence_coverage_facets_v2.yaml",
    "config/structured_numeric_claims_v2.yaml",
)


class ProbeFailure(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeFailure(message)


def _sha256_lf(path: Path) -> str:
    """Hash repository text with a platform-independent newline contract."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_implementation_manifest() -> dict[str, str]:
    """Return the exact active code/config authority for this execution."""
    manifest = {
        relative: _sha256_lf(ROOT / relative)
        for relative in EFFECTIVE_RUNTIME_INPUTS
    }
    _require(
        set(manifest) == set(EFFECTIVE_RUNTIME_INPUTS),
        "runtime implementation manifest is incomplete",
    )
    return manifest


def _configure_candidate_profile(env_file: Path | None = None) -> None:
    load_dotenv(env_file or (ROOT / ".env"), override=False)
    # The selected dotenv has already been read. Prevent src.config from
    # silently filling missing values from a different repository-root .env.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    for name in (
        "POST_RERANK_COVERAGE",
        "STRUCTURAL_NEIGHBOR_COVERAGE",
        "COVERAGE_MANDATORY_CALLOUT",
        "MP_MANDATORY_VERB_TRIGGER",
    ):
        os.environ.pop(name, None)
    os.environ["COVERAGE_RELEASE_PROFILE"] = "coverage_c1_v1"
    os.environ["MUST_PRESERVE_CONTRACT"] = "on"
    for name in (
        "TABLE_PREAMBLE_CLOSURE",
        "CANONICAL_HYQ_COVERAGE",
        "COMPATIBILITY_BUNDLE_COVERAGE",
        "RERANK_POOL_COVERAGE",
        "STRUCTURAL_CASCADE_COVERAGE",
        "LOGICAL_RECORD_COVERAGE",
        "EVIDENCE_DERIVATION_OVERLAY",
        "VISUAL_ASSETS_REGISTRY",
        "STRUCTURAL_NEIGHBOR_SHADOW",
        "MP_HYBRID_DETECT",
        "MP_SERVED_BINDING",
        "MP_DEFLINE_EQ",
        "MP_STEM_BINDING",
        "MP_DISTINCTIVE_TOKEN",
    ):
        os.environ[name] = "off"


class GetOnlyClient:
    """Expose only GET and count every real PostgREST request."""

    def __init__(self, client: httpx.Client):
        self._client = client
        self.get_requests = 0

    def get(self, *args, **kwargs):
        self.get_requests += 1
        return self._client.get(*args, **kwargs)


def _fetched_candidate_snapshot_sha(rows: list[dict[str, Any]]) -> str:
    bounded = []
    for row in rows:
        content = str(row.get("content") or "")
        bounded.append(
            {
                "id": str(row.get("id") or ""),
                "document_id": str(row.get("document_id") or ""),
                "extraction_sha256": str(row.get("extraction_sha256") or ""),
                "chunk_index": row.get("chunk_index"),
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    encoded = json.dumps(
        bounded, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_probe(*, env_file: Path | None = None) -> dict[str, object]:
    _configure_candidate_profile(env_file)

    from src import config
    from src.rag.post_rerank_coverage import (
        has_exact_mandatory_callout_receipt,
    )
    from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn
    from src.rag.structural_neighbor_coverage import DEFAULT_CONFIG
    from src.rag.structural_neighbor_shadow import fetch_structural_neighbor_rows

    config.validate_config(require_telegram=False, production=True)
    _require(
        config.COVERAGE_RELEASE_POLICY.profile == "coverage_c1_v1",
        "C1 candidate profile was not resolved",
    )

    raw_bytes = FREEZE.read_bytes()
    _require(
        hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()
        == FREEZE_SHA256,
        "sealed S113 context freeze drifted",
    )
    payload = json.loads(raw_bytes.decode("utf-8"))
    row = next(item for item in payload["rows"] if item["qid"] == "hp017")
    prefix = [dict(item) for item in row["context"][:10]]
    _require(len(prefix) == 10, "hp017 prefix is not ten rows")

    fetch_receipt: dict[str, Any] = {}
    generator_calls = 0
    with httpx.Client(timeout=3.0) as raw_client:
        guarded = GetOnlyClient(raw_client)

        def live_fetcher(seeds, **bounds):
            hydrated, candidates, read_trace = fetch_structural_neighbor_rows(
                seeds,
                client=guarded,
                **bounds,
            )
            fetch_receipt.update(
                {
                    "seed_rows": len(hydrated),
                    "fetched_candidate_rows": len(candidates),
                    "fetched_candidate_snapshot_sha256": (
                        _fetched_candidate_snapshot_sha(candidates)
                    ),
                    "reported_http_requests": read_trace.get("http_requests", 0),
                    "rows_read": read_trace.get("rows_read", 0),
                }
            )
            return hydrated, candidates, read_trace

        def no_model_generate(_query, _chunks, *, available_models=None):
            nonlocal generator_calls
            del available_models
            generator_calls += 1
            return {"answer": "", "diagrams": [], "probe_transport": "local_stub"}

        result = execute_rag_turn(
            query=row["question"],
            query_for_retrieval=row["question"],
            target_models=["Pearl"],
            available_models=None,
            retrieval_top_k=50,
            rerank_top_k=10,
            adapters=RagServingAdapters(
                retrieve=lambda _query, **_kwargs: list(prefix),
                rerank=lambda _query, chunks, **_kwargs: list(chunks[:10]),
                observe_structural_shadow=lambda _query, _chunks: None,
                generate=no_model_generate,
                structural_fetcher=live_fetcher,
            ),
        )

    served = result["chunks"]
    trace = result["coverage_trace"]
    target_positions = [
        index
        for index, chunk in enumerate(served, start=1)
        if chunk.get("id") == TARGET_ID
    ]
    _require(
        fetch_receipt.get("fetched_candidate_rows", 0) > len(prefix),
        "live fetch did not return rows beyond the frozen seeds",
    )
    _require(
        guarded.get_requests == fetch_receipt.get("reported_http_requests"),
        "HTTP request accounting mismatch",
    )
    _require(trace.get("status") == "appended", "live structural coverage did not append")
    _require(trace.get("protected_prefix_equal") is True, "live prefix receipt is false")
    _require(len(target_positions) == 1, "warning-bearing target was not appended exactly once")
    target = served[target_positions[0] - 1]
    _require(
        has_exact_mandatory_callout_receipt(target),
        "live target has no exact mandatory-callout receipt",
    )
    _require(generator_calls == 1, "local generation boundary was not invoked exactly once")

    return {
        "probe": PROBE_STATUS,
        "profile": config.COVERAGE_RELEASE_POLICY.profile,
        "authority": {
            "schema": MANIFEST_SCHEMA,
            "implementation_sha256_lf": build_implementation_manifest(),
            "source_freeze_sha256": FREEZE_SHA256,
            "selector_config_sha256": _sha256_lf(DEFAULT_CONFIG),
            "fetched_candidate_snapshot_sha256": fetch_receipt[
                "fetched_candidate_snapshot_sha256"
            ],
        },
        "seed_rows": fetch_receipt["seed_rows"],
        # This is the raw, pre-selector fetch set. It can include the ten seed
        # rows and must not be described as 110 eligible competitors.
        "fetched_candidate_rows": fetch_receipt["fetched_candidate_rows"],
        "rows_read": fetch_receipt["rows_read"],
        "served_rows": len(served),
        "target_fragment": target_positions[0],
        "target_callout_receipted": True,
        "http_get_requests": guarded.get_requests,
        "database_writes": 0,
        "paid_model_calls": 0,
        "uses_frozen_retrieval_prefix": True,
        "proves_live_retrieval": False,
        "proves_live_rerank": False,
        "proves_model_synthesis": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-live-read-only",
        action="store_true",
        help="Required acknowledgement that this performs bounded Supabase GETs.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional dotenv file; process environment remains authoritative.",
    )
    args = parser.parse_args()
    if not args.confirm_live_read_only:
        parser.error("--confirm-live-read-only is required")
    print(
        json.dumps(
            run_probe(env_file=args.env_file),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
