## Revisión adversarial — s327 (Fable 5, independiente)

**[crítico] [confianza: alto] [ancla: read_file → "path ausente del snapshot congelado"; grep evals/** sin hits para "medicion|censo|16 casos"]** — El cierre S3 («censo COMPLETO de los 16 casos auditables — ver `evals/s327_eje_pregunta_medicion_v1.md`») cita un fichero que NO existe en el snapshot ni en el manifiesto de cambios. La única métrica de calidad del eje `es_pregunta` es hoy una afirmación sin artefacto: patrón exacto del autor (declarar "medido/cerrado" lo no verificable). O el fichero no se versionó (fallo de proceso) o el censo no existe. El hallazgo S3 de Sol NO puede darse por cerrado.

**[medio] [confianza: medio] [ancla: app.py:585-596 vs app.py:534-538]** — El S2 (504 por ≈16 lecturas sin presupuesto) se cerró SOLO en la portada: `pagina_resumen` pasa `presupuesto` a `leer_vista` (l.538), pero `pagina_metricas` (l.588) recorre TODAS las vistas sin presupuesto y además pinta tabla completa de cada una. Salvo que `leer_vista` tenga presupuesto por defecto (no verificado), `/metricas` conserva el mismo modo de fallo que motivó S2. El briefing dice "cerrado" sin acotar el alcance del cierre.

**[medio] [confianza: medio] [ancla: briefing "109/109 con taxonomía v7" vs S7 "taxonomía v8 y histórico re-clasificado"; yaml:94 `version: 8`]** — Inconsistencia interna de framing: si el histórico quedó en v7, por contrato (yaml:35-36) las 109 filas cuentan como PENDIENTES frente a la v8 vigente. Existen `s327_es_pregunta_v7.json` y `v8.json` en el manifiesto, lo que sugiere re-corrida, pero el Estado del briefing afirma lo contrario que su propio S7.

**[menor] [confianza: alto] [ancla: migrations/024:33-36 y 024:61]** — Comentario duplicado (copy-paste sin releer) y postcondición por conteo de substring `es_pregunta` (≥4 ocurrencias): funciona hoy, pero es frágil — cualquier comentario o alias futuro que contenga la palabra la satisface sin filtrar nada.

**[menor] [confianza: medio] [ancla: clasificacion.py:125-127]** — `termina_en_interrogacion` no cubre «¿cuántos lazos» (apertura sin cierre, frecuente en teclado móvil ES); cae al LLM con sesgo True, aceptable, pero la regla "literal" de Alberto deja ese hueco sin declarar.

**Verificado y sólido**: (1) ruta con parámetro — normalización ANTES de la puerta (app.py:1027-1034), sufijo contra lista cerrada o 404 (562-565), nunca viaja a PostgREST; (2) regla dura DESPUÉS del parser (clasificacion.py:334-335) y defecto True (222-223); (3) filtros `es_pregunta`/`COALESCE(...,TRUE)` en las 8 vistas de 023 y en 024; (4) orden CHECK-fuera→mapa→CHECK-v7 y columna-al-final respetados (023:81-96, 190-194).

**Claims 5-6 (móvil/CSP) no verificadas** por presupuesto: "0 px de scroll medido con navegador real" es inauditable desde el repo; tómese como declaración del autor, no como hecho.

**Veredicto**: NO sólido hasta resolver el primero — un cierre de ronda anclado a un fichero inexistente invalida el "7/7 confirmados y cerrados".