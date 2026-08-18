# s324h v4 — El default que miente está TRES veces

> **Cuarta versión. Las tres anteriores fueron NO SÓLIDO** (r42, r43/r44), y el patrón de
> los hallazgos es siempre el mismo: yo afirmaba por encima de lo medido y ensanchaba el
> alcance. Esta versión invierte el orden — **primero se midió el terreno, después se
> escribió**. Cada afirmación de este documento tiene un `fichero:línea` detrás y se ha
> verificado en esta sesión. Donde no hay medición, se dice.

> **Adjudicación de Alberto (18-ago):** vía estricta, «aunque necesites varias rondas de
> validación; es importante que la solución sea BP/robusta/escalable». Y la decisión de
> producto de expandir la voz al plan: *«que la transcripción de audio haga lo mismo que
> escribir la pregunta en el chat, y esa debería ser la prioridad»*.

---

## 1. El diagnóstico real (medido esta sesión, no intuido)

Las tres versiones anteriores decían que el problema era «la voz no pasa por el plan».
Eso es el **síntoma**. La causa es esta:

```
src/logging_db.py:135                      log_query(source: str = "text", ...)
src/orchestrator/contracts.py              TurnRequest.source: str = "text"
src/orchestrator/telegram_adapter.py:37    build_turn_request(source: str = "text", ...)
```

**El mismo default optimista, replicado en las tres capas.** No es un descuido puntual:
es un patrón. Y es un default que **miente**: si un llamador se olvida de la procedencia,
nada falla — se registra una fila afirmando que el turno vino por teclado.

Por eso el fallo aparece en sitios que parecían no tener relación entre sí, y por eso la
r44 encontró que mi propio arreglo iba a crear otra instancia del mismo defecto
(`_ejecutar_plan` cae a `_process_query` sin procedencia — `telegram_bot.py:1647`).

**Un default sólo debe existir cuando el valor omitido es verdad.** `"text"` no lo es:
es la mitad de los casos.

### 1.1 El síntoma que lo destapó

Alberto, con la transcripción YA correcta: «¿Qué centrales de Detnov tienes?» por voz →
«no he encontrado información relevante»; tecleada → el listado de 14. Medido: las dos
formas planifican `ruta='inventario'` idéntica. `handle_voice` nunca llama a `plan_turn`
(`telegram_bot.py:1391-1404`), así que las **nueve** rutas de atajo son inalcanzables por
voz — aplazamiento declarado de la fase B del #70.

---

## 2. El diseño, en tres capas

Cada capa ataca el problema en su nivel. La 3 es la estructural; las otras dos la hacen
usable y verificable.

### Capa 1 — Origen: un valor que no se puede construir mal

```python
@dataclass(frozen=True)
class Procedencia:
    """De dónde viene el turno. Se construye UNA vez, en el manejador."""
    source: str
    transcription: str | None = None

    @classmethod
    def de_texto(cls) -> "Procedencia":
        return cls(source="text")

    @classmethod
    def de_voz(cls, asr_crudo: str) -> "Procedencia":
        if not asr_crudo:
            raise ValueError("una procedencia de voz sin ASR crudo no es auditable")
        return cls(source="voice", transcription=asr_crudo)
```

`source` **sin default** y constructores por canal: no existe forma de fabricar una
procedencia de voz sin transcripción. Eso es lo que la v2 llamó «irrepresentable» sin
serlo — aquí sí lo es, y el test lo comprueba.

**Por qué NO es el tercer vocabulario que Sol mató en r44 (M5):** `Procedencia` no compite
con `TurnRequest` — lo **alimenta**. `build_turn_request` pasa a recibirla y derivar de
ella sus dos campos, en vez de tener su propio default. Un solo origen, tres consumidores.

### Capa 2 — Frontera: obligatoria en la firma

```python
async def _ejecutar_plan(update, context, user_id, query, plan, *, procedencia): ...
async def _responder_atajo(update, respuesta, *, user_id, query, registrar, procedencia): ...
```

**Radio medido:** `_ejecutar_plan` tiene **2** llamadores (`telegram_bot.py:1524` y
`tests/test_s316e_fase_a_equivalencia.py:326`); `_responder_atajo` tiene **1**
(`telegram_bot.py:1609`).

Y la caída conversacional —el crítico convergente de Sol y Opus 5 en r44— la reenvía:

```python
await _process_query(update, context, query, preambulo=plan.preambulo,
                     source=procedencia.source, transcription=procedencia.transcription)
```

### Capa 3 — Raíz: el default desaparece de los tres sitios

`source` pasa a ser **obligatorio** en `log_query`, en `TurnRequest` y en
`build_turn_request`. Olvidarlo deja de ser una mentira silenciosa y pasa a ser un
`TypeError` en el acto.

**Radio medido, y es pequeño:**

| | Cuántos | Dónde |
|---|---|---|
| Call sites de `log_query` en producción | **8**, todos en `telegram_bot.py` | 4 ya pasan `source` (1913, 2027, 2197, 2398); 4 no (1575, 1624, 1638, 1718) |
| Call sites de `build_turn_request` | **1** | `telegram_adapter.py` es su único constructor de `TurnRequest` |
| Dobles de `log_query` en tests que se romperían | **0** | Todos usan `lambda **k` / `lambda **kwargs` — verificado en `test_f1_activation_wiring`, `test_mt0d_orchestrator_seam`, `test_response_formatter` |

**`transcription` sí conserva su default `None`**, porque en texto la ausencia es la
verdad. La invariante que importa —`source=="voice"` ⟹ hay transcripción— la garantiza el
constructor de la capa 1, no un `if` repetido en cada llamada.

**`source` NO se tipa como `Literal["text","voice"]`.** Medido: `query_logs.source` es
`TEXT DEFAULT 'text'` **sin CHECK** (`supabase_schema.sql:97`), y `'error'` es un valor de
primera clase — se usa en `telegram_bot.py:2398` y hay una vista que filtra por él
(`supabase_schema.sql:674`). Un `Literal` binario sería falso. (Sol lo propuso en r44 M3
«aunque `log_query` admita además `error`»; el censo dice que el dominio real es ternario.)

---

## 3. Lo que hace el plan compartido

```python
async def _servir_turno(update, context, user_id, query, *, procedencia) -> None:
    if await _capture_reply_explanation(update, user_id, query):
        return
    meta = Meta(es_reply=update.message.reply_to_message is not None,
                mismatch_answer=mismatch_answer_activo(),
                fuente="voz" if procedencia.source == "voice" else "texto")
    estado_modelos = _estado_modelos_conversacion(context.user_data)
    plan = plan_turn(query, estado_modelos, meta,
                     _resolver_hechos(plan_turn_hechos(query, estado_modelos, meta)))
    if plan.transicion == _turn_plan.INVALIDAR:
        _aplicar_estado(context.user_data, WorkingState())
    await _ejecutar_plan(update, context, user_id, query, plan, procedencia=procedencia)
```

`Meta` se construye **una vez** (Fable r43: la v1 la tenía en dos sitios y la de voz
omitía `mismatch_answer`). `_ejecutar_plan` sigue siendo dueño de la caída conversacional,
así que `plan.preambulo` no se pierde (Sol y Fable, r43).

**La guarda de `user_data` se conserva.** `handle_voice` tiene hoy
`if isinstance(getattr(context, "user_data", None), dict)` (`telegram_bot.py:1382`); la v3
la retiraba sin declararlo (Opus 5, r44). Se mantiene en el preludio.

---

## 4. Qué pasa cuando falla la consulta de identidad — RESUELTO, no pendiente

La v3 lo declaró como el único punto que bloqueaba y pedía adjudicación de Alberto.
**Era un error mío: la conducta ya existe.** Medido con sonda sobre `error_taxonomy`:

| Excepción que puede lanzar la consulta | Clase | Mensaje |
|---|---|---|
| `ConnectTimeout` / `ReadTimeout` / `ConnectError` | `red_datos`, reintentable | «No he podido consultar la base de manuales ahora mismo (fallo de conexión). Vuelve a enviarme la pregunta en unos segundos.» |
| `HTTPStatusError` 5xx | `red_datos`, reintentable | ídem |
| `HTTPStatusError` 401 | `bug`, grave, **no** reintentable | «…es un defecto» |

La taxonomía ya distingue «la base no responde, reintenta» de «la clave está mal, esto es
un bug» — más fino que el mensaje único que yo proponía. Y `handle_voice` ya deriva sus
excepciones ahí (`telegram_bot.py:1412-1429`).

**Consecuencia:** no se añade ninguna frontera de fail-open. La de la v2 fue matada por
Sol (regresión de SEGURIDAD: saltarse `mismatch`/`marca_no_servida` puede dar una
respuesta cross-brand) y por Fable (regresión de OBSERVABILIDAD: convertir una incidencia
visible en degradación silenciosa desmonta la telemetría de `bot_errors` que s324e
construyó). **La conducta de hoy se conserva, y es la correcta.**

---

## 5. Cambios de conducta — todos declarados, todos con fila en el gate

| # | Cambio | Valoración |
|---|---|---|
| B1 | `_capture_reply_explanation` pasa a correr en voz | **Coste declarado** (Opus 5, r44): esa función no distingue pregunta de explicación — si el reply apunta a una respuesta anclada, se traga el mensaje y contesta «Anotado 👍». Verificado en `telegram_bot.py:1436-1462`. **Ya pasa hoy en texto**: no es un defecto que nazca aquí, es uno existente que el cableado extiende al otro canal. Paridad incluye heredar los defectos; arreglarlo es un lote aparte (ver L2) |
| B2 | `es_reply` en voz pasa de `False` a `True` en replies ⇒ deja de invalidar | Es la conducta del texto, o sea paridad. Fila propia en el gate, **afirmando estado** (`mt_working_state`), no mensajes: invalidar o preservar puede dar la misma respuesta en el turno (Sol, r44) |
| B3 | Cortesía hablada deja de registrar fila | Coherente con la promesa v7 |
| B4 | Feedback hablado se captura como feedback | Ver L1 |

## 6. Límites — lo que este lote NO arregla

- **L1** — Un feedback hablado **no deja el ASR crudo en ningún almacén**: `log_feedback`
  no acepta `source` ni `transcription` (`logging_db.py:326-332`) y el plan declara
  `log_consulta=False` para esa ruta. Hueco de **esquema**. Se declara; no se tapa.
- **L2** — `_capture_reply_explanation` traga preguntas (B1). Preexistente en texto.
- **L3** — Clarify por voz ya pierde `transcription` hoy (`telegram_bot.py:1913, 2027`
  pasan `source` pero no `transcription`). Preexistente.
- **L4** — **No compra paridad bilingüe**: el ASR fuerza `language="es"` y el catálogo EN
  sigue en `xfail(strict)`.
- **L5** — El fallo «no te he entendido» (transcripción que no es ninguna marca) **no se
  aborda aquí**. Fable (r46) señaló que su causa raíz ya se atacó con el cambio de modelo
  ASR (s324g), y que el mensaje honesto sería remedio del residuo. Además Sol (r45)
  demostró que «cero marcas reconocidas» **no** demuestra «el ASR no entendió»: el
  reconocedor es un regex curado más el léxico de marcas servidas, así que una marca real
  fuera del regex o un descriptor son indistinguibles. Necesita diseño propio.
- **L6** — Sin smoke real contra Telegram hasta que Alberto mande un audio.

## 7. Las puertas — ya escritas y verificadas

`tests/test_s324h_paridad_voz_texto.py`, en el repo desde antes de esta propuesta, y
**comprobado que discrimina**: hoy falla en lo roto y pasa en lo que funciona.

1. **Paridad 9 rutas × 2 canales.** Compara la **secuencia completa de mensajes** —no sólo
   la respuesta—, porque la voz emite además la burbuja `🎤` y una métrica que sólo mirase
   la respuesta daría paridad donde no la hay (Sol, r43).
2. **Procedencia con aserción ANTI-VACUIDAD**: sin ella el test pasaba cuando la voz no
   escribía nada, que es el estado roto de hoy.
3. **No-regresión ×3**: PASAN hoy y protegen la ruta conversacional. Es el crítico de r44
   convertido en puerta.
4. **B2 afirma estado**, con frase discriminante verificada por sonda («y de Notifier?»
   preserva en los DOS canales y no servía).
5. **Test AST** exigiendo `source=` **y** `transcription=` — pendiente de escribir; la v3
   sólo exigía `source`, con lo que un atajo podía perder el ASR crudo sin que la suite lo
   notara (Fable, r43).
6. **Equivalencia s316e**: sus **asserts de conducta** son intocables. La *fixture* sí se
   adapta mecánicamente para pasar `procedencia` — la v3 decía «los tests no pueden
   moverse» y eso contradecía su propio cambio de firma (Sol, r44 M5). Distinción explícita.

## 8. Por qué es BP, estructural y escalable

**BP**: ningún default afirma algo que puede ser falso. Un turno de voz no puede quedar
registrado como texto sin que la suite lo cante.

**Estructural**: ataca la causa —el default replicado en tres capas— y no el síntoma —la
ruta que faltaba—. Después de esto, el bug que motivó el lote **no se puede reintroducir
en ninguna de las tres capas**, no porque alguien se acuerde, sino porque la firma no lo
permite.

**Escalable**: el canal que venga construye su `Procedencia` y todo lo demás funciona sin
tocarse. Y cualquier `log_query` futuro, en cualquier fichero, tiene que declarar de dónde
viene el turno.

**Lo que NO se afirma**: esto no mejora el fail-open, no arregla el hueco de esquema del
feedback hablado, no aborda «no te he entendido», y no da paridad bilingüe.
