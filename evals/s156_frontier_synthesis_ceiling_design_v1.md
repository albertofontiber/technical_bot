# S156 frontier synthesis ceiling probe

## Decision

The four remaining source-attested synthesis questions are already served their
decisive evidence. Before adding another extraction or agent loop, S156 measures
whether a stronger single-pass generator can close the omissions with the exact
frozen v2 context and current guided prompt contract.

Both frontier arms receive the same source packet and no target obligation data:

- Claude Fable 5, adaptive thinking, `xhigh` effort;
- GPT-5.6 Sol, `xhigh` reasoning.

There are four calls per arm, no retries and no answer-to-answer dialogue. All
eight outputs are checkpointed before the frozen 13-relation oracle is loaded.
This is a ceiling diagnostic, not a production model bake-off.

## Gate

An arm may proceed only to a separately preregistered fresh-cohort routing test
when it covers at least 11/13 source-attested relations, produces no invalid
fragment citation, completes every call and has no token-limit stop. Direct
production, fact credit and target-specific prompt tuning remain forbidden.

If neither arm passes, model substitution is closed and the next architecture
must preserve source text while restructuring evidence. It may not tune another
prompt or selector on these four questions.
