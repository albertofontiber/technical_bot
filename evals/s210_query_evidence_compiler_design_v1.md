# S210 — compilador extractivo condicionado por pregunta

## Objetivo y evidencia causal

La foto comparable permanece en 143/157 facts OK, con 12 synthesis-miss y dos
retrieval-miss. El mayor sub-bucket es `hp017` (cinco relaciones). S210 intenta
recuperar al menos 11 de las 12 relaciones residuales de forma estable, incluidas
al menos cuatro de `hp017`, sin cambiar retrieval ni enseñar al mecanismo IDs,
valores, modelos o vocabulario de los targets.

No se repite una línea cerrada. S155 mostró en una cohorte independiente que la
extracción condicionada por pregunta encontraba 32/37 answer points, pero con
precisión insuficiente (62,5%). S193 mostró que seleccionar IDs y compilar sus
spans exactos daba +5/37, +2 preguntas completas y cero regresiones, pero el
selector plano recordó solo 27/34 puntos disponibles. S210 compone esas señales:
pool extractivo de alta cobertura → selección de IDs → una verificación de
cobertura → compilación determinista. No vuelve a probar un writer libre, un
ledger de facetas, un relation store offline ni otro holdout de preguntas Kidde.

## Mecanismo limpio

1. Haiku 4.5 inspecciona cada chunk ya servido junto con la pregunta y propone
   claims atómicos. Cada claim debe incluir una cita contigua exacta. El código
   liga la cita a offsets reales; las filas inválidas se descartan y nunca llegan
   al planner o a la respuesta.
2. En paralelo, un fallback local y bilingüe ya versionado aporta hasta doce
   spans query-relevant. No genera valores ni recupera documentos nuevos.
3. Terra 5.6 `low` ve solo la pregunta y candidatos con IDs opacos. Selecciona
   como máximo doce. Una segunda llamada, con rol de verificador, puede añadir
   como máximo seis sin quitar lo ya seleccionado. No redacta la respuesta.
4. El compilador local reproduce cada span elegido, con su fragmento `[F#]`, en
   el orden seleccionado. La respuesta baseline es un prefijo byte-idéntico: un
   ID elegido no puede ser omitido ni puede borrar un claim previo.

El módulo no contiene `cat018`, `hp002`, `hp011`, `hp017`, fabricantes, modelos,
números esperados ni los nombres de las 12 relaciones. Los scorers sí conocen el
gold, pero se abren solo después de sellar todas las respuestas.

## Medición y límites honestos

Se ejecutan dos réplicas completas por pregunta. La cohorte pagada contiene los
cuatro targets y las 14 preguntas S173 como guardrail aditivo: 130 extracciones,
36 planes y 36 verificaciones, 202 llamadas máximas, `max_retries=0` y sin
resume. Los 14 ítems S173 fueron observados por mecanismos anteriores; por ello
solo prueban no-regresión/ruido y no cuentan como generalización fresca.
Antes de la primera llamada, el runner calcula un techo conservador de la
ejecución completa: cobra cada byte UTF-8 de los prompts extractivos como un
token, el límite duro de 100.000 bytes de cada plan/verificación y todos los
outputs a su máximo. Si ese total no queda por debajo de 75 USD, aborta con cero
llamadas.

El GO local exige simultáneamente:

- al menos 11 relaciones residuales target nuevas y estables en ambas réplicas;
- al menos cuatro de las cinco relaciones `hp017` estables;
- la relación target previamente cubierta sigue cubierta en ambas réplicas;
- cero contradicciones cardinales nuevas respecto al baseline, citas inválidas
  o prefijos baseline alterados; el conflicto cardinal ya presente sigue siendo
  deuda y no se presenta como resuelto;
- cero regresiones en los 37 answer points del guardrail;
- precisión de evidencia seleccionada ≥70% y apéndice medio ≤5.000 caracteres;
- coste real por debajo del techo sellado.

Un GO local no mueve facts todavía. Abre una única revisión atómica de resultados:
Sol 5.6 `xhigh` como principal y Fable 5 como independiente comprueban source
support, entailment, contradicciones y utilidad de cada ganancia estable. Solo
acuerdo completo y ≥11 facts aceptados permite proyectar 154/157. Incluso en ese
caso la integración de runtime continúa default-off hasta un gate de preguntas
reales externas; este experimento no es evidencia fresca de generalización.

Un NO-GO cierra la composición sin cambiar prompts, umbrales, modelos o cohorte.
No se reintenta ni se postseleccionan respuestas favorables.

## Invariantes

- `chunks_v2` es la fuente activa y no se escribe en base de datos.
- `chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE` como línea explícita.
- No hay preguntas ni golds nuevos, por lo que no aplica otra autoría pixel-PDF.
- Railway es demo y nunca bloquea PR o merge con CI verde.
- Sol 5.6 `xhigh` es revisor principal; Fable 5 es el otro Frontier independiente.
