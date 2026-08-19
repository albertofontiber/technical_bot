# s324i v2 — El panel a Vercel con los usuarios en Supabase (opción a2)

> **Adjudicado por Alberto (18-ago)**: subdominio `techassistant.fontiber.com`, y **(a2)**:
> la lista de usuarios sale de las variables de entorno y pasa a Supabase, con revocación
> real e inmediata; el cerrojo distribuido cae del mismo árbol.

> **La v1 fue NO SÓLIDO** (Sol: 1 crítico + 6 medios). Dos hallazgos rompían premisas que yo
> le había vendido a Alberto, y esta v2 existe porque **la corrección cambió su decisión**,
> no porque hubiera que pulir la redacción.

---

## 0. Qué rompió la v1, y por qué esto es (a2) y no (a1)

**«Revocación en la siguiente petición» era falso.** `DASHBOARD_USUARIOS` es una variable de
entorno, y el propio código lo declara: *«cambiar la variable en Railway surta efecto **al
reiniciar el servicio**»* (`auth.py:233-236`). En Vercel eso es **redesplegar**.

De ahí la consecuencia estructural: **mientras la lista viva en el entorno, la revocación no
puede ser más rápida que un despliegue.** Alberto eligió (a2) al saberlo.

**Y la idempotencia que propuse era imposible.** Dije que un reintento «devuelve la misma
invitación»; el fichero lo desmiente tres párrafos antes de donde yo miraba
(`gestion.py:16-24`): *«en la base se guarda su SHA-256, y el enlace se enseña UNA vez. El
panel no puede volver a mostrarlo porque nadie puede: lo que hay guardado es una huella.»*

---

## 1. Los usuarios a Supabase — usando la interfaz que YA existe

**Medido**: `Backend` es un `Protocol` con **un solo método**, `autenticar(usuario,
contrasena) -> Usuario | None` (`auth.py:186-190`), y `Usuario` sólo lleva `nombre`. No hay
ninguna tabla de usuarios hoy.

DEC-231 punto 3 dejó esa interfaz escrita *precisamente* para esto: «la autenticación es una
pieza ENCHUFABLE». La v1 se la saltaba leyendo el entorno desde `app.py` — que es lo que Sol
señaló (M2). **Aquí se usa para lo que existe.**

### 1.1 La tabla

```sql
CREATE TABLE panel_usuarios (
    usuario      TEXT PRIMARY KEY,          -- normalizado en minúsculas
    registro     TEXT NOT NULL,             -- scrypt: algoritmo+params+sal+hash
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    alta_por     TEXT NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocado_en  TIMESTAMPTZ,
    revocado_por TEXT
);
```

**Sin contraseñas**: `registro` es el mismo formato scrypt de hoy, generado por
`scripts/s324f_dashboard_password.py`, que **no guarda nada**.

**Revocar = `UPDATE ... SET activo = FALSE`.** Efectivo en la **siguiente petición**, ahora sí.

### 1.2 La interfaz se AMPLÍA, no se rodea

```python
class Backend(Protocol):
    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None: ...
    def vigente(self, nombre: str) -> Usuario | None: ...   # NUEVO
```

`vigente` es la revalidación: ¿este usuario sigue activo **y con el mismo registro**? Devuelve
`None` si lo quitaron, lo desactivaron o le cambiaron la contraseña.

**`BackendEntorno` la implementa igual** (leyendo la variable), así que los dobles y el modo
local siguen funcionando y la sustitución es real y no un parche.

### 1.3 Cambio de contraseña, sin guardar nada sensible

El payload de la cookie lleva hoy `{u, csrf, iat, exp}` (medido). Se añade `h`: un digest corto
del registro. Si el registro cambia, el digest no cuadra → fuera. No hace falta comparar
contraseñas ni almacenarlas en la cookie.

### 1.4 El precio, declarado

**Si Supabase no responde, nadie entra — y los que están dentro salen.** La lista de usuarios
deja de ser configuración de despliegue y pasa a ser un dato en línea.

Es **fail-closed**, y para un panel que gobierna accesos al bot es la degradación correcta: un
panel de control que sigue abierto cuando no puede comprobar quién eres, no está controlando
nada. Pero es un cambio real frente a hoy y va escrito, no descubierto.

**Alcance acotado a propósito**: el panel **lee** usuarios, no los gestiona. Dar de alta sigue
siendo generar el registro con el script y un `INSERT` — el mismo flujo de hoy, con revocación
inmediata añadida. Meter gestión de usuarios en el panel es superficie nueva y va aparte.

## 2. El cerrojo, en la misma base

Del mismo árbol que (a2), y responde al bloqueante 5 (Sol 2) y a los cuatro huecos que Sol
señaló en la v1 (M7):

```sql
CREATE TABLE panel_intentos (
    clave     TEXT PRIMARY KEY,      -- HMAC(usuario|ip, secreto) — ver abajo
    fallos    INTEGER NOT NULL DEFAULT 0,
    ultimo    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Hueco (Sol, v1) | Cómo se cierra |
|---|---|
| **Atomicidad** | El incremento es `UPDATE ... SET fallos = fallos + 1` (o `INSERT ON CONFLICT DO UPDATE`), no un read-modify-write en Python. Sin carreras que pierdan incrementos |
| **La IP es DATO PERSONAL** | **No se guarda la IP.** La clave es un `HMAC(usuario\|ip, DASHBOARD_SECRET)`: sirve igual para contar y no es reversible. Encaja con el RGPD que ya está montado, en vez de abrirle un frente |
| **Poda / crecimiento ilimitado** | Borrado por antigüedad en la propia escritura (`DELETE WHERE ultimo < now() - interval`), y `clave` es PK: el tamaño está acotado por usuarios×IPs recientes, no por intentos |
| **Indisponibilidad** | **Fail-open declarado en el contador, no en la autenticación**: si la tabla no responde, el intento se permite pero `scrypt` (~170 ms medido) sigue corriendo. Bloquear el login legítimo por un fallo de telemetría sería peor que el ataque |

## 3. Idempotencia — rediseñada, porque la de la v1 era imposible

**No se puede devolver el mismo enlace.** Lo que sí se puede, y es lo que importa, es **no crear
la segunda credencial**:

- **PRG**: POST → 303 → GET, para que el F5 no reenvíe el formulario.
- **Clave de idempotencia** derivada de (nota + días + operador + ventana), con `UNIQUE` en la
  base. El segundo intento **no crea nada** y muestra: *«ya emitiste esta invitación hace un
  momento. Si perdiste el enlace, anúlala y emite otra.»*

**Lo que NO promete**: recuperar el enlace. Es imposible por diseño y decirlo es parte de la
propuesta, no una excusa.

## 4. Las métricas: `select` explícito — y NO es una línea

Sol (M3) desmontó mi «cambia una línea»: además del `select`, **el renderizador busca campos
adicionales y los pinta aparte** (`app.py:385-399`). Hay que quitar las dos cosas.

Y la puerta tiene que probar los **dos** sentidos: que una columna nueva **no** se pinta, y que
una columna declarada que **desaparece o se renombra** se detecta en vez de romper la página.

## 5. `X-Forwarded-For` — medición de verdad, no una visita

Mi «medición» de la v1 no medía nada (Sol M4): una visita externa observa un caso y no prueba
qué hace Vercel con una cabecera **preinyectada por el atacante**.

**La medición correcta**: enviar valores señuelo en `X-Forwarded-For`, contrastar contra la
cabecera que la plataforma garantiza, y **fijar una regla de confianza** (cuántos saltos son
suyos). Contar saltos una vez no es estructural; la regla sí.

**Gate de despliegue**: hasta que esa regla esté fijada y probada, el cerrojo por IP no se
considera efectivo — y se dice, en vez de suponerlo.

## 6. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| (a1): revalidar contra la variable de entorno | Da revocación «tras redesplegar», no inmediata. Alberto eligió (a2) al conocer el dato |
| Leer el entorno desde `app.py` para revalidar (**la v1**) | Rodea la interfaz enchufable que DEC-231 creó justo para esto, e invalida el futuro backend del war room y los dobles |
| Guardar la contraseña o su hash en la cookie | Innecesario: un digest del registro basta y no mete material sensible en el navegador |
| Guardar la IP en claro en la tabla del cerrojo | Es dato personal y abre un frente de RGPD por una función que se puede hacer con un HMAC |
| Fallback a la variable si Supabase cae | Reabre el agujero: quien pueda tirar la base recupera al usuario revocado |
| Que el panel gestione usuarios | Superficie nueva. v1 lee; el alta sigue siendo script + INSERT |

## 7. Las puertas

1. **Revocación efectiva**: sesión abierta → `activo = FALSE` → la siguiente petición redirige.
   Control: un usuario activo **no** es expulsado.
2. **Cambio de contraseña**: cambia el registro → fuera. Control: mismo registro → dentro.
3. **Fail-closed declarado**: con la base caída, nadie entra **y** los de dentro salen. Es una
   prueba de la conducta elegida, no un accidente que se descubre en producción.
4. **Cerrojo atómico**: N incrementos concurrentes → contador exacto (sin carreras perdidas).
5. **Sin IP en claro**: test que comprueba que la tabla no contiene ninguna IP.
6. **Idempotencia**: dos POST idénticos → **una** invitación. Control: dos distintos → dos.
7. **Columnas en los dos sentidos**: una columna nueva no se pinta; una declarada que
   desaparece se detecta.
8. **Sin red**: el panel entero probable sin credenciales — la lección de s324h, donde un gate
   pasaba en local y fallaba en CI porque llamaba a Supabase.

## 8. Por qué es BP, robusto y escalable

**BP**: revocar a alguien es un `UPDATE`, no un redespliegue; y ningún dato se enseña sin que
alguien lo haya declarado. **Robusto**: el fail-open está donde debe (el contador) y el
fail-closed donde debe (la identidad); el incremento es atómico, y la IP no se almacena.
**Escalable**: la interfaz `Backend` es la que ya existía —esto es su primera implementación
real, no una excepción—, y el cerrojo vale igual con dos usuarios que con veinte.

**Lo que NO se afirma**: esto no mide `X-Forwarded-For` (§5 es el método, no el resultado), no
mete gestión de usuarios en el panel, y no toca el war room.

## 9. Alcance real, dicho sin adornos

Esto es **más grande** que la v1: tabla nueva, backend nuevo, ampliación de una interfaz,
cerrojo distribuido, dos migraciones y ocho puertas. No es «un retoque antes de desplegar».

**Recomendación de secuencia**: validar este diseño con el dúo ahora, y **cablear en sesión
fresca**. Vengo de una sesión con quince correcciones del dúo encima; el diseño se sostiene en
mediciones escritas, pero la implementación merece un contexto limpio — es el mismo criterio
por el que el Protocolo 3 exige agente fresco en cada ronda.
