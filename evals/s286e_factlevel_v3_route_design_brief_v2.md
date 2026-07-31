# s286e — Instrumento factlevel v3 (v2 post-dúo; v1 = histórico). Dúo r1: sub-agente
# SÓLIDO-CON-CAMBIOS (2 BLOCKER + 3 MAYOR + 5 menores) + Sol 8 hallazgos (3 críticos) — CONVERGEN.

## SIN CAMBIO (validado por ambos lados, regla-C)
Motivación entera (ruta bypasea el seam; bvg válido; doble ceguera :280/:517/:610; lane
predicate :1998-1999; hipótesis obligations-only refutada) + orden instrumento-antes-de-lever
(mecánicamente necesario: bajo la ruta v2.2 CUALQUIER lever de lane es invisible) + semántica
synthesis-miss-con-sub-tag (no clase terminal nueva) + fuera-de-scope declarados.

## CAMBIOS v1→v2 (unión de los dos lados)
1. **[B1/Sol-c1] Soporte sobre pool ∪ appends**: `judge_fact` corre también sobre las filas
   apendizadas; `_pm_map` se extiende a los ids apendizados. `in_pool` INTACTO (señal upstream
   pura, solo pool-50).
2. **[B2/Sol-c2] `served` = VISTA DEL GENERADOR, no `pipeline["chunks"]`**: espejo del filtro
   de admisión (generator.py:590-604: threshold 0.4 ∨ `is_validated_coverage_chunk` ∨ rama
   bundle) → la subclase `threshold-drop` VIVE. Para filas de coverage validadas, el soporte se
   juzga sobre `coverage_context_content(chunk)` (los excerpts que el generador VE, no el
   content completo). **Clase nueva de trazabilidad `append_view_truncated`**: el valor está en
   el chunk pero fuera de las cards servidas = gap de EXCERPT de lane (ni retrieval ni
   síntesis) — sin ella, la campaña apuntaría al lever equivocado.
3. **[Sol-c3/№8] Captura single-run con adapters MODULE-LEVEL**: `execute_rag_turn` devuelve
   solo conteos — el pool-50 ordenado y el topk se capturan con wrappers de retrieve/rerank
   (deepcopy en captura; module-level como `_eval_strict_rerank` de bvg — el seam-guard AST
   camina el cuerpo de `run_pipeline` y un closure anidado lo rompería). NO re-recuperar fuera
   del run (rompe identidad). Llamada keyword-only (el sketch v1 fallaba).
4. **[M3] Política de fail-open**: `coverage_trace.status=="error"` (o lane con error) → retry
   1×; si persiste → gold marcado `coverage_degraded` y EXCLUIDO de cualquier inferencia
   seeds/radio (consistente con los fail-fast de juez muerto :522-524). Nada se promedia en
   silencio; conecta con la contradicción config-v1-shadow-only: si la lane erroreara por eso,
   el full lo DISTINGUE de «anchors no entran».
5. **[M4/Sol] `pipe_sha` extendido** al closure del seam: serving_pipeline.py,
   coverage_runtime.py, post_rerank_coverage.py, release_profiles.py, structural_neighbor_*.py
   + configs del perfil activo (config/*.yaml consumidos) — un dirty-tree en coverage ya no
   reutiliza partials incompatibles (clase s101b).
6. **[M5/Sol] Estabilidad sobre la composición SERVIDA**: las reps regeneran desde
   `pipeline["chunks"]` (prefijo+appends del turno primario), no desde `topk`.
7. **[m6] `STRUCTURAL_NEIGHBOR_SHADOW: "off"` pineado en DEMO_FLAGS** (el patrón bvg llama al
   observer; un .env sucio no puede activarlo en medición).
8. **[m9 — ORDEN BARATO-PRIMERO] Smoke v3 dirigido**: `--qids hp011,hp013,hp014,hp017` (~$3)
   responde «¿entran los anchors con la ruta real?» ANTES del full (~$23). El smoke estándar
   valida plomería; este valida la pregunta de la etapa 1. Ambos antes del full.
9. **[m10] Tag de output**: default `v3_<fecha>` (INSTRUMENT_VERSION en el tag — sin colisión
   mismo-día con los fulls v2.2).
10. **[m7/#57] El assert-ruta redundante se ELIMINA del plan** (el seam-guard AST es la
    autoridad); #57 queda como estaba (eje flags) + la adición del assessment al tuple `cases`.
11. **[Sol-m6] Etiquetado honesto del delta**: v2.2→v3 mismo-día = FOTO NUEVA de serie nueva
    (rerank no determinista documentado :714-716) — NO «la medición causal del seam». La
    reconciliación de etapas usa el campo nuevo n(via_coverage_append) publicado en la fila.
12. **[Sol-m7] El espejo bvg incluye su paso de validación del contrato de release**
    (test_bot_vs_gold.py:230-237) — no solo la llamada al seam. El término «byte-a-byte» se
    retira (over-claim): es ESPEJO FUNCIONAL con deltas declarados (captura + juez).

## RIESGOS (v1 §riesgos sigue + añadidos)
- Los conveyed-checks sobre excerpts pueden clasificar `append_view_truncated` donde v2.2 decía
  retrieval-miss — es la VERDAD del pipeline (el lever sería de excerpt de lane, y se vería).
- Coste revisado: smoke plomería $3 + smoke anchors $3 + full ~$23.

## PLAN
1. ~~Dúo r1~~ HECHO (este v2 = respuesta; convergencia bilateral). 2. Ronda de confirmación
FRESCA focused sobre v2. 3. Build (Opus ejecuta bajo spec cerrado; los wrappers module-level y
la vista-del-generador son los puntos delicados). 4. Smoke plomería → smoke anchors → full v3
= fila canónica + mapa real etapa 1. 5. Tally + scoreboard + DEC.

## ADENDA r2 (confirmación fresca: CAMBIOS-ANTES-DE-BUILD → incorporados; ESTE es el spec sellado)
13. **[r2-1 crítico] DEMO_FLAGS pinea el flag-set COMPLETO del seam**: los 7 flags-hoja
    env-resueltos que post_rerank consulta y NO son profile-owned — `TABLE_PREAMBLE_CLOSURE`,
    `CANONICAL_HYQ_COVERAGE`, `COMPATIBILITY_BUNDLE_COVERAGE`, `RERANK_POOL_COVERAGE`,
    `STRUCTURAL_CASCADE_COVERAGE`, `LOGICAL_RECORD_COVERAGE`, `EVIDENCE_DERIVATION_OVERLAY` —
    todos `"off"` (= Railway ship: son TARGET_OFF/ausentes). Un .env sucio ya no mide otra stack.
14. **[r2-2] `pipe_sha` = closure por IMPORTS, no lista a mano**: hashear `src/rag/*.py` que el
    seam importa (walk de imports desde serving_pipeline + post_rerank_coverage; incluye
    compatibility_bundle_coverage, doc_scoped_hyq_coverage, table_preamble_closure,
    rerank_pool_coverage, mp_lexicon, document_local_coverage, structural_neighbor_*) +
    release_profiles.py + los config yaml consumidos.
15. **[r2-3] `append_view_truncated` = SUB-MOTIVO de synthesis-miss** (5 clases terminales
    INTACTAS; precedente exacto: `threshold-drop` ya vive ahí aunque el generador no viera el
    valor). Cascada: se evalúa en el conveyed-check del soporte servido; NO prevalece sobre
    rerank-miss (si el valor está en pool-no-topk, la señal upstream manda). La fila del
    scoreboard publica n(via_coverage_append) y n(append_view_truncated).
16. **[r2-4] El filtro de admisión se EXPORTA de generator.py** como función única e importada
    (fuente única, cero duplicación — la clase de deriva que v3 corrige).
17. **[r2-5 premisa corregida] El seam SÍ devuelve `chunks`/`coverage_trace`/`generation`;
    topk = `chunks[:reranked_rows]`** (garantía de prefijo protegido) → solo hace falta el
    wrapper de CAPTURA de retrieve (module-level); el de rerank estricto ya existe como patrón
    bvg y se pasa como adapter.
18. **[r2-6] El retry del fail-open = loop sobre UN único call-site** de `execute_rag_turn`
    (el guard asserta count==1 en el cuerpo).
19. **[r2-7] SPLIT de sets de soporte**: `sup_pool` (alimenta in_pool/in_topk/pool_rank/clases
    upstream) vs `sup_served` (alimenta reaches_gen/conveyed) — hoy un solo `sup` alimenta todo.
