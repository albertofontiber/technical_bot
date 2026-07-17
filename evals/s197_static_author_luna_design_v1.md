# S197 — fresh real-document static author and Luna semantic gate

## Purpose and causal question

S197 is the first real-document evaluation authorized by S196's synthetic transport
GO. It asks whether the exact static rectangular schema that compiled once on a
synthetic fixture can construct a clean author cohort with cross-provider,
excerpt-internal validation on 14 structurally disjoint `chunks_v2` documents. It does
not retry S194 or S195 and does not
open the S193 planner, protected targets, runtime integration or production.

This is an upstream author-contract test, not a fact-improvement claim. A GO means
only that a separate S198 may measure the planner on the sealed cohort with the
existing 90% recall / 80% precision / 75% complete-question thresholds. A NO-GO
stops before that downstream stage. S197 has zero official or diagnostic fact credit
in either case.

The decision objective is binary: determine whether replacing S195's dynamic grammar
with S196's static transport eliminates author-contract failures strongly enough to
produce one usable, Luna-screened diagnostic cohort without relaxing population or
semantic gates. The primary endpoint is `GO_STATIC_AUTHOR_LUNA_SCREENED_COHORT_SEALED`,
defined as every preregistered population check, every excerpt-screening check and the
receipt-binding check being true in the single run. There is no fact delta in S197; its
only positive decision is permission to preregister, not execute, S198.

## Fresh source freeze

`scripts/s197_build_fresh_source_packet.py` performs two bounded, GET-only full scans
of `chunks_v2`. Their row counts and complete ordered-row fingerprints must be
identical before selection continues; a count-only match is insufficient. This is a
stability receipt across two scans, not a transactional database snapshot. Selection
is deterministic from seed `s197-static-author-luna-fresh-v1` and requires:

- exactly 14 items, documents and manufacturers;
- seven table and seven prose excerpts;
- no document, source-file or manufacturer/product-pair reuse from the frozen
  development/evaluation packets, now including both S194 and S195;
- no protected target document or chunk UUID;
- no exact protected-target content or extraction-hash equivalent;
- every protected target UUID must resolve as a chunk and/or document in both stable
  scans; an unresolved target aborts source freeze instead of silently reducing exact-
  equivalence coverage;
- an evidence-unit manifest sealed before any model sees the packet;
- zero database writes.

The source contract recomputes the packet hash, cardinalities, structural disjointness,
internal target-equivalence receipt consistency, double-scan linkage and every evidence
unit. The target-equivalence rows are derived by the source builder from the stable
live read and linked to its fingerprint; the offline runner does not independently
re-query those rows. S194 and S195 documents are checked explicitly as well as through
the accumulated prior-packet contract. The source packet is created exclusively and
cannot replace an existing packet.

“Fresh” in this evaluation means disjoint document/chunk IDs, source filenames,
manufacturer/product pairs and exact protected-target content/extraction hashes.
Semantic near-duplicate and OEM-relabel overlap against prior packets are explicitly
`NOT_MEASURED`; S197 does not claim absence of either.

## Clean author boundary inherited from S196

S197 imports the provider schema from the frozen S196 authority without modifying it:
four always-present point objects, each with `active`, `claim`, `facet` and three
always-present support strings. The provider grammar contains no arrays, refs/defs,
combinators, enums, consts or excerpt-specific values. Empty strings represent unused
fields.

The generic grammar is only the transport half of the contract. Deterministic code
enforces item identity, allowed facets, two-to-four contiguous active points when
eligible, zero active points when ineligible, one-to-three contiguous support IDs,
source membership, per-point uniqueness, inactive-slot emptiness, distinct claims and
receipt reconstruction from the sealed evidence-unit manifest. Raw author JSON is
persisted for valid and invalid responses.

The ban on dynamic source-ID enums/consts applies to the Anthropic author grammar. The
separate OpenAI screening schema may bind its returned `item_id` with a per-item
`const`; that does not reintroduce the S195 author-compiler failure.

This is deliberately not a hybrid bridge: corpus-specific invariants live in ordinary
deterministic validation, while the provider receives one stable grammar. The same
boundary can be reused for unseen documents without generating a new schema per
excerpt.

## Cross-provider, excerpt-internal semantic validation

Haiku 4.5 is the economic author. Only if the author population passes every frozen
gate does Luna `gpt-5.6-luna`, reasoning `none`, validate all 14 items. Luna is a
different provider and sees the bound source identity, the question, every authored
claim with its cited unit IDs, and all evidence units from that excerpt. Its strict
output records eligibility correctness, Spanish question language, naturalness for a
field technician, semantic non-redundancy across answer points, question answerability
and support plus best-fit facet for every active point. Luna also judges whether the
point set completely covers the material exceptions, warnings, bounds, prerequisites
and qualifiers needed for that question within the excerpt. Any invalid Luna output,
wrong eligibility,
non-Spanish or unnatural eligible question, paraphrastic/redundant answer points,
incomplete point set, unanswerable eligible question, unsupported claim or wrong facet
is a NO-GO. Boolean judgements and issue strings must agree: passing/null judgements
have an empty issue, while every false judgement requires a non-empty reason.

This validates only the supplied excerpt. Luna does not see the full document or other
sources, so document-wide omissions, multi-document contradictions, OEM relabels and
Spain-vs-US profile conflicts remain `NOT_MEASURED`. The sealed output is therefore a
Luna-screened diagnostic cohort, not a complete multi-document gold authority. Judge
accuracy calibration and human agreement are `NOT_MEASURED`; cross-provider separation
proves operational independence, not semantic correctness.

Because Haiku chooses both question and points, coverage of all technical opportunities
in an excerpt and question-difficulty representativeness are also `NOT_MEASURED`. S198
may diagnose planner behavior only on this screened cohort; it cannot generalize the
denominators beyond it or move facts.

Known corpus/input failure modes are also outside this gate and explicitly
`NOT_MEASURED`: OCR loss, scan- or diagram-only evidence, seven-segment/display
interpretation, and ES↔EN vocabulary/translation coverage.

Population gates are fixed before source selection and execution:

- at least 12 eligible questions from at least 12 manufacturers;
- at least five table and five prose questions;
- at least 24 answer points;
- zero invalid author outputs;
- zero invalid semantic-validator outputs;
- all eligible questions Spanish and natural for a field technician;
- all answer points semantically distinct, not merely different under `casefold`;
- all point sets complete for their question within the excerpt;
- all active claims fully supported and assigned the best generic facet;
- zero excerpt-unsupported claims and zero excerpt-unanswerable eligible questions.

No threshold is adjusted after seeing the cohort. The same cohort is never retried or
rebuilt. Planner thresholds remain 90/80/75 but are not executed in S197.

The screened-cohort seal contains the authored items, all Luna reviews and the
physical SHA-256 of the complete Luna receipt artifact. Each receipt binds the authored
item hash, exact semantic input hash, output-schema hash, raw response and normalized
review. The gate recomputes those hashes, reparses and renormalizes raw output, and
requires exact per-item equality before sealing the aggregate decision.

## Execution and failure semantics

Execution freezes Anthropic SDK `0.97.0` and OpenAI SDK `2.30.0` at their serializer
boundaries. Both clients use `max_retries=0`. The current-workspace exclusive lock is
created before either client is constructed or any provider request is sent. Separate
immutable prepaid checkpoints are written after token-count preflight and before the
first author or Luna inference. Progress receipts use flushed same-directory temporary
files and atomic replacement; the locks and prepaid authorities are never overwritten.

The maximum is 14 Haiku inferences plus 14 Luna inferences, 28 token-count preflights,
56 provider requests and $3 internal worst-case cost. A provider interruption before
any known content failure is HOLD. Once a deterministic or semantic failure is known,
a later provider interruption cannot erase it and seals a NO-GO. Provider 400s are
stage-specific request rejections; S197 does not infer a new generic schema-compiler
claim from a lexical error string.

A budget rejection after the workspace lock is also finalized as an auditable result.
In particular, if Luna preflight makes the combined bound exceed $3 after all author
calls, S197 seals `NO_GO_SEMANTIC_BUDGET_AFTER_AUTHOR_EXECUTION` with the completed
checkpoint hashes instead of raising an unresumable bare exception.

An outer post-lock finalizer covers unexpected exceptions not handled by the explicit
provider branches, including client construction. It seals HOLD when no content
failure is known and NO-GO when completed checkpoints already contain a known invalid
or failed review. Pre-lock configuration/source failures still raise without claiming
execution authority.

The lock is explicitly local to this workspace, not a distributed idempotency service.
Repository history and the frozen execution permit make another checkout auditable,
but do not technically prevent it.

Each execution generates a random owner token and writes it atomically into the lock.
The outer finalizer seals a post-lock failure only when that exact token matches; a
process that loses the exclusive-create race cannot write HOLD/NO-GO over the winner.

## Review, non-goals and explicit lanes

Sol 5.6 xhigh is the principal frontier reviewer for design and critical closeout only.
Fable 5 is the required second independent frontier reviewer through the versioned
`scripts/adversarial_review_fable.py` runner. Its raw receipt must byte-pair to the
principal Sol review; a missing local credential or provider route leaves the duo
pending and is not represented as model unavailability or as a waiver. Neither frontier
model executes the cohort. Execution uses the economic author, economic cross-provider
validator and deterministic local code.

S197 cannot claim planner performance, target-fact improvement, runtime quality,
independent validation of the default-off S172/S188 candidates, or production readiness.
It performs no retrieval, reranking, target probe, database write, runtime change or
deployment. Railway is a demo and is not a PR/merge gate.

A GO hands S198 only inherited headline constraints: recall at least 90%, precision at
least 80%, complete questions at least 75%, exactness and deterministic-contract
checks, zero regressions of covered obligations and zero new conflicts. The result pins
the physical hash of the canonical decision authority and explicitly says these are not
yet an executable contract. S198 must preregister denominators, matching, exactness,
obligation and conflict definitions plus all authority hashes before it can run.

Authorization freezes every versioned file read or executed after the lock: source,
prior packets, protected-target authorities, S114, exclusion/UUID/source helpers,
semantic and transport authorities, unitizer, canonical decision, requirements, runner,
tests, design and Sol adjudication. Any drift aborts before provider execution.

`chunks_v3` remains an explicit separate lane with status
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. S197 neither reads, materializes nor migrates it, does
not patch individual questions, and points to the canonical roadmap instead of copying
historical metrics. A future structural v4 hypothesis remains the only legitimate
reopening trigger.
