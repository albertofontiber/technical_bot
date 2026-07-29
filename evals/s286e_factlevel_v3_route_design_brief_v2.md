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
