# S110 — complemento determinista del pool tras rerank

## Decisión

`GO_RERANK_STAGE_8_OF_8`, con `HOLD_RELEASE`.

Los ocho claims atómicos que seguían bloqueados en rerank pasan al límite del
generador. No se declara ningún OK nuevo: el baseline oficial permanece en
`93/127`. Tres de esos ocho claims siguen fallando después en síntesis y el
provenance de ABORT en hp011 continúa abierto.

## Funnel reconciliado después de S109

De los once claims residuales adjudicados:

- `hp003.battery.two_12v_in_series` y
  `hp017.cause_effect.remove_default_rule_1` ya estaban en generador por S109.
- `hp013.config.stored_in_eeprom` sigue siendo retrieval miss: la fuente
  literal correcta no está en el pool congelado.
- Los ocho restantes eran rerank misses y S110 lleva los ocho a generador.

Además, S109 ya había reparado el provenance same-family de los dos claims de
hp018. `hp011.abort.same_family_provenance` no lo recupera este selector y no se
mezcla con la métrica de contenido.

## Mecanismo

- Carril `RERANK_POOL_COVERAGE`, estricto `on|off` y default `off`.
- Reutiliza únicamente el pool ya recuperado: cero modelos, cero consultas de
  embeddings y cero lecturas nuevas de base de datos.
- Mantiene el top-10 del reranker como prefijo inmutable y añade como máximo dos
  chunks, dentro del máximo global de cuatro.
- Restringe por catálogo canónico; acepta como fallback acotado un
  `product_model` exactamente equivalente cuando el documento aún está pendiente
  de adjudicación de catálogo.
- Usa intenciones técnicas versionadas bilingües y BM25F local sobre cuerpo y
  título; selecciona perfiles de necesidad distintos para evitar dos paráfrasis
  del mismo subtema.
- Une ventanas contiguas de tablas/formularios fragmentados sin generar texto.
- Exige al menos seis anclas de alineación y un receipt de span exacto.
- Rechaza índices y duplicados de una misma ubicación con similitud léxica alta.
- Structural, HYQ y pool entregan al generador únicamente los extractos exactos
  atestados, conservando el chunk padre completo para provenance.

No hay QIDs, valores gold, respuestas esperadas ni códigos de producto
inyectados en el selector.

## Medición barata y resultado

- Replay local sobre 39 preguntas: 8/8 claims de rerank llegan a generador.
- Runtime combinado real structural + HYQ + pool: 8/8; prefijos protegidos 11/11;
  máximo cuatro appends.
- Todos los chunks servidos pasan revalidación de span y frontera del generador;
  cero páginas tipo índice.
- En el replay pool-only, los extractos servidos representan el 22,98% de los
  caracteres de los chunks padre.
- Al comprimir también structural/HYQ, los siete prompts realmente cambiados
  bajan de 113.268 a 103.711 tokens de entrada (-8,44%).

La cohorte es conocida y el umbral se ajustó durante el desarrollo; por tanto
es un screen retrospectivo, no evidencia held-out de despliegue.

Tras la primera regresión pagada, la deduplicación se endureció para rechazar
solo duplicados de la misma ubicación con Jaccard >= 0,9, en vez de descartar
todo segundo chunk de esa ubicación. El replay final sigue recuperando 8/8 y
mantiene idénticos todos los candidatos de los cinco QIDs objetivo. La selección
solo cambia en `cat019` y `hp017`, dos preguntas de protección: por ello la
regresión pagada de esas dos preguntas no se considera evidencia de release
para el selector final. Se repetirá una sola vez, junto con la validación de la
mejora de síntesis, para no pagar dos veces por prompts que volverán a cambiar.

## Cascada downstream

La generación productiva se ejecutó solo sobre las once preguntas cuyo contexto
cambió. No se llamó al reranker ni a jueces:

- 70 de los 93 OK son bit-inertes porque su contexto no cambia.
- 23 OK requerían revisión de respuesta.
- En dos variantes generales de serving se conservaron 22/23, pero la única
  omisión cambió (`0,75 A` en v1; `750 mA` en v2). No hay regresión común.
- La revisión sigue siendo diagnóstica y no autoriza release: `cat019` y
  `hp017` deben repetirse con el selector final por el ajuste de deduplicación
  descrito arriba.
- Los targets downstream quedaron en 5/8: siguen como synthesis misses
  `hp009.loop.return_terminals` y las dos semánticas exactas de `r.I` en hp011.

Esto es coherente con el contrato upstream→downstream: el rerank está reparado;
la evidencia no se ha perdido y ahora el cuello de botella observable es la
síntesis. No se introduce ningún fix por QID para forzar 23/23.

## Siguiente paso

Diseñar una cobertura de obligaciones de respuesta que opere sobre claims
derivados de la pregunta y los spans servidos, empezando por los tres synthesis
miss recién expuestos. Después se repite una regresión acotada de las once
preguntas y solo entonces se considera activar el flag fuera de local.
