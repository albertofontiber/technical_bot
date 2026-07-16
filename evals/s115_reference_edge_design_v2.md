# S115 — Exact reference-edge coverage (design v2)

Status: frozen contract before implementation.  Scope: local shadow only.

This version supersedes the rejected design v1.  It replaces only S114's
`explicit_intra_document_reference` facet; S114 artifacts remain immutable.
The versioned lexical and numeric contract is
`config/reference_edge_contract_v1.yaml`, SHA256
`81738aa6d9871653f7cdb33684268a50a933ddc2713bad6434926f0d1c4c0dd0`.

## Deterministic reference edge

The versioned regex emits one edge per occurrence:

`(section_number, optional_subsection, source_start, source_end, local_clause)`.

The local clause is bounded by the nearest newline or sentence punctuation in a
240-character radius.  Edges are never collapsed.  Normalized query/object and
purpose/attribute tokens use only the frozen stopword and action-prefix lists.

## Section cluster and anchor receipt

An evidence row is eligible only when:

1. candidate and served rows have the same nonempty `document_id` and valid
   64-hex `extraction_sha256`;
2. candidate `section_title` or `section_path` begins with the exact reference;
3. exactly one anchor row exists with the same strong identity and normalized
   section metadata, and `abs(anchor.chunk_index - evidence.chunk_index) <= 2`;
4. the anchor contains the exact numbered Markdown heading inside its first 240
   characters;
5. the anchor is not a TOC: reject three or more numbered dot-leader entries;
6. no intervening row contains an incompatible numbered body heading.

Zero or multiple compatible anchors is fail-closed.  A separate immutable anchor
receipt records the exact heading span.  Evidence cards contain only evidence-row
bytes.  This admits the hp002 cluster (heading chunk 171, table chunk 172) while
rejecting metadata-only TOC fragments.

## Bound obligation tuples

Question requirements are tuples, never coarse Boolean slots:

`(intent, object_tokens, attribute_tokens, required_signal)`.

- `intent` is the ordered set of matching frozen intent regexes.
- `object_tokens` are distinctive query tokens excluding generic/action tokens.
- `attribute_tokens` are distinctive tokens shared by query and local reference
  clause, plus distinctive words in the exact referenced section title.
- `required_signal` is intent-specific: numeric value+unit, structured mapping,
  diagnostic relation, or action+object in the same clause/table row/list item.

Evidence atoms use the same tuple shape.  Object binding requires at least one
object token and one attribute/purpose token inside the same atomic span.  The
identity contract may instead bind a structured model/order-code mapping to an
identity section title; this is a generic exception, not a product list.

The candidate must add at least one bound atom signature absent from all served
source atoms.  A signature is the normalized intent, bound objects/attributes and
exact extracted signal (value+unit, code pair, action+object, or diagnostic
relation).  Thus a tangential appendix does not pass merely because it shares a
section number, and an already-served voltage threshold is not re-added.

## Exact card construction

Candidate atoms come only from these byte-stable units, in order:

1. referenced subsection block, if a marker is present;
2. individual Markdown table rows;
3. numbered/list items;
4. paragraphs split on blank lines.

Units over 720 characters are split only at newline boundaries; fragments under
40 non-whitespace characters are rejected.  Semantic score is the exact tuple:

`(contract_pass, object_hits, purpose_attribute_hits, novel_atom_count)`.

All components are integers.  Require contract pass, object hits >=1 and
purpose/attribute hits >=1.  Identity mappings may satisfy object binding through
the exact section title.  If two different evidence rows share the maximal score,
reject the edge.  Within one row, source byte offset is the deterministic tie-break.

Return at most two cards.  A second card is admitted only when it adds a distinct
structured value/code or required atom.  Each card and the anchor receipt carry
candidate/document/extraction/content/quote hashes and exact bounds.

## Explicit rejection trace

Every edge reports one terminal reason: no strong identity, no unique body anchor,
TOC, incompatible heading, no bound obligation, no contract-bearing atom, no novel
atom, semantic tie, or selected.  No model, database call, QID, gold fact or manual
label is an input.

## Development and metamorphic gates

S114 labels are regression fixtures only.  Before freezing implementation hash,
tests must cover:

- split heading/body cluster and changed section numbering;
- same section number in a TOC;
- duplicate compatible headings (fail closed);
- incompatible intervening heading;
- same reference with a different object;
- source already carrying the requested numeric atom;
- subsection evidence outside the first 720 characters;
- structured-code mapping with renamed synthetic codes;
- byte-identical receipts and tamper rejection.

Development expectations may guide implementation but are not release metrics:
retain useful S114 positives, reject or repair irrelevant/ambiguous cards, recover
the visible identity-mapping false negative, and preserve hp002 V01/V02 carriage.

## Sealed evaluation boundary

The nested holdout was sealed before this design at SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`:
12 cases from two manufacturers.  It is only a smoke gate.

After implementation and generic/metamorphic tests:

1. freeze selector and config hashes;
2. unseal once, without tuning;
3. ambiguous counts as non-relevant;
4. strict precision = relevant / selected;
5. contamination severity: high = contradicts/misdirects the requested action;
   medium = materially omits or substitutes the requested evidence; low = merely
   tangential but non-conflicting;
6. inspect every potential-but-not-selected edge for a visible high-confidence FN;
7. any tuning invalidates the nested result and requires a fresh cohort.

Only a clean nested smoke permits creation of a broader fresh cross-manufacturer
cohort.  Answer regression and default-off integration remain unauthorized.
