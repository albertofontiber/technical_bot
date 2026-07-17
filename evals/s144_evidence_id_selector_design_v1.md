# S144 immutable evidence-ID selector design v1

## Decision

Replace quote copying with deterministic immutable evidence units. Code owns all
source spans and IDs; the cheap model may only select IDs from the supplied set.
It cannot emit prose, values, quotes, offsets, or unknown IDs. Selected IDs map
back to exact source bytes and source identity.

This removes S143's transport failure class while retaining the useful part of
the agentic design: semantic query-to-evidence selection across languages and
manual layouts.

## Prototype

- challenge: the seven eligible questions and 14 exact claims from the now-open
  S142/S143 cohort;
- segmentation: frozen S144 evidence-unit contract, exact spans, <=50 units per
  question, all 14 claims representable before model execution;
- executor: one Haiku call per question, max six selected IDs, no retry;
- validation: every selected ID must be unique and belong to that question;
- metrics: exact claim containment and selected-unit precision.

Gate: claim recall >= 0.80, selected-unit precision >= 0.70, positive coverage
on >=6/7 questions, zero invalid IDs, and conservative total cost below $0.20.

Passing is only a development GO. It authorizes a production-quality cached
planner implementation and a fresh independent cohort. It does not authorize
integration, deployment, push, or facts moving to OK.

## Production requirements if the prototype passes

- typed deterministic obligations run first;
- ID selection only for under-covered complex queries;
- content-addressed cache includes query, exact unit manifest, prompt, schema,
  model and identity contract;
- invalid/empty output fails closed with no retry;
- final answer generation and post-generation obligation coverage remain
  separately validated;
- a fresh independent gate plus one frontier adversarial review is required.
