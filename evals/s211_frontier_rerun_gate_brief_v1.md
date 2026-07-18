# S211 compact rerun-integrity gate

Decision: may S211 execute one new complete diagnostic matrix after the S210
fail-closed partial run, without creating a false GO or benchmark postselection?

S210 stopped at call 126/202 before scoring because its provider JSON schema
omitted `maxItems` while the local validator enforced at most 16 claims. The
provider returned 17 claims on one chunk; the response was journaled and rejected.
There was no retry, resume, result artifact, scorer run, gold opening, fact credit,
or semantic inspection/tuning of candidate answers. Operational counts and the
17-claim failing response were observed. S210 is permanently NO-GO with 0 facts.

S211 makes exactly one generic contract correction:

- provider schema: `claims.maxItems = MAX_MODEL_CLAIMS_PER_CHUNK`;
- local v2 entrypoint validates that same schema before the frozen span binder;
- synthetic tests prove 16 accepted and 17 rejected;
- system prompts, models, fallback, selection, verifier, exact compiler, scorer,
  cohort, two replicas, thresholds, call geometry and budget are unchanged;
- no target IDs, products, values, fact names or S210 outputs enter the mechanism.

S211 will make all 202 calls again from zero. It cannot resume or reuse S210 calls.
It records that the target cohort has prior partial exposure and therefore cannot
claim fresh generalization. It is only a diagnostic continuation. Local GO still
requires stable 11/12 residual relations, 4/5 in the largest residual question,
zero regressions/new cardinality contradictions, exact source-span receipts,
valid citations, bounded appendix and cost. Local GO awards zero facts and only
opens a separate atomic Sol xhigh + Fable review; runtime remains unwired/default-
off pending later external real-question validation. Any incomplete or NO-GO S211
closes with no tuning or further call.

The execution has 130 Haiku extractions, 36 Terra-low plans and 36 Terra-low
verifications, no provider retry, and a conservative pre-call upper bound of
$22.948314 under a $75 internal ceiling. No retrieval, DB write or Railway gate.
`chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.

Frozen zero-call preflight portable SHA-256:
`977fc32d674ca262f7623b832f920a8e5c21f8cb0e49f185858afff6dfba06d7`.

PASS if this one complete rerun is methodologically acceptable for the stated
diagnostic decision. FAIL only for a concrete mechanism or isolation defect that
can falsely produce GO. Do not require fresh generalization or runtime validation
at this gate; those claims are explicitly forbidden and deferred.
