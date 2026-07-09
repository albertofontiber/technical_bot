# s101 — Plan autónomo nocturno (7-8 jul 2026) · REANUDABLE

**Mandato (Alberto):** subir OK hacia >95% bajando los buckets de miss, upstream-first
(retrieval-miss → synthesis-miss), objetivo 1-2 por bucket. GO de un mecanismo de retrieval =
REDUCCIÓN DEL BUCKET (pool-50 same-family), no OK ni PASS. BP+estructural+escalable-30+; flag
de OVERFITTING si se llega a fine-tuning de golds. Decisiones inequívocas = las tomo y las
comunico; las ambiguas → `evals/s101_decisiones_alberto.md` (con recomendación).

**UPDATE ~00:30: Alberto RECARGÓ OpenAI antes de dormir** → cola re-secuenciada:
1. Full v2 relanzado LIMPIO y SERIALIZADO (bjukzd5d6) — nada más pesado de GPT en paralelo.
2. Al cerrar el full: cross-models pendientes (dual-soporte final · tiebreak port · hyq seam
   post-iteraciones) + jueces semánticos (hp020-'4y8' · cat013 probe · hp018-'1A').
3. Lo Anthropic/Voyage sigue en paralelo sin conflicto (hyq gen MIDT180/MIDT190, tiebreak measure).
Guardarraíl intacto: NADA se shipea esta noche (los cross-models corren, pero el ship-gate de
cualquier lever = bvg + GO de Alberto).

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

---

## FASE 2 — mapa de ataque (cierre de la noche, ~03:30; detalle: `evals/s101_fase2_map.md`)
Diagnóstico de los 21 still-miss (workflow 21 agentes + síntesis lever-aware): **solo ~6 son fallos
REALES del generador** — el resto: ~10 mis-clasificación del instrumento (serving a nivel-doc, no
chunk-portador; TOC como ancla falsa; hp010 = matcheo por string no fact-id) + ~4 juez sobre-estricto.
**Levers (orden recomendado):**
1. **L1 — endurecer el clasificador** (serving a nivel-chunk + fact-id + TOC=not-served) → re-run (~$15-20). El scoreboard se VUELVE honesto; los ~10 pasan al ledger retrieval.
2. **L3 — juez v2 refinos** (morfología, cuantificadores, answer sin truncar) — mismo batch que L1; micro-check cat008 in/out vs fuente.
3. **L2 — ship de levers retrieval YA-GO** (los reclasificados los necesitan): hyq corpus-wide (D2) · **tramo A3-enunciados dirigido a las tablas señaladas** (params RP1r → r.I/05-295/ABORT; bornes ADW535 → EEPROM/PWR-R; Tipo SW AM-8200) · demote-TOC en rerank (barato) · split ZXe D1 (DEC-074).
4. **L4 — gate de familia-de-variantes en generación** (cat021: enumerar variantes o clarify-si-diverge, regla s79/s80; MÉTRICA declarada ≠ DEC-051-PASS) + **L5 directiva de cobertura** (los 2 de length/position — el fidelity-block ya midió +3/0, D6).
5. Residual esperado post-L1..L5: ~1-3 synth reales. Los reclasificados-a-retrieval se atacan con L2 y sus gates.
