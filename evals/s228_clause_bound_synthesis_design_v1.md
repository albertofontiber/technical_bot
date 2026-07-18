# S228 — síntesis por bloques ligados a cláusula y fuente

## Problema y diferencia estructural

La foto canónica permanece en **143/157 facts OK (91,08%)**: 12
`synthesis-miss` y 2 `retrieval-miss`. En los 12 de síntesis, la evidencia
decisiva llega al generador; el fallo es que una única redacción comprime u
omite relaciones, condiciones, excepciones o prerrequisitos.

S228 no reabre las líneas cerradas de reescritura/addendum ni S216. S216
dividía la pregunta sin ligar cada foco a fuentes y volvía a entregar todo el
contexto a cada escritor. S228 cambia la unidad de respuesta completa:

1. Terra 5.6 `low` ve la pregunta y unidades deterministas, exactas y ligadas a
   los chunks ya servidos. Devuelve 1–8 obligaciones y, para cada una, 1–5 IDs
   de unidades que la soportan. No ve respuestas, golds, QIDs de evaluación ni
   scorer.
2. Cada obligación se redacta en una llamada Sonnet 4.6 separada que solo ve la
   pregunta, la etiqueta no publicable de la obligación y sus unidades exactas.
   Devuelve claims estructurados y los IDs fuente usados; no genera citas.
3. Un validador local rechaza IDs desconocidos o fuera de la obligación. Un
   ensamblador determinista deriva las citas `[F<n>]` de los IDs, incluye cada
   bloque exactamente una vez y no hace ninguna reescritura final. Las
   etiquetas del planner no se publican.

La arquitectura evita tanto la competencia entre hechos en una redacción
monolítica como el borrado de contenido por un corrector posterior. No añade
texto fuente crudo al borrador: produce una respuesta técnica normal, pero cada
párrafo conserva un vínculo verificable a unidades concretas.

## Screen diagnóstico, no validación externa

El intento S227 de completar una cohorte Kidde externa se detuvo sin reintento:
Fable 5 alcanzó `max_tokens` en el primer ítem. Por tanto S228 usa únicamente
una población de desarrollo ya expuesta y **no puede autorizar targets ni
crédito oficial**:

- 7 preguntas multi-chunk históricas con 7 synthesis misses y 17 facts OK
  protegidos;
- 2 preguntas Kidde multi-source previamente aprobadas como guardrail, con 9
  facts;
- dos réplicas completas e independientes del tratamiento;
- generación y score físicamente separados: el runner no importa ni abre el
  score packet.

El presupuesto de salida por pregunta y réplica es agregado: 2.400 tokens
repartidos entre obligaciones. No se multiplica sin límite al aumentar los
bloques. Hay cero retries, cero resume, cero retrieval/DB y cero llamadas a los
12 targets.

El gate local exige al menos 3/7 gains estables (presentes en ambas réplicas),
cero regresiones en cualquiera de los 17 facts protegidos, Kidde no peor en
ninguna réplica, cero salidas inválidas, cero cortes por tokens, cero IDs o
citas fuera de contrato y coste inferior a $25. El matcher local solo abre una
revisión semántica ciega; no concede facts.

Un eventual review semántico oculta plan, mappings, métricas y nombre de brazo;
presenta pregunta, contexto y respuestas A/B con mapping aleatorio. Sol 5.6
`xhigh` es principal y Fable 5 el revisor independiente. Completitud, soporte,
consistencia o una regresión material son blockers. Incluso un PASS dual solo
justifica buscar una cohorte fresca; no abre targets porque S228 no es
independiente.

## Límites

- `chunks_v2=ACTIVE_READ_ONLY`.
- `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`.
- default de producción sin cambios; integración y despliegue prohibidos.
- Railway es demo y no condiciona PR o merge.
- no patch/tuning ni segunda ejecución sobre esta misma población.

## Decisión solicitada al dúo Frontier

Devuelve PASS solo si este único diagnóstico acotado puede medir de forma
honesta si la síntesis por bloques ligados a fuente recupera relaciones sin
regredir contenido. Devuelve FAIL únicamente con blockers concretos que puedan
producir un falso GO, fuga de score/gold, soporte fabricado, gasto no acotado o
una repetición material de una línea ya cerrada. No solicites convergencia ni
otra ronda de revisión.
