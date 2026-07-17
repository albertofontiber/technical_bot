# S194 — descomposición de pregunta y compilación exacta desde unidades fuente

## Objetivo y causalidad

El bucket diagnóstico dominante contiene **12 `synthesis-miss`**. S193 aisló
el cuello de botella: el apéndice determinista ganó +5/37 puntos y no produjo
regresiones, pero el selector plano recuperó solo 27/34 puntos soportados
(79,41%, por debajo del 90% preregistrado). S194 conserva el renderer local y
cambia una sola pieza upstream: antes de elegir evidencia, el planificador debe
descomponer la pregunta en subobligaciones explícitas y ligar cada una a IDs de
unidades fuente inmutables.

No se reutiliza el relation store global: S170 y S186 ya cerraron esa vía como
NO-GO corpus-wide. La unidad de selección será `EvidenceUnitV2`, reconstruible
desde spans del chunk y con encabezado de tabla cuando corresponda. El modelo
no redacta respuesta ni texto fuente; un compilador local copia literalmente
las unidades seleccionadas y añade citas `[F1]`.

## Cohorte fresca y aislamiento

S168/S170 se conserva únicamente como evidencia de desarrollo. No decide
S194 porque ya fue observado y no satisface la orden canónica de cohorte
fresca.

El gate decisivo congela, antes de crear preguntas o golds, **14 chunks vivos
de `chunks_v2`** (7 tabla y 7 prosa) de fabricantes y documentos distintos.
La selección es determinista desde una lectura GET-only de Supabase y excluye:

- documentos, chunks y pares fabricante/modelo usados en los packets
  versionados anteriores;
- UUIDs y documentos presentes en los artefactos target S141–S163 y S173.

Los textos de esas preguntas no participan en la selección fuente. Esto prueba
aislamiento documental/UUID, no ausencia de parecido semántico accidental entre
preguntas; ese overlap semántico queda explícitamente como `NOT_MEASURED`.

El packet registra hash de cada excerpt, hash estable del conjunto elegible,
conteos de la lectura, cero escrituras y un manifest pre-autor de cada ID,
tipo, span y hash de unidad. El runner falla cerrado si la reconstrucción no
coincide con ese manifest. Las preguntas se escriben después del freeze por
`claude-haiku-4-5-20251001`, un modelo económico. Debe producir de dos a cuatro
puntos materiales y uno a tres IDs fuente por punto. El
planificador usa otro proveedor/modelo económico, `gpt-5.6-luna` con reasoning
`none`. Esta elección de esfuerzo es una apuesta medida, no evidencia previa.

El ejecutor Luna recibe pregunta, identidad y unidades; nunca ve claims gold,
support IDs, respuestas target ni puntuación. Devuelve como máximo 12
subobligaciones y 18 IDs únicos conocidos. Todos los planes y sus hashes quedan
checkpointados antes de abrir el gold para puntuar. No hay reintentos ni ajuste
de prompt o umbrales sobre la cohorte.

## Gate upstream → downstream

1. **Fuente:** 14 items, 14 fabricantes, 14 documentos, 7 tabla, 7 prosa y
   cero overlap con desarrollo/targets.
2. **Autor económico:** al menos 12 preguntas elegibles, 12 fabricantes,
   5 tablas, 5 prosas y 24 puntos; cero outputs inválidos.
3. **Planificador descompuesto:** 100% de outputs válidos, recall de puntos
   soportados >=90%, precisión de unidades >=80%, preguntas completas >=75%,
   <=70 selecciones totales y cero IDs inventados o cruces de identidad.
4. **Compilador local:** contenido reconstruido exactamente desde spans,
   determinismo bit a bit en dos ejecuciones y cero citas inválidas.
5. **Probe target condicionado:** solo si 1–4 pasan se abren los cuatro targets
   congelados. Se compila el mismo tipo de apéndice y se revalidan **todas** las
   obligaciones S141, no solo los 12 residuals. Ninguna obligación previamente
   cubierta puede dejar de estarlo ni puede aparecer un conflicto nuevo que los
   contratos versionados `build/validate_answer_conflicts` detecten.
   Solo después se cuentan residuals convertidos a cubiertos.

El techo observado con el validator actual es 11/12: la reconstrucción oracle
existente cubre 4/5 obligaciones de `hp017`. Esto no prueba que todo apéndice
futuro sea incapaz de resolver la cardinalidad; simplemente impide prometer el
facto duodécimo en este tramo.

## Estados de decisión

- **GO_LOCAL_DEFAULT_OFF:** pasan fuente, autor, planificador, compilador y
  probe target, con cero regresiones semánticas. Autoriza implementar el seam
  runtime default-off y ejecutar regresión completa fresca; no autoriza serving,
  producción ni crédito oficial.
- **HOLD:** una dependencia externa no completa una llamada o el artefacto
  target resulta materialmente incompleto. Se conserva el checkpoint y no se
  repite la misma cohorte.
- **NO-GO:** falla cualquier umbral, aislamiento, identidad, exactitud o no
  regresión. Si ocurre upstream, los targets permanecen cerrados.

El prefijo byte-idéntico del baseline se registra como propiedad del compilador,
pero no cuenta por sí solo como no regresión: decide la revalidación semántica
de todas las obligaciones ya cubiertas.

## Línea explícita `chunks_v3`

S140 permanece como `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`: recall@10 empató
16/24 y MRR empeoró 0,4021→0,3694. S194 no rematerializa ni migra v3. Todos sus
resultados incluirán un brazo explícito `chunks_v3_lane` con ese baseline,
`changed_by_s194=false` y el único trigger admisible: una hipótesis estructural
v4 que mejore ranking sin pérdidas por fabricante/heldout. No se permiten
parches por pregunta.

## Frontera de autorización

Este tramo no convierte el denominador híbrido de 157 en KPI atómico ni borra
los 77 legacy carries. Tampoco promociona los candidatos S172/S188, que aún
necesitan generalización independiente. No hay escrituras de base de datos,
migraciones, cambios de tabla, despliegues ni llamadas frontera de ejecución.
Railway sigue siendo demo: un fallo de deploy no forma parte del gate y no
puede bloquear PR o merge con CI verde.
