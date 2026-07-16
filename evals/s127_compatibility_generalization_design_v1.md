# S127 compatibility generalization design v1

## Decision and scope

S126 proved that a source-bound, three-facet compatibility bundle can recover
the two `cat013` retrieval misses without allowing a model to infer unsupported
cross-manufacturer compatibility.  It did **not** prove that the mechanism
generalizes beyond that known pair.  S127 addresses that P2 gap only.  It does
not claim an answer-level OK, change a gold fact, enable a production flag, or
change the generic serving budget.

The target metric for this work is relational retrieval quality on an
independent multi-manufacturer cohort:

- 100% exact-receipt and catalog-scope precision;
- zero partial bundles and zero false topology matches;
- recovery of at least 80% of adjudicated locally eligible positive cases;
- at least three eligible positives spanning three device manufacturers and
  two host-panel manufacturers; otherwise the result is `INCONCLUSIVE`.

This metric is deliberately different from the official fact funnel.  S126's
measured result remains two retrieval transitions (`retrieval-miss` to
`synthesis-not-measured`), zero facts moved to OK.  S127 cannot add OK credit.

## Verified development diagnosis

Six real two-entity questions were selected from the frozen local corpus.  They
are development material because their products and source documents were
inspected while diagnosing the mechanism; they are not held out.

The current navigation path can hydrate up to six relevant candidates, but it
applies the generic greedy three-row serving selection before the relational
validator runs.  In the inspected `CR-6EA` / `DXc1` case, the six candidates
contained the decisive device protocol span, the device roster span and the
host topology span.  The greedy trim nevertheless kept a false host roster, an
installation span and the topology span.  The complete valid triplet was
therefore made impossible before validation.

A second precision failure is latent in topology classification: a panel
network ring may contain both `ring` and `return` vocabulary while saying
nothing about a detection-device loop.  Treating it as loop topology would
produce an unsafe relational bundle.

## Recommendation

Separate the compatibility lane's **navigation candidate budget** from its
**served evidence budget**:

1. keep up to six canonical, exact-receipt navigation candidates internally;
2. enumerate deterministic candidate triplets rather than greedily selecting
   three individual rows;
3. accept exactly one complete triplet containing:
   - `protocol_scope` and `supported_device_roster` from the same governed
     device document, extraction and product group;
   - an exact device-token occurrence in the roster span;
   - `loop_topology` from the other resolved product group;
   - distinct parent/provenance receipts for all three facets;
4. require topology evidence to contain all of:
   - a loop anchor (`lazo`, `bucle`, `loop` or `SLC`);
   - a closed/return anchor;
   - a detection-device context anchor (for example `detección`, `detector`,
     `dispositivo`, `equipo`, `analógico`, `addressable` or `sensor`);
5. rank valid triplets deterministically; reject ambiguity rather than merging
   evidence across competing documents;
6. append exactly three rows atomically, or append none.

The generic HYQ serving limit remains two and all other compatibility behavior
remains default-off.  The six-row pool is internal navigation breadth, not a
larger prompt/context allowance.

## Alternatives considered and rejected

1. **Raise the global serving limit.** Rejected because it leaks irrelevant
   evidence into every query, spends context tokens and does not enforce the
   required relation.
2. **Keep greedy selection and tune facet weights.** Rejected because any
   per-row score can still discard a lower-ranked member of the only valid
   triplet; the unit of selection must be the relation bundle.
3. **Use an LLM or agentic reranker.** Rejected for this bounded decision.  The
   obligations and provenance constraints are deterministic, so a model adds
   cost, non-repeatability and an unsupported-inference surface without adding
   necessary semantics.
4. **Add product, manufacturer, QID or expected-answer rules.** Rejected as
   direct overfitting and non-scalable to 30+ manufacturers.
5. **Relax exact device-token binding to section titles or neighboring chunks.**
   Rejected for this iteration.  It would make `SGMCB200` easier to recover but
   weakens the evidence contract.  Title/content separation is recorded as a
   possible upstream chunk-lineage issue and remains fail-closed.
6. **Treat any ring/return text as topology.** Rejected because network-ring and
   electromagnetic-compatibility passages are hard negatives, not evidence of
   a detection loop.

## Why this is BP, structural and scalable

The change models retrieval as constrained set selection: navigation may be
broad, but serving is a small, provenance-complete evidence set.  This is the
same precision-first pattern used elsewhere in the bot for atomic procedure and
reference bundles.  It is structural because it changes the selection unit
from independent chunks to a typed relation; scalable because its vocabulary
and invariants are product-agnostic and its search is bounded (`n <= 6`, at
most 20 triplets); and economical because local replay requires no model calls
or database writes.

## Known gaps and risks

- The development set is exposed and cannot establish generalization.
- Some manuals separate the product name into a heading-only chunk.  Those
  cases will remain false negatives until a separately governed chunk-lineage
  mechanism is justified.
- Same-manufacturer or explicitly cross-certified compatibility is not proved
  merely by this bundle.  The bundle is sufficient for safe downstream refusal
  when support is incomplete, not for asserting compatibility.
- A six-candidate pool may still miss evidence because of earlier retrieval or
  catalog resolution.  Such cases remain retrieval misses and must not be
  relabeled as selector failures.
- Bilingual lexical anchors are deliberately conservative.  Independent cases
  in additional languages can make the gate inconclusive but cannot justify
  vocabulary expansion after seeing their outcomes.
- The official fact funnel remains unchanged until a separate frozen full
  assessment is run after release approval.

## Cheap execution and gate order

1. Freeze the exposed development cohort and pre-change hashes.
2. Obtain adversarial review of this design before implementation.
3. Add deterministic unit attacks and a local frozen-snapshot replay.
4. Freeze mechanism code/config hashes.
5. Select and preregister an independent cohort excluding every S126 and S127
   development product, source and near-duplicate family.
6. Run the local independent replay twice and require identical receipts.
7. Only if the local gate passes, run the minimum read-only live probe with zero
   model calls and zero writes.
8. Obtain final adversarial GO/NO-GO.  Keep the flag off and assign zero OK
   credit unless a separately authorized assessment supports a funnel change.

## Frozen pre-change inputs

| Input | SHA-256 |
| --- | --- |
| `src/rag/compatibility_bundle_coverage.py` | `2e03b4af1448fce57f219e4ef128a393687ae32f5a3bbf4eb6b8726d4fc5ab0c` |
| `src/rag/doc_scoped_hyq_coverage.py` | `d938d4ce43757627e9db4c99dab948ef6b6dcb28cf82c7ee102edf359c65c43b` |
| `config/retrieval_facets_compatibility_candidate_v2.yaml` | `b2b600eb78b0817a746a0fd1249c243a8046f8cdf4e5c11435088b6096bae6ad` |
| `config/evidence_coverage_compatibility_candidate_v1.yaml` | `f6c73113746608d8fff567f6fa23a2415433c429c77f5e3121429b77f453d937` |
| `tmp/s117_m25/derived_snapshot_v2.jsonl.gz` | `a825e4dd02b918ddafebab4419cb416b6edc5f1b823a7a9d423f96718d7b6217` |
| `data/catalog/doc_map.jsonl` | `992c62c21b5772caebf09f422adca20ffe4035143861ca931e5198e820572c82` |
