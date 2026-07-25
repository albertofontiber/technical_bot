# s284 — Manifiesto del pase de higiene de `scripts/` (v1)

**Fecha:** 25 jul 2026 · **Rama:** `claude/s282-h0t2-qa` · **Coste:** $0 (sin llamadas a modelo, sin
DB, sin red) · **Alcance:** pase SCOPED de limpieza, **no exhaustivo**.

**Qué se hizo:** se archivaron (no se borraron) 92 scripts one-shot de `scripts/` a
`scripts/archive/` vía `git mv`, se re-verificó `TECH_DEBT.md` ítem por ítem contra el código y se
reconciliaron las cifras del banner de `docs/ARCHITECTURE.md`. **`src/` no se tocó: cero cambios de
comportamiento.** `evals/*` preexistentes, `supabase/`, `.github/` y los docs canónicos distintos de
ARCHITECTURE tampoco se tocaron.

---

## 1. Método (y por qué el gate no es vacuo)

1. **Índice de referencias, no intuición.** Se escaneó el repo entero (3.208 ficheros de texto:
   `tests/`, `.github/`, `src/`, `docs/`, `scripts/`, `evals/`, `config/`, `supabase/`,
   `migrations/`, `data/`, `spotcheck/`, raíz) con una única regex combinada de los **587** stems de
   `scripts/*.py`, con **límites de token** (`(?<![A-Za-z0-9_])stem(?![A-Za-z0-9_])`) y excluyendo la
   auto-referencia del propio fichero. Resultado: **99 scripts con CERO referencias** en todo el repo.
2. **Segunda pasada independiente con `grep -E`** sobre la lista final, ya con la rama actualizada por
   la lane s284 paralela. **Gate vacuo cazado y corregido:** la primera pasada de cross-check usó
   `paste` sobre un fichero con CRLF, así que el patrón quedó `stem\r|stem\r|…` y **no podía casar
   nada** — devolvía "0 refs" por construcción. Se rehízo con `tr -d '\r'` y con un canario
   (`SANITY: 67 ficheros de scripts/ casan`) que demuestra que el patrón sí muerde.
3. **Distinción artefacto vs. referencia.** Varios tests leen `evals/<stem>_v1.json` (p.ej.
   `tests/test_s168_ledger_failure_attribution.py`). Eso es la **salida** del script, no el script:
   los `evals/` no se movieron, así que esos tests siguen leyendo exactamente el mismo fichero. Se
   verificó abriendo cada uno de esos tests.
4. **Colisiones de prefijo declaradas.** `s101_hyq_negcontrol` es prefijo de `s101_hyq_negcontrol2`
   (que se queda). El escaneo con límites de token las distingue; el `grep` laxo no. Se re-corrió el
   cross-check con límites de palabra explícitos → **0 hits** en `scripts/` fuera de `archive/`.
5. **Suite completa antes y después** (ver §6).

## 2. Movimientos — 92 scripts a `scripts/archive/`

Todos con `git mv` (git conserva el historial y detecta el rename). "Refs" = referencias vivas
verificadas en `tests/`, `.github/`, `src/`, `docs/`, `config/`, `supabase/`, `migrations/`,
`evals/`, `CLAUDE.md`, `TECH_DEBT.md` y el resto de `scripts/`.

| Script | Sesión-origen | Por qué se archiva | Refs |
|---|---|---|---|
| `analyze_language_audit.py` | abr-2026 (pre-numeración) | diagnóstico one-shot de la campaña `category='General'` + auditoría de idiomas; su salida vive en `logs/` y en TECH_DEBT #6/#7 | 0 |
| `analyze_languages.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `audit_product_model_catalog.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `estimate_translation_cost.py` | abr-2026 (pre-numeración) | diagnóstico one-shot de la campaña `category='General'` + auditoría de idiomas; su salida vive en `logs/` y en TECH_DEBT #6/#7 | 0 |
| `external_review_preregistration.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `fix_b5_product_model.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `fix_search_chunks_text_rpc.py` | s17 | migración 003 / RPC de la tabla VIEJA `chunks`; ya no gobierna nada en `chunks_v2` | 0 |
| `fts_repopulate.py` | abr-2026 (Sprints 3+4) | repoblado one-shot del `search_vector` sobre la tabla VIEJA `chunks` (pre-SWAP); producción es `chunks_v2` desde s27 | 0 |
| `inspect_doc_15584.py` | abr-2026 (pre-numeración) | diagnóstico one-shot de la campaña `category='General'` + auditoría de idiomas; su salida vive en `logs/` y en TECH_DEBT #6/#7 | 0 |
| `inspect_doc_generic.py` | abr-2026 (pre-numeración) | diagnóstico one-shot de la campaña `category='General'` + auditoría de idiomas; su salida vive en `logs/` y en TECH_DEBT #6/#7 | 0 |
| `investigate_general_category.py` | abr-2026 (pre-numeración) | diagnóstico one-shot de la campaña `category='General'` + auditoría de idiomas; su salida vive en `logs/` y en TECH_DEBT #6/#7 | 0 |
| `layer_a_remap_no_chunks.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `poc_test_extractors.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `retrieval16_deathpoint.py` | s78 | diagnóstico/smoke one-shot del Backfill A de identidad (DEC-060); el backfill está aplicado en prod | 0 |
| `retrieval16_identity_audit.py` | s78 | diagnóstico/smoke one-shot del Backfill A de identidad (DEC-060); el backfill está aplicado en prod | 0 |
| `run_migration_003.py` | s17 | migración 003 / RPC de la tabla VIEJA `chunks`; ya no gobierna nada en `chunks_v2` | 0 |
| `t1_select_docs.py` | t1 prep | selección determinista de docs para T1 (pre-vuelo de coste); T1 no se ejecutó por esa vía | 0 |
| `verify_cowork_claims.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `verify_cowork_claims2.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `verify_cowork_claims3.py` | s27 (SWAP a chunks_v2) | one-shot del SWAP: fix B5, re-mapeo capa A, PoC de extractores y verificaciones documentales puntuales; el SWAP está cerrado y verificado | 0 |
| `s63_gate.py` | s63 | gate pre-registrado + corrida held-out del ciclo A (DEC-044); ejecutados, veredicto sellado en `evals/s63_*` | 0 |
| `s63_heldout.py` | s63 | gate pre-registrado + corrida held-out del ciclo A (DEC-044); ejecutados, veredicto sellado en `evals/s63_*` | 0 |
| `s78_handler_smoke.py` | s78 | prechecks/smoke one-shot del Backfill A (DEC-060) | 0 |
| `s78_prechecks.py` | s78 | prechecks/smoke one-shot del Backfill A (DEC-060) | 0 |
| `s79_locator_validate.py` | s79 | validación one-shot del localizador grado-audit (DEC-061) | 0 |
| `s83_canon_merge.py` | s83 | extracción dúo + precisión/muestra del activo de identidad (DEC-067); el activo ya está construido y adjudicado | 0 |
| `s83_full_extract_batch.py` | s83 | extracción dúo + precisión/muestra del activo de identidad (DEC-067); el activo ya está construido y adjudicado | 0 |
| `s83_pilot_precision.py` | s83 | extracción dúo + precisión/muestra del activo de identidad (DEC-067); el activo ya está construido y adjudicado | 0 |
| `s83_sample_measure.py` | s83 | extracción dúo + precisión/muestra del activo de identidad (DEC-067); el activo ya está construido y adjudicado | 0 |
| `s86_capa1_measure.py` | s86 | A/B judge-free de levers ya MEDIDOS y settled (identidad / IDENTITY_MAP / neighbor-window) | 0 |
| `s86_map_measure.py` | s86 | A/B judge-free de levers ya MEDIDOS y settled (identidad / IDENTITY_MAP / neighbor-window) | 0 |
| `s86_neighbor_measure.py` | s86 | A/B judge-free de levers ya MEDIDOS y settled (identidad / IDENTITY_MAP / neighbor-window) | 0 |
| `s92_pin_regen.py` | s92 | regeneración one-shot del `pool_pin` del instrumento s85 con `IDENTITY_RESOLVE=on` | 0 |
| `s93_trace_misses.py` | s93 | bake-off fine-grained (DEC-085); trazas y track HyDE NO-GO, veredicto sellado | 0 |
| `s93_trackC_hyde.py` | s93 | bake-off fine-grained (DEC-085); trazas y track HyDE NO-GO, veredicto sellado | 0 |
| `s94_f1_requal.py` | s94 | piloto F1-F3 de enunciados; el sidecar `PILOT_PARENT_SWAP` que usaban fue retirado en T0 (el linkage vive en `chunks_v2.parent_id`) | 0 |
| `s94_f2_probe.py` | s94 | piloto F1-F3 de enunciados; el sidecar `PILOT_PARENT_SWAP` que usaban fue retirado en T0 (el linkage vive en `chunks_v2.parent_id`) | 0 |
| `s94_f3_run.py` | s94 | piloto F1-F3 de enunciados; el sidecar `PILOT_PARENT_SWAP` que usaban fue retirado en T0 (el linkage vive en `chunks_v2.parent_id`) | 0 |
| `s95_d_gate0.py` | s95 | gate-0 del piloto D, cerrado NO-GO (DEC-089) | 0 |
| `s101_hyq_negcontrol.py` | s101 | control negativo one-shot del piloto hyq (gates pre-registrados ya cumplidos) | 0 |
| `s102_hyq_retry_empties.py` | s102 | «pasada única» declarada sobre los registros vacíos del jsonl hyq; ejecutada y cerrada | 0 |
| `s103_gold_arm_probe.py` | s103 | probes one-shot del landing hyq v3.1 (DEC-101); el landing está shippeado | 0 |
| `s103_seam_probe.py` | s103 | probes one-shot del landing hyq v3.1 (DEC-101); el landing está shippeado | 0 |
| `s103_top100_probe.py` | s103 | probes one-shot del landing hyq v3.1 (DEC-101); el landing está shippeado | 0 |
| `s108_cat007_measurement_probe.py` | s108 | probe read-only de los dos falsos-miss de cat007; artefacto `evals/s108_cat007_measurement_probe_v1.json` conservado | 0 |
| `s109_post_rerank_runtime_replay.py` | s109 | replay one-shot del seam post-rerank; el seam ya está cableado y con tests propios | 0 |
| `s110_freeze_combined_contexts.py` | s110 | freeze/replay one-shot del pool de rerank | 0 |
| `s110_rerank_pool_replay.py` | s110 | freeze/replay one-shot del pool de rerank | 0 |
| `s111_upstream_cascade_replay.py` | s111 | replay one-shot de la cascada upstream | 0 |
| `s113_build_fact_ledger.py` | s113 | constructores/freezes/regresión one-shot del ledger S113; los `*_v1.json` que leen los tests siguen en `evals/` | 0 |
| `s113_freeze_full_contexts.py` | s113 | constructores/freezes/regresión one-shot del ledger S113; los `*_v1.json` que leen los tests siguen en `evals/` | 0 |
| `s113_full_answer_regression.py` | s113 | constructores/freezes/regresión one-shot del ledger S113; los `*_v1.json` que leen los tests siguen en `evals/` | 0 |
| `s114_build_fact_ledger.py` | s114 | freezes, held-out y challenges one-shot del bundle de procedimiento; artefactos conservados en `evals/` | 0 |
| `s114_build_partial_evidence_membership.py` | s114 | freezes, held-out y challenges one-shot del bundle de procedimiento; artefactos conservados en `evals/` | 0 |
| `s114_freeze_product_scope.py` | s114 | freezes, held-out y challenges one-shot del bundle de procedimiento; artefactos conservados en `evals/` | 0 |
| `s114_procedure_bundle_heldout.py` | s114 | freezes, held-out y challenges one-shot del bundle de procedimiento; artefactos conservados en `evals/` | 0 |
| `s114_procedure_bundle_section_challenge.py` | s114 | freezes, held-out y challenges one-shot del bundle de procedimiento; artefactos conservados en `evals/` | 0 |
| `s115_freeze_reference_edge_nested_holdout.py` | s115 | freeze del holdout anidado + replay dev de reference-edge (no es evidencia de release) | 0 |
| `s115_reference_edge_dev_replay.py` | s115 | freeze del holdout anidado + replay dev de reference-edge (no es evidencia de release) | 0 |
| `s117_m27_span_binding_diagnostic.py` | s117 | diagnóstico read-only de un gate de binding fallido | 0 |
| `s126_gate_independent_prerequisites.py` | s126 | scan/adjudicación/replay one-shot de prerequisitos independientes | 0 |
| `s126_replay_structural_upstream.py` | s126 | scan/adjudicación/replay one-shot de prerequisitos independientes | 0 |
| `s126_scan_independent_prerequisites.py` | s126 | scan/adjudicación/replay one-shot de prerequisitos independientes | 0 |
| `s128_adjudicate_explicit_relation_census.py` | s128 | censo determinista + sellado de su adjudicación (relaciones técnicas explícitas) | 0 |
| `s128_explicit_relation_census.py` | s128 | censo determinista + sellado de su adjudicación (relaciones técnicas explícitas) | 0 |
| `s147_build_fresh_source_packet.py` | s147 | constructor one-shot del packet source-first | 0 |
| `s162_scan_numeric_superscripts.py` | s162 | scan de descubrimiento read-only de superíndices numéricos | 0 |
| `s168_build_source_unit_gold_packet.py` | s168 | constructor del packet + atribución del NO-GO semántico (score congelado) | 0 |
| `s168_ledger_failure_attribution.py` | s168 | constructor del packet + atribución del NO-GO semántico (score congelado) | 0 |
| `s170_relation_store_transport_attribution.py` | s170 | atribución one-shot de fallos de construcción, sin reintento | 0 |
| `s171_build_s147_source_unit_gold.py` | s171 | mapeo one-shot de gold exacto a IDs de unidad de evidencia | 0 |
| `s173_build_single_source_omission_cohort.py` | s173 | constructor one-shot de la cohorte de omisión | 0 |
| `s174_adjudicate_prerequisite_blind_audit.py` | s174 | selección + adjudicación one-shot del audit ciego de prerequisitos | 0 |
| `s174_select_prerequisite_blind_audit.py` | s174 | selección + adjudicación one-shot del audit ciego de prerequisitos | 0 |
| `s177_governed_derivation_shadow.py` | s177 | replay local one-shot de derivaciones gobernadas | 0 |
| `s188_compatibility_answer_cascade.py` | s188 | cascada de respuesta read-only sobre las tarjetas de compatibilidad | 0 |
| `s209_review_compact_design.py` | s209 | review cards one-shot del frontier para la decisión S209 | 0 |
| `s209_review_decision_card.py` | s209 | review cards one-shot del frontier para la decisión S209 | 0 |
| `s209_review_fresh_planner_design.py` | s209 | review cards one-shot del frontier para la decisión S209 | 0 |
| `s210_close_incomplete_run.py` | s210 | sellado de run incompleto + re-emisión/veredicto puntual del dúo | 0 |
| `s210_fable_final_design_verdict.py` | s210 | sellado de run incompleto + re-emisión/veredicto puntual del dúo | 0 |
| `s210_repair_fable_design_decision_format.py` | s210 | sellado de run incompleto + re-emisión/veredicto puntual del dúo | 0 |
| `s211_close_zero_call_provider_rejection.py` | s211 | sellado del rechazo de esquema pre-modelo que cerró S211 | 0 |
| `s212_analyze_relation_funnel.py` | s212 | adaptadores/análisis one-shot del gate de binding S212 | 0 |
| `s212_review_full_binding_gate_v2.py` | s212 | adaptadores/análisis one-shot del gate de binding S212 | 0 |
| `s212_review_overflow_gate.py` | s212 | adaptadores/análisis one-shot del gate de binding S212 | 0 |
| `s213_close_incomplete_run.py` | s213 | sellado del stop fail-closed por longitud | 0 |
| `s214_close_incomplete_run.py` | s214 | sellado del stop fail-closed por límite de compleción | 0 |
| `s228_run_clause_bound_synthesis_pilot.py` | s228 | piloto clause-bound (run + score) ejecutado y cerrado | 0 |
| `s228_score_clause_bound_synthesis_pilot.py` | s228 | piloto clause-bound (run + score) ejecutado y cerrado | 0 |
| `s260_adjudicate_adversarial_review.py` | s260 | adjudicación one-shot del dúo de diseño S260 | 0 |
| `s271_872c_respec_rescore.py` | s271 | re-score $0 de réplicas ya almacenadas (DEC-128); certificación en `evals/s271_872c_respec_rescore_v1.json` | 0 |

### Caveat declarado sobre los scripts archivados

Casi todos resuelven la raíz del repo con `Path(__file__).resolve().parents[1]`. Al bajar un nivel,
ese `parents[1]` pasa a ser `scripts/` en vez de la raíz. **Si alguna vez hay que resucitar uno, hay
que ajustar el índice del `parents[...]` (o moverlo de vuelta) antes de ejecutarlo.** Se archivan como
artefacto histórico legible, no como herramienta lista para correr. Ninguno era ejecutable desde
ningún camino vivo (0 refs), así que nada en el repo depende de esa resolución de rutas hoy.

Este caveat y el puntero a este manifiesto quedan también en `scripts/archive/README.md`, para que el
directorio no sea opaco para quien lo encuentre sin contexto.

## 3. Candidatos con 0 referencias que SE QUEDAN (7 de 99)

| Script | Por qué se queda |
|---|---|
| `s277_c1_p1_v2_contract.py` (`s277_build_c1_p1_v2_contract.py`) | zona de drift-seals s277 (INTOCABLE por contrato de la lane); la familia `s277_c1_p1*` ancla blobs sellados y 88 guards |
| `s277_adjudicate_document_local_review.py` | misma zona s277: la P1 es baseline inmutable con audit de hashes reproducible; en duda = se queda |
| `s281_h0t3_selftest.py` | su propio docstring lo declara territorio de la lane `s281_h0t3_*`, y el packet H0-T3 está **pendiente de adjudicación de Alberto** (trabajo vivo, no histórico) |
| `parity_probe_orchestrator.py` | probe de paridad byte-a-byte DIRECT↔ORCH del orquestador multi-turn, que está **vivo en producción** (`ORCHESTRATOR_PATH=on`): es diagnóstico de un seam activo, no un one-shot |
| `s101_hp011_fix.py` | hp011 sigue en el lote de decisiones de Alberto (P2: chunk corrupto `2113ac69`, patch vs re-render); este script es el precedente/plantilla exacto de ese patch de corpus |
| `synthesis_trampa.py` | certificación NEGATIVA (guardarraíl anti-sobre-acreditación) del juez `synthesis_miss_judge.py`, que **sí se queda** en `scripts/` |
| `synthesis_calib_sample.py` | par del anterior: muestra estratificada para la certificación hand-labeled del mismo juez vivo |

## 4. Intocables: verificados presentes en `scripts/` tras el pase

`s277_c1_p1*.py` (10 ficheros) · `adversarial_review.py` · `adversarial_review_fable.py` ·
`adversarial_briefing.md` · `test_bot_vs_gold.py` · `test_multiturn_vs_gold.py` ·
`factlevel_assessment.py` · `enunciados_pass.py` · `update_inventario.py` · `check_deps.py` y
`catalog_store.py` (los dos pasos que CI ejecuta además de pytest) · `s133_true_pgvector_runtime_gate.py`
y `s131_m0b_*` (workflow `s133-true-pgvector.yml`) · `gold_store.py` · `atomic_scorer.py` ·
`s277_c1_release_gate.py` y `s277_c1_live_reachability_probe.py` (sellados en
`tests/test_c1_release_gate.py`). Ninguno estaba en la lista de 0-refs; todos siguen en su sitio.

**Recuento de `scripts/*.py`: 587 → 495** (92 movidos, 0 borrados).

## 5. Estado de `TECH_DEBT.md` (re-verificado, nada borrado)

Se añadió el bloque **«Re-verificación s284»** con una fila por ítem (**64 filas** = los 55 números
más los sub-ítems 5b/11b/11c/11d/11f/11g/11h/11i y el segundo «#18») y su **ancla de verificación**;
el índice S277 se conserva íntegro como histórico. Ninguna fila de deuda se editó ni se borró —
**no se resolvió deuda, solo se re-etiquetó estado**.

Reparto: **41 [VIGENTE]** (7 de ellas matizadas: parcial / residual / degradado / raíz / activo) ·
**17 [CERRADO]** (2 nuevos respecto al índice S277: #29 y #19) · **6 [CADUCO]**.

**Cambios de estado respecto al índice S277 (lo que este pase realmente descubre):**

- **#29 RLS → CERRADO.** DEC-150 (s278): Alberto aplicó el hardening; 13/13 tablas `public` con RLS,
  grants `anon`/`authenticated` sobre `chunks_v2_enunciados` revocados, `EXECUTE` de
  `create_hnsw_index()` revocado, clase crítica del Advisor desaparecida. El índice S277 aún lo
  listaba como abierto. Residual declarado: `p1_readonly` sin policies → 0 filas.
- **#19 eval multi-turn → CERRADO.** Existe y está medida: `scripts/test_multiturn_vs_gold.py` +
  `tests/test_multiturn_golds_contract.py`; Fase 1 e2e K=3 = 18 PASS / 2 PARCIAL / 1 residual, y viva
  en producción (DEC-153/155/156).
- **#1 y #2 → CADUCO.** Describen dicts hardcoded en `src/ingestion/chunker.py`, fichero que **ya no
  existe** (retirado por #38/s43). El pipeline vivo `src/reingest/metadata.py` no los tiene: la
  identidad sale del sidecar del portal + `config/manufacturers/*.yaml` + `data/catalog/*.jsonl`. La
  deuda se evaporó por sustitución, no se pagó.
- **#5b y #10 → CADUCO.** `category` salió del path de retrieval (DEC-073) y el canal
  `has_diagram`/`diagram_url` fue sustituido por `document_visual_assets` (DEC-123/133): los dos
  ítems describen contratos que ya no gobiernan el serving.
- **#12 → CADUCO.** `scripts/run_eval.py` ya no es la vara (lo son `test_bot_vs_gold.py` +
  `atomic_scorer.py`); el substring-match que describe no gobierna ninguna medida vigente.
- **#11b → CADUCO** (absorbido por el frente de síntesis + Evidence Contract vivo).
- **#6 → CERRADO-instrumento** (filtro de idioma vivo en runtime + test de determinismo); el residual
  es decisión de política por documento, no falta de herramienta.
- **#45 → CERRADO por sustitución** (registro `document_visual_assets`, `VISUAL_ASSETS_REGISTRY=on`).

**Confirmados VIGENTES con ancla fresca de código** (no son "probablemente siguen abiertos"):
#3 (`ingestion_run_id` = 0 hits) · #5 (`manufacturer_group` = 0 hits) · #8 (`query_gaps` = 0 hits) ·
#21 (`product_family` = 0 hits) · #47 (`_get_all_known_manufacturers`, `retriever.py:2805`, sigue con
`limit=200` sin `ORDER BY`) · #50 (`LEVER2_IDENTITY` sigue conviviendo con el resolver data-driven) ·
#54 (`sentence_spans`, `mp_lexicon.py:33`, sigue partiendo por puntuación+espacio).

**Hallazgo suelto:** `src/config.py:292` cita «TECH_DEBT #74», número inexistente (el máximo es #55).
No se tocó `src/`; queda anotado.

## 6. `docs/ARCHITECTURE.md` — diff resumido (solo cifras y banner de estado)

Dos ediciones, ambas dentro del bloque «⚡ Estado del sistema». Ninguna sección explicativa se tocó.

1. **Banner de estado `s281` → `s283`:**
   - «la release C1 está a un click / PR #184» → **release EN PRODUCCIÓN** (merge `f65ec66` + flip
     Railway verificado vivo).
   - **Baseline oficial 12 PASS / 25 PARCIAL / 2 FALLO → 16 / 20 / 3** (baseline v2 con paridad
     completa de flags, DEC-157), declarando que el `cat016`-FALLO de v1 era **artefacto de paridad**
     (harness sin `HYQ_TABLE`), y nombrando los 3 FALLO restantes (cat007 K-inestable, cat024
     conflicto, hp011).
   - «Multi-turn: Fase 0 CONSTRUIDA … Fase 1 gateada al GO» → **Fase 0 + Fase 1 VIVAS en producción**
     (PRs #185/#186, `bot_version f1bee30` verificado en `query_logs`, `ORCHESTRATOR_PATH=on` +
     `CONVERSATION_POLICY=impl`), manteniendo explícito que el DDL `convo` y la campaña H0 siguen **NO
     aplicados** (gateados por Alberto).
   - **Suite 3158/0 → 3228/0.**
   - Párrafo nuevo (4 líneas) con el cierre de la cola de calidad s283: DEC-157/158/159 (cat016
     resuelto por paridad · cat022 + hp012-retrieval techo-declarados · hp011 + hp012-framing
     aparcados-en-datos · mt11b espera dogfooding).
2. **Encabezado del párrafo de cobertura document-local:** «candidata, post-rerank y **default-off**»
   → «candidata y post-rerank — **VIVA en producción bajo `coverage_c1_v4`**» (era default-off hasta
   el flip de s281). Se verificó que `coverage_c1_v4` existe como perfil en
   `src/release_profiles.py:22`.

Cifras del "resumen estable s71" (25.090 chunks · 1.170 docs · 31 marcas · 587 modelos · 146/154
fact-level) **no se tocaron**: no ha habido escritura de corpus desde entonces (el expediente H0-T2
está firmado pero su SQL sigue **sin aplicar**, pendiente de Alberto).

## 7. Verificación final — suite completa

```
ANTES  (HEAD a1aff79, antes de los movimientos):
  python -m pytest -q -p no:randomly
  3228 passed, 5 skipped in 667.90s (0:11:07)

DESPUÉS (tras los 92 git mv + ediciones de TECH_DEBT/ARCHITECTURE):
  python -m pytest -q -p no:randomly
  3228 passed, 5 skipped in 576.41s (0:09:36)
```

**0 movimientos revertidos**: ningún `git mv` rompió ningún test.

## 8. Incidencia de concurrencia — declarada, no silenciada

Mientras esta lane trabajaba, **otra lane paralela (s284 goldreview r2) commiteó en la misma rama**
(`734e6dc`, `308bf83`). Su `git commit` recogió el índice de git tal como estaba, y por tanto
**absorbió los 92 renames que esta lane había dejado stageados con `git mv`** — se ven como
`scripts/{ => archive}/…` dentro de `734e6dc`.

- Esta lane **no ejecutó ningún `git commit`** (mandato "NO commits" respetado).
- **Nada se perdió ni se corrompió**: los renames son exactamente los de este manifiesto (92, mode
  100644, 0 bytes de cambio de contenido), y el árbol de trabajo es el estado deseado.
- Efecto colateral a saber: los movimientos ya **no** son revertibles con un simple `git restore`; hay
  que revertirlos por `git mv` inverso si se quisiera deshacer.
- Las ediciones de `TECH_DEBT.md`, `docs/ARCHITECTURE.md` y este manifiesto se dejan **sin stagear**,
  para que un `git commit` ajeno no las barra sin querer.
- La misma lane modificó `scripts/test_bot_vs_gold.py` y `scripts/test_multiturn_vs_gold.py` (fix del
  truncado `[:3000]` del juez). **Esta lane no tocó ninguno de los dos** — son intocables por su
  contrato.
