# S192 — Control causal Terra como generador directo

## Pregunta

¿Sustituir únicamente `claude-sonnet-4-6` por `gpt-5.6-terra` mejora las omisiones de
síntesis cuando pregunta, evidencia servida y contrato del generador permanecen idénticos?

## Diseño

- Cohorte de desarrollo S173: 14 preguntas, 14 fabricantes, 7 tablas y 7 fragmentos de
  prosa; solapamiento cero con las cuatro preguntas objetivo.
- Un único brazo candidato con Terra y razonamiento `low`.
- Mismo `build_prompt` de producción y un solo fragmento fuente por pregunta.
- Cero retrieval, reranking, herramientas, consultas a base de datos, reintentos o ajuste
  posterior.
- Las respuestas se guardan antes de cargar el gold y la baseline para puntuar.

Este control no es una propuesta de producción. Aísla el efecto del modelo. Si falla, no se
sube el razonamiento ni se modifica el prompt sobre esta cohorte. El siguiente mecanismo será
arquitectónico: selección de obligaciones tipadas por identificador y renderizado que no pueda
omitir identificadores seleccionados.

## Gate de desarrollo

- 14/14 respuestas completas, sin parada por límite de tokens.
- Ganancia de al menos 4 de los 37 puntos de respuesta frente a Sonnet 4.6.
- Al menos 2 preguntas completas adicionales.
- Cero puntos que Sonnet cubría y Terra pierda.
- Cero citas a fragmentos inexistentes.

Pasar solo autoriza diseñar una validación fresca y medir coste/latencia. No autoriza cambiar el
modelo del bot, desplegar ni reclasificar facts.

