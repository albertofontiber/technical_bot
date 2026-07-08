# s102 — Plan autónomo (8 jul 2026, tarde) · REANUDABLE — sucede a s101_plan_autonomo.md

**Mandato vivo (Alberto):** OK>95% bajando buckets, upstream-first; GO = reducción del bucket;
BP+estructural+escalable-30+; flag de overfitting; decisiones inequívocas = tomar y comunicar
(log en `evals/s101_decisiones_alberto.md`); ambiguas → ese fichero con recomendación.

## Estado al escribir esto (rama eval/s100-factlevel-assessment, HEAD 5c5dd11)
| Pieza | Estado |
|---|---|
| Scoreboard v3 (juez v2.1): OK 89 (70%) · synth 18 (~6 reales) · retr 11 · rerank 7 · corpus 3 | ✅ estampado |
| Instrumento **v2.2** (H4 toc-kill, `instrument:` estampado en artefacto) | ✅ committeado — el próximo full estrena fila v2.2 |
| L2c demote-TOC | ✅ **NO-GO** (DEC-096) — seam en `evals/s102_toc_seam.patch`; colateral: LLM-rerank NO determinista a temp=0 |
| Tiebreak port | ✅ fuera de src/ (`evals/s101_tiebreak_port.patch` + guard) |
| hyq corpus-wide (D2-OK) | tramos 1-2 ✅ QA 15/15 c/u · **tramo 3 EN VUELO** · fix S4 aplicado (error≠done) |
| Fidelity block (D6) | +3/0 congelado válido — ship-candidato, gate bvg pendiente, SIN decisión Alberto |
| D5 (residual-ancilar) | recomendación NO perseguir — pendiente Alberto |

## Cola de ejecución (en orden)
1. **Tramos hyq 4-8** (~$12 c/u): al notificar cada tramo → QA muestral 15 (seed nuevo) → siguiente.
   Al CERRAR tramos: (a) pasada retry-empties (~848 `[]` históricos, ~$3, el fix S4 ya separa
   error/NONE hacia adelante); (b) commit del jsonl (NUNCA con tramo en append — S3);
   (c) build tabla A3-style `chunks_v2_hyq` con **dedup por chunk_id** (1.877 dupes de origen)
   + HNSW + RPC (patrón migración s95 con rollback) + embed (~$2-5) + cuota/barra portadas del
   piloto → (d) gate bvg no-regresión → (e) GO final Alberto para activación.
2. **L4 — gate de familia-de-variantes en generación** (cluster cat021 ×4, el mayor bloque synth
   real): GROUND HECHO (s102): los 4 facts cat021 tienen reaches_gen=True (contenido servido) pero
   el bot ELIGIÓ 40/40R y respondió solo su código de pedido — «40/40» es ambiguo entre variantes
   de tecnología DIVERGENTE (I=IR3 · U=UV · M=Multi-IR/hidrógeno · R=single-IR · L=?) → la regla
   s79/s80 exige ENUMERAR variantes (diverge) — fallo 100% generación, cero retrieval.
   Diseño candidato: bloque de prompt flag-gated (GENERATOR_VARIANT_GATE) «si la query referencia
   una familia y los fragmentos muestran variantes con tecnología/valores DISTINTOS → enumera por
   variante; clarify solo si no puedes enumerar». SENTINEL OBLIGATORIO: hp009 (family-genérico →
   answer directo, NO clarify — el otro lado de la regla s79/s80) + hp018 mixto. Medición fact-level
   A/B con árbitro dual; dúo antes de commit (generador = zona de dolor).
   Métrica declarada: facts cat021 conveyed en fact-level A/B + sentinels sin regresión (≠ DEC-051
   que fue PASS). OJO: cambio de generador = zona de dolor → dúo antes de commit.
3. **L5 — directiva de cobertura** (length-pressure/position-late, ~2 facts): relacionado con el
   fidelity block (D6) — si D6 recibe GO, medir L5 ENCIMA de fidelity para no medir dos veces.
4. **Verificación manual de los 3 corpus-gap del v3** (protocolo feedback_corpus_gap — son FN
   hasta probar lo contrario). Barato, judge-free (grep del valor en el manual objetivo).
5. Cierre de sesión: PLAN_RAG_2026 (compacto) + HISTORY (narrado) + DECISIONS (DEC-096 ya ✅) +
   LEVER_DIGEST (fila demote-TOC ya ✅; refrescar hyq al cerrar ship) + ARCHITECTURE + memoria.

## Reglas nuevas establecidas HOY (no re-aprender)
- **A/B de rerank exige control de ruido base** (OFF-vs-OFF o N-reps): el LLM-rerank cambia slots
  con input idéntico a temp=0 (S1, DEC-096b). El eje factual K=1 ya era inusable (DEC-090); esto
  extiende la norma al served-set.
- **Lever cerrado ⇒ seam a patch** (`git apply --check` + guard fail-fast que verifique que el
  dispatcher CONSULTA el flag — un stub no pasa).
- **Error de API ≠ registro vacío** en generadores resumibles (S4): no-write + reintento + fail-fast.
- PowerShell `>` escribe UTF-16 → los patches/artefactos SIEMPRE via Bash o `-Encoding utf8`.

## Cómo retomar si esto se para
- Leer este fichero + `evals/s101_decisiones_alberto.md` (sección s102) + `git log --oneline -8`.
- ¿Tramo hyq en vuelo? `Get-Process python` + contar líneas de `evals/s99_hyq_generated.jsonl`
  (cada tramo = +3000 registros de chunk). Relanzar: `python scripts/s102_hyq_corpuswide.py tranche 3000`.
- Artefactos de referencia: `evals/s102_toc_measure.yaml` (L2c), `evals/s100_factlevel_full_v3juez.yaml`
  (scoreboard v3 por-hecho), `evals/s101_fase2_map.md` (clusters synth).
