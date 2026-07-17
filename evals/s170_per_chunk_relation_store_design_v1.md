# S170 per-chunk typed relation store development gate

S170 tests the transport-only successor frozen by S151 and the architecture
recommended by S150: extract relations offline one chunk at a time, checkpoint
each result immutably, and let query-time selection operate on explicit relation
atoms rather than rediscovering multi-unit relations from raw evidence.

This is a development reuse gate. It uses the already sealed S168 source packet
and independent Sonnet gold, but no target questions. Fourteen Haiku extraction
calls create a store of generic, product-bound typed relations. Each relation
has a subject, predicate, object, conditions, qualifiers and one to three known
header-aware source-unit IDs. The application assigns the relation ID, validates
every source span/hash and forbids batch extraction or retry.

Only if all fourteen stores are valid and non-empty, thirteen Haiku selector
calls receive the S168 questions and relation atoms without raw source text.
Selected relations deterministically materialize their source-unit union for
gold scoring and later citation-bound writing.

The frozen semantic gates remain claim recall >= 0.90, source-unit precision >=
0.80 and complete-question rate >= 0.75, with zero invalid extraction/selection
outputs and identity mismatches. A pass authorizes only a fresh
document-independent promotion cohort plus a separate semantic-fidelity audit.
It grants no target probe, fact credit or production change.

There are at most 27 Haiku calls, zero retries and a USD 2.00 internal ceiling.
