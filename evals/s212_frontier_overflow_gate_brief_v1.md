# S212 compact deterministic-overflow gate

Decision: can S212 safely run one complete diagnostic matrix with a provider-
compatible schema and a deterministic local first-16 overflow policy?

Observed causal facts:

- S210's schema without `maxItems` was accepted for 88 Haiku calls.
- One S210 response contained 17 claims; the local hard limit 16 stopped the run
  before score. S210 is sealed NO-GO with 0 facts.
- S211 added schema `maxItems: 16`; Anthropic rejected that unsupported keyword
  before model invocation, with 0 tokens/cost/target output. S211 is sealed NO-GO.

S212 makes one change. It sends the proven provider-supported S210 schema. For
each response, local code retains the first 16 claims in provider order and drops
the tail before exact span binding. The raw response is journaled; final receipts
list every overflow call, raw count, drop count and raw hash. Tests prove 17→first
16 exactly and under-limit behavior unchanged.

This policy can reduce recall but cannot add or alter evidence. Every retained
claim still needs schema validity, exact contiguous source binding, deduplication,
opaque-ID selection, completeness verification and literal compilation. Missing a
necessary tail claim makes stable coverage fail; it cannot grant a fact. No gold,
target identity, product, expected value or prior model output influences which
claim is retained.

All 202 calls are new; no S210 output is reused and S211 produced none. Prompts,
models, fallback, selector, verifier, compiler, scorer, cohort, replicas, gates and
budget are unchanged. The cohort has prior partial exposure and cannot establish
fresh generalization. Local GO still requires 11/12 stable relations, 4/5 largest
bucket, zero regressions/new cardinality contradictions, source receipts, citation
and length/cost gates. It awards 0 facts and only opens atomic Sol xhigh + Fable
review. Runtime remains unwired/default-off pending external validation.

No retry/resume or post-output tuning is allowed. The conservative pre-call bound
is $22.948314 under $75. `chunks_v3` remains
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway is not a gate.

Frozen zero-call preflight portable SHA-256:
`05c7518b7b382ce9d2e986fb1f6b48572b9674d27731963f045252293bd33221`.

PASS if the first-16 policy may lose recall but cannot falsely produce the stated
diagnostic GO. FAIL only for a concrete false-GO, isolation or safety defect. Do
not require fresh generalization or runtime validation at this gate.
