# S159 table-preamble closure design v2

## Delta from S158 v1

S158 v1 recovered the FAAST table qualifier and produced 29 correct closures
out of 30 independent pairs, but one exposed predecessor tail contained a
complete earlier table. The frozen zero-cross-table gate therefore closed v1
as `NO_GO`.

V2 adds one corpus-independent structural invariant: the exact heading-to-end
candidate span must not itself contain a complete Markdown pipe table. The
exposed S158 failure is development evidence only and is never reused as v2
held-out evidence.

All other identity, exact-adjacency, span, size, mutation and cost boundaries
remain unchanged. No product, manufacturer, question or expected value enters
the selector.

## Fresh validation

The independent cohort is rebuilt mechanically from `chunks_v2` and excludes
every document present in the S158 independent packet as well as the known
FAAST target documents. Semantic review starts only after that packet is
frozen.

The local gate requires zero cross-table attachments and 100% correct table
continuity. A passing local gate permits one minimal target answer probe; it
does not authorize production or OK credit.

