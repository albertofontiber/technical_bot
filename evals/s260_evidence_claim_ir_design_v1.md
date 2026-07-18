# S260 - source-bound AnswerIR with deterministic rendering

## Objective

Test one clean synthesis architecture against the twelve frozen synthesis
misses. The model does not write a free-form answer and no post-answer patch is
applied. An economical model emits an intermediate representation (IR) of
atomic, complete, source-bound claims. Local code validates every source
reference and deterministically renders every accepted claim exactly once.

This attacks the largest causal family identified in S243: conditions, scope,
bounds and other qualifiers disappearing inside evidence that the answer
already cites. The IR instruction is generic. It contains no QID, evaluator
obligation, target anchor, product-specific template or gold text.

## Treatment

- Input: the four already-sealed questions and their 51 served chunks from the
  S235 generation-only packet.
- Model: `gpt-5.6-terra`, reasoning `medium`, two replicas per question.
- Output: 1-18 claims. Each claim is a single complete technical relation and
  names 1-3 source fragment numbers. Claims cannot contain citation markers.
- Local validation: rejects unknown fragments, duplicate fragment references,
  duplicate claims, multiline claims, unbounded text or writer-authored
  citations.
- Rendering: emits every accepted claim once and derives `[F<n>]` citations and
  a source list locally. There is no final rewrite, planner, selector, addendum,
  retry, retrieval or database call.

The instruction requires a claim to retain subject, predicate, object and all
material conditions, scope, units, bounds, granularity, prerequisites,
warnings and verification requirements. Conflicting source statements must be
reported separately and must not be resolved by inference. Counts may only be
asserted when the source states the count or the rendered claim enumerates the
members.

## Evaluation and stopping

Generation cannot open the physically separate S235 score packet. Only after
all eight responses and the generation artifact are sealed does the scorer
open the 20 frozen obligations, 12 residual IDs and one conflict. A separate
post-generation builder verifies the exact eight-call ledger and freezes the
generation artifact, ledger, preregistration, execution permit, scorer and all
scoring dependencies in a score-execution permit. The scorer fails closed on
any mismatch.

The local gate requires:

- at least three residual obligations covered in both replicas;
- at least two stable gains from `compound_relation_qualifier_loss`, the
  largest residual family;
- zero loss, in either replica, of any obligation covered by the canonical
  answer;
- zero unsafe conflict handling and zero invalid citations;
- all calls complete and total cost below USD 5.

This is a one-shot target mechanism screen, not independent validation. A local
GO grants no fact credit and no production authorization. It only opens one
blind full-answer review by Sol 5.6 xhigh (principal) and Fable 5 (independent),
followed by the full protected regression suite. A local NO-GO closes S260 with
no prompt adjustment, reasoning change, third replica or successor correction
loop.

## Prior lines not reopened

S260 is not a direct model substitution (S156/S192), typed relation store and
selector (S153/S186/S193), free-form prompt rewrite (S175/S247), question
decomposition (S216), clause-bound multi-writer assembly (S235/S242), or a
post-answer rewrite/addendum (S220-S223). Its causal package is a directly
generated answer IR plus deterministic publication of every validated claim.

`chunks_v2=ACTIVE_READ_ONLY`; `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.
Production defaults remain unchanged and Railway is not a PR or merge gate.
