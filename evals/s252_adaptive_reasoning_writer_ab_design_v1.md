# S252 — Freeze-hardened adaptive-reasoning writer A/B

S252 is the one permitted successor to the adversarially closed S251. It keeps
the same inference question and fixes every confirmed review finding without
changing the semantic arms.

## Arms and attribution

Control and treatment use `claude-sonnet-4-6`, the current fidelity system
prompt, guided plan, sealed 51-fragment `chunks_v2` context and an 8,000-token
ceiling. Control uses `temperature=0`; treatment is the provider-supported
package `adaptive thinking + effort=high + temperature omitted`. Results are
called stable observed package differences, never an isolated causal effect of
thinking.

There are exactly two paired replicates per question and exactly 16 semantic
calls. Transport and semantic retries are both zero. Any failed or non-`end_turn`
call closes the run. The provider-visible system and user messages are
byte-identical between arms.

## Two-phase freeze

The generation score packet remains absent from provider inputs. A pre-run
execution permit binds the design, runner and sealed generation packet.

After all generation outputs are complete, a separate local builder verifies
the preregistered SHA-256 values for:

- the score packet;
- the scorer itself;
- the shared scoring core;
- `s201_real_question_planner_gate.py`;
- `answer_planner.py`, `omission_correction.py` and `visual_gold.py`.

It then creates a sealed score-execution permit that additionally binds the
exact completed generation artifact SHA-256. The scorer refuses to run without
that post-generation permit and independently rechecks every bound hash. This
closes the S251 generation-to-scoring interval.

The scorer also rejects any question without exactly two replicas whose IDs are
exactly `{1, 2}`, or any replica lacking non-empty control/treatment answers.

## Deterministic gate

All 20 frozen obligations and the frozen conflict are scored. GO to semantic
review requires:

- at least two stable observed residual gains present in both treatment
  replicas and absent from both control replicas;
- stable treatment residual coverage greater than control;
- zero protected canonical-obligation regressions;
- zero unsafe conflict selections;
- zero invalid citations;
- observed successful-response usage below $15.

The preflight is a conservative response-usage bound, not a provider billing
guarantee. There are no retries; any transport ambiguity closes the run and
must be reconciled against provider billing before any release claim.

## Semantic and release boundary

A deterministic GO grants zero fact credit. Sol 5.6 xhigh and independent
Fable 5 must inspect every full treatment answer against the full frozen source
context, not only recovered obligations. They must confirm the proposed gains,
reject unsupported new claims even when citation numbers are in range, and
check protected content and conflict handling. One adjudication round only.

Only a dual semantic pass can open a full regression of the current 143 OK
facts. No effort, prompt, model, token or same-target tuning follows either a
GO or NO-GO. Railway is not a merge gate. `chunks_v2` remains active/read-only;
wholesale `chunks_v3` remains final no-go.

