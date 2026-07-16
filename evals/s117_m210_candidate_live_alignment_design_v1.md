# S117 M2.10 — repetición causal M2.7A sobre el candidato v1

Estado: diseño para revisión adversarial. No autoriza implementación ni ejecución.

## Objetivo y autoridad

M2.10 responde únicamente:

> Tras la preservación de contenido M2.8, ¿los 18 documentos y 21 tasks live del
> piloto M2.7A quedan mecánicamente alineados con la superficie de bloques parseados,
> y sigue existiendo una correspondencia exacta para cada target/overlap?

Un GO se denomina `CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY`. Su autoridad es
`frozen_candidate_projection_and_delta_raw_parsed_block_surface_only`.

No adjudica semántica, retrieval, rerank, synthesis ni facts `OK`; no prueba
fidelidad PDF/visual; no crea row IDs candidatos; no autoriza M3, DB, load, serving o
deploy.

## Por qué no se reejecuta el chunker

M2.8 ya ejecutó el chunker productivo sobre los 1.068 documentos y demostró:

- igualdad exacta entre la proyección candidata y la proyección treatment M2.7C;
- token stream candidato igual al raw parsed-token stream en cada documento;
- 333.161/333.161 bloques cubiertos y 0 missing;
- delta de fingerprints exacto contra baseline.

M2.9 reconcilió después las 100 identidades baseline-missing como candidate-covered,
con 0 regresiones. Volver a leer el raw store o ejecutar el chunker sobre 18
documentos no aportaría una medición independiente: repetiría el productor ya
validado. M2.10 deriva un recibo causal desde evidencia congelada y explicita toda
sustitución.

```text
candidate_evidence_mode =
  substituted_from_m27c_treatment_via_m28_exact_projection_hash
candidate_rows_persisted = false
candidate_row_ids_claimed = false
```

## Inputs históricos exactos

Los JSON se validan por hash antes de parsearse de forma estricta. Los YAML se usan
solo como blobs hash-bound.

| role | path | bytes | SHA-256 | use |
|---|---|---:|---|---|
| m27a_seed1 | `evals/s117_m27_live_evidence_seed1_v1.json` | 55.785.643 | `47e591d472b501bce3439fa081d9b7478296f0035fbb4a84ef7ef7c1c4a7bb13` | parsed |
| m27a_seed2 | `evals/s117_m27_live_evidence_seed2_v1.json` | 55.785.643 | `47e591d472b501bce3439fa081d9b7478296f0035fbb4a84ef7ef7c1c4a7bb13` | equality/hash only |
| m27a_gate | `evals/s117_m27_live_evidence_gate_v1.yaml` | 4.011 | `26f009b232fcebbdfa544410581f82e33ec87de253cebd8d542caed61c838692` | hash-only |
| m27c_seed1 | `evals/s117_m27_loss_safe_chunking_probe_seed1_v2.json` | 2.471.378 | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` | parsed |
| m27c_seed2 | `evals/s117_m27_loss_safe_chunking_probe_seed2_v2.json` | 2.471.378 | `24c99a59a448284fca342c36941973b092dec1bc5c5f6c6586e09e730ec858f7` | equality/hash only |
| m27c_gate | `evals/s117_m27_loss_safe_chunking_probe_gate_v2.yaml` | 2.926 | `62f7b0ac1b220924f25c8c2073d8e5c301e56443d8de875cc3ab980ffdeebbbf` | hash-only |
| m28_seed1 | `evals/s117_m28_candidate_materialization_seed1_v1.json` | 4.264 | `b18df39ad1677d0f20da4b78f32a8823162d826ff2387a82032adbac1d292b9e` | parsed |
| m28_seed2 | `evals/s117_m28_candidate_materialization_seed2_v1.json` | 4.264 | `b18df39ad1677d0f20da4b78f32a8823162d826ff2387a82032adbac1d292b9e` | equality/hash only |
| m28_gate | `evals/s117_m28_candidate_materialization_gate_v1.yaml` | 6.229 | `bbac69b7d2cc7e9323a3083083890feb0619a16c328e4cc7d216e5111cb24a83` | hash-only |
| m29_seed1 | `evals/s117_m29_reconciled_loss_ledger_seed1_v1.json` | 704.522 | `06c82f2a276b0be28926205dc3910b0c7f3468b97a623c5114d6892bd146daf1` | parsed |
| m29_seed2 | `evals/s117_m29_reconciled_loss_ledger_seed2_v1.json` | 704.522 | `06c82f2a276b0be28926205dc3910b0c7f3468b97a623c5114d6892bd146daf1` | equality/hash only |
| m29_gate | `evals/s117_m29_reconciled_loss_ledger_gate_v1.yaml` | 6.239 | `ed243b6b6922f14464b0d300ba203cf580548550e3e2b22e2e14b52ea23eaa17` | hash-only |

El preregistro posterior añadirá este diseño, runner y tests; el permit se crea
después. No puede haber autorreferencia.

## Cadena causal por documento

Antes de proyectar, el runner recomputa los 18 receipts documentales y 21 receipts
de task M2.7A, sus cuatro manifests y sus enlaces internos. También recomputa los
receipts/proyecciones M2.7C y valida los receipts M2.8/M2.9 contra sus schemas
cerrados. Un hash de fichero correcto no sustituye estos checks internos.

### Puente baseline M2.7A → M2.7C

Para cada uno de los 18 documentos, la evidencia M2.7A se proyecta al mismo contrato
de fingerprint usado por M2.7C. Se exige exactamente:

```text
m27a.raw_artifact_sha256 = m27c.raw_artifact_sha256
m27a.raw_surface_sha256 = m27c.raw_surface_sha256
len(m27a.v3_rows) = m27c.baseline_rows
fingerprint_multiset(m27a.v3_rows) =
  m27c.baseline_fingerprint_multiset_sha256
```

Así, `fingerprint_multiset_equal` no queda flotando sobre un baseline distinto del
que contiene los 21 targets. Este puente es obligatorio tanto en documentos changed
como unchanged.

### Poblaciones exactas

Del M2.7A congelado:

```text
affected_documents = 18
live_tasks = 21
baseline_aligned_documents = 17
baseline_unresolved_documents = 1
baseline_aligned_tasks = 20
baseline_unresolved_tasks = 1
```

El conjunto de documentos `changed=true` de M2.7C contiene 27 identidades. Su
intersección exacta con los 18 documentos live debe ser:

```text
{
  8d128ca2ca13754bb74e0dcf16014e74141e352ae819aa25e35784c2f60245f6
}
```

Los otros 17 documentos deben tener simultáneamente:

```text
changed = false
fingerprint_multiset_equal = true
treatment_surface_equal_raw = true
treatment_missing_block_indexes = []
coverage_regression_block_indexes = []
```

La proyección treatment completa de 1.068 documentos debe recomputar exactamente
640.933 bytes y SHA
`4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881`.
Ambos receipts M2.8 deben declarar ese mismo hash y
`treatment_projection_exact=true`. Ese puente permite denominar candidata a la
evidencia treatment, sin afirmar receipts candidatos persistidos por documento.

### Único documento cambiado

Para `8d128...45f6`, el contrato exacto es:

```text
raw_blocks = 1455
baseline_rows = 119
candidate_rows = 119
baseline_missing = [630, 631]
candidate_missing = []
gain = [630, 631]
regression = []
delta = {unchanged:118, removed:1, added:1, modified:1}
```

La única modificación lógica es:

```text
baseline ordinal 39, span 629..629,
  fingerprint f87e6ec0eea220727a09870c81b4b5578142b555ee0f8656d1655260d5c836ac
candidate ordinal 39, span 629..631,
  fingerprint 286610fb5e5771fd4d21fbe184222e1f437da198689c87566a3b0cd5ed180439
```

El único task live del documento es
`acd5058d-06cf-5626-aabd-a93eb75b2f44`. Su target congelado es ordinal 61,
span `796..796`, content SHA
`995c4ac013e1dcb64dca7740592d61f15f07b27dc516357678cc7b0063865a17`
y fingerprint
`83adfac4b272c0130e1d86d1851b55b29bc50e4f725aab8320c7cbe4602ec70d`.
El delta debe contener exactamente el mapping unchanged `61 -> 61` con ese
fingerprint. El row modificado `39 / 629..631` no puede solapar el target/overlap
`61 / 796..796`.

El candidate surface SHA del documento debe ser igual al raw surface SHA. Por tanto,
el documento pasa de `unresolved` a `exact_whitespace_equivalent` por la recuperación
de los bloques 630–631; no por una excepción del task distante.

## Cadena causal por task

Para cada uno de los 21 task receipts M2.7A se reconstruye el fingerprint lógico del
target y de sus rows solapadas con el mismo contrato M2.7C:

```text
fingerprint = SHA256(canonical({
  content_surface_sha256,
  source_block_start,
  source_block_end,
  section_lineage,
  section_title,
  section_path,
  page_number,
  is_flow_diagram,
  has_diagram,
  confidence
}))
```

Gates exactos:

1. Hay 21 targets y exactamente una row solapada por task.
2. Los 21 fingerprints target son únicos dentro de su documento baseline.
3. Los 21 fingerprints overlap son únicos dentro de su documento baseline.
4. Para los 20 tasks en los 17 documentos unchanged, la igualdad exacta del
   multiset baseline/candidato implica una única ocurrencia candidata de cada
   fingerprint.
5. Para el task del documento changed, target y overlap usan el mapping unchanged
   `61 -> 61` y el delta modificado es disjunto.
6. El documento de cada task tiene candidate surface igual a raw, 0 candidate
   missing y 0 regression.

El resultado demuestra membership lógica exacta. No serializa ni inventa row IDs o
materialization IDs por task. Para los documentos unchanged tampoco afirma un
ordinal candidato si no existe un mapping ordinal persistido; usa
`unique_fingerprint_membership`. Solo el documento changed puede serializar el
mapping `61 -> 61` porque está explícito en el delta congelado.

## Output cerrado y sin contenido

El output no loadable contiene exactamente:

```text
instrument
schema_version
status
loadable
authority
candidate_evidence_mode
candidate_rows_persisted
candidate_row_ids_claimed
dependencies
counts
documents
tasks
manifests
checks
failures
cost
authorization
```

### Document receipt

Exactamente 18 objetos, ordenados por extraction SHA:

```text
schema = s117_m210_candidate_document_alignment_v1
extraction_sha256
baseline_alignment_status
candidate_alignment_status
candidate_surface_sha256
raw_surface_sha256
candidate_surface_equal_raw
candidate_missing_block_indexes
coverage_gain_block_indexes
coverage_regression_block_indexes
fingerprint_multiset_changed
candidate_mapping_mode =
  unchanged_fingerprint_multiset | frozen_changed_delta
m210_document_receipt_sha256
```

No incluye raw text, base64, rows ni rutas. El receipt hashea el objeto sin su propio
campo.

### Task receipt

Exactamente 21 objetos, ordenados por `local_row_id`:

```text
schema = s117_m210_candidate_task_alignment_v1
local_row_id
extraction_sha256
original_task_evidence_receipt_sha256
target_content_sha256
target_fingerprint_sha256
target_source_block_start
target_source_block_end
target_baseline_occurrences
target_candidate_occurrences
overlap_count
overlap_fingerprints_sha256
all_overlap_fingerprints_unique
candidate_membership_mode =
  unique_fingerprint_membership | frozen_delta_unchanged_mapping
candidate_ordinal = int | null
changed_delta_disjoint_from_target
baseline_alignment_status
candidate_alignment_status
m210_document_receipt_sha256
m210_task_receipt_sha256
```

`candidate_ordinal` es 61 solo para `acd5058d...`; es null para los otros 20. No se
serializa contenido, títulos, lineage ni ventanas raw.

### Conteos, manifests y checks

Conteos exactos preregistrables:

```text
documents = 18
tasks = 21
baseline_aligned_documents = 17
baseline_unresolved_documents = 1
candidate_aligned_documents = 18
candidate_unresolved_documents = 0
baseline_aligned_tasks = 20
baseline_unresolved_tasks = 1
candidate_aligned_tasks = 21
candidate_unresolved_tasks = 0
changed_affected_documents = 1
unchanged_affected_documents = 17
unique_target_memberships = 21
unique_overlap_memberships = 21
```

Manifests exactos sobre arrays JSON canónicos sin LF:

```text
documents_sha256
document_receipts_sha256
tasks_sha256
task_receipts_sha256
affected_document_identities_sha256
task_identities_sha256
```

Checks bool exactos:

```text
contract_integrity
m27a_seed_equivalence
m27c_seed_equivalence
m28_seed_equivalence
m29_seed_equivalence
m27a_m27c_baseline_bridge_exact
candidate_projection_bridge_exact
affected_population_exact
changed_intersection_exact
document_alignment_exact
target_fingerprints_unique
overlap_fingerprints_unique
changed_target_mapping_exact
task_membership_exact
manifest_integrity_exact
output_schema_exact
zero_external_cost
```

GO solo si los 17 son `true` y `failures=[]`. Los failure codes son un enum cerrado;
cualquier NO_GO tiene arrays vacíos, counts cero, manifests/dependencies cero, checks
bool exactamente false y ninguna excepción/path/contenido.

Coste exacto cero para modelos, red, DB, raw-store, chunk executions, embeddings,
context generation y candidate executions.

Autorización mantiene `adjudication:false`, `M27A_complete:false` hasta el gate,
`facts_moved_to_ok:0`, `M3:BLOCKED`, y false para retrieval, rerank, synthesis, load,
serving y deploy.

## Implementación y ejecución

Runner stdlib-only, sin imports de producción ni runners M27/M28/M29. Contratos
M2.10 en JSON estricto; YAML histórico hash-only. Se parsea solo seed1 de cada par
después de exigir igualdad byte/hash con seed2. Esto evita duplicar en memoria los
55,8 MB M2.7A.

Dos procesos seeds 1/2 perturban documentos/tasks antes de restaurar orden canónico.
Outputs byte-identical, JSON canónico y un LF. Paths fijos; escritura exclusiva y
protegida frente a symlink/junction; socket tripwire restaurado en éxito/fallo;
no-go sanitizado.

Pruebas negativas mínimas:

- drift de cualquier input, seed pair, projection hash o population;
- intersección changed distinta de la identidad exacta;
- target/overlap no único, ausente o duplicado;
- delta 61→61 alterado, row39 solapando 796 o gain 630–631 incompleto;
- document surface/missing/regression inconsistente;
- identidad movida y artefacto re-firmado;
- cualquiera de receipts/manifests alterado;
- tipos bool/int ambiguos, extra/missing keys, BOM/duplicate/nonfinite JSON;
- path/symlink/junction/output preexistente;
- intento de red y restauración del tripwire;
- canarios reales de contenido, path, excepción, entorno y secreto en NO_GO.

Secuencia: GO de diseño → runner/tests → regresión/revisión → preregistro → permit →
dos ejecuciones → gate. Ninguna etapa autoriza modelos, adjudicación ni downstream.

## Cierre normativo v1.1

Esta sección supersede cualquier formulación descriptiva anterior que resulte menos
específica. Es el único contrato implementable.

### Fingerprint y multiset exactos

`surface(text)` es exactamente `" ".join(text.split())`. El core de cada row tiene
exactamente estas claves y ninguna otra:

```text
content_surface_sha256 = SHA256(UTF-8(surface(content)))
source_block_start
source_block_end
section_lineage
section_title
section_path
page_number
is_flow_diagram
has_diagram
confidence
```

`fingerprint_sha256 = SHA256(canonical_json(core))`. `canonical_json` es UTF-8,
`ensure_ascii=false`, claves ordenadas, separadores `,`/`:` sin whitespace, sin LF y
con números finitos.

El multiset de un documento se calcula así:

1. crear pares `(fingerprint_sha256, ordinal)` para todas las rows;
2. ordenar lexicográficamente por ese par;
3. enumerar el array ordenado desde cero y producir por elemento exactamente
   `{fingerprint_sha256, occurrence}`, donde `occurrence` es el índice global de esa
   enumeración, no un contador por fingerprint;
4. `fingerprint_multiset_sha256 = SHA256(canonical_json(array))`.

El bridge 18/18 requiere igualdad de ese SHA con
`m27c.documents[*].baseline_fingerprint_multiset_sha256`.

### Proyección exacta M2.7A

Top-level debe tener exactamente las claves históricas `authorization`, `checks`,
`claim`, `contract_integrity`, `cost`, `counts`, `dependencies`, `determinism`,
`evidence_status`, `instrument`, `legacy_document_receipts`, `manifests`,
`mechanical_alignment_status`, `raw_document_receipts`, `review_fiches`, `status` y
`task_evidence`.

Valores gateados:

```text
instrument = s117_m27_live_evidence_v1
contract_integrity = GO
evidence_status = GO
mechanical_alignment_status = NO_GO
status = CONTRACT_GO_EVIDENCE_GO_ALIGNMENT_NO_GO
counts = {affected_documents:18, aligned_documents:17, aligned_tasks:20,
          live_tasks:21, original_complete_tasks:14, supplemented_tasks:7,
          unresolved_alignment_documents:1, unresolved_alignment_tasks:1}
```

Cada `raw_document_receipt` tiene exactamente las 17 claves históricas:

```text
alignment_status
document_stream_whitespace_equal
extraction_sha256
first_surface_mismatch
independent_validation_failures
raw_artifact_base64
raw_artifact_bytes
raw_artifact_sha256
raw_block_manifest_sha256
raw_blocks
raw_surface_sha256
receipt_sha256
row_by_row_regeneration_equal
schema
v3_row_manifest_sha256
v3_rows
v3_surface_sha256
```

`schema = s117_m27_raw_document_stream_evidence_v1`. El receipt es
`SHA256(canonical_json(objeto sin receipt_sha256))`. Cada raw block y v3 row también
debe tener receipt válido con la misma fórmula. Los 18 extraction SHA son únicos.
Raw block tiene exactamente `kind`, `lineage`, `page`, `receipt_sha256`,
`source_block_index`, `text`, `text_sha256`. V3 row tiene exactamente
`chunk_index`, `chunker_sha256`, `confidence`, `content`, `content_sha256`,
`duplicate_of`, `extraction_sha256`, `has_diagram`, `id`, `is_flow_diagram`,
`materialization_id`, `page_number`, `provenance_contract`,
`provenance_payload_sha256`, `provenance_version`, `raw_artifact_sha256`,
`receipt_sha256`, `section_anchor`, `section_lineage`, `section_path`,
`section_title`, `source_block_end`, `source_block_start`.

Cada `task_evidence` tiene exactamente las 21 claves históricas:

```text
adjudication_status
boundary
comparison_receipt_sha256
evidence_complete
extraction_sha256
frozen_policy_evidence
legacy_evidence_completion_verified
legacy_evidence_mode
legacy_evidence_receipt_sha256
local_row_id
mechanical_raw_alignment
original_raw_evidence_sha256
original_task_receipt_sha256
overlap_manifest_sha256
overlapping_v3_rows
raw_block_window
raw_block_window_manifest_sha256
raw_document_receipt_sha256
receipt_sha256
schema
target_row
```

`schema = s117_m27_live_task_evidence_v1`, `evidence_complete=true`,
`adjudication_status=not_authorized`; receipt con la misma fórmula. Target y overlap
rows tienen receipts válidos. Las 21 identidades son únicas y enlazan uno de los 18
document receipts.

Los cuatro manifests M2.7A se recomputan como SHA-256 de la concatenación, en orden
por la clave indicada, de `canonical_json(row) + LF`:

```text
raw_document_receipts_sha256      key extraction_sha256
legacy_document_receipts_sha256   key extraction_sha256
task_evidence_sha256              key local_row_id
review_fiches_sha256              key local_row_id
```

Solo después se proyectan fingerprints; `raw_artifact_base64`, contenido y ventanas
no se serializan en M2.10.

Las 11 checks M2.7A exactas son `affected_documents_exact`,
`all_21_evidence_complete`, `all_task_receipts_crosslinked`, `live_tasks_exact`,
`m27_seed_bytes_identical`, `m27_seed_receipts_valid`, `original_complete_exact`,
`review_fiches_exact`, `supplemented_incomplete_exact`, `zero_adjudication`,
`zero_external_cost`; todas bool true. Cost tiene exactamente `database_reads`,
`database_writes`, `embedding_calls`, `model_calls`, todos int no bool y cero.

### Proyección exacta M2.7C

Top-level exacto: `authority`, `authorization`, `changed_document_deltas`, `checks`,
`cost`, `dependencies`, `determinism`, `documents`, `instrument`, `manifests`,
`population`, `status`, `statuses`, `supersedes`, `treatment_contract`.

Valores gateados: instrument `s117_m27_loss_safe_chunking_probe_v2`, authority
`raw_store_parsed_block_surface_only`, status
`CONTRACT_GO_BASELINE_GO_TREATMENT_GO_DELTA_GO`, los cuatro statuses `GO`, 20 checks
bool true, coste externo cero y population exacta 1.068/333.161,
baseline 31.212 rows/333.061 covered/100 missing, treatment 31.226/333.161/0,
27 changed y 1.041 unchanged.

Las 20 checks exactas son `baseline_covered_exact`, `baseline_manifest_exact`,
`baseline_missing_count_exact`, `baseline_missing_exact`, `baseline_rows_exact`,
`changed_documents_have_delta`, `coverage_gain_exact`, `delta_partitions_exact`,
`document_population_exact`, `loss_document_set_exact`, `no_coverage_regression`,
`override_restored`, `raw_blocks_exact`, `treatment_all_blocks_covered`,
`treatment_surface_equal_raw_every_document`, `treatment_zero_missing`,
`unaffected_fingerprint_multisets_equal`, `unchanged_document_count_exact`,
`zero_adjudication`, `zero_external_cost`.

Cada documento consumido exige, como mínimo tipado exacto, los campos:

```text
schema = s117_m27_loss_safe_chunking_document_v1
extraction_sha256, raw_artifact_sha256, raw_blocks
baseline_rows, baseline_covered_blocks, baseline_missing_block_indexes
baseline_surface_sha256, baseline_fingerprint_multiset_sha256
treatment_rows, treatment_covered_blocks, treatment_missing_block_indexes
treatment_surface_sha256, treatment_surface_equal_raw
treatment_fingerprint_multiset_sha256
coverage_gain_block_indexes, coverage_regression_block_indexes
fingerprint_multiset_equal, changed, receipt_sha256
```

El document receipt se recomputa sobre el objeto histórico completo sin
`receipt_sha256`. Índices int no bool, ordenados, únicos y dentro de raw_blocks.
Covered/missing/gain/regression cumplen las ecuaciones por conjuntos de M2.9.

La proyección treatment exacta es el array de 1.068 objetos M2.8 con las 13 claves
`schema`, `extraction_sha256`, `raw_artifact_sha256`, `raw_blocks`, `rows`,
`covered_blocks`, `missing_block_indexes`, `surface_sha256`, `surface_equal_raw`,
`fingerprint_multiset_sha256`, `coverage_gain_block_indexes`,
`coverage_regression_block_indexes`, `changed`, ordenado por extraction SHA. Debe
medir 640.933 bytes y hashear `4cd69...f8881`.

Cada changed delta tiene exactamente `added`, `extraction_sha256`, `modified`,
`receipt_sha256`, `removed`, `schema`, `treatment_contract_sha256`, `unchanged`;
receipt sobre el objeto sin receipt. `unchanged` proyecta exactamente
`baseline_ordinal:int`, `fingerprint_sha256:SHA`, `treatment_ordinal:int`.
`modified` proyecta los dos ordinals, dos fingerprints y overlap start/end.
`removed`/`added` proyectan ordinal, content/content SHA/fingerprint SHA,
source_block_start/end y los campos estructurales del fingerprint.

### Proyección exacta M2.8

Top-level exacto: `authority`, `authorization`, `checks`, `cost`, `dependencies`,
`failures`, `generation`, `instrument`, `loadable`, `manifests`, `population`,
`schema_version`, `source`, `status`. Se exige schema_version int 1, status `GO`,
loadable false, failures vacío, las 11 checks exactas bool true, coste cero,
population exacta congelada y:

```text
candidate_projection_sha256 = 4cd69...f8881
candidate_document_receipts_sha256 = 57e462...93a
coverage_gain_identities_sha256 = 6b0410...a675
```

Ambos seeds son JSON lógicamente idénticos. La proyección M2.7C recomputada debe
igualar el candidate projection hash; no basta confiar en el booleano.

Las 11 checks M2.8 exactas son `candidate_identity_new`, `contract_integrity`,
`external_calls_blocked`, `generation_identity_exact`, `global_invariants_exact`,
`output_schema_exact`, `population_exact`, `raw_token_intervals_exact`,
`row_mapping_and_identity_exact`, `source_exact`, `treatment_projection_exact`.
Population exacta:

```text
documents:1068, raw_blocks:333161, rows:31226, titled_rows:29413,
untitled_rows:1813, covered_blocks:333161, missing_blocks:0,
coverage_gain_blocks:100, coverage_regression_blocks:0,
changed_documents:27, unchanged_documents:1041,
delta_unchanged_rows:2529, delta_removed_rows:15, delta_added_rows:29,
delta_overlap_modified_rows:15, delta_pure_added_rows:14,
validation_failures:0
```

### Proyección y enlace exactos M2.9

Top-level exacto: `instrument`, `schema_version`, `status`, `loadable`, `authority`,
`candidate_evidence_mode`, `candidate_per_document_receipts_persisted`,
`dependencies`, `population`, `documents`,
`resolved_baseline_missing_identities`, `manifests`, `checks`, `failures`, `cost`,
`authorization`.

Se exige status `RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY`, loadable false, 15
checks bool true, failures vacío, coste cero, population exacta del gate M2.9 y los
seis manifests recomputados según su diseño. Cada uno de sus 1.068 document receipts
tiene schema cerrado M2.9 y receipt válido.

Population M2.9 exacta:

```text
documents:1068, raw_blocks:333161,
baseline_covered_blocks:333061, baseline_missing_blocks:100,
candidate_covered_blocks:333161, candidate_missing_blocks:0,
coverage_gain_blocks:100, coverage_regression_blocks:0,
changed_fingerprint_multiset_documents:27,
unchanged_fingerprint_multiset_documents:1041,
baseline_authorized_exclusion_identities:13,
baseline_unruled_loss_identities:87,
reconciled_baseline_missing_identities:100,
unresolved_baseline_missing_identities:0
```

El document receipt M2.9 tiene exactamente `schema`, `extraction_sha256`,
`raw_artifact_sha256`, `raw_blocks`, `baseline_covered_blocks`,
`baseline_missing_block_indexes`, `candidate_covered_blocks`,
`candidate_missing_block_indexes`, `coverage_gain_block_indexes`,
`coverage_regression_block_indexes`, `fingerprint_multiset_changed`,
`m29_document_receipt_sha256`. Receipt sobre el objeto sin su propio campo.
Los seis manifests M2.9 son SHA-256 de arrays JSON canónicos sin LF: documents
completos; `{extraction_sha256,m29_document_receipt_sha256}`; resolved completos;
`{extraction_sha256,source_block_index,m29_resolution_receipt_sha256}`;
`{extraction_sha256,source_block_index}` baseline missing; y el mismo array candidate
missing. Las 15 checks exactas son
`contract_integrity`, `m27c_seed_equivalence`, `candidate_seed_equivalence`,
`candidate_projection_bridge_exact`, `document_population_exact`,
`document_partitions_exact`, `compact_integrity_exact`,
`baseline_missing_identity_set_exact`, `candidate_missing_empty`,
`coverage_gain_exact`, `coverage_regression_empty`,
`resolved_identity_bindings_exact`, `manifest_integrity_exact`,
`output_schema_exact`, `zero_external_cost`.

Cada resolved identity M2.9 tiene exactamente `schema`, `extraction_sha256`,
`source_block_index`, `source_page_ordinal`, `page`, `kind`, `text_sha256`,
`ledger_receipt_sha256`, `baseline_disposition`, `baseline_rule_id`,
`candidate_disposition`, `m29_document_receipt_sha256`, `resolution_evidence`,
`m29_resolution_receipt_sha256`; receipt sobre el objeto sin su propio campo.
Cost M2.9 tiene exactamente `database_reads:0`, `database_writes:0`,
`model_calls:0`, `network_calls:0`, `raw_store_reads:0`, `chunk_executions:0`,
`manual_adjudications:0`, `additional_candidate_executions:0` y
`external_calls_blocked:true`, con tipos bool/int exactos.

Para los 18 documentos afectados, se exige:

```text
m29.raw_artifact_sha256 = m27c.raw_artifact_sha256
m29.raw_blocks = m27c.raw_blocks
m29.baseline_missing = m27c.baseline_missing
m29.candidate_missing = m27c.treatment_missing
m29.gain = m27c.gain
m29.regression = m27c.regression
m29.fingerprint_multiset_changed = m27c.changed
```

Así M2.9 aporta corroboración per-documento de cobertura y el anchor global
`6b0410...a675`; no aporta surface ni rows. Ambos seeds son lógicamente idénticos.

### Ciclo contractual exacto

El preregistro JSON congela exactamente 15 inputs: los 12 históricos de la tabla,
este diseño final, runner y tests. Su schema top-level exacto es:

```text
instrument, schema_version, status, scope, frozen_inputs, expected,
execution, authorization
```

`status=frozen_before_execution`; `frozen_inputs` tiene 15 roles exactos con
`path/sha256/format/use`; expected fija counts, projection, changed identity,
mapping 61→61, checks/failures/dependency roles; execution fija seeds `[1,2]` y dos
outputs; authorization mantiene execution false.

Los 15 roles exactos son `m27a_seed1`, `m27a_seed2`, `m27a_gate`, `m27c_seed1`,
`m27c_seed2`, `m27c_gate`, `m28_seed1`, `m28_seed2`, `m28_gate`, `m29_seed1`,
`m29_seed2`, `m29_gate`, `design`, `runner`, `runner_tests`. Los 17 dependencies del
output son esos mismos más `preregistration` y `execution_permit`; no se admite
ningún role adicional o ausente.

El permit JSON posterior tiene exactamente:

```text
instrument, schema_version, status, bindings, allowed_seeds,
additional_candidate_execution, authorization
```

Bindings exactos: preregistration/design/runner/tests. Autoriza dos ejecuciones
locales del ledger M2.10, no candidate/chunk execution. El output registra 17
dependencies: los 15 preregistrados más `preregistration` y `execution_permit`.

### Schema único de output

Todos los objetos son cerrados. Tipos `bool` e `int` son exactos; nunca se acepta la
equivalencia Python bool/int.

Envelope exacto: las 17 claves ya enumeradas en “Output cerrado y sin contenido”.
Valores fijos: instrument `s117_m210_candidate_live_alignment_v1`, schema_version int
1, status enum `CANDIDATE_LIVE_ALIGNMENT_GO_UPSTREAM_ONLY|NO_GO`, loadable false,
authority exacta y los tres flags de evidencia exactos. Dependencies tiene los 17
roles, cada valor SHA lowercase.

Document receipt exacto, con tipos:

```text
schema: s117_m210_candidate_document_alignment_v1
extraction_sha256: SHA
baseline_alignment_status: exact_whitespace_equivalent | unresolved
candidate_alignment_status: exact_whitespace_equivalent
candidate_surface_sha256: SHA
raw_surface_sha256: SHA
candidate_surface_equal_raw: bool true
candidate_missing_block_indexes: array[int] == []
coverage_gain_block_indexes: array[int]
coverage_regression_block_indexes: array[int] == []
fingerprint_multiset_changed: bool
candidate_mapping_mode: unchanged_fingerprint_multiset | frozen_changed_delta
m210_document_receipt_sha256: SHA del objeto sin receipt
```

Condicional: mapping unchanged iff changed=false; frozen delta iff changed=true.
Exactamente un documento baseline unresolved/changed/frozen-delta y debe ser
`8d128...45f6`; sus gains son `[630,631]`. Los otros 17 son baseline exact/unchanged.

Task receipt exacto, con tipos:

```text
schema: s117_m210_candidate_task_alignment_v1
local_row_id: UUID string
extraction_sha256: SHA
original_task_evidence_receipt_sha256: SHA
target_content_sha256: SHA
target_fingerprint_sha256: SHA
target_source_block_start: int
target_source_block_end: int
target_baseline_occurrences: int == 1
target_candidate_occurrences: int == 1
overlap_count: int == 1
overlap_fingerprints_sha256: SHA256(canonical array exacto, sin LF)
all_overlap_fingerprints_unique: bool true
candidate_membership_mode: unique_fingerprint_membership |
                           frozen_delta_unchanged_mapping
candidate_ordinal: null | int
changed_delta_disjoint_from_target: bool true
baseline_alignment_status: exact_whitespace_equivalent | unresolved
candidate_alignment_status: exact_whitespace_equivalent
m210_document_receipt_sha256: SHA enlazado
m210_task_receipt_sha256: SHA del objeto sin receipt
```

Condicional: solo task `acd5058d...` usa frozen mapping, candidate ordinal 61 y
baseline unresolved; los otros 20 usan unique membership, ordinal null y baseline
exact.

El array de overlap hasheado contiene objetos exactos
`{fingerprint_sha256,source_block_start,source_block_end}`, ordenados por
`(source_block_start,source_block_end,fingerprint_sha256)`. No contiene strings
sueltos, ordinals, row IDs ni receipts.

Los seis manifests son SHA-256 de estos arrays JSON canónicos sin LF:

```text
documents_sha256                  documents completos
document_receipts_sha256          [{extraction_sha256,m210_document_receipt_sha256}]
tasks_sha256                      tasks completos
task_receipts_sha256              [{local_row_id,m210_task_receipt_sha256}]
affected_document_identities_sha256 [{extraction_sha256}]
task_identities_sha256            [{local_row_id}]
```

Los dos últimos manifests son anchors preregistrados, no meras observaciones:

```text
affected_document_identities_sha256 =
  e96ad542c470f858616248429fd82aada4c1e2bd2b1ae02b1a75f6843128195a
task_identities_sha256 =
  fc92a3d2dc194716ff6d0b4263b3abc31d2cdc744db707cb5e0d996c905a2fcc
```

Cada document receipt M2.10 debe corresponder uno-a-uno a la misma extraction en
M2.7A, M2.7C y M2.9, y sus raw/surface/missing/gain/regression/changed fields deben
igualar las proyecciones normativas anteriores. Cada task receipt M2.10 debe
corresponder uno-a-uno al mismo `local_row_id` M2.7A y enlazar exactamente su
`extraction_sha256`, `receipt_sha256`, target content SHA, span y fingerprint. Estos
enlaces se validan aunque el output haya reconstruido todos sus receipts/manifests.

Checks exactos son los 17 ya enumerados. Failure enum exacto y orden de prioridad:

```text
contract_integrity_failure
m27a_seed_drift
m27c_seed_drift
m28_seed_drift
m29_seed_drift
m27a_receipt_failure
m27c_receipt_failure
m27a_m27c_baseline_bridge_failure
candidate_projection_bridge_failure
affected_population_drift
changed_intersection_drift
document_alignment_failure
target_membership_failure
overlap_membership_failure
changed_target_mapping_failure
manifest_integrity_failure
output_schema_failure
external_call_attempt
internal_failure
```

GO iff checks todas bool true, failures vacío, counts exactos y prereg/permit válidos.
NO_GO: documents/tasks vacíos, counts todos int 0, manifests/dependencies todos SHA
cero, 17 checks bool false y exactamente un failure sanitizado. Flags
`preregistration_frozen` y `execution_permit_valid` reflejan preflight, con
`permit=>prereg`; ningún path, excepción o contenido se serializa.

Cost exacto:

```text
model_calls:0, network_calls:0, database_reads:0, database_writes:0,
raw_store_reads:0, chunk_executions:0, candidate_executions:0,
embedding_generations:0, context_generations:0, manual_adjudications:0,
external_calls_blocked:true
```

Authorization exacto:

```text
preregistration_frozen:bool observed
execution_permit_valid:bool observed
M27A_repeat_gate:false
adjudication:false
raw_store_read:false
chunk_execution:false
additional_candidate_execution:false
database:false, network:false, models:false, embeddings:false
retrieval:false, rerank:false, synthesis:false
context_generation:false, load:false, serving:false, deploy:false
facts_moved_to_ok:int 0
M3:BLOCKED
```

La allowlist del runner queda limitada a stdlib (`hashlib`, `json`, `math`, `random`,
`socket`, `sys`, `pathlib`, `typing`, `uuid` solo para validar IDs). Se prohíben
`os`, subprocess, importlib, HTTP/DB/model SDKs, módulos de producción y runners
M27/M28/M29.
