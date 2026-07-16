# S128 explicit technical-relation extractor design v1

## Decision and boundary

Build only a deterministic **offline shadow extractor** for relations that a
manual states explicitly.  It runs upstream of retrieval over the same
versioned raw extraction blocks and section lineage used to materialize
`chunks_v3`.  It does not run over arbitrary nearest-neighbour chunks, call a
model, write to the database, change production, or earn fact/OK credit.

S127 is permanently revoked: its `protocol + roster + topology` composition
found zero valid relation in 57,646 governed combinations.  S128 must never
recreate that inference in another form.  In particular:

```text
A uses protocol P + B uses protocol P != A is compatible with B
```

No transitivity or reciprocity is assumed.  `A supports B` does not create
`B supports A`; `compatible_with` remains directional unless one exact source
asserts both directions.

## Evidence supporting a build pilot

The preregistered zero-cost census covered 12 documents across four
relation-closed OEM/rebrand classes.  It found 11 eligible explicit relations,
100% exact candidate receipts, zero hard-negative acceptances and identical
bytes across two runs.  This is only development evidence; it authorizes this
design, not a generalization claim.

## Input contract

The extractor consumes ordered raw extraction blocks plus their frozen S116/S117
lineage:

- `raw_artifact_sha256`, `extraction_sha256` and `source_block_index`;
- block text and block-text SHA-256;
- exact section lineage, including each heading block receipt;
- catalog-authorized document IDs and product aliases;
- the versioned technical-entity registry described below.

It must not treat generated `context`, HYQ prose, embeddings, reranker scores or
LLM summaries as evidence.  A flattened chunk may be used only in replay to
locate an already frozen raw-block span; the production candidate contract is
raw-block-first.

## Versioned entity registry

Products resolve through canonical catalog IDs and relation-closed aliases.
Non-product objects use typed IDs in a separate, reviewed registry:

- `protocol:<id>` and `protocol-class:<id>`;
- `device-class:<manufacturer-or-standard>:<id>`;
- `component-class:<id>`;
- document-local `terminal-set:<governed-family>:<id>`.

Every registry item contains canonical bilingual aliases, type, provenance,
version and ambiguity status.  The parser may resolve an object only when an
exact alias occurs inside its evidence span.  It may not invent a registry item
from a benchmark answer or from another relation.

## Output edge contract

Each accepted edge contains exactly:

1. contract/version and deterministic edge ID;
2. normalized `subject_id`, `predicate`, normalized `object_id`;
3. `polarity` (`positive` or `negative`);
4. ordered qualifiers, each with an exact receipt;
5. document, extraction and raw-artifact hashes;
6. subject, predicate, object and qualifier block/span receipts;
7. section-lineage receipt if heading scope binds an anaphoric subject;
8. parser/config/entity-registry hashes;
9. ambiguity and resolution status;
10. `direct_relation=true` and `derived_relation=false`.

Allowed predicates in v1 are directional: `supports`, `compatible_with`,
`listed_for`, `requires`, `uses_protocol`, `connects_to` and `excludes`.
Unknown predicates are rejected, not coerced to the nearest label.

## Deterministic extraction pipeline

1. **Resolve the governed document scope.** Reject ambiguous catalog bindings.
2. **Create bounded structural windows.** A window is one sentence, list item,
   table row with its column headers, or a section heading plus one immediately
   governed item. It never crosses a section boundary.
3. **Bind the subject.** Priority is exact subject mention in the window, then
   exact enumeration in the active heading. Document-level primary product is
   insufficient for pronouns such as “this device” when the document covers
   multiple products.
4. **Match a predicate template.** Templates are bilingual and generic; no QID,
   expected answer, manufacturer or product literal is allowed in parser code.
5. **Resolve the object from an exact alias.** Generic words such as “panel”,
   “device” or “compatible protocol” require an explicit typed-registry match;
   otherwise the candidate remains unresolved.
6. **Preserve direction, polarity and qualifiers.** Negation, “only”, firmware,
   region, base type, resistance and conditional clauses are part of the edge,
   never discarded.
7. **Revalidate receipts independently.** Recompute every block/span/hash and
   registry/catalog binding.  Append the complete edge atomically or none.
8. **Deduplicate only identical semantics and provenance.** Multiple source
   attestations remain separate evidence receipts for one semantic edge.

The parser produces a disposition for every lexical/structural candidate.  A
candidate with unresolved subject/object, unclear direction, cross-section
evidence or unsupported composition fails closed.

## Development and independent gates

The 12 census documents form exposed development data.  The 11 adjudicated
relations are the development gold set.  Before implementation, freeze a
metadata-only held-out set excluding:

- all S128 development documents, extractions and source-PDF hashes;
- their four relation-closed classes and aliases;
- translations/revisions and shared document families.

The held-out set must contain at least five source-adjudicated eligible edges
across three unseen relation-closed classes; otherwise the result is
`INCONCLUSIVE`, never GO.

Both development and held-out require:

- precision `100%` and zero hard-negative edges;
- exact provenance `100%`;
- recall at least `80%` over eligible source-first edges;
- zero composed, reciprocal or transitive compatibility edges;
- two byte-identical executions;
- no model/network/database calls or writes.

Development may tune only generic templates and ontology aliases.  Held-out
results cannot tune the extractor; a failed held-out gate requires a new
version and new independent cohort.

## Retrieval seam after an eventual held-out GO

An accepted edge would first live in a local shadow JSONL relation index.  A
later, separately reviewed retrieval experiment may fetch exact relation edges
by resolved subject/object and predicate intent.  The edge brings its original
source evidence; it cannot serve as a compatibility answer by itself when its
predicate is merely `uses_protocol`, `requires` or `connects_to`.

Only an explicit `compatible_with`/`supports` edge matching the query direction
and qualifiers may move a fact past the retrieval stage.  Rerank and synthesis
are then measured independently downstream.  A retrieval transition is valid
stage improvement, but it is not an OK until the complete frozen funnel says so.

## Alternatives rejected

- An agentic/LLM relation extractor is unnecessary for the first pilot and
  adds cost, non-determinism and unsupported inference risk.
- Increasing context or top-k repeats S127 and cannot create an absent edge.
- Treating catalog `rebrand-of` as technical compatibility confuses commercial
  identity with an installation claim.
- Product-specific regexes or adjudicated candidate IDs in runtime are
  benchmark overfit.
- Storing only prose summaries loses direction, polarity, qualifiers and exact
  provenance.

## Risks and cheapest failure modes

- Section headings can incorrectly scope a pronoun across multi-product
  documents.  Require exact heading enumeration and same-section lineage.
- Tables may separate row objects from headers.  Bind only within one table
  block whose header receipt is explicit.
- The entity registry may be too sparse.  Missing objects reduce recall and
  remain unresolved; they never justify free-text edge creation.
- LlamaParse may split or corrupt a source assertion.  Record an upstream
  extraction/lineage miss rather than relaxing spans.
- The census is development-exposed.  No architecture claim extends beyond the
  independent gate.

## Cheap execution order

1. Fresh adversarial GO/NO-GO on this design.
2. Freeze the development gold receipts and metadata-only held-out exclusions.
3. Implement the local entity registry, parser, receipts and unit attacks.
4. Run development twice; stop immediately on precision/provenance failure.
5. Source-first adjudicate and seal held-out eligibility without parser output.
6. Run held-out twice.  Do not tune on the result.
7. Only after held-out GO, design a separate offline shadow retrieval replay.
