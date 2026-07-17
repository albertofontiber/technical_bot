# S197 — versioned Fable 5 executor and byte-bound frontier duo

## Decision and objective

Recover the Fable 5 review path that was exercised successfully from Codex on
2026-07-12/13 but remained untracked in another workspace. The objective is a
reproducible high-risk review contract: GPT-5.6 Sol xhigh remains the principal
reviewer and a separate `claude-fable-5` execution reviews the same frozen seed
bytes without seeing Sol's output. This change has zero fact delta and does not
authorize the S197 paid cohort.

The implementation is `scripts/adversarial_review_fable.py`. It calls Anthropic
directly with `max_retries=0`, the exact provider model ID
`claude-fable-5`, the canonical versioned briefing and read-only repo tools. It
does not depend on an ignored `.claude/` agent file, a Claude host session or a
standalone `fable` executable.

## Pairing and independence contract

Before any Sol call, `scripts/adversarial_review.py` now hashes the ordered,
repo-relative input paths and their exact bytes, the canonical briefing and the
complete tool-visible repository view into `adversarial_duo_subject_v1`. That
view is restricted to Git-tracked plus unignored untracked files and excludes
`.env*` paths, internal directories, the tally and prior reviewer outputs. This
is a path policy, not a general secret scanner: a credential committed under an
unrecognized filename would remain visible and is a repository-governance
failure outside this runner's claim. The completed Sol tally row stores the aggregate view hash/count and starts as
`pending_fable`. Both runners seed every explicit file in full; neither can
claim byte parity over a truncated exposure. Each process reads the complete
view twice and fails if bytes, visibility, HEAD or manifest drift; after equality,
the frozen in-memory view is the sole source. Subject hashing, strict UTF-8 seed decoding, automatic
change manifest and every `read_file`/`grep_repo`/`list_dir` result derive only
from that snapshot, never from a later worktree read. A Git-visible symbolic
link is rejected rather than followed, so the view cannot import bytes from
outside the repository root.

Paired/fallback Fable requires an explicit `--sol-ts`; the Fable-only tier uses
`--standalone`. On success it persists the raw response,
usage, tool trace and output SHA-256, then atomically replaces exactly one tally
line only if all of these remain true:

- the target is a completed, exact `gpt-5.6-sol`/`xhigh` principal run;
- its Fable state is still pending;
- the ordered file inventory and every physical input SHA-256 equal Fable's;
- briefing, HEAD-derived change manifest and complete tool-visible repo-view hashes still match;
- both reviews used the same tools mode;
- the Fable provider model equals the frozen `claude-fable-5` pin.

The resulting state is `complete_pending_adjudication`; Rule C still requires
claim verification before `complete`. A missing credential, provider route or
failed call appends a timestamped attempt with cost/tool/provider evidence when
available, returns nonzero and leaves the Sol entry retryable and pending. It is
not converted into the ambiguous `omitted_unavailable` state.

The attachment boundary independently validates the exact Fable model pin,
contract flag, completion state, provider IDs/models/stop sequence and both
physical output hashes before it can change the duo state. It reconstructs the
final provider text, aggregate usage and tool calls from the raw trace and requires
exact receipt equality. It also revalidates Sol's raw/normalized physical artifacts,
model, effort, IDs, statuses and final text before closing the pair.
It does not trust a caller-constructed dictionary merely because it originated
in the same module.

For MEDIUM decisions outside a pain zone, `--standalone` persists an explicit
`fable_standalone` row without claiming Sol ran. A paired `--sol-ts` may also
complete the documented Fable+human fallback when its byte-bound Sol row is
`sol_omitted`; that result remains explicitly Sol-omitted and cannot be called a
complete frontier duo.

Both runners receive a canonical instruction not to consult prior reviewer
output, and both tool sandboxes deny the tally, `evals/adversarial_reviews/` and
named Sol/GPT/Fable review artifacts. Fable also receives a model-specific
independence reminder. Thus both models share frozen seed bytes and repository
authorities without one review anchoring the other.

## Budgets, failure semantics and limitations

The Fable loop defaults to 12 read-only tool calls, 300,000 cumulative tokens,
80,000 tokens of final headroom and 16,000 maximum output tokens per request.
Every request receives a conservative UTF-8-byte input bound before it is sent;
reported provider usage, including cache-create/cache-read tokens, is checked cumulatively. Each response must report the
exact requested provider model and a stop reason consistent with its content
(`tool_use` or final `end_turn`); truncation fails closed and cannot close the
duo. The receipt byte-binds the full serialized provider response trace, IDs,
reported models and stop reasons separately from the normalized review text.
Sol symmetrically persists its normalized review and serialized Responses API
trace with physical hashes, IDs, reported models and statuses in the tally. A
provider response that fails closed still leaves its raw trace linked from the
failed Sol row; no normalized review is fabricated.

The tally replacement preserves every non-target physical line and uses a
same-directory temporary file plus `os.replace`. Execution is deliberately
serialized by the operator: concurrent Sol append and Fable attachment are not
a distributed transaction. The explicit timestamp, pending-state and byte
identity checks prevent mis-pairing, but this local review tool does not claim a
multi-process locking service.

Exact provider model availability is an external dependency. Deprecation or a
renamed model must produce a declared failed attempt and an explicit protocol
decision; an unapproved substitute cannot satisfy the Fable side.

## Alternatives rejected

- Reuse Claude's native `.claude/agents` runtime: not reproducible from a clean
  Codex worktree and was the source of the current integration loss.
- Copy a Fable answer manually into the log: loses exact input binding, cost,
  tool trace and raw-output identity.
- Treat Sol alone or another economical model as Fable: violates the explicit
  two-frontier-reviewer decision.
- Bundle Sol output as Fable context: cheaper convergence but destroys the
  independent lens the second review is intended to provide.

## Deterministic verification and closeout

Tests cover the exact model pin, Anthropic tool schemas, symmetric independence
deny-list, absence of `.claude` dependency, conservative token preflight,
provider attestation, tool-loop trace, truncation failure, full repo-view and
ordered subject hashing, failed-attempt audit, exact atomic pairing,
subject-drift rejection, symlink rejection, a real temporary-Git integration
case and CLI pairing requirements. Sol completed the final review. Two exact-model
Fable attempts reached the provider and used the frozen repo tools, but returned an
empty final text block and were rejected/audited. DEC-106 records the explicit choice
not to add a third convergence attempt or block this preparation merge; the result is
not mislabeled as a completed duo.

Railway is a demo and is not part of this decision, PR gate or merge gate.
