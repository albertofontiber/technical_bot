# S109 — integración post-rerank default-off

## Decisión

`GO_REAL_RUNTIME_5_OF_5_TO_DOWNSTREAM`, pero `NO DEPLOY` todavía.

Los cinco retrieval misses reales de la cohorte congelada llegan ahora al
generador por el camino de código del bot. Los dos facts CAT007 restantes ya se
habían atribuido en S108 a un defecto de medición, por lo que los siete retrieval
miss originales quedan explicados o desbloqueados sin cambiar el baseline oficial.

## Resultado por fact

| QID | Movimiento medido | Resultado downstream |
| --- | --- | --- |
| hp011 | retrieval → generator | synthesis miss |
| hp012 | retrieval → generator | OK candidato |
| hp013 | retrieval → generator | synthesis miss |
| hp014 | retrieval → generator | OK candidato |
| hp017 | retrieval → generator | OK candidato |

`OK candidato` exige hecho exacto y cita de uno de los fragmentos fuente que lo
soporta. No se convierte en OK oficial hasta superar regresión de los 93 OK
protegidos y los gates de release.

## Contrato implementado

- `POST_RERANK_COVERAGE=off` es el master switch.
- `STRUCTURAL_NEIGHBOR_COVERAGE=off` y
  `CANONICAL_HYQ_COVERAGE=off` habilitan cada lane por separado.
- El top-K del reranker es un prefijo protegido: no se reordena ni se modifica.
- Se añaden como máximo cuatro chunks y como máximo dos por lane.
- Structural neighbor exige mismo documento y mismo hash de extracción.
- HYQ queda limitado por el catálogo canónico, usa la prosa generada solo para
  navegación y sirve siempre el chunk padre real.
- Ambos lanes requieren spans fuente exactos y revalidación en el límite del
  generador; fallan abiertos sin interrumpir la respuesta.
- Railway no se modificó.

## Coste y verificación

- Retrieval/runtime: 0 llamadas de modelo, 0 escrituras de base de datos.
- Synthesis: 5 llamadas al generador, 0 llamadas al reranker, 0 jueces LLM.
- Tokens medidos: 86.524 entrada y 4.891 salida.
- Suite completa: 593 passed, 2 skipped.

Artefactos machine-readable:

- `evals/s109_post_rerank_runtime_replay_v1.json`
- `evals/s109_bounded_synthesis_runtime_pilot_v1.json`

## Siguiente gate

Atacar hp011 y hp013 como synthesis misses con un mecanismo general de cobertura
de obligaciones, y después ejecutar regresión protegida antes de considerar la
activación local o en Railway.
