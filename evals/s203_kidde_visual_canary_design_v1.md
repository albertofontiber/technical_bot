# S203 — Kidde pixel-grounded gold canary

## Purpose

The existing 51-question gold ledger contains seven Kidde-related questions,
but none exercises the three selected source families or their technical
predicates. S203 does not claim an empty Kidde gold catalog. It tests whether a
new, visual-first authoring lane can create precise and independently reviewed
questions without looking at bot behavior.

The canary is frozen at three items before any frontier-model call:

1. a heat-detector configuration table;
2. a two-page manual relay-test procedure;
3. a comparison table for normal and two-state input modes.

The exact installation-sheet basenames and resolved PDF byte hashes are absent
from existing gold citations. The builder discovers the selected product-family
manuals from model/document tokens across the full 55-PDF Kidde directory and
fails if that discovery differs from the declared inventory. Semantic novelty
is not presumed from filenames: both reviewers receive existing questions plus
their atomic facts and must reject duplicates or covered predicates.

The PDFs themselves are not claimed as previously unseen. They appeared in
earlier source inventories or diagnostic packets: S200 used the heat sheet's
English introduction, S197 used the single-output English introduction, S195
used the multi-I/O English test procedure, and S159 used a mechanical table.
The current Spanish page spans and technical predicates are disjoint. This is a
new benchmark-authoring test over new source units, not a repetition of those
closed extraction investigations.

## Pixel contract

Every item binds the SHA-256 of the complete source PDF, page count, selected
page numbers, extracted text and a committed 200 dpi PNG for every target page
and its visual boundary. Frontier models receive only the same PNG bytes and
page labels; extracted text stays in the packet for local audit and is not sent
to either author or reviewer. This makes the canary genuinely pixel-grounded.

The target spans were inspected before generation and are legible, not clipped,
and correctly bounded by the adjacent language sections. This source evidence
is immutable for the canary. No chunks table, retrieval output, bot answer or
current fact classification is an input to question selection or gold writing.

## Frontier duo without convergence loops

GPT-5.6 Sol with `xhigh` reasoning is the principal author. Fable 5 independently
authors a candidate from the same source pixels, without seeing Sol's output.
After both independent candidates exist:

- Fable reviews Sol's candidate against the pixels;
- Sol reviews Fable's candidate against the pixels;
- the final gold, if any, is Sol's candidate only; candidates are never merged;
- all three Sol candidates must pass Fable review, all three Fable candidates
  must pass Sol review, and there may be no unsupported core fact, wrong page,
  duplicate question or material disagreement. At cross-review time each model
  sees both independently generated candidates and must report any material
  divergence explicitly;
- there is one provider attempt per planned call and no prompt tuning, retry or
  post-selection on these same three items.

This uses frontier models for the high-judgment authoring and critical review,
while packet construction, hashing, validation and later scoring remain local
and deterministic.

## Scope and stop lines

At most eight paid calls are permitted: three independent generations per model
plus one batched cross-review per model. The canary ceiling is USD 40 inside the
user's USD 200 authorization. A provider failure or invalid structured output is
`HOLD_FRONTIER_INCOMPLETE`; a semantic or visual disagreement is
`NO_GO_VISUAL_GOLD`; only a complete dual pass is `GO_KIDDE_GOLD_CANARY`.

A GO creates three candidate benchmark questions but moves zero facts to OK. It
only authorizes a separate preregistration that must bind corpus, chunk table,
index/embeddings, retrieval and generation configuration, judge, seeds, baseline
and explicit zero-regression thresholds before any bot evaluation. `chunks_v2`
remains active and
`chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. Railway is a demo and is
not a PR or merge gate when CI is green.
