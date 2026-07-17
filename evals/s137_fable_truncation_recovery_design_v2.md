# S137 v2 — bounded recovery from the Fable max-token truncation

Status: recovery design frozen before implementation or retry.

## Failure and scope

The S137 v1 packet and Sol judgement completed and validated. The first Fable
call reached its pre-registered 8,000-token output cap while adaptive `xhigh`
reasoning was active. It produced no persisted valid judgement, so no Fable
semantic decision exists. Sol's semantic decision has not been inspected.

This is a transport/output-budget failure, not evidence about chunk quality.
V2 changes only Fable's output cap from 8,000 to 20,000 tokens and makes the
truncated-attempt receipt durable. It reuses the validated Sol response and the
byte-identical v1 packet, mapping, system prompt, JSON schema, rubric and
terminal rule. It does not rebuild, add, remove or reorder evidence.

## Recovery execution

1. Validate physical hashes of every v1 dependency and validate Sol's stored
   structured judgement against the frozen public packet.
2. Count the unchanged Fable input through the provider token-count endpoint.
3. Reserve cumulative worst-case cost for: valid Sol v1 actual cost, Fable v1
   truncated-attempt upper bound, one Fable v2 call at its full output cap, and
   the still-optional Sol arbitration at its full caps.
4. Refuse inference unless that cumulative value is below the same USD 10
   internal ceiling.
5. Execute Fable exactly once. Persist a receipt even if it truncates or fails
   validation; no further Fable retry is authorised.
6. If valid, compute both terminal decisions locally. Call Sol arbitration once
   only for terminal disagreements, exactly as in S137 v1.

The user-wide ceiling remains USD 50. Cumulative accounting uses the conservative
upper bound for the lost Fable v1 response, so the reported spend cannot be
understated by the missing provider receipt.

## Gate

The S137 semantic gate is unchanged: all three final questions must be
`CANDIDATE_SUCCESS_AT_10`; any real loss, invalid response, truncation or hold
keeps `chunks_v3` out of production. No fact moves to `OK` and no production,
migration, retrieval or chunker change is authorised.

