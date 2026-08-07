# s306 — Propuesta a atacar: visibilidad del fail-open de canal (#63)

Commit `1391c1a`, rama `claude/s306-canal-degradado`. Impacto MEDIO en zona de dolor
(retrieval). Corre `git show 1391c1a` para el delta completo.

## OBJETIVO + MÉTRICA (declarados)

**Objetivo**: hacer VISIBLE el fail-open de canal del retriever — en s303 un 500
transitorio del RPC de enunciados bajó el pool de 34→23 chunks (−32%) sin que ningún
log ni métrica lo registrara; un fallo recurrente se leería como «el bot responde peor»
sin causa, contaminando las vistas de s301 y cualquier medición futura.
**Métrica**: NO toca ningún lever de eval. Listón: serving BYTE-IDÉNTICO salvo (a) el
reintento único ante 5xx del RPC de enunciados y (b) telemetría nueva. Suite completa
3589 passed, 0 fallos.

## Qué se construyó

1. `src/rag/retriever.py` — `vector_search` acepta `_trace`; los 3 fail-opens
   interiores (ENUNCIADOS / HYQ_TABLE / HYQ_HYDRATE) registran
   `{channel, error, error_type}` vía `_record_channel_failure` (el MISMO seam s289 del
   canal VECTOR — un formato para la clase). Reintento ÚNICO ante `status_code >= 500`
   del RPC `match_chunks_v2_enunciados`; ni 4xx (error de la petición) ni timeout
   (duplicaría la espera del turno malo).
2. `src/rag/serving_pipeline.py` — `execute_rag_turn` crea `retrieval_health` y lo pasa
   a `adapters.retrieve` SOLO si la firma acepta `_trace` (inspección con
   `inspect.signature`, NO try/TypeError: el reintento re-correría el retrieval entero
   para enmascarar un bug genuino). Lo expone como `pipeline["retrieval_health"]`.
3. `src/orchestrator/contracts.py` + `orchestrator.py` — `RetrievalResult.channel_failures`
   (tuple, default `()` para no romper constructores previos).
4. `src/rag/runtime_trace.py` — sección `retrieval` REQUERIDA del esquema cerrado;
   `_ALLOWED_CHANNELS = {VECTOR, ENUNCIADOS, HYQ_TABLE, HYQ_HYDRATE}`; al trace
   persistido solo cruzan TOKENS (canal + error_type de allowlist); el `repr` (puede
   llevar URL/payload) se queda en proceso; cota 8; validador actualizado.
5. `src/bot/telegram_bot.py` — `retrieval_health` en las DOS ramas (adapter clásico y
   orquestador — paridad).
6. `supabase/migration_proposals/20260807120000_s306_salud_canal_retrieval_v1.sql` +
   espejo en `supabase_schema.sql` — vista `salud_canal_retrieval_v1`: % de turnos
   degradados por día y por canal; security_invoker; API a cero; postcondiciones;
   filtra `COALESCE(route,'rag')='rag'` (los shortcuts no hacen retrieval).
7. `tests/test_s306_canal_degradado.py` (17) + expectativa de `test_s289_channel_health.py`
   actualizada (el registro lleva `error_type` nuevo).

## Claims fuertes del autor (atácalas contra el código)

- C1: el serving es byte-idéntico salvo el reintento 5xx — el registro jamás cambia qué
  chunks se sirven ni su orden.
- C2: el reintento no puede duplicar efectos (RPC de solo lectura) ni entrar en bucle
  (exactamente 1 reintento).
- C3: la inspección de firma cubre los callers reales (retrieve_chunks tiene `_trace`)
  y TODOS los fakes de test existentes (sin `_trace` → sin salud, sin TypeError).
- C4: la sección `retrieval` REQUERIDA no rompe nada — el validador solo corre en el
  sink de escritura (`logging_db.py` es el único caller, verificado con grep) y
  builder+validador shipean juntos.
- C5: ningún dato personal ni identificador cruza al trace persistido: solo tokens de
  allowlist; el `repr` (que puede llevar URL) se queda en proceso.
- C6: la vista es aditiva pura — sin carrera de deploy en ningún orden; `@>` containment
  sobre `[{"channel": "X"}]` cuenta bien; «sin medida» ≠ «sano» preservado
  (turnos_con_medida vs turnos_degradados).
- C7: en la rama del orquestador, `retrieval_health` se reconstruye desde
  `turn.retrieval.channel_failures` — paridad con la rama clásica.

## Preguntas duras (no te limites a ellas)

- ¿Hay algún caller de `vector_search` fuera de `retrieve_chunks` (deep_lookup, sondas)
  que ahora pierda registro o reciba un kwarg inesperado?
- ¿El `_trace` compartido puede mezclar turnos con `asyncio.to_thread` (rama orquestador)?
- ¿El fake del test (`_Cliente.colas` con `pop(0)` si `len>1`) puede dar un falso verde
  en el test del retry?
- ¿`retrieval_health` puede quedar sin asignar en algún camino del bot que llegue a
  `build_rag_serving_trace`?
- ¿Algún constructor de trace fuera de la suite (`scripts/`) que el REQUERIDO rompa?
