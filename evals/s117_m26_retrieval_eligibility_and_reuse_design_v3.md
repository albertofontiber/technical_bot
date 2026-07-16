# S117 M2.6 — cierre de ortogonalidad y cohortes v3

Este addendum supersede M2.6 v2 donde exista incompatibilidad. Mantiene los
conteos de binding, la policy autoritativa, el predicado SQL y la prohibición de
reuse sin provenance completa.

## Cuatro ejes realmente ortogonales

Cada una de las 31.212 filas recibe cuatro clasificaciones independientes. Una
clasificación nunca corta la ejecución de otra.

### 1. `load_binding_status`

- `live_exact_active` — 10.219;
- `live_exact_nonactive` — 519;
- `projected_backfill_candidate` — 19.572;
- `projected_backfill_nonactive` — 4;
- `binding_unresolved` — 898.

Solo las dos clases live son hoy cargables. Las projected se analizan, pero no
se autorizan como load/reuse.

### 2. `retrieval_policy_class`

Se conserva el enum autoritativo `eligible|register_only|unsupported_language|
duplicate`, calculado después de dedup y comprometido por receipts.

Toda fila cuya clase sea distinta de `eligible`, incluida `duplicate`, debe
tener `context`, `embedding` y `search_vector` nulos en la materialización
futura. El booleano generated no es una segunda fuente de verdad.

### 3. `structural_identity_status`

Se calcula para todas las filas, incluidas projected, nonactive, policy-excluded
y duplicate. No consulta binding/policy del target y no usa metadata prohibida.

Precedencia cerrada:

1. `no_content_donor`;
2. `no_structural_donor`;
3. `multiple_structural_donors`;
4. `unique_donor_document_binding_mismatch`;
5. `unique_donor_marked_duplicate`;
6. `independent_unique_structural_donor`.

La estructura usa únicamente extracción exacta, contenido byte a byte,
section title/path, página, flags de diagrama y confidence float32. Perturbar
manufacturer, product, category, distributor, protocol, doc_type o language no
puede cambiar status, candidate IDs ni receipt.

### 4. Evidencia de enriquecimiento

Contexto y embedding se evalúan sobre el resultado estructural sin consultar
si el target es live/projected. La autorización final, separada, será la
conjunción de los cuatro ejes.

## Cohortes protegidas por diferencia exacta de sets

Un freezer de cohortes reconstruye el selector M2 solo para definir la historia
que se debe reconciliar; nunca alimenta el selector independiente.

Genera receipts canónicos por `(local_row_id, donor_chunk_id)` y tres sets:

- `baseline_strict`: 2.623 filas sobre snapshot M2 fuente;
- `projected_strict`: 8.061 filas sobre snapshot M2.5 derivado;
- `new_m25_strict = projected_strict - baseline_strict`: 5.438 filas.

El freezer exige:

- manifest de contexto/embedding idéntico a los receipts ya congelados de M2 y
  M2.5;
- `baseline_strict ⊂ projected_strict` sin filas perdidas;
- intersección baseline/new vacía;
- unión baseline/new exactamente projected;
- counts 2.623 + 5.438 = 8.061.

El auditor independiente enumera las 31.212 filas desde cero y luego reporta,
sin usar esos sets para buscar donors, los resultados de identidad/evidencia en
las tres subcohortes.

## Contexto — availability, compatibility, input

Taxonomía cerrada:

1. `structural_identity_not_unique`;
2. `context_missing_or_empty`;
3. `context_generation_receipt_unavailable`;
4. `context_output_receipt_unavailable`;
5. `context_contract_mismatch`;
6. `context_target_donor_input_mismatch`;
7. `context_evidence_compatible`.

Primero se prueba que existen receipts; solo entonces se compara contrato y,
por último, igualdad del input target↔donor. Un receipt declarado cuyo hash no
reconstruye es fallo interno global, no un terminal recuperable.

El snapshot actual no incluye receipts históricos completos. El prereg fija
`authorized_context_rows=0`.

## Embedding — availability, compatibility, input

Taxonomía cerrada:

1. `structural_identity_not_unique`;
2. `embedding_missing`;
3. `embedding_model_receipt_unavailable`;
4. `embedding_vector_receipt_unavailable`;
5. `embedding_query_contract_mismatch`;
6. `embedding_target_donor_input_mismatch`;
7. `embedding_evidence_compatible`.

El contract mismatch cubre provider, modelo, input type, dimensión y límites.
La igualdad del input se comprueba después de establecer disponibilidad y
compatibilidad. Un model/vector receipt presente pero criptográficamente
inconsistente aborta el gate.

El snapshot actual declara payload/model receipt ausentes. El prereg fija
`authorized_embedding_rows=0`.

## Autorización fila a fila

Ningún status agregado concede reuse. Para cada fila:

`base_authorizable = load_binding_status == live_exact_active AND
retrieval_policy_class == eligible AND structural_identity_status ==
independent_unique_structural_donor`.

Después:

- contexto autorizable = base + `context_evidence_compatible`;
- embedding autorizable = base + `embedding_evidence_compatible`.

Las filas projected pueden resultar estructuralmente limpias y cuantificar
trabajo futuro, pero `base_authorizable=false` hasta remediación documental
live. Las filas live tampoco se autorizan sin receipts de enriquecimiento.

## Semántica del resultado

- `contract_integrity=GO` exige cuatro taxonomías cerradas, manifests exactos,
  tests metamórficos y cohortes reconciliadas;
- `authorized_context_rows` debe ser exactamente 0;
- `authorized_embedding_rows` debe ser exactamente 0;
- cualquier autorización positiva con los inputs congelados da NO_GO;
- M3 sigue BLOCKED.

El predicado SQL común exacto y el gate PostgreSQL+pgvector posterior de v2 se
mantienen sin cambios.
