# S202 — fresh real-question dual-gold gate

## Decision

Close S201 as `HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE` without retrying its 12
questions.  The provider rejected the dynamic array-cardinality dialect during
the first Anthropic token-count preflight, before any completed inference.  The
next legitimate attempt changes only that upstream transport and uses a fresh,
pre-existing question cohort.

S202 is intentionally smaller than the former all-in-one runner.  It constructs
and seals dual-model source-unit gold only.  Planner and target evaluation remain
closed until this upstream artifact passes.  This preserves the direction
source facts → source-unit gold → planner → deterministic compiler → target
replay and prevents another transport failure from consuming downstream work.

## Fresh population

The deterministic packet starts from the same versioned S100 fact ledger and
S113 serving contexts but excludes:

- all 12 questions attempted by S201;
- the four frozen synthesis targets (`cat018`, `hp002`, `hp011`, `hp017`);
- the two integrated default-off candidates (`cat007`, `cat013`).

Eligibility uses only pre-existing question identity, at least two and at most
six benchmark facts, non-empty context and primary manufacturer/product
identity.  Seeded selection takes manufacturer diversity first and then fills
without repeating normalized manufacturer/product pairs.  It never reads fact
text, answer class, `reaches_gen`, planner output or model output when choosing.

The resulting frozen packet has 12 questions, 5 manufacturers, 12 normalized
products and 43 benchmark facts.  Five manufacturers is the full diversity left
after the exclusions; it is reported as exhaustion, not hidden by reusing S201.

## Clean transport generalization

`src/rag/source_unit_gold.py` owns the reusable contract.  The Anthropic-facing
schema is a static rectangle of six point slots by six support slots.  It has no
array type, dynamic enum/const, `$ref`/`$defs`, combinator or cardinality keyword.
Point order, qid identity, active cardinality, unit membership, contiguity,
uniqueness and empty unused slots are enforced deterministically after parsing.
The schema contains no question-, fact- or source-specific values.

This is the same architectural boundary proven by S196, expanded to the maximum
cardinalities already frozen by S201.  The exact 6×6 schema passed Anthropic's
provider compiler through `count_tokens` before preregistration: 0 inference
calls, 0 retries, $0.  This check does not claim semantic or inference success.

Haiku 4.5 economically authors the ordered support mapping.  Luna economically
validates each supported/unsupported decision and may return up to three
independent equivalent support sets.  Gold passes only with:

- 0 invalid Haiku outputs;
- 0 invalid Luna outputs;
- 0 semantic disagreements;
- at least 36 of 43 facts independently confirmed as source-supported.

The 36-point threshold is unchanged from S201.  Unsupported facts stay outside
the future planner recall denominator; they are not silently converted to misses
or removed from the population.

## Bounded execution and stopping

Maximum execution is 12 Haiku calls plus 12 Luna calls, `max_retries=0`, under a
$3 internal ceiling.  No DB read/write, retrieval, reranking, final-answer
generation, runtime integration, deployment or production mutation is allowed.
Any author transport failure stops before Luna.  Any invalid validator output,
semantic disagreement or support-floor failure is `NO_GO_DUAL_GOLD`.  Provider
incompletion is HOLD.  There is no same-cohort retry.

A GO only authorizes a separately frozen real-question planner evaluation.  It
moves 0 official or diagnostic facts by itself.  Before any later runtime seam,
the critical review contract remains GPT-5.6 Sol `xhigh` principal plus Fable 5
independent, with no retry loop if Fable again returns an unusable final.

## Explicit orthogonal lanes

`chunks_v2` remains the active source.  `chunks_v3` stays
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` (recall@10 16/24 vs 16/24; MRR
0.4021 vs 0.3694), with no migration, materialization or per-question patch.
Railway is a demo and is not a PR/merge gate when CI is green.
