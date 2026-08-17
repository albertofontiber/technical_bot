# s324e — Allowlist: resolución del dúo (Sol r1) + refuerzos de Alberto + criterio de GO

Anexo de `s324e_allowlist_propuesta_v1.md`, que ya está corregido con todo lo de aquí.
Cubre **dos rondas**: el dúo (Sol, r1, 8 hallazgos) y el 2º revisor (Opus 5, r2, 5 hallazgos),
más los tres refuerzos de Alberto. **Estado real**: commiteado (`df4752f`), **016 aplicada en
producción el 17-ago**, y **Railway sin tocar** — que es lo único que falta para que el control
exista de verdad.

## 1. Los tres refuerzos de Alberto

| # | Pedido | Qué se hizo |
|---|---|---|
| R1 | Caducidad 7 → **2 días** | Default `2` (`access.DIAS_CADUCIDAD_DEFECTO`), `--dias` sigue existiendo pero **acotado a 7**, y la cota va también como `CHECK` en la 016 — el script no es el único cliente posible de la tabla. Docstring, ayuda y texto de salida actualizados. |
| R2 | **Aviso de canje** | `canjear_invitacion` devuelve `ResultadoCanje(estado, nota, creada_por, invitacion_id)` en vez de una cadena; el bot avisa a `access.ids_bootstrap()` enfrentando «era para X» con «lo ha canjeado Y». Sin administradores configurados **no falla**: log y sigue. Un envío fallido va por `_reportar_error(update=None, etapa="aviso_canje")` — se clasifica y registra, pero **no se le contesta nada al DG**, que acaba de recibir «Invitación aceptada» y cuyo alta ya está confirmada. |
| R3 | Latencia real de revocación | **Derivada del diseño, anclada en test y corregida dos veces** (ver §5): el informe decía «≤10 min», que era solo el caso bueno, y después «≤70 min», que era una suma mal hecha. |

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

**Latencia de revocación — DERIVADA del diseño y anclada en test**, no observada end-to-end
(2º revisor, menor 4: no hay smoke contra Telegram, así que «medida» sobre-afirmaba). Se
recorrió el reloj segundo a segundo sobre `access.decidir` con la base doblada:

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

**Suite completa**: `python -m pytest -q` → **4192 passed, 46 skipped, 0 failed** (9:31,
exit 0). De ellos, **125 propios**, $0, sin red ni DB, con los ocho hallazgos y los tres
refuerzos anclados, más los 5 del 2º revisor. Dos de ellos son de anti-regresión pura: el doble de PostgREST **aplica los CHECK**
de la 016 (sin eso, el fallo de la re-admisión seguiría invisible) y `test_ptb_no_para_el_update_cuando_un_handler_lanza`
pina la semántica de PTB que obliga a que la puerta no lance nunca.

**Smoke offline sobre los handlers REALES**: puerta rechaza → `/start` con enlace → canje →
aviso al administrador → puerta deja pasar → 2ª persona rebotada → **el mismo DG bloqueado al
escribir en un grupo**, con el aviso una sola vez. Y contra el Supabase real, solo lectura, con
las tablas ausentes: el script sale con mensaje claro y código 2.

**Lo que sigue sin verificarse**: el `GRANT UPDATE` sobre la columna de conflicto solo se
ejerce en una re-admisión, que todavía no ha ocurrido en producción. Y no hay smoke contra
Telegram real: el canje no se ha probado con un enlace de verdad.

## 6. Segunda ronda: 5 hallazgos de Opus 5 + el incidente al aplicar la 016

**El incidente, porque la lección vale para todo el repo.** La 016 se aplicó el 17-ago **a la
segunda**, y el defecto era del fichero: llevaba dentro la prueba del un-solo-uso envuelta en
`BEGIN/ROLLBACK`. El SQL Editor de Supabase ejecuta el script entero dentro de una transacción,
así que ese `BEGIN` no abría otra y el `ROLLBACK` **deshizo también la creación de las tablas**
— con el agravante de que la validación imprimía `1`, que era cierto *dentro* de la
transacción. El intento con `SAVEPOINT` falló con `25P01` en otro cliente.
**Regla que queda: un fichero que CREA no puede llevar dentro una prueba que necesita
deshacerse, porque CÓMO se deshace depende del cliente SQL.** La prueba vive ahora en
`016_validacion_un_solo_uso.sql`; la 016 no lleva control de transacción de ningún tipo, solo
DDL + GRANT + `NOTIFY pgrst, 'reload schema'` (que también hizo falta: PostgREST cacheaba el
esquema y devolvía 404 sobre tablas ya creadas). Anclado en
`test_la_prueba_de_un_solo_uso_vive_fuera_del_fichero_que_crea`.

| # | Hallazgo | Resolución |
|---|---|---|
| 1 medio | «Es UN update condicional» es incompleto | **Aceptado y corregido en los tres sitios.** Lo atómico es el **quemado del token**; **canje+alta son dos peticiones REST sin transacción común** (la RPC se descartó en §2). §1 lo separa explícitamente y §3.6 declara la ventana. Test nuevo que la ejerce: `test_el_canje_y_el_alta_NO_comparten_transaccion`. Es el hallazgo más útil de la ronda: mis propios tests admitían la ventana mientras la prosa la presentaba como resuelta por el motor. |
| 2 medio | Sin plazo ni purga (art. 5.1.e) | **Aceptado. Gap material declarado, propuesta escrita, NO implementada**: sección «PENDIENTE MATERIAL» en `RGPD_RETENCION.md` con plazos por tipo de fila (6 meses la invitación nunca canjeada, 12 el resto) y mecanismo (una política más en `rgpd_retencion_pasada`, no un job nuevo). **Decide Alberto el plazo; el abogado valida.** |
| 3 medio | «Sin commit» era falso | **Aceptado**: cabecera actualizada al estado real — commiteado `df4752f`, 016 aplicada, **Railway sin tocar** (que es lo único que falta para que el control exista de verdad). |
| 4 menor | «Latencia medida» sobre-afirma | **Aceptado**: son constantes **derivadas del diseño y ancladas en test offline**, no observación end-to-end. Corregido en anexo, propuesta, `DG_DEPLOYMENT` y el texto del script. |
| 5 menor, especulativo | Crecimiento de memoria | **Aceptado e implementado** pese a ser especulativo: son estructuras sin cota alimentadas desde fuera, en el componente que atiende a los no autorizados. Cota de 10.000 con poda (caducado primero; **negativos antes que positivos**). |

**Lo que el hallazgo 5 destapó de paso**: la primera versión de la poda desalojaba «lo más
antiguo por confirmación», y **su propio test la tumbó** — una riada de denegaciones *frescas*
echaba antes al DG legítimo, cuya confirmación es más vieja que la del último intruso. Justo al
revés de lo que hay que proteger. Ahora los negativos caen primero: perder un NO cuesta una
consulta; perder un SÍ cuesta la gracia degradada.

**Nada discutido en esta ronda tampoco.** Matiz sobre el 3, sin consecuencia para el veredicto:
el estado no era «inconsistente» por descuido sino por desfase temporal — el informe se escribió
antes del commit del coordinador. La corrección es la misma.
