# s324i v7 — El panel a Vercel: el diseño tras cinco tandas del dúo (10+14+12+10+9)

> **Punto de partida (DEC-237)**: (a2) adjudicado por Alberto — `techassistant.fontiber.com`,
> los usuarios salen de las variables de entorno y pasan a Supabase. Traza de rondas en s324j
> (en cada una: hallazgos 100 % confirmados con regla C, 0 falsos positivos):
> **v3** cerró los diez de la v2 → **r1**: NO SÓLIDO (3 críticos; tally `2026-08-19T07:50:18`) →
> **v4** → **r2**: cero críticos (`2026-08-19T08:06:55`) → **v5** → **r3**: cero críticos; Fable
> «SÓLIDO con residuos» (`2026-08-19T08:19:51`) → **v6** → **r4**: cero críticos por tercera
> ronda; Sol 4 medios + 1 menor, Fable «sin críticos … resiste ancla por ancla», 2 medios + 2
> menores, TODOS de contrato-por-enumerar/linaje/prosa — ninguno del mecanismo
> (`2026-08-19T08:34:58`). Esta **v7** cierra los nueve de r4.
>
> **Regla de la sesión**: diseño, dúo, y NO cablear. «No desplegar hasta que sea SÓLIDO.»

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

## 0-bis. Los catorce de la ronda r1 (sobre la v3) → dónde queda cada uno

Sol (S-*), 8/8 confirmados contra código/docs antes de tocar nada; Fable (F-*) emparejado.

| # | Hallazgo (con su verificación) | Cierre |
|---|---|---|
| S-C1 | El PATCH de anular escribe `nota` y el GRANT de la 016 no la concede (verificado: `migrations/016_allowlist_invitaciones.sql:321-322` vs `gestion.py:273`) — **defecto LATENTE de HOY**, no sólo de la propuesta | §4.3 (nuevo) + 020 + puerta 9 |
| S-C2 / F-C1 | Contradicción interna §5↔§1.3: «transporte caído» tenía dos conductas opuestas (señuelo+None vs excepción+503). Convergente en los DOS revisores | §5 (reescrito) |
| S-C3 | `FOR UPDATE` no bloquea filas inexistentes: la primera ráfaga por clave fresca entraba entera | §3.2 (sembrar antes del lock) |
| S-M1 | `acierto` borra la clave `u:` con los fallos del atacante dentro. Verificado: es la semántica DELIBERADA de hoy (`auth.py:338-341`) | §3.2 (declarada como heredada) + puerta 4 |
| S-M2 | El cap no es concurrente entre claves disjuntas | §3.4 (advisory lock) |
| S-M3 | «pg_cron sería infra nueva» era FALSO (la pasada mensual EXISTE: s299, `docs/RGPD_RETENCION.md:139-150`); y `retencion_s` no tenía constante fuente | §6 (se amplía la pasada existente; constante nueva declarada) |
| S-M4 | Los CHECK no trasladaban charset/longitud ni el formato completo | §1.1 (CHECK ampliado + dónde vive la validación completa) |
| S-M5 | Falta `NOTIFY pgrst, 'reload schema'` — la 016 FASE D nació de un incidente real (404 con las tablas ya creadas) | §1.2 y §13 (ambas migraciones lo llevan) |
| F-M1 | El «503 sin contar el intento» era inalcanzable en fallo PARCIAL: `admitir` ya contó antes de que `autenticar` lance | §1.3 (el fantasma, declarado con su alcance exacto) |
| F-m1 | `gestion.py:20-24` afirma un «POST-redirect-GET» que nunca existió (`app.py:730-735` renderiza) | §4.1 (el cableado reescribe ese docstring) |
| F-m2 | «migrations/016» era ambiguo: la numeración YA colisionó (`016_allowlist_invitaciones.sql` y `016_validacion_un_solo_uso.sql`) | Nombres completos en todo el doc + aviso en §13 |
| F-m3 | Derivar `K` de `DASHBOARD_SECRET` acopla el botón de pánico al cerrojo: rotar el secreto resetea los contadores en plena crisis — precio sin declarar | §3.1 (precio declarado) + §10 (alternativa pepper, descartada con motivo) |
| F-m4 | DEC-237 no localizado por su grep (0 hits) | Límite del scan del revisor: verificado humano en `docs/DECISIONS.md:7803` esta sesión; sin cambio |

## 0-ter. Los doce de la ronda r2 (sobre la v4) → dónde queda cada uno

| # | Hallazgo (verificado con regla C) | Cierre |
|---|---|---|
| S2-M1 | Ampliar la pasada mensual no ejecuta: corre como rol `rgpd_retencion` (verificado: `supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql:125-181`) y la 019 sólo concedía a `service_role` | §1.2 (GRANT al rol + POLICY de ventana, el patrón s295 exacto) |
| S2-M2 | «La concurrencia real de Postgres no corre en la suite» era un gap FALSO: el repo levanta Postgres 17 desechable en CI (`tests/test_s295_rgpd_integracion_pg.py` + workflow) y exige verificar el EFECTO | Puerta 4 (test de integración pg del cerrojo) |
| S2-M3 | Aritmética del cap: con 9.999 filas y 2 claves nuevas, «si está al cap» no poda y quedan 10.001 | §3.4 (podar hasta `count + nuevas ≤ cap`) |
| S2-M4 | `GRANT UPDATE (nota)` perpetuaba el parche de r41 cuando la 020 ya elimina su única justificación (evitar migración) | §4.3 (columna `revocada_por` + CHECK del patrón `bot_allowlist_revocacion_completa`, `migrations/016_allowlist_invitaciones.sql:224-228`) |
| S2-M5 | `panel_usuarios` admitía estados de auditoría contradictorios (`activo=false` sin autor/fecha, o activo con revocación) | §1.1 (CHECK que ata los tres campos) |
| S2-M6 | `op TEXT UNIQUE` nullable no obliga a las filas NUEVAS (infinitos NULL) | §4.2 (`NOT NULL DEFAULT gen_random_uuid()::text` + CHECK de longitud) |
| S2-m1 | «Formato completo validado por `_partir`» sobre-afirmaba (parámetros extra tolerados, longitudes no exigidas) | §1.1 (el claim real: LEGIBLE por el mismo parser que usa `verificar`) |
| S2-m2 | El margen tras rotar el secreto no es «≤4»: el cerrojo de hoy admite 5 (`fallos <= FALLOS_LIBRES` abierto) | §1.3, §3.1, §10 (cifra corregida: `FALLOS_LIBRES + 1`) |
| F2-M1 | La clase S-C1 reproducible DENTRO de `panel_puerta`: los GRANT de tabla que la RPC INVOKER ejerce no estaban enumerados, y 9-bis sólo cruzaba `gestion.py` | §1.2 (GRANT de `panel_intentos` enumerado) + puerta 9-bis ampliada |
| F2-M2 | `tabla_ausente`/`sin_credenciales` son configuración PERSISTENTE, no transporte transitorio: el fail-open quedaba silencioso e indefinido | §3.5 (frontera redefinida: sonda de arranque + fail-open sólo ante `error`, con log) |
| F2-m1 | Cookies pre-despliegue sin `h`: la regla de expulsión no estaba en el contrato (y un `compare_digest` con `None` lanza) | §2 (regla explícita) + puerta 2 (control) |
| F2-m2 | Anclas fuera de su presupuesto y los tallies de r1 son afirmación del autor | Meta-nota: correcto — los tallies los audita quien adjudique, no el propio dúo |

## 0-quater. Los diez de la ronda r3 (sobre la v5) → dónde queda cada uno

| # | Hallazgo (verificado con regla C) | Cierre |
|---|---|---|
| S3-M1 | En Vercel sin `lifespan`, degradar `tabla_ausente`/`sin_credenciales` a fail-open+log dejaba el panel operando sin cerrojo indefinidamente si el smoke se omite | §3.5 (fail-closed TAMBIÉN en runtime para estados de configuración) |
| S3-M2 | El CLI anula con SELECT→check→PATCH incondicional (verificado: `scripts/s324e_invitaciones.py:357-381`): puede «anular» una invitación canjeada en la ventana | §4.3 (el CLI adopta el PATCH condicional del panel) |
| S3-M3 | «Un registro que el script acepta no puede producir un usuario inalcanzable» seguía siendo falso: `_partir` tolera sal/hash de 1 byte y `verificar` deriva 32 | §1.1 (validador ESTRICTO en el script de alta) |
| S3-M4 | El autocontrol de la pasada de 24 meses afirma EXACTAMENTE 4 tablas y una política por tabla, y su recibo un solo `corte` (verificado: `s299_job_programado_v1.sql:176-228`): «ampliarla» tocaba un contrato vivo endurecido | §6 (función HERMANA: se instancia el patrón, no se edita la función) |
| S3-M5 | `panel_usuarios` entraba en la matriz sin plazo para filas revocadas | §6 (plazo `[DECIDIR: Alberto]` con dueño, el dispositivo canónico) |
| S3-m1 | Contrato criptográfico incompleto (truncado sin longitud; `b64` sin variante) | §3.1 (16 bytes + base64url sin relleno) |
| F3-M1 | `_escribir` aplana el 409/23505 en `ERROR` genérico (verificado: `gestion.py:104-105`): el mensaje «ya emitiste» del que cuelga M3 no tenía mecanismo | §4.2 (estado `DUPLICADO` declarado en el vocabulario) |
| F3-m1 | «La sonda no tiene efecto alguno» sobre-afirmaba: poda caducados y toma el lock | §3.5 (claim corregido: sin efecto sobre CONTADORES) |
| F3-m2 | `pg_advisory_xact_lock` se retiene hasta COMMIT, no hasta el fin de la «fase»: `admitir` queda totalmente serializado y la prosa sugería un lock de fase | §3.2/§3.4 (semántica real declarada; `FOR UPDATE` queda como segunda capa) |
| F3-m3 | `sesion.py:8` enumera `{u, iat, exp, csrf}` y el alcance decía «sesion.py: nada» — deuda de prosa con `h` nuevo | §13 (el docstring entra en el alcance) |

(F3-espec — Fable no pudo verificar el test pg de s295 por límite de glob: existe, leído esta
sesión — `tests/test_s295_rgpd_integracion_pg.py` + `.github/workflows/s295-rgpd-retencion-pg.yml`.)

## 0-quinquies. Los nueve de la ronda r4 (sobre la v6) → dónde queda cada uno

| # | Hallazgo (verificado con regla C) | Cierre |
|---|---|---|
| S4-M1 | «`error` = transitorio» era falso: `datos.py:92-100` aplana CUALQUIER 4xx/5xx (400 de firma, 401/403 de ACL, SQL persistente) en `ERROR` → fail-open indefinido en Vercel sin `lifespan` | §3.5 (la frontera es «¿se pudo HABLAR?»: respuesta ≥400 del cerrojo = configuración = 503) |
| S4-M2 | El alcance (§13) seguía ordenando validar con `_partir`, contradiciendo el cierre estricto de S3-M3; y ninguna puerta exigía el rechazo | §13 corregido + puerta 11 nueva |
| S4-M3 | La hermana sin sus dos controles del precedente: REVOKE nominal (s299:333-340) y postcondición del job activo (s299:466-496) | §6 (ambos, literales) + puerta 9 |
| S4-M4 | `Usuario.sello=""` era compatibilidad FALSA: el doble viejo construye, pero el login emite `h=""` y la siguiente petición expulsa — rotura conductual oculta | §2 (sello OBLIGATORIO, sin default; dobles actualizados y enumerados) |
| S4-m1 | `/salir` dependía de Supabase: durante una caída, 503 y la cookie que querías borrar sigue viva | §2 (el logout es local: firma+CSRF y borrado, sin consultar identidad) |
| F4-M1 | `panel_retencion_pasada` NO estaba en la puerta 9 — la clase s296 exacta (EXECUTE por defaults de Supabase en una función que borra y estampa recibos) | Puerta 9 (la hermana entra al gate) |
| F4-M2 | Dependencia de linaje sin declarar: el rol `rgpd_retencion` y `rgpd_recibos` nacen en `supabase/migration_proposals` aplicadas A MANO — la 019 abortaría en el GRANT en un entorno sin s295/s299, y el test pg necesita fabricar ese entorno | §13 (guard fail-fast en la 019 + preámbulo del test declarado) |
| F4-m1 | «Viva en producción … con recibo» sobre-afirmaba: job ACTIVO y dry-run con ROLLBACK; cero pasadas reales (primer recibo esperado 1-sep, `RGPD_RETENCION.md:145-146`) | §6 (reword honesto) |
| F4-m2 | El `sello` no declaraba variante de base64 (las claves HMAC sí, tras S3-m1) | §2 (base64url sin relleno, la misma) |

---

## 1. Los usuarios a Supabase

### 1.1 La tabla — con las lecciones dentro, no en la prosa

```sql
CREATE TABLE public.panel_usuarios (
    usuario      TEXT PRIMARY KEY
                 CHECK (usuario ~ '^[a-z0-9._@-]{1,64}$'),
    registro     TEXT NOT NULL CHECK (registro LIKE 'scrypt$%'),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    alta_por     TEXT NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocado_en  TIMESTAMPTZ,
    revocado_por TEXT,
    CONSTRAINT panel_usuarios_revocacion_coherente CHECK (
        (activo AND revocado_en IS NULL AND revocado_por IS NULL)
        OR (NOT activo AND revocado_en IS NOT NULL AND revocado_por IS NOT NULL)
    )
);
```

El tercer CHECK (ronda r2, S2-M5) hace imposibles los estados de auditoría contradictorios que
los GRANT por columnas permitirían crear por separado: no puede existir un usuario desactivado
sin autor y fecha de revocación, ni uno activo con revocación registrada. Reactivar a alguien
obliga a limpiar las dos columnas en el mismo UPDATE. Es el mismo contrato que
`bot_allowlist_revocacion_completa` (`migrations/016_allowlist_invitaciones.sql:224-228`), y aquí
puede ser estricto desde el día uno porque la tabla nace ahora — sin filas legacy que tolerar.

Dos CHECK que no son adorno, y la frontera honesta de cada uno (ronda r1, S-M4): el de `usuario`
impone en el TIPO **el mismo charset y longitud que el backend exige al autenticar** (§5) — no
sólo la normalización de `_normalizar_usuario` (`auth.py:205-206`): una fila que el panel jamás
podría encontrar no puede ni existir. El regex vive duplicado en SQL y en Python por necesidad;
la puerta 6-bis los ata: una tabla de casos (válidos e inválidos) compartida que ambos lados
deben aceptar/rechazar igual. El de `registro` corta EN LA BASE el error que
`validar_configuracion` caza hoy en el arranque (`auth.py:399-409`): pegar la contraseña en claro
donde iba el hash. **Y lo que el CHECK no puede validar lo valida el script de alta, ESTRICTO**
(rondas r2/r3, S2-m1 y S3-M3 — la segunda tumbó a la primera: «legible por `verificar`» no
bastaba, porque `_partir` tolera una sal o un hash de UN byte y `verificar` deriva siempre
`LONGITUD_CLAVE_BYTES = 32` (`auth.py:109,153-154`) — un registro así es legible y NO PUEDE
verificar jamás: un usuario inalcanzable). El script de alta valida con un helper nuevo
`validar_registro_estricto` en `auth.py`: `_partir` **más** sal de exactamente
`LONGITUD_SAL_BYTES` (16), clave de exactamente `LONGITUD_CLAVE_BYTES` (32) y solo los parámetros
`n,r,p` — es decir, exactamente lo que `hash_contrasena` emite. Ahora sí: un registro que el
script acepta verificará con la contraseña correcta.

**Alta y revocación siguen fuera del panel** (alcance v1 de la v2, conservado): el registro lo
genera `scripts/s324f_dashboard_password.py` (que no guarda nada) y el INSERT/UPDATE lo ejecuta
un script de operación con la service key — el mismo patrón que el CLI de invitaciones. Revocar =
`UPDATE ... SET activo = FALSE, revocado_en = now(), revocado_por = ...`. Efectivo en la
siguiente petición (§2). Baja LÓGICA, sin DELETE: misma disciplina y mismo motivo que
`bot_allowlist` (`migrations/016:230-234` — conservar la traza; la supresión a petición va
aparte, §6).

### 1.2 La frontera de la 016, aplicada — el crítico C1

La migración nueva (`migrations/019_panel_usuarios_cerrojo.sql`) lleva, para CADA tabla nueva, el
patrón exacto de `migrations/016_allowlist_invitaciones.sql:266-292`:

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

`panel_intentos` (§3) lleva el mismo bloque, y sus GRANT van **enumerados, no aludidos** (ronda
r2, F2-M1: la clase S-C1 —una escritura sin su GRANT— puede reproducirse DENTRO de la RPC, que
es `SECURITY INVOKER` y ejerce los privilegios de quien la llama):

```sql
GRANT SELECT ON public.panel_intentos TO service_role;             -- FOR UPDATE de admitir
GRANT INSERT (clave, fallos, ultimo) ON public.panel_intentos TO service_role;  -- siembra+upsert
GRANT UPDATE (fallos, ultimo) ON public.panel_intentos TO service_role;         -- incremento
GRANT DELETE ON public.panel_intentos TO service_role;             -- poda, cap y acierto
```

`DELETE` está aquí y no en las otras tablas por una diferencia razonada: borrar ES el contrato de
esta tabla (poda, cap, `acierto`) y no hay nada que conservar — al revés que en las tablas con
traza. La puerta 9-bis cruza TAMBIÉN las sentencias del cuerpo de `panel_puerta` con estos GRANT,
no sólo los payloads de `gestion.py`.

**Y la pasada de retención necesita su propio acceso** (ronda r2, S2-M1 — verificado: la pasada
mensual corre como el rol `rgpd_retencion`, no como `service_role`, con el plazo impuesto por
POLICY, `20260803140000_s295_rgpd_rol_retencion_v2.sql:125-181`). La 019 replica ese patrón
exacto para la tabla nueva:

```sql
GRANT SELECT (clave, ultimo) ON public.panel_intentos TO rgpd_retencion;
GRANT DELETE ON public.panel_intentos TO rgpd_retencion;
CREATE POLICY rgpd_retencion_ventana ON public.panel_intentos
    TO rgpd_retencion
    USING (ultimo < now() - interval '24 hours');
```

La política ES el plazo: el rol de retención no puede tocar una fila dentro de ventana **aunque
el SQL de la pasada tuviera un bug** — el invariante vive en el motor, que es exactamente el
diseño de s295. (`service_role` tiene `rolbypassrls`, así que el camino del cerrojo no se
entera — mismo comentario que deja escrito la s295.)

**El gate ACL es un test, no una intención** (puerta 9): igual que
`tests/test_s277_p1_document_local_snapshot_v2_acl.py` fija el texto de su migración, un test
nuevo afirma que la 019 contiene RLS+FORCE y el REVOKE para cada tabla nueva, y el
`REVOKE ALL ON FUNCTION` + `GRANT EXECUTE ... TO service_role` de la RPC (§3.3). Si alguien
añade una tabla al panel sin frontera, la suite lo dice.

**Y las DOS migraciones terminan con `NOTIFY pgrst, 'reload schema';`** (ronda r1, S-M5): la
FASE D de la 016 existe porque ya pasó DOS veces que las tablas existían y PostgREST seguía
devolviendo 404 desde su caché (`migrations/016_allowlist_invitaciones.sql:396-402`) — y aquí
además hay una FUNCIÓN nueva, que el caché de PostgREST también tiene que redescubrir.

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
por-usuario. **Sobre el cerrojo, la frontera exacta y no la deseada** (ronda r1, F-M1): con
contar-al-admitir (§3.2), cuando `autenticar` lanza la excepción el +1 de `admitir` **ya está
escrito**. En la caída TOTAL no se cuenta nada (la RPC también falla y es fail-open, §3.5); en el
fallo PARCIAL (cerrojo vivo, lectura de usuarios caída) ese +1 se queda como el fantasma de §3.2:
decae solo, solo pesa por encima de `FALLOS_LIBRES`, y la página 503 dice «no eres tú», así que
no invita a re-teclear la contraseña en bucle. No se especifica una devolución: sería una segunda
RPC para un caso raro cuyo coste real es el margen que el cerrojo de hoy ya da — **5 intentos**
(`fallos <= FALLOS_LIBRES` deja pasar con 4, así que bloquea a partir del sexto; cifra corregida
en r2, S2-m2).
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
    sello: str              # opaco, SIEMPRE no vacío — sin default a propósito (r4, S4-M4)

class Backend(Protocol):
    def autenticar(self, usuario: str, contrasena: str) -> Usuario | None: ...
    def sello(self, nombre: str) -> str | None: ...
```

**`sello` es obligatorio, sin default** (ronda r4, S4-M4): la v6 le ponía `""` «para que los
constructores existentes no se rompan», y esa compatibilidad era FALSA — un doble viejo
construiría, el login emitiría `h=""` y la puerta expulsaría en la siguiente petición: una rotura
CONDUCTUAL escondida detrás de una de construcción. Sin default, cada constructor que falte se
rompe EN EL TEST, con traza, que es donde debe romperse; los dobles afectados están enumerados en
§13.

- **`sello(nombre)`** devuelve el sello VIGENTE de un usuario activo, `None` si no existe o está
  revocado, y lanza `IdentidadNoDisponible` si el transporte no responde (§1.3: `None` expulsa,
  la excepción es un 503 que no sirve nada y no mata la cookie). El sello es
  `b64url_sin_relleno(sha256(registro)[:12])` — la MISMA variante base64 que las claves del
  cerrojo (§3.1; ronda r4, F4-m2) — y cambia exactamente cuando cambia la contraseña.
- **Al entrar**: `autenticar` lee la fila UNA vez, verifica scrypt y devuelve
  `Usuario(nombre, sello)` — sin segunda lectura ni ventana entre leer y sellar. El payload de la
  cookie pasa de `{u, csrf, iat, exp}` (medido en `sesion.py:8`) a llevar también `h = sello`.
- **En cada petición**, la puerta (`despachar`, tras `sesion.verificar`) añade UNA comprobación,
  con la regla completa escrita (ronda r2, F2-m1): sea `h = payload.get("h")`; **si `h` no es una
  cadena no vacía → fuera** (cookies de antes del despliegue, que no llevan `h`; nunca una
  excepción — `compare_digest` no llega a ver un `None`); si `backend.sello(u)` es `None` →
  fuera; si `sello != h` (`hmac.compare_digest`, la disciplina de `sesion.py:160-167`) → fuera.
  «Fuera» es siempre el mismo camino: 303 a `/entrar` borrando la cookie. Revocar y cambiar la
  contraseña expulsan en la **siguiente petición** — que es la promesa por la que Alberto
  eligió (a2).
- **Una excepción, con motivo: `POST /salir` NO revalida el sello** (ronda r4, S4-m1). Borrar tu
  propia cookie no puede depender de que Supabase responda: con la base caída, un `/salir`
  revalidado daría 503 y dejaría VIVA la cookie que el usuario intentaba destruir. El logout
  verifica firma y CSRF en local (todo lo que necesita) y borra — no lee ni escribe nada de
  nadie, así que saltarse la revalidación no abre ninguna puerta.

**Por qué `h` puede viajar en una cookie firmada y no cifrada** (el contrato de
`sesion.py:23-27` es «no meter material sensible», no «cifrar»): el sello es un truncado de
SHA-256 sobre un registro que contiene una sal aleatoria de 16 bytes (`auth.py:71,117`) — no es
invertible, no permite diccionario (la sal no se conoce) y no sirve para entrar. Lo único que
revela es «la credencial cambió», que es su función.

**`BackendEntorno` implementa `sello` igual** (digest del registro de la variable), así que la
paridad de la v2 §1.2 se mantiene: el modo local sigue funcionando y la sustitución es un backend
más, no una excepción. Los dobles de los tests ganan el método Y el campo (S4-M4): la migración
de tests es explícita, pequeña y visible — no una compatibilidad aparente que rompe en runtime.

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
u:<hmac>   donde hmac = b64url_sin_relleno( HMAC-SHA256(K, usuario)[:16] )
ip:<hmac>  donde hmac = b64url_sin_relleno( HMAC-SHA256(K, ip)[:16] )
K = HMAC-SHA256(DASHBOARD_SECRET, "panel_intentos:v1")   # clave DERIVADA, no el secreto a pelo
```

El contrato criptográfico, completo (ronda r3, S3-m1): truncado a **16 bytes** (128 bits — de
sobra para claves de un contador cuyo universo real son decenas de valores; el truncado corto que
invitaría colisiones queda fuera por contrato, no por costumbre) y **base64url sin relleno** — la
variante URL-safe de `sesion._b64`, que es la que casa con el regex de la puerta 5.

Cada intento fallido escribe DOS filas; `bloqueado` es el máximo de las dos esperas. Rotar IP ya
no da intentos ilimitados contra un usuario (su fila `u:` sigue contando); rotar usuario no
esquiva el límite de una IP (su fila `ip:` sigue contando). La clave se deriva con etiqueta de
propósito para no reutilizar el secreto de firma de cookies en otro rol.

**Precio del acoplamiento, declarado** (ronda r1, F-m3): rotar `DASHBOARD_SECRET` — el botón de
pánico ante una cookie robada (`sesion.py:12-15`) — rota también `K`, deja huérfanas las filas de
intentos y le da al atacante contadores frescos en plena crisis. Se acepta en vez de añadir un
secreto dedicado: el coste son **5 intentos** de margen por clave (`FALLOS_LIBRES + 1`, la cifra
exacta del cerrojo de hoy — corregida en r2, S2-m2) sobre el suelo scrypt (~100 ms/intento), el
evento es raro y manual, y un pepper propio sería una variable más que generar, rotar y perder
(§10).

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

`admitir` es UNA función en la base (§3.3) que, en una sola transacción: poda lo caducado;
**siembra las filas que falten** (`INSERT ... ON CONFLICT DO NOTHING`, en orden estable de
claves) — porque `FOR UPDATE` **no puede bloquear una fila que no existe** (ronda r1, S-C3: sin
la siembra, la primera ráfaga contra una clave fresca vería «ausente» N veces y entraría entera);
**después** toma las filas con `FOR UPDATE` en ese mismo orden (dos llamadas concurrentes se
serializan, sin interbloqueo, y la que espera relee la versión ya confirmada — EvalPlanQual bajo
READ COMMITTED, el MISMO mecanismo con el que el canje gana a dos pulsadores simultáneos,
`src/logging_db.py:782-796`); calcula la espera con la fórmula de hoy (`auth.py:313-322`:
`min(base·2^(fallos-libres-1), max)` desde `ultimo`); si alguna clave está cerrada devuelve la
espera **sin incrementar** (hoy un intento bloqueado tampoco suma — `app.py:285-292` corta antes
de `fallo`; la fila sembrada con `fallos=0` que pueda quedar es inerte y la poda la recoge); si
no, incrementa las dos y devuelve `0.0`.

- **El rebaño queda acotado**: la petición concurrente K espera el lock de la fila (que la
  siembra garantiza existente) y ve los K−1 incrementos anteriores, así que con
  `FALLOS_LIBRES = 4` entran ~5, no N — también en el primer asalto a una clave fresca. Es la
  semántica que el umbral prometía.
- **`acierto` limpia CON los fallos del atacante dentro, y es heredado, no un descuido**
  (ronda r1, S-M1): si el legítimo entra mientras un atacante martillea su usuario, el DELETE de
  la clave `u:` borra también los fallos acumulados del atacante — exactamente lo que hoy hace
  `Cerrojo.acierto` (`auth.py:338-341`, «un login bueno limpia el historial de esas claves»). El
  atacante NO queda libre: su clave `ip:` es suya, no del legítimo, y sobrevive al acierto. La
  puerta 4 cubre este entrelazado afirmando la semántica DOCUMENTADA, para que nadie la «arregle»
  sin decidirlo.
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
(`ultimo < now() − retencion`); (2) **si el recuento MÁS las claves que esta llamada va a
sembrar supera el cap** (`count + nuevas > cap` — la aritmética exacta, corregida en r2, S2-M3:
«si está al cap» dejaba colar `cap + nuevas − 1`), sacrifica lo más antiguo hasta que la siembra
quepa — «perder un bloqueo vivo regala una tanda de intentos; quedarse sin memoria regala el
servicio» vale igual cambiando memoria por tabla. El cap viaja como argumento; el índice sobre
`ultimo` hace ambas fases baratas.

**Para que el cap sea un techo y no una intención** (ronda r2, S2-M2): llamadas concurrentes con
claves DISJUNTAS no comparten locks de fila, así que podrían comprobar «bajo el límite» a la vez
y superarlo al insertar. `panel_puerta` toma
`pg_advisory_xact_lock(hashtext('panel_intentos'))` al empezar — y **la semántica real se declara
sin eufemismo** (ronda r3, F3-m2): un advisory lock DE TRANSACCIÓN se retiene hasta el COMMIT, no
hasta el final de una «fase», así que **cada `admitir` se serializa ENTERO contra los demás**. El
`acierto` (un DELETE por PostgREST) y las lecturas no lo tocan. A la escala de este panel,
serializar los intentos de login es gratis y es exactamente el invariante del cerrojo en memoria
(un dict de un solo proceso también atiende de uno en uno); la siembra + `FOR UPDATE` en orden
estable de §3.2 queda como SEGUNDA capa — hoy redundante bajo el lock global, y lo que sostiene
la corrección si algún día alguien estrecha ese lock.

La retención tiene ahora **constante fuente** (ronda r1, S-M3): `CERROJO_RETENCION_S = 24 * 3600`
nace junto a las demás del cerrojo (`auth.py:285-295`) y viaja como argumento igual que ellas —
en la v3 el argumento `retencion_s` existía sin que ninguna constante lo definiera. Consecuencia
RGPD: la poda ES el plazo de retención, y su red para el caso residual está en §6.

### 3.5 Indisponibilidad — conservado de la v2, con la frontera exacta

**Fail-open en el contador, fail-closed en la identidad — y la frontera partida por lo que cada
estado ES** (ronda r2, F2-M2: `tabla_ausente` y `sin_credenciales` no son transporte transitorio,
son configuración PERSISTENTE, y tratarlos como fail-open dejaba la protección anti-fuerza-bruta
apagada en silencio, indefinidamente):

- **La frontera del fail-open es «¿se pudo HABLAR?», no el estado `error`** (ronda r4, S4-M1: el
  vocabulario aplana CUALQUIER 4xx/5xx en `ERROR` — `datos.py:92-100` — y un 400 por firma de la
  RPC, un 401/403 de ACL o un error SQL son defectos PERSISTENTES que habrían dejado el cerrojo
  apagado para siempre bajo la etiqueta «transitorio»). La regla, en el transporte del cerrojo:
  **fallo de conexión** (la rama `httpx.HTTPError` — timeout, DNS, red: PostgREST no llegó a
  responder) → fail-open: el intento se permite, scrypt sigue corriendo (~100 ms de suelo,
  `auth.py:24-25,273`) y **cada ocurrencia deja un log a nivel ERROR**. **Cualquier RESPUESTA
  HTTP ≥ 400 de la RPC** → PostgREST habló y algo está mal de forma reproducible (firma,
  permisos, función ausente, SQL): es la clase configuración de abajo → 503. Precio declarado: un
  5xx pasajero de PostgREST cae del lado cerrado — aceptable, porque la identidad (mismo
  Supabase) estaría fallando igual y el panel entero ya está en 503.
- **`tabla_ausente` / `sin_credenciales` (configuración)** → un despliegue mal hecho, y la
  respuesta es **fail-closed en TODAS las capas** (ronda r3, S3-M1: la v5 los degradaba en
  runtime a fail-open+log, y un log no sustituye al fail-closed para un estado PERSISTENTE — con
  el smoke omitido, el panel habría operado sin cerrojo indefinidamente). Tres capas, mismas
  conductas: (1) **arranque**: con `CerrojoSupabase` enchufado, `comprobar_arranque` llama a
  `panel_puerta` con la lista de claves VACÍA — una sonda real de extremo a extremo (función
  migrada, GRANT concedidos, caché de PostgREST recargada) **sin efecto sobre ningún contador**
  (sí ejecuta la poda de caducados y toma el lock un instante — efectos benignos, dichos: F3-m1);
  si falla, el deploy no arranca con el motivo escrito — el criterio de `validar_configuracion`
  (`auth.py:370-377`). (2) **runtime** (donde el `lifespan` no corrió, §9): `admitir` con
  CUALQUIER respuesta ≥400 — `tabla_ausente` y `sin_credenciales` incluidos, y también la firma
  mala, la ACL y el SQL roto que S4-M1 sacó de la etiqueta «transitorio» — **NO degrada a
  fail-open**: la entrada responde el MISMO 503 de configuración que `IdentidadNoDisponible`
  (§1.3), porque un panel que no puede contar intentos por estar mal desplegado no debe estar
  atendiendo logins; simetría exacta con la identidad, cuyo mismo estado también es 503.
  (3) **smoke del runbook**: la misma sonda, como primer paso.
- **Una espera devuelta por la función JAMÁS se ignora.** Y la identidad va al revés: sin base no
  entra nadie (§1.3).

## 4. El enlace único — M2 y M3

### 4.1 Sin PRG: el render del POST se queda — el medio M2

Sol tenía razón otra vez: tras un 303, el GET no puede reconstruir un token que no está
almacenado en ninguna parte; un «canal flash» habría que guardarlo en algún sitio (cookie, tabla)
— y eso es persistir el secreto que la regla de `gestion.py:16-24` existe para no persistir. La
esta propuesta retira el PRG de la emisión y CONSERVA lo que el código ya hace deliberadamente
(`app.py:730-735`): el enlace se enseña en la respuesta del POST que lo crea, una vez, nunca en
una URL. El problema que el PRG intentaba arreglar (el F5 reenvía el formulario) lo arregla §4.2
donde de verdad está: en no crear la segunda credencial.

Y una deuda de prosa que esta sección no puede dejar viva (ronda r1, F-m1): el docstring de
`gestion.py:20-24` dice «de ahí el POST-redirect-GET…» describiendo un PRG que **nunca existió**
(`app.py:730-735` renderiza, deliberadamente y con su precio escrito). El cableado reescribe ese
párrafo — la misma disciplina que §7 exige para el comentario de `datos.py`: ningún racional
vigente contradiciendo al código.

### 4.2 Idempotencia por OPERACIÓN, no por contenido — el medio M3

La clave de la v2 (nota+días+operador+ventana) confundía un reintento con una segunda emisión
legítima: misma persona pidiendo dos invitaciones iguales en la misma ventana → bloqueada; el
mismo F5 cruzando la frontera de la ventana → duplicado. Se identifica **la petición**, no su
payload:

- El formulario de invitar lleva un campo oculto `op` — un token aleatorio
  (`secrets.token_urlsafe(16)`) generado al PINTAR el formulario.
- `bot_invitaciones` gana la columna, y **obligatoria también para las filas nuevas** (ronda r2,
  S2-M6: `UNIQUE` nullable admite infinitos NULL y no obliga a nadie):
  `op TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::text` con
  `CHECK (char_length(op) BETWEEN 8 AND 64)`. El `DEFAULT` es lo que permite el `NOT NULL` sin
  romper a NADIE: las filas históricas lo reciben en el propio `ADD COLUMN` (un default VOLÁTIL
  se evalúa POR FILA en Postgres — cada fila vieja recibe un valor distinto, el UNIQUE no choca),
  y el CLI de invitaciones (`scripts/s324e_invitaciones.py:207-208`), que no envía `op`, queda
  cubierto con la semántica correcta — cada invocación del CLI ES una operación distinta.
  Migración `migrations/020_invitaciones_op.sql`, con su `GRANT INSERT (op)` añadido al grant por
  columnas de la 016.
- El POST inserta con su `op`. Un F5 reenvía el MISMO `op` → violación de UNIQUE → el
  panel responde «ya emitiste esta invitación: está en la lista. El enlace sólo se enseñó al
  crearla; si lo perdiste, anúlala y emite otra.» — sin crear nada y sin fingir que puede
  re-enseñar el enlace.
- **Y el mecanismo del mensaje se declara, no se supone** (ronda r3, F3-M1): hoy `_escribir`
  aplanaría ese rechazo en «Supabase respondió 409» (`gestion.py:104-105` — su vocabulario no
  tiene cómo decir «duplicado»). El vocabulario de escritura gana UN estado, `DUPLICADO`,
  detectado por el código PostgREST de violación de unicidad (`23505`) en el cuerpo del error —
  la misma técnica con la que `_escribir` ya distingue `tabla_ausente` por `_CODIGOS_AUSENTE`
  (`gestion.py:97-103`). Solo el camino de emitir lo consume; para el resto de escrituras un
  duplicado sigue siendo el error que es.
- Una segunda emisión INTENCIONAL sale de un formulario recién pintado → `op` nuevo → segunda
  fila. Dos pestañas = dos formularios = dos `op` = dos invitaciones — correcto, porque son dos
  operaciones.

`op` es ruido aleatorio sin dato personal; no entra en la matriz. Las otras dos escrituras del
panel no necesitan idempotencia nueva: anular y revocar son condicionales por su PATCH
(`gestion.py:264-274, 295-301` — el segundo intento afecta 0 filas y lo dice). Pero una de las
dos está ROTA hoy por otra vía, y es el §4.3.

### 4.3 El GRANT que la anulación necesita y no tiene — el crítico S-C1 de la ronda r1

Hallazgo de Sol, verificado contra los dos ficheros: la anulación firma en la nota —
`gestion.py:271-273` escribe `{"revocada_at": ..., "nota": _nota_con_firma(...)}` (dúo r41 de
s324f: «la anulación quedaba sin firmar») — pero el GRANT de columnas de la 016 sólo concede
`UPDATE (canjeada_at, canjeada_por, revocada_at)` sobre `bot_invitaciones`
(`migrations/016_allowlist_invitaciones.sql:321-322`). Contra un Supabase real, ese PATCH entero
muere con `42501`: **anular una invitación no funciona hoy** — es un defecto LATENTE que los
tests sin red no pueden ver y que r41 introdujo arreglando otro (la firma). La v3 lo heredaba
presentando la anulación como «ya idempotente».

**El cierre NO es conceder la nota — es retirar el parche entero** (ronda r2, S2-M4: la firma
en la nota existía SOLO porque «añadir columna exige migración», `gestion.py:219-224`; con la 020
abierta, esa justificación desaparece, y concederle `UPDATE (nota)` a la 020 habría perpetuado el
parche: texto de auditoría mezclado con texto humano, truncado a 500 chars, y una columna de
persona editable en general). La 020 hace lo estructural:

```sql
ALTER TABLE public.bot_invitaciones ADD COLUMN revocada_por TEXT;
UPDATE public.bot_invitaciones
    SET revocada_por = '(anterior a la 020)' WHERE revocada_at IS NOT NULL;
ALTER TABLE public.bot_invitaciones ADD CONSTRAINT bot_invitaciones_revocacion_completa CHECK (
    (revocada_at IS NULL AND revocada_por IS NULL)
    OR (revocada_at IS NOT NULL AND revocada_por IS NOT NULL)
);
GRANT UPDATE (revocada_por) ON public.bot_invitaciones TO service_role;
```

— el patrón LITERAL de `bot_allowlist_revocacion_completa`
(`migrations/016_allowlist_invitaciones.sql:224-228`), con el backfill que hace posible el CHECK
estricto sobre las filas ya anuladas. `_nota_con_firma` se retira; el panel escribe
`revocada_por = 'panel:<usuario>'` (la misma forma que `revocado_por` en la allowlist,
`gestion.py:300`) y el CLI — que hoy anula escribiendo solo `revocada_at`
(`scripts/s324e_invitaciones.py:379`) y violaría el CHECK — pasa a firmar también:
`revocada_por = 'cli:<quien>'`. La nota vuelve a ser SOLO el «para quién es».

**Y el CLI hereda además el PATCH condicional del panel** (ronda r3, S3-M2 — verificado:
`cmd_revocar_invitacion` comprueba `canjeada_at` en Python y luego PATCHea INCONDICIONAL con solo
`id=eq.` (`scripts/s324e_invitaciones.py:357-381`): si alguien canjea entre la lectura y la
escritura, el CLI marca revocada una invitación YA canjeada e imprime «anulada» — mintiendo,
porque el acceso quedó concedido). El cierre es el que el panel ya usa
(`gestion.py:264-274`): condiciones `revocada_at=is.null&canjeada_at=is.null` EN el PATCH, y con
0 filas afectadas decir la verdad («no se ha anulado: se canjeó o se anuló mientras mirabas»).
**Lo que NO se añade, con motivo**: un CHECK que prohíba `canjeada_at` y `revocada_at`
simultáneos. Con los dos escritores condicionales ese estado ya no es producible, y el CHECK
exigiría reescribir la historia si alguna fila legada lo tiene — los CHECK nuevos afirman lo que
los escritores garantizan de aquí en adelante, no falsifican lo que pasó.

La lección estructural va a la puerta 9-bis: **cada columna que el panel o el CLI escriben debe
estar en un GRANT** — un test estático cruza los payloads de escritura con los GRANT de las
migraciones, para que el PRÓXIMO r41 no pueda volver a abrir esta clase de agujero en silencio.

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
- **Respuesta VACÍA → `verificar(contrasena, _SENUELO)` y `None`** (`auth.py:197-202`): el coste
  scrypt (~100 ms, dominante sobre el jitter de red) se paga igual exista o no el usuario, y el
  mensaje de la página sigue siendo uno solo (`app.py:297-301`). **Transporte caído →
  `IdentidadNoDisponible`, sin señuelo** — la conducta es la de §1.3 (503 uniforme) y NO ésta: la
  v3 prescribía aquí las dos a la vez y el dúo lo cazó por ambos lados (S-C2 y F-C1). El señuelo
  existe para que «no existe» y «contraseña mala» tarden lo mismo; una caída no distingue
  usuarios (falla igual para todos, antes de tocar credencial alguna), así que no necesita
  señuelo — necesita no mentir.
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
  Entra en la matriz de retención con fila propia: **plazo `CERROJO_RETENCION_S` (24 h),
  ejecutado por la poda de §3.4 en cada escritura**, finalidad «seguridad del panel (control de
  fuerza bruta)». **Y el caso residual (cesa el tráfico, nadie poda) NO va a un runbook manual**:
  la v3 decía «pg_cron sería infra nueva» y era FALSO (r1, S-M3) — el mecanismo mensual
  automatizado YA existe, **con su estado dicho sin inflarlo** (ronda r4, F4-m1):
  `public.rgpd_retencion_pasada` está APLICADA con su job de pg_cron ACTIVO y verificado y un
  dry-run con ROLLBACK — cero pasadas reales todavía; el primer recibo real se espera el 1-sep
  (`docs/RGPD_RETENCION.md:139-150`). Es mecanismo verificado, no mecanismo ya ejercido, y la red
  del residuo cuelga de él con ese estado declarado. **Y el verbo
  correcto no es «ampliar» — es INSTANCIAR el patrón** (ronda r3, S3-M4: el autocontrol de esa
  función afirma el mecanismo sobre EXACTAMENTE cuatro tablas, exige exactamente UNA política por
  tabla y verifica el texto del predicado de 24 meses; su recibo lleva UN `corte`
  (`20260805150000_s299_job_programado_v1.sql:176-228`) — meterle una quinta tabla con OTRA
  ventana era editar un contrato vivo endurecido por su propio dúo). La 019 crea una función
  HERMANA pequeña, `panel_retencion_pasada(p_origen)`, con las mismas tres piezas del patrón:
  corre como `rgpd_retencion` con el cinturón de `current_user`, **aserta SU ventana** (RLS
  forzada + exactamente una política `rgpd_retencion_ventana` sobre `panel_intentos` con el
  predicado de 24 h) antes de tocar nada, y deja SU recibo en `rgpd_recibos` (`origen`
  manual/cron, `corte = now() − 24 h`, `resultado = {"panel_intentos": N}`). Un segundo schedule
  de pg_cron, cero ediciones a la función de 24 meses. **Y los DOS controles del precedente que
  la v6 no trasladó** (ronda r4, S4-M3 y F4-M1 — convergentes): (a) el **REVOKE NOMINAL** de
  EXECUTE — `FROM PUBLIC, anon, authenticated, service_role` — porque los default privileges de
  Supabase conceden EXECUTE sobre toda función nueva de `public` y revocar solo PUBLIC los deja
  puestos (la clase que s296→s299 sufrió VIVA en producción; el patrón literal:
  `s299_job_programado_v1.sql:333-340`); (b) la **postcondición del reloj**: si pg_cron está
  disponible, el job de la hermana DEBE existir ACTIVO, con comando y horario exactos y un
  `username` que puede asumir `rgpd_retencion` — imposible el «migración en verde sin programar
  nada» (`s299_job_programado_v1.sql:466-496`). Ambos entran al gate de la puerta 9.
  Granularidad declarada: 24 h operativas por la poda, red mensual automatizada para el residuo.
- **`panel_usuarios` es dato personal en claro** (nombres de usuario reales, quién dio el alta,
  cuándo): fila propia en la matriz, supresión a petición aparte de la baja lógica (como declara
  la 016 para la allowlist, `migrations/016_allowlist_invitaciones.sql:230-234`), y entra en el
  **paquete del abogado** — que DEC-231 ya exigía para el panel entero. **Con su plazo, no en
  blanco** (ronda r3, S3-M5): las filas ACTIVAS viven mientras el usuario tenga acceso (es la
  credencial); las REVOCADAS conservan la traza con plazo **`[DECIDIR: Alberto]`** — el mismo
  dispositivo y el mismo cajón de decisión pendiente que el canon usa para `user_consent`
  (`docs/RGPD_RETENCION.md:221`), con dueño nombrado, en vez de un «indefinido» que nadie
  decidió.
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
  control compensatorio, y gana dos pasos: la sonda del cerrojo (`panel_puerta` con claves
  vacías, §3.5 — la misma que el arranque ejecuta donde el `lifespan` sí corre) y el smoke del
  cerrojo con dos procesos concurrentes contra el despliegue real — la capa PostgREST que el
  contenedor de la puerta 4 no lleva.
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
| AMPLIAR `rgpd_retencion_pasada` con `panel_intentos` (la v5) | Su autocontrol afirma EXACTAMENTE 4 tablas, una política por tabla y el predicado de 24 meses, y su recibo un solo `corte` (s299:176-228): meterle otra tabla con otra ventana es editar un contrato vivo endurecido por su dúo. Se instancia el patrón en una función hermana (§6) |
| Un MECANISMO de retención paralelo (rol/recibos/scheduler propios) | El patrón s299 (rol + ventana-como-política + recibo + pg_cron) ya existe y se reutiliza entero; solo la función y su schedule son nuevos. La v3 descartaba «pg_cron» creyéndolo infra nueva — era falso |
| Runbook manual para el residuo de retención (la v3) | Un DELETE que depende de que alguien se acuerde no es retención; el mecanismo automatizado existe y tiene recibo (§6) |
| Pepper propio (`PANEL_INTENTOS_PEPPER`) para `K` | Un secreto más que generar, rotar y poder perder, para comprar 5 intentos por clave en un evento raro y manual (rotar `DASHBOARD_SECRET`); el precio se declara en §3.1 en vez de añadir superficie |
| Devolver el +1 cuando `autenticar` lanza `IdentidadNoDisponible` | Segunda RPC (PostgREST no decrementa) para un fallo PARCIAL raro cuyo coste son 5 intentos de margen que decaen solos (§1.3) |

## 11. Las puertas (todas ejecutables sin red, salvo donde se declara)

1. **Revocación efectiva**: sesión abierta → `activo = FALSE` → la siguiente petición redirige.
   Control: un usuario activo no es expulsado.
2. **Cambio de contraseña**: cambia el registro → sello distinto → fuera. Control: mismo
   registro → dentro. Y el caso legado (ronda r2, F2-m1): una cookie firmada VÁLIDA pero sin `h`
   (o con `h` que no es cadena) → fuera por el camino normal, sin excepción.
3. **Fail-closed declarado**: backend con transporte caído → nadie entra (503 de estado, no «
   credenciales incorrectas») y a los de dentro no se les sirve NINGÚN dato (503 sin matar la
   cookie); al volver la base, el revocado es expulsado en su primera petición. Es la conducta
   elegida (§1.3), probada, no un accidente.
4. **Admisión atómica (semántica)**: contra el doble en memoria con `admitir`: (a) N llamadas
   «concurrentes» admiten como mucho `FALLOS_LIBRES + 1`; (b) la tabla de casos secuenciales
   (fallos→espera) del cerrojo de hoy se reproduce idéntica; esa misma tabla va como
   comentario-contrato en el SQL; (c) **el entrelazado con `acierto`** (ronda r1, S-M1): legítimo
   entra mientras el atacante martillea → la clave `u:` se limpia (semántica heredada de
   `auth.py:338-341`, afirmada como DOCUMENTADA) y la clave `ip:` del atacante conserva sus
   fallos. **Y la concurrencia REAL sí se ejercita** (ronda r2, S2-M2 — mi «no hay Postgres en
   la suite» era un gap falso): el repo ya levanta un PostgreSQL desechable en CI para verificar
   el EFECTO y no el texto (`tests/test_s295_rgpd_integracion_pg.py` +
   `.github/workflows/s295-rgpd-retencion-pg.yml`, gateado por `RGPD_TEST_DATABASE_URL`, lección
   #60: «verificar el EFECTO, no el código»). `panel_puerta` recibe el mismo tratamiento: un test
   de integración que aplica la 019 entera y ejercita con hilos la ráfaga sobre clave fresca
   (admite ≤ `FALLOS_LIBRES + 1`), el cap con siembra concurrente, la POLICY de ventana del rol
   de retención, y que un rol sin EXECUTE no puede llamar a la función. La suite sin red sigue
   cubriendo la semántica con el doble; **gap restante declarado**: el contenedor es Postgres, no
   Supabase (PostgREST y su caché solo se prueban en el smoke post-deploy de §9).
5. **Sin identificadores en claro en el cerrojo**: las claves que salen hacia la tabla casan con
   `^(u|ip):[A-Za-z0-9_-]+$` y no contienen ni el usuario ni la IP de entrada.
6. **Señuelo preservado**: en las cuatro ramas de credencial de `autenticar` (acierta, falla, no
   existe, inactivo) `verificar` corre exactamente una vez; en la rama de transporte caído NO
   corre y se lanza `IdentidadNoDisponible` (§5 — la conducta única que la ronda r1 exigió).
6-bis. **Charset atado en los dos lados**: una tabla de casos (nombres válidos e inválidos)
   compartida que el CHECK SQL de §1.1 y el guard Python de §5 deben aceptar/rechazar igual — el
   regex vive duplicado por necesidad y esta puerta impide que diverja.
7. **Idempotencia por operación**: mismo `op` dos veces → una invitación y el mensaje sin enlace;
   `op` distinto → dos invitaciones.
8. **Columnas en los dos sentidos**: una columna nueva de una vista no se pinta; una declarada
   que desaparece se detecta sin romper la página (§7).
9. **ACL en el texto de las migraciones** (estilo `test_s277_p1_..._acl.py`): RLS+FORCE+REVOKE
   por cada tabla nueva; los CUATRO GRANT enumerados de `panel_intentos` a `service_role` y los
   dos (+POLICY de ventana) a `rgpd_retencion`; `REVOKE ALL ON FUNCTION` + `GRANT EXECUTE ...
   service_role` para `panel_puerta`; **para `panel_retencion_pasada`, el REVOKE NOMINAL
   (`PUBLIC, anon, authenticated, service_role`) y la postcondición del job activo** (ronda r4,
   F4-M1/S4-M3 — sin esto la hermana nacía ejecutable por la API por los defaults de Supabase);
   `GRANT INSERT (op)`, la columna `revocada_por` con su CHECK+backfill y
   `GRANT UPDATE (revocada_por)` en la 020; y el `NOTIFY pgrst, 'reload schema'` presente en
   ambas.
9-bis. **Toda columna escrita tiene su GRANT**: un test estático cruza cada payload de escritura
   de `gestion.py` y del CLI, **y cada sentencia del cuerpo de `panel_puerta`** (ronda r2,
   F2-M1: la RPC es INVOKER y ejerce los mismos GRANT), con los GRANT por columnas de las
   migraciones — la clase de agujero de S-C1 (r41 firmó en `nota` sin que la 016 la concediera)
   no puede volver a entrar en silencio.
10. **Sin red**: toda la suite del panel corre sin credenciales — la lección de s324h sigue
    vigente; los backends nuevos reciben su transporte inyectado (un doble de `datos.leer` y del
    POST de la RPC).
11. **Alta estricta** (ronda r4, S4-M2): el script de alta RECHAZA un registro con sal o hash de
    longitud distinta a la canónica (16/32) o con parámetros extra — los casos que `_partir`
    tolera y `verificar` jamás validará (§1.1). Control: el registro que emite
    `hash_contrasena` pasa.

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
usuarios en el panel; no toca el war room; no prueba PostgREST ni su caché en CI (la concurrencia
y las ACL de Postgres SÍ se ejercitan en el contenedor de la puerta 4; lo que queda para el smoke
post-deploy es la capa PostgREST/Supabase); no devuelve el +1 provisional en el fallo parcial
(§1.3, fantasma declarado); no garantiza el `lifespan` en Vercel (§9 y §3.5, controles
compensatorios); y deja sin inspeccionar las mismas dependencias externas que las rondas
anteriores declararon (documentación de Vercel, DNS/WAF, esquema realmente aplicado en Supabase,
y el código exacto de PostgREST para «función ausente» — que el test de integración de la puerta
4 no puede fijar, porque el contenedor no lleva PostgREST).

## 13. Alcance real y secuencia

Tamaño honesto: **2 migraciones** (019: `panel_usuarios` + `panel_intentos` + `panel_puerta` +
ACL enumerada —incluidos los GRANT+POLICY del rol `rgpd_retencion`— + NOTIFY; 020:
`bot_invitaciones.op NOT NULL DEFAULT` + `revocada_por`+CHECK+backfill + sus GRANT + NOTIFY),
**1 módulo nuevo** (`dashboard/cerrojo.py`), **1 script de operación** (alta/revocación de
usuarios del panel con la service key, validando con `validar_registro_estricto` — no con
`_partir` a secas, que es exactamente lo que S3-M3/S4-M2 tumbaron — antes de emitir el INSERT),
tocados `auth.py` (Usuario.sello, Backend.sello, BackendSupabase, IdentidadNoDisponible, admitir,
`CERROJO_RETENCION_S`, `validar_registro_estricto`), `sesion.py` (SOLO su docstring: la
enumeración del payload en `sesion.py:8` gana `h` — la deuda de prosa de F3-m3; el código no
cambia, el payload es un dict), `app.py` (puerta con sello + 503; cerrojo nuevo; op en el
formulario), `gestion.py` (op + estado `DUPLICADO`; `revocada_por` en vez de `_nota_con_firma`;
docstring del PRG que nunca fue), `scripts/s324e_invitaciones.py` (el CLI firma `revocada_por` y
adopta el PATCH condicional), `datos.py` (select explícito de vistas + comentario),
`api/index.py` (enchufe), la función hermana `panel_retencion_pasada` + su schedule (§6, en la
019), **1 test de integración
pg + su workflow** (puerta 4, patrón s295), y ~13 puertas de test sin red. Nota de numeración
(ronda r1, F-m2): «016» ya colisionó una vez (`016_allowlist_invitaciones.sql` /
`016_validacion_un_solo_uso.sql`) — al cablear, verificar que 019/020 siguen libres y citar
SIEMPRE el nombre completo.

**Dependencia de linaje, declarada** (ronda r4, F4-M2): el rol `rgpd_retencion` y la tabla
`rgpd_recibos` NO los crea ningún fichero de `migrations/` — nacen en
`supabase/migration_proposals/` (s295 y s299), aplicadas a mano. Dos consecuencias cableadas:
(a) la 019 abre con un guard fail-fast (`DO` block: si el rol o `rgpd_recibos` no existen,
`RAISE EXCEPTION` con el mensaje «aplica antes s295 y s299» — el criterio de los arranques del
repo: fallar con el motivo escrito, no a mitad de un GRANT); (b) el preámbulo del test de
integración pg (puerta 4) FABRICA ese entorno igual que el test de s295 fabrica el suyo: aplica
las dos propuestas versionadas y crea un `service_role` de contenedor **con `BYPASSRLS`** —
sin ese atributo, `panel_puerta` bajo RLS FORCE sin política para `service_role` vería cero
filas y el test probaría un mundo que no es el de Supabase.

**Secuencia**: (1) dúo sobre esta v7 — es autenticación, ALTO, el dúo es innegociable; las rondas
r1 (v3), r2 (v4), r3 (v5) y r4 (v6) ya corrieron y sus cuarenta y cinco hallazgos están cerrados
arriba;
(2) cablear en
sesión fresca SOLO si SÓLIDO (el criterio de DEC-237 sigue: el patrón de fallo era «no vi un
contrato escrito», y eso se caza con contexto limpio, no con más rondas aquí); (3) migrar,
desplegar con el runbook, y ejecutar la medición de XFF ANTES de dar el cerrojo-por-IP por
efectivo. El paso (3) incluye el smoke del cerrojo contra el despliegue real (la capa PostgREST
que el contenedor de CI no cubre).
