# S244 — contrato de átomos fuente dentro del fragmento

## Decisión que este diseño puede cambiar

Autorizar o cerrar un experimento pequeño de representación **pre-respuesta** para
los `synthesis-miss`. No autoriza integración, cambio de default, crédito oficial
ni despliegue.

## Objetivo y métrica de hoy

- Denominador congelado: 157 hechos; 143 `OK` (91,08 %).
- Residual: 12 `synthesis-miss`; hacen falta 11 ganancias netas para 154/157
  (98,09 %).
- S243 atribuye 11/12 a pérdida de detalle dentro de un fragmento que la respuesta
  canónica ya citó y solo 1/12 a selección de fragmento.
- En el A/B S242, planner y baseline contemporáneo incluyeron los fragmentos que
  contienen 10/12 residuales. S242 obtuvo 0 ganancias estables, 3 regresiones
  protegidas y 1 conflicto inseguro: seleccionar fragmentos y luego pedir a un
  writer que invente obligaciones no resolvió el cuello.

Por tanto, la métrica inmediata no es retrieval ni `PASS`: es si una
representación source-bound conserva, con densidad acotada, las relaciones que
se pierden **dentro de evidencia ya seleccionada**. Solo un gate local positivo
autoriza medir después el delta end-to-end sobre los 12 hechos.

## Mecanismo propuesto, upstream → downstream

### A. Atomizador determinista source-bound

Entrada: texto exacto de un fragmento ya servido. Salida: átomos con ID estable,
categoría, uno o varios spans exactos y SHA-256; nunca claims parafraseados.

Detectores genéricos, sin nombres de producto ni tipos de relación de los targets:

1. `numeric_bundle`: valor + unidad y, cuando comparten cláusula, límites,
   tolerancia, paso/granularidad y ámbito.
2. `condition_dependency`: cláusulas `if/when/when all/until/before/after` y
   equivalentes ES, preservando condición, acción y target juntos.
3. `structured_member`: fila con cabecera, miembro de lista con su padre o
   definición `campo: significado`.
4. `mandatory_safety_verification`: requisito, prerrequisito, warning,
   comprobación, test o commissioning explícito.
5. `enumeration_cardinality`: aserción de cantidad y miembros enumerados; el
   validador no permite afirmar un count incompatible con los miembros visibles.

Invariantes:

- cada byte emitido se reconstruye exclusivamente desde spans del input;
- determinismo byte-a-byte e IDs ligados a identidad y contenido;
- ningún átomo individual supera 900 caracteres;
- máximo 48 átomos; el exceso falla cerrado, no trunca;
- se deduplican spans, pero se conservan varias categorías si aplican;
- ES/EN explícitos; cualquier otro idioma queda fuera del alcance medido;
- conflictos se etiquetan para disclosure y nunca se resuelven por precedencia.

### B. Gate local no-target ya versionado

Fuente: `evals/s171_s147_source_unit_gold_v1.json` más los excerpts congelados de
`evals/s147_fresh_source_packet_v1.json`: 14 preguntas, 37 answer-points, 14
fabricantes, estratos tabla y prosa, con `exact_quote` y receipts de spans.

Este cohort es independiente de `cat018/hp002/hp011/hp017`, pero **no es un
held-out virgen**: fue usado para evaluar mecanismos anteriores. Aquí solo mide
transferencia de forma fuente de un mecanismo nuevo; no demuestra mejora
end-to-end ni permite crédito oficial.

El código se escribe contra fixtures sintéticos ES/EN. Después se abre S171 una
sola vez y no se ajustan patrones/umbrales a sus fallos. Si falla, la versión v1
se cierra; cualquier v2 requeriría hipótesis causal nueva y otro cohort.

Gates pre-registrados:

- source-bound, hash, determinismo, límites y fail-closed: 100 %;
- recall de quote: al menos 34/37 (≥91,89 %) global;
- recall por estrato: ≥80 % tanto en tabla como en prosa;
- cobertura de las cuatro familias S243 mediante fixtures sintéticos: 100 %;
- no-trivialidad: unión de spans emitidos ≤70 % de caracteres no-blancos del
  cohort y mediana por item ≤75 %;
- control negativo sintético sin señales estructurales: cero átomos;
- cero acceso a los cuatro target qids durante el gate local.

`quote recall` significa que todos los caracteres no-blancos de la cita exacta
quedan cubiertos, en orden, por los spans de uno o más átomos del mismo item; no
basta compartir números o keywords.

### C. Canary end-to-end solo si B pasa

Tratamiento mínimo: mantener el contexto original y el writer de producción,
pero adjuntar antes de redactar únicamente los átomos source-bound detectados,
con instrucción de conservar los que respondan a la pregunta. No hay planner de
obligaciones, retry, addendum post-respuesta ni mutación determinista de una
respuesta ya escrita.

Orden de evaluación:

1. canary pareado pequeño no-target con hechos ya versionados;
2. si no hay regresión, 2 repeticiones por los cuatro qids del residual;
3. ganancia estable = el hecho mejora en ambas repeticiones;
4. antes de default-on: 143 hechos protegidos completos y disclosure neutral del
   conflicto `hp017` de menú 7/8.

Gate para continuar después del target probe: ≥3/12 ganancias estables, cero
regresiones protegidas, cero citas inválidas y cero conflicto resuelto de forma
unilateral. Es señal para escalar, no claim de 98 %.

## Diferencia frente a ramas cerradas

- S141/S153: no hay templates ni tipos de relación por producto; solo spans y
  estructura fuente genérica.
- S149/S150: no hay selector global ni loop de verificación de cobertura.
- S206: no es un checklist abstracto de facetas; cada ítem es contenido exacto
  ligado a spans del fragmento.
- S216: no descompone la pregunta ni genera respuestas por foco.
- S222/S223: ocurre antes del writer y no añade texto a posteriori.
- S235/S242: no pide a un LLM que autorice obligaciones; la representación nace
  determinísticamente del fragmento.

## Alternativas descartadas

- Otra búsqueda/rerank/selección global: métrica equivocada para 11/12 y 10/12
  fragmentos ya presentes en runs actuales.
- Repetir S242 con prompts: 0 ganancias y regresiones; sería tuning del mismo
  instrumento.
- Cambiar directamente a Sol/Fable como generador: S156 midió 2/13 y 4/13.
- Golds nuevos: no hacen falta para probar primero esta hipótesis.
- Marcar todo el fragmento: pasa recall de forma trivial y no reduce la carga de
  síntesis; lo impiden los gates de densidad.

## Riesgos y límites declarados

- El atomizador puede tener recall alto sin que el writer use los átomos: por eso
  B solo autoriza C, no integración.
- Keywords ES/EN pueden perder formulaciones raras u OCR defectuoso.
- Cabeceras/tablas mal extraídas siguen limitadas por la extracción upstream.
- Señalar demasiados átomos puede diluir la respuesta; densidad y regresiones son
  gates, no observaciones informativas.
- El residual de selección `hp011/F13` está explícitamente fuera de este lever.
- `chunks_v2` permanece `ACTIVE_READ_ONLY`; `chunks_v3` permanece
  `FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y solo línea explícita de evaluación.
- Railway es demo y no bloquea PR/merge con CI verde.

