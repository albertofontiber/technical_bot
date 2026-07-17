# S158 table-preamble closure design v1

## Decision

Evaluate a deterministic post-rerank context-closure lane for Markdown tables
whose heading or applicability notes were separated from their rows by the
existing `chunks_v2` boundary. The lane repairs an evidence-packet boundary; it
does not retrieve a new document, infer a missing qualifier, or generate prose.

## Eligibility contract

A candidate preamble is eligible only when all conditions hold:

1. A chunk already present in the protected reranked prefix begins with a
   Markdown pipe table.
2. The candidate is exactly `chunk_index - 1` in the same `document_id` and
   immutable `extraction_sha256`.
3. The candidate contains the same normalized table heading as the served
   chunk's `section_title`.
4. Only the exact source span from that final matching heading to the end of
   the candidate may be appended. The span must be bounded and non-empty.
5. The protected prefix is byte-identical and no candidate may be admitted
   through product names, QIDs, benchmark facts, expected values or model
   output.

The query relevance of the preamble is inherited from the already reranked
table. The preamble cannot introduce an unrelated document, revision or table.

## Runtime shape

- read-only hydration from `chunks_v2`;
- one bounded same-blob predecessor lookup;
- no LLM, embedding, reranker or database write;
- exact-span receipt revalidated at the serving seam;
- at most one preamble per protected table chunk and at most two per answer;
- fail open: an invalid or unavailable predecessor changes nothing.

The mechanism is a new versioned lane. It does not relax the existing
structural-neighbor selector, whose purpose is query-aligned fact discovery.

## Validation

Development verifies the known FAAST split only after this contract is frozen.
Generalization uses a source-first corpus cohort selected mechanically from
non-target documents before reviewing semantic usefulness. The cohort must
contain multiple manufacturers and table types.

Promotion requires:

- exact identity and adjacency for every emission;
- exact preamble receipt for every emission;
- 100% table-heading continuity;
- no unrelated prose after the matched heading;
- zero protected-prefix mutation;
- deterministic output;
- full existing tests and protected regression unchanged;
- no answer/KPI credit until an answer probe and frozen funnel reconciliation.

## Stop rules

Stop without serving integration if corpus generalization is too sparse, any
cross-table or cross-blob attachment occurs, bounded exact spans cannot be
maintained, or protected answers regress. Do not add FAAST-specific strings or
loosen adjacency to make the target pass.

