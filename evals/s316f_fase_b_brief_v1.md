# s316f — Fase B del rediseño (DEC-200 v3): brief para el dúo

**Qué es.** El build de la fase B, SIN commitear (ver `git diff HEAD`). La fase A
(mergeada, PR #235) dejó el plan como decisor con la guardia −1 aún viva y enmascarando;
la fase B completa la unificación:

1. **Guardia −1 RETIRADA** (TypeHandler + `brand_switch_guard` + núcleo): la invalidación
   es `plan.transicion`, aplicada por `_aplicar_estado` — el ESCRITOR ÚNICO — en
   `handle_message`, ANTES de ejecutar la ruta (contrato C3: la política resuelve DESDE
   el estado post-plan).
2. **Claves legacy RETIRADAS** (`last_detected_models`, `last_query_time`). El régimen
   stub (rollback de `CONVERSATION_POLICY`) lee/escribe el estado ÚNICO:
   `turn_plan.transicion_basica` con el QUIRK legacy reproducido a conciencia (la
   ventana se refresca en TODO turno RAG — un contexto expirado puede resucitar).
3. **Telemetría de feedback DECLARADA fuera del invariante**
   (`last_query`/`last_response`/`last_query_log_id`; dueño: `_process_query`). El v3
   decía «migrar a WorkingState»; migrar cambiaría el anclaje del feedback tras un
   CLARIFY (hoy conserva el turno RAG anterior) — se decidió declarar-alcance. JÚZGALO.
4. **Voz**: `_decidir_transicion` + `_aplicar_estado` + `_lexico_marcas_cacheado()` —
   disciplina de caché UNIFICADA (coste declarado: marca ingestada mid-proceso no
   dispara switches hasta restart, norma operativa del resto de consumidores).
5. **Los 2 writes F1** (CLARIFY/DECLINE + backfill) pasan por el escritor único.
6. **Tests pineados actualizados**: censo AST de un-solo-escritor sustituye al de
   grupo −1; batería precisión/recall contra el core puro; 2 contratos de
   `f1_activation` al internal nuevo; NUEVOS: rollback stub e2e (señal del paso 1c:
   vaga clarifica sin contexto, va a RAG con él) + quirk unit.

**Estado**: suites afectadas 109 passed + 1 xfailed; suite completa corriendo.

**Preguntas para el revisor**: ¿la semántica stub reproduce TODO el legacy (modelos
preservados si no truthy; ventana desde cualquier turno RAG; paso 1c y rewriter)?
¿alguna ruta llega a `_process_query` sin pasar por el plan? ¿el AST del escritor único
caza todas las formas de escritura? ¿quedó algún consumidor con fetch fresco de la
lista? ¿la señal del paso 1c puede dar verde sin carry?
