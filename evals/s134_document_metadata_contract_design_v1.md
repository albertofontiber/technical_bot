# S134 — contrato canónico de metadatos documentales para `chunks_v3` shadow

## Objetivo

Eliminar la reinferencia de fabricante, modelo y procedencia en cada ingestión
shadow. Cada documento lógico tendrá un único registro versionado y sus chunks
heredarán ese registro por `document_id`. El detector heurístico seguirá siendo
solo una propuesta inicial para documentos nuevos; no será autoridad silenciosa.

Esta fase no publica `chunks_v3`, no altera producción y no mueve facts a OK.

## Autoridad de esta versión

La fuente local congelada es el snapshot remoto v2 y el universo activo es el
manifest de bindings candidato S131. Para cada `document_id` activo se consideran
únicamente chunks base (`parent_id = null`) del snapshot.

Los campos documentales son:

- obligatorios: `manufacturer`, `product_model`, `source_file`;
- opcionales: `distributor`, `doc_type`, `category`.

Un campo solo se acepta si todos sus valores no vacíos son idénticos. Los campos
obligatorios deben tener exactamente un valor no vacío; los opcionales pueden ser
unánimes o completamente nulos. Cualquier conflicto, documento sin chunks base o
campo obligatorio vacío hace fallar toda la ejecución. No se usan mayoría,
normalización difusa ni reparación manual.

Los documentos lógicos con varias extracciones activas conservan un único
registro, con la lista ordenada de sus `extraction_sha256`. La autoridad resultante
se denomina `legacy_v2_unanimous_active_shadow_v1`: es suficiente para evaluar el
shadow, pero no constituye todavía una verdad productiva universal.

## Identidad, determinismo y privacidad

La salida contiene una fila ordenada por `document_id` con los seis campos,
extracciones, conteo de chunks fuente, autoridad y recibos SHA-256 canónicos. No
contiene `content`, `context`, preguntas, respuestas ni embeddings.

El script debe verificar antes de leer:

1. SHA-256 físico del snapshot comprimido;
2. SHA-256 del manifest S131;
3. recibo lógico del JSONL descomprimido;
4. conteos congelados del universo activo.

Dos ejecuciones independientes deben producir bytes idénticos. Cada fila tendrá
un recibo sobre todos sus campos salvo el propio recibo, y el manifest tendrá un
recibo sobre la lista completa de filas.

## Contrato de persistencia posterior

La implementación SQL posterior, si este gate pasa, añadirá una tabla normalizada
de snapshots de metadatos con clave `(materialization_id, document_id)`. Los chunks
shadow elegibles deberán referenciar el recibo exacto de su documento y sus campos
deberán coincidir con él. La vista de retrieval fallará cerrada ante ausencia o
divergencia. Los registros se volverán inmutables al sellar la materialización.

No se modifica ninguna migración histórica S117/S131. Cualquier cambio será una
migración nueva y versionada, validada primero en PostgreSQL desechable.

## Gate

GO exige simultáneamente:

- 999 documentos activos distintos y 1.002 bindings de extracción activos;
- cero conflictos en los seis campos;
- cero valores obligatorios ausentes;
- exactamente tres documentos con dos extracciones y el resto con una;
- igualdad byte a byte entre dos ejecuciones;
- pruebas unitarias negativas que demuestren fallo cerrado;
- coste cero en modelos, embeddings, red, base de datos y escrituras productivas.

Si cualquier condición falla, el resultado es NO-GO y no se construye el shadow
de retrieval v2/v3 sobre metadatos inferidos.
