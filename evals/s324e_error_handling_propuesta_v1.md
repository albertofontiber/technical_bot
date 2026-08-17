# s324e — Manejo de errores del bot: red de seguridad + insights (propuesta v1)

> **Estado: CABLEADO y SIN APLICAR.** Nada tocado en Railway ni en Supabase; la migración
> `015_bot_errores.sql` está escrita y **no ejecutada** (comprobado: la tabla no existe).
> **Dúo r37 (Sol xhigh) aplicado**: los 7 hallazgos, 2 críticos. Pendiente: revisión de Alberto
> y del asesor jurídico (aviso v8).
>
> **Verificado**: suite completa en verde y smoke **de solo lectura** contra Supabase real — el
> script detecta la tabla ausente, lee las heredadas (0) y sale 0; cazó un fallo real (reventaba
> al imprimir un emoji en consola cp1252).

## El fallo que se cierra

Verificado por grep: **24 `except Exception` dispersos y CERO `add_error_handler`**. Fuera de
dos puntos (`accept_command`, `_process_query`), una excepción no manejada deja al técnico en
**silencio**. Y donde sí hay mensaje, es **uno para todo**: un timeout transitorio (reintentar
funciona) y un `KeyError` determinista (reintentar falla igual) se cuentan con la misma frase.
Con Directores Generales en el piloto, el silencio se lee como «esto no funciona».

## Recomendación

Cuatro piezas, cada una en su sitio:

1. **`src/bot/error_taxonomy.py` — hoja PURA** (sin I/O, sin entorno, **sin importar ningún
   SDK**). Clasifica por CAUSA y devuelve una `Decision`: clase, severidad, `reintentable`,
   mensaje, si lleva código de incidencia y si es siquiera *entregable*. Clasificación
   **nominal** (nombres del MRO) y no `isinstance`: importar los SDK en una hoja que carga al
   arrancar el worker significa que uno que reestructure sus excepciones **apaga el bot en el
   import** — el mecanismo contra el silencio sería lo que apaga el bot. El agujero de lo
   nominal lo cierra un test con excepciones **reales de los 5 orígenes** (httpx, telegram,
   anthropic, openai, voyageai): si un `pip install -U` mueve un nombre, cae la suite.
2. **Red de seguridad global**: `app.add_error_handler(error_handler)`, registrado **sin
   gatear** — una red detrás de un flag no es una red. `_reportar_error(...)` es el **punto
   único** que clasifica, avisa y registra; los dos puntos que ya respondían pasan por él. Los
   **24 `except` locales no se tocan**: ya responden, y convertirlos sería una regresión.
3. **Persistencia en dos piezas, por gobernanza**: la **consulta** (dato personal) sigue yendo a
   `query_logs` con `source='error'` — ya está en la matriz de retención, ya cascadea y ya la
   excluyen las vistas de salud; el **diagnóstico** va a `bot_errors` por FK
   `ON DELETE CASCADE`. `bot_errors` **no tiene dato personal DIRECTO, pero sí ENLAZABLE** por
   esa FK (el script la recorre para sacar pregunta y autor): no queda fuera del RGPD, **hereda**
   la gobernanza de `query_logs` en vez de crear un contenedor con reglas propias.
4. **`scripts/s324e_bot_errores_insights.py`**: agrega por clase / módulo:línea / día / etapa,
   saca el top-5 de preguntas que fallan y cuenta **cuántas veces el técnico se quedó sin
   aviso**.

**Taxonomía resultante** (vocabulario cerrado, idéntico en código y en el `CHECK` de la tabla —
un test lo compara):

| clase | causa | reintentar | severidad |
|---|---|---|---|
| `red_datos` | timeout/red hacia Supabase (httpx) | **sí** | aviso |
| `llm_saturado` | 429/529/503 del proveedor (Anthropic, OpenAI, Voyage) | **sí** | aviso |
| `llm_fallo` | error real del proveedor; **el 4xx manda sobre el nombre** y nunca reintenta | según código | grave — **crítico** si es credencial |
| `transporte_telegram` | envío: >4096 chars, `parse_mode` roto, `RetryAfter`, bot bloqueado | según variante | aviso/grave/**crítico** |
| `datos_ausentes` | señal EXPLÍCITA (`raise DatosAusentes`) | no | aviso |
| `bug` | **residual honesto**: defecto nuestro | no | grave |

## Alternativas consideradas y por qué se descartan

- **Solo el handler global, sin taxonomía.** Cierra el silencio pero no la segunda mitad del
  encargo: sin clase no hay insight, solo un contador.
- **Columna JSONB en `query_logs` (sin esquema nuevo)** — la que el encargo pide declarar. Se
  descarta porque `rag_trace` ya demostró el coste: validador cerrado y `CHECK` que mantener,
  agrupar por clave JSON no usa índice, y **faltó en producción meses sin que nadie lo notara**
  (s301). Además un error puede no tener consulta (`/start`, callback, job).
- **Los campos en el `response` TEXT** (hoy, `Tipo@etapa`): parsear substrings. Frágil.
- **`bot_errors` con `telegram_user_id` y el texto de la consulta.** Duplicaría el dato personal
  en un contenedor con reglas propias: quinta política `rgpd_retencion_ventana`, cambio en
  `rgpd_retencion_pasada` y un paso más en el runbook. El encargo admite «la consulta **o su
  id**»: con la FK se obtiene lo mismo heredando la gobernanza que ya existe.
- **Flag para el handler global.** Lo que sustituye es el silencio. Sí llevan flag sus efectos:
  `BOT_ERROR_REPLY` (nuevo, **default on**) y `BOT_ERROR_LOGGING` (default off, `on` en Railway).
- **Refactorizar los 24 `except`.** Riesgo alto, beneficio bajo.

## Gaps y riesgos declarados

1. **`mensaje_corto` es `str(exc)` redactado, no garantizado.** Se quitan URLs, tokens, cadenas
   ≥20 chars y números ≥7 dígitos, y se descarta entero si reproduce el texto del técnico (ya en
   sus dos formas, cruda y normalizada, tras r37); aun así una excepción puede citarlo de un modo
   que la redacción no reconozca. s286 prohibió `str(exc)` por esto. `BOT_ERROR_LOGGING=off` lo
   apaga sin deploy. **Sigue siendo el riesgo nº 1.**
2. **Head-of-line con Supabase caído (r37, claim RETIRADA).** El registro va a `to_thread` pero
   se **espera** igual, y PTB procesa los updates de uno en uno: los demás técnicos hacen cola
   detrás de hasta 3 timeouts REST. `to_thread` solo evita bloquear el bucle. El arreglo real
   —espera acotada o `concurrent_updates`— es serving y pide su propio dúo: no se cuela aquí.
3. **Sin la 015 aplicada no hay insights ricos** — solo el registro degradado de s286.
   `log_bot_error` detecta la tabla ausente y degrada. La ESCRITURA no se ha probado contra
   Supabase real: solo con dobles.
4. **`datos_ausentes` tiene 0 call sites**: costura nominal. Deducirla de un `KeyError`
   disfrazaría defectos nuestros de huecos de corpus.
5. **`_process_query` deja DOS líneas de log** (la histórica, pinada por un test RGPD, y la
   estructurada); ninguna lleva la consulta.
6. **`route` de las filas de error sigue igual** (default `'rag'`; el `CHECK` no admite
   `'error'`). Wart heredado: cambiarlo mueve métricas de canal.
7. **`has_consent` es fail-closed**: en una caída de Supabase el error se cuenta pero la
   consulta no, así que un pico traerá menos preguntas.
8. **`_handle_catalog` sigue sin insight** (residual de s286, menor porque `handle_voice` entró).
9. **Sin smoke contra Telegram.**

## Por qué es BP, estructural y escalable

**BP**: la red global es el mecanismo que la propia librería expone
(`Application.add_error_handler`); clasificar-antes-de-decidir con clase + severidad +
`reintentable` es el patrón estándar; el residual va a `bug`, no a un cajón cómodo.

**Estructural**: ataca la causa (no había punto único ni vocabulario de fallos), no el síntoma.
Queda **un** sitio que decide qué se dice, qué se guarda y con qué severidad, y **un**
vocabulario compartido por código, base y script, con test que los compara. El dato personal se
queda donde ya está gobernado.

**Escalable a 30+ fabricantes**: el eje del error es la CAUSA TÉCNICA, ortogonal al fabricante —
la taxonomía no crece con el catálogo (0 filas por fabricante). Y el top-5 de preguntas que
fallan más la cola por `modulo:línea` convierten el piloto en una lista priorizada.
