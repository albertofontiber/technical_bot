# S117 M2.8 candidate materialization design v3 — pure validation addendum

Status: proposed after adversarial rejection of the v2 runtime import closure.

This addendum supersedes only the runtime-helper, implementation-whitelist and related
test clauses of `s117_m28_candidate_materialization_design_v2.md`. Every other v2
contract remains normative, including the selected evidence hashes, exact neutral
projection, three validation edges, identities, population oracle, execution
interlock, recursive output schema, determinism and authorization boundary. If the
documents conflict, v3 wins. The execution preregistration must hash-bind both v2 and
v3.

## Defect closed by this addendum

The M2.7C probe helpers cannot be imported by the candidate runtime. Their import
closure reaches M2 legacy reuse code, `os`, dotenv, contextualization, embedding and
model configuration. Hash-binding those modules would document the coupling but would
not satisfy the zero-environment/zero-model contract.

Therefore M2.7 files are frozen evidence inputs only. Candidate code may parse their
JSON/YAML artifacts as data, but may not import any M2, M26 or M27 Python module.

## Pure M2.8 validation module

Implementation adds `scripts/s117_m28_candidate_validation.py`. It owns the minimum
pure functions needed by the runner:

1. canonical JSON bytes and SHA-256;
2. whitespace-token surface normalization;
3. treatment row-core and fingerprint construction;
4. strict seed-to-neutral-projection extraction;
5. candidate document projection construction;
6. raw parsed-block/token-interval, span, page, diagram, confidence and lineage
   validation;
7. recursive output-schema validation and sanitized failure-code validation.

It does not copy chunking, packing, splitting, row mapping or identity generation.
Production chunking remains in `src/reingest/chunk.py`; production row mapping remains
in `src/reingest/chunk_provenance.py`; independent row/UUID reconstruction and global
row invariants remain in `scripts/s117_materialize_chunks_v3_local.py`.

The pure helper may import only:

- Python standard-library modules with no environment, subprocess, network, database
  or model access;
- `src.reingest.chunk`;
- `src.reingest.chunk_provenance`;
- `scripts.s117_materialize_chunks_v3_local` for its safe row/lineage/global validators.

The candidate runner may import only the same safe closure plus
`scripts.s117_m28_candidate_validation` and `yaml`. Neither runner nor helper may
import M2/M26/M27 Python modules, config, dotenv, contextualize, embed, OpenAI,
Anthropic, requests/http clients, database clients or project application modules.

## Revised validation graph

The three v2 evidence edges remain, but all executed helpers are safe M2.8/local code:

1. Production `materialize_raw_record` rows are compared as a per-document list with
   `validate_rows_against_raw`, which independently reconstructs row fields,
   provenance payloads and UUIDv5 identities while reusing the current chunker.
2. A separate current `chunk_document` result is converted by the pure M2.8 row-core
   helper and validated by the pure M2.8 raw-token interval validator. This validator
   is an implementation port of the already-frozen v2 rules, not an import or wrapper
   around M2.7 code.
3. Candidate projections built by the pure M2.8 helper are byte-compared with the
   exact neutral projections extracted as data from both frozen M2.7C seed files.

The runner still performs three chunk invocations per document. Independence remains
limited exactly as stated in v2: edge 1 independently validates mapping/identity, edge
2 validates chunk output against raw parsed tokens, and edge 3 validates the full
candidate population against frozen treatment evidence.

## Exact equivalence contract for the pure port

Before execution preregistration, synthetic vectors must freeze and test:

- canonical JSON encoding, Unicode behavior and SHA-256;
- whitespace normalization over spaces, tabs and line breaks;
- anchor/lineage conversion and row fingerprint fields;
- accepted same-block splits and legitimate partial-overlap spans;
- rejected omission, duplication, reorder, empty surface, shifted span and overclaim;
- raw-bound page, Mermaid/flow, page-image, confidence and lineage behavior;
- projection field renaming and exact canonical ordering;
- seed-1 and seed-2 neutral projection: 1,068 documents, 640,933 canonical bytes and
  SHA-256 `4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881`.

Synthetic expected hashes/receipts are literal fixtures frozen in the tests; the helper
may not generate its own expected values during assertions. The future real execution
must still require byte equality between candidate and frozen treatment projections,
so synthetic equivalence cannot replace the full-corpus gate.

## Recursive import-closure proof

The tests parse imports recursively from these local roots:

- future candidate runner;
- pure M2.8 validator;
- `scripts/s117_materialize_chunks_v3_local.py`;
- `src/reingest/chunk.py`;
- `src/reingest/chunk_provenance.py`;
- any local module newly reached by those files.

An explicit preregistered allowlist names every permitted local module and external
package. Any unlisted local edge, dynamic import, wildcard import or import parse
failure is NO_GO. AST inspection rejects access to `os.environ`, `os.getenv`, dotenv,
subprocess, sockets outside the isolated blocking tripwire, HTTP clients, DB clients,
model SDKs, config modules and the forbidden project namespaces.

A clean interpreter import test then imports only the future runner and pure helper and
asserts that no forbidden namespace is present in `sys.modules`. This test may launch
a local Python subprocess solely to obtain a clean interpreter; subprocess use remains
forbidden in the runner/helper runtime closure. The subprocess receives an explicit
working directory and no secrets; it performs no network or external call.

The future preregistration hash-binds the pure helper, runner, tests and every file in
the accepted local import closure. Frozen M2.7 Python files remain path/SHA evidence
for historical audit but are explicitly absent from the runtime import allowlist.

## Revised static forbidden set

Runner/helper source and recursive closure must contain no reference or import path to:

- `_with_treatment_override`, `build_probe` or `_document_probe`;
- `s117_m27_*`, `s117_m26_*`, `s117_m2_*` or any old runner;
- `NOISE_CHARS` assignment, monkeypatch or override;
- environment readers or `.env`;
- subprocess/process launch;
- network connection primitives except the isolated fail-closed socket tripwire;
- DB/Supabase/Postgres clients;
- model, contextualization or embedding modules.

M2.7 evidence paths may appear only as selected data-file strings in contract loading;
they must never appear in an import statement or dynamic import.

## Implementation whitelist and interlock

After adversarial GO on v3, the only permitted implementation changes are:

- create `scripts/s117_m28_candidate_validation.py`;
- create `scripts/s117_m28_candidate_materialization.py`;
- create `tests/test_s117_m28_candidate_materialization.py`;
- create or update M2.8 design, preregistration and gate artifacts.

No production file, M2.7 evidence/code, schema, policy or serving path may change.
Before a frozen execution preregistration and separate `EXECUTION_GO_LOCAL_ONLY`
permit exist, tests use synthetic temporary data only and the CLI must refuse the real
store before reading record content.

## Authorization

Adversarial GO on this addendum authorizes only the pure helper, runner and synthetic
tests on the whitelist. It does not authorize real-store candidate execution,
preregistration status changes, execution permit, database/network/model calls,
retrieval changes, load, serving, deployment, fact relabeling or M3.
