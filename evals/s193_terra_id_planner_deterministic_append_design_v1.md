# S193 — Planificador por IDs y apéndice determinista

## Hipótesis

El fallo dominante no es que el generador carezca de evidencia, sino que una obligación relevante
puede desaparecer entre selección y prosa. Se separan esas dos responsabilidades:

1. Terra selecciona únicamente IDs de relaciones tipadas ya ligadas a spans fuente.
2. La aplicación resuelve los IDs y anexa sus unidades fuente exactas a la respuesta base.
3. No hay una segunda redacción libre: un ID seleccionado no puede ser omitido.

El candidato es aditivo y conserva literalmente la respuesta Sonnet base. Esta forma experimental
permite medir el valor causal del planificador y garantiza cero regresiones textuales. No representa
el formato final para técnicos; un resultado positivo requerirá después un compilador de respuesta
legible y un gate fresco.

## Cohorte y contaminación

- Las mismas 14 preguntas de desarrollo S173, sin solapamiento con los cuatro targets.
- El selector ve pregunta y relaciones normalizadas, nunca gold, respuesta base ni exact quotes.
- El gold y las respuestas base solo se abren después de guardar los 14 checkpoints.
- El relation store tiene un techo local de 34/37 puntos; el experimento no lo modifica.

## Gate

- 14/14 selecciones válidas, hasta 12 IDs por pregunta, cero IDs inventados.
- Respuesta aditiva: al menos +4 puntos y +2 preguntas completas frente a la baseline.
- Cero puntos regresados y cero citas inválidas.
- Recall de puntos de las unidades seleccionadas >= 90% respecto al techo 34/37 del store.
- Precisión de unidades seleccionadas >= 75% y máximo 70 unidades totales.

Pasar solo autoriza diseñar el compilador legible y una validación en cohorte fresca. No autoriza
producción, target probe ni reclasificación de facts.

