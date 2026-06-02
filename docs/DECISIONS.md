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
