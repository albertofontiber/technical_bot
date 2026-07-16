# S115 — Exact reference-edge coverage (design v7)

Status: frozen after v6 development replay and before generic-title binding.
Local shadow only. Active config remains `config/reference_edge_contract_v4.yaml`,
SHA256 `2dab22ba5b324e5ad42709aa0d6a8638a3b80b25d03eae7667fa3b3ad229823c`.

This version inherits v5-v6. The labelled development replay retained one known
false positive: a generic source sentence listed WiFi section 5.5.4, and its card
was selected for a question about raising user level merely because both mentioned
an already-connected user. The referenced section title itself had no query topic.

For a `generic` edge only, an evidence row is now contract-bearing only when the
exact referenced section title shares at least one distinctive query token. A
`query_aligned` edge is unchanged. This is evaluated after strong identity and
anchor resolution, appears as `generic_section_not_query_bound` in candidate
trace, and does not remove the edge from the potential audit.

This generic structural rule admits examples such as query `WiFi` ↔ title `WiFi
options` and query `speaker output` ↔ title `speaker output wiring`, while rejecting
an unrelated WiFi appendix for a `user level` request. It contains no product,
manufacturer, QID, expected answer or manual-specific vocabulary.

The nested holdout SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains sealed and all v5-v6 invalidation rules remain in force.
