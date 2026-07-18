# S235 — direct clause-bound synthesis A/B

## Decision to test

The canonical scoreboard is 143/157 facts OK (91.08%): 12 synthesis misses and
2 retrieval misses. The 12 genuine synthesis residuals are already frozen in
S163 and occur in four questions (`cat018`, `hp002`, `hp011`, `hp017`). No new
gold or new question is needed for this experiment.

S235 tests whether the remaining failures are caused by monolithic synthesis
under multiple simultaneous technical obligations. The treatment is the S228
clause-bound architecture already integrated default-off:

1. a cheap planner decomposes the question and binds each obligation to a
   minimal set of evidence units;
2. one isolated writer call answers only that obligation and sees only its
   bound units;
3. local validation rejects unknown unit IDs, invalid claim geometry and
   writer-invented citation markers;
4. a deterministic assembler emits every block exactly once and derives
   fragment citations from the accepted unit IDs.

This is an evidence-bound decomposition experiment, not a prompt-only rewrite,
post-hoc appendix, full-answer revision, or new-gold exercise. Those adjacent
lines are already closed or are outside the immediate residual bucket.

## Paired causal design

- Population: the exact four frozen target questions, 51 frozen served chunks,
  20 evaluator obligations, 12 genuine residual IDs and one frozen document
  conflict.
- Baseline: the current guided production-style prompt, generated afresh by
  `claude-sonnet-4-6` at temperature 0.
- Treatment: `claude-haiku-4-5-20251001` as the economic planner and the same
  `claude-sonnet-4-6` writer family at temperature 0.
- Replication: two independent provider responses per arm and question.
- Output budget: 3,600 tokens per baseline answer and an aggregate maximum of
  3,600 writer tokens per treatment answer. Decomposition cannot win merely by
  receiving a larger answer budget.
- Retrieval, chunks, questions and model family for answer writing remain
  fixed. The intended causal variable is obligation/evidence isolation plus
  deterministic assembly.

## Leakage boundary

`s235_direct_clause_bound_generation_packet_v1.json` contains only question and
served context. It contains no canonical answer, evaluator obligation,
residual ID, anchor or conflict. The generation runner imports and opens only
that packet. The physically separate score packet is opened only after all
eight paired generations are sealed `COMPLETE_SCORE_NOT_OPENED`.

The score packet and scoring code are therefore unavailable to both the
planner and writers. The planner may create its own untrusted obligation labels;
these are generation outputs, not evaluator labels.

## Deterministic and safety checks

For each frozen obligation, the existing deterministic validator records
coverage in the canonical answer, both contemporary baselines and both
treatments. A residual is:

- **stable treatment coverage** only when both treatment replicas cover it;
- **stable baseline coverage** only when both baseline replicas cover it;
- a **strict causal gain** only when both treatment replicas cover it and
  neither baseline replica does.

The direct A/B advances to semantic adjudication only if:

1. stable treatment residual coverage exceeds stable baseline coverage;
2. at least one strict causal gain exists;
3. no obligation covered by the canonical answer is lost in either treatment;
4. every treatment has zero invalid citations;
5. every treatment safely handles the frozen version conflict;
6. actual stage cost is below $25.

This deterministic match is a routing gate, not official fact credit. Any
candidate gains receive one semantic review from principal reviewer
`gpt-5.6-sol` at `xhigh` and one independent review from `claude-fable-5` at
`xhigh`. There are no review-convergence rounds. Official score movement and a
default-on decision require dual semantic acceptance plus the existing full
regression suite.

## Failure and cost policy

- Provider SDK retries are disabled.
- A call may receive at most one manual retry only after a recognized transport
  error (408/409/429/5xx/520/529). Semantic/schema/model failures receive zero
  retries.
- Attempt and completion events are sealed before scoring.
- The conservative preflight counts every UTF-8 input byte as a possible token,
  includes the maximum 12 writers per treatment, and doubles the estimate for
  the bounded transport allowance. It must remain below $25.
- Design review is exactly one Sol call and one Fable call. A failed provider
  transport is recorded; it does not start an open-ended convergence loop.

## Interpretation

- `GO_FRONTIER_SEMANTIC_ADJUDICATION`: causal signal and deterministic safety
  checks pass; run the one-shot semantic review.
- `NO_GO_S235_DIRECT_AB`: close or redesign from the observed failing stage.
- Reaching 154/157 (98.09%) before semantic review is only a projection; it is
  not official until dual review and regression complete.

Production remains default-off throughout S235. `chunks_v2` remains
`ACTIVE_READ_ONLY`; wholesale `chunks_v3` remains `FINAL_NO_GO`; Railway is a
demo and is never a PR or merge gate.
