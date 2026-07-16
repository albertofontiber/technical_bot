# S117 M2.8 candidate materialization design v1

## Decision this instrument may support

This instrument may establish only that the patched production chunker creates a new,
deterministic, lossless and provenance-valid local `chunks_v3` candidate over the
frozen 1,068-document development corpus. It does not establish PDF fidelity,
semantic quality, retrieval improvement, a fact-stage transition, database readiness,
or M3.

The execution output is a non-loadable receipt. It contains identities, hashes,
counts, checks and per-document receipt hashes, but no contexts, embeddings or
database mutations.

## Causal chain and fixed boundary

The candidate is allowed to inherit the M2.7C structural oracle only because all of
the following are hash-bound:

1. M2.7C proved, with two byte-identical seeded probes, that disabling the generic
   length-only deletion preserved all 333,161 parsed raw blocks and added no other
   behavioral override.
2. M2.8 changed the production `_cleanup` implementation by removing only that
   deletion and its derived merge barrier.
3. M2.8 focused tests, the full regression, and independent adversarial review passed
   on the exact production postimage.

This is structural evidence over parsed whitespace-token surfaces. The 29 added rows
are not 29 facts, and zero facts move to `OK` in this phase.

## Frozen identities

The preregistration must bind the following values before candidate execution:

- source store: 1,069 JSON files, 1,068 extraction records and only `_failures.json`
  as a non-record artifact;
- source manifest SHA-256:
  `752c044be1531d5bc2e2879f79acf1dbeffabcbeb9bb9d16f5e14a5676aa5810`;
- candidate production chunker SHA-256:
  `d851abf6761d8e5ff6dee4d2727b85c86fda21059dce8875a028cf8298e87764`;
- unchanged materializer SHA-256:
  `bb218a509ca56f2ddf4e44d73c4235cefacfb4296a4b98c9d49a627a2536e65c`;
- frozen independent row validator SHA-256:
  `36037383c1c33c630e9df6add9f3c188dc10e2dfd79ff33f53ee04f44aa4c342`;
- baseline chunker SHA-256:
  `4b76ab219854c625f4ce5e55665e2c89d14739e4eee0ab01607aae7ecda4fd43`;
- baseline generation-manifest SHA-256:
  `3040da3ace4e033f6bc52e3cf092e2427262d91729ecb67fe7a104a71cbd73a1`;
- baseline materialization ID: `eb426a33-91cb-543e-a0c9-fd615dbc36cb`;
- baseline rows-manifest SHA-256:
  `68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3`.

The candidate generation identity is derived before chunk execution from the frozen
ordered extraction/raw-artifact descriptors, the candidate chunker hash and the
unchanged materializer hash. An independent implementation of the canonical identity
contract gives:

- candidate generation-manifest SHA-256:
  `f702ddcf3d51a479fff90c95f1ccd6206680da4a262462f80a74b10c1b3c1089`;
- candidate materialization ID: `1852e61c-ac7f-5232-be1c-627ea54f29b5`.

Both must be exact and different from baseline. The candidate rows-manifest hash is
an observation, not an oracle chosen after seeing an execution. It must be identical
across the two frozen seeded executions and different from the baseline rows manifest.

## Runner architecture

The future runner is `scripts/s117_m28_candidate_materialization.py`. It composes
existing production and independent validators; it does not copy or modify chunking
logic.

For each raw record it must:

1. Strictly parse JSON and bind filename, extraction SHA-256 and raw-artifact SHA-256.
2. Invoke the production path `chunk_provenance.materialize_raw_record`, which invokes
   the current `chunk_document` directly. No `NOISE_CHARS` override, monkeypatch,
   alternate chunker, fixture-specific branch or replay of the former chunker is
   allowed.
3. Pass every materialized row through the frozen independent
   `validate_rows_against_raw` provenance validator.
4. Independently invoke the current `chunk_document` once for structural receipts and
   convert its chunks only through the frozen M2.7C row-core/fingerprint helpers.
5. Apply the frozen M2.7C v2 token-interval validator, proving that candidate row
   tokens equal raw parsed-block tokens in order and that every claimed span is the
   first/last raw block intersected by that row's token interval.
6. Compare the candidate per-document row count, token-surface hash, block coverage
   and fingerprint-multiset hash with the frozen M2.7C treatment receipt for that same
   extraction. This comparison covers all 1,068 documents. It must not rerun the old
   chunker or reconstruct a baseline with the patched chunker.
7. Recompute every stable row identity under the exact candidate materialization ID,
   check UUID validity and uniqueness, and reject any row that declares another
   materialization ID or chunker hash. Diagnostic IDs are never copied into candidate
   rows. Candidate identity generation must use the unchanged provenance contract.

The duplicate direct chunking in steps 2 and 4 is intentional: the production
materializer and the raw-token oracle exercise separate paths and are compared by
content/provenance receipts. It incurs no model, network or database cost.

## Frozen candidate oracle

Execution is GO only if all exact observations hold:

- documents: 1,068;
- raw parsed blocks: 333,161;
- candidate rows: 31,226;
- titled candidate rows: 29,413;
- untitled candidate rows: 1,813;
- covered raw blocks: 333,161;
- missing raw blocks: 0;
- coverage regressions relative to the frozen baseline receipts: 0;
- coverage gains: the exact frozen set of 100 block identities;
- documents whose fingerprint multiset changes: the exact frozen set of 27;
- unchanged documents: the exact frozen set of 1,041;
- changed-document delta carried from the frozen accounted probe:
  2,529 unchanged, 15 removed, 29 added, 15 overlap-modified and 14 pure-added rows;
- all 1,068 candidate document receipts equal their frozen treatment receipts;
- validation failures: 0.

The titled-row oracle is fixed before execution as baseline 29,399, minus 15 titled
removed rows, plus 29 titled added rows from the frozen M2.7C delta. It may not be
adjusted after candidate execution.

## Baseline comparison without contaminated replay

The baseline is data, not executable code in this instrument. The runner may read only
the frozen baseline materialization receipt and the frozen M2.7C seed receipts. It
must never execute the old runner under the candidate chunker, override the candidate
chunker to imitate baseline behavior, or label current rows with the baseline
materialization ID.

Equivalence to the diagnostic treatment is transitive but explicit:

`frozen baseline -> accounted M2.7C treatment -> patched production candidate`.

The first edge is frozen by the M2.7C gate. The runner measures the second edge over
all documents. A mismatch on either edge is NO_GO.

## Determinism and output contract

Two separate processes run with seeds 1 and 2. Each seed perturbs document processing
order and in-memory row order, after which canonical ordering is restored. The seed,
wall-clock time, physical paths and output filename are excluded from the payload.

The two UTF-8 JSON outputs must be byte-identical and have one final LF. Their logical
payload hashes, generation-manifest hashes, materialization IDs, rows-manifest hashes,
document-receipt-manifest hashes and all counts must be identical.

The receipt may include the ordered generation manifest and compact per-document
hash/count receipts. It must exclude raw text, chunk content, PDFs, contexts,
embeddings, secrets and environment values. It is marked `loadable: false`.

## Fail-closed tests before preregistration

The runner tests must prove at least:

- exact input-hash and selected-path binding;
- candidate chunker differs from baseline and candidate identity is exact;
- production invocation has no override or old-runner replay;
- malformed source manifest, filename identity and raw-artifact hash are rejected;
- omission, duplication, reorder and shifted/overclaimed spans are rejected;
- candidate row/materialization/chunker identity drift is rejected;
- a one-document fingerprint or treatment-receipt drift is rejected;
- expected counts and document sets cannot be relaxed after execution;
- seed perturbations restore the same canonical payload;
- the output contains no chunk content or raw text;
- any failed check produces `NO_GO` and a non-zero process exit.

Focused tests and the complete repository regression must pass after runner
implementation and before freezing the execution preregistration.

## Authorization boundary

Design, runner implementation, local tests and preregistration are allowed in M2.8.
Candidate execution requires a separate post-prereg GO. Even a successful candidate
materialization does not authorize database access, schema changes, retrieval-policy
changes, contexts, embeddings, load, serving, deployment, fact relabeling or M3.

After a successful candidate gate, the next upstream step is a full loss ledger and
then a repeat of M2.7A over the frozen 18 affected documents / 21 tasks. Only after
that may evidence cascade toward atomicity, retrieval, rerank and synthesis.
