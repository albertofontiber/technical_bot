# S139 - schema-hardened completion of the S138 semantic MRR gate

Status: design frozen before implementation and provider calls.

## Why S139 exists

S138 produced one valid Sol judgement and valid Fable judgements for questions
1 and 2. Fable question 3 returned structured JSON and selected a minimum
sufficient set for both arms, but omitted one of the 20 required per-item
assessments. The local validator correctly rejected it. S138 therefore has no
aggregate and remains HOLD; the omitted assessment may not be inferred or
patched after seeing the answer.

The generic provider schema allowed a variable-length assessment array while
the stricter completeness rule existed only in local validation. S139 repairs
that protocol gap generically: it generates a packet-specific JSON schema whose
array positions require every opaque set and evidence ID exactly once. This is
content-agnostic and reusable for any blinded packet.

## Frozen reuse and new calls

S139 reuses without modification:

- the S138 packet, private rank mapping, rubric, validation and MRR formula;
- the complete valid Sol judgement for all three questions;
- Fable question-atomic judgements 1 and 2.

It authorizes one Fable xhigh call for question 3 under the hardened schema.
If valid, it combines the three independent judgements. Any two-arm semantic
rank tuple that differs from Sol is sent together in one final blinded Sol
xhigh arbitration, also under a packet-specific schema. No retry is allowed.

## Gate and cost

The S138 gate is unchanged: all three final two-arm semantic tuples must be
valid and candidate hybrid MRR@10 must be at least baseline. S139 also counts
the already-paid invalid Fable output and conservatively reserves the unknown
cost of the pre-response HTTP 520.

Before token counting, incremental worst case is USD 2.705. Including all known
S138 spend and the HTTP-520 reserve gives USD 5.42271250, below the frozen S138
USD 10 internal ceiling. Including S137 gives USD 8.93658000. The broader user
ceiling remains USD 250.

No production migration, deployment, chunk change, retrieval change, threshold
change or fact movement is authorized.
