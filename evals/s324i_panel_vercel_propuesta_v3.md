# s324i v3 — El panel a Vercel: los diez defectos de la v2, cerrados uno a uno

> **Punto de partida (DEC-237)**: (a2) adjudicado por Alberto — `techassistant.fontiber.com`,
> los usuarios salen de las variables de entorno y pasan a Supabase. La v2 tenía «la estructura
> correcta y diez defectos enumerados» (Sol, r2: 3 críticos + 7 medios,
> `evals/adversarial_reviews/2026-08-18T23-50-06_gpt-5.6-sol_f4fe2c8a0f33.md`). Esta v3 existe
> para cerrar los diez; lo que la v2 ya tenía bien (fail-closed en la identidad, alcance
> lee-no-gestiona, §métricas, §XFF) se conserva y se dice dónde.
>
> **Regla de la sesión**: diseño, dúo, y NO cablear. «No desplegar hasta que la v3 sea SÓLIDO.»

---

## 0. Los diez de la v2 → dónde queda cada uno

| # | Defecto (Sol r2, con su ancla) | Cierre |
|---|---|---|
| C1 | Tablas de credenciales sin RLS/FORCE/REVOKE/GRANT mínimo ni gate ACL (`migrations/016:266-292` ya escribía el patrón) | §1.2 + puerta 9 |
| C2 | El contrato del digest `h` es irrealizable con `vigente()` (`auth.py:186-190`: `Usuario` sólo lleva `nombre`) | §2 (el `sello`) |
| C3 | `HMAC(usuario\|ip)` fusiona dos claves que el cerrojo cuenta por separado (`auth.py:363`) | §3.1 (dos filas, dos claves) |
| M1 | Incremento exacto ≠ admisión atómica: el rebaño pasa la comprobación antes de que nadie registre | §3.2 (contar la admisión, no el fallo) |
| M2 | PRG pierde el enlace único (tras el 303 no hay de dónde reconstruirlo) | §4.1 (sin PRG: se conserva el render del POST) |
| M3 | Clave de idempotencia por contenido confunde reintento con operación intencional | §4.2 (token por formulario, no por payload) |
| M4 | PostgREST no puede expresar `fallos = fallos + 1` (`gestion.py:82-112` sólo envía JSON) | §3.3 (RPC endurecida) |
| M5 | La poda temporal no acota tamaño; se perdió el techo duro (`auth.py:295,343-357`) | §3.4 (cap duro en la propia función) |
| M6 | HMAC con clave conservada es SEUDONIMIZACIÓN; el canon ya rechaza el framing (`RGPD_RETENCION.md:67-75`) | §6 (declarado como tal + matriz + plazo) |
| M7 | El backend nuevo no preserva el señuelo scrypt → reabre el oráculo de enumeración (`auth.py:197-203`) | §5 + puerta 6 |

---

## 1. Los usuarios a Supabase

### 1.1 La tabla — con las lecciones dentro, no en la prosa

```sql
CREATE TABLE public.panel_usuarios (
    usuario      TEXT PRIMARY KEY
                 CHECK (usuario = lower(btrim(usuario)) AND usuario <> ''),
    registro     TEXT NOT NULL CHECK (registro LIKE 'scrypt$%'),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    alta_por     TEXT NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocado_en  TIMESTAMPTZ,
    revocado_por TEXT
);
```

Dos CHECK que no son adorno: el de `usuario` impone en el TIPO la normalización que
`_normalizar_usuario` hace en Python (`auth.py:205-206`) — una fila `Alberto` no puede existir y
por tanto no puede dejar de encontrarse; el de `registro` corta EN LA BASE el error que
`validar_configuracion` caza hoy en el arranque (`auth.py:399-409`): pegar la contraseña en claro
donde iba el hash. Es la misma clase de fallo, movida del código al esquema.

**Alta y revocación siguen fuera del panel** (alcance v1 de la v2, conservado): el registro lo
genera `scripts/s324f_dashboard_password.py` (que no guarda nada) y el INSERT/UPDATE lo ejecuta
un script de operación con la service key — el mismo patrón que el CLI de invitaciones. Revocar =
`UPDATE ... SET activo = FALSE, revocado_en = now(), revocado_por = ...`. Efectivo en la
siguiente petición (§2). Baja LÓGICA, sin DELETE: misma disciplina y mismo motivo que
`bot_allowlist` (`migrations/016:230-234` — conservar la traza; la supresión a petición va
aparte, §6).

### 1.2 La frontera de la 016, aplicada — el crítico C1

La migración nueva (`migrations/019_panel_usuarios_cerrojo.sql`) lleva, para CADA tabla nueva, el
patrón exacto de `migrations/016:266-292`:

```sql
ALTER TABLE public.panel_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.panel_usuarios FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE public.panel_usuarios
    FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT (usuario, registro, activo) ON public.panel_usuarios TO service_role;
GRANT INSERT (usuario, registro, activo, alta_por)
    ON public.panel_usuarios TO service_role;
GRANT UPDATE (registro, activo, revocado_en, revocado_por)
    ON public.panel_usuarios TO service_role;
```

- El **SELECT es por columnas**: el camino de autenticación sólo puede leer
  `usuario, registro, activo`. `alta_por`/`creado_en`/`revocado_*` no viajan a PostgREST porque
  ningún camino del panel los necesita — lo que no se trae no se puede filtrar
  (la regla de `gestion.py:115-122`).
- Las **columnas de auditoría no están en ningún GRANT de escritura**: `creado_en` la pone su
  DEFAULT y nadie puede reescribir por REST ni `usuario`, ni `alta_por`, ni `creado_en` — la
  traza de quién dio el alta no es editable con la credencial del panel.
- **INSERT/UPDATE existen para el script de operación**, no para el panel: el código del panel no
  escribe en esta tabla. El **LÍMITE de la 016 aplica igual y se declara igual**
  (`migrations/016:270-276`): panel y script comparten `SUPABASE_SERVICE_KEY`, así que los
  privilegios no separan «panel» de «operador» — eso lo separa el código; lo que sí impiden es lo
  que ninguno debe poder hacer (DELETE, y leer columnas de más por REST).
- **Sin DELETE**: la baja es lógica; la supresión a petición la ejecuta el operador aparte, a la
  vista (§6).

`panel_intentos` (§3) lleva el mismo bloque con una diferencia razonada: ahí `service_role` SÍ
recibe `DELETE`, porque borrar ES parte del contrato de esa tabla (poda y `acierto`), y no hay
nada que conservar — al revés que en las tablas con traza.

**El gate ACL es un test, no una intención** (puerta 9): igual que
`tests/test_s277_p1_document_local_snapshot_v2_acl.py` fija el texto de su migración, un test
nuevo afirma que la 019 contiene RLS+FORCE y el REVOKE para cada tabla nueva, y el
`REVOKE ALL ON FUNCTION` + `GRANT EXECUTE ... TO service_role` de la RPC (§3.3). Si alguien
añade una tabla al panel sin frontera, la suite lo dice.

### 1.3 El precio de (a2) — fail-closed, y SIN mentir en la pantalla

**Si Supabase no responde, nadie entra.** Fail-closed en la identidad, fail-open sólo en el
contador (§3.5). Sin fallback a la variable de entorno: quien pueda tirar la base no recupera al
usuario revocado.

Con un matiz que la v2 no tenía y que el contrato `Usuario | None` no puede expresar: «no
existe/contraseña mala» y «no he podido comprobarlo» son respuestas DISTINTAS, y aplanarlas en
`None` haría que un usuario legítimo viera «Usuario o contraseña incorrectos» durante una caída —
una mentira. El backend gana una excepción declarada, `IdentidadNoDisponible` (sólo la lanza el
transporte, nunca una credencial mala): la ruta de entrada responde 503 «el panel no puede
comprobar identidades ahora mismo» — un estado del servicio igual para todo el mundo, sin señal
por-usuario y sin contar el intento en el cerrojo (no hubo intento contra una credencial).
`BackendEntorno` no la lanza nunca; los dobles no cambian. Y para los que están DENTRO, la misma
distinción en `sello()`: `None` (revocado/cambiada) → fuera; `IdentidadNoDisponible` → 503 sin
servir NINGÚN dato y sin matar la cookie — fail-closed intacto (con la base caída no se enseña
nada), sin convertir un timeout en un cierre de sesión falso, y el revocado durante la caída ve
el mismo 503 que todos hasta que la base vuelva y `sello()` lo expulse.

## 2. La revalidación que SÍ se puede construir: el `sello` — el crítico C2

La v2 pedía un digest `h` en la cookie y una `vigente(nombre) -> Usuario | None` que no podía ni
crearlo ni compararlo, porque `Usuario` sólo lleva `nombre` (`auth.py:175-183`). Se rediseña el
contrato, no la prosa:

```python
@dataclass(frozen=True)
class Usuario:
    nombre: str
    sello: str = ""          # opaco; "" = backend sin revalidación (los dobles viejos siguen valiendo)

class Backend(Protocol):
    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None: ...
    def sello(self, nombre: str) -> str | None: ...
```

- **`sello(nombre)`** devuelve el sello VIGENTE de un usuario activo, `None` si no existe o está
  revocado, y lanza `IdentidadNoDisponible` si el transporte no responde (§1.3: `None` expulsa,
  la excepción es un 503 que no sirve nada y no mata la cookie). El sello es
  `b64(sha256(registro)[:12])`: cambia exactamente cuando cambia la contraseña.
- **Al entrar**: `autenticar` lee la fila UNA vez, verifica scrypt y devuelve
  `Usuario(nombre, sello)` — sin segunda lectura ni ventana entre leer y sellar. El payload de la
  cookie pasa de `{u, csrf, iat, exp}` (medido en `sesion.py:8`) a llevar también `h = sello`.
- **En cada petición**, la puerta (`despachar`, tras `sesion.verificar`) añade UNA comprobación:
  `backend.sello(u)` es `None` → fuera; distinto de `h` (comparado con `hmac.compare_digest`,
  la disciplina de `sesion.py:160-167`) → fuera. Revocar y cambiar la contraseña expulsan en la
  **siguiente petición** — que es la promesa por la que Alberto eligió (a2).

**Por qué `h` puede viajar en una cookie firmada y no cifrada** (el contrato de
`sesion.py:23-27` es «no meter material sensible», no «cifrar»): el sello es un truncado de
SHA-256 sobre un registro que contiene una sal aleatoria de 16 bytes (`auth.py:71,117`) — no es
invertible, no permite diccionario (la sal no se conoce) y no sirve para entrar. Lo único que
revela es «la credencial cambió», que es su función.

**`BackendEntorno` implementa `sello` igual** (digest del registro de la variable), así que la
paridad de la v2 §1.2 se mantiene: los dobles y el modo local siguen funcionando, y la
sustitución es un backend más, no una excepción. Los dobles de los tests ganan el método; el
campo nuevo de `Usuario` tiene default, así que ningún constructor existente se rompe.

**Propiedad ganada que hoy no existe**: cambiar la contraseña de UN usuario mata SUS sesiones
robadas. Hoy el único botón es rotar `DASHBOARD_SECRET`, que expulsa a todos (`sesion.py:12-15`).
El botón global se conserva; aparece el fino.

**Precio declarado**: una lectura a Supabase por petición (las páginas ya hacen varias:
`datos.salud()` hace dos — `datos.py:293-297`); y al desplegar esto, las cookies vivas no llevan
`h` → una re-entrada forzada, una vez (la sesión dura 8 h como mucho, `sesion.py:50`).

**Enumeración**: `sello()` no necesita señuelo — sólo recibe nombres que ya pasaron una firma
HMAC válida (la cookie), no entrada del atacante. El señuelo vive donde vive el ataque:
`autenticar` (§5).

## 3. El cerrojo, distribuido sin debilitarse — C3, M1, M4, M5

### 3.1 Dos claves, dos filas — el crítico C3

El cerrojo vigente cuenta usuario e IP por SEPARADO y cierra si UNA cierra
(`auth.py:277-283, 324-326`): sólo-por-IP regala el ataque distribuido; sólo-por-usuario deja que
cualquiera bloquee a Alberto. La v2 fusionaba las dos en una clave y rompía ambas mitades. La v3
conserva la estructura EXACTA de `claves_de` (`auth.py:363-364`) — dos claves con su espacio de
nombres — y seudonimiza el identificador, no la estructura:

```
u:<hmac>   donde hmac = HMAC-SHA256(K, usuario)        (troncado, b64)
ip:<hmac>  donde hmac = HMAC-SHA256(K, ip)
K = HMAC-SHA256(DASHBOARD_SECRET, "panel_intentos:v1")   # clave DERIVADA, no el secreto a pelo
```

Cada intento fallido escribe DOS filas; `bloqueado` es el máximo de las dos esperas. Rotar IP ya
no da intentos ilimitados contra un usuario (su fila `u:` sigue contando); rotar usuario no
esquiva el límite de una IP (su fila `ip:` sigue contando). La clave se deriva con etiqueta de
propósito para no reutilizar el secreto de firma de cookies en otro rol.

```sql
CREATE TABLE public.panel_intentos (
    clave  TEXT PRIMARY KEY,
    fallos INTEGER NOT NULL DEFAULT 0 CHECK (fallos >= 0),
    ultimo TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_panel_intentos_ultimo ON public.panel_intentos (ultimo);
```

### 3.2 Contar la ADMISIÓN, no el fallo — el medio M1

Sol tenía razón: con «comprobar → scrypt → registrar el fallo», N peticiones concurrentes pasan
la comprobación antes de que ninguna registre, y el umbral no bloquea nada. El arreglo no es una
transacción alrededor: es **mover el contador al momento de la admisión**. El contrato del
cerrojo cambia de tres métodos a dos:

```python
admitir(claves) -> float   # 0.0 = adelante — y el intento YA está contado
acierto(claves) -> None    # un login bueno borra las filas (la devolución del provisional)
```

`admitir` es UNA función en la base (§3.3) que, en una sola transacción: poda lo caducado, toma
las filas de las claves **en orden estable y con `FOR UPDATE`** (dos llamadas concurrentes se
serializan sobre las mismas filas, sin interbloqueo), calcula la espera con la fórmula de hoy
(`auth.py:313-322`: `min(base·2^(fallos-libres-1), max)` desde `ultimo`); si alguna clave está
cerrada devuelve la espera **sin escribir** (hoy un intento bloqueado tampoco suma —
`app.py:285-292` corta antes de `fallo`); si no, incrementa las dos y devuelve `0.0`.

- **El rebaño queda acotado**: la petición concurrente K ve los K−1 incrementos anteriores
  (el `FOR UPDATE` la hizo esperar), así que con `FALLOS_LIBRES = 4` entran ~5, no N. Es la
  semántica que el umbral prometía.
- **La secuencia no cambia**: para intentos uno detrás de otro, «contar al admitir y comprobar el
  estado previo» produce exactamente los mismos bloqueos que el cerrojo de hoy (el intento k ve
  `fallos = k−1`, igual que ahora; el sexto intento de una tanda fallida se bloquea en ambos).
  El doble en memoria lo prueba (puerta 4).
- **El reloj es `now()` de la base**, no `time.monotonic()` de una instancia serverless que nace
  y muere — relojes coherentes entre invocaciones gratis.
- **Precio declarado**: si el proceso muere entre `admitir` y `acierto`, el usuario carga un +1
  fantasma que decae solo (sólo pesa por encima de 4 fallos). Y un login bueno cuesta un DELETE
  más — nada, a esta escala.

El `Cerrojo` en memoria (`auth.py:304`) gana `admitir` con la misma semántica y se queda para el
modo local y los tests; `CerrojoSupabase` vive en un módulo nuevo `dashboard/cerrojo.py`. La
invariante de auditoría de `gestion.py:6-8` («TODAS las peticiones no-GET del panel están en este
fichero») se AMPLÍA en su propio docstring: las no-GET viven en `gestion.py` (las tres de
gestión) y en `cerrojo.py` (la RPC y el DELETE de `acierto`) — la propiedad se conserva
enumerable, no se erosiona en silencio.

### 3.3 La RPC, con el agujero histórico cerrado de entrada — el medio M4

`_escribir` sólo envía JSON a PostgREST (`gestion.py:82-112`) y PostgREST no expresa
`fallos = fallos + 1`: hace falta una función. Este repo ya RECHAZÓ una RPC una vez, con motivo:
`rgpd_quedan_identificados` nació ejecutable por `anon` (s296→s299) y el canje la descartó por
eso (`src/logging_db.py:798-809`). Aquí la RPC es INEVITABLE (no hay forma REST de la
lectura-modificación-escritura atómica), así que se construye con el patrón que el repo ya tiene
endurecido y gateado — `document_local_snapshot_v2`
(`supabase/migrations/20260722013000_...sql:157-158` + su ACL):

```sql
CREATE FUNCTION public.panel_puerta(
    claves text[], libres int, base_s numeric, max_s numeric,
    retencion_s numeric, cap int
) RETURNS numeric
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$ ... $$;

REVOKE ALL ON FUNCTION public.panel_puerta(text[], int, numeric, numeric, numeric, int)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.panel_puerta(text[], int, numeric, numeric, numeric, int)
    TO service_role;
```

- **`SECURITY INVOKER`**: la función no presta privilegios — corre como `service_role`, que ya
  tiene los suyos sobre `panel_intentos`. El fallo de s296 (una DEFINER que regala poderes a
  quien pueda ejecutarla) no puede reproducirse.
- **`REVOKE ... FROM PUBLIC`** explícito: las funciones nacen ejecutables por PUBLIC en Postgres;
  ese default ES el agujero de s296 y aquí se cierra en la misma migración, con el gate de texto
  de la puerta 9 encima.
- **Las constantes viajan como argumentos** desde `auth.py:286-295`: una sola fuente
  (`FALLOS_LIBRES`, `BLOQUEO_BASE_S`, `BLOQUEO_MAX_S`, el cap), sin copia en SQL que derive.
  La FÓRMULA sí vive en los dos lados (Python para el cerrojo local, SQL para el distribuido);
  la equivalencia la fija la tabla de casos de la puerta 4 — compartida por ambos — y el smoke
  post-deploy (§9). Gap declarado: no hay Postgres en la suite sin red (§11).
- **Transporte**: `cerrojo.py` hace `POST /rest/v1/rpc/panel_puerta` con el vocabulario de
  estados de `datos.leer` (ok · tabla_ausente · sin_credenciales · error). «Función aún no
  migrada» debe mapear a `tabla_ausente` — pendiente verificar al cablear el código exacto de
  PostgREST para función ausente (previsiblemente `PGRST202`; hoy `datos._CODIGOS_AUSENTE` no lo
  lista, `datos.py:49`).

### 3.4 El techo duro, recuperado — el medio M5

La poda temporal no acota nada: usuario e IP son entradas del atacante, que fabrica combinaciones
frescas más rápido de lo que caducan. El cerrojo en memoria ya tenía la respuesta
(`CERROJO_MAX_ENTRADAS = 10_000` y una poda en dos fases, `auth.py:295,343-357`); la función la
reproduce en el mismo orden y con el mismo racional: (1) borra lo caducado
(`ultimo < now() − retencion`); (2) si aún está al cap, sacrifica lo más antiguo (~10 %) —
«perder un bloqueo vivo regala una tanda de intentos; quedarse sin memoria regala el servicio»
vale igual cambiando memoria por tabla. El cap viaja como argumento; el índice sobre `ultimo`
hace ambas fases baratas. Consecuencia RGPD de regalo: la poda ES el plazo de retención (§6).

### 3.5 Indisponibilidad — conservado de la v2, con la frontera exacta

**Fail-open en el contador, fail-closed en la identidad.** Si la RPC no responde
(`error`/`tabla_ausente`/`sin_credenciales`), el intento se permite y scrypt sigue corriendo
(~100 ms de suelo, `auth.py:24-25,273`); un fallo de telemetría no puede dejar fuera al legítimo.
La frontera: fail-open SOLO ante fallo de transporte — una espera devuelta por la función JAMÁS
se ignora. Y la identidad va al revés: sin base no entra nadie (§1.3).

## 4. El enlace único — M2 y M3

### 4.1 Sin PRG: el render del POST se queda — el medio M2

Sol tenía razón otra vez: tras un 303, el GET no puede reconstruir un token que no está
almacenado en ninguna parte; un «canal flash» habría que guardarlo en algún sitio (cookie, tabla)
— y eso es persistir el secreto que la regla de `gestion.py:16-24` existe para no persistir. La
v3 retira el PRG de la emisión y CONSERVA lo que el código ya hace deliberadamente
(`app.py:730-735`): el enlace se enseña en la respuesta del POST que lo crea, una vez, nunca en
una URL. El problema que el PRG intentaba arreglar (el F5 reenvía el formulario) lo arregla §4.2
donde de verdad está: en no crear la segunda credencial.

### 4.2 Idempotencia por OPERACIÓN, no por contenido — el medio M3

La clave de la v2 (nota+días+operador+ventana) confundía un reintento con una segunda emisión
legítima: misma persona pidiendo dos invitaciones iguales en la misma ventana → bloqueada; el
mismo F5 cruzando la frontera de la ventana → duplicado. Se identifica **la petición**, no su
payload:

- El formulario de invitar lleva un campo oculto `op` — un token aleatorio
  (`secrets.token_urlsafe(16)`) generado al PINTAR el formulario.
- `bot_invitaciones` gana una columna `op TEXT UNIQUE` (nullable: las filas históricas no llevan;
  UNIQUE con NULLs múltiples). Migración `migrations/020_invitaciones_op.sql`, con su
  `GRANT INSERT (op)` añadido al grant por columnas de la 016.
- El POST inserta con su `op`. Un F5 reenvía el MISMO `op` → violación de UNIQUE (23505) → el
  panel responde «ya emitiste esta invitación: está en la lista. El enlace sólo se enseñó al
  crearla; si lo perdiste, anúlala y emite otra.» — sin crear nada y sin fingir que puede
  re-enseñar el enlace.
- Una segunda emisión INTENCIONAL sale de un formulario recién pintado → `op` nuevo → segunda
  fila. Dos pestañas = dos formularios = dos `op` = dos invitaciones — correcto, porque son dos
  operaciones.

`op` es ruido aleatorio sin dato personal; no entra en la matriz. Las otras dos escrituras del
panel no necesitan nada de esto: anular y revocar ya son idempotentes por su PATCH condicional
(`gestion.py:264-274, 295-301` — el segundo intento afecta 0 filas y lo dice).

## 5. El señuelo se conserva — el medio M7

`BackendSupabase.autenticar` hereda la disciplina de `BackendEntorno` (`auth.py:238-247`), no
solo su interfaz:

- **La entrada se acota ANTES de viajar en un filtro**: el nombre que llega del formulario se
  normaliza (`_normalizar_usuario`) y se valida contra un charset cerrado (minúsculas, dígitos y
  `._@-`, longitud acotada) ANTES de construir `usuario=eq.X` — los caracteres que la sintaxis de
  filtros de PostgREST trata como estructura (`,`, `(`, `)`…) no llegan a ella. Un nombre que no
  pasa el charset se trata como inexistente: señuelo y `None`, sin consulta. El mismo guard
  aplica al nombre que `sello()` saca de la cookie, aunque ése ya pasó una firma.
- **Una sola consulta**, por PK, con `activo` en el filtro
  (`usuario=eq.X&activo=is.true&select=usuario,registro&limit=1`): ausente e inactivo son LA
  MISMA respuesta vacía — el transporte no puede distinguirlos, así que el código tampoco puede
  filtrarlos por accidente.
- **Respuesta vacía o transporte caído → `verificar(contrasena, _SENUELO)` y `None`**
  (`auth.py:197-202`): el coste scrypt (~100 ms, dominante sobre el jitter de red) se paga en
  TODAS las ramas, y el mensaje de la página sigue siendo uno solo (`app.py:297-301`).
- **Puerta 6**: un test cuenta que `verificar` corre EXACTAMENTE una vez en las cuatro ramas
  (existe-y-acierta, existe-y-falla, no-existe, inactivo) — estructura, no cronómetro, que es lo
  único estable en CI.

## 6. RGPD: seudonimización DECLARADA, no anonimización vendida — el medio M6

El canon del proyecto ya dijo que un HMAC con clave conservada es seudonimización
(`docs/RGPD_RETENCION.md:67-75` descartó exactamente ese framing para los IDs de Telegram), y la
v2 lo vendía como «no es reversible → encaja con el RGPD». Se corrige el CLAIM, no la técnica:

- **`panel_intentos` es dato personal seudonimizado** (con `K` se puede recomprobar una IP o un
  usuario concreto; el espacio IPv4 es recorrible). El HMAC compra MINIMIZACIÓN — un volcado de
  la tabla no enseña IPs ni usuarios, y el panel nunca necesita recuperarlos — no una exención.
  Entra en la matriz de retención con fila propia: **plazo corto (la retención que la poda de
  §3.4 ya ejecuta en cada escritura)**, finalidad «seguridad del panel (control de fuerza
  bruta)», y una línea en el procedimiento de supresión del runbook para el caso residual (si el
  tráfico cesa, nadie poda: el operador ejecuta el DELETE del plazo — mismo modelo operador-a-la-vista
  que el resto de la retención del proyecto).
- **`panel_usuarios` es dato personal en claro** (nombres de usuario reales, quién dio el alta,
  cuándo): fila propia en la matriz, supresión a petición aparte de la baja lógica (como declara
  la 016 para la allowlist, `migrations/016:230-234`), y entra en el **paquete del abogado** —
  que DEC-231 ya exigía para el panel entero.
- La clave `K` es derivada con etiqueta de propósito (§3.1); rotar `DASHBOARD_SECRET` la rota
  también — las filas viejas quedan huérfanas e imposibles de recomprobar, y caducan por plazo.

## 7. Las métricas: columnas declaradas en los DOS sentidos — conservado de la v2 §4

Sin cambios de fondo respecto a la v2, con una honestidad añadida: esto INVIERTE una decisión
escrita. `datos.leer_vista` pide `select=*` A PROPÓSITO y su comentario explica por qué
(`datos.py:270-277`: que una columna nueva se enseñe en vez de esconderse); `_tabla_de_vista`
pinta las extra al final (`app.py:385-400`). Ese razonamiento era correcto para un panel interno
y deja de serlo expuesto a internet con DGs dentro: en la nueva exposición, **nada se pinta sin
que alguien lo haya declarado**. El cableado cambia las dos cosas (el `select` explícito desde
las columnas declaradas de cada `Vista` Y el render de extras) y REESCRIBE ese comentario — no
se deja un racional vigente contradiciendo al código. La puerta 8 prueba los dos sentidos: una
columna nueva en la vista NO aparece; una declarada que desaparece se detecta (la tarjeta lo
dice) en vez de romper la página.

## 8. `X-Forwarded-For`: el método de la v2 §5, intacto — y qué vale mientras tanto

Sin cambios: la medición es enviar valores señuelo en `X-Forwarded-For` contra el despliegue real,
contrastar con la cabecera que Vercel garantiza (candidatas a medir, no a suponer:
`x-vercel-forwarded-for`, `x-real-ip`), y FIJAR la regla de confianza (cuántos saltos son de la
plataforma) en `_ip_cliente` — cuyo comentario ya avisa de que hoy está calibrado para
EXACTAMENTE un proxy (`app.py:180-182`). **Gate de despliegue**: hasta que la regla esté fijada y
probada, el cerrojo por IP no se considera efectivo. Lo nuevo que C3 compra: **la mitad por
usuario del cerrojo es efectiva YA**, porque no depende de ninguna cabecera — el gate de XFF deja
de ser «el cerrojo no cuenta» y pasa a ser «la mitad por IP no cuenta».

## 9. El arranque en Vercel: quién enchufa qué

- **El punto de arranque elige el backend** — la misma filosofía de `api/index.py` («el panel no
  sabe que está en Vercel»; quien lo arranca, sí): `api/index.py` llama
  `auth.usar_backend(BackendSupabase())` y `usar_cerrojo(CerrojoSupabase())`;
  `python -m dashboard` (local) se queda con `BackendEntorno` + cerrojo en memoria → dobles,
  tests y modo local intactos. Sin variable mágica de selección.
- **`validar_configuracion` ya está preparada para esto**: su guardia
  `isinstance(_backend, BackendEntorno)` (`auth.py:383-384`) salta la comprobación de
  `DASHBOARD_USUARIOS` con el backend nuevo, y su docstring dice que el backend nuevo «traerá la
  suya» (`auth.py:379-381`): la suya es `datos.hay_credenciales()` + `sesion.secreto()`, cableada
  en `comprobar_arranque`.
- **Límite declarado**: el `lifespan` ASGI no está garantizado en el runtime Python de Vercel, así
  que `comprobar_arranque` puede no ejecutarse allí. No es un agujero de seguridad — `secreto()`
  se exige en cada petición (`app.py:803`) y sin credenciales nadie entra (fail-closed) — pero un
  error de configuración aparece como 500 genérico logueado en la primera petición, no como
  deploy fallido. La verificación post-deploy del runbook (`docs/DASHBOARD_DESPLIEGUE.md`) es el
  control compensatorio, y gana un paso: el smoke del cerrojo con dos procesos concurrentes
  (puerta 4, su mitad real).
- `DASHBOARD_USUARIOS` desaparece de Vercel; `DASHBOARD_SECRET`, `SUPABASE_URL` y
  `SUPABASE_SERVICE_KEY` se quedan.

## 10. Alternativas consideradas y descartadas

| Alternativa | Por qué no |
|---|---|
| (a1) revalidar contra la variable de entorno | Revocación «tras redesplegar»; Alberto eligió (a2) al conocer el dato (DEC-237) |
| Leer el entorno desde `app.py` (la v1) | Rodea la interfaz enchufable de DEC-231 §3 e invalida el backend futuro del war room y los dobles |
| Fallback a la variable si Supabase cae | Reabre el agujero: quien tire la base recupera al usuario revocado |
| Que el panel gestione usuarios (alta/revocación web) | Superficie nueva; el alta sigue siendo script + INSERT firmado |
| Guardar contraseña o su hash en la cookie | Innecesario: el sello (truncado de SHA-256 con sal desconocida) basta y no es material utilizable |
| Cachear el `sello` con TTL | Reintroduce la latencia de revocación que (a2) existe para eliminar; el coste real es un GET por petición |
| Tabla de sesiones en servidor | `sesion.py:8-15` ya la descartó con motivo; el sello da el «matar sesiones de UN usuario» sin tabla, job ni dependencia en cada petición |
| `HMAC(usuario\|ip)` como clave única (la v2) | Fusiona lo que el cerrojo cuenta por separado: debilita ambas mitades (crítico C3) |
| IP en claro en `panel_intentos` | El HMAC compra minimización real (un volcado no enseña IPs) a coste cero; lo que NO compra (exención RGPD) ya no se afirma (§6) |
| `SECURITY DEFINER` para la RPC | El fallo histórico exacto del repo (s296→s299, `logging_db.py:805-809`); INVOKER + REVOKE + gate de texto |
| Contador vía PostgREST sin RPC | Inexpresable: PostgREST no tiene `fallos = fallos + 1` (M4) |
| PRG con «canal flash» para el enlace | El flash hay que persistirlo en algún sitio → viola «el enlace se enseña UNA vez y no se guarda» (`gestion.py:16-24`) |
| Idempotencia por contenido + ventana (la v2) | Confunde reintento con operación intencional en los dos sentidos (M3) |
| `pg_cron` para la retención de intentos | Infra nueva para lo que la poda-en-escritura ya hace; el residuo lo cubre el procedimiento de supresión existente (§6) |

## 11. Las puertas (todas ejecutables sin red, salvo donde se declara)

1. **Revocación efectiva**: sesión abierta → `activo = FALSE` → la siguiente petición redirige.
   Control: un usuario activo no es expulsado.
2. **Cambio de contraseña**: cambia el registro → sello distinto → fuera. Control: mismo
   registro → dentro. (Ahora implementable: el sello viaja en `h` y `sello()` lo recomputa.)
3. **Fail-closed declarado**: backend con transporte caído → nadie entra (503 de estado, no «
   credenciales incorrectas») y a los de dentro no se les sirve NINGÚN dato (503 sin matar la
   cookie); al volver la base, el revocado es expulsado en su primera petición. Es la conducta
   elegida (§1.3), probada, no un accidente.
4. **Admisión atómica (semántica)**: contra el doble en memoria con `admitir`: (a) N llamadas
   «concurrentes» (sin `acierto` intercalado) admiten como mucho `FALLOS_LIBRES + 1`; (b) la
   tabla de casos secuenciales (fallos→espera) del cerrojo de hoy se reproduce idéntica; esa
   misma tabla va como comentario-contrato en el SQL. **Gap declarado**: la concurrencia REAL de
   Postgres no corre en la suite sin red — la sostienen el diseño de la función (una transacción,
   `FOR UPDATE`, claves en orden estable) y el smoke post-deploy con dos procesos (§9).
5. **Sin identificadores en claro en el cerrojo**: las claves que salen hacia la tabla casan con
   `^(u|ip):[A-Za-z0-9_-]+$` y no contienen ni el usuario ni la IP de entrada.
6. **Señuelo preservado**: en las cuatro ramas de `autenticar` (acierta, falla, no existe,
   inactivo) `verificar` corre exactamente una vez (§5).
7. **Idempotencia por operación**: mismo `op` dos veces → una invitación y el mensaje sin enlace;
   `op` distinto → dos invitaciones.
8. **Columnas en los dos sentidos**: una columna nueva de una vista no se pinta; una declarada
   que desaparece se detecta sin romper la página (§7).
9. **ACL en el texto de las migraciones** (estilo `test_s277_p1_..._acl.py`): RLS+FORCE+REVOKE
   por cada tabla nueva; `REVOKE ALL ON FUNCTION` + `GRANT EXECUTE ... service_role` para
   `panel_puerta`; `GRANT INSERT (op)` en la 020.
10. **Sin red**: toda la suite del panel corre sin credenciales — la lección de s324h sigue
    vigente; los backends nuevos reciben su transporte inyectado (un doble de `datos.leer` y del
    POST de la RPC).

## 12. Por qué es BP + estructural + escalable — y lo que NO se afirma

**BP**: revocar es un `UPDATE` efectivo en la siguiente petición; ninguna tabla nueva nace sin la
frontera RLS/REVOKE/GRANT que el repo ya canonizó; la RPC usa el patrón endurecido existente; el
señuelo, el CSRF, las cabeceras y la regla del token no se tocan. **Estructural**: cada cierre
ataca la causa (el contador se mueve al momento de la admisión; la idempotencia identifica la
operación; los CHECK meten en el esquema lo que eran validaciones de arranque), no el síntoma.
**Escalable**: `Backend` sigue siendo la interfaz de DEC-231 §3 con su primera implementación
real; el cerrojo y la tabla valen igual para dos usuarios que para veinte; nada de esto es
por-fabricante.

**Lo que NO se afirma**: esto no mide XFF (§8 es el método y su gate); no mete gestión de
usuarios en el panel; no toca el war room; no prueba la concurrencia real de Postgres en CI
(puerta 4, gap declarado); no garantiza el `lifespan` en Vercel (§9, control compensatorio); y
deja sin inspeccionar las mismas dependencias externas que declaró Sol en r1 (documentación de
Vercel, DNS/WAF, esquema realmente aplicado en Supabase).

## 13. Alcance real y secuencia

Tamaño honesto: **2 migraciones** (019: `panel_usuarios` + `panel_intentos` + `panel_puerta` +
ACL; 020: `bot_invitaciones.op`), **1 módulo nuevo** (`dashboard/cerrojo.py`), **1 script de
operación** (alta/revocación de usuarios del panel con la service key), tocados `auth.py`
(Usuario.sello, Backend.sello, BackendSupabase, admitir), `sesion.py` (nada — el payload es un
dict), `app.py` (puerta con sello; cerrojo nuevo; op en el formulario), `gestion.py` (op +
docstring), `datos.py` (select explícito de vistas + comentario), `api/index.py` (enchufe),
y ~10 puertas nuevas de test.

**Secuencia**: (1) dúo sobre esta v3 — es autenticación, ALTO, el dúo es innegociable; (2)
cablear en sesión fresca SOLO si SÓLIDO (el criterio de DEC-237 sigue: el patrón de fallo era «no
vi un contrato escrito», y eso se caza con contexto limpio, no con más rondas aquí); (3) migrar,
desplegar con el runbook, y ejecutar la medición de XFF ANTES de dar el cerrojo-por-IP por
efectivo. El paso (3) incluye el smoke concurrente del cerrojo.
