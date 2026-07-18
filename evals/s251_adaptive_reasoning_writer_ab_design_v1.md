# S251 — Adaptive-reasoning writer A/B v1

## Question

Does adaptive reasoning in the current `claude-sonnet-4-6` writer reduce the
twelve frozen synthesis omissions without changing retrieval, evidence,
prompt, obligation guidance, model identity or answer assembly?

This is a downstream inference-mode experiment motivated by S243: eleven of
twelve residuals lose detail inside fragments already cited. It follows local
no-go results for S248/S249 and does not reopen their extractor designs.

## Frozen arms

Both arms use the sealed S235 generation packet: four questions, 51 immutable
`chunks_v2` fragments, the current fidelity prompt, code-gated selection block,
guided answer plan, Sonnet 4.6, and an 8,000-token response ceiling.

- Control: `temperature=0`, no thinking fields.
- Treatment: no temperature field; `thinking={"type":"adaptive"}` and
  `output_config={"effort":"high"}`. Anthropic requires the temperature
  difference as part of the thinking feature envelope; it is not an
  independently tuned variable.

The provider-visible system and user messages must be byte-identical between
paired arms. The treatment receives no hidden checklist, gold, residual ID,
answer, score field or target label. Text extraction ignores thinking blocks
and returns only provider text blocks.

Each question receives two paired replicates, interleaved control/treatment.
There are 16 semantic calls, no semantic retries, and at most one retry for a
transient transport status. A retry repeats the exact same labelled request.

## Why direct target use is bounded

The twelve misses and their evaluator are already frozen and have been exposed
by prior diagnostics. S251 does not tune a prompt or detector against them; it
tests one provider-supported, global inference setting exactly once. The score
packet remains unopened until all generation outputs are checkpointed.

A positive result is not production proof. It authorizes one semantic review
and then a full protected-fact regression. No further effort level, token
budget, prompt or same-target iteration is allowed from this result.

## Gates

The frozen deterministic evaluator scores all 20 obligations, not only the 12
residuals, and the one known conflict. GO to semantic review requires:

- treatment has at least two strict causal residual gains present in both
  treatment replicates and absent from both control replicates;
- stable treatment residual coverage exceeds stable control coverage;
- zero protected canonical-obligation regressions;
- zero unsafe conflict selections;
- zero invalid citations;
- every response ends normally with non-empty text;
- actual experiment cost remains below $15.

Sol 5.6 xhigh is the principal design reviewer and Fable 5 is the independent
frontier reviewer. One review round only; disagreement or any critical blocker
closes the experiment. The review itself does not inspect either reviewer's
output and does not create a convergence loop.

## Release boundary

Even a deterministic-score GO moves zero official facts until a one-shot dual
semantic adjudication confirms the gains. A confirmed target gain still cannot
turn the flag on by default before the current 143 OK facts pass a full
protected regression. Railway is a demo and never blocks a green merge.
`chunks_v2` remains active/read-only; wholesale `chunks_v3` remains final no-go.

