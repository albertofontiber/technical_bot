# s324f — Panel web del bot: gestión de acceso + métricas (propuesta v1)

**Estado (17-ago)**: **construido y verificado en rama; NADA desplegado, NADA commiteado**.
Suite **4317 passed, 46 skipped** (baseline 4192 + 125 tests nuevos). Impacto **ALTO**:
servicio nuevo expuesto a internet con datos personales detrás. **Levers**: ninguno medido —
esto no toca retrieval ni generación. Pendiente: dúo adversarial, revisión del autor, deploy.

---

## 1. Recomendación

**Un servicio ASGI de siete rutas, renderizado en el servidor, en `dashboard/`.**

- **Dónde vive**: paquete `dashboard/` de primer nivel, hermano de `src/` — no dentro. `src/`
  es el árbol del BOT y su censo de módulos es un trinquete anti-acreción; el panel es una
  SEGUNDA aplicación sobre los mismos datos. La flecha va sólo panel→`src`, y eso **lo
  garantiza el CI**: `dashboard` entra en `RAICES_PROHIBIDAS` del contrato de imports, así que
  un `import dashboard` dentro de `src/` pone la suite roja. Es DEC-231 §2 («si el panel cae,
  el bot sigue») convertida en invariante, no en disciplina.
- **Autenticación enchufable** (DEC-231 §3): todo llama a
  `auth.autenticar(usuario, contraseña) -> Usuario | None`. Hoy detrás hay `BackendEntorno`
  (usuarios y hashes en una variable de Railway); el día que sepamos qué es el login del war
  room se escribe otro backend y **no se toca ni una ruta**. Hay un test que sustituye el
  backend para probar justo eso.
- **`scrypt` de la biblioteca estándar** (`n=2¹⁵, r=8, p=1` ≈ 32 MiB y 173 ms medidos en el
  smoke), con sal por usuario y **los parámetros dentro del propio registro**: subir el coste
  mañana no invalida los hashes de hoy, y los tests usan parámetros baratos sin tocar los de
  producción. Cero dependencias nuevas.
- **Sesión sin estado**: cookie firmada con HMAC-SHA256, `HttpOnly` + `Secure` +
  `SameSite=Strict`, caducidad **verificada en el servidor** (el `Max-Age` es una cortesía
  para el navegador). Rotar `DASHBOARD_SECRET` cierra **todas** las sesiones al instante: ése
  es el botón de pánico ante una cookie robada, y es lo que permite no montar una tabla de
  sesiones para dos personas.
- **Escritura protegida por dos capas**: token CSRF ligado a la sesión **y** comprobación de
  origen. La segunda existe porque la primera no puede cubrir el formulario de entrada (aún no
  hay sesión que ligar): el login CSRF muere en el control de origen.
- **Nada sin sesión**: `RUTAS_PUBLICAS` tiene dos entradas y las dos son la pantalla de login.
  El test que lo comprueba **recorre la tabla de rutas real**, así que una ruta nueva que
  alguien añada mañana entra sola en el test.
- **Reutiliza, no reimplementa**: `src.bot.access` para el vocabulario del token y el estado
  derivado de una invitación; `scripts.s324e_bot_errores_insights.agregar` tal cual para los
  errores; las 7 vistas SQL se **leen**, no se recalculan.
- **Un arreglo de raíz**: `_estado_invitacion` era privado del CLI. Con el panel había dos
  lectores de las mismas filas, así que sube a la hoja pura como `access.estado_invitacion`,
  con tests. Sin eso, CLI y panel podían discrepar sin que nada se pusiera rojo.

## 2. Alternativas consideradas y por qué se descartan

- **FastAPI** (ya declarado en `requirements.txt`, así que era «gratis»). Descartada por: (a)
  no está instalado en el entorno, y una suite que no corre en limpio incumple el Protocolo 1
  — los tests actuales corren **sin instalar nada**; (b) quien parsea HTTP es **uvicorn en los
  dos casos**, el framework sólo enruta siete rutas de igualdad exacta; (c) trae `/docs`
  autogenerado, superficie pública en un panel donde nada debe responder sin sesión. **El
  precio, declarado**: ~60 líneas de enrutado, cookies y formulario escritas a mano. Si el
  panel creciera (subidas, API, roles), lo correcto sería cambiarla — y es un fichero.
- **SPA + PostgREST desde el navegador**: exige RLS por usuario para un panel de dos personas
  y acerca la clave de servicio al cliente. DEC-231 §1 ya lo cerró.
- **argon2 / bcrypt**: ruedas compiladas, superficie de supply-chain y un fallo de build más
  en el despliegue, a cambio de nada medible frente a scrypt aquí.
- **Tabla de sesiones en Supabase**: compra poder matar UNA sesión; cuesta migración, job de
  limpieza y una consulta a Supabase en CADA petición. La rotación del secreto cubre el caso
  real (cookie robada) sin nada de eso.
- **Jinja2**: su autoescapado no es el default de la librería. Aquí la garantía es un tipo
  (`Seguro`): lo no marcado se escapa, y olvidar el marcador falla hacia el lado seguro.
- **Consultas SQL nuevas**: si una pregunta no la responde una vista, se dice — no se escribe
  una consulta paralela que mañana diverja de la que Alberto mira desde Supabase.

## 3. Gaps y riesgos declarados

1. **La superficie nueva es real y es el coste que DEC-183 no quiso pagar.** Una contraseña
   filtrada da acceso a la pantalla de Acceso: identificadores de Telegram y nombres.
   Mitigación escrita, no automática: rotar `DASHBOARD_SECRET`.
2. **El cerrojo permite un bloqueo dirigido**: contar fallos por usuario deja que alguien
   bloquee a `alberto` 15 minutos escribiendo su nombre. Es el lado bueno del intercambio —
   contar sólo por IP regala el ataque distribuido — pero es un precio, no un detalle.
3. **`X-Forwarded-For`**: se toma el último salto, que es correcto con **exactamente un proxy
   de confianza** (Railway). Si mañana hay CDN, hay que contar saltos.
4. **Emitir invitación no es POST-redirect-GET**: el enlace se enseña una vez y no puede viajar
   en una URL. F5 emite una invitación de más — visible y anulable, pero es fricción real.
5. **`/metricas` hace 7 lecturas secuenciales** (~1 s contra Supabase real). Sin paralelizar a
   propósito; si molesta, se mide y se arregla.
6. **El cerrojo y la sesión son estado de proceso**: con dos réplicas en Railway, los contadores
   no se comparten. Para dos usuarios no paga coordinarlos; **desplegar con una sola réplica**.
7. **`dashboard/errores.py` importa de `scripts/`**. Es reutilización deliberada de la función
   pura, pero es una aplicación importando una herramienta. Retiro declarado: si el panel pasa
   a ser el consumidor principal, `agregar` se gradúa a módulo propio.
8. **Sin healthcheck posible**: no hay endpoint anónimo. En Railway, dejarlo sin configurar (o
   apuntarlo a `/entrar`).
9. **Lo NO verificado**: no se ha probado ninguna ESCRITURA contra Supabase real (prohibido en
   este encargo) — emitir y revocar están ejercitados con dobles y contra los mismos endpoints
   que usa el CLI ya probado, pero eso es una inferencia, no una observación.

## 4. Por qué es BP, estructural y escalable

**BP**: nada sin sesión, hash memory-hard, cookie firmada y endurecida, CSRF en dos capas, CSP
sin JavaScript posible, `no-store` en toda respuesta, secreto que no llega al navegador — con
un test por cada afirmación. **Estructural**: las cabeceras de seguridad se aplican en la capa
de transporte y no en cada manejador (la primera versión las ponía en quien construía la
página y **las redirecciones salían desnudas** — incluida la que lleva la cookie de sesión; lo
cazó su propio test, y la corrección fue mover el punto, no parchear las llamadas). Lo mismo
con el escapado (un tipo, no disciplina) y con la frontera bot↔panel (CI, no convención).
**Escalable**: sustituir la autenticación es cambiar un objeto; añadir una vista es una fila de
datos; una columna nueva aparece sola y una que falte no rompe la página.
