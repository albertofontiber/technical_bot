# s87 — Instrumento de diagnóstico de SÍNTESIS (fact-in-answer) · brief para el dúo

## Objetivo de HOY (+ MÉTRICA)
Diagnosticar autónomamente el cuello del eval = **SÍNTESIS**. **Métrica de HOY = nº de fallos de
síntesis REALES** (hechos que llegan al contexto del generador pero la RESPUESTA no transmite),
con su **mecanismo**. NO es PASS (diferido, DEC-071e) ni retrieval-miss (settled=14, DEC-073).

## Metric-check contra el settled (Protocolo 2.5 / 4)
- **Settled citado:** «SÍNTESIS = el cuello (103/132)» — DEC-070/071/073, **métrica = retrieval-bucket**
  (hecho soportado por un chunk del top-5, `by_target`). Es una cota de *lo sintetizable*.
- **Coincidencia:** el settled dice «retrieval entrega 103 hechos al contexto → el cuello es
  downstream». HOY **no lo re-litigo** (el retrieval SÍ entrega). Lo **REFINO/RE-MIDO dirigido**:
  de esos 103, ¿cuántos son fallos de síntesis reales? Es re-medición (como B0 re-abrió el
  retrieval-miss vía juez semántico), no re-litigación. Consistente.
- **Settled adyacente que este diagnóstico puede tocar:** «Lever de generación (prompt
  variant/completitud) SETTLED·PASS·NO-GO Δ_net=0» (DEC-051/s69, LEVER_DIGEST). Si el diagnóstico
  concluye que el cluster dominante es **omisión-por-completitud**, el fix barato ya está NO-GO
  **en PASS** (medido con ruler ±2 + 1 sola variante de prompt) → el hallazgo sería «el cuello es
  real pero el lever barato está NO-GO; el unlock es otra cosa (generación mejor / gold / juez)».
  Declararlo de entrada, no como sorpresa.

## Re-caracterización YA hecha ($0, Fase A) — el 103 NO es homogéneo
`by_target` SÍNTESIS = **103** de 134 hechos CORE (39 dev). Cruce con veredicto modal s67base:
- **25** en golds **PASS** (9 golds) → NO son fallos.
- **78** en golds **NO-PASS** (25 golds: 70 PARCIAL + 8 FALLO) → candidatos.
- Dominante = **PARCIAL** (respuesta parcialmente correcta; omite algunos hechos).

Dos casos reales eyeball (confirman heterogeneidad):
- **hp007** (gold PASS): omite 'cada 3/6 meses', 'cada 2 años' (el gold los da como *contexto* "otras
  frecuencias"; la pregunta es el test **anual**) → **omisión NO bloqueante / gold-suplementario**.
  Además run0=PASS pero modal=PARCIAL → **ruido K** (borderline).
- **cat007** (gold FALLO): omite 'no enclavado' y '10^5 operaciones' + **se escuda** ("el manual no
  especifica el corte de alimentación") pese a estar el failsafe en contexto → **omisión bloqueante
  + hedge-pese-a-presencia** (nota: failsafe = inferencia-no-en-fuente, DEC-062).

⇒ El cuello real ⊂ 78: los hechos que la respuesta **de verdad omite** de forma **bloqueante**.

## Diseño (INSTRUMENTO NUEVO de diagnóstico — juez+rúbrica nuevos, generación fresca, QA, trampa,
## sub-clasificador; NADA en prod, reach≠PASS) — **revisado por el dúo cross-model (6 findings)**

> **Hallazgo de plomería (regla-C):** el `s85_retrieval_miss_FINAL.yaml` NO persiste `top5_ids`/`pool_pin`
> (predatan el pin-upgrade), pero el `.partial.jsonl` SÍ trae `votes` por hecho (chunk-id→votos). Los
> chunk-ids son ESTABLES (mismo corpus/índice) → reconciliación $0 sin re-juzgar el pool.

### Paso 1 — generación FIEL a prod + captura del CONTEXTO REAL [cross-model finding 1+2]
Pipeline real por gold (`retrieve_chunks(50) → rerank(top_k=5, strict=True) → generate_answer`,
temp=0), idéntico a `test_bot_vs_gold.py:105-107` (sin `available_models`, como el harness/baseline).
**Instrumentar `generate_answer` para capturar `ctx_ids`** = los chunks que sobreviven
`similarity ≥ RELEVANCE_THRESHOLD` (=0.4, `generator.py:402`) Y se ensamblan al prompt. Esto ES
"lo que llegó al generador" — «en top-5» ≠ «en contexto» (un top-5 con sim<0.4 se cae). **Freeze-contract
COMPLETO en manifest** (finding 2): CHUNKS_TABLE+índice, EMBED_CACHE, HYDE, retriever/reranker model+config,
RELEVANCE_THRESHOLD, LLM_MODEL+temp, alias real gpt-5.5, git commit, seeds.

### Paso 2 — reaches-generator ($0, finding 1) + juez FACT-IN-ANSWER a nivel PROPOSICIÓN [finding 3]
Por hecho SÍNTESIS (seed = los 103 del bucket): `support_ids` = {chunk-id : votos≥4} del partial jsonl.
- **reaches_gen = support_ids ∩ ctx_ids ≠ ∅** (el chunk-soporte del hecho llegó de verdad al generador).
- **judge_B (proposición, no valor-suelto):** «¿la RESPUESTA afirma el HECHO completo — el valor «{valor}»
  EN la relación «{texto}»?» K=5, ≥4/5. Un número/código que aparece asociado a OTRA condición/periodicidad
  /componente NO cuenta (finding 3: mata el value-in-answer laxo). Admite ES↔EN/paráfrasis/OCR; excluye ante duda.

### Paso 3 — clasificación (reporta omitido y bloqueante POR SEPARADO) [finding 5]
| reaches_gen | conveyed | clase |
|---|---|---|
| False | — | **NOT-IN-CTX** (cayó por 0.4/jitter → retrieval/umbral, NO síntesis; reconcilia con retrieval-miss) |
| True | True | **SYNTH-OK** (el bot sintetizó el hecho en-contexto) |
| True | False | **SYNTH-MISS** (fallo de síntesis REAL) |

- **Primario (verdict-independiente):** `omitted-in-answer` = SYNTH-MISS.
- **Secundario (caveat stale):** SYNTH-MISS ∩ verdict-NO-PASS(s67base) = proxy de "bloqueante". NO se
  mezcla con el primario.

### Paso 4 — mecanismo de los SYNTH-MISS (2ª pasada: lee answer+texto-gold+chunk-soporte)
**completeness** (necesario, no incluido) / **hedge-fidelity** (contradice/se escuda pese a contexto) /
**gold-supplementary** (contexto NO exigido — hp007 freqs no-anuales; DEC-062: el juez holístico es
INERTE a core/supp → "omitido" ≠ "debía estar"). Cruce explícito con **settled s69** (completitud NO-GO
en PASS): si `completeness` domina → el lever barato ya está NO-GO.

### Paso 5 — certificación del juez_B (finding 4: MÁS que trampa numérica)
1. **Calibración hand-labeled** (~20 pares (hecho,answer) que YO etiqueto leyendo): conveyed / omitido /
   valor-en-relación-INCORRECTA / no-numérico ("no enclavado") / ES↔EN → mido accuracy del juez_B.
2. **Trampa extendida:** valor perturbado (dígitos +3) **Y no-numérico negado** ("no enclavado"→"enclavado")
   contra la respuesta real → debe dar omitted. FP = sobre-acreditación (desinfla synthesis-miss). ≤10%.
3. El control-PASS (25 hechos) es señal DÉBIL sola (PASS admite omisión gold-suplementaria) → informa, no calibra.

## Universo / freeze
- 103 SÍNTESIS `by_target` (incl. 25 PASS como control). **Held-out 12 EMBARGADO** (los 39 son dev).
- Congelar: prompt+rúbrica sha, top5-pin (ya inmutable en FINAL yaml), K=5, ≥4/5, git commit, seeds.

## Gaps / riesgos declarados
1. **El juez puede sobre-acreditar "conveyed"** (alusión vaga cuenta) → desinfla synthesis-miss.
   Mitiga: umbral estricto + trampa + rúbrica "valor concreto presente".
2. **Verdict s67base stale** (pre-VECTOR_NOCAT): se usa SOLO como señal secundaria de "bloqueante";
   la señal primaria (conveyed/omitted) es verdict-independiente.
3. **gold-supplementary confound** (hp007): un hecho omitido no-bloqueante NO es lever; el paso 3
   lo separa. El eval canónico es INERTE a core/supp (DEC-062) → "omitido" ≠ "debía estar".
4. **Ruido K del verdict** (hp007 flickerea PASS↔PARCIAL): reportar borderline aparte, no forzar.
5. **Coste**: ~103 facts × K5 (answer corta, no 50 chunks) ≈ barato; **validar en subset (hp007+cat007)
   primero, estimar $/pasada, NO re-correr el full iterando** (`feedback_cost_discipline`, incidente $50).
6. **No-build de raíz**: esto es DIAGNÓSTICO (mide el mecanismo), NADA en prod. reach≠PASS.

## Resolución del dúo (findings → decisiones) — cross-model GPT-5.5 + sub-agente Opus (CONVERGEN)
Ambos lados INDEPENDIENTES cazaron el mismo CRÍTICO central (capturar el contexto POST-umbral, no el
top5 crudo). Regla-C: todos verificados contra código/artefacto; 0 falsos-positivos.
1. **[CRÍTICO, ambos] Contexto post-`RELEVANCE_THRESHOLD`=0.4:** un top-5 con sim<0.4 se cae del prompt
   (`generator.py:402`) → «en top-5» ≠ «llegó al generador». **DECISIÓN:** capturar `fresh_ctx_ids` =
   top5 con `similarity≥0.4` (replico el filtro en el script, importo la constante); clase **NOT-IN-CTX**
   (below-threshold-drop) = reaches_gen False. `reaches_gen = support_ids(votos≥4) ∩ fresh_ctx_ids ≠ ∅`.
2. **[CRÍTICO, sub-agente] Artefacto-semilla equivocado:** los pins viven en **`s85_retrieval_miss_DEF.yaml`**
   (top5_ids+pool_pin+votes poblados), NO en FINAL (None). **DECISIÓN:** semilla = **DEF** (declaro commit).
   DEF/FINAL coinciden en SÍNTESIS=**103** (verificado); difieren 1 en RERANK/RETRIEVAL (DEF RETR=14 = canónico
   DEC-073) → irrelevante para el universo=103.
3. **[MEDIO, sub-agente] Verdict s67base stale estructura el 25/78:** **DECISIÓN:** el HEADLINE es
   **verdict-INDEPENDIENTE** (`omitted-in-answer` = SYNTH-MISS + mecanismo). El cruce con verdict es lente
   SECUNDARIA caveada. **Re-derivar el PASS actual = des-diferir PASS = gate de Alberto (DEC-071e)** → NO
   autónomo; se ofrece como follow-up (barato, misma tanda que la regeneración) si Alberto lo abre.
4. **[MEDIO, sub-agente] `available_models=None`:** el harness llama `generate_answer(q, chunks)` sin models
   (`test_bot_vs_gold.py:107`) → contrato de fidelidad declarado (un cambio del handler Telegram lo rompería).
5. **[MENOR, sub-agente] Separar mecanismos:** `hedge-fidelity` → **`hedge-defensivo`** (se escuda pese a
   contexto, cat007) vs **`contradice`** (afirma valor falso) — levers distintos (anti-hedge vs fidelidad).
   Mecanismos finales: completeness / hedge-defensivo / contradice / gold-supplementary.
6. **[MENOR, sub-agente, tranquilizador] El eje NO está invalidado:** verificado contra DEF que los 103
   SÍNTESIS-by_target tienen soporte firme (votos≥4) en un chunk del top-5 (103/103) → el chunk-soporte SÍ
   alcanzó el input del generador; medir si la RESPUESTA lo transmite es la pregunta correcta.
7. **[MEDIO, cross-model] Juez proposición, no valor-suelto** + **[MEDIO] certificación > trampa numérica**:
   ya incorporados (Paso 2 + Paso 5).

## Preguntas para el dúo (respondidas arriba)
- ¿El split conveyed/omitted-en-answer es el eje correcto, o hay un confound estructural que
  lo invalide (p.ej. el generador vio MÁS contexto que el top-5 pineado)?
- ¿Generar-desde-top5-pineado replica fielmente la generación de prod, o falta un paso del
  ensamblado de contexto (system prompt / orden / citas [F#])?
- ¿La trampa + control PASS bastan para certificar el juez, o falta un eje?
- ¿Algún settled adicional que este diagnóstico esté por pisar sin declararlo?
