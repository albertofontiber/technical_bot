# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El plan de acción único para llevar el Technical Bot
> desde su estado actual (3 fabricantes, en producción) hasta una solución
> alineada con best practices de Mayo 2026, escalable a 30+ fabricantes de PCI y
> usable por técnicos reales. Funde tres fuentes: la auditoría inicial, las
> recomendaciones de la calibración con Cowork (Opus 4.7), y los hallazgos
> empíricos de la Fase 0.
>
> **Audiencia.** Alberto (decisión estratégica) y cualquier sesión de desarrollo
> futura — debe poder leerse en frío y saber qué hacer y por qué.
>
> **Fecha base:** 22 mayo 2026. **Última actualización:** 8 jun 2026 (sesión 52) — ver "Estado actual y próximos pasos" justo debajo.
>
> **📍 Mapa canónico (un dueño por tema — para no repetir la inconsistencia de la s35).** ESTE
> documento es el **único canónico** del **roadmap + estado + qué sigue**. Los demás lo
> referencian, NO lo duplican: `docs/RULER_DESIGN.md` = diseño del ruler + decisiones D1-D11;
> `docs/DECISIONS.md` = el *por qué* de las decisiones de impacto med/alto; `TECH_DEBT.md` =
> deuda con triggers; `docs/ARCHITECTURE.md` = cómo funciona el sistema. Si el rumbo aparece
> en dos sitios y discrepan, **manda éste**.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best
> practice de Mayo 2026 con fuente identificable, (2) estructural — ataca la
> causa raíz, no el síntoma, (3) escalable a 30+ fabricantes sin fricción por
> fabricante. Si una propuesta no cumple los tres, se declara como gap honesto.
>
> **⚡ Estado actual y próximos pasos (sesión 30; ACTUALIZADO hasta s35 — ver al final de este bloque) — supersede el detalle de fases de abajo, que es rationale histórico (mayo 2026).**
> - **Ya hecho** vs el plan original: re-ingesta + `chunks_v2` en producción (Voyage 1024, sesión 27); catálogo dinámico + atribución de fabricante (sesión 28); eval determinista + matcher estricto (sesión 29); lever de **generación** ejecutado (sesión 30 — change-1 anti-falso-rechazo, **direccional**).
> - **Hallazgo que reordena el plan (sesión 30):** el **eval/gold (el «ruler») está parcialmente NO fiable** — errores factuales, conflictos entre manuales y OCR en ~7 de 19 golds → las cifras de calidad son **indicativas, no firmes** hasta arreglarlo. Detalle canónico en **`TECH_DEBT.md` #33** (no se duplica aquí).
> - **Orden de trabajo vigente:** (1) **arreglar el ruler** (gold-fix holístico; conflictos/matrices/OCR necesitan técnico real + PDFs renderizables — ver #33); (2) **filtrar chunks no-ES/EN** del retrieval (96 chunks fr/de/pt); (3) **lever del reranker** (elección empírica; el filtro modelo/categoría se queda como guarda de precisión). El reranker **NO antes del ruler** — medir contra golds rotos repite el error de llamar «trampa» a un win.
> - Cambios de sesión 30 en rama `feat/generation-lever` (NO en main). Log entre sesiones: memoria del proyecto.
>
> **Actualización s31-s33 (el ruler se está ARREGLANDO, no solo diagnosticando):**
> - **(s31)** ruler rediseñado como instrumento construido desde la FUENTE: `scripts/gold_store.py` (única puerta) + toolkit de verificación (`render_pdf_page` + cross-model GPT-5.5 `cross_verify_image` + `pdf_grep`) + **`docs/RULER_DESIGN.md`** (decisiones D1-D11, fuente canónica del diseño) + agente revisor adversarial (Protocolo 3).
> - **(s32)** **scorer atómico** por-hecho (`scripts/atomic_scorer.py`, 3 ejes: completitud mecánica + factual cross-model + conducta) reemplaza al juez LLM opaco; gate de alucinación caracterizado (`TECH_DEBT.md` #35).
> - **(s33)** **Fase 1 Tier A COMPLETO: 12/19 golds verificados** contra la fuente (hp001/02/03/05/07/08/10/11/14/17/19/20). **Matiz al hallazgo s30**: los `answer`-de-spec resultaron CORRECTOS; lo «no fiable» eran los golds de CONDUCTA (hp006/09/17) y CONFLICTO/OCR (hp012/18), hoy en cuarentena (7 restantes = Tier B conducta + Tier C diferido a técnico+PDF).
> - **Orden de trabajo actualizado (s33):** terminar Fase 1 (Tier B conducta → cuarentena a 0) → refinos del scorer (#35) → lever de generación re-evaluado contra el ruler ya fiable. **Sigue sin tocar producción** (eval-infra).
>
> **Actualización s34-s35 (1 jun 2026 — ESTE bloque es ahora la fuente canónica del estado):**
> - **(s34)** Ruler COMPLETO (**19/19** verificados). `change-1` re-validado y **REVERTIDO** de producción (`DECISIONS.md` DEC-001): no rescata falso-rechazos (son retrieval) e inducía sobre-respuesta en hp015. Producción = baseline limpio (chunks_v2 sin change-1); pendiente smoke en Telegram.
> - **(s35) Decisión de rumbo — el siguiente trabajo es CRECER EL RULER por cobertura-diagnóstica** (NO gate estadístico; `DECISIONS.md` DEC-003): breadth-baseline FIJO (eje fabricante/tipo/modalidad/idioma; 5 conductas + multi-marca-parcial = guarda anti-regresión) + golds lever-targeted ENCIMA; parada = cobertura de TAXONOMÍA, no un N. El sub-plan detallado del ruler (fases, INTERLEAVE) vive en `RULER_DESIGN §4`.
> - **Orden vigente:** (1) auditar 13 PARCIAL/5 FALLO (¿retrieval vs síntesis?) → (2) crecer baseline + lever-targeted → (3) tirar del lever que señale → medir → repetir. **Tarea próxima elevada:** metadata de revisión en chunks_v2 (`TECH_DEBT #4`, DEC-004). El reranker sigue **ABIERTO** (no asumido).
> - Supera el framing s30 "el ruler está roto / arreglarlo antes del reranker": el ruler ya está completo y fiable.
>
> **Actualización s36 (1 jun 2026 — paso (1) del orden vigente HECHO):**
> - **Auditoría DEC-003 ejecutada** (embudo retrieval HyDE-off por hecho atómico; instrumento
>   `scripts/audit_retrieval_funnel.py`, datos `evals/dec003_retrieval_funnel_*.yaml`; 2 revisiones
>   adversariales 5/5 + 7/7). **Hallazgo: el cuello está REPARTIDO, no es único** (`DECISIONS.md`
>   DEC-005). Los 5 FALLO = **4 retrieval-funnel** (hp006/17/18/19: el dato no llega al top-5) **+ 1
>   síntesis** (hp020: lo tenía y sobre-admitió). Las PARCIAL son mezcla (varias con el dato en top-5
>   = síntesis-incompleta). **0 corpus-gaps reales** → extracción (#10) NO es el lever.
> - **Lever (tras 2 reviews adversariales + validación — el framing inicial se corrigió 3×; traza
>   completa en DEC-005):** el "clúster manual-equivocado" era over-generalizado → validado **n=1**
>   (solo hp017 no trae el manual al pool, por `product_model` mal etiquetado `AC-220` + el **bug de
>   merge de scores PLANOS de s29** que entierra la similitud vectorial real; HyDE-ON no lo mitiga —
>   caveat HyDE CERRADO). **El cuello dominante es within-doc chunk-ranking** (manual correcto en el
>   pool, el chunk de la respuesta no llega al top-5); hp006 es recall-miss de página (ni en vector
>   top-50). **doc-routing/`doc_type` DESCARTADO.**
> - **RESOLUCIÓN del lever (4ª review — `DECISIONS.md` DEC-005): la síntesis RRF se RETRACTÓ.** Verificado
>   que **RRF ya se construyó y midió (`gate.py`/`gate_results.json`, PR#8): hit@5 idéntico vec vs
>   hybrid-RRF, NO movió** (sobre gold roto + proxy de recall). **Propuse 4 mecanismos de lever esta
>   sesión (change-1→doc-routing→fail-open→RRF) y los 4 cayeron** por review+verificación — el bucle viene
>   de debatir levers sobre PROXIES en vez del árbitro end-to-end. **NO hay lever de retrieval recomendado.**
> - **Próximo (lo que SÍ se sostiene):** (a) la **diagnosis está HECHA** (no más mecanismos a ciegas);
>   (b) **ejecutar el paso ya aprobado de DEC-003: crecer el ruler + medir END-TO-END** (única vía para
>   volver falsable cualquier lever); (c) fix seguro pase lo que pase: `product_model='AC-220'` del
>   Config-ES de la PEARL (bug B5, n=1); (d) opcional barato: re-correr `gate.py` sobre el ruler arreglado
>   (sigue siendo proxy). Instrumentos: `audit_retrieval_funnel.py`, `validate_s29_burial.py`.
>
> **Actualización s37 (1 jun 2026 — paso (b) de s36 HECHO: medido END-TO-END):**
> - **Árbitro end-to-end corrido sobre los 19 por primera vez** (`test_bot_vs_gold.py` genera respuestas →
>   `atomic_scorer.py --llm`, 3 ejes, HyDE-off, `chunks_v2`, metadata de prod ACTUAL). Baseline: **8 FALLO /
>   10 PARCIAL / 1 REVISAR / 0 PASS** (0 PASS = alarma fuerte, no conteo definitivo — la prosa-frágil degrada
>   PASS→PARCIAL, #35). **Consistente con DEC-005 a nivel end-to-end** (no solo funnel): over-admit/clarify donde
>   el dato está enterrado (hp017 AC-220, hp019, hp018) + síntesis/contradicción (hp005 matriz, hp011, hp013).
>   `DECISIONS.md` DEC-006.
> - **Scorer ajustado (Protocolo 3 dual SÓLIDO)**: answer-con-conflicto delega el surfaceo a COMPLETITUD
>   (hp012 limpio); discriminador **hedged-admit** (p>0 = parcial con hedge, no admit real → 3 falsos-FALLO
>   hp001/14/15 corregidos, conserva over-admit reales hp017/19); **refuse-inference EXCLUIDO de ANSWER_LIKE**
>   (cae a REVISAR) hasta su check dedicado (el eje factual contradicción-only no caza inferencia indebida).
> - **Límites del árbitro (fiable para señal CATEGÓRICA, aún no deltas finos)**: prosa-frágil deflacta
>   completitud → los PARCIAL son un SUELO (TECH_DEBT #35) + eje factual no-determinista (TECH_DEBT #37).
>   Coherente con RULER_DESIGN §0 (diagnóstico, no gate estadístico).
> - **Próximo (DEC-003 capa 1)**: crecer el breadth-baseline (admit/refuse-inference/clarify + eje
>   fabricante/ES-EN) sobre esta base; fix `product_model='AC-220'` (prod, contrato de seguridad) re-medido
>   como delta vs este baseline; endurecer completitud-prosa (#35) para leer deltas finos.
>
> **Actualización s38 (1 jun 2026):**
> - **(1) Dos fixes de prod shippeados** (PR #24, `DECISIONS.md` DEC-007): relabel `product_model
>   AC-220→Pearl` (Manual Config-ES de la PEARL; hp017 pool 0→9 chunks, **FALLO→responde**) + **filtro de
>   idioma** en retrieval (~96 chunks no-ES/EN; 243 tests + smoke). **El baseline s37 queda SUPERSEDED** (prod
>   cambió) → cualquier delta futuro se mide contra un baseline FRESCO sobre el catálogo crecido.
> - **(2) `TECH_DEBT #38`**: retirar el pipeline `src/ingestion/` VIEJO (legacy desde el SWAP a chunks_v2; el
>   bot vivo no lo usa; `re_ingest`/`run_ingestion` escriben en la tabla `chunks` muerta). Workstream aparte.
> - **(3) Dirección aprobada (DEC-008)**: crecer el ruler = **catálogo diagnóstico SINTÉTICO 3-bandas**
>   (Claude + GPT-5.5 co-generan source-verified; dúo critica), instrumento para localizar dónde falla la
>   cadena. Plan maestro canónico: **`docs/CATALOG_PLAN.md`** (v4, tras 3 pasadas del dúo). Ejecución por
>   frontera de supervisión: **noche autónoma** = construir #35; **mañana supervisado** = pipeline de autoría +
>   autorar ~6-8 + diagnóstico end-to-end.
> - **(4) Ejecutado (noche + mañana s38):** **Fase A HECHA** — #35 juez-LLM de completitud de prosa
>   (`atomic_scorer.py --prose-llm`, default OFF, test de equivalencia; evidencia cruda en `evals/phaseA_35_*`).
>   **B1 FIRMADO** por Alberto (los rescates de prosa = paráfrasis correctas; 1 a vigilar: hp007 'cada 2 años').
>   **C4 (cross-check de localización) DISEÑADO + reconciliado**: el dúo eliminó la **ruta semántica** (circular —
>   rankea el sustrato del bot) → C4 = grep multi-manual + mapeo producto→manuales + render±1 + **doble-señal AND**,
>   **localización ROBUSTA, no budget-bounded** (decisión Alberto: definir bien los golds manda sobre el coste). El
>   diseño durable vive en **`RULER_DESIGN §2`**; `CATALOG_PLAN` (marcado TRANSITORIO) lo referencia, no lo duplica.
> **Actualización s39 (2 jun 2026) — `DECISIONS.md` DEC-010:**
> - **C4 CONSTRUIDO** (`scripts/locate_fact.py`) + **`cross_generate.py`** (co-gen GPT-5.5). producto→manuales =
>   **opción D** (autor explícito `--manuals` + sugeridor filesystem; NO `product_model`, sucio) tras el dúo tumbar
>   mi "B-síntesis" (NO escala: 2/23 fabricantes con carpeta; `_Privado` no es dedup). Contratos refuse/admit DIFERIDOS.
> - **Piloto autorado: `cat001` (PEARL multi-doc), `cat005` (Fidegas CS4, gas, dominio nuevo), `cat007` (FAAST
>   LT-200, eje ES/EN)** por el proceso C4→co-gen→doble-lectura→poda→dúo C3→regla C→`gold_store.upsert` (**22 golds, 0
>   errores**). El test ciego de C4 (hp017/05/12) cerró el "test ciego del localizador" pendiente + cazó 6 bugs (4 de
>   C4 + 2 de autoría), todos arreglados.
> - **1er DIAGNÓSTICO end-to-end sobre el ruler crecido** (HyDE-off, chunks_v2, `atomic_scorer` mecánico): **3 PARCIAL,
>   0 alucinación**. **cat005 5/6 y cat007 4/5 = fuertes** (bot maneja dominio nuevo + retrieval cross-variante);
>   **cat001 2/7 = SÍNTESIS INCOMPLETA real** (omite los hechos cross-doc duros — conflicto 40-CLIP, 0,75 A, 99+99
>   CLIP, 255/8192 — y deriva a detalle tangencial; retrieval ✓, 0 alucinación). **El cuello multi-doc = completitud
>   de SÍNTESIS (consistente con DEC-005/006), no retrieval ni alucinación.** El ruler crecido DISCRIMINA = instrumento válido.
> - **Caveat (DEC-006):** corrido sin `--prose-llm` → PARCIAL = SUELO (matcher-prosa frágil under-cuenta; la
>   incompletitud de cat001 es real, verificada a mano).
> - **Próximo (s40):** crecer el catálogo (Tier B gap-diagnóstico 12/14/15 + conductas 16/18/19 con contratos
>   refuse/admit) + endurecer `atomic_scorer --prose-llm` para deltas finos. Rama `eval/s38-night-catalog`; **PR a
>   `main` cuando cierre el lote** (lleva C4 + cross_generate + #35 + los golds del catálogo).
> **Actualización s40 (2 jun 2026) — `DECISIONS.md` DEC-011 (CONSOLIDACIÓN del árbitro; sin crecer golds, foco elegido por Alberto):**
> - **Fix RAÍZ del matcher de RANGOS** (`strict_match.distinctive`, `(?<!\d)` antes del signo): `distinctive("110-230")` daba
>   `-230` (guion de rango leído como signo) → falso-miss en `_anchor_present`/`_value_on_page`. **Era la causa REAL del
>   "cat005 PARCIAL=suelo" de DEC-010, NO la prosa.** → **cat005 5/6→6/6 PASS**; los 19 golds IDÉNTICOS (A/B mecánico = cero
>   regresión); 249 tests (+6 nuevos `tests/test_strict_match.py`).
> - **`--prose-llm` (#35) NO se endurece**: el cabo de B1 (hp007 'cada 2 años') está CERRADO = NO over-credit (el bot dice
>   "bienal"/"trimestral" literal). Conservador en los casos ejercidos (cat007 'no enclavado' NO se rescata; n pequeño).
> - **Diagnóstico autoritativo del piloto post-fix**: cat005 **PASS 6/6**, cat007 4/5 (miss real), cat001 2/7 (omisión real de
>   anchors cross-doc; 0 contradicciones → omisión, no error; la causa síntesis-vs-retrieval es del funnel s39, no re-verificada).
>   Efecto colateral declarado: la relajación de sumas-sin-espacios afecta el matcher compartido (1/134 hechos = solo cat001,
>   impacto actual 0). **Protocolo 3 dual**: sub-agente SÓLIDO 9/9 + cross-model 5/5 (todos FRAMING), 0 FP.
> - **Próximo (s41)**: crecer el catálogo (Tier B 12/14/15 + conductas 16/18/19 + contratos refuse/admit) sobre el árbitro
>   consolidado; opcional, baseline FRESCO de los 19 post-AC220.
> **Actualización s41 (2 jun 2026) — `DECISIONS.md` DEC-012 (eje NO-FABRICACIÓN del árbitro):**
> - **Alcance ELEGIDO por Alberto: CERRAR el árbitro endurecido** (autoría de celdas → s42). Al especificar los
>   contratos refuse/admit (diferidos en s39) el dúo destapó un agujero del scorer: el eje factual es solo-CONTRADICCIÓN
>   → un bot que FABRICA sobre el vacío (corpus sin el dato) no contradice nada y no se cazaba.
> - **Cableado (eval-only, no toca prod)**: (1) **C1** — `score_gold` ramifica por `estado`-del-hecho (los
>   `ausente-probado` salen de completitud y alimentan el eje nuevo; cubre el answer MIXTO D5 — hp006/09/13 —, no solo
>   admit/refuse); (2) eje **NO-FABRICACIÓN** (`undue_inference_check`, cross-model GPT-5.5, gated `--llm`, conservador):
>   afirmar un hecho ausente-probado = FALLO (asimetría de seguridad); (3) **refuse-inference entra en `ANSWER_LIKE`**
>   (deja de caer a REVISAR). Decisión §6 = check-LLM por FALSABILIDAD (voto del dúo), con fallback humano si el spot-check no valida.
> - **Re-baseline FRESCO post-AC220** (HyDE-off, `--llm --prose-llm`, cierra el gap (a) de DEC-011): **7 FALLO / 10
>   PARCIAL / 2 REVISAR / 0 PASS** (19; vs s37 8/10/1/0 — AC-220 sacó hp017 de FALLO, el eje no-fabricación metió hp006).
>   El eje FUNCIONA (hp006 fabrica un procedimiento de localización no documentado); el filtro factual mejoró hp013.
>   **261 tests** (+8 `tests/test_atomic_scorer.py`, incl. casos cruzados error+FALLO).
> - **Protocolo 3 dual × 2 RONDAS (22 findings / 22 confirmados / 0 FP)**: R1 diseño (3 críticos: el scorer ignoraba
>   `estado`; modo-ausencia greenfield; `_ECOSYSTEM_OF` colapsa Detnov↔Securiton por OEM → contrato B exige ecosistemas
>   DISJUNTOS); R2 diff (**bug CRÍTICO de orden** del veredicto enmascaraba un FALLO si el otro eje daba error →
>   ARREGLADO; + refuse offline sin red; + ausente-probado-con-valor iría al factual). Todos aplicados.
> - **Gaps**: el eje no-fabricación es estructuralmente más frágil que el factual (sin ancla de valor) → señal
>   CATEGÓRICA, spot-check humano; **FP en hp006** por hecho `ausente-probado` mal formulado (mezcla ausente+contexto
>   cubierto) → deuda re-formular + lección de autoría; recall/especificidad del check NO validados sobre golds de
>   conducta reales (n=0).
> - **s42 HECHO — #37 CERRADO, baseline LEGIBLE (`DECISIONS.md` DEC-015):** (1) `TECH_DEBT #37` resuelto =
>   **response_format** (mata el ruido de formato, 0 error→REVISAR) + **mayoría+flag** (mata el de sampling) +
>   spot-check humano del residual; temp/seed MUERTOS (gpt-5.5 sin knob de determinismo, testeado); la cirugía de
>   prompt (cláusula (d)) se intentó y se **REVIRTIÓ** (2 rondas de dúo: scope creep + hueco echo-and-deny +
>   pushback de Alberto) → `_FACTUAL_SYS` idéntico a pre-s42. (2) **diagnóstico ESTABLE del bulto** entregado:
>   baseline 22 golds K=12 = **7 FALLO estables** (hp005/06/08/09/11/13/19 — el "7 FALLO" de s41 CONFIRMADO
>   no-ruido) / 12 PARCIAL (4 a review: hp001/02/10/20) / 1 PASS / 2 REVISAR; **18/22 estables**
>   (`evals/factual_variance_baseline.json`).
> - **Próximo (s43):** **(3) tirar del lever de mayor señal sobre el bulto** (concreto TBD tras el diagnóstico, NO
>   presupuesto), medido vs ESTE baseline legible (INTERLEAVE: mejora de PRODUCTO, sin hacer desde s34). Spot-check
>   humano de los 4 REVIEW antes de anclar un lever en ellos (hp010 es un 6-6). Smoke barato del eje no-fabricación
>   (#19 + 1 #18 disjunto) intercalable. **DESCARTADO** (DEC-013, sigue): modo-ausencia ambicioso + #16 admit.
>   Re-formular hp006 se mantiene.
>
> **Actualización s43 (3 jun 2026) — `DECISIONS.md` DEC-016 (ZOOM-OUT estratégico; Alberto cuestionó el ritmo):**
> - **Diagnóstico de fundamentos (4 agentes paralelos + verificación):** `chunks_v2` = LlamaParse multimodal EJECUTADO + contenido ~99% sano → **SALVAGE, NO rebuild** (overhaul rechazado con evidencia; las guardas verificadas son la atadura real, no el legacy; core cruft ~5-8%; `catalog.json` ya escala a 30+).
> - **Lever de retrieval (reranker Voyage) MEDIDO end-to-end y DESCARTADO (CONDICIONAL):** el funnel (+2 proxy) NO predijo el end-to-end; juez-inline = empate-con-churn, árbitro single-pass = dentro del ruido de #37 → no se shipea. **Condicional (Amdahl):** re-test tras síntesis.
> - **HALLAZGO DOMINANTE: el cuello del bulto es SÍNTESIS/GENERACIÓN** (con el chunk en top-5 el bot contradice/omite/sobre-admite) — confirma DEC-005/006/s39 a nivel de VEREDICTO. **s44 = Track D (lever de síntesis)**, medido con K-mayoría (el single-pass es ruidoso).
> - **A2 (fusión de scores planos s29) = higiene COMPROMETIDA** (no lever): quitar cruft recurrente; vara = no-regresión; P3; vigilar boosts load-bearing de diagrama/wiring.
> - **Track C (`#38`) HECHO**: 24 ficheros v1 fuera, 176 tests verdes (PR #32 MERGEADO). **Track B**: drafts Spectrex (llama, dominio nuevo) + scoping de conductas, **sin upsert** (pendiente co-gen + dúo C3 + sign-off).
> - **CORRECCIÓN + PLAN s44 (tras el dúo del PLAN — `DECISIONS.md` DEC-016 CORRECCIÓN):** el funnel desmiente "síntesis dominante" → cuello **MIXTO, RETRIEVAL-PESADO** (RETRIEVAL 12/4 ≥ SÍNTESIS 7/3; hp008 mixto, hp019/09 = retrieval). Síntesis = UN cuello material, no el dominante. **A2 PROMOVIDO de higiene a lever a testear.** **Plan s44:** (0) spot-check 4 REVIEW (hp001/02/10/20) + hp006 [Alberto adjudica, material preparado] + corregir DEC-016 ✓; **(1a) dimensionar el burial BARATO** (re-estampar sims vectoriales reales en los flat-paths → re-correr SOLO el funnel sobre los 7 FALLO, ~1h → separa burial-A2-addressable vs recall-miss); **(1b)** si mueve → fusión principiada (P3 + guardas-duras-vs-heurísticas declaradas + sensitivity, **#2 DESBUNDLEADO**), medir K-mayoría; **(2) síntesis (Track D)** sobre lo que quede del bulto. **Safety-debt NOMBRADA** (no "diferida por eval-ciego"): #1 latest-wins + #2 flowchart-as-fact. Diferidos: #3 (escala/ingesta), Track B promote, TIER3/confidence.
> - **CIERRE s43 (`DECISIONS.md` DEC-017):** gold-fixes hp002/hp006 **APLICADOS** (spot-check humano de Alberto contra fuente + dual review; corrigen 2 FP del árbitro por **precisión del gold**, sin tocar los ejes). hp002→**PASS** confirmado; hp006→**PARCIAL** (recall-miss; eje no-fab post-fix pendiente del re-baseline s44 por API GPT-5.5 flaky al cierre). **Bulto LIMPIO = 8 FALLO confirmados** (`hp001/05/08/09/11/13/19/20`; el spot-check **CLARIFICÓ**: −1 FP [hp006] +2 confirmados-reales [hp001/hp020] — más FIABLE, ~mismo tamaño). **s44 PASO 1 = re-baseline K-mayoría** (confirma hp006 + el bulto) → A2 (reranker Voyage default + fusión calibrada, dimensionado por (1a)/(2)) + síntesis. Learnings escalables y los 5 over-claims de framing de la sesión (todos cazados por el proceso) en DEC-017 + `feedback_my_bias #18`.
> - **s44 EN CURSO (4 jun 2026 — re-rumbo tras el dúo; `DECISIONS.md` DEC-018 al cierre):** PR#34 MERGEADO. **(a) Aclaración "A2"** (verificado git — ver `TECH_DEBT #32`): A2-fusión (constantes planas del retriever, **NO tocadas, vivas en `origin/main`**) ≠ A2-extracción (LlamaParse `src/reingest/`, conservada) ≠ ingesta-v1 (`#38`, borrada s43). **(b) El dúo tumbó "A2-first como build-RRF"** (cross-model GPT + sub-agente, verificado en código): la dimensión (1a) se midió **HyDE-OFF** pero producción corre **HyDE-ON** (`hyde.py:39` default, sin override commiteado — Railway pendiente) → atribución burial/síntesis de s43 **NO reconciliada con el path real**; `RETRIEVAL_TOP_K=15` → re-estampar sobre `merged` alcanza ~2/6 hechos (16-50 exigen ensanchar fetch); per-hecho ≠ per-pregunta (solo el árbitro end-to-end lo zanja). **(c) Reframe (instinto de Alberto):** A2-fusión = **BORRAR el cruft de scores planos s29 + rankear por coseno Voyage real** (conservar guardas: filtros modelo/categoría [#32 §1241] + ruta diagrama + match exacto), NO construir fusión. **Plan corregido:** (0) reconciliar base = confirmar HyDE en Railway + **A/B HyDE on-vs-off en chunks_v2** (en s29/corpus viejo se midió no-ayuda + rompe-determinismo #32:1250 → si se confirma en chunks_v2, OFF tras flag = base determinista); (1) **borrar cruft + ensanchar fetch**, P3 + A/B K-mayoría no-regresión (check diagrama); (2) **síntesis Track D** (hp020/hp001 over-admit) en paralelo. Bot SIN usuarios → borrar libre + medir delta.
> - **RESULTADO s44 (5 jun 2026 — `DECISIONS.md` DEC-018, SHIPPED):** el lever NO fue borrar-cruft NI síntesis — fue **`#16` retrieve-wide** (`RETRIEVAL_TOP_K` 15→50, RERANK_TOP_K=5 sin cambio). El burial era el **CORTE `merged[:15]`** (no el reranker, que rankea por contenido); el pool ancho deja sobrevivir + el reranker sube. **A/B K=3 HyDE-off: FALLO ~6→1 estable** (wide 1/1/1; base 5/6/7), **7 mejoras / 1 regresión** (hp013 completitud). Residual = **hp006** (recall-miss, corpus aparte). **Los "casos síntesis" (hp019/20/01) MEJORARON con retrieval → eran retrieval-contexto** → **Track D (síntesis) y borrar-cruft (#32) DEPRIORIZADOS** por medición. **SHIPPED** (PR `feat/s44-retrieve-wide`, 176 tests + smoke 6/6; Protocolo 3 SÓLIDO + nota latencia rerank). **Pendiente desbundleado: HyDE-off** (default commiteado + Railway override + confirmación @50; medí HyDE-off, bot despliega HyDE-on). **Frontera siguiente = 14 PARCIAL** (completitud). Vindica el instinto de Alberto (el lever más barato —un constante— ganó sobre 2 sesiones de plan de build).
> - **PRÓXIMO s45 (framing reconciliado con estas Fases + validado por dúo NO-SÓLIDO→CORREGIDO; brief en `evals/_s45_framing_brief.md`):** seguimos en **Fase 1** (calidad). retrieve-wide cerró casi-todo FALLO; **residual F1 = ~1 FALLO (hp006, recall-miss de corpus) + 14 PARCIAL** (con caveat SUELO-de-medición #35/DEC-006). s45 = **GATE PURO, sin pre-suponer lever** (el dúo cazó que pre-supuse "síntesis" — el lever que s44 deprioritizó POR MEDICIÓN, citando diagnosis pre-s44): **(0)** cerrar el gap de atribución DEC-018(f) = re-medir **HyDE on-vs-off EN el path retrieve-wide** (la medición s29 NO transfiere) + A/B de **cap-rerank** contra las ganancias de s44 (no re-enterrar chunks rank-30-50 multi-doc; necesita el override de Railway de Alberto). **(1)** triage de los 14 PARCIAL con `--prose-llm` **ANCLADO EN FUENTE** (spot-check vs manual, anti-circularidad — si no, es "ablandar el evaluador hasta que el residual desaparezca"): clasifica suelo-medición / retrieval-residual / recall-miss / síntesis-genuina (cat001-tipo). **(2)** atacar el residual REAL dominante que diga el triage, **definido ESTRUCTURALMENTE** (packing / evidence-planning / fusión cross-doc / citas obligatorias), NO "lever de síntesis" abstracto; A/B K-mayoría DOS EJES (completitud↑ SIN invención↑, DEC-001). **hp006 = item propio** (corpus / term-exacto / BM25), atacar o diferir-con-razón — NO bundleado con completitud. **Track B** (breadth del eval: Spectrex/conductas) interleave CON umbral anti-regresión. **F2 (escala-prep) NO se adelanta** (orden canónico F1→F2 §660). **La pregunta estrecha:** *"con `--prose-llm` anclado-en-fuente, ¿cuántos de los 14 PARCIAL son cuello REAL vs suelo, y cuál es el mecanismo dominante de los reales?"* → el lever SALE de ahí, no antes. Dúo: `adversarial_review_log` 2026-06-05 (GPT + sub-agente, NO-SÓLIDO, 2 conflaciones cazadas = 2º over-frame de la sesión, `feedback_my_bias`).
> - **RESULTADO s45 (5 jun 2026 — `DECISIONS.md` DEC-019):** **GATE: F1 NO tiene lever de calidad limpio dominante.** El triage source-anchored (funnel @ **pool-50** + `--dump` per-caso = el ÁRBITRO vs el proxy grueso) mostró que la "síntesis domina" del funnel es **artefacto parcial**: el matcher `_chunk_has` (`all(a in nc)`, SIN frontera-dígito) cuenta "99"∈"990"/"1993"; y el bucket SÍNTESIS cuenta hechos-en-top5 **sin mirar si el bot los omitió** → infla (los PASS tenían SÍNTESIS alto). De los 4 candidatos de síntesis fuerte: **2 genuinos (hp001 clave 2222 en top-5 omitida; cat001 159+159), 2 NO (hp008 = retrieval-miss de modelos 551; hp012 = artefacto del matcher)**. Síntesis-genuina ≈ **2-4 casos dispersos, NO cuello dominante**. Sumado: recall no convierte (`TECH_DEBT:1246`), contexto-width muerto (RERANK-MISS marginal), FALLO peligrosos cerrados (retrieve-wide), y **3 levers muertos esta sesión** (L1-contexto, síntesis/L2, foundations-bundle) — **TODOS pre-supuestos, cazados por el dúo ANTES de cablear**. **Cierra DEC-018(f):** adoptar **HyDE-OFF** (= el path validado de s44; determinismo; s29 no transfiere → re-medir on/off@50 segmentado). **Plan corregido (DEC-019), barato-primero · audit-como-gate · comportamiento-sólo-si-el-gate-lo-pide:** **Fase 0** higiene sí-o-sí (estampar config en el eval + frontera-dígito en el matcher + borrar one-offs muertos + HyDE-off@50 + externalizar `CATEGORY_TERMS` + recall@k como gate CI) → **Fase 1 = EL GATE** (audit de los 14 source-anchored, clasificar {suelo/retrieval-residual/recall-miss/síntesis-genuina} y **PARAR al clasificar** — decide lever, no ratifica uno elegido) → **Fase 2** comportamiento SÓLO si el gate lo pide (Voyage reranker / contextual-retrieval = A/B feature-flag midiendo **regresión-diagramas** explícita; cruft = ya descartado s44, es sort-key no inerte) → **Fase 3 = F2** (catálogo de modelos YA hecho/catalog-first `retriever.py:101`; pendiente real = `CATEGORY_TERMS` a datos + contrato identidad-producto/conflictos ES-EN/OEM/España-vs-US + test **matriz-dificultad**, no held-out binario). **Dúo s45 (3 cross-model + 4 sub-agente, TODOS NO-SÓLIDA→corregido):** cazó **6 over-frames míos** = `feedback_my_bias` **reincidente** (pre-suponer lever antes del gate, 3×; ancla FALSA "reranker = fuente del ruido" cuando corre `temperature=0` `reranker.py:112` y el ruido es el juez holístico + generación). El proceso (medir + dúo + instinto-Alberto) los frenó ANTES de tocar prod. Refs: `adversarial_review_log` 2026-06-05; `evals/_s45_*` (funnel, proposals, triage dumps).
> - **RESULTADO s46 (6 jun 2026 — `DECISIONS.md` DEC-020):** **F0 higiene SHIPPED (4/6; 2 diferidos) + F1 GATE → F2 = medir contextual-retrieval.** **F0:** frontera-dígito canónica `anchor_present` (centraliza+dedup, `TECH_DEBT #39`) + config estampada en el gate (`{meta,results}`) + HyDE-off default (`hyde.py:39`, cierra DEC-018f) + borrados one-offs `_s44_*`; **diferidos** recall@k-gate (`TECH_DEBT #40`, CI offline) + CATEGORY_TERMS (→F3). 179 tests, 5 commits, PR pendiente. **F1 GATE source-anchored (matcher arreglado): SÍNTESIS MUERTA** — 0 síntesis-genuina fuerte (el fix del matcher reclasificó las "2-4 síntesis" de DEC-019 como artefacto del substring crudo 99∈990). **Mi over-frame F2-retrieval lo cazó el sub-agente** (12/16 sin fuerte-retrieval; hp008=catálogo→F3; recall-no-convierte por precisión/generación) y **el cross-model rompió el echo-chamber Claude**: `:1246` (top-k/RRF/rerank/dense medidos-no-convierten) NO descarta **contextual-retrieval** (cimiento BP NO-medido). **Decisión Alberto: F2 = medir contextual-retrieval** (A/B slice, conversión de veredictos; gaps: prior negativo `:1246`, juez ruidoso `#35`, filtros `:1250`). Dúo = sub-agente×2 + cross-model (`adversarial_review_log` 2026-06-06). `feedback_my_bias` reincidente (over-frame F2), cazado ANTES de cablear (0 código de prod en F1).
> - **RESULTADO s47 (en curso — 6 jun 2026, `DECISIONS.md` DEC-021): revisión estructural → criterios de EXCELENCIA + base escalable LOCKED (v4).** Antes de construir el experimento, Alberto cuestionó el rumbo (tamaño del eval, BP, PARCIAL, orquestación) → rediseño: **§A DoD = EXCELENCIA** (completitud de `core` soportado-por-corpus) **+ seguridad, NO solo no-daño**; **§B** ship-criterion (+ zona gris: mejor-mecanismo sin delta shipea si estructural/escala+sin-complejidad+no-regresión); **§C** expandir eval **~60-100** (reabre DEC-003 "no-N": held-out + señal, NO CI) con split **dev/held-out** + embargo; **§D** ruido del juez = **MEDIR-PRIMERO** (correr 2 jueces sobre las 22 → decide si construir dual-judge; juez único CONGELADO para el 1er A/B); **§E** identidad-producto = **SHRINK** (ya existe: `catalog.py` data-driven + `metadata.py` identidad-en-ingesta; queda ecosistema + admit-on-empty + seam ASD — F3-traído-adelante + apuesta anticipatoria declarada); **§F** freeze-contract = **run-manifest**. Dúo formalizado (`.claude/agents/adversarial-reviewer` + briefing; **piloto cross-model-con-fuentes VALIDADO**). 2 rondas, ~21 hallazgos confirmados 0 FP, 3 over-claims míos "ya-existe" cazados (`feedback_my_bias`). **PRÓXIMO = CONSTRUIR:** run-manifest + expandir eval (autoría industrializada, paralelo-seguro, no toca índice) + **A/B contextual-retrieval** sobre el eval grande (juez congelado). **§D ya RESUELTO (s47, medir-primero K=5 → DIFERIR el dual-judge:** Claude over-strict 5/22, GPT 0 catches únicos; juez único GPT-5.5 + K-mayoría; `scripts/judge_kruns.py`). Secuencia respeta freeze-contract. **s47 se cerró en milestone (criterios v4 + §D); el BUILD del lever (§A wiring + expandir eval + A/B) → s48.** Pendiente §H: consolidar este bloque de estado (numeración Fase 0-5 vs F0-F3 + log a fichero historia).
> - **RESULTADO s48 (6-7 jun 2026 — `DECISIONS.md` DEC-022): el "BUILD del lever F2" destapó que el cimiento YA existía → premisa corregida + diagnóstico de retrieval CERRADO con datos + lever de generación smoke-débil DIFERIDO.** El **reconocimiento del código barato-primero (ANTES de construir)** reveló que **contextual-retrieval (Anthropic sept-2024) YA está implementado y activo al 100%** (`chunks_v2` 22.849/22.849 con blurb B7 `context+content` embebido; `contextualize.py`+`embed.py:55`; verificado en código + BD prod) → la premisa "F2 = medir el cimiento **OMITIDO**" (DEC-020e, arrastrada s45-47) era falsa en el "omitido/construir"; el **"no-medido" (delta e2e) sigue** (el blurb entra al retrieval, NO a la generación: `generator.py:411` solo `content`; reranker tampoco; by-design Anthropic). **Fase-1.1 reconciliada** (estaba "pendiente"). **Audit 8/8 FALLO [análisis]: 0 primariamente-léxico** (hp008=corpus-gap de extracción, no léxico; resto síntesis/razonamiento + hp011 7-seg; el léxico/BM25 no está en prod —FTS=`plainto_tsquery` AND `migrations/006:292`, sin RRF— pero NO es el cuello de los 8 → miré el cimiento que el dúo exigió, lo descarté con datos, no a ciegas como s46). **Lever context→generator** (destapado por el dúo): flag `GENERATOR_INCLUDE_CONTEXT` default OFF (prod intacto); **smoke-DÉBIL** (A≈B, el bot ignora el blurb que ya sitúa con el header, 0 fabricación, generador no-determinista → A/B exige K-mayoría; no concluyente, 3 casos single-run). **Dúo ronda 2 SPLIT** (sub-agente "cerrar/débil-por-diseño" vs cross-model "no cerrar — content-claro≠diversidad; mecanismos plausibles content-pobre/multi-doc/ES-EN/OEM") → **NO cerrar; diferir a A/B pre-registrado + estratificado en Track B-dev** (`docs/PREREG_ab_context2gen.md`); el eval grande da el test concluyente **por DIVERSIDAD estratificada, NO por N bruto**; diferir-con-pre-registro ≠ procrastinación (s27). **PRÓXIMO s49 = Track B = el trabajo de valor** (expandir eval ~60-100 con estratos content-pobre/multi-doc/ES-EN/OEM + `split` dev/held-out + embargo en `gold_store`) → habilita el A/B-lever pre-registrado + **A/B contextual-retrieval (ablación)** vivo-separado + F3 (escala). **feedback_my_bias #20:** over-frame pro-F3 (cerrar sin léxico) cazado por el dúo ronda 1; **el cross-model rompió el echo-chamber otra vez** (el sub-agente Claude convergió con mi prior y SE DELATÓ: "comparto tu blind spot, corre el cross-model"). 0 FP. Cero código de prod efectivo (flag inerte).
> - **RESULTADO s49 (7 jun 2026 — `DECISIONS.md` DEC-023): backbone de Track B SHIPPED-a-rama; el DÚO cazó un fallo de embargo CRÍTICO antes de cablear.** Alberto eligió **"backbone + decidir el bulk luego"** (barato-primero). Construido el cimiento infraestructural común a todos los caminos: esquema del ruler con **`split`** (dev/held-out) + **`estrato`** (multi-tag de vocabulario CONTROLADO, 1:1 con el PREREG) en `gold_store.py` + validación tiered + helpers `dev()`/`heldout()`; **retrofit de los 22** (todos `split=dev`, ya inspeccionados; 17 con estrato anclado — los 5 estratos del PREREG cubiertos pero VARIOS a **n=1**, lo que confirma empíricamente por qué el bulk hace falta); `tests/test_gold_store.py` NUEVO (16; no existía test del ruler); **suite 195 verde**; 0 cambios de producto. **El bite crítico del dúo (cross-model 6/6 + sub-agente 5/5, 0 FP, NO-SÓLIDA, verificado regla C):** el embargo del held-out debía vivir en la **PUERTA** (`gold_store.verified(include_heldout=False)`), NO solo en `test_bot_vs_gold` — porque el JUEZ del A/B corre vía `verified()` (4 consumidores) y la autoría entra `verificado` → un held-out nuevo quedaría EXPUESTO al juez. Corregido + `TECH_DEBT #42` (lectores-directos de diagnóstico). Bites adoptados (todos): §A wiring + run-manifest **DIFERIDOS explícitos** (DoD-de-medición, no hay lever en el backbone); `content-pobre` con def **operacional offline** (anti-circular); `control-pass` **fuera** del vocabulario. **Rebanada vertical = opción (a) del dúo [declarar el gap]:** validó esquema + compat-de-pipeline (`author_atomic_facts` preserva split/estrato; `upsert` fail-closed exige split) + embargo; **NO** valida el localizador-duro (= BULK, diferido por Alberto; a medias envenenaría el árbitro). **PRÓXIMO:** decidir el bulk (camino-corto-A/B vs base-completa DEC-021 §C) con el backbone montado → autoría con estratos + held-out embargado → A/B-lever pre-registrado + A/B contextual-retrieval (ablación) + F3. `feedback_my_bias`: over-frame = embargo-en-un-harness (estructural), cazado por el dúo ANTES de cablear; el control funcionó (0 prod tocado).
> - **RESULTADO s49b (7 jun 2026 — `DECISIONS.md` DEC-024): piloto Track B (gold #1 cat008) + control anti-olvido de procedimientos (3 capas).** Alberto eligió seguir con el bulk; arrancado el piloto. **cat008** (M710/MI-DMMI, estrato diagrama+oem-relabel) autorado por el **procedimiento COMPLETO** (loc exhaustiva 12 variantes + render±1 + doble-señal cross-model en guía Y manual oficial Notifier; RFL 47kΩ cuádruple-señal + 18kΩ M200E-EOL-R18 + opción VdS; falso conflicto "10k" descartado) → upserted (23 golds). **Hallazgo de método:** el dato del diagrama SÍ está en chunks_v2 (LlamaParse multimodal) → "diagrama" ≠ corpus-gap automático; chunks_v2 = nota POST-hoc, JAMÁS criterio (circular — corrección de Alberto). **Control anti-olvido (Alberto: "que no se te escape el procedimiento"):** (1) CLAUDE.md **Protocolo 4** (registro gatillo→acción + regla "verifica el checklist punto-por-punto ANTES de 'hecho'"); (2) RULER_DESIGN §2 checklist explícito; (3) gold_store **enforcement-puerta** (upsert valida; verificado exige `metodo`+`verificado_por`). **El dúo cazó NO-SÓLIDA (cross-model 7/7 + sub-agente 6/6, 0 FP): reproduje el sesgo #20 (verificación incompleta) DENTRO del diseño anti-sesgo** (premisa falsa: 22/23 ya tenían `metodo` top-level) + upsert no era puerta → v2 más simple. 198 tests. **PENDIENTE: golds #2-5** (FAD-905 scouteado, NO upserted — retomar con conexión estable, por el procedimiento completo) + PR. `feedback_my_bias #22`. La conexión inestable forzó cierre parcial protegido (commits `cd28700`/`00b5543`).
> - **RESULTADO s50 (7 jun 2026 — `DECISIONS.md` DEC-025): la sesión arregló el CIMIENTO de autoría de golds (0 golds escritos, por buena razón — más valioso que 4 golds sobre cimiento roto).** Arrancar #2-5 destapó dos errores que cazó **Alberto**: el **VICIO** (scoutear `content-pobre` consultando chunks_v2 = criterio de SELECCIÓN circular, reproducción de cat008/s49b) + un **DUPLICADO** (mi "ASD535 flujo bajo" = **hp002** ya existente; no revisé las preguntas existentes, solo el conteo de estratos). **Hallazgo de raíz: `content-pobre`/`fragmento-truncado` están MAL DEFINIDOS como categoría de AUTORÍA** — son propiedades del *chunking* (¿el valor está en el `content` del chunk?), invisibles desde la pregunta → obligan a chunk-peeking ANTES de escribir (empírico: 2 fallos source-first; cat008 era diagrama y NO content-pobre). **Reframe (Alberto + dúo): autorar por DIMENSIÓN DE FALLO** (definible desde la FUENTE: síntesis/es-en/conflicto/oem/familia/scan-ocr + las conductas) → cero chunk-peeking; los artefactos (content-pobre/fragmento/tabla/diagrama) BAJAN a **CAUSA post-hoc** (lo que el ruler DESTAPA → enruta el lever de extracción; reconcilia §7↔§8). **Completitud (Alberto "¿nos dejamos alguno?"):** organizar por fallo SACÓ A LA LUZ 3 dims sin slot que el canon ya nombra: **conflicto-revisión** (§1), **mezcla-cross-product** (§0), **síntesis/completitud intra-manual** (multi-doc viejo = solo ≥2 manuales) + candidato term-mismatch. **Alcance (Pregunta cero, anti-sobre-ingeniería): principio + guard MÍNIMO ya + consolidación DIFERIDA a gatillo DURO** (antes del 1er A/B-lever, porque el A/B lee los estratos = freeze-contract; no "tras 10-15 golds"). **Tier 1 cableado + verificado (198 tests, rama `eval/s50-failure-dim-taxonomy`):** `gold_store` split `ESTRATOS_AUTORIA`/`ESTRATOS_POSTHOC` + `CLAUDE.md` Protocolo 4 (no-duplicado + dimensión-fallo + chunks_v2-jamás-en-selección) + `RULER §2` paso 0. **Mix #2-5 corregido (dúo cazó mi over-pivot):** mi 1er mix (re-target a conductas no-answer) MATABA el A/B (estratos PREREG famélicos) → mayoría estratos-A/B + 1 clarify; admit/refuse-inference DIFERIDOS hasta el **contrato de ausencia**. **2 dúos CONVERGENTES** (mix NO-SÓLIDA; alcance SÓLIDA+2fixes), 0 FP. `feedback_my_bias`: Alberto caza los conceptuales/de-cimiento; el dúo los de framing/alcance. **PENDIENTE s51:** golds #2-5 por dimensión-de-fallo (guards puestos = camino por defecto); consolidación §8+PREREG+3 dims (gatillo: antes del A/B-lever); contrato de ausencia (admit/refuse).
> - **RESULTADO s51 (8 jun 2026 — `DECISIONS.md` DEC-026): bulk Track B — 4 golds autorados por DIMENSIÓN DE FALLO (ruler 23→27); es-us DIFERIDO por límite de corpus.** Ejecutado el pendiente de s50 con el procedimiento COMPLETO (`RULER §2`) y **SERIAL** (Alberto declinó paralelizar la autoría en zona de dolor: el sesgo se replica × agentes; el briefing del sub-agente es el riesgo; precisión>velocidad). **GATE del dúo sobre la SELECCIÓN antes de autorar** (cross-model 6/6 + sub-agente 4/4, 0 FP, NO-SÓLIDA→corregida): cazó `SDX-751EM`/`SDX-751` ausentes del catálogo + solape #5/hp008 (→ cambié la familia del clarify a 751-ión CPX/IDX); #4 a provisional; mi sub-claim "PDFs US cifrados" FALSO = framing reincidente. **4 golds, cada uno doble-señal TRIPLE (match-texto + Claude render + GPT en frío `cross_verify_image`) + check post-hoc de que muerde:** `cat009` conflicto-revisión (NFS Supra EOL **4K7→6K8 Ω**, v04→v05 EN; rev vieja viva en chunks_v2 ×5) · `cat010` es-en (IS-mA1 e2S ATEX, EN-only: 24V dc/barrera 28V·93mA, Ui=28V/Ii=93mA/Pi=660mW, Ex ia IIC) · `cat011` familia-ambigua/**clarify** (near-name "751": CPX-751E ión estándar vs IDX-751 óptico seguridad-intrínseca; candidatos del catálogo D6) · `cat012` síntesis-completitud intra-manual (batería AM-8200 = (A+B)×1,2, fusiona consumo §3.12/13 + fórmula/autonomía §11 + capacidad §3.4.1, dispersos en chunks distintos). **+2 tags a `ESTRATOS_AUTORIA`** (`conflicto-revision`, `sintesis-completitud`; def inline = cambio-1-línea sancionado, NO la consolidación §8). Mix DEC-025(f) cumplido (3 A/B + 1 clarify); estratos reforzados (es-en 1→2; conflicto-rev/síntesis/familia-ambigua 0→1; clarify 1→2). **Hallazgo de corpus:** español-céntrico → dimensiones cross-language escasas en las FUENTES (es-us sin fuente fresca = duplicaría hp012/hp006; es-en limpio sólo en nicho importado IS-mA1) → anotado para el bulk. **El procedimiento + el dúo evitaron 3 golds malos** (WFDEN no-EN-only; SDX-751EM no-catálogo; AM-8200N-usuario sin specs). **200 tests verdes, 27 golds, rama `eval/s51-golds` → PR.** PENDIENTE: es-us (cuando entren manuales US); consolidación §8/PREREG/3-dims (gatillo: 1er A/B-lever); contrato de ausencia (admit/refuse); poblar held-out (todos `dev` ahora). Canónico **DEC-026**.
> - **RESULTADO s52 (8 jun 2026 — `DECISIONS.md` DEC-027): adquisición de corpus Kidde (download+parse), INGESTA a `chunks_v2` DIFERIDA.** Alberto pidió avanzar la descarga+parse de manuales Kidde **en paralelo al RULER** (no contamina: los golds anclan en la FUENTE, no en chunks_v2 — DEC-025). Reverse-engineered el portal `firesecurityproducts.com` (SPA Angular → **API PIM REST**: OAuth password-grant + el gate real `Origin/Referer` + `product_group`/`product_downloads`; método reproducible en **`docs/CORPUS_FIRESECURITYPRODUCTS.md`**). **17 SKUs** (paneles Kidde "Control", brand 17316; series NC / 2X-A / 2X-A Táctil) → **31 PDFs / ~696 pp** (`Manuales_Kidde/`, 3 categorías, ES + fallback-EN, dedup por serie 107→31). **Parse LlamaParse 31/31 OK** (agentic sonnet-4.5 = config del corpus `agent_anthropic-sonnet-45`; ~$42; calidad validada: tablas/diagramas capturados). Inventario: hoja `Kidde` (19 prod / 31 docs) vía `update_inventario.py` + sidecar de metadata del PIM. **INERTE al corpus/eval**: la **ingesta a `chunks_v2` sigue DIFERIDA** (gate RULER + Protocolo 3 — no romper el freeze-contract del A/B). Rama `corpus/kidde-panels`. **No toca el rumbo del RULER** (pendientes s51 intactos). Canónico **DEC-027**.
> - **RESULTADO s52 (eval — `DECISIONS.md` DEC-028): cerrados los 2 huecos n=0 de conductas de SEGURIDAD del ruler (`admit`/`refuse-inference`) + smoke-validación + sync del juez. Ruler 27→30.** La pregunta de Alberto ("¿ampliamos con más preguntas?") se resolvió **eval-driven**: NO volumen de specs normales (diluiría un instrumento DIAGNÓSTICO, RULER §0; testea donde el bot es fuerte) sino **cobertura de los huecos** — las 2 conductas de seguridad de lo alto de la jerarquía estaban a **n=0** (medido: answer 24/clarify 2/conflicto 1/admit 0/refuse 0). 3 golds SERIAL por `RULER §2` con **GATE del dúo sobre la selección**: `cat013` refuse-inference (CAD-150 Detnov + óptico Notifier SDX-751: lazo Detnov vs protocolo CLIP; ningún manual avala la compat cross-marca → no inferir compat NI incompat, surfacear por-producto + redirigir) · `cat014` answer (DGD-600 vida útil 10 años presente + MTBF ausente-probado) · `cat015` admit (firmware CAD-150 ausente del corpus; localización exhaustiva multi-doc ES+EN). **El dúo cazó mi falso-admit reincidente** (C2b: la vida útil SÍ está documentada → era `answer`, no `admit`; patrón s33 + sesgo #20/#22, source-verified regla C); Alberto lo mantuvo como answer. **Smoke dirigido (chunks_v2, juez sincronizado a las 5 conductas): 2 PASS + 1 PARCIAL** → el bot YA maneja las conductas de seguridad (rehúsa/admite/no-fabrica bien); el PARCIAL (cat013) = incompletitud por **sub-retrieval cross-marca** (solo trajo el manual Detnov), un **lead de retrieval** logueado, no déficit de golds → **medir-primero evitó autorar de más**. Sync del juez `test_bot_vs_gold` (estaba stale pre-Track-B). **Diferido:** estratos de contenido n=1 (gatillo A/B-lever); contrato de ausencia formal; refuerzo seguridad a n=2 (opcional); poblar held-out. 200 tests, rama `eval/s52-safety-conducts`. Canónico **DEC-028**.
> - **RESULTADO s53 (8 jun 2026 — `DECISIONS.md` DEC-029): corpus "base instalada TRATEIN" (multi-marca) vía pedidos del portal, INGESTA DIFERIDA.** Alberto pidió "más Kidde" → scrapear el área de pedidos (`/my-orders`): los 10 pedidos de **TRATEIN PCI** = **41 productos distintos MULTI-MARCA** (no solo Kidde: + Aritech, Edwards, genéricos) = la **base instalada real** (lo más relevante para el técnico). Método nuevo (reproducible, `docs/CORPUS_FIRESECURITYPRODUCTS.md §7`): `orders`→`order_details`→`line_items` (product_id directo) → pipeline probado. **76 PDFs** agrupados por marca real (`product_details`): Kidde/Aritech/Edwards/Otros. **Parse: 66 nuevos / 893 pp / ~$50** (solape 2X-A con s52 saltado por SHA). Inventario 4 marcas (Kidde 33/55 · Aritech 13/33 · Edwards 2/3 · Otros 12/16). Atribución 2X = Aritech (OEM) vs Kidde-marketing s52 → cross-listed documentado. **INERTE**: ingesta a `chunks_v2` DIFERIDA. Hecho en `git worktree` aislado (árbol compartido con la sesión paralela del eval). Rama `corpus/kidde-installed-base`. Canónico **DEC-029**.
> - **RESULTADO s54 (8 jun 2026 — `DECISIONS.md` DEC-030): Detnov CAD-171 (serie Vesta) añadido al corpus, INGESTA DIFERIDA.** Alberto detectó una central Detnov nueva no identificada (CAD-171, 2 lazos). `detnov.com` es WordPress estático → 5 PDFs por links directos (datasheet ES+EN, instalación MI-716, + config/software CAD-250 MC-380/MS-416). **No-duplicados verificado** (la hoja Detnov ya tiene CAD-250 instalación+usuario, NO config/software → contenido nuevo). Parse **5/5 OK** (~218 pp / ~$12). Inventario: **APPEND** a la hoja Detnov legacy (4-col; NO rebuild, que borraría los 109) → 110 prod / 124 docs. **INERTE**: ingesta a `chunks_v2` DIFERIDA. Worktree aislado off main (#47). Rama `corpus/detnov-cad171`. Canónico **DEC-030**.

---

## 1. Resumen ejecutivo

**El estado real no es el que dice la métrica.** El eval reporta 51/52 PASS (98%),
pero esa cifra está sobreestimada y mide algo más estrecho de lo que parece. La
Fase 0 (calibración del eval) lo ha confirmado con evidencia.

**Lo que hemos aprendido, con datos:**

1. **El bot NO tiene un problema de invención de datos.** Verificación determinista
   de los 52 casos: de 49 datos duros citados (números, normas, switches,
   secciones), **49 están soportados por los chunks (100%), 0 miscitados, 0
   inventados**. La narrativa de "alucinaciones" que arrastrábamos no se sostiene
   para datos verificables.

2. **El problema real es el RETRIEVAL**, no la generación. Hay casos donde la
   respuesta correcta existe literalmente en el corpus pero el retrieval no se la
   entrega al bot (hp009: resistencia fin de línea 6,8 kΩ; hp001: contraseña de
   instalador). El bot responde con honestidad "no aparece" — no alucina, pero la
   respuesta es inservible para el técnico porque le faltó información.

3. **El eval mismo está parcialmente "amañado" sin querer.** Varias preguntas se
   recalibraron de `answer` a `admit_no_info` asumiendo que el corpus no tenía la
   respuesta. Verificado: en hp006, cm001, cm005 la respuesta SÍ está en el
   corpus. El eval bajó el listón en vez de arreglar el retrieval.

4. **El judge actual está mal de ALCANCE, no de calibración.** Evalúa "¿el bot fue
   fiel a los 5 chunks que recibió?" — y casi siempre sí. No evalúa "¿el bot dio
   la mejor respuesta que el corpus permite?". Esa segunda pregunta es la que
   importa.

5. **Un evaluador es tan fiable como la integridad de su input.** Durante la Fase 0,
   un bug propio (truncado de chunks a 1.800 caracteres) hizo que el 78% de los
   chunks llegaran mutilados al calibrador. Lección estructural, no anecdótica.

**El plan en una frase por fase:**

- **Fase 0** — Reanclar la métrica: judge v2 + verificación determinista. *(en curso)*
- **Fase 1** — Calidad estructural: arreglar el retrieval y la extracción de PDFs.
- **Fase 2** — Escalabilidad: quitar el hardcoding por fabricante antes del fabricante ~5.
- **Fase 3** — Routing + tool use: el "agentic RAG" bien entendido.
- **Fase 4** — Eval orgánico (queries reales de DGs) + CI.
- **Fase 5** — Técnicos reales (post 1-sept): field-grade eval y multi-turno.

---

## 2. El estado real del sistema — auditoría honesta

### 2.1 Por qué la métrica "98%" es engañosa

El judge automático (Claude Sonnet 4.6) reporta 51/52 PASS. Tres razones por las
que esa cifra no significa "el bot funciona al 98%":

- **Alcance estrecho.** El judge solo compara la respuesta del bot contra los
  chunks que el retrieval le pasó. Si el retrieval falló y el bot dijo "no tengo
  info", el judge lo da por bueno — sin saber que la info sí existía en el corpus.
- **El eval persiguió al bot.** Las preguntas que el bot fallaba se reclasificaron
  a `admit_no_info`. La categoría `cross_manual` tiene hoy 7 de 8 preguntas
  esperando "el bot admite que no sabe". El 98% mide "acierta el comportamiento
  que le pedimos", no "responde bien".
- **Sin gold standard humano.** Las 52 preguntas tienen `verified: false`. No hay
  ancla externa que diga si el judge acierta.

### 2.2 Lo que SÍ funciona (no tocar)

- **Faithfulness citacional.** Verificado: el bot no inventa datos duros (§3.4).
- **Retrieval híbrido base** — vector + keyword + content search en paralelo, con
  filtros cross-product y diversificación multi-doc. La estructura es correcta.
- **HyDE** — la expansión de query con hipótesis de manual funciona y está en
  producción (resolvió el vocabulary mismatch de hp001).
- **Observability** — `query_logs` captura cada interacción con consent RGPD.
- **Document lifecycle** — gestión de revisiones (supersede chains) Phase 1.
- **Arquitectura agnóstica al fabricante** en schema, retriever y generator.

### 2.3 Lo que NO funciona — los gaps reales

| Gap | Evidencia | Capa | Severidad |
|---|---|---|---|
| Retrieval miss: info en corpus que no llega al bot | hp009 (6,8 kΩ), hp001 (contraseña), hp005, hp014 | retrieval | **Alta** |
| Extracción de tablas: `[TABLA EXTRAÍDA]` mal aplicado (falsos + y −) | hp002, hp003, ≥12 casos | ingesta | **Alta** |
| Tablas con marcas visuales (X/✓) perdidas en extracción | hp007 (VESDA Tabla 7-1) | ingesta | **Alta** |
| Recalibraciones de YAML que enmascaran fallos de retrieval | hp006, cm001, cm005 (verificado: la info existe) | eval | Media |
| Reranker = LLM genérico (Sonnet pide a Sonnet) | reranker.py | retrieval | Media |
| `MODEL_PATTERN` regex hardcoded por fabricante | retriever.py (~50 líneas para 3 fabricantes) | escalabilidad | **Alta** (a 30+) |
| Atribución de fabricante incorrecta | ASD = Securiton, no Detnov | metadata | Media |
| Prompt del generator monolítico y saturado | TECH_DEBT #28 (regresión al añadir un bloque) | generación | Media |
| `section_title` de chunks no coincide con el contenido | hp003 (dice 2.4, trae 2.3) | ingesta | Media |
| Sin separación retrieve_top_k / generate_top_k | config.py (ambos = 5) | retrieval | Media |
| Judge de alcance estrecho, sin gold, mismo modelo que el bot | §2.1 | eval | **Alta** |

### 2.4 Escalabilidad a 30+ fabricantes

El **core** escala (schema, retriever, generator, eval son agnósticos). El
**boilerplate por fabricante NO escala**:

- `MODEL_PATTERN` regex hardcoded — 50 líneas para 3 fabricantes → ~500 para 30.
- Overrides de metadata hardcoded en `chunker.py`.
- Scraping con un script ad-hoc por fabricante.

**Regla:** el sprint de externalización a YAML (Fase 2) debe hacerse **antes del
fabricante ~5**, y siempre antes de la ingesta masiva post-M&A. Hacerlo después
duplica trabajo.

---

## 3. Hallazgos de la Fase 0 — calibración del eval

### 3.1 El proceso seguido

1. Se generaron 5 archivos de calibración (52 casos) para revisión humana.
2. Alberto calibró a mano hp001-hp004 (gold humano real).
3. Cowork (Opus 4.7, con acceso al corpus) calibró los 52 y produjo un documento
   de recomendaciones + una auto-auditoría adversarial de sus propios golds.
4. Claude verificó de forma **determinista** los claims objetivos contra los PDFs
   y los chunks completos.

### 3.2 El bug de truncado y su lección

`build_calibration_v2.py` truncaba el contenido de cada chunk a 1.800 caracteres.
**El 78% de los chunks (203 de 260) superaban ese límite**; las 52 preguntas
tenían al menos un chunk truncado. Cowork calibró sobre información mutilada — en
hp010 y hp011 declaró "fabricación citacional" porque el dato estaba en la
posición 1.870 y 2.148 del chunk, después del corte.

**Lección estructural:** un evaluador (LLM o humano) es exactamente tan fiable
como la integridad del input que recibe, y no tiene forma de saber que su input
está incompleto. → La verificación de hechos debe operar **siempre sobre la
fuente canónica completa**, nunca sobre una representación intermedia.

### 3.3 Verificación documental — resultados

Verificación con PyMuPDF sobre los PDF reales (inmune al truncado):

| Claim de Cowork | Verificación |
|---|---|
| hp006: "Earth Fault" está en AFP-300/400 como "Falla de Tierra" | ✅ Confirmado (50253SP págs. 80/160/215) |
| hp009: la resistencia fin de línea 6,8 kΩ existe | ✅ Confirmado (MIE-MI-530 pág. 21, sec. 3.4.4) |
| hp013: el ADW535 sí tiene batería de litio | ✅ Confirmado (pág. 29) |
| cm003: ASD531 es −10/+55 °C y 70%/95% humedad | ✅ Confirmado (pág. 91) — corrige el gold |
| cm001/cm005: doc Honeywell con respuesta cerrada existe | ✅ Confirmado (1 pág., literal) |
| cm004: dato "EN54-2 13.7 = 512" es real | ✅ Confirmado (MIDT190 pág. 24) |
| hp019: gold "−20/+60 °C" | ❌ Erróneo — el manual real es −10/+55 |

### 3.4 Verificación de citación — el bot no inventa datos duros

`scripts/verify_citations.py` extrae cada dato duro citado con `[F<n>]` y verifica
deterministamente si está en el chunk citado. Sobre los 52 casos:

> **49 datos duros citados → 49 soportados (100%), 0 miscitados, 0 inventados.**

(Los 4 que la primera pasada marcó como dudosos eran falsos positivos de formato
de unidad: `²` vs `2`, `Ω` vs `R`/`ohm`. Resueltos con normalización.)

**Límite honesto:** esta capa solo cubre datos duros. Las afirmaciones
cualitativas (rutas de menú, procedimientos) necesitan la capa 2 del judge v2
(§5). Pero la conclusión sobre datos verificables es sólida.

### 3.5 Conclusión de la Fase 0

El problema del bot **no es la alucinación citacional**. Es:

1. **Retrieval** — no entrega al bot información que sí está en el corpus.
2. **Extracción** — tablas y metadata mal extraídas del PDF.
3. **El eval mismo** — judge de alcance estrecho + recalibraciones que bajan el listón.

Esto **reordena las prioridades**: la Fase 1 (retrieval + extracción) es la de
mayor impacto en calidad real. El esfuerzo en "anti-alucinación" (validadores
post-generación) es un camino equivocado — ya falló una vez (TECH_DEBT #11i) y la
evidencia dice que la alucinación no es el cuello de botella.

---

## 4. El plan de acción — 5 fases

### Fase 0 — Reanclar la métrica *(en curso)*

**Objetivo:** una métrica que mida calidad real, no "comportamiento que pedimos".

| Tarea | Estado |
|---|---|
| Verificación de citación determinista (capa 1 del judge v2) | ✅ Prototipo funcionando |
| Arreglar el bug de truncado en `build_calibration_v2.py` | Pendiente |
| Corregir premisas falsas en `rag_improvements_recommendations.md` | Pendiente |
| Judge v2 — capa 2 (claims cualitativos) + arquitectura completa | Pendiente (§5) |
| Gold answers regeneradas con extracción de PDF + validación humana en muestra | Pendiente |
| Holdout split: `calibration_set` (~10) / `eval_set` (~42) | Pendiente |
| Validación humana de Alberto en muestra pequeña (criterio, no hechos) | Pendiente |

### Fase 1 — Calidad estructural (retrieval + extracción)

**Objetivo:** cerrar los retrieval misses. Es la fase de mayor impacto en calidad.

1. **Contextual retrieval** (Anthropic, sept 2024) — añadir a cada chunk un
   párrafo de contexto generado antes de embeber. Reduce el fallo de retrieval
   ~49% según Anthropic. **HECHO (verificado s48, DEC-022): YA implementado y activo
   al 100% en `chunks_v2`** (B7 `contextualize.py` → embebido `context+content`,
   `embed.py:55`). Su **delta end-to-end NO se ha medido** (el blurb solo entra al
   retrieval, no a la generación); ablación pendiente (Track B). *Estructural, escalable.*
2. **Extracción visual de PDFs** — sustituir el extractor actual por LlamaParse
   en **modo multimodal** (VLM), no estándar (ver Resultado del PoC abajo).
   Elimina el `[TABLA EXTRAÍDA]` con sus falsos positivos y el texto sin
   espacios. Visión por defecto, no como fallback condicional.
3. **Reranker dedicado** — sustituir el reranker LLM-genérico por Cohere Rerank
   3.5 o Voyage Rerank-2 (cross-encoder entrenado). Más preciso, más barato, más
   rápido.
4. **BM25 + RRF** — fusión híbrida vector + BM25 con Reciprocal Rank Fusion.
   Captura términos exactos del dominio que los embeddings pierden.
5. **Separar retrieve_top_k (15-20) de generate_top_k (5-8)** — recall amplio para
   el reranker, contexto acotado para el generador.
6. **Auditar y revertir las recalibraciones de YAML ilegítimas** — hp006, cm001,
   cm005: verificado que la info existe; revertir a `answer`.

#### Diagnóstico del corpus (22 mayo 2026)

Inventario de los 1.208 PDFs (24.696 páginas) — `logs/corpus_diagnosis.json`:

- **Carga visual:** 567 documentos (47%) tienen contenido visual denso (≥0,5
  imágenes grandes por página). El contenido visual no es un caso aislado — es
  casi medio corpus.
- **Idiomas:** ~66% ES, ~17% EN, ~9% PT/FR/IT, ~8% sin detectar.
- **Duplicación:** 241 PDFs son copias byte-idénticas (verificado por SHA-256 en
  la Etapa A1: 1.208 PDFs → 967 únicos). 139 de los duplicados cruzan carpeta de
  fabricante — flag en el manifiesto para resolver la atribución en B5.
- **Escala del re-proceso:** 20.486 páginas únicas a extraer (de 24.696 totales,
  verificado en A1). Coste de extracción agéntica ≈$1.150 (≈45 créd/pág ×
  20.486 págs) — verificado tras el probe; pago único.

#### Decisiones de diseño del pipeline de re-ingesta

1. **Multimodal de primera clase, no fallback condicional.** Con el 47% del corpus
   con contenido visual denso, la visión se aplica por defecto. La arquitectura
   actual (visión solo si poco texto + imágenes grandes) está mal calibrada.
2. **De-duplicación a dos niveles.** Nivel 1: hash SHA-256 del archivo (caza los
   ~188 duplicados). Nivel 2: dedup **semántica a nivel de chunk** (embedding,
   intra-producto) — caza los chunks ES/EN equivalentes (descarta el redundante,
   conserva el contenido único, prefiere ES) y la duplicación del chunker
   (TECH_DEBT #7).
3. **Política de idiomas.** Se indexa: todo lo que contenga español (monolingüe o
   multilingüe) + lo solo-EN. NO se indexan los monolingües PT/FR/IT — pero se
   *registran* (no se borran): si un producto solo está documentado en otro
   idioma, hay que saber que la fuente existe para traducir/indexar bajo demanda.
4. **Detección de idioma por bloque/página** con librería robusta (`lingua`), no
   por heurística — un manual "ES FR GB IT" tiene páginas de cada idioma y el
   filtro de idioma del retrieval las necesita bien etiquetadas.
5. **El pipeline es el mismo para re-procesar el corpus y para añadir un manual
   nuevo** — automatizable desde el día uno. "Añadir un fabricante" debe ser un
   comando, no un script ad-hoc.
6. **`page_number` fiable por chunk** — prerrequisito del deep-link a la fuente
   (enlace `manual.pdf#page=N` para que el técnico vaya directo a la página).

#### Resultado del PoC de extracción (22 mayo 2026)

PoC sobre 6 manuales representativos, 3 stacks — `logs/poc_extraction/`:

- **El extractor actual (baseline) hay que sustituirlo — demostrado.** Pierde los
  espacios entre palabras dentro de los bloques que marca como tabla (`pdfplumber`
  produce texto pegado, ilegible), falsea tablas masivamente (`[TABLA EXTRAÍDA]`
  en títulos de figura y párrafos normales), no genera estructura (0 headers),
  25-28% de duplicación interna, y 0 caracteres en escaneados.
- **LlamaParse gana en texto y tablas** — texto legible, headers, tablas markdown
  excelentes (cabeceras + valores), OCR de escaneados, 6-13% duplicación.
- **Docling**: texto narrativo limpio pero pierde el contenido visual (marca
  `<!-- image -->` sin leerlo) y es lento en CPU.
- **Hallazgo clave (MPDT190 / hp005):** las capturas de pantalla de UI con texto
  extraíble — donde vive mucho procedimiento — se **pierden** con LlamaParse y
  Docling en modo estándar (las tratan como imagen). El baseline las capturaba por
  fuerza bruta. → **El modo multimodal de LlamaParse es obligatorio**, no opcional;
  el modo estándar sería una regresión en el contenido visual.
- **Diagramas de flujo decisionales** (MPDT190 pág. 60 — diagrama de la Matriz de
  Control, relevante para hp005): ningún extractor reconstruye la estructura —
  extraen las cajas como texto suelto y pierden las flechas y la jerarquía de
  decisión. Inservible como texto. Requieren **doble vía**: el VLM describe la
  lógica del flujo (para que el bot razone) **+** se adjunta la imagen del
  diagrama en la respuesta al técnico (para que lo vea). Es el test más exigente
  de la tarea #12.

**Decisión (confirmada — tarea #12, 22 mayo 2026):** stack de extracción =
**LlamaParse en modo multimodal** (`parse_mode=parse_page_with_lvm`). El modo
estándar queda descartado. Salvedad estructural: los diagramas de flujo
decisionales exigen "doble vía" obligatoria — ver el resultado abajo.

#### Resultado de la tarea #12 — confirmación del modo multimodal (22 mayo 2026)

`scripts/poc_multimodal.py` ejecutó LlamaParse multimodal
(`parse_page_with_lvm`, VLM = `anthropic-sonnet-4.5`) sobre un excerpt de 9
páginas de MPDT190 (printed 53-61): teclado de edición, los dos diagramas de
flujo decisionales (7.2 Categorías de entrada, 7.3 Categorías de salida) y
capturas UI. Salida en `logs/poc_extraction/visual_MPDT190__llamaparse_lvm_anthropic-sonnet-45.md`.

**Se confirma el modo multimodal como stack.** Frente al estándar es una mejora
cualitativa, no incremental:

- **Texto, tablas, teclados, capturas UI:** limpios y fieles. Donde el estándar
  daba texto sin espacios o tablas falsas, el multimodal produce markdown
  estructurado y legible.
- **Diagramas de flujo:** el estándar los convertía en una tabla de 38-47 filas
  de palabras sueltas — 0% usable. El multimodal los reconstruye como grafos
  `mermaid` con nodos y aristas dirigidas — la lógica de decisión pasa de
  invisible a navegable.

**Salvedad — verificada contra las páginas reales 58 y 60 (`_MPDT190_verify_p65/67.png`).**
En los diagramas de flujo el VLM produce salida *estructurada pero parcialmente
inventada*, lo que es **más peligroso que la ensalada de palabras**: es una
alucinación con apariencia de orden, y ni el bot ni el judge pueden detectarla.

- **Notas al pie inventadas.** Las notas (a)-(h), de letra minúscula en el
  original, salen como una misma frase plausible repetida 7-8 veces verbatim.
  El VLM no pudo leerlas y rellenó.
- **Etiquetas mal leídas.** "REARME" → "REPLICA ARMA"; "ACTIVACIÓN TÉCNICA" →
  "ACTIVACIÓN ESCENA"; cajas con palabras pegadas ("CONTROLLa").
- **Grafo parcialmente incoherente.** Nodos conectores (C1-C13) referenciados
  pero sin definir; subgrafo "ALARMA" colgando suelto.

**Segunda verificación — el otro lado del límite (rango de hp005, PDF 71-78).**
Una segunda pasada multimodal sobre el procedimiento de "coincidencia de dos
detectores" — la respuesta de la pregunta hp005 del eval, en capturas de menú y
texto procedimental — confirma que sobre ese tipo de contenido el multimodal es
**fiel y legible**: las pantallas salen como bloques de código limpios, los
pasos numerados son coherentes, las cajas IMPORTANTE/EN54 se conservan.
Verificado contra las páginas reales 65-66: los únicos errores son misreads
puntuales de etiqueta ("TRANSFERIR FLAG"→"FIJO", "n"→"3 COINCIDENCIA ZONAS"),
sin invención estructural ni notas fabricadas. **La fiabilidad del multimodal es
dependiente del tipo de contenido:** alta en narrativa, tablas, capturas de UI y
teclados; baja en los diagramas — crítica en los flowcharts decisionales densos.

(Matiz de método: hp005 está documentado como un fallo de *retrieval*, no de
extracción — el judge constató que el retrieval trajo chunks de fecha/hora en
vez del procedimiento de coincidencia. El multimodal no moverá hp005; lo moverá
la Fase 1 de retrieval. El test sirve para mapear la extracción, no para
diagnosticar hp005.)

**Tercera verificación — capítulo §7 completo (PDF 68-90, 23 págs).** El test
más representativo: un capítulo real continuo, no páginas sueltas. Narrativa,
decenas de capturas de menú, tablas y cajas de aviso salen fieles y usables, y
la respuesta completa de hp005 (coincidencia de entrada + salida de sirena, con
ejemplo trabajado incluido) queda bien cubierta. Afina el límite de los
diagramas — verificado contra las páginas reales 79-80: el render `mermaid` es
*siempre* una linealización con pérdida. En flujos lineales por naturaleza
(navegación de menús) es adecuada; en diagramas cuyo sentido está en la
estructura no lineal (los tiempos del pulsador ESPERA de 7.8.4, los árboles de
decisión de 7.2/7.3) pierde lo esencial — en los simples de forma silenciosa
(AHJ y NYC salen como grafos idénticos), en los densos con incoherencia e
invención. Donde el manual acompaña el diagrama con prosa explicativa, la prosa
sí se extrae bien y carga la información real (caso 7.8.4).

**Conclusión.** Stack confirmado, pero la "doble vía" que la Fase 1 anticipó
para los diagramas de flujo **deja de ser recomendación y pasa a ser obligatoria**:

1. La re-ingesta debe **detectar las páginas de diagrama de flujo** y marcar sus
   chunks de texto como *baja confianza / orientativos* — nunca fuente citable única.
2. La **imagen del diagrama se adjunta siempre** a la respuesta del técnico.
3. El texto del VLM sirve de andamiaje de navegación ("este diagrama trata de X,
   ramifica en Y"), no de cita textual.

Esto refina el plan, no lo contradice: la tarea #12 demuestra *por qué* la doble
vía es imprescindible y descarta confiar en el texto del VLM para flowcharts.

**Follow-up no bloqueante:** medir el coste real por página de
`parse_page_with_lvm` y compararlo con `parse_page_with_agent` — el presupuesto
de re-proceso (~$250-500) depende del modo final. No afecta a la decisión
arquitectónica: la doble vía es necesaria con cualquier modelo (la alucinación
en flowcharts es un problema de legibilidad del original, no de capacidad del VLM).

#### Arquitectura del pipeline de re-ingesta (decidida sesión 22, 22 mayo 2026)

**Principio — dos etapas con una frontera duradera.** El paso caro, externo e
irreversible es la extracción LlamaParse. Se aísla en una Etapa A cuyo output es
un artefacto duradero; el resto es una Etapa B local, barata y re-ejecutable.
Cualquier fallo de chunking, contexto, embedding o dedup se corrige re-corriendo
la Etapa B — nunca se re-paga LlamaParse. Es la respuesta estructural a "no
repetir el proceso".

```
ETAPA A — Extracción   (cara · externa · se paga UNA vez · artefacto duradero)
  A1  Inventario+dedup   walk del corpus, SHA-256 → manifiesto de archivos
                         únicos (descarta las ~188 copias byte-idénticas)
  A2  Extracción         LlamaParse parse_page_with_agent → JSON por archivo
                         (markdown + imágenes + nº de pág); modelo VLM
                         pendiente del probe representativo
  A3  Store duradero     Supabase Storage, clave = hash + config de extracción
  ───────────────────── frontera duradera ─────────────────────
ETAPA B — Indexación   (barata · local · re-ejecutable infinitas veces)
  B1  Idioma             lingua por bloque markdown (+ regex de marcadores)
  B2  Política idiomas   indexa ES / multilingüe-con-ES / EN-only;
                         registra-sin-indexar PT/FR/IT-only
  B3  Chunking           headers markdown + split por tamaño (techo <8000
                         chars con el blurb); sin partir tablas/procedimientos;
                         section_path (parent-child); page_number del JSON
  B4  Diagramas flujo    el VLM los clasifica en A2 → chunk confidence baja
                         + imagen adjunta (doble vía, tarea #12)
  B5  Metadata           detect_metadata() — interfaz; YAML en Fase 2
  B6  Dedup semántico    NO DESTRUCTIVO — marca duplicate_of, no borra
  B7  Contextual retr.   blurb por chunk (Haiku + prompt caching), cacheado
  B8  Embed + index      Voyage voyage-4-large @1024 · HNSW · tabla chunks_v2
  GATE  recall sobre las 52 preguntas del eval + checks automáticos
  SWAP  RENAME TABLE chunks→chunks_old, chunks_v2→chunks
```

**Decisiones fijadas:**
- **Extracción: LlamaParse `parse_page_with_agent`** — el modo agéntico domina
  a `lvm` (mejor calidad verificada y más barato: 45 vs 60 créd/pág). Modelo VLM
  pendiente del probe representativo. Coste realista del corpus ≈$1.150.
- **Embedding: Voyage `voyage-4-large` @1024 dims** — líder de retrieval
  multilingüe (mayo 2026); 1024 respeta el límite ~2000 del índice HNSW.
- **Dimensión 1024 como contrato** — todos los modelos serios soportan
  Matryoshka; almacenar siempre `vector(1024)` evita migración de schema ante
  un cambio futuro de modelo.
- **Abstracción de proveedor** en el módulo de embedding (`embed(texts,
  input_type)` con adaptadores Voyage/Cohere/OpenAI) — cambiar de modelo es
  config, no reescritura.
- **Store de Etapa A:** Supabase Storage.
- **Reemplazo del corpus:** `chunks_v2` + swap por `RENAME TABLE` — las RPC del
  retriever referencian `chunks` por nombre y siguen válidas sin tocarse.
- **`documents` NO se reconstruye** — `document_registry` es idempotente (hash).
- **`translator.py` se retira** — la política de idiomas indexa EN-only sin traducir.

**Robustez (anti "fallo grave que exija reprocesar"):**
- **Resumable** — estado por archivo; el run multi-día se reanuda.
- **Probe de coste** — antes del run completo, extraer ~150 páginas, medir
  créditos LlamaParse reales y extrapolar. No comprometer 23k páginas a ciegas.
- **Puerta de aceptación** — checks automáticos + recall de las 52 preguntas del
  eval + muestreo humano. Go-live solo pasada la puerta.

**Schema** (`chunks_v2`, migración versionada): añade `language`,
`is_flow_diagram`/`confidence`, `section_path`, `context` (separado de
`content`), `embedding vector(1024)` con índice HNSW.

**Módulos** — `src/reingest/`: `inventory` (A1), `extract` (A2/A3), `language`
(B1/B2), `chunk` (B3), `metadata` (B5), `dedup` (B6), `contextualize` (B7),
`embed`+`index` (B8), `pipeline` (orquestador). `src/ingestion/` se conserva
como referencia hasta que el pipeline nuevo lo sustituya.

**Orden de construcción:** A1 → A2/A3 + probe de coste → [run de extracción tras
visto bueno] → módulos B sobre el store → GATE → SWAP.

### Fase 2 — Escalabilidad pre-M&A

**Objetivo:** que añadir un fabricante cueste 2-3h, no 8-15h. Antes del fabricante ~5.

1. **Externalizar `MODEL_PATTERN` y overrides a YAML** — `config/manufacturers/{nombre}.yaml`. Un no-desarrollador puede editar.
2. **Template de scraping** — framework común; cada fabricante define solo selectores y login.
3. **Migrations versionadas** — `supabase migration`, no SQL ad-hoc.
4. **Corregir atribución de fabricante** — campo separado fabricante real vs distribuidor (ASD = Securiton).

### Fase 3 — Routing + tool use ("agentic RAG" bien entendido)

**Objetivo:** que el pipeline se adapte a la query, sin caer en el loop de agente libre.

1. **Intent classifier / query routing** — rutas catálogo / saludo / técnica /
   cross-brand. Cada ruta su pipeline. Evita que un saludo pague HyDE + 5 búsquedas.
2. **Tool use nativo** — el generador decide cuándo pedir más chunks
   (`search_more`), cuándo clarificar, cuándo cerrar. Límite 3 iteraciones.
3. **Memoria conversacional** — resumen del historial reciente del técnico.
   Resuelve "varias preguntas sobre un manual / saltar de manual a manual".

### Fase 4 — Eval orgánico + CI

1. **Tier 2 DG-grade** — curar 20-30 queries reales de los DGs desde `query_logs`,
   marcadas `verified: true`.
2. **Calibración inversa con los DGs** — que validen una muestra de veredictos del judge.
3. **CI con eval automático** — cada PR ejecuta el eval; bloquea merge si regresión.

### Fase 5 — Técnicos reales (post 1-septiembre)

1. **Tier 3 field-grade** — queries reales de técnicos en obra (jerga, voz, typos).
2. **Eval multi-turno** — diálogos de 2-3 turnos.
3. **Validación técnica de golds pendientes** — los que necesitan un técnico PCI
   (p. ej. hp004: ¿el DGD-600 a 220V es AC o DC?).

### Orden y dependencias

```
Fase 0 ──> Fase 1 ──> Fase 2 ──> Fase 3 ──> Fase 4 ──> Fase 5
(métrica)  (calidad)  (escala)   (routing)  (CI)       (campo)
   │                                                     ▲
   └── sin métrica fiable, el resto se mide a ciegas ─────┘
```

Fase 0 es prerrequisito de todo. Fase 1 antes que Fase 2 (calidad antes que
escala). Fase 3 nunca antes que Fase 1 (no tiene sentido un agente sofisticado
sobre un retrieval roto). Fases 4-5 dependen de deploy a DGs y de 1-sept.

**Refinamiento del orden Fase 0 ↔ Fase 1 (22 mayo 2026, tras la tarea #12).**
La frontera Fase 0 / Fase 1 se ordena por *dependencia de datos*, no por número
de fase. Las gold answers de la Fase 0 se generan a partir de la extracción del
corpus: generarlas sobre la extracción actual — rota, demostrado en el PoC y la
tarea #12 — las haría heredar sus puntos ciegos (contenido de diagramas y
capturas perdido). Sería repetir la lección central de la Fase 0: *un evaluador
es tan fiable como la integridad de su input*. Secuencia real:

1. **Paralelo, ya** — judge v2 *código* (cross-model, verificación de citación,
   secciones F/V) + fix del truncado. Es código: no depende del corpus.
2. **Re-ingesta** — extracción multimodal + contextual retrieval en una pasada.
   Se valida por inspección directa; no necesita el eval.
3. **Gold answers + holdout + calibración humana** — sobre el corpus ya
   re-ingestado. Se generan una sola vez, sobre datos correctos.
4. **Tuning de retrieval** (BM25+RRF, reranker dedicado, top_k split) — medido
   contra la métrica ya fiable del paso 3.

El espíritu se respeta: el *tuning de retrieval* no se toca sin métrica fiable.
Se corrige solo la imprecisión de "Fase 0 entera antes que Fase 1 entera".

---

## 5. El judge v2 — arquitectura

El judge actual evalúa "bot vs chunks F" — alcance demasiado estrecho. El judge v2
tiene **tres capas**:

**Capa A — Gold answers versionadas.** Una respuesta canónica por pregunta,
generada por un LLM fuerte **con extracción programática del PDF** (no de memoria
— el sesgo de "citar de memoria" produjo 6 errores de gold en la Fase 0),
validada por humano en muestra, almacenada con cita exacta (manual + página). Se
regeneran cuando cambia el corpus.

**Capa B — Judge operativo cross-model.** Un LLM distinto del generador y del
generador del gold. Evalúa en **dos ejes separados**:
- *Faithfulness vs chunks F* — ¿el bot fue fiel a lo que recibió?
  - Sub-capa determinista: datos duros (verify_citations.py — ya prototipado).
  - Sub-capa LLM atómica: claims cualitativos, un claim contra un chunk, temp=0.
- *Correctness + completitud vs gold* — ¿el bot dio la mejor respuesta posible?
- Y reporta **retrieval recall** por separado: ¿los chunks que el gold necesita
  estaban en F? — distingue fallo de retrieval de fallo de generación.

**Capa C — Calibración humana periódica.** Holdout split (~10 calibration / ~42
eval). Mide agreement judge↔humano. Se rehace cuando el judge cambia.

**Principio:** la fiabilidad viene del **determinismo y de la independencia**, no
del modelo más potente. La Fase 0 demostró que un LLM más capaz (Opus) con input
incompleto falla; una búsqueda de texto determinista sobre el input completo no.

---

## 6. Recomendaciones de Cowork — qué se acepta y qué se corrige

El documento `rag_improvements_recommendations.md` es sólido en diagnóstico
general. Evaluado punto por punto:

**Se acepta (converge con la auditoría):**
- Extracción de tablas mala (falsos `[TABLA EXTRAÍDA]`). → Fase 1.
- Híbrida BM25 + embeddings + reranker. → Fase 1.
- Headers semánticos + parent-child retrieval. → Fase 1.
- Recalibraciones de YAML sospechosas. → Fase 1, verificado.
- Separar evaluación de retrieval vs generación. → judge v2, Capa B.
- Cambiar la métrica primaria a agreement con humano. → Fase 0.

**Se corrige (premisa falsa):**
- ❌ Patrón "G7 — fabricación citacional", basado en hp010/hp011. La verificación
  determinista demostró 0 invención citacional. hp010/hp011 eran artefacto del
  truncado. **El patrón G7 se elimina.**
- ⚠️ Recomendación "groundedness check post-generación con Haiku" — es una variante
  del validador post-generación que **ya se probó y se revirtió** (TECH_DEBT #11i,
  net-negativo). La variante barata estructural (verificación de citación
  determinista) sí — ya está en el judge v2. La variante LLM, no.
- ⚠️ "Revertir recalibraciones de YAML" — correcto en intención, pero verificar
  SIEMPRE contra el corpus antes de revertir. hp006/cm001/cm005 verificados; el
  resto no asumir.

**Falta en el documento de Cowork (lo añade este plan):**
- Contextual retrieval (Anthropic sept 2024).
- Escalabilidad a 30+ fabricantes (todo el documento es calidad, nada de estructura).
- El prompt monolítico del generator.
- El historial del proyecto (qué ya se probó y falló).

---

## 7. Lo que NO hay que hacer (anti-patrones)

- **Validador post-generación con LLM** — ya falló (TECH_DEBT #11i). La evidencia
  dice que la alucinación no es el cuello de botella; el retrieval sí.
- **Recalibrar el YAML para "tapar" un fallo de retrieval** — sube el PASS y baja
  la calidad real. Antes de cambiar `answer → admit_no_info`, verificar el corpus.
- **Confiar en una métrica sin calibrar** contra una referencia externa al menos
  una vez.
- **Evaluar sobre representaciones intermedias** (un `.md` que puede truncarse) en
  vez de la fuente canónica completa.
- **Reescribir desde cero** — la estructura del retriever híbrido es buena; los
  cambios son ortogonales a lo que funciona.
- **Quick fixes por fabricante** — cada parche hardcoded multiplica por 30.

## 8. Principios de trabajo para las próximas sesiones

1. **Contrato BP + estructural + escalable** — toda propuesta se valida contra los
   tres criterios *antes* de proponerla, y se declara el resultado.
2. **Eval-driven** — ningún cambio se da por bueno sin medir delta. Pero la
   métrica tiene que ser fiable primero (Fase 0).
3. **Verificar la cadena entera antes de concluir** — la Fase 0 enseñó que una
   conclusión ("X falló") sin verificar el input puede ser falsa. Verificar primero.
4. **Determinismo donde se pueda, LLM solo donde haga falta** — los hechos se
   verifican con código; el lenguaje, con LLM en tareas acotadas.
5. **No legacy** — si un desarrollo no cumple el contrato, se rehace. No se
   acumula deuda para "ya lo arreglaremos".

---

## 9. Evaluación de chunks_v2 antes del SWAP (sesión 27)

> **Pivot v2→v3 (27 mayo 2026) — enfoque (a) pragmático.** Tras construir el
> aparato formal (v2: acceptance test, umbral 0.65, MDE, BCa, judge blinded),
> Alberto hizo un step-back: *"¿para qué sirve lo que estás haciendo?"*. La
> conclusión honesta: **el SWAP ya está decidido** (chunks viejo tiene bugs
> documentados), así que un veredicto estadístico no decide nada nuevo — es
> sobre-ingeniería. Además, el valor REAL producido en la sesión no fue la
> métrica sino un **hallazgo cualitativo**: el fix B5 (product_model = código
> de doc → el bot no encontraba ID3000/INSPIRE en producción, 0 chunks → 672).
>
> **v3 — el gold answers como herramienta de DIAGNÓSTICO, no como gate**:
> 1. Construir gold answers (Opus 4.7 sobre **texto completo** de los PDFs —
>    no páginas recortadas; recortar producía admit_no_info falsos, p.ej. hp020
>    pág 49 / hp006 pág 215 fuera del recorte).
> 2. Probar el bot real con chunks_v2 sobre las 19 → comparar vs gold →
>    encontrar **dónde falla** → arreglarlo (como B5).
> 3. SWAP con confianza cualitativa (shadow/canary). Sin umbral estadístico.
> 4. El gold queda como **baseline reusable** para medir mejoras de Fase 2+.
>
> Lo que se DESCARTA de v2: umbral 0.65, MDE, bootstrap BCa, permutation test,
> judge cross-model blinded, calibración Capa C formal. La comparación bot↔gold
> es cualitativa (revisión directa o judge LLM simple). El §9 v2 queda abajo
> como referencia del razonamiento (no se ejecuta).

---

### [v2 — NO EJECUTADO, referencia histórica] Pre-registro del acceptance test

**Pivot v1→v2 (27 mayo 2026)**: la v1 de §9 era un pre-registro de A/B paired
(`chunks_v2` vs `chunks` viejo). La v2 es un **acceptance test absoluto** de
`chunks_v2`. Razón del pivot: el corpus viejo tiene bugs documentados de
parsing/chunking (verificados en sesión 22 con PyMuPDF — caso hp006 Earth Fault
es el ejemplo), y la decisión de SWAP no es genuinamente binaria. El control es
un inferior conocido; comparar contra él es trabajo sin valor decisorio. La
pregunta real es **"¿supera `chunks_v2` un umbral mínimo de calidad para
producción?"**, no "¿es mejor que el viejo?". La v1 queda en historia git
(commit `fdf7d5f`) más auditoría externa con gpt-5.5 (`evals/preregistration_review_gpt-5.5.md`)
cuyos hallazgos vivos en v2 se indican inline.

### 9.1 Diseño

Acceptance test absoluto sobre N=19 preguntas hp* del eval. Sin grupo control
decisorio. Una sola condición experimental: el bot real con `chunks_v2` en
config de producción (**`hyb_new`** — el retriever real es híbrido vec+keyword).

Hallazgo vivo de v1: hp016 (B501RF) removida del set por pregunta mal
formulada (B501RF es familia de productos, no un producto único — el bot
debería pedir clarificación, pero la pregunta del eval no permite distinguir
si el fallo es del bot o de la pregunta). N=19 final.

### 9.2 Pregunta decisoria y métrica primaria

**Pregunta decisoria**: ¿supera `chunks_v2` un umbral mínimo de calidad sobre
las 20 preguntas hp* del eval?

**Métrica primaria**: `correctness` [0-1] que el judge cross-model asigna a
cada respuesta del bot vs gold answer (Capa A), promediado paired sobre N=19.

**Umbral fijado pre-run**: `lower_bound_IC95(correctness_mean) > 0.65`. No la
media observada — el límite inferior del intervalo de confianza al 95%. Esto
controla por incertidumbre con N pequeño.

### 9.3 Métricas secundarias y constraints duros

**Faithfulness** (vs chunks recuperados, no vs gold): mide alucinación.
**Constraint duro compuesto** (regla robusta a N pequeño + ruido del judge —
elegida sobre `lower_bound_IC95 > 0.85` que con N=19 exigiría media observada
~0.91, propenso a NO PASS por estrechez estadística aunque el bot apenas
aluci):
- `mean_faithfulness ≥ 0.85` sobre N=19 (la media en sí, no el límite inferior)
- Ninguna pregunta individual con `faithfulness < 0.60` (cap anti-catástrofe)

Razonamiento del 0.85 vs el 0.65 de correctness: alucinar en sistemas PCI es
worst-case (técnico puede actuar sobre info inventada → riesgo de incidente),
así que faithfulness se exige sustancialmente más alta que correctness. El
cap `< 0.60` por caso protege contra una sola alucinación catastrófica que la
media agregada podría enmascarar.

**Completitud**: cobertura de aspectos del gold. Informativa, no decisoria.

**Retrieval** (Hit@5, MRR@15): informativos. Sin guardrail formal — el GATE
de retrieval ya se ejecutó (sesión 26), confirmó dirección positiva sin
significancia.

### 9.4 Safety-critical por caso (Tier A / Tier B)

Las preguntas hp* no son equivalentes — mal responder valores numéricos /
wiring es peor que mal responder procedurales recoverables. Guardrails
individuales:

**Tier A — Safety-critical estricto** (7 preguntas). Si CUALQUIERA tiene
`correctness < 0.50` individualmente, **NO PASS automático** (bloqueo):
- `hp001` — menú programación avanzada CAD-250 (acceso indebido = romper config)
- `hp003` — wiring baterías 24V CAD-150 (voltaje crítico)
- `hp004` — tensión y consumo DGD-600 (spec numérico)
- `hp005` — programar zona ID3000 sirena (sirena mal programada = sistema no protege)
- `hp009` — resistencia fin línea Morley ZX (valor numérico)
- `hp012` — capacidad lazos AM2020 (dimensionado sistema)
- `hp014` — aislamiento línea ID2000 (wiring crítico)

**Tier B — Troubleshooting protectivo** (4 preguntas). Si CUALQUIERA tiene
`correctness < 0.40`, **REVISIÓN MANUAL** antes de SWAP (no bloqueo automático):
- `hp002` — ASD535 alarma flujo
- `hp006` — Earth Fault AFP-400
- `hp011` — RP1r post-extinción
- `hp017` — retardo salida PEARL

**Resto** (8 preguntas: hp007, hp008, hp010, hp013, hp015, hp018, hp019, hp020):
sin guardrail individual, cuentan solo en agregado.

### 9.5 Test estadístico

- Bootstrap **BCa** (bias-corrected accelerated) con 10.000 resamples, semilla
  fijada pre-run (`seed=42`). BCa elegido sobre percentile por mejor cobertura
  con N pequeño (hallazgo vivo gpt-5.5).
- Unidad de resampling: pregunta.
- Estadístico: media de `correctness` sobre N=19.
- Reporte adicional: Wilcoxon signed-rank vs 0.65 (sensibilidad — NO decisorio).

### 9.6 Reglas de decisión PASS / NO PASS

**PASS** (SWAP a shadow/canary autorizado) — conjunción de:
- `lower_bound_IC95(correctness_mean) > 0.65`
- `mean_faithfulness ≥ 0.85`
- Ninguna pregunta con `faithfulness < 0.60`
- Tier A: todas las 7 con `correctness ≥ 0.50`
- Tier B: si alguna `correctness < 0.40` → revisión manual; tras revisión, el
  PASS sigue siendo válido SOLO si Alberto autoriza explícitamente esa caída

**NO PASS** (no SWAP) si cualquiera de:
- `lower_bound_IC95(correctness_mean) ≤ 0.65`
- `mean_faithfulness < 0.85`
- Cualquier pregunta con `faithfulness < 0.60`
- Cualquier Tier A con `correctness < 0.50`

En NO PASS: identificar **dónde** falla `chunks_v2` (qué preguntas, qué chunks
se recuperan, qué dice el judge). Input para Fase 2 (mejoras de retrieval).

### 9.7 Dataset freeze + pipeline freeze

Antes del acceptance run, commit dedicado `freeze: acceptance test pre-run`
con hash sha256 de los artefactos congelados:
- `evals/baseline_v1.yaml` (post-remove hp016)
- `evals/gold_answers_v1.yaml` (output de Capa A + validación humana 100%)
- `prompts/judge_rubric.md` (Capa B — prompt y rúbrica del judge)
- Manifest del pipeline: modelo generador (`claude-sonnet-...`), prompt RAG
  (system_prompt v2.3), top-K, retriever config (hybrid), filter params,
  dedup params, fallback.
- Manifest de `chunks_v2`: count, fecha indexado, modelo embed, dimensiones.

Tras freeze, NO modificar artefactos. Cualquier cambio → nuevo freeze, nuevo
acceptance run.

### 9.8 Judge cross-model (Capa B)

- **Modelo**: `gpt-5.5` (verificado en audit externa — capacidad de razonamiento
  profundo sobre §9 v1: 40+ hallazgos vs 15 de gpt-5.2).
- **Decoding**: default (gpt-5.5 es reasoning model y no acepta `temperature=0`).
  Seed si soportado en la API. Esto introduce algo de varianza intra-run que se
  mide en calibración Capa C.
- **Blinding** (hallazgo vivo gpt-5.5): el judge **no debe saber** de qué corpus
  viene la respuesta (chunks_v2 vs vec_old exploratorio). IDs aleatorios por
  réplica, metadata anonimizada, orden de evaluación aleatorizado con seed fijo.
- **Prompt + rúbrica congelados** antes del run. Rúbrica distinta por
  `conducta_esperada`:
  - `answer`: correctness vs gold (factualidad + completitud)
  - `ask_clarification`: ¿el bot pide la clarificación correcta?
  - `admit_no_info`: ¿el bot admite y no alucina? (alucinar = correctness=0)

### 9.9 Calibración Capa C (judge vs humano)

Antes del acceptance run principal: muestra de ≥ 5 preguntas evaluadas por
Alberto + por el judge en paralelo. Métrica de agreement: ICC(2,1) sobre
correctness continuo + raw agreement sobre conducta. Si agreement < 80%,
ajustar rúbrica e iterar (máx 2 iteraciones). Si tras 2 iteraciones agreement
sigue < 80%, **bloquear acceptance run** y revisar con Alberto.

### 9.10 ITT policy (manejo de fallos)

- API error / timeout / respuesta vacía → `correctness = 0` (no exclusión post-hoc)
- Retries: máx 2 con backoff exponencial
- Logs completos: prompts, responses, judge verdicts, timestamps, model versions

### 9.11 Comparativo exploratorio `vec_old` (no decisorio)

Tras el acceptance run principal, correr el bot también con `chunks` viejo
(config `vec_old`) sobre las mismas 20 preguntas. Output: tabla por pregunta
de `correctness_new − correctness_old`. Sirve para:

- Identificar dónde `chunks_v2` mejora y dónde aún pierde
- Priorizar Fase 2 (mejoras de retrieval: HyDE / reranker / BM25+RRF)
- **NO autoriza ni bloquea SWAP** — solo input para mejoras post-SWAP

Prohibido usar este resultado para reabrir la decisión principal.

### 9.12 Si PASS — Post-SWAP en shadow/canary

`chunks_v2` no entra a 100% de tráfico al primer SWAP. Plan:

1. RENAME atómico: `chunks → chunks_old`, `chunks_v2 → chunks`. <5s downtime.
2. **Canary 10%** del tráfico durante mínimo 48h. Monitorizar:
   - Latencia p95 retrieval
   - Coste/query (Voyage embed query + Sonnet generation)
   - Tasa de retrieval vacío
   - Tickets / quejas / feedback de DG
3. Si métricas online OK → 100% gradual (25 / 50 / 100% a 24h cada paso).
4. **Rollback plan**: RENAME inverso si métricas online se degradan. Documentado.

### 9.13 Si NO PASS — Análisis y Fase 2

No SWAP. Análisis estructurado:

- Por pregunta: qué chunks recuperó el bot, qué dijo el gold, qué dijo el bot,
  qué dijo el judge
- Estratificar por: producto, fabricante, `question_type`, `conducta_esperada`
- Output: lista priorizada de mejoras candidatas para Fase 2

Re-run acceptance test tras Fase 2 (con dataset y judge congelados — no se
toca el contrato del eval, solo el sistema).

### 9.14 Enriquecimiento del eval (backlog) — Plan Y'

> **⚠️ Reconciliado (s35).** El "**Cuándo: NO ahora**" de abajo era framing de s27 anclado a
> "no bloquear el SWAP" (objetivo ya cumplido). **NO contradice** la decisión vigente de
> **crecer el ruler ahora** (bloque de estado arriba + `RULER_DESIGN §4` + `DECISIONS.md`
> DEC-003): son **dos ejes compatibles**. §9.14 = enriquecimiento **orgánico** con preguntas
> **reales** (due diligence / técnicos, #10) = ancla de realismo **futura** (aún no disponible);
> "crecer el ruler ahora" = construir el **instrumento diagnóstico** con golds sintéticos
> estratificados. Suman; §9.14 NO dice "no crecer ahora".

El eval actual es estrecho: 19 preguntas, 3 fabricantes (Detnov/Notifier/
Morley), solo PCI-detección. El scope real es 30+ fabricantes y multi-dominio.
Ampliarlo tiene sentido, pero la **calidad importa más que la cantidad**:
hp018/hp019 (sesión 27) demostraron que las preguntas sintéticas arrastran
**premisas erróneas** ("zona 1" en ZXe, "Detnov ASD" cuando es Securiton).

**Jerarquía de fuentes (mejor → peor)**:
1. **Preguntas reales de Alberto durante due diligence** — cuando evalúa una
   empresa target y pregunta al bot sobre sus productos, esa es la pregunta de
   oro: realista y alineada con el caso de uso. **Enriquecimiento orgánico**:
   capturar esas queries (query_logs) → casos de eval. Cobertura dirigida por
   el negocio, no aleatoria.
2. Queries reales de técnicos PCI (cuando existan).
3. Sintéticas con Opus 4.7 sobre PDFs (cobertura amplia, baratas) — requieren
   **validación de premisa**: patrón anti-circular = Opus extrae fragmento +
   genera pregunta → modelo distinto (o Alberto) valida que la pregunta es
   correcta y respondible → Opus genera gold. Validación humana por sampling
   estratificado (no 100% — no escala).

**Cuándo**: NO ahora (no bloquea el SWAP, que es el objetivo inmediato).
Tras el SWAP, conforme Alberto use el bot. El pipeline de gold (Capa A,
`scripts/layer_a_build.py`) ya permite generar pregunta+gold barato cuando se
quiera cubrir productos de una target concreta.

**Norma**: ningún caso nuevo entra al eval sin validar su premisa — la lección
de hp018/hp019 es que una pregunta mal formulada contamina la medición.

---

## Changelog

- **22 mayo 2026** — Documento creado. Consolida auditoría inicial + calibración
  Cowork + hallazgos de Fase 0 (bug de truncado, verificación documental,
  verificación de citación 100% en datos duros).
- **22 mayo 2026** — Añadido a la Fase 1: diagnóstico del corpus (1.208 PDFs, 47%
  con carga visual densa, ~188 duplicados) y las 6 decisiones de diseño del
  pipeline de re-ingesta, incluida la política de idiomas.
- **22 mayo 2026** — Añadido el resultado del PoC de extracción: baseline a
  sustituir (pierde espacios, falsea tablas), LlamaParse en modo multimodal como
  stack elegido (pendiente confirmar modo multimodal — tarea #12).
- **22 mayo 2026** — Tarea #12 cerrada: confirmado el modo multimodal de
  LlamaParse (`parse_page_with_lvm`) como stack de extracción. Salvedad: en
  diagramas de flujo el VLM alucina (notas inventadas, etiquetas mal leídas),
  verificado contra las páginas reales — la "doble vía" texto+imagen pasa de
  recomendada a obligatoria.
- **22 mayo 2026** — §4: refinado el orden Fase 0 ↔ Fase 1 — secuenciar por
  dependencia de datos. La re-ingesta precede a las gold answers (que heredarían
  los puntos ciegos de la extracción si se generan antes). El judge v2 *código*
  va en paralelo; el tuning de retrieval sigue esperando a la métrica fiable.
- **22 mayo 2026** — Fase 1: fijada la arquitectura del pipeline de re-ingesta
  (dos etapas con frontera duradera) y el modelo de embedding (Voyage
  `voyage-4-large` @1024, con dimensión-contrato y abstracción de proveedor).
  Arranca la construcción por la Etapa A1 (inventario + dedup nivel 1).
- **22 mayo 2026** — Fase 1: coste de extracción medido (dashboard LlamaParse):
  estándar 3 créd/pág, agéntico 45, `lvm` 60. **`lvm` descartado** — dominado
  por el modo agéntico (mejor calidad verificada *y* más barato). Modo de
  extracción fijado = `parse_page_with_agent`; presupuesto realista ≈$1.150
  (no $250-500). El modelo VLM se decidirá con un probe representativo (~150
  págs) — los single-runs de 9 págs no son base fiable. Construido el módulo
  A2/A3 (`src/reingest/extract.py`).
- **22 mayo 2026** — Probe cerrado, decisión de extracción fijada: **agéntico en
  todo el corpus** (`parse_page_with_agent`), ≈$1.150 pago único. Se exploró y
  descartó el enfoque por niveles (estándar barato + agéntico solo en lo
  difícil): verificado que el modo estándar **corrompe silenciosamente** las
  tablas de marcas ✓ — la VESDA Tabla 7-1 salió con 0/7 marcas y confianza 0,96
  (parece correcta, es falsa); el agéntico, 7/7. Los fallos silenciosos no los
  caza ningún router barato (confianza, word-salad, agregación por documento —
  los tres fallan en pruebas). Para un corpus de seguridad, agéntico-en-todo es
  la única opción sin errores silenciosos. El run completo requiere plan de pago
  de LlamaParse (supera el free tier de 10k créd/mes).
- **22 mayo 2026** — Cierre de sesión 22. Alberto contrató el Plan Pro de
  LlamaParse → run de extracción completo desbloqueado. Próxima sesión: lanzar
  el run agéntico completo (background, resumable) + construir la Etapa B
  (idioma, chunking, contextual retrieval, embed Voyage + HNSW `chunks_v2`).
- **22 mayo 2026** — Sesión 23. (1) **Run de extracción A2 lanzado** en
  background (resumable; verificados antes los 15 archivos ya extraídos —
  agéntico `premium`, markdown con headers, tablas limpias). (2) **Etapa B
  construida entera** — `migrations/006_chunks_v2.sql` + 8 módulos en
  `src/reingest/`: `language` (B1/B2), `chunk` (B3/B4), `metadata` (B5),
  `dedup` (B6), `contextualize` (B7), `embed`+`index` (B8) y `pipeline`
  (orquestador, estado por archivo, re-ejecutable). Validada: dry-run completo
  sobre lo extraído (0 fallos), contextualize probado con llamada real a Haiku
  (blurbs correctos), language/chunk/metadata/dedup con pruebas unitarias.
  Cumple el contrato BP+estructural+escalable; gaps declarados abajo.
  Refinamientos de diseño hechos durante la construcción:
  · **chunk.py — headers como cortes BLANDOS, no duros.** Un corte por cada
    header fragmenta los spec-sheets en decenas de chunks inservibles (medido:
    845→445 chunks al pasar a acumulación por tamaño). Las secciones minúsculas
    se acumulan; subir en la jerarquía (header más somero) sí corta siempre.
  · **B6 (dedup) corre POST-embed.** El orden del diagrama (B6→B7→B8) no es
    implementable: el dedup semántico necesita los embeddings. Orden real
    B7→B8→B6→index. El marcado no destructivo (`duplicate_of`) hace el orden
    flexible.
  · **migración 006 FASE D — el SWAP también reemplaza las RPC.** El plan decía
    "las RPC siguen válidas sin tocarse": cierto para las referencias por
    nombre de columna, falso para la dimensión del embedding (1536→1024). El
    SWAP hace DROP+RENAME de `match_chunks`/`search_chunks_text` a sus versiones
    `_v2`. El código Python del retriever sigue intacto.
  · **`chunks_v2` es superconjunto de `chunks`** — el retriever selecciona
    columnas por nombre vía PostgREST, así que el swap por RENAME es
    transparente sin tocar `retriever.py`.
  · **A3 store local** (`data/extraction/`), no Supabase Storage — decisión de
    la sesión 22; durable igualmente (carpeta sincronizada), más simple.
  **Gap declarado:** B5 (metadata) es la *interfaz* de Fase 1 — la detección de
  modelo/fabricante es aproximada (regex compacta + mapa de prefijos); da falsos
  positivos en filenames que son números de catálogo. La precisión es la
  externalización a YAML de la Fase 2; no es un quick-fix pendiente, es el
  alcance que el plan asignó a B5.
  **Bloqueantes del run real de la Etapa B:** (a) falta `VOYAGE_API_KEY` en
  `.env` — solo la necesita B8; (b) aplicar `migrations/006_chunks_v2.sql` en el
  SQL Editor de Supabase; (c) que termine la extracción.
  **Próxima sesión:** dejar terminar la extracción (~1-2 días, resumable) →
  aplicar migración 006 + añadir Voyage key → `python -m src.reingest.pipeline`
  → GATE (recall de las 52 preguntas sobre `chunks_v2`) → SWAP (FASE D).
- **22 mayo 2026** — Sesión 23 cierre, dos refinamientos:
  · **Alcance fijado** — Alberto: extraer todo el corpus; **Morley dentro del
    alcance de calidad y validación** (no se filtra nada; pipeline ya lo
    procesa). Composición real del corpus medida: Notifier 70% (14.430
    páginas), Morley 17% (3.457), Detnov + marcas especiales 13% (2.599).
  · **Gap de atribución marca/distribuidor cerrado** (§2.3, Securiton/VESDA).
    Mapeo cerrado con Alberto vía datasheets, encodeado en B5: **Securiton**
    (ASD/ADW/ART), **Xtralis** (VESDA — Notifier la comercializa),
    **Pfannenberg** (PA/DS/PY-X), **Argus Security** (SG*), **Pepperl-Fuchs**
    (Z728 estricto — Z-200-R de Detnov NO cae aquí), **Spectrex** (SharpEye
    40-40/20-20), **SenseWare** (210-Series UV/IR); todos con distribuidor
    Detnov salvo VESDA (Notifier). FireBeam y Signaline corregidos a Detnov
    (eran marcas propias, no terceras como había puesto inicialmente).
    Patrones por regex de modelo específico con guards anti-falsos-positivos
    ("2020" año, "DS-00000-00", "Z728_installation"). Añadida columna
    `distributor TEXT` a `chunks_v2` + ambas RPC — semilla del "campo separado
    marca/distribuidor" que el plan tenía para Fase 2, traída ahora para que
    `chunks_v2` nazca con la atribución completa y no requiera migración
    futura. Validado sobre los 105 docs ya extraídos: Securiton/Pfannenberg/
    Argus/Pepperl-Fuchs/Spectrex con marca y modelo limpios. La reconciliación
    del retriever (su MODEL_PATTERN sigue clasificando ASD como Detnov) sigue
    siendo Fase 2 por diseño — junto con la externalización a YAML.
  · El proceso de extracción cayó a las 104 imágenes (causa no identificada,
    log se había quedado vacío por buffering); re-lanzado con `python -u` para
    que el log capture progreso en tiempo real. Resumable como diseñado.
- **23-24 mayo 2026** — Sesión 24, ejecución de la Etapa B end-to-end. Alberto
  añadió `VOYAGE_API_KEY` y aplicó `migrations/006_chunks_v2.sql`. Pipeline
  arrancó, sobrevivió 9,5 h y crasheó al doc ~99 por `PermissionError` de
  Windows/OneDrive sobre `_save_json` (race del sincronizador con `os.replace`
  atómico); patch retry-on-PermissionError en `_save_json`, re-lanzado. Otros
  2 docs (50253SP, MIDT170) crashearon con 409 Conflict de PostgREST sobre
  `chunks_v2.duplicate_of_fkey` (root cause = FK violation: B6 marcaba un
  chunk como duplicado de otro que aún no había entrado por orden de batch);
  patch en `index.py` ordena `duplicate_of IS NULL` primero antes de los
  marcados. **Pipeline completo: 22.849 chunks indexados, 915 docs done, 44
  register-only, 6 empty, 0 fallos finales.** 2 PDFs corruptos legacy (RC4
  encryption muy vieja) aceptados como pérdida (`MADT731_03_A`, `MNDT710`,
  deprecado per Alberto). Voyage `voyage-4-large` confirmado nativo 1024 (no
  hace falta `output_dimension`; el SDK 0.2.4 no lo expone igualmente). B6
  post-index dedup (`dedup_pass.py`) ejecutado sobre los 21.575 chunks no
  marcados: **1.286 duplicados intra-producto cross-archivo marcados** (~11%
  del corpus, mayoría ES/EN equivalentes). Listo para el GATE.
- **24-25 mayo 2026** — Sesión 25, **diseño y construcción del GATE** (Bloques
  A y B troceados):
  · **Bloque A — definición:** métrica = Hit@5 (primaria) + Recall@5 +
    Recall@15 + MRR@15, con bootstrap IC95% para "delta significativo" en
    lugar de un umbral pre-comprometido (más honesto estadísticamente).
    Criterio SWAP = **2 pisos**: piso 1 GATE-recall + piso 2 mini-judge sobre
    ~12 preguntas con mayor `|delta_recall|`. Revertido hp006 a `answer` (el
    único caso verificado de recalibración mal hecha — `cm001`/`cm005` son
    política deliberada). Política cross-brand DIFERIDA a post-SWAP.
  · **Bloque B — mecánica:** retrieval medido = vector puro + híbrido completo.
    Chunks relevantes identificados con Sonnet (NO Voyage para evitar el
    "evaluador y evaluado misma vara"). Brute-force: TODOS los chunks del
    producto, Sonnet juzga cada uno (~5.000 calls, ~$15). Eval-B paralelo
    diferido junto con política cross-brand. Script GATE pendiente
    (`scripts/gate.py`) con git SHA + eval hash + caché de query embeddings +
    bootstrap IC95.
  · **B5 fix expuesto por el GATE** — la creación del gold reveló que B5 no
    detectaba ZXe/DXc/PEARL/INSPIRE/AgileIQ (sin dígitos) ni B5xx (Notifier);
    pattern añadido `_LETTER_MODELS` (filename-only para evitar FP por menciones
    en content) + `_FILENAME_ONLY_PATTERNS` para B5xx + blacklist
    `_NON_PRODUCT_CODES` (EN-54/NFPA-72/IP-65/CEM-2004 ya no contaminan) +
    normalización underscore→espacio antes de `\b`. Script
    `update_product_models_v2.py` re-aplicó B5 sobre `chunks_v2`: **214 docs
    actualizaron metadata** (176 mejorados + 38 NULL→atribuido). El fix es
    estructural-en-su-alcance, no parche; la externalización completa a YAML
    sigue siendo Fase 2 (T17 task pendiente).
  · **B.2 cross-validación con Opus** (judge v2 Capa B): Opus 4.6 juzgó las
    mismas 1.768 decisiones de Sonnet (100% positives + 100% negs de las 8
    `no_relevant_in_candidates` + 30% random del resto), $23, 14 min. **Raw
    agreement 95,1%, Cohen's κ = 0,56 (moderada)**. Asimetría clara: 78
    chunks que Sonnet rechazó pero Opus considera relevantes (false negatives
    de Sonnet) vs solo 8 al revés. Concentración en `hp016` (12/15
    disagreements — sospecha fuerte) y `hp011` (25/90). 86 disagreements en
    `evals/gate_validation_disagreements.md` formato side-by-side para
    revisión humana.
  **Capa A (Opus + PDFs originales) DIFERIDA a post-SWAP**, tal como el plan
  §4 (refinamiento Fase 0/1) prescribe: gold answers deben generarse "sobre el
  corpus ya re-ingestado", no antes. T17 (Fase 2 YAML) también post-SWAP.
  **Próxima sesión:** Alberto revisa los 86 disagreements (45-60 min offline,
  empezar por hp016+hp011 — si el patrón está claro, calibrar velocidad) →
  merge sus decisiones en `gate_relevant_chunks.json` → construir
  `scripts/gate.py` (T13) y `scripts/gate_judge.py` (T14) → ejecutar GATE
  end-to-end (T15) → verdict SWAP basado en piso 1 + piso 2.
- **26 mayo 2026** — Sesión 26, revisión humana de disagreements del GATE en
  curso (hp001-hp003 cerrados, hp004+ pendiente). Calibración del criterio y
  dos hallazgos estructurales:
  · **Criterio fijado: PROCEDURAL PURO.** SI si el bot citaría el chunk para
    construir alguna parte de la respuesta al técnico; NO si tangencial,
    producto distinto o apuntador sin contenido propio. **Rigor de dominio
    (corregir valores imprecisos) DIFERIDO a Capa A** (gold answers post-SWAP
    con técnico PCI real). En esta capa medimos retrieval recall, no answer
    quality — confundir ambos cosas inflaría falsos NO. Caso pivote registrado
    en `evals/gate_validation_disagreements.md`: hp004 `bf78e1db-f87` (chunk
    DGD-600 dice "24V o 220V"; rango real 22-38V/180-240V — procedural=SI,
    rigor de dominio=NO; resuelto SI, anotado para Capa A).
  · **Bug detectado y parcheado: `cross_validate_relevance.py:311`** truncaba
    el render del .md a 1500 chars mientras Sonnet/Opus juzgaban sobre 4000
    (`MAX_CHUNK_CHARS`). La revisión humana operaba con menos información que
    los LLMs — gap silencioso, manifestación nueva de la lección Fase 0
    "verificar contra la fuente canónica completa". Detectado por Alberto al
    notar que Sonnet citaba "BAT" en hp003 #2 sin que él lo viera. Parche:
    `[:1500]` → `[:MAX_CHUNK_CHARS]`. Script `scripts/expand_disagreements_md.py`
    creado para regenerar el .md preservando decisiones humanas ya tomadas
    (chunk_ids estables, fetch a Supabase, reemplazo inline con assert de
    preservación de decisiones/comentarios).
  · **Follow-ups de Fase 1 detectados** durante la revisión humana, registrados
    en cabecera del `.md` para no bloquear el GATE: (a) `page_number` off-by-2
    sistemático en docs CAD-150 (bug del chunker B3); (b) chunks ES/EN
    equivalentes no marcados `duplicate_of` (gap de B6 dedup semántico — caso
    hp003 #1↔#6 CAD-150 Cautions 1.2); (c) chunk con header de siguiente
    sección sin contenido (edge del corte por tamaño en B3).
  · **Alcance del GATE inicial fijado**: las 13 decisiones cross-manual `cm*`
    (cm002 × 5, cm003 × 2, cm004 × 5, cm005 × 1) **NO entran** en esta pasada
    — alineado con "política cross-brand DIFERIDA a post-SWAP" del Bloque A.
    3 de 4 son `admit_no_info` (decidir relevancia no aporta señal); la única
    `answer` (cm002, migración AFP-200 → ID3000) también es cross-brand. Se
    retomarán bajo Capa A del judge v2 con técnico PCI real. El GATE inicial
    arranca con 73 chunks sobre 17 preguntas hp*.
  · **T12 — Merge de decisiones humanas ejecutado**: 19 chunks añadidos (Sonnet
    NO → Alberto SI, casos de falsos negativos de Sonnet), 3 quitados (Sonnet
    SI → Alberto NO), 51 no-op. Re-evaluación de verdicts: hp018 sube a
    `relevant_found` (0→1), hp019 baja a `no_relevant_in_candidates` (2→0). 5
    de 19 preguntas answer-type quedan como `admit_no_info` de facto tras
    revisión humana (hp012, hp013, hp014, hp016, hp019) — corpus no documenta
    troubleshooting de baterías B501RF, extinción RP1r post-descarga, etc.
    Hallazgo del proceso valioso (post-SWAP: actualizar `baseline_v1.yaml`).
    Output: `evals/gate_relevant_chunks.json` (85 relevant_chunks tras merge)
    + `evals/human_review_audit.json` (log detallado). Script:
    `scripts/merge_human_decisions.py` (idempotente, con assert/backup).
  · **T13 — gate.py implementado y ejecutado**: 4 configs (vec_old, vec_new,
    hyb_old, hyb_new) sobre 11 preguntas con relevant_chunks>0, bootstrap
    IC95 paired por pregunta, sin HyDE. **Match doble strict+loose** (sesión
    26): strict por chunk_id válido solo dentro chunks_v2; loose por
    (source_file, page_number) para cross-tabla (chunks viejo OpenAI 1536 vs
    chunks_v2 Voyage 1024 tienen IDs distintos tras re-chunking). Filtro
    `filter_product` aplicado en RPCs (crítico: sin él, vec trae chunks de
    manuales temáticamente similares en vez del producto correcto). Script:
    `scripts/gate.py`.
  · **Resultados del GATE base (n=11)**: chunks_v2 supera direccionalmente a
    chunks viejo en TODAS las métricas, **pero ninguna alcanza significancia
    estadística** (IC95 cruza 0). Hit@5 loose: 0.273 → 0.364 (+0.091
    IC95=[-0.18, +0.36]); MRR@15: 0.169 → 0.318 (+0.149 IC95=[-0.03, +0.38]).
    **Verdict piso 1 = NO PASS estricto** por n bajo (no por delta cero).
    Strict para vec_new (0.364) ≈ loose (0.364) — cuando vec_new trae chunk
    de página relevante, suele ser el chunk_id exacto del gold (señal de
    buen chunking en chunks_v2). Recall absoluto bajo (~36% hit@5) — espacio
    para tuning post-SWAP (HyDE/reranker/BM25+RRF). Output:
    `evals/gate_results.json`.
  · **Auto-crítica del método y descubrimiento de contradicción en el plan**:
    tras 4 rondas de "¿hay más gaps?" empujadas por Alberto, identificado
    que (a) Plan B+ matriz 2×2 NO atacaba causa raíz (n=11) y (b) Plan Y
    (ampliar eval) era mejor pero seguía midiendo proxy débil (Hit@5 vs
    gold-relevance) en vez del kpi real (calidad de respuesta del bot). (c)
    Descubierta **contradicción interna del plan**: §4 (refinamiento Fase
    0/1, 22 mayo) dice Capa A va paso 3 ANTES del tuning (paso 4); §6
    cierre sesión 25 dijo "Capa A DIFERIDA a post-SWAP". §4 era el orden
    correcto. La razón del diferimiento ("gold sobre corpus re-ingestado")
    no aplica — chunks_v2 ya existe, solo no está en producción; Capa A
    se puede hacer hoy sobre chunks_v2.
  · **Plan Z fijado para próxima sesión — orden correcto del plan §4**:
    1. Construir **Capa A** (gold answers para las 17 preguntas hp*) con LLM
       strong (Opus) + extracción programática del PDF (no de memoria —
       lección Fase 0 sobre los 6 errores de gold de Cowork por citar de
       memoria) + validación humana de Alberto al 100% (con N=17 es
       factible, BP estadística). Coste ~3-4h tu tiempo + ~$5 API.
    2. Extender **judge v2 Capa B** con métricas de calidad de respuesta
       (faithfulness vs chunks F + correctness vs gold + completitud).
       **Judge cross-model: tercer modelo distinto del generador del bot
       (Sonnet) y del generador del gold (Opus)** — plan §5 explícito.
       Candidatos Mayo 2026: GPT-5, Gemini 2.5 Pro, Mistral Large. ~2-3h.
    3. **Re-correr GATE** midiendo Δ_quality (no solo Δ_retrieval). Las
       métricas de calidad numéricas continuas tienen menos varianza que
       hit@5 binario → más potencia con el mismo n=11. ~1h run.
    4. **Decidir SWAP** basado en Δ_quality + Δ_retrieval combinados, con
       MDE pre-comprometido antes de mirar resultados (BP de A/B testing,
       evita p-hacking) — definir en próxima sesión.
  · **Gaps materiales declarados (no bloqueantes, atención requerida)**:
    (a) chunks_v2 readiness — B5 metadata aún tiene falsos positivos en
    filenames numéricos; flow diagram coverage no auditada; blurbs B7 sin
    sampling de calidad. (b) Judge cross-model — falta decidir tercer
    modelo concreto. (c) Sample size validación humana — fijado en 100%
    para N=17 (vs ambigüedad del plan §5 "en muestra"). (d) Proxy
    fundamental — sin técnico real, todo es proxy; Capa A es mejor proxy
    que Hit@5 pero limitado. (e) **Plan Y (ampliar eval con queries reales
    de query_logs) queda en backlog** por si tras Plan Z el delta sigue
    cruzando 0 — usar query_logs es BP (no sintéticas).
  · **Gap META del método**: mi auto-crítica fue REACTIVA (gaps declarados
    en iteraciones 2-4 cuando Alberto preguntó "¿hay más gaps?"), no
    PROACTIVA como prescribe la norma de memoria personal *"declarar gap
    honestamente sin esperar pushback"*. Patrón observado: cada propuesta
    inicial decía "los pasos pasan el contrato" pero no declaraba riesgos
    obvios (strict vs loose match, n=11, contradicción §4/§6) hasta
    iteraciones posteriores. **Compromiso para próxima sesión y siguientes:
    declarar gaps en la propuesta inicial, sin esperar pushback.** El
    sistema no debe depender de Alberto como anti-bias humano.
