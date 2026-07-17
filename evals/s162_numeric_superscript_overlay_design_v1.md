# S162 — Geometry-bound numeric superscript overlay v1

## Objective and metric

Resolve the single `document-extraction-hold` without a product, model, table,
token or answer-specific patch. The mechanism passes only if it preserves PDF
superscript typography with exact provenance and zero observed false attachment
on an independent cohort. Answer-level OK credit remains out of scope.

## Root cause

The immutable LlamaParse record flattens visually distinct spans. In the target
PDF, `10` is a 7.98 pt baseline span and `5` is a 4.98 pt superscript span, but
the Markdown contains `105`. A plain regex cannot know whether `105` means one
hundred and five, ten to the fifth, or a footnote marker.

## Candidate contract

The raw extraction JSON is immutable. A deterministic offline normalizer may
derive a copy of a page Markdown field and a provenance receipt only when all of
these conditions hold:

1. the PDF bytes match the extraction record SHA-256;
2. the PDF engine marks a numeric span as superscript;
3. the immediately preceding non-blank span ends in digits;
4. the script is at most 80% of the base font size, its baseline is elevated by
   at least 0.5 pt, and the spans are horizontally adjacent;
5. the flattened numeric token occurs exactly once as a complete token on the
   corresponding LlamaParse page;
6. at least two alphabetic anchor tokens from the same PDF line also occur in
   the local Markdown line window around that token;
7. competing geometry signals do not map to the same Markdown offset.

The derived representation is literal HTML typography — for example
`10<sup>5</sup>` — not an inferred mathematical rewrite. The downstream model
may interpret the source, but the normalizer only preserves what the PDF marks.
Every ambiguous case abstains.

## Architectural placement

This is an offline document-normalization layer between immutable extraction and
chunking. It is not a Telegram/runtime rule and does not query the vector store.
No existing chunks are mutated in place during qualification. Production wiring,
re-embedding and document replacement require a separate versioned gate.

## Invariants

- no manufacturer, product, document, page, table or target token constants;
- no LLM, OCR or network call;
- raw input object and raw extraction file remain byte-identical;
- only the uniquely mapped Markdown token changes;
- exact page, offset, hashes, glyph geometry and matched anchors are receipted;
- idempotent: a second pass produces no additional changes;
- fail closed on PDF/hash mismatch; abstain on semantic ambiguity;
- `chunks_v2` remains active and unchanged during this experiment.

## Qualification sequence

1. Freeze this design and the preregistration.
2. Implement the pure normalizer and unit tests, including adversarial negatives.
3. Re-run the target locally and prove the expected single-token delta.
4. Validate on fresh non-target documents from the corpus discovery receipt.
5. Run the full test suite.
6. Use one bounded Sol 5.6 xhigh + Fable 5 xhigh review on the finished candidate
   and receipts. One round only; disagreements become HOLD, not iteration loops.
7. Only after local and adversarial GO may a separate minimal answer probe be
   considered. No new paid answer call is authorized by this design.

## Explicit non-goals

- repairing subscripts, OCR-only scans, arbitrary formula parsing or footnote
  linking;
- retrofitting every historical chunk;
- changing the generator prompt to suppress the observed answer;
- claiming that every `<sup>` is an exponent;
- promoting S161 to production before the extraction hold is closed.

