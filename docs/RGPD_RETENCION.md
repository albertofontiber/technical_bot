# Matriz de retención RGPD — tablas de producción del Technical Bot

> **Qué es este documento.** La respuesta a «qué dato personal guardamos, dónde, para qué,
> cuánto tiempo y qué lo borra», para las tablas **que están hoy en producción**.
>
> **Ámbito — no confundir con el otro doc.** `docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md` es la
> matriz del schema **futuro `convo`** (multi-turn durable), sigue SIN FIRMAR con 20 celdas
> `[DECIDIR]`, y su firma exige validación legal. Este documento **NO la sustituye y NO
> desbloquea `convo`**: cubre tablas distintas.
>
> **Decisiones tomadas por Alberto (2 ago 2026)**, marcadas ⬤. Lo que no está decidido se
> declara como pendiente, no se inventa.
>
> **Aviso**: este documento lo redacta el asistente técnico, no un asesor legal. Los plazos y
> la base jurídica los valida quien lleve cumplimiento en Fontiber.

## Principio rector: DISOCIAR, no borrar ⬤

El valor del histórico para el proyecto está en el **contenido** (la pregunta, la respuesta y
la explicación de un fallo son material de evaluación y candidatos a gold), **no en quién
preguntó**. Por eso el plazo no termina en un `DELETE` sino retirando el identificador.

**Con el nombre correcto: esto es SEUDONIMIZACIÓN, no anonimización** (Considerando 26 RGPD).
Dos razones, ambas declaradas y no disimuladas:

1. Mientras existan otras columnas que permitan re-vincular la fila con la persona, el dato
   sigue siendo personal (ver «lo que hoy NO funciona»).
2. Aun retirando **todos** los identificadores estructurados, el texto libre escrito por un
   técnico puede contener un nombre, una empresa, una obra o un teléfono. Llamar «anónimo» a
   eso sin una evaluación de reidentificación sería declarar de más.

## Lo que hoy NO funciona (verificado contra la DB real, 3 ago 2026)

**La retención no es ejecutable todavía.** Dos bloqueos independientes:

| # | Bloqueo | Evidencia |
|---|---|---|
| 1 | **No existe todavía el rol que puede escribir.** El hardening de julio dejó a `service_role` con solo SELECT+INSERT, a propósito — y **no se va a tocar**: es la identidad del bot. El privilegio vive en un rol dedicado `rgpd_retencion` que aún no está creado | `PATCH → 403` con la clave de servicio; `SET LOCAL ROLE rgpd_retencion` → «role does not exist» |
| 2 | Aunque escribiera, **no bastaría**: las hijas conservan el identificador y se unen por `query_log_id` | `answer_feedback.telegram_user_id BIGINT NOT NULL`; `answer_messages.telegram_chat_id BIGINT NOT NULL` (== user_id en chat privado) |

El `ON DELETE CASCADE` de esas FK **solo actúa al BORRAR** la fila padre. Una retención que
ACTUALIZA no dispara ninguna cascada — por eso la columna «qué lo borra» de abajo distingue
la supresión a petición (sí cascadea) del vencimiento del plazo (no cascadea).

> El diseño completo está en
> `supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql`: un rol
> dedicado `rgpd_retencion` (NOLOGIN, NOINHERIT, **NOBYPASSRLS**) con privilegios de
> COLUMNA y políticas RLS que acotan lo que puede tocar a `created_at < now() - interval
> '24 months'` — **la ventana de retención pasa a ser un invariante de la base** para quien
> actúa como ese rol (NO ata a `postgres`, que es owner y `BYPASSRLS`, ni a `service_role`;
> por eso el job comprueba `current_user` tras asumirlo). **`service_role` no cambia en absoluto**;
> hay postcondición que lo ancla. **Sin aplicar**: pendiente de revisar y ejecutar.
> `scripts/rgpd_retencion.py` lo comprueba en cada ejecución y sale con código 2.

## La matriz

| Dato | Dónde vive | Para qué | Retención ⬤ | Supresión a petición | Al vencer el plazo |
|---|---|---|---|---|---|
| Pregunta, respuesta, transcripción de voz | `query_logs` | Diagnóstico, calibración con preguntas reales | **24 meses identificado → disociado indefinido** | `DELETE` (cascadea a las hijas) | Se retira el id — **hoy bloqueado (1)** |
| ID de Telegram del autor | `query_logs.telegram_user_id` | Vincular consulta ↔ persona | **24 meses** | `DELETE` | → NULL — **hoy bloqueado (1)** |
| Voto 👍/👎 y su motivo | `answer_feedback` | Señal de calidad | Sigue a su consulta | **CASCADE** desde `query_logs` | — |
| **ID del votante** | `answer_feedback.telegram_user_id` | Un voto por persona y consulta | 24 meses | ⚠️ CASCADE **solo si votó su propia consulta** — ver nota | **NO se retira hoy** — es `NOT NULL`; exige `DROP NOT NULL` (propuesta §2) |
| Explicación en texto libre del 👎 | `answer_feedback.comment` | Convertir el 👎 en caso diagnosticable | Sigue a su consulta | CASCADE | Se conserva; puede contener datos personales en prosa |
| Ancla mensaje ↔ consulta | `answer_messages` (`telegram_chat_id`, `telegram_message_id`) | Atribuir una respuesta de Telegram a su consulta | Sigue a su consulta | CASCADE | **Se BORRA** — mapeo operativo sin valor analítico a 24 meses (propuesta §3) |
| Feedback libre del canal antiguo + **copias** de pregunta/respuesta | `feedback` | Histórico | Igual que `query_logs` | ⚠️ **NO CASCADEA** (sin FK): hay que borrarla a mano | → NULL — **hoy bloqueado (1)** |
| Aceptación de términos, `display_name` | `user_consent` | Prueba del consentimiento | ⚠️ **hoy indefinido** — ver pendiente 1 | Revocación lógica (`revoked_at`) **no borra nada** | **[DECIDIR]** |
| **Exports a disco** (`display_name`, `telegram_user_id`, pregunta, transcripción, respuesta) | `data/eval/logs_export_*.csv\|xlsx` vía `scripts/review_logs.py` | Curar eval orgánico | ⚠️ **ninguna** — fuera de Supabase e **inalcanzable** para el job | Borrado manual del fichero | Nada |
| **Extracto de recibos en git** (`query`, `response`, `created_at` de 3 consultas) | `evals/s272_live_receipts_v1.json` + copia en `tests/fixtures/` | Recibos de una ventana de flag | ⚠️ **ninguna** — vive en el HISTORIAL DE GIT, fuera del alcance del job | Reescritura de historia (costosa) | Nada |
| **Audio original de las notas de voz** | **NO SE ALMACENA** por nosotros | — | — | — | Temporal borrado en un `finally` tras transcribir |

### Nota sobre el votante: la supresión a petición NO le alcanza del todo

El voto se atribuye a `callback.from_user.id` **sin filtrar chat privado**
(`telegram_bot.py`), así que en un grupo la persona B puede votar la consulta de A — y de
hecho el `UNIQUE (query_log_id, telegram_user_id)` existe justo porque puede haber varios
votantes por consulta. Consecuencia: `DELETE FROM query_logs WHERE telegram_user_id = X`
**no alcanza los votos que X emitió sobre consultas ajenas**, porque cascadea desde la
consulta, no desde el votante. La supresión a petición debe llevar además:
`DELETE FROM answer_feedback WHERE telegram_user_id = X`. Hoy el bot se usa 1:1, así que la
exposición es teórica — pero el procedimiento estaba incompleto y ahora no lo está.

### Nota sobre los recibos versionados en git

`evals/s272_live_receipts_v1.json` contiene pregunta, respuesta y fecha de 3 consultas reales
extraídas de `query_logs`. **Revisado: no lleva identificadores** (ni `telegram_user_id` ni
`display_name`) y las 3 preguntas las disparó Alberto, no un tercero. No es equiparable a los
exports de `review_logs.py`. Pero deja una regla que sí importa y que hasta ahora no estaba
escrita: **todo extracto de contenido de producción que se versione en git debe revisarse
columna a columna y declararse aquí** — git no tiene plazo de retención y una supresión a
petición no lo alcanza.

### Nota sobre `user_consent`

`log_user_consent` hace *upsert* con `merge-duplicates` sobre la PK del usuario ⇒ **solo
sobrevive la última versión aceptada**. Decir «prueba del consentimiento» sin más declaraba de
más: no hay traza de que alguien aceptase la v2 o la v3. Si esa traza importa, la tabla
necesita ser append-only por (usuario, versión). **[DECIDIR]**

## Encargados de tratamiento y ubicación

| Proveedor | Qué hace | Dónde | DPA |
|---|---|---|---|
| **Railway** | Ejecuta el bot; sus **logs de proceso** pueden recoger metadatos de error (ya NO la pregunta: s295 quitó el texto del log) | Fuera de la UE | ⬤ asumido — retención de logs no controlada por nosotros |
| **Telegram** | **Transporta** la conversación entera (texto, audio, respuestas) y la retiene según su propia política | Fuera de la UE | ⬤ asumido — **no controlamos su retención** |
| **Supabase** | Almacena todo lo anterior | **`eu-north-1` (Estocolmo, UE)** — verificado vía API | ⬤ asumido firmado |
| **Anthropic** | Genera la respuesta (recibe la pregunta y los fragmentos) | Fuera de la UE | ⬤ asumido firmado — **transferencia pendiente de mecanismo** |
| **Voyage AI** | **Embebe la pregunta** para buscar en `chunks_v2` — recibe el texto de CADA consulta | Fuera de la UE | ⬤ asumido firmado — **transferencia pendiente**; hallazgo del dúo: faltaba en esta tabla y en los términos |
| **OpenAI** | Transcribe el audio (Whisper) · juez de evaluación | Fuera de la UE | ⬤ asumido firmado — **transferencia pendiente de mecanismo** |

> **Asunción declarada, NO hecho verificado**: Alberto pidió asumir los DPA firmados para no
> bloquear el trabajo. Queda escrito aquí como asunción para que nadie lo lea como comprobado.
> Acción pendiente: aceptar el DPA en la consola de cada proveedor, revisar si ofrecen
> retención cero para API, y documentar el mecanismo de transferencia de los que procesan
> fuera de la UE.

## Derechos del interesado

- **Canal** ⬤: `info@fontiber.com` (declarado en los términos que el técnico acepta).
- **Supresión**: hoy es **manual** y está documentada en `docs/DG_DEPLOYMENT.md`:
  `UPDATE user_consent SET revoked_at = NOW() …` + `DELETE FROM query_logs WHERE
  telegram_user_id = X` (la cascada se lleva votos, explicaciones y anclas de SUS consultas)
  + `DELETE FROM answer_feedback WHERE telegram_user_id = X` (los votos que emitió sobre
  consultas AJENAS, que la cascada no alcanza) + `DELETE FROM feedback WHERE telegram_user_id = X`. **No alcanza los exports a disco**: hay que borrarlos
  aparte.
- **Acceso y portabilidad**: no implementados. Hoy se atienden a mano.

## Pendiente (con dueño)

1. **Aplicar la propuesta del rol de retención** —
   `supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql` (enfoque
   aprobado por Alberto el 3-ago; queda ejecutarla). Sin ella la retención no es ejecutable.
   `user_consent` queda FUERA y necesita decisión aparte.
2. **`feedback` no cascadea** (sin FK a `query_logs`): un borrado a petición debe acordarse de
   ella a mano. → *Propuesto: añadir la FK con CASCADE. Decisión de Alberto.*
3. **Exports a disco**: `scripts/review_logs.py` deposita datos personales fuera de Supabase
   sin plazo. → *Propuesto: plazo corto + borrado, o excluir las columnas identificadoras.*
4. **Programar el job**: hoy es de EJECUCIÓN MANUAL por diseño. Programarlo exigiría una
   credencial durable con membresía en `rgpd_retencion`, y el rol solo se concede a
   `postgres` ⇒ un scheduler guardaría un `DATABASE_URL` de operador, **más potente** que el
   `service_role` que se evitó tocar. Requiere antes un rol runner LOGIN acotado. → *Alberto.*
5. **Autoservicio `/borrar`**: hoy el técnico tiene que escribir a un correo. → *Propuesto, no
   construido.*
6. **Mecanismo de transferencia** para Telegram, Anthropic y OpenAI. → *Alberto / asesor legal.*

## Estado real hoy (verificado 3 ago 2026)

71 consultas desde el 7 de abril, 1 usuario con consentimiento activo, 1 feedback libre, 3
votos, 4 anclas. **0 filas fuera de plazo** (la más antigua es de abril de 2026 ⇒ vence en
2028). La exposición **hoy** es trivial; la matriz existe para que deje de serlo de forma
controlada cuando entren técnicos, no para el estado actual — y para que el plazo llegue con
la maquinaria ya construida y probada, no improvisada.
