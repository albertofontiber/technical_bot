# S137 v3 — question-atomic Fable adjudication

Status: final recovery design frozen before implementation or model calls.

## Trigger and diagnosis

The single Fable v2 response completed, but its structured judgement was invalid:
one Xtralis evidence label had a one-character transcription error and another
evidence item was absent. The full response is retained only as an invalid
receipt and contributes zero semantic votes. No semantic labels from Sol or the
invalid Fable response are used to design this recovery.

Two independent failures now establish that a monolithic 47-item Fable response
is not a reliable transport unit under adaptive `xhigh` reasoning: v1 truncated;
v2 completed but violated exact set coverage. The correction is general
question-atomic execution, not a question- or manufacturer-specific exception.

## Frozen execution

- Split the unchanged public packet mechanically into its three questions.
- Submit every question once to `claude-fable-5`, adaptive thinking,
  `effort=xhigh`, structured output, with a 10,000-token cap per question.
- Use the byte-identical v1 system prompt, schema, rubric, evidence labels,
  content and order within each question.
- Validate and persist each response before starting the next. Each response
  must contain exactly its one question and classify every evidence label once.
- Combine the three valid atomic judgements locally and revalidate them against
  the full frozen packet.
- If any call truncates, fails, or returns an invalid judgement, stop with
  `HOLD`. No atomic retry or fourth Fable recovery protocol is authorised.

All three questions are re-adjudicated. Reusing the two structurally valid
subparts from the invalid v2 response is forbidden because it would make the
execution path conditional on observed response quality and weaken judge
independence.

## Cost and downstream rule

Before inference, count each atomic input at the provider. Cumulative worst-case
cost includes valid Sol v1 actual cost, the conservative upper bound of the lost
Fable v1 call, actual Fable v2 cost, all three atomic calls at full caps, and the
optional Sol arbitration at full caps. Abort unless the total is below USD 10.

After valid combination, terminal mapping and optional arbitration are exactly
the S137 v1 rules. All three questions must end as
`CANDIDATE_SUCCESS_AT_10`; otherwise `chunks_v3` remains out of production. No
fact, chunk, retrieval threshold, migration or deployment is changed by v3.

