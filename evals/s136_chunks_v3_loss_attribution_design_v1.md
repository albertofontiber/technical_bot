# S136 — atribución local de pérdidas del shadow `chunks_v3`

## Objetivo

Explicar, sin cambiar cohortes ni gates, las tres pérdidas top-10 observadas en
S135 V2. El instrumento es diagnóstico: no promueve v3, no ajusta umbrales y no
mueve facts.

## Universo congelado

Se reconstruyen exactamente las poblaciones, planes de consulta y bundles de
S135 V2 desde sus inputs congelados. Solo se analizan los tres `question_id`
registrados como pérdidas en su gate.

## Atribuciones mecánicas

Para cada pérdida se publican:

1. rank del gold v2, rank completo del bundle v3 y ranks individuales de sus
   miembros;
2. igualdad de la superficie de tokens del gold v2 frente a la concatenación
   del bundle v3;
3. presencia o ausencia de contexto en cada miembro;
4. número de filas candidatas que quedan por encima del peor miembro gold,
   separadas entre donantes legacy exactos y filas nuevas/resegmentadas;
5. cuántas pertenecen al mismo documento;
6. contrafactual `strict-donor-only`: mismo ranking, pero retirando solo para
   diagnóstico las filas v3 que no tienen donante de contexto exacto.

El contrafactual no es una propuesta de serving: sirve únicamente para separar
una pérdida causada por el corte del gold de otra causada por la expansión de la
población sin contextos equivalentes.

## Taxonomía cerrada

- `evaluation_bundle_overstrict`: algún miembro está en top-10 pero el bundle
  completo exige además un fragmento sin términos de consulta;
- `candidate_population_competition`: el gold es idéntico y conserva contexto,
  pero filas candidatas adicionales lo desplazan;
- `gold_context_absent_after_resegmentation`: el gold se resegmenta y sus nuevos
  miembros carecen de contexto reutilizable;
- `mixed`: concurren dos o más mecanismos;
- `unresolved`: las comprobaciones mecánicas no permiten atribuirlo.

La clasificación se deriva de reglas explícitas, no de lectura semántica:

- bundle de más de un miembro, mejor miembro top-10 y bundle incompleto =>
  `evaluation_bundle_overstrict`;
- bundle de un miembro con superficie/contexto exactos y recuperación top-10 en
  `strict-donor-only` => `candidate_population_competition`;
- bundle resegmentado con algún contexto ausente =>
  `gold_context_absent_after_resegmentation`;
- múltiples condiciones => `mixed`.

## Límites

La atribución no decide qué competidores son semánticamente válidos ni cuál es
el fragmento mínimo que responde a la pregunta. Si eso fuera necesario, se
requerirá una adjudicación ciega separada. Esta fase usa PostgreSQL real local y
cuesta 0 USD: sin red, modelos, embeddings, APIs ni base remota.
