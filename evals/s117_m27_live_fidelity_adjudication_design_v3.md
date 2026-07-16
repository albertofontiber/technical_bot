# S117 M2.7A — cierre contractual v3

Estado: **borrador para revisión adversarial final; no autoriza ejecución**.
Supersede M2.7A v2 exclusivamente en los puntos siguientes. La separación de
`raw_store_fidelity`, `legacy_semantic_relation` y policy congelada, sus
disposiciones fail-closed y la prohibición absoluta de autoridad M3/downstream
permanecen vigentes.

## 1. Fidelidad al raw store: autoridad documental, no del target aislado

`source_block_start/end` no contiene offsets dentro de párrafos o listas
oversized. Varios chunks correctos pueden compartir el mismo intervalo. Por
tanto, ni la omisión ni la cobertura se juzgan sobre el target aislado.

Para cada documento afectado, el runner debe:

1. regenerar con el chunker, materializer y validator congelados el stream
   completo y ordenado de chunks v3;
2. exigir igualdad fila a fila con la materialización local congelada: ID,
   ordinal, contenido, hashes, span, lineage y campos estructurales;
3. construir el stream raw ordenado de bloques y el stream v3 ordenado de
   chunks, y verificar bidireccionalmente bajo normalización exclusiva de
   whitespace que no existe omisión, duplicación ni reorder a nivel documental;
4. materializar para cada task su target y todos los chunks v3 cuyos intervalos
   solapen cualquiera de los bloques del target, con manifest de pertenencia,
   contenido completo y hashes;
5. incluir los bloques raw solapados y un bloque de frontera anterior/posterior
   cuando existan.

La regeneración prueba reproducibilidad; solo la alineación raw↔stream completo
prueba `raw_store_fidelity`. El target se declara `faithful` como miembro de un
stream documental verificado, no porque por sí solo cubra todo su span. Si la
alineación documental no cierra, el resultado es `unresolved` o `unfaithful`
solo cuando existe una contradicción positiva. Tablas/diagramas que no cierren
textualmente bajo la misma regla permanecen `unresolved` y no se rescatan por
similitud.

Esta prueba sigue limitada al JSON extraído. No afirma fidelity al PDF, al
render visual ni a LlamaParse.

## 2. Dos procesos distintos

### 2.1 Runner determinista y sin modelos

El runner de evidencia y el agregador mecánico realizan cero llamadas de red o
modelo. Dos procesos con seeds diferentes deben producir evidencia byte-identical
y el mismo logical hash. Esto certifica inputs, joins, manifests, alineación y
derivación mecánica; no certifica la verdad de una adjudicación experta.

### 2.2 Adjudicación experta con receipts

La adjudicación ocurre después de congelar la evidencia. Cada receipt sella:

- schema/version y hash del contrato de rúbrica;
- `task_manifest_sha256` y hashes exactos de toda evidencia consumida;
- reviewer method, identity, provider/model y parámetros;
- hash del prompt/instrucciones cuando aplique;
- los tres ejes, siete flags, root cause, rationale y citas exactas.

Warnings/safety, tablas, diagramas y cualquier `source_faithful_delta` exigen dos
revisiones independientes. Ambos reviewers reciben exactamente la misma
evidencia y rúbrica; el segundo no recibe ni puede referenciar el resultado del
primero. La independencia queda demostrada por dos receipts con identidades
distintas, `review_sequence` distinto y `prior_decision_visible=false`.

El agregador valida los receipts y decide mecánicamente. Cualquier diferencia
entre reviewers en `raw_store_fidelity`, `legacy_semantic_relation`,
`retrieval_policy_status` o cualquiera de los siete flags convierte la task en
`unresolved`. Nunca promedia ni elige una mayoría.

## 3. Secuencia autorizada

Tras GO adversarial de este diseño solo se autoriza:

1. implementar y testear el runner local de evidencia;
2. congelar prereg, código, tests e inputs por SHA-256;
3. generar dos seeds de evidencia y probar identidad;
4. producir fichas de revisión enlazadas a la evidencia completa;
5. congelar por separado el contrato de adjudicación antes de crear decisiones.

No se autoriza todavía llamar a modelos, importar decisiones, cambiar policy,
modificar chunks, ejecutar DB, generar contextos/embeddings ni desbloquear M3.
