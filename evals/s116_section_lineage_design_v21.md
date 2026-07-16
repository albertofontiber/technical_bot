# S116 section-lineage contract v2.1 addendum

Status: frozen before implementation. This addendum keeps the v2 architecture
and closes the final three adversarial measurement gaps.

1. Anchor resolution fails when either the anchor or resolved `_Block` lacks an
   explicit `source_block_index`. `level` must be a non-boolean integer in
   `[1, 6]`; title, page, text and hash must all resolve exactly. `page=None`
   remains valid.
2. Every chunk, not just titled chunks, must satisfy one atomic state. Its
   source span resolves, its lineage equals the common lineage of every block in
   that span (including empty lineage), and `anchor/title/path` are either all
   derived consistently or all empty. The treatment corpus gate is zero
   `chunk_lineage_state_failures`.
3. Baseline and treatment must use the same Python runtime, audit scripts,
   metadata code, manufacturer registry and manufacturer YAML manifest. Only
   `src/reingest/chunk.py` may differ.

Cleanup additionally must not claim a continuous source span across a discarded
noise chunk. A normal same-lineage merge extends `source_block_end`; a merge
candidate separated by discarded noise remains separate. All v2 boundaries and
the complete 12-case test matrix remain mandatory.
