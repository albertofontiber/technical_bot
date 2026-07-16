# S116 section-lineage contract v1

Status: frozen for adversarial review before implementation.

## Observed upstream failure

The frozen local baseline replays the current chunker over every JSON in the
already-paid extraction store. Of 28,907 chunks carrying a `section_title`,
10,448 (36.1%) do not contain their leaf heading in their own content bytes;
2,485 of those continuations have a numbered section title. This occurs across
multiple detected manufacturers. The single processing error is the store's
`_failures.json` manifest rather than an extraction record and remains in both
arms of the comparison.

This does **not** mean the metadata is false. It means the current `Chunk`
object cannot distinguish a title inherited from a real earlier heading from a
naked or stale metadata string. That distinction blocked S115 from using an
otherwise useful procedure safely.

Baseline evidence:

- Store manifest SHA-256: `752c044be1531d5bc2e2879f79acf1dbeffabcbeb9bb9d16f5e14a5676aa5810`
- Chunker SHA-256: `58be85e8cdf2cfac475e7f7cd23639b04f7b22a1c60938ffec86e76cb2c60985`
- Records processed/errors: `1068/1`
- Total chunks/content characters: `30315/62828879`

## Design objective

Preserve an immutable, locally verifiable receipt for the exact Markdown
heading from which each section identity was inherited, without copying that
heading into continuation content and without changing retrieval or serving.

## Contract

### `SectionAnchor`

Every parsed Markdown heading creates one immutable anchor with:

- `heading_text`: the exact normalized Markdown line consumed by the parser,
  including its `#` prefix;
- `title` and `level`: values parsed from that same line;
- `source_page`: extraction page carrying the line;
- `source_block_index`: monotonically increasing index in the flattened
  document, disambiguating repeated/running headings;
- `heading_sha256`: SHA-256 of the UTF-8 `heading_text`.

An anchor is internally valid only when the line reparses to the stored title
and level, the hash matches, and the source coordinates are well-formed.

### Block lineage

The flattening pass carries the full tuple of active `SectionAnchor` objects on
every syntactic block. The existing `(level, title)` path remains a derived
compatibility view; it is not an independent authority.

### Chunk lineage

The common anchor lineage of all blocks in a chunk defines its section path.
The last common anchor becomes `Chunk.section_anchor`. Therefore:

- a continuation split by size retains the exact earlier heading receipt;
- a section crossing a page retains the receipt from the page where its heading
  appeared;
- a chunk containing sibling subsections receives only their common parent
  anchor;
- a chunk with no common anchored ancestor has no section metadata or anchor.

`section_title` and `section_path` are derived from the common lineage in the
same operation. A non-null `section_title` without a valid `section_anchor` is
an invariant violation in the treatment arm.

### Cleanup boundary

A sub-minimum chunk may merge backward only when both chunks have the same
section identity. Anchored identity is the tuple
`(source_page, source_block_index, heading_sha256)`. Two genuinely unsectioned
chunks may merge; anchored and unanchored chunks, or chunks with different
anchors, never merge.

This closes a separate structural defect in the current cleanup pass, which can
merge a short new section into the previous section while retaining the
previous metadata.

## Evidence and trust boundary

The treatment is an in-memory shadow contract. It does not claim that a
heading hash alone proves membership in a persisted extraction artifact.
Production-grade provenance later requires a separate envelope containing:

- an `extraction_artifact_sha256` over the raw extraction JSON (distinct from
  the existing PDF SHA stored as `extraction_sha256`);
- stable source coordinates sufficient to resolve the heading in that exact
  artifact;
- verification at ingestion and before any retrieval-time use of the receipt.

No schema or index mapper is changed in S116's local treatment. That envelope
and its versioned migration require a separate gate after fresh validation.

## Explicit non-goals

- Do not prepend or duplicate headings in chunk content.
- Do not alter target/max chunk sizes.
- Do not tune for any S114/S115 fact or manufacturer.
- Do not change embeddings, retrieval, reranking, synthesis, or prompts.
- Do not query the database, call a model, or use the network.
- Do not reclassify any fact as OK.

## Required tests before corpus replay

1. Same-page continuation inherits a valid anchor.
2. Oversized splits all inherit the same valid anchor.
3. Page-crossing continuation points to the original heading page.
4. A short new sibling section never merges into the previous sibling.
5. Same-section short continuations may merge without changing identity.
6. Mixed sibling headings resolve to their common parent, never an arbitrary
   child.
7. Heading-free content has no anchor.
8. Receipt tampering fails validation.
9. Chunk content is byte-for-byte composed only from original parsed blocks;
   no synthetic heading is inserted.

## Gates and staged release

The frozen `s116_raw_store_ab_prereg_v1` treatment gate applies to the exact
same store manifest. Passing it produces only an engineering GO for a newly
sealed held-out validation. It does not authorize database migration,
re-ingestion, index or serving integration, production rollout, or an OK-count
claim.

Rejected shortcuts:

- copying headings into every continuation, because it changes retrieval text
  and can manufacture apparent relevance;
- trusting `section_title` alone, because S115 showed that it lacks byte-backed
  provenance;
- fetching neighboring chunks at query time, because it couples correctness to
  mutable index state and adds latency;
- manufacturer-specific heading rules, because they do not scale to the target
  corpus.
