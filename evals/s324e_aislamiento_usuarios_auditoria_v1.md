# s324e — Aislamiento entre usuarios: auditoría del red line del piloto multi-DG (v1)

**Red line (Alberto):** cada DG tiene su sesión y son independientes; un usuario ve sólo
aquello por lo que pregunta. El feedback agregado sí bebe de todos.

**Método.** Turno leído (handler → plan → política → orquestador → generación →
render) + `tests/test_s324e_aislamiento_usuarios.py` (12 verdes, 1 `xfail`; $0, sin red ni
DB). PTB se conduce **real y offline**: la semántica del framework se mide, no se supone.
Control anti-vacuidad: compartiendo `user_data` entre los dos DG, 4 tests se ponen rojos.
Las líneas de `telegram_bot.py` son de HOY (otro agente lo edita en paralelo).

---

## P1 · ¿Puede la conversación de un usuario aparecer en la respuesta de otro? — **NO**

- **Estado por usuario.** `context.user_data` lo indexa PTB por `user.id` (medido:
  `test_ptb_particiona_user_data_por_usuario`; la clave es el **usuario**, no el chat).
  Ahí viven el estado conversacional (escritor único `telegram_bot.py:160`, invariante AST
  de s316 — **no duplicado**, solo anclado) y el clúster de feedback (`:1501-1502`,
  `:1521`, `:1590-1591`, `:1694`).
- **Estado de proceso: censo CERRADO de 5 nombres**, todos derivados del CORPUS.
  `_fabricantes_cache:308`, `_marcas_db_cache:665`, `_inventario_falla_ts:330` (sin
  clave); `_inventario_cache:329` con clave `marca(+filtros json)` (`:596`, `:617`);
  `_INTENT_FN_CELL:669`, que guarda el **cliente** del clasificador bajo la clave literal
  `"fn"` (`:696`, `:710`), nunca conversación. Probado por conducta: dos DG con el mismo
  inventario producen **una** entrada y el **mismo** valor; el filtro sí entra en la clave
  (sin eso, dos vistas se servirían cruzadas). El censo es un test: un global nuevo lo
  enrojece.
- **`fn.ultima`** (`intent_llm.py:81/85`) es atributo de función = estado de proceso
  escrito **en cada turno**. Confirmado por AST que **ningún** módulo servido
  (`src/bot` + `src/orchestrator` + `src/rag`) lo **lee**: la telemetría del turno es el
  dict `intent_obs` (`:672`, `:1435`). Único lector vivo:
  `scripts/s316g_intent_cohort_gate.py:58` (gate secuencial, fuera del serving).
- Sin argumentos por defecto mutables en `src/`. Las cachés de retrieval (`_T2Q1_CACHE`,
  `_HYQ_CACHE`, `_KNOWN_MANUFACTURERS_CACHE`) leen ficheros/DB del corpus;
  `logging_db._consent_cache/_seudonimo_emitido` (`:66-71`) van **keyed por user_id**.

**Límite operativo (no de código):** la unidad es el *usuario de Telegram*. Dos DG en el
**mismo grupo** tendrían estados separados pero se verían los mensajes: **el piloto va en
chats privados 1:1.**

## P2 · `user_data` en un reinicio — **memoria pura: pérdida de contexto, NO fuga**

`run_bot` (`:2142`, `:2152`) construye la Application **sin** `.persistence(...)`
(verificado en vivo: `app.persistence is None`). Un redeploy de Railway a mitad de
conversación borra `mt_working_state` y el clúster de feedback de **todos** los DG.

Efecto exacto, probado: el siguiente turno anafórico **no** se contesta con el producto de
nadie — F1 lo resuelve **CLARIFY a $0** pidiendo el modelo. Sobreviven: consentimiento, el
ancla de explicación por *reply* (`answer_messages`, en DB) y la telemetría ya escrita.
`run_polling` sin `drop_pending_updates` (default `False`) entrega al arrancar lo enviado
durante el corte — no se pierde, pero se procesa con estado vacío.

## P3 · Concurrencia — **hoy no hay entrelazado; y aunque lo hubiera, no cruza**

`run_bot` no llama a `.concurrent_updates(...)`, así que PTB 22.7 usa
`SimpleUpdateProcessor(max_concurrent_updates=1)` y `Application.__update_fetcher`
**awaita** cada update en vez de crear tarea: turnos **de uno en uno** (verificado en
vivo). Los 4 `global` del bot son cachés de corpus; ningún atributo de módulo se escribe
en caliente con datos de usuario.

Prueba **independiente** de esa configuración: dos turnos **en vuelo a la vez** —barrera
dentro del hilo de `asyncio.to_thread(run_turn, …)` (`:1568`), solapamiento garantizado—
sin cruce de estado ni de respuesta.

**Lo que sí muerde el piloto (latencia, no fuga):** *head-of-line* — un turno RAG largo
bloquea a los demás DG. Si se enciende la concurrencia, el test se pone rojo y obliga a
decidirlo conscientemente.

## P4 · Doble instancia — **HUECO REAL: no hay guarda** (testigo `xfail(strict)`)

Con long polling, dos procesos con el mismo token hacen que Telegram devuelva **409
Conflict**; PTB lo enruta a `on_err_cb` y `network_retry_loop` reintenta con
`max_retries=-1` (**indefinido**). Ninguna para. Los updates se reparten no
determinísticamente: los turnos de un mismo DG caen en procesos distintos y **su sesión se
parte**. `Conflict` ya se clasifica como crítico de transporte
(`error_taxonomy.py:266`), pero clasificar no es parar.

**Recomendación: parada explícita ante `Conflict`** en la red global — 6 líneas, sin DDL
ni infra. **No la cablo: toca `telegram_bot.py`**, que otro agente edita. Diff propuesto:

```python
from telegram.error import Conflict            # junto a los imports de telegram

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    exc = getattr(context, "error", None)
    # (s324e) 409 = OTRA instancia con el mismo token. PTB reintentaría siempre y
    # Telegram repartiría los updates: la sesión de un DG se parte en dos procesos.
    if isinstance(exc, Conflict):
        logger.critical("409 Conflict: otra instancia con el mismo token; parando")
        aplicacion = getattr(context, "application", None)
        if aplicacion is not None:
            aplicacion.stop_running()
        return
    ...                                          # resto igual
```

*Riesgo declarado:* en un redeploy con solape podría pararse la instancia nueva; mitiga que
Railway hace stop-then-start y que `stop_running()` sale limpio y relanza.
*Alternativa descartada:* lock por token en DB — más fuerte, pero exige DDL, TTL y
huérfanos; desproporcionado para un piloto y no cierra el 409 antes.

## Lo que NO queda garantizado (declarado)

1. Guarda de instancia única (P4) — pendiente del diff.
2. `_inventario_cache` crece sin cota: memoria, no aislamiento.
3. Los tests conducen **texto**; `handle_voice:930` comparte `_process_query`, su ASR no.
4. Chats de grupo (ver P1): garantía de estado, no de visibilidad.
5. Si se enciende `concurrent_updates`, revisar `_INTENT_FN_CELL` (sin lock,
   *last-write-wins* declarado — benigno: se pisa un **cliente**, no datos).
