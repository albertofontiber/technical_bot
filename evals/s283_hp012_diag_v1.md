# s283 — Diagnóstico hp012 (Notifier AM2020/AFP1010, answer-con-conflicto ES-vs-US)

**Lane:** hp012-diag (s283). **Rama:** claude/s282-h0t2-qa @ 1f35093. **DB:** SELECT-only. **Sin commits.**
**Baseline auditado:** `evals/bot_vs_gold_39_baseline_c1v4_parity_s283.yaml` (hp012 = **PARCIAL**, conducta_bot=answer-con-conflicto).
**Residual declarado** (DEC-152 «framing US hp012» · DEC-157 cola viva): *«no explica claramente la
discrepancia España vs US ni presenta bien las dos variantes completas; afirma el máximo de 4 lazos
como si fuera general y lo restringe a LIB-400».*

## TL;DR — VEREDICTO

El residual de hp012 son **DOS defectos apilados**, no uno:

1. **RETRIEVAL-MISS del total US (792 / 1980).** El chunk que enuncia la variante US COMPLETA
   —`15088SP` **p151** (id `b162a7eb`): *«El AFP1010 es capaz de un máximo de cuatro LIBs (792
   dispositivos en total…)»* + AM2020 1980— **EXISTE en `chunks_v2` pero NO entra al pool** (0/55).
   El bot literalmente **no puede** enunciar «792» ni «1980» (hechos atómicos *core*/`supplementary`
   del gold). Clase DEC-085 (within-doc miss, gap de vocabulario query↔celda). **Techo honesto: sin
   este chunk, ningún fix de presentación alcanza PASS.**
2. **PRESENTACIÓN sin atribución de mercado.** Con `396` (ES) y `4 lazos` (US) AMBOS servidos, la
   prosa los **funde bajo un único encabezado «AFP1010» sin decir ES-vs-US** → lee como
   contradicción interna, no como dos variantes documentales. **Estable 3/3.** Ningún mecanismo del
   pipeline atribuye por fuente: el `answer_conflict_guard` está gateado a Causa-Efecto (inerte
   aquí), el Evidence Contract dispara en un **eje EQUIVOCADO** (conteo-vs-figura, no ES/US) y su
   aritmética 4×(99+99) **jamás dispara** (operandos no co-servidos + 792 no servido), y el prompt
   `fidelity` empuja reporte literal por-fragmento (desalienta la síntesis cross-fragmento).

**Corrección a DEC-149:** la afirmación «el EC ya appendiza discloses ES/US + arithmetic 4×(99+99)
para hp012» **NO reproduce** bajo el contexto servido de paridad s283. El EC appendiza 2 notas
`declared_vs_enumerated` (10-lazos-lista-3, 4-lazos-lista-2), ambas en el eje conteo-vs-figura y
**potencialmente contraproducentes** (refuerzan la lectura de «fuente inconsistente»).

---

## §1 — TRAZA ($0): pool + servido top-10 + ledger EC offline

Env de paridad (DEC-157 §1): `COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on
IDENTITY_RESOLVE_POLICY=replace MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on HYQ_TABLE=on
VISUAL_ASSETS_REGISTRY=on RERANK_TOP_K=10 LLM_MAX_TOKENS=3500 GENERATOR_SELECTION_BLOCK=on
GENERATOR_PROMPT_VARIANT=fidelity`. Query: *«¿Cuántos lazos direccionables soporta la Notifier
AM2020/AFP1010 y cuántos dispositivos por lazo?»*. `retrieve_chunks(top_k=50)` → 55 chunks;
`rerank(strict, K=10)` + coverage → 12 servidos (== `[F#]` del writer).

### Chunks exactos de cada variante

| variante | dato | chunk | ¿en pool? | ¿servido top-10? |
|---|---|---|---|---|
| **ES (396 / 2 lazos)** | «AFP1010 limitado a máximo de dos LIB-200 (total 396)» | `MPDT280` **p3** id `5730afb3` | sí (rank 11) | **SÍ — F1 (pos 0)** |
| ES per-lazo (99+99, 10 lazos AM2020) | «AM2020 hasta 10 lazos, cada uno 99 + 99» | `MFDT280` **p4** id `c6340793`/`d582e7ba` | sí (rank 3) | **SÍ** (F2/F4 en runs pagados) |
| **US (4 lazos, sin total)** | «gabinete CAB-A3 con LIB-400 exclusivamente… máximo de cuatro lazos del AFP1010» | `15088SP` **p30** id `d8892f08` | sí (rank 42) | **SÍ — F4/F5** |
| **US total (792 / 1980) — el hecho que falta** | «El AFP1010 es capaz de un máximo de cuatro LIBs (**792** dispositivos en total)» + AM2020 **1980** | `15088SP` **p151** id `b162a7eb` | **NO (0/55)** | **NO** |
| US total (792, 2º testigo) | «= 792 …» | `15088SP` **p14** id `f03d3ae4` | **NO (0/55)** | **NO** |

- **Autoridad/orden:** la variante **ES gana la posición 0** (F1 = MPDT280 p3, el «396»); la US llega
  más abajo (F4/F5 = 15088SP p30/31) y **solo con el enunciado de «4 lazos», nunca con «792»**. El
  mapa de tokens del pool confirma: `396`→rank [11], `792`→**[] (ausente del pool entero)**,
  `1980`→ausente. `retrieve_chunks` trae 342 chunks-candidatos de 15088SP en corpus pero las páginas
  p151/p14 (los totales) quedan fuera del top-50 (gap de vocabulario: la pregunta pide «lazos… y
  dispositivos por lazo», no «total del sistema» — la celda p151 no casa).

### Ledger EC offline sobre las cards servidas ($0)

`build_obligation_ledger` (11 obligaciones) → **2 aplicables, ambas `attribution_conflict/declared_vs_enumerated`:**

```
[APPLIC] declared_vs_enumerated  MFDT280 p4  declared 10 enumerated 3  noun=lazos
[APPLIC] declared_vs_enumerated  15088SP p30 declared 4  enumerated 2  noun=lazos
```

`apply_evidence_contract` appendiza EXACTAMENTE:

```
- Nota: la fuente es inconsistente: "La AM2020 puede soportar hasta 10 lazos…" (MFDT280, p.4) declara
  10 lazos y la enumeración servida lista 3 (MFDT280, p.4).
- Nota: la fuente es inconsistente: "…máximo de cuatro lazos del sistema AFP1010." (15088SP, p.30)
  declara 4 lazos y la enumeración servida lista 2 (15088SP, p.30).
```

**Ambas notas son eje conteo-declarado↔figura-enumerada (una figura dibuja menos lazos que el
máximo textual) — NO el conflicto ES-vs-US.** Ninguna obligación `arithmetic` (4×(99+99)=792) ni
`parameter_two_values` (mismo sujeto, valor distinto, fuente distinta) se genera: la aritmética
exige multiplicador `total de N` + 2 sumandos `hasta A/B` **co-servidos en el mismo fragmento** (no
lo están) y el 792 no está servido; `parameter_two_values` exige líneas rígidas `Etiqueta: valor`
(la prosa «máximo de dos LIB-200» / «máximo de cuatro lazos» no matchea).

---

## §2 — REPRODUCE (~$0.4): 3 generaciones, prosa vs apéndice EC

`retrieve→rerank(strict,K=10)→generate_answer`, env de paridad completo, N=3 (sin juez —
clasificación manual). Todas `stop=end_turn`, 12 servidos, EC = 2 entradas idénticas cada run.

| señal (SOLO en prosa, apéndice EC excluido) | run1 | run2 | run3 | estable |
|---|---|---|---|---|
| `396` (ES total) | ✓ | ✓ | ✓ | **3/3** |
| **`792` (US total)** | **✗** | **✗** | **✗** | **0/3 (retrieval-miss)** |
| `1980` (AM2020 total) | ✗ | ✗ | ✗ | 0/3 |
| `4 lazos / cuatro` (US) | ✓ | ✓ | ✓ | 3/3 |
| `2 lazos / dos LIB-200` (ES) | ✓ | ✓ | (implícito) | 3/3 |
| **ATTR «España»** | **✗** | **✗** | **✗** | **0/3** |
| **ATTR «US / EE.UU.»** | **✗** | **✗** | **✗** | **0/3** |
| **ATTR «mercado / variante / discrepancia / difieren»** | **✗** | **✗** | **✗** | **0/3** |
| **CLAIM «máximo de 4 lazos» (como general)** | **✓** | **✓** | **✓** | **3/3** |

**Prosa AFP1010 de run1 (textual):**
> ### AFP1010
> - Número máximo de lazos: limitado a un máximo de **dos LIB-200** [F1]
> - Total máximo de dispositivos en el sistema AFP1010: **396 dispositivos** [F1]
> - El gabinete **CAB-A3** con módulos LIB-400 exclusivamente puede alojar un máximo de **cuatro
>   lazos** en el AFP1010 [F5]

### Clasificación por run (contra las 4 categorías del brief)

Los 3 runs caen en la **MISMA combinación estable** — no hay dispersión de modo:

- **(b) presenta ambas SIN atribuir ES-vs-US — DOMINANTE, 3/3.** «dos LIB-200/396» y «cuatro lazos»
  bajo el único header «AFP1010», sin una sola palabra de mercado/fuente-de-mercado. El lector no
  puede saber que provienen de dos manuales de mercados distintos.
- **(d) «4 lazos como general» — 3/3.** Enuncia «máximo de cuatro lazos» como capacidad real del
  AFP1010, restringida a CAB-A3/LIB-400 (exactamente el diagnóstico del baseline).
- **(a) parcial:** NO esconde una variante del todo (ambos valores aparecen), pero **degrada la US**:
  el total US (792) y el AM2020 (1980) desaparecen (no servidos) → la variante US queda coja.
- **(c) el apéndice EC contradice/ignora, 3/3:** el EC lleva discloses, pero en el **eje equivocado**
  (conteo-vs-figura); la prosa ni los usa ni se reconcilia con ellos, y para el lector *«declara 4 y
  la enumeración lista 2»* **compone** la lectura de contradicción interna en vez de aclarar ES/US.
  El disclose ES/US que el gold pide **no existe como kind**.

**Frontera:** la varianza entre generaciones es de sub-ítems menores (99+99 explícito o no); el
patrón de fallo (b)+(d) es **determinista 3/3**, no un flip single-pass.

---

## §3 — RAÍZ: por qué NINGÚN lever vivo atribuye el conflicto

| mecanismo | ¿debería surfacear ES/US? | por qué NO lo hace (verificado en código) |
|---|---|---|
| `answer_conflict_guard` (`answer_planner.build_answer_conflicts`) | candidato natural | **Gateado por `_CAUSE_EFFECT_INTENT`** (`answer_planner.py:1560`) → solo dispara en queries causa-efecto/retardo/salida. Para hp012 devuelve `[]` (verificado: `_CAUSE_EFFECT_INTENT.search(query)=False`). Es un detector estrecho de un conflicto CONCRETO (nº de menú «Causa y Efecto» entre revisiones, `KNOWN_ANSWER_CONFLICTS`), no un detector genérico. |
| `evidence_contract` (`declared_vs_enumerated`) | — | dispara en conteo-declarado↔figura (eje ortogonal); **útil-ruido** aquí. |
| `evidence_contract` (`parameter_two_values`) | sería el kind correcto | exige líneas `Etiqueta: valor` con misma etiqueta/unidad, valor distinto, fuente distinta. La evidencia de hp012 es **prosa** («máximo de dos LIB-200» vs «máximo de cuatro lazos»), no líneas param → 0 matches. |
| `evidence_contract` (`arithmetic` N×(A+B)) | daría 792 derivado | exige `total de N` + 2 sumandos `hasta A/B` **co-servidos**; no lo están, y 792 no está servido. 0 obligaciones. |
| prompt `fidelity` (DEC-098, SHIP) | — | «afirma SOLO como el fragmento lo establece LITERALMENTE; no añadas distinciones que el fragmento no mencione» → **desalienta** la síntesis «esto es ES vs esto es US» (es inferencia cross-fragmento). Con fidelity ON el writer funde 3/3. |

**Métrica de cada lever (Protocolo 2/4):** objetivo de HOY = hp012 **PARCIAL** (c1_v4, juez GPT-5.5
single-pass, baseline v2 s283). DEC-098 fidelity = SHIP medido en *golds de omisión* (≠ este eje;
demostrado insuficiente aquí). DEC-097 prompt-gated selection = **NO-GO** medido en *sobre-disparo
en preguntas de spec* (hp009 clarify-en-vez-de-answer 2/3→3/3). DEC-085/093 enunciados = mecanismo
que PAGA la clase fine-grained (hp012-'2 lazos/396' 0.621>0.569), medido en *retrieval-flip*.

**Generalización de clase (grep del gold store):** `conducta_esperada: answer-con-conflicto` = **n=1
(SOLO hp012)** de 51 golds. Las otras menciones dicen explícitamente *«NO es answer-con-conflicto»*
(cat024/cat009 = conflicto-revisión latest-wins, eje distinto). DEC-149(e): es-us **DIFERIDO como
clase** (corpus español-céntrico). → **un fix presentación-solo paga n=1 con blast-radius amplio =
peor ratio.** Un fix que generalice (retrieval de la clase agregado-total, o un seam EC determinista
reusable en multi-mercado futuro + conflicto-revisión) vale más.

---

## §4 — PROPUESTAS rankeadas (SIN implementar)

Nota rectora: **el techo lo pone el retrieval.** «792» es hecho *core* del gold y NO está servido →
cualquier fix de presentación aislado tapa (b)+(d) pero **no puede alcanzar PASS**. Por eso B lidera.

### Rank 1 — B: rescatar el chunk US-total (`15088SP` p151, `b162a7eb`) al pool vía enunciado/HyQ

- **Mecánica:** el chunk existe y es ORO (contiene «cuatro LIBs (792)» + AM2020 «1980» en una sola
  celda) pero muere en retrieval (within-doc miss, gap de vocabulario). Extraer su **enunciado**
  («¿cuántos dispositivos totales admite el AFP1010 / el AM2020?») a `chunks_v2_enunciados` (mismo
  mecanismo DEC-085/093 que ya pagó el lado ES '2 lazos/396') **o** un surrogate `chunks_v2_hyq`
  question-side (mismo canal que rescató cat016·autobúsqueda, DEC-099/157). Sirve el p151 → el writer
  tiene la variante US COMPLETA y limpia para citar.
- **Por qué NO repite DEC-097:** es **retrieval**, no un guardrail de prompt. DEC-097 falló porque
  una instrucción textual no auto-ejecuta y sobre-dispara en spec; aquí no hay prompt — se añade un
  vector recuperable, unit-testeable por su flip de rank.
- **Generaliza:** ataca la clase entera «agregado/total within-doc miss» (DEC-085), la de mayor masa
  estructural — no n=1.
- **Coste de medición:** **$0** confirmar el flip (trace: ¿el enunciado/surrogate de p151 entra al
  top-10?) → **~$0.4** `ONLY_QIDS=hp012` pagado. Métrica: 792/1980 → prosa (retrieval-flip); PASS
  solo si además se resuelve la atribución (ver C).
- **Riesgo/gap:** construir el enunciado es tarea de corpus (extracción); HyQ tiene quota. Y con 792
  servido, (b)/(d) pueden persistir → probablemente necesita A. Es el ceiling-lifter, no el fix total.

### Rank 2 — A: kind EC `attribution_conflict` cross-source de PROSA (sujeto igual, valor distinto, fuente distinta), answer-gated

- **Mecánica:** builder determinista nuevo en `evidence_contract.py`: detecta, entre fragmentos de
  **`source_file` DISTINTO**, el MISMO sujeto gobernado (stem «AFP1010»+«lazos») con **cardinal
  distinto** (2 vs 4) y hace **DISCLOSE con atribución de fuente**: *«Según MPDT280 (Notifier España)
  el AFP1010 admite 2 LIB-200 / 396; según 15088SP (US) admite 4 lazos.»* Reusa el render/cita de
  `parameter_two_values` (`_render_action`). Answer-gated (solo si la prosa ya dio un valor y omitió
  la contraparte con su fuente); gates de plausibilidad estilo `_count_conflict_ok`.
- **Por qué NO repite DEC-097:** es **código determinista, fail-closed, $0-testeable** contra el
  contexto servido — la clase de mecanismo que YA shippeó (DEC-149) y que ya existe como
  `parameter_two_values`. NO es un prompt: no puede «sobre-disparar en spec» de forma no-testeable;
  su disparo se mide offline en los 39 (colateral esperado 0). Añade un DISCLOSE (append), jamás
  reescribe la prosa. El sobre-disparo se acota con: fuente-distinta + cardinal-distinto +
  answer-gate + léxico de precisión existente.
- **Generaliza:** n=1 HOY, pero es un seam reusable para multi-mercado futuro (DEC-149e) y —con la
  guarda de NO-supersesión— **complementa** conflicto-revisión sin pisarlo.
- **Coste de medición:** **$0** oráculo EC offline (precisión/recall sobre las cards servidas de los
  39 — ¿dispara SOLO en hp012? colateral 0 en cat009/cat024 latest-wins?) → **~$0.4** hp012 + 3-4
  controles. Métrica: hp012 gana la atribución ES/US (tapa (b)/(d)); **sigue PARCIAL sin B** (falta 792).
- **Riesgo/gap:** debe **no disparar** en los golds conflicto-revisión (cat009/cat024 = latest-wins,
  no surface-both) — guarda dura por fuente-distinta-sin-supersesión. Requiere dúo Protocolo 3
  (zona-de-dolor: corpus/idiomas/EC-schema) antes de cablear.

### Rank 3 — C: B + A combinados (secuencial B→A)

- **Mecánica:** único camino que puede llegar a **PASS** (US total servido + framing ES/US disclosed).
  Secuencia: B primero (ceiling-lifter, validación $0 más barata) → re-medir hp012 → A solo si la
  atribución sigue fallando con 792 ya servido.
- **Coste:** ~$0.8 pagado + 2 dúos. Métrica: candidato real a PASS (único).
- **Riesgo:** 2 builds; scope-creep para un n=1 — justificar por el valor de clase de B (retrieval) +
  el valor de seam de A (EC reusable), no por hp012 solo.

### Rank 4 — RECHAZADA: enmienda al prompt `fidelity` («atribuye cada valor a su mercado ES/US»)

- **Por qué se descarta (DEC-097 aplicado):** un guardrail textual (a) **no auto-ejecuta** —el writer
  YA tiene el bloque fidelity y funde 3/3—; (b) **sobre-dispararía** en toda query multi-doc de spec
  (la mayor parte del corpus es multi-fuente) con riesgo en los golds conflicto-revisión y en los
  multi-source answer; (c) **no es $0-testeable** (exige runs pagados para caracterizar el
  sobre-disparo = exactamente el modo de fallo de DEC-097). Blast-radius amplio para pago n=1. El
  camino BP estructural es el detector determinista (A), no el prompt.

### Rank 5 — Aceptar el residual declarado (coste $0)

- hp012 fue gold-reviewed; DEC-152/157 ya lo declaran residual («framing US»). Dado n=1 + es-us
  diferido, mantener PARCIAL es defendible **si** B/A no pasan su gate de colateral. Es el default.
- **Observación honesta (no cambio de gold):** el hecho US «792» del gold está anclado a páginas
  (p151/p14) que el pipeline actual **no sirve**; el gold es plenamente servible SOLO si el retrieval
  alcanza p151 (Rank 1). Es diagnóstico, no re-litigio de la barra.

### Secundaria (riesgo de precisión, no headline)

Las 2 notas `declared_vs_enumerated` del EC para hp012 son plausiblemente **net-negativas** (enmarcan
un hueco figura-vs-conteo benigno como «fuente inconsistente», componiendo la lectura de contradicción
interna). Merece un vistazo de precisión al kind (¿cuántos de los 39 reciben este disclose figura-vs-
conteo y en cuántos es genuino?), pero **suprimir es arriesgado** (regresaría los casos donde el
disclose es real) → medir antes de tocar; fuera del alcance de esta lane.

---

## Repro (comandos; env de paridad, delta = ONLY_QIDS=hp012)
Los scripts viven en el scratchpad de sesión (no versionados, convención de las lanes s283).
```
# TRAZA ($0): pool + servido + ledger EC offline  (identifica 396@F1, 4-lazos@F4/5, 792 ausente)
python <scratchpad>/s283_hp012_trace.py
# REPRODUCE (~$0.4): 3 generaciones, prosa vs apéndice EC
N_RUNS=3 python <scratchpad>/s283_hp012_repro.py
# Harness canónico single-turn (opcional, ~$0.4):
COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on IDENTITY_RESOLVE_POLICY=replace \
MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on HYQ_TABLE=on VISUAL_ASSETS_REGISTRY=on \
RERANK_TOP_K=10 LLM_MAX_TOKENS=3500 GENERATOR_SELECTION_BLOCK=on GENERATOR_PROMPT_VARIANT=fidelity \
ONLY_QIDS=hp012 OUTPUT_OVERRIDE=evals/_s283_hp012_harness.yaml python scripts/test_bot_vs_gold.py
```
**Artefactos de trabajo (scratchpad, no versionados):** `s283_hp012_trace.py`, `s283_hp012_repro.py`,
`probe_hp012_792.py`, `_s283_hp012_served_dump.txt`, `_s283_hp012_ans_run{1,2,3}.md`.
**Chunk IDs clave:** ES 396 = `MPDT280` p3 `5730afb3` · US 4-lazos = `15088SP` p30 `d8892f08` ·
**US 792/1980 (existe, NO servido) = `15088SP` p151 `b162a7eb`** (+ p14 `f03d3ae4`).
