# S157 post-answer source-preserving omission correction

## Hypothesis

The remaining synthesis failures are broad questions whose decisive facts are
distributed across several already-served fragments. Pre-answer selectors and
model-written claim maps under-selected or altered source text. S157 instead
looks for omissions only after the normal bot has drafted its answer.

## Architecture

1. A source-first cohort contains twelve unseen manuals, twelve manufacturers
   and three nearby chunks per manual. It excludes the target documents and all
   earlier S135/S146/S147 challenge documents.
2. Haiku authors one natural multi-fragment field question per packet, with two
   to four exact answer points spanning at least two fragments. Authoring occurs
   only after this implementation and gate are frozen.
3. The current production generator (Claude Sonnet 4.6, current fidelity/guided
   prompt) writes the baseline draft.
4. Each fragment is independently unitized into immutable contiguous spans or
   exact table-header/row composites. Haiku sees the question, draft and units
   from one fragment, and selects only IDs containing a material fact omitted
   from the draft. It cannot write claims, quotes or source identities.
5. If at least one unit is selected, the same production generator receives the
   draft, the full original context and the selected original units, then writes
   one complete revision. There is no iterative loop.

The design is a bounded corrective-RAG pattern. It is product-agnostic, keeps
all evidence source-reconstructible, uses a cheap executor for exhaustive local
comparison, and reserves the production-grade model for answer writing.

## Gates and credit

The locally authored answer-point proxy must improve by at least three points,
raise complete-question rate by at least 15 percentage points, regress at most
one question, keep every fragment citation valid and remain under budget. A pass
only permits one blinded Sol/Fable semantic comparison of baseline versus
candidate. It does not expose the four frozen targets, change production or move
facts to OK.

Failures close this architecture without prompt retries or cohort-specific
tuning. A semantic pass would then permit a separately frozen four-target probe,
followed by the protected full regression before any production decision.
