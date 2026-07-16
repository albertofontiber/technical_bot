# S117 M2.6 — cierre de manifests, binding evidence e input embedding v4

Este addendum supersede M2.6 v3 solo en los tres puntos siguientes.

## Dos familias de manifests de cohorte

El freezer no equipara receipts de esquemas distintos.

### `legacy_replay_manifest`

Reproduce byte a byte las fórmulas y el orden del analyzer M2 congelado:

- contexto: `{id, context_sha256, context_input_sha256}`;
- embedding: `{id, embedding_input_sha256, embedding_input_chars}`.

Genera por separado baseline y proyección, y exige igualdad exacta con los
cuatro hashes ya congelados en M2 y M2.5. Esta familia demuestra que el replay
reconstruyó exactamente las membresías históricas.

### `membership_pair_manifest`

Después del replay exacto se crea un receipt nuevo y explícitamente derivado:
`{local_row_id, donor_chunk_id}`. No se presenta como previamente congelado.

Sobre estos pairs se exige:

- unicidad de `local_row_id` en cada set;
- baseline 2.623, projected 8.061 y diferencia 5.438;
- baseline subconjunto propio de projected;
- baseline y new disjuntos;
- unión baseline+new exactamente projected;
- manifest canónico determinista por set.

## Discovery estructural y binding evidence separados

El discovery nunca consulta documentos ni aliases. Su taxonomía queda:

1. `no_content_donor`;
2. `no_structural_donor`;
3. `multiple_structural_donors`;
4. `unique_donor_marked_duplicate`;
5. `independent_unique_structural_donor`.

Solo después de obtener un donor único se calcula un receipt ortogonal
`donor_binding_evidence_status`:

1. `structural_donor_not_unique`;
2. `live_exact_document_match`;
3. `projected_observed_document_match`;
4. `expected_document_binding_unavailable`;
5. `donor_document_binding_mismatch`.

Fuentes permitidas del expected ID:

- live: exclusivamente `documents` del snapshot fuente, por SHA canónico exacto
  y único;
- projected: exclusivamente el binding receipt fail-closed M2.5, conservando su
  etiqueta analítica;
- unresolved: ninguna; nunca se infiere expected ID desde el donor.

Está prohibido leer documentos/aliases del snapshot derivado para decidir
binding live o para construir el expected ID. `load_binding_status` continúa
siendo la única autoridad de carga. Un projected match aporta evidencia, no
autorización.

## Dependencia contexto → embedding

El input de embedding es `context + content`. Por tanto:

- contexto autorizable = base live/policy/identity/binding +
  `context_evidence_compatible`;
- embedding autorizable = la condición anterior +
  `embedding_evidence_compatible`.

Nunca se autoriza un embedding cuyo contexto no esté autorizado. Con el
snapshot actual ambos conteos siguen preregistrados a cero.
