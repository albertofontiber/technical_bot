# S164 legacy held-out omission-correction canary

## Purpose

S157 left the post-answer omission-correction architecture unmeasured because
its synthetic multi-fragment cohort could not be authored without relaxing the
frozen independence rules. S164 does not retry that cohort. It uses the already
frozen `ho008` held-out question, five served chunks and five historical draft
answers from S63 as a cheap architecture canary.

The canary is independent of the four current synthesis target questions, but
it is not a new blinded promotion cohort: its historical semantic judgement is
already known. A pass can only authorize a larger versioned held-out test. It
cannot authorize target execution, integration or production.

## Architecture under test

1. Select generation seed `0` mechanically from the S63 treatment arm.
2. Unitize each of the five immutable served fragments into exact contiguous
   spans or table-row/header composites.
3. Haiku compares the question and draft with one fragment at a time and may
   return only source-unit IDs containing material omissions.
4. If units are selected, Sonnet writes one revised answer using the original
   full context, draft and exact selected units. There are no loops or retries.
5. A deterministic evaluation-only oracle checks the ten pre-existing atomic
   facts for `ho008`, citation bounds and regressions.

No gold fact, target relation, product-specific rule or expected answer is sent
to either model. Every selected unit remains reconstructible from its original
fragment.

## Gates

- gain at least two of ten atomic facts;
- regress zero previously covered facts;
- zero invalid fragment citations;
- zero invalid selector outputs;
- at least one exact source unit selected;
- spend below the frozen internal ceiling.

A pass means only `GO_TO_LARGER_LEGACY_HELDOUT_TEST`. A failure closes this
architecture without prompt tuning on `ho008`.
