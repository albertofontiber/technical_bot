# S139 v2 - provider-compatible exact keyed schema

Status: design addendum frozen after the no-inference schema preflight failure
and before any S139 model inference.

Anthropic rejected the v1 packet-specific schema at token counting because its
structured-output subset does not support `maxItems`. No model response or
token usage exists. The evidence-completeness objective is unchanged.

V2 represents the judgement as nested closed objects keyed by the already
opaque question, evidence-set and evidence IDs. Every key is listed in both
`properties` and `required`, with `additionalProperties: false`. This guarantees
every question, set and evidence assessment exactly once without array-length,
tuple-array or uniqueness keywords. A deterministic local adapter converts the
keyed provider output to the frozen S138 array contract, then the unchanged
S138 validator and semantic-rank logic run.

The same v1 call limits, evidence, models, rubric, MRR gate and budgets apply:
one Fable q3 completion and at most one Sol arbitration, with zero retries. A
provider token-count call must accept the keyed schema before inference.
