# s94 · SPEC del piloto extracción→enunciados (v2 POST-DÚO)

> **v1→v2:** dúo completo (cross-model GPT-5.5: 7 hallazgos [6 confirmados, 1 refutado por
> código] + sub-agente fresco: 8 hallazgos H1-H8, 0 FP [H3 spot-checked contra el store]).
> **Fork interno del dúo resuelto por regla-C:** el SWAP surrogate→padre NO contamina la
> métrica — la famtie acredita PRESENCIA, no score (`retrieval_miss_famtie.py:154-163`:
> `in_pool = any(cid in pin...)`), y swap-con-score-del-surrogate ES el multi-vector
> canónico (sub-agente A). El residuo válido del cross-model (reordenación post-merge,
> punto de inserción, desplazamiento por-índice) queda incorporado (H1/H2/H6).

## EL PROBLEMA (foco)
10 hechos-miss fine-grained (testbed post-paso-0, `evals/s93_bakeoff_resultados.md`): soporte
juzgado existe, familia correcta, NUNCA entra a canal. Mecanismo diagnosticado: gap de
vocabulario query↔celda. **Evidencia HONESTA (cross-model CRÍTICO-2): track C = 2/4 en el
subcluster de TABLA (micro-slice, no comparable 1:1); para la clase prosa-datos el mecanismo
es HIPÓTESIS a medir, no medido.** Objetivo: decidir el pase corpus (~$150-300 + QA aparte)
con evidencia POR CLASE.

## Criterio de decisión pre-registrado (ESTRATIFICADO — CRÍTICO-2/H8)
- **GO-tabla:** ≥2 flips famtie-estricto entre los hechos-clase-tabla (~4-6).
- **Clase prosa-datos:** reportada aparte; GO-prosa solo con ≥2 flips propios.
- Headline ≥3/10 se mantiene como resumen, pero **la decisión de presupuesto se toma por
  clase** (un pase corpus solo-tablas es opción legítima y más barata).
- **Un NO exige triage (H1):** cada no-flip se localiza con `_trace` por-etapa —
  surrogate cruza el canal y muere en merge-cut/diversify = **mecanismo VIVO, killer =
  lever de pipeline** (la clase hp012/DEC-085) ≠ NO-GO del mecanismo. Sin triage no hay
  veredicto NO válido.
- Guard de regresión: nueva-miss fuera del jitter ±2 sobre las 132 facts → NO-SHIP.
- **Empate R1-vs-R2 (H8):** diferencia de 1 hecho = ruido (n pequeño); empate → gana R1
  por coste (prior Pinecone declarado).
- **F4 declara (H8):** el effect-size del pase corpus queda ESTIMADO por extrapolación
  por-doc (el testbed son ~12 docs) — Alberto decide sobre lo medido, no sobre la estimación.

## Brazos
- **R2 enunciado LLM** (principal): fila/dato → frase técnica con producto+sección+valores.
  **Receta de embedding = EXACTAMENTE la que produjo el 2/4 (H4): blurb B7 ALMACENADO del
  chunk-padre + enunciado.** Sub-ablación prefijo-desde-store (la variante ortogonal-al-
  re-chunking): **delta-check ~$0.01 sobre los 4 hechos del track C ANTES de F2** — si el
  prefijo mueve el coseno más que la tie-band, se declara y R2 corre con blurb-padre.
- **R1 plantilla determinista** (decisor de coste): pairing `cabecera=valor` desde los `rows`
  del store. **Cobertura declarada (H3, verificado): rows presentes ~95% pero `isPerfectTable`
  minoritario (MIE-MI-530 5/34 · MIDT180 14/41 · MPDT280 29/65 · HLSI-MN-103 31/66) → el
  pairing es HEURÍSTICA en tablas imperfectas, no "por construcción"; R1 se limita a tablas
  con rows y su cobertura se reporta.** No es $0: parser + QA presupuestados (~horas, $0 LLM).
- **R3 resumen por TABLA** (control de granularidad, canon vendors).

## Invariantes v2
1. **Ancla estable por surrogate (MEDIO-4):** `(sha256-doc, page, table_index, row_hash)`
   guardada en el surrogate; re-link tras re-chunking = algoritmo declarado (buscar el chunk
   que contiene esa page/región). Ortogonalidad re-frameada honesta: el pase LLM nunca se
   repite; un re-chunking exige re-link mecánico + re-embed de enunciados si R2 corre con
   blurb-padre (solo embeddings, barato).
2. **QA de fidelidad a nivel de FILA (H3, sube de nivel):** el valor Y su discriminador
   (producto/variante/cabecera) deben co-ocurrir en la MISMA fila/línea fuente — caza el
   MISPAIRING (RD-TableBench: el fallo real es confusión de filas, no solo valores
   inventados; el propio track C tuvo best-stmts sin el hecho — hp018). Aplica a R1 Y R2;
   tasa por brazo reportada.
3. **SWAP surrogate→padre:** punto de inserción **PRE-merge** (antes del dedup de
   `_merge_channels`), fila del padre HIDRATADA completa (pm/source_file/language/status —
   si no, muere en post_superseded/post_lang o la famtie no acredita same_fam); múltiples
   surrogates del mismo padre → dedup keep-max; **canal de entrada registrado por flip**
   (los surrogates con pm también entran por content_search stamp 0.70-0.85 — atribución
   visible) (H6). **Delimitación DEC-069 re-redactada (H2): el swap NO INFLA el pool; el
   desplazamiento por-índice (los surrogates ocupan slots del top-50 corpus-wide para
   TODAS las queries) es real y lo MIDE el guard nueva-miss ±2** — no se niega.
4. **Padre-ACREDITABLE pre-mapeado en F0 (H5):** por hecho, el chunk-id con votes≥4 ∩
   same-fam ∩ RPC-recuperable (no-duplicate). Donde solo vota un `duplicate_of` (hp011:
   4581dc4b→b4347ec9 no-votado) → equivalencia declarada vía duplicate_of o hecho marcado
   no-medible-por-instrumento (no cuenta ni a favor ni en contra).
5. **Batch reversible CONCRETO (cross-model MEDIO-3):** los chunks nuevos se insertan con
   `extraction_sha256 = 's94-pilot:'+ancla` (columna TEXT NOT NULL existente, controlada
   por nosotros) → rollback = `DELETE WHERE extraction_sha256 LIKE 's94-pilot%'`. Sin DDL.
6. **Cita siempre del chunk-padre** (producción multi-vector): el texto derivado jamás se
   cita como manual.

## Fases
- **F0**: set fijo (~12 docs-soporte del testbed — reconcilia el "~6" de DEC-085, que era
  estimación; H7) + clasificación tabla/prosa por hecho + pre-mapa acreditable (inv. 4) +
  tabla de predicciones por brazo Y por clase + matriz de decisión (arriba) — TODO antes
  de generar nada.
- **F1**: generación 3 brazos sobre las mismas regiones + QA-fila (inv. 2) + delta-check de
  prefijo (R2). Coste ~$5-15 LLM.
- **F2**: probe cos-vs-frontera (harness track B) — **DEMOTED a PRIORIZACIÓN (cross-model
  MENOR-7 + H1): no mata brazos** salvo margen extremo y consistente; freeze estampado;
  declarado proxy (la frontera post-merge real es más dura: sim#(50−n_keyword), H1).
- **F3**: inserción con batch-mark + SWAP (inv. 3) + pin-regen + famtie ON/OFF vs control
  mismo-día. DOS eventos + triage `_trace` de cada no-flip (H1).
- **F4**: tabla brazo × clase × hechos × fidelidad × coste-de-escalar (**QA como línea
  aparte**, H7) + effect-size declarado estimado → decisión de presupuesto de Alberto.

## Guard-rails (sin cambio)
PASS no se toca · nada a demo (ship-gate famtie + bvg PASS-control ±2, decisión Alberto) ·
re-chunking fuera · overfit-al-testbed prohibido · coste piloto ~$5-20 + horas parser R1.

## Registro del dúo
Cross-model: 7 hallazgos — 6 confirmados aplicados; 1 refutado por código (CRÍTICO-1 núcleo:
"el score prestado contamina la métrica" — la famtie es de presencia; el residuo válido
incorporado vía H1/H6). Sub-agente: 8/8 confirmados (H3 spot-checked contra el store).
Tally: `evals/adversarial_review_log.jsonl`.
