# S130 — gate v2 de adecuación e impacto de `chunks_v3`

Este documento sustituye el diseño v1, que quedó en **NO-GO-to-build** tras la
revisión adversarial. El gate es local, determinista y sin llamadas a modelos,
red, base de datos, contextualización ni embeddings.

## Decisiones que debe separar

El diagnóstico produce dos ejes independientes:

1. **S — almacenamiento/chunker**: `v3_adequate`, `v4_required` o
   `inconclusive`.
2. **P — proyección para retrieval**: `projection_not_required`,
   `projection_required` o `inconclusive`.

La combinación autoriza, como máximo, el diseño de una de cuatro ramas futuras:

| S | P | Rama candidata posterior |
|---|---|---|
| v3 adecuado | sin proyección | v3 |
| v3 adecuado | proyección requerida | v3 + proyección |
| v4 requerido | sin proyección | v4 |
| v4 requerido | proyección requerida | v4 + proyección |

Este gate **no autoriza por sí solo un A/B**, una migración ni un v4. Autoriza
prerregistrar la rama correcta y evita confundir pérdida de evidencia, fronteras
de chunk y ruido recuperable.

## Poblaciones y embargo

Población de desarrollo:

- los 1.068 registros del raw store S117 y sus 31.226 filas v3;
- los 100 bloques recuperados en los 27 documentos cambiados;
- los 157 claims reconciliados de S118/S125, incluidos los no medidos.

Antes de escanear contenido se materializa
`s130_chunks_v3_heldout_exclusion_manifest_v1.json`. Sus fuentes mínimas son los
freezes S114, S115 y S116 y cualquier cohorte marcada como held-out/holdout en el
registro de evaluación. El manifiesto debe:

1. resolver identidades exactas a `document_id`, `extraction_sha256`, PDF hash,
   nombre normalizado y revisión cuando existan;
2. expandir la exclusión por traducción, revisión, rebrand/OEM y documento
   relacionado usando únicamente relaciones de catálogo ya congeladas;
3. registrar colisiones y relaciones no resolubles;
4. excluir esas unidades de métricas, muestras y adjudicación de desarrollo;
5. revelar en el informe solo recuentos de exclusión, no resultados held-out.

Si una identidad conocida no puede resolverse de forma inequívoca, el gate queda
`inconclusive`; no se inspecciona ni se usa como desarrollo. Un cambio posterior
de chunker crea una versión nueva y solo entonces puede validarse sobre held-out
embargado.

## Carril A — mapa completo claim→fuente→bloque ganado

Bindings autoritativos:

- M1: `document_id`, página y support spans de
  `s125_m1_known_hold_contract_v1.json`;
- legacy: PDF/página/quote de `gold_answers_v1.yaml`, enlazados por basename
  normalizado exacto y página;
- `document_id→extraction_sha256`: freeze M2.5 de S117.

No se permite fuzzy matching silencioso. Una colisión queda `binding_collision`
y falla cerrada. Los 157 claims y los 100 bloques ganados deben acabar en una y
solo una disposición:

- claims: `outside_changed_documents`,
  `changed_document_no_gained_page_binding`, `gained_page_no_support_overlap`,
  `candidate_material_support_manual_review`, `binding_unresolved` o
  `binding_collision`;
- bloques: `material_support_for_non_ok_or_unmeasured`,
  `material_support_for_already_ok`, `context_only`, `surface_risk`,
  `no_claim_link`, `embargoed` o `unresolved`.

El solapamiento léxico solo propone candidatos. Para recibir crédito, una cita
exacta del texto ganado debe existir en el bloque raw y soportar materialmente el
claim; el chunk vecino no puede aportar ese crédito.

### Tabla de decisión de impacto

| Condición | Decisión |
|---|---|
| 157/157 claims y 100/100 bloques dispuestos; cero colisiones en evidencia positiva; al menos un span ganado material para un claim no-OK/no medido | existe señal para diseñar shadow v3 |
| Solo se beneficia evidencia ya OK o contexto no material | no pagar shadow por el KPI actual |
| Algún claim/bloque queda sin disposición o un positivo depende de binding ambiguo | impacto inconcluso |

La primera fila es señal de descubrimiento upstream, no convierte ningún fact en
OK ni autoriza producción.

## Carril B — adecuación corpus-wide de v3

Se rematerializa v3 desde el raw store congelado y se comprueba primero contra
los recibos M28/M29. Sobre la población no embargada se miden:

1. preservación exacta del stream de bloques y trazabilidad raw→fila;
2. fronteras `caption→tabla`, introducción→lista/procedimiento y continuaciones
   de sección;
3. lineage ausente, mezcla de ramas hermanas y headings repetidos compatibles
   con running headers;
4. filas de riesgo superficial: símbolos, números de página, tablas vacías y
   headers/footers repetidos;
5. metadata visual por todas las páginas de la fila, diferenciando screenshot de
   página completa de imagen/diagrama real.

Los proxies son **riesgos para adjudicar**, no “ruido semántico” demostrado. En
particular, los 87 bloques M29 sin regla permanecen sin juicio hasta revisión.

### Tamaño y truncación B8

El código vigente limita el texto enviado a B8 a 16.000 caracteres, incluyendo
`context + content`. Por tanto se separan:

- `definite_content_truncation`: `len(content) > 16.000`;
- `structural_oversize_only`: `7.000 < len(content) <= 16.000`;
- `pre_context_truncation_risk`: contenido que podría superar 16.000 al añadir
  contexto B7, sin declararlo pérdida todavía;
- `exact_post_context_truncation`: solo medible después de B7 con
  `len(context + content)` real.

El gate local pre-B7 no usa el umbral 7.000 como prueba de truncación.

## Gate para recomendar diseño v4

Se recomienda **diseñar**, no construir, v4 únicamente por una de estas vías:

### Vía hard correctness

Existe pérdida de contenido, binding raw→fila roto o truncación cierta causada
por composición/fronteras del chunker. El caso debe reproducirse desde raw y no
pertenecer a extracción, metadata, contextualización o retrieval.

### Vía sistémica

Se cumplen simultáneamente:

1. la clase pertenece a composición/fronteras del chunker;
2. afecta al menos al 1% de filas elegibles **después de limitar la contribución
   de cada documento al 10% del peso total**;
3. aparece en al menos 20 documentos, 3 componentes de linaje independientes
   tras colapsar revisiones/traducciones/rebrands y 2 fabricantes;
4. ningún documento aporta más del 10% de la evidencia ponderada;
5. existe una regla general sin fabricante, modelo, documento, qid, literal gold
   ni pregunta concreta;
6. una proyección no destructiva sobre v3 no puede resolver el problema.

Si el patrón no alcanza diversidad o materialidad, se registra como deuda/riesgo
sin abrir v4. Si se modifica el algoritmo, se congela v4 antes de mirar el
held-out y se valida después sobre él.

## Contrato de proyección para retrieval

La capa fuente permanece lossless: `content` y provenance son inmutables. Una
eventual proyección solo puede añadir:

- una disposición por bloque con regla y recibo;
- `retrieval_eligible`;
- un `retrieval_text` derivado, con hash de transformación y cobertura exacta de
  bloques fuente.

La misma proyección debe alimentar coherentemente contextualización, embeddings,
FTS, HYQ/enunciados y cualquier fusión. Las citas siempre se renderizan desde
`content`, nunca desde texto derivado. No se admiten reglas por fabricante,
modelo, documento o qid. El pipeline actual embebe todas las filas; por ello este
gate solo puede decidir `projection_required`, no afirmar que la proyección ya
está implementada.

## Contrato de paridad del futuro A/B v2↔candidato

El A/B posterior reconstruye ambos brazos desde el mismo raw store y en la misma
ejecución. Deben ser idénticos salvo chunker y, si la rama lo exige, la proyección
prerregistrada:

- snapshot raw, catálogo y metadata;
- prompt/modelo/configuración y política de caché B7;
- proveedor/modelo/dimensión/límite de B8;
- esquema, parámetros y población de índices vectorial y FTS;
- HYQ/enunciados, fusion, rerank, flags y límites;
- cohorte de consultas, filtros, top-k, seeds y recibos.

Se congelan hashes de cada componente y de cada fila contextualizada/embebida. Si
los embeddings v2 históricos no pueden reproducirse, ambos brazos se construyen
de nuevo; nunca se compara v2 histórico con v3 nuevo. M28/M29 solo prueban
materialización estructural y no sustituyen esta prueba semántica/retrieval.

## Crédito upstream→downstream

- chunking GO: evidencia material preservada sin regresión;
- retrieval GO: evidencia antes ausente entra en el pool, aunque termine como
  rerank- o synthesis-miss;
- rerank GO: entra en la ventana servida;
- synthesis GO: el claim queda cubierto sin invención.

Moverse entre etapas es progreso de esa etapa, pero ningún claim pasa a OK hasta
completar la cascada.

## Alternativas y riesgos

- **Solo comparar v2 y v3**: no detectaría un defecto nuevo y sistémico de v3.
- **Buscar v4 desde los fallos del benchmark**: contamina el diseño y favorece
  overfitting.
- **Migrar antes del A/B reproducible**: mezcla chunker, embeddings e índices.
- **Eliminar texto “feo” del almacenamiento**: destruye auditabilidad; el lugar
  correcto, si se demuestra necesario, es una proyección reversible.

Riesgos residuales: el raw store prueba fidelidad respecto de la extracción, no
del PDF visual; los proxies requieren adjudicación; las relaciones de
revisión/traducción/OEM pueden ser incompletas y en ese caso el resultado queda
inconcluso, no imputado.

## BP, estructura, escala y coste

Separar evidencia lossless, proyección recuperable e índice es un patrón
reutilizable y auditable. Los umbrales exigen alcance transversal y linajes
independientes, por lo que no dependen de los fabricantes actuales y escalan a
30+. La fase aquí descrita cuesta cero llamadas de modelo, red, DB o embeddings;
solo después de una señal material se autoriza diseñar el A/B mínimo.
