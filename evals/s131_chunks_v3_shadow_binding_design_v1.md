# S131 — reconciliación de binding y shadow atribuible para `chunks_v3`

## 1. Objetivo y límite de autoridad

S131 corrige el contrato de persistencia preparado antes de que existiesen la
materialización lossless actual y la reconciliación de identidades S130.

El objetivo inmediato es autorizar **implementación local y revisión estática**
de un binding explícito `extracción -> documento` y de su SQL versionado. Este
diseño no autoriza aplicar migraciones, acceder a una base de datos, cargar
filas, generar contexto, crear embeddings, servir `chunks_v3`, desplegar,
reclasificar facts ni construir `chunks_v4`.

## 2. Evidencia congelada

| Rol | Ruta | SHA-256 |
|---|---|---|
| candidato lossless actual | `evals/s117_m28_candidate_materialization_seed1_v1.json` | `b18df39ad1677d0f20da4b78f32a8823162d826ff2387a82032adbac1d292b9e` |
| gate de cobertura reconciliada | `evals/s117_m29_reconciled_loss_ledger_gate_v1.yaml` | `ed243b6b6922f14464b0d300ba203cf580548550e3e2b22e2e14b52ea23eaa17` |
| snapshot v2 read-only | `tmp/s117_m2/remote_snapshot_v1.jsonl.gz` | `3013c553da20c72fbfe0dc801dad4ea4b063ecff3138dcf55b5cd7831cf79067` |
| embargo S130 | `evals/s130_chunks_v3_heldout_exclusion_manifest_v2.json` | `654ee7c211b2d908912e5600513fbc293ba9cda9bb6a9482e1266e378fd099b8` |
| auditoría S130 | `evals/s130_chunks_v3_adequacy_audit_v2.json` | `8d53ae28a5b78f4f3392a8cdaf1008fef6e4f302a448af09bbbf9f0076163e7c` |
| triage S130 | `evals/s130_chunks_v3_gap_triage_v1.yaml` | `8f90a3d31b1db9e5ad09c919804fefb512d0a7d7daf03f849e9ed5f2766fbd0e` |
| SQL antiguo, solo antecedente | `supabase/migrations/20260714102428_chunks_v3_provenance_shadow.sql` | `cc328b3d11fadd2f094c491cfe4d8713044f89d2de05b7e405bd92b09c2ede90` |
| política M27 antigua, solo antecedente | `evals/s117_m27_common_retrieval_policy_contract_v2.sql` | `77e385906345ceedcd1c6eaa2c653851e6219020768e02e8f7ece78da784d6ae` |

El candidato vigente tiene 1.068 extracciones, 31.226 filas, 333.161 bloques
raw cubiertos, 100 bloques ganados frente al baseline y cero regresiones. El
chunker vigente es `d851abf6761d8e5ff6dee4d2727b85c86fda21059dce8875a028cf8298e87764`.

## 3. Deuda que se sustituye

Los contratos S117 de antecedente no son aplicables al shadow actual porque:

1. fijan el chunker `4b76ab...` y 31.212 filas, no el candidato actual;
2. exigen `documents.source_pdf_sha256 = chunks_v3.extraction_sha256`;
3. hacen `document_id` obligatorio para las 1.068 extracciones;
4. mezclan identidad del JSON extraído, identidad física del PDF y documento
   lógico;
5. el propio gate S117 declaró M0b no ejecutado y `NO_GO_FOR_DB`.

No se modifica ni se reinterpreta evidencia histórica. Una migración correctiva
posterior debe ser un fichero nuevo y versionado; el SQL anterior queda como
antecedente no autoritativo.

## 4. Namespaces y autoridad del binding

Se mantienen separados:

- `extraction_sha256`: identidad del registro de extracción y clave del raw;
- `raw_artifact_sha256`: hash de los bytes JSON concretos;
- `source_pdf_identity`: identidad documental, que puede ser SHA físico o
  `backfill:*`;
- `document_id`: identidad lógica del catálogo;
- `binding_receipt_sha256`: recibo de la decisión extracción→documento.

El snapshot de chunks v2 ofrece una relación histórica útil para un A/B, pero
no convierte la extracción en PDF. Su autoridad se denomina
`legacy_snapshot_reciprocal_shadow_only` y no basta para publicación productiva.

## 5. Población cerrada del binding

El ledger se deriva exclusivamente de las filas `kind=chunk` y `kind=document`
del snapshot congelado, por igualdad exacta y sin fuzzy matching.

| Estado de extracción | Extracciones | Uso |
|---|---:|---|
| `bound_active_physical_sha_verified` | 405 | A/B shadow |
| `bound_active_legacy_snapshot_only` | 597 | A/B shadow; identidad PDF no verificada |
| `bound_nonactive_legacy_snapshot` | 8 | registro estructural, no retrieval |
| `unbound_snapshot_empty_document` | 8 | registro estructural, no retrieval |
| `unbound_absent_from_snapshot` | 50 | registro estructural, no retrieval |
| **Total** | **1.068** | |

Las dos primeras clases forman exactamente 1.002 extracciones asociadas a 999
documentos activos. Las 1.010 extracciones con documento recíproco se asocian a
1.007 documentos; tres documentos tienen dos extracciones históricas. Esto no
es una colisión extracción→documento y se conserva explícitamente.

Los ocho bindings no activos se desglosan en cinco `needs_review` y tres
`superseded`. Ninguna de las 66 extracciones no elegibles recibe documento
inventado, fallback por nombre o elegibilidad fail-open.

## 6. Manifest de binding determinista

Antes del SQL se implementará un generador local con dos ejecuciones sembradas
y payload canónico byte-idéntico. Una entrada por extracción, ordenada por
`extraction_sha256`, contendrá exclusivamente:

1. `materialization_id`;
2. `extraction_sha256`;
3. `document_id` nullable;
4. `binding_status` de la tabla anterior;
5. `binding_authority`;
6. `document_status_at_snapshot` nullable;
7. `source_pdf_identity_status` (`known_physical`, `synthetic_backfill` o
   `unknown`);
8. `snapshot_binding_ledger_sha256`;
9. `binding_receipt_sha256`.

El recibo por fila compromete todos esos campos salvo sí mismo. El manifest
compromete las 1.068 filas, sus conteos y el SHA canónico del ledger snapshot
`1eec4001dfee4eb2228e92bb8f71018e02dc84e738b1973bce2aaabf5b97eaeb`.

Falla cerrado ante identidad vacía inesperada, extracción ausente del universo
raw, más de un documento por extracción, documento inexistente, status
desconocido, deriva de conteos o no determinismo.

## 7. Contrato SQL v2

La implementación SQL posterior será una migración nueva y transaccional que
compone sobre el antecedente S117 en una base fresca. Debe:

1. crear `chunk_document_bindings_v1` con PK
   `(materialization_id, extraction_sha256)`, FKs a generación y documento
   nullable, estados cerrados y receipts SHA-256;
2. permitir `chunks_v3.document_id IS NULL`, pero nunca omitir el binding: toda
   fila debe resolver por `(materialization_id, extraction_sha256)`;
3. validar en la RPC de sellado que el `document_id` denormalizado de cada chunk
   sea `IS NOT DISTINCT FROM` el del binding;
4. añadir a la generación `expected_bindings`,
   `bindings_manifest_sha256` y conteos esperados por estado;
5. exigir 1.068 bindings y 31.226 chunks antes de validar la generación;
6. mantener filas y bindings append-only tras sellar;
7. revocar acceso a `PUBLIC`, `anon` y `authenticated`, y conservar publicación
   mediante RPC estrecha de mínimo privilegio;
8. eliminar de validadores y vistas la igualdad falsa
   `source_pdf_sha256 = extraction_sha256`;
9. no crear HNSW ni habilitar serving.

La vista de retrieval shadow será la intersección de cuatro condiciones:

- generación `active` en el shadow;
- binding en una de las dos clases `bound_active_*`;
- `documents.status = 'active'` en el snapshot/base usada por el experimento;
- política de fila elegible y `duplicate_of IS NULL`.

Una deriva entre el status documental congelado y la base objetivo bloquea la
carga y obliga a capturar un snapshot read-only nuevo. No se actualiza el
manifest silenciosamente.

## 8. M0b en PostgreSQL+pgvector desechable

El gate real, bajo autorización separada, aplicará en orden:

1. fixture mínimo compatible con Supabase (`anon`, `authenticated`,
   `service_role`, `documents`, `chunks_v2`, `spanish_unaccent`, pgvector);
2. migración S117 antecedente;
3. migración correctiva S131;
4. fixtures de las cinco clases de binding;
5. validación, publicación, retiro, descarte y carreras de transición;
6. catálogo, constraints, RLS, grants, vistas y firmas RPC;
7. pruebas negativas de binding ausente, documento divergente, status no
   elegible, count/hash incorrecto y mutación post-sellado;
8. rollback completo y verificación de ausencia de residuos.

El entorno local actual no dispone de `docker`, `podman`, `psql` ni CLI de
Supabase. S131 no instala software ni usa Railway por inferencia. Tras GO del
contrato se elegirá, con autorización separada, el runtime desechable de menor
coste y riesgo.

## 9. Shadow atribuible y control de coste

Antes de embeddings o modelos se ejecutará un probe lexical determinista sobre
dos brazos reconstruidos desde el mismo universo raw y restringidos a las mismas
1.002 extracciones activas:

1. baseline loss-accounted de 31.212 filas, sin proyección P;
2. candidato lossless de 31.226 filas, sin proyección P.

Mismos queries, filtros, FTS, top-k, fusion desactivada, cohortes y adjudicación.
Este probe puede demostrar no-regresión o señal lexical, pero no efecto vector,
rerank, synthesis ni transición a OK.

Solo si ese gate pasa se audita donación exacta de contexto/embedding. Reutilizar
requiere igualdad de contenido, metadata enumerada, input efectivo, modelo y
dimensiones; no se presupone un número de donors. Primero se congela el residual
y después, si hiciera falta, se solicita un techo explícito para llamadas.

## 10. Anti-overfit y resultados permitidos

- Cero reglas por fabricante, modelo, documento, qid, pregunta o literal gold.
- Los 70 held-out S130 no se abren ni participan en tuning.
- Los 39 bindings de claims aún no resueltos mantienen el impacto KPI
  inconcluso.
- No se cambia el funnel ni se mueve ningún fact a OK.
- No se construye `chunks_v4`: cualquier gap recuperable se aborda después como
  proyección reversible, separada del almacenamiento lossless.

Tras revisión adversarial, el único resultado positivo de V1 es
`GO_TO_IMPLEMENT_BINDING_MANIFEST_AND_STATIC_SQL_V2`. Cualquier ejecución DB,
lexical, vectorial o productiva requiere su gate posterior.
