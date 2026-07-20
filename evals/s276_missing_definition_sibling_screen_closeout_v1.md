# S276 — closeout del screen offline seed-278

**Veredicto: `NO_GO_OFFLINE_SCREEN`.** No construir el mecanismo en runtime ni
gastar en una A/B pagada a partir de esta población.

## Resultado preregistrado

- Acceso: solo GET sobre `chunks_v2`; 0 modelos y 0 escrituras DB.
- Frescura: 80 documentos seleccionados, solape 0 con v1 + seeds 270–277.
- Censo: 1.033 fragmentos, 67 bloques parsables en 24 documentos.
- Distribución: 40 bloques con 1 hermano, 17 con 2, 7 con 3 y 3 con 4.
- Autoconsistencia de forma: 67/67 full y 67/67 con ítem seleccionado
  truncado se rederivan con el mismo parser que construye los positivos.
- Controles: 0/67 clean FP, 0/201 boundary FP, 0/67 oversize FP,
  0 cross-record FP, 0 receipts manipulados aceptados y 0 drift flag-off.
- Gate que falla: **2 fabricantes observados < mínimo congelado de 3**
  (Notifier 47 bloques, Morley 20). Todos los demás checks pasan.

El 100 % anterior es **autorrederivación determinista** de una mutación de forma
dentro de la gramática del propio parser; no valida independientemente el recall
de esa gramática, la mejora de respuestas ni la relevancia semántica. Los 201
boundary controls son mutaciones sintéticas: prueban el corte ante esos
separadores, no precisión sobre todos los límites naturales del corpus.

La revisión adversarial detectó dos límites adicionales de provenance. El gate
`sampled_docs` cuenta documentos seleccionados, no documentos con fragmentos no
vacíos; en esta ejecución sí se cribaron 1.033 fragmentos, pero el check no
implementa literalmente «documentos realmente leídos». Además, el build registra
los hashes actuales de cohortes previas sin compararlos fail-closed con el
preregistro, y ni el builder dependiente ni el snapshot del corpus quedaron
congelados de forma suficiente para demostrar que toda la cadena de freeze
precedió al GET. Los hashes de salida acreditan consistencia posterior, no esa
cronología completa.

## Pushback cualitativo posterior (no cambia el gate)

La inspección del artefacto congelado refuerza el NO-GO: 41/67 bloques (61,19 %)
caen dentro de descripciones bracketed de diagramas/imágenes, con etiquetas como
`Component A`, `Left side` o `Top right`; un solo documento aporta 20/67 bloques
(29,85 %). El prereg había declarado que «0 FP» solo cubría límites
estructurales, y esta observación demuestra por qué no puede reinterpretarse
como 0 daño semántico.

No se corrige el detector sobre seed-278 después de ver estos casos. Hacerlo
consumiría la población y convertiría el screen en ajuste post-hoc. Si en el
futuro se reabre esta familia, necesita una nueva semilla y preregistro con, como
mínimo, exclusión explícita de visual/UI-description, control de dominancia por
documento, freeze completo de builder/corpus/exclusiones, revalidación fail-closed
de hashes previos, conteos separados de docs seleccionados/con fragmentos/cribados
y una señal independiente de relevancia. Dado que su alcance causal
conocido sigue siendo solo 1/6 residuales, no es el siguiente lever recomendado
para buscar +5.
