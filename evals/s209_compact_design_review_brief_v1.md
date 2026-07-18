# S209 compact Frontier decision brief

Review the following design decision, not code style. Return PASS only if the
experiment can validly decide whether the decomposed evidence planner should be
opened on the 12-fact synthesis target.

## Prior evidence

- Canonical baseline: 143/157 facts OK (91.08%); target 154/157 for at least
  98%. Residual: 12 synthesis misses and 2 retrieval misses.
- S193 produced the best prior signal (+5/37 and +2 complete questions), but
  selector recall was 79.4%, below its preregistered 90% gate.
- S208 generated 3 pixel golds / 20 facts. Sol's mapping was valid for all 20,
  including an exact genuine page-{2,3} support set. Fable returned every
  boolean true and PASS on all items, but put positive explanations in a legacy
  `issues` array that the preregistered validator treated as blocking. S208 was
  correctly sealed NO-GO with no retry, no planner calls and zero fact credit.

## Contract correction

- Historical v3 remains byte-identical and hash-bound.
- New v4 requires exact top-level, item and fact shapes.
- Each fact has five explicit booleans: pixel support, unit-text support,
  minimal completeness, citation-page completeness and alternative-path
  completeness.
- `blocking_issues` and audit `notes` are separate at item and fact level.
  Notes never affect verdicts. PASS requires every boolean true and no blocker.
  Any false fact must name a fact-level blocker. Unknown/legacy fields and
  truthy non-booleans fail closed.
- Deterministic fixtures cover positive notes, blockers, false booleans,
  explained FAIL, extra fields and integer-as-boolean rejection.

## Fresh cohort and honesty limits

- Two new questions/fact sets; no S208 question, fact or mapping is reused.
- Two source identities not used by S203-S208 visual cohorts, but both overlap
  official corpus sources. Neither external nor source-independent validation
  is claimed.
- Kidde has no remaining technical page of at least 700 extracted characters
  with zero S99 coverage among unused visual sources. Three initial topics were
  rejected because S99 already asked semantic equivalents.
- Replacement candidate 1: KE-DP3020W pages 1-2, a natural cross-page link from
  the visible dual-wavelength/multi-angle nuisance-discrimination mechanism to
  forward/backward scattering, supervision and particle-sensitivity specs.
- Replacement candidate 2: NC page 36, pre-test prerequisite plus quarterly,
  annual and cleaning obligations; no same-source S99 question exists on that
  page.
- Semantic novelty is not asserted locally. Sol and Fable independently author
  from pixels and cross-review; any duplicate or unsupported fact is NO-GO.
- Three 200 dpi full-page renders were directly inspected and SHA-bound. The
  packet has 25 non-overlapping, gap-free evidence units capped at 450 chars.

## Frozen execution geometry

- Principal: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent: `claude-fable-5`.
- Planner after all upstream passes: `gpt-5.6-terra`, reasoning `low`.
- Calls: 4 Frontier generations + 2 cross-reviews + 2 support reviews = 8
  Frontier maximum; 2 Terra planner calls; zero retries; zero target calls.
- Support mapper must enumerate primary and every alternative minimal complete
  unit set. Every mapped page set must exactly equal the declared citation set.
- Planner sees question, source identity and evidence units, but never answer,
  facts or support IDs. It must emit at least two obligations per question.
- GO requires: both questions valid and independently published; every support
  review passes; 0 invalid plans; selected-unit precision >=0.80; 100% atomic
  fact-support recall; 2/2 complete questions; 2/2 exact deterministic
  compilations.
- Any semantic, gold, mapping or planner failure is NO-GO with no same-cohort
  repair. Provider/model incompleteness is HOLD. GO authorizes only a separate,
  frozen target A/B and grants zero fact credit/runtime integration.
- Internal ceiling: $50; user's total ceiling $200. Railway is not a gate.
- `chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.

## Review questions

1. Does v4 remove only the schema ambiguity while preserving fail-closed
   semantics?
2. Is the two-item cohort sufficient for the narrow mechanism decision without
   being represented as external generalization?
3. Can any leakage, support-equivalence error or metric definition falsely
   produce GO?
4. Are the GO/HOLD/NO-GO and target isolation rules complete?

Return ONLY JSON:
`{"reviewer":"exact model id","verdict":"PASS or FAIL","findings":[{"id":"...","severity":"critical or major","description":"...","required_fix":"..."}],"residual_risks":["..."]}`
