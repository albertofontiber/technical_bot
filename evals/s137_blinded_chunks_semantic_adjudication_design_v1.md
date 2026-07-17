# S137 — blinded semantic adjudication of the three S135 chunk losses

Status: design frozen before runner implementation or model execution.

## Objective

Decide whether the three frozen S135 top-10 losses are real retrieval regressions
of `candidate_v3`, or whether the exact-gold proxy under-credits other
answer-bearing evidence and/or requires an unnecessarily large gold bundle.

This probe does not tune the chunker, retrieval query, ranks, thresholds, golds,
or facts. It only adjudicates the relevance of an already-frozen evidence
population. No result may move a fact to `OK`.

## Frozen population and anti-overfit boundary

The population is exactly the three loss question IDs in the S136 gate. The
questions come from the independent S114 held-out cohort, which predates
`chunks_v3`. For each question the evidence population is:

1. the first 15 frozen `candidate_v3` results recorded by S136; plus
2. any candidate provenance-gold member not already present in those 15.

No item may be added or removed after a judge response. Duplicate or near-
duplicate content remains visible because redundancy is one of the measured
properties.

## Blind packet

A deterministic local builder reconstructs the candidate rows from the same
S135/S136 frozen inputs and raw extraction store. It creates:

- a judge packet containing only question, manufacturer, model and, for every
  evidence item, a deterministic opaque label, source section/page metadata and
  raw source content;
- a private mapping from opaque labels to candidate IDs, ranks, donor status and
  provenance-gold membership.

The packet excludes arm name, rank, score, database/document/chunk IDs, donor
status, gold membership, generated contextual prose, S135/S136 classifications
and the private mapping. Judges have no tools and receive only the public packet
and the frozen rubric. The private mapping is consumed only after both initial
judgements are complete.

## Rubric and output

Each judge must label every evidence item once as `DIRECT`, `SUPPORTING`,
`IRRELEVANT` or `UNCERTAIN`; identify exact/near duplicates; select the minimum
set of evidence needed to answer the question; and classify overall
answerability as `COMPLETE`, `PARTIAL` or `NONE`. A short claim and rationale are
required, but no free-form answer-generation quality is scored.

The local validator fails closed on missing/unknown/duplicate labels, malformed
JSON, a minimum set containing unknown items, or an internally inconsistent
minimum set. A valid `COMPLETE` judgement must have a non-empty minimum set,
every selected item must be `DIRECT` or `SUPPORTING`, and at least one selected
item must be `DIRECT`.

## Independent judges and model economy

- Primary: `gpt-5.6-sol`, Responses API, `reasoning.effort=xhigh`, structured
  output, no tools, no Pro mode.
- Independent adversarial judge: `claude-fable-5`, adaptive thinking with
  `output_config.effort=xhigh`, structured output, no tools.
- Both see byte-identical packet/rubric content and neither sees the other's
  output.
- An optional bounded `gpt-5.6-sol` arbitration is allowed only for terminal
  disagreements. It sees the packet and two anonymised judgements, never model
  identities. It cannot change evidence labels or retrieval ranks.

All deterministic construction, validation, mapping and aggregation is local.
The paid runner obtains exact provider input-token counts before inference and
computes a conservative maximum using the configured output caps. It refuses to
start if the cumulative worst case exceeds USD 10, a stricter internal ceiling
than the user's USD 50 authorisation.

## Mechanical terminal decision per judge

After unblinding, a question is `CANDIDATE_SUCCESS_AT_10` only when:

1. overall answerability is `COMPLETE`;
2. the judge's minimum sufficient set is non-empty; and
3. every member of that set has frozen candidate rank 10 or better.

Otherwise it is `REAL_CANDIDATE_RETRIEVAL_LOSS`. This rule handles multi-item
answers without post-hoc semantic thresholds. For Xtralis it directly tests
whether the unranked second provenance member is actually required.

The two independent terminal decisions must agree per question. A disagreement
uses the pre-authorised arbitration once. Failure, truncation or unresolved
disagreement remains `HOLD`; it is never counted as success.

## Promotion gate

`chunks_v3` can advance from the S135 loss gate only if all three questions end
as `CANDIDATE_SUCCESS_AT_10`, all packet/response validators pass, no evidence
population drift is detected, and actual spend remains below USD 10. This is
necessary but not sufficient for production migration: the already-frozen S134
metadata gate and all other S135 safety checks still apply.

Any real loss keeps `chunks_v3` at `NO_GO` and yields a question-level structural
diagnosis before another chunker or contextualisation change is designed. No
corpus-wide regeneration is authorised by S137.
