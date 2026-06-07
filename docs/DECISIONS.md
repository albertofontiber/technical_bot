# Log de decisiones — Technical Bot

> **Qué es.** Registro **append-only** de las decisiones de impacto **MEDIO/ALTO** del
> proyecto, con su **motivo y las alternativas descartadas**, para trazabilidad futura: si
> en una sesión futura nos cuestionamos un camino, aquí está por qué se eligió y qué se
> rechazó. Nace de la lección de la sesión 35: una decisión sin traza obliga a re-litigar
> el marco entero (y a depender de Alberto como memoria humana).
>
> **Cuándo se escribe.** En el cierre de sesión (ver `CLAUDE.md` → "Cierre de sesión"), o
> en el momento de tomar una decisión med/alto. El Protocolo 2 ya obliga a declarar
> alternativas + motivo al proponer; esto solo lo **persiste**.
>
> **Relación con otros docs (mapa canónico).** `PLAN_RAG_2026.md` = roadmap + estado
> (canónico). `RULER_DESIGN.md` = diseño del ruler + sus decisiones D1-D11. `TECH_DEBT.md`
> = deuda con triggers. `ARCHITECTURE.md` = cómo funciona. **Este log** = el *por qué* de
> las decisiones de rumbo. Las decisiones de diseño del ruler viven como D1-D11 en
> `RULER_DESIGN §5`; aquí van las de rumbo/proceso/producción.
>
> **Formato de entrada.** `DEC-NNN — título` · fecha · impacto · decisión · contexto ·
> alternativas descartadas + por qué · revisión adversarial (ref) · estado.

---

## DEC-001 — Revertir change-1 (lever de generación anti-falso-rechazo)
- **Fecha**: 1 jun 2026 (sesión 34). **Impacto**: ALTO (producción).
- **Decisión**: revertir change-1 (bloque "DOS ERRORES SIMÉTRICOS" del SYSTEM_PROMPT) de `main`.
- **Contexto**: re-validado contra el ruler 19/19 (A/B HyDE-off, temp=0): NO rescata ningún
  falso-rechazo (los 5 FALLO son idénticos con/sin → son **retrieval**) e **induce
  sobre-respuesta** en hp015 (inferencia procedimental NO documentada sobre datos reales del
  CCD-103 — riesgo real, pero NO alucinación de datos).
- **Alternativas descartadas**: mantener change-1 → rechazada (neutral-negativo + riesgo hp015).
- **Por qué**: revertir por **PRECAUCIÓN** (riesgo hp015), NO por superioridad de la rama-B.
- **Revisión adversarial**: `adversarial_review_log.jsonl` entrada 2 (9/9 confirmados; cazó
  over-claims de framing: "no rescata ninguno" = escala gruesa; "retrieval es el cuello"
  retractado; revert = precaución, no superioridad).
- **Estado**: ✅ HECHO (PR #18, squash `8473996`, en `main`; Railway desplegado; pendiente
  smoke en Telegram de Alberto).

## DEC-002 — `PLAN_RAG_2026.md` como único doc canónico + este `DECISIONS.md`
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: MEDIO (proceso/docs).
- **Decisión**: `PLAN_RAG_2026.md` es el **único doc canónico** de roadmap + estado + qué
  sigue. Los demás docs tienen un dueño único por tema (mapa canónico en sus cabeceras) y
  apuntan a PLAN, no duplican. Este `DECISIONS.md` registra las decisiones med/alto. El
  cierre de sesión reconcilia PLAN + apendiza aquí.
- **Contexto**: la inconsistencia `PLAN §9.14` (stale, framing s27 "no ampliar ahora") vs
  `RULER_DESIGN §4`/D1 (canónico, "crecer el ruler ahora") **descarriló una sesión entera**;
  el roadmap vivía duplicado en varios sitios y derivaron.
- **Alternativas descartadas**: (a) un doc mega-único → rechazada (ARCHITECTURE/TECH_DEBT
  sirven propósitos distintos; fusionar no es la raíz); (b) sección dentro de PLAN en vez de
  fichero separado → Alberto eligió fichero `DECISIONS.md` separado.
- **Revisión adversarial**: la inconsistencia la cazó el dúo (log entrada 3, F3: "obsoleto"
  era over-claim → son dos ejes compatibles → cross-pointer, no sobreescribir).
- **Estado**: ✅ HECHO (esta pasada de higiene documental).

## DEC-003 — Crecer el ruler por cobertura-diagnóstica (método y nivel)
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: ALTO (gobierna la medición de todos los
  levers futuros, en la ventana pre-técnicos).
- **Decisión**: crecer el ruler como instrumento **DIAGNÓSTICO** (NO gate estadístico).
  **Dos capas**: (1) **breadth-baseline FIJO** con el eje del doc (fabricante/tipo/modalidad
  + idioma/ES-EN) cubriendo las 5 conductas (`RULER_DESIGN §1`) + el caso multi-marca-parcial
  + ES/EN — se re-ejecuta siempre = guarda anti-regresión; (2) golds **lever-targeted ENCIMA**
  (no en lugar de). **Criterio de parada = cobertura de TAXONOMÍA** (cada conducta + cada modo
  que el lever toca representado ≥1 vez con calidad), NO un N. Autoría **costosa** (`§6 Gap #4`)
  → crecer **modesto**. **Barrera anti-contaminación** del sintético (pregunta generada
  cross-model y/o revisión de premisa). Asimetría de ausencia + **fracción ciega** de
  localización en los golds nuevos. El "modo de fallo" es **sesgo de autoría declarado**, no
  el eje primario (sería circular).
- **Contexto**: el ruler 19/19 es fiable pero estrecho (3 fabricantes, mayoría spec-lookups);
  sin más cobertura los deltas de lever son ilegibles (lección change-1 con n=19). La ventana
  para construir el instrumento es **antes** de que haya técnicos (recurso escaso de validación).
- **Alternativas descartadas**: (a) **N fijo objetivo** → gate estadístico, anti-patrón
  `feedback_my_bias #14`; (b) **puro lever-driven sin baseline** → ciega la regresión
  multi-marca YA documentada (nd003/cm007, `TECH_DEBT:310`); (c) **estratificar solo por modo
  de fallo** → circular + revertía el eje del diseño (`RULER_DESIGN:241`); (d) **esperar a las
  preguntas reales de DD** → ventana pre-técnicos (honrado en parte: crecer modesto + diferir
  la inversión grande a #10, que aún no está disponible).
- **Revisión adversarial**: log entradas 3 y 4 (cross-model 8/8 + sub-agente Claude, 2
  críticos). Corrigió over-claims míos: G2 revertía el eje sin declararlo (#15); "autoría
  barata" contradecía Gap #4; "~5-8 golds" era gate estadístico encubierto.
- **Estado**: 🟢 APROBADO; ejecución pendiente. Orden: auditar 13 PARCIAL/5 FALLO → asegurar
  baseline (taxonomía + multi-marca) → golds lever-targeted encima → tirar del lever → medir
  sobre baseline+incremento → repetir (INTERLEAVE).

## DEC-004 — Elevar la metadata de revisión a tarea próxima
- **Fecha**: 1 jun 2026 (sesión 35). **Impacto**: MEDIO (corpus/ingesta; riesgo de corrección
  en producción).
- **Decisión**: elevar la gestión de revisiones (`TECH_DEBT #4`) de *trigger-gated* a **tarea
  próxima**.
- **Contexto**: `chunks_v2` (corpus de producción) NO tiene metadata de revisión/fecha/estado
  (verificado en `migrations/006_chunks_v2.sql`); las RPC no filtran por ella → el bot puede
  **citar una revisión obsoleta** y no puede aplicar la conducta "latest-wins" (`RULER_DESIGN §1:67-72`).
- **Alternativas descartadas**: dejarlo tras su trigger original → rechazada (riesgo de
  corrección en prod + es prerrequisito para enforce latest-wins).
- **Estado**: 🔼 ELEVADO; trabajo (revision_parser → columna en chunks_v2/`documents` → filtro
  en las RPC, ~4-6h) pendiente. Documentado en `TECH_DEBT #4`.

## DEC-005 — Auditoría DEC-003 ejecutada: el cuello está REPARTIDO; doc-routing co-primario
- **Fecha**: 1 jun 2026 (sesión 36). **Impacto**: ALTO (gobierna el próximo lever).
- **Decisión** *(RECOMENDACIÓN — ejecución pendiente de confirmación de Alberto)*: el próximo
  lever es **RETRIEVAL**, con **dos sub-causas estructurales CO-PRIMARIAS**: (1) **doc-routing
  multi-manual** — una query "cómo PROGRAMAR X" no enruta al manual de *Configuración* y trae el
  de *Operación* (clúster mayor; incluye los FALLO hp017/hp018); (2) **ranking within-doc** de
  tablas de specs / secciones concretas (hp006/hp019: el manual correcto entra, la página no). El
  **bundle barato** (subir `retrieve_top_k` + reranker cross-encoder Voyage, ya cableado en
  `reranker.py:rerank_chunks_voyage`) ataca (2) y los rerank-miss, **pero NO (1)** —verificado: la
  causa de hp017 es el **fail-open de `_diversify_by_source_file`** (busca por FTS-keyword, no por
  `doc_type`), no saturación → subir `top_k` no lo arregla. **Generación/conducta** = slice menor
  (hp020 sobre-admite teniendo el dato; hp004 clarify; colas incompletas de PARCIAL). **Extracción
  (#10) descartada**: 0 corpus-gaps reales.
- **Contexto**: auditoría del embudo (HyDE-off, `chunks_v2`, retrieve15→rerank5) por hecho atómico
  CORE, matcher estricto **per-chunk**. Hechos CORE fuertes: **SÍNTESIS≈12 / RERANK≈2 / RETRIEVAL≈13
  / GAP 0** (los 3 "GAP" del instrumento eran artefactos de matcher word/digit, verificados a mano).
  **Los 5 FALLO = 4 retrieval-funnel (hp006/17/18/19) + 1 síntesis (hp020).** Reconcilia: **CORRIGE
  s29** ("generación es el cuello" descansaba en el gold ROTO pre-s31 + el matcher fuzzy que
  sobre-contaba "dato en top-5") y **SHARPENS s34/DEC-001** ("los 5 FALLO son retrieval") a nivel de
  chunk. Instrumento reusable: `scripts/audit_retrieval_funnel.py`; datos:
  `evals/dec003_retrieval_funnel_{noTgt,tgtmodels}.yaml`.
- **Alternativas descartadas (como primer/único lever)**: (a) generación/prompt → change-1 ya
  revertido net-negativo (DEC-001), solo 1/5 FALLO, y parte es CONDUCTA (eje del ruler, no lever);
  (b) extracción #10 → 0 gaps reales; (c) cheap-bundle SOLO → insuficiente para el clúster mayor
  (doc-routing); (d) HyDE on/off → ortogonal, medir aparte.
- **Revisión adversarial**: log entradas **5 (GPT-5.5, 5/5)** + **6 (sub-agente Claude, 7/7)**, EN
  PARALELO. Cazaron y se corrigió: servibilidad solo manual-level → añadí check **fact-level**
  (`fetch_manual_chunks`); `target_models` no replicaba Telegram → **re-medido con `--target-models`
  = diagnóstico idéntico**; anchors cortos 1-núm-2díg inflaban SÍNTESIS → endurecidos a débil;
  "confirma s34" → "corrige/matiza"; **doc-routing de contingente → co-primario**. 1 slip direccional
  del sub-agente (dijo que el sesgo de anchors favorecía la recomendación; es al revés) cazado por
  regla C.
- **Gaps declarados**: n=18, 3 fabricantes, casi todo spec/procedimiento-lookup (0 refuse-inference,
  0 multi-marca, solo 1 clarify en los FALLO); el corte SÍNTESIS/RERANK es **ruidoso** (reranker LLM
  no determinista) → me apoyo en `pool15` (determinista); el label CORPUS-GAP del instrumento es poco
  fiable para hechos word/digit y prosa (produjo 3 falsos, verificados).
- **Estado**: 🟡 AUDITORÍA HECHA; **el framing del lever de abajo quedó SUPERSEDED en la misma sesión
  — ver ACTUALIZACIÓN**.

- **ACTUALIZACIÓN (misma sesión, 2ª pasada adversarial — log entradas 7 GPT-5.5 7/7 + 8 sub-agente 5/5):
  el mecanismo "doc-routing / fail-open de `_diversify`" estaba MAL ANCLADO. RETRACTADO.** Una 2ª review
  del path (fork A=fix del fail-open / B=poblar `doc_type`) lo tumbó, y lo **verifiqué con query directo
  (regla C, `_dec005_verify_hp017`)**: el manual de Configuración ES de la PEARL (997-671, 124 chunks)
  está **mal-etiquetado `product_model='AC-220'`** (no PEARL) → excluido del boosting por modelo y de
  `_get_source_files_for_model('Pearl')`; **SÍ** aparece en vector amplio (3/50) pero **ENTERRADO** bajo
  los chunks PEARL con score-PLANO → **es el bug del merge de scores planos que s29 YA diagnosticó (y
  nunca se arregló)**, no el fail-open del FTS. **Raíz real del clúster "manual equivocado" = (1)
  `product_model` mal atribuido (clase B5, familia de `doc_type`=6%) + (2) bug de merge plano de s29**
  (constantes 0.65–0.85 por-path entierran la similitud vectorial real; s29 lo verificó en hp019, ahora
  en hp017). **Lever revisado = arreglar el merge-scoring (fusión calibrada/RRF, PLAN F1#4) + sanear
  `product_model`** — ambos raíz, ya diagnosticados, más estructurales que A/B/doc-routing; NO requieren
  re-ingesta de contenido. Over-claims retirados (ambas reviews + verificación): "clúster mayor = manual
  ausente" (hp018/hp011 ya tienen el manual en pool15 = página/rerank), "0 corpus-gaps reales" (acotar a
  los 5 FALLO), "fork A-vs-B" (dicotomía falsa), y el FP del sub-agente "vía D filename→doc_type DOMINA"
  (no: para hp017 los chunks no llegan al pool, no hay nada que boostear hasta arreglar el burial).
  **Caveat clave NO resuelto**: toda la auditoría es **HyDE-OFF**; producción usa HyDE-ON, que podría
  mitigar el burial. **Próximo paso APROBADO (Alberto): VALIDAR la hipótesis del burial across el clúster
  (hp005/08/11/18) y con HyDE-ON antes de tocar código** → si se confirma, fix merge-scoring +
  product_model, medido end-to-end vs baseline crecido. Lección meta: change-1 (s30), doc-routing (s36a)
  y fail-open (s36b) eran mecanismos NUEVOS propuestos mientras el bug-raíz de s29 seguía sin arreglar.

- **VALIDACIÓN ejecutada (`scripts/validate_s29_burial.py` → `evals/dec005_burial_validation.yaml`;
  HyDE-OFF vs ON sobre hp017/05/08/11/18 + hp006/19):**
  1. **HyDE-ON no cambia NINGUNA clasificación** (OFF→ON idéntico; HyDE solo sube las sims ~0.6→0.7
     uniformemente) → la auditoría HyDE-OFF **es representativa de producción**. Caveat HyDE CERRADO.
  2. **El "clúster manual-equivocado" era over-generalizado (GPT [crit] confirmado): es n=1.** Solo
     **hp017** falla en traer el manual al pool (metadata `AC-220` + burial s29; HyDE no lo rescata —
     Config-ES en vector rank 3-7, nunca al pool-15). **hp005/08/11/18 SÍ meten el manual al pool** →
     within-doc/rerank, no manual-equivocado.
  3. **hp006 es más hondo**: las páginas de Earth-Fault NO son alcanzables por vector ni en top-50
     (`in_widevec50=False`) → recall-miss real de página (el manual entra al pool por keyword/modelo,
     pero trae otras páginas) → necesita BM25/term-exacto o mejor chunking, no rerank.
  4. → **El cuello dominante NO es routing de manual: es within-doc chunk-ranking** (manual correcto en
     el pool, el chunk con la respuesta no llega al top-5). doc-routing/`doc_type` DESCARTADO como lever.
  - **LEVER consolidado (recomendación; aún no revisado por los adversarios — pendiente Protocolo 3 sobre
    ESTA síntesis):** **sustituir el merge híbrido de scores PLANOS por fusión BM25+dense con RRF**
    (PLAN F1#4) — arregla el bug de s29 (burial: hp017, hp019) **y** el recall de término exacto
    (hp006 "Tierra"/"Earth Fault"), de una; + **sanear `product_model`** (hp017 `AC-220`); el
    cross-encoder reranker es 2ª etapa complementaria (solo ayuda a chunks ya en el pool). Medir
    end-to-end vs baseline crecido. **Revisado el mecanismo 3× esta sesión (cada vez los adversarios/
    verificación lo afinaron) → humildad: validar la síntesis RRF antes de construir.**
  - **Estado**: 🟢 mecanismo VALIDADO (within-doc + s29 burial + metadata; HyDE descartado como mitigante).
    Lever RRF = recomendación pendiente de (a) 3ª review adversarial sobre la síntesis y (b) crecer golds.

- **RESOLUCIÓN del lever (4ª pasada adversarial — log 9 GPT-5.5 7/7 + 10 sub-agente 5/5; VERIFICADO por
  mí, regla C): la síntesis RRF NO SE SOSTIENE → RETRACTADA.** El sub-agente halló (y confirmé en
  `gate.py:133 rrf_fuse` + `evals/gate_results.json`) que **RRF YA se construyó y midió (PR#8, 26-may):
  `hyb_new hit@5 = 0.3636 == vec_new 0.3636` (idéntico; recall@15 0.286→0.305 trivial; verdict NO PASS)**
  — sobre el gold ROTO pre-s31, como proxy de recall, HyDE-off. RRF no rescató NINGUNA de las misses
  (hp006/09/11/12/14/18 = 0.0 en todas las configs incl. RRF). hp017 entra al pool por el saneo de
  `product_model` (no por RRF: vector rank 3 no garantiza top-5); hp006 es recall/chunking (FTS usa AND
  `@@`: si falta el literal, BM25 tampoco). El "ataca los 3 mecanismos de una" = mi patrón #15 otra vez.
- **PATRÓN META de la sesión (feedback_my_bias): propuse 4 mecanismos de lever (change-1→doc-routing→
  fail-open→RRF) y los 4 cayeron por review+verificación.** La causa del bucle: debatir levers sobre
  PROXIES (recall, HyDE-off, gold roto, n=18) en vez del árbitro (calidad end-to-end sobre el ruler
  arreglado). Los protocolos 1+3 hicieron su trabajo (8 reviews, 0 FP propios graves).
- **DECISIÓN (lo que SÍ se sostiene):** (1) la **DIAGNOSIS de DEC-003 está HECHA y es sólida** (instrumentos
  `audit_retrieval_funnel.py` + `validate_s29_burial.py`); NO recomendar ningún build de retrieval ahora.
  (2) El siguiente paso es el que DEC-003 ya aprobó y que yo me salté: **crecer el ruler + medir
  end-to-end** — es lo único que vuelve falsable cualquier decisión de lever. (3) Fix verificado y seguro
  pase lo que pase: **`product_model='AC-220'` del Config-ES de la PEARL** (bug de metadata B5, n=1, bajo
  leverage pero correcto). (4) Opcional barato: re-correr `gate.py` sobre el ruler arreglado (sigue siendo
  proxy de recall, no end-to-end). **No 5º mecanismo.**
- **Estado**: 🔴 lever de retrieval SIN recomendación viable tras 4 intentos; ✅ diagnosis completa;
  pivote APROBADO conceptualmente a "crecer ruler + medir end-to-end" (ejecución pendiente de Alberto).

## DEC-006 — Árbitro end-to-end establecido y calibrado; el bot CONFIRMA DEC-005
- **Fecha**: 1 jun 2026 (sesión 37). **Impacto**: ALTO (instrumento de decisión de todos los levers futuros).
- **Decisión**: ejecutado el paso aprobado en DEC-003/005 — **medir end-to-end** los 19 golds con el árbitro
  real (`test_bot_vs_gold.py` genera respuestas → `atomic_scorer.py --llm`, 3 ejes, HyDE-off, `chunks_v2`,
  metadata de prod ACTUAL). Es el árbitro que vuelve falsable cualquier lever; queda operativo + **ajustado**
  (1 FP de conducta corregido; límites #35/#37 abiertos = calibración PARCIAL, no estabilidad general).
- **Resultado (baseline s37, HyDE-off — config de EVAL, no prod-equivalente: prod usa HyDE-ON)**: **8 FALLO /
  10 PARCIAL / 1 REVISAR / 0 PASS** (0 PASS = el scorer no halló respuesta plena; **alarma fuerte, NO conteo
  definitivo** — la prosa-frágil puede degradar PASS→PARCIAL, #35). **Consistente con el diagnóstico de DEC-005,
  ahora a nivel end-to-end** (no solo funnel): el bot sobre-admite/sobre-clarifica donde el dato está enterrado
  (hp017 bug AC-220, hp019, hp018) + errores de síntesis/contradicción (hp005 matriz, hp011 "00", hp013 batería).
- **Calibración del scorer (2 cambios, dual-review Protocolo 3 SÓLIDO)**: (1) **answer-family gate** —
  answer-con-conflicto colapsa a "answer"; que surfacee AMBAS variantes lo mide COMPLETITUD sobre los hechos
  atómicos, no una heurística de conducta → hp012 puntúa limpio (antes caía siempre a REVISAR). (2)
  **discriminador hedged-admit** — un "admite" con hechos core ENTREGADOS (p>0) es respuesta parcial con hedge,
  no admit real (p≈0) → 3 falsos-FALLO (hp001/14/15) reclasificados a PARCIAL, conservando los over-admit
  REALES (hp017/19, p=0). **refuse-inference EXCLUIDO de ANSWER_LIKE** (cae a REVISAR = juicio humano) hasta
  su check dedicado de "inferencia indebida": el eje factual es contradicción-only → no caza la fabricación de
  compatibilidad cross-brand que no contradiga un hecho listado (cazado por cross-model + sub-agente).
- **Hallazgo clave (lo que el primer run reveló)**: el `atomic_scorer` es fiable para señal CATEGÓRICA
  (over-admit, alucinación) pero **aún no para deltas finos**: (a) admit-FP [ARREGLADO esta sesión]; (b)
  **fragilidad de match de prosa** deflacta completitud → los PARCIAL son un **SUELO**, no el techo real del bot
  (TECH_DEBT #35, completitud-prosa por LLM); (c) **no-determinismo del eje factual** (la contradicción
  cross-model varía run-a-run: hp008/11/13 cambiaron de etiqueta — TECH_DEBT #37 nuevo). Coherente con
  RULER_DESIGN §0 (instrumento DIAGNÓSTICO, no gate estadístico).
- **Alternativas descartadas**: (a) juez opaco del harness → superado por el atómico (s32) + vocabulario de
  conducta stale; (b) crecer el ruler ANTES de medir → la review adversarial lo reordenó (medir-primero valida
  pipeline+scorer y evita autorar sobre un harness no validado); (c) endurecer el scorer-prosa (#35) esta misma
  sesión → diferido (Alberto eligió consolidar); (d) hacer el fix AC-220 inline → es dato de PROD en Supabase →
  cambio separado con contrato de seguridad, medido como delta vs este baseline (pre-fix = realidad actual).
- **Revisión adversarial**: log entradas **11-12** (plan: GPT 7/7 + sub-agente 8/8 → **NO SÓLIDO** → plan
  revisado: medir-primero, elevar eje fabricante/ES-EN, admit al final, pin de metadata pre-fix, regla de
  muestreo) + **13-14** (diff del scorer: GPT 5/5 + sub-agente 3/3 **SÓLIDO** → refuse-inference quitado de
  ANSWER_LIKE, L193 unificado a `expected_gate`). El sub-agente verificó EN CÓDIGO: sin bug de wiring, ningún
  FALLO real se vuelve PASS (solo PARCIAL), asimetría de seguridad preservada (alucinación precede a conducta).
  Tally sano: ~23 hallazgos, ~23 confirmados, 0 FP.
- **Nota de proceso (3ª review adversarial del cierre, log 15-16)**: PR #22 se mergeó (squash `0bba404`) con
  **SOLO s36** mientras la sesión avanzaba; el commit s37 quedó VARADO en su rama (lección s34 sobre reusar rama
  post-squash, re-confirmada) → rescatado vía cherry-pick a un PR nuevo sobre el `origin/main` real. Sin la 3ª
  review el cierre se habría declarado "hecho" con s37 perdido.
- **Estado**: ✅ árbitro operativo + ajustado; baseline s37 registrado como referencia. **Próximo (DEC-003 capa
  1, diferido a s38)**: crecer el breadth-baseline (admit/refuse-inference/clarify + eje fabricante/ES-EN) sobre
  esta base; fix `product_model='AC-220'` (prod, contrato de seguridad) re-medido como delta; endurecer
  completitud-prosa (#35) para que el árbitro lea deltas finos; refuse-inference necesita su check + golds.

## DEC-007 — Dos fixes de producción shippeados (AC-220 relabel + filtro de idioma)
- **Fecha**: 1 jun 2026 (sesión 38). **Impacto**: MEDIO (producción).
- **Decisión**: shippeados vía **PR #24 (merged, `99f8f3d`)**: (1) relabel `product_model 'AC-220' → 'Pearl'`
  del Manual de Configuración ES de la PEARL (`997-671-005-3_Configuration_ES`, 124 chunks, dato en
  `chunks_v2`); (2) **filtro de idioma** en retrieval (`_filter_by_language` descarta los ~96 chunks
  no-ES/EN del pool; + `language` en los selects PostgREST).
- **Contexto/medido**: AC-220 — los chunks del manual de config pasan de **0→9** en el pool-15 de hp017
  (rank 1, HyDE-off determinista) y el bot pasa de **over-admitir (FALLO s37)** a **responder** citando el
  manual correcto. Filtro idioma — 243 tests + smoke vs prod (3 queries, `langs ⊆ {es,en}`, 0 extranjeros).
- **Alternativas descartadas**: AC-220 inline sin medir → rechazada (contrato de seguridad + delta);
  filtro vía RPC migration → rechazada (bypassa el gate PR→Railway; el filtro Python pasa por revisión).
- **Revisión**: smoke + suite verde; AC-220 verificado al píxel (contenido = manual PEARL). `fix_ac220_product_model.py`
  = record idempotente.
- **Estado**: ✅ HECHO (PR #24 merged). Raíz AC-220 = extracción B5 (reaparece en re-ingesta) → `TECH_DEBT #38`/#9.
  **Baseline s37 SUPERSEDED** (prod cambió: AC-220 + filtro idioma).

## DEC-008 — Dirección: crecer el ruler como catálogo diagnóstico sintético 3-bandas
- **Fecha**: 1 jun 2026 (sesión 38). **Impacto**: ALTO (gobierna la fase pre-técnicos).
- **Decisión**: crecer el ruler generando un **catálogo de golds Tier-1 sintéticos source-verified** vía
  proceso **3-bandas** (Claude + GPT-5.5 co-generan desde el manual; dúo adversarial critica), usado como
  **instrumento DIAGNÓSTICO** (correr el bot → localizar en qué parte de la cadena falla con
  `audit_retrieval_funnel` + `atomic_scorer`). **Ejecución por frontera de supervisión**: NOCHE autónoma =
  solo construir `#35` (juez-LLM de completitud, detrás de flag-off + datos crudos); MAÑANA supervisada =
  sign-off de #35 + construir el pipeline de autoría (C4 = localización 2-rutas, convergencia-por-CONTENIDO,
  render±1, doble-lectura de valores; contratos refuse/admit; `cross_generate`) + autorar ~6-8 + diagnóstico.
  **Plan maestro canónico: `docs/CATALOG_PLAN.md` (v4).**
- **Contexto**: no hay técnicos (y serán USUARIOS, no curadores); Alberto no es fuente (query_logs = ecos del
  propio eval, NO señal independiente); 4 levers cayeron en s36 sobre proxies. La maquinaria diagnóstica ya
  existe (s36/s37); falta INPUT ancho (19 golds, 3 fabricantes). GPT-5.5 (linaje ≠ bot=Sonnet) **MITIGA** la
  circularidad al co-generar, NO la rompe; el sign-off humano del scorer (B1) es el único corte fuerte.
- **Alternativas descartadas**: (a) preguntas reales de Alberto/técnicos → no hay fuente fiable; (b) 100%
  Claude-autor → circularidad Sonnet↔Sonnet; (c) routing per-página / Workflow para 6-8 → over-engineering
  (#10 / no aplica); (d) construir+confiar el scorer la misma noche → circular → split a sign-off humano.
- **Revisión adversarial**: **3 pasadas del dúo sobre el plan maestro** (log entradas 18-20 GPT-5.5 +
  sub-agentes en paralelo), todas NO SÓLIDO hasta v4. Cazaron mis over-claims de FRAMING (§0 "GPT rompe
  circularidad", C4 etiqueta-sin-mecanismo, "auto-detecta casos duros") + **2 errores fácticos** (`diagnose_corpus`
  es doc-level no per-página; **AC-220 ya aplicado → baseline s37 superseded**). Regla C: corregí 1 FP parcial del
  sub-agente (coordenadas C4 = ambas físicas, migración 006 → fix = converger por CONTENIDO). Convergió a v4 cuando
  los hallazgos pasaron a contratos-de-implementación (resueltos en B2 supervisado), no fallos estructurales.
- **Estado**: 🟢 APROBADO; plan maestro v4 CERRADO (`docs/CATALOG_PLAN.md`). **Próximo**: Fase A esta noche (#35);
  B/C mañana supervisado.

## DEC-009 — Refinamientos de ejecución de DEC-008 (s38 supervisada): C4 robusto + estructura de docs
- **Fecha**: 2 jun 2026 (sesión 38, mañana supervisada — tras Fase A HECHA y B1 FIRMADO). **Impacto**: MEDIO
  (ejecución de DEC-008; afecta la calidad del ruler, que Alberto declaró clave).
- **Decisiones**:
  1. **C4 (cross-check de localización) = localización ROBUSTA, NO budget-bounded** (decisión Alberto: "prefiero
     una solución robusta antes que mala y barata, ya que definir buenos golds es clave"). La **ruta semántica
     per-manual se ELIMINA** (el dúo: rankear `chunks_v2`/Voyage = el sustrato del bot → circular, viola
     `RULER_DESIGN §0`). C4 final = grep multi-manual + mapeo producto→manuales + **render±1** + **doble-señal AND**
     (lectura cross-model del render ∧ match determinista del valor en el texto de esa página); scan o discrepancia
     → `needs_human`, no fabricar. **Diseño durable = `RULER_DESIGN §2`** (a construir en B2/s39).
  2. **Estructura de docs (single-source; aplica DEC-002)**: NO fusionar `RULER_DESIGN` y `CATALOG_PLAN`. Cada uno
     un hogar: `RULER_DESIGN` = diseño DURABLE del ruler (localización §2, conductas §1) + record; `CATALOG_PLAN`
     = ejecución TRANSITORIA de UN esfuerzo (fases, rejilla, contrato del run) que **referencia §2, no lo duplica**,
     y se **ARCHIVA** al cerrar (lecciones durables → RULER_DESIGN/DECISIONS); `PLAN` = roadmap+estado.
- **Alternativas descartadas**: (a) localización barata budget-bounded (render top-k acotado) → rechazada por
  Alberto (golds = clave > coste); (b) fusionar RULER_DESIGN+CATALOG_PLAN en un doc → no (mezcla diseño durable con
  ejecución transitoria); (c) C4 folded en CATALOG_PLAN como hogar del diseño (vuelta previa) → REVERTIDO (el diseño
  durable va en RULER_DESIGN §2; CATALOG_PLAN solo lo del run).
- **Revisión adversarial**: dúo sobre el diseño C4 (`adversarial_review_log` ts 12:18, 8/8, ruta-b circular eliminada)
  + sobre la estructura de docs (ts 12:56: sub-agente SÓLIDO-separar; cazó **`RULER_DESIGN §4` STALE** = la trampa
  DEC-002 que mi "puntero F3" subestimaba, y mi fold de C4 equivocado; 1 FP parcial del cross-model "duplicación
  material" → re-statement-citando-§2). Regla C aplicada. Mi over-claim "single-source ya satisfecho" retirado.
- **Estado**: ✅ HECHO (diseño + reconciliación). Commit `9db0263` en `eval/s38-night-catalog` (rebasada sobre
  `main`=#25, 243 tests verdes). C4 se CONSTRUYE en B2/s39.

## DEC-010 — C4 + cross_generate construidos; producto→manuales = opción D (filesystem); piloto cat001/005/007 + 1er diagnóstico
- **Fecha**: 2 jun 2026 (sesión 39, supervisada). **Impacto**: ALTO (instrumento de localización del ruler + 1er gold crecido medido).
- **Decisiones**:
  1. **C4 construido** = `scripts/locate_fact.py` (grep multi-manual sobre PDFs FUENTE → render±1 → **doble-señal AND**:
     lectura cross-model GPT-5.5 ∧ match determinista; scan/discrepancia → `needs_human`). chunks_v2 SOLO para
     corpus-existence (no circular, RULER_DESIGN §0/§2). **`scripts/cross_generate.py`** = co-generador GPT-5.5 (C2).
  2. **producto→manuales = OPCIÓN D** (NO la "B-síntesis" que propuse): el SET de manuales lo fija el AUTOR
     explícito (`--manuals`), con un sugeridor exhaustivo dirigido por FILESYSTEM (no por `product_model`, que está
     estructuralmente sucio: doc-codes 'MPDT-280', 'AM2020 y AFP1010', familia dispersa en ≥5 etiquetas — verificado).
  3. **Contratos refuse/admit DIFERIDOS** (no hubo celdas de conducta en el piloto 1/5/7; van con 16/18/19).
  4. **Piloto autorado (3 golds, `cat001/005/007`)** por el proceso C4→co-gen→doble-lectura→poda→**dúo C3**→regla C→
     `gold_store.upsert` (22 golds, 0 errores de esquema).
- **Diagnóstico end-to-end (1ª medición sobre el ruler crecido; HyDE-off, chunks_v2, `atomic_scorer` mecánico)**:
  3 PARCIAL, **factual=sin contradicciones en los 3 (0 alucinación)**. Localizado por hecho: **cat005** (CS4 gas,
  single-doc) 5/6 y **cat007** (FAAST, ES/EN, single-doc) 4/5 = FUERTES (misses = ruido de matcher / menores); el
  bot maneja **dominio nuevo** (gas/Fidegas) y retrieval **cross-variante** (FAAST QIGs hermanos) sin fallar.
  **cat001** (PEARL multi-doc) 2/7 = **SÍNTESIS INCOMPLETA real** (verificado leyendo la respuesta): retrieval ✓
  (ambos manuales) + 0 alucinación, pero omitió los hechos cross-doc duros (conflicto 40-CLIP en lazo mixto, 0,75 A,
  99+99 CLIP, zonas 255/8192) y derivó a detalle tangencial. **Consistente con DEC-005/006: el cuello en multi-doc
  es completitud de SÍNTESIS, no retrieval ni alucinación.** El ruler crecido **discrimina** (instrumento válido).
- **Contexto/método**: B2→B3→C de DEC-008/009. La rebanada vertical (test ciego de C4 sobre hp017/hp005/hp012,
  ignorando la `page` conocida) cerró el "test ciego del localizador" que RULER_DESIGN §2 declaraba pendiente, y
  cazó 4 bugs de mi implementación (fuga de idioma; match determinista value-only; veredicto VLM value-only;
  sobre-generación de prosa) + 2 bugs más en autoría (`_value_on_page` substring sin frontera → '792'∈'13792';
  parser de `--pages` con nombres con espacios). La doble-señal cazó un misread de dígito (3240 vs 3244 → 3244 @400dpi).
- **Alternativas descartadas**: (a) **B-síntesis** (grep por carpeta del fabricante) → NO SÓLIDO en review: solo 2/23
  fabricantes tienen carpeta dedicada (no escala al contrato), `_Privado` NO es dedup (288 docs únicos en Notifier,
  incl. los del gold hp012), describía un sistema sin construir; (b) sanear `product_model` antes → es un lever de
  retrieval del bot, separado; C4 debe ser INDEPENDIENTE de esa metadata (§0); (c) índice versionado
  `producto→source_files` (forma escalable de D) → DIFERIDO (para 6-8 golds basta `--manuals` explícito).
- **Revisión adversarial**: dúo (sub-agente Claude + GPT-5.5) ×4 — diseño producto→manuales (`adversarial_review_log`
  entrada 6: NO SÓLIDO sobre B, 10 hallazgos/10 confirmados/0 FP, 3 críticos verificados por mí regla C) + C3 por
  gold (cat001/005/007, todos SÓLIDO-CON-CAMBIOS; cambios verificados al píxel). El cross-model cazó lo que mi
  auto-pushback del contrato NO (presenté B como sólido tras pushback; era NO SÓLIDO) → guardarraíl anti-bias OK.
- **Gaps declarados**: (a) `atomic_scorer` mecánico (sin `--prose-llm`) → **PARCIAL es un SUELO** (matcher-prosa
  frágil: cat005 '110-230', cat001 '25' under-contados; la incompletitud de cat001 SÍ es real, verificada a mano);
  (b) piloto n=3, 1 multi-doc → señal categórica, no delta fino; (c) `_provenance.corpus_chunks_v2` "PENDIENTE" en
  cat005/007 quedó RESUELTO (CS4=11, FAAST LT-200 ES=42 chunks → cubiertos; no corpus-gap) — corregir nota.
- **Estado**: ✅ HECHO. **Próximo (s40)**: crecer el catálogo a más celdas (Tier B gap-diagnóstico 12/14/15 +
  conductas 16/18/19 con sus contratos refuse/admit) + endurecer `atomic_scorer --prose-llm` para leer deltas finos;
  el índice versionado producto→source_files si la autoría escala. PR de `eval/s38-night-catalog` a `main` cuando se cierre el lote.

## DEC-011 — Consolidación del árbitro (s40): fix del matcher de rangos + `--prose-llm` validado para el cabo B1
- **Fecha**: 2 jun 2026 (sesión 40). **Impacto**: MEDIO (instrumento de medición que gobierna los levers futuros).
- **Decisión**: sesión de CONSOLIDACIÓN del árbitro (Alberto eligió foco "solo consolidar", NO crecer golds). Tres resultados:
  1. **Fix RAÍZ del matcher de RANGOS** en `strict_match.distinctive()`: `_NUM = r"(?<!\d)[+\-]?\d[\d.,]*"`. Antes,
     `distinctive("110-230")`→`{'110','-230'}` (el guion de un rango se leía como signo); el `-230` fallaba la frontera de
     dígito de `_anchor_present` (atomic_scorer) Y `_value_on_page` (locate_fact) → falso-miss. **Era la causa REAL del
     "cat005 PARCIAL=suelo" de DEC-010, NO fragilidad de prosa** (el caveat conflataba dos cosas). → cat005 5/6→**6/6 PASS**
     (el bot cita "110-230 Vac"); **los 19 golds hp/cm/nd IDÉNTICOS** (A/B mecánico sobre el cache k5 = cero regresión);
     249 tests (+6 nuevos en `tests/test_strict_match.py` que fijan el contrato rango-vs-signo).
  2. **`--prose-llm` (#35): NO se endurece.** El cabo de B1 (hp007 `'cada 2 años'` sospechoso de over-credit) está
     RESUELTO: el bot dice literalmente "mantenimiento **bienal**" (=cada 2 años) y "comprobación **trimestral**" (=cada 3
     meses) → paráfrasis legítima. Prueba de no-over-credit en el piloto: cat007 `'no enclavado'`→"no cubierto" (el bot
     ADMITIÓ no conocer el failsafe). El overlay es conservador (solo False→True). NO es validación amplia (n pequeño).
  3. **Diagnóstico autoritativo del piloto post-fix** (HyDE-off, chunks_v2, `--llm --prose-llm`): **cat005 PASS 6/6**
     (0 contradicciones), cat007 PARCIAL 4/5 (miss REAL: el bot admitió), cat001 PARCIAL 2/7 (omisión REAL de anchors
     cross-doc duros; factual=0 contradicciones → omisión, NO error). La CAUSA de cat001 (síntesis vs retrieval) es del
     funnel de s39, **NO re-verificada aquí** (sin over-claim causal).
- **Efecto colateral declarado** (sub-agente, hallazgo B): el fix vive en el matcher COMPARTIDO; soltar el signo de una
  **suma SIN espacios** ('159+159/99+99') relaja `all(anchor in chunk)`. Impacto ACTUAL = cero (19+3 A/B idéntico);
  potencialmente más laxo para futuros hechos-suma en el scorer Y en los instrumentos de retrieval. Prevalencia: **1 hecho
  de 134** (solo cat001; hp012 '99 + 99' CON espacios es INMUNE; los 3 rangos NO inflan = soltar el `-X` espurio es fix).
- **Alternativas descartadas**: (a) endurecer el prompt de prosa → innecesario (cabo B1 cerrado, no over-credit); (b) fix
  solo-rangos para evitar la relajación de sumas → la leniency es intrínseca (rango y suma = mismo fenómeno "operador entre
  dígitos") + impacto 0 + hacky → sobre-ingeniería para 1/134; (c) regenerar un baseline FRESCO de los 19 post-AC220 →
  fuera del scope (Alberto acotó a consolidar + piloto); queda como trabajo disponible.
- **Revisión adversarial (Protocolo 3, dual — código de medición)**: sub-agente Claude (lee código + A/B empírico) →
  **SÓLIDO**, 9/9 confirmados/0 FP (cazó: 2º consumidor con frontera `_value_on_page`; la relajación de sumas afecta cat001
  no hp012; recall-inflación acotada 1/134). Cross-model GPT-5.5 (`adversarial_review_log` ts 2026-06-02T18:01:40) →
  5/5 confirmados/0 FP, **TODOS de FRAMING** (mi sesgo): "validado en general"→cabo-B1; "no toca scoring"→matcher
  compartido; "cuello multi-doc confirmado"→omisión-no-causa. Framing aplicado a esta entrada.
- **Gaps declarados**: (a) el A/B de los 19 usó respuestas CACHEADAS pre-AC220 (s37) → válido SOLO como check de
  regresión del matcher (mismas respuestas, solo cambió el matcher), NO baseline fresco; (b) prose-llm validado con n
  pequeño; (c) "cat001 incompletitud real" se apoya en anchors ausentes + factual=0 + lectura manual s39, no en técnico;
  (d) relajación de sumas aceptada sin endurecer.
- **Estado**: ✅ HECHO (rama `eval/s40-arbiter-consolidation` → PR). **Próximo (s41)**: crecer el catálogo (Tier B
  12/14/15 + conductas 16/18/19 con contratos refuse/admit) sobre el árbitro consolidado; opcional, baseline fresco de
  los 19 post-AC220.

## DEC-012 — Eje NO-FABRICACIÓN del scorer + ramificación por estado-del-hecho (contrato admit/refuse-inference)
- **Fecha**: 2 jun 2026 (sesión 41). **Impacto**: MEDIO (instrumento de medición que gobierna los levers; zona de
  dolor = scorer/conductas). **Alcance ELEGIDO por Alberto**: cerrar el árbitro endurecido; autoría de celdas → s42.
- **Contexto**: s41 iba a autorar celdas de conducta (#16 admit, #18 refuse-inference, #19 clarify), pero los
  **contratos refuse/admit estaban DIFERIDOS** (DEC-010 §3). Al especificarlos, el dúo destapó un **agujero del
  scorer**: el eje factual (`factual_check`) es **solo-contradicción** → cuando el corpus está VACÍO sobre un tema, un
  bot que FABRICA sobre el vacío no contradice nada y NO se caza (lo declaraba el propio código, `atomic_scorer §57-60`).
- **Decisión (la §6, elegida por Alberto tras el voto del dúo)**: cablear un **eje NO-FABRICACIÓN** como check LLM
  cross-model, NO el fallback humano (REVISAR). El voto del dúo fue check-LLM **por FALSABILIDAD** (no por "escala", que
  el autor sobre-ponderaba): el fallback humano deja refuse-inference en REVISAR para siempre = cero señal categórica, y
  un humano sin veredicto-máquina contra el que contrastar es igual de opaco. Lo construido:
  1. **C1 — `score_gold` ramifica por `estado`-del-hecho**: los `ausente-probado` salen del denominador de completitud
     (el bot NO debe entregarlos) y alimentan el eje no-fabricación. Cubre el patrón D5 (ausente-probado dentro de un
     `answer` mixto: hp006/09/13), no solo admit/refuse → el eje va POR-HECHO, no por conducta_esperada.
  2. **`undue_inference_check`** (cross-model GPT-5.5, gated `--llm`, binario, conservador): caza que el bot AFIRME un
     hecho ausente-probado (valor/compatibilidad/recomendación/inferencia; claims prohibidos enumerados en `_UNDUE_SYS`).
     Asimetría de seguridad: afirmar un ausente = FALLO.
  3. **refuse-inference entra en `ANSWER_LIKE`** (deja de caer a REVISAR): su fallo típico lo caza ahora el eje no-fabricación.
- **Validación end-to-end (re-baseline FRESCO post-AC220, HyDE-off, `--llm --prose-llm`)**: **7 FALLO / 10 PARCIAL /
  2 REVISAR / 0 PASS** (19 golds; vs s37 8/10/1/0: AC-220 sacó hp017 de FALLO, el eje no-fabricación metió hp006). El
  eje **funciona**: hp006 PARCIAL→FALLO (el bot fabrica un procedimiento de localización del fallo de tierra que el
  manual NO documenta — spot-check humano: 2/3 marcas correctas; 1 FP por hecho mal formulado, ver gaps). hp009 "sin
  fabricación sobre ausentes" (FALLO por completitud, no por fabricación = correcto). El **filtro factual** (los
  ausente-probado ya NO van a `factual_check`) MEJORÓ hp013 (contradicción sobre un hecho PRESENTE real, no sobre el ausente).
- **Alternativas descartadas**: (a) **fallback humano** (refuse/admit→REVISAR siempre) — suelo seguro pero cero señal
  categórica, no escala; es el fallback si el spot-check no valida. (b) **solo keywords** (`_NOINFO`) — frágil, solo-ES,
  no caza fabricación parcial. (c) **colapsar refuse→admit** — refuse SÍ da contenido (specs por-producto); colapsarlo
  perdería la completitud de los `presente`.
- **Revisión adversarial (Protocolo 3, DUAL × 2 RONDAS — `adversarial_review_log` 2026-06-02T20:00/20:05/20:25/20:30)**:
  - **R1 (diseño)**: ambos SÓLIDO-CON-CAMBIOS. 3 críticos: el scorer no leía `f["estado"]` (los 3 ausente-probado de
    hp006/09/13 viven en answer mixto, no admit/refuse); el "modo-ausencia" de locate_fact es greenfield no reutilización;
    `_ECOSYSTEM_OF` (retriever.py:230) colapsa Detnov↔Securiton por OEM → Contrato B debe elegir ecosistemas DISJUNTOS.
  - **R2 (diff)**: ambos SÓLIDO-CON-CAMBIOS. **BUG CRÍTICO de orden** (cross+sub): los errores de eje (REVISAR) se
    evaluaban ANTES que los FALLOS → un FALLO real se degradaba a REVISAR si el otro eje daba error → violaba la
    asimetría de seguridad. **ARREGLADO** (FALLOS primero). + refuse offline sin red (sub) → degradar PASS+absent a
    REVISAR sin `--llm`; + ausente-probado con valor no-null iría al factual (sub) → filtro factual; + esquema JSON
    (cross) + cita de línea (sub). **TODOS aplicados.**
  - **Tally s41: 22 findings / 22 confirmados / 0 FP** (cross 6+6, sub 6+4). Regla C: verifiqué en código el bug de
    orden, `_ECOSYSTEM_OF` y los 3 ausente-probado con valor=null; cacé 1 sobre-cuenta menor del sub (4 vs 3 hechos,
    dentro de un finding válido). 261 tests verdes (+8 nuevos `tests/test_atomic_scorer.py`, incl. casos cruzados error+FALLO).
- **Gaps declarados**: (a) el eje no-fabricación es estructuralmente **MÁS FRÁGIL que el factual** (opera sobre
  valor=null, sin ancla textual) → señal CATEGÓRICA no fina; spot-check humano. (b) **FP en hp006**: el check marcó 3
  fabricaciones, 1 es falsa (explicar el aviso Tierra SÍ está en MIDT170) porque el hecho `ausente-probado` de hp006
  **mezcla** "no hay procedimiento" con una nota parentética sobre otro manual → **deuda: re-formular el hecho
  quirúrgicamente** (TECH_DEBT) + **lección de autoría** (los ausente-probado = solo lo ausente). El veredicto
  CATEGÓRICO (FALLO) es correcto igual (≥2 fabricaciones reales). (c) recall/especificidad del check NO validados sobre
  golds de conducta REALES (n=0 hoy; las celdas #16/#18 de s42 lo harán). (d) varianza del factual LLM en el CONTEO de
  contradicciones (no en el categórico) — TECH_DEBT #37. (e) el **modo-ausencia de locate_fact** y la autoría de celdas
  se DIFIRIERON a s42 (Alberto acotó s41 a cerrar el árbitro).
- **Estado**: ✅ HECHO (rama `eval/s41-nonfab-axis` → PR #29 MERGEADO `55a6b5a`; eval-only, no toca prod). **Próximo
  (s42)**: ver DEC-013 (rumbo REORIENTADO tras el dúo).

## DEC-013 — Rumbo de s42 REORIENTADO tras el dúo: #37 (determinismo) → lever del BULTO; modo-ausencia DESCARTADO
- **Fecha**: 2 jun 2026 (sesión 41, planificación de s42). **Impacto**: ALTO (decide el rumbo; supersede el backlog
  "autoría de conductas" heredado del cierre de s41). **A petición de Alberto**: Protocolo 3 dual sobre el plan ANTES de comprometer s42.
- **Decisión (elegida por Alberto tras el dúo)**: s42 = **#37 → lever del bulto**, NO autoría de conductas por cobertura.
  1. **PRIMERO cerrar `TECH_DEBT #37`** (eje factual no-determinista: temp=0 + multi-run/votación, o caracterizar la
     varianza). Prerrequisito REAL: el re-baseline "7 FALLO" es un draw de una variable ruidosa → sin estabilizarlo,
     ningún delta de lever es legible (medir un lever contra esto repetiría el error "medir contra gold roto", s30).
  2. **Diagnóstico ESTABLE del bulto** de FALLO: contradicción (hp005/11/13, eje factual) + completitud-0/N (hp008/09)
     + síntesis (cat001). El bulto ≈6-7 golds; el eje no-fabricación de s41 toca **1** (hp006).
  3. **Tirar del lever de mayor señal sobre el bulto** — concreto **TBD tras el diagnóstico estable** (NO presuponer
     "generación-grounding" ni "anti-fabricación"), medido vs el baseline estabilizado. INTERLEAVE (RULER_DESIGN §4):
     demostrar mejora de PRODUCTO, lo que no se hace desde s34.
  - **Smoke barato del eje no-fabricación** (#19 clarify + 1 #18 refuse-inference, par disjunto verificado contra
    `_ECOSYSTEM_OF`: Notifier↔Morley/Detnov) = higiene del instrumento mergeado sin ejercer (hp006 tiene FP);
    **intercalable, NO bloqueante** — el lever del bulto se mide con factual+completitud, NO usa el eje no-fabricación.
- **DESCARTADO para s42** (el dúo lo desmontó): **modo-ausencia ambicioso + #16 admit**. grep=0 ≠ ausencia CONCEPTUAL
  (vocabulary mismatch ES/EN); `is_scan` es por-DOC (`scan_ratio>=0.6`) cuando la trampa OCR es por-PÁGINA (clase D4,
  costó hp009/18) → afirmar `absence_supported` es frágil + el set de manuales no es cerrado. "Validar el eje con
  n=2-3" = over-claim (es ejercitar, no validar: recall/especificidad necesita n≥5/9). Diferidos hasta un modo-ausencia por-página, si vale la pena.
- **Alternativas**: (A) backlog literal (modo-ausencia+autoría) — desaconsejado; (B) lever YA sin estabilizar #37 —
  repite "medir contra gold roto"; (C/C') autorar-para-validar-el-eje — el "validar" es ilusión con n pequeño, y el
  lever del bulto no necesita el eje no-fabricación → el smoke se degrada a higiene intercalable.
- **Revisión adversarial (Protocolo 3, dual)**: cross-model **7/7** + sub-agente **7/7**, 0 FP (`adversarial_review_log`
  2026-06-02T21:35/21:40). **LOAD-BEARING (sub-agente)**: mi plan conflactó CONTRADICCIÓN (hp005/11/13, eje factual)
  con FABRICACIÓN (eje no-fab, toca hp006 n=1) → el "lever anti-fabricación" presupuesto atacaba **1 gold** = sesgo de
  inercia del backlog. **Regla C**: verifiqué la conflación en el baseline-log + el no-determinismo de #37 + `is_scan`
  por-doc + los pares disjuntos; **matiz mío sobre el sub-agente** (no es FP): su "lever de generación-grounding" es
  HIPÓTESIS (la causa del bulto —retrieval vs generación vs síntesis— no está re-verificada), no certeza → el lever concreto se decide con el bulto estable.
- **Gaps**: el lever concreto NO está decidido (a propósito); #37 puede revelar que parte del "bulto" era ruido (menos
  FALLO reales de los contados); el smoke del eje no-fab con n pequeño es señal categórica, no validación.
- **Estado**: ✅ rumbo fijado. **s42 (sesión dedicada) arranca por `TECH_DEBT #37`.** Canónico: `PLAN` bloque s41 "Próximo (s42)".

## DEC-014 — Método de cierre de `TECH_DEBT #37` (denoise del eje factual): v2 tras el dúo
- **Fecha**: 2 jun 2026 (sesión 42, ejecución del paso 1 de DEC-013). **Impacto**: MEDIO (zona de dolor:
  scoring/árbitro; fija cómo se estabiliza el baseline contra el que se medirá TODO lever). **A petición de
  Alberto**: Protocolo 3 dual sobre el plan ANTES de cablear; orden "primero plasmar v2, luego ejecutar".
- **Contexto**: DEC-013 fijó "cerrar #37 primero" y esbozó "temp=0 + multi-run/votación". Leer
  `atomic_scorer.py` + cómo todo el repo llama a gpt-5.5 desmonta ese esbozo → método v2.
- **Decisión (v2 — principios A PRIORI + parámetros data-dependent declarados)**:
  1. **Testear, no inferir** (temp/seed): la fuente del ruido son las 3 llamadas cross-model
     (`factual_check:143`, `undue_inference_check:200`, `prose_complete_check:249`) SIN `temperature`/`seed`.
     Pero "el repo lo omite ⇒ gpt-5.5 rechaza temp≠1" es INFERENCIA (H2) → 1-2 llamadas controladas la
     resuelven: ¿`temperature=0` da error? ¿`seed`+input idéntico → output/`system_fingerprint` idéntico?
     (`seed` probablemente INERTE en reasoning-model sin sampling — verificar, no asumir).
  2. **Endurecer el formato en el ORIGEN > promediar sobre el ruido**: las llamadas no usan
     `response_format`/schema; un parse/red error → `factual_error` → veredicto REVISAR (`:327-330`) =
     inestabilidad NO-sampling y NO-0↔1. → `response_format={"type":"json_object"}` (o structured outputs si
     gpt-5.5 los soporta) mata esa fuente estructuralmente. Fix más BP que la votación.
  3. **Caracterización screen-then-focus**: K=5 screen sobre los 19 → golds con CUALQUIER inestabilidad de
     VEREDICTO (flips-a-REVISAR-por-error contados APARTE de cruces de conteo 0↔1) → K alto (10-15)
     FOCALIZADO en el subconjunto inestable (K=5 plano es subpotente para una tasa ~3/19 ≈ p0.15: "varianza
     ~0" podría ser submuestreo = cierre prematuro).
  4. **Agregación = decisión de SEGURIDAD a priori, NO empírica**: el eje es false-negative-biased por
     contrato (`:122` "ante la duda NO marques contradicción"). Votar por MAYORÍA lava una contradicción
     real que solo 2/K runs cazan (washout) = 2ª capa conservadora; la DIRECCIÓN no se elige minimizando
     varianza. Salida honesta para un eje frágil = **veredicto + FLAG DE ESTABILIDAD + spot-check humano**
     (patrón DEC-012), no voto silencioso. Unión/≥1 tampoco es incondicional: depende de si el ruido per-run
     son MISSES (unión recupera) o SPURIOUS (unión amplifica) → lo decide la ESTRUCTURA del error de (3).
  5. **Separar diagnose de confirm**: la screen DIAGNOSTICA; se congela la regla; el baseline se valida en
     pasada CONFIRMATORIA separada (no elegir K+regla y declarar baseline del mismo draw = post-hoc).
     Artefactos auditables logueados (raw outputs, modelo, `system_fingerprint`, tasa parse-error, regla).
- **Sharpening (verificado en código)**: el veredicto es robusto al CONTEO salvo el filo 0↔1
  (`if contradictions: FALLO`, `:323`); s37: hp011 (1→2)/hp013 (2→1) siguen FALLO, hp008 (1→0) cae a
  completitud-0/4 = FALLO igual → la métrica es ESTABILIDAD-DE-VEREDICTO, no varianza-de-conteo.
- **Alternativas descartadas**: (A) `temp=0` y listo — gpt-5.5 probablemente lo rechaza + no da
  bit-determinismo (`run_eval.py:514`). (B) votación por mayoría — washout sobre eje de seguridad
  (desmontado por el sub-agente). (C) `seed` como único mecanismo — best-effort, probablemente inerte.
  (D) votación a ciegas con K fijo sin medir — presupone K, pierde el diagnóstico. (E) decidir la agregación
  "con los datos" (mi propuesta inicial) — dejaría que la minimización de varianza eligiera mayoría en
  silencio (la regla insegura); cazado por el dúo.
- **Revisión adversarial (Protocolo 3, dual)**: cross-model **5/5** + sub-agente **+2** medio/alto, **0 FP**
  (`adversarial_review_log` 2026-06-02T22:11, entrada #31). **LOAD-BEARING (sub-agente)**: agregación por
  mayoría sobre eje de seguridad asimétrico = washout; la dirección es a priori, no empírica. **Convergencia
  (ambos)**: testear temp/seed empíricamente + endurecer `response_format` (kill estructural) > votar.
  **Regla C**: verifiqué el path error→REVISAR (`:150/:156/:327-330`), la ausencia de `response_format`, y el
  contrato false-negative-biased (`:122`). **Regla F (matiz mío)**: unión no es incondicional → flag de
  estabilidad + spot-check, no voto.
- **Gaps**: K y la dirección final de agregación quedan data-dependent (a propósito); el micro-test (1) puede
  revelar que `temp=0` SÍ funciona (simplificaría parte de (2)-(4)); si tras endurecer el formato la varianza
  de veredicto resulta ~0, #37 cierra SIN aparato de votación (buen desenlace eval-driven, no fallo).
  `prose_complete_check` comparte el ruido pero queda fuera del baseline `--llm` (flag `--prose-llm`, #35.1).
- **Estado**: ✅ EJECUTADO (s42) — ver **Resultado** abajo. **#37 (determinismo del eje factual) CERRADO.**

## DEC-015 — Resultado de #37 (s42): contrato (d) REVERTIDO, baseline legible = response_format + mayoría+flag
- **Fecha**: 3 jun 2026 (s42, ejecución). **Impacto**: MEDIO (cierra el método de DEC-014; decide el baseline
  contra el que s43 medirá el lever). **Eval-only** (no toca producción). Dúo: log `adversarial_review_log` #31-33.
- **Lo ejecutado**:
  1. **temp/seed MUERTOS** (probe `scripts/probe_gpt55_determinism.py`, testeado NO inferido): gpt-5.5 RECHAZA
     `temperature=0` ("only default 1 supported") y `seed` es inerte (`system_fingerprint=None`) → no hay knob
     de determinismo a nivel API; el sampling es irreducible. Alts A/B (de DEC-014) muertas empíricamente.
  2. **`response_format={"type":"json_object"}`** en las 3 llamadas cross-model (aceptado por gpt-5.5) → mata el
     path parse/red-error→REVISAR en el ORIGEN. Confirmado: **0 error→REVISAR** en los 22 golds del baseline.
  3. **Caracterización** (`scripts/characterize_factual_variance.py`, K-run + estabilidad de VEREDICTO): el bulto
     (hp005/11/13 contradicción + hp006/08/09 completitud + hp019) es VERDICT-STABLE; el sharpening H3 validado
     (el conteo wobblea pero el veredicto no cruza salvo en el filo 0↔1).
  4. **Sub-quest del contrato (cláusula (d)) INTENTADO y REVERTIDO** (2 rondas de dúo): la caracterización mostró
     que la inestabilidad de hp010/hp020 venía de que el eje factual contaba "el bot dice que el manual no cubre
     X" como contradicción (infra-declaración = competencia de COMPLETITUD). Afiné `_FACTUAL_SYS` para excluirlo.
     El dúo lo tumbó 2×: (v1) introdujo un FP en hp001 — mi adjudicación "feature/bug-de-producto" fue FALSA
     (regla C en `evals/_layer_a_hp001.json`: INSTALADOR≡ADMINISTRADOR es sinónimo, ruta correcta); (v2, tras
     arreglar hp001) el override de Gap-1 tenía un HUECO real **echo-and-deny** (el bot echa los dígitos al negar
     → `_anchor_present` léxico ve el valor → present=True → PASS; reproducido en código). **Pushback de Alberto
     ("si el dúo la tumba, ¿por qué mantenerla?") → REVERTIR la cláusula entera**: era scope creep (re-scope de
     correctitud, NO un denoiser) y mayoría+flag resuelve hp010/hp020 igual. `_FACTUAL_SYS` queda **idéntico a
     pre-s42**. Mis 2 errores eran de FRAMING/over-claim (`feedback_my_bias`) — el dúo los cazó antes de `main`.
  5. **Agregación = veredicto por MAYORÍA + flag de review** en todo gold no-unánime (cierra CM1: ningún FALLO
     minoritario se lava en silencio → spot-check humano, patrón DEC-012). El ruido en el filo es spurious-positivo
     (modal=0) y el bulto es mayoría-robusto → mayoría no lava nada real; la "unión a-priori" del 1er dúo quedó
     refutada POR EL DATO (Regla F: la dirección de agregación SÍ se decidió con la estructura del error medida).
  6. **BASELINE LEGIBLE** (`evals/factual_variance_baseline.json`, 22 golds K=12): **7 FALLO estables**
     (hp005/06/08/09/11/13/19) — el "7 FALLO" de s41 CONFIRMADO no-ruido — / 12 PARCIAL (8 estables + 4 review:
     hp001/02/10/20) / 1 PASS / 2 REVISAR. **18/22 estables, 0 error→REVISAR.**
- **#37 denoise = response_format (ruido de formato) + mayoría (ruido de sampling) + flag→spot-check (residual).**
  La cirugía de prompt NO sobrevive (revertida). El veredicto del eje factual NO cambió vs pre-s42.
- **Gaps**: los 4 `REVIEW` necesitan spot-check humano antes de usar su veredicto como ancla de lever; hp010 es un
  6-6 (el más incierto). El `--legacy-sys`/`_LEGACY_FACTUAL_SYS` del harness es código de A/B (tras el revert,
  legacy==actual) — retirar si molesta.
- **Estado**: ✅ #37 cerrado, baseline legible. **Próximo s43**: DEC-013 paso 3 (el lever sobre el bulto), medido
  vs este baseline. Relacionado: DEC-013 (rumbo), DEC-014 (método), DEC-012 (flag/spot-check).

## DEC-016 — s43: SALVAGE no rebuild (fundamento sano) + lever de retrieval MEDIDO y descartado (condicional) → SÍNTESIS es el cuello
- **Fecha**: 3 jun 2026 (sesión 43). **Impacto**: ALTO (descarta overhaul + descarta retrieval-ranking como lever + dirige el siguiente lever a SÍNTESIS). **Disparador**: Alberto cuestionó el ritmo (s35–s42 ≈ afinar el instrumento con ~1 cambio de producto real) y si tenía sentido un overhaul vs seguir parcheando legacy que nunca vio producción real.
- **(a) Diagnóstico de fundamentos (4 agentes paralelos + verificación en código) → SALVAGE, NO rebuild.** `chunks_v2` = LlamaParse multimodal EJECUTADO (966 JSON 23-may, 22.849 chunks, schema Fase-1 completo); contenido ~99% legible, tablas ~96% sanas, flowcharts coherentes (la alucinación "REPLICA ARMA" = 0 ocurrencias, era del corpus VIEJO); defectos ACOTADOS (figuras→tablas-vacías ~3.8%, finos 0.4%) → **fundamento SÓLIDO, no re-ingestar**. Core (`retriever.py`): cruft ~5-8% (constantes de score plano + sort ingenuo); guardas anti-alucinación verificadas+testeadas; `extract_product_models` ya catalog-first (escala a 30+); `rerank_chunks_voyage` ya cableado; `confidence` NO se usa downstream. **Rebuild RECHAZADO**: la atadura real son las GUARDAS verificadas (no el legacy), y un rewrite las arriesga para un bot cuyo contrato#1 es no-alucinar; ~1-2 sem vs 1.5-2 d con upside negativo. Alts descartadas: blank-slate (trampa del rewrite); re-ingesta (ya hecha, corpus sano).
- **(b) Lever de retrieval (reranker cross-encoder Voyage) MEDIDO end-to-end y DESCARTADO — CONDICIONAL.** El funnel (proxy "target-en-top5") prometía +2 (rescata hp005/008); el end-to-end lo DESMINTIÓ: juez-inline = empate-con-churn (−1F/−1✓, 3↑/3↓); árbitro single-pass = **dentro del ruido de #37** (mi baseline LLM ni reproduce s42: hp002 P→F, hp013 F→P sin tocar el reranker). **Dos jueces ruidosos discrepan → el efecto del reranker es indistinguible del ruido, y regresa hp002/hp005/hp013 → NO se shipea.** Shipearlo por el +2 del funnel habría sido "decidir sobre proxy" (anti-patrón DEC-005). **Negativo CONDICIONAL, no "nunca"** (a petición de Alberto, comentario 2): cuello secuencial (Amdahl) — retrieval-ranking es lateral MIENTRAS síntesis domine; **re-test tras aterrizar el lever de síntesis**. Caveat: puede seguir siendo moot (los chunks ya llegan a top-5).
- **(c) HALLAZGO DOMINANTE (robusto): el cuello del bulto es SÍNTESIS/GENERACIÓN, no retrieval.** Incluso con el chunk en top-5 (Voyage), el bot CONTRADICE hechos verificados (hp005/11/02), extrae incompleto (hp008 core 0/4) o sobre-admite (hp006). Confirma DEC-005/006/s39 **a nivel de VEREDICTO** (no solo funnel) y confirma el instinto de Alberto (gap estructural, no micro-retrieval). → **s44 = Track D: lever de SÍNTESIS/GENERACIÓN** (concreto TBD; duro — generación tiene mal historial, p.ej. change-1 revertido DEC-001; exige diseño + dúo + medición **K-mayoría** DEC-015, NO single-pass).
- **(d) A2 (fusión de scores planos de s29, `TECH_DEBT #32`) = tarea de HIGIENE comprometida, NO lever de calidad** (a petición de Alberto, comentario 1). Es cruft recurrente que confunde cada diagnóstico de retrieval; quitarlo = higiene estructural (energía #38) + pizarra limpia para la revisita condicional de (b). PERO es cambio al retriever VIVO → Protocolo 3 + A/B **denoised**, vara = **NO-regresión** (no "mejorar"); riesgo de boosts load-bearing (0.85 de `typed_search`/`diagram_search` surfacea diagrama/wiring — no es limpieza pura). Prioridad < síntesis; comprometida (no diferida vaga).
- **(e) Track C (`TECH_DEBT #38`) EJECUTADO**: 24 ficheros v1 borrados (10 módulos `src/ingestion/` pdfplumber + 3 tests v1 + 11 scripts acoplados); **176 tests verdes**; vivos (`embedder`/`supabase_client`/`run_bot`) intactos; reversible (tabla `chunks` vieja = rollback del SWAP). TIER 3 (~45 one-offs) → archivar (follow-up). Plan verificado por import-graph (sub-agente).
- **(f) Track B (cobertura, breadth)**: drafts de gold para **Spectrex** (detección de LLAMA = dominio NUEVO; cat008/009/010 spec-lookup source-verificados) + hoja de scoping de las 3 conductas (refuse-inference Notifier↔Morley / admit / clarify). **DRAFTS sin upsert** (pendientes co-gen GPT-5.5 + dúo C3 + sign-off humano). Hallazgo: ES≠EN para el 40/40R → anclado solo a ES.
- **Revisión adversarial (Protocolo 3, dual sobre el RUMBO)**: cross-model GPT **9/9** + sub-agente, 0 FP (`adversarial_review_log` 2026-06-03T11:21). **CRÍTICO convergente cazado**: build-before-measure repetía el anti-patrón DEC-005 (elegir lever por RAZONAMIENTO, no por medición) → invertido a measure-first (corrí funnel + A/B). Mi claim-A mal-citaba la diagnosis ("síntesis dominante" cuando DEC-005 dijo "within-doc retrieval"); la medición end-to-end resolvió la duda a favor de SÍNTESIS. `feedback_my_bias` (convergencia cómoda) cazado por 2ª vez en sesión, antes de tocar prod.
- **Nota de método**: el árbitro single-pass es demasiado ruidoso (#37) para un A/B de lever → toda medición de lever futura usa K-mayoría (DEC-015). El "efecto dentro del ruido" ES la señal de "no fiable".
- **Estado**: ✅ rumbo fijado. Instrumentación del reranker (flag en `audit_retrieval_funnel.py` + `test_bot_vs_gold.py`) = tooling de eval, se queda (para la revisita condicional). **Próximo s44: Track D (lever de síntesis).** Relacionado: DEC-005/006 (cuello repartido/síntesis), DEC-015 (baseline + #37), DEC-001 (change-1: historial de levers de generación), `TECH_DEBT #32` (A2) / `#38` (Track C).

- **CORRECCIÓN (misma sesión, dúo sobre el PLAN de s44 — `adversarial_review_log` 2026-06-03T14:16, cross-model GPT 9/9 + sub-agente, 0 FP; CRÍTICO verificado por mí en `evals/dec003_retrieval_funnel_noTgt*.yaml`):** los claims **(b)** y **(c)** de arriba estaban OVER-CLAIMED. El funnel de los 7 FALLO dice **RETRIEVAL = 12 hechos / 4 fuertes ≥ SÍNTESIS = 7 / 3** → el cuello es **MIXTO y RETRIEVAL-PESADO**, NO "síntesis dominante". Ejemplos mal atribuidos: **hp008 es MIXTO** (2 hechos retrieval-fuertes `in_pool15=false` + 2 síntesis), **hp019/hp009 son RETRIEVAL** (within-doc/page-miss), no síntesis. Reescritura: **(c) "síntesis es el cuello" → "síntesis es UN cuello material, no el dominante"**; **(b) "retrieval descartado" → "reranking-de-pool-FIJO lateral; el burial de COMPOSICIÓN del pool (el bucket MAYOR) sigue sin testear end-to-end"** → **A2 REFORZADO** (ataca el bucket mayor, no es mera higiene). **3er over-claim de framing de la sesión** (`feedback_my_bias`), cazado por el proceso — e irónicamente lo OPUESTO de mi miedo declarado (no sobre-corregí hacia Alberto en (B); INFRA-ponderé retrieval en (C)). **VERIFICADO sound por el dúo** (no fue sobre-corrección): A2/burial real (el reranker corre tras `retrieve_chunks(...)[:k]` → ciego a la composición; `telegram_bot.py:447/450`, merge-sort mezcla escalas `retriever.py:1094`); **PR#8 ≠ operador de A2** (`gate.py rrf_fuse` fusionó rows RPC crudos = midió el SWAP de embeddings, NO RRF-vs-flat → "no movió" NO refuta A2); #3 diferible (solo hp017 `mislabel`, ya fixed). **Cambios al plan s44 (adoptados, canónicos en `PLAN` bloque s43 'Próximo'):** (1) reframe síntesis no-dominante; (2) **DIMENSIONAMIENTO BARATO antes de construir la fusión** (re-estampar sims vectoriales reales en los flat-paths → re-correr SOLO el funnel sobre los 7 FALLO, ~1h, separa burial-A2-addressable vs recall-miss) ANTES de comprometer RRF; (3) **DESBUNDLE #2** de A2 (contamina la medición + degrada un vector de no-alucinación a tweak); (4) calibraciones (aísla→dimensiona; null-result NO cierra s29; medición escalonada; declarar guardas-contrato-duro vs heurísticas-sospechosas + sensitivity; #1 latest-wins / #2 flowchart = **safety-debt NOMBRADA**, no "diferida por eval-ciego").

## DEC-017 — s43 (cierre): spot-check humano + gold-fixes (hp002/hp006) → bulto LIMPIO = 8 FALLO confirmados
- **Fecha**: 3 jun 2026 (sesión 43, cierre). **Impacto**: MEDIO (eval-base/ruler = zona de dolor; gobierna la medición de todo lever). **Eval-only.**
- **Qué**: spot-check humano de Alberto sobre los 4 REVIEW (hp001/02/10/20) + hp006 (CONTRA LA FUENTE, regla #15) + source-validation (render) + **review dual Protocolo 3 de los gold-fixes** → 2 FP del árbitro corregidos por **precisión del gold**, sin tocar los ejes de seguridad.
- **hp002** (REVIEW): el `core #5` era INCOMPLETO vs `p122 punto 13` (el reset inicial condicional —si tras limpiar siguen fuera de tolerancia— está documentado; el bot lo decía bien, con la salvaguarda de conducto-limpio). Reformulado (verbatim p122 + 2.2.17) → **PASS confirmado (5/5)**.
- **hp006** (era 1 de los 7 FALLO estables): el `ausente-probado` MEZCLABA "no hay localización paso-a-paso" (genuinamente ausente) + "MFDT170 no menciona 'Tierra'" (= GATILLO del FP del eje no-fab; la inferencia hedgeada del bot "fallo de tierra → avería del sistema" es DEFENDIBLE, no fabricación). Fix final = **SOLO acotar el ausente-probado** a "no localización paso-a-paso en los manuales consultados por el bot (MFDT170/MIDT170/MPDT170/MADT232), EXCL. 50253" → factual LIMPIO + gatillo no-fab removido → **PARCIAL esperado** (recall-miss real; el contenido 'Tierra' documentado no le llegó al bot). *(Confirmación del eje no-fab post-fix ROL a s44 K-mayoría: API GPT-5.5 flaky al cierre.)*
- **2 over-reaches MÍOS en la autoría del fix de hp006, ambos cazados por el proceso**: (i) añadir un hecho `presente` deductivo → rompía el eje FACTUAL (la admisión honesta del bot pasaba a contradicción) — **cazado por el dual (sub-agente corrió el scorer)**; (ii) incluir 50253SP en la lista del ausente → re-disparaba el flag (el bot REDIRIGE a 50253 + no verifiqué su ausencia) — **cazado por el re-run (Rule C)**. Lección: el fix correcto es QUITAR el gatillo, no AÑADIR; y solo afirmar lo verificado, excl. el destino de redirección.
- **BULTO LIMPIO (derivado; los golds no-tocados no cambian)** = **8 FALLO CONFIRMADOS**: `hp001, hp005, hp008, hp009, hp011, hp013, hp019, hp020`. El spot-check **clarificó, NO encogió**: −1 FP (hp006→PARCIAL), +2 confirmados-reales (hp001/hp020, eran REVIEW). Más fiable, ~mismo tamaño. Atribución (de (1a)/(2)): burial-A2 (hp019/hp020 limpios + hp008/05/11/01 marginal/parcial) + síntesis + recall-miss.
- **Learnings escalables (a 30+)**: (a) los hechos del gold capturan el MATIZ COMPLETO de la fuente, no un absoluto; (b) `ausente-probado` quirúrgico, SOLO lo verificado, EXCL. el destino de redirección del bot; (c) un hecho `presente` que el bot NO puede recuperar no debe redactarse de forma que su negación honesta cuente como contradicción; (d) **check pre-upsert en C4**: "¿una respuesta source-correcta u honestamente hedgeada sería penalizada? ¿cada `presente` con ancla literal Y recuperable?"; (e) **"estable ≠ correcto"** (los FP eran estables run-to-run; solo el spot-check humano + correr-el-scorer los caza, no el denoise #37 ni 1 agente). (f) Los ejes de seguridad NO se relajan — se corrige su INPUT.
- **Revisión adversarial**: dual sobre los gold-fixes (`adversarial_review_log` 2026-06-03T22:40, cross-model GPT 7/7 + sub-agente que CORRIÓ el scorer; 0 FP) — cazó el over-reach (i). **Meta-sesión**: 5 over-claims de framing míos, los 5 cazados por el proceso (dúo / re-run / source-validation) → `feedback_my_bias #18`. El corte en zona de dolor es el DUAL + correr el scorer, no 1 agente.
- **Estado**: gold-fixes APLICADOS en `gold_answers_v1.yaml` (YAML válido; hp002 PASS confirmado; hp006 factual limpio + non-fab pendiente). **s44 PASO 1: re-baseline K-mayoría** (confirma hp006 + el bulto de 8) → luego **A2** (reranker Voyage default + fusión calibrada, dimensionado por (1a)/(2)) + **síntesis**. Material en frío: `_s44_spotcheck.md`, `_s44_goldfixes.md`, `scripts/_s44_dimension_burial.py`, `scripts/_s44_hp001_hp020.py`. Relacionado: DEC-016 (+CORRECCIÓN), DEC-015 (#37/baseline), DEC-012 (eje no-fab).

## DEC-018 — s44: el lever del bulto = retrieve-wide (#16), NO A2-build ni síntesis — medido K=3 y shipped
- **Fecha**: 5 jun 2026 (s44). **Impacto**: ALTO (cambia el retriever VIVO + descarta por MEDICIÓN dos levers planeados — borrar-cruft A2 y síntesis Track D). **Disparador**: el bulto de 8 FALLO (DEC-017); el plan s43 era A2-build (fusión de scores) + síntesis.
- **(a) El dúo (Protocolo 3, cross-model GPT + sub-agente, verificado regla C en código) tumbó "A2-first como build":** el dimensionado del burial corría **HyDE-OFF** mientras el default es **ON** (`hyde.py:39`) → gap no reconciliado con el path real; `RETRIEVAL_TOP_K=15` (`config.py:36`) → re-estampar sobre `merged` alcanza ~2/6 hechos (rango vectorial 16-50 ni se trae); per-hecho ≠ per-pregunta. → la atribución retrieval-vs-síntesis de s43 NO era fiable.
- **(b) Reframe (instinto de Alberto) + mecanismo verificado:** el burial es el **CORTE `merged[:15]`** (`retriever.py:1094/1131` — los keyword-stamps planos 0.80-0.85 decapitan los chunks de coseno real), **NO el reranker** (`reranker.py` rankea por CONTENIDO, Claude lee 800 chars/chunk). → el lever es **retrieve-wide** (`TECH_DEBT #16`, `RETRIEVAL_TOP_K` 15→50, RERANK_TOP_K=5 sin cambio), NO construir fusión NI borrar constantes: el pool ancho deja sobrevivir los chunks y el reranker los sube.
- **(c) Medición (A/B K=3 HyDE-off, `test_bot_vs_gold` SCORE_ALL):** FALLO **~6→1 estable** (3 réplicas wide idénticas 1/1/1; base ruidoso 5/6/7), **7 mejoras / 1 regresión**. Único FALLO residual = **hp006** (recall-miss: 'Tierra' no recuperable en corpus — item aparte, no de este lever). Regresión = **hp013** (PASS→PARCIAL: el reranker eligió un 5-de-50 que omitió un detalle de batería; borderline, ambas respuestas no-inventan → completitud, no seguridad). **Los casos que parecían SÍNTESIS (hp019/hp020/hp001) MEJORARON con retrieval** → eran retrieval-CONTEXTO (el chunk en top-5 pero el contexto de soporte no, + ruido), no síntesis pura; el "chunk en top-5 = síntesis" del funnel era demasiado grueso.
- **(d) Dos levers DESCARTADOS por la medición:** **borrar-cruft** (#32 A2-fusión) — retrieve-wide *sortea* el burial sin tocar constantes → DEPRIORIZADO (sigue siendo cruft real pero no bloquea calidad). **Síntesis Track D** — sus casos ancla eran retrieval → no se necesita para el bulto. Frontera siguiente = los **14 PARCIAL** (completitud), re-evaluar ahí.
- **(e) Protocolo 3 sobre el cambio (sub-agente, SÓLIDO + 1 nota):** [MEDIA] el prompt de rerank crece con el pool (N=50→~12K tok; multi-modelo `effective_top_k=100`→~22K tok) → +latencia + ~3-7× coste de la llamada rerank. Smoke 6/6 sano; latencia 15-39s (pipeline multi-etapa rerank-LLM+generate, no específico de 50). **Aceptado** (sin usuarios); mitigaciones documentadas (HyDE-off + cap-rerank-~30 futuro).
- **(f) HyDE — DESBUNDLEADO, NEXT (no en este PR):** medí con HyDE-OFF; el bot despliega HyDE-ON (default). El A/B aisló retrieve (HyDE-off en AMBOS brazos) → atribución limpia. Inmediato: adoptar HyDE-off (default commiteado en `hyde.py` + Alberto limpia override de Railway + confirmación HyDE-on-vs-off@50) — #32:1250 lo midió no-help + non-determinista en s29; ADEMÁS corta latencia.
- **Alternativas descartadas:** A2-build RRF (dúo: alcance ~2/6, path equivocado); borrar-cruft (innecesario — retrieve-wide lo sortea); retrieve=30 (Alberto eligió 50; 30 = follow-up si hp013/latencia molesta).
- **Vindica el instinto de Alberto** (s35-s42: "afinas el instrumento, ~1 cambio de producto real"; "no sobre-ingenieríes, el bot no está en producción, actúa simple"): el lever **más barato — un constante — ganó** sobre 2 sesiones de plan de build.
- **Revisión adversarial**: dúo del RUMBO (`adversarial_review_log` 2026-06-04, GPT + sub-agente → NO-SÓLIDO, forzó el reframe) + sub-agente del CAMBIO (SÓLIDO + nota latencia). Verificado regla C.
- **Estado**: `RETRIEVAL_TOP_K=50` cableado; **176 tests verdes + smoke 6/6**; PR `feat/s44-retrieve-wide` (pendiente merge). Material: `evals/_s44_*` (dimensionado, A/B K=3 r1-r3, anomalías). Pendiente: merge → **HyDE-off (next)** → frontera PARCIAL/completitud. Relacionado: DEC-016 (+CORRECCIÓN, originó el reframe), `TECH_DEBT #16` (este lever) / `#32` (A2-fusión, deprioritizada).

## DEC-019 — s45: GATE — F1 sin lever de calidad limpio; plan corregido = higiene + audit-como-gate + F2
- **Fecha**: 5 jun 2026 (s45). **Impacto**: ALTO (decide el rumbo F1-vs-F2 + descarta por MEDICIÓN 3 levers + corrige el método). **Disparador**: la frontera de los 14 PARCIAL (DEC-018) + la pregunta de Alberto: ¿qué cimiento BP vale la pena AUNQUE el delta sea pequeño?
- **(a) El GATE (source-anchored = el ÁRBITRO vs el proxy):** triage con `audit_retrieval_funnel.py` @ **pool-50** (arreglado de 15) + `--dump` per-caso del contenido REAL del top-5. **F1 NO tiene lever de calidad limpio dominante.** La "síntesis domina" del funnel es **artefacto parcial**: (1) el matcher `_chunk_has` (`all(a in nc)`, SIN frontera-dígito, `:117`) cuenta "99"∈"990"/"1993" (vs `atomic_scorer._anchor_present:82` que SÍ tiene frontera); (2) el bucket SÍNTESIS cuenta hechos-en-top5 **sin comprobar si el bot los omitió** → cuenta como "síntesis" hechos USADOS (los PASS tenían SÍNTESIS alto). Verificado con --dump: de 4 candidatos fuertes, **2 genuinos (hp001 clave 2222 en top-5 omitida; cat001 159+159), 2 NO (hp008=retrieval-miss modelos 551; hp012=artefacto)**. Síntesis-genuina ≈ 2-4 casos dispersos.
- **(b) 3 levers DESCARTADOS por medición esta sesión** (todos pre-supuestos, cazados por el dúo ANTES de cablear): **L1-contexto** (RERANK-MISS marginal); **síntesis/L2** (resucitaba change-2 s30 + Track-D s44 sobre el mismo proxy in-top5=síntesis que DEC-018d ya descartó end-to-end); **foundations-bundle** (ancla FALSA "reranker=ruido" cuando corre `temperature=0` `reranker.py:112` — el ruido es el juez holístico + generación). + recall no convierte (`TECH_DEBT:1246`).
- **(c) Decisión: F1 = SUFICIENTE para la fase pre-técnico** (FALLO peligrosos cerrados por retrieve-wide; residual = correcto-pero-incompleto, ~2-4 síntesis-genuina + retrieval-residual + suelo #35, NO medible-de-fiable con el juez ruidoso). **Adoptar HyDE-OFF** (= path validado s44; determinismo; re-medir on/off@50 segmentado — s29 no transfiere). Cierra DEC-018(f).
- **(d) Plan corregido (barato-primero · audit-como-gate · comportamiento-sólo-si-el-gate-lo-pide):** **F0** higiene sí-o-sí (estampar config eval + frontera-dígito matcher + borrar one-offs + HyDE-off@50 + externalizar `CATEGORY_TERMS:657` + recall@k CI) → **F1 = EL GATE** (audit de los 14 source-anchored, classify-and-stop — decide lever, no ratifica) → **F2** comportamiento SÓLO si el gate lo pide (Voyage reranker/contextual-retrieval = A/B feature-flag midiendo regresión-diagramas) → **F3 = escala** (catálogo modelos YA hecho catalog-first `retriever.py:101`; pendiente real = `CATEGORY_TERMS`→datos + contrato identidad-producto/conflictos ES-EN/OEM + test matriz-dificultad). **Cimiento BP omitido** (sub-agente): contextual-retrieval (Anthropic 2024) + recall@k separado del juez como gate CI.
- **Alternativas descartadas:** lever de generación/síntesis AHORA (change-1/2 + Track-D = 3 fracasos medidos; DEC-001 riesgo + ruido + sin usuarios); foundations-bundle "sí o sí" (casi todo necesita A/B+no-regresión; era ruteo-alrededor del problema de medición); consolidar el eval-sprawl a uno (ortogonal por diseño — recall@k determinista vs juez end-to-end, el desacople de s42).
- **Revisión adversarial:** dúo s45 = **3 cross-model + 4 sub-agente, TODOS NO-SÓLIDA→corregido** (`adversarial_review_log` 2026-06-05). Cazó **6 over-frames míos** = `feedback_my_bias` reincidente (pre-suponer lever antes del gate ×3 + ancla falsa). El proceso (medir + dúo + instinto-Alberto) los frenó ANTES de tocar prod. Validado regla C (matcher-frontera, reranker temp=0, catalog-first, sort-key).
- **Estado**: 0 código de producto cambiado (sólo `audit_retrieval_funnel.py`→pool-50, herramienta de diagnóstico). Branch `eval/s45-gate`. **PRÓXIMO s46:** ejecutar F0+F1 desde rama fresca de `main`; el audit decide F2-lever vs directo F3-escala (prior honesto: F3). Relacionado: DEC-018 (frontera 14 PARCIAL), `TECH_DEBT #16/#32/#37`, DEC-001/005/006 (historial generación), DEC-013/014/015 (ruido juez factual, ya cerrado).

## DEC-020 — s46: F0 higiene SHIPPED + F1 GATE (síntesis muerta, retrieval-clásico no-convierte) → F2 = medir contextual-retrieval
- **Fecha**: 6 jun 2026 (s46). **Impacto**: ALTO (decide el rumbo F2 = medir el único cimiento de retrieval no-probado). **Disparador**: ejecutar F0+F1 de DEC-019.
- **(a) F0 higiene (4/6 hechos, 2 diferidos):** #2 frontera-dígito canónica `anchor_present` en `strict_match` (dúo P3 sub-agente 3/3 reales; centraliza + dedup `atomic_scorer._anchor_present` byte-idéntico; `locate_fact`/recall fuera de scope → `TECH_DEBT #39` frontera-compuesta); #1 config estampada en el output del gate (`{meta,results}`: git_commit/hyde/K/tabla); #4 HyDE-off default (`hyde.py:39`, cierra DEC-018f; toca prod sólo en deploy); #3 borrados 2 one-offs `_s44_*` (−615). **Diferidos por medición/pregunta-cero:** #6 recall@k-gate → `TECH_DEBT #40` (CI offline no corre recall real; trigger=tocar retrieval); #5 CATEGORY_TERMS → F3 (entrelazado con `_CATEGORY_PHRASES`+taxonomía; el contrato ES-EN/OEM ya en F3). 179 tests. Commits f8c448c/53ca839/36465fe/738c6f0/ef20709.
- **(b) F1 GATE source-anchored (matcher arreglado) — SÍNTESIS MUERTA:** cruce automatizado (audit funnel @ pool-50 + `anchor_present` sobre `bot_answer`) = **0 síntesis-genuina FUERTE** (el bot usa todo dato fuerte que ve en top5; solo omite lo que no llega). **El fix F0#2 reclasificó las "2-4 síntesis-genuina" de DEC-019** (cat001 159+159, hp001) como RETRIEVAL/rerank — eran artefacto del substring crudo (99∈990). Confirma DEC-018d/019, ahora limpio.
- **(c) Mi over-frame F2-retrieval CAZADO por el sub-agente (feedback_my_bias reincidente):** leí el cuello-retrieval (cat001/hp002/hp008/hp011) como lever F2 → REFUTADO: 12/16 no-PASS con 0 fuerte-retrieval; hp008=36% del retrieval en UN caso-catálogo (→F3 identidad-producto); cada PARCIAL/FALLO arrastra precisión/razonamiento que el retrieval no convierte (hp011 `ri` mal-descrito=generación; hp002 razonamiento flujo-bajo/alto). Verificado en diagnósticos (regla C).
- **(d) El cross-model GPT-5.5 ROMPIÓ el echo-chamber Claude (yo+sub-agente=ambos Claude):** "recall-no-convierte ≠ descarta TODO retrieval-lever". Verificado `TECH_DEBT:1246` (regla C): top-k/RRF/rerank/dense-only YA medidos-no-convierten, PERO **contextual-retrieval + BM25-léxico-term-exacto = NO medidos** → declarar F3 sin medirlos = racionalización.
- **(e) Decisión (Alberto): F2 = MEDIR contextual-retrieval** (el cimiento BP omitido de DEC-019), no F3-directo ni el experimento-BM25-barato. Eval-driven: A/B en slice de manuales no-PASS, **conversión de veredictos** (no exposición de hechos). Convierte→lever (roll-out F2); no→F3 sólido por medición. **Gaps:** prior negativo (`:1246` generación/filtros bloquean), juez ruidoso (`#35` suelo-medición de pocos casos), filtros-precisión (`:1250` anti-alucinación cross-product), coste (re-embeber slice + eval×16×2).
- **Alternativas descartadas:** F3-directo (cross-model: racionalización sin medir lo no-probado); experimento-BM25-barato (Alberto eligió el cimiento grande); generación/síntesis ahora (muerta, F1 source-anchored).
- **Revisión adversarial:** dúo s46 = sub-agente P3 sobre F0#2 (3/3 reales, NO-SÓLIDA→3 fixes) + sub-agente F1-gate (cazó mi over-frame F2 → F3) + cross-model F1-gate (rompió el consenso Claude → experimento-puente). `adversarial_review_log` 2026-06-06.
- **Estado**: F0 en rama `eval/s46-hygiene-gate` (5 commits + docs de cierre; PR pendiente). 0 código de producto en F1 (el gate = análisis). **PRÓXIMO s47:** diseño detallado (Protocolo 2 + investigar `reingest`/embedder) + build del experimento contextual-retrieval (slice + A/B conversión + dúo ANTES de cablear). Relacionado: DEC-019 (el plan), DEC-018 (retrieve-wide), `TECH_DEBT #39/#40`, `:1246/:1250`.

## DEC-021 — s47: revisión estructural → criterios de EXCELENCIA + base escalable (medir-primero el dual-judge)
- **Fecha**: 6 jun 2026 (s47). **Impacto**: ALTO (DoD/método del ruler + escala). **Disparador**: dudas estructurales de Alberto pre-s47 (tamaño del eval, BP de RAG, patrones de los PARCIAL, orquestación del dúo) → rediseño del rumbo antes de construir el experimento de contextual-retrieval.
- **(a) §A DoD F1 = EXCELENCIA + seguridad, NO solo "no-daño"** (corrige mi over-frame inicial de solo-no-fallo = bot mediocre-seguro). Bar POSITIVO = completitud de hechos `core` **soportados por el corpus** (el scorer ya lo da: `atomic_scorer:285-293` excluye `ausente-probado` → el techo-de-corpus ya se maneja); falta CABLEAR `verify_citations.py` ("bien citados") + agregación a nivel suite + fijar umbral. Validación = §D; el humano (no-experto) spot-chequea SOLO flags (excepción, no gate). **Sin %PASS de CI** (DEC-003/sin-usuarios; un % mediría ruido del juez).
- **(b) §B ship-criterion**: mueve veredictos **O** mejora por **severidad/eje** (peligroso→benigno cuenta) · 2 ejes (completitud↑ sin invención↑, DEC-001) · delta > ruido (regla numérica: fuera del inestable hp001/02/10/20) · no-regresión (diagramas+PASS) · coste/latencia. **Zona gris** (no-daño pero mecanismo mejor): shipea sin delta SÓLO si (estructural/escala O cierra-riesgo) Y sin-complejidad-material Y no-regresión.
- **(c) §C expandir el eval — REABRE DEC-003 "no-N"** (correcto a n=19/diagnóstico; las metas nuevas held-out + señal-por-lever lo justifican; NO es gate de CI). Target DERIVADO del **suelo de held-out** (≥20 fiable) → **~60-100** (dev ~45-70 / held-out ~20-30); da smoke/delta-grande/generalización, **NO señal fina per-slice**. Split **dev/held-out** con **embargo** (held-out nunca tuneado/inspeccionado) vía marcador `split` (distinto de `estado`, que excluye del A/B). Autoría **industrializada** (`CATALOG_PLAN` sintético source-verified). NO miles (training-scale).
- **(d) §D ruido del juez — DECISIÓN: MEDIR-PRIMERO.** Determinista cubre 96% de hechos duros (`anchor_present`, cero ruido). El dual-judge (Claude+GPT) cerraría el residual cualitativo (#37 ~18%) PERO es build nuevo + "acuerdo=verdad" = riesgo de fallo correlacionado + no debe cambiar el juez a mitad del A/B. → **correr los 2 jueces sobre las 22, medir desacuerdo** (bajo→diferir seguro; alto→construir con dato). **Juez único CONGELADO para el 1er A/B.** Build del dual-judge DIFERIDO pendiente de ese dato.
  - **RESULTADO (s47, medir-primero ejecutado — `scripts/judge_disagreement.py` n=1 + `judge_kruns.py` K=5; dúo×2):** **DIFERIR confirmado.** K=5: 17/22 acuerdo estable (6 sí-contradicción = los FALLO reales, 11 no), **5/22 desacuerdo-ESTABLE TODOS Claude-alto/GPT-bajo** (cat007/hp001/hp008/hp010/hp015), **0 catches únicos de GPT** (hp003/hp006 de n=1 eran RUIDO: a K=5 hp003=ambos-bajo, hp006=ambos-alto). Los 5 flags de Claude son **falsos-positivos de contrato** (`:104` omitir/añadir-extra/admitir-incompletitud ≠ contradicción), **2 sobre respuestas PASS** (hp001 'Mapas'=extra; hp015 ya-correcta) → añadir Claude **degradaría respuestas buenas, 0 cobertura nueva**. Eje no-fabricación (hp006/09/13): acuerdo, Claude sin ventaja. → **juez único GPT-5.5 + K-mayoría (DEC-015)**; un Claude con prompt alineado al contrato es opción futura SI GPT muestra hueco (hoy no). **Matiz de contrato destapado** (pendiente, no bloquea): el eje no distingue "no está en los **fragmentos recuperados**" (retrieval-local, honesto) de "**el manual** no lo describe" (manual-global, fabricación). **Meta `feedback_my_bias`:** 3 interpretaciones, las 3 aterrizaron en "diferir" pero 2 por razonamiento sesgado (la última: pivote 'ya son no-PASS' FALSO, hp001/hp015=PASS, cazado por verificación-en-fuente del dúo); destino correcto, atajo roto. Dúo `adversarial_review_log` 2026-06-06 (4 entradas: n=1 + K=5, sub-agente + cross-model).
- **(e) §E identidad-producto (escala) — SHRINK por verificación.** El dúo+regla-C confirmó que ya existe en gran parte: `catalog.py:1` data-driven **reemplaza** `MODEL_PATTERN` (ya solo fail-safe `retriever.py:18`); identidad por chunk derivada **en ingesta** (`metadata.py:345`). Queda estrecho: ecosistema-por-dato + **admit-on-empty** (no inventar al quedarse sin material, canario hp002) + seam ASD=Securiton. Es **F3 traído-adelante consciente** (tesis M&A = 30+) + **apuesta anticipatoria no-eval-driven** (no hay corpus de 30 marcas → sobre principio+canario; timebox, no gold-plate).
- **(f) §F freeze-contract + secuencia**: el A/B congela corpus+índice+embeddings+juez+config vía **run-manifest** persistido (no params impresos; el config-stamp de F0 es parcial). Expandir golds NO toca el índice → paralelo-seguro; el resto serializa. Orden: industrializar-autoría+expandir-eval (+§A wiring +run-manifest) → medir-primero-desacuerdo → **medir contextual-retrieval** (juez congelado) → identidad (serializado). **hp011/extracción DEPRIORITIZADA** (chunks_v2 YA es LlamaParse-multimodal `:1241`; el 7-seg es cola dura, tarea #10).
- **(g) Proceso/dúo formalizado**: revisor adversarial como sub-agente `.claude/agents/adversarial-reviewer.md` (local — `.claude/` gitignored) + briefing editado (catálogo: done-ness/"consolidación", freeze-contract, apuesta-anticipatoria). **PILOTO 4b VALIDADO**: dar al cross-model los ficheros fuente le hizo cazar claims de código (schema/env-knobs) que antes no podía → **adoptado** (diversidad por modelo+lente, no por inanizar inputs).
- **Alternativas descartadas**: %PASS de CI (§A; rigor mal dirigido sin usuarios); construir dual-judge YA (build+calibración-de-Alberto+retrasa) y diferir-ciego (sin medir el gap) → **medir-primero** gana en ambas; miles de golds (training-scale, overkill+coste); re-VLM para hp011 (ya ejecutado).
- **Revisión adversarial**: dúo s47 = sub-agente×2 + cross-model×2 (con fuentes), `adversarial_review_log` 2026-06-06. v1: 8/8 (GPT). v3: 8/8 (GPT) + 4/4 (sub-agente), 0 FP — cazaron 3 over-claims míos "ya-existe/medible" (§A,§D) + 1 inverso (§E gap sobre-dimensionado); regla C corrigió 1 over-statement del sub-agente (§A techo-corpus). `feedback_my_bias` reincidente, cazado ANTES de cablear.
- **Estado**: criterios LOCKED (v4). Rama `eval/s47-criterios-excelencia`. **PRÓXIMO = CONSTRUIR** (run-manifest + expandir eval + medir-primero + contextual-retrieval). Relacionado: DEC-019/020 (plan F0-F3), DEC-003 (no-N reabierto), DEC-012 (ejes seguridad), `CATALOG_PLAN` (autoría).

## DEC-022 — s48: contextual-retrieval YA implementado (premisa F2 corregida) + audit 0/8 léxico + lever context→generator smoke-débil → diferido pre-registrado; trabajo = Track B
- **Fecha**: 6-7 jun 2026 (s48). **Impacto**: ALTO (corrige la premisa de F2 que arrastraban DEC-019/020/021; cierra con datos el diagnóstico de retrieval de F1). **Disparador**: arrancar el "BUILD del lever" de DEC-021 → el reconocimiento del código (barato-primero, ANTES de construir) destapó que el cimiento ya existía.
- **(a) HALLAZGO mayor (verificado código + BD prod): contextual-retrieval (Anthropic sept-2024) YA está implementado y activo.** `chunks_v2` = **22.849/22.849 chunks con blurb `context` poblado** (B7 `contextualize.py`, Haiku+prompt-caching, prompt=el de Anthropic) → embebido `context+content` (`embed.py:55`). La premisa "F2 = medir el cimiento **OMITIDO**" (DEC-020e) era **falsa en el "omitido/construir"**; el **"no-medido" (delta end-to-end) sigue cierto**. PLAN:381 lo listaba "pendiente" → reconciliado.
- **(b) El blurb solo vive en el RETRIEVAL, no en la generación.** `generator.py:411` arma el prompt con solo `content`; el reranker no lee `context` (by-design Anthropic: la cita que ve el técnico queda limpia). Además el retriever solo DEVUELVE `context` en la rama vector (RPC); las ramas keyword/content lo omiten en su SELECT (deuda; el hidratado por id requiere `SUPABASE_SERVICE_KEY`).
- **(c) Audit 8/8 FALLO (DEC-017) — [ANÁLISIS, no dato-auditado] 0 primariamente-léxico.** Cruzando veredicto + `_provenance.corpus_chunks_v2` + modo-de-fallo: hp001/05/13 síntesis, hp009/19 razonamiento (premisa a corregir), hp020 síntesis/ruido-juez, **hp008 = corpus-gap de extracción** (la lista del Apéndice-3 ID3000 NO está en `content` — tabla-imagen), hp011 = displays 7-seg. El léxico/BM25-término-exacto NO está construido en prod (no hay RRF; FTS = `plainto_tsquery` AND-frágil, `migrations/006:292`) PERO el audit muestra que **no es el cuello de ninguno de los 8** (hp008, el candidato, es extracción). → cerrar F2 sin mirar el léxico habría repetido el pecado de s46; lo miré, lo descarté con datos.
- **(d) Lever context→generator (lo destapó el dúo): smoke-DÉBIL.** Flag `GENERATOR_INCLUDE_CONTEXT` (default OFF, blurb marcado "orientativo, no citable" para mitigar fabricación). Smoke con context hidratado completo (hp005/13, síntesis): **A≈B en sustancia, el bot ignora el blurb** (ya sitúa con el header), **0 fabricación**, generador no-determinista (A/B exige K-mayoría). NO concluyente (3 casos single-run). NO cerrado: diferido a A/B pre-registrado + estratificado en Track B-dev (`docs/PREREG_ab_context2gen.md`).
- **(e) Decisión (Alberto, tras dúo): NO cerrar el lever; diferir; Track B = el trabajo de valor.** El dúo (ronda 2) fue SPLIT: sub-agente Claude "cerrar (débil-por-diseño)" vs cross-model GPT-5.5 "no cerrar — el smoke usó casos de content-claro; hay mecanismos plausibles (content-pobre/multi-doc/ES-EN/OEM) donde el blurb podría aportar". Síntesis: ampliar el eval da el test concluyente **por DIVERSIDAD estratificada, no por N bruto**; diferir-con-pre-registro ≠ procrastinación. Proceder: Track B (expandir eval con estratos + split dev/held-out + embargo) → habilita el A/B-lever pre-registrado + da poder a futuros A/B; F3 (escala) de fondo; el **A/B de contextual-retrieval (ablación, el blurb en retrieval) sigue vivo y SEPARADO**.
- **Correcciones de framing (ambos revisores, patrón over-claim reincidente)**: "0 léxico" → [análisis] en estos 8; "contextual activo 100%" → cobertura poblada + entra al embedding, su efecto e2e nunca medido; "síntesis muerta" → no es el cuello dominante.
- **Alternativas descartadas**: cerrar el lever con el smoke (cross-model: 3 casos homogéneos no bastan); A/B completo 22×K ahora (sub-agente: no hay casos diversos en los 22; overkill); F3-directo (repetiría el pecado s46 de descartar lo no-mirado).
- **Revisión adversarial**: dúo s48 = 2 rondas (cross-model GPT-5.5 ×2 + sub-agente Claude ×2). R1 cazó mi over-frame pro-F3 (cerrar sin léxico). R2 SPLIT, el cross-model rompió el echo-chamber (el sub-agente Claude convergió con mi prior y SE DELATÓ: "comparto tu blind spot, corre el cross-model"). 0 FP. `adversarial_review_log` 2026-06-06/07.
- **Estado**: 1 cambio de prod (`generator.py` flag, default OFF → inerte). Rama `eval/s48-contextual-retrieval`. **PRÓXIMO s49 = Track B** (autoría industrializada source-anchored con estratos + `split` dev/held-out + `tags` en `gold_store`, greenfield) → A/B-lever pre-registrado + A/B contextual-retrieval (ablación) + F3. Relacionado: DEC-020 (premisa corregida), DEC-021 §C/§F (eval grande, freeze-contract), DEC-019 (F1 sin lever limpio), `feedback_my_bias #20`.

## DEC-023 — s49: backbone de Track B (esquema `split`+`estrato` + EMBARGO en la puerta) — el dúo cazó un fallo de embargo crítico ANTES de cablear
- **Fecha**: 7 jun 2026 (s49). **Impacto**: MEDIO-en-zona-de-dolor (esquema del ruler; reversible pero gobierna toda la medición de Track B). **Disparador**: arrancar Track B (DEC-022e); Alberto eligió **"backbone + decidir el bulk luego"** (barato-primero, anti-empaquetar).
- **(a) Lo construido (backbone infraestructural, común a camino-corto-A/B y base-completa):** esquema del ruler extendido en `gold_store.py` con dos campos top-level: **`split`** (`dev`/`held-out`, partición del eval, ortogonal a `estado`) + **`estrato`** (LISTA multi-tag de vocabulario CONTROLADO). Validación tiered (split obligatorio en `verificado`; estrato tag-fuera-de-vocab = ERROR). Retrofit de los 22 (todos `split=dev` — ya inspeccionados; 17 con estrato anclado, 5 sin). `tests/test_gold_store.py` NUEVO (16 tests; no existía test del ruler). Suite **195 verde**. 0 cambios de producto (eval-infra). Rama `eval/s49-track-b-backbone`.
- **(b) BITE CRÍTICO del dúo (convergente cross-model + sub-agente, verificado regla C): el EMBARGO debe vivir en la PUERTA, no en un harness.** Mi diseño v1 ponía el embargo solo en `test_bot_vs_gold.py`. Pero el juez del A/B (K-mayoría, PREREG) corre vía `gold_store.verified()`, que usan **4 consumidores** (`atomic_scorer:408`, `judge_kruns:82`, `judge_disagreement:99`, `characterize_factual_variance:83`) sin filtrar split; + la autoría entra `estado=verificado` → un held-out nuevo lo recogería `verified()` → el juez lo puntúa → **embargo roto justo en el camino que mide el lever**. **FIX:** `verified(include_heldout=False)` excluye held-out por defecto (cubre los 4 sin tocarlos; hoy no-op, 0 held-out) + helpers `dev()`/`heldout()` + filtro replicado en `test_bot_vs_gold.py` (lee el YAML directo). Lectores-directos de DIAGNÓSTICO (`audit_retrieval_funnel`/`retrieval_eval`/`validate_s29_burial`) declarados como gap → `TECH_DEBT #42` (no son el camino que DECIDE el lever; migrarlos = over-scope).
- **(c) Otros bites adoptados (todos, 0 rechazados):** §A wiring (`verify_citations`→suite) **DIFERIDO explícitamente** (era "abierto al dúo" = subcontratar el corte que la pregunta-cero ya contesta; mismo argumento que el run-manifest: es DoD-de-medición, no hay lever en el backbone) · `content-pobre` con **def operacional OFFLINE** ("valor core no en el body del `content`"), no "donde el blurb ayudaría" (circular) · vocabulario **1:1 con el PREREG** (no diluir `fragmento-truncado`/`vocabulary-mismatch`) · `split` **obligatorio post-retrofit** ( no `ausente=dev` permanente = exposición silenciosa) · **`control-pass` FUERA** del vocabulario (estado histórico, circularidad temporal → se selecciona en tiempo de A/B) · **no añadir eje-dominio** (over-build confirmado).
- **(d) Rebanada vertical — opción (a) del dúo [declarar el gap] sobre la (b) [autoría dura], declarado:** el dúo ofreció endurecer con localización dura **O** declarar honestamente que la rebanada no la valida. Elegí (a) porque una autoría C4 de localización dura es trabajo de **BULK** (Alberto lo difirió explícitamente; una sesión dio 3 golds en s38-39) y a medias **envenenaría el árbitro** (riesgo FP-gold de s43). La rebanada SÍ validó, end-to-end: el pipeline de re-autoría (`author_atomic_facts:1317` hace `get()`→muta→`upsert`) **preserva** split/estrato; la autoría nueva (`cross_generate` propone, el autor ensambla, `upsert` exige split en verificado = **fail-closed**, el bulk no crea held-out "sin querer"); + el embargo aislado (16 tests). **NO validado (declarado):** el localizador-duro (riesgo del BULK, mitigado allí con dúo C3 + spot-check humano + locate_fact ciego, no eliminado).
- **Alternativas descartadas:** embargo solo en el harness (bite (b): roto en el camino del juez); `estrato` enum-único (pierde cobertura cruzada multi-tag); `estrato` como dict-de-ejes (más estructura de la necesaria); autoría dura ahora (bulk diferido + riesgo de envenenar); run-manifest completo ahora (aparato no-usado, lección s27 — diferido al 1er A/B con el embargo declarado disciplinario hasta entonces).
- **Revisión adversarial (Protocolo 3, zona de dolor → dúo ANTES de cablear):** cross-model GPT-5.5 **6/6 confirmados** + sub-agente Claude **5/5**, **0 FP**, severidad máx = crítico → veredicto **NO-SÓLIDA** (convergente en el embargo). `adversarial_review_log` 2026-06-07 (2 entradas). El control funcionó: el fallo de embargo se cazó y verificó (regla C) ANTES de tocar nada — de haber cableado v1, el held-out habría estado expuesto al juez.
- **`feedback_my_bias`:** el over-frame fue el embargo-en-un-harness (estructural, no de framing) + el §A "abierto al dúo" (subcontratar el corte). Ambos cazados por el dúo ANTES de cablear; el reencuadre de la rebanada (opción a) lo decidí yo, declarado para visibilidad.
- **Estado**: ✅ backbone SHIPPED-a-rama (195 tests, 0 cambios de prod). **PRÓXIMO s49b/s50:** decidir el bulk (camino-corto-A/B vs base-completa DEC-021 §C) con el backbone montado → autoría del bulk con estratos + held-out embargado → A/B-lever pre-registrado + A/B contextual-retrieval. Relacionado: DEC-022 (Track B = trabajo de valor), DEC-021 §C/§F (eval grande, freeze-contract, run-manifest diferido), `PREREG_ab_context2gen`, `TECH_DEBT #42` (lectores-directos), `RULER_DESIGN §8` (taxonomía estratos).

## DEC-024 — s49b: control anti-olvido de procedimientos canónicos (3 capas) + piloto Track B cat008
- **Fecha**: 7 jun 2026 (s49b). **Impacto**: ALTO (proceso que gobierna toda la autoría futura + toca el esquema de `gold_store`). **Disparador**: Alberto cazó **2×** que declaré "procedimiento de autoría seguido" sin completarlo (cat008: v1 solo-guía; v2 sin render±1) + señaló el patrón general (la premisa "contextual-retrieval omitido" no verificada, arrastrada 3 sesiones, DEC-022).
- **(a) Diagnóstico (raíz):** NO es falta de documentación (RULER_DESIGN §2 ya tenía el procedimiento) — es **activación en el punto de uso**: solo `CLAUDE.md` se carga siempre. Los 2 fallos = "no traer al contexto / no verificar lo ya establecido ANTES de actuar". Laguna del Protocolo 1 (no listaba los procedimientos a verificar).
- **(b) Solución — 3 capas:** (1) **`CLAUDE.md` Protocolo 4** = "Registro de procedimientos canónicos (gatillo→acción)" + regla rectora *"antes de declarar 'hecho/verificado', re-lee el checklist canónico y verifícalo punto por punto EN EL MISMO TURNO"*. (2) **`RULER_DESIGN §2` checklist explícito** tildea-ble (8 puntos). (3) **`gold_store` enforcement-puerta**: `upsert` VALIDA antes de escribir (antes solo round-trip → ahora rechaza errores); `verificado` exige `_provenance.metodo`+`verificado_por`. 198 tests.
- **(c) El dúo (Protocolo 3, zona de dolor) cazó NO-SÓLIDA — cross-model 7/7 + sub-agente 6/6, 0 FP, verificado regla C:** (i) **premisa FALSA del dato** — 22/23 golds YA tienen `_provenance.metodo` top-level (miré `localizacion.metodo` anidado, que solo tiene cat008) = **reproduje el sesgo #20 (verificación incompleta) DENTRO del diseño del control anti-sesgo**; (ii) `upsert` no validaba → "puerta" no era puerta; (iii) grandfather-flag heredable por copy-paste = bypass; (iv) enforcement str-libre = documenta≠ejecuta (teatro parcial); (v) over-claims de framing. → **v2 más simple:** sin grandfathering (22/23 ya cumplen + normalizar cat008 → 23/23; el dúo me ahorró el aparato); leer los campos que YA son contrato (no inventar); upsert-valida = puerta real; re-etiquetar honesto.
- **(d) Límite honesto (declarado):** el enforcement verifica que DOCUMENTÉ los pasos, NO que los EJECUTÉ. Es **defensa-en-profundidad** (la raíz "activación" la atacan las capas 1+2); la ejecución la asegura el dúo P3 + el checklist. Convierte olvido-silencioso en omisión-visible o mentira-consciente.
- **(e) Piloto Track B cat008** (M710 / MI-DMMI, estrato diagrama+oem-relabel): autorado por el procedimiento COMPLETO (localización exhaustiva 12 variantes + render±1 + doble-señal cross-model Claude+GPT en guía Y manual oficial Notifier). RFL 47kΩ (cuádruple señal) + 18kΩ serie (M200E-EOL-R18) + opción VdS (M200E-EOL-RD); descartó el falso conflicto "10k" (ruido tabla alemana). **Hallazgo de método:** el dato del diagrama SÍ está en chunks_v2 (LlamaParse multimodal) → "diagrama" ≠ corpus-gap automático; chunks_v2 es nota POST-hoc, jamás criterio (circular — corrección de Alberto).
- **Alternativas descartadas:** campos estructurados por-paso (rompen los 22 + over-eng); grandfather-flag (bypass heredable → innecesario al leer campos existentes); hook settings.json (frágil; autoría vía script no Edit); seguir dependiendo de que Alberto pregunte (lo que se elimina).
- **Revisión adversarial:** dúo s49b = cross-model GPT-5.5 7/7 + sub-agente Claude 6/6, 0 FP, NO-SÓLIDA convergente. `adversarial_review_log` 2026-06-07.
- **`feedback_my_bias` #22:** el doble fallo de verificación-incompleta (cat008 ×2 + la premisa del dato EN el diseño anti-sesgo) = el sesgo más nítido de la saga; el control (Protocolo 4) lo institucionaliza. Antídoto aplicado: re-leer el procedimiento + verificar punto-por-punto ANTES de "hecho".
- **Estado**: ✅ 3 capas cableadas + cat008 upserted (23 golds) + 198 tests, commit `cd28700` (rama `eval/s49b-piloto-antiolvido`). **PENDIENTE**: golds piloto **#2-5** (FAD-905 scouteado, NO upserted — a retomar con conexión estable, por el procedimiento completo) + PR. Relacionado: DEC-023 (esquema/embargo en la puerta), DEC-022 (premisa contextual-retrieval), `CLAUDE.md` Protocolo 4, `RULER_DESIGN §2`.
