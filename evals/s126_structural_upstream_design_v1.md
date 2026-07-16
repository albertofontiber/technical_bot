# S126 structural upstream design v1

## Frozen problem

The reconciled residual population contains four retrieval misses, two
synthesis misses and one source-contract hold.  This design addresses only the
four retrieval misses.  It must not claim an OK answer or modify gold facts.

| Claim | First failed stage | Structural cause | Candidate mechanism |
| --- | --- | --- | --- |
| `cat017#2` | retrieval | a quantified entitlement prerequisite is outside served context | typed prerequisite coverage |
| `hp010#1` | retrieval | an access prerequisite is outside served context | typed prerequisite coverage |
| `cat013#0` | retrieval | compatibility navigation and evidence validation omit loop topology | compatibility evidence contract |
| `cat013#1` | retrieval | an accepted secondary document binding was stranded on another branch; compatibility validation omits protocol/device rosters | port accepted binding plus compatibility evidence contract |

`hp011#2` and `hp011#3` already have decisive evidence in served context and
therefore stay downstream in synthesis. `cat008#3` stays outside bot tuning
until its contradictory terminal assignments are adjudicated from the source
document.

## Mechanism A: governed data reconciliation

Port only the already-adjudicated `MIDT190 -> notifier:sdx-751` secondary
document binding from commit `5f06ab5`.  Preserve its original provenance.
This is integration-debt repair, not a new fact-specific inference.  The
catalog must validate with zero errors and unrelated bindings must not change.

## Mechanism B: typed prerequisite coverage

Reuse the existing shadow-only procedure prerequisite selector for two
manufacturer-independent relations:

1. an access or authorization condition that precedes a requested technical
   action in the same governed document;
2. a quantified entitlement relation containing a licence, a distributive
   quantifier and its governed unit (for example per loop, channel or panel).

No QID, expected answer, fact key or gold receipt may reach selection. Existing
known-cohort recovery is development evidence only. Release remains blocked
until a preregistered independent opportunity set exercises the applicable
facets with zero false-positive selections.

The explicit-reference facet is excluded from this S126 candidate because its
earlier section challenge did not converge.

## Mechanism C: compatibility evidence contract

Compatibility questions require complementary evidence, not a single generic
similarity winner. A bounded, canonical-document navigation lane may return at
most three exact source spans covering distinct relation types:

1. protocol or manufacturer-family scope;
2. an official compatible-device roster containing the queried device;
3. loop topology or installation constraints relevant to interoperability.

The candidate vocabulary is generic, bilingual and contains no manufacturer,
product, QID, answer value or numeric target. Every appended span must be an
exact receipt from a catalog-authorized document. HYQ prose remains navigation
metadata and is never served as evidence.

The three-span ceiling is intentional for multi-entity compatibility: one span
for each complementary obligation and no duplicate facet. It is a retrieval
precondition only; synthesis must still refuse unsupported cross-manufacturer
compatibility conclusions.

## Cheap gate order

1. deterministic unit and config tests;
2. local frozen-snapshot replay over the exact four retrieval claims;
3. read-only document-scoped HYQ probe for `cat013` only, with zero model calls
   and zero database writes;
4. protected frozen regression before any serving integration;
5. adversarial review for convergence on safety, provenance and scalability.

## Decision rules

- A recovered retrieval claim moves only to the next failed stage; it does not
  become OK automatically.
- Any cross-product or cross-document evidence outside canonical scope is an
  automatic NO-GO.
- Any source receipt mismatch is an automatic NO-GO.
- Zero applicable independent prerequisite examples is inconclusive, not GO.
- The source-contract hold cannot earn bot-improvement credit.
- Serving remains default-off until all applicable gates pass.
