# S216 — síntesis descompuesta por pregunta

## Diagnóstico y mecanismo

El scoreboard canónico sigue en **143/157 facts OK (91,08%)**: 12
`synthesis-miss` y 2 `retrieval-miss`. En los 12 de síntesis, la evidencia
decisiva ya está servida. El generador actual recibe una pregunta compuesta y
todo el contexto en una sola llamada; una respuesta fluida puede comprimir u
omitir relaciones aunque la evidencia esté presente.

S216 cambia el contrato de ejecución, no el corpus ni retrieval:

1. Terra `low` ve únicamente la pregunta y la divide en 1–6 focos que cubren
   sus partes explícitas. No ve chunks, respuestas, golds, QIDs ni fallos.
2. Cada foco se responde en una llamada independiente al generador Sonnet 4.6
   real, con **todo el contexto servido original**. No hay selección de
   evidencia ni claim map.
3. Cada bloque conserva el alcance y producto de la pregunta original. Se
   rechazan citas fuera de los fragmentos servidos.
4. Un ensamblador local incluye todos los bloques exactamente una vez. No hay
   redactor final ni bucle de reparación que pueda volver a comprimirlos.

La arquitectura es distinta de las líneas cerradas: S154/S155 extrajeron
claims por chunk; S157/S173 detectaron omisiones después de un borrador;
S193/S210/S212/S213 seleccionaron o compilaron evidencia; S206 añadió un
ledger al mismo prompt monolítico. S216 no extrae, selecciona ni añade facts:
reduce el ancho de cada decisión de síntesis manteniendo intacta la evidencia.

## Evaluación sin target tuning

El primer screen reutiliza como desarrollo —no como validación externa— las 14
preguntas S173, 14 fabricantes y 37 answer points congelados antes de S216.
Sus baselines Sonnet 4.6 ya existen (26/37 puntos, 6/14 preguntas completas).
La generación S216 no puede abrir el gold hasta que todas las descomposiciones
y todos los bloques estén checkpointed.

El GO local exige simultáneamente:

- al menos +4 puntos y +2 preguntas completas;
- cero puntos previamente cubiertos perdidos;
- cero decomposiciones inválidas, `max_tokens` o citas fuera de rango;
- todos los focos ensamblados exactamente una vez;
- revisión semántica posterior e independiente de Sol 5.6 `xhigh` y Fable 5
  sin contradicciones, claims no soportados ni pérdida material frente al
  baseline.

El gate no puede mover facts canónicos. Solo un GO dual permite una nueva PR
que congele una ejecución única sobre `cat018`, `hp002`, `hp011` y `hp017`.
Esa ejecución exige después adjudicación atómica y regresión sobre los facts OK
protegidos. Una mejora target sigue siendo evidencia interna; antes de
`default-on` se requiere validación externa independiente.

## Límites operativos

- máximo 14 llamadas Terra y 84 llamadas Sonnet en el screen; cero retries;
- máximo interno $15 y techo del usuario $200;
- ejecución económica/local; Frontier solo para diseño y revisión crítica;
- ninguna lectura de DB, cambio de chunks, deploy o escritura en Railway;
- `chunks_v2` sigue activo y
  `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`;
- Railway es demo y no condiciona PR/merge con CI verde.

Un fallo cierra S216 sin ajustar el decomposer ni repetir el mismo corpus.
