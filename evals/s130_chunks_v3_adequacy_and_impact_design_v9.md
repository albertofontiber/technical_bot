# S130 — reconciliación v9 de identidades held-out

V9 compone directamente sobre el contrato normativo V7, SHA-256
`afd32696a91a6b324373002afdf988ae9df89d0e18ea266b7d77784ddb5e9a57`,
y sustituye por completo V8, que recibió `NO-GO-to-implement-v2`.

V9 no cambia el censo, sus métricas, el mapa claim→extracción→bloque ganado, la
tabla S/P, los gates de v4/migración, la población ni el coste. Solo corrige la
construcción del embargo previo al censo.

## 1. Evidencia inmutable del fail-closed v1

| Recibo | SHA-256 |
|---|---|
| `evals/s130_chunks_v3_adequacy_execution_permit_v1.yaml` | `2553646bce79dd81e8cba610a9dfa84a33654ccf59992ea58b02fc79a41fa1ca` |
| `evals/s130_chunks_v3_adequacy_execution_consumption_v1.json` | `0cba9d165542bdecd1302c99bebec81a96d85c44e6276184fa0e971313333bce` |
| `evals/s130_chunks_v3_heldout_exclusion_manifest_v1.json` | `dc3582c5b467d4d0366700f8d7d39814562c8db9657458585fcb7f4d611c8d4d` |

El v1 verificó criptográficamente los bytes del raw store, pero se detuvo antes
de parsear JSON, acceder a campos de contenido, chunkear o hacer inspección
semántica. Sus 35 fallos no son resultados de `chunks_v3`.

## 2. Tres namespaces separados

Queda prohibido usar estos campos como sinónimos:

- `extraction_sha256`: identidad física del JSON del raw store; gobierna la
  exclusión del censo;
- `source_pdf_identity`: valor documental congelado; puede ser un SHA físico o
  una identidad `backfill:*`;
- `source_pdf_identity_status`: `known_physical`, `synthetic_backfill` o
  `unknown`.

Una identidad `backfill:*` nunca se serializa ni se cuenta como SHA de un PDF.
Una extracción con binding primario ausente nunca adquiere por inferencia el
papel de PDF fuente.

En el snapshot V7 hay 423 documentos con SHA PDF físico conocido y 748 con
identidad sintética `backfill:*`; cero tienen identidad vacía. Los 423 hashes
físicos únicos conocidos tienen intersección cero con los 12 PDFs S116. Esto no
demuestra por sí solo el solape frente a los 748 desconocidos físicos.

## 3. Ledgers de binding independientes

Solo se leen campos de metadata; quedan fuera `content`, `context`, preguntas,
respuestas y resultados held-out.

### 3.1 Ledger de metadata S114

Sobre `source_rows ∪ candidate_scopes` se construye una unión por `id` con
1.859 filas. Cada entrada canónica contiene:

`extraction_sha256`, `document_id`, basename NFKC+casefold, `row_ids` ordenados y
`occurrences`.

Se exigen simultáneamente:

- una única pareja `(document_id, basename)` por extracción;
- una única extracción por `(document_id, basename)`;
- ningún campo vacío ni colisión de `id` con metadata distinta;
- 36 extracciones y cero conflictos en ambas direcciones;
- SHA-256 del JSON canónico del ledger
  `50e52bbb52288da94b31f57721223634f10afbf81b2f5d1198c9a556fc2b8e3f`.

### 3.2 Ledger del snapshot de chunks

Las 25.090 filas `kind=chunk` del snapshot V7 se reducen a entradas canónicas
`document_id`, `extraction_sha256`, `chunk_rows`, ordenadas lexicalmente. Se
exigen 1.018 pares, 1.008 documentos, 1.018 extracciones y SHA-256 canónico
`1eec4001dfee4eb2228e92bb8f71018e02dc84e738b1973bce2aaabf5b97eaeb`.

El ledger global contiene tres documentos no vacíos con más de una extracción
y ocho extracciones históricas sin `document_id`; se serializan como conflictos
conocidos y nunca pueden entrar en un binding elegible. No existe ninguna
extracción no vacía asociada a dos documentos.

### 3.3 Regla de binding S114/S115

Una selección es válida si y solo si:

1. la extracción existe como nombre físico del raw store;
2. el documento existe en el inventario documental V7;
3. el par exacto aparece sin ambigüedad en ambos ledgers;
4. para terminal M2.5 `primary_unique_active_pdf_sha`, el documento coincide;
5. para `primary_absent_pdf_sha`, el receipt tiene `document_id=null`,
   `matching_document_count=0` y la extracción aparece en al menos dos filas
   concordantes del ledger S114;
6. cualquier otro terminal, singleton, conflicto o contradicción falla cerrado.

Evidencia esperada: S114 contiene 24 filas/22 extracciones-documentos únicos;
S115, 12 filas/5 únicos; combinados, 36 filas/24 pares únicos. Los 16 pares
únicos `primary_absent_pdf_sha` aparecen entre 3 y 181 veces en S114. Ningún
par seleccionado toca un conflicto del snapshot.

La exclusión física siempre usa las 24 extracciones únicas. La ausencia en
`doc_map` se registra como `product_expansion_unavailable`; no invalida el par,
porque V7 define el snapshot completo como inventario documental autoritativo.

## 4. Resolución exacta S63

Para cada referencia PDF se aplica, sin fuzzy matching:

1. basename con exactamente un par elegible en `doc_map` + ledger snapshot;
2. si no existe, basename con exactamente un par en el ledger S114, que debe
   cumplir después todas las reglas de binding de la sección 3.3;
3. si ambos niveles contienen el basename, deben devolver el mismo par;
4. cero matches PDF, más de un match o discrepancia falla cerrado.

Una referencia con extensión distinta de `.pdf`, cero matches en ambos índices
y fuera de la población raw PDF se registra como
`logical_support_outside_raw_pdf_population`; no crea exclusión física.

Conteos esperados: 29 referencias S63 por QID (25 catálogo, 3 ledger S114, 1
soporte no-PDF) y 23 identidades únicas (20, 2 y 1 respectivamente). El soporte
no-PDF es `model_catalog.json`; su nombre se serializa como evidencia, pero la
regla se decide por tipo de población, no por nombre.

## 5. Cierre relacional y proyección física

El cierre conserva V7: relaciones de producto hasta punto fijo, después
`docrel` hasta punto fijo. Cada documento del cierre se proyecta a extracción
solo mediante un par no ambiguo del ledger snapshot o, si coincide, del ledger
S114. Una extracción directa siempre permanece excluida.

La identidad congelada esperada contiene 43 documentos/extracciones directos y
un cierre de 70 documentos proyectados a 70 extracciones, sin unresolved ni
ambigüedad. Cualquier deriva de esos conteos o cualquier documento del cierre
sin proyección única falla cerrado. El embargo serializa hashes, cardinalidades,
conflictos conocidos y receipts de cada ruta.

## 6. Cohorte independiente S116

El campo `pdf_identity_overlap_with_development: 0` de
`s116_independent_document_holdout_replay_v1.json` no es evidencia: fue emitido
como constante y queda expresamente excluido de la decisión de identidad.

La cohorte activa son solo los 12 documentos del prereg V4 y acquisition V2.
Los dos PDFs fallidos del status histórico V1 no pertenecen a esta cohorte, no
se declaran independientes y no se usan en el censo ni en su validación.

La independencia se acepta únicamente si:

- los 12 SHA PDF coinciden con acquisition V2 y no solapan los 423 hashes PDF
  físicos conocidos del snapshot;
- `s116_independent_near_duplicate_screen_prereg_v2.yaml`, SHA-256
  `7eb89caae2d9336715a5faf71933b45505a25b1265f7de3f0e04b8995996f8da`,
  sigue congelado;
- `s116_independent_near_duplicate_screen_v2.json`, SHA-256
  `89ac9ab7b64ba0330cea0d7b6b0acb10f5740eff595e53a4ea13f4783cff2fb`,
  verifica el manifest exacto de las 1.068 extracciones de desarrollo, los 12
  hashes candidatos, cero duplicados de contenido normalizado y cero
  near-duplicates sobre los umbrales preregistrados.

Así, el screen de contenido ya congelado cubre la zona donde el hash físico del
PDF de desarrollo es desconocido. S130 no vuelve a leer ese contenido. Los 12
documentos se registran como `independent_external_not_in_development_census` y
no crean exclusiones físicas.

## 7. Ejecución v2

- Los recibos v1 permanecen intocables.
- Se requieren prereg, tests, permiso y outputs v2 nuevos y hash-pinned.
- El permiso v2 es one-shot y se consume antes de parsear JSON, acceder a
  campos de contenido o ejecutar el chunker.
- La verificación criptográfica de bytes previa al embargo sí está permitida y
  debe distinguirse de una lectura semántica.
- Ninguna regla autoriza v4, migración, reclasificación de facts, modelos, red,
  base de datos o cambios productivos.
