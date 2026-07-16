# S117 M2.7 — auditoría upstream, contrato común de retrieval y presupuesto fresco v1

## Alcance y autoridad

M2.7 consume únicamente los artefactos congelados de M2.6 y los raw records ya
usados por S117. No accede a `.env`, red, modelos, base de datos ni payloads
vectoriales. No aplica migraciones, no carga datos y no sirve `chunks_v3`.

El único GO posible es `LOCAL_READINESS_GO`. M3, generación, schema, load,
HNSW, serving y cualquier claim sobre facts OK continúan bloqueados.

Fuentes autoritativas:

- población y ejes live/policy/identity: M2.6 seed congelado;
- contenido y provenance v3: raw store + materializador/chunker congelados;
- donors legacy: exclusivamente el snapshot fuente M2, filas base;
- binding projected: solo diagnóstico; nunca se trata como live;
- costes: contrato runtime congelado y precios oficiales versionados, sin
  asumir créditos gratuitos ni cache hits no observados.

## A. Auditoría documental upstream

### Poblaciones

La aceptación se decide sobre las 8.493 filas `live_exact_active + eligible`.
Dentro de ellas se auditan exhaustivamente:

- 461 `no_content_donor`;
- 129 `no_structural_donor`;
- 0 `multiple_structural_donors`.

Como control de escalabilidad, se reportan aparte —sin autoridad live— las
1.240 filas projected elegibles: 984 + 238 + 18. Las 679 live y 1.881 projected
con donor legacy marcado duplicate se conservan como exclusión histórica; no
son candidatas a reuse ni desencadenan un fix de v3.

### Evidencia por fila

Cada fila debe emitir un receipt que contenga:

- identidad local, extraction SHA, source span y provenance payload SHA;
- terminal live/projected y clase de policy;
- conteo de donors base del mismo extraction SHA;
- clasificación cerrada y métricas que la justifican;
- manifest determinista, sin snippets ni metadata fabricante/modelo en la
  decisión.

Para `no_structural_donor`, el contenido debe tener al menos un donor exacto y
se reporta el conjunto cerrado de campos divergentes entre
`section_title, section_path, page_number, is_flow_diagram, has_diagram,
confidence_f32`. La clasificación es `structure_only_delta`.

Para `no_content_donor`, se tokeniza con NFKC + casefold y whitespace
colapsado, preservando números y puntuación técnica. Se evalúa contra los
donors base ordenados por `chunk_index`:

1. `normalized_single_donor_exact`: igualdad normalizada con un donor;
2. `document_sequence_resegmentation`: la secuencia completa de tokens local
   aparece contigua en la secuencia legacy del documento;
3. `near_resegmentation`: cobertura de shingles contiguos de 5 tokens >= 0,98;
4. `unresolved_content_delta`: resto.

Los thresholds se congelan antes de ejecutar y se prueban con positivos,
negativos y mutaciones de metadata. `near_resegmentation` es evidencia de
cambio de frontera, no prueba de fidelidad semántica. Todo
`unresolved_content_delta` live queda en adjudicación y bloquea un claim de
fidelidad; el instrumento nunca aplica fixes automáticamente.

### Gate documental

El gate exige:

- población y taxonomías exactas/fail-closed;
- todos los source/provenance receipts internamente válidos;
- 590/590 live clasificadas;
- projected separado y no autorizante;
- muestra determinista por categoría y decil de longitud para revisión;
- cero claims de pérdida o mejora basados solo en la ausencia de donor legacy.

## B. Contrato común vector/FTS

M2.7 produce una especificación SQL `NO_GO_FOR_DB`, no una migración aplicable.
La especificación será parseable y tendrá tests estáticos, pero la ausencia de
PostgreSQL+pgvector local deja la ejecución/planificación para un gate posterior
en una base desechable.

### Estado autoritativo

`chunks_v3` necesita:

- `retrieval_policy_class` cerrado a
  `eligible|register_only|unsupported_language|duplicate`;
- `retrieval_eligible` generado y almacenado desde la clase;
- constraint que haga equivalente `duplicate` y `duplicate_of IS NOT NULL`.

### Única frontera común

Una view `security_invoker` no expuesta públicamente será la única fuente de
ambas RPC. Debe contener exactamente:

```sql
FROM public.chunks_v3 AS c
JOIN public.chunk_materializations_v1 AS m
  ON m.id = c.materialization_id AND m.state = 'active'
JOIN public.documents AS d
  ON d.id = c.document_id
 AND d.source_pdf_sha256 = c.extraction_sha256
 AND d.status = 'active'
WHERE c.retrieval_eligible
  AND c.duplicate_of IS NULL
```

Vector añade embedding no nulo, receipt/origin autorizado, threshold, filtros
tipados y orden por distancia. FTS añade `search_vector @@ query`, filtros
tipados y orden por rank. Los filtros se ejecutan dentro de SQL antes del
`LIMIT`; ambas RPC limitan explícitamente el máximo solicitado.

No se permite `target_materialization_id` en las RPC servidas: no puede saltar
el estado active. La inspección de una generación validated debe usar un
testbed privado separado.

### Índices y seguridad

- GIN para `search_vector` con predicado parcial estático de eligibility;
- la definición HNSW queda declarada pero diferida hasta disponer de embeddings
  y poder medir EXPLAIN/recall; si se crea, solo usa predicados estáticos;
- no se indexan estados de tablas relacionadas dentro de un partial index;
- view y RPC son `security_invoker`, `search_path=''`;
- `PUBLIC`, `anon` y `authenticated` no reciben acceso;
- `service_role` recibe solo `SELECT` en la view y `EXECUTE` en las RPC;
- grants y RLS se tratan como capas separadas.

Referencias verificadas el 2026-07-14:

- https://supabase.com/docs/guides/ai/semantic-search
- https://supabase.com/docs/guides/database/full-text-search
- https://supabase.com/docs/guides/ai/vector-indexes
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically

## C. Presupuesto de regeneración fresca

La población es exactamente 8.493 filas live+eligible. Reuse = 0.

El runner calcula de forma determinista:

- 8.493 llamadas de contexto y documentos distintos;
- caracteres exactos de documento e instrucción por request;
- proxy token `ceil(chars/4)`, separado en cache write, cache read e input
  uncached;
- escenario conservador sin cache y escenario proxy con cache;
- output ceiling exacto: `8.493 * 200` tokens;
- 8.493 inputs de embedding;
- límites de caracteres/tokens para `context + content` y batches exactos según
  `_BATCH_SIZE=128` y `_BATCH_CHAR_BUDGET=320000`.

El coste USD se etiqueta `planning_proxy`, no factura exacta. Usa:

- Haiku 4.5: input $1/MTok, cache write 5m $1,25/MTok, cache read
  $0,10/MTok, output $5/MTok;
- Voyage 4 Large: $0,12/MTok después del free tier.

No se asume free tier Voyage disponible. El cache proxy no afirma hits: Haiku
4.5 requiere un mínimo cacheable y el tokenizer exacto/usage receipt solo existe
al ejecutar. Se publica un techo conservador sin cache y una estimación con
cache, junto con todas las fórmulas.

Fuentes de precio verificadas el 2026-07-14:

- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- https://docs.voyageai.com/docs/pricing

## Determinismo, revisión y stopping rules

- seeds 1 y 2 solo alteran el orden de inputs y deben producir bytes idénticos;
- toda taxonomía rechaza terminals desconocidos;
- metadata de fabricante/modelo nunca decide la clase;
- un pre-review adversarial congela diseño, runner, tests y prereg;
- un post-review recalcula manifests, counts, fórmulas y SQL contract;
- cualquier drift, unresolved live sin adjudicación o divergencia seeded es
  `LOCAL_READINESS_NO_GO`;
- ningún resultado M2.7 autoriza modelos, DB, migración, load o serving.
