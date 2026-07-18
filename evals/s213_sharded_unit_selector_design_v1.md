# S213 — deterministic upstream units and sharded downstream selection

Status: design and implementation candidate, frozen before any paid S213 call.

## Why this tranche exists

The canonical denominator remains 157 and the current canonical score remains 143 facts OK
(91.08%). Reaching at least 98% requires 154/157, hence at least 11 of the 12 residual synthesis
relations must become stable qualified gains. The largest residual bucket is hp017 with 5 relations.

S212 established the causal funnel without moving credit: five residual relations were absent from
the candidate pool, six reached the pool but were lost by question-wide selection, and only one was
stable qualified. S213 changes those two mechanisms, upstream first and downstream second. It does
not re-open closed retrieval or chunks investigations.

## Mechanism

1. `evidence_units_v2` enumerates header-aware, source-bound units deterministically for every
   already-served chunk. No model proposes claims, quotes, spans, facts, or answer prose.
2. There is no parallel claim extractor or query-overlap fallback lane. This removes the hybrid
   bridge: every selectable item comes from the same deterministic unit contract.
3. Terra sees one question and one chunk at a time. It may select at most four opaque IDs and may
   return empty. A second independent Terra call over the same shard may add at most two IDs.
4. There is no question-wide selector. The compiler unions shard selections and reconstructs every
   byte from exact source spans. The baseline answer is immutable and
   the appendix is bounded to 32 IDs and 12,000 characters.

The zero-call preflight must prove that deterministic header-aware units overlap all 12 frozen
residual source obligations. This validates source coverage; it does not alter the generic candidate
builder or selection prompt.

## Frozen population and execution

- Four target questions: cat018, hp002, hp011, hp017; 51 frozen chunks; 12 residual relations.
- Fourteen independent single-source guardrails; 14 chunks and 37 answer points.
- Two complete fresh replicas; no reuse of S210/S212 model outputs.
- 65 shards per replica, one Terra low selector plus one Terra low verifier per shard: exactly 260
  calls, zero provider retries and no resume.
- No retrieval, database, chunks, answer-writer, or runtime calls.
- Hard 50,000-byte prompt cap; provider-supported schemas omit unsupported array-size keywords and
  all cardinality checks are local and fail closed.

## Gates and credit

The gates remain unchanged: at least 11/12 stable residual gains, at least 4/5 hp017 gains, zero
protected-relation regressions, zero new hp017 cardinality contradictions, zero independent
guardrail regressions, selected-evidence precision at least 0.70, zero invalid citations or baseline
prefix failures, mean appendix at most 5,000 characters, and actual cost below the sealed ceiling.

Local GO moves zero facts. Credit requires a single sealed atomic-result review agreeing between
the principal reviewer GPT-5.6 Sol xhigh and independent Fable 5. The target cohort is already
partially exposed, so even a GO is mechanism evidence on the frozen cohort, not fresh generalization.
No same-cohort prompt, threshold, or cap tuning follows a NO-GO.

The factual gate reuses the historical S210 scorer without modifying its byte-frozen file. Because
that scorer hard-codes the S210 call header (`202`), an S213-only adapter first verifies the original
260-call artifact seal and complete matrix, creates an ephemeral sealed proxy changing only
`calls: 260 -> 202`, runs every frozen answer/receipt/cost check, then rebinds the published score's
input hash to the untouched S213 receipt. A contract test proves that the proxy has no other delta.

## Decision boundaries

- S213 is evaluation-only and default-off. A successful experiment still requires a separate
  integration and fresh holdout tranche before production.
- chunks_v2 remains `ACTIVE_READ_ONLY`.
- chunks_v3 remains explicit `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.
- Railway is a demo and never a PR or merge gate; green CI is the merge gate.
