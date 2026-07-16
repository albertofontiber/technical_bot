# S130 — reconciliación v8 de identidades held-out antes del censo

Contrato normativo compuesto por:

- `evals/s130_chunks_v3_adequacy_and_impact_design_v7.md`, SHA-256
  `afd32696a91a6b324373002afdf988ae9df89d0e18ea266b7d77784ddb5e9a57`;
- esta corrección de la resolución de identidades en fase 0.

V8 no cambia el censo, sus métricas, el mapa claim→extracción→bloque ganado, la
tabla S/P, los gates de v4/migración, la población ni el coste. Corrige una
suposición falsa del embargo v1: que todo raw record tiene binding primario por
`source_pdf_sha256` y que todo documento del snapshot aparece en `doc_map`.

## Evidencia del fail-closed v1

La ejecución autorizada por el permiso v1 se consumió y paró antes de leer
contenido del raw store:

| Recibo inmutable | SHA-256 |
|---|---|
| `evals/s130_chunks_v3_adequacy_execution_permit_v1.yaml` | `2553646bce79dd81e8cba610a9dfa84a33654ccf59992ea58b02fc79a41fa1ca` |
| `evals/s130_chunks_v3_adequacy_execution_consumption_v1.json` | `0cba9d165542bdecd1302c99bebec81a96d85c44e6276184fa0e971313333bce` |
| `evals/s130_chunks_v3_heldout_exclusion_manifest_v1.json` | `dc3582c5b467d4d0366700f8d7d39814562c8db9657458585fcb7f4d611c8d4d` |

Diagnóstico mecánico sobre los inputs ya congelados:

- S114: 24/24 extracciones existen en el raw store y 24/24 `document_id`
  existen en el snapshot completo; 9 tienen binding primario exacto y 15 tienen
  terminal M2.5 `primary_absent_pdf_sha`; ninguno tiene binding contradictorio;
- S115: 12/12 extracciones y documentos existen; los 12 tienen terminal
  `primary_absent_pdf_sha`; ninguno tiene binding contradictorio;
- seis documentos S114 no aparecen en `doc_map`, inventario que V6/V7 ya
  declaró incompleto;
- de las 29 identidades documentales S63, 25 resuelven de forma única por el
  catálogo, tres por metadata exacta y única del freeze S114, y una
  (`data/model_catalog.json`) no es un PDF ni pertenece a la población raw.

Los 35 fallos son, por tanto, una única incompatibilidad de contrato de
identidad más cuatro resoluciones S63 incompletas; no son gaps de `chunks_v3`.

## Sustitución normativa de fase 0

### 1. Binding directo de filas congeladas S114/S115

Para cada fila seleccionada se usan únicamente sus campos de metadata
`id`, `source_file`, `document_id` y `extraction_sha256`; queda prohibido leer o
comparar `content`, `context`, preguntas, respuestas o resultados held-out.

La fila es válida si y solo si:

1. `extraction_sha256` es un nombre exacto del raw store;
2. `document_id` existe en el snapshot documental completo V7;
3. existe exactamente un receipt M2.5 para la extracción y se cumple una de:
   - `primary_unique_active_pdf_sha` con el mismo `document_id`; o
   - `primary_absent_pdf_sha`, `matching_document_count = 0` y
     `document_id = null` en el receipt;
4. cualquier binding no nulo diferente, receipt ausente, terminal diferente,
   colisión o ambigüedad falla cerrado.

La extracción y el documento validados entran siempre en exclusión directa.
`doc_map` solo amplía por producto cuando tenga una fila con `entries`; su
ausencia se registra como `product_expansion_unavailable` pero no invalida la
exclusión directa ni la expansión por `docrel` en el universo documental V7.

### 2. Resolución de identidades S63

Para cada referencia PDF S63 se aplica esta precedencia exacta, sin fuzzy match:

1. basename normalizado con exactamente una extracción en `doc_map`+M2.5;
2. si no existe allí, basename con exactamente un par
   `(extraction_sha256, document_id)` en la metadata del universo congelado
   S114 (`source_rows ∪ candidate_scopes`), validado después por las reglas de
   binding directo anteriores;
3. cero o más de un par en cualquiera de los dos niveles falla cerrado.

Una referencia S63 con extensión distinta de `.pdf`, cero matches en ambos
índices y fuera de la población raw PDF se registra como
`logical_support_outside_raw_pdf_population`; no crea una exclusión física y no
falla. Esta regla es por tipo de población, no por nombre de archivo.

La resolución por metadata congelada no puede aportar producto por inferencia:
solo se amplía por los `entries` realmente presentes en `doc_map`. Todos los
bindings, terminales, rutas de resolución y ausencias de expansión deben quedar
contados y serializados en el embargo v2.

## Inmutabilidad y segunda ejecución

- Los tres recibos v1 permanecen intocables.
- La corrección requiere prereg, hashes, tests, permiso y outputs v2 nuevos.
- El permiso v2 será también one-shot y se consumirá antes de cualquier lectura
  de contenido.
- Ninguna regla permite inspeccionar contenido held-out, construir v4, migrar,
  reclasificar facts ni cambiar producción.
