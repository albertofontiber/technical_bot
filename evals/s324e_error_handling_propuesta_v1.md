# s324e — Manejo de errores del bot: red de seguridad + insights (propuesta v1)

> **Estado: CABLEADO y SIN APLICAR.** Nada tocado en Railway ni en Supabase; la migración
> `015_bot_errores.sql` está escrita y **no ejecutada** (comprobado: la tabla no existe).
> Pendiente: revisión de Alberto + **dúo adversarial** (serving = zona de dolor).
>
> **Verificado**: suite completa en verde y smoke **de solo lectura** del script contra Supabase
> real — detecta la tabla ausente, lee las heredadas (0) y sale 0. Ese smoke cazó un fallo real:
> el informe reventaba al imprimir un emoji en consola cp1252.

## El fallo que se cierra

Verificado hoy por grep: **24 `except Exception` dispersos y CERO `add_error_handler`**. Fuera
de dos puntos (`accept_command`, `_process_query`), una excepción no manejada deja al técnico
en **silencio**: escribe y no pasa nada. Y donde sí hay mensaje, es **uno solo para todo**: un
timeout transitorio (reintentar funciona) y un `KeyError` determinista (reintentar falla
siempre igual) se cuentan con la misma frase. Con Directores Generales en el piloto, el
silencio se lee como «esto no funciona».

## Recomendación

Cuatro piezas, cada una en su sitio:

1. **`src/bot/error_taxonomy.py` — hoja PURA** (sin I/O, sin entorno, **sin importar ningún
   SDK**). Clasifica por CAUSA y devuelve una `Decision`: clase, severidad, `reintentable`,
   mensaje al técnico, si lleva código de incidencia y si es siquiera *entregable*.
   Clasificación **nominal** (nombres del MRO) y no `isinstance`: importar
   telegram/anthropic/openai en una hoja que carga al arrancar el worker significa que un SDK
   que reestructure sus excepciones **apaga el bot en el import** — justo el mecanismo que
   existe contra el silencio. El agujero de lo nominal (un rename) lo cierra un test que
   construye excepciones **reales**: si `pip install -U` mueve un nombre, cae la suite.
2. **Red de seguridad global**: `app.add_error_handler(error_handler)`, registrado **sin
   gatear** — una red detrás de un flag no es una red. `_reportar_error(...)` es el **punto
   único** que clasifica, avisa y registra; los dos puntos que ya respondían pasan por él. Los
   **24 `except` locales no se tocan**: ya responden, y convertirlos sería una regresión.
3. **Persistencia en dos piezas, por gobernanza**: la **consulta** (dato personal) sigue yendo a
   `query_logs` con `source='error'` — ya está en la matriz de retención, ya cascadea y ya la
   excluyen las vistas de salud; el **diagnóstico** va a `bot_errors` por FK
   `ON DELETE CASCADE`. **`bot_errors` no contiene dato personal alguno.** El registro corre en
   un **hilo** (`asyncio.to_thread`, patrón ya usado en el bot): con Supabase caído fallan
   todos los turnos, y registrar en el bucle dejaría al bot mudo para todos.
4. **`scripts/s324e_bot_errores_insights.py`**: agrega por clase / módulo:línea / día / etapa,
   saca el top-5 de preguntas que fallan y cuenta **cuántas veces el técnico se quedó sin
   aviso**.

**Taxonomía resultante** (vocabulario cerrado, idéntico en código y en el `CHECK` de la tabla —
un test lo compara):

| clase | causa | reintentar | severidad |
|---|---|---|---|
| `red_datos` | timeout/red hacia Supabase o Voyage (httpx) | **sí** | aviso |
| `llm_saturado` | 429/529 del proveedor | **sí** | aviso |
| `llm_fallo` | error real del proveedor (5xx, bad request) | no | grave — **crítico** si es credencial |
| `transporte_telegram` | envío: >4096 chars, `parse_mode` roto, `RetryAfter`, bot bloqueado | según variante | aviso/grave/**crítico** |
| `datos_ausentes` | señal EXPLÍCITA (`raise DatosAusentes`) | no | aviso |
| `bug` | **residual honesto**: defecto nuestro | no | grave |

## Alternativas consideradas y por qué se descartan

- **Solo el handler global, sin taxonomía.** Cierra el silencio pero no la segunda mitad del
  encargo: sin clase no hay insight, solo un contador.
- **Columna JSONB en `query_logs` (sin esquema nuevo)** — la alternativa que el encargo pide
  declarar. Se descarta porque `rag_trace` ya demostró el coste: validador cerrado + `CHECK` de
  tamaño que mantener, agrupar por clave JSON no usa índice, y **la columna faltó en producción
  meses sin que nadie lo notara** (s301). Además un error puede no tener consulta (`/start`,
  callback, job): obligaría a inventar una fila de consulta que no existió.
- **Meter los campos en el `response` TEXT** (lo de hoy, `Tipo@etapa`): cinco campos en una
  cadena ⇒ el script parsearía substrings. Frágil y no indexable.
- **`bot_errors` con `telegram_user_id` y el texto de la consulta.** Sería un **contenedor de
  dato personal NUEVO**: quinta política `rgpd_retencion_ventana`, cambio en
  `rgpd_retencion_pasada` y un paso más en el runbook de supresión. El encargo ya admite «la
  consulta **o su id**»: con la FK se obtiene lo mismo y **cero frente RGPD nuevo**.
- **Flag para el handler global.** Descartado: lo que sustituye es el silencio. Los que sí
  llevan flag son sus dos efectos — `BOT_ERROR_REPLY` (nuevo, **default on**) y
  `BOT_ERROR_LOGGING` (existente, default off, ya `on` en Railway).
- **Refactorizar los 24 `except`.** Riesgo alto, beneficio bajo.

## Gaps y riesgos declarados

1. **`mensaje_corto` es `str(exc)` redactado, no garantizado.** Se quitan URLs, tokens
   `123456789:AA…`, cadenas ≥20 chars y números ≥7 dígitos, y se descarta entero si reproduce la
   consulta; aun así una excepción puede citar texto del técnico de forma que la redacción no
   reconozca. s286 prohibió `str(exc)` justo por esto. Se acepta por valor diagnóstico y porque
   `BOT_ERROR_LOGGING=off` lo apaga sin deploy. **El dúo debe atacar esto primero.**
2. **`datos_ausentes` tiene 0 call sites hoy**: costura nominal, no clase viva. Deducirla de un
   `KeyError` sería peor — disfrazaría defectos nuestros de huecos de corpus.
3. **Sin la 015 aplicada no hay insights ricos** — solo el registro degradado de s286.
   `log_bot_error` detecta la tabla ausente (PGRST205/404), avisa **una** vez y degrada. La
   escritura no se ha probado contra Supabase real: solo con dobles.
4. **`_process_query` deja ahora DOS líneas de log** (la histórica, pinada por un test RGPD, y
   la estructurada); ninguna lleva la consulta.
5. **`route` de las filas de error sigue como estaba** (default `'rag'`; el `CHECK` no admite
   `'error'`). Wart heredado: cambiarlo mueve métricas de canal, es decisión aparte.
6. **`has_consent` es fail-closed**: en una caída de Supabase el error se cuenta pero la
   consulta no. Correcto, y significa que un pico de errores traerá menos preguntas.
7. **`_handle_catalog` sigue sin insight**: responde bien pero no registra (residual de s286,
   ahora menor porque `handle_voice` sí entró). Fuera por la regla de los otros 23 `except`.
8. **Sin smoke contra Telegram.**

## Por qué es BP, estructural y escalable

**BP**: la red global es el mecanismo que la propia librería expone
(`Application.add_error_handler`); clasificar-antes-de-decidir con clase + severidad +
`reintentable` es el patrón estándar; el residual va a `bug`, no a un cajón cómodo.

**Estructural**: ataca la causa (no había punto único de manejo ni vocabulario de fallos), no
el síntoma. Queda **un** sitio que decide qué se dice, qué se guarda y con qué severidad, y
**un** vocabulario compartido por código, base y script, con test que los compara. El diseño de
datos elige gobernanza antes que comodidad: el dato personal se queda donde ya está gobernado.

**Escalable a 30+ fabricantes**: el eje del error es la CAUSA TÉCNICA, ortogonal al fabricante —
la taxonomía no crece con el catálogo (0 filas por fabricante). Y el top-5 de preguntas que
fallan más la cola por `modulo:línea` convierten el piloto en una lista priorizada.
