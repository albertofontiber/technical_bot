# S213 compact frontier design gate

Decision: may S213 execute once as a bounded diagnostic without a remaining concrete path to false
GO, source fabrication, target leakage, or unbounded spend?

S212 scored 1/12 stable residual gains and 0/5 hp017 gains. Its sealed causal funnel found five
upstream candidate-coverage misses and six downstream question-wide selection misses. S213 changes
those mechanisms in upstream-to-downstream order and does not tune a product, question, expected
answer, fact name, scoring regex, or threshold.

Upstream is now one clean deterministic lane. `evidence_units_v2` enumerates source-bound contiguous
units and source-bound table-header/row composites from each already-served chunk. No model extracts
claims or authors quotes. There is no query-overlap fallback lane. The zero-call preflight verifies
that these units overlap all 12 frozen residual source obligations, including all five hp017
relations. That coverage measurement uses gold only in preflight; questions, unit IDs and exact unit
content are the only fields visible to Terra. Fact names, obligation spans, baselines and golds are
not in model payloads.

Downstream is sharded by source chunk. For each question/chunk, Terra 5.6 low selects zero to four
opaque IDs. A fresh second Terra low call sees the same shard plus selected IDs and may add zero to
two. There is no question-wide selector, so evidence from one chunk never competes with another
chunk for a global ID quota. Both calls can only return known local IDs; duplicates, unknown IDs,
wrong cardinality, invalid COMPLETE/INCOMPLETE shapes, wrong model/status, or prompt-cap violations
fail closed.

The exact compiler unions all shard IDs only after both calls. It accepts at most 32 unique IDs and
12,000 appendix characters. Any overflow aborts and cannot produce a scored result. Every output
block is exact unit content. Every receipt carries the source candidate, fragment and exact source
span(s); table composites emit separate header and row span receipts. The immutable baseline is a
byte-identical prefix. The frozen S210 scorer independently requires both answer coverage and an
overlapping source-span receipt for factual credit.

Population and gates are unchanged: four exposed targets (51 chunks, 12 residual relations), 14
independent single-source guardrails (14 chunks, 37 answer points), and two fresh replicas. GO needs
at least 11/12 stable gains and 4/5 hp017 gains, zero prior-relation regressions, zero new hp017
cardinality contradictions, zero guardrail point regressions, evidence precision >=0.70, no invalid
citations or baseline-prefix failures, mean appendix <=5,000 chars, and cost below the permit.
Local GO awards zero facts and only opens a separate atomic Sol xhigh + Fable result review.

Execution is exactly 130 selector plus 130 verifier calls, zero provider retries/resume, no reuse of
prior model outputs, no retrieval/database/runtime calls and no post-NO-GO same-cohort tuning. The
largest observed prompt is 17,758 bytes under a hard 50,000-byte cap. A deliberately conservative
bound counts each possible UTF-8 input byte as a token, includes both system prompts and the full
700-token output cap for all 260 calls: $35.646975 under the sealed $75 ceiling.

This is mechanism evidence on a partially exposed target cohort, not fresh generalization. S213 is
evaluation-only/default-off even after local success. chunks_v2 remains `ACTIVE_READ_ONLY`;
chunks_v3 remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway is not a PR/merge gate.

Portable preflight SHA-256:
`1c0b3d821e21c1b38d4eff44deaf15ba49ce2f2b6fb055fd9d535145db3bb1be`.

PASS only if this one diagnostic execution is bounded and cannot falsely claim GO through a
remaining concrete implementation or isolation defect. FAIL only with a concrete blocker. Do not
require style work, more cohorts, deployment, external validation, or another review round at this
gate; those remain downstream requirements for generalization and production credit.
