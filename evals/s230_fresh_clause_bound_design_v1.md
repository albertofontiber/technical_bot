# S230 - fresh pixel cohort and clause-bound causal canary

## Frozen problem

The canonical score remains 143/157 facts OK (91.08%): 12 synthesis misses
and 2 retrieval misses. Prior work already established that decisive evidence
reaches the generator for the synthesis misses. Monolithic rewrites and
addenda can recover facts but also delete, contradict, or add unsupported
claims. Those lines are closed and are not repeated here.

## Fresh population

The candidate population was selected before any model or bot output. Exact
source-identity exclusion covers S203-S217 and the official gold. Three
apparently fresh PDFs were rejected because they appeared anywhere in official
gold provenance. The frozen packet therefore uses only two wholly unseen Kidde
PDF identities and six non-overlapping pages:

- one cross-document Class A versus Class B loop item;
- one distant-page battery configuration/location item;
- one adjacent-page output termination/count item.

Every page was rendered at 200 dpi and inspected at original resolution. Gold
questions and answers are not hand-authored: Sol 5.6 xhigh and Fable 5 each
author every item independently from pixels, then cross-review the other
candidate. Sol maps immutable accepted facts to exact evidence-unit IDs and
Fable independently reviews the mapping.

## Transport and stopping

Each item is a separate provider call. Both providers receive strict JSON
schemas. An append-only provider receipt is written before semantic validation,
and a separate attempt checkpoint is written before each call. There are zero
retries, no candidate repair or merge, at most 18 gold calls, and no target,
retrieval, database, production, deployment, or official-credit action.

## Structural A/B after a gold GO

Only if all three items pass authorship, reciprocal pixel review and support
mapping, run a fresh causal canary with identical question, evidence and writer
family in both arms:

- control: one monolithic answer call over all exact evidence units;
- treatment: a low-cost planner binds 1-8 question obligations to exact unit
  IDs; one strictly structured writer call produces each obligation block from
  only its bound units; a local validator rejects unknown or out-of-bound IDs;
  deterministic assembly emits each validated block once and derives citations
  from source identity.

The treatment has no final rewrite and cannot silently discard an accepted
block. Provider calls are checkpointed before validation. Two replicates are
used. A local exact matcher may only open blind semantic review; it cannot grant
facts. Sol 5.6 xhigh is principal semantic reviewer and Fable 5 is independent.
The external gate requires stable treatment completeness gains on at least two
of three items, zero supported-fact regressions in any replicate, zero invalid
IDs/citations/claims, and dual semantic PASS. A failure closes this mechanism
without tuning on the same pages.

Even a full external PASS authorizes only a pre-registered bounded probe on the
12 synthesis targets. It does not change production defaults or facts OK.

## Invariants

- `chunks_v2=ACTIVE_READ_ONLY`.
- `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; no wholesale rerun.
- production defaults remain unchanged.
- Railway is a demo and never a PR or merge gate.
- budget ceiling is the user's USD 200; this stage stops internally at USD 150.

