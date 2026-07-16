# S116 section-lineage contract v2

Status: amended after adversarial NO-GO on v1; frozen before implementation.

## Objective and terminology

The corpus baseline found 10,448 continuations whose `section_title` is not
present as a leaf heading in their own bytes. The local treatment preserves the
actual heading occurrence that generated that metadata. Its receipt provides
**internal consistency and resolvability inside the in-memory extraction
record**, not cryptographic provenance of membership in a persisted raw file.

Strong provenance remains a later contract: hash the complete raw extraction
artifact, persist stable coordinates, and re-resolve the heading against that
exact artifact at ingestion and use time. The existing `extraction_sha256` is a
PDF hash and must not be presented as the raw-artifact hash.

## Immutable occurrence identity

Each syntactic Markdown heading occurrence creates a distinct immutable
`SectionAnchor`:

- exact parser-consumed `heading_text`;
- parsed `title` and `level`;
- `source_page`, which may be `None`;
- unique monotonically increasing `source_block_index` in the flattened
  document;
- `heading_sha256`, an internal tamper check over `heading_text`.

Internal verification reparses `heading_text`, checks exact title and level,
checks its hash and coordinates, and resolves `source_block_index` against the
real flattened heading block. `page=None` is valid when that block resolves and
also has `page=None`.

Identical title/level text at two block indexes always creates two identities.
This safely distinguishes genuine repeated siblings. A repeated running header
also starts a new identity; without reliable layout evidence, the system fails
closed and measures any added fragmentation rather than pretending continuity.
Page-crossing content retains the original identity only when no new heading
occurrence intervenes.

## Full lineage and source span

Every `_Block` carries its full tuple of active anchors. Its compatibility
`path` is derived from that tuple. Oversized pieces retain the exact same full
lineage and original source block index.

Every `Chunk` carries:

- `section_lineage`: the common prefix of the lineage of **every** source block
  it contains, including empty lineages;
- `section_anchor`: the last anchor in that tuple, or `None`;
- inclusive `source_block_start` and `source_block_end` coordinates.

If any block is truly unsectioned, it contributes an empty lineage and the
common lineage is empty. A mixed preamble plus section must not acquire the
section's identity by ignoring the preamble. `section_title` and `section_path`
are derived atomically from `section_lineage`; a title without a resolvable
anchor is an invariant failure.

The local audit resolves every anchor in the full lineage against the actual
flattened record and recomputes the common lineage for the complete source
span. This detects orphan, stale and arbitrarily chosen anchors.

## Cleanup

Backward merge of a short chunk is allowed only when the complete ordered
lineage identity tuple matches. Anchored-to-unanchored and differing lineages
never merge. Two chunks with empty lineage may merge. The existing prohibition
on merging flow diagrams remains mandatory.

Identity uses heading occurrence coordinates and hash, never title/path text.
Thus siblings with identical names and running-header occurrences remain
separate.

## Exact content conservation

For every successfully processed extraction filename, baseline and treatment
must have the same SHA-256 over the ordered output stream
`"\n\n".join(chunk.content)`. Equality per document detects output omission,
duplication, mutation and reordering while allowing chunk boundaries to change.
Aggregate character counts remain diagnostic only.

## Required test matrix

1. Same-page and page-crossing continuations without a repeated heading.
2. `page=None` anchor resolution.
3. Running heading repeated on a later page creates a new identity.
4. Genuine sibling with identical title/level creates a new identity.
5. Same title at different levels creates a new identity.
6. Mixed anchored and truly unanchored blocks yield empty common lineage.
7. Mixed siblings yield only their true common parent.
8. Every oversized piece preserves full lineage and source index.
9. Cleanup compares full lineage, blocks anchored/unanchored and different
   identities, permits identical lineage, and never merges flow diagrams.
10. Source block indexes are unique, contiguous and monotonically increasing.
11. Tampered hash/title/level/index and stale/orphan anchors fail resolution.
12. Chunk output contains no synthetic heading and corpus replay is byte-for-byte
    deterministic.

## Boundaries

No schema, index mapper, retrieval, reranking, synthesis, prompt, reingestion,
serving, deployment, database, network or model change is authorized here.
Passing the v2 A/B gate authorizes only creation of a fresh held-out validation.
