# s333 · La RED aprende a juzgar: clasificador LLM tras la plantilla de corrección — propuesta v1 (21-ago-2026)

> **GO de Alberto** (21-ago, tras s332b): «a medida que aumente el número de usuarios la forma
> de expresarse de cada uno será diferente, y encima los técnicos no tienen la formación léxica
> para expresarse correctamente… implementarlo ya igual es lo más acertado». Contrato explícito:
> **BP, robusto, escalable.** Estado: PROPUESTA (pre-dúo). Nada cableado.

## 0 · Evidencia y encuadre (Protocolo 2.5 — métricas de lo que toco)

- **Lo observado**: `57b8d482` («sí, dije Kidde» → plantilla vacía; s332b lo cubrió por léxico)
  y `576a7ef9` («me refería a Kidde», cubierto en s332). Dos fraseos en el primer día de la
  clase = la firma de superficie lingüística ABIERTA; el argumento product-side de Alberto
  (diversidad de usuarios, sin precisión léxica) la adelanta a priori. La mitigación por léxico
  (R1 v2) implica un PR por fraseo nuevo y un miss de usuario por cada uno — no escala a 5-10
  técnicos.
- **INTENT_LLM (DEC-203/204) — el precedente que EXTIENDO, no el que zanja**: su gate 40/40
  (0 falsos SWITCH, K=3, umbral asimétrico) midió COMPAT-vs-SWITCH en la rama ambigua de marca
  **in-window**. Población DISTINTA a la de hoy ⇒ su PASS **no transfiere**: esta extensión
  necesita cohorte y gate PROPIOS. Lo que sí reuso es el patrón entero (seam, fail-open,
  parser estricto, atestación, anti-gate-shopping DEC-126).
- **S276**: esto NO es el router general de intents (blueprint sin autorización de build) —
  es UNA población nueva sobre el seam existente.

## 1 · Recomendación

### 1.A Arquitectura: fast-path determinista + red LLM (dos niveles DENTRO de la red)

La plantilla cerrada de s332/s332b se queda como **fast-path** ($0, 0ms, cubre lo observado).
El clasificador LLM entra SOLO cuando la plantilla NO casa y el turno tiene forma de candidato.
El léxico deja de tener presión de crecimiento (la cola la recoge el LLM); las filas futuras
son OPTIMIZACIÓN de coste (mover un fraseo frecuente a $0), no condición de funcionamiento.

### 1.B Población (acotada y declarada — el coste vive aquí)

Turnos que cumplen TODO (= exactamente los que hoy caen a `new_brand_no_state` con material
de rebuild):

1. `F1_MARCA_CORRECCION=on` y `F1_CORRECCION_LLM=on` (la rama LLM vive DENTRO del guard de la
   determinista: apagar la primera apaga ambas — dependencia declarada, sin interlock extra).
2. `matched_brands` con **exactamente UNA marca no-ambigua** (multi-marca o `_MARCAS_AMBIGUAS`
   ⇒ sin LLM, cascada de hoy — sin base para un rebuild unívoco).
3. `real == ()` (sin modelo explícito — A ya habría ganado) · sin pending vivo (precedencia
   s331).
4. `working_state.last_query` presente y `within_window(now)` (material de rebuild).
5. **`in_window == False`** (sin modelos bindeados): la rama in-window conserva INTACTO su
   clasificador COMPAT/SWITCH shipped — cero interferencia, cero gate-shopping. La corrección
   con producto bindeado queda determinista-only hasta que se OBSERVE (hoy: 0 observaciones).
6. `_correction_rebuild` (plantilla) devolvió None — el fast-path falló.

Volumen estimado: un puñado de turnos/día en piloto (los brand-sin-modelo-sin-estado que la
plantilla no caza). Latencia solo ahí: la declarada del seam (p50 1,3 s / p95 4,4 s,
`intent_llm.py` cabecera) contra turnos RAG de ~28 s. Coste por turno ~$0.0002.

### 1.C Contrato del clasificador (módulo nuevo `correccion_llm` junto a `intent_llm`)

- **Binario, sin extracción**: la MARCA viene del token gobernado ya casado (determinista);
  el LLM solo juzga la relación entre turnos. Parser ESTRICTO enum:
  `CORRECCION → "correccion"` · `NUEVO → "nuevo"` · resto → `None` (fail-open total, JAMÁS
  lanza). Prompt (una fuente, la que mide el gate ES la que sirve):

  ```
  Eres el enrutador de un asistente técnico de sistemas contra incendios.
  El técnico preguntó antes: «{last_query}»
  Su siguiente mensaje es: «{q}»
  La marca «{marca}» aparece en el mensaje nuevo.

  ¿El mensaje CORRIGE su pregunta anterior — indica que la marca/nombre que usó
  antes estaba mal y que la correcta es «{marca}» (espera la respuesta a la MISMA
  pregunta, ahora con esa marca)—, o es un TEMA NUEVO sobre «{marca}»?

  Responde EXACTAMENTE una palabra: CORRECCION o NUEVO.
  ```

- **Minimización, desviación DECLARADA vs INTENT_LLM**: aquí `last_query` SÍ viaja en el
  prompt — el juicio ES sobre la relación con la pregunta anterior y sin ella es incontestable.
  Mismo proveedor y mismo dato que la generación ya envía en cada turno RAG (no amplía
  superficie de datos); `last_answer_excerpt` NO viaja.
- Config espejo del seam probado: `claude-sonnet-4-6` (el que pasó el gate de juicio; Haiku
  NO-GO por méritos), `timeout 6 s`, `max_retries=0`, `temperature 0`, `max_tokens` mínimo,
  `fn.ultima` + `fn.config` (atestación e2e), cliente reutilizado a nivel proceso.

### 1.D Consumo en la política y telemetría

- `resolve()` gana `correccion=None` opcional (espejo EXACTO del parámetro `intent`): None =
  byte-idéntico. En la rama de corrección, tras el miss de la plantilla y las guardas de §1.B:
  `correccion(query, working_state)` → `"correccion"` ⇒ la MISMA resolución STANDALONE de
  s332 (rebuild + `Asuncion(marca_corregida)` + `state_query_override`) con
  **`rationale="brand_correction_llm"`** (atribución de mecanismo en gates y lecturas);
  `"nuevo"`/None ⇒ cascada de hoy.
- Seam de transporte `_correccion_seam` espejo de `_intent_seam` (celda de proceso; fallo de
  CONSTRUCCIÓN ruidoso + centinela; `asyncio.to_thread` ya envuelve el resolve).
- **Trace**: sección `correccion` tri-estado `{status, decision, latency_ms}` — patrón
  IDÉNTICO a `intent` (REQUERIDA; cambio de esquema versionado; pin `_CLAVES_HISTORICAS`
  actualizado con comentario; el criterio byte-idéntico de gates sigue siendo la CONDUCTA
  SERVIDA). La `Asuncion` resultante ya se estampa en `asunciones` (sin cambios).
- Espejo MT: `correccion=None` en modo contrato (byte-idéntico); flow con flag on inyectable.

### 1.E El «sí» PELADO tras el aviso (adjudicar en dúo: diseñar sí, construir DIFERIDO)

Clase adyacente declarada en s332b: el aviso invita y el usuario responde «sí» sin repetir la
marca. NO es un problema de clasificación (no hay marca en el turno ⇒ ni la plantilla ni este
clasificador aplican): es ESTADO — `pending_aviso` en WorkingState (patrón `pending_mention`
s331: SET al servir un aviso con `asumido`, CONSUME por afirmación del léxico gobernado ⇒
rebuild con esa marca, CLEAR en toda otra salida, ventana propia). Propuesta: queda DISEÑADO
aquí y se construye cuando haya UNA observación (hoy: cero — la respuesta real trajo la marca).
Disciplina DEC-233 aplicada a mecanismos, no solo a filas.

### 1.F Flags y ship

`F1_CORRECCION_LLM` (`on/off`, default **off** = byte-idéntico; inventario P1). Ship: PR →
merge → var en Railway (Alberto) → verificación DEC-099 (conversación real con fraseo NO
tabulado, p.ej. «que no hombre, que es Kidde» — ANTES de añadirlo al léxico).

## 2 · Gate PRE-REGISTRADO (cohorte propia — el PASS de INTENT_LLM no transfiere)

- **Cohorte congelada** `evals/s333_correccion_cohort_v1.yaml` (~36 casos, GOLD autorado y
  el dúo lo revisa; etiquetas límite las adjudica Alberto — precedente hp011#2):
  - **12 positivas**: las 2 reales (`57b8d482`, `576a7ef9` como habrían llegado SIN léxico) +
    variantes informales ES («que no, que es Kidde», «KIDDE te digo», «era kidde no id»,
    «te he dicho kidde»), voz-style con muletillas, EN («no I said Kidde», «I meant the Kidde
    one»).
  - **24 negativas**, incluidas las difíciles: tema-nuevo con marca («¿qué centrales de la
    marca Kidde tienes?» = `6ee97e80` real), queja («los Kidde fallan mucho»), comparación
    («¿Kidde es mejor que Notifier?»), pregunta técnica nueva con marca, saludo+marca.
- **Ejecución**: K=3 por caso, `temperature 0`, el MISMO módulo que sirve (una fuente).
- **Barra asimétrica pre-registrada**: **0 falsas CORRECCION** (la clase cara: reescribir la
  pregunta de un usuario que cambiaba de tema) **y ≥10/12 positivas**. Un falso-CORRECCION =
  NO-GO del flip (el fail-open a plantilla/léxico sigue siendo el suelo). Coste ~$0.03.
- **e2e**: replay de `57b8d482` con el cue retirado del léxico en el harness (fuerza el camino
  LLM) ⇒ `brand_correction_llm` + respuesta Kidde sin plantilla. GC0 conducta-byte con flag
  off + MT 52/52 + suite verde exit real.

## 3 · Alternativas consideradas y descartadas

1. **Extender el prompt COMPAT/SWITCH a 3 salidas**: re-prompt = cohorte nueva congelada para
   TODO el lever shipped (anti-gate-shopping DEC-126) + conflación de poblaciones distintas.
   Dos clasificadores pequeños y medidos > uno grande re-medido.
2. **LLM-first (sustituir la plantilla)**: pierde el $0/0ms del 100% de lo ya cubierto y
   convierte cada corrección frecuente en coste recurrente. La plantilla delante es
   estrictamente mejor.
3. **Extracción de marca por LLM (texto libre)**: rompe el parser-estricto-como-guard
   (Fable r12) y añade superficie de privacidad; el token gobernado ya la da gratis.
4. **Incluir la población in-window**: 0 observaciones + interferencia con el lever shipped +
   doble llamada en el mismo turno. Diferido a observación.
5. **Router general de intents**: S276, sin autorización de build. No.
6. **Construir ya el `pending_aviso`** (§1.E): 0 observaciones; mecanismo diseñado y diferido.

## 4 · Riesgos declarados

- **R1 falso-CORRECCION** (reescribir un tema nuevo): barra 0-en-gate + fail-open + el
  disclosure de s332 lo hace AUTOEVIDENTE en el mensaje («Respondo a tu pregunta anterior…»)
  — un fallo se ve y se corrige en el turno siguiente, no es silencioso.
- **R2 sesgo de cohorte** (GOLD autorado por mí): el dúo revisa la cohorte ANTES de correr el
  gate; etiquetas límite a Alberto.
- **R3 latencia** (p50 1,3 s solo en la población §1.B): declarada; el suelo es la conducta
  de hoy (plantilla vacía), no un turno bueno.
- **R4 deriva de proveedor/modelo**: pin de modelo + atestación de config + re-gate si cambia
  (DEC-126).
- **R5 dependencia de estado in-memory** (restart ⇒ sin `last_query`): heredada de F1,
  declarada desde s281.

## 5 · Por qué BP + estructural + escalable (el contrato del GO)

- **BP**: clasificación acotada con gate de juicio y fail-open — el patrón ya validado en
  producción por INTENT_LLM; determinista-primero donde converge, LLM donde no.
- **Estructural**: ataca la raíz del no-escalado del léxico (juicio semántico, no enumeración);
  reusa el seam, el parser-guard, la atestación y la metodología de gates existentes — cero
  arquitectura nueva.
- **Escalable**: el coste crece con los MISSES de la plantilla (decrecientes: cada fraseo
  frecuente puede bajar a $0 como fila), no con usuarios×fraseos; 30+ fabricantes no tocan
  nada (la marca es token gobernado); ES/EN cubiertos por el mismo juicio.

## 6 · Checklist de build (B1-B7, post-dúo)

- B1 `correccion_llm.py` (prompt+parser+constructor, una fuente) + tests.
- B2 rama en `resolve()` (+`correccion=None`) + rationale propio + espejo MT + fakes + tests.
- B3 seam `_correccion_seam` + celda + obs + tests.
- B4 sección `correccion` del trace (tri-estado) + pin + tests.
- B5 flag + inventario P1.
- B6 cohorte congelada + gate runner + RUN con recibo.
- B7 GC0/e2e/MT/suite + recibos + cierre docs.

## 7 · Traza del dúo

(pendiente — v1 al dúo: Sol xhigh + Fable emparejados, agentes frescos, cero git durante la ronda)
