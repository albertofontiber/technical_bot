# S176 deterministic evidence card v1

## Decision being tested

Test a source-extractive complement to the current generated answer. The
current answer remains byte-identical. A deterministic selector may append at
most two short, exact evidence units from already served source text when those
units are strongly aligned with the question. This cannot retrieve, infer,
rewrite or remove a claim.

This differs from the closed omission-correction and relation-ledger lines:
there is no model selector, no generated relation and no revision. The visible
card is an auditable excerpt that a field technician can compare directly with
the answer. It is a common extractive-RAG safety pattern, but must still prove
that the additional text is useful rather than clutter.

## Frozen selector

1. Build the existing source-bound header-aware evidence units. Table units
   contain the exact table header plus one exact row; prose units are contiguous
   exact spans.
2. Fold accents and Markdown, remove the existing generic stopword list and
   score units with deterministic BM25 over question terms.
3. A unit is eligible only when it matches at least two distinct question terms
   and at least 25% of the distinct question terms.
4. Select at most two non-duplicate units in score order, with a total rendered
   source budget of 1,800 characters. Oversized units are skipped, never cut.
5. Append selected units under `Evidencia literal del manual`, preserving their
   complete bytes and original fragment citation.

No QID, manufacturer, product, expected value, answer point or target relation
participates in selection. Ties resolve by exact unit identity.

## Development screen

Use the same sealed 14-question/14-manufacturer S173 cohort and immutable
current-policy answers. Candidate answers and selection receipts are created
before loading the answer-point gold. Passing requires:

- at least four additional answer points and two additional complete questions;
- zero regressions (guaranteed structurally, verified nevertheless);
- zero invalid citations or source-span failures;
- evidence cards on at least two but no more than twelve questions;
- mean appended source text no greater than 1,200 characters among selected
  questions.

A local pass authorizes one blinded semantic/adversarial review for relevance,
answer readability and safety. It does not authorize a target probe, runtime,
production or fact credit. A failure closes this version without tuning on the
same cohort.

