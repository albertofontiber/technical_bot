# S195 — bounded author transport before a fresh cohort

## Decision

S195 repairs the upstream contract that invalidated S194. It does not retry S194,
does not reuse its 14 documents, and does not open the Luna planner or send protected
target questions/content to a model. The deterministic builder does read UUIDs from
frozen target artifacts solely to exclude overlapping documents/chunks; this is part of
the pre-existing freshness contract, not a target probe. A passing S195 only authorizes
a separate downstream S196 with S194's
90% recall, 80% precision and 75% complete-question thresholds unchanged.

## Root cause and provider boundary

The S194 prompt and deterministic validator required one to three unique
`support_unit_ids`, but the schema sent in `output_config.format.schema` left that
array unbounded. Anthropic structured outputs support array `minItems` only for 0 or
1 and explicitly do not support further array constraints. Therefore sending
`maxItems: 3` or `uniqueItems: true` would not be a valid provider contract.

S195 makes the boundary explicit:

1. The canonical domain schema retains `minItems: 1`, `maxItems: 3` and
   `uniqueItems: true`.
2. The Anthropic transport contains no arrays. Each answer point has exactly three
   support slots: one source-bound primary ID plus two nullable source-bound IDs.
3. All allowed IDs are a per-document enum frozen before authorship. The grammar
   therefore forbids unknown IDs and structurally caps support at three.
4. A deterministic adapter rejects duplicate IDs, non-contiguous answer-point slots,
   invalid eligibility shape and any canonical-schema violation, then reconstructs
   the canonical arrays and immutable support receipts.
5. Tests fail closed if unsupported array keywords or any transport array reappear.

Shape is necessary but not sufficient for gold quality. After the author population
passes, an independent economic OpenAI Luna call reviews all 14 items, including Haiku's
ineligible decisions. For eligible items it sees each claim, its cited IDs and the complete
source-unit set derived from the selected frozen chunk excerpt, so
it can detect cherry-picked support and omitted exceptions/bounds. It must mark the
eligibility decision correct, each claim fully supported by the cited IDs and the question
answerable as written. Zero incorrect exclusions, zero unsupported claims, zero unanswerable
questions and zero invalid validator outputs are required. The validator cannot edit
labels. This is cross-provider semantic validation, not frontier execution.

This is a reusable transport adapter, not a one-case prompt patch. The remaining
semantic author constraints stay deterministic where the provider dialect cannot
express them.

Official provider reference:
<https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations>

## Freshness and stopping rules

- Read `chunks_v2` by GET/HEAD only and freeze cardinality before/after.
- Use a new seed and item prefix.
- Exclude all prior packets plus every S194 document.
- Resolve UUID-bound protected target rows in the read-only snapshot, then also exclude
  exact `content_sha256` and `extraction_sha256` equivalents. This does not claim fuzzy,
  OEM or semantic duplicate detection; those remain outside the freshness guarantee.
  The contract fails if no protected UUID or no corresponding live target row resolves,
  and persists per-row ID/hash receipts for deterministic revalidation.
- Keep 14 manufacturers/documents with 7 table and 7 prose items.
- Haiku 4.5 is the only author model; Luna is the independent economic validator.
  Both use zero retries and there is zero frontier execution.
- The Anthropic SDK is constructed with `max_retries=0`; an `IN_PROGRESS` checkpoint
  is acquired with exclusive file creation before the first paid request, so a crash or
  concurrent process cannot silently authorize a replay. The OpenAI validator also uses
  `max_retries=0`, `store=False` and its own exclusive pre-paid checkpoint.
- The source packet itself is created with exclusive file creation; concurrent freezes
  cannot overwrite one another.
- Any invalid author output closes S195 as `NO_GO_COHORT_CONSTRUCTION`.
- API/transport dependency failure is `HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE`; a completed
  refusal or `max_tokens` response is a measured invalid author output and therefore
  `NO_GO_COHORT_CONSTRUCTION`. A provider 400 rejecting our request/schema is
  `NO_GO_EXECUTION_CONTRACT_REJECTED`, not HOLD. If an invalid output precedes a later
  provider interruption, NO-GO takes precedence. The same cohort is never retried.
- No runtime, database, production, deployment or official fact credit.
- Railway is not a gate.

The runner does not trust a self-describing YAML. It requires the exact preregistered
Haiku/Luna IDs and roles, token caps, 28 paid inference calls, up to 28 token-count
preflight requests (56 provider requests maximum), zero retries/frontier/database
calls, pricing, budget, validation thresholds, output paths, forbidden actions and the
complete frozen-artifact inventories. The execution permit has a separately exact
limits/artifact contract. Hashes are checked only after those inventories are fixed.

S195 passes only when every frozen population gate is true: at least 12 eligible
questions, 12 eligible manufacturers, 5 table questions, 5 prose questions and 24
answer points, with exactly zero invalid author outputs. The 90/80/75 planner metrics
belong to S196 and are not claimed by this upstream gate.

Scope limitation: each S195 item is deliberately one selected chunk excerpt and the source
selection is stratified by table/prose and manufacturer, not by language. S195 cannot
establish full-document, cross-chunk, ES/EN or multi-document generalization; Luna cannot
detect qualifiers outside the frozen excerpt. S196 conclusions must keep that scope unless
a separately frozen full-document/language/multi-document cohort is added.

## Explicit chunks_v3 lane

`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` remains unchanged. S195 neither reads nor writes
`chunks_v3`, performs no migration/materialization, and forbids per-question patching.
Only a new structural v4 hypothesis that improves ranking without manufacturer or
held-out loss can trigger reconsideration.

This lane uses its historical retrieval-ranking denominators (`recall@10` and MRR).
S196's 90/80/75 values measure planner claim recall, selected-unit precision and
complete-question rate on another denominator; they neither support nor overturn the
chunks_v3 wholesale decision.
