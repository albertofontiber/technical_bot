# S277 C1 P1 implementation review brief

Date: 2026-07-20
Impact: HIGH — prerelease quality gate, budget/WAL protocol, configuration identity,
corpus fencing, and deterministic fact scoring.
Scope: offline tooling only. No P1 model calls, deployment, Railway mutation, or
Supabase write has been authorized or performed by this change.

## Decision under review

Review the implemented P1 package as a fail-closed release gate for the candidate C1
coverage profile. P1 does **not** establish the global 98% KPI and it has not been run.
The intended paid cohort is 13 frozen QIDs and 27 independent end-to-end replicas
(27 generations; normally about 81 paid model calls including query embedding and
reranking), with a conservative preregistered cost bound below USD 10.

The implementation must refuse paid execution until an explicit product adapter and
all external identities/receipts/locks/permits are supplied. The in-repository test
adapter produces synthetic, self-consistent receipts: those tests exercise the
orchestrator but do not prove the bytes sent by the product SDK, the physical
derivation of pool/prefix/context, a visual GET, or Telegram delivery. Those are
acceptance criteria for the separately reviewed product adapter, and its absence is a
current stop-line. A stored free control for the known PEARL 7-vs-8 conflict is
expected to produce HOLD, never a candidate PASS.

There is a second, separately named stop-line: the current RPC/REST/relation hashes
are only declared surface identities, not observations of live RPC definitions,
ACLs, overloads, indexes or operational configuration. The product-facing
`fence-open-verify`, `fence-close-verify`, `run` and `finalize` handlers therefore stop first at
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`. A future change must materialize and
review the exact live manifest contract before any of those handlers may proceed.

## Primary files

- `scripts/s277_build_c1_p1_contract.py`
- `scripts/s277_c1_p1.py`
- `scripts/s277_c1_p1_scorer.py`
- `evals/s277_c1_p1_fact_contract_v1.json`
- `evals/s277_c1_p1_prereg_v1.yaml`
- `evals/s277_c1_p1_release_config_schema_v1.json`
- `tests/test_s277_c1_p1_contract.py`
- `tests/test_s277_c1_p1_runner.py`
- `tests/test_s277_c1_p1_scorer.py`
- `evals/s277_c1_p1_design_v1.md`
- `docs/C1_RELEASE_RUNBOOK.md`

Related C1 release identity changes:

- `scripts/s277_c1_release_gate.py`
- `scripts/s277_c1_live_reachability_probe.py`
- `tests/test_c1_release_gate.py`
- `evals/s277_c1_live_reachability_receipt_v1.json`

## Invariants to attack

1. **Exact cohort and input.** Exactly the preregistered 27 ordered replicas must be
   scored. Each replica binds the exact QID, question/query, expected target-model list
   and `available_models=None`; it does not merely accept non-empty substitute inputs.
   Manufacturer/language are not fields in this preregistered input contract and must
   be proven separately by the future product adapter/routing receipt.
2. **Physical generation chain.** The offline core must bind each canonical
   provider-intent payload and observed response through the declared post-processing
   stages, final answer, renderer output, and receipt. It must remain impossible to
   score one stored response while referencing a different sealed response. Product
   execution has a stronger, still-unimplemented requirement: the adapter must prove
   that the actual SDK/network request used the exact query for embedding, query +
   real pool and product prompt for rerank, and system/user prompts + physically
   derived served context for synthesis. The intended lineage is `embedding response
   → retrieval pool → rerank request/response → prefix → structural fetch/coverage →
   served context → synthesis request/response`; coherent hashes from the synthetic
   adapter are not proof that those product transformations occurred.
3. **Authoritative finalization.** Caller-supplied score JSON or a weakened/replaced
   fact contract must not mint PASS. Finalize must re-score the exact preregistration,
   contract, manifest, and 27 receipt hashes and compare canonical results. Every
   reopen used by resume, score or finalize must also re-run the complete semantic
   replica validator over all 27 receipts, verify the active implementation against
   the genesis snapshot, and re-open all 81 provider responses and fence watches.
   The injected per-replica callback is only a bounded early-abort hint; its rows are
   persisted under `non_authoritative_early_abort_checks` with explicit authority and
   cannot mint PASS. Only the canonical offline `score_run` used again by `finalize`
   is authoritative.
4. **Configuration identity.** Live snapshot freshness and exact production semantic
   values must be enforced, including retrieval/rerank widths, generation token cap,
   backend/model/prompt identities, identity policy, HYDE and other semantic flags.
   `VISUAL_ASSETS_REGISTRY` is orthogonal: preserve its exact live state (`on` in the
   documented production snapshot); drift/absence is HOLD, not a silent off/on cycle.
   Only the preregistered C1 profile projection may differ between bootstrap and target.
   Every replica must prove the effective target profile, commit/tree and semantic hash;
   `coverage={status: ok}` is not sufficient evidence.
5. **Budget and network boundary.** Envelope/token maxima and conservative call cost
   must be checked before every possible provider send; observed usage/cost must be
   checked afterward. WAL is fsync-before-send, has no automatic retry for uncertain
   post-send state, and resume must bind the current request hash. Static and observed
   totals must remain under the hard USD 10 cap.
   A paid authorization must have a unique run/authorization ID, be atomically claimed
   in a durable ledger outside the artifact directory, bind that directory, and be
   impossible to reuse to obtain a second USD 10 budget. Journal, sidecars and ledger
   paths must be canonical and sealed in genesis; an existing claim with deleted or
   reinitialized run state must HOLD, while a complete canonical resume must not send
   again. An exclusive canonical lease must prevent a second active runner from
   touching WAL/result, and its ownership must still be exact before every send.
   A completed run must reopen as exactly 162 alternating WAL events in the
   preregistered order. Reserve max-cost and accumulated-prior values, response
   model/usage, terminal actual cost and the result budget summary must all be
   recomputed from the genesis-bound 81-call budget; self-consistent but underreported
   cost artefacts must fail.
6. **Corpus fence.** Opening/closing receipts, external locks, heartbeat, deadline,
   fingerprints, and final-under-lock checks must fail closed. Close time must fall
   inside the protected window. The exact canonical relation/RPC/index/config surface
   (including `chunks_v2`) must be derived and bound; watcher evidence is revalidated
   immediately before every provider send, not just once per replica. The implemented
   helpers validate only the declared surface/lock contract used by synthetic tests.
   They must not be credited as live RPC/index/config attestation: the product CLIs
   remain machine-blocked until observed manifest bodies and their expected contract
   are materialized. PostgREST identity is read-only; local hashes do not pretend to
   be third-party attestation.
7. **Fact/citation semantics.** Protect the exact transformed 43-row base packet
   without double-counting guard-only rows. This is not literally every historical
   S113 OK row: `hp017#1:instruccion de entrada` is explicitly removed because its
   contemporary components remain S274 residuals, while hp017#2 and the banked hp002
   conversion are explicit versioned substitutions. hp017 additionally requires its
   compound target plus both F12 warning clauses with correct source/range attribution.
   Known 7-vs-8 conflict must HOLD. Citation syntax or file/page identity alone must
   not prove support. Generic automatic PASS requires the whole cited local claim to
   equal the canonical affirmative statement and the served fragment to contain its
   preregistered fact-specific quote (or match an exact content/span hash). Negations,
   relation changes and paraphrases are REVIEW. hp013 has no automatic PASS path: a
   machine-safe precheck still requires blind human semantic adjudication.
8. **Release expiry/lineage.** Tested tree/commit, manifest, config projections,
   corpus/provider/runtime identities, receipt set and TTL must be bound. A squash,
   rebase, tree/config/corpus drift, expired receipt, or missing external role/permit
   must invalidate reuse.
   WAL and artifact store must start with an immutable run genesis and every request,
   call, replica and resume must carry it; a crash may not let candidate B reuse A.
   Config/prereg/fingerprint/fence/runtime/budget/input snapshots must be rebuilt at
   execution start; runtime identity, lease ownership and the reserved request hash
   must be rechecked at the final pre-send boundary for every provider call.
9. **No accidental execution surface.** The repository must not contain a working
   paid/product adapter disguised as a test helper. The CLI should plan and score
   stored controls safely, while real `run --execute` remains fail-closed until the
   separately reviewed adapter and external prerequisites exist.
10. **Renderer authority.** Telegram parts must equal a fresh call to the versioned
    `format_telegram_messages(answer)` implementation; a declared completeness boolean
    and coherent hash over different text must fail.

## Known boundaries (do not misclassify as implemented guarantees)

- Authorized workspace/operator is a declared trust boundary; file hashes are
  integrity bindings, not protection from a malicious authorized local writer.
- Synthetic adapter receipts prove fail-closed orchestration and mutation rejection,
  not real retrieval derivation, product SDK request-byte parity, visual delivery, or
  network-side attestation.
- No independent global factual-validity judge is added here. The deterministic
  scorer applies the frozen source contract and registered conflicts.
- The injected per-replica callback can only stop spend early. It is not an
  authoritative scorer and may not be cited as PASS evidence; the USD 10 cap remains
  the bound if it fails to abort. Canonical scoring happens offline after all receipts.
- The production adapter, Railway snapshot/patch receipt, PostgREST runner role,
  corpus-fence service/locks, provider/runtime receipt and spend permit are absent.
- The current adapter protocol cannot prove that `prepare()` is side-effect-free and
  the semantic projection does not yet include every release-gate-only switch
  (`ANSWER_OBLIGATION_PLANNER`, `GENERATOR_INCLUDE_CONTEXT`, `IDENTITY_FETCH`). Both
  are mandatory design items for the separately reviewed product adapter/config
  package, not guarantees of this offline core.
- The implementation hash manifest is not yet transitively complete: at minimum the
  conflict scorer executes `src/rag/answer_planner.py`, which is not currently sealed.
  The final duo therefore blocks removal of the product stop-line until the product
  adapter package closes and mutation-tests the complete executed dependency graph.
- The product adapter must reject non-terminal rerank responses and provide an
  independently bound provider-usage/cost receipt. The offline core can validate
  internal consistency, but cannot authenticate self-reported token usage by itself.
- The live fence manifest contract is absent. Required future bodies include exact RPC
  identity/signature/result/definition/volatility/security/owner/ACL/overload evidence
  and exact index validity/readiness/definition plus PostgREST/ACL/config snapshots at
  open/watch/close. Declared surface hashes are not substitutes.
- The filesystem execution lease is single-host. It is never auto-reclaimed; stale
  recovery and any multi-host/distributed lock are separately reviewed future work.
- `score-stored-controls --contract` may be used diagnostically with a custom contract;
  only its canonical default is evidence for the recorded 3/3 conflict, and it can
  never score or mint candidate PASS.
- Therefore the only safe current outcome is a fail-closed offline HOLD. P1 execution
  and any release GO remain blocked.

## Frozen local verification and final-duo outcome

- P1 contract/runner/scorer suite: `181 passed`.
- Full local suite: `2461 passed, 6 skipped, 4 failed`; the four failures are the
  pre-existing Windows raw-byte/CRLF receipt cases (`s117`, `s131`, two `s133`),
  while the LF-normalized P1 suite is green. Linux CI remains the merge authority.
- `py_compile`: PASS.
- Deterministic artefact generation: byte-identical across two consecutive builds.
- `plan`: 27 replicas / 81 planned calls / 0 paid calls.
- stored control: `HOLD_PREPAID_KNOWN_CONFLICT_RISK`, PEARL conflict 3/3.
- No P1 model call, Railway mutation or Supabase write was made.
- Final Sol/Fable duo completed at `2026-07-21T00:06:50` / `00:08:56`.
  The two semantic false-PASS paths stayed closed, but Sol confirmed the transitive
  implementation-manifest gap above. Per the bounded stopping rule, no further
  offline patch/review loop was opened; the artifact closes as HOLD, not PASS.

## Review request

Inspect the implementation and mutation tests, not only this brief. Try to construct
forgeries, partial/resumed runs, stale snapshots, semantic config drift, response/stop
reason mismatches, reordered/missing/extra replicas, fake citations, expired fences,
and budget races that could yield PASS or a provider send. Anchor every strong finding
to a file and line. Separate confirmed defects from declared external prerequisites or
deliberately trusted boundaries.
