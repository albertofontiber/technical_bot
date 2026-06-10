# Propuesta s45 — lever de SÍNTESIS/completitud (dúo, Protocolo 3). Autor = Claude.

> Atácala: contrato, fallo-conocido (DEC-001 change-1), sobre-ingeniería, **overfit**, alineamiento PLAN.
> Bite anclado en evidencia, no ritual. Verifica claims fuertes contra código/corpus (regla C).

## Diagnóstico VERIFICADO (funnel pool-50, HyDE-OFF, anclado en FUENTE — `atomic_facts` del gold, NO el juez)
- **SÍNTESIS domina:** 59/85 hechos CORE-presente (todos) · **23/35 fuertes** (anchors fiables: códigos/núm ≥3 díg).
  RERANK-MISS marginal (3-10) → **L1/ensanchar-contexto MUERTO**. Cola RETRIEVAL (7 fuertes: hp002 umbrales, hp008 modelos, hp006).
- **Sub-mecanismo = UNDER-EXTRACCIÓN:** el bot responde pero omite hechos que SÍ están en su top-5. hp012: omite "99 det + 99 mód/lazo"
  y el conflicto "2-vs-4 lazos" — ambos en top-5 (`15088SP`/`MFDT280`), 3 SÍNTESIS fuertes. cat001: omite límites de aisladores en contexto.
- **Reconciliación con DEC-003** (que concluyó "FALLO = retrieval" a pool-15): DEC-003 auditó los **FALLO a pool-15** (retrieval,
  que retrieve-wide CERRÓ s44); esto audita los **PARCIAL a pool-50** (síntesis). **retrieve-wide MOVIÓ el cuello retrieval→síntesis.**
  Matcher HARDENED (fuertes; no el fuzzy de s29 que sobre-contaba "dato en top-5") + gold fixed (s43) → NO es el artefacto de s29.
  **[#1 ATÁCALO con `--dump`: ¿los hechos SÍNTESIS están DE VERDAD en un chunk del top-5, en contexto que el bot debió usar?]**

## Causa estructural (en el prompt — verificado `generator.py:16-125`)
El `SYSTEM_PROMPT` es una **FORTALEZA anti-invención** (líneas 30-99: "CERO INVENCIÓN", 5 anti-ejemplos, regla-gatillo
"normalmente/típicamente", revisión mental, citación `[F<n>]` obligatoria). Esa presión enorme + rule-7 "conciso **pero** completo"
(infra-especificada, 1 frase) empuja a **UNDER-extracción**: el bot juega a la defensiva y OMITE. La completitud no tiene peso
estructural frente al muro anti-invención. **El lever = reequilibrar, SIN aflojar la no-invención.**

## El lever (QUIRÚRGICO — NO un rewrite; lección change-1 = scope-creep + over-respuesta hp015)
AÑADIR un bloque de COMPLETITUD subordinado a cero-invención (candidato EXACTO a atacar por fraseo):

> **COMPLETITUD (subordinada a CERO INVENCIÓN):** Una vez aplicada la no-invención, sé EXHAUSTIVO con lo que SÍ está en los
> fragmentos. Si la pregunta tiene varias partes, o hay varios datos relevantes presentes en los `[F<n>]` (specs, pasos,
> condiciones, límites, excepciones, o CONFLICTOS entre fuentes), INCLÚYELOS TODOS — no entregues un subconjunto "por brevedad".
> "Conciso" = sin relleno, NO menos hechos. Si dos fragmentos se contradicen en un dato que responde la pregunta, señala el
> conflicto explícitamente con ambas cifras y sus `[F<n>]`.

## Guardarraíl DEC-001 (change-1 se revirtió por inducir over-respuesta en hp015 — NO repetir)
- El cambio NO afloja cero-invención; opera DENTRO ("presentes en los `[F<n>]`"). Riesgo IDÉNTICO a change-1: empujar
  completitud → empujar invención / over-inferencia procedimental.
- **Validación 2-EJES, A/B (prompt-actual vs +bloque), K-mayoría — NO el juez holístico (±1-4 ruidoso):**
  - **Completitud↑:** `atomic_scorer` per-hecho sobre los CORE — ¿incluye ahora el bot los hechos in-top5 que omitía?
    (strict-match = delta determinista; prose-llm = spot para prosa).
  - **Invención NO↑:** faithfulness — ¿afirma algún dato/inferencia sin soporte en `[F<n>]`? (el eje que change-1 violó en hp015).
    Cualquier REGRESIÓN aquí **bloquea el ship** (como change-1).
- Vara de aceptación: completitud↑ MATERIAL **y** invención plana/↓. Sube invención → revertir.

## Preguntas para el dúo
1. **[sub-agente, `--dump`]** ¿"SÍNTESIS domina @ pool-50" es REAL o el sobre-conteo que DEC-003 advirtió? Spot-check 2-3 fuertes
   (hp012, cat001): el anchor, ¿está en un chunk del top-5, en contexto usable, o es co-ocurrencia espuria?
2. ¿El bloque repite change-1 (over-respuesta)? ¿El guardarraíl 2-ejes (faithfulness bloqueante) basta para no subir invención?
3. **Overfit:** ¿el bloque cambia un MECANISMO o está fraseado para que pasen los 14 PARCIAL? ¿"señala conflictos" está hecho
   a medida de hp012/cat007? ¿Generaliza a 30+ fab / ES-EN?
4. ¿Hay un cambio MÁS quirúrgico/seguro? (p.ej. sólo reframear "conciso" en rule-7 SIN bloque nuevo; o evidence-planning fuera del prompt).
5. ¿n=22 + juez ruidoso deja leer el delta, o el atomic per-hecho es obligatorio? ¿Cómo medir "invención" sin un árbitro ruidoso?

## Contrato
BP + estructural (raíz: el balance del prompt) + escalable (30+ fab, ES/EN) + anti-overfit + 2-ejes DEC-001-aware + gaps declarados.
