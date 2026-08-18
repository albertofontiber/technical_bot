# s324h — Revisión del CÓDIGO cableado (Fase 1)

**El diseño ya está revisado y aprobado.** Fable dio **SÓLIDO** a la v5
(`evals/s324h_voz_al_plan_propuesta_v5.md` + `s324h_v5_addendum_r48.md`) tras verificar
trece anclajes contra el repo. Esta ronda es distinta: **atacad la IMPLEMENTACIÓN**, no
el diseño. Lo que puede estar mal ahora está en el código, no en el documento.

El diff completo está en `evals/s324h_cableado_fase1.diff` (259 líneas). Los ficheros
nuevos, `src/bot/procedencia.py` y `tests/test_s324h_procedencia.py`, van enteros.
`src/bot/telegram_bot.py` **no** se adjunta —145 KB ahogarían el presupuesto— pero está
en el repo y las tools pueden leerlo.

---

## Qué se cableó

1. **`Procedencia`** (`src/bot/procedencia.py`): canal del turno + ASR crudo, con la
   invariante en `__post_init__`. Sin default: omitir el canal es `TypeError`.
2. **`_servir_turno`**: el preludio compartido (captura de reply → `Meta` → hechos →
   plan → transición → despachador). Los dos manejadores quedan reducidos a construir su
   `Procedencia`.
3. **`_FUENTE_META`**: mapa explícito `text/voice` → `texto/voz`. Antes era
   `"voz" if source == "voice" else "texto"`, que colapsaba cualquier canal futuro.
4. **Frontera obligatoria**: `_ejecutar_plan` y `_responder_atajo` exigen `procedencia`
   keyword-only sin default; los cuatro `log_query` de atajo la propagan.
5. **El crítico de r44**: la caída conversacional reenvía `source`/`transcription` a
   `_process_query`.
6. **Dos defaults muertos**: `log_query(source)` y `_process_query(source)` sin default.
7. **Restricción PAGADA retirada y declarada**: el `try/except` local de `handle_voice`
   (Sol fase-B M5) que dejaba continuar el turno ante un fallo del clasificador. Razones
   escritas en el código: paridad (el texto nunca lo tuvo) y observabilidad (el `warning`
   moría en el log sin dejar fila en `bot_errors`).

## Estado medido

- Gate de paridad: **24/24**. Antes de cablear fallaban 12 — discrimina.
- `tests/test_s324h_procedencia.py`: **17/17** (invariante + AST + completitud del mapa).
- Nueve tests rotos por el cambio de firma, **todos ejerciendo el default mentiroso**:
  siete adaptados mecánicamente; la fixture de `test_s316e` adaptada **sin tocar sus
  asserts de conducta**; y `test_audio_input` **sí cambia un assert**, declarado en el
  propio test — la voz ahora recibe `preambulo`, o sea el lever de mismatch, que antes
  sólo llegaba por teclado.
- Suite completa: corriendo al escribir esto.

## Dónde mirar con más saña

1. **La rama `else` de `handle_voice`.** Si `context.user_data` no es dict, se salta el
   preludio y llama a `_process_query` directo. ¿Es correcta esa degradación, o abre una
   vía por la que la voz vuelve a saltarse el plan sin que ningún test lo note?
2. **`_servir_turno` accede a `update.message.reply_to_message` sin `getattr`**, mientras
   `_capture_reply_explanation` sí lo usa. ¿Puede reventar con un Update real?
3. **Orden de efectos**: ¿la transición se aplica antes de ejecutar la ruta, como exige el
   contrato de flujo de datos del v3? ¿Se rompió algo al mover el bloque?
4. **`_FUENTE_META[procedencia.source]`** lanza `KeyError` a propósito. ¿Está en un sitio
   donde ese `KeyError` es un fallo de test y no un turno perdido en producción?
5. **El gate**: `_comparables` normaliza `query_log_id` a `"<uuid>"`. ¿Esa normalización
   tapa algo que debería cazar? ¿Y hay ahora algún camino por el que la paridad pase sin
   que la conducta lo sea?
6. **Fugas del diff**: ¿queda algún `log_query`, en cualquier fichero, que pueda
   registrar un turno de voz como texto? El AST sólo vigila `_ejecutar_plan` y
   `_responder_atajo`.
7. **`Procedencia` es frozen pero `transcription` es `str | None`**: ¿algún sitio la
   muta, la reconstruye mal, o pierde el ASR crudo por el camino?

## Lo que NO es esta ronda

No re-litiguéis el diseño (validado en r48), ni el alcance en dos fases (la Fase 2 —
`TurnRequest`, `build_turn_request` y la migración — está declarada y fuera), ni los
límites L1–L6 de la v5.
