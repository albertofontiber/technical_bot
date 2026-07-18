# S216 — síntesis descompuesta por pregunta (diseño corregido)

## Diagnóstico y mecanismo

El scoreboard canónico sigue en **143/157 facts OK (91,08%)**: 12
`synthesis-miss` y 2 `retrieval-miss`. En los 12 de síntesis, la evidencia
decisiva ya está servida. El generador actual recibe una pregunta compuesta y
todo el contexto en una llamada; puede comprimir u omitir relaciones aunque la
evidencia esté presente.

S216 cambia el contrato de ejecución, no el corpus ni retrieval:

1. Terra `low` ve únicamente la pregunta y la divide en 1–6 focos sobre sus
   partes explícitas. No ve chunks, respuestas, score packets, QIDs ni fallos.
2. Cada foco se responde en una llamada independiente al generador Sonnet 4.6
   real, con **todo el contexto servido original**. No hay selección de
   evidencia ni claim map.
3. Un ensamblador local incluye cada bloque exactamente una vez. Los textos de
   los focos son control data: se sustituyen por encabezados neutros `Parte N`
   y nunca entran en el candidato ni en el scorer.
4. No hay redactor final ni reparación. Cada bloque debe terminar normalmente,
   citar al menos un `[F<n>]` servido y no citar fuera de rango. La fidelidad
   semántica de la cita no se sobre-afirma: la revisa después el dúo Frontier.

La arquitectura es distinta de líneas cerradas: S154/S155 extrajeron claims
por chunk; S157/S173 detectaron omisiones después de un borrador;
S193/S210/S212/S213 seleccionaron o compilaron evidencia; S206 añadió un
ledger al mismo prompt monolítico. S216 no extrae ni selecciona facts: reduce el
ancho de cada decisión de síntesis manteniendo intacta la evidencia.

## A/B causal contemporáneo

S216 no compara contra respuestas históricas. Cada pregunta ejecuta dos
controles monolíticos y dos tratamientos descompuestos bajo el mismo commit,
modelo, system prompt, flags y contexto, en orden simétrico
`control-1 → treatment-1 → treatment-2 → control-2`.

Cada réplica dispone del mismo máximo agregado de salida: 1.600 tokens. El
control recibe 1.600 en una llamada; el tratamiento reparte por construcción
`floor(1600 / n_focos)` a cada foco. Por tanto, una ganancia no puede atribuirse
a multiplicar la capacidad máxima. El permit debe congelar exhaustivamente
todos los `frozen_inputs` del preregistro; una lista ausente, incompleta,
duplicada o divergente falla antes de cualquier llamada.

## Poblaciones y score isolation

El packet de generación está versionado y no contiene facts, answer points,
golds ni respuestas:

- **eficacia de desarrollo:** 14 preguntas S173 single-source, 14 fabricantes
  y 37 answer points ya usados antes de S216. Su reuso es deliberado y no
  independiente: la familia de screens puede sobreajustarse; un fallo cierra
  S216 y no permite sucesor sobre esos 37 puntos;
- **guardrail representativo multi-chunk:** las 35 preguntas S113 no-target,
  con 376 chunks servidos. Tras generación, un scorer separado abre los 87
  facts históricamente OK y veta cualquier regresión estable contemporánea.

El screen exige al menos 4 gains de punto estables (ambos treatment cubren y
ningún control cubre), 2 gains estables de pregunta completa, cero regresiones
de desarrollo y cero regresiones sobre los facts OK multi-chunk. El scorer no
se importa ni abre hasta que todas las generaciones están checkpointed.

## Revisión semántica obligatoria

Un GO local no autoriza targets. El contrato semántico congelado divide las 49
preguntas en siete batches y presenta a Sol 5.6 `xhigh` y Fable 5, de forma
independiente y cegada A/B:

- pregunta, focos como datos no confiables, todos los fragmentos y dos
  réplicas por brazo;
- ninguna métrica local, gold ni mapping de brazos;
- cobertura de partes explícitas y ausencia de scope añadido en el plan;
- soporte, completitud, fidelidad de citas y consistencia de ambos outputs;
- contradicciones entre bloques y pérdida material frente al otro brazo.

Cualquier blocker de cualquiera de los dos revisores produce NO-GO. Solo un
GO dual abre una PR separada para `cat018`, `hp002`, `hp011` y `hp017`. Una
mejora target aún exige adjudicación atómica, regresión protegida y validación
externa antes de `default-on`.

## Límites operativos

- 49 llamadas Terra; 196–686 llamadas Sonnet según focos; 14 llamadas Frontier
  solo si el gate local pasa; cero retries y cero resume;
- techo interno conjunto pre-target $150; techo del usuario $200;
- ninguna lectura de DB, cambio de chunks, deploy o escritura en Railway;
- `chunks_v2` sigue activo y
  `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`;
- Railway es demo y no condiciona PR/merge con CI verde.
