# Panel del bot — cómo se despliega (y qué falta antes)

> **Estado (17-ago-2026)**: el panel está **construido, probado y sin desplegar**. Este documento
> es el runbook para ponerlo en Vercel, más lo que hay que arreglar antes de exponerlo.

## Por qué Vercel

Decisión de Alberto (17-ago). Antes se había fijado «servicio aparte en Railway» (DEC-231 §2), y
Vercel lo mejora en tres cosas: es donde **ya vive el war room**, así que comparte cuenta, dominio
y forma de configurar credenciales; **no se paga por tenerlo encendido** (un panel que se abre unas
veces al día no justifica un contenedor 24/7); y **mantiene intacta la decisión de seguridad**,
porque las funciones corren en el servidor y la clave de Supabase sigue sin llegar al navegador.
Eso último es lo que separa esta opción de la alternativa «SPA que habla con Supabase», que exigiría
escribir políticas RLS desde cero y convertirlas en la única barrera.

## Lo que hay que arreglar ANTES de exponerlo — no es opcional

**El cerrojo contra fuerza bruta cuenta en memoria del proceso.** `dashboard/auth.py::Cerrojo`
guarda los intentos fallidos en un diccionario; su docstring ya declaraba el precio («si Railway
reinicia, los contadores se van con él»). En serverless es peor: **cada intento puede caer en una
instancia distinta**, así que la espera creciente casi no llega a aplicarse. Lo que queda de
defensa es `scrypt` (~170 ms por intento, medido) y la longitud de la contraseña.

Opciones, por orden de preferencia:

1. **Mover el contador a Supabase** — una tabla pequeña (`clave`, `fallos`, `ultimo`) y dos
   sentencias en el camino del login. Es lo correcto y es lo que hay que hacer, pero **toca
   autenticación**, así que va con dúo adversarial antes de cablearse (Protocolo 3).
2. **Contraseña larga generada** (20+ caracteres de un gestor) y aceptar el hueco **declarado**
   mientras el panel sea de dos personas. Con esa entropía, 170 ms por intento hace inviable la
   fuerza bruta aunque el cerrojo no cuente.

Mientras no esté (1), **la opción 2 es una condición de despliegue, no una recomendación**.

## Configuración

Variables de entorno en Vercel:

| Variable | Qué es | Cómo se obtiene |
|---|---|---|
| `DASHBOARD_SECRET` | Firma de la cookie de sesión. Rotarla **cierra todas las sesiones**: es el botón de pánico ante una cookie robada | `python -c "import secrets;print(secrets.token_urlsafe(32))"` |
| `DASHBOARD_USUARIOS` | `usuario:registro` separados por **`;`** o por salto de línea — **no por coma**, que ya vive dentro de los parámetros del registro (`n=32768,r=8,p=1`) y partirla trocearía cada hash (dúo r41: la guía decía «coma» y seguirla rompía el arranque multiusuario). El registro lleva el algoritmo y sus parámetros dentro | `python scripts/s324f_dashboard_password.py` — pide la contraseña por consola, imprime el registro y **no guarda nada** |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | La base del **bot** (no la del war room) | Las mismas que usa Railway |
| `DASHBOARD_SESION_HORAS` | Opcional. Duración de la sesión; por defecto 8 h | — |

**Mismas credenciales que el war room, dos logins.** El war room identifica al admin con
`ADMIN_EMAIL_n` + `ADMIN_PASS_HASH_n` (bcrypt) en variables de Vercel. El panel del bot usa el
mismo email y la misma contraseña, pero con **su propio hash** (scrypt) en su propia variable: se
teclea lo mismo en los dos sitios y no viaja ningún secreto entre proyectos, que son dos bases de
datos y dos audiencias distintas. Sesión única real (SSO) exigiría compartir el secreto de NextAuth
y un dominio raíz común — factible, más acoplamiento del que compra hoy, y la pieza de
autenticación es enchufable si algún día se quiere.

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
