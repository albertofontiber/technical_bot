# S122 — Enforced, source-bound answer contract

## Objective

S121 proved that adding factual obligations to the prompt is insufficient: the
generator can ignore them, can obey a competing clarification heuristic, and can
select one side of rejected document conflicts. S122 makes the contract an
enforced runtime boundary while keeping the mechanism manufacturer-independent,
default-off and cheap to test.

This phase is local only. It performs no model, network, retrieval, rerank,
database, serving or deployment calls and cannot move another fact to official
`OK`.

## Versioned runtime contract

`ANSWER_OBLIGATION_PLANNER=enforced` activates a new S122 contract. Existing
`off`, `observe`, `supplement` and `guided` behaviour and the frozen S119/S120
planner versions remain reproducible.

The S122 answer contract contains two separately validated collections:

1. **Obligations** — positive, atomic, source-bound relations extracted only
   from the final served context. Each retains fragment, candidate, source span,
   semantic kind and anchors.
2. **Evidence conflicts** — mutually incompatible values for one semantic slot.
   A conflict is a first-class constraint; silently dropping it from the plan is
   no longer sufficient. The first implementation covers cause/effect menu
   numbers through a generic semantic slot, with a versioned schema that can be
   extended to numeric specifications without product exceptions.

The exact ordered contract, exact provider envelope, enforcement policy,
validator, renderer and conflict-schema versions are part of answer-cache
identity. An answer produced under S120 cannot be reused under S122.

## Precedence rules

1. The provider **system** envelope contains only code-authored enforcement
   policy. Source statements never receive system privilege: the ordered
   evidence payload is serialised as JSON inside an explicitly delimited data
   block in the application-built user message. Post-generation enforcement,
   not prompt obedience, remains authoritative.
2. A bounded family alignment admitted by the contract authorises only the
   shared relation represented by that obligation. It does not globally convert
   a family query into a specific-product query and does not relax alignment for
   other facts.
3. Every conflict slot is bound to product/family and semantic operation. A
   conflict may be omitted when irrelevant. If the response mentions its
   semantic slot, it must disclose the conflict and may not select one value as
   authoritative. S122 v1 never auto-resolves a document conflict; future
   resolution requires comparable document identities and a separately
   versioned, strict revision precedence rule.
4. No prompt instruction can turn a failed post-generation contract validation
   into a successful response.

## Closed execution loop

1. Build the S122 contract from the final served chunks.
2. Generate once using code-authored policy in the system envelope and the
   delimited evidence contract as data in the user envelope.
3. Validate obligation coverage and conflict safety deterministically.
4. If valid, return the generated answer byte-for-byte.
5. If invalid, discard the unsafe prose and reconstruct a concise, explicitly
   labelled **respuesta parcial protegida** only from the contract's source
   statements and conflict notices. Do not append to the unsafe draft and do
   not make a second model call.
6. Revalidate the reconstructed response.
7. Each obligation kind declares which query intents it can cover directly. If
   the contract does not cover the query core, return `fail_closed`: it may list
   validated prerequisite facts, but must state that the requested procedure is
   incomplete and direct the technician to the exact manual/revision. Never
   present auxiliary facts as a complete answer.
8. If reconstruction itself fails validation, return the same fail-closed
   boundary without the invalid reconstruction. Expose the status in metadata
   and never return the invalid draft.

Reconstruction is a safety path, not a normal answer style. It deliberately
trades breadth for groundedness only when the generated draft has already failed
the contract.

## Semantic validation changes

- Each relational kind is validated inside a bounded clause/window and has an
  explicit polarity guard. Tokens scattered across unrelated paragraphs cannot
  satisfy a relation; negated or contradictory predicates fail validation.
- `cause_effect_output_selector` requires the positive activation action and a
  concrete output class/identifier in one bounded relation window. A downstream
  loop-device navigation label is not allowed to over-constrain an atomic claim
  about selecting the output.
- Inflected positive deletion forms such as `deben eliminarse` satisfy the
  deletion relation; `no deben eliminarse` and equivalent negations fail.
- `closed_loop_return_path` requires start/OUT, return and an explicit
  closed/complete return relation in one bounded window. `No es un lazo cerrado`,
  `no retornar` and mixed positive/negative topology fail.
- If an end-of-line-resistance question has a validated closed-loop obligation,
  reconstruction answers narrowly for that loop and explains that the cable
  returns to the panel. It must not generalise the conclusion to siren or
  peripheral circuits.

## Cost and failure budget

- Maximum provider calls per normal answer remain **one**.
- Validation and reconstruction are local string/contract operations.
- No LLM judge participates in serving.
- Metadata records `pass`, `source_bound_reconstruction` or `fail_closed`, plus
  initial/final validation and conflicts, so the funnel remains auditable.

## Anti-overfit requirements

- Production code contains no qid, fact ID, expected-answer string or product-
  keyed exception.
- Synthetic Spanish and English products exercise every semantic rule.
- Negative tests cover partial output selectors, incomplete loop topology,
  cross-paragraph token scattering, negated relations, one-sided conflict
  assertions, disclosed conflicts and unrelated RFL circuits.
- Before implementation, a replay over the frozen 39 questions and its exact
  allowlist are preregistered. Answers that pass remain byte-identical and
  unexpected `source_bound_reconstruction` or `fail_closed` outside that
  allowlist must be zero.
- The frozen 39-question obligation packets must change only where the S122
  contract explicitly corrects validator/constraint semantics; every change is
  listed before any paid probe.
- Local replay of S121 answers is diagnostic only. It cannot claim causal answer
  improvement because no new response has been generated.

## Local GO gate

- `hp005` passes without reconstruction under exact-claim output-selector
  semantics.
- The unsafe `hp009` draft cannot be returned; the reconstructed answer covers
  the closed loop and OUT-to-return path without repeating the universal RFL
  error.
- The unsafe `hp017` draft cannot be returned. Because its obligations are
  prerequisites rather than complete delay-programming coverage, the safe output
  is explicitly fail-closed/partial, covers default-rule deletion and Rule 1
  behaviour, and does not select menu 7 or 8.
- All targeted, protected and full tests pass with zero external calls.
- Adversarial review has no open P0/P1 before seeking separate authorisation for
  a bounded fresh probe.
