# S168 source-unit-bound gold ledger gate

S168 is a transport-only successor to the S167 cohort-construction NO-GO. It
does not reuse S167 documents, questions or labels and does not relax any S167
semantic threshold.

The new source-first packet contains fourteen further manufacturers and
fourteen further documents (seven table, seven prose), with zero overlap with
prior evaluation documents, known target documents/chunks and development
manufacturer-product pairs.

Instead of asking the independent Sonnet labeler to recopy exact text, the
application first creates immutable header-aware evidence units. The labeler
writes a natural Spanish field question and two to four necessary answer
points. Each point contains a generic frozen facet and one to three known
source-unit IDs. The application validates every ID, cardinality, source span
and content hash. A source unit may support several points or facets. No model
may write or repair source text.

After the cohort is sealed, Haiku receives the same immutable units, bound
source identity and frozen S165 facets. S166 validates its many-to-many ledger.
A gold point is covered only when all of its required source-unit IDs are in
the selected stable union. Selected-unit precision is measured against the
union of all gold support IDs.

The frozen gates remain: at least 12 questions/manufacturers, at least 5 table
and 5 prose questions, at least 24 answer points, claim recall >= 0.90,
selected-unit precision >= 0.80, complete-question rate >= 0.75, and zero
invalid selector outputs or identity mismatches.

A pass authorizes only a bounded target probe plus one critical adversarial
review before integration. It grants no fact credit and no production change.
There are no retries, no same-cohort repair and an internal cost ceiling of
USD 2.50.
