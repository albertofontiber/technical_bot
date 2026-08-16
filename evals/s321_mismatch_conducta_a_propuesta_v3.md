# s321 — Conducta (a) ante marca↔producto errónea · **v3 = DISEÑO CONSOLIDADO, PENDIENTE DE DECISIÓN DE PRODUCTO — NO se cablea en sesión autónoma**

**Historial**: v1 (flag en el handler) → Sol 6 medios: viola DEC-200 (punto de decisión único), la ruta
nueva viola el CHECK de `query_logs.route`, voz no pasa por el plan. v2 (`fallback_ruta` + `rag_trace` +
`target_models_override`) → Sol **1 crítico + 4 medios**, todos verificados: `rag_trace` NO es libre
(`runtime_trace.build_rag_serving_trace` es «*the only runtime trace shape allowed*» con enums cerrados —
una clave libre descarta la traza entera); F1 (`resolve_conversational_turn`) re-resuelve `target_models`
DESPUÉS del override ⇒ inerte en producción; `fallback_ruta` significa degradación, no continuación;
el multi-modelo no está resuelto; el preámbulo no entra en `query_logs.response` ni en `last_response`.
**0 falsos positivos en las dos rondas.**

## Por qué NO se cablea hoy (decisión de alcance, declarada)

El diseño correcto toca **cuatro subsistemas** del serving: `TurnPlan` (campo tipado nuevo),
`runtime_trace` (builder + validador + tests), `conversation_policy_impl` (F1 con entrada explícita de
modelo resuelto), y `_process_query`/`log_query` (respuesta compuesta). Dos de ellos se graduaron hace
una semana (DEC-209/211). Y hay una **decisión de producto** abierta que no es mía: qué hacer con **dos
marcas y/o dos modelos** en la misma pregunta («el ASD535 de Detnov y el ADW535 de Securiton…»). Cablear
esto sin Alberto sería exactamente lo que el Protocolo 2 prohíbe: construir sobre un contrato no decidido.

## Diseño v3 (para la sesión dedicada)

1. **`TurnPlan.preambulo: Mapping | None`** — campo NUEVO tipado (no `fallback_ruta`): «antes de ejecutar
   `ruta`, envía este preámbulo». Para mismatch-answer: `ruta="conversacional"`, `preambulo={"tipo":
   "mismatch_corrected", "modelo", "marca_real", "marca_mencionada"}`. `plan_turn` sigue pura: el flag
   entra por `Meta.mismatch_answer` (leído por el shell de `MISMATCH_ANSWER`). Byte-equivalencia con
   `False`.
2. **`runtime_trace`**: nueva sección acotada `mismatch_corrected: {modelo, marca_real, marca_mencionada}
   | None` en `build_rag_serving_trace` con su validador (strings acotados por longitud, no libres) y
   test; el sink la acepta. Sin ruta nueva ⇒ sin migración del CHECK (queda `route="rag"`; filtrar por
   `rag_trace->'mismatch_corrected'`). Si Alberto prefiere ruta de primera clase, migración versionada.
3. **F1**: `resolve_conversational_turn(..., resolved_model: str | None)` — cuando viene del plan, F1 lo
   usa como `turn_models=[resolved_model]` en vez de re-detectar; test con `CONVERSATION_POLICY=impl`.
4. **Respuesta compuesta**: `_process_query(..., preambulo: str | None)` antepone el preámbulo al texto
   que guarda en `last_response` y en `query_logs.response` (una fila, respuesta completa que vio el
   usuario; el feedback posterior la conserva).
5. **Multi-modelo — DECISIÓN DE ALBERTO**: (a) fuera de alcance: si `len(modelos)>1` NO se aplica
   mismatch-answer (se responde como hoy = (b)); (b) emparejar marca↔modelo por proximidad textual y
   corregir solo el par erróneo; (c) otra. Recomiendo **(a)** para v1 del cableado — la clase
   multi-producto es rara y el emparejamiento es un contrato nuevo.
6. **Voz**: fuera (no pasa por `plan_turn`); se declara.
7. **Tests de integración** con adapters congelados y `CONVERSATION_POLICY=impl`: dos mensajes, una fila
   con `response` = preámbulo+RAG y `rag_trace.mismatch_corrected`, modelo servido = resuelto; OFF
   byte-idéntico; marca correcta sin preámbulo; voz sin cambio.

## Coste estimado de la sesión dedicada
Medio día con dúo (dos rondas mínimo: diseño v3 → build). No es un parche.

## Recibos
Sol v1 ts=2026-08-16T13:08:52 · Sol v2 ts=2026-08-16T14:12:49 (tally completado, 0 FP). Fable no se
lanzó sobre v1/v2 a propósito: el diseño ya sabía que cambiaba; se emparejará sobre la v3 en la sesión
dedicada.
