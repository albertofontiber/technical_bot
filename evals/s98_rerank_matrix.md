# s98 · Matriz de experimentos del RERANK (pre-registro — PARA EL DÚO)

> GO de Alberto para trabajo AUTÓNOMO nocturno. Objetivo: quedarse con la(s) mejora(s)
> **ESTRUCTURAL(es)** del rerank (o su combinación) que dejen el **rerank-miss en 1-2**, sin
> overfitting. El dúo valida ESTE diseño Y cada mejora antes de "quedársela". Held-out
> EMBARGADO (medir en DEV — corregido: medir en held-out contaminaría; Alberto s98).

## Problema (medido, funnel s98)
El reranker LLM (claude-sonnet-4-6) tira del top-5 servido chunks-aguja que SÍ están en el
pool, prefiriendo chunks que casan léxicamente con la pregunta pero no contienen la respuesta
(hp001: aguja en pool-pos-1, tirada; +7 facts más = 8 rerank-miss en los NO-PASS).

## Diseño para AISLAR el rerank (barato + limpio)
- **Congelar el pool-50 COMPLETO (con content) por gold dev** una vez (config shipped: A3 on,
  tie-break off, identity on/add). Cada método SOLO re-rankea el pool congelado → top-5. Sin
  re-retrieval → aísla el rerank y abarata (solo la llamada de rerank por gold×método).
- **Métrica primaria — RERANK-MISS (sobre los 39 dev, NO solo los NO-PASS):** para cada fact
  CORE cuya aguja (needle famtie / valor-en-content) ESTÁ en el pool-50 congelado, ¿está la
  aguja en el top-5 re-rankeado? Cuenta los NO. Baseline lo fija M0. Objetivo: **1-2**.
- **No-regresión (bidireccional, anti-overfit):** los facts que HOY se sirven (aguja en top-5
  del rerank actual) DEBEN seguir sirviéndose. Cualquier método que recupere X pero pierda ≥X
  no vale. Se reporta el listado pareado (gana/pierde por fact), no solo el neto.

## Métodos ESTRUCTURALES a probar (principiados, del research sourced s98 — NO hacks por-gold)
- **M0 — baseline**: prompt de rerank actual (fija el baseline de rerank-miss).
- **M1 — redefinición de relevancia (prompt)**: cambiar el criterio de "¿habla del tema?" a
  **"¿este pasaje CONTIENE el procedimiento/dato que responde la pregunta?"**. Evidencia:
  arxiv 2504.07104 (multi-criteria "contains the answer"). Coste ~0.
- **M2 — query original al rerank**: asegurar que el rerank ve la pregunta ORIGINAL del técnico,
  no una reescrita/expandida (regla operativa del consenso). Verificar primero qué recibe hoy.
- **M3 — reranker instruction-following**: Voyage rerank-2.5 (`RERANKER_BACKEND=voyage` ya
  existe) con una INSTRUCCIÓN NL que redefine relevancia hacia "contiene la respuesta".
  Evidencia: +7.94% vs Cohere; instruction-following; 'technical docs' evaluado.
- **M4 — reasoning reranker**: (si M1-M3 no bastan) Rank1 open-weights o un prompt de rerank
  con razonamiento explícito. CAVEAT medido ("CoT Falls Short" 2510.08985): el razonamiento
  puede DEGRADAR casos normales → medir el eje factual, NO asumir.
- **M5 — combinaciones** de las que pasen individualmente.

## Guardarraíles ANTI-OVERFITTING (el énfasis de Alberto)
1. **Estructural, no por-gold**: cada método es un mecanismo GENERAL (redefinir relevancia,
   modelo, instrucción) — PROHIBIDO tunear contra golds concretos o el fraseo de las 8 agujas.
2. **Medir sobre los 39 dev COMPLETOS** (todos los facts-core con aguja-en-pool), no solo los 8.
3. **No-regresión bidireccional** (arriba) — un método que rompe served-facts se descarta aunque
   baje el rerank-miss.
4. **Dúo valida cada método ANTES de quedárselo** (no solo el diseño): ¿es estructural o es
   overfit disfrazado? ¿el mecanismo generaliza fuera de los 8?
5. **Held-out INTACTO** — reservado para 1 validación final del ganador (o diferido, modelo s84).
6. **Split de generalización**: si un método gana, confirmar que gana en un SUBSET no-usado-para-
   -elegir (partir los facts-con-aguja-en-pool en tuning/holdout-interno) antes de declararlo.

## Gates de decisión
- Un método SE QUEDA si: rerank-miss ≤ baseline−2 (dirección correcta) Y 0 nuevas-regresiones
  persistentes Y el dúo lo valida como estructural Y generaliza en el split interno.
- El objetivo global (rerank-miss 1-2) puede requerir COMBINACIÓN (M5) — se prueba solo con las
  piezas que pasan individualmente.
- Si NINGUNA combinación estructural llega a 1-2 sin regresión → se reporta honestamente el
  mejor alcanzable + por qué (no se fuerza con hacks).

## Preguntas para el dúo
1. ¿La métrica rerank-miss (aguja-en-pool → aguja-en-top5) está bien definida y es falsable?
   ¿El congelar-pool aísla de verdad el rerank, o pierde algún efecto?
2. ¿Los métodos M1-M5 son estructurales, o alguno huele a overfit? ¿falta algún BP del research?
3. ¿El split de generalización (#6) es suficiente anti-overfit con solo 39 dev, o hace falta otra
   salvaguarda?
4. ¿Riesgo de que optimizar rerank-miss (retrieval-level) degrade el PASS o la invención? ¿hay
   que añadir un gate de no-regresión de PASS-control antes de shippear el ganador?

---
## v2 — correcciones del dúo (2026-07-05, ambas mitades convergentes, 2 críticos c/u)
1. **FIDELIDAD (sub-agente, CRÍTICO):** el pool congelado v1 perdió `similarity` (el generador
   filtra top-5 por `similarity>=0.4`, generator.py:402) y `has_diagram`. → **harness v2
   (`scripts/s98_rerank_harness.py`) re-congela con retrieve_chunks directo (todos los campos)
   + manifest de config**; la métrica ahora = "aguja SOBREVIVE al filtro 0.4 post-rerank".
2. **PATH PRODUCTIVO (cross-model, CRÍTICO):** Voyage solo se enruta si NOT target_models
   (reranker.py:269) y prod SIEMPRE pasa target_models → el rerank de nuestro caso es
   **LLM-rerank**. El harness rerankea CON target_models (fiel). **M3/Voyage NO despliega para
   queries-con-modelo sin cambiar el dispatcher** → despriorizado; el brazo primario = M1
   (prompt LLM "¿contiene la respuesta?").
3. **M2 ELIMINADO:** la query original ya llega al rerank (telegram:465) → es invariante, no brazo.
4. **strict=True** en el harness (fail-open trunca y contaminaría la métrica).
5. **DEC-048 declarado:** el cross-encoder Voyage YA fue ROLLBACK (degradó la cola PARCIAL→FALLO,
   PASS-control 5→8). Métrica de hoy (rerank-miss retrieval-level) ≠ métrica DEC-048 (PASS e2e) →
   re-intentar es legítimo PERO el ganador PASA por el gate bvg duro (abajo).
6. **GATE FINAL DURO (no pregunta):** el método ganador se corre por `bvg_kmajority.py` completo
   (generate+judge, PASS-control + invención) ANTES de declararlo ship-able. rerank-miss NO basta
   (s97: famtie 7→6 pasó, bvg cazó hp001).
7. **Honestidad n-pequeño:** ~8-15 agujas rerank-miss → un split estadístico es ruido. Anti-overfit
   real = mecanismo principiado (no por-gold) + no-regresión sobre TODOS los facts-servidos
   (conjunto grande) + dúo valida estructural. NO se declara "generaliza" desde un holdout de n≈4.
