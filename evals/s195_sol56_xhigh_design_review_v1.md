# S195 — Sol 5.6 xhigh design review and adjudication

## Receipts

- `2026-07-17T14:25:00`: `gpt-5.6-sol`, `xhigh`, primary contract true,
  30 read-only tool calls, 153,949 tokens. The run completed and its tool trace was
  logged, but the detached local process lost final stdout. It is not adjudicable and
  is not counted as a favorable review.
- `2026-07-17T14:28:16`: bounded replay with the same model/effort and the four S195
  artifacts attached, using the documented `--no-tools` escape. It completed with
  16,834 tokens and produced seven readable findings.
- Fable 5 executor check: `fable` and `claude` commands absent; the available Codex
  binary does not expose a Fable pin in this environment. Status:
  `omitted_unavailable`; no substitute receipt is claimed.

## Rule-C adjudication of the readable review

1. **Target isolation — confirmed as framing, severity recalibrated to medium.** The
   builder reads UUIDs from frozen target artifacts to exclude overlaps, so the
   literal statement that targets are not opened was too broad. No target question or
   content is sent to an author/planner model. The design now says this explicitly.
2. **Prompt/transport contradiction — false positive.** `_author_prompt` contains
   identity, facets and evidence units; it does not request a field named
   `support_unit_ids`. The base system asks semantically for one-to-three source-unit
   IDs, which is compatible with slots. Even so, S195 now appends an explicit slot
   mapping to remove ambiguity without changing the labeling task.
3. **SDK retries and pre-paid checkpoint — confirmed critical.** Anthropic 0.97.0
   defaults to `max_retries=2`, and the first checkpoint was after the first paid call.
   Fixed with `Anthropic(..., max_retries=0)` plus a sealed `IN_PROGRESS_PRE_PAID_CALL`
   receipt before any `messages.create`.
4. **`max_tokens` classification — design ambiguity confirmed, behavior retained.** A
   completed/billed refusal or truncation is an invalid author output and closes the
   cohort as NO-GO under the no-retry rule. Only API/transport dependency failure is
   HOLD. The design now states the distinction.
5. **Validated cohort label on invalid outputs — confirmed medium.** Population checks
   now run before sealing; a failing cohort is labeled
   `SEALED_REJECTED_COHORT_CONSTRUCTION` and carries the checks.
6. **Missing S195 success thresholds in the design — confirmed medium.** The design now
   lists 12 eligible questions/manufacturers, 5 table, 5 prose, 24 answer points and
   zero invalid outputs, separating them from S196's 90/80/75 metrics.
7. **Packet self-certification — confirmed medium.** The runner now recomputes packet
   SHA, item/document/manufacturer counts, strata, IDs/prefix, prior document/source
   file/product-pair exclusion, S194 disjointness and target document/chunk exclusion.

Readable review tally: 7 findings, 6 confirmed or partially confirmed, 1 false
positive, maximum confirmed severity critical. All confirmed issues were addressed
before source freeze or paid Haiku execution.

## Follow-up review after the first fixes

Receipt `2026-07-17T14:33:50`: `gpt-5.6-sol`, `xhigh`, primary contract true,
bounded `--no-tools` review with the revised diff attached. Six findings were readable:

1. **API 400 / invalid-before-interruption precedence — confirmed critical.** Provider
   bad-request rejection is now `NO_GO_EXECUTION_CONTRACT_REJECTED`; an invalid output
   already persisted takes NO-GO precedence over a later external interruption.
2. **Semantic support of gold claims — confirmed critical.** Shape and ID receipts cannot
   prove entailment. S195 now preregisters an independent economic Luna validator over
   each claim and only its cited-unit text. All claims/questions must pass; the validator
   cannot edit labels and uses zero frontier execution calls.
3. **chunks_v3 denominator mismatch — false positive/orthogonal.** The wholesale kill is
   a historical retrieval-ranking decision. S196's 90/80/75 metrics are explicitly on
   another denominator and cannot support or overturn it; the design now spells this out.
4. **UUID-only target freshness — confirmed medium.** The builder now resolves protected
   UUID rows in the frozen snapshot and excludes exact content and extraction hashes.
   Fuzzy/OEM/semantic equivalents remain explicitly outside the guarantee.
5. **Language and multi-document scope — confirmed medium.** The design now limits S195
   to single-document, non-language-stratified evidence and forbids broad ES/EN or
   multi-document claims without another frozen cohort.
6. **Non-atomic check-then-write — confirmed medium.** Pre-paid checkpoints now use
   exclusive file creation; concurrent contenders fail before a paid call.

Follow-up tally: 6 findings, 5 confirmed, 1 false positive, maximum confirmed severity
critical. Relevant tests cover the semantic gate, exact point slots, exclusive checkpoint
and target-equivalence exclusion.

## Final design review after semantic validation was added

Receipt `2026-07-17T14:44:53`: `gpt-5.6-sol`, `xhigh`, primary contract true,
bounded `--no-tools` review with the complete revised diff attached. Five findings were
readable and all were confirmed:

1. **Self-declared prereg contract — confirmed critical.** The runner now requires exact
   model IDs/roles, token caps, 28-call maximum, zero retries/frontier/database calls,
   pricing, budget, validation gates, outputs, forbidden actions and fixed artifact
   inventories before checking their hashes. The permit has its own exact limits.
2. **Potentially vacuous target equivalence — confirmed medium.** The builder persists
   protected UUID count and per-row ID/content/extraction receipts. The runner requires
   non-empty UUIDs/resolved rows and reconstructs every hash set from those receipts.
3. **Semantic judge saw only author-selected evidence — confirmed medium.** Luna now sees
   all frozen units for the document plus the cited IDs, enabling it to reject omitted
   exceptions, warnings, bounds, prerequisites and product qualifiers.
4. **Source freeze check-then-write — confirmed medium.** The packet now uses exclusive
   creation, so concurrent builders cannot overwrite it.
5. **Known semantic failure lost to later HOLD — confirmed medium.** HOLD routing now
   inspects valid semantic reviews as well as validation errors; any known unsupported
   claim/question keeps NO-GO precedence if a later provider call is interrupted.

Final-design-review tally: 5 findings, 5 confirmed, 0 false positives, maximum severity
critical. All were fixed before source freeze or economic execution; 36 relevant tests
pass after the fixes.

## Closeout review

Receipt `2026-07-17T14:51:25`: `gpt-5.6-sol`, `xhigh`, primary contract true,
bounded `--no-tools` closeout over the design, adjudication, runner and tests. Five
findings were readable:

1. **“Complete document” scope — confirmed framing, recalibrated to medium.** Units are
   complete only for the selected frozen chunk excerpt, not the entire document. The
   contract is now `single_frozen_chunk_excerpt` and explicitly forbids full-document,
   cross-chunk or multi-document claims.
2. **Ineligible author items unreviewed — confirmed medium.** Luna now reviews all 14
   eligibility decisions. An ineligible label passes only when the excerpt cannot support
   two useful distinct answer points.
3. **Unauditable 400 classification — confirmed medium.** Contract NO-GO and external
   HOLD artifacts now persist a sanitized status code, request ID, error type/code and
   bounded message; no prompt or secret is persisted.
4. **“Haiku only execution model” — confirmed minor framing.** Corrected to sole author;
   Luna is the economic independent validator.
5. **“28 calls” ambiguity — confirmed minor framing.** The exact contract is 28 paid
   inference calls plus at most 28 token-count preflights: 56 provider requests maximum.

Closeout tally: 5 findings confirmed, 0 false positives, maximum adjudicated severity
medium after recalibrating the first from architectural failure to an over-claim of scope.
All were corrected before source freeze; the design is closed for S195 execution.
