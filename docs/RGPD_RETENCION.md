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

**Encima, s299 (construida — pendiente de aplicar):** la pasada se mueve a UNA función en
la base (`public.rgpd_retencion_pasada`, `SET role` en el encabezado + cinturón de
`current_user`), pg_cron la ejecuta el día 1 de cada mes (04:30 UTC) sin que ninguna
credencial salga de la base, y cada pasada confirmada deja recibo en `rgpd_recibos`.
`scripts/rgpd_retencion.py` queda como driver manual de esa misma función (dry-run = la
misma pasada + ROLLBACK, recibo incluido). Gap declarado: el contenedor de CI no trae
pg_cron ⇒ la RAMA de programación no se ejerce en CI (la función sí, entera); en
producción la postcondición exige el job si pg_cron está disponible — que lo está
(verificado, 1.6.4).

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
| Pregunta, respuesta, transcripción de voz | `query_logs` | Diagnóstico, calibración con preguntas reales | **24 meses identificado → disociado indefinido** | `DELETE` (cascadea a las hijas) | Se retira el id — **hoy bloqueado (1)** |
| ID de Telegram del autor | `query_logs.telegram_user_id` | Vincular consulta ↔ persona | **24 meses** | `DELETE` | → NULL — **hoy bloqueado (1)** |
| Voto 👍/👎 y su motivo | `answer_feedback` | Señal de calidad | Sigue a su consulta | **CASCADE** desde `query_logs` | — |
| **ID del votante** | `answer_feedback.telegram_user_id` | Un voto por persona y consulta | 24 meses | ⚠️ CASCADE **solo si votó su propia consulta** — ver nota | **NO se retira hoy** — es `NOT NULL`; exige `DROP NOT NULL` (propuesta §2) |
| Explicación en texto libre del 👎 | `answer_feedback.comment` | Convertir el 👎 en caso diagnosticable | Sigue a su consulta | CASCADE | Se conserva; puede contener datos personales en prosa |
| Ancla mensaje ↔ consulta | `answer_messages` (`telegram_chat_id`, `telegram_message_id`) | Atribuir una respuesta de Telegram a su consulta | Sigue a su consulta | CASCADE | **Se BORRA** — mapeo operativo sin valor analítico a 24 meses (propuesta §3) |
| Feedback libre del canal antiguo + **copias** de pregunta/respuesta | `feedback` | Histórico | Igual que `query_logs` | ⚠️ **NO CASCADEA** (sin FK): hay que borrarla a mano | → NULL — **hoy bloqueado (1)** |
| Aceptación de términos, `display_name` | `user_consent` | Prueba del consentimiento | ⚠️ **hoy indefinido** — ver pendiente 1 | Revocación lógica (`revoked_at`) **no borra nada** | **[DECIDIR]** |
| **Libro de eventos de consentimiento** (`telegram_user_id`, versión, evento, fecha) | `consent_events` (s297) | EVIDENCIA de aceptaciones y revocaciones — solo inserción para el bot | ⚠️ mismo **[DECIDIR]** que `user_consent` (es la prueba; fuera de `rgpd_quedan_identificados`, como ella) | **[DECIDIR]** con el asesor: borrar vs conservar como prueba de cumplimiento (alineado con el runbook) | **[DECIDIR]** |
| **Exports a disco** (desde s296: **seudónimo**, pregunta, transcripción, respuesta — SIN `display_name` ni `telegram_user_id`) | `data/eval/logs_export_*.csv\|xlsx` vía `scripts/review_logs.py` | Curar eval orgánico | ⚠️ **ninguna** — fuera de Supabase e **inalcanzable** para el job | Borrado manual del fichero | Nada |
| **Exports ANTERIORES a s296** (llevan `display_name` y `telegram_user_id`) | los ficheros ya generados | — | ⚠️ ninguna | Borrado manual — **hay que buscarlos**: el cambio no toca lo ya escrito | Nada |
| **Correspondencia código ↔ persona** | `persona_seudonimo` | Agrupar el histórico de un técnico sin identificarlo | Mientras le quede alguna fila identificada | `DELETE` (hay que incluirla) | **Se BORRA** — ese borrado ES el punto de no retorno |
| **Marca de utilidad del feedback** | `answer_feedback.utilidad` | Reconocer aportaciones valiosas (posible incentivo) | Sigue a su consulta | CASCADE | Se conserva: no identifica por sí sola |
| **Extracto de recibos en git** (`query`, `response`, `created_at` de 3 consultas) | `evals/s272_live_receipts_v1.json` + copia en `tests/fixtures/` | Recibos de una ventana de flag | ⚠️ **ninguna** — vive en el HISTORIAL DE GIT, fuera del alcance del job | Reescritura de historia (costosa) | Nada |
| **Recibos de las pasadas de retención** (origen, corte, conteos; ids de FILA ya disociada — el conteo de vínculos destruidos va SIN ids a propósito) | `rgpd_recibos` (s299) | Evidencia de que la retención corrió (manual o pg_cron) — solo inserción, ilegible para el bot | Indefinida: es evidencia de cumplimiento y no identifica a nadie | No aplica (no lleva persona) | Nada |
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

## Cómo se informa: aviso en DOS CAPAS

La segunda capa lleva además lo que un aviso debe llevar y antes no estaba en ninguna parte
visible para el técnico: **responsable identificado**, **base jurídica**, **cómo retirar el
consentimiento**, **reclamación ante la AEPD** y **transferencias fuera de la UE** (con el canal
para preguntar por las garantías). Declararlo solo en este documento interno no informaba a
nadie.

El texto de aceptación (`/start`) es la **primera capa**: qué se guarda, cuánto, quién lo ve, que
hay proveedores fuera de la UE, y el canal de derechos. El **detalle completo** —proveedores por
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
| **Voyage AI** | **DPF**: la declaración de MongoDB nombra expresamente a *Voyage AI Innovations, Inc.* como entidad certificada (EU-US + extensión UK + Swiss-US), con DPA de MongoDB disponible. La más sólida de las cinco | [mongodb.com/legal/data-privacy-framework-statement](https://www.mongodb.com/legal/data-privacy-framework-statement) | Confirmar entrada en el registro; archivar DPA |
| **Railway** | **SCCs (Decisión 2021/914) incorporadas en su DPA autoservicio**; su política declara además cumplimiento EU-US DPF + UK + Swiss | [railway.com/legal/dpa](https://railway.com/legal/dpa) · [railway.com/legal/privacy](https://railway.com/legal/privacy) | Ejecutar el DPA self-service y archivarlo |
| **Supabase** | El almacenamiento está **en la UE** (`eu-north-1`, verificado vía API): en operación normal el dato no sale. DPA con módulos SCC para sub-encargados | [supabase.com/legal/dpa](https://supabase.com/legal/dpa) | Aceptar/archivar DPA |
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
  consultas AJENAS, que la cascada no alcanza) + `DELETE FROM feedback WHERE telegram_user_id = X` + **`DELETE FROM persona_seudonimo WHERE telegram_user_id = X`** (la correspondencia es dato personal: sin borrarla, el código seguiría llevando a la persona). **No alcanza los exports a disco**: hay que borrarlos
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
4. ~~Programar el job~~ **CONSTRUIDO (s299)**: pg_cron DENTRO de la base — el argumento
   histórico contra programar («un scheduler guardaría un `DATABASE_URL` de operador») era
   contra el cron EXTERNO, y pg_cron es justo lo que lo evita: ninguna credencial sale de la
   base, la pasada es UNA función (`rgpd_retencion_pasada`) que asume el rol en su
   encabezado, y cada pasada confirmada deja recibo en `rgpd_recibos`. **Pendiente: APLICAR
   la migración s299 en el SQL Editor** (→ Alberto) y verificar `SELECT * FROM cron.job` +
   el primer recibo mensual. ⚠️ Hasta aplicarla, `scripts/rgpd_retencion.py` de esta
   versión sale con exit 2 (la función aún no existe en producción) — diagnóstico incluido.
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
