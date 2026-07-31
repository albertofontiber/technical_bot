# s287 — ETAPA 2 (rerank-miss 4 → <2): plan de diagnóstico (pre-diseño, pre-dúo)

## Estado de entrada (full v3 canónico, DEC-163)
4 hechos: cat010#0 «24V dc» (lexical-distractor) · cat017#4 «CLSS» (lexical-distractor) ·
hp018#1 «6K8» + hp018#4 «1 A» (pos-buried — el residual document-side que DEC-092 dejó
declarado). Todos in_pool=True, in_topk=False.

## Levers YA MEDIDOS que NO se re-litigan sin métrica nueva (digest)
Afinar el reranker = NO-GO (DEC-092, 6 métodos) · ancho top-10 = YA shippeado · demote-TOC =
NO-GO (DEC-096) · tie-break coseno = CERRADO (s101) · el rerank LLM NO es determinista a
temp=0 (DEC-096: todo A/B exige control de ruido OFF-vs-OFF o N-reps).

## Diagnóstico a correr (read-only, ~$0, ANTES de diseñar nada)
1. Por cada uno de los 4: pool_rank vivo, contenido del chunk-soporte, y QUÉ chunks del top-10
   lo desplazan (¿distractores léxicos del mismo doc? ¿otros docs?). Fuente: el YAML v3 ya
   trae pool_ids ordenados + los ids-soporte.
2. hp018×2: cruzar con el histórico DEC-092 («hp005/hp006 >rank-15 = document-side») — ¿los
   soportes de 6K8/1A siguen en la MISMA posición del pool que entonces, o el corpus post-
   tachados los movió? ¿el canal hyq/enunciados les da surrogate (deberían: son specs)?
3. lexical-distractor ×2: ¿el distractor comparte tokens con la QUERY (clase FTS/vocabulario,
   DEC-085) o con el VALOR? Eso separa lever-de-canal de lever-de-orden.
4. Estabilidad: 1 rep OFF-vs-OFF del rerank sobre los 2 golds baratos (control de ruido
   DEC-096) para no diseñar contra el dado del LLM-rerank.

## Por qué el dúo NO se convoca todavía (anti-ritual, guardarraíl del Protocolo 3)
No hay decisión de diseño que desafiar: esto es un plan de LECTURA. El dúo (sub-agente fresco
+ Sol xhigh, zona de dolor retrieval) se lanza sobre el DISEÑO del lever que salga del
diagnóstico, antes de cablear — como en el instrumento v3.

## Nota de frontera con la etapa 3
5 de los 13 synthesis-miss son `via_coverage_append` + omitted (el LLM no usa lo que la lane
sirve) — si el diagnóstico de etapa 2 toca el orden de servido, medir el interlock con esos 5
(el append vive FUERA del top-k y el prompt los presenta después del prefijo).
