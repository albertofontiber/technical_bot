# s324h v3 — La voz pasa por el plan (alcance ESTRECHADO tras dos rondas de dúo)

> **Adjudicación de producto (Alberto, 18-ago, en sesión).** El código vivo declara que
> expandir la voz al plan completo es «una decisión de producto SEPARADA»
> (`telegram_bot.py`, `handle_voice`). Alberto la adjudicó explícitamente: *«me preocupa
> más la transcripción de audio que haga lo mismo que escribir la pregunta en el chat,
> y esa debería ser la prioridad»*. La v2 la ejecutó con argumento técnico sin citarla
> (hallazgo menor de Fable, r43); aquí queda citada. Alberto además eligió la vía
> **estricta**: v3 + tercera ronda antes de cablear.

> **Qué cambia respecto a la v2: el alcance SE ESTRECHA.** Las dos rondas anteriores
> devolvieron NO SÓLIDO, y en la r43 **los dos críticos atacaban alcance que añadí yo**,
> no lo que se pidió. La v3 quita ese alcance. No es una v2 con parches: es la v2 menos
> lo que no debía estar.

---

## 0. Objetivo, alcance y NO-alcance

**Objetivo**: que la misma pregunta obtenga la misma respuesta por voz y por texto.

**Alcance (dos cosas, ninguna más):**
1. La voz pasa por `plan_turn` y por el despachador, igual que el texto.
2. La procedencia (`source`, `transcription`) llega a las **cuatro** rutas de atajo que
   escriben en `query_logs`.

**NO-alcance, explícito y por qué:**

| Fuera | Por qué |
|---|---|
| **La frontera de fail-open a conversacional** | Los DOS revisores la mataron por motivos que no se solapan. Sol: es regresión de SEGURIDAD — `lookup_model_manufacturer` hace `raise_for_status()`, así que un blip de red degradaría al RAG **saltándose** las guardas `mismatch`/`marca_no_servida`, y el bot podría contestar sobre otra marca. Fable: es regresión de OBSERVABILIDAD — convierte una incidencia visible en degradación silenciosa, desmontando la telemetría de `bot_errors` que s324e acaba de construir. **La conducta de fail-open de hoy se conserva TAL CUAL en los dos canales.** El fail-closed correcto ante identidad no verificable es un problema propio, preexistente, con su propio dúo |
| **El tipo `Entrada`** | `TurnRequest` (`orchestrator/contracts.py`) ya lleva `source` + `transcription`. Un dataclass nuevo sería un TERCER vocabulario, y con el mismo default mentiroso (Sol M5 + Fable M1) |
| **`transcription` en clarify** (`telegram_bot.py:1913, 2027`) | Pasan `source=source` pero no `transcription`: un clarify por voz **ya pierde hoy** el ASR crudo. Es un hueco PREEXISTENTE, no de esta refactorización. Apuntado como deuda; ensancharlo aquí repetiría el error que el dúo me ha recortado dos veces |
| **Paridad bilingüe** | El ASR fuerza `language="es"` y el catálogo EN sigue en `xfail(strict)`. La v1 lo vendió como «escalable» sin verificarlo |

---

## 1. Diagnóstico (verificado por los dos revisores en las dos rondas)

`handle_voice` no llama a `plan_turn`: sólo a `_decidir_transicion`, y salta a
`_process_query` (RAG completo). Las **nueve** rutas de atajo son inalcanzables por voz.
Medido: la pregunta hablada y la tecleada planifican ambas `ruta='inventario'` con
`datos={'marca':'Detnov','filtros':{'categoria':'central'}}`.

`_ejecutar_plan` **ya existe** y ya es el despachador tonto, dueño de la caída a
conversacional con `plan.preambulo`. Lo que falta compartir es el **preludio**.

---

## 2. La pieza

### 2.1 Preludio compartido — `Meta` construida UNA vez

```python
async def _servir_turno(update, context, user_id, query, *,
                        source: str, transcription: str | None) -> None:
    if await _capture_reply_explanation(update, user_id, query):
        return
    meta = Meta(es_reply=update.message.reply_to_message is not None,
                mismatch_answer=mismatch_answer_activo(),
                fuente="voz" if source == "voice" else "texto")
    estado_modelos = _estado_modelos_conversacion(context.user_data)   # (Fable r43: era libre)
    plan = plan_turn(query, estado_modelos, meta,
                     _resolver_hechos(plan_turn_hechos(query, estado_modelos, meta)))
    if plan.transicion == _turn_plan.INVALIDAR:
        _aplicar_estado(context.user_data, WorkingState())
    await _ejecutar_plan(update, context, user_id, query, plan,
                         source=source, transcription=transcription)
```

**Sin `try` nuevo**: si `_resolver_hechos` lanza, escapa igual que hoy — al manejador de
errores en texto y al `except` de `handle_voice` en voz. Conducta preservada, incidencia
preservada, guardas de marca preservadas.

### 2.2 La procedencia: parámetros **keyword-only sin default**

No un tipo nuevo, no un default que miente:

```python
async def _ejecutar_plan(update, context, user_id, query, plan, *,
                         source: str, transcription: str | None): ...
async def _responder_atajo(update, respuesta, *, user_id, query, registrar,
                           source: str, transcription: str | None): ...
```

Sin default, `source` es **obligatorio en la firma**: una llamada que lo omita es un
`TypeError`, no una fila mal atribuida. Y las cuatro `log_query` de atajo lo propagan.

**Corrección de prosa de la v2**: dije «hace irrepresentable el estado incorrecto» y no
es cierto — `source` sigue siendo un `str` y admite cualquier cadena (Sol M3 + Fable M1).
Lo que sí es cierto, y es lo que se afirma aquí: **el estado incorrecto no se puede
introducir sin romper la suite**. Es una puerta, no una imposibilidad de tipos.
(Un `Literal` global tampoco valdría: `log_query` recibe además `source="error"` en
`telegram_bot.py:2398`, así que el dominio no es binario.)

### 2.3 Censo exacto de lo que se toca

| Ruta | ¿Loguea? | Línea | Hoy | Tras el cambio |
|---|---|---|---|---|
| inventario | sí | 1575 | sin `source` | `source` + `transcription` |
| mismatch | sí | 1624 | sin `source` | `source` + `transcription` |
| marca_no_servida | sí | 1638 | sin `source` | `source` + `transcription` |
| catálogo / fabricantes | sí (vía `_responder_atajo`) | 1718 | sin `source` | `source` + `transcription` |
| 3 cortesías | **no** (`log_consulta=False`) | — | — | sin cambio |
| feedback | usa `log_feedback`, no `query_logs` | — | — | ver límite L2 |

(La v2 decía «los nueve atajos llaman `log_query`». **Falso**: son cuatro. Cazado por Fable.)

---

## 3. Cambios de conducta — declarados, cada uno con su fila en el gate

| # | Cambio | Valoración |
|---|---|---|
| B1 | **`_capture_reply_explanation` pasa a correr en voz** | GANANCIA: hoy una explicación hablada en reply se va al RAG |
| B2 | **`es_reply` en voz pasa de `False` a `True` en replies** ⇒ `PRESERVAR` incondicional, o sea deja de invalidar el contexto de marca | Es PARIDAD con texto, y por eso es correcto — pero es cambio real y la v2 no lo declaró (Fable r43). Fila propia en el gate, con variante reply |
| B3 | Cortesía hablada **deja de loguearse** | Coherente con la promesa v7; hoy un «hola» hablado sí deja fila |
| B4 | Feedback hablado **se captura como feedback** en vez de ir al RAG | Deseable; ver límite L2 |

## 4. Límites declarados (lo que este lote NO arregla)

- **L1** — La conducta de fail-open no mejora en ningún canal: se preserva. Deuda propia.
- **L2** — **Un feedback hablado no deja el ASR crudo en NINGÚN almacén**: `log_feedback`
  no acepta `source` ni `transcription`, y el plan declara `log_consulta=False` para esa
  ruta. Es un hueco de **esquema**, no de enrutado (Fable r43). Se declara; no se tapa.
- **L3** — Clarify por voz ya pierde hoy `transcription` (preexistente).
- **L4** — Sin smoke real contra Telegram hasta que Alberto mande un audio.

## 5. Las puertas

1. **Test AST** sobre `_ejecutar_plan` y `_responder_atajo`: toda llamada a `log_query`
   debe pasar `source=` **y** `transcription=`. La v2 sólo exigía `source=`, con lo que
   un atajo podía loguear `source="voice"` y perder el ASR crudo sin que la suite lo
   notara (Fable r43). Precedente en casa: el test de mecanicidad por AST de
   `_resolver_hechos` (`test_s316e_fase_a_equivalencia.py:359`).
2. **Tabla de paridad — 10 rutas × 2 canales** (nueve + captura de reply, que es fila
   propia: Sol r43), con **variantes reply** para B2. Se compara la **secuencia completa
   de mensajes**, no sólo el texto de la respuesta: la voz emite además la burbuja
   `🎤 <transcripción>`, y una métrica que sólo mirase «el texto de la respuesta» daría
   paridad donde no la hay (Sol r43). GO = filas idénticas salvo en lo que DEBE diferir:
   la burbuja ASR, `source` y `transcription`.
3. **Equivalencia byte a byte del camino de TEXTO**: los tests s316e no pueden moverse.
   Si se mueven, la refactorización rompió algo que hoy funciona.

## 6. Por qué es BP, estructural y escalable

**BP**: la misma pregunta obtiene la misma respuesta por los dos canales, y ninguna fila
de `query_logs` puede quedar mal atribuida de canal sin romper la suite. **Estructural**:
el preludio deja de estar duplicado-y-mutilado; `Meta` tiene un solo constructor; la
procedencia es un parámetro obligatorio y no un default optimista. **Escalable**: la ruta
que nazca mañana funciona por voz sin tocar nada, y el test AST obliga a cualquier
`log_query` futuro de atajo a declarar su origen.

**Y lo que NO se afirma** (dos rondas de dúo me han enseñado a escribir esta sección):
esto no mejora el fail-open, no arregla el hueco de esquema del feedback hablado, no da
paridad bilingüe, y no hace nada «irrepresentable» — pone una puerta.
