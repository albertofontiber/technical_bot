# S117 M2.7C — diseño de chunking con pérdida explícita

## Estado y autoridad

Documento de diseño, no autorización de cambio. No autoriza modificar el
chunker congelado, regenerar `chunks_v3`, llamar a modelos, acceder a red o DB,
crear embeddings, cargar, servir, desplegar ni mover facts a `OK`.

## Evidencia que obliga el cambio

El audit M2.7B cubrió exactamente 1.068 documentos, 31.212 filas v3 y 333.161
bloques raw. El contrato y el ledger pasaron, pero quedaron 87 pérdidas sin
regla en 22 documentos. La proyección compacta determinista las descompone en:

- 62 separadores de guiones bajos;
- 3 artefactos Markdown sin contenido alfanumérico (tabla vacía y reglas);
- 5 números cortos;
- 7 títulos cortos;
- 10 códigos o rótulos alfanuméricos.

El origen común es `_cleanup`: elimina cualquier chunk con
`_meaningful_len(content) < 15`. La misma condición borra layout vacío y texto
potencialmente técnico como `ACM-32A`, `UCIP - MODBUS` o `Event Data`. Longitud
no demuestra ruido semántico.

## Invariante objetivo

Para todo bloque no vacío del raw store debe cumplirse exactamente una de estas
condiciones:

1. sus bytes de texto están representados, en orden, en una o más filas de la
   materialización; o
2. existe una exclusión versionada, determinista, receipted y recalculable desde
   la forma del raw, cuya regla no contiene selectores de fabricante, producto,
   documento, UUID, hash de extracción ni literales observados ad hoc.

Una heurística de longitud nunca puede producir por sí sola la condición 2.

## Separación de responsabilidades

### Capa A — raw store

Es la evidencia inmutable. Nunca se reescribe durante este cambio.

### Capa B — materialización de contenido

Debe conservar por defecto todo bloque no vacío. El packing puede fusionar
chunks pequeños únicamente si mantiene orden, texto, lineage y spans exactos.
No puede eliminar contenido por longitud.

El primer tratamiento que se medirá desactiva solo el descarte
`_meaningful_len < NOISE_CHARS`; no introduce reglas nuevas ni modifica
parsing, packing, lineage, atomicidad o límites de tamaño.

### Capa C — proyección de retrieval

Presencia en la materialización y elegibilidad para retrieval son decisiones
distintas. Una fila preservada puede clasificarse como no recuperable mediante
la política estática receipted. Ninguna fila nueva se cargará ni servirá hasta
que esa proyección tenga un contrato cerrado.

La política actual no contiene una clase específica de layout. Por tanto el
probe de Capa B no autoriza considerar automáticamente `eligible` sus filas
nuevas. Una fase posterior comparará dos opciones:

- registrar layout puro como `register_only`; o
- añadir una clase cerrada `layout_only` no elegible.

La elección se hará contra la población real de chunks del tratamiento, no
contra los 87 bloques usados para descubrir el fallo. Los candidatos de reglas
solo podrán describir formas sintácticas de alta precisión. Códigos, títulos,
unidades, valores, estados y texto alfanumérico corto serán controles negativos
obligatorios.

## Probe local anterior a cualquier implementación

El probe contrafactual será offline y determinista:

1. usa exactamente los 1.068 raw records del manifest congelado;
2. materializa baseline con el chunker congelado;
3. materializa treatment con el mismo código y parámetros salvo descarte por
   longitud desactivado;
4. compara por documento el número de filas, spans, contenido y cobertura de
   bloques;
5. publica todas las filas añadidas con texto, hashes, lineage, spans,
   `_meaningful_len` y una taxonomía sintáctica diagnóstica;
6. verifica que todo bloque que M2.7B marcó como pérdida pasa a estar cubierto;
7. no adjudica ruido, no cambia la política y no afirma calidad de retrieval.

Dos seeds deben producir payload lógico y bytes idénticos. La perturbación solo
puede alterar el orden de entrada antes de restaurar el orden canónico.

## Gates fail-closed del probe

- población exacta: 1.068 documentos y 31.212 filas baseline;
- manifest baseline exacto al M2.7B congelado;
- cero cambios en documentos no afectados salvo renumeración derivada de filas
  añadidas dentro del mismo documento;
- cero bloques no vacíos sin cobertura en treatment;
- texto raw reconstruible en orden desde treatment;
- toda fila treatment valida contra raw, lineage y spans;
- conjunto de documentos y bloques recuperados exactamente igual a las 100
  exclusiones/pérdidas observadas por M2.7B, salvo que el packing conservador
  cubra además bloques ya cubiertos sin alterar sus bytes;
- hashes y receipts recalculables;
- 0 llamadas de red, DB o modelos y 0 hechos movidos a `OK`.

Un incumplimiento produce `NO_GO`; no se corrigen umbrales después de ver el
resultado.

## Decisiones explícitamente rechazadas

- reducir `NOISE_CHARS` a otro umbral;
- añadir excepciones por los 22 documentos o por los textos observados;
- autorizar como ruido todo contenido sin caracteres alfanuméricos;
- fusionar a través de lineages o gaps para ocultar una pérdida;
- cargar las filas del tratamiento como elegibles antes de cerrar Capa C;
- usar un LLM para decidir qué descartar.

## Secuencia de promoción

1. revisión adversarial y preregistro del probe Capa B;
2. dos ejecuciones locales deterministas del probe;
3. diseño y controles negativos de la proyección Capa C;
4. implementación local conjunta de preservación + política de retrieval;
5. repetición del ledger corpus-wide M2.7B con cero pérdidas no regladas;
6. repetición de M2.7A sobre los 21 casos live;
7. solo tras gates y regresión completa, evaluar rematerialización o carga.

Esta secuencia acepta progreso por etapa: recuperar un bloque aguas arriba es
una mejora válida aunque el fact pase después a `rerank_miss` o
`synthesis_miss`. No se contabiliza como `OK` hasta superar el funnel completo.
