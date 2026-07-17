# S173 — single-source post-answer omission correction

## Decision being tested

Test the existing bounded omission-correction architecture only where retrieval
and source identity are already fixed: one correct served source excerpt per
question. This isolates synthesis coverage from the sibling-selection failure
that closed S164. It does not reopen S164 or change its result.

The generation population is the sealed S147/S171 cohort: 14 questions from 14
manufacturers, balanced across seven tables and seven prose excerpts, with zero
target-question overlap. Answer points are absent from the generation packet and
are loaded only after every baseline, selector and revision checkpoint is sealed.
The cohort has been used for development of other synthesis mechanisms, so S173
may authorize a target probe but cannot by itself establish external production
generalization.

## Frozen execution graph

1. The current production-grade writer (`claude-sonnet-4-6`) produces an
   untouched baseline from the current guided generator prompt and one source.
2. The cheap executor (`claude-haiku-4-5-20251001`) sees the question, draft and
   deterministic evidence units from that same source. It selects explicit,
   materially necessary omissions; it cannot retrieve another document.
3. The same production-grade writer performs at most one source-preserving
   revision when at least one validated unit was selected.
4. Only after all generation artifacts are checkpointed, the existing local
   point-coverage screen compares baseline and candidate against the sealed gold.
5. A passing local screen authorizes one separate blinded Sol 5.6 xhigh semantic
   validation. It does not authorize production or fact credit.

## Gates

- all 14 items must complete with zero invalid selector outputs, invalid fragment
  citations or token-limit stops;
- candidate point gain must be at least four of 37, with zero point regressions;
- at least two additional questions must become complete;
- at least one original source unit must be selected;
- no answer-point claim or exact quote may enter any generation prompt;
- total preflight cost must remain below the internal ceiling.

A failure closes this architecture for the current corpus. A pass proceeds only
to blinded semantic validation, because lexical coverage does not measure
unsupported additions, answer usefulness or safety.

