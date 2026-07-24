# Matriz de lifecycle RGPD — datos conversacionales (schema `convo`, s281 Fase 0)

**Estado: PLANTILLA SIN FIRMAR. Todas las celdas `[DECIDIR]` requieren decisión de
Alberto CON validación legal (DPO / asesor). Ingeniería NO las supone.**

## Regla dura (bloqueante)

> NINGUNA migración de `convo` se aplica a la base de datos sin esta matriz
> **firmada** (categoría de dato · finalidad · base legal · TTL · actor de
> borrado · propagación). Bloquea:
> - `supabase/migration_proposals/20260723100000_s281_convo_schema_f0.sql` (schema/tablas)
> - `supabase/migration_proposals/20260723100001_s281_convo_rpcs_f0.sql` (RPCs)
>
> Hasta la firma, el código de Fase 0 se verifica **EXCLUSIVAMENTE con tests
> SINTÉTICOS** (fixtures/stubs). Cero conversaciones reales, ni siquiera en
> staging: almacenar tráfico real ya es tratamiento de datos personales.
> (Fix `RGPD-SIN-ESCAPATORIA` del dúo r1; assessment §3.2; diseño v2 §5.1.)

## Contexto que la firma debe fijar (transversal a todas las filas)

- **Responsable / encargado del tratamiento:** [DECIDIR] (Fontiber como responsable; canal Telegram y proveedores LLM como encargados).
- **Base legal por defecto candidata:** [DECIDIR] (¿interés legítimo del servicio técnico? ¿ejecución de contrato? ¿consentimiento para memoria durable opt-in?).
- **Aviso / información al interesado (técnico):** [DECIDIR] (texto y momento — p.ej. mensaje de bienvenida del bot).
- **Solicitud de borrado/anonimización:** activa un lifecycle destructivo explícito; el event log NO es "append-only inmune". El borrado debe ALCANZAR todas las columnas de propagación de la tabla de abajo.
- **Backups:** expiran por política documentada [DECIDIR: ventana]; no son excepción al borrado, se declaran como retención residual acotada.
- **Proveedor LLM (Claude / Voyage):** contrato/config con retención y tratamiento acordados [DECIDIR: cero-retención vs. retención X]; el texto enviado para generar/embedear sale del perímetro `convo`.

## Matriz por categoría de dato

Columnas de **propagación de borrado**: marca en cada una si el borrado de esta
categoría debe alcanzarla (S = sí / N = no / [DECIDIR]).

| # | Categoría de dato (columna origen) | ¿Dato personal? | Finalidad | Base legal | TTL | Actor de borrado | Prop → snapshots | Prop → turn_runs | Prop → outbox/attempts | Prop → query_logs | Prop → backups | Prop → proveedor LLM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Identificador de chat/canal (`conversations.channel`, `external_chat_id`) | Sí (identificador online) | Enrutar la conversación al técnico correcto | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | S | S | [DECIDIR] | [DECIDIR] | N |
| 2 | Handle público (`conversations.public_id`) | Pseudónimo | Referencia externa estable sin exponer el chat id | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | S | S | [DECIDIR] | [DECIDIR] | N |
| 3 | Tenant/owner interno (`conversations.tenant_id`) | No (metadato org.) | Aislamiento multi-fabricante (M&A) | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | N | N | [DECIDIR] | [DECIDIR] | N |
| 4 | Id de update del transporte (`conversation_events.external_update_id`) | Sí (ligado a identificador) | Dedup de ingress (effectively-once) | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | N | N | [DECIDIR] | [DECIDIR] | N |
| 5 | **Texto libre del técnico** (`conversation_events.content_text`, role='user') | **Sí — texto libre, dato personal potencial (posible cat. especial no intencionada)** | Entender la consulta técnica y responderla | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | [DECIDIR] | [DECIDIR] | [DECIDIR] | [DECIDIR] | **S (se envía al LLM)** |
| 6 | Respuesta del bot / tool output (`conversation_events.content_text`, role='assistant'/'tool') | Sí (puede reflejar dato del hilo) | Historial conversacional, follow-ups | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | [DECIDIR] | [DECIDIR] | [DECIDIR] | [DECIDIR] | [DECIDIR] |
| 7 | Payload estructurado del evento (`conversation_events.payload`) | [DECIDIR] (según contenido) | Trace del pipeline | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | [DECIDIR] | N | [DECIDIR] | [DECIDIR] | N |
| 8 | Working state / summary (`conversation_snapshots.working_state`, `summary_text`) | Sí (derivado de mensajes) | Estado de trabajo durable, resúmenes | [DECIDIR] | [DECIDIR] | [DECIDIR] | (esta tabla) | [DECIDIR] | N | [DECIDIR] | [DECIDIR] | [DECIDIR] |
| 9 | Metadata de cómputo del turno (`turn_runs`: modelo/prompt, tokens, coste, latencia, error) | No (operativo, ligado a conversación) | Observabilidad, coste, diagnóstico | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | (esta tabla) | N | [DECIDIR] | [DECIDIR] | N |
| 10 | Identidad de worker/lease (`turn_runs.lease_owner`) | No (id interno de proceso) | Fencing / effectively-once | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | (esta tabla) | N | N | [DECIDIR] | N |
| 11 | Respuesta final entregada (`delivery_outbox.payload_text`) | Sí (puede reflejar dato del hilo) | Outbox transaccional, reintentos | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | N | (esta tabla) | [DECIDIR] | [DECIDIR] | N |
| 12 | Destino/receipt de entrega (`delivery_outbox.destination`, `external_receipt`; `delivery_attempts.external_receipt`) | Sí (identificador de destino) | Conciliación de entrega, no-reemisión | [DECIDIR] | [DECIDIR] | [DECIDIR] | N | N | (esta tabla) | [DECIDIR] | [DECIDIR] | N |
| 13 | Timestamps de ciclo de vida (todas las tablas `*_at`) | No (metadato) | Auditoría, TTL, lifecycle | [DECIDIR] | [DECIDIR] | [DECIDIR] | S | S | S | [DECIDIR] | [DECIDIR] | N |

## Notas de propagación (para completar en la firma)

- El borrado/anonimización de una conversación debe alcanzar, como mínimo:
  `conversation_events`, `conversation_snapshots`, `turn_runs`,
  `delivery_outbox`, `delivery_attempts`, más `query_logs`, cachés, exports y
  colas fuera de `convo` (assessment §3.2). Las FK `ON DELETE CASCADE` del
  schema propagan DENTRO de `convo` al borrar la fila `conversations`; el resto
  (query_logs, backups, proveedor LLM) es propagación FUERA de `convo` y se
  decide aquí.
- `status = 'erased'` en `conversations` es el estado terminal de anonimización
  previsto por el schema; la firma debe definir si el borrado es físico (DELETE
  con cascada) o anonimización in-place (qué columnas se nulan/hashean).
- Memoria durable de usuario: FUERA de este build (opt-in, fase posterior); si
  se añade, entra como fila nueva con base legal = consentimiento.

## Firma

- **Decidido por:** ____________________  **Fecha:** __________
- **Validación legal (DPO/asesor):** ____________________  **Fecha:** __________
