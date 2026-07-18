# S212 corrected compact full-binding gate

Decision: does the corrected S212 eliminate the false-GO path identified by Sol
while remaining bounded and provider-compatible?

The rejected v1 policy kept only the first 16 claims. Sol correctly blocked it:
claim 17 could contain bindable contradictory/regressive evidence, so dropping it
before checks might allow false GO. Fable had passed v1, but v1 is abandoned and
will never execute.

Corrected S212 sends the Anthropic-supported schema already proven over 88 S210
extractor calls. It validates the entire response against that schema, then exact-
binds every claim in provider order using deterministic batches of at most 16,
because the frozen binder accepts at most 16 per invocation. It deduplicates exact
source spans across batches. Nothing is truncated or suppressed before planner,
verifier, contradiction/regression checks, or scoring.

Boundedness is independent of claim count: Haiku output is capped at 2,200 tokens
per chunk; Terra inputs have a hard 100,000 UTF-8-byte cap; planner selects at most
12 IDs and verifier adds at most six; compiled appendix is capped at 12,000 chars;
the complete-run conservative cost bound is $22.948314 under $75. Any exceeded
bound stops the run and cannot produce GO.

The raw journal and final receipt identify every call above the legacy 16 threshold,
raw count, fully-bound excess count, and raw hash. Tests prove all 17 synthetic
claims bind in exact order in two batches and under-limit behavior is unchanged.

No prior output is reused. S211 produced no target output. Prompts, models,
fallback, selector, verifier, compiler, scorer, cohort, two replicas, GO thresholds
and budget remain unchanged. The target cohort's partial S210 exposure is disclosed;
this is not fresh generalization. Local GO still needs stable 11/12 relations, 4/5
largest bucket, zero regressions/new cardinality contradictions and all source,
citation, precision, length and cost gates. It awards zero facts and only opens a
separate atomic Sol xhigh + Fable review. Runtime remains unwired/default-off.

No retry/resume or post-output tuning is permitted. `chunks_v3` remains
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway is not a gate.

Frozen corrected preflight portable SHA-256:
`ba53a7a4c10c1f00f127e2e59960285cbebb93ec9348e8ec474d37402ca97ce3`.

PASS only if binding all claims in batches closes the prior false-GO blocker and
the run stays bounded. FAIL only for a concrete remaining false-GO, isolation or
safety defect. Do not require external validation at this diagnostic gate.
