# s316g — Lever INTENT_LLM (v1) — SUPERADO por `s316g_lever_intent_llm_propuesta_v2.md`

> Ronda 10 del dúo: NO-SÓLIDO ×2 con veredicto de dirección («la arquitectura apunta a
> SÓLIDO con las reparaciones»). Los 17 hallazgos y sus resoluciones, en el v2. Los tres
> que cargaban peso: el gate estubeaba el juicio que constituye el lever (→ cohorte
> congelada con umbral asimétrico predeclarado); la extensión de misma-marca comparaba
> nombre-completo contra token-primario (8/26 fabricantes multi-palabra — verificado
> ejecutando); y el harness MT no podía correr el gate como estaba escrito (sin `intent`,
> sin stub por turno). Este v1 queda como registro.

**OBJETIVO + MÉTRICA de HOY.** Cerrar la causa (2) de #70 — el fall-through: «¿y en
Morley cómo se hace el reset?» tras contexto Kidde ARRASTRA, porque la rama B de la
política clasifica «marca sola + in-window» como compatibilidad incondicionalmente
(`conversation_policy_impl:398-403`). Métrica del gate (DEC-154: eje MT propio):
**48/48 del harness MT intactos + golds nuevos en verde + flag OFF byte-idéntico**.
El testigo XFAIL del instrumento (`test_testigo_fallthrough_marca_sin_switch_explicito`)
es el criterio de cierre: con el flag ON y el intent estubeado, su gemelo-ON debe pasar.

**AUDITORÍA DE LEVERS (Protocolo 2 §5 / 4).** El NO-GO agéntico (DEC-089, deep-lookup
Haiku) está settled en **retrieval-miss de respuesta única**; Alberto adjudicó en s281b
que NO transfiere a lo conversacional (DECISIONS:3637) y DEC-154 fija el gate MT propio.
Cinco rondas de dúo (s316b-d) establecieron que las reglas de vocabulario **no
convergen** en esta rama: tildes, muletillas, «en» vs «con», inglés, longitud — cada
ronda halló contraejemplos nuevos. La pragmática es abierta; una lista no la cierra.
Éste es el lever que Alberto pidió evaluar («¿no hay una vía más elegante tipo LLM?»)
y que el rediseño dejó con un único enchufe.

## Recomendación

**Un clasificador de intención inyectado en la rama B, con el patrón EXACTO del
rewriter** (la política no hace I/O; el callable lo suministra el transporte; modo
contrato = None = diferir):

1. **Seam en la política** (`resolve(..., intent: IntentFn | None = None)`):
   en la rama B (marca sola, in-window), tras la exención de misma-marca:
   - `intent is None` (contrato / $0 / flag OFF) → carry_forward
     `brand_compatibility_in_window` — **byte-idéntico a hoy**;
   - `intent(query, ws) == "compat"` → carry_forward `brand_compat_confirmed_llm`;
   - `== "switch"` → STANDALONE, `target_models=()`, `new_brand_topic_switch_llm`;
   - `None`/excepción → carry_forward `brand_compat_failopen_llm` (fail-open = la
     conducta de hoy; el error JAMÁS rompe el turno).
2. **Extensión de la exención de misma-marca** (el agujero que el lever activa): la
   rama B usa `_same_manufacturer` (mapa de 4) — «¿y Kidde saca nuevos?» con estado
   Kidde iría al LLM siendo la misma marca. Misma corrección de identidad directa que
   la guardia pagó en s316b: `token == classify(modelo_estado).lower()` como segunda
   condición. Determinista, $0, reduce llamadas.
3. **Transporte**: flag `INTENT_LLM` (default OFF, byte-inerte). ON → `_process_query`
   construye el callable: Haiku (`claude-haiku-4-5`, precedente GO DEC-102: mejor QA y
   4× más barato), prompt de UNA decisión con las dos frases en contexto (pregunta +
   producto en curso), respuesta de un token (`COMPAT`/`SWITCH`), `max_tokens=4`,
   timeout 3 s, toda excepción → None. **La decisión se estampa en `rag_trace`**
   (`intent_llm: {decision, ms}`) — el compromiso de observabilidad: medible en
   producción, no un regex invisible.
4. **Golds re-hechos ANTES del gate** (el prerrequisito declarado): mt13 t2
   Hochiki→**Morley**, t3 Apollo→**Notifier** (marcas SERVIDAS: la cadena
   producción-real llega a la política vía fall-through, cosa que Hochiki/Apollo no
   hacen — el contrato dejaba de ser un artefacto del harness); t4 (misma marca) queda.
   **mt14 NUEVO**: el fall-through orgánico (contexto NC-PF2 → «¿y en Morley cómo se
   hace el reset?») esperando STANDALONE con flag ON. En modo contrato el intent se
   estubea determinista (como el rewrite diferido); el juicio REAL de Haiku se valida
   en una pasada e2e puntual (~$0,01) antes del flip.
5. **Cierre del testigo**: gemelo-ON del xfail en el instrumento (flag ON + stub) en
   verde; el xfail original queda mientras el default sea OFF y se retira cuando
   Alberto flippee en Railway.

## Alternativas consideradas y descartadas

- **Más reglas de vocabulario**: 5 rondas de dúo con contraejemplos nuevos cada vez; no
  converge y no escala a 30+ marcas ni a EN.
- **LLM para toda la clasificación del turno**: paga latencia/coste en el ~80%+ de
  turnos que la cascada resuelve gratis y bien; el cuello es UNA rama ambigua.
- **Arreglar solo el default de la rama B sin LLM** (switch por defecto): invierte el
  error — rompería la compatibilidad legítima, que es la conducta mayoritaria del gold.
- **Esperar a tener técnicos reales y medir**: el fallo es de uso real YA (query_logs).

## Gaps / riesgos declarados

1. **El juicio del LLM no es determinista** frente a contratos congelados → en tests
   SIEMPRE estubeado (patrón replay del repo); el real solo en el e2e puntual y en
   producción, TRAZADO. El gate de contrato prueba el cableado, no el juicio.
2. **Latencia**: +300-500 ms en la rama ambigua (subset del 19% de turnos con marca sin
   modelo). Contra 28 s de turno, ruido — pero se mide en `rag_trace.timings`.
3. **Coste**: ~$0,0002/disparo. Ledger no necesario a este orden.
4. **El fail-open reproduce el bug** cuando Haiku falla (carry como hoy): correcto por
   diseño (peor sería romper el turno), pero significa que el cierre del fall-through
   es *best-effort*, no garantizado. El testigo-ON usa stub, no cubre el fallo de red.
5. **Marcas fuera de `BRAND_TOKENS`** no entran a la rama B → el lever no las ve. El
   vocabulario ya une seed+config gobernada; el residuo se declara, no se arregla aquí.
6. **Editar golds MT** toca un contrato con test propio: los cambios van con su diff
   razonado en el DEC y el contrato re-congelado — no silenciosamente.
7. **Flip en Railway** = decisión de Alberto tras el e2e puntual, como todo flag.

## Por qué BP + estructural + escalable

- **BP**: patrón de seam ya probado en el repo (rewrite), flag byte-inerte, fail-open
  total, decisión trazada, juicio caro solo en la rama que lo necesita, modelo con
  precedente GO medido (DEC-102).
- **Estructural**: ataca la conflación DONDE vive (la rama B) con el tipo de señal que
  el problema requiere (pragmática ≠ regex), sin tocar el resto de la cascada ni el
  contrato del plan.
- **Escalable**: cero listas nuevas que mantener; una marca nueva en config entra al
  vocabulario y el clasificador la juzga igual; ES/EN gratis (el LLM no distingue).
