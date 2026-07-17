# S191 — Gate ciego de utilidad de activos visuales

## Hipótesis

Un clasificador visual económico, ejecutado una sola vez durante la ingesta y no en cada query,
puede distinguir activos técnicos útiles de portadas/marketing con precisión suficiente para
habilitar un registro documental de imágenes. El criterio es deliberadamente conservador: una
imagen omitida es menos dañina que una imagen incorrecta enviada a un técnico de campo.

## Cohorte congelada

`evals/s191_visual_utility_cohort_v1.json` contiene 60 activos exactos, 12 fabricantes y cinco
estratos de 12 elementos: primera página, wiring, procedure, specification y other. La selección
se hizo antes de cualquier label, con hash de binario, documento, página y URL, sin preguntas del
ruler ni reglas por fabricante.

## Patrón advisor–executor

1. **Executor económico:** `claude-haiku-4-5-20251001` clasifica seis lotes de 10 imágenes. Solo
   devuelve vocabulario cerrado, confianza y una razón de máximo 12 palabras. Cero reintentos.
2. **Política local:** candidato a servir únicamente si Haiku devuelve `useful`, confianza
   `high`, visual técnico legible y rol `wiring/table/procedure/ui`.
3. **Advisor/revisor frontera:** solo si el executor produce entre 10 y 30 positivos válidos,
   una llamada a `gpt-5.6-sol` xhigh y una a `claude-fable-5` xhigh revisan exclusivamente esos
   positivos, con imágenes, sin ver entre sí sus decisiones. Cero rondas adicionales.
4. **Intersección segura:** cualquier desacuerdo o `uncertain` se excluye; no se corrige el
   prompt ni se repite la misma cohorte.

## Gate

- 60/60 filas con recibo válido del executor y hashes intactos.
- Positivos Haiku entre 10 y 30; fuera de ese rango se considera calibración no informativa.
- Precisión adversarial conjunta ≥95% sobre positivos Haiku.
- Cero portada, marketing o foto de producto aprobada para servir.
- Cero cruce de documento/página/hash y cero activos inaccesibles.
- Si una llamada frontera es incompleta, el resultado es HOLD, no retry.

Pasar el gate solo autoriza diseñar y probar en base desechable el registro
`document_visual_assets`; no autoriza backfill productivo, flag, deploy ni movimiento de facts.

## Presupuesto

- Haiku: máximo 6 llamadas, coste interno máximo $2.
- Sol: máximo 1 llamada, coste conservador máximo $3.
- Fable: máximo 1 llamada, coste conservador máximo $5.
- S191 total: stop-line $10, muy por debajo del techo global del usuario.

Las llamadas frontera son el gate de seguridad de una funcionalidad visible, no iteraciones de
diseño. No se llama a ambos modelos si el screen barato falla.
