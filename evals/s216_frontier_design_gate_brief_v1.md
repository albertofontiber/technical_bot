# S216 Frontier design gate

## Objective and metric

Reduce the canonical 12 `synthesis-miss` facts without target tuning. The first
measured metric is a non-target development screen: improve at least 4 of 37
frozen answer points and 2 of 14 complete questions, with zero point regression,
invalid citation, invalid decomposition, or incomplete call. This screen moves
zero canonical facts and is not external validation.

## Proposed architectural lever

The current generator answers a compound question in one call over the full
served context. S216 decomposes only the question with economical Terra, then
runs the unchanged Sonnet 4.6 generator independently for every validated focus
over the same complete served context. A deterministic assembler includes every
block exactly once; no final model may compress the blocks.

The decomposer sees no source, gold, answer, QID, target, or previous failure.
It cannot select evidence or write claims. The four canonical target questions
remain unopened until a local pass and an independent Sol/Fable semantic result
pass. A target pass would still require protected regression and later external
validation before production.

## Authorities to review

- `evals/s216_decomposed_synthesis_design_v1.md`
- `evals/s216_decomposed_synthesis_prereg_v1.yaml`
- `src/rag/decomposed_synthesis.py`
- `scripts/s216_run_decomposed_synthesis_screen.py`
- `tests/test_decomposed_synthesis.py`
- `evals/s153_research_branch_closeout_v1.yaml`
- `evals/s155_question_conditioned_claim_map_gate_v1.yaml`
- `evals/s156_frontier_synthesis_ceiling_attribution_and_gate_v1.yaml`
- `evals/s173_single_source_omission_correction_gate_v1.yaml`
- `evals/s206_answer_facet_ledger_closure_v1.yaml`

## Required reviewer decision

Review implementation and experiment contract, not hypothetical target outputs.
Return PASS only if the mechanism is materially distinct from closed lines,
question-only decomposition is actually enforced, assembly cannot silently drop
a focus, score isolation and no-retry/cost bounds fail closed, and the result
cannot be framed as generalization, external validation, production readiness,
or canonical fact credit. Flag any unsupported claim, target leakage, hidden
retry path, prompt-injection privilege escalation, metric mismatch, or unsafe
multi-block contradiction path. Railway and deployment are out of scope;
`chunks_v3` remains wholesale NO-GO.
