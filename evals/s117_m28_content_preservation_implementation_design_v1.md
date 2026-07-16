# S117 M2.8 — diseño de implementación de preservación de contenido v1

## Estado

Diseño sin autorización de implementación. No modifica el chunker, no genera
una materialización loadable y no autoriza DB, embeddings, serving, deploy, M3
ni facts `OK`.

## Base causal congelada

El probe M2.7C v2 demuestra sobre los 1.068 documentos que desactivar únicamente
el descarte `_meaningful_len(content) < 15`:

- recupera exactamente los 100 bloques ausentes;
- conserva los 333.061 bloques ya cubiertos;
- termina con 333.161/333.161 bloques cubiertos;
- cambia solo los 27 documentos esperados;
- mantiene fingerprints idénticos en los otros 1.041;
- pasa de 31.212 a 31.226 filas (+14);
- produce dos ejecuciones byte-identical con los cuatro estados `GO`.

La autoridad es la superficie whitespace-token de los bloques parseados del raw
store. No es una afirmación de fidelidad byte, PDF, visual o semántica del
extractor.

## Cambio mínimo propuesto

En `src/reingest/chunk.py`, `_cleanup` dejará de eliminar chunks en función de
longitud o `_meaningful_len`. Continuará:

- fusionando un chunk sub-`MIN_CHARS` con el anterior solo si comparten lineage,
  sus spans tocan, ninguno es flow diagram y no se supera `MAX_CHARS`;
- manteniendo aislados los flow diagrams;
- renumerando después los ordinals de forma contigua.

No cambia parsing, packing inicial, atomicidad, límites, lineage, page binding,
diagramas, deduplicación ni retrieval.

`_meaningful_len` se conserva como métrica diagnóstica. `NOISE_CHARS` puede
mantenerse temporalmente como constante de compatibilidad para reproducir
instrumentos históricos, pero no gobernará comportamiento productivo. No se
añade un nuevo umbral.

## Invariantes de implementación

1. Todo chunk no vacío que entra en `_cleanup` aparece en la salida, solo o
   fusionado; nunca se descarta.
2. La concatenación whitespace-token de salida es igual a la de entrada.
3. Cada span de salida cubre exactamente los bloques tocados por su contenido,
   validado mediante intervalos de tokens.
4. No se fusionan lineages distintos, gaps ni diagramas.
5. Códigos, títulos, valores, unidades, estados, operadores y símbolos cortos
   se preservan por defecto.

## Identidad versionada

El cambio produce un nuevo SHA del chunker y, por tanto, un manifest y
`materialization_id` nuevos. Está prohibido reutilizar el ID v3 baseline o
presentar las filas M2.7C diagnósticas como loadables.

La materialización candidata se construirá directamente con el nuevo chunker,
no mediante override. El baseline se toma de sus artefactos congelados; no se
intenta reejecutar el runner histórico bajo el código nuevo.

## Gates locales previos a promoción

### Gate unitario

- short alphanumeric, heading, numeric, sentinel y symbol-only se preservan;
- merges válidos conservan texto, lineage y span;
- lineage/gap/diagram barriers permanecen;
- oversized shared y oversized+tail merge pasan binding por intervalos;
- reorder, duplicación y span desplazado fallan;
- regresión completa verde.

### Gate corpus-wide

Contra los inputs ya congelados:

- 1.068 documentos y 333.161 bloques exactos;
- 31.226 filas candidatas;
- manifest, IDs y receipts deterministas en dos seeds;
- 333.161 bloques cubiertos, cero exclusiones y cero pérdidas;
- ganancia exacta de las 100 identidades M2.7B;
- ningún bloque previamente cubierto regresa;
- 27 documentos cambiados y 1.041 fingerprints estables;
- delta de filas reconciliado exactamente con M2.7C v2;
- 0 red, DB, modelos, contexto o embeddings.

### Repetición live M2.7A

Los 21 casos con evidencia completa se vuelven a enlazar a la materialización
candidata. Para GO upstream se exige 21/21 documentos y tasks alineados. Esto no
mueve automáticamente ningún fact a `OK`: un fact puede progresar después a
`rerank_miss` o `synthesis_miss`.

## Separación de retrieval

Preservar una fila no implica que deba ser recuperable. La clasificación de
retrieval es una fase posterior e independiente:

- se reutilizará `register_only`, no una clase nueva, si una regla estructural
  llega a demostrar layout puro;
- se persistirán `retrieval_policy_reason`, payload y receipt recalculable;
- context, embedding y search vector serán `NULL` para no elegibles;
- cualquier ambigüedad permanece preservada y no recibe una exclusión nueva
  por layout; continúa aplicando su clase independiente existente;
- no habrá reglas por fabricante, documento, UUID ni los 14 textos observados.

La fase C se evaluará sobre la materialización candidata completa y con
controles negativos técnicos. No bloquea medir primero la corrección upstream,
pero sí bloquea carga/serving.

## Secuencia

1. revisión adversarial y preregistro de implementación;
2. cambio mínimo + tests;
3. materialización candidata local en dos seeds;
4. ledger corpus-wide y M2.7A sobre candidata;
5. diseño/gate `register_only`;
6. solo entonces cascada retrieval → rerank → synthesis y decisión de carga.

Un fallo conserva el baseline actual y produce `NO_GO`; no se ajustan reglas o
expectativas tras observar los resultados.
