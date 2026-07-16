# S131 — enmienda v2 de binding, aislamiento y partición experimental

Contrato normativo compuesto por:

- `evals/s131_chunks_v3_shadow_binding_design_v1.md`, SHA-256
  `85d1127771d7d958d3971e3a26d694bb72a6a1107dd95cf762c254e4fa665aad`;
- las sustituciones completas de las secciones 6 a 10 definidas aquí.

V2 conserva el objetivo, evidencia, deuda sustituida, namespaces y taxonomía de
V1. No autoriza DB, carga, modelos, embeddings, serving, deploy, facts OK ni v4.

## Sustitución de V1.6 — manifest exacto de binding y partición

El generador local ejecuta dos procesos independientes y exige payload canónico
byte-idéntico. No usa aleatoriedad; “dos procesos” es una prueba de
determinismo, no dos muestras estadísticas.

Una entrada por extracción, ordenada por `extraction_sha256`, contiene
exclusivamente:

1. `materialization_id`;
2. `extraction_sha256`;
3. `raw_artifact_sha256`;
4. `document_id` nullable;
5. `binding_status`;
6. `binding_authority`;
7. `document_status_at_snapshot` nullable;
8. `source_pdf_identity` nullable;
9. `source_pdf_identity_status`;
10. `evaluation_partition` (`development`, `heldout_s130`);
11. `snapshot_binding_ledger_sha256`;
12. `heldout_manifest_sha256`;
13. `binding_receipt_sha256`.

`binding_receipt_sha256` compromete los campos 1–12. El manifest global
compromete las 1.068 entradas, los conteos por estado/partición, el descriptor
ordenado `(extraction_sha256, raw_artifact_sha256)` de la generación, el ledger
snapshot
`1eec4001dfee4eb2228e92bb8f71018e02dc84e738b1973bce2aaabf5b97eaeb`
y el embargo S130
`654ee7c211b2d908912e5600513fbc293ba9cda9bb6a9482e1266e378fd099b8`.

El valor exacto de `source_pdf_identity`, no solo su status, se toma de la fila
documental congelada. Para unbound es `null` y status `unknown`. Un documento
bound con identidad vacía falla cerrado.

Tabla de verdad normativa:

| `binding_status` | documento | status doc | identidad PDF | authority | retrieval binding |
|---|---|---|---|---|---|
| `bound_active_physical_sha_verified` | no nulo | `active` | SHA físico igual a `extraction_sha256` | `m25_exact_active_and_snapshot_reciprocal` | sí |
| `bound_active_legacy_snapshot_only` | no nulo | `active` | valor exacto congelado, sin elevarlo a extracción/PDF | `legacy_snapshot_reciprocal_shadow_only` | sí |
| `bound_nonactive_legacy_snapshot` | no nulo | `needs_review` o `superseded` | valor exacto congelado | `legacy_snapshot_reciprocal_shadow_only` | no |
| `unbound_snapshot_empty_document` | `null` | `null` | `null` | `snapshot_empty_document_shadow_only` | no |
| `unbound_absent_from_snapshot` | `null` | `null` | `null` | `absent_from_snapshot_shadow_only` | no |

Ninguna combinación adicional es válida. Para cada chunk, `extraction_sha256`
y `raw_artifact_sha256` deben coincidir con el binding y con el descriptor de la
generación. Para cada bound, la base objetivo debe contener el mismo
`document_id`, `status` y `source_pdf_sha256` congelados. Cualquier deriva exacta
bloquea; una clase legacy nunca se promociona por inferencia.

Partición cerrada:

| Partición | Extracciones bound-active | Baseline filas | Candidato filas | changed docs |
|---|---:|---:|---:|---:|
| `development` | 932 | 26.588 | 26.601 | 24 |
| `heldout_s130` | 70 | 3.372 | 3.373 | 3 |
| **combinado comparable** | **1.002** | **29.960** | **29.974** | **27** |

Los totales 31.212/31.226 pertenecen a las generaciones completas de 1.068
extracciones y son solo controles globales; nunca son denominador del A/B.

## Sustitución de V1.7 — SQL v2 cerrado y shadow-only

La migración correctiva nueva compone sobre S117 solo en PostgreSQL desechable.
Debe dejar inutilizables para API normal los grants y RPCs heredados antes de
crear cualquier ruta shadow:

1. revocar a `service_role` todo `SELECT`/`INSERT` sobre
   `chunks_v3`, `chunk_materializations_v1` y bindings;
2. revocar a `service_role` `EXECUTE` sobre las firmas S117
   `match_chunks_v3`, `search_chunks_text_v3`, publish, validate y discard;
3. dropear o sustituir las dos RPC de retrieval S117 para que ninguna seleccione
   por defecto una generación `state='active'`;
4. no usar `active` para el shadow: las generaciones consultables permanecen
   `validated` y nunca pasan por la RPC S117 de publish;
5. crear roles `NOLOGIN` separados:
   `technical_bot_chunks_v3_shadow_loader` y
   `technical_bot_chunks_v3_shadow_runner`; no concederlos a roles de API;
6. loader: solo insert de generación/binding/chunks y ejecución de validate o
   discard shadow; runner: solo `SELECT` de la vista y `EXECUTE` de RPCs shadow;
7. ninguna tabla base es accesible directamente por el runner.

`chunk_document_bindings_v1` usa PK
`(materialization_id, extraction_sha256)`, FK a generación y FK nullable a
documento. Contiene todos los campos por extracción del manifest, incluida
`evaluation_partition`; los hashes globales de ledger y embargo también se
persisten para enforcement. Checks y RPC de sellado imponen la tabla de verdad
V2.6, conteos 405/597/8/8/50 y una fila de binding por cada una de las 1.068
extracciones.

`chunks_v3.document_id` pasa a nullable, pero toda fila requiere exactamente un
binding. La RPC de sellado exige simultáneamente:

- 1.068 bindings y el `expected_chunks` exacto del manifest del brazo:
  31.212 para baseline o 31.226 para candidato;
- manifests de generación, rows y bindings exactos;
- `c.document_id IS NOT DISTINCT FROM b.document_id`;
- `c.raw_artifact_sha256 = b.raw_artifact_sha256`;
- cero chunks sin binding y cero bindings sin chunks;
- conteos por status y partición exactos;
- documento/status/identidad PDF exactos para todo bound;
- cero bound no activo o unbound marcado como retrieval.

Bindings y chunks son append-only después de validar. Toda mutación de status,
authority, identidad, documento, raw hash, partición o receipt falla.

La vista `chunks_v3_shadow_retrieval_eligible_v2` es
`WITH (security_invoker=true)` y fija literalmente esta conjunción:

```text
materialization.state = 'validated'
AND binding_status IN (
  'bound_active_physical_sha_verified',
  'bound_active_legacy_snapshot_only'
)
AND binding.document_status_at_snapshot = 'active'
AND documents.status = 'active'
AND documents.source_pdf_sha256 IS NOT DISTINCT FROM binding.source_pdf_identity
AND chunks.document_id IS NOT DISTINCT FROM binding.document_id
AND chunks.raw_artifact_sha256 = binding.raw_artifact_sha256
AND chunks.retrieval_policy_class = 'eligible'
AND chunks.retrieval_policy_receipt_sha256 IS NOT NULL
AND chunks.duplicate_of IS NULL
```

Las RPC shadow exigen `materialization_id` y `evaluation_partition` explícitos,
validan ambos contra un manifest experimental congelado y solo son ejecutables
por `technical_bot_chunks_v3_shadow_runner`. No existe default, fallback a
`active`, override para `service_role` ni grant a `PUBLIC`, `anon`,
`authenticated` o `service_role`.

Baseline y candidato son dos materializaciones `validated` distintas. Cada una
tiene su propio manifest de binding —el `materialization_id` forma parte del
recibo— aunque comparten el mismo universo de 1.068 extracciones, raw descriptors
y particiones. Ninguna se publica como `active`.

## Sustitución de V1.8 — M0b y pruebas negativas

M0b sigue requiriendo autorización separada y PostgreSQL+pgvector desechable.
Tras fixture Supabase, S117 antecedente y corrección S131, debe probar:

1. catálogo, tipos, checks, FKs, índices, triggers, RLS, owners y `search_path`;
2. las cinco filas válidas de la tabla de verdad;
3. rechazo de toda combinación cruzada status↔document nullability↔authority↔
   document status↔PDF status↔retrieval;
4. rechazo de raw hash, PDF identity, document status, counts o manifests
   divergentes;
5. rechazo de chunk sin binding, binding sin chunks y documento denormalizado
   distinto;
6. inmutabilidad después de `validated` y carreras validate/discard;
7. `service_role` y roles API no pueden leer, insertar, publicar ni ejecutar
   retrieval v3;
8. el runner no puede leer tablas base ni otra materialización/partición;
9. las RPC S117 no sirven ninguna generación v3;
10. rollback completo sin roles, funciones, vistas, tablas, policies o grants
    residuales S131.

No se instala runtime ni se usa Railway bajo esta autorización.

## Sustitución de V1.9 — A/B lexical y held-out de una sola apertura

Fase A usa solo `development`: 932 extracciones, 26.588/26.601 filas. Antes de
ejecutar se congelan hashes de:

- manifests de ambas ramas y partición;
- queries y respuestas gold de desarrollo;
- normalización, FTS/configuración lingüística y filtros;
- top-k, tie-break determinista y política de duplicados;
- métricas, denominadores y umbrales de no-regresión/mejora;
- código, tests, runtime y outputs exclusivos.

No hay modelos, embeddings, rerank ni synthesis. El resultado solo acredita la
etapa lexical medida.

Solo después de cerrar Fase A se congela el artefacto candidato ganador y todos
los elementos anteriores. Fase B abre una única vez `heldout_s130`: 70
extracciones, 3.372/3.373 filas. Tras su resultado no se adapta regla, umbral,
query, filtro, chunker ni proyección; cualquier iteración futura crea un diseño
nuevo y otro held-out aún no observado.

El cálculo de identidad y cardinalidad del held-out no es inspección semántica:
no serializa texto, gold ni resultados de retrieval. El contenido no participa
en tuning de Fase A.

Vector, contextualización, rerank y synthesis continúan bloqueados. Solo tras
GO lexical se auditan donors exactos y se congela el residual antes de solicitar
créditos o llamadas.

## Sustitución de V1.10 — anti-overfit y salida permitida

- Cero reglas por fabricante, modelo, documento, qid, pregunta o literal gold.
- Development decide; held-out confirma una vez y nunca retroalimenta V2.
- Los 39 bindings de claims no resueltos mantienen impacto KPI inconcluso.
- Cero facts pasan a OK por esta fase.
- No hay v4, DB, modelos, embeddings, serving ni deploy autorizados.

Tras GO adversarial, la única salida positiva de V2 es
`GO_TO_IMPLEMENT_BINDING_MANIFEST_AND_STATIC_SQL_V2`.
