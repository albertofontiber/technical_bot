# s316h — Cierre de los DOS gates del flip de INTENT_LLM (DEC-203b) — propuesta v1

PR #237 mergeada (lever construido, flag OFF byte-idéntico). DEC-203b dejó el flip
BLOQUEADO por dos gates declarados (Sol C3, r11). Esta propuesta los CIERRA — está
CONSTRUIDA en el working tree (sin commitear): atacad el código real, no el papel.

## Gate 1 — paquete de observabilidad en `rag_trace` (esquema cerrado)

**Qué hay** (`src/rag/runtime_trace.py` + `src/bot/telegram_bot.py`):

- Sección `intent` REQUERIDA en `rag_serving_trace_v1`:
  `{status, decision, latency_ms}` con enums cerrados
  (`status ∈ {off, not_invoked, invoked, construction_failed}`,
  `decision ∈ {none, compat, switch, fail_open}`, latencia acotada a 60 s).
- **Coherencia CERRADA** builder+validador: sin invocación ⇒ decision=none y
  latency=0 (coerción en builder, RECHAZO en validador si se fabrica a mano);
  invocado ⇒ decision obligatoria (`fail_open` ES decisión: el clasificador
  devolvió None y la política siguió con carry). Token de esquema se mantiene
  v1 (precedente s306 `retrieval` / s315 `timings`: clave nueva REQUERIDA,
  solo el sink valida, filas históricas no se re-validan).
- **Captura POR TURNO**: `_intent_seam(intent_obs)` extraído del handler a nivel
  módulo. El wrapper mide `perf_counter` y estampa en el dict del turno EN EL
  MISMO HILO de la llamada. La lectura post-resolve de `fn.ultima` (atributo
  compartido a nivel proceso) SALE del camino servido — dos turnos concurrentes
  podían pisarse la decisión. `ultima` queda para el gate de juicio (secuencial).
- `build_rag_serving_trace(..., intent_obs=)` cableado en el único build site;
  `intent_obs` nace `{}` antes de `if f1_active:` y `{}` degrada a `status=off`.
- Tests: 5 nuevos en `test_rag_runtime_trace.py` (off/invocado/coerción/tokens
  libres/trinquete+combinaciones ilegales) + 4 de seam en
  `test_s316g_intent_lever.py` (off estampa, por-turno sin estado cruzado,
  None/basura⇒fail_open, construcción fallida ruidosa+centinela+trazada).

## Gate 2 — e2e del CAMINO SERVIDO con recibo

**Qué hay** (`scripts/s316h_intent_e2e.py` → `evals/s316h_intent_e2e_result_v1.json`, PASS):

- Composición SERVIDA en todos los legs (lección r11 — paridad, no símil):
  `_intent_seam` del bot + `resolve_conversational_turn` real +
  `asyncio.to_thread` + `build/validate_rag_serving_trace` del turno.
- Legs: off (byte-inerte) · frío (celda vacía, 1ª llamada real paga TLS) ·
  caliente (mismo cliente de proceso) · timeout (cliente real con timeout
  minúsculo ⇒ fail-open inmediato, sin la cola de ~19 s que max_retries=0
  eliminó) · key mala (fail-open sin excepción) · construcción fallida
  (inyección declarada ⇒ centinela False + telemetría construction_failed +
  conducta OFF). **Las cifras canónicas viven en el RECIBO, no aquí** (r12:
  Sol y Fable cazaron que esta prosa citaba la corrida FAIL previa — duplicar
  números es fabricar drift; corregido no re-copiándolos).
- **Criterio PASS = SOLO mecánica de transporte.** Los 5 canarios son casos
  VERBATIM de la cohorte congelada v1.1 y su acierto (5/5) se registra como
  informativo — el juicio quedó zanjado en el gate con GO adjudicado
  (ANTI-GATE-SHOPPING: este e2e no re-litiga ni re-tunea).
- La 1ª corrida del e2e MORDIÓ: yo asertaba el rationale pelado
  (`brand_compat_confirmed_llm`) y el servido lleva prefijo de ruta
  (`carry_forward:...`) — exactamente la clase de drift que un símil no habría
  visto. Corregido a `endswith` sobre el formato real.

## Alternativas descartadas

1. **Traza también en la ruta clarify/decline** — descartada: toda decisión
   INVOCADA (compat/switch/fail_open) resuelve a rutas retrieve y por tanto
   llega al build site RAG; un turno clarify solo podría portar `not_invoked`,
   que no lleva información de decisión. Construir la forma cerrada completa
   (coverage/must_preserve/...) para una ruta $0 sería peso sin señal.
2. **Telemetría vía `fn.ultima` (como el log de s316g)** — descartada: estado
   mutable compartido a nivel proceso; con turnos concurrentes la decisión de un
   chat podía estamparse en la traza de otro. Por-turno en el hilo de la llamada
   elimina la clase, no el síntoma.
3. **Bump del token de esquema a v2** — descartado: rompería el precedente
   s306/s315 (claves nuevas requeridas bajo v1, validación solo en el sink) sin
   ganar nada — no hay lector que dependa de la forma exacta v1.
4. **e2e vía Telegram real** — descartado: exigiría TELEGRAM_BOT_TOKEN y un chat
   vivo; el seam extraído hace que el e2e ejecute EL código del handler sin el
   transporte Telegram, que ya cubre el smoke del bot.

## Gaps declarados

- Las filas clarify/decline no llevan sección `intent` (route ≠ rag): un
  `not_invoked` en esas rutas se pierde — sin información de decisión dentro.
- Leg 5 (construcción) usa inyección de fallo (patch de `construir_intent_fn`);
  el seam, el centinela y la política son reales. Declarado en el recibo.
- Leg timeout prima la celda de proceso con el constructor REAL y timeout 0,05 s
  (el seam no parametriza timeout — el servido usa 6 s fijo).
- La latencia del wrapper incluye `contexto_del_estado` (resolución de marca) —
  es la latencia del turno REAL, ligeramente mayor que el `ms` interno del fn.
- El flip sigue siendo decisión de Alberto en Railway; tras él: retirar el
  testigo XFAIL del fall-through y estampar el veredicto en LEVER_DIGEST.

## Estado tras el dúo r12 (Sol 6 · Fable 5, convergentes, 0 contradicciones)

Fable verificó a favor la mecánica («la coherencia builder+validador es real y
CERRADA»); los hallazgos fueron de pegamento, proveniencia y framing. TODO aplicado:

- **Sol C1** → el pegamento del handler (flag→seam→política→build site→log_query)
  quedó gateado EN CI: `test_lever_intent_atraviesa_el_pegamento_del_handler` +
  espejo flag-off en el instrumento de transporte. El e2e declara su límite y
  referencia ese test en el recibo.
- **Sol C2 + Fable F3** → recibo con `artefactos_sha256` (6 ficheros ejecutados),
  `git_estado`, y la corrida FINAL se genera SOBRE el commit.
- **Sol M1** → estado `not_wired` ≠ `off`: «telemetría sin cablear» ya no puede
  disfrazarse de «lever apagado»; el handler estampa `off` EXPLÍCITO.
- **Sol M2** → atestación de config: el fn construido por el seam en el leg frío
  DEBE llevar `{timeout_s: 6.0, max_retries: 0}` (criterio de PASS); el leg
  timeout declara su config inyectada.
- **Sol M3** → deuda declarada TECH_DEBT #74 (token v1 con claves crecientes;
  fix cuando exista un consumidor de re-validación — pregunta cero).
- **Fable F2** → `rewrite` centinela en el resolve del e2e (paridad de firma con
  el handler); invocaciones registradas en el recibo (esperado: 0).
- **Fable F1 / Sol menor** → esta prosa ya no duplica cifras del recibo.
- **Fable F4/F5** → supuestos documentados en el código (el parser estricto es el
  guard anti-drift del enum; la celda sin lock es last-write-wins benigno).

## Por qué BP / estructural / escalable

- Sigue el patrón EXACTO ya establecido del módulo (tri-estado medible,
  allowlists, coerción-en-builder + rechazo-en-validador, trinquete de clave
  requerida): un lector de la traza puede distinguir «lever apagado» /
  «no invocado» / «invocado con X» / «construcción rota» sin ambigüedad.
- El seam extraído no es solo para este e2e: cualquier verificación futura del
  camino servido (o un cambio de transporte) ejecuta la misma función.
- Coste marginal $0 con flag OFF; la sección pesa ~70 bytes en un cap de 8 KB.
