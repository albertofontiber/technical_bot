# Assessment a nivel-hecho — doc CANÓNICO (s100)

**Qué es.** El instrumento estandarizado que mide **dónde cae cada hecho** de los golds a lo largo del
pipeline RAG: OK / synthesis-miss / rerank-miss / retrieval-miss / corpus-gap. Reemplaza los 4 instrumentos
ad-hoc (s85/s87/s88/s99) que bit-roteaban. **Fuente de verdad de "qué tal funciona el bot" a nivel-hecho**
— para trazar cómo cada mejora mueve la aguja (ver **Scoreboard** abajo).

**Entry-point:** `scripts/factlevel_assessment.py {smoke|full}`. Salida: `evals/s100_factlevel_<mode>.yaml`
(+ manifest embebido con freeze-contract) + `.partial.jsonl` resumible (auto-invalida si cambia el freeze).

## ⚠ Caveat de medición (leer siempre)
Mide la **RUTA EVAL-HARNESS**, no el bot Telegram real:
- **SÍ** el pipeline con los flags de la demo (Railway): `RERANK_TOP_K=10`, `ENUNCIADOS_MULTIVECTOR=on`,
  `IDENTITY_RESOLVE=on/ADD`, `LLM_MAX_TOKENS=3500`, `CHUNKS_TABLE=chunks_v2`, `HYDE=off`.
- **NO** `target_models` (priorización de producto del reranker) ni `available_models` (mensaje de
  fallback del generador) — eso es la ruta Telegram. Elegido así (s100) para **paridad con bvg / DEC-075 /
  ancho** y todas las mediciones previas → comparabilidad. Medir la ruta Telegram sería un track SEPARADO
  con su propio baseline.

## Cómo se corre
```
python scripts/factlevel_assessment.py smoke            # subset (5 golds) + estimación de coste (~$3)
python scripts/factlevel_assessment.py smoke --qids X   # golds concretos
python scripts/factlevel_assessment.py full             # 39 dev (~$22, ~2h, resumible)
```
El script EXPORTA los flags de la demo antes de importar el pipeline y **assertea** que resuelven (anti
bug-s45: medir top-5 local cuando la demo sirve 10). Smoke SIEMPRE antes del full (disciplina de coste).

## Taxonomía (v3, family-aware, TODOS los facts clasificados)
| Clase | Definición | Sub-motivo |
|---|---|---|
| **OK** | servido (post-`RELEVANCE_THRESHOLD`) + transmitido en la respuesta | — |
| **synthesis-miss** | servido pero la respuesta NO lo transmite | `omitted`/`hedged`(→lever PROMPT) · `partial`(→lever RETRIEVAL/chunking) · `contradicted`(valor distinto) · `threshold-drop` · **+ STABILITY**: `stable-miss`(estructural) vs `flip`(ruido de generación) |
| **rerank-miss** | chunk-soporte same-family en pool-50 pero NO sobrevive al top-k | `pos-buried`/`lexical-distractor` |
| **retrieval-miss** | servible en corpus pero NINGÚN chunk same-family en el pool-50 | `within-doc`(gap vocabulario) · `es-en` · `model-filter`/`cross-fam`(identidad) |
| **corpus-gap** | NO servible en el corpus (**default = FN-MÍO**, `feedback_corpus_gap`) | verificación anti-FN reforzada |
| *(meta-ref)* | el valor es un puntero (apéndice/tabla), no un dato → fuera del histograma | — |

**FAMILY-AWARE (clave):** un chunk-soporte solo acredita si es de la **misma familia de producto** que el
gold (vía `product_model`, reusa `retrieval_miss_famtie`). Sin esto, un valor que coincide por casualidad en
OTRO producto acredita mal (bug hp018/DEC-091b). **`lexically_anchorable`** es FLAG, no gate: prosa/
periodicidades se clasifican vía juez SEMÁNTICO (recupera la cola de síntesis que el gate `measurable()`
antes filtraba — comparabilidad con DEC-075).

## Limitaciones conocidas (declaradas — leer antes de sobre-interpretar)
1. **corpus-gap = FN por defecto** (`feedback_corpus_gap`): los golds son píxel-verificados servibles →
   corpus-gap real ≈ 0. Todo corpus-gap que reporte el instrumento se VERIFICA a mano (grep del valor en el
   manual objetivo) antes de aceptarlo. En s100 los 5 corpus-gap eran FN (el valor SÍ estaba en el manual).
2. **Sub-motivo de síntesis contaminado por scope/gold:** "omitted" mezcla synthesis-miss reales con
   **artefactos de scope** (ej. s100 hp007 'cada 6 meses': el bot respondió correctamente la pregunta ANUAL
   y omitió la periodicidad semestral porque no se preguntaba). Separar unos de otros = **gold-review
   por-hecho** (el eje gold/juez, etapa separada). El sub-motivo es INDICATIVO, no zanja qué lever mover.
3. **Eje gold/juez ADVISORY:** usa veredictos PASS de un bvg previo (no fresco). El eje gold/juez fresco
   necesita el PASS caro sobre el pipeline actual (diferido, gate Alberto).
4. **corpus-check por `targets` (no primario/family):** `target_servable` incluye corroboradores → un hecho
   servible solo vía manual corroborador puede tapar un corpus-gap del primario (dirección conservadora,
   consistente con #1). No corregido (impacto ≈0 dado #1).
5. **`answer[:6000]` en los jueces conveyed/submotivo:** con respuestas largas (ancho-10) un hecho
   transmitido al final puede truncarse → falso synth-miss. Heredado del juez; nice-to-have subir el cap.
6. **family fail-open:** si no se resuelve la familia del gold (`family_resolved=False`), el filtro se
   desactiva (marcado en el output, NO silencioso) — el famtie canónico los excluía. En s100: 0 golds.

## Scoreboard (append-only — 1 fila por corrida; traza la aguja)
> Números = salida cruda del instrumento; "corpus→verif" = tras verificación manual anti-FN. Clases
> mayoritarias (OK/synth/retrieval/rerank) son el eje comparable. Detalle por-hecho en el `.yaml` del run.

| Fecha | Commit | Corpus | OK | synth (estruct/flip) | retrieval | rerank | corpus-gap (raw→verif) | Flags demo | Notas |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-07 | e5d745d (+build s100 sin commitear) | 25090 | 89 (67%) | **22 (16/6)** | 13 (+~4 de corpus FN) ≈ **17** | 4 | 5 → **~0** (FN verif.) | RERANK_TOP_K=10 · ENUNCIADOS=on · IDENTITY=ADD · LLM_MAX=3500 | **BASELINE s100.** Síntesis = cuello dominante (16 estruct.: ~10 omitted/hedged=lever prompt + ~5 partial=lever retrieval + 2 contradicted). Retrieval within-doc (11)=gap vocabulario (DEC-085/86). **Identidad + corpus ≈ 0** con datos frescos. `s100_factlevel_full.yaml` |

**Cómo añadir una fila:** correr `full` tras un cambio de pipeline/golds → estampar la fila (fecha, commit,
corpus count del manifest, el agregado, flags) → verificar corpus-gaps a mano → nota de qué cambió.

## Referencias
- Spec de diseño (dúo ×3): `evals/s99_factlevel_assessment_spec.md`.
- Decisión + racional: `docs/DECISIONS.md` (DEC-094).
- Instrumentos absorbidos (retirables): `retrieval_miss_judge` · `synthesis_miss_judge` ·
  `audit_retrieval_funnel` · `retrieval_miss_famtie` · `retrieval_miss_diagnose` · `synthesis_stability` ·
  `s87_rootcause`.
