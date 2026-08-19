# s326 — Cableado de las métricas de USO/CALIDAD del panel: revisión del dúo

**Contexto**: la propuesta `evals/s326_panel_metricas_uso_propuesta_v1.md` (mergeada, PR #305)
quedó ADJUDICADA ENTERA por Alberto el 19-ago en el hilo: **(1) drill-down con prosa = OPCIÓN
(a)** — pregunta y comentario del técnico, completos, en el panel autenticado (reabre a
conciencia el «fuera de v1» de DEC-231; gate nuevo: addendum al paquete del abogado);
**(2) taxonomía v1 OK; (3) por-usuario con ALIAS de allowlist OK; (4) coste OK**. Este
briefing cubre el CABLEADO (sin commitear aún — el diff contra HEAD es exactamente esta
sesión). Impacto: MEDIO-ALTO (esquema nuevo + superficie del panel expuesto) → dúo
innegociable ANTES de commitear.

## Alcance (lee con tools; ancla fichero:línea; el manifiesto de cambios es el diff vivo)

- `migrations/021_query_clasificacion.sql` — tabla derivada + 8 vistas + ACL + postcondiciones.
- `src/clasificacion.py` — núcleo del clasificador batch (NUEVO, módulo RAÍZ).
- `scripts/clasificar_preguntas.py` — CLI de backfill/re-taxonomización con recibo.
- `config/taxonomia_preguntas_v1.yaml` — taxonomía cerrada versionada (9 ids).
- `src/bot/telegram_bot.py` — SOLO `schedule_clasificacion` (seam JobQueue, flag off) +
  import; `src/config.py` + `src/flags.py` — el flag `CLASIFICADOR_PREGUNTAS`.
- `dashboard/explorador.py` (NUEVO) + `dashboard/app.py` (`pagina_explorador`, ruta, nota
  de honestidad en métricas) + `dashboard/datos.py` (7 vistas declaradas) +
  `dashboard/render.py` (_NAV).
- Tests: `tests/test_s326_*.py` (3 ficheros) + censo import contract 128→129.

## Qué afirmamos (verifícalo o refútalo, con ancla)

1. **El bot no cambia**: con `CLASIFICADOR_PREGUNTAS=off` (default) el worker es
   byte-equivalente (el seam devuelve `[]`); NADA del clasificador corre en la ruta de
   respuesta; encendido, el job es fail-open total (021 sin aplicar / Supabase caído /
   LLM caído → warning y reintento, jamás toca un turno).
2. **Frontera de imports**: `src/clasificacion.py` es raíz e importa SOLO raíz; el
   catálogo entra INYECTADO (`Catalogo`) desde el seam del bot y el script. La matriz
   `raiz→rag` de `test_import_contract` no se toca; censo 128→129 explicado.
3. **ACL (clase 9-bis)**: cada columna que el job escribe tiene su GRANT en la 021
   (cruzado en test contra el payload real); RLS ENABLE+FORCE; anon/authenticated
   revocados de tabla y de las 8 vistas; vistas con `security_invoker`.
4. **Parser estricto**: categoría fuera de la lista = respuesta DESCARTADA (fila
   pendiente), jamás degradada a `otros`; el CHECK SQL == ids del YAML (test cruzado);
   taxonomía v2 exige migración hermana (contrato escrito en el YAML).
5. **Explorador**: filtros de LISTAS CERRADAS (periodo/feedback fijos; categoría =
   taxonomía; marca = whitelist derivada de los datos) — nada de la URL se parsea ni
   llega crudo a PostgREST; prosa pintada ESCAPADA; `response` NO se expone (solo
   longitud); GET sin CSRF a propósito (lectura pura); la puerta de sesión cubre
   `/explorador` vía la parametrización existente de `test_s324f_dashboard_rutas`.
6. **Vistas sin fan-out**: los joins a `answer_feedback` van por el PAR
   (query_log_id, telegram_user_id=autor) que es UNIQUE → máx. 1 fila; los unnest de
   marcas/modelos multiplican A PROPÓSITO (conteo de menciones).
7. **RGPD**: `query_clasificacion` no lleva id de persona y muere en CASCADE; el alias
   del por-usuario es `bot_allowlist.nota` (mismo dato que la pestaña Acceso); las
   filas `source='error'` quedan fuera del Explorador y del por-usuario.

## Gaps YA declarados (no los re-descubras: atácalos si crees que son MÁS graves)

- Sin gate pg propio para la 021 (postcondiciones dentro de la migración + gate ACL de
  texto; el patrón s324j-panel-pg no la cubre).
- Marcas por voz infracontadas (DEC-233, workstream ASR aparte).
- `bot_marcas_semanal` como fuente de la whitelist del filtro: si la 021 no está
  aplicada, el filtro de marca queda vacío (degradación declarada).
- El gate de CALIDAD del clasificador (≥85 % acuerdo, ~30 etiquetas a mano) queda para
  el backfill — la 021 puede aplicarse antes.

**Pregunta al revisor**: ¿hay algún camino por el que (a) el panel exponga algo sin
sesión o a `anon`, (b) el job escriba una columna sin GRANT o rompa la supresión RGPD,
(c) un parámetro de URL llegue crudo a PostgREST, o (d) el flag off NO sea byte-inerte?
