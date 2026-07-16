# S117 M2.9 — cierre contractual del ledger reconciliado v2

Este documento supersede v1. Conserva su objetivo y corrige su cierre de schemas,
inputs, manifests, autoridad, autorización e imports. Ningún código puede ejecutarse
bajo v1.

## Resultado permitido

El único GO posible es `RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY`, con autoridad
`reconciled_frozen_evidence_raw_parsed_block_surface_only`.

La formulación exacta será **100 identidades baseline-missing reconciliadas como
cubiertas por el candidato**. No se las denominará 100 facts, 100 hechos recuperados
ni 100 respuestas corregidas.

El modo de evidencia se serializa sin abreviar:

```text
candidate_evidence_mode = substituted_from_frozen_treatment_via_exact_projection_hash
candidate_per_document_receipts_persisted = false
```

M2.8 no persistió receipts candidatos completos por documento. Demostró que la
proyección candidata completa era byte-equal a la proyección treatment M2.7C. M2.9
usa por ello los campos treatment congelados como sustituto explícito; no afirma una
nueva observación per-documento.

## Inputs históricos exactos

Los JSON marcados `parsed` se cargan con parser estricto después de validar el hash
del fichero. Los demás se usan únicamente como blobs hash-bound y nunca se parsean.
Las rutas son relativas al root del worktree; toda ruta debe resolver dentro de él,
sin symlinks en ningún componente.

| role | path | SHA-256 | format | use |
|---|---|---|---|---|
| design_v1 | `evals/s117_m29_reconciled_loss_ledger_design_v1.md` | `6ff33b249266bb4ad5aeb519bdd7f5cda61af7c2bc20a07e9653a88c1818732c` | blob | hash-only |
| m27c_seed1 | `evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json` | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` | JSON | parsed |
| m27c_seed2 | `evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json` | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` | JSON | parsed |
| m27c_gate | `evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml` | `62f7b0ac1b220924f25c8c2073d8e5c301e56443d8de875cc3ab980ffdeebbbf` | blob | hash-only |
| compact100 | `evals/s117_m27_loss_rows_compact_v1.json` | `9424d343b21c4894044bfad5cc6fbfd39f2f45b9e2c3da26d8901d381820a894` | JSON | parsed |
| m28_seed1 | `evals/s117_m28_candidate_materialization_seed1_v1.json` | `b18df39ad1677d0f20da4b78f32a8823162d826ff2387a82032adbac1d292b9e` | JSON | parsed |
| m28_seed2 | `evals/s117_m28_candidate_materialization_seed2_v1.json` | `b18df39ad1677d0f20da4b78f32a8823162d826ff2387a82032adbac1d292b9e` | JSON | parsed |
| m28_gate | `evals/s117_m28_candidate_materialization_gate_v1.yaml` | `bbac69b7d2cc7e9323a3083083890feb0619a16c328e4cc7d216e5111cb24a83` | blob | hash-only |
| m28_prereg | `evals/s117_m28_candidate_materialization_prereg_v1.yaml` | `93a065b40220aa29eea9f69022a5cd582c2515a889971ca264085dcb43a11bcb` | blob | hash-only |
| m28_permit | `evals/s117_m28_candidate_materialization_execution_permit_v1.yaml` | `5ba7dea032cadce514fd8ff4f749774d5169c5cca7816daf2af4ea260bb378cc` | blob | hash-only |

El preregistro M2.9 congela exactamente 13 inputs: los 10 de la tabla anterior más
`design_v2`, runner y tests. No puede congelar su propio hash ni el del permit aún
inexistente. Después, el permit congela exactamente los hashes del preregistro,
`design_v2`, runner y tests. Solo el output final registra los 15 hashes observados:
los 13 del preregistro más preregistro y permit.

Los únicos dos ficheros implementables bajo este diseño son:

```text
scripts/s117_m29_reconciled_loss_ledger.py
tests/test_s117_m29_reconciled_loss_ledger.py
```

## JSON estricto, proyecciones y cierre de inputs

Los contratos M2.9 de preregistro y permit serán JSON estricto, no YAML. Los YAML
históricos de la tabla anterior son evidencia hash-only. El parser rechaza BOM,
duplicate keys, NaN, Infinity, -Infinity y cualquier número no finito, incluido
`1e999`.

Después de validar el hash exacto del fichero, el runner proyecta únicamente los
campos enumerados. Los otros campos de un JSON histórico quedan hash-bound pero no
son autoridad semántica del ledger.

### Proyección M2.7C

Top-level usados, con tipos exactos:

```text
instrument: str == s117_m27_loss_safe_chunking_probe_v2
authority: str == raw_store_parsed_block_surface_only
status: str == CONTRACT_GO_BASELINE_GO_TREATMENT_GO_DELTA_GO
statuses: object exacto con baseline_replay, contract_integrity,
          delta_accounted, treatment_lossless; todos str == GO
population: object exacto con baseline_covered_blocks, baseline_missing_blocks,
            baseline_rows, changed_documents, documents, raw_blocks,
            treatment_covered_blocks, treatment_missing_blocks, treatment_rows,
            unchanged_documents; todos int no bool
documents: array
checks: object con el enum histórico exacto; todos bool true
cost: object exacto database_reads, database_writes, model_calls, network_calls;
      todos int == 0
```

El enum exacto de 20 checks M2.7C es:

```text
baseline_covered_exact
baseline_manifest_exact
baseline_missing_count_exact
baseline_missing_exact
baseline_rows_exact
changed_documents_have_delta
coverage_gain_exact
delta_partitions_exact
document_population_exact
loss_document_set_exact
no_coverage_regression
override_restored
raw_blocks_exact
treatment_all_blocks_covered
treatment_surface_equal_raw_every_document
treatment_zero_missing
unaffected_fingerprint_multisets_equal
unchanged_document_count_exact
zero_adjudication
zero_external_cost
```

Cada elemento de `documents` aporta dos proyecciones. La primera es la proyección
exacta M2.8 treatment, necesaria para recomputar el puente `4cd69...`:

```text
schema: str == s117_m28_candidate_treatment_projection_v1
extraction_sha256: SHA-256
raw_artifact_sha256: SHA-256
raw_blocks: int >= 0
rows: int >= 0                         <- treatment_rows
covered_blocks: int >= 0               <- treatment_covered_blocks
missing_block_indexes: array[int]      <- treatment_missing_block_indexes
surface_sha256: SHA-256                <- treatment_surface_sha256
surface_equal_raw: bool                <- treatment_surface_equal_raw
fingerprint_multiset_sha256: SHA-256   <- treatment_fingerprint_multiset_sha256
coverage_gain_block_indexes: array[int]
coverage_regression_block_indexes: array[int]
changed: bool
```

La lista se ordena por `extraction_sha256` y su JSON canónico sin LF debe medir
640.933 bytes y tener SHA-256
`4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881`.

La segunda proyección alimenta el recibo M2.9 y exige estos campos usados y tipos,
aunque el objeto histórico puede contener más campos hash-bound:

```text
extraction_sha256: SHA-256
raw_artifact_sha256: SHA-256
raw_blocks: int >= 0
baseline_covered_blocks: int >= 0
baseline_missing_block_indexes: array[int >= 0]
treatment_covered_blocks: int >= 0
treatment_missing_block_indexes: array[int >= 0]
coverage_gain_block_indexes: array[int >= 0]
coverage_regression_block_indexes: array[int >= 0]
changed: bool
```

Los arrays de índices deben estar ordenados, ser únicos y estar dentro de
`[0, raw_blocks)`. `changed` significa exclusivamente cambio en el multiset de
fingerprints congelado; en M2.9 se renombra `fingerprint_multiset_changed`.

Los dos seeds deben producir proyecciones canónicas idénticas. Sus conteos exactos
son 1.068 documentos, 333.161 raw, baseline 333.061/100, candidato sustituto
333.161/0, 27 changed y 1.041 unchanged.

## Ecuaciones normativas de reconciliación

El runner debe demostrar estas ecuaciones por documento; copiar conteos agregados
no satisface ningún gate:

```text
candidate_missing = treatment_missing
baseline_covered = raw_blocks - len(baseline_missing)
candidate_covered = raw_blocks - len(candidate_missing)
gain = baseline_missing - candidate_missing
regression = candidate_missing - baseline_missing
```

Los campos `baseline_covered_blocks`, `treatment_covered_blocks`,
`coverage_gain_block_indexes` y `coverage_regression_block_indexes` del input deben
ser exactamente iguales a las cantidades/conjuntos recalculados. Globalmente:

```text
union(compact100 identities) = union(baseline_missing identities)
union(gain identities) = union(baseline_missing identities)
union(candidate_missing identities) = empty
union(regression identities) = empty
```

Cada fila compact100 debe pertenecer al `baseline_missing` y `gain` del mismo
`extraction_sha256`, no pertenecer a `candidate_missing`, y enlazar exactamente el
`m29_document_receipt_sha256` de ese documento. Una identidad movida a otro
documento o índice es `NO_GO`, aunque los totales sigan siendo 100/0.

### Proyección compact100

El objeto top-level exacto usado contiene:

```text
instrument == s117_m27_compact_loss_report_v1
authority == diagnostic_only_no_policy_or_semantic_adjudication
counts.rows == 100
counts.documents == 27
counts.dispositions == {authorized_exclusion: 13, unruled_loss: 87}
logical_payload_sha256 == bfb54e1465c6ef66cfd72bad02c4f4653c8e9ab60033ca627278c225aec252ab
rows: array
```

El set de claves top-level del fichero histórico es exactamente `authority`,
`authorization`, `counts`, `instrument`, `logical_payload_sha256`, `rows`, `source`
y `unique_unruled_texts`. Sus subárboles no proyectados siguen protegidos por el
hash exacto del fichero y por el logical hash, pero no aportan autoridad semántica.

Se recalcula el logical hash como SHA-256 del JSON canónico del objeto completo tras
eliminar `logical_payload_sha256`. Cada fila proyecta y valida:

```text
extraction_sha256: SHA-256
source_block_index: int >= 0
source_page_ordinal: int >= 0
page: int >= 1
kind: enum[heading, paragraph, table]
text: str
text_sha256: SHA-256 == SHA256(UTF-8(text))
ledger_receipt_sha256: SHA-256 opaco y congelado
disposition: enum[authorized_exclusion, unruled_loss]
rule_id: str standalone_numeric_page_boundary_exact_v1 si authorized_exclusion;
         null si unruled_loss
```

`ledger_receipt_sha256` no se recomputa: el compacto no conserva todos sus campos
de origen. Se trata como enlace opaco hash-bound. Las identidades
`(extraction_sha256, source_block_index)` deben ser únicas.

### Proyección M2.8

Cada receipt tiene exactamente las claves top-level `authority`, `authorization`,
`checks`, `cost`, `dependencies`, `failures`, `generation`, `instrument`,
`loadable`, `manifests`, `population`, `schema_version`, `source` y `status`. Los
subárboles no proyectados están hash-bound pero no aportan autoridad al ledger. Los
campos consumidos exigen estos valores y tipos exactos:

```text
instrument == s117_m28_candidate_materialization_v1
schema_version == 1
status == GO
loadable == false
authority == raw_store_parsed_block_whitespace_token_surface_only
failures == []
checks: objeto con exactamente 11 claves congeladas; todas true
cost: {database_reads:0, database_writes:0, external_calls_blocked:true,
       model_calls:0, network_calls:0}
population: objeto de 17 claves congeladas, incluidos documents=1068,
            raw_blocks=333161, covered_blocks=333161, missing_blocks=0,
            coverage_gain_blocks=100, coverage_regression_blocks=0,
            changed_documents=27, unchanged_documents=1041,
            validation_failures=0
manifests.candidate_projection_sha256 ==
  4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881
manifests.candidate_document_receipts_sha256 ==
  57e4624d812188f97ea0bd9c81ccb76e6693fde40db41701ad60f3dd9edb293a
manifests.coverage_gain_identities_sha256 ==
  6b0410a662c5523b04e3c19049199d8f27649653f34a6f3d87fee3a84147a675
checks.treatment_projection_exact == true
```

Ambos receipts deben ser objetos canónicos idénticos. La igualdad entre el
`candidate_projection_sha256` y el hash de la proyección treatment reconstruida
desde cada seed M2.7C es el puente candidato por documento.

Las 11 claves exactas de `checks` M2.8 son:

```text
candidate_identity_new
contract_integrity
external_calls_blocked
generation_identity_exact
global_invariants_exact
output_schema_exact
population_exact
raw_token_intervals_exact
row_mapping_and_identity_exact
source_exact
treatment_projection_exact
```

Las 17 claves exactas de `population` M2.8 son:

```text
changed_documents
coverage_gain_blocks
coverage_regression_blocks
covered_blocks
delta_added_rows
delta_overlap_modified_rows
delta_pure_added_rows
delta_removed_rows
delta_unchanged_rows
documents
missing_blocks
raw_blocks
rows
titled_rows
unchanged_documents
untitled_rows
validation_failures
```

## Schema exacto del output

No se permiten claves adicionales en ningún objeto M2.9.

### Envelope

```text
instrument: str == s117_m29_reconciled_loss_ledger_v1
schema_version: int == 1
status: enum[RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY, NO_GO]
loadable: bool == false
authority: str == reconciled_frozen_evidence_raw_parsed_block_surface_only
candidate_evidence_mode: str ==
  substituted_from_frozen_treatment_via_exact_projection_hash
candidate_per_document_receipts_persisted: bool == false
dependencies: object
population: object
documents: array
resolved_baseline_missing_identities: array
manifests: object
checks: object
failures: array
cost: object
authorization: object
```

`dependencies` tiene exactamente 15 roles: `design_v1`, `design_v2`, `runner`,
`runner_tests`, `preregistration`, `execution_permit`, `m27c_seed1`, `m27c_seed2`,
`m27c_gate`, `compact100`, `m28_seed1`, `m28_seed2`, `m28_gate`, `m28_prereg` y
`m28_permit`. Cada valor es únicamente el SHA-256 observado.

`population` tiene exactamente estas claves `int` no bool:

```text
documents
raw_blocks
baseline_covered_blocks
baseline_missing_blocks
candidate_covered_blocks
candidate_missing_blocks
coverage_gain_blocks
coverage_regression_blocks
changed_fingerprint_multiset_documents
unchanged_fingerprint_multiset_documents
baseline_authorized_exclusion_identities
baseline_unruled_loss_identities
reconciled_baseline_missing_identities
unresolved_baseline_missing_identities
```

### Recibo documental M2.9

Cada elemento de `documents` tiene exactamente:

```text
schema: str == s117_m29_document_reconciliation_v1
extraction_sha256: SHA-256
raw_artifact_sha256: SHA-256
raw_blocks: int >= 0
baseline_covered_blocks: int >= 0
baseline_missing_block_indexes: array[int]
candidate_covered_blocks: int >= 0
candidate_missing_block_indexes: array[int]
coverage_gain_block_indexes: array[int]
coverage_regression_block_indexes: array[int]
fingerprint_multiset_changed: bool
m29_document_receipt_sha256: SHA-256
```

El receipt es SHA-256 del JSON canónico del objeto sin
`m29_document_receipt_sha256`. Documentos ordenados por `extraction_sha256`.

### Identidad baseline-missing reconciliada

Cada elemento de `resolved_baseline_missing_identities` tiene exactamente:

```text
schema: str == s117_m29_resolved_baseline_missing_identity_v1
extraction_sha256: SHA-256
source_block_index: int >= 0
source_page_ordinal: int >= 0
page: int >= 1
kind: enum[heading, paragraph, table]
text_sha256: SHA-256
ledger_receipt_sha256: SHA-256 opaco
baseline_disposition: enum[authorized_exclusion, unruled_loss]
baseline_rule_id: str standalone_numeric_page_boundary_exact_v1 | null
candidate_disposition: str == covered
m29_document_receipt_sha256: SHA-256
resolution_evidence: str ==
  substituted_treatment_document_via_candidate_projection_sha256_4cd69ba2912a
m29_resolution_receipt_sha256: SHA-256
```

El receipt es SHA-256 del objeto sin `m29_resolution_receipt_sha256`. Filas ordenadas
por `(extraction_sha256, source_block_index)`.

### Manifests

JSON canónico significa UTF-8, claves ordenadas, `ensure_ascii=false` y separadores
`,`/`:` sin whitespace ni LF. Cada manifest es SHA-256 de exactamente un array
canónico, sin LF:

```text
documents_sha256 = SHA256(canonical(documents))
document_receipts_sha256 = SHA256(canonical([
  {extraction_sha256, m29_document_receipt_sha256}, ...]))
resolved_baseline_missing_sha256 =
  SHA256(canonical(resolved_baseline_missing_identities))
resolution_receipts_sha256 = SHA256(canonical([
  {extraction_sha256, source_block_index, m29_resolution_receipt_sha256}, ...]))
baseline_missing_identities_sha256 = SHA256(canonical([
  {extraction_sha256, source_block_index}, ...]))
candidate_missing_identities_sha256 = SHA256(canonical([]))
```

`manifests` contiene exactamente esas seis claves.

### Checks, failures, coste y autorización

`checks` contiene exactamente estas 15 claves bool:

```text
contract_integrity
m27c_seed_equivalence
candidate_seed_equivalence
candidate_projection_bridge_exact
document_population_exact
document_partitions_exact
compact_integrity_exact
baseline_missing_identity_set_exact
candidate_missing_empty
coverage_gain_exact
coverage_regression_empty
resolved_identity_bindings_exact
manifest_integrity_exact
output_schema_exact
zero_external_cost
```

GO si y solo si las 15 son `true` y `failures == []`. `failures` solo admite estos
códigos, sin duplicados y en este orden de prioridad:

```text
contract_integrity_failure
m27c_seed_drift
candidate_seed_drift
candidate_projection_bridge_failure
document_population_drift
document_partition_failure
compact_integrity_failure
baseline_missing_identity_drift
candidate_missing_nonempty
coverage_gain_drift
coverage_regression_nonempty
resolved_identity_binding_failure
manifest_integrity_failure
output_schema_failure
external_call_attempt
internal_failure
```

Un NO_GO usa el mismo envelope cerrado, arrays de evidencia vacíos, hashes cero,
conteos cero, las 15 checks exactamente `false` y únicamente códigos sanitizados;
nunca serializa excepciones, paths, texto, variables de entorno ni secretos.
`authorization.preregistration_frozen` refleja si el preregistro estricto y sus 13
hashes fueron validados antes del fallo; `authorization.execution_permit_valid`
refleja si el permit estricto, sus cuatro bindings y el seed fueron validados. En GO
ambos son obligatoriamente `true`; en NO_GO cada uno conserva únicamente su valor
observado. Ningún otro flag de autorización cambia.

`cost` contiene exactamente:

```text
database_reads: 0
database_writes: 0
model_calls: 0
network_calls: 0
raw_store_reads: 0
chunk_executions: 0
manual_adjudications: 0
additional_candidate_executions: 0
external_calls_blocked: true
```

`authorization` contiene exactamente:

```text
preregistration_frozen: bool observed; true required for GO
execution_permit_valid: bool observed; true required for GO
raw_store_read: false
chunk_execution: false
manual_adjudication: false
additional_candidate_execution: false
M27A: false
database: false
network: false
models: false
embeddings: false
retrieval: false
context_generation: false
load: false
serving: false
deploy: false
facts_moved_to_ok: 0
M3: BLOCKED
```

## Interlock, imports y determinismo

Preregistro y permit M2.9 son JSON estrictos y tienen schemas exactos. El
preregistro fija los 13 roles/hashes, expected population, projection hash, enums,
seeds `[1,2]` y paths de output relativos exactos. El permit fija hashes de
preregistro, design v2, runner y tests, `allowed_seeds:[1,2]`,
`additional_candidate_execution:false` y no contiene datos del corpus.

El runner no acepta rutas por CLI; solo `--seed 1` o `--seed 2`. Resuelve inputs y
output exclusivamente desde contratos fijos dentro del root. Verifica ambos
contratos y todos los hashes antes de cargar un JSON histórico.

Allowlist exacta de imports del runner:

```text
__future__.annotations
hashlib
json
math
random
socket
sys
pathlib.Path
typing.Any
```

Se prohíben `os`, `subprocess`, `importlib`, `urllib`, HTTP/DB/model SDKs, módulos de
producción y cualquier runner M2/M27/M28. No se leen variables de entorno. Un
tripwire sustituye `socket.socket` antes de leer inputs parseados y se restaura en
`finally`.

Cada seed perturba primero documentos e identidades resueltas y luego restaura el
orden canónico. Dos procesos separados deben producir JSON canónico byte-identical
con exactamente un LF final. El gate posterior registra file SHA y payload SHA.

El preregistro, permit y ejecución requieren GO adversarial separado. Nada de este
diseño autoriza raw-store, chunker, nueva ejecución candidata, M2.7A, DB, red,
modelos, load, serving, deploy ni movimiento de facts a `OK`.

## Pruebas negativas normativas

Los tests del único runner implementable deben cubrir, como mínimo:

1. drift de hash en cada clase de input seleccionado y en preregistro/permit;
2. drift entre M2.7C seed1/seed2 y M2.8 seed1/seed2;
3. tamaño/hash de proyección treatment incorrecto;
4. identidad baseline missing borrada, añadida, duplicada o movida de documento o
   índice conservando el total;
5. gain sin baseline missing, candidate missing oculto y regresión ocultada;
6. receipt documental, receipt de resolución o cualquiera de los seis manifests
   alterado con conteos intactos;
7. logical hash, `text_sha256`, disposición o `rule_id` incorrecto en compact100;
8. BOM, duplicate JSON keys, NaN, Infinity, -Infinity y `1e999`;
9. clave adicional o ausente en contratos M2.9 y en cualquier output;
10. path absoluto, `..`, backslash, symlink en fichero o directorio y escape del
    root;
11. imports fuera de allowlist, entorno, subprocess, import dinámico y módulos de
    producción/M2/M27/M28;
12. intento real de `socket.socket`, rechazo y restauración del tripwire tanto en
    éxito como en excepción;
13. perturbación seed 1/2 seguida de orden canónico y payload byte-identical;
14. canarios de texto del manual, path absoluto, mensaje de excepción, variable de
    entorno y secreto ausentes de todos los NO_GO serializados;
15. GO imposible si una check es false, existe un failure, los dos flags de
    preflight no son true, `loadable` cambia o cualquier coste deja de ser cero.

La revisión de tests debe ocurrir antes de congelar el preregistro. La ejecución del
ledger sigue requiriendo un permit y un GO adversarial posteriores.
