# S141 source-bound technical obligations design v1

## Decision

Build a versioned, deterministic obligation extractor for explicit operational
relations already present in the exact context served to answer generation.
This is a synthesis mechanism: it cannot retrieve absent evidence and it earns
no retrieval credit.

The implementation reuses the fail-closed principles of S128, but not S128's
product-compatibility ontology. S141 covers operational relations such as:

- a condition or prerequisite bound to an action;
- a safety isolation or verification requirement;
- a bounded range/threshold with its scope and delay;
- fields that must be configured together;
- an explicit cardinality bound to the described option family; and
- a special state/value bound to its operational consequence.

## Evidence boundary

An obligation is eligible only when all of the following hold:

1. Its complete statement is an exact span of one served chunk, or a bounded
   composition of exact spans from served chunks for the same resolved product.
2. The chunk is aligned to the query by exact model identity, a bounded numeric
   family rule, or a versioned governed-catalog source attestation produced by
   retrieval. A product-name substring is not an attestation.
3. Every required value, qualifier, condition and action is present in the
   source span. Missing qualifiers remain an upstream/source-contract miss.
4. The query has a matching generic intent. Merely finding safety or numeric
   prose in an unrelated manual section does not create an obligation.
5. No QID, benchmark fact ID, manufacturer, product literal, candidate ID or
   expected answer is present in runtime extraction rules.

## Runtime architecture

The extractor lives in a separate module and returns typed candidates with:

- relation kind and version;
- exact fragment/candidate/span provenance;
- source statement;
- atomic semantic anchors; and
- a deterministic semantic identity used for deduplication/conflict rejection.

`answer_planner` converts candidates into its existing `AnswerObligation`
envelope. Only S141 contract calls may emit or enforce the new kinds. S119-S124
historical contracts remain byte-stable.

The governed identity seam is explicit. When `IDENTITY_RESOLVE=on`, retrieval
may attach a query-bound receipt to chunks whose `source_file` belongs to the
catalog-authorized source set. The planner verifies the query hash, source file,
catalog contract and positive expansion before accepting a named sibling. It
does not call the resolver implicitly or infer family membership from text.

## Validation and rendering

Each enforceable kind has a bounded, polarity-aware local validator. Listing
the right words in unrelated paragraphs is insufficient. A generated answer
must preserve the relation and may not contradict it later.

If first-pass generation fails the contract, the existing source-bound renderer
may reconstruct only from eligible obligations and exact citations. If the
query core is not represented, it fails closed.

Every output-affecting version is included in the answer cache identity:
planner, extractor, identity receipt, enforcement policy, validator and
renderer. No answer cached under S122 can be reused as an S141 answer.

## Frozen development target

The latest reconciled funnel contains 18 provisional synthesis misses. S141
must first audit their evidence boundary:

- five FAAST channel-2 qualifier misses have no explicit two-channel
  applicability qualifier in the served context and are therefore upstream
  source-contract misses, not S141 repair targets;
- thirteen claims across PEARL, AM-8200, ASD535 and RP1r have the decisive
  relation already served and form the S141 development target.

This reclassification is provisional until the audit artifact verifies exact
source spans and counts. It cannot increase OK by itself.

## Gates

Local development gate:

- exact source receipts: 100%;
- target relation extraction: 13/13 or explicit conservative residuals;
- target source-incomplete rejection: 5/5;
- hard-negative acceptance: 0;
- byte-identical extraction across two runs;
- no model, network or database call;
- all pre-existing tests and protected answer regressions pass.

Independent/generalization gate:

- real non-target manuals or frozen questions selected without inspecting
  extractor output;
- zero cross-product/cross-section relations;
- no new obligation on unrelated intent negatives;
- all emitted positive obligations manually traceable to exact spans;
- a failed gate creates a new version; held-out output is not tuning data.

Only after local gates pass may a minimal answer-generation probe run on one
representative question per relation family. Frontier models are reserved for
one final adversarial review, not iterative implementation.

## Non-goals

- No `chunks_v3` migration. S140 rejected the wholesale candidate on symmetric
  semantic MRR.
- No prompt-only insertion of missing FAAST qualifiers.
- No online agentic planner over the full context in v1; its recurring token,
  latency and nondeterminism costs are not justified before deterministic
  coverage is measured.
- No database write, deployment, push or production KPI change in this phase.

## Stop rules

Stop and retain the result as diagnostic if precision/provenance fails, if the
new kinds require product-specific rules, or if protected answers regress. A
partial high-precision mechanism is preferable to relaxing the evidence or
identity contract.
