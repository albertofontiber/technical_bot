# S138 — symmetric semantic fallback MRR for the three S137 questions

Status: design frozen before implementation or model calls.

## Objective and scope

S135's exact-provenance proxy missed three candidate top-10 successes. S137
proved that each candidate top-10 contains a minimum sufficient answer. Because
using those semantic ranks only for v3 would be asymmetric, S138 measures both
v2 and v3 on exactly those three fallback questions.

All other 21 S135 questions retain their frozen exact-gold MRR contribution.
Questions where both arms already have an exact gold hit do not activate the
semantic fallback, even when their exact ranks differ. This is a conditional
proxy-repair rule, not a replacement semantic evaluation invented for all rows.

## Frozen evidence and blinding

The local builder reconstructs the frozen S135 baseline and candidate
populations and reruns the same keyword plan, PostgreSQL FTS configuration,
manufacturer/model filters and ID tie-break. For each fallback question it takes
top 10 from both arms.

Each arm becomes an opaque evidence set and every chunk an opaque evidence ID.
Set order and item order are deterministic hash order. Judges see question,
manufacturer/model, section/page metadata and raw source content. They do not
see arm, rank, score, gold, donor/context status, database IDs, S135/S137 labels,
or the private mapping. Generated contextual prose is excluded from semantic
judgement.

For each of the two anonymous sets, a judge must classify every item and choose
the smallest sufficient set. The semantic rank is the worst frozen rank among
that minimum set. `PARTIAL`, `NONE`, invalid output, or any selected item outside
top 10 becomes `HOLD`.

## Judges and convergence

- Primary: one structured `gpt-5.6-sol` Responses call, `xhigh`, containing all
  three questions.
- Independent: three question-atomic structured `claude-fable-5` calls,
  adaptive thinking and `xhigh`.
- Both receive the same rubric and evidence. Neither sees the other's output.
- If their two-arm semantic-rank tuple differs for a question, one blinded Sol
  arbitration covers only the disagreement questions. No retries are allowed.

## Hybrid MRR and gate

For each arm:

1. start with its frozen S135 reciprocal-rank sum;
2. remove that arm's original contribution for the three fallback questions;
3. add `1 / semantic_rank` from the final symmetric S138 adjudication;
4. divide by 24.

This applies the same fallback definition to v2 and v3. Promotion readiness
requires: three valid final two-arm tuples, candidate hybrid MRR@10 not below
baseline, the S137 hit/recall reconciliation still passing, all manifests and
validators passing, and spend below the S138 USD 10 ceiling. It remains a shadow
promotion decision only; no production migration, fact movement or deployment
is authorised.

