# s286e — Instrumento factlevel v3: cruzar el seam de serving (diseño pre-dúo)

## HALLAZGO QUE LO MOTIVA (traza Opus, verificada regla-C en código)
`factlevel_assessment.py::run_pipeline` (:277-284) hace `retrieve_chunks → rerank →
generate_answer` DIRECTO — **nunca cruza `execute_rag_turn`**, donde viven TODAS las lanes de
coverage C1 (post_rerank_coverage). Consecuencias:
1. **El full s286b "corregido" TAMPOCO midió la ship-config**: los DEMO_FLAGS s286b activaron el
   perfil, pero la RUTA lo bypasea (2º eje de staleness del día: #57 vigilaba flags, no ruta).
2. El bvg SÍ cruza el seam (`test_bot_vs_gold.py:170`) → el baseline 11/16/12 es VÁLIDO.
3. Doble ceguera semántica del instrumento aunque el seam corriera: `served_ids` se deriva del
   topk PRE-append (:280) y `in_pool` se juzga solo contra el pool de retrieval (:517/:610) —
   una fila apendizada por coverage es IRREPRESENTABLE (reaches_gen jamás True para appends).
4. El guardarraíl existe y no cubre al assessment: `tests/test_serving_pipeline.py:219-247`
   fija bvg+smoke al seam; factlevel hace 3 de los 4 bypasses prohibidos y no está en `cases`.
5. Hipótesis «lane obligations-only» REFUTADA: el predicado real es solo
   `structural and not compatibility_applicable` (post_rerank_coverage.py:1998-1999); la lane
   S109 se construyó PARA estos hechos (su doc registra hp011/hp012/hp013/hp014/hp017
   retrieval→generator). El trigger NO se amplía — lo roto es la MEDICIÓN.

## OBJETIVO + MÉTRICA
Que el mapa de la campaña (retrieval→rerank→synth, objetivo <2/etapa) mida el MISMO pipeline
que sirve el bot y que mide bvg. MÉTRICA de éxito: (a) el assessment cruza `execute_rag_turn`
con el patrón bvg exacto; (b) el seam-guard de CI lo cubre; (c) las filas apendizadas son
representables en la taxonomía; (d) full v3 re-medido = fila canónica del scoreboard.

## CAMBIOS (instrumento v2.2 → v3.0; freeze-hash roto DECLARADO)
1. **Ruta**: `run_pipeline` → `execute_rag_turn(query, query_for_retrieval=query,
   target_models=None, available_models=None, retrieval_top_k, rerank_top_k,
   adapters=RagServingAdapters(retrieve_chunks, _strict_rerank, observe_structural_shadow,
   generate_answer))` — espejo byte-a-byte del patrón bvg (`test_bot_vs_gold.py:163-185`,
   reranker estricto incluido). Exponer por gold: `coverage_status`, `appended_ids` + lane.
2. **Semántica de etapas (el compás de la campaña, sin romperlo)**:
   - `in_pool` NO cambia de significado (señal upstream de retrieval puro).
   - `served_ids` = `pipeline["chunks"]` (incluye appends) → `reaches_gen` vuelve a ser verdad.
   - Clasificación: un hecho ausente del pool-50 pero SERVIDO vía append ya no es
     retrieval-miss — fluye a conveyed-check (OK o synthesis-miss) con sub-tag
     `via_coverage_append=<lane>` para trazabilidad del mecanismo. Un hecho ausente de pool Y
     de servido sigue = retrieval-miss. rerank-miss idéntico (pool sí, topk no, append no).
3. **Guardarraíl**: añadir `("scripts/factlevel_assessment.py", "run_pipeline")` al tuple
   `cases` de `tests/test_serving_pipeline.py:221` — CI caza la próxima deriva de ruta.
4. **TECH_DEBT #57 → eje ruta**: el assert de arranque del assessment compara flags Y ruta
   (presencia de `execute_rag_turn` en `run_pipeline`) — barato, textual, suficiente.
5. `INSTRUMENT_VERSION = "v3.0"` + nota de no-comparabilidad (v2.2 media pipeline pre-C1 de
   facto; las filas s286/s286b del scoreboard reciben la anotación).

## FUERA DE SCOPE (declarado, no colado)
- La contradicción config (`structural_neighbor_coverage_v1.yaml:26-29 serving.enabled:false`
  + hard-fail «must remain shadow-only») vs lane sirviendo bajo c1_v4 — ítem de LANE, no de
  instrumento; se registra y se resuelve aparte (candidato: config v2 con serving explícito).
- Cualquier cambio del selector/trigger/caps de la lane (los riesgos declarados del código:
  presupuesto compartido, hp002:r1, atomicidad de perfil, sellos DEC-147, byte-inertness).
- El gate R2 de producción (población ~sept; paquete de Alberto).

## RIESGOS / GAPS DECLARADOS
1. Ruptura de comparabilidad total con v2.2 (todas las clases pueden moverse): se declara y la
   fila v3 arranca serie nueva. El delta v2.2→v3 mismo-día ES la medición del seam (valioso).
2. Los appends cambian el INPUT del generador → los conveyed-checks se mueven también
   (esperado: es el pipeline real).
3. **La entrada de los 4 anchors NO está garantizada**: los seeds vivos (prefijo rerank
   ship-config) ≠ served_ids congelados del replay (hp011#2 marca best_pool_rank:15). El full
   v3 lo MIDE — sin asumir. Si no entran, el siguiente lever es seeds/radio (diseño aparte).
4. Coste: smoke $3 + full ~$23 (3º del día; los dos previos quedan como contrafactuales
   pre-C1-flags y pre-C1-ruta — la escalera de correcciones queda trazada en el scoreboard).
5. `strict=True` del reranker de bvg vs `strict=True` actual del assessment: idéntico ya.

## ALTERNATIVAS DESCARTADAS
- Acreditar appends post-hoc sin cambiar la ruta: sigue sin correr las lanes (mide nada nuevo).
- Cambiar solo semántica sin ruta: ídem.
- Reusar outputs de bvg para el funnel: bvg no clasifica por-hecho ni por-etapa (otro rol).
- Ampliar el trigger de la lane «para que entren»: refutado por la traza — el trigger ya cubre;
  y tocarlo exige perfil nuevo + re-sellado (riesgos DEC-147), sin evidencia aún de necesidad.

## PLAN
1. Dúo (este brief): sub-agente Fable fresco + Sol 5.6 xhigh (MEDIO-alto en zona de dolor:
   instrumento de retrieval). 2. Build (Opus ejecuta, yo superviso): ruta+semántica+tests.
3. Smoke v3 ($3) → full v3 (~$23) = fila canónica → mapa real de la etapa 1. 4. Con el mapa:
   diseño del lever que quede (si los anchors entran solos, la etapa 1 puede cerrar sin lever).
