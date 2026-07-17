# S137 v3.1 — resume the already-triggered arbitration

Status: finalisation design frozen before arbitration implementation or call.

All three question-atomic Fable responses completed, validated and were combined
successfully. The v3 runner then derived at least one terminal disagreement and
entered the pre-authorised arbitration path, but failed locally before inference:
the reused v2 helper requested the v2 budget-key name from the v3 preregistration.
No arbitration response or charge exists.

V3.1 is a local finalisation addendum only. It freezes and revalidates the public
packet, private mapping, valid Sol v1 response, all three atomic Fable receipts
and the combined Fable judgement. It derives the disagreement set with the
unchanged v1 terminal function, counts one blinded Sol arbitration input, and
executes at most that one call with `gpt-5.6-sol`, `xhigh`, the unchanged prompt,
schema and rubric. No primary or Fable call is repeated.

The preflight includes every prior cost: valid Sol v1 actual cost, conservative
upper bound for truncated Fable v1, actual invalid Fable v2 cost, actual atomic
Fable cost, and the arbitration at its full output cap. It aborts before
inference unless cumulative worst case is below USD 10.

After arbitration, aggregation and promotion use the original S137 terminal and
all-three-success rules. Any invalid arbitration becomes `HOLD`; no retry or
further protocol is authorised. No fact, chunker, retrieval rule, migration,
production configuration or deployment changes in v3.1.

