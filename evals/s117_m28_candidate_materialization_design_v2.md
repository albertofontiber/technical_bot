# S117 M2.8 candidate materialization design v2

Status: proposed after adversarial rejection of v1. This document supersedes v1 for
implementation authority only after a separate adversarial GO.

## Narrow decision

The instrument may establish only that the patched production chunker creates a new,
deterministic, parsed-token-lossless and provenance-valid local `chunks_v3` candidate
over the frozen 1,068-document development corpus. Its output is a non-loadable
receipt. It does not establish PDF fidelity, semantic quality, retrieval improvement,
a fact-stage transition, database readiness or M3. Zero facts move to `OK` here.

## Selected-path and hash binding

The execution preregistration must bind every selected logical path and SHA-256 below.
The runner accepts an explicit source-workspace root and resolves the selected store
path beneath it; it does not discover paths through environment variables.

| Role | Selected path | SHA-256 |
|---|---|---|
| baseline materialization receipt | `evals/s117_chunks_v3_development_materialization_v1.json` | `d9f69e8d1428e11afa56723817f64226aa53db786c8034453dfde4adbbedca3a` |
| M2.7C preregistration | `evals/s117_m27_loss_safe_chunking_probe_prereg_v2.yaml` | `7e40c5aaea6a41c2971fba4dff1952a6909fda86e4e1cfd4b1a97cb6bef1ab22` |
| M2.7C gate | `evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml` | `62f7b0ac1b220924f25c8c2073d8e5c301e56443d8de875cc3ab980ffdeebbbf` |
| M2.7C seed 1 | `evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json` | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` |
| M2.7C seed 2 | `evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json` | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` |
| compact frozen 100 | `evals/s117_m27_loss_rows_compact_v1.json` | `9424d343b21c4894044bfad5cc6fbfd39f2f45b9e2c3da26d8901d381820a894` |
| M2.8 implementation freeze | `evals/s117_m28_content_preservation_implementation_freeze_v1.yaml` | `4f14d5341cae0a9ef7cd9e1b4a37c7ac2c76947f33d6890822ac0bc91b11584e` |
| M2.8 post-patch gate | `evals/s117_m28_content_preservation_implementation_gate_v1.yaml` | `7d0bb1690a94b9475c9537f0fbae5bac71a5d8c18346e314aed0c85371334511` |
| production chunker | `src/reingest/chunk.py` | `d851abf6761d8e5ff6dee4d2727b85c86fda21059dce8875a028cf8298e87764` |
| production materializer | `src/reingest/chunk_provenance.py` | `bb218a509ca56f2ddf4e44d73c4235cefacfb4296a4b98c9d49a627a2536e65c` |
| row/identity validator | `scripts/s117_materialize_chunks_v3_local.py` | `36037383c1c33c630e9df6add9f3c188dc10e2dfd79ff33f53ee04f44aa4c342` |
| M2.7C row-core/fingerprint helper | `scripts/s117_m27_loss_safe_chunking_probe.py` | `c89802216ef9fd4c61764987f441384c7f9e6f82b5cb39e65e39eaf2d1fd0bb0` |
| M2.7C token-interval validator | `scripts/s117_m27_loss_safe_chunking_probe_v2.py` | `84ea712f193afa8866e07a02671ca65a32cbe0153665ee72aa1280588dd00a4d` |
| canonical/surface helper | `scripts/s117_m27_live_evidence.py` | `cf2cb3f54163b68745f95075b84602a0133ca69843958516b0dc14f4ab20234a` |

Selected source store: `data/extraction/agent_anthropic-sonnet-45`, resolved beneath
the explicit source-workspace root. It must contain 1,069 JSON files, 1,068 records,
only `_failures.json` as a non-record artifact, and have store-manifest SHA-256
`752c044be1531d5bc2e2879f79acf1dbeffabcbeb9bb9d16f5e14a5676aa5810`.
The resolved store must remain beneath the supplied root. Symlink/path escape is
NO_GO. Physical roots and paths never enter the output.

The future runner, its tests, this v2 design and all executed local helpers are also
hash-bound by the execution preregistration. A selected path mismatch is NO_GO; no
fallback search is allowed.

## Frozen generation identities

Baseline evidence is limited to what is actually exposed by the frozen receipts:

- chunker: `4b76ab219854c625f4ce5e55665e2c89d14739e4eee0ab01607aae7ecda4fd43`;
- generation manifest: `3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1`;
- materialization ID: `eb426a33-91cb-543e-a0c9-fd615dbc36cb`;
- rows-manifest hash: `68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3`.

The complete baseline row-ID set is not persisted, so this instrument makes no claim
of enumerated row-ID disjointness from baseline. It uses frozen M2.7C baseline-side
receipts for row-level comparison and treats the baseline rows-manifest only as hash
evidence.

Before any chunk execution, production and independent identity implementations must
both derive from the 1,068 frozen extraction/raw descriptors:

- candidate generation-manifest SHA-256:
  `f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089`;
- candidate materialization ID: `1852e61c-ac7f-5232-be1c-627ea54f29b5`.

They must be exact and different from baseline. The candidate rows-manifest hash is a
post-execution observation: it must be byte-identical across seeded processes and
different from the baseline rows-manifest hash, but it may not be selected or adjusted
after seeing seed 1.

## Exact frozen treatment projection

Whole M2.7C document receipts cannot be compared to candidate receipts: they contain
both baseline and diagnostic treatment fields and the old treatment-contract identity.
Instead, both M2.7C seeds are projected to this exact per-document schema:

```text
schema = s117_m28_candidate_treatment_projection_v1
extraction_sha256
raw_artifact_sha256
raw_blocks
rows                         <- treatment_rows
covered_blocks               <- treatment_covered_blocks
missing_block_indexes        <- treatment_missing_block_indexes
surface_sha256               <- treatment_surface_sha256
surface_equal_raw            <- treatment_surface_equal_raw
fingerprint_multiset_sha256  <- treatment_fingerprint_multiset_sha256
coverage_gain_block_indexes
coverage_regression_block_indexes
changed
```

The projection is a list ordered by `extraction_sha256`, canonical JSON with sorted
keys, comma/colon separators and UTF-8 `ensure_ascii=false`. It contains 1,068 unique
documents, is 640,933 bytes before any final output newline, and has SHA-256
`4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881`
for each frozen seed. Seed projection mismatch is NO_GO.

Candidate projection fields are measured as follows. Raw/document, row, coverage and
surface fields come from the candidate and raw blocks. Coverage gain/regression are
set differences between candidate coverage and the frozen baseline covered set
encoded by each M2.7C receipt. `changed` is candidate fingerprint multiset inequality
against that receipt's frozen baseline fingerprint multiset. Thus none of these fields
is copied from the treatment side merely to make equality pass. The 1,068 candidate
projections must equal the frozen treatment projections byte for byte. No claim is
made that a new receipt hash equals an old dual baseline/treatment receipt hash.

## Three validation edges, with honest independence

The runner is `scripts/s117_m28_candidate_materialization.py`. There are three
explicit edges:

1. **Production rows -> independent row mapper and identity reconstruction.**
   `chunk_provenance.materialize_raw_record` produces one row list per document.
   `validate_rows_against_raw` receives that full list and reconstructs fields,
   provenance payloads, UUIDv5 row IDs and duplicate targets without calling the
   production row mapper. It does call the same current `chunk_document`, so it is
   independent of row mapping/identity code, not independent of chunking.
2. **Direct current chunks -> raw parsed-token intervals.** A separate direct
   `chunk_document` result is converted only through the frozen row-core/fingerprint
   helpers and passed to the M2.7C v2 token-interval validator. This proves ordered
   token equality, exact intersected spans, raw-bound page/diagram/confidence and
   lineage. It is the noncircular raw-content edge.
3. **Candidate projection -> frozen M2.7C treatment projection.** Candidate-measured
   counts, surfaces, coverage and fingerprints are compared with the exact projection
   above across all documents. The frozen M2.7C gate supplies the already-accounted
   baseline-to-treatment edge; the old chunker is never replayed.

There are three chunk invocations per document: production materialization, row-mapper
reconstruction and direct token validation. This redundancy is intentional and local.
Tests inject drift independently into the production rows, row reconstruction,
direct-token result and frozen projection; each edge must fail closed.

## Identity and global invariants

For every candidate row, the independent validator must recompute and exactly match:

- candidate materialization ID and chunker SHA-256;
- canonical provenance payload and its SHA-256;
- UUIDv5 row ID from candidate materialization ID, extraction, ordinal and payload;
- contiguous per-document ordinal and duplicate target.

The runner then calls the frozen `_global_failures` equivalent over all 31,226 rows and
requires globally unique row IDs and `(materialization_id, extraction_sha256,
chunk_index)` tuples, with no orphan, self, cross-generation or chained duplicate.
No baseline or diagnostic materialization/namespace/ID is ever an input to candidate
row identity. Known diagnostic IDs may be checked for equality as a supplemental
negative, but absence of equality is not presented as proof about unavailable full
ID sets.

## Frozen population oracle

All values are fixed before execution:

- documents 1,068; raw blocks 333,161; rows 31,226;
- titled rows 29,413 and untitled rows 1,813;
- covered blocks 333,161; missing blocks 0;
- exact 100 baseline-to-candidate gain identities; zero regressions;
- exact changed set 27 and unchanged set 1,041;
- frozen delta: 2,529 unchanged, 15 removed, 29 added, 15 overlap-modified and
  14 pure-added rows;
- zero validation failures.

`titled` means `bool(section_title)` is true. The title oracle is derived before
execution as baseline 29,399 minus all 15 titled removed rows plus all 29 titled added
rows from the frozen delta. It may not be relaxed after execution.

## Strict source and execution interlock

Strict JSON means: UTF-8; object root; no duplicate object keys at any depth; no NaN,
Infinity or other non-finite constants; filename stem equals the record's exact
lowercase SHA-256. Any violation is a sanitized NO_GO.

The real-store CLI refuses before reading record content unless an explicit execution
permit has the exact selected path, status `EXECUTION_GO_LOCAL_ONLY`, and hash-binds
the frozen execution preregistration, runner, tests and design. The preregistration in
turn hash-binds every dependency above and the store contract. Missing, wrong-status,
wrong-path or wrong-hash permits fail closed.

Before that permit exists, implementation tests may use only synthetic temporary
stores. The runner and tests may not read the real source store. Implementation may
create only the new runner, its tests and M2.8 contract artifacts; production files
are immutable.

Static inspection forbids `_with_treatment_override`, `build_probe`,
`_document_probe`, old-runner execution, monkeypatch/assignment of `NOISE_CHARS`,
environment access, subprocesses and DB/model clients. Imports for network access are
forbidden except an isolated `socket` tripwire that replaces connection primitives
with fail-closed stubs during execution and restores them in `finally`. Runtime tests
prove attempted network calls fail. DB/model modules are neither imported nor called.

## Determinism

Separate processes use seeds 1 and 2. Each loads the same sorted selected file list,
then shuffles processing order. Before aggregate validation, rows are separately
shuffled and restored to `(extraction_sha256, chunk_index)` order; document projections
are restored to `extraction_sha256` order. The seed is excluded from the payload.

The external post-execution gate records that one process used seed 1 and the other
seed 2 and compares their files. Outputs must be byte-identical canonical UTF-8 JSON
with sorted keys, comma/colon separators and exactly one final LF. Their logical hash,
generation identity, row-manifest hash, candidate-projection hash and all counts must
match.

## Recursively closed output and leakage controls

The output schema is exact; unknown keys at any depth are forbidden:

- top level: `instrument`, `schema_version`, `status`, `loadable`, `authority`,
  `dependencies`, `source`, `generation`, `population`, `manifests`, `checks`,
  `failures`, `cost`, `authorization`;
- `dependencies`: hashes only for preregistration, permit, runner, tests, design and
  every selected evidence/code dependency listed above;
- `source`: `store_slug`, JSON/record counts, non-record artifact names and source
  manifest hash;
- `generation`: manifest schema/hash, materialization ID, rows-manifest hash/bytes;
- `population`: only the frozen numeric counts in the population oracle;
- `manifests`: hashes only for candidate treatment projection, compact candidate
  document receipts, candidate row IDs and the frozen coverage-gain identity set;
- `checks`: a preregistered fixed mapping of check-code to boolean;
- `failures`: a sorted unique array drawn only from a preregistered failure-code enum;
- `cost`: zero integer counters plus `external_calls_blocked: true`;
- `authorization`: fixed false values for database, network, models, retrieval,
  contexts, embeddings, load, serving and deploy; `facts_moved_to_ok: 0`; `M3: BLOCKED`.

The receipt excludes generation descriptors, per-document hashes, row fields, content,
raw text, content-hash preimages, physical paths, seeds, time/runtime values, exception
messages, tracebacks, environment values and secrets. `loadable` is always false.
Exceptions are mapped by stage to fixed failure codes; messages are never serialized.

Serialized GO and NO_GO tests use unique canaries in raw/chunk text, paths, environment
values, exception messages and fake secrets. A recursive allowlist validator and raw
byte search must prove every canary absent. Tests also reject content-like keys or
unknown nested keys. Failure produces sanitized NO_GO plus a non-zero exit.

## Required implementation tests

Before freezing the execution preregistration, synthetic-only tests must prove:

- exact selected-path/hash/store binding and real-store interlock;
- strict JSON duplicate/non-finite/root/filename rejection;
- identity derivation through production and independent implementations;
- drift rejection independently on all three validation edges;
- omission, duplication, reorder and shifted/overclaimed spans fail closed;
- exact UUIDv5 derivation, global ID/ordinal uniqueness and duplicate invariants;
- exact projection schema/hash and fixed oracle/set rejection;
- no override, old replay, environment, subprocess, DB or model path exists;
- runtime network tripwire blocks attempts and restores in `finally`;
- seed perturbation restores a byte-identical canonical payload;
- recursive output allowlist and GO/NO_GO canary non-leakage;
- any failed check returns sanitized NO_GO and non-zero.

Focused tests and the complete repository regression must pass before preregistration.
The future execution preregistration freezes runner/test/design/helper hashes, failure
enum, check-key set, output schema and exact oracle. Oracle changes after either seed
are forbidden.

## Authorization boundary

This v2 may authorize only runner implementation and synthetic tests after adversarial
GO. Candidate execution requires: frozen preregistration, adversarial review of the
postimage, and a separate hash-bound `EXECUTION_GO_LOCAL_ONLY` permit. Even a successful
candidate receipt does not authorize database access, schema or retrieval changes,
contexts, embeddings, load, serving, deployment, fact relabeling or M3.

After a candidate GO, the next upstream step is a fresh full loss ledger, followed by
M2.7A over the frozen 18 affected documents / 21 tasks. Only then can evidence cascade
toward atomicity, retrieval, rerank and synthesis.
