# HISTORY — Technical Bot (traza histórica del PLAN)

> Fichero histórico **append-only**, extraído de `docs/PLAN_RAG_2026.md` en s56 (DEC-036) para
> compactar el PLAN (el log de estado crecía ~1 párrafo denso por sesión y el doc llegó a 123KB
> releídos en cada arranque de sesión). Aquí viven: (1) el **log de sesiones s30→s55**, (2) el
> **rationale histórico de mayo 2026** (secciones 1-9 del PLAN original, SUPERSEDED — la numeración
> original se conserva para que las citas antiguas tipo "PLAN §9.14" o "§660" resuelvan aquí),
> (3) el **changelog** original.
>
> **El estado vigente y el rumbo viven en `docs/PLAN_RAG_2026.md`** — si discrepan, manda el PLAN.
> Desde s56, el cierre de sesión apendiza el RESULTADO de cada sesión al final del log de abajo.

## Log de sesiones (s30 → s57d)

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
> - **RESULTADO s52b (eval — `DECISIONS.md` DEC-031): expansión del eval dirigida al A/B (context→generator), +5 golds (ruler 30→35); round PARCIAL cerrado en PR #49 (decisión de Alberto).** Continuación de DEC-028. Diana = diversidad estratificada para el primer A/B-lever (NO volumen; content-pobre POST-HOC). **Gate del dúo sobre la selección** (cross-model 11/10/0-FP; reshape adoptado: cortada la triplicación battery). 5 golds SERIAL por `RULER §2`: cat016 CAD-150 multi-doc · **cat017 INSPIRE** multi-doc (lazo OPAL + CLSS + licencia CLIP, producto nuevo) · **cat018 AM-8200** síntesis (CBE causa-efecto, no-battery, producto nuevo) · cat019 CAD-250 síntesis (maniobra) · cat020 DXc multi-doc (override mercado España 80/100/108%). **Auto-catch**: DXc pivotó de causa-efecto (que era el 3er clon de patrón) a market-override. **Smoke (chunks_v2): 1 PASS / 3 PARCIAL / 1 FALLO** → los golds DISCRIMINAN la diana del A/B (sub-retrieval multi-doc + incompletitud síntesis + 1 contradicción del bot). **Fix del dúo** (regla de SIMETRÍA: pasar las fuentes al cross-model) + borrados `AGENTS.md`/`.codex/` (artefactos de Codex). 35 golds, 200 tests. `feedback_my_bias #26` (recaí en #24 turnos-sin-ejecutar; + auto-catch del over-index). **PENDIENTE (sesión fresca)**: refuerzos n=1 + held-out embargado + es-en → hacia 10-15; consolidación §8/PREREG; luego el A/B context→generator. Canónico **DEC-031**.
> - **RESULTADO s55 (8 jun 2026 — `DECISIONS.md` DEC-032): Detnov CAD-201 + CAD-201-PLUS (serie Vesta), INGESTA DIFERIDA.** 2 centrales más de la serie Vesta. **Dedup fuerte** ("solo lo que no tengamos"): CAD-201 y CAD-201-PLUS linkan los mismos 5 PDFs, 2 ya teníamos (config/software CAD-250 de CAD-171) → solo **3 nuevos** (datasheet ES+EN + instalación MI-715); CAD-201-PLUS sin docs propios. Parse 3/3 OK (~$3; los 2 config saltados por SHA). Inventario: APPEND a hoja Detnov → 112 prod / 134 docs. **INERTE**: ingesta DIFERIDA. Worktree off main (#49). Rama `corpus/detnov-cad201`. Canónico **DEC-032**.
> - **RESULTADO s53 (eval — `DECISIONS.md` DEC-033): consolidación §8/PREREG (gate DURO pre-A/B) CABLEADA + batch dirigido (3 golds); round PARCIAL en PR #52.** (Numeración: DEC-032 lo tomó el corpus s55 en paralelo → esta consolidación del eval = DEC-033.) Cerrado el gatillo duro de DEC-031: la **taxonomía de estratos quedó CONGELADA** (el A/B la lee = freeze-contract). **Decisión taxonómica (catch del dúo):** `tabla-matriz`/`scan-ocr`/`diagrama` DEMOTADOS de AUTORÍA a **POST-HOC** (completa lo que DEC-025b dejó diferido; §2:156+§7:412 los enrutan al lever de extracción = post-hoc). Discriminador limpio: **AUTORÍA = fallo cognitivo fuente-puro; POST-HOC = causa de extracción**. PREREG des-bloqueado (sin pre-selección content-pobre; hipótesis reformulada; PASS-control sub-contrato). **Dúo ×2 (Protocolo 3, zona de dolor):** consolidación NO-SÓLIDA→corregida (D2 era reapertura encubierta de DEC-025b) + selección NO-SÓLIDA convergente — **cazó 2 candidatos ENVENENADOS antes de autorar** (AFP-300 sin manual=bug AC-220; VEP síntesis-falsa=delegada a software ASPIRE). **3 golds (35→38), SERIAL `RULER §2` (render+doble-señal Claude+GPT):** cat021 clarify Spectrex 40/40 (**fabricante NUEVO**) · cat022 answer Spectrex 40/40L vs L4 · cat023 answer Securiton ASD532 (EN 54-20). **Hallazgo honesto (localize-first):** la **síntesis genuina es corpus-escasa** (3 candidatos post-gate → 0 genuinos) → estrato del A/B topado ~n=3 (declarado, como es-us). **Corrección de Alberto:** reclasificar (no tirar) los candidatos cuya dimensión CLAIMED no aguanta → Spectrex/ASD532 a `answer` (mi sesgo #23 over→under). 200 tests, 0 errores. `feedback_my_bias #27`. **PENDIENTE**: batch hacia ~10-12 (conflicto-revisión + breadth ES + oem verificado; síntesis topada ~3); held-out embargado; luego el **A/B context→generator** (PREREG ya reconciliado). Canónico **DEC-033**.
> - **RESULTADO s54 (eval — `DECISIONS.md` DEC-034): memoria consolidada (durable) + 1 gold conflicto-revisión (cat024 MAD-472), ruler 38→39; el dúo tumbó mi over-claim de breadth y la dimensión topó por corpus.** Arranque: **consolidación de memoria** — `MEMORY.md` (índice cargado cada sesión) reventaba el límite 24KB (28.8KB) por apilar el log de sesiones DENTRO de la línea del índice → colapsado a one-liners (28.8→2.6KB) + migrado el detalle a los topic files (sin pérdida; trampa cazada: s52/s52b vivían SOLO en el índice) + **guard de raíz en `CLAUDE.md` cierre** (índice = 1 línea/memoria, nunca apilar) para que no recurra. **Selección source-first + gate del dúo** (Protocolo 3, zona de dolor): 2 candidatos → **MAD-472** (sirena Detnov, conflicto-revisión: consumo en alarma `<15 mA` V1 → `17 mA` V2, mismo doc `55347200` mismo idioma, **cuádruple-verificado**: fitz + chunks_v2 SQL + render píxel 400dpi + digital-native) y **LDA BA Series** (breadth-ES). **El dúo CONVERGENTE (sub-agente + cross-model, 0 FP) tumbó el LDA**: lookup de viñeta limpia sin modo de fallo = el patrón s52 "diluir donde el bot es fuerte" + split held-out invertido + mi framing "breadth=robustez-fabricante" = racionalización (`feedback_my_bias #28`, over-claim de framing convergente). **Yo cacé la vice-remediation del sub-agente** ("reformula LDA a `tabla-matriz`" = chunks_v2-peeking, s50). **Pregunta de Alberto sobre el protocolo (respondida):** SELECCIÓN+autoría = desde la FUENTE; chunks_v2 SOLO para existencia (§2.1) + verificación regla C, NUNCA criterio de selección. **Instinto de Alberto (más conflictos Detnov) → scout source-first de doc-codes Detnov:** **MAD-472 es el ÚNICO par limpio** (PAD-10/10A = rename sin value-diff; Zócalo/FAD-905 `_V2` sin base en corpus) → **conflicto-revisión es corpus-limitado (2 golds: cat009+cat024)**, confirmado DESDE LA FUENTE (no por no mirar). **cat024 autorado** (vía `gold_store.upsert`, 0 errores esquema, 200 tests) + **smoke chunks_v2 = PASS** (el bot resuelve el conflicto: trae ambas revs, da 17 mA latest + surfacea la discrepancia → no cazó bug; dato diagnóstico legítimo + **PASS-control** para el A/B; reforzó conflicto-revisión n=1→2). **Convergencia: breadth Y más-conflictos → MISMO lever = ENRIQUECER EL CORPUS** (ingestar Kidde/Aritech a `chunks_v2`; el corpus guardó mayormente la última revisión → más conflictos vivos llegarían con la ingesta). **PENDIENTE**: lever de **ingesta Kidde/Aritech** (breadth 30+, con Protocolo 2 — el cuello real de breadth, no el conteo de golds); held-out embargado; luego el **A/B context→generator**. 39 golds, rama `eval/s54-golds-batch`. Canónico **DEC-034**.
> - **RESULTADO s55 (corpus — `DECISIONS.md` DEC-035): identidad de producto DATA-DRIVEN (Capa A+B del seam Fase 2) — habilita la ingesta sin envenenar el corpus; ingesta DIFERIDA al merge (PR #54).** El lever de ingesta (DEC-034) arrancó con un **dry-run de atribución B5 (sin gastar API)** que cazó que ingestar los 103 docs nuevos tal cual **envenena el corpus**: `manufacturer=None` 95/103 + `product_model` basura (`HASTA-256`/`REV-005`/`EN-54-20`). Causa raíz: `metadata.py` marca sus tablas **"SEAM FASE 2"** (Kidde/Aritech/Edwards no existen). Alberto cuestionó mi parche → rediseño estructural. **El dúo (R1) tumbó mi Capa C (esquema `product_models[]`)**: reabría TECH_DEBT #18 (diferido); el multi-modelo es #43 (series, eval-driven) → **DIFERIDO**. **Construido A+B**: Capa A = tablas→`config/manufacturers/*.yaml` + `manufacturer_registry.py` (equivalencia 1068 docs 0-diffs); Capa B = `sidecar.py` lee el `_metadata.json` del portal (`equipo`→modelo real, OEM override `2X-A`→Aritech verificado por cross-listing). Resultado: 0 basura, 965 viejos 0 regresiones, OEM correcto. **Dúo R2 (impl, 0 FP)**: path robusto + validación config + alarma fallo-abierto + golden como test. **PR #54 MERGEADO** (commit `8866877`) + **ingesta EJECUTADA**: `chunks_v2` 22.849→**25.090** (+2.241); Aritech 43 docs/Kidde 33/Edwards 3 con identidad correcta (`2X-A`→Aritech OEM, **0 basura**, 6 PT descartados por idioma); catálogo re-construido 536→**587 modelos**; **smoke de retrieval OK** ("2X-A"→26 chunks Aritech del manual real, "FHSD8310"→Edwards). 3 muertes del proceso por suspensión tapa/batería (idempotente+reanudable, 0 pérdida). Rama `corpus/s55-ingest` → PR. **PENDIENTE: held-out embargado + A/B context→generator** (el corpus enriquecido habilita más conflictos-vivos + breadth). Canónico **DEC-035**.


> - **RESULTADO s56 (10 jun 2026 — `DECISIONS.md` DEC-036): revisión estructural end-to-end (estreno de Fable 5 como asistente) — rumbo CONFIRMADO sin overhaul; §H ejecutado; gate de atribución ANTES del factor modelo; reviewer pin fable; corpus pospuesto.** Reconocimiento por 3 sub-agentes + propuesta + **dúo completo ANTES de presentar** (sub-agente 10/10 + cross-model 8/8, 0 FP; cazó mi bias #20 reincidente: "residual=generación" era over-claim con atribución STALE pre-s55 y sin baseline de los 39). Firmas de Alberto (4/4): **(1)** docs §H YA: PLAN 123KB→~6KB compacto + historial íntegro a `docs/HISTORY.md` + ARCHITECTURE banner→puntero (81→60KB) + TECH_DEBT índice de estado (✅ #16/#38; sin renumerar) + 64 logs a `evals/archive/` + borrados validator.py/test_validator.py/logs-raíz (dedup.py NO: vivo — bite del dúo); **(2)** rumbo levers: s57 held-out → s58 GATE de atribución (baseline K=5 de los 39 = PASS-control del PREREG + audit context-sufficiency + instrumentar stop_reason) → s59 lever según gate (generación → A/B 2×2 {Sonnet,Opus 4.8}×{blurb OFF,ON} pre-registrado, endpoint GLOBAL, Batches −50%; sub-retrieval → lever retrieval, Opus no se toca); **(3)** corpus POSPUESTO hasta cerrar el ciclo (freeze-contract); **(4)** reviewer `model: fable` (hipótesis con seguimiento per-model en tally; cross-model INNEGOCIABLE en ALTO/dolor; ronda nueva = agente fresco). Verificados de paso: contextual-retrieval 100% post-s55 (25.090/25.090); tally real del dúo 98.5% confirmados / 1.1% FP (75 reviews); Detnov CAD-171/201 SÍ ingestados (doc-trace de DEC-035 incompleto). `feedback_my_bias` #29. Canónico **DEC-036**.

> - **RESULTADO s57 (10 jun 2026 — `DECISIONS.md` DEC-037): held-out embargado POBLADO — selección gateada por el dúo (11+2 reservas) + primeros 2 golds `ho` + criterio de confirmación PRE-REGISTRADO + TECH_DEBT #42 cerrado.** Paso 1 del orden DEC-036. **Selección** (paso 0 `RULER §2`, patrón DEC-031b): fuentes frescas s55 (Aritech/Kidde/Edwards; el lote es nido de OEM real — la 2X-A con los MISMOS PDFs bajo Kidde y Aritech; ModuLaser espejo Kidde/Edwards) + puente Detnov fresco (CAD-171); doc `evals/_s57_heldout_selection_proposal.md` v2 (local). **Dúo (sub-agente FRESCO pin fable 12/11/1-FP-parcial + cross-model GPT-5.5 6/5/0)**: v1 NO-SÓLIDA→v2 — cazó 2 clones residuales (ho002≈cat023; ho009 ROTO contra el catálogo: `2X-AT-F2` = match exacto → por D6 no es clarify → re-draft a "2X-AT"), el agujero F2 (los lectores-directos del YAML exponían el held-out JUSTO en las herramientas del gate s58 → **fix de raíz ejecutado**: `gold_store.exclude_heldout()` + 3 lectores + test = **#42 CERRADO**), y el hueco conceptual del PREREG ("confirmado en held-out" sin definir) → **criterio PRE-REGISTRADO** (corrida única; CONFIRMA = Δ global mismo signo + 0 fabricaciones K-estables nuevas; zona gris = Alberto, "confirmación DÉBIL"). Auto-catch propio: v1 concentraba 7/13 en la familia 2X-A → rebalanceo. **Autorados 2/11 SERIAL (checklist §2 punto-por-punto, SIN correr el bot):** `ho004` (es-en; alineación FD2705R — procedimiento SOLO-EN; render±1 + co-gen GPT 0-desacuerdos + match 14/14 anchors) y `ho003` (es-en; KE-DP3020W↔2X-A + EN 54-13 — el no-asterisco verificado AL PÍXEL con cross-model dirigido, lección 7-seg; la localización exhaustiva matizó el estrato: compatibilidad de serie + firmware≥5.0 SÍ están en ES; hallazgo que enriqueció el gold con un CORE nuevo). **Embargo verificado el mismo turno**: `verified()`=39, `heldout()`=[ho004,ho003]; ruler = **41 golds / 0 errores**; suite **217 verde**. **PENDIENTE (s57b)**: ho001/002/005-011 sobre la selección firmada; **decisión de Alberto**: N held-out 11-ampliable (recomendado) vs ≥20 (DEC-021 §C) antes del A/B. Canónico **DEC-037**.

> - **RESULTADO s57b (10 jun 2026 — continuación de DEC-037): firma del N + 2 golds held-out más (4/11).** Alberto FIRMÓ el N del held-out: **11-AMPLIABLE** (DEC-037f; ≥20 descartado por coste de oportunidad; el embargo no caduca → ampliable post-s59). Autorados SERIAL (checklist §2, sin bot): **ho001** (oem-relabel: configuración de zonas de la 2X-AF2 formulada como KIDDE con corpus=Aritech — 512 zonas / números 01-9.999 / nota 4095 2010-2GUI / alta por Config de lazo / modo Mixta default que SÍ mezcla detectores+pulsadores; render±1 con offset impreso +6 consistente + co-gen GPT-5.5 0-desacuerdos + 11/11 anchors + capacidad doble-fuente con el datasheet AF2-09) y **ho005** (multi-doc REAL: ampliación con la tarjeta 2X-A-LB — el sheet ML [bloque ES pp7-8: LOOP3/4 + OUT5-8, ranura 2, tierra a espárragos de la CAJA no de la tarjeta, EOL 4,7/15 kΩ por clase] remite explícitamente al manual del panel [p98: alta por Ajustes del panel → Tarjeta expansión → LB + 'use solo 2X-A-LB']; 11/11 anchors). Ruler = **43 golds (39 dev + 4 held-out)**, 0 errores, embargo verificado en el mismo turno (`verified()`=39). **PENDIENTE (s57c)**: ho002/006/007/008/009/010/011. Canónico **DEC-037** (estado actualizado).

> - **RESULTADO s57c (10 jun 2026 — `DECISIONS.md` DEC-038): autoría held-out COMPLETADA (11/11) — los 7 restantes autorados SERIAL; 3 resoluciones condicionales según FUENTE; composición final declarada; gap del eje admit elevado a Alberto.** Los 7 (checklist §2 punto-por-punto, sin bot, doble-señal co-gen GPT-5.5 + anchors deterministas + SQL existence): **ho002** oem-relabel ModuLaser (clúster = display + 1-8 detectores; ≤4 no-distribuido por cinta J3/J5 / ≤8 distribuido por SNET+ máx 1.200 m; rebrand Edwards≡Kidde verificado al píxel p31≡p31; 19/19 anchors) · **ho006** NC rearme+anular (re-etiqueta PRE-FIRMADA multi-doc→sintesis: ambos predicados en el manual de OPERACIÓN pp28-33; el de instalación solo trae el rearme AUX 24V; 12/12) · **ho007** 2X-A día/noche+retardos (bisagra EN la fuente: p135 "no procesa retardos en modo noche"→Tabla 23; 19/19) · **ho008** CAD-171 (2 lazos base→8 con 3×TBUD-NG, 2.000 zonas; sintesis según-fuente — el dato vive íntegro pero disperso en MI-716; neutralidad #43 respetada; 14/14) · **ho009** clarify "2X-AT" (∉ catálogo → 6 variantes -P/-S/-FB verificadas en datasheets; 11/11) · **ho010** NC-en-red: la rama pre-firmada "si documentado → answer (declarado)" se ACTIVÓ — red real vía tarjeta 2010-1-NB, anillo clase A / bus restringido EN 54-2, nodos 00-32 (prio-2 no usada: su trigger era documentada-TRIVIAL; 13/13; la doble-señal cazó mi error de lectura "y"→"o") · **ho011** refuse FD2705R (anclado en límites POSITIVOS: Entorno=Interior + IP50 revelados por el RENDER + 5-50 m con redirección a la variante 100 m/4 reflectores; 13/13). **Dúo (P3, MEDIO-en-zona-de-dolor): sub-agente FRESCO 4 findings / 2 confirmados / 0 FP** — F1 [MEDIO] mi nota anti-dup de ho006 sobre-afirmaba ("0 golds" falso por folding YAML; hp011/hp015/cat016 tocan rearme/anulación con predicados distintos → no-dup EN SUSTANCIA; **nota corregida pre-commit** — patrón `feedback_my_bias` cazado por el sistema) + F3 [BAJO] fact-de-conducta de ho011 movido a notes (esquema consistente con cat013); 10 citas verbatim verificadas EXACTAS por el reviewer en 6 PDFs. **Composición final (divergente del resumen DEC-037a por ramas pre-firmadas): multi-doc 1 · sintesis 3 · admit 0 · refuse 1** → **GAP FORMAL (DEC-038d, decisión de Alberto al arrancar s58 CON DEADLINE):** admit held-out a 0 y la opción "ampliable" caduca DE FACTO en la corrida única del PREREG → (i) autorar 1 admit gateado ANTES de la corrida de s59 (candidata: la prio-2 firmada) vs (ii) declarar refuse-only; la pregunta va TAMBIÉN al cross-model del gate s58. Ruler = **50 golds (39 dev + 11 held-out)**, 0 errores, embargo verificado (`verified()`=39), suite **217**. **SIGUIENTE (s58)**: decisión DEC-038d + GATE de atribución (baseline K=5 + context-sufficiency + stop_reason). Canónico **DEC-038**.

> - **RESULTADO s57d (10 jun 2026 — `DECISIONS.md` DEC-038d RESUELTA): Alberto firmó la opción (i) y el admit held-out quedó AUTORADO — ho014; el eje no-fabricación held-out CUBIERTO (admit+refuse); ruler = 51 golds (39 dev + 12 held-out).** La candidata pre-firmada (prio-2 de ho010: software config 2X-A) **CAYÓ honestamente en verificación**: el manual EN de la 2X-A (en corpus) la NOMBRA ("our **Configuration Utility** software application", p54, ×5pp) → habría sido answer, no admit. Candidata NUEVA re-gateada: **ho014** "¿cuál es la referencia del cartucho del filtro de polvo de repuesto del ModuLaser?" — admit, **subtipo de cat015** (identificador concreto ausente: allí versión de firmware, aquí SKU de repuesto físico). **AUSENCIA PROBADA** (D5): barrido bilingüe + sinónimos (filtro/filter/dust filter/filter cartridge/spare/recambio/9-30\d{3}/P\/N) sobre los 8 docs de la familia ModuLaser en corpus + corpus-wide → 0 SKU; 0 líneas filtro∩código en los 2 manuales (126+134pp); único doc de repuestos del corpus = DXC-Referencias-repuestos (Morley, otra familia); indicio auxiliar: el corpus SÍ lista accesorios ModuLaser con SKU (9-30441 APIC). PRESENCIA servida en el gold: fallo de filtro al 20% (=bloqueo 80%), Expirac. Filtro MM/AA (aviso 10:00 día 1), procedimiento 5 pasos con detector ENCENDIDO (cara IN arriba, Figura 26), no-reutilizar/desechar, ropa+mascarilla, filtro externo en áreas sucias. **MINI-GATE del dúo COMPLETO pre-autoría** (la letra de DEC-038d "gateado" + tiering s56): sub-agente FRESCO = SÓLIDA con 3 bites aplicados (anti-dup del brief ampliado con hp002/hp007 — mismo patrón F1 de s57c, cazado otra vez; redirección al proveedor como CONDUCTA PROPIA, no atribuida al manual — su "proveedor local" p107 es del párrafo detector-contaminado >30%; core del gold = la AUSENCIA, cuándo/cómo = supp) + **cross-model GPT-5.5** = 5 findings aplicados (documentar barrido bilingüe; hueco spare-parts-genéricos cerrado por SQL; indicio APIC rebajado de "prueba" a auxiliar; proveedor-local-en-contexto **CONVERGE** con el sub-agente; "patrón nuevo"→subtipo de cat015). Autoría: render píxel pp106-109+51+83 ES y pp115-116 Kidde (±1; pp107-108 al píxel: procedimiento + Figura 26 SIN referencia) + co-gen GPT-5.5 (26 hechos, 0 desacuerdos + **confirmación independiente**: "no aparece ninguna referencia, número de pieza ni SKU del cartucho") + **14/14 anchors** + upsert por la puerta. Embargo vivo (`verified()`=39), suite **217**, tally del dúo registrado (3 entradas s57c/s57d en `adversarial_review_log`). **SIGUIENTE (s58)**: GATE de atribución PURO (baseline K=5 de los 39 dev + audit context-sufficiency + instrumentar stop_reason) → s59 lever según gate. Canónico **DEC-038** (estado d actualizado).

> - **RESULTADO s58 (10 jun 2026 — `DECISIONS.md` DEC-039): GATE de atribución EJECUTADO — runner K-mayoría construido y gateado, baseline fresco de los 39 dev corrido, residual CLASIFICADO, PARAR cumplido.** **Instrumento** (`scripts/bvg_kmajority.py`, dúo ronda 1 ANTES de cablear): 4 fases reanudables — freeze (top-5 CONGELADO por gold con blurb `context` hidratado por id; el brazo B de s59 lo necesita) → generate (K=5, brazo A blurb OFF; `stop_reason`/`output_tokens` instrumentados en `generator.py`, 4 tests) → judge (GPT-5.5 + prompts del harness + `response_format` = **JUEZ NUEVO CONGELADO de la ventana**; serie vieja no-comparable declarada) → report (partición pre-registrada). **Run-manifest DEC-021 §F completo** (1ª materialización: corpus fingerprint 25.090 + max(created_at); sha256 de prompts; alias del juez RESUELTO `gpt-5.5-2026-04-23` ×195; seeds = knob-muerto). **El dúo mordió en las DOS rondas (27 findings / 26 confirmados / 1 FP):** r1-diseño: el sub-agente cazó la **verdad-vacua** (11/34 answer-golds con todos los core DÉBILES habrían caído TODOS en GENERACIÓN = mi bias #20 encarnado en la regla → bucket `INDETERMINADO-solo-debiles` pre-registrado) y el cross-model p2 cazó **2 CRÍTICOS del criterio PREREG** (Δ global con 2 lecturas defendibles; "0 fabricaciones" no decidible con el juez cualitativo) → **cláusulas C1/C2 A FIRMA de Alberto** + mi v2 del PASS-control re-escribía el sub-contrato (vuelto a la LETRA: modal PASS); r2-lectura: el sub-agente cazó que mi v1 **pre-nombraba lever** (A2/composición) citando DEC-016-CORRECCIÓN **supersedida por DEC-018** (el patrón pre-suponer-lever INVERTIDO hacia retrieval, `feedback_my_bias` #30) + cross-model p3 5/5 de honestidad (hp010/hp012 → NO-LOCALIZADO; spot-check exploratorio congelado). **RESULTADO del baseline (195 generaciones / 195 juicios, 0 errores):** **PASS-control FIJADO = 10** (6 unánimes; hp019/hp020 — FALLO estables s43 — hoy PASS = el residual viejo estaba STALE) · K-INESTABLE 3 (hp003 = varianza real del generador 1/5 runs) · **residual 26 clasificado**: retrieval-localizado 8 (within-doc-miss 11 domina; multi-doc clásico minoritario hp008+hp001) · GENERACIÓN 4 (cat020 el más limpio; por SEVERIDAD los FALLO-modales reparten hacia generación/sobre-admisión) · NO-LOCALIZADO 2 · INDETERMINADO 8 (sobre-admisión 4/8) · CUALITATIVA 4 (hp004 único fallo de conducta). **Truncamiento DESCARTADO** (195/195 `end_turn`); suelo-del-juez no aparece como cuello. **El mecanismo del within-doc-miss NO está medido** (POST-wide; freeze guarda top-5, no pool-50) → entrega a s59: 2 pasos baratos EXPLORATORIOS congelados (funnel split de los 8; spot-check de los 4 sobre-admisión) — informan, **el branch lo firma Alberto** (retrieval-dirigido vs A/B 2×2 generación). Las 195 generaciones PERSISTIDAS (el atomic_scorer del A/B corre sobre ellas, C2). Artefactos versionados `evals/s58_*`; suite **221**; ventana de freeze del corpus ABIERTA. Canónico **DEC-039**.

> - **RESULTADO s58b (10 jun 2026 — `DECISIONS.md` DEC-039g): los 2 pasos baratos EJECUTADOS + Alberto firmó el BRANCH s59 (retrieval-RECALL) y las cláusulas C1/C2 del PREREG.** Alberto eligió "pasos baratos primero" → **(1) funnel split de los 8 retrieval-localizados** (hechos FUERTES): RETRIEVAL=14 ni-al-pool-50 · CORPUS-GAP=3 (extracción: tabla-mantenimiento hp007 + "159+159" cat017) · RERANK-MISS=2 → **el mecanismo del within-doc-miss es RECALL del retrieve**, no rerank ni composición-A2. **(2) spot-check de las 4 sobre-admisiones vs el top-5 CONGELADO**: cat016/hp006/hp013 = retrieval-honesto (los términos decisivos ausentes de TODO su top-5); hp009 = generación-IDENTIDAD ("RFL de 150 Ohmios" literal delante, etiquetado ZXAE/ZXEE, y el bot declaró no-cobertura — no mapeó ZXe↔ZXAE/ZXEE, TECH_DEBT #43). Cuadro final: **bulto retrieval ≈11 golds (mecanismo RECALL) / generación 4+1-identidad**. **FIRMAS** (recomendación con Protocolo 2 — alternativas y gaps declarados): branch s59 = **retrieval-RECALL** (dimensionamiento del por-qué → diseño con dúo → medición K-mayoría vs baseline congelado; A/B 2×2 VIVO de plan B con su brazo A ya corrido; hp009 → fix de identidad separado) + **C1/C2 escritas al PREREG como bloque firmado** (Δ global ordinal answer-only; fabricaciones vía atomic_scorer sobre generaciones persistidas). Canónico **DEC-039(g)**.

---

# Rationale histórico (mayo 2026) — cuerpo original del PLAN [SUPERSEDED]

> Todo lo que sigue es el cuerpo del PLAN tal como quedó en mayo 2026 + parches de sesión.
> Numeración de secciones ORIGINAL (## 1 … ## 9, Changelog). Estado: superseded por el PLAN
> compacto; valor = rationale y trazabilidad de citas antiguas.

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
- **s59 (10 jun 2026)** — Lever retrieval-RECALL "canal vectorial sano" EJECUTADO de punta a punta y ROLLBACKEADO por el criterio pre-registrado (DEC-040). Dimensionamiento: causa raíz MEDIDA — `chunks_v2.category` sin taxonomía canónica desde el SWAP s44 (0 filas; 58% NULL, 25% 'ES') → canal vectorial principal devolvía 0 SIEMPRE en el 85% de las queries (+ ef_search=40<k); los 14 hechos RECALL tienen rank vectorial exacto 7–110 (10≤50). Lever L-i diseñado con dúo (2 rondas + focal; 5b diferido por consenso; 30 findings/0 FP) y MEDIDO: gate-1 11/11, gate-2 RECALL-fuertes 14→3 (mayoría al top-5), pero A/B K=5 Δ_net=0 con redistribución → ROLLBACK regla 1 (cat010 unánime PASS→PARCIAL 3-2; ganancias cat020 FALLO→PASS + hp001 PARCIAL→PASS compensadas por cat005/9/10+hp018). El criterio duro evitó shipear un empate. Código preservado en `s59-lever-code-ROLLBACKED`; instrumentos nuevos (diagnosis seq-scan, gate1 --alter/--reset, fabrications-K, ab_verdict, runner BVG_RUN_ID); F 0→0. L-ii (ALTER ef_search) DENEGADO por permission-mode → pendiente Alberto; cláusula R del PREREG (held-out retrieval) escrita pre-datos, pendiente de firma; TECH_DEBT #44 (contrato de category, escritor incluido). Siguiente branch = decisión Alberto: merge/ranking-lever vs 2×2 generación vs L-ii-solo.
- **s59b (10 jun 2026)** — Firma + autorizaciones post-merge #64 (DEC-040f): cláusula R del PREREG FIRMADA por Alberto (held-out de levers de retrieval desbloqueado-bajo-criterio); L-ii AUTORIZADO y EJECUTADO por Alberto (proconfig None→ef_search=120; gate-1@120 10/10 PASS, canal sirve 50/50; ventana DB ABIERTA); re-etiquetado de `chunks_v2.category` (#44) DIFERIDO con triggers firmes (freeze abierto = edit-in-place prohibido por DEC-036e; pregunta cero: el rumbo s60 no usa las etiquetas; triggers = cierre del ciclo + antes de la próxima ingesta).
- **s60 (10-11 jun 2026)** — Lever de MERGE diseñado (v1→v4, dúo ×2 rondas: r1 sub-agente 11/11 + cross-model 6/6; r2 sub-agente 12 + cross-model 7/7; 0 FP en los 4 tallies) y REDEFINIDO por 3 gates baratos en cascada SIN build (DEC-041). Audit primero (Protocolo 4): stamps 0.65-0.85 vs cosenos 0.52-0.68; el corte casi no muerde (pool mediano 26-30; corte activo 4-8/39); mordidas reales = orden-al-reranker + dedup (stamp pisa coseno) + diversificadores. Hallazgo cat020: la ganancia +2 del A/B s59 volteó con top-5 idéntico → ruido de generación/juez → Δ_net pool-atribuible real de s59 ≈ −2 y techo del MERGE +2-frágil. Paso-0 (~72 llamadas, pools congelados): reranker LLM sensible al orden 11/12 — pero también en PASS-control (palanca sin freno). r2 descubrió de rebote el DADO ENTRE-CORRIDAS del reranker LLM (3/12 golds cambian top-5 con input bit-idéntico entre sesiones; hp018, la pérdida "atribuible" de s59, entre ellos) → shadow-rerank del baseline pre-registrado (conservador, no-exonerante; X1 cross-model). Gate-D (regla pre-acordada con Alberto): cross-encoder Voyage rerank-2.5 determinista 12/12 + insensible al orden 12/12 → LEVER REDEFINIDO = L-i + cross-encoder (DEC-016b re-litigable: condiciones de descarte disueltas). Hallazgo colateral #45: chunks_v2.has_diagram/diagram_url a CERO (vs 44.035 en la vieja) — el bot no sirve diagramas desde el SWAP s44 (degradación de producto en silencio; hermano de #44). Bias #31 cazado por el dúo: re-instalé la lectura de PR#8 que DECISIONS:579 ya había corregido. Prod intacto; ventana DB abierta; corpus congelado. Branch eval/s60-merge-lever (PR al cierre). Siguiente (s61): diseño compacto del lever redefinido + dúo fresco → build → gates → A/B K=5 (criterio §3-v4 + shadow-rerank) → held-out bajo R si SHIP.
- **s61 (11 jun 2026)** — Lever redefinido (L-i + cross-encoder) DISEÑADO (v1→v3, dúo ×2 rondas frescas: 28 findings / 1 FP; críticos del cross-model = header de paridad del doc al CE y dispatch condicional que limita el ship a lo medido; el dúo desenterró el 4º camino de los stamps: el generador FILTRA el top-5 por `similarity>=0.4` y ve los scores a 2dp → todo el ciclo pasó a medirse sobre "la vista del generador"), CONSTRUIDO tras flag reversible (`RERANKER_BACKEND` default llm; 237 tests verdes; manifest de bvg honesto) y PARADO en el GATE pre-A/B: **NO-GO por D2 pre-registrado** (las 2 ganancias demostradas de s59 perdidas) con D1 limpio 0/6. Diagnóstico VERIFICADO (controles LLM-mismo-pool + rank-probes): **hp001 nunca fue recuperable por un reranker** — su chunk vivía en la frontera del corte vectorial k=50 y el embedding de la MISMA query deriva 0.003 entre sesiones (el dado también vive en la cola del POOL, con cualquier reranker); **cat012 sí es del CE pero la raíz es corpus**: 3 revisiones del mismo manual conviviendo (#43) monopolizan un top-5 de scoring por pares. Colaterales: CE 5× más rápido / ~15× más barato / determinista 39/39; corte-a-50 muerde 9/39 @ef120. **Alberto (4 opciones en la mesa): cerrar el ciclo SIN pagar el A/B → s62 = ciclo #43 (supersesión/near-dups, audit-primero; ⚠️ NO latest-wins naive — hp011/ES↔US viven de ambas variantes)**. Lever preservado en `s61-lever-code-ROLLBACKED` (revisita barata tras #43); plan B MERGE descartado con datos (hereda hp001 + conserva el dado del LLM). La calibración DEC-016b cerró el círculo: gate de ~$1.5 evitó un A/B de ~$30-50 condenado a GRIS/ROLLBACK. Prod intacto; corpus 25.090. Traza: DEC-042 + `evals/s61_gate_diagnosis.md`.
- **s62 (11 jun 2026)** — AUDIT #43 ejecutado (audit-primero, read-only: shingles por doc + Jaccard por fabricante + B3 por metadata + 4 verificaciones regla-C) y **REFUTÓ el diagnóstico de s61**: los AM-8200 NO eran near-dups (J_doc 0.001-0.032) — el mecanismo real de cat012 es **identidad producto↔serie** (el filtro matchea substring → los HERMANOS 8200G/N entran a la query AM-8200 y el CE llena el top-5 con secciones conceptualmente equivalentes de 3 productos distintos). CORRECCIÓN canonizada en DEC-042 + lección #32 al log de bias (mecanismo canonizado sin medir en un diagnóstico post-mortem — regla-C también para diagnósticos). Mix real de la deuda: capa A identidad producto↔serie (daño medido) · capa B metadata rota de lotes viejos (Spectrex bajo Detnov ×15, model=unknown masivo, revision-basura, document_family=filename, supersedes 0/1065) · capa C near-dup textual MARGINAL (1 revisión MAD-472 V2 → cat024; 41 grupos ES/EN legítimos que se conservan). La supersesión retroactiva quedó SIN MATERIA (contrato → flujo de ingesta futura). **Branch (Alberto): CICLO A** — registry de series curado-por-evidencia en el seam s55 (cero DDL) + filtro de 3 niveles (sin entrada → comportamiento actual; hermanos NO pasan; fail-open intacto); diseño v1 escrito (`_s62_seriesA_design.md`, pre-dúo — dúo fresco arranca s63). Protocolo nuevo de medición: gates de retrieval con el MISMO embedding por par (el drift 0.003 contamina diffs de pools). Todo read-only; prod intacto; corpus 25.090. Traza: DEC-043 + `evals/s62_audit43_diagnosis.md`.
- **s64 (12 jun 2026)** — **Lifecycle #46 CERRADO (DEC-045): el contrato de supersesión POBLADO por primera vez (3 cadenas) + fix de re-entrada en diversify; la parte (b) del item — re-ingesta del MS-416 "actualizado del portal" — quedó SIN MATERIA por verificación.** La sesión arrancó con pregunta-cero sobre la premisa de (b) ANTES de diseñar: descarga + SHA de los 4 URLs del portal Detnov (páginas CAD-171, CAD-250 ES y CAD-201) → **todo byte-idéntico a lo ya ingestado** (MS-416-2026-b `e1985c3d…` 73pp; viejo `49d0f899…` 76pp; Wayback sin snapshots). La claim de s63 ("Detnov actualizó in-place; el actual de 73pp difiere de lo ingestado") fue un **cruce de identidades** entre las dos ediciones conviviendo — el "73pp del portal" ERA el -2026-b ya ingestado; el "lo ingestado" de la comparación era el viejo de 76pp → lección #34 (claims observacionales se canonizan CON evidencia reproducible: sha/URL/fecha). La verificación de estado destapó además que el pipeline s44/s55 **no crea filas en `documents`** (los 2 sucesores Detnov tenían document_id NULL en sus 224 chunks → sin identidad, sin lifecycle posible, cadena sin destino) y que **los suplementos de diversify se saltaban el lifecycle filter** (4b corre antes; el re-fetch después → docs needs_review YA re-entraban hoy, y los superseded de (a) habrían re-entrado igual — variante lifecycle del F1-r1 s63). Dúo sobre el diseño pre-registrado (sub-agente fresco 8/8 + cross-model GPT-5.5 5/5, **0 FP**): el INSERT violaba `document_family NOT NULL` (crítico F2), el fix era media-lección §1c-2 (pre-filtro de slots además del cinturón, F1), C2 sobre wide no garantizaba el top-k servido de cat019 — single-source sobre el rev-b enterrado (F3), el spec no declaraba `status=` explícito (X1) y el cinturón incondicional rompía `include_superseded` (X2). Ejecución del runner 5 fases: precheck GO (hechos-gold de cat019/hp001 presentes en el sucesor; cobertura de secciones MS-416 90%≥75%) → before → fix + 260 tests → **apply con autorización explícita de Alberto** (el clasificador de permisos bloqueó mi 1ª ejecución — freno correcto, mismo patrón que el merge s63) → after **GO: C1 0 docs viejos en 39 pools · C3 36/36 byte-idénticos (cat005 dado-de-red convergió) · cat024 pool 4→7** → smoke real: maniobras CAD-250 responde desde MC-380-2026-c **citando 'rev c'** (los chunks enlazados llevan revisión por primera vez), MAD-472 desde V2. Fingerprint de freeze extendido con dimensión lifecycle (era ciego a status; bug de paginación del runner cazado y corregido: PostgREST max-rows contó 1000/1067): **1067 docs {1059 active · 3 superseded · 5 needs_review} · 262 chunks excluidos · corpus 25.090 intacto**. **Ventana de freeze CERRADA**; supersede-traps del eval legacy NO se autoran (ruler vivo ya cubre vía cat024 + C1). PR #71 (cierre s63) mergeado por Alberto al arrancar. Siguiente: capa B (higiene de metadata, con el backfill s64 como patrón) → revisita CE → ingesta grande tras #44/#45.
- **s63 (12 jun 2026)** — **CICLO A SHIPPED (PR #70): registry de series + filtro de 3 niveles + diversify corregido — primer lever de retrieval en producción desde el SWAP s44 (DEC-044).** Dúo ×2 rondas FRESCAS sobre el diseño (r1: 17 findings — crítico: diversify RE-INTRODUCÍA a los hermanos justo después del filtro; r2: 19 — críticos CONVERGENTES sub-agente+cross-model: bug de polaridad multi-modelo en mi v2 y "la rama shared solo filtra, no fetchea" [el doc de serie no llega por recall vectorial: pool CAD-201 medido 17/17 MI-715]; 0 FP netos) → FINAL con el principio INVERTIDO respecto a v1: el substring histórico se queda como base y el registry solo añade vetos de hermanos + aperturas de shared_docs declarados ("cero cambio salvo lo declarado"). Curación de Alberto con evidence anclada en chunks_v2 (AM-8200 sin shared — el G sin doc de usuario queda como gap honesto; Vesta con MC-380 rev-c y MS-416-2026 vigentes); su corrección del MS-416 cazó mi **lección #33**: leí la tabla de revisiones INTERNA del PDF (desactualizada por Detnov) en vez del contenido (p12 lo decía claro). Build: `series_registry.py` (fail-open, maximal-munch en conjunto, flag `SERIES_REGISTRY_ENABLED` = kill-switch) + filtro escalonado + diversify (fetch dirigido de shared + pre-filtro de missing + cinturón + `_content_keywords` — la identidad envenenaba el FTS del fetch) + harness dual-arm (embed-cache por par; pairing por pool: idénticos comparten frozen, Δ:=0 estructural); 256 tests (221 intactos). Gate G1-G8 pre-registrado y **GO** (cat012 pool 28→9 100% producto correcto con la tabla retenida; probe d2 con candado+2222; 38/42 byte-a-byte; 1 enmienda de instrumento: convergencia r2 tras cazar timeouts de red como falsos "cambiados"). A/B K=5 con pairing: **SHIP Δ_net=+2** — cat012 PARCIAL→PASS (la fórmula y la Tabla 1 por fin en la respuesta) y cat018 FALLO→PASS (su PASS de s58 se sostenía en el manual del producto equivocado), 0 regresiones, 37 Δ:=0, coste ≈ 2 golds en vez de 39. Held-out (cláusula R, corrida ÚNICA — 1ª ejecución del protocolo DEC-037c): **DÉBIL Δ=0** — 11/12 idénticos; ho008 (CAD-171) modal IGUAL con la vista ganando los docs de serie; 0 fabricaciones — **ACEPTADO por Alberto declarado** → PR #70 **mergeado por Alberto** (mi merge lo bloqueó el clasificador de permisos: freno correcto en deploy-a-prod). Post-ciclo apuntado: TECH_DEBT #46 (lifecycle de 3 docs sustituidos + re-ingesta del MS-416 actualizado del portal — Detnov actualizó el PDF in-place y lo ingestado difiere) + capa B + revisita CE con el filtro nuevo. Instrumentos que quedan: embed-cache por par, pairing por pool, INCLUDE_HELDOUT, convergencia anti-dado-de-red.

- **s65 (12 jun 2026)** — **CAPA B de #43 CERRADA (DEC-046): higiene de identidad de los lotes viejos — el item #43 queda COMPLETO (capa A s63 · capa B s65).** Audit dirigido fresco primero (Protocolo 4, `evals/s65_audit_capab.yaml`): los números corrigieron el cuadro del s62 — el unknown masivo vive en `documents` (203), NO en chunks (401 = 1,6%); el mismatch real de manufacturer es **86 docs** (por evidencia doc↔moda-de-chunks, no 17 por keyword); las 165 filas sin chunks eran TODAS `active` (90 con contenido solo en la tabla vieja + 75 en ninguna, con duplicados de identidad con/sin `.pdf`); y 2.065 chunks de los lotes s55/s58 (Aritech 895 · Kidde 676 · Detnov 164 · Edwards 156 · 115 sin marca) vivían SIN fila en `documents` = fuera del lifecycle y sin revisión citable. Diseño v2 tras dúo (sub-agente FRESCO 13/13 confirmados 0 FP, máx CRÍTICO; cross-model GPT-5.5 7/7 con valor 0 FP): el crítico F1 cazó la colisión A1×A4 (el doc RIF_08791 estaba en ambas poblaciones: enlazarlo y retirarlo lo habría hecho invisible) → orden obligatorio A1→recompute-B6→A4 + assert; X1 cazó la contradicción de poblar `language` por moda mientras B4 se difiere (en sources `_ml` la moda MIENTE) → language/doc_type NULL; F4 el `UNIQUE (manufacturer, sha)` exigía pre-casado por sha; F5 el enlace lleva `AND document_id IS NULL`; F6/X2 la moda de chunks es circular → cross-check sidecar/canal + unanimidad + curación; F8 corrigió mi motivación de A2 (el header del generador NO lleva manufacturer — el efecto real es el catálogo); X3/X6 reescribieron A4 (retired solo con señal fuerte; needs_review = cola estructurada, no notes-texto-libre). Runner 6 fases (`scripts/s65_capab.py`, lógica pura testeada) con plan CONGELADO como objeto de autorización: inventory → before (39 pools, embed-cache; 1 solo gold esperado-afectado: hp020) → **apply con GO explícito de Alberto** (546 steps con before-values por fila) → after → smoke. Resultado: **103 filas nuevas + 1 enlace + 2.040 chunks enlazados** (residual honesto: 25 chunks / 8 sources del canal "Otros" sin marca demostrable — el sidecar decía brand=Otros; curados con evidencia 6 Aritech + 2 Kidde, el resto fuera) · 86 manufacturer corregidos (85 docs + 8 chunks del MAD565, la excepción donde los chunks estaban mal) · 80 revisiones-basura → NULL · 164 docs → 90 retired + **74 needs_review = cola curada de re-ingesta**. Verificación: 38/39 pools byte-idénticos + hp020 idéntico + **cat011 reclasificado dado-de-red-en-BEFORE con evidencia HISTÓRICA** (su pool s64 before/after era n=40 con SG*=25 — idéntico al after de hoy, estable ×3; el before de hoy n=15 era el degradado por timeouts de los fetches — patrón s63); invariante A4 PASS; 279 tests. Tres colaterales: (1) falso-STOP del assert global del runner (los 8 "violadores" eran los 3 superseded s64 + 5 needs_review Morley, que tienen chunks POR CONTRATO — exclusión en runtime, no des-enlace; assert corregido a scope-del-plan, transparencia en el apply_log); (2) **bug de paginación de `get_available_manufacturers`** cazado por el smoke F8 (cap PostgREST max-rows=1000 con 1.170 docs — la MISMA lección que el fingerprint s64; fix paginado + 2 tests; catálogo 26→**30 marcas** con Aritech/Kidde/Edwards/Honeywell visibles); (3) la lista del diversify-por-manufacturer medida en 2 marcas (`_get_all_known_manufacturers`, 200 chunks físicos sin ORDER BY → TECH_DEBT #47). El ESCRITOR del hueco sigue vivo declarado: `resolve_document_id` casa pero no crea fila — el contrato de identidad EN INGESTA (crear fila + preferir active al casar + sha-check) es prerrequisito del PLAN punto 2 (ingesta grande). Estado: 1.170 docs {998 active · 3 superseded · 79 needs_review · 90 retired}; corpus 25.090 intacto (0 chunks creados/borrados). Siguiente: revisita CE → ingesta grande tras #44/#45/contrato-en-ingesta.
- **s66 (12 jun 2026)** — **Re-gate del lever CE = GO (DEC-047): la revisita condicional de DEC-042e ejecutada con scope RE-DECIDIDO a CE-PURO; el A/B queda habilitado y Alberto lo fijó para s67.** Arranque por el punto 1 del PLAN con verificación de estado primero (Protocolo 4): branch `s61-lever-code-ROLLBACKED` intacto; main divergido +315 líneas en `retriever.py` (series s63 + lifecycle s64) pero LIMPIO en `reranker.py`/`config.py`/`telegram_bot.py` desde el merge-base → transplante posible sin rebase. Diseño v1 con la decisión de scope como pregunta abierta (Protocolo 2: 4 opciones) → dúo FRESCO r1 (sub-agente 8/8 + cross-model GPT-5.5 5/5, **0 FP**, tally en log): **F1 (ALTA) refutó mi premisa heredada "hp001 irrecuperable, fuera de pool"** — s64 devolvió sus hechos al sucesor MC-380-c EN pool (`s64_precheck.yaml`) y yo cité "C3 36/36 s64" sin notar que ese conteo EXCLUYE a hp001 por afectado (reincidencia del patrón premisa-no-verificada, cazada por el DÚO sin Alberto → branch pre-registrada en vez de premisa); F2 paridad-control extendida a D2′ (la estructura del falso-culpable s61); F5 corrigió la cifra del churn de L-i (24/39 @ef40 — el 35/39 era del PAQUETE, dominado por el CE); X1 (crítico) exigió las anclas de cat018 LISTADAS antes de cualquier retrieve (el pre-check empírico validó el punto: la candidata "apendice a" daba 0 hits = infalsable); X4 corrigió el coste del gate a ~$5-6 (el "~$2" del PLAN heredaba la subestimación s61); X5 puso "archivar sin gate" como opción legítima. **Alberto: CE-puro + gate.** Build: transplante de 5 archivos (dispatch Y1 + header de paridad + strict + provenance + retirada del flag legacy `RERANKER`), SIN `retriever.py`; 290 tests. Instrumento `s66_gate.py` 5 fases con probes CONGELADAS pre-paso-A; calibración F8 ($0): la referencia nueva (LLM-modal actual, no frozen-s58 muerto) pasa 6/6 unánimes sobre el artefacto s61. Paso A: ef=120 + corpus 25.090 + lifecycle s65 + registry fingerprint estampados; pools frescos CUADRAN el canon (cat012=9, cat024=7, hp001=26). **El precheck disparó STOP-D2 en cat018 — freno pre-registrado correcto, $0 gastados** → diagnóstico regla-C: el PASS vigente s63 se sostuvo con h1+h4 SOLAMENTE (h2/h3 JAMÁS en pool/vista s63; pool fresco equivalente 16/16 keys) = **falso-STOP por anclas MÍAS sobre-especificadas** (el probe protege lo que el SHIP SIRVE, no los 4 atomic_facts del gold) → enmienda pre-paso-B APROBADA por Alberto (condición=h1+h4; h2/h3 informativas; paralelo DEC-044d). Paso B (~$4.5 real): **CE determinista 39/39 + orden-insensible 7/7 críticos + 0 chunks sub-0.4; D1 6/6 limpio (vía-1 4-5/3 Y vía-2 completas); D2′ 0 pérdidas atribuibles — cat012 retiene 4/4 hechos bajo CE (en s61 perdía h2/h3 por los hermanos: el cierre río-arriba de s63 CONFIRMADO empíricamente); cat018 retiene h1+h4**; hp001 INFORMATIVA ('candado' en pool y AMBAS vistas; '2222' fuera — frontera de pool re-confirmada, con el matiz de que ya no falta el doc entero sino el chunk p20). Dado del LLM re-medido HOY: 12/39 votos no-unánimes (cat018/hp014 a 1/1/1) — el defecto de producto del statu-quo, fresco. Latencia rerank: CE p95 0.84s vs LLM 2.86s (~3.4×; p50 ~4.8×). **GO habilita, NO autoriza (DEC-016b). Alberto (3 opciones): A/B en s67** — mini-diseño con pairing-por-vista + dúo fresco + re-freeze del baseline (pendiente de todos modos) + brazo CE; ventana X2 (fingerprints idénticos o re-gate ~$5). Prod intacto (rama sin mergear; flag default llm = inerte); corpus 25.090. Traza: DEC-047 + `evals/s66_gate_{probes,precheck,report}.yaml` + commits 8112bd6/8a6088d.
- **s67 (12 jun 2026)** — **A/B del swap CE ejecutado (GO de Alberto sobre el diseño v2 post-dúo) = ROLLBACK por la tabla pre-registrada; el lever CE queda ARCHIVADO con evidencia end-to-end y el re-freeze `s67base` queda como baseline NUEVO del ruler (DEC-048).** Arranque canónico: PR #74 mergeado verificado → ventana X2 verificada VIGENTE (script nuevo `s67_x2_check.py` 7/7 contra `s66_gate_pools.json:meta`; código gate→main diff VACÍO). Mini-diseño del A/B (re-freeze LLM K=5 + brazo CE K=5, pairing por vista-del-generador idéntica firma F1-s61, criterio §7-s61 con tabla INTOCADA + F7-endurecida) → dúo r1 FRESCO: sub-agente **7/7 confirmados 0 FP** (F1 ALTA: hueco dado-mediado — freeze-A es una tirada NUEVA y en un gold gate-unánime puede ser 4ª-vista → un mover dado-mediado habría contado ATRIBUIBLE y una caída disparado ROLLBACK por ruido del baseline → dado-plausible := no-unánime-gate ∨ freeze-A∉vistas-gate + STOP sistémico ≥9/35; F2: recuento del dado RE-DERIVADO del artefacto = **11/39 no-unánimes** [9× 2/1 + 2× 1/1/1; 24 unánimes con rerank + 4 short-circuit vacuos] — el "12/39" del PLAN era falso, patrón bias #35; F3: pool==gate era esperanza inter-sesión [gate SIN embed-cache] y la secuencia v1 pagaba generación ANTES del assert → día D reordenado; F4: drift del juez ENTRE brazos no cubierto [R4 compara alias+SHAs] → assert judge_model_real; F5: phase_report ignora --qids → herencia explícita shared_from para los paired; F6: regla-1-context-idéntico VACUA bajo pairing, declarada; F7: 4 short-circuit, churn fresco s66=35) + cross-model GPT-5.5 **6/6 confirmados 0 FP** (X1: freeze-contract partido — x2_check ampliado a código con --code-baseline falla-cerrado; X2/X6 convergentes con F3; X4: "atribuible-operacional bajo n=3+1"; X5: retención-del-gate = proxy presencia-en-vista, no end-to-end). Build §4: manifest honesto de bvg RE-APLICADO A MANO sobre main (4 bloques de la rama s61 preservando lifecycle-fingerprint/cláusula-R/series_registry/embed_cache_path — diff residual verificado) + `s67_ab.py` (asserts tri-vía+pool, pairing, herencia, veredicto) + test provenance; **300 tests verdes**; commit del build = code-baseline. **Día D: el assert (i) STOPeó por embed-drift server-side ANTES de pagar generación** (3/39 pools frontera con 1 chunk in/out — DEC-042d vivo; cat019 expuso además que `round(sim,2)` cruza fronteras de redondeo con drift 0.001 — la firma fue FIEL al header real del generador) → **re-gate ~$5 con `EMBED_CACHE_PATH` compartido y `GATE_RUN_ID=s67` parametrizado = GO** (D1 0 fail-both · D2′ 0 pérdidas · CE determinista · swap 35 — el cache ancla gate y A/B a la MISMA ventana de vectores POR CONSTRUCCIÓN: el riesgo F3 muere estructuralmente) → asserts verdes (4ª-vista 5/35 = dado puro) → brazo A 195/195+195/195 '?'=0 → checkpoint coste PASA (~$25-30 proyectado vs techo $90) → brazo B 175/175 (35 no-paired) → herencia 4 paired → reports → **VEREDICTO ROLLBACK**: Δ_net=0 (techo +0/+1 confirmado; cat012 GANA PARCIAL→PASS 3/5 sin margen — coherente con el gate) · SIN regla-1 (cat023 única caída de PASS, dado-excluido, control=1 ok) · **F_post 8 > F_base 5** (cat007/cat017/hp001/hp014 PARCIAL→FALLO; hp001 atribuible-operacional — el gold-frontera pierde su PARCIAL bajo CE) · **conducta 2 regresiones** (cat016/hp014 answer→admit; hipótesis mecanística declarada: la vista CE pierde el chunk de la respuesta parcial y el generador admite). Dos condiciones independientes de ROLLBACK; juez servido idéntico entre brazos (gpt-5.5-2026-04-23); instrumento limpio. El beneficio NO-end-to-end del CE (determinismo, latencia p95 0.81 vs 3.29, coste ~15×) no se compra degradando la cola PARCIAL→FALLO — F7 nunca aplicó (no era GRIS). Baseline s67base: 10/39 PASS-control (5 unánimes) · 4 K-INESTABLES · residual 25 con atribución. Flag default `llm` inerte; Railway intacto; held-out NO tocado (solo aplicaba si SHIP). Coste real sesión ~$30. Siguiente: PLAN punto 1 = corpus (contratos #44/#45/identidad-en-ingesta); el dado del LLM queda como defecto declarado para el ciclo profundidad-del-canal. Traza: DEC-048 + `evals/s67_ab_report.yaml` + `s67_gate_*` + `s67base_*`/`s67ce_*` + `evals/_s67_ab_design.md` (v2, local) + rama `eval/s67-ab-ce`.
- **s67b (12 jun 2026)** — **Re-priorización del roadmap confirmada por Alberto (DEC-049), post-merge del PR #75.** Su pregunta ("¿qué nos queda? me da la sensación de que estamos muy lejos") → assessment con el canon: la base de seguridad (no-fabrica/admite/rehúsa/cita) está conseguida y medida; el 10/39 del ruler adversarial NO es tasa de acierto real (los golds se autoran por dimensión de fallo); lo que no se ha movido es la cola difícil, y 3 ciclos de reranker = 0 dijeron dónde NO está el cuello. **Nuevo orden**: (1) ciclo del CANAL VECTORIAL — audit de dimensionamiento primero con la pregunta chunk-quality integrada; #44 category-como-BOOST + L-i renacido + corte según audit; (2) re-gate CE ~$5 condicional a pools nuevos; (3) 2×2 generación + cartera de levers por gate (system prompt del generador, prompt del rerank, k); (4) diagramas PARTIDOS — datos paralelizable ya (mapeo (doc,página) desde la tabla vieja: 44.035 vs 0/25.090 en v2; eval-inerte verificado por before/after — fingerprint ciego a edits in-place) + cableado post-canal; (5) **corpus DIFERIDO demand-driven hasta chatbot estable** (decisión de negocio: las 31 marcas = las de uso frecuente; la meta 30+ fabricantes SIGUE, fase posterior; reactivación por gap real vía Excel inventario). Dureza de la tabla de decisión: diferida con marco (cambios SOLO pre-registrados y motivados por evidencia, nunca post-hoc). Sin dúo (decisión de prioridad negocio+evidencia, no de diseño — cada ciclo llevará el suyo). Traza: DEC-049; rama `docs/s68-rumbo-canal` → PR.
- **s68 (12-13 jun 2026, SESIÓN AUTÓNOMA NOCTURNA — GO explícito de Alberto: techo $100, prod/held-out intocables; gasto real ~$7)** — **El ciclo del canal vectorial (punto 1 DEC-049) EJECUTADO punta a punta: audit → lever → gate-0 NO-GO pre-registrado → chunk-quality descartada (DEC-050). Nada shippeado; flag inerte; PR preparado para Alberto.** **(a) AUDIT de dimensionamiento** (`s68_audit_canal.py|yaml`, read-only, $0; 22 golds residual-answer × 28 hechos fuertes con las probes del D3): el cuello dominante NO es profundidad (rank 51-110: 2 hechos) sino **la MEZCLA del pool: 10 hechos con rank vectorial ≤50 [canal sano] FUERA del pool servido** — traza-1 confirmó en los 10 que el pool está dominado por keyword-stamps planos (0.8 ×12-28; hp002 17/17 por-encima-del-winner son stamps) sobre cosenos reales 0.52-0.68; + 11 EN-TOP5-pero-falla + 9 solo-débiles (≈50% no-retrieval) + 3 sospecha-gap; mecanismo verificado en el código vivo (dedup keyword-first `:1092-1104` + sort por similarity `:1106` + canal con category→0-filas + broad-5). **(b) Lever MERGE+L-i′** (revivió el plan-B s60 v4 actualizando 8 sesiones de sustrato): diseño v5→v6→v6.1 con dúo r1 FRESCO — sub-agente **12/12 confirmados 0 FP, 3 ALTOS** (F1: m7 contra control congelado sin dado = P(falso-disparo)~0.75 → banda de dado $0 con las 3 vistas del gate s67; F3: mi "content_search sin category" dejaba las 3c-i VIVAS con category=None = canal de ruido nuevo [s59 las ELIMINÓ] → réplica exacta; F6: mi (d2) round-robin SUSTITUÍA el interleave-por-source INTOCABLE del 5a [lo que arregló hp001/hp003/hp005/hp006/hp013/hp017] → (d2) MUERTA; F7: hp001[54]/hp011[65] inalcanzables con k=50 → techo +0..+3) + cross-model GPT-5.5 **6/6 confirmados 0 FP, 1 CRÍTICO** (Y1: la precondición-B dejaba "re-pesar" POST-medición → rama pre-registrada ANTES de medir [pre-check: 0 chunks con categoría canónica → 3c-i se eliminan]; Y4: banda declarada heurística-parcial con válvula pre-registrada). Build tras flag `MERGE_STRATEGY` (stamps|quota|cosine, default stamps = main bit-idéntico): `_merge_channels` extraído + etiquetado `_channel` + L-i′ condicional + `supplement_rescore_fn` en el 5a (lógica intocada); 310 tests; **PARIDAD end-to-end 39/39** (stamps+cache ≡ s67base congelado). **(c) GATE-0 (~$5): NO-GO firme por la letra** — m1: cosine captura **12/12 hechos alcanzables** al pool (quota 7/12: en hp008 los 36 stamps no dejan slots), hp001/hp011 NO entran (sanity F7 ✓); **m6: cosine 10/12 hechos al TOP-5 modal** (hp008 4/4 — la conversión que #32 negaba SÍ ocurre con el pool sano); m4 vista intacta; PERO **m7: quota 8/10 y cosine 9/10 PASS-control fuera de la banda de dado, con re-barajado profundo** (cat022-quota overlap 0/5 [su PASS vive de 4×0.85]; cat010-cosine 2/5) → condición dura (≤1) ni de lejos, válvula no aplica → **el A/B (~$25-30) NO se pagó** (calibración DEC-016b; el prior DEC-041(A) "NO-GO probable" CONFIRMADO y declarado pre-gasto en v6.1 §0). **(d) Bloque-2 ($0): los chunks servidos están SANOS** (11 EN-TOP5: lens 1.1-3.1K, 0 frag, 100% blurb, legibles; 9 solo-débiles: frag 0/5) ⇒ **chunk-quality DESCARTADA como cuello — el ~50% no-retrieval del residual es GENERACIÓN/síntesis** (la pregunta de Alberto respondida con dato; lever #10 al fondo). Candidata futura declarada CON forking-path (nació post-gate-0): variante ADITIVA del merge (ciclo propio + dúo). PLAN re-secuenciado: generación sube a punto 1 (2×2 + system-prompt + prompt-rerank [hp018: su hecho estaba EN pool y el rerank no lo sube ni sano]); re-gate CE SIN MATERIA (el canal no cambió). Instrumentos nuevos: `s68_audit_canal.py` (audit por-hecho con ranks/naturaleza) + `s68_gate0.py` (paridad/pools-con-traza-por-etapa/poollevel/rerank-n3/veredicto-con-banda) + flag MERGE_STRATEGY. Traza: DEC-050 + `evals/s68_{audit_canal,gate0_*}` + `evals/_s68_merge_design.md` (v6.1, local) + rama `eval/s68-audit-canal` → PR.
- **s69 (13 jun 2026)** — **A/B del lever de GENERACIÓN (completitud + guarda de fidelidad tras flag `GENERATOR_PROMPT_VARIANT`) = NO-GO; cierra la fase de levers-baratos del eval y abre el pivote a producto/deploy (DEC-051).** Tras el NO-GO del canal (s68), el ciclo de generación: audit de resolución s68b ($0, el eval SÍ tiene resolución) → **el bias #20 reapareció en 2 capas y costó 4 audits fijar la diana**: v1 diana=12 (cazado r1), v2 diana=8 vía re-audit-por-relato-del-juez (= bias #20 más sutil, cazado r2 por cross-model+sub-agente convergentes), cerrado solo con el re-audit a nivel de CONTENIDO → diana VERIFICADA = 4 sólida (cat008/cat020/hp005/hp014) + 1 recuperada (cat019) + 1 parcial (hp017); techo ~4-5. De camino se diagnosticaron los 4 reclasificados-a-retrieval ($0): hp006/hp009 corpus-gap (sin doc AFP-400/ZXe en corpus), hp013/cat016 within-doc-miss (doc servido, chunk fuera del top-5). Diseño v3.2 con dúo r1+r2 FRESCOS + 2 cortes cross-model (el GPT-5.5 fue el corte consistente; el sub-agente Opus = mismo modelo que el autor compartió el blind spot en r1 y lo cazó en r2 leyendo el canon): enmiendas clave = **verificación content-level de los flips decisivos antes de SHIP/rollback** (bias #20 aplicado a la decisión), flag ESTRICTO en el harness, available_models como SHIP-gate, paridad a nivel-de-CONSTRUCCIÓN (no output-LLM, que es no-determinista DEC-015 — corrección cross-model). Build tras flag (default base = prod inerte; suite 317; assembled_system_sha estampado). Consulta del dúo sobre "aprovechar el run" (§8): C1 medir available_models = TRAMPA (toca el call-site del run principal) → SHIP-gate; C2 K=10 = inútil (4/5 diana PARCIAL 5/5 unánime); C3 (predicción-vs-resultado) + C4 (delta output_tokens = proxy de verbosidad) $0 adoptados. **A/B (~$20): brazo fidelity (195 gen, 0 err, assembled_sha distinto) vs s67base re-juzgado en la misma tanda (mata el drift del juez). RESULTADO: Δ_net=0 — ningún gold de la diana flipeó a PASS; predicción §4 FALSADA + 1 regresión de conducta (cat011 clarify→answer, content-verificada: 'El modelo correcto es SDX-751' vs preguntar cuál) + verbosidad en 3 PASS-control.** La verificación content-level PAGÓ: el prompt SÍ añadió completitud (hp014 metió FET=20 y el límite 32) sin flipear Y rompió clarify → efecto modesto + colateral, no inercia (el Δ=0 del juez solo habría mentido "inerte"). **Hallazgo del re-judge: ±2 de varianza del juez** (re-juzgar idénticas respuestas base = F 5→7) → el ruler no distingue fiable un win de +1/+2 (SHIP exige +2 = el suelo de ruido). **NO-GO: flag inerte; NO se salta a Opus.** **Lectura estratégica + pivote (lo que Alberto pidió planear):** 3 ciclos de lever barato (s67 CE · s68 canal · s69 generación), 3 negativos; residual mapeado + ruler ruidoso → la fase de exprimir-el-residual está agotada → **pivote del eval a producto/deploy para los técnicos de ~sept**: #45 diagramas-datos (feature visible, eval-inerte) + fix de available_models (bug pre-existente: models_context contradice clarify) + scaffolding de eval orgánico (query_gaps + logging = el ruler que importa). Corpus sigue diferido (DEC-049). Prod intacto (flag default base); held-out NO tocado. Instrumentos nuevos: flag GENERATOR_PROMPT_VARIANT + `s69_ab.py` (veredicto con flips-decisivos para verificación content-level) + `test_s69_prompt_variant.py` (paridad a nivel de construcción). Traza: DEC-051 + `evals/s69_*` + `evals/_s69_generation_design.md` (v3.2) + rama `eval/s68-audit-canal` → PR.
- **s71 (13 jun 2026)** — **Re-análisis del residual dirigido por el pushback de Alberto = CORRIGE el pivote de s69; el cuello es RETRIEVAL (inanición del pool), atacable con fixes concretos (DEC-052).** Alberto cuestionó el pivote-a-producto de s69 ("hay que mejorar el bot antes de diagramas") y mandó 2 tracks ortogonales autónomos con dúo + compactar/cerrar. Ejecutados como **workflows adversariales batched** (rate-limits del servidor + apagones del equipo gestionados con resume desde run-id: los agentes cacheados vuelven al instante). **Track 1 (audit del ruler, doble-escéptico auditor→defensor, 13 candidatos):** solo cat012 sobrevive como gold-injusto→maybe-PASS (debatible); el defensor tumbó 4 que el auditor marcó injustos (cat009/cat011/cat019/cat020 = gold JUSTO, bot falló de verdad) → **el escepticismo de Alberto validado: el bot NO está infra-puntuado** (~11/39 como mucho, no la subida grande que intuí); 6 reclasificados a retrieval-miss (la info ESTÁ en corpus, no servida — hp006 era mi hand-wave de "corpus-gap"); 10 dudas sustantivas para Alberto. **Clasificación v2:** 16 retrieval-miss + 2 retrieval-family ≈ 18 de 29 (≈60%) = el cuello. **Track 2 (diagnóstico de retrieval, 17 golds, 6 mecanismos, 16/17 fixable):** raíz común = INANICIÓN DEL POOL aguas arriba — keyword_search limit=5 sin order (orden físico arbitrario; el chunk en pos 8 justo pasado el cap), broad-fallback vectorial capado a 5, reranker LLM lee solo content[:800] (el hecho en offset 2566 fuera de la ventana). Fixes CONCRETOS y baratos (subir límites/order/ventana del reranker), varios MEDIDOS end-to-end (hp003: preview 800→2400 → el reranker ya sirve el chunk correcto). NO es el canal-broad (NO-GO s68). **El pivote de s69 queda CORREGIDO: el residual SÍ es lever-addressable; declararlo "agotado" fue prematuro (faltaba la diagnosis per-gold) — lección a feedback_my_bias: el pivote-a-producto fue huida cómoda tras 3 NO-GO, cazada por Alberto.** Siguiente sesión (hand-off limpio): construir los fixes por prioridad (reranker-preview → broad-fallback → keyword-order → diversify-rescues), cada uno tras flag, medido con cobertura granular (s70, anti-±2) + content-level + dúo + gate PASS-control. Objetivo 11+ de 16 → PASS. Prod intacto; held-out intacto. Instrumentos: `s71_bundle.py` + workflows track1/track2 batched. Traza: DEC-052 + `evals/s71_*` + rama `eval/s68-audit-canal` → PR.
- **s72 (14 jun 2026)** — **Lever 2 (IDENTIDAD) construido tras flags: Brazo A (e-series) VERIFICADO end-to-end · Brazo B (rescate pm, cat013) = NO-OP hasta Lever 1 (DEC-053).** Arranque del build de los fixes de retrieval de DEC-052, empezando por el eje identidad (orden decidido con Alberto: Lever 2 antes que Lever 1, más barato/escalable/bajo riesgo). **Audit de campos de chunk** (workflow 4 lectores + síntesis + crítico, $0): scope Lever 2 = {alias + series-config + rescate pm}; **section_path = deuda nueva #48** (poblado con breadcrumbs curados pero 0 refs en `src/rag` → no llega al cliente/reranker; es lever de RANK no identidad → diferido); category/language/diagramas/doc_type/distributor = backfill diferido; cat001→Lever 1, C(hp006)/D(section_path) diferidos. Housekeeping: **restaurado `s68_audit_canal.yaml`** (re-run accidental que lo había pisado de 22 golds→1, recuperado de HEAD), typo #6→#43 en `s71_track2`, TECH_DEBT #48 logueado. **Brazo A (hp009/hp018) tras `LEVER2_IDENTITY`**: alias config-driven (`model_aliases` en `morley.yaml`) + entrada `series:` e-series (per-entry flag-gating nuevo en `series_registry`) + guard de colisión. **Dúo ×2 rondas frescas**: r1/diseño v1 (sub-agente 8 / cross-model 6) cazó que **C estaba roto** (strip tras `[:3]` en `extract_search_keywords`) y **B medía mal** (cat013 es `refuse-inference`, no `answer`) → C/D diferidos, B re-gateado; r2/forma del alias (sub-agente 5 / cross-model 5, **0 FP**, CRÍTICO convergente: **ZXe-como-member ownea el espurio ZXAE/ZXEE** — verificado `owners()` — → `members=[ZX2e,ZX5e]` reales, paraguas SOLO en `model_aliases`; me corrigieron el "plegar" que recomendé = sesgo #20 abstracción-cómoda; mantener `model_aliases` capa separada = más escalable). **VERIFICADO end-to-end contra corpus real**: A da la vuelta al pool de hp009/hp018 (**0→23/26 chunks reales** ZX2e/ZX5e, espurio 22/26→**0**, +25 docs de serie MI-530). **Brazo B (cat013) tras `LEVER2_PM_RESCUE`**: rescate en `_filter_to_query_models` (source_file-only + guarda `manufacturer==classify` + `len(core)≥4`, gated). **Dúo r3** (cross-model 7 + workflow 3-lentes [pass-control/guarda/medición] + síntesis): GO-con-enmiendas, hallazgos verificados EMPÍRICAMENTE corriendo el filtro real — **invariante single-model nunca cambia** (cap=2<failopen=3) → blast-control = 4 multi-modelo (cat008/hp012/cat022/cat007); **inversión cross-brand** por seed-fallback vía content-match → FIX source_file-only; **#11h está REVERTIDO** (solo SYSTEM_PROMPT). **VERIFY-FIRST (barato, antes de gastar en medir): B es NO-OP para cat013** — los 25 chunks SDX-751 (mal-atribuidos a LOCAL-360, manufacturer Notifier, token en source_file = precondiciones OK) **nunca entran al pool** (rank ~11, broad-fallback capado a 5) → el rescate no puede recuperar lo ausente → **cat013 bloqueado en Lever 1**. **330 tests verdes; flags default OFF = prod inerte (paridad probada); 3 rondas de dúo, 0 FP en todas** (el dúo me corrigió el rumbo 3×: C/B-gate, fold→no-fold, B-NO-OP — `feedback_my_bias` operando). **Resultado**: A = candidato a ship (retrieval probado; falta medir PASS = generador+juez); B = correcto+seguro+testeado pero diferido a post-Lever 1; cat013/C/D/cat001 → siguientes. Honestidad eval-driven: ningún gold medido como PASS aún. Siguiente: medir PASS-delta de A (A/B con cobertura granular s70 + gate PASS-control + pin embed_cache) → **Lever 1** (profundidad del pool: broad-fallback/keyword-order/diversify — desbloquea cat013 + el grueso de los 16). Prod intacto; held-out intacto. Instrumentos: flags `LEVER2_IDENTITY`/`LEVER2_PM_RESCUE` + per-entry flag-gating + `model_aliases` + 12 tests nuevos. Traza: DEC-053 + `evals/_s72_{lever2_design,alias_shape_decision,brazoB_review}.md` + `adversarial_review_log` s72 (6 entradas) + rama `eval/s68-audit-canal` → PR.
- **s73 (15 jun 2026)** — **Medición del Brazo A (identidad e-series) = FALLO→PARCIAL ×2 (GRIS, 0 regresión); se shippeó `LEVER2_IDENTITY` como tapón (PR #80) PERO resultó NO-OP en prod (DEC-054/055).** El `manufacturer-check` del handler bloquea fabricante+pm-compuesto ANTES del retrieval; el eval (bvg) y el prod-smoke lo BYPASEAN = **bias #40 (la lección más cara): "mejorar retrieval en eval" ≠ "mejorar el bot"; el smoke de un ship debe entrar por el HANDLER completo** → flag de vuelta a OFF (corregido en s74). Raíz estructural de identidad = detector LLM-en-ingesta (DEC-054), al gatillo de ingesta 30+. Harness endurecido tras workflow adversarial (`ab_verdict.py` capa de veredicto compartida + `s73_ab.py`, dúo Opus+cross-model 0 FP). 347 tests. Traza: DEC-054/055 + `evals/s73_ab_report.yaml` + rama `eval/s73-lever2-ship`. *(Entrada reconstruida en s74 — s73 cerró sin apendizar a HISTORY.)*
- **s74 (15 jun 2026)** — **Lever 1 BATCH construido tras flags + gate-0 judge-free = lift de retrieval REAL pero MODESTO → BANCADO (no shipped); el cuello de retrieval se FRAGMENTÓ → re-dirección a la RAÍZ DE DATOS (DEC-056).** Arranque: corregido el NO-OP de s73 (flag a OFF). **Re-secuencia con Alberto (×3 pushbacks, todos correctos, cazando mi fast-convergence):** (i) gate-fix #49 NO primero (sin técnicos hasta ~sept + Δ_eval=0 → deploy-prep); (ii) Lever 1 batcheado, NO 2c aislado (1 gold inmedible bajo ±2); (iii) la raíz de datos > más tapones de retrieval. **Build del batch (353 tests, paridad probada, default OFF = prod inerte):** 2a `LEVER1_BROAD_FALLBACK` (broad-fallback `5→effective_top_k`) · 2b `LEVER1_KEYWORD_ORDER` (keyword_search `order=page_number.asc,id.asc` + limit 5→15 — el dúo MATÓ el `order` por content_type del diag s71 = over-fit, verificado contra DB que entierra el winner bajo 'general') · 2c `RERANK_PREVIEW_CHARS` (preview LLM 800→2400). **3 rondas de dúo (sub-agente Opus + cross-model GPT-5.5, 0 FP en todas)** sobre rumbo/2c/batch — cazó: error fáctico en mi brief (vía-C = el lever L-i de s59 ya ROLLBACKeado, no "zona s68"); sobre-afirmación heredada "2c MEDIDO end-to-end" (era single-pass rerank-only, dado-confundido — bias #35/#38); el `order` over-fit de 2b. **Verify-first ($0, determinista):** el batch mete los canales correctos al pool en 15/15 (2a=VECTOR, 2b=MODEL). **Gate-0 (factcov-sobre-top5 = ¿las citas del gold en el top-5 del reranker?, modal n=3 + firm-up n=7, ~$15, judge-free → esquiva el ±2):** lift REAL pero afinado = target 48%→67% @2400 PERO **solo 2 golds fuertes+estables (hp008 0→3, hp002 3→6)** + 5 marginales (+1, dado-ruidosos) + **~3-4 REGRESIONES** (cat016 1→0, hp009 2→1, hp011 dado, **PASS-control cat022 1→0**). **2400 elegido por dato** (4000 midió peor −2; el CE Voyage lee su propio 4000 independiente del flag → no aporta aguas abajo; el generador lee content completo, no el preview). **Decisión Alberto: bancar tras flags (NO shippear)** — modesto + colateral + sin usuarios + PASS sin medir; el A/B (~$25) saldría casi seguro GRIS (±2 del juez + dado del reranker sobre 2 golds). El win granular de retrieval queda CONFIRMADO y bancable; el PASS se valida con el ruler que importe (eval orgánico / dual-judge). **Mapa de NO-PASS (workflow adversarial, 3 streams + verificación):** los 29 NO-PASS = ~16 retrieval + 5 generación + 4 corpus-gap + 2 borderline + 1 diseño + 1 gold-injusto (cat012, único; bias #20 verificado — el bot falla de verdad en 28/29). Overlay del batch → **el cuello de retrieval se FRAGMENTÓ**: 2 claros + 5 marginales + residual disperso (identidad 3, frontera 2, stamps 1) de +1-o-regresan, sub-suelo de ruido → **no hay siguiente lever de retrieval que valga** (re-entra en la fase de levers-baratos que DEC-051e cerró). Cuellos vinculantes = el ±2 del ruler (dual-judge = prerrequisito, DEC-051d) + las RAÍCES DE DATOS del SWAP. **SIGUIENTE BLOQUE (decidido con Alberto, tras 3 preguntas suyas afinando "la raíz"): NO el gate de prod #49 (prod, sin usuarios, eval-invisible → deploy-prep), NO backfill de categorías (#44 filtro-EQ muerto DEC-040 + freeze + el batch ya compensa), sino el detector de identidad (DEC-054) + backfill `product_model`** — el pm COMPUESTO rompe en DOS sitios: el gate del handler (prod) Y el filtro de modelo `_filter_to_query_models` DENTRO del retrieval (**eval-MEDIBLE**: cat013/hp009/hp018); partirlo arregla ambos de raíz + es la MISMA herramienta de escala 30+ (prep F2). **Lección a `feedback_my_bias`:** el dúo+workflows cazaron repetidamente mi fast-convergence (re-elevar #49 ya descartado, sobre-afirmar el batch, el `order` over-fit); Alberto cazó el resto. Prod intacto; held-out intacto. Instrumentos: flags `LEVER1_*`/`RERANK_PREVIEW_CHARS` + `scripts/s74_lever1_{verify,gate0}.py` + workflows (2c-nextstep-audit, nopass-map). Traza: DEC-056 + `evals/_s74_*` + `evals/s74_lever1_{gate0,firmup}.json` + `adversarial_review_log` s74 + rama `eval/s74-lever1-batch` → PR.
- **s75 (15 jun 2026)** — **Audit-first de la raíz de identidad (DEC-054): MEDIDO que el detector de identidad tiene ~0 palanca eval real → DIFERIDO a su gatillo (ingesta-30+), NO se construye como lever (DEC-057).** Arranque: `main` sincronizado tras el merge de s74 (PR #81, `f1829e6`). Releído el canon en frío, encontré una tensión real: el "Qué sigue §1" apuntaba al detector como siguiente bloque "eval-medible (~3 golds)", pero (i) su build está GATED a ingesta-30+ sin disparar, (ii) la lectura estratégica del PLAN dice lo contrario (pivote a deploy-prep). Lo puse sobre la mesa (Protocolo 2) → **Alberto eligió audit-first** (medir antes de decidir). **Audit ($0, read-only, `scripts/s75_identity_audit.py` → `s75_identity_audit.yaml`):** **(1) palanca eval ≈0** — crucé los 17 NO-PASS de retrieval (s71 track2) por el fix que de verdad los mueve: 9 Lever 1 (inanición del pool), 2 config-seam (hp009/hp018 = e-series en `morley.yaml`, Brazo A ya construido, **verificado**), 1 detector (cat013), 5 otros. El detector toca SOLO cat013 — **y cat013 es gold de CONDUCTA (`refuse-inference` cross-marca Detnov+Notifier, verificado en `gold_answers_v1.yaml`)**, no de retrieval-recall: el detector no lo arregla y podría EMPEORARLO → confirma DEC-054 (identidad ⊥ inanición del pool) y refina hacia abajo el sub-claim "eval-medible cat013/hp009/hp018" de DEC-056(f). **(2) escala = real pero ACOTADA, proxies ruidosos**: 78 pm-compuesto (1A sobre-cuenta: `20/20I` es modelo único con `/`), ≤114 mis-atribución (el proxy crudo dio 368 pero estaba CONTAMINADO por códigos de manual `MNDT-xxx`; regla-C lo cazó al inspeccionar ejemplos; el catálogo MISMO los heredó como pseudo-modelos = **la circularidad que DEC-054 predijo**), 18 clusters inconsistencia; concentrado en 3-4 marcas legacy. **Dúo (Protocolo 3, ALTO zona-de-dolor → cross-model INNEGOCIABLE; ronda FRESCA): sub-agente Opus + cross-model GPT-5.5, fuerte convergencia, 0 FP.** Confirmó DIFERIR pero corrigió mi **FRAMING** (sesgo #38/#39/#40): "≈0 medido + completo + BP" → honesto = "0 retrieval-net sobre **17/29** diagnosticados; cat013 es conducta; escala = proxy ruidoso; gap de selección (solo cat009/NFS-Supra plausiblemente identidad-adyacente fuera de track2, pero es lifecycle/source-conflict, no pm); falta freeze-contract". Verifiqué cada claim fuerte contra código/artefacto (regla C) antes de canonizar — el más decisivo (cat013=refuse-inference) confirmado. **Decisión Alberto: cerrar limpio sobre el audit corregido.** El valor de s75 fue exactamente parar de atribuirle al detector palanca que no tiene (gate/audit-primero funcionando, DEC-005/019). **SIGUIENTE BLOQUE (s76, decidido con Alberto): revisión EXHAUSTIVA en ultracode de cómo recuperar los NO-PASS de forma ESTRUCTURAL (no overfitting)** — confrontando que DEC-051e declaró agotada la fase de levers-baratos: ¿hay una clase de fix estructural (raíz-de-datos/generación/retrieval) que esa fase no agotó, distinguible del overfitting del ruler? Restricciones: ±2 del ruler (dual-judge), prior "fase agotada", mapa de 29 NO-PASS. **Lección a `feedback_my_bias`:** el dúo cazó otra vez mi sesgo de sobre-afirmar ("medido/completo/BP") — el audit estaba bien, el FRAMING no; honestidad eval-driven = declarar proxies ruidosos como ruidosos. 353 tests. Prod intacto; held-out intacto. Instrumentos: `scripts/s75_identity_audit.py` (audit reproducible) + `evals/s75_audit_brief.md`. Traza: DEC-057 + `evals/s75_identity_audit.{py,yaml}` + `adversarial_review_log` s75 + rama `eval/s75-identity-audit` → PR.
- **s76 (15 jun 2026)** — **Revisión estructural EXHAUSTIVA de los 29 NO-PASS en ultracode (DEC-058): la fase de levers de RETRIEVAL está agotada de verdad; la clase NO-tocada por esa fase es de DATOS (revisión/precedencia #4); PROD-REACH mide que el gate corta 7/9 mal antes del RAG (deploy-prep #49 sube); el ruler tiene un sesgo sistemático MEDIDO (no solo ±2).** Arranque: PR #82 (s75) mergeado; rama fresca `eval/s76-structural-nopass`. **Scout en frío** (PLAN/DECISIONS/ruler/handler) + un hallazgo que reencuadra: el gate manufacturer-check del handler (telegram_bot.py:292-339) corta ANTES del retrieval = bias #40 generalizado (el eval lo bypasea). **Workflow ultracode (29 agentes: 7 clases estructurales × diagnóstico + 3 lentes adversariales + síntesis; default escéptico, carga de la prueba del lado "hay clase nueva")** + **cross-model GPT-5.5 sobre el PLAN (8/8 confirmados, 0 FP)** → el dúo-Opus compartió blind spots del autor Opus; el cross-model cortó 2 puntos: el gate-CONTRATO no es droppable (separado de la mis-atribución #43 que sí se refutó), y el contrato de datos de #4 es judge-free (desacoplable del dual-judge). Alberto eligió ejecutar **3 acciones medibles** (no parar). **(1) PROD-REACH (medido, judge-free, `s76_prod_reach.py` → funciones REALES del handler, NO re-implementadas):** 9/29 cortados antes del RAG; **verificación regla-C en DB viva** (count_rows: CAD-150=103 · ZXe=157-207 · 40-40=486 · RP1r=581 Morley+Notifier · ADW535=201 solo-Securiton) → **7 cortes ERRÓNEOS** (catálogo de `lookup_model_manufacturer` desincronizado con el corpus + regex RP1[RR] en `_NOTIFIER_PATTERNS`) + 2 frontera OEM-relabel (ADW/ASD). Confirma el mecanismo exacto del NO-OP de LEVER2_IDENTITY (ZXe cortado antes del RAG). **reach ≠ PASS** preservado. **(2) Contrato de revisión #4 = SPEC** (`_s76_revision_contract_spec.md`, diseño no-build): árbitro de precedencia (revisión=latest-wins vs variante-regional vs OEM vs multi-parte vs datasheet; ante duda NO supersede) + validación judge-free (paridad de POOL); gated a ingesta F2; cat008 NO es de #4 (OEM-relabel→identidad). **(3) Sonda dual-judge HOLÍSTICA (medido, `s76_dualjudge_sonda.py`):** resolví la tensión interna por regla-C (s47 midió los EJES del scorer, no el ruler de veredicto → el dual-judge holístico NUNCA se midió-primero); medido = **30.8% desacuerdo cross-model, 11/12 Claude más LAXO**; cat019/cat020 = triple confirmación de sesgo del juez (audit humano should_be=PASS + Claude=PASS vs GPT-PARCIAL-estable) → **2 falsos NO-PASS (+cat012 debatible)**; GO/NO-GO: "2º-juez+voto"=NO (laxo global, no toca el ±2 sampling), recalibrar-rubric-por-principio = real pero gated. **Corte cross-model de CIERRE sobre los hallazgos MEDIDOS (7/7 confirmados, 0 FP):** cazó 2× mi sobre-afirmación (bias #42: "única clase", "cierra #40 de raíz", "2-3 falsos NO-PASS") + 1 inconsistencia real del spec (cat008) → **canonizado en la versión CORREGIDA, no la grandilocuente**. **Recomendación: 3 builds futuros gated, NADA shippeado** — gate-fix #49 sube (defecto latente medido en prod, deploy-prep) · contrato #4 (build a ingesta) · rubric del juez (organic-eval). 353 tests verdes; sin cambio de código de prod (solo instrumentos de medición + specs + docs); prod y held-out intactos. **Acumulado de control: 1 workflow (21 lentes) + 2 cortes cross-model (8/8 + 7/7), 0 FP.** Lección a `feedback_my_bias` #42: la sobre-afirmación reincidió sobre RESULTADOS MEDIDOS (no solo proxies como s75) — el cross-model es el corte fiable cuando autor+sub-agente son ambos Opus. Instrumentos: `scripts/s76_{prod_reach,dualjudge_sonda}.py`. Traza: DEC-058 + `evals/s76_*` + `evals/_s76_*` + `adversarial_review_log` s76 + rama `eval/s76-structural-nopass` → PR.
- **s77 (16 jun 2026)** — **Gate-fix #49 CABLEADO = fall-through manufacturer-aware (Option D, PR #85): el gate del handler ya no da falso-refuse cuando la marca está en DB pero el modelo es un nombre de FAMILIA; corrección de PROD judge-free, reach≠PASS, CERO delta de eval (DEC-059).** Arranque audit-first (item 1 de "Qué sigue" de s76; Alberto eligió "medir respuestas → dúo → cablear"). **(a) Audit por-modelo (`s77_gate_audit.py`, DB real) CORRIGE el framing de s76:** los 6 catalog-miss NO son "modelo ausente/catálogo desincronizado" sino **FAMILIA↔VARIANTE** — la gold pregunta por el nombre de familia (CAD-150/ZXe/40-40), que NO existe como `product_model`; solo existen las variantes (CAD-150-8/R, ZX2e/ZX5e, 40-40L/M/I); `lookup_model_manufacturer` hace `eq` exacto → None. Los "103/157/486 chunks" de s76 eran SUMAS sobre variantes (content literal "CAD-150"=1). Para los 6: marca correcta+en-DB, y `_filter_to_query_models` (substring-norm) recupera las variantes en fall-through (`filtro_recupera=True` ∀6). **(b) Medición judge-free del fall-through (`s77_fallthrough_measure.py`, réplica de `_process_query`, baseline prod-inerte):** 6/6 conducta MEJOR que el falso-refuse — answer-de-marca-correcta + cat013 refuse-inference ✓ + cat021 clarify ✓; cero alucinación cross-brand. **(c) Dúo (Protocolo 3, sub-agente Opus + cross-model GPT-5.5, #7): 6 findings / 6 confirmados / 0 FP** — el cross-model cazó (2ª sesión seguida) mi sobre-afirmación sobre RESULTADOS MEDIDOS ("refuta el riesgo"/"aguanta") que el sub-agente Opus dio por honesta = blind-spot compartido dúo-Opus → rebajado a "evidencia preliminar" (bias #42 reincidente). Hallazgo más fuerte (cross-model): riesgo modelo-VECINO. **(d) Huecos cerrados (`s77_regression_probes.py`, K=3):** el path FIEL de Option D admite/rehúsa 3/3 (cad151 vecino-inexistente ADMIT+desambigua; zxe+sdx cross-brand REFUSE) — el filtro descarta el vecino-exacto (`cad151 ⊄ cad1508`) y fail-opens a pool DIVERSO; la sustitución 40/41R→40/40R SÍ ocurre pero es PRE-EXISTENTE+off-path (el patrón no extrae "40/41R" → no llega a la rama del modelo; prod actual ya cae al RAG por la rama solo-marca). **(e) Cable (Option D, `telegram_bot.py:315`, quirúrgico, una rama):** si `manufacturer_in_db(mentioned)` → fall-through; refuse solo si la marca también ausente; rama `CUT_A_mismatch` (RP1r/OEM) intacta. **Smoke por el HANDLER REAL (`s77_handler_smoke.py`, lección #40): 10/10** — 6 FALL_THROUGH, Siemens-ausente REFUSE, RP1r REFUSE_A_mismatch, control+saludo sin cambio. 353 tests. **reach≠PASS y CERO delta de eval — ESTRUCTURAL** (el harness `test_bot_vs_gold.py:101` llama `retrieve_chunks` directo y bypasea el gate, verificado por el sub-agente → cambiar el gate NO mueve el número; es puro fix de PROD). NADA en prod aún: PR #85 contra main (Alberto mergea → Railway despliega; rollback = revertir el commit, sin migración/datos). Los 3 mismatch (RP1r/ASD/ADW=Securiton-OEM) siguen su curso por el contrato de identidad #49. **Lección a `feedback_my_bias` #42:** la sobre-afirmación sobre medidas reincidió; el cross-model es el corte fiable cuando autor+sub-agente son ambos Opus. Instrumentos: `scripts/s77_{gate_audit,fallthrough_measure,regression_probes,handler_smoke}.py`. Traza: DEC-059 + `evals/s77_*.yaml` + `_s77_gate_fix_design.md` + `adversarial_review_log` s77 + PR #85, rama `eval/s77-gate-fix-49`.
- **s78 (16 jun 2026)** — **Curación de identidad del corpus (ground-truth de Alberto, 4 familias) → BACKFILL A aplicado en prod (eval-inerte) + backlog D1-D6; lecciones HNSW + eval-economía (DEC-060).** Plan "1+2" de s77: Alberto eligió atacar la identidad del dato "sin trampas al solitario". **Curación (memoria `reference_*`):** CAD-150 (familia↔variante); Morley ZX (ZX1e/2e/5e por lazos; **ZXSe**=ZX1Se/2Se/5Se/10Se familia MODERNA en `MIE-MI-600` tagueado `unknown`; ZXR50A con teclado vs P sin; **"ZXe" no existe→clarify**); RP1r (4 productos: **RP1r-Supra=Notifier** [el corpus lo tenía Morley ~312 ch], VSN-RP1r=Morley, RP1r-a-secas=Notifier extinción, OPC-RP1r=software); FAAST (System Sensor LT-200/Xtralis FLEX, Honeywell; **NFXI-ASD=Notifier** [corpus Securiton]); **Securiton=marca APARTE** (Detnov la vende), NO Honeywell. **Paso 0/0b (diagnóstico judge-free, $0):** de los 16 retrieval-miss solo ~4 son identidad-bloqueada; **~12 son retrieval-MECÁNICO** (el filtro substring ya absorbe el colapso de familia) — **confirma s75 (identidad ⊥ el cuello del eval)**; 3 no eran retrieval (cat013 refuse/cat021 clarify/hp009 identidad). **Partición honesta:** Backfill A = correcciones de etiqueta primaria standalone+eval-inertes; findability de variantes (ZXSe/ZX1e) NO va en A — VERIFICADO `extract("ZX5Se")=[]` (el tag combinado NO basta sin split del catálogo) = D1; levers de retrieval ~10 = D2; multi-marca (grupo Honeywell, TECH_DEBT #5 trigger cumplido) = D3. **Backfill A APLICADO (`s78_identity_backfill.py`, s64-style, reversible):** FIX1 RP1r-Supra→Notifier 312 + FIX2 NFXI-ASD→Notifier 135 (+7 docs) + FIX4 NFXI-FLX 83 + canon ZX50 126/ZXR50A-P 18/RP1r 65 = 447 mfr+292 pm. Verificado: count-match → before-snapshot (rollback) → apply (GO Alberto) → `from`==0 ∀ → **smoke handler 4/4 LIVE ("Notifier RP1r-Supra" deja de dar mismatch-refuse)** → **eval-freeze 9/39** (vs ~10/39 base = ruido del juez ±2/K-inestab; CERO PASS→FALLO; cat022 intacto). **Lección HNSW (reusable):** 1er apply falló por `statement timeout` (UPDATE masivo re-inserta cada fila en el grafo HNSW); estado verificado=rollback atómico limpio, 0 parciales; fix=**PATCH en lotes de 10**. **Dúo #8: 7/7+5/5, 0 FP** — cazó la cifra inflada FIX1 (624→312, bias #42/#43 cifras REINCIDENTE, esta vez TAMBIÉN por el sub-agente Opus vía DB) + rollback-sin-snapshot-documents + smoke-ZX5Se-vacuo, corregidos pre-apply. **Eval-economía (Alberto):** corrí el eval-freeze a un cambio probadamente inerte = info marginal por coste; regla = reservar el eval pagado para lo que MUEVE el número (D2). reach≠PASS, ~0 eval (corrección de prod+escala). Backlog D1-D6 preservado (spec §DIFERIDO + memoria). Traza: DEC-060 + `scripts/s78_*`/`retrieval16_*`/`cad150_corpus_probe` + `evals/s78_*` + `reference_{detnov-cad150,morley-zx-rp1r,faast}` (memoria) + `adversarial_review_log` s78 + rama `eval/s78-identity-backfill` → PR.
- **s79 (17 jun 2026)** — **Gate pre-D2: el matcher de recall está ROTO y contaminó las conclusiones de retrieval de la sesión; el plan de revisión de los 30 NO-PASS VIVE pero su instrumento necesita arreglo (dúo CON-CAMBIOS); lección sobre-instrumentación + sobre-corrección (DEC-061). NADA shippeado a prod.** Alberto pidió, antes de D2, entender los flips del eval + el porqué del fallo de retrieval (gate antes del lever). **(a) Flips 9-vs-10 = ruido del juez (verificado por-gold):** 9/39 (`test_bot_vs_gold` single-pass) vs 10/39 (s67base K-mayoría) — los 5 golds que difieren eran TODOS K-inestables; cat007 NO flipeó. **(b) HALLAZGO mayor (regla-C, SQL + dúo, cazado por el "¿estás seguro?" de Alberto): `chunk_has_quote_strict` (`strict_match.py:122`) está ROTO** — FP (`all(a in nc)` con `in` crudo: `'24'∈'240'`, `'2222'`∈cualquier chunk) + FN (prosa OCR `overlap≥0.8`). Mis probes s79 (`recall_deathstage`/`vecrank`/`burial`) lo usaban → **rank-53/64/87, "within-doc muerto" y "corpus-gap cat016/cat007" NO son fiables**; cat016/cat007 SÍ están en el corpus (SQL). A re-medir con predicado limpio (bias #35: no heredar el suelo). Construí `audit_locator` (anchor_present + source-tie per-fact + token-containment OCR-robusto; 5/5 tests con los casos FP/FN reales). **(c) Identidad FAAST (SQL, accionable):** la familia FAAST LT-200 mal-tagueada en 3 manuales — `I56-6574`(autónomo,OEM System Sensor)=`FAAST LT-200`; `I56-6575`(addressable)=`LT-200` (ES=System Sensor/EN=Notifier inconsistente); `I56-6577`(addressable NFXI-ASD11/12/22, OEM Notifier-exclusivo)=`ASD11`. El tag `ASD11` excluye el chunk del failsafe ante query "FAAST LT-200" (`_filter_to_query_models`) → candidato a backfill s78-style = **mejora de retrieval VÍA IDENTIDAD** (distinta de los levers de ranking cerrados por DEC-056). **(d) Gold-flags:** cat007 "relé de avería FAILSAFE/se desenergiza" = INFERENCIA del autor (0 ocurrencias en el manual; lo documentado = "señaliza en modo servicio + al desconectar la alimentación + no enclavado") — correcta + dúo-vetada, NO fabricada → flag gold-design (estricto-vs-inferencia-útil, DIFERIDO); **hp009 = answer family-genérico** (EOL invariante en la e-series; NO "clarify" en bruto — corrige la memoria), hp018 = mixto (nº sirenas variant-específico). **(e) Audit de los 30 NO-PASS por raíz DISEÑADO** (cascada CORPUS-GAP/RETRIEVAL-MISS/RERANK-MISS/SINTESIS + predicado bimodal + ejes generación/gold-design/judge) → **dúo (workflow 7-lentes Opus + cross-model GPT-5.5) = CON-CAMBIOS, `proceed_to_30=FALSE`:** el quote-path del funnel (`audit_retrieval_funnel.py:132`) AÚN usa el matcher roto para el ~63% de hechos; el juez semántico C2 NO está implementado (descrito como hecho = bias #44); C6 invertido (`audit_locator` tiene 2 fixes que el funnel NO tiene → portarlos); C3 comparaba 2 rerankers distintos (ruido de método) en vez de K-maj del reranker de prod; C4 sin banda de error + fuente de veredictos equivocada (s45, no k5); C5 cobertura sobre el matcher roto + eje gold-design circular contra `conducta_esperada`. **(f) Lección sobre-instrumentación + sobre-corrección (`feedback_my_bias #45`):** la sesión espiraló construyendo aparato cada vez mayor (probes→`audit_locator`→audit de 30); al frenar el dúo, SOBRE-CORREGÍ a "abandonar el audit" (bias #30) cuando el dúo decía CON-CAMBIOS (arreglar y correr) — Alberto lo cortó, el audit VIVE; + "28/29 localizado" era validación CIRCULAR (auto-calificada). El cross-model cortó mis over-claims 4 rondas (6ª-7ª sesión = control ESTRUCTURAL). **Qué sigue:** gold-review D6 (cat007/hp009/hp018, $0, primero) → backfill identidad FAAST LT-200 (s78-style) → arreglar el instrumento del audit (predicado limpio en el funnel + coste acotado + banda error + fuente k5) → correr el audit de los 30 → priorizar. dual-judge gated (organic-eval ~sept). 353 tests; prod y held-out intactos. Control: 4 cross-model + 1 workflow 7-lentes, 0 FP que sobrevivan regla-C. Traza: DEC-061 + `scripts/{audit_locator,s79_*,test_audit_locator}.py` + `audit_retrieval_funnel.py` + `evals/_s79_*.md`/`s79_*.json` + `adversarial_review_log` s79 + rama `eval/s79-retrieval-audit-gate`.
- **s80 (17 jun 2026)** — **Backfill de identidad de la SERIE FAAST LT-200 APLICADO en prod (DB-only, findability de serie viva) + criterio gold D6 (core/supp=importancia) + hallazgo latente: el catálogo de modelos de prod está congelado en s55 (DEC-062/063).** Retomamos el plan s79. **(a) D6 gold-review ($0):** cerré el criterio con cross-model (cita BP TREC vital/okay/RAGAS/DeepEval/ARES) — `core`/`supplementary` codifica IMPORTANCIA, NO provenance; demotar inferencias correctas a supplementary era sobre-corrección mía (las vacía del conjunto vital + las saca del audit `audit_retrieval_funnel.py:325` + baja la completitud del árbitro atómico `atomic_scorer.py:289` — el sub-agente Opus cazó que mi "scorer inerte a tipo" era FALSO). Inferencia válida si predicado⊆documentado; no-invención en el OUTPUT (`undue_inference_check`); **el eval CANÓNICO (juez holístico `bvg_kmajority`/`test_bot_vs_gold` sobre `gold_answer`) es INERTE a `tipo`** → core/supp gobierna el audit/diagnóstico, NO el veredicto (responde el pushback de Alberto "¿necesitamos core/supp?"). cat007 failsafe=inferencia VÁLIDA (sin editar tipo); hp009/hp018 `answer` correcto. **(b) Crux cat007 RESUELTO AL PÍXEL** (Alberto: "¿no deberías evaluarlo tú al píxel sin preguntarme? si no, no escala"): render p5 de los 3 QIGs → standalone (6574) vs addressable (6575/6577) DIFIEREN (6574 relé PREALARMA; addressable lazo) PERO los hechos de cat007 (alarma/avería NC-C-NA, sirenas 47kΩ, 2/0,5A, 10⁵, no-enclavado) IDÉNTICOS en las 3 → alcanzable vía 6574 → **el backfill NO arregla cat007** (downstream: rerank/gen/es-en/gold). Corrige la premisa de la memoria s79. **(c) Backfill APLICADO (`s80_faast_backfill.py`, s78-style, GO de Alberto):** FX1 (6575 `LT-200`→`FAAST LT-200` 78) + FX2 (6575-ES mfr→Notifier 41) + FX3 (6577 `ASD11`→`FAAST LT-200` 73); count-match→snapshot (`evals/s80_faast_backfill_snapshot.json`)→apply lotes-10→`after` from=0 ∀; reversible. **Findability de serie VIVA, verificada contra el estado REAL de prod (catálogo s55 + DB):** "FAAST LT-200" alcanza standalone+loop+ASD (antes solo standalone; se extrae por patrón estático = catalog-independiente). Smoke COULD-regress OK (Morley/System Sensor siguen; "NFXI-ASD11"→MULTI doc=tradeoff declarado). DB-only (como s78), NO deploy de código. **Decisiones (Alberto):** manufacturer=`Notifier` pragmático (el seam multi-marca NO existe → System Sensor regresaría findability Notifier/Morley; OEM real+Morley→D3); 6577 pm=`FAAST LT-200` serie (modelo NFXI-ASD11 recuperable como metadata pero el path bare de usuario se pierde-hasta-D3 — corregí mi erróneo "no se pierde", cross-model). **NO eval-inerte** (≠s78: product_model visible al generador `generator.py:452` + mueve selección) → guardarraíl findability+ por handler real + no-regresión; riesgo cross-gold BAJO (DB-only localizado: solo cat007 en la familia FAAST; "LT-200" sigue substring; ASD535/532=Detnov token distinto). **(d) HALLAZGO LATENTE (DEC-063):** al regenerar el catálogo (GUARD-REGEN) el diff salió MUCHO más amplio que FAAST → regla-C: `data/model_catalog.json` congelado en s55 (`8876e56`); `catalog.py:_load()` LEE el json (NO reconstruye) → prod corre un detector s55; s64/s77/s78 no están en el catálogo. **PERO no es bug activo (verificado en código): el gate lee la DB LIVE** (`lookup_model_manufacturer` retriever.py:716, `manufacturer_in_db` :788 = httpx Supabase) → la decisión de MARCA (gate-fix #49) es live → **s77/s78 SÍ vivos en prod**; el catálogo-stale solo afecta `extract_product_models` (detección, fall-through seguro) = LATENTE. GUARD-REGEN NO desplegado (bundlea s55→hoy = blast radius → tarea separada). **Control: 2 cross-model (6/6+7/7) + 1 workflow 3-fases, 0 FP; #42/#43 reincidió 3× sobre framing ("scorer inerte"/"no se pierde"/"estructural"/"FINAL"), cortado por el cross-model cada vez = control ESTRUCTURAL estable.** Lección `feedback_my_bias #45/#46`: verificar dominio AL PÍXEL yo mismo (preguntar no escala a 30+); sobre-afirmación de framing reincidente. Mapas de identidad RP1r/FAAST/ZXSe-vs-ZXe reconciliados con Alberto + DB (fantasma del ~600 RP1r corregido a 312/314, #44). reach≠PASS; 353 tests; prod (DB) tocado + reversible, held-out intacto. **Qué sigue:** D1 (backfill ZXSe `MIE-MI-600 unknown→familia` + split ZXe `ZX2e/ZX5e`, con split de catálogo + regen) → instrumento del audit (predicado limpio + banda error + k5) → audit de 30 → priorizar. Backlog baja prioridad: re-sync catálogo s55→hoy (full no-regresión) + CI anti-drift. dual-judge gated (~sept). Traza: DEC-062/063 + `scripts/s80_faast_backfill.py` + `evals/s80_faast_backfill_snapshot.json` + `evals/_s80_*.md` + `adversarial_review_log` s80 + memoria `reference_{faast,morley-zx-rp1r}` + rama `eval/s80-faast-identity-backfill`.
- **s81 (17 jun 2026)** — **Instrumento del audit ARREGLADO (DEC-061) + audit de los 30 NO-PASS CORRIDO → distribución de raíces (DEC-064). Contrato de autonomía nuevo (`feedback_autonomy`).** Alberto pidió MÁS autonomía (en sesiones recientes requerí input constante) → acordamos: actúo-y-reporto, el DÚO (no Alberto) es el anti-bias, stop-line=el merge a main lo da él. **Re-secuencié D1 detrás del audit** (orden de DEC-061, no el del cierre s80): verifiqué al píxel que NINGÚN gold canónico (`gold_answers_v1.yaml`) apunta a ZXSe → la findability-D1 es eval-inerte + dispara el blast-radius del catálogo (DEC-063); el audit localiza dónde importa la identidad ANTES de pagar eso. **(a) Instrumento (los 5 defectos de DEC-061(e); `audit_locator.py`+`audit_retrieval_funnel.py`):** retiré el matcher roto `chunk_has_quote_strict` del funnel (conservado solo para `bvg_kmajority` legacy); predicado limpio `fact_match_score` **VALOR-EXIGIDO** (el datum distintivo DEBE estar [cov>0] + el `texto` como CONTEXTO que desambigua → mata el FP 'prosa del enunciado sin el dato' Y el FN del token-corto NC-C-NA); `measurable` segrega no-medibles (single-digit `1 A`/`4 circuitos`, frases sin tokens → juez semántico DIFERIDO); confianza por SCORE del match (borderline=[0.55,0.70)), no a priori; source-tie fail-open + **primario-vs-corroborador** (flag PRIMARIO-NO-RECUPERADO); fuente de veredictos k5; K=1 (reranker temp=0, jitter nulo verificado). **(b) Dúo #9 (3 rondas, 3 cross-model GPT-5.5 + 3 sub-agente Opus, 0 FP), cada ronda cazó defectos REALES:** r1/spec (anchors-FP-mismo-manual, FIX-A↔D, short-token-FN); r2/diff (**REGRESIÓN que YO introduje** — el refactor rompió `fact_probe`/`_chunk_has`/`present_in` que `bvg_kmajority` importa, cazada por GREP regla-C NO el dúo → legacy restaurado; + corroborador-enmascara-primario [hp018: pool=MI-310, MI-530 primario no entra] + tier-a-priori-colapsa-banda); r3/diff (FP '`1 A` marcado SINTESIS por la prosa sin el dato' → valor-exigido). **Cap en r3 (sin round-4): el valor-exigido se verificó por TESTS, anti-#45.** El cross-model cazó framing que el sub-agente Opus (mismo modelo) compartía = control ESTRUCTURAL (consistente s77/s80). **(c) HISTOGRAMA de los 30 dev NO-PASS** (~93 hechos core medibles + 19 no-medibles; `evals/dec003_retrieval_funnel_noTgt_llm.yaml`): **RETRIEVAL 28-38** (recall: hecho EN el manual, NO en pool-50) **≈ SINTESIS 34-39** (el generador lo VIO → gen/gold/juez) **>> RERANK-MISS 6-7 >> CORPUS-GAP 9** (riesgo FN); 16 borderline; **4 PRIMARIO-NO-RECUPERADO** (cat011/cat019/hp001/hp018). **(d) LECTURA:** **DEC-056 (RANKING agotado) CONFIRMADO** (RERANK ~7% → el reranker NO es el cuello) **pero MATIZADO** — el RECALL (~38%, el chunk ni entra al pool = lever DISTINTO del ranking) NO está cerrado, y es en parte IDENTIDAD (los 4 PRIMARIO traen el corroborador) → **RE-VALIDA D1/D3 como lever de eval VÍA el bucket RETRIEVAL** (no findability-por-sí-misma); el instrumento-primero PAGÓ (localizó dónde importa la identidad — cierra el fork del inicio honestamente). **Caveats:** cubre 83% de los hechos (19 no-medibles=juez semántico diferido); corroborador cuenta como SINTESIS (decisión semántica defendible, flags PRIMARIO marcan lo peor); 9 CORPUS-GAP=riesgo FN es-en/OCR. **Chip spawneado:** fix robustez citations-str en `bvg_kmajority._locate_missing` (mismo bug que arreglé en `target_servable`). reach≠PASS, NADA en prod (toda la sesión = instrumento + diagnóstico, código branch-local); 353 tests; held-out intacto. **Qué sigue:** atacar los cuellos co-binding — (1) recall/identidad: los 4 PRIMARIO-NO-RECUPERADO + el bucket RETRIEVAL (D1/D3 — por qué el primario no se recupera) AHORA con eval-leverage demostrado; (2) generación/gold de los SINTESIS (gold-review + dual-judge ~sept) vía el deep-dive por-SINTESIS (C5, diferido); juez semántico para los no-medibles. Traza: DEC-064 + `scripts/{audit_locator,audit_retrieval_funnel,test_audit_locator}.py` + `evals/_s81_audit_instrument_spec.md` + `evals/dec003_retrieval_funnel_noTgt_llm.yaml` + `adversarial_review_log` s81 (dúo #9, 3 rondas) + memoria `feedback_autonomy` + rama `eval/s81-zx-d1-audit-instrument`.
- **s82 (17 jun 2026)** — **Investigación CORPUS-GAP (prioridad de Alberto) + plan de ataque PRIMARIO/RETRIEVAL (DEC-065). Workflow 29-agentes Opus + cross-model GPT-5.5 = dúo #10, 0 FP. NADA en prod (diagnóstico).** Tras mergear PR #88, Alberto pidió planear el ataque a los 4 PRIMARIO + bucket RETRIEVAL y, como PRIORIDAD, investigar el CORPUS-GAP ("estoy casi seguro de que no existe"). **Herramienta:** `scripts/corpus_grep.py` (ILIKE full-corpus de chunks_v2 por contenido). **VEREDICTO (acotado, post-cross-model): los 9 CORPUS-GAP del audit s81 son FALSOS NEGATIVOS del matcher léxico — 0 reales.** El valor está VERBATIM en el corpus (casi siempre el manual OBJETIVO del gold); **causa raíz = es-en** (LlamaParse extrae la columna EN de manuales multilingües: cat013 "closed loop", cat007 NA↔NO) **+ OCR/acento** (cat011 "INTRÍSECA" sin N, hp010 acento) **+ literal-compacto** (NC-C-NA, 99+99) **+ filename≠doc-nº** (cat020). Es el residual es-en que s81 declaró como caveat del juez-semántico-DIFERIDO → PROBADO material (fabricó el bucket entero). Verificado: verificadores frescos del workflow (volcaron los chunks REALES de la DB) + **regla-C propia al píxel** (cat007 tabla-relé FAAST; cat020 `DXc_Manual variaciones de mercado` INGERIDO p6 defaults España; hp013 EEPROM ADW535 — dudé de cat007/cat020 y la evidencia CONFIRMÓ el workflow). **Histograma corregido: CORPUS-GAP 9→0** (reubican a RETRIEVAL o downstream-gen, p.ej. hp012=conflicto US-ES). **PRIMARIO: 2 de 4 reales** — cat019/hp001 = FALSO POSITIVO de source-naming (token gold `CAD-250-MC-380-es` ≠ filename `CAD-250_Manual-Configuracion-MC-380-es-2026-c`; el primario es #1 del pool = artefacto del INSTRUMENTO, no del bot); cat011 = real-pero-reach≠PASS (el bot ya clarifica bien); hp018 = real (model-filter 'ZXe'→pm equivocado). **Cuello real = RECALL** (DEC-056 SIGUE: ranking agotado, recall es lever DISTINTO): model-filter-excludes ×3 (hp018/hp002/hp006) + recall-frontier-vector ×6 (cat011/hp001/cat017/hp005/hp008/cat016) + source-naming-artifact ×2 (instrumento). **PLAN A/B/C** (separar PROD-del-bot de INSTRUMENTO/GOLD): **A** instrumento/gold no-eval (A1 matcher CORPUS-GAP es-en/OCR-aware [raíz; versionar/congelar — cambia históricos; anclar juez semántico a fuente]; A2 matcher PRIMARIO slug-laxo; A3 gold cat011); **B** PROD model-filter, MEDIR (B4 hp018 **CANDIDATO** flip `LEVER2_IDENTITY=ON` [pool 0→11=reach, NO PASS]; B5 hp006 series-registry AFP-300/400; B6 hp002 broad-fallback+category); **C** PROD recall-frontier, MEDIR (C7 within-doc/family diversify ± ef_search [contrato+métrica de regresión]; C9 cat016 synonym-aware [duro]; C8 cat011 opcional). Orden A→B4→B5/B6→C7→C9. **El cross-model (dúo #10) cazó mi over-claim de framing OTRA VEZ** (#42-#47, 6ª sesión seguida: "prior 100%/PROBADO"→"los 9 auditados"; "0 ingesta nueva"→"para estos 9"; hp018 "fix verificado"→"candidato, medir end-to-end") = control estructural estable. Honesto: B/C sin delta medido (reach≠PASS en cat011/cat019/hp001); A no mueve la métrica (mejora el diagnóstico). Traza: DEC-065 + `scripts/corpus_grep.py` + `evals/_s82_findings.md` + `evals/_s82_worklist.{py,json}` (local) + `adversarial_review_log` s82 (dúo #10) + rama `eval/s82-recall-corpusgap`. **Qué sigue:** ejecutar el plan (fork abierto: A1 matcher es-en vs B4 hp018-flip primero).
- **s83 (18 jun 2026)** — **El pre-filtro vectorial family-aware (headline construido) = NO-OP MEDIDO → revertido; el lever de los model-filter-excludes es LEVER2_IDENTITY (resolución de identidad), que recupera el manual correcto pero reach≠PASS. Dúo #11 (sub-agente Opus + cross-model GPT-5.5) cazó el confound. NADA en prod/mergeado (DEC-066).** Alberto pidió plan-detallado-primero + máxima autonomía (ultracode). **5 rondas de pushback en plan-mode** afinaron el rumbo: (1) ¿categorías o modelos? → modelos (los golds son model-specific; la categoría es legacy/rota, TECH_DEBT #44, DIFERIDA); (2) no está en prod → muévete más rápido; (3) el filtro de modelo ¿pre o post-retrieval? → los léxicos PRE-filtran (imatch), el vectorial NO (post-filtro fail-open) = su punto 1; (4) ¿a nivel doc o chunk? → DOCUMENTO/familia (BP: el `product_model` se asigna a nivel doc `metadata.py:15` y se hereda; el reranker sube la variante); (5) ¿el doc puede pertenecer a varios modelos? → SÍ, y la infra YA existe (`series_registry`: members + shared_docs + `passes_nivel2`). **Construí (Pieza 1c)** el pre-filtro FAMILY-AWARE del canal vectorial (over-fetch 200 SIN filtro en el ANN + filtro client-side recall-safe `passes_nivel2 ∪ unknown`, familia-primero-relleno, fail-open, flag `MODEL_PREFILTER`). **VEREDICTO (aislamiento 2×2, funnel judge-free, hp018): el pre-filtro SOLO = INERTE (PRIMARIO False); `LEVER2_IDENTITY` SOLO recupera el primario (False→True, MIE-MI-310→MIE-MI-530).** Mecanismo: al resolver ZXe→ZX2e/ZX5e los canales LÉXICOS (que YA pre-filtran por modelo) recuperan el manual; el vectorial no necesita pre-filtrar (+ el post-filtro `_filter_to_query_models` niega el unknown-inclusion → redundante). **→ el cuello era la RESOLUCIÓN de identidad, no el canal vectorial; el lever real = `LEVER2_IDENTITY` (B4, ya candidato en DEC-065).** **Dúo #11: el sub-agente Opus (NO-SÓLIDA, 2 críticos) Y el cross-model GPT-5.5 (6/7) cazaron el MISMO confound INDEPENDIENTEMENTE** (el efecto medido lo produce LEVER2_IDENTITY, no el pre-filtro) — 6/7 + 5/6 confirmados, 0 FP, severity_max=crítico; **sesgo de over-claim de framing cortado por 7ª sesión seguida = control estructural**. Apliqué 2 fixes del dúo pre-revert (product_filter→None; fail-open familia-casi-vacía) pero el lever entero = NO-OP → **REVERTIDO (eval-driven, no shippear clutter; 353 tests verdes restaurados)**. **bvg K=5 del lever real (B4, hp018+hp009, base vs treat):** el freeze recupera el e-series correcto en AMBOS; **hp009 residual→K-INESTABLE** (mejora, gana votos PASS); **hp018 residual→residual** (recall arreglado, residual reatribuido INDETERMINADO→SUB-RETRIEVAL; **reach≠PASS** — residual=generación/diodo de polarización) = **GRIS** (movimiento + 0 regresión, 0 PASS-control limpio; DEC-065 lo predijo). No-regresión estructural: solo existe 1 alias (`ZXe→ZX2e/ZX5e`) → LEVER2 solo toca hp018/hp009. **Pieza 3 (bilingüe, read-only, $0, en paralelo):** es-en = lever PEQUEÑO — 9 pares ES/EN casi-idénticos (444 ch → ~205 EN duplicados, dedup $0, ojo cat007 cita ambos); EN-only REAL = solo 2-3 golds (~21 ch: cat010, cat011-parcial; ~$20-50 traducir el lote); hallazgo nuevo: **ho002/ho014 = ModuLaser NO ingestado (corpus-missing, NO bilingüe)** → fork s84 (dedup → traducir EN-only). **Audit 1a (`s75_identity_audit`, estado real):** identidad-sucia ≈ 200/1170 docs (78 pm-compuesto + 114 mis-atribución + 18 inconsistencia) — limpieza broad DIFERIDA a s84 (golds-touching no la necesitaba: hp018 ya recupera vía config existente + identidad). **Qué sigue:** decisión de Alberto sobre ship de B4 (`LEVER2_IDENTITY` = corrección de identidad REAL —arregla ZXe↔ZXAE/ZXEE, recupera el manual correcto, mejora hp009—, pero GRIS no-PASS → valor de corrección, no de métrica). s84: A1 (matcher es-en + histograma verdadero, foundational), limpieza broad identidad, B5 (hp006 AFP-400 series), categorías, versiones. Lección `feedback_my_bias #49`. Traza: DEC-066 + `evals/_s83_*` (brief/funnel/bvg/crossmodel logs) + `adversarial_review_log` dúo #11 + rama `eval/s83-retrieval-model-aware`. reach≠PASS; 353 tests; prod y held-out intactos.
- **s83 · F2 (29 jun 2026)** — **Activo de identidad multi-label LIMPIO de los 1014 docs construido (Capa 1 JSONL crudo + Capa 2 tablas normalizadas) vía extracción dúo + adjudicación de Alberto; regla de granularidad + base-unión dúo-validadas en 3 rondas; branch-local, NADA en DB (DEC-067).** Es el bloque F2 que DEC-066 señaló (`LEVER2_IDENTITY` = la RESOLUCIÓN de identidad era el cuello). **Pipeline A→D:** **A** extracción dúo (Opus 4.8 + GPT-5.5, structured-output, ~$145 Batches API) de los 1014 docs → **B** reconciliación + canonicalización por key-set (conflicts **120→29**, 76% ruido de superficie) → **C** Alberto adjudicó los **29** por la prueba covers-vs-mentions (cubre=contenido accionable; menciona=compatibilidad/accesorio→relations/mentions; findability lens) → **D** tablas `document_models`(2761 productos)/`document_identity`. **Regla de granularidad (Fix1):** 1 producto=1 registro, canonical=nombre comercial + aliases=SKU/descriptivo, compuestos partidos (evidence-gated), merge-key=model+canonical (aliases NUNCA puentean → no fusiona DS5≠DS10 ni cross-brand RP1r-Supra≠VSN-RP1r), higiene de aliases (compuesto-puente + códigos-internos fuera), software-foco=primary vs software_tool/mention=accesorio, package=bundle, compat canonicalizado. **Fold-in BASE-UNIÓN (el bug más caro):** los 29 deben partir de la UNIÓN canónica (igual que los 985) y la adjudicación MODIFICA encima — construir desde el diff del conflicto tiraba el set ACORDADO (**78 productos perdidos** en centrales; rol heredado del crudo dejaba 15 primaries en MNDT060, debía ser 1). **Dúo COMPLETO ×3 (sub-agente Opus + cross-model GPT-5.5), cada ronda cazó bugs REALES:** r10 (Fix1: bridging de aliases genéricos, ~152 primaries degradados); r11 (7 fidelidad: CAD-250 omitida, BE-XP/NR45-24/PRL-P2P perdidos, **Pearl-tentativo-encodado-firme=mi sesgo**, software-role); r12 (78-producto fold-in + rol-heredado, MNDT060 15→1). El cross-model refutó por regla-C 1-2 FP del propio dúo (124-143=part-number válido; CAD-BLED/B extraídos-por-ambos). **Adjudicación de Alberto al píxel** cazó identidad de dominio: FAD=**2 productos** (902 2A/905 5A), BE-XP=paquete (no modelo), códigos 124-xxx=PCB-misleading, **CFP-800≡Serie800** (gap de RESOLUCIÓN, MNDT020 SÍ ingestado — NO gap de corpus). **Higiene #1 (compat canonicalizado, $0)** + **re-pass ARCHIVADO innecesario** (la "falta de módulos" era MI fold-in, no gap de extracción; AMBOS modelos los extrajeron → fix $0; NO eval-gated: no hay golds + no se mide un defecto conocido — Alberto cortó mi over-instrumentación). **Lección `feedback_my_bias #50`:** mis-diagnóstico de síntoma→causa sin verificar el sustrato (atribuí a recall lo que era fold-in; verificar el crudo lo refutó) + cadena de errores de encoding cazados por dúo×3 + Alberto al píxel + over-instrumentación reincidente (#45, gateé en medición un fix de corrección conocido) cortada por ALBERTO no el dúo. El dúo+Alberto = anti-bias, control estructural mantenido. **Qué sigue:** cerrar s83 → **s84 = diseñar+medir el CONSUMO (F)** (índice inverso producto→docs + relaciones por-entidad; el VALOR se mide ahí, DEC-066 territorio donde el pre-filtro fue NO-OP) [+ **QA de muestra de los 985** en paralelo: no human-validados] → **aplicar a DB (E, stop-line de Alberto) SOLO si F mide ganancia**. reach≠PASS; tests `src/` sin tocar; prod/DB/held-out intactos. Traza: DEC-067 + `evals/s83_{conflicts_groundtruth,conflicts_resolved,document_models_final,document_identity_final}` + `scripts/s83_{build_document_models,finalize_tables}.py` + `adversarial_review_log` (dúo r10/r11/r12) + memoria `s83_identity_asset` + rama `eval/s83-retrieval-model-aware`.
- **s84 (30 jun 2026)** — **El cuello del eval NO es retrieval-vía-identidad — es SÍNTESIS. El lever de retrieval que SÍ funciona = arreglar un BUG (el filtro por la columna `category` MUERTA): retrieval-miss 27→15 (net −12). DEC-069/070/071.** Sesión larguísima (50+ turnos), enteramente diagnóstico + 1 fix branch-local; NADA mergeado; PASS no medido (diferido a síntesis). **(1) F1 consumo de identidad (índice inverso producto→docs) = NO-OP-con-regresión → revertido (DEC-069):** construí el índice (5274 claves, JOIN 1014/1014) + consumo aditivo en diversify; verify-first léxico dio divergencia 17/39 pero el path REAL solo cambia 3/39 y el funnel OFF-vs-identidad-ON deja RETRIEVAL plano (28→29) + hp012 regresión. **Identidad ⊥ el cuello del eval RE-CONFIRMADO full-stack** (s75/DEC-057). Dúo#12 cazó el confound. El activo de identidad sigue durable (findability/catálogo/30+, NO recall del eval). **(2) Reframe de Alberto → re-diagnóstico vía JUEZ SEMÁNTICO (DEC-070):** "¿retrieval-miss antes vs ahora?" + "el corpus-gap no me lo creo". Verificado: **corpus-gap=0** (los 11 valores existen en el corpus, `corpus_grep`, 2ª vez tras s82); el funnel LÉXICO inflaba RETRIEVAL **~45%** (22/49 facts son ARTEFACTO = recuperados pero el matcher es-en no los ve). **Funnel CORREGIDO: SINTESIS 63% (el cuello REAL) · RETRIEVAL 24% · RERANK 12% · CORPUS-GAP 0.** El retrieval-miss real ≈ 26/27 **within-doc** (manual recuperado, chunk-valor no surfaceado); es-en=0; identidad=0. Workflow 16-agentes (ultracode) diseccionó la causa: canal vectorial muerto + keyword-FTS within-doc roto (`extract_search_keywords` corta top-3 por orden antes de quitar identidad; STOP_WORDS sin tildes; FTS-AND). **(3) El BUG del filtro de categoría = el lever (DEC-071):** Alberto — "si es competencia global ¿cómo no ayuda la identidad?" + "elimina el bug, deja de escabullirte" + "mide en RETRIEVAL no PASS". Verificado: `category` muerta (DEC-040) → vector principal filtra → 0 filas el 85% queries → canal semántico MUERTO (hp002 pool=VECTOR 0). El fix (`VECTOR_NOCAT`, 4 sitios incl. el 5b que el sub-agente cazó y el cross-model no) = **retrieval-miss 27→15 (net −12, 8 mejoran, cat022 regresa por redistribución tipo-L-i)**; supera a (c) within-doc-vector (+6 vs +3 → (c) revertido). Es L-i en mecanismo pero medido en RETRIEVAL (DEC-040/068 lo settled en PASS = métrica distinta; el intento de re-medir L-i como "métrica nueva" SÍ fue **#51** [dúo#14, no grepié DEC-068 que firmé el mismo día]; lo que sobrevive es el bug-fix por principio). **Cambio de modelo operativo (DEC-071e):** sin técnicos (Railway=demo) → `main`=branch único (dev=demo), stop-line=tests-verdes (no PASS-gate), freeze per-eval, **PASS diferido a síntesis** (el blocker, gut de Alberto + dato). **Dúo ×4** (#12 F1, #13 within-doc, #14 recall-remeasure=#51, #15 implementación): el cross-model cortó mi over-claim de framing **8ª sesión seguida**; el sub-agente cazó 2 NO-OPs estructurales (within-doc-vector wiring, el 4º sitio del bug) que el cross-model no vio = control en CAPAS. **Lecciones `feedback_my_bias` #52 (me escabullí del bug de categoría apoyándome en un "settled"-de-PASS hasta que Alberto insistió 2× "deja de escabullirte"; al abordarlo re-litigué L-i sin grepear DEC-068-de-hoy = #51 reincidente, cazado por el sub-agente) · #53 (over-claim "0 push-out" desde UNA corrida; al re-verificar [regla-C propia] cat022 regresa determinista = redistribución de pool de L-i).** reach≠PASS; 355 tests; prod/held-out intactos; activo s83 durable. **Qué sigue: s85 = limpieza de raíz (quitar el filtro de categoría muerta + workarounds + flags inertes, no flag) → rerank → SÍNTESIS.** Traza: DEC-069/070/071 + `adversarial_review_log` dúo#12-15 + `evals/s84_*` + `scripts/s84_{build_identity_index,factprobe}.py` + `tests/test_vector_nocat.py` + workflow `s84-retrieval-deepdive` + rama `eval/s83-retrieval-model-aware`.
- **s84·M (30 jun 2026) — mantenimiento (NO consume s85)** — **Consolidación de memoria + control ESTRUCTURAL anti-recall (DEC-072, PR #92).** **(1) Memoria:** `project_techbot.md` podado **273KB→5KB** (pila de ~50 bloques "Estado" s27→s73 → un único bloque de estado DURABLE; la traza vive en HISTORY/DECISIONS/PLAN); `feedback_my_bias` reconciliado **#52/#53** (el índice los tenía inline, el topic file llegaba a #51); `MEMORY.md` índice compactado (2 líneas-monstruo → punteros de 1 línea). **(2) Anti-recall:** Alberto preguntó si añadir memoria para no reincidir en s83/s84 (dúo matando por métrica equivocada; escabullirse del filtro de `category`; NEGAR que existía; OLVIDAR contextual-retrieval). Diagnóstico: el canon estaba COMPLETO (category=DEC-040; contextual-retrieval=DEC-020/022; L-i=DEC-040/050/068) → fallo de **CONSULTA**, no de canon ausente → más prosa NO lo arregla. Panel adversarial 4-lentes + verificación BP contra los docs de Claude Code → **hook `SessionStart` que inyecta `docs/LEVER_DIGEST.md`** (8 levers SETTLED + columna MÉTRICA) cada sesión, NO un doc/tabla a-abrir-a-mano; fila de Protocolo 4 afilada; campo OBJETIVO+MÉTRICA en el brief adversarial (el "dúo mató por métrica equivocada" era framing del AUTOR, verificado contra el brief real). Alternativas (doc aparte, tabla inline, columna de hechos, fila nueva, lección #54) MATADAS por el panel. **Residual honesto:** no arregla la evasión motivada; **cero delta de eval** (recall-hardening, no toca SÍNTESIS); cross-model GPT-5.5 no corrido (sin key) → panel Opus + docs + Alberto; hook gitignored = setup local (instalado en `main` local). reach≠PASS; PR #92 mergeado. **NO toca el roadmap: s85 sigue = limpieza de raíz → rerank → SÍNTESIS.** Traza: DEC-072 + PR #92 + `docs/LEVER_DIGEST.md`.

## s85 (1 jul 2026) — DEC-073: limpieza A mergeada + instrumento family-aware de retrieval-miss (=14) + diagnóstico B1 (3 clusters)

Sesión larga colaborativa (Alberto guiando + dúos #16-#20). Tres bloques:

**A — limpieza de raíz (MERGEADA #94).** `VECTOR_NOCAT` de s84 pasa a permanente/sin-flag: el filtro por la columna `category` MUERTA fuera de raíz (4 sitios + broad-fallback + 3c-i + detección inerte en `retrieve_chunks` + param de `content_search`). Verificado judge-free (modelo operativo s84): 354 tests + equivalencia de pools NEW-vs-OLD(flag-ON) = 38/39 idénticos + cat005 idéntico en isolación (net −63 líneas). Dúo #16: el sub-agente Opus cazó un bloque `detected_category` muerto + comentario falso "feeds catalog"; el cross-model cortó over-claim de framing de la equivalencia.

**B0 — instrumento family-aware de retrieval-miss.** Reemplaza el predicado LÉXICO del funnel (DEC-070 lo midió inflando ~45%) por un juez semántico GPT-5.5 K=5 (rúbrica estricta versionada, umbral ≥4/5, pin del pool → re-derivación exacta). Diseño dúo-revisado ANTES de build (elección de Alberto): dúo #17 cazó 6 fallos (2 CRÍTICO, incl. pre-filtro top-8-coseno = FN estructural en within-doc). **Corrección clave de Alberto (ground-truth Morley): el tie por filename-token acredita mal** — by-target daba hp018=found vía MIE-MI-310 (familia ZXAE/ZXEE) para ZXe/MIE-MI-530 (ZX2e/ZX5e) = producto distinto que coincide por azar. → tie por FAMILIA de `product_model`. Dúo #18 (famtie) cazó 2 CRÍTICOS (manual_pin pm=None por el SELECT; fail-open) → arreglados sin re-juzgar (patch pm-by-id, disciplina de coste tras el incidente ~$50 de re-correr el instrumento caro ~5× en s84→s85). Pasada definitiva 39/39 limpia (paced, resumible sobrevivió ~5 teardowns). **retrieval-miss canónico = 14** (de 132 hechos CORE; SÍNTESIS 103 = el cuello sigue siendo síntesis). CORPUS-GAP=1 residual (hp011 'r.1' token-corto = FN del pre-filtro léxico; prior corpus-gap≈0 de Alberto se sostiene, cazado 4ª vez → memoria `feedback_corpus_gap`).

**B1 — diagnóstico por (ETAPA-DE-FALLO × MOTIVO).** Dúo #19 DEMOLIÓ la v1 (inferia el punto-de-fallo desde universos paralelos vector_search(200)/keyword, no el pipeline real → no distinguía model-filter de depth) — blind-spot compartido Opus. Reescrito instrumentando `retrieve_chunks` con un trace INERTE (param `_trace`, 354 tests) que emite la membresía del chunk-valor por-etapa real. Dúo #20 (3ª ronda) refinó: es-en vía la columna `language` de la DB (no heurística de keywords, que daba FP), lever discrimina within-doc, guards NO_VAL/error. **Mapa canónico para B2: RECALL-INTRADOC 8 (el manual está en pool, el chunk-valor no → within-doc/chunking, NO HyDE-global) · MODEL-FILTER 4 (hp018 = identidad, `_filter_to_query_models` con resolución 'ZXE' expulsa el manual ZX2E/ZX5e correcto, mantiene ZXAE/ZXEE) · RECALL-GLOBAL 2 (findability).**

**Cierre:** A en demo; B0/B1 branch-local `eval/s85-retrieval-miss` (13 commits). Coste ~$12-14. Próxima (s86 dedicada): B2 métodos por cluster (RECALL autónomo; MODEL-FILTER=identidad settled-lever → check-de-métrica + dúo+contrato con Alberto: el ⊥-recall se midió en funnel léxico, el instrumento corregido lo re-abre = re-medición no re-litigación). Lecciones a memoria: `feedback_corpus_gap`, `feedback_cost_discipline`.

---

## s86 (1 jul 2026) — B2 por los 3 clusters de retrieval-miss → identidad ~4-palanca (no el cuello); BP = catálogo canónico 2-etapas (NO LEVER2); plan (A)||síntesis

**RECALL-INTRADOC (8) descompuesto a nivel-chunk.** Caracterización (DEF.yaml + chunk_index): el chunk-valor existe en el manual pero 0 entran al pool. **5 = hard-tail de INGESTA** — no es ANN-miss ni chunking-roto ni baja-similitud (todo descartado midiendo): el coseno del value-chunk (0.43-0.51) está **por debajo del suelo del canal vector (~0.50)** = "aguja en chunk grande". Levers query-time DESCARTADOS con medición: **neighbor-window retrieval-stage = NO-GO** (zero-sum pool-50, A/B jitter-controlado +4/−29 broad, +4/−26 restringido); synthesis-stage sentence-window = BP pero MENOR (4/8, dist≤2 al top-5); **ef_search = marginal** (sim client-side: los hace candidatos pero compiten con cientos al mismo coseno — corregí mi propio "ef_search resuelve" tras un bug de patch); **más-contexto (blurb/voyage-context-4) = insuficiente** (ablación $0: blurb ayuda ±0.03-0.05, no despega del suelo). Fix BP = **capa-ingesta** (multi-granularidad/parent-doc + extracción-tablas + BM25 + ColBERT), foundational futuro. 3 "coupled a identidad" resultaron **within-doc** (el mapa limpia el flood pero es necesario-NO-suficiente — workflow map-coverage).

**MODEL-FILTER (4, hp018) = identidad = ~4 de palanca REAL del eval (no más).** `LEVER2_IDENTITY` (curado) resuelve 4/4 (alias ZXe→[ZX2e,ZX5e] + series/shared_docs voltean el pool de MIE-310 wrong-family a MIE-530) pero **regresa hp009/aisladores −1** (family-genérico) = net +3. **hp011 lo mis-diagnostiqué como identidad→clarify; el dúo cazó la racionalización:** el gold Alberto-verificado dice RP1r=RP1r-Supra (mismo equipo, conducta=answer), miss=RECALL-INTRADOC.

**La BP de identidad NO es LEVER2 (quick-fix per-familia) ni un filtro (adivina mal o contamina) — es entity-linking de 2 ETAPAS contra catálogo canónico.** El mapa data-driven (`s83 family_scope`) resuelve el paraguas ZXe y separa familias, PERO el matching de texto libre es frágil → net-negativo tal-cual (−2 hp011 al adivinar RP1r→a-secas). Dúo + literatura (Query Brand Entity Linking arXiv 2502.01555; selective clarification EVPI/CLAM 2212.07769/SAGE-Agent 2511.08798) confirman la BP: **catálogo gobernado + re-tag DOC canónico + resolución query-side híbrida (determinista + LLM-al-margen) + clarify-on-ambiguity** (BP, pero sin caso de ambigüedad real en el eval). Alberto cortó mi convergencia a quick-fixes 3-4 veces.

**Plan (decisión Alberto): (A) catálogo canónico || SÍNTESIS, en 2 sesiones.** (A) = 4-7 sesiones casi-autónomas, ~3.5-6.5h de Alberto (s83 ground-truth ya gastado); ⊥ el PASS (cimiento escala-30+/catálogo). SÍNTESIS = el cuello (103), arranca por diagnóstico autónomo; la palanca del eval. Paralelizable (código disjunto verificado; solo el DB re-tag serializa). Código s86 (neighbor-window + IDENTITY_MAP/identity_index.py) flag-gated OFF, 354 tests, NADA mergeado.

**Cierre:** DEC-074 + LEVER_DIGEST (fila identidad) + PLAN + memoria. Sesión larga con muchas mis-diagnosis mías cazadas por el dúo/medición/Alberto (`feedback_my_bias` convergencia) = el sistema de control funcionando. Próxima: síntesis (diagnóstico) + (A) Fase 0 (contrato) en paralelo.

---

## Sesión 87 (1 jul 2026) — diagnóstico autónomo de SÍNTESIS: el "cuello 103" era una COTA, no fallos (DEC-075)

Alberto eligió arrancar s87 por SÍNTESIS (diagnóstico autónomo). **Hallazgo central: el bucket "SÍNTESIS 103/132" (DEC-070/073) contaba hechos SINTETIZABLES (soportados por un chunk del top-5), NO fallos de síntesis** — la re-caracterización que el PLAN anticipaba ("el funnel léxico mintió ~45%").

**Método (dúo-hardened ANTES de build, Protocolo 3):** brief del instrumento → cross-model GPT-5.5 + sub-agente Opus CONVERGIERON en el CRÍTICO (capturar el contexto POST-`RELEVANCE_THRESHOLD`=0.4, no el top-5 crudo — un top-5 con sim<0.4 se cae del prompt) + el sub-agente cazó el artefacto-semilla equivocado (pins en `DEF.yaml`, no `FINAL`). 6/6 findings confirmados, 0 FP. Instrumento `synthesis_miss_judge.py`: juez GPT-5.5 K=5 **a nivel-PROPOSICIÓN** (valor EN su relación `texto`) sobre la respuesta del pipeline fiel a prod; `reaches_gen = support_ids(votos≥4) ∩ ctx_ids(post-0.4)`.

**Fase A ($0):** de los 103, **25 en golds PASS** + 78 en NO-PASS. **Full (103):** SYNTH-OK 82 · SYNTH-MISS 20 · NOT-IN-CTX 1. **Subset eyeball-verificado:** las respuestas actuales son MÁS completas que s67base — cat007 pasó de FALLO (se escudaba, omitía 'no enclavado'/'10⁵') a transmitir los 5 hechos. **Atribución limpia:** mismo generador/temp/tabla que s67base (verificado) → la mejora es de **VECTOR_NOCAT** (mejor retrieval → contexto más rico).

**Varianza (Sonnet temp=0 no-determinista, declarado en s67base):** 2 generaciones → **16 stable-MISS · 9 flip · 78 stable-OK**. Cuello ROBUSTO = 16.

**Certificación (workflow adjudica-ciego + verifica-adversarial, cross-model del juez GPT-5.5; + trampa):** de los 20 SYNTH-MISS → ~3-4 **judge-FN** (bot SÍ transmite), 9 **PARTIAL**, ~7 **OMITTED** (2=hp007 varianza). Controles **10/11 CONVEYED**; 1 over-credit = **hp018 '4 circuitos'** (respuesta del producto EQUIVOCADO ZXAE≠ZX5e → IDENTIDAD, DEC-074). Ambas correcciones REDUCEN el cuello → **~13-14 genuinos**. El dúo de agentes corrigió en AMBAS direcciones (cazó el over-credit hp018 Y confirmó OMITTED reales) — no solo confirmó mi narrativa (resultado sesgo-sensible → `feedback_my_bias` control operando).

**Mecanismo (heterogéneo, SIN lever barato):** completeness ~10 (=lever de generación **settled NO-GO en PASS**, DEC-051) · **contradicts ~4 (FIDELIDAD:** hp001 '1111' invertido, hp013 'EEPROM' invertido, cat020) · hedge-defensive ~2.

**Recomendación (Protocolo 2; des-diferir PASS = gate de Alberto):** (1) **des-diferir PASS y medir el baseline actual** (probablemente subió mucho post-VECTOR_NOCAT; tengo las respuestas frescas rep0/rep1, re-juzgar es barato, lo ofrezco sin correrlo); (2) **"atacar síntesis" está mis-dimensionado** (no hay cuello de 103; residual ~13-14 sin lever barato) → leverage real = (A) catálogo/escala + retrieval foundational (DEC-074) + eval orgánico; (3) 3-4 fidelity-contradicts per-caso.

**PASS des-diferido MEDIDO (Alberto autorizó en la misma sesión; `bvg_kmajority all BVG_RUN_ID=s87`, K=5 holístico):** **PASS-control = 9 · K-INESTABLE 6 · residual 24 — PLANO vs s67base (10+4), dentro del ruido ±2. Mi predicción "subió mucho" FALSADA por la medición** (`feedback_my_bias`: des-diferir fue lo correcto, el gate me corrigió; VECTOR_NOCAT mejoró el mecanismo pero no el PASS holístico — "80% hechos ≠ 80% PASS" confirmado). Alberto pidió clasificar los misses por motivo → **root-cause SEMÁNTICO** (`s87_rootcause.py`, integra famtie retrieval-miss=14 + s87 synthesis stable-MISS + DEF rerank, no el matcher léxico): de los 30 NO-PASS → **SÍNTESIS 11 · OTRO gold/juez 10 · RERANK 6 · RETRIEVAL 2 · IDENTIDAD 1.** El bucket **OTRO (10, SIN miss de pipeline)** = fidelity-errors reales del bot (cat022 longitud-onda-IR, hp001 '1111' access-level, cat009 6K8), falso-NO-PASS de juez (cat019, s76-flagged), conducta (hp004 debía clarify), supp-facts (cat008/hp008/hp020). **Meta-hallazgo: ~10/30 fallan ⊥ el pipeline → arreglar retrieval+síntesis NO los pasaría; plateau noise-limited CONFIRMADO al nivel de gold (DEC-051e medido); NO hay lever de pipeline que mueva PASS. Highest-leverage PASS = dual-judge + gold-review del bucket OTRO (s47/s76); el unlock de calidad real = eval orgánico (~sept).**

**Disciplina de coste:** validé el juez en subset antes del full; el primer workflow se rate-limiteó (agentes leyendo un JSON de 73k → 2.2M tokens) → rehecho leaner con archivos por-fila. El PASS eval = 195 gen + 195 juicios (autorizado, una corrida, no iterada). **NADA en prod, reach≠PASS, 354 tests verdes.** Instrumentos: `synthesis_miss_judge.py` + `_trampa`/`_calib_sample`/`_stability`/`s87_rootcause.py`, `evals/s87_synthesis_findings.md` + `_instrument_brief.md` + `s87_gate_report.yaml`. **Cierre:** DEC-075 (+f PASS) + LEVER_DIGEST (fila cuello) + PLAN + memoria. Branch `eval/s87-synthesis-diagnosis` → PR.

---

## Sesión 88 (1-2 jul 2026, nocturna autónoma) — per-caso NO-PASS (cero invenciones del generador) + DÚO v2 (DEC-076/077)

Alberto (yéndose a dormir): "¿qué puedes avanzar tú de forma autónoma para atacar de forma clara los NO-PASS?" + (al volver) "cambia el sub-agente a Fable 5 y asegura que el cross-model también lee el código".

**Per-caso al píxel de los 5 "fidelity-errors" de DEC-075f (gold → top5 congelado → literal → corpus): CERO invenciones/inversiones del generador.** hp001 ('2222' EXISTE en 3 docs, fronterizo top5 — corrige un FN del rootcause que lo tenía en "OTRO"), cat022 (banda-IR en el MISMO doc servido, p8), hp013 (frontera síntesis/retrieval: p16 explícita no servida, token EEPROM servido ignorado), cat009+cat020 (**GOLD/JUEZ-review**: el literal servido dice "condensador (suministrado) o resistencia 6K8" vs gold; el juez penaliza material correcto añadido). +2 fallos menores de calibración del generador. **Dossier de los 30 NO-PASS por clase accionable** (`evals/s88_nopass_dossier.md` + `s88_corpus_probes.yaml`): A gold/juez-review (la palanca CANDIDATA más barata, gate Alberto) · B within-doc (settled s86 en la MISMA métrica, capa-ingesta foundational) · C completeness (settled DEC-051) · D rerank (settled) · E identidad. **Cero builds** = disciplina del digest. **Dúo COMPLETO mordió mi sobre-benevolencia hacia el bot** (cross-model 8 findings/7 confirmados; sub-agente reclasificó cat020→gold/juez-puro y hp013→frontera, verificó TODOS los claims de corpus independientemente).

**DÚO v2 (DEC-077, pedido de Alberto):** sub-agente `opus`→`fable` (mismo árbol que el autor Fable 5 → cross-model sigue INNEGOCIABLE) + `adversarial_review.py` v2 con **loop agéntico read-only** (read_file/grep_repo/list_dir; sandbox + deny .env/tally; cap 30; --no-tools escape) = **paridad de información** entre ambos lados. Smoke E2E: cazó 2 claims falsas plantadas con ancla fichero:línea (14 tool-calls). **Cierra TECH_DEBT #36** preservando su invariante (artefacto por lente no-Claude + salida cruda). Docs sincronizados (CLAUDE.md P3, ADVERSARIAL_REVIEWER.md, briefing, memoria).

**Pendiente de Alberto (en lote, ~30-45 min):** el gold-review de la Clase A (cat009/cat020/cat019/cat012/hp004/cat024 con evidencia literal) — única palanca candidata de PASS a corto; PR #97 (s87) lista para merge.

**s88b (2ª tanda nocturna, misma noche):** Alberto preguntó qué más avanzar autónomo → (1) **(A) Fase 0 drafteada**: `docs/IDENTITY_CATALOG_CONTRACT.md` (contrato de gobernanza del catálogo canónico) — modelo de datos con construct **homónimo** (el catch crítico del dúo: la cascada exact-match-first reproducía el −2 medido de hp011, "RP1r"→extinción dropeando Supra), gobernanza blast-radius-first (paraguas/homónimos nacen candidate; QA por lote; convergente≠correcto demostrado con CAD150R en la semilla), guard anti-dos-copias (hash+frescura, la quemadura DEC-063), F3 con semántica multi-producto explícita (doc-level≠chunk-level, TECH_DEBT #49), D1-D7 para la ~1h de Alberto. Dúo COMPLETO (primera ronda REAL del cross-model-con-tools: 23 tool-calls, 6/6 confirmados 0 FP, anclas fichero:línea reales — valida DEC-077; + sub-agente Fable H1-H9). (2) **Paquete de adjudicación Clase A** (`evals/s88_goldreview_packet.md`): cat009/cat020/cat024/hp004/cat012 con literal+edición-propuesta+casilla → el gate de Alberto baja a ~15-20 min; cat019/K-INESTABLES apartados como evidencia del dual-judge. Gates intactos: NADA aplicado a golds/DB/main.

---

## Sesión 89 (2 jul 2026) — gold-review Clase A aplicado con adjudicación de Alberto (DEC-078)

Alberto mergeó #97/#98 y adjudicó el packet: A1✅ A2✅ A4(a); A3 con pregunta (¿el 7 mA es de otra variante?) y A5 con pregunta (¿recomiendas desglose?). **A3 verificado al píxel ANTES de editar**: el 7 mA es del MISMO MAD-472 (tablas de lazo de 3 manuales del sistema CAD-250) — discrepancia documental REAL; Alberto eligió (b) surfacear+precedencia. **Ediciones aplicadas vía gold_store** (0 errores) + **re-juicio dirigido K=5**: **hp004 → PASS 5/5 UNÁNIME (+1)**; **cat024 → PARCIAL 5/5 (sin FALLOs)**; cat009/cat020 sin movimiento (el juez completista encuentra la siguiente arista → **el plateau DEC-075f se confirma post-gold-edit; el lever restante del bucket = dual-judge**). **A5 cat012 resuelto-solo** (ya PASS 5/5 en s87; la línea del packet era dato stale de s67base — corrección honesta del autor). **Pregunta ES/EN respondida** (BP: no excluir EN; gobernar equivalencia en consumo) y cableada al contrato del catálogo (`docrel language-variant-of`, F1 casi gratis con `languages[]` de s83). PASS-map ~10/39 (no re-freeze). Pendiente de Alberto: contrato F0 D1-D7.

---

## Sesión 90 (2 jul 2026) — F0 aprobado → F1a slice vertical Morley CONSTRUIDO (DEC-079)

Alberto aprobó el contrato F0 (D1-D7 según recomendaciones, tras SUS 3 rondas de preguntas — dúo cross-árbol, frontera con #4, atribución por-chunk — y la última pasada BP-MDM con validación externa: merge/split-redirects, F1a-slice, namespace, catalog-gate). **Construido:** `catalog_store.py` (la puerta, patrón gold_store: validate con reglas duras + `resolve()` con contrato `expand` y check-homónimo PRIMERO) + `s90_f1a_morley.py` (slice: gt nivel-1 + semilla s83 nivel-2/3 + doc_map por document_id real, 114/114) + Catalog gate en CI + 27 tests (378 total). **El slice cazó 3 clases de bug ANTES del bulk** (su propósito): colisión alias↔canonical (ZXr-A por smoke → check en la puerta → cazó DX2/EXP), divergent-unknown expandiendo contra el contrato (cross-model), CI sin gate. Smoke final: `RP1r`→prefer Supra (hp011 ✓), `ZXe`→3 variantes divergent (hp018 ✓), `ZXSe`→fail-open (sin adjudicar), `ZX`→bloqueado candidate. Dúo: cross-model 6/6 aplicados; sub-agente sobre el estado final (findings → follow-up). QA-cola para Alberto (~15 min): 4 conflictos + 2 candidates de alto blast-radius + adjudicar divergent de ZXSe. NADA en prod/DB (repo-only). Siguiente: QA del slice (Alberto) → F1 bulk (31 marcas) → F2 resolución query-side tras flag.

**s90b — QA del slice ADJUDICADO por Alberto y APLICADO → F1a CERRADO.** Alberto revisó el pre-QA (packet P1-P8 con evidencia corpus+web) y aportó dominio que la evidencia mecánica no veía: **P4 corrección** (MA-100 no existe — los MIE-MA-100_* son manuales de la central **HRZ2-8**, verificado en corpus → producto nuevo + doc_map); **P3 tri-desambiguación** de EXP (tarjeta Mod.EXP / impresora Mod.EXP-060R / wireless MIW-EXP); **P7 con pantallazos** (BRH/BRS-PC-I05 = refs NUEVAS de MI-BRH/BRS-PC-I → aliases; 795-072/068-100 = placas de lazo ZXSe por protocolo, Tabla 2 MIE-MI-600 p15; BRH/BGL ambiguos cross-brand con Notifier → fail-open; MK-* = software de config; FAAST-LT = familia multi-marca → F1 bulk con reference_faast); **P6 ZX → CLARIFY adjudicado** ("más seguro que adivinar"). P1 ZXSe divergent=TRUE (desbloquea MIE-MI-600), P2 DX2→alias+variant-of de los SKU, P5 los 5 paraguas, P8 doc_map MU-315/MU-535/DXc-variaciones (MIEMU520P fuera: PT). Todo con provenance `gt-s90-alberto-qa`; smoke del lote completo verde; 383 tests. **F1a CERRADO → F1 bulk (31 marcas) al merge de #101.**

---

## Sesión 91 (2 jul 2026) — F1 BULK: las 31 marcas en el catálogo canónico (DEC-080)

Tras el merge de #101 (F1a+QA de Alberto), la carga completa: 1014 docs / 2761 menciones → **~1.6k productos, 39 homónimos, 861 doc_map, 9 docrel ES/EN** (los ~9 de DEC-066, vía doc-number+idioma). BRAND_MAP 96→31 con resolución contextual gateada; typo-merge #49 (AFP-400≡AFP400, 30 fusiones); x-brand jamás-merge-auto. **Dúo completo 2 rondas** — el sub-agente cazó la REINCIDENCIA de la clase H5 (gt FAAST sin los -HS creaba duplicados consumibles → re-transcrito FIEL leyendo la memoria) + doc_map con namespace equivocado (68); el cross-model cazó colisiones-consumibles y el QA infradeclarado. Todo aplicado y verificado. Golds-clave resuelven (Pearl/AM-8200/ID3000/CAD-150/FAAST); lo dudoso fail-open. PR #102. **Gates: paquete-decisión ~25 homónimos (Alberto) — no bloquea F2; siguiente = F2 query-side tras flag + F2.5 shadow.**

- **s91 (2 jul 2026)** — **La sesión del catálogo VIVO: adjudicación masiva de Alberto (3 packets) + F2 diseñado-y-construido con el dúo mordiendo en cada capa.** (1) **Homónimos (DEC-081):** pre-QA 3-capas (corpus+web+píxel — 30 portadas + 2 PDFs de notifier.es descargados en sesión: © System Sensor 2002 en AMBOS manuales 6200R/LPB-620 zanjó el caso REFL) → Alberto adjudicó G1✅ G2✅ G3✏️×3 (VSN-4REL oem=Esser verificado en catálogo esser.es; CMX oem=Xtralis y PAK oem=Carrier verificados en fichas ADI) G4=APIC-clarify → APLICADO por la puerta (30 winners/33 redirects/quedan 9); el sub-agente cazó 3 H5 en MIS añadidos pre-commit (oem no adjudicados). **Gap D1 cazado: data/catalog NO estaba versionado** (.gitignore data/* + test skip silencioso) → los 7 JSONL a git (~1MB), CI ejecuta el catálogo por primera vez. PR #103 (re-montada tras 2ª reincidencia push-a-rama-mergeada → regla viva afilada: el check DEBE gatear). (2) **Plan F2 (DEC-082):** v1 TUMBADA por el dúo — "expansión aditiva del pool" re-litigaba DEC-069 sin citarlo (¡yo incumplí Protocolo 4!); v2.2 tras 2 rondas (15+13 hallazgos, 0 FP): seams medidos (models-list + unión-protectora doc_map), famtie+pin-regen (la famtie NO re-recupera — hallazgo que salvó una sesión de medición NO-OP), detector sin la bomba '≤3 chars mata zxe', vendimias pre/post-NOCAT al LEVER_DIGEST (pregunta de Alberto sobre contaminación de settled → fila DEC-069 + columna vendimia). **Contrato §5.1 enmendado (✅ Alberto): expand-only, clarify por-pregunta diferido** (PR #105). (3) **F2-S1 CONSTRUIDO (PR #106):** resolver query-side flag 3-estados, dúo r3 sobre el build = 14 hallazgos aplicados pre-PR (seam-2 reemplazaba→unión-protectora; 'dimensiones' disparaba paraguas Dimension; tests escribían en la shadow real), suite 411. (4) **Packet C2 COMPLETO (DEC-083):** 19 marcas → 43 productos re-domiciliados en 3 tandas de Alberto (~10 min), con 3 correcciones suyas convertidas en reglas: hosting≠OEM (NSRE24 → OEM 'ADA Componentes Electrónicos' al píxel), string-grupo→contextual, **familia≠marca (FAAST → paraguas familia + LT-200 adjudicado divergent=true, ambos EXPANDEN; estaba unknown/fail-open desde s80)**. Gates abiertos: merge #105+#106 → S2 (shadow+famtie).

## s93b (2-3 jul 2026) — Bake-off fine-grained: el mecanismo que financia la re-ingesta es EXTRACCIÓN→ENUNCIADOS
Alberto empujó el plan gate-0 (PR #110, FTS-only) a bake-off multi-mecanismo ("no sé si deberías
tratar otros métodos FINE-GRAINED") — pushback aceptado: enmienda v3.2 con tracks B (multi-gran) y
C (extracción-tablas) + mini-brazo HyDE, dúo completo PRE-ejecución (cross-model 7 hallazgos, 2
CRÍTICOS confirmados contra código; sub-agente F1-F7 con el paso-0 `_trace` como adición estrella).
Ejecución 8h autónomas sobre el testbed de 11 miss-facts (guard excluyó hp006 'Tierra'):
**paso-0**: 30/31 soportes nunca entran a canal; hp012 '99+99' muere en diversify → re-atribuido.
**A-FTS**: NO-GO 1/11 + desplazamiento 0-15/20 en controles. **B**: 1/10 vs frontera real (aislar
ALEJA, 5/8 sub<padre). **C**: 2/4 ✅ (hp011, hp012-'2 lazos/396' con margen) — único mecanismo con
hechos únicos. **HyDE**: 0-1/10 (comprime sin cruzar). Lectura: el cuello es gap de VOCABULARIO
query↔celda, no chunk-size. Regla-C contra mi propio instrumento cazó 3: evento-v1 con frontera
falsa (8/10 WIN falsos→1/10), brazo HyDE NO-OP silencioso (hyde.py:84 sin flag), 2/31 sup
duplicate_of. Nada cablado. Artefacto: `evals/s93_bakeoff_resultados.md`. DEC-084/085; digest con
4 filas tocadas. Decisión pendiente de Alberto: piloto extracción (~$5-15) → re-ingesta (~$150-300).

## s94 (3 jul 2026) — Piloto extracción→enunciados: GO medido (famtie 12→6 con R2)
GO de Alberto tras validar el spec v2 con el dúo (fork del SWAP resuelto por regla-C contra código:
la famtie acredita presencia; el multi-vector swap es medición válida). F0 pre-registro (4 tabla /
6 prosa; padres acreditables; predicciones por brazo×clase) → F1 generación 368 candidatos + QA
(v1→v2 por regla-C: whitelist de metadata inyectada; tras el fix el gate cazó 2 alucinaciones
reales sin FP; delta-check confirmó blurb-padre) → F2 probe (R2 3/10 proxy) → F3 por-brazo con
SWAP pre-merge + rollback verificado ×3: **R2 12→6 (5/10, 0 nuevas-miss, predicciones 3/3 ✓) ·
R1 12→10 (0/4 tabla, FALSADA → descartado) · R3 12→8 (4 flips/11 surrogates, falsada al alza)**.
Triage: hp011/'99+99' mueren en diversify (lever pipeline); cat013/cat016 sin mecanismo (vocab
operativo). Pase corpus ≈$160-270+QA = decisión Alberto. DEC-086; digest actualizado; nada en demo.

## s94b/T0 (3 jul 2026) — Infra permanente del pase de enunciados (GO de Alberto al enfoque por tramos)
Alberto preguntó si el pase corpus debía ser de golpe o por partes → tramos validados por el dúo,
que tumbó la v1 por heredar la infra del PILOTO (6 CRÍTICOS: sidecar fail-open, sin contrato de
schema, ventana demo-sirve-derivado F1). T0 ejecutado con GO: migración 007 aplicada (regla-C
pre-apply salvó el ef_search de s59b, que las defs del repo habían perdido; un DROP fallido no tiró
la demo — transaccional), invariante de no-servicio en 9 GETs + RPC, swap ENUNCIADOS_MULTIVECTOR
from-row, QA generalizado con 3 vueltas de calibración (el sub-agente REPRODUJO la ceguera a
decimales: '13,9' alucinado pasaba — fix _normv verificado), panel de desplazamiento (fix EMBARGO:
el filtro 'heldout' vs 'held-out' metía los 12 embargados al pin; query_gaps era 404 → query_logs),
pase idempotente por-doc con smoke real (MIDT180: 427 QA-OK, cobertura 65%). Dúo del build: 6+9
hallazgos, 0 FP, todos aplicados + 4 tests (14 total del feature). Umbral QA y coste re-registrados
por el smoke (T1 ~$40-100 medirá el real). 435 tests. Demo intacta. DEC-087. Gate: GO de gasto T1.

## s94c/T1 (3 jul 2026) — Pase corpus por tramos: NO-GO del enfoque; T1 cazó un fallo de arquitectura antes del gasto de corpus
GO de Alberto al gasto de T1 (~$50-75). Piloto de 14 docs generado con Sonnet 4.6 (21.995
enunciados) para el gate de reproducción. **G1 FALLA (2/6 flips):** insertar los surrogates
en el MISMO índice HNSW que los chunks reales lo diluyó (índice ×2, 47% surrogates) →
recall de los originales cae (control 12→19); el multivector dio 13, neto PEOR que el
baseline limpio 12. El mecanismo del piloto s94 (12→6) no escaló porque aquel usó 251
surrogates transitorios y dirigidos; a docs-enteros se ahoga (dilución + enterramiento del
enunciado relevante entre sus hermanos). Aislamiento verificado: 12→19 (inserción) →17
(delete, fantasmas HNSW) →12 (VACUUM, lista idéntica a s92). Side-by-side confirmó Sonnet 5
como vintage (mejor calidad, ≤coste). Restauré la demo (dump + delete + revert RPC + VACUUM),
cacé y arreglé un bug latente (FK duplicate_of sin índice → migración 009), 435 tests verdes.
**T1 (~$50-75) cazó un fallo arquitectónico ANTES del gasto de corpus ($150+) = el diseño de
tramos funcionando.** Redesign pendiente (dúo+Alberto): tabla/índice separado para surrogates,
índices parciales, o generación dirigida. DEC-088. Nada de T2-T3 hasta resolver.

## s95 (4 jul 2026) — Redesign de enunciados medido con 2 pilotos: arquitectura tabla-separada VALIDADA (12→7); deep-lookup NO-GO; agentic RAG descartado con evidencia
Pregunta de Alberto ("¿cómo se hace en RAGs similares? ¿agentic RAG?") → research con fuentes
verificadas (workflow 3 agentes): la BP unánime es surrogates en índice PROPIO con padre-por-ID
(LangChain/LlamaIndex/Dense X/pgvector partial-index) — el T1 re-derivó empíricamente por qué; y
agentic RAG como arquitectura NO paga para nuestro perfil de fallo (ACL 2026). Plan de 2 pilotos
pre-registrado → dúo (15/15 confirmados regla-C, 0 FP, 4 críticos: parser booleano habría hecho
de IDENTITY_FETCH=llm un NO-OP silencioso; punto de fusión sin pinear; pre-filtro léxico
re-introducía el techo DEC-085) → ejecución. **Piloto A: tabla `chunks_v2_enunciados` separada
(011/012), dump T1 re-embebido ($3), 3 brazos: 12→8 → 12→8 → 12→7 con colapso Dense-X; control
12 INTACTO en todos y 0 regresiones = dilución eliminada por construcción, candidato a ship
(gate bvg pendiente).** Trace de los no-reproducidos: el residual NO es de índice ('35' = gap de
generación; PWR-R/'1 A' = distancia pregunta-tarea↔enunciado-fila que ni s94 cruzaba por cos —
puerta de su flip s94 sin identificar, declarado). **Piloto D: NO-GO estructural** (12→11, 0/6;
el seam solo gatilla con doc AUSENTE del pool y la clase dominante es doc-presente-aguja-ausente;
38% gatillado > 25%). Gate-0 de D cazó 3 gaps de doc_map → packet a Alberto (catálogo NO tocado).
DEC-089. 441 tests. Coste total s95 ≈ $3.5.

## s96 (4-5 jul 2026) — Gate bvg de A3 PASADO 4/4; el ship del flag queda en manos de Alberto
Pregunta de Alberto ("¿qué opina el dúo de cómo proceder?") → plan s96 pre-registrado → dúo
(11/11 confirmados regla-C, 0 FP, 3 críticos): el sub-agente cazó que un hiccup de Supabase en
el RPC de enunciados habría matado el canal vectorial ENTERO en silencio (fail-open propio
aplicado + test) y que 'true'/'1' eran OFF silencioso en el flag (parser estricto); ambos lados
cazaron que yo citaba el harness equivocado para el gate (single-pass vs bvg_kmajority
K-mayoría) y el manifest sin stamp de la variable de tratamiento; mi "riesgo R3" resultó falso
(escrito sin leer el código — retirado). Gate ejecutado (~$12-18, brazos s96ctl/s96on mismo
día): **rescate→top-5 3/3 golds-flip · PASS-control 11→13 (+2 en banda, residual 23→19) ·
invención sin subida · latencia p50 +725ms → PASADO 4/4 (DEC-090).** Regla-C ×2 contra mi
propia alarma de invención: el "2 vs 13" era FALSO (9/13 golds con top-5 idéntico entre brazos
+ el mismo control da 2→20 entre runs) → **norma nueva: el eje factual del atomic a K=1 es
inusable para comparar brazos; matriz pareada multi-run sobre los golds cuyo input cambió**.
Bonus del gate: hp006 JP2→JP6 = mispairing de SÍNTESIS sobre el chunk correcto que el rescate
por fin trae (expuesto, no creado; en control el bot fabricaba) → evidencia nueva al dossier
síntesis. Pendiente SOLO de Alberto: flag on en Railway + smoke post-flip. Held-out intacto.

## s96b (5 jul 2026) — A3 SHIPPED: merge + flag on + verificado en producción
Alberto mergeó la PR #111 y puso `ENUNCIADOS_MULTIVECTOR=on` en Railway. Post-flip completo:
smoke e2e local con flag efectivo (rescate al pool + rerank + generación OK, fail-open detrás)
→ 2 queries reales de Alberto por Telegram → verificación en producción: los timestamps del RPC
`match_chunks_v2_enunciados` en los logs de Supabase casan exactamente con ambas queries
(21:03-21:05 UTC); la respuesta de AFP-400 cita el hecho antes-inencontrable ('LED de Fallo de
Tierra en la placa MPS-400'); la de CAD-150 es idéntica a su versión pre-deploy del 2-jul (0
regresión); latencia 34-47s dentro de la banda histórica. **El canal multi-vector de enunciados
queda VIVO en la demo.** Rollback = quitar la env var.

---
## s98 — 5 jul 2026 — Matriz de rerank autónoma: el lever que paga es SERVIR-MÁS, no tocar el reranker; reencuadrado a hiperparámetro-de-ancho; smoke caza truncado → NO ship limpio (DEC-092)
Alberto pidió trabajo autónomo nocturno: matriz de experimentos del rerank para dejar el
rerank-miss en 1-2 con una mejora ESTRUCTURAL (no overfit), dúo antes de implementar, medir en DEV
(held-out embargado). Construí un harness que congela el pool-50 real por gold dev (con similarity/
target_models/todos los campos — fidelidad corregida por el dúo v1) y re-rankea el pool congelado
por método → top-N → filtro sim≥0.4 = "servido"; métrica RERANK-MISS = aguja-en-pool que NO
sobrevive al servido (baseline top-5 = 13).

**Matriz de 8 métodos.** Las SEIS intervenciones SOBRE el reranker fallan o empeoran: prompt
"¿contiene la respuesta?" (wash 14), prompt forzado (17), modelo Opus 4.8 (16 — capacidad NO es el
límite), ventana 800→2500 (21), Voyage cross-encoder (21, coherente DEC-048), RRF fusión retrieval+
rerank (45 — retrieval es baja-precisión, fusionar mete ruido, +3/−35). La que paga: **servir top-8
= 6 (+7/−0), servir top-10 = 2 (+11/−0), alcanza el objetivo**. Mecanismo: el reranker NO se
equivoca de relevancia, coloca los chunks-respuesta en rank 6-15; la ventana de servicio de 5
(DEC-018 "generate narrow") era el cuello.

**El dúo (cross-model GPT-5.5 + sub-agente Sonnet — Fable sin créditos, override; convergentes, 0
FP) reencuadró el hallazgo de "breakthrough estructural" a "hiperparámetro de ANCHO dev-elegido".**
Críticos confirmados (regla-C): (a) el bvg histórico rerankea SIN target_models → no es el path
prod; (b) T10 cambia `top_k` en el prompt → mide "pedir-10+servir-10", el mecanismo "rank 6-10" sin
probar; (c) `LLM_MAX_TOKENS=2048` fijo → riesgo de truncado con 10 chunks; (d) falta eje coste/
latencia. Experimento **CUT15** (petición fija=15, cortes 5/8/10/15 → 18/10/3/1) ZANJA: 17 agujas
en rank 5-14 (diagnóstico confirmado) PERO cut@5-de-15=18≠M0=13 (el tamaño de petición cambia el
orden) → palanca de ancho, no arreglo del reranker.

**Smoke e2e barato (path prod real, top_k 5 vs 10) — el gate barato ANTES del bvg caro (disciplina
de coste) — cazó el riesgo load-bearing:** cat019 (CONTROL) truncó a k=10 en 1 de 2 runs (roza el
cap 2048, intermitente; k=8=1920 no trunca). Rescate a nivel-respuesta PARCIAL 3/9 (hp011/hp015/
hp017 ganan el fact; 4 no-show = synthesis-drop). **Veredicto: rerank-miss 1-2 ES alcanzable a nivel
retrieval (T10=2) PERO top_k=10 NO es ship limpio** (truncado intermitente + rescate parcial + coste
2×). NO se cablea. Gate bvg prod-fiel (`BVG_TARGET_MODELS`) + flag `RERANK_TOP_K` (getenv) + pre-
registro LISTOS para el GO de Alberto; recomendación = no-ship-10-as-is (subir LLM_MAX_TOKENS o
top_k=8). Fixes prod defensibles: retry-sin-temperature (modelos 2026), parser regex robusto,
`relevance_instruction`. Tests 450 verdes. Residual del reranker (hp005/hp006 >rank-15) =
document-side. **No corrí el bvg caro autónomo (pregunta cero: no cambia una decisión que yo pueda
tomar — ship = Alberto + cross-model FULL; el smoke ya recomienda no-ship-as-is).**

## s99b (6 jul 2026) — rumbo demo-vs-nota, identidad re-scopeada, DEC-075 caduco, y estándar de medición (DEC-093)
Sesión larga, mucha exploración, 3 muros — y el DÚO como caballo de batalla anti-bias (cortó ~5 sobre-afirmaciones
de framing MÍAS). Arrancó por FOCO 1 (cablear el detector `extract_product_models` al catálogo gobernado). El dúo
×2 lo re-scopeó: el detector vive del catálogo VIEJO (`model_catalog.json`); el resolver gobernado
(`catalog_resolver`, `IDENTITY_RESOLVE=on`) es OTRO extractor; CS4 es `candidate:true` → ni uno ni otro la reconoce
→ cablear NO arregla CS4 (eso es B/DEC-074, adjudicar datos). Alberto decidió **blindar-demo → luego nota**, gas
FUERA (PCI-fuego puro, TECH_DEBT #75; Pepperl-Fuchs SÍ es PCI vía Detnov — corregido over-reach mío). Packet de
candidatos (630 sin confirmar, T1≈363 incendios BRUTO que necesita QA, no toggle). El "fix barato de demo" falló
3×: heurístico carry-forward v1 (marca+longitud) y v2 (código-sólido) TUMBADOS por el dúo (FP sobre vocab técnico
RS485/IP54); el reescritor conversacional (condense-question, BP para multi-turn) resultó NO arreglar el CS4 —
**medido: query CS4 limpia → el bot RESPONDE la CS4 gas** (2388 chars, retrieval semántico pese a `extract=[]`) →
viola PCI-puro; el fix del CS4 visible = declinar-gas (pequeño) + B. Reescritor **APARCADO** con checklist de retake
(`evals/s99_rewriter_design.md`). **Pivote a la NOTA (opción c).** Al recargar el estado, hallazgo clave: **DEC-075
(síntesis "settled, sin lever barato; PASS plano ~9/39") está CADUCO** — medido s87 sobre corpus 9-jun, ANTES de
ancho-10/A3/identidad, sin re-medir a nivel-hecho (Alberto lo cazó; yo corregía con datos caducos). Idea de Alberto:
re-medir a nivel-hecho (132 hechos) con datos actuales. Al intentarlo: **la infra de medición BIT-ROTEÓ** — el DEF
s85 se desalineó de los golds (editados s97c) → `synthesis_miss_judge.py:114` crashea; reusar el DEF viejo no es
viable; assessment actual ≈$15. Alberto pidió **estandarizar el proceso** (repetido 4× ad-hoc): spec v2 dúo-hardened
(`evals/s99_factlevel_assessment_spec.md`) que unifica los 4 instrumentos (retrieval_miss+synthesis_miss+
audit_retrieval_funnel+s87_rootcause), taxonomía consistente 5-clases + sub-motivo, anti-bit-rot (regenerar-siempre),
freeze-contract completo. **NADA en prod, NADA cablado** (todo diseño+medición+docs). **1ª tarea próxima sesión =
construir el estándar → correrlo (~$15-20) → decidir foco con datos frescos.** DEC-093.

## s100 (6-7 jul 2026) — assessment a nivel-hecho ESTANDARIZADO construido+corrido → síntesis RE-CONFIRMADA como cuello (DEC-094)
Construido `scripts/factlevel_assessment.py` (unifica los 7 instrumentos ad-hoc) + doc canónico `docs/FACTLEVEL_ASSESSMENT.md`
con **scoreboard append-only** (petición de Alberto = source-of-truth de "qué tal funciona el bot" a nivel-hecho, para
trazar cómo cada mejora mueve la aguja). Proceso dúo-intensivo: spec v2→**v3** (dúo ×3, 8 fixes verificados regla-C, 2
BLOQUEA-medición: bug-s45 top-5-vs-10 + flag muerto DIVERSIFY_TIEBREAK); build v1→v2→v3 (dúo código ×2 cazó 8 issues, incl.
mi over-claim "pipeline shippeado" cuando era ruta harness); **3 smokes cazaron 2 bugs de diseño reales** (measurable() gate
filtraba 38% = la cola de síntesis → no reproducía DEC-075; corpus-gap mislabel de cross-familia). Flag-set de la demo
confirmado con Alberto vía Railway. Fork resuelto (ruta HARNESS, no Telegram — paridad con bvg/DEC-075).
**RESULTADO (39 golds, 133 facts, ruta harness):** OK 89 (67%) · **synth-miss 16 estructural** (+6 flip) · retrieval within-doc
~17 (gap vocabulario) · rerank 4 · **corpus-gap ~0** (5 raw, TODOS FN verificados a mano — `feedback_corpus_gap` 4ª vez) ·
**identidad 0**. **Titular: síntesis SIGUE siendo el cuello dominante post-ancho/A3/identidad → DEC-075 re-confirmado en
veredicto (su medición s87 sí era caduca); identidad+corpus descartados con datos frescos.** Refinado por sub-motivo
(~10 omitted/hedged=lever prompt + ~5 partial=lever retrieval + 2 contradicted) PERO el sub-motivo está contaminado por
scope/gold (hp007: bot respondió lo preguntado) → qué-lever-dentro-de-síntesis = gold-review por-hecho, NO zanjado (spot-check
regla-C me frenó de sobre-afirmar el lever de prompt). Punch-list dúo-final de 7 aplicado al código; #4/#7 documentados como
limitación. **Rama `eval/s100-factlevel-assessment` (fresca desde main+#113); baseline en el scoreboard.** DEC-094.

## s100b-s101 (7-8 jul 2026, autónomo nocturno) — instrumento dual×2, 4 levers upstream medidos, scoreboard v2 (DEC-095)
Mandato Alberto (Fable 5 ultracode): OK>95% bajando buckets, upstream-first, GO=reducción-de-bucket,
flag de overfit. **Instrumento**: dual-judge en conveyed Y soporte (2 clases de FN del juez GPT-single
cazadas con evidencia adversarial el mismo día: 5-7 conveyed-FN verificados leyendo respuestas + 6/7
"retrieval-miss" adjudicados supports por workflow 7-jueces/21-refuters 0-refutaciones) + fail-fast del
primario (incidente real: cuota OpenAI murió mid-run 2×; run inválido en cuarentena) + freeze-hash con
pipeline-src + seams pineados. **Gold-review pixel-vs-fuente** (dúo, NUNCA vs bot): 5 demotes de scope +
hp011 r.1→r.I (Alberto se retractó de s30 — mnemónicos rS/rI; el corpus r.i era correcto; lección:
el cross-model dictaminó GOLD-ERROR y fue anulado citando al humano — tenía razón). **Levers**: hyq/HyPE
piloto GO (2/7 flips incl. el gate falsable cat016; cuota-propia + barra 0.45 = los 2 hiperparámetros
que separan señal de desplazamiento; residual-ancilar DECLARADO anti-overfit) · tiebreak CERRADO
definitivo (re-medido con ancho-10: centinela hp001 regresa + 9 EXCESS/null=0) · cat013=identidad
(DEC-074) · no-anclables=clase-juez. Método nuevo de la noche: **control negativo null-corrected**
(el jitter run-a-run NO es cero — sin null, el 1er control dio 9 falsos EXCESS). **Scoreboard v2**
(juez v2, sanos): OK 91 (71%) · synth 22 (14/8; cluster cat021×4 variantes) · retrieval 8 · rerank 5 ·
corpus 2. Fase 2 abierta: A/B fact-level del fidelity-block (smoke 0/0; full en vuelo al cierre).
NADA shippeado (tiering nocturno + ship-gates = Alberto). Ficheros para Alberto:
`evals/s101_plan_autonomo.md` + `evals/s101_decisiones_alberto.md` (D2 ship-hyq · D3 no-anclables ·
D4 scope-borderline · D5 residual-ancilar, con recomendaciones). DEC-095.

## s102 (9 jul 2026) — hyq de piloto a PRODUCCIÓN en un día, con el gate haciendo su trabajo

Sesión de ship completo del canal question-side (D2/D8): migración 013 aplicada por Alberto →
load 70.134 preguntas (0 poison) → **el gate de flips v1 FALLÓ 0/2** e hizo exactamente su
trabajo: diagnóstico medido (corpus-wide el espacio-pregunta es fuerte-en-tema/débil-en-producto;
la cuota global compraba slots que el model-filter tira; el diversify re-litigaba la cuota con
sims incomensurables) → mecánica v2 (family-parity nivel-fila patrón-012 + carve-out) → gate v4
2/2 CON atribución causal. Dúo Protocolo 3 ×2 rondas (4 tallies, 0 rubber-stamp: typo-flag que
mataba el canal vectorial en silencio → flag a import-time; false-PASS sin atribución; ventana
id-duplicado; keep-max-antes-del-filtro; ef_search<match_count; paginación Supabase 1000). bvg
outcome: 0 regresiones reales (hp020 = 4ª instancia del artefacto DEC-092b, verificado por agente
independiente) + 4 gains PASS. Negcontrol pool-level ROJO registrado sin edulcorar y arbitrado.
Cazado en el smoke de prod: la var apuntaba a main SIN el código → PR #115 → **flip cat016
verificado en query_logs** (10:54Z admit → 11:15Z autobúsqueda completa). Full v2.2 (demo real):
OK 91 (72%) · synth 18→8 (cluster cat021×4 resuelto por composición — confirma DEC-097) ·
corpus-gap real 0. La factura del canal quedó visible y trazada (cat022×3+hp018×3 desplazados por
el squeeze del diversify sobre keyword) → siguiente lever: aterrizar el desplazamiento en la cola
VECTOR (a medir). Extra: regla operativa de Alberto = orchestrator (Fable lidera; sub-agentes
mecánicos en Opus/Sonnet; el pin fable del dúo intocable). DEC-096..099 · TECH_DEBT #52.

## s103 (9 jul 2026) — el gate tumba mi lever y eso es el sistema funcionando (DEC-100)

Sesión limpia arrancada del plan s102→s103. El lever §1 (displacement-landing: que la cuota hyq
desplace cola VECTOR, no keyword) fue de diseño a veredicto en una sesión: dúo Protocolo 3 en 2
rondas × 2 lados (el sub-agente r1 cazó un CRÍTICO — los early-returns del diversify + merge
stamps sin cap habrían hecho que mi eviction v1 arrasara el canal vectorial entero; el cross-model
cazó las escalas incomensurables Y una cita errónea que AMBOS sub-agentes Claude repitieron —
validación en vivo del mismo-árbol≠independencia de Alberto s102), cableado v2.1 con 5 contratos
de test nuevos (466 verdes), y gate judge-free A/B same-day (worktree@HEAD vs fix, config-stamped,
null OFF-vs-OFF incluido). Resultado: el mecanismo CUMPLE su diseño (cat022 3/3 chunks diana
recuperados, anclaje corpus-amplio +1/−0 con null 0/0) y AUN ASÍ es NO-GO — rompe el flip
shippeado hp018·6K8 (el trim recortó el surrogate load-bearing por 3 milésimas de sim-pregunta),
deja hp011 fuera del null y SUBE el negcontrol 7→9 (la posición-de-interleave tampoco es proxy de
rank). Revert por pre-registro, seam preservado. Lo que el NO-GO compra: la clase cat022 queda
PROBADA recuperable (target correcto) y los 4 ejes observables (canal/score/sim-pregunta/posición)
quedan MEDIDOS como ciegos al valor — el discriminador restante es FAMILIA, lo que convierte el
landing family-aware en el primer consumo medible del entity-linking (DEC-074) en vez de otra
iteración de tuning. El flag anti-overfit (G4) funcionó por diseño: los 6 diana no podían tumbar
el lever; los controles amplios sí. De propina: synth residual mapeado (6/8 estables, cluster
cat021 NO reaparece → fork DEC-097 sigue cerrado) y matriz de transición v3→v2.2 reconstruida de
git como artefacto reproducible. Prod intacto todo el día.

## s103b (9-10 jul 2026, autónomo con tope $150) — del NO-GO al candidato de ship en una noche: la alternativa que el gate compró

Alberto autorizó continuar autónomo (≤$150) y preguntó por top-100. Respuesta medida, no
opinada: probe judge-free → NO paga (3/11 retrieval-miss entrarían, a ranks 55-91; 5 ni a 100 =
gap de vocabulario s93; el coste del ancho en el rerank está medido s98 y ef_search=120 se queda
corto multi-modelo). Lo grande: al aterrizar la arrancada del entity-linking, el artefacto F9
(regla C contra mi propia claim, con lista RESUELTA de modelos) tumbó el family-aware landing
(0 cross-family positivos en TODOS los golds clave — habría sido NO-OP) y eso forzó re-examinar
la A2 que DEC-100 descartó sin medir: NO re-cobrar. v3.1 = el aside como EXTENSIÓN ACOTADA
(patrón identity-fetch) — el doble descuento desaparece de raíz. Dúo r1 sobre el diseño (ambos
lados CON-CAMBIOS: 5/6 filas de mi tabla eran tautológicas, el spec tenía dos cableados y uno
era NO-OP silencioso, el gate no medía el efecto real rerank-50→60) → v3.1 cableada → TODOS los
gates judge-free en verde (diana 4/4 incluido hp018·p21; containment 0-missing; negcontrol 6≤7;
flips 2/2 tras cazar un artefacto de instrumento — `_stage_of` clasificaba por primera-
desaparición y el pipeline ya no es monotónico) → bvg K=3: +cat022 FALLO→PASS, cat024 artefacto
del juez (5ª instancia DEC-092b), y UNA regresión real: cat021, el cluster composición-sensible
de DEC-097, cuyo fork pre-declarado disparó con composición fallida reproducible (el rerank-60
sirve el user-guide EN del 40/40R y la generación asume la variante). Su remedio: el seam s102
cura cat021 3/3 pero rompe hp009 (2/3; la iteración de wording lo EMPEORÓ a 3/3 — segunda
medición de "los guardrails de prompt no auto-ejecutan") → trigger movido A CÓDIGO
(`_SELECTION_INTENT`): sweep 39 dev = solo cat021 dispara, spec/avería byte-idénticas POR
CONSTRUCCIÓN. Ronda de dúo sobre el DIFF: el cross-model clavó 2 CRÍTICOS de PROCESO (el D1-v1
decía NO-PASA y seguí — instrumento inválido, pero la desviación del pre-registro va DECLARADA,
no narrada como pasó; cambio de métrica visible en addendum) y el sub-agente EJECUTÓ el regex
contra fraseo real de técnico y tumbó mis alternativas laxas («¿cuál pongo?» = resistencias/
jumpers) + el agujero de freeze en bvg_kmajority. Todo corregido y testeado (473 verdes, 12
tests nuevos). hp009 atribuido con probe de 2 brazos: PARCIAL=PARCIAL, baseline. Paquete DEC-101
a GO de Alberto: merge + `GENERATOR_SELECTION_BLOCK=on` en Railway (sin el env var el neto sería
+cat022/−cat021 — asimetría de activación declarada). Coste ~$90. El día entero es el sistema
funcionando: 5 rondas de dúo, ~50 findings confirmados/~1 FP, 3 instrumentos cazados mintiendo
(D1-v1, table-gate, mi regex) — y cada gate que tumbó algo compró el diseño siguiente.

## s104 (10 jul 2026) — R2 con red de seguridad completa: el día en que TODOS los gates dispararon y ninguno mintió

Alberto dio GO a R2 con dos mandatos (no gastar dos veces; modelo barato sin perder calidad) y
la sesión fue una cadena de puertas haciendo su trabajo. La auditoría previa encontró el tramo
T1 YA en prod (21.995 enunciados — nada que re-pagar) y el dúo del diseño cazó el CRÍTICO que
habría quemado ~$115 en el sitio equivocado: el pase legacy insertaba al índice COMPARTIDO
(el NO-GO medido de DEC-088). Pipeline reconstruido (generar→dump→loader-A3) + 9 fixes con
bugs ejecutados por el propio sub-agente («claude-haiku-4-5» contiene "-5" y el guard de la
familia 5 le quitaba el temperature=0 justo al brazo del A/B; sha_of por substring colisionaba
en 5 nombres reales del store). G0 midió a Haiku MEJOR que Sonnet en QA-pass y 4x más barato,
con el panel de 40 pares cazando meta-líneas conversacionales DEL BRAZO CARO que el QA
determinista no ve. T2 generó 81/81 docs (45.889 enunciados, ~$10) sobreviviendo a una
desconexión de internet (checkpoint por-doc + ledger con snapshot que pagó cuando OneDrive
desmaterializó el fichero) y a la cuota de OpenAI agotándose a mitad (recarga de Alberto).
Y entonces la puerta grande: cargados 49K a la tabla A3 (71K total), el gate anti-dilución
disparó — 0 ganancias de ancla, 2 OK perdidas, el sort-mixto sin cuota no aguanta 3x
(exactamente el riesgo-mayor declarado, exactamente la clase que hyq resolvió con cuota) →
rollback verificado 0/0, tail no gastado, activo a salvo en dumps. En paralelo, el assessment
v3 estampó la medición del ship de ayer: OK 91→93, retrieval-miss 12→7, la lista diana completa
del DEC-101 convertida, y los 2 "corpus-gap" nuevos verificados a mano como FN (5ª y 6ª vez).
El día deja: +2 OK en el scoreboard, un activo de 55K enunciados pagado y protegido, el modo
de fallo de escala diagnosticado con artefactos, y la cabeza de cola nítida — la cuota del
canal enunciados, con dúo y su gate de re-carga ya construido.

## s194 (17 jul 2026) — cohorte fresca para síntesis; el gate para antes del selector (DEC-103)

Retomado `main@5868c9b` (PR #120) en worktree limpio. La foto canónica comparable se mantuvo:
157 facts = 143 OK, 12 synthesis-miss y 2 retrieval-miss; 77 legacy carries impiden aún un KPI
atómico oficial. Se eligió el bucket dominante de síntesis upstream→downstream, sin reabrir
S140 (`chunks_v3` wholesale NO-GO) ni ajustar S193 sobre sus 14 preguntas observadas.

El primer diseño intentaba decidir con S168/S170. La revisión GPT-5.5 lo tumbó: era independiente
de targets pero no fresco. Se construyó entonces un freeze GET-only real de las 25.090 filas de
`chunks_v2`: 14 documentos/fabricantes nuevos, 7 tabla + 7 prosa, exclusiones versionadas y
manifest pre-autor de unidades. Una segunda revisión crítica cazó cinco fallos más antes del
gasto: conflictos no validados, HOLD inexistente, prereg/permit pendientes, overclaim de overlap
semántico y IDs no sellados. Todos se corrigieron; tally conjunto = 10/10 confirmados, 0 FP.

Ejecución económica sin retry: Haiku 14/14, $0,078186. Produjo 13 preguntas elegibles,
50 puntos, 7 tabla y 6 prosa, pero `s194_src_09` excedió la cardinalidad de IDs de soporte.
Como el gate exigía cero inválidos, resultado `NO_GO_COHORT_CONSTRUCTION`. Luna = 0 llamadas;
targets = cerrados; facts movidos = 0; producción/DB/Railway = intactos. Root cause del
instrumento: el JSON Schema permitía cualquier longitud de array aunque el prompt/validator
exigían 1–3 IDs. Próxima iteración legítima: sellar esa cardinalidad y usar otra cohorte fresca,
sin reutilizar outputs ni relajar umbrales.

## pre-S197 (17 jul 2026) — runner Fable recuperado y siguiente gate upstream preparado (DEC-106)

Tras integrar S196 en PR #123 se recuperó desde el workspace anterior el ejecutor directo de
`claude-fable-5` que sí se había usado desde Codex pero nunca se versionó. El contrato nuevo liga
Sol 5.6 xhigh y Fable a los mismos bytes ordenados, briefing, HEAD, manifiesto y vista Git; guarda
respuestas físicas, rechaza symlinks/cambios concurrentes y conserva evidencia de fallos. Sol
encontró cuatro defectos medios finales, todos corregidos con pruebas. Fable llegó dos veces al
modelo exacto y leyó el repo, pero devolvió un bloque final vacío; ambos intentos quedaron como
`failed_api` con trace, no como `omitted_unavailable` ni como dúo completo. Alberto pidió evitar
otra convergencia y volver cuanto antes al aumento de OK, por lo que no hubo tercer intento.

En paralelo quedó versionado, aún sin gasto ni cohorte generada, el tramo S197: doble scan GET-only
de una cohorte real nueva excluyendo S194+S195; schema estático S196 con autor Haiku; validación
determinista y screening excerpt-internal Luna de 14/14; locks/checkpoints, cero retries y techo
interno $3. Facts movidos = 0. El siguiente paso es integrar con CI verde y ejecutar una sola vez
ese gate upstream; planner/targets sólo se abren después de GO. `chunks_v3` permanece NO-GO
wholesale y Railway sigue fuera del gate de merge.

## S197 (17 jul 2026) — transporte válido, autor semánticamente insuficiente (DEC-107)

Desde `main@87a06bd` se ejecutó una sola cohorte real: doble scan idéntico de 25.090 filas,
14 documentos/fabricantes nuevos, 7 tabla + 7 prosa y cero overlap S194/S195/targets. El schema
rectangular S196 sí generalizó: Haiku hizo 14/14, 14 elegibles, 42 puntos y cero inválidos. Luna
screened 14/14 por $0,063155 y paró el funnel: 12/14 ítems fallaron; 8 por point-set incompleto
respecto a la pregunta, 5 por support/relevancia y 6 por facet. Total $0,15476.

El resultado fue `NO_GO_COHORT_CONSTRUCTION`, facts 0 y planner/targets/DB/runtime intactos. La
causa dominante pasa de compilación a scope closure: el mismo autor formula una pregunta amplia y
luego sólo puede emitir cuatro puntos. Próximo mecanismo generalizable: puntos support-bound y
facetados primero; pregunta acotada después; cohorte nueva excluyendo también S197. No se repara ni
reintenta esta población. `chunks_v3` y Railway no cambian.


## S269 (18-19 jul 2026, ultracode nocturno autónomo, mandato ≥98% OK) — triage de los 12 + contrato must-preserve medido + diagramas y voz cerrados

Encargo de Alberto: familiarizarse con el avance Codex (143/157 OK, 12 synthesis-miss),
re-revisar el análisis de causas, y atacar los 12 con mecanismos BP/robustos/escalables —
o entender si los golds los inflan. Dúo Fable+Sol xhigh en validación de diseño; ejecución en
modelos baratos; smoke antes de gasto; tope $300.

**Mapa (7 lectores).** El "análisis de Sol de los 12" no existía per-fact (S169 quedó
incompleto); lo que hay: taxonomía causal s243 (11/12 within-cited-fragment; familias
qualifier 5 / bundle 3 / mandatory 3 / count 1) + S156 (frontier one-shot con contexto completo
solo cubre 2-4/13 → el problema es el contrato de completitud, no capacidad). Positivos
enterrados: S193 (+5/0 regresiones, cerrado por umbral de selector), S249 (precisión 1.0),
S223 (cerrado con review incompleta). Restricción vigente s261/s260: cohorte estructural
independiente ANTES de tocar los 12.

**Track 1 — triage (DEC-121).** 4 analistas + audit del instrumento + verificador adversarial
= 12/12 verificados: 8 CORE / 3 SUPPLEMENTARY / 1 SOURCE-CONFLICT ("seis" vs 7 columnas
verificadas al vector). Instrumento JUSTO (0 FN). Si Alberto acepta: denominador 154, objetivo
+8. Packet al píxel con renders por página → adjudicación de Alberto.

**Track 2 — contrato must-preserve (DEC-122).** Diseño v2 dúo-adjudicado (18/18, 0 FP) →
build → el dúo del build (16 hallazgos, 0 FP) tumbó el INSTRUMENTO v1: gold de modelo barato
no fiable (87% de negativos mal etiquetados; Fable cazó además 2 errores del propio diagnóstico
del orquestador — el anti-bias funcionando). Pivote: harness de MUTACIONES con gold mecánico
(patrón S249). 3 iteraciones de contrato de binding, cada una en población fresca
(seed-270/271/272): **final recall 4/4 GO (1.0/0.93/1.0/0.83) + cross-binding 0 + attestation
0 + MANDATORY limpio**; residual abierto: clean-noise R/B FP=40 (hermanos con 2 tokens
genuinos) — decisión de diseño para Alberto, sin iterar más (compromiso anti-overfit). El
brazo híbrido Haiku ($0.57) resultó idéntico: el residual es del binding, no de la detección.
Etapa 2 (probe a los 4 targets) queda gateada por la adjudicación del residual + la reapertura
formal s222/s223 (decisión de Alberto, con la evidencia del cierre-incompleto de S223).

**Ortogonales.** (A) Diagramas (DEC-123): el bot no servía NINGUNO (0/25.090 URLs en v2);
registro document_visual_assets construido completo en rama propia — bridge 5.096 páginas
byte-idéntico al audit S190, clasificador full-bridge $3.52 (serving-set 4.489), gate de
activación PASS 59/60 + 0 portadas; migración 014 BLOQUEADA por permisos → runbook de 5 pasos
para Alberto; flag off. (B) Voz (DEC-124): catálogo regenerado (+6 modelos al vocabulario
Whisper), whisper-1 se queda, Wispr Flow descartado (app cliente, no ASR server-side);
migración de ASR sigue gateada a 30 audios reales.

**Método/coste.** 2 workflows (7+7 agentes) + panel visual (6) + 3 builders + 2 rondas de dúo
completas (Sol 695K+504K tokens, Fable 106K+202K; 1 intento vacío de Fable re-lanzado per
DEC-106). Gasto externo total ≈ $27 de $300. Las claims fuertes verificadas por regla-C en
código/datos antes de adjudicar. Sin tocar prod; sin targets expuestos; held-out intacto;
suite 1.933 verdes (4 CRLF pre-existentes del checkout Windows).

## S270 (19 jul 2026, continuación autónoma) — adjudicación de Alberto aplicada + campaña de probes del mecanismo + visual data-ready

Alberto adjudicó el packet (DEC-125: 8 CORE incl. TONE restaurada, 2 SUPP, disclosure-respec,
merge warnings → denominador 154, objetivo +8) y dio permiso explícito a la reapertura s222/s223
(DEC-126). Migración 014 aplicada por Alberto; carga visual completada y verificada (5.096 filas,
4.489 servibles) — diagramas data-ready, flag pendiente. Campaña de probes del contrato
must-preserve (DEC-127): 3 probes pareados con validación fresca previa a cada versión →
1 conversión ESTABLE (obl_b6f6, seguridad, 3/3 en v2 y v3), disclosure de dos lados ENTREGADO
(spec 872c a decisión), 0 regresiones/0 conflictos en 36 réplicas, Etapa 3 viva limpia (5/5
monotónicos, 0 apéndices en preguntas sanas). Iteración detenida por disciplina; residual
mapeado por-clase con dueño (serving-view, alcance-no-citado, binding-tension, gap-instrumento
híbrido, retrieval-2). Coste sesión completa ≈ $36.

## S276 (20 jul 2026) — seed-278 NO-GO, norte conversacional direccional y recovery del runner Fable

Se ejecutó el screen offline fresco seed-278 de `missing-definition-sibling`: GET-only sobre 80
documentos seleccionados/1.033 fragmentos, 0 modelos y 0 escrituras DB. Censó 67 bloques en 24
documentos y rederivó 67/67 full/truncated, pero sólo observó 2 fabricantes frente al mínimo
congelado de 3. La inspección posterior encontró 41/67 descripciones visuales/UI y dominancia
20/67 de un documento. Veredicto: `NO_GO_OFFLINE_SCREEN`; seed consumido, sin runtime, A/B, deploy
ni crédito al funnel. La revisión aclaró que 67/67 es autoconsistencia del parser, los 201 boundary
controls son sintéticos y los hashes post-run no demuestran la cronología completa del freeze.

En paralelo se auditó la causa de los seis synthesis-miss y el cimiento futuro multi-turn/multi-hop.
Cinco de seis ya reciben su evidencia parcial o completa; el gap estructural dominante está en
selección/binding/cita, no en ampliar top-k. El blueprint
`DIRECTIONAL_BLUEPRINT_NO_BUILD_AUTHORIZATION` propone orquestador
transport-neutral, estado durable versionado, deduplicación de ingress, lease/reclaim, orden por
conversación y outbox; single-hop barato por defecto; rewrite condicional; 2 hops default/3 hard
cap; verifier fail-closed. Repair queda separado como segundo writer y el lifecycle RGPD es gate
previo a DDL. No se autorizó ningún cambio productivo ni de schema.

El dúo original cerró con 8 findings únicos confirmados, 0 FP, máximo medio. Durante Fable, tres
runs auditados terminaron `end_turn` sin texto visible tras tools (491.741 tokens): dos traces
persistieron `thinking` + `text` vacío y uno `content=[]`; otro run no-tools
truncó por `max_tokens` (33.435), y el primer run exitoso consumió 116.863. La revisión de la
corrección añadió Sol 99.434 + Fable 156.993 tokens; un Sol previo falló por 500 interno tras
68.513. Total registrado de la sesión: Fable 799.032 y Sol 271.606 tokens. El screen costó $0 en
modelos; el runner no registra el equivalente monetario de las revisiones.

El segundo dúo cazó que el primer recovery era inoperante: reinyectaba el assistant vacío y la API
real lo rechaza con HTTP 400. También encontró `tool_use` admisible en el cierre, schemas fuera de
la cota, falta de fencing/outbox unique, deny-list incompleta y gaps de tests/framing. Todos los
defectos del runner/contrato se verificaron y corrigieron: recovery por segundo user turn (request
vivo aceptado), un solo retry tools-off, fencing+CAS propietario, budget completo y validators
fail-closed. La causa raíz interna del modelo/proveedor sigue sin estar demostrada; el cambio
mitiga el síntoma y falla cerrado. La ronda incluyó por
error una adjudicación previa como seed, así que queda NO-PASS, no como certificación independiente.
El trace prueba autoconsistencia de lo persistido, no completitud atestada por el proveedor. Tests
dirigidos antes de la suite final: 56 del reviewer + 14 del screen. Suite completa: 2.225 passed,
6 skipped y los 4 fallos raw-hash/CRLF de Windows ya conocidos; ninguna regresión nueva de S276.

## S277 (20 jul 2026) — el miss vivo convierte C1 en una unidad de release verificable y P1 se construye antes de gastar

Alberto hizo la pregunta PEARL solicitada. El bot produjo una sola generación de 4.449 caracteres
que Telegram partió en dos mensajes: explicó extensamente retardos, pero omitió ambos avisos F12 y
dio «menú 8» como instrucción sin revelar el conflicto 7-vs-8. La observación corrigió dos premisas:
dos mensajes no eran dos respuestas y el target alcanzable en retrieval no implicaba síntesis. El
campo `query_logs.response`, truncado a 4.096 caracteres, tampoco podía ser el árbitro del texto
completo. El marcador quedó 146/154 (94,81 %), sin crédito nuevo.

Se materializó en la PR #184 un release profile atómico `coverage_c1_v1`, un seam único de serving,
trazas privacy-safe y gates A/B. A pasa offline sin red; B repitió cinco GET read-only, leyó 120
filas/110 candidatas y alcanzó el target en F12, con 0 writes y 0 modelos. El primer intento B
agotó su timeout de tres segundos y falló cerrado; un único retry de la lectura completó. La
verificación en CI descubrió que el pin S113 era raw-CRLF de Windows; se cambió a SHA-256 LF para
que Windows/Linux validen los mismos bytes semánticos. No se desplegó el profile ni la migración.

Después se diseñó y construyó P1 offline. Preregistra 13 QIDs, 27 réplicas/27 generaciones y exactamente
81 llamadas pagables; protege 43 filas base de peso KPI 42, una guarda hp013 y el target compuesto
hp017. El bound estático es 6,777 USD y el cap 10 USD. El paquete incluye contrato fact-specific,
scorer determinista, doble opt-in, WAL fsync/no-retry/no-double-send, identidad Git/runtime/config,
proyección semántica, fingerprint/fence y cadena de receipts input→provider→postprocesado→render.
`finalize` recompone el score desde contrato/prereg/27 receipts y no confía en un PASS aportado.
El control histórico de cero coste confirmó 3/3 el conflicto hp017 y dejó
`HOLD_PREPAID_KNOWN_CONFLICT_RISK` sin atribuir resultado al candidato.

La integración encontró antes del commit dos fallos de diseño materiales: el primer contrato
forzaba `VISUAL_ASSETS_REGISTRY=off` aunque la capacidad era ortogonal/viva, y el primer finalizer
aceptaba demasiado del JSON de score. Se cambió a preservación exacta `on|off` y re-score
autoritativo. Una auditoría cross-cut posterior detectó bindings incompletos entre pregunta
preregistrada, payload físico, stop reason y respuesta; configuración 50→10/3500 no suficientemente
sellada; límites de tokens post-send; fence sin deadline/heartbeat final; y resume sin comparación
directa del request hash. Se añadieron invariantes y mutaciones para todas esas clases antes del
dúo final. Dos auditorías de congelación posteriores encontraron y cerraron además: pérdida/
corrupción de responses y watches tras el run; heartbeat con edad absoluta vencida; continuación
tras un terminal UNKNOWN/FAILED; gasto fuera del orden preregistrado; reapertura sin volver a
validar las 27 réplicas; drift tardío de implementación; y ausencia de recomputación de modelo,
usage, costes y presupuesto sobre las 81 respuestas/162 eventos WAL. La suite P1 focal final quedó
en **181/181**.

El supuesto «manifest físico» del fence también se corrigió de framing: los hashes disponibles
sólo describen nombres RPC/GET/relaciones y locks, no firmas/ACL/overloads, índices ni
PostgREST/config observados. No se fabricó un contrato live con datos sintéticos. Los cuatro CLI
operativos quedan bloqueados como primera operación con
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED` hasta una fase externa revisada con bodies
pre/watch/post y expected contract canónico.

Fable 5 sí estuvo disponible y se usó de forma real: las rondas de diseño terminaron normalmente
como `claude-fable-5` a las 16:37 (168.963 tokens) y 17:07 (171.732), ambas con `end_turn` final.
Los intentos fallidos de esta sesión fueron preflights conservadores de presupuesto, distintos del
síntoma upstream S276. La investigación S276 sigue siendo el estado correcto: tres respuestas
físicas vacías descartaron pérdida del parser local, pero no demostraron la causa raíz interna;
#183 sólo añade una recuperación tools-off y luego falla cerrado.

El dúo final de implementación terminó con Sol a las 00:06:50 y Fable 5 a las 00:08:56.
Confirmó que los dos false-PASS semánticos estaban cerrados —claim canónico completo + quote/hash
fuente para auto-PASS; negación, relación alterada, paráfrasis o contenido irrelevante quedan
REVIEW/FAIL—, pero encontró un blocker nuevo para retirar la stop-line: el manifest de
implementation hashes no cubre transitivamente al menos `src/rag/answer_planner.py`, ejecutado por
el scorer de conflicto. Conforme al corte anti-parálisis, no se abrió otra ronda de parche+dúo:
el core se cierra como HOLD seguro, no como release-ready. La suite amplia local terminó
2461 pass / 6 skip / 4 fallos raw-hash/CRLF Windows ya conocidos (s117, s131, s133×2); CI Linux
queda como autoridad pendiente. Totales: 0 llamadas P1, 0 mutaciones Railway/Supabase y ninguna
autorización de gasto o despliegue.

### S277 — segunda P1: bound de rerank reproducido y corregido

Tras corregir la atestación del SDK, una nueva P1 sobre `e49cb73` abrió y cerró correctamente
el fence, pero terminó `NO_GO_PARTIAL` tras una sola embedding completada. No hubo WAL ni llamada
Anthropic para el rerank. Coste observado: 0,0000024 USD; 0/27 réplicas; cero mutaciones; manifest
y fingerprint idénticos pre/post. La autorización quedó consumida y `score` rechazó el artefacto
incompleto.

El replay read-only exacto reutilizó ese embedding: 43 filas, 34.192 caracteres de preview,
payload de 40.220 bytes y bound total 40.732 frente al límite 10.000. Reprodujo
`HOLD_INPUT_TOKEN_BOUND` sin inferencia nueva. El wrapper strict había ocultado el código como
`RerankStrictError`; se amplió su `try` para preservar también fallos P1 pre-WAL. Alberto fijó el
techo duro en 30 USD y el prereg se alineó con bounds 95.000/249.000 y worst-case 29,727 USD,
sin alterar la lógica productiva RAG. El fix queda offline-green y requiere una autorización/run
nuevos; no existe `P1_PASS` ni GO.

### S277 — tercera P1: falso FAIL de Markdown corregido y miss de fuente aislado

La P1 sobre `b06f05c` persistió 18/27 réplicas y completó 54/81 llamadas antes de parar en
`hp011:r1` con `NO_GO_PROTECTED_CONTRACT`. Coste observado: 1,82090244 USD; cero reserva
desconocida, cero mutaciones Railway/Supabase y fence `CLOSED_VERIFIED` con corpus/manifest
idénticos pre/post. No se creó `P1_PASS`.

La parada fue inicialmente un FAIL falso: el scorer interpretaba los separadores Markdown `---`
como el valor técnico `--` y exigía `t.A`. Se estrechó el detector a usos técnicos inequívocos y
el mismo artefacto pasa a REVIEW offline, sin repetir inferencias. La inspección de ese REVIEW
aisló el defecto productivo: la página 63 autoritativa del manual RP1r-Supra no estaba en el pool,
prefijo, structural fetch ni contexto, mientras F9 procedía de una guía rápida incompleta. La
respuesta invirtió el significado de `00`. Pool coverage e HYQ tampoco recuperaron la página en
probes GET-only, por lo que no habrá otro run pagado hasta demostrar una recuperación
intra-documento genérica y acotada. Los 18 artefactos se reutilizan para diagnóstico; no pueden
mezclarse con nueve respuestas nuevas para certificar un código distinto.

La inspección posterior del corpus añadió una stop-line más temprana: p63 existe en v.04 (2013,
`t.H`) y v.07 (2018, corrección visual `t.Fi`→`t.A`), ambas activas. El dedupe cruza las revisiones
y excluye la fila v.07 usada por la adjudicación gold; la migración de reconciliación dejó la
precedencia expresamente diferida. Por ello no se implementa una búsqueda por filename que mezcle
autoridades ni un latest-wins silencioso. Primero se prepara y mide la adjudicación lifecycle y la
reparación de dedupe; su aplicación live requiere autorización separada.

### S277 — migración lifecycle HP011 preparada offline

La prelectura GET-only confirmó la foto exacta: v.04=94 chunks y 43 `duplicate_of` no nulos;
v.07=96 y 42. La matriz entre revisiones era `3/40/38/4` (v.04→v.04, v.04→v.07,
v.07→v.04, v.07→v.07), incluido p63 v.07→p63 v.04. Se creó la migración transaccional
`20260721190847`, que adjudica v.07 sobre v.04, congela y limpia solo las 38 parejas v.07→v.04
y corrige las notas de lifecycle; cualquier drift aborta. El rollback manual emparejado restaura
las 38 parejas y ambos documentos bajo guards simétricos.

Seis tests de contrato pasan. Un PostgreSQL embebido desechable ejecutó aplicación, rollback
exacto y un caso con drift que abortó sin mutar lifecycle. No se aplicó la migración live, no hubo
llamadas de modelo ni gasto. Estado: `HP011_LIFECYCLE_MIGRATION_READY_LIVE_AUTHORIZATION_PENDING`;
el siguiente paso requiere autorización separada para aplicar/verificar antes de construir la
lane intradocumento.

### S277 — migración lifecycle HP011 aplicada y verificada live

Alberto autorizó explícitamente aplicar el cambio. El primer `db push --dry-run` desde el
checkout normal falló cerrado: producción contenía siete versiones antiguas sin fichero local y
el repo tres migraciones anteriores sin fila remota. No se usaron `--include-all` ni
`migration repair`. Se construyó una proyección temporal exacta con las diez versiones ya
aplicadas como stubs no ejecutables y un hardlink byte-idéntico del target; el segundo dry-run
enumeró únicamente `20260721190847_reconcile_hp011_v04_v07_lifecycle.sql`.

Supabase CLI 2.109.1 aplicó esa única migración con exit 0. La verificación posterior confirmó
simultáneamente la fila `supabase_migrations.schema_migrations` (versión, nombre y 8 statements)
y todas las postcondiciones: v.04 `superseded` por v.07, v.07 `active` y sucesora de v.04,
94/96 chunks intactos, 43/4 duplicados no nulos, topología 3/40/0/4 y p63 v.07 canónica con
`duplicate_of=NULL`. Las tres versiones local-only siguen ausentes remotamente y los diez stubs
no alteraron history. No hubo modelos, gasto, Railway, deploy, merge ni movimiento del KPI.

El receipt auditable es `evals/s277_hp011_lifecycle_live_apply_receipt_v1.json`. Estado:
`HP011_LIFECYCLE_APPLIED_VERIFIED_DOCUMENT_LOCAL_RECOVERY_PENDING`; el siguiente paso es medir
sin modelos la lane intradocumento genérica y fail-closed. El drift permanente del historial
queda en TECH_DEBT #55 y prohíbe `db push` normal hasta reconciliación separada.

### S277 — recuperación document-local alcanza `GO_MECHANISM`

Se reconcilió el historial Supabase sin fabricar versiones: siete SQL remote-only se recuperaron
con una comparación normalizada y tres local-only ausentes se trasladaron a propuestas. Con el
árbol 11/11 alineado se aplicaron normalmente las migraciones del snapshot atómico y de autoridad
exacta de blob, sin `migration repair` ni `--include-all`.

La lane default-off pasó el probe GET-only de 13 QIDs: prefijos intactos, máximo un append, sólo
hp011 seleccionado y registro p63 ligado a la revisión activa v.07 y al blob exacto. La identidad
servida se canonicaliza desde `documents` (`Notifier / RP1r / usuario`) en vez de conservar labels
legacy del chunk; el catálogo histórico no participa dentro del blob ya autorizado. Los fallos de
lifecycle, identidad, caps, formato y recibo degradan cerrados, incluida una fila pipe sin
cabecera/separador/aridad coherente. El probe hizo 84 GET, cero llamadas de modelo y cero
escrituras de base de datos.

El resultado es `GO_MECHANISM`, no `P1_PASS`: C1 sigue NO-GO y el KPI permanece 146/154.
Siguiente paso: perfil atómico nuevo (`coverage_c1_v2`) y, después, P1 limpia 27/27 con
artefactos nuevos.

### S277 — lineage v2 aplicada, `coverage_c1_v2` listo y P1 v2 pendiente

La cuarta ronda Sol/Fable cerró el último defecto de autoridad positiva: una etiqueta legacy de
familia no podía demostrar membresía. Se introdujo `document_revision_lineages`, se vinculó HP011
mediante `documents.revision_lineage_id`, se exigió una sola revisión activa por lineage y se
limitó el pool combinado a 64 con estado de overflow explícito. La migración lineage v2 y la ACL
P1 se aplicaron live. El receipt v2 quedó `RECONCILED` con 7/7 checks; la definición live de
`document_local_snapshot_v2` quedó pineada por SHA-256 LF
`19975e3784e0cd12176cbf0b246c4e0ee8a4eed008de7542d0c6d0b6c0f9a82e`.

El probe v2 repitió el gate estrecho del mecanismo: 22/22 checks, 13 QIDs, prefijos intactos,
sólo HP011 seleccionado, 84 GET, cero llamadas de modelo y cero escrituras DB. Reportó de forma
explícita que 12/13 QIDs no atraviesan la puerta de lifecycle/idioma. Las cuatro rondas
adversariales Sol/Fable terminaron adjudicadas: 35 findings, 30 confirmados/resueltos y 5 falsos
positivos. No se ejecutó una quinta ronda; el packet v5 quedó como handoff terminal.

Se materializó `coverage_c1_v2` sin mutar `coverage_c1_v1`: añade document-local al perfil
atómico, sella el GET v2 y exige una traza por réplica ligada 1:1 al transporte físico; hp011:r1/r2
deben seleccionar y servir un único ID. El preregistro P1 v2 conserva 27/27 réplicas, 81 llamadas
y cap interno de 30 USD. **No se ejecutó P1 v2 y no existe `P1_PASS`.** El 18/27 histórico queda
sólo como diagnóstico. KPI: 146/154 (94,81 %), sin movimiento. TECH_DEBT #29 no bloquea esta
medición, pero sí merge/release global; multi-turn/multi-hop continúa `NOT_BUILT`.

### S277 — P1 fresca completa `b92ff51`: NO-GO y cambio a método offline-first

El run `p1-v3-b92ff51-20260722a` completó las 27 réplicas y las 81 llamadas previstas sobre
commit `b92ff51`/tree `de347f6`, por 2,69369748 USD. El fence cerró, manifest y fingerprint
pre/post coincidieron, Railway/Supabase registraron cero mutaciones y no hubo deploy. La
adjudicación ciega de 91 ítems produjo 62 PASS y 29 FAIL; agrupados por respuesta, 10/27 quedaron
limpias y 17/27 con al menos un fallo. `final.json` cerró
`P1_NO_GO / NO_GO_PROTECTED_CONTRACT`. El KPI continúa 146/154.

La tanda incluyó tres runs v2 diagnósticos previos a 17/27: `511bd58` (51 llamadas,
1,70976360 USD), `b131464` (54, 1,81440744 USD) y `eefc388` (54, 1,82350344 USD). Los dos últimos
pararon `NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET`; el primero, `NO_GO_PROTECTED_CONTRACT`. Con
`b92ff51`, el subtotal observado de los cuatro es 8,04137196 USD y reserva desconocida cero. No
se reanudan ni mezclan; el saldo total de la autorización requiere reconciliar también todo gasto
fuera de este artifact root.

La medición corrigió dos confusiones: el 18/27 anterior era cardinalidad generada por un run
abortado, no calidad, y 62/29 son ítems semánticos, no respuestas. El residual también dejó de
tratarse como una sola clase de síntesis: hp018:r1, cat017, hp002 y cat019 requieren resolver
identidad/orden, catálogo, reserva o autoridad/source-card antes del writer; otros fallos sí son
obligaciones compuestas, atribución/conflicto o cita sobre evidencia ya servida.

Se reconoció el coste de haber iterado demasiado sobre runner/scorer/fence sin un filtro barato de
full answers. Se añadió un counterfactual de cero llamadas que reproduce el borde determinista
sobre los 27 drafts/contextos congelados. Su baseline preserva 62/62 PASS y 93/93 checks
automáticos, pero deja 29/29 FAIL, por lo que emite `OFFLINE_PREFLIGHT_HOLD`. Como congela el
contexto no puede arreglar los fallos de fuente: antes de otra P1 se debe añadir un gate separado
de candidate-context/source receipts y combinar ambos hasta corregir los 29 sin regresiones ni
reviews pendientes. El replay WIP existente parte de cero modelos; para el candidato vNext se
diseña primero, se reconcilia el ledger y Protocol 3 Sol+Fable se ejecuta antes del build de
impacto. Si cambia el request hash de embedding/rerank, se exige después un piloto context-only
acotado. La rama conserva
tests que demuestran la semántica de una futura política `replace` y el instrumento; no cambia
runtime. Tanto `replace` como el orden estable de `content_search` se retiraron al comprobar que
los rechazaban correctamente schema/hash históricos. El próximo candidato debe versionar
schema/config/prereg e implementation hashes y no reescribir artefactos sellados.

El traspaso completo para Claude Code quedó en
`docs/HANDOFF_P1_B92FF51_2026-07-22.md`; la PR #184 permanece draft. No se implementó aún
Evidence Contract, catálogo INSPIRE, reserva hp002 ni migración/source-card cat019, y no se
autorizaron merge, deploy, canary ni DDL nuevo. Multi-turn/multi-hop sigue separado bajo DEC-136.

## s278 (22 jul 2026) — gobernanza simplificada + vNext implementado offline (Fable, sesión continua con 2 pausas)

Alberto retomó el traspaso de Codex con Fable y decidió el rumbo: **conservar el aparato s277,
desmontar la obligación procesal** (DEC-148). En una sesión: verificación íntegra del handoff en
host (hash audit PASS, HOLD reproducido exit 2, 324 tests focales) → census de identidad
add-vs-replace 845 unidades $0 con verificación adversarial independiente (CONFIRMADO; 3 filas a
adjudicar; 58 aliases indetectables; ceros tautológicos declarados) → #183 MERGEADO a main
(runtime-inert verificado) y #184 convertido en PR de trabajo (su merge = flip de release por
construcción: el contrato de release_profiles rechaza la config legacy en producción — hallazgo
que corrigió el plan de "mergear la pila ya") → diseño vNext v1 → dúo Protocolo 3 (Sol xhigh 8
hallazgos, 3 críticos incl. stop-line de seguridad #29 omitida; Fable 14; 0 FP) → v2 → implementación
en 4 fases con workflows de lanes disjuntas: guard+quarantine, ORDER BY+autoridad, seals
re-anclados a blobs sellados, migración RLS preparada (NO aplicada), perfil coverage_c1_v3,
reserva hp002, Evidence Contract v1 + iteración de precisión/recall contra el oráculo. Cierre
verificado: **suite 2907/0** y **brazo EC quirúrgico (10/10 réplicas objetivo, colateral 0,
dev-check 14/15)** sobre commit limpio; baseline byte-inerte intacto. La tabla EC por-ítem
(verificada contra receipts) corrigió el techo postgen a 15/29 y el split causal del handoff §5.
Los "4 fallos CRLF conocidos" resultaron ser una clase de 10→89 seals stale que pre-existían en
`b92ff51` prístino — re-anclados, no relajados. Detalle → DEC-148/149. KPI sin movimiento:
146/154 (la aguja se mide en la pasada harness pendiente de ledger).

## s279-s280 (22-23 jul 2026, nocturna) — selection-reach cerrada con census adversarial + diseño multi-turn adjudicado (primer run del modelo Opus-ejecuta/Fable-orquesta)

Sesión autónoma nocturna bajo instrucción de Alberto (dormía): cerrar la etapa de release y
lanzar el diseño multi-turn. La ronda selection-reach pasó por 3 rondas de dúo de diseño + build
en 4 fases (Opus ejecutando, Fable revisando — el nuevo modelo operativo) + census con
freeze-contract que ADJUDICÓ CONTRA el build dos veces (los probes no convertían; la enmienda
A5' tuvo que registrarse como cambio post-probe tras el pushback del dúo a mi framing). Resultado
final: C1 overflow verificado en vivo, cat017 sirviendo su diana bajo vista real, cat019 residual
declarado sin aflojar reglas, suite 3079/0, oráculo byte-inerte, pasada final con hp018 en PASS
holístico. Hallazgo estratégico H0: el lane document-local solo alcanza docs identity-complete —
la campaña de backfill de identidad es el desbloqueador general (workstream post-release). El
diseño multi-turn s280 (Fases 0-1 build / 2-4 gated) quedó adjudicado en v2 con el mecanismo
físico decidido (RPCs SECURITY DEFINER) y la autorización trazada. Detalle → DEC-152; release
pendiente SOLO de la lectura + click de Alberto.

## s281 (23 jul 2026) — día: baseline oficial de 39 + Fase 0 multi-turn completa (con 3 pausas)

Sesión diurna tras el cierre nocturno s279-280, con el mandato "adelante" de Alberto sobre el
plan propuesto (baseline 39 como primer acto + kickoff MT-0 en el modelo Opus-ejecuta/Fable-revisa).
Tres pausas limpias de Alberto (protocolo: agentes parados, WIP committeado etiquetado, memoria
al día; un corte de internet a mitad de la 3ª no perdió nada — el push había entrado).

**Baseline:** worktree nuevo `Technical Bot-s281` (rama off la release 9cfa6f8 → #184 congelada
para su lectura; PR renombrada + des-drafteada de paso). Primer arranque abortado a céntimos
(DB fría: enunciados 500 + coverage timeout fail-open → un baseline degradado de facto no se
estampa); RPCs calentados a mano y relanzada limpia: **12 PASS / 25 PARCIAL / 2 FALLO**, cero
fail-opens salvo hp010 (re-verificada sola: mismo veredicto). Respondidas las 3 preguntas de
Alberto: el juez juzga bien (ruido conocido y acotado), NO se cambia a Sol (s47 vigente), y su
intuición multi-turn es correcta con reparto honesto (resuelve incompletitud, no errores; la
vara single-turn no se relaja).

**Fase 0:** MT-0b y MT-0a en paralelo con el baseline; MT-0c tras ellas; MT-0d al final.
El sistema de review pagó en cada lane: Fable-orquestador cazó `fail_run` inalcanzable (MT-0b)
y el mismatch de vocabulario cross-lane (MT-0a); el dúo focal de MT-0c (obligatorio, zona
effectively-once) convergió ×3 en el janitor-dañino y añadió heartbeat-sin-caller,
auth-service_role y el max_attempts=0 del fake (único de Sol; 1 run InternalServerError con
retry). 9 fixes aplicados por lane Opus y verificados punto-por-punto contra el diff. MT-0d
dejó el bot con 3 seams default-off byte-invariantes (el camino OFF es textualmente el código
viejo). Suites encadenadas: 3079 → 3094 → 3143 → 3146 → **3158/0** (aritmética exacta por lane).

**Cierre:** DEC-153 + PLAN reconciliado (Estado actual s281) + este apéndice + memoria.
Todo en `claude/s281-mt0` @ HEAD del cierre; queda el bloque de Alberto (merge #184 + flip,
matriz RGPD, visto DDL, GO de Fase 1).

### s281 (23 jul, tarde) — RELEASE DESPLEGADA: CI en verde por primera vez + merge #184 + flip verificado vivo

Alberto fue a mergear y el check requerido estaba rojo. Diagnóstico en capas: el CI nunca había
corrido la suite entera (checkout shallow vs drift-seals que exigen commits históricos →
`fetch-depth: 0`); destapado eso, 3 fallos de plataforma latentes (el sha del YAML de facetas
hasheaba bytes de checkout CRLF/LF → sha de contenido canónico + pins re-anclados; y el test de
open-response-perdida esperaba un TIMEOUT que era accidente de timing de Windows — `process_path`
escribe el hold del re-dispatch como respuesta, así que Linux mostraba el comportamiento fiel a
producción; la invariante de recuperación quedó estricta). Primer diagnóstico del fence corregido
sobre la marcha (la vía real era el fichero de respuesta, no el pump). Suite en CI: 3080/0.
Merge de Alberto (`f65ec66`) + flip Railway + smoke: fila sellada `bot_version=f65ec66`, EC vivo.
El smoke ZXSe (elección mía) cayó en el gap D1 conocido (`MIE-MI-600` 88 chunks `unknown`,
verificado en DB): el bot admitió en vez de inventar — conducta correcta sobre agujero de
identidad; H0 sube de prioridad. La rama s281 heredó release+fixes vía merge de main (`32a7ed1`).

## s281b (23-24 jul) — autonomía plena: Fase 1 multi-turn MEDIDA + campaña H0 hasta packet

Con el GO de Alberto (Fase 1 + H0 en paralelo, mandato BP-no-escatimar, herramientas externas
eval-driven, DEC-154 acotando el NO-GO agéntico a su métrica): MT-1b construyó la eval
conversacional (15 flujos, vara K=3, interfaz ConversationPolicy con $0-guarantee estructural);
MT-1a implementó la cascada determinista + rewriter Sonnet dual-prompt (vara 31/31); el dúo
focal la RECHAZÓ-EN-ESTADO con 12 hallazgos ejecutados (artículos ×3-convergente, resurrección
de estado con el espejo del harness compartiendo el bug, validate-rewrite agujereado por
substring/invención, fallback inseguro) → lote 12/12 + vara endurecida a 48 turnos con los
escenarios del propio dúo. El e2e pagado (~$3.3) destapó y midió el fix estructural de que la
query resuelta debe alimentar también la generación (6/8 FALLOs eran el writer sin antecedente)
→ final 18/2/1 con el residual adjudicado a conducta single-turn diseñada. A/B condense-LC:
empate direccional, fontiber default. En paralelo H0: census (solo 6 lineages en 998 docs —
capa nueva s277, no regresión; las capas de identidad previas intactas), packet T3 de re-tag
con la migración simétrica ZXe/ZXSe adjudicada por Alberto (etiqueta=FAMILIA) y el contrato
batch_attested_v1 para industrializar el Tramo 2. Sol abortó 1 run por worktree-cambiante →
patrón nuevo: vista estable dedicada para reviews con lanes paralelas. Todo en claude/s281-mt0;
DB y prod intactas; el paquete de decisiones de Alberto quedó listo en lote.

## s282 (24 jul) — F1 vivo + la campaña H0-T2 hasta expediente de firma

Alberto mergeó #185/#186 y puso los flags: primera conversación real del bot (PEARL + follow-up
resuelto $0, verificado en query_logs). En paralelo, el QA del activo s83 se convirtió en la
demostración más completa del sistema anti-bias hasta la fecha: el instrumento optimista dijo
879, el dúo lo tumbó, el re-gating dijo 548, el LQAS paró en el draw 2 con una clase sistemática
real (Securiton _TD), el guard de plausibilidad la degradó de raíz, el draw 3 confirmó 0/59, el
dúo final tumbó el EXPEDIENTE (ledger ausente + escritura sin sellar) manteniendo la cohorte, y
el lote final lo dejó firmable: manifest sellado 1:1, SQL con before-image y rollback, attestation
con framing estadístico honesto. Cuatro rondas de "no" bien fundamentado antes del primer UPDATE
masivo de la historia del corpus — exactamente el aparato que Alberto pidió. Coste: $0.92.

## s285 (25-28 jul 2026) — La campaña H0 tocó tierra: T3 + T2 ejecutados en la DB de producción

La sesión que convirtió tres días de aparato (census, adjudicaciones, LQAS, expediente) en
escrituras reales. Alberto pegó el SQL de T3 (20 UPDATEs / 221 chunks con sus 26 adjudicaciones
+ 2 documentos basura eliminados con backup) y los chunks `unknown` activos pasaron de 318 a 1
(el compat Notifier-Morley deliberado). El cierre arrastró todo lo colateral: Excel, catálogo
canónico (con el producto `morley:vsn-rp1r-plus2` que Alberto desambiguó con URLs — el alias
apuntaba al producto equivocado de Notifier), la retirada de 5 aliases «nombre-de-propiedad»
(«1 zona», «Dos Zonas»…) que eran falsos positivos latentes del detector, y TECH_DEBT #56
(la clase de separadores del detector no cubre `()*`). El gate cat009 con el catálogo mergeado
dio PASS donde antes había PARCIAL — el saneado pagó solo.

T2 llegó después de que Alberto preguntara lo correcto: «¿esto es Best Practice y qué hago yo?»
— la respuesta (fill-only fail-closed, conteos exactos o aborta, before-image, LQAS con paradas
reales) le bastó, pegó el SQL y la verificación en vivo 1:1 contra el manifest devolvió
533/533 doc_type + 301/301 language, 0 mismatches, 0 sobrescrituras. De regalo: descubrimos que
`documents.language` ya tenía un consumidor vivo (señal de autoridad ES en document-local
coverage), así que el metadato recién escrito alimenta mecanismo real desde el primer día.
Sus preguntas de multi-idioma quedaron respondidas con código en mano: el retrieval no filtra
por idioma (voyage-4-large es multilingüe; el vocabulario técnico ancla cross-language) y los
209 multi-idioma se quedan NULL hasta que exista consumidor de la convención.

Cifras vivas al cierre: 1.169 docs (996 active) · 25.088 chunks_v2 · 1 unknown. La identidad
del corpus — el gap D1 que el smoke ZXSe expuso en producción el día del release — queda
cerrada de punta a punta en cinco días. DEC-161.

## s286 (28-29 jul 2026) — el arco del objetivo: seguridad hp018 cerrada, corpus saneado, vara honesta, telemetría construida

La sesión ejecutó el orden adjudicado por Alberto de punta a punta, con su directiva de autonomía
(«continúa sin buscar mi aprobación de cada paso; input solo en bloqueantes; lo demás,
empaquétalo») como modo operativo. PRIORIDAD-1 primero: la traza de hp018 mostró frecuencia 100%
del patrón peligroso y disparó la excepción del guard adelantado — 3 rondas de dúo (45
hallazgos, incluido 1 falso positivo mío que el tally registra), y el A/B ciego pre-registrado
(veredictos hasheados antes del unmask) dio peligro 10/10→0/20 con 0 supresiones en 48: A'+C'
shippeados default-off. Los tachados `~~` (adjudicación: énfasis mal renderizado) salieron de la
DB con un tokenizer de runs y ceremonia completa de staging+backup — 907 filas, verificación en
vivo 0 mismatches — y la post-verificación cazó dos fugas que el plan no había cerrado
(content_search sin filtro de duplicados y un t.Fi literal en otro chunk, parcheado
píxel-en-mano). La vara v4 de su T2b pasó diseño→dúo→controles→sanity→adjudicación sellada, y el
baseline con la config de ship estampó la línea de salida del objetivo: 11/16/12. Cuando Alberto
preguntó por qué se disparaban los FALLO, la respuesta fue una medición pareada, no una teoría:
re-juzgar las mismas 39 respuestas bajo v3 dio 10/25/4 — la vara explica +8 de los +9 FALLO, el
residuo real es +1, y v4 además PASA una más que v3 porque los SUPP ausentes ya no degradan.
El paquete de telemetría (su GO) atravesó el ciclo completo: el dúo r1 tumbó el diseño v1 (RLS
ausente que habría repetido la exposición pre-hardening, FK sin CASCADE que rompía su borrado
RGPD, una métrica no-info contra una constante que no existe, y una tabla `feedback` viva que yo
había ignorado) → v2 → GO-BUILD → build completo con suite 3308/0. De camino: el parser de
diagramas amputaba la cola de la mitad de las respuestas (fix), el juez multi-turn llevaba toda
la serie s281b con el gold EN BLANCO (fix, re-medición pendiente), y la clasificación P1 de los
flags nuevos se hizo sin tocar el módulo sellado tras comprobar que ampliarlo re-rompía 89 pins.
Cierra la sesión el full del assessment nivel-hecho corriendo como gate del lever loop, con el
smoke validado ($3) y el 500 transitorio del canal enunciados verificado como blip, no como
degradación. Pendiente de Alberto, empaquetado sin urgencia: paste D9 (answer_feedback), re-accept
por el bump de términos, lote de ONs con runbook de sondas, y D1-D11.


## s288 (30 jul 2026, tramo autónomo) — A-core: de la consolidación al paste

Alberto adjudicó upstream-first («¿por qué no recomiendas A?») y dio «arranca y procede de
forma autónoma». El tramo convirtió la consolidación A1+A2 en un arco completo: census
verificado contra la DB viva (los placeholder son sha256 del NOMBRE; el binding
extraction==source_pdf ya se cumplía en 414 docs; solo 9 docs con lineage; 7.421 filas hyq
apuntando a padres deduplicados; 1.334 PDFs locales en OneDrive), H1 pre-verificada a mano
34/34, spec normativo único llevado por el dúo a v3 en dos rondas (18/18 hallazgos confirmados,
0 FP — Sol tumbó dos veces el bulk-lineage y una la columna document_id en hyq; Fable cazó la
circularidad del gate H1 y el guard del UNIQUE), y build en carriles Opus: census F0
determinista (H1 60/60), lane F2 endurecida (suite 3393, smoke embed real OK), packet P-A de
585 filas verificado 16/16 contra la DB, y un detector de idioma que su propio gate de
calibración paró dos veces hasta cazar la clase real (anotaciones inglesas del extractor en
docs españoles diagram-heavy) y cerrar en 100,0% con 2 backfills erróneos evitados. Bandeja de
Alberto: paste P-A (single point of failure del arco), QA-30 de idioma (30/30-o-HALT), y la
política de tramos de lineage. Traza: DEC-165; tally en adversarial_review_log (3 entradas).


## s288b (31 jul 2026) — lever ontología hyq: de autorar a adoptar

El dúo tumbó dos veces el diseño inicial (autorar arquetipos que ya existían en v4/v5;
adoptar el par sin su barrera) y el lever final quedó en su forma mínima: dos punteros, una
barrera espejo y trazabilidad, con la tabla de 10 cambios pre-registrada a nombres exactos y
todos los gates en verde. cat010 — el retrieval-miss que A-core dejó atribuido a arquetipo —
entra y sirve sus dos manuales con los valores de alimentación IS en las quotes. El outcome
espera a A3 (lane ON). Acumulado adversarial de la sesión s288+s288b: 34/34 hallazgos
confirmados, 0 falsos positivos.

## s288c (31 jul 2026) — investigación completa de la pieza 3 de etapa 2: la cuota muere ×2 en dúo y el diagnóstico $0 encuentra los bugs reales en las puertas existentes

**Arranque — recuperación de estado**: el cierre s288b NO estaba pusheado (19 commits solo en
`C:\dev\technical_bot`) → push; el brief de cat017 del agente Opus sí llegó (sobrevivió al cierre,
escrito 07:26) y una segunda pasada independiente lo corroboró con regla-C + addenda. PR #189
abierta (51 commits s287→s288b) → CI ROJO por bug Linux-only del instrumento
(`seam_config_assets` hacía stat() de docstrings como rutas; Windows traga winerror 123, Linux
revienta ENAMETOOLONG) → fix quirúrgico 5 líneas → verde → Alberto mergeó. **Corrección honesta
post-merge**: el PR body decía «todo default-off» pero P1 corpus-aware va VIVA sin flag
(incondicional bajo replace del perfil C1) → desplegada en Railway; su re-medición pendiente se
cerró con el mapa re-anclado (abajo). QA-30 v4 reenviado como fichero (el link epitaxy de la
sesión anterior murió con ella).

**Investigación cat017#4 (cuota-por-faceta, GO 31-jul)**:
- Recon ×3 pasadas + dúo r1 (Sol 8 + sub-agente 5 = 13/13 confirmados, 0 FP): fork lane-vecinos
  CERRADO en código (rank_key 5-claves + max_anchors schema 1..4 + cap per-lane 2); cuota v1 no
  build-ready (fork-A circular — el arquetipo `commissioning_setup` se autoró contra el
  chunk-respuesta del gold —, cohorte stale, gate sin aislamiento causal, contrato-93 violado).
- Probe serve-rate judge-free committeado (`scripts/s288c_cat017_serve_rate_probe.py`): 0/6 por
  la ruta harness exacta → MISS-ESTABLE; exclusión SISTEMÁTICA de selección (0/8 acumulado).
- Mapa re-anclado (10 golds P1, N=2): OK estables 22→26 · retrieval 4→0 (hp010#0/#1 convierten;
  hp009#0 baja a síntesis; hp013#1 flippy) · hp018#1/#4 confirmados OK · única regresión estable
  = hp002#4 (clase SEGURIDAD) — P1 concentró su pool (50→32-34) y el singleton cayó a rank 21-23.
  **Etapa 2 en HEAD = {cat017#4, hp002#4}, mismo mecanismo.**
- Re-spec content-keyed sobre need-groups → dúo r2 (Sol 9 + sub-agente 9 = 18/18, 0 FP): NO-GO —
  F1/F2 críticos: la «autoría ciega» estaba contaminada EN LA ORDEN (los descriptores de clase
  eran el gold abstraído; la query de hp002 no tiene vocabulario de mantenimiento) y el predicado
  cobertura-de-grupo ≠ predicado del fallo (la selección de cat017 YA contiene sub-intención-2).
  Regla-C contra mí ×2: bandas de estabilidad sin recibo committeado (scratchpad) + fail-open mal
  atribuido (es el canal vector PRINCIPAL, retriever.py:1638).
- Diagnóstico $0 de las puertas existentes (la respuesta final): AMBOS misses mueren por
  orden/fallback en lanes YA construidas. cat017: `document_local` dispara, `b7633e98` elegible y
  atesta True en contrafactual — muere en `bucket[0]`-único + aborto sin fallback
  (post_rerank_coverage.py:1118/:1377-82). hp002: singleton identificado (`5b6a3a19` p.121 §9.3);
  pasa TODOS los gates de `obligation_warning_reserve` y pierde por selector primer-match-por-pool
  (rerank_pool_coverage.py:535-585; el presupuesto se lo lleva una fila de changelog). Bonus:
  matcher de attestation token-exacto sin stemming (lemas de config vs flexiones reales) →
  TECH_DEBT #59; F7 (grupos existentes para hp002) refutado por medición 0/26.

**Estado al cierre**: NADA cableado (2 diseños muertos en revisión, 0 build desperdiciado); ruta
adjudicada = diseño de los 2 fixes quirúrgicos → dúo r3 → build flag-off → gates (sweep-39;
por-fila sobre `339f06e0`; dirigido pareado ~$2-4) + pieza observabilidad (salud/fail-open por
canal en traza — `_channel` ya se estampa) + recibos committeados de estabilidad de pool.
Hallazgo transversal: pool del reranker VENTANA-DEPENDIENTE (bandas 1/12-14/44 en ~2h).
Dúo acumulado sesión: 31/31 confirmados, 0 FP (tallies completados en el log, r1+r2).
Gasto ≈ $20. Traza: DEC-167 + brief v1 (5 addendas) + re-spec (consolidación r2) +
`s288c_gate_diagnosis_v1.md`.

## s289 (1 ago 2026) — etapa 2 ejecutada: los 2 fixes de orden/fallback, del diseño al gate con dúo ×3

Arranque desde el «Al retomar» de s288c. **Diseño** anclado en el diagnóstico + audit $0 fresco
sobre los 7 competidores reales de hp002 en DB (halló que la exclusión-de-changelog sola era
insuficiente y una clase FP nueva: el marcador-huérfano `> **Peligro**` de 13 chars) + censo de
284 docs. **Dúo r3 pre-build** (Sol xhigh 5 hallazgos [crítico: brazos pareados sobre pools
serializados idénticos] + sub-agente Fable 8 [filtros POR-GRUPO; firma pineada]; GO-con-cambios,
13 resoluciones al spec). **Build flag-off** (`FACET_COMPLEMENT_FALLBACK` +
`OBLIGATION_RESERVE_ORDERED`, DEMO_FLAGS + SAFE_DEFAULTS, byte-invariantes; 16→21 tests nuevos).
**Gates**: captura congelada 39 golds (embedding+rerank fresco, ~$5) → sweep 5-brazos $0 con
réplica-OFF y atribución por flag → G-3 pareado per-fact con el juez del instrumento →
**cat017#4 CONVERTIDA (miss→conveyed-stable, A-only) · 0 regresiones/39 facts**. El orden v1
(blockquote-first) sirvió un callout ajeno en la ventana capturada → **escalada v2
pre-declarada** (sección-con-intención primaria) disparada por dato, trigger preservado.
**r4 focal post-gates** (Sol 6/6): freeze-binding de harness propio, brazos A-only/B-only,
probe de ventana-mala (**hp002#4 miss-stable→flip**: el portador se sirve, el residual es
síntesis), recibo G-2 formal, censo re-declarado. **Observabilidad DEC-167(c)**: fail-open del
canal VECTOR (el único silencioso) con log+traza + `channel_health` en `_trace`. Sol cazó 2× en
la sesión la clase «validado-vs-visible» — el control estructural operando. 0 FP en 3 rondas.
Suite final verde. Coste ≈$9-12. Traza: DEC-168.

## s290 (1 ago 2026, tarde) — foto post-etapa-2, diagnóstico de etapa 3 en fan-out con refutadores, instrumento v3.2

Post-ONs de Alberto (PR #191 + Railway). **Foto** mapa-10 N=2 bajo flags ON: hp002 5/5 OK con
el aviso p.121 apendizado por la reserva (Fix B en la ruta viva); estables cat017#2/cat017#4/
hp009#0/hp013#1, flips hp002#4/hp013#0/hp018#0. **Pregunta de Alberto** («¿atacar los synth
antes del full?») → sí con matiz: solo los estables frescos; full diferido. **Diagnóstico** =
workflow de 4 misiones judge-free + 1 refutador adversarial por misión (8 agentes, 0 errores):
el patrón pagó — los refutadores cazaron 2 anclas falsas ANTES del dúo (la «slot-competition»
era output del anexo determinista, no del modelo; el «único chunk» de la cardinalidad era
falso) y trajeron el hallazgo positivo del 2º carrier (4c186fb2, «dos licencias por módulo»).
**Dúo r1** (Sol 6 [3 críticos] + Fable 7, 0 FP): mi brazo determinista de L2 re-abría el NO-GO
medido MP_SERVED_BINDING (24/105 FP) sin citarlo — 4ª cazada de la sesión a `feedback_my_bias`;
adjudicación = L1 a+b GO (guard c HOLD), L2 hipótesis-con-gate-FP, L3a NO-GO-todavía (probe $0
de lanes existentes primero), L3b re-frame (doc_map YA lo mapea), L3c GO consumiendo doc_map.
**Build v3.2** (un corte de serie): votos por-id del eje servido + dual-rescue en
support_over_served/append (la única asimetría sin red — FN medido en cat017#4) + puente de
familia doc_map (join gobernado doc-a-doc, guard de ambigüedad medido por dato) + pool_ids.
**Gate 3/3 expectativas pre-declaradas**: cat017#4 rerank-miss→OK (los votos por-id muestran
el near-threshold 0/5→2/5→5/5; via_coverage_append vía la lane de Fix A ⇒ **las 2 dianas de
etapa 2 convertidas de verdad**) · cat017#2 sin OK-falso · hp009 centinela intacto con puente
inerte. Suite verde tras actualizar el pin deliberado de versión. Traza: DEC-169.


## s291 (1-2 ago 2026) — el full v3.2: etapas 1-2 completadas corpus-wide; L2 construido con dúo y V1 medido

GO de Alberto al full (~$25). **OK 115/131 (88%)** — retrieval 10→2 (centinela+techo) y
rerank 4→0 desde el mapa canónico: las dos primeras etapas de la campaña quedan hechas a
nivel corpus, y la cascada upstream→downstream que motivó el orden de Alberto quedó MEDIDA
(hp013#1 pasó de retrieval-techo a synth: el carrier ya se sirve y ahora el cuello es el LLM).
Cola de etapa 3 = 9 synth estables. En paralelo, L2 (apéndice determinista del aviso
obligatorio servido — la clase SEGURIDAD hp002#4): diseño v1 → dúo r2 (Sol 8 + Fable 8, 0 FP;
el gate pareado se rediseñó a pareado-de-drafts $0; vector de flags codificado en el contrato
de release; slot propio sin tocar banked) → **V1a/V1b medidos ANTES de construir** (0-átomos
3/20 clase precaución = no-op limpio; dedup dirección letal 0/4) → build default-off + 7 tests
→ suite 3426/0. El ON de L2 queda gateado por G-FP de amplitud con recibo por-fila. Traza:
DEC-170.


## s292 (1-2 ago 2026) — etapa 3 diagnosticada; L3 tumbado por el dúo; tres sondas mías corregidas por regla-C

Tras el ON de L2 (verificado vivo en query real), Alberto pidió atacar la cola de síntesis por
el orden barato. **Fan-out de 18 agentes** (9 diagnósticos judge-free + 9 refutadores) sobre los
9 synth estables del FULL v3.2: **no son 9 problemas, son 4 clases** — 3 levers vivos, 1
gold-split, 1 re-cablear, 2 gold-review, 2 techo. **Signature-check $0** del hallazgo
transversal: ACOTADO a cat017#2 (1/10) ⇒ el «rerank 0» de DEC-170 se sostiene. **hp011#2**
re-cablado: mecanismo confirmado con la orientación INVERTIDA (se sirve el valor, falta el
label, a gap-1 de la misma lane que ya corre). **L3** (gatillo «siempre» en el léxico
MANDATORY): censo mató el gatillo naive (69% FP) antes del dúo; el apretado llegó con números
— y el dúo lo tumbó igual (13/13, 0 FP): `atom_good_form=False` lo haría no-op silencioso y
parchear el léxico compartido explota a la lane L2 VIVA en prod. **Lección de método de la
sesión: tres sondas mías fallaron y las cacé yo antes de reportar** — la del signature-check
era ciega a su propia hipótesis, la de exigibilidad mataba el lever por pasar contexto vacío
(corrección auto-favorable ⇒ marcada para verificación externa), y el marcador del probe de
ventana-mala era markdown-unaware. Una sonda que confirma lo que quiero exige el mismo
escrutinio que un resultado adverso. Alberto adjudicó el **pin del sub-agente a Opus 5** al
agotarse el crédito de Fable. Traza: DEC-171.

## s293 (2 ago 2026) — dos levers cerrados con medición, cero código de producción

Sesión de **cierre por evidencia**: los 2 levers vivos que quedaban en cola de etapa 3
(hp017#2 y cat017#2) quedan resueltos sin cablear una línea. Arrancó con una sorpresa de
infraestructura: el checkout desde el que se trabajaba (dentro de OneDrive) llevaba **muerto
desde el 13 de julio** — HEAD en s107, `main` local 545 commits por detrás y el `.git`
corrompido a nivel de refs por la sincronización entre máquinas (existe una rama
`main-ASGlaptop` que es el `refs/heads/main` del portátil sincronizado como fichero en
conflicto). El trabajo real vive en `C:\dev\technical_bot`; baseline verificado ahí:
**3427 passed / 5 skipped** en `610f137`, y los módulos de coverage/serving/generación
**byte-idénticos** contra `bf2bf8e` (el commit del FULL v3.2) ⇒ las sondas miden el mismo
código que el recibo.

**hp017#2** pasó de «supresión por conflict-guard» a **dos causas**. El mecanismo se confirmó
al píxel: la fuente pone la ruta («menú Editar Configuración») y el valor en conflicto
(«7: Causa y Efecto») en la **misma frase**, a 12 caracteres, y el guard repara **por bloque**
⇒ borra la lista de 3 pasos entera. Tres turnos reales: `surgical_repair` 3/3, ruta presente
antes 3/3 y ausente después 3/3. Y el conflicto es **real e intra-documento** (el mismo manual
dice `7` en la prosa de p.45 y `8:Causa y Efecto` en el árbol de menú de pp.15/26/41): el
criterio del guard es correcto, el defecto es de granularidad. Pero el lever murió por dos
sitios a la vez. **Economía**: el juez canónico K=5 sobre el borrador PRE-guard da 3/5, 1/5 y
2/5 — por debajo del umbral firme de 4 — porque el hecho tiene **dos mitades** y el modelo
nunca escribe la segunda («borrar la Regla 1»: 0/3 con cinco marcadores, paráfrasis
incluidas). **Seguridad**: el peldaño de redacción que yo proponía conservaba la cita del span
mientras el aviso mapea fragmento→valor, así que el validador decía `safe` y el técnico
**reconstruía el número** — el agujero exacto que el guard existe para cerrar, y que hoy no
existe porque esa línea muere entera. Corolario incómodo: mejorar retrieval habría empeorado
ese lever.

**cat017#2** cerró el probe $0 que DEC-169 dejó pre-declarado, con un replay de la etapa de
coverage sobre el pool grabado que **se auto-verifica**: el brazo baseline reproduce los 4
apéndices del recibo en orden y lane antes de creerse ningún contrafactual. Ni
`RERANK_POOL_COVERAGE=on` ni `CANONICAL_HYQ_COVERAGE=on` traen el carrier. Y el porqué es más
fino que «no hay lane»: `facet_complement` **ya detecta** la necesidad «licencia» y la da por
satisfecha con el chunk **puntero** —el que dice «Consulte… 4188-1125-ES»— mientras el dato
vive en el documento referenciado, a rank 18 del pool.

**Método.** El dúo (Sol xhigh + sub-agente Opus 5) devolvió **15 hallazgos, 15 confirmados,
0 falsos positivos**, y no cazó un detalle: cazó **el gate entero** — vara ciega que medía la
mitad del hecho que me convenía, NO-GO sin contraste pareado, circularidad de usar el mismo
validador como filtro y como árbitro, G4 tautológico, y la falta del invariante de integridad
de span que DEC-171 ya exigía. Los dos revisores convergieron además en la misma medición
barata que **mi propia sonda había pre-declarado en su docstring y yo no había ejecutado**.
La lección que queda: *cuando una sonda escribe su propio criterio de refutación, se ejecuta
ANTES de diseñar el gate*. Y regla-C sobre mis sondas **cuatro** veces: un censo con filtro
español y espacio-sensible que habría declarado fantasma un registro real, un replay con el
flag-set copiado a mano que no reproducía el recibo, una sonda que no pasaba `similarity` y
mataba el guard antes de llegar a él, y un marcador ciego a paráfrasis. Traza: DEC-172.

**s293 (cont.) — la criba de alcanzabilidad.** Tras el NO-GO del lever A, Alberto aprobó
generalizar lo que lo había matado: **antes de diseñar, medir si el hecho-diana es alcanzable**
con la evidencia ideal delante (DEC-173, ahora fila del Protocolo 4). Coste ~$1 por hecho.
Resultado sobre los candidatos que quedaban: **`cat017#2` alcanzable** (0/5 → 5/5 en 3/3 al
servir el carrier) y **`hp003#4` alcanzable** (0/5 → 5/5 en 3/3 con el apéndice del span
«Desconecte siempre…»), pero **`hp011#2` NO** — 0/5 → 0/5 en 3/3 con AMBAS mitades inyectadas y
admitidas, sin que la respuesta llegue a mencionar el «295»: el modelo tiene el dato y contesta
con otro parámetro, así que la **pair-completion que s292 iba a diseñar no habría pagado**. Dos
levers confirmados y dos muertos por unos pocos dólares y antes de escribir una línea. La sonda
me falló tres veces más y las tres las cacé antes de reportar: oráculo incompleto (inyectaba
media evidencia), **carrier equivocado heredado del censo de s292** (el documento tiene
`chunk_index` duplicados y el label `t.A` vive en el gemelo que aquel censo no eligió), y un
patrón ciego a «magneto térmico» con espacio que fingía un hueco de corpus donde el span estaba
servido. Traza: DEC-173.

## s294 (2 ago 2026) — L3 v2: el gatillo se limpió, y aun así se para

Sesión de continuación autónoma sobre el único lever de etapa 3 con retorno demostrado y
población medida. Se cumplieron **cinco de las seis** condiciones que el dúo le puso en s292, y
la sexta —la adjudicación ciega— acabó decidiendo en contra dos veces.

El **F1** se cerró antes de diseñar nada: `_sentence_has_finite_verb` devuelve True en las cinco
formas candidatas, así que el átomo pasa la whitelist sin exención y la v1 moría **solo** porque
`_mandatory_triggers` devolvía vacío en sus dos llamadas. El seam por-parámetro dentro de
`must_preserve` bastaba. El **F4/F5/F6** se cerraron con un censo out-of-sample de los 1.552
chunks del corpus que contienen «siempre»/«always», con la lista cerrada de imperativos derivada
de los datos en vez de inventada, y con el inglés dentro por primera vez.

Entonces entró el control que importa. **Adjudicación ciega r1** (cross-model, taxonomía
pre-registrada, la diana metida sin marcar): **12 espurias de 61**, o sea STOP por la regla de
daño. El reparto mandó un **rediseño, no un parche** — 11 de las 12 estaban en la forma B, que
se eliminó entera, y 8 eran spans rotos que mi propio detector no veía, así que el guard se
recalibró al listón del adjudicador. **r2: 1 espuria de 60, 98,3% de precisión**, con la diana
declarada legítima en las dos rondas.

Y aun así, STOP. La regla estaba pre-registrada y la excusa disponible se comprobó en vez de
usarse: `_near_duplicate_span` devuelve False para esa pareja, luego el apéndice emitiría las
dos. Pero lo que decidió de verdad fue otra medición: sobre la superficie real de emisión el
gatillo dispara tres veces en dos chunks del **mismo manual**, y sirve la obligación **en
español y sus dos gemelas en inglés dentro de la misma respuesta**. Cumplir el requisito
bilingüe que exigía el dúo **creó** el problema. Shipear pedía dos cambios en la lane L2 viva
para entregar un hecho, sin justificación independiente: **Alberto eligió parar** y pasar al
lever B de `cat017#2`.

Se llevan dos cosas de valor sin haber tocado producción: **dos defectos latentes de la lane
viva** con causa exacta (el punto ciego de contención del dedup y el hueco de política de
idioma del apéndice), y un censo reproducible por si se retoma. Y tres fallos propios cazados
—paginación sin `ORDER BY` que hacía el censo irreproducible, `\b` escritos como bytes de
retroceso que convertían una exclusión en no-op silencioso, y una contabilidad de rechazos
prematura—, los tres **por verificar el efecto y no el código**. Traza: DEC-174.

**s294 (cont.) — el lever B cae por población, y aparece algo mejor.** Con L3 parado, el
siguiente era el lever B de `cat017#2`. Su mecanismo estaba probado y su retorno también
(0/5→5/5), así que fui al censo que DEC-173 obliga a hacer antes de diseñar — y el censo lo
mató: **1 gold de 39** en el eval y **0,13% del corpus**. Al clasificar las remisiones de 3.000
chunks salió por qué: **329 son internas** al propio documento (no cruzan nada), 343 son vagas,
28 citan manuales que no tenemos y **solo 4** citan uno que sí. Con eso **retiro el argumento
estructural que yo mismo había usado** para recomendarlo. Etapa 3 queda cerrada como cola de
ingeniería: sus tres levers vivos están resueltos y lo que resta es adjudicación de golds y
techo. La regla que queda: **alcanzabilidad y población son ortogonales, y un lever necesita
las dos** — `cat017#2` era alcanzable y a la vez población 1.

Del descarte salió el hallazgo más útil del día: esas remisiones a manuales ausentes son
**peticiones explícitas del propio fabricante**, así que ordenarlas da una **lista de
adquisición dirigida por citas**. Barrido del corpus entero: **44 CANDIDATOS citados y
ausentes, 77 citas**, concentrados en Notifier/Morley series ID50/ID1000 — tenemos el manual de
instalación y falta el de **programación**, justo donde vive el detalle que pregunta un técnico.
Antes de publicarla la corregí dos veces: normalizar guiones (el corpus escribe `MIDT155` donde
el manual cita `MI-DT-155`, y sin eso **160 documentos presentes salían como ausentes**) y
exigir una palabra de documento entre el verbo y el código (el pie de página del propio manual
se colaba como destino). Traza: DEC-175.

## s294 (2 ago 2026) — cuatro levers muertos con recibo, y un canal que empieza a traer señal

Día largo y de forma poco habitual: **casi todo lo que se midió terminó en NO-GO, y eso es el
resultado**, no el fracaso. `hp017#2` y `hp011#2` cayeron por **no ser alcanzables** —ni con la
evidencia perfecta delante el modelo transmite el hecho—; `hp003#4`/L3 v2 se paró **después** de
que el gatillo llegara al 98,3% de precisión en adjudicación ciega, porque shipearlo exigía dos
cambios en una lane viva para ganar un hecho; y el lever B cayó por **población**: alcanzable
(5/5) pero 1 gold de 39 y 0,13% del corpus, lo que desmintió mi propio argumento estructural.
Cero líneas de producción desperdiciadas en los cuatro.

De ese trabajo salieron **dos gates baratos que quedan como procedimiento**: la sonda de
**alcanzabilidad** («¿el techo está en el hecho o en el pipeline?», DEC-173) y su gemela de
**población** («¿cuántos casos hay?», DEC-175). Son ortogonales —`cat017#2` era alcanzable *y*
población 1— y cuestan un dólar frente a un diseño entero con dúo.

La segunda mitad del día fue **fontanería con retorno**: los puntos 1 y 5 del paquete de
telemetría, construidos, desplegados y verificados contra la base real. Un 👎 ya no es una señal
muda: el bot invita a explicar, captura la prosa **por intención explícita** (`ForceReply`, para
que una pregunta posterior no se confunda con feedback — aviso de Alberto que gobernó el diseño)
y la ancla a la consulta, al veredicto y a la evidencia servida. Sin esquema nuevo: el dúo tumbó
mi diseño porque s286 ya había decidido dónde vivía esa prosa y yo no lo grepeé.

Y el día cerró con lo que no estaba en el plan: **el primer fallo orgánico**. Alberto probó el
canal recién hecho, el bot le dio mal la ruta al menú AVANZADO de la CAD-171 teniendo el dato
servido, y al verificarlo contra el manual resultó ser **la misma clase que `hp011#2`**: responder
con el **elemento vecino**. Dos instancias, una de uso real, el mismo día que se abrió el canal.
Eso matiza mi propia propuesta de la mañana: **la población que quería fabricar con una cohorte
empieza a entrar sola** en cuanto hay una persona usando el bot y una forma de contarlo.

**Método.** Cinco fallos propios cazados, **todos probando el efecto y ninguno leyendo el
código**: un `merge-duplicates` que devolvía 403 en cada insert y se tragaba con el fail-open
(ni un ancla jamás, sin un error a la vista); unos `\b` escritos como bytes de retroceso que
convertían una exclusión en no-op —y un primer «arreglo» que sustituía backspace por backspace—;
un `ForceReply(selective=True)` que apuntaba al bot en vez de al técnico; un test de regresión
que grepeaba el fuente y fallaba por su propio comentario; y una variable encendida en Railway
sin el código desplegado. **Lección #59**: citar evidencia **truncada** en un brief induce
críticos falsos — recorté el mensaje de Alberto a 160 caracteres y los dos revisores concluyeron
lo mismo y equivocado. Un revisor solo puede ser tan bueno como la cita que se le pasa.
Traza: DEC-172..176.

---

## s295 (3 ago 2026) — la matriz RGPD, y el duo tumbando mi propia pieza central

**El bloqueo.** s294 cerro con un riesgo declarado y sin cerrar: el bot ahora PIDE prosa al
tecnico tras un 👎, y no habia matriz de retencion.

**La decision.** Alberto fijo 24 meses y `info@fontiber.com`, y pidio asumir los DPA firmados
para no bloquear. Sobre eso, mi decision de diseno: el plazo no termina en `DELETE` sino
retirando el identificador — el valor del historico esta en el contenido (material de eval),
no en quien pregunto, y un plazo que quema el activo se pospone para siempre.

**Y entonces el duo lo tumbo.** Los dos revisores, por separado, cazaron que **el mecanismo no
anonimizaba nada**:

1. **No podia escribir.** `service_role` tiene solo SELECT+INSERT sobre `query_logs` y
   `feedback` — DELIBERADAMENTE (el hardening de julio hizo `REVOKE ALL` con una postcondicion
   que revienta si alguien le da UPDATE). `--aplicar` habria devuelto 403. Lo verifique yo
   contra la DB antes de que llegaran sus informes, con una sonda de filtro imposible; el
   cross-model lo tenia como su primer critico.
2. **Aunque escribiera, no bastaba.** Quitar `query_logs.telegram_user_id` deja la consulta
   re-identificable por sus hijas, que se unen por `query_log_id`:
   `answer_feedback.telegram_user_id NOT NULL` y `answer_messages.telegram_chat_id NOT NULL`
   (== user_id en chat privado). El CASCADE de esas FK solo actua al BORRAR el padre; una
   retencion que ACTUALIZA no dispara nada. Era **seudonimizacion**, y yo la habia llamado
   anonimizacion en el doc, en el codigo y en los terminos que el tecnico acepta.

**Y tres cosas mas que eran mias.** El motivo que yo daba para excluir `answer_feedback` (su
UNIQUE) era **tecnicamente falso** — en Postgres un UNIQUE admite varios NULL; el blocker real
es el NOT NULL, y lo tenia cementado en DECISIONS y impreso en cada ejecucion. Mi claim de que
esto **desbloqueaba el DDL `convo`** era falsa: ese gate exige una matriz DISTINTA
(`RGPD_LIFECYCLE_MATRIX_TEMPLATE.md`, 20 celdas `[DECIDIR]`) firmada con validacion legal — y
yo escribi un doc nuevo sin grepear que la plantilla ya existia. Y mis tres tests nuevos ni
siquiera importaban `sys`.

**Lo que quedo.** La matriz, corregida, con las tres filas que me faltaban: el ID del votante,
el ancla de mensajes y —hallazgo del sub-agente— los **exports a disco** de `review_logs.py`,
que sacan `display_name` + `telegram_user_id` + pregunta + respuesta fuera de Supabase, sin
plazo y fuera del alcance del job. Los terminos v4 corregidos: el audio (se declaraba guardar
el original y no se guarda), Telegram como transporte que retiene por su cuenta, y
«disociado» en lugar de «anonimizado». Un **tripwire de hash** sobre el texto de los terminos,
que cierra el agujero de fondo: los pins de version no impedian editar el texto dejando la
version quieta. El job, que ahora sirve para una cosa util y honesta: **demostrar con recibo
que la retencion no es ejecutable** (exit 2). Y el diseno completo como PROPUESTA sin aplicar,
porque revierte parcialmente una postura de seguridad deliberada — eso es de Alberto.

**Y una ronda 2, que hizo falta.** El sub-agente exigio re-correr el duo sobre el artefacto
reescrito, y tenia razon: la segunda ronda encontro que el job cubria solo la tabla padre (tras
aplicar la migracion habria salido con exit 0 dejando dos identificadores vivos), que sin
barrera una ejecucion podia quedar a medias e irreversible, que el filtro «imposible» de la
sonda no lo era, y que el preflight daba un FALSO OK en `answer_feedback` — tiene UPDATE de
tabla, pero su columna es NOT NULL y un PATCH sobre conjunto vacio no evalua constraints. Ese
ultimo es el mismo fallo de la ronda 1, una capa mas abajo: **la sonda comprobaba el privilegio
y yo lo llamaba «el efecto»**. Se arregla leyendo el `required` que PostgREST publica en su
OpenAPI.

**Dos bugs preexistentes de propina.** `set_consent` decia refrescar `accepted_at` y limpiar
`revoked_at` sin incluir ninguna de las dos en el payload: un usuario revocado que re-aceptaba
quedaba servido en memoria y revocado en la base. Y el `logger.error` metia la pregunta cruda
del tecnico en el log del worker de Railway, fuera de toda gobernanza.

**Y el cierre, que llego por una pregunta de Alberto.** Pregunto que implicaciones tenia la
propuesta. Al desglosarlas aparecio la que decide y que yo no habia puesto delante:
`service_role` **es la identidad del bot**, el worker de Railway encendido 24/7 — concederle
UPDATE/DELETE pagaba superficie permanente de un proceso expuesto a internet por un privilegio
que se ejerce una vez cada varios anos. Alberto aprobo mover el privilegio a un **rol dedicado**
`rgpd_retencion` (NOLOGIN/NOINHERIT/NOBYPASSRLS, `SET LOCAL ROLE` desde conexion de operador),
patron que el repo ya usaba en `p1_readonly`.

Y el cambio de enfoque **disolvio tres parches** de la ronda 2 en vez de mantenerlos: sobre
conexion directa el dry-run ejecuta de verdad y hace ROLLBACK (verifica el EFECTO, no el
privilegio — se acabo el falso OK), las 4 tablas van en UNA transaccion (la ejecucion parcial
deja de existir), y como el rol es NOBYPASSRLS sobre tablas con FORCE RLS, **sus politicas
convierten la ventana de 24 meses en un invariante del motor**: ni un bug ni un `--meses 0`
pueden tocar una fila reciente. Cuando el diseno correcto hace desaparecer los parches en vez de
sumarlos, suele ser senal de que es el correcto.

**Ronda 3, y el golpe que faltaba.** El sub-agente lo dijo sin rodeos: **nada de esto habia
tocado un PostgreSQL**. Los tests corrian sobre una conexion falsa, asi que probaban que se
emiten las sentencias correctas, no que la base haga lo que yo afirmaba — y afirmaba cosas
fuertes. La leccion #60 que esta sesion escribe se incumplia en el mismo commit. La respuesta
fue construir el instrumento: esquema + propuesta ejecutada de verdad + filas vencidas y
recientes, en un contenedor desechable en CI. Ahi se comprueba que el rol NO VE las filas
nuevas, que no puede leer la pregunta ni el comentario, que el trigger corta la
re-vinculacion, y que el rollback declarado funciona de verdad.

Ademas: **Voyage AI no estaba declarado** —cada consulta se embebe con Voyage para buscar en
`chunks_v2`, mientras los terminos decian «no se comparten con nadie mas»— y **la retencion se
podia deshacer sola**: un 👍/👎 en un teclado de hace dos anos re-identificaba la consulta
vencida. Y dos afirmaciones mias que eran falsas: `ALTER ROLE … SET statement_timeout` no se
aplica al `SET ROLE` (el precedente de `p1_readonly` lo documenta, lo tenia delante), y «una
ejecucion a mano no puede tocar una fila reciente» tampoco — `postgres` es owner y BYPASSRLS.

**Ronda 4 — y la leccion mas fina de la sesion.** Alberto pregunto si convenia alargar los
terminos para cubrir el futuro y ahorrarse re-aceptaciones. No: un consentimiento debe ser
especifico, y la churn viene de la BASE JURIDICA elegida, no de la redaccion — que ademas no
estaba declarada en ninguna parte. Se hizo aviso en dos capas (1.803 -> 971 chars + `/privacidad`)
y se declaro la base con su recomendacion.

Y entonces el duo caz **el fallo mas instructivo del dia**: al mover la sustancia a la segunda
capa, **la deje fuera del tripwire de hash**. Es decir: el refactor que reducia friccion abrio un
agujero por el que se podia cambiar un destinatario o un plazo sin que nadie re-aceptara. Regla:
**cuando muevo contenido protegido, el control se mueve con el, o deja de proteger.** Tambien
perdi el alcance de la promesa al resumir («se retira tu identificador» a secas, cuando el
mecanismo solo cubre consultas y valoraciones), y el aviso «completo» no llevaba responsable,
base juridica, retirada del consentimiento ni reclamacion ante la AEPD: los tenia en la matriz
interna, que ningun tecnico lee.

**La leccion (#60).** Un mecanismo de cumplimiento que no puede ejecutarse **aparenta**
cumplimiento, y eso es peor que no tenerlo: el dry-run informaba «0 candidatas» y se leia como
«listo». La unica defensa fue verificar el EFECTO contra la base real, no leer el codigo — la
misma regla transversal de s293-s294, ahora con un caso donde el codigo era correcto y el
sistema no. Y la de siempre: **grepear si el artefacto ya existe antes de escribirlo**.

Traza: DEC-177 · `docs/RGPD_RETENCION.md` ·
`supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql` · TECH_DEBT #60.

---

## s296 (4 ago 2026) — el seudonimo que salva el corpus, y el bonus que obliga a decir la verdad

**Como empezo.** Alberto pidio que le explicara los pendientes de la matriz en lenguaje llano. Al
hacerlo aparecio lo que su pregunta destapaba: le daba miedo perder las consultas de un tecnico
bueno que se fuera. El contenido nunca corrio peligro —el diseno guarda el QUE y tira el QUIEN—,
pero su miedo apuntaba a algo que yo no habia visto: **poner el identificador a NULL destruye la
AGRUPACION**. Doscientas preguntas excelentes sueltas, sin poder saber que son de la misma persona.

**El arreglo, y el regalo.** Un codigo aleatorio estable por persona, en una tabla de
correspondencias. Y resulta que la misma pieza resuelve el otro pendiente: los exports a disco
llevan el codigo desde el primer dia, asi que **el identificador real no sale nunca de la base**.
Un problema menos, no una pieza mas.

**El bonus, y lo que obligo a corregir.** Alberto quiere poder reconocer a quien aporte feedback
valioso. Tecnicamente cabe —durante los 24 meses el identificador sigue ahi—, pero el aviso decia
literalmente *«no se usa para perfilarte ni para decisiones sobre ti»*, y un bonus **ES** una
decision sobre la persona. Habria sido usar los datos contradiciendo lo prometido. v7.

Y hubo que corregirle dos ideas, ambas razonables y ambas equivocadas: que seudonimizar libera del
permiso (no: el dato seudonimizado sigue siendo personal, y lo que manda es la FINALIDAD), y que
podia «dar permisos especiales» a ciertos tecnicos (los permisos los dan ellos; lo que el decide es
el PESO, que no necesita permiso de nadie).

**La pieza de la que estoy mas contento.** `service_role` —la identidad del proceso con el que
habla el tecnico— **pierde** el UPDATE de tabla sobre `answer_feedback`. El dato que sostendria un
incentivo no puede escribirse desde el canal que toca el interesado. Y fijate que el cambio
ENDURECE la seguridad: quita un privilegio para habilitar una funcionalidad.

**Y el aviso que no es legal sino de producto**: pagar por feedback cambia lo que el feedback mide.
Se mediria quien ha entendido como se cobra, no donde falla el bot. De ahi que la marca sea por
CONSECUENCIA (corrigio / gold / corpus / ninguna) y la ponga una persona despues del hecho.

**Dos fallos mas que solo aparecieron ejecutando.** Tercera y cuarta instancia de la leccion #60:
quien no tuviera codigo quedaba FUERA de la retencion en silencio, con el recibo diciendo «0
tocadas»; y el borrado del vinculo NO VEIA las filas recientes —la propia politica de ventana se
las oculta al rol— asi que lo destruia antes de tiempo, lo que habria partido el corpus del tecnico
en dos codigos. Los dos se leen correctos en el SQL. 19/19 en verde tras arreglarlos.

Traza: DEC-178 · `supabase/migration_proposals/20260804120000_s296_seudonimo_y_calidad_v1.sql`.

**s296 — el duo, dos rondas, y seis fallos que el codigo no ensena.** El cross-model caz que
**los exports no agrupaban nada**: el codigo se leia de una columna que solo se rellena al
vencer el plazo, asi que la finalidad que motivo la pieza estaba invertida hasta 2028. El
sub-agente anadi que **el bootstrap deshacia la pieza central** (re-ejecutarlo devolvia al bot
la escritura de la marca que sostendria un bonus), que **el trigger impedia marcar la utilidad
del feedback mas antiguo** —el que ha tenido tiempo de demostrar que sirvio— y que la tabla que
vincula codigo y persona **nacia accesible para los roles anonimos**, con un fixture que no
creaba esos roles y por tanto no podia cazarlo.

Y uno mio, que conviene registrar tal cual: **arregle mal un hallazgo**. Acote el borrado del
vinculo con una ventana sobre la fecha de emision del codigo — que no es la fecha de los datos —
y eso hacia imposible borrar un codigo emitido por el propio job. Lo caz el CI. Al revisarlo, la
preocupacion original era infundada. Regla: **cuando un arreglo exige un criterio que no es el
del problema, el arreglo esta mal planteado**; lo correcto era declarar el caso, no inventar una
cota.

Al cierre: 22/22 contra Postgres real, seis fallos corregidos y tres gaps nuevos declarados sin
resolver.

---

## s297 (5 ago 2026) — el libro que no debia mentir, y las cuatro maneras en que podia

La sentada pequena ("dos gaps y una columna") produjo la densidad de hallazgos mas alta de la
linea RGPD: 15 del duo, 4 criticos, sobre ~300 lineas de delta. Los cuatro criticos comparten
forma: **un mecanismo de evidencia o de garantia que, en cierto camino, hacia lo contrario de
lo que prometia**. La marca "inalcanzable" era insertable (INSERT de tabla cubre toda columna,
tambien las nuevas); el usuario revocado seguia entrando (cache sin TTL); el reintento
"protector" re-materializaba el dato recien suprimido (las copias); y el backfill del libro
--el libro cuya unica razon de ser es no mentir-- duplicaba evidencia si la migracion se
re-ejecutaba, con COMMIT limpio y postcondicion complice (>= en vez de igualdad).

El quinto, del sub-agente, es el mas fino: el fail-open del libro **solo era fail-open para
errores HTTP**. Una excepcion de transporte tras el estado ya commiteado devolvia False, el
bot pedia reintentar un consentimiento ya dado, y el usuario quedaba atascado en la cache de
misses. La leccion: "fail-open" es una propiedad del CAMINO DE ERROR completo, no del caso de
error que uno penso primero.

Y en el LIA, el framing de siempre, cazado otra vez: garantias construidas presentadas como
vigentes, y una afirmacion empirica ("el laboratorio no predijo los fallos organicos") con
n=1 y ese n=1 en contra. Retirada CON la retirada explicada en el propio documento — que el
asesor vea que estuvo y por que se quito.

Al cierre: 9 unitarios + integracion contra Postgres real incluyendo la RE-EJECUCION de la
migracion, el INSERT tramposo ejercido como service_role en las dos tablas, y la coherencia
marca-fecha. Verde a la primera en CI la ronda inicial (la ruta del workflow se anadio ANTES
del primer push — leccion s296 aplicada).

## s299 (5 ago 2026) — el reloj dentro de la base, y el oraculo que llevaba un dia abierto

Alberto cerro la segunda tanda de decisiones RGPD (base juridica = interes legitimo tras
validacion del asesor; exports con seudonimo confirmados; /borrar por correo; scheduler SI;
transferencias las documenta el asistente y las valida el asesor) y la sesion construyo el
lote s299: la pasada de retencion se movio de Python a UNA funcion en la base
(`rgpd_retencion_pasada`, `SET role` en el encabezado + cinturon de `current_user` +
asercion de ventana ARMADA), pg_cron la ejecuta el dia 1 de cada mes sin que ninguna
credencial salga de la base, cada pasada confirmada deja recibo en `rgpd_recibos`
(solo-insercion, ilegible para el bot), y el script queda como driver manual de la misma
funcion — dos implementaciones de una operacion irreversible driftan, asi que ahora hay una.

El duo pago la sesion entera. El sub-agente encontro un hallazgo VIVO EN PRODUCCION: los
default privileges de Supabase conceden EXECUTE sobre toda funcion nueva de `public`, s296
solo revoco PUBLIC, y `rgpd_quedan_identificados` — SECURITY DEFINER, «¿este id tiene
datos?» — llevaba desde el 5-ago ejecutable por la clave anonima via PostgREST RPC.
Verificado contra el catalogo vivo antes de actuar; cerrado con REVOKE nominal + el fixture
de CI reproduciendo el default de FUNCIONES (el CI era ciego a la clase: mi propio REVOKE
solo-PUBLIC habia pasado verde y habria tumbado la migracion en el SQL Editor contra su
propia postcondicion). El cross-model encontro el conceptual: el punto de no retorno no
miraba `answer_messages`, y un ancla reciente de una consulta vencida mantenia la cadena
chat_id → consulta → seudonimo despues de destruir el vinculo — la funcion aprende la
4ª tabla, con test de edades desalineadas. Mas siete hallazgos menores aplicados (membresia
SET de quien programa, origen sin default, recibo por tocadas, celdas stale de la matriz,
Voyage rebajada de «certificada» a «declaracion nominal» — mi framing, otra vez).

La ronda 2 (agentes frescos sobre el delta) dio SOLIDA con 10 menores/medios: la
asercion de ventana subio a exclusividad+predicado (una 2a politica permisiva de debug
la burlaba), la carrera del punto de no retorno quedo DECLARADA (consecuencia = el
corpus-en-dos-codigos ya aceptado en s296) y los recibos re-clasificados como dato
seudonimizado, no evidencia impersonal. Las transferencias quedaron documentadas con fuente y fecha en la matriz (SCCs-en-DPA para
cuatro; DPF solo declarado por el propio proveedor en Voyage/MongoDB; Telegram sin DPA =
responsable propio del transporte, posicion que confirma el asesor). CI contra Postgres
real en verde con la cola entera. Cierre esa misma tarde: Alberto mergeo la PR #210 y
aplico la migracion — verificado contra el catalogo (job mensual ACTIVO, oraculo CERRADO
para los tres roles, recibos blindados) y dry-run exit 0, con 2 vinculos huerfanos del
backfill s296 (sin datos en ninguna tabla) que caeran en la primera pasada real. Primer
recibo esperado: 1-sep. Queda de Alberto: LIA + tabla de transferencias al asesor, y la
vigilancia trimestral del recibo. Traza: DEC-181.

## s300 (6 ago 2026) — los tres frentes de Alberto, auditados antes de asentir

Alberto pidio anadir al plan dashboard, refactoring modular y automatizacion. La sesion
respondio con arqueologia en vez de asentimiento: 20 agentes de barrido + verificacion
adversarial de cada claim fuerte (varias CAYERON: "no hay veredicto previo de refactor" era
falsa, "las vistas no existen en produccion" era falsa, "420 scripts archivables" bailaba
con la definicion). El resultado cambio la forma de los tres: el dashboard ya estaba
construido en un 70% (el gap real: NADIE lee el porque del voto negativo), el refactor no
necesita reescritura sino un DESTINO + fronteras en CI (la acrecion sedimentaba porque nada
lo impedia), y la automatizacion tiene dos joyas (guardas de ingesta: el corpus vive SOLO en
OneDrive y el inventario desde C:\dev produce vacio SIN fallar; gold_store validate no esta
en CI aunque su docstring lo afirma) y dos prematuros declarados.

Cuando Alberto pregunto "¿es BP? la arquitectura podria ser mucho mas modular", la respuesta
honesta fue A MEDIAS: su instinto senalaba el hueco real (faltaba el destino publicado),
pero "mucho mas modular" literal era la trampa (la escala a 30+ fabricantes es por DATOS,
no por codigo). El puente: la arquitectura como INVARIANTE DE CI. Censo de 10 agentes
(grafo AST de 113 modulos, alcanzabilidad, sellos, flags, acoplamientos, seams) → sintesis
→ 3 verificaciones → `tests/test_import_contract.py` (L0): matriz + 6 excepciones exactas
con trinquete + isla de 35 en cuarentena logica + raices prohibidas + importlib vetado.
Nacio verde y el duo lo endurecio: el cross-model cazo que el gate C1 rechaza paths fuera
de scripts/|src/ (los 2 modulos isla que un probe sellado importa quedan ANCLADOS — L2a
mueve 33/35) y que el recolector no veia el harness/ futuro; el sub-agente hizo mutation
testing (9/10 cazadas) y verifico la ISLA exacta con censo independiente. Blueprint en
docs/BLUEPRINT_MODERNIZACION.md; lotes L1-L3 esperan GO por-lote. Traza: DEC-182.

## s301 (6 ago 2026) — el dashboard resulto ser abrir grifos, y el aviso mando

El frente 6 se construyo como se habia auditado: sin app. Export del voto negativo CON su
porque (la prosa del ForceReply de s294 por fin sale del SQL manual), columna route con
log de los shortcuts de consulta y de los dos clarify que respondian sin dejar rastro,
cinco vistas agregadas (las 2 de salud por fin versionadas + feedback/motivos/uso), Gold
gate en CI, guardas de ingesta contra el manifiesto-vacio, y el camino de escritura de la
marca de utilidad que no existia. Todo S, cero infra nueva, DEC-162f intacto.

La leccion de la sesion la puso el duo. El cross-model cazo un CRITICO de CONTRATO: el
aviso v7 promete literalmente que los saludos y despedidas no se registran — y mis ramas
nuevas los registraban. La observabilidad tambien es tratamiento: se revirtio la cortesia
y quedo la regla (DEC-183) de contrastar toda metrica nueva contra el aviso ANTES de
cablearla. El sub-agente convirtio un hallazgo especulativo en real verificando contra el
catalogo vivo: la migracion de rag_trace de JULIO nunca se aplico — el bot llevaba
semanas logueando sin traza por su fallback silencioso — y el caso ambas-columnas-
ausentes habria perdido log y teclado de feedback en cada consulta durante la ventana de
deploy; el fallback es ahora componible por columna nombrada y ESTRICTO (el laxo se comia
la ruta ante una violacion del CHECK: el patron de la casa, otra vez). 12 hallazgos, 0
falsos positivos. Queda de Alberto: aplicar las DOS migraciones (julio + s301) en una
sentada y montar el dashboard de Supabase sobre las vistas. Traza: DEC-183.


## s302 (6 ago 2026) — el packet que desmonto mi propio frente de trabajo

Toco adjudicar los 44 "documentos citados y ausentes" que el PLAN arrastraba desde s294 como
frente de adquisicion. Ocho agentes, uno a uno, contra el corpus real. Resultado: **7 huecos
reales de 44**. Dieciocho ya estaban ingestados con OTRO nombre de fichero — incluido el
numero 1 del ranking con 11 citas, que resulto ser un PDF que ya teniamos —, diez eran
referencias de PIEZA o rangos de direcciones de lazo, cinco erratas de imprenta y pies de
pagina. El barrido casaba el codigo citado contra el NOMBRE del fichero, y Honeywell imprime
el codigo solo en la portada.

Y el caso que duele: la "Guia Avanzada de Configuracion de la CAD-171", que yo habia puesto
en cabeza del packet como el documento del primer fallo organico del bot, YA LA TENEMOS. Es
el MC-380 rev c ("Adaptacion para CAD-171"), ingestado y mapeado a detnov:cad-171, y su
seccion 5.4 documenta exactamente la ruta AJUSTES > AVANZADO que el bot fallo. El fallo era
100% de seleccion: DEC-176 sale reforzado y no se arregla comprando nada. Cuarta vez de la
clase feedback_corpus_gap — pero con forma nueva: no sobre-atribuyo un instrumento, sino que
yo eleve la salida CRUDA de un probe (rotulada "candidatos, NO confirmados" en su propio
JSON) a frente del PLAN, y la mantuve tres sesiones sin adjudicar. Regla nueva: la salida de
un probe no entra al PLAN como hecho hasta adjudicarse.

Lo accionable que queda es pequeno y bueno: tres documentos con valor real (997-340-005
programacion por PC de la ID1000; 997-415, seis citas y dos marcas; y 997-412, que el
barrido PERDIO por un break en citas dobles — el bug que lo hace no-fiable para negar,
TECH_DEBT #62). Y un hallazgo operativo util: en notifier.es y morley-ias.es los PDF estan
abiertos y lo que esta cerrado es el INDICE. Traza: DEC-184 + evals/s302_adquisicion_packet_v1.md.

## s303-s306 (7 ago 2026) — Tres hipótesis mías cayeron por verificación; lo que quedó en pie es mejor que lo que proponían

El arco empezó con la sonda del fallo orgánico y terminó con dos deudas estructurales
resueltas. Por el camino, el sistema de control (dúo + suite + testigos) me corrigió tres
veces, y esa es la historia real de la sesión.

**El caso CAD-171, cerrado en firme.** La sonda s303 ya decía SÍNTESIS (§5.4 servido en
rango 1). La pregunta de Alberto («¿ese catálogo estaba asociado a la CAD-171?») me llevó a
una hipótesis mejor-sonante: la identidad adjudicada muere en la frontera catálogo→chunk
(57% del corpus). El dúo la demolió con tres hechos que verifiqué antes de aceptar: mi
instrumento paginaba sin ORDER BY (12-21% de docs perdidos POR PASADA — cifras retiradas),
medía etiqueta cuando la pregunta es alcanzabilidad, y la identidad SÍ llega (seam 2 +
series_registry — la serie Vesta con el MC-380 declarada desde s63). Instrumento v2:
residual 4,1%, casi todo `unresolved:`. Veredicto final: **selección de sección dentro del
documento correcto** — el bot respondió DESDE el MC-380 (la ruta que dio está en su p.20),
así que ni siquiera la etiqueta CAD-250 lo frenó. DEC-185.

**El techo, medido con 3 generadores (s305).** Oráculo de DEC-173 tal cual, única variable
el modelo: Sonnet 4.6 / Sonnet 5 / Opus 5 → 0/3 firmes los tres, máx 2/5, 9 respuestas con
hash distinto. El techo NO es del modelo. Los tres responden el DEFAULT del parámetro en
vez del RANGO que pide el gold → ítem nuevo para la sentada B2 (alcance de gold, no
ingeniería). Controles que pagaron: el testigo del efecto (mi 1ª aserción era demasiado
estricta), y la guarda que impide contar un brazo ABORTADO como 0/5 (el primer smoke
proclamaba «techo confirmado» con 2 brazos muertos por API). Colateral: #64 — el generador
no se podía cambiar de modelo (temperature + ThinkingBlock); resuelto con rechazo aprendido
en runtime y extracción por tipo; mi 1ª versión rompió 29 tests por ser MÁS estricta que el
código histórico (claim de equivalencia sin verificar). PR #215 mergeada. DEC-186.

**#63 resuelto (s306, PR #216).** El fail-open de canal (500 → pool 34→23 en silencio)
registra ahora en el seam s289 extendido a los 4 canales; reintento único ante 5xx; sección
`retrieval` TRI-ESTADO en rag_trace — el dúo convergió desde ambos lados en que mi v1
colapsaba «sin seam» a «sano», el defecto reintroducido una capa arriba — + vista
`salud_canal_retrieval_v1` + test-ancla del seam en producción. Dúo 8/8 confirmados, 0 FP.
Suite 3591. DEC-187.

**Patrón de la sesión (va a feedback_my_bias)**: mis diseños razonables, mis claims sobre
ellos en exceso — «la identidad no llega», «equivalencia byte a byte», «sin medida ≠ sano» —
y las tres veces lo cazó una verificación externa, no mi criterio. El control estructural
funciona; el sesgo persiste; la conclusión operativa es no firmar ninguna propiedad de
diseño sin el test o el testigo que la ancle.

## s307 (7 ago 2026, tarde-noche) — El bot deja de hablar de su corpus de memoria; la telemetría s306 estrena filas; y el dúo me tumba la v1 con 4 críticos

Alberto probó el bot recién desplegado y cazó DOS fallos orgánicos en una tarde, ambos de
la misma raíz: la intro decía «Notifier, Morley y Detnov» (30 fabricantes reales) y «¿qué
productos de Securiton tienes?» cayó al RAG — que presentó su ventana de 10 chunks como
inventario, sin los dos ASD grandes. Sus turnos fueron además las PRIMERAS filas con
`measured=true`: la telemetría s306 funcionando en producción el mismo día de su merge.

El lote (PR #218): textos derivados de datos vivos (con el texto legal intacto y pinneado
por hash) + ruta de inventario por fabricante (cruce por document_id, acotada, estrecha,
fail-open, 30 marcas). El dúo dio NO-GO a mi v1 con 4 críticos medidos — incluido mi
patrón: verifiqué «completo por construcción» en n=1 confirmatorio mientras 6 marcas
devolvían vacío; y Sol cazó en mi «fix» de paginación el corte silencioso tras la primera
página (cap PostgREST). 13/13 confirmados, 0 FP, todo aplicado, sweep final 30/30.

También: el 👎 de Alberto capturó reason_class pero su prosa llegó como consulta nueva
(#66, primer dato del punto 5); y documents.product_model resultó estar stale post-H0
(#65). El packet B2 quedó en 10 ítems (PR #217 mergeada). DEC-188.

## s311-s313 (8 ago 2026, tarde) — L2b y L2c cierran; el blueprint a un lote; y el dúo corta en las DOS direcciones

L2b (registro de flags): el censo pasó de v3 a v5.1 a golpe de hallazgo — el pin fantasma
destapó las vías indirectas, Sol las comillas simples y las flags-en-bucle, el sub-agente
la tercera tupla y la CIRCULARIDAD (el test escaneaba con los mismos patrones ciegos del
generador). 91 flags, 2 divergencias reales declaradas, un fantasma documentado
(DIVERSIFY_TIEBREAK, lever s97 nunca mergeado), y el pin por AST que mató la clase entera
de contaminación de entorno (2 bugs cazados por el camino).

L2c (split del doble-inquilino): delegado con spec cerrada, verificado pieza a pieza,
byte-identidad AST×3. El FP central de Sol refutado con recibo — sexta ronda del dúo del
arco y primera donde la regla C corta hacia el revisor. Los dos lotes L2 engranaron el
mismo día (el registro cazó al split moviendo lectores). E3c retirada; el contrato encoge
por tercera vez en la semana (6→5→4 excepciones).

También: packet B2 v3 mergeado (sentada de Alberto desbloqueada), el misterio del CI
resuelto (conflicto de tally, no cuota — `merge=union` lo extingue), y Opus 5 + backfill
confirmados en producción con recibos de Alberto. DEC-190.

> - **RESULTADO s314 (8-9 ago 2026 — DEC-191/192): L3 NO-GO por medición (blueprint CERRADO 4✓/2 NO-GO medidos) + `ingest_new.py` estrenado con el lote Casmar/Kidde + el gap orgánico del NC-PF2 re-clasificado a FINDABILITY.** L3: el pre-flight DEC-189 apuntado a `embed.py` halló 4 pins vivos en preregs s117 (sha coincidente) → se ancla y declara (PR #226). Casmar: harvest reproducible (94 SKUs, 266 PDFs, form_id obligatorio) → cruce (SKU,tipo) → 104 gaps → descarga+dedup (75 nuevos de 104; 29 dups PIM) → dúo (11/11 confirmados, 0 FP; reanudabilidad + lote-en-scratchpad + doc_type cazados ANTES de gastar) → etapa 1 (NC-PFx, 4 docs; la reanudabilidad se estrenó a la primera) → sonda 0/5 → **descubrimiento: el manual YA estaba (bcn-3100017, pm=`NC` invisible para «NC-PF2»)** → fix de identidad pm=lista-con-barras (nuevos + bcn + 5 hojas de familia + 2 docs KIT 2X-AT byte-idénticos) → sonda 5/5 → re-diagnóstico de falsos-gaps (1 near-dup XIP retirado) → etapa 2 (70 docs, 943 chunks, 0 fallos) → re-cruce final **104→1 residual declarado (KE-ASA-AUXR: no existe doc propio)**. Corpus: 26.215 chunks · 1.243 documents · Kidde 103 · Excel reconciliado (`update_inventario --data-root`). ~$60 LlamaParse. Ramas `claude/s314-l3-nogo` (mergeada) y `claude/s314-casmar-ingest`.

## s315 (9 ago 2026) — Los puntos de Alberto: latencia INSTRUMENTADA, links a manuales, barrido pm-de-familia APLICADO (49 docs), y el gap de los canales derivados

Sesión lanzada por Alberto con su lista de puntos (automode). Tres frentes ejecutados
end-to-end + dos hallazgos.

**Punto 1 (rapidez, prioridad 2).** Medido primero: p50 34,5s / p95 57,6s (n=52, 60 días) y
CERO atribución por etapa — `rag_trace` no llevaba timings. Construido: `stage_timings` en
`execute_rag_turn` (retrieve/rerank/coverage/generate) → sección `timings` REQUERIDA
tri-estado del trace (patrón s306; measured exige 4 etapas int — un mapping roto no se
disfraza de medida) → vista `salud_latencia_etapas_v1` (casts guardados por jsonb_typeof,
totales de la MISMA población que las etapas). Migración APLICADA vía MCP. El plan de ataque
se decide con ~1 semana de datos; candidatos ya documentados (cap-rerank-~30, retrieve=30,
keep-alive del typing — expira a ~5s y el turno dura 34).

**Punto 6 (links).** `documents.source_url` + backfill por sha256 desde el manifiesto Casmar
(76/1.243, recibo) + leyenda de fuentes con `URL#page=N` tras `SOURCE_LEGEND_LINKS` (estricto,
default off = byte-idéntico). El dúo (sub-agente Opus, SÓLIDO-CON-CAMBIOS, 12 hallazgos 0
críticos) convirtió el diseño: la URL viaja en el chunk enriquecido por el fetch batched de
documents del retriever — cero round-trips nuevos, cero bloqueo del event loop. Los 12
hallazgos aplicados (timings propagados por TurnResult; vista robusta a filas malformadas;
recibo del backfill post-apply; e2e del handler en tests). Smoke real: línea con
`#page=3` de un manual Casmar vivo.

**Barrido pm-de-familia (la semilla s314 — 4ª instancia findability, ejecutada a escala).**
Censo SQL corpus-wide (variantes atestadas en el PROPIO contenido del doc, ≥3 menciones,
filtro imatch-mismatch con el patrón exacto del retriever) → 525 filas brutas → filtro de
forma → adjudicación con extractos (agente 1: 49 docs / 104 variantes SUJETO, 0
compatibilidad) → refutación independiente (workflow 3 agentes: 101/104 confirmadas, 0
refutadas; 5 verificadas directas por mismatch de nombre) → invariantes deterministas
104/104 (cada variante matchea el pm nuevo, ninguna matcheaba el viejo) → **APLICADO a
producción (chunks_v2 + documents, 2 tandas guardadas por pm=antes) → verificación 49/49 en
ambas tablas + sonda imatch server-side 6/6**. Recibo: `evals/s315_family_pm_patch_v1.json`.
Familias rescatadas: LDM-32/E32/R32, MPS15/25/50, DX1E/2E/4E, XP (XPP-1/XPC-8/XPM-8…),
FSL100-*, códigos de pedido VESDA-E, TG-* (pasarelas = producto propio, no compat), Pearl
PRL-D-1/2, ICAM IFT/IAS/ILS…

**Hallazgo de Alberto (pregunta a media sesión) = TECH_DEBT #68**: el lote s314 (1.091
chunks) tiene 0 enunciados y 0 hyq — `ingest_new.py` no corre los generadores de los canales
derivados vivos en prod. Todo doc nuevo es hoy «corpus de segunda clase» para esos canales.
Trigger: antes del siguiente lote.

**Bloqueos del entorno (declarados)**: push a GitHub imposible (la App no puede crear refs —
`403 Resource not accessible by integration` — y el git local no tiene credencial de
escritura; 3 commits locales en `claude/chatbot-pending-items-amutbm` esperando permiso);
casmarglobal.com bloqueado por egress → el recon Aritech/Edwards quedó preparado
(`scripts/s315_casmar_recon.py`) con la evidencia offline: 2X=Aritech-OEM ya en corpus,
Edwards sin rastro en Casmar (fuente conocida: firesecurityproducts.com). Sol no ejecutable
(sin OPENAI key) — dúo declarado con gap; sub-agente Opus + refutadores + verificación
determinista como compensación. Puntos 4 (página cómo-utilizar) y 5 (fotos: sonda de
alcanzabilidad con fotos reales ANTES de diseñar) quedan en cola con diseño anotado.
DEC-193.

## s315b (9 ago 2026, noche) — El dúo corta el build del #68 (NO-SÓLIDO, 13 hallazgos aplicados) y los timings vivos señalan a retrieval

La fase de derivados por lote se construyó reusando lo canónico y el sub-agente Opus la
tumbó ANTES del run: el append de hyq inutilizaba el loader global (su --wipe habría
borrado el lote — CRÍTICO → contrato de prefijos hyq-v1-*/hyq-lote-*), E2 abortaba el
lote entero por un doc sin filas, el resume del loader A3 estaba roto por paginación
(el mismo bug que s102 ya había arreglado en su gemelo), y la verificación fallaba en
resumes parciales. Los 13 aplicados; suite verde; run del lote Casmar pendiente en local.
DEC-194.

Además, Alberto usando el bot cazó en una tarde: `<br/>` literales en el apéndice
must_preserve (fix v7 de presentación, clase blockquote), el «Reply to…» del feedback
reviviendo tras el «Anotado» (ReplyKeyboardRemove no desarma ForceReply → ahora la
invitación se borra al capturar, con guarda estricta), el carry-forward ignorando su
«pasemos a Morley» (#70, diagnóstico en query_logs: catalog_shortcut no toca el contexto)
y un disclaimer legal citado como obligación de evidencia (#71, aparato protegido). Y los
timings estrenados en producción dieron la primera atribución real: retrieve 11-27s por
turno — el 40-45% de la latencia que nadie tenía en el radar.

## s316 (10 ago 2026) — Retomar contra una sesión cloud: el dúo corta el run, y dos métodos que daban falsos negativos

Alberto pidió retomar con cuidado porque la sesión anterior corrió en cloud. La
reconciliación no encontró conflictos de código (local iba 5 commits por detrás, FF
limpio) pero sí **dos agujeros de gobernanza**: s315c no existía en ningún doc canónico, y
el hook que inyecta el digest de levers (DEC-072) llevaba caído quién sabe cuánto — el
control anti-recall no se estaba ejecutando. Se reconstruyó y se VERSIONÓ, que era el gap
que el propio DEC-072 había declarado y que se materializó.

**El dúo hizo su trabajo, y dolió.** El run del lote Casmar (#68) estaba a un `--aplicar`
de escribir en producción con el dúo declarado a medias (Sol no era ejecutable en cloud).
En local sí lo era. Sol devolvió 3 críticos, todos de la misma clase: **el pipeline podía
estampar recibo ✅ habiendo cubierto una fracción del lote**. Se corrigieron; la segunda
ronda (Sol + sub-agente Opus 5) devolvió **NO-SÓLIDO** sobre los propios fixes, y la pieza
central —cambiar el dedup hyq a keep-FIRST por documento— resultó ser **un no-op**:
`parse_questions` ya deduplica global por texto, y un test del repo fija como contrato lo
contrario de lo que yo había afirmado. Alberto adjudicó revertir. El dedup queda como
lever ABIERTO sin medir, que es lo honesto: no es un fix, es un lever con coste (toca el
techo `LIMIT 200` del RPC global, donde el filtro de familia corre DESPUÉS del truncado).
Lo que sí quedó: fail-closed real, comprobación de fuga `source_file`, congelado de
selección, y 8 tests — la crítica de que los fixes anteriores no traían ninguno era justa.

**Dos métodos daban falsos negativos, y los dos se cazaron con controles.** El script de
subida a Storage pedía `limit=10000` contra el cap de 1.000 de PostgREST: 243 documentos
invisibles, y el `--aplicar` los habría saltado sin poblar su link. Y el barrido Casmar de
s314 ya no funciona —`filters[sku]` dejó de filtrar— lo que hacía que un barrido de huecos
devolviera «0» con toda naturalidad; se destapó corriendo **NC-PF2 como control positivo**
antes de dar el resultado por bueno. El método real (los documentos viven en el `onclick`
de la ficha, con un `attributeCode` que separa homologaciones de forma autoritativa) se
descubrió con el navegador y quedó cableado.

**Y una pregunta mal respondida.** Adjudiqué el frente Aritech/Edwards concluyendo que
«AS250 es el único hueco real» — y Alberto corrigió el encuadre: no quiere productos
nuevos, quiere **los manuales que faltan de los equipos que ya están**. Con la pregunta
correcta y el método corregido: 19 candidatos Aritech, 0 Edwards. El criterio quedó en
memoria para no repetir el error. DEC-195/195b/196.

## s316b (10 ago 2026) — Tres rondas de dúo para descubrir que el fix imaginado era un no-op, y el instrumento que faltaba

Alberto priorizó #70 (el bot respondió Kidde después de que él pidiera «pasemos a
productos Morley» — fallo orgánico, de uso real). Dos diseños de fix murieron en el dúo
la misma tarde, y la autopsia es la parte valiosa: **ambos habrían pasado sus tests sin
arreglar nada**. El v1 limpiaba `last_detected_models` — y Sol cazó que esa clave está
MUERTA: F1 corre en producción (`CONVERSATION_POLICY=impl`, verificado contra la API de
Railway; mi inferencia por la traza era inválida porque la traza nunca emite política).
El v2 prometía cubrir el fall-through con una heurística que, ejecutada, devuelve False
para ese caso, y medirse con un harness que jamás toca `handle_message`.

La lección estructural la dieron los dos revisores convergiendo: **el unit del riesgo es
la rama terminal, no la ruta de log** (7 de los 13 `return` de `handle_message` responden
sin registrar nada), y lo que faltaba no era el fix sino **la forma de VER el fallo**.
Alberto adjudicó instrumento-primero, y la prescripción conjunta del dúo se construyó tal
cual: un harness de transporte que conduce `handle_message` real con dobles $0 — el
testigo del fallo orgánico (verbatim de query_logs) en `xfail(strict=True)`, un control
causal que prueba que el rojo es el bug y no el doble, el control de compatibilidad con
marca SERVIDA (el de Hochiki era vacuo: la ruta lo corta antes de llegar a la política), y
un censo AST de ramas terminales que obliga a decidir qué hace con el estado cada rama
nueva. Primer run: 3 passed, 1 xfailed — #70 es demostrable por primera vez, y el día que
el fix aterrice el XPASS estricto obligará a retirar el marcador.

De la misma jornada: el sha-dedup de Casmar (19 candidatos → 10 nuevos de verdad; 7 ya
estaban en corpus con OTRO nombre, byte-idénticos; Alberto acota a los 2 manuales de
instalación y descarta las hojas de datos), y la verificación de que los fixes de
`<br/>`/ForceReply están DESPLEGADOS desde las 22:45Z del 9-ago — las capturas de Alberto
eran de 30-50 minutos antes del deploy — aunque sin ejercitar aún (0 consultas
posteriores). TECH_DEBT #70 re-escrito con el mecanismo real y las restricciones pagadas;
DEC-197.

## s316c (10 ago 2026, madrugada) — Dos deudas grandes cerradas, y una clase de defecto que estaba en tres sitios

Alberto se fue a dormir con la red inestable y el encargo de retomar solo. Los dos trabajos
largos —los canales derivados del lote y la subida del corpus a Storage— acabaron cerrados,
pero el camino fue más instructivo que el destino.

**#68 y #69 cerrados.** El lote que en s314 entró como «corpus de segunda clase» ya tiene
sus dos canales (10.161 enunciados, 2.516 hyq) y el corpus tiene link: 1.084 de 1.243
documentos, con los 159 restantes explicados uno a uno —son los de sha placeholder, que por
construcción no pueden casarse por contenido—. Ese «cero documentos con sha real quedaron
fuera» se comprobó con una consulta que separa los dos casos, no se dedujo.

**Lo que de verdad costó fue la red.** Tres scripts distintos murieron por la MISMA causa: una
excepción de transporte sin capturar. Todos tenían bisección o manejo para códigos de estado
HTTP; ninguno para una conexión cortada, que es un fallo de otra naturaleza —uno devuelve
respuesta, el otro no llega a haberla—. El peor caso fue la subida a Storage: murió en el
primer fichero y dejó 0 de 1.008. El más caro, E2: tumbó la carga DESPUÉS de generar los
10.161 enunciados, con los $18,67 ya gastados.

Los parcheé de uno en uno según reventaban, que es tapar y no arreglar; queda como
TECH_DEBT #72 con el matiz que impide hacerlo mecánicamente: la idempotencia que hace seguro
reintentar no es universal. Pero sí hubo un arreglo de fondo dentro de su script: cuando el
backoff no bastó, en vez de subirlo a ciegas se hizo que **bisecte el lote ante fallo de
transporte**. Un envío de 500 filas con embedding ronda los 10 MB, y cuanta más superficie
más fácil que la red lo corte; partiendo, el envío se adapta a lo que la conexión aguante.
Con eso, la carga que había fallado cuatro veces pasó a la primera. DEC-199.

## s316d (11 ago 2026) — El rediseño sobrevive al dúo (la arquitectura; los contratos, a la tercera), y el barrido de manuales termina honestamente en cero

La pregunta de Alberto —«¿no hay una vía más elegante tipo LLM?»— destapó lo que los
parches no decían: tres mecanismos tocando el estado conversacional y la mitad de los
turnos sin pasar por la política. El rediseño (plan puro con contrato de hechos, un solo
escritor, F1 intacta debajo) pasó dos rondas de dúo: la primera tumbó las dos claims de
carga (pureza que no sobrevivía al I/O; rollback que leía un estado sin escritor), la
segunda declaró la arquitectura sostenida y redujo el bite a contratos — el
enmascaramiento de la guardia en fase A lo encontraron los dos revisores por separado.
El v3 queda vigente a la espera del GO. Fable 5 volvió como sub-agente (pin restaurado
por Alberto) y rindió.

Y el punto 4 se cerró en cero, que es el cierre correcto: los «10 manuales nuevos» del
barrido Casmar quedaron en NINGUNO al comparar la revisión de portada — dos eran
ediciones antiguas de manuales ya ingestados. El sha prueba bytes, no información. La
lección quedó como puerta automática diseñada (#73) y como memoria. DEC-200.


## s316e (11 ago 2026) — La fase A aterriza con la equivalencia medida, no prometida

El GO de Alberto abrió el build del rediseño y el método pagó: los tests de equivalencia
se escribieron ANTES de tocar nada y salieron verdes contra el código viejo — la conducta
quedó fijada como espec, y el refactor tuvo que caber en ella. El punto de decisión único
(`turn_plan`) absorbió la cascada entera; `handle_message` quedó en pre-pasos declarados,
una llamada al plan y un despachador que no examina texto.

El dúo de build dejó la vara alta: Fable dio el primer SÓLIDO de la sesión y no lo dio
gratis — montó su propia batería diferencial de 32 casos contra HEAD en un worktree (cero
divergencias), verificó el predicado perezoso en 72 combinaciones y aun así encontró la
versión fase-A de la lección FUEGO: un sobre-fetch en el camino más caliente que añadía
superficie de fallo de red a turnos que jamás la habían tenido. Sol, por su lado, cazó que
dos campos del plan eran decorativos y que un test declarado en un docstring no existía.
Todo aplicado; el test de mecanicidad mordió dos veces mientras nacía, que es la mejor
señal de que no es de pelusa. Suite final: 3.720 en verde. La fase B queda pendiente con
su checklist afilado. DEC-201.


## s316f (11 ago 2026, tarde) — La fase B cierra el rediseño, y el crítico de la ronda fue contra el testigo, no contra el código

La fase B retiró lo que la fase A había dejado andamiado: fuera la guardia de grupo −1,
fuera las claves legacy, un solo estado conversacional con un solo escritor y el rollback
de CONVERSATION_POLICY conservando el carry-forward — el escenario que en la ronda 6 del
diseño estaba roto en silencio.

Lo notable de la ronda 9 es dónde mordió: Fable ejecutó el control de vacuidad de mi
testigo e2e y demostró que daba verde SIN carry — «tensión» no está en PCI_TERMS, así que
la consulta vaga iba a RAG con o sin contexto. El código era correcto (lo verificó
espiando build_turn_request); el testigo no. Es la misma lección del instrumento de
transporte, en espejo: un test que no puede fallar no es una garantía, y la única forma
de saberlo es intentar que falle. Sol, por su lado, destapó que el anclaje del feedback
tras un clarify llevaba tiempo siendo incoherente — texto nuevo con FK vieja — y eso
salió de defender una divergencia del diseño con un rationale que resultó falso: la
corrección acabó siendo mejor que lo que el diseño pedía. DEC-202.


## s316g (11 ago 2026) — El lever LLM: un gate que corta, una adjudicación limpia, y la ronda que salvó la paridad

El lever de intención llegó a su gate pre-registrado y el gate hizo su trabajo dos veces.
Primero cortó a Haiku con un fallo claro (una compatibilidad legítima en inglés juzgada
switch, 3/3 estable). Luego dejó a Sonnet a una etiqueta del GO — y esa etiqueta era el
caso límite deliberado de la cohorte, con dos modelos discrepando 6/6 de la etiqueta del
autor. La adjudicación fue de Alberto, sobre el mérito del caso y no sobre el resultado
del gate; con ella, Sonnet quedó 40/40 y el gate se RE-CORRIÓ con el cliente servido y
freeze de hashes para que el recibo lo genere el runner, no una re-puntuación a mano.

La ronda 11 del dúo pagó su precio otra vez: Sol demostró que la exención de misma-marca
se tragaba el caso mixto de la propia cohorte — el gate había medido un camino que el
serving se saltaba, la clase de divergencia medido↔servido más peligrosa que hay — y
Fable probó ejecutando que el único fabricante con guion rompía la exención, que el
serving pagaba una cola de reintentos que el gate jamás midió, y que un flag ON mal
configurado fallaba en silencio. Todo aplicado y re-verificado; el gate MT quedó
re-congelado en 52/52 con la aserción anti-verde-vacuo mordiendo de verdad.

El flip queda bloqueado por dos gates declarados (observabilidad en rag_trace + e2e del
camino servido). El fall-through de #70 — la causa (2) que abrió todo esto hace tres
días — tiene por fin su mecanismo medido esperando el interruptor. DEC-203/203b.

## s316h (11 ago 2026, noche) — Los dos gates del flip, cerrados

PR #237 mergeada por la mañana; Alberto: «sigue a por los dos gates del flip». Gate 1:
la decisión del clasificador deja de vivir en un logger.info — sección `intent` en el
esquema cerrado de rag_trace, con el patrón de la casa (enums cerrados, coherencia
builder+validador, trinquete de clave requerida) y dos mejoras que el log no tenía:
captura POR TURNO (la lectura de `fn.ultima` era estado de proceso compartido — carrera
entre turnos concurrentes) y `not_wired` ≠ `off` (telemetría sin cablear jamás se
disfraza de lever apagado). El seam del lever se extrajo del handler (`_intent_seam`)
para que el gate 2 no fuera un símil: el e2e ejecuta EL código servido — frío, caliente,
timeout, key mala, construcción rota — y PASA 6/6 con recibo y proveniencia.

El dúo r12 fue el de los espejos: Sol demostró que el e2e NO conducía handle_message
(la misma clase de agujero que el propio e2e presumía de cerrar) → el pegamento
flag→seam→política→traza→log quedó gateado EN CI dentro del instrumento de transporte,
que existía justo para esto. Y los dos revisores, por separado, cazaron que mi prosa
citaba las latencias de la corrida FAIL previa en vez de las del recibo adjunto — el
fix estructural fue dejar de duplicar cifras, no corregirlas. Once hallazgos entre los
dos, cero contradicciones, cero falsos positivos, todo aplicado. DEC-204, TECH_DEBT #74.

El flip es ahora, por primera vez desde que #70 abrió este arco hace tres días, una
decisión de UNA variable en Railway — con la traza lista para medir lo que pase después.

## s317 (12 ago 2026) — La puerta de revisión, y el perfil que unió dos deudas

Alberto redirigió la sesión: sin técnicos usando el bot, el censo del pulgar-abajo no
tiene señal que censar — foco en arquitectura y flujos. Dos frentes en paralelo.

Uno: #73 construido y cerrado. La puerta de revisión de la ingesta nació de los dos
sustos reales de s316d (dos «nuevos» que eran revisiones viejas) y se diseñó con las
familias de señal MUESTREADAS del corpus, no inventadas. El dúo r13 la hizo mejor en
todo lo que importa: Sol cazó que era ciega INTRA-LOTE y que la señal no se persistía
(una revisión solo-de-portada quedaba invisible para siempre); Fable PROBÓ que la fecha
se colaba en la tupla de revisión y un candidato podía bloquearse comparando días. Y
los dos, por tercera ronda consecutiva, me cazaron framing inflado en el censo. El
censo final sobre 1.069 documentos reales: 134 con señal, un único par supersedido
vivo (DP312x 202503/202512) que va a adjudicación de Alberto.

Dos: el perfil de retrieval que la fase 2 de rapidez esperaba «con una semana de
datos» que nunca llegaría sin tráfico. Seis filas reales bastaron para señalar al
gordo (retrieve 11-27 s/turno) y el cProfile local hizo el resto: CATORCE clientes
httpx construidos por consulta — siete segundos de contextos SSL leídos del disco,
más handshakes — unos 10 s/turno de puro overhead. La fase 2 de rapidez y la deuda
#72 resultaron ser el mismo trabajo, y ahora tiene recibo y retorno medido.

## s317b (12 ago 2026, madrugada) — El flip encendido y el turno partido por la mitad

Alberto mergeó #239, añadió la variable, y pidió plan claro + autonomía. Bloque 0:
verificar el flip contra la API de Railway (por servicio — el detalle que la memoria
ya guardaba), retirar el testigo XFAIL que llevaba tres días documentando el bug, y
estampar el lever en LEVER_DIGEST. #70 entero, causa 1 y causa 2, quedó cerrado en
producción en cuatro días de arco.

Bloque 1: #72 fase 1. El perfil había señalado ~10 s/turno de puro overhead de
transporte; el fix fue un cliente de proceso con un shim de UN token por sitio (55
migrados, cuerpos intactos) y la suite entera corriendo en modo kill-switch para que
veinte ficheros de fakes siguieran interceptando sin tocar una línea. El dúo r14 pagó
como siempre: Sol probó que mis limits eran código muerto (un HTTPTransport explícito
los ignora — expiry real de 5 s, no mis 30 prometidos) y que el kill-switch no era «la
forma de hoy»; Fable probó que mi «retries=1 cubre la conexión caducada» era falso y
me obligó a declararlo como riesgo residual. Cuarta ronda consecutiva cazándome
framing. Los tripwires de la casa (sello P1, registro de flags) cazaron el resto.

Resultado medido con la comparación correcta (within vs cross-mode, A/B intercalado):
retrieval 19→4,5 s caliente, paridad = jitter base exacto, cero efecto del pool en los
ids servidos. El turno del técnico — cuando vuelva a haber técnicos — baja del orden
de 30 s al de 15-20. La fase 2 (retries con idempotencia + paralelizar canales) queda
abierta con su residual medido: 4,4 s de espera secuencial.

## s317c (12 ago 2026) — #72 fase 2: el retrieval queda en 2,6 s

La fase 2 se diseñó ANTES de construirse y el dúo r15 (Sol 6 · Fable 5, 0 FP) trabajó
sobre el diseño: mi precedente «3c paraleliza desde s59» resultó HUECO (fan-out real =
1 por un `break` — quinta ronda consecutiva cazándome framing), el kill-switch de fase
1 no cubría la fase 2 (flags propios `RETRIEVAL_PARALLEL`/`HTTP_RETRIES`), PoolTimeout
quedó EXCLUIDO del set reintentable (backpressure local no se reintenta — Fable), y
los retries se acotaron a serving read-only: los 4 canales s306 conservan su fail-open
medido y los scripts su bisección+poison (un retry de POST sin upsert duplica — Sol,
verificado leyendo s104). De regalo estructural: content_search y el fetch del
diversify tragaban excepciones sin traza → canales CONTENT/DIVERSIFY en el esquema
cerrado. Medido con gate de paridad: PARIDAD EXACTA de ids en las 3 queries y mediana
4,2 → 2,6 s. Acumulado de la sesión de rapidez: el retrieval que costaba 19 s en el
perfil v1 cuesta 2,6 s (−86%). #72 cerrada para el serving; DEC-207.

## s318 (12-ago-2026) — #71 construido flag-off con dúo r16; el paquete de sentada única queda en manos de Alberto

La sesión ejecutó #71 de punta a punta sin encenderlo: censo (108 docs con
boilerplate de responsabilidad; 105 activos), frame `legal_disclaimer` en la
familia `_universal_frame_skip` con flag default-off (aparato protegido DEC-148),
y la sonda que el dúo obligó a rehacer — la v1 medía el regex y vendía «129
frases que desaparecerían»; la v2 ejecuta `_universal_obligations` con
pregunta-oráculo y da la cifra honesta: 83 obligaciones legales removidas en
70 docs, 0 técnicas cambiadas, 28 mixtas listadas verbatim para adjudicación.
Sol metió dos críticos contra mis propios recibos (la sonda-regex y la
contradicción de las mixtas) y Fable cazó la guarda ES ausente («el módulo no
es responsable de generar la alarma» es arquitectura, no exención) — sexta
ronda consecutiva cazando framing del autor. Todo aplicado; 24 tests
incluyendo el camino real off/on. La decisión del ON viaja en
`evals/s318_sentada_adjudicacion_packet_v1.md` (sentada única: DP312x + B2 +
#71), con el FULL fresco detrás, en la secuencia que Alberto fijó. También:
explicado el proceso de compartir el bot con DGs externos (aviso v8 + modelo
de acceso + bienvenida como pre-requisitos; paquete preparable a demanda).

## s319 (12-ago-2026) — Sesión de CONSOLIDACIÓN estructural completa: backup restaurable + backfill + graduación de flags + retirada del camino legacy (3 PRs, dúos r17-r19)

Alberto adjudicó la sesión de consolidación (1+2+3+4) con los puntos 1/4 del
paquete de apertura en paralelo, y el elefante (catálogo DEC-074) detrás. Se
ejecutó entera en tres PRs con dúo POR DISEÑO antes de cada build:

**PR-A (#244, mergeada)**: primer backup lógico restaurable bajo nuestro
control (drill de restauración obligatorio — 133.103 filas, PASS; capa PII
fuera con DECIDIR); backfill de revisión (94 docs, colisión única = DP312x,
auto-valida el censo s317); borrador del aviso v8 (6 DECIDIR para abogado) +
censo de primer tráfico con redacción de PII. El dúo r17 (Sol 10 con 2
críticos · Fable 3) rediseñó el backup ANTES de construirlo (recibo de bytes
≠ recuperación; un dump estático no hereda la retención RGPD) y cazó un ancla
falsa del autor («verificado import» que era un dict).

**PR-B (#245, mergeada)**: graduación de flags lote 1 — 7 + 1 pareja de 97:
el default del código deja de mentir sobre producción. El gate de
pre-verificación contra Railway disparó DOS veces (LLM_MAX_TOKENS=8000 sin
recibo → adjudicable; SELECTION_BLOCK no-settled → fuera), y el dúo r18 cazó
que el lote v1 rompía el ACOPLAMIENTO 10+3500 medido en DEC-092b. Los guards
de seguridad ganaron parser estricto (typo ya no degrada en silencio).

**PR-C**: el camino LEGACY de serving RETIRADO — run_turn es la ruta única,
ORCHESTRATOR_PATH muerto, CONVERSATION_POLICY graduado a impl con enum
estricto. Onda expansiva 68 tests → 0 en cuatro clases previstas. El dúo r19
cazó el fail-silent del rollback (typo → stub sin señal), las degradaciones
sin declarar del rollback-a-stub (INTENT_LLM inalcanzable) y la contaminación
legacy en DOCS y contratos («la clase que la PR decía eliminar estaba también
en la prosa»). Rollback re-documentado: por-lever preferente; stub = último
recurso explícito.

Racha del dúo: rondas 12-19 consecutivas cazando framing del autor — la
lección acumulada de la semana: los verdes dicen que el sistema pasa sus
pruebas; solo el adversario mirando la costura medido↔servido↔documentado
dice que las pruebas hablan del sistema.

## s320b (12-ago-2026) — E1 del elefante: el mapa se completa con la puerta y las sondas cazan lo que nadie había visto

E1 corrió entero en autónomo con la disciplina de la semana: derivar con la
maquinaria adjudicada (Catalog.resolve, jamás fuzzy), dúo sobre el diseño (r21
con dos críticos de Sol — el cruce por filename y los pm compuestos — y r22
fresco tras el aborto de Fable por tamaño de subject), freeze-contract y sonda
PRE antes de escribir. La sonda pagó: 20 de los 46 «sin entrada» eran UUIDs
stale de re-ingestas, y el censo de reconciliación descubrió 49 colisiones con
el id viejo aún vivo — posibles documentos duplicados activos que nadie había
visto. Se escribió solo lo que pasó todos los gates (26 altas + 11
reconciliaciones; doc_map 861→887, POST 46/46 con los 26 flips exactos) y todo
lo demás quedó en packets para la sentada: 49 colisiones, 67 ambiguos con
trazas, 133 candidates propuestos en draft, 4 de revisión humana, y los 620
candidates históricos pre-clasificados 620/620 contra contenido (359 confirmar
/ 261 revisar). Suite 3.833 verde. E2-E4 esperan; la sentada de Alberto decide
los packets.


## s320c (12-13 ago 2026) — el recibo que nunca leyó al juez, y una sentada que se salvó por dos vueltas de tuerca

Alberto preguntaba, antes de sentarse a adjudicar el packet B2, qué le recomendaba para
el ítem 2 (`hp011#2`, el alcance de `t.A`). Verificar la evidencia de ese ítem destapó
que la cifra que lo sostenía —el «0/3 firmes, máx 2/5» de s305— **nunca salió del juez**:
`s305_techo_modelo_ab.py` consumía `judge_conveyed21` con `sum(1 for v in <dict> if v)`,
que itera las CLAVES del dict y por tanto vale **siempre 2**. De ahí que el recibo tuviera
`base_yes = oracle_yes = 2` en las 9 reps de los 3 brazos, que `oracle_firme` fuera 0 por
construcción, y que el script solo pudiera imprimir «TECHO CONFIRMADO». DEC-186 se
construyó sobre eso. La clase, que es lo que lo hace deuda (#75): un juez que devuelve un
dict y un llamador que lo consume sin extraer la clave produce un número **plausible y
estable** — la peor forma de fallo, porque se lee como consistencia.

El dato de gobernanza duele más que el bug: el control adversarial **sí disparó** el 8-ago
—Sol emitió un crítico anclado en el recibo, con el patrón exacto— y se absorbió como
«matiz del umbral del juez». La cadena verificaba *prosa contra recibo*; faltaba el eslabón
*recibo contra instrumento*.

Re-juzgadas las respuestas guardadas con el juez canónico: correlación 9/9 entre «firme» y
la aparición literal del valor. Re-medición fresca (5 reps × 3 brazos, sellos nuevos): los
**tres brazos alcanzables**, opus-5 4/5 frente a 2/10 — que apunta a un eje de modelo sin
establecerlo (p=0,089 con las 15 reps, 0,061 con las 12 limpias). El script dispara su
propia guarda de «montaje no comparable». DEC-173 no cae: lo que hay es tensión empírica
entre dos composiciones con el mismo modelo de control.

Lo que la sesión enseñó de método fue más caro que el bug. Al retirar el ítem 2 argumenté
«el gold es legítimo porque el bot SÍ transmite el hecho» — el **mismo pecado en sentido
contrario**, decidir el alcance de un gold por el comportamiento de un modelo. Lo cazó Sol.
Después, una auditoría de los 8 ítems vivos devolvió «7 de 8 no marcables», y resultó que
el sesgo lo había puesto yo en el encargo («encuentra por qué NO marcar»): un pase de
falsación con el prior contrario tumbó 5 de las 7 acusaciones. Y al firmar 7
recomendaciones, el dúo tumbó por circularidad la mitad-de-alcance de tres —justificadas
con el scorer, con el serving y con el marcador— y el ancla de génesis de una cuarta.

Lo que sí funcionó fue **gastar lecturas de fuente en vez del criterio de Alberto**: cinco
consultas al corpus (AM-8200 p7, 15088SP p70, 50253SP p89, variaciones p5-6, CAD150R p19,
MI-716 p26/34/35) convirtieron cuatro preguntas abiertas en recomendaciones ancladas, y
confirmaron que la quinta —el ISO-X ante un fallo de tierra— tiene la fuente partida y es
genuinamente de Alberto. El packet quedó cerrado con tres columnas separadas por ítem: qué
escribe la marca, qué dice la fuente, qué decide él.

## s320d (13-ago-2026) — E2: el snapshot del detector deja de nacer de un SQL suelto, y el gate de equivalencia demostró por qué existe

La apuesta estructural del doble catálogo se ejecutó con el freno puesto donde
debía: el generador nuevo deriva del catálogo gobernado con la puerta
adjudicada del resolver, y el gate de equivalencia paró el build tres veces —
el derivado pleno era una expansión del detector disfrazada (1.235 altas), las
formas duplicadas del vivo se re-ordenaban cambiando qué servía el match, y
una «baja real» (VESDA-E-VEP) resultó estar sostenida por una query gold. El
v1 que queda es honesto: mecanismo gobernado con PASS total byte-idéntico en
conducta, y TODOS los cambios de datos (altas, bajas, gaps) en un packet
adjudicable por lotes. Dúo r23 pre-build completo (Sol 4 · Fable 3, 0 FP).

## s321 (14-ago-2026, nocturno) — E3: la identidad adjudicada llega a los chunks, con el dúo estrechando el lote hasta que la evidencia aguantó

Alberto preguntó «¿lo ha validado el dúo?» en el momento exacto: el split del
dry-run era mío y sin revisar. r25 lo rehizo (atestación=sujeto-dominante, no
mención; producto-real jamás se colapsa solo; hermanas sobre todas las
aplicables) y de 102 parejas quedaron 55 AUTO — que se aplicaron limpias:
579/579 chunks por-CAS con backup por fila, findability PASS fail-closed, y la
sonda E2-POST dando el cero pre-registrado. El residuo (47) viajó al packet con
la pasada LLM que Alberto mandó antes de dormir: fable-5 leyendo el contenido
real y citando verbatim — 15 quedaron «aplicables en bloque si asiente», 11
NO_DECIDIBLE honestos, y 1 donde el modelo defiende el pm actual contra el
mapa. Tres bugs de instrumento cazados por el camino (criterio circular vía
snapshot, patrón imatch asimétrico, temperature deprecada). TECH_DEBT #76
anotada por mandato: categoría+atributos de producto (el caso Detnov/Kidde).
E4 arranca a continuación.

## s321b (14-ago-2026, madrugada) — E4 cierra el elefante: el clarify lee el catálogo y la promesa de DEC-069 queda cumplida

El último tramo nocturno retiró el seed FAMILY_REGISTRY cumpliendo la promesa
que su propio comentario llevaba semanas haciendo: el clarify-por-divergencia
lee ahora el campo `clarify` adjudicable de las umbrellas, con las variantes
DERIVADAS de los miembros (el dúo r26 vetó re-declararlas y mató de paso el
fallback hardcoded, tercera copia del mismo dato), la provenance separada por
componente tras cazar Sol mi «datos T3» falso, y una sola instancia de
catálogo por proceso. Tests de texto-exacto donde el gate MT solo pedía
no-vacío; guard hp009 assertado; suite 3.841. Con E4, el elefante DEC-074/091b
está COMPLETO: lo que era «4-7 sesiones» aparcadas resultó ser ~3 de restante
real una vez el censo separó lo ya-ejecutado — y todos los residuos son
packets de datos esperando la sentada, no ingeniería pendiente.

## s322b (14 ago 2026) — El cierre de #76: los datos de Alberto, el dúo r28 y el inventario que por fin parece un mostrador

La sesión arrancó con tres mensajes de Alberto que eran, sin decirlo, un test de
integridad del sistema entero: PR #252 ya estaba mergeada (⇒ rama nueva), el
inventario genérico debía dejar de ser un listado infinito, y la CAD-250 «es
ampliable hasta 32 lazos creo, con módulos — no verás CAD-250-32». El corpus le
dio la razón con cita verbatim («soporta hasta 32 lazos en un único NODO»), y de
paso ancló CAD-171 («2 lazos») y CAD-201 («2 lazos ampliable a 8») — la
población no las había cazado por MUESTREO (secciones profundas), no por
ausencia. Su regla «toda central lleva capacidad» destapó que las 6 sin dato
eran las NC-PF convencionales: su dato son ZONAS, no lazos — clave hermana
nueva en el esquema, jamás fusionada. De la misma pasada cayó un defecto real
del writer (atribuía citas contra los 6 primeros chunks: 12 filas §0 saltadas,
rescatadas 12/12 contra doc completo) y el inventario genérico quedó agrupado
por tipología y familia gobernada, con cota por construcción.

El dúo r28 (Sol 7/7 + Fable 5/5, 0 FP) volvió a ganarse el sueldo: cazó el
sobre-claim «todo verbatim» del autor (el sufijo CAD-150 es derivación
DECLARADA), exigió `base` opcional (6 suelos inventados retirados), y su
predicción sobre verificar-50-almacenar-200 se MATERIALIZÓ: la re-verificación
full-text de 296 citas encontró exactamente 1 invención (tecnología «analogica»
de un SDK cuyo doc jamás dice addressable) — cazada y retirada. Fable añadió
inaplicable≠faltante (una convencional no «carece» de lazos), la colisión
«zonas de extinción» y el orden natural. Todo aplicado en el mismo diff.
Cierre: 138 clasificados Detnov+Kidde, 36/36 centrales con capacidad, smoke de
las 5 queries de mostrador en verde, deuda #76b (divergencia multi-mercado)
declarada con gatillo duro antes de Notifier. DEC-217.

### s322c (14 ago, tarde) — El packet E3 encogido y el estreno del carril online

Alberto preguntó si valía la pena revisar online las 32 filas no-alta del packet
E3. El censo dijo otra cosa: 12 eran parse-fails del mismo max_tokens=400 cazado
en #76, y 17 eran altas castigadas solo por hermanas sin resolver. La repesca v2
(muestreo doc-entero, full-text, hermanas-con-cita) dejó la sentada en 2 síes en
bloque (23+20) y 4 filas — y el carril online, estrenado en las 3 irreducibles,
pagó doble: confirmó ZXR50A (naming español del ZXr-A) y MPS-24AE como productos
reales, y destapó que «FD2705-10R» probablemente NO existe — es el nombre del
fichero fusionando FD2705R+FD2710R, un artefacto sentado en el doc_map como
canónico. La evidencia viaja en el packet con URL+quote+fecha; nada se escribe
sin adjudicación.

## s323 (15 ago 2026) — «Dónde corre Claude»: el móvil deja de ser un mirador y el dúo caza el centinela

Alberto pidió una sesión explícita para montar el cambio de «where Claude runs» y
poder gobernar el trabajo desde el móvil. La primera sorpresa fue que el gap real
no era la comodidad: el environment cloud estaba en **Default**, y eso es
exactamente lo que en s315/s316 dejó a `OPENAI_API_KEY` fuera y al revisor Sol sin
ejecutar — una sesión cloud no podía cerrar nada de impacto ALTO y **nada avisaba**.
La segunda fue de rumbo: no hay una superficie, hay tres, y **Remote Control cierra
el hueco que `ENTORNO_CLOUD.md` daba por perpetuo** («lo que el cloud NUNCA tendrá»:
OneDrive). La ingesta ya es gobernable desde el móvil; simplemente se ejecuta en la
máquina de casa. Montar solo cloud habría dejado media clase de trabajo fuera.

Alberto adjudicó contra mis dos recomendaciones —un solo environment con todas las
keys, y red Full— y eso se escribe tal cual en DEC-220, con el riesgo aceptado
delante: no hay secret store, así que la service key del corpus vive en el mismo
sitio donde una sesión lee portales de fabricantes. Partirlo en dos son dos minutos
el día que se prefiera.

Lo cableado responde a la lección de siempre: sin recibo no hay entorno verificado.
Nace `cloud_smoke.py` —que comprueba superficie, historial git, imports reales,
presencia de keys sin volcar su valor, y conectividad a los cinco destinos— y su
contrato se fija en tests. El hook de arranque, que reinstalaba todo en cada
`resume`, pasa a ser idempotente.

**Y el dúo volvió a ganarse el sueldo.** Devolvió NO SÓLIDO con tres hallazgos y
los tres eran ciertos: mis tests de no-fuga solo cubrían `--sin-red`, justo el modo
que evita el vector real (los mensajes de error de httpx llevan la URL dentro); la
URL del remote se publicaba verbatim en un recibo que se commitea, y en un clon
cloud viene con el token embebido; y **el centinela de idempotencia del hook no
sondeaba `cryptography`** — precisamente el módulo cuyo PanicException-al-importar
motivó ese hook en s315 — así que una marca presente y cinco imports buenos habrían
dado por buena una VM rota. El detalle que más dice: ese hallazgo, el mejor de los
tres, tuvo que marcarse CONCEPTUAL porque el revisor **no puede leer `.claude/`**
(deuda #79) — acertó razonando sobre mi propia descripción, que es exactamente la
dependencia que el Protocolo 3 existe para romper.

Queda pendiente lo único que convierte esto en verificado: el smoke de recepción
corriendo EN una sesión cloud del environment nuevo.

## s322i–s323 (15 ago 2026) — El día que los controles pararon tres veces al autor

La sesión empezó cerrando #76 y terminó con tres diseños míos en el suelo, y las dos cosas
son el mismo éxito. Por la mañana entró lo bueno: #76 al 100% para Detnov+Kidde, el packet
E3 completo con la cirugía FD2705 y el split ZXr que adjudicó Alberto con el manual en la
mano, y las dos adjudicaciones viejas de Railway cerradas con recibo y medición.

Por la tarde, el encogido: un workflow de nueve agentes convirtió 2.108 casillas en 1.181
en bloque + 911, y su verificador —al que le pedí una muestra de 12 citas— hizo el censo
completo de las 570 porque «12 sobre 570 detecta un fallo con ~2% de probabilidad, habría
sido teatro de rigor». Encontró 0 citas inventadas y, de paso, que la premisa del packet E1
era falsa desde el día que se escribió: las 49 «colisiones» eran fichas fantasma, y el anexo
must_preserve llevaba quién sabe cuánto sin dispararse en esos manuales.

Y luego vino la parte instructiva. Alberto pidió autonomía y se la prometí con una frase
que resultó falsa —«confirmar de más es barato»—; Sol demostró con tres anclas que quitar
`candidate` inyecta alias y términos en el detector, la clase FUEGO multiplicada por 600.
Rehíce el criterio, monté la puerta de retirada, la ejecuté… y de 18 filas pasaron 3, las
tres falsos positivos, con un producto real entre ellas. Mi predicado era «hay una medida
cerca», que en un manual técnico se cumple casi siempre: correlación disfrazada de prueba.
El tercer intento, el plan para arreglar #80 y #81, murió con dos críticos que eran de la
misma familia que el defecto que pretendían arreglar.

Cero filas tocadas en los tres casos. La lección no es que los dúos funcionen —eso ya se
sabía—, es que el autor produjo el mismo error tres veces con tres disfraces distintos, y
que sin el control habría escrito los tres. DEC-220.

## s321 (15-16 ago 2026) — La sentada que empezó por un ítem y acabó arreglando la regla con la que se mide

Alberto abrió preguntando qué le recomendaba para el ítem 2 del packet B2 (`hp011#2`) y qué
ficheros mirar. Al ir a la evidencia del ítem apareció que el recibo de s305 —el «techo del
modelo», DEC-186— **nunca había leído al juez**: `sum()` sobre el dict que devuelve
`judge_conveyed21` da siempre 2. De ahí salió medio día de tirar del hilo: re-juzgar las 9
respuestas guardadas, comprobar que el «NO alcanzable» de `hp017#2` que cerró la etapa 3 durante
meses no era una medición sino la etiqueta de un guard, endurecer la sonda para que un negativo
exija prueba de entrega y cobertura atestada, y reabrir DEC-173/175 con un censo que da población
≥3 donde se había decidido con 1. Se coordinó con una sesión paralela compartiendo árbol de
trabajo (cuatro colisiones de numeración, un `git add -A` que barrió 24.000 líneas ajenas y se
deshizo, un `--body -` que dejó una PR con un carácter de cuerpo).

Después vino la sentada de verdad, y Alberto la hizo **con criterio propio en cada ítem**: rechazó
el demote de `cat018` («no quiero falsear los misses» — la única casilla que mejoraba el marcador
sin tocar el bot); propuso el criterio de anclar en el pasaje con más «empaque» que, medido, se
convirtió en **DEC-221** («anclar en el que da el mecanismo»); leyó las dos reglas por defecto de la
PEARL mejor que yo (la Regla 1 anula porque comparte disparador; la Regla 2 no se cruza) y luego
cazó que **A5.4 es una sección de ejemplos** cuando Sol y yo la habíamos leído como norma en dos
rondas; razonó el ISO-X por lógica pura («si lo acotara no verías 'Tierra' en pantalla») y llegó
al mismo sitio que la tabla de la p71 (**DEC-223**); y pilló que el 2222 iba como supplementary
contra su propia marca. Dos de esas cuatro cosas ni Sol ni Fable las vieron.

La aplicación fue el commit largo: render de 17 páginas con ±1 (que cazó que el chunk «p26» del
MI-716 contiene la p27 física), GPT-5.5 leyendo en frío las mismas imágenes (7/7 coincidentes),
localización ES+EN por `doc_map` y no por `product_model` (porque `product_model` discrepa del
catálogo en el 35% de los documentos — **#84**, y me había hecho descartar el manual que
desambiguaba el ISO-X), seis upserts con un script que valida las seis en memoria antes de
escribir una, y la cascada s277 + canarios en el mismo commit. La migración de índices que Sol
pedía en dos rondas **no hizo falta**: `hp017#2` es un release_guard con anclas selladas y no se
parte; simulado antes, verificado después, 42/42.

Y en medio, el pequeño susto útil: un test que pasaba en solitario y se **apagaba en la suite**
—su `except` etiquetaba un `AssertionError` como «falta entorno»—, destapado porque `s156`
mutaba `os.environ` al construir un prompt y una variable con valor `"0"` (apagado) disparaba un
guard escrito para cazar el encendido (**#85**). Cerrado con el detector puesto: «ninguno: la
variable nunca cambia durante la sesión».

Queda decidido y sin cablear lo que más se va a notar: ante «el ASD535 de Detnov», el bot debe
**corregir la marca y responder en el mismo turno** (conducta (a), decisión de producto de Alberto).
Hoy corrige y pide confirmar. Y `hp002` no lo mide — el harness no pasa por esa ruta.

## s324 (16 ago 2026) — Alberto adjudica reglas, no filas; y por primera vez el lote entra por puertas que prueban

La sesión empezó con una pregunta de Alberto que era casi un reproche amable: ¿no podías hacer tú
la revisión exhaustiva con el adversarial y ahorrarme el trabajo manual? La respuesta honesta fue
que esa revisión ya se había hecho (el encogido de s322i) y que las 911 filas que quedaban «una a
una» no habían caído por un juez inseguro sino por falta de una regla. Así que en vez de un review
más, le puse siete reglas sobre la mesa. Las contestó en tres mensajes, con precisiones que solo
él tenía: KE-DP3120W es una mini-familia; VSN PLUS son 4/8/12 según MIEMI130; 2X-AT es la sub-familia
táctil; los FAAST «solo Notifier» son en realidad VESDA — «ese ejercicio ya lo hicimos», y el repo
lo confirmó (DEC-062/083, catalog_gt). Y R5 se convirtió, con su instinto, en la baja de seis
fragmentos portugueses con hermano español completo.

Lo demás fue construir la máquina que convierte reglas en filas SIN fiarse de nadie: un plan que
verifica cada cita contra el texto completo, un writer con freeze, backup, swap y CAS, y un censo
del radio de explosión que mide lo que r30 había avisado que nadie medía. La máquina cazó cosas
antes de escribir —dos productos que ya existían con otra grafía, un ExitPoint que ya era alias de
PF24V, un paraguas «2X-A» que dispara en «2 x a»— y el dúo cazó lo que la máquina no veía: Sol, que
el freeze era de papel y la escritura no atómica; y que R1', el refinamiento que a mí me parecía
obvio, no lo había firmado nadie. Fable acertó cinco veces desde las semillas… y fabricó una
transcripción de tools con ficheros que no existen (deuda #86). Aplicado, verificado en censo,
suite verde. Alberto vuelve a un packet con marcas fila a fila y una lista corta de lo que solo él
puede decidir. La Puerta A, la que r30 tumbó, quedó por fin validada contra su doble control; su
resultado honesto es que 0 de las 18 filas RETIRAR son de la clase que cubre. DEC-221.

## s321 tarde (16 ago 2026, autónoma) — Medir sí; cablear y reescribir, no sin él

Alberto se fue unas horas y dejó el rumbo: seguir con el dúo en lo delicado, coordinarme con la otra
sesión, no mergear. Lo que salió bien fue lo que se podía **medir**: el smoke y el full de factlevel
sobre el ruler recién aplicado dieron paridad con s291 y, hecho por hecho, exactamente lo que la
sentada pretendía — el split de `cat018` que él defendió contra el marcador sale OK+OK, el demote del
ISO-X sale del denominador, el `valor` de `cat020` que él fijó entra y pasa. Y el censo de #84 convirtió
una discrepancia de metadata en un daño de serving cuantificado: 309 chunks del manual de la AFP-400
que el catálogo declara y el alineado no ve.

Lo que salió bien de otra manera fue lo que **no** hice. Quise cablear la conducta (a) del `mismatch`
—«corregir y responder»— y Sol, en dos rondas sin un solo falso positivo, fue moviendo el diseño de «un
flag en el handler» a cuatro subsistemas y una decisión de producto que no es mía (¿qué pasa con dos
marcas en la misma pregunta?). Quise reescribir DEC-186 con su número real y Sol, otras dos rondas,
me devolvió tres veces a documentos que no había leído enteros — uno de ellos, el PLAN, con líneas que
yo mismo había escrito por la mañana. Las dos cosas quedan como diseño consolidado para una sesión con
él, y las dos son la misma lección de toda la sesión: concluir del titular sin leer el cuerpo. La
diferencia hoy es que el dúo lo cazó antes de que tocara código.

Un dato nuevo que sí se ganó: `hp013#1` bajó de escalón — el carrier PWR-R ya no entra ni al pool —,
y el registro decía lo contrario desde hace semanas.

## s324b/c (16-17 ago 2026, misma sesión que s324; tarde con Alberto + noche autónoma) — Medir la etapa 3 antes de construirla, y aplicar solo lo que él firmó

**Cómo empezó.** Con PR #275 mergeada, Alberto zanjó el modo de trabajo: **una sola sesión** («prefiero la
simplicidad de una sesión aunque luego ataquemos puntos en paralelo con agentes»): él revisa la asignación
documento→modelo en los packets; yo mido la etapa 3. Sus adjudicaciones fueron llegando en frases: «R1' OK»,
«§0.C revisado (en la copia `_AS2`) — consolida en un único documento», «Documento Vision Supra: baja, confirmo»,
«Doc Stratos: este doc es paraguas, no de modelo concreto», «§0.D revisado, con comentarios… hecho también §0.E»,
y sobre Detnov: «Confirmo que es modelo, y también lo son los otros». Cada una entró por la mecánica de s324
(plan verificado full-text → dry-run con censo → aplicar con recibo → verificación posterior 0 fallos), y el gate
volvió a ganarse el sueldo: confirmar CCD-102/104/108/112 ACTIVABA alias descriptivos («2 zonas», «4 zonas»,
«Conventional panels with 2 detection zones») que disparaban en consultas genéricas — la clase exacta que r30
había avisado; se retiraron 14 antes de confirmar. El revisor Fable standalone sobre el lote §0.C cazó 6 cosas
reales (paraguas «2X-A» diferido: la nota de Alberto adjudica el ALCANCE, no el riesgo léxico; NFXI-BSF-WCH sí
estaba atestada; una cita prestada de otra FAQ; alias ASCII de ID²NET; STRATOS es una gama). Y hp015 se resolvió
por DATOS, no por lever: CCD-103 era candidate bajo `unresolved` y hoy es `detnov:ccd-103` (tráfico real: una
detección nueva y verdadera).

**La etapa 3.** El encargo de la otra sesión (sondar los 8 «servido y omitido» del FULL 16-ago) lo ejecutó un
agente de medición: 7 ALCANZABLE / 1 NO (`hp009#0`); 3 de los alcanzables eran «flips» (la base ya transmitía a
veces). Escribí la propuesta del lever B (D1 «cierre de bloque de lista» + D2) y el dúo r33 la paró con razones
verificables — Sol: no es una vista pasiva, las listas no tienen fin inequívoco, base/oráculo independientes no
localizan retrieval vs síntesis; Fable (14 `tool_use` reales): «sustitución de denominador — Alberto debe adjudicar
con el 1, no con el 6/30». Cuando Alberto, antes de dormir, preguntó si no tenía sentido «construir el lever
apoyándome en el adversarial» y «atacar los no OK hasta >95%», le devolví el dato: población por gold {hp017,
hp005, hp015, hp001} = 4 y no es una clase; **un solo hecho pagable por serving** (`hp017#1`); los 19 «no OK» son
heterogéneos. «OK, a por ello». La noche fue de medir con dinero de verdad y $0 donde se pudo: la **prueba
offline D1** (código real de coverage, fidelidad 40/40) dijo que el cierre SÍ alcanza el bullet de hp017#1 pero solo
si la línea en blanco no rompe el bloque, que no paga ningún otro hecho no-OK y que toca 9 hechos OK para pagar 1;
el **replay sobre composición congelada** ($5,44) dijo que los 4 flips son **síntesis inestable 4/4** con la vista
idéntica — con N=3 un FULL los etiqueta por azar. DEC-175 lleva ahora la cifra de cabecera «1 hecho» y D1 no se
construye sin un GO explícito sobre ese 1. Los tres de conducta («negar la premisa») son un packet de gold-review.

**Lo preparado para mañana.** Los bloques E1b sin firmar: 11 planes con su dry-run del gate, 11/11 PASS (422
confirmables verificadas, 40 colisiones listadas con propuesta, 125 alias descriptivos que se retirarían antes; el
gate parió una regla nueva del clasificador —«truncación ambigua de familia»— porque `VSN12` disparaba «vsn 12»).
Nada aplicado: un «sí» por bloque. La suite cazó su propio acoplamiento: `test_s307` (cota de la lista plana de
inventario) dependía de que Notifier no tuviera productos clasificados; desde esta noche los tiene (software).

**Lección de la sesión.** Cuando el dueño propone construir, la respuesta correcta no es ni obedecer ni negarse:
es traer el dato que convierte la propuesta en decisión (Protocolo 2 + bias #51). Y un agente de medición rinde
si el encargo lleva las trampas escritas: los cuatro de esta noche devolvieron recibos verificables y ninguno
tocó `src/`.

# Archivo del PLAN — estados anteriores s100→s322b (movidos en s324d, 17 ago 2026)

> Texto ÍNTEGRO de los bloques «Estado anterior» que vivían en `docs/PLAN_RAG_2026.md` hasta s324d (y del
> «Qué sigue (s77)» + «Antecedentes s69–s83»), movido aquí sin editar para mantener el PLAN compacto (DEC-036).
> Las citas antiguas del tipo «PLAN → Estado anterior (s2xx)» resuelven en esta sección. Cada bloque conserva su
> encabezado original (`## Estado anterior (…)`), su fecha y sus anclas.

## Estado anterior (s322b — 14 ago 2026)

**El arco s318→s322b: sentada B2/DP312x/#71 ejecutadas por Alberto (PR #249);
consolidación s319 (backup restaurable + graduación de flags + retirada del legacy
serving, DEC-209/210/211, PRs #244-246); EL ELEFANTE COMPLETO — entity-linking
DEC-074/091b en E0-E4 (doc_map 219 activos + QA de candidates, derivación gobernada
del snapshot, re-tag F3a, clarify gobernado sustituye FAMILY_REGISTRY; DEC-212..215,
PRs #247/#248/#250/#251) — los residuos son PACKETS de adjudicación, no ingeniería;
y #76 «de mostrador» completo: mecanismo (DEC-216, dúo r27, PR #252) + cierre
Detnov+Kidde (DEC-217, dúo r28, s322b): 138 productos clasificados con cita
re-verificada FULL-TEXT (1 invención cazada), semántica de capacidad «N = hasta N»
(adjudicada), clave `zonas` para convencionales, la ampliación modular CAD-250
«hasta 32 lazos» anclada verbatim, e inventario genérico AGRUPADO por
tipología/familia (adjudicado 14-ago). Deuda nueva #76b (divergencia multi-mercado,
LATENTE) con gatillo duro antes de poblar Notifier. Arco previo s316→s317
(INTENT_LLM flippeado, #72 −86%, #73) en la lista de abajo.**

1. **#68 CERRADO** (DEC-199). El lote Casmar/Kidde pasa de **0/0** a **10.161 enunciados +
   2.516 hyq**, verificado en DB (V 10.161/10.161 ids; hyq universo completo, poison 0,
   smoke ✅). Coste real $18,67 + ~$4.
2. **#69 CERRADO** (DEC-199). `source_url` **76 → 1.084** de 1.243, con 1.007 objetos
   (1,30 GB) en el bucket `manuales`. Residuo de 159 EXPLICADO: son exactamente los de sha
   placeholder (#4 Phase 3); **cero docs con sha real quedaron fuera**. Coste marginal 0 €.
3. **#70 etapa 1 SHIPPEADA** (DEC-198, PR #232). Guardia de cambio de marca como
   `TypeHandler` en grupo -1. **La v1 cableada era PEOR que el bug** (`FUEGO` es fabricante
   real y «fuego» la palabra más común del sector ⇒ 8/19 consultas borraban contexto):
   recalibrada precisión-primero. **Etapa 2 ABIERTA** (el fall-through; toca el clasificador
   de F1, con gate MT propio) — testigo en `xfail(strict)` que avisará por XPASS.
4. **Instrumento de transporte VIVO** (DEC-197): conduce `handle_message` real, $0. Es lo
   que permitió que el fix de #70 fuera demostrable y no otra corazonada.
5. **Lever del dedup CERRADO CON DATO** (DEC-196→198): `dup_cross_vintage` = **0/2.516 =
   0,00%**. Era un no-op medido; revertirlo fue correcto.
6. **TECH_DEBT #72 NUEVO**: tres scripts murieron por la misma causa (excepción de
   transporte sin capturar) y se parchearon uno a uno. Falta un cliente Supabase común con
   política de reintentos; el matiz que lo impide hacer mecánico es que la idempotencia no
   es universal.

7. **Lever INTENT_LLM: construido, medido y con los GATES DEL FLIP CERRADOS**
   (s316g→h, DEC-203/203b/204, PR #237 + rama s316h): gate de juicio GO adjudicado
   (Sonnet 40/40 · 0 falsos SWITCH · freeze) · sección `intent` en el esquema cerrado
   de `rag_trace` (`not_wired`≠`off`, coherencia cerrada, captura POR TURNO — la
   carrera de `fn.ultima` fuera del camino servido) · e2e del camino servido PASS 6/6
   con proveniencia (`artefactos_sha256`, corrida final sobre el commit) · pegamento
   del handler gateado EN CI (instrumento de transporte). Flag OFF sigue byte-idéntico.

8. **#73 CERRADO** (s317, DEC-205, dúo r13 aplicado entero): puerta de revisión en la
   ingesta — señales de edición $0 (filename+portada, familias del corpus real), cruce
   corpus PAGINADO + INTRA-LOTE, contrato >=, señal persistida en `documents.revision`,
   override `--ignorar-revision [GLOB]` auditado. Censo: 1.069 activos → **1 par
   supersedido vivo (DP312x 202503/202512) a adjudicación de Alberto**. Rumbo de la
   sesión (Alberto): censo del 👎 APARCADO (sin técnicos activos); foco = arquitectura
   y flujos.
9. **Rapidez fase 2 DESBLOQUEADA sin esperar tráfico** (s317, perfil medido,
   `evals/s317_perfil_retrieval_v1.md`): retrieve como el gordo del turno (11-27 s en
   las 6 filas reales) y el perfil local atribuye **~10 s/turno a construir 14 clientes
   httpx por consulta** (7,25 s de contextos SSL + handshakes) → **la fase 2 ES #72**
   (cliente HTTP común); el residual (~8 s de RPCs secuenciales) es la fase siguiente.

10. **FLIP de INTENT_LLM EJECUTADO por Alberto y VERIFICADO** (s317b, DEC-205b): API
    Railway por servicio → `worker.INTENT_LLM='on'`. #70 etapa 2 corre en producción.
    Testigo XFAIL retirado (relevo = test de pegamento flag-ON); fila estampada en
    LEVER_DIGEST. Veredicto conducta-en-producción pendiente de TRÁFICO.
11. **#72 FASE 1 CERRADA** (s317, DEC-206, dúo r14 aplicado entero, PR #240): cliente
    HTTP compartido de proceso — retrieval caliente **19,0→4,5 s (−76%)**, mediana
    intercalada 11,9→4,6 s, paridad A/B limpia (cross-mode = within-mode en las 3
    queries). 55 sitios migrados; `HTTP_POOL=off` = rollback sin deploy; EN MAIN.
12. **#72 FASE 2 CERRADA → LA DEUDA QUEDA CERRADA PARA EL SERVING** (s317c, DEC-207,
    dúo r15 PRE-build aplicado entero): paralelización de canales léxicos 3a/3b
    (≤6 tareas GET, orden determinista, flag `RETRIEVAL_PARALLEL`) + retries
    transitorios opt-in read-only (`reintentos=1`, PoolTimeout EXCLUIDO, flag
    `HTTP_RETRIES`; canales s306 y scripts FUERA a conciencia) + canales
    CONTENT/DIVERSIFY en la traza cerrada. **Mediana 4,2→2,6 s con PARIDAD EXACTA de
    ids; acumulado desde el perfil v1: 19,0→2,6 s (−86%).** Residual fase 3 (upserts
    en writes de scripts) solo con señal de dolor.

**Qué sigue (s323b — identidad del corpus; LO PRIMERO al abrir sesión)**: (a) **rehacer el
plan de #80/#81 con las 10 correcciones del dúo r31** (`evals/s323_plan_80_81_v1.md`, adenda):
política explícita para ficheros sin fila activa · fallo ANTES del borrado en `index_chunks`
(hoy borra y luego inserta NULL) · invariante de COHERENCIA (el documento del doc_map debe ser
el MISMO que el de los chunks servidos — `doc_map→active` + `NOT NULL` NO capturan lo que
rompió #80) · baseline por-entry EJECUTADO (la sonda midió 49 atestaciones, no 191) ·
contabilidad 49+1+3+7=60. Vuelve al dúo y, si pasa, se aplica con mecánica T3. **Es un defecto
VIVO**: el anexo `must_preserve` no actúa en esos manuales; (b) la **limpieza de candidates
queda APARCADA** hasta tener el gate medido (`evals/s323_criterio_limpieza_candidates_v1.md`):
el dúo r30 tumbó las confirmaciones por el radio de explosión al detector (quitar `candidate`
activa alias + paraguas + términos del detector), y el predicado de retirada se auto-rechazó
por confundir correlación con prueba. Antes de retomarla: censo del radio de explosión (solo
lectura) + predicado de RECONSTRUIBILIDAD validado contra el doble control (positivos `MM-82`,
`TO-3200M`, `OF-48V`, `LOCAL-360`; negativos `VSN 2Plus`, `PL4-E`, `34110400`); (c) los
**packets v2 están listos y verificados** (568/568 citas verifican en su documento atribuido),
a la firma de Alberto cuando quiera; (d) **FULL fresco v3.2** — no medimos el bot end-to-end
desde antes del elefante, #76 y la subida de velocidad: todo lo que afirmamos hoy sobre su
calidad es inferencia.

**Qué sigue (s323)**: (a) **el smoke de recepción en cloud** — Alberto crea el
environment (variables + red Full, §3.1 de `ENTORNO_CLOUD.md`) y la primera sesión
cloud corre `cloud_smoke` + suite + `check_deps`; el recibo se commitea. Hasta
entonces DEC-220 no está verificada. (b) Lo de s322b/c que sigue vivo, abajo.

**Qué sigue (s322b/c — vigente)**: (a) **SENTADA ÚNICA de Alberto** — **packet E3 v2**
(`s321_e3_packet_adjudicacion_v2.md`, SUPERSEDE al v1: §0 23 + §0-bis 20 en bloque
+ solo 4 una-a-una con evidencia online adjunta — la repesca v2 s322c convirtió los
12 parse-fail del bug max_tokens y resolvió las hermanas a máquina) + E2 (1.235/23)
+ E1/E1b + s318-restante (el §1 de
#76 quedó VACÍO: la repesca v3 a tabla-de-modelos cerró Detnov+Kidde al 100% con
cita verbatim; el packet **E3 está COMPLETO** — 44 retags aplicados + split ZXr; y
**LLM_MAX_TOKENS y las 9 vars de Railway quedaron ADJUDICADOS y ejecutados**,
DEC-219 — ya no están en la cola); (b) FULL fresco v3.2 tras la
sentada; (c) poblar #76 en más marcas por packets — con el **gatillo #76b** (flag
de divergencia + `alcance`) OBLIGATORIO antes de Notifier/multi-mercado; (d) leer
traza intent/latencia cuando haya tráfico.

**Qué sigue (s321b — histórico)**: (a) SENTADA ÚNICA de Alberto — packets E3 (§0 15-en-bloque + §1 32) + E2 (1.235/23) + E1/E1b + s318-restante + LLM_MAX_TOKENS + vars Railway; (b) FULL fresco v3.2 tras la sentada; (c) #76 categoría+atributos (mandato 13-ago, diseño con dúo — consume el esquema clarify de E4); (d) leer traza intent/latencia cuando haya tráfico.

**Qué sigue (s321, E3 cerrado — histórico)**: (a) SENTADA de Alberto — packet E3 (§0 15-en-bloque + §1 32) + packet E2 (1.235 altas/23 bajas) + packets E1/E1b + LLM_MAX_TOKENS + vars Railway; (b) E4 (clarify gobernado sustituye FAMILY_REGISTRY) en curso nocturno; (c) FULL fresco tras la sentada; (d) #76 categoría+atributos (mandato 13-ago) tras E4.

**Qué sigue (s320b, E1 cerrado — histórico)**: (a) SENTADA ÚNICA ampliada — packet E1 (`evals/s320_e1_packet_adjudicacion_v1.md`: 49 colisiones-integridad + 67 tier B + 133 candidates draft + 4 revisión) + E1b (359 confirmar/261 revisar) + los packets previos (s318 + LLM_MAX_TOKENS + vars Railway); (b) FULL fresco tras la sentada; (c) E2 CERRADO v1 (DEC-213: mecanismo gobernado + packet `s320_e2_packet_adjudicacion_v1.md`); E2-swap con datos tras adjudicación · estructural, gates de equivalencia) · E3 re-tag F3a · E4 clarify sustituye FAMILY_REGISTRY — cada una con su dúo.

**Qué sigue (s319 cierre — sesión de consolidación COMPLETA, DEC-209/210/211)**:
(a) **SENTADA ÚNICA de Alberto** — `evals/s318_sentada_adjudicacion_packet_v1.md`:
DP312x supersedida (sí/no) + sentada B2 (packet v3) + encender
`EC_LEGAL_DISCLAIMER_SKIP` (#71, DEC-208); **+ 2 adjudicaciones nuevas de s319**:
LLM_MAX_TOKENS 8000-vs-3500 (el 8000 vive en Railway SIN recibo, DEC-210) y las
vars de Railway ahora redundantes (listas en DEC-210/211 — retirarlas cuando
quiera); (b) tras la sentada: **FULL fresco v3.2** (~$25, smoke primero) +
estampar scoreboard; (c) **EL ELEFANTE** (mandato s319): completar el
entity-linking del catálogo canónico (DEC-074/091b, 4-7 sesiones) — el
workstream de escalabilidad a 30+; (d) apertura a DGs: los puntos 1/4 están
PREPARADOS (aviso v8 borrador con 6 DECIDIR + censo de tráfico listo); faltan
2/3 (modelo de acceso + bienvenida) — a demanda; (e) verificar
pool+paralelización en `salud_latencia_etapas_v1` y leer la traza `intent`
cuando haya tráfico; (f) backup mensual (runbook ENTORNO_CLOUD); (g) #74 solo
si nace consumidor.

### s315 (9 ago 2026) — resumen

**s315 (los puntos de Alberto, automode — DEC-193):** (1) **latencia INSTRUMENTADA**
(p50 34,5s/p95 57,6s sin atribución → `stage_timings` por etapa en `rag_trace.timings`
tri-estado + vista `salud_latencia_etapas_v1` APLICADA; el plan de ataque se decide con ~1
semana de datos — nada optimizado a ciegas); (2) **links a manuales construidos**
(`documents.source_url` + backfill Casmar 76/1.243 + leyenda con `URL#page=N`; flag
`SOURCE_LEGEND_LINKS`, y OJO: es no-op si `SOURCE_LEGEND` está off — receta Railway:
encender AMBOS); (3) **barrido pm-de-familia APLICADO a producción y verificado 49/49**
(104 variantes SUJETO, refutación independiente ×3 + invariantes imatch 104/104; recibo
`evals/s315_family_pm_patch_v1.json` — la 4ª instancia findability cerrada a escala);
(4) **panel = guía dashboard Supabase** (`docs/DASHBOARD_SUPABASE_GUIA.md`, DEC-183 se
mantiene; las 6 vistas vivas y con datos); (5) **#68 NUEVO (pregunta de Alberto): los
lotes de ingesta nuevos NO pasan por enunciados/hyq** (lote s314: 1.091 chunks = 0/0
verificado) — trigger: ANTES del siguiente lote. **Deploy HECHO mismo día**: PR #228
mergeada, App de GitHub instalada (403 resuelto), flags de links ON en Railway, timings
VIVOS (primera atribución real: retrieve 11-27s ≈ 40-45% del turno — el sospechoso nº1
de la rapidez ya no es solo la generación). **s315b (#68)**: fase de canales derivados
por lote CONSTRUIDA (DEC-194; dúo NO-SÓLIDO → 13 fixes aplicados; contrato de vintages
hyq global/lote) — **run del lote Casmar pendiente en máquina con claves**:
`derive_channels_lote.py --since 2026-08-08 --tag casmar314 --data-root <OneDrive>`.
Bugs vivos cazados por Alberto: `<br/>` en apéndice must_preserve (FIX + tests) ·
carry-forward sobrevive al cambio de marca (#70) · disclaimer legal como obligación
(#71, aparato protegido). Storage: bucket `manuales` + subida OneDrive (807 a subir,
dry-run de Alberto hecho; --aplicar pendiente + diagnóstico de 269 sin-fila con el
script v2). Dúo con gap declarado (Sol sin key en el entorno; sub-agente Opus
12 hallazgos aplicados). **Cola de puntos de Alberto**: página cómo-utilizar (punto 4) ·
fotos/pantallazos (punto 5 — sonda de alcanzabilidad con fotos reales ANTES de diseñar) ·
Aritech/Edwards (recon listo `scripts/s315_casmar_recon.py`; egress bloqueado en la
sesión; evidencia: 2X ya en corpus, Edwards NO está en Casmar → firesecurityproducts.com)
· Tyco/Hikvision/Dahua/Ajax («más adelante», Alberto) · rapidez fase 2 (leer la vista con
datos) · sentada B2 (suya; **packet vigente = `evals/s312_goldreview_b2_packet_v3.md`**,
la v3 del dúo doble — el v1 de s294 es solo registro; staleness corregida por Alberto en
s315: yo mismo cité el v1).

## Estado anterior (s314 — 9 ago 2026)

**PRODUCCIÓN**: **paquete de telemetría pre-técnicos puntos 1+5 VIVOS** (PRs #200/#201/#202, 2
migraciones aplicadas, `TERMS_VERSION` v3). El 👎 deja de ser señal muda: invita a explicar,
captura la prosa con intención explícita (`ForceReply`) y la ancla a la consulta, al veredicto y
a la evidencia servida. Verificado contra la DB real, no solo con tests. Etapas 1-2 completas,
OK 115/131 sin cambios (nada de esto toca retrieval ni síntesis).

~~**Etapa 3 CERRADA como cola de ingeniería (DEC-172/174/175)**~~ → **REABIERTA EN LA PUERTA DE
POBLACIÓN (s321)**. Ese cierre tenía cuatro patas y le quedan dos. **Caen** `hp017#2` (su «no
alcanzable» NO era una medición de alcanzabilidad: sin inyección ni admisión; la primera sonda real,
s321, da **0/5 → 5/5 en 3/3** ⇒ es de RETRIEVAL, no de síntesis) y `hp011#2` (medición VÁLIDA el
2-ago, CADUCADA: s320c da los tres brazos alcanzables). **Aguantan** `hp003#4`/L3 v2 parado (98,3%
de precisión, pero exigía 2 cambios en la lane L2 viva para 1 hecho) y `cat017#2` NO-GO por
población (1 gold, 0,13% del corpus) — métrica POBLACIÓN, ortogonal a lo que ha caído.
**Ojo: reabierta NO significa «hay lever».** Los dos hechos son alcanzables pero su **población
está sin medir**, y la regla del propio DEC-175 exige las dos puertas. **Siguiente paso = censar**
(barato, sobre el recibo FULL congelado), no diseñar. Lo que resta ahí sigue siendo **adjudicación
de golds (Alberto)** + ese censo. Ver banners de DEC-173/DEC-175.

**El hallazgo que cambia el rumbo (DEC-176)**: el primer fallo ORGÁNICO —el bot dio mal la ruta
al menú AVANZADO de la CAD-171, teniendo el dato servido— es de **la misma clase que `hp011#2`**:
responde con el **elemento vecino**. **Dos instancias, una de uso real, el mismo día que se
abrió el canal.** ⇒ la población que DEC-175 quería fabricar con una cohorte **empieza a entrar
sola**; la prioridad pasa de construir instrumento a **dejar entrar señal**.

**Qué sigue (nada bloqueado):** (1) **sentada B2 de gold-review — 8 ítems adjudicables**; el packet
vigente es **`evals/s312_goldreview_b2_packet_v3.md`** (el v1 y su ítem 10 quedan como registro).
⚠️ **El ítem 2 (`hp011#2`) NO se adjudica**: su evidencia de s305 quedó retirada en s320c — el
instrumento no medía (TECH_DEBT #75), así que «los 3 modelos responden el DEFAULT y no el RANGO»
es **falso en 4 de las 9 respuestas** del propio recibo. Vuelve a la sentada solo si la re-medición
fresca lo justifica;
(2) ~~lista de adquisición: 44 documentos + la Guía Avanzada de la CAD-171~~ **CORREGIDO
(s302, DEC-184): eran 7-8, no 44 — y la Guía de la CAD-171 YA LA TENEMOS.** El packet
adjudicado (`evals/s302_adquisicion_packet_v1.md`) desmonta 37 de los 44 candidatos: 18 ya
están en corpus bajo otro nombre de fichero (el barrido casaba contra el NOMBRE, no contra
el código impreso en portada), 10 son referencias de PIEZA o rangos de direcciones, 5
erratas/pies de página. **Y la «Guía Avanzada de Configuración» de la CAD-171 es el
`MC-380 rev c` que YA está ingestado y mapeado a `detnov:cad-171` — con la ruta correcta
(`AJUSTES > AVANZADO`, §5.4 p.29) que el bot falló**: el primer fallo orgánico es 100% de
SELECCIÓN, se refuerza DEC-176 y NO se arregla comprando nada (4ª vez de la clase
`feedback_corpus_gap`). Quedan **3 documentos con valor real**: `997-340-005` (programación
por PC ID1000), `997-415` (actualización ID50/ID60/ZX50, 6 citas, dos marcas) y `997-412`
(Sinóptico IDR — hueco REAL que el barrido PERDIÓ por un bug de `break` en citas dobles).
Vía: los PDF de `notifier.es`/`morley-ias.es` se descargan sin login; lo cerrado es el
ÍNDICE → 3 altas de partner (→ Alberto). Deuda del instrumento: TECH_DEBT #62; (3) **RGPD (s295→s299, DEC-177..181): CERRADO Y VIVO EN PRODUCCIÓN (5-ago)** —
retención 24 meses → disociar con seudónimo estable, aviso en dos capas v7, libro de eventos,
marca de utilidad inalcanzable para el bot, bootstrap re-ejecutable con test en CI. **s299
(PR #210 mergeada + migración APLICADA el 5-ago): la pasada es UNA función en la base +
reloj pg_cron mensual VIVO (primer recibo 1-sep) + recibos**; el dúo cazó y cerró un oráculo
de pertenencia VIVO en producción (default privileges de Supabase sobre funciones —
`rgpd_quedan_identificados` ejecutable por la clave anónima; CERRADO y re-verificado contra
el catálogo) y el punto de no retorno aprende `answer_messages`. Transferencias DOCUMENTADAS
con fuente (valida asesor). **Acciones de Alberto**: LIA y tabla de transferencias al asesor
+ vigilancia trimestral del recibo mensual. Residuo:
base jurídica (decidida: interés legítimo, efectiva tras validación → aviso v8) +
`user_consent`/`consent_events` [DECIDIR plazo]. **NO desbloquea `convo`**: ese gate exige la
matriz `RGPD_LIFECYCLE_MATRIX_TEMPLATE.md` FIRMADA, que sigue sin firmar;
(4) puntos 2/3/4 del #60 (reacciones: cambian el transporte, piden
sonda + dúo propios) y punto 6 (corrección de marca, engancha con `hp002` del packet);
(5) `hp003#4` sigue siendo el único lever vivo de etapa 3 si alguna vez se retoma L3 v2.
**Frentes nuevos (Alberto, 6-ago; forma auditada con evidencia — 20+10 agentes + 3
verificaciones adversariales, s300):**
(6) **«dashboard» SIN app — CONSTRUIDO (s301, PR #213; DEC-183)**: export del 👎 con
motivo y prosa, `route` + log de shortcuts de consulta y clarify (#31 cerrado; la
CORTESÍA excluida — promesa literal del aviso v7, crítico del dúo), 5 vistas agregadas
versionadas (front = dashboard de Supabase), Gold gate en CI, guardas de ingesta,
`marcar_utilidad.py`. **Acciones de Alberto tras el merge**: aplicar EN ORDEN las
migraciones `20260720095702` (rag_trace — la de JULIO, descubierta sin aplicar: el bot
llevaba semanas logueando sin traza) y `20260806150000_s301`; montar el dashboard de
Supabase sobre las 5 vistas (clicks).
(7) **automatización proporcionada** — ingesta: guardas anti-manifiesto-vacío ✓ +
**`ingest_new.py` CONSTRUIDO Y ESTRENADO (s314, DEC-192)**: driver A2+B por canal con
gates fail-closed, dry-run con coste, alta de `documents` ANTES de indexar, reanudable;
primer lote real = Casmar/Kidde 74 docs (ver bloque 10). Falta del frente: playbook
re-escrito contra `src/reingest/`; ops: `gold_store validate` a CI (3 líneas — su docstring dice que CI lo
corre y es falso), verificación corpus↔store↔`chunks_v2` (S), `BOT_ERROR_LOGGING=on` en
Railway (Alberto, coste cero); feedback→gold: puente 👎-con-prosa→packet pre-rellenado
(M, DESPUÉS del export). PREMATUROS declarados: eval periódica en cron y auto-ingesta
por scraper — pasan a obligatorios con el primer técnico real.
(8) **modernización dirigida por blueprint** (`docs/BLUEPRINT_MODERNIZACION.md`): L0
HECHO — `tests/test_import_contract.py`, la arquitectura como invariante de CI (matriz
de paquetes + 6 excepciones con trinquete + 2 ciclos permitidos + isla-harness de 35
módulos en cuarentena LÓGICA desde el día 0); lotes L1 (catalog_store) → L2a (isla →
`harness/`) → L2b (flags.py recortado) → L2c (split lane vetada) → L3 (embed), cada uno
con paridad + sellos enumerados + dúo. NO se reescribe nada medido; `retriever.py` no
se parte en estos lotes.
**(9) CERRADO (s303→s306) — el fallo orgánico clasificado en firme, el techo medido con 3
modelos, y las dos deudas colaterales resueltas.**
· **Veredicto FINAL del caso CAD-171 (s303, confirmado tras el arco s304): SELECCIÓN DE
SECCIÓN dentro del documento correcto.** El bot tuvo servidos EN LA MISMA PASADA el §5.4
AVANZADO (rango 1) y el §5.1 GENERAL (rango 4) del MISMO `MC-380`, y encabezó con la ruta
del §5.1 — no descartó el documento por su etiqueta: respondió desde él. Retrieval e
identidad DESCARTADOS por dos vías independientes.
· **La hipótesis intermedia de propagación de identidad (s304) MURIÓ en el dúo**, y con
razón triple verificada: mi instrumento paginaba sin `ORDER BY` (perdía 12-21% de los docs
por pasada — cifras 57%/1.112 RETIRADAS); medía coincidencia-de-etiqueta cuando la pregunta
es ALCANZABILIDAD (la granularidad de familia es deliberada); y la identidad SÍ llega por
el seam 2 doc_map-aware + `series_registry` — que para ESTE caso declara la serie Vesta
desde s63/DEC-043. Instrumento v2 corregido: residual 4,1%/55 ids, casi todos `unresolved:`
(candidatos que el catálogo declara no consumir). **No hay lever ahí.** DEC-185.
· ⚠️ **s305 — «el techo NO es del MODELO»: EN REVISIÓN desde s320c (12-ago), NO citar como
settled.** Lo publicado (Sonnet 4.6 / Sonnet 5 / Opus 5 = 0/3 firmes los tres, máx 2/5) **no
procede del juez**: el script sumaba sobre las CLAVES del dict que devuelve `judge_conveyed21`
⇒ constante 2 en las 9 reps de los 3 brazos, `oracle_firme` 0 por construcción, veredicto
infalsable — ni la guarda del control podía dispararse (TECH_DEBT #75). Re-juzgadas con el juez
canónico las respuestas que el recibo sí guardó: **sonnet-4-6 2/3 firmes · opus-5 2/3**,
correlación 9/9 entre «firme» y la aparición literal del valor ⇒ **cae «TECHO CONFIRMADO»**, y por
la lógica del propio script (control alcanzable) lo que queda es **«MONTAJE NO COMPARABLE» /
INCONCLUYENTE**, NO «el techo era del modelo» — con n=3 por brazo el eje modelo nunca tuvo
potencia (p≈4/9 ⇒ P(0 de 3)=0,17). **DEC-173 NO cae**: su recibo (s293) es medición válida y lo
que hay es tensión empírica 2-ago vs 7-ago con el mismo control (lower bound: respuestas truncadas
a 1.500 chars, corrida del 7-ago).
**Re-medición fresca CERRADA** (`evals/s320c_techo_modelo_ab_v2.json`, 5 reps/brazo, 0 votos de
juez fallidos): **los TRES brazos ALCANZABLES** — sonnet-4-6 **1/5** firmes · sonnet-5 **1/5** ·
**opus-5 4/5**, max 5/5 los tres ⇒ el script dispara **MONTAJE NO COMPARABLE**. Lo que deja: (a)
el hecho **sí es alcanzable hoy** ⇒ el «NO alcanzable» de DEC-173 no describe el sistema actual y
su corolario «la pair-completion NO pagaría» queda **contestado**; (b) la clase real es
**transmisión INESTABLE** (6/15 firmes con evidencia perfecta), no «techo»; (c) `base`=0/5 en 14
de 15 ⇒ el hueco es de **serving**; (d) opus-5 4/5 vs 2/10 apunta a eje de modelo **sin
establecerlo** (Fisher agrupado p=0,089 — el diseño nunca tuvo potencia). Caveat: 3 de 15 reps con
canal degradado (fail-open) y las 3 dieron 0/5 ⇒ no es freeze-contract limpio. Hasta el dúo: la
clase «elemento vecino» NO está cerrada por el eje modelo y el ítem 2 del packet B2 no se
adjudica. Recibos: `evals/s320c_rejudge_s305_stored_v1.json` · el roto
`evals/s305_techo_modelo_ab_v1.json` se conserva como prueba. DEC-186 pendiente de reescritura.
· **TECH_DEBT #64 RESUELTO** (PR #215): el generador ya puede cambiar de modelo
(`temperature` aprendida en runtime ante rechazo + bloque de texto por tipo con
equivalencia histórica exacta — mi 1ª versión rompió 29 tests por ser más estricta que el
código viejo; lección estampada).
· **TECH_DEBT #63 RESUELTO** (s306, PR #216, dúo 8/8 confirmados 0 FP): el fail-open de
canal registra en el seam s289 extendido (4 canales), reintento único ante 5xx del RPC de
enunciados, sección `retrieval` TRI-ESTADO en `rag_trace` (sin sección / `measured=false`
seam-no-conectado / `measured=true`+lista — el dúo convergió en que mi v1 colapsaba «sin
seam» a «sano», el defecto reintroducido una capa arriba) + vista `salud_canal_retrieval_v1`
+ test-ancla del seam en los adapters de producción. **Alberto tras el merge: aplicar la
migración `20260807120000_s306` en el SQL Editor.**
· **s307 (mismo día, PR #218): 2º y 3º datos orgánicos de Alberto** — intro stale (3
marcas de 30) e inventario-desde-ventana-RAG (Securiton sin ASD535). Lote: textos
derivados de datos vivos (texto legal v7 INTACTO, pin sha256; su línea viaja en el bump
v8) + ruta de inventario por fabricante (document_id, acotada, estrecha, 30/30 marcas
verificadas en vivo). El dúo tumbó mi v1 con 4 CRÍTICOS (13/13, 0 FP — n=1
confirmatorio otra vez, cap de PostgREST, límite de Telegram, colisión con «lista de
averías»). La telemetría s306 estrenó filas measured=true con los turnos de Alberto.
Deudas nuevas: #65 documents.product_model stale · #66 prosa del 👎 como consulta ·
#67 alias cortos. DEC-188.
· **s308-s313: los CINCO GO de Alberto ejecutados** — deudas #65/#67 + swap a Opus 5
(CONFIRMADO en prod: Railway 12:52 UTC) + blueprint L1→L2c COMPLETO con dúo por lote
(L2a = NO-GO por medición DEC-189; contrato 6→4 excepciones; sello +4 entradas; registro
de 91 flags como invariante) + packet B2 v3 (dúo doble, mergeado — sentada DESBLOQUEADA).
**Blueprint CERRADO (s314, DEC-191, PR #226): L3 NO-GO por medición** — el pre-flight
DEC-189 sobre `embed.py` halló 4 pins vivos en preregs s117 (sha coincidente; el replay
del audit m26 moriría fail-closed) → se ancla y declara; E2 queda con trigger. Balance
final: L0 ✓ L1 ✓ L2a NO-GO L2b ✓ L2c ✓ L3 NO-GO. De la cola de GOs: ingesta
Tyco/Hikvision/Dahua/Ajax (espera respuesta de Alberto: ¿OneDrive o portales? — para
Kidde la respuesta fue Casmar, ver bloque 10) y reacciones Telegram. DEC-189/190.
**(10) s314 — lote Casmar/Kidde + la 4ª instancia de la clase identidad (DEC-192).** La
pregunta orgánica de Alberto (manual instalación NC-PF2) disparó: harvest Casmar
reproducible (94 SKUs, 266 PDFs, `form_id` obligatorio) → cruce → 104 gaps → dúo
(11/11 confirmados, 0 FP) → ingesta en 2 etapas (74 docs, 1.091 chunks, ~$60, 0 fallos,
reanudabilidad estrenada) → **hallazgo: el manual YA estaba (`bcn-3100017`, pm=`NC`
invisible para «NC-PF2» — FINDABILITY, clase hp011#2/DEC-176)** → fix de identidad
pm=lista-con-barras (nuevos + bcn + 5 hojas de familia + 2 docs KIT 2X-AT) → sonda
0/5→**5/5 a evidencia** → re-cruce final **104→1 residual declarado**. Corpus: 26.215
chunks · 1.243 documents · Kidde 103 · Excel reconciliado (`--data-root`).
Traza: DEC-176 (origen) · DEC-185..192 · HISTORY s303-s314; frentes 6-8: DEC-182.

---

## Estado anterior (s293 — 2 ago 2026)

**PRODUCCIÓN**: sin cambios (L2 `OBLIGATION_WARNING_APPENDIX` vivo; etapas 1-2 completas;
OK 115/131, 88%). **s293 no cableó NADA**: cerró 2 de los 3 levers vivos de etapa 3 con
medición, no con código (DEC-172).

- **hp017#2 = NO-GO y RE-CLASIFICADO a DOS causas.** El conflict-guard sí suprime la mitad
  «ruta» (causal medido: PRE-guard 3/5 → POST 0/5, juez canónico K=5) pero la mitad «borrar la
  Regla 1» el modelo **no la escribe** (0/3 reps, 5 marcadores con paráfrasis) ⇒ **ni con el
  guard perfecto llega al umbral firme**. El residual es omisión de síntesis = otra clase.
  El lever de span-repair además **abría** un agujero de seguridad (línea redactada que
  conserva su cita + aviso que mapea fragmento→valor ⇒ el lector reconstruye el número).
  Dúo 15/15 confirmados, 0 FP, crítico.
- **cat017#2: probe $0 de lanes CERRADO** (el paso que DEC-169 dejó pre-declarado). Ninguna
  lane existente trae el carrier `4c186fb2` (pool rank 18): `facet_complement` ya detecta la
  necesidad «licencia» y la da por satisfecha con el chunk **puntero** («Consulte…
  4188-1125-ES»), mientras el dato vive en el documento referenciado. Lever B (referencia
  gobernada, pool-only, sin fetch nuevo) diseñado a nivel de mecanismo, **no construido**.
- **Daño cualitativo documentado**: el guard borra un procedimiento de 3 pasos por un número
  dudoso. Sin retorno en métrica, pero es coste de usuario y queda escrito.

- **CRIBA DE ALCANZABILIDAD (DEC-173, procedimiento nuevo en el Protocolo 4)**: antes de
  diseñar un lever de serving/síntesis se mide si el hecho transmite **con la evidencia ideal
  delante** (oráculo + juez K=5, ~$1/hecho). Veredictos: **ALCANZABLES** `cat017#2` (0/5→5/5)
  y `hp003#4` (0/5→5/5); ~~**NO alcanzables** `hp017#2` y **`hp011#2`**~~ **← LOS DOS CAÍDOS
  (s321)**: `hp017#2` nunca se sondó de verdad (0/5→**5/5 en 3/3** al servir el carrier de la p43) y
  el 0/5 de `hp011#2` caducó (s320c: tres brazos alcanzables) ⇒ el «la pair-completion **no
  pagaría**» queda **CONTESTADO**, pendiente de censo de población.

**Qué sigue (nada bloqueado, y ahora con retorno DEMOSTRADO o descartado por hecho):**
(0) **L3 v2 PARADO (s294/DEC-174, opción A de Alberto)**: el gatillo llegó a 98,3% de precisión
en adjudicación ciega, pero shipearlo exige 2 cambios en la lane L2 viva (política de idioma +
dedup por contención) para 1 hecho — y el propio requisito bilingüe crea un duplicado
cross-lingüe en la diana. Quedan 2 defectos latentes de L2 documentados. **Lever B de `cat017#2` = NO-GO por POBLACIÓN** (DEC-175): alcanzable (5/5) pero
**1 gold de 39** y **0,13% del corpus** — el censo desmintió mi propio argumento estructural.
⇒ ~~**Etapa 3 queda CERRADA como cola de ingeniería**~~ **REABIERTA EN LA PUERTA DE POBLACIÓN
(s321)** — ver el bloque de «Estado actual» y los banners de DEC-173/175. ⚠️ Y el «0,13%» de la
línea anterior **queda RETIRADO**: DEC-184 desmontó ese barrido (de 44 ausentes, 7 reales). Lo que
resta es adjudicación de golds (tuya) + **censar la población** antes de diseñar nada. **Subproducto: lista de adquisición dirigida
por citas** — 44 CANDIDATOS (⚠️ s302/DEC-184: adjudicados = 7 reales; el resto ya estaban en
corpus con otro nombre o eran refs de pieza) que nuestros manuales citan (77 citas), concentrados en
Notifier/Morley ID50/ID1000: tenemos el manual de instalación y falta el de PROGRAMACIÓN, que es
donde vive el detalle que pregunta un técnico (`evals/s294_citation_gap_v1.json`);
(1) **hp003#4** = el lever vivo que queda de etapa 3;
(2) **lever B de cat017#2** si Alberto lo abre (toca lane viva en release C1 ⇒ dúo + flag-off
+ gate de no-desplazamiento); (3) **sentada B2 de gold-review** (packet: hp006#2 · hp008#4 ·
cat018#2-split · meta-ref cat020#2 · hp001#2 · gold hp002 «de Detnov» · ~~**nuevo: hp017#2, cuya mitad «Regla 1» decide si el hecho es
alcanzable**~~ **RESUELTO (s321): ES alcanzable, 3/3 firmes a 5/5 al servir el carrier de la p43**); (4) hp011#2 re-cablado espera diseño;
(5) bandeja Alberto: QA-30 v4 · tramos P-C · DROP de 8 backups s285-s287 · B1 entity-linking ·
B3 juez (~sept) · B4 follow-up de 👎. Traza: DEC-172 + HISTORY s293.

---

## Estado anterior (s292 — 2 ago 2026)

**PRODUCCIÓN**: L2 (`OBLIGATION_WARNING_APPENDIX`) VIVO y verificado en query real
(`query_logs` 19:41Z: aviso de seguridad + apéndice). Etapas 1-2 completas; OK 115/131 (88%).

**s292 cerró — etapa 3 DIAGNOSTICADA y repartida (DEC-171):**
- **Los 9 synth estables = 4 clases**: 3 levers vivos (hp003#4 hueco de léxico · hp017#2
  supresión por conflict-guard · cat017#2 recuperado-no-servido) · 1 gold-split (cat018#2) ·
  1 re-cablear (hp011#2) · 2 gold-review (hp006#2, hp008#4) · 2 techo (hp013#1, hp017#1).
- **Hallazgo transversal ACOTADO**: signature-check $0 = 1/10 (solo cat017#2) ⇒ el «rerank 0»
  del FULL se sostiene.
- **L3 NO-GO como diseñado** (dúo 13/13, 0 FP): `atom_good_form=False` lo haría no-op y el
  seam obvio explota a serving (la lane L2 viva). Nada cableado; v2 con lista de tareas.
- **Pin del sub-agente → Opus 5** (Alberto; crédito Fable agotado). Cross-model intacto.

**Qué sigue (nada bloqueado, todo con recibo):** (1) **L3 v2** si se retoma — seam
por-parámetro + lista cerrada de imperativos + guard de span + vara ciega + censo
out-of-sample + ES/EN; (2) **hp017#2** (conflict-guard) y **cat017#2** (probe $0 de lanes) =
los otros 2 levers vivos; (3) **A3 / perfil c1_v5** (gate de outcome, paquete ON #2);
(4) **sentada B2 de gold-review** (packet: hp006#2 · hp008#4 · cat018#2-split · meta-ref
cat020#2 · hp001#2 · gold hp002 «de Detnov»); (5) bandeja Alberto: QA-30 v4 · tramos P-C ·
DROP de 8 backups s285-s287 · B1 entity-linking · B3 juez (~sept) · B4 follow-up de 👎.
Traza: DEC-171 + HISTORY s292.

---

## Estado anterior (s291 — 2 ago 2026)

**PRODUCCIÓN**: sin cambios desde los ONs de etapa 2 (query real en query_logs 16:02Z ✓).

**s291 cerró — HITO DEL FULL v3.2 + lever L2 construido (DEC-170):**
- **FULL 39 bajo v3.2** (GO Alberto): **OK 115/131 (88%) · synth 12 · rerank 0 · retrieval 2
  (centinela+techo) · corpus-gap 2 (cat013×2 FN conocidos)**. Etapas 1-2 COMPLETADAS
  corpus-wide; cascada medida (hp013#1 retrieval→synth). vs v3.0: +14 OK (serving real +
  honestidad v3.2, empaquetado declarado). via_coverage_append=14 facts.
- **Cola etapa 3 = 9 synth estables**: cat017#2 · cat018#2 · hp003#4 · hp006#2 · hp008#4 ·
  hp011#2 · hp013#1 · hp017#1 · hp017#2 (hp009 centinela fuera).
- **L2 `OBLIGATION_WARNING_APPENDIX`** (hp002#4 SEGURIDAD): construido default-off tras dúo r2
  (14 resoluciones) + V1 medido; suite 3426/0. **ON gateado por G-FP de amplitud** (~$5,
  recibo por-fila) + G-directed — pendientes.

**Qué sigue:** (1) **G-FP + G-directed de L2** → paquete de decisión ON a Alberto;
(2) **etapa 3 sobre los 9** (diagnóstico por sub-motivo con patrón refutador s290 → levers
con dúo); (3) A3/perfil c1_v5 (lane hyq ON, centinela hp009); (4) bandeja Alberto: QA-30 v4
· tramos P-C · DROP backup (smoke Telegram ✓ 1-ago: texto completo 2 msgs + álbum 4/4
adecuado = VISUAL_ASSETS_REGISTRY verificado vivo).

**Backlog adjudicado (Alberto 1-ago, «atacar después» — orden tentativo tras etapa 3):**
- **(B1) Entity-linking / relaciones del catálogo gobernado** (clase cat013 cross-family:
  protocolo CLIP, componentes/OEM compartidos): GENERALIZABLE — capa de consumo del activo
  s83 (pieza F), `relations.jsonl` ya en esquema; consumida por family-filter del serving Y
  crédito del instrumento (patrón puente doc_map v3.2). Diseño con dúo cuando toque.
- **(B2) Sentada de gold-review** (packet a preparar para adjudicación de Alberto):
  meta-ref cat020#2 (valor→«específicos de la versión España» + la referencia al manual de
  variaciones pasa a expectativa de CITA) · afilar `texto` de hp001#2 «1111» (sin tocar el
  valor — reduce fragilidad del juez) · + los 2 cat013 si B1 no los resuelve antes.
- **(B4) Follow-up de 👎 en Telegram** («¿qué falló?» con botones → caso diagnosticable;
  idea de Alberto 1-ago): integrado en TECH_DEBT #60 punto 5 — va en el paquete
  pre-técnicos, trigger ANTES del primer técnico real.
- **(B3) Juez: NO cambiar ahora; revisar en el re-baseline del eval orgánico (~sept).**
  Cambiar el primario a Opus 5 rompería la propiedad CROSS-VENDOR (Claude genera / GPT
  juzga = anti-echo-chamber deliberado, DEC-023) además del freeze de comparabilidad; el
  ruido-de-juez hoy es ~1-2 hechos (no dominante). Vía barata si se quiere mejora antes:
  subir el SECUNDARIO del dual-rescue (Opus 4.8→5) re-validando la suite balanceada s100.
Traza: DEC-170 + HISTORY s291.

---

## Estado anterior (s290 — 1 ago 2026, tarde)

**PRODUCCIÓN**: PR #191 MERGEADA + los 2 flags de etapa 2 ON en Railway (Alberto, mediodía).
Smoke Telegram pendiente de su primera query real (verificable en query_logs).

**s290 cerró — foto post-etapa-2 + diagnóstico de etapa 3 + instrumento v3.2 (DEC-169):**
- **Foto** (mapa-10 N=2, flags ON): rep1 OK 27/33 · hp002 5/5 OK con el aviso p.121 apendizado
  por la reserva = Fix B vivo en la ruta del instrumento. Estables: cat017#2 (omitted),
  cat017#4 (→ FN del instrumento, ver abajo), hp009#0 (centinela), hp013#1 (techo).
- **Diagnóstico etapa 3** = workflow 4 misiones judge-free + refutador POR misión (8 agentes,
  2 anclas falsas cazadas + hallazgo del 2º carrier) + dúo r1 (Sol 6 + Fable 7, 0 FP):
  cat017#4=FN instrumento · hp002#4=discrecionalidad+bind_atoms-ciego (brazo determinista =
  hipótesis sobre población distinta del NO-GO MP_SERVED_BINDING 24/105, gate FP obligatorio)
  · cat017#2 NO-techo (2 carriers, recuperado-no-servido + crédito de familia) · hp009#0
  centinela fuera de cola. Brief: `evals/s290_etapa3_diagnosis_v1.md` v1.1.
- **Instrumento v3.2** (un corte de serie): votos por-id servidos + dual-rescue en el eje
  servido/append (asimetría cerrada) + puente familia doc_map (join gobernado) + pool_ids.
  Gate 3/3 expectativas: cat017#4→OK (las 2 dianas de etapa 2 convertidas DE VERDAD) ·
  cat017#2 sin OK-falso · hp009 intacto con puente inerte.

**Qué sigue:** (1) **FULL de 39 bajo v3.2** = cola real de etapa 3 (~$23, gate de gasto);
(2) diseño L2 (hp002#4 determinista con gate FP pre-registrado tipo DEC-134-P3 + brazo
prompt/header) — construible flag-off en paralelo; (3) probe $0 de lanes existentes para
recuperado-no-servido (L3a) DESPUÉS de dimensionar con el full; (4) A3/perfil c1_v5 (lane hyq
ON con centinela hp009); (5) bandeja Alberto: smoke Telegram + QA-30 v4 · tramos P-C · ONs
telemetría + D9 · DROP backup. Traza: DEC-168/169 + HISTORY s289/s290.

---

## Estado anterior (s289 — 1 ago 2026)

**PRODUCCIÓN**: sin cambios de release (la de #189 sigue viva). Rama de sesión
`claude/s289-etapa2-order-fixes` (desde `claude/s288d-pretecnicos-note` = main + TECH_DEBT #60)
— TODO lo de s289 default-off; el ON de los 2 flags nuevos = decisión de Alberto vía PR.

**s289 cerró — ETAPA 2 EJECUTADA (DEC-168)**: los 2 fixes de orden/fallback de DEC-167(b)
construidos flag-off byte-invariantes + gateados con cadena ligada por hash:
- **Fix A `FACET_COMPLEMENT_FALLBACK`** (fallback de attestation, orden total, firma histórica
  preservada) → **cat017#4 miss-stable→conveyed-stable, atribuido A-only**.
- **Fix B `OBLIGATION_RESERVE_ORDERED`** (filtros POR-GRUPO tabla/marcador-huérfano en
  `_warning_span` + orden v2 sección-con-intención>blockquote>pool-rank; la escalada v2
  pre-declarada disparó por dato — trigger preservado) → **hp002#4 miss-stable→flip en
  ventana-mala** (el portador p.121 SE SIRVE; residual = síntesis) · ventana fresca
  auto-resuelta por rerank (variance DEC-096b).
- Gates: **G-1 sweep-39 5-brazos** sobre captura congelada (réplica-OFF limpia; 9 golds
  cambian, 8/9 = B puro) · **G-2 por-fila 339f06e0** inocuo (recibo formal) · **G-3 pareado
  per-fact PASS: 0 regresiones en 39 facts** (+2 bonus flip→stable) · suite 3419/0.
- **Observabilidad DEC-167(c)**: fail-open del canal VECTOR con log+traza (era el único
  silencioso) + `channel_health` en el seam `_trace`.
- **Dúo r3 pre-build + r4 focal post-gates** (Sol 5+6 hallazgos, 0 FP; Fable 8): 2 cazadas de
  la clase «validado-vs-visible»; freeze-binding + atribución por flag + selección≠conversión
  incorporados. Tallies 00:06/01:44. Coste sesión ≈$9-12.

**Qué sigue:** (1) **PR de la rama s289** (incluye s288d) + decisión de Alberto sobre los ONs
(`FACET_COMPLEMENT_FALLBACK` + `OBLIGATION_RESERVE_ORDERED` en Railway; rollback = quitar la
variable); (2) **etapa 3 síntesis** (13 estables; ahora también el residual flip de hp002#4
en ventana-mala) sobre serving estable + re-baseline bvg vs 11/16/12; (3) **A3 / perfil c1_v5**
(lane hyq ON: eficacia cat010/hp012 + centinela hp009 + estrictez per-arquetipo); (4) bandeja
Alberto: QA-30 v4 · tramos P-C · ONs Railway + paste D9 · DROP documents_backup_s288_pa;
(5) lane inventario/catálogo. Traza: DEC-168 + HISTORY s289.

---

## Estado anterior (s288c — 31 jul 2026)

**PRODUCCIÓN**: PR #189 MERGEADA (31-jul) → Railway despliega s287→s288b: todo default-off SALVO
**P1 corpus-aware, VIVA sin flag** (incondicional bajo `replace` del perfil C1; nota de release
tardía declarada en DEC-167; re-medición = mapa re-anclado, neto +4 OK / retr 4→0 / 1 regresión
hp002#4). Rama `claude/s282-h0t2-qa` acumula ahora solo s288c (post-merge), pendiente de PR nueva.

**CAMPAÑA upstream→downstream (mapa canónico DEC-163, instrumento v3.1 N=2)**: etapa 1
retrieval con residual ÍNTEGRAMENTE atribuido (cat010#0/hp012#3/hp013#1 → A-core; hp001
judge-fragile; hp009/hp010 pendientes de medir bajo P1) · etapa 2 rerank en 2 estables con
mecanismos nombrados · etapa 3 síntesis (13 estables) ESPERANDO serving estable (A-core) —
orden de Alberto: infraestructura antes de síntesis.

**s288 cerró — A-CORE ejecutado hasta la bandeja de Alberto** (spec normativo único
`evals/s288_acore_design_brief_v1.md` v3 SELLADO; dúo r1 Sol+Fable + r2 Sol focused = 18/18
hallazgos confirmados, 0 FP; DEC-165): (a) **F0 census v2** determinista 2× — H1 CONFIRMADA
60/60 (extraction_sha256 == sha de bytes del PDF; 1.334 blobs locales censados, dual-key 1.012
docs), partición 1169/1169, colisiones 0; (b) **F2 lane doc_scoped_hyq endurecida** — scope por
document_id vía embed FK (name-scope muerto), tier blob-verificado ANTES de navegar (6/6 cero
holgura), dup excluidos, suite 3393 passed + smoke embed real PASSED (lane sigue OFF);
(c) **P-A staged**: 585 docs placeholder→sha real (`evals/s288_acore_pA_apply_v1.sql`,
--verify 16/16 PASS live, dry-run, rollback) — PASTE DE ALBERTO pendiente; (d) **P-B gateado
como debía**: detector idioma v3 (clase diagram-heavy cazada: anotaciones EN del extractor →
FIX 3 limpieza de input; calibración 100,0% 389/389; 2 backfills erróneos evitados), cohorte
406 {es 307, en 99}, **QA-30 v3 = adjudicación de Alberto (30/30-o-HALT)**; (e) **P-C
re-diseñado a TRAMOS** (2 rondas de Sol tumban bulk-verified; semántica canónica intacta;
ritmo de Alberto; el GO de A-core NO depende de ello); (f) P-D ELIMINADO (join-through FK).

**F3 CERRADO (30-jul tarde, paste P-A de Alberto aplicado)**: delta live exacto al
pre-registro (placeholders 744→159 · binding_ok 414→999 · P-A elegibles →0 = gate
aplicado==100%) · probe cohorte: **hp012 mecanismo CONFIRMADO** (lane sirve 15088SP
p.108+p.151 con las facetas de la aguja) · cat010 = archetype None (diana del lever
taxonomía) · hp013 baseline confirmado. Addendum F3 en DEC-165.

**s288b (31-jul): lever ontología hyq EJECUTADO (DEC-166)** — la lane adopta el par
retrieval-v4+evidence-v5 con barrera query-card; 7/7 gates $0; **cat010 convertida en
MECANISMO** (intrinsic_safety, 2 parents con valores IS); entradas 17→21; residuales
declarados (estrictez per-arquetipo → gap A3; hp009-centinela). Dúo s288+s288b: 34/34, 0 FP.

**s288c (31-jul): pieza 3 de etapa 2 RESUELTA en diagnóstico (DEC-167)** — cuota-por-faceta
CERRADA como familia (2 diseños tumbados en dúo, 31/31 confirmados 0 FP); probe serve-rate 0/6
committeado; mapa re-anclado 10 golds P1 (OK 22→26, retr 4→0, regresión única hp002#4 SEGURIDAD);
**etapa 2 HEAD = {cat017#4, hp002#4}, ambos mueren por orden/fallback en lanes EXISTENTES**
(document_local `bucket[0]`-sin-fallback · obligation_warning primer-match) — diagnóstico $0 con
funnel exacto (`evals/s288c_gate_diagnosis_v1.md`). Colaterales: CI fix Linux del instrumento ·
matcher attestation sin stemming (TECH_DEBT #59) · pool ventana-dependiente.

**Qué sigue:** (1) **los 2 fixes quirúrgicos DEC-167** (diseño → dúo r3 → build flag-off →
gates: sweep-39 + por-fila `339f06e0` + dirigido pareado ~$2-4) + **pieza observabilidad**
(salud/fail-open por canal en traza + recibos de estabilidad committeados); (2) **etapa 3
síntesis** (13 estables) sobre serving estable + re-baseline bvg vs 11/16/12; (3) **A3 / perfil
c1_v5** (lane hyq ON: eficacia cat010/hp012 + centinela hp009 + estrictez per-arquetipo);
(4) bandeja Alberto: QA-30 v4 (30/30-o-HALT → staging P-B) · tramos P-C · ONs Railway + paste D9
· PR nueva del tramo s288c; (5) lane inventario/catálogo. Traza: DEC-163..167 + HISTORY
s288/s288b/s288c.

## Estado anterior (s286 — 29 jul 2026)

**PRODUCCIÓN**: sin cambios de release (C1 + MT F0+F1 vivas; DDL `convo` sigue gateado por matriz
RGPD). La rama `claude/s282-h0t2-qa` acumula s282→s286 lista para PR/merge.

**BASELINE v4 = LÍNEA DE SALIDA DEL OBJETIVO: 11 PASS / 16 PARCIAL / 12 FALLO** (39 golds,
ship-config completa, `judge_vara=v4` en todas las filas — DEC-162d). **Descomposición pareada**
(mismas respuestas, mismos golds, letra v3): 10/25/4 ⇒ la vara explica +8 de los +9 FALLO vs
s284; residuo real +1; v4 PASA una más que v3 (SUPP ya no degrada). **OBJETIVO (Alberto 28-jul):
FALLO→0** (salvo techo DEC-158: cat022/hp012-retr) **y PARCIAL≤10**, vara v4 CONGELADA durante
el arco, solo palancas BP/estructurales, golds no se ablandan sin adjudicación.

**s286 cerró**: (a) SEGURIDAD hp018 — guard A'+C' shippeado default-off (A/B ciego 10/10→0/20,
0 supresiones; DEC-162a); (b) tachados `~~` ejecutados en DB (907 filas, 0 mismatches) + 2 fugas
de dedup cerradas + t.Fi patch; (c) vara v4 (T2b) con adjudicación sellada; (d) conducta medida
(follow-ups 10/10→0/12 · direct-first · listing-gate · fix parser diagramas); (e) telemetría
CONSTRUIDA (dúo 18 hallazgos/0 FP → `answer_feedback` + vistas salud + digest + 👍/👎; paste D9
pendiente); (f) bug juez MT gold-en-blanco (fix; re-medición e2e pendiente bajo v4). Suite
3308/0. Composición del gap: FALLO real = 10 (2 = techo DEC-158); buckets = CORE-facts perdidos
(14 PARCIAL + ~5 FALLO) · identidad/variante (hp009/hp018/cat011, conecta con split ZXe/ZXSe
D1-identidad) · conducta fina (cat013/hp004/cat015) · invención (cat020).

**Qué sigue:** (1) **full del assessment nivel-hecho** (EN CURSO al cierre, ~$23) → estampar
scoreboard + verificar corpus-gaps a mano → elegir palanca del bucket-1 con evidencia (gate
primero, delta en eval, dúo antes de cablear); (2) lever loop por buckets hacia FALLO→0 /
PARCIAL≤10; (3) lane inventario/catálogo («¿qué productos tienes de X?» — dogfooding Detnov/
Kidde); (4) lote de Alberto (paste D9 · re-accept TERMS v2 · ONs con runbook · D1-D11 ·
merge PR); (5) re-medición e2e MT bajo v4. Traza: DEC-162 + HISTORY s286.

## Estado anterior (s285 — 28 jul 2026)

**PRODUCCIÓN**: release C1 viva (#184, perfil `coverage_c1_v4` + identidad `replace` + Evidence
Contract) **+ multi-turn Fase 0+Fase 1 vivas** (#185/#186; `ORCHESTRATOR_PATH=on` +
`CONVERSATION_POLICY=impl`, carry-forward verificado en `query_logs`; rollback = quitar
variables). DDL schema `convo` sigue **NO aplicado** (gateado por matriz RGPD).

**Baseline oficial v3 de los 39 golds: 16 PASS / 20 PARCIAL / 3 FALLO** (DEC-160; **vara v3** =
juez con ventana completa tras el fix del bug [:3000] que llevaba desde 28-may; paridad de flags
harness↔Railway obligatoria [DEC-157]; gate de no-regresión F1 apunta aquí). Juez GPT-5.5 NO se
cambia (s47 vigente). Fact-level 146/154 sin movimiento.

**CAMPAÑA H0 DE IDENTIDAD EJECUTADA EN DB (s285, DEC-161)**: T3 (20 UPDATEs / 221 chunks, 26
adjudicaciones de Alberto, 2 docs basura eliminados) + T2 (backfill s83: 533 `doc_type` + 301
`language`, verificado 1:1 en vivo, 0 sobrescrituras). **Chunks `unknown` activos: 318→1.**
Cifras vivas: 1.169 docs (996 active) · 25.088 chunks_v2. El catálogo canónico saneado
(vsn-rp1r-plus2 + retirada de aliases-propiedad) subió cat009 PARCIAL→PASS. Cola de calidad
s283 cerrada ítem a ítem (DEC-157/158/159: cat016 resuelto · cat022+hp012-retr techo-declarados
· hp011+hp012-framing aparcados-en-datos).

**Qué sigue:** (1) **PRIORIDAD-1 SEGURIDAD hp018** — generación intermitente de «sirenas en
serie» (DEC-160c): traza + frecuencia + guard con dúo; (2) **lote de decisiones de Alberto**
(sin prisa, en su orden): sentada goldreview-r2 (`evals/s284_goldreview_r2_packet_v1.md`) ·
121 conflictos QA · semántica tachados `~~` (desbloquea hp011) · P2 chunk 2113ac69 · firma T1
lineage (5 docs) · matriz RGPD · visto DDL · GO paquete telemetría (#3+#4) · abrir PR de la
rama s282 (acumula s282-s285) · borrar 2 huérfanos Storage (opcional); (3) mejoras 5.1/5.2
(gating de visual assets en preguntas genéricas · «También puedo ayudarte» A/B) + dogfooding.
Traza: DEC-148..161 + HISTORY s277-s285.

## Estado anterior (S277 — 22 jul 2026)

### Cierre operativo de la P1 fresca y handoff

**C1 continúa NO-GO.** El run sellado `p1-v3-b92ff51-20260722a`, sobre commit
`b92ff51e5af180352366158614ca83f7fdfc186d` y tree
`de347f6add8ae1a5fe9a9514a5d077af8b55b66d`, completó **27/27 réplicas y 81/81 llamadas**
por **2,69369748 USD**, con cero mutaciones Railway/Supabase, fence cerrado y
manifest/fingerprint pre/post idénticos. `final.json` es autoritativo:
`P1_NO_GO / NO_GO_PROTECTED_CONTRACT`, `release_deployed=false`.

Tres runs v2 previos de la misma tanda terminaron a 17/27 (`511bd58`, `b131464`, `eefc388`) por
1,70976360 + 1,81440744 + 1,82350344 USD. Los cuatro runs locales suman **8,04137196 USD** y
reserva desconocida cero; este subtotal no sustituye la reconciliación completa del techo
acumulado de 100 USD antes de otra llamada.

La adjudicación ciega resolvió **91 ítems semánticos: 62 PASS / 29 FAIL**. A nivel de respuesta
completa son **10/27 limpias y 17/27 con al menos un FAIL**. El antiguo “18/27” describía
respuestas persistidas por una P1 abortada, no 18 respuestas PASS. No existe `P1_PASS`, no se
bancan facts y el marcador sigue **146/154 (94,81 %), gap +5**.

La causa ya no se trata como “sólo síntesis”: parte de los 29 FAIL carece de la fuente correcta
en el contexto servido —identidad/orden en hp018, catálogo INSPIRE en cat017, reserva del warning
en hp002 y autoridad/source-card de prosa en cat019—; el resto son omisiones compuestas,
atribución/conflicto o cita local sobre evidencia ya servida. La rama de handoff conserva tests
que demuestran la semántica necesaria de una futura política `replace` y un preflight offline
exacto; no cambia runtime. El runner y `retriever.py` históricos siguen sellados en `add` y sin
el nuevo orden hasta versionar schema/config/prereg e implementation hashes. Aún no hay un
candidato integral ni un Evidence Contract implementado.

**Único qué-sigue operativo (DEC-148/149, s278):** gobernanza simplificada (Alberto); `b92ff51`
baseline inmutable; sin gate de receipts ni P1 ceremonial. **HECHO s278 (DEC-149, rama
`codex/s277-c1-release-integrity`):** census ($0, adversarial-CONFIRMADO) · diseño vNext v2
dúo-hardened (`evals/s278_vnext_design_v2.md`) · implementación completa offline — guard+quarantine
identidad, order/autoridad `content_search`, perfil `coverage_c1_v3`, reserva hp002, **Evidence
Contract v1 quirúrgico** (10/10 réplicas objetivo, colateral 0, dev-check 14/15; techo postgen
real 15/29), seals re-anclados (suite **2907/0**), migración RLS PREPARADA sin aplicar, INSPIRE §2a
gobernado, **§4 COMPLETO dúo-hardened r2** (blob-identity canónica + prose source card; el
crítico e2e del dúo = propuesta RPC v3 NO-aplicada `migration_proposals/20260722200000_...`),
**pasada harness parcial ejecutada** (8 QIDs ~$2 + brazo control v2/add: ítems P1 presentes en
vivo, controles limpios, ledger waived por Alberto). **HECHO ADEMÁS (22-jul noche, DEC-150/151):** bloque LIVE aplicado por Alberto y verificado —
**RLS #29 CERRADO** (13/13 tablas, grants anon revocados, Advisor sin clase crítica) · data-fix
×2 (7 docs identity-complete: MC-380 par + HOP-138-8ES/9ES + 4188-1132-ES + MS-416 par) · RPC
v3 canónico aplicado + flip Python · 4 adjudicaciones de catálogo aplicadas (quarantine VACÍA) ·
smoke: cat017/cat019 sirven su doc por primera vez. **DECISIÓN B de Alberto: release RETENIDA**
hasta cerrar la ronda estructural del selector (diagnóstico medido: overflow por-scope
sistemático + elegibilidad por-faceta + ontología de facetas). **QUEDA:** (a) diseño v2 de las
3 compuertas (v1 → dúo: C1 sólida-con-cambios, C2/C3 NO-sólidas — adjudicación
`evals/s278_selection_reach_duo_r1_adjudication_v1.yaml`; insumos v2: cap por-vía, fork
versionado de facetas, presupuesto propio estilo reserve, truncado combinado, prereg de regla,
census obligatorio) → dúo r2 → build; (b) pasada final completa 13 QIDs+controles (~$3) →
lectura de Alberto → merge #184 (= flip `COVERAGE_RELEASE_PROFILE=coverage_c1_v3` +
`IDENTITY_RESOLVE_POLICY=replace` + retirar flags-hoja en Railway, checklist diseño §7) =
release; después DEC-136 (multi-turn). Histórico:
[`docs/HANDOFF_P1_B92FF51_2026-07-22.md`](HANDOFF_P1_B92FF51_2026-07-22.md) (§9 SUPERADO).

**Multi-turn/multi-hop sigue `NOT_BUILT` y separado bajo DEC-136.** El Evidence Contract debe
ser reusable por el verifier futuro, pero este frente no autoriza estado conversacional, DDL,
colas ni inferencias adicionales.

### Contexto histórico anterior a la P1 completa

Los párrafos siguientes conservan la cronología que llevó al run fresco. Sus menciones a “P1
pendiente” son históricas y quedan sustituidas por el cierre operativo anterior y DEC-147.

**Marcador canónico sin movimiento desde S274: 154 facts = 146 OK · 6 synthesis-miss ·
2 retrieval-miss = 146/154 (94,81%); faltan +5 para 151 (≥98%).** Es la foto de trabajo
adjudicada; `official_atomic_kpi` sigue sin materializarse como KPI independiente. S277 no
banca facts, no cambia el denominador y no demuestra generalización.

**La observación viva cerró el recibo pendiente y mantuvo C1 en NO-GO.** La respuesta PEARL
aportada por Alberto fue una sola generación de 4.449 caracteres que Telegram dividió en dos
mensajes. No incluyó ninguno de los dos avisos F12 y afirmó un menú plano «8» sin revelar el
conflicto conocido 7-vs-8. `query_logs.response` se trunca a 4.096 caracteres, por lo que no es
autoridad sobre la respuesta completa. Resultado: el par legacy que convirtió el fact en el
probe S274 no equivale a un release C1 íntegro ni a síntesis fiable en vivo.

**Candidato de release C1 — todavía no desplegado.** La base de la PR #184 construyó el profile
atómico `coverage_c1_v1`, un seam único de serving, trazas privacy-safe y dos gates previos: A offline
prueba ensamblaje sin red; B GET-only prueba que, condicionado al prefijo congelado, el fetch
live alcanza el target PEARL en F12. A y B pasan, pero ninguno genera ni puntúa una respuesta;
por eso no autorizan release. El hash S113 se normalizó a LF para que el mismo pin valga en
Windows y Linux. S277 extendió esa base de forma aditiva a `coverage_c1_v2`, todavía sin merge ni
deploy del código. `VISUAL_ASSETS_REGISTRY` es ortogonal y el contrato P1 conserva exactamente su estado
vivo; no lo apaga como efecto lateral.

**La tercera P1 alcanzó síntesis real y cerró `NO_GO_PARTIAL`, sin mutaciones.** El run
`p1-8c7818cce1174f1ea0538028693ee515`, ligado a `b06f05c`, persistió 18/27 réplicas y
completó 54/81 llamadas antes de la parada temprana en `hp011:r1`. Coste observado:
**1,82090244 USD**, reserva desconocida cero; Railway y Supabase registraron cero mutaciones.
El fence cerró `CLOSED_VERIFIED` y el manifest/fingerprint pre/post permanecieron idénticos.
El resultado terminal es `NO_GO_PARTIAL / NO_GO_PROTECTED_CONTRACT`; no existe `P1_PASS`.

La causa de la parada mezclaba un defecto instrumental y otro real. El scorer interpretaba
cualquier substring `--` como el valor técnico especial de `r.I`; por ello confundió los
separadores Markdown `---` de la respuesta con ese estado y emitió un FAIL falso por ausencia de
`t.A`. La detección se acotó al token técnico inequívoco y el replay offline de la misma respuesta
pasa de FAIL a **REVIEW**, sin repetir ni pagar llamadas. El REVIEW sí es material: la página 63
no estaba en el pool, prefijo, fetch structural ni contexto servido. F9 procedía de una guía
rápida incompleta y la respuesta afirmó erróneamente que `00` inhibe el rearme. La inspección
GET-only descubrió además una frontera anterior a retrieval: `HLSI-MN-103_RP1r-Supra_lr` tiene
dos revisiones activas. La v.04 (2013) expresa `t.H`; la v.07 (2018), fuente de la adjudicación
gold experta, corrige el texto mediante `t.Fi` tachado y `t.A` insertado. La v.07 está parcialmente
marcada como duplicada de v.04, y la migración de reconciliación dejó su precedencia
intencionadamente pendiente. Pool coverage e HYQ no recuperaron la autoridad; ampliar búsqueda
antes de resolver lifecycle mezclaría revisiones y tampoco sería un camino honesto a GO.

**La adjudicación lifecycle quedó aplicada y verificada en Supabase.** La
migración `20260721190847_reconcile_hp011_v04_v07_lifecycle.sql` declara explícitamente que
v.07 supersede a v.04; bloquea solo los dos documentos y sus 190 chunks; exige identidades,
revisiones, hashes y topología exactos; y despeja únicamente los 38 enlaces v.07→v.04 que
ocultan parte de la revisión autoritativa. Conserva los 4 duplicados internos de v.07, los 43
enlaces históricos de v.04 y toda cardinalidad. Un rollback manual emparejado restaura las 38
parejas y ambos estados lifecycle. Se validaron aplicación, rollback exacto y rechazo con drift
en PostgreSQL embebido, además de 6 pruebas de contrato. Tras autorización explícita, Supabase
CLI 2.109.1 hizo un dry-run de una sola migración y la aplicó con exit 0. La lectura post confirma
v.04 `superseded`→v.07, v.07 `active`→v.04, cardinalidad 94/96, duplicados no nulos 43/4,
cero enlaces v.07→v.04 y p63 v.07 con `duplicate_of=NULL`; la historia registra versión/nombre y
8 statements. No hubo llamadas de modelo, deploy, cambio Railway ni gasto. El receipt es
`evals/s277_hp011_lifecycle_live_apply_receipt_v1.json`.

**El historial y la autoridad lineage v2 quedaron reconciliados y aplicados live por evidencia.**
Las siete versiones remote-only se recuperaron desde `schema_migrations.statements`; las tres
local-only, confirmadas ausentes live, se trasladaron a `supabase/migration_proposals` sin fingir
history ni ejecutarlas. Tras alinear el árbol se aplicaron normalmente las cuatro versiones
document-local `20260721210847`, `20260721220110`, `20260722013000` y `20260722014500`, sin
`migration repair` ni `--include-all`. El receipt v2 pasa **7/7 checks**, fija la lineage HP011 y
el ACL/RLS mínimo de `p1_readonly`, y liga la definición live de
`document_local_snapshot_v2` al SHA-256 LF
`19975e3784e0cd12176cbf0b246c4e0ee8a4eed008de7542d0c6d0b6c0f9a82e`:
`evals/s277_document_local_migration_reconciliation_receipt_v2.json`.

El paquete **P1 v2** sella 13 QIDs, 27 réplicas/27 generaciones y exactamente 81 llamadas a
modelos; protege 43 filas
base de peso KPI 42, la guarda hp013 y el target compuesto hp017. Incluye scorer determinista,
preregistro, límite estático conservador de **29,727 USD** bajo los tamaños preregistrados, techo duro
de **30 USD**, WAL fsync/no-retry, identidad de release, proyección semántica de configuración,
fingerprint/fence y receipts internos ligados desde input preregistrado hasta respuesta/render.
El preflight se reconstruye al ejecutar; runtime, lease y request reservado se revalidan antes
de cada send; topología/claim/lease impiden doble runner y reinicialización de presupuesto. Toda
reapertura reconstruye las 81 llamadas y sus respuestas,
revalida las 27 réplicas, exige 162 eventos WAL alternos y recompone el coste/presupuesto exacto.
El delta normativo vive en `evals/s277_c1_p1_design_v2.md`,
`evals/s277_c1_p1_prereg_v2.yaml` y
`evals/s277_c1_p1_release_config_schema_v2.json`: bootstrap `off`, target
`coverage_c1_v2`, GET document-local atestado 1:1 y ejecución completamente nueva.
**[HISTÓRICO PRE-RUN, SUPERADO POR DEC-147]** Estaba preregistrado offline, pero P1 v2 seguía
`PENDING` y no se había ejecutado.
Ya están implementados el adapter productivo y sus receipts de transporte físico, el cierre
transitivo exacto de implementación, la captura read-only de Railway, el manifest live
pre/watch/post de RPC/ACL/índices/config, el fence PostgreSQL persistente read-only operado por
IPC sin credenciales —incluido aborto explícito—, el guard PostgREST de superficie exacta y el
executor que los ensambla. El control almacenado de 0 USD confirma el conflicto hp017 en 3/3 y emite
`HOLD_PREPAID_KNOWN_CONFLICT_RISK`; nunca atribuye PASS/FAIL al candidato no medido.

La última revisión bloqueante también sella los bordes de la ventana: identidad de sesión
preasignada para abortar un `open` de respuesta perdida, artefactos vacíos/disjuntos de
credenciales e IPC, y hash del manifest post ligado al receipt de cierre.

**Frontera de seguridad corregida.** El `transaction_read_only=on` observado en el endpoint de
identidad acredita sólo ese GET; no demuestra que los POST a RPC sean transacciones read-only.
La seguridad efectiva de esos POST procede del rol `p1_readonly` con ACL/RLS mínimos, la allowlist
exacta del guard y la ausencia de funciones `SECURITY DEFINER` accesibles. En PostgreSQL 17 la
membresía debe quedar en tres grants no heredables exactos: `authenticator <- postgres` con
`SET TRUE/ADMIN FALSE`, `postgres <- postgres` con `SET TRUE/ADMIN FALSE` y el grant automático
`postgres <- supabase_admin` con `SET FALSE/ADMIN TRUE`. La migración versionada que materializa
ese rol quedó **aplicada y verificada** en producción como `20260721120000`.

**[HISTÓRICO PRE-RUN, SUPERADO POR DEC-147] Estado entonces:** `coverage_c1_v2` materializado;
P1 v2 `PENDING`/no ejecutada; C1 continuaba NO-GO. La lane intradocumento genérica pasó 22/22
checks en su probe v2 GET-only sobre los 13
QIDs congelados: preservó todos los prefijos byte a byte, sólo añadió el registro autoritativo de
hp011 y quedó ligada a una lineage gobernada, a la revisión activa, al blob y al SHA exactos. Falla
cerrada ante lineage NULL/no verificada, lifecycle ambiguo o ramificado, drift, overflow, metadata
no autoritativa o un registro Markdown sin cabecera, separador inmediato y aridad coherentes. El
selector dentro del blob exacto no consulta el catálogo histórico. La aplicabilidad se declara:
sólo hp011 alcanza el selector; 12/13 quedan rechazados por lifecycle o idioma. El probe hizo
**84 GET, cero llamadas de modelo y cero escrituras de base de datos**; ambos controles
adicionales se ejecutaron contra el RPC live. Receipt:
`evals/s277_document_local_coverage_probe_v2.json`.

`coverage_c1_v1` permanece byte-semánticamente inmutable y document-local off.
`coverage_c1_v2` añade la quinta capacidad `DOCUMENT_LOCAL_COVERAGE` y sólo permite las lanes
structural + document-local. Cada réplica v2 exige una única lane trace document-local, un
`status=error` produce NO-GO y `http_requests` debe casar 1:1 con los GET físicos; `hp011:r1/r2`
exigen además un único ID seleccionado y servido. `GO_MECHANISM` y el perfil listo no acreditan
una respuesta generada, `P1_PASS`, release ni movimiento del KPI. El run terminal 18/27 no se
reanuda ni se completa: sólo sirve para diagnóstico; la certificación debe empezar fresca 27/27,
con 81 llamadas y cap interno de 30 USD. No hubo deploy ni cambio de Railway y el marcador
permanece 146/154.

**Revisión adversarial cerrada.** Hubo cuatro rondas Sol/Fable, todas completas y adjudicadas:
35 findings, 30 confirmados/resueltos y 5 falsos positivos. No se lanzó una quinta ronda; el
packet v5 es el handoff terminal, no otra revisión:
`evals/s277_document_local_coverage_review_packet_v5.md`.

El Advisor confirma deuda legacy de RLS/grants —incluida `chunks_v2_enunciados`— separada del
RPC mínimo. TECH_DEBT #29 **no bloquea la medición P1 v2**, pero sí bloquea merge/release global
y exige una migración forward-only, inventario y smokes antes del GO final de seguridad/C1.

**Multi-turn/multi-hop permanece separado y `NOT_BUILT` (DEC-136).** El norte sigue siendo
orquestador transport-neutral, estado/event log durable, ingress idempotente, leases+fencing,
CAS propietario y outbox; single-hop barato por defecto, rewrite sólo para follow-ups
dependientes, 2 hops por defecto/3 hard cap y verifier fail-closed. No hay permiso de DDL/build
ni inferencia adicional para esta línea.

**Qué sigue, por orden y sin abrir otro frente:** (1) materializar inputs/recibo/credenciales y
ejecutar una sola P1 v2 completamente nueva de 27/27 sobre el árbol y perfil ya congelados, con
81 llamadas, cap interno de 30 USD y artifact root nuevo; los 18 artefactos anteriores sirven para
diagnóstico, no para completar la certificación; (2) sólo con `P1_PASS`, cerrar TECH_DEBT #29 en
un gate de seguridad separado; (3) pedir autorización separada de merge/deploy/canary; y (4)
medir el +5 mediante eval orgánico/fresco u otra familia causal. `GO_MECHANISM` no autoriza por sí
solo release. La Fase 0 conversacional sigue `NOT_BUILT` y requiere una decisión separada de
Alberto.


<a id="estado-anterior-s205--18-jul-2026"></a>
## Estado anterior (S205 cerrado — 18 jul 2026)

**La foto diagnóstica comparable más reciente es 157 facts: 143 OK · 12 synthesis-miss ·
2 retrieval-miss = 91,08% OK, gap 11 facts hasta el objetivo ≥98% (154/157).** No es todavía un KPI atómico oficial ni
un resultado desplegado: parte del puente híbrido S133, conserva 77 legacy carries pendientes y
presupone dos candidatos locales/default-off. El bridge exacto es: S172 lleva la extracción
`10^5` de hold→OK y deja 141/157; S188 añade dos facts de compatibilidad/topología de
retrieval→OK, dejando 143/157. Estos movimientos sí son crédito diagnóstico de etapa, pero su
crédito productivo sigue siendo cero mientras los flags estén apagados y falte generalización
independiente.

**El orden de trabajo sigue en síntesis porque retrieval es residual (2 vs 12), y S192-S193 han
aislado el siguiente cuello sin tocar targets.** Sustituir Sonnet 4.6 directamente por Terra
`low` es **NO-GO**: 25/37 vs 26/37 puntos, −1 neto, 2 regresiones, +1 pregunta completa;
$0,259085. En cambio, separar planificación y redacción sí da señal causal: S193 conserva la
respuesta base y anexa determinísticamente spans ligados a IDs, por lo que un ID elegido no puede
omitirse. El candidato alcanza 31/37, **+5 puntos, +2 preguntas completas y 0 regresiones** por
$0,071248. No pasa el gate completo porque el selector solo cubre 27/34 puntos disponibles en el
store (79,4% < 90%), aunque la precisión de unidades sí pasa (78,3% ≥75%). Conclusión: el
renderizado con postcondición es candidato estructural; el selector de obligaciones es ahora el
cuello medido. S193 no mueve facts ni autoriza producción. No se ajustará el prompt sobre estas 14
preguntas; el siguiente paso exige descomposición de pregunta y validación fresca.

**S194 ejecutó esa validación fresca y se cerró antes del selector, sin mover facts.** Se congeló
por GET-only una cohorte nueva de `chunks_v2`: 25.090 filas leídas, 14 documentos/fabricantes
distintos, 7 tabla + 7 prosa, cero overlap documental/UUID/pares de desarrollo y manifest
pre-autor de cada unidad fuente. El autor económico Haiku produjo 13 preguntas elegibles,
7 tabla + 6 prosa y 50 puntos, pero **1/14 output fue inválido** porque asignó una cardinalidad de
soporte fuera del contrato. El gate exigía cero inválidos, así que el estado es
`NO_GO_COHORT_CONSTRUCTION`. Coste: **$0,078186**. No se llamó a Luna, no se abrió ninguno de los
cuatro targets, no se ejecutó el compilador sobre ellos y el crédito diagnóstico/productivo es
0. No se repite esta cohorte ni se relajan umbrales. La causalidad útil es upstream: el schema
estructurado del autor describía `support_unit_ids` como array, pero no imponía en JSON Schema el
`minItems=1`, `maxItems=3` y `uniqueItems=true` que el validador sí exigía. El siguiente intento,
si se prioriza, debe corregir ese contrato **antes** de congelar otra cohorte documental nueva;
no reutilizar outputs ni tocar el selector S193 sobre poblaciones ya observadas.

**S195 corrigió la clase de cardinalidad, pero destapó el siguiente límite upstream y también
se cerró sin mover facts.** Anthropic no admite `maxItems`/`uniqueItems` en el dialecto compilado,
por lo que se separó el contrato canónico exacto de un transporte sin arrays: cuatro slots de
puntos y tres slots de soporte por punto, con IDs ligados al documento, normalización determinista
y validación semántica externa Luna prevista para los 14 ítems. Sol 5.6 xhigh revisó el diseño;
la fila histórica llamó `omitted_unavailable` a lo que en realidad era ausencia de ejecutor
versionado en ese worktree, no indisponibilidad global de Fable 5. La cohorte fue
enteramente nueva y excluyó S194: 25.090 filas GET-only, 14 documentos/fabricantes, 7+7, cero
overlap previo/target y cero equivalencia exacta de contenido/extracción. Los 14 conteos de tokens
pasaron, pero la primera inferencia Haiku fue rechazada con 400
`Schema is too complex for compilation`; `max_retries=0`, checkpoint previo, **0 inferencias
completadas**, Luna 0 llamadas y targets/planner cerrados. Estado:
`NO_GO_EXECUTION_CONTRACT_REJECTED`; crédito de facts 0. No se reutiliza S195.

DEC-104 fijó que la reapertura legítima no era “añadir keywords” ni simplificar sobre la población
observada: primero un canary sintético separado con schema estático mínimo y solo después otra
cohorte nueva que excluya S194+S195. La simplificación debía conservar slots estructurales y mover
pertenencia/duplicados de IDs al validador determinista, evitando enums dinámicos y `$defs`.

**S196 completó ese canary y es GO del transporte, no del sistema.** El schema rectangular estático
(4 puntos × 3 soportes) contiene cero arrays, refs/defs, combinators, enums o consts; las restricciones
específicas viven en validación determinista. Sobre dos unidades 100% sintéticas, Haiku 4.5 compiló,
devolvió `end_turn` y produjo dos puntos válidos en una única inferencia. SDK 0.97.0, cero retries,
coste $0,002583. Sol 5.6 xhigh revisó tres iteraciones; Fable volvió a quedar mal rotulado por la
misma ausencia local de ejecutor versionado. Crédito de
facts 0 y ningún documento/target/Luna/planner se abrió. El resultado autoriza solamente un S197
separado: cohorte real nueva, disjunta de S194+S195, mismo schema genérico y validación externa Luna.

**El pre-S197 deja ese siguiente tramo listo sin ejecutar la cohorte.** Se versionó el runner
directo de `claude-fable-5` usado anteriormente desde Codex y el dúo byte-bound con Sol 5.6 xhigh,
eliminando la dependencia de un agente `.claude` local y el estado ambiguo
`omitted_unavailable`. También quedaron preparados el doble freeze GET-only de una cohorte nueva
disjunta de S194+S195 y el gate Haiku→Luna con schema S196, cero retries, locks, checkpoints,
presupuesto ≤$3 y STOP upstream. La verificación local pasa; dos intentos reales de Fable usaron
el pin exacto y tools pero terminaron con bloque de texto vacío, por lo que constan como fallo de
respuesta del proveedor, no como modelo ausente ni como revisión completada. Sol encontró cuatro
defectos medios del propio protocolo; se corrigieron sin abrir otra ronda. Facts movidos: 0.

**S197 ejecutó esa cohorte una sola vez y volvió a detener el funnel upstream.** El doble scan
GET-only fue idéntico sobre 25.090 filas y selló 14 documentos/fabricantes nuevos, 7 tabla + 7
prosa y cero overlap prohibido. El transporte estático S196 ya no es el cuello: Haiku completó
14/14, produjo 14 preguntas elegibles y 42 puntos con **0 outputs inválidos**. Luna revisó 14/14
sin outputs inválidos, pero 12 ítems fallaron al menos un gate: 8 tenían un point-set incompleto
para el alcance de su propia pregunta, 5 contenían un punto no plenamente soportado o irrelevante
para la pregunta y 6 asignaban mal el facet. Resultado `NO_GO_COHORT_CONSTRUCTION`, coste
$0,15476, facts 0; planner, targets, DB, runtime y producción no se abrieron. La clase dominante
ya no es compilación sino cierre pregunta↔obligaciones. El siguiente mecanismo debe seleccionar
primero 2–4 obligaciones support-bound, validar support+facet con definiciones genéricas y sólo
después redactar una pregunta exactamente acotada a ellas, sobre otra cohorte que excluya S197.

**S198 cerró el diseño point-first y el riesgo de transporte nuevo; aún no ha ejecutado la
cohorte real.** Sol 5.6 xhigh principal y Fable 5 independiente completaron la misma revisión;
11/11 observaciones se corrigieron en una sola adjudicación, sin bucle de convergencia. El paquete
seleccionará primero obligaciones support-bound, aplicará una elegibilidad y precedencia de facets
congeladas, y renderizará después la pregunta desde los claims aceptados. Antes de seleccionar
otra fuente, el canary 100% sintético del nuevo schema `{item_id, question}` compiló en Haiku:
1/1 salida válida, cero retry, $0,000686, estado `GO_QUESTION_SCHEMA_CANARY_COMPILED`. Esto mueve
0 facts y sólo autoriza construir desde `main` un packet GET-only nuevo, disjunto de
S194+S195+S197, reportando además el inventario y reserva que quedan. El planner continúa cerrado
hasta que una ejecución única obtenga cero fallos en ambos screens upstream.

**S198 ejecutó después el tramo real y se detuvo todavía más arriba de lo previsto.** La reserva
manufacturer-disjoint ya no podía producir 7+7: quedaban cinco fabricantes de prosa compatibles.
Se congeló por ello un packet exhaustion-aware de 12 fabricantes/documentos nuevos, 7 tabla + 5
prosa, con doble scan GET-only idéntico de 25.090 filas y cero overlap/escrituras. Haiku produjo
12/12 outputs válidos y 37 puntos, pero sólo 10 fuentes fueron elegibles (6 tabla + 4 prosa).
Como el mínimo seguía siendo 12 elegibles, el estado es `NO_GO_POINT_PLAN_STRUCTURAL_GATE` por
$0,070886. Luna, writer, scope-screen, planner y targets recibieron 0 llamadas; no se postseleccionan
los diez casos y la calidad semántica del mecanismo continúa `NOT_MEASURED`. El siguiente intento
legítimo debe restaurar 14→mínimo 12 sobre documentos/source-files/pares nuevos, permitiendo sólo
repetición histórica de fabricante y conservando 14 fabricantes distintos dentro de la cohorte.

**S199 restauró 14 fuentes, pero el cuello poblacional persiste.** El inventario permitió 14
documentos/source-files/pares nuevos, 7+7, pero un máximo de 13 fabricantes; se congeló una sola
repetición sin usar outputs. Haiku produjo 14/14 outputs válidos, 9 elegibles de 9 fabricantes,
4 tabla + 5 prosa y 34 puntos. El gate estructural volvió a parar antes de Luna/writer/planner por
$0,083863 y facts 0. La reserva posterior conserva 647 documentos pero sólo 10 fabricantes: ya no
puede cumplir el mínimo anterior de 12. Para evitar análisis indefinido queda un único intento
final, prelimitado a 24 fuentes balanceadas (12+12), máximo 10 fabricantes, motor S198 intacto y
mínimos 12 elegibles / 8 fabricantes / 5+5 / 24 puntos / cero fallos. Si no pasa, se cierra esta
línea y se cambia de mecanismo; no se reutilizan identidades o issues de S198/S199.

**S200 consumió ese último intento y cerró la línea.** El holdout final tenía 24 fuentes nuevas,
12+12, 24 documentos/source-files/pares y cobertura de los 10 fabricantes restantes. Haiku dio
24/24 outputs válidos, 11 elegibles de 7 fabricantes, 6 tabla + 5 prosa y 40 puntos. Pasaron
estratos/puntos/transporte, pero fallaron los mínimos predeclarados de 12 ítems y 8 fabricantes;
Luna/writer/planner quedaron en cero y el coste fue $0,144517. No habrá S201 poblacional ni otra
calibración point-first. El siguiente orden limpia primero el puente local/default-off mediante
generalización independiente S188→S172 —sin fingir aumento del 143 diagnóstico— y vuelve después
al residual de 12 synthesis-miss con preguntas reales, no con otra autoría source-first.

**La auditoría posterior evita repetir S127/S128 o fabricar población para S172.** S188 ya fue
generalizado sobre seis pares independientes en S127: 57.646 asignaciones produjeron cero
relaciones exactas válidas y la línea global quedó revocada; S128 solo puede reabrirse ante un
funnel nuevo materialmente relation-bound. S172 ya tiene holdout interno preregistrado, 11
documentos, 33 derivaciones propagadas y replay live default-off; el discovery exhaustivo no deja
otro positivo versionado no visto. Ninguno ofrece ahora un nuevo OK legítimo y no se repiten sus
modelos/revisores.

**Pre-S201 sustituyó la población artificial por preguntas reales preexistentes.** El packet
determinista selecciona 12 preguntas sin usar respuesta, clase, `reaches_gen` ni outputs: 8
fabricantes, 12 productos y 43 facts, incluyendo soporte parcial/nulo. Haiku mapea facts a unidades
y Luna valida independientemente soporte y hasta tres conjuntos equivalentes; cualquier desacuerdo
detiene antes de Terra. El planner conserva 90/80/75, máximo 70 unidades, compilación exacta y cero
retry. Solo un PASS abre un packet target autocontenido de los 12 residuals; PASS target requiere
cero regresiones/conflictos y al menos un residual nuevo. Sol 5.6 xhigh detectó seis defectos del
borrador y los seis se corrigieron; Fable 5 llegó al proveedor pero devolvió final vacío tras siete
tools, queda incompleto y no se reintenta.

**S201 se cerró antes de la primera inferencia y no se reintenta.** El primer `count_tokens` de
Anthropic rechazó el schema de autor con arrays y cardinalidad dinámica (`minItems`/`maxItems`), la
misma frontera de dialecto ya aislada en S195-S196. No existe receipt de inferencia completada, Luna,
Terra y targets quedaron en cero, coste de inferencia conocido $0 y facts movidos 0. La cohorte S201
queda consumida: reintentarla tras cambiar transporte contaminaría el holdout.

**Pre-S202 corrigió la causa como contrato reutilizable y separó de nuevo upstream de downstream.**
Una cohorte hash nueva excluye las 12 preguntas S201, los cuatro targets y los dos default-off:
12 preguntas, 5 fabricantes —toda la diversidad restante—, 12 productos y 43 facts. El transporte
Haiku es un rectángulo estático 6×6 sin arrays, enums dinámicos, refs ni combinators; identidad,
cardinalidad, pertenencia y duplicados se validan localmente en `src/rag/source_unit_gold.py`. El
schema exacto pasó el compilador `count_tokens` con 0 inferencias/retries y $0. S202 ejecutaría solo
Haiku→Luna: 0 outputs inválidos, 0 desacuerdos y ≥36 facts source-supported. Un GO únicamente
autorizaría congelar después el planner Terra; S202 no ejecutaría planner/targets ni movería facts.

**S202 resolvió el transporte pero cerró `NO_GO_DUAL_GOLD` antes del planner.** Haiku completó
12/12 mappings válidos para los 43 facts: la causa S201 no reapareció. Luna completó 12 llamadas,
pero sólo 5 outputs pasaron el contrato y 7 fueron inválidos. Seis declararon acuerdo con la
decisión supported/unsupported sin incluir el set exacto del autor: el prompt definía acuerdo sobre
la decisión mientras el validador local lo exigía sobre el mapping, una incompatibilidad real del
instrumento. El séptimo usó un ID fuera del manifest. Los 13 soportados reportados proceden sólo de
las cinco filas válidas y **no** permiten estimar support-rate. Coste $1,258906; facts 0; no hubo
postselección, retry, Terra ni target. Quedan sólo cuatro preguntas S100 no observadas, insuficientes
para otro holdout de 12. La siguiente población se construirá desde manuales Kidde hoy sin preguntas,
con gold visual página-a-página y autoría/cross-review Sol 5.6 `xhigh` + Fable 5 antes de usar modelos
económicos para el benchmark.

**S203 probó el transporte visual y ambos Frontier, pero cerró `NO_GO_VISUAL_GOLD`.** Tres
unidades Kidde nuevas quedaron ligadas a 11 renders pixel-only; Sol y Fable completaron 3/3
autorías cada uno y las dos revisiones cruzadas (8 llamadas, **$14,07876** conservadores). Sol
rechazó un candidato Fable por recomendar BR para una sala de calderas sin recomendación literal
en la fuente. Fable dio PASS a los tres Sol, pero dejó dos notas explícitamente no materiales en
`issues` para el relé y el gate congelado trataba cualquier `issues` como bloqueo. Solo 1/3 pares
fue limpio bajo la letra estricta; no se postseleccionó, no se añadieron golds y se movieron 0
facts. S204 usará páginas/predicados frescos y un contrato reusable que prohíba recomendaciones no
literales y separe `blocking_issues` de `nonblocking_notes`; no reintenta S203.

**Pre-S204 corrige el instrumento y congela una población visual no contaminada.** El contrato
reusable `src/rag/visual_gold.py` prohíbe inferir aplicaciones desde límites numéricos, restringe
facts a páginas focus y separa defectos bloqueantes de notas no materiales con consistencia local
PASS/FAIL. La primera selección local detectó a tiempo que sus predicados textuales ya aparecían
en las preguntas HyQ S99 embebidas del lado documento: no son golds, pero usarlas en evaluación
contaminaría retrieval. Se descartaron antes de autoría. El packet final incluye en el filtro de
duplicados las 51 preguntas gold y las 179 HyQ de los tres PDFs seleccionados, y congela cinco
renders de tres predicados visuales no presentes como preguntas exactas: topología Clase A entre
bases, posiciones DIP 008/112 y distinción de ranuras del KE-DBA-AUXW. La novedad semántica sigue
siendo un gate bloqueante de los revisores, no una afirmación local. Cero solape basename/SHA con fuentes
gold y cohorte S203 excluida. Sol 5.6 `xhigh` y Fable 5 alcanzaron sus pins en la revisión de diseño
monolítica, pero ambos agotaron el allowance sin JSON final; constan como incompletos, no
indisponibles, por **$3,25083**, sin retry. La auditoría determinista corrigió además el PASS vacío.
La preejecución pasa 4/4 tests y autoriza únicamente una PR con CI; tras merge, una ejecución
separada de máximo ocho llamadas y $40. Aún mueve 0 facts.

**S204 ejecutó las ocho llamadas y cerró `NO_GO_VISUAL_GOLD`, sin repetir los defectos S203.**
Sol y Fable produjeron 3/3 candidatos válidos; Fable dio PASS a los tres candidatos principales
Sol, incluidas notas no materiales que el nuevo contrato permitió correctamente. Sol dio PASS a
2/3 candidatos Fable y bloqueó sólo el cableado Clase A: sus seis facts eran visibles y correctos,
pero la respuesta final dejó una frase de polaridad ambigua y omitió la advertencia visible de
desenergizar/descargar antes del cableado. Es un fallo de contenido real, no del schema. Coste
conservador **$15,729345**; 2/3 pares simétricos limpios, pero no se postseleccionan, reparan o
salvan; golds 0, facts 0, bot cerrado. La causalidad nueva es de geometría: hacer publication-gate
del candidato independiente permite que un defecto exclusivo de un candidato no final vete un
candidato principal que sí pasó revisión independiente. Un sucesor fresco puede usar el candidato
independiente sólo como probe ciego de desacuerdo: debe seguir generándose antes de review, ambas
direcciones deben declarar cero desacuerdo material y Fable debe dar PASS a cada candidato Sol.
Debe congelarse antes de elegir páginas nuevas y nunca rescatar S204.

**S205 validó la geometría principal, pero la auditoría determinista cerró la cohorte por
contaminación.** La regla se congeló en un commit anterior a la selección: Sol 5.6 `xhigh` era el
único autor publicable, Fable 5 generaba a ciegas y debía aprobar todos los Sol, y el borrador
Fable sólo actuaba como probe de desacuerdo. Tras PR #142 y CI verde se completaron 8/8 llamadas
por **$11,81598**: seis candidatos válidos, Fable PASS 3/3 a Sol, Sol PASS 2/3 a Fable y cero
desacuerdos materiales; el runner produjo un GO mecánico. La revisión local obligatoria detectó
que `s205k03` pregunta por los modelos/funciones de barreras de la misma tabla y el mismo PDF ya
embebidos por `hyq:54c2275f…:2`. Sol sí marcó ese duplicado al revisar el counterpart; Fable lo
negó suponiendo erróneamente otro documento porque el packet no exponía identidad de source en
las filas de cobertura. Medirlo downstream premiaría leakage del retriever. El estado autoritativo
es por ello `CLOSED_NO_GO_VISUAL_GOLD`: no se salvan los otros dos candidatos, no se integra gold,
no se abre bot y se mueven 0 facts. La línea de canarios visuales se cierra aquí para evitar otra
convergencia; se vuelve directamente a las 12 synthesis-miss existentes.

**`chunks_v3` no se migra al completo.** S140 cerró el shadow representativo como
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`: empata recall funcional@10 (16/24 vs 16/24) pero empeora el
primer rango útil/MRR (0,4021→0,3694). `chunks_v2` sigue siendo el baseline activo. V3 preserva
más superficie upstream y su contrato de procedencia es valioso, pero esa propiedad no compensa
una regresión downstream. Solo se diseñará v4 si una causa estructural local mejora el ranking sin
pérdidas por fabricante/held-out; no se parchearán preguntas concretas.

**Frentes ortogonales:** (a) voz tiene selector versionado y default `whisper-1`; no se migra de
modelo sin 30 notas reales estratificadas, que hoy no existen; (b) el renderer de Telegram ya
preserva contenido, tablas y mensajes largos y pasa su gate local; (c) S190 demostró que el canal
de imágenes está implementado en bot/generador pero sin datos en `chunks_v2`: 0/25.090 URLs.
Existe un bridge exacto hacia 5.096 páginas legacy (7.685 chunks; 30/30 assets vivos), pero una
muestra visual contiene portadas/marketing. Por ello el backfill directo es NO-GO. S191 ejecutó
Luna sobre 60/60 activos válidos por **$0,04029**, pero el trigger 10–30 positivos quedó mal
calibrado frente a una cohorte con 48 estratos de intención técnica y produjo 44. No se cambió el
umbral post hoc ni se llamó a Sol/Fable. La calidad del clasificador queda sin medir; el diseño BP
sigue siendo un registro ligado a documento+revisión+página+hash, independiente del chunker.

**Producción no ha cambiado en este bloque.** No se ha hecho deploy, migración ni escritura
remota. Railway sigue siendo una demo y no es condición para merge con CI verde. Próximos pasos,
por orden: (1) merge CI-verde del resultado S205; (2) volver a las 12 synthesis-miss y reconstruir
su evidencia upstream con los artefactos ya versionados, sin otra autoría de preguntas; (3)
congelar un cambio estructural sobre el mayor sub-bucket y medirlo primero en población no usada
para diseñarlo; (4) reconciliar el bridge diagnóstico/productivo sin sumar de nuevo S172/S188;
(5) al alcanzar ≥98%, pasar a diagramas/formato/Wispr Flow; (6) recoger 30 audios reales antes de
comparar ASR. El funnel conserva sus etapas: S193 mantiene señal de renderer; S194, S195, S197,
S198, S199, S200, S202, S203, S204 y S205 son NO-GO upstream, S196 y los canarios de transporte
son GO instrumentales, S201 es HOLD cerrado y todos siguen con crédito de facts cero.

## Estado anterior (s129 — 15 jul 2026)

**No existe todavía un KPI atómico oficial vigente.** La última evaluación completa y
comparable (`s100_factlevel_full.yaml`, commit `9790673`, ya anterior al branch/worktree actual)
dio **93/127 OK (73%) · synthesis 11 · retrieval 7 · rerank 14 · corpus-gap 2→0 tras revisión
manual**. La fila del scoreboard tenía retrieval/rerank transpuestos y se corrigió en s129.

El **79** era un puente híbrido que aparcaba 33 parents y dejaba 11 claims sin respuesta; el
**111** aparece al sustituir esos 33 parents por 58 core claims y reutilizar respuestas congeladas.
No son tres puntos del mismo KPI ni 32 mejoras del bot. La foto provisional sin activar S126 es:
**157 claims · OK 111 · synthesis-not-measured 27 · synthesis-miss 14 · retrieval-miss 4 ·
source-contract-hold 1**. S126, local y default-off, movería 2 retrieval→not-measured y **0→OK**.
Además quedan **77 legacy carries** por migrar/adjudicar antes de poder publicar un KPI plenamente
atómico; hasta entonces, cualquier funnel completo será híbrido y debe conservar crosswalk.

**`chunks_v3`: GO estructural local, no GO de calidad/producción.** Se rematerializaron
determinísticamente 1.068 documentos / 31.226 filas; recupera 100 bloques antes perdidos, con 0
pérdidas detectadas, y cambia contenido en 27 documentos. Aún no hay DB apply/rollback real,
contexto, embeddings, shadow load ni A/B retrieval. Nueve qids antiguos estuvieron expuestos a
documentos cambiados, pero eso no prueba que el span nuevo soporte el fact. S127 queda
**NO-GO/revocado** y S128 (extractor relacional) **pausado antes de build**.

**Estado de ingeniería:** branch local S108-S111 = 4 commits sobre el `origin/main` local;
S112-S128 siguen mayoritariamente en worktree (**463 paths dirty, ~2,4 GB untracked**). La suite
actual pasa **1.285 tests, 5 skipped, 0 failed**. Nada de este bloque implica deploy o cambio de
producción verificado.

**Qué sigue, por orden:** (1) mapping exacto `claim→extraction→bloque ganado` sobre los 27 docs/100
bloques; si no encuentra oportunidad material, parar la rama KPI de v3; (2) en paralelo, M0b de
PostgreSQL+pgvector desechable (apply, permisos, activación y rollback); (3) solo con señal, generar
contexto/embeddings para el shadow mínimo y medir **retrieval→rerank→synthesis** en cascada contra
`chunks_v2`; (4) resolver los 27 not-measured reales con evidencia congelada y los 2 de S126 en
brazo separado; (5) cerrar los 77 legacy o publicar ambos denominadores con crosswalk. Solo entonces
elegir el mayor bucket fresco y reabrir mecanismos como el extractor relacional.

## Estado anterior (s104 — 10 jul 2026)

**s104 (DEC-102) — R2 corpus-wide ejecutado hasta su gate; DEC-101 MEDIDO en scoreboard (fila
v3: OK 93/73%, retrieval 12→7, lista diana completa convertida +9/−7).** R2: pipeline seguro
(generar→dump→loader-A3; el dúo cazó que el pase legacy insertaba al índice compartido del
NO-GO DEC-088) · G0 = Haiku GO medido (4x más barato, QA-pass superior; panel cazó meta-líneas
DE Sonnet) · T2 81/81 generado (45.889 enunciados QA-passed en dumps, ~$10) · **carga a 71K =
GATE T2 DISPARÓ** (0 ganancias de ancla, 2 OK perdidas, crowding del sort-mixto sin cuota —
la clase que hyq resolvió con fusión-por-cuota) → **rollback a T1 VERIFICADO 0/0; tail (~$95)
NO gastado**. Activo a salvo: 54.849 enunciados Haiku en dumps locales; re-carga post-fix ≈$1.
**Qué sigue (cabeza de cola): CUOTA del canal enunciados** (espejo hyq DEC-099; dúo obligatorio
+ gate de re-carga = probe pre/post committeado) → re-cargar T2 → si gate pasa, tail → gate
final (bvg + assessment fila v4). Después: synth/gold-review (DEC-094) + entity-linking #52.1.
Costes sesión: ~$135 envelope + R2 $14/$180. Prod = demo v3 (DEC-101) con tabla A3 en estado
T1 exacto.

## Estado anterior (s103b — 10 jul 2026)

**s103b (DEC-101) — landing RESUELTO por extensión acotada + selección code-gated: CANDIDATO DE
SHIP GATEADO, pendiente GO de Alberto (merge + Railway `GENERATOR_SELECTION_BLOCK=on`).** Tras el
NO-GO de la eviction (DEC-100, abajo), la re-apertura MEDIDA de su alternativa A2: el carve-out
deja de reservar slots (el doble cobro desaparece de raíz) y el aside viaja como extensión
(≤ top_k+cuota, patrón identity-fetch). Gates: diana 4/4 (incl. hp018·p21) · anclas +1/−0 ·
containment 0-missing · negcontrol 6≤7 · flips 2/2 · churn anclas-OK 0-loss · **bvg +cat022
FALLO→PASS**; la única regresión real (cat021, composición-sensible DEC-097) curada con el bloque
de selección con trigger EN CÓDIGO (el prompt-gated sobre-dispara hp009 — 2 mediciones; regex
determinista: sweep 39 = solo cat021, spec/avería byte-idénticas por construcción). cat024/hp009
= artefacto-juez/baseline (leídos). Family-aware landing MEDIDO NO-OP (0 cross-family con lista
resuelta) → queda como hygiene DEC-074. Top-100 MEDIDO no-paga (3/11 a ranks 55-91; 5 ni a 100 =
vocabulario). Desviaciones de proceso declaradas en DEC-101 (D1-v1 inválido→v2, métrica
refinada; fix `_stage_of` no-monotonía). Suite 473. Coste sesión ~$90/$150. **Qué sigue:** (1)
GO/NO-GO de Alberto al ship DEC-101; tras ship → assessment smoke→full (fila v3 del scoreboard,
caveat bucket in-pool +10). (2) **Entity-linking (DEC-074)**: primer consumo = sinónimos/series
del family-filter hyq (#52.1) — el family-aware landing quedó medido NO-OP; hygiene bajo REPLACE
sigue candidata. (3) Gateados: enunciados R2 ($160-270, presupuesto Alberto) · #52.2 al gatillo.

## Estado anterior (s103 — 9 jul 2026)

**s103 (DEC-100) — lever displacement-landing (eviction) MEDIDO → NO-GO por gate pre-declarado →
REVERTIDO.** El rediseño del carve-out hyq (diversify a top_k completo + eviction VECTOR por
posición + trim del aside; dúo 2 rondas × 2 lados, 14+ findings/0 FP) FUNCIONA para su diana
(cat022 recupera 3/3 chunks; anclaje corpus-amplio +1/−0) pero los CONTROLES amplios lo tumban:
rompe el flip shippeado hp018·6K8 (gate DEC-099), hp011 fuera del null, negcontrol EXCESS-HIGH
7→9. **Lección medida: canal/score/sim-pregunta/posición — los 4 ejes observables son ciegos al
valor.** Seam `evals/s103_displacement_seam.patch`; matriz v3→v2.2
`evals/s103_transition_matrix.json`. Synth residual mapeado (`evals/s103_synth_residual_map.md`):
6/8 stable-miss, cluster cat021 NO reaparece, 5×omitted → gold-review (DEC-094), no lever synth
nuevo. Prod NO tocado (revert por pre-registro).

## Estado anterior (s102 — 9 jul 2026)

**s102 (DEC-096..099) — canal hyq SHIPPEADO A PROD y VERIFICADO + demo completa medida (scoreboard
v2.2).** El canal question-side (tabla `chunks_v2_hyq` 70.134 preguntas + seam `HYQ_TABLE`, mecánica
v2: cuota 10 + barra 0.45 + family-parity nivel-fila patrón-012 + carve-out del diversify) pasó
flips 2/2 CON atribución + bvg 0-regresiones-reales, PR #115 mergeado, **flip cat016 verificado en
query_logs de prod** (d355867). **Scoreboard v2.2 (demo real: fidelity+hyq ON): OK 91 (72%) ·
synth 18→8 (¡cluster cat021×4 → OK vía composición-servida, sin tocar generador — confirma DEC-097!)
· retrieval 12 · rerank 13 · corpus-gap real 0.** Factura del canal VISIBLE y con mecanismo
verificado: cat022×3 + hp018×3 desplazados (el presupuesto reducido del diversify aprieta al canal
keyword — negcontrol rojo pool-level lo anticipó). **Qué sigue:** (1) lever candidato = aterrizar el
desplazamiento en la cola del canal VECTOR (no keyword) — medir antes de cablear, anti-overfit
flagged; (2) synth residual 8 (~reales); (3) el estructural grande = entity-linking/identidad
(DEC-074, F1 construido sin consumir). Levers cerrados: demote-TOC NO-GO (DEC-096) · selection-block
NO-GO+fork (DEC-097) · fidelity SHIPPED (DEC-098) · hyq SHIPPED (DEC-099). Límites declarados:
TECH_DEBT #52. Plan reanudable: `evals/s102_plan_autonomo.md`.

---

## Estado anterior (s101 — 8 jul 2026)

**s101 (DEC-095) — instrumento dual×2 + 4 levers upstream MEDIDOS + scoreboard v2 (autónomo nocturno,
mandato OK>95%).** El instrumento cazó y arregló 2 clases de FN de su propio juez (conveyed + soporte,
dual GPT→Opus con evidencia adversarial); gold-review pixel-vs-fuente (5 demotes + hp011 r.I — Alberto
corrigió su s30; el cross-model tenía razón contra el ground-truth humano). **Scoreboard v2 (juez v2):
OK 91 (71%) · synth 22 (14 stable/8 flip; cluster cat021×4 = variantes 40/40) · retrieval 8 · rerank 5 ·
corpus 2.** Levers: **hyq/HyPE piloto GO** (2/7 flips, cuota+barra; ship=D2 Alberto; residual-ancilar
declarado anti-overfit) · **tiebreak CERRADO** (2ª medición, con ancho-10: centinela hp001 regresa) ·
cat013=identidad (DEC-074). **Qué sigue: Fase 2 (synth 22→1-2)** — A/B fact-level del fidelity-block
en vuelo (métrica ≠ DEC-051-PASS); cluster cat021 (variantes) = candidato específico; luego D2-D5 de
`evals/s101_decisiones_alberto.md`. Plan reanudable: `evals/s101_plan_autonomo.md`.

---

## Estado anterior (s100 — 7 jul 2026)

**s100 (DEC-094) — assessment a nivel-hecho ESTANDARIZADO construido+corrido → foco RE-DERIVADO con datos frescos.**
Se construyó `scripts/factlevel_assessment.py` (unifica los 7 instrumentos ad-hoc) + doc canónico
`docs/FACTLEVEL_ASSESSMENT.md` con **scoreboard append-only** (source-of-truth de "qué tal funciona el bot" a
nivel-hecho, para trazar la aguja; medido en ruta HARNESS con flags-demo, NO el bot Telegram — caveat declarado).
**RESULTADO (39 golds, 133 facts):** OK 89 (67%) · **synth-miss 16 estructural** (+6 flip) · retrieval within-doc ~17
(gap vocabulario) · rerank 4 · **corpus-gap ~0** (5 raw TODOS FN, verificados a mano — `feedback_corpus_gap`) ·
**identidad 0**. **Titular: síntesis SIGUE siendo el cuello dominante post-ancho/A3/identidad → DEC-075 re-confirmado
en veredicto (su medición s87 sí era caduca); identidad+corpus descartados con datos frescos.** Refinado por sub-motivo
(~10 omitted/hedged=lever prompt + ~5 partial=lever retrieval + 2 contradicted) PERO **contaminado por scope/gold**
(hp007: el bot respondió lo preguntado) → qué-lever-DENTRO-de-síntesis = gold-review por-hecho, NO zanjado por este run.
Dúo-intensivo (spec ×3 + código ×2 + 3 smokes cazaron 4 bugs de diseño). Rama `eval/s100-factlevel-assessment`.
**Rumbo previo (s99b) VIGENTE en lo suyo:** blindar-demo→nota pivotó a NOTA; reescritor APARCADO (`evals/s99_rewriter_design.md`);
identidad B = QA ~363 candidatos (DEC-074); PCI-fuego puro (TECH_DEBT #75).

---

**Antecedente s87 (DEC-075) — diagnóstico de síntesis (⚠️ CADUCO, pre-ancho/A3/identidad):**
**s87 (DEC-075): diagnóstico autónomo de SÍNTESIS → el "cuello 103" era una COTA, no fallos.** El bucket
SÍNTESIS `by_target` (103/132, DEC-070/073) contaba hechos SINTETIZABLES (soportados por un chunk del top-5),
NO fallos de síntesis. Midiendo la RESPUESTA actual directamente (instrumento nuevo `synthesis_miss_judge.py`,
juez GPT-5.5 K=5 a nivel-proposición, dúo-hardened, 2 gen para varianza): el pipeline actual **sintetiza
~76-80% de los hechos en-contexto**; el cuello de síntesis ROBUSTO = **16 stable-MISS (~13-14 genuinos)**, cola
pequeña y HETEROGÉNEA — completeness ~10 (=lever de generación **settled NO-GO en PASS**, DEC-051) · contradicts
~4 (FIDELIDAD: bot afirma inconsistente, p.ej. hp001 '1111' access-level, hp013 'EEPROM' invertido) · hedge ~2 ·
judge-FN ~3-4 · identidad hp018 (DEC-074). **Sin lever barato de síntesis.** Atribución verificada: mejora vs
s67base con el MISMO modelo/temp/tabla → efecto de **VECTOR_NOCAT** (mejor retrieval → contexto más rico).
Certificado por dúo de agentes (adjudica-ciego + verifica-adversarial) que corrigió en AMBAS direcciones (cazó
over-credit hp018 + confirmó OMITTED reales). **NADA en prod, reach≠PASS, 354 tests. Refina (NO refuta) DEC-070/073.**

**PASS des-diferido MEDIDO (Alberto autorizó): PASS-control = 9 · K-INESTABLE 6 · residual 24 — PLANO vs s67base
(10+4), dentro del ruido ±2.** Mi predicción "subió mucho" FALSADA por la medición (VECTOR_NOCAT mejoró el
mecanismo pero no el PASS holístico; "80% hechos ≠ 80% PASS" confirmado). **Root-cause SEMÁNTICO de los 30
NO-PASS:** SÍNTESIS 11 (completeness=NO-GO+fidelidad) · **OTRO gold/juez 10 (sin miss de pipeline** → fidelity-errors
reales cat022/hp001/cat009, falso-NO-PASS juez cat019, conducta, supp) · RERANK 6 (settled) · RETRIEVAL 2 (ingesta) ·
IDENTIDAD 1. **Meta-hallazgo: ~10/30 fallan ⊥ el pipeline → arreglar retrieval+síntesis NO los pasaría. Plateau
noise-limited CONFIRMADO al nivel de gold (DEC-051e medido); NO hay lever de pipeline que mueva PASS.**

<details><summary>Antecedente s86 (DEC-074) — B2 por los 3 clusters: identidad ~4-palanca (no el cuello), BP=catálogo 2-etapas</summary>

**s86 (DEC-074): B2 por los 3 clusters de retrieval-miss.** **RECALL-INTRADOC (8)** = 5 hard-tail de INGESTA (coseno sub-suelo/"aguja en chunk grande"; neighbor-window NO-GO + ef_search marginal + más-contexto insuficiente, todo DESCARTADO midiendo → fix BP = capa-ingesta multi-granularidad/tablas, foundational futuro); 3 within-doc. **MODEL-FILTER (4, hp018) = identidad, ~4 de palanca REAL** (no el cuello): `LEVER2_IDENTITY` curado da 4/4 pero es quick-fix (per-familia, regresa hp009) → NO shipear; hp011 mis-diagnosticado (RP1r-Supra, within-doc). **BP identidad = catálogo canónico de 2 ETAPAS** (workstream A); mapa data-driven solo (`family_scope`) = net-negativo. Código `neighbor-window`+`IDENTITY_MAP` flag-gated OFF.
</details>

<details><summary>Antecedente s85 (DEC-073) — limpieza A mergeada + instrumento family-aware (=14) + B1</summary>

- **A — limpieza de raíz MERGEADA (PR #94, en demo):** `VECTOR_NOCAT` permanente (sin flag) — el filtro por la columna `category` MUERTA fuera de raíz (4 sitios + broad-fallback + 3c-i + detección inerte + param content_search). Verificado judge-free: 354 tests + equivalencia de pools 38/39 (net −63 líneas). Conserva MERGE_STRATEGY/LEVER2_IDENTITY/PM_RESCUE + detección para catálogo.
- **A — limpieza de raíz MERGEADA (PR #94, en demo):** `VECTOR_NOCAT` permanente (sin flag) — el filtro por la columna `category` MUERTA fuera de raíz (4 sitios + broad-fallback + 3c-i + detección inerte + param content_search). Verificado judge-free: 354 tests + equivalencia de pools 38/39 (net −63 líneas). Conserva MERGE_STRATEGY/LEVER2_IDENTITY/PM_RESCUE + detección para catálogo.
- **B0 — instrumento family-aware de retrieval-miss (`retrieval_miss_judge.py` + `_famtie.py`):** juez semántico GPT-5.5 K=5 (sustituye el matcher léxico que inflaba ~45%, DEC-070) + **tie por FAMILIA de `product_model`** (corrección de Alberto: by-target acreditaba hp018 vía manual de familia equivocada ZXAE/ZXEE por azar) + pin del pool. **retrieval-miss canónico = 14** (SÍNTESIS 103 = el cuello sigue siendo síntesis; CORPUS-GAP=1 residual FN). Dúos #17/#18 cazaron 8 bugs (2+2 CRÍTICO) → arreglados sin re-juzgar.
- **B0/B1 — instrumento family-aware (=14) + diagnóstico por (etapa×motivo):** juez GPT-5.5 K=5 + tie por FAMILIA de `product_model` + pin del pool. Mapa B2: RECALL-INTRADOC 8 · MODEL-FILTER 4 (hp018) · RECALL-GLOBAL 2. (Detalle: DEC-073.)
</details>

**Modelo operativo (DEC-071e) VIGENTE:** `main`=dev=demo, stop-line=tests-verdes, PASS diferido a síntesis, freeze per-eval. Disciplina de coste (`feedback_cost_discipline`).

**Qué sigue — s100 RE-CONFIRMÓ síntesis como cuello a nivel-hecho (16 estructural); PASS sigue plano (~9-10/39). Decisiones para Alberto:**
0. **(s100, fresco) El cuello a nivel-HECHO es síntesis (16 estruct.) + retrieval within-doc (~17, vocabulario).** Identidad/corpus
   descartados con datos frescos. El **lever dentro de síntesis** (prompt para omitted/hedged vs retrieval/chunking para partial) NO
   está zanjado: el sub-motivo está contaminado por scope/gold → requiere **gold-review por-hecho** de los 16 (eje gold/juez) ANTES
   de apostar. El retrieval within-doc = gap de vocabulario, lever caro (re-ingesta A3/tablas, DEC-085/86, gate presupuesto).
1. **NO perseguir levers de síntesis/rerank/retrieval CIEGAMENTE por PASS** — el PASS sigue plano (~10/30 NO-PASS ⊥ pipeline,
   DEC-051e). Pero el nivel-HECHO SÍ tiene señal accionable (síntesis 16) — separar "mejora el bot a nivel-hecho" de "mueve PASS".
2. **Highest-leverage PASS = dual-judge + gold-review del bucket OTRO (10 golds)** (s47 §D / s76): cat019 ya medido
   falso-NO-PASS (juez-bias); los 6 K-INESTABLE tienen votos PASS. Recuperaría varios PASS reales-pero-juzgados-PARCIAL
   **sin tocar el bot**. Es el ruler-hardening que DEC-051d gatea. Requiere held-out + cross-model.
3. **Fidelity-errors reales del bot (cat022 longitud-onda-IR, hp001 '1111', cat009 6K8)** = per-caso: ¿retrieval de
   sección equivocada o generación? Bugs de calidad genuinos, actionable (barato).
4. **Foundational (⊥ PASS a corto): (A) catálogo canónico de identidad** (BP entity-linking 2-etapas; escala-30+;
   4-7 ses, ~3.5-6.5h Alberto; Fase 0 = drafta contrato) + **capa-ingesta retrieval** (DEC-074) para RETRIEVAL/IDENTIDAD.
5. **El unlock de calidad REAL = eval orgánico (técnicos, ~sept)** — el ruler ±2 es el techo (DEC-051e/s69).

**DEC-056 SIGUE (ranking); DEC-068 SIGUE (L-i por PASS settled). Identidad ~4-palanca (DEC-074). SÍNTESIS ROBUSTA ~16 stable-MISS (DEC-075). PASS plano ~9/39 MEDIDO (DEC-075f) — plateau noise-limited.**

**s88 (DEC-076/077, nocturna autónoma):** per-caso al píxel de los "fidelity-errors" → **CERO invenciones del
generador** (se disuelven en within-doc + gold/juez-review; corrige un FN del rootcause en hp001); **dossier de
los 30 NO-PASS** (`evals/s88_nopass_dossier.md`) para decisión-en-lote de Alberto — la Clase A (gold/juez-review,
~6-7 candidatos con evidencia literal) es la palanca CANDIDATA más barata de PASS (delta no medido, gate Alberto).
**DÚO v2 (pedido Alberto):** sub-agente→`fable` + cross-model CON tools read-only sobre el repo (paridad de
información; cierra TECH_DEBT #36; smoke validado).

**s91 (DEC-080): F1 BULK — las 31 marcas en el catálogo canónico.** ~1.6k productos / 39 homónimos /
861 doc_map / 9 docrel ES/EN (los de DEC-066); BRAND_MAP 96→31; typo-merge #49 (30); x-brand jamás-merge-auto;
dúo 2 rondas (14 findings aplicados; la clase H5 reincidió en el gt FAAST → re-transcrito fiel). Golds-clave
resuelven; lo dudoso fail-open. PR #102.

**s91b (DEC-081): los 25 homónimos ADJUDICADOS por Alberto (G1✅ G2✅ G3✏️×3-verificados G4=APIC-clarify)
y APLICADOS** (`s91_apply_homonyms.py`: 30 winners / 33 redirects+rebrand-of / quedan 9 homónimos [2 gt +
APIC + 6 cola]; `systemsensor:6424` creado; umbrella B500; oem SOLO adjudicado: Esser/Xtralis/Carrier/SS×2).
Sub-agente adversarial cazó 3 H5 en MIS añadidos pre-commit (0 FP). **FIX D1: `data/catalog/` entra a git**
(`.gitignore data/*` lo dejaba SIN versionar y el test de integración skippeaba → repo-first real).
**Gate restante: merge PR #103 (Alberto) — CUMPLIDO.**

**s91c (DEC-082): plan F2 v2.2 dúo-hardened (×2 rondas, 15+13 hallazgos 0 FP)** — mecanismo = los 2
seams medidos (models-list LEVER2→catálogo + unión-protectora doc_map en `_filter_to_query_models`),
NO vía aditiva (DEC-069, fila nueva en LEVER_DIGEST con VENDIMIA de config); **contrato §5.1
ENMENDADO (✅ Alberto, PR #105): F2 expand-only, clarify conduct-level → fase posterior por-pregunta.**

**s91d (DEC-083): F2-S1 CONSTRUIDO (PR #106, dúo r3: 14 hallazgos aplicados pre-PR)** — resolver
query-side tras `IDENTITY_RESOLVE=off|shadow|on` (default off), detector regex-generada del catálogo,
brazos add/replace, fail-fast de flags en arranque, shadow a Supabase (`identity_resolve_shadow`
creada), stamp catálogo-commit; 28 tests nuevos (suite 411). **+ packet C2 COMPLETO adjudicado
(3 tandas Alberto): 19 marcas → 43 productos re-domiciliados; lecciones: hosting≠OEM,
string-grupo→contextual, familia≠marca (FAAST→paraguas familia+LT-200 divergent=true, expanden).**

**s92-s93 (DEC-084): F2 MEDIDO Y SHIPPEADO A DEMO; el lever identidad-en-retrieval queda EXHAUSTO.**
S2 con predicciones pre-registradas + pin-regen: **ADD gana** (retrieval-miss famtie 15-control→**12**;
hp018 4/4 contrato; hp009 intacto; REPLACE reproduce la regresión hp009 CON mecanismo visible) →
`IDENTITY_RESOLVE=on`+`add` **ON en Railway** (PRs #107-#109; verificado vivo vía shadow: ZXe→+3
variantes). S3-fetch acotado: **NO-OP 12→12** (el selector léxico no encuentra los chunk-ids juzgados)
→ NO-SHIP, código tras flag default-off. **−3 neto banked; el residual 12 ≠ identidad.**

**s93b (DEC-085): BAKE-OFF fine-grained EJECUTADO (8h autónomas; plan v3.2 dúo-hardened ×2 +
pushback de Alberto "no solo FTS")** — `evals/s93_bakeoff_resultados.md` = artefacto de decisión.
**PASO-0 trace: 30/31 soportes nunca entran a canal (fine-grained confirmado); hp012 '99+99' muere
en diversify → lever diversify, no ingesta. A-FTS: NO-GO 1/11 + desplazamiento 12-19/20 en controles.
B-multigranularidad cruda: 1/10 (aislar ALEJA: 5/8 sub<padre). C-extracción-tablas→ENUNCIADOS: 2/4 ✅
único mecanismo con hechos que nada más gana → ES el que financia la re-ingesta (~$150-300, gate
presupuesto Alberto; piloto natural = ~6 docs del testbed + famtie). HyDE solo: 0-1/10 (comprime
gaps, no cruza; re-evaluable post-ingesta). Cuello re-caracterizado: gap de VOCABULARIO query↔celda,
no tamaño del chunk per se.** Nada cablado (FTS_ALL_QUERIES no se construyó; flags intactos).

**s94 (DEC-086): PILOTO extracción→enunciados EJECUTADO — GO del mecanismo (criterio pre-registrado
cumplido en las 3 barras).** Spec v2 dúo-hardened + validación BP (multi-vector/verbalization =
canon). **R2 enunciado-LLM: famtie 12→6 (5/10 testbed + colateral '99+99'; GO-tabla 2/4 ✓ GO-prosa
3/6 ✓ 0 nuevas-miss; predicciones clavadas) · R1 plantilla DESCARTADO por medición (0/4) · R3
resumen/tabla complemento barato (12→8, gana ISO-X).** Triage: hp011+'99+99' mueren en DIVERSIFY
(mecanismo vivo → lever pipeline aparte); cat013/cat016 = vocabulario operativo puro (sin mecanismo
aún). Seam `PILOT_PARENT_SWAP` default-off (5 tests); inserciones REVERTIDAS ×3 (0 restantes);
nada shippeado. Artefactos: `evals/s94_pilot_{spec,run}.md` + `s94_f3_results.json`.

**s94b/T0 (DEC-087): la infraestructura PERMANENTE del pase construida y dúo-hardened (2 rondas
del dúo sobre plan + 2 sobre build; 30 hallazgos aplicados, 0 FP).** Migración **007 APLICADA**
(parent_id CASCADE + ingest_batch + RPC include_surrogates default-false; ef_search s59b preservado
vía set_config; rollback ejecutable `007_rollback.sql`) · **invariante de NO-SERVICIO** (9 GETs +
RPC: una fila con parent_id JAMÁS se sirve cruda — cierra la ventana demo-sirve-derivado F1) ·
swap `ENUNCIADOS_MULTIVECTOR` from-row (14 tests) · **QA generalizado calibrado ×3** (fix DECIMALES
reproducido: '13,9' alucinado pasaba; 86.6% final, 2/2 conocidas siempre) · panel de desplazamiento
(fix EMBARGO: los 12 held-out estaban dentro del pin v1; re-pineado dev+query_logs + suelo de ruido)
· pase idempotente por-doc (temperature=0, prompts v1 congelados; smoke MIDT180 427 QA-OK, cov 65%).
Umbral QA re-registrado a calibración-en-T1 (~78-86% real full-doc, no el 97% del piloto); coste
re-estimado: T1 ~$40-100 y su medición fija T2-T3 (banda $160-270 obsoleta). 435 tests; demo intacta
(flag off, 0 surrogates).

**s94c/T1 (DEC-088): pase corpus EJECUTADO → NO-GO del enfoque "surrogates en índice compartido".**
Gate G1 (reproducción) FALLA 2/6: los 21.995 enunciados en el MISMO HNSW que los 22.339 chunks
reales lo diluyen (índice ×2) → recall real cae 12→19, multivector 13 (neto peor que 12). El
piloto s94 (12→6) no escaló: usó 251 surrogates dirigidos/transitorios; a docs-enteros el mecanismo
se ahoga (dilución + enterramiento). **T1 (~$50-75) cazó el fallo ANTES del gasto de corpus ($150+)
= tramos funcionando.** Demo restaurada (dump+delete+revert+VACUUM); schema T0 conservado; bug
latente arreglado (FK duplicate_of → migración 009). Side-by-side: **Sonnet 5** es el vintage
(mejor calidad, ≤coste). 435 tests.

**s95 (DEC-089): redesign MEDIDO con 2 pilotos ($3.5).** Research verificado (BP unánime: surrogates
en índice propio; Dense X +2.2 con embedder fuerte; agentic-RAG-como-arquitectura descartado con
evidencia ACL-2026 + perfil de fallo propio) + dúo sobre el plan (15/15 confirmados, 0 FP, 4
críticos) + ejecución: **A3 (tabla `chunks_v2_enunciados` SEPARADA + paridad de filtros + colapso
Dense-X; migraciones 011/012) = famtie 12→7, 0 regresiones, control 12 INTACTO — arquitectura
VALIDADA, candidato a ship.** Piloto D (deep-lookup Haiku en seam IDENTITY_FETCH, parser
3-estados) = NO-GO (12→11, 0/6, 38% gatillado: el seam solo corre con doc AUSENTE y la clase
dominante es doc-presente-aguja-ausente). Residual 7 caracterizado por clase. Flag OFF en demo;
nada shippeado. 441 tests.

**s98 (DEC-092): matriz de rerank autónoma → el lever que paga es SERVIR-MÁS al generador
(top-8/10), NO tocar el reranker (6 métodos NO-GO: prompt×2, Opus 4.8, ventana 2500, Voyage-CE,
RRF). El dúo lo reencuadró de "estructural" a HIPERPARÁMETRO-DE-ANCHO (CUT15 confirma agujas en
rank 6-15 + el confound tamaño-petición). rerank-miss 1-2 ES alcanzable a nivel retrieval (top-10=2)
PERO el smoke e2e cazó truncado intermitente en un control (`LLM_MAX_TOKENS=2048` fijo, TECH_DEBT
#74) + rescate en respuesta parcial 3/9 → NO ship limpio.** Gate bvg prod-fiel (flag
`BVG_TARGET_MODELS`) + flag `RERANK_TOP_K` (getenv, default 5) + pre-registro
(`evals/s98_bvg_gate_prereg.md`) LISTOS para GO de Alberto; **recomendación = no-ship-10-as-is**
(subir LLM_MAX_TOKENS o quedarse en top_k=8). Residual reranker (hp005/hp006 >rank-15) =
document-side. **s97 (DEC-091/091b): tie-break diversify NO-GO** (hp001 regresión de contenido;
bloqueado en el reranker — s98 midió ese "afinar el reranker" = NO-GO como fix de calidad).

**s96 (DEC-090): gate bvg de A3 EJECUTADO y PASADO 4/4** (plan dúo-hardened: 11/11 confirmados,
0 FP, 2 fixes críticos de código aplicados — fail-open del canal enunciados + parser estricto del
flag): rescate→top-5 3/3 golds-flip · PASS-control 11→13 (+2 en banda; residual 23→19) ·
invención sin subida (matriz pareada 10/33=10/33; **eje factual del atomic a K=1 INUSABLE para
A/B — norma nueva DEC-090**) · latencia p50 +725ms. hp006 JP2→JP6 = mispairing de SÍNTESIS
expuesto por el rescate → dossier síntesis. Held-out no consumido. 443 tests.

**A3 SHIPPED A DEMO (5 jul):** PR #111 mergeada por Alberto + `ENUNCIADOS_MULTIVECTOR=on` en
Railway + **verificado en producción** (post-flip completo: smoke e2e local con flag efectivo;
RPC de enunciados llamado por 2 queries reales de Telegram — timestamps casan con query_logs;
AFP-400 responde con el hecho antes-inencontrable 'Fallo de Tierra'/MPS-400 citado; CAD-150
idéntica pre/post-deploy = 0 regresión; latencia 34-47s en banda histórica). Rollback = quitar
la env var.

**Qué sigue (decisiones de Alberto, sin dependencia entre sí):** (1) **packet doc_map**
(MIE-MI-310↔zxe [DB: ZXAE/ZXEE] · MIDT190↔sdx-751 [DB: ID3000] · 15092SP [DB: INA]); (2) **T2-T3
re-scopeado** (no gastar por famtie; si se retoma: Sonnet 5 + gates por-tramo, DEC-088); (3) '35'
→ regeneración dirigida (C) opcional. Luego: lever diversify (hp011 + '99+99'); conduct-level
clarify + calc-assist CON Alberto (el deep-lookup D queda aparcado flag-off como hipótesis de ese
modo); S4/F3 re-tag; workstream SÍNTESIS (dossier con la evidencia nueva JP2→JP6). Backlog:
BRAND_MAP→`catalog_gt.py`; re-homing FL*; 6 homónimos cola; ~630 candidates; dual-judge ~sept.

**s90 (DEC-079): F0 APROBADO (D1-D7) → contrato CANÓNICO; F1a slice vertical Morley CONSTRUIDO.**
`catalog_store.py` (la puerta: validate reglas-duras + resolve con contrato `expand`, check-homónimo
PRIMERO) + slice cargado (`data/catalog/`: gt nivel-1 + semilla s83, doc_map por document_id 114/114) +
Catalog gate en CI + 378 tests. **El slice cazó 3 clases de bug antes del bulk** (colisión
alias↔canonical, divergent-unknown expandiendo, CI sin gate). Smoke: hp011 `RP1r`→prefer Supra ✓,
hp018 `ZXe`→3 variantes ✓. **QA ADJUDICADO y APLICADO (s90b: P1-P8, correcciones de dominio HRZ2-8/EXP×3/BRH-BGL cross-brand) → F1a CERRADO. Gate: merge #101 → F1 bulk (31 marcas) → F2 query-side tras flag.**

**s89 (DEC-078): gold-review Clase A APLICADO (adjudicación de Alberto; #97/#98 mergeadas).** hp004 →
**PASS 5/5 unánime (+1, PASS-map ~10/39)**; cat024 → PARCIAL 5/5 (sin FALLOs; discrepancia 7-vs-17
verificada al píxel = MISMO modelo); cat009/cat020 sin movimiento (el juez completista encuentra la
siguiente arista) → **el plateau se confirma post-gold-edit; el lever restante del bucket OTRO = dual-judge**.
cat012 resuelto-solo (ya PASS 5/5). ES/EN → `docrel language-variant-of` añadido al contrato del catálogo.
**Pendiente de Alberto: contrato F0 (D1-D7, ~1h) → F1.**

**s88b (2ª tanda nocturna): (A) Fase 0 DRAFTEADA + paquete de adjudicación.** (1) **Contrato de gobernanza del
catálogo canónico** (`docs/IDENTITY_CATALOG_CONTRACT.md`, DRAFT dúo-hardened): modelo de datos (producto/alias/
paraguas/**homónimo**/relación/doc_map por `document_id`), gobernanza anti-Excel-opaco (jerarquía de fuentes,
blast-radius manda, QA por lote, tally con error-rate), consumo (cascada check-homónimo-primero + clarify-si-
divergent-adjudicado + fail-open), fases F1-F4 con gates y criterios medibles. Dúo COMPLETO: cross-model-con-tools
6/6 + sub-agente H1-H9 (críticos: la cascada exact-match reproducía el −2 hp011; convergente≠correcto demostrado
en la semilla). **GATE: tus D1-D7 (~1h)**. (2) **Paquete de adjudicación Clase A** (`evals/s88_goldreview_packet.md`):
5 casos con literal + edición propuesta + casilla ✅/✏️/❌ → tu gate baja a ~15-20 min.

### Antecedente s83·F2 (DEC-067)

**s83·F2: activo de IDENTIDAD MULTI-LABEL LIMPIO de los 1014 docs construido (1014 docs, 2761 productos) vía extracción dúo (Opus 4.8 + GPT-5.5, ~$145 Batches API) + adjudicación de Alberto de los 29 conflicts; regla de granularidad + fold-in base-unión dúo-validados ×3; branch-local en `main` (PR #90), NADA en DB.** Es el bloque F2 que DEC-066 señaló como el lever (`LEVER2_IDENTITY`). **s84 midió su CONSUMO = NO-OP en el eval (DEC-069)** → el activo vale para findability/catálogo/30+/corrección, NO para recall del eval. Detalle: DEC-067, `s83_identity_asset.md`.

### Antecedente s83·retrieval (DEC-066)

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

## s324d (17 ago 2026, mañana autónoma) — Lo que se puede avanzar sin pisar el tejado del dueño

Alberto mergeó la PR #276 y preguntó qué podía avanzar yo mientras él revisaba su parte. La respuesta buena a esa
pregunta no es «lo que sea»: es lo que no depende de su firma y deja el terreno listo para cuando firme. Cinco
cosas. **E2 re-derivado** después de los lotes de la noche (el snapshot conservador sigue PASS; el pleno pierde 5
golds conocidos y CCD-103 ya no está entre ellos: el dato que anoche resolvió `hp015` también asoma aquí). **El PLAN
podado** de 162 KB a 17 KB: veintidós «Estado anterior» y el «Qué sigue (s77)» con sus antecedentes viven ahora
íntegros en HISTORY, y el PLAN vuelve a ser lo que DEC-036 pedía —un documento que se relee entero al arrancar.
**#86**: el runner Fable cuenta sus `tool_use` reales y, si son cero con el modo tools activo, lo dice en el nombre
del fichero, en una nota lateral y por stderr; el `.md` no se toca porque su sha es el del texto del proveedor. En
la primera revisión emparejada tras el cambio, el recibo dijo «11 tool-calls reales» sin que nadie abriera el JSON.

**#89, la sonda.** Aquí la lección de la mañana. Endurecí los cinco defectos que el agente de medición había visto
(recibo pineado, span sin guard de cobertura, `SystemExit` que tiraba las reps, sin coste, carrier duplicado) y lo
llevé al dúo porque la deuda decía «con dúo, no de paso». Sol trajo siete hallazgos, tres críticos, y los tres eran
míos por omisión: los votos caídos del juez contaban como «no» (podían fabricar un NO_ALCANZABLE), un recibo parcial
podía llevar un veredicto completo, y mi guard de cobertura acreditaba «32» dentro de «132» y no exigía predicado.
Fable, emparejado, coincidió en el segundo. Los apliqué todos, y el instrumento nuevo se validó a sí mismo en el
smoke: mi oráculo pareado pasaba al juez el dict del generador en vez del texto —cinco votos caídos— y el veredicto
salió `INCONCLUYENTE_JUEZ_INCOMPLETO` en lugar de un NO falso. Antes de esta mañana ese error habría producido un
negativo limpio y creíble. Colateral honesto: el ALCANZABLE de anoche para `hp017#1` en modo `serve` venía con el
carrier duplicado a similarity máxima; pareado y sin duplicar, una rep da 0/5 —coherente con la prueba offline D1—
y no cambia la cifra de cabecera («1 hecho»), porque una rep no es una medida.

**#88 y #87.** Cincuenta y cinco documentos siguen con el `product_model` viejo en `documents` mientras el 100 % de
sus chunks ya lleva el canónico que E3 adjudicó; el retag está preparado con dry-run 55/55 y guardas T3, y espera
un «sí» porque escribe en una tabla de producción aunque serving no la lea. Y la re-ingesta OCR de TI-007 no es
autónoma: el repo no tiene OCR (PyMuPDF cuenta páginas; `struck_ocr` es política de display).

**Lección.** «Con dúo, no de paso» no es un ritual: en instrumentos de medición el dúo caza lo que convierte un
error de programación en un veredicto científico falso.

## s324d tarde (17 ago 2026, autónoma) — El día que el instrumento resultó ser el problema

Alberto pidió tres cosas por la mañana y marcó las cuatro prioridades por la tarde. Lo que salió no estaba en
ninguna de las listas.

**Perseguir un documento hasta el fondo.** TI-007 llevaba en el corpus con 47 chars y la deuda decía «hace falta
OCR». No hacía falta: el PDF tenía 2.246 chars de texto nativo y LlamaParse devolvía 3.708 en el campo `text` del
mismo JSON — con 34 en `md`. La ingesta hacía `md or text`, que sólo cae a `text` si `md` está **vacío**. Un `or`
se había comido un documento entero. La guarda salió con dúo (Sol y Fable, 10 hallazgos, 0 falsos positivos) y dos
guardarraíles del repo me pararon por el camino, ambos con razón: el freeze-contract que pinea el chunker por sha, y
el contrato de imports que prohíbe `rag → reingest`. El módulo acabó donde la matriz manda. TI-007 pasó de 47 a
3.601 chars con su procedimiento dentro.

**Tirar del hilo equivocado, y saberlo tarde.** El siguiente documento con castellano perdido no era el mismo caso:
ahí el markdown estaba entero y lo que lo mataba era el filtro de idioma por chunk, que en una ficha multilingüe
—con las seis traducciones concatenadas dentro de la misma celda— adjudica «alemán» a un chunk que lleva 4.122 chars
de español y lo tira. El 93 % del documento. Escribí el diagnóstico, escribí el fix, lo llevé al dúo… y sólo
entonces medí el alcance: 2.146 chars de boilerplate en 13 documentos. Marginal. El orden correcto era el inverso, y
lo dije en el cierre de la propuesta: la «pregunta cero» la apliqué tarde.

**El revisor que me corrigió el razonamiento, no el código.** Fable no pudo correr (le pasé un fichero de 293 KB como
semilla y reventó el presupuesto), Alberto adjudicó el fallback a Opus 5, y Opus dictaminó NO SÓLIDO. Tenía razón en
lo importante: mi «0 casos accionables» estaba medido **por documento con umbral 500** mientras el fix que quería
matar decide **por chunk con 400** — el mismatch de métrica que el Protocolo 4 lleva escrito con todas las letras y
que cometí igual. Y una frase mía era directamente falsa: los 842 documentos «sanos» no tienen cero texto ausente,
tienen menos de 500 chars, que es el mismo umbral de la cohorte: el suelo era tautológico. La opción que faltaba
—declarar el drop, contar lo que el filtro tira— la propuso él, cuesta cero y es la que resuelve la medición.

**Y lo que de verdad importaba estaba en otro sitio.** Medir los 15 hechos no-OK del ruler con cinco generaciones
sobre la MISMA vista congelada costó nueve dólares y dijo esto: **nueve son inestables y sólo seis son defecto
real**. El ruler, que etiqueta con una sola generación, clasifica ~60 % de sus fallos por azar. El 86 % del FULL
lleva una barra de error que no estábamos contando, comparar dos FULL con N=1 puede dar deltas de puro ruido, y la
cola de defectos que hay que atacar son seis, no quince. Después de dos días buscando levers de retrieval y de
serving para subir los OKs —con un único hecho pagable al final de todo—, resulta que la pregunta era otra: la
generación no es estable.

**Lección.** Tres veces se movió el árbol durante un dúo (agentes en background, y yo mismo commiteando) y rompió dos
emparejamientos: la regla ya no es «no muevas HEAD», es «nadie escribe mientras el dúo corre». Y la de fondo: cuando
el número que mides tiene más varianza que el efecto que buscas, todo lo que decidas encima es ruido con formato de
decisión.

## s324e (17 ago 2026) — El día que la pregunta dejó de ser «cuánto mejora» y pasó a ser «se puede enseñar»

Alberto cambió la prioridad a media tarde: «¿qué falta para compartir el bot con Directores Generales?».
La respuesta no estaba en el eval. Estaba en dos números que llevaban meses ahí sin que nadie los mirara
juntos: **96 consultas, un solo usuario** — él — y **seis pulgares abajo, cero arriba**. Y al abrir los
comentarios de esos seis, todos decían la misma cosa: el bot hablaba de productos de otra marca. El fallo
número uno para la confianza de un director estaba diagnosticado desde s321 y sin cablear.

**Lo que se construyó.** Una puerta de acceso por invitación de un solo uso, con caducidad corta y
revocación; manejo de errores que ya no puede dejar a nadie en silencio, con una taxonomía por causa y una
tabla pensada para que Alberto vea patrones; la prueba —no la promesa— de que un DG no puede ver la
conversación de otro; y la corrección de marca cruzada, cableada y apagada, esperando su interruptor.

**Lo que enseñó el proceso.** Los dúos cazaron tres críticos que ningún test habría encontrado: que la ruta
de voz podía persistir la transcripción de un técnico saltándose la única defensa contra el eco; que un
typo en una variable de Railway —`onn` en vez de `on`— dejaba el piloto abierto de par en par, porque el
código interpretaba «no te entiendo» como «adelante»; y que la puerta miraba quién escribía pero no dónde,
así que un DG podía meter el bot en un grupo y publicar las respuestas ante gente no invitada. Los tres
eran omisiones, no errores: cosas que nadie había pensado, no cosas mal hechas.

**Y lo que enseñó equivocarse.** La migración del control de acceso falló dos veces, y la segunda fue culpa
mía: diagnostiqué que el editor SQL abría una transacción, propuse un arreglo basado en esa teoría, y el
error que devolvió —`SAVEPOINT can only be used in transaction blocks`— demostró que mi premisa era falsa.
Lo que sí era cierto es lo que había visto con los ojos: las tablas no existían pese a que la validación
imprimía un `1` triunfal. La solución no fue adivinar mejor el comportamiento del cliente, sino **eliminar
la dependencia**: un fichero que crea tablas no lleva dentro una prueba que necesita deshacerse. Esa
lección quedó cableada como test, que es la única forma de que sobreviva a la memoria de quien la aprendió.

**Un test que corrigió a su autor.** Al poner cota a las cachés de la puerta, la poda natural —descartar lo
más antiguo— resultó ser exactamente la equivocada: una avalancha de denegaciones recientes habría echado
antes al director legítimo que al último intruso. Ahora caen primero los negativos, porque perder un «no»
cuesta una consulta y perder un «sí» cuesta el acceso de quien sí debía entrar.

**Dos veces me corrigió Alberto, y las dos tenía razón.** Cuando propuse plazos de retención de 6 y 12
meses para las tablas nuevas, preguntó por qué no los mismos que el resto: la consistencia era mejor
argumento que mi granularidad, y encima resultó que los 24 meses no son una convención sino un invariante
cableado en la base. Y cuando insistió en que el enlace debía servir una sola vez, me obligó a precisar
algo que yo había contado mal: lo atómico es el quemado del token, no el conjunto de canje y alta.

**Dónde quedó.** Todo en rama, nada desplegado, ningún flag encendido. Lo que falta no es código: es un
abogado, un merge y tres variables de entorno en el orden correcto.


## s324f (17-ago-2026) — La puerta se encendió, y el primer usuario real encontró en 30 segundos lo que 4.300 tests no veían

La sesión empezó verificando producción tras el merge: Railway desplegó, el bot arrancó y dejó en
el log el aviso de que la puerta estaba apagada — el código del piloto en producción e **inerte**,
que era exactamente el estado diseñado. De paso salieron dos correcciones que sólo se ven mirando
la máquina: la cabecera de la migración 015 seguía diciendo «NO APLICADA» cuando llevaba horas
aplicada, y el PLAN afirmaba que sin `BOT_ALLOWLIST_BOOTSTRAP` Alberto se quedaría fuera de su
propio bot. **Ya no era verdad** —la migración lo había dado de alta en la base—, pero la variable
seguía haciendo falta por otra razón que nadie había escrito: el **aviso de canje** se manda a los
ids de esa variable, así que sin ella la contramedida anti-reenvío que él mismo pidió se queda
muda. El riesgo no desapareció; se había mudado de sitio.

Alberto encendió la puerta. Arrancó con «puerta de acceso ACTIVA … bootstrap=1 ids, tope diario=30»
y su primera consulta la atravesó: el criterio O2 del piloto, verificado con tráfico real y no con
un test. Entonces escribió lo que escribiría cualquier director general al abrir el bot por primera
vez —«¿qué fabricantes tienes?»— y el bot le contestó con **22 modelos de 756**, agrupados bajo
`DESCARTADO`, `EN_unico`, `ES` y `PT`: etiquetas internas del proceso de ingesta presentadas como
si fueran familias de producto. Encima no pudo puntuarlo, porque los atajos no llevaban botones, y
la respuesta ni siquiera se guardaba: un 👎 habría señalado a un texto que no existía en ninguna
parte.

**Ninguna suite lo cazaba, y no por descuido: los tests congelaban esa conducta como correcta.**
Había uno llamado `test_catalogo_typing_log_sin_response_y_seudonimo` que verificaba justamente que
el atajo NO guardara la respuesta. Lo destapó un usuario en medio minuto.

El diagnóstico apiló cinco causas medidas —un `limit=5000` que PostgREST corta en 1000, sin orden;
un `.get(clave, "General")` que no cubre `None` y tiraba 630 de las 1000 filas que llegaban; una
columna `category` usada para dos cosas a la vez— pero la conclusión importante fue otra: **la
lección del tope de 1000 estaba escrita 200 líneas antes, en el mismo fichero**, con la historia de
los dos smokes que la enseñaron. Y la regla de no derivar el catálogo de los `product_model` de
chunks llevaba escrita desde un dúo anterior: «jamás los pm de chunks». No era una lección
pendiente de aprender. Era una función que nunca se migró, y la única superviviente.

El dúo r39 devolvió **13 hallazgos y ninguno de los dos dijo SÓLIDO**. Tres cosas que dejó, más
allá de la lista: Sol vio que el atajo **envía antes de registrar**, así que colgar el teclado tal
cual habría creado botones apuntando a filas inexistentes — el arreglo pasó a ser el orden, no el
teclado. Fable sospechó que la cifra «1000 productos» del autor fuera precisamente el max-rows de
PostgREST, es decir, que la medición padeciera el mismo fallo que denunciaba: resultó **falso
positivo** (el catálogo en fichero tiene 1696 → 1011 activos → 1000 con documentación), pero la
sospecha era exactamente la correcta y su exigencia —declarar cómo se midió cada número— se quedó.
Y los dos, por separado, cazaron la misma sobre-afirmación: «todos eran el mismo defecto». No lo
eran.

Los dos hallazgos de mayor severidad resultaron ser **mecanismos reales con efecto medido cero**:
filtrar por documento activo cuesta 7 productos de 1000 y ninguna marca; la tercera fuente de
fabricantes que Fable encontró no produce ninguna marca fantasma hoy. Se adoptaron igual, pero
declarando la medida — porque adoptar un hallazgo y obedecerlo no son lo mismo.

Alberto adjudicó dos reglas de negocio (un producto vendido bajo varias marcas aparece en todas;
nombres completos), y una de las dos llegó con una **premisa falsa del autor**: le habían dicho que
los nombres completos no exigían mantener ninguna lista, y el campo tenía cinco grafías de Morley y
un «unknown». La salida no fue volver a preguntarle, sino que su regla se aplicaba en el sitio
equivocado: al **buscar** por marca sí —el técnico busca por lo que pone en la etiqueta del
equipo—, pero al **listar** hay una fuente limpia que ya existía. Listar y buscar quieren fuentes
distintas.

Cerró con el panel web construido y verificado a mano (sin sesión no responde ninguna ruta, ni
siquiera con el esqueleto de la página; las acciones destructivas mueren tres veces: sin sesión,
sin token y desde otro origen), el paquete del abogado listo para reenviar con seis preguntas
concretas —dos de ellas nunca formuladas hasta hoy: se anota el nombre de un invitado antes de que
acepte nada, y la puerta decide antes del consentimiento, así que ese tratamiento no puede
apoyarse en el consentimiento de esa persona— y una pieza nueva que Alberto pidió generalizar:
cuando una respuesta no cabe, **se dice y se ofrece cómo pedir el resto**, con el espacio del aviso
reservado antes que el contenido para que sea imposible recortar en silencio.



## s324h (18 ago 2026) — La noche en que el dúo me corrigió ocho veces

El piloto llevaba horas vivo cuando Alberto mandó un audio con la transcripción ya arreglada y el
bot le dijo que no tenía información. La misma pregunta, tecleada, devolvía el listado. Medirlo
costó dos minutos: el plan acertaba con las dos formas — por voz nadie le preguntaba.

Lo que costó fue **no arreglarlo mal**. Escribí cinco versiones de la propuesta y el dúo tumbó las
tres primeras. La v1 metía una regresión del lever de mismatch **en el camino de texto**, que
funcionaba. La v2 añadía una frontera de fail-open que Sol mató por seguridad —podía contestar con
el manual de otra central— y Fable por observabilidad, cada uno sin ver lo del otro. La v3 declaró
«resuelto» un punto apoyándose en una sonda del clasificador que no probaba la cadena.

El patrón de los ocho hallazgos siempre fue el mismo, y es mío: **afirmar por encima de lo medido**.
«Siete rutas» siendo nueve. «Escalable a bilingüe» sin verificarlo. «Irrepresentable» cuando era una
puerta. «Radio medido» con un subconjunto. «Todos adaptados» con la suite en rojo. Y una
justificación de observabilidad escrita en un comentario del código que era simplemente falsa.

Tres veces el instrumento con el que iba a corregir algo resultó ser el que fallaba: un grep con un
filtro que se comía las líneas comentadas —y por poco acuso a Sol de un falso positivo—, un script
de migración que introdujo cuatro defectos que los tests no cazaban, y una prueba en directorio
temporal montada sin `data/`.

Al final el diagnóstico real no era «falta cablear una ruta»: era que el mismo default optimista
estaba replicado seis veces, y un default que miente convierte el olvido en un registro falso y
permanente. Eso sí se puede cerrar de raíz.

Y cerró CI, no el dúo. El gate llamaba a la red y pasaba en local porque yo tenía credenciales.
Sol y Fable leen el código; no lo ejecutan sin `.env`. El entorno limpio resultó ser un revisor que
ningún modelo sustituye.

## s325 (18 ago 2026) — «Dónde corre Claude»: el cloud deja de depender del PC, y el dúo tumba mi diseño dos veces

Alberto pidió montar el cambio de «where Claude runs» para gobernar el trabajo desde
el móvil. Lo primero que apareció no fue comodidad: el environment estaba en
**Default**, que es exactamente lo que en s315/s316 dejó fuera `OPENAI_API_KEY` y al
revisor Sol sin ejecutar — una sesión cloud no podía cerrar nada de impacto ALTO y
**nada avisaba**. Nace `cloud_smoke.py` para que eso no vuelva a pasar en silencio:
verifica superficie, historial git, imports reales, presencia de keys sin volcar su
valor y conectividad, y estampa recibo. Su contrato —nunca vuelca un secreto— se fija
en tests, no en el docstring.

Alberto adjudicó **contra mis dos recomendaciones**: un solo environment con todas las
keys y red Full, con el riesgo escrito delante (no hay secret store). Y acotó el
alcance a **Cloud + Dispatch**, dejando Remote Control documentado sin activar; no deja
hueco, porque las sesiones que abre Dispatch corren EN EL PC y ven OneDrive.

**Después vino la pregunta que cambió la sesión**: «quiero usar cloud sin depender de
tener el ordenador encendido». Medido, el único hueco real era el **extraction store**
(1.143 JSON / 354 MB, solo en OneDrive): los PDFs llevaban en el bucket desde #69. Se
subió a un bucket privado y nació el resolutor disco-primero-bucket-después.

**Y el dúo hizo su trabajo dos veces, ambas NO SÓLIDO.** En el diseño: faltaba un
consumidor entero, `ingest_new` resultó ser PRODUCTOR y no solo lector, y mi «descarga
perezosa» era falsa porque el mapa doc→sha recorre el store completo. En el código —la
ronda que casi me salto— apareció lo más caro: al renombrar una variable dejé cuatro
referencias huérfanas y `pipeline.run()` reventaba con `NameError` en sus caminos
normales… **y la suite pasó verde con el bug dentro**, porque no existía ni un test que
EJECUTARA `run()`. Hoy existen dos. También salió que el manifiesto se sobrescribía
ante cualquier error del GET (un 500 podía dejar el store con UNA entrada visible), que
los timeouts escapaban sin ser `StoreError` y que mi `--verificar` era **circular**:
comparaba el sha local contra el que declaraba el propio manifiesto, generado de ese
mismo local. Cuando dije «0 fallos cruzando SHA», medía menos de lo que sonaba.

De propina, un bug que solo mordía en la nube: `os.path.basename` sobre rutas de
Windows **no separa en Linux**, así que el mapa doc→sha habría salido vacío sin decir
nada justo al correr en cloud.

Alberto pidió entonces la pieza que faltaba: consistencia como **mecanismo, no
runbook**. El store tiene productores conocidos, así que publican al bucket en el mismo
acto en que escriben —Sol encontró que eran dos, no uno—, el verificador por hash es
red y no mecanismo, y la `config` de extracción es la versión: un extractor nuevo
estrena prefijo y no puede mezclarse con el anterior. Lo que quedó sin cerrar está en
#80, declarado: disco parcial que manda sin contraste, estado que no valida su config,
caché sin purga.

Cierre: cloud cubre evals, sondas, harness, enunciados, re-ingesta, DB, código y docs
con el portátil cerrado. Ingestar manuales NUEVOS sigue siendo local, y está escrito
como límite, no como pendiente.

## s324h — cierre VERIFICADO EN PRODUCCIÓN (19-ago-2026)

Alberto aplicó las migraciones **017** y **018**. La 017 se confirma en su propio `CHECK`
(ya lista `cuota_agotada`). La 018 la verifiqué contra el catálogo, porque «ejecutada con
éxito» no es la postcondición: un `COMMIT` limpio es compatible con que el `DEFAULT` siga
vivo. Medido: `column_default = NULL`, `is_nullable = NO`, `CHECK (source IN
('text','voice','error'))`. **Las seis capas del default mentiroso están cerradas.**

Y el smoke que quedaba pendiente **ya había ocurrido sin que ninguno lo supiera**. El recibo
no es un test: es `query_logs.route`, que separa `rag` de `catalog_shortcut`. La MISMA
pregunta cambió de ruta al cambiar de canal —14:16 voz → `rag` (152 chars, «no he encontrado
información relevante»); 20:36 voz → `catalog_shortcut` (494)— y ese 494 es **idéntico al del
turno tecleado de las 14:18**, con la pregunta redactada distinta. Paridad byte a byte en
tráfico real. El censo de las 10 filas de voz da **cero ASR perdidos**: la invariante que
`Procedencia` impone en el TIPO se cumple también en los datos ya escritos.

**Dato del piloto que reordena prioridades**: desde el 10-ago, la voz es **9 de 21 turnos
(43%)**. La paridad de voz no era un caso de borde — Alberto la puso primero y el tráfico le
da la razón. Reparto por ruta: `rag` 13 · `catalog_shortcut` 7 · `manufacturer_mismatch` 1 ·
sin ruta 1 (fila anterior a la instrumentación).

**`route` es un instrumento que no estaba en el radar** y mide en producción lo que hasta hoy
sólo medía el harness: qué ruta toma cada turno, por canal.

### s324i — el panel a Vercel: DOS rondas NO SÓLIDO, sin cablear

Alberto adjudicó `techassistant.fontiber.com` y, al saber que `DASHBOARD_USUARIOS` es variable
de entorno (revocar exige redesplegar), eligió **(a2)**: los usuarios a Supabase.

La v1 cayó con un crítico que **cambió su decisión**; la v2 con **tres**, dos de ellos fallos
de seguridad míos: (1) la tabla de credenciales sin RLS/FORCE/REVOKE, con el patrón YA escrito
en `migrations/016:266-292` — en `public`, PostgREST expondría usuarios y hashes scrypt;
(2) `HMAC(usuario|ip)` **fusiona** dos claves que el cerrojo cuenta por separado
(`auth.py:363`), así que rotar IP daba intentos ilimitados contra un usuario: mi «sirve igual»
DEBILITABA el cerrojo mientras yo creía mejorar la privacidad; (3) el contrato del digest `h`
es irrealizable con la firma de `vigente()`. Más: el HMAC con clave conservada es
seudonimización, y `docs/RGPD_RETENCION.md:67-75` ya rechaza ese framing.

**Decisión: no se cablea.** El patrón de los tres críticos es «no vi un contrato que estaba en
el repo», y eso empeora con contexto acumulado. Va a sesión fresca, con la v2 y sus diez
defectos enumerados como punto de partida.

## s324j (19 ago 2026) — El diseño del panel sobrevive a seis rondas del dúo, y el dúo me caza mintiendo tres veces por sesión de camino

Sesión cloud (web), arrancada con la PR #294 recién mergeada y un solo encargo del handoff de
s324i: escribir la v3 del panel a Vercel que cerrara los diez defectos de DEC-237, y pasarla por
el dúo ANTES de tocar código. Se hizo eso — y el dúo convirtió «una v3 y una ronda» en v3→v9 y
seis rondas completas, todas en la misma sesión.

**El arranque fue el protocolo, no la memoria**: los diez defectos salieron del log del dúo (no
del resumen del PLAN), y cada ancla se verificó contra el código antes de diseñar — auth.py
entero, la 016, el precedente RPC endurecido de s277, y el rechazo histórico de RPC de s296→s299
que vive en el docstring del canje. El auto-pushback de la v3 añadió tres cierres que nadie había
pedido (IdentidadNoDisponible para que una caída no mienta «credenciales incorrectas», charset
cerrado antes del filtro PostgREST, auditoría no reescribible por REST). No bastó: r1 la tumbó
con 3 críticos, y el peor era MÍO y de esa misma tarde — §5 y §1.3 prescribían conductas OPUESTAS
para el transporte caído, y lo cazaron LOS DOS revisores por separado.

**Lo que dejó la maratón** (64 hallazgos, 0 falsos positivos, regla C en todos): el sello de
credencial realizable donde vigente() era imposible; el cerrojo contar-al-admitir con siembra
antes del lock (FOR UPDATE no bloquea filas que no existen), upsert siempre (el DELETE de acierto
no deja admisiones sin contar) y advisory lock con su semántica dicha sin eufemismo; la clave ip:
APAGADA hasta medir XFF (el hallazgo de r5: con la IP compartida del proxy, 5 fallos de un
atacante eran un 429 GLOBAL — el gate decía «inefectivo» donde había denegación de servicio); la
retención por función hermana diaria con recibo (ampliar la pasada de 24 meses tocaba un contrato
vivo que afirma EXACTAMENTE 4 tablas); y la lección meta: tres veces en seis rondas el defecto
fue «mi prosa afirmaba más que el diseño» (el 503 «sin contar», el «formato completo», las «≤48h
garantizadas» que el canon desmiente porque un reloj roto aborta en silencio).

**El regalo colateral de r1**: anular una invitación está ROTA HOY contra Supabase real — r41
(s324f) arregló «la anulación queda sin firmar» escribiendo la firma en `nota`, y la 016 nunca
concedió UPDATE sobre esa columna. Un dúo cerrando un hallazgo abrió otro que ningún test sin red
ve. De ahí la puerta 9-bis: toda columna escrita tiene su GRANT, cruzado estáticamente.

**Cierre**: r6 terminó con Fable en «SÓLIDO» explícito y Sol sin un solo defecto de mecanismo
desde r2. Adjudiqué el cierre de las rondas de diseño (el guardarraíl anti-ritual existe para
esto) — la v9 es SÓLIDO-para-cablear, el GO es de Alberto, y la sesión de cableado corre SU dúo
sobre el diff. DEC-239 (renumerada de 238 en la propia sesión: la PR #295 viva de s325g ya había tomado DEC-238 — la lección de DEC-237 aplicada ANTES del merge, no después). Operativa: el primer Fable de r3 murió por presupuesto (el default de
300k; DEC-236 sigue pendiente de raíz) y corrió con 600k/16 tools el resto de la sesión, con
tool_use reales y ~20-30 anclas verificadas por ronda. Nota de higiene cloud: el digest de levers
no apareció inyectado en el contexto (el hook está cableado y el script funciona — verificado
ejecutándolo); esta sesión no opinaba sobre ningún lever, no bloqueó. La memoria indexada
(MEMORY.md) no está versionada en el repo y no se toca desde cloud; la traza canónica queda en
DECISIONS/PLAN/HISTORY.

## s324j — continuación (19 ago 2026): el panel, cableado; y el adversarial impidiéndome cerrar con medio dúo

Con el diseño v9 ya cerrado (seis rondas del dúo, DEC-239), la continuación fue CABLEARLO. Se leyó
la v9 entera y se implementó pieza a pieza contra su contrato: el sello de credencial en la cookie,
el backend de Supabase con la disciplina del señuelo heredada, el cerrojo distribuido
`panel_puerta`, la idempotencia por `op`, la firma `revocada_por` (que además cierra el 42501
LATENTE de hoy en la anulación), las dos migraciones con su ACL enumerada y sus postcondiciones, y
~90 puertas de test. Detalle que vale la pena: los tests PREDIJERON sus propias roturas — los dos
dobles de backend sin `sello` se rompieron EN el test con traza, que es exactamente donde S4-M4 del
diseño dijo que debían romperse. Para correr el gate de integración de verdad hizo falta instalar
Postgres 17 local (PG16 no basta: la propuesta s295 usa el privilegio `MAINTAIN`, 17+); 17/17
contra base real, incluida la ráfaga concurrente y el escenario adversarial del cap.

El dúo sobre el DIFF (Protocolo 3) fue lo más instructivo. El cross-model Sol corrió cuatro rondas
y cazó un fallo de SEGURIDAD real que ni el 2º revisor ni yo vimos en el cableado: `panel_puerta`
sembraba una fila `u:` antes de comprobar el bloqueo, así que un atacante ya cerrado por su `ip:`
seguía inflando el cap — una divergencia con el doble en memoria, que comprueba antes de sembrar.
Se corrigió reordenando la RPC. Y dos de MIS fixes de esa ronda fueron sobre-correcciones que Sol
revirtió (aceptar `'1 day'` en un autocontrol; quitar un trigger de CI que era una dependencia
real). La ronda de verificación no fue ritual.

El final es el mejor ejemplo de `feedback_my_bias` de la sesión. Estaba a punto de declarar el
cableado «sólido» con un «sello final» que corría SOLO el cross-model Sol, porque el 2º revisor
frontera Anthropic (Fable, y su fallback Opus) cayó por **crédito agotado** de la cuenta a mitad
del diff. Sol emitió un crítico PROCEDIMENTAL, y la regla C lo confirmó contra el canon:
`ADVERSARIAL_REVIEWER.md` dice literal que una credencial ausente deja `pending_fable` y «no
completa ni dispensa el dúo», y yo había citado DEC-236 (que es sobre el ahogo por CONTEXTO, no por
crédito) como si dispensara. No dispensa. Así que el cableado NO se declara sólido ni se mergea:
queda cableado + verificado + cross-model completo, con el 2º revisor PENDIENTE hasta que Alberto
recargue crédito. El adversarial existe justo para esto — para que no llame «hecho» a medio
control. La PR se queda en draft.
## s325g (19 ago 2026) — Los 50 segundos se van a la caché: el setup script entra en juego sin sacar la lógica del repo

Alberto adjudicó lo que s325d dejó medido y aparcado: mover la instalación de dependencias
al setup script del environment, que se cachea ~7 días como snapshot del filesystem. La
objeción que lo había congelado («no duplicar la lógica fuera del repo») se resolvió por
extracción, no por copia: la instalación entera —workarounds s315, centinela s323— vive
ahora en `.claude/hooks/install-deps.sh`, y el campo del environment queda en cinco líneas
que clonan `main` e invocan ese script. El hook de SessionStart no pierde la instalación:
la conserva como fallback autosanador (caché caliente → no-op de ~3 s medidos; caché fría o
requirements cambiados → instala como siempre), de modo que el peor caso del movimiento es
exactamente el comportamiento anterior.

El detalle que hacía o rompía el diseño: el centinela en `/tmp` no sobreviviría a un
snapshot si `/tmp` es tmpfs, y entonces la caché traería los paquetes pero el hook
reinstalaría igual. Se mudó a site-packages, donde marcador y paquetes viajan juntos por
construcción. Verificado en la sesión: dry-run de ambas ramas, doble corrida real
(instala con la tolerancia de langdetect disparándose tal cual s315 → salta en 3,1 s),
hook end-to-end en 2,3 s. Lo inverificable desde aquí quedó declarado: el snapshot real y
el clone dentro del setup solo se confirman en la primera VM nueva tras pegar el campo.
Y el casi-accidente del cierre: `.gitignore` ignora `.claude/hooks/*` con excepciones por
fichero — sin añadir la de `install-deps.sh`, el commit habría salido SIN el fichero
central y el setup script habría clonado un main donde no existe, con el fallback del hook
tapando el hueco indefinidamente. Cazado revisando `git status` antes de commitear.

Tres rondas de revisor (Fable standalone, con la key derivada del alias de s325f — primera
sesión que la usa). La r1 no pudo leer los shells (`.claude/` está en el SKIP del sandbox)
y aun así cazó el over-claim del peor caso y la falta de señal observable; la r2, con los
shells adjuntos, cazó el hueco material — la huella no incluía el PROPIO script, así que un
cambio del instalador habría viajado ~7 días sin aplicarse — más la mal-atribución de
`deps_cache` en la sesión de build; la r3 devolvió SÓLIDO dejando dos residuos que quedaron
escritos (drift de versiones sin pin, semántica de /proc/uptime — esta última medida cierta
en esta VM). Adjudicación Regla C completa en el log: 14 hallazgos, 13 confirmados.

La sesión venía de cerrar el ciclo del PR #289 (el recibo NO LISTO quedó superado por el
recibo LISTO de la re-corrida y se cerró sin merge), y corrió con la key de Anthropic
derivada del alias `ANTHROPIC_API_KEY_SCRIPTS` que s325f cableó — primera sesión que usa
esa vía para el revisor del Protocolo 3.

## s324j-bis (19 ago 2026) — El seguimiento post-merge del panel: los 3 medios de Sol cerrados y el dúo, POR FIN, completo

La PR #296 (el cableado del panel, DEC-240) se mergeó con el sello final del dúo aún
abierto: Sol acababa de cazar 3 medios reales (el cap con fuga de +1, la carrera
`acierto`↔`admitir` sin ejercitar con hilos, el gate pg con cobertura parcial) y el 2º
revisor frontera acababa de morir por segunda vez ahogado en el diff de 3768 líneas (la
clase DEC-236). Alberto recargó el crédito de Anthropic a media sesión — «para que
sigas» — y el seguimiento se hizo en rama reiniciada desde `main` (PR nueva; una PR
mergeada no se reabre).

Lo memorable de la sesión no son los tres fixes (están en DEC-241) sino el pulso con el
control: **cinco rondas de Sol convergiendo de crítico a nit** — dos críticos
PROCEDIMENTALES seguidos cazándome el mismo intento con dos disfraces («cerrar el
pending_fable con el delta» y luego «supersederlo»): heredar cobertura que no existe.
La resolución honesta quedó escrita: el delta SELLADO con dúo completo, y el resto del
cableado declarado como gap abierto de 2º frontera, a decisión de Alberto. Y el guard
del techo creció de una condición a tres (cardinality>cap, cap NULL, claves NULL) porque
cada ronda encontró el NULL que faltaba — con test parametrizado que deja rojo quitar
cualquiera de las tres.

El 2º frontera (Fable, pin s316d) completó A LA PRIMERA con el remedio DEC-236 aplicado
de verdad: briefing compacto acotado al delta + presupuesto del runner subido a 600k
(dos intentos previos murieron en el preflight con el default de 300k). Veredicto
SÓLIDO con 3 menores de framing — uno de ellos el sesgo conocido del autor cazado en
vivo: el comentario del fixture atribuía el bootstrap a un `display_name` que el arnés
jamás inserta (sobrevive por el COALESCE de la 016). Cero falsos positivos en las dos
patas, seis tallies completados con regla C, y las cifras del cierre citadas de
ejecución real: gate pg 22/22 contra Postgres 17.11, suite 4517/67/2.

A media sesión Alberto pidió trabajar en español, avisó del merge de la PR #297 (solo
TECH_DEBT, sin roce) y cambió el modelo de la sesión a Fable 5 «porque Opus 4.8 estaba
dando demasiadas vueltas» — el aviso llegó justo cuando las rondas convergían a nits, y
la respuesta correcta fue la que pedía: cerrar la adjudicación de una vez en lugar de
otra vuelta de dúo.

## s324j-ter (19 ago 2026) — «Pago el segundo revisor»: las tres tandas que cerraron el gap

Alberto mergeó la #298 a los seis minutos de abrirse, adjudicó pagar la revisión
2º-frontera del resto del cableado, y preguntó — en llano — qué es lo que estaba
pasando. Las tres tandas (identidad, puerta HTTP, gestión) completaron a la primera
con el remedio DEC-236 por fin operativo: briefing compacto por trozo + presupuesto
600k. La estructura que satisface el canon sin re-pagar: los bytes eran IDÉNTICOS a
los que Sol auditó en sus 4 rondas (git diff vacío, escrito en DEC-243 — renumerada de 242 al chocar con el DEC-242 de s325h-c en el merge), así que
Fable standalone completa el dúo por fichero.

Trece hallazgos, trece confirmados, cero falsos positivos — y la mitad fueron el
revisor cazando MIS briefings en vez del código (punteros errados, orden invertido,
GRANTs mal atribuidos): el framing falso ES hallazgo, y esta vez el sesgo del autor
quedó tallado tres veces. Del código salieron tres cierres reales: el validador
estricto tragaba params duplicados en silencio (el dict() colapsaba `n=999,n=32768`),
la invariante señuelo↔params vivía en una convención de script (ahora es un flag del
validador que el alta exige), y `csrf_valido` convertía un token no-ASCII en
TypeError en vez del 403 prometido (compare_digest sobre str exige ASCII — ahora
compara bytes). Más un docstring de api/index.py que aún contaba el cerrojo en
memoria de la era pre-019, y el charset de `op` subido del regex del panel al CHECK
de la base.

El panel queda con dúo completo en TODO el cableado y una lista de «falta» que ya es
solo operación: merge de la PR de tandas, GO, dos gates de exponer con dueño, y el
runbook de aplicar/configurar/smoke.

## s324j-quater (19 ago 2026, noche) — El panel, VIVO

Alberto creó el proyecto de Vercel (propio, DEC-244) y el primer deploy murió
exactamente donde estaba previsto: 541 MB de requirements del bot contra el
límite de 500. El arreglo (`api/requirements.txt` con la clausura real: httpx y
python-dotenv, más el test que impide que se pudra) entró por la #302 y Vercel
lo validó solo — preview Ready antes de que nadie lo pidiera. El segundo 500
fue el diseño defendiéndose: la sonda de arranque —que resultó SÍ correr en
Vercel, medición que zanja el «lifespan no garantizado»— encontró la base sin
migrar y se negó a arrancar, con el error exacto escrito en los logs.

Alberto dijo «aplícalas tú»: 019 y 020 entraron por el conector de Supabase,
cada una entera y transaccional, con las postcondiciones en verde y el reloj
diario activo a la primera. El smoke de producción salió de libro: 303 con
cuerpo vacío, /entrar en 200, ni rastro de SUPABASE en el fuente, CSP y DENY
servidas. https://technical-bot-lake.vercel.app — «-lake» porque el nombre
pelado ya era de otro. Queda el alta (contraseña de Alberto, no mía) y los dos
gates de exponer con dueño.

**Cierre (19-ago noche):** Alberto se dio de alta y ENTRÓ — la cadena entera
(scrypt, sello, cookie, cerrojo vía PostgREST) verificada con el login real.
Sesión cerrada con todo mergeado y sin pendientes; lo siguiente que pidió:
las métricas que quiere añadir al panel (feedback suyo, sesión próxima).

## s326 (19-ago-2026) — Métricas de uso/calidad para el panel: la mitad ya estaba capturada; propuesta v1 sin cablear

Alberto pidió cinco métricas de usabilidad para el panel (tipología de pregunta, fabricantes,
modelos, feedback por pregunta con sub-feedback y motivo, preguntas por usuario) con la idea de
una tabla por-pregunta + pivot + gráficas + filtros. La sesión midió antes de opinar: 109 filas
en `query_logs` (2 usuarios, pre-piloto), `product_models` al 70 %, la `category` legacy muerta
(1/109), y la captura de feedback de s294 COMPLETA (verdict + `reason_class` + «te lo explico»
→`comment`) — el gap real es de EXPOSICIÓN y de dos dimensiones que faltan (tipología,
fabricante), no de captura. Propuesta v1 escrita y NO cableada
(`evals/s326_panel_metricas_uso_propuesta_v1.md`): tabla derivada `query_clasificacion` (1:1,
CASCADE, sin id de persona) + job batch determinista-primero (rutas y catálogo a $0; Haiku solo
para la categoría de filas `rag`; taxonomía cerrada versionada, el «otros» se limpia y se
re-corre global — céntimos) + vistas semanales nuevas y página Explorador con filtros fijos;
bonus `bot_marcas_sin_corpus` (demanda no cubierta = señal M&A, el `query_gaps` de TECH_DEBT #8).
Quedan las 4 adjudicaciones de Alberto (drill-down con prosa —el «fuera de v1» de DEC-231—,
taxonomía, identidad del por-usuario, coste) y el dúo al cablear. El bot no se toca en ninguna
pieza. **Adjudicado en el hilo (19-ago tarde)**: taxonomía v1 OK · por-usuario con ALIAS de
allowlist OK · coste OK; el drill-down con prosa quedó explicado con opciones (a/b/c) y
pendiente de Alberto.

**Cierre s326 (misma tarde-noche):** la adjudicación que faltaba llegó en minutos —
**opción (a): prosa completa**— y la sesión cableó el paquete entero: migración **021**
(`query_clasificacion` + 8 vistas con postcondiciones que comprueban TODO lo que revocan),
`src/clasificacion.py` (raíz PURA: el catálogo entra inyectado, la matriz de imports ni se
toca), el seam `CLASIFICADOR_PREGUNTAS` (off; con guard para el PTB sin job-queue), el CLI
con recibo, y la pestaña **Explorador** con filtros de listas cerradas. El dúo corrió
SECUENCIAL a conciencia: Sol xhigh sobre el diff vivo devolvió **7/7 confirmados, 0 FP** —
el mejor: el barrido más-antiguo-primero habría dejado filas nuevas PERMANENTEMENTE sin
clasificar al pasar de 20k (reescrito a dos consultas anti-join auto-drenantes); el más
delicado: la etiqueta «sin alta · id N» correlacionaba un identificador directo con conteos
y prosa (fuera el id; trinquete en el gate ACL) — y `RGPD_RETENCION.md` afirmaba tres cosas
que el código nuevo desmentía (enmendado, con la subsección s326 y la tabla en la matriz).
Con los cierres aplicados, **Fable revisó el árbol FINAL** (sin emparejar por bytes, correcto
y documentado): **SÓLIDO estructural en seguridad/ACL/RGPD**, 1 medio (mi docstring describía
la fuente vieja de la whitelist — el sesgo conocido: la prosa contando un diseño que ya no
es) y 4 menores, todos aplicados. Smoke REAL contra producción ($0,003): el atajo de Kidde
se clasifica por regla a $0, el multi-turno hereda el modelo del contexto (2X-AF1→Aritech) y
«¿tienes productos de Luka Modric?» cae a `otros` sin inventar marca. Queda, en orden:
aplicar la 021 → backfill con gate de acuerdo ≥85 % → (opcional) flag on → addendum del
abogado antes de invitar DGs al panel. DEC-245.

**Cierre s326-b (noche):** con el GO de Alberto la **021 entró en producción** por el conector
(entera; postcondiciones + verificación externa verdes) y el **backfill clasificó las 109
preguntas del histórico** (10 por regla a $0, 98+1 por Haiku, 0 fallos, $0,085, recibo en
`evals/s326_backfill_v1.json`). Por el camino, el backfill destapó un incidente de libro: el
upsert `merge-duplicates` de PostgREST re-escribe también la PK, chocando con el trinquete del
gate ACL — se cerró SIN ablandar el trinquete (fila nueva → INSERT ignore-duplicates; fila
vieja → PATCH sin PK), medido con cuatro llamadas mínimas. Y la vista de demanda-no-cubierta
pagó en su primera lectura: «death knife», «death knob» y «nfs» — el ASR destrozando «Detnov»
(DEC-233), por fin como métrica. Distribución del histórico: catálogo 46 · specs 22 ·
configuración 13 · otros 9 (8 %) · compatibilidad 7 · instalación 6 · averías 6. Queda el gate
de acuerdo de Alberto (muestra de 35 en el hilo), el flag opcional y el addendum del abogado.

**s326b (19-ago, noche) — el gate dijo NO, y esa era la gracia.** La muestra de 35 volvió de
Alberto con siete adjudicaciones: fusionar instalación+configuración y catálogo+especificaciones
(«son difíciles de diferenciar»), acotar compatibilidad a «¿se pueden conectar dos equipos,
típicamente de marcas distintas?», mandar los mensajes de una sola palabra a `otros`, y —la que
cambió el diseño— «la 26 no es una pregunta, es feedback». De ahí nació `no_es_pregunta`, que
resultó ser el **10 %** del histórico: sin ella, cada gráfica de tipología llevaba un denominador
contaminado con acuses de recibo y quejas. La 022 entró al segundo intento: el primero puso el
UPDATE antes de retirar el CHECK viejo y murió con 23514, revirtiendo entero sin tocar una fila
—la transacción haciendo exactamente lo que la 016 enseñó a exigirle—, y la lección quedó escrita
en la cabecera del fichero. Cuatro pasadas del histórico (v2→v5) por **~$0,49 y ~6 minutos**,
109/109 y cero fallos: la promesa de «re-taxonomizar cuesta céntimos» dejó de ser una promesa. De
las tres iteraciones de descripciones, dos cerraban adjudicaciones de Alberto que el clasificador
incumplía y **la tercera reparaba un daño que causaron mis propios refuerzos** (tanto insistir en
«escueto → otros» empujó allí preguntas de especificaciones perfectamente claras); el tuneo se
paró con un residual conocido en pie, para no ajustar el prompt a 109 filas. DEC-246.


## ARCHIVO — «Estado actual» del PLAN en s324j (19 ago 2026), retirado en s327

> Movido aquí al reconciliar el PLAN en s327: llevaba tres sesiones congelado en s324j mientras
> el trabajo iba por s326/s326b/s327. El PLAN se relee en cada arranque y se mantiene COMPACTO
> (DEC-036); el *por qué* de todo lo de abajo vive en DEC-240…DEC-244, y su narración en las
> secciones s324j de este mismo fichero. Se conserva verbatim como recibo, no como estado.

### Estado actual (s324j — 19 ago 2026; panel MERGEADO + seguimiento del dúo SELLADO)

**La voz ya hace lo mismo que el texto (DEC-235, PR #284 mergeada).** El piloto destapó que
`handle_voice` nunca llamaba a `plan_turn`: las NUEVE rutas de atajo eran inalcanzables hablando
— la misma pregunta se contestaba tecleada y se rechazaba dicha. La causa no era la ruta que
faltaba: era el mismo default `= "text"` replicado SEIS veces, que hacía que olvidar la
procedencia registrase en silencio un audio como si se hubiera tecleado. **Las SEIS capas
cerradas**: Fase 1 (`Procedencia` + preludio compartido), Fase 2 (`TurnRequest` /
`build_turn_request`, PR #287) y la sexta —el `DEFAULT` del esquema— con la **018 APLICADA por
Alberto** (verificado 19-ago: `column_default = NULL`, `is_nullable = NO`, CHECK
`text|voice|error`). La **017** también (el CHECK ya lista `cuota_agotada`).
Suite 4426 verde. 8 rondas de dúo; el gate verificado que DISCRIMINA (12/24 fallaban antes).

**VERIFICADO EN PRODUCCIÓN (19-ago), no sólo en la suite.** El recibo está en `query_logs.route`,
que separa `rag` de `catalog_shortcut`, y lo prueba **la misma pregunta cambiando de ruta al
cambiar de canal**:

| hora (18-ago) | canal | `route` | `response_length` |
|---|---|---|---|
| 14:16 | voice | `rag` | 152 — «no he encontrado información relevante» |
| 14:18 | text | `catalog_shortcut` | **494** — el listado de 14 |
| **20:36** | **voice** | **`catalog_shortcut`** | **494** |
| 21:42 | voice | `catalog_shortcut` | 1041 — Kidde, 36 centrales |

Los dos `494` son **la misma respuesta byte a byte** por canales distintos y con la pregunta
redactada distinta: es la paridad del gate ocurriendo con tráfico real. Y el censo de las 10 filas
de voz da **cero ASR perdidos** — la invariante que `Procedencia` impone en el TIPO se cumple
también en los datos que ya estaban escritos.

> **⚠️ El párrafo que sigue quedó REFUTADO el mismo día, por s325h-e/DEC-247**: la caché del
> environment SÍ puede persistir `site-packages` (al menos a veces — no es una propiedad
> uniforme, y el hueco sigue sin explicar). Se conserva tal cual porque este bloque es un
> **recibo** de lo que el PLAN decía al retirarlo, no un estado: la traza de un diagnóstico
> invertido vale más que un archivo limpio (mismo criterio que DEC-247 aplicó a DEC-242).
> El estado vigente de este frente vive en el «Estado actual» del PLAN.

**Cerrado (s325h-c)**: Alberto pegó el Setup script y se verificó en VM nueva — **NO baja a
~30 s**: 99 s de boot a deps listas, 163/164 entradas de site-packages escritas post-boot. Las
deps no estaban en disco al arrancar; DEC-238 queda degradada a redundancia inocua
(DEC-242 · `evals/s325h_setup_script_verificacion_v2.json`).
**La sospecha se desplaza fuera del repo, sin cerrarse** (s325h-d, contrastado con la doc
oficial): la caché conserva lo que el setup script escribe sin exclusión de rutas documentada, y
el script «solo corre cuando NO existe caché». Alberto declara no haber tocado script ni dominios
desde que lo pegó ⇒ ninguna causa de rebuild documentada aplica. Se retira la vía «venv bajo un
prefijo que viaje». **Pendiente ANTES de concluir nada**: abrir una sesión nueva y correr
`python scripts/cloud_smoke.py` → leer `deps_cache` (la 1.ª línea del hook NO basta: dos de los
tres desenlaces son idénticos a simple vista — DEC-242 addendum).

**Abierto, con dueño**: «no te he entendido» (el ASR devuelve algo que no es marca → el bot afirma
un hueco de corpus que no existe; el arreglo es GENERAR las variantes de las 30 marcas como ya se
generan las de los modelos, no coleccionar confusiones) · el gate de ASR con ≥30 audios reales
(DEC-234: el bake-off no lo cumplió) · #86 el runner de Fable pega 191 KB y ahoga a su revisor
(DEC-236, diagnóstico medido) · bloque A del catálogo (`detnov:ccd-103` → convencional, regla
adjudicada, control independiente: reproduce 14 citas CAD sin contradicción).

#### QUÉ SIGUE (entonces) — el panel a Vercel: MERGEADO (#296) + seguimiento SELLADO (DEC-241); falta el GO y aplicar

**El cableado está en `main`** (PR #296, mergeada por Alberto 19-ago; diseño DEC-239, cableado
DEC-240) **y el seguimiento post-merge está listo en PR aparte** (DEC-241): la PR #296 se mergeó
con el sello final del dúo abierto, y ese sello (Sol) cazó 3 medios que ahora están cerrados —
**S-M1** el cap tenía fuga de +1 (el DELETE no excluía las claves de la propia admisión; cierre:
`<> ALL(claves)` + guard de tres ramas NULL-safe; cota declarada INDUCTIVA), **S-M2** la carrera
`acierto`↔`admitir` con hilos (ley de conservación con siembra; cierre por tres patas), **S-M3**
el gate pg congela sus dependencias reales y prueba la 020 contra la **016 canónica** (la copia
estrecha era una 016 de ficción). **El dúo del seguimiento está COMPLETO**: 5 rondas Sol xhigh +
**Fable emparejado en la final — SÓLIDO** (3 menores de framing, aplicados; 0 falsos positivos).
Remedio DEC-236 que funcionó: briefing compacto + `FABLE_REVIEW_MAX_TOTAL_TOKENS=600000`.
**Verificado**: gate pg **22/22** contra Postgres 17 real (control negativo del discriminante
ejecutado); suite **4517 passed, 67 skipped**.

**El gap 2º-frontera está CERRADO (DEC-243)**: Alberto pagó la revisión por trozos y las TRES
tandas completaron a la primera (briefings compactos + presupuesto 600k — el remedio DEC-236).
Identidad **SÓLIDO con reservas** (3 cierres cableados: estricto anti-duplicados +
`exigir_produccion` en el alta + csrf sobre bytes), puerta HTTP **SÓLIDO** (rojo documental:
docstring legacy de `api/index.py` reescrito), gestión **SÓLIDO** (charset de `op` al CHECK de
la 020). 13 hallazgos, 13 confirmados, 0 falsos positivos. La #298 (seguimiento) también está
MERGEADA. Con esto TODO el cableado del panel tiene dúo completo.

**LIVE (19-ago noche): el panel está DESPLEGADO en https://technical-bot-lake.vercel.app**
(proyecto Vercel propio, DEC-244; `api/requirements.txt` mínimo tras el 541MB>500 del primer
deploy) **y las migraciones 019/020 APLICADAS en producción** (vía conector Supabase, enteras y
transaccionales, postcondiciones verdes, reloj diario activo). Smoke verificado (303 vacío →
/entrar 200, sin SUPABASE en el fuente, CSP/DENY). Medido: el lifespan ASGI SÍ corre en Vercel
— el fail-CERRAR de arranque se observó en producción con la 019 aún sin aplicar.

**Lo que FALTA para USARLO, en orden**:
1. ~~Mergear las PRs~~ HECHO (#301 tandas, #302 requirements — mergeadas por Alberto).
2. ~~El GO de despliegue~~ DADO por los hechos (Alberto creó el proyecto y ordenó aplicar las migraciones).
3. ~~El ALTA de usuarios~~ HECHA (19-ago noche): Alberto se dio de alta y **ENTRÓ** — el login
   real ejercitó la cadena entera (scrypt, sello, cookie firmada, cerrojo `panel_puerta` vía
   PostgREST). El panel está OPERATIVO de punta a punta.
4. **s326: las MÉTRICAS del panel — adjudicada ENTERA y CABLEADA (propuesta mergeada en
   #305; el cableado va en PR aparte, rama `claude/technical-bot-dashboard-metrics-jpbrns`).**
   La lista de Alberto (19-ago): tipología · fabricantes · modelos · feedback por pregunta
   (sub-feedback + motivo en texto) · por-usuario. Propuesta:
   `evals/s326_panel_metricas_uso_propuesta_v1.md`. **Adjudicaciones (19-ago, en el hilo):
   drill-down con prosa = OPCIÓN (a) completa · taxonomía v1 OK · por-usuario con ALIAS de
   allowlist OK · coste OK.** Cableado: migración **021** (`query_clasificacion` + 8 vistas,
   postcondiciones dentro) · `src/clasificacion.py` (raíz pura, catálogo INYECTADO — la
   matriz de imports ni se toca) · seam `CLASIFICADOR_PREGUNTAS` (default off =
   conducta del bot idéntica; nada corre en la ruta de respuesta) ·
   `scripts/clasificar_preguntas.py` (backfill/re-taxonomización con
   recibo) · página **Explorador** con filtros de listas cerradas. **Para USARLO, en orden**:
   (i) ~~aplicar la 021~~ **APLICADA** (19-ago noche, conector, GO de Alberto; DEC-245 add. 2);
   (ii) ~~backfill~~ **HECHO** (109/109, $0,085); (iii) ~~gate de acuerdo v1~~ **CORRIDO Y
   FALLADO — y eso lo puso en marcha todo** (~80 % < 85 %): Alberto adjudicó SIETE cambios,
   nació la **taxonomía v2** (fusiones catálogo+specs e instalación+config, compatibilidad
   acotada a «¿funciona X con Y?» entre marcas, y la clase nueva `no_es_pregunta` = 10 % del
   histórico), se aplicó la **022** y el histórico se re-clasificó **cuatro veces** (v2→v5) por
   **~$0,49 y ~6 min, 109/109 y 0 fallos** — el ciclo del «otros» ejecutado por primera vez y
   MEDIDO (DEC-246); (iv) **PENDIENTE: el gate de acuerdo de la v5** — muestra nueva entregada
   a Alberto en el hilo, con un residual declarado («especificaciones técnicas del NC» en
   `otros`, 1/109) y dos gaps: `catalogo_especificaciones` = 61,5 % (categoría dominante por la
   fusión que él pidió) y `no_es_pregunta` mezclando ruido con quejas de calidad;
   (v) opcional `CLASIFICADOR_PREGUNTAS=on` en Railway para la corrida automática cada 6 h
   (sin ella, re-correr el script tras tráfico nuevo).
   **Gate de EXPONER nuevo que nace aquí: addendum del Explorador (prosa de
   preguntas/comentarios, adjudicación (a)/DEC-231) al paquete del abogado.**
5. **Los gates de EXPONER que siguen abiertos** (v9 §13): plazo `[DECIDIR: Alberto]` de `panel_usuarios` ·
   panel en el paquete del abogado (que NOMBRA la purga 24m pendiente de `bot_invitaciones`) ·
   medición XFF antes de encender la mitad `ip:` del cerrojo (`INCLUIR_CLAVE_IP` sigue en False;
   NO bloquea el live — el cerrojo por usuario funciona desde el día 1).
6. ~~Aplicar 019/020 + proyecto Vercel + variables + smoke~~ HECHO (19-ago noche; recibos en
   el runbook). Runbook: `docs/DASHBOARD_DESPLIEGUE.md`.

**Ya arreglado en el cableado — un LATENTE de hoy** (S-C1): anular una invitación estaba ROTA
contra Supabase real (`gestion.py` firmaba en `nota`, la 016 no concedía `UPDATE (nota)` → 42501);
la 020 lo cierra de raíz con `revocada_por`.


## s327 (20-ago-2026) — La noche de los tres encargos, y el revisor cazándome citando un fichero que no existía

Alberto se fue a dormir dejando tres encargos y una adjudicación de diseño. Los tres encargos se
cerraron. La adjudicación resultó ser lo importante.

**«Separar lo que es pregunta de lo que no.»** En s326b habíamos hecho nacer `no_es_pregunta` como
una categoría más de la taxonomía, y funcionaba: el 10 % del histórico dejó de contaminar los
denominadores. Alberto miró eso y dijo que no era el sitio. Tenía razón por un motivo que yo no
había visto al diseñarlo: **el tema de un mensaje y si el mensaje pide algo son dimensiones
ortogonales**. Con una sola columna, una queja de un técnico —«me has pasado información de la
ID3000 que no es de Detnov»— obligaba a elegir entre etiquetar su tema o marcarla como no-pregunta,
y perdías la otra mitad. Con dos ejes no hay que elegir: las no-preguntas conservan su tema y se
miran aparte. La migración 023 abrió la columna, las ocho vistas de análisis pasaron a filtrarla, y
la 024 arregló lo que se me había escapado —los **votos** seguían contándose sobre no-preguntas—.

La regla que Alberto dictó es literal y barata: **lo que termina en «?» es pregunta**, punto. Eso lo
decide el código, sin LLM y sin coste, y —esto importa— se aplica **DESPUÉS** de parsear la
respuesta del modelo, porque manda sobre él. El resto se infiere por contexto, y ante la duda se
clasifica como pregunta. Todo el diseño sesga hacia el falso positivo a propósito: colar un acuse de
recibo en el análisis cuesta ruido; perder la pregunta de un técnico cuesta la pregunta.

Y aquí es donde la sesión se puso interesante. Sol, en su ronda, señaló que mis recibos probaban
**ejecución** (109/109, 0 fallos, coste) pero no **calidad**: nadie había comprobado si el eje deja
fuera del análisis una pregunta real. Hice el censo —completo, no muestra: 93 de 109 los resuelve la
regla determinista sin criterio de nadie, y los 16 que decide el modelo se revisan uno a uno— y
escribí en el briefing «cierre S3: ver `evals/s327_eje_pregunta_medicion_v1.md`». Luego lancé a
Fable. **Y creé el fichero catorce minutos después de lanzarlo.**

Fable devolvió NO SÓLIDO con eso de crítico: *«el cierre S3 cita un fichero que NO existe en el
snapshot; o no se versionó, o el censo no existe»*. Es el patrón exacto que el Protocolo 1 existe
para cortar —declarar cerrado lo que el otro no puede verificar—, cometido **dentro del aparato
montado para cortarlo**, y en el hallazgo de un revisor que yo mismo pago para que no dependa de
Alberto ser el anti-bias. El cierre no fue discutirlo: fue versionar el artefacto y **re-derivar sus
cifras contra la base de producción** en vez de contra mi memoria — 109 filas, 93 terminan en «?»,
102 marcadas pregunta, 7 no, cero sin clasificar, todas en taxonomía v8. Los números cuadran con el
censo (102−93 = 9 decididas por el modelo, más 7 no-preguntas = los 16 auditables), y ahora
cualquiera puede re-correr la consulta. La regla que se lleva el Protocolo 4 es de una línea: **el
artefacto se versiona ANTES de citarlo.** Un cierre anclado a algo que el revisor no puede abrir no
es una verificación, es una promesa.

Los otros cuatro de Fable fueron del mismo estilo incómodo y útil: el presupuesto de tiempo que Sol
me había hecho poner en la portada **no estaba en `/metricas`**, que lee catorce vistas y pinta la
tabla entera de cada una — o sea, la página más expuesta al 504 era justo la que se quedó sin
cubrir. El briefing decía v7 donde el YAML decía v8. Un comentario duplicado en la 024. Y un hueco
que decidí **no** tapar: «¿cuántos lazos» —apertura sin cierre, que el teclado del móvil español
produce a todas horas— no la coge la regla y cae al LLM. Ampliar la regla por mi cuenta sería
re-litigar una adjudicación de Alberto, que fue explícita sobre el signo **final**; se declara en el
código y se deja.

De paso se pagó una deuda **el mismo día que se disparó su trigger**. La #91 se había abierto la
noche anterior diciendo «la próxima migración que toque `query_clasificacion` trae gate», y la 023
la tocó. Once casos contra un PostgreSQL 17 real —16 no vale: el arnés usa el privilegio `MAINTAIN`,
que es de 17— ejerciendo el **efecto** y no el texto: que `service_role` **no** puede tocar la clave
primaria (ese permiso exacto ya mordió con un 42501 en el backfill de s326), que `anon` no ve nada
de las diez vistas, que el CASCADE se lleva la clasificación, que el CHECK vivo coincide con el YAML
leído de `pg_constraint`, y que los votos de las no-preguntas no cuentan. Con control negativo
ejecutado. Correrlo por primera vez encontró un defecto suyo: contaba las filas que sembraba el
arnés compartido.

Los tres encargos: el **móvil** se midió con Chromium real —0 px de scroll horizontal en 390, 768 y
1440— y el bug del header se diagnosticó leyendo estilos computados en vez de adivinando (el nav
heredaba `flex-basis:0%`, así que su `width:100%` no servía de nada); la CSP sigue en
`default-src 'none'` y sigue sin una línea de JavaScript. El **inventario del primer DG** salió en
verde salvo por una cosa, y es la de siempre: el paquete del abogado, que además está
desactualizado —describe el aviso v8 mientras el código sirve el v9—. Y la **portada de un vistazo**
trajo la primera ruta con parámetro del panel, que se normaliza antes de la puerta de sesión y
resuelve el sufijo contra una lista cerrada o devuelve 404.

Quedan dos deudas nuevas y las dos son sobre no poder comprobar cosas. La #93: nuestro dúo es
**secuencial** a propósito —Fable audita los cierres de Sol, que es donde estuvo su valor hoy— pero
el tally exige que ambos vean los mismos bytes, así que el enganche nunca cuadra y el recibo se
pierde; salió tres veces en dos días. La #94: el CSS del panel no tiene red de seguridad, y el móvil
es el dispositivo del técnico en obra. DEC-248.


## s328 (20-ago-2026) — La primera regresión visible, y la lección de haber verificado lo que no era

Alberto abrió `/metricas` en el escritorio y dijo que se veía «como con zoom». Tenía razón, era
mía, y era de la noche anterior.

La causa resultó ser más interesante que el síntoma. El gráfico de barras no era una cosa: eran
**dos**. Las barras vivían en un SVG que yo había hecho fluido en s327 para que no se saliera de un
móvil, y los rótulos vivían fuera, en `<div>`s de 28 píxeles fijos, en una columna al lado. Dos
sistemas de coordenadas que tenían que coincidir a mano, y que solo coincidían cuando el SVG se
pintaba exactamente a una unidad por píxel — es decir, cuando su contenedor medía 410 px y ni uno
más. En una tarjeta ancha de escritorio el SVG escalaba y los rótulos no. Medido después con
Chromium: **×2,29 y 264 px de separación entre cada barra y su rótulo a 1440 px**.

Lo incómodo no fue el bug. Fue esto: **en móvil también estaba roto** —81 px a 390— y yo había
escrito «móvil verificado con navegador real» doce horas antes. Y era cierto lo que medí: cero
píxeles de desbordamiento horizontal, en las tres anchuras, con Chromium de verdad. El problema es
que medí *desbordamiento*, y este fallo no desbordaba: se ampliaba. Verifiqué algo real y concluí
otra cosa. La clase, que vale más que el caso: **los tests del panel leen HTML, y la geometría no
está en el HTML** — la calcula el navegador, y lo que no se le pregunta no se sabe.

El arreglo se eligió para que la pregunta no vuelva a poder hacerse mal: el rótulo pasa DENTRO del
SVG. Una escala, no dos, y la alineación es correcta **por construcción** a cualquier anchura, no
porque dos números coincidan. El CSS topa el gráfico en su ancho natural —fluido hacia abajo, nunca
ampliado— y `barras()` deja de aceptar un parámetro de ancho, porque un llamador que lo cambiara
movería el `viewBox` sin mover el tope, que es exactamente el desajuste que se estaba cerrando.

`TECH_DEBT #94` se había abierto a las cinco de la mañana diciendo «el primer cambio de CSS
posterior a s327 debería traer el gate de navegador». El primer cambio fue el propio s327, y lo
cobró antes de que nadie lo pagara. Ahora existe: levanta la app de verdad y la recorre con Chromium
en tres anchuras exigiendo que no desborde, que no se amplíe y que cada rótulo esté a menos de tres
píxeles de su barra.

Y entonces el revisor hizo su trabajo. Cinco hallazgos, los cinco confirmados, y **dos de ellos
sobre el gate que acababa de escribir**: que se saltaba en silencio si Chromium fallaba en CI —o
sea, un job verde sin haber medido nada, que es exactamente el patrón de cobertura-que-miente que
#94 venía a cerrar, reintroducido dentro del arreglo de #94—, y que la sonda buscaba los rótulos
**por nombre de clase**, con lo que cazaba mi implementación concreta y no la clase de error. Un
tercero era peor de lo que parecía: al reescribir la regla `.entrar` para la puerta nueva le había
cambiado el layout **a la página de error**, que la reutiliza desde siempre. Y un cuarto señaló que
mi «control negativo ejecutado: 13 rojos» era una frase, no un artefacto — el render viejo ya no
existe en el árbol, así que nadie podía repetirlo. Ahora el patrón roto está versionado como página
sintética y dos tests exigen que la sonda lo marque *y* que no marque el render vigente.

Los tres juntos tienen nombre: **construí el instrumento de verificación y no verifiqué el
instrumento**. Un gate que se salta, una sonda que mira mi arreglo y un control negativo que es
prosa fallan todos hacia el mismo lado, el verde.

La otra mitad de la noche fue la puerta. Alberto quiso que `/entrar` se viera como el login del Data
Room, así que se trajeron sus tokens de marca —navy, cobre, arena— y el patrón de su logotipo, con
el nombre de esta herramienta. Lo que no se trajo importa igual: el botón de «Mostrar» la contraseña
necesita JavaScript y aquí la CSP no deja correr ninguno; «¿olvidaste tu contraseña?» y
«verificación en dos pasos» describen cosas que el Data Room tiene y este panel no, y un enlace
muerto y una promesa de seguridad falsa son peores que su ausencia; y la Playfair Display obligaría
a abrir la CSP a dos dominios de Google en un panel que hoy no pide nada de fuera. Todo cuelga de
`body.entrada`: la puerta es la cara de la casa, y detrás sigue estando la herramienta. DEC-249.


## s328b (20-ago-2026) — La tercera vez que se dibuja el mismo gráfico, y la primera que la letra se queda quieta

Alberto mandó un pantallazo con tres peticiones en una línea: que las gráficas salieran de izquierda
a derecha y no de arriba a abajo, que usaran el mismo tamaño de letra, y que los nombres de los ejes
estuvieran alineados con las barras.

Lo primero fue comprobar qué estaba mirando, porque el pantallazo era de **producción** — el código
de anoche, sin el arreglo de esta misma mañana. Pero al renderizar la versión arreglada al mismo
ancho apareció algo que no esperaba: **también fallaba lo del tamaño de letra, por el motivo
contrario**. El SVG de s327 se ampliaba en una tarjeta ancha; el arreglo de s328, con los rótulos
metidos dentro, encogía en una tarjeta estrecha y dejaba la letra en unos ocho píxeles. Dos diseños,
dos fallos opuestos, una sola causa: **una escala uniforme mueve el texto por definición**. No hay
ajuste que salve a un SVG de eso. Que Alberto pidiera «el mismo tamaño de letra» era, sin él
saberlo, el diagnóstico.

Así que el gráfico dejó de ser un SVG. Ahora es una lista de columnas en HTML: el texto es texto —12
píxeles son 12 píxeles a cualquier anchura, los mismos que el resto de la página— y lo único que
estira es la barra. La altura viaja en una clase de una tabla fija de 101 reglas, porque un atributo
de estilo sería «inline style» y obligaría a abrir la CSP en un panel que no tiene JavaScript. Y la
clase de fallo que ocupó toda la mañana —dos sistemas de coordenadas que tienen que coincidir— no se
vigila: **desaparece**, porque el rótulo y su columna son hijos del mismo elemento de la rejilla.

De las tres opciones que le ofrecí para «izquierda a derecha», Alberto eligió columnas verticales.
Yo recomendaba mantener las barras horizontales con las filas bien alineadas, y él tenía mejor
criterio para su panel: en una serie temporal el tiempo debe avanzar hacia la derecha, y las vistas
temporales ya venían invertidas justo para eso.

Lo que enseñó el rediseño no vino de diseñarlo, vino de medirlo. Reusé la clase `.cifra`, que ya
existía para las tarjetas de KPI con un `min-width` de 150 píxeles: cada columna pasó a medir eso y
solo cabían dos por tarjeta. Lo cazó mirar la captura, no un test — ningún invariante dice «las
clases nuevas no colisionan». El gate de `style=` cazó mi propio **comentario**, que explicaba por
qué no se usa un atributo de estilo escribiendo el atributo literal; no se ablandó el gate, se
reescribió el comentario. Y el arnés de medida me mintió dos veces: sacaba las fechas ascendentes
cuando las vistas ordenan al revés —el gráfico salía invertido y parecía un fallo del código— y
repetía la misma etiqueta en todas las filas, con lo que las cuatro gráficas dimensionales sumaban
en una sola barra. Un doble perezoso no verifica: tranquiliza.

El detalle que mejor resume la mañana es el recorte de los rótulos. Puse catorce caracteres a ojo;
el gate midió once píxeles de texto cortado en escritorio y veintitrés en móvil, y bajó a doce. Pero
solo lo midió porque antes había sembrado en el arnés los ids largos de verdad de la taxonomía
—`catalogo_especificaciones`—: con etiquetas cortas, ese gate pasaba en vacío. Un gate que nunca ha
visto su fallo no se sabe si lo vería.

Esta vez sin dúo adversarial, por adjudicación explícita de Alberto para abaratar el rediseño.
DEC-250.


## s328c (20-ago-2026) — El gate pasa a la primera, y la fuente demuestra que «descargarla» era la respuesta

Tres encargos sueltos de Alberto, y los tres acabaron enseñando algo distinto.

**La fuente.** Preguntó si podíamos replicar lo del Data Room, «no sé si ahí nos descargamos las
fuentes o algo». Sí: `next/font/google` descarga la fuente en el build y la sirve desde el propio
origen, y su CSP lo demuestra — `font-src 'self'`, sin un solo dominio de Google. Su intuición era
exacta. Aquí no hay build ni ficheros estáticos, así que los bytes viajan **en el código**: un
módulo Python con la Playfair Display recortada a los catorce glifos que el logotipo pinta, mil
novecientos ochenta y ocho bytes. Que vayan en código y no en un `.woff2` en disco no es capricho —
es la lección de s326b, donde `config/` llevaba desde #308 sin viajar al bundle de Vercel, en
silencio, porque había que re-incluirlo a mano. Un módulo Python viaja por construcción. Y la CSP se
abre **solo** en la puerta: `font-src data:` en la respuesta del login y en ninguna otra.

Lo que no quise dejar es un binario opaco de cuatro kilobytes en el repo con un «confía en mí», así
que hay un script que lo regenera y un `--comprobar` que compara el juego de glifos con lo
versionado. Escribirlo mordió a la primera de una forma que hace gracia: `re.sub` leía el espacio
duro de la cadena de reemplazo como un escape de plantilla y reventaba con «bad escape \u».

**El gate de acuerdo.** Alberto pidió la taxonomía «que la reviso», y lo primero fue no dársela. El
paquete que llevaba días esperando era de la **v6** e incluía `no_es_pregunta` — una categoría que
había dejado de existir en la v7, cuando se convirtió en el eje. Entregarlo habría sido pedirle que
adjudicara decisiones que el sistema ya no toma: trabajo real gastado en un artefacto muerto. Se
regeneró contra producción, con las siete no-preguntas enteras —son las decisiones caras— y
veintidós preguntas estratificadas.

Contestó en dos líneas: las siete primeras no son preguntas, y en las demás está alineado.
**Veintinueve de veintinueve.** El umbral era ochenta y cinco por ciento. Es la primera vez que este
gate pasa: la v1 sacó un ochenta y disparó el ciclo del «otros» que produjo la v2. La taxonomía deja
de ser una propuesta mía y pasa a ser criterio compartido, que es exactamente para lo que existía el
gate.

**Y el punto que añadió**, que resultó ser el más interesante: si alguien escribe «qué productos
Detnov tienes» sin signos de interrogación, también debería contar como pregunta. Tenía razón, y la
regla determinista no lo coge —mira el signo final, que es su propia adjudicación—. La reacción
obvia era ampliar la regla. En vez de eso lo medí: ocho de ocho peticiones sin un solo signo
reconocidas, cuatro de cuatro controles limpios. La conducta que pedía **ya estaba**.

Pero no la sostiene una regla: la sostiene el prompt. Y ahí está lo que aprendí escribiéndolo. Una
conducta sostenida por CÓDIGO se protege con un test; una sostenida por un PROMPT solo se protege
midiéndola contra el modelo de verdad. Meter una regla determinista para «asegurarla» habría
convertido una señal en un punto ciego: si mañana un cambio de descripciones rompiera el eje, la
regla lo taparía en vez de dejar que se viera. Así que queda como sonda versionada con su gatillo —
re-correr cuando suba la versión de la taxonomía o se cambie de modelo— y sin tocar el código.

Nota de entrega, pequeña pero deliberada: los veintinueve mensajes son prosa de técnicos, que es
justo lo que el paquete del abogado tiene pendiente de validar. Se los pasé como fichero, no como
página publicada. Adelantarme a esa consulta por comodidad de formato habría sido barato de hacer y
caro de explicar. DEC-251.


## s328d (20-ago-2026) — El anexo que era una copia, y por eso mentía

Alberto pidió dos cosas del paquete del abogado —actualizar el anexo del aviso y añadir las dos
preguntas que faltaban— y firmó el plazo que quedaba en blanco: veinticuatro meses.

Lo del anexo tenía una trampa que se ve al mirarlo dos segundos. El documento llevaba el aviso **v8**
transcrito a mano mientras producción servía el **v9**, y la primera pregunta del paquete —una de
las dos que bloquean el piloto— es literalmente «¿es válido este aviso?». Es decir: el asesor iba a
validar un texto que ya no es el que la gente acepta.

Actualizar el anexo habría arreglado el síntoma. La causa es que **el anexo era una copia**, y toda
copia se desfasa; la siguiente vez que alguien toque el texto del bot volvería a pasar lo mismo. Así
que ahora se **genera del código que se sirve**, leyendo las dos constantes por AST —sin importar el
módulo del bot, que arrastra medio sistema y haría que un anexo dependiera de tener el entorno
completo—, y hay un `--comprobar` que dice si el documento se ha vuelto a quedar atrás.

Y ahí el control negativo hizo su trabajo, otra vez. Subí la versión a mano para ver si el
comprobador lo cazaba y **dijo que todo estaba al día**: comparaba el texto y no la etiqueta, así
que un bump sin cambio de prosa pasaba en verde y el anexo seguiría titulado con la versión vieja.
El asesor validando un texto correcto bajo un nombre falso. Se cerró cruzando también el título, y
esta vez el control salió rojo cuando debía.

Del v9 salió además una pregunta que nadie había hecho. Entre el v8 y el v9, la mención a que los
datos salen de la UE **bajó de la pantalla de aceptación al detalle de `/privacidad`** — decisión de
Alberto en su día para aligerar el primer contacto. La transferencia es real y la segunda capa se
lee sin aceptar nada, pero es el único cambio del v9 que puede morder la validez del
consentimiento, así que sube a P1 como pregunta expresa en vez de quedarse como nota de diseño. De
paso apareció una deriva hermana: el documento interno de retención seguía afirmando que la primera
capa menciona los proveedores fuera de la UE. Desde el v9 no lo menciona. Corregido con fecha y
motivo, no en silencio.

Las dos preguntas nuevas se escribieron sin suavizar lo incómodo. La del Explorador dice lo que hay:
hasta ahora el responsable veía **cifras**, y ahora puede **leer lo que la gente escribió**. La de la
clasificación acota con los tres hechos que de verdad importan —datos ya recogidos, mismo proveedor
que ya recibía la pregunta, ninguna decisión sobre la persona— y pregunta lo único que queda en
duda: si es tratamiento ulterior compatible o finalidad nueva. Ambas van marcadas como nuevas, con
una nota en cabecera: el sistema creció mientras el documento esperaba, y esconderlo obligaría al
asesor a comparar a ciegas.

El plazo, por último, no era una casilla `[DECIDIR]` sin rellenar: era una **fila que faltaba** en la
matriz. Ahora está, con veinticuatro meses y con la misma excepción declarada que la lista de acceso
—el usuario es la clave primaria, así que no se puede disociar sin destruir la fila—. Y con el gap
escrito al lado en vez de escondido: el plazo está decidido y **no hay job que lo ejecute**.

Queda una cosa y es de Alberto: rellenar a quién se abre el piloto y cuándo, y mandarlo. DEC-252.


## s328e (20-ago-2026) — «¿Sonda o determinista?», y la pregunta que destapó otra cosa

Alberto preguntó si el eje sin signos de interrogación estaba mejor como sonda o como regla
determinista. Al pensarlo en serio tuve que **corregirme**: le había dicho que una regla «taparía la
señal», y ese argumento era flojo. La sonda puede medir lo que decide el modelo antes de que la
regla lo pise, así que no se tapa nada. Si esa hubiera sido la única objeción, la regla salía
gratis.

La razón de verdad resultó ser lingüística, y más incómoda. En castellano el marcador interrogativo
que una regla detecta sin ambigüedad es **la tilde** —`qué`, `cómo`, `cuánto`— y un técnico
escribiendo desde el móvil en una obra no pone tildes. La regla segura deja fuera justo el caso que
Alberto señaló; la regla útil se traga subordinadas normales («que no me va el lazo») y mete ruido
en el denominador, que es literalmente para lo que se creó el eje. No hay regla léxica limpia para
esto en castellano. El `¿` de apertura sí sería inequívoco, pero de ochenta y cuatro mensajes que lo
llevan, **cero** carecen del cierre: sería una regla para un caso que no ha ocurrido nunca.

Y entonces apareció lo que de verdad estaba mal, y no era ninguna de las dos opciones que
discutíamos. **El gatillo de la sonda vivía en un docstring**: «re-correr al subir la versión». Es la
protección más débil que existe —depende de que alguien se acuerde— y el eje es la decisión más cara
del clasificador: un `false` equivocado saca el mensaje de todo el análisis sin dejar rastro.

Así que la sonda pasó a ser **pre-vuelo del job**. Antes de escribir una sola fila, mide los doce
casos congelados y aborta si el eje ha regresado. Es el único camino por el que un prompt nuevo llega
a los datos, así que no hay forma de saltárselo por olvido — y protege más que la regla, porque la
regla solo habría cubierto las aperturas léxicas y el pre-vuelo cubre el eje entero.

Un detalle del diseño que me gusta más que el resto: **corre solo si el prompt cambió, medido por su
huella**, no por la versión del YAML. El contrato dice que tocar una descripción obliga a subir
`version`, pero eso es una convención que nadie impide saltarse; un sha256 de la plantilla más las
descripciones, no. Lo comprobé retocando una descripción sin tocar la versión: la huella cambió y la
sonda se re-armó.

Los tests que acompañan esto tienen una cabecera que dice algo que prefiero dejar escrito: **no hay
test que pueda proteger la conducta**, porque la sostiene el prompt y un test con un LLM de mentira
no mide al modelo. Lo que se testea es el arnés — que la sonda caza un eje regresado, que no se
contenta con decir «pregunta» a todo, que una respuesta que el parser rechaza cuenta como fallo y no
como silencio aprobado, y que una regresión aborta **sin llegar a llamar** al clasificador. La
medición contra el modelo de verdad vive aparte, con su recibo. Separar esas dos cosas —lo que un
test puede garantizar y lo que solo una medición puede— es lo que hace honesto al conjunto.
DEC-253.

---

## s329 (20-ago-2026) — Dos cosas que nadie había configurado: un bit y un nombre

La sesión empezó con «¿retomamos?» y el arranque canónico destapó, antes de tocar nada, que **el
digest de levers no venía inyectado**. La ironía es exacta: `inject_lever_digest.sh` se versionó en
s316 *precisamente* para que el control de DEC-072 viajara con el repo a las sesiones cloud, y viajó
—pero commiteado en modo `100644`, sin bit de ejecución, mientras sus dos hermanos van en `100755`.
El harness lo ejecutaba y moría con **exit 126, Permission denied**, en cada checkout cloud desde
s316 — trece sesiones atrás. En silencio, porque el script es fail-open a propósito. En local nunca se notó: git no toca el
bit de un working tree que ya existe, así que en la máquina de Alberto el hook seguía corriendo.

La lección no es el bit. Es que **versionar el control no bastaba: había que versionar también su
permiso de ejecución**, y nada lo comprobaba. Por eso el arreglo no se quedó en `chmod`: los dos
hooks se invocan ahora vía `bash <script>` desde `settings.json` —el idioma que `session-start.sh`
ya usaba para llamar a `install-deps.sh`— y con eso el arranque deja de depender de un bit que un
checkout, un zip o un filesystem pueden perder. Verificado en el mismo turno por las dos vías, y
confirmado en vivo poco después: el `resume` de esa misma sesión ya inyectó el digest.

Lo segundo lo trajo Alberto con un pantallazo del panel: había emitido la invitación de un DG y el
enlace salía `https://t.me/<NOMBRE_DEL_BOT>?start=...`, con un aviso pidiéndole sustituir el nombre
a mano. «Quiero que el link para compartir ya sea de copiar y pegar.»

El aviso decía que faltaba `TELEGRAM_BOT_USERNAME` en el entorno del panel, y era verdad, pero la
verdad completa resultó ser peor y más simple: **la variable no existía en NINGÚN entorno
desplegado**. El censo por la API de Railway lo dejó claro —tampoco en el worker—, y en el repo solo
la conocían los tests y la ayuda del CLI. Es decir: el placeholder no era un despiste de
configuración de Vercel, era el estado por defecto del sistema en todas partes.

Con eso, poner la variable en Vercel dejaba de ser el arreglo: habría tapado el síntoma en un
entorno y dejado viva la clase en cada preview y cada entorno nuevo. La decisión fue mover el dato a
donde le corresponde. El **@username de un bot no es un secreto ni un tunable: es la identidad
pública del producto**, viaja en cada enlace que ya se comparte y cambia prácticamente nunca. Así
que vive en código —`access.BOT_USERNAME_DEFECTO`— y la variable queda como override para apuntar a
un bot de pruebas. No lo copié de los tests: lo verifiqué contra `getMe` de Telegram con el token
vivo del worker, que es la única fuente que no puede estar desfasada.

El dúo (Fable, standalone) devolvió `SÓLIDO` con tres menores, y **dos de ellos eran de los que
duelen porque tienen razón**. El primero: la receta de invitar en `DG_DEPLOYMENT.md` seguía pasando
`--bot PCI_Soporte_tecnico_bot` explícito, y como el explícito gana al default, un operador que
copiara esa línea tras un renombrado estamparía el nombre viejo *aunque el default estuviera
corregido* — mi propia mitigación, incompleta. El segundo: yo había escrito «test de integración del
panel sin la variable», pero el test end-to-end que de verdad pinta el enlace seguía con la variable
pineada en su fixture, así que **la ruta real —la que corre en Vercel hoy— no se ejercitaba**.
Bastaba borrar esa línea. Los dos arreglados en el mismo commit.

Y la suite completa dejó el último detalle, que es el sistema funcionando como debe: el único fallo
de 4.645 tests fue el **registro de flags de s311 cazando el `getenv` nuevo sin censar**. Un
invariante que se pone rojo cuando alguien añade una lectura del entorno y no la declara. Censada la
flag (96 → 97, con la nota de que el default real vive en código, no ahí), verde.

Cierre: PR #318 mergeada por Alberto, y el deployment de producción de Vercel es exactamente ese
merge. La próxima invitación sale de copiar y pegar. DEC-254 y DEC-255.

---

## s330 (20-ago-2026) — El job que ya existía, y el derecho que estaba roto

Alberto eligió el frente: «job de purga». Yo se lo había ofrecido con esta frase — *el plazo de 24
meses está decidido y no hay job que lo ejecute* —, y era **falsa**. Lo primero que hice fue mirar el
código, que es lo que el Protocolo 4 manda antes de tocar una premisa, y ahí estaba:
`rgpd_retencion_pasada` en producción desde el 5 de agosto, corriendo por pg_cron el día 1 de cada
mes, con la ventana de 24 meses metida en las políticas RLS para que la garantice el motor y no la
buena voluntad de quien escribe la sentencia. Si hubiera empezado a construir, habría hecho un
segundo job — exactamente el drift que s299 eliminó a propósito, y que habría dividido en dos una
operación irreversible.

Lo que faltaba de verdad era más pequeño y estaba escrito: ampliar esa pasada a las tres tablas de
control de acceso. El propio documento decía el mecanismo correcto — «una política más, no un job
nuevo» — y hasta la tabla de reglas. Parecía media sesión.

**Y entonces Sol dijo que la regla canónica no se podía ejecutar.** La matriz manda poner
`canjeada_por = NULL` conservando `canjeada_at`, y eso viola un CHECK de la propia tabla. No fallaría
esa fila: fallaría **la pasada entera**, revirtiendo también la disociación de `query_logs`,
`feedback`, `answer_feedback` y la destrucción del vínculo, con el error escondido en
`cron.job_run_details` y sin aparecer hasta 2028, que es cuando existirá la primera fila elegible.
No era un bug de mi diseño: era la regla adjudicada la que no era ejecutable, así que fue a
adjudicación con cuatro opciones. Alberto eligió el tercer estado explícito, que es el que conserva
la traza del canje sin romper el invariante para todo lo demás.

**Y Fable encontró que el mismo CHECK rompía algo que no era de 2028, sino de hoy.** La sentencia
que nuestro runbook prescribe para atender un derecho de supresión —el artículo 17— es la misma que
la base rechaza. Estaba escrita así en cuatro sitios, incluido el runbook operativo del piloto. Si un
DG hubiera pedido el borrado de sus datos esta semana, el procedimiento habría fallado con un error
de restricción. Lo encontramos arreglando otra cosa, que es la forma más incómoda de encontrar algo
y también la más barata.

Los otros dos hallazgos son de la misma familia: la aserción de mecanismo de s299 exige que la
política de cada tabla lleve `created_at` literal, así que ampliar el array de nombres —lo que decía
mi primera versión— habría dejado la pasada abortando cada mes; y re-ejecutar s299 después de esto
reinstalaría la versión de cuatro tablas en silencio, para lo cual un banner no vale: la protección
es una precondición que aborta.

Pero lo más caro no lo vio ninguno de los dos revisores, ni yo. Lo vio **PostgreSQL**. Al ejecutar el
gate, `CREATE OR REPLACE` sobre la función falló con *permission denied*, y la causa está en su
propio encabezado: al reemplazar una función que lleva `SET role`, el chequeo del objeto previo
ocurre ya con ese rol asumido, y a ese rol s299 le había revocado todo. Cuando s299 la **creó** no
había nada que chequear, así que el problema solo existe para quien la **amplía** — es decir, para
esta sesión y para todas las que vengan. El arreglo es un `DROP` explícito antes del `CREATE`, y ese
`DROP` traía su propia trampa: la función renace bajo los default privileges de Supabase, que
conceden EXECUTE a la API entera. Ampliar la retención estuvo a un paso de reabrir el agujero que
s299 ya había pagado una vez.

El contenedor no traía PostgreSQL 17 —solo el 16, que ni siquiera conoce un privilegio que la cola
usa—, así que lo instalé. 53 de 53 verdes, y el control negativo ejecutado: con la ventana saboteada
a `USING (true)`, la migración no aplica. Después, al ver que el gate de CI pasaba en 39 segundos,
fui a los logs a comprobar que había **medido** en vez de saltarse: ahí estaban mis propios controles
negativos disparando contra el servidor. Esa desconfianza la enseñó s328.

Nada de esto está aplicado en producción: eso es de Alberto, y el propio documento lo condiciona
además al visto bueno del abogado. Tampoco corre riesgo: el censo dice 2, 2 y 1 filas, cero vencidas,
y la más antigua es del 17 de agosto — lo primero que este código podría borrar es de agosto de 2028.
DEC-256.

## s331 (20-ago-2026, sesión web nocturna) — El 👎 de la Kidde se convierte en el ataque entero: 6 dúos, build flag-off M1→M3c, y dos reglas de proceso pagadas en carne propia

Arrancó como «¿ataco los synthesis miss?» y el arranque canónico dijo NO con la métrica en la
mano (Etapa 3 = NO-GO serving, población 1). El pantallazo de Alberto (T2 «Sobre la 2X-AF1-FBS»
→ T3 re-pregunta amnésica, 👎 con texto) la re-dirigió: TECH_DEBT #49 trigger (c) disparado por
un técnico real. Diagnóstico con sondas $0: la variante muere DOS veces (alias de familia al
leer; hint-solo-bindeados al arrastrar) mientras el resolver gobernado la detecta hasta en
grafía ASR — y la re-pregunta vive también como PLANTILLA sin LLM. Seis rondas de dúo (v1→v6;
4 emparejados limpios) tumbaron dos seams equivocadas, un event-loop-block de ~3 s, una
violación de la frontera de privacidad del trace, un invariante de test que era mentira y la
polaridad de la gramática — Alberto cortó en r-v6 («paralysis by analysis») y los restos pasaron
a checklist de build B1-B11. Build por hitos con suite verde CITADA, esquema advisor/executor
(Fable orquesta; Opus 5 ejecutó M2 y M3c-threading con specs cerradas — y cazó él solo el
bloqueante del contrato de imports): M1 seam de composición · M2 detector 2-puertas + léxicos
gobernados · M3a TurnIdentity/pending · M3b gramática+corte+lifecycle espejado · M3c threading
(verificado por MUTACIÓN) + conducta en prompt y plantillas. 3 flags off = byte-idéntico; gates
M4 y ship quedan pre-registrados (v6 §4), sin encender nada. Dos cicatrices de proceso, ambas
declaradas en el repo: los commits intermedios que rompieron el emparejado de Fable r-v1 (regla:
cero git durante una ronda), y el «suite VERDE» falso de c83c0bff (el exit 0 era del tail — la
puerta del inventario P1 lo cazó; regla: pipefail + ningún número no visto en un resultado).
De propina: el flake real del fence IPC (2× en CI, 0/60 local) arreglado con espera acotada,
adjudicado por Alberto. PRs: #322 mergeada en vivo; #323 draft con el ciclo entero. DEC-257.

## s331-packet (20 ago 2026) — El residuo del packet E1: tres preguntas delegadas, y un dúo que corrige la evidencia sin cambiar la conclusión

Alberto abrió la review de los packets pendientes y, sobre el E1 v2, hizo lo contrario de lo
habitual: en vez de contestar las tres preguntas ⏳ que le esperaban, me las devolvió («las 3
preguntas son para ti»), pidió atacar los no-bloqueantes y preguntó si quedaba algo en §1.A.

Las tres se adjudicaron leyendo la FUENTE, no la ficha: los PDF originales viven en el bucket
público, así que `MADT015_01`, `MNDT600` y `MNDT701` se decidieron con el manual delante.

Lo interesante fue el dúo. Mi propuesta descartaba la hipótesis de Alberto («¿puede ser de la serie
FS, por el esquema de bornes?») con un censo de grafía: no hay ids `fs2-*`. **Sol lo cazó como
crítico**: el catálogo tiene `notifier:fs-1/fs-2/fs-4` y el corpus el manual `FS2-1` activo, con
doc_map adjudicado. Mi censo era ciego a la grafía, no una prueba. La respuesta correcta exigía la
comparación al píxel, y esa es la que zanja: las FS son de 1/2/4 zonas, con final de línea solo
resistivo, sin entradas digitales ni retardos; la guía tiene 8 zonas, condensador como EFL
alternativo, dos entradas digitales configurables y retardos — y su árbol de configuración es
idéntico, opción por opción, al del anexo hermano que se titula «Anexo al manual de instalación de
la central **NFS 2-8**». La conclusión sobrevivió; la evidencia que la sostenía, no. Lo mismo pasó
con el censo del «SMART3 GD2»: era circular (miraba solo docs con pm `SMART*`, justo la clase que el
plan estaba corrigiendo) y encima truncaba a 1.000 filas. Re-hecho corpus-wide sobre los 1.054
activos, el veredicto se puede dar cerrado: ese documento no está, y los seis «hits» eran el
programador «PGD-200».

Fable aportó el hallazgo de instrumento: la findability que iba a validar el retag de `MADT015_01`
la satisfacía **la fila que el propio plan añadía**. Un gate que no puede fallar es un ritual, así
que el writer ganó modos explícitos: cuando la entry viene del plan, se exige además que el modelo
ya resolviera en el catálogo previo, y el recibo lo imprime (`autosatisfecha_por_el_plan: true`).

Se aplicó con la puerta de siempre: dry-run PASS (detector +0/−0, 0 gold perdidas, 0 disparos en 111
consultas reales), CAS por chunk, recibo y verificación posterior. Cuatro retags, dos filas de
doc_map, y la baja del fragmento FR que Alberto ya había firmado. Con TI-007 atestado —la
re-ingesta de s324d había traído el texto pero devuelto el pm al artefacto— **§1.A queda completa**.

Y quedó una deuda que solo aparece cuando miras dos veces el mismo documento: **#94**. Los retags de
`product_model` no sobreviven a una re-ingesta, porque el pipeline vuelve a derivar el modelo del
nombre del fichero. TI-007 es la prueba: es la segunda vez que se corrige a mano. El arreglo bueno no
es re-aplicar parches, es que la detección pregunte al doc_map antes de inventar.

De lo que Alberto tenía pendiente en este fichero queda una frase: si el paraguas «2X-A» incluye o no
los once táctiles. La medida ya está hecha —no pierde ninguna gold, dos golds ganan doce fuentes cada
una, y lo único que dispara es una sonda de tokens sintética que ningún técnico escribiría—, así que
la decisión es de alcance de producto, que es suya, no de riesgo, que era mía.

## s331b (20 ago 2026) — Alberto cuestiona mis dos «unknown», y la serie 20/20 aparece entera

Cerrado el residuo del packet, Alberto no aceptó dos de mis adjudicaciones y preguntó por qué:
«MNDT600: ¿por qué unknown?» y «MNDT701: es el software del modelo IR3, ¿no tiene sentido asociar el
manual a ese modelo?».

En la primera tenía razón sobre mi criterio: yo había aplicado la regla estricta (sin cita, sin
doc_map) justo donde tenía su adjudicación explícita y un anclaje real —la portada descrita en el
chunk dice «smart GASDETECTOR» y «sensitron», y la tabla imprime las células «S1096/2096»—, mientras
que a MADT015_01 le había concedido evidencia documental de una hermana. Doble rasero.

En la segunda el hallazgo fue mayor que la pregunta. Al censar el corpus buscando dónde enganchar el
software apareció que **la serie 20/20 SharpEye entera no estaba en el catálogo**: ocho documentos
activos, cero productos, mientras la serie hermana 40/40 sí estaba desde s324b. El manual del
software no estaba huérfano por ser software; lo estaba porque su detector no existía.

Alberto pidió medirlo antes de decidir, así que se montaron cinco sondas —tres alcances para el gas,
dos para la llama— y se pasaron por el gate real. Las cinco pasaban, y ahí estuvo lo útil: **el
veredicto no decidía nada, el detalle sí**. Promover los candidates SMART metía doce alias
descriptivos que son basura de extracción («SMART 3 con pantalla», «SMART 4 (COPTIR) Multi-sensor»,
y un «serie 3G» que colisiona con la red móvil de los documentos UCIP). Las altas de la serie 20/20,
en cambio, eran once términos de modelo sin un solo alias sucio. Firmó «A + E».

El dúo r39 —emparejado esta vez, tras el drift que rompió el anterior— cambió el lote antes de
escribirlo. Sol pidió el plan combinado con su propio dry-run (dos recibos separados contra el mismo
estado inicial se invalidan entre sí) y señaló que atar el software a los tres detectores afirmaba
más de lo que la evidencia decía. Al verificarlo aparecieron dos datos que no estaban en la
propuesta: RS-485 no distingue a los IR³ (también lo lleva el 20/20R single-IR, y los UV se
configuran con microinterruptores), y **el software es de 1997, anterior a los tres manuales**, uno
de ellos de 2011. Así que las tres entradas del software se escribieron como `secondary`: el
documento entra en las fuentes del producto —eso se verificó en el resolver— pero no reclama el
scope gobernado. Fable añadió que mi lista de gaps nombraba la fila equivocada (la cita más floja es
20/20R con dos chunks, no 20/20I con tres) y que uno de los ocho «huérfanos» ya tenía fila.

Y de la pregunta final de Alberto —dónde seguir asignando modelos— salió el dato que faltaba: la
cola real no vive en ningún packet. Son **85 documentos activos sin doc_map**, que tras este lote
quedan en 77, y se obtienen cruzando `documents` contra el catálogo.


## s331c (20 ago 2026, noche) — el packet devuelve el favor: el feedback humano encuentra lo que el gate no miraba

El cierre de la sesión lo marcó una pregunta de Alberto que parecía menor: «¿me puedes recordar las
reglas R1, R2…? ¿Deberíamos ajustarlas? ¿Mi feedback ha sido útil?».

Al hacer el balance salió un patrón que merece quedar escrito: de sus 30 anotaciones, **las 5
preguntas produjeron más hallazgos que las 11 confirmaciones**, y las 3 notas que estaban
equivocadas no costaron nada porque ninguna se aplicó sin verificar. Su «¿por qué unknown?» destapó
que faltaba una serie entera del catálogo. Una nota suya *mal ubicada* —cayó en el documento
homónimo— destapó seis atestaciones equivocadas y, con ellas, un hueco del gate que llevaba
bloqueando por diseño cualquier limpieza de contaminación. Un enlace de una línea evitó acuñar un id
inmutable equivocado. Y su «son los modelos de System Sensor, se ve en la foto» destapó que **cinco
documentos de FAAST están atribuidos a Xtralis, que es el competidor**.

Las reglas salieron tocadas en tres sitios. **R3** tenía un hueco que nadie había visto: gobierna el
`vendido_bajo` del producto y no decía nada del `manufacturer` del documento, que es otra autoridad
—y es justo la que está mal en los cinco FAAST—. **R5** llevaba cinco días esperando ejemplos y ya
los tenía vividos, con un matiz nuevo: antes de atestar por ficha hay que mirar si el documento es un
fragmento con hermano completo, porque entonces la respuesta es la baja. Y nació **R8**: la grafía
canónica es la del fabricante, no la del documento, porque los ids son inmutables. Eso ya se había
hecho de facto con `S20/20MI`; DOA lo convirtió en regla.

Dos de los errores, sin embargo, no eran de las reglas sino del instrumento. El packet presentaba los
documentos homónimos sin distinguirlos y imprimía la propuesta del juez al lado de lo aplicado. Los
dos defectos costaron tiempo real —uno de ellos, seis atestaciones equivocadas— y los dos están
corregidos en el **v3**, que además solo arrastra lo vivo: 67 filas en vez de 192.

## s331d (21 ago 2026) — La pasada completa de Alberto: el aprendizaje se mide antes de escribirse, y el dúo caza dos errores míos que tres pasadas propias no vieron

Alberto subió su repaso íntegro del packet v3 y pidió tres cosas: que «aprendiese» de la
clasificación, que construyese la **Wiki de modelos** que había propuesto en una anotación, y que
propusiera **automatizar la asignación de manuales** manteniendo siempre a alguien que valide.

**Lo primero fue no hacerle caso a mis propias impresiones.** Sus notas se prestan a leerlas y sacar
lecciones que suenan bien —el ritual que DEC-072 prohíbe—, así que primero un censo determinista.
El reparto no lo daba ninguna lectura cualitativa: **57 anotaciones → 34 decisiones distintas**, con
**23 duplicadas** (`morley:tg` se le preguntó **quince veces**) y una minoría de correcciones. Y la
medida del acierto de lo que el packet le recomendaba **mató la propuesta que yo iba a hacer**: iba a
proponer auto-aplicar los patrones que él ya había firmado, y resultó que P1 acierta **60%** y P3
**44%** sobre esta población. El «lo firmaste 9 veces» que el packet imprimía era cierto… en el v2.
Una **tasa base heredada de otra población**, presentada como confianza, en la única capa donde no
hay gate.

Al descomponer los fallos apareció el diagnóstico bueno: **no son errores, son incompletitudes**. En
4 de 6 casos lo que el juez proponía era correcto y parcial. La causa es estructural — cada fila
pregunta UNA cosa donde el documento plantea SEIS — y de ahí sale la recomendación: descomponer en
Q1–Q6 con umbral medido por sub-pregunta.

**Y entonces el dúo hizo su trabajo, que es el motivo de que exista.** Doce hallazgos, doce
confirmados, cero falsos positivos, veredicto de Fable **«No SÓLIDO»**. El reparto entre los dos
revisores fue el que justifica el cross-model:

- **Sol atacó la evidencia.** Yo había escrito que el re-juicio K=5 «convergió 5/5 en el veredicto
  equivocado». **Falso**: el `v5/5` del recibo son los votos VÁLIDOS, y el panel se partió **3-2**.
  El propio packet imprimía «NO convergente» al lado. La conclusión sobrevive por un mecanismo mejor
  —ninguno de los dos bandos podía acertar porque la respuesta no cabía en la rúbrica— pero la
  evidencia que cité era falsa, y con un panel partido **ya no puedo descartar que un juez mejor
  ayude**. Su segundo crítico: «mismo id = misma decisión» es falso, y 3 de los 9 ids repetidos
  llevan decisiones distintas por documento — agrupar por id a secas **perdería** decisiones.
- **Fable atacó el instrumento.** Mi propio script de censo usaba **dos definiciones incompatibles de
  «acuerdo»** en sus dos mitades, y eso inflaba las «correcciones» de 18 a 22 **en la dirección que
  favorecía mi propuesta**. También destapó que un ejemplo de mi propio gap declarado era falso.

Los dos hallazgos que más cambiaron la propuesta son errores míos que tres pasadas propias no habían
visto. Quedó una traza incompleta declarada: la review de Fable no emparejó porque edité otros
ficheros del repo entre las dos corridas.

**La Wiki de modelos** quedó construida y probada: una vista de sólo lectura sobre el catálogo
gobernado, en `/catalogo`. Su invariante —nada que la Wiki llame «utilizable» puede ser algo que el
resolver rechace— cazó una divergencia real al escribirse: los **81 `redirect`** cruzan de marca
(`morley:b501ap` → `systemsensor:b501ap`) y no son ni utilizables ni retirados; son el mismo equipo
bajo otra marca, y en clase propia resultan ser **la vista OEM que no estaba en ningún sitio**. Su
primer censo destapó **245 manuales huérfanos**, **184 de ellos únicamente porque todos sus ids
siguen en cuarentena**.

**Por el camino se cerró el caso que Alberto pidió confirmar**: `D838-1_kac sounders` estaba
etiquetado con la norma francesa AFNOR de su tabla de tonos. El sujeto real es la gama de sirenas
**WMSOU de System Sensor Europe** — las ocho especificaciones coinciden literalmente con la hoja
publicada del fabricante y **no** con las de sus hermanos rebrandeados, que dan 95 dB(A) e IP21C/IP44
en vez de 100 dB(A) e IP24/IP65. El nombre del fichero dice «kac» y miente: R8 en versión fuerte, el
fichero engaña también sobre la MARCA.

Diez reglas nuevas (**R9–R18**), cada una anclada en la anotación que la hizo nacer, viven ahora en
`data/catalog/reglas_clasificacion.json` — en JSON y junto al catálogo que gobiernan, para que no se
queden en prosa que la sesión siguiente no lee. DEC-266 y DEC-267 (nacieron como DEC-263/264 y se
renumeraron al mergear: la sesión s332 llegó antes con esos números).

## s332 (21 ago 2026) — Los dos GO de la mañana, ejecutados antes de comer: lo asumido se declara

Alberto dio el doble GO a media mañana —la tabla de confusiones ASR con un requisito nuevo
(«avisar que estás incluyendo productos sobre una marca que no es la detectada, y que se pueda
desmentir; y que sea generalizable») y la corrección de marca sin estado— con la PR #325 aún
en conflicto por la colisión de numeración con la sesión paralela del packet (resuelta: mis
DEC-257/258 conservan número en main, el cierre pasa a DEC-263, y dos referencias mías que el
barrido ajeno pisó vuelven a su sitio). La evidencia se leyó de query_logs VERBATIM antes de
diseñar: «BQide» no existe en ningún catálogo (reescribible), pero «ID» ES la familia ID3000
de Notifier — la fila que pedía a gritos ser reescrita habría corrompido a un usuario legítimo,
y de ahí nació el MODO por fila (reescrito/aviso) y el case-sensitive que deja al «id» español
en paz. El dúo (Sol xhigh + Fable, 13/13 con sustancia, 0 FP) mató en la v1 el «oráculo-de-plan»
—re-invocar al planificador sobre texto sintético era volver a los dos dueños que s316e/s324h
enterraron— y la v2 quedó en dos niveles honestos: la TABLA previene (T1, atajo de catálogo
intacto) y la RED F1 recupera lo no tabulado reconstruyendo la pregunta anterior, con
`state_query_override` para que «me refería a Kidde» jamás se vuelva la base de nada. Fable
además cazó el docstring del módulo contradiciendo su propio contrato y el homógrafo; Sol, la
laguna de estado y el criterio laxo del gate. Build advisor/executor en PARALELO sobre worktree
compartido (E1 tabla/voz/contracts; E2 rama F1/léxico/espejo MT) con especificaciones cerradas:
E1 cazó de raíz un ciclo de imports que el comentario de E2 negaba (el analizador cuenta los
lazy) y corrió la suite del árbol conjunto: 4817/0. La primitiva `Asuncion` se renderiza
DETERMINISTA en el bot —confirmación 🏷/ℹ️ y sufijo citando la pregunta base, para que hasta un
rebuild rancio quede a la vista— y el trace gana la sección `asunciones` tri-estado sin una
letra de contenido de usuario. Gates sobre la mañana real: GC0 7/7 off=hoy, GC1 7/7 (donde
había «No he encontrado información relevante» ahora hay Serie NC de Kidde con citas), GC3 4/4.
Ship listo: 2 vars, flip de Alberto, verificación DEC-099 por voz. La mañana entera —incidente,
diagnóstico, GO, diseño, dúo, build a cuatro manos, gates y cierre— cupo en una sesión. DEC-264.



## s333 (21 ago 2026, mediodía-tarde) — La red aprende a juzgar: del «¿escalan las reglas?» de Alberto a un clasificador con SU frontera, en una tarde

Nació de una pregunta de dirección, no de un plan: Alberto miró el fix s332b y preguntó si
implementar reglas escalaría o si acabaríamos «con 39207245 reglas» — y si no tocaba un LLM
que detectara el intent. La respuesta honesta era que el repo ya vivía en esa doctrina
(INTENT_LLM existe porque cinco rondas de dúo demostraron que las reglas no convergían en la
rama ambigua), y que la pieza donde su instinto mordía de verdad era el léxico de corrección.
Su pushback lo remató: con 5-10 técnicos sin precisión léxica, la superficie es abierta a
priori. GO con contrato («BP, robusto, escalable»).

El diseño extendió el patrón probado en vez de inventar: fast-path determinista intacto,
clasificador binario SOLO en su miss, población acotada, cohorte y gate PROPIOS (el 40/40 de
INTENT_LLM midió otra métrica y NO transfiere). El dúo (10/10, 0 FP) mató lo que había que
matar antes de nacer: el crítico de Sol —`to_thread` solo envolvía el resolve con
`_intent_fn`, y el flag nuevo a solas habría congelado el event loop 6 segundos— y el medio
de Fable —la población tragaba marca+código-no-resuelto—. El executor Opus cableó módulo y
rama con spec cerrada (y cazó él solo que «2X-AF9999» resuelve el prefijo «2X-A», invalidando
mi caso de guarda); el trace ganó su sección tri-estado; la revisión Fable de la cohorte cazó
mi propia nota falsa (N3 con dos marcas gobernadas = fuera de población).

El gate hizo exactamente su trabajo, tres veces. v1: NO-GO con 3 falsas que no eran fallos
del modelo sino LÍMITES de mi gold — y Alberto los adjudicó uno a uno, dejando una frontera
mejor que la mía: «¿el mensaje se sostiene solo?». v2 (su frontera codificada en el prompt):
NO-GO por UNA falsa que era la misma clase que la que él acababa de adjudicar como corrección
— el clasificador estaba siendo más consistente con su criterio que mi propio gold. v2.1
(relabel puro): **GO — 14/14, 0 falsas, guarda 2/2**. Haiku quedó descartado con métrica
propia (13 falsas), no por herencia. El e2e con el clasificador real cerró el círculo:
«sí, dije Kidde» sin cue en el léxico ⇒ `brand_correction_llm` en 1,4 s y respuesta Kidde.

Dos cicatrices de proceso, ambas de la misma familia que el pipe-trap: un assert de replace
tumbado por whitespace cuya cadena con `;` dejó correr un gate repetido sobre la cohorte
vieja, y un backtick ejecutado dentro de un `-m` que mutiló una línea de commit. Declaradas,
con regla. PRs del día: #325 (cierre s331 + colisión de numeración con la sesión paralela),
#327 (build s332 entero), #328 (fix s332b), #329 (s333, pendiente de merge). DEC-263→265 y 268 (266/267 son de la sesión paralela).

## s334 (21 ago 2026, tarde) — La conversación que ejercitó las tres capas y encontró la cuarta

Alberto probó el flip de s333 por voz y Whisper le escupió la 4ª y 5ª corrupción de «Kidde»
del día («ITIDE», «KIDE») — la segunda DENTRO del propio turno de corrección, donde ninguna
capa podía verla: el cue era válido pero la marca corrupta no casaba ningún token gobernado y
la red entera quedaba inalcanzable. Y en «Ahora quiero Morley» tras un listado por atajo, el
clasificador de s333 se estrenó en producción con mecánica perfecta… razonando contra una
`last_query` rancia, porque el atajo de catálogo nunca escribió estado (la R8 que s332 declaró
como deuda). Su «es subóptimo» era exacto en los dos casos.

La respuesta fue en dos tiempos. Inmediato: filas observadas kide/itide (la vía pre-autorizada,
PR #331 en verde mientras se diseñaba lo demás). Estructural, con GO doble y dúo (10/10, 0 FP):
el fuzzy ACOTADO al slot de marca — reframeado con honestidad tras el crítico de Sol («tu
propia fila kide consumió la evidencia viva: esto es una apuesta anticipatoria del owner, no un
rescate medido») y blindado con el guard-test de Fable (la invariante de unicidad se audita
sobre el conjunto VIVO en cada CI, no una vez) — y la R8 cerrada de raíz: las CINCO rutas
terminales de atajo (Sol cazó que «solo inventario» era falso) escriben la transición de
respuesta por un helper extraído de `advance_working_state` (divergencia imposible por
construcción) a través del escritor único, consumiendo de paso el pending que cruzaba atajos.

El gate midió lo que había que medir en vez de presuponerlo: con estado fresco, el clasificador
real leyó «Ahora quiero Morley» como corrección (1.261 ms) y la respuesta e2e sirvió las
centrales Morley-IAS — la conversación de la tarde, reparada de raíz y con recibo. De regalo,
los tests del fuzzy descubrieron que la plantilla s332 no toleraba el «de» preposicional del
fraseo real de Alberto. Suite 4900 en verde. DEC-269.

## s335 (21 ago 2026, tarde) — La anafórica entra al prompt (con fila obligatoria) y el atajo aprende los fraseos del técnico

La tarde dejó dos cabos del mismo hilo de la conversación real `fabef50b`: «Quiero ver las
centrales de Morley.» moría con plantilla vacía (el punto que Whisper añade rompía el ancla
`\??$` del atajo — un hueco que afectaba HASTA a las formas interrogativas existentes dichas
por voz, porque la voz alcanza el plan desde s324h), y «Y ahora quiero ver las de Morley.»
era `nuevo` para el clasificador (correcto bajo el prompt v2 — la anáfora no estaba en el
criterio). Alberto adjudicó la segunda como CORRECCION («es una corrección i.e. "dime qué
centrales de Morley tienes"») y dio GO a los fraseos.

El dúo (Sol 6 + Fable 7 = 13/13 con sustancia, 0 FP) mató la v1 por dos críticos gemelos:
relabel-sin-prompt no cambia conducta (la analogía con v2.1 era FALSA — allí el gold se alineó
con el modelo; aquí el modelo dijo `nuevo` en producción), y la barra agregada podía dar GO
nominal con el caso motivador en rojo. El rediseño honesto: prompt v3 con la regla anafórica
explícita, cohorte v3 re-congelada ENTERA (DEC-126) y **fila OBLIGATORIA que debe pasar su
propia mayoría K** — regla de gate nueva y generalizable. Resultado: **GO 15/15, p15 3/3,
0 falsas/22** — y las negativas con sustantivo propio («ahora quiero ver detectores Notifier»)
siguen `nuevo`: la regla discrimina exactamente anáfora vs petición completa.

La pieza A (`INVENTARIO_FRASEOS`, default off) es la gramática v2 del atajo: tolerancia
terminal gateada + desiderativas/imperativas ES+EN con la frontera de Sol-4 (ancla terminal,
cola SOLO de filtros censados — «quiero saber qué centrales Morley tienen salida de relé»
sigue al RAG). El flag entra al plan como dato (`Meta`, patrón MISMATCH_ANSWER) y
`marca_destino` comparte el predicado: UNA definición de intención de inventario. GB1/GB2
21/21: el e2e completo (atajo→R8→clasificador real 1576 ms→RAG Morley-IAS sin cross-brand)
quedó medido, incluido el cruce `_SWITCH_FRASE` que Fable-3 exigió no presumir: con modelos
bindeados la guardia INVALIDA y mata la población del clasificador ANTES de resolve; la
población real del cue anafórico son los estados con `models=()` — exactamente los que R8
crea. Limitación DECLARADA (Sol-1): el rebuild sirve por RAG = lista potencialmente parcial
(clase s307); el listado gobernado es la pieza A con la petición entera. La pieza C («sí»
pelado) quedó censada en 3 casos y NO cableada — irá con su GO y su dúo.

Suite 4932 verde + MT 52/52. Recibos: `evals/s335_gate_resultado_v1.md`,
`s335_gate_result_v3.json`, `s335_gb_result_v1.json`. DEC-270. Pendiente al cierre: merge
#333 + flip + verificación por voz con los puntos de Whisper.

---

## s334 (21 ago 2026) — «¿puedes atacarlo de forma autónoma?»: 52 manuales rescatados, y las tres veces que el número que yo daba no era el número que había

Alberto reencuadró el problema y el reencuadre era el trabajo: «sobre los 535 —aunque lo mejor
creo que es enfocarlo desde el punto de vista de *manuales huérfanos*— ¿puedes atacarlo de forma
autónoma?». Un candidate en cuarentena no le importa a nadie. Un **manual que no puede servir a
nadie** sí: es un PDF pagado, ingerido, troceado y embebido que el bot no alcanza cuando el
técnico pregunta por su modelo. Había 245.

Empecé con 157 filas de «clase A» —token nombrado, marca resuelta, cita verificada con frontera
de palabra en su propio documento— y la sensación de tener el trabajo hecho. Lo que pasó después
fue que **cada vez que medí en vez de razonar, el número bajó**:

- 157 no eran ids: eran **pares `(id × manual)`**. Ids distintos: **118**. Yo había escrito 149 en
  la sesión anterior contando pares y llamándolos ids.
- De los 110 que quedaban tras apartar riesgos declarados, la verificación con el resolver real
  dejó **89**. Los 21 que se cayeron no eran ruido: eran tres fallos con nombre que **no se ven
  desde el texto del documento**. Homónimos abiertos (`morley:sp-200` y `notifier:sp-200`
  comparten token y su fila está `candidate:true/fail-open`, así que promover deja el término EN
  el detector y el manual FUERA). Gemelos (`ID-3000` ya resuelve a `notifier:id3000`; `TG-1020`
  resuelve a **`desico:tg-1020`**, que ni siquiera es la misma marca). Y no-detectables (`00051`
  es digit-only y el detector los excluye a propósito; `EEV(2)` lleva paréntesis).
- Y de los 89, el dúo tumbó **8 más**.

**Lo que encontró el dúo r42 es lo mejor de la sesión.** Once hallazgos, once verificados contra
el código y los recibos, cero falsos positivos.

Sol atacó la raíz: **«clase A» no prueba que la fila sea un producto.** Prueba que el token está
en el texto, y ya. `notifier:eia-485` estaba en mi lote con 71 menciones en su manual — porque
**EIA-485 es el bus RS-485** y el manual explica cómo cablearlo. Promoverlo habría convertido
cualquier consulta de bus, de cualquier fabricante, en una consulta sobre un documento de
Notifier. Yo había escrito en la propuesta, con todas las letras, «ninguna fila entra porque
parece un modelo». Era falso.

Fable encontró la otra mitad, y es la que más me costó ver: **promover puede ESTRECHAR.** Mi
instrumento preguntaba «¿llega su manual?» y nunca «¿se pierde alguna otra fuente?». Al medirlo:
`8100E FAAST` pasaba de 14 fuentes a 1 y de 14 modelos a 2; `TG-6000`, `TG-6000 Net` y
`TG-NOTIFIER` perdían el paraguas `TG` y con él **los 4 manuales genéricos del TG**, que son
justo los que responden las consultas TG. Es el mecanismo hp009/DEC-091b, el mismo que hizo
regresar a LEVER2, reapareciendo por una puerta que yo no estaba mirando. Uno de los cinco,
`M710-CZ`, tenía saldo positivo (−2 fuentes, +4) y me tentó dejarlo dentro; lo saqué porque la
regla que aplico a `TG-6000` no puede tener excepciones según me convenga el saldo.

Ese veredicto ahora **está cableado en el instrumento** (`DESBLOQUEA_PERO_ESTRECHA`, con el peor
caso mandando sobre el mejor), así que la próxima tanda lo caza sin que nadie tenga que acordarse.

Por el camino apareció un hueco del gate que llevaba ahí desde s324: su censo mide
`allowed_sources` —que sólo **añade**, porque la unión es protectora— y **no mide `models`**, que
**resta** bajo la política de producción (`replace`). O sea que el gate no podía ver la clase de
regresión que más nos ha costado históricamente. Nace `s334_huerfanos_seam1.py`: 0 pérdidas de
modelo en 156 consultas, los dos lotes.

**Resultado aplicado:** huérfanos 245 → **193**, cuarentena 601 → **520**, consumibles 1.024 →
**1.105**. Y dos ganancias que no son estadística: la gold de `CS4` —el fallo que `HISTORY.md`
documentaba como «CS4 es candidate → ni uno ni otro la reconoce»— y la de la resistencia de fin
de línea del **NFS Supra**, que gana **9 fuentes**.

**El patrón que se repite y que ya tiene nombre** (G1–G5, escritas la sesión anterior): valido el
número y no la definición del número. Tres veces en dos sesiones, siempre sesgado hacia mi propia
conclusión, siempre cazado por otro. La diferencia esta vez es que el instrumento se quedó
arreglado, no sólo la cifra.

**Nota de proceso:** commiteé entre la ejecución de Sol y la de Fable, y el emparejamiento
automático falló porque el manifiesto derivado del snapshot dejó de coincidir. Las semillas eran
las mismas y las dos reviews están guardadas y adjudicadas — falta el sello, no el revisor. No
volver a commitear entre Sol y Fable.

---

## s334b (21 ago 2026) — «193 no me parece correcto»: dos errores míos, un lote que baja a 18, y las dos reglas que escribí por la mañana parándome por la tarde

Alberto no dio por buenos los 193 huérfanos y me dijo que atacara hasta dejar 10. La primera cosa
que encontré al volver a mirar fue que **59 de esos 193 nunca fueron huérfanos**: mi contador
preguntaba `id in consumibles` con la clasificación de la Wiki, donde un `redirect` cae en su propia
clase, mientras el resolver hace `follow_redirect` **antes** de indexar el documento. Reimplementé
la definición en vez de usar la del consumidor y me inventé 59 problemas. La cifra real era **134**.

La segunda fue peor de argumentar: había apartado 181 `unresolved:` diciendo que asignarles
fabricante era adjudicación. Es cierto, y no viene al caso — **promover no exige asignarlo**. El
detector se construye con el `canonical_model` y el índice con su `norm_token`: el namespace no
interviene en ningún sitio. Descarté por prior lo que un instrumento sabía medir.

Con las dos cosas corregidas construí un lote que baja de **134 a 18**, con tres mecanismos nuevos
y cada uno verificado antes de entrar. El que más me gustó: el veredicto
`DESBLOQUEA_PERO_ESTRECHA` que Fable me había obligado a cablear en r42 **no era un muro, era una
señal de que al plan le faltaba su acompañamiento** — añadiendo al `doc_map` del producto, como
`secondary`, las fuentes que la promoción le quitaría, el caso peor (`notifier:tg-6000`) pasa de
«4 fuentes → 1» a «4 → 5». Y el validador del catálogo, al tumbar mi primera versión con 13
«canonical_model DUPLICADO», resultó estar señalando el hallazgo: varios `unresolved:X` son
duplicados de un `<marca>:X` que ya existe, y ahí la operación buena no es promover, es
**redirigir** — se alcanza el manual sin meter un solo término nuevo en el detector.

Hubo también un acierto de método del que me alegro: los 25 términos de riesgo los medí contando en
cuántos documentos aparecen. Con `ilike *X*` salían cuatro palabras. Pero el detector usa **frontera
de palabra**, y con frontera `ITAC` cae de 270 documentos a **11** —casaba dentro de
«capaci**tac**ión»— y `NAS` de 231 a **11**. Dos productos legítimos que habría tirado por medir con
un operador distinto del que usa el consumidor. Sobrevivieron sólo `VIEW` (331) e `INDICATOR` (260),
que sí son palabras inglesas.

**Y entonces el dúo me paró.** Diez hallazgos, diez verificados, cero falsos positivos — y dos de
ellos son **reglas que yo mismo escribí esta misma sesión**: R21 dice literalmente «resolver H o G
es ADJUDICACIÓN, nunca mecánica», y mis 25 redirects resolvían gemelos mecánicamente; el trigger de
`TECH_DEBT #99` dice «higiene de alias antes del siguiente lote grande» cuando uno active más de 20,
y éste activa decenas — el subconjunto más conservador que supe construir todavía activa 85.

Los otros dos críticos son de la misma familia y duelen más. Las 43 altas de `doc_map` escribían «el
manual menciona el producto y sirve como fuente» **sin que yo hubiera leído los 43 documentos**:
inferido de que el paraguas los traía. Y Fable señaló que las «7 ganancias» en gold que yo presentaba
como prueba eran en buena parte **ensanche producido por el propio lote** — una pregunta sobre la
capacidad de batería de la AM-8200 «ganaba» el manual de un gateway. El instrumento de validación lo
estaba modificando el cambio que valida.

Así que **NO-GO**, y creo que es la parte útil de la sesión. Lo que entrego es la corrección de la
definición (con test y control negativo) y un camino ordenado a ≤10 con el prerrequisito nombrado:
higiene de alias primero, leer los 43 documentos después, y dos decisiones de Alberto —las 3
fusiones Morley↔Notifier, que desbloquean 6 manuales de golpe, y los 25 redirects, que R21 dice que
firma él—. Quedan 5 irreducibles: referencias puramente numéricas y un `EEV(2)`, que el detector
excluye a propósito.

Bajar el número aflojando la evidencia es exactamente lo que esas reglas existen para impedir. Que
me hayan parado a mí, el mismo día que las escribí, es la mejor prueba de que sirven.

---

## s334c/d/e (21 ago 2026) — Los dos pasos que eran míos devuelven peor resultado que el prometido, y por eso valen

El dúo me había parado el lote que bajaba a 18 con cuatro objeciones. Dos eran mías —R21 y el
trigger de `TECH_DEBT #99`— y dos me pedían trabajo: hacer la higiene de alias y leer los 43
documentos cuyas atestaciones yo había deducido. Hice los dos. Los dos me dieron la razón a ellos.

**La higiene se pasaba de frenada, y luego invirtió su propio orden.** Censé los 1.175 alias que la
puerta de `_add` deja entrar. Mi regla marcó 82, y al mirarlos uno a uno dos clases enteras estaban
mal: **56 eran alias puramente numéricos** —que `_add` ya descarta por diseño, o sea que retirarlos
es ruido y encima destruye números de parte que un técnico sí escribe— y el criterio del **número de
fabricantes** estaba marcando **cross-references** como si fueran vocabulario genérico: `AFP400` sale
en documentos de Morley, Notifier y Xtralis porque las centrales de una marca se citan en los
manuales de otra. Corregida, la regla dejó 18.

Y ahí mordió R20, la regla que yo mismo había escrito por la mañana: **13 de esos 18 son la única
vía por la que el detector alcanza su producto.** Ocho porque el producto está en cuarentena —su
canónico no entra en el detector *porque* es candidate, así que el alias descriptivo es lo único que
queda— y cinco porque el canónico es digit-only: `kac:2001` se llama literalmente `2001`, que el
detector nunca podrá ver, de modo que `Model 2001` es su vía permanente. **Eso invierte el orden que
el propio `TECH_DEBT #99` prescribía**: la higiene no puede ir del todo antes del lote grande, porque
ocho de los alias «basura» sólo dejan de ser necesarios *después* de promover. Retiré 5.

**Las 43 atestaciones: sobrevivieron 6.** Sol había dicho que estaban deducidas de que el paraguas
las traía, no leídas, y que así el plan «fabrica atestaciones para hacer verde el mismo gate que
evalúa el cambio». Las leí: **32 sin cita, 5 sin texto, 6 verificadas**. El caso que lo resume es
`systemsensor:8100e-faast`, con **catorce documentos y ni uno que lo nombre** — eran manuales de la
familia FAAST que el paraguas arrastraba, sobre otros modelos. Mi inferencia era falsa el 86% de las
veces, y con las citas delante el mecanismo **rescata 0 de 12** de los casos que dependían de él.

**Y de ahí sale la corrección que le debo a Alberto.** Le dije que había «un lote medido que baja de
134 a 18». Era cierto como medida del plan; el plan no sobrevive a su propia verificación. El 18
descansaba en el `doc_map` (muerto) y en los redirects (suyos por R21). **El suelo real sin
adjudicación es 100**, y ahí lo dejé aplicado: 65 promociones con cita verificada más las 6
atestaciones leídas, con 0 gold perdidas, 0 disparos en los negativos y 0 pérdidas de modelo en el
seam 1. Huérfanos 134 → 100, cuarentena 520 → 455, consumibles 1.105 → 1.170.

Tres veces en un día he dado un número que medía algo más ancho de lo que yo decía, y las tres el
número bajó al medirlo bien. La diferencia con la mañana es que ahora el que corrige es el
instrumento, no otro: la regla de R20 saltó sola sobre los alias, y la verificación de citas era un
paso que el dúo pidió y que yo ejecuté sin regatearlo.

---

## s336 (21-ago-2026) — La clave de Gemini, y una sonda que medía qué páginas habíamos guardado

Alberto me ofreció una clave de Google Gemini para «rascar» los manuales huérfanos que ningún
camino de texto alcanza. Monté una sonda multimodal para medirlo y la primera corrida devolvió
`gemini 0/37`. Miré el desglose de errores antes que el titular y eran 58 llamadas perdidas con
429: reportarle «Gemini no lo consigue» habría sido vender un fallo de infraestructura como un
dato. Arreglé el paso… contra el eje equivocado, porque leí la cuota como si fuera por minuto
cuando el `quotaId` dice `GenerateRequestsPerDayPerProjectPerModel-FreeTier`: son **20 al día**.

Con los tres lectores funcionando, la segunda corrida volvió a dar negativos en fila. Seis
seguidos son un olor, así que en vez de teorizar me bajé las páginas y las miré. La portada del
FAD-902 dice **«GUIDE MANUAL / Power Supplies»** y no nombra el modelo por ningún lado; su página
8 es «3.4 Descripción de los leds». **Los lectores acertaban en todas.** La sonda no medía qué
modelo lee mejor una página: medía qué páginas habíamos guardado — `document_visual_assets` es una
selección, mediana de 2 páginas por huérfano en manuales de 30.

Por el camino me equivoqué en voz alta dos veces y las dos hay que dejarlas escritas: llamé
«recortes de figura» a lo que son páginas completas (`visual_role` describe lo que hay EN la
página), y di por buena la explicación antes de mirar.

Los PDF originales sí están en Storage, 83 de los 84. Lo cual convierte la pregunta cara en una
gratis: **¿está el nombre en la capa de texto del PDF?** Leerlos enteros costó minutos y contestó
los 84 de golpe. El resultado: **un lector multimodal paga 2** — los dos escaneados. Los demás se
reparten entre adjudicaciones y promociones. La clave de Gemini nunca fue el desbloqueo.

Dos números míos no llegaron a salir de aquí, y esa es la única mejora que compone. «75 de 84 lo
tienen en el PDF» se cae con **R19** —`NAS`, `TG`, `RHistorico.exe` y «modelo antideflagrante»
pasan la cita sin identificar nada—, y contra el canónico son 49. Y «lo perdimos al extraer» es
**falso en 48 de 49**: el dato ya estaba en `chunks_v2`; lo que faltaba era promover. Los frené yo,
con reglas que había escrito antes, y no el dúo ni Alberto.

Luego vino el lote. Los «20 promovibles» eran una condición de evidencia, no una adjudicación:
R19 y R21 se comieron 17, y el gate cazó lo que mi R21 no vio —sólo cruzaba canónico↔canónico, y
`notifier-inspire-e10` ya es alias de `notifier:inspire-e10`—. El dúo devolvió **9 hallazgos, 9
verificados, 0 falsos**, y los dos revisores convergieron en el mismo fallo: mi prosa decía «R19 6
/ R21 10 / SUJETO 1» y su propio recibo dice R21=11, R19=6, **SUJETO=0**. Había presentado como la
guarda que descartó ID-3000 un filtro que no decidió ni un caso.

Y el hallazgo de Fable cambió el lote. Señaló que el censo del gate flagea `AM-LCD` con
`[sin_digitos, acronimo_corto]` —la clase con la que R19 mata `NAS`— y que yo había escrito
«LPX-751 es el más débil» omitiéndolo. Medí su huella en el corpus **esperando limpiar el flag** y
lo confirmó: uno de sus seis documentos es «Pantalla **FM/AM LCD**», de un manual de radio.
Quedaron dos: `SDX-751-TEM` y `LPX-751`. Huérfanos 84 → 82.

Verificando ese hallazgo apareció lo más caro del día: dos pases idénticos daban `AM-LCD=2` y
`AM-LCD=6`, y el corpus salía con 954 documentos teniendo 1.080. Mis paginadores no pasaban
`order`, y **PostgREST no garantiza orden estable entre rangos**. Arreglado con `order` +
verificación contra `count=exact`, que falla ruidosamente en vez de fiarse de que la última página
venga corta. Re-corrí los dos censos que ya le había enseñado a Alberto: salen idénticos.

Alberto zanjó además una preferencia — **Anthropic sobre Gemini cuando haya que elegir** — y la
cablé en vez de sólo anotarla: `LECTORES=claude,gpt` por defecto. El cross-model no se toca;
Claude y GPT ya son dos familias, y eso es lo que hace del acuerdo una evidencia.

**Lo que queda como rumbo, y no es técnico.** 82 no se acerca a los «10 como máximo» que pidió, y
ahora sé por qué con números: **53 de los 82 están gated en decisiones suyas**. Al descomponerlas
apareció lo mejor de la sesión: los 29 «redirects pendientes» no eran una cola plana — **17 se
desbloquean con 5 firmas**, y `unresolved:id50` → `notifier:id-50` vale 12 manuales él solo.
Simulado sobre una copia del catálogo, **82 → 65 sin un solo huérfano nuevo**. El cuello de botella
dejó de ser el corpus y pasó a ser el calendario de Alberto, que es un sitio mucho mejor donde
tenerlo.

## s336-lote (21/22 ago 2026, noche) — El catálogo Notifier abre los ojos: 3→364 clasificados con un gate que mordió de verdad

La pregunta real de Alberto de las 17:53 («¿Qué centrales de Notifier tienes?» → «ninguno
de los 3 clasificados casa») destapó que la vista Notifier estaba CIEGA: 502 de 505
productos sin clasificar. Su GO abrió el lote: el método CERRADO de s322b (pasada con cita
verbatim + repesca dirigida + full-text) sobre la diana del JOIN REAL — y el camino dejó
tres lecciones que valen más que el resultado. (1) Mi censo a mano inventó «18 sin docs»
por contar con ids crudos en vez de `follow_redirect` — la MISMA clase que s334b, G3 dos
veces en un día. (2) Rompí el emparejamiento de la primera ronda del dúo committeando a
mitad (el gate pinna `repo_head`): ronda repetida LIMPIA, 20 hallazgos en total, entre
ellos dos críticos de Sol (la divergencia NO observada escribía fusión; `clasificacion`
no persistía su doc) y la circularidad del GT que etiqueté leyendo texto completo.
(3) El gate pre-registrado FALLÓ primero (92,9%) exactamente en la trampa que el GT había
pinnado — pl4-e, la tarjeta de ampliación clasificada como su central anfitriona — y el
writer se negó a escribir; la regla R16 al prompt y una re-pasada quirúrgica de las 65
«central» lo llevaron a 100% sin tocar el GT nunca.

Escritura atómica (shadow de 7 jsonl, backup, os.replace con rollback probado): 361 filas
con su doc auditable. Efecto: centrales 0→32, el replay sirve 32 (suelo pre-registrado 11),
cobertura 71,9% → PASS honesto. Suite 4955 + MT 52/52 con el catálogo escrito. La
capacidad, conservadora por diseño (#76b): 1 escrita, 31 a packet — jamás fusión. Y el
residuo con nombre: 98 parse-fail que eran INSTRUMENTO (max_tokens agotado sin texto),
recuperables por ~$2 cuando vuelva el crédito — que se agotó dos veces en el día, la
segunda a mitad de la recuperación. El enum enseñó sus huecos (anunciador, extinción,
audio/EVAC, impresora, barrera-IS): packet a Alberto. DEC-279 (acuñada DEC-273 en el hilo; renumerada al fusionar con la línea de huérfanos que publicó DEC-273→278 primero).
