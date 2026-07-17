# S190 — Contrato de activos visuales ligados a la fuente

## Decisión ejecutiva

El bot ya sabe transportar imágenes hasta Telegram, pero `chunks_v2` no tiene ninguna
`diagram_url` utilizable. No se debe reparar copiando la URL legacy a cada chunk: el activo
visual pertenece a una revisión documental y una página, no a una segmentación concreta.
Además, `has_diagram=true` en las 25.090 filas activas y una muestra visual contiene portadas y
material comercial; por tanto, la bandera no significa “diagrama técnico útil”.

La solución candidata es una tabla versionada de activos de documento, independiente de
`chunks_v2`, `chunks_v3` o un futuro `chunks_v4`, con unión exacta por documento y página.
La activación queda bloqueada hasta medir la utilidad visual con alta precisión.

## Evidencia medida, solo lectura

Fuente reproducible: `evals/s190_visual_asset_bridge_audit_v1.json`.

- Tabla activa: 25.090 chunks y 16.380 páginas documentales únicas.
- `has_diagram=true`: 25.090/25.090; `diagram_url` presente: 0/25.090.
- Registro legacy: 44.035 filas con URL, condensadas en 6.872 páginas.
- Join exacto `(document_id, page_number)`: 5.099 páginas.
- Join con una única URL y `source_file` exactamente consistente: 5.096 páginas.
- Ambigüedad de URL: 0 páginas.
- Alcance potencial: 7.685 chunks, 30,63% de las filas activas; 31,11% de sus páginas.
- Salud del almacenamiento: 30/30 URLs deterministas respondieron HTTP 200 y `image/jpeg`.
- Revisión visual diagnóstica, no estadística: 2/5 imágenes eran esquemas técnicos útiles;
  3/5 eran portada o material comercial. Esto veta un backfill ciego.

## Contrato propuesto

Entidad `document_visual_assets` (nombre provisional):

| Campo | Contrato |
|---|---|
| `document_id` | FK a la revisión documental exacta; nunca solo nombre de fichero |
| `page_index` | índice nativo del extractor, con `page_label` opcional separado |
| `asset_sha256` | identidad inmutable del binario |
| `storage_url` | localizador; su valor no constituye la identidad |
| `media_type`, `width`, `height` | recibo de transporte |
| `asset_scope` | `page_render` o `crop`; no fingir que una página completa es un diagrama |
| `visual_role` | vocabulario cerrado: `wiring`, `table`, `procedure`, `ui`, `product_photo`, `cover`, `marketing`, `other` |
| `technical_utility` | `useful`, `not_useful`, `uncertain`; `uncertain` no se sirve |
| `classifier_contract`, `classifier_receipt` | versión, evidencia y trazabilidad de la clasificación |
| `source_extraction_sha256` | une el activo a una extracción inmutable |

Restricciones:

1. Un activo se asocia al chunk solo en lectura mediante `document_id + page_index` y una
   extracción compatible. No se duplica su URL en cada generación de chunks.
2. Solo se sirven activos `technical_utility=useful`, con HTTP/Storage validado y cuya página
   pertenece a un fragmento seleccionado como evidencia para la respuesta.
3. Nunca se genera una imagen para sustituir el manual. Se entrega exclusivamente el activo
   exacto del documento fuente.
4. Máximo dos activos por respuesta. La respuesta de texto es independiente y falla abierta si
   Telegram o Storage no pueden entregar la imagen.
5. La leyenda muestra manual, revisión y página. No afirma que una página completa sea un crop.
6. No hay reglas por fabricante, modelo o pregunta; el contrato escala a 30+ fabricantes.

## Selección de alta precisión

La selección no dependerá del texto libre `DIAGRAMAS_RELEVANTES` como única autoridad. El
candidato debe combinar:

- evidencia servida y citada en la respuesta;
- intención visual genérica (`esquema`, `conexionado`, `tabla`, `diagrama`, `pantalla`, etc.);
- `visual_role` y `technical_utility` del activo;
- límite y deduplicación deterministas.

Una segunda vía podrá adjuntar una tabla aunque la pregunta no diga “tabla” cuando una obligación
de respuesta esté ligada explícitamente a una tabla y el activo sea `table`. Debe medirse por
separado para no degradar precisión.

## Gate S191 antes de cualquier escritura productiva

1. Congelar una muestra estratificada de al menos 60 páginas, mínimo 8 fabricantes y los roles
   `wiring/table/procedure/ui/cover/marketing`.
2. Etiquetar utilidad sin revelar la decisión del candidato. Usar un modelo económico de visión
   para ejecución y revisión frontera solo del contrato, discrepancias o stop-line.
3. Requerir precisión de adjunto ≥95%, cero portada/marketing servido y 0 cruces de
   documento/revisión/página. La falta de adjunto es preferible a un adjunto incorrecto.
4. Probar al menos 24 preguntas visuales y 24 controles no visuales, sin preguntas o reglas por
   fabricante creadas tras ver fallos del candidato.
5. Crear la migración y el backfill en una base desechable; validar apply, rollback, RLS y hashes.
6. Activar solo en shadow mediante un flag nuevo. `chunks_v2.diagram_url` permanece sin mutar.

## Fuera de alcance de S190

- No cambia el funnel factual ni mueve facts a `OK`.
- No autoriza producción, Railway, Supabase writes ni migración de chunks.
- No resuelve el 68,9% de páginas sin activo legacy; esas páginas requieren render desde el PDF
  exacto una vez que el contrato de activos haya pasado el gate.
