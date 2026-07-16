# S117 — diseño v2 de `chunks_v3` por generaciones inmutables

## Decisión

`chunks_v3` será un shadow multigeneración rematerializado exclusivamente desde
raws sellados. `chunks_v2` no se altera, no se renombra y no se usa para inferir
linage. Una generación se carga como `loading`, se valida completa y solo
entonces puede publicarse atómicamente como `active`.

## Identidad de generación y fila

Namespaces UUIDv5 congelados:

- materialización: `3a4c744b-e79c-57db-98cd-9cb8ef55d4cf`
- fila: `2c1f6003-f8ce-5472-96c4-7c43899234b1`

Serialización canónica: JSON UTF-8, claves ordenadas, separadores `(',', ':')`,
`ensure_ascii=false`, sin valores implícitos.

El manifest de generación contiene, como mínimo:

- schema y versión del manifest;
- `provenance_contract` y versión;
- `chunker_sha256`;
- lista ordenada por `extraction_sha256` de
  `{extraction_sha256, raw_artifact_sha256}`;
- hashes de las implementaciones que transforman/validan la fila.

`manifest_sha256 = SHA256(canonical_json(manifest))` y
`materialization_id = UUIDv5(materialization_namespace, "v1\\0" + manifest_sha256)`.

Por fila se calcula `provenance_payload_sha256` sobre:

`{provenance_version, provenance_contract, raw_artifact_sha256,
chunker_sha256, content_sha256, source_block_start, source_block_end,
section_anchor, section_lineage}`.

`chunk_id = UUIDv5(row_namespace,
"v1\\0" + materialization_id + "\\0" + extraction_sha256 + "\\0" +
chunk_index + "\\0" + provenance_payload_sha256)`.

Así, otro raw, chunker, contrato, span, anchor, lineage, contenido o generación
produce otra identidad. La unicidad es `(materialization_id,
extraction_sha256, chunk_index)` y `(materialization_id, id)`.

## Tablas y atomicidad

### `chunk_materializations_v1`

Registro append-oriented con `id`, `manifest_sha256`, `manifest JSONB`,
`manifest_receipt_sha256`, `state` (`loading|validated|active|retired|failed`),
conteos esperados/observados y timestamps. Solo puede existir un `active`.

### `chunks_v3`

Superconjunto del contrato de retrieval de `chunks_v2`, con
`materialization_id` obligatorio y el envelope estructural. Las filas de una
generación `validated|active|retired` son inmutables mediante trigger. Durante
`loading` el loader solo usa INSERT; recuperación o borrado de una carga fallida
requiere una operación explícita sobre esa generación, nunca delete-then-insert
sobre una publicada.

### Publicación

Una función `SECURITY INVOKER`, ejecutable solo por `service_role`, toma advisory
lock, bloquea la materialización, valida estado/conteos/sets de duplicados y
cambia en una misma transacción el `active` anterior a `retired` y el candidato
a `active`. La publicación no cambia el flag/tabla que sirve el bot; ese switch
es un gate posterior y humano.

## `duplicate_of`

El dedup puede cruzar documentos del mismo producto. El FK compuesto
`(materialization_id, duplicate_of)` referencia
`chunks_v3(materialization_id, id)`, por lo que nunca cruza generaciones.

Antes de validar/publicar se exige globalmente:

- no self-reference;
- todo target existe en la misma generación;
- el target es canónico (`target.duplicate_of IS NULL`);
- cero ciclos y cero cadenas duplicate→duplicate.

El FK es `DEFERRABLE INITIALLY DEFERRED` para permitir bulk load ordenado; la
validación global sigue siendo obligatoria.

## Envelope estructural y alcance de la claim

Campos obligatorios: `raw_artifact_sha256`, `chunker_sha256`,
`content_sha256`, `provenance_payload_sha256`, `source_block_start/end`,
`section_anchor` y `section_lineage`.

Los spans de bloques prueban únicamente la procedencia del lineage. No se
presentan como offsets textuales exactos: al partir un bloque oversized varias
piezas comparten coordenada de bloque. La procedencia del contenido se prueba
re-ejecutando el chunker congelado sobre el raw y comparando la fila completa,
no mediante `content_sha256` aislado.

El recibo de generación sella el locator lógico del raw store, su manifest, los
hashes raw, el manifest de filas ordenadas y los hashes del materializador y
validador. Sin raw recuperable + receipt verificable la generación no puede
pasar a `validated`.

## Provenance de contexto y embedding

El enriquecimiento queda explícitamente separado del envelope estructural:

- `context_origin`: `generated_v3|legacy_v2_reuse|none`;
- `context_sha256`, `context_input_sha256`, `contextualizer_sha256`,
  `context_prompt_sha256`, `context_model`, límites efectivos;
- `embedding_origin`: `generated_v3|legacy_v2_reuse|none`;
- `embedding_input_sha256`, provider/model/input type/dimensión,
  `embedding_sha256` sobre float32 big-endian canónico;
- `donor_chunk_id` cuando exista reutilización.

Una donación v2 solo se admite si coinciden exactamente
`extraction_sha256`, content, section title/path, page, metadata enumerada,
context y `embedding_input_sha256`. Como v2 carece de receipts criptográficos
de modelo/vector, se etiqueta siempre `legacy_v2_reuse`: preserva el baseline,
pero no se presenta como embedding demostrado. Una fila `generated_v3` exige
receipt con raw/document-input hash, prompt, implementación, modelo y vector.

No se reutiliza contexto únicamente por PDF SHA. Debe coincidir el hash exacto
del documento efectivo enviado al contextualizer y todos sus límites.

## `document_id`

Para producción solo se resuelve por `documents.source_pdf_sha256` exacto y
único. No existe fallback por filename ni fail-open a `NULL`. Los raws
independientes de evaluación pueden materializarse localmente sin `document_id`,
pero no son elegibles para carga del corpus productivo.

## Seguridad

- RLS habilitado desde creación.
- Revocación explícita de tabla y de cada firma de función a `PUBLIC`, `anon` y
  `authenticated`.
- RPCs `SECURITY INVOKER`, `search_path=''`, objetos cualificados.
- `service_role` recibe el mínimo acceso de carga/lectura/publicación; no se
  confía en RLS frente a su `BYPASSRLS`.
- Checks `NOT NULL` para ordinal no negativo, estados, constantes, tipos JSONB y
  hashes. Schema drift produce error; no se oculta con `IF NOT EXISTS`.

## Índices

M0 crea PK, unicidad, FKs y B-tree/GIN requeridos. HNSW se difiere hasta después
de la carga validada. Su gate separado exige pgvector compatible, índice
`vector_cosine_ops` válido, filas `embedding IS NOT NULL AND duplicate_of IS
NULL`, `ANALYZE` y replay de planes/recall.

## Secuencia de gates

1. **M0a contrato local:** writer/validator/SQL y property tests, cero red.
2. **M0b SQL real:** aplicar + rollback en PostgreSQL con pgvector desechable;
   comprobar catálogo, RLS, grants, funciones y transiciones. Obligatorio antes
   de cualquier DB real; el entorno local actual no dispone de Docker/psql.
3. **M1 rematerialización local:** 1.068 raws + 12 independientes ya observados,
   más fixtures sintéticos/property tests sin ramas por SHA/filename.
4. **M2 diff read-only:** estimar donación exacta y coste residual.
5. **M2.5 snapshot enriquecido:** generación/reuso local con receipt y techo de
   coste explícito, antes de cualquier carga.
6. **M3 DB shadow:** autorización separada para esquema y carga; verificar
   manifest/conteos/inmutabilidad/rollback.
7. **M4a índice:** autorización y gate propios; luego `ANALYZE`.
8. **M4b funnel:** cohortes/umbrales congelados para retrieval→rerank→synthesis
   y regresión fact-level.
9. **M5 serving:** GO humano explícito, flag default-off, canary y rollback
   ensayado. Nunca automático por pasar métricas.

## No autorizado por M0a/M1

Supabase reads/writes, SQL remoto, modelos, embeddings, carga, HNSW, serving,
deploy, fact relabeling o afirmación de mejora en `% OK`.
