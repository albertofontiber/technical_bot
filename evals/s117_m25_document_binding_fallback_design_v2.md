# S117 M2.5 — contrato de binding documental v2

Este documento conserva el mecanismo criptográfico de v1 y cierra taxonomía,
gramática, precedencia y baseline.

## Gramática de `source_pdf_sha256`

- SHA canónico válido: `str` que casa exactamente `^[0-9a-f]{64}$`.
- Único placeholder admitido para fallback:
  `^backfill:[0-9a-f]{64}$`.
- `null`, string vacío, tipos no string y cualquier otro valor son inválidos y
  fallan cerrados; no se reinterpretan como ausencia.

El snapshot contiene 423 SHA canónicos y 748 sentinels `backfill:`; no contiene
otros valores. Esta distribución se congela por manifest, no como una regla de
excepción para documentos concretos.

## Precedencia exhaustiva raw → terminal

Para cada uno de los 1.068 raws, en este orden:

### Binding primario

1. Buscar filas `documents` cuyo SHA canónico sea exactamente el SHA raw.
2. Si hay más de una: `primary_ambiguous_pdf_sha`.
3. Si hay exactamente una y no está `active`:
   `primary_non_active_pdf_sha` (desglosado por status).
4. Si hay exactamente una y está `active`: `primary_unique_active_pdf_sha`.
5. Solo si hay cero se evalúa fallback.

### Fallback

1. Cero base chunks con `extraction_sha256` exacto:
   `fallback_no_base_chunks`.
2. Algún base chunk con `document_id IS NULL`:
   `fallback_null_document_id`.
3. Más de un `document_id` distinto: `fallback_ambiguous_document_id`.
4. Para el único ID, cero filas `documents`: `fallback_missing_document`.
5. Más de una fila `documents`: `fallback_ambiguous_document_row`.
6. Documento no `active`: `fallback_non_active_document`.
7. `source_pdf_sha256` canónico distinto del target:
   `fallback_conflicting_valid_pdf_sha`.
8. Sentinel exacto `backfill:<64hex>`:
   `fallback_unique_active_backfill_binding`.
9. `null`: `fallback_null_pdf_sha`.
10. string vacío: `fallback_empty_pdf_sha`.
11. cualquier otro tipo/valor: `fallback_malformed_pdf_sha`.

Un SHA canónico igual al target después de que el primario encontrase cero es
una violación interna del snapshot y da NO-GO, no un terminal recuperable.
Cada raw cae en exactamente un terminal y la suma debe ser 1.068.

## Baseline primario preregistrado

Antes de implementar fallback, un runner en modo `freeze-primary` debe guardar
por raw:

- terminal primario (`unique_active`, `non_active`, `ambiguous`, `absent`);
- `document_id` y status cuando sean únicos;
- SHA-256 de un recibo canónico por raw y manifest global.

El baseline congela además hashes exactos de snapshot gzip/JSONL, raw store,
sidecars, prereg M2.6, ambos replay seed outputs y runner. El modo projection
debe demostrar byte-invariante el recibo primario de los 1.068 raws; solo los
`primary_absent` pueden entrar al fallback. Comparar agregados no basta.

## Evidencia diagnóstica no autorizante

Aplicando únicamente la precedencia observable al snapshot, entre los 646
`primary_absent` aparecen 596 candidatos `backfill` seguros con 16.540 **filas
legacy**, 1 conflicto SHA válido, 1 superseded, 8 con doc ID nulo y 40 sin base
chunks. El probe deberá calcular desde cero las filas **locales** movidas; no se
divide 16.540 por las 17.074 filas locales unresolved.

## Gate del probe futuro

Se mantienen todos los requisitos v1: ejecución local con seeds 1/2, cero
`.env`/DB/red/modelos/vectores, binding primario byte-invariante, taxonomía
cerrada, funnel downstream completo y outputs byte-idénticos. GO no admite
reuse ni DB writes; solo autoriza diseñar la validación metadata-independent y
vectorial posterior.
