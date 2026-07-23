# s280 — Diseño BUILDABLE multi-turn / multi-hop (v2, POST-dúo r1)

**Estado:** v2 tras adjudicar el dúo r1 (Sol 8 + Fable 7 —
`evals/s280_multiturn_duo_r1_adjudication_v1.yaml`; los 11 fixes incorporados, marcados [FIX-*]).
**Autorización trazada [FIX-DEC]:** la instrucción explícita de Alberto (22-jul noche) autoriza el
DISEÑO ya; el BUILD de Fases 0-1 arranca tras su lectura matinal (quedará en DEC) — DEC-136
`NO_BUILD_AUTHORIZATION` queda superado por esa decisión humana, no por este documento.
Convierte el blueprint direccional DEC-136 +
`evals/s276_multiturn_multihop_architecture_assessment_v1.md` (CANÓNICO — este diseño NO lo
repite: lo referencia y toma decisiones donde el assessment dejaba opciones) en un plan de build
ejecutable bajo el modelo operativo s279+ (Alberto, 22-jul): **Opus 4.8 ejecuta las lanes; Fable 5
orquesta/valida/revisa**; presupuesto Fable ≤$100 autorizado con mandato de optimización.
**Mandato de Alberto:** diseño primero; solución BP/robusta/escalable.

## 0. Alcance decidido (donde el assessment dejaba abanico)

- **Se construye: Fase 0 (cimiento shadow, $0/query) y Fase 1 (multi-turn útil).**
- **Se diseña con gates pero NO se construye aún: Fases 2 (multi-hop bounded), 3 (verifier), 4
  (repair).** Cada una tiene gate pre-registrado (assessment §4) y NO se abre sin pasar el
  anterior + lectura de Alberto.
- Rationale: el valor inmediato para técnicos es conversación útil (follow-ups, referencias);
  multi-hop tiene NO-GOs adyacentes medidos (deep-lookup S95) y exige eval orgánico que no existe
  hasta ~sept. Anti-scope-creep explícito.

## 1. Decisiones de arquitectura (resueltas aquí; el assessment las dejaba abiertas)

1. **Privilegios/schema + MECANISMO FÍSICO [FIX-ACCESO, el load-bearing del build]:** schema
   **PRIVADO `convo`** (no `public`). Las TABLAS no reciben ningún grant PostgREST. El acceso
   runtime es vía **RPCs SECURITY DEFINER** en el schema `convo`, expuestas SOLO a un rol
   dedicado (`convo_rpc`) que el bot usa por la MISMA pila httpx→PostgREST actual (cero
   dependencias nuevas). Cada RPC encapsula UNA transacción corta: `convo.ingress(...)`
   (dedup + orden/CAS), `convo.claim_run(...)` (lease/reclaim + fencing),
   `convo.complete_run(...)` (CAS propietario `running→answer_ready` + outbox `pending`
   ATÓMICOS), `convo.record_delivery(...)` (attempts/receipts). Alternativa DESCARTADA y
   declarada: driver PG directo en el hot path (dependencia runtime nueva + pooling Supavisor +
   implicaciones Railway). El corpus sigue por la vía actual — dos credenciales lógicas, una
   pila HTTP.
2. **DDL por fases y NO antes de la matriz RGPD:** las migraciones se PREPARAN como propuestas
   (patrón s278: `migration_proposals/`), y solo se aplican tras la **matriz de lifecycle firmada
   por Alberto** (categoría de dato · finalidad · TTL · actor de borrado · propagación a
   snapshots/runs/outbox/query_logs/backups/proveedor LLM). La matriz es un entregable de la Fase
   0 con plantilla incluida — decisión de Alberto, no de ingeniería (assessment §3.2).
3. **Orquestador transport-neutral:** módulo nuevo `src/orchestrator/` con los contratos del
   assessment (`TurnRequest`, `TurnPlan{single_hop|clarify}`, `RetrievalResult`, `TurnResult`);
   `telegram_bot._process_query` queda como adapter. El hot-path síncrono se AÍSLA en executor
   (assessment: no abrir hops concurrentes sobre clientes síncronos en el event loop) — la
   migración a async de clientes es OTRA fase, no un prerequisito de Fase 0/1.
4. **Verifier de Fase 3 [FIX-VERIFIER — sin «≡»]:** REUSA del Evidence Contract el LEDGER de
   obligaciones como generador de candidatos y la filosofía fail-closed; pero la atomización de
   claims respuesta→evidencia con entailment (el corazón del verifier del assessment §3.3-C) es
   un **componente NUEVO**, gateado por el contrato S260 ÍNTEGRO (cohorte fresca multichunk,
   control contemporáneo mismo-modelo, entailment claim↔fuente, cero tuning sobre residuales).
   El `DISCLOSE` del EC y el `disclose_insufficient` del verifier son HOMÓNIMOS, no equivalentes
   (el EC escribe en la respuesta; el verifier NO escribe — veredicto accept|clarify|
   disclose_insufficient|abstain). En Fases 0-1: validadores actuales, cero verifier LLM.
5. **Rewrite conversacional (Fase 1) — retake del patrón S99 CON sus gates:** solo se invoca si
   el turno NO es standalone (clasificador determinista primero: pronombres/deícticos/elipsis +
   ausencia de producto explícito); rewrite estructurado source-bound (modelo económico), conserva
   original+rewrite en el trace; gates del S99: dominio/decline (gas fuera), códigos técnicos
   verbatim (nunca se reescriben), cambio de producto explícito gana al historial, ambigüedad ⇒
   clarify. Re-ground SIEMPRE: el texto previo del bot jamás es evidencia (assessment §3.1).
6. **Working state y snapshots:** según assessment §3.1-3.2 sin cambios. Memoria durable de
   usuario: FUERA de este build (opt-in, fase posterior, decisión de producto).
7. **Effectively-once:** el paquete completo del assessment (dedup ingress por
   `(channel, external_update_id)` · orden por conversación con CAS `state_version` · lease +
   heartbeat + fencing token monotónico · CAS propietario en `running→answer_ready` · outbox
   transaccional con unique lógica + attempts/receipts) se implementa ÍNTEGRO en Fase 0 — es la
   parte barata de hacer bien ahora y carísima de retrofit.

8. **Carry-forward de 1h existente [FIX-CARRY, telegram_bot:509-524]:** en Fase 1 MIGRA a
   working state durable (misma semántica de resolución determinista, fuente de verdad ÚNICA);
   el mecanismo in-memory se RETIRA al activar Fase 1. El follow-up simple dentro de la ventana
   (hoy $0) debe seguir siendo $0 vía clasificador determinista + working state — caso dedicado
   en MT-1b que lo pinea.
9. **Concurrencia de transporte [FIX-PTB]:** Fases 0-1 mantienen el procesamiento SECUENCIAL de
   updates de PTB (como hoy, sin `concurrent_updates`); habilitarla es decisión de Fase 2 con
   audit de thread-safety de los clientes síncronos module-level. Los tests «2 concurrentes» de
   MT-1b ejercitan orden/CAS a nivel orquestador (inyección directa), no el transporte.

## 2. Esquema (propuesta de Fase 0 — NO aplicar sin matriz RGPD) [FIX-DDL · FIX-YAGNI]

Fase 0 crea SOLO el núcleo: `conversations`, `conversation_events`, `conversation_snapshots`,
`turn_runs`, `delivery_outbox` + `delivery_attempts`, en schema `convo`, con las constraints del
assessment §3.2 (identity bigint, `(conversation_id, id)`, unique `(channel, external_update_id)`,
partial indexes de leases/outbox, cero HTTP/LLM en transacción — garantizado por construcción:
las transacciones viven DENTRO de las RPCs §1.1). **El DDL COMPLETO (tipos, nullability, CHECKs
de estados, cascadas de borrado, scope de uniques, default privileges y el contrato transaccional
de cada RPC) es el ENTREGABLE de la lane MT-0b** — este diseño no lo declara «exacto».
DIFERIDO por YAGNI adjudicado: `retrieval_hops` → propuesta de Fase 2; `turn_evidence` /
`answer_claims` / `claim_support` → propuesta de Fase 3 (su shape depende del contrato S260, no
medido — congelarlo ahora sería especulativo y ampliaría la matriz RGPD sin datos que existan).

## 3. Plan de ejecución (modelo Opus-ejecuta / Fable-orquesta)

| Lane | Contenido | Modelo | Review |
|---|---|---|---|
| MT-0a | `src/orchestrator/` contratos + adapter single_hop paridad | Opus | Fable diff-review |
| MT-0b | DDL completo propuesto `convo` + RPCs SECURITY DEFINER + rol `convo_rpc` + matriz RGPD plantilla | Opus | Fable + **visto Alberto** |
| MT-0c | Ingress dedup + orden/CAS + lease/fencing + outbox (con tests de crash/restart/concurrencia) | Opus | Fable diff-review + dúo focal (zona effectively-once) |
| MT-0d | Persistencia de trazas retrieval/coverage existentes + shadow flag byte-invariante | Opus | Fable |
| MT-1a | Clasificador standalone determinista + rewrite gateado + trace | Opus | Fable + dúo focal (gates S99) |
| MT-1b | Eval multi-turn NUEVA (follow-ups, pronombres, cambio producto, corrección, no-contestable, reinicio, 2 concurrentes) — se construye ANTES de activar 1a | Opus | Fable |

Gates pre-registrados por fase = assessment §4 verbatim (Fase 0: paridad byte-a-byte + crash en
cada frontera + aislamiento de chats + lifecycle; Fase 1: eval nueva + no-regresión del harness
single-turn actual + coste 0 en standalone). Presupuesto [FIX-PRESUPUESTO]: por-LANE con kill-switch — cap de 3 rondas de
iteración por lane; superarlo escala a Alberto. El lado Fable corre in-session (plan); el
gasto API real (Sol/Opus) se estampa por lane en el DEC de cierre de cada fase. La
referencia s279 (una lane puede comer 4-7 rondas) invalida estimaciones optimistas —
se mide, no se promete.

## 4. Métricas y no-re-litigio

- Métrica de Fase 0 [FIX-PARIDAD]: **paridad byte-a-byte con INSTRUMENTO PROPIO** — un modo
  nuevo del harness conduce `TurnRequest` por el ORQUESTADOR con adapters stub/replay (seam
  `RagServingAdapters`); la paridad se define PRE-LLM (contexto/prompt/plan en bytes) + shadow de
  ejecución única para el resto. bvg queda como juez de NO-REGRESIÓN de calidad, no de paridad
  (entra por debajo del seam refactorizado — sería un gate vacuo).
- Umbrales auditables de Fase 1 [FIX-UMBRALES] (pre-registrados, control contemporáneo):
  precisión del clasificador standalone/dependiente ≥95% sobre MT-1b · corrección del rewrite
  (muestra adjudicada por Alberto, 0 entidades inventadas) · no-regresión del harness single-turn
  (mismos QIDs, misma vara) · tasa de clarify-indebido <5% en standalone · latencia p50 por ruta
  declarada · coste = 0 en standalone, 1 llamada económica máx en dependiente.
- Métrica de Fase 1: la eval multi-turn nueva (MT-1b) + no-regresión del single-turn.
- NO se re-abre: S206/S216/S235 (checklist/multiwriter — el diseño usa hops+writer único),
  agente abierto (descartado con state machine en su lugar), GraphRAG, embeddings-de-transcript
  (assessment §5). El deep-lookup S95 NO-GO se respeta: multi-hop solo con router/budget cerrado
  y NUNCA como agente libre.

## 5. Gaps declarados

1. [FIX-RGPD] La matriz de lifecycle la decide Alberto CON validación legal (no es una
   suposición de ingeniería) y bloquea TODO DDL de `convo` y todo dato conversacional real:
   hasta su aprobación, el código de Fase 0 se verifica EXCLUSIVAMENTE con tests sintéticos
   (fixtures/stubs). Sin staging con conversaciones reales — eso ya sería tratamiento.
2. La eval MT-1b se construye sin tráfico orgánico (llega ~sept) — se declara dev-eval; el gate
   orgánico queda para cuando exista.
3. El aislamiento del executor (síncrono-en-thread) es un puente: la migración async de clientes
   es deuda declarada para antes de Fase 2 (hops concurrentes).
4. Coste de Fase 1 en el slice dependiente: 1 llamada económica (rewrite) — se mide en la eval.
5. H0 de s279 (campaña de backfill de identidad) es workstream paralelo independiente — no lo
   absorbe este diseño.
