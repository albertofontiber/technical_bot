# s301 — Propuesta a atacar: «dashboard» sin app (frente 6) + S-wins de ops (frente 7)

## OBJETIVO + MÉTRICA (declarados)

**Objetivo**: responder «quién usa el bot, cuánto, qué feedback da y POR QUÉ es negativo»
abriendo los grifos de la telemetría YA construida — sin app nueva (DEC-162f sigue
vigente y NO se reabre: su métrica es proporcionalidad, «infra nueva sin usuarios aún»).
**Métrica**: no toca ningún lever de eval (ni retrieval ni síntesis). Listón: suite
completa verde; el camino RAG queda BYTE-IDÉNTICO salvo un campo nuevo en el log
(fire-and-forget); las vistas nuevas son agregados sin ids ni prosa; la carrera de deploy
(código antes que migración) NO puede perder ni el log ni el teclado de feedback.

## Qué se construyó (commit 3efadf3, rama claude/s301-swins)

1. `scripts/review_logs.py` — `_attach_tap_verdicts` lleva ahora `tap_reason` y
   `tap_comment` junto a `tap_verdict` (agregación por query con dropna); `route` y las
   2 columnas nuevas en `front`.
2. `src/logging_db.py` — `log_query(route="rag")` + fila con `route` + **fallback de
   compatibilidad**: 400 con 'route' en el texto ⇒ reintenta sin la columna + warning
   una sola vez (misma clase que el fallback de `rag_trace`; `getattr(resp,"text","")`
   defensivo — un fake sin `.text` mataba el log entero, lo cazó la suite).
3. `src/bot/telegram_bot.py` — las 6 ramas de shortcut loggean su ruta
   (greeting/thanks/bye/catalog_shortcut/manufacturer_mismatch/manufacturer_no_model×2)
   con la respuesta literal capturada en variable; catalog loggea sin texto (vive en el
   handler; declarado).
4. `supabase/migration_proposals/20260806150000_s301_observabilidad_v1.sql` (PENDIENTE
   de aplicar) — `route` + CHECK; las 2 vistas de salud versionadas (idénticas al
   bootstrap); 3 vistas nuevas agregadas con `security_invoker` + REVOKE a
   anon/authenticated; postcondiciones (vistas con security_invoker, API a cero).
   Bootstrap espejado (DEC-180: estado FINAL).
5. `.github/workflows/ci.yml` — Gold gate (`gold_store.py validate`).
6. Guardas de ingesta (inventory/extract/pipeline): `SystemExit` ante vacío.
7. `scripts/marcar_utilidad.py` — camino de escritura del operador para `utilidad`
   (DATABASE_URL; marca+fecha juntas; solo `utilidad IS NULL`; taxonomía de la base).
8. `tests/test_s301_observabilidad.py` (13) + TECH_DEBT #31 → HECHO.

## Claims fuertes del autor (atácalas)

- C1: el camino RAG no cambia de conducta — `route` solo añade un campo al POST del log
  y el default cubre todos los call-sites existentes (error incluido).
- C2: la carrera de deploy es inofensiva en AMBOS órdenes (código-primero: fallback;
  migración-primero: columna nullable con CHECK que admite el default 'rag').
- C3: las vistas nuevas no exponen dato personal: agregados puros (COUNT/percentile);
  el único uso de `telegram_user_id` es COUNT(DISTINCT); la prosa se cuenta, no se
  muestra. `security_invoker` en las 5 (sin él, la vista perfora la RLS leyendo como
  owner).
- C4: los shortcuts loggean con el MISMO fire-and-forget que RAG: un fallo de log jamás
  toca la respuesta (log_query traga excepciones); y `user_id` está en scope en las 6
  ramas.
- C5: `marcar_utilidad` no puede violar el CHECK de coherencia (marca+fecha juntas
  siempre) ni re-marcar sin decisión explícita (`AND utilidad IS NULL`).
- C6: el Gold gate no puede poner el CI rojo HOY: `gold_store.py validate` = exit 0
  (0 errores / 10 warnings / 51 golds, verificado en s300).

## Riesgos YA declarados (atácalos si la mitigación es débil)

- El texto del 400 de PostgREST es el detector del fallback (`'route' in resp.text`) —
  heurística sobre mensaje de error, como la de `rag_trace`. Un 400 ajeno que contenga
  la palabra 'route' dispararía un reintento inofensivo (sin la columna) — benigno.
- `_handle_catalog` loggea sin response text (el texto vive en el handler) — métrica de
  canal completa, contenido no duplicado.
- ~~«los shortcuts pueden recibir voz transcrita»~~ — RETIRADO (H5 del dúo): `handle_voice`
  llama a `_process_query` directo y NUNCA pasa por los shortcuts; la declaración
  describía un camino inexistente.
- «Fire-and-forget» ACOTADO (Y4/H6 del dúo): `log_query` es HTTP síncrono (hasta 2 POSTs
  × 10 s) dentro del handler async — no toca la respuesta (ya enviada) pero bloquea el
  event loop. Es la clase PRE-existente del camino RAG (+call-sites, no regresión);
  deuda anotada en TECH_DEBT con trigger = primer técnico real (mover a
  `asyncio.to_thread` todos los call-sites juntos).
- Filas históricas con `route` NULL: las vistas hacen COALESCE(route,'rag') — correcto
  porque los shortcuts NUNCA loggearon antes (todas las filas históricas son RAG/error).
