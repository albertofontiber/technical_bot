# S117 M2.9 — diseño del ledger reconciliado de pérdidas v1

## Decisión y límite de autoridad

M2.9 no vuelve a ejecutar el chunker, no lee el raw store y no constituye una
nueva medición del corpus. Construye una derivación determinista y cerrada desde
evidencia ya congelada para responder una sola pregunta:

> ¿Las 100 identidades de bloque que faltaban en el baseline están cubiertas por
> la materialización candidata, sin que aparezca ninguna pérdida nueva?

La autoridad máxima del resultado es
`reconciled_frozen_evidence_raw_parsed_block_surface_only`. Un GO prueba
reconciliación estructural de cobertura sobre bloques ya parseados. No prueba
fidelidad visual al PDF, corrección semántica, mejora de retrieval/rerank/synthesis,
transición de facts a `OK` ni aptitud para carga o serving.

## Cadena de evidencia

El runner recibirá, mediante preregistro con hashes exactos:

1. Los dos outputs M2.7C. Cada uno contiene los 1.068 documentos, los conjuntos
   baseline/treatment de missing blocks, las ganancias y regresiones, y el delta
   completo de los 27 documentos afectados. Ambos seeds ya son byte-identical.
2. El informe compacto M2.7B con las 100 identidades baseline perdidas y sus
   disposiciones congeladas: 13 `authorized_exclusion` y 87 `unruled_loss`.
3. Los dos receipts M2.8 del candidato. Ambos prueban que la proyección candidata
   de 1.068 documentos es exactamente la proyección treatment de M2.7C, con hash
   `4cd69ba2912a8b7e1899512f99e7a1e3abd4ec970c96e9c4286b28443a0f8881`,
   333.161/333.161 bloques cubiertos, 100 ganancias y 0 regresiones.
4. Los gates M2.7C y M2.8, el preregistro y el permit de materialización candidata,
   para enlazar autoridad, ejecución consumida, no-carga y límites de inferencia.

La conclusión por bloque no se copiará de una etiqueta agregada. Para cada
documento se reconstruirán desde los outputs M2.7C los conjuntos exactos:

- `baseline_missing_block_indexes`;
- `treatment_missing_block_indexes`;
- `coverage_gain_block_indexes`;
- `coverage_regression_block_indexes`.

La igualdad de proyección demostrada por M2.8 permite sustituir de forma explícita
`candidate_missing = treatment_missing` y
`candidate_gain = treatment_gain`, siempre que ambos candidate receipts sean
idénticos, canónicos, `GO`, no loadable, tengan cero failures, y declaren
`treatment_projection_exact=true`. Si cualquiera de esos enlaces falla, el ledger
es `NO_GO`; no existe fallback.

## Salida cerrada

El payload no loadable tendrá esquema cerrado y cinco secciones de evidencia:

### `dependencies`

Mapa exacto de roles preregistrados a SHA-256 observados. No contendrá rutas físicas.

### `population`

Conteos agregados exactos:

- 1.068 documentos y 333.161 bloques raw;
- baseline: 333.061 cubiertos y 100 missing;
- candidato: 333.161 cubiertos y 0 missing;
- 100 ganancias, 0 regresiones;
- 27 documentos cambiados y 1.041 estables;
- 13 exclusiones autorizadas y 87 pérdidas no regladas en baseline;
- 100 pérdidas baseline reconciliadas como cubiertas por el candidato.

### `documents`

Lista canónica de 1.068 recibos, ordenada por `extraction_sha256`, con esquema
cerrado:

```text
schema
extraction_sha256
raw_artifact_sha256
raw_blocks
baseline_covered_blocks
baseline_missing_block_indexes
candidate_covered_blocks
candidate_missing_block_indexes
coverage_gain_block_indexes
coverage_regression_block_indexes
changed
receipt_sha256
```

`receipt_sha256` se calcula sobre el mismo objeto sin ese campo. Se validarán
identidades únicas, índices enteros no negativos, ordenados y sin duplicados,
índices dentro de rango, particiones de cobertura exactas y las igualdades:

```text
gain       = baseline_missing - candidate_missing
regression = candidate_missing - baseline_missing
```

### `resolved_losses`

Lista canónica de exactamente 100 filas, ordenada por
`(extraction_sha256, source_block_index)`. No incluirá `text`, contexto ni rutas.
Cada fila tendrá:

```text
schema
extraction_sha256
source_block_index
source_page_ordinal
page
kind
text_sha256
ledger_receipt_sha256
baseline_disposition
baseline_rule_id
candidate_disposition = covered
document_receipt_sha256
resolution_evidence = exact_candidate_projection
receipt_sha256
```

Los campos de identidad y disposición salen del compacto M2.7B. Cada identidad
debe aparecer una sola vez, estar en `baseline_missing`, estar en
`coverage_gain`, no estar en `candidate_missing` y enlazar el recibo documental
correspondiente. `receipt_sha256` se calcula excluyéndose a sí mismo.

### `manifests`, `checks`, `failures`, `cost` y `authorization`

Los manifests hash-bindearán las listas canónicas de documentos, pérdidas
resueltas, identidades baseline missing e identidades candidate missing. `checks`
será un mapa cerrado. `failures` será una lista cerrada de códigos sanitizados,
sin excepciones, paths ni contenido. Coste externo exacto cero.

La autorización conservará `facts_moved_to_ok: 0`, `M3: BLOCKED`, y `false` para
DB, network, modelos, embeddings, retrieval, context generation, load, serving y
deploy.

## Independencia, determinismo y ejecución

El runner será stdlib-only y no importará runners M2.7/M2.8 ni módulos de
producción. Implementará localmente:

- JSON estricto UTF-8: rechaza BOM, duplicate keys, NaN/Infinity y números no
  finitos;
- JSON canónico: claves ordenadas, separadores compactos y `ensure_ascii=false`;
- validación de esquema cerrado para todos los inputs consumidos y el output;
- validación exacta de todos los hashes seleccionados antes de derivar filas;
- tripwire de red por socket;
- códigos de fallo fijos y salida cerrada también en `NO_GO`.

Dos procesos separados, seeds 1 y 2, perturbarán el orden de documentos y pérdidas
antes de restaurar el orden canónico. Sus outputs deberán ser byte-identical,
canonical JSON y terminar en exactamente un LF. Las ejecuciones solo se autorizarán
mediante un permit separado posterior al preregistro y a la revisión adversarial.

## Gates de aceptación preregistrables

Todos son obligatorios:

1. hashes y esquemas de inputs exactos;
2. ambos M2.7C seeds equivalentes en proyección documental y delta;
3. ambos candidate receipts byte-equivalentes en contenido lógico y `GO`;
4. enlace candidato-proyección-treatment exacto;
5. 1.068 recibos únicos y particiones por documento exactas;
6. conjunto baseline missing exactamente igual al compacto100;
7. conjunto candidate missing vacío;
8. ganancias exactamente iguales a las 100 identidades baseline missing;
9. regresiones vacías;
10. 100/100 filas resueltas con enlaces de recibo válidos;
11. conteos y manifests exactos;
12. output cerrado, no loadable y cero coste externo;
13. dos seeds byte/logical identical.

El GO se denominará `RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY`. No autoriza por sí
mismo M2.7A. Tras su gate, M2.7A tendrá contrato y permit propios sobre los 18
documentos/21 tareas afectados.

## Amenazas y pruebas negativas obligatorias

Los tests deberán rechazar al menos:

- borrar una identidad del compacto100;
- añadir una identidad que nunca faltó;
- mover una identidad a otro documento o índice;
- duplicar una pérdida o un documento;
- presentar gain sin baseline missing;
- ocultar una regresión;
- alterar un receipt o manifest conservando los conteos;
- candidato con `treatment_projection_exact=false`, failures o `loadable=true`;
- drift entre seed1 y seed2 de M2.7C o M2.8;
- dependencia, preregistro o permit con hash distinto;
- symlink/path escape y fichero seleccionado extra;
- duplicate JSON keys, BOM, NaN/Infinity o `1e999`;
- intento de red;
- fuga de path, excepción, texto del manual, variable de entorno o secreto en
  outputs GO/NO_GO.

No se permite reabrir adjudicaciones baseline ni reinterpretar las 13 exclusiones.
M2.9 conserva el histórico: aquellas filas fueron pérdida/exclusión en baseline y
quedan reconciliadas como cobertura candidata; no se reescribe su pasado.
