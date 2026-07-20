# S276 — assessment estructural y norte multi-turn / multi-hop

Estado: `DIRECTIONAL_BLUEPRINT_NO_BUILD_AUTHORIZATION`

Este documento responde dos preguntas distintas sin atribuir a una la evidencia de la otra:

1. si un cambio estructural de síntesis podría atacar los seis `synthesis-miss` residuales;
2. qué cimiento conviene preparar para un chatbot multi-turn y multi-hop robusto, escalable y
   sensible a coste.

No autoriza migraciones, flags, llamadas de modelos, target probes, deploy ni crédito de facts.

## 1. Evidencia local que limita la recomendación

- Foto diagnóstica banked: `146/154 = 94,81 %`, con 6 synthesis-miss y 2 retrieval-miss.
  Sigue sin ser un KPI atómico oficial porque conserva 77 legacy carries.
- El reach audit S275 demuestra que cuatro spans residuales ya estaban servidos al 100 %, uno al
  86,68 % con todos sus anchors presentes y sólo `obl_b2043` al 0 %. Por tanto, añadir contexto
  indiscriminadamente no es una vía causal a +5.
- Causas residuales observadas:
  - `obl_b2043`: gap puro de serving-view;
  - `obl_2f5d`: evidencia servida pero no citada;
  - `obl_7bba`, `obl_015f`, `obl_7aa7`: selección/cita/binding de la relación;
  - `obl_a5d9`: detección/selección semántica del qualifier.
- El runtime actual es single-turn salvo un carry-forward en memoria del modelo detectado durante
  una hora (`src/bot/telegram_bot.py:509-524`). No existe conversación durable, event log, estado
  versionado, hop receipt ni claim/evidence trace. `query_logs` guarda una fila plana por consulta.
- La ruta viva hace retrieve → rerank → coverage → una generación libre → planner/postcondición
  must-preserve (`src/bot/telegram_bot.py:542-606`, `src/rag/generator.py:645-795`).
- `retrieve_chunks` y `apply_post_rerank_coverage_with_trace` ya ofrecen seams de traza, pero el
  handler de Telegram no los persiste. Además, el hot path async llama clientes síncronos de
  retrieval, Anthropic y Supabase; varios hops bloquearían el event loop si no se extrae o aísla.

### Líneas previas: outcomes medidos, cierres de diseño y mecanismos no medidos

- Ledger genérico de facetas S206: 0 relaciones residuales estables, 0 preguntas completas y
  1 regresión protegida en 28 llamadas. NO-GO para synthesis-miss.
- Descomposición question-only S216: CLOSED NO-GO en diseño; la cohorte single-source no
  representaba el objetivo multichunk y la completitud no bloqueaba.
- Clause-bound multi-writer S235/S242: 0 strict causal gains, 3 regresiones protegidas y
  1 conflicto inseguro. NO-GO.
- Evidence-claim IR S260: no fue refutado por outcome; se cerró antes de generación porque faltaban
  cohorte estructural independiente, control contemporáneo mismo-modelo y validación
  claim↔fragmento. Está `NOT_MEASURED`, no `GO`.
- Planner integrado S248/S122: sólo 1/12 residuales entró al plan, 0/12 fue enforceable y una
  pregunta fue sustituida por fail-closed. No es el cimiento del orquestador nuevo.
- Mecanismo-de-anexo S274: agotado para los seis tras cuatro probes; no existe probe #5.
- Agentic deep lookup S95/DEC-089, medido sobre retrieval-miss: 12→11, 0/6 en testbed. No justifica
  un agente abierto como solución general.

La métrica de hoy es fact coverage de synthesis-miss; los NO-GO de S206 y S235 sí pisan ese
objetivo. El deep lookup fue medido sobre retrieval y no zanja la futura necesidad multi-hop,
pero sí desaconseja desplegarla sin routing y presupuesto cerrado.

## 2. Qué significa 94,81 %, 98 % y 100 %

`facts OK` es una vara interna, no un estándar interoperable de RAG. RAGAS y ARES separan, entre
otros ejes, relevancia del contexto, fidelidad y relevancia/calidad de respuesta. No existe un
porcentaje universal de “RAG best practice”. CRAG observó un resultado muy inferior en un benchmark
abierto difícil; no es numéricamente comparable con este corpus cerrado, pero refuta que 100 % sea
lo normal en RAG generativo.

Como orientación estadística y suponiendo —de forma optimista— facts iid:

| Foto | Point estimate | Wilson 95 % aproximado |
|---|---:|---:|
| 146/154 | 94,81 % | 90,1–97,3 % |
| 151/154 | 98,05 % | 94,4–99,3 % |
| 154/154 | 100 % | 97,6–100 % |

Los facts comparten preguntas y mecanismos y el set ha guiado iteraciones, así que iid no se
cumple y los intervalos son sólo ilustrativos. Incluso 154/154 no certificaría por sí solo una
tasa real ≥98 %; con cero fallos harían falta aproximadamente 189 hechos frescos e independientes
para que el límite Wilson inferior supere 98 %.

Interpretación propuesta:

- 98,05 % puede mantenerse como hito interno, no como certificado de fiabilidad productiva.
- Para facts críticos, el SLO correcto es “100 % soportado o aclarar/abstener”, no “el writer libre
  acierta siempre”.
- El release scorecard debe separar: desarrollo conocido, holdout fresco, tráfico orgánico y
  all-core-facts-per-question. Un promedio por facts puede ocultar respuestas incompletas.

## 3. Recomendación estructural

Construir un **orquestador acotado y source-bound** con una ruta barata single-hop por defecto.
La unidad persistente no será el prompt ni el transcript completo, sino el turno y sus objetos
auditables:

`turn → resolved context → retrieval hop(s) → evidence units → claims/support → verification → answer`

El primer refactor extrae `_process_query` a un servicio transport-neutral. Sus contratos mínimos
son `TurnRequest`, `TurnPlan`, `RetrievalResult` y `TurnResult`; Telegram queda como adapter de
ingress/egress. En Fase 0 el `TurnPlan` sólo puede ser `single_hop` o `clarify` y delega al pipeline
actual, lo que permite demostrar paridad antes de introducir comportamiento multi-hop.

### 3.1 Memoria en capas

1. **Event log durable e inmutable mientras el registro exista dentro de su política de
   retención**: mensajes, eventos de herramienta y estados del run. Es la verdad canónica
   operativa. Una solicitud válida de borrado/anonimización activa un lifecycle destructivo
   explícito; no se presenta como compatible por definición con «append-only».
2. **Working state pequeño y versionado**: producto/manual activo, locale/revisión, referencias
   pendientes, restricciones y `last_event_id`. Nunca es la única copia de la conversación.
3. **Summary derivado**: lleva versión y rango de eventos fuente. Se puede regenerar; no reemplaza
   el log.
4. **Memoria durable de usuario**: sólo opt-in, con procedencia y caducidad. No se embebe cada
   mensaje automáticamente ni se mezcla el historial con el corpus técnico.

Regla de seguridad: una respuesta anterior del bot puede resolver “eso” o el producto activo,
pero no se convierte en evidencia técnica. Toda afirmación técnica se vuelve a groundear en los
manuales.

### 3.2 Estado y esquema propuesto, aún sin DDL

- `conversations`: ID público, owner/tenant interno, canal/chat externo, status, versión de estado,
  timestamps y retención.
- `conversation_events`: `bigint identity`, FK a conversación, turn/idempotency key, rol/tipo,
  contenido y timestamp; índice `(conversation_id, id)` para cursor pagination.
- `conversation_snapshots`: versión, `through_event_id`, scope/resumen/referencias y provenance.
- `turn_runs`: input event, pipeline/model/prompt versions, ruta, `compute_status`, tokens, coste, latencia,
  error, `attempt_no`, `lease_owner`, `lease_expires_at`, `fencing_token` monotónico y timestamps.
  Estados de cómputo mínimos: `received → running → answer_ready`, con `failed`/reclaim explícitos.
- `retrieval_hops`: `turn_run_id`, número de hop, standalone query, dependencia, IDs/receipts,
  sufficiency/stop reason.
- `turn_evidence` + `answer_claims` + `claim_support`: relaciones normalizadas; JSONB sólo para
  payloads flexibles de trace, no para las claves relacionales.
- `delivery_outbox` + `delivery_attempts`: respuesta final, canal/destino, `delivery_status`
  (`pending → sending → delivered`, con `retryable/dead_letter`), intentos, receipt externo y
  timestamps. El outbox `pending` se crea en la misma transacción corta que marca el run
  `answer_ready`; el envío a Telegram ocurre después, fuera de esa transacción. `completed` es un
  estado agregado derivado sólo cuando han terminado las entregas requeridas. Unique mínima:
  `(turn_run_id, channel, destination, logical_delivery_key)`.

Constraints e índices obligatorios: unique sobre `(channel, external_update_id)`, secuencia/orden
por conversación, FK indexadas, `(conversation_id, id)`, `(turn_run_id, hop_no)`, y partial indexes
para leases y outbox pendientes. Transacciones cortas; ninguna llamada HTTP/LLM dentro de una
transacción. La concurrencia por chat se resuelve con compare-and-swap sobre `state_version` o una
cola por conversación. Lease + heartbeat permiten reclamar un run abandonado; una máquina caída
puede repetir cómputo si el proveedor LLM no ofrece idempotencia, pero el delivery ledger evita
reemitir deliberadamente un resultado ya confirmado.

El lease por sí solo no da ownership: toda transición `running → answer_ready` y la creación del
outbox `pending` deben hacer CAS sobre `(run_id, attempt_no, lease_owner, fencing_token,
compute_status=running)` en
la misma transacción. Un reclaim incrementa el fencing token; así un worker obsoleto ya no puede
completar ni publicar después del nuevo propietario. La unique del outbox es una segunda barrera,
no sustituye el fencing.

No se promete exactly-once sobre Telegram: existe una ventana irresoluble si el proceso cae después
del envío y antes de persistir el receipt. El objetivo honesto es procesamiento y entrega
**effectively-once**, con deduplicación de ingress, orden por conversación, outbox transaccional,
reintentos acotados y conciliación de receipts.

Las tablas de conversación no deben quedar expuestas por accidente en `public`. Si se sirven por
Data API: grants mínimos + RLS de ownership/tenant y columnas RLS indexadas. Dado que Telegram no
aporta un `auth.uid()` de Supabase y el runtime hoy usa `service_role`, el diseño de build debe elegir
explícitamente entre un rol DB backend de mínimos privilegios en schema privado o una capa de auth;
no debe fingir que RLS protege una ruta que la service key bypassa.

Antes de DDL debe existir una matriz de lifecycle revisada con el responsable de privacidad/DPO:
categoría de dato, finalidad/base aplicable, aviso/consentimiento cuando corresponda, TTL, actor de
borrado y propagación. El borrado/anonimización debe alcanzar `conversation_events`, snapshots,
runs, hops, evidence/claims, outbox, `query_logs`, caches, exports y colas; las copias de seguridad
expiran por una política documentada, y los proveedores LLM se configuran/contratan con la
retención y tratamiento acordados. La memoria durable de usuario sigue siendo opt-in y mínima.
Este documento define el control técnico; la base jurídica y los plazos concretos requieren
validación legal, no una suposición del equipo de ingeniería.

### 3.3 Ruta de ejecución adaptativa

**Ruta A — default barata**

1. Resolver determinísticamente producto/referencias cuando sea inequívoco.
2. Si la query ya es standalone: retrieval actual + writer actual, sin llamada adicional.
3. Si depende del historial: rewrite estructurado y source-bound; conservar query original y
   rewrite en el trace.
4. Sin verifier LLM adicional para preguntas simples con soporte suficiente y validators locales
   limpios.

El reescritor conversacional no parte de cero: S99 ya lo reconoció como patrón BP, pero quedó
aparcado porque no arreglaba el caso CS4 y podía convertir una query de gas en una respuesta
out-of-domain. Su retake exige gates explícitos de dominio/decline, códigos técnicos, cambio de
tema/producto y controles standalone; no se reactiva como llamada universal.

**Ruta B — multi-hop acotada**

Se activa sólo si la pregunta depende de evidencia aún no disponible, tiene subproblemas enlazados
o falla el gate de suficiencia. Máximo inicial: 2–3 hops. Cada hop produce subquery, dependencia,
evidencia y receipt. Stops obligatorios: evidencia suficiente, query repetida, cero progreso,
ambigüedad material, límite de latencia/coste o máximo de hops. Si falta identidad/producto o la
cadena no cierra, se aclara al usuario; no se rellena con conocimiento paramétrico.

El default inicial es 2 hops y 3 es hard cap. Subqueries independientes pueden recuperar en
paralelo; un hop sólo es secuencial cuando depende de una entidad o referencia descubierta en el
anterior. Se hace una única redacción final sobre la evidencia fusionada.

No se persiste chain-of-thought libre. Sólo estado operativo estructurado y motivos de ruta/stop.

**Ruta C — verificación condicional; repair deshabilitado inicialmente**

- Validadores deterministas actuales siguen cubriendo números, bundles, warnings y citas.
- En preguntas fact-dense, multi-hop o con baja suficiencia, un verifier separado atomiza claims,
  comprueba soporte/binding y marca omisiones candidatas contra evidence units query-relevant.
- En la primera versión el verifier sólo puede `accept` o fallar cerrado hacia
  `clarify | disclose_insufficient | abstain`; no escribe ni fusiona claims.
- Contradicción, ambigüedad o soporte insuficiente nunca activa una regeneración silenciosa.

Esta C es el mecanismo con causalidad plausible para cinco residuales post-retrieval, pero **no está
demostrada**. Antes de target o runtime exige el contrato pendiente de S260: cohorte fresca
multichunk positiva/negativa, control contemporáneo mismo-modelo, entailment claim↔fuente,
completitud bloqueante, revisión full-answer y cero tuning sobre los seis residuales.

Un repair generativo sería una fase posterior y se reconoce como **segundo writer pass**, no como
«un único writer». Sólo puede reabrirse con gate propio, merge determinista, support/citation
receipt para cada adición, manejo explícito de conflictos y revalidación de la respuesta completa;
sin esas condiciones reabre la superficie de regresión de S235.

## 4. Fases por coste y gates

### Fase 0 — cimiento sin cambio de respuestas

- Introducir interfaces `TurnContext`, `TurnRun`, `RetrievalHop`, `EvidenceReceipt` y un adapter
  single-hop que llame exactamente al pipeline actual.
- Persistir event log, state version, deduplicación de ingress, estado reclaimable con fencing y
  outbox unique;
  ampliar observabilidad.
- Consumir y persistir las trazas ya disponibles de retrieval/coverage; separar construcción de
  evidencia, llamada del writer y transporte.
- Ejecutar el pipeline síncrono fuera del event loop o migrar sus clientes a async antes de abrir
  hops concurrentes.
- Flag `shadow`: el estado se escribe/valida, pero query, chunks y respuesta siguen byte-invariantes.

Coste de inferencia por query: 0 adicional. Gate: paridad byte a byte + retries/crash en cada
frontera (`LLM`, persistencia y Telegram) + orden concurrente + recuperación tras restart +
aislamiento de chats + lifecycle RGPD/retención/borrado + carga concurrente.

### Fase 1 — multi-turn útil

- Resolver referencias y rewrite sólo cuando el turno no sea standalone.
- Re-ground de facts siempre; nunca usar el texto previo del bot como fuente.
- Eval nueva: follow-ups, pronombres, cambio de producto, correcciones, pregunta no contestable,
  reinicio y dos mensajes concurrentes.

Coste: 0 en consultas standalone; una llamada económica sólo en el slice dependiente. Gate:
retrieval y answer quality vs control contemporáneo, más latencia/coste por ruta.

### Fase 2 — multi-hop bounded

- Planner de acciones estructuradas, máximo 2–3 retrievals y un único writer final.
- Escalado por router/sufficiency; no varios writers por foco.
- Eval orgánico/fresco multi-hop con path completeness y receipts por hop.

Coste: 1–2 retrievals extra y, como máximo inicial, una llamada económica de routing/planning en
el slice complejo. Gate: mejora end-to-end, cero unsupported claims, budget/latency y stop safety.

### Fase 3 — verifier fail-closed

- Primero verifier económico calibrado en español/PCI y ejecutado sólo por riesgo.
- Subir de modelo o añadir segunda verificación únicamente si el delta neto lo paga.

Coste: una llamada económica en el slice de riesgo. Gate separado para unsupported-claim
precision, omission recall, protected facts, conflictos, tasa de clarify/abstain y coste.

### Fase 4 opcional — repair experimental

- Segundo writer pass sólo sobre cohorte fresca y con el contrato de merge/revalidación completo.
- No se habilita por target ni se atribuye como cimiento necesario de multi-hop.

Coste: otra generación en el slice reparable más verificación full-answer; sólo se justifica si la
mejora neta supera regresiones, latencia y coste frente a `clarify/abstain`.

## 5. Alternativas consideradas

- **Más contexto/top-k para todos**: descartado como solución de synthesis; S275 ya muestra que
  5/6 no son gaps puros de vista y “Lost in the Middle” advierte que más contexto puede diluir.
- **Prompt/checklist genérico**: descartado; S206 dio 0 gains y 1 regresión.
- **Question decomposition + múltiples writers**: descartado tal cual; S216 no tenía instrumento
  representativo y S235 produjo regresiones/conflicto. La propuesta usa hops de retrieval y un
  writer final, no generación independiente por foco.
- **Agente abierto/ReAct sin límites**: descartado. Se conserva la idea de intercalar acciones y
  evidencia, pero con state machine, schemas, stop rules y budget explícito.
- **GraphRAG generalizado ahora**: descartado. El corpus es manualístico y la causa actual está
  mayoritariamente después del retrieval; indexar un grafo añade coste/operación sin evidencia de
  que cierre estos misses. Puede reabrirse para preguntas globales cross-manual observadas.
- **Embeddings de transcript completo como memoria**: descartado por ruido, coste, privacidad y
  contaminación del corpus técnico. Event log + snapshots + retrieval de memoria por necesidad.
- **Redis/infra adicional desde el día 1**: descartado. Postgres/Supabase basta para durabilidad,
  locks/versiones e índices al volumen actual; se añade cache/queue externa sólo con señal de p95
  o concurrencia. Jobs diferidos pueden usar una cola durable, no el path interactivo.

## 6. Riesgos y gaps declarados

- El evidence/claim ledger puede repetir el fallo S206 si “query-relevant” se vuelve un checklist
  genérico; el gate fresco y entailment son obligatorios.
- Rewrite conversacional puede introducir entidades o resolver mal pronombres; debe ser
  estructurado, conservar original y aclarar ante ambigüedad.
- Resúmenes pueden perpetuar un error anterior; son derivados versionados, nunca fuente técnica.
- Multi-hop amplifica latencia, coste y errores de ruta; el default sigue single-hop y el router se
  evalúa con controles negativos.
- Telegram puede entregar duplicados o turnos simultáneos; una unique key no basta. Sin
  lease/reclaim, fencing token, orden por conversación, CAS propietario, outbox unique y receipts
  puede duplicarse cómputo o entrega.
- El event log no puede llamarse append-only sin un lifecycle de supresión: el build debe propagar
  borrado/anonimización a derivados, logs, colas, caches, backups y proveedores según la política
  aprobada.
- El actual uso de service key y tablas `public` exige un diseño de privilegios explícito antes de
  almacenar conversaciones. RLS nominal no basta si el backend la bypassa.
- 146/154 y 151/154 no acreditan generalización productiva; hace falta eval multi-turn fresca y
  tráfico orgánico.

## 7. Evidencia externa primaria

- RAGAS: https://aclanthology.org/2024.eacl-demo.16/
- ARES: https://aclanthology.org/2024.naacl-long.20/
- RAGTruth: https://aclanthology.org/2024.acl-long.585/
- CRAG benchmark: https://arxiv.org/abs/2406.04744
- Lost in the Middle: https://aclanthology.org/2024.tacl-1.9/
- IRCoT: https://aclanthology.org/2023.acl-long.557/
- ReAct: https://arxiv.org/abs/2210.03629
- Self-RAG: https://arxiv.org/abs/2310.11511
- SELF-multi-RAG: https://aclanthology.org/2024.findings-emnlp.622/
- mtRAG: https://aclanthology.org/2025.tacl-1.36/
- LongMemEval: https://arxiv.org/abs/2410.10813
- CONQRR: https://aclanthology.org/2022.emnlp-main.679/
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase API security: https://supabase.com/docs/guides/api/securing-your-api
- Supabase connection management: https://supabase.com/docs/guides/database/connection-management
- Supabase Queues: https://supabase.com/docs/guides/queues
