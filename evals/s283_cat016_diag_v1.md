# s283 — Diagnóstico cat016: artefacto de paridad de flags (HYQ_TABLE), no regresión

**Lane:** cat016-diag (s283). **Rama:** claude/s282-h0t2-qa @ 2809358. **DB:** SELECT-only. **Sin commits.**
**Baseline auditado:** `evals/bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml` (25 PARCIAL / 12 PASS / **2 FALLO = cat016, cat022**).

## TL;DR — VEREDICTO

cat016-FALLO del baseline oficial es un **ARTEFACTO DE PARIDAD DE FLAGS**, no una regresión.
El env del baseline **omitió `HYQ_TABLE=on`** (default del código = `off`), midiendo así una config
**distinta de la de producción** (Railway lleva `HYQ_TABLE=on`, DEC-099, verificado en query_logs).
El canal question-side hyq es exactamente el que arregló cat016 en s102 (DEC-099, flip 2/2:
cat016·autobúsqueda + hp018·6K8).

- **Traza retrieval ($0):** el chunk de la autobúsqueda (id `294a778c`, `55315013` render p11,
  «Para realizar la autobusqueda acceda al menú BUCLE…») está **AUSENTE del pool entero** SIN hyq;
  CON hyq entra como surrogate `HYQ_SURR` en el aside `post_hyq_aside`.
- **A/B pagado (retrieve→rerank strict K=10→generate, ~$0.2 total):**
  - HYQ **off** (env baseline): autobúsqueda **NO servida** en top-10 → respuesta omite el alta → reproduce el FALLO.
  - HYQ **on** (paridad): autobúsqueda **servida en posición 0** → respuesta describe el alta correctamente.
- **Harness canónico (juez GPT-5.5, `ONLY_QIDS=cat016`, HYQ on):** **cat016 = PASS** (los 5 hechos atómicos cubiertos).
- **Flip medido: FALLO → PASS.**

cat022 (el otro FALLO) es un gap REAL (banda IR 40/40L vs 40/40L4, Spectrex), NO relacionado con paridad.

---

## §1 — AUDITORÍA DE PARIDAD DE FLAGS (reusable para TODO baseline futuro)

Env del baseline (declarado): `COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on
IDENTITY_RESOLVE_POLICY=replace MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on RERANK_TOP_K=10
LLM_MAX_TOKENS=3500 GENERATOR_SELECTION_BLOCK=on GENERATOR_PROMPT_VARIANT=fidelity`.

Método: enumerados TODOS los `os.getenv(...)`/`_strict_on_off(...)` de `src/**` + el contrato de
`src/release_profiles.py`. Fuente de «Railway-esperado»: DEC-xx / `docs/ARCHITECTURE.md` §banner /
`docs/C1_RELEASE_RUNBOOK.md`.

### A. Flags que posee el profile `coverage_c1_v4` (encendidos ATÓMICAMENTE por el profile)
El baseline setea el profile → los 9 quedan ON = **CUBIERTO** (resueltos por `CoverageReleasePolicy`,
no por env-leaf; `_strict_on_off` los lee del policy para `PROFILE_OWNED_FLAGS`).

| flag | default leaf | c1_v4 | baseline (via profile) | estado |
|---|---|---|---|---|
| POST_RERANK_COVERAGE | off | on | on | CUBIERTO |
| STRUCTURAL_NEIGHBOR_COVERAGE | off | on | on | CUBIERTO |
| COVERAGE_MANDATORY_CALLOUT | off | on | on | CUBIERTO |
| MP_MANDATORY_VERB_TRIGGER | off | on | on | CUBIERTO |
| DOCUMENT_LOCAL_COVERAGE | off | on | on | CUBIERTO |
| EVIDENCE_CONTRACT | off | on | on | CUBIERTO |
| OBLIGATION_WARNING_RESERVE | off | on | on | CUBIERTO |
| PROSE_SOURCE_CARD | off | on | on | CUBIERTO |
| DOCUMENT_LOCAL_SELECTION_V2 | off | on | on | CUBIERTO |

### B. Leaf flags seteados EXPLÍCITAMENTE en el env baseline
| flag | default | Railway-esperado (ref) | baseline-env | estado |
|---|---|---|---|---|
| IDENTITY_RESOLVE | off | on (DEC-081/083) | on | CUBIERTO |
| IDENTITY_RESOLVE_POLICY | add | replace (c1_v3+ gate) | replace | CUBIERTO |
| MUST_PRESERVE_CONTRACT | off | on (req. c1_vN) | on | CUBIERTO |
| ENUNCIADOS_MULTIVECTOR | off | on (DEC-089/090) | on | CUBIERTO¹ |
| RERANK_TOP_K | 5 | 10 (DEC-092) | 10 | CUBIERTO |
| LLM_MAX_TOKENS | 2048 | 3500 (DEC-092) | 3500 | CUBIERTO |
| GENERATOR_SELECTION_BLOCK | off | on (DEC-101) | on | CUBIERTO |
| GENERATOR_PROMPT_VARIANT | base | fidelity (DEC-098) | fidelity | CUBIERTO |

### C. Leaf flags NO en el env baseline pero cuyo DEFAULT == Railway (cubiertos por default)
CHUNKS_TABLE (chunks_v2, además forzado por el harness) · RERANKER_BACKEND (llm, s67) ·
MERGE_STRATEGY (stamps, s68) · RERANK_PREVIEW_CHARS (800) · SERIES_REGISTRY_ENABLED (true/ON,
DEC-044) · HYDE_ENABLED (false) · NEIGHBOR_WINDOW (0) · HYQ_PILOT_QUOTA (10) · HYQ_PILOT_MIN_COS
(0.45) · HYQ_PILOT_FILE ("" — prod usa la TABLA, no el npz) · ENUNCIADOS_QUOTA_FUSION (off, CERRADO
PERMANENTE) · IDENTITY_FETCH (off, NO-SHIP DEC-084) · LEVER2_IDENTITY / IDENTITY_MAP / LEVER1_KEYWORD_ORDER
/ LEVER2_PM_RESCUE / NEIGHBOR_MODELS_ONLY (off, retirados/no-ship) · ANSWER_OBLIGATION_PLANNER (off) ·
GENERATOR_INCLUDE_CONTEXT (off) · las 6 coverage-lane leaf (TABLE_PREAMBLE_CLOSURE,
CANONICAL_HYQ_COVERAGE, COMPATIBILITY_BUNDLE_COVERAGE, RERANK_POOL_COVERAGE, STRUCTURAL_CASCADE_COVERAGE,
LOGICAL_RECORD_COVERAGE — off; c1_v4 las RECHAZA en boot si on) · EVIDENCE_DERIVATION_OVERLAY /
DEDUP_REFERENCE_NAVIGATION / R2_REPAIR_NAVIGATION / STRUCTURAL_NEIGHBOR_SHADOW (off) · CONVO_SHADOW /
CONVO_MAINTENANCE (off, Fase 0). **Todos = CUBIERTO** (default coincide con prod).

### D. GAPS — Railway espera un valor que el env baseline NO provee
| # | flag | default | Railway-esperado (ref) | baseline-env | impacto en retrieval/cat016 |
|---|---|---|---|---|---|
| **1** | **HYQ_TABLE** | **off** | **on** (DEC-099; ARCHITECTURE §banner; flip cat016 en query_logs) | **OMITIDO → off** | **GAP RETRIEVAL — causa medida de cat016-FALLO** |
| 2 | VISUAL_ASSETS_REGISTRY | off | on (foto viva; C1_RELEASE_RUNBOOK §6 «on en la foto documentada») | OMITIDO → off | GAP generator-side (adjunta diagramas a páginas ya citadas); **ortogonal a retrieval, NO causa cat016** |
| 3 | ORCHESTRATOR_PATH | off | on (F1, s282, post-baseline) | OMITIDO → off | GAP **byte-invariante** (routing compute-only; config.py: «byte-invariant with the historical path when OFF») — sin efecto en respuesta |
| 4 | CONVERSATION_POLICY | stub | impl (F1, s282, post-baseline) | OMITIDO → stub | GAP **solo multi-turn**; el harness es `serving_seam_v1_historical_single_turn_inputs` — no lo ejercita |

**Único gap que afecta retrieval/generación single-turn = HYQ_TABLE (#1).** #2 es cosmético
(diagramas), #3 byte-invariante, #4 multi-turn. #3/#4 además se activaron en prod en s282, DESPUÉS
del commit del baseline (33c87bd, s281): a la hora de estampar el baseline la prod-de-entonces no
los tenía; el gap real y persistente a s281 = HYQ_TABLE + VISUAL_ASSETS_REGISTRY.

¹ Caveat de entorno: en ESTA corrida el RPC `match_chunks_v2_enunciados` devolvió **HTTP 500**
(fail-open → sirvió sin surrogates de enunciados). No afecta la conclusión de cat016 (el fixer es
hyq, no enunciados) y el A/B off/on comparte ese fail-open, así que el flip es atribuible SOLO a
HYQ_TABLE. Se deja anotado como observación separada (posible incidencia de DB a revisar).

---

## §2 — TRAZA cat016 (retrieval, $0)

Query: «En la Detnov CAD-150, ¿como se da de alta un detector nuevo en el lazo y como se prueba que
funciona?». Gold ALTA = `55315013` §3.3 autobúsqueda (render p11); gold PRUEBA = `55315008`
§3.1.1.5 modo prueba. `retrieve_chunks(top_k=50)`, env baseline completo, único delta = HYQ_TABLE.

| | HYQ **off** (baseline) | HYQ **on** (paridad) |
|---|---|---|
| pool devuelto | 14 | 16 (`post_hyq_aside` 13→16) |
| chunk autobúsqueda (`294a778c`, 55315013 p11) en el pool | **NO (ausente)** | **SÍ — `HYQ_SURR` (ch=VECTOR)** |
| chunks 55315013 en pool con texto «autob» | 0 (pp. 12/8/10/1/9/7, ninguno lleva el texto) | +1 (el surrogate p11 lo lleva) |
| doc 55315008 (prueba) en pool | sí (8 chunks) | sí (9, +2 `HYQ_SURR`) |

El doc de instalación (55315013) SÍ está en el pool sin hyq, pero **el párrafo concreto de la
autobúsqueda no** (gap de vocabulario query↔celda, la clase que hyq/HyPE ataca — s86/s93/DEC-099).
El surrogate question-side de la tabla `chunks_v2_hyq` mapea una pregunta hipotética («¿cómo se da
de alta un detector?») al chunk-padre p11 y lo re-adjunta.

---

## §3 — A/B PAGADO: served top-10 + generación + juez

`retrieve → rerank(strict, K=10) → generate`, mismo entorno, único delta = HYQ_TABLE.

| | HYQ **off** | HYQ **on** |
|---|---|---|
| autobúsqueda en top-10 **SERVIDO** | **NO** | **SÍ — posición 0** (`HYQ_SURR`, sim-pregunta 0.481) |
| respuesta menciona autobúsqueda | **NO** (omite el alta) | **SÍ** («realizar una autobúsqueda del lazo… menú BUCLE… el sistema escaneará…») |
| parte PRUEBA (modo prueba, 20 min) | sí | sí |
| **veredicto** | **FALLO** (reproduce el baseline: «afirma que el procedimiento no está disponible») | **PASS** (harness canónico, juez GPT-5.5) |

Respuesta HYQ-on cubre los 5 hechos atómicos del gold: (1) alta autobúsqueda menú BUCLE ✓ (2)
asignación zona+elemento ✓ (3) modo PRUEBA de zona ✓ (4) retardo anulado + retorno 20 min ✓ (5)
menú ELEMENTO→VER estado/tipo ✓. Diag del juez: «cubre correctamente el alta por autobúsqueda…
la prueba mediante modo PRUEBA de zona… no contradicen lo esencial de la referencia» → **PASS**.

---

## §4 — CLASIFICACIÓN

**cat016 = ARTEFACTO DE PARIDAD DE FLAGS.** El baseline midió `HYQ_TABLE=off`, una config que NO es
la desplegada (`HYQ_TABLE=on` en Railway). Con paridad completa cat016 **flipea FALLO→PASS**. No hay
regresión de código ni gap de corpus (el gold es servible; el chunk existe y se sirve con la config
de prod).

Corroboración cruzada: el propio diag del baseline dice que la parte de PRUEBA estaba bien y que solo
«falla en lo esencial del alta» — precisamente la mitad que el canal hyq rescata (DEC-099 registró el
flip cat016·autobúsqueda como uno de sus 2 gates de aceptación).

**cat022 (2º FALLO) NO es artefacto de paridad:** banda IR 40/40L (2,5–3,0 µm) vs 40/40L4 (4,5 µm),
Spectrex — gap real de síntesis/retrieval, fuera del alcance de HYQ_TABLE. No flipea con paridad.

---

## §5 — RECOMENDACIÓN

1. **Re-estampar el baseline oficial de 39 con env de PARIDAD COMPLETA** = env actual **+ `HYQ_TABLE=on`
   + `VISUAL_ASSETS_REGISTRY=on`**. Un baseline que no refleja la config desplegada mide un fantasma;
   la disciplina «freeze-contract» (DEC-023) exige que el env medido == el env servido. Esta tabla §1
   debe volverse el **checklist de paridad de env** de todo baseline futuro (no solo cat016).
   - **Coste estimado:** ~$3 (una pasada de harness sobre los 39 golds; cifra consistente con las
     pasadas previas del proyecto).
   - **Qué cambia (esperado):** cat016 **FALLO→PASS** (medido aquí). Candidato adicional: **hp018·6K8**
     (el otro flip de DEC-099 vía hyq) — verificar si está entre los 39 y si sube. VISUAL_ASSETS_REGISTRY
     solo adjunta diagramas a páginas ya citadas → **no debería** cambiar veredictos (validar que no
     rompe ninguno). cat022 se mantiene FALLO (gap real, no paridad). Resultado probable: **≥13 PASS /
     ≤24 PARCIAL / 1 FALLO** (cat022).
2. **Antes del re-estampado**, resolver/o documentar el **HTTP 500 del RPC `match_chunks_v2_enunciados`**
   (§1 nota ¹): con ENUNCIADOS_MULTIVECTOR=on pero el RPC caído, el baseline nuevo mediría enunciados
   fail-open (= efectivamente off) y volvería a NO ser paridad. Verificar el estado del RPC en la DB
   antes de gastar los ~$3.
3. **No re-litigar cat022 aquí** — es un fork de síntesis/identidad (relacionado con DEC-100/101,
   displacement landing), independiente de esta lane.

---

## Repro (comandos, todos con el env baseline; delta = `HYQ_TABLE`)
```
# Traza retrieval ($0): con/sin HYQ_TABLE=on → posición del surrogate autobúsqueda 294a778c
# A/B gen + harness canónico:
COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on IDENTITY_RESOLVE_POLICY=replace \
MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on HYQ_TABLE=on RERANK_TOP_K=10 LLM_MAX_TOKENS=3500 \
GENERATOR_SELECTION_BLOCK=on GENERATOR_PROMPT_VARIANT=fidelity ONLY_QIDS=cat016 \
python scripts/test_bot_vs_gold.py     # → cat016 PASS (juez GPT-5.5)
```
Artefactos de trabajo (scratchpad, no versionados): `s283_cat016_trace.py`, `s283_cat016_ab.py`,
`_s283_ans_hyq_{True,False}.txt`, `_s283_harness_cat016_hyqon.yaml`.
