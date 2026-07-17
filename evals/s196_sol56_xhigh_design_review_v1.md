# S196 — Sol 5.6 xhigh design review and adjudication

## Initial review receipt

Receipt `2026-07-17T15:26:44`: `gpt-5.6-sol`, `reasoning_effort=xhigh`,
primary contract satisfied, 30 read-only tool calls. Fable 5 is
`omitted_unavailable`: neither a `fable` nor a compatible pinned executor exists in this
environment, and no substitute receipt is claimed.

## Rule-C adjudication

1. **Executable dependencies outside the freeze — confirmed medium.** The first runner
   imported schema formatting, cost, facets, stable hashing, error sanitization and the
   chunks_v3 receipt from S165/S167/S194/S195 while the planned freeze covered only the
   S196 files. These helpers now live in the frozen S196 runner; `requirements.txt` is an
   additional frozen input. The default env path remains a path only, not executable
   experiment logic.
2. **Over-broad 400 attribution — confirmed medium.** A token-count or unrelated
   inference 400 could have been called a schema-compiler rejection. The runner now
   records the request stage. Preflight 400 is
   `NO_GO_PREFLIGHT_REQUEST_REJECTED`; inference 400 is attributed to compilation only
   when the sanitized message explicitly mentions schema plus compilation/complexity;
   otherwise it is `NO_GO_INFERENCE_REQUEST_REJECTED_UNATTRIBUTED`.
3. **Operational path under-tested — confirmed medium.** Tests now inject a deterministic
   fake client and assert `max_retries=0`, preflight→exclusive checkpoint→inference order,
   accepted-schema receipt, budget stop before checkpoint, exclusive lock behavior and
   stage/message-specific 400 classification.

Tally: 3 findings, 3 confirmed, 0 false positives, maximum severity medium. All fixes
precede preregistration and paid execution. A follow-up Sol review is required before
freeze.

## Follow-up review

Receipt `2026-07-17T15:32:08`: `gpt-5.6-sol`, `reasoning_effort=xhigh`, primary
contract satisfied, 30 read-only tool calls. Three further findings were readable:

1. **Lock after preflight — confirmed medium.** Two concurrent processes could each send
   token-count requests before one acquired the checkpoint. S196 now acquires a dedicated
   immutable execution lock before constructing/sending through the client. A second
   execution is tested to fail before client construction or any provider request.
2. **Unpinned resolved SDK — confirmed medium.** `anthropic>=0.40.0` does not identify the
   serializer actually used. The prereg now pins `0.97.0`; the runner verifies the
   installed distribution version before the lock and records it in lock, checkpoint,
   final receipts and result authority.
3. **Non-atomic checkpoint overwrite — confirmed medium.** The first version overwrote its
   own lock/receipt after inference. S196 now separates immutable lock and pre-paid
   checkpoint from the final receipts. Receipts and result are created with a flushed
   same-directory temp file and `os.replace`, never by truncating an authority file.

Follow-up tally: 3 findings, 3 confirmed, 0 false positives, maximum severity medium.
All fixes precede preregistration and paid execution. A final narrow closeout review is
required before freeze.

## Narrow closeout review

Receipt `2026-07-17T15:38:22`: `gpt-5.6-sol`, `reasoning_effort=xhigh`, primary
contract satisfied, bounded `--no-tools` review over the full revised artifacts. Six
findings were readable:

1. **“Globally” over-claim — confirmed medium as framing.** The lock is filesystem-local.
   The design and exact execution contract now say `current_workspace`; no shared
   cross-host idempotency service is claimed.
2. **Invalid raw output not auditable — confirmed medium.** The fixture is synthetic, so
   final receipts now persist `raw_synthetic_output` plus its hash for valid or invalid
   structured responses.
3. **400 attribution still too lexical — confirmed medium.** Attribution now requires an
   anchored positive provider message beginning `Schema is too complex for compilation`.
   Negated/succeeded/co-occurrence messages remain un-attributed; tests cover them.
4. **Lock-order test did not observe the lock — confirmed minor.** Factory and token-count
   fake both assert the lock already exists. A separate isolated-lock test proves client
   construction is blocked with no other artifact present.
5. **Full-environment freeze over-claim — confirmed minor.** The design now limits the
   exact resolved-version guarantee to the Anthropic serializer boundary. Requirements
   remain context; no hermetic Python claim is made.
6. **Duplicated chunks_v3 baseline — confirmed minor.** S196 keeps the lane explicit but
   records only status, non-change flags and canonical roadmap reference; historical
   metrics are not copied.

Closeout tally: 6 findings, 6 confirmed, 0 false positives, maximum severity medium.
All fixes precede preregistration and paid execution.
