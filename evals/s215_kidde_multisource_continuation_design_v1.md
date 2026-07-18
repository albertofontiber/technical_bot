# S215: deterministic continuation of the unattempted Kidde cohort

## Purpose

Finish the fresh multi-document gold cohort needed to develop and evaluate a
generic relevance/compression mechanism. S215 does not score the bot and cannot
move an official fact. It consumes the three S214 items that Fable never saw,
plus their already completed and locally valid Sol candidates.

## Why this is a clean successor

S214 is closed and immutable. S215 has a new preregistration, ledger, runner and
result namespace. Membership is computed without reading candidate semantics:
preserve S214 packet order, remove the one item whose Fable authorship call is
present in the closed S214 ledger, and require the exact three item IDs recorded
as unattempted by the sealed S214 closure. The failed NC item is never retried,
repaired, merged or replaced.

The three Sol candidates are immutable inputs, not new calls. Each corresponding
Fable authorship call is a first attempt and receives only the original frozen
topic, disclosed prior coverage and page pixels. It does not receive the Sol
candidate or extracted evidence units. The 12,000-token Fable envelope is frozen
before execution and changes only the provider completion allowance for these
never-attempted items; it does not alter the authoring contract by output.

## Fail-closed geometry

All three items are mandatory. GO requires, for every item:

1. the inherited Sol candidate remains locally valid;
2. a completed exact-model Fable candidate is locally valid;
3. Sol 5.6 xhigh passes the Fable candidate against pixels;
4. Fable 5 passes the Sol candidate against pixels;
5. the principal publication/disagreement gate passes;
6. Sol maps every principal fact to exact deterministic evidence unit IDs; and
7. Fable verifies pixel and unit support, completeness and alternative paths.

There are at most 15 execution calls: 3 Fable authorship, 6 reciprocal review
and 6 support calls. Provider retries, same-item retries, candidate repair,
candidate merge, item replacement and output-conditioned threshold changes are
forbidden. A provider or parsing interruption seals the new ledger
`INCOMPLETE_FINAL` automatically. A semantic failure seals NO-GO. Neither path
can publish a partial cohort.

## Frontier use and downstream boundary

Sol 5.6 xhigh is the principal author/reviewer/mapper and Fable 5 is the
independent author/reviewer. One compact dual Frontier design decision is made
after this design is merged; no iterative review convergence is allowed.

S215 ends at a fresh, support-validated, unintegrated cohort. Only a later
preregistered experiment may develop a generic upstream-to-downstream mechanism
on it, followed by an untouched target evaluation. `chunks_v2` remains active
and read-only. Wholesale `chunks_v3` remains final NO-GO. Railway and deployment
are not merge gates.
