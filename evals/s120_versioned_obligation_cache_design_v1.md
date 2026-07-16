# S120 — Versioned obligation packet and selective answer-cache invalidation

## Decision being tested

S119 found four measured synthesis omissions in three cached answers even though
the supporting evidence had reached the generator. S120 tests whether those
omissions can be represented as deterministic, source-bound answer obligations
without using evaluation IDs, expected answers, or manufacturer-specific
exceptions.

This is a local design and replay. It does **not** claim that a bot answer has
improved. A fresh, separately authorised generator probe is required before any
fact can move to `OK` causally.

## Structural rules

1. Obligations may be created only from chunks present in the final generator
   context and aligned to the product named in the question.
2. A generic family label may align to a slash-declared numeric family only
   when the evidence itself names at least two variants and every variant
   reduces to the same family after removing digits. A single sibling is not a
   family declaration.
3. Cause/effect output selection requires one product-bound UI record that
   jointly contains an activation action, an output class, and a concrete
   equipment selector. Partial records fail closed.
4. Closed-loop topology requires one product-bound record that jointly contains
   start/OUT, return, and an explicit complete-loop or return-to-panel relation.
5. Cause/effect default-rule behaviour and removal of default rules are separate
   atomic obligations. Conflicting menu numbers remain rejected and cannot
   suppress stable, non-numbered relations.
6. Every generated-answer cache key must include a canonical obligation packet
   SHA, an explicit obligation-contract version, and a SHA of the exact request
   envelope passed to the model provider. The envelope includes the fully
   rendered context headers and content, system and user messages, model,
   output limit, sampling parameters, and any provider options. Changes to any
   of these inputs invalidate reuse.

## Anti-overfit constraints

- Production planner code must contain no `qid`, fact ID, gold-answer text, or
  lookup table keyed by the frozen evaluation cohort.
- Tests must include synthetic products and both Spanish and English wording
  where the rule is language-dependent.
- Negative tests must reject partial UI records, single numeric siblings,
  unrelated slash families, incomplete loop paths, and conflicting menu
  numbers.
- The complete ordered obligation payload (statements, anchors, candidate IDs,
  source spans, facets and IDs), not just obligation kinds, must remain
  byte-identical between the versioned S119 and S120 planner contracts outside
  the three diagnostic questions.

## Local acceptance gate

- The three diagnostic questions obtain the missing structural obligation
  families from their final served context.
- All four S119 missing claims map to an atomic obligation, while no claim is
  reclassified as `OK`.
- Canonical packets and cache identities are deterministic and sensitive to
  version, evidence, headers, messages, model, and sampling changes.
- The full local planner/test chain passes with zero network, model, database,
  or serving calls.

If this gate passes, the next permissible step is a minimal fresh-answer probe
for the distinct affected questions, followed by manual atomic adjudication and
the frozen protected regression. The probe is not authorised by this document.
