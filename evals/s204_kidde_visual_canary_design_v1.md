# S204 — fresh Kidde visual-gold canary and reusable contract

## Purpose

S204 tests whether a corrected, reusable pixel-grounded gold-authoring contract
generalises to three fresh Kidde source units. It is not a retry, repair or
post-selection of S203. No candidate, question, answer or page from the closed
S203 cohort is reused.

The official 157-fact scoreboard remains 143 OK, 12 synthesis misses and 2
retrieval misses (91.08%). S204 can create evaluation material but gives zero
official fact credit by itself. Any bot evaluation after a GO requires a separate
upstream-to-downstream preregistration and frozen baseline.

## Closed S203 findings incorporated once

1. Application or scenario recommendations are forbidden unless the supplied
   pixels state them explicitly. Numeric limits do not imply suitability.
2. Reviewer output separates `blocking_issues` from `nonblocking_notes`. Only
   blocking conditions invalidate PASS; verdict consistency is validated locally.

These are generic contract corrections in `src/rag/visual_gold.py`, not
case-specific prompt hints.

## Fresh source units

The builder discovers the complete locally available manual family for each
selected product, binds source PDF bytes, and commits the exact 200 dpi pixels.
Selection occurred before model or bot output was seen.

| ID | Product/source unit | Focus | Stratum |
| --- | --- | --- | --- |
| `kidde_base_class_a_terminals` | KE-DB3010W/B standard mounting base | pages 1 and 4; visual Class A topology plus terminal map | diagram + terminal table |
| `kidde_indoor_dip_examples` | indoor addressable notification family | page 12; exact visual DIP positions for addresses 008 and 112 | visual configuration |
| `kidde_deep_accessory_slots` | KE-DBA-AUXW deep accessory | pages 1 and 3; visual distinction of address-tag and locking-tab slots | visual identification |

All three source basenames and byte hashes are disjoint from existing gold
sources. Earlier artifacts only inventoried these files; they did not author or
evaluate these page/predicate units. The packet carries every existing gold
question and atomic-fact text for semantic duplicate review. It also carries all
S99 HyQ questions associated with the three source PDFs: those are doc-side
retriever augmentations, not test golds, but excluding semantic duplicates avoids
retrieval contamination. The selected predicates depend on visual relationships
not present as exact HyQ questions; semantic novelty remains a blocking cross-review
gate rather than a local assertion.

## Bounded frontier protocol

- Principal author/reviewer: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent model: `claude-fable-5`.
- Three independent pixel-only generations per model, then one batched
  cross-review per model: at most eight paid calls.
- Provider retries: zero. Same-item retry: false. Candidate merging, repair,
  salvage and post-selection: forbidden.
- A semantic `INSUFFICIENT` is NO-GO. Provider/model incompleteness is HOLD.
- The principal Sol candidates become candidate golds only if both whole-cohort
  review directions PASS. The output remains unintegrated and has zero official
  fact credit.
- Conservative S204 execution ceiling: USD 40. User-wide authorization: USD 200.

## GO / HOLD / NO-GO

- `GO_KIDDE_GOLD_CANARY`: all six candidates are locally valid and both batched
  cross-reviews PASS every item and fact under the materiality-aware contract.
- `HOLD_FRONTIER_INCOMPLETE`: provider/model response is missing, malformed,
  incomplete or does not match the exact model pin.
- `NO_GO_VISUAL_GOLD`: source/candidate is semantically insufficient or either
  review direction finds a blocking issue.

No retry or tuning on these items follows HOLD or NO-GO.

## Downstream boundary

A GO only authorizes a new PR that freezes corpus/chunks_v2, index/embeddings,
retrieval/rerank/generation configuration, judge/seeds, baseline outputs and
zero-regression thresholds before evaluating these candidate questions. It does
not authorize database writes or production activation.

`chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE` and is carried as an
explicit evaluation line only. Railway is a demo and is never a PR/merge gate;
green CI is the merge gate.
