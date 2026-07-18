# S216 corrected Frontier design gate

## Objective and metric

Reduce the canonical 12 `synthesis-miss` facts without target tuning. S216 is a
development mechanism screen, not external validation and not fact credit.

## Lever and causal isolation

Terra sees only each question and emits 1–6 focus questions. The unchanged
Sonnet 4.6 generator answers every focus independently over the complete served
context. A deterministic assembler publishes only neutral `Parte N` headings
and writer outputs; focus text never enters the candidate or scorer.

Every question runs a contemporary symmetric 2x2 A/B under one commit, context,
model, system and flags. Control has one 1,600-token call per replicate;
treatment splits the same aggregate 1,600 maximum over its focuses. Thus the
lever cannot win from historical generator drift or multiplied output capacity.

## Populations and gates

The score-free packet contains 49 non-target questions:

- 14 reused S173 single-source development questions / 37 points;
- all 35 S113 non-target multi-chunk questions / 376 served chunks; after all
  generations, a separate scorer protects 87 historically OK facts.

Local GO requires 4 stable point gains, 2 stable complete-question gains, zero
development regressions and zero protected multi-chunk regressions. Reusing
S173 is explicitly non-independent; S216 may not receive a successor on those
37 points.

Only a local GO triggers a frozen blinded semantic review of all 49 questions
by Sol 5.6 xhigh and Fable 5. Each sees question, untrusted plan, sources and
two replicas per blind arm, but no gold, metric or mapping. It checks plan
coverage/scope, source support, completeness, citation faithfulness, internal
and cross-block consistency, and material loss. Any blocker is NO-GO.

## Corrections to the first duo review

- historical baseline replaced by contemporary 2x2 controls;
- aggregate output capacity equalized at 1,600 tokens per arm/replicate;
- decomposer text removed from candidate/scoring;
- missing citations now fail locally; faithfulness is claimed only after review;
- permit artifact list must exactly equal the complete preregistered set;
- multi-chunk guardrail and executable semantic review contract added;
- precall envelope drift now writes a failure receipt before stopping.

## Required reviewer decision

Verify the corrected implementation and experiment contract. PASS only if the
lever is isolated, score packets remain unavailable during generation, every
focus is assembled once without its text, output budgets are truly equal,
multi-chunk regressions and contradictions are gated, permit/freezes fail
closed, provider calls have no retry/resume, and no screen result can be framed
as external validation, production readiness or canonical fact credit.

`chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway is out of scope.
