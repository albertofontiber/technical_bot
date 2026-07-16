# S115 — Exact reference-edge coverage (design v6)

Status: frozen after v5 metamorphic replay and before alignment-tier implementation.
Local shadow only. Active config remains `config/reference_edge_contract_v4.yaml`,
SHA256 `2dab22ba5b324e5ad42709aa0d6a8638a3b80b25d03eae7667fa3b3ad229823c`.

This version inherits every v5 safety contract. The first local replay after
removing the premature edge filter exposed a generic cross-reference competing
globally with a query-aligned reference: a low-specificity test-procedure appendix
could outrank the directly referenced airflow section through incidental attribute
hits.

All valid explicit references still emit edges. Selection now has two deterministic
tiers:

1. an edge is `query_aligned` when its bounded source clause shares at least one
   distinctive query token;
2. an edge is `generic` otherwise;
3. if any query-aligned edge produces valid novel evidence, generic-edge winners
   remain audited but cannot compete globally;
4. generic edges compete only as a fallback when no query-aligned edge produces a
   winner.

Within each tier the exact v5 row score and tie rules are unchanged. This preserves
generic “consult section N for more information” recovery while preventing it from
overriding a more specifically bound reference. The alignment flag and tier outcome
must be visible in the per-edge trace. No labelled product term or case identifier
is part of the rule.

The nested holdout SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains sealed. All v5 freeze and invalidation rules remain in force.
