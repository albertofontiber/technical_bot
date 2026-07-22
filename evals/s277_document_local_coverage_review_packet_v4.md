# S277 document-local coverage — bounded confirmation packet v4

## Decision requested

Confirm or reject `GO_MECHANISM` for the default-off document-local recovery
lane. This is the one bounded confirmation round after resolving the findings
from v1-v3. It does not authorize a production profile, merge, deploy, P1, or a
change to the 146/154 fact KPI. Report only material blockers to that narrow
decision; product extensions such as EN, generic record parsing, multi-turn or
global database hardening are explicitly future work.

## Mechanism and authority boundary

`validated structural neighbour → one GET/STABLE atomic family+FTS snapshot →
Python lineage revalidation → catalogue-neutral semantic ranking inside the
exact document/blob → exact bounded Markdown-row attestation → at most one
append`.

- `DOCUMENT_LOCAL_COVERAGE` is strict `on|off`, defaults off, and remains
  excluded from sealed profile `coverage_c1_v1`.
- `public.document_local_snapshot_v1` is SQL, `STABLE`, `SECURITY INVOKER`,
  empty-search-path and service-role-only. PUBLIC/anon/authenticated cannot
  execute it.
- Up to two scopes are resolved in one statement snapshot. Family cardinality
  and FTS candidates use independent `limit+1` sentinels. SQL and Python require
  one active revision, one root, reciprocal pointers, a complete acyclic walk,
  allowed lifecycle states and exact active SHA/source-file binding.
- Candidate authority is the normalized active document plus exact
  `document_id + extraction_sha256 + source_file + duplicate_of IS NULL`.
  Before ranking, the active document overwrites and attests all five identity
  fields (`document_family`, `language`, `doc_type`, `manufacturer`,
  `product_model`); legacy denormalized chunk labels are deliberately not
  authority.
- The generic retrieval-pool selector still uses the governed catalogue in its
  original lane. This exact-document caller now passes
  `apply_catalog_scope=False`: historical catalogue preferences cannot suppress
  or favour a row after exact document/blob authority is established. A
  regression test replaces `resolve_query` with a forbidden callback and proves
  that this path never invokes it.
- Serving accepts a Markdown pipe data row only when the immediately preceding
  non-empty line is a valid separator row. Isolated pipe text, prose, HTML,
  multiline, oversized and two-data-row spans fail closed.
- Version 1 is ES-only because the physical vector is
  `spanish_unaccent`. Unsupported document languages fail closed independently.

## Durable and live evidence

- `evals/s277_document_local_migration_reconciliation_receipt_v1.json` records
  the evidence-based reconciliation: seven exact remote-only recoveries, three
  genuinely unapplied files moved to `migration_proposals`, 11/11 history
  alignment before forward work, two normal dry-run/apply sequences, no
  `migration repair`, no `--include-all`, and terminal RPC ACL/state.
- Both forward migrations are present in live history:
  `20260721210847_s277_document_local_snapshot_rpc.sql` and
  `20260721220110_s277_document_local_exact_blob_authority.sql`.
- Fresh receipt `evals/s277_document_local_coverage_probe_v1.json` reports
  `GO_MECHANISM` with 22/22 checks true over 13 sealed QIDs. Only HP011 selects
  one local row; the protected prefixes remain byte-equal; target chunk ID is
  absent from every request.
- The probe now hashes the complete 21-file imported production closure, the two
  integration surfaces and all seven YAML files actually read. It also hashes
  itself, both migrations and the migration reconciliation receipt. The
  anti-target scan covers all production source/config dependencies, not four
  hand-picked files.
- The governed/product catalogues remain unloaded throughout the probe after
  the exact-document bypass. Their eager code dependencies are still included
  in the manifest; target-aware catalogue data is not a runtime input to this
  lane.
- Python mutation controls cover ambiguous/disconnected/nonreciprocal
  lifecycle, SHA mismatch, duplicates, cross-blob/tampered/incomplete records
  and candidate overflow. Two additional GETs exercise the deployed RPC itself:
  all anchor SHAs are changed and rejected as
  `active_revision_not_bound_to_anchor_blob`; malformed `a&&b` is rejected as
  `invalid_request`.
- Remote cost evidence is not a hardcoded per-row counter. All mutating httpx
  verbs are replaced by fail-closed counting guards during the exercised path;
  zero attempts occurred. Every observed remote request is GET, and the sealed
  RPC function bodies are statically verified read-only. The complete runtime
  closure has no model-provider imports and execution stops before generation.
  Receipt: 84 GET, 0 model calls, 0 database writes, one declared local receipt
  write, 14.478 seconds.
- Current focused regressions: 110 runtime/SQL/serving/profile tests, 64 sealed
  C1 contract/scorer tests and 36 migration-proposal/runtime-evidence tests all
  pass. The full suite finished with 2,696 passed, 6 skipped and the same 10
  historical frozen-receipt/hash failures reproduced on the base commit; no new
  failure belongs to this mechanism. Those historical artefacts are not resealed.

## Narrow interpretation and residual risk

- This replays sealed reranker prefixes; it does not rerun retrieval, reranking,
  generation or fact judging. It cannot bank a fact or move 146/154.
- `GO_MECHANISM` means the lane may be included in a new versioned release
  profile candidate. It is not `P1_PASS`; the eventual release gate remains one
  fresh clean 27/27 run.
- `coverage_c1_v1` remains immutable. Integration must create a new profile
  (planned `coverage_c1_v2`) and re-seal its exact closure before P1.
- Returned material is bounded and the client deadline is two seconds; no
  general PostgreSQL scan-time guarantee is claimed. Latency/plan monitoring is
  required as the corpus grows.
- EN and non-Markdown logical records require ingestion-time structural
  metadata, not serving-time guessing. Multi-turn/multi-hop remains `NOT_BUILT`.
- Legacy RLS/grant findings, including `chunks_v2_enunciados`, are separate
  pre-existing security debt. They block a global database-security GO but were
  not introduced or widened by this service-only RPC and are not hidden by this
  mechanism verdict.

## Confirmation focus

Re-check only whether any material defect remains in exact-blob/lifecycle
authority, catalogue independence, SQL/Python negative controls, complete
runtime manifest, Markdown attestation, C1 isolation, hidden model/write paths
or the narrow `GO_MECHANISM` framing. Do not require P1, deployment, multi-turn,
EN support or global legacy-security remediation for this mechanism-only gate.
