# S212 — binding completo por lotes compatible con el proveedor

## Causa y único cambio

S210 probó que el schema extractivo base es aceptado por Anthropic durante 88
llamadas, pero una respuesta con 17 claims chocó con el límite local de 16. S211
intentó expresar ese mismo límite como `maxItems`; Anthropic rechazó la propiedad
antes del modelo, con cero tokens y cero coste.

S212 conserva el schema proveedor-compatible de S210 y cambia solo la política
local ante más de 16 claims: valida la respuesta completa y liga todos los claims,
en orden, mediante lotes deterministas de hasta 16 que satisfacen el validador
congelado. Deduplica spans también entre lotes. El journal conserva la respuesta
cruda; al finalizar, el recibo enumera cada llamada que superó el límite legado,
conteo crudo, claims adicionales íntegramente ligados y hash.

No se descarta evidencia antes de los checks: cada claim queda sometido a schema,
exact source binding, deduplicación, planner por IDs, verificador, compilación
literal y scorer con recibo de span. La ejecución sigue acotada por los 2.200 tokens
de output por chunk, el prompt máximo de 100 KB y los topes 12+6 de selección.

## Integridad experimental

No se reutiliza ninguna llamada S210. S211 no produjo output target. S212 vuelve a
ejecutar las 202 llamadas completas sin retry/resume. La cohorte target tuvo
exposición parcial en S210; se declara y no permite afirmar generalización fresca.
No se cambian prompts, modelos, fallback, selector, verifier, compilador, scorer,
cohorte, réplicas, thresholds ni presupuesto.

Se heredan los gates: al menos 11/12 relaciones residuales estables, 4/5 de
`hp017`, cero regresiones/contradicciones cardinales nuevas, evidencia precisa,
citas válidas, prefijo baseline exacto, apéndice acotado y coste bajo techo. GO
local mueve cero facts y abre una única revisión atómica Sol 5.6 xhigh + Fable 5.
Solo acuerdo sobre al menos 11 facts permite proyectar 154/157. Runtime continúa
sin cablear/default-off hasta validación externa real.

La primera revisión de diseño S212 rechazó correctamente el recorte first-16 por
el riesgo de ocultar una contradicción. Este diseño lo sustituye por binding
completo y requiere una nueva decisión exacta de Sol xhigh y Fable. Un nuevo
fallo, NO-GO o ejecución incompleta cierra S212 sin modificación ni otra
llamada. `chunks_v2` permanece read-only, `chunks_v3` en
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`, y Railway nunca bloquea CI/merge.
