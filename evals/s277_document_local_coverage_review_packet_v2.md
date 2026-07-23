# S277 document-local coverage — adversarial review packet v2

## Objective and decision metric

Decide whether this default-off mechanism is safe enough to deploy as an
**unreleased candidate** and then rerun its 13-QID GET-only probe. It is not a
production release, does not authorize P1 and cannot change the current
146/154 fact KPI.

The mechanism passes this stage only if it:

1. recovers the HP011 source row without a QID, chunk-ID, page or gold-value
   rule;
2. preserves the protected prefix byte-for-byte and appends at most one row;
3. proves lifecycle authority over the complete document family, including
   disconnected revisions and chains longer than two;
4. obtains lifecycle rows and exact-blob FTS candidates from one PostgreSQL
   statement snapshot through a read-only GET RPC;
5. admits only a complete bounded Markdown pipe row with an exact receipt;
   formats whose record boundary cannot be proved must fail closed; and
6. leaves `coverage_c1_v1` import-isolated and rejects the new flag under that
   historical profile.

## Corrected architecture

`served validated structural neighbour → GET/STABLE atomic family+FTS snapshot
→ Python lineage revalidation → existing semantic selector → exact bounded
Markdown-row attestation → one append`.

- `DOCUMENT_LOCAL_COVERAGE` is strict `on|off`, defaults off and is outside C1.
- `public.document_local_snapshot_v1` is `LANGUAGE sql STABLE SECURITY INVOKER`,
  has an empty search path and is executable only by `service_role`. `PUBLIC`,
  `anon` and `authenticated` are revoked.
- PostgREST invokes the RPC through GET, so the request is read-only. Lifecycle
  and candidates are produced inside the same statement snapshot; there is no
  client-side lifecycle/chunk TOCTOU.
- The RPC reads the entire exact `(manufacturer, document_family, language)`
  family through a `family_limit+1` LATERAL sentinel, requires consistent
  `doc_type`/`product_model`, one active
  revision, only active/superseded statuses, one root, reciprocal pointers and
  a complete acyclic walk. It binds the active anchor to exact PDF SHA and
  source filename.
- The RPC returns the bounded family rows as part of its envelope. Python
  independently re-runs the lineage resolver and checks cardinalities,
  authority, scope partition, candidate identity and a hash of the immutable
  response before semantic selection.
- Up to two structural scopes are adjudicated independently in one RPC. An
  unsupported or invalid scope cannot suppress a separate valid ES scope.
- The physical `chunks_v2.search_vector` uses `spanish_unaccent`; therefore v1
  is explicitly ES-only. EN scopes fail closed and are reported, not queried.
- FTS is exact on active `document_id`, extraction SHA, source filename and
  `duplicate_of IS NULL`, with 64+1 evidence per scope and no retry. A noisy
  scope is discarded independently; two valid scopes may contribute up to 128
  candidates to the existing selector.
- Serving no longer claims generic logical-record recovery. The v1 contract is
  `markdown_pipe_row_v1`: all selector cards must intersect exactly one bounded
  data row; only its adjacent separator may also be touched. Prose, HTML,
  multiline, oversized or two-data-row spans are rejected.
- Explicit `logical_record_expansion=False` retains its override semantics;
  the default document-local view serves the separately receipted complete row.
- Runtime import remains lazy, preserving the sealed C1 v1 dependency closure.

## Evidence available before durable deployment

- The migration compiled and executed against the live schema inside an
  explicit transaction ending in `ROLLBACK`: schema/version valid, one HP011
  authority and its two complete family rows returned; no durable function,
  permission or data change remained.
- Focused implementation, serving, release-profile and SQL-contract tests:
  **96 passed**.
- Sealed C1 contract and scorer tests after the correction: **64 passed**.
- Tests include disconnected second active, a complete three-revision chain,
  family/candidate overflow, tampered envelope/scope receipts, ES+EN in both
  orders, EN-only, deadline/no-retry, separator-to-data HP011 shape, prose,
  HTML, oversized row, two data rows, tampered record bounds and explicit
  serving override.
- The earlier `s277_document_local_coverage_probe_v1.json` exercised the
  superseded multi-GET implementation and is not evidence for v2. The probe
  script has been migrated to the atomic RPC; its new live receipt is pending
  this review and durable installation of the reviewed migration bytes.

## Deliberate limitations / non-claims

- ES only. This candidate is not yet ES/EN-ready.
- Markdown single-row records only. Generic prose/multiline record boundaries
  require ingestion-time structural offsets and are not inferred at serving.
- The probe will replay sealed reranker prefixes; it will not rerun live
  retrieval, reranking, generation or fact judging.
- Lifecycle metadata availability limits organic reach and will be reported
  separately from selector reach. A no-append control does not prove that the
  semantic selector ran.
- No multi-turn/multi-hop state architecture is introduced here.
- The two-second HTTP deadline bounds client waiting but is not claimed as a
  PostgreSQL cancellation guarantee. Server work is structurally bounded by
  family and candidate sentinels; no wall-time guarantee is claimed.
- Durable installation is additionally blocked by TECH_DEBT #55 until the ten
  divergent migration-history versions are reconciled by evidence. Normal
  `db push`, `--include-all` and inferential `migration repair` remain forbidden.
- No new release profile or P1 authorization is included. Promotion requires a
  new profile; `coverage_c1_v1` remains immutable.

## Review focus

Re-check the prior Sol/Fable blockers: disconnected active revisions, complete
chains ≥3, statement-snapshot/TOCTOU guarantee, SQL/Python resolver divergence,
cross-scope suppression, ES-only framing, exact Markdown-record proof, RPC
permissions, target leakage, boundedness, hidden writes and C1 closure.
