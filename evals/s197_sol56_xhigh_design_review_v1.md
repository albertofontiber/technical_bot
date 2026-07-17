# S197 — Sol 5.6 xhigh findings and agent evidence packet

## Rule-C status

`USER_AUTHORIZED_AGENT_VERIFIED`. The technical dispositions below were checked against
code/tests; Alberto repeatedly instructed “OK, corrígelos” and then “continúa”. That
authorizes the corrections and integration, while the paid cohort remains a separate
post-merge action. Earlier `omitted_unavailable` wording is superseded: it described a
missing versioned executor in that worktree, not global Fable availability.

## Initial review receipt

Receipt `2026-07-17T16:12:25`: `gpt-5.6-sol`,
`reasoning_effort=xhigh`, principal contract satisfied, 30 read-only tool calls and
186,252 total tokens. The original row recorded Fable as `omitted_unavailable` because
the worktree lacked the untracked direct executor used previously from Codex. The
executor is now versioned; no substitute review is represented as Fable.

## Rule-C adjudication

1. **“Entirely fresh” over-claimed — confirmed medium.** Structural disjointness did
   not measure semantic near-duplicates or OEM relabels against prior packets. The
   source receipt and design now say those two overlaps are `NOT_MEASURED`; “fresh” is
   defined narrowly as ID, filename, manufacturer/product-pair and protected-target
   exact-hash disjointness.
2. **Target-equivalence recomputation over-claimed — confirmed medium.** The offline
   runner verified consistency of duplicated receipt fields but did not independently
   query target rows. The design now says exactly that. The builder links the target
   receipt to the stable source fingerprint, while the runner checks that linkage and
   internal row/hash consistency; no second source-of-truth claim remains.
3. **Spanish/naturality gate missing — confirmed medium.** Presence and length did not
   prove the author obeyed the Spanish field-technician contract. Luna's strict output
   now separately adjudicates Spanish language and naturalness for every eligible
   question, and both are mandatory cohort gates.
4. **Validation scope over-claimed — confirmed medium.** Luna sees every unit in the
   selected excerpt, not the full document or corpus. The artifact is renamed from a
   gold cohort to a Luna-screened diagnostic cohort; result and design call the gate
   `CROSS_PROVIDER_EXCERPT_INTERNAL` and explicitly mark document-wide completeness,
   multi-document/OEM and country-profile conflicts `NOT_MEASURED`.
5. **Count-stable read was not a snapshot — confirmed medium.** S197 now requires two
   complete ordered GET-only scans with identical row counts and full-row fingerprints.
   It calls this a double-scan stability receipt, not a transactional snapshot. Equal
   cardinality with content drift is tested to fail closed.
6. **Source contract under-tested — confirmed medium.** In addition to the operational
   fake-client test, a synthetic 14-item packet now exercises the real source contract.
   Negative tests rehash manipulated packets and prove rejection of prior overlap,
   scan-fingerprint drift, broken target linkage, excerpt drift and evidence-manifest
   drift.

Initial tally: 6 findings, 6 confirmed, 0 false positives, maximum severity medium.
All fixes precede source freeze, preregistration and paid execution. A fresh Sol
follow-up is required before S197 freezes the real packet.

## Follow-up review receipt and adjudication

Receipt `2026-07-17T16:21:44`: `gpt-5.6-sol`,
`reasoning_effort=xhigh`, principal contract satisfied and 30 read-only tool calls.
The historical Fable omission has the corrected interpretation above.

1. **Paraphrastic points could inflate the cohort — confirmed medium.** Exact
   `casefold` uniqueness was insufficient. Luna now emits a strict
   `answer_points_semantically_distinct` judgement for every eligible item; any
   paraphrase/redundancy fails the cohort gate and is given known-failure precedence.
2. **Post-author budget failure was unsealed — confirmed medium.** Both author and Luna
   budget failures after the workspace lock now finalize through `seal_failure`. The
   Luna path records `NO_GO_SEMANTIC_BUDGET_AFTER_AUTHOR_EXECUTION` plus completed
   checkpoint hashes, and a test verifies atomic result creation after author receipts.
3. **Protected target UUID resolution was incomplete — confirmed medium.** The source
   builder now records a per-UUID chunk/document resolution receipt and fails closed on
   any unresolved target. The offline contract requires the exact target-ID inventory,
   valid nonzero resolution counts and an empty unresolved set; tests cover success and
   failure.
4. **S198 hand-off omitted inherited gates — confirmed minor.** The result now carries
   the complete downstream contract: 90/80/75, exactness, deterministic contracts, zero
   covered-obligation regressions and zero new versioned-contract conflicts.

Follow-up tally: 4 findings, 4 confirmed, 0 false positives, maximum severity medium.
All fixes precede source freeze and paid execution. A narrow final Sol closeout is
required before preregistration.

## Narrow closeout receipt and adjudication

Receipt `2026-07-17T16:30:35`: `gpt-5.6-sol`,
`reasoning_effort=xhigh`, principal contract satisfied, bounded `--no-tools` review of
the full revised artifact set. The historical Fable omission has the corrected
interpretation above.

1. **Facet correctness was unmeasured — confirmed critical.** Each Luna point review
   now has mandatory `facet_correct/facet_issue`; every active point must use the
   best-fit generic facet for GO.
2. **Answer-point completeness was implicit — confirmed critical.** Luna now separately
   judges whether the full point set covers every material exception, warning, bound,
   prerequisite and qualifier needed for the question within the excerpt. This is a
   mandatory gate distinct from support and answerability.
3. **Cohort seal did not bind Luna judgements — confirmed medium.** The cohort now embeds
   all normalized reviews and hashes the complete semantic receipt artifact. Every
   receipt binds authored-item, exact-input and output-schema hashes plus raw output and
   normalized review; the gate verifies the bijection.
4. **Authorization freeze omitted live authorities — confirmed medium.** The inventory
   now includes all prior packets and target files plus S114, S146/S165/S167 helpers,
   S194/S195/S196 authorities, unitizer, canonical decisions and requirements.
5. **Unhandled post-lock exceptions could strand execution — confirmed medium.** The
   public executor now wraps the one-shot implementation and atomically seals any
   unexpected post-lock exception, preserving known-failure precedence. A constructor-
   failure test proves the HOLD result is written.
6. **S198 “complete contract” was an over-claim — confirmed medium.** It is renamed a set
   of inherited headline constraints, pins the canonical decision hash and requires
   S198 to preregister all executable definitions and denominators separately.
7. **Boolean/issue contradictions were accepted — confirmed minor.** The validator now
   requires empty issues for true/null judgements and non-empty reasons for false ones,
   including claim support and facet correctness; contradictions fail closed.

Closeout tally: 7 findings, 7 confirmed, 0 false positives, maximum severity critical.
All fixes precede source freeze and paid execution. One final regression-focused Sol
review is required because the closeout found critical omissions.

## Regression review receipt and adjudication

Receipt `2026-07-17T16:39:29`: `gpt-5.6-sol`,
`reasoning_effort=xhigh`, principal contract satisfied, bounded `--no-tools` review.
The historical Fable omission has the corrected interpretation above.

1. **Target-resolution receipts were not reconciled to rows — confirmed critical.** The
   runner now recomputes every per-UUID chunk/document count and status from
   `resolved_rows` and requires exact ordered equality with the receipt. A coordinated
   mutation that removes resolved rows and rehashes every aggregate is tested to fail.
2. **Known author NO-GO ignored mathematical impossibility — confirmed medium.** Before
   each call, S197 now computes the best possible remaining eligible/manufacturer,
   table/prose and point counts. Provider interruption receives NO-GO precedence once
   any frozen population threshold is unreachable, even with structurally valid prior
   ineligible outputs.
3. **Semantic receipt binding was under-verified — confirmed medium.** The bijection now
   recomputes exact semantic input and schema hashes, raw-output hash, reparses and
   normalizes raw JSON, and requires equality with receipt and cohort review. A tampered
   input hash is tested to fail.
4. **A single uncalibrated Luna cannot create gold — confirmed medium.** The artifact and
   status are renamed `Luna-screened`; result fields mark judge calibration and human
   agreement `NOT_MEASURED` and state `SCREEN_ONLY_NOT_GOLD_AUTHORITY`.
5. **Author-selected questions can bias difficulty/opportunity coverage — confirmed
   medium.** Excerpt-opportunity coverage, difficulty representativeness and
   generalization beyond the screened cohort are explicit `NOT_MEASURED` limits. S198
   may only make a cohort-bounded diagnostic claim and still moves zero facts.
6. **Raw manufacturer strings inflated diversity — confirmed minor.** Source and
   population gates now use NFKC + trim + casefold identity normalization. OEM aliases
   remain separately `NOT_MEASURED`; tests collapse case, whitespace and full-width
   variants before applying the 12/14 manufacturer gates.

Regression tally: 6 findings, 6 confirmed, 0 false positives, maximum severity critical.
All fixes precede source freeze and paid execution. A final focused Sol audit must find
no blocking regression before preregistration.

## Final focused audit receipt and agent disposition

Receipt `2026-07-17T16:49:39`: `gpt-5.6-sol`,
`reasoning_effort=xhigh`, principal contract satisfied, bounded `--no-tools` review.
The historical Fable omission has the corrected interpretation above.

1. **Human Rule-C identity absent — substantiated and process-blocking.** This document
   now marks every technical disposition as agent evidence pending Alberto. No source
   freeze or paid execution is authorized by the agent tally alone.
2. **Lock ownership race — agent-substantiated critical.** Execution now creates a
   random owner token, writes it in the exclusive lock and permits the outer finalizer
   to seal only on exact token match. A simulated losing process cannot create a result.
3. **Author-schema prohibition contradicted semantic `const` — agent-substantiated
   critical.** The forbidden rule is narrowed to dynamic *author* source-ID
   enums/consts. The design explicitly permits the separate OpenAI review schema to bind
   its response identity; S196's Anthropic grammar remains static.
4. **Decision objective and primary metric absent — agent-substantiated medium.** The
   design now states the causal transport hypothesis and one binary primary endpoint:
   every population, screening and receipt-binding check true in the single run. A GO
   authorizes only S198 preregistration and has zero fact delta.
5. **Author prompt prohibited necessary paraphrase — agent-substantiated medium.** It now
   requires accurate Spanish paraphrase while forbidding long quotation, outside
   knowledge, product mixing and invented IDs.
6. **Known corpus-language gaps omitted — agent-substantiated medium.** OCR, scan/
   diagram-only evidence, seven-segment displays and ES↔EN vocabulary/translation are
   explicit `NOT_MEASURED` modes.
7. **Snapshot naming contradicted double-scan framing — agent-substantiated minor.** S197
   receipts now use `full_scan_sha256` and `stable_full_scan_sha256`; imported legacy
   `snapshot_sha256` names are stripped before the packet is written.

Final audit tally: 7 findings, 6 technical dispositions agent-substantiated, 1 human
process gate pending, 0 adjudicated false positives. Maximum severity critical. The
Alberto subsequently authorized the fixes and continuation. The versioned direct
Fable runner reached `claude-fable-5` twice on the final byte-bound subject, but both
responses ended with an empty text block; both failed attempts and provider traces are
audited. Per DEC-106 there is no third convergence attempt and this external failure
does not block the preparation PR; it is not represented as a completed duo.
