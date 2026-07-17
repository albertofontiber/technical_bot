# S146 fresh header-aware evidence gate

## Decision being tested

S145 isolated one generic representation failure: a correct fixed-width table
row was selected without the headers needed to interpret its values. S146 tests
whether immutable composite units made only from exact header and row source
spans solve that class without product-specific rules or fuzzy evidence.

## Independence and execution

- The source-first packet is selected mechanically from the frozen local v2
  snapshot, excludes all 36 S135 representative documents, and contains 14
  distinct manufacturers split equally between tables and prose.
- The V2 unitizer and paid runner are frozen before Haiku authors any questions.
- One Haiku author call creates only question-essential claims. Invalid quotes
  may be dropped deterministically; there are no model retries.
- One cheap ID-selection call is then made per eligible question. IDs and their
  source spans are validated locally; unknown IDs fail closed.

## Credit boundary

A passing fresh gate permits only an implementation probe against the 13 known
synthesis targets. It does not move facts to OK, authorize production, or revive
the rejected wholesale chunks_v3 migration.
