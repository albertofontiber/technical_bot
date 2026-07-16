# S117 M2.6 — contrato local de elegibilidad y validación independiente v2

Este documento supersede íntegramente M2.6 v1 y, para decisiones de reuse,
supersede la cláusula de `s117_chunks_v3_persistence_design_v2.md` que permitía
`legacy_v2_reuse` sin provenance criptográfica completa.

## Alcance y separación de decisiones

M2.6 es local, read-only y no autorizante. Reconcilia las 31.212 filas en tres
ejes ortogonales:

1. realidad de binding cargable;
2. policy estática de retrieval;
3. evidencia independiente de contexto y embedding.

No lee DB, `.env` ni payloads vectoriales, no llama modelos y no modifica
schema, carga o serving. M3 permanece bloqueado.

## Eje A — binding real, no proyectado

Los aliases de M2.5 solo prueban una hipótesis analítica. No existen en
`documents` y no cuentan como binding live.

La foto congelada se etiqueta sin ambigüedad:

- `live_exact_active`: SHA raw canónico = `documents.source_pdf_sha256`, único,
  status active;
- `live_exact_nonactive`: igualdad canónica exacta, documento no active;
- `projected_backfill_candidate`: binding M2.5 seguro pero el documento live
  conserva `backfill:<sha>`;
- `projected_backfill_nonactive`: igual, con documento no active;
- `binding_unresolved`: cualquier otro terminal fail-closed.

Conteos observados que el runner debe recomputar desde el snapshot fuente, no
desde el snapshot con aliases:

- 10.219 filas `live_exact_active`;
- 519 `live_exact_nonactive`;
- 19.572 `projected_backfill_candidate`;
- 4 `projected_backfill_nonactive`;
- 898 `binding_unresolved`.

Solo las dos primeras clases son hoy `load_binding_valid`. M3 no puede usar las
19.572 proyectadas hasta que una remediación documental versionada demuestre en
DB la igualdad canónica real. No se insertan IDs sintéticos ni se baja el gate.

## Eje B — policy autoritativa y versionada

No se persisten dos campos editables `eligible + reason`. La fuente única es un
enum cerrado `retrieval_policy_class`:

- `eligible`;
- `register_only`;
- `unsupported_language`;
- `duplicate`.

Precedencia determinista por fila, después de finalizar dedup:

1. profile documental `register_only`;
2. chunk en idioma no indexable;
3. `duplicate_of IS NOT NULL`;
4. `eligible`.

`retrieval_eligible` será una columna generated/stored derivada exclusivamente
de `retrieval_policy_class='eligible'`. Checks adicionales exigen:

- `eligible -> duplicate_of IS NULL`;
- `duplicate -> duplicate_of IS NOT NULL`;
- contexto, embedding y `search_vector` nulos para exclusions de policy;
- dedup cerrado antes de calcular receipts y antes de publicar.

El manifest de materialización debe incluir:

- SHA-256 del contrato de policy y de su implementación;
- profile/verdict y language efectivos;
- `retrieval_policy_class` por fila;
- receipt por fila sobre extracción, ordinal, clase, language, duplicate target
  y policy-contract SHA;
- manifest y conteos exactos por clase.

La DB no intenta reimplementar el detector Python: valida el manifest sellado,
la coherencia enum/duplicate/enrichment y los conteos preregistrados.

## Eje C — returnability efectiva

La policy estática no congela estados live. El predicado productivo común y
exacto de ambos RPCs será, sin bypass:

```sql
FROM public.chunks_v3 AS c
JOIN public.chunk_materializations_v1 AS m
  ON m.id = c.materialization_id
 AND m.state = 'active'
JOIN public.documents AS d
  ON d.id = c.document_id
 AND d.source_pdf_sha256 = c.extraction_sha256
 AND d.status = 'active'
WHERE c.retrieval_eligible
  AND c.duplicate_of IS NULL
```

Vector añade exclusivamente embedding autorizado/no nulo, threshold y filtros;
FTS añade `search_vector IS NOT NULL`, tsquery y filtros. Un parámetro explícito
de materialización no puede saltarse `m.state='active'` en los RPCs productivos;
un futuro shadow necesita otra función interna, otra firma y privilegios
estrechos.

Los índices parciales GIN/HNSW solo cubren policy estática y canonicalidad:
estado de materialización/documento se comprueba live porque cruza tablas. El
SQL real, catálogo y `EXPLAIN` en PostgreSQL+pgvector desechable son un gate
posterior, no una claim de M2.6.

## Universo independiente de donor

El runner enumera desde cero las 31.212 filas locales y los 25.090 base chunks
legacy. No llama al selector de candidatos M2 ni usa metadata de fabricante,
producto, categoría, distribuidor, protocolo, tipo documental o language para
encontrar donors.

Para cada target reconstruye candidatos mediante:

1. `extraction_sha256` exacto;
2. contenido byte a byte;
3. estructura congelada: section title/path, página, flags de diagrama y
   confidence float32.

Después clasifica target y donor. La cohorte M2.5 de 5.438 filas se conserva
solo como una subcohorte de reconciliación: debe aparecer íntegra en el universo
independiente, pero no define sus miembros ni su autorización.

Tests metamórficos alteran toda la metadata prohibida en target y donor y deben
conservar byte-idénticos clasificación, IDs candidatos y receipts.

## Taxonomía cerrada de identidad

Precedencia por target sobre las 31.212 filas:

1. `target_not_live_load_bound`;
2. `target_document_nonactive`;
3. `target_policy_excluded`;
4. `target_marked_duplicate`;
5. `no_content_donor`;
6. `no_structural_donor`;
7. `multiple_structural_donors`;
8. `donor_document_binding_mismatch`;
9. `donor_marked_duplicate`;
10. `independent_unique_structural_donor`.

Cada fila cae exactamente en un terminal. Un estado fuera de la taxonomía es
fallo interno. Para la subcohorte 5.438 se publica el mismo desglose y se exige
cero policy-excluded targets.

## Taxonomía cerrada de contexto

Solo se evalúa enriquecimiento tras identidad independiente limpia:

1. `identity_not_authorizable`;
2. `context_missing_or_empty`;
3. `context_target_donor_input_mismatch`;
4. `context_output_receipt_unavailable`;
5. `context_generation_receipt_unavailable`;
6. `context_authorized`.

Autorizar exige texto, output SHA, input exacto target↔donor, implementación,
prompt, modelo y límites efectivos ligados al donor. El snapshot no contiene
esa provenance. El prereg congela `context_authorized=0`; cualquier valor mayor
es NO-GO por contaminación del instrumento. Decisión operativa: regenerar.

## Taxonomía cerrada de embedding

También se evalúa después de identidad limpia:

1. `identity_not_authorizable`;
2. `embedding_missing`;
3. `embedding_dimensions_mismatch`;
4. `embedding_target_donor_input_mismatch`;
5. `embedding_model_receipt_unavailable`;
6. `embedding_vector_receipt_unavailable`;
7. `embedding_authorized`.

Autorizar exige input SHA target↔donor, provider/model/input type, dimensión,
SHA float32 canónico y receipt que pruebe el mismo modelo usado por queries.
El snapshot declara payloads cero, `vector_sha256=null` y model receipt null.
El prereg congela `embedding_authorized=0`; cualquier valor mayor es NO-GO.
Decisión operativa: regenerar.

## Salud del gate frente a autorización

El único GO agregado es `contract_integrity=GO`, que significa taxonomías
cerradas, manifests deterministas y ausencia de policy leakage. La salida no
usa `context_reuse: GO` ni `embedding_reuse: GO`.

Publica exclusivamente conteos por fila:

- `authorized_context_rows` — esperado exactamente 0;
- `authorized_embedding_rows` — esperado exactamente 0;
- `regenerate_context_rows`;
- `regenerate_embedding_rows`.

Una ejecución correcta puede y, con los inputs actuales, debe tener integridad
GO y autorizaciones cero. Esto no es una ausencia de resultado: descarta reuse
no demostrable y fija el workload real sin gastar modelos.

## Gate de ejecución

- prereg antes del runner final;
- seeds `PYTHONHASHSEED=1,2`, outputs byte-idénticos;
- M2.5 y baseline primaria invariantes;
- 31.212 targets y 25.090 donors base exactos;
- manifest por eje load/policy/identity/context/embedding;
- subcohorte protegida de 5.438 reconciliada pero no usada como selector;
- `authorized_context_rows=0` y `authorized_embedding_rows=0`;
- cero DB/red/modelos/vectores;
- suite local completa y revisión adversarial antes/después.

M2.6 no autoriza remediación documental, migración, carga, HNSW, serving,
deploy ni relabel de facts. Solo congela el contrato y el workload seguro.
