# S209 fresh-predicate planner holdout

## Decision being tested

S208 showed that the v3 contract can represent exact multi-page support, but
its independent review was invalid because one ambiguous field mixed blockers
with positive audit notes. S209 tests the corrected v4 review contract on a
fresh cohort and, only if that passes, measures the unchanged decomposed
evidence planner.

This is the final small holdout on this planner line before either opening a
separate target A/B preregistration or abandoning the line. S208 questions,
facts, mappings and model outputs are forbidden inputs.

## Cohort

- Two Kidde questions from two source identities not used by S203-S208 visual
  cohorts. Both identities overlap the official corpus, so neither external nor
  source-independent validation is claimed.
- One natural cross-page mechanism-to-specification item (KE-DP3020W pages
  1-2) and one bounded single-page maintenance procedure (NC page 36).
- Three full-page 200 dpi renders were inspected directly and bound by SHA-256.
- The first three selected topics were rejected locally because S99 already
  contained semantic equivalents. Novelty of the replacement predicates still
  requires both Frontier reviews; it is not asserted by local selection.

## Model roles and cost

- GPT-5.6 Sol xhigh is principal author, disagreement reviewer and support
  mapper.
- Claude Fable 5 independently authors, performs the publication review and
  reviews the immutable support mapping.
- GPT-5.6 Terra low runs the planner only after every upstream gate passes.
- Maximum geometry: 8 Frontier calls, 2 Terra calls, zero retries, zero target
  calls, and a conservative internal ceiling of USD 50.

## Fail-closed gates

1. Both models must produce valid pixel-only candidates for both items.
2. Fable must pass every Sol candidate; Sol must find no material disagreement
   in Fable's independent candidates.
3. Sol must map every frozen fact to exact citation-page sets and enumerate all
   alternative minimal complete unit sets.
4. Fable v4 must return explicit booleans and separate `blocking_issues` from
   audit `notes`. Notes never affect a verdict; every false fact must name a
   blocker.
5. Terra must return valid plans with at least two obligations per question,
   at least 0.80 selected-unit precision, 100% fact-support recall, both
   questions complete and exact deterministic compilation.

Any upstream failure is NO-GO with no same-cohort retry or reinterpretation.
Provider incompleteness is HOLD. A GO authorizes only a separately frozen target
A/B; it grants no official fact credit and no runtime integration.

## Fixed exclusions

- `chunks_v3`: `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.
- No retrieval, reranking, database writes, production changes or official-gold
  mutation.
- Railway remains a demo and never gates PRs or merges; green CI does.
