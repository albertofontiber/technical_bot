# S275 — Preflight de serving-view generalizada

**Estado:** diagnóstico local completo; ningún build de runtime, ningún target
reabierto y ninguna ejecución de pago autorizada.

## Resultado primero

La expansión de serving-view tiene un alcance causal directo conocido de **1 de
los 6** residuales, no de +5. El artefacto reproducible
`s275_serving_view_reach_preflight_v1.json` compara cada span exacto de S235 con
la vista congelada S113:

| obligación | vista del predicado | cobertura | lectura causal |
|---|---:|---:|---|
| `obl_2f5d79e354b9` | coverage card | 100 % | ya se sirvió completo; omisión de selección/cita |
| `obl_7bba8d03d496` | prefix completo | 100 % | ya se sirvió completo; no es truncación |
| `obl_a5d9fa1f9253` | prefix completo | 100 % | ya se sirvió completo; no es truncación |
| `obl_015f9b9aaa3a` | prefix completo | 100 % | ya se sirvió completo; no es truncación |
| `obl_b2043cd4379b` | coverage cards | **0 %** | la definición de entrada queda totalmente fuera |
| `obl_7aa723717412` | coverage cards | **86,68 %** | hay clip final, pero los 3 anchors del matcher ya están servidos; su causa es binding/cita |

La evidencia no autoriza afirmar que una vista más amplia convertirá siquiera
`b2043`; solo demuestra que el mecanismo actual no puede transmitirlo. El clip
de `7aa7` no explica su miss actual porque `instrucción de salida`, `todas las
condiciones de entrada` y `equipos asignados` ya están en la parte servida. Los
cuatro spans al 100 % y `7aa7` necesitan otra
familia (planificación/selección o evaluación orgánica), no más caracteres.

## Candidato mínimo

El candidato estructural mínimo es una **bounded missing-definition-sibling
card**, análoga a la card C1 ya existente:

1. Si una card validada intersecta un ítem Markdown de definición (`* Etiqueta:`)
   dentro de un bloque explícito, contiguo y homogéneo, detectar si un hermano
   del mismo bloque quedó totalmente fuera.
2. Servir como máximo **un hermano omitido** y completo; en F12 es
   `Instrucción de entrada`, mientras `Instrucción de salida` ya está servida.
3. Guardar la card en campo propio, con flag default-off y receipt que la
   rederive byte a byte. No mutar `served_coverage_cards` ni heredar
   `local_semantic_validated` del selector.
4. Mantener paridad: generador y must-preserve ven la misma vista exacta. Nunca
   leer el chunk completo como fallback.

No se propone un clasificador semántico target-specific ni una lista de términos
PEARL. La unidad es un registro de lista con límites estructurales verificables.

## Gates offline antes de gastar

Una preregistración sucesora debe congelar, antes del build:

- censo de todos los chunks de coverage validados: candidatos, tamaño añadido,
  fabricantes y distribución de 1–4 hermanos;
- flag-off byte-idéntico y receipts fail-closed, incluyendo tamper tests;
- máximo de 1 card y 600 caracteres; STOP ante cruce de heading,
  tabla, indentación o bloque no contiguo;
- cohorte de mutaciones nueva y disjunta (semilla candidata 278, aún no usada):
  recall de ítem truncado y hermano omitido, con **0 expansiones a elementos no
  pertenecientes al mismo registro** en clean;
- regresión sobre suites S274 y smoke estructural, sin tocar DB ni generar.

Solo si todo eso es GO se revisaría un diseño de ejecución con el dúo adversarial.

## Medición posterior permitida

El probe #5 sobre los seis targets está cerrado por el compromiso anti-overfit
S274. Por eso una validación pagada tendría que usar preguntas reales frescas y
disjuntas u observación orgánica, con OFF/ON contemporáneo, mismos documentos y
gates de cero daño. Los targets actuales no pueden bankarse a partir de esta
preflight ni de una simulación de spans.

Presupuesto orientativo heredado del handoff: unos USD 10 para la fase pagada;
esta cifra necesita autorización y preregistración nueva. El censo, el build
flag-off y la cohorte mecánica pueden hacerse localmente sin coste de modelos.

## Decisión informada

- **Si la prioridad es calidad estructural del producto:** construir y gatear
  offline el cierre de registros de lista es razonable; su valor no depende de
  prometer 98 % inmediato.
- **Si la prioridad es alcanzar 98 % en el funnel actual:** este lever no basta
  por sí solo; su alcance causal directo conocido es 1 y aún quedarían al menos
  +4 incluso si convirtiera.
- **Si la prioridad es evitar más optimización sobre los mismos seis casos:** el
  siguiente árbitro correcto es evaluación orgánica con técnicos y, en paralelo,
  resolver el KPI atómico oficial que sigue `null` por los carries legacy.
