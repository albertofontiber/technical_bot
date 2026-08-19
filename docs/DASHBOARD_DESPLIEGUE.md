# Panel del bot — cómo se despliega (y qué falta antes)

> **Estado (19-ago-2026, s324j)**: el panel está **construido, probado y sin desplegar** — CON el
> cableado de la v9 dentro (DEC-239: usuarios en Supabase, sello, cerrojo distribuido, `op`,
> `revocada_por`). Este documento es el runbook para ponerlo en Vercel, con sus GATES.

## Los pasos de la 019/020, en orden (lo nuevo de s324j)

1. **Aplicar `migrations/019_panel_usuarios_cerrojo.sql` y luego
   `migrations/020_invitaciones_op.sql`** — **CADA fichero ENTERO, con un aplicador
   transaccional** (el SQL Editor de Supabase ejecuta el script completo en UNA transacción;
   desde consola, `psql --single-transaction`). NUNCA sentencia a sentencia: entre el CREATE y su
   REVOKE los defaults de Supabase dejarían la tabla de credenciales expuesta. Los ficheros NO
   llevan BEGIN propio a propósito (la lección de la 016, dos fallos reales). La 019 exige la
   cola s295→s299 aplicada (su preflight lo comprueba y aborta con el motivo).
2. **Alta de los usuarios del panel**: `python -m scripts.s324j_panel_usuario alta alberto`
   (valida estricto + challenge; escribe con la service key). `DASHBOARD_USUARIOS` desaparece de
   Vercel — la lista vive en `panel_usuarios` y revocar es un UPDATE efectivo en la siguiente
   petición (`... revocar <usuario>`).
3. **La sonda del cerrojo**, antes de dar nada por bueno:
   `curl` de login NO hace falta — basta ejecutar en local con las credenciales de producción
   `python -c "from dashboard import auth, cerrojo; auth.usar_backend(auth.BackendSupabase()); cerrojo.usar_cerrojo(cerrojo.CerrojoSupabase()); cerrojo.sonda(); print('cerrojo OK')"`
   (es la MISMA sonda que ejecuta `comprobar_arranque` donde el lifespan corre: función migrada,
   GRANT concedidos, caché de PostgREST recargada — sin tocar contadores).
4. **Smoke del cerrojo contra el despliegue real** (la capa PostgREST que el contenedor de CI no
   cubre): 6 intentos de login con contraseña mala → el sexto debe responder 429; un login bueno
   después del bloqueo… espera el minuto o usa otro usuario. Con DOS terminales a la vez si se
   quiere el entrelazado.
5. **Vigilancia del reloj de retención** (herencia del canon: un reloj roto ABORTA en silencio y
   solo el recibo demuestra ejecución): en cada sesión de mantenimiento,
   `SELECT max(ejecutado_at) FROM rgpd_recibos WHERE resultado ? 'panel_intentos';` debe ser de
   las últimas 48 h; si no, `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;`
   y arreglar el reloj antes que nada.

## Gates previos a EXPONER — no opcionales (v9 §13, DEC-239)

- **Plazo de `panel_usuarios` revocados**: `[DECIDIR: Alberto]` en la matriz de retención — una
  fila en blanco no entra a producción.
- **El panel dentro del paquete del abogado** (la mitigación que DEC-231 exigió), nombrando el
  pendiente canónico: la purga 24m de `bot_invitaciones`/`bot_allowlist` está adjudicada (s324e)
  y sin mecanismo — declarada, no escondida.
- **La medición de XFF** (método en v9 §8): hasta fijar la regla de confianza, la clave `ip:` del
  cerrojo NI CUENTA NI BLOQUEA (`dashboard/cerrojo.py::INCLUIR_CLAVE_IP = False`). No es solo
  «inefectiva»: con la IP compartida del proxy y el MAX sobre claves, 5 fallos de un atacante
  serían un 429 GLOBAL. Encenderla = medir primero, voltear la constante después.

## Riesgo declarado del cerrojo: el desalojo del cap con `ip:` apagada

Con la clave `ip:` apagada (estado actual, hasta medir XFF), un atacante que mande muchos logins
con usuarios inventados **distintos** crea una fila `u:<hmac>` fresca por intento; cuando la tabla
llega al cap (`CERROJO_MAX_ENTRADAS = 10.000`) la poda expulsa las más antiguas, y puede empujar
fuera la fila de bloqueo de un usuario concreto, cuyo backoff se resetea. No es gratis para el
servidor —mientras el atacante no esté bloqueado, cada intento paga el señuelo scrypt (~100 ms)—,
pero sí barato para él. Dos cosas lo acotan, y por eso va declarado y no como bug pendiente:

1. El suelo scrypt hace inviable la fuerza bruta de una contraseña larga aunque el backoff se
   resetee.
2. **Encender la mitad `ip:` tras la medición de XFF cierra el caso de UNA IP** (ronda de
   verificación, S2-M1): `panel_puerta` comprueba el bloqueo ANTES de podar o sembrar, así que un
   intento cuya clave `ip:` ya está cerrada **no toca la tabla** — ni crea la fila `u:` nueva ni
   dispara la poda. Con `ip:` contando, un atacante desde una IP fija se bloquea a sí mismo y deja
   de inflar. (Antes del reorden la siembra iba primero y el bypass sobrevivía a `ip:`; se
   corrigió realineando la RPC con el doble en memoria.)

   **Lo que `ip:` NO cierra**, y hay que decirlo: un botnet con IPs rotatorias y usuarios frescos
   no bloquea ninguna clave, así que sigue pudiendo inflar el cap. Es el límite estructural del
   cerrojo por-IP, ya declarado en `dashboard/auth.py` («un botnet con mil direcciones»): contra
   un ataque verdaderamente distribuido la defensa es el suelo scrypt sobre una contraseña larga,
   no el cerrojo. El cap mantiene la tabla acotada; no promete preservar todos los bloqueos vivos
   bajo un ataque distribuido.

El gate de XFF no es opcional, pero tampoco es una bala de plata contra el desalojo. Si el patrón
se observara, la respuesta es subir el cap, adelantar la medición de XFF, o —si un botnet lo
explotara— endurecer aguas arriba (rate-limit del borde), no un parche en la RPC.

## Por qué Vercel — y en PROYECTO PROPIO

Decisión de Alberto (17-ago; **matizada el 19-ago, DEC-244**). Antes se había fijado «servicio
aparte en Railway» (DEC-231 §2), y Vercel lo mejora en tres cosas: es donde ya vive el war room,
así que comparte **cuenta** y forma de configurar credenciales; **no se paga por tenerlo
encendido** (un panel que se abre unas veces al día no justifica un contenedor 24/7); y
**mantiene intacta la decisión de seguridad**, porque las funciones corren en el servidor y la
clave de Supabase sigue sin llegar al navegador. Eso último es lo que separa esta opción de la
alternativa «SPA que habla con Supabase», que exigiría escribir políticas RLS desde cero y
convertirlas en la única barrera.

**PROYECTO PROPIO, no el del war room (Alberto, 19-ago — DEC-244)**: el panel se despliega como
un proyecto de Vercel NUEVO apuntando a ESTE repo, con su URL propia. La frase original
«comparte dominio» queda superada: comparten cuenta de Vercel y nada más — dos proyectos, dos
URLs, dos juegos de variables, dos superficies de fallo. El código no nota la diferencia
(verificado al decidirlo): el check de Origin compara contra el `host` de la propia petición, la
cookie es host-only (sin `Domain=`), y `vercel.json` no nombra proyecto ni dominio.

**Crear el proyecto** (una vez): Vercel → Add New Project → importar `technical_bot` (root del
repo, framework «Other» — `vercel.json` ya trae runtime, región y rewrites) → poner las
variables de la tabla de abajo EN ESE proyecto → deploy. La URL resultante (la
`*.vercel.app` del proyecto, o el dominio propio que se le asigne) es la del panel.

## El cerrojo en serverless — RESUELTO en s324j (histórico abajo)

**La opción (1) está cableada** (DEC-239, tras seis rondas de dúo sobre el diseño y una sobre el
diff): el contador vive en `panel_intentos` y la admisión entera es UNA transacción en la base
(`panel_puerta`, migración 019) — contar AL admitir acota el rebaño concurrente que
«comprobar→scrypt→registrar» dejaba pasar. `api/index.py` enchufa `CerrojoSupabase`; en local y
en tests sigue el de memoria. **Matiz vigente**: hasta la medición de XFF, el cerrojo distribuido
cuenta y bloquea SOLO por usuario (la clave `ip:` está apagada — gate de arriba); la contraseña
larga generada (20+ del gestor) sigue siendo higiene recomendada, ya no condición.

<details><summary>Histórico (17-ago): el análisis que llevó a (1)</summary>
El cerrojo en memoria («si Railway reinicia, los contadores se van») era casi decorativo en
serverless: cada intento puede caer en una instancia distinta. Defensa restante: scrypt (~170 ms
por intento, medido) + longitud de contraseña. La opción 2 (contraseña larga como condición de
despliegue) fue el puente hasta cablear (1).
</details>

## Configuración

Variables de entorno en Vercel:

| Variable | Qué es | Cómo se obtiene |
|---|---|---|
| `DASHBOARD_SECRET` | Firma de la cookie de sesión. Rotarla **cierra todas las sesiones**: es el botón de pánico ante una cookie robada | `python -c "import secrets;print(secrets.token_urlsafe(32))"` |
| ~~`DASHBOARD_USUARIOS`~~ | **NO va en Vercel (s324j, a2/DEC-239)**: la lista vive en `panel_usuarios` y revocar es un UPDATE, no un redespliegue. La variable queda SOLO para el modo local (`python -m dashboard`, `BackendEntorno`): `usuario:registro` separados por `;` o salto de línea — no por coma (dúo r41) | Local: `python scripts/s324f_dashboard_password.py`. Producción: `python -m scripts.s324j_panel_usuario alta <usuario>` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | La base del **bot** (no la del war room) | Las mismas que usa Railway |
| `DASHBOARD_SESION_HORAS` | Opcional. Duración de la sesión; por defecto 8 h | — |

**Mismas credenciales que el war room, dos logins.** El war room identifica al admin con
`ADMIN_EMAIL_n` + `ADMIN_PASS_HASH_n` (bcrypt) en variables de Vercel. El panel del bot usa el
mismo email y la misma contraseña, pero con **su propio hash** (scrypt) — que en producción vive
en la fila de `panel_usuarios` (s324j/DEC-239), NO en una variable de Vercel (esa era la lista en
`DASHBOARD_USUARIOS`, retirada de producción con a2). Se teclea lo mismo en los dos sitios y no
viaja ningún secreto entre proyectos, que son dos bases de datos y dos audiencias distintas.
Sesión única real (SSO) exigiría compartir el secreto de NextAuth y un dominio raíz común —
factible, más acoplamiento del que compra hoy, y la pieza de autenticación es enchufable si algún
día se quiere.

## Ficheros

- `api/index.py` — el punto de entrada que Vercel descubre. Una línea: importa `app`. El panel no
  sabe que está en Vercel.
- `vercel.json` — región y runtime.
- `api/requirements.txt` — **el que Vercel instala** (el builder Python prefiere el que vive
  junto al entrypoint): SOLO `httpx` y `python-dotenv`, la clausura transitiva real de la
  superficie del panel. Existe porque el primer deploy (19-ago) murió instalando el
  `requirements.txt` de la raíz — el del bot entero — con «bundle size 541.43 MB > 500 MB».
  Lo vigila `tests/test_s324j_panel_requirements.py`: un tercero nuevo en `api/`/`dashboard/`
  sin declararlo ahí (o uno declarado de más) pone la suite en rojo antes que el deploy.
- `requirements.txt` (raíz) — sigue siendo el del BOT (Railway); el panel no lo usa en Vercel.

## Verificación después de desplegar

1. Abrir la URL **sin sesión**: debe redirigir a `/entrar` **con el cuerpo vacío** — ni el
   esqueleto de la página protegida.
2. Entrar con las credenciales y comprobar que se ven las cuatro pantallas.
3. En el navegador, ver el código fuente de cualquier página y buscar `SUPABASE`: **no debe
   aparecer nada**. Es la comprobación de que la clave no llegó al cliente.
4. Cerrar sesión y volver a la URL protegida: debe redirigir otra vez.

Los cuatro puntos están cubiertos por tests, pero la comprobación en el despliegue real es la que
vale: los tests prueban el código, no la configuración.

## Límites conocidos de Vercel para este panel

- **Tiempo de función**: las consultas van a vistas SQL ya agregadas y responden rápido, pero si
  alguna creciera, el corte de la plataforma la mataría a mitad. Si pasa, se verá como una página
  en blanco, no como un error claro.
- **Arranque en frío**: la primera visita del día tarda un poco más. Irrelevante para este uso.
- **Escrituras**: las tres acciones del panel (invitar, anular, revocar) son sentencias sueltas
  contra Supabase; no dependen de que el proceso siga vivo después de responder.
