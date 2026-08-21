# s333 · Clasificador LLM tras la plantilla de corrección — v2 VINCULANTE (post-dúo, 21-ago-2026)

> Sustituye a la v1. Integra los 10 hallazgos de la ronda emparejada (Sol xhigh 6 · Fable 4,
> ts=2026-08-21T11:07:37; adjudicación completa en §8). El GO y el contrato de Alberto
> (BP + robusto + escalable) intactos. Fable: «sólido en arquitectura y método; NO ship del
> gate sin cerrar el hallazgo medio y sin pinnar la regla K=3» — ambos cerrados aquí.

## 1 · Arquitectura (sin cambios de fondo vs v1; dos correcciones DURAS del dúo)

Fast-path determinista (plantilla s332/s332b, $0) + red LLM SOLO en su miss. Dos correcciones:

- **(Sol-1, CRÍTICO confirmado) Contrato de threading del seam**: hoy el bot mueve el resolve
  a `asyncio.to_thread` SOLO si `_intent_fn` existe (`telegram_bot.py:2154-2170`). La regla
  pasa a ser: **`to_thread` cuando CUALQUIER seam LLM esté activo** (`_intent_fn` o
  `_correccion_fn`); sin esto, `F1_CORRECCION_LLM=on` con `INTENT_LLM=off` ejecutaría hasta
  6 s síncronos EN el event loop (todos los chats congelados). Test e2e dedicado: solo-corrección
  activa ⇒ camino threaded.
- **(Fable-1, MEDIO confirmado) Guarda de model-token**: condición nueva de población —
  `not _has_model_type_token(ql)`. Un turno con marca + código NO resuelto («no, era la Kidde
  2X-AF9999» con el código destrozado) hoy va a `new_brand_switch_model_token` (standalone del
  tema NUEVO) y ESA conducta se conserva: reescribirlo como corrección perdería el código que
  el usuario acaba de dar. Con código RESUELTO, A ya ganó (sin cambios). Test de la guarda.

## 2 · Población (todas las condiciones; sin «exactamente» — Fable-4)

1. `F1_MARCA_CORRECCION=on` **y** `F1_CORRECCION_LLM=on` (la rama LLM vive dentro del guard
   determinista; dependencia declarada).
2. Exactamente UNA marca no-ambigua en el turno (multi-marca / `_MARCAS_AMBIGUAS` ⇒ fuera).
3. `real == ()` · sin pending vivo (precedencias ya corridas).
4. `working_state.last_query` presente y `within_window(now)`.
5. `in_window == False` (sin modelos bindeados — la rama COMPAT/SWITCH shipped queda intacta).
6. La plantilla determinista devolvió None.
7. **`not _has_model_type_token(ql)`** (§1).

Es un SUBCONJUNTO de los turnos que hoy caen a `new_brand_no_state` (no «exactamente»: las
guardas 2 y 7 dejan fuera clases que siguen con la conducta de hoy — dirección declarada).
Volumen: puñado/día en piloto. Latencia solo ahí (p50 1,3 s / p95 4,4 s, cabecera de
`intent_llm.py`) frente a turnos RAG de ~28 s. Coste ~$0.0002/turno.

## 3 · Contrato del clasificador (= v1 §1.C con dos ajustes)

Binario CORRECCION/NUEVO; marca = token gobernado (sin extracción libre); parser estricto;
fail-open total; config espejo (`timeout 6 s`, `max_retries=0`, `temperature 0`, celda de
proceso, `fn.ultima`+`fn.config`). Prompt de v1 §1.C sin cambios (una fuente; el que mide el
gate ES el que sirve).

- **(Sol-3) Modelo**: pin de ship = `claude-sonnet-4-6` como default CONSERVADOR (la familia
  que ya pasó un gate de juicio en este seam) — **sin heredar el «Haiku NO-GO»**, que midió
  COMPAT/SWITCH (métrica distinta; Protocolo 2.5). El gate corre un **brazo Haiku
  INFORMATIVO** en la misma cohorte (~+$0.02): si Sonnet PASS ⇒ Sonnet shipa (el dato Haiku
  queda para el lever de coste futuro); Sonnet FAIL + Haiku PASS ⇒ adjudicación con Alberto,
  no auto-swap.
- **(Sol-5) Evaluación de privacidad EXPLÍCITA** (la v1 sobre-afirmaba «no amplía superficie»):
  el payload asocia DOS turnos del usuario (`last_query` + `q` + marca) en UNA petición
  adicional al mismo proveedor (Anthropic, mismo DPA que generación; API sin retención de
  entrenamiento). La asociación entre turnos consecutivos YA viaja al mismo proveedor en el
  camino s332 (el rebuild manda «{last_query} (el usuario corrige…)» a generación); la
  frecuencia añadida = solo los misses de plantilla; finalidad acotada = enrutado;
  `last_answer_excerpt` NO viaja; nada se persiste fuera de `query_logs` (retención vigente).
  Delta real declarado: +1 petición en la población §2, mismo perímetro de datos.

## 4 · Consumo, telemetría, espejo (= v1 §1.D) + adyacencia declarada

`resolve(..., correccion=None)`; guardas §2; `"correccion"` ⇒ resolución STANDALONE de s332
(rebuild + `Asuncion` + `state_query_override`) con `rationale="brand_correction_llm"`;
`"nuevo"`/None ⇒ cascada de hoy. Seam `_correccion_seam` espejo (construcción ruidosa +
centinela). Trace: sección `correccion` tri-estado `{status, decision, latency_ms}` (patrón
`intent`, REQUERIDA, pin actualizado con comentario; byte-criterio de gates = conducta servida).
Espejo MT con `correccion=None` en contrato.

**(Sol-2) Adyacencia de `last_query` — riesgo HEREDADO, no nuevo**: `within_window` prueba
edad, no adyacencia; los atajos de catálogo no refrescan estado (R8 s332) y CLARIFY/DECLINE
tampoco (R9). El fast-path determinista tiene EXACTAMENTE el mismo hueco desde s332 — el LLM
no lo amplía (juzga sobre la misma `last_query` que la plantilla usaría). Controles vigentes:
el sufijo cita la pregunta reconstruida VERBATIM (un rebuild sobre base rancia es autoevidente
y corregible en el turno siguiente) + casos `previo=atajo` y `previo=DECLINE` en el e2e (GC2
s332 ya los lista; aquí se re-ejecutan con el flag LLM on). Raíz (refresco de estado en
atajos) = deuda aparte ya declarada, fuera de este lote.

## 5 · Gate PRE-REGISTRADO (regla de agregación PINNADA — Sol-4/Fable-2)

Cohorte congelada `evals/s333_correccion_cohort_v1.yaml` (12 positivas / 24 negativas, v1 §2)
**+ 2 negativas nuevas de la clase Fable-1** (marca + código no-resuelto) que verifican la
GUARDA (no llegan al LLM: el runner las corre contra `resolve()` entero, no contra el
clasificador aislado). Revisión pre-gate de la cohorte: **Fable standalone** (desviación
declarada del «dúo entero»: proporcionalidad — la ronda de diseño ya moldeó la cohorte;
etiquetas límite las adjudica Alberto, precedente hp011#2).

**Agregación K=3, pinnada ANTES de correr (espejo s316g «cualquier voto dañino cuenta»):**
- NEGATIVA: falla si **CUALQUIERA** de sus K votos es CORRECCION (voto dañino = 1 basta).
- POSITIVA: pasa solo con **MAYORÍA ≥2/3** de votos CORRECCION.
- `None`/timeout cuenta como NUEVO (la dirección del fail-open): inocuo en negativas,
  en contra en positivas.

**Barra (con el framing honesto de Fable-3):** 0 negativas falladas (falsas CORRECCION) **y**
≥10/12 positivas — declarando que 2 positivas (57b8d482, 576a7ef9) las absorbe el fast-path
en producción (solo el harness las fuerza al LLM retirando el cue): la barra efectiva sobre la
cola REAL que servirá el LLM es **≥8/10 de las restantes**. Coste total del run (Sonnet K=3 +
brazo Haiku informativo): ~$0.05.

**e2e**: replay `57b8d482` con cue retirado ⇒ `brand_correction_llm` + respuesta Kidde ·
test de threading (Sol-1) · GC0 conducta-byte flags off · MT 52/52 · suite exit real.

## 6 · Piezas nuevas (framing corregido — Sol-6: «cero PATRÓN nuevo», no «cero arquitectura»)

Módulo `correccion_llm.py` · rama en `resolve()` + param · seam + celda · flag
`F1_CORRECCION_LLM` + inventario P1 · sección `correccion` del trace · cohorte + runner del
gate. Todo sobre patrones ya probados (INTENT_LLM/DEC-203-204; tri-estado; plantilla s332).
`pending_aviso`: diseñado (v1 §1.E), construcción DIFERIDA a observación (sin cambios).

## 7 · Alternativas y riesgos

Las 6 alternativas descartadas de v1 §3 siguen; riesgos v1 §4 + **R6-adyacencia** (§4, heredado,
controles declarados) + la clase Fable-1 cerrada por guarda. R2 (sesgo de cohorte) mitigado
por Fable-standalone pre-gate + límites a Alberto.

## 8 · Traza y adjudicación de la ronda (ts=2026-08-21T11:07:37, emparejada)

| # | hallazgo | verif. | adjudicación |
|---|---|---|---|
| Sol-1 (crítico) | «to_thread ya envuelve» FALSO — solo con `_intent_fn` | CONFIRMADO (bot:2154-2170, leído) | §1: contrato threading con CUALQUIER seam + test e2e |
| Sol-2 | adyacencia de `last_query` (atajos/CLARIFY no refrescan) | CONFIRMADO (R8/R9 s332) | §4: heredado del fast-path, controles declarados, raíz=deuda aparte |
| Sol-3 | «Haiku NO-GO» = mismatch de métrica | CONFIRMADO | §3: pin conservador sin herencia + brazo Haiku informativo |
| Sol-4 | agregación K ambigua = gate-shopping | CONFIRMADO | §5: regla pinnada (voto dañino / mayoría / None=NUEVO) |
| Sol-5 | «no amplía superficie» sobre-afirmado | CONFIRMADO | §3: evaluación de privacidad explícita con el delta real |
| Sol-6 (menor) | «cero arquitectura nueva» contradice checklist | CONFIRMADO | §6: reword + lista de piezas |
| Fable-1 (medio) | población traga marca+código-no-resuelto (hoy `switch_model_token`) | CONFIRMADO (impl:848-856, 528-538) | §1/§2: guarda 7 + 2 negativas de clase en cohorte + test |
| Fable-2 (menor) | K=3 sin regla en la barra | CONFIRMADO (=Sol-4) | §5 |
| Fable-3 (menor) | barra efectiva 8/10, no 10/12 (2 positivas las absorbe el fast-path) | CONFIRMADO | §5: declarado en la barra |
| Fable-4 (menor) | «exactamente los de new_brand_no_state» sobra en ambas direcciones | CONFIRMADO | §2: subconjunto declarado |

**10/10 con sustancia, 0 falsos positivos.** Los dos bloqueantes de Fable (guarda + regla K)
y el crítico de Sol (threading) quedan cerrados en la spec. v2 = spec VINCULANTE del build.

## 9 · Checklist de build (actualiza v1 §6)

- B1 `correccion_llm.py` + tests.
- B2 rama en `resolve()` (+guarda `_has_model_type_token`) + rationale + espejo MT + fakes + tests.
- B3 seam `_correccion_seam` + **contrato de threading (cualquier seam ⇒ to_thread)** + tests.
- B4 sección `correccion` del trace + pin + tests.
- B5 flag + inventario P1.
- B6 cohorte (12+2 / 24+2) + revisión Fable-standalone + runner con la regla K pinnada + RUN
  (Sonnet + brazo Haiku) con recibo.
- B7 e2e (replay + threading) + GC0 + MT + suite + recibos + cierre docs.
