# S154 question-conditioned claim map design v1

## Decision

Test one bounded map stage before changing retrieval, prompts or production.
Each already-served chunk is inspected independently with the technician's
question visible. A cheap executor may emit zero or more atomic claims, but
every claim must carry a contiguous exact quote from that one chunk.

This differs materially from the rejected lines:

- S149 selected a small global subset and under-covered broad questions.
- S150 added one global verifier and still prioritized surface facets.
- S153 extracted a fixed source-first relation ontology without the question
  and omitted eight of thirteen target relations.

S154 has no global selector and no fixed technical ontology. It maps every
served chunk, unions all source-bound question-relevant claims, and stops
before answer generation unless the claim ledger itself passes.

## Generalization and anti-overfit boundary

The mapper receives only the question and one source chunk. It never receives
QIDs, expected answers, gold facts, target relation names, other chunks or
prior misses. Its reusable coverage facets are direct answer, procedure,
configuration, prerequisite/safety, threshold/default, diagnostic,
exception/warning, and verification.

The frozen target oracle is loaded only after all provider responses are
checkpointed. A pre-existing independent cohort (S147: fourteen documents and
fourteen manufacturers, selected and authored before S154) is evaluated in the
same run. No output from either cohort may be used to retry or edit v1.

## Gates

- exactly 65 one-chunk calls: 51 frozen target contexts plus 14 independent;
- no retries and no model-authored identity fields;
- 100% provider receipts checkpointed before validation;
- zero accepted claims without an exact source span;
- target coverage at least 11/13, with 13/13 required before an answer probe;
- independent gold-point lexical coverage at least 80%;
- at least 80% of independent emitted claims overlap a frozen gold point;
- total actual cost below $1.75.

Any failed gate closes S154. Passing the claim-map gate permits only a separate
four-answer composition preregistration; it moves zero facts to OK and does not
authorize production, deployment or push.

