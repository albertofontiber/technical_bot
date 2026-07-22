"""Atomic release profiles for coupled RAG serving features.

The historical feature flags remain available in ``legacy`` mode so old offline
harnesses stay reproducible.  Production must use an explicit profile for the
C1 coverage chain; this prevents a leaf flag from being enabled while the
upstream selector that makes it reachable is still disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import os


PROFILE_ENV = "COVERAGE_RELEASE_PROFILE"
LEGACY_PROFILE = "legacy"
OFF_PROFILE = "off"
C1_PROFILE = "coverage_c1_v1"
C1_V2_PROFILE = "coverage_c1_v2"
SUPPORTED_PROFILES = (LEGACY_PROFILE, OFF_PROFILE, C1_PROFILE, C1_V2_PROFILE)

# Stable cross-module identity for the document-local lane. Keeping these
# strings in the release contract lets C1 v1 remain import-isolated while C1 v2
# activates the already-validated implementation as one atomic unit.
DOCUMENT_LOCAL_LANE = "document_local_content_coverage_v1"
DOCUMENT_LOCAL_VALIDATION = (
    "atomic_unique_active_family_fts_exact_markdown_pipe_row_v1"
)

# The original four switches are the C1 v1 unit; C1 v2 atomically adds the
# document-local lane. Outside legacy mode every leaf variable is forbidden:
# the selected profile is authoritative.
PROFILE_OWNED_FLAGS = (
    "POST_RERANK_COVERAGE",
    "STRUCTURAL_NEIGHBOR_COVERAGE",
    "COVERAGE_MANDATORY_CALLOUT",
    "MP_MANDATORY_VERB_TRIGGER",
    "DOCUMENT_LOCAL_COVERAGE",
)

_C1_V1_ENABLED_FLAGS = frozenset(PROFILE_OWNED_FLAGS[:4])
_C1_V2_ENABLED_FLAGS = frozenset(PROFILE_OWNED_FLAGS)

# Coverage lanes that share the post-rerank append seam.  C1 v1 intentionally
# isolates the structural lane until the wider stack has its own release gate.
COVERAGE_LANE_FLAGS = (
    "STRUCTURAL_NEIGHBOR_COVERAGE",
    "TABLE_PREAMBLE_CLOSURE",
    "CANONICAL_HYQ_COVERAGE",
    "COMPATIBILITY_BUNDLE_COVERAGE",
    "RERANK_POOL_COVERAGE",
    "DOCUMENT_LOCAL_COVERAGE",
    "STRUCTURAL_CASCADE_COVERAGE",
)
COVERAGE_MODIFIER_FLAGS = ("LOGICAL_RECORD_COVERAGE",)


def _strict_on_off(
    name: str,
    environ: Mapping[str, str],
    *,
    default: str = "off",
) -> bool:
    raw = str(environ.get(name, default)).strip().lower()
    if raw == "on":
        return True
    if raw == "off":
        return False
    raise RuntimeError(f"{name}={raw!r} is invalid; expected on|off")


@dataclass(frozen=True)
class CoverageReleasePolicy:
    """Resolved, immutable policy for the coupled C1 switches."""

    profile: str
    post_rerank_coverage: bool
    structural_neighbor_coverage: bool
    coverage_mandatory_callout: bool
    mp_mandatory_verb_trigger: bool
    document_local_coverage: bool
    legacy_overrides: tuple[str, ...] = ()

    def flag(self, name: str) -> bool:
        values = {
            "POST_RERANK_COVERAGE": self.post_rerank_coverage,
            "STRUCTURAL_NEIGHBOR_COVERAGE": self.structural_neighbor_coverage,
            "COVERAGE_MANDATORY_CALLOUT": self.coverage_mandatory_callout,
            "MP_MANDATORY_VERB_TRIGGER": self.mp_mandatory_verb_trigger,
            "DOCUMENT_LOCAL_COVERAGE": self.document_local_coverage,
        }
        try:
            return values[name]
        except KeyError as exc:
            raise KeyError(f"{name} is not owned by {PROFILE_ENV}") from exc

    def safe_snapshot(self) -> dict[str, object]:
        """Return a secret-free snapshot suitable for runtime telemetry."""
        return {
            "profile": self.profile,
            "post_rerank_coverage": self.post_rerank_coverage,
            "structural_neighbor_coverage": self.structural_neighbor_coverage,
            "coverage_mandatory_callout": self.coverage_mandatory_callout,
            "mp_mandatory_verb_trigger": self.mp_mandatory_verb_trigger,
            "document_local_coverage": self.document_local_coverage,
        }


def load_coverage_release_policy(
    environ: Mapping[str, str] | None = None,
) -> CoverageReleasePolicy:
    """Resolve the profile from one environment snapshot.

    ``legacy`` is the backwards-compatible default for offline tooling.  The
    production validator below rejects active C1 switches in that mode.
    """
    env = os.environ if environ is None else environ
    profile = str(env.get(PROFILE_ENV, LEGACY_PROFILE)).strip().lower()
    if profile not in SUPPORTED_PROFILES:
        allowed = "|".join(SUPPORTED_PROFILES)
        raise RuntimeError(f"{PROFILE_ENV}={profile!r} is invalid; expected {allowed}")

    legacy_overrides = tuple(name for name in PROFILE_OWNED_FLAGS if name in env)
    if profile == LEGACY_PROFILE:
        values = {name: _strict_on_off(name, env) for name in PROFILE_OWNED_FLAGS}
    else:
        enabled_flags = {
            OFF_PROFILE: frozenset(),
            C1_PROFILE: _C1_V1_ENABLED_FLAGS,
            C1_V2_PROFILE: _C1_V2_ENABLED_FLAGS,
        }[profile]
        values = {name: name in enabled_flags for name in PROFILE_OWNED_FLAGS}

    return CoverageReleasePolicy(
        profile=profile,
        post_rerank_coverage=values["POST_RERANK_COVERAGE"],
        structural_neighbor_coverage=values["STRUCTURAL_NEIGHBOR_COVERAGE"],
        coverage_mandatory_callout=values["COVERAGE_MANDATORY_CALLOUT"],
        mp_mandatory_verb_trigger=values["MP_MANDATORY_VERB_TRIGGER"],
        document_local_coverage=values["DOCUMENT_LOCAL_COVERAGE"],
        legacy_overrides=legacy_overrides,
    )


def validate_release_contract(
    policy: CoverageReleasePolicy,
    *,
    production: bool,
    must_preserve_enabled: bool,
    coverage_lanes: Mapping[str, bool],
) -> None:
    """Fail fast on partial, ambiguous, or historically unapproved releases."""
    errors: list[str] = []

    if policy.profile != LEGACY_PROFILE and policy.legacy_overrides:
        errors.append(
            f"{PROFILE_ENV} is authoritative; remove legacy overrides: "
            + ", ".join(policy.legacy_overrides)
        )

    effective_features = dict(coverage_lanes)
    effective_features["STRUCTURAL_NEIGHBOR_COVERAGE"] = (
        policy.structural_neighbor_coverage
    )
    effective_features["DOCUMENT_LOCAL_COVERAGE"] = policy.document_local_coverage
    active_lanes = sorted(
        name
        for name in COVERAGE_LANE_FLAGS
        if effective_features.get(name) is True
    )
    active_modifiers = sorted(
        name
        for name in COVERAGE_MODIFIER_FLAGS
        if effective_features.get(name) is True
    )

    if active_lanes and not policy.post_rerank_coverage:
        errors.append(
            "coverage lanes require POST_RERANK_COVERAGE: " + ", ".join(active_lanes)
        )
    if policy.post_rerank_coverage and not active_lanes:
        errors.append("POST_RERANK_COVERAGE requires at least one coverage lane")
    if active_modifiers and (
        not policy.post_rerank_coverage or not active_lanes
    ):
        errors.append(
            "coverage modifiers require the coverage master and an append lane: "
            + ", ".join(active_modifiers)
        )
    if effective_features.get("STRUCTURAL_CASCADE_COVERAGE") and not effective_features.get(
        "RERANK_POOL_COVERAGE"
    ):
        errors.append("STRUCTURAL_CASCADE_COVERAGE requires RERANK_POOL_COVERAGE")
    if effective_features.get("DOCUMENT_LOCAL_COVERAGE") and not effective_features.get(
        "STRUCTURAL_NEIGHBOR_COVERAGE"
    ):
        errors.append(
            "DOCUMENT_LOCAL_COVERAGE requires STRUCTURAL_NEIGHBOR_COVERAGE"
        )
    if policy.coverage_mandatory_callout and (
        not policy.post_rerank_coverage or not active_lanes
    ):
        errors.append(
            "COVERAGE_MANDATORY_CALLOUT requires the coverage master and a lane"
        )
    if policy.mp_mandatory_verb_trigger and not must_preserve_enabled:
        errors.append("MP_MANDATORY_VERB_TRIGGER requires MUST_PRESERVE_CONTRACT=on")

    if policy.profile in {C1_PROFILE, C1_V2_PROFILE}:
        expected_lanes = {"STRUCTURAL_NEIGHBOR_COVERAGE"}
        if policy.profile == C1_V2_PROFILE:
            expected_lanes.add("DOCUMENT_LOCAL_COVERAGE")
        unrelated = sorted(
            name
            for name, enabled in effective_features.items()
            if name not in expected_lanes and enabled
        )
        if unrelated:
            if policy.profile == C1_PROFILE:
                errors.append(
                    f"{C1_PROFILE} isolates structural coverage; disable: "
                    + ", ".join(unrelated)
                )
            else:
                errors.append(
                    f"{C1_V2_PROFILE} permits exactly "
                    + "+".join(sorted(expected_lanes))
                    + "; disable: "
                    + ", ".join(unrelated)
                )
        if not must_preserve_enabled:
            errors.append(
                f"{policy.profile} requires MUST_PRESERVE_CONTRACT=on"
            )

    if production and policy.profile == LEGACY_PROFILE:
        errors.append(
            "production requires an explicit COVERAGE_RELEASE_PROFILE "
            "(off, coverage_c1_v1, or coverage_c1_v2)"
        )

    if errors:
        raise RuntimeError("invalid RAG release contract: " + "; ".join(errors))
