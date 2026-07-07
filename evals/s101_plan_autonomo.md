# s101 — Plan autónomo nocturno (7-8 jul 2026) · REANUDABLE

**Mandato (Alberto):** subir OK hacia >95% bajando los buckets de miss, upstream-first
(retrieval-miss → synthesis-miss), objetivo 1-2 por bucket. GO de un mecanismo de retrieval =
REDUCCIÓN DEL BUCKET (pool-50 same-family), no OK ni PASS. BP+estructural+escalable-30+; flag
de OVERFITTING si se llega a fine-tuning de golds. Decisiones inequívocas = las tomo y las
comunico; las ambiguas → `evals/s101_decisiones_alberto.md` (con recomendación).

**Restricción de la noche: OpenAI SIN CUOTA** (429 desde ~23:00). Implicaciones:
- NO full v2 (scoreboard) · NO jueces GPT (retrieval_miss_judge/conveyed/semantic-corpus) ·
  NO cross-model (`adversarial_review.py`).
- SÍ: harnesses léxicos (fact_match), Voyage (embed), Claude (generación hyq, rerank, sub-agente).
- → los misses ANCLABLES se pueden medir judge-free; los no-anclables (hp020-'4y8') esperan cuota.
- Tiering: revisiones de esta noche = sub-agente only, **cross-model PENDIENTE de cuota** →
  NADA se shipea ni se mergea esta noche (todo flag-gated OFF / branch-local).

## Estado al escribir esto (commits en rama eval/s100-factlevel-assessment)
| Pieza | Estado |
|---|---|
| Instrumento (dual-judge conveyed + dual-soporte + fail-fast primario) | ✅ committeado |
| Demotes scope (5 facts) + hp011 gold r.1→r.I (corrección Alberto) | ✅ committeados |
| Corpus: r.S aplicado, r.i restaurado (3 chunks HLSI) | ✅ verificado en DB |
| Piloto hyq | ✅ **GO del mecanismo** (cat016+hp018-6K8 flip; control negativo null-corrected OK) |
| Tiebreak s97 portado (flag off) + medición con ancho-10 | ⏳ midiendo (bbvhrkpzy) |
| Full v2 (scoreboard juez-v2) | ❌ BLOQUEADO por cuota (run inválido en cuarentena: `s100_factlevel_full_v2_INVALIDO_quota.yaml`) |

## Mapa upstream vivo (post-todo, 18→~10)
| Fact | Bucket real | Lever |
|---|---|---|
| ~~6 support-FN~~ | — | ✅ dual-soporte (instrumento) |
| ~~cat016·autobúsqueda, hp018·6K8~~ | — | ✅ hyq (piloto GO) |
| hp011·'05a295', hp013·PWR-R, hp017·instrucción | RECALL | **hyq residual** → diagnóstico cos + ampliar variedad de preguntas POR DOC (gold-blind) → re-embed → re-medir (judge-free, anclables) |
| hp014·'35' (≤35Ω lazo) | RECALL-efectivo (val doc MIDT180) | generar hyq para MIDT180 + medir |
| hp012·'4 lazos/792' | DIVERSIFY | **tiebreak** (midiendo) |
| cat013·CLIP + bucle-cerrado | identidad (val_chunks=0 por family-filter) | diagnóstico judge-free del filtro vs doc_map MIDT190→sdx-751 (ya en main s97) |
| hp020·'4 y 8' | no-anclable | espera cuota (juez semántico) |

## Cola de ejecución de esta noche (en orden)
1. ✅→ veredicto tiebreak (hp012 flip + centinela hp001 + negcontrol) → si GO-mecanismo: documentar; ship-gate (bvg) espera cuota.
2. Diagnóstico hyq-residual (judge-free): ¿las preguntas de los val-chunks de hp011/hp013/hp017 existen y a qué cos quedan de la barra 0.45? → si es cobertura/registro: **regenerar variedad por DOC entero** (HLSI-MN-103, ADW535_TD_T140358, 997-671) con prompt de más registros (gold-blind, estructural) → re-embed → re-medir los 3 (lexical).
3. hp014: generar hyq para MIDT180 (doc entero) → re-embed → medir.
4. cat013: probe judge-free del family-filter (¿por qué gold_family excluye los chunks MIDT190 con el doc_map ya adjudicado?) → si el fix es de datos (pm/doc_map), proponerlo en decisiones-Alberto; si es del harness (gold_family), arreglar el harness.
5. Cierre de docs de sesión: DECISIONS (DEC-095 borrador), FACTLEVEL doc (scoreboard nota v2-inválido + judge-v2), PLAN/HISTORY, memoria. Commit.
6. (Si cuota vuelve antes de que despierte Alberto — NO contar con ello) full v2 serializado.

## Cómo retomar mañana (si esto se para)
- Leer este fichero + `evals/s101_decisiones_alberto.md` + `git log --oneline -15`.
- Tareas del tracker: #4 (full v2, espera cuota), #5 (Fase 1, en curso), #6 (Fase 2, espera full v2).
- Artefactos de medición: `evals/s101_hyq_measure.yaml`, `evals/s101_tiebreak_measure.yaml`,
  `evals/s101_hyq_negcontrol2.yaml`, `evals/s101_deathpoint.yaml`, `evals/s101_inpool_adjudication.json`.
- Al recargar OpenAI: `python scripts/factlevel_assessment.py full` (SOLO, sin otros runs en paralelo)
  → scoreboard v2 (fila con juez-v2, no comparable directo a v1 — sumar judge_disagreements).
- Pendiente dúo: cross-model sobre (a) dual-soporte final, (b) tiebreak port, (c) cualquier cambio de
  esta noche — ANTES de considerar ship de nada.
