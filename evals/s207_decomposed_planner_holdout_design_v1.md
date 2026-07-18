# S207 — pixel-audited holdout for the decomposed evidence planner

## Decision scope

S207 measures the still-unproven structural successor to S193: decompose a
question into explicit subobligations, select immutable source-unit IDs, and
compile only those units deterministically. It does not test retrieval,
reranking, chunk migration, free-prose generation, or a general benchmark
expansion programme.

The canonical denominator remains 157 facts: 143 OK, 12 synthesis misses, and
2 retrieval misses. Reaching 98% requires 154 OK, hence 11 additional facts.
S207 is an upstream falsification test and grants no official fact credit.

## Why this does not reopen S203–S205

S205 showed that principal Sol authorship plus Fable publication review can
produce pixel-correct candidates, but its cohort was invalidated by hidden
same-PDF semantic coverage. S207 uses visual authorship only because no frozen
planner holdout exists. The builder now discloses exact source identity and all
same-source HyQs, rejects any focus page with an existing HyQ, excludes official
gold and S203–S205 source identities, and forbids retry, repair, merging, or
post-selection. Multilingual mirrors and same-table predicates remain an
explicit semantic veto for both frontier models. Standalone visual-gold
expansion remains closed.

## Frozen holdout

Three predicates were selected before model or bot output and checked against
full-page 200 dpi renders with page-bound pixel receipts:

1. KE-DM3110 isolator parasitics across pages 15–16: active-isolation
   consumption, maximum leakage current, and maximum series impedance.
2. Excellence outdoor notification device page 10: the paired nominal currents
   for a closed isolator and for an active isolator during a short circuit.
3. 2X-A operation manual page 37: the bounded LCD-test route, defective-pixel
   purpose, and exit action.

They span a cross-page specification table, a paired operating limit, and a
bounded diagnostic procedure. The three PDFs have no source-identity overlap
with official gold or S203–S205. Existing same-source HyQs are included verbatim
for semantic review; exact-page novelty is necessary but not sufficient.

Evidence units use the general header-aware unitizer with a 450-character cap
and zero overlap. Units longer than 600 characters fail the build. This removes
the whole-page escape hatch identified by the adversarial review while retaining
immutable source spans and hashes.

## Gold and mapping construction

- Principal author/reviewer: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent author/reviewer: `claude-fable-5`.
- Authorship and cross-review receive page pixels, the frozen topic, source
  identity, and novelty coverage. Extracted text and evidence IDs are withheld.
- Sol authors three candidates; Fable independently authors the same three.
  Fable must pass every Sol candidate. Sol reviews Fable candidates only as a
  blind material-disagreement probe. Fable candidates are never published.
- The corrected v2 author contract binds its citation example to an allowed
  focus page; historical visual-gold code and frozen cohorts remain unchanged.
- After pixel gold passes, Sol maps each immutable atomic fact to the smallest
  complete set of frozen evidence-unit IDs using pixels and units. Fable reviews
  every mapping independently. This mapping phase cannot change questions,
  facts, answers, pages, or units.
- Any invalid output, insufficiency, semantic duplicate, unsupported fact,
  unknown ID, mapping defect, or material disagreement closes S207. No retries.

## Planner experiment

The economic planner receives only the Spanish question, a whitelisted bound
identity, and frozen evidence units. Gold claims and support IDs remain hidden.
It must return at least two distinct, non-empty subobligations with allowed unit
IDs. The deterministic compiler starts from an empty diagnostic base and emits
an exact source appendix; that appendix is not customer-facing answer prose.
Foreign-language evidence is therefore scored as source selection, not inserted
into a production response.

There are exactly three planner calls using `gpt-5.6-terra` at low reasoning.
Frontier models are reserved for pixel correctness, support mapping, and critical
review. A failed economic configuration closes only this exact S207 execution;
it neither proves nor disproves every possible planner configuration, and S207
has no tuning or escalation loop.

## Frozen upstream gates

`GO_S207_TARGET_PREREG` requires all of the following:

- 3/3 Sol candidates valid and 3/3 Fable publication reviews PASS;
- zero semantic duplicates, unsupported claims, invalid citations, or material
  disagreements;
- every fact mapped to known units on its cited page and every mapping passed by
  Fable;
- 3/3 planner outputs valid, each with at least two distinct obligations and no
  unknown identity field or unit ID;
- atomic-fact support recall at least 90%;
- selected-unit precision at least 80%;
- all 3/3 questions complete;
- exact deterministic compilation and zero invalid citations.

Passing S207 authorizes only a separate target A/B preregistration. It does not
open a target run automatically, authorize runtime integration, or claim 11
stable gains. Before any target call, that later preregistration must freeze the
unchanged S141 target obligations and contexts, baseline answers, candidate
runner and prompts, compiler, judges, model IDs, reasoning settings, seeds or
repeat policy, protected suite, hashes, and GO/HOLD/NO-GO rules. Stable official
movement then requires at least 11 new fact gains across the frozen repeat
policy, zero prior-covered regressions, zero new contradictions, and green CI.

## Invariants

- `chunks_v2` stays active and read-only in S207.
- `chunks_v3` stays `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; no migration,
  materialization, or per-question patch is allowed.
- No retrieval, reranker, database write, deployment, or official benchmark
  mutation occurs in this upstream holdout.
- Railway is a demo and never gates a PR or merge; green CI does.
- Production, canonical fact credit, and benchmark changes require a separate
  reviewed promotion.
