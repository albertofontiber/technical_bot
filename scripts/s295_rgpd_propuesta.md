# Propuesta s295 (RONDA 3 — diseño NUEVO) — Retención RGPD con rol dedicado

> **Aviso al revisor**: tercera ronda. Las dos anteriores tumbaron el diseño y el mecanismo
> ha cambiado por completo (de PostgREST + `service_role` a rol dedicado + conexión directa
> + políticas RLS). **No des nada por bueno porque ya pasara una revisión: lo que revisas es
> otro artefacto.** El árbol está congelado mientras revisas.

## OBJETIVO + MÉTRICA de HOY

**Objetivo**: que la retención de 24 meses sea ejecutable, sin ampliar la superficie de
privilegios del bot.

**Métrica**: NINGUNA de calidad de respuesta. No toca retrieval ni generación; no hay delta
de eval y no se reclama ninguno. El criterio es de cumplimiento y de corrección factual de
lo que se le declara al usuario. Si algo aquí parece reclamar mejora de calidad, es error mío.

## El giro respecto a la ronda 2

Alberto preguntó qué implicaciones tenía la propuesta anterior. Al desglosarlas apareció la
que decide: **`service_role` es la identidad del bot** — la misma clave que usa el worker de
Railway encendido 24/7. La v1 le concedía UPDATE de columna y DELETE, es decir, pagaba con
superficie permanente de un proceso expuesto a internet un privilegio que se ejerce una vez
cada varios años. Alberto aprobó moverlo a un **rol dedicado**.

## El diseño v2

`supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql` (SIN aplicar):

1. Rol `rgpd_retencion`: `NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
   NOBYPASSRLS`, `statement_timeout = 120s`. Concedido **solo a `postgres`** con
   `INHERIT FALSE` + `SET TRUE`. **NO a `authenticator`**: no se ejerce por HTTP.
2. Privilegios de **columna**: `SELECT (id, created_at, <columna id>)` + `UPDATE (<columna
   id>)` en `query_logs`, `feedback`, `answer_feedback`; `SELECT (...)` + `DELETE` de tabla en
   `answer_messages`. El rol **no puede leer** pregunta, transcripción, respuesta ni comentario.
3. **Políticas RLS** `rgpd_retencion_ventana` en las 4 tablas, acotadas a
   `created_at < now() - interval '24 months'`. Como el rol es NOBYPASSRLS y las tablas tienen
   FORCE RLS con 0 políticas, sin política no vería nada; con ella, **la ventana de retención
   es un invariante del motor**, no un filtro del script.
4. `ALTER TABLE answer_feedback ALTER COLUMN telegram_user_id DROP NOT NULL`.
5. Postcondiciones: el rol tiene lo que necesita **y nada más** (no INSERT, no UPDATE de tabla,
   no DELETE donde no toca, no lectura de contenido), las 4 políticas existen, la columna es
   nullable, y **`service_role` no ha ganado ni un privilegio**.
6. Rollback declarado, incluido que el `SET NOT NULL` deja de ser posible tras la primera
   ejecución real.

## El job — `scripts/rgpd_retencion.py`

Conexión directa (`DATABASE_URL`) + `SET LOCAL ROLE rgpd_retencion` como primera sentencia.
Las 4 tablas en **una transacción**. Dry-run = ejecutar de verdad y `ROLLBACK`. `--aplicar`
= `COMMIT`. `--recibo` escribe los ids en JSON. `--meses >= 1` validado en el parser (defensa
en profundidad; la ventana real la impone la política). Meses de CALENDARIO. Diagnóstico que
traduce el fallo al hueco real (rol ausente → apunta a la migración; permiso; NOT NULL).

**Tres parches de la ronda 2 desaparecen** en vez de mantenerse: la sonda de conjunto vacío y
su falso OK (ahora se verifica el efecto real), la barrera anti-ejecución-parcial (ahora lo da
la transacción), y la lectura del OpenAPI para adivinar el `NOT NULL`.

## Verificado

- El job corre contra la base real: conecta, intenta `SET LOCAL ROLE` y sale con **exit 2**
  diciendo que el rol no existe y qué migración lo crea.
- 26 tests en `tests/test_s295_rgpd_retencion.py`, verdes.
- Suite completa: **en ejecución** al escribir esto (la anterior, con el diseño previo, dio
  3513 passed / 5 skipped / 0 failed).
- Privilegios y nullability leídos del catálogo real; `service_role` tiene `rolbypassrls`;
  las 4 tablas tienen RLS + FORCE RLS con 0 políticas.

## Fuera de alcance, declarado en la matriz

`user_consent` (decisión pendiente), los exports a disco de `scripts/review_logs.py`, el
extracto de recibos versionado en git, y la retención de Telegram/Railway/Anthropic/OpenAI.
Y el resultado es **seudonimización**, no anonimización: el texto libre puede identificar.

## Gaps y riesgos declarados

1. DPAs = asunción, no hecho. 2. Transferencia internacional sin documentar. 3. `feedback` no
cascadea. 4. El job no está programado. 5. Acceso y portabilidad no implementados. 6. No soy
asesor legal. 7. Un bootstrap limpio (`supabase_schema.sql`) no crearía el rol: hay que
replicar el bloque al aplicar — pero, a diferencia de la v1, **no hay que tocar sus
postcondiciones**, porque solo miran `anon`/`authenticated`/`service_role` y ninguno cambia.

## Lo que te pido que ataques

¿Las políticas RLS hacen lo que digo, para las cuatro operaciones (SELECT/UPDATE/DELETE) y con
`USING` vs `WITH CHECK` correctos? ¿Se puede tocar una fila reciente por algún camino?
¿`SET LOCAL ROLE` acota de verdad, o `postgres` conserva algo por herencia? ¿La transacción
única tiene alguna pega (bloqueos, `statement_timeout`, tamaño)? ¿Queda alguna afirmación que
declare de más o de menos en la matriz, los términos, el docstring, DEC-177 o HISTORY? ¿Los 26
tests prueban lo que dicen probar?
