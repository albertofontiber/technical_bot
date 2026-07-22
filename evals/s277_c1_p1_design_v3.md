# S277 C1 P1 v3 — governed document-source activation

This document is the normative delta over `s277_c1_p1_design_v2.md`. The fact
contract, 13-QID/27-replica population, 81-call plan, deterministic scorer,
WAL/no-retry semantics, provider models, physical token bounds, release profile
and static worst-case cost of USD 29.727 remain unchanged.

## Document-local activation authority

The first sentence of the v2 section "Document-local authority and physical
boundary" is superseded. The lane has two closed activation routes:

1. A governed source contract may activate the lane without a served structural
   anchor. The query must resolve through the canonical catalog to an exact
   `(document_id, source_file)` present in the versioned source-contract
   registry. The registry supplies an exact extraction SHA and document
   identity as a hint only. This route is exclusive when present, permits one
   or two deduplicated scopes, and fails closed before I/O on malformed,
   duplicate or overflowing input.
2. When no governed source contract resolves, the v2 fallback remains: a
   served, validated structural anchor is required. Protected-prefix exact-blob
   hints may supplement that fallback but cannot activate it alone.

Both routes retain the v2 physical boundary: at most one GET to
`/rest/v1/rpc/document_local_snapshot_v2`, never POST and never a model call or
database write. The live RPC remains the sole authority for verified lineage,
active revision, exact blob and returned chunks. A stale registry SHA or any
identity/lineage ambiguity therefore fails closed.

The governed registry is a bounded pilot source policy, not a QID lookup: it
contains no question, protected fact, target chunk, page or expected answer.
Its current evidence covers the RP1r governed source only. P1 cannot be used to
claim organic generalization or readiness of this registry for 30+ document
families; expansion requires a separately versioned selection/cardinality
policy.

## Sealed attestation

The v3 preregistration seals this document, the source-contract registry and
the catalog/runtime implementation manifest. A document-local GET records a
privacy-safe seed count, closed route histogram, scope hash and truncation
flag. For `hp011:r1` and `hp011:r2`, the paid gate additionally requires exactly
one `governed_source_contract` seed, no truncation, one physical GET and one
authoritative satisfied chunk present once in served context.

## Interpretation and stop lines

The next measurement starts as a new 27/27 run with a new v3 preregistration
hash, authorization, artifact root, genesis, live receipts and fence window.
All v2 attempts remain diagnostic and cannot be resumed into this
certification. A P1 PASS still means only
`NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS`; it does not change 146/154 or prove the
98% product KPI. Merge, deploy and canary remain separate decisions.
