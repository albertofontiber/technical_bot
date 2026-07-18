# S223 — auditor monotónico con contexto completo

S220 mostró que una reescritura con contexto completo encuentra relaciones que
el selector por fragmento no marcó, pero puede borrar o contradecir contenido.
S222 mostró que el addendum preserva el borrador, pero hereda los falsos
negativos del selector. S223 combina las dos propiedades útiles sin sus fallos:
una sola llamada de auditoría ve pregunta, borrador y todo el contexto servido,
y devuelve únicamente precisiones aditivas. La composición local conserva el
borrador byte a byte.

No hay selección de evidencia, claim map, descomposición, loop, targets ni
golds visibles. El GO local solo permite revisión semántica dual y después un
guardrail completo no-target. No autoriza producción ni crédito oficial.

`chunks_v2=ACTIVE`, `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no
condiciona PR o merge.
