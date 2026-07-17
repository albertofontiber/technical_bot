# S142 query-scoped evidence generalization design v1

## Decision

Evaluate a deterministic extractive fallback that selects at most three exact,
query-relevant source records from chunks already aligned by retrieval. It is a
general evidence-planning layer, not a replacement for retrieval, reranking, or
typed technical obligations.

S141 v1 remains a valid local diagnostic for 13 development relations but did
not emit on its first independent cohort. S142 therefore adds a product-agnostic
layer based on structural records and generic technical concepts, developed on
the now-open S114 cohort. It contains no manufacturer, product, QID, expected
answer, benchmark fact, or candidate identifier.

## Evidence and identity boundary

- Selection operates only on chunks already product-aligned by the planner.
- Every candidate carries one exact source interval and deterministic identity.
- No value is translated, inferred, normalized across products, or copied from
  the question into the source statement.
- Cross-language terms are used only to rank source records. The emitted text is
  still the exact manual span.
- A question without a recognized technical intent, or source without a
  matching concept plus a factual/relation signal, emits nothing.

## Development contract

The opened S114 source-first cohort contains 24 questions from 12 manufacturers.
One Spanish/Russian-only pair is excluded from positive recall because a local
lexical selector cannot safely infer the cross-language relation. The frozen
development support set contains 28 exact relations across the other 23
questions.

Required before independent execution:

- 28/28 development relations contained in selected exact spans;
- at most three selected records per question;
- exact source bounds and byte-determinism;
- unrelated/content-free queries emit zero;
- runtime source contains no development/product literals;
- no model, network, or database call.

## Independent contract

The sealed cohort was created source-first from 12 documents acquired in S116:
Bosch, Siemens, Hochiki, and Apollo, with zero PDF identity overlap with S141 or
S114 development. Haiku authored questions and exact claims as a cheap executor;
only claims with exact or unique whitespace-only source alignment survived.

The S142 extractor implementation and development tests are frozen before
opening cohort contents. Independent metrics are mechanical:

- claim recall: an exact claim quote is contained by at least one selected span;
- candidate precision: a selected span contains at least one exact claim quote;
- cross-item leakage: a span may only come from its own sealed item;
- maximum three selected spans per question;
- byte-identical output across two runs.

Minimum gate: claim recall >= 0.80, candidate precision >= 0.70, zero leakage,
and at least five eligible questions with a positive emission. Failure creates a
new version and burns this cohort for future tuning.

## Integration gate after independent success

Only after the independent extractor gate passes may `answer_planner` add an
S142 contract. The generic record must have a conservative bounded validator;
failure to demonstrate coverage should force exact source-bound reconstruction,
not accept a bag of disconnected keywords. All cache-affecting versions must be
updated. Historical S119-S141 contracts remain stable.

The integrated path then requires the full protected test suite, a local replay
of the 13 synthesis targets, and a minimal answer-generation probe. Official OK
credit remains zero until answer-level adjudication passes.

## Non-goals

- No chunks_v3 migration (S140 remains NO_GO).
- No online agentic planner or recurring LLM extraction.
- No product-specific exceptions.
- No production deployment, database write, push, or KPI change.
