# S222 — corrección monotónica mediante addendum

S220 demostró que la detección source-preserving recupera los 7/7 facts de
síntesis de desarrollo, pero la reescritura completa perdió 3/17 facts ya OK y
una respuesta agotó tokens. S222 cambia solo el paso downstream: el borrador
queda byte a byte intacto y Sonnet redacta exclusivamente precisiones breves
apoyadas por las unidades ya seleccionadas a ciegas. La composición local añade
ese bloque al borrador; nunca lo reemplaza.

La propiedad de no regresión es estructural, no un scorer post hoc. El modelo
no ve facts, golds, clases de fallo, targets ni resultados S220. No se repite la
selección ni se cambian sus IDs. Este reuso sirve únicamente como desarrollo de
la capa downstream; un GO exige después el guardrail completo no-target antes
de cualquier target o producción.

`chunks_v2=ACTIVE`, `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no es
gate de PR/merge.
