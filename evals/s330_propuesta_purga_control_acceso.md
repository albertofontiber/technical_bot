# s330 — Cerrar el PENDIENTE MATERIAL de retención: purga de las tres tablas de control de acceso

## 0. Qué NO es esto (verificado antes de proponer, Protocolo 4)

La premisa con la que llegué —«no hay job de purga»— era **FALSA**. Verificado leyendo el repo:
`public.rgpd_retencion_pasada(TEXT)` existe, está **APLICADA EN PRODUCCIÓN desde el 5-ago-2026**
(s295→s296→s297→s299), corre por **pg_cron el día 1 de cada mes a las 04:30 UTC** como `postgres`
asumiendo el rol `rgpd_retencion`, y deja recibo en `public.rgpd_recibos`. Cubre 4 tablas
(`query_logs`, `feedback`, `answer_feedback`, `answer_messages`) más la destrucción del vínculo
(`persona_seudonimo`). Un job nuevo sería el **drift que s299 eliminó a propósito**.

Lo que de verdad falta es lo que `docs/RGPD_RETENCION.md` marca como **«PENDIENTE MATERIAL — plazo
y purga de las dos tablas (art. 5.1.e) ⚠️»**, más `panel_usuarios` (plazo adjudicado el 20-ago,
DEC-252). El propio doc ya dice el mecanismo correcto: **«una política más en
`rgpd_retencion_pasada`, no un job nuevo»**.

## 1. RECOMENDACIÓN

Extender el mecanismo existente a las tres tablas, en una migración nueva
(`s330_rgpd_control_acceso_v1.sql`) en `supabase/migration_proposals/` — el patrón del repo para
esta cola, que Alberto aplica a mano en el SQL Editor.

**Reglas (las de la matriz ya adjudicada por Alberto, 17-ago + DEC-252):**

| Tabla | Condición | Ancla | Acción |
|---|---|---|---|
| `bot_invitaciones` nunca canjeada | `canjeada_at IS NULL` | `creada_at` + 24m | `nota = NULL` |
| `bot_invitaciones` canjeada | alta ya revocada hace 24m **o alta inexistente** | ver §2 | `nota = NULL`, `canjeada_por = NULL` |
| `bot_allowlist` revocada | `revocado_at IS NOT NULL` | `revocado_at` + 24m | **`DELETE`** (el id es PK: no se puede disociar) |
| `bot_allowlist` activa | — | — | se conserva: es su finalidad |
| `panel_usuarios` revocado | `activo = FALSE` (CHECK garantiza `revocado_en NOT NULL`) | `revocado_en` + 24m | **`DELETE`** (el usuario es PK) |

**Piezas:**
1. **GRANTs de columna mínimos** al rol: `bot_invitaciones` SELECT(id, creada_at, canjeada_at) +
   UPDATE(nota, canjeada_por) · `bot_allowlist` SELECT(telegram_user_id, revocado_at,
   invitacion_id) + DELETE · `panel_usuarios` SELECT(usuario, revocado_en) + DELETE.
2. **Políticas `rgpd_retencion_ventana`** en las tres (RLS ya está ENABLE+FORCE en las tres:
   016 líneas 276-279, 019 líneas 110-111). La ventana sigue siendo invariante del motor.
3. **Función acotada `rgpd_invitacion_vencida(UUID)`** SECURITY DEFINER — ver §2.
4. **`CREATE OR REPLACE` de `rgpd_retencion_pasada`**: el array de la aserción de mecanismo pasa de
   4 a 7 tablas, y tres sentencias nuevas con su entrada de recibo. **Orden: invitaciones ANTES de
   allowlist** (si se borra el alta primero, desaparece el ancla de la invitación en esa misma pasada).
5. **Recibo sin identificadores**: `bot_allowlist` y `panel_usuarios` registran **solo conteo**, como
   `persona_seudonimo` — ahí el id ES la persona. `bot_invitaciones` sí registra uuids de fila.

## 2. LA SUTILEZA QUE DECIDE EL DISEÑO — por qué hace falta una función SECURITY DEFINER

La regla de la invitación canjeada ancla en `bot_allowlist.revocado_at`, **otra tabla**. Un predicado
RLS con subconsulta directa parece bastar, y **no basta**: la subconsulta se evalúa bajo las políticas
del propio rol, que solo le enseñan filas vencidas.

- Alta viva → el rol no la ve → `NOT EXISTS` cierto → **disociaría la nota de un acceso ACTIVO**.
  Es literalmente el fallo #2 de s296 («el borrado del vínculo no veía las filas recientes»).
- Alta ya borrada por una pasada anterior (o por supresión a petición) → nada la referencia → la
  invitación conservaría `nota` y `canjeada_por` **para siempre, en silencio**: el fallo #1 de s296.

Por eso, mismo patrón ya validado aquí (`rgpd_quedan_identificados`): función SECURITY DEFINER con
visibilidad completa que responde SOLO esa pregunta.

```sql
-- vencida = (nunca canjeada y 24m desde creada) O
--           (canjeada, 24m desde el canje, y no queda alta viva ni revocada-hace-poco)
SELECT CASE WHEN i.canjeada_at IS NULL
            THEN i.creada_at  < now() - interval '24 months'
            ELSE i.canjeada_at < now() - interval '24 months'
                 AND NOT EXISTS (SELECT 1 FROM public.bot_allowlist a
                                  WHERE a.invitacion_id = p_id
                                    AND (a.revocado_at IS NULL
                                         OR a.revocado_at >= now() - interval '24 months'))
       END
  FROM public.bot_invitaciones i WHERE i.id = p_id
```

El término `canjeada_at + 24m` del caso B es el **conservador**: no cambia nada en el caso normal
(el canje siempre precede a la revocación), y evita disociar la traza de un canje reciente cuya alta
alguien borró a mano.

**Blindaje obligatorio, y es la lección de s299**: `rgpd_quedan_identificados` nació ejecutable por
`anon`/`authenticated`/`service_role` (los default privileges de Supabase conceden EXECUTE sobre toda
función nueva de `public`; s296 solo revocó PUBLIC) y quedó como oráculo alcanzable por RPC. La
función nueva lleva `REVOKE ALL FROM PUBLIC, anon, authenticated, service_role` + `GRANT EXECUTE` solo
a `rgpd_retencion`, con postcondición que lo asevera.

## 3. ALTERNATIVAS DESCARTADAS

- **(a) Un job/cron nuevo para estas tablas.** Es el drift que s299 eliminó: dos implementaciones de
  una operación irreversible, y la próxima tabla se añade a una y se olvida en la otra. Además
  exigiría sacar credenciales de la base (pg_cron no las saca).
- **(b) Predicado RLS con subconsulta directa, sin función.** Medido contra el diseño en §2: rompe en
  los dos extremos (destruye datos de accesos vivos / no alcanza a los huérfanos).
- **(c) Anclar la invitación canjeada en `creada_at` a secas** (sin mirar el alta). Simple, pero
  borra «para quién era» mientras el acceso sigue VIVO — destruye justo la traza de auditoría que
  la tabla existe para dar, y contradice la regla adjudicada.
- **(d) Estampar en la invitación una copia de `revocado_at` cuando el panel revoca.** Evita la
  función, pero duplica estado y añade una segunda escritura al panel que puede fallar por separado
  — un dato de cumplimiento que depende de que la app se acuerde.
- **(e) No borrar `bot_allowlist`, disociar.** Imposible: `telegram_user_id` es PK. Es la excepción
  ya declarada en la matriz; la traza «hubo un alta y la emitió X» sobrevive en la invitación
  (`creada_por`, `canjeada_at`).

## 4. GAPS Y RIESGOS DECLARADOS

1. **Aplicar es de Alberto y hay validación legal pendiente.** El doc pide (1) escribir la política
   —esto— y (2) la validación del abogado, que va en el mismo paquete que el aviso v8. Este trabajo
   cierra (1). **Nada se aplica a producción en esta sesión.**
2. **Riesgo destructivo inmediato = 0, MEDIDO** contra producción hoy: `bot_invitaciones` 2 filas,
   `bot_allowlist` 2, `panel_usuarios` 1, y **0 vencidas** en las tres; la fila más antigua es del
   17-ago-2026 ⇒ lo primero que podría borrarse sería en **agosto de 2028**. Es un cambio preventivo.
3. **El gate de CI no ejercita la rama de programación** (el contenedor no trae pg_cron) — límite
   heredado de s299, no nuevo. La función sí se ejercita entera.
4. **`panel_intentos` puede quedar con una fila huérfana** (`clave = 'usuario:<x>'`) tras borrar al
   usuario: no hay FK. No es dato personal identificable por sí solo y el reloj de retención de
   intentos ya lo recorta; se declara, no se disimula.
5. **El panel enseñará menos filas revocadas** cuando esto empiece a actuar (2028). No rompe código:
   `resumen_acceso` cuenta lo que lee.
6. **Sujetos distintos en el mismo mecanismo**: `panel_usuarios` son administradores de Fontiber, no
   técnicos. Se acepta porque el rol es «retención», no «técnicos», el recibo distingue por tabla y
   el plazo lo unificó Alberto a propósito; la alternativa era un segundo mecanismo.
7. **Comentario obsoleto que hay que corregir**: `migrations/016` líneas 93-96 afirman que el job
   «NO las toca ni necesita una política nueva». Dejarlo sería la clase de copia-que-miente que
   DEC-252 atacó.
8. **No toca ningún lever medido** (esto no es retrieval ni síntesis): el punto 5 del Protocolo 2 no
   aplica, y se declara en vez de omitirse.

## 5. POR QUÉ ES BP + ESTRUCTURAL + ESCALABLE

- **Estructural**: cierra un incumplimiento del art. 5.1.e declarado por escrito, en la raíz — una
  política más en la única implementación existente, no un aparato paralelo.
- **BP**: la ventana sigue siendo invariante del motor (RLS), el rol sigue sin poder leer contenido,
  los privilegios son de COLUMNA, el recibo no registra identificadores donde el id es la persona, y
  el oráculo nuevo nace blindado por la lección que este mismo repo pagó en s299.
- **Escalable**: la próxima tabla con dato personal se añade por el mismo sitio (GRANT + política +
  sentencia + entrada de recibo), y la aserción de mecanismo crece con ella.

## 6. ALCANCE DE LA SESIÓN

Migración + rollback + tests de integración contra PostgreSQL real (fixture extendido con las tres
tablas) + paths del workflow + docs (RGPD_RETENCION, el comentario de 016, PLAN, DECISIONS,
TECH_DEBT). **Sin aplicar en producción.**
