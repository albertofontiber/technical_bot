# S140 - endpoint-aligned semantic-rank completion

Status: final protocol design frozen before S140 model inference.

## Objective

Complete the symmetric v2/v3 semantic MRR gate without weakening its endpoint.
The metric needs, for each opaque evidence set, whether it completely answers
the question and the smallest sufficient evidence IDs. The semantic rank is
the worst frozen rank in that set.

S138 additionally requested 20 per-item relevance records per question. Those
records are useful audit detail but do not enter semantic rank. One omission
invalidated Fable q3; attempts to make the 20-item array structurally exact were
rejected before inference by Anthropic's supported schema/grammar limits. S140
removes only this non-endpoint output burden. Judges still receive and must read
all 20 raw evidence items.

## Frozen reuse and calls

- Reuse the frozen S138 packet, private mapping, valid full Sol judgement and
  valid Fable q1/q2 judgements.
- Make one Fable xhigh q3 call returning only answerability, minimum sufficient
  IDs, confidence and short rationale for both opaque sets.
- Convert the reused full judgements to the same endpoint representation.
- If the two-arm rank tuple differs for any question, make one blinded Sol
  xhigh arbitration over all disagreements, using the endpoint schema.
- No retries or further protocol recovery.

The endpoint validator requires exact question and set coverage, valid opaque
IDs, nonempty minimum sets only for `COMPLETE`, and no duplicates. Invalid or
non-complete output is HOLD. The hybrid-MRR formula and candidate >= baseline
gate remain identical to S138.

## Cost and scope

Incremental cap worst case is USD 1.815. Including known S138 spend and the
conservative HTTP-520 reserve gives USD 4.53271250; including S137 gives USD
8.04658000. The stricter USD 10 internal ceiling remains binding.

No production, deployment, migration, chunk/retrieval/threshold change or fact
movement is authorized.
