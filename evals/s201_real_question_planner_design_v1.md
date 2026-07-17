# S201 — gate de planificación sobre preguntas técnicas reales preexistentes

## Decisión causal

El residual dominante sigue siendo `synthesis-miss`: 12 obligaciones repartidas
entre `cat018`, `hp002`, `hp011` y `hp017`. S193 demostró que un compilador
determinista puede añadir evidencia sin regresiones, pero el selector plano solo
alcanzó 79,41% de recall. S194–S200 no llegaron a evaluar el planificador
descompuesto porque la población de preguntas inventadas desde chunks falló antes,
en autoría o construcción de cohorte.

S201 cambia únicamente esa pieza upstream. No genera otra población artificial:
evalúa el planificador y el compilador ya especificados sobre preguntas benchmark
reales que existían antes de S194. Solo un GO abre el probe sellado de los 12
residuals.

## Cohorte y alcance de independencia

El builder parte de `s100_factlevel_full.yaml` y del contexto servido e inmutable de
`s113_full_contexts_freeze_v1.json`. Son elegibles preguntas con al menos dos facts
benchmark, sin consultar si alcanzaban generación ni su clase. Se excluyen antes de
seleccionar:

- los cuatro targets S141/S163;
- `cat007` y `cat013`, candidatos default-off de S172/S188;
- cualquier pregunta sin contexto servido o identidad primaria completa.

Con semilla fija se elige primero un item por fabricante y después se completa por
orden hash, sin repetir el par fabricante/producto normalizado. La selección no usa
respuesta, clase final, `reaches_gen`, salida de planificador ni resultado target. El
resultado es una cohorte de 12 preguntas, 8 fabricantes, 12 productos y 43 facts
benchmark. Incluye preguntas con soporte parcial o potencialmente nulo para que la
cohorte no quede condicionada a éxitos previos del pipeline.

Esta es una cohorte independiente del desarrollo source-first S173–S200 y no está
ajustada a los cuatro targets. No se presenta como un holdout secreto o nunca visto:
las preguntas son artefactos históricos visibles en el repositorio. La afirmación
medida es generalización a preguntas técnicas preexistentes y diversas, no
generalización externa a un corpus nuevo.

## Gold fuente y aislamiento del planificador

El packet contiene pregunta, identidad, contexts `chunks_v2`, hashes y manifests de
`EvidenceUnitV2`; no contiene claims gold ni respuestas. Después del freeze,
`claude-haiku-4-5-20251001` liga cada fact histórico al conjunto mínimo de IDs fuente
o lo declara sin soporte en el contexto servido. No redacta preguntas, respuestas ni
texto fuente. Todo ID, cardinalidad, contenido y span se valida localmente.

Un segundo modelo económico y de proveedor distinto, `gpt-5.6-luna`, valida sin ver
salidas del planificador cada decisión soportado/no soportado y cada conjunto fuente.
Puede registrar hasta tres conjuntos alternativos semánticamente equivalentes. Solo
se sella un punto cuando ambos modelos coinciden; cualquier desacuerdo u output
inválido cierra el gate antes del planner. La puntuación acepta cualquiera de los
conjuntos consensuados, no coincidencia ciega con un único conjunto Haiku.

El planificador `gpt-5.6-terra` con esfuerzo `low` recibe solo la pregunta,
identidades y unidades fuente. No ve claims, support IDs, baseline answers, clases,
targets ni métricas. Sus 12 outputs se sellan antes de reabrir el gold para puntuar.
No hay reintentos ni cambios de prompt o umbral sobre la cohorte.

## Gate upstream → downstream

1. **Población:** 12 preguntas, al menos 8 fabricantes, 12 productos únicos, 43
   facts benchmark, cero overlap target/default-off y `chunks_v2` exclusivamente.
2. **Gold dual:** cero outputs inválidos, cero desacuerdos semánticos y al menos 36
   puntos con soporte consensuado. Los no soportados se conservan como negativos y
   no se convierten en éxitos ficticios.
3. **Planificador:** recall de puntos >=90%, precisión de unidades >=80%, al menos
   75% de preguntas completas, como máximo 70 unidades seleccionadas y cero plans
   inválidos.
4. **Compilador local:** reconstrucción exacta desde spans, determinismo bit a bit,
   prefijo baseline intacto y cero citas inválidas.
5. **Probe target condicionado:** solo si 1–4 pasan se ejecutan `cat018`, `hp002`,
   `hp011` y `hp017`. Se revalidan todas las obligaciones S141 y conflictos
   versionados. Debe haber cero regresiones, cero conflictos nuevos, compilación
   exacta/determinista y al menos un residual nuevo cubierto antes de declarar PASS.

Las preguntas, chunks atestados, respuestas baseline, obligaciones y conflictos del
probe se materializan antes del freeze en un packet autocontenido. Durante la
ejecución pagada no se vuelve a resolver catálogo ni se regeneran obligaciones; el
veredicto consume ese packet y validadores deterministas también congelados.

Un GO sigue siendo local y default-off. No concede crédito oficial ni activa serving.
Antes de una integración runtime requiere revisión crítica principal con GPT-5.6 Sol
`xhigh`, revisión independiente con Fable 5 y una regresión completa fresca. Las
revisiones frontera no se usan para autoría, selección ni ejecución del benchmark;
si un proveedor no está disponible se registra una sola vez y no se converge por
reintentos sobre el mismo artefacto.

## Estados

- `GO_LOCAL_DEFAULT_OFF`: pasan holdout y target con cero regresiones; autoriza
  preparar integración default-off y revisión crítica.
- `NO_GO_GOLD_CONSTRUCTION`: el gold fuente no queda completo y válido; no se abre
  el planner.
- `NO_GO_REAL_QUESTION_GATE`: falla cualquier umbral del holdout; targets cerrados.
- `NO_GO_TARGET_SEMANTIC_REGRESSION`: pasa el holdout pero falla el probe target;
  crédito cero.
- `HOLD_EXTERNAL_DEPENDENCY_INCOMPLETE`: un proveedor no completa; se conservan
  checkpoints y se prohíbe repetir la cohorte.

## `chunks_v3`, KPI y despliegue

`chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`: recall@10 16/24 en ambos
brazos y MRR 0,4021→0,3694. S201 no materializa, migra ni parchea v3. Solo una
hipótesis estructural v4 con mejora de ranking sin pérdidas podría reabrir esa línea.

El denominador canónico no cambia durante el gate: 157 = 143 OK + 12
`synthesis-miss` + 2 `retrieval-miss`. S172 (+1) y S188 (+2) siguen siendo candidatos
diagnósticos default-off, sin doble conteo. No hay escrituras de base de datos,
migraciones ni despliegues. Railway es una demo y nunca forma parte del gate de PR o
merge cuando CI está verde.
