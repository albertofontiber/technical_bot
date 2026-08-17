# s324e — Control de acceso al bot para el piloto con DGs (propuesta v1)

**Estado (17-ago)**: **commiteado** (`df4752f`) y **016 APLICADA en producción** (costó dos
intentos, por un defecto del propio fichero — anexo §6). Falta lo que enciende el control:
`BOT_ALLOWLIST_BOOTSTRAP` y `BOT_ALLOWLIST=on` en **Railway, sin tocar**. Impacto ALTO.
**Levers**: ninguno medido; sí toca TECH_DEBT #(RLS).

> Incorpora las correcciones de los **dos** revisores y los refuerzos de Alberto. Resolución
> hallazgo a hallazgo, criterio de GO y verificación: anexo `s324e_allowlist_duo_r1_v1.md`.

---

## 1. Recomendación

**Una puerta, dos tablas, tres flags.**

- **`bot_allowlist`** (quién entra hoy) y **`bot_invitaciones`** (enlaces de un solo uso).
- **La puerta es un `TypeHandler` en el grupo −1** que lanza `ApplicationHandlerStop`. PTB
  evalúa los grupos de menor a mayor, así que **todo** handler nace detrás — incluido el que
  alguien añada en marzo. No es un `if` por handler.
- **Orden: puerta → consentimiento**, por **minimización**: con el consentimiento delante,
  cualquiera podría enviar `/accept Su Nombre` y guardaríamos su nombre e id en `user_consent`
  para una finalidad que no existe. Dos excepciones: `/start` (recibe el token) y
  `/privacidad` (s295).
- **El QUEMADO del token es atómico** — un update condicional (`WHERE token_hash=… AND
  canjeada_at IS NULL AND revocada_at IS NULL AND expira_at > now()`): bajo READ COMMITTED la
  segunda escritura re-evalúa su `WHERE` tras el COMMIT de la primera y afecta a 0 filas, así
  que de dos a la vez entra una. **Lo que NO es atómico es canje+alta**: son dos peticiones
  REST sin transacción común (se descartó la RPC, §2), con compensación y ventana declarada
  en §3.6.
- **En la base vive el SHA-256, nunca el token**: protege copias de SOLO LECTURA (backup,
  consola, export), **no de la service key** —quien la tenga se inserta una fila de allowlist—,
  así que la frontera real es esa credencial. `token_urlsafe(24)` = 192 bits.
- **Solo chat privado**: la puerta rechaza grupos aunque el remitente esté autorizado — lo que
  se protege es dónde se PUBLICA la respuesta, no solo quién pregunta.
- **Fail-closed con matiz**: base caída + sí confirmado hace <1 h → entra (la ventana **no se
  renueva con el uso**); sin confirmación previa → **nadie nuevo entra**. Tabla ausente =
  `indeterminado`. Y solo un `off` RECONOCIBLE apaga la puerta: una errata la deja puesta y
  aborta el arranque.
- **Bootstrap**: `BOT_ALLOWLIST_BOOTSTRAP` (sin tocar base ni caché) **más** el `INSERT…SELECT`
  de la FASE B, que dio de alta a quien ya tenía consentimiento.
- **Tope**: `BOT_DAILY_LIMIT=30` en memoria. **`BOT_ALLOWLIST=off` por defecto**: inerte, y es
  el kill-switch.

**Despliegue**: el orden importa; está en la cabecera de la 016 y en `DG_DEPLOYMENT` §4.3.b.

## 2. Alternativas consideradas y por qué se descartan

| Alternativa | Por qué no |
|---|---|
| Allowlist solo en variable | Sin alta/baja/nota ni traza, y cada cambio exige deploy. **Se conserva** como bootstrap. |
| Acceso comprobado en cada handler | Se olvida: el gate de consentimiento es de s21 y `feedback_callback` no lo tuvo hasta **s286**. |
| Consentimiento antes de la puerta | Guarda datos de no invitados (§1). |
| Guardar el token en claro | Convierte cualquier lectura de la tabla en un juego de llaves. |
| `SELECT` y luego `UPDATE` al canjear | Deja abierta la ventana de la carrera. |
| RPC `SECURITY DEFINER` (canje atómico) | Mejor en teoría; se descarta **por historia de este repo**: `rgpd_quedan_identificados` nació ejecutable por `anon` (s296→s299), y aquí sería un oráculo de canje expuesto a internet. Primera candidata si esto crece — el precio es el riesgo 6. |
| Tope contando `query_logs` | Un roundtrip por turno y ciego a las rutas que no se registran. |
| Fail-open cuando la base cae | Abre la puerta justo cuando no se puede comprobar nada. |
| Fail-closed puro, sin caché | Una caída de Supabase echa a los DGs a mitad de conversación. |
| bcrypt/argon2 para el token | Los KDF lentos protegen secretos de entropía baja; contra 192 bits no hay diccionario. |
| Gobernar grupos, no prohibirlos | Autorizar CHATS además de personas: otra tabla y otro modo de fallo, para un caso de uso que el piloto no tiene. |
| Puerta encendida por defecto | Cerraría el bot antes de aplicar la 016 (`main` auto-despliega). |

## 3. Gaps y riesgos declarados

1. **El enlace reenviado**: no se impide con un deep-link. Se acota (un uso, 2 días, máx. 7,
   revocable) y se hace **visible en minutos** — el aviso enfrenta «era para X» con «lo canjeó
   Y». Residual real.
2. ~~La 016 sin ejecutar~~ **RESUELTO**: aplicada el 17-ago. Queda sin ejercer el `GRANT
   UPDATE` sobre la columna de conflicto (solo se usa en una re-admisión).
3. **Una invitación PENDIENTE sobrevive a una revocación**: sin canjear no tiene
   `telegram_user_id`, así que `revocar-acceso` las lista y avisa.
4. **El tope vive en memoria**: un redeploy regala el cupo; cuenta saludos.
5. **Latencia de revocación** (derivada del diseño, anclada en test; sin medición e2e): ≤10 min con la base sana; ≤60 min con Supabase caído
   (la gracia). Los ids de bootstrap NO los alcanza `revocar-acceso`: van por variable.
6. **Canje y alta NO comparten transacción**: dos peticiones REST (se descartó la RPC). Si el
   alta falla se devuelve el token; si la devolución también falla, queda quemado sin alta.
   Ventana real, con compensación, ejercida en test.
7. **Sin plazo de conservación para las dos tablas** (art. 5.1.e): el job mensual no las
   alcanza —lo dice la propia 016— y `bot_invitaciones` guarda `nota` y `canjeada_por` (id
   DIRECTO, de quien puede no ser el destinatario) sin caducidad. **Gap material**: plazo y
   purga propuestos en `RGPD_RETENCION.md`; **decide Alberto, valida el abogado**.
8. **Un defecto en la puerta deja el bot inaccesible** (fail-closed deliberado). Salida sin
   deploy: los ids de bootstrap.
9. **No cascadean desde `query_logs`**: la supresión lleva dos líneas más, ya en la matriz.
10. **Bot y script comparten `SUPABASE_SERVICE_KEY`**: los GRANT no separan operador de bot,
   pero sí impiden lo que ninguno debe poder: borrar.
11. **`/start` no está acotado**: exento de cupo, un desconocido fuerza una petición por intento.
12. **Sin smoke contra Telegram real**: el canje no se ha probado con un enlace de verdad.
13. **Cachés acotadas a 10.000** con poda (caducado primero, negativos antes que positivos).
   Bajo riada, un positivo desalojado pierde su gracia degradada.

## 4. Por qué es BP, estructural y escalable

**Estructural**: la autorización deja de ser una condición repetida y pasa a ser una posición
en el pipeline de PTB; añadir un handler ya no es una oportunidad de olvidarse, y un test
impide registrar nada por delante. Es la disciplina del punto único de s324e, en la entrada.

**BP**: secreto solo en hash; el quemado del token resuelto por el motor; RLS forzada y `GRANT`
por columnas sin `DELETE`; vocabulario pinado entre capas; cada flag con su kill-switch; y el
dato personal declarado columna a columna antes de existir.

**Escalable a 30+**: por update, una lectura cacheada 10 min (0 I/O normalmente); el alta se
delega en un enlace, no en un operador copiando ids; y la traza vive en la tabla. **No resuelve
la identidad**: autoriza un `telegram_user_id`, no a una persona.

---

## 5. Verificación (Protocolo 1)

Suite y detalle: **anexo §5**. Lo esencial: 125 tests propios verdes ($0, sin red ni DB) y el
viaje completo del DG —puerta rechaza → canje → aviso → puerta deja pasar → 2ª persona
rebotada → el mismo DG bloqueado en un grupo— ejercido offline sobre los handlers REALES.
