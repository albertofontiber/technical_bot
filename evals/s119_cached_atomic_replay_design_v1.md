# S119 cached atomic replay design v1

## Decision scope

S119 resolves the 22 `pending-replay` transformed claims in the S118 hybrid
diagnostic bridge using only already-frozen S113 contexts and answers.  It is a
retrospective cache audit, not a prospective holdout and not an official atomic
benchmark.

The replay answers three separate questions per claim:

1. Does source-bound support reach the exact frozen generator context?
2. Does an exact frozen S113 answer exist for that context?
3. If it exists, does it satisfy a claim-specific semantic coverage contract?

No missing answer is labelled `synthesis-miss`.  It is labelled
`synthesis-not-measured`.  No missing evidence binding is guessed to be a
retrieval or rerank failure; it is labelled `evidence-binding-unresolved` until
an earlier-stage receipt can close the boundary.

## Anti-overfit controls

- The population is the exact set of 22 S118 `pending-replay` claim IDs.
- Source semantics come from the pre-existing S106 P0 selection adjudication,
  projected with its original file SHA-256.
- Evidence is bound to qid, chunk ID, source file, page and content SHA-256.
- A separate answer-independent adjudication binds every S118 claim text,
  value, citation and source-page identity to accepted support spans.  It also
  records why apparent page/manual differences are offsets, revision updates,
  or explicitly accepted same-product workflow equivalences.
- Multi-chunk claims require every declared evidence group.
- Synthesis rules are claim-specific bounded semantic spans; anchor presence
  alone is not sufficient when the claim contains a relation or instruction.
- The contract cannot contain runtime outcome fields.
- The 11 available answer SHA-256 values have a separate retrospective manual
  semantic adjudication.  Regexes remain machine receipts; they are not the
  sole authority for polarity or verdict.
- Inputs and outputs use strict duplicate-key parsing, allowlisted outputs and
  atomic replacement.
- The original S118 bridge and all gold rulers remain immutable.

## Stage policy

| Condition | Diagnostic result |
|---|---|
| One or more required evidence groups do not bind | `evidence-binding-unresolved` |
| All evidence groups bind, but no exact frozen answer exists | `synthesis-not-measured` |
| Evidence binds and the answer exists, but a coverage rule fails | `synthesis-miss` |
| Evidence binds and every coverage rule passes | `OK` |

An `OK` is an observed classification inside the S118 hybrid diagnostic view.
The seven observed OK claims come from pre-existing cached answers: S119 makes
no runtime change, moves zero facts causally, and claims no bot improvement.
S119 must leave the official atomic denominator, target and OK count null.

## Cost and authority

The authorized execution surface is local filesystem reads plus two canonical
JSON outputs.  Network, database, retrieval, rerank, model, serving, deploy and
gold mutation are all forbidden.  Expected model and network calls are zero.

## Exit gate

S119 can receive a restricted GO when:

- the 22-claim population is bijective;
- every projected S106 source row is hash-bound;
- every claimed generator pass has an exact chunk receipt;
- each response has the exact per-qid serving-context SHA used by S113;
- each cached-answer verdict agrees with the frozen manual adjudication;
- missing answers remain unmeasured;
- the replay is byte-deterministic;
- negative tests reject drift, duplicate keys, forbidden outcome fields and
  non-canonical outputs;
- an adversarial reviewer finds no P0/P1 blocker.
