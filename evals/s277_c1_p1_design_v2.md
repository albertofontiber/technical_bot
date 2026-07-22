# S277 C1 P1 v2 — additive release-integrity contract

This document is the normative delta over `s277_c1_p1_design_v1.md`. The fact
contract, 13-QID/27-replica population, 81-call plan, deterministic scorer,
WAL/no-retry semantics, provider models, physical token bounds and static
worst-case cost of USD 29.727 remain unchanged.

## Release identity

- Bootstrap: `COVERAGE_RELEASE_PROFILE=off`.
- Target: `COVERAGE_RELEASE_PROFILE=coverage_c1_v2`.
- The five profile-owned leaf variables, including
  `DOCUMENT_LOCAL_COVERAGE`, must be absent from the live Railway snapshot.
- v1 retains exactly its original four capabilities and document-local off.
- v2 enables those four capabilities plus document-local. The only coverage
  lanes permitted by the target contract are structural and document-local;
  `MUST_PRESERVE_CONTRACT=on` remains mandatory and
  `VISUAL_ASSETS_REGISTRY` remains an orthogonal preserved value.

## Document-local authority and physical boundary

The lane may run only after a served, validated structural anchor. It performs
at most one physical GET to
`/rest/v1/rpc/document_local_snapshot_v2`, never POST. Positive revision-family
membership is exact equality of a governed `revision_lineage_id`; legacy labels
may only reject a lineage for drift, never add or hide members. NULL or
unverified lineage, incomplete/branched lifecycle, non-reciprocal pointers,
multiple active rows, wrong active blob, per-scope overflow or combined pool
above 64 all fail closed.

The RPC is SQL, STABLE, SECURITY INVOKER and has an empty search path. Its live
`pg_get_functiondef` SHA-256 (LF) is
`19975e3784e0cd12176cbf0b246c4e0ee8a4eed008de7542d0c6d0b6c0f9a82e`.
`p1_readonly` receives EXECUTE plus SELECT on only the lineage-registry columns
`id` and `authority_status`; RLS exposes verified rows only. The HTTP guard
blocks direct registry access and all unexpected paths or methods.

## Per-replica attestation

Under v2 every replica must contain exactly one document-local lane trace.
`status=error` is terminal NO-GO. The trace's reported request count must match
the physical GET receipts one-for-one. For `hp011:r1` and `hp011:r2`, the
attestation additionally requires exactly one v2 GET, exactly one selected
chunk ID and that ID present in the served context. IDs and source text remain
inside the sealed private receipt; privacy-safe runtime telemetry persists only
lane, closed status and counts.

## Interpretation and stop lines

P1 starts as a new 27/27 run with a new preregistration hash, authorization,
artifact root, genesis, live receipts and fence window. The prior 18/27 run is
diagnostic only and cannot be resumed into this certification. A P1 PASS means
only `NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS`; it neither changes 146/154 nor
proves the ≥98% product KPI. Merge, deploy and canary remain separate decisions.
The confirmed legacy RLS/grant debt remains a final security-release blocker,
not a blocker to this bounded measurement.
