# s319 PR-C — Retirada del camino LEGACY de serving (propuesta ejecutada, v1)

**Qué era**: `handle_message` mantenía DOS rutas de servicio — la del orquestador
(`run_turn`, ON en producción desde su ship) y el `else` histórico
(`execute_rag_turn` inline). Dos rutas que deben evolucionar juntas = la clase
que produjo #70. Diseño pre-aprobado en la propuesta v2 (dúo r17, hallazgos
CONVO_SHADOW + ancla-attestation aplicados aquí).

## La cirugía

- `run_turn` es la ruta ÚNICA; el `else` inline murió (~26 líneas).
- `CONVO_SHADOW` resuelto a la pierna viva (`shadow_result = turn`;
  `turn_result_from_pipeline` ya no se importa). El flag CONVO_SHADOW sigue
  vivo (Phase 0, default off — su graduación no es de esta PR).
- `ORCHESTRATOR_PATH` RETIRADO del código (config, registro, imports). El
  testigo de la retirada: `not hasattr(config, "ORCHESTRATOR_PATH")` en el
  test de flags Phase-0.
- `CONVERSATION_POLICY` graduado `stub`→`impl` (= producción verificada). El
  régimen stub queda por env EXPLÍCITO — **el rollback documentado cambia**:
  ya no es «quitar la var» sino `CONVERSATION_POLICY=stub`.
- `f1_active` ya no está encadenado al flag muerto: depende SOLO de su flag.
- El SEAM `execute_rag_turn`/`RagServingAdapters` queda INTACTO en
  serving_pipeline.py — el release gate P1 lo conduce directamente y lo
  atestigua POR STRING (`s277_c1_p1.py:5891`; ancla corregida en r17/Fable).

## Onda expansiva medida (68 tests: 34 errors + 34 failed → 0)

Clases, todas previstas por la propuesta:
- **A (34 errors)**: fixtures con `setattr(bot, "ORCHESTRATOR_PATH", True)` —
  forzaban lo que ahora es incondicional; retirados.
- **B (~25)**: tests de handler que parcheaban el pipeline inline
  (`bot.retrieve_chunks/rerank/generate_answer/observe_…`) → parchean los
  módulos FUENTE (from_production importa PEREZOSO — mismo efecto, ruta
  única). Los fake-updates ganan `update_id`/`effective_chat` (el request del
  orquestador los lee; el pipeline inline no).
- **C (6)**: contratos del default viejo («stub por defecto») → re-contratados
  con el default impl Y el mundo stub por env explícito, ambos assertados.
- **D**: los tests de PARIDAD legacy↔orquestador pierden su objeto con la ruta
  única — re-anclados a «el handler conduce run_turn» (la paridad byte-a-byte
  fue el guardia DURANTE la coexistencia; su trabajo terminó).

## Gates

- Suite completa (incluye batería P1 — la attestation por string del seam).
- MT 52/52 + instrumento de transporte (los 186 de los 10 ficheros migrados).
- Pre-condición de asentamiento: ORCHESTRATOR_PATH=on + CONVERSATION_POLICY=impl
  VERIFICADOS en Railway (API, s317b) y en producción desde su ship con e2e
  propio (DEC-205b); sin incidentes en query_logs desde entonces.

## Gaps declarados

- La paridad orquestador↔legacy ya no es medible EN CI (el legacy no existe);
  el replay congelado del instrumento de transporte es la guarda de conducta.
- Las vars ORCHESTRATOR_PATH/CONVERSATION_POLICY de Railway quedan redundantes
  (nadie lee la primera; la segunda coincide con el default) — retirarlas es
  de Alberto (lista DEC-210/211).
