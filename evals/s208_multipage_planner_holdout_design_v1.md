# S208 — clean multi-page support contract and fresh-predicate planner holdout

## Decision scope

S207 stopped before planner execution because two valid atomic facts required a
model-scope sentence on page 15 and their numeric value on page 16, while the
frozen support validator only accepted units from one singular cited page. S208
repairs that general contract and runs one fresh holdout. It does not reinterpret,
retry, repair, rescore or reuse the S207 cohort.

The canonical denominator remains 157 facts: 143 OK, 12 synthesis misses and 2
retrieval misses. Reaching 98% requires 154 OK, hence 11 additional facts. S208
is an upstream falsification test and grants no official fact credit.

## Clean contract, not a hybrid bridge

Historical v2 artifacts keep their singular `citation` field unchanged. New v3
facts use only an explicit `citations` list and one page-bound visual-evidence
receipt per citation. The singular form is rejected. A mapped support set is
valid only when its page set equals the declared citation-page set exactly:
every necessary page is present and no undeclared or decorative page is added.

This is the general form needed for specifications, footnotes, model scope,
table continuations and procedures that cross pages. It removes the S207
one-page assumption without special-casing any model, value, language, page or
target fact. Unit IDs remain immutable and page-bound; the compiler remains
deterministic.

## Honest corpus constraint

The audited Kidde candidates did not yield a suitable unused source identity for
the required multi-page predicate after exclusions. This is recorded as a
bounded selection result, not an exhaustive proof about every possible Kidde
question. S208 therefore freezes three candidate-new predicates from three PDFs
already represented in official gold, while excluding every prior S203–S207
visual cohort. A versioned selection receipt records selected and rejected
examples. The packet discloses all official facts and all same-source S99
questions to both frontier models; only their later PASS can validate semantic
novelty.

This is a fresh-predicate holdout, not source-independent or external
validation. Exact-page S99 presence is disclosed but is not treated as a
semantic-duplication oracle: unrelated questions on a page do not contaminate a
new predicate. Any semantic overlap, including multilingual or cross-page
paraphrases, is still a blocking veto in frontier authorship and review.

## Frozen Kidde predicates

1. KE-DP3120W isolation geometry across pages 2–3: the two 13 Ω maximum
   impedance positions, the footnote equivalence to 500 m of 1.5 mm² (16 AWG)
   cable, 128 isolators per loop and 32 devices between isolators. At least one
   atomic fact must genuinely require both pages.
2. 2X-A Self-test on page 91: default-off state, menu route, enable control,
   TestH and ReportH ranges, and save/apply sequence.
3. NC internal-fault startup on page 89: fast/slow LED pattern, operator
   credential, Reset action and persistent-fault outcome.
All four full pages were rendered at 200 dpi and inspected pixel by pixel before
freeze. The manual inspection is versioned separately and bound to every render
by SHA-256; the builder verifies it rather than manufacturing PASS receipts.
Evidence units form one gap-free, non-overlapping source partition with a
450-character target, no unit over 600 characters and no alternative duplicate
ID path.

## Frontier and economic roles

- Principal author/reviewer: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent author/reviewer: `claude-fable-5`.
- Sol and Fable independently author all three questions from pixels. Fable must
  pass every Sol publication candidate; Sol reviews the Fable set as a material
  disagreement probe. No repair, merge, retry or post-selection is allowed.
- After pixel gold freezes, Sol maps each fact to the smallest complete unit set
  and exhaustively lists any alternative minimal complete unit sets. Fable
  independently reviews every mapping, exact citation-page coverage and the
  completeness of alternative paths. Planner scoring accepts any reviewed
  support-equivalent set rather than circularly requiring one privileged ID.
- Only after all frontier gates pass does `gpt-5.6-terra` at low reasoning plan
  three questions. Gold answers, facts and support IDs remain hidden from it.

The paid ceiling is 10 frontier calls plus 3 economic calls, with zero provider
retry. Frontier models are used only for pixel authorship, critical review and
support mapping; rendering, unitization, compilation, hashing and scoring are
local and deterministic.

This design-review snapshot intentionally precedes the paid-execution
preregistration. After the single allowed correction/adjudication pass, a
versioned preregistration will hash the corrected design, packet, builder,
runner, contracts, tests and both review artifacts. Preflight and paid execution
are forbidden until that file exists and verifies; its absence during design
review is therefore expected, not an execution-ready claim.

## Frozen GO / HOLD / NO-GO

`GO_S208_TARGET_PREREG` requires all of the following:

- 3/3 valid Sol candidates and 3/3 valid independent Fable candidates;
- 3/3 Fable publication reviews PASS, zero semantic duplicates, unsupported
  facts or material disagreements;
- at least one genuine cross-page fact in the frozen multipage item;
- every fact mapping uses known unit IDs and its mapped page set exactly equals
  its declared citation-page set;
- 3/3 Fable support reviews PASS;
- 3/3 valid Terra outputs, each with at least two distinct obligations;
- selected-unit precision at least 80%, 3/3 complete questions and 3/3 exact
  deterministic compilations. Atomic-fact support recall is still reported, but
  it is not duplicated as a weaker gate because 3/3 completeness already forces
  100% recall.

An unavailable credential, provider or incomplete external call yields
`HOLD_S208_EXTERNAL_OR_INCOMPLETE`. Invalid/duplicate gold, failed cross-review,
invalid mapping or failed mapping review yields the corresponding S208 NO-GO.
A structurally valid but insufficient Terra-low result yields
`NO_GO_S208_TERRA_LOW`. There is no retry or tuning loop on this cohort.

## What a GO authorizes

A GO authorizes only a separate target A/B preregistration. Before any target
call, that later PR must freeze the unchanged S141 target obligations and
contexts, baseline answers, candidate prompts and compiler, judge/scorer,
model settings, reasoning settings, seeds or explicit repeat policy, full
configuration, protected suite, hashes and GO/HOLD/NO-GO rules. Official
promotion still requires at least 11 stable new fact gains, zero prior-covered
regressions, zero new contradictions and green CI.

## Invariants

- `chunks_v2` stays active and read-only in S208.
- `chunks_v3` stays `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; there is no migration,
  materialization or per-question patch.
- S208 performs no retrieval, reranking, database write, deployment, official
  gold mutation, production integration or canonical fact movement.
- Railway remains a demo and never gates a PR or merge; green CI does.
- Closed S197–S207 lines are not reopened, and S207 receives no same-cohort
  retry or favorable reinterpretation.
