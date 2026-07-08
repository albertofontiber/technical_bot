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

## Dual-judge de conveyed (s100b — CAMBIO DE JUEZ declarado)
El juez conveyed **v1 era GPT-5.5 single K=5** (contrato DEC-021). En s100 se verificó (leyendo las
respuestas del full) que daba **~5-7 FN/16 synth-miss** (valor LITERAL en la respuesta con conveyed=0:
hp006 'MPS-400', hp013 'EEPROM', hp018 '4 salidas'). **v2 = DUAL-JUDGE**: GPT-5.5 primario estricto → si
miss, **Opus 4.8 K=5 adjudica** (mismo prompt congelado); synthesis-miss requiere **consenso de miss**;
Opus≥4/5 (0 fails) → OK flagged `judge_disagreement` (listado en el output). Las reps de stability usan
el MISMO árbitro dual. Validación balanceada (artefacto: `evals/s100_dualjudge_validation.txt`): 5 flips
FN / coincide-miss 11/16 / **0 FP sobre valores perturbados-falsos (5/5 rechaza)** / 6/6 OK-reales.
**Implicación de comparabilidad:** filas del scoreboard con juez v1 y v2 NO son directamente comparables
en synth-miss (v1 sobre-cuenta) — por eso la columna "Juez". **Para comparar contra corridas v1:
`synth-miss_v1-equiv = synth-miss_v2 + judge_disagreements`** (el output lo imprime). Todo synth-miss
histórico (DEC-075/s87/s99) es single-GPT. Esto EXTIENDE DEC-021 (que difirió el dual-judge y fijó juez
único GPT-5.5), declarado como CAMBIO de juez: el eje soporte/invención sigue single GPT-5.5 + K-mayoría.
**Protocolo del run:** spot-check regla-C de los `judge_disagreements` listados (la suite de aceptación
n=5/6 es chica — la salvaguarda real es la trazabilidad del flip).

**Dual-SOPORTE targeted (s101):** el juez de soporte (GPT-5.5, mismo patrón estricto) mostró la MISMA
clase de FN — 6/7 facts "retrieval-miss" con candidato léxico en el pool eran FN (artefacto versionado:
`evals/s101_inpool_adjudication.json` — workflow de 7 adjudicadores + 21 refuters adversariales, 0/18
votos de refutación; p.ej. hp001 '2222' = "clave de administrador por defecto, 2222" literal). Regla:
**`sup_fam=∅`** (sin soporte same-family — no `sup` raw, que perdería el caso GPT-acredita-solo-cross-family)
+ `fact_match≥FLOOR` en pool → Opus K=5 re-juzga los candidatos ORDENADOS por score (cap 8, truncation
flagged); el flip = UNIÓN con sup y queda flagged `support_judge_disagreement`. **Residual declarado:**
soporte parafraseado NO-léxico con sup_fam=∅ sigue single-judge (clase no demostrada). El eje de
INVENCIÓN sigue single GPT-5.5. **Protocolo del run (igual que conveyed):** spot-check regla-C de los
`support_disagreements` listados. Caveat de validación (H6 dúo): los 7 adjudicadores/21 refuters del
artefacto eran Claude-family (validan a Opus con posibles blind spots compartidos) — mitigado por el
pre-gate léxico (el valor está LITERAL en el chunk acreditado) + trazabilidad del flip.

## v2.2 — kill de anclas-TOC en el crédito de soporte (s102, cierra la cuarentena H4)
Una página de ÍNDICE acreditada como soporte matchea el anchor léxico (sus títulos contienen los
términos) sin portar el CONTENIDO → un miss con soporte solo-TOC se clasificaba synthesis-miss
("el soporte llegó al generador") cuando el contenido nunca llegó. **v2.2**: en el crédito L1 de
hechos anclables, un chunk que `is_toc_page` (`scripts/toc_heuristic.py`, determinista, 9 tests)
se mata (`support_toc_killed` visible) y entra en el MISMO canal `l1_killed` → si el soporte queda
vacío, el rescate dual Opus re-adjudica (un título de TOC sí puede soportar hechos nominales:
"Importar archivo de licencia (.bin)"); la regla H1b (post-kill jamás aterriza corpus-gap limpio)
aplica. Efecto esperado: misses solo-TOC se re-bucketizan synthesis→rerank/retrieval (ledger
honesto). **El artefacto estampa `instrument: v2.2`** (cada cambio de juez/clasificador se declara
EN el output, no solo aquí). Residuo declarado: si el TOC-kill NO vacía el soporte, los killed no
se re-adjudican (consistente con L1 v2.1). Origen: lever demote-TOC en rerank medido NO-GO
(DEC-096, `evals/s102_toc_measure.yaml` — colateral: el LLM-rerank NO es determinista a temp=0).

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
5. **`answer[:12000]` (v2.1; era 6000 y truncaba respuestas ancho-10) en los jueces conveyed/submotivo:** con respuestas largas (ancho-10) un hecho
   transmitido al final puede truncarse → falso synth-miss. Heredado del juez; nice-to-have subir el cap.
6. **family fail-open:** si no se resuelve la familia del gold (`family_resolved=False`), el filtro se
   desactiva (marcado en el output, NO silencioso) — el famtie canónico los excluía. En s100: 0 golds.

## Scoreboard (append-only — 1 fila por corrida; traza la aguja)
> Números = salida cruda del instrumento; "corpus→verif" = tras verificación manual anti-FN. Clases
> mayoritarias (OK/synth/retrieval/rerank) son el eje comparable. Detalle por-hecho en el `.yaml` del run.

| Fecha | Commit | Juez | Corpus | OK | synth (estruct/flip) | retrieval | rerank | corpus-gap (raw→verif) | Flags demo | Notas |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-07 | e5d745d (+build s100 sin commitear) | v1 GPT-5.5 single | 25090 | 89 (67%) | **22 (16/6)** ⚠ sobre-cuenta (juez v1: ~5-7 FN verificados) | 13 (+~4 de corpus FN) ≈ **17** | 4 | 5 → **~0** (FN verif.) | RERANK_TOP_K=10 · ENUNCIADOS=on · IDENTITY=ADD · LLM_MAX=3500 | **BASELINE s100.** Síntesis = cuello dominante A NIVEL CLASE. Gold-review posterior (s100b): de los 16 "estruct." → ~5 judge-FN + ~6 scope (5 demotados) + 1 error real (hp010 Nivel-2/3) + cola real pequeña. Retrieval within-doc (11)=gap vocabulario. **Identidad + corpus ≈ 0.** `s100_factlevel_full_v1juez.yaml` |
| 2026-07-08 | 4dd97be+ (s101; golds: 5 demotes + hp011 r.I; corpus: r.S) | **v2 dual** (GPT→Opus, conveyed+soporte) | 25090 | **91 (71%)** | **22 (14 stable / 8 flip)** — REAL bajo árbitro dual (12 omitted · 6 partial · 4 contradicted; cluster cat021×4 = síntesis de familia-de-variantes 40/40) | **8** (cat016·cat022×2·hp011·hp012·hp013·hp014·hp018-1A) | 5 | **2** | idem + juez v2 | **BASELINE v2 (jueces sanos: 1+1 flips duales, 5 votos fallidos).** Upstream 18→10 por fixes de instrumento+golds. hyq NO shipped (cat016/6K8 cuentan aún; piloto GO aparte). NOTA: run intermedio inválido por cuota OpenAI muerta mid-run (en cuarentena `_v2_INVALIDO_quota`); fail-fast del primario cableado después. `s100_factlevel_full.yaml` |

| 2026-07-08b | s102 (L1 crédito-anclado+red-Opus · L3 juez v2.1 cap12k+cuantificadores) | **v2.1 dual** | 25090 | 89 (70%) | **18** (L1/L3 movieron 4 al ledger honesto; incluye residuo H4-TOC declarado + ~6 reales) | **11** | 7 | 3 → **0** (FN verif. a mano s102: cat013#0=55315013 p.9/20 · cat013#1='CLIP' literal MIDT190 p.69 (=identidad, DEC-074) · hp014#2=literal MIDT180 p.44, causa: gold `targets:[]` vacío — 6ª vez `feedback_corpus_gap`) | idem + seams pineados | Fila HONESTA post-endurecimiento (dúo ×2, 13 hallazgos). D4 aplicada DESPUÉS (hp009-aisladores demote → denominador −1 en el próximo run). hyq tramo-1 corpus-wide en generación (D2-OK). Próximo full = instrumento **v2.2** (H4 toc-kill). `s100_factlevel_full_v3juez.yaml` |

**Cómo añadir una fila:** correr `full` tras un cambio de pipeline/golds → estampar la fila (fecha, commit,
corpus count del manifest, el agregado, flags) → verificar corpus-gaps a mano → nota de qué cambió.

## Referencias
- Spec de diseño (dúo ×3): `evals/s99_factlevel_assessment_spec.md`.
- Decisión + racional: `docs/DECISIONS.md` (DEC-094).
- Instrumentos absorbidos (retirables): `retrieval_miss_judge` · `synthesis_miss_judge` ·
  `audit_retrieval_funnel` · `retrieval_miss_famtie` · `retrieval_miss_diagnose` · `synthesis_stability` ·
  `s87_rootcause`.
