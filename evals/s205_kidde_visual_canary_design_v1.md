# S205 — principal-author Kidde visual-gold canary

## Decision and purpose

S204 showed that the pixel contract can produce six source-supported, page-correct
candidate fact sets, but its symmetric publication rule let a standalone defect in
the non-final Fable draft veto a clean Sol draft. S205 tests the clean publication
geometry already frozen in commit `af6de65`: GPT-5.6 Sol xhigh is the sole final
gold author, Fable 5 is an independent blind author and the independent reviewer
of every Sol candidate.

This is a fresh population, not a repair, retry, salvage or post-selection of S204.
The official scoreboard remains 143/157 facts OK (91.08%): S205 creates candidate
evaluation material and gives zero official credit until a separately frozen bot
evaluation converts facts.

## Publication geometry

- Sol xhigh authors the only publishable candidates.
- Fable authors blind counterparts before either review sees the other draft.
- Fable must PASS every Sol candidate, every fact and the whole cohort from pixels.
- Sol reviews the Fable counterparts as an independent material-disagreement probe.
- A flaw belonging only to an unpublished Fable counterpart is diagnostic, not a
  veto. Topic drift, counterpart disagreement with Sol or any material disagreement
  remains a veto.
- Candidate merge, repair, retry, salvage and post-selection are forbidden.

The generic gate is isolated in `src/rag/principal_visual_gold.py`; the provider
runtime is reusable and enforces exact model identities, zero retries and a sealed
call ledger. S204 artifacts remain immutable.

## Fresh source units

Selection happened after the geometry commit and before model or bot output. The
builder discovers each complete locally available product-document set, binds PDF
and 200 dpi pixel hashes, and carries all 51 existing gold questions plus the 116
S99 HyQ questions associated with the selected sources for semantic duplicate
screening.

| ID | Frozen page/predicate | Stratum |
| --- | --- | --- |
| `kidde_kuwait_pcb_callouts` | Kuwait 2X-A manual p.10: numbered PCB connectors and components | dense hardware diagram |
| `kidde_touchscreen_regions` | Spanish 2X-AT quick-start p.11: three numbered idle-screen regions | annotated UI diagram |
| `kidde_900_is_barriers` | 900 Series compatibility list p.5: exact conventional IS barrier models/functions | dense compatibility table |

All selected source basenames and byte hashes are disjoint from the existing gold
sources. S99 has no question on any focus page. S203 and S204 cohorts are closed
and excluded.

## Bounded frontier protocol

- Principal/final author: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent author and principal reviewer: `claude-fable-5`.
- Three pixel-only generations per model plus one batched cross-review per model:
  eight paid calls maximum, provider retries zero, USD 40 conservative ceiling.
- A semantic `INSUFFICIENT` is NO-GO. A provider/model identity, completion or JSON
  failure is HOLD. No same-item retry follows either result.
- No separate frontier design loop is opened: S204 already exercised exact frontier
  design attempts, the successor geometry is a deterministic correction frozen
  before population selection, and the eight calls include the critical independent
  pixel review. This avoids analysis churn and spends frontier tokens on evidence.

## GO / HOLD / NO-GO

- `GO_KIDDE_GOLD_CANARY`: all six candidates are locally valid; Fable passes all
  Sol candidates; every counterpart remains topic-aligned and there is zero material
  disagreement. Only the three Sol candidates are emitted, still unintegrated.
- `HOLD_FRONTIER_INCOMPLETE`: any exact provider/model response is incomplete,
  malformed or missing.
- `NO_GO_VISUAL_GOLD`: source/candidate insufficiency, any blocking finding in a Sol
  candidate, topic drift or any material disagreement.

## Downstream boundary

A GO authorizes only a new PR that freezes corpus/chunks_v2, index/embeddings,
retrieval/rerank/generation configuration, judge/seeds, baseline outputs and
zero-regression thresholds before evaluating these questions. It does not authorize
database writes or production activation. `chunks_v3` remains
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` as an explicit evaluation line. Railway is a demo;
green CI, not Railway, gates PRs and merges.
