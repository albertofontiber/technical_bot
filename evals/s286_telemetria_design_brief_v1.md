# s286 — Diseño del paquete de TELEMETRÍA (#3 salud + #4 feedback técnico; GO de Alberto 28-jul)

## OBJETIVO + MÉTRICA
Contexto de Alberto (RGPD, 28-jul): herramienta interna solo-empleados del Grupo; finalidad =
mejorar el bot + entender adopción para promoverla; sesión por técnico; uso interno. Sin
técnicos reales aún (meses) → el paquete debe ser BARATO de mantener y estar LISTO el día 1.
MÉTRICA de éxito del diseño: 0 nueva infra externa; salud consultable en 1 comando; feedback
capturable con 1 tap del técnico; todo reversible por flag.

## A — SALUD DEL BOT (sobre `query_logs` existente; sin escrituras nuevas salvo errores)
1. **Vista SQL `bot_health_daily`** (read-only, sin riesgo): agregados diarios desde
   `query_logs` — volumen, usuarios únicos, p50/p95 `response_time_ms`, % respuestas no-info
   (prefijo del fallback), longitud media, por `bot_version`. + vista `bot_health_semanal`.
2. **Captura de errores**: hoy una excepción del handler NO deja fila. Fix mínimo SIN
   migración: fila en `query_logs` con `source='error'` y el resumen de excepción en
   `response` (cap 2000 chars) — flag `BOT_ERROR_LOGGING=on`. (Alternativa tabla aparte:
   descartada — más esquema para el mismo dato; revisitable si el volumen lo pide.)
3. **Digest**: `scripts/bot_health_report.py` imprime el resumen (día/semana/desde-siempre);
   ejecutable por cualquiera de los dos; programable más adelante (scheduled) cuando haya
   técnicos. SIN dashboard web (desproporcionado hoy).

## B — FEEDBACK DEL TÉCNICO (👍/👎 con 1 tap)
1. **Tabla `answer_feedback`** (migración → paste de Alberto): id uuid PK ·
   `query_log_id` uuid FK→query_logs · `telegram_user_id` bigint · `verdict` text
   check in ('up','down') · `comment` text NULL · `created_at` timestamptz default now().
2. **Bot**: inline keyboard (👍/👎) bajo cada respuesta, flag `TELEGRAM_FEEDBACK=on`
   (default off = byte-idéntico). Callback handler escribe la fila. Requisito de plumbing:
   capturar el `id` devuelto por el INSERT a query_logs para enlazar (verificar en build cómo
   loguea `telegram_bot.py`; si hoy no recupera el id, devolverlo con `RETURNING`).
3. **Fase 2 (fuera de este paquete)**: al 👎, pregunta opcional «¿qué faltó?» → `comment`.
   Empezamos con el tap puro (fricción mínima = más señal).
4. **RGPD**: `telegram_user_id` ya se almacena hoy en query_logs (práctica existente);
   feedback no añade categoría nueva de dato personal. Se anota en la matriz RGPD (interés
   legítimo / relación laboral, uso interno, empleados del Grupo — framing de Alberto).

## ALTERNATIVAS DESCARTADAS
- Dashboard (Grafana/Metabase/web): infra nueva sin usuarios aún — cuando haya técnicos y
  volumen, se revisa (la vista SQL ya deja los datos listos para cualquier front).
- Métricas push (Prometheus/logs externos): tercero + coste + RGPD superficie — no.
- Feedback por comando (/feedback texto): más fricción que un tap → menos señal.
- Tabla de errores separada: mismo dato, más esquema.

## GAPS DECLARADOS
1. `source='error'` sobrecarga semántica de query_logs (source hoy = text|voice…) — se
   declara y documenta; el filtro de salud excluye 'error' del volumen de preguntas.
2. El enlace feedback→query_log depende de recuperar el id del INSERT (verificar en build).
3. Sin retención definida aún (RGPD matrix pendiente de Alberto) — las vistas no borran nada;
   la política de retención se aplicará cuando la matriz exista.
4. p95 sobre pocos datos (demo) es ruidoso — el digest lo etiqueta con n.

## PLAN
1. Dúo sobre este brief (toca esquema DB + handler prod).
2. Build: migración `answer_feedback` + vistas (paste de Alberto) · handler flag-gated +
   tests · `bot_health_report.py`.
3. Smoke: feedback e2e en el bot demo (tap propio) + digest sobre datos reales.
4. Entrega en el paquete final del arco (flags en el lote de ONs).
