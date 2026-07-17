# S196 — static rectangular transport compile canary

## Purpose

S196 isolates the provider-compiler boundary that stopped S195. It does not retry the
S195 cohort and does not read any real document, target, chunk table or prior author
output. Its only paid execution is one Haiku inference over two synthetic evidence
sentences after one token-count preflight.

The canary answers one upstream question: can Anthropic compile and return the exact
static transport shape proposed for the next fresh author cohort? A GO does not measure
gold quality, planner recall, target facts or production behavior. It only authorizes a
separate S197 source freeze and author→Luna evaluation.

## Clean transport

The S195 compiler rejection combined four answer-point slots, three support slots,
per-excerpt ID enums and `$defs`. S196 removes the dynamic and compositional elements
instead of weakening the canonical contract:

- four answer-point objects are always present;
- each point has `active`, `claim`, `facet`, `support_1`, `support_2`, `support_3`;
- unused strings are `""`; inactive slots contain no other content;
- the provider schema contains no arrays, refs/defs, combinators, enums or consts;
- source-ID membership, one-to-three cardinality, uniqueness, contiguity, facet
  membership, item identity and inactive-slot emptiness are enforced deterministically;
- the schema is identical for every future excerpt. Source IDs exist only in the prompt
  and deterministic validator, never in the provider grammar.

This is the reusable clean boundary requested after S195: provider grammar expresses a
fixed record layout; deterministic code enforces corpus-specific invariants. S197 must
retain both halves. It may not turn the generic strings into an unvalidated free-form
contract.

## Frozen synthetic fixture and gates

The fixture uses `SYNTHETIC_VENDOR / CANARY_MODEL_1` and two invented evidence-unit IDs:

1. `E001`: disconnect electrical power before maintenance;
2. `E002`: reinstall the safety cover before restoring power.

The author must return an eligible question, exactly two contiguous active points,
known/unique support IDs covering both units, allowed facets, and two empty inactive
slots. A preflight 400 is `NO_GO_PREFLIGHT_REQUEST_REJECTED` and cannot claim anything
about schema compilation. An inference 400 is `NO_GO_STATIC_SCHEMA_COMPILE_REJECTED` only
when the sanitized provider message explicitly attributes it to schema compilation or
complexity; other inference 400s are `NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED`.
A compiled schema with invalid content is `NO_GO_STATIC_TRANSPORT_VALIDATION`. Only
compilation plus deterministic validation yields `GO_STATIC_TRANSPORT_COMPILED`.
Because the fixture is synthetic, the raw provider JSON is persisted alongside its hash
so a blocking validation decision can be reproduced and inspected.

There is no retry after the run acquires authority. The Anthropic client uses
`max_retries=0`; an immutable exclusive lock is acquired before the token-count request,
then a separate immutable pre-paid checkpoint is acquired before the one inference.
Final receipts and result use same-directory temp files plus atomic replace, so neither
immutable authority file is truncated during finalization. Budget is capped at $0.02,
with one inference and at most two provider requests within this workspace. The file lock
does not claim cross-host/global exclusion; repository history and the sealed permit make
any execution from another checkout auditable, but are not a shared idempotency service. Haiku
4.5 is the economic execution model. Sol 5.6 xhigh is used only for critical design
review; Fable 5 is the second independent frontier reviewer when its executor exists.
The runner contains its own schema formatter, cost calculation, facet vocabulary,
stable hashing, error sanitizer and chunks_v3 receipt. `requirements.txt` is recorded as
context, while the dependency frozen as part of the provider-serialization boundary is
specifically Anthropic SDK `0.97.0`; the runner verifies and records that resolved version
before acquiring the lock or sending a request. It does not claim a fully hermetic Python
environment. Tests exercise the
zero-retry client, exclusive lock→preflight→immutable checkpoint→paid inference order,
second-run exclusion, budget stop and stage-specific 400 classification.

## What S196 cannot claim

- no real-document, language, table/prose, manufacturer or semantic generalization;
- no evidence that Haiku will author a valid 14-item cohort;
- no external Luna semantic validation;
- no planner 90/80/75 measurement and no protected target opening;
- no runtime/default-off integration, database write, production or fact credit.

`chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. S196 neither reads nor writes it
and cannot reopen that ranking decision. Its receipt points to the canonical roadmap and
does not duplicate historical ranking metrics. Railway is a demo and is not a PR/merge gate.
