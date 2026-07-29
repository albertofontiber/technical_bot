# s286 — Diseño TELEMETRÍA v2 (post-dúo: sub-agente SÓLIDO-CON-CAMBIOS + Sol 8 hallazgos; v1 = histórico)

Cambios v1→v2 = unión de los dos lados del dúo (todos los anclajes verificados regla-C).

## OBJETIVO + MÉTRICA (sin cambio)
Interno solo-empleados; finalidad mejorar bot + adopción; barato de mantener, listo día 1.
MÉTRICA: 0 infra externa; salud en 1 comando; feedback en 1 tap; comportamiento reversible
por flag + DDL con rollback SQL en el mismo paste (v2: «todo reversible por flag» de v1
sobre-afirmaba — los flags no revierten esquema).

## A — SALUD DEL BOT
1. **Vistas `bot_health_daily` / `bot_health_semanal`** sobre `query_logs`, con:
   - **«consultas RAG respondidas»** (NO «volumen/adopción»: saludos, catálogo,
     fabricante-ausente, clarify vago y F1 CLARIFY/DECLINE retornan HOY sin `log_query` —
     telegram_bot.py:360-368/385-388/429-449/607-615/668-685 — y son invisibles).
   - **% no-info = HEURÍSTICA declarada** (familia de patrones `ILIKE 'No tengo información%'
     / 'No dispongo%'` — el admit-no-info es prosa libre del LLM, generator.py:125 es ejemplo
     de conducta, no constante). `_EMPTY_ANSWER_FALLBACK` (telegram_bot.py:62) se cuenta
     APARTE como «error de transporte». El digest etiqueta ambas como heurística.
   - p50/p95 `response_time_ms` etiquetado **«latencia de pipeline»** (se mide antes del envío
     Telegram, telegram_bot.py:829-849 — no incluye transporte/entrega).
   - Segmentación **dogfooding vs técnicos**: `INTERNAL_TELEGRAM_IDS` (env csv, hoy = Alberto)
     excluidos vía WHERE en vistas + digest. Se define AHORA que es gratis.
   - Filas `source='error'` EXCLUIDAS del volumen (verificado: `source` es TEXT sin CHECK y
     los consumidores actuales lo toleran — review_logs.py:123, enunciados_panel.py:47).
2. **Captura de errores** (flag `BOT_ERROR_LOGGING`, default off): fila con `source='error'`
   y `response` = **allowlist `error_type` + `stage`** (p.ej. `TimeoutError@retrieval`) —
   NUNCA `str(exc)` (puede contener URLs con el token del bot; el proyecto ya silencia httpx
   por esto, telegram_bot.py:106-113). El except exterior extrae su PROPIO user_id (el actual
   queda sin ligar si falla antes de :831). Error tardío post-log ⇒ puede haber fila normal +
   fila error del mismo turno (las vistas lo toleran). Alcance enumerado en build:
   `_process_query` except exterior sí; `handle_voice`/`_handle_catalog` tragan las suyas —
   se instrumentan también o se declaran fuera.
3. **Digest** `scripts/bot_health_report.py` (día/semana/histórico, n visible, sin dashboard).

## B — FEEDBACK DEL TÉCNICO (👍/👎)
1. **Tabla nueva `answer_feedback`** — CONVIVE con la tabla `feedback` existente (v1 la
   ignoraba; hoy captura free-text vía `_FEEDBACK_PATTERNS`/`log_feedback`,
   telegram_bot.py:453-454/491-510, logging_db.py:137-160). **Roles disjuntos declarados:**
   `answer_feedback` = veredicto estructurado 1-tap ligado por FK; `feedback` = prosa
   espontánea (sigue viva, sin sunset). La Fase 2 «¿qué faltó?» escribirá
   `answer_feedback.comment`, NO `feedback`. **`scripts/review_logs.py` se extiende EN ESTE
   paquete** para adjuntar también los veredictos (join exacto por FK; el match difuso
   `startswith` de :87 queda solo para la tabla vieja) — sin esto el feedback nuevo nace
   invisible al flujo de revisión.
2. **DDL (paste de Alberto, con rollback SQL en el mismo fichero):**
   - Columnas: id uuid PK · `query_log_id` uuid NOT NULL **REFERENCES query_logs(id) ON
     DELETE CASCADE** (sin esto, el borrado RGPD documentado `DELETE FROM query_logs WHERE
     telegram_user_id=X` — DG_DEPLOYMENT.md:128 — fallaría) · `telegram_user_id` bigint
     NOT NULL · `verdict` text CHECK in ('up','down') · `comment` text NULL · `created_at`
     timestamptz DEFAULT now().
   - **`UNIQUE(query_log_id, telegram_user_id)`** + upsert last-wins (toggle 👍→👎 = cambia
     de opinión; taps duplicados = idempotentes).
   - **Hardening OBLIGATORIO patrón s278** (BLOCKER del dúo): ENABLE+FORCE RLS · REVOKE ALL
     FROM PUBLIC/anon/authenticated · GRANT SELECT, INSERT, **UPDATE** (upsert) TO
     service_role · postcondiciones que abortan (espejo supabase_schema.sql:175-286 /
     migración 20260713164800; precedente UPDATE: user_consent por set_consent).
   - DG_DEPLOYMENT: añadir `answer_feedback` a la nota de borrado RGPD (CASCADE lo hace solo;
     se documenta igualmente).
3. **Plumbing del id — UUID cliente-side** (no RETURNING): `log_query` postea con `Prefer:
   return=minimal` (logging_db.py:28) y tiene un 2º insert de compatibilidad (:117-123);
   generar el uuid en el bot y pasarlo como `id` funciona con ambos y sin esperar
   representación. Si `log_query` falla (es fail-open) ⇒ **ese turno NO muestra keyboard**
   (política documentada; sin FK colgante).
4. **Callback handler** (`CallbackQueryHandler`, hoy no existe — telegram_bot.py:969-973):
   - `callback_data` autocontenido `fb:u:<uuid>` / `fb:d:<uuid>` (41 bytes < 64 de Telegram)
     ⇒ taps tras días/restart funcionan sin estado en memoria.
   - SIEMPRE `callback_query.answer()` (evita spinner infinito en taps stale).
   - **Handler registrado INCONDICIONALMENTE; el flag `TELEGRAM_FEEDBACK` gatea solo el
     ATTACH del keyboard** (si gateara el handler, apagar el flag dejaría botones muertos).
   - `has_consent` en el callback (un usuario revocado puede tapear un keyboard viejo).
   - Autoría del voto: el fila lleva el `telegram_user_id` del TAPEADOR (chat 1:1 → dueño).
5. **Posición del keyboard**: en el ÚLTIMO fragmento de texto; los diagramas van después vía
   `reply_media_group` (que no acepta reply_markup) ⇒ el keyboard queda por encima de las
   fotos — ACEPTADO (simple) y documentado.
6. **Consentimiento**: añadir línea «tu valoración 👍/👎 de las respuestas» a `_CONSENT_TERMS`
   (telegram_bot.py:186-190) + bump `TERMS_VERSION` v1→v2 (logging_db.py:22). Gratis hoy
   (solo usuarios demo), caro después. + anotación en la matriz RGPD.

## C — OPCIONAL EMPAQUETADO PARA ALBERTO (decisión diferida, NO se construye por defecto)
Logging ligero de las rutas pre-pipeline (saludo/catálogo/clarify/F1-directo) con
`category='direct'`, `chunks_used=0`, flag `BOT_DIRECT_LOGGING` default off — es lo que haría
que «adopción» midiera adopción de verdad (hoy esos turnos de onboarding son invisibles).
Coste: +1 llamada log en 5 rutas. Se decide en el paquete final del arco.

## ALTERNATIVAS DESCARTADAS (v2)
- Extender la tabla `feedback` con verdict+FK: exigiría DROP NOT NULL de `feedback_text` +
  mezcla de semánticas upsert/append en una tabla; roles disjuntos en dos tablas es más
  limpio y el flujo de revisión une ambas por FK/match.
- Marcador estructurado de answer-kind en `rag_trace` (opción b del dúo para no-info):
  contradice «sin escrituras nuevas» y toca un esquema cerrado — la heurística declarada
  basta para un digest interno; revisitable si la métrica se vuelve contractual.
- Dashboard / push metrics / feedback-por-comando / tabla de errores separada (v1, siguen).

## GAPS DECLARADOS (v2)
1. % no-info y «consultas RAG» son heurísticas/proxies etiquetadas (no ground truth).
2. Latencia = pipeline, no end-to-end (sin receipt de entrega — desproporcionado hoy).
3. Retención: pendiente de la matriz RGPD de Alberto; las vistas no borran nada.
4. p95 con n bajo es ruido (etiquetado con n).
5. El opcional C queda OFF: hasta que se decida, la métrica de adopción subcuenta onboarding.

## PLAN
1. ~~Dúo r1~~ HECHO (este v2 = respuesta). 2. Ronda de confirmación FRESCA sobre v2 (focused).
3. Build: DDL+rollback (paste Alberto) · handler+keyboard flag-gated + tests · digest ·
   review_logs extendido · consent bump. 4. Smoke e2e demo (tap propio). 5. Paquete final.
