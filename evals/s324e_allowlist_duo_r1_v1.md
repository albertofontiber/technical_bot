# s324e — Allowlist: resolución del dúo (Sol r1) + refuerzos de Alberto + criterio de GO

Anexo de `s324e_allowlist_propuesta_v1.md`, que ya está corregido con todo lo de aquí.
**Nada aplicado ni desplegado; sin commit.**

## 1. Los tres refuerzos de Alberto

| # | Pedido | Qué se hizo |
|---|---|---|
| R1 | Caducidad 7 → **2 días** | Default `2` (`access.DIAS_CADUCIDAD_DEFECTO`), `--dias` sigue existiendo pero **acotado a 7**, y la cota va también como `CHECK` en la 016 — el script no es el único cliente posible de la tabla. Docstring, ayuda y texto de salida actualizados. |
| R2 | **Aviso de canje** | `canjear_invitacion` devuelve `ResultadoCanje(estado, nota, creada_por, invitacion_id)` en vez de una cadena; el bot avisa a `access.ids_bootstrap()` enfrentando «era para X» con «lo ha canjeado Y». Sin administradores configurados **no falla**: log y sigue. Un envío fallido va por `_reportar_error(update=None, etapa="aviso_canje")` — se clasifica y registra, pero **no se le contesta nada al DG**, que acaba de recibir «Invitación aceptada» y cuyo alta ya está confirmada. |
| R3 | Latencia real de revocación | **Medida y corregida** (ver §3). El informe decía «≤10 min» y ese era solo el caso bueno. |

**Texto exacto del aviso** (el que recibirá Alberto):

```
🔑 Invitación canjeada

Era para: Juan Pérez, DG de Acme
La ha canjeado: Marta Ruiz (@martaruiz) · id 987654321

Si no es quien esperabas, el enlace se reenvió. Quítale el acceso con:
python -m scripts.s324e_invitaciones revocar-acceso 987654321
```

## 2. Los 8 hallazgos del dúo

| # | Hallazgo | Resolución |
|---|---|---|
| 1 crítico | Errata en `BOT_ALLOWLIST` ⇒ piloto abierto | **Aplicado, y la lógica se invierte**: la puerta se apaga solo con un `off` RECONOCIBLE (`off\|0\|false\|no`); cualquier otra cosa la deja PUESTA. **Cerrar, no «no arrancar»** — decisión y motivo en §4. Además `access.validar_configuracion()` aborta el arranque desde `run_bot` con el valor mal escrito en el mensaje, y valida también `BOT_ALLOWLIST_BOOTSTRAP` (un id ilegible se ignoraba en silencio y dejaba fuera a quien administra) y `BOT_DAILY_LIMIT`. |
| 2 crítico | La puerta no mira el tipo de chat ⇒ grupos | **Aplicado**: `es_chat_privado` en la puerta, **antes** que la exención de `/start` (si no, un `/start <token>` tecleado en un grupo canjearía desde ahí). Estricto: un tipo ausente o desconocido no es privado. Se avisa **una vez por grupo** y luego se para en silencio. Recomendación para Alberto, que es configuración: BotFather → `/setjoingroups` → **Disable**. |
| 3 medio | Readmisión viola el `CHECK` | **Aplicado y probado**: se limpian `revocado_at`, `revocado_por` y `motivo_revocacion` **juntos** (la revocación es un hecho de tres campos). El doble de PostgREST ahora **aplica los CHECK**, así que el test del ciclo alta → revocación → nueva invitación → alta caía antes del arreglo. La propuesta afirmaba algo que no era cierto; ya lo es. |
| 4 medio | Canje perdido en vuelo | **Aplicado por los dos lados**: liberación best-effort por `(token_hash, canjeada_por)` —no hace falta el id, y el filtro impide soltar un canje ajeno— y un mensaje **verdadero en los dos casos** (`MENSAJE_CANJE_INCIERTO`), porque desde el código no se puede saber si el PATCH se confirmó. Si también falla la liberación, la invitación queda quemada: **gap declarado**, visible en `listar` («usada» sin fila en la allowlist). |
| 5 medio | `telegram_user_id` en los logs de Railway | **Aplicado**: se registra el **id de la invitación** (uuid, no identifica por sí solo). Quién canjeó vive donde está gobernado: `bot_invitaciones.canjeada_por` y el aviso. Declarado en `RGPD_RETENCION.md`, con un test que impide que vuelva. |
| 6 método | Falta OBJETIVO + MÉTRICA del GO | **Aplicado**: §3. |
| 7 menor | «Se acota a 7 días» era falso | **Aplicado**: cota real en el emisor (`argparse`) y en la base (`CHECK … interval '7 days'`). |
| 8 menor | «Una clave filtrada no entrega invitaciones» | **Corregido**: el hash protege copias de **solo lectura**; **no** protege de la service key, que puede insertarse una fila de allowlist directamente. Esa credencial sigue siendo la frontera real y así se escribe ahora. |

**Nada discutido**: los ocho se aceptan. Matiz sobre el 1, sin consecuencia: el ejemplo citaba `1` como valor que se leía OFF y en realidad sí estaba en la lista de encendido; el fallo real (`onn`) es exactamente como lo describe.

## 3. Criterio de GO del despliegue (hallazgo 6)

Objetivo del control: **que el piloto solo lo use quien fue invitado, y que eso no corte a
quien sí lo fue.** Verificable así — Alberto abre el piloto si O1–O4 pasan:

| | Objetivo | Métrica y cómo se comprueba | Umbral |
|---|---|---|---|
| **O1** | Bloquea a no invitados | En CI: 0 de N updates de un id fuera de la allowlist alcanzan el pipeline. En producción, tras 48 h: `SELECT count(*) FROM query_logs q WHERE q.created_at > <encendido> AND NOT EXISTS (SELECT 1 FROM bot_allowlist a WHERE a.telegram_user_id = q.telegram_user_id AND a.revocado_at IS NULL)` | **= 0** (descontando ids de bootstrap) |
| **O2** | No corta a autorizados | Con base sana, el 100 % de los updates de ids activos pasa. En producción: 0 quejas de acceso + 0 líneas `puerta: update rechazado` con `origen=db` para ids que están en la allowlist | **0 falsos rechazos** |
| **O3** | Un solo uso, de verdad | `SELECT count(*) FROM bot_invitaciones WHERE canjeada_at IS NOT NULL GROUP BY id` y altas por invitación | **1 alta por invitación; 0 altas sin invitación ni bootstrap** |
| **O4** | Solo chat privado | 0 respuestas técnicas emitidas en chats de tipo ≠ `private` | **= 0** |

**Tolerancias operativas declaradas** (no son fallos del control): con Supabase caído, un
usuario ya confirmado sigue entrando hasta 1 h y **nadie nuevo entra** — es el fail-closed con
matiz, por diseño; una revocación tarda ≤10 min en surtir efecto (≤60 min con la base caída);
y el tope diario puede reiniciarse en un redeploy. Si O1 u O4 fallan una sola vez, **NO-GO** y
`BOT_ALLOWLIST=off`.

## 4. La decisión del crítico 1: CERRAR, no «no arrancar» (y por qué las dos)

En **runtime** un valor no reconocido **cierra** la puerta en vez de abrirla. Es la única
opción defendible: la alternativa —abortar el proceso en caliente— convierte un error de
configuración en una caída total del servicio, y encima el bot ya está sirviendo cuando eso
ocurriría. Cerrar es el fallo seguro de un control de acceso.

En **arranque** sí se aborta (`validar_configuracion()` desde `run_bot`), porque ahí el coste
es el contrario: nadie está siendo servido todavía, Railway conserva el despliegue anterior, y
el motivo queda escrito con el valor exacto. Un deploy que no arranca se ve; un bot cerrado
en silencio se descubre cuando un DG se queja.

**Efecto colateral declarado**: con una errata, el bot queda cerrado para todos. Dos salidas,
ninguna con deploy: `BOT_ALLOWLIST_BOOTSTRAP` (no pasa por base ni caché) y corregir la
variable. La asimetría es deliberada: **apagar un control debe costar escribirlo bien;
encenderlo, no.**

## 5. Verificación (Protocolo 1)

**Latencia de revocación — MEDIDA, no estimada.** Se recorrió el reloj segundo a segundo sobre
`access.decidir` con la base doblada:

| Escenario | Deja de pasar a los | |
|---|---|---|
| Base sana | **600 s = 10 min** | el TTL de la caché |
| Supabase caído | **3.601 s ≈ 60 min** | la gracia degradada |
| Id en `BOT_ALLOWLIST_BOOTSTRAP` | **nunca** | no pasa por la base: hay que sacarlo de Railway |

**Corrección de una cifra propia**: la primera versión de este anexo decía «≤70 min» sumando
TTL + gracia. Es falso: la gracia se cuenta desde la **última confirmación de la base**, no
desde que caduca la caché, así que el peor caso es el **mayor** de los dos, no la suma. Medido
y corregido en el script, en `DG_DEPLOYMENT` y en la propuesta.

**Turno en curso**: la puerta decide POR UPDATE. El turno que ya pasó **termina** —no se puede
des-enviar una respuesta— y el corte llega en el mensaje siguiente. Anclado en
`test_un_turno_en_curso_termina_pero_el_siguiente_ya_no_pasa`.

**Suite completa**: `python -m pytest -q` → **4186 passed, 46 skipped, 0 failed** (10:49,
exit 0). De ellos, **119 propios**, $0, sin red ni DB, con los ocho hallazgos y los tres
refuerzos anclados (re-corridos 119/119 tras los últimos retoques posteriores a esa corrida,
que solo tocaron docstrings y documentación). Dos de ellos son de anti-regresión pura: el doble de PostgREST **aplica los CHECK**
de la 016 (sin eso, el fallo de la re-admisión seguiría invisible) y `test_ptb_no_para_el_update_cuando_un_handler_lanza`
pina la semántica de PTB que obliga a que la puerta no lance nunca.

**Smoke offline sobre los handlers REALES**: puerta rechaza → `/start` con enlace → canje →
aviso al administrador → puerta deja pasar → 2ª persona rebotada → **el mismo DG bloqueado al
escribir en un grupo**, con el aviso una sola vez. Y contra el Supabase real, solo lectura, con
las tablas ausentes: el script sale con mensaje claro y código 2.

**Lo que sigue sin verificarse**: la 016 no se ha ejecutado en ningún Postgres (no hay
docker/psql/psycopg en la máquina), así que los tres `CHECK`, los `GRANT` y el `INSERT…SELECT`
del bootstrap están revisados a ojo y con un chequeo estático de sintaxis, no ejecutados.
