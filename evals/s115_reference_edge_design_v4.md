# S115 — Exact reference-edge coverage (design v4)

Status: frozen before switching the implementation to contract v3. Local shadow only.

This design inherits the section-cluster, immutable anchor, bound-atom, exact-card,
tie and evaluation contracts from `s115_reference_edge_design_v2.md`, plus the
lexical hardening in `s115_reference_edge_design_v3.md`. It replaces only the
line-boundary grammar with `config/reference_edge_contract_v3.yaml`, SHA256
`e9c9a06d05fca6d0d5e4e82fd9bb00b58cbd3a855b73328c70b8c46f0e38d69c`.

The development test for an explicit subsection beyond the first card exposed a
generic parser defect: `\s*` immediately after a multiline start anchor can
consume a preceding newline. The subsection match then starts on that newline,
while the bounded-paragraph parser requires the first character to be non-newline,
so a valid subsection yields no atomic units. Contract v3 restricts indentation
around headings, subsection markers and TOC rows to horizontal whitespace.

The reference expression also makes its existing invariant explicit: when an
opening parenthesis follows the section number, a subsection marker must be
captured instead of silently backtracking to a section-only edge. No object,
manufacturer, product, QID, expected answer or labelled diagnostic term changes.

The nested holdout SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains sealed. Source, active config and tests must be hashed after all local
tests pass and before the one allowed unseal. Any post-unseal selector/config
change invalidates that smoke result.
