# s324e — Control de acceso al bot para el piloto con DGs (propuesta v1)

**Estado**: construido, **nada aplicado ni desplegado** (016 sin aplicar, Railway sin tocar,
sin commit). Cifras al pie. Impacto ALTO: toca serving, esquema y RGPD.

> **Este documento ya incorpora las correcciones del dúo (Sol, r1) y los tres refuerzos de
> Alberto.** La resolución hallazgo a hallazgo y el criterio de GO viven en el anexo
> `s324e_allowlist_duo_r1_v1.md`; aquí solo queda el diseño, ya corregido.

**Levers**: ninguno medido — ni `LEVER_DIGEST` ni el PLAN cubren control de acceso, así que no
hay «settled» que contrastar. Sí toca TECH_DEBT #(RLS): las tablas nacen con RLS forzada.

---

## 1. Recomendación

**Una puerta, dos tablas, tres flags.**

- **`bot_allowlist`** (quién puede entrar hoy) y **`bot_invitaciones`** (enlaces de un solo
  uso). Migración **016, NO aplicada**.
- **La puerta es un `TypeHandler` en el grupo −1** (`access_gate`) que lanza
  `ApplicationHandlerStop`. PTB evalúa los grupos de menor a mayor, así que **todo** handler
  —incluido el que alguien añada en marzo— nace detrás. No es un `if` por handler.
- **Orden: puerta → consentimiento.** Es **minimización**: con el consentimiento delante,
  cualquiera podría enviar `/accept Su Nombre` y guardaríamos su nombre e id en `user_consent`
  (plazo aún `[DECIDIR]`) para una finalidad que no existe. Dos excepciones nombradas:
  `/start` (el único que recibe el token) y `/privacidad` (s295).
- **Canje = UN update condicional** (`WHERE token_hash=… AND canjeada_at IS NULL AND
  revocada_at IS NULL AND expira_at > now()`). Bajo READ COMMITTED la segunda escritura
  re-evalúa su `WHERE` tras el COMMIT de la primera y afecta a 0 filas: entra una.
- **En la base vive el SHA-256, nunca el token**: protege las copias de SOLO LECTURA (backup,
  consola, export). **No protege de la service key** —quien la tenga se inserta una fila de
  allowlist— así que la frontera real es esa credencial. `token_urlsafe(24)` = 192 bits.
- **Solo chat privado**: la puerta rechaza grupos aunque el remitente esté autorizado — lo que
  se protege es dónde se PUBLICA la respuesta, no solo quién pregunta.
- **Fail-closed con matiz**: base caída + sí confirmado hace <1 h → entra (la ventana **no se
  renueva con el uso**); sin confirmación previa → **no entra nadie nuevo**. Tabla ausente =
  `indeterminado`, no `desconocido`. Y solo un `off` RECONOCIBLE apaga la puerta: una errata
  la deja puesta y aborta el arranque.
- **Bootstrap**: `BOT_ALLOWLIST_BOOTSTRAP` (ids, sin tocar base ni caché) **más** el
  `INSERT…SELECT` de la FASE B que da de alta a quien ya tiene consentimiento activo.
- **Tope**: `BOT_DAILY_LIMIT=30`, en memoria, con mensaje que explica qué pasa y cuándo vuelve.
- **`BOT_ALLOWLIST=off` por defecto**: el commit es inerte y el flag es el kill-switch.

**Despliegue**: el orden importa; está en la cabecera de la 016 y en `DG_DEPLOYMENT` §4.3.b.

## 2. Alternativas consideradas y por qué se descartan

| Alternativa | Por qué no |
|---|---|
| Allowlist solo en variable de entorno | Sin alta/baja/nota ni traza, y cada cambio exige deploy. **Se conserva** como bootstrap, no como mecanismo. |
| Comprobar el acceso en cada handler | Se olvida: el gate de consentimiento es de s21 y `feedback_callback` no lo tuvo hasta **s286**. |
| Consentimiento antes de la puerta | Guarda datos de no invitados (§1). |
| Guardar el token en claro | Convierte cualquier lectura de la tabla en un juego de llaves. |
| `SELECT` y luego `UPDATE` al canjear | Deja abierta la ventana de la carrera. |
| Función RPC `SECURITY DEFINER` (canje atómico) | Mejor en teoría; se descarta **por historia de este repo**: `rgpd_quedan_identificados` nació ejecutable por `anon` (s296→s299), y aquí sería un oráculo de canje expuesto a internet. Primera candidata si esto crece. |
| Tope contando `query_logs` | Un roundtrip por turno y ciego a las rutas que no se registran. |
| Fail-open cuando la base cae | Abre la puerta justo cuando no se puede comprobar nada. |
| Fail-closed puro, sin caché | Una caída de Supabase echa a los DGs a mitad de conversación. |
| bcrypt/argon2 para el token | Los KDF lentos protegen secretos de entropía baja; contra 192 bits no hay diccionario. |
| Gobernar grupos en vez de prohibirlos | Autorizar CHATS además de personas: otra tabla, otra revocación y otro modo de fallo, para un caso de uso que el piloto no tiene. |
| Puerta encendida por defecto | Cerraría el bot antes de aplicar la 016 (`main` auto-despliega; las migraciones van a mano). |

## 3. Gaps y riesgos declarados

1. **El enlace reenviado a un tercero**: no se puede impedir con un deep-link. Se acota (un uso,
   2 días con máximo de 7, revocable) y se hace **visible en minutos** — un aviso a quien
   administra enfrenta «era para X» con «lo ha canjeado Y». Residual real, no cubierto.
2. **La 016 no se ha ejecutado en ningún Postgres** (sin docker/psql aquí): un error de
   sintaxis aparecería al pegarla, y el `GRANT UPDATE` sobre la columna de conflicto va sin
   verificar, marcado «VERIFICAR AL APLICAR».
3. **Una invitación PENDIENTE sobrevive a una revocación**: no se puede cruzar sola (sin
   canjear no tiene `telegram_user_id`), así que `revocar-acceso` las lista y avisa.
4. **El tope vive en memoria**: un redeploy regala el cupo; cuenta saludos.
5. **Latencia de revocación, medida**: ≤10 min con la base sana; ≤60 min con Supabase caído
   (la gracia). Los ids de bootstrap NO los alcanza `revocar-acceso`: van por variable.
6. **Un defecto en la puerta deja el bot inaccesible** (fail-closed deliberado). Salida sin
   deploy: los ids de bootstrap.
7. **Ninguna de las dos tablas cascadea desde `query_logs`**: la supresión a petición lleva
   dos líneas más, ya escritas en la matriz.
8. **Bot y script comparten `SUPABASE_SERVICE_KEY`**: los GRANT no separan operador de bot
   —eso lo hace el código— pero sí impiden lo que ninguno debe poder: borrar.
9. **`/start` no está medido**: exento de cupo, un desconocido fuerza una petición por intento.
10. **Sin dúo y sin smoke contra Telegram real**: el canje no se ha probado con un enlace real.

## 4. Por qué es BP, estructural y escalable

**Estructural**: la autorización deja de ser una condición repetida y pasa a ser una posición
en el pipeline de PTB; añadir un handler ya no es una oportunidad de olvidarse, y un test
impide registrar nada por delante. Es la disciplina del punto único de s324e, aplicada a la
entrada.

**BP**: secreto solo en hash; un solo uso resuelto por el motor, no por código; RLS forzada y
`GRANT` por columnas sin `DELETE`; vocabulario pinado entre capas; cada flag con su
kill-switch; y el dato personal declarado columna a columna antes de existir.

**Escalable a 30+ técnicos**: por update, una lectura cacheada 10 min (0 I/O en el caso normal);
el alta se delega en un enlace, no en un operador copiando ids; y la traza vive en la tabla, no
en la memoria de nadie. **No resuelve la identidad**: autoriza un `telegram_user_id`, no a una
persona — basta para el piloto, no para clientes finales.

---

## 5. Verificación (Protocolo 1)

Suite completa y detalle de la verificación: **anexo §5**. Aquí, lo esencial: 119 tests propios
verdes ($0, sin red ni DB), smoke real de solo lectura contra Supabase con las tablas ausentes,
y el viaje completo del DG —puerta rechaza → canje → puerta deja pasar → 2ª persona rebotada →
el mismo DG bloqueado en un grupo— ejercido offline sobre los handlers REALES.

**Aviso al revisor**: otro agente edita el repo en paralelo (`MISMATCH_ANSWER` en `flags.py`,
`turn_plan.py`, `conversation_policy_impl.py`, `runtime_trace.py`); hay que separar los dos
changesets al commitear. `src/flags.py` es el único fichero compartido.
