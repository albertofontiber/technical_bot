# Propuesta s45 — palanca ESTRUCTURAL de completitud (dúo, Protocolo 3). Autor = Claude.

> Atácala: contrato (BP + estructural-raíz + escalable), **overfit**, fallo-conocido (DEC-001),
> sobre-ingeniería, desalineamiento con el PLAN. NO la defiendas — produce *bite* anclado en evidencia.

## Estado verificado (s45, hoy)
- **Fase 1 (calidad).** retrieve-wide (s44, `RETRIEVAL_TOP_K` 15→50) cerró los FALLO **peligrosos** (respuesta incorrecta).
- **Residual ESTABLE** (robusto al ruido, medido en 8 corridas HyDE-OFF): **1 FALLO real = hp006** (recall-miss de corpus);
  **~14 PARCIAL = "correcto pero INCOMPLETO"** (omite hechos que el técnico necesita); resto OK.
- **Hallazgo de medición (hoy):** el juez holístico gpt-5.5 + la generación Sonnet NO son deterministas (`temp=0`
  NO reproduce; 0/22 respuestas idénticas entre réplicas de s44). El conteo de FALLO de la **misma config** baila **1–4**
  por tirada. → todo lever se mide con **K-mayoría**; el residual se define por el **SET estable**, no por veredictos sueltos.
- **Diagnóstico canónico (DEC-005/006):** cuello dominante = el bot recupera los chunks correctos pero **OMITE hechos
  presentes** → completitud de SÍNTESIS. PERO s44 mostró que varios "casos síntesis" eran en realidad **retrieval-contexto**
  (el hecho estaba enterrado, no omitido). → la causa real (síntesis-omisión vs contexto-ausente) **NO está aislada por mecanismo**.

## Restricción DURA (de Alberto)
Atacar mecanismos **ESTRUCTURALES** que muevan la aguja y **GENERALICEN** (síntesis / reranker / generación / contexto / config).
**PROHIBIDO** el micro-ajuste que hace pasar una pregunta concreta PARCIAL→PASS y sólo sirve para ESA (overfit). El lever debe
cambiar un MECANISMO, validado sobre el SET entero, no parchear síntomas.

## La pregunta que DECIDE el lever (estructural, NO overfit)
¿Los hechos OMITIDOS están **DENTRO** del contexto que ve el generador (top-5 post-rerank, filtrado por `RELEVANCE_THRESHOLD`,
`generator.py:361`) o **FUERA**?
- **FUERA** → lever de **CONTEXTO/RETRIEVAL** (el generador nunca vio el hecho).
- **DENTRO pero omitido** → lever de **SÍNTESIS** (el generador lo tenía y no lo usó).
Se mide reutilizando `audit_retrieval_funnel.py` / `locate_fact.py` (per-hecho, anclado en FUENTE) sobre los ~14 PARCIAL estables.
Es **atribución de MECANISMO**, no parche por-pregunta.

## Candidatos estructurales (rankéalos / atácalos)
- **L1 — Ancho de contexto al generador:** `RERANK_TOP_K` 5→8/10 y/o bajar `RELEVANCE_THRESHOLD`. retrieve-wide ensanchó el
  POOL (50) y el reranker desentierra, pero **el generador SÓLO ve 5** → si el hecho cae en rank 6-10, nunca lo ve. Es la
  CONTINUACIÓN natural de retrieve-wide (mismo mecanismo de burial, siguiente corte). Config, generaliza, **bajo overfit**.
  Riesgo: dilución / invención↑ / latencia / coste-tokens.
- **L2 — Prompt de síntesis exhaustiva:** el `SYSTEM_PROMPT` dice "conciso pero completo" (`generator.py:27`, tensión).
  Rebalancear a "extrae TODOS los hechos de la pregunta presentes en el contexto; enumera completo; señala conflictos".
  Riesgo: **DEC-001** (cambios de generación net-negativos; change-2 revertido), invención↑, **overfit a fraseo del eval**.
- **L3 — Rerank consciente de COBERTURA:** rankear por cobertura de las FACETAS de la pregunta, no sólo relevancia top-1.
  Ataca el caso multi-faceta/cross-doc (cat001, hp012-conflicto). Más build; medio overfit.
- **L4 — Recall término-exacto (hp006):** BM25/híbrido para términos técnicos exactos ("Tierra" = fallo de aislamiento a masa).
  Impacto más estrecho (1 caso conocido), pero ataca el único FALLO real.

## Mi recomendación (ATÁCALA)
1. **Diagnóstico de MECANISMO** (dentro/fuera de contexto) sobre los ~14 PARCIAL estables — barato, reusa instrumentos, NO overfit.
2. Pull del lever que diga el diagnóstico; **prior fuerte = L1** (continúa retrieve-wide; el corte top-5 es el siguiente burial).
3. Validar **K-mayoría + DOS EJES** (completitud↑ **SIN** invención↑, DEC-001) sobre TODO el set — **generalización, no eval-max**
   (NO barrer `RERANK_TOP_K` 5..10 y quedarse el pico del eval = eso ES overfit al eval).

## Preguntas para el dúo
1. ¿Es **L1** el mejor needle-mover de bajo-overfit, o hay un **pez más gordo** que se me escapa (reranker LLM-genérico,
   chunking, formato del contexto, el propio `RELEVANCE_THRESHOLD`, packing)?
2. ¿El "diagnóstico de mecanismo" es **measure-first legítimo** o **otra vuelta de afinar-el-instrumento** (la queja de Alberto s35-42)?
   ¿Dónde está la línea aquí?
3. ¿Riesgos de L1 (dilución del contexto → MÁS PARCIAL/invención) reales? ¿Escala a 30+ fabricantes / ES-EN?
4. Dado **sin usuarios** durante meses (M&A due-diligence): ¿F1-quality-lever AHORA, o declarar F1 suficiente-para-fase y pasar
   a **F2 (escala: quitar hardcoding por fabricante)** — que también es estructural y está en la ruta crítica del M&A?

## Contrato
BP + estructural (raíz, no parche) + escalable (30+ fab, ES/EN) + **anti-overfit** + medido con K-mayoría + todos los gaps declarados.
