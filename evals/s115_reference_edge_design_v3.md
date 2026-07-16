# S115 — Exact reference-edge coverage (design v3)

Status: frozen before switching the implementation to contract v2.  Local shadow only.

This design inherits the section-cluster, immutable anchor, bound-atom, exact-card,
tie and evaluation contracts from `s115_reference_edge_design_v2.md`.  It replaces
only the lexical contract with `config/reference_edge_contract_v2.yaml`, SHA256
`74c9dddd928f9e1d80f78837ca259aea2a33e13debd9fc87c8f4d93564de2fe7`.

The version change fixes three generic defects found on the labelled development
set before implementation hash freeze:

1. An optional subsection followed by punctuation is now captured with a
   look-ahead, so `section N.N.N(e).` cannot backtrack to a section-only edge.
2. Spanish/English articles, prepositions and action words cannot bind as
   technical object or attribute tokens.
3. Ambiguous one-letter duration/distance units are removed.  A model phrase such
   as `VEA 2 software` can no longer satisfy a quantitative evidence contract as
   `2 s`.

Additionally, procedure intent accepts only an explicit action signal.  A colon
plus uppercase tokens is not a procedure mapping; structured mappings remain
available to identity and diagnostic intents.  This removes UI/footer fragments
that contain product codes but no requested action.

No product, manufacturer, QID, expected value or diagnostic-case term is added to
the selector/config.  The same generic and metamorphic tests remain mandatory.
The nested holdout SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains sealed.  After local development, source+config+tests hashes must be frozen
before the one allowed unseal; any subsequent tuning invalidates the smoke result.
