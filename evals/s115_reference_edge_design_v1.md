# S115 — Exact reference-edge coverage (design v1)

Status: proposed, not implemented, not integrated.

## Problem boundary

S114 proved that following a numbered manual reference by section metadata and
lexical overlap is not precise enough.  On a preregistered challenge it selected
10 rows: 4 relevant, 4 irrelevant and 2 ambiguous, plus one visible false
negative.  Exact hashes proved provenance, but not that the bounded evidence
answered the question.

S115 replaces only the `explicit_intra_document_reference` facet.  The frozen
S114 selector and its artifacts remain unchanged.  Access/unlock and licensed-
loop rules are out of scope and remain unproven outside the known cohort.

## Contract

Inputs are only the user query, already-served rows and product-scoped candidate
rows.  The selector never receives QIDs, facts, expected values, gold receipts or
manual labels.  It performs no database write or model call.

An appended row must satisfy all four gates below.  Failure at any gate means no
append, with a structured rejection reason.

### 1. Exact reference edge

Parse each reference independently into:

- exact section number;
- optional subsection marker such as `2.2.7(e)`;
- reference cue and local purpose clause;
- source offsets;
- query-aligned and purpose-specific anchors.

Multiple references in one source row remain separate edges.  They must never be
collapsed to an unordered set.

### 2. Body-section resolution

A candidate must share strong document identity and its section metadata must
begin with the exact reference.  In addition, the candidate content itself must
contain the matching body heading near its start.  Reject table-of-contents rows,
dot-leader indexes, and metadata-only matches.  When duplicates remain, rank the
body fragment whose title and evidence windows best align with the edge purpose;
do not rank by generic operational-token count.

### 3. Decisive bounded evidence

Build at most two exact cards of at most 720 characters each.  Prefer, in order:

1. the explicitly referenced subsection;
2. atomic table rows with distinct structured values;
3. paragraph or list-item windows aligned to query plus edge purpose.

The cards—not the full row—must satisfy an intent-specific evidence contract:

- quantitative: aligned number/comparator and unit or named scale;
- identity/model verification: model/order-code mapping or structured option row;
- procedure/configuration: aligned action plus object, and either an ordered step,
  imperative instruction or explicit method/setting;
- diagnostic: observable/code/measurement plus its interpretation or action.

A selected row is not recovered unless every decisive term declared by the local
contract is present inside the exact cards.

### 4. Uncovered-slot delta

Represent question needs as coarse, reusable slots: quantitative, identity,
procedure/configuration and diagnostic.  Extract the same evidence signals from
the served source and candidate cards.  Append only when the candidate increases
coverage of a required slot.

This prevents tangential expansion when the source already contains the requested
answer (for example a voltage threshold or the final restart/logon action).  A
reference can be technically valid yet irrelevant to the user's missing slot.

## Expected diagnostic behavior (development evidence only)

The adjudicated S114 cases may be used as unit fixtures, never as release proof:

- retain: `sec005`, `sec015`, `sec019`, `sec020`;
- reject: `sec008`, `sec011`, `sec021`, `sec027` unless a different exact body
  fragment and bounded card truly satisfies the question;
- `sec009` must reach subsection `(e)` or reject;
- `sec023` must include the asked threshold or reject because the source already
  carries it;
- recover `sec017` through the identity/model-code contract rather than loose
  lexical overlap.

The original `hp002` target must still produce two exact table-row cards carrying
`V01` and `V02`.

## Anti-overfit evaluation

1. The S114 challenge becomes a labelled development set only.
2. A nested holdout was sealed before implementation at
   `evals/s115_reference_edge_nested_holdout_freeze_v1.json` (12 cases, two
   manufacturers).  Its small manufacturer count makes it a smoke gate, not
   release evidence.
3. Freeze the S115 source hash before unsealing that nested set.
4. If the nested smoke passes, create a fresh cross-manufacturer reference-edge
   cohort from current corpus rows not used in S114/S115 design.
5. Require zero medium/high contamination, strict precision >=90% when at least
   five rows are selected, at least one true positive, and no visible high-
   confidence false negative.
6. Only then run the protected answer-level regression.  Production/default-off
   integration remains a separate decision.

## Cost and rollout

- Local deterministic development and tests first.
- No embedding, reranker, judge or generator calls for design replay.
- At most one small structured semantic judge may be proposed later only if the
  deterministic version is inconclusive; it requires a separate preregistration
  and token budget.
- New module remains unreachable from runtime serving until all gates pass.
