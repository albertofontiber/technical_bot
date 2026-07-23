# s280 — Diseño BUILDABLE multi-turn / multi-hop (v1, PRE-dúo)

**Estado:** BORRADOR para Protocolo 3 (Sol + Fable). Convierte el blueprint direccional DEC-136 +
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

1. **Privilegios/schema [assessment §3.2 último párrafo]:** schema **PRIVADO `convo`** (no
   `public`), accedido por un rol backend NUEVO de mínimos privilegios (`convo_rw`: INSERT/SELECT/
   UPDATE solo sobre las tablas del schema; sin acceso a `public.chunks*`). El bot usa DOS
   conexiones lógicas: la actual (service, corpus RO) y `convo_rw` (estado conversacional). NO se
   finge RLS donde una service key la bypassa: la frontera es el schema + el rol. Data API de
   Supabase NO expone `convo` (sin grants a anon/authenticated/PostgREST roles).
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
4. **Verifier ≡ reuso del Evidence Contract (s278):** el verifier de Fase 3 consume el MISMO
   primitivo (`evidence_contract.apply_evidence_contract` → ledger de obligaciones + validación
   de cobertura/citas/conflictos, fail-closed, sin QID). En Fases 0-1 los validadores actuales
   (must_preserve/EC bajo perfil) siguen siendo la única verificación — cero verifier LLM nuevo.
   El contrato de S260 (cohorte fresca, entailment, control mismo-modelo) queda pineado como gate
   de la Fase 3, sin excepciones.
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

## 2. Esquema (propuesta DDL de Fase 0 — NO aplicar sin matriz RGPD)

Tablas y constraints EXACTAS del assessment §3.2 (`conversations`, `conversation_events`,
`conversation_snapshots`, `turn_runs`, `retrieval_hops`, `turn_evidence`/`answer_claims`/
`claim_support`, `delivery_outbox`/`delivery_attempts`), en schema `convo`, con: identity bigint
para eventos, índice `(conversation_id, id)`, unique `(channel, external_update_id)`, partial
indexes para leases y outbox pendientes, y CERO llamadas HTTP/LLM dentro de transacción.
`retrieval_hops`/`turn_evidence`/`answer_claims`/`claim_support` se CREAN en Fase 0 pero solo se
ESCRIBEN desde Fase 2/3 (evita migración incremental del núcleo).

## 3. Plan de ejecución (modelo Opus-ejecuta / Fable-orquesta)

| Lane | Contenido | Modelo | Review |
|---|---|---|---|
| MT-0a | `src/orchestrator/` contratos + adapter single_hop paridad | Opus | Fable diff-review |
| MT-0b | Migraciones propuestas `convo` + rol `convo_rw` + matriz RGPD plantilla | Opus | Fable + **visto Alberto** |
| MT-0c | Ingress dedup + orden/CAS + lease/fencing + outbox (con tests de crash/restart/concurrencia) | Opus | Fable diff-review + dúo focal (zona effectively-once) |
| MT-0d | Persistencia de trazas retrieval/coverage existentes + shadow flag byte-invariante | Opus | Fable |
| MT-1a | Clasificador standalone determinista + rewrite gateado + trace | Opus | Fable + dúo focal (gates S99) |
| MT-1b | Eval multi-turn NUEVA (follow-ups, pronombres, cambio producto, corrección, no-contestable, reinicio, 2 concurrentes) — se construye ANTES de activar 1a | Opus | Fable |

Gates pre-registrados por fase = assessment §4 verbatim (Fase 0: paridad byte-a-byte + crash en
cada frontera + aislamiento de chats + lifecycle; Fase 1: eval nueva + no-regresión del harness
single-turn actual + coste 0 en standalone). Presupuesto Fable estimado: diseño+dúo+reviews
≈$25-40 del cap $100; ejecución en Opus.

## 4. Métricas y no-re-litigio

- Métrica de Fase 0: **paridad byte-a-byte** (el harness bvg actual como juez de igualdad) — no
  toca los levers settled de calidad.
- Métrica de Fase 1: la eval multi-turn nueva (MT-1b) + no-regresión del single-turn.
- NO se re-abre: S206/S216/S235 (checklist/multiwriter — el diseño usa hops+writer único),
  agente abierto (descartado con state machine en su lugar), GraphRAG, embeddings-de-transcript
  (assessment §5). El deep-lookup S95 NO-GO se respeta: multi-hop solo con router/budget cerrado
  y NUNCA como agente libre.

## 5. Gaps declarados

1. La matriz RGPD requiere decisión legal de Alberto — bloquea el DDL, no el código de Fase 0
   (que puede correr contra schema en shadow con tablas en una DB de staging o el proposal
   aplicado tras el visto).
2. La eval MT-1b se construye sin tráfico orgánico (llega ~sept) — se declara dev-eval; el gate
   orgánico queda para cuando exista.
3. El aislamiento del executor (síncrono-en-thread) es un puente: la migración async de clientes
   es deuda declarada para antes de Fase 2 (hops concurrentes).
4. Coste de Fase 1 en el slice dependiente: 1 llamada económica (rewrite) — se mide en la eval.
5. H0 de s279 (campaña de backfill de identidad) es workstream paralelo independiente — no lo
   absorbe este diseño.
