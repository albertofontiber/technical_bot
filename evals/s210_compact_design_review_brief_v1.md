# S210 compact Frontier design gate

## Decision requested

PASS only if this frozen experiment can safely decide whether a generic
query-conditioned evidence compiler advances to a separate atomic result review.
This review does not award facts, claim 98%, authorize runtime integration, or
establish fresh external generalization.

## Frozen hypothesis and mechanism

Current canonical diagnostic snapshot: 143/157 facts OK, 12 synthesis misses and
two retrieval misses. S210 must recover at least 11/12 residual relations in both
full replicas, including at least 4/5 in the largest residual question, without a
regression. The runtime mechanism contains no target IDs, fact names, expected
values, model names, manufacturers, or products.

For each already-retrieved chunk, Haiku 4.5 receives only the question and chunk
text and emits atomic claims with a shortest contiguous exact quote. Local code
binds every quote to real source offsets, permits whitespace-only repair, and
drops invalid claims. A deterministic generic query-relevance fallback contributes
at most 12 source spans. Terra 5.6 low sees the question plus opaque evidence IDs,
selects at most 12, and one independent-role Terra call may add at most six. Terra
cannot write prose. Local code copies every selected exact span with its existing
fragment citation into an appendix; the original baseline remains byte-identical
as a prefix.

Models see neither baseline nor gold. Scoring opens only after all 202 responses
are sealed. There are two replicas of four target questions plus 14 previously
observed S173 questions used only as additive no-regression/noise guardrails. The
old guardrail is explicitly not fresh generalization evidence.

## Fail-closed gates

Local GO requires all of the following: at least 11 stable residual relation
gains; at least four stable gains in the largest question; no loss of a previously
covered target relation; no new cardinality contradiction relative to the
baseline; zero regressions across 37 guardrail answer points; selected-evidence
precision at least 0.70 on the guardrail; exact baseline prefixes; valid fragment
citations; mean appendix at most 5,000 characters; and actual cost below the
sealed ceiling. A target gain is qualified only when the candidate answer passes
the pre-existing relation validator and a selected exact source-span receipt
overlaps the pre-existing obligation span. The already-present cardinality
conflict remains debt and cannot be claimed as fixed merely by appending text.

A local GO still moves zero facts. It permits exactly one Sol 5.6 xhigh principal
plus Fable 5 independent atomic review of source support, entailment,
contradictions, and usefulness. Only their full agreement on at least 11 facts can
produce the diagnostic 154/157 projection. Runtime remains unwired/default-off
until a later external real-question gate. NO-GO closes S210 without tuning,
postselection, retry, or cohort changes.

## Isolation, call geometry, and spend

The run performs 130 extractor calls, 36 planner calls and 36 verifier calls,
with provider retries disabled and no resume. Before the first provider call, it
charges UTF-8 bytes as input tokens, every unknown Terra prompt at its hard
100,000-byte cap, and every output at its maximum. The frozen conservative bound
is $22.948314, below the internal $75 ceiling; observed spend is checked again.
No retrieval, reranking, database write, free writer, or runtime integration is
performed. `chunks_v2` stays read-only; `chunks_v3` stays
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway is not a merge gate.

Frozen zero-call preflight SHA-256:
`69592124cfc32f70eafaf3597c1f3dc4433481c158a84c3f6ade887110d330f2`.

Review specifically for a concrete defect that could falsely produce local GO,
leak target answers into the mechanism, break exact-span binding, permit an
unbounded run, or overstate what the cohort establishes. Do not require style
work, another cohort, runtime validation, or another review round at this gate.
