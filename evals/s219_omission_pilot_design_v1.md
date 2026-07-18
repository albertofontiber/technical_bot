# S219 — screen causal de corrección post-respuesta

El residuo canónico sigue en 143/157: 12 `synthesis-miss` y 2
`retrieval-miss`. La evidencia de los misses de síntesis ya llega al generador;
el patrón común son relaciones incompletas (condiciones, excepciones,
prerrequisitos, límites o consecuencias), no contexto tardío ni falta de
recall.

S219 no diseña otro selector. Ejecuta sin cambios la arquitectura genérica
source-preserving de S157, que no llegó a evaluarse en multichunk porque su
autor externo solo produjo 2/12 preguntas elegibles. Tras el borrador normal,
Haiku compara por fragmento la pregunta y el borrador contra unidades fuente
inmutables; solo devuelve IDs. Si detecta omisiones, Sonnet 4.6 hace una única
revisión con el contexto completo, el borrador y el texto original de esas
unidades. No hay loop, reescritura de evidencia, reglas por QID ni cambios de
retrieval.

El screen separa físicamente generación y score. La generación no importa el
scorer ni abre facts/golds. Usa siete `synthesis-miss` multichunk históricos
no-target solo como población de desarrollo, más dos preguntas Kidde
multi-manual cuyos candidatos principales habían sido aprobados pixel a pixel
por Fable en S215. Estas dos son un guardrail útil, no una validación externa
independiente ni publicación de golds.

GO exige recuperar al menos 3 de los 7 facts omitidos, cero regresiones en los
17 facts históricamente OK de esas preguntas, cero regresiones en los 9 facts
Kidde, cero citas fuera de rango, cero salidas inválidas y cero cortes por
tokens. Un GO solo abre el guardrail completo de las 35 preguntas no-target;
no abre todavía targets ni producción. Un NO-GO cierra esta línea exacta sin
convergencia ni reparación posterior.

`chunks_v2` permanece activo. `chunks_v3` conserva el cierre explícito
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. Railway es demo y no condiciona PR o merge.
