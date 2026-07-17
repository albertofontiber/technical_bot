# S162 — Geometry-bound numeric superscript overlay v2

## Delta from v1

V1 correctly abstained everywhere but failed its target gate because PDF table
cells that share a visual row can be emitted as separate text lines/blocks. V2
changes one contract element only: source anchors come from the same **visual
row**, not the same PyMuPDF text-line object. All SHA, typography, uniqueness,
immutability and abstention guards remain unchanged.

## Visual-row anchor contract

For a geometry-qualified numeric superscript signal, collect alphabetic anchors
from page spans only when:

1. their vertical bounding box overlaps the base span by at least 60% of the
   smaller span height, or their baselines differ by no more than 1 pt;
2. their horizontal distance from the base/script interval is no more than 25
   base-font widths;
3. the resulting anchor token has at least three alphabetic characters.

At least two of these PDF visual-row anchors must occur in the local Markdown
window around the unique flattened token. The visual row is evidence only for
alignment; the derived text remains literal `<sup>` markup and carries no claim
that the script is a mathematical exponent.

## Preserved v1 invariants

- raw LlamaParse record and PDF bytes remain immutable;
- PDF SHA must equal extraction SHA;
- native superscript flag + numeric base/script + font/baseline/adjacency gates;
- unique complete-token match on the corresponding Markdown page;
- conflicts and ambiguities abstain;
- exact hashes, offsets, geometry and anchors are receipted;
- default-off/offline qualification only; no `chunks_v2`, DB or runtime writes;
- no constants for target token, PDF, table, product, manufacturer or question;
- idempotent and zero-model execution.

## Gate

Target: exactly one `105` → `10<sup>5</sup>` replacement on page 5 and zero
other deltas. Independent: at least 8 non-target documents and 10 mappings,
with 100% geometry/attachment correctness and zero false attachments. If that
coverage is unavailable, v2 is NO-GO rather than weakening the contract.

