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

## Riesgo declarado del cerrojo: el desalojo del cap es forzable (dúo del cableado, F-M1)

`panel_puerta` siembra una fila `u:<hmac>` por cada intento de login ANTES de comprobar
credenciales, y la poda del cap (`CERROJO_MAX_ENTRADAS = 10.000`) borra las filas más antiguas.
Consecuencia, heredada del cerrojo en memoria y ahora declarada: un atacante que mande ~10.000
logins con usuarios inventados **distintos** llena la tabla y expulsa la fila de bloqueo de un
usuario concreto, cuyo backoff se resetea (renace con `fallos = 0`). No es gratis para el
servidor —cada intento paga el señuelo scrypt (~100 ms), así que 10.000 son también un coste de
CPU—, pero sí barato para el atacante. Dos cosas lo acotan, y por eso van aquí y no como bug:
(1) el suelo scrypt sigue haciendo inviable la fuerza bruta de una contraseña larga aunque el
backoff se resetee; (2) **encender la mitad `ip:` tras la medición de XFF lo mitiga de raíz** —
con la clave por IP contando, el atacante acumula su propio bloqueo mientras infla las `u:`. Es
un refuerzo más de que el gate de XFF no es opcional. Si el patrón se observara en producción, la
respuesta es subir el cap o adelantar la medición de XFF, no un parche.

## Por qué Vercel

Decisión de Alberto (17-ago). Antes se había fijado «servicio aparte en Railway» (DEC-231 §2), y
Vercel lo mejora en tres cosas: es donde **ya vive el war room**, así que comparte cuenta, dominio
y forma de configurar credenciales; **no se paga por tenerlo encendido** (un panel que se abre unas
veces al día no justifica un contenedor 24/7); y **mantiene intacta la decisión de seguridad**,
porque las funciones corren en el servidor y la clave de Supabase sigue sin llegar al navegador.
Eso último es lo que separa esta opción de la alternativa «SPA que habla con Supabase», que exigiría
escribir políticas RLS desde cero y convertirlas en la única barrera.

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
- `requirements.txt` — el del repo; el panel sólo necesita `httpx` y `python-dotenv` (medido: no
  arrastra anthropic, voyage ni telegram).

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
