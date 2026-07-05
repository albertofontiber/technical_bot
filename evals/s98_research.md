# s98 · Research BP del gap de vocabulario (sourced + adversarial) — para P4

> Workflow 4 agentes sourced + 1 verificación adversarial. Fuentes verificadas.
> Salida completa: task wsabdxyrz. Incertidumbre honesta declarada: papers 2026 clave
> (Beyond-the-Reranker 2606.28367, 2602.18613) son de semanas atrás, sin réplica, dominios
> no-manuales-técnicos-ES → **cada paso se decide por delta MEDIDO en held-out, no por estas
> cifras externas**.

## Bottom line
- **Mi prior "el rerank es la mayor palanca": PARCIALMENTE apoyado.** Para la CLASE-I
  (aguja en el pool pero mal-rankeada = hp001 HOY), el rerank ES la palanca de mayor
  retorno — "Beyond the Reranker": quitarlo hunde nDCG@10 0.644→0.034 (−95%). NO es sesgo
  de reciente: es la lectura correcta PARA ESTE caso. **Corrección**: como ley GENERAL se
  pasa — HyDE sigue dando ganancia con rerank fuerte presente en bajo-solapamiento; Anthropic
  atribuye el mayor salto a Contextual-Embeddings+BM25, rerank = los últimos 18pp.

## Secuencia por evidencia/coste (para nuestro caso)
1. **PASO 1 (más barato, mayor evidencia, reversible) = ARREGLAR EL PROMPT DEL RERANK**
   (ya tenemos rerank LLM Sonnet): (1a) pasarle la query ORIGINAL, no reescrita; (1b)
   redefinir relevancia de "¿habla del tema?" → **"¿este pasaje CONTIENE el
   procedimiento/la respuesta?"**. Coste horas, sin API nueva, sin tocar índice.
   **GATE: delta en retrieval-miss del held-out, NO PASS.** Y desbloquea el tie-break.
   CAVEAT medido ("CoT Falls Short" 2510.08985): el razonamiento verboso puede DEGRADAR en
   casos léxicos normales → MEDIR el eje factual, no asumir.
2. **PASO 2 (si el prompt no basta)**: reranker instruction-following = **Voyage rerank-2.5**
   (ya estamos en Voyage; +7.94% vs Cohere; acepta instrucción NL que redefine relevancia)
   o **Rank1** open-weights (razona el gap léxico; +3× en BRIGHT-reasoning).
3. **PASO 3 (clase-II, no-recuperado)**: **hypothetical-QUESTIONS al indexar (HyPE/HyQE)** —
   OJO, refinamiento clave del research: es **question-side** (convierte la búsqueda en
   question↔question), DISTINTO de A3/Dense-X que es **answer-side** (enunciados). A3 NO
   cierra el gap de vocabulario/registro; las preguntas-hipotéticas SÍ. Mismo patrón de
   tabla-separada de A3. Coste medio (1 pasada LLM al indexar; dedup+cap).
4. **PASO 4 (query-side)**: HyDE, después del fix de rerank, medido (añade latencia+varianza).
- **DESCARTADO por evidencia/coste: swap de embedder** — el gap es arquitectónico; un
  embedder más potente compra ~0.5-5% (ruido) y NO toca la clase-I (la aguja ya llegó).

## Contradicciones que la verificación resolvió
- "¿razonar ayuda?" bifurca (Rank1 +3× BRIGHT vs "CoT Falls Short" degrada) → NO es bala de
  plata; MEDIR en nuestro eje factual.
- La verificación cazó que un agente citó "Beyond the Reranker" SOLO para "rerank es el
  bottleneck" y OMITIÓ que la misma fuente dice que HyDE SÍ ayuda con rerank presente en
  bajo-solapamiento → el peso conjunto NO dice "solo rerank".
