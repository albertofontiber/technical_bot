# S127 compatibility generalization design v2

## Status and corrected decision scope

This version supersedes v1 after an adversarial `NO-GO-to-build` with four P1
findings.  S127 does not evaluate or prove device interoperability.  It tests a
narrower retrieval capability: whether the bot can construct a source-bound
three-facet **diagnostic refusal bundle** for two resolved entities without
serving partial or misleading evidence.

S126's measured result remains two retrieval transitions from
`retrieval-miss` to `synthesis-not-measured` and zero facts moved to OK.  S127
cannot add OK credit or change the official funnel.

## Metric for today

The independent target is `three_facet_diagnostic_bundle_opportunity`, not a
"compatibility positive".  A question is an eligible opportunity only when a
source-first adjudication, frozen before selector execution, identifies:

1. exact protocol-scope and official device-roster spans in one governed
   document/extraction associated with one resolved entity group;
2. an exact field-device detection-loop topology span in a governed document
   associated with the counterpart group;
3. distinct immutable parent receipts for the three facets; and
4. no explicit source span proving direct interoperability between the queried
   products.  Explicit interoperability belongs to a different future answer
   contract and is excluded from this diagnostic-refusal evaluation.

Release metrics:

- exact-receipt and catalog-scope precision: 100%;
- partial bundles or false topology matches: 0;
- recall over independently adjudicated eligible opportunities: at least 80%;
- at least three eligible opportunities across three relation-closed OEM/rebrand
  classes and two counterpart-panel classes; otherwise `INCONCLUSIVE`;
- two identical local runs, including candidate-pool and rejection receipts.

Three eligible examples are a pilot gate, not evidence that coverage has been
proved for 30+ manufacturers.  A GO permits default-off integration only.

## Verified development diagnosis

The six exposed development questions in
`evals/s127_compatibility_development_cohort_v2.yaml` show that the navigation
path can hydrate relevant parents and then destroy the only valid relation by
applying generic per-row greedy selection before relational validation.  In the
inspected `CR-6EA` / `DXc1` case, the six hydrated candidates included protocol,
roster and topology evidence; the greedy three-row trim discarded the first two.

Two additional contract gaps are verified in current code:

- `catalog_resolver` returns two unordered source groups.  It does not prove a
  syntactic `device` / `host` orientation.
- one parent may carry cards for multiple facets, while the current bundle
  validator requires each served parent to attest exactly one facet.

## Recommendation

### 1. Separate navigation breadth from served evidence

Expose a compatibility-only candidate-pool mode from document-scoped HYQ.
Generic HYQ behavior remains byte-compatible.  Candidate-pool rows are
navigation-only and cannot carry a serving validation marker.  Evaluate pool
prefixes `k=3,4,5,6` on exposed development material and freeze the smallest k
that reaches the maximum valid-bundle recovery with zero negative acceptance.
Never tune k on the independent cohort.

The final served budget remains exactly three rows.  No larger model prompt or
global retrieval limit is introduced.

### 2. Project typed candidate atoms

Project every candidate into `(parent_id, facet)` atoms containing only the
exact cards for that facet.  Enumerate the typed Cartesian product
`protocol_scope x supported_device_roster x loop_topology`, requiring three
distinct parent/provenance receipts.  This handles a multi-facet parent without
allowing one parent to satisfy two served obligations.

### 3. Use neutral group orientation and reject ambiguity

The group supplying same-document protocol plus roster is
`identity_evidence_group`; the other is `counterpart_topology_group`.  Do not
call them device/host and do not infer their roles from query word order.

A relational signature contains:

- canonical IDs of both groups;
- protocol/roster document ID and extraction SHA;
- topology document ID and extraction SHA; and
- the three immutable parent provenance keys.

All valid assignments are grouped by orientation and governed-document pair.
If more than one orientation or more than one competing document-pair signature
survives, return no bundle with `ambiguous_relational_evidence`.  Only duplicate
assignments with the same signature may be tie-broken, using preregistered
navigation rank, exact span coordinates and parent ID in that order.

Catalog `primary` / `secondary` is not used as a technical entity role.  It
describes document coverage and can legitimately mark the panel manual that
lists a device as secondary.  Official catalog authorization, exact receipts
and unique orientation remain mandatory.  Enriching resolver output with
coverage-role metadata is deferred because it is not needed to make this
diagnostic refusal safe.

### 4. Strengthen topology to a local typed relation

The exact topology card itself, not another section of its parent, must contain
all three groups:

1. loop: `lazo`, `bucle`, `loop` or `SLC`;
2. closed path: a closed or return form;
3. detection context: a detection, detector, sensor, analog-addressable or
   addressable form.

Generic `device`, `equipment`, `panel`, network `ring/anillo` and RS485
`peripheral loop` are insufficient.  The versioned vocabulary is frozen before
the independent run.  Every build and serving revalidation reruns this semantic
guard over the exact card.

### 5. Make the run auditable and fail-closed

Trace and fingerprint:

- full hydrated candidate pool and its order;
- every `(parent, facet)` projection;
- every typed assignment accepted or rejected, with reason;
- relational signatures and ambiguity result; and
- the final exact-three bundle receipt.

Append all three rows atomically or none.  HYQ prose remains navigation metadata
and is never evidence.

## Alternatives considered and rejected

1. **Raise global serving limits.** It increases context and noise without
   enforcing the relation.
2. **Tune greedy facet weights.** Per-row scores can still discard a required
   member of the only valid set.
3. **Use an LLM/agentic reranker.** This bounded provenance decision is
   deterministic; a model adds cost, variability and unsupported inference.
4. **Infer roles from Spanish syntax or product type.** Fragile across natural
   queries, languages and 30+ manufacturers; neutral roles plus unique
   orientation are safer.
5. **Treat catalog primary/secondary as host/device.** Those fields express
   document coverage, not the role in this query.
6. **Relax device-token binding to headings/neighbors.** This would recover
   `SGMCB200` by weakening the exact evidence contract.  It remains an upstream
   chunk-lineage gap.
7. **Add QID/product/manufacturer rules.** Direct overfit.
8. **Treat the bundle as compatibility proof.** Three separately true facts do
   not prove interoperability; the only authorized output here is a
   source-bound refusal.

## BP, structural nature and scalability

The selector operates on a constrained evidence set rather than independent
chunks: broad bounded navigation, typed exact-span atoms, relational validation
and minimal serving.  It is structural and manufacturer-agnostic.  With at most
six parents and at most one selected card per required facet per parent under
the frozen evidence config, there are at most 120 ordered typed parent
assignments before validation.  All work is deterministic and local until the
minimum read-only probe.

## Known gaps and risks

- Development material is exposed and establishes no generalization.
- Heading/content separation remains a false-negative source.
- Earlier navigation can still miss a source; that remains retrieval miss.
- Conservative ES/EN vocabulary may make the independent result inconclusive.
- Resolver source groups can contain many official documents.  Ambiguity now
  fails closed, which favors precision over recall.
- Same-manufacturer and explicitly cross-certified interoperability need a
  separate source contract; this design does not answer them affirmatively.
- A three-example independent pilot cannot validate 30-manufacturer coverage.
- Official funnel metrics remain unchanged without a later frozen assessment.

## Evaluation hygiene and execution order

1. Freeze corrected development cohort, real hard negatives and all pre-change
   hashes.
2. Obtain fresh adversarial GO-to-build on this v2 contract.
3. Implement deterministic unit attacks and local replay only.
4. Run the k=3..6 development curve; freeze code, config and chosen k.
5. Build the independent exclusion closure from S126/S127 seeds using the
   preregistered product relation and near-duplicate rules in the cohort.
6. Select independent products from metadata only; freeze natural query
   templates before reading source contents.
7. Adjudicate source eligibility without selector output; then seal the
   adjudication artifact.
8. Run the independent replay twice.  Do not expand vocabulary, change k or
   alter exclusions after seeing results.
9. Only after local GO, run a minimum GET-only live probe with zero model calls
   and zero writes.
10. Obtain final adversarial review.  Keep the flag off and assign zero OK
    credit unless separately authorized.

## Frozen pre-change inputs

| Input | SHA-256 |
| --- | --- |
| `src/rag/compatibility_bundle_coverage.py` | `2e03b4af1448fce57f219e4ef128a393687ae32f5a3bbf4eb6b8726d4fc5ab0c` |
| `src/rag/doc_scoped_hyq_coverage.py` | `d938d4ce43757627e9db4c99dab948ef6b6dcb28cf82c7ee102edf359c65c43b` |
| `config/retrieval_facets_compatibility_candidate_v2.yaml` | `b2b600eb78b0817a746a0fd1249c243a8046f8cdf4e5c11435088b6096bae6ad` |
| `config/evidence_coverage_compatibility_candidate_v1.yaml` | `f6c73113746608d8fff567f6fa23a2415433c429c77f5e3121429b77f453d937` |
| `tmp/s117_m25/derived_snapshot_v2.jsonl.gz` | `a825e4dd02b918ddafebab4419cb416b6edc5f1b823a7a9d423f96718d7b6217` |
| `data/catalog/doc_map.jsonl` | `992c62c21b5772caebf09f422adca20ffe4035143861ca931e5198e820572c82` |
