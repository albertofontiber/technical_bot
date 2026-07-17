# S189 — piloto del writer con índice relacional completo

## Hipótesis

S186 extrajo relaciones que cubren 34/37 puntos del cohort independiente, pero
el selector Haiku redujo esa cobertura a 28/37. Un writer puede recibir el
índice completo del único chunk recuperado, junto a los spans fuente exactos,
eliminando esa pérdida de selección sin añadir un bucle agéntico ni otra
llamada query-time.

## Piloto causal y límites

- Cuatro items de desarrollo ya adjudicados, dos de tabla y dos de prosa, con
  seis omisiones posibles en el baseline.
- Máximo cuatro llamadas al writer de producción (`claude-sonnet-4-6`),
  temperatura cero, sin reintentos.
- Las relaciones son navegación semántica no probatoria; cada una se entrega
  con las unidades exactas que la sustentan. La respuesta solo puede citar el
  fragmento fuente F1.
- Gold y baseline se cargan para scoring únicamente después de checkpointar
  todas las respuestas candidatas.
- GO de desarrollo exige ganar al menos tres puntos, cero regresiones, cero
  citas inválidas y cero cortes por límite de tokens.
- Un GO no autoriza targets ni runtime: obliga a una cohorte fresca antes de
  cualquier promoción. Un NO-GO cierra el patrón de "todas las relaciones" sin
  tuning sobre el mismo cohort.

## Riesgo principal

El texto de las relaciones fue generado en ingesta. Aunque está ligado a spans
exactos, podría sesgar al writer. Por eso el piloto conserva y muestra el texto
fuente, prohíbe usar el índice como evidencia y no puede promoverse sin una
auditoría de fidelidad independiente.
