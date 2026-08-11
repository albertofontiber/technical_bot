# s316d — Rediseño: UN punto de decisión conversacional (el anti-Frankenstein) — para el dúo

> ## SUPERADO por `s316_rediseno_punto_decision_unico_v2.md` (dúo NO-SÓLIDO ×2, convergente)
>
> Sol y Fable 5 (primera ronda con el pin restaurado) tumbaron los DOS claims de carga, y
> ambos críticos los verifiqué yo en código ANTES de leer el segundo veredicto:
>
> 1. **La pureza de `plan_turn` no sobrevivía al paso 5**: `lookup_model_manufacturer` y
>    `manufacturer_in_db` hacen I/O por consulta y DECIDEN mismatch/no-servida; y
>    `_inventario_fabricante()→None` degrada la ruta a RAG DESPUÉS del I/O — o el plan
>    hacía I/O (contradicción) o el despachador decidía (no era tonto).
> 2. **El rollback prometido estaba ROTO**: los únicos writes con contenido de
>    `mt_working_state` están gateados por `f1_active` (`:1388`, `:1506`). Bajo
>    `CONVERSATION_POLICY=stub` tras la fase B, mi adaptador de 3 líneas LEÍA un estado
>    que nadie escribe ⇒ carry-forward muerto en silencio justo en el rollback documentado.
>    Y arreglarlo à la ligera creaba un TERCER mutador — contradicción interna del diseño.
>
> El v2 resuelve ambos con dos movimientos: **contrato de hechos explícitos** (el plan
> declara qué hechos necesita; el shell los trae cacheados SIN decidir; los fallbacks son
> rutas condicionales DEL plan) y **un solo ESCRITOR con transiciones puras declaradas**
> (el despachador aplica transiciones; plan, política y regla-legacy las producen como
> VALORES — nadie más muta). También: ruta `feedback` añadida al censo, la voz NO se
> expande en fase A (decisión aparte), la partición del brand-switch (con/sin modelo) se
> declara como CONTRATO con test, el seam Haiku se elimina como aparato anticipatorio
> (pregunta cero), y la actualización del instrumento entra en el alcance de la fase B.

**Encargo de Alberto (11-ago)**: «prepara el rediseño con su dúo, porque es importante que el
diseño sea BP y robusto, especialmente a nivel arquitectónico/estructural — no quiero que
tengamos un Frankenstein».

**OBJETIVO + MÉTRICA de HOY**: eliminar la causa arquitectónica de #70 y de sus parches —
que **7 de los 13 retornos terminales de `handle_message` responden sin consultar la política
conversacional**, lo que obligó a crear la guardia de grupo −1 (parche de transporte) y hoy
deja TRES mecanismos tocando el estado (guardia · carry-forward legacy · política F1) con DOS
semánticas de invalidación. Métrica de éxito: (a) el instrumento de transporte demuestra que
**ninguna rama terminal decide sobre el estado fuera del plan** (invariante nuevo, por AST +
conducción); (b) equivalencia por ruta contra HOY (misma respuesta, mismo log, mismo efecto
de estado) en las rutas no tocadas; (c) el testigo orgánico de #70 sigue VERDE y el de
compatibilidad también.

**LEVER (Protocolo 4, digest consultado)**: ninguno medido se re-litiga. NO es agentic RAG
(DEC-089: NO-GO como arquitectura, métrica retrieval-miss; DEC-154: aquello no transfiere a
lo conversacional, pero tampoco lo necesito — esto no itera retrieval). NO toca retrieval ni
síntesis: es la estructura del despacho conversacional. Delta single-turn = 0 por
construcción; la vara es el gate MT + el instrumento.

## El problema, con números de esta sesión

- `handle_message`: 13 retornos terminales; 7 responden sin `log_query` y **ninguno de los
  tempranos consulta la política** ⇒ F1 no ve los turnos que cambian el tema (causa 1 de #70).
- Para arreglar el fallo orgánico hubo que poner `brand_switch_guard` en grupo −1: correcta
  como parche (precisión-primero, medida), pero es **un cuarto lugar** donde se decide sobre
  el estado, fuera de la política que existe para eso.
- `last_detected_models` sigue escribiéndose (`:1496`) estando MUERTO bajo F1 — y el dúo
  demostró que ni siquiera se limpia coherentemente en todas las rutas.
- La etapa 2 de #70 (la conflación de la rama B) se cortó DOS veces por el dúo; ambas
  encarnaciones habrían añadido más reglas sobre esta base inestable.

## Recomendación: `plan_turn` — clasificación pura, despacho tonto, estado en UN sitio

```
handle_message / handle_voice (tras ASR)
    │
    ├─ pre-paso transporte: captura de reply anclado (#60 5b — necesita reply_to_message)
    │
    ▼
plan = plan_turn(texto, estado, es_reply=False)     ← ÚNICO punto de decisión ($0, puro,
    │                                                  sin I/O, transport-neutral)
    │   plan.ruta      ∈ {cortesía(greeting|thanks|bye) · catalogo · inventario ·
    │                     mismatch · marca_no_servida · conversacional}
    │   plan.estado    ∈ {PRESERVAR · INVALIDAR(motivo) · N/A}
    │   plan.log       ∈ {sí · no}   (cortesía NO se loggea: promesa del aviso v7)
    │
    ▼
despachador en transporte (tonto):
    aplica plan.estado UNA vez → ejecuta la respuesta de la ruta (los handlers con I/O
    — _handle_catalog, _inventario_fabricante — siguen en transporte) → loggea si toca
    │
    └─ ruta=conversacional → _process_query → cascada F1 (CONGELADA, no se toca)
```

1. **`plan_turn` vive en `src/orchestrator/turn_plan.py`**: transport-neutral, puro,
   determinista. Absorbe los regex de cortesía/catálogo/marca de `telegram_bot.py` y **la
   lógica completa de la guardia** (frase de switch, resolutor dinámico, `_MARCAS_AMBIGUAS`,
   exención de misma marca, filtro normativo — todo lo pagado en s316b/c, intacto).
2. **La guardia de grupo −1 SE RETIRA** en el mismo cambio: existía solo porque las rutas se
   saltaban la política. Su predicado no se pierde — se muda al plan, que es donde una
   decisión de estado debe vivir. El `TypeHandler` desaparece; una pieza menos.
3. **UN estado**: `last_detected_models` se retira. El bloque legacy (rollback
   `CONVERSATION_POLICY=stub`) pasa a leer `mt_working_state.last_target_models` vía un
   adaptador de 3 líneas ⇒ **el rollback conserva carry-forward Y conserva el fix de #70**
   (la invalidación vive en el plan, independiente del flag) — la restricción rollback-safe
   del dúo se cumple por construcción, no por duplicación de claves.
4. **UNA semántica de invalidación**: `WorkingState()` completo (la de la etapa 1, la que
   evita el «Ha pasado un rato» mentiroso). El `advance_working_state` de rutas $0 deja de
   existir como caso especial: el estado solo lo mutan el plan (invalidación) y la política
   (resolución conversacional).
5. **La cascada F1 NO se toca**: `PolicyRoute`, sus golds y su gate MT quedan byte-intactos.
   `plan_turn` es una CAPA ENCIMA, no una reescritura del contrato congelado. (El CHECK de
   `query_logs_route` ya reservó los valores de cortesía en s301 — la taxonomía del plan se
   alinea con la del esquema, no inventa otra.)
6. **El seam para el LLM de intención queda creado y VACÍO**: la rama ambigua del plan
   (marca servida + sin modelo + estado vivo + ni compat clara ni switch claro) es HOY
   `PRESERVAR` (= comportamiento actual). Enchufar ahí la llamada Haiku es un lever
   POSTERIOR con su propio diseño+dúo+gate MT — este rediseño le da el único lugar donde
   vivir sin ser un injerto.

## Migración (dos fases en una PR, verificables por separado)

- **Fase A — extracción mecánica**: mover regexes y decisiones a `plan_turn`; el
  despachador reproduce HOY byte a byte. Verificación: tests de equivalencia por ruta
  (misma respuesta, mismo `route` en el log, mismo efecto de estado) — el instrumento de
  transporte es exactamente el harness para esto.
- **Fase B — unificación de estado**: retirar `last_detected_models` + adaptador legacy +
  retirar el `TypeHandler`. Verificación: testigos del instrumento (orgánico VERDE,
  compatibilidad VERDE, fall-through XFAIL se mantiene hasta el lever LLM) + invariante
  nuevo «ninguna rama decide estado fuera del plan» + suite completa.

## Alternativas consideradas y descartadas

- **Extender `PolicyRoute` con las rutas de transporte** (una sola taxonomía): toca el enum
  congelado, sus golds MT y el CHECK de la DB a la vez — máximo churn de contrato para el
  mismo invariante. La capa encima logra el punto único sin desestabilizar lo medido.
- **Seguir parcheando (etapa 2 sobre la guardia)**: dos NO-SÓLIDOS consecutivos del dúo son
  evidencia de que la base no aguanta más reglas; sería el cuarto mecanismo.
- **LLM orchestrator para todo el turno**: paga latencia/coste en el ~80% de turnos que las
  reglas resuelven bien y gratis; y el cuello medido del bot no es el enrutado.
- **Agentic/graph RAG como sustituto**: NO-GO medido (DEC-089) en su métrica; el cuello es
  vocabulario query↔celda, no multi-hop; el grafo que el corpus necesita YA existe como
  catálogo gobernado (DEC-074). Reconsiderable solo si compatibilidad-cruzada emerge como
  clase de fallo medida en queries reales.
- **Hacerlo con flag** (`TRANSPORT_PLANNER=on/off`): duplicaría el despacho entero durante
  la transición — un Frankenstein temporal para evitar otro. La equivalencia por ruta + el
  instrumento dan la red de seguridad que el flag daría, sin la bifurcación.

## Gaps / riesgos declarados

1. **Superficie de regresión = todas las rutas del bot vivo.** Mitigación: fase A mecánica
   con equivalencia byte-a-byte + instrumento; pero el riesgo residual de un matiz de
   Markdown/orden de replies existe y se paga en el smoke de producción.
2. **La promesa de privacidad** (cortesía sin log) pasa de estar implícita en el orden de
   los ifs a ser un CAMPO del plan (`log=no`). Es más explícita — pero un error en el
   despachador la rompería en un sitio nuevo; test dedicado obligatorio.
3. **`plan_turn` necesita el catálogo** (marcas servidas) para mismatch/no_model: hoy eso
   consulta DB con caché. El plan es puro: recibe las marcas como ARGUMENTO (el transporte
   se las da cacheadas). Si la caché está fría, el primer turno paga lo que hoy ya paga.
4. **El fall-through de #70 (etapa 2) NO se arregla aquí**: la rama ambigua queda
   `PRESERVAR` hasta el lever LLM. El testigo sigue XFAIL — honesto y visible.
5. **El coste es de UNA sesión larga** (extracción + equivalencia + unificación + docs),
   contra el goteo permanente de parches que está costando la alternativa.
6. **`handle_voice` y comandos**: la voz entra por el mismo plan tras el ASR (llamada
   explícita, cubierta por contrato de fuente); los `CommandHandler` quedan fuera del plan
   a propósito (no son turnos conversacionales) — declarado, no olvidado.

## Por qué BP + estructural + escalable

- **BP**: separación clásica clasificar/ejecutar (pure core, imperative shell); el estado
  con un solo dueño; la promesa de privacidad como dato verificable; cero I/O en la
  decisión; y ninguna pieza nueva de infraestructura — es una reorganización de lo que hay.
- **Estructural**: ataca la causa (decisiones dispersas en 13 retornos) y no el síntoma
  (qué regla falta en qué rama). La guardia −1 —un parche correcto— se RETIRA en vez de
  acumularse: el sistema queda con menos piezas que antes del rediseño, no con más.
- **Escalable**: una ruta nueva = una entrada en el plan con su decisión de estado
  EXPLÍCITA, forzada por el invariante del instrumento (el censo deja de ser un recuento y
  pasa a ser un contrato); el lever LLM, cuando llegue, tiene un único enchufe; y un
  transporte nuevo (WhatsApp, web) reusa el plan entero — hoy tendría que copiar los ifs.
