# s321 — Conducta (a) ante marca↔producto errónea: «corregir la marca Y responder» · PROPUESTA v1 (nada cableado)

**Origen**: `DEC-224 §B`. Decisión de PRODUCTO de Alberto (16-ago): ante «el ASD535 **de Detnov**», el bot
debe **corregir la marca y responder en el mismo turno**. Hoy corrige y **pide confirmar** (conducta b).
Prefiere fluidez con el riesgo declarado.

**Impacto**: MEDIO en zona de dolor (serving del bot de Telegram) ⇒ **dúo completo ANTES de cablear**
(Protocolo 3). Flag **default OFF byte-idéntico**; el ON es acción de Alberto en Railway.

---

## 1 · Estado real HOY (verificado en código, no en docs)

- `src/orchestrator/turn_plan.py:451-460`: detecta la 1ª marca del texto (`_MANUFACTURER_NAMES`), extrae
  modelos, resuelve `Hecho("marca_de_modelo", modelo)` en el catálogo; si la marca real ≠ mencionada →
  `TurnPlan(ruta="mismatch", datos={modelo, marca_real, marca_mencionada}, log_consulta=True)`.
- `src/bot/telegram_bot.py:1178-1189`: responde literal «*El *{modelo}* es un producto de *{marca_real}*,
  no de _{mencionada}_. ¿Te refieres al *{modelo}* de *{marca_real}*? Si es así, dime tu pregunta y te
  ayudo.*», loguea `route="manufacturer_mismatch"`, y **`return`** — no llama a `_process_query`.
- `_process_query(update, context, query, source, transcription)` (l.1306) extrae `target_models` **de la
  query** (`extract_product_models`), que **no mira la marca**: con «el ASD535 de Detnov» resuelve
  `['ASD535']` (verificado ejecutando el detector en s321). El RAG llegaría al ASD535 real por catálogo.
- El harness (`test_bot_vs_gold.run_bot`) llama a `execute_rag_turn` directo y **no atraviesa esta ruta**
  ⇒ el cambio es **invisible para factlevel/bvg**; se prueba con tests del handler + smoke del bot real.

## 2 · Recomendación

**Un flag, un sitio, sin tocar el planificador.**

```
MISMATCH_ANSWER = off (default) | on
```
- `off` → conducta actual **byte-idéntica** (mismo texto, mismo `return`, mismo log).
- `on`  → en la ruta `mismatch`: (1) enviar la corrección de marca **corta** («*El *{modelo}* es un producto
  de *{marca_real}*, no de _{mencionada}_. Te respondo sobre el *{modelo}* de *{marca_real}*:*»);
  (2) `await _process_query(update, context, query)` **con la query original**; (3) log de la ruta con
  `route="manufacturer_mismatch_answered"` (nombre NUEVO para no contaminar la serie histórica de
  `manufacturer_mismatch`).

**Por qué la query original y no reescrita** («ASD535 de Securiton…»): reescribirla inventa texto del
usuario en el log de consultas y en el contexto conversacional; y no hace falta — `extract_product_models`
ya resuelve el modelo sin la marca. Menos superficie, menos sorpresas.

**Por qué en `telegram_bot.py` y no en `turn_plan.py`**: el plan **describe** el turno («esto es un
mismatch»); qué se hace con él es transporte/handler. `turn_plan` no cambia ⇒ sus tests no cambian ⇒ la
detección sigue idéntica con flag on/off. Solo cambia la **reacción**.

**Registro**: `src/flags.py` alta de `MISMATCH_ANSWER` (`default_fuente: '"off"'`, `via: getenv`,
`lectores: src/bot/telegram_bot.py`) — el test `test_s311_flags_registry` lo exige.

## 3 · Alternativas descartadas

- **(b) dejar como hoy** — es la conducta actual; Alberto la descartó (un turno más).
- **Reescribir la query con la marca correcta** — inventa texto del usuario; innecesario (§2).
- **Devolver desde `turn_plan` una ruta nueva `mismatch_answer`** — mueve una decisión de transporte al
  planificador y obliga a tocar sus tests; el flag en el handler es más pequeño y reversible.
- **Suprimir la corrección y responder a secas** — perdería la corrección de marca, que es la mitad del
  valor (el técnico se entera de que se equivocó).
- **Cablearlo ON por defecto** — no: es serving; ON = acción de Alberto con recibo (patrón DEC-203b/205b).

## 4 · Riesgos declarados

1. **El técnico se equivocó de APARATO, no solo de marca** (p. ej. dice «ASD535 de Detnov» pero quería el
   ADW535). Con (a) el bot responde sobre el ASD535 y el técnico puede no darse cuenta. Con (b) el
   «¿te refieres a…?» lo cazaba. **Es el riesgo que Alberto acepta**; se mitiga con la corrección
   explícita al principio del mensaje.
2. **`_process_query` sigue el pipeline completo** (sesión, contexto conversacional, logging). Llamarla
   desde `mismatch` **duplica** un `log_query` si no se tiene cuidado (el mismatch ya loguea). Diseño:
   con `on`, la ruta mismatch NO loguea por su cuenta — deja que `_process_query` loguee, y añade el
   marcador `manufacturer_mismatch_answered` vía su parámetro/contexto (a verificar en el código: si
   `_process_query` no admite un `route` externo, se loguea la corrección aparte con `response_length`
   solo de la corrección — declarar cuál).
3. **Contexto conversacional**: la corrección va como mensaje separado; el `_process_query` guarda la
   respuesta RAG en la sesión. El siguiente turno «¿y el modelo grande?» resolvería sobre ASD535 —
   correcto.
4. **No hay smoke real posible en esta PR** (no toco prod). Se deja el checklist de encendido para Alberto:
   flip en Railway → 3 preguntas de prueba (marca errónea / marca correcta / marca no servida) → recibo en
   `query_logs`.

## 5 · Qué prueba (tests, todos con flag OFF y ON explícitos)

- `off`: `handle_message` sobre «el ASD535 de Detnov…» → **exactamente** el texto actual, `return` sin
  RAG, `route="manufacturer_mismatch"` (byte-identidad con un fixture del texto actual).
- `on`: mismo input → 1er mensaje = corrección corta; después `_process_query` **invocada una vez** con
  la query original; log con la ruta nueva.
- `on` con marca **correcta** («ASD535 de Securiton») → NO pasa por mismatch (turn_plan igual) ⇒ RAG
  directo, sin corrección — el control limpio (`hp019`).
- `on` con marca **no servida** → ruta `marca_no_servida` intacta.
- Registro de flags: `MISMATCH_ANSWER` en `REGISTRO` con lector `telegram_bot.py`.

## 6 · Lo que el dúo tiene que atacar

1. ¿Es correcto NO tocar `turn_plan` y hacerlo en el handler, o hay una razón de arquitectura (F1/orquestador,
   `conversation_policy`) por la que la ruta debería nacer ya como «mismatch-answer»?
2. El doble log (mismatch + `_process_query`): ¿cómo lo resuelve el código actual para rutas parecidas
   (p. ej. `inventario` con `fallback_ruta`)? ¿Hay un patrón que reutilizar?
3. ¿La query original basta siempre? Casos donde `extract_product_models` NO resuelva el modelo pero el
   catálogo sí lo haya resuelto para el mismatch (¿puede pasar? `turn_plan` usó `modelos[0]`).
4. Voz: `_process_query(source="voice", transcription=…)` — ¿la ruta mismatch se alcanza desde voz? Si sí,
   ¿el flag debe pasar `source`?
5. ¿Qué smoke SÍ se puede hacer sin prod? (¿un test de integración con el `Update` fake que ya usen los
   tests del bot?)
