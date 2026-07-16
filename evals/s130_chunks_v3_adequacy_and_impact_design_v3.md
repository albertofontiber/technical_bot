# S130 — gate v3 de adecuación e impacto de `chunks_v3`

Este diseño sustituye v1 y v2, ambos **NO-GO-to-build**. Es una auditoría local,
determinista y sin modelos, red, DB, contextualización ni embeddings. No autoriza
migración, producción ni construcción de v4.

## Dos ejes y estados cerrados

El informe asigna dos ejes independientes:

- **S — almacenamiento/chunker**: `v3_adequate`, `v4_design_required` o
  `inconclusive`.
- **P — proyección recuperable**: `projection_design_warranted`,
  `no_projection_design_signal` o `inconclusive`.

Una auditoría estructural nunca afirma que una proyección sea necesaria para
retrieval; `required` solo podría establecerlo un A/B posterior.

### Precondiciones comunes

Antes de asignar S o P deben cumplirse todas:

1. embargo materializado y `GO`;
2. raw store, chunker, materializador y recibos M28/M29 con hashes válidos;
3. 100% de documentos y filas no embargados procesados;
4. toda detección incluida en una disposición final, sin `pending`, colisión ni
   identidad no resuelta;
5. dos ejecuciones locales producen payload canónico byte-idéntico.

Si falla una precondición, ambos ejes son `inconclusive`.

### Tabla de verdad S

| Condición tras las precondiciones | S |
|---|---|
| Se cumple vía hard o vía sistémica v4 | `v4_design_required` |
| Ninguna vía v4 se cumple; cero pérdida raw→stored y cero binding raw→fila roto | `v3_adequate` |
| Cualquier otro caso | `inconclusive` |

### Tabla de verdad P

| Condición tras las precondiciones | P |
|---|---|
| Existe una clase no destructiva y retrieval-owned que cumple el umbral sistémico de diversidad, o clipping B8 cierto resoluble conservando `content` | `projection_design_warranted` |
| No existe ninguna de esas clases | `no_projection_design_signal` |
| Responsabilidad o resolución no demostrada | `inconclusive` |

Las combinaciones S×P solo seleccionan la rama que se podrá **diseñar** después:
v3, v3+P, v4 o v4+P.

## Registro exhaustivo de embargo

Fase 0 materializa de forma fail-closed
`evals/s130_chunks_v3_heldout_exclusion_manifest_v1.json` desde estos inputs
autoritativos exactos:

| Rol | Ruta | SHA-256 |
|---|---|---|
| held-out antiguo por pregunta | `evals/s63_pairing_heldout.yaml` | `f5158103ae4a8ab8228617c852dea05ea7de3c11524111b3571bcdbd8152abc3` |
| veredicto S63 | `evals/s63_heldout_verdict.yaml` | `dc2e777bce09c8176b7e7359383817e00027b9162ba42141656d520365081fe4` |
| freeze de procedimientos | `evals/s114_procedure_bundle_heldout_freeze_v1.json` | `227e808a2ba2308acce89f90722fd46a63bad30aae0cde630191154b4ff07d94` |
| freeze nested de referencias | `evals/s115_reference_edge_nested_holdout_freeze_v1.json` | `107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e` |
| adquisición independiente | `evals/s116_independent_holdout_acquisition_v2.json` | `d0ab94546cb899b73e69d5cd6ae3ea5b660bbab74c835834a24cda35ce5e5544` |
| replay independiente | `evals/s116_independent_document_holdout_replay_v1.json` | `241a1812de979743b10f369be5f0795579c17ca74642b286c6bc96a2a3e372fa` |
| estado independiente | `evals/s116_independent_document_holdout_status_v1.yaml` | `fbe69648c289817486865b848d8ba193bc6cfedc573ee31fe19ac86e996bb1e2` |
| binding extracción→documento | `evals/s117_m25_primary_binding_baseline_v1.json` | `bd7b24e93f730f5bbecd688cacc8fb233abdac07b68096ec934327670df4e626` |
| mapa documental | `data/catalog/doc_map.jsonl` | `992c62c21b5772caebf09f422adca20ffe4035143861ca931e5198e820572c82` |
| relaciones de catálogo | `data/catalog/relations.jsonl` | `09bb24af2ac5f0277cd6f80fc36e61ef710da4d2cd8704b1392e67e5df1f699d` |

Los preregistros superseded no añaden identidades y no son fuentes. S117 M26 es
una auditoría de reutilización de cohortes ya expuestas, no un nuevo held-out.

El materializador resuelve y congela, por semilla: `qid` cuando aplique,
`chunk_id`, `document_id`, `extraction_sha256`, PDF hash, basename normalizado,
revisión y producto. Expande por punto fijo las relaciones ya congeladas de
traducción, revisión, `variant-of`, `shared-doc`, rebrand/OEM y documentos
relacionados. El output incluye el cierre exacto, sus recibos y recuentos, pero no
resultados de preguntas held-out.

Una semilla o relación no resoluble, una colisión o el drift de un hash detiene
la fase 0 y prohíbe leer contenido para la auditoría. Los activos independientes
S116 no se consideran disponibles para validar v4 hasta revalidar su presencia;
su identidad sí permanece embargada.

## Carril A — impacto claim→fuente→bloque ganado

Bindings permitidos:

- M1: `document_id`, página y support spans de S125;
- legacy: PDF/página/quote de `gold_answers_v1.yaml`, por basename normalizado
  exacto y página;
- `document_id→extraction_sha256`: S117 M2.5.

No hay fuzzy matching. Una colisión falla cerrada. Tras excluir el cierre
embargado se congelan denominadores reales `N_claims_eligible` y
`N_gained_blocks_eligible`; nunca se presupone 157/100.

Cada claim elegible termina en: `outside_changed_documents`,
`changed_document_no_gained_page_binding`, `gained_page_no_support_overlap`,
`material_support_confirmed`, `material_support_rejected`, `manual_review_pending`,
`binding_unresolved` o `binding_collision`.

Cada bloque elegible termina en: `material_support_non_ok_or_unmeasured`,
`material_support_already_ok`, `context_only`, `surface_risk`, `no_claim_link`,
`manual_review_pending`, `unresolved` o `binding_collision`.

Un positivo exige `extraction_sha256`, `source_block_index`, página, offsets
`start/end`, quote exacta, `quote_sha256`, claim id y verificación de que la quote
es subcadena del bloque raw. Solapamiento léxico solo propone candidatos.

### Gate de impacto

| Condición | Resultado |
|---|---|
| Todos los elegibles tienen disposición final; cero pending/unresolved/collision; ≥1 positivo exacto para claim no-OK/no medido | `shadow_signal` |
| Todo resuelto pero solo beneficia OK/contexto/no-claim | `no_kpi_shadow_signal` |
| Cualquier pending/unresolved/collision o cobertura incompleta | `impact_inconclusive` |

`shadow_signal` es crédito upstream de descubrimiento; no mueve un fact a OK.

## Carril B — adecuación corpus-wide

Se rematerializa v3 desde raw y se valida contra M28/M29. Sobre el universo no
embargado se miden y adjudican:

1. preservación exacta del stream y cobertura raw→fila;
2. fronteras caption→tabla, introducción→lista/procedimiento y continuaciones;
3. lineage ausente, ramas hermanas mezcladas y running headers repetidos;
4. riesgos superficiales: símbolos, páginas, tablas vacías y boilerplate;
5. metadata visual usando **todas** las páginas cubiertas por la fila, separando
   screenshot de página completa de imagen/diagrama real.

Los proxies no prueban ruido semántico. Los 87 bloques M29 sin regla permanecen
sin juicio hasta adjudicación final.

### Tamaño y representación B8

B8 usa `context + "\n\n" + content` y recorta a 16.000 caracteres:

- `stored_content_over_16000`: prueba riesgo/clip de la representación B8, no
  pérdida raw→stored ni defecto v3 por sí solo;
- `structural_oversize_7000_16000`: tamaño estructural, no truncación;
- pre-B7 se informa `margin_to_16000 = 16000 - len(content)`, no un booleano;
- post-B7, `exact_embedding_length = len(context) + 2 + len(content)` y
  `exact_b8_clipped = exact_embedding_length > 16000`.

Una fila atómica larga se enruta primero a P. Solo puede apoyar v4 si una
proyección lossless/reversible no conserva su semántica recuperable y además
cumple una vía v4.

## Gate anti-overfit v4

### Vía hard correctness

Hay pérdida real raw→stored o binding raw→fila roto, reproducible y causado por
composición/fronteras del chunker; no por extracción, metadata, contextualización,
embedding ni retrieval. Además, una proyección no destructiva sobre la evidencia
almacenada no puede recuperar el contenido/relación perdido.

### Vía sistémica

Se cumplen todas:

1. clase propia de composición/fronteras del chunker;
2. ≥1% de filas elegibles, limitando cada documento al 10% del peso;
3. ≥20 documentos, ≥3 componentes de linaje independientes tras colapsar
   revisión/traducción/rebrand y ≥2 fabricantes;
4. ningún documento aporta >10% de la evidencia ponderada;
5. regla general sin fabricante, modelo, documento, qid, literal gold ni pregunta;
6. proyección no destructiva insuficiente.

Si no hay hard failure ni diversidad sistémica, no se abre v4. Cualquier cambio
posterior se congela antes de mirar held-out y crea versión nueva.

## Contrato de una eventual proyección

`content` y provenance son inmutables. La proyección solo añade disposición por
bloque, recibo, `retrieval_eligible` y/o `retrieval_text` derivado con hash de
transformación y cobertura exacta de bloques fuente. La misma proyección debe
alimentar B7, embeddings, FTS, HYQ/enunciados y fusion; las citas siempre salen
de `content`. No admite reglas por fabricante/modelo/documento/qid.

## Futuro A/B atribuible

Primera fase obligatoria: dos brazos reconstruidos juntos, **v2 sin P vs v3 sin
P**, para aislar chunker. Si P tiene señal, el diseño preferido es factorial 2×2:

1. v2 sin P;
2. v3 sin P;
3. v2 + P;
4. v3 + P.

Si el presupuesto no permite 2×2, se ejecuta primero v2 vs v3 sin P y después,
sobre el chunker ganador congelado, sin P vs P. Esa variante estima efectos
secuenciales pero no interacción; nunca se presenta como factorial.

Todos los brazos comparten snapshot raw/catálogo, B7 prompt/modelo/config/caché,
B8 proveedor/modelo/dimensión/límite, índices vector/FTS, HYQ/enunciados, fusion,
rerank, flags, top-k, seeds, cohortes y recibos. Se congelan hashes por componente
y fila. Si v2 histórico no es reproducible, ambos brazos se regeneran; nunca se
compara histórico contra nuevo.

## Crédito, BP y coste

Chunking, retrieval, rerank y synthesis reciben crédito por superar su propia
etapa; solo completar la cascada mueve el claim a OK. La separación evidencia
lossless→proyección recuperable→índice es auditable y escalable a 30+
fabricantes. Este gate cuesta cero modelos, red, DB y embeddings. Solo una señal
material autoriza diseñar el experimento mínimo posterior.
