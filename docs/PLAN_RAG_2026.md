# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 15 jun 2026 (s76, DEC-058 — **revisión estructural de los 29 NO-PASS en ultracode**: la fase de
> levers de RETRIEVAL está AGOTADA; la clase NO-tocada por esa fase es de DATOS = contrato de
> REVISIÓN/precedencia [#4, spec escrito]. **PROD-REACH medido:** el gate del handler corta 7/9 mal
> antes del RAG [catálogo desincronizado + regex] → deploy-prep #49 SUBE. **Sonda dual-judge:** el ruler
> tiene un sesgo sistemático MEDIDO [30.8% cross-model; cat019/cat020 = falsos NO-PASS], no solo ±2.
> NADA shippeado [3 builds gated]. 1 workflow + 2 cortes cross-model, 0 FP).
>
> **El historial vive en [`docs/HISTORY.md`](HISTORY.md)** (movido en s56): log de sesiones
> s30→s55, rationale histórico de mayo 2026 (secciones originales ## 1-9, con su numeración —
> las citas antiguas tipo "PLAN §9.14" o "§660" resuelven allí) y changelog. Este fichero queda
> compacto a propósito: es el doc que se relee en cada arranque de sesión.
>
> **📍 Mapa canónico (un dueño por tema).** ESTE documento es el **único canónico** del
> **roadmap + estado + qué sigue**. Los demás lo referencian, NO lo duplican:
> `docs/RULER_DESIGN.md` = diseño del ruler (D1-D11 + §2 procedimiento + §8 taxonomía);
> `docs/DECISIONS.md` = el *por qué* de las decisiones med/alto; `TECH_DEBT.md` = deuda con
> triggers; `docs/ARCHITECTURE.md` = cómo funciona el sistema; `docs/HISTORY.md` = traza
> histórica (append-only). Si el rumbo aparece en dos sitios y discrepan, **manda éste**.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best practice con fuente
> identificable, (2) estructural — ataca la causa raíz, no el síntoma, (3) escalable a 30+
> fabricantes sin fricción por fabricante. Si una propuesta no cumple los tres, se declara como
> gap honesto.

## Estado actual (s83 — 18 jun 2026)

**s83 (DEC-066): el pre-filtro vectorial family-aware (headline construido) = NO-OP MEDIDO → revertido; el lever de los model-filter-excludes es LEVER2_IDENTITY (resolución de identidad). Dúo #11 (sub-agente Opus + cross-model GPT-5.5) cazó el confound. NADA en prod/mergeado.** Tras **5 rondas de pushback** de Alberto (plan-primero + máxima autonomía/ultracode), el headline quedó en su punto 1: el canal vectorial NO pre-filtra por modelo (los léxicos sí). Construí el pre-filtro FAMILY-AWARE del canal vectorial (over-fetch 200 + filtro recall-safe `passes_nivel2 ∪ unknown`, flag `MODEL_PREFILTER`, a nivel doc/familia reusando `series_registry`). **VEREDICTO (aislamiento 2×2 hp018): el pre-filtro SOLO = INERTE; `LEVER2_IDENTITY` SOLO recupera el primario** (MIE-MI-310 corroborador → MIE-MI-530 e-series) — porque al resolver ZXe→ZX2e/ZX5e los canales LÉXICOS (que YA pre-filtran por modelo) recuperan el manual; el vectorial no necesita pre-filtrar (el post-filtro ya limpia su ruido). **El cuello era la RESOLUCIÓN de identidad, no el canal vectorial → el lever real = `LEVER2_IDENTITY` (B4, ya candidato en DEC-065).** bvg K=5 (hp018+hp009): recupera el e-series correcto en ambos; **hp009 residual→K-INESTABLE** (mejora, gana votos PASS), **hp018 residual→residual** (recall arreglado pero **reach≠PASS**, residual=generación/diodo) = **GRIS** (movimiento + 0 regresión, 0 PASS-control limpio). Pre-filtro **REVERTIDO** (eval-driven; 353 tests verdes restaurados). **Pieza 3 (bilingüe, $0)**: lever PEQUEÑO — 9 pares ES/EN casi-idénticos (~205 ch duplicados, dedup) + EN-only real solo 2-3 golds + ho002/ho014=ModuLaser NO-ingestado → fork s84. **Qué sigue**: decisión de Alberto sobre ship de B4 (corrección de identidad REAL —arregla ZXe↔ZXAE/ZXEE + mejora hp009—, pero GRIS no-PASS); s84 = A1 (matcher es-en + histograma verdadero, foundational), limpieza broad de identidad (~78 pm-compuesto + 114 mis-atribución), B5 (hp006 AFP-400 series), categorías (TECH_DEBT #44), versiones. **DEC-056 SIGUE (ranking); el RECALL vía identidad es lever DISTINTO.**

### Antecedente s82 (DEC-065)

**s82 (DEC-065): investigación CORPUS-GAP (prioridad de Alberto) + plan PRIMARIO/RETRIEVAL. Workflow 29-agentes + cross-model (dúo #10), 0 FP. NADA en prod (diagnóstico).** **VEREDICTO (acotado): los 9 CORPUS-GAP del audit s81 son FN del matcher léxico — 0 reales** (el valor está VERBATIM en el corpus, casi siempre el manual objetivo; raíz = es-en [LlamaParse extrae la columna EN de manuales multilingües] + OCR/acento + literal-compacto + filename≠doc-nº). Es el residual es-en que s81 declaró diferido → PROBADO material (fabricó el bucket). Verificado: verificadores frescos (volcaron chunks DB) + regla-C propia al píxel (cat007/cat020/hp013). **Histograma corregido: CORPUS-GAP 9→0** (reubican a RETRIEVAL o downstream-gen). **PRIMARIO 2/4 reales:** cat019/hp001 = falso-positivo de source-naming del audit (token gold ≠ filename; primario es #1 del pool); cat011 reach≠PASS; hp018 real (model-filter). **Cuello real = RECALL** (DEC-056 SIGUE: ranking agotado, recall es lever DISTINTO): model-filter-excludes ×3 (hp018/hp002/hp006) + recall-frontier-vector ×6. **PLAN A/B/C:** **A** instrumento/gold no-eval (A1 matcher CORPUS-GAP es-en/OCR-aware [raíz; versionar/congelar]; A2 matcher PRIMARIO slug-laxo; A3 gold cat011); **B** PROD model-filter MEDIR (B4 hp018 CANDIDATO `LEVER2_IDENTITY=ON`; B5 hp006 series-registry; B6 hp002 broad-fallback); **C** PROD recall-frontier MEDIR (C7 within-doc diversify [contrato+métrica]; C9 cat016 synonym-aware). Orden A→B4→B5/B6→C7→C9. `scripts/corpus_grep.py` = herramienta reusable. El cross-model cortó mi over-claim de framing OTRA VEZ (#42-#47, 6ª sesión = control estructural). **Qué sigue:** ejecutar el plan (fork abierto a Alberto: A1 matcher es-en vs B4 hp018-flip primero). **DEC-056 SIGUE (ranking); el RECALL es lever DISTINTO.**

### Antecedente s81 (DEC-064)

**s81 (DEC-064): instrumento del audit ARREGLADO (DEC-061) + audit de los 30 NO-PASS CORRIDO → distribución de raíces. Contrato de autonomía nuevo (`feedback_autonomy`: actúo-y-reporto, el DÚO es el anti-bias, stop-line=el merge lo da Alberto).** Re-secuencié D1 detrás del audit (orden de DEC-061): verifiqué al píxel que NINGÚN gold canónico apunta a ZXSe → la findability-D1 es eval-inerte + dispara el blast-radius del catálogo (DEC-063). **Instrumento (5 defectos de DEC-061(e)):** retiré el matcher roto del funnel; predicado limpio `fact_match_score` **VALOR-EXIGIDO** (el datum debe estar [cov>0] + texto como contexto → mata el FP 'prosa sin el dato' + el FN token-corto); `measurable` segrega no-medibles (single-digit `1 A`/`4 circuitos` → juez semántico diferido); confianza por SCORE (borderline), no a priori; primario-vs-corroborador con flag PRIMARIO-NO-RECUPERADO; fuente k5; K=1 (reranker temp=0). **Dúo #9 (3 rondas, 3 cross-model + 3 sub-agente Opus, 0 FP)** cazó en cada ronda — incl. una REGRESIÓN que introduje en `bvg_kmajority` (cazada por grep regla-C, legacy restaurado); capé en r3 (anti-#45). **HISTOGRAMA de los 30** (~93 hechos medibles + 19 no-medibles): **RETRIEVAL 28-38 (recall, NO ranking) ≈ SINTESIS 34-39 (gen/gold/juez) >> RERANK 6-7 >> CORPUS-GAP 9; 16 borderline; 4 PRIMARIO-NO-RECUPERADO (cat011/cat019/hp001/hp018).** **Lectura: DEC-056 (RANKING agotado) CONFIRMADO (RERANK ~7%) pero MATIZADO — el RECALL (~38%) NO está cerrado y es en parte IDENTIDAD → RE-VALIDA D1/D3 VÍA el bucket RETRIEVAL** (el instrumento-primero pagó: localizó dónde importa la identidad, vs findability-por-sí-misma eval-inerte). Caveats: 83% cobertura (19 no-medibles=juez semántico diferido), corroborador=SINTESIS (flags marcan lo peor), CORPUS-GAP=riesgo FN. reach≠PASS, NADA en prod (instrumento+diagnóstico, branch-local); 353 tests; held-out intacto. **Qué sigue:** atacar los co-binding — (1) recall/identidad: los 4 PRIMARIO + el bucket RETRIEVAL (D1/D3, por qué el primario no se recupera) — AHORA con eval-leverage demostrado; (2) generación/gold de los SINTESIS (gold-review + dual-judge ~sept) vía el deep-dive por-SINTESIS (C5, diferido); juez semántico para los no-medibles. **DEC-056 SIGUE (ranking); el RECALL es lever DISTINTO.**

### Antecedente s80 (DEC-062/063)

**s80 (DEC-062/063): backfill de identidad de la SERIE FAAST LT-200 APLICADO en prod (DB-only, findability de serie VIVA) + criterio gold D6 (core/supp=IMPORTANCIA). Verificado AL PÍXEL que NO arregla cat007** (standalone 6574 vs addressable 6575/6577 difieren en prealarma/lazo, pero los hechos de cat007 son IDÉNTICOS en las 3 → alcanzable vía 6574 → cat007 es downstream: rerank/gen/es-en/gold). **Backfill** `s80_faast_backfill.py` (FX1 6575 `LT-200`→`FAAST LT-200` 78 + FX2 6575-ES mfr→Notifier 41 + FX3 6577 `ASD11`→`FAAST LT-200` 73; count-match→snapshot→apply lotes-10→from=0 ∀; reversible). **Decisiones (Alberto):** manufacturer=`Notifier` pragmático (el seam multi-marca NO existe → OEM System Sensor + Morley → D3); 6577 pm=`FAAST LT-200` serie (modelo NFXI-ASD11 → D3, recuperable como metadata pero path bare de usuario perdido-hasta-D3). **NO eval-inerte** (product_model visible al generador) → guardarraíl findability+ por handler real + no-regresión; riesgo cross-gold BAJO (solo cat007 en la familia; "LT-200" sigue substring). **Criterio D6 (cross-model, cita BP TREC/RAGAS/DeepEval/ARES):** core/supp=IMPORTANCIA no provenance; inferencia válida si predicado⊆documentado; no-invención en el OUTPUT; **el eval CANÓNICO (juez holístico sobre `gold_answer`) es INERTE a `tipo`** → core/supp gobierna el audit, NO el veredicto. cat007 failsafe=inferencia válida (sin editar). **HALLAZGO LATENTE (DEC-063): `model_catalog.json` congelado en s55 (`8876e56`); prod LEE el json (no reconstruye) → el detector dinámico no refleja s64/s77/s78. PERO el gate lee la DB LIVE (`lookup_model_manufacturer`/`manufacturer_in_db` = httpx Supabase) → s77/s78 SÍ vivos; catálogo-stale = LATENTE (solo afecta extract de modelos post-s55, fall-through seguro), no bug activo.** Dúo: 2 cross-model (6/6+7/7) + 1 workflow 3-fases, 0 FP; #42/#43 reincidió 3× sobre framing, cortado por cross-model = control estructural. Lección #45/#46: verificar dominio AL PÍXEL yo mismo (preguntar no escala). reach≠PASS; 353 tests; prod (DB) tocado+reversible, held-out intacto. **Qué sigue:** D1 (backfill ZXSe `MIE-MI-600 unknown→familia` + split ZXe `ZX2e/ZX5e`, con split de catálogo + regen — `extract("ZX5Se")=[]` verificado) → arreglar el instrumento del audit (predicado limpio + banda error + fuente k5) → correr el audit de los 30 → priorizar. Backlog baja prioridad: re-sync catálogo s55→hoy (full no-regresión) + CI anti-drift. dual-judge gated (~sept). **DEC-056 (levers de RANKING agotados) SIGUE — NO re-litigado.**

### Antecedente s79 (DEC-061)

**s79 (DEC-061): gate pre-D2 → el matcher de recall (`chunk_has_quote_strict`) está ROTO (FP `'24'∈'240'`/`'2222'`∈cualquier chunk; FN prosa OCR) y contaminó las conclusiones de retrieval de la sesión (rank-53/64/87, "within-doc muerto", "corpus-gap cat016/cat007" — cat016/cat007 SÍ están en el corpus, SQL).** El plan de revisión de los **30 NO-PASS por raíz VIVE** (cascada CORPUS-GAP/RETRIEVAL-MISS/RERANK-MISS/SINTESIS + predicado bimodal + ejes generación/gold-design/judge), pero el **dúo (workflow 7-lentes Opus + 4× cross-model GPT-5.5) = CON-CAMBIOS, NO escalar aún**: el quote-path del funnel (`audit_retrieval_funnel.py:132`) sigue usando el matcher roto para ~63% de hechos; el juez semántico no está implementado (bias #44); C6 invertido (`audit_locator` tiene 2 fixes que el funnel NO tiene → portarlos); C3/C4/C5 con fallos (reranker equivocado / sin banda de error / fuente k5 / eje gold-design circular). **Hallazgos accionables SQL-verificados:** identidad FAAST LT-200 mal-tagueada en 3 manuales (6574=`FAAST LT-200`/6575=`LT-200`·System Sensor/**6577=`ASD11`**, OEM Notifier-exclusivo → el tag excluye el chunk del failsafe = mejora de retrieval VÍA IDENTIDAD, candidato backfill s78-style); gold-flags cat007 "FAILSAFE"=inferencia-no-en-fuente (no fabricada), **hp009=answer family-genérico** (NO clarify en bruto), hp018=mixto. **Lección `feedback_my_bias #45`: SOBRE-INSTRUMENTACIÓN + sobre-corrección** (espiralé construyendo aparato; al frenar el dúo sobre-corregí a "abandonar"=bias #30; Alberto lo cortó). reach≠PASS, NADA en prod (toda la sesión = investigación + diseño). **Qué sigue:** gold-review D6 (cat007/hp009/hp018, $0, primero) → backfill identidad FAAST LT-200 → arreglar el instrumento del audit (predicado limpio en el funnel + coste acotado + banda de error + fuente k5) → correr el audit de los 30 → priorizar. dual-judge gated (organic-eval ~sept). **DEC-056 (levers de RANKING agotados) SIGUE — NO re-litigado.**

### Antecedente s78 (DEC-060)

**s78 (DEC-060): curación de identidad del corpus (ground-truth de Alberto, 4 familias) → BACKFILL A APLICADO en prod** (correcciones de marca/etiqueta **eval-inertes**, reversibles vía snapshot): RP1r-Supra Morley→Notifier 312 [arregla el mismatch-refuse del gate, **LIVE**], NFXI-ASD Securiton→Notifier 135 (+7 docs), NFXI-FLX 83, canonicalizaciones ZX50 126/ZXR50A-P 18/RP1r 65 = 447 mfr+292 pm. Dúo #8 0 FP; **eval-freeze 9/39** (vs ~10/39 base = ruido del juez, sin movimiento, cero PASS→FALLO). **Securiton = marca aparte (Detnov la vende), NO Honeywell.** Lección HNSW: UPDATE masivo→`statement timeout` → PATCH en lotes (reusable). **Backlog (no perder, spec `_s78_identity_backfill_spec.md` §DIFERIDO + memoria):** **D1** findability ZXSe/ZX1e (tag combinado + **split del catálogo** en `build_model_catalog.py`+regen — verificado que el tag SOLO no basta, `extract("ZX5Se")=[]`); **D2** levers de retrieval de los ~10 golds (preview-2400 aislado + within-doc; pre-checks cat022/cat007 hechos); **D3** Capa-2 multi-marca (grupo Honeywell + alias OEM↔vendedor, **TECH_DEBT #5 trigger cumplido**); **D4** contrato #4 revisión (v04/v07 HLSI-MN-103); **D5** sección↔variante; **D6** gold hp009/hp018→clarify. **reach≠PASS, ~0 eval — es corrección de prod + escala, no la métrica.** Rubric del juez sigue en cola (organic-eval ~sept).

### Antecedente s77 (DEC-059)

**s77 (DEC-059): gate-fix #49 CABLEADO = fall-through manufacturer-aware (Option D) — PR #85, NADA en prod aún (Alberto mergea → Railway despliega).** El gate del handler ya no da falso-refuse cuando la marca está en DB pero el modelo es un nombre de FAMILIA. **Audit (`s77_gate_audit.py`, DB real) corrige el framing de s76:** los 6 catalog-miss son **familia↔variante** (CAD-150→CAD-150-8/R, ZXe→ZX2e/ZX5e, 40/40→40-40L/M; los "103/157/486 chunks" eran SUMAS sobre variantes), no "modelo ausente". **Medido judge-free** (`s77_fallthrough_measure.py` + `s77_regression_probes.py` K=3 + smoke por el HANDLER REAL `s77_handler_smoke.py` 10/10 + 353 tests): 6/6 fall-through MEJOR que el falso-refuse (cat013 refuse-inference ✓, cat021 clarify ✓), no-regresión del fallo opuesto (el path fiel admite/rehúsa 3/3). **reach ≠ PASS y CERO delta de eval — ESTRUCTURAL** (el harness bypasea el gate): corrección de PROD, no sube la métrica. Dúo #7 (Opus+GPT-5.5) 0 FP; el cross-model rebajó mi sobre-afirmación (bias #42). Los 3 mismatch (RP1r/Securiton-OEM) NO los arregla esto → contrato de identidad #49.

### Antecedente s76 (DEC-058)

**s76 (DEC-058): revisión estructural EXHAUSTIVA de los 29 NO-PASS en ultracode = la fase de levers de
RETRIEVAL está agotada de verdad; la única clase NO-tocada por esa fase es de DATOS.** 1 workflow
ultracode (29 agentes, 7 clases × diagnóstico + 3 lentes adversariales) + 2 cortes cross-model GPT-5.5
(8/8 y 7/7, **0 FP**). Alberto eligió ejecutar 3 acciones MEDIBLES (no parar):
- **(1) PROD-REACH (medido, judge-free, `scripts/s76_prod_reach.py`):** el gate manufacturer-check del
  handler (telegram_bot.py:292-339) corta **9/29 antes del RAG; 7 son cortes ERRÓNEOS** (verificado en DB:
  corpus con 103-581 chunks del modelo, pero el catálogo de `lookup_model_manufacturer` está
  DESINCRONIZADO [CAD-150/ZXe/40-40 ausentes] + el regex mete RP1r/Morley bajo Notifier); 2 son frontera
  OEM-relabel. → para esos 7, ningún fix de retrieval ayuda en prod; el fix es el GATE (#49, deploy-prep).
  Confirma el mecanismo del NO-OP de LEVER2_IDENTITY (ZXe cortado antes del RAG). **reach ≠ PASS.**
- **(2) Contrato de revisión #4 = SPEC** (`evals/_s76_revision_contract_spec.md`, diseño no-build):
  árbitro de precedencia (revisión=latest-wins vs variante-regional vs OEM vs multi-parte vs datasheet;
  ante duda NO supersede) + validación judge-free; **vía = backfill s64-style (sin re-ingestión ni DDL — columnas
  ya existen en `documents`, `revision_date` 1/1170 = gap del parser) → candidato CERCANO, no gated a ingesta**. La
  única clase estructural que el lever-phase de retrieval no tocó (cat009/cat024; cat008 es OEM-relabel→identidad).
- **(3) Sonda dual-judge holística (medido, `scripts/s76_dualjudge_sonda.py`):** el dual-judge holístico
  NUNCA se midió-primero (s47 midió los ejes del scorer, no el ruler de veredicto). Medido = **30.8%
  desacuerdo cross-model, 11/12 Claude más laxo**; cat019/cat020 = sesgo sistemático del juez
  triple-confirmado (audit humano should_be=PASS + Claude=PASS vs GPT-PARCIAL) → **2 falsos NO-PASS**
  (+cat012 debatible). "2º-juez+voto"=NO (laxo global, no toca el ±2 sampling); recalibrar-rubric-por-principio = real pero gated.

**NADA shippeado (plan MEDIDO, no delta de prod; eval-driven).** Sin cambio de código de prod (solo
instrumentos de medición + specs). 353 tests. **Recomendación:** gate-fix #49 SUBE (defecto latente
medido en prod, deploy-prep) · contrato #4 (build a ingesta) · rubric del juez (organic-eval ~sept).

### Antecedente s75 (DEC-057)

**s75 (DEC-057): audit-first de la raíz de identidad (DEC-054) = el detector tiene ~0 palanca eval real → DIFERIDO
a su gatillo (ingesta-30+), NO se construye como lever.** Alberto eligió medir antes de decidir build/defer/pivote.
El audit ($0, read-only, `scripts/s75_identity_audit.py` → `evals/s75_identity_audit.yaml`): **(1) palanca eval ≈0** —
de los 17 NO-PASS de retrieval (s71 track2), el detector toca SOLO cat013, y cat013 es gold de **CONDUCTA**
(`refuse-inference` cross-marca, verificado en `gold_answers_v1.yaml`) que el detector no arregla y podría EMPEORAR;
hp009/hp018 son **CONFIG** (e-series en `morley.yaml`, Brazo A ya construido), no el detector → confirma DEC-054
(identidad ⊥ inanición del pool) y refina hacia abajo el sub-claim "eval-medible cat013/hp009/hp018" de DEC-056(f).
**(2) escala = real pero ACOTADA, en proxies ruidosos** (no pisos): 78 etiquetas separador-aparente (sobre-cuenta:
`20/20I`), ≤114 docs mis-atribución (crudo 368 contaminado por códigos de manual que el catálogo MISMO heredó =
la circularidad que DEC-054 predijo), 18 clusters inconsistencia; concentrado en 3-4 marcas legacy (Notifier/Morley/Detnov).
**Dúo (sub-agente Opus + cross-model GPT-5.5, ronda FRESCA, 0 FP, fuerte convergencia):** confirma DIFERIR, corrige mi
FRAMING (sesgo #38/#39/#40: "≈0 medido/completo/BP" → honesto: 17/29 examinados, cat013=conducta, escala=proxy ruidoso,
falta freeze-contract). DIFERIR = gate/audit-primero funcionando (no construir aparato de 0 palanca antes del gatillo).
1 dúo, 0 FP. Rama `eval/s75-identity-audit` → PR.

### Antecedente s74 (DEC-056)

**s74 (DEC-056): Lever 1 BATCH (cluster de inanición del pool) CONSTRUIDO tras flags inertes + gate-0
judge-free = lift de retrieval REAL pero MODESTO → BANCADO (no shipped), A/B con juez DIFERIDO; el cuello
de retrieval se FRAGMENTÓ → siguiente = la RAÍZ DE DATOS, no más levers de retrieval.** Corrección de
arranque: el "ship `LEVER2_IDENTITY`" de s73 era **NO-OP en prod** (el `manufacturer-check` del handler
bloquea fabricante+pm-compuesto ANTES del retrieval; el eval lo bypasea = bias #40) → flag de vuelta a OFF.
**Build (353 tests, paridad probada, default OFF = prod inerte):** 2a `LEVER1_BROAD_FALLBACK` (broad-fallback
`5→effective_top_k`) · 2b `LEVER1_KEYWORD_ORDER` (keyword_search `order` determinista + limit 5→15; el dúo mató
el `order` por content_type del diag = over-fit) · 2c `RERANK_PREVIEW_CHARS` (preview reranker 800→2400).
**Gate-0 (factcov-sobre-top5, modal n=3 + firm-up n=7, ~$15, esquiva el ±2):** target 48%→67% @2400 PERO afinado
= **solo 2 golds fuertes+estables (hp008/hp002)** + 5 marginales (+1, dado-ruidosos) + **~3-4 regresiones**
(cat016, hp009, hp011-dado, **PASS-control cat022**). **2400 elegido por dato** (4000 peor; el CE Voyage lee su
propio 4000 → 4000 no aporta). **Decisión Alberto:** bancar tras flags (NO shippear — modesto + colateral + sin
usuarios + PASS sin medir); el A/B saldría casi seguro GRIS (±2 + dado). **Mapa de NO-PASS (workflow adversarial):**
29 NO-PASS = ~16 retrieval + 5 generación + 4 corpus-gap + 2 borderline + 1 diseño + 1 gold-injusto (cat012, único;
bias #20 verificado — el bot falla de verdad en 28/29). El cuello de retrieval **FRAGMENTADO** → no hay siguiente
lever de retrieval que valga (re-entra en la fase que DEC-051e cerró); cuellos vinculantes = el ±2 del ruler
(dual-judge = prerrequisito) + las raíces de datos del SWAP. 3 dúos + 2 workflows, 0 FP. Rama `eval/s74-lever1-batch` → PR.

### Antecedente s73 (DEC-054/055)

**Brazo A (identidad e-series) MEDIDO = FALLO→PARCIAL ×2 (GRIS, 0 regresión) → se shippeó `LEVER2_IDENTITY`
como tapón, PERO resultó NO-OP en prod** (el manufacturer-check del handler lo bloquea antes del retrieval; el
eval/smoke lo bypasean = bias #40 → corregido en s74, flag a OFF). **Identidad ESTRUCTURAL (DEC-054):** la raíz
es el detector LLM-en-ingesta (#49 refinado) — diseñado/anotado, construido al gatillo (ingesta 30+); config a
mano = tapón, NO "la identidad escala". Harness endurecido (`ab_verdict.py`+`s73_ab.py`, dúo 0 FP). 347 tests. DEC-054/055; HISTORY.

### Antecedente s72 (DEC-053)

**s72 (DEC-053): primer build de los fixes de retrieval (DEC-052) — Lever 2 (IDENTIDAD) tras
flags; Brazo A VERIFICADO end-to-end, Brazo B NO-OP hasta Lever 1.** Orden decidido con Alberto:
Lever 2 (identidad) ANTES que Lever 1 (profundidad del pool) = más barato/escalable/bajo riesgo.
**Brazo A** (alias-paraguas `model_aliases` + serie e-series en `series_registry`, flag
`LEVER2_IDENTITY`): **VERIFICADO contra corpus real** — el pool de hp009/hp018 se da la vuelta
(0→23/26 chunks reales ZX2e/ZX5e, espurio 22/26→0, +25 docs de serie MI-530) = **candidato a
ship; falta medir PASS** (eval-driven incompleto). **Brazo B** (rescate de pm mal-atribuido en
`_filter_to_query_models`, flag `LEVER2_PM_RESCUE`): correcto+seguro+testeado, pero **verify-first
= NO-OP para cat013** (los chunks SDX-751 no entran al pool [broad-fallback capado a 5] → el
rescate no recupera lo ausente → **bloqueado en Lever 1**). **3 rondas de dúo (incl. cross-model
GPT-5.5), 0 FP** — corrigieron el rumbo 3× (C roto/B-gate; paraguas-no-en-members; B-NO-OP =
`feedback_my_bias` operando). C (keyword-strip hp006) / D (section_path, TECH_DEBT #48 nuevo) /
cat001 DIFERIDOS. 330 tests; flags default OFF = prod inerte (paridad probada). DEC-053; HISTORY.

### Antecedente s71 (DEC-052)

**El re-análisis del residual (pedido por Alberto, escéptico del pivote s69)
= el cuello es RETRIEVAL, atacable con fixes concretos.** Dos tracks ortogonales con dúo
adversarial (workflows batched; rate-limits y apagones gestionados con resume). **Track 1
(audit del ruler, doble-escéptico auditor+defensor):** de 13 candidatos a "gold-injusto",
solo **cat012** sobrevive como maybe-PASS (debatible) — el guard anti-"trampas al solitario"
tumbó 4 que el auditor marcó injustos (cat009/cat011/cat019/cat020 = gold JUSTO, bot falló);
**el bot NO está infra-puntuado, escepticismo de Alberto validado**; 6 golds reclasificados
a retrieval-miss; 10 dudas para Alberto (`s71_track1_audit.yaml`). **Clasificación v2 de los
29 no-PASS** (`s71_classification_v2.yaml`): **16 RETRIEVAL-miss + 2 retrieval-family ≈ 18
(≈60%)** · 4 generación · 3 corpus-gap? · 2 borderline (bot ~correcto, PARCIAL conservador)
· 1 diseño (cat011 catálogo) · 1 gold-injusto (cat012). **Track 2 (diagnóstico de retrieval,
17 golds, 6 mecanismos, 16/17 fixable** — `s71_track2_retrieval_diag.yaml`): raíz común =
**INANICIÓN DEL POOL aguas arriba** — `keyword_search` limit=5 sin order (orden físico
arbitrario), broad-fallback vectorial capado a 5, reranker LLM lee solo `content[:800]` (el
hecho cae fuera). Fixes CONCRETOS y baratos (subir límites, order, ventana del reranker),
varios MEDIDOS end-to-end (hp003: preview 800→2400 → el reranker ya sirve el chunk correcto).
NO es el canal-broad (NO-GO s68). **El pivote-a-producto de s69 queda CORREGIDO: el residual
SÍ es lever-addressable — la conclusión "agotado" fue prematura (le faltaba este diagnóstico
quirúrgico per-gold).** DEC-052; HISTORY.

### Antecedente s69 (corregido por s71):

**s69 (DEC-051): A/B del lever de GENERACIÓN (completitud + guarda de fidelidad tras flag)
= NO-GO — y con él CIERRA la fase de levers-baratos del eval.** Tras el NO-GO del canal
(s68), el ciclo de generación completo: audit de resolución ($0 — el eval SÍ tiene
resolución) → **4 audits para fijar la diana** (el bias #20 reapareció en 2 capas: diana
inflada 12→8→5; el re-audit por relato-del-juez ERA bias #20, cerrado solo a
nivel-de-CONTENIDO: 4 sólida [cat008/cat020/hp005/hp014] + 1 recuperada [cat019]) → diseño
v3.2 con dúo r1+r2 + 2 cortes cross-model (enmiendas: **verificación content-level de los
flips decisivos** [bias #20 aplicado a la DECISIÓN], flag estricto, available_models como
SHIP-gate) → build tras flag `GENERATOR_PROMPT_VARIANT` (default base = prod inerte;
paridad a nivel-de-construcción $0 — no output-LLM que es no-determinista; suite 317) →
A/B (~$20): brazo `fidelity` (195 gen, 0 err, `assembled_sha` distinto = corrió de verdad)
vs `s67base` **re-juzgado en la misma tanda** (mata el drift del juez). **Resultado:
Δ_net=0 — NINGÚN gold de la diana flipeó a PASS; la predicción §4 FALSADA · +1 regresión
de conducta (cat011 clarify→answer, content-verificada) · verbosidad en 3 PASS-control.**
La **verificación content-level (enmienda B) PAGÓ**: el Δ=0 del juez solo habría dicho
"inerte", pero el prompt SÍ añadió completitud (hp014 metió FET=20 y el límite 32) sin
flipear modal Y rompió clarify en cat011 → cuadro real = efecto modesto + colateral, no
inercia. **Hallazgo del re-judge: ±2 de varianza del juez** (re-juzgar las MISMAS
respuestas base dio F 5→7). **NO-GO: flag default base (inerte); NO se salta a Opus**
(anti-racionalización §4 — el prompt-completitud falló, no es prueba de que la capacidad
sea el cuello). DEC-051; HISTORY. (s68 DEC-050 canal NO-GO; s67 DEC-048 CE ROLLBACK.)

**Lectura estratégica (la que define el rumbo de abajo):** 3 ciclos de lever barato, 3
negativos. El residual está **mapeado y desmenuzado** (corpus-gap diferido · within-doc-miss
· generación que el prompt no mueve · K-INESTABLE = ruido del juez) y **el ruler tiene ±2
de ruido** justo donde SHIP exige +2. Conclusión honesta: **la fase de exprimir-el-residual-
con-levers-baratos está agotada**; cada NO-GO costó ~$20-30 y evitó shippear ruido, pero el
valor marginal del siguiente micro-lever es bajo. Los unlocks reales son corpus (diferido a
demanda) y **eval orgánico (técnicos, ~sept)** — gated. El pivote: dejar de pulir el eval y
**preparar producto/deploy para cuando lleguen los técnicos**.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5; dispatcher `RERANKER_BACKEND` default `llm` — el swap a CE
Voyage se midió en A/B s67 = **ROLLBACK**, lever archivado con evidencia; el dispatcher
queda como instrumento) → generador `claude-sonnet-4-6` (temp=0,
`max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles; 25 huérfanos
residuales) / 1.170 docs {active 998 · superseded 3 · needs_review 79 · retired 90} / 31
marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035; **catálogo
de fabricantes 30 marcas** tras el backfill s65 + fix de paginación). **⚠️ Contratos rotos por
el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120,
default mantener); ventana de freeze del corpus: CERRADA (s64); fingerprint con dimensión
lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo, intacto en s69),
taxonomía CONGELADA (DEC-033), juez GPT-5.5 + K-mayoría. **Baseline VIGENTE = re-freeze
`s67base`** (12 jun 2026: 10/39 PASS-control · 5 unánimes · 4 K-INESTABLES; manifest
completo + `s67_embed_cache.json` como pin de embeddings); frozen-s58 = referencia
histórica muerta. Próximo freeze: correr SIEMPRE con `EMBED_CACHE_PATH` (DEC-048c).
**⚠️ Límite de resolución medido (s69): ±2 de varianza del juez** — re-juzgar las MISMAS
respuestas base dio F 5→7. SHIP exige Δ_net≥+2 = justo en el suelo de ruido → el ruler
actual NO distingue fiable un win de +1/+2. Endurecerlo (dual-judge, s47§D) sería
prerrequisito de MÁS lever-work; gated a "¿vale sin técnicos reales?" (lean: esperar al
eval orgánico).

## Qué sigue (s77 — builds estructurales GATED, priorizados por s76/DEC-058)

**s76 entregó el plan MEDIDO** (no delta de prod). Los 3 fixes estructurales, por orden, TODOS gated:

1. **Gate-fix #49 (deploy-prep) — ✅ CABLEADO s77 (DEC-059, PR #85).** Option D = fall-through
   manufacturer-aware (`telegram_bot.py:315`): si la marca está en DB → fall-through al RAG en vez de
   hard-refuse; refuse solo si la marca también está ausente. Raíz auditada = **familia↔variante** (no modelo
   ausente). Medido judge-free (reach≠PASS, CERO delta de eval — el harness bypasea el gate; corrección de
   PROD): 6/6 fall-through mejor que el falso-refuse, no-regresión del fallo opuesto, smoke por handler real
   10/10, 353 tests, dúo #7 0 FP. **PENDIENTE: que Alberto mergee el PR #85** (Railway despliega al merge).
   Los 3 mismatch (RP1r/Securiton-OEM) NO los arregla → contrato de identidad #49.
2. **Contrato de revisión/precedencia #4** — spec escrito (`evals/_s76_revision_contract_spec.md`); la única
   clase estructural que el lever-phase de retrieval NO tocó (cat009/cat024; cat008 es OEM-relabel→identidad).
   **Vía = backfill guardarraíl-eado s64-style** (sin re-ingestión ni DDL — verificado en DB: las columnas ya
   existen en `documents`, `revision_date` 1/1170 = gap del parser [el 70%], `document_family` filename-naive →
   re-derivar; el `_filter_by_document_status` de s64 ya consume `superseded`) → **candidato CERCANO, junto a #49**,
   NO gated a la ingesta lejana; la corrección de prod (no servir revisiones obsoletas) se valida judge-free; el
   win end-to-end en eval (2 golds < ±2) sí necesita el dual-judge.
3. **Rubric del juez (completitud-correcta ≠ contradicción)** — sesgo sistemático MEDIDO (cat019/cat020 =
   falsos NO-PASS, triple-confirmado). Recalibrar por-principio cuando haya algo que shippear que dependa de
   ello, o en el eval orgánico (~sept), con cross-model + held-out. NO "2º-juez-y-voto" (laxo global).

**Diferidos confirmados (sin cambio):** detector de identidad (DEC-054/057, a ingesta-30+); batch Lever 1
BANCADO tras flags (lift modesto + colateral cat022; el A/B espera al ruler que importe); categorías #44 (NO
backfill — filtro-EQ muerto DEC-040; si vuelve, BOOST en ingesta nunca filtro).

**Fases macro (rationale en HISTORY):** F1 calidad (levers de retrieval = rendimiento decreciente; el ±2 del
ruler es el techo) → **F2 escala (identidad de producto en ingesta = EL siguiente bloque)** → F3 routing/tool-use +
multi-dominio del scope M&A → F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** gate-fix #49 del handler (deploy-prep pre-sept — prod-reachability; sin usuarios no urge,
el eval no lo ve); **dual-judge** (s47 §D — prerrequisito si se mide algún win pequeño, DEC-051d); buckets
residuales de bajo-leverage en el ruler ruidoso (generación 5 [s69 NO-GO], corpus-gap 4, frontera/stamps,
cat016/cat007 [reranker no sube el chunk-en-pool], cat021 [variant-aware diversify], cat008 [generación pura]);
es-us (sin manuales US); contrato de ausencia formal (admit/refuse); prompt caching (umbral ≥50 queries/día);
language/revision_date masivos (contrato de ingesta); TECH_DEBT #40 (recall-gate CI)/#47/#48 (section_path);
**dureza de la tabla de decisión** (SOLO pre-registrado y motivado por evidencia, NUNCA post-hoc).
