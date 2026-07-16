# S127 compatibility generalization design v3

## Status

This is the self-contained build contract that supersedes v1 and v2.  V1 was
rejected for unbound roles, contaminated exclusions, a circular metric and an
underspecified triplet selector.  V2 closed those issues but was rejected
because its positive detection-context requirement regressed the exact S126
topology receipt and because its ambiguity signature mixed document-level
ambiguity with bundle-level receipts.

No S127 build has started.  S126 remains two retrieval-stage transitions and
zero facts moved to OK.  S127 evaluates only a
`three_facet_diagnostic_refusal_bundle_opportunity`; it neither proves
interoperability nor earns official funnel credit.

## Independent pilot gate

Eligibility is adjudicated from exact source spans and sealed before selector
execution.  An eligible opportunity has same-document protocol and official
roster evidence for one resolved group, field-loop topology evidence for the
counterpart group, three distinct parent receipts, and no explicit proof of
direct interoperability between the queried products.

The default-off integration gate requires 100% receipt/catalog precision, zero
partial bundles, zero false topology controls, at least 80% recall over eligible
opportunities, and at least three eligible opportunities across three
relation-closed OEM/rebrand classes and two counterpart classes.  Otherwise the
result is `INCONCLUSIVE`.  This is a pilot, not proof across 30 manufacturers.

## Normative selector contract

1. Generic HYQ behavior and its serving limit remain unchanged.
2. Compatibility navigation may return an internal, non-servable ordered pool.
   Development evaluates prefixes `k=3,4,5,6` and freezes the smallest k that
   achieves maximum valid recovery with zero negative acceptance.  Independent
   data cannot tune k.
3. Project every parent into `(parent_id, facet)` atoms containing only exact
   cards for that facet.
4. Enumerate the typed product
   `protocol_scope x supported_device_roster x loop_topology` with three
   distinct parent provenance keys.
5. The group supplying protocol plus roster is neutrally named
   `identity_evidence_group`; the other is `counterpart_topology_group`.
   Resolver order and query syntax never assign device/host roles.
6. Protocol and roster must share canonical group, document ID and extraction
   SHA.  The roster's exact receipts must name that group's governed token.
   Topology must belong to the other canonical group.
7. Define two separate immutable objects:

   - `ambiguity_key`: canonical orientation plus protocol/roster document ID and
     extraction SHA plus topology document ID and extraction SHA;
   - `bundle_receipt`: ambiguity key plus all three parent IDs, chunk indexes,
     exact card offsets and quote hashes.

8. More than one `ambiguity_key` is `ambiguous_relational_evidence` and returns
   no bundle.  Alternatives within one key are equivalent document-level
   evidence and may be ranked by navigation rank, then exact span coordinates,
   then parent ID.  The chosen `bundle_receipt` is unique and revalidated at
   serving.
9. Append exactly three rows atomically or append none.  HYQ prose is never
   evidence.  Cross-manufacturer output remains a deterministic source-bound
   refusal; the provider is not called for an incomplete or invalid bundle.

Catalog `primary/secondary` is intentionally not treated as a technical query
role: it describes document coverage and may legitimately label the panel
manual that lists a device as secondary.  Exact catalog authorization and the
unique document-level ambiguity key are the authority controls.

## Normative topology guard

The exact `loop_topology` card must contain:

- a loop form: `lazo`, `bucle`, `loop` or `SLC`; and
- a closed-path form: closed or return.

The same exact card is rejected if it contains a competing non-field-loop
meaning: `red`, `network`, `ring`, `anillo`, `RS485`, `peripheral` or `serial`.
The veto is intentionally conservative.  It preserves both frozen positive
receipts without constructing a new neighboring-span mechanism, while rejecting
the frozen network-ring receipt that otherwise satisfies loop plus closed.

The guard runs both during build and serving revalidation.  Vocabulary is
versioned and product/manufacturer/QID-free.  Real exact receipts are frozen in
`evals/s127_compatibility_development_cohort_v3.yaml`.

## Required audit receipts

Every run fingerprints the ordered hydrated pool, each projected atom, every
typed assignment and rejection reason, all ambiguity keys and the final bundle
receipt.  Two local runs must be identical.  The independent exclusion closure
(products, rebrands, aliases, sources, documents, extraction/source-PDF hashes
and revision/translation families) is materialized and frozen before selecting
the cohort, not merely recomputed from an algorithm.

## Alternatives rejected

- Global context growth and greedy weight tuning do not enforce a relation.
- An LLM/agentic reranker adds cost and unsupported inference to a deterministic
  bounded decision.
- Query-syntax roles and catalog primary/secondary are not reliable device/host
  semantics.
- A new positive field-context card or neighboring-chunk join is not justified:
  it would change the S126 evidence contract and require its own upstream design.
- QID/product/manufacturer rules are overfit.
- This three-facet bundle is not affirmative compatibility proof.

## Risks declared up front

- Heading/content separation remains fail-closed (`SGMCB200`).
- The semantic veto can reject a legitimate field loop whose exact card also
  discusses a network; precision is preferred and the case remains retrieval
  miss.
- A non-network technical loop with loop+return vocabulary may still be a false
  topology candidate.  One such exact-card negative remains a P2 expansion
  requirement before any external-generalization claim, but does not authorize
  weakening the current hard-negative gate.
- Six parents may still be insufficient; the development curve only chooses the
  smallest tested bounded pool and does not prove corpus-wide recall.
- Official funnel metrics remain unchanged without a later frozen assessment.

## Cheap execution order

1. Fresh adversarial GO-to-build on v3.
2. Deterministic code/config/tests only.
3. Two local development replays including k=3..6 and frozen controls.
4. Freeze code, config, selected k and materialized exclusion closure.
5. Metadata-only independent selection; freeze natural ES/EN query templates.
6. Source-first adjudication without selector output; seal receipts.
7. Two identical independent local replays.
8. Minimum GET-only live probe only after local GO: zero model calls and writes.
9. Final fresh adversarial review; flag stays off and OK credit stays zero.

## Pre-change hashes

The six pre-change inputs and hashes in v2 remain normative and were verified by
the round-1 reviewer.  In particular:

- compatibility implementation: `2e03b4af1448fce57f219e4ef128a393687ae32f5a3bbf4eb6b8726d4fc5ab0c`;
- document-scoped HYQ: `d938d4ce43757627e9db4c99dab948ef6b6dcb28cf82c7ee102edf359c65c43b`;
- frozen snapshot: `a825e4dd02b918ddafebab4419cb416b6edc5f1b823a7a9d423f96718d7b6217`;
- catalog map: `992c62c21b5772caebf09f422adca20ffe4035143861ca931e5198e820572c82`.
