# S115 — Exact reference-edge coverage (design v5)

Status: frozen after adversarial NO-GO and before implementation changes. Local
shadow only.

This version keeps the strong document/extraction identity, unique byte-backed
section anchor, TOC rejection, exact evidence receipts and fail-closed ties from
design v2-v4. It uses `config/reference_edge_contract_v4.yaml`, SHA256
`2dab22ba5b324e5ad42709aa0d6a8638a3b80b25d03eae7667fa3b3ad229823c`.
The unused `subsection_search_rows` knob is removed; no product, manufacturer,
QID, gold value or labelled diagnostic term is introduced.

## Corrections required by the adversarial review

1. **Canonical novelty.** A source and candidate atom are compared by the fixed
   query obligation, intent, signal kind and normalized exact signal. Incidental
   differences in title, purpose or the number of matching object words cannot
   make an already-served value/code/action novel. Unit hit sets remain ranking
   evidence only.
2. **Section-bounded bytes.** Candidate evidence ends before the first
   incompatible numbered heading inside the same chunk. A referenced subsection
   is additionally bounded by the next subsection marker. Table rows and list
   items are atomic and cannot be re-served inside a wrapping paragraph. Units
   over 720 characters are split only at newline boundaries; an indivisible
   overlong line fails closed.
3. **Edge generation before semantic binding.** Every syntactically valid explicit
   section reference emits an edge, including generic clauses such as “consult
   section 2.8 for more information”. Query/object/attribute binding happens only
   against candidate evidence. Strong identity and anchor rules are unchanged.
4. **Strict identity and diagnostic signals.** Identity needs an explicit pair in
   one unit: at least two structured codes with a mapping separator, or a
   multi-cell Markdown row containing a structured code and descriptive content.
   Diagnostic prose needs both a relation and an observable code/numeric value;
   a diagnostic table row needs a structured code and at least two nonempty cells.
5. **Auditable potential and terminal state.** A potential edge has at least one
   exact-section candidate with the same strong identity. Every parsed edge lists
   candidate rejection reasons and exactly one terminal state. Empty receipt sets
   are reported as `not_applicable`, never as verified evidence.

The row score is exactly `(contract_pass, max_object_hits,
max_purpose_attribute_hits, unique_novel_atom_count)`. Card ordering uses the same
first three components plus per-unit novel atom count and then byte offset.

## Upstream versus selector false negatives

- `selector_false_negative`: a potential edge has a valid unique byte-backed
  anchor and decisive contract-bearing evidence, but the selector does not carry it.
- `upstream_unresolvable`: relevant content exists, but the extracted scope lacks
  the byte-backed heading/provenance needed to create a valid section cluster.

The known `sec017` order-code diagram is `upstream_unresolvable`: its metadata says
section 1.2 but neither that chunk nor a sibling contains the numbered heading in
source bytes. It must remain rejected here and be addressed in extraction/chunking;
it is not permission to weaken the anchor contract.

## Sealed evaluation

The nested file SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains unopened. Before its single allowed replay, freeze hashes for selector,
active config, generic/metamorphic tests, runner, runner tests, design and prereg.
The replay must audit all selected cards and every potential-not-selected edge.
Any subsequent selector/config change invalidates the result.
