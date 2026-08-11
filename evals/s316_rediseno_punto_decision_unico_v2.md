# s316d v2 — Punto de decisión conversacional: hechos explícitos + un solo escritor

> ## SUPERADO por `s316_rediseno_punto_decision_unico_v3.md` (ronda 7 del dúo)
>
> NO-SÓLIDO ×2 de nuevo, pero con un cambio de naturaleza que ambos revisores declaran:
> **la arquitectura se sostiene y los críticos de la ronda 1 quedan resueltos como
> contradicción** (Fable, verificando hecho a hecho: los únicos hechos con I/O real son
> `marca_de_modelo` y `marca_servida`; la degradación inventario→RAG queda bien modelada
> como `fallback_ruta`). Lo que tumba esta ronda son CONTRATOS sobre-afirmados, no la
> forma: el v3 es precisión de claims y alcance, no re-diseño.

**Qué es.** El rediseño del despacho conversacional, corregido tras el dúo NO-SÓLIDO ×2
sobre el v1 (Sol + Fable 5; ambos críticos verificados por mí en código). El objetivo, la
métrica y el análisis de levers del v1 siguen vigentes; aquí solo lo que CAMBIA y el
diseño completo resultante. Nada cableado.

## Los dos invariantes, ahora sin las contradicciones del v1

### Invariante 1 — decisión pura con CONTRATO DE HECHOS (resuelve el crítico de pureza)

El v1 pretendía que `plan_turn` fuera puro «recibiendo las marcas como argumento», pero
las rutas mismatch/no-servida/inventario se deciden con I/O por consulta
(`lookup_model_manufacturer`, `manufacturer_in_db` con alias-ilike) y el inventario puede
degradar a RAG DESPUÉS del I/O. El v2 lo modela en dos pasadas, ambas puras:

```
paso 1  necesita = plan_turn_hechos(texto, estado)
        → frozenset de HECHOS requeridos, p.ej.:
          { marca_servida("morley"), marca_de_modelo("NC-PF2") }
        (cortesía, feedback, sin-marca → frozenset vacío: deciden sin hechos)

shell   hechos = resolver_hechos(necesita)     ← I/O MECÁNICO: trae exactamente lo
        (las mismas llamadas y cachés de hoy)    pedido; CERO decisiones

paso 2  plan = plan_turn(texto, estado, hechos) → TurnPlan
```

`TurnPlan` (dataclass frozen):

```
ruta            ∈ {greeting · thanks · bye · feedback · catalogo · inventario ·
                   mismatch · marca_no_servida · conversacional}
fallback_ruta   Optional[ruta]   # p.ej. inventario → conversacional si el shell
                                 # informa inventario_vacío: la DEGRADACIÓN es una
                                 # decisión DEL PLAN, expresada como valor
transicion      PRESERVAR | INVALIDAR(motivo) | N_A
log             sí | no          # cortesía y feedback: no (promesa aviso v7)
typing          bool             # send_action per-ruta (hallazgo Fable: hoy es
                                 # per-ruta y el v1 no lo modelaba)
```

- El plan es una función total de `(texto, estado, hechos)` — determinista, testeable
  sin red, sin mocks de httpx.
- El shell que resuelve hechos es MECÁNICO por contrato: un test fija que `resolver_hechos`
  no contiene lógica condicional sobre el TEXTO (solo sobre qué hechos se pidieron).
- El despachador ejecuta `ruta` (o `fallback_ruta` si el handler devuelve vacío) y aplica
  `transicion`. No examina el texto jamás.

### Invariante 2 — UN ESCRITOR, transiciones puras declaradas (resuelve el crítico de rollback)

El v1 decía «solo plan y política mutan» y a la vez prometía rollback con un adaptador de
solo-lectura — contradicción, porque bajo `CONVERSATION_POLICY=stub` los writes de
`mt_working_state` (hoy gateados por `f1_active` en `:1388`/`:1506`) desaparecen y nadie
escribiría el estado. El v2 reformula el invariante como es honesto:

> **Todas las mutaciones de `mt_working_state` las aplica EL DESPACHADOR, ejecutando
> transiciones PURAS producidas por una de tres fuentes declaradas:**
> 1. `plan.transicion` (invalidación por cambio de marca — corre SIEMPRE, en ambos
>    regímenes: el fix de #70 es independiente del flag);
> 2. `advance_working_state(...)` de la política (régimen `impl`);
> 3. `transicion_basica(estado, modelos_detectados, ts)` (régimen `stub`): la regla
>    legacy de hoy (:1493-1496) expresada como función pura sobre el estado ÚNICO —
>    setea `last_target_models`/`last_turn_at` tras un turno RAG con modelos.

- `last_detected_models` se retira; el régimen stub escribe y lee `mt_working_state` vía
  `transicion_basica` ⇒ **rollback = mismo carry-forward de hoy + fix de #70 intacto**,
  sin clave duplicada y sin tercer mutador ad-hoc: la tercera fuente es una función pura
  de 5 líneas con su test de ventana (`SESSION_TIMEOUT` == `WINDOW_SECONDS` == 3600,
  verificado por Fable — la conversión temporal es 1:1 y el test lo fija).
- «Un solo dueño» del v1 se corrige a: **un solo ESCRITOR, tres fuentes de transición
  declaradas y con precedencia fija** (plan → política/legacy). Es menos épico y es verdad.

## Correcciones del censo y el alcance (hallazgos medios)

1. **Ruta `feedback` añadida** al enum del plan (el v1 la omitía y es una rama terminal
   real: responde, no loggea, lee `last_query`/`last_response`). Su handler sigue en
   transporte; su decisión (es-feedback, no-loggear, PRESERVAR estado) vive en el plan.
2. **La voz NO se expande en fase A.** Hoy `handle_voice` va directo a `_process_query`
   (sin saludos/catálogo/feedback hablados). Pasarla por el plan completo sería una
   EXPANSIÓN funcional, no un refactor — el v1 la colaba como «mecánica». En fase A la
   voz invoca el plan con `fuente=voz`, que restringe a {invalidación, conversacional} =
   comportamiento de hoy byte a byte. Expandir la voz al plan completo queda como
   decisión de producto SEPARADA para Alberto (probablemente deseable, nunca implícita).
3. **La partición del brand-switch se declara COMO CONTRATO**: sin token de modelo →
   decide el plan (la lógica pagada de s316b/c); con token de modelo → decide la política
   (`new_brand_switch_model_token`, congelada). Un test la fija para que ninguna regla
   futura caiga del lado equivocado (hallazgo Fable: la partición era coherente pero
   tácita).
4. **El seam Haiku se ELIMINA del diseño** (Sol: aparato anticipatorio; pregunta cero).
   La rama ambigua es `PRESERVAR` y punto. Cuando el lever LLM tenga diseño+gate propios,
   su enchufe será `plan.transicion` — no hay que pre-construir nada.
5. **El instrumento entra en el alcance de la fase B**: tres de sus tests PINEAN
   mecanismos que la fase B retira (registro grupo −1, orden guardia<proceso en voz,
   censo de returns). La misma PR los sustituye por el invariante nuevo («toda mutación
   pasa por el despachador» — verificable por AST: cero asignaciones a
   `mt_working_state` fuera del despachador) y re-congela el censo. Declarado: esa PR
   reescribe parte de su propia red de seguridad, y por eso la fase A aterriza ANTES y
   con la red vieja intacta.
6. **Gap ES/EN declarado** (no nuevo, heredado de s316b): el léxico de switch es solo
   español; «switch to Morley» no invalida. Sigue igual tras el rediseño — mover ≠
   arreglar — y queda anotado en TECH_DEBT #70 etapa 2, no escondido.

## Migración (revisada)

- **Fase A** — extracción con hechos: `turn_plan.py` (plan + `TurnPlan` + hechos) +
  despachador en transporte + equivalencia byte-a-byte por ruta (texto de respuesta,
  `route` del log, efecto de estado, `typing`). La voz restringida. La guardia −1 SIGUE
  VIVA en fase A (redundante pero inocua: el plan produce la misma invalidación).
  Verificación: instrumento actual SIN tocar + tests de equivalencia nuevos.
- **Fase B** — unificación: retirar `TypeHandler`, retirar `last_detected_models`,
  `transicion_basica` para el régimen stub, actualizar los tests pineados del
  instrumento al invariante nuevo. Verificación: testigos (orgánico VERDE, compat VERDE,
  fall-through XFAIL), invariante por AST, suite completa, y smoke manual del bot.
- **Reversibilidad fase B**: `git revert` + redeploy limpio — el estado es memoria de
  proceso (un redeploy lo vacía de todos modos), no hay migración de datos ni DDL.

## Gaps / riesgos que SIGUEN declarados (del v1, vigentes)

- Superficie de regresión = todas las rutas del bot vivo; la equivalencia por ruta es la
  mitigación, el riesgo residual se paga en smoke de producción.
- La promesa de privacidad pasa a ser el campo `log` del plan: test dedicado obligatorio.
- El fall-through de #70 (etapa 2) NO se arregla aquí; testigo sigue XFAIL.
- Coste ~1 sesión larga. Los `CommandHandler` quedan fuera del plan a propósito.

## Por qué esto ya no es el Frankenstein

El sistema resultante tiene: una función pura que decide (con sus hechos explícitos), un
shell mecánico que los trae, un despachador que ejecuta y es el único que escribe, la
cascada F1 intacta debajo, y DOS piezas retiradas (guardia −1, clave legacy). Cada regla
futura tiene un lugar obvio donde vivir y un invariante por AST que la obliga a vivir ahí.
