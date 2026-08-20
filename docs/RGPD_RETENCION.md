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

## Base jurídica — [DECIDIR], y es el lever que más ahorra a futuro

**Hoy el sistema OPERA como si la base fuese el CONSENTIMIENTO**: el gate `/accept` no permite
usar el bot sin aceptar, y así se declara ahora al técnico. Conviene la precisión: ese gate
prueba una acción técnica, **no resuelve la validez jurídica de la base** — que es justo lo que
queda pendiente de decidir.

**Por qué es frágil.** El consentimiento debe ser *libre*, y para una herramienta de trabajo que
la empresa pone a disposición del técnico hay desequilibrio: quien no puede negarse sin coste
laboral no consiente libremente. Para un caso así lo habitual es **interés legítimo** o
**ejecución de contrato**, con un aviso de información en lugar de una casilla.

**Qué cambia en la práctica.** Con consentimiento, un cambio material del aviso obliga a
**re-aceptar** (es lo que hace `TERMS_VERSION`). Con interés legítimo o contrato, el cambio se
**informa** — lo que reduce la fricción, aunque no la elimina: un cambio sustancial de finalidad
sigue exigiendo aviso y puede exigir rehacer la ponderación.
Es decir: **la churn de re-aceptaciones es consecuencia de la base elegida**, no un problema de
redacción — y no se arregla escribiendo términos más largos ni pre-declarando propósitos
futuros (un consentimiento tiene que ser específico; una cláusula que cubra «mejoras futuras»
no autoriza nada y solo hace el aviso más vago hoy).

**Recomendación** (asistente técnico, NO asesor legal): pasar a **interés legítimo** para el uso
del bot como herramienta de trabajo, conservando el **consentimiento explícito** solo para lo
que de verdad lo requiera (p. ej. memoria durable opt-in). Requiere análisis de ponderación
documentado. **Decisión de Alberto con validación legal**; la plantilla de `convo`
(`RGPD_LIFECYCLE_MATRIX_TEMPLATE.md`) ya lo tenía como `[DECIDIR]` y aquí faltaba.

**Momento**: hoy hay UNA fila de consentimiento, así que la fricción es de una persona. El
momento de decidirlo es **antes de que entren técnicos**, no ahora.

## El seudónimo estable: una sola pieza para agrupar y para desvincular ⬤

**Decisión de Alberto (4-ago).** El plazo no pone el identificador a NULL: lo sustituye por un
**código aleatorio, estable por persona**. Motivo, en sus palabras: no quiere perder el corpus de
un técnico bueno que se vaya. Con NULL quedarían 200 preguntas excelentes sueltas, sin poder
saber que son de la misma persona; con un código estable, el corpus sobrevive agrupado y el
vínculo con la persona no.

**Y resuelve a la vez el problema de los exports.** Un seudónimo solo para la retención y otro
solo para los exports darían dos numeraciones que no casan. Una sola pieza, usada desde el
principio:

| | |
|---|---|
| Alta | Cada técnico recibe un código aleatorio la primera vez que usa el bot |
| Correspondencia | Una tabla pequeña `persona_seudonimo` (código ↔ `telegram_user_id`) |
| Exports | Llevan **siempre el código, nunca el identificador real**. Precisión: el identificador sí se LEE al proceso que genera el fichero; lo garantizado es que **no se escribe al fichero** |
| Operativa | La base conserva el identificador real mientras haga falta (consentimiento, peticiones) |
| A los 24 meses | Se sustituye el identificador por el código en los registros **y se borra la fila de correspondencia** — ese borrado ES el punto de no retorno |

**Contrapartida declarada**: `persona_seudonimo` **es dato personal mientras existe** (vincula
código y persona). Entra en la matriz, en el procedimiento de supresión a petición y en el
alcance del job. No se disimula: se ha cambiado un riesgo difuso (identificador esparcido por
exports) por uno concentrado y gobernado (una tabla, un borrado).

**Alternativa descartada**: derivar el código del identificador con una función y una clave
secreta (HMAC). Evita la tabla, pero los identificadores de Telegram son un espacio pequeño: con
la clave se pueden recorrer todos y deshacer el seudónimo. Sería irreversible solo si se destruye
la clave — y entonces vuelve el problema de no poder emitir el mismo código otra vez.

### Límites del seudónimo, declarados

**No es «el mismo código para siempre».** Lo es mientras viva la correspondencia. El vínculo
se destruye en cuanto esa persona no tiene NINGUNA fila identificada — incluido quien aceptó y
nunca preguntó, cuyo código no agrupa nada y por tanto no se pierde nada al borrarlo. Si a alguien
se le destruye el vínculo (no le quedaba nada identificado) y luego vuelve, recibe un código
NUEVO y su histórico queda en dos bloques. **No es un fallo: es la irreversibilidad
funcionando** — un vínculo destruido no se puede resucitar, esa es justo la garantía. Pero
conviene decirlo, porque la prosa «estable siempre» sugería lo contrario.

**~~El append-only no conservaba la traza de una revocación~~ — RESUELTO y APLICADO (5-ago)**. El estado
(`user_consent`) sigue siendo lo que `has_consent` consulta; la EVIDENCIA vive en
`consent_events`, un libro de solo inserción para el bot donde cada aceptación y cada
revocación es una fila nueva con su fecha. Dos límites declarados: (a) el backfill es
**reconstrucción** — el upsert antiguo destruyó el histórico v1..v6 y el libro arranca con lo
único que sobrevivió, sin fingir más; (b) el evento se escribe fail-open tras el estado —
bloquear al técnico porque falló el libro sería desproporcionado— así que una divergencia
puntual es posible **en las dos direcciones**: por omisión (evento que no llegó a escribirse)
y, en la revocación manual, por falso positivo si las dos sentencias no van en una transacción
— por eso el runbook la exige en `BEGIN…COMMIT`. Se detectaría comparando ambas tablas; no hay
reconciliación automática.

**El feedback espontáneo puede perderse si la consulta se borra entre medias.** Al añadir el
enlace con cascada, un `feedback` cuya consulta padre desaparezca justo antes de escribirlo
falla entero (antes se guardaba suelto). Ventana pequeña y el caso es raro; se declara.

**La destrucción del vínculo tiene una carrera declarada (s299).** Una consulta que se
confirme en el instante exacto de la pasada mensual puede llegar después del snapshot del
oráculo y el vínculo destruirse igual. La consecuencia NO es una re-identificación: es el
mismo «corpus en dos códigos» del que vuelve tras la destrucción (límite de arriba), y la
emisión de códigos de la siguiente pasada lo recoge. A la escala actual es ~0; si entran
técnicos en volumen, la pasada debe subir a `SERIALIZABLE` con retry (TECH_DEBT).

## Principio rector: DISOCIAR, no borrar ⬤

El valor del histórico para el proyecto está en el **contenido** (la pregunta, la respuesta y
la explicación de un fallo son material de evaluación y candidatos a gold), **no en quién
preguntó**. Por eso el plazo no termina en un `DELETE` sino retirando el identificador.

**Con el nombre correcto: esto es SEUDONIMIZACIÓN, no anonimización** (Considerando 26 RGPD).
Dos razones, ambas declaradas y no disimuladas:

1. Mientras existan otras columnas que permitan re-vincular la fila con la persona, el dato
   sigue siendo personal (ver el estado de despliegue, más abajo).
2. Aun retirando **todos** los identificadores estructurados, el texto libre escrito por un
   técnico puede contener un nombre, una empresa, una obra o un teléfono. Llamar «anónimo» a
   eso sin una evaluación de reidentificación sería declarar de más.

## Estado de despliegue: EJECUTABLE (cola aplicada el 5 ago 2026)

**Alberto aplicó las tres migraciones** (s295 → s296 → s297) en el SQL Editor de Supabase y
ejecutó el dry-run del job, que asumió el rol y recorrió las cinco tablas con 0 candidatas.
Verificado además contra el catálogo de producción: rol `rgpd_retencion` con sus atributos, 4
políticas de ventana + 3 del vínculo, trigger anti-reidentificación armado, seudónimo emitido
por el backfill, 1 evento en el libro (origen `backfill`), `answer_feedback.telegram_user_id`
nullable, y los privilegios de columna exactos (la marca NO insertable por el bot; el voto y
el feedback, sí).

Los dos bloqueos históricos (el rol no existía; las hijas conservaban el identificador y el
CASCADE solo actúa al borrar) quedan documentados en DEC-177/178 como motivo del diseño, no
aquí como estado.

**Encima, s299 — APLICADA (5-ago, misma tarde; PR #210 mergeada):** la pasada es UNA
función en la base (`public.rgpd_retencion_pasada`, `SET role` en el encabezado + cinturón
de `current_user`), pg_cron la ejecuta el día 1 de cada mes (04:30 UTC) sin que ninguna
credencial salga de la base, y cada pasada confirmada deja recibo en `rgpd_recibos`.
Verificado contra el catálogo tras aplicar: job ACTIVO a nombre de `postgres` con horario y
comando exactos + dry-run del driver con exit 0 (2 vínculos sin datos en ninguna tabla
caerán en la primera pasada real — caso benigno declarado). **Primer recibo esperado:
1-sep, 04:30 UTC.**
`scripts/rgpd_retencion.py` queda como driver manual de esa misma función (dry-run = la
misma pasada + ROLLBACK, recibo incluido). Gap declarado: el contenedor de CI no trae
pg_cron ⇒ la RAMA de programación no se ejerce en CI (la función sí, entera); en
producción la postcondición exige el job si pg_cron está disponible — que lo está
(verificado, 1.6.4).

**Además, s299 CIERRA un hallazgo del dúo VIVO en producción**: `rgpd_quedan_identificados`
(s296) nació ejecutable por `anon`/`authenticated`/`service_role` — los default privileges
de Supabase conceden EXECUTE sobre toda función nueva de `public`, y s296 solo revocó
PUBLIC. Es un **oráculo de pertenencia** («¿este telegram_user_id tiene datos?», SECURITY
DEFINER) alcanzable por PostgREST RPC con la clave anónima (verificado contra el catálogo
vivo el 5-ago). **CERRADO ese mismo día al aplicar s299** — re-verificado contra el
catálogo: los tres roles sin EXECUTE. La misma clase se corrige de raíz: el
fixture de CI ahora reproduce los default privileges de FUNCIONES, y el punto de no
retorno aprende la 4ª tabla (`answer_messages` — un ancla reciente de una consulta
vencida mantenía la cadena chat_id → consulta → seudónimo tras destruir el vínculo).

Nota operativa que sigue vigente: el `ON DELETE CASCADE` actúa al BORRAR la fila padre, por
eso la matriz distingue la supresión a petición (cascadea) del vencimiento del plazo (el job
estampa el seudónimo, no borra).

> El diseño completo está en
> `supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql`: un rol
> dedicado `rgpd_retencion` (NOLOGIN, NOINHERIT, **NOBYPASSRLS**) con privilegios de
> COLUMNA y políticas RLS que acotan lo que puede tocar a `created_at < now() - interval
> '24 months'` — **la ventana de retención pasa a ser un invariante de la base** para quien
> actúa como ese rol (NO ata a `postgres`, que es owner y `BYPASSRLS`, ni a `service_role`;
> por eso el job comprueba `current_user` tras asumirlo). **`service_role` no cambia en absoluto**;
> hay postcondición que lo ancla. **APLICADA en producción (5 ago 2026)**.
> `scripts/rgpd_retencion.py` comprueba el estado en cada ejecución: exit 0 con la cola
> aplicada, exit 2 con diagnóstico si en algún entorno faltara.

> **Y una segunda migración encima** (s296):
> `supabase/migration_proposals/20260804120000_s296_seudonimo_y_calidad_v1.sql` — el
> seudónimo estable, `user_consent` append-only, el enlace de `feedback` y la marca de
> utilidad. **APLICADA (5 ago 2026)**, después de la anterior; y encima la tercera,
> s297 (libro de eventos), también aplicada. La cola entera se verifica junta contra un
> PostgreSQL real en CI en cada cambio.

### Dos fallos que solo aparecieron ejecutando (s296)

Se dejan escritos porque son la misma clase y conviene reconocerla:

1. **Quien no tuviera código quedaba FUERA de la retención, en silencio.** La emisión en
   `/accept` es fail-open, así que puede faltar; sin código, el `UPDATE ... FROM` no casaba
   sus filas — conservaban el identificador para siempre y el recibo decía «0 tocadas».
   *Arreglo*: el job emite el que falte antes de estampar nada.
2. **El borrado del vínculo no veía las filas recientes.** La condición «solo si no le queda
   nada identificado» se consultaba desde el propio rol, cuya política solo le enseña filas
   vencidas: las recientes «no existían» y destruía el vínculo antes de tiempo, lo que
   partiría el corpus del técnico en dos códigos. *Arreglo*: una función acotada
   (`rgpd_quedan_identificados`) que responde solo esa pregunta con visibilidad completa.

Los dos se leen correctos en el código. La diferencia la marca ejecutarlos.

## La matriz

| Dato | Dónde vive | Para qué | Retención ⬤ | Supresión a petición | Al vencer el plazo |
|---|---|---|---|---|---|
| Pregunta, respuesta, transcripción de voz | `query_logs` | Diagnóstico, calibración con preguntas reales | **24 meses identificado → disociado indefinido** | `DELETE` (cascadea a las hijas) | El job estampa el **seudónimo** y retira el id — **vivo: manual + mensual por pg_cron** (s299 aplicada el 5-ago; primer recibo 1-sep) |
| ID de Telegram del autor | `query_logs.telegram_user_id` | Vincular consulta ↔ persona | **24 meses** | `DELETE` | → **seudónimo estable** + retirada del id (aplicado s295/s296) |
| Voto 👍/👎 y su motivo | `answer_feedback` | Señal de calidad | Sigue a su consulta | **CASCADE** desde `query_logs` | — |
| **ID del votante** | `answer_feedback.telegram_user_id` | Un voto por persona y consulta | 24 meses | ⚠️ CASCADE **solo si votó su propia consulta** — ver nota | → seudónimo + retirada del id (el `DROP NOT NULL` se aplicó en s295) |
| Explicación en texto libre del 👎 | `answer_feedback.comment` | Convertir el 👎 en caso diagnosticable | Sigue a su consulta | CASCADE | Se conserva; puede contener datos personales en prosa |
| Ancla mensaje ↔ consulta | `answer_messages` (`telegram_chat_id`, `telegram_message_id`) | Atribuir una respuesta de Telegram a su consulta | Sigue a su consulta | CASCADE | **Se BORRA** — mapeo operativo sin valor analítico a 24 meses (propuesta §3) |
| Feedback libre del canal antiguo + **copias** de pregunta/respuesta | `feedback` | Histórico | Igual que `query_logs` | **Cascadea desde s296** vía `query_log_id` — ⚠️ las filas PRE-s296 (sin enlace) hay que borrarlas a mano | → seudónimo + retirada del id (aplicado) |
| Aceptación de términos, `display_name` | `user_consent` | Prueba del consentimiento | ⚠️ **hoy indefinido** — ver pendiente 1 | Revocación lógica (`revoked_at`) **no borra nada** | **[DECIDIR]** |
| **Libro de eventos de consentimiento** (`telegram_user_id`, versión, evento, fecha) | `consent_events` (s297) | EVIDENCIA de aceptaciones y revocaciones — solo inserción para el bot | ⚠️ mismo **[DECIDIR]** que `user_consent` (es la prueba; fuera de `rgpd_quedan_identificados`, como ella) | **[DECIDIR]** con el asesor: borrar vs conservar como prueba de cumplimiento (alineado con el runbook) | **[DECIDIR]** |
| **Exports a disco** (desde s296: **seudónimo**, pregunta, transcripción, respuesta; desde s301 además `route` y el voto con su **motivo y comentario** — `tap_reason`/`tap_comment`: prosa que puede llevar datos personales, misma clase que `feedback_text`, bajo el MISMO seudónimo — SIN `display_name` ni `telegram_user_id`) | `data/eval/logs_export_*.csv\|xlsx` vía `scripts/review_logs.py` | Curar eval orgánico | ⚠️ **ninguna** — fuera de Supabase e **inalcanzable** para el job | Borrado manual del fichero (incluye la prosa del voto) | Nada |
| **Exports ANTERIORES a s296** (llevan `display_name` y `telegram_user_id`) | los ficheros ya generados | — | ⚠️ ninguna | Borrado manual — **hay que buscarlos**: el cambio no toca lo ya escrito | Nada |
| **Correspondencia código ↔ persona** | `persona_seudonimo` | Agrupar el histórico de un técnico sin identificarlo | Mientras le quede alguna fila identificada | `DELETE` (hay que incluirla) | **Se BORRA** — ese borrado ES el punto de no retorno |
| **Marca de utilidad del feedback** | `answer_feedback.utilidad` | Reconocer aportaciones valiosas (posible incentivo) | Sigue a su consulta | CASCADE | Se conserva: no identifica por sí sola |
| **Diagnóstico de un error del bot** (clase, tipo de excepción, `modulo.py:línea`, severidad, si el técnico recibió aviso, y `mensaje_corto` = `str(exc)` REDACTADO a 200 chars) | `bot_errors` (s324e — **migración 015 NO aplicada**) | Saber qué falla y dónde, para arreglarlo | Sigue a su consulta cuando la hay | CASCADE vía `query_log_id`. ⚠️ Es dato **ENLAZABLE**, no «sin dato personal» (r37): la FK permite llegar a la pregunta y al autor. Las filas SIN consulta (fallo sin texto, o autor sin consentimiento) quedan sueltas y ya no identifican a nadie | Se conserva: la tabla no lleva `telegram_user_id` ni texto propio, así que el job no tiene nada que disociar aquí y no necesita una quinta política |
| **Extracto de recibos en git** (`query`, `response`, `created_at` de 3 consultas) | `evals/s272_live_receipts_v1.json` + copia en `tests/fixtures/` | Recibos de una ventana de flag | ⚠️ **ninguna** — vive en el HISTORIAL DE GIT, fuera del alcance del job | Reescritura de historia (costosa) | Nada |
| **Recibos de las pasadas de retención** (origen, corte, conteos; ids de FILA — el conteo de vínculos destruidos va SIN ids a propósito) | `rgpd_recibos` (s299) | Evidencia de que la retención corrió (manual o pg_cron) — solo inserción, ilegible para el bot | ⚠️ Son datos **seudonimizados** mientras viva la correspondencia (uuid → fila → seudónimo → persona): solo lectura del operador; su plazo entra en el mismo **[DECIDIR]** que `user_consent` | Las filas referidas se borran por cascada; los uuid del recibo quedan apuntando a nada (inofensivo, declarado) | Nada |
| **Quién puede usar el bot** (`telegram_user_id` = identificador DIRECTO; `nota` = nombre/cargo en texto libre; `alta_por`/`revocado_por` = etiqueta del OPERADOR que decidió) | `bot_allowlist` (s324e — **016 aplicada el 17-ago-2026**) | Control de acceso del piloto por invitación: gasto, confidencialidad del corpus y no registrar consultas de quien no fue invitado | ⚠️ **SIN PLAZO — gap material abierto** (ver «PENDIENTE MATERIAL» arriba: propuesta de 12 meses, decide Alberto + abogado). Es ESTADO OPERATIVO y **no se puede disociar** (una lista de acceso con seudónimos no autoriza a nadie), así que el job mensual no la toca ni necesita una política nueva | `DELETE FROM bot_allowlist WHERE telegram_user_id = X`. ⚠️ **NO cascadea desde `query_logs`**: un borrado que solo toque `query_logs` deja a la persona en la lista. Revisar además la `nota`, que lleva su nombre escrito dentro | Nada — no hay identificador que disociar sin destruir la función de la tabla |
| **Invitaciones al piloto** (`nota` = para quién se emitió, existe aunque nunca se canjee; `canjeada_por` = identificador DIRECTO de quien abrió el enlace, que puede NO ser el destinatario si se reenvió; `token_hash` = SHA-256, **no** es dato personal y **no** es el token) | `bot_invitaciones` (s324e — **016 aplicada el 17-ago-2026**) | Emitir, auditar y anular accesos; ver si un enlace lo usó la persona prevista | **24 meses** (Alberto, 17-ago — la misma ventana que el resto de la matriz). Implementado en s330, **pendiente de aplicar** | `UPDATE bot_invitaciones SET canjeada_por = NULL, disociada_at = now() WHERE canjeada_por = X` — la marca es obligatoria (s330: sin ella el CHECK del canje rechaza la sentencia); se conserva la traza del canje sin el identificador de quien lo hizo; y revisar la `nota` | `rgpd_retencion_pasada` (mensual) |
| **Cuentas del panel web** (`usuario` = nombre de acceso, normalmente el correo o un alias — es la CLAVE de la tabla; `registro` = hash scrypt de la contraseña; `alta_por` / `revocado_por` = etiqueta del operador) | `panel_usuarios` (s324j — **019 aplicada el 19-ago-2026**) | Autenticar al administrador del panel; conservar quién dio el alta y quién revocó | **24 meses desde la revocación** — decidido por Alberto el 20-ago-2026, por CONSISTENCIA con el resto del sistema: un plazo único es más simple de cumplir y de explicar que tres. Mientras la cuenta esté ACTIVA se conserva | `DELETE` de la fila entera. ⚠️ Misma excepción que `bot_allowlist`: aquí el identificador **es la clave primaria**, así que no se puede disociar sin destruir la fila — por eso se borra en lugar de seudonimizar. Hoy la baja es LÓGICA (`activo=false`); el borrado a los 24 meses **está decidido y SIN MECANISMO** — no hay job que lo ejecute, y así se declara | Nada — no hay identificador que disociar sin destruir la función de la tabla |
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

### Nota sobre `bot_errors` y el `mensaje_corto` (s324e)

La tabla se diseñó para **no duplicar** dato personal: sin `telegram_user_id` y sin el texto de
la consulta. **Corrección tras el dúo r37**: eso NO la convierte en «tabla sin dato personal»
—como se escribió primero—, porque `query_log_id` es una FK y el script de insights la recorre
justamente para sacar la pregunta y el autor. Es **dato enlazable**, y por tanto dato personal a
efectos de tratamiento. Lo que se gana es que **hereda** la gobernanza de `query_logs` en vez de
crear un contenedor con reglas propias: (a) el procedimiento de supresión a petición la alcanza
**sin añadir un paso** (y el índice sobre la FK es lo que lo mantiene barato); (b) el job
mensual no necesita conocerla, porque aquí no hay identificador que disociar. Sobre si la
finalidad es nueva: **a juicio del asistente no lo es** —el texto sigue guardándose donde ya se
guardaba, con finalidad «diagnóstico»— pero **quien decide si eso exige tocar el aviso o
`TERMS_VERSION` es el asesor jurídico, no este documento**; el aviso v8 está redactado y
pendiente solo de esa revisión, y es ahí donde entra esta tabla.

El único campo con riesgo residual es `mensaje_corto`: es `str(exc)` **redactado** (URLs,
tokens tipo `123456789:AA…`, cadenas de ≥20 caracteres y números de ≥7 dígitos se sustituyen;
el mensaje se descarta ENTERO si reproduce la consulta) y truncado a 200 caracteres. **No es
una garantía**: una excepción puede citar texto del técnico de una forma que la redacción no
reconozca. Se acepta porque (i) es el campo con más valor diagnóstico, (ii) vive dentro de la
misma cascada que la consulta, y (iii) el flag `BOT_ERROR_LOGGING` lo apaga entero sin deploy.
La alternativa —no guardar mensaje— deja la clase y el módulo, que es bastante menos útil.

### Nota sobre el control de acceso (s324e) — la tabla que NO cascadea

`bot_allowlist` y `bot_invitaciones` son las dos primeras tablas con dato personal que
**no cuelgan de `query_logs`**, y eso cambia el runbook: hasta ahora «suprimir» era borrar
la consulta y dejar que la cascada hiciera el resto. Aquí no hay cascada que valga —
la allowlist existe justo para responder «¿este id puede entrar?» ANTES de que haya
ninguna consulta. Las dos líneas nuevas del procedimiento están en la matriz de arriba y
en «Derechos del interesado»; se dicen aquí también porque es el paso que se olvida.

**El AVISO DE CANJE — una comunicación de datos de una persona a otra, y por tanto lo que
más conviene mirar aquí.** Cuando alguien canjea una invitación, el bot envía a los ids de
`BOT_ALLOWLIST_BOOTSTRAP` (quien administra) un mensaje con: la `nota` de para quién era la
invitación, y el **nombre de perfil de Telegram, el alias público y el id** de quien la ha
canjeado. Es la contramedida contra el reenvío: enfrenta «era para X» con «lo ha canjeado Y».
Precisiones, porque no todas empujan en la misma dirección:

- **Finalidad**: la misma que la allowlist —control de acceso a una herramienta de trabajo—, no
  una nueva. **Destinatario**: el propio responsable (el administrador de Fontiber), no un
  tercero; es información que ya podía consultar en la base con sus credenciales.
- **Pero sí aparece un dato NUEVO**: el *nombre de perfil y el alias de Telegram* de quien
  canjea. No es lo mismo que `user_consent.display_name` (que lo declara la persona al aceptar):
  este viene de Telegram y se trata sin que la persona lo haya facilitado a Fontiber. **No se
  PERSISTE por nuestra parte** —el id ya vivía en `bot_invitaciones.canjeada_por` y el nombre
  solo viaja en el mensaje—, pero el mensaje queda en el chat de Telegram del administrador, con
  la retención de Telegram, que ya está declarada como no controlada por nosotros.
- **A juicio del asistente esto NO exige `TERMS_VERSION` nueva** (ni finalidad ni destinatario
  nuevos), pero **sí es candidato a una línea del aviso v8**: «si accedes por invitación,
  registramos que la has canjeado y se lo comunicamos a quien te invitó». **Lo decide el asesor,
  no este documento** — mismo criterio que con `bot_errors`.
- Minimización aplicada: se manda lo justo para decidir y actuar (contraste + id para revocar),
  no el histórico ni el resto de la ficha.

**Lo que se retiró del log del proceso.** El canje escribía `telegram_user_id` en el log de
Railway, que está fuera de la matriz y fuera de cualquier supresión a petición (es la misma
razón por la que s295 sacó de ahí el texto de la consulta). Ahora se registra el **id de la
invitación** —un uuid, que no identifica a nadie por sí solo— y quién canjeó vive únicamente
donde está gobernado: `bot_invitaciones.canjeada_por` y el aviso de arriba.

### PENDIENTE MATERIAL — plazo y purga de las dos tablas (art. 5.1.e) ⚠️

**El hueco, sin adornos** (2º revisor, s324e): estas dos tablas **no tienen plazo**. La 016
declara que `rgpd_retencion_pasada` no las alcanza y eso se presentó como una virtud del diseño
—no hay identificador que disociar sin destruir la función de la tabla—, pero de ahí no se sigue
que puedan conservarse indefinidamente. `bot_invitaciones` guarda `nota` (nombre y cargo de una
persona real, escrito aunque la invitación **nunca se canjee**) y `canjeada_por` (identificador
**directo** de quien abrió el enlace, que puede no ser el destinatario). Decir «entra en el
mismo `[DECIDIR]` que `user_consent`» describe el hueco; no lo cierra.

**Plazo ADJUDICADO por Alberto (17-ago, s324e): los MISMOS 24 meses que el resto de la
matriz.** Su criterio —«debería ser consistente con el tiempo de mantenimiento del resto de
tablas, para que sea más simple»— es el correcto, y hay un argumento que lo refuerza y que la
propuesta inicial del asistente (6/12 meses) no tuvo en cuenta: **los 24 meses no son una
convención de este documento, son un INVARIANTE DE LA BASE** — el rol `rgpd_retencion` lleva
`interval '24 months'` cableado (s295/s299). Tres ventanas distintas habrían significado tres
formas de incumplir, un aviso de privacidad que anuncia una sola cifra, y una explicación más
larga al asesor. Una sola ventana es más simple de implementar, de auditar y de contar.

| Fila | Cuándo | Qué se hace |
|---|---|---|
| Invitación **nunca canjeada** (caducada o anulada) | **24 meses** desde `creada_at` | `nota = NULL` (es el único dato personal de una llave que nadie usó) |
| Invitación **canjeada**, con el acceso ya revocado | **24 meses** desde `revocado_at` del alta | `nota = NULL`, `canjeada_por = NULL`. Sobrevive «hubo un alta y la emitió X», que es la traza de auditoría sin la persona |
| Fila de `bot_allowlist` **revocada** | **24 meses** desde `revocado_at` | **`DELETE`** — y esta es la excepción que hay que declarar: `telegram_user_id` es la clave primaria, así que **no se puede disociar sin destruir la fila**. Es el único sitio de la matriz donde la acción a los 24 meses es borrar en vez de disociar |
| Fila de `bot_allowlist` **activa** | — | Se conserva mientras dure el acceso: es su finalidad |

Mecanismo: **una política más en `rgpd_retencion_pasada`**, no un job nuevo — el rol, el recibo
y el cron ya existen, y con el mismo intervalo la función no necesita parámetro nuevo.

**Sigue PENDIENTE (no implementado) y qué falta**: el plazo ya está decidido; falta (1) escribir
la política en la función de la base y (2) la **validación del abogado**, que va en el mismo
paquete que el aviso v8 y que el otro punto abierto (el aviso de canje comunica el nombre de
perfil y alias de Telegram de quien canjea, que es un dato nuevo). Hasta (1) y (2), esto es un
gap declarado con su plazo fijado, no un problema resuelto.

Tres decisiones de diseño con efecto en protección de datos, declaradas:

1. **La puerta va ANTES del consentimiento** (`telegram_bot.access_gate`). Es
   minimización: si el consentimiento fuese primero, cualquiera que encuentre el bot
   podría enviar `/accept Su Nombre` y quedaríamos con su nombre y su identificador
   guardados en `user_consent` —tabla cuyo plazo sigue siendo un `[DECIDIR]`— para una
   finalidad que no existe, porque nunca va a usar el sistema. Con la puerta delante,
   solo se registra a quien fue invitado. `/privacidad` queda FUERA de la puerta a
   propósito: poder leer el aviso sin haber aceptado nada es lo que hace informada la
   aceptación (s295), y el texto es el aviso público del responsable.
2. **El token de invitación no se guarda**: en la base vive su SHA-256. Una copia de
   seguridad, la consola de Supabase o una clave filtrada NO entregan invitaciones
   utilizables. El precio es que el enlace se enseña una sola vez.
3. **La baja es LÓGICA** (`revocado_at`), no un `DELETE`: borrar la fila destruiría la
   única prueba de quién dio acceso a quién y cuándo se le quitó. El `DELETE` queda
   reservado a la supresión a petición, donde el objetivo ES que no quede rastro.

A juicio del asistente esto **no es finalidad nueva** —control de acceso a una herramienta
de trabajo, coherente con la base de interés legítimo ya decidida por Alberto el 5-ago—,
pero **quien decide si toca el aviso o `TERMS_VERSION` es el asesor**, igual que con
`bot_errors`. Lo que sí conviene que el aviso v8 recoja, si el asesor lo comparte: que el
acceso es por invitación y que se conserva quién invitó a quién.

### Nota sobre los recibos versionados en git

`evals/s272_live_receipts_v1.json` contiene pregunta, respuesta y fecha de 3 consultas reales
extraídas de `query_logs`. **Revisado: no lleva identificadores** (ni `telegram_user_id` ni
`display_name`) y las 3 preguntas las disparó Alberto, no un tercero. No es equiparable a los
exports de `review_logs.py`. Pero deja una regla que sí importa y que hasta ahora no estaba
escrita: **todo extracto de contenido de producción que se versione en git debe revisarse
columna a columna y declararse aquí** — git no tiene plazo de retención y una supresión a
petición no lo alcanza.

### Nota sobre `user_consent`

~~El upsert machacaba: solo sobrevivía la última versión aceptada~~ — **RESUELTO y APLICADO
(5-ago)**: desde s296 hay una fila por (persona, versión) y desde s297 el libro
`consent_events` conserva la traza de cada aceptación y revocación. Límite histórico
declarado: lo pisado antes de s296 (v1..v6) es irrecuperable y el libro arranca con una
reconstrucción marcada `origen='backfill'`, sin fingir más. Lo que SIGUE pendiente aquí es
el **PLAZO** de `user_consent`/`consent_events` — **[DECIDIR]** con el asesor.

## El panel de control (s324f): una VENTANA nueva, no un tratamiento nuevo

**Qué es y por qué aparece aquí.** DEC-231 reabre DEC-183 y añade un servicio web propio
(`dashboard/`, otro servicio de Railway) para gestionar el acceso al piloto y mirar las
métricas. No recoge ni un dato que no se recogiera ya, no crea ninguna tabla y no llama a
ningún proveedor nuevo: **es una forma nueva de MIRAR datos que ya existen**. Por eso no
añade filas a la matriz — pero sí añade una superficie, y una superficie sobre datos
personales se declara. **⚠️ (s326) El «no crea ninguna tabla» quedó atrás**: la migración
021 añade `query_clasificacion` (derivada, enlazable) — dada de alta en la subsección s326
de abajo, con el criterio de `bot_errors`.

**Qué expone exactamente, y con qué base.** El panel no tiene una base jurídica propia: lee
para las MISMAS finalidades ya declaradas arriba, y el acceso de quien administra es una
medida de seguridad del art. 32 (control de acceso), no una finalidad nueva.

| Pantalla | Qué datos personales enseña | Para qué (finalidad ya declarada) | Minimización aplicada |
|---|---|---|---|
| **Acceso** | `telegram_user_id` (identificador DIRECTO), `nota` (nombre y cargo), quién dio de alta y quién revocó, `canjeada_por` | Control de acceso del piloto: emitir, auditar y revocar | Es la única pantalla con identificadores directos, y los necesita: **sin el id no se puede revocar y sin la nota no se puede auditar**. El `select` es explícito columna a columna (no `select=*`) y **no trae `token_hash`**. La nota se recorta a 60 caracteres en pantalla |
| **Resumen** y **Métricas** | Ninguno directo en las 7 vistas de s301-s315 (seudónimo o agregados). **⚠️ SUPERSEDIDO EN PARTE por s326** (ver «El Explorador y las métricas de uso», más abajo): la vista «Quién pregunta cuánto» SÍ cruza con la allowlist por adjudicación de Alberto | Salud y uso del bot | Las 7 vistas originales siguen sin cruzar nada; el cruce nuevo usa el alias (`nota`), nunca el id, y el histórico sin alta se agrupa SIN identificador |
| **Errores** | Preguntas escritas por técnicos (top de las que más fallan), sin autor | Saber qué falla para arreglarlo | Se muestran **recortadas a 110 caracteres, agregadas por repetición y sin `telegram_user_id`**. La cifra «técnicos afectados» es un CONTEO de identificadores distintos, no la lista |
| **Cualquiera** | — | — | `Cache-Control: no-store` en TODA respuesta: ni el navegador ni un proxy intermedio guardan copia de una página con estos datos dentro |

**Lo que el panel NO puede hacer, por diseño y no por convención**: escribir en `query_logs`,
`user_consent` o `consent_events`, y canjear una invitación. Sus únicas escrituras son tres:
emitir una invitación y poner dos marcas de tiempo (anular invitación, revocar acceso).
**⚠️ La primera prohibición original —«leer las conversaciones de los DGs (fuera de v1 por
DEC-231)»— quedó SUPERSEDIDA en s326**: Alberto, como el gatillo que la propia DEC-231
preveía («entra cuando el piloto lo pida»), adjudicó abrir el Explorador con la PREGUNTA y el
comentario del técnico. El detalle y sus salvaguardas, en la sección siguiente.

### s326 — El Explorador y las métricas de uso: la ventana crece, y se declara

**Qué cambió (19-ago-2026, adjudicación de Alberto en el hilo; propuesta
`evals/s326_panel_metricas_uso_propuesta_v1.md`)**: (a) una pestaña nueva, **Explorador**,
enseña pregunta a pregunta el TEXTO escrito por el técnico y su comentario del «✍️ Te lo
explico», con su clasificación y su feedback — es exactamente el «fuera de v1» de DEC-231,
reabierto a conciencia por quien lo aplazó; (b) la vista «Quién pregunta cuánto» cruza los
conteos con el **alias** de la allowlist (`nota`) — el mismo dato humano que la pestaña de
Acceso; el histórico sin alta se agrupa bajo la etiqueta fija «sin alta (histórico)», **sin
identificador** (hallazgo del dúo s326: correlacionar id↔conteos↔prosa habría sido exposición
nueva; el alias no lo es).

**La tabla nueva de la matriz — `query_clasificacion` (migración 021)**: derivada 1:1 de
`query_logs` (categoría de la pregunta por taxonomía cerrada, marcas/modelos canónicos,
menciones sin corpus). **Sin identificador propio**, pero FK a `query_logs` ⇒ **dato
enlazable**, exactamente el criterio ya fijado para `bot_errors` (arriba): hereda la
gobernanza de `query_logs` — la supresión a petición la alcanza **sin pasos nuevos** (ON
DELETE CASCADE, verificado en la postcondición de la 021), el job mensual no necesita
conocerla (nada que disociar), y es **reconstruible y desechable** (borrarla no pierde dato
original). El clasificador envía la pregunta a la API de Anthropic para etiquetarla — el
MISMO encargado y el mismo flujo ya declarados para generar respuestas; finalidad:
estadística de uso/calidad del propio servicio.

**Minimización del Explorador**: solo panel autenticado (misma puerta y cabeceras);
`response` NO se expone (solo su longitud); filas `source='error'` fuera; filtros de listas
cerradas; prosa siempre escapada; `Cache-Control: no-store` como en todo el panel.

**Para el paquete del abogado — ADDENDUM PENDIENTE (gate declarado en el PLAN)**: que el
asesor confirme (1) la lectura de conversaciones desde el panel por el responsable/admins
como parte del tratamiento ya informado (el aviso ya dice que las consultas se guardan y
quién las ve), y (2) si la clasificación estadística merece mención expresa en el registro
de actividades. Hasta ese addendum, el Explorador puede usarse internamente (Alberto), y la
invitación de DGs al panel espera al paquete — como ya esperaba por DEC-231.

**Medidas de seguridad, para el registro de actividades**: sin acceso anónimo a ninguna ruta
(sólo la pantalla de entrada responde sin sesión); contraseña con `scrypt` (memory-hard, sal
por usuario, parámetros en el propio registro) y **nunca en claro en el repo ni en un
fichero**; sesión en cookie firmada con HMAC-SHA256, `HttpOnly` + `Secure` +
`SameSite=Strict` y caducidad verificada en el servidor; cerrojo con espera creciente contra
la fuerza bruta; CSRF por token de sesión más comprobación de origen en toda escritura; CSP
sin JavaScript posible; y **la clave de servicio de Supabase no sale del proceso** (hay un
test que recorre todas las respuestas y falla si aparece).

**Consecuencia declarada, y es la de DEC-183**: esto es superficie nueva expuesta a internet
con datos personales detrás. El riesgo residual no es cero — una contraseña filtrada da
acceso a la pantalla de Acceso, es decir, a los identificadores y a los nombres. La respuesta
operativa está escrita y es barata: rotar `DASHBOARD_SECRET` en Railway cierra **todas** las
sesiones abiertas al instante.

**Para el paquete del abogado** (el mismo del aviso v8 y del aviso de canje): que exista un
panel interno con estos datos **no cambia lo que se le informa al técnico** —el tratamiento
es el mismo— pero conviene que el asesor lo confirme, y que diga si el registro de
actividades de tratamiento debe recoger expresamente esta vía de acceso. Es una pregunta
para él, no un gap que este documento pueda cerrar solo.

## Cómo se informa: aviso en DOS CAPAS

La segunda capa lleva además lo que un aviso debe llevar y antes no estaba en ninguna parte
visible para el técnico: **responsable identificado**, **base jurídica**, **cómo retirar el
consentimiento**, **reclamación ante la AEPD** y **transferencias fuera de la UE** (con el canal
para preguntar por las garantías). Declararlo solo en este documento interno no informaba a
nadie.

El texto de aceptación (`/start`) es la **primera capa**: qué se guarda, cuánto, quién lo ve y el
canal de derechos. ⚠️ **Corregido el 20-ago-2026**: este párrafo decía que la primera capa dice
«que hay proveedores fuera de la UE», y **desde el v9 ya no lo dice** — esa mención bajó al detalle
de `/privacidad` por decisión de Alberto (s324f). Es un cambio con consecuencias jurídicas, así que
va como pregunta EXPRESA al asesor (P1 y anexo B del paquete), no como nota interna. El **detalle completo** —proveedores por
función, finalidad, plazos, derechos— vive en **`/privacidad`**, que se puede leer **sin haber
aceptado nada** (condición para que la primera capa cuente como informada).

Los destinatarios se describen **por categoría, con la lista actual** («búsqueda en los
manuales: Voyage AI»), que es lo que pide el RGPD («destinatarios *o categorías de
destinatarios*»). Consecuencia práctica **acotada**: sustituir un proveedor por otro **equivalente** dentro de la
misma categoría no obliga a rehacer el aviso. Pero la categoría **no da inmunidad**: si el
sustituto cambia el país, las garantías de transferencia, sus subencargados o su plazo de
conservación, eso es material y hay que informarlo igual. Lo que sí exige aviso nuevo —y re-aceptación mientras la
base sea el consentimiento— es una **categoría de dato nueva** (p. ej. fotos), un **propósito
nuevo** (p. ej. memoria durable) o un destinatario **fuera de las categorías declaradas**.

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
> retención cero para API, y archivarlos. El **mecanismo de transferencia** de cada uno está
> ya documentado en la sección siguiente (5-ago-2026); lo valida el asesor.

## Mecanismos de transferencia (documentados 5-ago-2026 — los valida el asesor)

Cuando un dato personal viaja a un encargado fuera de la UE, el RGPD exige un vehículo
legal: la **certificación DPF** (EU-US Data Privacy Framework, registro público) o las
**SCCs** (cláusulas contractuales tipo, normalmente incorporadas en el DPA del proveedor).
Verificado por el asistente contra las fuentes indicadas el 5-ago-2026; **el asesor confirma
las entradas del registro DPF** (dataprivacyframework.gov) antes de apoyarse en ellas.

| Proveedor | Mecanismo documentado | Fuente (5-ago-2026) | Acción restante |
|---|---|---|---|
| **Anthropic** | **SCCs en su DPA comercial**. Su propia política de privacidad declara adecuación + SCCs y **NO declara DPF**; contrata la región europea desde *Anthropic Ireland, Limited*. Fuentes terciarias lo listan como DPF-certificado (jun-2026) — **no apoyarse en DPF** hasta que el asesor lo vea en el registro | [anthropic.com/legal/privacy](https://www.anthropic.com/legal/privacy) | Aceptar/archivar DPA de la consola API |
| **OpenAI** | **SCCs incorporadas en su DPA público** (vigente 1-ene-2026); fuentes terciarias: DPF activo (jun-2026) — comprobar registro | [openai.com/policies/data-processing-addendum](https://openai.com/policies/data-processing-addendum/) | Aceptar/archivar DPA |
| **Voyage AI** | **DPF declarado por el PROPIO proveedor**: la declaración de MongoDB nombra expresamente a *Voyage AI Innovations, Inc.* entre las entidades que se auto-certifican (EU-US + extensión UK + Swiss-US), con DPA de MongoDB disponible. Es declaración nominal del proveedor, **no certificación confirmada**: la entrada del registro la comprueba el asesor | [mongodb.com/legal/data-privacy-framework-statement](https://www.mongodb.com/legal/data-privacy-framework-statement) | Confirmar entrada en el registro; archivar DPA |
| **Railway** | **SCCs (Decisión 2021/914) incorporadas en su DPA autoservicio**; su política declara además cumplimiento EU-US DPF + UK + Swiss | [railway.com/legal/dpa](https://railway.com/legal/dpa) · [railway.com/legal/privacy](https://railway.com/legal/privacy) | Ejecutar el DPA self-service y archivarlo |
| **Supabase** | El **almacenamiento** está en la UE (`eu-north-1`, verificado vía API) — eso cubre dónde viven los datos, no toda operación de la empresa (soporte/backups son de una entidad US); por eso su DPA con módulos SCC aplica igualmente | [supabase.com/legal/dpa](https://supabase.com/legal/dpa) | Aceptar/archivar DPA |
| **Telegram** | **NO ofrece DPA.** Su propia política se declara **responsable (controller)** del tratamiento de sus usuarios del EEE, con representante art. 27 (EDPO). Refuerza la posición ya declarada en el aviso: responsable propio del transporte, como una operadora — **la valida el asesor** | [telegram.org/privacy](https://telegram.org/privacy) | Validación del asesor de la posición |

**Mantenimiento**: las certificaciones DPF se renuevan ANUALMENTE — revisar esta tabla al
año o al cambiar/añadir proveedor (la categoría del aviso no da inmunidad si cambia el
mecanismo de transferencia; ver «Cómo se informa»).

## Derechos del interesado

- **Canal** ⬤: `info@fontiber.com` (declarado en los términos que el técnico acepta).
- **Supresión**: hoy es **manual** y está documentada en `docs/DG_DEPLOYMENT.md`:
  `UPDATE user_consent SET revoked_at = NOW() …` + `DELETE FROM query_logs WHERE
  telegram_user_id = X` (la cascada se lleva votos, explicaciones y anclas de SUS consultas)
  + `DELETE FROM answer_feedback WHERE telegram_user_id = X` (los votos que emitió sobre
  consultas AJENAS, que la cascada no alcanza) + `DELETE FROM feedback WHERE telegram_user_id = X` + **`DELETE FROM persona_seudonimo WHERE telegram_user_id = X`** (la correspondencia es dato personal: sin borrarla, el código seguiría llevando a la persona) + **(desde s324e, si la migración 016 está aplicada) `DELETE FROM bot_allowlist WHERE telegram_user_id = X`** y **`UPDATE bot_invitaciones SET canjeada_por = NULL, disociada_at = now() WHERE canjeada_por = X`** (desde s330 la marca es OBLIGATORIA: sin ella la sentencia falla con `23514`) — estas dos **no cascadean desde `query_logs`**, así que hay que acordarse de ellas a mano, y conviene revisar sus columnas `nota` (llevan el nombre y el cargo escritos). **No alcanza los exports a disco**: hay que borrarlos
  aparte.
- **Acceso y portabilidad**: no implementados. Hoy se atienden a mano.

## Pendiente (con dueño)

0. **DECIDIDO por Alberto (4-ago), construido y APLICADO (5-ago)**:
   - **Seudónimo estable** en lugar de NULL (sección de arriba), y **exports que solo lleven el
     código**.
   - **`user_consent`: una fila por (persona, versión)** con su fecha, en vez de una por
     persona. Hoy no se puede demostrar que alguien aceptó la v3 — solo la última. **Ojo con
     el nombre**: esto CONSERVA cada versión, pero NO es inmutable — re-aceptar la misma
     versión refresca su fila, y `service_role` mantiene UPDATE de tabla sobre el histórico.
     Inmutabilidad real exigiría quitarle ese UPDATE; queda anotado, no hecho.
   - **Enlace en `feedback`**: se añade la columna que hoy no existe y se rellena en cada
     escritura nueva, así la tabla entra en la cascada. Las filas antiguas (1) quedan huérfanas y
     así se declara. *Deuda anotada, NO resuelta aquí: lo verdaderamente BP sería tener un solo
     canal de feedback en vez de dos; es un refactor de producto, no de cumplimiento.*
   - **Supresión a petición = DESVINCULAR, no borrar** (Alberto quiere conservar el material):
     ante una petición se aplica el mismo mecanismo del plazo. **Cautela obligatoria**: revisar
     que el texto libre de esa persona no lleve su nombre escrito dentro.
   - **`/borrar` autoservicio: NO se construye.** La vía es escribir a `info@fontiber.com`, ya
     declarada en el aviso. Recordatorio: el plazo legal de respuesta es de un mes y la petición
     no se puede denegar.

1. ~~Aplicar la propuesta del rol de retención~~ **HECHO (5-ago)**: la cola s295 → s296 →
   s297 está aplicada y verificada. `user_consent` sigue FUERA y necesita decisión aparte.
2. ~~`feedback` no cascadea~~ **HECHO (s296/s297, aplicado 5-ago)**: el enlace existe y se
   rellena en cada escritura nueva. Las filas ANTERIORES al enlace siguen huérfanas: un
   borrado a petición aún debe acordarse de ellas a mano (está en el runbook).
3. ~~Exports a disco sin plazo~~ **RESUELTO por decisión de Alberto (5-ago)**: los exports
   llevan seudónimo desde s296 — sin identificadores directos, el plazo se disuelve.
   Higiene restante: no reenviarlos, y borrar los ANTERIORES a s296 si aparecen. → *Alberto.*
4. ~~Programar el job~~ **HECHO Y APLICADO (s299, 5-ago; PR #210)**: pg_cron DENTRO de la
   base — el argumento histórico contra programar («un scheduler guardaría un
   `DATABASE_URL` de operador») era contra el cron EXTERNO, y pg_cron es justo lo que lo
   evita: ninguna credencial sale de la base, la pasada es UNA función
   (`rgpd_retencion_pasada`) que asume el rol en su encabezado, y cada pasada confirmada
   deja recibo en `rgpd_recibos`. Verificado tras aplicar: job ACTIVO (`cron.job`),
   oráculo CERRADO, dry-run exit 0. **Primer recibo esperado: 1-sep.**
   **Vigilancia del reloj (ronda 2 del dúo)**: un reloj roto ABORTA en silencio — la
   pasada que no puede cumplir no deja recibo y el error solo vive en
   `cron.job_run_details`. Comprobación trimestral (o en cada sesión de mantenimiento):
   `SELECT max(ejecutado_at) FROM rgpd_recibos;` debe ser del mes en curso o el anterior;
   si no, mirar `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;`.
5. **Autoservicio `/borrar`: NO se construye** (decisión 5-ago) — la vía es
   `info@fontiber.com`, ya declarada en el aviso.
6. ~~Mecanismo de transferencia~~ **DOCUMENTADO (5-ago)**: tabla «Mecanismos de
   transferencia» de arriba, con fuentes y fecha. Falta: validación del asesor + aceptar y
   archivar los DPA. → *Alberto / asesor legal.*
7. ~~Identificación completa del responsable~~ **HECHO (v6)**: el aviso lleva razón social,
   CIF y domicilio — *Fontiber Industrial Partners, S.L. · CIF B24984759 · Calle de la Palma
   10, 28004 Madrid*, tomados del aviso legal de `fontiber.com` (indicado por Alberto).
8. **Decidir la base jurídica** (ver la sección de arriba). Es lo que determina si los cambios
   futuros del aviso exigen re-aceptación o basta con informar. → *Alberto / asesor legal.*

## Estado real hoy (verificado 3 ago 2026)

71 consultas desde el 7 de abril, 1 usuario con consentimiento activo, 1 feedback libre, 3
votos, 4 anclas. **0 filas fuera de plazo** (la más antigua es de abril de 2026 ⇒ vence en
2028). La exposición **hoy** es trivial; la matriz existe para que deje de serlo de forma
controlada cuando entren técnicos, no para el estado actual — y para que el plazo llegue con
la maquinaria ya construida y probada, no improvisada.

## Decisiones de Alberto (5-ago, segunda tanda) — registro

1. **Base jurídica: INTERÉS LEGÍTIMO — decidido.** Surte efecto tras la validación del asesor
   (regla del propio borrador LIA); entonces se construye el aviso v8 (base + derecho de
   oposición, `/accept` pasa a acuse de recibo, `TERMS_VERSION` pasa a tripwire de
   re-información).
2. **Exports: con seudónimo — confirmado.** Ya construido y vivo desde s296; el pendiente del
   plazo se disuelve (los ficheros nuevos no llevan identificadores directos). Higiene
   restante: no reenviarlos por correo/Drive, y borrar los ANTERIORES a s296 si aparecen.
3. **Programar el job: SÍ — aprobado scheduler.** Diseño elegido: **pg_cron dentro de
   Supabase** (extensión disponible, verificado) — ninguna credencial sale de la base; la
   función corre con `SET role = rgpd_retencion` a nivel de función, así que la ventana de 24
   meses sigue siendo invariante del motor también en la ejecución programada. Con tabla de
   recibos. **Construido (s299)**: migración `20260805150000_s299_job_programado_v1.sql`
   (la pasada pasa a ser UNA función en la base; el script queda como driver manual) —
   **pendiente de APLICAR en el SQL Editor** (pendiente 4).
4. **`/borrar`: por correo — confirmado** (ya era el estado; no se construye comando).
5. **Transferencias: las documenta el asistente y las valida el asesor** — por proveedor: DPA
   archivado + estado en el registro DPF o SCCs del contrato + nota de una línea aquí.
   Telegram es el caso especial (sin DPA: posición defendible = responsable propio del
   transporte, ya declarado en el aviso; la confirma el asesor).
