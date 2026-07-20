# S277 C1 P1 — diseño para revisión adversarial

Estado: `OFFLINE_CORE_SAFE_HOLD_RELEASE_BLOCKED_TRANSITIVE_IDENTITY_AND_EXTERNAL_PREREQUISITES`
Fecha: 2026-07-20
Ejecución pagada: **NO AUTORIZADA por este documento**

## 1. Decisión que debe informar

P1 es el gate prerelease de `coverage_c1_v1`. Debe decidir si el cambio C1 puede
pasar a la secuencia de despliegue de `docs/C1_RELEASE_RUNBOOK.md` sin pérdidas
observadas de contenido técnico protegido en las ejecuciones preregistradas y
consiguiendo que el bloque-warning de hp017 llegue completo, correctamente
atribuido y citado.

P1 **no** valida el objetivo de 98 %, no demuestra generalización y no convierte
146/154 en KPI atómico oficial:

- los 13 QIDs son `dev` y hp017 fue target de diseño;
- `evals/s274_banked_funnel_v1.json` mantiene `official_atomic_kpi: null` por los
  77 legacy carries pendientes;
- el resultado es un release gate sobre una cohorte conocida, no una estimación de
  calidad orgánica.

El marcador canónico permanece 146/154 hasta una adjudicación posterior que tenga
autoridad para moverlo.

## 2. Pregunta cero y alcance

Sí cambia una decisión: hoy C1 es NO-GO de release porque los probes existentes no
atraviesan conjuntamente retrieval live, rerank live y síntesis real. No se construye
un benchmark general nuevo ni se reabre el residual de seis synthesis misses.

Dentro de alcance:

1. abrir una ventana live protegida y ejecutar 27 réplicas end-to-end independientes;
2. atravesar en cada réplica retrieval, rerank, C1, síntesis y renderer reales;
3. probar el target hp017 y observar si se pierde alguno de 43 facts base
   protegidos en las réplicas P1;
4. producir recibos completos, reanudables sin reintentos y con techo de 10 USD.

Fuera de alcance:

- desplegar, cambiar Railway o escribir en Supabase;
- juzgar el 98 %, held-out u orgánico;
- implementar multi-turn/multi-hop;
- recuperar una respuesta P1 vacía con una segunda llamada;
- cambiar retrieval, rerank, generator o el core de producción para facilitar el
  instrumento.

## 3. Población y orden congelado

QIDs:

```text
cat001, cat017, cat018, cat019,
hp002, hp003, hp005, hp011, hp012, hp013, hp014, hp017, hp018
```

Todos son fresh single-turn y todos contienen modelo. La preparación de input replica
el camino sano de Telegram: `target_models=extract_product_models(question)`,
`query_for_retrieval=question`, `available_models=None`; no hay carry-forward de sesión.
El prereg sella las preguntas exactas y este resultado esperado, incluida la lista y
su orden:

```text
cat001=[Pearl]         cat017=[INSPIRE]       cat018=[AM-8200]
cat019=[CAD-250]       hp002=[ASD535]         hp003=[CAD-150]
hp005=[ID3000]         hp011=[RP1r]           hp012=[AM-2020, AFP1010]
hp013=[ADW535]         hp014=[ID2000]          hp017=[Pearl]
hp018=[ZXE]
```

La lista ya fue observada offline, sin red, en
`evals/s277_c1_p1_model_extraction_receipt_v1.json`, ligada al catálogo, gold,
`retriever.py`, commit y ausencia del legacy `LEVER2_IDENTITY`. El prereg congela esa
expectativa antes del run; no la presenta como propiedad eterna del catálogo.

El preflight vuelve a ejecutar `extract_product_models` y exige igualdad exacta,
`target_models != []`, `query_for_retrieval == question` y
`available_models is None`. Cualquier diferencia produce `HOLD_INPUT_DRIFT` antes
del primer endpoint pagable y se clasifica `HOLD_EXPECTATION_DRIFT`, no daño del
candidato; una ruta FTS para consulta sin modelo es inesperada y se
bloquea. No se reutiliza `test_bot_vs_gold.py`, que pasa `target_models=None` y trunca
texto para el juez.

Orden exacto de réplicas end-to-end, sin permutación:

```text
hp017:r1, hp017:r2, hp017:r3,
cat001:r1, cat001:r2, cat017:r1, cat017:r2,
cat018:r1, cat018:r2, cat019:r1, cat019:r2,
hp002:r1, hp002:r2, hp003:r1, hp003:r2,
hp005:r1, hp005:r2, hp011:r1, hp011:r2,
hp012:r1, hp012:r2, hp013:r1, hp013:r2,
hp014:r1, hp014:r2, hp018:r1, hp018:r2
```

Con `HYDE_ENABLED=false` y el reranker LLM sellados, cada réplica hace normalmente
un embedding Voyage, un rerank Sonnet y una síntesis Sonnet: **27 generaciones y
aproximadamente 81 llamadas pagables a modelos**. Los RPC/GET PostgREST se cuentan
separadamente como lecturas. El boundary bloquea cualquier operación o llamada de
modelo no preregistrada; “27 llamadas” sin el desglose sería contabilidad falsa.

## 4. Identidad del release candidato

El proceso no lee flags de un `.env` implícito. Un artefacto seguro
`s277_c1_p1_release_config_v1.json` debe fijar, sin secretos:

- `tested_commit_sha` y `tested_tree_sha` de un worktree detached creado desde ese
  commit, con status vacío y sin ficheros untracked; el worker nunca importa desde el
  checkout de desarrollo;
- versión del bot;
- modelo/temperatura/max tokens;
- retrieval/rerank K y backend;
- todos los switches capaces de alterar input, retrieval, contexto, generator,
  postcondición o renderer;
- hashes del catálogo/configuración y del manifest de implementación.
- versión exacta de Python y de los SDK Anthropic/Voyage, más hash del lock efectivo.

La fuente es un snapshot read-only del Railway **vivo actual**, no un estado futuro
imaginado. El artefacto seguro sella `railway_live_snapshot_sha256` y un
`planned_bootstrap_patch` declarativo exacto que elimina las cuatro legacy y fija
profile `off`. Una función pura aplica ese patch offline y deriva dos estados; P1 corre
contra el target derivado sin modificar Railway:

- `bootstrap_profile=off`, usado para desplegar y comprobar arranque sano;
- `p1_target_profile=coverage_c1_v1`, usado por P1 y tras activar;
- `common_config_sha256`, calculado sobre el env raw allowlisted tras excluir únicamente
  `COVERAGE_RELEASE_PROFILE` y exigir ausentes las cuatro variables legacy;
- `bootstrap_effective_config_sha256` y `target_effective_config_sha256`, porque los
  flags efectivos resueltos son distintos por diseño.

Antes del merge se retiran las cuatro variables legacy poseídas por el perfil. La
única transición de activación autorizada es
`COVERAGE_RELEASE_PROFILE: off -> coverage_c1_v1`; cualquier otro drift caduca P1.
El target exige `MUST_PRESERVE_CONTRACT=on`, `HYDE_ENABLED=false` y sólo la lane
structural entre las lanes de coverage.

`VISUAL_ASSETS_REGISTRY` es ortogonal al perfil C1. El contrato acepta únicamente
`on|off` y conserva exactamente el valor del snapshot vivo en bootstrap y target;
la foto documentada actual es `on`. Ausencia o drift produce HOLD. P1 no puede
apagarlo y reactivarlo como parte del mismo ensayo.

El env aislado de `scripts/s277_c1_release_gate.py` se usa para pruebas offline del
instrumento, pero **no sustituye** el recibo de configuración de despliegue. Si ambos
divergen, P1 queda `HOLD_CONFIG_DRIFT`; no se elige silenciosamente el más cómodo.

El merge normal de GitHub puede cambiar el commit sin cambiar el árbol. El release
acepta `deployed_commit_sha != tested_commit_sha` sólo mediante un receipt de merge que
demuestre que el commit probado es ancestro/padre, `deployed_tree_sha == tested_tree_sha`
y el manifest de implementación es idéntico. Squash/rebase que pierda esa lineage, un
árbol distinto o cualquier código adicional caduca P1. `bot_version` registra el SHA
desplegado y no se trata como input funcional del modelo.

## 5. Ventana live protegida y separación de deberes

Las 27 réplicas usan PostgREST y el grafo HNSW productivos. No comparten una transacción
ni se presentan como snapshot global ACID: cada réplica es una observación end-to-end
independiente. Para evitar que una ingesta contamine la cohorte durante P1, un proceso de
operador separado mantiene el fence; el runner pagado nunca recibe esa credencial.

El permit de ejecución nombra al `fence_owner`. Desde una conexión PostgreSQL directa,
no desde el pooler transaccional, el protocolo exacto es `BEGIN -> SHARE locks en orden
canónico -> fingerprint inicial -> 27 réplicas -> fingerprint final todavía bajo locks
-> COMMIT`. Estos locks
permiten SELECT/PostgREST y bloquean DML y DDL de tabla hasta cerrar P1. El receipt sella
backend PID, txid, relaciones/modos, timestamps, deadline y heartbeats; un watcher
read-only comprueba los locks antes y después de cada réplica. Pérdida de conexión, lock o heartbeat
produce `HOLD_CORPUS_FENCE_LOST` y no se reanuda el gasto. Como adquirir `SHARE` requiere
privilegios incompatibles con la identidad mínima del runner, su provisioning y uso son
una acción de operador autorizada aparte.

La lista de relaciones se deriva del fingerprint y excluye `query_logs`, que no afecta
retrieval. Los locks se adquieren `NOWAIT`, con deadline duro preregistrado máximo de
45 minutos, heartbeats por debajo de `idle_in_transaction_session_timeout` y cleanup
por cierre de conexión. El watcher inspecciona `pg_locks`/waiters: ante autovacuum,
DDL o cualquier waiter incompatible, libera el fence antes de otra llamada pagada y
emite HOLD. La ventana declara ausencia de ingesta/DDL/tráfico técnico y termina con
post-check de mantenimiento; no se mantiene el lock indefinidamente tras crash.

El fence de tabla deberá acompañarse de una ventana operativa que pause cambios de RPC,
ACL, índices, PostgREST y configuración. Los helpers implementados hoy sólo sellan la
**superficie declarada** de nombres/relaciones y locks; no observan definiciones RPC,
ACL, overloads, índices ni configuración live. Por ello no se presentan como manifest
físico. Los cuatro CLI productivos de fence/ejecución/finalización devuelven por máquina
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED` antes de leer receipts o credenciales.

Retirar ese HOLD exigirá un cambio separado: bodies pre/watch/post con firma/resultado,
`pg_get_functiondef` y hash, volatility, `prosecdef`, owner/ACL y cardinalidad de overload
por RPC; `pg_get_indexdef`, valid/ready, AM/opclass/dimensión/relación por índice; y
snapshots de PostgREST/ACL/config. Sus hashes deberán recomputarse localmente y compararse
con un contrato esperado canónico sellado en prereg, release-config y genesis. Una
mutación revertida entre controles seguirá siendo riesgo residual explícito del permit,
no aislamiento inexistente.

Para identidad de corpus se reutiliza `public.corpus_fingerprint_v1()` y el contrato
aplicado en `evals/s107_m014_corpus_fingerprint_apply_v1.json`; no se diseña otro Merkle.
La copia auditada `evals/s107_corpus_fingerprint_v1_function_audit.sql` tiene SHA-256 LF
`285dd74a1463bb71a21ab9bfb5ea4053789d606ede9b90b640c14008c676dbda`; el
`pg_get_functiondef` live debe conservar el hash
`1f280e0852158b63501aad2843a7e946ab9fac5a4c64a17851d6d63ed0e8ebca` del recibo S107.
Antes de P1, `fingerprint-calibrate` **verifica un receipt del operador** de una
ejecución sin llamadas a modelos; no ejecuta la función privilegiada desde el runner.
Sella function SHA, elapsed y carga, y exige un ceiling preregistrado. Sólo el operador
ejecuta esa función `SECURITY DEFINER` dos veces dentro de la transacción cercada; el
runner no usa `service_role`. Drift de fingerprint o superar el ceiling produce HOLD. Si este
camino no es viable, se rediseña o usa un clon físico hosted autorizado: no se degrada
silenciosamente a row counts.

El runner usa un JWT PostgREST `p1_readonly` sin DML/DDL ni `BYPASSRLS`, limitado a
lectura y a un `rpc_allowlist` generado desde la configuración sellada y un trace
offline del camino real. La ruta base incluye vector/FTS (`match_chunks_v2` y
`search_chunks_text_v2`); enunciados e HyQ añaden sus RPC sólo si sus lanes están ON.
Todas las llamadas observadas deben pertenecer a la allowlist exacta y cada lane ON
debe ejercitarse en un control; no se hardcodea una tripleta antes de materializar el
release-config. El boundary permite
GET y POST `/rpc/…` allowlisted porque PostgREST invoca RPC de lectura mediante POST,
pero bloquea POST a tablas, cualquier otra RPC y PATCH/PUT/DELETE antes de red. Cada
firma futura deberá tener hash revisado, volatility de lectura, `prosecdef=false`, ACL
exacta y ausencia de overload ambiguo. Esa verificación **no está materializada en
S277** y es precisamente la stop-line anterior. El método HTTP por sí solo no demuestra
read-only.

Tras desplegar con `bootstrap_profile=off`, el runbook verifica árbol/lineage, runtime,
`common_config_sha256`, fingerprint y manifest RPC/físico. El resultado sella IDs de
modelo solicitados/reportados y metadata disponible, `p1_completed_at` y
`p1_expires_at = p1_completed_at + 6h`. No afirma identidad inmutable de la
infraestructura Anthropic/Voyage: cambio/deprecación de ID, runtime, metadata o vencer
el TTL caduca P1 completo. Si todo coincide y sigue dentro del TTL, no se repiten las
27 réplicas. Después cambia sólo el profile; ya con
`coverage_c1_v1`, la configuración completa debe coincidir con `p1_target_profile`.
Cualquier otro drift caduca P1.

## 6. Fase E — 27 réplicas end-to-end

La implementación versionada en este cambio es el orquestador y contrato
**offline**, no el adapter productivo. El adapter posterior, revisado por separado,
deberá hacer que cada celda cruce `execute_rag_turn` una sola vez con
`retrieve_chunks`, `rerank(..., strict=True)`, observer, structural fetch,
selector/attestation, coverage, generator, must-preserve y renderer reales. Mientras
no se materialice y revise el manifiesto live físico, `run` falla primero con
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`. Una vez retirado ese bloqueo mediante
una implementación revisada, la ausencia de paridad y receipts del adapter mantiene
el siguiente cierre `HOLD_PRODUCTION_ADAPTER_NOT_INSTALLED`; P1 no es ejecutable en
ninguno de los dos estados. No hay replay en
un resultado autoritativo. Los replays deterministas offline pueden ayudar a
clasificar un fallo después, pero no rescatan la celda, no forman PASS y nunca
invocan una nueva síntesis.

Los adapters usados por los tests son sintéticos: demuestran las transiciones,
bindings y rechazos del orquestador, pero sus hashes coherentes no prueban que el pool,
prefijo, fetch estructural, contexto servido o rama visual hayan sido derivados por el
pipeline productivo. Tampoco prueban los bytes entregados al SDK ni la entrega final a
Telegram. Esas garantías nacen únicamente de las futuras pruebas de paridad/input-graph
y de receipts físicos del adapter productivo; hasta entonces son stop-lines, no
capacidades implementadas.

Por réplica se persisten completos y ordenados:

- pregunta, input preparado y modelos extraídos;
- retrieval pool y recibo físico del embedding;
- prefijo rerankeado y recibo físico del rerank;
- input/output raw del fetch structural;
- contexto servido y coverage/must-preserve traces;
- envelope de generación interceptado y sellado justo antes de enviarlo;
- respuesta y render de Telegram.

Fallback del reranker, contexto vacío, prefijo mutado, coverage `error`, identidad
duplicada, modelo/provider inesperado o ausencia del append esperado producen NO-GO.
En hp017, cada una de r1/r2/r3 debe alcanzar y receiptear el target de forma
independiente; no puede reutilizar el rerank favorable de otra réplica.

Cada respuesta persiste antes de validarse:

- payload físico completo del proveedor;
- response/request ID disponibles;
- modelo solicitado y reportado;
- stop reason y todos los campos de usage;
- respuesta completa, longitud y SHA-256;
- partes exactas del renderer Telegram;
- context/envelope hashes y coverage/must-preserve traces.

Respuesta vacía/invisible, `max_tokens`, modelo distinto, usage ausente, envelope
drift, postcondición error o excepción consumen la celda y producen NO-GO. No hay
recovery: una segunda llamada sería una réplica 28 encubierta.

## 7. Boundary de proveedor, WAL y reanudación

El boundary offline, el WAL y sus mutation tests están implementados. No se modifica
core de producción. El adapter futuro deberá correr en un subprocess limpio e
interceptar Anthropic y Voyage mediante proxies runner-only con estas condiciones:

- Anthropic siempre se instancia con `max_retries=0`;
- Voyage conserva intacta la cadena de producción
  `embed_query -> embed -> _embed_voyage`: se inyecta un
  `voyageai.Client(..., max_retries=0)` auditado y se envuelve sólo su transporte
  para reservar/persistir la llamada sin modificar argumentos ni respuesta;
- un tripwire runner-only sobre el backoff aborta antes de una segunda petición si
  el bucle de cuatro intentos de `_embed_voyage` intenta reintentar, y un contador
  prohíbe más de una delegación de red;
- sólo se permiten las operaciones/modelos preregistrados;
- la respuesta física se fsynca antes de parsear o puntuar.

Los tests de paridad del adapter futuro deberán exigir el mismo texto normalizado/truncado, orden, `model`,
`input_type`, dimensión, cardinalidad y resultado que el adaptador de producción, y
exactamente una petición tanto en éxito como en fallo. Se sellan los hashes de
`_embed_voyage`/`_PROVIDERS`. El runtime actual no puede asumirse compatible sólo
porque `requirements.txt` usa un mínimo abierto: la versión efectiva del SDK debe
coincidir exactamente con el release-config o P1 queda en HOLD.

Cada llamada tiene `call_key` determinista y journal JSONL append-only con cadena de
hashes:

```text
RESERVED_FSYNCED -> COMPLETED
                 -> FAILED_PRE_SEND_NO_RETRY
                 -> UNKNOWN_BILLED_POST_SEND
```

La reserva, request SHA, coste máximo y acumulado previo se escriben y `fsync` **antes**
de red. Al reabrir:

- `COMPLETED`: sólo se reanuda postproceso local desde el receipt;
- `FAILED_PRE_SEND_NO_RETRY`: sólo para un fallo local demostrado antes de delegar
  al transporte; no se llama de nuevo;
- reserva sin terminal al reabrir: se convierte en `UNKNOWN_BILLED_POST_SEND`
  conservador, conserva su coste reservado, bloquea el run y nunca se reemite.

La topología durable tampoco es inyectable. El journal es exactamente
`artifact_root/calls.jsonl`, sus sidecars tienen nombres canónicos y el ledger de
autorizaciones se deriva como
`artifact_root.parent/.s277_c1_p1_authorization_claims_v1`. El genesis sella el layout
y los hashes de sus rutas. Un lease `O_EXCL` canónico, indexado por artifact root, se
adquiere antes de claim/bind y su ownership se revalida antes de cada send; un segundo
runner no toca WAL ni result. Un claim global nuevo sólo adopta un artifact root sin
estado previo; un claim existente exige que WAL, directorio de claims y ambos genesis
ya existieran al abrir el proceso y coincidan. Borrar/reinicializar esos artefactos no
crea otro presupuesto: produce `HOLD_AUTHORIZATION_RESUME_STATE` antes de cualquier
send. Una reanudación canónica conserva los receipts y no delega de nuevo.

Una reapertura completa no confía sólo en hashes autoconsistentes. El genesis incorpora
un snapshot canónico de modelos, inputs, presupuesto de 81 llamadas e implementation
hashes. Resume, `score` y `finalize` reabren 81 responses + 81 fence watches, vuelven a
ejecutar el validador semántico sobre las 27 réplicas, reconstruyen los 81 envelopes y
revalidan modelo/usage/coste. El WAL debe ser exactamente 162 eventos alternos
reserve/completed en el orden preregistrado; max-cost, acumulado previo, coste observado
y resumen de presupuesto se recomputan y deben coincidir.

El preflight hace deep-copy JSON-native y sella config, prereg, fingerprint, fence,
runtime, budget e inputs. `run()` reconstruye y compara el bundle con una inspección
fresca; commit/tree/detached/clean se vuelven a validar justo antes del lease y antes
de cada una de las 81 delegaciones. Tras `prepare`, el request debe seguir igual al
hash reservado y el lease debe seguir siendo propiedad del runner. Cualquier drift
pre-send termina la celda sin delegar.

El boundary marca el punto de envío justo antes de delegar al SDK. Desde ese instante,
timeout, reset, cancelación o cualquier excepción se persiste como
`UNKNOWN_BILLED_POST_SEND`, aunque no haya response/usage; conserva el coste máximo
reservado y nunca se reclasifica como fallo gratuito.

Toda parada genera un result sellado `NO_GO_PARTIAL`; nunca deja la decisión escondida
en una excepción.

El runner actual valida el input preregistrado exacto, los envelopes y su hash WAL,
el payload canónico de intención persistido, `stop_reason`/modelo/usage contra la
respuesta sellada del adapter, tres etapas de postproceso, respuesta, hash y render.
La implementación del adapter deberá
añadir y probar el binding de los bytes reales enviados en embedding, rerank y
síntesis —incluidos pool, contexto servido y prompts— contra esos envelopes; los
hashes por sí solos no sustituyen esa revisión de paridad.

## 8. Coste

Techo conjunto de E: **10,00 USD a list price**, sin descontar free tiers.

Tarifas a pinnear con fecha y URL oficial en el prereg:

- Claude Sonnet 4.6: 3 USD/MTok input y 15 USD/MTok output;
- Voyage `voyage-4-large`: 0,12 USD/MTok;
- si el backend fuese Voyage `rerank-2.5`: 0,05 USD/MTok procesado.

No hay prompt cache en el candidato. Si aparece cache usage o cualquier modificador no
preregistrado, falla por drift. Para cada llamada:

```text
actual_observado + reservas_unknown + worst_case_restante_prereg <= 10.00
```

Antes de la primera llamada, un bound estático conservador de las 27 secuencias
embedding+rerank+síntesis debe caber. Tras construir cada input real se sustituye su
bound por el envelope exacto, conteo de tokens cuando el proveedor lo ofrece y
`max_tokens`, nunca por una media histórica. Si todo el resto preregistrado ya no cabe,
la siguiente petición no sale. El resultado reporta list-price derivado de usage, no
pretende ser la factura bancaria.

La revisión adversarial Sol/Fable tiene presupuesto separado y no consume el techo P1.
El canary post-activación añade tres recorridos end-to-end —normalmente 9 llamadas a
modelos— y requiere autorización/presupuesto separados; no se oculta dentro del PASS P1.

## 9. Fact packet protegido

Precedencia de autoridad:

1. marcas explícitas de Alberto S270 / DEC-125 / DEC-128;
2. gold verificado con provenance y citas;
3. S113 sólo para identificar qué facts estaban OK;
4. S201/S202 sólo como evidencia congelada, nunca como autoridad gold;
5. S272 para la conversión banked viva de hp002;
6. S273 sólo para el guard de release contemporáneo (qué fact no debe perderse),
   nunca para mover el KPI;
7. S274 para el target candidato, nunca para auto-pasarlo.

El packet contiene **43 facts base protegidos + 1 target C1 compuesto**:

Los 42 facts históricos no se indexan contra `atomic_facts` crudo. Se reconstruyen
con el contrato de `s118_build_atomic_benchmark._historical_core_facts`: por QID se
filtra primero `tipo=core && estado=presente`, después `#index` apunta a esa lista y
el suffix del `fact_key` debe coincidir con `fact.valor`. Cualquier desajuste de
índice, valor o hash es `HOLD_FACT_AUTHORITY`, no una selección manual silenciosa.
Después se aplican tres transformaciones versionadas y explícitas, sin alterar el KPI:

1. `hp017#1` histórico se excluye porque sus dos componentes contemporáneos
   `obl_b2043cd4379b`/`obl_7aa723717412` son residuales S274; en su lugar se protege como guard
   de release `hp017#2`, watch-fact cuya pérdida observada (2/3 OFF frente a 1/3 ON)
   disparó el STOP S273. Esto es una política conservadora de release, no una
   adjudicación gold ni una afirmación de estabilidad.
2. `hp017#3` se reemplaza por el disclosure DEC-128, sin doble conteo.
3. se añade la conversión hp002 banked en S272.

El resultado debe reconstruirse a exactamente 43 filas y la transformación se publica
como diff machine-readable; cualquier fila implícita o count distinto queda en HOLD.

| QID | Base | Contrato protegido resumido |
|---|---:|---|
| cat001 | 5 | 159+159/99+99; 0,75 A; límite mixto 40; autoconfig; edición 255/8192 |
| cat017 | 4 | HOP-433-100 pinout; capacidades; Auto Config; CLSS/site/.bin |
| cat018 | 1 | semántica CBE |
| cat019 | 4 | crear/coincidencias; EVENTO/ACCIÓN; ENTIDAD/CONDICIÓN; salidas |
| hp002 | 4 | fallo/ventana; bajo-obstrucción; 300 s; aislamiento previo banked |
| hp003 | 4 | 2x12 V serie; puente; rojo/negro; red antes que baterías |
| hp005 | 4 | matriz alarma; COINCIDENCIA 2; zona/subzona; salidas permitidas |
| hp011 | 1 | Rearme inhibido tras extinción + opciones; canónico `r.I`/`r.i`, alias visual `r.1` no puntuable solo; `--` exige `t.A`, nunca `t.Fi` |
| hp012 | 4 | AM2020 10; 99+99; AFP1010 ES 2/396; US 4/792 + conflicto |
| hp013 | 0 | safety guard: no inventar procedimiento ni garantizar conservación |
| hp014 | 4 | máximo/ID2000; continuidad; corto 2-4; tierra panel/+35 ohm |
| hp017 | 3 | retardo mediante C&E; Editar Configuración + Regla 1/precondición; disclosure DEC-128 |
| hp018 | 5 | 2/4 salidas; 6K8; diodo; A-D; 1 A |
| hp017 C1 | +1 | ambas cláusulas warning y sus citas al target dinámico |

Exclusiones/holds no se convierten en falsos requisitos: cat001 32/25/20;
cat017 licencia/lazo; pasos aún-miss cat018; hp002 V01/V02 y demoted; siblings hp011;
hp013 facts no-OK; número de menú plano hp017. `obl_b2043cd4379b` (instrucción de
entrada) y `obl_7aa723717412` (salida) siguen entre los seis synthesis misses y no se
disfrazan de baseline: pueden reportarse como observación informativa, pero no gatean
C1. El tercer baseline hp017 es el átomo contemporáneo completo
`hp017#2:Editar Configuracion`: ruta Editar Configuración -> Causa y Efecto y, si se
hace programación específica, borrar la Regla 1 por defecto que activa todas las
salidas ante cualquier entrada de alarma. `obl_e265a4c97a31`,
`obl_e8491bc1c321` y la ruta F8 son cláusulas/evidencia auxiliares, no sustitutos del
fact. El disclosure hp017
aprobado **reemplaza**, no duplica, `hp017#3:seis tipos de retardo` y aplica exactamente
DEC-128 opción 1: exige seis/6 junto a tipos de retardo, todas las
etiquetas no-basura de al menos uno de los lados servidos y un marcador explícito de
discrepancia. No exige el literal “siete”, porque ese cardinal sólo se obtuvo por
inspección visual y no es una surface servida autorizada. Esta excepción no ignora el
ruler: fue adjudicada expresamente por Alberto en DEC-128 opción 1; el “7” visual queda
registrado como gap de ingesta, no como requisito que el bot deba inventar. El fact
hp011 se revisa ante todo por función: Rearme inhibido tras extinción y opciones
`--`/`00`/default/`01-30`; dentro de `--`, `t.A` es cláusula obligatoria y `t.Fi` está
prohibido. Para auto-PASS se exige la afirmación canónica exacta completa; si el
identificador se omite pero función y opciones están completas queda REVIEW, no FAIL. Si se
imprime, DEC-095/DEC-125 soportan `r.I`/`r.i` como forms canónicas. `r.1` queda
registrado como alias OCR/display por
`evals/s269_goldreview_packet_v1_ADJUDICADO.md` y
`evals/s270_gold_adjudication_v1.yaml`, pero no es evidencia positiva independiente:
si aparece sin forma canónica ni disclosure de ambigüedad produce REVIEW.

Las citas stale de hp018 no se consumen: sus cinco facts se reanclan exclusivamente a
`MIE-MI-530rv001` en `evals/s113_full_contexts_freeze_v1.json` (SHA-256 LF
`556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498`), chunks
`90d51dac-bd0b-4051-b414-ced0fe6e33bb` (p. 20: 2/4 salidas, 1 A y 6K8) y
`72fc4c53-f507-4e67-9192-ebc68b94be78` (p. 21: diodo y terminales A-D), usando la
provenance ya verificada del gold. S201/S202 sólo aportan evidencia congelada; sus
mappings no tienen autoridad para cambiar el gold.

Los hashes de autoridad usan la convención del repo
`sha256(bytes.replace(b"\r\n", b"\n"))`; cuando importe la integridad física se
guarda además el hash raw, con ambos campos inequívocamente nombrados.

Cada fact declara statement, cláusulas, source refs, política de cita, surface forms,
claims prohibidos, autoridad y `kpi_weight`. Declara además `binding_level`:
`gold_verified_page` o `accepted_exact_span`. Manual/página y statement hash son
obligatorios para ambos; `source_start/end/span_sha256` sólo para
`accepted_exact_span`. No se fabrican spans para los legacy: S201/S202 no cerraron esa
autoridad. El target hp017 sí exige binding exacto y los facts con evidence exacta ya
aceptada pueden usarlo. Cuando el gold contiene una quote fact-specific, el contrato
conserva texto normalizado + hash y el scorer exige que aparezca en el contenido real
del fragmento; si existe `content_sha256`, lo recalcula sobre `chunk.content`. Una
referencia basada sólo en fichero/página nunca acredita PASS. Además, el auto-PASS
genérico exige que la unidad local citada completa coincida con el statement canónico
normalizado: las surface forms sólo localizan candidatos. Negación, relación distinta o
paráfrasis quedan REVIEW aunque contengan todos los tokens. Prosa no resoluble de forma determinista queda `REVIEW`;
`REVIEW` bloquea GO y pasa a packet humano ciego.

Las guardas que no son facts viven en `question_guards[]`, no implícitas en prosa.
Cada guarda declara `guard_id`, QID, cláusulas requeridas/prohibidas, surface forms,
autoridad, source refs, algoritmo y política PASS/FAIL/REVIEW. Para hp013 el contrato
machine-readable exige reconocer que el manual no documenta un procedimiento autónomo
para cambiar sólo la batería; no garantizar conservación de configuración; y, si
menciona EEPROM/no-volatilidad, expresarlo como fundamento de una expectativa matizada
y no como procedimiento certificado. Recomendar fabricante/servicio autorizado es una
mitigación permitida por el gold, no un requisito cuya omisión se llame regresión. Incluso
una formulación que supera el precheck determinista queda REVIEW —nunca auto-PASS— y
bloquea GO hasta adjudicación ciega; las violaciones explícitas siguen siendo FAIL. Por tanto
`protected_facts=[]` no deja hp013 sin scorer. Sus guardas se etiquetan
`safety_guard_only`, `kpi_weight=0` y `not_a_regression_fact=true`.

## 10. Scorer hp017

El scorer especial es **aditivo** a los tres facts base hp017.

1. Resuelve el target por ID sellado dentro del contexto servido; exige exactamente uno.
2. Revalida `has_exact_mandatory_callout_receipt` y deriva los dos spans desde las cards,
   no desde literales hardcodeados.
3. Deriva dinámicamente `F<n>` de la posición actual; no asume F12.
4. Trata `obl_16637b935bd4 + obl_0d6a30948dfd` como una obligación KPI compuesta
   por decisión de Alberto, pero exige sus dos cláusulas por separado. Para cada warning
   exige texto verbatim normalizado en una unidad local seguido por un grupo de citas
   que contenga `target_fragment`; una única cita compartida sólo vale si el grupo local
   abarca inequívocamente ambas cláusulas. Una cita adicional pasa automáticamente sólo
   si su fragmento contiene el mismo exact span validado y la misma identidad de
   producto/revisión; evidencia adicional válida pero no decidible queda REVIEW, y una
   cita inválida o no acreditada falla.
5. Negación/inversión, cita remota, fragmento incorrecto, marcador inválido o segundo
   fragmento no acreditado => FAIL.
6. Paráfrasis plausible => REVIEW, nunca auto-PASS.
7. Card/receipt/target con drift => `INSTRUMENT_ERROR`, no “fallo del bot”.

El conflicto hp017 7-vs-8 de menú (`conf_26f63590494f`) es hard-negative: emitir un
único número de menú sin disclosure/atribución falla, aunque los warnings pasen. Es
preexistente (3/3 en A-C1 histórico y también visible en la respuesta viva), por lo
que no se etiqueta falsamente como regresión causada por C1, pero sí bloquea un release
de seguridad si reaparece. Un preflight local de 0 USD puntúa primero las respuestas
almacenadas: si confirma el patrón, emite `HOLD_PREPAID_KNOWN_CONFLICT_RISK`, no un
NO-GO del runtime candidato que aún no se ha medido. E sólo puede empezar con un
permit posterior que cite expresamente ese prior y autorice medirlo; arreglar primero
es la ruta recomendada. En las respuestas candidatas, para pasar, el bot debe omitir el
número o revelar/atribuir la discrepancia entre fuentes/revisiones.

GO exige 3/3 con target appended/receipted, ambos warnings, citas locales exactas, los
tres facts base hp017, respuesta técnica no reducida a sólo-warning, cero citas inválidas,
cero conflicto y `end_turn`.

Para los otros QIDs, cada fact base debe estar presente en las dos ejecuciones
observadas (2/2). No hay mayoría. Esto no estima una tasa global de regresión ni
demuestra que el generador estocástico nunca pierda un fact. hp013 puede tener cero
facts y aun exige todas sus guardas de seguridad/identidad.

El validador recorre **todas** las marcas de cita de la respuesta y exige sintaxis,
rango e identidad válidos contra el contexto servido. El entailment factual automático
se limita al packet protegido, guardas, conflictos registrados y target hp017; la prosa
técnica adicional se conserva para auditoría pero P1 no afirma haber inventariado todas
sus proposiciones. Por tanto el resultado no significa “toda afirmación de las 27
respuestas fue probada”, sino ausencia de daño detectado dentro del contrato preregistrado.

## 11. Estados y decisión

`GO` sólo si:

- cualquier `HOLD_PREPAID_*` fue resuelto antes de ejecutar o consta en un permit de
  medición explícito; el HOLD por sí solo nunca adjudica al candidato;
- identidad de código/config y receipts por-réplica exacta;
- fence/fingerprint/manifest operativos vigentes;
- 27/27 generaciones completas dentro del techo;
- todos los 43 facts base presentes en cada réplica aplicable;
- hp017 target 3/3 bajo el scorer estricto;
- cero contradicciones o atribuciones inválidas detectadas respecto del packet,
  guardas, conflictos y target; cero cita sintácticamente inválida/fuera de rango en
  toda la respuesta; cero truncamiento o error;
- cada fila termina en `PASS` o `ADJUDICATED_PASS`, sin `REVIEW` sin resolver,
  llamadas huérfanas ni receipts incompletos.

`score` puede producir REVIEW. El scorer liga contrato/prereg/run/manifest y exactamente
los 27 receipts; `finalize` vuelve a puntuar de forma autoritativa y rechaza un score
aportado por el caller si no es canónicamente idéntico. Sólo puede transformar una fila REVIEW en
`ADJUDICATED_PASS` o `ADJUDICATED_FAIL` mediante decisión humana ciega ligada por hash
a respuesta, contexto, fact/source y versión del scorer. Nunca puede sobreescribir
FAIL ni `INSTRUMENT_ERROR`. Si la adjudicación cambia contrato, autoridad o algoritmo,
invalida el run y exige prereg/repetición; no se “adjudica” el instrumento después de
ver el resultado.

El claim positivo machine-readable es
`NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS`; nunca `ZERO_REGRESSION`.

Cualquier incumplimiento produce `NO_GO` o `HOLD` explícito. Una pérdida dura permite
parada temprana, pero siempre materializa `NO_GO_PARTIAL` y el coste consumido.

## 12. CLI y artefactos

CLI materializada (los subcomandos que consumen artefactos exigen todos sus argumentos):

```powershell
python scripts/s277_c1_p1.py plan
python scripts/s277_c1_p1.py score-stored-controls
python scripts/s277_c1_p1.py preflight --help
python scripts/s277_c1_p1.py fingerprint-calibrate --help
python scripts/s277_c1_p1.py fence-open-verify --help
python scripts/s277_c1_p1.py fence-close-verify --help
python scripts/s277_c1_p1.py score --help
python scripts/s277_c1_p1.py finalize --help
python scripts/s277_c1_p1.py run --help
```

`plan` confirma 27 réplicas/81 llamadas preregistradas y cero llamadas pagadas.
`score-stored-controls` confirma el conflicto 3/3 y devuelve HOLD sin medir el
candidato. `fence-open-verify`, `fence-close-verify`, `run` y `finalize` no importan credenciales ni
pueden alcanzar red en esta versión: su primera operación termina en
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`. Tras materializar y revisar ese contrato
seguirá siendo necesaria otra PR para el adapter productivo.

Verificación local reproducida tras el build: 179 tests P1 verdes y `py_compile`
verde. Los artefactos regenerados byte-idénticos tienen SHA-256 raw:

```text
fact contract  cf61c61dfc9e7d1471d28d5db8833a8097eccdd60c1a87a43445fa4b1e17c38d
prereg         100f29de15168a432945270f0dfcc351b52ccf4d8801aec7271077f657dc936e
schema         1e9bea474620579dd703c038299293be2f8894d96b9a8708cfd9a340721bd700
```

Artefactos:

- prereg y release-config safe;
- fact contract packet;
- fingerprint y contrato declarado de superficie/locks; manifest DB/RPC/index/config
  live pendiente y bloqueado por máquina;
- pool/prefix/context/envelope seal por réplica;
- WAL + receipts físicos por llamada;
- generations completas;
- checks de aborto temprano marcados `NON_AUTHORITATIVE_EARLY_ABORT_ONLY` y,
  por separado, score canónico offline autoritativo;
- review packet humano;
- adjudicación y result final sellado.

Los artefactos nunca incluyen secretos. Las respuestas completas y contextos técnicos sí se
conservan local/versionados según el contrato; `query_logs` no es autoridad porque
`src/logging_db.py` trunca la respuesta persistida a 4096 caracteres.

## 13. Alternativas consideradas

- **13 freezes + 27 síntesis replay:** útil como diagnóstico causal, pero descartado
  como autoridad de release porque ninguna respuesta nace de una réplica end-to-end y
  hp017 podría hacer 3/3 sobre un único rerank favorable. Ahorra sólo unas 28 llamadas
  baratas frente al camino compuesto.
- **Sólo frozen S113:** descartado; no prueba retrieval/rerank live del commit candidato.
- **Supabase Branch como clon de producción:** descartado para este gate: la documentación
  vigente indica que las branches nuevas son data-less. “Restore to a New Project” desde
  backup/PITR sí puede clonar datos, pero crea infraestructura hosted con coste y estado
  externo; queda como alternativa futura con autorización, no como efecto lateral de P1.
- **Dump lógico + restore local:** descartado para este gate: no preserva el grafo HNSW,
  exige Postgres/pgvector/PostgREST exactos que este host no tiene y convierte P1 en un
  workstream de infraestructura. Sólo sería aceptable con paridad top-k demostrada.
- **`test_bot_vs_gold.py`:** descartado; input no Telegram, juez truncado y sin WAL/coste.
- **Single pass o mayoría:** descartado; aporta menos evidencia observacional y
  permite pérdidas conocidas. Ni 1/1 ni 2/2 demuestran una tasa global de regresión
  cero.
- **Recovery automático de vacíos:** descartado; oculta una llamada extra y sesga el gate.
- **Refactor de ProviderBoundary en producción ahora:** valioso para multi-turn futuro, pero
  amplía C1 e invalida recibos. P1 usa proxies aislados; el refactor tendrá release propio.
- **Juez LLM como autoridad final:** descartado; determinismo donde es posible y lectura
  humana sólo para `REVIEW`, sin dejar que un juez reescriba el gold.

## 14. Gaps y stop-lines declarados

- El release-config seguro de Railway debe materializarse y sellarse antes de E.
- El control almacenado hp017 tiene prior alto de conflicto; se puntúa gratis como
  `HOLD_PREPAID_KNOWN_CONFLICT_RISK`. No adjudica el runtime no medido; arreglar primero
  es lo recomendado y medir pese al prior exige un permit explícito posterior.
- Deben provisionarse fuera de este runner el JWT `p1_readonly` y el proceso de fence
  separado; P1 no usa `service_role` ni crea roles/grants como efecto lateral.
- Debe materializarse y revisarse el manifest live de RPC signatures/ACL/overloads,
  índices y PostgREST/config. Hasta entonces los cuatro CLI operativos devuelven
  `HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`; los hashes de superficie sintéticos
  no son attestation física.
- La cohorte es conocida/dev; un PASS no autoriza claims de 98 % ni robustez orgánica.
- E prueba sólo los 13 afectados según el census congelado, no todas las preguntas
  futuras.
- hp011 puntúa función y opciones; `r.I`/`r.i` son canónicas y `r.1` es un alias
  OCR/display que no pasa por sí solo. Dentro de `--`, `t.A` es obligatorio y `t.Fi`
  está prohibido.
- La ejecución pagada requiere runner/scorer/packet commiteados, suite offline verde,
  revisión Sol+Fable adjudicada y autorización explícita de gasto posterior.
- El adapter productivo y sus pruebas de paridad/input-graph no existen en este cambio;
  deben ligar los bytes físicos enviados a cada etapa y no sólo aceptar hashes del
  orquestador. Su ausencia es un bloqueo intencional, no una capacidad implementada.
- El lease filesystem es deliberadamente **single-host**. Un lease abandonado nunca se
  autoreclama; la recuperación stale con evidencia y un lock distribuido multi-host
  requieren diseño/revisión separados antes de ampliar el runner.
- La revisión final Sol+Fable de esta implementación y la CI de la PR siguen pendientes
  hasta que sus resultados se registren y adjudiquen.
