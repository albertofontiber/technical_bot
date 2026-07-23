# S277 document-local coverage — final adversarial review packet v3

## Objective and decision metric

Decide whether the default-off document-local mechanism has earned
`GO_MECHANISM`: safe enough to become an unreleased candidate for a later clean
27/27 P1. This review does not authorize a production profile, deploy, P1, or a
change to the current 146/154 fact KPI.

The mechanism passes only if it generically recovers HP011 without target
rules, preserves the served prefix byte-for-byte, appends at most one exact
source record, proves complete lifecycle authority from one statement
snapshot, remains GET-only/model-free/write-free, and stays excluded from the
sealed `coverage_c1_v1` profile.

## Terminal architecture

`served validated structural neighbour → GET/STABLE atomic family+FTS snapshot
→ Python lineage revalidation → existing semantic selector → exact bounded
Markdown-row attestation → one append`.

- `DOCUMENT_LOCAL_COVERAGE` is strict `on|off`, defaults off and is rejected by
  `coverage_c1_v1`. Its runtime import is lazy.
- `public.document_local_snapshot_v1` is `LANGUAGE sql STABLE SECURITY
  INVOKER`, has an empty search path, and is executable only by `service_role`.
  `PUBLIC`, `anon` and `authenticated` are revoked.
- Up to two anchor scopes are resolved in one PostgreSQL statement. Each exact
  `(manufacturer, document_family, language)` family is read with a
  `family_limit+1` LATERAL sentinel. SQL and Python independently require one
  active revision, one root, only active/superseded statuses, reciprocal
  pointers, a complete acyclic walk and exact active SHA/file binding.
- The active normalized document row is authoritative. Candidate membership is
  exact `document_id + extraction_sha256 + source_file + duplicate_of IS NULL`.
  Legacy denormalized chunk labels are not authority: HP011 legitimately has
  `chunks_v2.doc_type=NULL` and `product_model=RP1r-Supra` while `documents`
  has `usuario` and `RP1r`. The forward-only migration
  `20260721220110_s277_document_local_exact_blob_authority.sql` removes only
  those suppressive label comparisons; it does not weaken blob identity or
  lifecycle validation.
- Family and FTS response materialization are bounded per scope with `limit+1`
  sentinels. Overflow discards only the affected scope. There is one RPC, no
  retry, at most 128 selector candidates and one append.
- Version 1 is explicitly ES-only because the physical search vector uses
  `spanish_unaccent`. Unsupported languages fail closed.
- Serving admits only one provably complete bounded Markdown pipe data row.
  Prose, HTML, multiline, oversized and two-data-row spans fail closed.

## Live evidence on the reviewed path

- Migration history was reconciled without `migration repair` or
  `--include-all`: seven remote-only SQL bodies were recovered exactly from
  `supabase_migrations.schema_migrations.statements[1]`; three genuinely
  unapplied local SQL files were moved to `supabase/migration_proposals`.
  The two chunks-v3 files are disposable/HOLD contracts; `rag_trace` remains
  gated until P1 PASS.
- Supabase CLI 2.109.1 showed 11/11 historical versions aligned. The first
  dry-run listed only `20260721210847`; the second listed only
  `20260721220110`. Both were then applied normally and now appear in remote
  history.
- Durable catalogue verification reports the terminal RPC as `STABLE`,
  non-definer, empty-search-path, service-role executable, and non-executable
  by PUBLIC/anon/authenticated.
- Before each durable apply, the exact SQL compiled inside an explicit
  transaction ending in `ROLLBACK`. The terminal trial returned one HP011
  authority, two family rows, 49 bounded candidates and the target chunk.
- `evals/s277_document_local_coverage_probe_v1.json` is a fresh live receipt:
  `GO_MECHANISM`, all 17 checks true, 13 sealed QIDs, only HP011 selected,
  exact Markdown-row receipt, authoritative lifecycle, negative controls,
  unchanged prefixes, 82 total GETs across structural hydration plus the 13
  atomic RPCs, zero model calls and zero database writes.
- Terminal focused SQL/runtime/serving tests: 67 passed. The broader focused
  implementation suite passed 98 tests before the forward-only SQL correction;
  sealed C1 contract/scorer tests passed 64. Final regression is still required
  before commit.

## Deliberate limitations and separate risks

- The probe replays sealed reranker prefixes. It does not rerun retrieval,
  reranking, generation or fact judging, so it cannot change 146/154.
- `GO_MECHANISM` is not P1 PASS. A later clean 27/27 P1 is still required under
  a new release profile.
- The two-second HTTP deadline bounds client waiting; it is not a PostgreSQL
  cancellation guarantee. Returned/materialized rows are bounded, but no
  general wall-time bound is claimed for an underlying FTS scan. Larger corpora
  need plan/latency monitoring and potentially a supporting index.
- ES and single-row Markdown are the v1 applicability boundary. EN and generic
  record recovery need ingestion-time structural offsets, not serving-time
  guessing.
- No multi-turn or multi-hop conversation state architecture is introduced.
- Supabase security advisors still report legacy public tables and functions,
  including broad anon/auth privileges with RLS disabled on
  `chunks_v2_enunciados`. This predates and is not widened by the service-only
  RPC, but it blocks any claim of a global database-security GO and requires a
  separate forward-only hardening migration.

## Review focus

Re-check target leakage, exact-blob authority after removing denormalized label
comparisons, SQL/Python lifecycle equivalence, disconnected/long/ambiguous
families, cross-scope suppression, RPC ACLs, GET/read-only claims, boundedness,
Markdown record proof, C1 closure, migration-history claims, hidden writes and
whether `GO_MECHANISM` is framed more broadly than the evidence supports.
