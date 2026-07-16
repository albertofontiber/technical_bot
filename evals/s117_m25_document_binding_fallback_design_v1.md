# S117 M2.5 — fallback criptográfico de binding documental

## Objetivo y alcance

Proyectar, solo en local y sobre el snapshot M2 ya sellado, cuántos targets que
hoy terminan en `target_document_unresolved` pueden enlazarse de forma
inequívoca a un documento legacy. El diseño no escribe ni corrige
`documents.source_pdf_sha256`, no admite reuse y no autoriza vectores, modelos,
load, serving o deploy.

## Evidencia de partida

De 1.068 raws congelados, 646 no resuelven por el binding primario exacto a
`documents.source_pdf_sha256`. En el snapshot:

- 596 raws tienen base chunks con su `extraction_sha256`, todos con el mismo
  `document_id` no nulo, cuyo documento existe, está `active` y no declara un
  SHA PDF válido conflictivo; esos documentos contienen 16.540 filas legacy;
- 1 apunta a un documento activo con otro SHA PDF válido y debe rechazarse;
- 1 apunta a un documento `superseded` y debe rechazarse;
- 8 tienen algún base chunk con `document_id` nulo y deben rechazarse;
- 40 no tienen base chunks legacy.

Las 16.540 filas son filas **legacy**, no una estimación del número exacto de
filas locales que saldrán de las 17.074 unresolved. Ese número solo puede
obtenerse rematerializando la población local y ejecutando la proyección.

## Binding primario inmutable

El binding actual por SHA PDF exacto, único y `active` sigue siendo prioritario
y debe producir exactamente los mismos resultados y manifests que M2.6. El
fallback solo se evalúa si no existe ninguna fila `documents` con el SHA target;
no repara casos ambiguos, inactivos ni conflictivos del binding primario.

## Fallback fail-closed

Para un target previamente unresolved por ausencia de SHA PDF:

1. usar exclusivamente su SHA-256 de extracción raw congelado;
2. seleccionar en el snapshot todos los `chunks_v2` base con
   `parent_id IS NULL` y `extraction_sha256` exacto;
3. exigir al menos un base chunk;
4. exigir que **todos** tengan `document_id` no nulo;
5. exigir un único `document_id` compartido, sin desempate;
6. exigir una única fila `documents` para ese ID y `status='active'`;
7. exigir que `source_pdf_sha256` del documento sea ausente/placeholder; un SHA
   válido distinto es conflicto y se rechaza;
8. enlazar solo para la proyección local y conservar un recibo de provenance.

Quedan prohibidos filename, fuzzy matching, manufacturer, metadata, heurísticas
de contenido, mayorías y excepciones por documento.

## Taxonomía adicional

- `primary_pdf_sha_binding`
- `fallback_unique_active_donor_binding`
- `fallback_no_base_chunks`
- `fallback_null_document_id`
- `fallback_ambiguous_document_id`
- `fallback_missing_document`
- `fallback_non_active_document`
- `fallback_conflicting_valid_pdf_sha`

Cada raw cae en exactamente un terminal de binding. La suma debe ser 1.068.

## Probe local propuesto

Un runner nuevo reutilizará el snapshot gzip, raw store, sidecars, chunker,
language determinista y analyzer congelados. Ejecutará dos veces en procesos con
`PYTHONHASHSEED=1|2`, sin `.env`, DB ni red. Debe reportar:

- documentos y filas locales movidas desde unresolved por cada terminal;
- funnel downstream completo para la población expandida;
- strict candidates, ceiling no autorizante y workloads nuevos;
- delta exacto frente a M2.6, manteniendo byte-invariantes los bindings
  primarios;
- manifests de provenance y outputs byte-idénticos entre seeds.

## Gate

GO requiere invariantes cerradas, taxonomía exhaustiva, cero branching por
fabricante, cero acceso externo, determinismo cross-seed y revisión
adversarial. GO autorizaría únicamente diseñar la validación
metadata-independent/vectorial posterior; nunca admite reuse ni una migración
de base de datos.
