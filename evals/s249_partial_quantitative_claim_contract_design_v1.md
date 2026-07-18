# S249 — Partial quantitative claim contract v1

## Causal scope

S243 attributes five residuals to compound qualifier loss. Three of those five
are quantitative bundles in which a generated answer already states part of a
source relation but loses a bound, scope, unit or step. S249 tests only that
subcause. It does not select documents, improve retrieval, enumerate all facts
in a fragment, or claim to solve the other nine residuals.

S248 proves that the existing S122 enforced contract covers zero current
residual obligations. Extending S122 with target-specific kinds would reopen
the closed S141 line and is forbidden.

## Mechanism

The detector receives an answer and the exact fragments already served to its
writer. It builds immutable relation-complete source atoms using S245's frozen
source-offset unitizer, but retains only atoms containing at least two distinct
technical quantitative fields:

- a lower/upper range with a shared engineering unit;
- two or more values carrying engineering units, percentages or tolerances;
- an alphanumeric configuration range such as two switch-position endpoints.

Dates, page numbers, revisions, document identifiers and isolated values are
not quantitative bundles.

For each answer segment, a source atom is reported as partial only when all of
the following hold:

1. the segment explicitly cites the atom's fragment (`[F<n>]`);
2. the segment reproduces at least one complete quantitative field from it;
3. the segment and atom share at least two non-trivial lexical anchors;
4. at least one other quantitative field from the same atom is absent.

The v1 local screen is detection-only. It cannot alter an answer. A later
candidate may expose the finding to a one-call structured answer compiler, but
no retry, model rewrite, generic evidence-card addendum or full-answer
fail-closed action is authorized by this design.

## Why this is not a repeat

- S176 selected up to two global BM25 source units and appended visible cards;
  S249 is answer-led, citation-bound and detects only partial quantitative
  relations.
- S245 highlighted 79% of nonblank source characters before generation; S249
  requires at least two technical numeric fields plus answer overlap and has a
  density ceiling of 25%.
- S220/S222/S223 rewrote or appended model-authored text after generation;
  S249 v1 performs no mutation and authorizes no retry or addendum.
- S141 encoded product-specific relation types; S249 has no product, QID,
  manufacturer, model or gold vocabulary.

## Local causal gate

The frozen non-target S147/S171 cohort contains 14 questions from 14
manufacturers, Spanish and English, table and prose. For every qualifying
source atom, the runner creates deterministic positive mutations by removing
one quantitative field from an otherwise exact source-bound segment while
retaining its fragment citation. Untouched complete segments and segments with
an unrelated number are negatives.

The mechanism advances to one dual frontier review only if:

- at least 12 qualifying atoms exist across at least 8 questions and 6
  manufacturers;
- both languages and both table/prose strata are represented;
- mutation recall is at least 0.90;
- negative precision is at least 0.95 and false-positive rate at most 0.05;
- qualifying source-span density is at most 0.25 globally and 0.30 at the
  median item;
- every finding is exactly reconstructible from source offsets;
- the unmodified baseline answers are never changed.

Thresholds and algorithm are frozen before running the local gate. Failure
closes S249 without target inspection, writer calls or prompt tuning.

## Later gates, not yet authorized

If and only if the local gate passes:

1. Sol 5.6 xhigh reviews the clean compiler boundary as principal reviewer;
   Fable 5 reviews independently. One round, no convergence loop.
2. A small non-target A/B tests whether a structured one-call writer can consume
   the contract without regressions.
3. Only a passing non-target A/B opens the exact quantitative subset of the
   twelve residuals.

Facts remain 143/157 until a complete answer-level adjudication passes. Railway
is not a merge gate. `chunks_v2` remains active/read-only and wholesale
`chunks_v3` remains final no-go.

