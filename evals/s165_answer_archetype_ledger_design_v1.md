# S165 product-bound answer-archetype ledger

## Problem addressed

The S164 generic omission detector selected sibling-product capacity facts and
ignored explicit safety/completeness relations in the queried product. Earlier
minimum evidence selectors also optimized for the most obvious surface answer
and under-selected implicit prerequisites, limits and verification steps.

## Hypothesis

A bounded ledger of reusable technical-answer facets can make selection more
complete without encoding manufacturers, products or benchmark facts. The
selector must bind the source packet to the query product before filling any
facet and may return only immutable source-unit IDs.

The reusable facets are:

- access or prerequisite;
- target object or configuration field;
- input, trigger or observed condition;
- output, action or corrective step;
- option, mode or default;
- measurement, limit or timing;
- safety, warning, exception or conflict;
- verification, commissioning or recovery.

The facets apply across programming, diagnosis, installation and specification
questions. They are a completeness checklist, not a requirement to fabricate a
slot: unsupported facets remain empty.

## Development gate

S165 reuses the fourteen exact-quote S147 items only as a target-independent
development cohort. The cohort was used previously to validate header-aware
evidence units, so it is not a fresh promotion set. A pass can authorize one
fresh independent test; it cannot authorize the four current target questions,
runtime integration or production.

Haiku receives the question, declared product identity, the generic facet
definitions and header-aware source units from one immutable excerpt. It returns
facet-to-unit-ID assignments. It cannot write claims, quotes or answers. All IDs
are validated locally and exact-quote coverage is scored only after outputs are
checkpointed.

## Frozen gates

- exact answer-point recall at least 90%;
- selected-unit precision at least 80%;
- at least 75% of questions fully covered;
- zero unknown or duplicate IDs;
- zero source-identity mismatch;
- no retries and spend below the internal ceiling.

No threshold may be relaxed after observing the results. Failure closes this
version without prompt tuning on S147.
