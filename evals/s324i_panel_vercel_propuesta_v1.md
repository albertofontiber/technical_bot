# s324i — El panel a Vercel y a `techassistant.fontiber.com`

> **Adjudicado por Alberto (18-ago)**: subdominio `techassistant.fontiber.com` («a futuro
> buscaré un nombre más fancy») y **opción (a) para la sesión: revalidar en cada petición**.

> **Método**: primero se midió el terreno, después se escribió. Cada afirmación lleva
> `fichero:línea` verificado en esta sesión. Es la corrección del patrón que el dúo me
> señaló ocho veces en s324h — afirmar por encima de lo medido.

El panel está **construido, probado y sin desplegar**. El dúo r41 dejó cinco condiciones
escritas en el runbook «como condiciones, no como recomendaciones». Esta propuesta cierra
las cuatro que se pueden cerrar, y declara la quinta.

---

## 0. Lo que cambia al pasar de Railway a Vercel

No es un cambio de hosting: **tres de los cinco hallazgos empeoran en serverless**.

| | En Railway (un proceso) | En Vercel (funciones) |
|---|---|---|
| Cerrojo de intentos | cuenta en memoria del proceso; se pierde al reiniciar | **cada intento puede caer en otra instancia** → la espera creciente casi no se aplica |
| Reintento del navegador | poco probable | un corte de función se ve como **página en blanco** → el F5 es lo natural |
| `X-Forwarded-For` | calibrado para **exactamente un proxy**: el borde de Railway | topología distinta, **sin revalidar** |

---

## 1. Sesión — revalidación en cada petición (opción (a) de Alberto)

**Lo que falla hoy** (Sol 5, bloqueante nº 1): una sesión válida no revalida contra
`DASHBOARD_USUARIOS`. Quitar a alguien o cambiarle la contraseña **no le expulsa hasta 8 h**;
la única revocación es rotar `DASHBOARD_SECRET`, que echa a todos.

**Medido antes de diseñar:**

| Pregunta | Medición |
|---|---|
| ¿Cuántos puntos de verificación hay? | **Uno solo** — `app.py:801`. El cambio entra por un sitio |
| ¿Qué lleva el payload? | `{u, csrf, iat, exp}` |
| ¿Cuánto cuesta releer la lista? | **0,001 ms** por petición (sin red, sin `scrypt`) |
| ¿Hace falta `scrypt`? | **No.** `scrypt` sólo corre en `verificar(contraseña, registro)`; comprobar que el usuario sigue en la lista es mirar un diccionario |

**Diseño**: en el único punto de verificación, además de validar firma y caducidad, comprobar
que `payload["u"]` **sigue en `DASHBOARD_USUARIOS`**. Si no está → `303` a `/entrar`.

**Y un segundo caso que la medición regaló**: detectar un **cambio de contraseña** sin
almacenar nada sensible. El registro (hash + sal) cambia al cambiarla, así que un digest
corto del registro dentro del payload invalida la sesión sola:

```python
# al abrir sesión: payload["h"] = digest_registro(registro_del_usuario)
# al verificar:    if payload.get("h") != digest_registro(registro_actual): -> /entrar
```

Con eso, (a) cubre los dos casos que importan: **quitar a alguien** y **cambiarle la
contraseña**, ambos efectivos en la siguiente petición y sin echar a nadie más.

**Coste declarado**: la sesión deja de ser autónoma — si `DASHBOARD_USUARIOS` desaparece de
las variables de entorno, **todo el mundo queda fuera**. Es fail-closed, y en un panel que
gobierna accesos al bot es la degradación correcta; pero es un cambio real respecto a hoy y
va escrito.

## 2. Invitar tiene que ser idempotente

**Lo que falla hoy** (Sol 6 + Fable 5): `generar_invitacion` llama a `access.token_nuevo()`
y escribe, **sin clave de idempotencia** (`gestion.py:163-190`). Cada F5 crea otra credencial
válida — y en Vercel el F5 es más probable, porque un corte de función se ve como página en
blanco.

**Diseño**: PRG (POST → redirect → GET) más una clave de idempotencia derivada del formulario
(nota + días + operador + ventana temporal) que la base rechaza por UNIQUE. Un reintento
devuelve **la misma** invitación en vez de crear otra.

**Gap declarado**: hace falta una columna/índice en `invitaciones`. Va como migración
**escrita y no aplicada**, igual que la 017 y la 018 — la aplica Alberto.

## 3. Las métricas: `select=*` es fail-open de esquema

**Lo que falla hoy** (Sol 7), y el código lo declara:

```python
# dashboard/datos.py:271
"""`select=*` a propósito: si la vista gana una columna, el panel la enseña"""
```

Es **deliberado y documentado**, pero es lo contrario de minimización: si mañana alguien añade
una columna sensible a una vista de Supabase, **aparece en el panel sin revisión**.

**Diseño**: el panel ya declara sus columnas una por una en `VISTAS` (`datos.py:136+`). Basta
usar esa lista como `select` explícito en vez de `*`. Cambia una línea y convierte el fail-open
en fail-closed: una columna nueva **no se enseña** hasta que alguien la añade a la declaración.

## 4. `X-Forwarded-For` en Vercel — revalidar, no suponer

`_ip_cliente` (`app.py:169-185`) toma el elemento **más a la derecha**, y su docstring declara
el alcance con honestidad: *«correcto con EXACTAMENTE un proxy de confianza delante, que es el
despliegue de hoy. Si algún día hay CDN, hay que contar saltos, y este comentario es el aviso.»*

**Vercel es ese día.** Hay que medir cuántos saltos añade su borde **antes** de exponer el panel,
porque de eso depende el cerrojo por IP: si se cuenta mal, es decorativo — basta mandar una
cabecera distinta en cada intento.

**Esto no se diseña, se mide**: un endpoint temporal que devuelva la cabecera cruda, una visita
desde fuera, y el número de saltos sale solo. **No cablear el cerrojo hasta tener esa medición.**

## 5. El cerrojo en serverless — declarado, NO resuelto

**Lo que falla** (Sol 2): el cerrojo cuenta en memoria del proceso (`auth.py:299-362`). En
serverless cada intento puede caer en otra instancia, así que la espera creciente casi no se
aplica. Queda `scrypt` (~170 ms medido) y la longitud de la contraseña — que evita fuerza bruta
ordinaria pero **no** credential-stuffing ni agotamiento por coste.

**Recomendación**: mover el contador a Supabase (una tabla pequeña: `clave`, `fallos`, `ultimo`).
Es lo correcto y ya estaba escrito en el runbook como opción 1.

**Alternativa mientras no esté**: contraseña larga generada (20+ caracteres de un gestor) y el
hueco **declarado**. El runbook dice que eso es «condición de despliegue, no recomendación».

**Mi posición**: con dos personas y contraseña de gestor, es asumible **si va declarado**; pero
no lo decido yo. Es la única de las cinco que sigue necesitando adjudicación de Alberto.

---

## 6. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Sesiones cortas (30–60 min) en vez de revalidar | Alberto eligió (a). Y la medición la respalda: revalidar cuesta 0,001 ms, así que la fricción del re-login no compra nada |
| Guardar la contraseña (o su hash) en el payload para detectar cambios | Innecesario y peor: un **digest del registro** basta y no mete material sensible en una cookie |
| Un `select` con lista blanca en la vista SQL en vez de en el panel | Deja la decisión en Supabase, donde la cambia cualquiera sin pasar por el repo. La declaración debe vivir versionada |
| Desplegar ya y arreglar después | Los cinco están en el runbook **como condiciones**. El nº 1 es justo el que hace que un panel de accesos no sirva para lo que existe |

## 7. Las puertas

1. **Revocación efectiva**: test que abre sesión, quita el usuario de `DASHBOARD_USUARIOS`, y
   comprueba que la siguiente petición redirige a `/entrar`. Y su control: un usuario que sigue
   en la lista **no** es expulsado.
2. **Cambio de contraseña**: mismo patrón, cambiando el registro en vez de quitarlo.
3. **Idempotencia**: dos POST idénticos → **una** invitación, y la segunda respuesta devuelve
   la misma. Control: dos POST **distintos** → dos invitaciones.
4. **Columnas**: test que añade una columna falsa a la respuesta y comprueba que **no** se pinta.
5. **Sin red**: el panel entero debe poder probarse sin credenciales — la lección de s324h, donde
   un gate pasaba en local y fallaba en CI porque llamaba a Supabase.

## 8. Por qué es BP, estructural y escalable

**BP**: un panel que gobierna accesos puede revocar en el acto; y no enseña datos que nadie ha
declarado que se enseñen. **Estructural**: la revalidación entra por el ÚNICO punto de
verificación que existe, y la lista de columnas ya está declarada — se usa la que hay, no se
inventa otra. **Escalable**: el digest del registro sirve igual con dos usuarios que con veinte,
y el `select` explícito no necesita mantenimiento salvo cuando alguien quiera enseñar algo nuevo,
que es exactamente cuando debe haber una decisión.

**Lo que NO se afirma**: esto no resuelve el cerrojo en serverless (§5, pendiente de
adjudicación), no revalida `X-Forwarded-For` —eso es medición, no diseño— y no toca el war room.
