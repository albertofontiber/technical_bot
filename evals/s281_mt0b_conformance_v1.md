# s281 MT-0b — Nota de conformidad (entregables vs. fixes vinculantes)

Lane MT-0b (Opus ejecuta; Fable + visto Alberto revisan). Entregables:

- `supabase/migration_proposals/20260723100000_s281_convo_schema_f0.sql` — schema `convo` + rol `convo_rpc`.
- `supabase/migration_proposals/20260723100001_s281_convo_rpcs_f0.sql` — 8 RPCs SECURITY DEFINER (los 5 grupos del brief + `fail_run`, fix del orquestador).
- `docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md` — plantilla de matriz de lifecycle.
- este documento.

## 1. Fixes vinculantes del dúo r1 → cómo los satisface el entregable

| Fix (dúo r1) | Cómo lo satisface | Dónde |
|---|---|---|
| **ACCESO-FISICO-CONVO** | Tablas de `convo` SIN grants a anon/authenticated/service_role; acceso runtime EXCLUSIVO vía RPCs SECURITY DEFINER expuestas SOLO a `convo_rpc` (NOLOGIN/NOINHERIT, impersonado por `authenticator` con SET ROLE, mismo patrón que `p1_readonly`). `convo_rpc` no recibe NINGÚN privilegio de tabla directo. Cada RPC = una txn corta, cero HTTP/LLM dentro. | schema §0, §7; RPCs (contrato global + grants a convo_rpc) |
| **DDL-BUILDABLE** | DDL completo: tipos concretos, nullability explícita, CHECKs de la máquina de estados (`turn_runs`, `delivery_outbox`, `delivery_attempts`) + invariantes de fila (running exige lease; answer_ready/delivered exigen timestamps), FKs con `ON DELETE CASCADE` razonada, uniques CON scope, partial indexes de leases activos y outbox pendiente, `fencing_token bigint` monotónico, default privileges + REVOKE. | schema §1-§7 |
| **YAGNI-TABLAS** | Se crean SOLO: `conversations`, `conversation_events`, `conversation_snapshots`, `turn_runs`, `delivery_outbox`, `delivery_attempts`. `retrieval_hops` (F2) y `turn_evidence`/`answer_claims`/`claim_support` (F3) NO se crean — declarado en la cabecera. | schema (cabecera + tablas 1-6) |
| **RGPD-SIN-ESCAPATORIA** | Plantilla de matriz con la regla dura al inicio: ninguna migración de A/B se aplica sin firma (Alberto + validación legal); hasta entonces solo tests SINTÉTICOS, sin staging real. Ambos `.sql` llevan el banner "BLOQUEADA POR MATRIZ RGPD / NO_GO_FOR_DB". Fila por cada categoría de dato (incl. texto libre del técnico = fila 5) con celdas `[DECIDIR]`. | `RGPD_LIFECYCLE_MATRIX_TEMPLATE.md`; cabecera de ambos `.sql` |

## 2. Paquete effectively-once (assessment §3.2) → mecanismo

| Propiedad | Mecanismo | Dónde |
|---|---|---|
| **Dedup de ingress** | `UNIQUE (channel, external_update_id)` en `conversation_events` + `convo.ingress` con `ON CONFLICT DO NOTHING` → update reentrante devuelve el mismo id con `is_new_event=false`, cero filas nuevas. | schema tabla 2; RPC (1) |
| **Orden por conversación / CAS** | `conversations.state_version` monotónico avanzado por `ingress` en cada evento nuevo; `conversation_events.id` (bigint identity) = orden global; índice `(conversation_id, id)`. | schema tablas 1-2; RPC (1) |
| **Lease + heartbeat + fencing** | `turn_runs.fencing_token bigint` incrementado en cada claim/reclaim; `claim_run` (pending→running), `heartbeat_run` (extiende solo el owner exacto), `reclaim_run` (lease vencido o failed → fencing++/attempt++, acotado por max_attempts). Partial indexes de leases activos y reclamables. | schema tabla 4; RPCs (2a/2b/2c) |
| **Máquina de estados completa (running→failed)** | `fail_run`: CAS propietario running→failed (mismo guard que `complete_run`) sella `failed_at` + `error_class`/`error_detail`; sin ella `failed` era inalcanzable y el retry-de-failed de `reclaim_run` nunca ejercitable. | schema tabla 4; RPC (6) |
| **CAS propietario running→answer_ready + outbox atómico** | `complete_run`: UPDATE guardado por `(id, compute_status=running, lease_owner, fencing_token)` + INSERT del outbox `pending` en la MISMA transacción. Un claim stale (fencing viejo) falla limpio, cero efecto. | RPC (3) |
| **Outbox transaccional + attempts/receipts** | `delivery_outbox` con `UNIQUE (turn_run_id, channel, destination, logical_delivery_key)` (2ª barrera, no sustituye fencing); `begin_delivery` (CAS pending/retryable→sending antes del envío HTTP externo) + `record_delivery` (acuse: delivered idempotente / retryable / dead_letter). El acuse se guarda con `attempt_status='sending'` → un 2º acuse no re-pisa receipt (`attempt_already_sealed`). No reemite un delivery confirmado. **Recovery de `sending` atascado** (sender caído entre `begin_delivery` y `record_delivery`): la fila queda `sending` y el índice de pendientes NO la ve → partial index `delivery_outbox_sending_stale_idx` la expone; el **janitor de MT-0c** (responsabilidad del orquestador; los datos ya lo soportan) escanea `sending` con `next_attempt_at < now()` y la sella vía `record_delivery(success=false, error_class='sending_lease_expired')` → `retryable`/`dead_letter`. | schema tablas 5-6 (+ índice sending-stale); RPCs (5a/5b) |

## 3. Decisiones tomadas donde el diseño dejaba libertad

1. **`ingress` crea el `turn_runs` pending** para eventos `role='user'` (idempotente por `UNIQUE input_event_id`), en vez de diferirlo a `claim_run`. Motivo: mantiene la creación de run dentro del effectively-once (una sola fila por evento) y da a `claim_run` algo que reclamar; un turno de usuario siempre engendra un turno de cómputo.
2. **`heartbeat_run` separado de `claim_run`**, y **`reclaim_run` separado** (uno para adquisición limpia de pending, otro para lease vencido/failed). Motivo: mapear 1:1 los grupos (2) y (4) del brief sin solapar predicados ambiguos; el CAS de cada uno es distinto.
3. **Entrega en dos fases** (`begin_delivery` claim + `record_delivery` acuse). Motivo: el envío a Telegram es HTTP y debe ocurrir FUERA de la transacción; claim-antes-de-enviar es lo que evita doble-envío (assessment: "no HTTP dentro de txn").
4. **`SET search_path = pg_catalog`** + tablas siempre cualificadas `convo.*` (en vez de `search_path = ''` con todo pg_catalog-cualificado). Motivo: legibilidad con la misma garantía anti-shadowing; los builtins resuelven, las tablas van explícitas.
5. **Membresía `authenticator`/`postgres` → `convo_rpc`** (SET TRUE, INHERIT FALSE) incluida y guardada por existencia de rol. Motivo: sin ella los RPCs no serían alcanzables por PostgREST; espeja el precedente `p1_readonly`. **[ORQUESTADOR: verificar contra el diseño]** — ver desviación D2.
6. **`last_event_id` sin FK** (puntero denormalizado mantenido por RPCs). Motivo: evita el ciclo de FK `conversations`↔`conversation_events` en el INSERT.
7. **`status='erased'` + `retention_class/expires_at`** en `conversations` como ganchos de lifecycle. Motivo: dar a la matriz RGPD un estado terminal de anonimización sobre el que decidir (físico vs. in-place).

## 4. Desviaciones declaradas (no silenciosas)

- **D1 — RESUELTA (rename `convo_rw` → `convo_rpc`).** El brief de MT-0b nombraba el rol `convo_rw`; el canónico diseño v2 §1.1 y §3 lo llaman `convo_rpc` (2 ocurrencias verificadas). El orquestador adjudicó el rename a `convo_rpc` (brief erró; el rol no tiene write directo, `convo_rpc` describe mejor su función). Aplicado en TODO: rol, comentarios, grants, `COMMENT ON ROLE`, membresías, y esta nota. Cerrada.
- **D2 — exposición de schema a PostgREST es config de OPS, no DDL.** Para que `/rpc/<fn>` resuelva, `convo` debe añadirse a `PGRST_DB_SCHEMAS` (Accept-Profile: convo) en el dashboard Supabase. Declarado en la cabecera del schema; no es aplicable vía migración. Exponer el schema es seguro porque las tablas no tienen grants.
- **D3 — writer de `conversation_snapshots` fuera de scope de MT-0b.** El brief especifica los grupos de RPC del effectively-once (ingress, claim/lease, complete+outbox, reclaim, delivery) + `fail_run` (fix del orquestador). La tabla `conversation_snapshots` se crea (requerida por el diseño §2) pero su RPC de escritura de working-state se difiere a MT-0c. Declarado en el COMMENT de la tabla.
- **D4 — enforcement de transiciones de estado por RPC, no por CHECK.** Un CHECK no ve el estado anterior; las transiciones (pending→running, etc.) se fuerzan por los predicados CAS de las RPCs. Los CHECKs solo restringen el conjunto de estados y los invariantes de fila. Documentado en el comentario de la máquina de estados (`turn_runs`).
- **D5 — propuesta NO validada en Postgres vivo.** Los `.sql` son sintácticamente plausibles para PG15/Supabase y coherentes internamente (nombres de columna, aridad de firmas en los grants, estados CHECK vs. usados por las RPCs revisados dos veces), pero no se han ejecutado (no hay acceso a DB y está prohibido). El apply/rollback en Postgres desechable es paso de una lane posterior, igual que el precedente s117 M0b.
- **D6 — REVOKE/GRANT sobre roles Supabase sin guarda de existencia.** Los `REVOKE ... FROM anon, authenticated, service_role` (schema §0, §7) y los `REVOKE ... FROM ... service_role` del `DO $grants$` (RPCs) asumen que esos roles EXISTEN — a diferencia del `DO $membership$`, que sí guarda `authenticator`/`postgres` por existencia. En Supabase real esos tres roles existen siempre; en un Postgres desechable de CI fallarían. **Declarado, no arreglado aquí:** la lane de validación apply/rollback debe pre-crear `anon`/`authenticated`/`service_role` (o añadir guardas de existencia entonces). No se guardan aquí para no divergir del estilo directo del precedente (`p1_readonly` también hace REVOKE directo sobre estos roles).

## 5. Verificación de coherencia interna (hecha)

- Estados de `turn_runs.compute_status` en el CHECK = `{pending, running, answer_ready, delivered, failed}` = exactamente los que usan las 8 RPCs (incl. `fail_run` que escribe `failed`).
- Estados de `delivery_outbox.delivery_status` en el CHECK = `{pending, sending, delivered, retryable, dead_letter}` = los usados por `begin_delivery`/`record_delivery`/`complete_run`.
- Nombres de columna referenciados por las RPCs verificados contra el DDL (conversations, conversation_events, turn_runs, delivery_outbox, delivery_attempts).
- Firmas de función en el bloque de grants (`DO $grants$`) con la aridad/tipos exactos de cada `CREATE FUNCTION` — 8 entradas, incl. `convo.fail_run(bigint,text,bigint,text,text)`.
- Índices de `delivery_outbox`: pendiente (`pending`/`retryable`) + sending-atascado (`sending`) = cobertura de las 3 rutas del sender.
- Sin BEGIN/COMMIT envolvente (convención codificada en tests/test_s277_hp011). Ningún test genérico lintea `migration_proposals/` (el glob de linteo es sobre `supabase/migrations/`).
