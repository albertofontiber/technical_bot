# S175 compact, routed answer policy v1

## Decision being tested

The current generator sends a large monolithic policy to every question. It
contains useful safety rules, but also unrelated behaviours, repeated rules and
conflicting cross-brand instructions. S175 tests whether a small policy for the
concrete, source-answerable route improves faithful coverage while reducing
input tokens. It is an evaluation-only candidate and does not modify runtime.

This is a policy-routing experiment, not a weaker safety policy. The compact
route retains the invariant rules: source-only claims, exact inline citations,
preserved conditions/polarity/units, explicit insufficiency and no unsupported
compatibility or absence inference. Ambiguity, cross-brand compatibility,
urgent operation and selection remain separate routes and are outside this
screen.

## Population and isolation

Use the sealed S173 cohort: 14 concrete questions, 14 manufacturers, seven
table and seven prose excerpts, one correct source excerpt per question and no
target-question overlap. Reuse the already checkpointed S173 current-policy
answers as the baseline. The candidate sees question, source metadata and
source excerpt only. Answer points are loaded only after all 14 candidate
responses have been checkpointed.

The cohort has been used in prior development and can only screen the design.
It cannot authorize production. A local pass authorizes a blinded adversarial
review and then a separately frozen target probe; it does not authorize either
step automatically.

## Candidate policy

The route must:

1. answer the exact question first;
2. include every source detail that materially changes execution,
   interpretation or safety of that answer;
3. preserve conditions, scope, polarity, mappings, units and warnings;
4. exclude merely adjacent information;
5. cite every factual sentence or bullet with the exact fragment number;
6. state insufficiency instead of completing a relation from prior knowledge;
7. avoid follow-up suggestions and Markdown tables;
8. finish with the source manual named in the fragment header.

No benchmark ID, target kind, answer point, expected value, manufacturer rule
or product-specific template may enter the candidate prompt.

## Frozen screen

The same `claude-sonnet-4-6` writer is used for baseline and candidate
comparability. Temperature is zero, output is bounded to 1,800 tokens and no
retry is allowed. The candidate must achieve all of:

- at least four additional answer points over the 26/37 frozen baseline;
- at least two additional complete questions over the 6/14 baseline;
- zero regressed answer points;
- zero invalid fragment citations or token-limit stops;
- at least 35% fewer counted input tokens;
- actual cost below the internal $1 ceiling.

Failure closes this version. No prompt tuning or target execution follows a
failure. Passing only authorizes a blinded semantic/adversarial review of the
sealed outputs before any target or runtime work.

