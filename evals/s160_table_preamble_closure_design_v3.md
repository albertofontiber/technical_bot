# S160 table-preamble closure design v3

## Delta from S159 v2

S159 v2 rejected complete Markdown tables inside a candidate preamble when
every delimiter cell had at least three hyphens. A fresh independent document
used an extracted delimiter row with one hyphen in an empty-width column. The
row is a real pipe table in the corpus, so v2 was closed as `NO_GO`.

V3 changes only delimiter recognition from three-or-more to one-or-more
hyphens, with the same optional alignment colons. It remains necessary for two
consecutive pipe rows to form a table header/delimiter pair. This is an
extraction-tolerance rule, not a semantic or product-specific relaxation.

Every S158/S159 target, packet and document is development-only. V3 uses a
third mechanically selected cohort that excludes all documents seen in both
prior independent packets and all known FAAST target documents.

