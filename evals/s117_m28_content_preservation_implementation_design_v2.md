# S117 M2.8 — addendum adversarial de implementación v2

Este addendum supersede v1 donde precise compatibilidad, spans, baseline, M2.7A
y Phase C. Sigue sin autorizar implementación, DB, load, serving ni M3.

## Compatibilidad, no replay

`NOISE_CHARS` podrá permanecer únicamente para compatibilidad de import/API de
instrumentos históricos. Ni `_cleanup` ni `chunk_document` podrán leerlo.
`_meaningful_len` seguirá disponible como métrica, pero no podrá gobernar
branches productivos.

El código nuevo no reproduce el override histórico. La única autoridad baseline
y treatment son los artefactos congelados; reejecutar runners antiguos bajo el
chunker candidato está prohibido.

## Diff exacto permitido

En producción solo se retira:

1. el branch que descarta por `_meaningful_len < NOISE_CHARS`;
2. `merge_barrier` y la condición asociada, que solo existían para impedir una
   fusión a través de contenido descartado;
3. comentarios/docstrings que afirman que chunks cortos se eliminan.

No se permite otro cambio a parse, packing, `TARGET_CHARS`, `MIN_CHARS`,
`MAX_CHARS`, atomicidad, split, lineage, merge o diagramas.

La barrera de merge es `is_flow_diagram`. `has_diagram` no es barrera y se
propaga con OR como en el baseline.

## Preservación antes de mutación

Los tests capturan el stream de tokens y metadatos de entrada antes de llamar a
`_cleanup`, porque esta función puede mutar el chunk previo durante un merge.
Después se exige:

- todo chunk no vacío queda solo o fusionado;
- tokens de salida iguales a los de entrada, en orden;
- spans forman el envelope de los bloques tocados;
- mismo full lineage para merge;
- adyacencia o overlap legítimo de un bloque shared/oversized, nunca gap;
- no merge ante lineage distinto, gap, flow diagram o exceso de `MAX_CHARS`;
- anchor, path, lineage, flags y ordinals contiguos permanecen coherentes.

El validator por intervalos acepta oversized shared y oversized+tail; rechaza
omisión, duplicación, reorder y span shifted/overclaimed.

## Baseline e identidad candidata

Baseline congelado:

- chunker SHA `4b76ab219854c625f4ce5e55665e2c89d14739e4eee0ab01607aae7ecda4fd43`;
- materialization ID `eb426a33-91cb-543e-a0c9-fd615dbc36cb`;
- 31.212 filas y rows manifest
  `68e87fd43702fcf53f14ff7fbdbe65e4faa346977a199ff7427333b8cab950f3`.

La candidata debe tener chunker SHA, generation manifest, materialization ID e
IDs de fila nuevos. No puede heredar IDs baseline ni diagnósticos M2.7C.

La comparación candidate↔baseline usa los artefactos congelados como datos. La
proyección semántica excluye identidades generacionales antes de comparar
contenido/spans/lineage; las identidades nuevas se validan por separado.

## Oracle causal no ajustable

31.226 filas es el oracle de equivalencia al treatment M2.7C v2, no un objetivo
que pueda ajustarse. Además del count se exige igualdad exacta de manifests y
multisets semánticos contra la proyección congelada:

- 1.068 documentos y 333.161 bloques;
- candidate 31.226;
- cobertura 333.161/333.161 y cero pérdida/reorder/duplicación;
- ganancia exacta de las 100 identidades y cero regresión;
- 27 documentos cambiados y 1.041 estables;
- delta 2.529 unchanged, 15 removed, 29 added, 15 overlap-modified y 14
  pure-added.

Cualquier diferencia es `NO_GO`; no se modifica el oracle después del run.

## M2.7A corregido

La población live correcta es 18 documentos afectados y 21 tasks. La
recomputación fresca local contra candidata y evidencia congelada exige:

- 18/18 documentos alineados;
- 21/21 tasks alineadas;
- task manifest y receipts exactos;
- resolución exacta del extraction
  `8d128ca2ca13754bb74e0dcf16014e74141e352ae819aa25e35784c2f60245f6`;
- similarity rescue prohibido;
- 0 red, DB o modelos y 0 facts `OK`.

## Phase C fuera de scope

M2.8 no cambia retrieval policy, schema, `register_only` ni clasificación de
layout. La cobertura upstream no descuenta filas por su política de retrieval.
La candidata conserva la clasificación independiente existente y no inventa
exclusiones nuevas.

Phase C tendrá prereg propio corpus-wide, predicado estructural, negativos
técnicos, `reason`/payload/receipt, default preserve y prohibición de selectores
por fabricante, documento, UUID o los 14 literales observados. Hasta entonces
load y serving continúan bloqueados.
