# s86 · B2 — método para el cluster RECALL-INTRADOC (8/14)

> Brief de propuesta (Protocolo 2) + input del dúo adversarial (Protocolo 3). Zona de
> dolor = retrieval → cross-model GPT-5.5 INNEGOCIABLE además del sub-agente Opus.

## Objetivo de HOY (con MÉTRICA)
Reducir el cluster **RECALL-INTRADOC = 8/14** del **retrieval-miss family-aware** (instrumento
s85, DEF.yaml pinneado, juez GPT-5.5 K=5). NO PASS (diferido a síntesis, DEC-071e). La métrica
de éxito = el chunk-valor **entra al pool family-tie** (in_pool_target=true) en la re-derivación.

## Diagnóstico a nivel-chunk (verificado, DEF.yaml + chunk_index de la DB)
Los 8 misses INTRADOC: el chunk-valor **existe en el manual correcto** (juez ≥4) pero **0 entran
al pool**. No es chunking-roto (el chunk existe) ni FN del instrumento (0 huérfanos). El chunk-valor
está casi siempre **adyacente** (por `chunk_index`) a un chunk que el retriever SÍ trajo del mismo doc:

| miss | DIST_MIN valor↔pool (mismo doc) |
|---|---|
| cat016/autobúsqueda · hp006/Tierra · hp012/2-lazos | **1** |
| hp006/ISO-X · hp013/PWR-R | **2** |
| hp011/05-295seg · hp014/35 | **6** |
| hp006/Fallo-Tierra | 12 (AFP-300 ausente; vía AFP-400) |

Cobertura acumulada por ventana ±W: **W=1→3/8 · W=2→5/8 · W=6→7/8 · W=12→8/8**.

**Insight clave:** varios valores son token-corto/bare (hp014 "35", cat013 "CLIP") = chunks de baja
findability propia PERO con vecino findable. El recall por adyacencia NO depende de la findability
del chunk-valor, solo de la de un vecino → ataca la raíz del token-corto within-doc.

## Recomendación: NEIGHBOR-WINDOW / parent-document expansion
Tras el merge de canales (o en el diversify per-doc), para cada chunk recuperado de un doc de
**familia-objetivo**, traer sus vecinos `chunk_index ∈ [i−W, i+W]` del mismo `source_file` y
añadirlos al pool. BP RAG estándar (sentence-window / parent-document retrieval, LlamaIndex/LangChain).

- **BP + estructural (raíz):** ataca el mecanismo medido (chunk-valor adyacente pero bajo el corte),
  no un gold. **Escalable:** puramente posicional (chunk_index + source_file), 0 config por-modelo/fabricante.
- **Anti-overfit:** no referencia ningún gold; augmentación de retrieval genérica.
- Punto de inserción: `retrieve_chunks` / `_diversify_by_source_file` (`retriever.py`).

## Alternativas consideradas (y por qué se descartan como método primario)
1. **Denser per-doc FTS** (subir `limit` en `_fetch_top_chunks_by_source_file`): usa relevancia de
   CONTENIDO. Pero los valores fallidos son bare/token-corto = baja findability por contenido → misma
   causa del miss. NO resuelve el token-corto. (Descartada como primaria; complementaria.)
2. **Subir POOL_K global:** fuerza bruta, no targetea within-doc, diluye el pool; el chunk-valor
   rankea bajo *globalmente* por ser within-doc → poco eficiente.
3. **HyDE-global:** el manual YA se encuentra; B1 lo excluyó explícitamente (within-doc ≠ global).
4. **Re-chunking / chunks más grandes / table-aware:** re-ingest corpus-wide, pesado, no quirúrgico.

## Gaps / riesgos declarados de entrada
- **Techo ≠ 8/8:** W=2 solo da 5/8; hp006/Fallo-Tierra (dist 12, AFP-300 ausente) queda fuera de W chico.
- **Bloat del pool:** ±W por cada chunk recuperado multiplica el pool → riesgo aguas-abajo (rerank/gen,
  PASS diferido) y de truncamiento por POOL_K. Mitigable: expandir SOLO docs de familia-objetivo, W chico,
  dedup, cap por-doc.
- **La métrica es in_pool (no PASS):** neighbor-expansion mete el chunk al pool = resuelve el
  retrieval-miss por definición; el impacto en síntesis/PASS es otro workstream (DEC-071e).
- **Coste de re-medición:** re-derivación family-aware dirigida sobre los 8 golds = barata (juez solo
  sobre el delta del pool), NO re-correr los 39 (feedback_cost_discipline).
- **Interacción con model-filter:** los vecinos deben sobrevivir `_filter_to_query_models` (mismo doc
  familia-objetivo → deberían pasar; verificar que no los expulsa).

## Check de lever-métrica (Protocolo 2.5 / Protocolo 4)
- **DEC-056** (RANKING levers agotados) — métrica PASS/RERANK. Neighbor-window = **RECALL**, no ranking
  → lever DISTINTO (el digest repite "el RECALL es lever DISTINTO"). NO colisiona.
- **within-doc diversify (C7, s82)** = candidato NUNCA construido/medido → no-settled. Fresh.
- El `diversify` actual reparte entre source_files/fabricantes; **no** hace expansión por vecindad →
  el método es nuevo, no re-litigación.

## VEREDICTO (s86, medido — dúo-hardened + A/B jitter-controlado)

**Neighbor-window en RETRIEVAL-stage = NO-GO.** A/B W0-vs-W2 (jitter-controlado, 39 golds):
broad **+4/−29**, restringido-a-familia **+4/−26**. Inyectar en pool-fijo POOL_K=50 es zero-sum
(cada vecino expulsa cola con value-chunks de otros facts). No hay diseño retrieval-stage que lo
evite a K fijo. Los 4 que entran = cat016, hp006/ISO-X, hp006/Tierra, hp013.

**Neighbor-window en SYNTHESIS-stage (sentence-window sobre el top-5) = BP válido pero MENOR.**
Medida la adyacencia del value-chunk al top-5 reranqueado: **4/8 a dist≤2** (los MISMOS 4 = señal
de consistencia; cero-expulsión porque es contexto aditivo, no compite por slots). Los otros 4
están a dist 6/10/29 o el value-doc no está en top-5 → no es problema de vecindad en ningún stage.
⇒ Item MENOR (4 facts de 132) para el **backlog de síntesis** cuando se ataque el cuello; NO se
construye ahora (síntesis diferida DEC-071e); NO justifica des-diferir síntesis por sí solo.

**Raíz real de INTRADOC (corrección de Alberto — SÍ es retrieval):** el value-chunk está
INFRA-RANKEADO (recall/ranking), no es synthesis. Inspección de los value-chunks: NO son bare ni
diminutos y YA tienen blurb contextual (Haiku) → **"aguja en chunk grande"**: el valor (PWR-R en
glosario de 7k chars; "35" en sección de cable) diluido en el embedding de la sección → baja
similitud query↔chunk. + ruido OCR (cat016 "aubusqueda"). = **cola dura** (8/132, reach≠PASS).

**Código:** flag NEIGHBOR_WINDOW default OFF, inerte, 354 tests verdes. Retrieval-stage = revertir
(NO-GO medido; la versión synthesis-stage sería otra inserción). Scripts de medición conservados.

## Preguntas para el dúo
1. ¿Es neighbor-window la raíz correcta, o el bloat lo hace peor que denser-FTS per-doc?
2. ¿W fijo vs adaptativo? ¿Cap por-doc? ¿Dónde exacto insertar (pre/post merge, pre/post model-filter)?
3. ¿Riesgo de regresión en los 31 PASS-control / 39 dev (meter ruido intra-doc)?
4. ¿La métrica in_pool es honesta aquí, o neighbor-window "gana" trivialmente sin ganar síntesis?
