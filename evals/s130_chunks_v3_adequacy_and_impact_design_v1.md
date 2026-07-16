# S130 — diseño del gate de adecuación e impacto de `chunks_v3`

## Decisión que debe habilitar

Decidir, antes de contexto/embeddings/DB, entre tres salidas mutuamente
excluyentes:

1. **A/B v2→v3**: v3 no muestra un gap estructural material que invalide medirlo.
2. **Proyección de retrieval sobre v3**: la capa lossless es correcta, pero ruido o
   metadata deben excluirse/marcarse sin volver a trocear el documento.
3. **Diseño v4**: existe una clase de fallo sistémica, material y propia de las
   fronteras/composición del chunker.

Este gate no mueve facts a OK, no cambia el chunker y no llama a modelos, red,
base de datos, contextualización ni embeddings.

## Pregunta cero

`chunks_v3` ya preserva los 333.161 bloques extraídos con cero pérdidas detectadas.
El trabajo solo cambia una decisión si distingue **preservación** de **utilidad para
retrieval** y evita pagar un shadow incapaz de ayudar o construir un v4 innecesario.

## Poblaciones completas

- Los 1.068 registros del raw store congelado y las 31.226 filas v3.
- Los 100 bloques recuperados en los 27 documentos cambiados, sin seleccionar
  ejemplos favorables.
- Los 157 claims del puente S125/S126, manteniendo visibles los denominadores y
  estados provisionales.
- Los held-out no participan en el diseño ni en los umbrales. Solo podrán validar
  una solución ya congelada.

## Carril A — mapa de impacto fact→fuente→bloque ganado

Para cada claim se conserva su binding autoritativo cuando existe:

- claims M1: `document_id`, página y support spans de
  `s125_m1_known_hold_contract_v1.json`;
- legacy carries: manual/página de las citas verificadas de
  `gold_answers_v1.yaml`, enlazadas al raw store por identidad normalizada de PDF;
- `document_id→extraction_sha256`: freeze M2.5 de S117.

Clasificaciones cerradas:

- `outside_changed_documents`;
- `changed_document_no_gained_page_binding`;
- `gained_page_no_support_overlap`;
- `candidate_material_support_manual_review`;
- `binding_unresolved`.

Un candidato léxico nunca recibe crédito automático. La revisión manual exige que
el **texto nuevo del bloque**, no solo el chunk vecino que lo absorbe, soporte una
parte material del claim. El mapa es evaluación de un chunker ya congelado; no se
retoca v3 contra los facts observados.

## Carril B — adecuación corpus-wide de v3

Se materializa localmente v3 desde el raw store y se compara con los recibos M28.
Se miden cinco clases, separando la capa responsable:

1. **Truncación/oversize**: filas por encima de 7.000 y 16.000 caracteres, tablas
   atómicas sobredimensionadas y contenido que B8 truncaría.
2. **Ruido/boilerplate**: bloques de símbolos, números de página, tablas vacías,
   headers/footers repetidos y filas dominadas por contenido no significativo.
3. **Fronteras relacionales**: caption→tabla, introducción→lista/procedimiento y
   continuaciones de la misma sección separadas sin carry-over.
4. **Jerarquía**: filas sin lineage, ramas hermanas mezcladas y headings repetidos
   compatibles con running headers.
5. **Visual**: `has_diagram` activado únicamente por `full_page_screenshot` frente
   a imágenes/diagramas reales. Este hallazgo se enruta a metadata, no a v4.

Los proxies se reportan como **riesgo**, no como fallo semántico probado.

## Gate v4

Solo se recomienda diseñar v4 si se cumplen todos:

1. el problema pertenece a composición/fronteras del chunker, no a extracción,
   metadata, contextualización o retrieval;
2. tiene evidencia corpus-wide: al menos 1% de filas, o 20 documentos y 2
   fabricantes, salvo un hard failure de truncación/pérdida;
3. existe un contrato generalizable sin reglas por fabricante, modelo, documento,
   qid, literal observado o gold;
4. la solución puede congelarse y validarse después contra held-out embargado;
5. el beneficio esperado no puede obtenerse con una proyección no destructiva
   sobre v3.

Si no se cumplen, v3 se congela y pasa al A/B. Si el problema es ruido, se conserva
v3 como capa de evidencia lossless y se propone una vista/flag de elegibilidad de
retrieval; no se destruye provenance para optimizar embeddings.

## Métricas y crédito upstream→downstream

- Extracción/chunking GO: evidencia material nueva preservada sin regresión.
- Retrieval GO: un fact antes ausente entra en el pool/servido, aunque después sea
  rerank- o synthesis-miss.
- Rerank GO: la evidencia recuperada entra en la ventana servida.
- Synthesis GO: la respuesta cubre el claim sin invención.

Ningún movimiento entre etapas se presenta como fact OK hasta completar la
cascada.

## Alternativas descartadas

- **Migrar v3 y medir directamente**: paga contexto/embeddings antes de saber si
  los deltas contienen señal y confunde losslessness con calidad.
- **Diseñar v4 ya**: los 100 deltas están dominados preliminarmente por ruido y no
  prueban un fallo de fronteras; sería solution-first y propenso a overfit.
- **Eliminar bloques de poco texto en el chunker**: reabre la pérdida que v3 acaba
  de cerrar y vuelve a confundir almacenamiento con elegibilidad de retrieval.
- **Auditar solo los facts fallidos**: no permite distinguir un patrón sistémico de
  una coincidencia del benchmark.

## Riesgos declarados

- Los matches legacy PDF/página pueden quedar sin resolver; se reportan, no se
  imputan por fuzzy matching silencioso.
- Los proxies de frontera y running-header necesitan revisión muestral antes de
  ser llamados defectos.
- El raw store demuestra fidelidad respecto de la extracción, no respecto del PDF
  visual original.
- Un A/B de retrieval seguirá siendo necesario aunque este gate sea GO.

## BP, estructura y escala

La separación **raw/evidence lossless → proyección recuperable → índice** mantiene
auditabilidad y permite optimizar retrieval sin destruir fuente. Los gates se
definen por propiedades de estructura y alcance corpus-wide, no por fabricante;
por tanto escalan a 30+ fabricantes y mantienen un held-out limpio para validar
cualquier cambio posterior.
