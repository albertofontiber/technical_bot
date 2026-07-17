# S143 bounded agentic evidence planner design v1

## Hypothesis

A cheap query-time model can act as an evidence planner before answer synthesis:
it selects a small set of exact supporting quotes from the already retrieved and
product-aligned context. Deterministic code verifies every quote byte-for-byte,
binds it to its fragment, rejects duplicates/oversize output, and caches the
validated packet by query/context/model/prompt identity.

This is not an autonomous web/database agent and it cannot add knowledge. It is
a bounded contextual-compression step intended for multi-part or procedural
queries where deterministic typed extractors leave the plan sparse.

## Architecture contract

1. Deterministic typed obligations remain the first path.
2. A trigger may invoke the cheap planner only for an under-covered complex
   query. The planner sees only the exact served fragments.
3. It returns 1-6 exact quotes and fragment numbers. No retry is allowed.
4. Validation rejects any quote that is not an exact substring of its declared
   fragment. A partial/invalid packet fails closed and is not sent downstream.
5. The validated exact quotes become source-bound obligations. Generated prose
   is not accepted as evidence.
6. The result is content-addressed and cached. Planner/model/prompt/schema and
   source identity are part of the cache key.
7. Final synthesis remains separately validated; planner success alone earns no
   OK credit.

## Prototype gate

Use the already-burned S142 independent cohort as development/challenge data,
not as a new held-out claim. Execute one production-shaped Haiku call per seven
eligible query/context pairs. Measure exact-claim coverage and quote precision.

The prototype is promising only if claim recall >= 0.80, quote precision >=
0.70, at least six of seven questions have a covered claim, every quote is exact,
and total conservative known cost is below $0.20. No retry is permitted.

Passing this prototype authorizes implementation plus a genuinely fresh
independent cohort. It does not authorize production, deployment, paid answer
generation, or facts moving to OK.

## Stop rules

- Any non-exact quote invalidates that question's packet.
- Provider/schema failure is checkpointed and not retried.
- Failure of recall/precision ends this version; do not tune on the same cohort.
- Fable/Sol are not used for this execution task. Reserve them for the final
  integrated architecture/adversarial gate if a fresh independent gate passes.
