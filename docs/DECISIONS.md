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

## DEC-025 — s50: reframe de la taxonomía del ruler (autorar por DIMENSIÓN DE FALLO, no por artefacto del chunking) + guard mínimo + mix #2-5 corregido
- **Fecha**: 7 jun 2026 (s50). **Impacto**: ALTO (gobierna TODA la autoría futura de golds + la taxonomía del eval). **Disparador**: arrancar los golds #2-5 destapó dos errores que cazó **Alberto**: (1) **el vicio** — scoutié `content-pobre` consultando chunks_v2 (= usar la representación del RAG como criterio de SELECCIÓN del ruler → circular, RULER §0/§2.7; reproducción del vicio cat008/s49b); (2) **un duplicado** — mi gold "ASD535 flujo bajo" = **hp002** ya existente (no revisé las preguntas existentes antes de autorar, solo el conteo de estratos).
- **(a) Hallazgo de raíz (Alberto):** `content-pobre`/`fragmento-truncado` están MAL DEFINIDOS como categoría de AUTORÍA — son propiedades del *chunking* (¿el valor está en el `content` del chunk?), invisibles desde la pregunta → obligan a mirar chunks_v2 ANTES de escribir = el vicio horneado en la taxonomía §8. **Empírico:** 2 fallos source-first de fila (Finales-de-línea, VSN-4REL: el valor en el text-layer → NO content-pobre); cat008 era `diagrama` y tampoco content-pobre.
- **(b) Reframe (Alberto + dúo):** autorar por **DIMENSIÓN DE FALLO** (qué intenta pillar al bot, definible desde la FUENTE: síntesis/es-en/conflicto/oem/familia/scan-ocr + las conductas) → cero chunk-peeking. Los artefactos (content-pobre/fragmento/tabla/diagrama) BAJAN a **CAUSA post-hoc** (lo que el ruler DESTAPA al diagnosticar POR QUÉ falló → enruta el lever de extracción; RULER §7:412 YA los trataba así → reconcilia §7↔§8). Discriminador fino (dúo): no es "desde la pregunta" sino **fuente-independiente, NO desde-el-chunk-del-RAG** (admit deriva de localización-en-FUENTE, legítimo).
- **(c) Completitud (Alberto "¿nos dejamos alguno?"):** organizar por fallo SACA A LA LUZ 3 dimensiones que el canon nombra pero la taxonomía-por-formato no tenía slot (verificado por el dúo): **conflicto-revisión** (latest-wins, RULER §1:67), **mezcla-cross-product** (RULER §0:19 literal), **síntesis/completitud intra-manual** (el `multi-doc` viejo = solo ≥2 manuales, §8:447). + candidato term-mismatch intra-idioma.
- **(d) Alcance — contrato + Pregunta cero (Alberto "¿sobre-ingeniería?"):** adoptar el PRINCIPIO = BP/estructural/escalable (raíz del vicio + diagnóstico + agnóstico al fabricante). PERO rediseñar §8+gold_store+PREREG ANTES de escribir un gold = over-engineering (mi patrón de empaquetar rumbo). **Decisión: adoptar principio + guard MÍNIMO ya + DIFERIR la consolidación completa** a gatillo DURO = **antes del 1er A/B-lever** (el A/B lee los estratos → freeze-contract; no "tras 10-15 golds", difuso).
- **(e) Guard mínimo cableado (Tier 1, dúo-aprobado, 198 tests):** `gold_store` split `ESTRATOS_AUTORIA` vs `ESTRATOS_POSTHOC` (content-pobre/fragmento), ESTRATOS=unión (legacy hp008 valida) + `CLAUDE.md` Protocolo 4 (no-duplicado + dimensión-fallo + chunks_v2-jamás-en-SELECCIÓN) + `RULER §2` paso 0. Blast-radius medido (content-pobre 1×, fragmento 0×).
- **(f) Mix #2-5 corregido (sub-decisión, dúo):** mi 1er mix (re-target a conductas no-answer) lo cazó el dúo CONVERGENTE como **over-pivot que mataba el A/B** (deja famélicos los estratos PREREG content-pobre/fragmento/es-en/conflicto). Corregido: **mayoría estratos-A/B + 1 conducta barata (clarify)** (⚠️ tras el reframe (b), los estratos-A/B **AUTORABLES** = es-en/conflicto/síntesis; **content-pobre/fragmento ya NO se autoran — emergen post-hoc**); admit/refuse-inference **DIFERIDOS** hasta definir el **contrato de ausencia** (cross-model B4 + CATALOG_PLAN gap g: ¿qué cuenta como "ausente"? corpus/índice/retrieved/OEM/dominio).
- **Alternativas descartadas:** (a) content-pobre source-first (no funciona — propiedad del chunking, no de la fuente); (b) re-target #2-5 a conductas no-answer (over-pivot, mata el A/B — dúo NO-SÓLIDA); (c) diferir TODO el rediseño (under-engineering, deja el rastrillo — dúo); (d) rediseño formal completo ya (over-engineering — Pregunta cero); (e) guard duro + re-tag hp008 (over para el mínimo; soft split-set basta).
- **Revisión adversarial (Protocolo 3, zona de dolor, 2 dúos):** (1) el MIX → cross-model + sub-agente CONVERGENTES **NO-SÓLIDA** (over-pivot, 0 FP); (2) el ALCANCE → CONVERGENTES **SÓLIDA con 2 fixes** (guard-ya + gatillo-duro; sub-agente F1-F4 + cross-model 8 bites, 0 FP). `adversarial_review_log` 2026-06-07.
- **`feedback_my_bias`:** el vicio (chunks_v2 selección) + el duplicado (no revisar existentes) cazados por **ALBERTO** (los conceptuales/de-cimiento); la oscilación **over-frame→over-correct-to-under-engineer** cazada por el **DÚO convergente**. Patrón nítido s50: Alberto caza los conceptuales; el dúo los de framing/alcance.
- **Estado:** ✅ Tier 1 guards cableados + verificados (198 tests, rama `eval/s50-failure-dim-taxonomy`). **0 golds escritos = la sesión arregló el CIMIENTO de autoría** (más valioso que 4 golds sobre cimiento roto). **PENDIENTE s51:** golds #2-5 por dimensión-de-fallo (guards puestos = camino por defecto); consolidación §8+PREREG+3 dims (gatillo: antes del A/B-lever); contrato de ausencia (admit/refuse). Relacionado: DEC-023/022 (Track B), DEC-021 §A/§C (DoD, eval 60-100), DEC-003 (cobertura de conductas), RULER §0/§1/§7/§8, PREREG, `TECH_DEBT`.

## DEC-026 — s51: bulk Track B (4 golds por dimensión-de-fallo, ruler 23→27) + es-us diferido por límite de corpus
- **Fecha**: 8 jun 2026 (s51). **Impacto**: MEDIO-ALTO (autoría del eval en zona de dolor; los golds entran al árbitro del A/B). **Disparador**: ejecutar el PENDIENTE de s50 (golds #2-5 por dimensión-de-fallo; guards Tier 1 ya puestos).
- **(a) Método**: autoría **SERIAL 1-a-1** (Alberto declinó paralelizar — en zona de dolor el sesgo se replica × agentes y el briefing del sub-agente es el riesgo; precisión>velocidad). Cada gold por el **procedimiento completo `RULER §2`**: localización exhaustiva ES+EN → render píxel + ±1 → **doble-señal TRIPLE** (match-texto + Claude render + GPT en frío `cross_verify_image.py`) → hechos atómicos → `gold_store.upsert` (la puerta valida). Check post-hoc de existencia/dispersión en chunks_v2 = diagnóstico, **NUNCA criterio de selección**.
- **(b) GATE del dúo sobre la SELECCIÓN (antes de autorar)** — el punto donde Alberto cazó dup+vicio en s50. Cross-model GPT-5.5 6/6 + sub-agente Claude 4/4, **0 FP, NO-SÓLIDA→corregida** (regla C verificada en fuente/código): (i) `SDX-751EM`/`SDX-751` NO están en `model_catalog.json` (el clarify ancla candidatos en el catálogo, D6) + solape total #5/hp008 → **cambié la familia del clarify** a 751-ión (CPX-751E vs IDX-751, ambos en catálogo); (ii) #4 (síntesis) **a provisional** hasta verificar que el hecho exige fusión; (iii) mi sub-claim "PDFs US cifrados" era FALSO = sesgo de framing reincidente (`feedback_my_bias`).
- **(c) Los 4 golds** (todos `split=dev`): `cat009` conflicto-revisión (NFS Supra EOL **4K7→6K8 Ω**, v04→v05 EN; latest-wins; rev vieja viva en chunks_v2 ×5 → muerde) · `cat010` es-en (IS-mA1 e2S ATEX, fuente EN-only: 24V dc vía barrera 28V/93mA, Ui=28V/Ii=93mA/Pi=660mW, Ex ia IIC) · `cat011` familia-ambigua/clarify (near-name "751": CPX-751E ión estándar vs IDX-751 óptico seguridad-intrínseca/zona peligrosa; candidatos del catálogo) · `cat012` síntesis-completitud intra-manual (dimensionado batería AM-8200 = (A+B)×1,2; fusiona consumo §3.12/13 + autonomía/fórmula §11 + capacidad §3.4.1, dispersos en chunks distintos).
- **(d) Esquema**: +2 tags a `gold_store.ESTRATOS_AUTORIA` (`conflicto-revision`, `sintesis-completitud`) con def inline = el cambio-de-1-línea **sancionado** por la nota de `gold_store.py` (NO la consolidación §8 diferida — no se reclasifica tabla/diagrama/scan ni se toca ESTRATOS_POSTHOC). Mix DEC-025(f) cumplido: 3 A/B + 1 clarify; estratos reforzados (es-en 1→2; conflicto-rev/síntesis/familia-ambigua 0→1).
- **(e) es-us DIFERIDO (gap declarado, Pregunta cero)**: 2 búsquedas independientes + verificación regla-C → no hay conflicto es-us fresco en el corpus (los únicos US reales, AM2020/AFP-300-400, ya están en hp012/hp006; reusarlos = duplicado encubierto). El corpus es **español-céntrico** → las dimensiones cross-language (es-us, es-en-EN-only) son escasas en las FUENTES. No se fabrica (RULER §0). Diferido hasta que entren manuales US al corpus.
- **Alternativas descartadas**: (a) paralelizar la autoría (declinada — zona de dolor); (b) forzar es-us reusando AM2020/AFP1010 con otro parámetro (= duplicado encubierto de hp012, cazado por el dúo); (c) familia-ambigua sobre 751-con-SDX-751EM (fuera de catálogo), MMX/MM (sin manuales propios) o 851 (sólo SD-851E en catálogo) → todas falladas en sourcing → 751-ión CPX/IDX.
- **Revisión adversarial**: dúo s51 = cross-model 6/6 + sub-agente 4/4, 0 FP, NO-SÓLIDA→corregida; `adversarial_review_log` 2026-06-07 (2 entradas del gate de selección).
- **`feedback_my_bias`**: el procedimiento (localización) + el dúo evitaron **3 golds malos** (WFDEN no-EN-only; SDX-751EM no-catálogo; AM-8200N-usuario sin specs). Patrón operativo nuevo: Alberto señaló 3× que cerraba turnos en "siguiente" sin ejecutar → corregido (terminar EN ejecución, no en plan).
- **Estado**: ✅ 4 golds + 2 tags + **200 tests verdes, 27 golds**, rama `eval/s51-golds` → PR. PENDIENTE: es-us (corpus US); consolidación §8/PREREG/3-dims (gatillo: 1er A/B-lever); contrato de ausencia (admit/refuse); poblar held-out (todos `dev`). Relacionado: DEC-025 (reframe), DEC-023 (esquema/embargo), DEC-021 §C (expandir eval).

## DEC-027 — s52: adquisición de corpus Kidde (paneles Control) vía API del portal Fire Security Products — download+parse hechos, INGESTA diferida
- **Fecha**: 8 jun 2026 (s52). **Impacto**: MEDIO (nuevo fabricante al corpus-pendiente-de-ingesta + método reutilizable para 30+; toca zona de dolor corpus/idiomas, pero **INERTE al eval** hasta la ingesta). **Disparador**: Alberto pidió avanzar la descarga + parse de manuales Kidde en paralelo al RULER (s51).
- **(a) Rumbo (Pregunta cero)**: separar **download+parse (inerte)** de **ingesta a `chunks_v2` (diferida)**. El parse se hace ahora (banco reutilizable + valida el pipeline e2e); la ingesta espera el **gate RULER + Protocolo 3** (un A/B no debe mover el corpus a media medición — freeze-contract). Se hace en paralelo al RULER porque la autoría de golds ancla en la **FUENTE**, no en chunks_v2 (DEC-025) → no se contaminan.
- **(b) Método (reverse-engineered, reproducible en `docs/CORPUS_FIRESECURITYPRODUCTS.md`)**: el portal `firesecurityproducts.com` es SPA Angular sobre **API PIM REST**; OAuth password-grant (client público del bundle) + el gate real **`Origin/Referer`** (400 "No access" sin él, aun con token) + `product_group` (enumerar; `sort=recommended` obligatorio; los `filters=` del navegador rompen 503) + `product_downloads` (3 categorías; ES + fallback-EN). Validado end-to-end (token→lista→PDF a disco). **Activo reutilizable** para otras marcas del portal (Aritech, Ziton, GST) y futuros lotes Kidde.
- **(c) Alcance s52**: 17 SKUs (paneles Kidde "Control", brand `17316`; 3 series NC / 2X-A / 2X-A Táctil) → **31 PDFs / ~696 pp** en `Manuales_Kidde/`; **parse LlamaParse 31/31 OK** (agentic sonnet-4.5 = config del corpus `agent_anthropic-sonnet-45`; ~$42; calidad validada: tablas/diagramas capturados, 190pp/1178 tablas en el manual 2X-A). Manuales **por-serie** → dedup 107 docs gross → **31 únicos** (SHA-256, `inventory.py`).
- **(d) Inventario + tooling**: hoja `Kidde` en `data/Inventario_Manuales.xlsx` (**19 productos / 31 docs**) vía `update_inventario.py` + **sidecar de metadata del PIM** (`Producto`/`Tipo`/`Idioma` exactos, no regex frágil). El script se **generalizó** (el sidecar puede fijar tipo/idioma, no solo `equipo`). **gitignore**: `Manuales_Kidde/` ignorado (PDFs grandes, como los demás `Manuales_*`); el xlsx se **versiona** vía excepción `!data/Inventario_Manuales.xlsx` (precedente `!Guia Tecnica Morley.xlsx`).
- **Alternativas descartadas**: (a) ingestar ya a chunks_v2 (rompe el freeze-contract del A/B; sin usuarios no urge); (b) scrapear el DOM (es SPA, no trae los docs); (c) replicar el filtro del navegador con `filters=` (rompe 503); (d) tipo/idioma por heurística de filename (datasheets→"Otro"; el sidecar del PIM es exacto).
- **Revisión adversarial**: Protocolo 1 aplicado en cada paso (verificar antes de declarar: slug del store `agent_anthropic-sonnet-45`, set a parsear = **33** [cazó 2 Notifier incidentales no-Kidde → chip de follow-up], xlsx gitignored). Sin dúo formal (impacto MEDIO + inerte al eval); el build de un scraper de PRODUCCIÓN sí pasaría Protocolo 3.
- **Estado**: ✅ download + parse + inventario hechos (31/31; suite de tests verde, exit 0). Rama `corpus/kidde-panels`. **DIFERIDO**: ingesta a `chunks_v2` (gate RULER + Protocolo 3). 2 PDFs Notifier (`MADT731`/`MNDT710`) fallan LlamaParse = gap pre-existente (chip de follow-up). Relacionado: DEC-025 (golds source-anchored ⊥ corpus), `docs/CORPUS_FIRESECURITYPRODUCTS.md`, `feedback_approach` (workflow nuevo fabricante).

## DEC-028 — s52: cerrados los huecos n=0 de conductas de SEGURIDAD del ruler (admit/refuse-inference) + smoke-validación + sync del juez del eval
- **Fecha**: 8 jun 2026 (s52). **Impacto**: MEDIO (autoría del ruler = el árbitro; zona de dolor corpus/idiomas/esquema; eval-infra, **producción intacta**). **Disparador**: Alberto preguntó si ampliar el eval con (a) más preguntas del mismo tipo para reforzar señales y (b) preguntas "normales" (specs/procedimientos) para volumen — pidiendo explícitamente NO rubber-stamp.
- **(a) Análisis (Pregunta cero, verificado en fuente)**: el ruler es DIAGNÓSTICO, no gate estadístico (RULER §0) → "volumen para potencia estadística" NO es su objetivo. El eje útil no es "difícil vs normal" sino **DISCRIMINACIÓN**. Distribución medida (27 golds): `answer` 24 · `clarify` 2 · `conflicto` 1 · **`admit` 0 · `refuse-inference` 0** → las DOS conductas de seguridad (lo más alto de Seguridad>Honestidad>Utilidad) sin un solo gold; varios estratos de contenido a n=1.
- **(b) Decisión (Alberto)**: cubrir los **huecos n=0** (admit/refuse), NO volumen de specs normales. 3 golds autorados SERIAL por `RULER §2`, **GATE del dúo sobre la SELECCIÓN** antes de autorar: `cat013` refuse-inference (CAD-150 Detnov ↔ óptico Notifier SDX-751; protocolos distintos —lazo Detnov vs CLIP—, ningún manual avala la compat cross-marca → no inferir compat NI incompat, surfacear por-producto + redirigir, DEC-012) · `cat014` answer (DGD-600 vida útil 10 años presente + MTBF ausente-probado) · `cat015` admit (firmware CAD-150 ausente del corpus; localización exhaustiva multi-doc ES+EN de 3 manuales + tarjeta de lazo, extracción confirmada buena; framing conservador "no en el corpus disponible", no "no existe").
- **(c) El dúo cazó un falso-admit reincidente**: C2b se propuso como `admit` ("MTBF/vida útil DGD-600"); el sub-agente (fuente) + el cross-model (conceptual) probaron que la **vida útil SÍ está documentada** (10 años, mismo datasheet que hp004) → habría sido un `answer` disfrazado de `admit` = patrón de los 4 falsos-admit de s33 + mi sesgo #20/#22 (presuponer ausencia sin localizar). Verificado en fuente (regla C: `565f4b65…json` + render p1). **Alberto decidió mantenerlo como `answer`** (cat014). El cross-model también afiló C1 (en genérico degeneraba a `clarify` → modelo exacto SDX-751) y exigió la localización multi-doc de C2a (admit).
- **(d) Smoke-validación (medir-primero, Alberto eligió)**: smoke dirigido `test_bot_vs_gold` `ONLY_QIDS` sobre chunks_v2, **juez sincronizado a las 5 conductas** (estaba stale: solo conocía answer/ask_clarification/admit_no_info). **2 PASS + 1 PARCIAL**: cat014 (answer) y cat015 (admit) PASS → el bot YA maneja las conductas de seguridad; cat013 (refuse) PARCIAL = SEGURO pero incompleto por **sub-retrieval cross-marca** (solo trajo el manual Detnov, no el Notifier) → **lead de retrieval** logueado, no un fallo de seguridad. **Implicación**: el bot maneja la seguridad → NO urge flood de más golds; medir-primero evitó gastar slots caros. Reforzar a n=2 = opcional/diferible.
- **Alternativas descartadas**: (a) volumen de specs/procedimientos normales (diluye el instrumento diagnóstico; testea conductas que el bot ya pasa; RULER §0); (b) reforzar a n=2 a ciegas antes de medir (el smoke mostró que el bot pasa → no urge); (c) inventar un estrato `admit`/`refuse` (son CONDUCTAS, no estratos — punto conceptual del dúo); (d) DROP de C2b (Alberto lo mantuvo como answer útil).
- **Revisión adversarial**: dúo COMPLETO sobre la selección (sub-agente Claude + cross-model GPT-5.5, `evals/adversarial_review_log.jsonl` ts `2026-06-08T12:43:59`): cross-model 7 findings / 7 confirmados / 0 FP / severidad máx crítico (el falso-admit C2b). Regla C aplicada; regla F: decido yo (mantener C2b como answer = decisión de Alberto).
- **Sync del juez (sub-decisión)**: `test_bot_vs_gold.py` — legend de conductas + enum + criterio sincronizados a las 5 canónicas (RULER §1) + filtros `ONLY_QIDS`/`OUTPUT_OVERRIDE` (smoke dirigido sin pisar el artefacto del run completo). Staleness pre-Track-B; cambio fiel + reversible; el smoke confirmó que ahora clasifica bien la conducta.
- **Estado**: ✅ ruler 27→30 (admit 0→1, refuse-inference 0→1); 200 tests verdes; 0 errores de esquema; smoke 2 PASS/1 PARCIAL. Rama `eval/s52-safety-conducts` (sobre `origin/main` post-PR45/DEC-027). **PENDIENTE**: estratos n=1 (gatillo A/B-lever); contrato de ausencia formal; poblar held-out (todos `dev`); el lead de sub-retrieval cross-marca (cat013) → audit de retrieval. Relacionado: DEC-026 (bulk Track B), DEC-025 (dimensión-de-fallo), DEC-012 (refuse-inference scoring), DEC-023 (embargo held-out).

## DEC-029 — s52: corpus "base instalada TRATEIN" (multi-marca, vía pedidos /my-orders) — download+parse, ingesta DIFERIDA
- **Fecha**: 8 jun 2026 (s52). **Impacto**: MEDIO (corpus-pendiente-de-ingesta multi-marca + método reutilizable; INERTE al eval hasta la ingesta). **Disparador**: Alberto pidió "más elementos de Kidde" → propuso scrapear el área de pedidos del portal (`/my-orders`) y extraer los productos comprados.
- **(a) Reframe (Pregunta cero, declarado)**: los pedidos NO son "Kidde" — son la **base instalada multi-marca de TRATEIN PCI** (el instalador dueño de la cuenta `KIDDE_USER`): Kidde (Excellence KE-*, ModuLaser) + **Aritech** (paneles 2X-A, detección serie 2000, módulos) + **Edwards** (ModuLaser) + genéricos. Es MÁS relevante para el técnico (lo que realmente tiene instalado), pero cambia el encuadre. Alberto eligió "todos los comprados" (vs solo-Kidde).
- **(b) Método (reproducible, `docs/CORPUS_FIRESECURITYPRODUCTS.md §7`)**: misma API PIM, pieza nueva = `orders` (lista de pedidos) → `order_details?order_number=…` → `line_items[]` (sku + **product_id** directo, sin resolver SKU→ID) → dedup → [pipeline probado] `product_downloads` (3 categorías ES+EN-fallback). Verificado end-to-end. Los pedidos se usan SOLO para **identificar productos**; NO se almacena ni commitea dato comercial (precios/PO/contacto).
- **(c) Alcance s52**: 10 pedidos → **41 productos distintos** (0 sin doc) → **76 PDFs** descargados, agrupados por **marca real** (`product_details.product_brand`): `Manuales_Kidde` (devices) / `Manuales_Aritech` / `Manuales_Edwards` / `Manuales_Otros` (genéricos `product_brand=None`). **Parse: 66 ficheros nuevos / 893 pp / ~$50** (el solape 2X-A con s52 ya extraído se salta por SHA; los 2 Notifier MNDT710/MADT731 vuelven a fallar como en s52). Parse lanzado en background; **verificación al cierre, pendiente**.
- **(d) Inventario (4 marcas)**: Kidde 33prod/55docs (panels s52 + devices, sidecar fusionado) · Aritech 13/33 · Edwards 2/3 · Otros 12/16 — vía `update_inventario.py` (+3 entradas `FABRICANTES`) + sidecars del PIM. **Atribución 2X (declarada)**: los 2X-A salen **Aritech** por `product_details` vs **Kidde** en s52 (el portal cross-brandea: Kidde=marca-marketing del filtro, Aritech=OEM); los manuales 2X-A compartidos quedan **cross-listed** en ambas hojas (`inventory.py` lo marca cross-manufacturer; aceptado, NO se reescribe s52).
- **Alternativas descartadas**: (a) solo marca Kidde (deja fuera Aritech/Edwards igualmente instalados); (b) una sola carpeta "base-instalada" (pierde la atribución por fabricante = la herramienta de gaps); (c) reescribir s52 para que 2X sea Aritech (rework de trabajo commiteado por una ambigüedad del portal).
- **Coordinación (operativo)**: árbol git COMPARTIDO con la sesión paralela (eval/DEC-028) → el inventario + commit se hicieron en un **`git worktree` aislado** desde `origin/main` para no mover el HEAD de la otra sesión. Lección: verificar rama/commit ANTES de cualquier op git en árbol compartido (un `git merge` mío abortó solo por asumir main).
- **Estado**: ✅ download (76 PDFs) + inventario (4 marcas) + docs. Parse lanzado (~$50). Rama `corpus/kidde-installed-base`. **DIFERIDO**: ingesta a `chunks_v2` (gate RULER + Protocolo 3). **PENDIENTE**: verificar parse; Detnov CAD-171 (item parkeado, tras este lote). Relacionado: DEC-027 (lote Kidde paneles), `docs/CORPUS_FIRESECURITYPRODUCTS.md §7`.

## DEC-030 — s54: Detnov CAD-171 (serie Vesta) añadido al corpus — download+parse, ingesta DIFERIDA
- **Fecha**: 8 jun 2026 (s54). **Impacto**: MEDIO-BAJO (extiende un fabricante existente con 1 producto; INERTE al eval). **Disparador**: Alberto detectó una central Detnov nueva no identificada (CAD-171, central compacta analógica 2 lazos, serie Vesta) y la parkeó para tras el lote Kidde.
- **(a) Método (otro sitio)**: `detnov.com` es **WordPress estático** → manuales = **links PDF directos** en la página del producto (sin auth/API; el método del portal Carrier NO aplica). 5 PDFs en `Manuales_Detnov/`: datasheet ES+EN, manual instalación (MI-716, ES) + 2 de configuración/software de la serie CAD/Vesta (MC-380, MS-416, ES; linkados desde CAD-171).
- **(b) No-duplicados (criterio de Alberto, verificado en fuente)**: los 5 NO están en el corpus — la hoja Detnov tiene CAD-250 con **instalación (MI-372) + usuario (MU-376)**, NO con configuración/software (MC-380/MS-416 son doc-tipos DISTINTOS) → contenido nuevo. SHA-store de extracción: ninguno presente. Parse **5/5 OK** (~218 pp / ~$12; los 2 Notifier de siempre fallan).
- **(c) Inventario**: Detnov es **legacy** (hoja 4-col, NO en `update_inventario.FABRICANTES`; sus 109 productos sin PDFs en disco) → **APPEND** de las 5 filas a la hoja existente (NO rebuild, que borraría los 109). Total Detnov 109→**110 prod / 119→124 docs**; estado del Resumen afinado (CAD-171 parse OK, ingesta diferida).
- **Alternativas descartadas**: (a) `update_inventario --only Detnov` (rebuild borraría los 109, sin PDFs en disco); (b) saltar los 2 manuales config CAD-250 (resultaron NO-duplicados: config/software ≠ instalación/usuario ya presentes); (c) modernizar Detnov a 6-col (requiere los 109 PDFs fuente, no disponibles).
- **Coordinación**: hecho en `git worktree` aislado off `origin/main` (#47 ya mergeado) — el árbol compartido seguía ocupado por la sesión paralela del eval.
- **Estado**: ✅ download (5 PDFs) + parse 5/5 OK + inventario (append). Rama `corpus/detnov-cad171`. **DIFERIDO**: ingesta a `chunks_v2` (gate RULER + Protocolo 3). Relacionado: DEC-029/DEC-027 (lotes de corpus), `docs/CORPUS_FIRESECURITYPRODUCTS.md` (otros sitios → método propio).

## DEC-031 — s52b: expansión del eval dirigida al A/B (context→generator) — +5 golds + fix de simetría del dúo (round PARCIAL, PR #49)
- **Fecha**: 8 jun 2026 (s52b, continuación de la expansión Track B / DEC-028). **Impacto**: MEDIO (autoría del ruler = árbitro; zona de dolor; eval-infra, **producción intacta**). **Disparador**: Alberto pidió ampliar el eval en 10-15 golds "de forma prácticamente autónoma sin validar cada uno", con ejemplos de **INSPIRE + AM-8200** (productos nuevos de Notifier).
- **(a) Diana (Pregunta cero + PREREG)**: dirigir los golds al primer A/B-lever (context→generator, `PREREG_ab_context2gen.md`) — diversidad estratificada (multi-doc/síntesis) donde el blurb podría ayudar; **content-pobre POST-HOC, NO preseleccionado** (DEC-025). NO volumen ciego (RULER §0 = diagnóstico).
- **(b) Gate del dúo sobre la SELECCIÓN** (sub-agente Claude + cross-model GPT-5.5; `adversarial_review_log.jsonl` ts `2026-06-08T14:08:27`; cross-model 11 findings / 10 conf / 0 FP). Reshape adoptado (regla F): cortada la **triplicación de battery-dimensioning** (cat012+ID3000+AM2020 = mismo template = N bruto, no diversidad — el PREREG pide diversidad); held-out (8)PEARL reformulado (solapaba hp020); (7)AM2020 descartado; tensión content-pobre (no preseleccionable por chunks) → framing honesto.
- **(c) 5 golds (cat016-020)**, SERIAL por `RULER §2`, doble-señal (render + extracción): cat016 CAD-150 multi-doc (alta+prueba) · **cat017 INSPIRE** multi-doc (lazo OPAL + CLSS + licencia CLIP) · **cat018 AM-8200** síntesis (CBE causa-efecto, NO-battery) · cat019 CAD-250 síntesis (maniobra) · cat020 DXc multi-doc (override de mercado España 80/100/108%).
- **(d) Auto-catch del principio del dúo**: DXc se iba a autorar como 3ª síntesis de causa-efecto (tras cat018 CBE + cat019 maniobra) = el mismo over-index que el dúo marcó con battery → lo PIVOTÉ a market-override (dimensión distinta). Lección: aplicar el PRINCIPIO del dúo proactivamente, no solo su recomendación literal.
- **(e) Smoke (chunks_v2, juez sincronizado a las 5 conductas)**: 1 PASS + 3 PARCIAL + 1 FALLO → los golds DISCRIMINAN (sub-retrieval multi-doc + incompletitud síntesis + 1 contradicción del bot en cat018) = exactamente la diana del A/B. Bien formados (answer→answer).
- **(f) Fix del dúo (a petición de Alberto)**: `docs/ADVERSARIAL_REVIEWER.md` — regla de **SIMETRÍA**: pasar las FUENTES (catálogo/golds) al cross-model, no solo la propuesta; el cross-model quedaba en desventaja factual ("no puedo validar existencia desde la propuesta") mientras el sub-agente (con repo) sí. Realización s47 hecha REGLA. + borrados `AGENTS.md` (copia stale de CLAUDE.md para Codex — NO era la def del dúo, que vive en `ADVERSARIAL_REVIEWER.md`+`adversarial_briefing.md`+`.claude/agents`) y `.codex/` (config de la migración a Codex).
- **Sesgo (`feedback_my_bias` #26)**: recaí en #24 (cerré un turno en "Continúo con CAD-250" SIN ejecutar → Alberto empujó "¿cómo vas?"). POSITIVO: auto-caché el over-index de causa-efecto (aplicar el principio del dúo, no su literal).
- **Alternativas descartadas**: volumen de specs normales (diluye, DEC-028); battery ×3 (clon-template); held-out PEARL (dup hp020); DXc causa-efecto (3er clon de patrón).
- **Estado**: ✅ 5 golds (35 total), 200 tests, esquema 0 errores; smoke 1 PASS/3 PARCIAL/1 FALLO. Rama `eval/s52b-batch` (sobre `origin/main` post-s54) → **PR #49** (round cerrado PARCIAL, decisión de Alberto). **PENDIENTE (sesión fresca)**: refuerzos n=1 (scan-ocr/conflicto-revisión/familia-ambigua) + held-out embargado + es-en (corpus-limitado) → hacia 10-15; consolidación §8/PREREG; luego el A/B context→generator. Relacionado: DEC-028, DEC-025, DEC-023, `PREREG_ab_context2gen.md`.

## DEC-032 — s55: Detnov CAD-201 + CAD-201-PLUS (serie Vesta) — download solo-no-duplicados + parse, ingesta DIFERIDA
- **Fecha**: 8 jun 2026 (s55). **Impacto**: BAJO (2 productos a un fabricante existente, fuerte dedup; INERTE al eval). **Disparador**: Alberto pidió 2 centrales Detnov más (CAD-201, CAD-201-PLUS), recordando "parsear solo los documentos que no tengamos".
- **(a) Dedup (criterio verificado en fuente)**: `detnov.com` WordPress directo; **CAD-201 y CAD-201-PLUS linkan los MISMOS 5 PDFs**, y **2 ya los teníamos** (config/software CAD-250 MC-380/MS-416, bajados con CAD-171 DEC-030) → solo **3 nuevos**: datasheet CAD-201 ES (DS-740) + EN (DS-741) + instalación MI-715. CAD-201-PLUS no tiene docs propios (usa los de CAD-201). Verificado: SHA-store NO para los 3; CAD-201 ausente de la hoja Detnov. Parse **3/3 OK** (~62 pp / ~$3); los 2 config se saltan por SHA (ya extraídos).
- **(b) Inventario**: APPEND a la hoja Detnov legacy: CAD-201 (5 docs) + CAD-201-PLUS (5 docs, idénticos) → 110→**112 prod / 124→134 docs**. Los config/software compartidos se listan por-producto (la hoja es gap-hunting per-product; ficheros ÚNICOS al corpus = solo 3, por SHA).
- **Alternativas descartadas**: (a) re-bajar/re-parsear los 2 config CAD-250 (ya en disco + en SHA-store de CAD-171); (b) listar CAD-201-PLUS sin sus docs (perdería findability per-product).
- **Coordinación**: worktree aislado off `origin/main` (**#49**, que la sesión paralela mergeó entremedias — origin/main se movió #48→#49 durante el lote) — árbol compartido ocupado por el eval.
- **Estado**: ✅ download (3 nuevos) + parse 3/3 OK + inventario. Rama `corpus/detnov-cad201`. **DIFERIDO**: ingesta a `chunks_v2`. Relacionado: DEC-030 (CAD-171), DEC-029/027 (lotes corpus).

## DEC-033 — s53 (eval): consolidación §8/PREREG (taxonomía CONGELADA pre-A/B) + batch dirigido (3 golds, localize-first) — round PARCIAL, PR #52
> Nota de numeración: `DEC-032` lo tomó el corpus s55 (CAD-201, mergeado #50) en paralelo a esta sesión → la consolidación del eval = **DEC-033** (los docs/PLAN/ARCHITECTURE/memoria de s53 referencian DEC-033).
- **Fecha**: 8 jun 2026 (s53 eval, continuación de DEC-031). **Impacto**: ALTO (la consolidación congela la taxonomía de estratos que TODOS los A/B futuros leen = freeze-contract; zona de dolor = esquema del ruler; **producción intacta**). **Disparador**: pendiente de DEC-031 (consolidación §8/PREREG = gatillo DURO antes del 1er A/B-lever) + ampliar la muestra. Alberto eligió: **consolidación + audit → A/B**; batch **AMPLIO ~10-12**; y corrigió mi over-drop (reclasificar, no tirar).
- **(a) Consolidación §8/PREREG CABLEADA (el gate duro).** El código (`gold_store`) ya tenía el split AUTORÍA/POSTHOC (s50/51); el DOC §8 estaba "EN REVISIÓN" stale y el PREREG **AUTO-BLOQUEADO** (pre-seleccionaba `content-pobre`, demotado a post-hoc por DEC-025). Reconciliado: §8 código↔doc; PREREG des-bloqueado (hipótesis reformulada — content-pobre = predicción secundaria post-hoc, NO población objetivo) + **PASS-control sub-contrato** (anti-circularidad, bite del dúo) + pre-req técnico del retriever conservado.
- **(b) Decisión taxonómica (catch del dúo): tabla-matriz/scan-ocr/diagrama DEMOTADOS de AUTORÍA → POST-HOC.** Mi D2 lo enmarcó como "el código ya decidió AUTORÍA, solo documento" = FALSO (framing): DEC-025(b) listó tabla/diagrama como artefactos a demotar; DEC-026(d) dijo "no se reclasifica tabla/diagrama/scan" (= DIFERIDO); `RULER §2:156` + `§7:412` enrutan diagrama/OCR/denso al lever de extracción #10 = post-hoc. → completé la reclasificación que DEC-025(b) dejó pendiente. **Discriminador limpio: AUTORÍA = fallo COGNITIVO fuente-puro; POST-HOC = causa de cómo el RAG extrajo.** Demote lockeado en `test_gold_store`. `ESTRATOS_AUTORIA` = 7 cognitivas + `mezcla-cross-product` n=0-pendiente; `POSTHOC` = 5.
- **(c) Audit + recalibración (Alberto).** Mi "0 golds" inicial era FALSO (el dúo: omití los refuerzos n=1 de DEC-031; "topado por corpus" solo aplica a es-en/es-us, NO a conflicto-revisión [mismo idioma] ni familia-ambigua). Alberto recalibró a batch AMPLIO ~10-12 (robustez del instrumento + breadth 30+). **Gate del dúo sobre la SELECCIÓN → NO-SÓLIDA convergente, 0 FP: cazó 2 candidatos ENVENENADOS ANTES de autorar** — #3 AFP-300 (atribución sucia del catálogo, sin manual; bug AC-220 §2:194, verificado: 0 PDF) + #1 VEP (premisa de síntesis FALSA: diseño delegado al software ASPIRE) — + #5 MAD-4xx (no near-name) + breadth EN-only recortado.
- **(d) 3 golds (35→38, todos `dev`), SERIAL por `RULER §2` (localización + render píxel + doble-señal Claude render + GPT cross_verify):** `cat021` familia-ambigua/**clarify** Spectrex SharpEye 40/40 (I/L/U/R/M = tecnología espectral distinta IR3/UV/UV-IR/IR-simple/multi-IR-hidrógeno; **FABRICANTE NUEVO** en el ruler) · `cat022` **answer** Spectrex 40/40L vs L4 (banda IR 2,5-3,0μm vs 4,5μm + sufijo B = BIT) · `cat023` **answer** Securiton ASD532 (clases de sensibilidad EN 54-20 A/B/C + config de flujo W01-W44).
- **(e) Hallazgo honesto (localize-first): la SÍNTESIS GENUINA es CORPUS-ESCASA.** 3 candidatos de síntesis examinados post-gate → **0 genuinos** (VEP delegado a software · AFP-300 envenenado · Spectrex cobertura = spec-table, no fusión-cálculo tipo cat012). → el estrato del A/B (síntesis) queda **topado ~n=3** (limitación a DECLARAR, como es-us en DEC-026e). La muestra crece por breadth/familia/conflicto/answer, NO por síntesis.
- **(f) Corrección de Alberto (anti-over-drop): RECLASIFICAR, no tirar.** Dropeé Spectrex-cobertura y ASD532 enteros al no aguantar la dimensión CLAIMED (síntesis/oem). Alberto: la disciplina es "no CLAIMear una dimensión que no aguanta", NO "tirar el gold" → reclasificados a `answer` (su dimensión real); solo AFP-300 (envenenado) se tiró. = mi sesgo **#23 oscilando over→UNDER** (sobre-corrección), cazado por Alberto.
- **Alternativas descartadas**: mantener tabla/diagrama/scan en AUTORÍA (revierte DEC-025b sin justificación; dúo); "0 golds" (omitía refuerzos factibles; dúo); forzar síntesis ×3 (2 de 3 no genuinos = fabricación, RULER §0); tirar Spectrex/ASD532 (over-drop; Alberto); oem-relabel ASD532 (rebrand no verificado en catálogo = over-claim).
- **Revisión adversarial (Protocolo 3, zona de dolor, 2 dúos completos cross-model + sub-agente)**: (1) consolidación → NO-SÓLIDA→corregida (D2 era reapertura encubierta + audit incompleto), 0 FP, `adversarial_review_log` `2026-06-08T18:02:36`; (2) selección → NO-SÓLIDA convergente (2 envenenados + MAD + breadth), 0 FP, `2026-06-08T18:36:58`. Regla C verificada en fuente.
- **`feedback_my_bias` #27**: el dúo cazó **#20/#22** (over-claim de dimensión sin localizar) en 2 candidatos ANTES de autorar; Alberto cazó la **#23** (over→under: tirar en vez de reclasificar). Patrón: el dúo caza el framing/over-claim; Alberto el cimiento + la oscilación.
- **Estado**: ✅ consolidación shipped + verificada (**200 tests, 0 errores de esquema**, 8 warnings post-hoc legacy esperados); **3 golds (38 total)**. Rama `eval/s53-consolidacion-prereg` → **PR #52** (round PARCIAL, decisión de Alberto: cerrar el gate + 3 golds, seguir el batch fresco). **PENDIENTE**: batch hacia ~10-12 (conflicto-revisión [scout 2 revs] + más breadth ES + oem verificado); síntesis topada ~3 (declarado); held-out embargado; luego el **A/B context→generator** (PREREG ya reconciliado). Relacionado: DEC-031/028/026/025 (Track B), DEC-023 (esquema/embargo), `PREREG_ab_context2gen.md`, `RULER_DESIGN §8`.

## DEC-034 — s54 (eval): memoria consolidada (durable) + 1 gold conflicto-revisión (cat024 MAD-472); el dúo tumbó mi over-claim de breadth; conflicto-revisión = corpus-limitado — PR
- **Fecha**: 8 jun 2026 (s54 eval, continuación de DEC-033). **Impacto**: MEDIO (1 gold + cambio de memoria/proceso; producción intacta; zona de dolor = corpus/ruler). **Disparador**: pendiente de DEC-033 (batch hacia ~10-12). Antes de los golds, Alberto flagueó el bloat de `MEMORY.md`.
- **(a) Consolidación de memoria (durable, root-cause).** `MEMORY.md` (índice, se carga cada sesión) reventaba el límite 24.4KB (28.8KB) porque el cierre apilaba el log de cada sesión (s44→s52b) DENTRO de la línea del índice — violando "índice = 1 línea/memoria, nunca contenido". Colapsado a one-liners (28.8→**2.6KB**); detalle migrado a los topic files (trampa cazada al leer-antes-de-borrar: s52/s52b + lecciones #26/#27 vivían SOLO en el índice → migrados, 0 pérdida; la traza canónica completa está en DECISIONS/PLAN). **Fix de raíz: guard en `CLAUDE.md` cierre** (detalle → topic file + DECISIONS; índice = 1 línea estable, nunca apilar el resultado de la sesión) → no recurre.
- **(b) Selección source-first + gate del dúo (Protocolo 3, zona de dolor).** 2 candidatos: **MAD-472** (sirena Detnov, conflicto-revisión) + **LDA BA Series** (breadth-ES). Gate dúo (sub-agente + cross-model con fuentes, regla de simetría) → **CONVERGENTE, 0 FP**: MAD-472 SÓLIDO (verificó en chunks_v2 que ambas revs coexisten = gap vivo); **LDA NO-SÓLIDA** = lookup de viñeta limpia sin modo de fallo (patrón s52 "diluir donde el bot es fuerte") + split held-out invertido (debe espejar dev) + mi framing "breadth=robustez-fabricante" = racionalización para colar un gold débil.
- **(c) MAD-472 conflicto-revisión, CUÁDRUPLE-verificado (cat024).** Consumo en alarma `<15 mA` (V1) → `17 mA` (V2), mismo doc `55347200` mismo idioma (ES+EN), ÚNICO valor cambiado (resto idéntico). Verificado: fitz-text (ambos PDFs) + chunks_v2 SQL (4 chunks, ambas revs presentes sin metadata de revisión = gap vivo) + render píxel 400dpi (tabla ES) + digital-native. conducta=`answer` (latest-wins 17 mA; NO answer-con-conflicto = eso es mercado ES-vs-US). Autorado vía `gold_store.upsert` (0 errores, 200 tests). **Smoke chunks_v2 = PASS**: el bot trae ambas revs, da 17 mA latest + surfacea la discrepancia → **no cazó bug** (el bot maneja conflicto-revisión); dato diagnóstico legítimo + **PASS-control** para el A/B; reforzó conflicto-revisión **n=1→2** (cat009+cat024).
- **(d) LDA RETIRADO (regla F, mi acuerdo con el dúo) + rechazo de su vice-remediation.** Doy la razón al dúo: el LDA-lookup no es diagnóstico (RULER §0 = el ruler caza FALLOS, no cobertura). PERO **rechacé la remediación del sub-agente** ("reformula LDA a `tabla-matriz`, su tabla está mangled por LlamaParse") = el VICIO chunks_v2-peeking (s50/DEC-025: solo sabes que está mangled mirando la extracción = post-hoc, no dimensión de fuente). El sub-agente Claude compartió mi punto ciego; lo cacé yo.
- **(e) Pregunta de Alberto sobre el protocolo (respondida + afirmada).** SELECCIÓN + autoría = desde la FUENTE (PDFs/render); chunks_v2 SOLO para **existencia** (§2.1 — lo que descartó Kidde) + **verificación regla C**, NUNCA criterio de selección. Boundary honesto declarado: el check "ambas revs en chunks_v2" (gap-vivo) = existencia-del-conflicto (la dimensión, como cat009 "rev vieja viva ×5"), no calidad-de-extracción (el vicio).
- **(f) Instinto de Alberto (más conflictos Detnov) → conflicto-revisión es CORPUS-LIMITADO.** Scout source-first de doc-codes Detnov: **MAD-472 es el ÚNICO par limpio** (PAD-10/10A = rename sin value-diff; Zócalo/FAD-905 `_V2` sin hermano de base en el corpus) → conflicto-revisión = 2 golds totales (cat009+cat024), confirmado DESDE LA FUENTE (no por no mirar). El corpus guardó mayormente la última revisión.
- **(g) Convergencia estratégica: breadth Y más-conflictos → MISMO lever = enriquecer el corpus.** Breadth-vía-lookup-limpio es débil diagnósticamente (el bite del dúo sobre LDA) + más conflictos requieren más revisiones en el corpus → ambos apuntan a la **ingesta de Kidde/Aritech a chunks_v2** (el cuello real de breadth, no el conteo de golds; alinea con la pregunta de Alberto sobre Kidde). Lever separado (Protocolo 2). Autorar golds Kidde pre-ingesta = admit/GAP-roto (RULER §1) + stale al ingestar → descartado.
- **Alternativas descartadas**: autorar LDA como breadth-answer (lookup sin modo de fallo = dilución RULER §0/s52; dúo); reformular LDA a tabla-matriz (chunks_v2-peeking = vicio s50; yo); forzar un 2º gold para cuadrar número (sesgo output-visible; s52 "medir evitó autorar de más"); golds Kidde pre-ingesta (admit/GAP-roto + stale).
- **Revisión adversarial (Protocolo 3, zona de dolor)**: gate de selección, sub-agente Claude + cross-model GPT-5.5 (con fuentes, regla de simetría), **CONVERGENTE 0 FP**, `adversarial_review_log` `2026-06-08T21:22:14`. Regla C verificada en chunks_v2 (query directa de los 4 chunks) + render píxel.
- **`feedback_my_bias` #28**: el dúo CONVERGENTE cazó mi over-claim de framing (#27 reincidente: empaquetar un gold débil con un framing "breadth/robustez" plausible + split invertido); yo cacé la vice-remediation del sub-agente (donde el Claude-sub-agente compartió mi punto ciego conceptual). Positivo: source-first + cuádruple-verificación + el protocolo chunks_v2 (existencia, no selección) se sostuvieron; **cat024-PASS reportado honestamente** (no cazó bug — venció al sesgo output-visible).
- **Estado**: ✅ memoria consolidada (durable) + **cat024 (39 golds), 0 errores de esquema, 200 tests, smoke PASS**. Rama `eval/s54-golds-batch` → **PR**. **PENDIENTE**: lever de **ingesta Kidde/Aritech** (breadth 30+, con Protocolo 2 — el cuello real); held-out embargado; luego el **A/B context→generator**. Relacionado: DEC-033/031/028/026/025 (Track B), DEC-027/029/030/032 (corpus Kidde/Detnov, pendientes de ingesta), `PREREG_ab_context2gen.md`, `RULER_DESIGN §8`, `feedback_my_bias.md`.

## DEC-035 — s55: identidad de producto DATA-DRIVEN (Capa A+B del seam Fase 2) — habilita la ingesta sin envenenar el corpus; ingesta DIFERIDA al merge (PR #54)

- **Gatillo (el lever de ingesta arrancó con un guardarraíl)**: dry-run de atribución B5 sobre los 103 docs nuevos **sin gastar API** → cazó que ingestar tal cual **ENVENENA el corpus**: `manufacturer=None` 95/103 + `product_model` basura (`HASTA-256`="hasta 256 zonas", `REV-005`=revisión, `EN-54-20`=norma, `RAL-9016`=color). Es hp017/AC-220 ×95. Causa raíz (verificada en código, Protocolo 4): `metadata.py` marca sus tablas **"SEAM DE FASE 2"**; Kidde/Aritech/Edwards no existen en ellas.
- **Alberto cuestionó mi v0** ("leer el sidecar de un portal" = parche/mosaico): hacerlo **estructural + escalable a 30+** + tener en cuenta **multi-modelo** (un manual de serie cubre N skus). Reframe a diseño de subsistema.
- **Dúo R1 (diseño) tumbó mi Capa C (esquema `product_models[]`)**: reabría **TECH_DEBT #18** (array diferido, trigger NO disparado); el problema multi-modelo es **#43** (manuales de serie invisibles a hermanos), con fix más barato (`series`/`applies_to`) **eval-driven**. **Capa C DIFERIDA.** El cross-model rompió mi echo-chamber: `brand→manufacturer` ciego habría roto la distinción OEM (2X-A = Aritech, no Kidde-marketing — DEC-029).
- **Construido (A+B, escalable sin código por-fabricante)**:
  - **Capa A** — tablas de identidad → `config/manufacturers/*.yaml` + `manufacturer_registry.py` (orden semántico `eval_order`). Equivalencia **estructural** (registry ≡ tablas) + **comportamiento** (1068 docs, **0 diffs**).
  - **Capa B** — `sidecar.py` lee `Manuales_<canal>/_metadata.json`: `equipo`→`product_model` real; manufacturer = patrón-filename OEM-aware (Pfannenberg `DS-*` en "Otros" gana) o canal + **OEM override** (`2X-`→Aritech, distr Kidde; verificado por cross-listing del inventario, 12 PDFs en hojas Kidde+Aritech). Restringido a canales del portal → corpus viejo intacto.
  - Resultado 103: Aritech 43/Kidde 33/None 16 (genéricos "Otros")/Pfannenberg 4/Edwards 3; `2X-A`→Aritech/distr Kidde; **0 basura**; 965 viejos **0 regresiones**.
- **Dúo R2 (implementación, 0 FP)**: path abs/rel robusto + validación config (`equipo_prefix` vacío, unicidad de prefijos) + alarma de fallo-abierto + golden de comportamiento como test. **Tally s55: 4 revisiones / ~24 confirmados / 0 FP** (anti-ritual sano; el dúo + Alberto cazaron mi fast-convergence ~4× en este tema — `feedback_my_bias`).
- **Alternativas descartadas**: parche sidecar-solo (mosaico, no escala a fabricantes sin portal); YAML sin sidecar (desperdicia la provenance del PIM); esquema array multi-modelo ahora (#18 diferido, over-eng pre-trigger); `brand→manufacturer` ciego (rompe OEM); repoblar el corpus viejo (innecesario, aditivo).
- **Gaps declarados**: la ingesta requiere **re-build del catálogo** (`build_model_catalog.py`) o los modelos nuevos no son detectables en query; misatribución pre-existente datasheets Detnov `CAD-201-DS-741`→Pfannenberg (no introducida por A/B); `retriever.py:1644` `limit:200` no listaría las marcas nuevas → **chip de tarea**; `product_model` con espacios/acentos ("2X-A Táctil") lo maneja el catálogo (precedente "INSPIRE E10").
- **Estado**: ✅ **PR #54 MERGEADO** (commit `8866877`; el CI `Dependency gate` falló 1ª vez por PyYAML no-declarado en requirements → fix `a37c5de`, lección Protocolo 1: el path real de un PR es el CI, no solo pytest local). **Ingesta EJECUTADA** (s55, tras el merge): 103 docs → `chunks_v2` **22.849→25.090** (+2.241 chunks). Marcas nuevas con identidad correcta en prod: **Aritech 43 docs/895 chunks, Kidde 33/676, Edwards 3/156**; `2X-A`→Aritech (OEM); **0 basura**; 6 docs PT descartados por política de idioma (`empty_after_language`, correcto). **Catálogo re-construido** (536→**587 modelos**; `2X-A`→Aritech incl. sku `2X-AT-F2`). **Smoke de retrieval OK** (Protocolo 1, path real): query "central 2X-A" → 26 chunks TODOS Aritech del manual de instalación real; "FHSD8310" → Edwards. El proceso de ingesta murió 3× por **suspensión tapa/batería** (idempotente + reanudable por `state.json`, 0 pérdida/duplicado; keep-awake `ES_SYSTEM_REQUIRED` no cubre tapa). Rama `corpus/s55-ingest` → PR. **PENDIENTE**: held-out embargado + **A/B context→generator**. Relacionado: DEC-034 (gatillo), DEC-027/029/030/032 (corpus descargado), TECH_DEBT #18 (array diferido)/#43 (series eval-driven), `adversarial_review_log` 2026-06-09, `CORPUS_FIRESECURITYPRODUCTS.md`.

## DEC-036 — s56: revisión estructural end-to-end (cambio de modelo del asistente a Fable 5) — rumbo CONFIRMADO sin overhaul; §H ejecutado (PLAN→HISTORY); gate de atribución ANTES del factor modelo; reviewer pin `model: fable`; corpus pospuesto

- **Gatillo**: Alberto pidió, al estrenar Fable 5 como modelo del asistente, una revisión crítica end-to-end contra el contrato (BP + raíz + escala 30+): ¿cambiar plan/arquitectura?, ¿cambiar LLM del bot u overhaul?, ¿reviewer a Fable + mejor interacción?, ¿limpieza docs/código?, + revisar pasos inmediatos + asks de autonomía + medidas de coste de tokens. **Impacto**: ALTO (rumbo + docs canónicos + diseño del reviewer). **Proceso**: reconocimiento por 3 sub-agentes (pipeline real / eval-infra / docs) → propuesta condensada (`evals/_s56_structural_review_proposal.md`) → **dúo completo ANTES de presentar** (sub-agente 10/10 confirmados + cross-model GPT-5.5 8/8, 0 FP formales; `adversarial_review_log` 2026-06-10T09:30) → 4 firmas de Alberto.
- **(a) Rumbo/arquitectura: NO overhaul.** Stack verificado = **alineado con BP 2026** (hybrid Voyage-4-large+keyword+intent; contextual-retrieval 100% — re-verificado post-s55: 25.090/25.090 con `context`; wide-50→rerank-5; identidad data-driven; eval juez cross-model + K-mayoría + embargo). Re-litigar el rebuild sin señal nueva = rigor mal dirigido (DEC-016 sigue). F3 agentic-RAG sigue gated. Gap declarado: multi-dominio M&A (rociadores/CCTV/accesos) no está en el plan — refuerza F3, no cambia el orden. *(Corrección del cross-model: "alineado con BP", no "ya es BP" — la cobertura del contrato se está midiendo, no demostrada.)*
- **(b) LLM del bot: NO cambiar por fiat — el dúo TUMBÓ mi v1 ("residual=generación → A/B modelo ya") como bias #20 reincidente.** Evidencia: DEC-019c describe el residual como MIXTO y no-medible-de-fiable; leads de sub-retrieval multi-doc abiertos (DEC-028/031); **toda atribución predata la ingesta s55 y NO existe baseline de los 39** (último artefacto full = smoke 1 gold s54). **Firmado: GATE primero (s58)** = baseline K=5 de los 39 dev (= el PASS-control que el PREREG exige) + audit per-caso context-sufficiency + instrumentar `stop_reason` (no se captura; `generator.py:484`) → clasificar {generación / sub-retrieval multi-doc / suelo-juez} y PARAR. **Si generación → A/B 2×2 pre-registrado** {Sonnet 4.6, Opus 4.8}×{blurb OFF,ON}: endpoint primario GLOBAL 2 ejes (estratos solo direccionales — TODOS n≤4, bite del sub-agente), run-manifest DEC-021 §F completo, Batches −50%, ship/rollback escrito antes de medir (extender PREREG). Brazo Opus pierde temp=0 (Opus 4.7+ rechaza sampling params) — absorbido por K-mayoría. Si sub-retrieval → lever de retrieval; Opus no se toca.
- **(c) Reviewer: pin `model: fable`** (frontmatter; antes sin `model:`). Razón: el valor del sub-agente = lectura de código anclada; la diversidad la da el cross-model. **Declarado como HIPÓTESIS con seguimiento** (el tally captura `model` → confirmed-rate per-model; bite del cross-model: "más capacidad = más bite" no está medido). Consecuencia: **cross-model INNEGOCIABLE en ALTO/zona-de-dolor** (autor+sub-agente mismo modelo = echo-chamber total). **Ronda nueva = agente FRESCO** (reutilizar ancla las conclusiones de la ronda 1 — el re-read es feature); SendMessage solo intra-ronda. Riesgos declarados: ~2× coste/review; el pin congela capacidad al próximo salto de harness (revisar entonces). Smoke del pin pendiente de la 1ª invocación real.
- **(d) Docs (§H de s47, EJECUTADO — la medida de coste de tokens RAÍZ, ~80-100K tokens/arranque):** PLAN 123KB→~6KB (estado actual + qué sigue + mapa canónico); historial ÍNTEGRO → **`docs/HISTORY.md`** (log s30→s55 + rationale mayo-2026 con numeración original — las citas "PLAN §9.14"/"§660" resuelven allí + changelog; append-only: el cierre de sesión apendiza el RESULTADO ahí, regla nueva en CLAUDE.md). ARCHITECTURE: banner-log (169 líneas duplicadas) → puntero compacto (81→60KB). TECH_DEBT: índice de estado generado arriba + ✅ verificados #16 (s44) y #38 (s43); SIN renumerar (refs = traza); anotado el doble "## 18". evals/: 64 logs de sesiones cerradas → `evals/archive/` (git mv + README-redirección; EXCLUIDOS los I/O de scripts vivos: `_s45_results_k50_hydeOFF.yaml` input de `audit_retrieval_funnel.py:64`, `_s47_judge_*.json` outputs). Borrados: `src/rag/validator.py` + `tests/test_validator.py` (muertos desde s13, #11i; git conserva) + logs sueltos de raíz. `dedup.py` NO se borra (VIVO en `pipeline.py:48` — el dúo cazó mi candidato no verificado).
- **(e) Corpus: POSPUESTO (decisión de Alberto)** hasta cerrar el ciclo A/B + confirmación held-out. Constraint de freeze: ninguna ingesta dentro de la ventana baseline→A/B→held-out (cláusula DEC-027). Aclaración verificada en BD: los Detnov CAD-171/201 SÍ entraron en la ingesta s55 (el doc-trace de DEC-035 solo nombraba Kidde/Aritech/Edwards; sub-claim stale del sub-agente corregido).
- **(f) Autonomía + coste de sesiones:** asks formalizados (mandato por sesión + lista de decisiones RESERVADAS [prod/Railway, gasto>techo, borrar datos, contratos del eval] vs delegadas-con-traza; techo de gasto API por sesión; firmas asíncronas en bloque). Medidas de tokens: docs compactos (raíz) + exploración vía sub-agentes + sesiones mono-workstream + para el eval: Batches −50% y caching del system prompt en runs burst (el revert s19 fue por tráfico esporádico de prod, no aplica a bursts). Prompt caching en PROD: diferido con umbral declarado (≥50 q/día con técnicos).
- **Alternativas descartadas**: overhaul radical (DEC-016, sin señal nueva); Fable 5 como generador del bot (2× precio de Opus sin hipótesis de mecanismo; solo si Opus no mueve); A/B de modelo SIN gate (mi v1 — atribución stale, riesgo de medir el lever equivocado); sub-agente en Opus 4.8 "por diversidad intra-Claude" (débil; la diversidad real la da GPT); renumerar TECH_DEBT (rompe refs); A/B context→generator EN SOLITARIO (si el gate señala generación, el 2×2 lo absorbe con el mismo freeze).
- **`feedback_my_bias` #29**: reincidí en #20 (pre-suponer "residual=generación" citando DECs que no lo dicen) — cazado por el DÚO antes de presentar (primera vez que el protocolo completo corre ANTES de la propuesta al humano); + 3 verificaciones incompletas cazadas (dedup.py "muerto", ref #33 vs #11i, tally citado sin computar — real: 98.5% confirmados / 1.1% FP en 75 reviews). El proceso funcionó: 18/18 hallazgos confirmados, 0 FP formales, 1 sub-claim del sub-agente corregido por mí contra la BD (Detnov).
- **Estado**: ✅ firmado por Alberto (4/4: docs YA, gate-primero, corpus pospuesto, pin fable) + ejecutado en rama `docs/s56-structural-review` → PR. **PENDIENTE**: s57 held-out embargado → s58 gate de atribución → s59 lever según gate. Relacionado: DEC-016/018/019/021§F/027/033/035, `PREREG_ab_context2gen.md`, `TECH_DEBT #11i/#16/#38/#40/#42/#43`, `evals/_s56_structural_review_proposal.md`, `adversarial_review_log` 2026-06-10.

## DEC-037 — s57: held-out embargado POBLADO (selección gateada por el dúo + primeros 2 golds `ho` + criterio de confirmación PRE-REGISTRADO + cierre TECH_DEBT #42)

- **Fecha**: 10 jun 2026 (s57). **Impacto**: ALTO (puebla el split que confirma cualquier lever; zona de dolor = esquema del ruler/corpus/idiomas; **producción intacta** — eval-infra). **Disparador**: paso 1 del "Qué sigue" del PLAN (DEC-036): el PREREG exige confirmación held-out y estaba a 0.
- **(a) SELECCIÓN gateada (paso 0 RULER §2, patrón DEC-031b):** 11 candidatos efectivos + 2 reservas, qid prefijo **`ho`**, doc `evals/_s57_heldout_selection_proposal.md` **v2** (local, gitignored como `_s56_*`; traza aquí). Fuentes: **lote fresco s55** (Aritech/Kidde/Edwards — ningún gold dev las usa) + **puente Detnov fresco** (CAD-171). Composición: oem-relabel 2 · es-en 2 · multi-doc 3 · síntesis 1-2 · familia-ambigua 1 · conducta-ausencia 1 · refuse 1 (~9 answer / 1 clarify / 1 admit-o-answer / 1 refuse ≈ eco del dev). Reglas operativas nuevas: **preguntas CERRADAS** (el gate no firma placeholders) + **re-gate por gold** si la autoría se desvía + **errata pre-resultado** (corrección anclada en FUENTE, documentada, sin bot) + **freeze-contract citado** en la corrida final + **neutralidad ante #43** (no diseñar golds para pillar/esquivar bugs conocidos de retrieval).
- **(b) Dúo (P3, ALTO en zona de dolor → sub-agente FRESCO pin fable + cross-model GPT-5.5, simetría DEC-031f con fuentes):** v1 = **NO-SÓLIDA** (corregible). Sub-agente **12 findings / 11 conf / 1 FP-parcial** (F4: "CAD-250 0 hits en MI-715" — eran 2; dirección válida); cross-model **6 / 5 conf / 0 FP**. Bites mayores ADOPTADOS: **F1** ho002 clonaba cat023 (EN54-20+flujo de aspirador → re-draft a arquitectura modular del ModuLaser); **F2** los lectores-directos del YAML exponían el held-out JUSTO en las herramientas del gate s58 (fix ejecutado, ver (d)); **F3** ho009 roto contra el catálogo (`2X-AT-F2` = entrada EXACTA → por D6 answer-con-asunción, no clarify → re-draft a near-name "2X-AT", 6 candidatas); **F10/X-conceptual** el "confirmado una vez en held-out" del PREREG no definía QUÉ confirma → **criterio PRE-REGISTRADO** (ver (c)); **X1** selección por conducta re-justificada (no viola DEC-025: el vicio era artefacto-de-chunking; precedente dev 8 golds sin tag; alimentan el eje no-fabricación); **X4** vía de errata. Mi auto-catch: la v1 concentraba 7/13 candidatos en la familia 2X-A → rebalanceo (2X-A ×4, NC ×2, ModuLaser, FD2705R ×2, CAD-171). Tally en `adversarial_review_log` 2026-06-10 (2 entradas).
- **(c) Criterio de confirmación HELD-OUT pre-registrado** (`PREREG_ab_context2gen.md` §nueva, escrito ANTES de conocer ningún delta; agnóstico al lever que el gate s58 señale): corrida ÚNICA `INCLUDE_HELDOUT=1` bajo freeze-contract completo; **CONFIRMA** = Δ global mismo signo que dev Y 0 fabricaciones K-estables nuevas; **NO-CONFIRMA** = signo contrario O ≥1 fabricación; zona gris (Δ≈0) = decisión de Alberto declarada "confirmación DÉBIL"; estratos solo direccionales (n≤3), reportan sin gatear.
- **(d) TECH_DEBT #42 CERRADO (fix de raíz, pre-requisito del primer upsert):** `gold_store.exclude_heldout()` público + filtro en los 3 lectores-directos (`audit_retrieval_funnel` —dump por qid embargado da error explícito—, `retrieval_eval`, `validate_s29_burial`) + test nuevo (`test_exclude_heldout_para_lectores_directos`). El trigger escrito de #42 ("cuando existan golds held-out reales") era literalmente hoy; sin esto, el audit de context-sufficiency de s58 habría corrido retrieval sobre el held-out por default. Suite **217 verde**.
- **(e) AUTORADOS 2/11 (SERIAL, checklist §2 punto-por-punto, SIN correr el bot):**
  - **ho004** (es-en, answer): "¿Cómo se alinea el detector de barrera FD2705R (reflector)?" — procedimiento SOLO en user guide EN pp5-7 (datasheet ES sin procedimiento); render pp4-8 ±1 + co-gen GPT-5.5 (0 desacuerdos) + match determinista **14/14 anchors**; 8 core + 3 supp; cobertura chunks_v2 por SQL (guide 9 chunks, model=FD2705R).
  - **ho003** (es-en, answer): "¿El KE-DP3020W vale para la central 2X-A? La instalación exige EN 54-13" — la localización exhaustiva MATIZÓ el estrato (bien: compatibilidad de serie + firmware≥5.0 SÍ están en ES en el installation sheet p6; lo EN-only: modelo-en-lista, def. asterisco EN 54-13, WARNING lista-cerrada); **no-asterisco del KE-DP3020W verificado al píxel** (p1; asteriscos reales en p4/p5 prueban que el render los distingue) + cross-model dirigido al asterisco (lección 7-seg) + firmware 5.0 como CORE nuevo; 4 core + 2 supp.
  - **Embargo verificado en el mismo turno** (Protocolo 1): `verified()`=39 (los ho invisibles), `heldout()`=[ho004, ho003]; ruler = **41 golds, 0 errores** de esquema.
- **(f) N del held-out — ✅ FIRMADO por Alberto (s57b, 10 jun 2026): 11-AMPLIABLE.** (Recomendación adoptada: no retrasa s58; el criterio (c) hace honesta la lectura a n~11; el embargo no caduca → ampliable post-s59 si el A/B lo exige. Alternativa ≥20 [suelo DEC-021 §C] descartada por coste de oportunidad: +2-3 sesiones antes del gate.)
- **Gaps declarados**: conflicto-revision/conflicto-es-us NO poblables desde el lote fresco (quedan dev-only); perfil held-out ≠ dev (marcas Carrier nuevas; puente Detnov como mitigación parcial, dependencia declarada); sin smoke = golds no-discriminantes se verían en la corrida final; es-en mejor cubierto en held-out (2/11) que en dev (2/39) — asimetría declarada; exposición previa mínima declarada (2 queries de smoke de existencia s55, sin gold).
- **Alternativas descartadas**: fuentes viejas no usadas (contaminación de autor + dup-riesgo DEC-031); volumen ≥20 ya (retrasa el gate s58); clonar plantillas dev (DEC-031; el dúo cazó 2 residuales en v1); poblar mezcla-cross-product (tag inexistente; cat013 cubre por conducta); smoke de discriminación (rompe el embargo).
- **Estado**: ✅ s57 (PR #58 mergeado, `0e7cb90`): 2 golds (ho003/ho004) + fix #42 + PREREG §held-out; 217 tests. **s57b (misma fecha)**: firma de Alberto en (f) = 11-AMPLIABLE + **2 golds más autorados** — **ho001** (oem-relabel: zonas de la 2X-AF2 formulada como KIDDE, corpus=Aritech; 512 zonas/01-9.999/modo Mixta default; render±1 + co-gen GPT 0-desacuerdos + 11/11 anchors + capacidad doble-fuente con datasheet AF2-09) y **ho005** (multi-doc REAL: ampliación con tarjeta 2X-A-LB — sheet ML bloque ES pp7-8 [ranura 2, LOOP3/4, tierra a espárragos de caja, EOL por clase] + manual del panel p98 [alta por menú + 'solo 2X-A-LB']; 11/11 anchors). Ruler = **43 golds (39 dev + 4 held-out)**, 0 errores, embargo verificado (`verified()`=39). Rama `eval/s57b-heldout` → PR. **✅ s57c: los 7 restantes autorados (DEC-038) — held-out COMPLETO 11/11.** Relacionado: DEC-023 (embargo), DEC-025 (dimensión-de-fallo), DEC-031 (gate de selección), DEC-036 (orden s57→s58→s59), `PREREG_ab_context2gen.md`, `TECH_DEBT #42` (cerrado)/#43 (neutralidad).

## DEC-038 — s57c: autoría held-out COMPLETADA (11/11) — 3 resoluciones condicionales según fuente + composición final divergente DECLARADA + gap del eje admit elevado a Alberto

- **Fecha**: 10 jun 2026 (s57c). **Impacto**: MEDIO (cierra la población del split de confirmación; mueve la composición held-out respecto al resumen de DEC-037a; **producción intacta** — eval-infra). **Disparador**: paso 1 del "Qué sigue" del PLAN (DEC-036/DEC-037): quedaban 7 de la selección firmada.
- **(a) AUTORADOS 7/7 (SERIAL, checklist §2 punto-por-punto, SIN correr el bot; doble-señal AND co-gen GPT-5.5 + anchors deterministas + SQL existence en cada uno):**
  - **ho002** (oem-relabel, answer): clúster ModuLaser FHSD8310 — 1 display (mínima/estándar) + 1-8 detectores; no-distribuido ≤4 misma ubicación (cinta J3/J5, la cinta lleva alimentación), distribuido ≤8 (SNET+, máx 1.200 m, PSU/módulo, EOL en J3/J5 libres), híbrido; 7 bits 1-127 → red SenseNET. **Rebrand verificado al píxel**: Edwards 04-4001 p31 ≡ Kidde 3103092 p31; ambos espejos en corpus bajo marcas distintas (140/151 chunks). 19/19 anchors; GPT 20 hechos 0 desacuerdos. FHSD8310 = módulo display estándar (datasheet) — la pregunta firmada no cambió.
  - **ho006** (multi-doc → **sintesis-completitud**, answer): NC rearme (nivel operador pwd 2222; comprobar alarmas/averías; botón rearme) + anular zona (botón "Desconexión" general + zona; LED ámbar fijo; reactivación; caso avería explícito). **Re-etiqueta = rama PRE-FIRMADA de la fila** ("si la localización lo resuelve en UN manual → re-etiqueta honesta"): ambos predicados en el manual de OPERACIÓN (pp25/28/29/33); el de instalación solo trae "Rearme de 24 V auxiliar" (salida AUX, otro concepto). Mini-gate (anti-dup + estrato) ejecutado; 12/12 anchors; GPT 16 hechos 0 desacuerdos.
  - **ho007** (sintesis-completitud, answer): 2X-A modo día/noche (Tabla 22: día=retardo aplicado/noche=inmediato+anula retardo; programa semanal; festivos default noche; Tabla 23 "Deshab retardos Modo Noche") + retardos de sirena (Config de lazo → Config Activación; máx 10 min; Wrn_Ret solo sirenas; habilitar tras configurar; pulsador manual omite). **Bisagra EN la fuente**: p135 → "no procesa los retardos en modo noche" + cross-ref a impresa 59. 19/19 anchors; GPT 57 hechos 0 desacuerdos.
  - **ho008** (multi-doc-o-sintesis → **sintesis-completitud** según fuente, answer): CAD-171 — base 2 lazos (en Power Board)/500 disp (250 por lazo)/2.000 zonas/250 áreas; ampliación 3×TBUD-NG → **"La CAD-171 soporta hasta 8 lazos"** (solo en tabla p15); red T-Network 64 nodos (>512.000 disp = datasheet, supp). El predicado completo vive ÍNTEGRO en MI-716 pero disperso (§2.8-2.9 + §4.4-4.5) → sintesis; rama pre-firmada ("según fuente"). Neutralidad #43 respetada (MC-380/MS-416 de serie barridos y registrados). 14/14 anchors; GPT 15 hechos 0 desacuerdos.
  - **ho009** (familia-ambigua, **clarify**): "2X-AT" ∉ catálogo (587 modelos) → 6 candidatas 2X-AT-F2* verificadas en datasheets: -P = PSU grande, -S = caja pequeña (sin "ampliables a 4" — solo cajas grandes), -FB = controles de bomberos, combinaciones; comunes táctil 7"/2 lazos 500 mA/256 disp/512 zonas. 11/11 anchors; GPT 20 hechos 0 desacuerdos (aporta PSU 10 A del FB-P). Nota: los 6 datasheets en corpus como manufacturer=Aritech (cross-brand del portal) y la pregunta dice "de Kidde" — la conducta medida sigue siendo el clarify.
  - **ho010** (conducta-ausencia → **answer DOCUMENTADO**, rama pre-firmada "si documentado → answer (declarado)"): la red NC entre sí EXISTE y es sustantiva — tarjeta 2010-1-NB (2 puertos punto a punto, p31), anillo clase A recomendado / bus clase B restringido (EN 54-2 no-remotas, p32), nodos 00-32 (00=independiente), "central virtual de 16 zonas compuesta por dos centrales de 8 zonas" (p80). **Prio-2 NO usada**: su trigger firmado era "documentada-TRIVIAL" y esto es una sección entera. Estrato vacío (precedente: 8 golds dev sin tag). 13/13 anchors; GPT 29 hechos; **la doble-señal cazó un error de lectura del autor** (render leído "una central Y un repetidor"; texto+GPT: "O" → verbatim corregido y declarado).
  - **ho011** (refuse-inference): FD2705R exterior/+distancia — refuse anclado en límites POSITIVOS documentados: **Entorno=Interior + IP50** (datasheet ES p2, revelado por el RENDER — el grep no lo mostraba) + 93% non-condensing + "condensation or icing" (guide EN p2) + rango 5-50 m con redirección documentada (50-100 m = detector de 100 m + 4 reflectores). 13/13 anchors; GPT 18 hechos 0 desacuerdos. Anti-dup cat013 (cross-brand ≠ extrapolación ambiental).
- **(b) Dúo (P3 — MEDIO en zona de dolor [esquema del ruler]):** sub-agente FRESCO pin fable sobre las 3 resoluciones condicionales + composición + muestreo de calidad: **4 findings / 2 confirmados / 0 FP** — **F1 [MEDIO, confirmado]** nota anti-dup de ho006 sobre-afirmada ("0 golds" falso: el grep por línea de `question:` no veía el folding YAML; hp011/hp015/cat016 tocan rearme/anulación con predicados/centrales DISTINTOS → no-dup en sustancia) → **nota corregida vía upsert pre-commit** (patrón `feedback_my_bias` cazado por el sistema, no por Alberto); **F2 [MEDIO]** = (c); **F3 [BAJO, aplicado]** fact-de-conducta de ho011 ("derivada de principios", estado:presente, sin precedente de esquema) → movido a notes (facts = hechos-de-fuente, consistencia con cat013); **F4 OK-con-evidencia**: letra de las 3 resoluciones respetada, 10 citas verbatim EXACTAS verificadas en 6 PDFs, embargo vivo, cero artefactos de corrida `ho*`. **Cross-model GPT-5.5**: participó en CADA gold (co-gen, 6 corridas, 0 desacuerdos netos + 2 erratas del autor cazadas: "y→o" ho010, "non-condensing" ho011); la **pregunta estrecha del F2 va etiquetada al cross-model del gate s58** (autor y sub-agente ambos fable — mismo blind spot potencial sobre "el criterio sigue siendo evaluable").
- **(c) COMPOSICIÓN FINAL DECLARADA (divergente del resumen DEC-037a, por ramas pre-firmadas activadas):** oem-relabel 2 (ho001/002) · es-en 2 (ho003/004) · **multi-doc 1** (ho005) · **sintesis-completitud 3** (ho006/007/008) · familia-ambigua 1 (ho009) · sin-tag 2 (ho010/011). Conductas: **9 answer / 1 clarify / 0 admit / 1 refuse**. El resumen de DEC-037a decía "multi-doc 3 · sintesis 1-2"; las filas condicionales firmadas producían exactamente este resultado al resolverse por FUENTE (forzar multi-doc habría sido tunear el estrato contra el canon DEC-025). Per-estrato n≤3 del PREREG respetado.
- **(d) GAP FORMAL — eje no-fabricación held-out sin admit (decisión de Alberto, CON DEADLINE):** la justificación X1 de DEC-037 alimentaba el eje no-fabricación con ho010 (admit) + ho011 (refuse); ho010 resultó answer-documentado → el eje queda con **ho011 solo (refuse, n=1)**. El criterio PREREG sigue siendo formalmente evaluable (las fabricaciones se detectan en CUALQUIER gold vía el eje invención), pero el stressor DIRIGIDO de admit en held-out es 0 y **las reservas firmadas no cubren admit** (ho012 es-en/ho013 clarify). **La opción "11-AMPLIABLE" (DEC-037f) caduca DE FACTO para este ciclo en la corrida única del PREREG**: si se quiere un probe admit held-out, hay que autorarlo (gateado por el dúo) **ANTES de la corrida de confirmación de s59** — después no hay re-tiro. **Decisión para Alberto en el arranque de s58**: (i) autorar 1 admit gateado pre-corrida (≈½ sesión; candidata natural = la prio-2 firmada de ho010 "¿qué software/utilidad de PC configura la 2X-A?" SI la localización prueba ausencia-del-nombre — pasaría mini-gate fresco) vs (ii) declarar el ciclo "refuse-only" y leer el eje admit solo en dev. La pregunta va TAMBIÉN al cross-model del gate s58 (b).
- **Alternativas descartadas**: forzar multi-doc/admit reformulando preguntas para cuadrar el resumen (= tunear el estrato/held-out contra el canon; la fuente manda); usar la prio-2 con la prio-1 documentada-sustantiva (su trigger firmado era solo "documentada-trivial"; usarla = re-formular → re-gate sin necesidad); añadir un 12º gold admit YA sin firma (cambia N sin Alberto — se eleva en (d)); re-gate del dúo por cada re-etiqueta (las ramas estaban pre-firmadas en las filas; el dúo de (b) revisó el agregado).
- **Estado**: ✅ ruler = **50 golds (39 dev + 11 held-out)**, 0 errores; embargo verificado en vivo (`verified()`=39); suite **217**; correcciones F1/F3 aplicadas pre-commit (PR #60 mergeado, `c132e1a`). **(d) RESUELTO EN s57d (misma fecha): Alberto FIRMÓ la opción (i)** — 1 admit gateado pre-corrida. **Ejecutado**: la candidata pre-firmada (prio-2, software config 2X-A) **CAYÓ honestamente en verificación** (el manual EN 2X-A en corpus la NOMBRA: "our Configuration Utility software application" p54 ×5pp → habría sido answer) → candidata NUEVA re-gateada: **ho014** "¿cuál es la referencia del cartucho del filtro de polvo de repuesto del ModuLaser?" — **admit** (subtipo de cat015: identificador concreto ausente; allí firmware, aquí SKU de repuesto). AUSENCIA PROBADA con barrido bilingüe+sinónimos en los 8 docs de la familia + corpus-wide (0 SKU; único doc de repuestos del corpus = DXC-Referencias-repuestos, Morley; los accesorios ModuLaser con SKU [9-30441 APIC] = indicio auxiliar); PRESENCIA servida (20%/80%, Expirac. Filtro MM/AA, procedimiento 5 pasos con detector ENCENDIDO, no-reutilizar, salud). **MINI-GATE del dúo COMPLETO pre-autoría** (cumple el tiering DEC-038b): sub-agente fresco SÓLIDA (3 bites aplicados: anti-dup ampliado con hp002/hp007, redirección como conducta propia, core=ausencia) + **cross-model GPT-5.5** (5 findings aplicados: documentación del barrido bilingüe, hueco spare-parts cerrado por SQL, indicio APIC rebajado, proveedor-local-en-contexto [CONVERGE con el sub-agente], subtipo-de-cat015); co-gen GPT-5.5 en la autoría (26 hechos, 0 desacuerdos + confirmación independiente del no-SKU) + 14/14 anchors + render píxel pp107-108. Ruler = **51 golds (39 dev + 12 held-out)**, 0 errores, embargo vivo, suite 217. El eje no-fabricación held-out queda admit 1 (ho014) + refuse 1 (ho011). **Siguiente (s58)**: gate de atribución PURO (baseline K=5 de los 39 dev + audit context-sufficiency + `stop_reason`). Relacionado: DEC-037 (selección/criterio/N), DEC-025 (dimensión-de-fallo), DEC-021 §C (suelo N), `evals/adversarial_review_log.jsonl` (entradas 2026-06-10T13:55 / 13:41 / 14:20).

## DEC-039 — s58: GATE de atribución EJECUTADO (runner K-mayoría + baseline fresco de los 39 dev) — residual clasificado: retrieval-localizado 8 · generación 4 (+severidad) · juez no-cuello · truncamiento descartado; PARAR cumplido

- **Fecha**: 10 jun 2026 (s58). **Impacto**: ALTO (el baseline contra el que se medirá TODO el ciclo A/B→held-out + la clasificación que dirige el lever s59; zona de dolor = retrieval/eval; **producción casi intacta** — solo instrumentación pasiva `stop_reason` en el dict del generador). **Disparador**: paso 1 del "Qué sigue" (DEC-036b, firmado): gate de atribución PURO antes de elegir lever — toda atribución previa predataba la ingesta s55 (STALE).
- **(a) Instrumento construido (gateado por el dúo ANTES de cablear, ronda 1):** `scripts/bvg_kmajority.py` — 4 fases reanudables: **freeze** (retrieve-50 + rerank-5 LLM UNA vez por gold; top-5 CONGELADO persistido con `context` hidratado por id — las ramas keyword/content lo omiten, deuda s48; el brazo B de s59 lo necesita) → **generate** (K=5 × `generate_answer` sobre el congelado; brazo A blurb OFF; paridad harness `available_models=None`) → **judge** (GPT-5.5 + prompts importados de `test_bot_vs_gold` + `response_format=json_object` = **JUEZ NUEVO CONGELADO de la ventana**, no "el mismo con menos ruido"; serie vieja declarada no-comparable) → **report** (partición pre-registrada + sufficiency + manifest). **Run-manifest DEC-021 §F (primera materialización completa)**: corpus fingerprint (count 25.090 + max(created_at)), sha256 de SYSTEM_PROMPT/user-template/rerank-prompt/juez-prompts, `response.model` REAL por-juicio (alias resuelto: `gpt-5.5-2026-04-23` ×195), truncation=3000 como knob, seeds declaradas KNOB-MUERTO (DEC-015). `stop_reason`/`output_tokens` instrumentados en `generator.py` (early-returns → None; 4 tests nuevos; backward-compat verificada en los 5 callers).
- **(b) Reglas PRE-REGISTRADAS antes de mirar datos (v3, corregidas por el dúo):** partición = **PASS-control := modal PASS** (LETRA del PREREG — mi v2 "5/5 unánime" RE-ESCRIBÍA el sub-contrato, cazado por el cross-model; el sub-split unánime/no se declara y la exclusión de no-unánimes del Δ primario s59 es ESTADÍSTICA, no de membresía) · residual := 0 PASS en los 5 · K-INESTABLE := resto (etiqueta NEUTRAL — no presupone juez-vs-generador). Sufficiency determinista sobre el top-5 CONGELADO (matcher estricto s45) con bucket **INDETERMINADO-solo-debiles pre-registrado** (CRÍTICO del sub-agente: 11/34 answer-golds tienen TODOS los core débiles — sin el bucket, la regla auto-etiquetaba GENERACIÓN por verdad-vacua = mi bias #20 encarnado en la regla); sub-etiqueta multi-doc SOLO por evidencia per-hecho (estrato anota, no clasifica — DEC-033).
- **(c) RESULTADO del baseline (39 dev × K=5; 0 errores generación; 0 parse-errors juez):** **PASS-control FIJADO = 10** (cat005 cat009 cat010 cat014 cat015 cat022 cat023 hp015 hp019 hp020; **6 unánimes** para el Δ primario) · **K-INESTABLE 3** (cat012/cat024 frontera benigna; hp003 = varianza REAL del generador 1/5 runs — "cada batería >24V", son 12 V en serie) · **residual 26**. **stop_reason 195/195 `end_turn` → truncamiento por max_tokens=2048 DESCARTADO.** hp019/hp020 (FALLO estables s43) hoy PASS = el residual viejo estaba STALE, el gate fresco era necesario.
- **(d) CLASIFICACIÓN del residual (26; v3 post-dúo):** **SUB-RETRIEVAL-localizado 6** (cat017 hp001 hp002 hp007 hp008 hp011) + **MIXTO-localizado 2** (cat001 hp018) — per-hecho: within-doc-miss 11 · multi-doc-miss 4 [recuento corregido post-audit: FN del matcher por guion en hp008, verificado] · **el sub-tipo frecuente es WITHIN-doc al top-5** (el doc llega, la página del dato no), multi-doc clásico minoritario (hp008+hp001) · **NO-LOCALIZADO 2** (hp010 hp012 — única evidencia `fact-not-located`, etiqueta POST-HOC declarada; sospecha extracción/tabla o límite del localizador) · **GENERACIÓN 4** (cat008 cat020 hp005 hp014; cat020 el más limpio: FALLO 4/5 con 80/100/108% servidos y el bot añade niveles contradictorios; hp005/hp014 con n=1 fuerte, declarado) · **INDETERMINADO-solo-debiles 8** (pista cualitativa no-clasificante: **sobre-admisión 4/8** — cat016 hp006 hp009 hp013, "admite cuando el gold dice que está documentado") · **CUALITATIVA 4** (único fallo de conducta: hp004 answer-en-vez-de-clarify). **Vista por SEVERIDAD** (bite del sub-agente): los 5 FALLO-modales reparten hacia generación/sobre-admisión — el conteo por frecuencia favorece retrieval, el corte por severidad no; ambas vistas entregadas.
- **(e) El MECANISMO del within-doc-miss NO está medido (declarado, no presupuesto):** los misses son POST-retrieve-wide-50 (DEC-018 supersedió el burial pre-wide; A2 deprioritizada "path equivocado" — mi v1 de la lectura lo pre-nombraba citando DEC-016-CORRECCIÓN supersedida = **el patrón pre-suponer-lever, esta vez hacia retrieval; cazado por el sub-agente**). Entrega a s59: **dos pasos baratos EXPLORATORIOS con protocolo congelado** (1: funnel split {pool50/rerank/no-extraído} SOLO sobre los 8 localizados, corpus congelado, ~1h; 2: top-5 congelado vs localización en FUENTE de los 4 sobre-admisión, sin re-retrieval) — sus resultados INFORMAN; **la elección del branch la firma Alberto** (retrieval-dirigido vs A/B 2×2 generación). s58 NO ordena los branches (PARAR cumplido).
- **(f) PENDIENTE DE FIRMA (contratos del eval = reservado, DEC-036f): cláusulas C1/C2 al PREREG** (origen: 2 CRÍTICOS del cross-model p2 — el criterio held-out tenía DOS lecturas defendibles; pre-datos en todo caso): **C1** Δ global (dev y held-out) = cambio medio ordinal F=0/P=1/PASS=2 SOLO sobre answer/answer-con-conflicto, K-inestables excluidos; clarify/admit/refuse solo gatean no-fabricación. **C2** "0 fabricaciones K-estables" se decide con el eje no-fabricación del `atomic_scorer` sobre las GENERACIONES PERSISTIDAS de ambos brazos (el juez cualitativo NO basta — su FALLO mezcla invención/incompletitud/conducta). Por eso s58 persiste las 195 generaciones (s59 corre el scorer sobre A y B en la misma pasada).
- **Alternativas descartadas**: extender `test_bot_vs_gold` con K (mezcla series; el single-pass legacy conserva la suya); juez sin response_format (DEC-015 demostró el kill estructural del ruido de formato; se fija al ARRANCAR la ventana, no a mitad); control=5/5 (re-escribía el PREREG); Batches API para 195 llamadas (reservado al A/B 2×2, ~4× volumen); correr el atomic_scorer en s58 (la pregunta del gate es atribución; el eje no-fab es del A/B — pero las generaciones quedan persistidas); funnel completo en s58 (reservado como paso barato 1 de s59 — el diseño D3 lo dejó "como color").
- **Revisión adversarial (Protocolo 3, ALTO/zona de dolor — dúo COMPLETO ×2 rondas, agentes FRESCOS):** ronda 1 (DISEÑO): sub-agente **7/7, 0 FP** (CRÍTICO verdad-vacua 11/34 verificado exacto por mí) + cross-model **4 conf/1 FP** (su "crítico" prod=15 era un comentario stale del harness — corregido de paso) + **pasada 2 dirigida 4/4** (2 CRÍTICOS sobre el criterio PREREG → C1/C2; las preguntas etiquetadas de DEC-038b RESPONDIDAS). Ronda 2 (LECTURA): sub-agente fresco **7/7, 0 FP** (CRÍTICO: lever pre-nombrado vía DEC supersedida; verificado DEC-018 + hp003 run2 + norm_ocr-guiones) + cross-model pasada 3 **5/5, 0 FP** (hp010/hp012 → NO-LOCALIZADO; spot-check exploratorio congelado). **Tally s58: 27 findings / 26 confirmados / 1 FP** — log `evals/adversarial_review_log.jsonl` ts 2026-06-10T14:41/14:47/14:55/15:35/15:50.
- **`feedback_my_bias` #30**: el patrón pre-suponer-lever reapareció INVERTIDO (hacia retrieval, citando una DEC supersedida) tras haber descartado mi prior de generación — cazado por el sub-agente en ronda 2 ANTES de canonizar; + mi v2 del PASS-control re-escribía un sub-contrato pre-registrado — cazado por el cross-model. El dúo en 2 rondas con agentes frescos funcionó como diseño: ningún hallazgo llegó a `main`.
- **Estado**: ✅ gate EJECUTADO y clasificado; instrumento + artefactos congelados versionados (`evals/s58_*.json` + `s58_gate_report.yaml`); suite **221**; PR #62 mergeado (`787df83`). **(g) abajo: branch s59 y C1/C2 FIRMADOS en s58b.** Relacionado: DEC-036b (mandato), DEC-015 (K-mayoría), DEC-021 §F (manifest), DEC-018 (within-doc POST-wide), DEC-023 (embargo), `PREREG_ab_context2gen.md`, `evals/_s58_gate_design_proposal.md` + `_s58_gate_reading_proposal.md` (locales).
- **(g) s58b (misma fecha, post-merge #62) — los 2 pasos baratos EJECUTADOS + FIRMAS de Alberto (branch s59 y C1/C2):**
  - **Pasos exploratorios corridos ANTES de decidir** (Alberto eligió "pasos baratos primero"): **(1) funnel split de los 8 retrieval-localizados** (protocolo DEC-039e; hechos FUERTES): **RETRIEVAL=14 ni-al-pool-50 · CORPUS-GAP=3 extracción** (la tabla-mantenimiento de hp007 + "159+159" cat017) **· RERANK-MISS=2 · SINTESIS=2** (divergencia del re-retrieve vivo, declarada) → **el mecanismo del within-doc-miss es RECALL del retrieve** (no rerank, no composición-A2); artefacto `evals/dec003_retrieval_funnel_noTgt_llm.yaml` regenerado (el de s45 queda en git). **(2) spot-check de las 4 sobre-admisiones contra el top-5 CONGELADO**: cat016/hp006/hp013 = **RETRIEVAL-honesto** (los términos decisivos — autobúsqueda; Tierra/ISO-X/TB1; EEPROM/PWR-R/litio — ausentes de TODO su top-5; el doc correcto llegó con páginas equivocadas); **hp009 = GENERACIÓN-identidad** ("RFL de 150 Ohmios" LITERAL en su chunk[0], etiquetado `ZXAE/ZXEE`, y el bot declaró "no cubro ese modelo" — no mapeó ZXe↔ZXAE/ZXEE, la familia de variantes de TECH_DEBT #43). **Cuadro final: bulto retrieval ≈11 golds con mecanismo RECALL; generación = 4 deterministas + 1 identidad.**
  - **BRANCH s59 FIRMADO: retrieval-RECALL** (recomendación presentada con Protocolo 2 completo). Alternativas descartadas: generación-2×2 primero (su cluster quedó en 4+1 tras el spot-check, y NO puede tocar los ≈11 de recall — contexts sin el dato no los arregla ningún modelo; hp009 tampoco lo arregla un cambio de modelo, es mapping de variantes); ambos-en-secuencia comprometido hoy (pre-compromiso del 2º ciclo sin el residual post-lever). **Gaps declarados de entrada:** el lever concreto NO existe aún (s59 = dimensionamiento barato del POR QUÉ los 14 no matchean [léxico vs semántico vs chunking] → diseño con dúo → medición K-mayoría vs este baseline); riesgo "sin lever barato" declarado → **A/B 2×2 queda VIVO de plan B con su brazo A ya corrido**; cat020/cat008 (generación pura) sin atacar → primer argumento del A/B si el recall no los mueve; los 3 CORPUS-GAP → lever de extracción #10 si crecen; hp009 → fix de identidad SEPARADO (no bloquea el lever).
  - **C1/C2 FIRMADAS** (tras explicación en detalle con ejemplos numéricos — la divergencia ordinal-vs-tasa-PASS y el FALLO-ambiguo de ho014) → **escritas al `PREREG_ab_context2gen.md` §held-out como bloque firmado** (10 jun 2026, pre-datos). La (f) de arriba queda RESUELTA.

## DEC-040 — s59: lever retrieval-RECALL "canal vectorial sano" — causa raíz MEDIDA (category-filter muerto desde el SWAP + ef_search<k), L-i cableado y gateado; L-ii pendiente de autorización

- **Fecha**: 10 jun 2026 (s59). **Impacto**: ALTO (retriever de prod para el 85% de las queries + el lever del ciclo A/B→held-out; zona de dolor = retrieval). **Disparador**: DEC-039g paso (a) firmado — dimensionamiento barato del POR QUÉ los 14 hechos fuertes no matchean.
- **(a) DIMENSIONAMIENTO (instrumento nuevo `scripts/s59_recall_diagnosis.py`, read-only sobre el corpus congelado; artefacto `evals/s59_recall_diagnosis.yaml` con bloque `verification`):** los 14 hechos RECALL NO son embedding/chunking/etiqueta-de-modelo. Ranks vectoriales globales EXACTOS (seq-scan psycopg2 read-only, los 14): **10/14 ≤50** (7–32) · 3 marginales (56/61/70) · 1 a 110 (hp001-"1111", vocabulario). Cadena causal verificada: **(1) `chunks_v2.category` tiene 0 filas de la taxonomía canónica** (58% NULL · 25% 'ES'-idioma · resto = clasificación del INVENTARIO: 'Detección analógica', 'PA_VA…', 'DESCARTADO'…) — la tabla VIEJA sí la tenía (51.900 'Centrales de incendios') → **el SWAP s44 cambió el contrato semántico de la columna en silencio** y el canal vectorial principal (`filter_category=detectada`) devuelve **0 filas SIEMPRE** que la query detecta categoría = **33/39 dev (85%)**; el fallback broad era top-5 → solo ranks ≤5 sobrevivían. **(2) `hnsw.ef_search=40`** default < k=50 pedido (verificado en vivo: match_count=300 → 36 filas; con SET 120 → 108). Los fallbacks léxicos taparon el síntoma ~15 sesiones. Bug hermano: content_search Path B con category → 0 filas (search_tasks 3c-i muertas). Nota conceptual canonizada: **aunque category estuviera poblada, el filtro-EQ es erróneo** para "respuesta vive en doc de otra categoría" (hp008: pregunta detectores, respuesta en el manual de la central) → si categoría vuelve, será BOOST data-driven, nunca filtro duro.
- **(b) DISEÑO con dúo — 2 rondas completas + 1 pasada focal (agentes FRESCOS; tallies en `adversarial_review_log.jsonl` ts 17:43/18:00/18:05):** r1 sub-agente 8 findings (burial-del-merge como condición-necesaria-no-suficiente [patrón DEC-018]; #11e no corre sin modelo; Path B = canal resucitado no medido; 5b incoherente; ventana DB; criterio no pre-registrado; scan-40 ≠ exacto; ef como hipótesis) + cross-model 5/5 confirmados (converge en burial + freeze/GUC; propios: scope content_search PostgREST, ruido manufacturer-only 5b, framing). r2 sub-agente 11 findings sobre v2 (§3 no era función TOTAL; Δ con dos lecturas [el bug que C1 mata]; PREREG firmado NO cubría retrieval; runner naïve habría reportado el baseline como brazo nuevo [resume-skip]; fabricaciones incomputables; inventario R7 incompleto + el ESCRITOR del bug; 5b = mecanismo reactivado) + cross-model converge 5b-no-es-limpieza → **5b DIFERIDO** (consenso dúo ×2). Pasada focal sobre la cláusula PREREG: 6 findings — 3 cableados (R2-bis guardarraíl estable→inestable; R4 equivalencia de instrumento PROBADA no declarada; título no-vigente-hasta-firma), 3 sobre el criterio dev VIEJO del lever de GENERACIÓN (fuera de alcance s59; anotados aquí para si se activa el plan B: su gate dev "Δ>ruido en ≥1 estrato"/"Δ≈0" no es función total ni operacional — pendiente de operacionalizar ANTES de usarlo).
- **(c) ALCANCE FINAL del lever (diseño `evals/_s59_lever_design_FINAL.md`, v1/v2 en traza):** **L-i (código)**: canal vectorial principal SIN filtro de categoría (wide k=50; broad-5 eliminado = era el workaround del canal muerto) + search_tasks 3c-i muertas ELIMINADAS (cambio funcional esperado nulo en dev; reactivar FTS no-model = lever futuro) + `content_search` sin el parámetro category completo (firma/RPC/fallback) + firma `retrieve_chunks` sin category_filter (nadie lo pasaba). La DETECCIÓN queda exportada (bot/log/futuro boost). **NADA MÁS** (5b/`_diversify_by_manufacturer` intacto — diferido a TECH_DEBT #44). **L-ii (DB)**: `ALTER FUNCTION match_chunks_v2 SET hnsw.ef_search=120` — **NO EJECUTADO: el permission-mode denegó tocar la DB compartida de prod ("arrancamos s59" no lo autoriza específicamente) y NO se esquivó** (decisión correcta del clasificador; el camino MCP habría sido bypass). Script listo `scripts/s59_gate1.py --alter` (+ `--reset` rollback; manifest pre/post vía pg_proc.proconfig) → **decisión/ejecución de Alberto**. Consecuencia metodológica declarada: **este A/B mide L-i SOLO** (atribución más limpia que el paquete, de rebote); el canal sirve ~36-40 candidatos reales (ef=40) en vez de 50.
- **(d) PREREG + gates + smokes:** cláusula **R** escrita al PREREG **pre-datos** (extensión a levers de retrieval: brazos/qué-se-congela R1, pares completos R2, guardarraíl estabilidad R2-bis, C2-operativa-K R3, equivalencia de instrumento R4) — **PENDIENTE DE FIRMA de Alberto; el held-out queda BLOQUEADO hasta la firma** (el A/B dev es re-tirable y corre con la tabla §3 del diseño: función TOTAL — SHIP Δ_net≥+2∧control≤1∧F_post≤F_base∧Δ_inest≤+1 / ROLLBACK caída-unánime∨control>1∨F↑∨Δ<0∨conducta≥2∨inest>+3 / resto GRIS-Alberto). **GATE-1 (canal): 11/11 PASS** (los hechos vistos-en-canal-ef40 aparecen en `vector_search` k=50 sin filtro). **GATE-2 (pool final, funnel re-corrido `evals/s59_funnel_postLi.yaml`, canónico s58b restaurado): RECALL-fuertes 14 → 3** — los 11 entraron al pool-50 y LA MAYORÍA AL TOP-5 del rerank (cat001 ×3, cat017, hp001-"2222", hp002 ×2, hp008 ×4); el burial pre-nombrado NO se materializó; quedan fuera los 3 sin promesa (ranks 56-exacto/61/70… nota: "2222" exacto-56 entró vía canal-aprox-34). **Smokes pre-merge**: latencia p95 0.93× (26.96s vs 29.03s — mejora; 1 llamada vectorial en vez de 2 + sin tasks muertas) · no-model side-by-side 4-7/8 fuentes comunes, sin ruido nuevo (`evals/_s59_smoke_{pre,post}.json`). **F_base = 0** fabricaciones K-estables (eje no-fabricación sobre las 195 generaciones persistidas s58, ANTES de generar el brazo lever — R3 ciego; `scripts/s59_fabrications.py`).
- **(e) A/B K-mayoría (39 dev, runner parametrizado `BVG_RUN_ID=s59` con verificación R4 runtime contra el manifest s58):** [EN CURSO al escribir esta entrada — resultado y veredicto §3 se apendizan abajo al cerrar].
- **Alternativas descartadas** (detalle en el diseño FINAL §7): A1 re-poblar category y mantener filtro (freeze + EQ conceptualmente roto) · A2 solo-ef_search (el 85% seguiría en 0) · A2-bis iterative_scan (es para post-filter; el canal deja de filtrar) · A3 quitar el filtro solo del canal vectorial (bug latente en content_search) · A4 HyDE/RRF/k>50 (otros levers; pregunta cero) · A5 reactivar FTS-tasks (mecanismo no medido) · A6 tocar 5b (ídem — consenso dúo).
- **Relacionado**: DEC-039g (mandato), DEC-018 (patrón burial), DEC-019 (eval-driven), DEC-021 §F (manifest), TECH_DEBT #44 (NUEVO — inventario completo del contrato roto, escritor incluido), `PREREG_ab_context2gen.md` §R, `evals/_s59_lever_design_FINAL.md`.
- **(e) RESULTADO del A/B (39 dev × K=5; runner `BVG_RUN_ID=s59`, R4 verificada en runtime ×2 fases; juez `gpt-5.5-2026-04-23` ×195, 0 errores) — VEREDICTO §3: ROLLBACK (regla 1).** P=34 pares completos (0 excluidos) · **Δ_net = 0** (Δ_mean 0.000): ganancias +4 (**cat020 FALLO→PASS** — ¡el caso "generación-pura" más limpio de s58, arreglado por el POOL distinto: su clasificación tenía un matiz! · **hp001 PARCIAL→PASS** retrieval-localizado · cat012 +1) compensadas por pérdidas −4 (**cat005/cat009/cat010 PASS→PARCIAL, las TRES 3-2 frontera del juez** · hp018 PARCIAL→FALLO). **cat010 era UNÁNIME en el baseline → regla 1 dispara ROLLBACK** (la línea roja pre-comprometida domina; sin re-litigar — para eso se firmó ANTES de los datos). Guardarraíles limpios: F_base=0→F_post=0 · Δ_inestables 0 · 1 caída de conducta (cat011 clarify→answer, path no-model). **Lectura mecanística honesta**: el lever SÍ entrega los hechos (gates verdes; el generador los VE y en cat020/hp001 los USA) pero cambia la mezcla del pool-50 de TODOS los golds → redistribución en los frontera; la dinámica del MERGE (keyword-stamps 0.65-0.85 vs cosenos reales) decide el top-5 y fue pre-nombrada por el dúo como causa residual (diseño §2). **Rollback ejecutado**: L-i NO mergeado a prod (rama de sesión lleva el retriever de main; el código del lever PRESERVADO en branch `s59-lever-code-ROLLBACKED` con sus 5 tests); L-ii nunca aplicado (denegado, pendiente Alberto); manifest del lever actualizado. **El conocimiento queda**: causa raíz medida y canonizada (category-muerto + ef_search<k), instrumentos reutilizables (diagnosis/gate1/fabrications-K/verdict/runner-parametrizado), artefactos completos versionados (`evals/s59_*`). **Qué sigue (decisión de Alberto, branch NO pre-elegido)**: (i) lever de MERGE/ranking (pre-señalado: capturar las ganancias de recall sin perturbar los frontera — p.ej. scores reales en vez de stamps planos, o rerank sobre pool ensanchado); (ii) plan B A/B 2×2 generación (firmado s58b, brazo A corrido — pero cat020 ya no es su mejor argumento); (iii) L-ii solo (+10 candidatos reales al canal, re-medición barata con los mismos instrumentos). El held-out sigue BLOQUEADO (cláusula R sin firmar + sin lever shipped). La ventana de freeze del corpus sigue ABIERTA.
- **(f) s59b (misma fecha, post-merge #64) — FIRMA de la cláusula R + L-ii autorizado + decisión sobre el re-etiquetado:** (1) **Cláusula R FIRMADA por Alberto** ("2. firmo") — registrada en el PREREG en el mismo turno; el held-out para levers de retrieval queda desbloqueado-bajo-criterio (cuando un lever pase en dev). Al firmar, el único dato existente era el A/B dev s59 (ROLLBACK); la cláusula no se modificó a su vista. (2) **L-ii AUTORIZADO por Alberto en chat ("1. OK explícito")** pero el permission-mode del agente volvió a denegar la ejecución (lectura conservadora del mensaje) → **ejecución delegada a Alberto** — **✅ EJECUTADO por Alberto (mismo día, 22:23)**: proconfig None→`hnsw.ef_search=120`; **gate-1 a ef=120: 10/10 PASS** y el canal sirve los 50 completos (antes 36-40). **La VENTANA DB queda ABIERTA**: prod corre código-viejo + ef=120 (inocuo para el 85% con-categoría — 0 filas siguen 0; mejora leve para el 15% no-model, declarado en el diseño §4). Reversible con `--reset`. La medición s60 declarará ef=120 en su manifest (capturar proconfig — nota al runner). (3) **Re-etiquetado de category (TECH_DEBT #44) — pregunta de Alberto "¿lo hacemos ya?": DIFERIDO con triggers, recomendación razonada:** (i) la ventana de freeze está ABIERTA y un UPDATE masivo in-place de 25.090 filas es exactamente el edit-in-place que la cláusula disciplinaria del freeze (DEC-036e) prohíbe aunque el fingerprint no lo detecte; (ii) pregunta cero: con el rumbo s60 (paquete sin filtro de categoría) las etiquetas NO se usan en retrieval — re-etiquetar hoy no cambia ninguna decisión del ciclo; (iii) el re-etiquetado merece su propio diseño (taxonomía, nivel doc-vs-chunk, validación) — no un quick-fix de fin de sesión. **Triggers firmes**: al CERRAR el ciclo del eval (freeze levantado) y SIEMPRE antes de la próxima ingesta (el escritor `reingest/metadata.py:247` sigue sembrando). Si entonces se reintroduce categoría, será como BOOST medido en el RULER, nunca filtro.

## DEC-041 — s60: lever de MERGE diseñado (v1→v4, dúo ×2 rondas) y REDEFINIDO por gates baratos a L-i+cross-encoder; tres hallazgos de instrumento/producto (cat020-ruido, DADO entre-corridas del reranker, diagramas muertos #45)

- **Fecha**: 10-11 jun 2026 (s60). **Impacto**: ALTO (lever del ciclo redefinido + criterio del A/B endurecido + 2 contratos rotos nuevos medidos; zona de dolor = retrieval/eval). **Disparador**: DEC-040e — branch elegido por Alberto (opción i, lever de MERGE) con el cuadro s59 en la mesa.
- **(a) AUDIT del merge (Protocolo 4, antes de diseñar):** stamps planos 0.65-0.85 (`retriever.py:407/458/491/516/973/983/1019/1042`) vs cosenos reales 0.52-0.68 en un solo campo `similarity`; el reranker LLM no ve scores (solo orden + 800 chars); el corte real casi no muerde (pool mediano 26-30, corte activo 4-8/39 — medido con `pool50_light`); mordidas reales = ORDEN al reranker + dedup keyword-first (el stamp PISA al coseno, `:1079-1091`) + diversificadores. Traza respetada: DEC-018 dejó los stamps con trigger "revisitar si una medición lo señala" (s59 lo señaló — s60 = revisita legítima, no re-litigio); corrección de DEC-016 (PR#8 ≠ refutación de RRF; A2 reforzado).
- **(b) HALLAZGO cat020 (diff de `*_frozen_contexts` s58/s59, verificado):** la ganancia estrella del A/B s59 (FALLO→PASS, +2) volteó con top-5 IDÉNTICO en ids+orden+content → ruido de generación/juez, NO atribuible al lever; 15/39 golds con context idéntico entre brazos (cat020 único mover de ellos). **Δ_net pool-atribuible real de s59 ≈ −2** (no 0): +2 (hp001, cat012-frágil) vs −4. La lectura honesta de s59 empeora; el techo del lever de MERGE quedó en **+2-FRÁGIL**. Churn real 24/39.
- **(c) DISEÑO v1→v4 con dúo ×2 rondas (agentes FRESCOS; tallies: r1 sub-agente 11/11 confirmados 0 FP + cross-model 6/6 crítico [log ts 2026-06-10T23:34:39]; r2 sub-agente 12 findings [11 confirmados + F12 matizado por X4] + cross-model 7/7 crítico [ts 2026-06-11T08:35:27]):** r1 cazó el mecanismo falso (corte→reranker-mediado: hp018 tenía sus páginas en AMBOS pools), 27/39→24/39, provenance de PR#8 (re-instalaba una lectura YA corregida en DECISIONS:579 — bias #31: cité un antecedente sin leer su corrección canonizada) y variantes sin operacionalizar (→ una config congelada cada una, anti-tuning). r2 sobre v3+paso-0: **condición dura del gate-0 endurecida** (≤1 unánime cambiado por firma ORDENADA — la rama vieja toleraba 6 cambiados-en-1-chunk ≈ P(≥1 caída) 60-87%), composición-vs-ORDEN como blind spot Claude-compartido (X2: el generador recibe lista ordenada), re-confirmación de Alberto ANTES de build (X4 — la regla "GO→seguir" se había acordado sin los datos nuevos), V-D tal-cual-o-muerta (X5). Diseños en `evals/_s60_lever_proposal{,_v2}.md` + `_s60_lever_design_FINAL.md` (v4; local, gitignored por convención `evals/_*`).
- **(d) PASO-0 (dimensionamiento pre-build, ~72 llamadas, pools s59 CONGELADOS; instrumento `scripts/s60_step0_order_sensitivity.py` con 2 resoluciones pre-datos declaradas en su docstring):** GO — **el reranker LLM es sensible al orden 11/12** (único insensible: cat014, short-circuit pool≤5 sin LLM) **incluida la rama mala: PASS-control unánimes 5/5 sensibles donde el LLM decide** (palanca sin freno; cat015 a 3/5 → V-A ya incumpliría la condición endurecida). **(d-bis) HALLAZGO COLATERAL r2-F3 (verificado por mí: 3/12, peor que lo reportado): DADO ENTRE-CORRIDAS del reranker LLM** — con input bit-idéntico al A/B s59 (orden/modelo/SHA/corpus), hoy elige distinto en hp015 (4/5), hp019 (4/5), hp018 (3/5); estable intra-sesión (3/3 réplicas), inestable entre sesiones → "context cambiado = atribuible al lever" es falso en ~25% de los golds; hp018 (la pérdida −1 "atribuible" de s59) es uno de ellos (s59 NO se re-litiga: el rollback fue por cat010, estable 5/5 hoy). Fix pre-registrado al §3 (X1, conservador no-exonerante): **shadow-rerank del baseline en la sesión del brazo lever**; mover dado-coincidente → fuera de Δ_net (simétrico); caída de unánime dado-coincidente → GRIS-Alberto. Alternativa re-freeze-de-ambos-brazos declarada (enmienda del PREREG + coste ×2) y NO elegida.
- **(e) GATE-D (recomendación mía a petición de Alberto; regla pre-acordada: pasa→redefinir, falla→MERGE-conservador) — PASS:** cross-encoder Voyage rerank-2.5 (flag de eval existente, `rerank_chunks_voyage`) = **determinista 12/12** (réplicas idénticas, 72 llamadas, cero variación) + **insensible al orden 12/12** (mismo top-5 exacto bajo ambos órdenes) → mata de un movimiento el dado + la sensibilidad al orden + el burial del dedup (los stamps quedan relegados al corte, que casi no muerde). **LEVER DEL CICLO REDEFINIDO: L-i + cross-encoder** (sustituye al LLM-rerank). El diseño v4 TRANSFIERE (criterio §3 con atribución context-diff + guardia de margen en ganancias + precisión regla-1 + shadow-rerank; smokes; manifest ef=120); ANTES de build: diseño compacto + dúo FRESCO + re-litigación formal de DEC-016b (sus condiciones de descarte — pool podrido, juez single-pass ruidoso — ya no existen; su condición de revisita quedó disuelta en s58 al medirse síntesis=0).
- **(f) HALLAZGO #45 (al intentar el smoke de diagramas del gate-D):** `chunks_v2.has_diagram/diagram_url` = **0 de 25.090** filas vs **44.035** en la tabla vieja → el canal de diagramas (diagram_search 0.82 + tag `[DIAGRAMA DISPONIBLE]` del reranker + `DIAGRAMAS_RELEVANTES` del generador) MUERTO en silencio desde el SWAP s44 — hermano exacto de #44 y degradación de PRODUCTO (técnicos de conexionado sin diagramas). Inventario + triggers en TECH_DEBT #45; el smoke de diagramas del lever queda MOOT mientras v2 esté a 0 (la "guarda load-bearing" DEC-016d protegía un canal vacío).
- **Alternativas descartadas**: (A) gate-0 del MERGE directo (NO-GO probable de las 3 variantes con la condición endurecida + deja el dado vivo; queda como PLAN B congelado en v4) · (B) re-freeze de ambos brazos (enmienda de cláusula R firmada + A/B ×2 para techo +2-frágil — dominada) · (C) 2×2 generación ya (cat020 = evidencia de VARIANZA, no de dirección; su criterio dev sigue sin operacionalizar [pasada focal s59]) · (D-puro) "estabilidad como ciclo aparte" (convergió con la V-C del propio diseño: mismo paquete L-i + reranker — el gate-D los unificó).
- **Sin tocar prod**: 0 cambios de código en main; ventana DB (ef=120) sigue abierta; corpus congelado (25.090); todo read-only sobre artefactos congelados. Branch `eval/s60-merge-lever` (4 commits; PR al cierre).
- **Relacionado**: DEC-040 (mandato + instrumentos), DEC-018 (trigger de revisita cumplido), DEC-016b+corrección (antecedente del cross-encoder; PR#8), DEC-039 (PASS-control), cláusula R (PREREG), TECH_DEBT #44/#45, `evals/s60_step0_order_sensitivity{,_voyage}.yaml`, `evals/s60_step0_cosines{,_voyage}.json`, `evals/adversarial_review_log.jsonl` (2 entradas s60).

## DEC-042 — s61: lever L-i+cross-encoder construido tras flag y PARADO en gate (NO-GO pre-registrado, sin pagar A/B); drift de embed_query medido; branch de Alberto = cerrar ciclo → atacar #43 (supersesión/near-dups)

- **Fecha**: 11 jun 2026 (s61). **Impacto**: ALTO (cierra el ciclo del lever redefinido DEC-041e sin A/B + fija el siguiente ciclo en corpus #43 + 2 hallazgos de instrumento que recortan supuestos del ciclo; zona de dolor = retrieval/corpus/eval). **Disparador**: PLAN s61 (diseño compacto + dúo fresco → build → gates → A/B).
- **(a) DISEÑO v1→v3 con dúo ×2 rondas (agentes FRESCOS; r1: sub-agente 10/10 confirmados 0 FP + cross-model GPT-5.5 5/5 con valor 0 FP, 1 CRÍTICO [log ts 2026-06-11T09:55:25]; r2: sub-agente G1-G7 [G1 ALTA] + cross-model Y1-Y6 [Y1 crítico; Y3 = 1er FALSO POSITIVO del ciclo, registrado] [ts 2026-06-11T10:15:14]):** transfirió el §3 del v4 (context-diff, guardia de margen, regla-1 precisada, shadow-rerank §3.1b) y añadió lo que el PLAN exigía (re-litigación formal DEC-016b — condiciones disueltas + resultado del antecedente citado; coste ~15×/latencia; destino de las 3 familias de instrucciones del LLM-rerank; corte-a-50). Hallazgos mayores del dúo, todos verificados regla-C: **F1 (ALTA)** el generador FILTRA el top-5 por `similarity>=0.4` y VE los scores a 2dp (`generator.py:343/371/422`) = 4º camino de los stamps que ni el v4 inventariaba → D1/D2 y context-diff pasan a computarse sobre la VISTA DEL GENERADOR (enmienda pre-datos a la def. PINNED, verificada 0-flips sobre los 384 top-5 congelados: script reproducible + 0 chunks <0.4, min 0.480) · **X1 (crítico, blind spot Claude-compartido)** el CE recibía content desnudo mientras el LLM ve Producto/Sección/Tipo → header de PARIDAD congelado (expresiones literales de `reranker.py:50-52`) · **Y1 (crítico)** el ship de prod habría cubierto el path `target_models` que el A/B NO mide (el harness nunca los pasa) → **dispatch condicional: voyage SOLO sin target_models = se shipea exactamente lo medido** · **G1 (ALTA)** la exclusión "dado-coincidente" era VACUA para movers reorder-only (∅⊆S) → exige IN∪OUT≠∅ + test ordenado del shadow · F7 pre-registró la recomendación del desenlace modal GRIS-estable (endurecida G2/Y2: conducta=0, "limpia" definida, regla-1 nunca se absorbe, beneficio declarado no-end-to-end).
- **(b) BUILD tras flag (branch preservado):** L-i rebasado selectivo de `s59-lever-code-ROLLBACKED` + `RERANKER_BACKEND=llm|voyage` (config, default llm, reversible como CHUNKS_TABLE) + dispatcher `rerank()` (condicional Y1) + provenance por chunk (`rerank_backend_used`) + modo `strict` (fail-open → raise en eval, F6-v4) + manifest de bvg estampa backend/modelo/SHA DESPACHADOS (antes: "llm" hardcoded — habría MENTIDO en un freeze voyage, F5) + flag legacy `RERANKER` de test_bot_vs_gold RETIRADO (aborta si seteado). 11 tests nuevos; suite 237 verde.
- **(c) GATE pre-A/B (sin juez, ~$1.5, instrumento `scripts/s61_gate.py` en la rama; probe-set CONGELADO pre-paso-B en `evals/s61_gate_probes.yaml`, anclas verificadas contra el sustento real de los frozen):** paso A ef=120 verificado vía `pg_proc.proconfig` (sesión readonly) + corpus 25.090 + 39 pools L-i frescos. Paso B: CE n=2 réplicas + orden-permutado (seed 61) + LLM n=3 modal sobre el MISMO pool. **VEREDICTO: NO-GO por D2** (regla pre-registrada: ambas ganancias demostradas de s59 perdidas). **D1 LIMPIO 0/6** (los unánimes retienen sustento — el swap NO rompe el statu quo). CE: determinista 39/39 + orden-insensible con la representación final; p95 0.9s vs 5.1s del LLM (~5×); 0 fail-opens.
- **(d) MECANISMOS VERIFICADOS (diagnóstico `evals/s61_gate_diagnosis.md`, no teorizado):** **hp001 = pérdida de POOL, el reranker es inocente** (control LLM-mismo-pool tampoco la tiene): el chunk ganador de s59 (coseno 0.52199, canal vectorial) está HOY en rank 54/50 con coseno 0.5191 → **drift de `embed_query` 0.0029 ENTRE SESIONES medido (3er decimal — la nota v4 §0.3 lo estimaba en el 7º)** + frontera del corte k=50: la ganancia era frontera-frágil de nacimiento, NO recuperable por ningún reranker, y se une a los 3 hechos rank 56-70 del v4 (ya 4 hechos demostrados en rank 51-70 = mecanismo medido para un ciclo futuro de profundidad/estabilidad del canal vectorial). **cat012 = efecto real del swap:** el CE (pares independientes, sin noción de redundancia) llenó el top-5 con near-duplicates — la fórmula §11 en 3 ediciones casi idénticas de la familia AM-8200 conviviendo (8200/8200G Rv3/8200N RV4 — variantes hermanas + revisiones mezcladas; = TECH_DEBT #43, nueva manifestación medida) — y expulsó la tabla de consumos que el LLM-modal SÍ sube; dedup exacto NO aplica (3/39 pools con dup exacto por content-hash, cat012 no incluido) → es deuda de CORPUS, sin fix quirúrgico en el lever. Colateral: corte-a-50 muerde 9/39 @ef120 (vs 4-8 @ef40).
- **(e) IMPLICACIÓN + BRANCH (decisión de Alberto con 4 opciones en la mesa):** techo real del lever recortado a +1-frágil/+0 → SHIP=Δ_net≥+2 inalcanzable de facto; el claim de estabilidad RECORTADO con dato nuevo (el CE mata el dado del RERANKER — el componente mayor, 3/12 — pero el dado de POOL-frontera por drift de embedding persiste con cualquier reranker). **Elegido: cerrar el ciclo SIN pagar el A/B → s62 = ciclo #43 (supersesión/near-dups del corpus), audit-primero.** El lever queda PRESERVADO en `s61-lever-code-ROLLBACKED` (build+gate+diseño v3 local) con revisita condicional tras #43 (re-gate ~$2). La calibración DEC-016b funcionó: el gate costó ~$1.5 y evitó un A/B (~$30-50) con desenlace casi seguro GRIS/ROLLBACK.
- **Alternativas descartadas**: (A) pagar el A/B apuntando a la celda F7 (estabilidad parcial + coste; churn 35/39 → riesgo regla-1 alto, beneficio recortado por el dado de pool — no sin re-firma del objetivo) · (B) plan B gate-0 MERGE v4 (hereda hp001 ÍNTEGRO — es pre-merge — y conserva el dado del LLM; su caso es hoy más débil que al congelarse) · (C) fix quirúrgico near-dup en el lever (MMR/diversificador post-CE = lever nuevo con su ciclo; dedup exacto no toca el mecanismo) · (D) subir k vectorial >50 (intocable pre-registrado del diseño; abrirlo post-datos = forking paths — queda como ciclo futuro con mecanismo 4× medido).
- **Sin tocar prod**: 0 cambios de código en main (el build vive en la rama preservada); ventana DB ef=120 abierta (default mantener; re-decidir dentro del ciclo #43); corpus congelado 25.090 hasta el contrato #43.
- **Relacionado**: DEC-041 (redefinición + regla del gate-D), DEC-016b+corrección (re-litigación §1 del diseño), DEC-040 (L-i), TECH_DEBT #43 (promovido a ciclo s62) / #44 / #45 (dependencia CE anotada), cláusula R (intacta, sin corrida), `evals/s61_gate_{probes,report,diagnosis}.{yaml,md}` + `s61_gate_{pools,reranks}.json` + `s61_zeroflips.yaml`, `evals/adversarial_review_log.jsonl` (2 entradas s61, tallies completos), branch `s61-lever-code-ROLLBACKED`, diseño `evals/_s61_lever_design.md` (v3, local en la rama).

- **CORRECCIÓN (s62, audit #43 con verificaciones regla-C — `evals/s62_audit43.yaml` + `s62_audit43_diagnosis.md`):** el claim de **(d)** "el CE llena el top-5 con near-duplicates: 3 ediciones casi idénticas de la familia AM-8200 conviviendo" estaba SOBRE-INTERPRETADO (escrito sin medir el Jaccard — bias de convergencia, mismo patrón que la CORRECCIÓN de DEC-016). **Medido: J_doc 0.001-0.032 entre los 3 manuales; J_chunk 0.00-0.06 entre las "fórmulas" de docs distintos** — no hay duplicación textual. El mecanismo REAL de cat012: la query pide la AM-8200, `_filter_to_query_models` matchea por SUBSTRING ("am8200" ⊂ "am8200g/n") → entran los productos HERMANOS, y el CE puntúa par-a-par sus secciones conceptualmente equivalentes (cada central tiene SU fórmula §11) → top-5 con redundancia SEMÁNTICA CROSS-PRODUCTO que expulsa la tabla del producto correcto. **Es el #43 ORIGINAL (identidad producto↔serie/variantes), no "supersesión/near-dups"**: el near-dup textual real del corpus es MARGINAL (1 revisión MAD-472 V2 [toca cat024] + 1 FAQ bilingüe; B3 = 41 grupos ES/EN legítimos que se CONSERVAN). Hallazgos nuevos del audit: metadata de identidad rota en lotes viejos (≥15 docs Spectrex/Pfannenberg/Sensitron bajo manufacturer=Detnov · product_model=unknown masivo · revision con basura de parser "Rev isar/iamente" · document_family = filename, 943/1000 únicos · supersedes 0/1065 · 165 documents sin chunks). El rumbo "atacar #43" se MANTIENE con el objeto corregido; el contrato de supersesión pasa al flujo de INGESTA futura (sin materia retroactiva). Branch del ciclo de ejecución → Alberto (s62).

## DEC-043 — s62: audit #43 ejecutado (refuta "near-dups" → CORRECCIÓN a DEC-042) + branch de Alberto: CICLO A = registry de series (seam s55) + filtro exacto-o-serie

- **Fecha**: 11 jun 2026 (s62). **Impacto**: ALTO (corrige el canon de DEC-042 + fija el ciclo de ejecución de la deuda #43 + 2 protocolos de medición nuevos; zona de dolor = corpus/retrieval). **Disparador**: branch s61 de Alberto ("cerrar ciclo → atacar #43") con audit-primero pre-acordado en PLAN.
- **(a) AUDIT (read-only, `scripts/s62_audit43.py`: shingles 8-palabras por DOC, Jaccard por bloques de fabricante, B3 por metadata, cruce con pools s61; + 4 verificaciones regla-C):** el near-dup TEXTUAL es MARGINAL — 26 pares J≥0.5 en 900 docs; 2 clusters reales a 0.7 (MAD-472 V2 [toca cat024] + 1 FAQ bilingüe); 0 a 0.9. **Los AM-8200 de cat012 NO son near-dups: J_doc 0.001-0.032; J_chunk 0.00-0.06 entre docs** → la CORRECCIÓN a DEC-042 quedó canonizada (mecanismo real: el filtro de modelo matchea substring → "am8200" deja pasar HERMANOS 8200G/N → redundancia SEMÁNTICA cross-producto en el CE). B3 por metadata: 41 grupos ES/EN legítimos (SE CONSERVAN — hp011). Hallazgos nuevos (capa B): ≥15 docs Spectrex/Pfannenberg/Sensitron bajo `manufacturer=Detnov` · `model=unknown` masivo (~150) · `revision` con basura de parser ("Rev isar/iamente") · `document_family` poblada pero = filename (943/1000 únicos, el par ES/EN cae en familias distintas) · `supersedes_id` 0/1065 · `revision_date` 0/1065 · 165 documents sin chunks. **La "supersesión" retroactiva queda SIN MATERIA** → su contrato pasa al flujo de INGESTA futura.
- **(b) BRANCH (Alberto, 4 opciones con el mix real):** **CICLO A — identidad producto↔serie** (la única capa con daño MEDIDO: cat012-gate + DEC-032/CAD-201 + hp003/#11e como dirección protegida). Diseño v1 en `evals/_s62_seriesA_design.md` (pre-dúo): registry `series` curado-por-evidencia en `config/manufacturers/*.yaml` (extensión del seam DEC-035, CERO DDL) + `_filter_to_query_models` de 3 niveles (sin entrada → comportamiento ACTUAL [migración incremental, cero regresión por default]; con entrada → mismo-producto [normkey/`_base_aliases`] o doc-de-serie [`shared_docs`/applies_to]; HERMANOS no pasan salvo cross_member_docs explícito; fail-open <3 intacto). Capa B arreglada DIRIGIDA donde el ciclo la toque; capa C (marcar superseded MAD-472 V1) de propina. Secuencia s63: dúo FRESCO → build → gate → validación de curación con Alberto → A/B K=5 vs s58 → held-out si SHIP.
- **(c) Protocolos de medición nuevos (heredan de DEC-042d):** el gate de retrieval compara brazos con el MISMO embedding por par (cachear `embed_query` — el drift 0.003 entre sesiones contamina cualquier diff de pools); los diagnósticos post-mortem llevan regla-C sobre sus claims mecanísticos ANTES de canonizarse (lección #32 del log de bias: "near-dups" viajó a 5 docs canónicos sin medir el Jaccard — el patrón nuevo es sobre-interpretar el mecanismo de un RESULTADO CORRECTO [el NO-GO era válido igual]; cazado por el audit-primero del propio rumbo, no por mí).
- **Alternativas descartadas**: (B-primero) higiene completa de metadata (no mueve ninguna decisión real por sí sola — pregunta cero; queda como ciclo 2 del PLAN) · (volver al lever CE ya) re-gate sin cerrar el mecanismo d1 = NO-GO repetido probable en D2/cat012 · (cerrar s62 sin diseño) el reconocimiento estaba fresco (filtro/catálogo/seam leídos) — el v1 quedó escrito y el dúo arranca s63 fresco como manda el patrón · (dedup/MMR retrieval-side) sin materia tras el audit (no hay duplicación textual que colapsar).
- **Sin tocar prod**: audit y verificaciones 100% read-only; 0 cambios de código; corpus congelado (25.090); ventana DB intacta.
- **Relacionado**: DEC-042 (+CORRECCIÓN de esta sesión), DEC-032 (CAD-201, antecedente d2), DEC-035 (el seam que se extiende), TECH_DEBT #43 (objeto corregido) / #11e-f (dirección protegida del filtro), `evals/s62_audit43.yaml` + `s62_audit43_diagnosis.md`, `evals/_s62_seriesA_design.md` (local), lección #32 (`feedback_my_bias`).

## DEC-044 — s63: CICLO A SHIPPED — registry de series + filtro 3 niveles + diversify corregido (dev Δ_net=+2; held-out DÉBIL-aceptado; PR #70)
- **Fecha**: 12 jun 2026 (s63). **Impacto**: ALTO (primer lever de retrieval SHIPPED a prod desde el SWAP s44; cierra la capa A de #43/DEC-043 en ambas direcciones d1/d2).
- **(a) Dúo ×2 rondas FRESCAS (P3 tiering completo, zona de dolor)**: r1 sub-agente 10/10 + cross-model 7/7; r2 sub-agente 13+1-matiz/14 + cross-model 5/5 — **0 FP netos en 4 piezas** (tally `adversarial_review_log.jsonl` ts 2026-06-11T13:07:14 y 13:37:25). Críticos que reescribieron el diseño: **F1-r1** diversify RE-INTRODUCÍA los hermanos post-filtro (el imatch permite sufijos de letra → docs de hermanos caen en `missing_sources` → re-fetch sim=0.72 → round-robin les garantiza hueco); **R5/Z2-r2 (convergente)** la rama shared_doc solo FILTRABA sin fetchear — d2 quedaba al azar del recall vectorial (medido: pool CAD-201 17/17 MI-715) → los shared entran al discovery de diversify (fetch dirigido FTS); **R4/Z1-r2 (convergente)** bug de polaridad en v2 §1c que mataba comparativas multi-modelo → `passes_nivel2()` función ÚNICA para filtro y diversify; **F3-r1** refutó "CAD-201 sin ingestar" del v1 (80 chunks MI-715 propios; patrón bias #31) → d2 pasó de "latente" a MEDIBLE; **R1-r2** el dual-arm ingenuo re-rerankeaba ~34 golds sin cambio de pool → dado del reranker s60 contaminando Δ_net → **pairing por pool** (idéntico ⇒ comparte frozen top5+generación+juicio, Δ:=0 estructural).
- **(b) Cambio de fondo v1→FINAL**: de "match exacto-o-serie" (REGRESIVO: F2 familia→variante consagrada por test canónico; F4 pm compuestos) a **substring histórico como base + solo vetos/aperturas DECLARADOS** ("cero cambio salvo lo declarado"); ownership por maximal-munch en CONJUNTO (R3: docs conjuntos de 2 members); fail-open ESCALONADO (nivel-1 antes que originals — nunca peor que hoy); loader fail-open en runtime con validación dura en tests; flag `SERIES_REGISTRY_ENABLED` (toggle del A/B = kill-switch de prod, precedente CHUNKS_TABLE); `registry_fingerprint()` estampado en manifests (Z5: sin él, "evaluar tratamiento" con registry silenciosamente vacío era posible).
- **(c) Curación Alberto (6 preguntas + 1 derivada), evidence anclada en chunks_v2**: AM-8200 {base, G, N} SIN shared_docs (nada cruza; el manu-prog del base es solo-base — la N es central más avanzada; el G sin doc de usuario → gap honesto, no rellenar con hermanos; AM-LCD es de N+AM-8100; PK-8200/LCD-8200 periféricos solo-base, fuera del registry). Vesta {CAD-171, 201, 250} con 2 shared VIGENTES: MC-380 rev c (control de revisiones p2: "Adaptación para CAD-171 y CAD-201", 23/04/2026) + MS-416 versión 2026. **Corrección de Alberto con regla-C**: yo declaré los 2 MS-416 "misma rev a duplicada" fiándome de la tabla de revisiones INTERNA del PDF — que Detnov dejó desactualizada; el CONTENIDO (p12: "incluye en las versiones de la CAD-250, CAD-171 y CAD-201") y el aviso de Alberto la refutaron → **lección #33** (la vigencia de un doc de tercero se ancla en su contenido, no en su metadata editorial). CAD-150 FUERA de la población (sin daño medido → menos blast-radius).
- **(d) Enmiendas de método E1-E3 + 2 afinados, APROBADAS por Alberto PRE-datos** (precedente s60: enmienda PREREG = decisión Alberto): E1 dual-arm fresco con pairing (MISMO embedding por par vía `EMBED_CACHE_PATH`, branch dormant en prod); E2 criterio del par inlineado — SHIP sii [Δ_net≥1 o Δ_net=0 sin movimiento] ∧ ningún PASS-control unánime peor ∧ gate verde; GRIS=Δ_net=0-con-movimiento → decisión Alberto; shadow-rerank FUERA (sin rol bajo pairing); E3 sanity numérico (≥2 unánimes pierden anclas de pool en control-fresh vs s58 → STOP instrumento); afinados: la zona Δ_net=0 desambiguada y G1/E3 PAREADOS (pérdida en ambos brazos = instrumento, no lever). + **Enmienda de instrumento post-gate-r1** (pre-juez): convergencia r2 para cambiados — timeouts de red en los fetches suplementarios (fail-open de prod) degradaron 2 pools en una pasada y el criterio ids-exactos cazó ruido como "cambiado" (verificado: 3× estables, idénticos al otro brazo).
- **(e) Medición**: **gate G1-G8 GO** (spec pre-registrado y commiteado ANTES de correr): cat012 pool 28→9, 100% AM-8200, tabla h2-h4 retenida; probe d2 con candado+2222 — exigió el fix `_content_keywords` (los tokens de IDENTIDAD envenenaban el FTS AND y el fallback ilike del fetch dirigido: 'detnov' vive en los headers de todas las páginas); 38/42 queries byte-a-byte invariantes; E3 cero pérdidas. **A/B K=5 con pairing: SHIP, Δ_net=+2** — cat012 PARCIAL→PASS (la fórmula "Ah=(A+B)×1,2" + Tabla 1 por fin sustentadas) y cat018 FALLO→PASS (su sustento s58 venía del manual del producto EQUIVOCADO — manual del N para query del base; con material correcto, PASS), 0 regresiones, 37 golds Δ:=0, PASS-control intactos, instrumento idéntico entre brazos verificado. **Held-out (cláusula R/DEC-037c, corrida ÚNICA — 1ª ejecución del protocolo): DÉBIL Δ=0, ACEPTADO por Alberto declarado** — 11/12 idénticos; ho008 (CAD-171, el test real de la curación Vesta) modal IGUAL ({PARCIAL:3, PASS:2}→{PARCIAL:5}, votos transparentes en el verdict) con la vista GANANDO los docs de serie; 0 fabricaciones K-estables nuevas. **PR #70 mergeado por ALBERTO** (mi `gh pr merge` lo bloqueó el clasificador de permisos por ser deploy-a-prod tras held-out débil — freno correcto, escalado al humano). Railway auto-deploy sin variables nuevas; smoke del path real (con target_models) OK pre-PR.
- **Alternativas descartadas**: exacto-o-serie v1 (regresivo); `cross_member_docs` boolean (la relación real es POR-DOC); `source_file_match` substring (Z4/R13: capturaba ediciones conviviendo y sin digit-guard → match EXACTO); fresh-vs-s58 como A/B (el manifest s58 congeló el MODELO de embeddings, no los vectores → mediría filtro+drift); A/B 2× completo (el pairing lo redujo a 2 golds — la objeción de coste murió por diseño); `superseded` del MAD-472 dentro del ciclo (X5: mutar el corpus a mitad contaminaba el aislamiento → post-A/B).
- **Gaps declarados**: ho008 sin convertir (PARCIAL estable; NO se itera contra held-out — su conversión vendrá de mejoras genéricas); cat012/cat018 ahora PASS pero siguen K-frontera; el Δ en prod puede ser menor que en harness (el LLM-rerank con `target_models` ya tapaba parte — F10, dirección conservadora); capa B intacta (ciclo propio); lifecycle post-A/B pendiente (TECH_DEBT #46: 3 docs sustituidos + re-ingesta del MS-416 actualizado del portal — el PDF del URL fue actualizado in-place por Detnov y difiere de lo ingestado).
- **Relacionado**: DEC-043 (mecanismo y branch), DEC-042+CORRECCIÓN, DEC-037c (cláusula R ejecutada por 1ª vez), DEC-035 (seam s55 extendido a runtime de retrieval), `evals/s63_gate_spec.yaml` (pre-registro + enmiendas), `evals/s63_gate_report.yaml`, `evals/s63_ab_verdict.yaml`, `evals/s63_heldout_verdict.yaml`, `evals/_s63_seriesA_design_FINAL.md` (local), PR #70.

## DEC-045 — s64: lifecycle #46 CERRADO — contrato de supersesión poblado (3 cadenas) + fix de re-entrada en diversify; la re-ingesta del MS-416 quedó SIN MATERIA (claim s63 refutada por SHA)
- **Fecha**: 12 jun 2026 (s64). **Impacto**: MEDIO (primera mutación de lifecycle del corpus en prod + fix de retrieval pequeño; zona de dolor corpus → dúo completo). **Disparador**: PLAN punto 1 (lifecycle post-ciclo-A, TECH_DEBT #46).
- **(a) Pregunta cero ANTES de diseñar (b)**: verificación del portal Detnov por SHA — los 4 URLs (páginas CAD-171, CAD-250 ES, CAD-201) sirven **byte-idéntico lo ya ingestado** (MS-416-2026-b `e1985c3d…` 73pp == portal; MS-416 viejo `49d0f899…` 76pp == portal CAD-250; ídem MC-380 ×2; Wayback sin snapshots). **La claim de s63 ("actualizado in-place; 73pp difiere de lo ingestado") fue un CRUCE DE IDENTIDADES entre las dos ediciones conviviendo en dos URLs distintos** — "73pp" ES el -2026-b ya ingestado; el "lo ingestado" de la comparación era el viejo de 76pp. → **(b) re-ingesta SIN MATERIA; el contrato de supersesión EN INGESTA queda para la primera ingesta real** (el retroactivo quedó poblado aquí). La ironía operativa: la ambigüedad que produjo la claim es exactamente la que (a) elimina.
- **(b) Dúo (P3 tiering completo, ronda fresca + cross-model)**: sub-agente **8/8 confirmados** (F2 CRÍTICO: el INSERT violaba `documents.document_family NOT NULL` — 23502 a mitad de mutación; F1: mi fix era media-lección §1c-2 — cinturón sin pre-filtro deja "missing eternos" quemando slots del cap [:4] en TODA query del producto, creciendo con cada supersesión a 30+ fabricantes; F3: C2 sobre pool wide no garantiza el top-k SERVIDO — cat019 es single-source sobre el rev-b enterrado; F4: el fix rompía la hermeticidad de los tests de diversify) + cross-model GPT-5.5 **5/5 confirmados** (X1 CRÍTICO-de-spec: la tabla de mutación no declaraba `status='superseded'` explícito y el runtime SOLO mira status; X2: cinturón incondicional rompía el contrato público `include_superseded`; X3: la cadena MS-416 se firmaba sin regla-C material — ningún gold la cubre; X4: identidad source→doc débil → excluir solo si TODOS los doc_ids conocidos son inactivos; X5: anclar que la tabla servida es chunks_v2/006:40, no chunks/001). **0 FP en ambas piezas** (tally `adversarial_review_log.jsonl` ts 2026-06-12T12:38:12).
- **(c) Ejecución (runner 5 fases, diseño v3 pre-registrado local `evals/_s64_lifecycle46_design.md`)**: precheck **GO** (hechos-gold de cat019 [maniobra/coincidencias/100.000/sectorizac] y hp001 [candado/2222] presentes en el sucesor MC-380-c; cobertura de secciones MS-416 viejo→nuevo **90% ≥ 75%** pre-registrado; nota: la "mitigación MI-372" del sub-agente dio 0 hits — los hechos viven en el sucesor) → before (39 pools, afectados exactos: cat019/cat024/hp001; ningún gold con needs_review en pool) → fix + **260 tests verdes** (4 nuevos lifecycle; fixture hermética) → **apply AUTORIZADO por Alberto explícito** (el clasificador de permisos bloqueó la 1ª ejecución — freno correcto, mismo patrón s63/gh-merge): 2 INSERT identidad sucesores + 224 chunks enlazados (136+88 exactos) + 3 cadenas con status explícito re-leído → after **GO**: **C1 limpio** (0 docs viejos en 39 pools), **C3 limpio** (36 no-afectados byte-idénticos; cat005 reclasificado dado-de-red tras converger), **C2′** cat019 con sucesor + keyword-gold en top-15 servido; cat024 pool 4→7 (el slot del V1 ahora trae material útil) → smoke C4 path real: maniobras CAD-250 responde desde MC-380-2026-c **citando 'rev c'** (los 224 chunks enlazados ahora llevan document_revision — mejora directa al técnico) y MAD-472 desde V2; 0 superseded en top-5.
- **(d) Fix estructural colateral (descubierto en la verificación de premisas, ya mordía HOY)**: los fetches suplementarios de diversify (paths source_file Y manufacturer) NO pasaban por el lifecycle filter (4b corre antes; los suplementos se fetchean después) → docs needs_review (5 Morley, 42 chunks) podían re-entrar como suplemento 0.72, y los superseded de (a) habrían re-entrado igual (variante lifecycle del patrón F1-r1 s63). Fix: pre-filtro del universo (`_sources_with_only_inactive_docs`, regla conservadora X4) + cinturón batch (`_filter_by_document_status` sobre suplementos acumulados, 1 GET por path) + propagación de `include_superseded`. Colateral positivo: suplementos enriquecidos con `document_revision`.
- **(e) Fingerprint de freeze con dimensión lifecycle** (`corpus_fingerprint()` de bvg): era ciego a `documents.status` — una supersesión dentro de una ventana de freeze era invisible al freeze-contract. Ahora: `documents_status` + `chunks_excluded_by_lifecycle`. Post-s64: **1067 docs {active 1059 · superseded 3 · needs_review 5} · 262 chunks excluidos (220 s64 + 42 Morley) · corpus 25.090 intacto** (0 chunks creados/borrados). Bug de instrumento cazado y corregido en el runner: la 1ª lectura paginaba mal (PostgREST max-rows=1000 → contó 1000/1067) — re-medido con paginación, nota en el reporte. **Ventana de freeze CERRADA** (el ciclo A/B→held-out terminó en s63; próximo ciclo de eval = re-freeze con baseline nuevo).
- **Alternativas descartadas**: re-ingestar el MS-416 "actualizado" (sin materia — ver a); solo status sin backfill de identidad de sucesores (dejaba a los 2 docs Detnov fuera del lifecycle para siempre y la cadena sin destino); borrar los chunks viejos (el contrato es exclusión en runtime + auditoría, no destrucción); A/B K=5 completo como guardarraíl (pregunta cero: higiene de datos de un contrato ya existente + lever ya medido en s63 — pools before/after + precheck + smoke es lo proporcional); flag de código nuevo para el fix (el kill-switch real es la reversión de datos: status back sin redeploy); autorar supersede-traps en eval_rag legacy (harness muerto; el ruler vivo ya cubre vía cat024 + C1).
- **Gaps declarados**: el efecto en la CALIDAD de respuesta de cat019/cat024/hp001 no se re-juzgó (se verá en el próximo eval del ruler; la traza completa de pools quedó commiteada); ventana prod entre mutación y deploy del fix = código viejo + datos nuevos → los viejos re-entrables solo como suplemento 0.72 capado a 2 chunks (NO PEOR que hoy, que entran a rank completo); la hipótesis "versión efímera del portal revertida" no es falsable hacia atrás (sin snapshots) — si Detnov re-publica, el SHA-check de la próxima descarga la caza.
- **Relacionado**: TECH_DEBT #46 (✅ cerrado), DEC-044(e) (origen), audit s62 capa C, `scripts/s64_lifecycle46.py` + `scripts/s64_state46.py`, `evals/s64_precheck.yaml`, `evals/s64_pools_{before,after}.json`, `evals/s64_apply_log.yaml`, `evals/s64_lifecycle46_report.yaml`, lección #34 (`feedback_my_bias`: la claim de s63 entró al canon sin verificación reproducible — el SHA-check de hoy la refutó).

## DEC-046 — s65: CAPA B de #43 CERRADA — backfill de identidad de lotes s55/s58 (103 filas + 2.040 chunks al lifecycle) + 86 manufacturer + 80 revisiones + cola needs_review; #43 COMPLETO

- **Fecha**: 12 jun 2026 (s65). **Impacto**: MEDIO (mutación de datos de identidad en prod + 1 fix de runtime colateral; zona de dolor corpus → dúo completo). **Disparador**: PLAN punto 1 (capa B, ciclo de higiene propio post-#46).
- **(a) AUDIT dirigido fresco (Protocolo 4, `scripts/s65_audit_capab.py` → `evals/s65_audit_capab.yaml`)**: corrigió el cuadro colateral del s62 — B2-unknown muerde en documents (203) no en chunks (401=1,6%); el mismatch de manufacturer por EVIDENCIA (doc↔moda de chunks enlazados) es 86, no 17-por-keyword; B6 = 165 filas active sin chunks v2 (90 solo-tabla-vieja + 75 en ninguna; duplicados con/sin `.pdf`); B7 = 2.065 chunks / 112 sources sin fila (lotes s55/s58 + 115 sin marca) — fuera del lifecycle (la regla conservadora X4-s64 nunca los excluye) y sin revisión citable; B4/B5 (language 974 NULL · revision_date 1.066 NULL · family=filename 1.007/1.067) sin consumidor actual → DIFERIDOS a contrato de ingesta (pregunta cero).
- **(b) Dúo sobre el diseño v1 (P3 tiering completo)**: sub-agente FRESCO **13/13 confirmados 0 FP** (F1 CRÍTICO: colisión A1×A4 — RIF_08791 en ambas poblaciones, enlazar+retirar = chunks invisibles → orden A1→recompute→A4 + assert; F3 rollback violaba la FK [DELETE antes de des-enlazar]; F4 UNIQUE(manufacturer,sha) 001:68 → pre-casado por sha; F5 enlace sin `AND document_id IS NULL` re-apuntaría no-huérfanos; F6 moda-de-chunks circular [FS24X] → cross-check canal/sidecar + unanimidad; F7 `distributor` no existe en documents; F8 mi motivación de A2 era falsa — el header del generador no lleva manufacturer, el consumidor real es el catálogo `get_available_manufacturers`; F9 precheck ciego a ENTRADAS por matchabilidad ganada + heap-cache del diversify; F10 firma en ORDEN del pool; F11 poblaciones fuera de artefacto [lección #34] → fase inventory congela; F12 freeze sin contrato roto; F13 residual NOT NULL declarado) + cross-model GPT-5.5 **7/7 con valor 0 FP** (X1: contradicción B4-diferido vs A1-puebla-language por moda — en `_ml` la moda miente → NULL; X2 converge F6; X3 retired≠gap: needs_review para docs reales sin contenido = cola humana; X4 converge F3 [snapshot por fila]; X5 converge F11; X6 notes-como-flag = deuda → status + inventory.yaml; X7 framing). Tally `adversarial_review_log.jsonl` ts 2026-06-12T14:47:20.
- **(c) Ejecución (runner `scripts/s65_capab.py` 6 fases; plan CONGELADO `evals/s65_capab_plan.yaml` = objeto del GO)**: inventory (re-mide y congela; curación canal-"Otros": 6 Aritech + 2 Kidde con evidencia por fila, 8 sources residuales SIN marca demostrable [brand=Otros en el sidecar] — quedan huérfanos honestos, 25 chunks) → before (39 pools embed-cache; afectado esperado: SOLO hp020) → **apply autorizado explícito por Alberto** (546 steps, before-values por fila): A1 103 INSERT + 1 enlace + 2.040 chunks enlazados; A2 85 docs manufacturer (+model si unknown) + excepción MAD565 (8 chunks Spectrex→Detnov: los chunks estaban mal, el doc bien); A3 80 revision→NULL (lista cerrada de 11 valores); A4 90 retired + 74 needs_review (semántica X3) → after **GO**: 38/39 byte-idénticos + hp020 idéntico + invariante A4 PASS → smoke real: 2X-A cita r004/r005/r006 (primera vez que el lote s55 lleva revisión), CAD-201 desde el MI-715 enlazado, AM-8200 estable, catálogo 30 marcas.
- **(d) cat011 — la única violación C3, RESUELTA POR EVIDENCIA HISTÓRICA (no re-litigada a ciegas)**: composición cambió 15→40 con 0 entradas de sources del plan → decisión pre-declarada STOP-instrumento → diagnóstico: el pool s64 (before Y after, pre-s65) era n=40 con SG*=25/VESDA=3 = el after de hoy, estable ×3 re-runs byte-idénticos → **el degradado era el BEFORE de hoy** (n=15, timeouts de los fetches suplementarios, fail-open — patrón documentado s63). Reclasificado dado-de-red-en-before; el A/B de pools NO mide al lever de s65.
- **(e) Colaterales**: (i) falso-STOP del assert global del runner en el 1er apply — exigía "ningún doc inactivo con chunks v2" GLOBAL, pero los 3 superseded s64 + 5 needs_review Morley tienen chunks POR CONTRATO (#46: exclusión en runtime, no des-enlace); verificado que ninguno era de A4 → assert corregido a scope-del-plan + nota de transparencia en `s65_apply_log.yaml` (las mutaciones habían completado TODAS); (ii) **fix de runtime: `get_available_manufacturers` paginado** (retriever.py:721) — pedía limit=5000 pero PostgREST capa a 1000 (misma lección que el fingerprint s64): con 1.170 docs las marcas nuevas eran invisibles al catálogo "Tengo manuales de:" (ya mordía con 1.067); cazado por el smoke F8, fix + 2 tests (`test_available_manufacturers.py`), catálogo 26→30; (iii) `_get_all_known_manufacturers` medida en 2 marcas (200 chunks físicos sin ORDER BY, cache) → TECH_DEBT #47.
- **Alternativas descartadas**: poblar B4/B5 masivo (fabricar metadata sin consumidor — X1 lo confirmó); DELETE de fantasmas/duplicados (contra DEC-045: auditoría, no destrucción); A/B K=5 con juez (desproporcionado para no-regresión de higiene); re-parse de revisión para los 80 B3 (scope-creep — NULL honesto, el parser bueno nace en ingesta); arreglar el ESCRITOR ahora (se diseña junto al contrato de supersesión en ingesta, PLAN punto 2, una sola vez); alinear manufacturer a ciegas chunks→documents (la dirección no es uniforme: MAD565).
- **Gaps declarados**: el escritor sigue vivo (`resolve_document_id` casa sin crear y sin preferir active — contrato F2 al PLAN punto 2); 25 chunks huérfanos residuales (8 sources canal Otros); pools del held-out sin precheck (embargo — se observará en el próximo re-freeze del eval); el efecto en calidad de respuesta no se re-juzgó (no es lever; criterio = no-regresión de pools); B2-documents restante (~165 unknown en docs con chunks) → contrato de ingesta + catálogo.
- **Relacionado**: TECH_DEBT #43 (✅ COMPLETO: A s63 + B s65; capa C marginal absorbida s64), #47 (nuevo), DEC-044/DEC-045 (precedentes), DEC-035 (seam s55 — fuente de la curación), `evals/s65_audit_capab.yaml` · `s65_capab_inventory.yaml` · `s65_capab_plan.yaml` · `s65_pools_{before,after}.json` · `s65_apply_log.yaml` · `s65_capab_report.yaml` · `evals/_s65_capab_design.md` (v2, local), lecciones #33/#34 aplicadas (vigencia por contenido; claims con evidencia reproducible).

## DEC-047 — s66: re-gate del lever CE = GO con scope RE-DECIDIDO a CE-PURO (sin L-i); falso-STOP de cat018 enmendado pre-paso-B; A/B fijado para s67

- **Fecha**: 12 jun 2026 (s66). **Impacto**: MEDIO-ALTO (re-scope de un lever preservado + gate que habilita el A/B del reranker de prod; zona de dolor retrieval/eval → dúo completo). **Disparador**: PLAN punto 1 (revisita condicional DEC-042e — condición cumplida: #43 COMPLETO tras s63/s64/s65).
- **(a) SCOPE re-decidido (Alberto, 4 opciones en la mesa — precedente X4-s60: la premisa del lever preservado cambió):** el lever s61 era el paquete {L-i + ef120 + CE}; lo revisitado en s66 es **CE-PURO** — swap del reranker tras flag (`RERANKER_BACKEND=voyage`, dispatch Y1: CE solo SIN `target_models`) sobre el retriever de main INTACTO. Motivos verificados: (i) el upside que L-i demostró (hp001 s59) quedó frontera-de-pool (DEC-042d) **y s64 devolvió sus hechos al pool SIN L-i** (F1 del dúo — ver b); (ii) cat012 capturado río arriba por el filtro de series (DEC-044); (iii) L-i re-baraja pools (churn 24/39 @ef40, cifra LIMPIA — F5: el 35/39 de s61 era del paquete, dominado por el CE) = re-comprar el riesgo regla-1 de s59 sin upside pendiente; (iv) `retriever.py` divergió +315 líneas (zona caliente s63/s64). **L-i ARCHIVADO no borrado**: causa raíz canonizada (DEC-040), branch `s59-lever-code-ROLLBACKED` vivo, renace en el ciclo futuro profundidad-del-canal (mecanismo rank 51-70, 4× medido). Alternativas descartadas: paquete fiel (riesgo+trabajo sin upside); re-gate sin build con CE de main content-pelado (mediría lo que no se shipea — viola Y1); archivar sin gate (X5 — legítima pero renuncia a evidencia post-s63 con el dado del LLM vivo como defecto de prod).
- **(b) Dúo r1 FRESCO sobre el diseño v1 (P3 tiering completo)**: sub-agente **8/8 confirmados 0 FP** (F1 ALTA: la premisa "hp001 irrecuperable, hoy fuera de pool" estaba REFUTADA por s64 — `s64_precheck.yaml` candado/2222 en el sucesor MC-380-c y `s64_lifecycle46_report.yaml` sucesor EN pool; mi diseño citaba "C3 36/36 s64" sin notar que ese conteo EXCLUYE a hp001 por afectado → branch pre-registrada + techo condicional; F2 ALTA: D2′ sin paridad-de-pool reconstruía el falso-culpable de s61 → pre-check y atribución extendidos; F3: STOP E3 añadido [precedente DEC-044d]; F4: cat015 indecidible con referencia muestreada → regla de unión + escalada, nunca silencio; F5: cifra churn corregida; F6: cualificador Y1 visible en el caso de ship; F7: flag legacy `RERANKER` vivo en main → a la lista de transplante; F8: calibración $0 de la vía-1 nueva) + cross-model GPT-5.5 **5/5 con valor 0 FP** (X1 CRÍTICO: anclas de cat018 = 50% del criterio D2′ sin listar → extraídas del gold_store y verificadas contra el sustento real ANTES de cualquier retrieve [la candidata "apendice a" dio 0 hits = infalsable — el pre-check validó el principio]; X2: cláusula de VENTANA del GO [fingerprints gate→A/B idénticos o re-gate]; X3: D2′ endurecido — en s61 eran ganancias-candidatas ["ambos perdidos"], hoy son SHIP de prod → UNA pérdida ATRIBUIBLE = NO-GO; X4: coste real ~$5-6, el "~$2" del PLAN heredaba la subestimación s61; X5: archivar-sin-gate como opción). Tally `adversarial_review_log.jsonl` ts 2026-06-12T16:53:29.
- **(c) Build (rama `eval/s66-ce-regate`, commit 8112bd6)**: transplante limpio desde `s61-lever-code-ROLLBACKED` (verificado: main no tocó esos archivos desde el merge-base 3730f16) — `reranker.py` (header de paridad 2.0 + dispatch Y1 + strict + provenance) · `config.py` (flag) · `telegram_bot.py` (dispatcher) · tests del dispatcher · retirada del flag legacy de `test_bot_vs_gold.py`. **SIN `retriever.py`** (L-i fuera). 290 tests verdes. Instrumento `scripts/s66_gate.py` (5 fases reanudables) + probes congeladas pre-paso-A.
- **(d) GATE (paso A limpio: ef=120, corpus 25.090, lifecycle s65 {998/79/90/3}, 262 excluidos, registry fingerprint 0bd1d3e979dc5147; pools frescos cuadran canon: cat012=9, cat024=7, hp001=26):** el precheck pre-paso-B disparó **STOP-D2 en cat018** (h2/h3 fuera del pool fresco) — freno pre-registrado correcto, $0 gastados → diagnóstico regla-C: **el PASS vigente s63 se sostuvo con h1+h4 SOLAMENTE** (h2/h3 JAMÁS en pool ni vista del s63 — `s63treat_frozen_contexts.json` + `s63_gate_pools_treatment.json`; pool fresco equivalente 16/16 source-page keys) = **falso-STOP por anclas sobre-especificadas del autor** (el probe debe proteger lo que el SHIP SIRVE, no los 4 atomic_facts del gold) → **enmienda pre-paso-B APROBADA por Alberto explícito** (condición=h1+h4; h2/h3 informativas; paralelo: enmienda de instrumento pre-juez DEC-044d). De regalo el diagnóstico re-confirmó el mecanismo DEC-044 (el control s63 servía el manual del N — 0/4 hechos).
- **(e) RESULTADO (paso B ~$4.5 real: 105 LLM + 77 CE; commit 8a6088d): VEREDICTO GO pre-registrado.** **D1 6/6** unánimes retienen sustento (vía-1 overlap 4-5/3 contra la vista LLM-modal ACTUAL — la referencia frozen-s58 se declaró muerta: el corpus efectivo cambió s64/s65 — Y vía-2 anclas completas); **D2′ 0 pérdidas atribuibles** (cat012 4/4 hechos en pool∧ambas-vistas — en s61 el CE perdía h2/h3 por los hermanos: **el cierre río-arriba de s63 queda CONFIRMADO empíricamente bajo CE**; cat018 h1+h4 retenidos); **instrumento limpio** (CE determinista 39/39, orden-insensible 7/7 críticos con pool>5, 0 chunks sub-0.4 en top-5 CE → nada de lo que sube se lo come el filtro del generador; corte-a-50 activo solo 3/39). hp001 INFORMATIVA por branch ('candado' en pool y AMBAS vistas; '2222' fuera — frontera de pool re-confirmada con matiz: ya no falta el doc, falta el chunk p20). **Dado del LLM re-medido hoy: 12/39 votos no-unánimes** (cat018/hp014 a 1/1/1) — el defecto de producto del statu-quo, cuantificado fresco. Latencias: CE p50 0.43/p95 0.84s vs LLM p50 2.06/p95 2.86s. **El GO habilita pero NO autoriza el A/B (DEC-016b). Branch de Alberto (3 opciones): A/B en s67** — mini-diseño propio (pairing por vista-del-generador idéntica; shadow-rerank sin rol bajo mismo-pool) + dúo fresco + re-freeze del baseline (pendiente de todos modos) + brazo CE K=5; criterio §3-v4 + F7-endurecida (GRIS-estable → recomendación pre-escrita SHIP-por-estabilidad, beneficio NO-end-to-end, solo path sin-target_models); ventana X2 = fingerprints de `s66_gate_report.yaml:meta` idénticos al arrancar o re-gate ~$5; coste ~$40-60 (marginal CE ~$20-30); techo end-to-end honesto ~+0/+1-frágil.
- **Sin tocar prod**: rama sin mergear al cierre (PR de s66); aún tras merge el dispatcher queda default `llm` = comportamiento idéntico (el swap real exige `RERANKER_BACKEND=voyage` en Railway tras A/B+held-out). Corpus 25.090 intacto; ventana DB ef=120 default mantener.
- **Relacionado**: DEC-042e (la revisita pactada) + DEC-042d (mecanismos hp001/cat012), DEC-044 (el filtro que cerró cat012 + enmienda-de-instrumento precedente), DEC-045/046 (los cambios de corpus que mataron la referencia s58), DEC-016b (gate habilita ≠ autoriza), DEC-043c (mismo-pool por par; regla-C en diagnósticos), cláusula R (el held-out solo tras SHIP en dev), lección #35 (`feedback_my_bias`: una conclusión MEDIDA también caduca si el sustrato cambia después — verificar contra los artefactos POSTERIORES al antecedente), `evals/s66_gate_{probes,calibracion,precheck,report}.yaml` + `s66_gate_{pools,reranks}.json` + `evals/_s66_ce_regate_design.md` (v2.1, local), branch `eval/s66-ce-regate` (commits 8112bd6 + 8a6088d).

## DEC-048 — s67: A/B del swap CE = ROLLBACK pre-registrado → lever CE ARCHIVADO con evidencia; re-freeze `s67base` = baseline nuevo del ruler; embed-cache = pin de embeddings de los ciclos de eval

- **Fecha**: 12 jun 2026 (s67). **Impacto**: ALTO (veredicto sobre el reranker de prod + baseline nuevo del ruler; zona de dolor eval/retrieval → dúo completo). **Disparador**: PLAN punto 1 (A/B habilitado por el GO s66, DEC-047; rumbo autorizado por Alberto; GASTO autorizado por Alberto sobre el diseño v2 post-dúo, conforme DEC-016b).
- **(a) Decisión principal — ROLLBACK del swap `RERANKER_BACKEND=voyage` y ARCHIVO del lever CE.** La tabla pre-registrada (transferida §7-s61, listón intocado) disparó por DOS condiciones independientes: **F_post 8 > F_base 5** (cat007/cat017/hp001/hp014 PARCIAL→FALLO; cat017/hp014 con dado-plausible, **hp001 atribuible-operacional** — el gold-frontera pierde su PARCIAL bajo CE) y **conducta ≥2** (cat016/hp014 answer→admit; hipótesis mecanística DECLARADA no canonizada: la vista CE pierde el chunk que sostenía la respuesta parcial y el generador, correctamente, admite). Δ_net=0 (techo +0/+1-frágil de s66 CONFIRMADO; cat012 — el SHIP s63 — GANA PARCIAL→PASS bajo CE pero 3/5 sin la guardia de margen ≥4/5: se lista, no cuenta — coherente con su 4/4 del gate); SIN regla-1 (cero PASS perdidos atribuibles; cat023 única caída de PASS = dado-excluido, control=1 dentro del límite); Δ_inest=0; instrumento limpio (juez servido idéntico entre brazos `gpt-5.5-2026-04-23`, 370 generaciones + 370 juicios '?'=0, asserts verdes). **El caso NO-end-to-end del CE (determinismo vs dado 11/39, latencia rerank p95 0.81s vs 3.29s, coste ~15×) no se compra al precio de degradar la cola PARCIAL→FALLO** — la F7-endurecida nunca aplicó (el desenlace no fue GRIS). El dado del rerank LLM queda como defecto de producto DECLARADO; su vía futura es el ciclo profundidad-del-canal (rank 51-70 4× medido DEC-042d; ahí renace L-i), no este swap. Flag default `llm` (inerte) + dispatcher + manifest honesto de bvg quedan como INSTRUMENTOS permanentes.
- **(b) Baseline del ruler RE-FREEZADO (valor no condicionado, pre-registrado §2 del diseño):** `s67base` (LLM K=5, 39 dev, 12 jun 2026) **sustituye a frozen-s58** (referencia muerta desde s64/s65): 10/39 PASS-control (cat005/cat010/cat014/cat015/cat018/cat022/cat023/hp015/hp019/hp020; 5 unánimes 5/5) · 4 K-INESTABLES (cat009/cat012/hp004/hp007) · residual 25 con atribución (9 INDETERMINADO-solo-débiles · 5 SUB-RETRIEVAL · 4 GENERACION · 4 MIXTO · 3 CUALITATIVA) · stop_reasons sanos (0 max_tokens). Manifest completo `s67base_run_manifest.json`.
- **(c) Embed-cache como PIN de embeddings del ciclo (estructural, nace del STOP):** el assert (i) del A/B cazó **embed-drift server-side** entre el gate (17:10) y los freezes (3/39 pools frontera, 1 chunk in/out — DEC-042d vivo) ANTES de pagar generación → re-gate ~$5 con `EMBED_CACHE_PATH=evals/s67_embed_cache.json` COMPARTIDO y `GATE_RUN_ID` parametrizado en `s66_gate.py` (artefactos `s67_gate_*`, probes congeladas s66 intactas como input) = **GO** (D1 0 fail-both · D2′ 0 pérdidas · CE determinista · swap 35 distintos). **El cache ancla gate y A/B a la MISMA ventana de vectores POR CONSTRUCCIÓN — todo freeze/gate futuro corre con `EMBED_CACHE_PATH` (el riesgo "pools de sesiones distintas" muere estructuralmente, no por suerte).** Colateral medido: la firma F1 con `round(sim,2)` cruza fronteras de redondeo con drift de 0.001 (cat019: misma vista, header con un dígito distinto → firma distinta) — comportamiento FIEL al header real del generador, declarado, no bug.
- **(d) Dúo r1 FRESCO sobre el diseño v1 (P3 tiering completo, 13/13 confirmados 0 FP, tally en log ts 2026-06-12T18:20:46 [+r1sub])**: sub-agente **7/7** (F1 ALTA: hueco dado-mediado — freeze-A es tirada NUEVA posterior a los votos del gate; en un gold gate-unánime puede ser 4ª-vista y un mover ahí es dado del brazo VIEJO → dado-plausible := no-unánime-gate ∨ firma(freeze-A)∉vistas-gate, computable $0 de `llm_top5_all`, + STOP sistémico ≥9/35; F2: el dado RE-DERIVADO del artefacto = **11/39 no-unánimes** [9× 2/1 + 2× 1/1/1; 24 unánimes rerankeados + 4 short-circuit vacuos] — el "12/39" del PLAN:47 era FALSO, patrón bias #35 [heredar cifra canonizada sin re-derivar], corregido en PLAN al cierre; F3: pool==gate era esperanza inter-sesión [el gate corrió SIN cache] y la secuencia v1 pagaba gen-A antes del assert → día D reordenado [el STOP real del día D validó EXACTAMENTE esto]; F4: drift del juez ENTRE brazos no cubierto → assert `judge_model_real` idéntico; F5: `phase_report` ignora `--qids` → herencia explícita generations+judgments base→ce con `shared_from` para los paired [sin ella: JUDGE-ERROR contaminando partición y Δ_inest]; F6: la rama regla-1-context-idéntico queda VACUA bajo pairing — la protección de los context-idénticos ES el pairing Δ:=0; F7: 4 short-circuit [no 1] y el churn fresco se cita del artefacto s66 [swap_aislado n_distintos=35]) + cross-model GPT-5.5 **6/6** (X1: freeze-contract partido — el x2_check con exit-0 no cubría drift del CÓDIGO del instrumento → ampliado con `--code-baseline` falla-cerrado + working-tree limpio en paths materiales; X2: "mismo-pool por construcción" sobre-afirmado → asserts verificables [su remedio inyectar-pool-materializado DESCARTADO razonado: tocaría el instrumento canónico bvg]; X3: assert CE==gate como verificación con semántica de fallo, no necesidad lógica [mecánica verificada: el CE devuelve los dicts del pool con la similarity del RETRIEVE intacta — `reranker.py:237` — el filtro 0.4 y la firma operan sobre el mismo campo en ambos brazos]; X4: "atribuible-operacional bajo n=3+1" con residual declarado; X5: retención-del-gate = proxy presencia-en-vista, NO end-to-end; X6: brazo B freeze-only antes del assert). Convergencia X2/X6↔F3 = señal fuerte; regla C aplicada a todos los claims (recuentos re-derivados, líneas verificadas).
- **(e) Build (rama `eval/s67-ab-ce`)**: manifest honesto de bvg **re-aplicado A MANO sobre main** (los 4 bloques de `s61-lever-code-ROLLBACKED`: imports dispatcher, `_assert_rerank_provenance` [llm-padded aceptado y avisado solo en llm; short-circuit en ambos; fail-open NUNCA], freeze vía `rerank(strict=True)`, manifest con backend/modelo/SHA DESPACHADOS] preservando lo que main ganó después [lifecycle-fingerprint s64, cláusula R held-out, bloque series_registry s63, embed_cache_path] — un checkout del archivo habría PISADO esos 4; diff residual verificado = solo-lo-de-main) + `scripts/s67_ab.py` (asserts (0) pool50 entre brazos / (i) vista-CE==gate / (ii) freeze-A∈vistas-gate / (iii) juez idéntico; pairing F1; herencia; clasificación de movers A2-enmendada; Δ_net con margen; tabla; report) + `s67_x2_check.py` ampliado X1 + test provenance (10 casos). 300 tests verdes. Coste real sesión ~$30 (gate $5 + brazo A ~$15 + brazo B ~$10) vs estimación $40-60 — el pairing ahorró poco (4/39, los SC) como se declaró.
- **Alternativas descartadas**: SHIP-por-estabilidad vía F7 (no aplicó: el desenlace no fue GRIS — F_post y conducta dispararon ROLLBACK; absorber eso habría sido re-litigar la tabla post-datos); re-gate parcial solo-golds-driftados (frankenstein de fingerprints — el gate es UN artefacto con UN manifest); absorber el STOP del assert (i) como "drift benigno" sin re-gate (patrón bias #32/#34: el falso-culpable se decide con evidencia, no con juicio post-hoc — y 1 de los 2 fallos [cat008] era vista materialmente distinta); inyectar el pool materializado del brazo A al B (X2 cross-model — tocaría bvg, el instrumento canónico de la serie); held-out (cláusula R: solo aplicaba si SHIP).
- **Gaps declarados**: el baseline-freeze es 1 tirada del dado LLM (mitigado por A2+clasificación, residual declarado); "atribuible-operacional" acota con n=3+1, no demuestra (X4); la conducta-regresión de cat016 es FALLO→FALLO con cambio de conducta (de respuesta-mala a admisión — la tabla la cuenta como regresión por contrato conducta_esperada=answer; discutible para el usuario final, declarado); corte-a-50 + filtro-0.4 intocados (gap heredado); el drift del juez vs s58 sigue sin pin de pesos (limitación de todo el ciclo); los 25 huérfanos + #47 siguen vivos (PLAN punto 2).
- **Relacionado**: DEC-047 (el GO que habilitó), DEC-016b (habilita ≠ autoriza — el GASTO lo autorizó Alberto sobre el v2), DEC-042d (el embed-drift y el mecanismo rank 51-70), DEC-043c (mismo-pool por par; regla-C en diagnósticos), DEC-044/045/046 (los SHIPs que el A/B re-confirmó río abajo: cat012 retiene su mecanismo bajo ambos backends), cláusula R (intacta), lecciones #35 (F2: cifra heredada sin re-derivar) y #13-#34 (el dúo cazó 13/13 pre-datos), `evals/s67_ab_report.yaml` · `s67_pairing.yaml` · `s67_gate_{pools,reranks,report,precheck,calibracion}` · `s67base_*`/`s67ce_*` (manifests completos) · `s67_embed_cache.json` (el pin) · `evals/_s67_ab_design.md` (v2, local) · `evals/adversarial_review_log.jsonl` ts 2026-06-12T18:20:46 · commits 4ad4079/657c7b2/76020d8 · rama `eval/s67-ab-ce`.

## DEC-049 — s67b: re-priorización del roadmap post-A/B — canal vectorial PRIMERO; corpus DIFERIDO demand-driven (decisión de negocio); diagramas partidos en datos∥cableado

- **Fecha**: 12 jun 2026 (s67b, conversación de rumbo post-merge del PR #75). **Impacto**: MEDIO-ALTO (re-ordena el "Qué sigue" canónico del PLAN). **Disparador**: pregunta de Alberto ("¿qué nos queda por probar? me da la sensación de que estamos muy lejos") → assessment con datos del canon → propuesta de Alberto confirmada con matices. Decisión de PRIORIDAD (negocio + evidencia), no de diseño: cada ciclo que nace de aquí lleva su propio audit/dúo (el dúo NO se corrió para esta DEC — se correrá sobre los DISEÑOS de cada ciclo).
- **(a) Corpus: DIFERIDO demand-driven hasta chatbot estable/robusto (decisión de NEGOCIO de Alberto).** "Las marcas que tenemos ahora son las que utilizan los técnicos con más frecuencia; no quiero añadir fabricantes o productos por el mero hecho de añadirlos." **La meta 30+ fabricantes SIGUE VIVA — fase posterior** ("no en esta fase, no hasta tener un chatbot estable, robusto, que funcione bien"). El dato técnico la apoya: el residual del ruler (25 golds) tiene solo ~3 corpus-gaps medidos — está dominado por sub-retrieval/indeterminados/generación, no por falta de documentos (1.170 docs / 998 active / 31 marcas / 587 modelos). Mecanismo de reactivación: gap REAL detectado en conversaciones (Excel `data/Inventario_Manuales.xlsx`) → entonces aplican los prerrequisitos ya definidos (contrato del escritor #44 + #45 + identidad/supersesión en ingesta DEC-045a + cola 74 needs_review).
- **(b) Canal vectorial = ciclo prioritario (s68+).** Intuición de Alberto ("el elefante en la habitación; antes de implementar un CE deberíamos arreglar el canal vectorial") CONFIRMADA por 4 datos del canon: canal principal devuelve 0 en ~85% de queries (category muerta desde s44, DEC-040) · el embedding SÍ encuentra los hechos (rank 7-110, s59) · hechos en rank 51-70 medidos 4× (DEC-042d) · corte-a-50 muerde 9/39 (s61); + la lección de 3 ciclos de reranker = 0 upside (s59/s61/s66-s67): un reranker reordena lo que entra — no rescata lo que NO entra al pool. **Audit de dimensionamiento PRIMERO** (Protocolo 4; instrumentos existentes: funnel s58b + diagnosis-ranks s59 + atribución s67base) con la pregunta de Alberto sobre CHUNKS integrada como pregunta (b) pre-registrada: cuánto del residual es canal (río arriba) vs calidad-de-chunk (extracción #10 — los 9 INDETERMINADO-solo-débiles); si domina chunk-quality, el techo del canal baja y se sabe ANTES de construir. Levers candidatos (orden lo da el audit): #44 category-como-BOOST (no filtro duro — frágil medido; incluye contrato del ESCRITOR `reingest/metadata.py`) · L-i renacido (`s59-lever-code-ROLLBACKED`) · profundidad/corte. Riesgo declarado: redistribución de frontera (regla-1, s59) — mitigada con la maquinaria s67 (paridad-control, clasificación de dado, embed-cache pin, baseline s67base).
- **(c) Orden post-canal:** re-gate CE ~$5 SOLO si el canal cambia los pools (puerta DEC-048; sin promesa de revival — el CE perdió la cola con paridad completa de información) → A/B 2×2 generación {Sonnet/Opus}×{blurb} (pre-registrado s56) sobre el freeze post-canal → **cartera de levers, cada uno por gate/audit barato (DEC-016b)**: system prompt del generador (no probado) · prompt del rerank-LLM (vs dado 11/39) · k/corte. No se pre-supone el orden interno.
- **(d) Diagramas (#45) PARTIDOS:** los diagramas apuntan a la tabla VIEJA (44.035 chunks con `has_diagram` allí vs **0/25.090 en chunks_v2** — nunca se extrajeron para v2, DEC-041); el mapeo chunk-a-chunk NO existe (chunking distinto) pero no hace falta: el diagrama pertenece a **(documento, página)**. (d1) **DATOS — paralelizable desde ya** en sesiones sueltas: mapeo por (doc, página) + extracción de faltantes + poblar metadata en v2; **eval-inerte VERIFICADO por contrato** (el retriever no lee esas columnas; before/after de pools por backfill OBLIGATORIO porque el corpus_fingerprint NO detecta edits in-place, DEC-036e). (d2) **CABLEADO de entrega post-canal**: adjuntar diagramas exige chunks confiables primero (si no, se adjunta el diagrama del chunk equivocado — el punto de Alberto).
- **(e) Dureza de la tabla de decisión: DIFERIDO con marco.** Alberto: "igual tenemos que replantearnos cambiar las reglas o rebajar su dureza — analizarlo más adelante." Marco pre-acordado para cuando toque: cualquier cambio del listón se hace PRE-REGISTRADO y motivado por evidencia (p.ej. "regla-1 a votos 3-2 castiga ruido del juez, medido"), NUNCA post-hoc para dejar pasar un lever; las válvulas existentes (dado-plausible s67, enmienda-de-instrumento con evidencia + Alberto s66/DEC-044d) ya absorben dureza legítima.
- **Alternativas descartadas**: ingesta ahora (completismo sin demanda; solo ~3 corpus-gaps en el residual; coste de oportunidad vs el canal); CE antes del canal (re-compraría lo medido en s67 sobre el mismo sustrato); diagramas antes del canal (adjuntaría diagramas de chunks equivocados; además su mitad de datos NO necesita esperar — se paraleliza); empezar por generación (retrieval domina el residual y el 2×2 sobre contexts pre-canal quedaría stale al cambiar los pools).
- **Gaps declarados**: el techo del canal NO está dimensionado (el audit es el paso 0 exactamente por eso); el ruler adversarial sub-mide ganancias de robustez (la mejora percibida por técnicos reales puede superar el delta de PASS); los 9 indeterminados-solo-débiles pueden resultar NO-canal (extracción) → re-priorización honesta si el audit lo dice; expectativa calibrada: upside conocido ≈ 5-9 golds + estabilidad, no una revolución del marcador.
- **Relacionado**: DEC-048 (el ROLLBACK que cierra el ciclo CE), DEC-040/041/042d (los datos del canal/diagramas/ranks), DEC-016b (gate habilita ≠ autoriza), DEC-036e (fingerprint ciego a edits in-place → before/after obligatorio en backfills), DEC-045a (prerrequisitos de la ingesta futura), TECH_DEBT #44/#45/#10/#40/#47, PLAN "Qué sigue" re-escrito (este es el cambio canónico), fases macro F1-F5 (F5 técnicos reales post 1-sept — el reloj de fondo de esta priorización).

## DEC-050 — s68 (autónoma nocturna): ciclo del canal ejecutado — audit por-hecho (stamps expulsan del pool) · lever MERGE+L-i′ gate-0 = NO-GO pre-registrado (mecanismo y conversión CONFIRMADOS; colateral inaceptable) · chunk-quality DESCARTADA con dato

- **Fecha**: 12-13 jun 2026 (s68). **Impacto**: ALTO (veredicto sobre el lever prioritario del PLAN + re-secuenciación del roadmap; zona de dolor retrieval → dúo completo). **Disparador**: DEC-049b punto 1; mandato de autonomía nocturna de Alberto (GO explícito, techo $100 de spend, "iterar y buscar soluciones sin pedir validación") — límites auto-impuestos y cumplidos: prod y held-out INTOCABLES, celdas-de-Alberto documentadas no decididas, todo en rama+PR. Gasto real ~$7.
- **(a) AUDIT del canal (paso 0 pre-registrado):** sobre el baseline s67base (sufficiency D3 per-hecho + pools congelados + embed-cache pin), 22 golds residual-answer / 28 hechos fuertes. Resultado que RE-DIMENSIONA el ciclo: profundidad casi sin materia (rank 51-110 = 2 hechos: hp001[54]/hp011[65]); **el cuello real = la mezcla del pool: 10 hechos que el canal vectorial SANO rankea ≤50 expulsados del pool-50 servido por los keyword-stamps planos** (0.80 keyword `:1059` · 0.85 boosts · 0.72 suplementos-lifecycle; dedup keyword-first que PISA el coseno `:1092-1104` + sort global por similarity `:1106`; el canal de prod además capado a broad-5 porque el principal filtra por category→0 filas en ~85%, re-verificado: 0 chunks con categoría canónica HOY). 11 hechos ya-servidos-que-fallan + 9 golds solo-débiles + 3 sospecha-gap completan el mapa.
- **(b) Lever MERGE+L-i′ (plan-B s60 revivido) → gate-0 NO-GO:** diseño v6.1 (hereda v4-s60; delta de sustrato verificado: V-B muerta por filtro-0.4 [posterior a s60], V-C muerta por DEC-048, (d2) muerta [F6: sustituía el interleave-por-source del 5a — intocable, consenso s59×2], L-i′ = réplica EXACTA s59 [F3], hp001/hp011 fuera del techo [F7: k=50], banda de dado en m7 [F1], rama 3c-i pre-registrada ANTES de medir [Y1 CRÍTICO — pre-check: 0 filas → eliminadas]). Dúo r1 completo 18/18 confirmados 0 FP. Build tras flag `MERGE_STRATEGY` default `stamps` (paridad end-to-end 39/39 verificada; 310 tests). **Gate-0: lo que el lever PROMETE, lo cumple** — captura-pool cosine 12/12 alcanzables (quota 7/12: los 36 stamps de hp008 no dejan slots a la composición), **conversión m6 cosine 10/12 al top-5 modal (hp008 4/4)** — la objeción histórica "recall no convierte" (#32) NO aplicó: el material expulsado ES lo que el reranker elige cuando lo ve. **PERO el colateral medido es inaceptable: 9/10 (cosine) y 8/10 (quota) PASS-control con top-5 modal FUERA de la banda de dado, con re-barajado profundo** (cat022-quota 0/5 — su PASS vive de 4×0.85; cat010-cosine 2/5). Con el precedente s59 (3 unánimes cambiados → 1 caída → ROLLBACK), pagar el A/B con 9/10 perturbados = ROLLBACK casi seguro → **NO-GO por la letra; el A/B no se paga** (DEC-016b: el gate existe para no comprar A/Bs sin mecanismo O con colateral evidente; el prior DEC-041(A) quedó CONFIRMADO y estaba declarado pre-gasto).
- **(c) Chunk-quality DESCARTADA como cuello (bloque-2, $0):** los chunks del top-5 en los 11 ya-servidos-que-fallan y los 9 solo-débiles están SANOS (lens 1.1-3.1K · 0 fragmentos · 100% con blurb contextual · content_type coherente · legibles — único atípico: cat020 muestra pantalla-de-panel, que ES el contenido real del manual). ⇒ la pregunta de Alberto (s67b: "¿mejorar los chunks ayudaría al retrieval?") tiene respuesta medida: NO como lever — **el ~50% no-retrieval del residual es GENERACIÓN/síntesis** (el material llega completo; la respuesta no lo integra). Lever #10 (extracción) al fondo del backlog.
- **(d) Consecuencias en el PLAN (re-secuenciación por evidencia, dentro del orden DEC-049):** GENERACIÓN sube a punto 1 (2×2 {Sonnet/Opus}×{blurb} pre-registrado s56, válido sobre s67base — el canal no cambió; system prompt del generador [no probado, diana = los 11 servidos-que-fallan]; prompt del rerank-LLM [dado 11/39 + hp018: su hecho estaba EN pool y el rerank no lo sube ni con pool sano]). Retrieval río-arriba queda como punto 2 CON decisión de Alberto: **candidata ADITIVA del merge declarada con forking-path explícito** (stamps intactos + cosenos del canal sano SOLO en slots libres — nació de mirar el gate-0; exige ciclo propio con dúo y pre-registro; las configs congeladas v6.1 MURIERON por anti-tuning y no se re-tunean) · profundidad k>50 (lever separado) · #44 category-como-BOOST. Re-gate del CE: SIN MATERIA (pools de prod intactos).
- **Alternativas descartadas**: pagar el A/B pese al m7 (violaría la letra pre-registrada y el precedente s59 lo hace ROLLBACK-casi-seguro; $25-30 ahorrados); re-tunear una 3ª variante esta noche (anti-tuning explícito del diseño: "si su config falla el gate-0, la variante MUERE"; la aditiva queda DECLARADA, no corrida); relajar m7 post-datos (el modo de fallo exacto que el pre-registro previene); seguir con el A/B de generación esta misma noche (decisión de secuencia que corresponde a Alberto con el mapa nuevo delante).
- **Gaps declarados**: el gate-0 es proxy (sin juez) — "9/10 perturbados ⇒ ROLLBACK" es inferencia del precedente s59, no medición end-to-end (declarada como tal); la banda de dado n=3 es heurística-parcial (Y4); la candidata aditiva lleva forking-path (mirada post-datos); los 3 sospecha-gap mantienen la semántica del instrumento s58 (docs objetivo, no corpus-wide); m7 ancla en 10 PASS-control (endurecimiento vs los 6 unánimes del v4, declarado en F1).
- **Relacionado**: DEC-049 (el orden que esto ejecuta), DEC-048 (baseline s67base + embed-cache pin — la maquinaria que hizo el audit barato), DEC-041 (el lever s60 y su prior), DEC-040 (causa raíz L-i), DEC-016b (gate habilita ≠ SHIP; proxy puede prometer lo que el end-to-end desmiente — esta vez el proxy mismo paró), lección #32 ("recall no convierte" — medida y esta vez REFUTADA en m6), `evals/s68_audit_canal.yaml` · `s68_gate0_{pools,poollevel,reranks,report}` · `evals/_s68_merge_design.md` (v6.1, local) · `adversarial_review_log.jsonl` ts 2026-06-12T23:50:05 [+r1sub] · commits 3fa70b2/ca560b7/b5be528/b224fc4 · rama `eval/s68-audit-canal`.

## DEC-051 — s69: A/B del lever de GENERACIÓN = NO-GO; cierra la fase de levers-baratos del eval; pivote a producto/deploy

- **Fecha**: 13 jun 2026 (s69). **Impacto**: ALTO (veredicto sobre el lever de generación + cierre de una fase de roadmap + re-dirección estratégica; zona de dolor eval/generación → dúo completo ×2 rondas + 2 cortes cross-model). **Disparador**: PLAN punto 1 (generación, tras el NO-GO del canal s68); GO de Alberto al A/B.
- **(a) Veredicto: NO-GO — el lever fidelity NO se shippea.** A/B (`s69fid` variant=fidelity vs `s67base` re-juzgado en la misma tanda): **Δ_net=0 — ningún gold de la diana flipeó a PASS; la predicción §4 (cat019/hp005/hp014/cat020 deberían mover) FALSADA** · +1 regresión de conducta (cat011 clarify→answer) · verbosidad en 3 PASS-control (+95-135 tokens, proxy C4). Por la tabla: no-SHIP (Δ_net<+2) + colateral real = NO-GO. Flag `GENERATOR_PROMPT_VARIANT` queda default `base` (inerte, prod intacto). **NO se salta a Opus** (anti-racionalización §4: el prompt-completitud falló, no es prueba de que la capacidad sea el cuello; cat008 [termómetro] no movió, pero tampoco los de omisión = el prompt falló, no el modelo).
- **(b) La verificación content-level (enmienda B del dúo) PAGÓ — y es la lección operativa.** El Δ_net=0 del juez, SOLO, habría dicho "lever inerte". Leyendo las respuestas: el prompt NO fue inerte — **hp014 añadió FET=20 y el límite normativo 32** (más completo) sin flipear modal; cat020/cat019 ganaron votos PASS; PERO cat011 pasó de preguntar "¿cuál de los 751?" (clarify) a "El modelo correcto es SDX-751" (answer) = rompió clarify. Cuadro real = **efecto modesto + colateral**, no inercia. La enmienda B (no auto-aplicar el veredicto del juez; verificar content-level los flips decisivos antes de SHIP/rollback) es el bias #20 aplicado a la DECISIÓN y evitó una lectura falsa.
- **(c) Bias #20 reincidente en 2 CAPAS — la diana costó 4 audits (lección a `feedback_my_bias` #36).** v1: diana=12 (auto-etiquetar generación sin verificar material servido). r1 lo cazó. v2: diana=8 vía un re-audit que clasificó por el RELATO DEL JUEZ, no a nivel de contenido = **el re-audit ERA bias #20 en capa más sutil**. r2 lo cazó (cross-model + sub-agente convergentes). Cerrado solo con el **re-audit a nivel de CONTENIDO** (`s69_content_reaudit.yaml`): diana VERIFICADA = 4 sólida (cat008/cat020/hp005/hp014, hecho-fuerte servido) + 1 recuperada (cat019, content-verificada) + 1 parcial (hp017). Lección: hacer un audit para CORREGIR un sesgo puede COMETERLO si verifica al nivel equivocado (narrativa vs contenido). El cross-model fue el corte consistente; el sub-agente Opus (mismo modelo que el autor) compartió el blind spot en r1 y lo cazó en r2 leyendo el propio canon (DECISIONS:854).
- **(d) Hallazgo del re-judge: ±2 de varianza del juez.** Re-juzgar las MISMAS generaciones base dio F 5→7 (vs el report s67base original). El juez GPT-5.5 K-mayoría tiene ~±2 de ruido en F sobre respuestas idénticas. SHIP exige Δ_net≥+2 = JUSTO el suelo de ruido → el ruler actual no distingue fiable un win de +1/+2. Implica: (i) las "+1 FALLO" de un lever son ruido; (ii) endurecer el ruler (dual-judge, s47§D) es prerrequisito de MÁS lever-work.
- **(e) Re-dirección estratégica (la decisión de rumbo que Alberto pidió, "planea como proceder").** 3 ciclos de lever barato (s67 CE ROLLBACK · s68 canal NO-GO · s69 generación NO-GO), 3 negativos. El residual está mapeado/desmenuzado y el ruler tiene ±2 de ruido. **Conclusión: la fase de exprimir-el-residual-con-levers-baratos está agotada** (valor marginal del 4º micro-lever bajo). **PIVOTE: del eval → a producto/deploy para los técnicos de ~sept** (#45 diagramas-datos como feature visible + fix de `available_models` [bug pre-existente que el cross-model cazó: `models_context` contradice la regla clarify] + scaffolding de eval orgánico [tabla `query_gaps` + logging] = el ruler que importa). Los unlocks grandes (corpus, eval orgánico) están gated; el deploy-prep no, y es necesario. PLAN "Qué sigue" reescrito.
- **(f) Build (rama `eval/s68-audit-canal`, flag inerte)**: `generator.py` `_FIDELITY_BLOCK` + `_assemble_system()` (runtime, base==SYSTEM_PROMPT byte-idéntico, fidelity +bloque) + `system=_assemble_system()`; `bvg_kmajority` exime `generate_fn_sha` del R4 (el refactor lo cambió; el aislamiento lo prueba el test de PARIDAD a nivel de construcción, $0 determinista — corrección cross-model: un output bit-idéntico fallaría por no-determinismo de Sonnet, DEC-015) + estampa `assembled_system_sha` real + flag ESTRICTO en el harness (typo aborta, no corre tratamiento-como-control). 317 tests. Dúo: r1 (sub 8/8... ver log) + r2 (sub 6/6 + cross 6/6) + corte final cross-model + consulta §8 (optimizar el run): C1 available_models TRAMPA [toca el call-site del run principal] → SHIP-gate; C2 K=10 inútil [4/5 diana PARCIAL 5/5]; C3+C4 ($0) adoptados.
- **Alternativas descartadas**: shippear pese a Δ_net=0 (cero upside + regresión cat011 real); saltar a Opus ahora (pre-supone el lever caro; el prompt falló ≠ capacidad es el cuello); seguir con el 4º micro-lever (within-doc/aditiva/k>50) como prioridad (valor marginal bajo tras 3 NO-GO; → BAJA prioridad, no descartados); relajar la tabla por el ±2 de ruido (el fix honesto es endurecer el ruler, no bajar el listón — DEC del s67b sobre dureza); ampliar el eval sintético ahora (sin técnicos reales optimiza el adversarial-39; el eval que importa es el orgánico).
- **Gaps declarados**: el pivote asume "bot bueno en lo común" medido por las conductas de seguridad + 10/39 PASS-control pero NO verificado con técnicos reales (esa verificación ES el eval orgánico, punto 3); el ±2 de ruido puede OCULTAR wins de +1 (el content-level vio que fidelity SÍ completaba) → "endurecer el ruler primero" si se reabre lever-work, no "los levers no sirven"; producto-eng es otro modo (no eval-driven con dúo) — aplica el contrato BP igual; el lever fidelity se ARCHIVA (flag vivo, reversible), no se borra.
- **Relacionado**: DEC-050 (canal NO-GO, el precedente inmediato), DEC-048 (CE ROLLBACK + baseline s67base + re-judge-mismo-batch heredado), DEC-049 (la priorización que esto ejecuta y re-dirige), DEC-016b (gate/proxy ≠ ship), DEC-001 (2 ejes), DEC-015 (Sonnet temp=0 no-determinista → paridad a nivel de construcción), DEC-033 (taxonomía congelada), s47§D (dual-judge diferido — ahora prerrequisito si se reabre), lección #36 (`feedback_my_bias`: bias #20 tiene capa-de-re-audit; verificar al nivel CORRECTO [contenido, no narrativa]), `evals/s69_ab_report.yaml` · `s69fid_*`/`s67rejud_*` · `s69_reaudit_solodebiles.yaml`/`s69_retrieval4_diag.yaml`/`s69_content_reaudit.yaml`/`s68b_resolution_audit.yaml` · `evals/_s69_generation_design.md` (v3.2, local) · `adversarial_review_log.jsonl` (5 entradas s69) · `tests/test_s69_prompt_variant.py` · commits del ciclo s69.

## DEC-052 — s71: re-análisis del residual (Track 1 audit del ruler + Track 2 retrieval) — CORRIGE el pivote de s69; el cuello es RETRIEVAL (inanición del pool), atacable con fixes concretos

- **Fecha**: 13 jun 2026 (s71). **Impacto**: ALTO (corrige la conclusión estratégica de DEC-051; re-dirige el roadmap a fixes de retrieval con diana medida; zona de dolor retrieval/ruler → dúo + workflows). **Disparador**: Alberto cuestionó el pivote-a-producto de s69 ("obviamente hay que mejorar el bot antes de diagramas") y mandó 2 tracks ortogonales autónomos con dúo + compactar/cerrar la sesión.
- **(a) Track 1 — audit ADVERSARIAL del ruler (¿gold injusto o bot falló?), doble-escéptico (workflow batched, 13 candidatos: K-INESTABLE + conducta + cat020-tipo + corpus-gap-admit):** auditor con default "gold justo, bot falló" → defensor (abogado del gold) tumba cualquier "injusto". **Resultado: solo cat012 sobrevive como gold-injusto→maybe-PASS (y debatible)**; el defensor tumbó 4 que el auditor había marcado injustos (cat009/cat011/cat019/cat020 = el gold ES justo, el bot tiene gap real). **El bot NO está infra-puntuado — el escepticismo de Alberto queda validado** (re-graduar como mucho cat012 → ~11/39, no la subida grande que yo intuí). 6 golds reclasificados a retrieval-miss (cat007/cat013/cat021/hp006/hp013/hp009 — la info ESTÁ en corpus pero no se sirvió; hp006 era mi "corpus-gap" hand-wave). 2 generación-real (hp004/hp007). 10 dudas sustantivas dejadas para Alberto (borde PASS/PARCIAL + decisiones de judge-prompt/catálogo). Artefacto `evals/s71_track1_audit.yaml`.
- **(b) Clasificación v2 reconciliada** (`s71_classification_v2.yaml`, override de s70 con Track 1): de los 29 no-PASS, **16 RETRIEVAL-miss + 2 retrieval-family ≈ 18 (≈60%)** · 4 generación · 3 corpus-gap? · 2 borderline (cat019/cat020, bot ~correcto, PARCIAL conservador) · 1 diseño (cat011 catálogo) · 1 gold-injusto (cat012). **El retrieval CRECIÓ de 13 a ~16-18** (Track 1 movió 5 golds dentro). Retrieval = EL cuello, con muchísimo.
- **(c) Track 2 — diagnóstico del mecanismo de retrieval (workflow batched, 17 golds, 6 mecanismos, 16/17 fixable):** filtro-modelo/series 8 · rerank-no-sube 1 (hp003) · stamps-dedup-pisa 2 (cat017/cat007) · frontera-k>50 3 (hp002/hp001/hp011) · corpus-gap-real 1 (hp017) · producto-conflicto 2 (cat008 no-fixable, cat021 sí). **Raíz común: INANICIÓN DEL POOL aguas arriba** — `keyword_search` limit=5 SIN order (devuelve 5/103 por orden físico arbitrario; el chunk necesario en posición 8 justo pasado el cap), broad-fallback vectorial capado a `limit=5`, y el reranker LLM lee solo `content[:800]` (el hecho cae en el offset 2566, fuera de la ventana). **Fixes CONCRETOS y baratos, varios MEDIDOS end-to-end** (hp003: subir preview 800→2400 en `reranker.py:74` → re-corrido sobre el pool congelado, el reranker AHORA sirve el chunk correcto). **NO es el canal-broad re-rankear-por-coseno (NO-GO s68)** — son fixes quirúrgicos de límites/order/ventana que sirven el chunk SIN re-barajar el pool. Artefacto `evals/s71_track2_retrieval_diag.yaml`.
- **(d) CORRIGE el pivote de s69 (la decisión estratégica).** DEC-051 concluyó "3 NO-GO → la fase de levers-baratos está agotada → pivote a producto/deploy". **Era PREMATURO:** se declaró el residual "no-atacable" SIN el diagnóstico quirúrgico per-gold. El re-análisis s70/s71 (dirigido por el pushback de Alberto) mostró que el residual SÍ es lever-addressable, el cuello es retrieval (inanición del pool, no capacidad ni generación), y hay fixes concretos baratos. **Lección (a `feedback_my_bias`): no declarar un residual "agotado/no-atacable" sin la diagnosis per-gold contra la fuente** — el pivote-a-producto fue una huida cómoda tras 3 NO-GO, cazada por Alberto.
- **Nueva dirección**: construir los fixes de retrieval por prioridad riesgo/leverage (reranker-preview → broad-fallback → keyword-order → diversify-rescues), cada uno tras flag, medido con la métrica granular de cobertura (s70, anti-±2) + content-level de flips + dúo + gate sobre PASS-control. Objetivo 11+ de 16 → PASS. PLAN "Qué sigue" reescrito.
- **Alternativas descartadas**: re-graduar golds para inflar el PASS-rate (Alberto: "no trampas al solitario" — el doble-escéptico lo previno: solo 1/13 sobrevivió); el panel de generadores/Opus (s70, el dúo lo mató: la métrica de cobertura no prueba capacidad + re-litigaba DEC-051; verificado que el residual NO es generación/capacidad); mantener el pivote-a-producto (refutado por el diagnóstico de retrieval); el canal-broad (NO-GO s68, los fixes de s71 son quirúrgicos no broad).
- **Gaps declarados**: los fixes de reranker/broad-fallback son GLOBALES (los 39 golds) → riesgo de regresión en PASS-control, gate obligatorio; el ±2 del juez exige medir con la cobertura granular además del veredicto; las 10 dudas de Track 1 son decisiones de Alberto (no resueltas); cat008 (producto-conflicto) y hp017 (corpus-gap) no son retrieval-fixables; Track 2 diagnosticó pero NO construyó (el build es la próxima sesión).
- **Relacionado**: DEC-051 (el pivote que esto corrige), DEC-050 (canal NO-GO — los fixes de s71 son quirúrgicos, no el broad), DEC-044 (filtro de series — relevante para producto-conflicto/series), DEC-016b (gate ≠ ship), DEC-001 (2 ejes), s70 (métrica granular + clasificación quirúrgica), `evals/s71_track1_audit.yaml` · `s71_classification_v2.yaml` · `s71_track2_retrieval_diag.yaml` · `s70_factcov.yaml` · `scripts/s71_bundle.py` · workflows s71-track1/track2 (batched, resume tras apagones) · rama `eval/s68-audit-canal`.

## DEC-053 — s72: Lever 2 (IDENTIDAD) construido tras flags — Brazo A (e-series) VERIFICADO end-to-end; Brazo B (rescate pm) correcto pero NO-OP para cat013 hasta Lever 1

- **Fecha**: 14 jun 2026 (s72). **Impacto**: MEDIO-ALTO (primer build de los fixes de retrieval de DEC-052; zona de dolor retrieval/identidad/esquema → dúo ×3 rondas incl. cross-model GPT-5.5; flags default OFF = prod inerte). **Disparador**: construir los fixes de s71 empezando por el eje IDENTIDAD (Lever 2), orden decidido con Alberto (Lever 2 antes que Lever 1 = más barato/escalable/bajo riesgo).
- **(a) Scope** (audit de campos workflow 4-lectores + síntesis + crítico): Lever 2 = {alias-paraguas + series-config + rescate pm mal-atribuido}. **Diferidos con motivo:** C keyword-strip hp006 (el fix real va dentro de `extract_search_keywords`, blast GLOBAL para 1 gold identidad-ADYACENTE), D section_path (deuda nueva **#48**: campo poblado con breadcrumbs curados que NO llega al cliente/reranker [0 refs en `src/rag`]; es lever de RANK no identidad → rompería atribución; + exponerlo al canal vectorial es migración SQL de `match_chunks`), cat001 (→Lever 1 diversify). category/language/diagramas/doc_type/distributor = backfill diferido (ningún gold los mueve).
- **(b) Brazo A (hp009/hp018) tras `LEVER2_IDENTITY`**: alias config-driven (`model_aliases` en `morley.yaml`: ZXe→{ZX2e,ZX5e}) + entrada `series:` e-series (per-entry flag-gating NUEVO en `series_registry`) + guard de colisión de aliases. **El dúo corrigió mi diseño** (sesgo #20 "plegar = abstracción cómoda"): el paraguas ZXe NO va en `members` — sería *owner* del producto espurio ZXAE/ZXEE (verificado `owners('zxae/zxee')={zxe}`) → `members=[ZX2e,ZX5e]` reales, paraguas SOLO en `model_aliases` (capa separada = más escalable a 30+, cross-model). **VERIFICADO end-to-end contra corpus real**: el pool de hp009/hp018 se da la vuelta (0→23/26 chunks reales ZX2e/ZX5e, espurio 22/26→0, +25 docs de serie MI-530). **A = candidato a ship** (retrieval probado).
- **(c) Brazo B (cat013) tras `LEVER2_PM_RESCUE`**: rescate en `_filter_to_query_models` (path nivel-1, **source_file-only** + guarda `manufacturer==classify_model_manufacturer` + `len(core)≥4`, gated). Dúo r3 (cross-model 7 + workflow 3-lentes + síntesis) = GO-con-enmiendas, hallazgos verificados empíricamente: invariante single-model NUNCA cambia (cap=2 < umbral fail-open=3) → blast-control = 4 multi-modelo; inversión cross-brand por seed-fallback vía content-match → **enmienda source_file-only**; #11h está REVERTIDO (solo SYSTEM_PROMPT + eje no-fabricación del scorer). **VERIFY-FIRST (barato, antes de medir): B es NO-OP para cat013** — los 25 chunks SDX-751 (mal-atribuidos a LOCAL-360, manufacturer Notifier) nunca entran al pool (rank ~11, broad-fallback capado a 5) → el rescate no puede recuperar lo ausente → **cat013 bloqueado en Lever 1**. B queda correcto+seguro+testeado, flag OFF, reactivable tras Lever 1.
- **(d) Estado eval-driven**: NINGÚN gold medido como PASS aún (contrato eval-driven PENDIENTE). A: retrieval probado, PASS por medir (generador+juez). B: NO-OP. cat013 explícitamente → post-Lever 1. 330 tests verdes; paridad flag-OFF probada.
- **Alternativas descartadas**: plegar el alias en la serie (dúo: `model_aliases` separado = más escalable + evita el latente del member-core); content-match en el rescate (dúo: source_file-only, anti inversión cross-brand); gatear el rescate a catalog-only (desactivaría cat013, también catalog-miss); incluir section_path/hp006 en esta tanda (scope-creep, rompe atribución del delta, DEC-019); meter aliases en el `registry_fingerprint` (rompía la paridad flag-OFF).
- **Gaps declarados**: B NO-OP hasta Lever 1; la guarda de B depende del seed de 3 marcas (frágil para modelos out-of-catalog, mitigado por source_file-only, disminuye según crece el catálogo); A y B son puentes config sobre la raíz de DATOS (#21 product_family / #43 capa B metadata); cat008 (control) cambiaría bajo B si su chunk estuviera en pool (medir al reactivar tras Lever 1); el PASS-delta de A SIN medir (eval-driven incompleto); refs file:line del memo/diagnóstico desfasadas (actualizar).
- **Relacionado**: DEC-052 (los fixes que esto empieza), DEC-043/#43 (series_registry + seam config), DEC-044 (filtro de modelo), DEC-019 (medir delta, no proxies), TECH_DEBT #48 (section_path, NUEVO) · #21/#43-capaB (raíz de datos diferida), `adversarial_review_log.jsonl` s72 (6 entradas, **0 FP** en 3 rondas), `evals/_s72_lever2_design.md` · `_s72_alias_shape_decision.md` · `_s72_brazoB_review.md`, rama `eval/s68-audit-canal`.

## DEC-054 — s73: identidad ESTRUCTURAL — el detector LLM-en-ingesta es la raíz de #49; DISEÑAR ahora (contrato anotado), CONSTRUIR al gatillo; el config a mano queda como tapón

- **Fecha**: 15 jun 2026 (s73). **Impacto**: ALTO (rumbo de la raíz de identidad; zona de dolor corpus/ingesta/retrieval → cross-model GPT-5.5 + workflow adversarial 7 agentes). **Disparador**: Alberto preguntó si el enfoque es robusto+escalable y propuso un proceso LLM que derive manual→modelos en ingesta + backfill.
- **Decisión**: la **dirección de Alberto es la raíz correcta y YA es el canon (#49 sol.1)** — derivar la identidad del corpus en ingesta (la serie se *calcula*, no se cura a mano). Su mejora real sobre el canon: usar un **LLM content-based** (no el regex genérico de #21) para desambiguar pm compuestos (AM2020/AFP1010) y elegir el modelo REAL sobre el más-frecuente/prefijo que hoy escoge `_detect_model` (`metadata.py:109-118`, la raíz de SDX-751→LOCAL-360). **Pero DISEÑAR ahora (contrato anotado en #49), NO construir el backfill ahora**: la economía de "ZXe-ahora + tech-debt resto" está INVERTIDA (lo barato = correr el LLM ~Haiku; lo caro/diferible = VERIFICAR el backfill a ~47+ familias/1.170 docs) → "done para ZXe" no entrega valor estructural (ZXe ya resuelto a mano, DEC-053). Build gated al trigger real de #49 (arranque ingesta 30+ / 2º gold de identidad fuera de serie).
- **Alcance corregido (mi sobre-afirmación, cazada por el dúo)**: el detector ataca P3(a) mis-atribución solo PARCIAL (aplicabilidad nivel-MANUAL ≠ atribución nivel-CHUNK), resuelve bien P2 shared-docs, y **NO resuelve P3(b) metadata-inconsistency** (conjunto-de-modelos ≠ IDs canónicos). Es ORTOGONAL al cuello MEDIDO (Lever 1/DEC-052, ~0 de los 16).
- **Alternativas descartadas**: construir+backfill ZXe ya (adelanta el timing gated, compite con Lever 1, no cobra valor); backfill ciego a 1.170 docs (coste dominante = verificación humana no dimensionada; precedente de deuda silenciosa = las 318 correcciones de #18-mfr nunca auditadas); cross-check del LLM contra el índice (circular — hereda la contaminación de filename; árbitro = el manual / muestra humana); columna `applies_to_models` en chunks (ALTER+INDEX+RETURNS TABLE de `match_chunks_v2`) → **alternativa BARATA: mapping modelo→familia en registry/YAML lazy-load** (sin DDL; `documents.document_family` ya existe).
- **Prerequisitos anotados (antes de cualquier backfill)**: cerrar **F2** del escritor (`index.py:resolve_document_id` no prefiere `active` ni crea filas) + replicar la normalización en el writer (o backfill y writer divergen); auditar P3(b) por-familia. [s73: F2 ANOTADO, NO cerrado — no hay ingesta activa.]
- **Mi error factual (regla C, cazado por el workflow)**: dije "4 fabricantes"; el corpus YA tiene **31 marcas / 1.170 docs / 587 modelos** (`ARCHITECTURE.md:22`) — confundí scope-M&A con estado-corpus.
- **Relacionado**: TECH_DEBT **#49** (refinado con todo esto), #21 (product_family), #43/#18-mfr (atribución), #44/#45 (contratos de ingesta), DEC-053 (A/B = puentes config sobre la raíz de datos), DEC-052 (Lever 1 = el cuello, ortogonal), `adversarial_review_log.jsonl` s73 (cross-model 7/7 + workflow 8/8, 0 FP).

## DEC-055 — s73: medición del Brazo A = FALLO→PARCIAL ×2 (GRIS, 0 regresión); identidad arreglada en prod (smoke) → SHIP `LEVER2_IDENTITY` como TAPÓN + combinar con Lever 1

- **Fecha**: 15 jun 2026 (s73). **Impacto**: ALTO (decide encender un flag en prod; eval-driven). **Disparador**: cerrar el contrato eval-driven que DEC-053(d) dejó abierto ("PASS-delta de A SIN medir").
- **Harness endurecido + dúo (HECHO)**: tras un workflow adversarial que cazó 5 fallos del diseño (asserts inexistentes, factcov-bucket-coupling, path-mismatch prod, s67_ab no-portable, n=2), se CABLEÓ: `scripts/ab_verdict.py` (capa de veredicto COMPARTIDA — paga la deuda del patrón s59/s67/s69 + tests) · `scripts/s73_ab.py` (asserts ejecutables SPLIT pre-pago/post-judge, factcov-DESDE-BASE [resuelve el bucket-coupling], árbol n=2, selftest) · `evals/_s73_prod_smoke.py` (path real CON target_models) · cache aislado `s73_embed_cache.json`. **Re-dúo sobre el cableado (Opus + cross-model, 0 FP)**: cazó 2 críticos — `no_invencion` hardcoded (→ veredicto auto topa en SHIP-CANDIDATO, 2º eje humano) y asserts no-ejecutables-pre-pago (→ split). 347 tests verdes.
- **Resultado MEDIDO** (K=5, base=s67base reusado, arm A flag ON): **hp009 y hp018 ambos FALLO→PARCIAL** (5/5 PARCIAL), **ninguno flipa a PASS** → **veredicto GRIS**. **0 regresión** (control 37 byte-idéntico). hp018 factcov 0.76→0.36 (NO es regresión: en OFF respondía completo sobre el producto EQUIVOCADO ZXAE/ZXEE; en ON correcto-pero-menos-completo — el juez movió ambos hacia arriba). **prod-smoke**: flag OFF responde sobre ZXAE/ZXEE (producto equivocado); flag ON sobre ZX2e/ZX5e (correcto) — hp018 responde bien, hp009 pide aclaración de variante.
- **Decisión (Alberto): SHIP `LEVER2_IDENTITY` como TAPÓN + combinar con Lever 1** (opción a+combinar, secuencia "activar YA, Lever 1 después"). Razón: el flag **deja de dar el producto equivocado** en un dominio de seguridad (PARCIAL-sobre-correcto ≫ FALLO-sobre-equivocado), 0 regresión, reversible (default OFF, kill-switch). El PASS no llega porque el cuello que queda es **completitud = Lever 1** (ortogonal a identidad), no la identidad. Activación = `LEVER2_IDENTITY=on` en Railway (env, reversible sin redeploy); rollback = quitar/off.
- **Guardarraíl de narración (workflow)**: shippear A es un tapón config de alto valor — **NO** narrar "la identidad escala/está resuelta" (techo #49/DEC-054). El PASS limpio se busca combinando con Lever 1.
- **Alternativas descartadas**: hold (no shippear hasta Lever 1) — descartada por el coste de seguridad de mantener el bug de producto-equivocado en prod; auto-SHIP del harness (el 2º eje no-invención no es auto-certificable → SHIP-CANDIDATO + confirmación humana, regla F); subir K (n=2 sigue cualitativo; rompería la comparabilidad con s67base K=5).
- **Gaps declarados**: n=2 (veredicto cualitativo, no inferencia); hp009 prod pide-aclaración (conducta segura pero ≠ "answer" del gold); el harness mide rerank SIN target_models (infra-mide el efecto prod, que es ≥ por el smoke); migración de s59/s67/s69 a `ab_verdict` pendiente (deuda parcial pagada).
- **Relacionado**: DEC-053 (A candidato a ship → ahora medido+shipped), DEC-052 (Lever 1 = lo siguiente), DEC-054 (la raíz estructural), DEC-019 (medir delta), TECH_DEBT #49, `evals/s73_ab_report.yaml` + `_s73_harness_design.md`, `adversarial_review_log.jsonl` s73, rama `eval/s73-lever2-ship` → PR.

## DEC-056 — s74: Lever 1 BATCH (cluster de inanición del pool) construido tras flags + gate-0 judge-free = lift de retrieval REAL pero MODESTO (no shipped, bancado); el cuello de retrieval se FRAGMENTÓ → siguiente raíz = detector de identidad (DEC-054) + backfill `product_model`, NO más levers de retrieval ni el gate de prod

- **Fecha**: 15 jun 2026 (s74). **Impacto**: ALTO (cierra el ciclo de levers de retrieval con medición + re-dirige el rumbo a la raíz de datos; zona de dolor retrieval/corpus). **Disparador**: PLAN "Qué sigue" s73 (Lever 1). Corrección de arranque: el "ship LEVER2_IDENTITY" de DEC-055 era **NO-OP en prod** (el `manufacturer-check` del handler bloquea fabricante+pm-compuesto ANTES del retrieval; el eval lo bypasea, bias #40) → flag de vuelta a OFF.
- **(a) Re-secuencia con Alberto (×3 pushbacks, todos correctos):** (i) gate-fix #49 NO primero — sin técnicos hasta ~sept + Δ_eval=0 (el eval bypasea el gate) → es deploy-prep, no urge; (ii) Lever 1 batcheado, NO 2c aislado (1 gold inmedible bajo el ±2); (iii) la raíz de datos > más tapones de retrieval.
- **(b) BUILD del batch tras flags inertes (default OFF = prod inerte, paridad probada, 353 tests):** 2a `LEVER1_BROAD_FALLBACK` (broad-fallback vectorial `5→effective_top_k`, retriever.py:~1100) · 2b `LEVER1_KEYWORD_ORDER` (keyword_search `order=page_number.asc,id.asc` determinista + limit 5→15; el dúo MATÓ el `order` por content_type del diag s71 = over-fit + entierra al winner bajo 'general', verificado contra DB) · 2c `RERANK_PREVIEW_CHARS` (preview del reranker LLM 800→2400; reranker.py:74). **Dúo ×3 rondas (sub-agente Opus + cross-model GPT-5.5, 0 FP)** sobre rumbo/2c/batch — cazó: error fáctico (vía-C = lever s59 ROLLBACKeado, no "zona s68"); sobre-afirmación "2c MEDIDO end-to-end" (era single-pass rerank-only, dado-confundido); el `order` over-fit de 2b.
- **(c) GATE-0 judge-free (factcov-sobre-top5 = ¿las citas del gold en el top-5 del reranker?, modal n=3 + firm-up n=7; ~$15; esquiva el ±2):** lift de retrieval **REAL pero MODESTO** — target 48%→67% (@2400), pero afinado: **2 golds fuertes+estables (hp008 0→3, hp002 3→6)** + 5 marginales (+1/+2, dado-ruidosos: hp003/hp018/cat001/cat017/hp013) + **~3-4 REGRESIONES** (cat016 1→0, hp009 2→1, hp011 dado, **PASS-control cat022 1→0**). **2400 elegido por dato** (4000 midió peor, −2; y el CE Voyage lee su propio 4000 independiente del flag → 4000 no aporta aguas abajo). Verify-first ($0): el batch mete los canales correctos al pool en 15/15 (2a=VECTOR, 2b=MODEL).
- **(d) DECISIÓN: bancar el batch tras flags (NO shippear) + A/B con juez DIFERIDO.** Razón: modesto + colateral (cat022) + sin usuarios + PASS sin medir; el A/B (~$25) saldría casi seguro GRIS (±2 del juez DEC-051d + dado del reranker sobre 2 golds fuertes). El win granular de retrieval queda CONFIRMADO y bancable; el PASS se valida con el ruler que importe (eval orgánico ~sept / dual-judge).
- **(e) RE-DIRECCIÓN (mapa de NO-PASS, workflow adversarial 3 streams + verificación):** los 29 NO-PASS = ~16 retrieval + 5 generación + 4 corpus-gap + 2 borderline + 1 diseño + 1 gold-injusto (cat012, único; bias #20 verificado: el bot falla de verdad en 28/29). Overlay del batch → **el cuello de retrieval se FRAGMENTÓ**: 2 golds claros + 5 marginales + residual disperso (identidad 3, frontera 2, stamps 1) de +1-o-regresan, en el sub-suelo de ruido. **No hay siguiente lever de retrieval que merezca la pena** (re-entra en la fase de levers-baratos que DEC-051e cerró). Cuellos vinculantes ahora = el ±2 del ruler (dual-judge = prerrequisito, DEC-051d) + las RAÍCES DE DATOS del SWAP.
- **(f) SIGUIENTE BLOQUE (decidido con Alberto): la raíz de datos, NO más retrieval ni el gate de prod.** El pm COMPUESTO (#49/#43) rompe en DOS sitios: el gate del handler (prod, eval-invisible, no urge) **Y** el filtro de modelo `_filter_to_query_models` DENTRO del retrieval (eval-MEDIBLE: cat013/hp009/hp018 mueren ahí). Arreglar el DATO (partir el pm vía el **detector-LLM-en-ingesta de DEC-054**) arregla ambos de raíz, es eval-medible, y es la MISMA herramienta de escala 30+ (no desechable) = prep de F2. **Categorías (#44): NO backfill ahora** — el filtro-EQ está muerto (DEC-040, la respuesta puede vivir en otra categoría); el batch ya rodea la categoría vacía; si vuelve será boost en el contrato de ingesta, no filtro.
- **Alternativas descartadas**: A/B con juez ahora (GRIS casi seguro + sin usuarios = bajo valor de decisión); preview 4000 (peor en el LLM + el CE lee su propio 4000 → sin beneficio aguas abajo); abrir un 5º lever de retrieval para el residual fragmentado (DEC-051e); backfill de categorías ahora (filtro muerto + viola freeze DEC-036e + beneficio incierto + se re-haría en ingesta); gate-fix #49 como siguiente (prod, sin usuarios, eval no lo ve → deploy-prep).
- **Gaps declarados**: el batch tiene ~3-4 regresiones de factcov (incl. PASS-control cat022) que el A/B tendría que pesar — no es ship-ready limpio; el lift está medido en factcov-sobre-top5 (RETRIEVAL), NO en PASS (el A/B se difirió); el dado del reranker contamina el per-gold (solo el agregado es fiable); el detector DEC-054 es un BUILD real (LLM-detector + validación) + re-baseline del freeze, con beneficio eval modesto (~3 golds) — se justifica como prep de escala, no como lever de 3 golds; HISTORY no tenía entrada s73 (puenteada en s74).
- **Relacionado**: DEC-052 (Lever 1 = lo que esto construye y mide), DEC-051 (±2 del ruler + fase de levers cerrada), DEC-040 (categoría=boost-no-filtro, A1 descartada), DEC-054 (el detector de identidad = la raíz, ahora el siguiente bloque), DEC-055 (el ship NO-OP que esto corrige), DEC-016b (gate antes de A/B), DEC-019 (medir delta no proxies), TECH_DEBT #44/#43/#49, `evals/_s74_{2c_decision,2c_design,lever1_batch_design}.md` + `s74_lever1_gate0.{py,json}` + `s74_lever1_firmup.json` + `s74_lever1_verify.py` + `tests/test_{rerank_preview_window,lever1_pool_flags}.py`, `adversarial_review_log.jsonl` s74 + workflows s74 (2c-nextstep-audit, nopass-map), rama `eval/s74-lever1-batch` → PR.

## DEC-057 — s75: audit-first de la raíz de identidad (DEC-054) = el detector tiene ~0 palanca eval real → DIFERIDO a su gatillo (ingesta-30+), NO se construye como lever; refina hacia abajo el sub-claim eval-medible de DEC-056(f)

- **Fecha**: 15 jun 2026 (s75). **Impacto**: ALTO (decide NO construir el detector ahora + redirige el rumbo con medición; zona de dolor identidad/corpus/retrieval/eval → dúo cross-model GPT-5.5 + sub-agente Opus, INNEGOCIABLE). **Disparador**: PLAN "Qué sigue §1" s74 (detector de identidad como siguiente bloque). Alberto eligió **audit-first** (medir antes de decidir build/defer/pivote).
- **Decisión: DIFERIR el build del detector (DEC-054)** a su gatillo real (arranque ingesta-30+). El audit-first ($0, read-only, `scripts/s75_identity_audit.py` → `evals/s75_identity_audit.yaml`) MIDIÓ que el detector tiene **~0 palanca eval real** → no se construye como lever; sigue siendo prep de escala F2 al gatillo. Es **gate/audit-primero funcionando** (DEC-005/019): no construir un aparato de 0 palanca antes del gatillo.
- **(a) Palanca eval ≈ 0 (lo decisivo).** De los 17 NO-PASS diagnosticados de retrieval (s71 track2), el detector toca SOLO **cat013** — y cat013 es gold de **CONDUCTA** (`refuse-inference` cross-marca Detnov+Notifier, **verificado en `gold_answers_v1.yaml`**), NO de retrieval-recall: el detector no lo arregla y **podría EMPEORARLO** (más contenido SDX-751 empuja al generador a inferir compatibilidad, #11f). **hp009/hp018 son CONFIG** (e-series en `morley.yaml`, Brazo A ya construido — verificado en `series_registry.py`), no el detector. → confirma DEC-054 ("identidad ⊥ inanición del pool = Lever 1") y **refina hacia abajo el sub-claim "eval-MEDIBLE: cat013/hp009/hp018" de DEC-056(f)** (que ya decía "no como lever de 3 golds" — esto lo lleva a ~0).
- **(b) Escala del problema de datos = real pero ACOTADA, en PROXIES RUIDOSOS (no pisos medidos).** 1A pm-compuesto: 78 etiquetas con separador/multi-modelo aparente (**sobre-cuenta**: `20/20I`, `DH500AC/DC` son modelos únicos con `/`). 1B mis-atribución (firma cat013): crudo 368 **CONTAMINADO** (el regex parsea códigos de manual `MNDT-xxx` como modelos; el catálogo `model_catalog.json` MISMO los heredó = **la circularidad que DEC-054 predijo**), refinado ≤114 docs/1218 chunks tras filtrar doc-codes (sigue con residual `GUIDE-`/SKU `55310011` → es ≤114, no piso limpio). 1C metadata-inconsistency: 18 clusters. Concentrado en 3-4 marcas legacy (Notifier/Morley/Detnov).
- **(c) Dúo (Protocolo 3, ronda FRESCA; sub-agente Opus + cross-model GPT-5.5, fuerte convergencia, 0 FP).** Confirmó DIFERIR pero corrigió mi **FRAMING** (sesgo #38/#39/#40): "≈0 medido + completo + BP" → honesto = "0 retrieval-net sobre los **17/29** diagnosticados; cat013 es conducta (no lever); escala = proxy ruidoso acotado; gap de selección (solo cat009/NFS-Supra plausiblemente identidad-adyacente fuera de track2, pero es lifecycle/source-conflict, no pm); falta freeze-contract si el audit es base de decisión". Verifiqué cada claim fuerte contra código/artefacto (regla C) antes de canonizar.
- **Alternativas descartadas**: build-ahora como prep-de-escala pura (gated + ~0 palanca + coste de VERIFICACIÓN del backfill no dimensionado e inminente = bias #38/#40); flag-tool-only / detector-proactivo-capa-2 sin backfill (no toca la atribución nivel-chunk = la mitad del aparato por ~0 palanca, DEC-054); profundizar cat009 + pool-trace de cat013 antes de cerrar (pulir algo que se difiere — el SIGNO de la decisión no cambia porque cat013 es gold de conducta).
- **Gaps declarados**: cifras de escala = proxies ruidosos (≤114, no piso limpio); 17/29 NO-PASS examinados (gen/corpus/borderline/diseño no cruzados con identidad salvo cat009); el audit no congela hash de corpus/catálogo (sin freeze-contract — si cambian, 78/≤114/18 se mueven sin traza); cat013 tiene costura interna (track2=in-pool/model-filter vs DEC-053=not-in-pool/broad-cap, dos chunks distintos) — MOOT para la decisión porque es gold de conducta.
- **Siguiente bloque (s76, decidido con Alberto): revisión EXHAUSTIVA en ultracode de cómo recuperar los golds NO-PASS de forma ESTRUCTURAL (no overfitting)** — confrontando que DEC-051e declaró agotada la fase de levers-baratos: ¿hay una clase de fix ESTRUCTURAL (raíz-de-datos / arquitectura de generación / arquitectura de retrieval) que esa fase NO agotó, distinguible del overfitting del ruler? Debe lidiar con el ±2 del ruler (dual-judge prerrequisito, DEC-051d) y el prior "fase agotada".
- **Relacionado**: DEC-054 (el detector = la raíz, ahora DIFERIDO con medición), DEC-056 (cuyo §(f) sub-claim eval-medible esto refina), DEC-052/053 (Lever 1 / Brazo B NO-OP para cat013), DEC-051 (fase de levers cerrada + ±2), DEC-005/019 (gate/audit-primero, medir delta), TECH_DEBT #49/#43/#21, `evals/s75_identity_audit.{py,yaml}` + `evals/s75_audit_brief.md` + `adversarial_review_log.jsonl` s75 (dúo), rama `eval/s75-identity-audit` → PR.

## DEC-058 — s76: revisión estructural de los 29 NO-PASS (ultracode) — la fase de levers de RETRIEVAL está agotada; la clase NO-tocada por esa fase es de DATOS (revisión/precedencia #4); PROD-REACH mide que el gate corta 7/9 mal antes del RAG (deploy-prep #49); el ruler tiene un sesgo sistemático MEDIDO (no solo ±2)

- **Fecha**: 15 jun 2026 (s76). **Impacto**: ALTO (revisión de rumbo + 3 hallazgos MEDIDOS que re-priorizan el roadmap; zona de dolor retrieval/ruler/gate → 1 workflow ultracode [29 agentes, 21 lentes adversariales] + 2 cortes cross-model GPT-5.5 [8/8 y 7/7 confirmados, **0 FP**]). **Disparador**: el bloque s76 decidido con Alberto (DEC-057): ¿hay una clase de fix ESTRUCTURAL que la fase de levers-baratos (DEC-051e) NO agotó, distinguible del overfitting del ruler? Alberto eligió ejecutar 3 acciones medibles.
- **(a) Meta-hallazgo (corregido por el cross-model — NO "única"): la clase que el lever-phase de RETRIEVAL no tocó es de DATOS — el contrato de REVISIÓN/precedencia (#4, cat009/cat024).** Ataca PRECEDENCIA entre chunks ya servidos (no inanición del pool) → ortogonal a Lever 1/2, no re-litiga DEC-056, generaliza a "conflicto-de-revisión a 30+ fabricantes", llega a prod. Distinta de la identidad (ya diferida DEC-057) y del sesgo del ruler (nuevo, §d). Eval-medible en SOLO 2 golds < ±2 → NO accionable como recuperador en s76.
- **(b) PROD-REACH (medido, judge-free, `scripts/s76_prod_reach.py` → `s76_prod_reach.yaml`): el gate manufacturer-check del handler (telegram_bot.py:292-339) corta 9/29 antes del RAG; 7 son cortes ERRÓNEOS** (verificado en DB viva: el corpus tiene 103-581 chunks del modelo, pero `lookup_model_manufacturer` [catálogo 587] devuelve None [CAD-150/ZXe/40-40 ausentes = catálogo desincronizado] o la marca equivocada [RP1R en `_NOTIFIER_PATTERNS` pero el corpus lo tiene Morley]). 2/9 son frontera OEM-relabel (ADW535/ASD535=Securiton → identidad #43/#49). → para esos 7, NINGÚN fix de retrieval ayuda en prod; el fix es el GATE (#49 deploy-prep). Confirma el mecanismo del NO-OP de LEVER2_IDENTITY (ZXe cortado antes del RAG). **reach ≠ PASS** (arreglar el gate los hace LLEGAR al retrieval; el PASS sigue dependiendo del retrieval bancado). Corte cross-model: el gate-fix REDUCE el rechazo-erróneo, NO "cierra #40 de raíz" — la raíz de datos (identidad/revisión) es la capa de abajo; sin contrato de identidad solo cambia falsos-rechazos por falsos-aceptados/mis-atribución.
- **(c) Contrato de revisión #4 = SPEC (diseño, no build, `evals/_s76_revision_contract_spec.md`).** Árbitro de precedencia (revisión=latest-wins vs variante-regional=answer-con-conflicto vs OEM-relabel vs multi-parte vs datasheet; regla rectora: ante duda NO supersede), validación judge-free (paridad de POOL servido, NO veredicto final). **Vía corregida (pushback de Alberto + verificación DB): es un BACKFILL guardarraíl-eado s64-style, NO re-ingestión ni DDL** — `documents` YA tiene las columnas (status/revision/revision_date/document_family/superseded_by_id; `revision_date` poblado **1/1170** = el gap que llena el parser; `document_family` 1170 pero filename-naive → re-derivar; el `_filter_by_document_status` de s64/DEC-045 ya consume `superseded`, 3 cadenas pobladas retroactivamente sin re-ingestar) → **candidato CERCANO, NO gated a la ingesta lejana**; el escritor-en-ingesta (#43 capa B) solo evita re-crear el hueco a futuro. cat008 NO es de #4 (es OEM-relabel/source-precedence → identidad).
- **(d) Sonda dual-judge HOLÍSTICA (medido, `scripts/s76_dualjudge_sonda.py` → `s76_dualjudge_sonda.json`): refuta que "el dual-judge ya se midió-primero"** — s47 (`judge_disagreement.py`) midió los EJES del scorer atómico, NO el ruler de VEREDICTO que produce el ±2 (verificado en su docstring). Medido ahora (Claude-Opus 2º vs GPT-5.5, k=3, s67base 39 dev): **30.8% de desacuerdo cross-model, 11/12 Claude más LAXO** (dirección OPUESTA al s47 sobre los ejes). cat019/cat020: **triple confirmación de sesgo del juez** (audit humano s71 `should_be=PASS` + Claude=PASS vs GPT-PARCIAL-estable; el juez confunde completitud-correcta con contradicción) → **2 falsos NO-PASS (+cat012 debatible)**. **GO/NO-GO:** "2º juez + voto" = NO (desplaza el ruler laxo globalmente, solo 2 corroborados por humano, no toca el ±2 de sampling same-model); **recalibrar el rubric por-principio** ("completitud-correcta ≠ contradicción") = lever REAL anclado en principio + 2 fuentes (no 2 golds = no overfit), pero zona-de-dolor (re-juzga todo) + infra de medición gated a "¿vale sin usuarios?" (organic-eval ~sept).
- **(e) Recomendación (a Alberto): 3 builds futuros GATED, NADA shippeado esta sesión.** (1) **gate-fix #49 SUBE de prioridad** (defecto LATENTE medido en prod; deploy-prep; toca prod → dúo + PR); (2) contrato #4 (spec listo, build a ingesta, validación judge-free); (3) rubric del juez (cuando haya algo que shippear que dependa de ello, o en organic-eval, con cross-model + held-out). Es plan MEDIDO, no delta de prod (eval-driven: ningún fix es "bueno" sin delta).
- **Alternativas descartadas**: 2º-juez-y-voto (laxo global); re-poblar category como lever (drop — los 6 golds mueren en el filtro-modelo, no por category; re-litiga DEC-040); techo k>50 (1 gold dado-puro hp011); gate-harden catalog-first (no resuelve los OEM/multimarca sin el contrato de identidad); cerrar s76 sin entregable estructural ("escéptico máximo" — refutado: el conflicto-de-revisión es raíz nueva verificada en DB).
- **Gaps declarados**: nada shippeado (plan MEDIDO); el gate-fix toca prod (dúo+PR antes de cablear); #4 y rubric GATED; las 2 cuts OEM-relabel necesitan el contrato de identidad (#43/#49, diferido DEC-057); el ±2 de sampling same-model NO lo toca el dual-judge. **Sesgo recurrente #42 (`feedback_my_bias`):** el cross-model cazó 2× mi sobre-afirmación de las conclusiones MEDIDAS ("única clase", "cierra #40 de raíz", "2-3 falsos NO-PASS", spec cat008 inconsistente) → canonizo la versión CORREGIDA (la lección de s75 reincidió, ahora sobre resultados medidos).
- **Relacionado**: DEC-051 (fase de levers + ±2), DEC-056 (Lever 1 bancado), DEC-057 (identidad diferida), DEC-040 (category boost-no-filtro), DEC-021§D/s47 (dual-judge medir-primero), TECH_DEBT #49 (gate/identidad, elevado con medida) · #4 (revisión, spec) · #43 (atribución), `scripts/s76_{prod_reach,dualjudge_sonda}.py` + `evals/s76_prod_reach.yaml` + `s76_dualjudge_sonda.json` + `_s76_revision_contract_spec.md` + `_s76_{structural_review_proposal,measured_findings}.md`, `adversarial_review_log.jsonl` s76 (workflow + 2 cortes), rama `eval/s76-structural-nopass` → PR.

## DEC-059 — s77: gate-fix #49 CABLEADO = fall-through manufacturer-aware (Option D); raíz de los 6 catalog-miss = FAMILIA↔VARIANTE (no "modelo ausente"); corrección de PROD judge-free (reach≠PASS, CERO delta de eval — ESTRUCTURAL)

- **Fecha**: 16 jun 2026 (s77). **Impacto**: MEDIO-ALTO (toca PROD = handler de Telegram; zona de dolor retrieval/gate/identidad → dúo Protocolo 3 INNEGOCIABLE: sub-agente Opus + cross-model GPT-5.5, dúo #7, 6/6 confirmados, **0 FP**). **Disparador**: el item 1 de "Qué sigue" de s76 (DEC-058) — el gate-fix #49 sube a deploy-prep, audit-first; Alberto eligió "medir respuestas → dúo → cablear".
- **(a) Raíz por-modelo auditada (`scripts/s77_gate_audit.py`, DB real) — CORRIGE el framing de s76**: los 6 catalog-miss NO son "modelo ausente / catálogo desincronizado" sino **FAMILIA↔VARIANTE** — la gold pregunta por el nombre de familia/marketing (CAD-150, ZXe, 40/40), que NO existe como `product_model`; solo existen las variantes (`CAD-150-8/R`(88+15), `ZX2e/ZX5e`(198)/`ZXAE-ZXEE`(157), `40-40L/M/I`(~75 c/u)). `lookup_model_manufacturer` hace `eq` exacto → None. Los "103/157/486 chunks" de DEC-058 eran SUMAS sobre variantes (el `content` literal "CAD-150"=1). Para los 6: marca correcta + en DB, y `_filter_to_query_models` (substring-norm) recupera las variantes en fall-through (`filtro_recupera=True` ∀6, p.ej. `cad150 ⊂ cad1508`).
- **(b) El cambio (Option D, quirúrgico, una rama, `telegram_bot.py:315`)**: si `manufacturer_in_db(mentioned)` → fall-through al RAG en vez de hard-refuse; refuse solo si la marca también está ausente. Rama `CUT_A_mismatch` (RP1r / OEM) NO tocada. Mueve el juicio "¿tengo este modelo?" del índice `product_model` (desincronizado, #49) al retrieval+generador (que ven el contenido real — el índice es un oráculo NO fiable de disponibilidad).
- **(c) Medido judge-free (reach≠PASS; CERO delta de eval — ESTRUCTURAL)**: el harness `test_bot_vs_gold.py:101` (`run_bot`) llama `retrieve_chunks` DIRECTO y bypasea el gate (verificado por el sub-agente) → cambiar el gate NO puede mover el eval. Es PURO fix de PROD (deja de dar el falso-refuse). (i) `s77_fallthrough_measure.py` (réplica de `_process_query`, baseline prod-inerte): 6/6 conducta MEJOR que el falso-refuse (answer-marca-correcta / cat013 refuse-inference / cat021 clarify), cero alucinación; (ii) no-regresión K=3 `s77_regression_probes.py`: el path FIEL de Option D admite/rehúsa 3/3 (cad151 vecino-inexistente ADMIT; zxe+sdx cross-brand REFUSE) — la sustitución 40/41R→40/40R es PRE-EXISTENTE + off-path (no la introduce el gate; el filtro descarta el vecino-exacto y fail-opens a pool diverso); (iii) smoke por el HANDLER REAL `s77_handler_smoke.py` (lección #40): 10/10; (iv) 353 tests.
- **(d) Dúo (Protocolo 3, #7) + bias #42 reincidente**: 6 findings / 6 confirmados / 0 FP (`adversarial_review_log.jsonl`, ts 2026-06-16T08:57:52). El **cross-model GPT-5.5 cazó (2ª sesión seguida) mi sobre-afirmación sobre RESULTADOS MEDIDOS** ("refuta el riesgo"/"el guardarraíl aguanta") que el sub-agente Opus —mismo modelo que el autor— dio por honesta = blind-spot compartido dúo-Opus → confirma por qué el cross-model es INNEGOCIABLE en zona de dolor. Framing rebajado a "evidencia preliminar". Hallazgo más fuerte (cross-model): riesgo modelo-vecino → medido y acotado (c-ii).
- **(e) Estado**: NADA en prod aún — **PR #85** contra main (Alberto mergea → Railway despliega). Rollback = revertir el commit (cambio aislado a una rama del handler; sin migración ni datos).
- **Alternativas descartadas**: fall-through "a secas" (tocaría `CUT_A_mismatch` → incurre en la mis-atribución que avisó el cross-model en s76); backfill de `product_model` (#49 prohíbe ciego + prerequisito F2-writer + es familia↔variante = decisión del contrato de ingesta); umbrella→variante en `extract` (Brazo A/`LEVER2_IDENTITY`, ortogonal al gate, gated a ingesta-30+, ~0 palanca eval DEC-054); no hacer nada (el falso-refuse es bug de prod real).
- **Gaps declarados**: reach≠PASS, sin delta de eval (corrige prod, no la métrica); los 3 mismatch (RP1r/ASD/ADW=Securiton-OEM) siguen mal-manejados → contrato de identidad #49; 1 sola sonda-ausente FIEL de marca dominante; sin enforcement de marca downstream (se apoya en `_filter_to_query_models` + conducta del generador); "No dispongo de manuales de X" = política limitada (OEM/relabel podría tener el manual bajo la matriz).
- **Relacionado**: DEC-058 (PROD-REACH lo midió + lo priorizó), TECH_DEBT #49 (gate/identidad) · #4 (revisión = siguiente candidato cercano), lección #40 (smoke por handler real) + #42 (`feedback_my_bias`, reincidente sobre medidas), `scripts/s77_{gate_audit,fallthrough_measure,regression_probes,handler_smoke}.py` + `evals/s77_{gate_audit,fallthrough_measure,regression_probes}.yaml` + `_s77_gate_fix_design.md` + `adversarial_review_log.jsonl` s77, PR #85, rama `eval/s77-gate-fix-49`.

## DEC-060 — s78: curación de identidad del corpus (ground-truth de Alberto, 4 familias) → BACKFILL A APLICADO en prod (correcciones de marca/etiqueta eval-inertes) + backlog D1-D6; lecciones HNSW (UPDATE masivo→timeout) + eval-economía

- **Fecha**: 16 jun 2026 (s78). **Impacto**: MEDIO-ALTO (escribe en PROD `chunks_v2`+`documents`; zona de dolor identidad/corpus → dúo #8 Protocolo 3 [sub-agente Opus + cross-model GPT-5.5], 0 FP). **Disparador**: plan "1+2" de s77/s78 — Alberto eligió atacar la identidad del dato (thread 1) "por mejoras estructurales, sin trampas al solitario".
- **(a) Curación con ground-truth de Alberto (4 familias, en memoria `reference_*`):** CAD-150 (familia↔variante + pág↔aplicabilidad); Morley ZX (ZX1e/2e/5e por lazos; ZXAE/ZXEE producto DISTINTO; **ZXSe**=ZX1Se/2Se/5Se/10Se familia MODERNA, vive en `MIE-MI-600` tagueado `unknown`; ZXR50A con teclado vs P sin; **"ZXe" no existe→clarify**); RP1r (4 productos: **RP1r-Supra=Notifier** [el corpus lo tenía Morley, ~312 ch], RP1r-a-secas=Notifier extinción, **VSN-RP1r=Morley**, OPC-RP1r=software); FAAST (System Sensor LT-200 / Xtralis FLEX, Honeywell; **NFXI-ASD=Notifier** [el corpus Securiton]). **Securiton = marca APARTE** (Detnov la vende en ES), NO Honeywell.
- **(b) Paso 0/0b (diagnóstico judge-free, $0):** de los 16 retrieval-miss, solo ~4 son identidad-bloqueada; **~12 son retrieval-MECÁNICO** (el filtro substring ya absorbe el colapso de familia donde la variante macheada es la correcta) → **confirma s75 (identidad ⊥ el cuello del eval)**; 3 NO eran retrieval (cat013 refuse / cat021 clarify / hp009 identidad). Punto-de-muerte por-gold: ventana-rerank 7 / within-doc 3 / recall+FAAST 1 (cat007).
- **(c) Partición HONESTA:** **Backfill A = correcciones de etiqueta PRIMARIA standalone + eval-inertes** (aplicado, ver d). La **findability de variantes (ZXSe/ZX1e) NO va en A** — VERIFICADO que el tag combinado NO basta (`extract("ZX5Se")=[]`; el catálogo trata el combinado como 1 token) → necesita split en `build_model_catalog.py`+regen (NO eval-inerte) = **D1**. Levers de retrieval de los ~10 (preview-2400/within-doc) = **D2**. Findability multi-marca (grupo Honeywell + alias OEM↔vendedor) = **D3/TECH_DEBT #5** (trigger cumplido).
- **(d) Backfill A APLICADO (`scripts/s78_identity_backfill.py`, s64-style, reversible):** FIX1 RP1r-Supra Morley→Notifier (312) + FIX2 NFXI-ASD Securiton→Notifier (135) [+7 `documents`] + FIX4 NFXI-FLX (83) + canon ZX-50→ZX50 (126)/ZXr-A-P→ZXR50A-P (18)/RP1R→RP1r (65) = **447 mfr + 292 pm**. Verificado: count-match exacto → before-snapshot (`evals/s78_backfill_snapshot.json`, rollback) → apply (GO de Alberto) → `from`==0 ∀ → **smoke handler 4/4 (LIVE: "Notifier RP1r-Supra" deja de dar mismatch-refuse)** → **eval-freeze 9/39** (vs ~10/39 base = dentro del ruido del juez ±2/K-inestabilidad; **CERO PASS→FALLO; cat022 intacto**). Valor = corrección de PROD + escala, ~0 eval (eval-inerte: la marca no entra al prompt + las canon no mueven selección).
- **(e) Lección operativa HNSW (reusable D1/D3):** el 1er apply falló con `statement timeout` — un UPDATE masivo en `chunks_v2` re-inserta cada fila en el índice HNSW. Estado verificado (regla-C, logs Supabase): **rollback atómico limpio, 0 cambios parciales**. Fix: **PATCH en lotes de 10** (bajo el timeout, idempotente vía from-value en el WHERE). Todo backfill futuro sobre `chunks_v2` debe batchear.
- **Dúo #8 (sub-agente Opus + cross-model GPT-5.5 sobre el spec): 7/7 + 5/5 confirmados, 0 FP.** Cazó la cifra inflada de FIX1 (~624→312 = bias #42/#43 cifras REINCIDENTE, esta vez cazada **también por el sub-agente Opus vía DB**, no solo el cross-model) + rollback-sin-snapshot-de-documents + smoke-ZX5Se-vacuo + eval-freeze-por-razón-equivocada → todo corregido ANTES del apply.
- **Alternativas descartadas**: bundlear D2 en el backfill (conflación de variable, D2 no listo, viola higiene s74); tag combinado SIN split de catálogo (no da findability — `extract=[]`); per-sección/per-chunk ahora (Capa 2).
- **Gaps / backlog D1-D6 (en `evals/_s78_identity_backfill_spec.md` §DIFERIDO + memoria):** D1 findability ZXSe/ZX1e; D2 levers retrieval ~10 golds; D3 Capa-2 multi-marca #5; D4 #4 revisión (v04/v07 HLSI-MN-103, near-dups); D5 sección↔variante; D6 gold hp009/hp018→clarify. RP1r-Supra queda multi-mfr post-fix (NL-Honeywell fuera de scope).
- **Eval-economía (lección, pariente s27):** corrí el eval-freeze a un cambio PROBADAMENTE eval-inerte = información marginal por coste real (Alberto lo señaló). Regla: NO pagar eval a lo ya-probado-inerte (argumento + count-match + reach/smoke bastan); reservar el eval pagado para los cambios que MUEVEN el número (el A/B de D2).
- **Relacionado**: DEC-059 (gate-fix #49, identidad en prod), DEC-058/057/054 (identidad medida/diferida), TECH_DEBT #49 (identidad) · #5 (grupo corporativo, trigger cumplido) · #4 (revisión), memoria `reference_{detnov-cad150,morley-zx-rp1r,faast}` + `feedback_my_bias`, `scripts/s78_*`+`retrieval16_*`+`cad150_corpus_probe.py` + `evals/s78_*` + `_s78_identity_backfill_spec.md` + `adversarial_review_log.jsonl` s78 (dúo #8), rama `eval/s78-identity-backfill` → PR.

## DEC-061 — s79: gate pre-D2 → el matcher de recall (`chunk_has_quote_strict`) está ROTO (FP/FN) y contaminó las conclusiones de retrieval de la sesión; el plan de revisión de los 30 NO-PASS VIVE pero su INSTRUMENTO necesita arreglo (dúo CON-CAMBIOS, no escalar aún); lección SOBRE-INSTRUMENTACIÓN + sobre-corrección

- **Fecha**: 17 jun 2026 (s79). **Impacto**: MEDIO-ALTO (define el MÉTODO del audit que dirige el roadmap; zona de dolor eval-instrument/retrieval → **4 cross-model GPT-5.5 + 1 workflow 7-lentes Opus, 0 FP que sobrevivan regla-C**). **Disparador**: Alberto pidió, ANTES de D2, entender los flips del eval + el porqué del fallo de retrieval (gate antes del lever, Protocolo 4). NADA shippeado a prod (toda la sesión = investigación + diseño; main intacto).
- **(a) Flips 9-vs-10 = ruido del juez (verificado por-gold):** 9/39 (`test_bot_vs_gold` single-pass) vs 10/39 (s67base K-mayoría); los 5 golds que difieren eran TODOS K-inestables en el baseline; cat007 NO flipeó. Single-pass vs K-mayoría sobre golds inestables = ruido, no señal del backfill s78.
- **(b) HALLAZGO mayor (regla-C, SQL + dúo): `chunk_has_quote_strict` (`strict_match.py:122`) está ROTO.** FALSO-POSITIVO (`all(a in nc)` con `in` crudo: `'24'∈'240'`, `'2222'∈cualquier chunk`) Y FALSO-NEGATIVO (prosa OCR → `overlap≥0.8`). Mis probes s79 (`recall_deathstage`/`vecrank`/`burial`) lo usaban → **sus conclusiones (rank-53/64/87, "within-doc muerto", "corpus-gap" cat016/cat007) NO son fiables**. cat016/cat007 SÍ están en el corpus (SQL verificado) — el "corpus-gap" era FN del matcher. Cazado por el "¿estás seguro?" de Alberto. **A re-medir con predicado limpio (bias #35: no heredar el suelo).**
- **(c) Identidad FAAST (SQL-verificado, accionable):** familia FAAST LT-200 mal-tagueada en 3 manuales — `I56-6574` (autónomo, OEM System Sensor)=`FAAST LT-200`; `I56-6575` (addressable, OEM System Sensor)=`LT-200` (ES=System Sensor / EN=Notifier, inconsistente); `I56-6577` (addressable NFXI-ASD11/12/22, OEM Notifier-EXCLUSIVO)=`ASD11`. El tag `ASD11` EXCLUYE el chunk del failsafe ante query "FAAST LT-200" (`_filter_to_query_models`) → **candidato a backfill s78-style = mejora de retrieval VÍA IDENTIDAD, distinta de los levers de ranking cerrados por DEC-056.**
- **(d) Gold-flags:** cat007 "relé de avería FAILSAFE / se desenergiza" = **INFERENCIA del autor** (0 ocurrencias de "failsafe/desenergiza" en TODO el I56-6577; lo documentado es "señaliza en modo servicio + al desconectar la alimentación + no enclavado") — eléctricamente correcta + dúo-vetada, **NO fabricada** → flag gold-design (estricto-documentado vs inferencia-útil, DIFERIDO). **hp009 = answer family-GENÉRICO** (EOL invariante en la e-series → responder refiriendo a ZXe-familia; NO "clarify" en bruto — **corrige la nota de memoria**); hp018 = mixto (nº de sirenas variant-específico). Criterio clarify-vs-answer (RAG BP): clarify SOLO si la respuesta DIVERGE entre variantes; invariante → answer.
- **(e) Audit de los 30 NO-PASS por raíz — diseñado, dúo CON-CAMBIOS, `proceed_to_30=FALSE`.** Taxonomía cascada (CORPUS-GAP/RETRIEVAL-MISS/RERANK-MISS/SINTESIS) + predicado bimodal (anchor fuerte→`anchor_present`; prosa→juez semántico) + ejes ortogonales (generación/gold-design/judge). El dúo exigió arreglar el INSTRUMENTO antes de escalar: **(i)** el quote-path del funnel (`audit_retrieval_funnel.py:132`) AÚN usa el matcher roto para el ~63% de hechos (prosa); el juez semántico de C2 NO está implementado (descrito como hecho = **bias #44 reincidente**); **(ii) C6 invertido:** `audit_locator` tiene 2 fixes que el funnel NO tiene (source-tie per-fact + prose-token-containment OCR-robusto) → PORTARLOS, no dropearlo; **(iii)** C3 comparaba dos rerankers distintos (ruido de método) en vez de K-mayoría del reranker de PROD; **(iv)** C4 sin banda de error + fuente de veredictos equivocada (`_s45` 17 golds, no `bot_vs_gold_results_k5` 30); **(v)** C5 cobertura-de-generación corría sobre el mismo matcher roto (`s70_factcov`) + eje gold-design CIRCULAR contra `conducta_esperada`.
- **(f) Lección SOBRE-INSTRUMENTACIÓN + sobre-corrección (`feedback_my_bias #45`):** la sesión ESPIRALÓ construyendo aparato de medición cada vez mayor (probes → `audit_locator` → diseño del audit de 30); al frenar el dúo, **SOBRE-CORREGÍ a "abandonar el audit"** (bias #30: invertir tras corregir) cuando el dúo decía CON-CAMBIOS (arreglar y correr). Alberto lo cortó: el audit VIVE. + el "28/29 localizado" fue validación CIRCULAR (el localizador auto-calificándose, sin ground-truth independiente). El cross-model cortó mis over-claims 4 rondas (6ª-7ª sesión seguida) = control ESTRUCTURAL.
- **Decisión / qué sigue:** NO el audit pesado tal cual. **Próxima sesión = gold-review D6 (cat007/hp009/hp018, $0, primero) → backfill identidad FAAST LT-200 (s78-style) → arreglar el instrumento del audit (predicado limpio en el funnel + coste acotado + banda de error + fuente k5) → correr el audit de los 30 → priorizar (identidad/gold-design/generación/corpus).** dual-judge sigue gated (organic-eval ~sept).
- **Alternativas descartadas**: escalar el audit de 30 con el matcher roto (4 lentes lo cazaron); ABANDONAR el audit (sobre-corrección mía, Alberto lo cortó); `audit_locator` nuevo como instrumento (reinventa el funnel — pero AL REVÉS: tiene 2 fixes que portar al funnel).
- **Relacionado**: DEC-056 (levers de RANKING de retrieval agotados — SIGUE, NO re-litigado), DEC-060 (backfill s78), TECH_DEBT (matcher roto contamina `s79_*`/funnel quote-path/`s70_factcov`), memoria `reference_{faast,morley-zx-rp1r}` + `feedback_my_bias #45`, `scripts/{audit_locator,s79_*,test_audit_locator}.py` + `audit_retrieval_funnel.py` + `evals/_s79_*.md` + `adversarial_review_log` s79 (4 rondas), rama `eval/s79-retrieval-audit-gate`.

## DEC-062 — s80: backfill de identidad de la SERIE FAAST LT-200 APLICADO en prod (DB-only, findability de serie viva) + criterio gold core/supp=IMPORTANCIA (D6); verificado AL PÍXEL que NO arregla cat007 (downstream)

- **Fecha**: 17 jun 2026 (s80). **Impacto**: MEDIO (corrección de prod identidad/findability, zona de dolor corpus/identidad → dúo: workflow 3-fases Opus + 2× cross-model GPT-5.5, 6/6+7/7, 0 FP). **Disparador**: retomar el plan s79; Alberto pidió "hacer el backfill ya que objetivamente está mal" (correctness independiente de cat007, precedente s78).
- **(a) D6 gold-review (criterio, $0):** `core`/`supplementary` del gold codifica **IMPORTANCIA, no provenance** (BP con cita, cross-model: TREC vital/okay, RAGAS, DeepEval, ARES). NO demotar inferencias correctas a supplementary (las vacía del conjunto vital + las saca del audit `audit_retrieval_funnel.py:325` + baja la completitud del árbitro atómico `atomic_scorer.py:289` — el sub-agente Opus cazó que mi "scorer inerte a tipo" era FALSO). Inferencia válida si su predicado ⊆ lo documentado; no-invención se mide en el OUTPUT (`undue_inference_check`), no recortando el gold. **El eval CANÓNICO (juez holístico `bvg_kmajority`/`test_bot_vs_gold` sobre `gold_answer`) es INERTE a `tipo`** → core/supp gobierna el audit/diagnóstico, NO el veredicto (responde el pushback de Alberto "¿necesitamos core/supp?"). cat007 "failsafe"=inferencia VÁLIDA (comportamiento en p5, etiqueta no-textual) → SIN editar tipo; hp009/hp018 conducta `answer` correcta. Sin tocar golds.
- **(b) Crux cat007 RESUELTO AL PÍXEL** (Alberto: "¿no deberías evaluarlo tú al píxel sin preguntarme? si no, no escala"): render p5 de los 3 QIGs → standalone (6574) vs addressable (6575/6577) DIFIEREN (6574 relé PREALARMA; addressable lazo) PERO los hechos de cat007 (alarma/avería NC-C-NA, sirenas 47kΩ, 2/0,5A, 10⁵, no-enclavado) IDÉNTICOS en las 3 → cat007 alcanzable vía 6574 → **el backfill NO arregla cat007** (su NO-PASS es downstream: rerank/gen/es-en/gold). Corrige la premisa de la memoria s79.
- **(c) Backfill APLICADO en prod (`s80_faast_backfill.py`, s78-style, GO de Alberto):** FX1 (6575 `LT-200`→`FAAST LT-200` 78) + FX2 (6575-ES mfr `System Sensor`→`Notifier` 41) + FX3 (6577 `ASD11`→`FAAST LT-200` 73); count-match → before-snapshot (`evals/s80_faast_backfill_snapshot.json`) → apply lotes-de-10 → `after` from-value=0 ∀; reversible. **Findability de serie VIVA, verificada contra el estado REAL de prod (catálogo s55 + DB):** "FAAST LT-200" alcanza standalone+loop+ASD (antes solo standalone; "FAAST LT-200" se extrae por PATRÓN ESTÁTICO = catalog-independiente). Smoke COULD-regress OK. DB-only (como s78), NO deploy de código.
- **Decisiones de convención (Alberto):** manufacturer=`Notifier` pragmático (el seam multi-marca NO existe → System Sensor regresaría findability Notifier/Morley; OEM real System Sensor + visibilidad Morley → D3); 6577 pm=`FAAST LT-200` serie (modelo NFXI-ASD11/12/22 recuperable como metadata para D3, PERO el path de usuario bare "NFXI-ASD11"→6577 se pierde-hasta-D3 — corregido del erróneo "no se pierde", cross-model).
- **NO es eval-inerte** (≠ s78): product_model es visible al generador (`generator.py:452`) + mueve la selección → guardarraíl = findability-POSITIVO por handler real (lección #40) + no-regresión NEGATIVO full-eval. Riesgo cross-gold BAJO (DB-only localizado: solo cat007 en la familia FAAST; "LT-200" sigue matcheando por substring; ASD535/532 son Detnov, token distinto).
- **Alternativas descartadas**: demotar "failsafe" a supplementary (sobre-corrección mía, cross-model lo cortó); tag combinado para 6577 (wrinkle de split de catálogo, beneficio hipotético-ahora); manufacturer=System Sensor ahora (regresaría findability sin el seam); desplegar el regen del catálogo en s80 (bundlea s55→hoy = blast radius → DEC-063, tarea separada).
- **Lección `feedback_my_bias #46` (extiende #42/#43):** la sobre-afirmación del FRAMING reincidió 3× en s80 ("scorer inerte a tipo" [el sub-agente Opus lo cazó vía atomic_scorer], "el modelo NO se pierde", "corrección ESTRUCTURAL", "FINAL") — cortada por el cross-model (6/6) cada vez = control ESTRUCTURAL estable. + verificar hechos de dominio AL PÍXEL yo mismo (Alberto: preguntar no escala a 30+).
- **Relacionado**: DEC-060 (backfill s78, mismo patrón), DEC-063 (catálogo-stale, hallazgo de esta sesión), DEC-056 (levers de ranking agotados — el backfill es identidad, OTRA clase), memoria `reference_{faast,morley-zx-rp1r}`, `scripts/s80_faast_backfill.py` + `evals/_s80_*.md` + `adversarial_review_log` s80 (2 cross-model + 1 workflow), rama `eval/s80-faast-identity-backfill`.

## DEC-063 — s80: HALLAZGO LATENTE — `data/model_catalog.json` congelado en s55; prod LEE el json (no reconstruye) → el detector dinámico no refleja s64/s77/s78, PERO el gate lee la DB live → s77/s78 SÍ vivos (latente, no bug activo)

- **Fecha**: 17 jun 2026 (s80). **Impacto**: MEDIO (completitud de extracción de modelos en prod; NO la corrección de marca). **Disparador**: al regenerar el catálogo para el GUARD-REGEN del backfill FAAST, el diff salió MUCHO más amplio que FAAST (RP1r/NFXI-FLX/ZX50/ZXR50 = targets de s64/s77/s78) → regla-C.
- **Hallazgo**: `data/model_catalog.json` se commiteó por última vez en s55 (`8876e56`); `src/rag/catalog.py:_load()` LEE ese json (`json.loads(_SNAPSHOT_PATH)`), NO reconstruye de la DB. Railway despliega `main` → **prod corre un detector de modelos s55**. Los backfills de identidad post-s55 (s64/s77/s78) cambiaron `chunks_v2` pero NO el catálogo (DEFECTO-4 era la punta del iceberg).
- **PERO NO es bug activo (verificado en código):** el gate del handler lee la DB LIVE — `lookup_model_manufacturer` (retriever.py:716), `manufacturer_in_db` (:788), `get_available_manufacturers` (:743) son httpx a Supabase `chunks_v2`. → la decisión de MARCA del gate (mismatch-refuse/fall-through, gate-fix #49) es live → **s77/#49 + identidad s78 SÍ plenamente vivos en prod; el catálogo-stale NO puede dar una decisión de marca errónea.** Lo único catalog-dependiente es `extract_product_models` (DETECCIÓN de modelos = catálogo s55 ∪ patrón estático); impacto BAJO: los modelos clave son patrón-estático, y un miss post-s55 cae a fall-through-a-RAG (seguro, no falso-refuse).
- **Decisión / qué sigue**: catálogo-stale = LATENTE, no urgente. Higiene a backlog (baja prioridad): re-sync s55→hoy del catálogo (completitud de extracción post-s55, blast radius 4 sesiones → full no-regresión eval bajo freeze-contract) + check CI que falle si `model_catalog.json` desincroniza con la DB (anti-recurrencia). GUARD-REGEN de s80 NO desplegado (no necesario; entangled con esto). Tarea-chip spawneada y luego RETIRADA (premisa "s77/s78 no vivos" refutada por código).
- **Alternativas descartadas**: desplegar el regen en s80 (bundlea s55→hoy sin eval); alarmar "s77/s78 rotos en prod" (refutado — el gate lee la DB live).
- **Relacionado**: DEC-062 (el backfill que lo destapó), DEC-059 (gate s77), DEC-060 (s78), memoria `reference_faast` (registrado), TECH_DEBT (catálogo desincronizado con la DB + falta auto-regen/CI).

## DEC-064 — s81: instrumento del audit ARREGLADO (DEC-061) + audit de los 30 NO-PASS CORRIDO → distribución de raíces (RECALL ~38% ≈ GENERACIÓN/GOLD ~37% co-binding; RERANK ~7% confirma DEC-056; identidad re-validada VÍA RETRIEVAL)

- **Fecha**: 17 jun 2026 (s81). **Impacto**: MEDIO-ALTO (define el MÉTODO del audit + produce el histograma que dirige el roadmap; zona de dolor eval-instrument/retrieval/esquema → dúo #9 = **3 rondas: 3 cross-model GPT-5.5 + 3 sub-agente Opus, 0 FP**). **Disparador**: Alberto pidió MÁS autonomía (contrato nuevo `feedback_autonomy`: actúo-y-reporto, el dúo es el anti-bias, stop-line=merge lo da él). Ejecuté el plan SANCIONADO DEC-061. **Re-secuencié D1 detrás del audit** (el orden de DEC-061, no el del cierre s80) tras verificar al píxel que NINGÚN gold canónico (`gold_answers_v1.yaml`) apunta a ZXSe → la findability-D1 era **eval-inerte** + el regen del catálogo arrastra el blast-radius DEC-063 → el audit localiza DÓNDE importa la identidad antes de pagar eso.
- **(a) Instrumento arreglado** (los 5 defectos de DEC-061(e); `scripts/audit_locator.py` + `audit_retrieval_funnel.py`): el matcher ROTO `chunk_has_quote_strict` se RETIRÓ del funnel (conservado solo para `bvg_kmajority` legacy, fuera de scope). Predicado limpio `fact_match_score` **VALOR-EXIGIDO**: el datum distintivo (nº≥2díg / código) DEBE estar (cov>0) + el `texto` como CONTEXTO que desambigua → mata el FP 'prosa del enunciado sin el dato' (crít r3) Y el FN del token-corto (NC-C-NA, r1). `measurable` segrega valores no-verificables léxicamente (single-digit `1 A`/`4 circuitos`, frases sin tokens → **no-medibles**, candidatos al juez semántico DIFERIDO). Confianza del bucket por SCORE del match (borderline=[0.55,0.70)), NO a priori del enunciado (r2: el `fact_tier` a-priori colapsaba la banda). Source-tie fail-open + **primario-vs-corroborador** (`primary_tokens=doc_tokens(fuente)` aparte; flag `PRIMARIO-NO-RECUPERADO`). Fuente de veredictos = `bot_vs_gold_results_k5.yaml` (los 30, no s45). K=1 (reranker temp=0, jitter nulo verificado, dúo r3). 8 tests (5 originales + 3 que codifican los FP/FN del dúo) + 353 tests verdes.
- **(b) Dúo #9 (3 rondas, 0 FP) — cazó defectos REALES en cada ronda** (`adversarial_review_log.jsonl` s81): r1/spec (anchors-FP-mismo-manual, FIX-A↔D-contradicción, short-token-FN); r2/diff (**REGRESIÓN que YO introduje**: el refactor rompió `fact_probe`/`_chunk_has`/`present_in` que `bvg_kmajority` importa — cazada por GREP regla-C, NO el dúo → legacy restaurado; + source-tie corroborador-enmascara-primario [hp018: pool=MI-310, MI-530 primario no entra] + tier-a-priori-colapsa-banda); r3/diff-corregido (el FP '`1 A` marcado SINTESIS por la prosa sin el dato' → predicado valor-exigido; corroborador→SINTESIS = decisión semántica DECLARADA + flag). **Cap en r3 (sin round-4):** el valor-exigido se verificó por TESTS, no por 4º dúo (anti-#45). El cross-model cazó framing que el sub-agente Opus (mismo modelo) compartía = control ESTRUCTURAL (consistente s77/s80).
- **(c) RESULTADO — histograma de los 30 dev NO-PASS** (~93 hechos core medibles, +19 no-medibles; `evals/dec003_retrieval_funnel_noTgt_llm.yaml`): **RETRIEVAL 28-38** (recall: hecho EN el manual, NO en pool-50) **≈ SINTESIS 34-39** (el generador lo VIO → gen/gold/juez) **>> RERANK-MISS 6-7 >> CORPUS-GAP 9** (riesgo FN). banda=16 borderline; **4 PRIMARIO-NO-RECUPERADO** (cat011/cat019/hp001/hp018 = el manual primario no se recupera, el corroborador en su lugar).
- **(d) LECTURA / qué decide:** DEC-056 (levers de RANKING agotados) se **CONFIRMA** (RERANK solo ~7% → el reranker NO es el cuello) **pero se MATIZA**: el RECALL (~38%, el chunk ni entra al pool — lever DISTINTO del ranking) NO está cerrado, y es en parte **IDENTIDAD** (los 4 PRIMARIO traen el corroborador en vez del primario) → **RE-VALIDA D1/D3 como lever de eval VÍA el bucket RETRIEVAL** (no findability-por-sí-misma). Los dos cuellos co-binding: recall/identidad y generación/gold/juez. El orden instrumento-primero PAGÓ (localizó dónde importa la identidad; cierra el fork del inicio honestamente).
- **Caveats declarados**: cubre 83% de los hechos (19 no-medibles → juez semántico diferido); corroborador cuenta como SINTESIS (decisión semántica defendible, los flags PRIMARIO marcan lo peor); 9 CORPUS-GAP = riesgo FN es-en/OCR (verificar a mano); el `texto` puede llevar meta-comentario del autor (cat007 `10^5`).
- **Alternativas descartadas**: correr el audit con el matcher roto (DEC-061 lo prohibió); juez semántico LLM ahora para toda la prosa (#45 + jitter; el valor-exigido basta para la DISTRIBUCIÓN); matchear el texto-prosa solo (FP '1 A', cazado r3); K=5 (reranker temp=0 → desperdicio #45); tocar el diagnóstico de `bvg_kmajority` (fuera de scope DEC-061; legacy preservado + **chip spawneado** para su fix de robustez citations-str); re-arquitectar el bucket para excluir corroborador (decisión semántica defendible + flag PRIMARIO).
- **Gaps**: 17% de hechos no-medibles (juez semántico diferido); el audit da la DISTRIBUCIÓN, NO el deep-dive por-SINTESIS (C5 = siguiente); cat007 `manual_chunks` sin-tie puede traer otro miembro de serie (verificado: no muerde en los 30).
- **Relacionado**: DEC-061 (plan sancionado), DEC-056 (ranking agotado — confirmado + matizado por el RECALL), DEC-060 (D1/D3 identidad re-validada), `feedback_autonomy` (contrato s81), `feedback_my_bias #45` (sobre-instrumentación — capé en r3), `scripts/{audit_locator,audit_retrieval_funnel,test_audit_locator}.py` + `evals/_s81_audit_instrument_spec.md` + `evals/dec003_retrieval_funnel_noTgt_llm.yaml` (histograma de los 30) + `adversarial_review_log` s81 + rama `eval/s81-zx-d1-audit-instrument`.

## DEC-065 — s82: investigación CORPUS-GAP → 0 de 9 son reales (todos FN del matcher léxico es-en/OCR del audit s81); 2 de 4 PRIMARIO = falso-positivo de source-naming; el cuello real es RECALL → plan de ataque A/B/C

- **Fecha**: 17 jun 2026 (s82). **Impacto**: MEDIO-ALTO (reclasifica un bucket ENTERO del audit s81 + redirige el roadmap de retrieval; zona de dolor retrieval/corpus/identidad → **workflow 29-agentes Opus [investigación + verificación adversarial FRESCA] + cross-model GPT-5.5 = dúo #10, 0 FP** + regla-C propia al píxel). **Disparador**: Alberto, tras mergear PR #88 (s81), pidió planear el ataque a los 4 PRIMARIO + bucket RETRIEVAL y, como PRIORIDAD, investigar el CORPUS-GAP ("estoy casi seguro de que no existe").
- **(a) Herramienta**: `scripts/corpus_grep.py` (búsqueda ILIKE full-corpus de `chunks_v2` por CONTENIDO, ES+EN, devuelve source_file/página/pm/snippet) — reusable para D1/D3/auditorías futuras. Scout `evals/_s82_worklist.py`/`.json` (gitignored).
- **(b) VEREDICTO CORPUS-GAP (acotado, post-cross-model): de los 9 CORPUS-GAP del audit s81, los 9 son FALSOS NEGATIVOS del matcher léxico** (`fact_match_score`, ILIKE español-exacto + frontera). El valor está VERBATIM en el corpus, casi siempre en el manual OBJETIVO del gold. Verificado: workflow (verificadores frescos volcaron los chunks REALES de la DB) + **regla-C propia al píxel** (cat007 tabla-relé FAAST 6574/6577; cat020 `DXc_Manual variaciones de mercado` INGERIDO p6 defaults España "Fuego:Niv4 Prealarma:Niv3" — dudé y la evidencia CONFIRMÓ; hp013 EEPROM en ADW535). **Causa raíz: es-en + OCR/acento + sesgo español-literal** (dominante: LlamaParse extrae la columna EN de manuales multilingües → cat013 "closed loop", cat007 NA↔NO; OCR cat011 "INTRÍSECA"; literal-compacto NC-C-NA/99+99; filename≠doc-nº cat020). Es el residual es-en que s81 declaró como caveat del juez-semántico-DIFERIDO → **PROBADO material** (fabricó el bucket entero). **Alcance HONESTO (corte cross-model): probado para estos 9 en este índice; NO prueba "0 corpus-gap en general"; "0 ingesta nueva" aplica A ESTOS 9, no descarta gaps escaneados/multi-doc/OEM en otros hechos.**
- **(c) Histograma corregido: CORPUS-GAP 9→0.** Los 9 NO desaparecen del problema: reubican a RETRIEVAL (el chunk-valor/ES no entra al pool, el hermano EN sí) o **downstream-gen/conducta** (hp012 = conflicto US-ES = answer-con-conflicto, NO recall — cross-model: no contaminar el plan C con esto).
- **(d) PRIMARIO: 2 de 4 reales.** cat019/hp001 = **FALSO POSITIVO de source-naming** (token gold `CAD-250-MC-380-es` no substring-machea el filename `CAD-250_Manual-Configuracion-MC-380-es-2026-c`; el primario es el #1 del pool) = artefacto del INSTRUMENTO del audit, no del bot. cat011 = real-miss pero **reach≠PASS** (el bot ya clarifica bien, gobernado por `model_catalog.json`). hp018 = real-miss, **model-filter-excludes** ('ZXe'→pm equivocado 'zxae/zxee').
- **(e) Cuello real = RECALL** (DEC-056 SIGUE: ranking agotado; recall es lever DISTINTO). model-filter-excludes ×3 (hp018/hp002/hp006) + recall-frontier-vector ×6 (cat011/hp001-fact2222/cat017/hp005/hp008/cat016) + source-naming-artifact ×2 (instrumento).
- **(f) PLAN A/B/C** (separar PROD-del-bot de INSTRUMENTO/GOLD):
  - **A. Instrumento/gold (el bot NO cambia; BAJO; no-eval; PRIMERO, descontamina):** A1 matcher CORPUS-GAP es-en/OCR-aware (raíz de los 9 FN; **versionar/congelar — cambia históricos; anclar el juez semántico a FUENTE con citas, no proxy opaco** [cross-model]; codificar el aprendizaje para no re-pagar el workflow); A2 matcher PRIMARIO slug-laxo (cat019/hp001 ruido); A3 atribución gold cat011.
  - **B. PROD model-filter (el bot MEJORA; MEDIR end-to-end ANTES de mergear):** B4 hp018 **CANDIDATO** flip `LEVER2_IDENTITY=ON` (ya construido; pool 0→11 = reach, NO PASS → medir held-out [cross-model/#46]); B5 hp006 series-registry AFP-300/400 (mismo seam CAD-250, escalable a 30+); B6 hp002 broad-fallback + sanear category-sink.
  - **C. PROD recall-frontier (lever común; MEDIR — delta no presupuesto):** C7 within-doc/family diversify ± ef_search (**necesita contrato + métrica de regresión** [cross-model]; verificar que es RECALL no re-ranking → no re-litiga DEC-056/s59/s74); C9 cat016 synonym-aware (el duro); C8 cat011 opcional (reach≠PASS).
  - **Orden**: A → B4 → B5/B6 → C7 → C9.
- **Gaps/riesgos**: B/C sin delta medido (reach≠PASS en cat011/cat019/hp001 = no mueven la métrica); A1 es arreglo del INSTRUMENTO del audit (mejora el diagnóstico, NO la métrica) — el es-en en PROD (el bot no recupera el chunk ES) es un arreglo DISTINTO del bot; hp012 (conflicto regional) necesita conducta explícita (surfacear ambos), no resolver por recall/gold.
- **Control**: workflow 29-agentes (9 inv + 9 verify FRESCO + 10 diag + synth) + cross-model GPT-5.5 (dúo #10, 8/8 + 13/13, 0 FP) + regla-C propia al píxel (3 casos; dudé de cat007/cat020 y la evidencia confirmó). El cross-model cortó el over-claim de framing (#42-#47, 6ª sesión seguida = control estructural estable). **NADA en prod** (diagnóstico; código branch-local = `corpus_grep.py`).
- **Relacionado**: DEC-064 (el audit s81 que produjo los buckets; A1 corrige su matcher), DEC-056 (ranking agotado — recall es lever distinto), DEC-060/063 (identidad D1/D3 → hp018/hp006), `feedback_my_bias` (#42-#47 framing), `scripts/corpus_grep.py` + `evals/_s82_findings.md` (local) + `adversarial_review_log` s82 (dúo #10) + rama `eval/s82-recall-corpusgap`.

## DEC-066 — s83: el pre-filtro vectorial family-aware (headline construido) = NO-OP MEDIDO → revertido; el lever de los model-filter-excludes es LEVER2_IDENTITY (resolución de identidad), que recupera el manual correcto pero reach≠PASS (hp018 residual; hp009 residual→K-INESTABLE)

- **Fecha**: 18 jun 2026 (s83). **Impacto**: MEDIO-ALTO (redirige el headline de retrieval; zona de dolor retrieval/identidad → **dúo #11: sub-agente Opus + cross-model GPT-5.5, AMBOS cazaron el confound independientemente**). **Disparador**: Alberto pidió plan-primero + máxima autonomía (ultracode); tras **5 rondas de pushback** fijó el headline = filtro de modelo a nivel DOCUMENTO/familia (su punto 1: el canal vectorial no pre-filtra por modelo) + diferir categorías/versiones/bilingüe.
- **(a) Construido (Pieza 1c)**: pre-filtro FAMILY-AWARE del canal vectorial (flag `MODEL_PREFILTER`, default OFF) — over-fetch `PREFILTER_FETCH_K=200` SIN filtro en el ANN (sin recall-cliff de HNSW) + filtro client-side a la pertenencia family-aware recall-safe (`series_registry.passes_nivel2` ∪ `product_model` unknown/null, familia-primero-relleno tras Fix B del dúo, fail-open) → recuperar el chunk model-correcto que la búsqueda ancha empuja fuera del top-k.
- **(b) VEREDICTO: NO-OP MEDIDO → REVERTIDO (eval-driven).** Aislamiento 2×2 (funnel judge-free, hp018): `LEVER2_IDENTITY` **SOLO** recupera el primario (PRIMARIO False→True, MIE-MI-310 corroborador → MIE-MI-530 e-series); `MODEL_PREFILTER` **SOLO = inerte** (PRIMARIO False). Mecanismo: al resolver ZXe→ZX2e/ZX5e, los canales **LÉXICOS** (que YA pre-filtran por modelo, `imatch product_model`) recuperan el manual; el canal vectorial no necesita pre-filtrar (+ el post-filtro `_filter_to_query_models` limpia su ruido y NIEGA el unknown-inclusion del pre-filtro → estructuralmente redundante). → **el punto 1 de Alberto es real (el vectorial no pre-filtra) pero el sistema ya compensa vía los canales léxicos; el cuello era la RESOLUCIÓN de identidad, no el canal vectorial.**
- **(c) El lever real = LEVER2_IDENTITY (B4, ya candidato en DEC-065).** bvg K=5 (hp018+hp009, base vs treat, juez GPT-5.5): el freeze recupera el e-series correcto (MIE-MI-310→MIE-MI-530) en AMBOS. **hp009 residual→K-INESTABLE** (mejora: gana votos PASS); **hp018 residual→residual** (recall arreglado, residual reatribuido INDETERMINADO→SUB-RETRIEVAL; **reach≠PASS** — el residual es generación/completitud: omite el diodo de polarización). Single-pass: hp018 FALLO→PARCIAL. **= GRIS** (movimiento positivo + 0 regresión, pero 0 PASS-control limpio → no cruza el umbral SHIP Δ_net≥+2). DEC-065 predijo reach≠PASS para hp018.
- **(d) Dúo #11**: sub-agente Opus (veredicto NO-SÓLIDA, 2 críticos) + cross-model GPT-5.5 (6/7) **cazaron el MISMO confound** (el efecto medido lo produce LEVER2_IDENTITY, no el pre-filtro) INDEPENDIENTEMENTE. 6/7 (cross) + 5/6 (sub) confirmados, 0 FP, severity_max=crítico. Es el sesgo de over-claim de framing (#42-#48) cortado por **7ª sesión seguida = control estructural**.
- **(e) Pieza 3 (bilingüe, read-only, $0)**: es-en = lever PEQUEÑO. 9 pares ES/EN casi-idénticos (444 ch → ~205 EN duplicados; dedup $0, ojo cat007 cita ambos); EN-only REAL = solo 2-3 golds (~21 ch: cat010, cat011-parcial; ~$20-50 traducir el lote). Hallazgo nuevo: **ho002/ho014 = ModuLaser NO ingestado (corpus-missing, NO bilingüe)**. → fork s84 (dedup → traducir EN-only).
- **Gaps/riesgos**: B4 reach≠PASS (no mueve la métrica headline, pero arregla la confusión de familia ZXe↔ZXAE/ZXEE + mejora hp009 + recupera el manual correcto) → **candidato de ship con valor de CORRECCIÓN, no de métrica; decisión de Alberto**. El pre-filtro NO se probó en recall-frontier golds (donde los léxicos podrían fallar) — revisita posible si la identidad no los cubre. **DIFERIDO a s84**: A1 (matcher es-en + histograma verdadero), limpieza broad de identidad (~78 pm-compuesto + 114 mis-atribución del audit 1a), B5 (hp006 AFP-400 series), categorías (TECH_DEBT #44), versiones, fix bilingüe.
- **Control**: NADA en prod, NADA mergeado; pre-filtro revertido (353 tests verdes restaurados); held-out intacto. **Relacionado**: DEC-065 (B4 candidato — este lo MIDIÓ → reach≠PASS confirmado bajo K-mayoría), DEC-056 (ranking agotado; esto es recall vía identidad, lever distinto), DEC-060/063 (identidad D1/D3), `feedback_my_bias` (#49), `scripts/{audit_retrieval_funnel,bvg_kmajority,adversarial_review}.py` (reusados) + `evals/_s83_*` + `adversarial_review_log` dúo #11 + rama `eval/s83-retrieval-model-aware`.

## DEC-067 — s83 (F2): activo de identidad multi-label LIMPIO de los 1014 docs construido (Capa 1 JSONL crudo + Capa 2 tablas normalizadas) vía extracción dúo + adjudicación de Alberto; regla de granularidad + base-unión dúo-validadas (3 rondas); branch-local, NADA en DB

- **Fecha**: 29 jun 2026 (s83, bloque F2 — la identidad limpia que DEC-066 señaló como el lever real, `LEVER2_IDENTITY`). **Impacto**: ALTO (activo foundational de identidad; zona de dolor identidad/esquema → **dúo COMPLETO ×3**, sub-agente Opus + cross-model GPT-5.5 INNEGOCIABLE). **Disparador**: el lever de DEC-066 era la RESOLUCIÓN de identidad; F2 = construir esa identidad limpia y multi-label para TODO el corpus, no solo golds-touching.
- **(a) Qué se construyó (2 capas, salida re-transformable)**: por cada uno de los 1014 docs, un registro multi-label (qué modelos cubre). **Capa 1** = JSONL crudo del dúo (Opus 4.8 + GPT-5.5, structured-output forzado, **~$145 Batches API**; re-leer=re-pagar). **Capa 2** = tablas normalizadas `document_models` (1 fila=1 producto físico) + `document_identity` (re-transform $0, re-ejecutable). Resultado: **1014 docs, 2761 productos, 36 `compatible_with`**.
- **(b) Reconciliación + adjudicación**: dúo coincide→auto; conflict→Alberto. Canonicalización por key-set (model∪canonical∪aliases) colapsó conflicts **120→29** (el 76% era ruido de superficie). Los **29 los adjudicó Alberto** (verdad de dominio) por la prueba **covers-vs-mentions** (cubre = contenido accionable SOBRE el producto; menciona = compatibilidad/objetivo/accesorio → `relations`/`mentions`, NO covered). Findability lens: "¿este doc serviría a un técnico que tiene este producto?".
- **(c) Regla de granularidad (dúo r10, Fix1)**: 1 producto=1 registro; `canonical`=nombre comercial limpio, `aliases`=SKU/descriptivo/base; compuestos se PARTEN (evidence-gated, no "3G/3D"); variantes pedibles=registros separados; SKU+nombre=1 registro; **merge-key = model+canonical (aliases NUNCA puentean)** → no fusiona hermanos distintos (DS5≠DS10) ni cross-brand (RP1r-Supra Notifier ≠ VSN-RP1r Morley); higiene de aliases (canonical-de-otro + compuesto-puente "AM2020/AFP1010" + códigos-internos `NNN-NNN` fuera); `software`=primary (el doc ES del software: TG-NOTIFIER/UPDL/PK-*/OPC-RP1r/MK-ZX) vs `software_tool`/`mention` (accesorio: WinHost/SCD250/MK-DXC); `package` (BE-XP/BE-400=bundle umbrella); `compat` canonicalizado contra el set del corpus.
- **(d) Fold-in BASE-UNIÓN (dúo r12, el bug más caro de la sesión)**: el fold-in de los 29 DEBE partir de la **unión canónica** (`build_models`, MISMA función que los 985) y la adjudicación MODIFICA encima — NO construir desde el diff del conflicto (eso descartaba el set **ACORDADO** = **78 productos perdidos** en centrales multi-producto). `primary`=sujeto del doc / `secondary`=módulos (el rol heredado del crudo se DEGRADA cuando hay primary adjudicado: MNDT060 15→1). Docs-limpieza (FAD/FS) usan `replace` (override, ignora ruido crudo).
- **(e) 3 rondas de dúo, cada una cazó bugs REALES** (regla-C verificó cada claim): **r10** (Fix1: bridging de aliases genéricos, ~152 primaries degradados a alias); **r11** (7 fidelidad: CAD-250 omitida, BE-XP/NR45-24/PRL-P2P perdidos, Pearl-tentativo-encodado-firme=mi sesgo, software-role); **r12** (78-producto fold-in + rol-heredado). El cross-model refutó por regla-C 1-2 FP (124-143=part-number válido del repetidor; CAD-BLED/B extraídos-por-ambos). **Adjudicación de Alberto al píxel** cazó identidad que ningún modelo podía: FAD=**2 productos** (902 2A / 905 5A), BE-XP=paquete (no modelo), códigos 124-xxx=misleading, **CFP-800≡Serie800** (gap de RESOLUCIÓN de identidad, MNDT020 SÍ ingestado — no gap de corpus).
- **(f) Decisión re-pass: ARCHIVADO como innecesario.** La "falta de módulos" NO era gap de extracción (AMBOS modelos los extrajeron: CPU-400/UZC-256/NIB-96 en crudo) sino MI fold-in; fix determinista $0. **NO eval-gated** (no hay golds que lo toquen; no se mide si un defecto conocido es defecto — corrección de Alberto a mi over-instrumentación, #45/#50). Eval-driven es para levers-de-eval, NO para corregir un activo foundational sin golds.
- **Alternativas descartadas**: fold-in desde conflict-diff (perdía 78 productos); software-siempre-primary (co-primarizaba accesorios); re-pass eval-gated (defecto conocido, sin golds); aplicar a DB antes de medir el consumo (riesgo NO-OP, DEC-066).
- **Gaps/riesgos declarados**: (1) **el VALOR no se realiza hasta el CONSUMO (F, medido aparte)** — donde el pre-filtro fue NO-OP (DEC-066); **E (DB-apply, stop-line de Alberto) gateado por F**. (2) los **985** (agree/superset) NO están human-validados — solo coincidieron 2 modelos → **QA de muestra PENDIENTE** (los errores COMPARTIDOS OCR/es-en/OEM no los caza el acuerdo). (3) **s84 estructural**: relaciones por-ENTIDAD (`software_of`/`programs`/`compatible_with` por producto, no por doc) + **índice inverso producto→docs** (vista derivada de Capa 2 = la estructura de retrieval; cierra la higiene cross-doc, resuelve CFP-800≡Serie800). (4) gaps de corpus REALES (NP7-12 batería, ModuLaser).
- **Control**: NADA en prod/DB/mergeado; branch-local; tests `src/` sin tocar; held-out intacto. **Relacionado**: DEC-066 (`LEVER2_IDENTITY` = el lever que esto construye limpio), DEC-056 (ranking agotado; esto es recall vía identidad), `feedback_my_bias` (#50), `adversarial_review_log` (dúo r10/r11/r12) + `evals/s83_{conflicts_groundtruth,conflicts_resolved,document_models_final,document_identity_final}` + `scripts/s83_{build_document_models,finalize_tables}.py` + memoria `s83_identity_asset` + rama `eval/s83-retrieval-model-aware`.

## DEC-068 — s83·F2 (cierre planificación): L-i / filtro-categoría-vectorial = SETTLED-archivado (re-litigar); el bloqueante es el RANKING; orden de F = identidad-primero vs MAIN congelado; categoría → catálogo/boost, nunca filtro duro

- **Fecha**: 29 jun 2026 (s83·F2). **Impacto**: MEDIO-ALTO (fija el rumbo de F + **previene re-litigar** un lever ya medido ×3; zona de dolor retrieval → **dúo r13+r14, ambos brazos convergentes**). **Disparador**: al planear el consumo de identidad, Claude propuso "vectorial ancho / quitar el filtro de categoría" como BP fresco; el dúo cazó que = re-litigar.
- **(a) L-i (vectorial ancho / quitar el filtro de categoría) = SETTLED, ARCHIVADO.** Medido ×3 con veredicto negativo: DEC-040 (A/B → ROLLBACK, Δ_net real ≈ −2), DEC-050 (MERGE+L-i′ **post-ef=120** → gate-0 NO-GO, 9/10 PASS-control), DEC-042 (L-i+CE → NO-GO). **El bloqueante NO es el filtro — es la MEZCLA/RANKING del pool** (stamps planos vs cosenos; DEC-041a). El filtro de categoría además **YA está inerte** (columna muerta desde el SWAP s44, 0 filas canónicas, broad-fallback opera; DEC-040a/DEC-056f) → quitarlo formalmente es ~NO-OP-con-churn. **No se re-abre** salvo CON un ranking robusto que no perturbe la frontera (entonces el filtro sale solo).
- **(b) Categoría = SETTLED:** si vuelve, es **BOOST data-driven en el ruler, NUNCA filtro duro** (canon DEC-040a; el EQ es conceptualmente erróneo — `chunk-category ≠ answer-category`, hp008). El dato de categoría del activo (DEC-067, free-text 99%) tiene **dos consumidores reales** — (1) las **rutas de catálogo** (`_handle_catalog`/`available_models`, rotas hoy por la columna muerta) y (2) un boost futuro (path no-model) — **previa CANONICALIZACIÓN** a una taxonomía (no volcar free-text). TECH_DEBT #44.
- **(c) Orden de F (dúo-validado):** **(1) medir el CONSUMO de identidad** (índice inverso producto→docs + resolución) contra el **MAIN actual CONGELADO**, diseño **factorial + freeze completo** (corpus/índice/embeddings/juez/seeds/config/proconfig); E (DB-apply) gateado por que mida ganancia → **(2 paralelo)** canonicalizar categoría → arreglar catálogo → **(3 después, si identidad gana y se quiere el canal)** ranking/merge (DEC-041, el bloqueante real). + QA de los 985.
- **Alternativas descartadas** (refutadas por el dúo r14, ancladas en DEC): "re-medir L-i primero para base limpia" — el sustrato ya se re-midió post-ef=120 (NO-GO); net-zero ≈ −2 importa el churn de frontera → **confunde L-i con identidad** (= medir-2-flags, #49); el filtro ya inerte → no-op-con-churn; paga un A/B (~$25-50) cuyo ±2 de ruido se traga el techo +1-frágil (DEC-051d/#44). "Poblar categoría para que el filtro EQ funcione" (A1, DEC-040, EQ roto). "Base limpia = L-i" → la base limpia correcta es **main congelado**, no L-i.
- **Control**: NADA ejecutado (toda la fase = planificación + dúo). **Relacionado**: DEC-040/041/042/050 (L-i/ranking medidos), DEC-056 (retrieval agotado, reafirmado 7×), DEC-066/067 (identidad = el lever vivo), `feedback_my_bias` (#51 — oscilar al último-que-empuja + re-litigar sin leer el canon), `adversarial_review_log` (dúo r13+r14, 0 FP, ambos brazos convergentes) + `evals/s84_{category_bp,plan}_review_brief.md`.

## DEC-069 — s84: F1 (consumo de identidad / índice inverso producto→docs) = NO-OP-con-regresión MEDIDO → revertido; identidad ⊥ el cuello del eval RE-CONFIRMADO full-stack

- **Fecha**: 29-30 jun 2026 (s84). **Impacto**: ALTO (cierra el bloque F del activo de identidad como lever de eval; zona de dolor retrieval/identidad → **dúo #12: sub-agente Opus + cross-model GPT-5.5**). **Disparador**: DEC-067/068 — el plan era diseñar+MEDIR el consumo del activo limpio (índice inverso) en retrieval.
- **(a) Construido (branch-local, flag `IDENTITY_INDEX` default OFF):** índice inverso `model(normkey)→{source_files by role}` desde `document_models_final` (5274 claves, self-consistency 100%; `scripts/s84_build_identity_index.py`); consumo ADITIVO en el seam de `_diversify_by_source_file` (unir source_files limpios, primary-first). JOIN verificado: 1014/1014 docs del activo ∈ chunks_v2.
- **(b) VEREDICTO: NO-OP-con-regresión MEDIDO → REVERTIDO.** Verify-first LÉXICO: divergencia 17/39 dev golds (S_clean\S_db). Pero el **path REAL** (retrieve_chunks) solo cambia el top_k de **3/39** (el canal vectorial ya alcanza la mayoría de docs divergentes — el bite #2 del dúo: la divergencia léxica sobre-cuenta). Funnel OFF vs identidad-ON (LEVER2_IDENTITY+IDENTITY_INDEX): **bucket RETRIEVAL PLANO 28→29**, solo hp018 PRIMARIO recuperado (GRIS reach≠PASS, ya DEC-066), y **hp012 REGRESÓN** (la unión aditiva desplaza 2 chunks-con-hecho fuera del pool-50). = identidad NO mueve el retrieval-miss.
- **(c) Identidad ⊥ el cuello del eval, RE-CONFIRMADO full-stack** (s75/DEC-057 lo dijo: ~4/16 identidad-bloqueada). El activo de identidad (DEC-067) es durable y vale para **findability/catálogo/escala-30+/corrección**, NO para recall del eval.
- **(d) Dúo #12** (sub-agente Opus + cross-model GPT-5.5): cazó el confound (la divergencia léxica sobre-cuenta; el factorial debe ser 2×2 LEVER2_IDENTITY×IDENTITY_INDEX; mismatch de normalización normkey-vs-normalize_model `/`; el over-claim "recall puro/divergencia REAL 17/39" = mi sesgo #42-#51, cortado otra vez). El sub-agente Opus fue decisivo en cazar la estructura del NO-OP.
- **Alternativas descartadas**: pagar el factorial 2×2 con juez (verify-first lo predijo NO-OP, #44 economía-de-eval); E (DB re-tag) antes de medir el consumo (riesgo NO-OP, la trampa DEC-066).
- **Gaps/riesgos**: el verify-first léxico SOBRE-cuenta (no ve el canal vectorial) → la divergencia no es la métrica. **Control**: NADA en prod/mergeado; `retriever.py` revertido (índice + seam fuera; el artefacto `s84_identity_index.json` + build script CONSERVADOS para E/catálogo). **Relacionado**: DEC-066/067 (el activo), DEC-057/056 (identidad⊥cuello), `feedback_my_bias` #49, `adversarial_review_log` dúo#12, `scripts/s84_build_identity_index.py`.

## DEC-070 — s84: re-diagnóstico del retrieval-miss vía JUEZ SEMÁNTICO (reframe de Alberto) → el funnel léxico inflaba retrieval ~45%; corpus-gap=0; el cuello REAL del eval es SÍNTESIS (63%)

- **Fecha**: 29-30 jun 2026 (s84). **Impacto**: ALTO (re-mapea el cuello del eval; corrige el instrumento de diagnóstico). **Disparador**: Alberto reframe — "¿comparamos el retrieval-miss de antes vs ahora?" + "el corpus-gap no me lo creo, las preguntas se hicieron con Opus/GPT sobre el corpus".
- **(a) Corpus-gap = 0 (tu hipótesis, 2ª vez tras s82):** los 11 CORPUS-GAP verificados con `corpus_grep` — los 11 valores existen en el corpus (40-122 chunks c/u), varios en el manual objetivo (hp013/ASD535, hp002, cat018/AM-8200, hp015/CCD-103). Son FN del matcher LÉXICO (es-en/OCR/forma `NC/C/NA`). Reclasificados a RETRIEVAL/within-doc/artefacto; 0 quedan.
- **(b) El funnel LÉXICO inflaba RETRIEVAL ~45%:** juez semántico (Opus, sobre el pool real) de los 49 facts retrieval-miss → **22 ARTEFACTO** (el valor SÍ está recuperado, el matcher es-en no lo vio; 16 en top5→eran SINTESIS, 6 en pool→RERANK) + **27 miss real**. es-en total = 8/49 (5 artefacto-EN + 3 miss-real). El eval de PRODUCCIÓN (juez GPT-5.5 sobre la respuesta) NO se ve afectado — solo el funnel de DIAGNÓSTICO mentía.
- **(c) Funnel CORREGIDO (los 22 artefactos a su bucket real):** **SINTESIS 71 (63%) · RERANK-MISS 14 (12%) · RETRIEVAL 27 (24%) · CORPUS-GAP 0.** → **el cuello dominante REAL es SÍNTESIS** (el bot recupera el dato en top5 pero la respuesta no lo usa), no retrieval ni identidad.
- **(d) Sizing de los 27 retrieval-miss reales:** 26/27 = **within-doc** (manual recuperado, 16/17 en top5, pero el chunk-valor específico no surfaceado); 1 doc-level (cat011, query ambigua = clarify correcto); es-en=0 en los 16 within-doc (todos ES). Causa estructural (workflow 16-agentes + dúo): canal vectorial muerto (→DEC-071) + keyword-FTS within-doc roto (`extract_search_keywords` corta top-3 por orden ANTES de quitar identidad → verbos de framing `está`/`tengo` consumen los slots; STOP_WORDS sin tildes; FTS-AND estricto).
- **Alternativas descartadas**: optimizar contra el funnel léxico (mentía ~45% en retrieval); within-doc semántico como fix de raíz (sobre-dimensionado para la Familia-1 keyword-bug — workflow lo cazó).
- **Gaps/riesgos**: juez semántico single-pass (margen en borderline; K-mayoría para blindar). **Control**: diagnóstico, NADA en prod. **Relacionado**: DEC-057/056, s82 (corpus-gap 9→0 ya entonces), `corpus_grep.py`, `audit_retrieval_funnel.py`, `scripts/s84_factprobe.py`, workflow `s84-retrieval-deepdive`, `feedback_my_bias` (#42-#51 over-claim).

## DEC-071 — s84: el BUG del filtro de categoría MUERTA = el lever de retrieval (net −12 retrieval-miss); (c) within-doc subsumido/revertido; cambio de modelo operativo (main=dev=demo, eval-PASS diferido a síntesis)

- **Fecha**: 30 jun 2026 (s84). **Impacto**: ALTO (lever de retrieval de prod + cambio del modelo operativo de la fase; zona de dolor retrieval → **dúo #13/#14/#15**). **Disparador**: Alberto — "si la causa es competencia global, ¿cómo es que la identidad no ayuda?" + "elimina el bug de categoría, deja de escabullirte" + "mide en retrieval, no PASS".
- **(a) El bug (DEC-040 re-verificado):** `chunks_v2.category` muerta desde el SWAP s44 (0 filas canónicas). Bajo `MERGE_STRATEGY=stamps` (prod), el canal vectorial principal filtra por `detected_category` → **0 filas el 85% de queries** (medido: hp002 pool = VECTOR 0; 9/10 within-doc misses detectan categoría). El cuello within-doc era el canal semántico MUERTO, no competencia intra-doc.
- **(b) El fix = el lever (`VECTOR_NOCAT`, 4 sitios):** bypasea la categoría muerta en {canal vectorial principal + broad-fallback + content_search 3c-i + `_diversify_by_manufacturer` 5b}, MANTENIENDO stamps (aislado del cosine-merge de L-i′/DEC-050). **Medido en RETRIEVAL (no PASS): retrieval-miss 27→15 (net −12, 8 golds mejoran, cat022 regresa por redistribución de pool tipo-L-i).** Supera a (c) within-doc vector (+6 vs +3, (c) es subconjunto) → **(c) REVERTIDO**.
- **(c) Es L-i en MECANISMO pero medido en métrica DISTINTA:** DEC-040/068 settled L-i en **PASS** (ROLLBACK por flips de juez 3-2 DOWNSTREAM, chunk seguía en pool = NO regresión de retrieval). s84 lo mide en **RETRIEVAL-miss** (el objetivo upstream actual). NO re-litiga el veredicto PASS (que sigue) — es un **bug-fix medido en retrieval**, decisión de Alberto sobre su métrica. (El intento de re-medir L-i en retrieval-miss como "métrica nueva" SÍ fue #51 [dúo#14, DEC-068 lo refutó]; lo que sobrevive es el bug-fix por principio + su efecto de retrieval, no la re-litigación.)
- **(d) Dúo de implementación (#15):** sub-agente cazó el 4º sitio (5b, `_diversify_by_manufacturer`, DEC-040 "A6") que el cross-model NO vio = complementariedad. Resto = falsos-positivos sanos (handler re-detecta categoría aparte → 0 consumidores rotos; gating limpio; mantener la detección correcto). Over-claim "fix completo" cazado → degradado a "4 sitios". `tests/test_vector_nocat.py` (+2, 355 verdes).
- **(e) CAMBIO DE MODELO OPERATIVO:** sin técnicos (Railway = solo demo), **se deja de tratar prod como sagrado**: `main` = branch único (dev=demo), auto-deploy, **stop-line = tests-verdes (no PASS-gate)**, **freeze solo per-eval**. **El eval de PASS se DIFIERE hasta atacar SÍNTESIS** (gut de Alberto + dato DEC-070: SINTESIS 63% = el blocker de PASS; pagar PASS antes mide ruido). Lo que se trabaje entre medias (retrieval/rerank) se mide en retrieval-miss, no PASS.
- **Alternativas descartadas**: flag-gatear el fix permanente (perpetúa la columna muerta viva bajo OFF → tropiezo recurrente; con cero usuarios el cuidado no compra nada); re-base del eval ahora (prematuro: síntesis bloquea PASS); pausar el auto-deploy (innecesario para una demo); (c) within-doc (subsumido por L-i).
- **Gaps/riesgos**: net +retrieval PERO con redistribución de pool (cat022 regresa — el efecto DEC-040); PASS no medido (apuesta upstream→downstream: el delta de PASS llega con síntesis); el fix está flag-gated en branch (la limpieza de raíz = s85). **Control**: branch-local `eval/s83-retrieval-model-aware`, flag default-OFF (prod inerte), 355 tests verdes; NADA mergeado. **Relacionado**: DEC-040 (el bug + L-i medido en PASS), DEC-050/056/068 (ranking/L-i settled-PASS), DEC-070 (el diagnóstico), `feedback_my_bias` (#52 escabullirse del bug apoyándose en un "settled"-de-otra-métrica; #53 over-claim "0 push-out" desde una corrida, corregido al re-verificar cat022), `feedback_autonomy` (modelo operativo nuevo), `adversarial_review_log` dúo#13/#14/#15, `evals/s84_{withindoc_vector,recall_remeasure,nocat_impl}_review_brief.md`, `tests/test_vector_nocat.py`.

## DEC-072 — s84·M (mantenimiento): control ESTRUCTURAL anti-recall (LEVER_DIGEST + hook SessionStart + Protocolo afilado) tras consolidación de memoria — verificado BP contra los docs de Claude Code (PR #92)

- **Fecha**: 30 jun 2026 (s84·M, mantenimiento post-s84; NO consume s85). **Impacto**: MEDIO (gobernanza: toca CLAUDE.md/briefing + establece procedimiento recurrente; zona de dolor = proceso/anti-bias). **Disparador**: tras consolidar el topic file de memoria (273KB→5KB), Alberto preguntó si añadir memoria para no reincidir en las trampas de s83/s84 (el dúo matando una sugerencia por la métrica EQUIVOCADA; escabullirme del filtro de `category`; NEGAR de primeras que el filtro existía; OLVIDAR que contextual-retrieval ya se había probado).
- **Diagnóstico (verificado)**: el canon estaba COMPLETO cada vez (category=DEC-040/TECH_DEBT#44; contextual-retrieval=DEC-020/022; L-i=DEC-040/050/068) → el fallo es de **CONSULTA**, no de canon ausente. Por tanto añadir prosa a un `feedback_my_bias` de 97KB que ya no se consultaba = empeora, no arregla.
- **Decisión (versión MÍNIMA)**: (1) `docs/LEVER_DIGEST.md` = digest lever-indexado de los ~8 levers SETTLED con columna **MÉTRICA obligatoria** (settled-en-PASS ≠ settled-en-retrieval-miss); (2) hook `SessionStart` (`.claude/hooks/inject_lever_digest.sh`, gitignored) que lo **inyecta cada sesión** (recall automático, no "acordarme de abrir"); (3) fila EXISTENTE de Protocolo 4 afilada ("nunca de memoria; el settled tiene MÉTRICA, verifica que coincide con el objetivo de HOY"); (4) Protocolo 2 ítem 5 + check en `adversarial_briefing.md` (el AUTOR declara OBJETIVO+MÉTRICA, el revisor audita el mismatch).
- **Alternativas descartadas (el panel adversarial mató mi borrador v1)**: (a) doc aparte `LEVER_LEDGER.md` → un doc que "debo abrir" hereda la dependencia que falló (#52: salté un DEC que firmé ese día) → embebido/inyectado; (b) tabla de estado inline en CLAUDE.md → **NO-BP** (CLAUDE.md=instrucciones durables, no estado mutable; <200 líneas; verificado contra docs de Claude Code: "if it must run at a specific point, use a HOOK; CLAUDE.md is not a hard enforcement layer") → hook que inyecta digest derivado; (c) columna de hechos/bugs → duplica TECH_DEBT #44/#45; (d) fila NUEVA en Protocolo 4 → ya existía una casi idéntica (DEC-022) → afilar > duplicar; (e) lección #54 en feedback_my_bias → más prosa en el archivo no-consultado = el fallo → puntero en su lugar. **Reframe clave (la lente que leyó el brief real `s84_category_bp_review_brief.md`):** "el dúo mató por la métrica equivocada" era **framing del AUTOR** (el brief enmarcaba PASS/BP y citaba DEC-066, un NO-OP-en-PASS, como precedente; "retrieval-miss" no aparecía), no juicio defectuoso del revisor → el fix es author-side.
- **Revisión adversarial**: workflow panel 4-lentes (3/4 válidos, convergentes, 0 FP material) + agente `claude-code-guide` (docs BP) + WebFetch del schema de hooks (verificado: `hookSpecificOutput.additionalContext` / stdout, matcher `startup|resume`, `${CLAUDE_PROJECT_DIR}`). **Cross-model GPT-5.5 NO corrido** (sin key en el entorno de autoría) → el corte fue panel Opus + docs + Alberto.
- **Gaps/riesgos declarados**: no arregla la **evasión motivada** (el ejemplo 2 necesitó pushback 2× de Alberto; backstop = Alberto + dúo); **cero delta de eval** (hardening de recall, NO toca el cuello SÍNTESIS); el hook vive en `.claude/` **gitignored** = setup local por checkout (instalado en `main` local; los archivos tracked mergean por git); digest hand-maintained (paso de cierre anti-drift añadido) hasta una posible generación desde tags greppables.
- **Estado**: ✅ tracked mergeado (PR #92: `docs/LEVER_DIGEST.md` + CLAUDE.md + `adversarial_briefing.md`) + hook instalado en `main` local (activa en la 1ª sesión nueva post-merge; fail-open hasta entonces) + memoria consolidada/reconciliada (#52/#53). **Relacionado**: DEC-040/068 (L-i = la métrica del settled), DEC-022 (la fila base de Protocolo 4), `feedback_my_bias` #51/#52/#53, CLAUDE.md Protocolos 2/4 + Cierre, `docs/LEVER_DIGEST.md`, PR #92.

## DEC-073 — s85: limpieza de raíz del filtro de categoría MUERTA (A, mergeada #94) + INSTRUMENTO family-aware de retrieval-miss (B0=14) + diagnóstico por (etapa×motivo) del pipeline real (B1: 3 clusters)

- **Fecha**: 1 jul 2026 (s85). **Impacto**: ALTO (limpieza de prod mergeada + instrumento-árbitro nuevo del que cuelga B; zona de dolor retrieval → **dúos #16-#20**). **Disparador**: Alberto (roadmap s85 limpieza→síntesis) + correcciones ground-truth de identidad Morley (hp018 MI-310≠MI-530).
- **(a) A — limpieza de raíz MERGEADA (PR #94):** el fix `VECTOR_NOCAT` de s84 pasa a PERMANENTE (sin flag): quita el filtro por la columna `category` MUERTA de los 4 sitios + broad-fallback (workaround del canal muerto) + 3c-i + detección inerte + param de `content_search`. Conserva MERGE_STRATEGY/LEVER2_IDENTITY/PM_RESCUE + la detección para catálogo (handler). **Verificado judge-free** (modelo operativo s84, PASS diferido a síntesis): 354 tests + **equivalencia de pools NEW(sin flag) vs OLD(flag-ON) en los 39 dev = 38/39 idénticos + cat005 idéntico en isolación** (net −63 líneas). Dúo #16 (sub-agente cazó bloque `detected_category` muerto + comentario falso; cross-model cortó over-claim de framing).
- **(b) B0 — instrumento REPRODUCIBLE de retrieval-miss con juez semántico** (`scripts/retrieval_miss_judge.py` + `retrieval_miss_famtie.py`): sustituye el predicado LÉXICO del funnel (DEC-070: inflaba ~45%) por un juez hecho-vs-chunk **GPT-5.5 K=5** (rúbrica estricta versionada, umbral ≥4/5). Pin del pool → re-derivación EXACTA. **Diseño dúo-revisado ANTES de build** (elección de Alberto): el dúo #17 cazó **6 fallos de diseño** (2 CRÍTICO, incl. pre-filtro top-8-coseno = FN estructural en within-doc) → diseño reescrito. Build: pasada definitiva 39/39 limpia (n_fail=0, paced workers=2-3, resumible sobrevivió ~5 teardowns). Dúo #18 (famtie) cazó **2 CRÍTICOS** (manual_pin pm=None por SELECT; fail-open) → arreglados **sin re-juzgar** (patch pm-by-id, disciplina de coste post-incidente $50).
- **(c) El tie FAMILY-AWARE (corrección de Alberto):** el tie por filename-token acreditaba mal — by-target daba hp018=found vía MIE-MI-310 (familia ZXAE/ZXEE) para una pregunta de ZXe/MIE-MI-530 (=ZX2e/ZX5e) = producto DISTINTO que coincide por azar. El tie correcto = MISMA FAMILIA de `product_model` (verificado en corpus). Con el tie corregido + los fixes del dúo: **retrieval-miss canónico = 14** (de 132 hechos CORE; SÍNTESIS 103 = el cuello sigue siendo síntesis, DEC-070/071 confirmado). CORPUS-GAP=1 (hp011 'r.1', FN residual del pre-filtro léxico con token de 3 chars → prior corpus-gap≈0 se sostiene, `feedback_corpus_gap`).
- **(d) B1 — diagnóstico por ETAPA-DE-FALLO (MECE del pipeline REAL) × MOTIVO** (`scripts/retrieval_miss_diagnose.py`): el dúo #19 DEMOLIÓ la v1 (inferia el fallo desde universos paralelos vector_search(200)/keyword, no el pipeline) → reescrito instrumentando `retrieve_chunks` con un **trace inerte** (param `_trace`, 354 tests verdes) que emite membresía por-etapa (channels/merge/superseded/model-filter/diversify/lang/final). Dúo #20 (3ª ronda) refinó: es-en vía la columna `language` de la DB (no heurística), lever discrimina within-doc, guards. **Mapa canónico para B2: RECALL-INTRADOC 8 (within-doc/chunking, NO HyDE-global) · MODEL-FILTER 4 (hp018=identidad, el model-filter expulsa el manual correcto) · RECALL-GLOBAL 2 (findability).**
- **Alternativas descartadas**: flag-gatear el fix de categoría (perpetúa la columna muerta viva); pre-filtro coseno/léxico solo en el juez (FN es-en/within-doc → juzgar pool completo); by-primary puro (demasiado estricto, falla source-naming hp001) o by-target puro (demasiado laxo, acredita familia equivocada hp018) → family-aware; instrumento frugal con pre-filtro para B3 (cambia el veredicto del juez → rompe consistencia; y B3 re-mide dirigido = barato de por sí, Alberto).
- **Gaps/riesgos declarados**: CORPUS-GAP=1 residual (hp011 'r.1' token-corto = FN del pre-filtro del manual); la resolución source-naming de la familia es un parche B0 (linkage gold-provenance↔corpus-filename = clase DEC-065, workstream aparte); el juez GPT-5.5 no cazable por el dúo mismo-modelo (golds-trampa pendientes de correr); **el número 14 depende del juez semántico (variance no caracterizada aún)**. reach≠PASS, PASS diferido a síntesis.
- **Estado**: A ✅ MERGEADA (#94, en demo). B0/B1 branch-local `eval/s85-retrieval-miss` (13 commits, NADA más a main). **Qué sigue: B2 — método estructural por los 3 clusters** (RECALL-INTRADOC + RECALL-GLOBAL autónomo; MODEL-FILTER=identidad es settled-lever → check-de-métrica del digest [identidad ⊥ recall DEC-057/066/069 medido en funnel léxico → el instrumento corregido lo RE-ABRE = re-medición no re-litigación] + dúo+contrato con Alberto). **Coste s85 ~$12-14** (tras el incidente $50 de s84→s85, `feedback_cost_discipline`). **Relacionado**: DEC-040/069/070/071 (category/L-i/family/el cuello=síntesis), DEC-065 (source-naming), DEC-057/066/069 (identidad settled), `feedback_corpus_gap`/`feedback_cost_discipline`, `adversarial_review_log` dúos #16-#20, PR #94.

## DEC-074 — s86: B2 por los 3 clusters de retrieval-miss → identidad ⊥ el eval (~4, no el cuello); el data-driven map necesita catálogo canónico de 2 etapas (BP, dúo+literatura), NO LEVER2 (quick-fix); plan (A)||síntesis

- **Fecha**: 1 jul 2026 (s86). **Impacto**: ALTO (rumbo del workstream de identidad + decisión de paralelizar; zona de dolor retrieval/identidad → múltiples dúos + cross-model + 4 workflows). **Disparador**: Alberto (s86 dedicada a B2; pushback repetido anti-quick-fix/anti-convergencia).
- **(a) RECALL-INTRADOC (8) descompuesto a nivel-chunk:** **5 = hard-tail de INGESTA** (el chunk-valor existe pero su coseno 0.43-0.51 está por debajo del suelo del canal vector ~0.50 → "aguja en chunk grande"; NO es ANN-miss ni chunking-roto — descartados midiendo). Levers query-time DESCARTADOS medidos: **neighbor-window retrieval-stage = NO-GO** (zero-sum pool-50: +4/−29 broad, +4/−26 restringido, A/B jitter-controlado); **synthesis-stage sentence-window = BP pero MENOR** (4/8, backlog síntesis); **ef_search = marginal** (los hace candidatos pero compiten con cientos al mismo coseno); **más-contexto (blurb/voyage-context-4) = insuficiente** (ablación $0: el blurb ayuda ±0.03-0.05 pero no despega del suelo). Fix BP = **capa-ingesta** (multi-granularidad/parent-doc + extracción-tablas + BM25 + ColBERT) → workstream foundational futuro (`memory/s86_finegrained_retrieval.md`, TECH_DEBT). **3 "coupled a identidad" resultaron within-doc** (el mapa limpia el flood pero es necesario-NO-suficiente; el value-chunk sigue siendo miss within-doc — workflow map-coverage).
- **(b) MODEL-FILTER (4, hp018) = identidad, ~4 de palanca REAL del eval (no más):** `LEVER2_IDENTITY` (curado) resuelve **4/4** (el alias ZXe→[ZX2e,ZX5e] + series/shared_docs voltean el pool de MIE-310 wrong-family a MIE-530 correcto) pero **regresa hp009/aisladores −1** (family-genérico, tensión clarify-vs-answer) = net **+3**. **hp011 NO es identidad** — mis-diagnosticado por mí; el gold Alberto-verificado dice RP1r=RP1r-Supra (mismo equipo, conducta=answer), miss=RECALL-INTRADOC (el dúo cazó la racionalización). Identidad ⊥ el cuello RE-CONFIRMADO (DEC-057/069): el cuello es **SÍNTESIS (103/132)**.
- **(c) El data-driven map necesita catálogo canónico de DOS ETAPAS (la BP real, NO LEVER2 ni el filtro):** el índice s84 (model-keyed) NO tiene los paraguas; el s83 `family_scope` SÍ (resuelve ZXe data-driven, separa AFP400/AFP4000, los 4 RP1r) PERO el matching de texto libre es frágil → **net-negativo tal como se construyó** (−2 hp011 al adivinar RP1r→a-secas y dropear el Supra correcto). **Un filtro no resuelve ambigüedad real: adivina (mal) o contamina.** La BP = **entity-linking de 2 etapas contra catálogo canónico** (dúo + literatura: Query Brand Entity Linking e-commerce arXiv 2502.01555; selective clarification vía EVPI CLAM 2212.07769/SAGE-Agent 2511.08798): (1) **catálogo gobernado** (ownership/versionado), (2) **lado-DOC canónico** = re-taguear chunks_v2 con ID de producto canónico (el `product_model` doc-level colisiona por substring; el cross-model exigió esto), (3) **resolución query-side híbrida** (determinista + LLM-al-margen) + **clarify-on-ambiguity** (el modo YA existe; matiz clarify-vs-diverge SETTLED s79/s80). **Clarify-on-ambiguity = BP** confirmado, pero **sin caso de ambigüedad real en el eval actual** (hp011 era el ejemplo y es answerable).
- **(d) LEVER2_IDENTITY = quick-fix, NO la solución:** curación por-familia (3/11 fabricantes, solo Morley con model_aliases hecho PARA hp018 → circular), no escala (TECH_DEBT #49/#50). El dúo lo confirmó NO-GO como arquitectura. **Su marca de borrado (#50) se REVISA:** su lado-query (aliases) es complemento del catálogo, pero el catálogo canónico lo subsume — se retira cuando (A) esté cableado.
- **Alternativas descartadas**: shipear LEVER2 (quick-fix); consumir el índice model-keyed (sin paraguas); filtro substring/family_scope laxo (colisión ZXe/ZXAE) o estricto (dropea rp1rsupra); LLM-en-todo-el-path (la literatura respalda híbrido determinista+LLM-al-margen); adivinar-el-más-probable (= el fallo medido).
- **Gaps/riesgos declarados**: (A) NO mueve el PASS del eval (~4 retrieval-miss + findability/catálogo/escala-30+); el "diverge" no es decidible query-side sin EVPI/atributos-normalizados; la curación necesita gobernanza (o "otro Excel opaco"); el eval mide hechos → acreditar un clarify ya está resuelto en el harness PASS. **Mis-diagnosis repetidas mías** (intradoc→identidad; hp011→clarify) cazadas por el dúo/medición = `feedback_my_bias` convergencia; el sistema (dúo+medición+Alberto) es el control.
- **(e) PLAN (decisión de Alberto): (A) catálogo canónico || SÍNTESIS, en 2 sesiones.** **(A)** = 4-7 sesiones, casi todo autónomo, **~3.5-6.5h de Alberto** en 3-4 lotes cortos (el ground-truth caro de s83 YA está gastado; lo nuevo = QA-sample pre-filtrado de los 985 + re-adjudicar hp018/hp011/hp009 + aprobar contrato+DB-apply). **Paralelizable con síntesis** (verificado: solape de código ≈0, `generator.py` no importa los módulos de identidad; único conflicto = el DB re-tag, gated y serializado tras síntesis). **SÍNTESIS** = el cuello del eval (103, generación), arranca por el **diagnóstico autónomo** (barato; puede re-caracterizar el 103 como el funnel léxico mintió ~45% en DEC-070); des-diferir PASS + gold-design + merge = gates de Alberto.
- **Estado**: branch-local `eval/s86-b2-retrieval`. Código: `neighbor-window` + `IDENTITY_MAP` (`src/rag/identity_index.py` family_scope) flag-gated **OFF** (inertes, 354 tests verdes). NADA mergeado. Scripts de medición + briefs conservados (`evals/s86_*`). Coste s86 bajo (medición judge-free; cross-model + workflows). **Relacionado**: DEC-057/066/069/073 (identidad), DEC-067 (activo s83/s84), DEC-070/071 (cuello=síntesis, modelo operativo), TECH_DEBT #49/#50/#51, `memory/s86_finegrained_retrieval.md`, `feedback_my_bias`/`feedback_cost_discipline`, `adversarial_review_log` (cross-model clarify).

## DEC-075 — s87: diagnóstico autónomo de SÍNTESIS → el "cuello 103" era una COTA de hechos sintetizables, NO fallos; midiendo la respuesta actual el cuello ROBUSTO ≈ 16 stable-MISS (~13-14 genuinos), heterogéneo, sin lever barato → recomendación: des-diferir PASS

- **Fecha**: 1 jul 2026 (s87). **Impacto**: ALTO (re-caracteriza el cuello del eval que gobierna el diferimiento de PASS y el dimensionado del workstream de síntesis; zona de dolor eval-instrument/juez-LLM/generación → dúo cross-model+sub-agente + 3 workflows). **Disparador**: Alberto eligió arrancar s87 por SÍNTESIS (diagnóstico autónomo); el PLAN anticipaba "puede re-caracterizar el número".
- **(a) El "103 SÍNTESIS" NUNCA fueron 103 fallos:** el bucket SÍNTESIS `by_target` (DEC-070/073) = hecho CORE soportado por un chunk del top-5 = **sintetizable** (cota superior), no fallo. Incluye hechos de golds que YA pasan. **Fase A ($0):** de los 103, **25 en golds PASS** + 78 en NO-PASS. NO re-litiga DEC-070/073 (el retrieval SÍ entrega los hechos al contexto) — los REFINA midiendo el downstream real.
- **(b) Instrumento nuevo `synthesis_miss_judge.py` (dúo-hardened):** juez GPT-5.5 K=5 **a nivel PROPOSICIÓN** (valor EN su relación `texto`, no valor-suelto) sobre la RESPUESTA generada por el pipeline FIEL a prod; `reaches_gen = support_ids(votos≥4 de DEF) ∩ ctx_ids(top5 post-`RELEVANCE_THRESHOLD`=0.4)`; clases NOT-IN-CTX / SYNTH-OK / SYNTH-MISS. **Full (103 hechos, 39 dev):** SYNTH-OK 82 · SYNTH-MISS 20 · NOT-IN-CTX 1. **2 generaciones (varianza Sonnet temp=0, declarada en s67base):** **16 stable-MISS · 9 flip · 78 stable-OK** → cuello ROBUSTO = 16.
- **(c) Certificación (workflow adjudica-ciego + verifica-adversarial, cross-model del juez GPT-5.5; + trampa):** de los 20 SYNTH-MISS → **~3-4 judge-FN** (bot SÍ transmite; cat011 '751'=clarify, cat016 'modo prueba', hp002 'reset'), **9 PARTIAL** (transmite parte/granularidad), **~7 OMITTED** (2=hp007 varianza). Controles **10/11 CONVEYED** (juez no sobre-acredita); **1 over-credit = hp018 '4 circuitos'** (la respuesta habla del producto EQUIVOCADO ZXAE≠ZX5e → IDENTIDAD/MODEL-FILTER, DEC-074, no síntesis; el seed by_target hereda la tie laxa que la famtie ya corrigió a retrieval-miss=14). **Ambas correcciones REDUCEN el cuello** → 16 es cota superior conservadora; genuino bot-atribuible ≈ **13-14**.
- **(d) Mecanismo (heterogéneo, SIN lever barato):** **completeness ~10** (omite secundario/granular) = **lever settled NO-GO en PASS** (DEC-051/s69, Δ_net=0); **contradicts ~4 (FIDELIDAD)** = el bot afirma inconsistente con el gold (hp001 '1111' access-level invertido, hp013 'EEPROM' invertido, cat020 universalidad) → per-caso, no un prompt; **hedge-defensive ~2** (se escuda pese a contexto); judge-FN/varianza/identidad el resto.
- **(e) Atribución (verificada):** las respuestas actuales son materialmente más completas que s67base con el **MISMO** generador (`claude-sonnet-4-6`, temp=0, `available_models=None`) y tabla `chunks_v2` → el efecto es de **VECTOR_NOCAT** (mejor retrieval → contexto más rico), no de un cambio de modelo.
- **Recomendación (Protocolo 2; des-diferir PASS = gate de Alberto):** **(1) des-diferir PASS y medir el baseline actual** (predije "subió mucho" — FALSADO abajo); **(2) "atacar síntesis" como workstream está mis-dimensionado** (no hay cuello de 103; el residual es cola pequeña sin lever barato) → leverage real = (A) catálogo/escala + retrieval foundational (DEC-074) + eval orgánico; **(3) 3-4 fidelity-contradicts merecen vistazo per-caso**.
- **(f) PASS des-diferido MEDIDO (Alberto autorizó en la misma sesión; `bvg_kmajority all BVG_RUN_ID=s87`, K=5 holístico, freeze-contract, held-out embargado):** **PASS-control = 9 · K-INESTABLE 6 · residual 24 — PLANO vs s67base (10 PASS + 4 K-INESTABLE), dentro del ruido ±2.** **Mi predicción "subió mucho" quedó FALSADA por la medición** (`feedback_my_bias`: des-diferir fue lo correcto, el gate me corrigió). VECTOR_NOCAT mejoró el MECANISMO (retrieval-miss 27→14, síntesis ~80%) pero el PASS holístico no se movió (el caveat "80% hechos ≠ 80% PASS" confirmado). **Root-cause SEMÁNTICO de los 30 NO-PASS (`s87_rootcause.py`, no el matcher léxico):** SÍNTESIS 11 (completeness=NO-GO+fidelidad) · **OTRO gold/juez 10 (SIN miss de pipeline** → fidelity-errors reales cat022/hp001/cat009, falso-NO-PASS de juez cat019, conducta hp004, supp-facts) · RERANK 6 (settled) · RETRIEVAL 2 (hard-tail ingesta) · IDENTIDAD 1. **Meta-hallazgo: ~10/30 NO-PASS fallan por razones ⊥ el pipeline → arreglar todo retrieval+síntesis NO los pasaría. Plateau noise-limited CONFIRMADO al nivel de gold (DEC-051e medido); NO hay lever de pipeline que mueva PASS.** Recomendación revisada: (1) NO perseguir síntesis/rerank; (2) highest-leverage PASS = **dual-judge + gold-review del bucket OTRO** (s47/s76, cat019 ya falso-NO-PASS); (3) fidelity-errors per-caso; (4) foundational (A)+capa-ingesta ⊥ PASS a corto; (5) unlock real = eval orgánico (~sept). Artefactos: `s87_gate_report.yaml`, `s87_rootcause.py/.yaml`.
- **Alternativas descartadas**: creer el "103" como fallos (era cota); juzgar valor-suelto (cross-model finding 3: cuenta números en relación equivocada); generar-desde-top5-pineado (falsea `similarity`/filtro 0.4); reusar s67base gens (pre-VECTOR_NOCAT desalineado); 1 sola generación (varianza no acotada → 2 reps); certificar solo con trampa (cross-model finding 4 → + adjudicación hand/agente + control-PASS).
- **Gaps/riesgos declarados**: varianza de generación (16 stable vs 20-21/gen); certificación por MUESTRA (20 MISS + 11 controles, no los 103 individualmente); **"80% hechos transmitidos ≠ 80% PASS"** (PASS es holístico ±2, s69 — la relación fact-completeness↔PASS solo la da el eval PASS diferido); seed by_target (tie laxa, hp018 identity-contamina el OK). **Resultado sesgo-sensible** (mi convergencia querría "cuello pequeño") → el dúo de agentes independiente CORRIGIÓ en ambas direcciones (cazó hp018 over-credit + confirmó OMITTED reales), no solo confirmó mi narrativa = `feedback_my_bias` control operando.
- **Control**: branch-local `eval/s87-synthesis-diagnosis`; **NADA en prod, reach≠PASS**, 354 tests verdes; sin cambio de código de prod (instrumentos de diagnóstico nuevos + docs). PASS diferido (gate Alberto). **Relacionado**: DEC-070/071/073 (el cuello=síntesis medido en retrieval-bucket; ESTE lo refina midiendo la respuesta), DEC-051 (completitud NO-GO en PASS = el lever del cluster dominante), DEC-062 (juez holístico inerte a core/supp), DEC-074 (hp018 identidad), `evals/s87_synthesis_findings.md` + `_instrument_brief.md`, `scripts/synthesis_miss_judge.py`/`_trampa.py`/`_calib_sample.py`/`_stability.py`, workflow `s87-synthesis-adjudicate-lean`, `adversarial_review_log` (cross-model 6/6 + sub-agente Opus), `feedback_my_bias`/`feedback_cost_discipline`.

## DEC-076 — s88: per-caso al píxel de los "fidelity-errors" → CERO invenciones del generador; el bucket se disuelve en within-doc + gold-review; dossier accionable de los 30 NO-PASS (dúo completo)

- **Fecha**: 1-2 jul 2026 (s88, trabajo autónomo nocturno autorizado por Alberto: "atacar de forma clara los NO-PASS"). **Impacto**: MEDIO (refina DEC-075(d)/(f); produce el dossier de decisión-en-lote; zona de dolor eval/gold → dúo completo). **Disparador**: DEC-075f señalaba "fidelity-errors reales del bot (cat022/hp001/cat009)" como accionable barato.
- **(a) Examen al píxel de los 5 casos "contradicts" (gold → top5 congelado s87 → literal del chunk → corpus):** **CERO invenciones/inversiones del generador contra el contexto servido** (el contrato CERO-INVENCIÓN se cumple) + 2 fallos MENORES de calibración (cat022 presenta la diferencia-que-encontró sin declarar que no tiene la específica; hp013 no explota señal débil in-context). El bucket se disuelve: **hp001+cat022 = within-doc retrieval** (el chunk-valor EXISTE — '2222' en MC-380 p18/MI_372 p29, banda-IR en MNDT722 p8 el MISMO doc servido — pero no sube al top-5) · **hp013 = frontera síntesis/retrieval** (frase explícita p16 no servida; token EEPROM sí, ignorado) · **cat009+cat020 = GOLD/JUEZ-review** (cat009: el literal servido dice "condensador **(suministrado)** o resistencia 6K8" — el gold atribuye "suministrada" a la 6K8 apoyado en la edición EN ambigua; cat020: el bot ACERTÓ los 3 números core del chunk servido y el juez penaliza la desagregación OTM/LSR-por-niveles AÑADIDA, correcta según el manual).
- **(b) Hallazgo de instrumento:** el examen corrige un **FN del rootcause s87** (hp001 estaba en "OTRO/n_retr=0"; es retrieval within-doc fronterizo — el '2222' entra al top5 solo a veces, por eso flipeó en estabilidad). El bucket "OTRO(gold/juez) 10" de DEC-075f se refina: parte es within-doc fronterizo no visto por el instrumento.
- **(c) Dossier `evals/s88_nopass_dossier.md`:** los 30 NO-PASS agrupados por clase accionable — **A gold/juez-review (candidatos, la palanca CANDIDATA más barata de PASS; delta NO medido; gate Alberto)** · B within-doc/fine-grained (~8, fix=capa-ingesta foundational DEC-074, settled-check con MÉTRICA declarada: los NO-GO s86 se midieron en RECALL-INTRADOC = la misma métrica) · C síntesis-completeness (settled NO-GO DEC-051) · D rerank (settled DEC-048/050) · E identidad (hp018, workstream A). **Cero builds** (nada no-settled afloró = disciplina del digest). Traza de probes: `evals/s88_corpus_probes.yaml` (fingerprint corpus IDÉNTICO al manifest s87).
- **Dúo COMPLETO (ambos mordieron mi sobre-benevolencia hacia el bot):** cross-model GPT-5.5 (8 findings, 7 confirmados, 1 FP-en-sustancia; cerró el gap corpus-live-vs-frozen con el fingerprint) + sub-agente fresco (SÓLIDA; verificó independientemente TODOS los claims de corpus = ciertos; reclasificó cat020 a gold/juez-puro y hp013 a frontera; "cero bugs"→"cero invenciones + 2 calibración"). Correcciones aplicadas in-place.
- **Alternativas descartadas**: arreglar los "fidelity-errors" con prompt de generación (NO existen como bugs de generación; y el lever de prompt es settled NO-GO DEC-051); levers nuevos de within-doc (settled s86 en la MISMA métrica); editar golds directamente (gate de Alberto, DEC-025).
- **Gaps/riesgos**: N=5 examinados al píxel (el resto del dossier hereda instrumentos); el delta PASS del gold-review NO está medido (candidatos debatibles); la clase A necesita la adjudicación de Alberto (ground-truth). **Control**: NADA en prod; cero cambios de código del bot; 354 tests. **Relacionado**: DEC-075 (refina d/f), DEC-051/048/050/074 (settled citados con métrica), DEC-025 (gate gold), `evals/s88_nopass_dossier.md` + `s88_corpus_probes.yaml`, `adversarial_review_log` (2 entradas s88).

## DEC-077 — s88: DÚO v2 (pedido de Alberto) — sub-agente re-pinneado `opus`→`fable` + el cross-model GPT-5.5 LEE el repo (loop agéntico read-only) = paridad de información; cierra TECH_DEBT #36

- **Fecha**: 2 jul 2026 (s88). **Impacto**: MEDIO (gobernanza del Protocolo 3 — procedimiento recurrente). **Disparador**: Alberto — "cambia el sub-agente adversarial de Opus 4.8 a Fable 5; asegura que el cross-model GPT-5.5 también lee el código, que ambos tengan la misma información".
- **(a) Sub-agente → `model: fable`** (`.claude/agents/adversarial-reviewer.md`; s73→s88 fue `opus`). Autor (Fable 5) y sub-agente (Fable 5) vuelven a compartir árbol → **el cross-model sigue INNEGOCIABLE en ALTO/zona-de-dolor** (nota actualizada en CLAUDE.md P3 + description del agente).
- **(b) Cross-model con TOOLS read-only** (`scripts/adversarial_review.py` v2): loop agéntico OpenAI function-calling con `read_file` (paginado, números de línea para anclas) / `grep_repo` (regex+glob) / `list_dir`. **Sandbox**: paths bajo la raíz; **deny-list** `.env*` (secretos), `.git/`+dirs internos, y el propio log de tally (anti-contaminación). **Cap 30 tool-calls** (disciplina de coste; al agotar → review con lo leído). `--no-tools` = escape legacy; `--diff` se mantiene. Tally registra `tool_calls`+`files_read` (auditable). **Invariante preservado** (TECH_DEBT #36): el cross-model ve el artefacto por lente no-Claude + salida CRUDA, NO anidado en el sub-agente.
- **(c) Verificado (Protocolo 1):** unit $0 (sandbox/deny/read/grep correctos) + **smoke E2E con 2 claims FALSAS plantadas** (RELEVANCE_THRESHOLD=0.5; reranker voyage-en-prod): las cazó AMBAS leyendo el código (14 tool-calls; anclas `generator.py:342-343`, `config.py:56-64`) + 2 medios legítimos (dispatcher target_models→LLM). Paridad demostrada.
- **(d) Docs sincronizados**: CLAUDE.md P3 (s56→s73→s88) · `docs/ADVERSARIAL_REVIEWER.md` (§simetría RESUELTA; la regla s52/DEC-028 de pasar-fuentes-a-mano queda como histórico/punto-de-partida) · `scripts/adversarial_briefing.md` (ambos lados leen el repo; exige usar tools para anclar) · TECH_DEBT #36 CERRADO · memoria (project_techbot §controles + índice).
- **Alternativas descartadas**: volcar el repo/ficheros al prompt (no escala, mantiene la selección); anidar el cross-model dentro del sub-agente (mata la independencia — el invariante #36); dejar el pin `opus` (Alberto decidió el modelo top actual; el racional s73 era "el modelo top verifica mejor").
- **Gaps/riesgos**: coste por review sube (~14-30 tool-calls vs single-shot) — cap + tally lo vigilan; el modelo GPT podría no usar las tools en briefs triviales (el user-prompt lo exige); deny-list mantenida a mano (si aparece un fichero sensible nuevo, añadirlo). **Control**: instrumento de gobernanza, NO toca prod del bot; smoke marcado en el tally como no-review-real. **Relacionado**: TECH_DEBT #36 (cerrado), DEC-028 (superada en parte), CLAUDE.md P3, `docs/ADVERSARIAL_REVIEWER.md`, `feedback_my_bias` (el dúo es el control estructural).

## DEC-078 — s89: gold-review Clase A APLICADO (adjudicación de Alberto) → hp004 PASS 5/5 (+1), cat024 sin FALLOs, cat012 resuelto-solo; cat009/cat020 confirman el plateau → dual-judge refuerza como lever del bucket

- **Fecha**: 2 jul 2026 (s89). **Impacto**: MEDIO (edición de golds = el ruler; gate de Alberto ejercido; zona de dolor gold/juez). **Disparador**: Alberto mergeó #97/#98 y adjudicó el packet s88 (A1✅ A2✅ A4a; A3/A5 con preguntas).
- **(a) Ediciones aplicadas vía `gold_store`** (validación 0 errores; provenance en `notes` de cada gold): **A1 cat009** "suministrado"→condensador (el literal HLSI-MN-025 ES p27; el gold citaba la edición EN de parse ambiguo); **A2 cat020** quitada la exigencia "independiente del tipo de equipo" (escala común vs config por Niveles OTM/LSR); **A4a hp004** nota de equivalencia (answer-AMBAS-versiones+confirmación cumple el clarify — decisión de dominio de Alberto); **A3(b) cat024** discrepancia 7-vs-17 mA como hecho core + precedencia manual-del-dispositivo — **verificada al píxel ANTES de editar** (pregunta de Alberto: ¿variante de familia? NO — el 7 mA es del MISMO modelo MAD-472 en las tablas de lazo de 3 manuales del sistema CAD-250 [MI_372 p55/MC-380 p87-94/MS-416 p70]; en reposo ambas fuentes coinciden 0,35 mA).
- **(b) Re-juicio DIRIGIDO (BVG_RUN_ID=s89, K=5, solo los 4 tocados):** **hp004 PARCIAL(4-1)→PASS 5/5 UNÁNIME** (+1 PASS real); **cat024 FALLO(2)+PARCIAL(3)→PARCIAL 5/5** (el FALLO desaparece; no PASS porque el bot lideró con el 7 mA sin marcar precedencia = comportamiento del bot); **cat009/cat020 SIN movimiento** (el juez completista encuentra el siguiente hecho faltante / sigue penalizando material añadido correcto) → **el plateau noise-limited (DEC-075f) se confirma también post-gold-edit; el lever restante del bucket OTRO es el dual-judge**, no más gold-edits.
- **(c) A5 cat012 RESUELTO-SOLO + corrección honesta:** cat012 ya es **PASS 5/5 unánime** en s87 (PASS-control fijado) — el "maybe-injusto" de s71/s74 se auto-resolvió con las respuestas post-VECTOR_NOCAT. La línea "residual PARCIAL" del packet era dato STALE de s67base (error del autor, corregido en el packet). NO se prepara desglose: nada que adjudicar.
- **(d) Pregunta ES/EN de Alberto (A1) respondida + cableada al catálogo:** BP = NO excluir EN en ingesta (contenido EN-only real; el EN a veces lleva la revisión vigente — cat009 mismo), SÍ gobernar equivalencia en consumo (prefer-ES/dedup en pool). Añadida la relación **`docrel language-variant-of`** al contrato del catálogo (F1 la detecta casi gratis: el activo s83 trae `languages[]`; los ~9 pares/~205 chunks duplicados de DEC-066).
- **Alternativas descartadas**: seguir editando cat009/cat020 persiguiendo el PASS (el juez encuentra la siguiente arista = re-litigar el plateau); cambiar conducta de cat024 a answer-con-conflicto (más invasivo, (b) bastó); preparar desglose de cat012 (ya PASS).
- **Gaps/riesgos**: el neto PASS-map = **10/39** (9+hp004) NO es un re-freeze del baseline (medición dirigida sobre golds editados; el baseline completo se re-mide cuando toque un freeze nuevo); cat009/cat020 quedan PARCIAL con evidencia de juez-bias documentada (insumo dual-judge ~sept). **Control**: golds editados SOLO con marca de Alberto (DEC-025); puerta validada; branch `eval/s89-goldreview`; held-out intacto; artefactos `s89_{frozen_contexts,generations,judgments}.json`. **Relacionado**: DEC-075/076 (dossier/root-cause), DEC-025 (gate gold), DEC-051d/075f (dual-judge), `evals/s88_goldreview_packet.md` (resoluciones in-doc), `docs/IDENTITY_CATALOG_CONTRACT.md` (docrel).

## DEC-079 — s90: F0 APROBADO por Alberto (D1-D7 según recomendaciones) → contrato CANÓNICO; F1a (slice vertical Morley) CONSTRUIDO: catalog_store (la puerta) + slice cargado + smoke — el slice cazó 3 clases de bug (su propósito)

- **Fecha**: 2 jul 2026 (s90). **Impacto**: ALTO (arranca el workstream A; nuevo módulo + datos versionados; zona de dolor identidad → dúo completo). **Disparador**: Alberto — "me parece bien lo que propones, ¿cerramos así y empiezas?" (tras 3 rondas de preguntas suyas integradas al contrato + validación BP-MDM externa con los ajustes s89e: merge/split-redirects, F1a-slice, namespace, catalog-gate).
- **(a) F0 cerrado:** `docs/IDENTITY_CATALOG_CONTRACT.md` pasa a CANÓNICO (D1 repo-first · D2 granularidad-s83 · D3 vendedor+rebrand-of · D4 clarify-si-diverge-como-principio · D5 PR-only+auto-entrada-acotada · D6 F2-antes-F3 · D7 homónimos prefer-donde-hay-gt).
- **(b) `scripts/catalog_store.py` — la puerta** (patrón gold_store): load/validate/resolve/write. Reglas duras cableadas: namespace+unicidad+inmutabilidad (merge/split=redirect acíclico), refs sin huérfanos, provenance/added_by en TODAS las colecciones, candidate-gating (paraguas/homónimos nacen candidate; un homónimo candidate BLOQUEA el exact del token = fail-open), colisión alias↔canonical = error. **`resolve()` con contrato `expand`** para el consumidor: check-homónimo PRIMERO (la clase hp011: prefer→expand; clarify→ids-como-opciones expand=False), exact/alias→expand, paraguas divergent-adjudicado→expand, **divergent=unknown→fail-open SIN expansión**. **Catalog gate en CI** (ci.yml). 27 tests nuevos (378 total verdes).
- **(c) `scripts/s90_f1a_morley.py` — el slice cargado** (`data/catalog/*.jsonl`): gt de Alberto nivel-1 (21 productos ZX*/RP1r×4, paraguas ZXe [divergent=true]/ZXSe [unknown→fail-open hasta adjudicar]/ZX2e-ZX5e, homónimo RP1r prefer:notifier:rp1r-supra [D7+hp011], 15 doc-prefijos del mapa s78) + semilla s83 nivel-2/3 (119 productos, 256 aliases, candidate por found_by) + **doc_map por document_id REAL** (114/114 docs Morley matcheados a `documents`). QA-cola: 4 conflictos honestos (2 etiquetas-no-producto, 2 colisiones alias↔canonical DX2/EXP a adjudicar) + 2 candidates de alto blast-radius (umbrella ZXR, homónimo ZX→clarify) → `evals/s90_f1a_qa_sample.md` (~15 min de Alberto).
- **(d) El slice CUMPLIÓ su propósito (cazar antes del bulk):** (1) el smoke cazó la **colisión alias↔canonical** (ZXr-A semilla pisaba el alias gt por exact) → reserva de aliases-gt en el loader + check COLISIONA en la puerta, que cazó 2 más (DX2/EXP); (2) el cross-model cazó **divergent-unknown expandiendo** (contra la letra del contrato) + **CI sin el gate** + 4 más (6/6, 0 FP); (3) la puerta validó las reglas duras sobre datos REALES (0 errores finales).
- **Dúo (ALTO/zona-dolor):** cross-model v2 con tools (23 tool-calls; 6/6 confirmados aplicados) + sub-agente fresco lanzado sobre el estado final (fidelidad-del-gt + bugs residuales; findings pendientes al escribir esta DEC — se incorporan como follow-up, declarado).
- **Alternativas descartadas**: cargar las 31 marcas de golpe (el slice ya cazó 3 clases de bug — el bulk las habría multiplicado ×31); DB-first (D1); resolver homónimos por frecuencia (adivinar = el fallo medido −2 hp011).
- **Gaps declarados**: docrel vacío en el slice (language-variants = F1 bulk); ZXSe fail-open hasta que Alberto adjudique divergent; 119 productos semilla con QA pendiente (candidate visible); normalización free-text completa (592 family_scope) = F1 bulk. **Control**: branch `eval/f1a-morley-slice`; NADA en prod ni DB (repo-only, D1); 378 tests; PASS no tocado. **Relacionado**: DEC-074/077/078, contrato F0, TECH_DEBT #49/#50, `s90_f1a_qa_sample.md`, `adversarial_review_log` s90.

## DEC-080 — s91: F1 BULK — el catálogo canónico de las 31 marcas cargado (1.6k productos), dúo completo con 10 findings aplicados; QA-riesgo con paquete-de-decisión para Alberto

- **Fecha**: 2 jul 2026 (s91). **Impacto**: ALTO (la carga completa del workstream A; zona de dolor identidad → dúo completo 2 rondas). **Disparador**: merge de #101 (F1a) → F1 bulk según el contrato F0.
- **(a) Construido**: `catalog_gt.py` (gt nivel-1 consolidado: Morley s78+s90, **FAAST re-transcrito FIEL** tras reincidencia de la clase H5 [los -HS], CAD-150 Detnov verificado fiel, Pearl; + BRAND_MAP 96 formas→~31 namespaces con tiers y casefold) + `s91_f1_bulk.py` (resolución contextual de GRUPO_BRANDS con mayoría-clara→candidate+QA; typo-merge same-namespace con id_remap global [30 fusiones = #49 en catálogo]; x-brand→candidate+homónimo-candidate fail-open [37, jamás merge auto]; doc_map namespace-del-doc-primero [68 mal-atribuciones corregidas]; **docrel por doc-number+idioma = 9 pares ES/EN — exactamente los ~9 de DEC-066**).
- **(b) Resultado**: ~1.6k productos (~740 candidate honestos) · 1.8k aliases · 15 umbrellas gt · 39 homónimos (2 gt + 37 candidate) · 861 docs mapeados · 9 docrel. Golds-clave resuelven: Pearl/AM-8200/ID3000 exact; CAD-150→6 variantes; FAAST por alias corto→gt. Ambigüedad real bloqueada (B501AP, CRE-4). **175 docs unresolved + 43 contextuales = candidate (jamás se fabrica marca).**
- **(c) Dúo (2 rondas, ambos lados)**: cross-model 5/5 (colisiones dejaban consumibles→candidate; QA infradeclaraba homónimos; paquete-decisión Alberto-size; casefold; gap docrel) + sub-agente 9 hallazgos (gt FAAST infiel [H5 reincide → re-lectura de la memoria antes de transcribir]; doc_map last-wins global; contextual sin gate; docrel muerto→9; typo-merge código muerto; Pearl cita). TODOS aplicados y verificados en datos.
- **Gates**: QA-riesgo (`evals/s91_f1_qa_riesgo.md`): **paquete de decisión ~25 homónimos cross-brand por blast-radius** (¿rebrand/OEM o distintos?) + backlog declarado (brands sin mapear, colisiones, contextuales). El catálogo es SEGURO sin el QA (todo lo dudoso = fail-open). **Siguiente: F2 resolución query-side tras flag + F2.5 shadow-mode.**
- **Control**: branch `eval/f1-bulk-catalog` (PR #102); NADA en prod/DB; 383 tests. **Relacionado**: DEC-079 (F0/F1a), contrato F0, TECH_DEBT #49 (typo-merge lo resuelve en catálogo), DEC-066 (docrel 9 pares), `adversarial_review_log` s91 ×2.

## DEC-081 — s91: los 25 homónimos cross-brand ADJUDICADOS por Alberto y APLICADOS al catálogo; gap D1 cazado (el catálogo no estaba versionado)

- **Fecha**: 2 jul 2026 (s91). **Impacto**: ALTO (primera adjudicación humana masiva del catálogo; identidad = zona de dolor). **Disparador**: pre-QA de homónimos (3 capas: corpus + web + píxel sobre PDFs reales, 30 portadas + 2 manuales descargados de notifier.es) → marcas de Alberto en sesión.
- **(a) Adjudicación** (`evals/s91_homonyms_preqa.md`): **G1 ✅** (12 ítems OEM System Sensor; matices: B501 vendedor SOLO Notifier; B524HTR ya limpio; REFL resuelto al píxel — © System Sensor 2002 en TODAS las páginas de AMBOS manuales 6200R/LPB-620, el de LPB-620 con Notifier España como garante, tablas de reflectores idénticas). **G2 ✅** (7 ítems OEM tercero: Sensitron/P+F/Spectrex/Firebeam/KAC — kac:* tenía doc propio D716 en corpus). **G3 ✏️** (5 OK + 3 ajustes de Alberto, los 3 VERIFICADOS: VSN-4REL no-Morley-only con oem=Esser [catálogo extinción esser.es p3-p4: VSN-232/485/4REL + ESS-RP1R-SUPRA]; CMX-10RM oem=Xtralis [ficha ADI brand='Xtralis by Honeywell' en el JSON de producto]; 2010-2-PAK-RMSDK oem=Carrier [ficha ADI brand-span='Carrier']). **G4 = B-clarify** (APIC: tarjetas incompatibles Aritech/ModuLaser vs Notifier/Stratos).
- **(b) Aplicado** (`scripts/s91_apply_homonyms.py`, por la puerta): 30 winners (24 tokens A-merge, algunos ×5 REFL), 33 redirects + rebrand-of, 30 homónimos retirados (quedan 9: 2 gt + APIC-clarify + 6 fail-open en cola), APIC→clarify candidate=false (sus productos QUEDAN candidate a propósito: canonical_model idéntico 'APIC' — consumo ciego sería la clase hp011), `systemsensor:6424` CREADO (OEM sin doc propio en corpus), umbrella B500 (tabla de Alberto; B524RTE declarado sin doc), **oem SOLO donde Alberto lo declaró** (Esser/Xtralis/Carrier/SS×2). Validate OK + 383 tests + smoke 30 tokens→canonical. **Ronda sub-agente adversarial (fidelidad packet→apply): 3/3 confirmados 0 FP, los 3 clase H5 en MIS añadidos** (oem=HLSI en UCIP y oem='Vision (HLSI)' en paneles VSN NO adjudicados → revertidos; 'Vision (HLSI)' omitido en vendido_bajo de VSN-CO → añadido) — el guardarraíl funcionó ANTES del commit; tally en `evals/adversarial_review_log.jsonl`.
- **(c) Gap D1 cazado y arreglado**: `.gitignore` `data/*` dejaba `data/catalog/*.jsonl` SIN VERSIONAR (git log vacío) mientras el contrato D1 aprobado dice REPO-FIRST ("rollback = git revert"); el test de integración hacía skip silencioso si faltaba el dir → CI nunca lo delató. Fix: `!data/catalog` + los 7 JSONL al PR #102 (~1MB). Alternativa descartada: dejarlo local (contradice D1 literal; el catálogo se perdería en cualquier clone/CI).
- **(d) Método que funcionó**: el pre-QA de 3 capas dejó a Alberto CERO PDFs por abrir — sus 4 marcas + 3 ajustes de conocimiento de mercado llegaron en ~30 min de chat; cada ajuste suyo se verificó contra fuente ANTES de fijarlo (Esser/ADI). Patrón a repetir para los 12 homónimos restantes y el 2º lote.

## DEC-082 — s91: plan F2 v1 TUMBADO por el dúo y corregido a v2 (mecanismo = los 2 seams medidos, no vía aditiva)

- **Fecha**: 2 jul 2026 (s91). **Impacto**: ALTO (rumbo del consumo del catálogo; zona de dolor retrieval+identidad → dúo completo, INNEGOCIABLE). **Disparador**: Alberto pidió "¿qué opina el adversarial dúo?" sobre el plan F2 mejorado.
- **Veredicto del dúo (15 hallazgos, 15 confirmados regla-C, 0 FP — la ronda más productiva del guardarraíl):** v1 NO-SÓLIDA. El hallazgo central (sub-agente H1, crítico): **"expansión aditiva del pool" re-litigaba DEC-069** (aditivo = NO-OP-con-regresión MEDIDO, revertido; `retriever.py:1443` lo dice en comentario) **sin citarlo — yo mismo incumplí el Protocolo 4** (grep del DEC antes de proponer). El cross-model convergió por la vía del código (el seam ignoraba `_filter_to_query_models`).
- **Decisión (v2, `evals/s91_f2_plan_propuesta.md`):** F2 alimenta los DOS seams EXISTENTES y medidos — (1) lista `models` generalizando LEVER2 de YAML→catálogo (el mecanismo que dio hp018 4/4 en DEC-074b; añadir-sin-retirar como hipótesis anti-hp009, la famtie decide) y (2) whitelist doc_map-aware en `_filter_to_query_models` (patrón IDENTITY_MAP; en v2.2/build = UNIÓN-PROTECTORA, el filtro medido corre intacto). [SUPERSEDIDO por la coda r2 y el build: el fetch por document_id NO es parte del mecanismo — solo fallback pre-registrado]. **Conducta pre-registrada: expand-only, answer/clarify intactos, clarify-por-divergencia DIFERIDO** (los 14 paraguas son divergent=true; cablearlo = regresión hp009, s79/s80). Instrumento = **famtie bajo freeze-contract con catálogo-commit** (contrato:167), bvg solo control ±2. Detector = regex generada estilo `catalog.py` desde el catálogo gobernado, pre-excluyendo SOLO digit-only [la coda r2 corrigió: '≤3-chars' mataba ZXe]; shadow-log a Supabase; shadow N≈69 declarado smoke (query_gaps NO existe — TECH_DEBT #8). Plan de retiro de las 6 vías de identidad declarado (anti-dos-copias §3). Regla de clase S3 con guard role=primary+namespace (la v1 habría promovido Z978/DH500/M710 — justo lo adjudicado como NO-identidad) y muestra 50.
- **Alternativas descartadas**: vía aditiva al pool (DEC-069, medida); clarify-por-divergent-true (regresión hp009); bvg como gate (PASS settled, instrumento equivocado); shadow como gate estadístico (N≈69 mono-autor).
- **Meta-lección (para el tally del guardarraíl)**: el autor (yo) re-propuso un lever MUERTO con otra piel ("expansión" ≠ "unión aditiva" solo en el nombre) — la clase de recaída que el digest de levers debía atajar y no atajó porque el DEC-069 no está en el digest como fila propia. **Acción: añadir fila "consumo aditivo del pool" al LEVER_DIGEST.**

**Coda DEC-082 (r2, misma sesión):** ronda de VALIDACIÓN sobre v2.1 = **13 hallazgos más, 13 confirmados regla-C, 0 FP** → v2.2. Los que pagan la ronda: la famtie lee `pool_pin` y NO re-recupera → S2 debe RE-GENERAR el pin con flag ON o la medición era NO-OP garantizado (sub-agente); "pre-excluir ≤3 chars" mataba ZXe (norm='zxe'=3, el caso central de hp018 — cross-model); el guard S3 v2 no bloqueaba su propio contraejemplo (notifier:z978 role=primary en TIDT089 → guard portante = no-hermano-multi-namespace); fetch-by-docid movido SOLO al fallback (no es seam existente); LEVER2=REPLACE medido vs ADD=hipótesis declarada; flags fail-fast incl. PM_RESCUE. **Queda 1 gate de Alberto: la ENMIENDA del contrato §5.1/F2-row (clarify por-pregunta, F2 expand-only) — el plan y el contrato no pueden divergir en silencio.**

## DEC-083 — s91: packet C2 COMPLETO adjudicado (Alberto, 3 tandas) y aplicado — 42 productos `unresolved:*` re-domiciliados; 2 lecciones de método

- **Fecha**: 2 jul 2026 (s91). **Impacto**: MEDIO (identidad/catálogo). **Qué**: las 19 marcas sin mapear de F1 → adjudicadas TODAS (`evals/s91_c2_brands_packet.md` v4-final; `scripts/s91_apply_c2.py` idempotente): detnov(MAD-481, doc propio en detnov.com) · kac(ENScape CWSS + campanas D391) · ada(NSRE24 — **OEM al píxel: logo 'ADA Componentes Electrónicos S.L.' en portada; notifier.es solo vende**) · coelbo(EFD) · ffe(F5000) · calectro · **firelite(14 productos, la fila más gorda — part-numbers Fire-Lite US en doc alojado por Notifier ES)** · avotec · cranford · desico · detectortesters · morley(795-122, numeración de tarjetas Morley) · notifier(FS8: evidencia interna 997-* con 5 hermanos en corpus) · HLS-formación=ruido · FAAST: "(System Sensor Europe)"→systemsensor, "(Honeywell)"→contextual-GRUPO (criterio Alberto: el string de grupo no decide per-modelo — LT-200=SS, FLEX=Xtralis).
- **Lección 1 (corrección de Alberto, 2 veces en la sesión): hosting ≠ OEM** — el PDF en notifier.es solo prueba quién VENDE; la señal válida es lo que hay EN el doc (logo/©/numeración propia/part-numbers). Aplicada como regla del packet y de los lotes futuros.
- **Lección 2: la tabla de marcas mapea el STRING-del-doc; el OEM per-modelo vive en `oem_manufacturer_marca`** — strings de grupo → contextual, nunca adjudicación global.
- **TODO**: BRAND_MAP en `catalog_gt.py` con los strings adjudicados (re-runs del loader); queda ~630 candidates de otras clases (S3 gated por demanda del shadow, plan v2.2).

**Coda DEC-083 (FAAST, corrección final de Alberto):** "FAAST (Honeywell)"/"FAAST (System Sensor Europe)" NO son marcas — son FAMILIA (el extractor s83 las clasificó mal y el packet lo arrastró 2 iteraciones). Materializado como paraguas gt: `FAAST` (familia, 13 miembros) + `FAAST LT-200` **adjudicado divergent=true** (estaba unknown/fail-open desde s80) con los 3 SKUs MI-FL* de Morley añadidos → ambos tokens EXPANDEN (contrato enmendado, expand-only). Estructura canónica: familia→sub-familia→modelos; comercialización=vendido_bajo; OEM=campo per-modelo (LT-200=SS, FLEX=Xtralis si entra). Lección 3 del packet: **familia ≠ marca — un string con paréntesis de grupo es señal de familia, no de brand.**

## DEC-084 — s92/s93: F2 medido con predicciones pre-registradas → ADD shippeado a demo (flag ON); fetch-acotado NO-OP; el lever identidad-en-retrieval EXHAUSTO con −3
- **Fecha**: 2 jul 2026 (s92-s93). **Impacto**: ALTO (retrieval/flags de demo). **Qué**: S2 con tabla pre-registrada (`evals/s92_f2_predicciones.md`) + pin-regen reutilizando labels GPT ($0): baseline-control mismo-día 15 → **ON+ADD 12** (hp018 4/4 = criterio del CONTRATO cumplido — el criterio LOCAL 5/5 NO se cumplió, ERRATA publicada, bias #51-clase cazado por el cross-model; hp009 INTACTO) · **ON+REPLACE 14 con hp009 regresado ×2** = la regresión histórica de LEVER2 reproducida CON mecanismo (quitar el token ZXE veta ZXAE/ZXEE). → `IDENTITY_RESOLVE=on`+`IDENTITY_RESOLVE_POLICY=add` **encendidos en Railway** (PRs #107-#109; LEVER2_IDENTITY eliminado; verificado vivo: shadow-row ZXe→+ZX1e/ZX2e/ZX5e en la respuesta demo).
- **S3-fetch acotado** (whitelist doc_map, append tras el corte, ≤12): mecanismo FUNCIONA (pools>50) pero **NO-OP medido 12→12** — el selector léxico no encuentra los chunk-ids juzgados entre cientos/doc (criterio pre-escrito ">8 → el cuello es el score léxico" ejecutado). **NO-SHIP**; código tras `IDENTITY_FETCH` default-off.
- **Veredicto del lever**: identidad-en-retrieval **EXHAUSTO** con −3 neto banked (métrica: retrieval-miss famtie). El residual 12 NO es identidad. Alternativas descartadas: replace (regresión), fetch (NO-OP), aditivo-ciego (DEC-069, ni se re-intentó). Ref: tally 4 rondas dúo s91-s93.

## DEC-085 — s93b: BAKE-OFF fine-grained (A-FTS / B-multigranularidad / C-extracción-tablas / HyDE) — el mecanismo que financia la re-ingesta es EXTRACCIÓN→ENUNCIADOS; FTS re-ruteo NO-GO
- **Fecha**: 3 jul 2026 (s93b, 8h autónomas). **Impacto**: ALTO (rumbo del workstream ingesta). **Qué**: plan v2 (PR #110) + enmienda v3.2 tras pushback de Alberto ("no solo FTS") con dúo completo pre-ejecución (cross-model 7 hallazgos, 2 CRÍTICOS confirmados contra código [receta embedding context+content `src/reingest/embed.py:52-59`; evento pool-frontier sobre-afirmado] + sub-agente F1-F7 [pin sin scores → cosenos LOCALES de embeddings almacenados, sin re-retrieval; paso-0 `_trace`]). Testbed = 11 miss-facts del pin ON+ADD (guard anti-circularidad excluyó hp006 'Tierra'). Artefacto de decisión: **`evals/s93_bakeoff_resultados.md`**.
- **Veredictos (métrica por-track en el artefacto):** paso-0: 30/31 soportes NUNCA entran a canal; hp012 '99+99' muere en `post_diversify` → **lever diversify, no ingesta**. **A** gate-0 FTS: **NO-GO 1/11** (<3 pre-registrado) + controles: top-20 FTS solapa 0-15/20 con pools sanos → desplazamiento medido. **B** span-oráculo: **1/10** vs frontera REAL del canal (RPC corpus-wide) — aislar ALEJA (5/8 sub<padre). **C** extracción-tablas→enunciados (micro-slice 4): **2/4 ✅** (hp011 0.591>0.539, hp012-'2 lazos/396' 0.621>0.569) — único mecanismo con hechos que nada más gana; predicción ≥2/4 cumplida. **HyDE** solo: 0-1/10 (sube todo el espacio, la barra sube igual; comprime gaps 0.006-0.016 sin cruzar).
- **Lectura estructural:** el cuello es el **gap de vocabulario query↔celda** (la pregunta describe la tarea; el soporte es una celda de spec), no el tamaño del chunk per se — corrige el framing s86. BM25-sobre-pregunta hereda el techo (coherente con "si falta el literal, BM25 tampoco", DECISIONS s3x).
- **Decisión/recomendación:** re-ingesta fine-grained SE FINANCIA vía extracción-tablas→enunciados (~$150-300, **gate presupuesto Alberto**; piloto natural ~6 docs del testbed + famtie). FTS re-ruteo NO-SHIP (no se construyó). HyDE re-evaluable solo COMBINADO post-ingesta. Nada cablado; flags intactos.
- **Honestidad de instrumento (regla-C sobre mí mismo, 3 cazados en el run):** evento v1 de B usaba la frontera del pool FINAL (8/10 "WIN" falsos → corregido a frontera corpus-wide: 1/10); brazo HyDE 1ª pasada = NO-OP silencioso (`hyde.py:84` fallback sin flag; cosenos ≡ espacio crudo ±drift); 2/31 sup son `duplicate_of` (invisibles al RPC; anotado). Tally: `evals/adversarial_review_log.jsonl` (196).

## DEC-086 — s94: PILOTO extracción→enunciados EJECUTADO — GO del mecanismo con criterio pre-registrado cumplido en las 3 barras (R2: famtie 12→6, 0 nuevas-miss); R1-plantilla descartado por medición; decisión de presupuesto lista para Alberto
- **Fecha**: 3 jul 2026 (s94). **Impacto**: ALTO (rumbo del workstream ingesta + seam nuevo en retriever tras flag). **Qué**: spec v2 dúo-hardened (`evals/s94_pilot_spec.md`; cross-model 7 [6 conf., 1 refutado por código: la famtie acredita PRESENCIA, no score → el SWAP multi-vector es medición válida] + sub-agente H1-H8 [triage obligatorio en NO; QA-fila anti-mispairing; padre-acreditable pre-mapeado]). Ejecución F0-F4 (`evals/s94_pilot_run.md`, predicciones pre-registradas ANTES de cada fase).
- **Resultados (famtie vs control-mismo-día 12, lista idéntica al pin s92 = 0 jitter):** **R2 enunciado-LLM 12→6** (5/10 testbed: PWR-R, '1 A', '35', '2 lazos/396', FdT + colateral '99+99'; GO-tabla 2/4 ✓, GO-prosa 3/6 ✓, 0 nuevas-miss — subconjunto estricto; predicciones clavadas 3/3) · **R1 plantilla 12→10** (0/4 tabla, predicción FALSADA → descartado; el pairing determinista NO compite con el enunciado) · **R3 resumen/tabla 12→8** (4 flips con solo 11 surrogates, incl. ISO-X que R2 no gana; predicción 0-2 falsada AL ALZA → complemento barato). Unión R2∪R3 (no medida, declarado): ~7/10 → famtie ~4-5.
- **Triage (H1, el porqué de cada NO):** hp011 = padre entra por swap y muere en DIVERSIFY → mecanismo VIVO, killer=pipeline (misma clase '99+99') → **lever diversify al backlog**; cat013/cat016 = el mecanismo no alcanza (vocabulario operativo puro, coherente con probe). hp001 '2222' borderline documentado (flip R3 posiblemente jitter — lectura conservadora declarada).
- **Build:** seam `PILOT_PARENT_SWAP` (default off, prod inerte) en `retriever.py` — swap 1:1 surrogate→padre-hidratado PRE-merge, keep-max, fail-closed, mapa sidecar (5 tests, `tests/test_s94_swap.py`); inserciones por-brazo con marca `extraction_sha256='s94-pilot:*'` y **rollback verificado 0-restantes ×3** (nada queda en DB).
- **Honestidad de instrumento (regla-C contra mí, 2 cazados en el run):** QA v1 tumbaba 93% de R1 por tratar el discriminador de producto (metadata adjudicada, EXIGIDO por el spec) como token inventado → v2 whitelist-metadata (tras el fix: R2 solo 2 fallos REALES de alucinación = el gate muerde sin FP); F2 v1 gateaba fact-bearing (erróneo para SWAP: el flip lo da cualquier surrogate del padre) → v2 dos niveles. Ambos declarados en el run-doc; delta-check H4 confirmó blurb-padre (0.010-0.054 ≫ tie).
- **Decisión pendiente (Alberto, presupuesto):** pase corpus R2(+R3) ≈ **$160-270 LLM** (estimación por-doc del piloto: ~$0.15-0.25/doc × 1.069) + QA aparte (~$10-30) + embeddings marginales; effect-size corpus = ESTIMADO (H8). Ship-gate sin cambio: bvg PASS-control ±2 antes de encender nada en demo. **Nada shippeado en esta sesión.**
- **Alternativas descartadas**: R1 como sustituto barato (medido 0/4); frameworks LangChain/LlamaIndex como "brazos" (mismo patrón, re-platform disfrazado — validación BP s93); gate B→C y criterios sin estratificar (dúo). **Relacionado**: DEC-085 (bake-off), spec v2, run-doc, tally 198+.

## DEC-087 — s94b/T0: infraestructura PERMANENTE del pase de enunciados construida y dúo-hardened — schema parent_id (007 APLICADA), invariante de no-servicio, ENUNCIADOS_MULTIVECTOR, QA generalizado (fix decimales REPRODUCIDO), panel de desplazamiento, pase idempotente
- **Fecha**: 3 jul 2026 (s94b/T0, GO de Alberto al plan de tramos v2). **Impacto**: ALTO (DDL en DB viva + seams de retrieval + instrumentos-gate de T1). **Qué**: los 6 entregables T0 del plan (`evals/s94_tranches_plan.md` v2):
- **(1) Migración 007 APLICADA** (verificación regla-C pre-apply contra `pg_get_functiondef`: las definiciones VIVAS diferían de la migración 006 del repo — 21 columnas + `SET hnsw.ef_search='120'` de s59b, que se habría PERDIDO; el rol MCP no puede adjuntar el GUC → `set_config(...,true)` en el body, equivalente en REST-por-llamada). `parent_id` ON DELETE CASCADE + `ingest_batch` + índices parciales; `match_chunks_v2` +parent_id +`include_surrogates DEFAULT FALSE`; FTS excluye SIEMPRE. **Rollback EJECUTABLE**: `migrations/007_rollback.sql` (defs pre-007 capturadas). Un DROP fallido a mitad NO dejó la demo caída (transaccional, verificado).
- **(2) Invariante de NO-SERVICIO** (cierra la ventana F1 del dúo s94b): `_no_surrogates` en los 9 GETs serving (8 retriever + `fetch_missing_doc_chunks` — el 9º lo cazó el dúo T0 como CRÍTICO convergente) + RPC default-exclude + `_get_source_files_for_model` (H5: los conteos movían diversify con flag off). Swap permanente `ENUNCIADOS_MULTIVECTOR` from-ROW (sin sidecar — retirado el PILOT_* fail-open), fail-closed, PRE-merge. **14 tests**.
- **(3) QA generalizado CALIBRADO con 2 vueltas de regla-C:** v1 94.9% → +valores-frecuentes 91.7% → **+DECIMALES 86.6%** (H2 del sub-agente, REPRODUCIDO por él y verificado el fix: '13,9 V' alucinado sobre fuente '13,8 V' pasaba — `_normv` preserva separadores → token '13p8'); 2/2 alucinaciones conocidas cazadas en las 3 vueltas. Lección de framing (bias #51, cazada por el sub-agente): "calibrado 2/2" era literal-cierto y materialmente sobre-afirmado — la clase dominante (decimales) no estaba cubierta.
- **(4) Panel de desplazamiento** con fix de EMBARGO (H1 CRÍTICO: el filtro `"heldout"` vs `"held-out"` del YAML era código muerto → los 12 held-out estaban DENTRO del pin; re-pineado dev-only + `query_logs` reales [`query_gaps` era 404] + freeze-guard config + rank-shift real + suelo de ruido self-compare).
- **(5) Pase idempotente** (`scripts/enunciados_pass.py`): uuid5+delete-POR-DOC (H4: resumable tras crash sin re-pagar), `resolve_parent` same-page ±1 (H6: el fallback doc-entero rompía la garantía de cita), temperature=0 (H7), prompts v1 CONGELADOS, extraction_sha256=del-padre (consistencia con index_chunks verificada). Smoke MIDT180 --dry: 548→427 QA-OK, cobertura 65%.
- **(6) Correcciones de gates por el smoke:** umbral QA-rate re-registrado a CALIBRACIÓN-EN-T1 (el ≥97% heredado del piloto era teatro con el signo cambiado: full-doc real ~78-86%); coste re-estimado (banda $160-270 OBSOLETA; T1 ~$40-100 y su medición fija T2-T3).
- **Dúo del build (2 rondas): cross-model 6/6 + sub-agente 9/9 (H2 con REPRO propio), 0 FP — todos aplicados.** El sub-agente verificó contra DB viva: demo HOY sin riesgo; ventana F1 cerrada. **435 tests verdes. Nada encendido** (`ENUNCIADOS_MULTIVECTOR=off`; 0 surrogates en DB).
- **Qué falta para T1 (gate = GO de gasto de Alberto, ~$40-100):** lista de docs T1 (marcas-golds + 2-3 no-vistas isPerfect-bajo) + umbral QA calibrado con los primeros ~20 docs + gate duro de reproducción (famtie ≤8 swap-on, ≥4/6 flips DEC-086).

## DEC-088 — s94c/T1: el pase corpus por tramos EJECUTADO → NO-GO del enfoque "surrogates en índice compartido"; T1 cazó un fallo arquitectónico ANTES del gasto de corpus (el diseño de tramos funcionando)
- **Fecha**: 3 jul 2026 (s94c/T1, GO de Alberto al gasto). **Impacto**: ALTO (rumbo del workstream ingesta + hallazgo de arquitectura de índice + toca la DB viva). **Qué**: T1 (36 docs seleccionados, ~$50-75) ejecutado con Sonnet 4.6 (p1) sobre los 14 docs-piloto para el gate de reproducción. `evals/t1_run.md` = artefacto de decisión.
- **VEREDICTO: NO-GO al enfoque tal-cual. Gate G1 (reproducción) FALLA: 2/6 flips DEC-086 (criterio ≥4/6).** El mecanismo enunciados→findability sigue vivo (piloto s94 lo midió 12→6) pero NO puede compartir el índice HNSW con los chunks reales.
- **Causa raíz (confirmada al 100%, no teorizada):** insertar 21.995 surrogates (parent_id set) al MISMO índice HNSW que los 22.339 chunks reales (índice ×2, 47% surrogates) → con ef_search=120 el traversal explora 120 candidatos de los que ~mitad son surrogates que el filtro `parent_id IS NULL` descarta DESPUÉS → ~60 reales efectivos → **recall de los chunks ORIGINALES cae: control 12→19**. `iterative_scan` (pgvector 0.8) solo recupera a 17. El multivector (13) queda NETO PEOR que el baseline limpio (12): dilución + enterramiento del enunciado relevante entre sus miles de hermanos del mismo doc. **El piloto s94 no lo vio porque usó 251 surrogates transitorios y DIRIGIDOS** (dilución despreciable); a escala de docs-enteros el mecanismo se ahoga.
- **Aislamiento decisivo (cadena verificada):** control 12 (pre-T1) → 19 (post-inserción) → DELETE del batch → **17 (NO 12: pgvector deja los vectores borrados como FANTASMAS en el grafo HNSW hasta VACUUM)** → `VACUUM chunks_v2` → **12 con lista de misses IDÉNTICA al baseline s92**. Dilución confirmada; demo restaurada.
- **2 fallos latentes cazados + arreglados de paso:** (1) la FK `chunks_v2.duplicate_of` no tenía índice de soporte → seqscan por-fila en cada DELETE (timeout al borrar el batch) → `idx_chunks_v2_duplicate_of` (migración 009, PERMANENTE). (2) Regla operativa nueva: rollback masivo de surrogates exige VACUUM o el recall no se restaura.
- **Restauración (rollback documentado):** 21.995 enunciados volcados a `evals/t1_surrogates_dump.jsonl` (gitignored, preserva ~$50-75 de generación) → batch borrado → RPC revertido a 007 (migraciones DB del episodio: 008 iterative_scan diagnóstico → 009 idx → 010 revert → VACUUM) → schema T0 (parent_id/ingest_batch/include_surrogates/invariante) CONSERVADO (infra válida, solo el ENFOQUE de pase es NO-GO). Demo = pre-T1 + índice 009 nuevo. 435 tests verdes.
- **Side-by-side p1(Sonnet 4.6) vs p2(Sonnet 5) — 6 docs unseen, dry:** p2 gana QA-rate (92.6% vs 90.0%), cobertura (100% vs 96%), volumen (+29%), a coste igual (intro $2/$10 hasta 31-ago). **Vintage recomendado para el redesign: Sonnet 5.** (Pricing verificado vía skill claude-api.)
- **Redesign (→ dúo + decisión Alberto, ANTES de más gasto):** (A) tabla/índice HNSW SEPARADO para surrogates — el canal multivector busca ahí y hace swap al padre; índice real intacto (el fix propio, y el churn de enunciados nunca toca los chunks reales); (B) índices HNSW PARCIALES en la misma tabla (WHERE parent_id IS NULL / NOT NULL); (C) generación DIRIGIDA (no docs-enteros) reduce volumen+enterramiento, combinable con A/B. Ninguno cablea sin dúo.
- **Alternativas descartadas**: seguir a T2-T3 con el enfoque actual (G1 falló, el mecanismo se ahoga); iterative_scan como fix suficiente (medido: 19→17, no basta); borrar sin VACUUM como restauración (medido: deja fantasmas). **Relacionado**: DEC-086/087, `evals/t1_run.md`, `migrations/009`, LEVER_DIGEST fila fine-grained.

## DEC-089 — s95: redesign de enunciados EJECUTADO con 2 pilotos ($3.5) — arquitectura tabla-separada VALIDADA con famtie 12→7 (candidato a ship, gate bvg pendiente); deep-lookup agéntico NO-GO; agentic-RAG-como-arquitectura descartado con evidencia
- **Fecha**: 4 jul 2026 (s95, GO de Alberto tras pregunta "¿cómo se hace en RAGs similares? ¿agentic RAG?"). **Impacto**: ALTO (rumbo del workstream + esquema DB). Artefacto: `evals/s95_redesign_pilots.md` (pre-registro v2 post-dúo + resultados).
- **Research previo (workflow 3 agentes, fuentes verificadas):** BP unánime multi-vector = surrogates en índice PROPIO, padre por ID (LangChain MultiVector/ParentDocument, LlamaIndex auto-merging, Dense X, Pinecone namespaces; pgvector README: partial index para filtro binario — el post-filtro documentadamente colapsa recall = el mecanismo exacto de DEC-088). **Dense X: +2.2 Recall@20 con embedder fuerte** (prior rebajado, honesto). **Agentic RAG general NO paga para nuestro perfil** (ACL 2026: 2.7-3.9× tokens y PIERDE vs re-ranker en refinamiento; nuestro root-cause no es multi-hop) → descartado como swap de arquitectura; la variante quirúrgica (deep-lookup) se midió como piloto D.
- **Dúo sobre el plan v1 (Protocolo 3): 15 hallazgos, 15 confirmados regla-C, 0 FP, 4 críticos** (IDENTITY_FETCH=llm habría sido NO-OP silencioso por parser booleano; punto de fusión del RPC = parámetro libre que decidía los gates; pre-filtro léxico en D re-introducía el techo DEC-085; set de flips mal citado + contradicción '99+99'). Todo integrado en v2 ANTES de medir. Tally: `evals/adversarial_review_log.jsonl`.
- **PILOTO A (tabla `chunks_v2_enunciados` separada + HNSW propio, migraciones 011/012, dump T1 re-embebido ~$3, receta pineada):** 3 brazos: A1 corpus-wide 12→8 · A2 +paridad de filtros 12→8 · **A3 +colapso Dense-X (fetch 200 → padres únicos keep-max → fusión → cap) 12→7**, 0 nuevas-miss en TODOS, **control 12 INTACTO en todos = la dilución DEC-088 eliminada por construcción; arquitectura VALIDADA**. A-G1 estricto (≥4/6 flips canónicos) FALLA (2/6) → rama parcial-informativo pre-registrada. Trace por-hecho de los 4 no reproducidos: '35' = gap de GENERACIÓN (0 enunciados de sus agujas; cobertura T1 parcial); PWR-R/'1 A' = distancia pregunta-TAREA↔enunciado-FILA (el F2 de s94 ya medía PWR-R cos 0.446 < frontera 0.516 — su puerta de flip en s94 queda SIN identificar, declarado); '99+99' = colateral/diversify. **El gap residual NO es de índice.**
- **PILOTO D (deep-lookup: selector Haiku lee outline del extraction store en el seam IDENTITY_FETCH, parser 3-estados fail-fast, sin pre-filtro léxico, página-exacta-primero cap 6): NO-GO.** Gate-0 recall-safe 16/19 (3 FAIL = gaps de doc_map, packet a Alberto, catálogo NO tocado). **D-G1 ❌ 12→11 con 0/6 canónicos** (solo '2222', que A3 ya gana); D-G4 ❌ 38% gatillado (>25%). **Causa estructural:** el seam solo gatilla con doc AUSENTE del pool; post identity-ADD la clase dominante es "doc presente, aguja ausente" → el mecanismo ni corre. NO se itera on-eval (sería tuning). Coste $0.13.
- **Decisiones que quedan a Alberto:** (1) ship-path de A3: flag `ENUNCIADOS_MULTIVECTOR=on` en demo SOLO tras bvg PASS-control ±2 (ship-gate DEC-086); (2) packet doc_map (MIE-MI-310↔zxe [DB: ZXAE/ZXEE], MIDT190↔sdx-751 [DB: ID3000], 15092SP [DB: INA]); (3) alcance T2-T3: con -5 en famtie y el residual no-enunciado-soluble, la re-ingesta full-corpus se re-scopea (valor para queries reales de técnicos = plausible pero NO medido — no gastar $100+ por famtie); (4) '35' → regeneración dirigida (C) si se quiere ese hecho.
- **Alternativas descartadas**: agentic RAG como arquitectura (evidencia arriba); iterar D (tuning-on-eval); tocar el catálogo unilateralmente (gobernanza de Alberto); T2-T3 automático (el gate por-tramo sigue vigente). **Relacionado**: DEC-085/086/087/088, migraciones 011/012, `evals/s95_d_gates.json`, `evals/t1_gates.json`.

## DEC-090 — s96: gate bvg de A3 EJECUTADO y PASADO 4/4 — el ship del flag `ENUNCIADOS_MULTIVECTOR` queda en manos de Alberto; hallazgo de instrumento (eje factual K=1 inusable para A/B)
- **Fecha**: 4-5 jul 2026 (s96, GO de Alberto ~$10-20; coste real ≈$12-18). **Impacto**: ALTO (ship a demo + contrato de medición). Artefacto: `evals/s96_ship_plan.md` (pre-registro v2 post-dúo + resultados); brazos `evals/s96{ctl,on}_*` con manifests que PRUEBAN el brazo (stamp `enunciados_multivector` + fingerprint tabla — H5 del dúo).
- **Los 4 criterios pre-registrados, PASADOS:** (1) **rescate→top-5: 3/3** golds-flip (hp001/hp006/hp012) con padre-rescatado en el top-5 congelado tras el rerank — el mecanismo completa el último tramo (el gap que la famtie no ve); (2) **Δ_net PASS-control +2** (11→13, dentro de ±2 y en dirección positiva; residual 23→19; cat013/hp018 de residual→K-INESTABLE = hechos rescatados llegando a respuestas); (3) **invención sin subida: 10/33 = 10/33** en la matriz pareada (11 golds-top5-cambiado × 3 runs × brazo) — REDISTRIBUCIÓN, no subida: el flag LIMPIA contradicciones consistentes (cat011/cat024 3/3→0/3) e introduce hp006 (mispairing JP2→JP6 sobre el chunk correcto que por fin llega — clase SÍNTESIS conocida, expuesta no creada; en control el bot FABRICABA); (4) **latencia p50 +725ms** (<1s).
- **Hallazgo de INSTRUMENTO (regla-C ×2 contra mi propia alarma):** la lectura ingenua "2 vs 13 contradicciones" habría matado el ship — FALSA: 9/13 golds tenían top-5 IDÉNTICO entre brazos (el flag no pudo causarlos) y el mismo control da 2→20 entre runs (muestreo de generación + detector no-determinista sobre input idéntico). **El eje factual del atomic_scorer a K=1 NO sirve para comparar brazos; la comparación válida = matriz pareada multi-run sobre los golds cuyo input cambió** (misma lección que el juez→K-mayoría, DEC-015). Queda como norma para futuros A/B con ese eje.
- **Build del gate (permanente, harness):** `bvg_kmajority.py` estampa ahora la variable de tratamiento `enunciados_multivector` (flag efectivo + fingerprint `chunks_v2_enunciados` + sha del swap) + `identity_resolve` + `retrieve_ms` p50 por gold (NINGÚN harness emitía latencia — H2 del dúo).
- **Qué queda:** decisión de Alberto = `ENUNCIADOS_MULTIVECTOR=on` en Railway (reversible); post-flip pre-registrado: smoke completo + verificación del flag efectivo + verificación en demo. Held-out NO consumido (declarado, modelo operativo s84). hp006/JP2-JP6 = evidencia nueva del cuello SÍNTESIS (mispairing en tablas densas) — al dossier del workstream síntesis, no bloquea este ship.
- **Alternativas descartadas:** leer el eje invención a K=1 (medido inusable); exigir ganancia de PASS (root-cause RETRIEVAL=2/30 — framing de Alberto confirmado: el valor se mide en famtie 12→7 + rescate-en-top-5, no en PASS). **Relacionado:** DEC-086/088/089, `evals/adversarial_review_log.jsonl` (2 rondas s96, 11/11+6/6 confirmados 0 FP).

## DEC-091 — s97: lever diversify (tie-break semántico de empates) EJECUTADO → NO-GO al ship (regresión de contenido real en hp001; el coseno-desempate hereda el gap de vocabulario). El dúo cazó mi racionalización pro-GO
- **Fecha**: 5 jul 2026 (s97; autor Opus 4.8). **Impacto**: ALTO (ship a demo + lección de método). Artefactos: `evals/s97_diversify_tiebreak.md` (pre-registro v2 + gate + veredicto), `evals/s97_ship_verdict.md`, brazos `evals/s97{ctl,on}_*`. Tally: `evals/adversarial_review_log.jsonl` (3 rondas s97: plan 12/12, veredicto BM25/RRF 9, ship-verdict cross-model 5 + Sonnet 3).
- **Qué**: `DIVERSIFY_TIEBREAK` = desempate por coseno real SOLO entre chunks empatados (stamps planos léxicos 0.80/0.70), within-source, clave-tupla (similarity intacta). Diagnóstico correcto (los stamps planos crean empates → orden arbitrario → round-robin ciego; la aguja de hp012·'99+99' quedaba fuera por sorteo). Build dúo-hardened, famtie **7→6 K=3 estable, 0 nuevas-miss** (G1/G2 ✅).
- **Gate bvg (ship-path, 2 brazos A3-on): PASA en la letra pero NO-GO en el fondo.** PASS-control 15→14 (−1 en banda ±2), invención 9→8 (no sube). PERO: 26/39 top-5 cambian, 5 golds flipan. El dúo (cross-model GPT-5.5 + sub-agente Sonnet, convergentes + regla-C del autor) verificó chunk-por-chunk: **hp001 PASS→FALLO es regresión de CONTENIDO real** — el tie-break sacó del top-5 el chunk con el atomic_fact core#1 ('candado 🔒 → PANTALLA ACCESO → código 2222' = la respuesta a "cómo entrar al menú de programación avanzada'); el juez falla 4/5 citando esa omisión. cat021 (filler/K-ruido) y hp013 (fallo de generación, no del tie-break) NO son regresiones reales; cat012/hp007 que entran SÍ son estabilizaciones reales. Neto: +2 gana, −1 regresión-real, 2 K-ruido.
- **NO-GO** por el tripwire pre-registrado ("re-barajado que saca contenido de un PASS-control = NO-GO sin racionalizar"). Una regresión de contenido verificada (hp001) basta, aunque el neto agregado sea −1-en-banda. **Mi lean pro-GO ("churn benigno") fue racionalización basada en leer 55 caracteres del chunk** — el dúo lo cazó (feedback_my_bias: el sistema no depende de Alberto como anti-bias; el cross-model corta mi over-claim, ahora 10 sesiones seguidas).
- **Lección estructural (la valiosa)**: el coseno-desempate NO es estrictamente mejor que el orden arbitrario — **hereda el gap de vocabulario** (DEC-085): degrada el chunk-respuesta-de-coseno-bajo (candado, gap query↔celda) bajo chunks de coseno-alto que casan con la pregunta pero no responden. Gana donde el mejor coseno ES la respuesta (hp012), pierde donde no (hp001). Callejón sin salida por esta vía; cualquier ranker sobre-la-query hereda el techo (consistente con FTS/BM25 NO-GO). El famtie 7→6 era real pero NO se traduce en calidad-de-respuesta neta.
- **Gap de INSTRUMENTO cazado (mejora del gate bvg)**: el agregado ±2 sobre 39 golds fue CIEGO a una regresión puntual-pero-real (hp001 promediada). Instrumento cheap a añadir antes de fiarse del agregado: "¿algún atomic_fact core del top5-control desaparece del top5-tratamiento?" para los PASS-control. → TECH_DEBT.
- **Estado**: flag OFF; el lever NO se mergea a main (código en la rama como medición reproducible). Catálogo doc_map (MIDT190→sdx-751, 15092SP→am2020/afp1010) + golds re-tipados s97c (adjudicados por Alberto, valor independiente) SÍ van a main. **Alternativas descartadas**: shipear en la letra (regresión real de contenido); re-medir K≥2 (el dato ya es concluyente — hp001 no es ambiguo); salvar el lever con otro tie-breaker (todos heredan el gap de vocabulario). **Relacionado**: DEC-050 (colateral cosine-merge, el mismo modo de fallo), DEC-085 (gap de vocabulario), DEC-090 (patrón bvg), TECH_DEBT #71.

## DEC-091b — s97 CORRECCIÓN (challenge de Alberto): el tie-break NO es "callejón sin salida" — está BLOQUEADO por el reranker
- **Fecha**: 5 jul 2026 (mismo día, tras challenge de Alberto). **Corrige el framing de DEC-091.**
- **Dato que lo fuerza**: la aguja de hp012 ('99+99') SÍ llega al **top-5 SERVIDO** con el tie-break (estaba en pool-pos-16, enterrada por la lotería de empates → rescatada al servido). El tie-break funciona de verdad para retrieval; no es mirage de pool. Y en hp001 el retrieval también acertó (respuesta en **pool-pos-1**); quien la tiró fue el **reranker LLM (claude-sonnet-4-6)**, que prefirió chunks que casan léxicamente con "avanzada" sobre el que contiene el procedimiento (candado→2222).
- **Framing corregido**: el tie-break es una herramienta de DOS CARAS — rescata respuestas enterradas (hp012) Y alimenta distractores al pool (hp001) — y su NETO depende de la calidad del reranker. Con el rerank actual (se aturde con distractores léxicos) = neto negativo → NO-GO **ahora**. Pero **NO está muerto: está bloqueado por el reranker**. El "callejón sin salida" de DEC-091 era over-claim. Hipótesis (NO medida): con un rerank robusto al gap de vocabulario, el tie-break podría ser net-positivo → re-medir antes de afirmar.
- **Reencuadre del residual (Q1 de Alberto)**: distinguir "no-recuperado" (→ document-side: hypothetical-questions / A3-prosa) vs **"recuperado-pero-no-servido"** (→ RERANK). hp001 es lo segundo (la respuesta estaba en pool-pos-1). El lever más barato y targeted para esa clase = afinar el reranker LLM (prompt/modelo que razone "¿contiene la respuesta?" vs "¿habla del tema?"), no regenerar corpus.
- **hp018/hp009 + ADD-vs-REPLACE (Q2 de Alberto, concedido)**: elegir ADD sobre REPLACE (DEC-084) fue en parte TAPAR incompletitud del entity-mapping. hp009 (familia-genérico/EOL): REPLACE quitó un doc CORRECTO (genérico no-mapeado al modelo) = sobre-filtrado. hp018: el '1 A' de MIE-MI-310 (ZXAE/ZXEE) es correcto para ZXe **por coincidencia de valor, no por calidad** — mecanismo inseguro (si fuese 2A, el bot serviría 2A como spec ZXe). **Fix BP estructural = completar el entity-linking del catálogo** (qué docs —genéricos + spec-compartida— sirven a qué productos) → REPLACE se vuelve seguro (mantiene genéricos, filtra cross-family real). Es el workstream DEC-074. El "flag cross-family en conducta" = cinturón de seguridad barato (útil para un bot de PCI: servir spec de otra familia en silencio = riesgo real), NO la cura.
- **Relacionado**: DEC-091, DEC-084 (ADD>REPLACE), DEC-074 (entity-linking BP), TECH_DEBT #72 (check core-servido).

## DEC-092 — s98: matriz de rerank (8 métodos) → el lever que paga es SERVIR-MÁS (top-10), NO tocar el reranker; reencuadrado por el dúo a hiperparámetro-de-ancho retrieval-level; smoke e2e caza truncado en un control → NO ship limpio
- **Fecha**: 5 jul 2026 (s98; autor Fable 5, Opus 4.8 al arranque). **Impacto**: ALTO (caracteriza el lever rerank + método). Artefactos: `evals/s98_rerank_matrix.md` (matriz + CUT15 + correcciones dúo), `evals/s98_duo_brief.md`, `evals/s98_bvg_gate_prereg.md`, `scripts/s98_rerank_harness.py` (+`s98_compare.py`, `s98_topk_smoke.py`), `evals/s98_rerank_{M0,M1,M2,M3,V0,R4,T8,T10,CUT15}.json`. Tally: `evals/adversarial_review_log.jsonl` (ronda s98: 8 confirmados, 0 FP).
- **Objetivo (Alberto, autónomo nocturno)**: rerank-miss a **1-2** con mejora ESTRUCTURAL (no overfit); dúo valida antes de implementar; medir en DEV (held-out embargado). Métrica = RERANK-MISS (aguja-en-pool que sobrevive al top-N servido + filtro sim≥0.4), 39 dev, 125 facts-core-con-aguja.
- **Matriz (baseline M0 top-5 = 13, ±1 jitter)**: M1 prompt "¿contiene la respuesta?" 14 (wash) · M2 forzada 17 (peor) · **M3 Opus 4.8 16 (capacidad NO es el límite)** · ventana 800→2500 21 (peor) · Voyage rerank-2.5 21 (peor, coherente DEC-048) · **RRF fusión retrieval+rerank 45 (+3/−35: retrieval es baja-precisión, fusionar mete ruido)**. **Las 6 intervenciones SOBRE el reranker fallan/empeoran.** · **T8 servir top-8 = 6 (+7/−0)** · **T10 servir top-10 = 2 (+11/−0), alcanza el objetivo.**
- **Hallazgo + reencuadre del dúo (cross-model GPT-5.5 + sub-agente Sonnet, convergentes, 0 FP)**: el reranker NO se equivoca de relevancia — coloca los chunks-respuesta en rank 6-15; la ventana de servicio de 5 (DEC-018 "generate narrow") era el cuello. **CUT15** (petición fija=15, cortes 5/8/10/15 → 18/10/3/1; 17 agujas en rank 5-14) CONFIRMA el diagnóstico Y la corrección del cross-model: cut@5-de-15=18≠M0=13 → el tamaño de petición cambia el orden ({top_k} entra en el prompt). **→ es palanca de ANCHO-DE-VENTANA (hiperparámetro dev-elegido), NO arreglo de calidad del reranker.** El dúo reencuadró "breakthrough estructural" → "hiperparámetro que exige gate e2e".
- **Reconciliación Protocolo 4 (declarada)**: métrica de HOY = rerank-miss retrieval-level; el settled = PASS-plateau noise-limited (DEC-075/078) → T10 NO promete subir PASS; valor = retrieval-level (patrón A3/DEC-090). Gate bvg = NO-REGRESIÓN, no caza-PASS. T10 ≠ consumo-aditivo (DEC-069/L22: aquel unía al pool por identidad y desplazaba; T10 sirve más del MISMO pool rankeado, pool intacto).
- **Smoke e2e barato (path prod real, top_k=5 vs 10 — ANTES del bvg caro, disciplina de coste) CAZA el riesgo load-bearing (INTERMITENTE)**: **cat019 (CONTROL) truncó a k=10 en 1 de 2 runs** (`stop=max_tokens` out 2048; re-check end_turn 1982) — la respuesta a k=10 ROZA el cap `LLM_MAX_TOKENS=2048` (fijo; contexto ~2× → generación más larga) = truncado estocástico al borde, no determinista (k=5 = end_turn 1432, margen holgado; k=8 = 1920). Los otros 5 controles intactos. Rescate a nivel-respuesta PARCIAL: 3/9 golds (hp011·ABORT+enclav, hp015·convencional, hp017·editar-config), 2 ya presentes a k=5, 4 no-show (synthesis-drop). **El harness retrieval-miss NUNCA llama al generador → no habría visto el truncado; el smoke barato lo cazó antes del bvg.**
- **Veredicto: rerank-miss 1-2 ES alcanzable a nivel retrieval (T10=2) PERO top_k=10 NO es ship limpio** — trunca ≥1 control (cat019) + beneficio parcial + coste 2× contexto/latencia. Shipearlo exigiría TAMBIÉN subir `LLM_MAX_TOKENS` (cambio aparte con sus riesgos) o aceptar truncado. Fallback pre-declarado = top_k=8 (recupera 7/13, menos contexto → menor riesgo). **NO se cablea.** Gate bvg diseñado + pre-registrado + modo prod-fiel (`BVG_TARGET_MODELS`) + flag `RERANK_TOP_K` (getenv, default 5 inerte) LISTOS para el GO de Alberto — pero el smoke ya recomienda no shipear 10 as-is.
- **Fixes prod (defensibles independientemente)**: reranker retry-sin-temperature (modelos 2026 la deprecan) + parser regex robusto (Opus añade texto tras el JSON) + param `relevance_instruction`; `RERANK_TOP_K`→getenv; bvg `BVG_TARGET_MODELS` (corrige el crítico del cross-model: bvg rerankeaba sin target_models = no-fiel al path prod). Tests 450 verdes.
- **Alternativas descartadas**: shipear top_k=10 as-is (riesgo de truncado intermitente en cat019 + rescate parcial); afinar el reranker (6 métodos medidos NO-GO — capacidad/prompt/ventura/CE/fusión); declararlo "estructural" (es hiperparámetro dev-elegido, riesgo sweep-peak); correr el bvg caro autónomo esta noche (pregunta cero: no cambia una decisión que YO pueda tomar — ship = Alberto + cross-model FULL; smoke ya recomienda no-ship-as-is). **Residual del reranker (hp005·CIRCUITO SIRENA, hp006·Tierra, enterrados >rank-15) = document-side (hypothetical-questions), no rerank.** **Relacionado**: DEC-018 (generate narrow), DEC-048 (CE rollback), DEC-069 (consumo-aditivo), DEC-075/078 (plateau), DEC-090 (patrón bvg/A3), DEC-091/091b (tie-break bloqueado en rerank — este lever es el "afinar el reranker" que 091b señalaba, MEDIDO NO-GO como fix de calidad), TECH_DEBT #72 (check core-servido).

## DEC-092b — s99: CORRECCIÓN del veredicto del ancho (challenge de Alberto) → top-10 SHIPPEADO. Las "regresiones" del gate eran artefactos del juez, no dilución real
- **Fecha**: 6 jul 2026 (s99). **Corrige el "NO ship limpio" de DEC-092.** **Impacto**: ALTO (ship a demo). Artefactos: `evals/s98_bvg_gate_prereg.md` (v2 dúo-endurecido), `scripts/s99_width_noregr.py` (gate no-regresión, juez canónico reusado), `scripts/s99_served_live.py` (medición justa), `scripts/s99_regr_verify.py` (verificación de regresiones), `evals/s99_width_noregr_K5.json`. PR #113.
- **Contexto**: DEC-092 (s98) declaró top-10 "no ship limpio" por rescate-respuesta parcial (smoke 3/9) + truncado borde. Alberto challengeó: (1) la vara justa del ancho es rerank-miss / servido-a-síntesis (NO PASS — medir PASS es "injusto" al reranker: hace su trabajo si mete el chunk en top-8 aunque síntesis no lo escriba); (2) las "regresiones" podían ser el bot sirviendo MÁS info, no dilución.
- **Medición justa (servido-a-síntesis, live, `s99_served_live.py`)**: top-8 sirve +3 / top-10 sirve +5 chunks-respuesta que top-5 tiraba, **0 regresión**, agujas en rank 3-9 (confirma el mecanismo). El ancho hace su trabajo.
- **Gate de no-regresión e2e (`s99_width_noregr.py`, control top-5@2048 vs top-10@3500, K=5 juez GPT-5.5 K-mayoría, 20 golds PASS-control+PARCIAL)**: `LLM_MAX_TOKENS`→getenv (fix crítico dúo: editar el literal cambiaba prod-Railway). K=3 dio +5/−2 (parecía positivo); **K=5 des-ruidó a +3/−3 aparente**. PERO **verificación leyendo las respuestas (regla s97: verificar antes de declarar, en el ESPEJO — no asumir regresión real de un juez ruidoso)**: las 3 "regresiones" NO son dilución — **cat005** añade "Firmware 1.2" (CONFIRMADO literal en corpus: "CS4 Digital Firmware 1.2"); **cat009** añade LEDs de modo + nivel de acceso (con fuente, MEJOR respuesta); **cat015** añade un hint sourced+hedged (borderline, único discutible, en gold admit-no-info); **hp001** = ruido (en K=5 gana). **El juez penaliza al bot por servir MÁS info correcta con fuente**, no por regresar. 0 invención, 0 truncado con 3500.
- **Veredicto CORREGIDO: top-10 ENRIQUECE la respuesta (más completa, con fuente), 0 regresión real, 0 invención.** Coste: +6-11% longitud (mediana) + 2× contexto. **SHIP (GO de Alberto).** PR #113 = `RERANK_TOP_K`/`LLM_MAX_TOKENS` getenv (inerte por defecto); Railway pone 10/3500. Cautela anotada: vigilar especulación en golds admit-no-info (cat015).
- **Lección de método**: el error de DEC-092 fue fiarme del veredicto PASS→PARCIAL del juez sin leer las respuestas — la regla-C / "verificar antes de declarar" de s97 aplica también EN EL ESPEJO (no declarar una regresión REAL sin verificar que lo es; un juez calibrado a golds penaliza info-extra-correcta). Alberto lo cazó. **Relacionado**: DEC-092 (s98), DEC-090 (patrón bvg/ship A3), DEC-091b (medir justo el lever, no confundir capas), `feedback_my_bias`.

## DEC-093 — s99b: rumbo demo-vs-nota, identidad re-scopeada, y DEC-075/síntesis DECLARADO CADUCO (re-medir)
- **Fecha**: 6 jul 2026. **Impacto**: ALTO (rumbo + método de medición). **Dúo**: 6 rondas (gate/plan/packet/carryforward/rewriter/assessment-spec), cross-model + sub-agente cada una; log `adversarial_review_log.jsonl` ts 2026-07-06. El dúo cortó ~5 sobre-afirmaciones de framing MÍAS → anti-bias sano.
- **Rumbo (Alberto)**: **blindar-demo → luego nota**. El trabajo de demo debe ir ACOTADO: falló 3× (heurístico carry-forward v1 marca+longitud, v2 código-sólido — ambos tumbados por el dúo por FP sobre vocab técnico RS485/IP54; y el reescritor NO arregla el caso CS4). Decisión final s99b: **pivotar a la NOTA** (opción c), reescritor APARCADO.
- **Reescritor conversacional = BP (condense-question)** para multi-turn (caso real del técnico on-site), pero **APARCADO con checklist de retake** (`evals/s99_rewriter_design.md`). **Medido**: query CS4 limpia → el bot RESPONDE la CS4 gas (2388 chars del `Manual-de-Usuario-CS4`, retrieval semántico pese a `extract_product_models=[]`) → el reescritor NO deja "no info", **hace responder gas = viola PCI-puro**. El fix del CS4 visible = **declinar-gas** (pequeño, determinista) + **B** (adjudicar). Reescritor + declinar-gas van ACOPLADOS.
- **PCI-fuego puro (gas FUERA por ahora)** — TECH_DEBT #75. `fidegas:cs4` es `candidate:true` → ni el detector viejo (`model_catalog.json`) ni el resolver gobernado lo reconocen (ambos excluyen candidates). **Pepperl-Fuchs SÍ es dominio PCI** (Z728 distribuido por Detnov, precedente s23-24) → corregido over-reach mío que lo metía fuera con el gas.
- **FOCO 1 re-scopeado (`evals/s99_foco1_gate.md`/`plan.md`, dúo ×2)**: "cablear detector→catálogo gobernado" NO arregla CS4 (candidate) ni ZXe-servido (retrieval). El detector vive del catálogo VIEJO (`model_catalog.json`, regen de `chunks_v2.product_model`+MODEL_PATTERN); el resolver gobernado (`catalog_resolver`, `IDENTITY_RESOLVE=on`) es OTRO extractor. Reconocimiento = B/DEC-074 (adjudicación de datos), no wiring.
- **Packet candidatos (`evals/s99_candidates_packet.md`, dúo ×2)**: 630 sin confirmar; **T1 ≈ 363** de incendios forma-modelo (BRUTO, necesita QA TOTAL — veneno alfanumérico + 98 tokens ≤4 chars; adjudicar NO es inerte: mueve top_k budget). Es el workstream B/DEC-074, no un toggle. "candidate"=pendiente QA humano, **⊥ idioma/versión** (filtros separados `_filter_by_document_status`/`_filter_by_language`); el contenido candidate SÍ se sirve, solo falta la identidad.
- **DEC-075 (síntesis "settled, sin lever barato; PASS plano ~9/39") DECLARADO CADUCO**: medido en s87 sobre corpus 2026-06-09, **ANTES** de ancho top-10 (DEC-092b, HOY), A3 enunciados (DEC-090), identidad-resolve (DEC-084). NO re-medido a nivel-hecho → **hay que re-medir**. (Alberto lo cazó; yo corregía con datos caducos = `feedback_my_bias`.)
- **La infra de medición BIT-ROTEÓ**: el DEF s85 (`s85_retrieval_miss_DEF.yaml`) se desalineó de los golds actuales (editados s97c) → `synthesis_miss_judge.py:114` (assert de longitud) crashea. Reusar el DEF viejo NO es viable. Un assessment actual cuesta ~$15 (regen DEF + synthesis), no $2.
- **Assessment a nivel-hecho ESTANDARIZADO — spec v2 dúo-hardened (`evals/s99_factlevel_assessment_spec.md`)**: unifica los 4 instrumentos ad-hoc (retrieval_miss + synthesis_miss + audit_retrieval_funnel + s87_rootcause). Fixes del dúo: 5 clases terminales (NO colapsar CORPUS-GAP), "servido"=post-`RELEVANCE_THRESHOLD`, `judge-FN`→eje gold/juez, anti-bit-rot=regenerar-siempre (cache circular descartado), freeze-contract completo (flags+pool pineado), sub-motivo=juez nuevo con contexto servido, coste ≈$15-20. **BUILD = 1ª tarea próxima sesión** → correr → decidir foco con datos frescos.
- **Alternativas descartadas**: whitelist elíptico (mutila follow-ups del técnico); heurístico de arrastre (FP sobre vocab técnico, dúo ×2); medir PASS holístico ahora (caro, no acciona síntesis); reusar DEF viejo (bit-rot). **Relacionado**: DEC-074 (entity-linking BP), DEC-075 (ahora caduco), DEC-084/090/092b (levers shippeados que invalidan la medición vieja), `feedback_my_bias`, `feedback_cost_discipline`.

## DEC-094 — s100: assessment a nivel-hecho ESTANDARIZADO construido+corrido → DEC-075/síntesis RE-CONFIRMADO fresco (cuello dominante); identidad+corpus ≈0; scoreboard como source-of-truth
- **Fecha**: 6-7 jul 2026 (s100; autor Opus 4.8). **Impacto**: ALTO (instrumento canónico de medición + re-deriva el foco). **Dúo**: spec ×3 rondas (cross-model GPT-5.5 + sub-agente Opus) + código ×2 rondas (v1: 8 hallazgos; final: SÓLIDA 0-BLOQUEA) — **todo verificado regla-C, 0 FP netos**; el dúo + los smokes cazaron 4 bugs de diseño que habrían dado números plausibles-pero-falsos. Artefactos: `scripts/factlevel_assessment.py`, `docs/FACTLEVEL_ASSESSMENT.md` (canónico + **scoreboard**), `evals/s99_factlevel_assessment_spec.md` (v3), `evals/s100_factlevel_full.yaml` (39 golds), `adversarial_review_log.jsonl` (s100).
- **Qué**: entry-point único `scripts/factlevel_assessment.py {smoke|full}` que unifica los 7 instrumentos ad-hoc (retrieval_miss_judge · synthesis_miss_judge · audit_retrieval_funnel · retrieval_miss_famtie · retrieval_miss_diagnose · synthesis_stability · s87_rootcause). Taxonomía family-aware, TODOS los facts clasificados (measurable=flag no gate → jueces semánticos sobre prosa/periodicidades), stability (rep×2, estructural vs flip), sub-motivo con chunks servidos, freeze-contract leído del entorno + asserts anti bug-s45.
- **Ruta medida = EVAL-HARNESS** (sin `target_models`/`available_models`), flags de la demo (Railway: RERANK_TOP_K=10, ENUNCIADOS=on, IDENTITY=ADD, LLM_MAX=3500). Decisión Alberto: paridad con bvg/DEC-075/ancho para comparabilidad. La ruta Telegram sería un track separado. (Caveat declarado en el doc canónico.)
- **RESULTADO (39 golds, 133 hechos)**: OK 89 (67%) · **synthesis-miss 22 → 16 estructural + 6 flip** · retrieval-miss 13 (+~4 de corpus-gap FN) ≈17 · rerank 4 · **corpus-gap 5 → ~0 (todos FN, verificados a mano: el valor SÍ está en el manual — `feedback_corpus_gap` validado 4ª vez)** · identidad/model-filter 0.
- **Titular (DEC-093 respondido con datos frescos)**: **síntesis SIGUE siendo el cuello dominante post-ancho/A3/identidad → DEC-075 RE-CONFIRMADO a nivel de CLASE** (no caduco en veredicto; sí lo era su medición s87). Refinado por sub-motivo (lo que DEC-075 no tenía): de los 16 estructurales ~10 omitted/hedged (lever PROMPT) + ~5 partial (lever RETRIEVAL/chunking) + 2 contradicted. **Identidad y corpus-gap descartados con datos frescos** (⊥ el cuello, RE-CONFIRMA DEC-074). Retrieval within-doc (11) = gap de vocabulario (DEC-085/86).
- **CAVEAT clave (no over-claim, `feedback_my_bias` — spot-check regla-C)**: el sub-motivo de síntesis está **contaminado por scope/gold** (hp007 'cada 6 meses': el bot respondió correctamente la pregunta ANUAL y omitió la semestral porque no se preguntaba = artefacto, no fallo). El nivel-CLASE (síntesis=cuello) es robusto; **qué lever DENTRO de síntesis necesita gold-review por-hecho** (eje gold/juez, etapa separada) → NO lo zanja este run. El eje gold/juez es ADVISORY (veredictos bvg previos; PASS fresco diferido).
- **Scoreboard (petición de Alberto)**: `docs/FACTLEVEL_ASSESSMENT.md` = source-of-truth append-only, 1 fila por corrida → traza cómo cada mejora mueve la aguja (medido en harness, no bot Telegram real — caveat declarado).
- **Alternativas descartadas**: ruta Telegram (no-comparable a DEC-075); measurable() como gate (filtraba 38% = la cola de síntesis → no reproduce DEC-075, cazado por smoke); corpus-gap como clase terminal sin verificación (FN garantizado, `feedback_corpus_gap`); re-correr el full tras el punch-list (la cola corpus ya hand-verificada, anti-coste). **Relacionado**: DEC-093 (declaró caduco → esto re-mide), DEC-075 (re-confirmado a nivel-clase), DEC-074 (identidad ⊥ cuello, re-confirmado), DEC-085/86 (retrieval within-doc = vocabulario), `feedback_corpus_gap`, `feedback_my_bias`, `feedback_cost_discipline`. Punch-list de 7 (dúo final) aplicado al código; #4/#7 documentados como limitación en el doc canónico.

## DEC-095 — s100b-s101: dual-judge en AMBOS ejes del instrumento + gold-review adjudicado + 4 levers upstream MEDIDOS (hyq GO · tiebreak CERRADO · identidad re-confirmada · ancilar declarado) + scoreboard v2
- **Fecha**: 7-8 jul 2026 (s100b-s101; autor Fable 5, mandato autónomo de Alberto: subir OK>95% bajando buckets, upstream-first, GO=reducción-de-bucket, flag de overfitting). **Impacto**: ALTO (instrumento + levers + scoreboard). Dúos: 5 rondas (dual-judge, support-dual, hyq seam ×2, pendientes) — ~40 hallazgos brutos, 0 FP netos, todo regla-C.
- **(a) INSTRUMENTO — dual-judge en los 2 ejes (cambio de juez v1→v2, declarado vs DEC-021):** conveyed (GPT-5.5→Opus 4.8, consenso-de-miss; suite 5 flips/0 FP fakes, artefacto `s100_dualjudge_validation.txt`) + **soporte targeted** (sup_fam=∅ + candidato léxico ordenado→Opus; evidencia `s101_inpool_adjudication.json`: 6/7 "retrieval-miss" eran FN del juez, 0/18 refuters). Fail-fast del primario muerto + flag de degradación por-batch (incidente real: cuota OpenAI murió mid-run → run en cuarentena `_v2_INVALIDO_quota`). Freeze-hash ancla corpus+golds+script+**pipeline-src**; seams de piloto PINEADOS off en DEMO_FLAGS.
- **(b) GOLD-REVIEW (pixel-vs-FUENTE, dúo Fable+GPT-5.5, nunca vs bot):** 5 demotes de scope aplicados (cat001#0, hp002#4, hp007#0/1/6 — Alberto GO); **hp011 r.1→r.I** (Alberto se retractó de s30: esquema mnemónico rS/rI; el corpus r.i era CORRECTO; mi fix intermedio revertido; r.5→r.S sí aplicado a 3 chunks). **LECCIÓN: el cross-model dictaminó GOLD-ERROR y el sub-agente lo anuló citando la adjudicación humana — el cross-model tenía razón contra el ground-truth humano** (a `feedback_7segment_reading`).
- **(c) LEVERS UPSTREAM (todos con control negativo null-corrected — el jitter run-a-run NO es cero, medirlo es obligatorio):**
  · **hyq/HyPE (piloto GO)**: seam offline 0-DDL, índice 7004 preguntas; **cuota propia** (escalas pregunta↔query vs chunk↔query incomensurables — el sort-mixto A3 corta todo) + **barra 0.45** (sin ella 9 EXCESS-HIGH). **2/7 RECALL flips (cat016 = el gate falsable + hp018-6K8)**; residual DECLARADO anti-overfit = hechos ANCILARES al intent (hp011/hp013/hp017: 338 padres sobre-barra, top-10 todos directos-al-intent — priorizarlos sería desplazar matches genuinos). Ship = D2 Alberto.
  · **tiebreak (CERRADO definitivo)**: re-medido CON ancho-10 (la vía de DEC-091b) → hp012 flipea PERO centinela hp001 regresa a nivel-hecho ('1111' sale del top-10 servido) + 9 EXCESS-HIGH/null=0. Tripwire DEC-091 dispara con AMBOS anchos.
  · **cat013 = identidad** (query CAD-150 vs doc ID3000; ni hyq ni léxico — workstream DEC-074). hp014/no-anclables = clase-juez (el dual-soporte arbitra).
- **(d) SCOREBOARD v2 (39 golds, 128 facts, juez v2, jueces sanos):** **OK 91 (71%) · synth 22 (14 stable/8 flip; 12 omitted·6 partial·4 contradicted; cluster cat021×4 = síntesis de familia-de-variantes) · retrieval 8 · rerank 5 · corpus 2.** Upstream 18→10 por fixes instrumento+golds (hyq no-shipped: cat016/6K8 cuentan). Fase 2 en curso: A/B fact-level del `fidelity` block (s69; DEC-051 fue métrica PASS → re-medible; smoke 0/0, full en vuelo).
- **Alternativas descartadas**: perseguir el residual-ancilar con regen dirigida/cuotas mayores (sweep-peak/overfit — flagged); re-correr el full degradado (cuarentena); tiebreak como ON-HOLD otra vez (2 mediciones bastan). **Relacionado**: DEC-021 (extendido), DEC-051 (métrica), DEC-074 (cat013), DEC-091/091b (cerrado), DEC-092b (patrón vara-justa), DEC-094 (el instrumento), `feedback_corpus_gap` (4ª y 5ª vez), `feedback_my_bias`, `feedback_cost_discipline` (incidente cuota + serialización).

## DEC-096 — s102: lever demote-TOC MEDIDO → NO-GO en rerank; la heurística pasa al INSTRUMENTO (v2.2, cierra H4); descubrimiento colateral: el LLM-rerank NO es determinista a temp=0
- **Fecha**: 8 jul 2026 (s102; autor Fable 5, mandato autónomo). **Impacto**: MEDIO (lever medido + cambio de instrumento en zona de dolor). **Dúo completo**: sub-agente Fable fresco (7 hallazgos, 1 CRÍTICO confirmado contra mis propios datos) + cross-model GPT-5.5 con tools (6 hallazgos, 4 confirmados, 1 FP por leer un fichero en append). Tally completo en `adversarial_review_log.jsonl` (2 entradas 8-jul).
- **(a) LEVER L2c (demote de páginas de índice en el rerank) → NO-GO.** Motivación: fase-2 diagnosticó el índice de HOP-138-8ES p.2 SERVIDO en cat017 robando el slot al chunk-respuesta (best_pool_rank=10). Medición (`scripts/s102_toc_measure.py` scan→gate-eyeball→measure; `evals/s102_toc_measure.yaml`): 32 TOCs flaggeados en pools (todos genuinos, 0 FP; 1 falso-negativo cazado y arreglado ANTES de medir: `# ÍNDICE` markdown sin dot-leaders = la página exacta motivadora). A/B OFF-vs-ON sobre pools congelados: **0 GAINS · superficie estocástica ~1-2 TOCs servidos/run** (el único en OFF cayó en cat022, gold 3/3 OK) · exclusión pre-backend re-baraja 11/39 served-sets con 1 loss de contenido real (hp011#3) — la clase DEC-091. **MÉTRICA del veredicto: proxy léxico servido (fact_match≥FLOOR sobre served-10, sin family-filter), NO bucket end-to-end** — evidencia negativa fuerte, no settled-absoluto.
- **(b) DESCUBRIMIENTO (S1 sub-agente, CRÍTICO, verificado):** cat001/cat011 con **0 TOCs en pool (input idéntico ambos brazos) cambiaron 2 slots servidos cada uno → el LLM-rerank NO es determinista ni a temperature=0**. Consecuencias: (i) el churn de cualquier A/B de rerank contiene RUIDO BASE → atribución de losses individuales no es limpia; (ii) el "TOC servido" del full v3 fue evento estocástico. Norma nueva: A/B de rerank exige control de ruido base (par OFF-vs-OFF) o N-reps — igual que la norma K=1-inusable del eje factual (DEC-090).
- **(c) INSTRUMENTO v2.2 (cierra cuarentena H4):** `scripts/toc_heuristic.py` (is_toc_page, determinista, 9 tests) + kill de anclas-TOC en el crédito de soporte L1 de `factlevel_assessment.py` — un índice acreditado NO es soporte por defecto (sus títulos matchean el anchor sin portar contenido → inflaba synthesis-miss); los kills van al canal `l1_killed` (rescate dual Opus si el soporte queda vacío — un título de TOC sí puede soportar hechos nominales) + visibles como `support_toc_killed`. **INSTRUMENT_VERSION="v2.2" estampado EN el artefacto** (F4: cada cambio de juez/clasificador declarado en el output, no solo en el doc). Residuo declarado (S5): si el TOC-kill NO vacía el soporte, los killed no se re-adjudican (consistente con L1 v2.1).
- **(d) Higiene del ship hyq (tramos 1-3/8 generados, QA 15/15 por tramo):** jsonl corrupto reparado (1 línea huérfana de append interrumpido); **fix S4**: un error de API ya NO se escribe como `questions=[]` (lo marcaba done PARA SIEMPRE, indistinguible del NONE legítimo) → no-write+reintento en el próximo tramo + fail-fast a los 20 errores (clase cuota-s100). Pendiente al cierre de tramos: pasada retry-empties sobre los ~848 `[]` históricos (~$3) + dedup por chunk_id en el build de la tabla (los 1.877 duplicados de origen s99 siguen en el fichero; el consumidor npz ya dedupea).
- **(e) Patrón "seam-a-patch" consolidado:** lever CERRADO ⇒ su código NO viaja a main — `evals/s101_tiebreak_port.patch` y `evals/s102_toc_seam.patch` (autocontenidos, `git apply --check` verificado) + guards fail-fast en los scripts de medición (el env de un seam ausente se ignoraría EN SILENCIO = clase s96-H3; el guard TOC verifica además que el dispatcher consulte el flag — un stub no pasa).
- **Alternativas descartadas**: variante post-rerank con margen de ranking (sin superficie que la justifique: ~1-2 TOCs servidos/run); mantener el seam flag-off en src (código muerto de un NO-GO); demote solo posicional (el LLM re-selecciona el TOC igual — matchea léxico). **Relacionado**: DEC-091 (clase composición-del-pool), DEC-092 (reranker no cede), DEC-094/095 (instrumento), `feedback_my_bias` (S1 = mi framing "delta=solo el lever" refutado por mis propios datos).

## DEC-097 — s102/L4: bloque de SELECCIÓN en generación MEDIDO → NO-GO tal-cual-medido; el mecanismo real de cat021 = composición-servida estocástica × generación-estable-dada-composición; reapertura = FORK (no rumbo pre-decidido)
- **Fecha**: 8 jul 2026 (s102; autor Fable 5, mandato autónomo). **Impacto**: MEDIO (lever de generación medido, zona de dolor). **Dúo completo**: cross-model GPT-5.5 (5 hallazgos, 5 confirmados, 1 CRÍTICO contra mi framing) + sub-agente Fable fresco (7 hallazgos, 7 confirmados). Tally en `adversarial_review_log.jsonl` (2 entradas 8-jul tarde). **Ambos lados RATIFICAN el NO-GO pero tumbaron mi framing dos veces** — las correcciones están baked en `evals/s102_selection_measure.yaml:verdict_s102`.
- **Qué se midió**: bloque de prompt flag-gated `GENERATOR_SELECTION_BLOCK` (consulta de SELECCIÓN sobre familia → enumerar variantes divergentes; complementa TIPO 2; diana=cluster cat021 «¿qué modelo pido?» donde el bot asumió 40/40R). A/B fact-level con pipe pineada (retrieve→rerank top-10 compartida), base ×1 / selection ×2 gens, árbitro dual. Población: cat021 target + sentinels hp009/hp018/cat022/cat019 + cat013 conductual. **MÉTRICA: conveyed fact-level dual sobre LA pipe de hoy = evidencia negativa fuerte, NO settled-absoluto** (estándar DEC-096a).
- **Resultado**: (1) **cat021 base HOY = 4/4** (enumera la familia citando un chunk-catálogo F10) → GO aritméticamente imposible. (2) **hp009 shift conductual INTERMITENTE 1/2**: gen1 = clarify puro (viola el gold s79/s80 family-genérico→responder; disparó en pregunta de PROPIEDAD ignorando su propia cláusula de escape — **los guardrails dentro del prompt no auto-ejecutan**), gen2 = clarify-preámbulo + respuesta completa. Sentinels restantes estables.
- **El mecanismo REAL de cat021 (SA2, corrige mi framing)**: lo estocástico es la **COMPOSICIÓN SERVIDA** (DEC-096b: rerank no-determinista a temp=0); **dada la composición mala del v3, la generación falló ESTABLE** (`stability=stable-miss` ×4 con `in_topk=True` ×4) → el prompt-lever sigue VIVO para la rama composición-mala. **Reapertura honesta = FORK**: si el full v2.2 re-muestra cat021 en miss → replay de SU composición (ahora replayable) → decidir serving-side vs prompt con datos. Mi «sería serving-side, no prompt» era pre-suponer (feedback_my_bias, dirección invertida — cazado por el dúo).
- **Fix de instrumento derivado (SA3, cableado)**: el assessment ahora **persiste `topk_ids`/`served_ids` por gold** — sin ellos una composición-que-falla no es replayable y el fork queda indecidible (le pasó a cat021-v3). Provenance pura, sin bump de versión.
- **Caveats declarados de la medición**: juez primario del A/B = `judge_conveyed` pre-v2.1 (consistente entre brazos; la comparación cruzada con v3 mezcla jueces — SA4); `sel`=OR-de-2-gens sesga PRO-tratamiento (SA5 — refuerza el NO-GO: ni con ventaja rescató); eje conductual NO fue gate pre-declarado (X3 — re-mediciones futuras deben pre-declararlo).
- **Seam-a-patch (patrón DEC-096e)**: `evals/s102_selection_seam.patch` (bloque+parser+_assemble_system+tests, `git apply --check` limpio) + guard fail-fast en `scripts/s102_selection_measure.py`; `src/`+`tests/` a HEAD.
- **Rescatable**: la clase «consulta de selección» como dimensión CONDUCTUAL para golds futuros (a 30+ fabricantes crecerá) — autoría por dimensión-de-fallo desde FUENTE (DEC-025), jamás para justificar el bloque retroactivamente.
- **Alternativas descartadas**: iterar el wording del trigger (no arregla el GO-imposible con base 4/4); estabilización por N-reps (lotería de coste sin cota que mediría varianza de serving, no el prompt); mantener el seam flag-off en src (código muerto de un NO-GO). **Relacionado**: DEC-096 (no-determinismo del rerank + patrón seam-a-patch), DEC-051 (lever de generación previo, métrica PASS), s79/s80 (regla clarify-si-diverge), `feedback_my_bias`.

## DEC-098 — s102/D6: fidelity-block GATE bvg PASADO → SHIP a demo (cambia el veredicto de DEC-051: aquel NO-GO era métrica-PASS pre-NOCAT; a nivel-hecho es +3/0 y el gate PASS-live sale limpio)
- **Fecha**: 8 jul 2026 (s102; ejecución de D6 con OK explícito de Alberto "como propones"). **Impacto**: MEDIO (ship de flag de generación a demo). Protocolo: decisión pre-aprobada por Alberto + gate pre-registrado en D6 — el dúo ya había endurecido el bloque en s69 y la medición fact-level en s101; esta ejecución siguió el patrón DEC-092b sin desviaciones.
- **Evidencia acumulada**: (1) fact-level A/B (s101, árbitro dual): **+3 rescates (hp002·hp006·hp010) − 0 regresiones**, contradicted sin subir. (2) **Gate bvg s102** (`scripts/s102_fidelity_gate.py`, 23 golds × ctrl/treat × K=3, pipe LIVE compartida t10@3500, juez GPT-5.5 canónico reusado): **0 regresiones REALES** — las 3 PASS→PARCIAL del juez (hp004/cat009/cat024) VERIFICADAS leyendo las 6 respuestas de cada una (3 agentes independientes): cores intactos 6/6 en las tres; deltas = línea-caveat (hp004), supplementary 24,1Vdc (cat009), framing de precedencia (cat024) — el patrón artefacto-del-juez de DEC-092b, tercera vez. **+3 gains a PASS (hp020·cat012·cat015) · 0 truncados**. Artefacto: `evals/s102_fidelity_gate.json`.
- **Métrica del veredicto (Protocolo 4)**: fact-level conveyed dual + PASS-live K=3 no-regresión. **DEC-051 ("lever de generación NO-GO, Δ_net=0") era métrica PASS holística pre-NOCAT/pre-ancho** — NO se re-litiga: se re-midió con vara nueva y el veredicto CAMBIA (patrón DEC-092b: la vara importa). Fila del digest sobrescrita in-place.
- **Coste declarado (vigilar en el próximo full v2.2)**: el bloque re-prioriza — densifica lo afirmado-sobre-la-pregunta y DEJA CAER caveats/supplementary periféricos (caveat "verifica la etiqueta" hp004 3/3→0/3; rango 24,1-26Vdc cat009 3/3→0/3). No toca cores. Si el v2.2 muestra pérdida de facts supplementary atribuible al bloque → re-abrir con ese dato.
- **Ship**: `GENERATOR_PROMPT_VARIANT=fidelity` en Railway (paso de Alberto; el código s69 vive en main desde entonces; reversible quitando la variable). El assessment NO pinea este flag en DEMO_FLAGS → al confirmarse el ship, pinearlo "fidelity" para que el próximo full mida la demo real.
- **Relacionado**: DEC-051 (veredicto sustituido), DEC-092b (patrón vara-justa + artefactos-del-juez), DEC-095 (medición fact-level), D6 en `evals/s101_decisiones_alberto.md`.

## DEC-099 — s102: SHIP hyq corpus-wide CONSTRUIDO Y GATEADO (mecánica v2) — pendiente SOLO GO de Alberto para activar

**Decisión.** El canal question-side hyq (piloto GO DEC-095, ship D2 aprobado por Alberto) queda
materializado y VERIFICADO end-to-end: migración 013 (`chunks_v2_hyq` + HNSW propio + RPC
`match_hyq`, aplicada por Alberto) · load 70.134 preguntas (0 poison, count==universo, self-hits
1.0000, `ingest_batch=hyq-v1-37a843f9`) · seam `HYQ_TABLE=on|off` (flag a IMPORT-time: typo =
crash-al-boot, no medio-apagado silencioso) · **mecánica v2** = cuota 10 + barra 0.45 del piloto
+ family-parity a NIVEL FILA (`_hyq_family_rows`, patrón 012) + carve-out del diversify con dedup.
La activación (`HYQ_TABLE=on` en Railway) queda gateada al GO de Alberto (mandato: nunca auto-ship).

**Por qué mecánica v2 (el gate lo exigió, no fue pre-diseño).** El gate de reproducción v1 falló
0/2 con causa MEDIDA: corpus-wide (70k preguntas vs 6.4k del piloto) el espacio-pregunta es
fuerte-en-TEMA y débil-en-PRODUCTO — los padres de la familia diana rankean ~49-53 tras paráfrasis
genéricas de otras marcas, la cuota global compraba slots que `_filter_to_query_models` tira
(n_hyq_in_pool=0 en todas las queries con modelo); y el diversify por-fichero re-litigaba la cuota
con sims incomensurables (hp018 RECALL→DIVERSIFY). Fix 1 = filtro de familia sobre el TEXTO de cada
pregunta ANTES del colapso keep-max (anclaje condicional del generador — fix #2 dúo r2), fallback
a-cero-matches no-peor. Fix 2 = set-aside de `_hyq_surrogate` alrededor del diversify (lógica
interna INTOCADA, consenso s59) con dedup del re-adjunte (ventana id-duplicado, fix #1 dúo r2).

**Evidencia (métricas declaradas).**
- Gate flips (pool-50 same-family CON atribución causal — sin atribución sería false-PASS, fix
  cross-model r1): **2/2** (cat016·autobúsqueda + hp018·6K8, las MISMAS preguntas ganadoras del
  piloto vía tabla) · 0 flips espurios · hp014 control-expectativa estable · `s102_hyq_table_gate.yaml`.
- bvg outcome (K=3, pairing por pool s63-R1 — 6/23 paired delta:=0, juez canónico, fidelity ambos
  brazos): **0 regresiones reales · 4 GAINS PASS (hp001/cat009/hp013/hp007)**. hp020 PASS→PARCIAL
  verificado ARTEFACTO DEL JUEZ por agente independiente elemento-a-elemento (4ª instancia
  DEC-092b) · `s102_hyq_bvg_gate.json` (gate_verdict estampado).
- Negcontrol pool-level (OFF/OFF/ON null-corrected): **ROJO registrado sin edulcorar** — 7
  EXCESS-HIGH en 4 golds (null=0; canal dispara 31/39 vs ~0 del piloto). Mecanismo TRAZADO con
  `_trace`: la fusión corta la cola CRUDA del vector (`results[:40]+cuota`) PRE-model-filter y en
  queries con modelo esa cola es load-bearing post-filtro (cat009: rank crudo 44 = rank 3 final).
  Arbitrado en OUTCOME: cat009 GANA a PASS, cat018/019/021 estables → trade neto-positivo en esta
  población. Si un full futuro muestra daño de esta clase → rediseño de la fusión (cap post-filtro).

**Alternativas descartadas.** Subir cuota/fetch-K (tuning ciego + desplazamiento medido s101) ·
family-filter server-side vía RPC (exigiría migración nueva y pm poco fiable justo donde importa
— ZXe=combinado/unknown; el texto-de-pregunta es la señal diseñada) · re-stamp de sims a 0.72
patrón-supplements (violaría la mecánica medida MUCHO más que el carve-out) · carve-out también en
`_diversify_by_manufacturer` (rama no-modelo = mecánica medida en piloto+negcontrol, sin evidencia
de fallo — asimetría DELIBERADA como disciplina de medición).

**Gaps/deuda declarados.** TECH_DEBT #52 (ventana series/shared-docs · techo top-200 client-side a
escala 30+ · pm=unknown sin adjudicar → workstream identidad DEC-074). Replay exacto del piloto
imposible (el npz medido s101 fue sobrescrito; backup en disco = vintage posterior 7004). Flake
orden-dependiente pre-existente en test_enunciados_multivector:212 (no relacionado).

**Proceso.** Dúo Protocolo 3 ×2 rondas (ALTO/zona-de-dolor, cross-model INNEGOCIABLE): r1
cross-model 5/5 (2 críticos: typo-flag silencioso → import-time; false-PASS sin atribución) +
sub-agente 9 (8 conf/1 FP; ef_search<match_count; 404-bisección; paginación-1000 verificada EN
VIVO). r2 cross-model 5 (4 conf/1 refutado) + sub-agente 8/8 (id-duplicado; keep-max-antes-del-
filtro). Tally completo en `adversarial_review_log.jsonl` (2026-07-09 ×4). 10 tests nuevos del
canal (`tests/test_hyq_channel.py`), suite 462 verdes.

**Ship-step restante.** GO Alberto → `HYQ_TABLE=on` en Railway → smoke post-activación (Protocolo
1: verificar stamps `_hyq` en una query real con modelo antes de declarar shipped) → full v2.2
(estrena H4 + provenance + fidelity + hyq) → nueva fila del scoreboard. Rollback trivial: quitar
la env var (flag-off = prod inerte); tabla/RPC con rollback declarado en 013.

## DEC-100 — s103: lever displacement-landing (eviction VECTOR post-diversify) MEDIDO → NO-GO por gate pre-declarado; el landing correcto es FAMILY-AWARE → primer consumo medible del entity-linking (DEC-074)

**Decisión.** El rediseño del carve-out hyq (diversify a top_k COMPLETO + eviction por
posición-de-cola de `_channel=='VECTOR'` con exclusiones `_hyq_boosted`/`_swapped_from_surrogate`
+ contrato sole-representative + fallback trim-del-aside) se cableó, se midió judge-free con A/B
same-day (old@29695cf vía git worktree vs fix working-tree, misma DB, config-stamped) y **FALLA el
gate pre-declarado en 3 puntos → REVERTIDO por pre-registro**. Seam reproducible:
`evals/s103_displacement_seam.patch`; diseño+veredicto: `evals/s103_displacement_landing_design.md`;
artefactos: `s103_displacement_probe_{old,old_b,fix}.json` · `s103_displacement_gate.json` ·
`s103_displacement_null.json` · `s103_hyq_{negcontrol,table_gate}_fixarm.yaml` ·
`s103_transition_matrix.json` (matriz v3→v2.2 reconstruida de git, 10 perdidos/12 ganados).

**Resultado medido (lo que el NO-GO compra).**
- El mecanismo FUNCIONA para su clase diana: cat022 recupera **3/3 chunks** desplazados
  (MNDT723 p58/p10, MNDT722 p14) y la transición de anclaje corpus-amplia es +1/−0 (109 facts,
  null 0/0). La clase "stamps load-bearing desplazados" es REAL y recuperable.
- PERO: (a) **rompe el flip shippeado hp018·6K8** (gate de aceptación DEC-099): en pools
  protected-heavy el trim recorta el surrogate load-bearing por 3 milésimas de sim-pregunta
  (0.454 vs 0.457 — la sim-pregunta no discrimina valor); (b) **hp011 fuera del null** (3
  served-v2.2 evictados; null 0/0); (c) **negcontrol EXCESS-HIGH SUBE 7→9** (posición-de-
  interleave ≠ rank OFF: la eviction de "cola" desplaza top-25); (d) hp018 p21 NO recuperable
  por diseño (ES cola vectorial = el precio medido del canal).

**Lección estructural.** Los 50 slots los paga alguien SIEMPRE. Los 4 ejes observables — canal,
score (incomensurable, dúo r1), sim-pregunta (6K8), posición de interleave (negcontrol) — son
TODOS ciegos al valor. El discriminador restante es **FAMILIA/identidad**: la cola que v2.1
protegió en hp018 era junk cross-family (MIE-MI-310 para pregunta ZXe) y la que el carve-out
viejo desplaza en cat022 es gold same-family (MNDT72x). **El landing family-aware queda como
HIPÓTESIS A GATEAR dentro del workstream entity-linking (DEC-074/§3 del plan s103) — su primer
consumo medible.** No se itera el landing por otro eje ciego (sería tuning; G4 declarado).

**Alternativas descartadas (medidas o razonadas en el diseño v2.1).** A1 quitar carve-out (anula
el canal, s102) · A2 crecer pool (contradice competencia-de-slots medida) · A3 tocar el diversify
(consenso s59 ×2) · A4 eviction por score (escalas incomensurables + arrasa canal en oversize,
CRÍTICO r1) · A5 cola global (empates de stamp evictan mejor-rankeados) · iterar v3 con otro eje
observable-ciego (los 4 están agotados por medición).

**Proceso (dúo Protocolo 3, MEDIO-en-zona-de-dolor → cross-model INNEGOCIABLE).** 2 rondas × 2
lados, agentes frescos: r1 sub-agente 7 findings (1 CRÍTICO: early-returns sin truncar + merge
stamps sin cap → eviction v1 arrasaría el canal) + cross-model 6/6 (escalas incomensurables:
`_enunciados_swap` propaga sim+`_channel` :1331, boost sobrescribe :999); r2 convergente ×2 en
sobre-claim "G1-safe" y gate ciego al trim + **el cross-model corrigió la cita errónea `:2456`
que AMBOS sub-agentes Claude repitieron** (mismo-árbol = mismo blind spot — validación en vivo de
la regla de Alberto s102). Tally: 14+ findings, 0 falsos positivos (`adversarial_review_log.jsonl`
2026-07-09 ×2 s103). El gate amplio (negcontrol+flips+null) cazó lo que los 6 diana no podían —
el guardarraíl anti-overfit G4 funcionó por diseño.

## DEC-101 — s103b: landing v3.1 = EXTENSIÓN ACOTADA del aside (re-apertura MEDIDA de la A2 de DEC-100) + bloque de selección CODE-GATED (fork DEC-097 ejecutado) — CANDIDATO DE SHIP gateado, pendiente GO de Alberto

**Decisión.** El landing del coste de la cuota hyq se resuelve QUITANDO el segundo cobro: el
carve-out deja de reservar slots del diversify y el aside viaja como **extensión acotada** del
pool (`≤ top_k + HYQ_PILOT_QUOTA`), post-`[:top_k]`, patrón identity-fetch, cinturón idioma
estricto, traza `post_hyq_aside`. La regresión que ESTA composición causa (cat021: el rerank-60
sirve el user-guide EN del 40/40R y la generación ASUME la variante) se cura con el **bloque de
selección s102 con trigger EN CÓDIGO** (`_SELECTION_INTENT` + `_assemble_system(query)`,
`GENERATOR_SELECTION_BLOCK`, default off). Diseño+código validados por dúo (2 rondas diseño + 1
ronda diff, ×2 lados; ~50 findings confirmados hoy, ~1 FP). **Ship = merge + Railway
`GENERATOR_SELECTION_BLOCK=on`** (la landing activa sola con HYQ_TABLE on — F5: sin el env var,
prod quedaría +cat022/−cat021; el deploy DEBE llevar ambos). Rollbacks separados: selection =
flag; landing = revert de código (o HYQ_TABLE=off, que mata el canal entero).

**Evidencia (misma DB, mismo día, artefactos evals/s103_*).**
- Judge-free: diana cat022 3/3 + hp018·p21 (4/4, lo que v2.1 no podía) · anclajes 39-golds
  +1/−0 (null 0/0) · served-v2.2 containment 0-missing (hp011=0 vs 3 en v2.1) · negcontrol
  EXCESS 6 ≤ 7 (mejor que el shipped) · flips 2/2 · churn-servido anclas-OK LOSS 0/GAIN +1 ·
  suite 473 (12 tests nuevos).
- Outcome (bvg K=3, 23 golds, ctrl=pools-old-dump vs treat=v3.1-live): **+cat022 FALLO→PASS**;
  cat024 = artefacto del juez (5ª instancia DEC-092b, K-votos {F,P,PASS} sobre respuestas casi
  idénticas y MEJOR ordenadas); **cat021 PASS→FALLO 3/3 REAL** → curado por el bloque
  (PASS/PARCIAL/PASS bajo config de ship — target flaky declarado s102, residual PARCIAL en el
  mapa); hp009 ATRIBUIDO (probe 2 brazos): PARCIAL=PARCIAL, conducta baseline K-INESTABLE, no
  v3.1. Latencia rerank mediana 2.18→2.55s (+17%, input 50→≤60).
- Selection code-gated: sweep 39 dev = SOLO cat021 dispara; fraseo negativo de técnico real
  («¿cuál pongo?» jumpers/resistencias — cazado EJECUTANDO por el sub-agente) en tests; hp009 y
  toda spec/avería byte-idénticas POR CONSTRUCCIÓN (unit tests, $0).

**Desviaciones de proceso, DECLARADAS (cross-model diff-review, 2 CRÍTICOS de proceso).** El D1
pre-declarado se corrió con instrumento de contraste INVÁLIDO (v1: medía la PRESENCIA del canal
ya shippeado y penalizaba el flip cat016; artefacto NO-PASA conservado sin editar); el v2
corrigió el contraste (old-vs-v3) y REFINÓ la métrica a anclas-OK-en-servido = cambio de métrica
post-declaración, visible en el ADDENDUM del diseño. El bvg corrió tras el v2. Fix de instrumento
colateral: `_stage_of` del diagnose clasificaba por primera-desaparición y el pipeline ya no es
monotónico (aside/fetch re-adjuntan post-lang) → `final` se comprueba primero (idéntico para
trazas monotónicas; el 0/2 del table-gate era ese artefacto — con el fix, 2/2). bvg_kmajority:
flag nuevo en equivalence-dict + manifest (freeze DEC-023).

**Alternativas descartadas (medidas).** v2.1 eviction (DEC-100 NO-GO) · cascada family-aware
(artefacto `s103_family_tier_probe.json`: 0 cross-family positivos con lista RESUELTA en TODOS
los golds clave → degenera a v2.1; queda como hygiene en DEC-074) · seam prompt-gated tal-cual
(cura cat021 3/3 pero hp009 2/3 clarify; iteración de wording lo EMPEORA 3/3 → los guardrails
de prompt no auto-ejecutan, 2ª medición) · top-100 (probe: 3/11 entran a ranks 55-91, 5 ni a
100 = gap vocabulario; coste medido del ancho en rerank s98 + ef_search=120 < eff_k 200).

**Gaps declarados.** cat021 sigue siendo target flaky (composición-sensible; residual PARCIAL);
el bucket in-pool del assessment gana +10 mecánico donde el canal dispara (caveat a estampar en
la fila v3 del scoreboard); fallback-truncate del rerank mata el aside (paridad con extras del
fetch, cambio en failure-path declarado); ⚠ ANTI-OVERFIT: misma población dev — contrapesos:
negcontrol 39 + null + anclas amplias + flips + sweep negativo del regex.

## DEC-102 — s104: R2 corpus-wide EJECUTADO HASTA SU GATE — generación Haiku GO (G0 medido) + activo corpus-adyacente pagado y a salvo; carga a escala NO-GO (crowding del canal sin cuota) → rollback verificado; el fix = cuota del canal enunciados (diseño siguiente, dúo + gate propio)

**Decisión/estado.** Con GO explícito de Alberto (presupuesto + modelo barato si no pierde
calidad): (1) **pipeline reconstruido seguro** — generar→dump→loader-A3 (el dúo cazó CRÍTICO:
el pase legacy insertaba en `chunks_v2`, el índice compartido del NO-GO DEC-088) + 9 fixes
verificados (temp-kw haiku-4-5, sha-map exacto con desambiguación por ancla-DB [5 colisiones
reales], vintage, guard pm-unknown, tope de gasto, chaff/meta contados, cinturón por-doc,
ledger con pre-seed T1 y reconciliación). (2) **G0 equivalencia MEDIDO: Haiku 4.5 GO**
(QA-pass 0.879 > Sonnet 0.861; útiles/item 0.98; hechos-tabla 0.94; banda cobertura NO-PASA
con diagnóstico = concentrado 2 docs + Sonnet-solo 0.799 → enmienda declarada; panel 40 pares
leído: paridad de atribución Y cazó meta-líneas DE SONNET pasando el QA → filtro nuevo).
Coste 4x menor ($0.86 vs $3.49 los brazos). (3) **T2 generado 81/81** (45.889 enunciados
QA-passed, ~$9.7; ambiguo HLSI-MN-103 resuelto por ancla-DB). (4) **Carga T2+G0H (49.207 →
tabla a 71K) → GATE T2 DISPARÓ: NO-GO a escala** — 0 ganancias de ancla en 39 pools (STOP
pre-declarado) + 2 anclas OK perdidas (hp005#2, hp006#2/ISO-X) + served-churn ×3 + 8 golds con
menos surrogates hyq. Mecanismo DIAGNOSTICADO: crowding interno (keep-max dedup + cap de
fusión desplazan cola vectorial sin aportar valor; cat021 inundado por docs 40-40 incl. el
guide EN de s103b). El sort-mixto SIN CUOTA (bien a 22K, DEC-089) no aguanta 71K = la clase
que hyq resolvió con fusión-por-cuota. (5) **Rollback DELETE-por-batch + VACUUM PG-directo →
restauración VERIFICADA probe 0/0** (pools = T1 exacto). Tail (~900 docs, ~$95) NO gastado.

**Activo pagado y a salvo** (mandato no-gastar-dos-veces CUMPLIDO): dumps locales con 54.849
enunciados Haiku QA-passed (T2+G0+SMOKE) + 21.995 T1 en prod. Re-carga post-fix ≈ $1.
Ledger+manifests committeados; coste R2 total ≈ $14.

**Siguiente (cabeza de cola):** diseño de la CUOTA del canal enunciados (espejo del patrón hyq
DEC-099: presupuesto propio en la fusión + barra; opciones: cuota fija de swapped-parents ·
cap por-doc en colapso · barra escalada) — dúo obligatorio (retrieval) + gate de re-carga =
el probe pre/post ya committeado (artefactos pre_t2/post_t2 = referencia del modo de fallo).

**Proceso.** Dúo R2 r1: cross-model 5/5 (CRÍTICO índice compartido) + sub-agente 13 (3 bugs
de código ejecutados/verificados). Los gates pagaron DOS veces en un día (T2 aquí; el bvg en
DEC-101) — el sistema de pre-registro + STOP funciona. Colaterales: ledger dañado por OneDrive
en la desconexión → restaurado del snapshot (el backup pre-declarado pagó); cuota OpenAI
agotada mid-run → recarga de Alberto; assessment v3 estampado (fila scoreboard, DEC-101 medido:
OK 93/73%, retrieval 12→7, lista diana completa convertida).

## DEC-103 — s194: planificador descompuesto sobre cohorte fresca → NO-GO en construcción del gold; selector y targets no se abren

**Decisión.** El siguiente tramo del bucket dominante (12 `synthesis-miss`) conserva la señal
causal de S193 — selección de IDs separada de compilación determinista — pero sustituye el
selector plano por descomposición explícita de subobligaciones sobre `EvidenceUnitV2`. S168/S170
no pueden decidir el gate porque ya fueron observados: la población decisiva debe ser documentalmente
fresca. Se selló un packet GET-only de `chunks_v2` (25.090 filas; 14 documentos/fabricantes;
7 tabla + 7 prosa; cero overlap versionado) y un manifest pre-autor de IDs, spans y hashes.

**Resultado y STOP.** Haiku económico completó 14/14 llamadas por **$0,078186**. La población
material era suficiente — 13 elegibles, 7 tabla, 6 prosa, 50 puntos — pero una salida
(`s194_src_09`) violó la cardinalidad de soporte. El preregistro exigía cero inválidos:
`NO_GO_COHORT_CONSTRUCTION`. Por diseño no se llamó a `gpt-5.6-luna`, no se abrió target,
no hubo retry ni cambio de umbral y se mueven **0 facts**. Este NO-GO no refuta la hipótesis del
planificador: la detuvo antes de medirla.

**Causa del instrumento.** El prompt y el validador exigían uno a tres IDs por punto, pero el
JSON Schema heredado de S168 solo declaraba un array. El proveedor pudo emitir una forma
estructuralmente válida que el validador rechazó después. Una nueva iteración solo es legítima
con `minItems=1`, `maxItems=3`, `uniqueItems=true` sellados **antes** de otra cohorte fresca; queda
prohibido repetir S194 o reutilizar sus outputs. Los umbrales downstream se mantienen: recall
≥90%, precisión ≥80%, preguntas completas ≥75%, exactitud y determinismo, cero regresiones de
obligaciones cubiertas y cero conflictos nuevos detectados por los contratos versionados.

**Revisión adversarial.** Dos rondas GPT-5.5 de diseño/código (10/10 hallazgos confirmados, 0 FP)
forzaron: cohorte realmente fresca; revalidación semántica además de prefijo byte-idéntico;
manifest de unidades; estado HOLD auditable; framing `NOT_MEASURED` para overlap semántico; y
validación explícita de conflictos. `chunks_v3` permanece en el resultado como brazo
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`, sin rematerialización ni parches por pregunta.

**Frontera.** No hay seam runtime nuevo, producción, migración, escritura DB o deploy. S172 y
S188 continúan como candidatos locales/default-off pendientes de generalización independiente.
Railway es demo y no bloquea PR/merge con CI verde. Artefactos: `evals/s194_*`,
`scripts/s194_*`, `tests/test_s194_*`.

## DEC-104 — s195: cardinalidad limpia mediante slots, pero el schema dinámico excede el compilador de Haiku

**Decisión.** S195 no reintenta S194. Se separa el contrato canónico (`support_unit_ids` de
1–3 únicos) del transporte Anthropic, porque su dialecto de structured outputs solo admite
`minItems` 0/1 y no compila `maxItems`/`uniqueItems`. El transporte usa cuatro slots de puntos y
tres de soporte, IDs enumerados por excerpt, normalización determinista y un validador económico
cross-provider Luna sobre los 14 ítems. Sol 5.6 xhigh fue el revisor principal; Fable 5 quedó
históricamente rotulado `omitted_unavailable` por ausencia del ejecutor versionado en ese
worktree, sin recibo fingido; DEC-106 corrige que eso no probaba indisponibilidad del modelo.

**Frescura y contrato.** Packet nuevo GET-only de `chunks_v2`: 25.090 filas, 14 documentos y
fabricantes, 7 tabla + 7 prosa, cero overlap previo/S194/target/product-pair y cero equivalencia
exacta de contenido/extracción. Se resolvieron 76 UUIDs target a 668 filas y se excluyeron 2.848
filas equivalentes. El runner fija modelos, gates, presupuestos, artefactos y límites; usa locks
exclusivos, `max_retries=0`, `store=False` en Luna y NO-GO con diagnóstico saneado para 400.

**Resultado y STOP.** Los 14 token-count preflights Haiku pasaron. La primera inferencia fue
rechazada antes de producir output: HTTP 400, request ID versionado, `Schema is too complex for
compilation`. El checkpoint registra `completed_calls=0`; Luna, planner y targets no se abrieron.
Estado `NO_GO_EXECUTION_CONTRACT_REJECTED`, facts movidos 0 y ningún crédito oficial/productivo.
No se reutiliza el packet ni se relaja ningún gate. El planner descompuesto sigue `NOT_MEASURED`.

**Siguiente trigger legítimo.** Probar primero un schema estático mínimo con un canary sintético
separado. Debe conservar slots para máximos, retirar enums dinámicos/`$defs` y dejar pertenencia y
unicidad de IDs al validador determinista. Solo tras una compilación real satisfactoria se congela
otra cohorte fresca excluyendo S194+S195; luego Haiku→Luna y, si todo upstream pasa, planner
downstream con 90/80/75 intactos. `chunks_v3` conserva
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` sobre sus métricas de ranking; Railway no es gate de PR/merge.

## DEC-105 — s196: el transporte rectangular estático compila; GO solo para una cohorte S197 nueva

**Decisión.** S196 ejecuta antes de otra cohorte el canary sintético exigido por DEC-104. El schema
Anthropic es idéntico para cualquier futura fuente: cuatro objetos de punto, tres strings de soporte
por punto y sentinel vacío; cero arrays, `$ref`/`$defs`, combinators, enums o consts. Identidad,
facets, cardinalidad 1–3, pertenencia, unicidad, contigüidad e inactividad se validan en código.

**Control.** Fixture inventado de dos unidades, sin documentos/chunks/targets. Lock exclusivo
workspace-local antes de cualquier request, checkpoint inmutable pre-pago, finalización atómica,
SDK Anthropic 0.97.0 verificado, `max_retries=0`, máximo 1 preflight + 1 inferencia y $0,02. Sol 5.6
xhigh fue revisor principal en tres rondas (12/12 hallazgos confirmados y corregidos); Fable 5 quedó
registrado como `omitted_unavailable` por ausencia del ejecutor en aquel worktree, sin sustituto
fingido. El pre-S197 corrige después el diagnóstico: no probaba indisponibilidad del modelo.

**Resultado.** `GO_STATIC_TRANSPORT_COMPILED`: Haiku aceptó el schema, terminó `end_turn` y el
adaptador reconstruyó dos puntos canónicos con IDs E001/E002 conocidos. 1 inferencia completada,
coste $0,002583, cero retry, documentos reales, Luna/planner/targets, producción o crédito de facts.
La causa de S195 queda acotada a su complejidad dinámica; los slots estáticos no son el bloqueo.

**Siguiente trigger.** Abrir un S197 separado con source freeze nuevo que excluya S194+S195, reuse
el schema S196 sin especializarlo por documento y pase Haiku→validador económico Luna para todos
los ítems. Solo un GO upstream autoriza medir después el planner 90/80/75. `chunks_v3` sigue
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` por referencia canónica, sin copiar sus métricas. Railway no es
gate de PR/merge.

## DEC-106 — pre-S197: dúo reproducible recuperado y gate real sellado; ejecutar upstream antes del planner

**Decisión.** Versionar el acceso directo al pin `claude-fable-5` y ligar Sol 5.6 xhigh + Fable
a una única vista Git inmutable, con artefactos físicos y estados de fallo auditables. La causa de
los anteriores `omitted_unavailable` era que el executor usado desde Codex estaba sin trackear en
otro workspace; no era evidencia de indisponibilidad global. El cierre revalida artefactos de
ambos proveedores, deriva uso/tools del trace, rechaza symlinks y cambios concurrentes y conserva
traces también en fallos.

**Resultado de revisión.** Sol principal completó la revisión y sus cuatro hallazgos medios se
corrigieron con tests. Dos llamadas independientes al pin exacto Fable 5 llegaron al proveedor,
leyeron el repo y cerraron `end_turn` con bloque de texto vacío; el runner las rechazó y preservó
traces/coste. El estado correcto es `failed_api`/pendiente, nunca `omitted_unavailable` ni dúo
completo. Por instrucción explícita de Alberto de evitar una convergencia indefinida, no se hace
un tercer intento ni se convierte este fallo externo en gate de merge con CI verde.

**Siguiente tramo.** Tras integrar esta preparación, ejecutar una sola cohorte S197 fresca,
disjunta de S194+S195: doble scan GET-only de `chunks_v2`, schema estático S196 con Haiku y
screening excerpt-internal de los 14 ítems con Luna. Un NO-GO se detiene upstream; un GO sólo
autoriza preregistrar S198 con 90/80/75. No mueve facts por sí mismo, no abre targets, no integra
runtime y no reabre `chunks_v3`, que continúa `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`. Railway es demo
y no bloquea PR/merge con CI verde.

## DEC-107 — S197: el transporte estático generaliza; NO-GO semántico antes del planner

**Ejecución sellada.** Una única cohorte nueva excluyó S194+S195 mediante dos scans GET-only
idénticos de 25.090 filas: 14 documentos, fabricantes y preguntas elegibles; 7 tabla + 7 prosa;
42 puntos; cero overlap prohibido y cero escrituras. Haiku 4.5 completó 14/14 con el schema
estático S196 y **0 outputs inválidos**. Esto cierra la deuda de compilación/transporte como causa
del STOP actual, no como calidad suficiente del autor.

**Resultado.** Luna 5.6 revisó 14/14 con 0 outputs inválidos. Doce ítems fallaron al menos un gate:
8 point-sets eran incompletos para el alcance de su pregunta, 5 incluían un punto no plenamente
soportado o irrelevante para lo preguntado y 6 tenían un facet incorrecto. Estado
`NO_GO_COHORT_CONSTRUCTION`; coste Haiku $0,091605 + Luna $0,063155 = **$0,15476**. Facts 0,
planner/targets cerrados, DB/runtime/producción intactos. No se reintenta, repara ni reevalúa S197.

**Lectura causal y siguiente trigger.** El bucket de fallo mayor es cierre pregunta↔point-set, no
schema ni planner. La siguiente hipótesis estructural invierte la dependencia: seleccionar primero
2–4 obligaciones ligadas a unidades fuente, validar claim/support/facet con definiciones genéricas,
y sólo después redactar una pregunta española cuyo alcance sea exactamente ese conjunto. Se debe
congelar antes de seleccionar una cohorte enteramente nueva que excluya S194+S195+S197; cero reglas
por fabricante, producto o pregunta observada. Sólo cero incompletos/unsupported/facet-error abre
el planner 90/80/75. `chunks_v3` sigue `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no es gate.

## DEC-108 — S198: paquete point-first corregido y schema question-only compilado

**Decisión.** La siguiente unidad ya no hace que un mismo autor invente primero una pregunta
potencialmente abierta y después intente comprimir su respuesta. S198 selecciona 2–4 obligaciones
atómicas ligadas a unidades, las somete a un screen independiente de support/facet/materialidad,
y sólo entonces permite que otro Haiku redacte una pregunta limitada al conjunto aceptado; una
segunda pantalla comprueba el cierre bidireccional. Es calificación del paquete completo, no
aislamiento causal de una pieza. La elegibilidad y la precedencia exhaustiva de ocho facets se
congelan antes de observar otra fuente; S197 sólo aporta conteos agregados, nunca reglas o ejemplos
por ítem.

**Revisión frontera sin convergencia abierta.** Sol 5.6 xhigh principal produjo seis hallazgos y
Fable 5 exacto completó independientemente con cinco; 11/11 se confirmaron y corrigieron en una
única adjudicación. El contrato deja de llamar “prueba/falsación” a un único juicio Luna no
calibrado, contabiliza el agotamiento de población fresca, declara el posible context starvation
del question-writer y congela SDKs, modelos, tokens, requests y precios. No se abrió otra ronda.

**Canary y resultado.** Antes de seleccionar documentos reales se ejecutó una sola llamada Haiku
sobre dos claims 100% sintéticos con el schema estático mínimo `{item_id, question}`: cero arrays,
refs/defs, combinators, enums o consts. Anthropic 0.97.0 lo compiló y devolvió una salida válida;
estado `GO_QUESTION_SCHEMA_CANARY_COMPILED`, 1/1 inferencias, cero retry, coste **$0,000686** y
hashes de resultado/receipt verificados. El canary no mide calidad semántica y mueve **0 facts**.

**Siguiente trigger.** Desde `main` limpio, construir mediante doble scan GET-only un packet de
14 documentos/fabricantes, 7 tabla + 7 prosa, excluyendo S194+S195+S197 y targets protegidos, y
reportar también el inventario/reserva elegible restante. Ejecutar una sola vez el paquete
point-first; sólo cero fallos upstream autoriza el planner 90/80/75. `chunks_v3` permanece
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway es demo y no bloquea PR/merge con CI verde.

## DEC-109 — S198: población fresca agotada y STOP estructural antes de Luna

**Construcción.** El primer contrato 7 tabla + 7 prosa se detuvo sin packet ni modelos porque,
tras excluir S194+S195+S197, sólo quedaban cinco fabricantes de prosa compatibles con los siete
fabricantes de tabla ya elegidos. Un bug mecánico posterior omitió `kind=chunk` en el filtro nuevo;
se selló, corrigió y probó sin crear packet ni llamar modelos. El intento definitivo conservó los
mínimos semánticos pero usó 12 fabricantes/documentos nuevos: 7 tabla + 5 prosa. Doble scan
GET-only idéntico de 25.090 filas, cero overlap histórico/target y cero escrituras. La reserva
versionada cuenta documentos restantes, no se presenta como otra cohorte manufacturer-disjoint.

**Resultado.** Haiku point-first completó 12/12 respuestas estructuralmente válidas, 0 inválidas,
10 ítems elegibles y 37 puntos. Dos fuentes fueron declaradas ineligibles; su corrección
semántica no se adjudica porque el gate poblacional detuvo el screen independiente. Al ser el
packet exactamente del mínimo 12, fallaron `eligible_items_gte_12`,
`eligible_manufacturers_gte_12` y `prose_items_gte_5`. Estado
`NO_GO_POINT_PLAN_STRUCTURAL_GATE`, coste **$0,070886**. Por el STOP upstream: Luna 0,
question-writer 0, question-screen 0, planner/targets 0 y facts 0. La calidad semántica point-first
y el cierre pregunta↔puntos siguen `NOT_MEASURED`; no se postseleccionan los diez elegibles.

**Siguiente trigger legítimo.** Recuperar el margen original de 14→mínimo 12 mediante otra
cohorte de documentos, source-files y pares fabricante/producto totalmente nuevos, manteniendo
14 fabricantes distintos dentro de esa cohorte pero permitiendo fabricantes ya vistos en
cohortes históricas. Es la única relajación: prompts, schemas, facets, zero-failure screens y
umbrales no cambian; sólo se pueden usar los conteos agregados, nunca los dos ítems observados.
`chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no es gate.

## DEC-110 — S199: margen 14→12 restaurado, pero la elegibilidad sigue bloqueando antes del screen

**Población.** Tras S198 sólo quedaban 13 fabricantes con documentos nuevos. S199 congeló el
máximo real sin usar outputs semánticos: 14 documentos/source-files/pares nuevos, 7 tabla + 7
prosa, 13 fabricantes y una repetición cross-stratum. Doble scan GET-only idéntico de 25.090
filas, cero overlap histórico/target y cero escrituras. El motor semántico S198 se reutilizó sin
cambiar prompts, schemas, facets o screens mediante un adaptador de evaluación, no un seam runtime.

**Resultado y STOP.** Haiku completó 14/14 outputs, 0 inválidos, 9 elegibles de 9 fabricantes,
4 tabla + 5 prosa y 34 puntos por **$0,083863**. Fallaron `eligible_items_gte_12`,
`eligible_manufacturers_gte_12` y `table_items_gte_5`; estado
`NO_GO_POINT_PLAN_STRUCTURAL_GATE`. Luna, writer, scope-screen, planner y targets recibieron cero
llamadas. No se usan identidades, claims, facets o issues observados y no se repara/postselecciona
el cohorte. El mecanismo semántico continúa `NOT_MEASURED`, no falsificado.

**Último trigger de esta línea.** La reserva totalmente nueva tiene 647 documentos pero sólo 10
fabricantes, por lo que el gate anterior de 12 fabricantes ya es imposible. Se autoriza una única
generalización final basada sólo en conteos agregados: 24 fuentes balanceadas (12 tabla + 12
prosa) sobre esos 10 fabricantes, motor S198 intacto y mínimos 12 ítems, 8 fabricantes, 5+5,
24 puntos y cero inválidos/fallos semánticos. Si la fuente o el upstream vuelven a fallar, se
cierra la línea point-first sin otro ajuste poblacional y se vuelve a otro mecanismo. No hay
nueva convergencia frontera. `chunks_v3` sigue `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no es gate.

## DEC-111 — S200: el holdout final no alcanza población y cierra la línea point-first

**Último holdout.** S200 consumió el trigger final de DEC-110: 24 documentos/source-files/pares
totalmente nuevos, 12 tabla + 12 prosa, balanceados sobre los 10 fabricantes restantes. El packet
se selló tras doble scan GET-only idéntico de 25.090 filas, cero overlap y cero escrituras. Se
reutilizó literalmente el motor semántico S198; sólo cambiaron namespace, límites de llamadas y
el mínimo poblacional predeclarado de 8 fabricantes. No hubo nueva revisión frontera.

**Resultado.** Haiku completó 24/24 outputs, 0 inválidos, 11 elegibles de 7 fabricantes,
6 tabla + 5 prosa y 40 puntos por **$0,144517**. Pasaron estratos, puntos y transporte; fallaron
los mínimos 12 ítems y 8 fabricantes. Estado `NO_GO_POINT_PLAN_STRUCTURAL_GATE`; Luna, writer,
scope-screen, planner y targets recibieron 0 llamadas. La key heredada
`eligible_manufacturers_gte_12` tiene label obsoleto, pero compara correctamente contra el valor
8 del preregistro. No cambia el veredicto.

**Cierre.** La línea de generalización source-first queda cerrada: cero cohortes sucesoras, cero
postselección y cero reparación desde identidades/issues S200. El paquete semántico no fue medido
ni falsificado; lo que no generaliza es la construcción de preguntas multi-obligación desde
chunks arbitrarios con densidad suficiente. Siguiente: limpiar el puente local/default-off con
generalización independiente S188 y después S172, declarando que eso no sube el 143 diagnóstico
que ya las presupone; luego volver a los 12 synthesis-miss con un mecanismo de preguntas reales,
no otro cohorte source-first. `chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no bloquea.

## DEC-112 — pre-S201: preguntas reales, gold dual y target evaluator autocontenido

**Cambio de mecanismo.** La auditoría de artefactos cerró dos desvíos antes de ejecutar modelos:
generalizar de nuevo S188 repetiría el NO-GO independiente S127 o reabriría S128 sin trigger, y
S172 ya agotó sus 46 candidatos mecánicos en los mismos 11 documentos evaluados. Pre-S201 vuelve
por ello al bucket dominante de 12 `synthesis-miss` sin otra autoría source-first. Congela 12
preguntas benchmark preexistentes mediante selección hash que no consulta respuesta, clase,
`reaches_gen` ni outputs: 8 fabricantes, 12 productos y 43 facts, incluidos hard cases con soporte
parcial o potencialmente nulo.

**Gate.** Haiku económico propone support-unit sets para todos los facts y Luna económico valida
independientemente cada decisión soportado/no soportado y hasta tres conjuntos semánticamente
equivalentes. Cualquier output inválido o desacuerdo detiene antes del planner. Terra `low` nunca ve
claims, gold, clases ni respuestas; se mantiene el contrato 90% recall / 80% precisión / 75%
completitud, máximo 70 unidades, compilación local exacta y `max_retries=0`. Solo un PASS abre el
packet autocontenido de `cat018`, `hp002`, `hp011` y `hp017`, que ya congela chunks atestados,
baselines, 20 obligaciones y un conflicto. El target no puede pasar con ganancia cero: exige al
menos un residual nuevo, cero regresiones y cero conflictos nuevos.

**Revisión y autorización.** GPT-5.6 Sol `xhigh` principal encontró seis hallazgos (dos críticos,
cuatro medios); 6/6 se confirmaron y corrigieron sin relajar umbrales. Fable 5 exacto llegó al
proveedor, usó siete tools y devolvió una revisión final vacía; el trace se conserva como
`failed_api`, no `omitted_unavailable`, y no se repite. El contrato queda congelado antes de pago:
máximo 40 llamadas económicas, $4 interno, cero DB/runtime/producción/deploy. La ejecución es el
siguiente tramo; hoy mueve 0 facts. `chunks_v3` permanece
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no es gate de PR/merge con CI verde.

## DEC-113 — S201 HOLD sin retry; S202 separa gold real de planner

**Cierre causal de S201.** La ejecución se detuvo en el primer preflight `count_tokens` de
Anthropic, antes de cualquier inferencia completada. El schema de autor había reintroducido arrays
con `minItems`/`maxItems`, dialecto que S195-S196 ya había demostrado incompatible. No hay receipt
de inferencia, Luna/Terra/targets recibieron 0 llamadas y el coste de inferencia conocido es $0. La
cohorte de 12 preguntas queda cerrada: no se corrige y reintenta el mismo holdout.

**Sucesor fresco y más estrecho.** S202 excluye todas las preguntas S201, los cuatro targets y los
dos candidatos default-off. La selección hash sigue sin usar textos de facts, clases, `reaches_gen`
ni outputs y congela 12 preguntas, 5 fabricantes, 12 productos y 43 facts. Cinco fabricantes es el
máximo restante tras las exclusiones, no un umbral relajado a partir de resultados.

**Generalización limpia del transporte.** El contrato reutilizable
`src/rag/source_unit_gold.py` presenta a Anthropic un rectángulo estático 6×6 sin arrays, valores
dinámicos, refs/defs ni combinators. El validador local impone identidad, orden, cardinalidad,
pertenencia, contigüidad, duplicados e inactividad. El schema exacto pasó `count_tokens` con 0
inferencias/retries y $0. Haiku autoriza y Luna valida independientemente; el gold requiere 0
outputs inválidos, 0 desacuerdos y ≥36/43 facts soportados.

**Frontera.** S202 no ejecuta planner ni targets y no puede mover facts. Un GO solo autoriza otro
freeze para Terra; un fallo cierra la cohorte sin retry. Una integración futura sigue requiriendo
revisión principal GPT-5.6 Sol `xhigh`, Fable 5 independiente sin bucle de convergencia y regresión
completa. `chunks_v3` permanece `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no bloquea merge con CI
verde.

## DEC-114 — S202: transporte resuelto, contrato dual-gold inválido y reserva Kidde

**Resultado.** Haiku completó 12/12 outputs válidos sobre 43 facts; el rectángulo estático 6×6
resuelve la causa S201. Luna hizo 12/12 llamadas, pero 7 outputs incumplieron validación: seis
declararon acuerdo sin repetir el set exacto del autor y uno usó un unit ID desconocido. Estado
`NO_GO_DUAL_GOLD`, coste **$1,258906**, sin Terra/targets y facts 0.

**Diagnóstico.** El prompt definía `agrees_with_author` como corrección de la decisión
supported/unsupported, mientras el validador local exigía además que una alternativa coincidiera
exactamente con el set del autor. Por tanto, seis fallos son incompatibilidad del instrumento, no
evidencia de fallo semántico del planner. El output desconocido sí es inválido de proveedor. Sólo
cinco filas son válidas; sus 13 soportados no estiman el support-rate y no se postseleccionan. La
cohorte queda cerrada sin retry ni relajación.

**Cambio de población.** Tras S201+S202 quedan cuatro preguntas S100 no observadas, insuficientes
para generalizar. La reserva legítima serán familias/predicados Kidde sin cobertura actual. La autoría de
pregunta y gold usará Sol 5.6 `xhigh` principal, Fable 5 independiente y evidencia verificada
visualmente página-a-página; un canary pequeño precederá al lote para limitar coste. Sólo después
se usará ejecución económica para medir. `chunks_v3` no cambia y Railway no es gate.

## DEC-115 — S203: el transporte visual y ambos Frontier funcionan; gold canary NO-GO sin postselección

**Freeze y revisión.** S203 congeló tres unidades nuevas de tres familias Kidde, 11 renders a
200 dpi, los 55 PDFs del universo y cero solape de basename/SHA contra las 78 fuentes resueltas
del gold existente. No afirmó que los PDFs fueran inéditos: S159/S195/S197/S200 habían usado
otras páginas/predicados. Sol 5.6 `xhigh` encontró ocho defectos del diseño; 8/8 se corrigieron
antes de la PR #138 (pixel-only real, focus/topic gate, comparación de candidatos, novedad por
SHA+facts, ledger de coste, insuficiencia=NO-GO, freeze downstream y descubrimiento automático).
Fable llegó al pin exacto en esa review pero devolvió `refusal`; se registró sin retry ni etiqueta
`unavailable`. CI verde y merge precedieron a la ejecución.

**Resultado.** Completaron las ocho llamadas congeladas: Sol 3/3 candidatos válidos, Fable 3/3,
Sol revisó los tres Fable y Fable los tres Sol. Coste conservador **$14,07876**. El resultado es
`NO_GO_VISUAL_GOLD`: Sol rechazó el candidato térmico de Fable por recomendar BR para sala de
calderas sin que la fuente haga esa recomendación; Fable dio PASS a los tres Sol, pero en el caso
de prueba de relé añadió dos observaciones explícitamente no materiales a `issues`, y el gate
local congelado trataba cualquier `issues` no vacío como bloqueante. Solo 1/3 pares queda limpio
bajo la letra estricta; no se postselecciona ni salva, se añaden 0 golds y se mueven 0 facts.

**Sucesor limpio.** La cohorte S203 queda cerrada sin retry/reparación. S204 debe usar páginas y
predicados Kidde frescos, extraer primero un contrato visual reusable (no copiar el runner),
prohibir recomendaciones de aplicación no literales y separar `blocking_issues` de
`nonblocking_notes` con consistencia de veredicto. Es corrección genérica de instrumento y se
medirá solo en población nueva. Planner/bot siguen cerrados. `chunks_v2` activo,
`chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE`, Railway fuera del gate.

## DEC-116 — pre-S204: contrato visual reusable, leakage HyQ cerrado y cohorte congelada

**Corrección genérica.** S204 extrae `src/rag/visual_gold.py`: payload estrictamente pixel-only,
citas sólo a páginas focus, prohibición de recomendaciones/aplicaciones no literales y revisión
con `blocking_issues` separadas de `nonblocking_notes`. Un PASS puede conservar notas de estilo,
pero el validador exige cero condiciones bloqueantes y rechaza contradicciones PASS/FAIL; también
rechaza el caso vacíamente verdadero sin reviews.

**Leakage detectado upstream.** La primera selección contenía preguntas sobre batería, pinout y
montaje que ya aparecían en S99 como HyQ doc-side. No son preguntas de test, pero evaluarlas
después contra un índice que las embebe sería contaminación. Se descartaron antes de cualquier
autoría. El packet final añade las 179 HyQ asociadas a los tres PDFs al screen semántico junto con
los 51 golds y congela tres relaciones visuales no presentes como preguntas exactas: topología
Clase A, posiciones DIP 008/112 y ranuras visuales del KE-DBA-AUXW. Los revisores conservan el gate
de novedad semántica. Son cinco páginas a 200 dpi, 55 PDFs descubiertos,
cero overlap basename/SHA con golds y exclusión explícita de S203.

**Revisión y gate.** Sol 5.6 `xhigh` y Fable 5 alcanzaron los pins exactos en sendas llamadas de
revisión monolítica, pero agotaron 10.000/8.000 tokens sin JSON final. Se registran como
`failed_api_incomplete`/`failed_api_max_tokens`, nunca `unavailable`, por coste conservador
**$3,25083** y sin retry. La auditoría determinista confirmó/corrigió tres defectos y pasa 4/4
tests. Se autoriza PR preejecución; sólo tras merge CI-verde se ejecutan como máximo ocho llamadas,
sin retry, merge, reparación, salvage o postselección y con techo $40. Un GO crea candidatos aún
no integrados y mueve 0 facts; requiere otro freeze antes de medir bot. `chunks_v2` sigue activo,
`chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no bloquea PR/merge.

## DEC-117 — S204: contrato corregido generaliza; el publication-gate dual simétrico no

**Resultado.** Tras PR #140 y CI verde, S204 completó las ocho llamadas congeladas: 3/3 candidatos
Sol válidos, 3/3 Fable válidos y dos cross-reviews completas por **$15,729345** conservadores.
Fable dio PASS a los tres Sol. Sol dio PASS a DIP 008/112 y ranuras, pero FAIL al cableado Clase A
de Fable: los seis facts estaban soportados, correctamente citados y entrañados, pero la frase
final podía interpretarse como unir polaridades opuestas y la instrucción de cableado omitía la
advertencia visible de cortar alimentación y descargar energía almacenada. Es bloqueo real de
completitud/seguridad, no repetición del falso bloqueo por `issues` S203.

**Cierre.** El estado es `NO_GO_VISUAL_GOLD`; los dos pares simétricos limpios no se postseleccionan
y los tres Sol aceptados por Fable no se salvan. No hay retry, reparación, gold, bot-eval ni facts.
El contrato reusable sí generaliza: notas no materiales no bloquean, no aparecieron inferencias de
aplicación, el screen gold+HyQ pasó y los tres predicados visuales fueron autorables/revisables.

**Geometría sucesora permitida.** El defecto aislado muestra que exigir calidad publicable al
candidato independiente —que nunca sería el gold final— acopla innecesariamente su calidad a la
del principal. En una población completamente nueva puede congelarse antes de selección una
geometría donde Fable siga generando a ciegas un counterpart para detectar desacuerdo, pero el
publication-gate se aplique al candidato Sol: Fable debe revisarlo y dar PASS, y ambas direcciones
deben declarar cero desacuerdo material. Los defectos propios del counterpart que no contradigan
el principal se diagnostican pero no lo vetan. Esto no autoriza rescatar S204. `chunks_v3` sigue
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; Railway no es gate.

## DEC-118 — S205: la geometría principal pasa, pero el leakage del mismo source invalida el GO

**Geometría y ejecución.** La función de publicación se congeló en `af6de65` antes de seleccionar
fuentes: Sol 5.6 `xhigh` es el único autor final; Fable 5 genera a ciegas, revisa todos los Sol y
su propio borrador sólo sirve como probe independiente de desacuerdo. Un defecto exclusivo del
borrador no publicado no veta; topic drift o discrepancia material sí. Sobre tres predicados
Kidde frescos respecto a S203/S204, la PR #142 pasó CI y se mezcló antes de ejecutar. Completaron
8/8 llamadas exactas, cero retries, seis candidatos válidos y dos reviews por **$11,81598**.
Fable dio PASS 3/3 a Sol; Sol dio PASS 2/3 a Fable; no se declaró desacuerdo material. El runner
emitió `GO_KIDDE_GOLD_CANARY` conforme al gate mecánico.

**Adjudicación local bloqueante.** `s205k03` pide los tres modelos y funciones de
`Conventional IS Barriers`. El ledger S99 ya contiene
`hyq:54c2275f-f08f-4cc8-bb33-df5c81dbcd02:2`, que pregunta qué barreras galvánicas/aislamiento
se usan con dispositivos convencionales. Su `source_file` coincide exactamente con el stem del
PDF seleccionado y ambos apuntan a la misma tabla; el desfase 4/5 es numeración de página del
pipeline, no otro documento. Sol detectó el duplicado al revisar el counterpart y lo marcó FAIL;
Fable lo negó al revisar el final, infiriendo erróneamente otro documento/producto porque las
filas de cobertura del packet omitían identidad de source. La novedad no puede delegarse sólo a
juicio semántico si el builder conoce una identidad exacta. Un benchmark downstream premiaría
la HyQ ya embebida y contaminaría retrieval.

**Cierre sin salvage.** El estado autoritativo es `CLOSED_NO_GO_VISUAL_GOLD`, aunque se conserva
el GO bruto para auditar la contradicción. No se postseleccionan los dos candidatos limpios, no se
repara, no se reintenta, no se integra gold y se mueven 0 facts. La línea de canarios visuales se
cierra para evitar otra convergencia y el trabajo vuelve al bucket dominante de 12 synthesis-miss
preexistentes, upstream→downstream. `chunks_v2` permanece activo,
`chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no bloquea PR/merge con CI verde.

## DEC-119 — S206: el ledger genérico de facetas no transmite relaciones fuente y queda cerrado sin código muerto

**Diseño y revisión.** S206 probó una hipótesis estructural distinta: reutilizar el clasificador de
arquetipos ya versionado para pedir al generador que comprobara facetas genéricas de diagnóstico o
programación sobre los chunks servidos. El tratamiento exigía producto reconocido, era byte-inerte
por defecto y no contenía IDs, modelos, números ni facts objetivo. Sol 5.6 `xhigh` fue revisor
principal y Fable 5 el independiente. Sus hallazgos materiales se corrigieron una sola vez antes de
mirar outputs: veto por claims no soportados, freeze completo, citas ligadas localmente a la
obligación, runner sin resume/retry y separación explícita entre proxy de relación y KPI canónico.
No se abrió otra ronda de convergencia.

**Resultado causal.** Las 28 llamadas Sonnet 4.6 congeladas (cuatro targets, dos guardrails y un
canary independiente; dos réplicas por brazo) costaron **$1,733967**. El tratamiento obtuvo **0**
relaciones residuales estables, **0** preguntas target completas y una regresión protegida en
`hp011/default_latched_faults`; no hubo citas inválidas ni truncados. El scorer local emitió
`NO_GO`, por lo que el veto semántico Frontier de resultados no podía rescatarlo y se omitió conforme
al contrato, ahorrando gasto. No se itera el wording ni se reintenta esta población.

**Cierre limpio.** El hook, flag, configuración, módulo y tests del candidato no viajan a producción.
Se conservan como `evals/s206_answer_facet_seam.patch`, verificado con `git apply --check`, junto con
preregistro, envelopes, receipts, scorer y reviews. Esto evita otro puente híbrido default-off: la
línea “recordar al modelo que cubra más facetas” queda cerrada como mecanismo. El scoreboard no
cambia: **143/157 OK (91,08%)**, 12 synthesis-miss y 2 retrieval-miss; faltan 11 facts para 98%.
`chunks_v2` permanece activo, `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no es gate.

## DEC-120 — S216: la descomposición por pregunta se cierra en diseño antes de una ejecución cara

**Hipótesis estructural.** S216 proponía sustituir la síntesis monolítica por una descomposición
question-only, responder cada foco con el contexto completo y ensamblar todos los bloques de forma
determinista. La versión corregida eliminó baselines históricos, igualó a 1.600 tokens el máximo
agregado de control y tratamiento, retiró el texto de los focos del candidato y separó generación
de scoring. La PR #167 congeló un A/B contemporáneo sobre 14 preguntas de desarrollo y un
guardrail de 35 preguntas multichunk, sin abrir los cuatro targets ni mover facts.

**Gate Frontier dual.** Sol 5.6 `xhigh` principal y Fable 5 independiente devolvieron NO-PASS
sobre el mismo commit mergeado. Coincidieron en tres defectos materiales: `question_complete` se
recogía pero no bloqueaba, el supuesto cegado revelaba treatment por sus encabezados `Parte N` y
el contrato sobre-afirmaba protección de 87 facts aunque solo vetaba los estables en ambos
controles contemporáneos. Sol añadió dos fallos de aislamiento confirmados: scorer/reviewer no
revalidaban el freeze completo entre fases y el runner leía los bytes de los score packets para
hashearlos mientras afirmaba que no estaban disponibles. Fable añadió un mismatch decisivo: la
eficacia se mediría en single-source mientras el objetivo real es multichunk.

**Cierre sin convergencia ni gasto masivo.** No se crea permit y no se ejecutan las 49 llamadas
Terra, las 196–686 Sonnet ni la revisión semántica de resultados. Se descarta parchear y repetir
S216 o reutilizar otra vez la cohorte S173. Una reapertura futura requeriría una población
multichunk fresca, aislamiento de contenido real entre fases, completitud bloqueante, outputs
cegables por formato y revalidación end-to-end del freeze. El marcador queda en **143/157 OK
(91,08%)**, con 12 synthesis-miss y 2 retrieval-miss; faltan 11 facts para 98%. `chunks_v2`
permanece activo, `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` y Railway no bloquea PR/merge.


---

## DEC-121 (S269, 18-19 jul 2026) — Triage de requiredness de los 12 synthesis-miss: PROPUESTA 8 CORE / 3 SUPPLEMENTARY / 1 SOURCE-CONFLICT, pendiente adjudicación de Alberto

**Decisión.** Ejecutar el gold-review synth pendiente (DEC-094) sobre los 12 residuales como
triage multi-agente (4 analistas independientes por-pregunta + auditoría del instrumento +
verificador adversarial, acuerdo 12/12) y elevar a Alberto un packet de adjudicación al píxel.
Propuesta: **8 CORE** (obl_7bba pestaña-padre · obl_b6f6 aislamiento-seguridad · obl_a5d9
rol-nominal [borderline] · obl_2f5d r.i-rearme [el más core; único selection-loss] · obl_b2043 ·
obl_7aa7 · obl_16637 · obl_0d6a) · **3 SUPPLEMENTARY** (obl_015f TONE [demote más débil] ·
obl_07ee 120%/A11-C32 [la pregunta es flujo BAJO] · obl_1615 paso-5s) · **1 SOURCE-CONFLICT**
(obl_872c: prosa "seis" vs tabla de 7 columnas pairwise-distintas VERIFICADAS → re-spec a
obligación de DISCLOSURE, guard s243). Instrumento auditado JUSTO (matcher determinista s163,
0 model calls, **0 INSTRUMENT-FN**). Los 2 retrieval-miss (cat017#2, hp010#1) confirmados
reales con hecho verbatim en corpus. **Proyección si se acepta:** denominador 157→154, objetivo
98% = 151/154 → +8 conversiones. **Nada se edita sin ✅ de Alberto + puerta gold_store.**
Artefactos: `evals/s269_triage_12misses_v1.yaml` · `evals/s269_goldreview_packet_v1.md` (con
renders por página). Motivo: pregunta explícita de Alberto ("¿hay problemas de golds que hagan
que esos 12 no sean tantos?"). Alternativa descartada: atacar los 12 solo con mecanismo
(ignoraría 3-4 demotes legítimos y un conflicto de fuente insalvable por síntesis).

## DEC-122 (S269) — Contrato de átomos must-preserve: diseño dúo-adjudicado; Etapa-1 v1 NO-GO de instrumento; pivote a harness de MUTACIONES con gold mecánico; veredicto final = recall 4/4 GO + residual de binding ABIERTO

**Decisión.** Mecanismo Track 2 para los 11/12 misses within-cited-fragment: detectores por
familia s243 + binding claim↔átomo con attestation de identidad (doc_map, fail-closed,
anti-S164) + render por postcondición (anexo VERBATIM monotónico, cap 4, disclosure ante
contradicción; caption sin "verificada"). Flag `MUST_PRESERVE_CONTRACT` default-off,
byte-idéntico off (verificado por dúo). **Proceso (2 rondas de dúo, 0 FP en 35 hallazgos):**
diseño v1→v2 (Sol xhigh 10 + Fable 8: gate de recall anti-inversión-S249, attestation,
degradación del claim "0 regresiones por construcción", reapertura formal s222/s223 = decisión
de Alberto ANTES de Etapa 2); build v1 (Sol 9 + Fable 7: gold de modelo barato NO fiable — 87%
de negativos marcados positivos, F-COUNT incumplió su prompt; 5 críticos de código verificados)
→ **pivote de instrumento: mutaciones con gold MECÁNICO** (patrón S249; sin etiquetadores).
**Iteración de contrato de binding ×3, cada una validada en población FRESCA** (seed-270:
36 FP hermanos → presencia-parcial; seed-271: 14 FP single-token → ≥2 tokens propios;
seed-272 = medida FINAL): **mutation_recall F-RANGE 1.0 · F-BUNDLE 0.931 · F-MANDATORY 1.0 ·
F-COUNT 0.828 (4/4 GO, brazos determinista e híbrido idénticos — el híbrido no añade recall) ·
cross-binding 0 FP · attestation 0 · cobertura 0.92 · MANDATORY clean 0 FP (16
conduct-appends).** **Residual ABIERTO reportado sin iterar** (compromiso anti-overfit):
clean-noise RANGE/BUNDLE FP=40 — átomos hermanos que comparten 2 tokens técnicos genuinos;
tensión estructural presencia-parcial vs FP=0. Opciones a adjudicar: (a) aceptar como
enriquecimiento (re-spec del gate con sanción de Alberto), (b) filtro de pertinencia
cheap-LLM en binding (+1 build en cohorte fresca), (c) restricción misma-familia. **Etapa 2
(probe único a los 4 targets, gate DEC-112, K=3) sigue gateada por: residual adjudicado +
reapertura formal de la familia s222/s223 por Alberto** (evidencia: cierre S223 fue con review
semántica INCOMPLETA + directiva de Alberto de no descartar líneas por condiciones distintas +
4 diferencias de diseño). Coste Track 2: ~$2.2 (labeling $1.63 + híbrido $0.57).

## DEC-123 (S269) — Registro de assets visuales (diagramas): construido completo, gate de activación PASS, pendiente SOLO runbook DB de Alberto

**Decisión.** Implementar el contrato S190 (rama `claude/s269-visual-assets`): tabla
`document_visual_assets` (migración 014 + rollback; independiente del chunker; `uncertain`
JAMÁS se sirve) + loader del bridge verificado **byte-idéntico** al audit S190 (5.096 páginas,
receipt sha c7787474) + clasificador de utilidad: v3 (80, banda [28,44] **NO-GO por diseño del
trigger** — proxy posicional refutada 2ª vez; calidad del clasificador con señal positiva,
spot-check 10/10) → v4 **full-bridge 5.096/5.096 ($3.52)**: useful 4.606 / serving-set 4.489
(useful ∧ rol∈{wiring,table,procedure,ui}) → **gate de activación PASS: 59/60 (0.983≥0.95) +
0 portadas/marketing** (panel 6 agentes visión + submuestra orquestador 13/13; NO gold humano,
declarado; auditable en `spotcheck_v4/`). Serving flag-gated `VISUAL_ASSETS_REGISTRY=off` con
filtro de rol triple; solo páginas de fragmentos CITADOS; cap 2. **La aplicación de la
migración 014 fue BLOQUEADA por permisos del entorno** → runbook de 5 pasos para Alberto en
`evals/s269_visual_utility_gate_v4.yaml`. Corrige la creencia de partida: el bot no servía
diagramas "de v1" — no servía NINGUNO (0/25.090 URLs en chunks_v2).

## DEC-124 (S269) — Voz: catálogo de modelos REGENERADO; whisper-1 se queda; Wispr Flow descartado como integración server-side

**Decisión.** Regenerar `data/model_catalog.json` desde chunks_v2 vivo (jun-09 → jul-18):
**+6 modelos reales** que faltaban en el vocabulario Whisper (9-30441, AD68N-0100, DM715,
N-MC-BB-G, NC-MC-0-G, NFXI-FLX); −2 duplicados de caso/guión sin pérdida (RP1R/ZX-50 con
RP1r/ZX50 vivos). 100 tests catalog/voice verdes. **Wispr Flow es app de dictado CLIENTE**
(el técnico dicta y el texto entra por teclado — cero integración server-side posible para
notas de voz de Telegram); el ASR real es OpenAI con selector versionado (allowlist whisper-1
default + gpt-4o-transcribe/-mini). **Constraint vigente intacto:** migrar de ASR exige el
gate ciego con ≥30 audios reales estratificados (`evals/voice_asr_model_selection_gate_v1.yaml`)
— hoy no existen; recogerlos antes de comparar.

## DEC-125 (S270, 19 jul 2026) — Adjudicación de Alberto del packet gold-review (DEC-121) APLICADA: 8 CORE (incl. demote rechazado + merge de warnings) + 1 disclosure + 2 SUPPLEMENTARY; denominador 157→154; corrección píxel t.Fi→t.A

**Decisión.** Registrar y proyectar las marcas de Alberto sobre
`evals/s269_goldreview_packet_v1_ADJUDICADO.md` (autoridad; DEC-025: el gold es suyo). Las 12
marcas: **(1)** obl_7bba ✏️→CORE — su nota es una PREGUNTA ("por qué estamos utilizando texto
en italiano… ¿un cambio de GPT 5.6 Sol?"), no un cambio ("estoy de acuerdo con el veredicto
que propones"); respuesta registrada: el italiano es el MOCK de pantalla del propio manual
(la UI del panel AM-8200 está en italiano; la prosa del manual -spa es español) — no lo
introdujo ningún modelo; al editar el gold, reflejar Programa/Programmazione. **(2)** obl_015f
❌ AL DEMOTE → QUEDA CORE ("Tiendo a ser más coservador, por lo que creo que sí lo
incluiría"). **(3)** obl_b6f6 ✅ CORE. **(4)** obl_a5d9 ✅ CORE. **(5)** obl_07ee ✅
SUPPLEMENTARY (demote parcial de los anchors 120 %/A11-C32). **(6)** obl_1615 ✅
SUPPLEMENTARY. **(7)** obl_2f5d ✅ CORE ("…pero seguro que no es t.Fi"). **(8)** obl_872c ✅
re-spec a DISCLOSURE (`document_value_conflict` "seis" vs 7; "muy bien identificada esta
inconsistencia"). **(9)** obl_b2043 ✅ CORE. **(10)** obl_7aa7 ✅ CORE. **(11)** obl_16637 ✏️
MERGE con obl_0d6a en UNA obligación de bloque-warning ("con que lo exijamos una vez es
suficiente"). **(12)** obl_0d6a ✅ (absorbida; carrier del merge = obl_0d6a, la formulación
más fuerte del par). **Aritmética resultante** (proyección determinista
`scripts/s270_project_adjudicated_funnel.py`, $0, SHA-pins LF-normalizados, falla en drift):
denominador 157 → **154** (−2 SUPP, −1 merge); funnel **143 OK / 9 synth (8 CORE + 1
disclosure re-specced) / 2 retrieval (92,86 %)**; `facts_moved_to_ok: 0` (reconciliación de
DENOMINADOR, no mueve OKs); `official_atomic_kpi: null` (los 77 legacy carries siguen);
objetivo declarado **98 % de 154 = 151 → +8**. Artefactos:
`evals/s270_gold_adjudication_v1.yaml` (marcas VERBATIM + provenance + tratamiento) ·
`evals/s270_adjudicated_funnel_v1.json` · test `tests/test_s270_project_adjudicated_funnel.py`.
**Corrección píxel t.Fi→t.A** (hallazgo §Verificación-de-renders del packet, zoom 500 dpi):
NINGÚN spec vivo ancla t.Fi (grep src/+scripts/; `answer_planner.py` kinds s141 limpio) — la
única mención viva era el comentario-ejemplo OCR de `src/rag/must_preserve.py` (anotado: t.Fi
= transliteración de t.A, el patrón sigue cazando la forma extraída; 0 cambio de
comportamiento). Los artefactos congelados (s113/s163/s235/triage) NO se mutan (patrón
S133/S153/S163): la corrección queda registrada como aplicable en la próxima regeneración del
spec y en toda edición de gold vía `gold_store` (ancla = t.A o ambigüedad 7-seg declarada;
`feedback_7segment_reading`). **Candidata de producto registrada** (nota de Alberto, fila 6):
¿servir los átomos SUPPLEMENTARY marcados como tales para visión más completa del técnico? —
ligada al mecanismo must-preserve (DEC-122: el render por postcondición podría anexar
supplementary etiquetado); decidir con la Etapa 2, no aquí. **Método:** aplicación mecánica de
la autoridad del gold — sin dúo (no hay decisión de diseño propia que revisar; el Protocolo 3
no aplica a registrar la adjudicación del dueño). **Alternativas descartadas:** (a) editar ya
los golds vía `gold_store` en la misma sesión — se separa para que la edición parta del
registro adjudicado commiteado + re-score dirigido (paso 3 del packet); (b) mutar los
congelados con t.A — violaría el freeze; (c) mantener la proyección solo en prosa de docs —
sin script pineado la aritmética no sería verificable ni estable ante drift.

## DEC-126 (S270, 19 jul 2026) — Reapertura FORMAL de la familia s222/s223 (permiso explícito de Alberto) + re-spec del residual clean-noise a opción (a) «enriquecimiento etiquetado» — desbloquea la Etapa 2 del contrato must-preserve (DEC-122)

**Decisión (registrada ANTES del build de la Etapa 2).** **(a) Reapertura formal de la familia
s222/s223.** Provenance = permiso explícito VERBATIM de Alberto (S270, 19 jul): *«reapertura de
S222/223: si tiene sentido para mejorar el bot, tienes permiso explícito para retomarlo»*, más su
OK a la re-spec del residual (opción a). La condición «si tiene sentido para mejorar el bot» queda
OPERACIONALIZADA por el gate de la propia Etapa 2 (≥1 conversión estable + 0 regresiones
protegidas estables + 0 conflictos nuevos): si el gate falla, la reapertura NO produce ship —
el permiso habilita el probe, no el default-on. Justificación técnica de por qué tiene sentido
(el contexto con el que Alberto fue informado 2×, DEC-122): el cierre S223 fue con review
semántica INCOMPLETA (Fable cortó por max_tokens; Sol revisó 520) + la directiva de Alberto de
no descartar líneas por condiciones de ejecución distintas + las 4 diferencias de diseño del
contrato vs la familia addendum: detector DETERMINISTA por familia (no LLM semántico),
attestation de identidad por catálogo fail-closed (anti-S164), spans VERBATIM con cita [Fn] +
disclosure ante contradicción numérica, y gates S249-preservados (recall por familia MEDIDO en
la Etapa 1: 4/4 GO, DEC-122). **(b) Re-spec del residual clean-noise a la opción (a) de
DEC-122:** los 40 FP RANGE/BUNDLE de átomos HERMANOS (comparten ≥2 tokens técnicos genuinos con
el claim) se re-especifican como ENRIQUECIMIENTO ETIQUETADO — anexos bajo el encabezado
«Información adicional del manual:», marcados como material adicional, no como corrección — y
dejan de contar como FP del gate de Etapa 1. Alineado con la preferencia de diseño de Alberto
(nota manuscrita de la fila 6 del packet adjudicado, registrada en DEC-125 como candidata de
producto: servir los átomos supplementary MARCADOS como tales «para que el técnico tenga una
visión más completa»). **Los gates de Etapa 2/3 NO se relajan:** regresiones protegidas y
conflictos nuevos se miden igual — un anexo hermano que rompa un matcher protegido o dispare el
detector de conflictos cuenta contra el gate exactamente como antes. **Alternativas
descartadas:** (a′) mantener la familia cerrada y no probar el mecanismo — dejaría el lever
synthesis sin su probe con la Etapa 1 en GO y contradiría el permiso explícito recibido;
(b′) opción (b) del residual (filtro de pertinencia cheap-LLM en el binding) — +1 build y
+coste en cohorte fresca ANTES de saber si el mecanismo convierte algo (prematuro; queda
disponible si la Etapa 2 muestra que el ruido daña); (c′) opción (c) restricción misma-familia —
recorta cobertura de `bundle_member_loss` sin evidencia de daño (y el daño, si existe, lo
cazan los gates de Etapa 2). **Método:** el diseño del mecanismo ya fue dúo-adjudicado en
DEC-122 (2 rondas, 0 FP en 35 hallazgos); esta DEC registra la AUTORIZACIÓN del dueño + la
re-spec del residual; el gate del probe se congela en
`evals/s270_etapa2_probe_prereg_v1.yaml` ANTES de construir el runner. Refs: DEC-122 ·
DEC-125 (candidata fila 6) · `evals/s269_synthesis_portfolio_design_v1.md` §1 Etapa 2 ·
`evals/s270_gold_adjudication_v1.yaml`.


## DEC-127 (S270) — Campaña de probes del contrato must-preserve CERRADA: GO del gate con 1 conversión estable; mapa causal completo del residual; Etapa 3 limpia; iteración de mecanismo DETENIDA por disciplina anti-overfit

**Decisión.** Tras 3 probes pareados a los 4 targets (v1 $0.75 / v2 $1.09 / v3 $1.14; cuenta de
probes VISIBLE en cada prereg; cambios entre probes justificados por FUNNEL, jamás por los
textos gold; cada versión validada antes en población fresca — seeds 273/274 GO), el veredicto:

- **CONVERTIDA ESTABLE: obl_b6f6211be439** (hp002, callout de seguridad "bloquear controles/
  alertas/extinción antes de mantenimiento) — 3/3 réplicas en v2 Y v3 (tras la priorización
  seguridad-primero del cap). **0 regresiones protegidas y 0 conflictos nuevos en 36 réplicas
  pareadas acumuladas.**
- **ENTREGADA pero no acreditable: obl_872c35fb41d7** — el mecanismo v3 anexa el disclosure
  COMPLETO de dos lados ("seis" declarado + las 8 etiquetas de la enumeración servida, citas
  dobles). El check pre-registrado exige el literal "siete", que NO existe en el texto servido
  (OCR = 8 etiquetas). **Pregunta de spec para Alberto:** ¿el disclosure exigible es el de la
  evidencia SERVIDA (6 vs 8 etiquetas — lo que el bot honesto puede afirmar) o el de la tabla
  real del PDF (6 vs 7)? Si lo primero, la conducta actual ES correcta y acreditable con check
  re-specced (2ª conversión).
- **Residual con palanca DISTINTA del mecanismo** (mapa causal verificado en trazas):
  obl_0d6a (merged warnings) = SERVING-VIEW — el bloque existe en el fragmento crudo pero la
  vista servida por la lane lo trunca (palanca retrieval/serving) · obl_2f5d (stretch) + átomos
  hp011 = fragmentos NO citados por el borrador (palanca de alcance/serving) · obl_7bba =
  tensión de binding declarada (la ventana de cita comparte 1 solo token propio "cbe"; NO se
  relajó el contrato ≥2 para no comprar conversiones con ruido) · obl_a5d9/obl_015f(TONE)/
  obl_b2043/obl_7aa7 = composites que dependen del brazo híbrido — el híbrido DISPARÓ (7-8
  calls/réplica, 0 errores) pero sus propuestas no llegan al anexo y los contadores por-causa
  no se persistieron en el trace → **gap de instrumento declarado**, diagnóstico pendiente.
- **Etapa 3 (regresión judge-free, ruta VIVA):** 5/5 smoke golds monotónicos (ON = OFF +
  apéndice opcional; texto base inmutable por construcción) y **0 apéndices disparados** en
  preguntas sanas — el mecanismo es silencioso donde no hace falta. $0.61.

**Iteración DETENIDA** (compromiso pre-declarado en el prereg v3): el siguiente paso NO es un
probe #4 — es (1) la decisión de spec de 872c (Alberto), (2) el diagnóstico del gap híbrido con
contadores persistidos (instrumento, sesión futura), (3) las palancas de serving-view/alcance
para 0d6a/2f5d/hp011 (workstream retrieval), (4) los 2 retrieval-miss (cat017#2, hp010#1).
**Aritmética honesta vs objetivo:** 143 OK + 1 conversión mecanismo (pendiente de re-score
oficial vía gold_store/instrumento) + 1 posible por spec-872c → el +8 para 151/154 NO se
alcanza esta sesión; el gap restante tiene dueño por-clase. Ship del mecanismo: flag
`MUST_PRESERVE_CONTRACT` default-off, merge tras dúo del código (Protocolo 3); crédito
productivo = decisión de release separada.

**Costes de la campaña:** probes $2.99 + Etapa-1 v5/v6 $0 + Etapa 3 $0.61. Alternativas
descartadas en cada paso: relajar el binding ≥2 (compra conversiones con ruido — rechazado
2×); re-probe sin validación fresca previa (overfit — jamás se hizo); tunear el check de 872c
en caliente (prohibido por prereg — se elevó a spec).

**Enmienda DEC-127 (ship-review del dúo, 19 jul — Sol 4/4 confirmados, 0 FP; Fable
failed_api ×2 por presupuesto, DEC-106 sin tercer intento; tally
ts=2026-07-19T16:05:35).** **(1) Claim de no-regresión ACOTADO (M3):** los "0
regresiones en 36 réplicas" cubren las 3 obligaciones PROTEGIDAS
(obl_05482a6b3f0e/obl_0db2b9f2842a/obl_5784f16b1a11, las cubiertas por el baseline
s235) — la cláusula de fact-anchors es VACÍA por ausencia en el packet (declarado en
el prereg v1); no es un claim de no-regresión general. **(2) Etapa 3 v1 INVALIDADA
(C1):** el smoke pareado comparó OFF-vs-OFF (el apply corría con el flag off →
passthrough byte-idéntico, trace None — tautología). Script corregido
(`scripts/s270_etapa3_smoke_pareado.py`: flag EFECTIVO alrededor del apply + assert
trace≠None con citas); la corrida corregida queda PENDIENTE de ejecución del
orquestador. **(3) ON-medido ≠ ON-shippeado (C2), RESUELTO con certificación
det-only:** los probes v2/v3 midieron el brazo ON con el detector HÍBRIDO inyectado
mientras el generador de prod aplica el contrato DETERMINISTA puro;
`scripts/s270_probe_det_certification.py` re-aplicó el contrato SIN detect_fn (path
exacto de prod) sobre los borradores OFF almacenados del probe v3, $0 y 0 exposición
nueva → **GO: obl_b6f6 3/3 det-only, 0 regresiones, 0 conflictos**
(`evals/s270_probe_det_certification_v1.json`) — el path mergeado queda certificado
y la decisión híbrido-en-prod NO es necesaria para este ship (si algún día se
quiere el híbrido en prod, es FORK explícito con su propia medición). **(4) Alcance
del resultado (M4):** la conversión obl_b6f6 es estabilidad LOCAL en los 4 targets
con contextos congelados s113 — NO generalización a demo/producción; esa medición
es el assessment estandarizado (DEC-094), no estos probes.

**DEC-127b (S270, cierre) — Etapa 3 CORREGIDA ejecutada (la v1 era OFF-vs-OFF, cazado por
dúo-Sol): monotonía 5/5 ✓, apéndices en ruta viva 2/5, y 3 DEFECTOS DE CALIDAD del apéndice =
BLOQUEADORES DE ACTIVACIÓN (no de merge):** (1) nota duplicada (hp001 — bug de dedup del
render); (2) span de enumeración VACÍO anexado verbatim (cat007 — tabla OCR T1-T10 en blanco;
falta guard de contenido-no-vacío); (3) emparejamiento conteo↔menú-de-navegación incoherente
(hp001 "2,4,6 u 8 lazos" · "Sistema | Otros | Reiniciar" — la precisión del F-COUNT cross en
pools vivos necesita el tie de sección más estricto). **El flag `MUST_PRESERVE_CONTRACT`
permanece OFF; la activación en demo queda gateada a los 3 fixes + re-smoke limpio.** El merge
default-off es seguro (byte-idéntico off + certificación det-only GO). Certificación det-only:
b6f6 3/3 en el path exacto de prod ($0, borradores almacenados) — el híbrido NO es necesario
para este ship.

**DEC-128 (S271) — obl_872c: disclosure re-especificado a OPCIÓN 1 «evidencia servida»
(adjudicación de Alberto).** El check `disclosure_covered` del instrumento
(`scripts/s270_etapa2_probe.py`, el runner v1 que importan los probes) acredita si la
respuesta (o su apéndice must-preserve) contiene: (a) el conteo DECLARADO («seis»/6
co-localizado con el sustantivo tipos-de-retardo); (b) las etiquetas enumeradas VISIBLES en
la evidencia servida — presencia sustancial: TODAS las no-basura de al menos un lado servido
(tira OCR de F1 o cabeceras de la tabla de F2); y (c) un marcador EXPLÍCITO de discrepancia
(«también indica» / «no coincide» / «difiere» / «discrepan» ...) — **SIN exigir el literal
«siete»**. Alternativa 2 (exigir el 7) DESCARTADA: el 7 solo es conocible al píxel → exigirlo
es pedirle al bot una INVENCIÓN; la curación de esa tabla queda como lever de INGESTA futuro.
Re-score $0 de las réplicas ON almacenadas del probe v3 con la spec re-specced →
**872c acredita 3/3 ON, 0/3 OFF = SEGUNDA conversión estable**
(`evals/s271_872c_respec_rescore_v1.json`; es re-score de SPEC sobre respuestas ya
generadas, NO un probe nuevo — bajo la spec vieja puntuaba 0/3 ON, 0/3 OFF). En la
certificación det-only v2 (con los guards s271) 872c también convierte det-only 3/3 y el
guard de contenido-informativo NO mata su disclosure (la tira de etiquetas OCR tiene texto
real, no celdas en blanco — verificado por-réplica en
`evals/s271_probe_det_certification_v2.json`).

Adjudicación adicional de Alberto (S271): el claim cat017#2 "licencia CLIP (una por circuito
de lazo CLIP)" se CONFIRMA CORE — clase muro-duro-condicional (la pregunta cubre "dar de
alta" un lazo genérico y la INSPIRE soporta OPAL y CLIP; sin el .bin el alta CLIP no
funciona), misma clase que obl_b6f6. Recomendación del orquestador aceptada verbatim por
Alberto ("OK a tu recomendación de mantenerla CORE"). El denominador 154 NO cambia. El
diagnóstico retrieval del Bloque B lo trata como CORE.

**DEC-129 (S271, Bloque A) — los 3 BLOQUEADORES DE ACTIVACIÓN de DEC-127b cerrados con
guards mecánicos y genéricos en `src/rag/must_preserve.py` (v4), sin tocar el contrato de
binding:** (1) **dedup del render** — dos átomos con span idéntico tras fold (o solapado
≥90% con el MISMO contenido numérico; números distintos = hecho distinto, se conservan)
anexan una sola vez; (2) **guard de contenido informativo** — ningún lado del anexo puede
ser vacío/solo-puntuación ni tabla de etiquetas-SIN-valores (celdas en blanco); si el
lado-enumeración de un disclosure no es informativo, el disclosure ENTERO no dispara (mejor
silencio que basura); distingue celdas-en-blanco de etiquetas-CON-texto (la tira OCR de
hp017 sigue viva); (3) **tie ESTRICTO del F-COUNT a distancia** — la enumeración de un tie
de sección/cross no puede ser un crumb de navegación/menú (línea única con `|`, ≤4
tokens/celda, sin números) y debe compartir dominio con el conteo (sustantivo contado en la
enumeración, o heading de sección compartiendo ≥1 token con la oración del conteo; en cross:
sustantivo o continuación de la misma sección); el candidato rechazado NO se sustituye por
el siguiente (conservador). Casos reales pineados en tests (hp001 «2,4,6 u 8 lazos»·crumb NO
liga; cat007 tabla T1..T10 no dispara). **Validación fresca seed=275** (población nueva,
exclusiones acumuladas v1+s270..274, brazo det $0):
`evals/s271_stage1_v7_gate_v1.yaml` → **GO** — gates v6 íntegros verdes (los fixes no se
compran con recall: F-RANGE 1.0 / F-BUNDLE 0.826 / F-MANDATORY 1.0 / F-COUNT 0.952) + 3
checks nuevos (dup_span 0 FP/83 + control 0/30; empty_enum 0 FP/21 + positivo 0.90;
navcrumb 0 FP/19 + no-relevance 0 FP/21 + positivo 1.0). Iteración de instrumento declarada
en el prereg (display binding-guard sobre la VENTANA, clase seed-272). **Certificación
det-only v2** ($0, borradores almacenados del probe v3, drift de sha DECLARADO):
`evals/s271_probe_det_certification_v2.json` → **GO, b6f6 3/3 estable + 872c 3/3** (2
conversiones det-only, 0 regresiones, 0 conflictos). **Etapa 3 re-preparada**: mismo
`scripts/s270_etapa3_smoke_pareado.py` con `--fresh` (borra result+apéndices previos); la
re-ejecución la paga el orquestador. El flag `MUST_PRESERVE_CONTRACT` sigue OFF: la
activación queda gateada al re-smoke LIMPIO (DEC-127b).

**DEC-129b (S271) — revisión adversarial del Bloque A (sub-agente Fable, ronda fresca):
SÓLIDA con 2 hallazgos medios → AMBOS cableados antes del commit + residuales declarados.**
(1) El dedup por ratio≥0.90+mismos-números colapsaba hechos distintos SIN números
("cable de la sirena" vs "de la fuente", ratio 0.946) → apriete: el dedup exige además el
MISMO set de tokens de contenido (test pineado; mitiga también la circularidad del control
del harness — el control excluye pares por el mismo predicado, así que la clase queda
cubierta por test unitario, no por el gate). (2) Bypass del tie estricto: una fila
clave-valor de screenshot con el sustantivo como etiqueta («Lazos | 2 | 4») escapaba al
crumb por el dígito y el sustantivo la endosaba → screen nuevo `_block_is_value_row`
(celda puramente numérica = valores, no miembros) aplicado a los 3 ties (tests sección y
cross). Ambos apretes re-medidos EN FRÍO: cohorte v7 re-construida con el detector final
(misma seed 275) + re-run + gate → **GO idéntico** (familias 1.0/0.826/1.0/0.952; 19
checks verdes) y certificación det-only v2 re-corrida → **GO (b6f6 3/3 + 872c 3/3)**.
**Residuales DECLARADOS (no cableados):** (a) `informative_span` no caza la variante
etiquetas-en-cabecera + filas en blanco (indistinguible mecánicamente de una enumeración
legítima de una línea; falla hacia anexar etiquetas CON texto, no celdas vacías); (b) la
limitación REAL del mecanismo con etiquetas punteadas que truncan la ventana de cita →
TECH_DEBT #54 (el fix del display en el harness v7 era de INSTRUMENTO y queda declarado en
el prereg). (c) La spec opción-1 de 872c mide ACTIVACIÓN del disclosure (satisfacible
íntegramente por el apéndice determinista), no calidad de generación — no leer el 3/3 como
calidad. **Pendiente del orquestador:** el lado cross-model del dúo (GPT-5.6 Sol, pagado)
ANTES del merge — zona de dolor, el dúo es innegociable (Protocolo 3).

**DEC-130 (S271, iteración FINAL del Bloque A) — Etapa 3 v2 (monotonía 5/5, guards v4
funcionan: 0 duplicados / 0 span-vacío / 0 navcrumb) sacó 2 clases nuevas en cola larga →
INVERSIÓN DE CONTRATO en el render: de blacklist a WHITELIST fail-closed de forma-buena
(`must_preserve` v5, `atom_good_form`).** Clases observadas: (a) cat007 anexó un MANDATORY
que era SOLO la cabecera «### <ins>ADVERTENCIA</ins>»; (b) hp001 emparejó el conteo
«Lazos | 2» (match de RX_COUNT cruzando líneas) con un volcado de descripción de UI
multi-línea (el navcrumb-guard solo cubría líneas únicas). Whitelist por span: (1) cláusula
textual completa — ≥1 oración con verbo CONJUGADO (léxico cerrado ES/EN; infinitivos y
gerundios de volcados de UI NO cuentan) y ≥40 chars tras quitar markup/headers; O (2) fila
etiqueta+valor — número CON UNIDAD + etiqueta textual en la misma línea (número pelado NO
es valor: «Lazos | 2» y timestamps de headers quedan fuera — calibrado con los casos
observados). Headers/markers jamás cuentan; MANDATORY exige el trigger + SU oración;
BUNDLE exige ≥2 miembros con descripción; en un disclosure AMBOS lados individualmente o
no dispara. Silencio > ruido; los spans siguen VERBATIM (la whitelist decide inclusión, no
reescribe). **Validación fresca seed=276** (`evals/s271_stage1_v8_gate_v1.yaml`) → **GO**:
gates previos íntegros (F-RANGE 0.976 / F-BUNDLE 0.923 / F-MANDATORY 1.0 / F-COUNT 0.905;
cross_count 0.909; disclosure2 0.909) + clases nuevas (heading_only 0 FP/30 + control 1.0;
ui_dump 0 FP/16). **Coste de la whitelist VISIBLE, no escondido:** 208 filas re-etiquetadas
como silencio-por-diseño (`whitelist_skips_reported`: mutation 108 — F-COUNT 60 / MANDATORY
26 / BUNDLE 22 — sobre todo disclosures cuyo lado-enumeración es lista de nombres pelados;
share total 0.153 en `whitelist_silence_share_reported`); 2 iteraciones de instrumento
DECLARADAS en el prereg (cross_count sin filtro puntuable heredado de v5: 10/27→10/11;
coverage re-specced a salud-de-instrumento, 1ª pasada 0.807 en git). **Certificación
det-only v2 re-corrida → GO: b6f6 3/3 estable; 872c 2/3 ON / 0/3 OFF = conversión ESTABLE
se mantiene (≥2/3), con matiz declarado: era 3/3 pre-whitelist — la réplica 3 dependía SOLO
del disclosure de la tira-de-etiquetas (forma-pobre por definición) y ahora calla; r1/r2
convierten vía la tabla F2 (filas con cláusulas).** No se tuneó la whitelist contra los
targets. Si la Etapa 3 v3 aún muestra ruido, NO se itera más: la recomendación pasa a
activación restringida por familia (criterio del coordinador). Flag sigue OFF.

**DEC-130b (S271, adjudicación del ship-review Sol — 3 medios + 1 menor, 4/4 confirmados, 0 FP):**
(M1/M2) los claims quedan ACOTADOS: "2 conversiones estables" = certificadas en replays
congelados det-only (b6f6 3/3; 872c 2/3 ≥ regla); "0 ruido" = smoke vivo sin apéndices espurios
(el camino positivo vivo NO disparó en el smoke — 2 identity_unresolved + 1 sin citas — y se
ejercitará en la primera ventana con flag ON leyendo query_logs). El requires_human_read de la
cert quedó RESUELTO EN POSITIVO: el orquestador regeneró determinísticamente y LEYÓ el apéndice
872c post-whitelist — disclosure con la tabla real de 7 tipos de retardo, verbatim y citada,
calidad alta. (M3) el coste de la whitelist (15.3% skips) queda con TRIPWIRE declarado: si en
cohortes futuras el share supera 0.25, se re-examina la definición (no se gatea retroactivo).
(menor) TECH_DEBT #54 (etiquetas con puntos truncan citation_window): frecuencia real sin medir,
declarado como gap vivo del ON. Fable-side = SÓLIDA del build (2 medios cableados). El merge
default-off queda autorizado por el dúo; la activación en demo sigue el plan DEC-127b/130.

## DEC-131 (S272, 19 jul 2026) — BANKING de la foto 145/154 (94,16%) con recibo VIVO de producción + formato Telegram de la respuesta (feedback directo de Alberto)

**Decisión 1 — Banking.** Se cobran oficialmente las 2 conversiones certificadas del contrato
must-preserve sobre el funnel adjudicado (DEC-125: 143/9/2/154):
`scripts/s272_bank_conversions.py` (patrón S270: aritmética determinista, $0, insumos
SHA-pineados LF-normalizados, fail-closed ante drift) → **145 OK / 7 synth / 2 retr / 154
(94,16%) — quedan +6 para 151 (98%)**; artefacto `evals/s272_banked_funnel_v1.json` con
`production_flag: MUST_PRESERVE_CONTRACT=on (Railway, confirmado por Alberto)` y
`mecanismo verificado en producción: sí (query_logs 16:26Z)`.

**Estado vivo POR CONVERSIÓN (Alberto disparó las 3 preguntas en vivo; recibos GET-only de
query_logs 2026-07-19 persistidos con sha256 del response en
`evals/s272_live_receipts_v1.json` y dentro del artefacto — sin datos personales):**
- **obl_b6f6211be439 — FIRE EN VIVO ✓** (16:26Z, ASD535): apéndice con el aviso de
  seguridad + checklist servido en producción. Certificación: det-only v2 3/3
  (`evals/s271_probe_det_certification_v2.json`).
- **Control sano CAD-250 SIN apéndice ✓** (16:34Z): silencio correcto en vivo.
- **obl_872c35fb41d7 — NO disparó en vivo** (16:29Z, PEARL); DIAGNOSTICADO reproduciendo la
  ruta viva: los chunks del 997-671 p43-45 con la tabla de tipos quedan en posiciones 22-33
  del pool, FUERA del top-10 servido — el mecanismo no puede anexar átomos de fragmentos no
  servidos. **Clase: composición-de-serving (retrieval-side), NO fallo del contrato**; la
  conversión queda **harness-only** (la foto oficial usa la ruta harness congelada donde
  esos fragmentos SÍ se sirven; certificación `evals/s271_872c_respec_rescore_v1.json`,
  spec opción-1 DEC-128 3/3 ON / 0/3 OFF). Convergencia viva = lever retrieval de la misma
  familia que Bloque B/C — sin acción ahora. El banking se sostiene con esta declaración de
  alcance explícita, sin sobre-claim.

**Los 7 synth restantes por clase (mapa causal DEC-127):** serving-view `obl_0d6a` ·
uncited `obl_2f5d` · binding-tension `obl_7bba` · composites `obl_a5d9`/`obl_015f`/
`obl_b2043`/`obl_7aa7`. Sigue sin KPI atómico oficial (77 legacy carries, S205).
Alternativa descartada: esperar un re-score completo vía gold_store/assessment para cobrar —
el patrón de proyección determinista S133/S270 con certificaciones congeladas + recibo vivo
es exactamente la traza auditable que el re-score usaría; no se duplica el instrumento.

**Decisión 2 — Formato Telegram (v6 del anexo + formatter), del feedback directo de Alberto
sobre la respuesta viva ASD535 ("faltan saltos de línea incluso de sección, y podría ser más
visual"):** (a) `render_appendix` v6 (`src/rag/must_preserve.py`): separador `---` +
cabecera en negrita con UN emoji estructural por bloque (⚠️ si contiene átomo MANDATORY /
📋 disclosures-tablas / 📖 genérico) y strip del marcador blockquote `> ` de los spans con
guard conservador (nunca ante dígito/operador: `> 100 mA` se conserva) — la selección y el
binding NO cambian; los spans siguen byte-preservados en contenido técnico. (b)
`response_formatter.py`: fix del `**Fuente:**` del generador (el `**` de cierre tras los dos
puntos quedaba LITERAL en Telegram — el `**` visible que reportó Alberto), 📄 en fuentes,
🔧 en cabeceras de paso (`**1. …**` y headings numerados), negrita + línea en blanco para
secciones `##`/MAYÚSCULAS:, no-doble-emoji en avisos que ya traen ⚠️ (léxico ampliado con
importante/aviso/caution), y strip del `"> ` heredado en bullets de apéndices YA almacenados
(mismo guard numérico). Vara verificada con fixture del recibo vivo
(`tests/fixtures/s272_asd535_live_response.json`): 0 tokens numéricos/modelo perdidos, tags
balanceados, sin `**` ni `> ` crudos; gate local del renderer re-corrido
(`scripts/s124_renderer_presentation_replay.py` → GO). Alternativas descartadas: parse_mode
Markdown de Telegram (frágil con notación eléctrica, ya descartado en el diseño del
formatter); emojis por frase (decorativo — el criterio es sobrio/estructural); strip
incondicional de `> ` (riesgo de borrar un operador de comparación).

## DEC-132 (S273, 19 jul 2026) — Bloque B cerrado en esta sesión: cuota-enunciados F3 STOP as-preregistered + hallazgo de instrumento cuantificado + negcontrol PASS + prereg v3 (única re-medición) — flag default-off, restricción s105 intacta

**Contexto.** El diagnóstico s272 (`evals/s273_retrieval2_diagnosis_v1.md`) identificó los 2
retrieval-miss CORE residuales (cat017#2, hp010#1) muriendo en la fusión del canal enunciados.
Diseño + prereg v1 → dúo COMPLETO adjudicado (Sol xhigh 7/7 con 3 críticos, Fable 5/5
«SÓLIDO-con-condiciones», 0 FP; tally + reviews crudas en el log) → prereg v2 con los 11 fixes
→ build flag-off (`ENUNCIADOS_QUOTA_FUSION`, carve-out slots-reservados espejo hyq DEC-099 +
dedup-at-fusion/atomicidad S4 del prior art s105 @33977c1) → fases sin-DB.

**Resultados medidos (artefactos committeados).**
- **F0 (vía B, cat017#2): NO-GO → RESIDUAL FORMAL.** El activo h1 no contiene el hecho-licencia
  con señal: dump T2 de HOP-138-9ES no cubre el chunk carrier (0 filas pp.5-7, 0 «licencia» en
  925); brazo condicional 4188-1125-ES generado acotado ($0.10) → carrier rank-99-de-108 vs
  floor de cuota 0.614. F2 (recarga) deshabilitada; jamás corrió (rollback vacuo, DB en T1).
- **F1 (vía A, hp010#1): GO.** Consistencia s272 OK; rank-6-de-nuevos exacto → entra por cuota
  Q=6; e2e: rerank top-2 → SERVIDO (1 muestra, informativo).
- **F3 (Alberto): STOP TAL CUAL PRE-REGISTRADO** (`evals/s273_f3_closeout_v1.yaml`): anclas
  pareadas +3 (hp015#0, hp018#2, hp018#3) / −1 (hp017#1), stop-hits de la unión dura s104+s105
  = 0; containment 14-missing contra la referencia v2.2 → dispara; **negcontrol PASS** (4 ≤ 7);
  diana hp010 en pool 3/3. El gate NO se re-litiga; lever = NO-GO-as-preregistered bajo v2;
  el flag queda default-off (byte-inerte) y NO se shippea.
- **Hallazgo de INSTRUMENTO (cuantificado y reproducido desde los probes):** la referencia de
  containment v2.2 (foto s102) no describe el pipeline actual — OFF-hoy = 16 missing contra
  ella vs ON = 14; delta pareado atribuible a la cuota = −6 (hp005×2, hp006×1, hp011×1,
  cat020×2 — watch-golds tocados) / +8 recuperados. El pool no adjudica hechos: puede ser daño
  real o re-barajado benigno clase DEC-092b.

**Decisión.** (1) El STOP se acata sin re-litigio. (2) La corrección es de MEDICIÓN, no de
mecanismo → **prereg v3** (`evals/s273_quota_prereg_v3.yaml`, NO ejecutado, requiere GO):
containment pareado CONTEMPORÁNEO OFF-vs-ON K-mayoría (la referencia v2.2 se RETIRA con su
razón declarada), árbitro a nivel RESPUESTA para los watch-golds (hp005/hp006/hp017/cat020,
K=3, matcher determinista) + conversión hp010 como gate de ship; mismos umbrales de
anclas/negcontrol; techo $4; **anti-gate-shopping explícito: UNA sola re-medición — STOP a
nivel respuesta ⇒ lever CERRADO sin más intentos**. (3) Restricción heredada s105 INTACTA
(«no subir N ni tunear contra hp006»; Q=6 congelado; autoridad versionada en
`evals/s273_s105_authority_excerpt_v1.md`, colisión de numeración DEC-103..105 documentada en
el diseño §7). (4) cat017#2 residual formal: su única vía viva declarada = re-scope s174
per-facet, decisión explícita aparte (riesgo gate-shopping ya declarado en s269).

**Alternativas descartadas.** Re-litigar el STOP leyendo el neto +3/−1 como PASS (el gate era
+0/−0: se acata); «arreglar» el gate tras verlo fallar sin retirar la referencia con causa
documentada (eso sí sería gate-shopping — aquí la causa es reproducible: el control OFF falla
más que el tratamiento); recargar F2 pese al F0 NO-GO (el hecho no está en el espacio
enunciados-generable barato); tocar Q/barra/mecánica (cerrado por herencia s105 y por el
contrato v3).

**Traza.** Rama `claude/s273-bloqueB-quota` (PR contra main); artefactos
`evals/s273_*`; instrumento `scripts/s273_quota_gates.py`; gasto sesión fases ≈ $0.22 de $3
(v2) — v3 presupuestado $4, sin ejecutar.

## DEC-132b (S273, 19 jul 2026) — Veredicto FINAL del Bloque B: v3 ejecutado completo → v3b STOP a nivel respuesta → **lever cuota-enunciados CERRADO PERMANENTE** (anti-gate-shopping cumplido); 2 residuales documentados con precisión

**Cadena v3 (la única re-medición permitida, `evals/s273_v3_closeout_v1.yaml`):**
**v3a PASS** (containment pareado contemporáneo, reuse probes F3 mismo-día/K=3; stop_hits=0
sobre la unión dura; hp017#1 enrutada al árbitro; negcontrol PASS 4≤7) → **v3b STOP** (daño
REAL a nivel respuesta, 24 réplicas pareadas: hp005#2 «misma zona o subzona» 3/3-OFF→0/3-ON
y hp017#2 «Editar Configuración» 2/3→1/3, matcher determinista NFKD) → **v3c NO_GO**
(hp010#1 convierte ESTABLE 2/3 y pool 3/3 — el mecanismo funciona para su diana — pero el
gate compuesto exige v3b PASS).

**Decisión (por el anti-gate-shopping pre-registrado en el prereg v3):** lever
cuota-enunciados **CERRADO PERMANENTE**; flag `ENUNCIADOS_QUOTA_FUSION` default-off
(byte-inerte) sin ship; **sin más intentos** bajo ninguna variante de esta mecánica;
reapertura futura = evidencia NUEVA clase-s272 + permiso explícito de Alberto (patrón
DEC-126). Q=6/barra 0.40 jamás tuneados (herencia s105 cumplida de prereg a cierre).

**Residuales (con clase, para el PLAN):**
- **hp010#1**: el mecanismo CONVIERTE (pool 3/3, respuesta 2/3) — se cierra por su COSTE
  medido en terceros (hp005#2, hp017#2), no por fallar en su diana. Lever futuro para
  hp010#1 = OTRA familia mecánica, o demostrar 0-daño en el mismo árbitro pareado.
- **cat017#2**: fuera del espacio de enunciados generable barato (MEDIDO en F0: activo T2
  sin el carrier; h1 fresco del 2º carrier rank-99-de-108). Vía si se reabre: re-scope s174
  per-facet (decisión explícita aparte; riesgo gate-shopping declarado s269).

**Nota honesta.** La re-medición v3 CONFIRMÓ la esencia del veredicto s105 con instrumento
corregido: el desplazamiento de la cuota cuesta hechos reales incluso a T1 con Q=6 —
esta vez a nivel RESPUESTA y pareado mismo-día, no contra una referencia caduca. Corregir
el instrumento (hallazgo F3) cambió la CALIDAD de la evidencia, no el signo. «No subir N
ni tunear contra hp006» queda vigente y reforzado. Bloque B: 0 conversiones bancables; la
foto oficial 145/154 no cambia; el camino a 151 pasa por los Bloques C/D (síntesis).

**Traza.** Artefactos `evals/s273_v3*`; réplicas persistidas; runner
`scripts/s273_v3_arbiter.py`; fila nueva del lever en `docs/LEVER_DIGEST.md`.

**DEC-133 (S271) — Track visual COMPLETO: expansión del registro `document_visual_assets` al
corpus entero de chunks_v2 → 13.257 páginas servibles (antes 4.489), cap 2→4 + álbum; falta
solo `VISUAL_ASSETS_REGISTRY=on`.** Decisión de Alberto (S271): (a) cap 2→4 con orden de
relevancia PRE-DECLARADO (páginas de fragmentos más citados por refs `[Fn]` agregadas por
página; empate → orden de cita; >2 imágenes → UN media-group en Telegram, caption en la
primera, fail-open a fotos sueltas) y (b) backfill del 69% de páginas sin asset legacy.
**Cadena medida:** probe de cobertura $0 con BIND criptográfico sha256(PDF)==extraction_sha256
→ 813/816 docs verificados, 11.249/11.284 páginas renderizables, 0 not-found
(`evals/s271_pdf_coverage_v1.json`); pipeline por tramos (render local 170dpi JPEG q80 →
upload sha-verificado post-subida con x-upsert=false → INSERT idempotente `uncertain` →
clasificador HEREDADO v4 gpt-5.6-luna → apply-labels → gate); **piloto 509 págs GATE PASS
60/60** (1 flag adjudicado por el orquestador leyendo el render, clase DEC-092b;
`evals/s271_pilot_gate_v1.yaml`); **bug de colisión de naming cazado fail-closed** (mismo
source_file bajo 2 document_ids — revisiones s107 —, 50 pares en t11-notifier) → esquema
docid8 + saneador `--fix-collisions` (100 saneados, 0 en tramos ya subidos, 11.249 paths
únicos); clasificación completa 11.219 labels / 30 uncertain fail-closed, coste REAL $11,81
(recibos; techo $12, estimado $7,76 — desviación por re-runs de batches con fallo de
validación); **gate resto v1 NO-PASS 56/60** (plantillas-en-blanco ×2, frontmatter, prosa
sin figura; `evals/s271_resto_gate_v1.yaml`) → **filtro determinista de contenido**
(`scripts/s271_content_filter.py`: rejilla de celdas vacías ≥6 sobre texto de chunks_v2 +
low-density SOLO con corroboración de imagen bytes/píxel<0.05; umbrales a priori, anti-overfit
— los 2 FP que endurecieron señales salieron del propio dry-run verify-first, no de los 60
observados; 41 degradados, 2 de ellos coincidentes con los observados sin tunear) → **re-gate
v2 en muestra fresca (seed 271b, excluye observados+degradados) PASS 57/60 = 0.950, 0
covers** (`evals/s271_resto_gate_v2.yaml`). **Serving final verificado por GET: 13.257 =
4.484 bridge-v4 + 8.773 s271.** Alternativas descartadas: backfill ciego legacy→chunks
(NO-GO S190); contrato de clasificador nuevo (el heredado v4 ya está gateado — comparabilidad);
servir sin filtro tras el NO-PASS (violaría el gate); tunear filtro/plantillas sobre los
observados (anti-overfit — follow-ups DECLARADOS sin aplicar: TOC vía `is_toc_page` DEC-096 y
plantilla-con-leyenda EFS/EM, ambos gateados a muestra fresca futura). Residual: 3 docs con
extraction_sha ambiguo excluidos fail-closed (35 págs; dos revisiones bajo un document_id —
inverso del caso docid8; task chip abierto para separarlos patrón s107); 30 uncertain jamás
se sirven. Activación = solo `VISUAL_ASSETS_REGISTRY=on` en Railway (runbook en el PR S271).

## DEC-134 (S274, 20 jul 2026) — Bloques C/D cerrados: el par callout-card+verb-trigger convierte obl_0d6a (BANKED 146/154, 94,81%); C2 NO-GO por su clase en población fresca; los 6 synth restantes EXHAUSTOS en la familia mecanismo-de-anexo — el camino a 151 exige OTRA familia

**Decisión.** (a) BANKING +1: `obl_0d6a30948dfd` (hp017, bloque-warning mergeado DEC-125)
convertida por el PAR `COVERAGE_MANDATORY_CALLOUT`+`MP_MANDATORY_VERB_TRIGGER` — funnel
oficial **146 OK / 6 synth / 2 retr / 154 (94,81%)**, quedan +5 para 151
(`evals/s274_banked_funnel_v1.json`, aritmética SHA-pineada `scripts/s274_bank_conversions.py`,
patrón DEC-131). (b) Config de SHIP candidata = SOLO ese par en Railway (runbook 1 línea;
`MUST_PRESERVE_CONTRACT` ya on); los otros 5 flags s274 quedan default-off SIN ship (ninguna
conversión los justifica). (c) La familia MECANISMO-DE-ANEXO queda **EXHAUSTA para los 6
residuales** — cada uno tuvo fix construido (P0, 7 flags por-fix del dúo), gateado en población
fresca (P1 v9 seed-277) y medido en el probe consolidado #4 con brazos de ablación (P2) sin
conversión, o murió en P1 con métrica; sin probe #5 (compromiso anti-overfit del prereg v2).

**Cadena medida (techo $15, gastado $1,51; DB GET-only en todas las fases).**
P0 build flag-off + dúo (Sol 7/7 · Fable 5/5, 0 FP) → P1 Etapa-1 v9 (cohorte fresca seed-277,
112 filas, exclusiones acumuladas v1+seed-270..276): heredados v8 ÍNTEGROS **GO** con la config
det candidata + 6/7 fixes **GO** en sus clases nuevas; **C2/`MP_SERVED_BINDING` NO-GO**:
`served_uncited_clean_fp=24/105` — 26 anexos de HERMANOS genuinos / 1 target verificados
por-fila = la clase seed-270 re-medida FALLA incluso con umbral reforzado ≥3 → **DEC-127
REFORZADO** (el binding fuera de la ventana de cita compra ruido; 2ª reconfirmación con
métrica). Iteración de INSTRUMENTO declarada en el prereg v9 (evaluador cross_count v5
puntuaba solo cross[0]; paridad display 7-seg = exclusión por diseño; defline bullet-label) —
flag-independiente, el mecanismo no se tocó. → P2 probe #4 ($0,60): **A-C1 convierte 0d6a 3/3
vs 0/3 en A0** (pareado mismo-día, generación fresca hp017 K=3 con la vista C1) e idéntico en
A-ALL-det → banking DESPLEGABLE det-only (regla Sol-C1); **0 daño en todos los brazos**
(protegidas/conflictos/anclas s104+s105/retrieval-invariante/0-diagramas-por-anexo); el resto
de brazos 0/3 en sus dianas. → P3 smoke vivo con la config candidata: **5/5 monotónicos, 0
apéndices espurios** ($0,64).

**Los 6 exhaustos (qué fix y cómo murió):** 2f5d=C2 NO-GO P1 (clase seed-270 reconfirmada) ·
7bba=D2 GO en P1 pero sin el token distintivo en la ventana real (0/3) · a5d9=D1c+D1b GO en P1
pero Haiku no propone el qualifier (0/3, ya 0/3 en el funnel N=3) · 015f=D1a GO pero ventana
[F8] sin tokens del bundle (0/3, predicho BAJA) · b2043=serving-view SIN gatillo (span
definicional — la card C1 es de léxico MANDATORY; corrección v2.2 confirmada) ·
7aa7=F-RELATION shape OK pero ventana [F12] sin tokens propios (0/3). Detalle canónico en
`evals/s274_bloquesCD_closeout_v1.yaml` + `evals/s274_banked_funnel_v1.json`.

**Alternativas descartadas.** Probe #5 / iterar los fixes en caliente (anti-overfit
pre-registrado; 4º probe a los mismos targets ya era el límite) · relajar el gate de C2 para
"comprar" 2f5d (el gate FP=0 era EL control de la clase seed-270 — relajarlo re-litiga DEC-127
sin evidencia nueva) · shippear flags sin conversión (banking solo-desplegable, Sol-C1) ·
binding a nivel fragmento para 015f (rechazado con métrica seed-270, 36 FP). **Camino a 151
(otra familia; opciones para Alberto):** gold round-2 lente source-contract · serving-view
generalizada (clase C1 para spans no-MANDATORY) · eval orgánico como árbitro de si los 6
importan en uso real.

**Traza.** Prereg `evals/s274_bloquesCD_prereg_v2.yaml` (dúo adjudicado en
`evals/adversarial_review_log.jsonl`); gate P1 `evals/s274_stage1_v9_gate_v1.yaml`; probe
`evals/s274_probeCD_result_v1.json` (+réplicas); smoke `evals/s270_etapa3_smoke_result_v1.json`;
cierre `evals/s274_bloquesCD_closeout_v1.yaml`; fila del lever sobrescrita in-place en
`docs/LEVER_DIGEST.md`.

## DEC-135 (S275, 20 jul 2026) — Gold round-2 cerrada NO-GO sin reabrir S270; serving-view generalizada tiene un solo gap causal puro y no es vía demostrada a +5

**Gold round-2.** Se construyeron dos diseños source-contract, pero no se ejecutó ninguna
adjudicación de casos. El dúo obligatorio Sol 5.6 xhigh + Fable 5 dio NO-GO a ambos y la
regla C confirmó 20/20 hallazgos, 0 falsos positivos. V1 rompía el cegado al permitir tools
repo-wide, colapsaba buckets E1, dejaba crédito E3 post hoc y volvía a preguntar requiredness
ya decidido en S270. V2 cerró esos grados de libertad, pero reveló el bloqueo de autoridad:
la ausencia de un átomo TONE explícito en `gold_answers_v1.yaml` puede ser deuda de
sincronización posterior a S270, no evidencia nueva para revertir el ❌ de Alberto al demote
de `obl_015f`; la topología input+output de hp017 también era visible cuando Alberto aceptó
por separado `b2043` y `7aa7`. Además, controles E1/E3 no estaban todos congelados sobre la
misma respuesta/estado banked. **Decisión:** no hay v3, cero edición de gold, cero cambio de
denominador y el funnel permanece **146/154 (94,81 %), gap +5**. Traza:
`evals/s275_gold_round2_closeout_v1.yaml` y los dos pares design/prereg/reviews en S275.

**Reach audit de serving-view.** Un instrumento local SHA-pineado comparó los spans exactos
S235 con la vista S113: `2f5d`, `7bba`, `a5d9` y `015f` estaban servidos al 100 %; `7aa7`
estaba al 86,68 %, pero la parte servida ya contenía los tres anchors evaluados; solo
`b2043` estaba al 0 %, íntegramente en el hueco entre cards de F12. Esto corrige el framing
«serving-view para los seis»: **solo `b2043` es gap puro de vista**; los demás son
cita/binding/detección/selección ya medidos en DEC-134. Candidato permitido: field-card propio,
default-off, exacto y rederivable, que sirva como máximo un hermano definicional omitido
(≤600 chars) cuando otro hermano homogéneo del mismo bloque ya esté validado; planner ciego,
paridad writer/must-preserve y jamás chunk completo.

**Siguiente gate.** Solo screen offline fresco seed-278, con exclusiones acumuladas, receipt
100 %, flag-off byte-idéntico y 0 expansiones a elementos ajenos al registro. El probe #5
sobre los mismos targets sigue prohibido. Si el screen pasa, cualquier medición de modelos
será A/B orgánico/disjunto con autorización separada (~USD 10); incluso convirtiendo el único
caso causal aún faltarían +4. Artefactos:
`scripts/s275_serving_view_reach_preflight.py`,
`evals/s275_serving_view_reach_preflight_v1.json` y
`evals/s275_serving_view_generalization_preflight_v1.md`.

## DEC-136 (S276, 20 jul 2026) — Seed-278 cierra NO-GO; norte conversacional acotado sin autorización de build; recovery fail-closed para el cierre vacío de Fable

**Impacto.** Medio/alto de evaluación y arquitectura futura; impacto productivo actual nulo. No
se modifican runtime, schema, flags, Railway, golds, denominador ni funnel.

**Contexto y evidencia.** El screen GET-only seed-278 recorrió 80 documentos seleccionados y
1.033 fragmentos, sin modelos ni escrituras DB. Encontró 67 bloques en 24 documentos y rederivó
67/67 en full y truncado, pero el gate preregistrado falló: 2 fabricantes < mínimo 3. La revisión
posterior mostró además 41/67 candidatos en descripciones visuales/UI y 20/67 concentrados en un
documento. El dúo Sol `2026-07-20T09:29:35` + Fable `2026-07-20T09:44:22`, adjudicado por regla C
en `evals/adversarial_review_log.jsonl`, confirmó 8 findings únicos/8, 0 FP, severidad máxima
media (`evals/s276_duo_adjudication_v1.yaml`): el 67/67 es autoconsistencia del parser; los
boundary controls son sintéticos; la cronología completa del freeze no quedó atestada; y el gate
de docs no mide literalmente fetches no vacíos. Ninguno cambia el gate mecánico fallido.

**Decisión 1 — screen.** `NO_GO_OFFLINE_SCREEN` definitivo para esta población. No se construye
la card en runtime, no se paga A/B, no hay crédito al funnel y seed-278 queda consumido. Reabrir
la familia exige semilla nueva, exclusión visual/UI, control de dominancia documental, labels o
parser independiente para cualquier claim de recall, conteos selected/with-fragments/screened y
freeze fail-closed de builder, corpus, exclusiones y hashes previos. El alcance causal conocido
sigue siendo 1/6; no se autoriza probe #5.

**Decisión 2 — dirección multi-turn/multi-hop, no build.** El norte es un orquestador
transport-neutral y acotado: single-hop por defecto; event log/working state/snapshots versionados;
ingress deduplicado; `turn_runs` reclaimable con lease/heartbeat y fencing token monotónico;
orden/CAS por conversación; CAS del intento propietario al completar + outbox unique por entrega
lógica + delivery attempts/receipts con objetivo effectively-once; rewrite sólo en
follow-ups dependientes; multi-hop con 2 hops por defecto y 3 hard cap; una redacción final; y
verifier condicional que inicialmente sólo `accept | clarify | disclose | abstain`. Un repair
futuro se reconoce como segundo writer pass, vive en fase separada y exige merge determinista,
conflictos y revalidación full-answer. Antes de DDL se exige lifecycle RGPD de retención,
minimización y propagación de borrado/anonimización a eventos, derivados, logs, outbox, caches,
colas, backups y proveedores, revisado con legal/DPO. Status:
`DIRECTIONAL_BLUEPRINT_NO_BUILD_AUTHORIZATION`.

**Decisión 3 — incidente Fable.** Tres ejecuciones auditadas terminaron `end_turn` sin texto
visible después de tools: dos payloads persistidos contenían `thinking` + un bloque `text` vacío
y el tercero `content=[]`; un run no-tools truncó por `max_tokens`. Esto descarta que el vacío
naciera en la extracción/normalización local, pero **no identifica la causa raíz interna del
modelo/proveedor**, que queda abierta. El runner ya fallaba cerrado y conservaba los traces, pero
obligaba a reintentos completos y costosos. Se añade una única recuperación interna del síntoma:
**no** reinyecta el assistant vacío, añade un segundo turno user
(forma admitida por Messages API), fuerza tools-off, conserva la respuesta vacía en el trace y
sólo acepta `tool_use* → como máximo un end_turn vacío inmediatamente penúltimo → end_turn final
no vacío y sin tool_use`. La cota incluye schemas de tools; inputs no-objeto, segundo vacío y
`max_tokens` siguen fail-closed. Contrato vivo: assistant vacío = HTTP 400; dos user consecutivos
= request aceptado. El trace demuestra autoconsistencia byte-bound de lo persistido, no
attestation independiente de completitud ni explicación causal del comportamiento upstream.
Tests dirigidos previos al cierre final: 56 del runner + 14 del screen.

**Alternativas descartadas.** Más contexto/top-k universal; checklist genérico S206; múltiples
writers/descomposición S216/S235; agente abierto; GraphRAG ahora; embedding del transcript entero;
Redis day-one; exactly-once prometido sobre Telegram; repair silencioso; relajar el gate de
fabricantes; retocar post-hoc seed-278; y retry automático de `max_tokens`.

**Revisión adversarial y estado.** El subject original queda
`complete_adjudicated_no_pass` porque las ocho observaciones eran válidas, aunque no alteran el
NO-GO. Outputs físicos:
`evals/adversarial_reviews/2026-07-20T09-29-35_gpt-5.6-sol_2766ebf454d4.md` y
`evals/adversarial_reviews/2026-07-20T09-44-22_claude-fable-5_f054af1576d1.md`; adjudicación:
`scripts/s276_adjudicate_adversarial_review.py`. El dúo de correcciones (Sol
`2026-07-20T10:06:50` + Fable `2026-07-20T10:09:26`) confirmó 8 findings únicos, 0 FP, máximo
crítico; reveló el assistant vacío inoperante y los guards anteriores. Su subject incluyó por
error la adjudicación previa, por lo que queda `complete_adjudicated_no_pass` y **no** se vende
como PASS independiente. Trazas y fixes:
`evals/s276_corrections_duo_adjudication_v1.yaml` y
`scripts/s276_adjudicate_corrections_review.py`. Las correcciones no autorizan ejecución: la
próxima decisión humana es eval orgánico/fresco y/o Fase 0 conversacional en shadow.

## DEC-137 (S277, 20 jul 2026) — La observación viva mantiene C1 NO-GO; profile atómico + P1 end-to-end quedan materializados offline, sin autorización de gasto ni deploy

**Impacto y métrica visible.** Alto en release integrity y evaluación; impacto productivo de
este cambio todavía nulo. El objetivo de hoy sigue siendo 151/154 (≥98 %) y el marcador no se
mueve: **146/154 (94,81 %), gap +5; 6 synthesis-miss + 2 retrieval-miss**. El +1 de S274 fue
3/3 en su probe pareado; no era evidencia de que la respuesta viva o el profile completo pasaran.
P1 usa la misma cohorte dev para proteger el release y no convierte esa métrica en un KPI orgánico.

**Evidencia que cambia el estado.** La respuesta PEARL aportada por Alberto fue una única
generación de 4.449 caracteres, dividida por Telegram en dos mensajes. Omitió los dos avisos F12
y presentó como instrucción plana el menú `8`, sin revelar el conflicto fuente conocido 7-vs-8.
El log persiste como máximo 4.096 caracteres y no puede reconstruir por sí solo la respuesta
completa. El gate A reproduce offline el ensamblaje C1 y el probe B GET-only alcanza el target en
F12 desde el prefijo congelado, pero ninguno atraviesa síntesis; por eso el release queda NO-GO.

**Decisión 1 — unidad de release estructural.** Los cuatro switches acoplados pasan a un único
profile `coverage_c1_v1`; fuera de `legacy` no se admiten overrides parciales. Un seam de serving
único produce la vista consumida por harness y Telegram, y una traza privacy-safe registra profile,
pool/prefijo/contexto, coverage, must-preserve, renderer y truncamientos. El rollout arranca en
profile `off` y sólo cambia al target tras identidad exacta. Las capacidades ortogonales ya vivas
—incluido `VISUAL_ASSETS_REGISTRY`— se proyectan y preservan exactamente; apagarlas para aislar C1
sería una regresión de configuración, no una simplificación permitida.

**Decisión 2 — P1 prerelease, no ejecución.** Se preregistran 13 QIDs y 27 réplicas independientes
(27 generaciones; exactamente 81 llamadas pagables: embedding + rerank + síntesis). El fact
contract contiene 43 filas base de peso KPI 42, una guarda hp013 y el target compuesto hp017. El
bound estático es 6,777 USD bajo los envelopes/tamaños sellados y el techo duro 10 USD. El runner
offline implementa doble opt-in, WAL fsync sin retry, reserva/coste por llamada, identidad Git/
runtime/config, proyección semántica, fingerprint y fence externo, receipts encadenados desde input
preregistrado hasta respuesta/render, scorer determinista y re-score autoritativo en `finalize`.
`P1_PASS` sólo puede significar `NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS`, nunca `ZERO_REGRESSION`.

La auditoría post-integración endureció esa reapertura: el genesis sella modelos, inputs,
presupuesto e implementation hashes; resume/score/finalize reabren 81 responses y 81 watches,
vuelven a validar las 27 réplicas y reconstruyen los 81 envelopes. El WAL completo debe contener
exactamente 162 eventos reserve/completed alternos; modelo, usage, max-cost, acumulado previo,
coste observado y `result.budget` se recomputan contra el plan de 81 llamadas. La suite P1 focal
queda en **181/181** antes del dúo final.

**Control gratuito y stop-line.** El re-score conflict-only de las tres respuestas A-C1 ya
almacenadas confirma 3/3 el menú plano y emite `HOLD_PREPAID_KNOWN_CONFLICT_RISK`; no mide el
candidato y no le atribuye PASS ni FAIL. La ruta recomendada es resolver/atribuir el conflicto
antes de pagar. Medir pese al prior exigiría un permit nuevo que lo acepte expresamente.

**Qué parte es BP y qué parte no generaliza todavía.** El patrón de seguridad sí es estructural:
profile atómico, least-privilege read-only, snapshot/fence de corpus, reservas de presupuesto,
no-double-send, receipts y fail-closed. El packet/scorer P1, en cambio, es deliberadamente
cohort-specific y contiene QIDs, surfaces y algoritmos especiales mantenidos a mano; no se presenta
como arquitectura multi-marca escalable. La configuración efectiva tampoco está completa hasta que
el adapter/config externo materialice, entre otros, `ANSWER_OBLIGATION_PLANNER`,
`GENERATOR_INCLUDE_CONTEXT` e `IDENTITY_FETCH`. Generalizar facts tipados o multi-turn/multi-hop es
un frente posterior y no se acredita con este gate.

**Alternativas descartadas.** `query_logs` como árbitro (texto truncado y sin átomos); sólo replay
S113 (no prueba retrieval/rerank live); una réplica o mayoría permisiva (no satisface protección
absoluta de esta cohorte); `test_bot_vs_gold.py` informal (sin WAL/coste/fence); clonar Supabase o
restaurar un dump local ahora (infraestructura/índice no equivalente); apagar visuales u otras
lanes ortogonales (mide otra configuración); y ejecutar primero para «ver qué pasa» (gasto con
conflicto conocido y artefactos todavía no autorizados).

**Gaps y límites declarados.** El release-config real aún no está materializado; faltan adapter
productivo revisado, identidad PostgREST `p1_readonly`, proceso de fence/operador y receipts
externos. Los hashes actuales de RPC/GET/relaciones son sólo un contrato de superficie sintético,
no observan firmas/ACL/overloads, índices ni PostgREST/config live. En vez de inventar ese manifest,
los CLI `fence-open-verify`, `fence-close-verify`, `run` y `finalize` devuelven como primera operación
`HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`. Retirarlo exige bodies live pre/watch/post y un
contrato esperado canónico revisado. La ejecución pagada y el canary post-activación requieren
autorizaciones separadas. La
cohorte es conocida/dev, cubre sólo los 13 QIDs afectados y no demuestra 98 %, tasa global de
regresión cero ni comportamiento orgánico. El trust boundary de los artefactos es un operador/
workspace autorizado; no es una attestation criptográfica de un tercero.

**Revisión y trazabilidad.** El diseño pasó dos dúos frescos Sol 5.6 xhigh + Fable 5
(`2026-07-20T16:32:35` y `17:04:06`), ambos `complete_adjudicated_no_pass`: 12 findings
confirmados y 5 falsos positivos entre rondas; las correcciones se incorporaron antes del build.
La auditoría de integración añadió los bindings de score, payload físico, configuración, coste,
WAL/reapertura y fence; también rebajó correctamente los hashes nominales a superficie declarada
y añadió la stop-line machine-enforced del manifest live. El dúo final de implementación
(`2026-07-21T00:06:50` Sol / `00:08:56` Fable) mantuvo cerrados los dos false-PASS semánticos,
pero confirmó que el manifest de implementation hashes no es transitivamente completo: omite al
menos `src/rag/answer_planner.py`, ejecutado por el scorer de conflicto. También dejó como
precondiciones del adapter real el stop reason terminal de rerank y la attestation externa de
usage/coste. Por el corte anti-parálisis no se abrió otra ronda: veredicto `SAFE_HOLD_NO_GO`, con
0 llamadas P1 y 0 mutaciones externas. Artefactos canónicos: `evals/s277_c1_p1_design_v1.md`,
`evals/s277_c1_p1_prereg_v1.yaml`, `evals/s277_c1_p1_fact_contract_v1.json`,
`scripts/s277_c1_p1.py`, `scripts/s277_c1_p1_scorer.py` y `docs/C1_RELEASE_RUNBOOK.md`.

## DEC-138 (S277, 21 jul 2026) — P1 pasa de SAFE HOLD de implementación a `CODE_READY`; el GO sigue pendiente de autorización, provisioning y ejecución real

**Impacto y estado visible.** Alto en integridad de release; impacto productivo todavía nulo.
Se cierran los blockers técnicos concretos que impedían siquiera ejecutar P1, pero no se cambia
el veredicto del candidato: **no existe `P1_PASS` ni GO operativo**. No se aplicó ninguna
migración, no hubo llamadas pagadas, cambio de Railway ni deploy. El marcador permanece
**146/154 (94,81 %), gap +5; 6 synthesis-miss + 2 retrieval-miss**. P1 sigue siendo un gate de
release sobre cohorte dev, no el mecanismo ni el árbitro que mueve el objetivo ≥98 %.

**Decisión 1 — closure ejecutable completo.** La implementación incorpora el adapter del path
productivo y liga los bytes/receipts físicos de embedding, rerank y síntesis a cada réplica;
rechaza terminaciones inválidas y revalida usage/modelo/coste. El manifest de implementación
cubre el cierre transitivo exacto de runner, scorer y módulos productivos ejecutados. Railway se
captura y revalida read-only contra los IDs canónicos y una proyección sin secretos. El manifest
live observa y compara pre/watch/post las definiciones y firmas RPC, volatility, `prosecdef`,
owner/ACL/overloads, índices/opclasses/dimensiones, relaciones/RLS, extensiones, roles y
PostgREST/config.

**Decisión 2 — ventana live y separación de deberes.** Un operador separado conserva una sesión
PostgreSQL persistente `READ ONLY`, adquiere los locks en orden, calcula el fingerprint y mantiene
heartbeats/watchers. El runner no recibe su DSN: usa IPC credential-free para `open`, watch,
`close` y `abort`. Todo fallo posterior a `open` solicita aborto explícito; sólo un rollback
confirmado produce receipt `ABORTED`, y la incertidumbre queda `AMBIGUOUS`. El guard PostgREST
acepta únicamente host, GET/RPC y JWT exactos del contrato; bloquea escrituras de tabla, RPC fuera
de allowlist, redirects y destinos ajenos. El executor revalida Railway, identidad y inputs live,
abre la ventana, ejecuta las 27 réplicas, captura el estado posterior y cierra o aborta; aun con
réplicas completas termina pendiente de `score`/`finalize`, nunca inventa un PASS.

La revisión bloqueante final cerró tres bordes del mismo protocolo: el `session_id` se
preasigna antes de adquirir locks para poder emitir un aborto ligado aunque se pierda la
respuesta de `open`; `artifact_dir` debe empezar vacío y ser disjunto del fichero de
credenciales y del IPC; y el receipt de `close` sella el hash del manifest post capturado bajo
el fence. Ninguno se pospone como hardening posterior.

**Corrección P0 — qué significa realmente read-only.** `transaction_read_only=on` en
`p1_runtime_identity_v1()` demuestra sólo la transacción del GET de identidad. No acredita los
POST `/rpc/...`: PostgREST elige su modo de transacción por separado y las funciones de retrieval
vigentes no se reclasifican artificialmente como `STABLE`. La seguridad efectiva de P1 procede de
la conjunción de (a) ACL/RLS mínimos del rol `p1_readonly`, (b) allowlist exacta del guard y (c)
ninguna función `SECURITY DEFINER` accesible al rol. La migración
`20260721120000_add_p1_readonly_role.sql` materializa y verifica ese contrato, incluida la
revocación del `EXECUTE` público observado sobre `create_hnsw_index()`. Está revisada pero **no
aplicada**; no se emite el JWT antes de que sus postcondiciones pasen.

**Decisión 3 — único siguiente paso, acotado.** El estado canónico es
`CODE_READY_OPERATIONAL_AUTHORIZATION_PENDING`. Con autorización explícita: (1) aplicar la
migración del rol y verificar postcondiciones; (2) provisionar fuera del checkout el PAT de
Supabase, un JWT efímero `p1_readonly` y la credencial PostgreSQL del operador; (3) materializar
release-config, manifest/evidencia live y un receipt que disponga expresamente el prior hp017;
(4) ejecutar una sola P1 preregistrada bajo el techo duro de 10 USD; y (5) cerrar/abortar el fence,
puntuar y finalizar. Sólo un `P1_PASS` vigente abre una autorización separada de merge/deploy y
canary. Credenciales presentes, código verde o un `run` completado sin `finalize` no equivalen a
GO.

**Límites conservados.** El lease de artefactos sigue siendo single-host y no se autoreclama;
la cohorte sigue siendo conocida/dev; el prior hp017 7-vs-8 debe constar en el permit; no se
promete regresión global cero. Multi-turn/multi-hop permanece `NOT_BUILT` y fuera de este release:
su arquitectura durable/transport-neutral conserva el roadmap de DEC-136 y exige autorización
propia.

## DEC-139 (S277, 21 jul 2026) — Se autoriza una única P1 exacta; el release continúa NO-GO hasta completar sus prerrequisitos y obtener `P1_PASS`

**Decisión humana y alcance.** Alberto autoriza una única ejecución preregistrada P1 de
27 réplicas/27 generaciones y exactamente 81 llamadas pagables —embedding, rerank y síntesis—,
con techo duro de 10 USD y aceptación expresa del prior hp017 documentado. Esta decisión no
autoriza merge, deploy, cambios de Railway ni canary. En el momento de registrarla siguen en cero
las llamadas P1 pagadas y no se atribuye ningún resultado.

**Prerrequisitos de seguridad.** Antes de emitir el bearer debe aplicarse y verificarse
`20260721120000_add_p1_readonly_role.sql`. En PostgreSQL 17 la membresía exacta sobre
`p1_readonly` son tres filas no heredables: `authenticator <- postgres: SET TRUE/ADMIN FALSE`,
`postgres <- postgres: SET TRUE/ADMIN FALSE` y el grant automático
`postgres <- supabase_admin: SET FALSE/ADMIN TRUE`; ACL/RLS mínimos, allowlist RPC y ausencia de
`SECURITY DEFINER` accesible siguen siendo condiciones conjuntas. La autenticación HTTP también
separa credenciales: `SUPABASE_KEY` alimenta `apikey`, mientras `P1_SUPABASE_JWT` alimenta
`Authorization: Bearer ...`; ninguna sustituye a la otra.

**Operación y estado.** Las herramientas Python se invocan desde la raíz como módulos
(`python -m scripts...`). Aún faltan aplicar/verificar la migración, provisionar fuera del checkout
PAT, API key, bearer y credencial del operador, capturar los inputs live, materializar el receipt
de autorización y ejecutar `run`, `score` y `finalize`. Por tanto el estado pasa de autorización
pendiente a `P1_EXECUTION_AUTHORIZED_OPERATIONAL_PREREQUISITES_PENDING`, pero permanece **NO-GO**:
sólo un `P1_PASS` sellado y vigente puede abrir una decisión posterior y separada de release.

## DEC-140 (S277, 21 jul 2026) — La migración mínima P1 queda aplicada y verificada; credenciales y ejecución siguen pendientes

**Cambio externo y evidencia.** Se aplicó en producción la migración
`20260721120000_add_p1_readonly_role.sql`, con SHA-256
`b698a69cc6fba48b7f1e3e6f78bf80c4327d6118878e1f0f15317420501a83a4`. Sus
postcondiciones verificaron los tres grants no heredables exactos de PostgreSQL 17
—`authenticator <- postgres` con `SET TRUE/ADMIN FALSE`, `postgres <- postgres` con
`SET TRUE/ADMIN FALSE` y `postgres <- supabase_admin` con `SET FALSE/ADMIN TRUE`—,
las ACL de tablas P1 `SELECT`-only, la identidad runtime aislada y un receipt live de
`SET ROLE p1_readonly`. La aplicación no ejecutó llamadas a modelos ni implicó merge,
deploy o cambio de Railway.

**Estado operativo.** `SUPABASE_KEY` y la credencial PostgreSQL del operador existen fuera
del candidato. El PAT de Supabase está provisionado de forma efímera fuera del checkout;
aún faltan el bearer efímero `P1_SUPABASE_JWT`, los inputs
live y `run`/`score`/`finalize`; siguen en cero las 27 réplicas y 81 llamadas autorizadas y no
existe `P1_PASS`. El estado canónico es por tanto
`P1_MIGRATION_VERIFIED_CREDENTIALS_PENDING`, todavía **NO-GO**.

**Riesgo separado antes del GO final.** La migración revocó `EXECUTE` de `PUBLIC` sobre
`create_hnsw_index()` y `p1_readonly` no alcanza esa función; el Advisor conserva, sin embargo,
avisos por grants explícitos preexistentes de `anon` y `authenticated`. No bloquean la identidad
mínima ni la ejecución acotada de P1, pero deben inventariarse, probarse y corregirse mediante
otra migración con autorización separada antes del GO final de C1. DEC-140 no amplía la
autorización a ese cambio, merge, deploy o canary.

## DEC-141 (S277, 21 jul 2026) — La única P1 cierra NO-GO parcial por atestación tardía del SDK; el fix requiere autorización y run nuevos

**Resultado autoritativo.** La P1 autorizada se ejecutó como
`p1-22bfc29e520b4002b3c4b9def2b63cdb` sobre el commit `537152a`. El fence abrió
`OPEN_VERIFIED`, pero la primera llamada planificada (`hp017:r1:embedding`) terminó
`UNKNOWN_BILLED_POST_SEND` con `HOLD_PROVIDER_SDK_VERSION`. El run quedó
`NO_GO_PARTIAL`: 0/27 réplicas, coste observado 0 USD y reserva conservadora máxima de
0,001 USD. No hubo retry. El manifest live conservó el mismo hash semántico pre/post
`68fd9a89d6c57a2879ba9ec7b33b13757831faaadde75277357b49698619da65`; los
fingerprints inicial/final fueron idénticos, el fence cerró `CLOSED_VERIFIED` y Railway y
Supabase registraron cero mutaciones. `score` devolvió `HOLD_RUN_INCOMPLETE`, por lo que no
se ejecuta `finalize` ni existe `P1_PASS`.

**Causa raíz.** El runtime tenía la distribución correcta `voyageai==0.2.4`, pero ese
release publica el valor interno obsoleto `voyageai.__version__ == 0.2.3`. `prepare` ya
atestaba correctamente la metadata de distribución 0.2.4; `_send_voyage` repetía después
una comprobación incorrecta del valor interno. Al ocurrir tras cruzar la frontera local de
delegación, el WAL debía clasificarla de forma conservadora como posiblemente facturada,
aunque el fallo sucede antes de crear el cliente o emitir HTTP.

**Corrección estructural.** `c2079e9` convierte la metadata instalada de distribución en
la única autoridad de versión, mueve imports y comprobaciones de capacidad al `prepare`
local y elimina las comprobaciones tardías de `__version__` tanto en Voyage como en
Anthropic. Así cualquier incompatibilidad estática se clasifica antes del send, y el receipt
sigue ligando la versión exacta del paquete. Pasan 39 pruebas focales, incluida la regresión
explícita `distribución=0.2.4 / módulo=0.2.3`.

**Decisión y límites.** La autorización de DEC-139 está consumida y el WAL terminal no se
reanuda ni se reintenta. El fix no convierte el run anterior en PASS y todavía no está medido.
Otra P1 exige autorización humana nueva, checkout detached de `c2079e9` o descendiente exacto,
credenciales/inputs/recibo nuevos y un artifact root vacío. Hasta entonces C1 permanece
`P1_NO_GO_PARTIAL_PROVIDER_SDK_FIXED_REAUTH_REQUIRED`; merge, deploy y canary siguen fuera de
alcance. El riesgo separado de `create_hnsw_index()` continúa pendiente antes de un GO final.

## DEC-142 (S277, 21 jul 2026) — La segunda P1 aísla un bound pre-WAL; el contrato se alinea al techo humano de 30 USD

**Resultado autoritativo.** La segunda autorización materializada cubrió una única P1 de
27 réplicas/81 llamadas sobre `e49cb73`, sin merge, deploy ni canary. El run
`p1-33d94efd57d84328aafbbdb4f052831d` completó `hp017:r1:embedding` y terminó
`NO_GO_PARTIAL` antes de reservar el rerank: 0/27 réplicas, una llamada Voyage completada,
coste observado 0,0000024 USD, cero reserva desconocida y cero mutaciones. El fence cerró
`CLOSED_VERIFIED`; corpus, manifest y fingerprint permanecieron idénticos. La autorización y
el run son terminales; `score` devolvió `HOLD_RUN_INCOMPLETE` y no existe `P1_PASS`.

**Causa exacta, sin nueva inferencia pagada.** Un replay read-only reutilizó el embedding ya
cobrado, recorrió el mismo retrieval con el JWT `p1_readonly` y capturó localmente el envelope
sin llamar a Anthropic. El pool tenía 43 filas, 41 previews completos de 800 caracteres y
34.192 caracteres de preview. El payload canónico medía 40.220 bytes; con la reserva fija de
512, el bound declarado era **40.732**, frente al máximo preregistrado **10.000**. El verificador
reprodujo exactamente `HOLD_INPUT_TOKEN_BOUND`. El código genérico adicional era instrumental:
el reranker strict envolvía el `P1Error` pre-WAL como `RerankStrictError` porque el router solo
preservaba errores posteriores a una respuesta de proveedor.

**Corrección estructural y presupuesto.** El router preserva ahora cualquier `P1Error` de
hook, coerción o validación, de modo que un fallo local conserva su código estable. El contrato
no cambia retrieval, rerank, síntesis ni modelos; amplía únicamente los bounds conservadores a
95.000 para rerank y 249.000 para síntesis. Sus reservas pasan a 0,30 y 0,80 USD por operación;
con embedding, el worst-case de las 81 llamadas es **29,727 USD**, inferior al techo duro humano
de **30 USD** expresamente fijado por Alberto. El caso reproducido queda cubierto con margen
2,33× y las pruebas de regresión verifican tanto el envelope completo como la propagación del
error pre-WAL.

**Decisión y siguiente paso.** El fix offline no convierte ninguno de los runs anteriores en
PASS. Otra P1 requiere autorización humana nueva y explícita, checkout detached del commit del
fix, credenciales/inputs/recibo nuevos y artifact root vacío. Hasta entonces C1 permanece
`P1_NO_GO_PARTIAL_RERANK_BOUND_FIXED_REAUTH_REQUIRED`; el marcador sigue 146/154 y merge,
deploy, canary y la arquitectura multi-turn/multi-hop permanecen fuera de este permiso.

## DEC-143 (S277, 21 jul 2026) — La tercera P1 separa un falso FAIL del miss real de autoridad y no se repite sin source recovery

**Resultado autoritativo.** La P1 sobre `b06f05c`, run
`p1-8c7818cce1174f1ea0538028693ee515`, terminó `NO_GO_PARTIAL /
NO_GO_PROTECTED_CONTRACT` tras persistir 18/27 réplicas y completar 54/81 llamadas. El coste
observado fue 1,82090244 USD, con cero reserva desconocida y cero mutaciones Railway/Supabase.
El fence cerró `CLOSED_VERIFIED`; manifest y fingerprint pre/post fueron idénticos. El run es
terminal y no existe `P1_PASS`.

**Defecto instrumental corregido sin repetir inferencia.** El scorer de hp011 consideraba
cualquier substring `--` como el estado técnico de `r.I`. Los separadores Markdown `---` de la
respuesta activaron por error la exigencia de `t.A` y produjeron un FAIL falso. La detección queda
limitada a un token técnico inequívoco —citado, tabular, asignado o en contexto local de estado—
y excluye reglas Markdown, runs más largos, `--help` y guiones de prosa. El replay del artefacto
inmutable cambia el FAIL a REVIEW; no exige ni justifica volver a pagar las 18 réplicas existentes.

**Bloqueo real y decisión.** El REVIEW reveló que la página 63 del manual autoritativo
`HLSI-MN-103_RP1r-Supra_lr`, que liga `-- ↔ t.A`, `00 = rearme permitido/default` y
`01–30 = inhibición`, no estaba en retrieval pool, prefijo de rerank, structural fetch ni contexto
servido. F9 era una guía rápida incompleta y la respuesta generada afirmó erróneamente que `00`
inhibe el rearme. Los probes GET-only de pool coverage e HYQ existentes tampoco recuperaron la
autoridad. Por tanto se prohíbe otra P1 por variación: antes debe pasar una prueba offline/GET-only
de recuperación intra-documento genérica, limitada y fail-closed, sin reglas por QID/manual ni
resucitar pilotos previamente NO-GO. Los 18 artefactos se conservan para diagnóstico; un GO
posterior requiere un run limpio porque el código sellado cambiará y faltan nueve réplicas.

**Descubrimiento de autoridad posterior, que precede al source recovery.** El corpus contiene dos
revisiones activas de esa familia. La v.04 (2013, `e98e05ff…`) conserva `t.H`; la v.07 (2018,
`494e71be…`), sobre la que se realizó la adjudicación gold experta, muestra `t.Fi` tachado y `t.A`
insertado. Hay enlaces `duplicate_of` cruzados entre ambas y el chunk v.07 p63 queda excluido por
ellos. La migración `20260713141223` declaró que la precedencia quedaba diferida. Por tanto una
búsqueda strict-document devolvería v.04 pero no la autoridad gold; una búsqueda por filename
mezclaría revisiones. La nueva stop-line es: primero adjudicación lifecycle y reparación de dedupe
medidas y autorizadas por separado; después, recuperación intra-documento. No se codifica
`latest-wins` como heurística runtime ni se cambia producción dentro de DEC-143.

**Límite de alcance.** Esta decisión no autoriza merge, deploy, canary ni construir multi-turn/
multi-hop. Esa arquitectura continúa separada bajo DEC-136.

## DEC-144 (S277, 21 jul 2026) — La autoridad HP011 queda materializada y aplicada como migración reversible y fail-closed

**Decisión de autoridad y alcance.** La v.07 de `HLSI-MN-103_RP1r-Supra_lr`
(`494e71be-873b-48c1-adb3-a21a122da111`, mayo de 2018, extracción `914ceacf…`) es la
revisión autoritativa adjudicada para HP011 y supersede explícitamente a v.04
(`e98e05ff-ee1d-5341-869a-65768855dae9`, noviembre de 2013, extracción `ccabe3df…`). No se
introduce una heurística runtime de fecha máxima: la decisión queda en los campos lifecycle del
registro. La v.07 contiene en p63 la corrección `t.A`; v.04 conserva `t.H`.

**Diseño de migración.** `20260721190847_reconcile_hp011_v04_v07_lifecycle.sql` opera en una
sola transacción con `lock_timeout=5s`, `statement_timeout=30s` y locks ordenados sobre
exactamente 2 documentos y 190 chunks. Exige 94/96 chunks, hashes y metadata exactos, estados
active sin punteros, y la matriz `duplicate_of` original: v.04=43 no nulos (`3` internos + `40`
hacia v.07), v.07=42 (`4` internos + `38` hacia v.04). Congela las 38 parejas que modifica,
enlaza v.04↔v.07, limpia solo esos 38 `duplicate_of`, conserva los 4 duplicados internos v.07 y
corrige las notas de procedencia que aún decían «deferred». Cualquier drift o cardinalidad
inesperada lanza excepción y revierte todo.

**Reversibilidad y prueba.** El rollback manual fuera del directorio autoaplicado recrea las 38
parejas exactas, exige el estado post, restaura 38 chunks y 2 documentos y revalida la matriz
original antes de commit. Seis pruebas estáticas sellan transacción, alcance DML, identidades,
mapa y simetría migración↔rollback. Un PostgreSQL embebido desechable ejecutó además tres rutas:
aplicación correcta, rollback byte-equivalente del estado modelado y drift previo que aborta sin
dejar mutaciones. Antes de autorizar el cambio, una lectura GET confirmó la metadata y la
topología live sin emitir escrituras, llamadas de modelo ni gasto.

**Ejecución autorizada y verificada.** Tras autorización explícita, se fijó Supabase CLI 2.109.1
y se construyó una proyección temporal de las diez versiones ya aplicadas. El target fue un
hardlink byte-idéntico al migration canónico (SHA-256
`e3d9b8bd5dfd6aac338ed61a3fb89d330728493add6916f817fe79299233f9e8`); el dry-run enumeró
únicamente `20260721190847` y `db push` terminó con exit 0. Dos lecturas post independientes
confirman la fila de history (versión/nombre/8 statements) y el estado: v.04 superseded por v.07,
v.07 active y sucesora de v.04, 94/96 chunks, 43/4 duplicados no nulos, topología 3/40/0/4 y
p63 v.07 libre de `duplicate_of`. No hubo modelo, coste, Railway, deploy, merge ni cambio del KPI.
Receipt: `evals/s277_hp011_lifecycle_live_apply_receipt_v1.json`.

**Integridad de historial y regla futura.** El checkout normal conserva siete versiones
remote-only y tres local-only; no se usaron `--include-all` ni `migration repair` y `db push`
normal queda fail-closed hasta una reconciliación separada (TECH_DEBT #55). Como el migration ya
está aplicado, su fichero queda inmutable. Para migraciones futuras ejecutadas por CLI se prohíbe
un `BEGIN/COMMIT` exterior cuando se exija atomicidad entre datos y
`supabase_migrations.schema_migrations`; los rollbacks manuales sí conservan su transacción.

**Estado y siguiente paso.** El estado es
`HP011_LIFECYCLE_APPLIED_VERIFIED_DOCUMENT_LOCAL_RECOVERY_PENDING`: el cambio resuelve la
autoridad y el dedupe de HP011, pero no mueve el marcador 146/154 ni el `NO_GO_PARTIAL` de P1.
El paso natural es construir y medir sin modelos la lane genérica de recuperación
intradocumento. Otra P1 continúa prohibida hasta que esa lane pase y el código sellado esté listo
para un run limpio 27/27.

## DEC-145 (S277, 22 jul 2026) — La recuperación document-local alcanza `GO_MECHANISM`; perfil nuevo y P1 limpia siguen pendientes

**Decisión estructural.** Se incorpora, default-off, una lane document-local que obtiene
autoridad y candidatos mediante una única función `STABLE`, `SECURITY INVOKER`, GET-compatible
y con `search_path` vacío. `document_local_snapshot_v1(jsonb,text,integer,integer)` sólo puede
ejecutarla `service_role`; `PUBLIC`, `anon` y `authenticated` quedan revocados. La autoridad
procede de `documents` y del vínculo exacto `(document_id, extraction_sha256, source_file)`, no
de etiquetas denormalizadas legacy del chunk. La familia y los candidatos están acotados en SQL
con lectura `limit+1`; cualquier ambigüedad, drift, overflow, revisión no activa, duplicado o
identidad incompleta falla cerrada.

**Identidad y selección.** Los cinco campos normalizados (`document_family`, `language`,
`doc_type`, `manufacturer`, `product_model`) se toman de la fila activa ya revalidada y se
sellan en el candidato antes del planner/generador. Esto evita que labels legacy como
`RP1r-Supra`/`NULL` contradigan la autoridad `RP1r`/`usuario`. El selector semántico reutilizado
opera con `apply_catalog_scope=False` sólo dentro del blob exacto: el carril genérico conserva su
catálogo, pero sus preferencias históricas no intervienen en este segundo salto.

**Contrato servido.** V1 es ES-only y sólo sirve un registro Markdown pipe completo —cabecera,
separador inmediatamente anterior, misma aridad y una fila de datos—, con máximo un append y
receipt exacto. No contiene QIDs, chunk IDs ni reglas por manual.

**Evidencia.** El probe congelado pasó 22/22 checks sobre 13 QIDs, conservó todos los prefijos
byte a byte, ejercitó
la lane sólo donde era aplicable y seleccionó únicamente la fila autoritativa p63 de hp011. Los
controles negativos cubren lifecycle, blob/SHA, duplicados, caps, identidad, tampering y formato;
dos controles se ejecutaron además contra el RPC desplegado. El recorrido hizo 84 GET, cero
llamadas de modelo y cero escrituras de base de datos. Receipt:
`evals/s277_document_local_coverage_probe_v1.json`.

**Historial.** Las siete migraciones remote-only se recuperaron con comparación normalizada y
las tres local-only ausentes se adjudicaron como propuestas; después se aplicaron normalmente
las dos migraciones forward del mecanismo. No hubo `migration repair` ni `--include-all`.
Receipt: `evals/s277_document_local_migration_reconciliation_receipt_v1.json`.

**Límite.** El veredicto es `GO_MECHANISM`, no `P1_PASS` ni GO de C1. La lane sigue fuera de
`coverage_c1_v1` y default-off. El siguiente cambio debe crear un perfil versionado nuevo;
después corresponde una P1 limpia 27/27. Esta decisión no banca facts, no mueve 146/154, no
autoriza merge/deploy/canary y no construye multi-turn/multi-hop.

## DEC-146 (S277, 22 jul 2026) — Lineage v2 y `coverage_c1_v2` quedan listos; P1 v2 debe empezar fresca y sigue pendiente

**Decisión de autoridad live.** Se sustituye la pertenencia positiva por etiqueta legacy por una
lineage gobernada explícita: `document_revision_lineages` y
`documents.revision_lineage_id` son la única vía positiva para agrupar revisiones. Las etiquetas
históricas sólo pueden provocar rechazo por drift; nunca añadir ni ocultar miembros. La migración
lineage v2 y su ACL P1 están aplicadas live. El receipt
`evals/s277_document_local_migration_reconciliation_receipt_v2.json` queda `RECONCILED` con
**7/7 checks**: history de las cuatro versiones document-local, lineage HP011 exacta, binding de
ambos documentos, RLS de `p1_readonly` y ACL mínima por columna. La definición live SQL/STABLE/
SECURITY INVOKER/empty-search-path de `document_local_snapshot_v2` queda pineada por SHA-256 LF
`19975e3784e0cd12176cbf0b246c4e0ee8a4eed008de7542d0c6d0b6c0f9a82e`.

**Decisión de mecanismo.** El probe v2 conserva `GO_MECHANISM` con **22/22 checks** sobre 13
QIDs, prefijos byte-idénticos, máximo un append y sólo HP011 seleccionado. Declara la
aplicabilidad real —12/13 rechazados por lifecycle o idioma— y recorrió **84 GET, 0 llamadas de
modelo y 0 escrituras de base de datos**. Los caps por scope y combinado, lifecycle, lineage,
blob/SHA, identidad, duplicados, tampering y formato Markdown fallan cerrados. Receipt:
`evals/s277_document_local_coverage_probe_v2.json`.

**Cierre adversarial, sin gate-shopping.** Se completaron y adjudicaron cuatro rondas Sol/Fable:
35 findings, 30 confirmados y resueltos, 5 falsos positivos. No se pidió ni ejecutó una quinta
ronda. `evals/s277_document_local_coverage_review_packet_v5.md` es un handoff de evidencia, no
una revisión nueva ni una vía para reabrir el veredicto.

**Decisión de perfil e integridad P1.** `coverage_c1_v1` queda inmutable y mantiene
document-local off. `coverage_c1_v2` activa atómicamente sus cuatro capacidades más
`DOCUMENT_LOCAL_COVERAGE`, permite sólo structural + document-local y conserva
`MUST_PRESERVE_CONTRACT=on`; visuales siguen siendo ortogonales. El guard admite como máximo un
GET a `/rest/v1/rpc/document_local_snapshot_v2`. Cada réplica v2 exige exactamente una lane trace
document-local, `status=error` es NO-GO y el recuento semántico debe casar 1:1 con receipts GET.
`hp011:r1/r2` exigen además un GET, un único ID seleccionado y ese ID en el contexto servido.
El delta normativo vive en `evals/s277_c1_p1_design_v2.md`,
`evals/s277_c1_p1_prereg_v2.yaml` y
`evals/s277_c1_p1_release_config_schema_v2.json`.

**Estado y siguiente paso.** P1 v2 está `PENDING` y no se ha ejecutado. Debe comenzar en un
artifact root nuevo, con inputs, receipt, credenciales, genesis y fence nuevos: **27/27 réplicas,
81 llamadas y cap interno de 30 USD**. El run histórico 18/27 permanece diagnóstico y no puede
completarse con nueve réplicas bajo el árbol nuevo. Incluso un `P1_PASS` no banca facts: el KPI
sigue **146/154 (94,81 %), gap +5** y exige eval orgánico/fresco u otra familia causal.

**Stop-lines de release y arquitectura futura.** TECH_DEBT #29 no bloquea esta medición P1
acotada, pero sí bloquea merge/release global hasta una migración forward-only, inventario de
RLS/grants/policies y smokes. Merge, deploy y canary requieren gates y autorización separados.
Multi-turn/multi-hop permanece `NOT_BUILT`; DEC-146 no autoriza DDL conversacional, estado durable,
hops ni inferencia adicional.

## DEC-147 (S277, 22 jul 2026) — La P1 fresca completa cierra `P1_NO_GO`; se corrige la unidad de medida y el siguiente gate pasa a offline-first

**Resultado autoritativo.** El run `p1-v3-b92ff51-20260722a`, sellado al commit
`b92ff51e5af180352366158614ca83f7fdfc186d` y tree
`de347f6add8ae1a5fe9a9514a5d077af8b55b66d`, completó 27/27 réplicas y exactamente 81 llamadas
por 2,69369748 USD, con cap interno 30 USD y reserva desconocida cero. Railway y Supabase
registraron cero mutaciones; fence y manifest/fingerprint cerraron estables. `final.json` queda
como autoridad terminal: `P1_NO_GO / NO_GO_PROTECTED_CONTRACT`, adjudicación aplicada,
`release_deployed=false`. No existe `P1_PASS`, no cambia el KPI y C1 continúa NO-GO.

**Ledger de la tanda.** Antes de `b92ff51`, tres runs v2 terminaron diagnósticos a 17/27:
`p1-v2-511bd58-20260722a` (51 llamadas, 1,70976360 USD,
`NO_GO_PROTECTED_CONTRACT`), `p1-v2-b131464-20260722d` (54, 1,81440744 USD,
`NO_GO_PRODUCT_DOCUMENT_LOCAL_TARGET`) y `p1-v2-eefc388-20260722a` (54, 1,82350344 USD,
mismo código). Junto con las 81 llamadas/2,69369748 USD del run final, el subtotal local es
**8,04137196 USD**, reserva desconocida cero. Este no es necesariamente el gasto completo desde
la autorización de 100 USD; antes de otra llamada se reconcilian también probes, reviews y runs
fuera de ese artifact root.

**Corrección de medición.** La adjudicación ciega resolvió 91 ítems semánticos: 62 PASS y
29 FAIL. Esos ítems no son respuestas ni llamadas. A nivel de respuesta completa hay 10/27
limpias y 17/27 con al menos un FAIL. El “18/27” citado anteriormente pertenecía al run histórico
abortado `p1-8c7818cce1174f1ea0538028693ee515` y significaba 18 respuestas persistidas, no 18 PASS.
Se prohíbe volver a usar “27/27” sin el calificador `generadas` o “62/29” sin el calificador
`ítems semánticos`.

**Corrección de método.** La sesión dedicó demasiado ciclo a integridad de runner/scorer/fence y
a iteraciones de prompt antes de ejecutar un preflight barato sobre las 27 respuestas completas.
El fallo de método queda aceptado: no se compra otra muestra hasta agotar lo que puede decidirse
offline. Se añade `scripts/s277_c1_p1_offline_counterfactual.py`, que reproduce sólo el borde
determinista planner→must-preserve→conflict-guard sobre drafts/contextos congelados, deniega
red/DB y nunca concede crédito de release. Su baseline queda
`OFFLINE_PREFLIGHT_HOLD`: 27/27 replay byte-exacto, 62/62 PASS y 93/93 checks automáticos
preservados, 0/29 FAIL corregidos, cero llamadas. Este v1 congela `served_context` y, por tanto,
no puede corregir honestamente los ≥10 fallos de fuente; su eventual
`OFFLINE_FROZEN_CONTEXT_PASS` sólo acredita postgeneración sobre un commit limpio y no autoriza
gasto. Antes de una P1 nueva se debe construir un gate de candidate-context/source receipts
hash-bound. Reusa provider receipts sólo con request hash idéntico; si cambia embedding/rerank,
se permite un experimento context-only acotado, preregistrado, contabilizado y sin síntesis, o el
gate queda HOLD. Después se combina con el oráculo hasta obtener 29/29 corregidos,
62/62 y 93/93 preservados, sin reviews nuevas pendientes, FAILs ni errores de instrumento.
Después seguirá siendo obligatoria una P1 autoritativa fresca.

**Límite del instrumento de handoff.** El oracle v1 es WIP de desarrollo: Protocol 3 Sol+Fable
queda pendiente; todavía no consume un manifest que valide la cadena completa
`final→result/score→adjudication→receipts`, y `--candidate-adjudication` confía en el operador más
allá de key/decision/binding. El manifest hash-bound
`evals/s277_c1_p1_b92ff51_handoff_manifest_v1.json` registra tamaños/hashes de los artefactos
externos, pero el
gate vNext debe consumirlo y endurecer cegado/reviewer/packet/bijection. Todo PASS exige commit
limpio; un working tree dirty queda HOLD.

**Split causal.** Los 29 FAIL no son una sola clase de “synthesis miss”. Parte carece de evidencia
correcta en el contexto: hp018:r1 mezcla ZXAE/ZXEE por identidad `add` y un `LIMIT` sin orden;
cat017 no cruza identidades INSPIRE/E10/E15 aún candidatas; hp002 tiene el warning en pool pero no
lo reserva; cat019 tiene el span activo, pero falla autoridad/lineage/metadata y el serving no
admite source cards de prosa. El resto sí son omisiones de obligación compuesta, atribución,
conflicto o cita local sobre fuente ya servida. Por ello se autoriza como dirección técnica —no
como implementación ya validada— un **Evidence Contract** nuevo, default-off, sin QID/gold en
runtime, que tipa obligaciones de safety, procedimiento, relación, atribución/conflicto,
compound y aritmética trazable; reserva evidencia antes del writer y valida cobertura/cita/
contradicción después. No puede fabricar fuente ausente ni mutar la semántica histórica de
`coverage_c1_v1/v2`.

**Cambios WIP y versionado.** La rama de handoff no cambia runtime. Contiene regresiones que
demuestran que una futura política `replace` excluye la familia incorrecta sin romper ZX2e/ZX5e
y el preflight offline. Tanto activar `replace` como añadir el orden estable
`source_file,page_number,id` a `content_search` produjeron los rechazos esperados del schema/hash
sellado y se retiraron antes del commit. Nada fue medido por la P1 `b92ff51`. El próximo
candidato debe versionar schema/config/prereg e implementation hashes en vez de relajar guards o
reescribir evidencia histórica. Catálogo INSPIRE, reserva hp002, autoridad/source-card cat019 y
Evidence Contract permanecen no implementados.

`replace` no queda aprobado globalmente por los controles ZXE: antes de activarlo se exige census
de todos los umbrellas/aliases con before/after, `doc_map`, no-empty y no-wrong-family, o política
versionada por clase. El `ORDER BY source_file,page_number,id` sólo resuelve no determinismo;
selección de revisión activa/autoridad debe preceder al `LIMIT` o usar over-fetch + filtro
fail-closed.

**Orden decidido.** (1) preservar run/artefactos como baseline; (2) ejecutar el census de
identidad y resolver la selección authority/lifecycle-first antes del `LIMIT` —o
over-fetch+filter—; (3) diseñar el contrato vNext, reconciliar `spent_so_far/remaining` antes de
cualquier llamada y, antes de build/commit de impacto, ejecutar Protocol 3 Sol+Fable y adjudicar
sus claims; (4) versionar schema/config/prereg/hashes y cerrar fuente/autoridad de hp018, cat017,
hp002 y cat019 con soluciones genéricas y fail-closed; (5) implementar Evidence Contract bajo
flag; (6) construir el source/context gate y combinarlo con el oráculo postgeneración sobre un
commit limpio; si cambia un binding, emitir packet HOLD, adjudicarlo ciegamente y repetir los
gates —si cambia el request hash, usar antes un piloto context-only acotado y contabilizado o
quedar HOLD—; (7) sólo con cero REVIEW pendiente y 29/29 + 62/62 + 93/93 crear inputs, receipt,
credenciales y artifact
root nuevos y ejecutar otra P1 27/27. La autorización de trabajo/gasto de Alberto sigue
vigente después de superar los gates y no exige una pregunta nueva, pero antes de cualquier
llamada hay que reconciliar `spent_so_far/remaining` contra el techo acumulado de 100 USD; cada
P1 conserva cap 30 USD. El permiso financiero no autoriza DDL live, merge, deploy o canary.

**Alternativas cerradas y alcance.** No se reabre con otro wording el checklist S206, la
descomposición/multiwriter S216, la sustitución directa por writer frontera, las revisiones
full-answer S219–221 con regresiones, ni todos los flags must-preserve agotados en DEC-134.
El marcador sigue 146/154 (94,81 %, gap +5); incluso un futuro `P1_PASS` exige eval
orgánico/fresco para bankear. Multi-turn/multi-hop continúa separado, `NOT_BUILT`, bajo DEC-136;
Evidence Contract sólo se diseña como seam reusable del verifier futuro. Handoff reproducible:
`docs/HANDOFF_P1_B92FF51_2026-07-22.md`.

---

## DEC-148 — s278 (22 jul 2026): gobernanza de release SIMPLIFICADA (decisión de Alberto); se conserva el trabajo s277, se desmonta la obligación procesal

**Decisión (Alberto, explícita: «OK, hazlo» sobre el encuadre propuesto).** El aparato s277 (P1,
fence, manifests, receipts, adjudicación ciega, oráculo) se CONSERVA como código+artefactos+
diagnóstico; la OBLIGACIÓN procesal hacia delante se desmonta. Nuevo criterio de cierre de C1:
(1) fixes de los 29 FAIL (split causal DEC-147) verificados con tests + oráculo offline $0 sobre
commit limpio (62/62+93/93 + FAILs postgeneración corregidos); (2) UNA pasada de harness pagada
(~$3) sobre los 13 QIDs como árbitro e2e; (3) lectura humana de Alberto + merge #184 + flip de
`COVERAGE_RELEASE_PROFILE` en Railway = release. NO se construye el segundo gate
`CANDIDATE_CONTEXT_SOURCE_RECEIPT_PREFLIGHT`; NO se repite una P1 ceremonial; el ledger se cierra
de una vez con el dashboard de facturación (pendiente cifra de Alberto; documentado ≈$9,86 de 100).

**Motivo.** Ritmo: el proceso s108→s277 se volvió el cuello (Alberto: «va muy lento», «no tengo
grip»). El valor del aparato era INFORMACIÓN (17/27 respuestas con fallos reales, fuentes exactas)
y ya está cobrado; la ceremonia marginal no cambia decisiones en un bot demo sin técnicos
(DEC-071e: stop-line = tests verdes). Los controles estructurales anti-over-claim que SÍ pagan se
conservan: eval congelada, verificar-antes-de-declarar (Protocolo 1), dúo Sol+Fable antes de
cablear decisiones med/alto (Protocolo 3).

**Hallazgo de la revisión de merge (corrige mi claim «#184 es inerte»):** el contrato de
`release_profiles.py` hace la config actual de Railway (callout+verb_trigger on SIN master/lane)
IRREPRESENTABLE en producción: default `legacy` → RuntimeError en `validate_config(production=True)`
(release_profiles.py:119,237-244) y los flags-hoja se rechazan como legacy-overrides con perfil
explícito (:156). → **mergear #184 ES el flip de release por construcción**. Consecuencia: #183
(runtime-inert verificado, 0 ficheros src/) se mergea YA; **#184 queda como el PR de trabajo** y su
merge coincide con el flip Railway al final (§0 del diseño). Railway leído por API (31 vars):
callout=on, verb_trigger=on, MUST_PRESERVE=on, master/lane ausentes, VISUAL_ASSETS_REGISTRY=on,
IDENTITY_RESOLVE=on/add.

**Ejecutado s278 (paso 3 del handoff, $0):** census catalog-wide add-vs-replace (845 unidades,
1.707 queries, offline, verificación adversarial independiente = CONFIRMADO):
`replace` seguro catálogo-side SALVO umbrella con miembro candidate (FAAST/Dimension = agujero
silencioso); drops reales = clase-hp018 (ZXe/CAD-150/B500 buenos, RP1r intencional DEC-074b);
58 aliases gobernados-indetectables (puntuación fuera de `_SEP`); INSPIRE detect()==[] confirmado.
Los ceros REPLACE_EMPTIES/DROPS_DOC son tautología del instrumento (NO evidencia); doc_map cubre
861/1014 → harness final sigue siendo el árbitro e2e. Artefactos: `evals/s278_identity_census_*`
+ raíz externa `Technical Bot-s277-artifacts\s278-identity-census\`. 3 filas de DATOS esperan
adjudicación de Alberto (FAAST candidate-member · ZXR membership MIE-MI-430 · G-100-R
alias-vs-paraguas); el guard estructural del diseño §1a las hace no-bloqueantes.

**Alternativas descartadas.** Revertir/deshacer el trabajo s277 (destruye traza de migraciones ya
aplicadas + diagnóstico; no ahorra tiempo — la lentitud era proceso, no código) · rebajar el listón
a «tests verdes = release» (los 29 FAIL incluyen omisiones de seguridad reales) · saltar ya a
multi-turn (DEC-136 sigue NOT_BUILT; heredaría el single-turn defectuoso) · perfil `off` o `c1_v1`
en Railway HOY para poder mergear #184 ya (ambos cambian comportamiento vivo: uno apaga el par
shippeado s274, el otro enciende master+lane nunca desplegados).

**Siguiente.** Diseño vNext v1 (`evals/s278_vnext_design_v1.md`: replace+guard candidate-member ·
determinismo/autoridad del LIMIT · INSPIRE + fix detectabilidad 58 aliases · reserva hp002 ·
cat019 code-side · Evidence Contract default-off) → dúo Protocolo 3 (Sol+Fable, zona-de-dolor) →
implementación → oráculo/tests → harness → Alberto.

---

## DEC-149 — s278 (22 jul 2026, tarde): vNext IMPLEMENTADO y verificado offline (fases 1-4); suite 2907/0; EC quirúrgico 10/10 réplicas objetivo

**Decisión/resultado.** El diseño `evals/s278_vnext_design_v2.md` (dúo-hardened, DEC-148) queda
implementado en la rama (`018176b..7564204`) y verificado offline:

- **§1a identidad:** guard candidate-member (`all_members_consumable` en `Catalog.resolve()`) +
  quarantine-list versionada (`config/identity_quarantine_v1.yaml`, semilla FAAST/ZXR/G-100-R).
  Census re-run: exactamente 3 unidades ADD_BROADENS→SAME, resto idéntico. Sigue INERTE
  (policy default `add`); el flip lo gobierna el perfil v3 por validación.
- **§1b:** `order=source_file.asc,page_number.asc,id.asc` server-side + ventana ×4 + rank de
  autoridad por `documents.status` (fail-open) en `content_search` Path A y fallback ilike de B.
  Residual >ventana declarado en docstring; se mide en la pasada e2e.
- **§7:** perfil `coverage_c1_v3` aditivo (v1/v2 byte-idénticos; `_C1_V2_ENABLED_FLAGS` re-anclado
  a `[:5]`); 3 flags nuevos profile-owned; v3 exige `IDENTITY_RESOLVE_POLICY=replace` fail-fast.
- **§3:** `OBLIGATION_WARNING_RESERVE` default-off (máx 1 warning mismo-scope, presupuesto propio
  pre-cap, detector determinista, fail-open; control hp009 en negativos).
- **§5 Evidence Contract v1** (`src/rag/evidence_contract.py`, flag `EVIDENCE_CONTRACT`
  default-off byte-inerte, seam tras conflict_guard, brazo `--with-evidence-contract` del oráculo):
  tras iteración de precisión/recall (léxico versionado `ec_precision_lexicon_v2`: stopstems de
  dominio + stem distintivo + frames no-obligacionales + gates de plausibilidad; 4 kinds
  answer-gated: enum_alternative/limit_pair/limit_method/ui_path; ruta-sujeto del universal;
  `_apply_struck_ocr` + paridad 7-seg heredada) → **brazo EC cambia EXACTAMENTE las 10 réplicas
  objetivo (antes 24/27), colateral 0, candidate_fails 0, automatic 93/93; dev-check 14/15 ítems**
  (hp014:r2#1 Megger = inalcanzable sin heurística frágil, probado con su gemelo en hp003 limpia).
  Brazo baseline byte-inerte perfecto (27/27, 62/62, 93/93, commit limpio `7564204`).
  Los 32 REVIEW del brazo EC son inherentes (bytes cambiados ⇒ adjudicación fresca); bajo DEC-148
  el árbitro es la pasada harness + lectura de Alberto.
- **§8 seals:** los 89 fallos de suite = 88 drift-guards del runner P1 (fixture autouse re-ancla
  extraction-sources al blob sellado del receipt, tamper-proof) + 1 convención de migración
  (BEGIN/COMMIT explícitos retirados de la migración RLS; atomicidad delegada al CLI).
  **Suite completa asentada: 2907 passed / 6 skipped / 0 failed** (incluye los 4 CRLF históricos,
  re-anclados). Ítem EC-table: techo real postgen = **15/29** (hp017:r1#2/r3#2 reclasificados a
  FUENTE contra receipts; corrige el split del handoff §5).

**Motivo.** DEC-148: cerrar los 29 FAIL con lo decidible offline antes de gastar. Método
offline-first de DEC-147 aplicado sin la ceremonia desmontada.

**Alternativas descartadas en la iteración:** forzar Megger con heurística por-pregunta (rompería
hp003 o la generalidad; probado empíricamente y descartado) · disparos con tokens genéricos de
dominio (colateral 13 réplicas) · re-anclar seals relajando hashes (prohibido DEC-147).

**PENDIENTE (declarado):** §2a INSPIRE catálogo (en curso al cierre de esta entrada) · §4
code-side (identidad de blob canónica + prose source card) — próxima tanda · data-fix 2 docs +
RLS apply (visto de Alberto) · pasada harness 13 QIDs+hp009/hp010 ~$3 (cifra de ledger de
Alberto) · 3 filas census (Alberto) · merge #184 = flip de release (Alberto).
Ref: adjudicación dúo `evals/s278_vnext_duo_r1_adjudication_v1.yaml`; reportes de lanes en
`Technical Bot-s277-artifacts\s278-fase3-lane-reports\` y oráculo en `...\s278-oracle-runs\`.

---

## DEC-150 — s278 (22 jul 2026, noche): bloque LIVE aplicado por Alberto (RLS #29 + data-fix + RPC v3) + 4 adjudicaciones de catálogo; cat017 convierte en vivo, cat019 sirve el doc con 1 residual de selección

**Decisión/ejecución.** Alberto aplicó en el SQL Editor las 3 migraciones preparadas (el permiso
de escritura de la tool estaba bloqueado por el clasificador — vía manual, receipts intactos):
(1) **RLS hardening** (gate #29): post-estado verificado por queries read-only — **13/13 tablas
public con RLS**, grants de `anon`/`authenticated` sobre `chunks_v2_enunciados` revocados (el
pre-estado era PEOR que lo documentado: anon tenía TODOS los privilegios incl. DELETE/TRUNCATE),
EXECUTE de `create_hnsw_index()` revocado; **Advisor: la clase crítica desapareció** (quedan
INFO rls-no-policy esperados por default-deny + WARNs legacy pre-existentes search_path/extensiones).
**TECH_DEBT #29 queda CERRABLE** (residual declarado: p1_readonly sin policies → 0 filas).
(2) **Data-fix cat017/cat019** (patrón DEC-144): 3 docs (`80e1b7d2`, `348c4ec1`, predecessor
`bc6bdd33`) identity-complete — doc_type='programacion', language='es', lineage `verified`
contract `explicit_document_ids_v1`. Blast-radius declarado: doc_type NULL es la norma
(1147/~1171); backfill por-doc, no masivo. (3) **RPC `document_local_snapshot_v3`** (comparación
de blob CANÓNICA en los DOS sitios SQL) + flip Python `SNAPSHOT_RPC/SCHEMA` a v3 (`3383de6`;
v2 vivo en DB para los seals P1). Receipts: `evals/s278_live_prestate_receipt_v1.json` + este DEC.

**Adjudicaciones de catálogo (Alberto, 4/4) aplicadas (`fd3b95b`):** FAAST 8100E promovido
(residual declarado: doc I56 pertenece al duplicado systemsensor no adjudicado) · ZXR += zxr4b/5b ·
INSPIRE firmware→e10/e15 · **G-100/G-500/G-100-R reestructurado con ground-truth de Alberto**
(MNDT503=G-100-4/8; MNDT500=G-500-S-32/64; G-100-R*=tarjetas de relé; 3 umbrellas nuevas, 4
aliases mono-modelo retirados). **Quarantine VACIADA**. Census: 840/845 idénticas, hp018/hp009 PASS.

**Smoke e2e post-bloque (~$0.5, candidato v3+replace):** **cat017 y cat019 sirven su doc objetivo
POR PRIMERA VEZ** (HOP-138-8ES vía catálogo+data-fix; MC-380-c vía blob canónico v3). Por ítems
P1: cat017 presenta `.bin`+licencia+CLSS+POL-200 (falta el sub-paso sitio/edificio); cat019 aún
NO lleva el span exacto «sirenas o módulos de control» — el lane document-local anexó 3 filas pipe
y la card de prosa es complementaria (solo dispara si la fila ganadora no es pipe-derivable):
**residual = alcance de SELECCIÓN del span de prosa**, diagnóstico con retrieve-trace offline
pendiente (el probe sintético no reproduce el seed estructural real).

**QUEDA para release:** (a) tuning de selección cat019-span + sitio/edificio cat017 ($0 + smoke
barato); (b) pasada final 13 QIDs+controles (~$3); (c) lectura de Alberto → merge #184 + flip
Railway. Ledger: waived por Alberto (histórico ignorado, decisión suya 22-jul).

---

## DEC-151 — s278 (22 jul 2026, noche): decisión B de Alberto (release RETENIDA) + data-fix v2 + diseño de selección v1 tumbado parcialmente por el dúo

**Decisión (Alberto).** Ante el fork A (release con parciales declarados) vs B (retener hasta la
ronda estructural del selector), **B**: el overflow por-scope es un defecto sistemático (el lane
document-local se auto-apaga en manuales grandes de configuración) y no hay deadline real. La
pasada final y el merge #184 esperan a la ronda.

**Data-fix v2 aplicado (Alberto, SQL Editor) y verificado:** 5 filas más identity-complete —
HOP-138-8ES sha real (era `backfill:*`), HOP-138-9ES (instalacion) y 4188-1132-ES (guia_rapida)
completos con lineage single-rev, par MS-416 (programacion) con lineage patrón MC-380. Semántica
del sha verificada contra el SQL v3 ANTES de escribir (source_pdf_sha256 == extraction_sha de
chunks; patrón hp011 confirmado). Receipt: `evals/s278_live_poststate_receipt_v2.json`.

**Diseño selection-reach v1 → dúo (Sol 8 + Fable 9): C1 sólida-con-cambios; C2/C3 NO-sólidas.**
Convergencias críticas (adjudicación `evals/s278_selection_reach_duo_r1_adjudication_v1.yaml`):
C3 era NO-OP bajo `MAX_NEED_GROUPS=3` y rompía byte-inercia por config de facetas COMPARTIDA
(4 consumidores, first-match; el oráculo congelado no lo habría visto = falso-GO); C2 escondía
que el cap real del lane es 1 fila total (cité el patrón hp002/reserve sin su mecanismo de
presupuesto propio); el cap COMBINADO 64 seguiría matando cat017 (caso 2-docs) tras C1. Además:
prereg de regla winner-por-faceta obligatorio (anti gold-tuning), census de selección OBLIGATORIO
(C3 mueve queries por código, no "si el dúo concluye"), control negativo de composición, receipt
honesto del truncado (RPC no expone totales), sesgo front-of-doc declarado y medible. El falso
bloqueo RLS de Sol era drift documental (RLS aplicada en DEC-150) — PLAN corregido.

**Siguiente:** diseño v2 con los 11 fixes adjudicados → dúo r2 → build → census+probes $0 →
smoke ~$0.5 → pasada final ~$3 → lectura de Alberto → merge #184 = release.

---

## DEC-152 — s279/s280 (22-23 jul, sesión nocturna autónoma): ronda selection-reach COMPLETA (build+census+A5'+pasada final) + diseño multi-turn v2 adjudicado; release LISTA PARA LA LECTURA de Alberto

**Modelo operativo estrenado (instrucción de Alberto, 22-jul noche):** Opus 4.8 ejecutó las 7
lanes de implementación; Fable 5 orquestó/revisó cada diff y corrió los dúos. Autorización de
$100 de crédito Fable con mandato de optimización — registrada en memoria y aplicada.

**Ronda selection-reach (decisión B) cerrada:**
- Build I-III (perfil `coverage_c1_v4` + flag `DOCUMENT_LOCAL_SELECTION_V2`, v3 congelado ·
  facetas v5 solo-lane con validador schema-condicionado y v4 byte-pineado · waterfall
  work-conserving + plan v5 + trim A5 · vía por-faceta post-composición con attestation portante
  y presupuesto propio + fix del reused en coverage_runtime).
- Census fase IV con freeze-contract A1 (fingerprint por par + hash de la función SQL):
  **adjudicó CONTRA el build** (2 probes NOT_SELECTED) con 3 hallazgos — C1 verificado EN VIVO
  (cat019: 0→64/81 candidatos), H1 inconsistencia trim↔gate, H0 estratégico (el lane solo alcanza
  los 3 docs gobernados; 12 QIDs mueren aguas arriba en identidad backfill/lineage → **workstream
  post-release: campaña de backfill de identidad**, conecta con el activo s83).
- Enmienda A5' en DOS rondas de dúo (la primera tumbó mi framing «no es calibración» — quedó
  registrada como CAMBIO POST-PROBE con la alternativa nombrada y el discriminador ex-ante);
  census v2 (18 queries): cat017 diana elegible y servido bajo vista real; control verboso nuevo
  cumple pre-registro; **cat019 residual DECLARADO (2 FAILs r1/r2 de 29)** — reglas no aflojadas
  post-resultado.
- Verificación: oráculo baseline byte-inerte tras TODO el build (27/27+62/62+93/93) · suite
  completa **3079/0** · pasada final pagada 15 QIDs (~$3): juez holístico 14 PARCIAL + **1 PASS
  (hp018 — el fallo emblemático de la P1, ahora con familia correcta + diodo + supervisión y sin
  «en serie»)**; por ítems P1: hp002 extinción ✓ · hp011 t.A/Abort/Flow ✓ (persiste «ri»
  alucinado — cola calidad) · hp012 792+LIB-200+España ✓ (US-lado parcial) · hp014 B+/pantalla/
  32/25 ✓ (Megger fluctúa) · hp017 disclose ✓ · cat017 licencia/CLSS ✓ (.bin/sitio/edificio
  fluctúan) · cat019 residual confirmado. **Frontera visible: varianza de sub-ítems entre
  generaciones del writer único** (misma clase que la varianza r1/r2 de la P1).

**Diseño multi-turn s280 v2 ADJUDICADO** (dúo r1: Sol 8 + Fable 7; los 11 fixes incorporados —
mecanismo físico RPCs SECURITY DEFINER, verifier sin falso-equiv al EC, instrumento propio de
paridad, RGPD sin escapatoria, YAGNI de tablas, carry-forward migrado, PTB secuencial,
presupuesto por-lane). **El BUILD de Fases 0-1 arranca tras la lectura matinal de Alberto** —
esta línea es la traza que supera el `NO_BUILD_AUTHORIZATION` de DEC-136 con decisión humana.

**Para la lectura de Alberto (la adjudicación es suya, DEC-148):** merge #184 + flip Railway
(checklist diseño §7: `coverage_c1_v4` + `IDENTITY_RESOLVE_POLICY=replace` + retirar flags-hoja)
= release. Residuales declarados: cat019 ×2 · «ri» hp011 · framing US hp012 · varianza de
sub-ítems · H0 backfill. Gasto nocturno: pasada ~$3 + 2 smokes ~$1 + ~6 rondas Sol (tokens en
tally); lado Fable in-session.

## DEC-153 — s281 (23 jul): baseline oficial 39 + juez-se-queda + build MT Fase 0 COMPLETO (4 lanes, dúo focal en la zona effectively-once)
- **(a) Baseline oficial 39 QIDs bajo la release config (`coverage_c1_v4`+replace+EC+k10+fidelity, código 9cfa6f8): 12 PASS / 25 PARCIAL / 2 FALLO** — vara harness single-pass juez GPT-5.5 (≠ K-mayoría DEC-023; flips ±1-2 en golds inestables declarados). Doble uso pre-registrado: sello post-release + gate de no-regresión single-turn de la Fase 1 (misma vara consigo misma). Caveat: hp010 fail-open de coverage en el run → re-run limpio aparte = mismo veredicto (número intacto). FALLOs de clase conocida: cat016 (niega alta documentada) + cat022 (datos-finos DEC-085). Coste ~$9-10 (falso arranque DB-fría abortado a céntimos + recheck). Artefactos: `evals/bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml` + `s281_hp010_recheck.yaml`.
- **(b) El juez NO se cambia a GPT-5.6 Sol** (pregunta de Alberto): el estudio juez-vs-juez s47 (K=5) sigue vigente — 0 catches únicos del 2º juez, degradaría respuestas buenas; condición de reapertura registrada ("si GPT muestra hueco") NO disparada hoy; cambiarlo invalidaría la comparabilidad de todos los veredictos de lever + el baseline (a). Camino si algún día: repetir el protocolo s47 con Sol → re-freeze → re-baseline. Multi-turn y completitud: el follow-up resuelve la clase "falta detalle" (mayoría de los 25 PARCIAL) pero NO los errores técnicos ni las advertencias omitidas (suelo = Evidence Contract turno 1); la vara single-turn NO se relaja por existir multi-turn.
- **(c) Build MT Fase 0 COMPLETO** (rama `claude/s281-mt0` 6cec9a0→8f1d354; diseño v2 DEC-152; suite final 3158/0): MT-0b (DDL `convo` + 8 RPCs + plantilla RGPD; review Fable cazó `fail_run` inalcanzable + rename `convo_rpc` adjudicado al canónico; NO_GO_FOR_DB) · MT-0a (orquestador + paridad byte-a-byte por construcción vía reuso del seam `serving_pipeline`; envelope real capturado) · MT-0c (effectively-once runtime; **dúo focal r1: Sol xhigh RECHAZAR + sub-agente Fable SÓLIDO-CON-CAMBIOS → adjudicación 6 confirmados 0 FP** [janitor-reclaim-dañino ×3 convergente · heartbeat-sin-caller · auth-service_role · scan-sin-superficie · ventana-estrecha · fake-max-attempts único de Sol] + 9 fixes verificados punto-por-punto; enmienda DDL read-RPCs `20260723120000`) · MT-0d (adapter + 3 flags default-off byte-invariantes). Dependencias de activación real DOCUMENTADAS en docstrings (matriz RGPD firmada · DDL aplicado · JWT `role=convo_rpc` estilo p1_readonly · PGRST_DB_SCHEMAS · actor de scheduling · puente sender sync). Alternativas descartadas en las rondas: janitor-que-recomputa (diferido, F0 sin actor), heartbeat runtime (F1; COMPUTE_LEASE 600s lo sustituye en F0), fallback silencioso a service key (prohibido — fail-fast).
- **(d) Proceso**: modelo operativo s279+ (Opus ejecuta / Fable orquesta-revisa) validado en las 4 lanes — el review del orquestador + dúo cazaron 16 hallazgos reales acumulados con 0 FP adjudicados; 2 lanes se durmieron "esperando notificaciones" (modo de fallo de sub-agente: prohibir run_in_background para pytest en briefs futuros); 1 muerte por API mid-response recuperada vía resume-con-contexto. PR #184 renombrada+des-drafteada (título "NO-GO" era histórico). Refs: `evals/s281_mt0c_duo_r1_adjudication_v1.yaml` · `evals/s281_mt0b_conformance_v1.md` · tally `evals/adversarial_review_log.jsonl` (1 run Sol InternalServerError + retry OK).
- **Pendiente de Alberto (bloque, sin dependencia entre sí):** (1) lectura+merge #184 + flip Railway = release; (2) matriz RGPD sobre la plantilla (con validación legal) — gatea el APPLY del DDL, no el código; (3) visto al DDL MT-0b; (4) GO de Fase 1 multi-turn (MT-1a/1b).

## DEC-154 — s281b (23 jul): el NO-GO agéntico S95 queda acotado a su MÉTRICA (adjudicación de Alberto)
- **Alberto:** "el agente lo evaluamos para la parte de respuesta única […] no asumiría que ya se probó y no funcionó, porque estamos hablando de utilidades diferentes". CORRECTO por Protocolo 4: el NO-GO S95 (deep-lookup/agentic) es settled SOLO en su métrica — retrieval-miss de respuesta-única — y NO transfiere a la utilidad conversacional.
- **Se mantiene (fundamentos propios, ⊥ S95):** el orquestador de turno = state machine, no agente libre (effectively-once, auditoría, fail-closed en dominio PCI).
- **Consecuencia:** el gate de Fase 2 (multi-hop acotado) se pre-registrará sobre la MÉTRICA CONVERSACIONAL (eval MT + orgánico), sin heredar S95. Nota de alcance añadida a la fila del digest.

## DEC-155 — s281b (24 jul): FASE 1 MULTI-TURN MEDIDA — policy dúo-hardened + e2e pagado + 2 fixes medidos + A/B prompts; H0 con packet ejecutable
- **(a) Ciclo completo MT-1a:** build (vara 31/31) → dúo focal r1 RECHAZAR-EN-ESTADO (12 confirmados: convergencia ×3 artículos, resurrección-estado ×2 con espejo-harness, validate-rewrite débil, fallback-inseguro; 3 no-defecto) → lote 12/12 aplicado + vara ENDURECIDA 31→48 turnos/21 flujos/13 clases (los escenarios del dúo = golds permanentes) → contract 48/48 $0.
- **(b) e2e pagado (juez GPT-5.5 K=3, ~$3.3 total):** 1ª pasada 11P/2PARC/8F → diagnósticos destaparon 2 FIXES MEDIDOS: (1) **la query RESUELTA debe alimentar también la GENERACIÓN** (condense-question BP; 6/8 FALLOs = writer-sin-antecedente pidiendo modelo pese al carry; para standalone resuelta==cruda → paridad F0 intacta) + (2) expected del juez derivado de la RUTA (clarify esperada ≠ answer; artefacto mt07b/c). Re-run: 7/8→PASS. **Final: 18 PASS / 2 PARCIAL / 1 FALLO-residual** (mt11b: la policy acertó standalone; el writer single-turn pide modelo en pregunta genérica modelo-divergente = conducta DISEÑADA ask_clarification; tensión gold-vs-conducta declarada, gold intacto).
- **(c) A/B prompts (autorización Alberto herramientas-externas):** condense_lc 3/3 PASS en flujos rewrite pero con imprecisión semántica ("elemento ID3000" confunde central↔elemento); fontiber preciso. n=3 = direccional → **fontiber default**, re-medir con orgánico.
- **(d) Spec de ACTIVACIÓN (pendiente Alberto, flag-gated todo):** cableo MT-0d con TurnRequest.query = query RESUELTA (el fix (b1) es de composición, vive hoy en el driver e2e) + CONVERSATION_POLICY=impl + working-state durable (RGPD-gateado) + backfill de excerpt post-generación. NADA activo en prod.
- **(e) H0:** census (6 lineages/998 activos) + packet T3 ejecutable (re-tag 28 files; migración simétrica ZXe/ZXSe adjudicada etiqueta=FAMILIA; fix verificado del caso vivo ZXSe = model-filter excluía chunks unknown) + contrato batch_attested_v1 (LQAS). Todo PROPUESTA, DB intacta.
- **Gasto s281b:** ~$3.3 e2e + 2 rondas Sol (1 abortada por worktree-cambiante → patrón vista-estable para lanes paralelas). Refs: s281_mt1a_duo_r1_adjudication_v1.yaml · multiturn_e2e_rerun8_fontiber.yaml · multiturn_e2e_ab_condense_lc.yaml · s281_h0*_v1.md.

## DEC-156 — s282 (24 jul): F1 vivo verificado + campaña H0-T2 hasta EXPEDIENTE DE FIRMA (3 rondas de dúo + 4 draws LQAS)
- **(a) Multi-turn F1 VIVO en producción** (merges #185/#186 de Alberto + flip): smoke conversacional PEARL con follow-up sin producto resuelto por carry-forward, sellado `bot_version=f1bee30` en query_logs. Fix CI heredado: lookup de categoría fail-open (httpx sin credenciales tumbaba 4 tests multiturn).
- **(b) QA del activo s83 (prerequisito T2) — la cadena anti-bias trabajó 3 veces contra nosotros:** v1 "879 aplicables" → dúo r1 RECHAZAR (circularidad testigo, salvaguarda-familia no implementada, s83_empty inflado, juez fabricando corroboración [FS2-1, grep]) → v2 re-gating por write_op (548; pm JAMÁS auto) → LQAS draw2 PARÓ (clase Securiton _TD: manuales 118-129pp etiquetados datasheet; draw1 la había falso-aceptado) → guard de plausibilidad ($0: clase-corta>30ch→adjudicate, mueve exactamente 3, margen 13/21↔201+) → draw3 seed593 0/59 → dúo T2-apply RECHAZAR-EXPEDIENTE/COHORTE-SANA (draw3 sin ledger [4ª instancia del patrón salvaguarda-declarada→feedback #54 extendido a VERIFICACIONES: sin ledger no hubo verificación]; paquete de escritura no sellado; bound sobre-afirmado) → lote final: ledger 59-filas re-verificado 0/59 + manifest 533 sellado (mapeo doc_id 1:1, 0 huérfanos) + SQL staging+conteos+before-image+rollback + attestation v2 con framing honesto (0 defectos en 177 verificaciones/3 draws; NO bound limpio; aceptación = Alberto).
- **(c) Expediente final para la firma:** `s282_qa_s83_attestation_v2.md` + `s282_t2_manifest_v1.json` (533: doc_type 533 + language-singleton 301, fill-only NULL-guarded) + `s282_t2_apply_v1.sql`. Conflictos a adjudicar: 121 + 209 language-multi advisory + 423 adjudicate. Coste total QA: $0.92.
- **Refs:** s282_qa_s83_duo_r1 + s282_t2_apply_duo_r1 (YAML) · draws sample_v1/redraw_v1/draw3_v1 · tally (2 rondas Sol, 1 abortada por worktree-cambiante → patrón vista-estable).

## DEC-157 — s283 (24 jul): paridad de flags descubierta y contratada + baseline v2 + hp011 desmitificado
- **(a) cat016-FALLO del baseline v1 era ARTEFACTO DE PARIDAD** (env sin HYQ_TABLE; flip FALLO→PASS medido con único-delta). Tabla de paridad harness↔Railway = contrato para todo baseline futuro (`s283_cat016_diag_v1.md`).
- **(b) BASELINE OFICIAL v2 (paridad completa): 16 PASS / 20 PARCIAL / 3 FALLO** (~$3; gate no-regresión F1 apunta aquí; los 3 FALLO = clase flip single-pass: cat007 K-inestable, cat024 conflicto, hp011).
- **(c) hp011-«ri» desmitificado con mecanismo**: NO invención — propagación fiel de superficie corrupta servida (tachado OCR t.Fi + duplicado corrupto ri/4.1.2 de HLSI-MA-103 p2 = P2 al lote de Alberto). P1 (struck-OCR al contexto del generador) construido flag-off y MEDIDO: target OK (hp011→PARCIAL) pero colateral en controles (truncado de prosa tras tachados mid-line) → **NO-GO auto-ship**; candidato span-strip = regla nueva gateada por dúo. Interrupción por créditos Anthropic agotados mid-run (Alberto recargó) — recordatorio: la cuenta es compartida con PROD.
- **Cola viva**: hp012 (framing US) · cat022 (datos-finos, el FALLO real) · span-strip+dúo · mt11b (evidencia de dogfooding). Gasto s283 ~$4.5.

## DEC-158 — s283b (24 jul): rescate within-doc vía enunciados hacia ficheros SATURADOS = NO-GO medido (muro diversify)
- Flip-check in-process ($0.15, sin DB-write): la autoría de enunciados es sólida pero el padre rescatado muere en `_diversify_by_source_file` cuando el source_file diana ya satura sus slots con hermanos de score alto (cat022 `c94d2270` muere incluso a 0.99 forzado; hp012 `b162a7eb` a su cosine real). El canal A3 paga en ficheros INFRA-representados (cat016, hp012-ES), no en saturados. NO reabre cuota (s271-273) ni diversify (s59 intocado); confirma DEC-102 por otro camino.
- **cat022 + hp012-retrieval = residuales TECHO-BLOQUEADOS declarados** (mecanismo documentado; revisitar SOLO con evidencia orgánica que suba su peso). Vivo: hp012-framing (EC `attribution_conflict`) + hp011 span-strip → paquete de diseño conjunto gateado por dúo.

## DEC-159 — s283c (24 jul): dual-EC RECHAZADO pre-build por el dúo — los prerequisitos son DECISIONES DE DATOS (lote Alberto), no más ingeniería
- R1 market_attribution: muerta en diseño (no-dispara/gate-vacuo/premisas-falsas, ejecutado). **Raíz real = poblar lineage/supersedes (= campaña H0 T1/T2 ya en el lote)**. hp012-framing residual hasta entonces.
- R2 span-strip: inversión de seguridad real (119 ~~no~~-class; afirmaría complementos de negaciones tachadas). **Prerequisito = adjudicar semántica de ~~ por clase de doc (184 docs, Securiton TDs) → lote Alberto junto a P2-hp011**. Camino constructivo (span-strip solo-tablas) anotado. P1 flag-off = groundwork medido conservado.
- Cierre de la cola de calidad s283: cat016 RESUELTO (paridad) · cat022 + hp012-retrieval TECHO-DECLARADOS (DEC-158) · hp011 + hp012-framing APARCADOS-EN-DATOS (este DEC) · mt11b espera dogfooding. Ref: s283_dualec_duo_r1_adjudication_v1.yaml.

## DEC-160 — s284 (25 jul): fix de instrumento [:3000] + baseline v3 + higiene + goldreview r2 + hallazgo de seguridad hp018
- **(a) BUG DE INSTRUMENTO desde 28-may:** el juez bvg (y el e2e MT) solo veía los primeros 3000 chars (20/39 respuestas lo superaban, máx 7286). Artefactos PROBADOS por offset (cat001/cat019/cat017). Fix = ventana completa; **vara v3** declarada (juez/prompt/criterios idénticos; sin comparabilidad hacia atrás). El e2e multi-turn 18/2/1 se re-medirá bajo vara v3 cuando toque.
- **(b) Baseline v3: 16/20/3, composición rotada** — suben cat007/cat024/hp011; bajan hp009 (crítica conocida entera) y hp018.
- **(c) SEGURIDAD hp018:** generación INTERMITENTE de "conecta las sirenas en serie" (peligrosa; v2 PASS sin la frase — varianza real, no ventana). "en serie" existe en MIE-MP-520 p27 → hipótesis propagación+mal-aplicación. **PRIORIDAD 1 próxima cola**: traza + frecuencia + guard (dúo; el EC no cubre instrucciones afirmativas peligrosas — clase nueva).
- **(d) Goldreview r2 PACKET listo** (20 fichas A=10/B=4/C=4/D=2 + 2 transversales + 5 ediciones de gold + 4 rumbo) para la sentada de Alberto — los 4 C probados por offset quedan re-evaluados de facto por (b). **(e) Higiene**: 92 scripts archivados con manifiesto; TECH_DEBT 41/17/6 re-verificado; ARCHITECTURE reconciliada; suite 3228/0. Gasto s284 ~$6.

## DEC-161 — s285 (25-28 jul): campaña H0 de identidad EJECUTADA EN DB (T3 + T2) y verificada en vivo
- **(a) T3 EJECUTADO** (paste de Alberto, SQL inline tras tumbar el `\set` no soportado por el editor Supabase): 20 UPDATEs / 221 chunks re-tagueados con las 26 adjudicaciones (etiqueta=FAMILIA, ZXe/ZXSe simétrico) + 2 documentos eliminados por su orden (#21 QR + #26 genérico; orden RESTRICT-safe visual_assets→chunks→documents, backups `_s285_t3_del_*`). **Census post-T3: chunks `unknown` activos 318→1** (el deliberado compat Notifier-Morley, análisis O4-keep).
- **(b) Cierre T3 completo**: Excel −3 filas (backup local gitignored) · catálogo canónico mergeado (`morley:vsn-rp1r-plus2` con provenance URL de Alberto + redirect del alias que apuntaba a `notifier:rp1r-supra` + 21 aliases tolerancia + 15 productos companion; validate 0 err) · **5 aliases genéricos-de-propiedad RETIRADOS** («1 zona»/«Dos Zonas»… = nombre-de-propiedad, riesgo FP, 0/51 golds) · exclusión documentada del roundtrip test (canonicals con `()*` fuera de la clase de separadores del detector = **TECH_DEBT #56**, fix de raíz gateado por dúo) · 2 objetos Storage huérfanos identificados (borrado manual de Alberto, opcional) · **gate cat009 = PASS con el catálogo mergeado** (era PARCIAL — el saneado mejoró, no regresó).
- **(c) T2 EJECUTADO Y VERIFICADO EN VIVO** (paste de Alberto tras firma; guards del SQL pasaron): verificación 1:1 contra el manifest sellado = **533/533 `doc_type` + 301/301 `language` correctos, 0 mismatches, 0 sobrescrituras**. Residual global esperado (fuera del lote atestado): 605 doc_type NULL / 769 language NULL. Rollback no exige el export: old=NULL por construcción + manifest en repo.
- **(d) Hallazgo**: `documents.language` ya tiene consumidor vivo (`document_local_coverage.py:905` usa `language='es'` como señal de autoridad) → los 301 alimentan mecanismo real desde hoy, y la futura convención multi-idioma (209 docs, advisory) debe ser compatible con él. Se REAFIRMA no inventar convención sin consumidor.
- **Cifras vivas post-campaña**: 1.169 docs (996 active) · 25.088 chunks_v2 · 1 unknown activo.
- **Refs**: s285_t3_final_apply_v1.sql · s285_t3_cierre_v1.md · s285_census_post_t3_report.md · s285_cat009_gate_post_merge.yaml · s282_t2_manifest_v1.json · verificación en vivo (psycopg2 1:1, este cierre).

## DEC-162 — s286 (28-29 jul): guard hp018 A'+C' · tachados ejecutado en DB · VARA v4 + BASELINE v4 + descomposición · conducta medida · telemetría construida
- **(a) SEGURIDAD hp018 CERRADA (guard, adelantado por frecuencia 100%)**: A' (`ANTI_DIAGRAM_INVENTION`, bloque prompt anti-invención de procedimientos) + C' (`WIRING_TOPOLOGY_GUARD`, guard DETERMINISTA de topología: segmentación fence-atómica, léxico bilingüe con negación, binding [Fn]→chunk, fail-closed por etapas). Dúo 3 rondas / 45 hallazgos (1 FP mío corregido en tally). **A/B 24 gens, adjudicación CIEGA pre-registrada (veredictos hasheados pre-unmask): peligro 10/10 → 0/20, supresiones 0/48** → SHIP default-off; ON = lote Railway. Specs: `s286_hp018_guard_design_brief_v3_1.md`; resultado: `s286_hp018_ab_resultado_v1.md`.
- **(b) TACHADOS `~~` EJECUTADO EN DB** (adjudicación Alberto: énfasis mal renderizado): census 907 filas (tokenizer de runs: 2=marker, 4-flanqueado=cierre+apertura, 3/≥5=literal) → staging + paste → **backup 908 · updated 907 · verificación en vivo 0 mismatches texto+vector**; + P2 duplicado retirado + micro-patch `t.Fi→t.A` píxel-verificado (HLSI-MN-103 p63) + **2 fugas de dedup cazadas y cerradas** (hyq surrogate-swap + content_search Path A sin `duplicate_of`). hp011 post-limpieza K=3: PARCIAL×3 con 0 t.Fi/0 «Resumen inhibido» (residual = síntesis del core t.A, no corrupción).
- **(c) VARA v4 (T2b de Alberto)**: el juez ve los atomic_facts tipados `[CORE]`/`[SUPP]` para TODOS los golds; PASS = todos los CORE cubiertos; **SUPP ausente NUNCA degrada; FALLO prevalece SIEMPRE**; contrato de conducta no-answer; anti-checklist. Dominio validado {v3,v4} + estampa por-fila `judge_vara` + guard en kmajority (aborta v4 sin ACK — D3: alinear antes del próximo uso). Diseño→dúo completo→smoke→controles→sanity→adjudicación sellada (`s286_vara_v4_adjudicacion_v1.md`).
- **(d) BASELINE v4 (ship-config) = LÍNEA DE SALIDA DEL OBJETIVO: 11 PASS / 16 PARCIAL / 12 FALLO.** Pregunta de Alberto («¿por qué se disparan los FALLO?») respondida con MEDICIÓN, no teoría — **descomposición pareada** (mismas 39 respuestas + mismos golds, re-juzgadas bajo v3): v3 da 10/25/4 ⇒ **la vara explica +8 de los +9 FALLO** (los 8 flips = un-CORE-mal que v3 dejaba en PARCIAL; cat020 era PASS con rangos OTM/láser inventados dentro); residuo generación+golds+corpus = +1 FALLO; y v4 PASA una MÁS que v3 (SUPP-ausente ya no degrada: cat009/014/023/024 restaurados). El bot no empeoró; la regla es honesta. Objetivo (Alberto 28-jul): FALLO→0 salvo techo DEC-158 (cat022/hp012-retr) y PARCIAL≤10, sobre ESTA línea, vara congelada durante el arco. Artefactos: `bot_vs_gold_39_baseline_shipconfig_v4judge_s286.yaml` · `s286_vara_decomposicion_v1.json`.
- **(e) CONDUCTA (dogfooding de Alberto) MEDIDA**: follow-ups A/B 24-gens coletilla 10/10→0/12 (D1: OFF recomendado) · `GENERATOR_DIRECT_FIRST` (anti lede-burial) · `VISUAL_ASSETS_LISTING_GATE` (el bug «¿qué productos Detnov tienes?» que vio Alberto) · **fix del parser DIAGRAMAS_RELEVANTES** (amputaba la cola de ~50% de respuestas Y perdía los diagramas — regex extrae el array y re-injerta la cola). Flags default-off = byte-idéntico; clasificación P1 en `release_config` SIN tocar el módulo sellado (ampliar la tupla re-rompía 89 pins; allowlist = mismo fail-closed, desviación declarada en comentario).
- **(f) TELEMETRÍA CONSTRUIDA (GO de Alberto; salud #3 + feedback #4)**: dúo r1 obligatorio (Sol 8 + sub-agente 10 hallazgos, 0 FP; BLOCKER = RLS ausente en la tabla nueva; Sol único: FK sin ON DELETE rompía el borrado RGPD; sub-agente único: la métrica no-info medía contra una constante inexistente + tabla `feedback` existente ignorada) → brief v2 → r2 GO-BUILD → build: `answer_feedback` (FK CASCADE, UNIQUE upsert last-wins, hardening s107-pattern con postcondiciones; paste D9 pendiente de Alberto) + vistas `bot_health_daily/semanal` (security_invoker) + digest `bot_health_report.py` (dogfooding segmentado SOLO aquí — fuente única) + keyboard 👍/👎 (`TELEGRAM_FEEDBACK`, handler INCONDICIONAL) + `BOT_ERROR_LOGGING` (allowlist `error_type@stage`, nunca str(exc) — token risk) + `TERMS_VERSION` v1→v2 + `review_logs` join exacto FK. Suite 3308/0.
- **(g) Bug de instrumento MT**: el juez multi-turn corría con gold EN BLANCO (`g["answer"]` vs `gold_answer`) — TODA la serie e2e s281b afectada; fix + re-medición pendiente bajo v4 (con (c)).
- **Cifras**: suite 3308/0 · gasto s286 ≈ $12 + full assessment ~$23 en curso · corpus fingerprint re-anclado post-arco (D7). Paquete de decisiones diferidas D1-D11 + lote ONs: `s286_decisiones_diferidas_v1.md`.

### DEC-162h — s286b (29 jul, adenda): STALENESS del assessment cazada por Alberto; full re-medido con ship-config
Su pregunta («¿por qué 10 retrieval-miss si teníamos ~1?») destapó DOS fallos míos: (1) el
flag-set DEMO_FLAGS del `factlevel_assessment.py` llevaba congelado desde el 10-jul → el full
del 29-jul midió el pipeline PRE-C1 (sin `coverage_c1_v4`/`MUST_PRESERVE_CONTRACT`/identity
`replace`) y sus retr=10/rerank=8 sobre-cuentan lo que la release C1 ya convierte — NO
comparable con la foto banked 146/154 (retr 2, DEC-131/134), que es el prior real; (2) respondí
«la comparación legítima es s104 vs hoy» con el scoreboard incompleto, sin grepear las DEC de la
campaña S269-S274 (violación del gatillo Protocolo 4 «nunca de memoria»). Corrección: DEMO_FLAGS
→ ship-config del baseline v4 (freeze-hash roto declarado), fila del scoreboard corregida
in-place, smoke corregido PASS (OK 19/23), full corregido re-lanzado (~$23; el full stale queda
como contrafactual «pipeline sin C1»). Estructural: TECH_DEBT nuevo — DEMO_FLAGS sin trigger de
sync con releases; candidato = check en el cierre de sesión cuando una release cambia flags de
Railway. Lección #54 en feedback_my_bias.

## DEC-163 — s286e (29-30 jul, nocturno autónomo): instrumento factlevel v3.0 (ruta real) + MAPA CANÓNICO de la campaña + veredicto ETAPA 1
- **(a) Instrumento v3.0 construido bajo spec sellado** (dúo r1: Fable 10 + Sol 8 hallazgos, 0 FP, convergencia en 2 BLOCKERs; r2 confirmación fresca: 7 cierres; 19 cláusulas): el assessment cruza `execute_rag_turn` (patrón bvg), `served` = vista del generador (`admitted_evidence_rows` exportado — generator.py NO estaba sellado, pre-check con race identificada y descartada), soporte split pool/servido, appends juzgados sobre `coverage_context_content`, sub-motivo `append_view_truncated`, fail-open→`coverage_degraded`, pipe_sha por import-closure (40 módulos + 39 configs), 8 pins nuevos en DEMO_FLAGS, seam-guard CI cubre el assessment. Suite 3317/0.
- **(b) Los smokes v3 probaron el mecanismo**: la lane `same_blob_structural_neighbor_coverage_v1` SIRVE (7 facts `via_coverage_append` en el full). En los golds diana la transición vs la ruta stale fue retr 4→1 · OK 7→8 · synth 1→4 = **la cascada upstream→downstream que Alberto anticipó, materializada y medida** (el hecho llega y el LLM lo omite).
- **(c) MAPA CANÓNICO (full v3, serie nueva): OK 101/131 (77%) · synth 13 · retr 10 · rerank 4 · corpus 3→0 (FN 9ª instancia).** Reconciliación declarada: NO comparable 1:1 con v2.2 (ruta distinta + rerank no determinista) ni con la foto banked 146/154 (otra contabilidad). El bvg baseline 11/16/12 sigue siendo la vara del OBJETIVO.
- **(d) VEREDICTO ETAPA 1 (retrieval <2, marco 29-jul):** de los 10: 4 techo DEC-158 · 3 clase identidad (vías retrieval agotadas por medición — DEC-074/084/091b; ruta = workstream entity-linking, NO se re-litiga) · 1 centinela hp001 · 1 mecanismo real (hp013#1: seed-proximity, valor a ~12 páginas del seed más cercano, radio lane ±8) · 1 en auditoría (cat008#3). **Residual mecanismo-abierto = 1-2 ⇒ umbral alcanzado con atribución explícita, no por barrido.**
- **(e) HALLAZGO cat008#3 (pendiente de auditoría de fuente, NO adjudicado):** los docs de MI-DMMI (I56-2006-004, ES) y MI-DMMIE (I56-4406-001, EN) **se contradicen en el puente interno** (T5↔T2 vs T5↔T4) y ninguno de los chunks servidos respalda el mapping del gold (1/2=in) — mismo patrón que hp018 ZXe/ZX5e: divergencia de VARIANTE. Siguiente paso: auditoría píxel de la fuente del gold ANTES de tocar nada (el gold no se ablanda sin adjudicación de Alberto).
- **(f) ETAPA 2 abierta (rerank 4):** cat010#0 + cat017#4 (lexical-distractor) · hp018#1/#4 (pos-buried, el residual document-side de DEC-092). Brief de diagnóstico escrito; el dúo se lanza cuando haya DISEÑO que desafiar (anti-ritual: no se convoca para rubber-stamp de un plan de lectura).
- Todo committeado en `claude/s282-h0t2-qa`; ejecución nocturna bajo la directiva de autonomía del 29-jul (cero decisiones de Alberto tomadas por mí: gold intacto, prod intacta, paquete D1-D11 intacto).

## DEC-164 — s287 (30 jul): auditoría del techo DEC-158 (pregunta de Alberto) → LETRA FALSIFICADA 4/4, conclusión re-caracterizada; el «techo» son TRES cosas distintas
- **(a) El mecanismo declarado por DEC-158 está MUERTO bajo el pipeline actual** (auditoría read-only, trazas de ambos runs v3 + sondas): `_diversify_by_source_file` no puede ser el punto de muerte — solo fetcha `missing_sources`, su cap real es 16/50 (no 3/10), el reranker no tiene cuota por fichero, y el fichero diana de cat022 POSEE 7/10 slots servidos.
- **(b) cat022#0/#1 (bandas IR): POROSO con lever acotado.** Las dianas viven a **1, 3, 6 y 8** chunk_index de seeds SERVIDOS con mismo document_id+extraction_sha — DENTRO del radio ±8 de la lane structural. La lane no dispara por un gate ORTOGONAL: `expand_query_facets` → `archetype=None` (ningún arquetipo de retrieval_facets_v3 cubre la clase «diferencia-entre-variantes/semántica-de-sufijo») → `require_evidence_facet` fail-closed. **Candidato de lever (a dúo antes de cablear): cubrir esa clase de arquetipo — sin tocar radio, cap, cuota ni diversify.**
- **(c) hp012#3: techo CONFIRMADO pero RE-ATRIBUIDO** a seed-proximity out-of-radius (d=26/15 > 8, con las 2 anclas gastadas) = la clase hp013#1, no diversify.
- **(d) El flip de «BIT» NO era porosidad**: retrieval byte-idéntico entre runs; fue no-determinismo del juez semántico sobre hecho no-anclable (run 1 = miss FALSO del instrumento; el OK del run 2 es blando — la afirmación compuesta vive en un chunk no servido). Residual declarado del instrumento.
- **(e) Consecuencia para el OBJETIVO**: mantener «cat022+hp012 = techo» tal cual blindaba de la auditoría 2 hechos con palanca acotada e inflaba el numerador de FALLO→0. DEC-158 queda SUPERSEDED en su letra; la exclusión del objetivo se re-evalúa tras medir el lever de faceta. ARCHITECTURE/PLAN se reconcilian al cierre.

## DEC-165 — s288 (30 jul, autónomo): A-CORE ejecutado — autoridad documental + scope hyq (consolidación A1+A2; el arco census→staging→paste)

**Decisión.** Consolidar A1+A2 en un solo workstream «A-core» con spec normativo único
(`evals/s288_acore_design_brief_v1.md`, v3 SELLADO) y ejecutarlo hasta la bandeja de Alberto:
F0 census determinista + F2 lane hardening + P-A staged; P-B gateado a QA humana; P-C
re-diseñado a tramos; P-D eliminado.

**Motivo / traza del dúo (18/18 confirmados regla-C, 0 FP — `adversarial_review_log.jsonl`).**
- r1 (Sol NO-SÓLIDO 5 + sub-agente Fable SÓLIDO-CON-CAMBIOS 7): la migración document_id en
  hyq era una segunda fuente de verdad sin invariante (el rebinding hp011 ya reescribió
  chunks_v2.document_id) → **P-D ELIMINADO**, scope+dedup van por el embed de la FK
  autoritativa (`chunks_v2!inner`; `idx_chunks_v2_document_id` verificado). El bulk-lineage
  «verified» vaciaba la semántica canónica (authority_evidence_sha256 NOT NULL; adjudicación
  explícita) y su elegibilidad era vulnerable al label-drift. El gate H1 v1 era CIRCULAR
  (match por sha no puede fallar) → clave independiente por stem. P-A necesitaba el guard del
  UNIQUE (manufacturer, sha) — prevalencia medida 0.
- r2 (Sol focused 6): P-A por sha-only = circularidad per-doc → **dual-key stem+sha por
  fila**; el bulk-lineage cae DEFINITIVO (los predicados no adjudican autoridad) → **P-C =
  tramos adjudicados por Alberto** con dossier por-doc, y la lane hyq NO exige lineage: su
  tier honesto es **blob-verificado** (activo + sha real + binding), mismo expuesto que el
  canal vectorial de prod; el tier lineage-adjudicado queda exclusivo de document_local.
  Gate de volumen pre-registrado (aplicado==100% de elegibles); freeze de eficacia incluye
  `EMBED_CACHE_PATH`; campos desnorm de hyq demovidos al parent embebido.

**Ejecutado (commits 0581a0c→39a8961).**
- **F0** (`scripts/s288_acore_census_v2.py`, determinismo 2×): H1 CONFIRMADA 60/60 no-circular
  — `extraction_sha256` ES el sha de los bytes del PDF y los 1.334 blobs locales de OneDrive
  son los ingestados (dual-key 1.012 docs; 0 solo-sha, 0 sin-match). Partición 1169/1169.
  Colisiones de blob 0. Census hyq: 7.421 filas (10,6%) con padre dup — el canal retrieval
  guarda, la lane no guardaba.
- **F2** (lane doc_scoped_hyq): scope por document_id vía embed (name-scope muerto), autoridad
  ANTES de navegar (presupuesto 1+4+1=6/6 cero holgura), dup excluidos servidor+cinturón,
  parents_rejected trazados. Suite 3393 passed (+19 gates). Smoke embed contra deploy real
  PASSED (fallback P-D innecesario). Lane sigue OFF.
- **P-A staged** (`evals/s288_acore_pA_apply_v1.sql`): 585 docs placeholder→sha real;
  generador determinista (re-emisión byte-idéntica), parser real PG17 OK, `--verify` 16/16
  PASS contra DB live, 0 exclusiones, backup anti-reuse + rollback + dry-run. **Paste de
  Alberto pendiente** (stop-line).
- **P-B**: el gate de calibración PARÓ un backfill defectuoso — clase nueva cazada:
  extracciones diagram-heavy con ANOTACIONES EN INGLÉS del extractor (bd0c2e27: doc español
  con 39/40 marcadores «en» provenientes de `[Diagram showing…]`). FIX 3 = limpieza de input
  mecanismo-motivada → calibración 100,0% (389/389), 2 backfills erróneos evitados
  (D700-3-Sp, 4188-1132-PT), cohorte 406 {es 307, en 99}. **Gate (e)(iii) ABIERTO: QA-30 v3
  (`evals/s288_acore_pB_qa30_v3.md`), 30/30-o-HALT, adjudica Alberto.**

**Alternativas descartadas.** A1-standalone (scope irrealizable sin document_id) · P-D columna
denormalizada · bulk-lineage en cualquier variante (2 rondas) · sha-only matching · reutilizar
`audit_chunk_languages.py` (lee tabla legacy `chunks`).

**Pendiente (F3, tras el paste).** Census v3 delta con gate aplicado==100% · receipts de lane
(atribución por mecanismo) · eficacia cohorte {cat010#0, hp012#3} + hp013#1 en 39 dev con
freeze completo · después: etapa 3 síntesis sobre serving estable + re-baseline bvg.

**F3 EJECUTADO (mismo día, post-paste de Alberto — commits f8caccb + census v4).**
Paste P-A verificado en vivo EXACTO al pre-registro: placeholders 744→159 · sha real
425→1.010 · backup 585 filas · binding post 585/585. Census v4 (determinista 2×, sha
8ae2060269a1e931): **binding_ok 414→999 (+585 == el packet) · P-A elegibles 585→0 (packet
agotado = gate aplicado==100% cerrado formalmente)** · P-B intacto 406 (sigue gateado a
QA-30) · hyq dup 7.421 sin cambio (marks-only, la lane los excluye). H1 v4 «INCONCLUSA
32/32» = artefacto esperado (el estrato placeholder casi desapareció con el paste; 0
mismatches; el veredicto canónico es el 60/60 pre-paste). Probe F3.2 de cohorte
(`evals/s288_acore_f3_cohort_probe_v1.json`, $0, receipts completos): **hp012 MECANISMO
CONFIRMADO** — la lane sirve 2 parents de 15088SP con las facetas de la aguja
(per_unit_capacity p.108 + system_total p.151) y rechaza 2 docs no-activos con razón
trazada; **cat010 = archetype None** (clase alimentación/ATEX → diana ya diagnosticada del
lever de taxonomía post-A-core); **hp013 baseline doble-bloqueo confirmado**. A-core queda
CERRADO en mecanismo; el impacto en outcome se medirá con la lane ON (A3/perfil) y el
re-baseline de campaña.

## DEC-166 — s288b (31 jul): lever ONTOLOGÍA de la lane hyq — adopción del par v4/v5 con barrera; cat010 convertida en MECANISMO

**Decisión.** La lane `doc_scoped_hyq_coverage` abandona la taxonomía primitiva v1 y adopta el
par ya probado (retrieval_facets_v4 + evidence_coverage_facets_v5) CON la tercera pieza que lo
hace seguro: barrera query-card (≥1 card con query_term_hits; rechazos trazados
`no_matching_card`/`no_query_aligned_card`). Cero ediciones de configs (inertness 7/7 por
bytes). Lane sigue OFF.

**Traza del dúo (16/16 confirmados, 0 FP).** r1 convergente: mi v1 AUTORABA arquetipos que ya
existían (intrinsic_safety en v4:5-12, stems nativos, cards en v5) — prior-art omitido; r2
(Sol): el par no es transferible sin la barrera de su consumidor (v5 declara alignment 0;
rerank_pool impone `_query_card`), tabla pre-registrada a nombres runtime EXACTOS, extractor
para LANE_PAIRS, gate-0 con receipt sellado.

**Medido (gates 7/7 PASS, $0 — `evals/s288b_taxonomy_gates_v1.json` + `s288b_gate0_receipt_v1.json`).**
Diff v1→v4 en 39 dev == tabla pre-registrada (10 cambios/29 sin cambio, 0 extra) · over-trigger
limpio · sweep 21 queries → 23 parents, 0 sin card alineada · **cat010: None→intrinsic_safety,
sirve 2 parents (EN p.1 + manual IS MA1 p.8) con quotes de valores IS (24V dc, 28V 93mA,
barreras Zener ATEX/IECEx)** — símbolos Ui/Ii/Pi/Ci/Li NO en los spans servidos (clase excerpt,
no corpus) · entradas a lane 17→21 (gana cat010/hp002/hp008/hp009/hp013; pierde cat023,
adjudicado) · suite 3398. Desviaciones aceptadas: umbral barrera=1 (el 6 de rerank_pool es
IMPOSIBLE aquí — query_term_hits capado 0..4 por esquema; con 6 → 0/23, medido) ·
compatibility_bundle opt-out explícito byte-equivalente (reusa el colector).

**Residuales declarados.** (1) Estrictez per-arquetipo de v4 NO restaurada: 8/17 parents
preexistentes bajo el mínimo v4 de su arquetipo — gap conocido, se re-evalúa en el gate de A3
(outcome, lane ON). (2) hp009 entra a loop_eol → nota-CENTINELA de conducta para A3. (3)
cat009 entra por arquetipo pero sin scope de resolver; hp013 entra y sirve 0 (sin surrogate
PWR-R) — coherente con lo pre-registrado. (4) cat010#0 SIGUE rerank-class en el mapa DEC-163
hasta medir outcome: este lever abre la vía de cobertura, no re-clasifica el miss.

## DEC-167 — s288c (31 jul): pieza 3 de etapa 2 investigada a fondo — la cuota-por-faceta MUERE ×2 en dúo; los misses reales son bugs de orden/fallback en puertas EXISTENTES; ruta = 2 fixes quirúrgicos

**Decisión.** (a) La cuota-por-faceta queda **CERRADA como familia de lever nuevo** para etapa 2
(dos diseños consecutivos — v1 slots + v2 content-keyed — tumbados en dúo con 31/31 hallazgos
confirmados 0 FP entre r1 y r2). (b) La ruta viva para {cat017#4, hp002#4} = **fixes quirúrgicos
en las lanes existentes**: (i) fallback de iteración del bucket en `_facet_gate_and_select` /
`_append_facet_complement` (hoy `bucket[0]`-único + aborto si no atesta,
post_rerank_coverage.py:1118/:1377-82); (ii) selección puntuada en `obligation_warning_reserve_v1`
(hoy primer-match por pool-rank, rerank_pool_coverage.py:535-585). Ambos MEDIO-en-zona-de-dolor
⇒ dúo r3 obligatorio ANTES de build. (c) Pieza de observabilidad adelantada (ambos dúos lo
pidieron): exponer salud/fail-open por canal en traza (`_channel` ya se estampa por fila; el
fail-open silencioso es el del canal vector PRINCIPAL) + recibos de estabilidad committeados.

**Motivo / evidencia (toda con recibo).**
- Probe serve-rate judge-free (`scripts/s288c_cat017_serve_rate_probe.py` + json, mandato dúo r1):
  0/6 ruta harness exacta ⇒ exclusión SISTEMÁTICA de selección (0/8 con reps canónicas).
- Mapa re-anclado 10 golds P1 (N=2): OK 22→26 · retr 4→0 · hp018#1/#4 OK · regresión única
  hp002#4 (SEGURIDAD) ⇒ etapa 2 HEAD = {cat017#4, hp002#4}, mecanismo común (monopolio de
  selección within-doc).
- Diagnóstico $0 (`evals/s288c_gate_diagnosis_v1.md` + probe reejecutable): cat017 = la lane
  document_local dispara y `b7633e98` atesta True en contrafactual (muere por orden+no-fallback);
  hp002 = singleton `5b6a3a19` p.121 pasa TODOS los gates de la reserva y pierde por orden (el
  presupuesto 1 se lo lleva una fila de changelog con la palabra «Advertencia»). Reproducción
  byte-exacta de appends HEAD en 2 ventanas de pool ⇒ inmune a la inestabilidad.
- Dúo r1 (13/13): lane-vecinos CERRADA (rank_key 5-claves; max_anchors schema 1..4; cap per-lane
  2; sin señal no-contaminada). Dúo r2 (18/18): la «autoría ciega» del re-spec estaba contaminada
  EN LA ORDEN (F1, verificado: query hp002 sin léxico de mantenimiento) y el predicado
  cobertura-de-grupo ≠ predicado del fallo (F2, verificado: sub-intención-2 ya servida en cat017).
- Tallies completos en `evals/adversarial_review_log.jsonl` (ts 08:37 r1 · 22:40 r2).

**Alternativas descartadas.** Cuota v1 slots (8-Sol r1) · re-spec content-keyed (F1/F2 r2) ·
lane-vecinos presupuesto/orden (H4 r1: 4 topes duros) · re-tune reranker (settled DEC-092) ·
ampliar K (cobrado DEC-092b) · residual-declarado-sin-diagnóstico (contradecía upstream-first
con un hecho de SEGURIDAD en el suelo).

**Colaterales de la sesión.** (1) CI fix Linux-only del instrumento (docstrings-como-rutas,
ENAMETOOLONG; commit 9a9736b). (2) P1 a prod SIN flag vía merge #189 — el PR body decía «todo
default-off» (inexacto, corrección declarada en sesión); re-medición cubierta por el mapa
re-anclado; bvg K=3 de tocados queda opcional. (3) Matcher de attestation sin stemming (lemas vs
flexiones) = TECH_DEBT #59; refutó F7 por medición (0/26 grupos atestan el singleton). (4) Pool
del reranker ventana-dependiente (bandas 1/12-14/44) — la banda 12-14/44 sin recibo committeado
(lección #56 de feedback_my_bias): se re-emite committeada dentro de la pieza de observabilidad.
(5) Instrumento: hueco `l1_killed` con sup no-vacío nunca re-adjudicado
(factlevel_assessment.py:731) — sin efecto en estas 2 dianas (kills verificados correctos),
anotado para la próxima revisión del instrumento.

## DEC-168 — s289 (1 ago 2026): etapa 2 EJECUTADA — 2 fixes de orden/fallback construidos flag-off, gates PASS, cat017#4 convertida (Fix A) y hp002#4 miss→flip en ventana-mala (Fix B); observabilidad de canales entregada

**Decisión.** (a) Los 2 fixes quirúrgicos de DEC-167(b) quedan CONSTRUIDOS default-off,
byte-invariantes con flag off, y GATEADOS con cadena de evidencia ligada por hash:
`FACET_COMPLEMENT_FALLBACK` (fallback de attestation en la vía por-faceta:
`_facet_gate_and_select_all` + iteración del orden total; firma histórica preservada) y
`OBLIGATION_RESERVE_ORDERED` (2 filtros de clase POR-GRUPO en `_warning_span` — grupo-tabla y
marcador-huérfano — + orden determinista v2 `(sección-con-intención, blockquote, pool_rank)` en
la reserva). (b) La pieza de observabilidad DEC-167(c): fail-open del canal VECTOR con log+traza
(era el ÚNICO silencioso) + `channel_health` en el seam `_trace` inerte. (c) El ON en Railway =
decisión de Alberto (checklist en el PR); rollback = quitar la variable.

**Resultados de gates (recibos en `evals/s289_*`).**
- G-0: suite 3416+3/0 (los 3 de observabilidad tras el último run verde).
- G-1 sweep-39, 5 brazos (OFF/ON/réplica-OFF/A-only/B-only) sobre captura única congelada
  (39 embeddings + 39 rerank, patrón DEC-096b): harness PASS (fidelidad replay 0 · réplica 0);
  9 golds cambian composición; atribución 8/9 = Fix B puro, cat017 = A∘B descomponible.
- G-2 por-fila `339f06e0` (cohorte protegida S273/DEC-132b): 0 citas de soporte ×5 facts ×2
  reps HEAD + answer no extrae del changelog (recibo formal) + outcome en G-3.
- G-3 dirigido pareado per-fact (9 golds, 39 facts, N=2, juez del instrumento GPT-5.5 K=5 →
  dual Opus en miss): **PASS — cat017#4 miss-stable→conveyed-stable · 0 regresiones**; bonus
  cat008#3/hp014#1 flip→conveyed-stable; hp002 5/5 conveyed-stable en ON.
- Probe ventana-mala (r4-1; prefijo HEAD sin el portador): **hp002#4 OFF=miss-stable →
  ON=flip** (el portador `5b6a3a19` SE SIRVE; conversión parcial = residual de síntesis, no de
  serving) · **cat017#4 bajo A-only = conveyed-stable** (conversión atribuible a Fix A).

**Método (lo durable).**
- **Escalada v2 pre-declarada y disparada por dato**: el orden v1 (blockquote-first) sirvió en
  la ventana capturada un callout AJENO al procedimiento (`fa55311c` «Instalación» > p.121 por
  pool-rank) → v2 = sección-con-intención primaria (léxico `_OBLIGATION_INTENT` ya existente,
  cero vocabulario nuevo; la letra «selección puntuada» de DEC-167(b)(ii)). Trigger preservado
  (`s289_g1_sweep39_result_orderv1_trigger.json`).
- **Dúo ×2 + r4 post-gates**: r3 pre-build (Sol 5/5 crítico-metodológico [brazos sobre pools
  serializados idénticos] + Fable 8 anclados [filtros POR-GRUPO; firma pineada por el probe
  reproductor de DEC-167]) y r4 focal post-gates (Sol 6/6: freeze-binding, atribución por flag,
  selección≠conversión, censo re-declarado) — **2 veces en la sesión el control estructural
  cazó la clase «validado-vs-visible» de feedback_my_bias**. Tallies completos (ts 00:06 r3 ·
  01:44 r4), 0 FP en las 3 rondas de Sol.
- **Freeze-binding de harness propio** (r4-2): sha captura + commit + sha golds estampados; G-3
  se niega ante captura no-ligada. La captura (1.2MB gz) committeada como ancla.
- Audit $0 pre-diseño sobre competidores reales (perfil de FP medido: tabla/prosa-incidental/
  marcador-huérfano) + censo 284 docs (población = pools de los 39 golds; distribución, NO
  universal semántico — 2 clases FP-en-blockquote declaradas del propio recibo).

**Alternativas descartadas (con quién las mató).** Excluir-changelog solo (insuficiente:
5 FPs por delante, audit s289) · per-chunk post-return (A3 Fable: entierra callouts reales) ·
romper la firma de `_facet_gate_and_select` (A4: 4 ficheros pineados) · cap de intentos
(número mágico) · extender el merge de `_warning_span` (radio) · blockquote-first como señal
primaria (r4-5 + trigger v1) · G-3 solo-dianas (S2=A1: todo gold con vista cambiada).

**Gaps declarados.** hp002#4 convierte PARCIAL (flip) en ventana-mala — residual = síntesis
(el hecho compite en respuesta larga), no serving; la ventana fresca lo auto-resuelve vía
rerank (variance DEC-096b). La etiqueta `attribution:"interaction"` del runner es un check de
unión demasiado estricto (cat017 documentado como A∘B limpio). Coste sesión ≈$9-12 de gates
(captura con rerank fresco > el ~$2-4 pre-registrado; declarado y a cambio mata la caveat de
staleness).

## DEC-169 — s290 (1 ago 2026): foto post-etapa-2 + diagnóstico de etapa 3 en fan-out adversarial + instrumento v3.2 (asimetría del acreditador servido cerrada, puente doc_map, pool_ids)

**Decisión.** (a) La foto post-ONs de etapa 2 (mapa-10 N=2, flags ON, freeze nuevo) se estampó
en el scoreboard; hp002 5/5 OK en rep1 con el aviso p.121 APENDIZADO por la reserva ordenada =
Fix B sirviendo en la ruta viva. (b) El diagnóstico de etapa 3 se corrió como WORKFLOW de 4
misiones judge-free + 1 refutador adversarial por misión (8 agentes, 0 errores) + regla-C mía
+ dúo r1 (Sol 6 + Fable 7, 0 FP) → levers ADJUDICADOS con secuencia. (c) El instrumento sube a
**v3.2** (un solo corte de serie, dúo-mandado): votos por-id del eje servido persistidos +
rescate dual-Opus en `support_over_served`/`support_over_append_content` (única asimetría sin
red; FN medido cat017#4) + puente de familia vía **doc_map** (join gobernado doc-a-doc por
catalog-ids role=primary, guard de ambigüedad >4 stems, fail-open) + `pool_ids` estampados.
Guard conveyed-antes-de-rerank-miss **EN HOLD** (dúo: cambia la semántica de OK).

**Gate v3.2 (recibo `s100_factlevel_smoke_v32gate.yaml`, expectativas pre-declaradas):**
cat017#4 rerank-miss→**OK** (votos por-id muestran el near-threshold del primario 0/5→2/5→5/5
entre ventanas; `via_coverage_append=True` vía la lane de Fix A — **las 2 dianas de etapa 2
convertidas de verdad**) · cat017#2 synthesis-miss SIN cambio (0 OK falso; conveyed sigue
gateando) · hp009#0 centinela INTACTO con `bridged_rows=[]` (el puente no ablandó crédito) ·
puente acredita 4 filas en cat017 (visibilidad nueva).

**Diagnóstico etapa 3 (brief `evals/s290_etapa3_diagnosis_v1.md` v1.1, refutadores + dúo):**
- cat017#4 = FN del instrumento (cerrado con v3.2).
- hp002#4 = omisión discrecional + `bind_atoms` ciego a fragmentos no-citados
  (must_preserve.py:1685-1688); el brazo determinista es HIPÓTESIS NUEVA sobre población
  distinta del NO-GO medido `MP_SERVED_BINDING` (24/105 FP, DEC-127×2 — cazado por el dúo
  tras proponerlo yo sin grepear: 4ª instancia de la clase en la sesión) → diseño L2 con gate
  FP pre-registrado tipo DEC-134-P3; brazo prompt/header paralelo.
- cat017#2 NO es techo: DOS carriers de la cardinalidad (5bb83899 + 4c186fb2, verificados);
  clase recuperado-pero-no-servido (rank-en-ventana variable; pool_ids v3.2 lo mide gratis) +
  crédito de familia reparado por el puente. L3a (serving) NO-GO-todavía: probe $0 de las 2
  lanes existentes (RERANK_POOL_COVERAGE off-por-stack-C1; hyq doc_scoped pendiente A3) y
  dimensionar con el FULL antes de diseñar lane nueva.
- hp009#0 = centinela conducta (DEC-166) — fuera de cola; tripwire en cada A/B.
- L3b re-frame: doc_map YA mapea el doc de licencias; normalización runtime nueva = doble
  verdad (rechazada); re-tag corpus = clase en cuarentena (identity_quarantine_v1).

**Secuencia vigente:** v3.2 ✓ → re-run mapa-10 (opcional barato) → **FULL de 39 bajo v3.2**
(cola real de etapa 3) → dimensionar recuperado-no-servido → L3a si paga. L2 en paralelo
flag-off; su gate GO bajo v3.2. Tripwire hp009 en todo A/B.

**Alternativas descartadas.** Guard conveyed 1(c) (hold) · normalización runtime de familia ·
re-tag de corpus · encender RERANK_POOL_COVERAGE global (re-abre stack C1) · atacar la cola
vieja de synth sin re-confirmar (clase DEC-075-caduco) · full ANTES del diagnóstico (medía
cola que los fixes de instrumento iban a mover).

**Método (durable).** Workflow de diagnóstico con refutador-por-misión pagó: 2 anclas falsas
cazadas ANTES del dúo (slot-competition era output del anexo; «único chunk» era falso) y el
hallazgo positivo del segundo carrier vino del refutador. El patrón queda: diagnóstico →
refutación → regla-C → dúo → build. Costes: workflow ~$0 API-jueces (agentes harness) · gate
v3.2 ~$4 · mapa N=2 ~$8.

## DEC-170 — s291 (1-2 ago 2026): FULL v3.2 = HITO (OK 88%, etapas 1-2 completadas corpus-wide) + lever L2 construido flag-off con dúo r2 y V1 medido

**Decisión.** (a) El FULL de 39 bajo el instrumento v3.2 (GO de Alberto, ~$25) queda estampado
como 1ª fila de la serie: **OK 115/131 (88%) · synth 12 (10 estables) · rerank 0 · retrieval 2
(centinela+techo) · corpus-gap 2 (cat013×2, clase FN verificada 8ª/9ª vez)**. Las etapas 1 y 2
de la campaña están COMPLETADAS corpus-wide; la **cascada upstream→downstream quedó medida**
(hp013#1 retrieval→synth: el serving nuevo ya sirve su carrier y el LLM lo omite **[s321 tarde: YA NO — con corpus 26215 el carrier no entra ni al pool (FULL 16-ago `raw=0`); y con el carrier inyectado el oráculo tampoco lo transmite (sonda serve 0/5×3, ver DEC-175). Fue verdad en s291; hoy no.]**). Cola de
etapa 3 = 9 synth estables (hp009 centinela excluido). (b) El lever **L2
`OBLIGATION_WARNING_APPENDIX`** (clase hp002#4 SEGURIDAD) queda CONSTRUIDO default-off tras
dúo r2 (Sol 8 + Fable 8, 0 FP, 14 resoluciones) y **V1 medido pre-build** ($0: clase 0-átomos
3/20 toda precaución/cabecera con clause_form-fail = no-op limpio; dedup dirección letal 0/4,
doble benigna 1/4): revalidación de receipt, átomo sintético del quote entero, dedup
`atom_satisfied`, slot propio post-selección (ni desplaza banked ni es desplazado), herencia
de identidad+attestation, dependencia de vector `appendix⇒ordered+reserve+contract` en el
contrato de release. Suite 3426/0. (c) **El ON de L2 queda GATEADO por G-FP de amplitud**
(drafts coherentes sobre las composiciones de la captura s289, ~$5, recibo por-fila
espurio/redundante/legítimo, tripwire STOP>5/39) + G-directed hp002#4 — pendientes.

**Método.** El diseño v1 de L2 lo tumbó 2× el dúo ANTES de gastar (r2: gate pareado-de-drafts
$0 en vez de regeneración; vector de flags; cap del renderer; ambas direcciones del dedup) y
V1a/V1b convirtieron 2 riesgos en cifras. Los 2 corpus-gap del full = los cat013 conocidos
(DEC-074, no re-litigados). La comparación 77%→88% empaqueta serving real + honestidad de
instrumento — declarado, no se desagrega sin re-run v3.0 (no se paga: la serie vieja está
cerrada).

**Siguiente.** G-FP+G-directed de L2 (→ decisión ON de Alberto empaquetada) · etapa 3 sobre
los 9 (diagnóstico por sub-motivo omitted/partial con el patrón refutador de s290) · smoke
Telegram de los fixes (query procedimental de Alberto).

## DEC-171 — s292 (1-2 ago 2026): etapa 3 diagnosticada (9 = 4 clases) · hallazgo transversal ACOTADO · lever L3 NO-GO-como-diseñado · pin del sub-agente → Opus 5 (Alberto)

**Decisión.** (a) La cola de etapa 3 queda **diagnosticada y repartida**: los 9 synth-miss
estables NO son 9 problemas sino **4 clases** — 3 levers vivos (hp003#4 hueco de léxico ·
hp017#2 supresión por conflict-guard post-generación · cat017#2 recuperado-no-servido) · 1
gold-split (cat018#2) · 1 re-cablear (hp011#2, diagnóstico REFUTADO) · 2 gold-review
(hp006#2, hp008#4) · 2 techo (hp013#1, hp017#1). Brief:
`evals/s291c_etapa3_nine_diagnosis_v1.md`. (b) El **hallazgo transversal** («el rerank 0 del
FULL está infracontado por asimetría de vara soporte-vs-conveyed») queda **ACOTADO a
cat017#2**: signature-check determinista sobre los 10 estables = **1/10**; la línea de DEC-170
se sostiene. (c) **L3 (`MP_SIEMPRE_TRIGGER`) = NO-GO COMO ESTABA DISEÑADO** (dúo 13/13, 0 FP):
`atom_good_form=False` mataría el átomo en la whitelist aunque el detector lo viera ⇒ no-op
silencioso; y el seam obvio (parchear `mp_lexicon`) **explota a SERVING** porque
`rerank_pool_coverage:463` lo consume para la lane L2 **viva en producción**. NADA cableado.
(d) **Pin del sub-agente adversarial → `opus` (Opus 5), adjudicado por Alberto**: el crédito de
Fable 5 se agotó y el pin `fable` (s88) dejó de ser ejecutable. Cross-model INNEGOCIABLE
intacto. CLAUDE.md actualizado.

**Método (lo durable de esta sesión).**
- **Medir ANTES de diseñar** volvió a pagar: el gatillo naive murió por censo (69% FP) sin
  llegar al dúo, y el apretado llegó al dúo con números.
- **Regla-C sobre mis propias sondas, 3 veces**: (i) la sonda del signature-check v1 dio 0/10
  y era CIEGA a su hipótesis (matcher de anchor + sin kill de TOC + ties) — corregida, encontró
  el carrier correcto; (ii) la sonda de exigibilidad v1 pasaba `procedural_context_tokens`
  vacíos y MATABA el lever — corregida contra el código de producción y **marcada para
  verificación externa** por ser una corrección auto-favorable; (iii) el marcador del probe de
  ventana-mala era markdown-unaware (FAIL falso). **El patrón a retener: una sonda que
  confirma lo que quiero exige el mismo escrutinio que un resultado adverso.**
- El **fan-out con refutador-por-misión** (18 agentes) cazó 2 anclas falsas y aportó el
  hallazgo del 2º carrier; el dúo posterior cazó lo que el fan-out no vio. Capas, no
  redundancia.

**Alternativas descartadas.** Parchear el léxico compartido (radio a serving) · patrón
morfológico de clase abierta para el imperativo (la vía viva es **lista cerrada**, precedente
`MANDATORY_VERB_TRIGGERS`) · atacar los 9 con levers de prompt (settled DEC-051) · dar por
refutado el hallazgo transversal con la sonda ciega.

**Estado para la v2 de L3 (si se retoma).** Seam por-parámetro a `_detect_mandatory` **y**
`_mandatory_clause_form` + gate de invariancia de `served_ids` OFF/ON · lista cerrada de
imperativos · guard de integridad de span (≥4 spans rotos medidos: citas decapitadas en clase
SEGURIDAD) · vara ciega con taxonomía pre-registrada (mi tripwire caía sobre el valor
observado) · censo out-of-sample · resolver ES/EN (el léxico se declara bilingüe).

## DEC-172 — s293 (2 ago 2026): lever A (span-repair del conflict-guard) = NO-GO por economía Y seguridad · cat017#2 = probe $0 de lanes CERRADO · hp017#2 re-clasificado a DOS causas

**Decisión.** (a) **Lever A NO-GO, nada cableado** (dúo 15/15 confirmados, 0 FP, severidad
máxima crítico; sub-agente Opus 5: «NO-SÓLIDA»). Cae por dos motivos independientes:
**economía** — juez canónico `judge_conveyed21` K=5 sobre el borrador **PRE-guard** = 3/5,
1/5, 2/5 < `THRESH_FIRM` 4 ⇒ ni con el guard perfecto `hp017#2` alcanza el umbral; y
**seguridad** — el peldaño de redacción conserva la cita del span (`[F2]`) mientras el aviso
mapea fragmento→valor (`answer_planner.py:2718`), así que el validador dice `safe` pero el
lector **reconstruye el número**: elección unilateral de facto, justo lo que el guard existe
para impedir (`:2758-2759`); hoy esa línea muere entera (`:2829`). Corolario declarado:
**mejorar retrieval empeoraría ese lever**. Recibo: `evals/s293_lever_a_guard_verdict_v1.md`.
(b) **`hp017#2` se RE-CLASIFICA: no es solo supresión por conflict-guard** (como fijó
DEC-171) sino **dos causas** — supresión de la mitad «ruta» (efecto causal medido 3/5→0/5) +
**omisión de síntesis** de la mitad «borrar la Regla 1», que el modelo no escribe (0/3 reps,
cinco marcadores incluyendo paráfrasis). (c) **cat017#2: cerrado el probe $0 de lanes que
DEC-169 dejó pre-declarado** — ni `RERANK_POOL_COVERAGE=on` ni `CANONICAL_HYQ_COVERAGE=on`
traen el carrier `4c186fb2` (pool rank 18); la conduct `facet_complement` de
`document_local_content_coverage_v1` YA detecta la necesidad («licencia») y la da por
satisfecha con el chunk **PUNTERO** (hook «Consulte… 4188-1125-ES»), `attested`, mientras el
dato vive en el documento referenciado, fuera de su scope document-local. Corrección: el 2º
carrier `5bb83899` de DEC-169 **no está en el pool** de este run. **Lever B diseñado a nivel
de mecanismo, NO construido** (decisión de Alberto: solo A).

**Método (lo durable).**
- **La medición decisiva era barata y la tenía pre-declarada sin ejecutar**: mi propia sonda
  escribía en su docstring «si el modelo NO escribía la ruta, el lever no paga»; los dos
  revisores convergieron en ejecutar el juez sobre el borrador PRE-guard ya persistido. La
  regla que queda: **cuando una sonda pre-declara su propio criterio de refutación, ejecutarlo
  ANTES de diseñar el gate**, no después.
- **Regla-C sobre mis propias sondas, 4 veces en la sesión** (censo con filtro ES-only y
  espacio-sensible que habría declarado fantasma un registro REAL; replay con flag-set copiado
  a mano que no reproducía el recibo; sonda pre-guard sin `similarity` ⇒ el guard ni corría;
  y el marcador `regla\s*1` ciego a paráfrasis, verificado con 5 marcadores).
- **Auto-verificación de fidelidad como parte del diseño de la sonda**: el replay de coverage
  exige reproducir los `appended_ids` del recibo en orden y lane ANTES de creerse ningún
  brazo contrafactual. Es lo que convirtió el probe de lanes en evidencia y no en opinión.
- El dúo cazó **el gate entero**, no un detalle: vara ciega (media verdad del hecho), NO-GO sin
  contraste pareado, circularidad validador-filtro/validador-árbitro, G1 sin cobertura del
  camino nuevo, G4 tautológico, A/B no pareado, y falta del **invariante de integridad de
  span** que DEC-171 ya exigía para esta clase.

**Alternativas descartadas.** Construir A con el gate v1 (lo mata el dúo) · relajar el
registro `KNOWN_ANSWER_CONFLICTS` o el umbral del validador (el conflicto está VERIFICADO en
corpus: intra-documento, `7` en prosa p.45 vs `8:Causa y Efecto` en el árbol de menú de
pp.15/26/41 del MISMO manual) · brazo serving-side de hp017#2 (roza settled y, medido, no
quita el colateral) · reescritura del bloque por modelo (llamada de modelo en un guard
determinista always-on) · encender `RERANK_POOL_COVERAGE` global (ya descartado en DEC-169:
re-abre la stack C1; además, medido, tampoco trae el carrier).

**Lo que queda en pie y NO se re-litiga.** El guard **borra un procedimiento de 3 pasos** por
un número dudoso (daño cualitativo real, medido 3/3, sin retorno en métrica) · su **criterio
es correcto** y el defecto es de granularidad · la huella del guard es **1/39 golds** · el
tier de un cambio que toca seguridad es **ALTO** (`docs/ADVERSARIAL_REVIEWER.md:24-27`), no
MEDIO. Requisitos para una v2 (si alguien la retoma) en el veredicto, §«Si alguien retoma».

## DEC-173 — s293 (2 ago 2026): sonda de ALCANZABILIDAD como gate previo al diseño de todo lever de serving/síntesis · 2 levers confirmados y 2 muertos

> ⚠️ **(b) CORREGIDO en s321 — LOS DOS «NO ALCANZABLE» DE ESTA ENTRADA HAN CAÍDO. (a), el
> PROCEDIMIENTO, NO se toca — pero se REBAJA de «validado» a «útil y aún NO endurecido para
> emitir un NO».** Destapó ambos, sí; pero su recibo solo sella `git_sha`, cuando el freeze-contract
> canónico (CLAUDE.md:112) exige corpus, índice, embeddings, juez, semillas y config. Un «NO
> alcanzable» emitido con ese sellado no es auditable.
>
> No caen por lo mismo, y la distinción es la lección:
>
> - **`hp017#2` — la medición era INVÁLIDA, nunca fue de alcanzabilidad.** Su recibo
>   (`evals/s293_hp017_conveyed_preguard_v1.json`) tiene reps de la forma `{pre_yes, post_yes}`,
>   **sin inyección alguna y sin campo de ids admitidos**: medía el efecto del guard (DEC-172) y se
>   le importó la etiqueta a la tabla de esta DEC como si fuera de la misma familia que los otros
>   tres. **La primera sonda real es de s321** (modo `serve`, carrier de la p43 `94cbb0ce` —que trae
>   ruta + Regla 1 + el porqué en un pasaje contiguo— admitido 3/3): **base 0/5 → oráculo 5/5 en las
>   TRES reps**, `alcanzable: true`, `oracle_firme 3/3` (`evals/s293_reachability_hp017_hp017_2.json`).
>   ⇒ **servir el carrier es el bloqueador dominante**. ⚠️ NO afirmo «es de retrieval y no de
>   síntesis»: base y oráculo son generaciones independientes y el recibo no guarda la composición
>   base, así que el 5/5 prueba ALCANZABILIDAD, no localiza el fallo en exclusiva. De hecho
>   `evals/s278_ec_item_table_v1.md:36` registra una réplica (hp017:r2) con `94cbb0ce` **SÍ servido**
>   y el hecho aún incompleto ⇒ servirlo mueve mucho, pero no basta siempre.
> - **`hp011#2` — la medición era VÁLIDA y ha CADUCADO.** Modo `serve`, **los 2 carriers del `inject` admitidos** en las 3 reps
>   (el recibo lista 3 entradas porque uno aparece dos veces), juez leído por clave: era una medición limpia del 2-ago. Pero s320c re-midió y da los
>   **TRES brazos alcanzables**; el sistema se movió entre medias. ⚠️ **Asimetría declarada**: la
>   vara es la MISMA en ambos (`any rep ≥ THRESH_FIRM`), pero la fuerza no — `hp017#2` cae con
>   **3/3 firmes a 5/5**, inequívoco; `hp011#2` cae con **6/15 firmes** (1/5 · 1/5 · 4/5) = alcanzable
>   por el criterio canónico pero con transmisión **INESTABLE**. No son equivalentes. Nadie le puso fecha de caducidad
>   a la conclusión. ⇒ el corolario **«la pair-completion que s292 iba a diseñar NO pagaría» queda
>   CONTESTADO** para el sistema de hoy.
>
> **Lo que NO cae**: los dos ALCANZABLE (`cat017#2`, `hp003#4`) tenían admisión verificada y ninguna
> hipótesis los pone en duda; no se re-sondan (ninguno decide nada hoy: uno es NO-GO por población,
> el otro está PARADO por DEC-174).
>
> **Endurecimiento que nace de aquí** (fase 2, pendiente): un «NO alcanzable» solo debe poder
> emitirse con **PRUEBA DE ENTREGA positiva**, y esa prueba es DISTINTA por modo — mi primera
> redacción («`oracle_ids_admitidos` no vacío») bloqueaba falsamente todo NO legítimo en modo
> `appendix`, que no produce ids sino `span`/`fragment_number` (dúo, convergente). Debe ser:
> **`serve` → TODOS los carriers del `inject` admitidos** (no basta «no vacío»: hay que probar que
> entraron todos los requeridos, no uno de dos); **`appendix` → span no vacío y presente literal en
> la respuesta aumentada**. Y en ambos, sin prueba de entrega el veredicto emitible es
> INCONCLUYENTE, nunca NO. El recibo de `hp017#2` no tenía ninguna de las dos y se llevó la etiqueta.
> Y todo veredicto debe **estampar el estado de corpus**: el 12-ago el corpus se movió TRES veces y
> un «NO alcanzable» envejece en silencio. La regla-C de esta misma entrada ya había cazado 3 fallos
> de la sonda (oráculo incompleto, carrier equivocado, patrón ciego) — el patrón estaba a la vista.


**Decisión.** (a) Se establece un **procedimiento nuevo y recurrente**: antes de diseñar
cualquier lever de serving/síntesis para un hecho-diana, **medir si el hecho es ALCANZABLE**
— oráculo de evidencia perfecta (inyectar el carrier en la vista del generador, o simular el
apéndice con el span verbatim) + juez canónico `judge_conveyed21` K=5. Si no transmite ni con
la evidencia ideal delante, **ningún lever de serving puede pagarlo** y el diseño sobra.
Instrumento: `scripts/s293_reachability_probe.py`; queda en la tabla del Protocolo 4 de
CLAUDE.md. Coste medido: ~$1 por hecho, minutos. (b) **Veredictos** (N=3, `THRESH_FIRM=4`;
recibo `evals/s293_reachability_result_v1.md`): **cat017#2 ALCANZABLE** (0/5 → **5/5 en 3/3**
al servir `4c186fb2`) ⇒ el lever B tiene retorno de +1 hecho garantizado · **hp003#4
ALCANZABLE** (0/5 → **5/5 en 3/3** con el apéndice del span mandatorio) ⇒ el lever L3
convertiría, con el caveat de que el «stable-miss» del recibo NO es estable con composición
fresca (1 de 3 bases dio 5/5) · **hp011#2 NO alcanzable** (0/5 → **0/5 en 3/3** con AMBAS
mitades admitidas; la respuesta ni menciona el «295») ⇒ **la pair-completion que s292 iba a
diseñar NO pagaría**: el modelo tiene el dato y contesta con otro parámetro (`r.i`), así que
el residual es selección/síntesis o alcance de gold, NO serving · **hp017#2 NO alcanzable**
(DEC-172).

**Por qué es estructural y no un truco de esta cola.** El gate es independiente del lever, del
mecanismo y del gold: solo necesita el hecho, su carrier y el juez que ya arbitra la métrica.
Escala a 30+ fabricantes porque no depende de conocimiento de producto, y convierte la
pregunta cara («¿este lever funcionaría?») en una barata («¿el techo está en el hecho o en el
pipeline?»). En esta sesión habría ahorrado el diseño del lever A y el del pair-completion.

**Regla-C sobre la propia sonda (3 fallos cazados antes de reportar).** Oráculo INCOMPLETO en
hp011#2 (inyectaba solo la mitad del label; corregido con las dos y verificando que el modelo
las tenía delante) · **carrier equivocado heredado del censo de s292**: `4581dc4b` NO contiene
el label `t.A` — el documento tiene `chunk_index` DUPLICADOS y el portador real es `f18362c6`
· patrón CIEGO en hp003#4 (`/magnetot/` no ve «magneto térmico» con espacio; el span existe y
está servido en `eaa39792` p.8 §2.3, y `feedback_corpus_gap` vuelve a tener razón).

**Alternativas descartadas.** Diseñar el lever y descubrir el techo en el gate (es lo que pasó
con el lever A: dos revisores y un diseño entero para llegar a lo que la sonda dice en
minutos) · usar un regex propio como vara (lección #58) · dar por bueno el censo de una sesión
anterior sin verificar el carrier (habría producido un NO-GO falso en hp011#2).

**Límites declarados.** N=3 separa 5/5 de 0/5 pero no estima tasas finas · el oráculo `serve`
fuerza la admisión (mide «si lo viera», no la viabilidad de la lane) · el oráculo `appendix`
dice que el span BASTA, no que el lever lo elegiría · **un «alcanzable» NO es un GO**: el
diseño sigue necesitando dúo, flag-off y su gate.

## DEC-174 — s294 (2 ago 2026): L3 v2 PARADO por decisión de Alberto (opción A) · el gatillo quedó limpio (98,3%) pero exige 2 cambios en la lane viva · 2 defectos latentes de L2 documentados

**Decisión.** (a) **L3 v2 se para** y el trabajo de etapa 3 pasa al **lever B de `cat017#2`**
(alcanzabilidad probada 0/5→5/5, DEC-173; no toca léxico ni dedup compartidos). Adjudicado por
Alberto sobre bifurcación con evidencia balanceada (`evals/s294_l3_v2_status_v1.md`).
(b) **Nada cableado en `src/`**: la sesión no tocó producción. (c) Quedan documentados **dos
defectos LATENTES de la lane L2 viva**, encontrados sin tocarla y con causa exacta —(1) punto
ciego de **contención** en `_near_duplicate_span` (`must_preserve:2074-2089`): con solape
0,908 ≥ 0,90 y números iguales, un solo token de diferencia hace que conserve AMBOS spans
cuando uno **contiene** al otro; y (2) **hueco de política de idioma** del apéndice: no
distingue el idioma del span respecto al de la respuesta.

**Lo que sí se midió (y queda reusable).** Censo **out-of-sample reproducible** del gatillo
«siempre» (1.552 chunks del corpus, `scripts/s294_siempre_census.py`) · **dos adjudicaciones
CIEGAS** del cross-model con taxonomía pre-registrada y la diana incluida sin marcar: **r1
12/61 espurias (80,3%) ⇒ STOP**, rediseño (fuera la forma B, donde estaban 11 de las 12; guard
de span recalibrado al listón del adjudicador; exclusión de la trampa «Siempre on»), **r2 1/60
(98,3%) ⇒ STOP igualmente por la regla de daño pre-registrada** · **F1 verificado suficiente**:
`_sentence_has_finite_verb` = True en las 5 formas ⇒ el átomo pasa la whitelist sin exención;
la v1 moría SOLO porque `_mandatory_triggers` devolvía `[]` en los dos sitios.

**El hallazgo que decidió.** Sobre la superficie REAL de emisión (398 chunks servidos de los 39
golds) el gatillo v2 dispara **3 veces en 2 chunks del mismo manual CAD-150**: la diana ES
(`eaa39792` p.8) y sus **dos gemelas EN** (`7849231c` p.20) — y **ambos chunks se sirven en la
MISMA respuesta de hp003**, con cap de familia 2 ⇒ el apéndice emitiría la obligación en
español **y** su gemela inglesa. `_near_duplicate_span` no puede cazarlo (idioma y tokens
distintos). Es consecuencia DIRECTA de satisfacer F5 (léxico declarado bilingüe): **cumplir el
requisito del dúo creó el problema**.

**Alternativas descartadas.** Reinterpretar la regla de daño a la vista de r2 (se comprobó si
la excusa disponible —«el pipeline ya deduplica»— se sostenía: **no**, medido) · shipear
aceptando el duplicado cross-lingüe · tocar `_near_duplicate_span` y la política de idioma
para entregar 1 hecho, sin justificación independiente (**0 casos** con el léxico actual en los
398 servidos).

**Método (durable).** El patrón «adjudicación ciega con taxonomía pre-registrada + regla de
daño» funcionó como control: r1 mandó un rediseño (no un parche) y r2 impidió que yo cerrara
en falso. **Tres fallos propios cazados**: paginación sin `ORDER BY` que hacía el censo
irreproducible (268 vs 235 capturas con el mismo código, 23% de población perdida); `\b`
escritos como **bytes de retroceso (0x08)** por escapado de heredoc, que convertían una
exclusión en no-op silencioso (y cuyo primer «arreglo» sustituía backspace por backspace);
contabilidad de rechazos anotada antes de evaluar la forma B. La lección operativa:
**verificar el EFECTO, no el código** — los tres se cazaron con pruebas de comportamiento
(`cat -A`, dos corridas consecutivas, casos unitarios), ninguno leyendo el fuente.

## DEC-175 — s294 (2 ago 2026): lever B `cat017#2` = NO-GO por POBLACIÓN (1 gold · 0,13% del corpus) · etapa 3 cerrada como cola de ingeniería · subproducto: lista de adquisición dirigida por citas

> ⚠️ **(b) RETIRADO en s321 — «etapa 3 cerrada como cola de INGENIERÍA» ya NO se sostiene. (a) y (c)
> quedan INTACTAS.**
>
> Ese cierre se apoyaba en **cuatro patas** y le quedan **dos**: los dos «no alcanzables» que cita
> (`hp017#2` y `hp011#2`) han caído — el primero por medición inválida, el segundo por caducidad
> (ver el banner de DEC-173). **Aguantan** hp003#4/L3 v2 PARADO (DEC-174, regla de daño) y
> `cat017#2` NO-GO por POBLACIÓN (esta misma entrada).
>
> ⚠️ **(a) TAMPOCO queda intacta — crítico de Sol, VERIFICADO.** Distinguir por métrica es legítimo
> (Fable lo confirma: «legítima, no conveniente»), pero **no basta si la medición citada está rota**,
> y una de sus dos patas lo está: **DEC-184 desmontó el barrido** del que sale el «0,13% del corpus»
> — de 44 documentos supuestamente ausentes **solo 7 eran huecos reales**; 18 ya estaban en corpus
> con otro nombre. Si 18 de los «ausentes» sí estaban, las «solo 4 referencias útiles» son muchas
> más, y el error corre **a favor** del lever B. ⇒ **la pata POBLACIÓN-CORPUS queda RETIRADA hasta
> recalcular**; la pata **POBLACIÓN-GOLDS (1 de 39)** es otra medición y **sí aguanta**. Lección:
> apliqué bien la regla de métricas sobre una cifra que nadie había vuelto a mirar.
>
> **Lo que sostiene la discriminación**: la métrica de (a) es **POBLACIÓN** (1 gold de 39), no
> `conveyed`. El objetivo de hoy es conveyed bajo el oráculo
> de alcanzabilidad ⇒ **no coinciden** ⇒ no lo toco. Lo mismo con DEC-174, cuya métrica es la
> precisión del gatillo (98,3%) más la regla de daño pre-registrada.
>
> **Y lo que esto NO autoriza.** Los dos hechos reabiertos son ALCANZABLES pero su **población está
> SIN MEDIR**, así que vuelven **al embudo en la puerta de población, no como levers** — aplicando
> la regla que estableció esta misma entrada: *«alcanzabilidad y población son ortogonales; un lever
> necesita las dos»*. Estado correcto: **REABIERTA en la puerta de población**, ni «cerrada» ni «hay
> lever».
>
> **Pista con ancla, declarada como no verificada hoy**: la clase de `hp017#2` —«el doc llega, la
> página del dato no»— se contó en **within-doc-miss 11** y el DEC de aquel residual la llama «el
> sub-tipo frecuente», frente a la población **1** que mató al lever B. Plausiblemente pasa la
> puerta que el otro no pasó, pero **es hipótesis**: la cifra es de un DEC anterior y desde entonces
> se han movido corpus y golds. **CENSADO en s321** (`scripts/s321_censo_poblacion_carrier.py`,
> recibo `evals/s321_censo_poblacion_carrier_v1.json`): **cota inferior = 3** — `hp001#2` y
> `hp012#3` (etiquetados `submotivo: within-doc`: carrier en corpus que nunca llegó al pool) más
> `hp017#2` (probado por sonda, escondido en `synthesis-miss`). **Contra la población 1 que mató
> al lever B ⇒ la puerta NO se cierra por población**, pero tampoco queda probada: falta sondar
> `hp013#1` (~$1), el único otro con la firma oculta y resultado de fallo, y los 12
> `synthesis-miss` son la cota superior de dónde puede haber más.
> *(Mi v1 del censo concluyó «inmedible» desde UN filtro que buscaba la firma CONTRARIA a la de
> la clase — un carrier nunca recuperado da `raw=0`, no `raw>0`. Lo tumbaron los DOS revisores;
> el «negativo cómodo» que yo mismo había dicho temer.)*
>
> **`hp013#1` SONDADO (s321 tarde, 16-ago, `evals/s293_reachability_hp013_hp013_1.json`)** —
> primero `appendix`: **no construible** (el carrier PWR-R no está en los 12 servidos hoy; contradice
> la línea 3984 «el serving nuevo ya sirve su carrier» — y el FULL del mismo día lo confirma: bajó a
> `retrieval-miss`, `raw=0 in_pool=False`). Después `serve` con los dos carriers (`a19e8735` p56 tabla
> de bornes + `2365dfaa` p12 glosario), 3 reps, guardas nuevas: entrega probada 3/3 (`admitidos_unicos=2,
> faltan=[]`), cobertura atestada, sello parcial ⇒ **NO_ALCANZABLE, base 0/5 → oráculo 0/5 ×3**. Y lo
> informativo es QUÉ dijo el oráculo con la tabla delante: las tres veces «la batería de litio de la
> LMB35… no hay procedimiento», **sin mencionar PWR-R ni «redundante»** — la pregunta dice «batería
> tampón» y el modelo se ancla en «batería»; el hecho exige NEGAR la premisa («no es una batería, es la
> alimentación redundante»), y servir el carrier no le hace negarla. ⇒ `hp013#1` **NO es candidato de
> serving** (ni retrieval ni apéndice pagan): es caso de conducta/gold-review, no de lever B. **La cota
> inferior de la población de lever B queda en ≥2** (`hp001#2`, `hp012#3` + `hp017#2` probado) — sigue
> por encima de la población 1 que mató al lever; la puerta sigue sin cerrarse por población.
> *(Este NO sí se ganó: con la sonda de ayer habría salido igual pero sin poder distinguirlo del NO
> falso de `hp017#2`; hoy lleva prueba de entrega, cobertura y el texto del oráculo.)*
>
> **LOS 8 «SERVIDO Y OMITIDO» SONDADOS (s324b, 16-ago, encargo `evals/s321_encargo_sondas_etapa3_v1.md`;
> agregado `evals/s321_poblacion_etapa3_v1.md`; recibos `evals/s293_reachability_{cat001_3,cat008_3,
> cat016_1,hp005_3,hp009_0,hp015_0,hp015_2,hp017_1}.json`; ~$11-13, 14 invocaciones).** Veredictos literales del
> instrumento: **7 ALCANZABLE / 1 NO_ALCANZABLE (`hp009#0`, con entrega 3/3 + cobertura atestada; máx 3/5) /
> 0 INCONCLUYENTE finales**; `hp015#0` y `hp015#2` = un mismo gold ⇒ **6 observaciones ALCANZABLE / 1 NO**.
> El dato que la vara canónica no separa y aquí importa: **3 de los ALCANZABLE son «flips»** (la BASE ya
> transmite hoy sin oráculo: `cat001#3` 5/5 ×3, `cat008#3` 5/5 ×3, `cat016#1` 1/3) — contradicen su etiqueta
> `conveyed_yes 0` del FULL 16-ago; el oráculo LEVANTA una base no firme en `hp005#3`, `hp015` y `hp017#1`
> (0→5). **Cota inferior de población**: por la vara literal **≥7 golds** (≥2 + {cat001, cat008, cat016, hp005,
> hp015}); contando solo donde el oráculo aporta sobre la base **≥4 golds** (≥2 + {hp005, hp015}; `hp017` ya
> contado vía `hp017#2`). **En ambas lecturas ≥3 alcanzables nuevos ⇒ desenlace «≥3-4» del encargo: la
> población deja de ser el bloqueador y el lever de etapa 3 vuelve a ser DISEÑABLE — con dúo, flag-off y gate,
> y NO en esta sesión (regla 5 del encargo).** Adjudicación pendiente de Alberto: ¿cuenta un flip como
> población? (el hub trabaja con la lectura conservadora, ≥4). Lo que NO dice: alcanzable ≠ GO (DEC-173); no
> localiza retrieval vs síntesis; `hp009#0` es caso de conducta/gold-review (el modelo contesta «¿qué RFL?»
> con las RFL que existen y no niega la premisa ni nombra `Retorno`), no de serving. Defectos del instrumento
> vistos → TECH_DEBT #89. Sello parcial: el catálogo/doc_map mutó durante la medición (lote §0.C, familias
> distintas de los golds medidos; declarado).
>
> **CORRECCIÓN ARITMÉTICA Y CIFRA DE CABECERA (s324c, misma noche; propuesta `evals/s324c_lever_b_propuesta_v1.md`
> + dúo r33 Sol/Fable, ambos aplicados):** la base «≥2» venía del FULL del 1-ago; en el FULL 16-ago `hp012#3` y
> `cat017#2` están **OK** ⇒ la población de HOY por gold es **{hp017, hp005, hp015, hp001} = 4** — y NO es una clase:
> `hp015` es un problema de DATOS (CCD-103 era candidate bajo `unresolved` → resuelto esa noche: `detnov:ccd-103`
> confirmada), `hp005#3` es omisión inestable con carrier servido (base 5/0/5), `hp001#2` es within-doc (NO-GO
> medido 3×), y **el único hecho que un lever de serving levanta con evidencia es `hp017#1`** (las tarjetas de
> cobertura de 360 chars cortan el bullet «Instrucción de entrada» — D1 «cierre de bloque de lista»). Fable r33:
> «sustitución de denominador — Alberto debe adjudicar con el 1, no con el 6/30». **Cifra de cabecera: 1 hecho
> pagable por serving. D1 NO se construye hasta medirlo offline** (¿alcanza el bullet? ¿cuántos hechos no-OK toca?)
> y replay sobre composición congelada de los flips (Sol: base/oráculo independientes no localizan retrieval vs
> síntesis). Los tres de conducta («negar la premisa»: `hp009#0`, `hp013#1`, `hp011#2`) → packet de gold-review
> `evals/s324c_goldreview_conducta_packet_v1.md`.
> **Prueba offline D1 hecha esa noche** ($0; `scripts/s324c_d1_prueba_offline.py`, replay del FULL 16-ago con la etapa de
> coverage REAL importada, fidelidad 40/40 golds / 48 filas servidas): el cierre SÍ alcanza el bullet de `hp017#1` pero SOLO
> con la definición A («línea en blanco entre ítems NO rompe el bloque»; +406 chars, 139 ajenos) — con B/B1 (Fable) no lo
> alcanza; hechos NO-OK adicionales con beneficio literal = 0; dispara en 6/27 filas estructurales (no 6/30) y cambia la
> vista de filas que soportan 9 hechos OK. **Veredicto: NO construir** salvo GO explícito de Alberto sobre «1» (y entonces
> pinear A como test y hacer G2 — oráculo del bloque cerrado en posición de lane — antes de G3).
> **Replay sobre composición congelada hecho esa noche** ($5,44; `scripts/s324c_replay_congelado.py`, mecanismo
> `gen_answer_only` de s289/DEC-168: N=5 respuestas sobre la MISMA vista + N=3 turnos frescos, juez `judge_conveyed21`
> K=5 THRESH_FIRM 4 intacto): los 4 «flips» (`cat001#3` 3/5, `cat008#3` 1/5, `cat016#1` 2/5, `hp005#3` 4/5 con la vista
> idéntica; 0/12 frescos reproducen ids+orden por el rerank no determinista y aun así la varianza dominante es de la
> RESPUESTA — una componente del hecho entra o no; juez bimodal 28/32) ⇒ **4/4 SÍNTESIS INESTABLE, 0 SERVING**: los flips
> NO son población de un lever de serving y con N=3 el FULL/sonda los etiqueta «flip» o «stable-miss» por azar. Responde
> con dato la pregunta que quedaba a Alberto («¿cuenta un flip como población?»): no para serving. La población de
> serving sigue en **1 hecho** (`hp017#1`).


**Decisión.** (a) **Lever B NO-GO**, y no por mecanismo (correcto, con retorno probado
0/5→5/5 en DEC-173) sino por **población**, que es justo lo que DEC-173 obliga a medir antes de
diseñar: **1 gold de 39** (solo `cat017`; `facet_complement` solo dispara en 2) y **≈0,13% del
corpus** (de las remisiones halladas en 3.000 chunks: 329 son INTERNAS a su propio documento,
343 vagas, 28 citan documentos que NO tenemos y **solo 4** citan uno que sí). **Retiro
explícitamente el argumento estructural que yo mismo usé al recomendarlo** («los manuales se
citan entre sí ⇒ escala a 30+»): el corpus lo desmiente. Construirlo sería 1 hecho tocando la
satisfacción de necesidades de `document_local_content_coverage_v1`, **viva en release C1**.
(b) Con esto **etapa 3 queda cerrada como cola de INGENIERÍA**: sus 3 levers vivos están
resueltos —hp017#2 y hp011#2 **no alcanzables** (DEC-172/173), hp003#4/L3 v2 **parado** tras
llegar a 98,3% de precisión (DEC-174), cat017#2 **NO-GO por población** (este DEC)—; lo que
resta es **adjudicación de golds (Alberto)** y techo declarado. (c) **Subproducto que se
queda**: `scripts/s294_citation_gap.py` produce una **lista de adquisición dirigida por citas**
— **44 documentos citados por nuestros manuales y ausentes del corpus, 77 citas**, concentrada
en Notifier/Morley series ID50/ID1000/1000 (tenemos el manual de instalación y **falta el de
programación**, que es donde vive el detalle que pregunta un técnico). Recibo con la cita
literal para adjudicación humana: `evals/s294_citation_gap_v1.json`.

**Por qué el subproducto vale más que el lever.** El lever movía 1 hecho del eval; la lista
ataca la causa raíz de una clase entera de preguntas sin respuesta, está ordenada por
frecuencia con la que el propio fabricante remite al documento, y es insumo directo del
objetivo 30+ y del Excel de inventario (`feedback_approach`).

**Método (durable) — el censo de población es el gate barato que faltaba.** DEC-173 introdujo
la sonda de alcanzabilidad («¿el techo está en el hecho?»); s294 muestra que hace falta su
gemela: **«¿cuántos casos hay?»**. Alcanzabilidad y población son ortogonales — `cat017#2` es
ALCANZABLE (5/5) y a la vez POBLACIÓN 1. Un lever necesita las dos.

**Regla-C sobre mis propias mediciones (dos correcciones antes de publicar la lista).**
(1) **Guiones**: el corpus escribe `MIDT155` donde el manual cita `MI-DT-155` ⇒ sin normalizar,
**160 documentos PRESENTES salían como ausentes** (42% de lista falsa). (2) **Ruido de pie de
página**: el código del propio manual caía en la ventana cuando el verbo remitía a una sección
(«Véase la Sección 4.1.4 … PK-ID3000») ⇒ se exige una palabra de documento entre verbo y código
y ≤100 chars: 93 → 44. Residual declarado: códigos-comodín (`997-670-00X` = manual Pearl que SÍ
tenemos).

**Alternativas descartadas.** Construir el lever B igualmente (1 hecho sobre lane viva) ·
declarar «estructural» sin censo (era mi propia afirmación, y el corpus la desmiente) ·
publicar la lista de adquisición sin normalizar guiones (habría mandado a comprar 160
documentos, ~42% ya en el corpus).

## DEC-176 — s294 (2 ago 2026): paquete de telemetría PRE-TÉCNICOS puntos 1+5 EN PRODUCCIÓN · el 👎 pasa de señal muda a caso diagnosticable · primer fallo ORGÁNICO del bot, de una clase ya conocida

**Decisión.** (a) **Puntos 1 y 5 del TECH_DEBT #60 construidos, desplegados y VERIFICADOS contra
la DB real** (PRs #200/#201/#202; 2 migraciones aplicadas por Alberto): ancla
`message_id → query_log_id` (tabla puente `answer_messages`) + follow-up del 👎 que **invita a
la prosa** y la captura con **intención explícita** vía `ForceReply`, anclada a la consulta y
escrita en `answer_feedback.comment`. (b) **`TERMS_VERSION` v2 → v3** (autorizado por Alberto:
sin técnicos en activo): el bot ahora PIDE la explicación, antes solo recogía lo espontáneo, y
los términos la enumeran. (c) **Quedan FUERA a propósito**: puntos 2/3/4 (reacciones de
Telegram — cambian el transporte, el debt avisa del gotcha de `allowed_updates`) y punto 6
(corrección de marca con relanzamiento — engancha con `hp002`, que está en el packet B2).

**Diseño, tras el dúo (17 hallazgos, 15 confirmados, 2 FP inducidos por mí).** El aviso de
Alberto gobernó el diseño: «el técnico puede PASAR del feedback y hacer otra pregunta». Se
resuelve **por diseño, no por heurística** — `ForceReply` abre la caja apuntando al mensaje del
bot, así que la explicación llega como REPLY y se ancla exacta; un mensaje suelto NO se captura
y el bot lo responde como siempre; un reply irresoluble **no degrada** a «última consulta».
**CERO esquema nuevo**: la prosa va a `answer_feedback.comment`, que es lo que **s286/DEC-162f
ya había decidido** («escribirá `answer_feedback.comment`, NO `feedback`») y que yo propuse
contradecir sin grepear el settled — el dúo lo tumbó.

**Hallazgo de producto, y el más valioso del día.** El primer caso ORGÁNICO entró por ese bucle
el mismo día: el bot dio mal la ruta al menú AVANZADO de la CAD-171 («AJUSTES > GENERAL», que él
mismo etiqueta *básica*) teniendo AVANZADO en la evidencia servida. **Verificado contra la
fuente** (tres diagramas coincidentes, p.26/34/35 de `Manual_CAD-171-MI-716-es`). **No es dato
falso: es fallo de SELECCIÓN — responde con el ELEMENTO VECINO.** Es la **misma clase que
`hp011#2`** (`r.i` en vez de `t.A`). ⇒ **Dos instancias, una de uso real.** Matiza el argumento
de DEC-175 («ningún lever de síntesis se diseña con n=1»): **la población no había que
fabricarla, había que dejarla entrar**. Recibo: `evals/s294_cad171_menu_avanzado_v1.md`;
candidato a gold en el packet B2 (ítem 9), sin crear — DEC-025.

**Método (durable) — el efecto, no el código.** Cinco fallos propios cazados, TODOS por probar
la conducta y ninguno leyendo el fuente: (1) `merge-duplicates` en una tabla con solo
SELECT+INSERT ⇒ **403 en cada insert, tragado por el fail-open**: ni un ancla jamás, sin un solo
error a la vista (cazado en smoke contra la DB); (2) `\b` escritos como **bytes de retroceso**
(0x08) por escapado de heredoc ⇒ exclusión convertida en no-op, y mi primer «arreglo»
sustituía backspace por backspace; (3) `ForceReply(selective=True)` apuntando al bot y no al
técnico ⇒ la caja se quedaba armada (lo cazó Alberto probando); (4) un test de regresión que
grepeaba el FUENTE y fallaba por la cadena de su propio comentario; (5) el flag encendido en
Railway **sin el código desplegado** (`git log origin/main..HEAD` lo destapó — Protocolo 1).

**Lección nueva (#59).** **Citar evidencia TRUNCADA en un brief induce críticos falsos.** Puse
el mensaje real de Alberto recortado a 160 caracteres y **ambos revisores** concluyeron «el
detector no dispara» como CRÍTICO; con el texto completo sí dispara. El sub-agente detectó la
contradicción por su cuenta y exigió resolverla antes de diseñar encima — tenía razón. Un
revisor solo puede ser tan bueno como la cita que se le pasa: las citas del brief van íntegras
o marcadas como recorte.

**Riesgo declarado que NO se ha cerrado.** La **matriz de retención RGPD sigue sin existir**
(verificado: se menciona una vez en el debt, no hay purga de `query_logs`). El bot ahora **pide**
prosa, así que la exposición crece; los datos nuevos heredan CASCADE, pero el hueco de fondo es
de Alberto y precede a este cambio.

**Alternativas descartadas.** FK sobre la tabla legacy `feedback` (contradecía s286/DEC-162f, y
además solo tiene GRANT SELECT+INSERT con postcondición que lo exige ⇒ la FK solo podría fijarse
en el INSERT) · capturar el siguiente mensaje sin intención explícita (rompería la función
principal: se tragaría preguntas) · pedir *reply* manual sin `ForceReply` (correcto pero con
tasa de captura baja) · texto libre gateado tras flag (la cautela no protegía nada: el texto ya
se guardaba, peor, sin enlace y sin cascada).

---

## DEC-177 (s295) — Retención RGPD: matriz + términos v4 + la constatación de que la retención NO es ejecutable

**Contexto.** s294 dejó un riesgo declarado y sin cerrar: el bot ahora **pide** prosa tras un 👎
y no existía matriz de retención.

**Decisión de Alberto (2-ago).** Retención **24 meses**; canal **`info@fontiber.com`**; DPAs
**asumidos firmados** para no bloquear (asunción DECLARADA en la matriz, no hecho verificado).

**Decisión de diseño.** El plazo no termina en `DELETE` sino retirando el identificador: el
valor del histórico está en el CONTENIDO (material de evaluación y candidatos a gold), no en
quién preguntó, y un plazo que quema el activo se pospone indefinidamente. **Con el nombre
correcto: seudonimización** (Considerando 26), no anonimización — el texto libre de un técnico
puede contener nombres, empresas u obras.

**Lo que el dúo tumbó (ambos revisores, por separado).** El mecanismo que había construido
**no anonimizaba**:
1. **No podía escribir**: `service_role` tiene solo SELECT+INSERT sobre `query_logs`/`feedback`
   — deliberadamente (`20260713164800_harden_personal_data_tables_v1.sql` hizo `REVOKE ALL` con
   postcondición que revienta si alguien concede UPDATE). Medido: `PATCH → 403` en ambas.
2. **Aunque escribiera, no bastaba**: `answer_feedback.telegram_user_id NOT NULL` y
   `answer_messages.telegram_chat_id NOT NULL` (== user_id en chat privado) sobreviven y se unen
   por `query_log_id`. El `ON DELETE CASCADE` solo actúa al BORRAR el padre.
3. El motivo que yo daba para excluir `answer_feedback` (**el UNIQUE**) era **falso**: en
   Postgres un UNIQUE admite múltiples NULL; el blocker real es el **NOT NULL**.
4. Mi claim de que esto **desbloqueaba `convo`** era **falsa**: ese gate exige
   `docs/RGPD_LIFECYCLE_MATRIX_TEMPLATE.md` FIRMADA con validación legal — matriz distinta, que
   ya existía y no grepeé antes de escribir un doc nuevo.
5. `scripts/review_logs.py` exporta `display_name` + `telegram_user_id` + pregunta +
   transcripción + respuesta a `data/eval/*.csv|xlsx`: dato personal **fuera de Supabase**, sin
   plazo e inalcanzable para el job. No estaba en la matriz.
6. `user_consent` hace upsert con `merge-duplicates` ⇒ **solo sobrevive la última versión**
   aceptada; llamarlo «prueba del consentimiento» declaraba de más.

**Qué queda cableado.**
- `docs/RGPD_RETENCION.md` — la matriz CORREGIDA, con las filas que faltaban y con lo que hoy
  NO funciona en su propia tabla, no en una nota al pie.
- Términos v4 (`TERMS_VERSION` v3→v4): el audio (**se declaraba guardar el original y no se
  guarda**), Telegram como transporte con retención propia, «disociado» en vez de
  «anonimizado», plazo y canal.
- **Tripwire de HASH** sobre `_CONSENT_TERMS`: **detector de drift, no cierre automático**.
  Los pins de versión no veían una edición del texto con la versión quieta; el hash la ve y
  obliga a pasar por la decisión. Lo que NO puede es impedir que alguien actualice el digest y
  deje `v4` — eso es juicio humano, y se declara en vez de venderlo como garantía.
- `scripts/rgpd_retencion.py` — dry-run por defecto, meses de CALENDARIO, `--meses >= 1`
  validado en el parser (un `--meses 0` habría seleccionado todo el histórico), ids de las filas
  tocadas conservados (el registro es parte del cumplimiento), y **falla ruidosamente (exit 2)**
  en vez de aparentar cumplimiento. *(La sonda `preflight_escritura` que describía esta línea
  fue SUSTITUIDA en la v2 por la transacción real con `ROLLBACK`; ver más abajo.)*
- `supabase/migration_proposals/20260803140000_s295_rgpd_rol_retencion_v2.sql` — el diseño
  completo (GRANT de COLUMNA para `query_logs`/`feedback`/`answer_feedback`, `DROP NOT NULL` en
  `answer_feedback`, `DELETE` de `answer_messages`), con postcondiciones, rollback declarado
  (que deja de ser posible tras la primera ejecución) y el **cambio acompañante obligatorio en
  `supabase_schema.sql`**: su `REVOKE ALL ON TABLE` retira también los privilegios de columna y
  su postcondición abortaría el bootstrap. **NO aplicada.**

**Lo que decide Alberto.** Aplicar o rechazar esa propuesta: **revierte parcialmente un
hardening deliberado**. También `user_consent` (¿se borra la fila cuando ya no queda dato
identificado de esa persona?), la FK de `feedback`, el plazo de los exports a disco, `/borrar`
y el mecanismo de transferencia.

**Alternativas descartadas.** *Purgar con `DELETE`* — cumple, pero quema el material de eval y
un plazo que duele se pospone. *Anonimizar ya el histórico* — 0 filas fuera de plazo; sería
destruir dato sin obligación. *Aplicar el GRANT en `supabase/migrations/`* — se aplica solo con
`db push` y esto cambia una postura de seguridad: va a `migration_proposals/`, el patrón que el
repo ya usa para DDL gateado por RGPD. *Tocar `supabase_schema.sql` ahora* — crearía la
divergencia inversa (bootstrap con un privilegio que producción no tiene). *Resolver
`user_consent` por mi cuenta* — cambia qué significa la prueba de consentimiento.

**Ronda 2 del dúo — seis correcciones más, todas verificadas.** (1) El job cubría solo el
padre: tras aplicar la migración habría salido con exit 0 dejando vivos los identificadores de
las hijas ⇒ ahora `OBJETIVOS` cubre las 4 tablas con modo (`nulificar`/`borrar`). (2) Sin
**barrera**, un privilegio divergente dejaba `query_logs` ya disociado (irreversible) y el resto
intacto: ejecución parcial, el peor estado posible ⇒ se comprueban TODOS los permisos antes de
escribir nada. (3) El filtro de la sonda (año 2000) **no era estructuralmente vacío** —
`created_at` no tiene `NOT NULL` ni cota, un backfill lo habría convertido en escritura real ⇒
ahora se exige la columna nula Y no-nula a la vez. (4) El preflight daba un **falso OK** en
`answer_feedback` (tiene UPDATE de tabla, pero la columna es `NOT NULL` y un PATCH sobre
conjunto vacío no evalúa constraints) ⇒ se lee el `required` del OpenAPI de PostgREST. (5) El
cambio acompañante del bootstrap estaba **incompleto**: el `GRANT DELETE` también aborta su
postcondición de TABLA. (6) La supresión a petición **no alcanzaba los votos que una persona
emitió sobre consultas ajenas** (el voto es `callback.from_user.id` sin filtro de chat privado;
la cascada baja desde la consulta, no desde el votante) ⇒ el procedimiento lleva ahora
`DELETE FROM answer_feedback WHERE telegram_user_id = X`.

**Dos bugs preexistentes cazados de paso.** `set_consent` documentaba que refrescaba
`accepted_at` y limpiaba `revoked_at`, y **no incluía ninguna de las dos en el payload**: la
prueba de consentimiento «v4» conservaba la fecha de v1, y un usuario revocado que re-aceptaba
quedaba servido por `_consent_cache` mientras la base lo daba por revocado (y bloqueado otra vez
al reiniciar el proceso). Y `logger.error(f"Error processing query '{query}': …")` metía la
pregunta cruda —texto libre de un técnico— en el log del worker en Railway, fuera de la matriz
y de cualquier supresión. Ambos arreglados; Railway entra en la tabla de encargados.

**Renombrado** `scripts/rgpd_anonimizar.py` → `scripts/rgpd_retencion.py`: el nombre del único
artefacto probatorio afirmaba justo lo que el resto del documento declara falso.

**v1 → v2: rol dedicado, NO `service_role` (decisión de Alberto, 3-ago).** Al presentar las
implicaciones apareció la que decide: **`service_role` es la identidad del bot** — la misma clave
del worker de Railway encendido 24/7. Concederle UPDATE/DELETE pagaba con superficie permanente
de un proceso expuesto a internet un privilegio que se ejerce una vez cada varios meses, y el más
fuerte (DELETE de anclas) quedaba colgando de él. La v2 lo mueve a un rol `rgpd_retencion`
NOLOGIN/NOINHERIT/NOBYPASSRLS que se asume con `SET LOCAL ROLE` desde una conexión de operador,
con credenciales fuera del entorno del bot. **El hardening de julio queda intacto** y hay
postcondición que lo ancla. Patrón ya establecido en el repo: `p1_readonly` (s277).

**Lo que el cambio de enfoque regaló, y que no estaba en el plan.** Al pasar de PostgREST a
conexión directa, tres defectos que la ronda 2 obligó a parchear **desaparecen de raíz**:
- El dry-run **ejecuta las sentencias reales y hace `ROLLBACK`** ⇒ verifica el EFECTO, con
  privilegios y constraints evaluados sobre filas de verdad. Se acabaron la sonda de conjunto
  vacío, el falso OK de `answer_feedback` y la lectura del OpenAPI para adivinar el `NOT NULL`.
- Las 4 tablas van en **UNA transacción** ⇒ la ejecución parcial deja de ser posible; la
  «barrera» de preflight sobra.
- El rol es NOBYPASSRLS y las tablas tienen FORCE RLS con 0 políticas, así que las **políticas
  del rol acotan la ventana a `created_at < now() - interval '24 months'`**: el plazo pasa a ser
  un **invariante del motor**, no un filtro que el script deba acordarse de poner. Un bug, un
  `--meses 0` o una ejecución a mano no pueden tocar una fila reciente. La validación del parser
  queda como defensa en profundidad. Y si el plazo cambia, cambia por migración — que es como
  debe cambiar una decisión gobernada.
- Bonus: la v1 obligaba a mover `supabase_schema.sql` a la vez (su `REVOKE ALL` se llevaba los
  grants de columna y su postcondición abortaba). La v2 **no toca sus postcondiciones**: solo
  miran `anon`/`authenticated`/`service_role`, y ninguno cambia.

**Alternativas descartadas en esta segunda vuelta.** *Conceder a `service_role`* (v1): simple,
pero paga superficie permanente del bot por un privilegio episódico. *Ejecutarlo a mano como
`postgres` desde el editor SQL*: cero superficie nueva, pero sin recibo, sin verificación y no
programable; además `postgres` puede tocarlo TODO, así que un error de copia no tiene tope.
*Dar `BYPASSRLS` al rol nuevo*: haría innecesarias las políticas y tiraría justo la propiedad más
valiosa —la ventana como invariante—. *Concederlo también a `authenticator`*: abriría el camino
HTTP; no dárselo es parte del diseño.

**Ronda 3 del dúo — el hallazgo que obligó a construir instrumento.** El sub-agente señaló que
**ningún artefacto había tocado un PostgreSQL**: los tests usaban conexión falsa, así que probaban
que se emiten las sentencias correctas, no que la base haga lo afirmado — y lo afirmado era fuerte
(la ventana como invariante RLS, el rol sin acceso al contenido, la retención que no se deshace).
Es decir: **la lección #60 que esta misma sesión escribe se incumplía en el mismo commit**. Se
cierra con `tests/test_s295_rgpd_integracion_pg.py` + `.github/workflows/s295-rgpd-retencion-pg.yml`
(contenedor desechable, patrón del gate s133): levanta el esquema, **ejecuta la propuesta entera**
—si una postcondición falla, el test revienta—, siembra filas vencidas y recientes, y comprueba el
comportamiento con datos reales.

Y siete correcciones más, todas verificadas antes de actuar:
- **Voyage AI no estaba declarado.** Producción fuerza `chunks_v2` ⇒ cada consulta se embebe con
  Voyage (`embedder.py`, `input_type="query"`), mientras los términos decían «no se comparten con
  nadie más». Términos → **v5** con los cinco encargados, la transferencia fuera de la UE y la
  promesa acotada a lo que el mecanismo hace.
- **La retención se podía deshacer sola**: tras disociar, la fila de `query_logs` sigue existiendo,
  así que un 👍/👎 en un teclado de hace dos años insertaba un voto identificado (FK válida, UNIQUE
  sin choque por NULLS DISTINCT) y re-identificaba la consulta otros 24 meses. Cerrado con un
  TRIGGER en el motor, no en Python: cubre a cualquier cliente.
- **`--meses` eliminado**: contradecía la política gobernada en las dos direcciones.
- **`ALTER ROLE … SET statement_timeout` es NO-OP** al asumir el rol con `SET ROLE` — el precedente
  `p1_readonly` lo documenta literalmente. El límite lo pone `SET LOCAL` en la sesión.
- **`SET LOCAL ROLE` fuera de transacción es un no-op con warning** ⇒ todo correría como operador
  (owner + BYPASSRLS). El job ahora **comprueba `current_user`** y aborta si no se asumió.
- **`created_at` era NULLABLE** en las cuatro tablas: una fila sin fecha no vencía jamás. 0 nulos
  hoy (verificado) ⇒ `SET NOT NULL` cierra el hueco.
- **Postcondiciones por igualdad exacta** sobre los 8 privilegios (como el bootstrap) en vez de
  «ausencia de algunos»; RLS + FORCE RLS afirmada en la propia migración (`answer_feedback` solo la
  recibía en el bootstrap ⇒ no reproducible por `db push`); políticas verificadas por rol y
  predicado, no solo por nombre.

**Dos afirmaciones mías, corregidas.** «Una ejecución a mano no puede tocar una fila reciente» era
falsa: `postgres` es owner y `BYPASSRLS`; el invariante rige **para quien actúa como el rol**. Y el
job **no es programable tal cual**: haría falta un rol runner LOGIN acotado, porque un scheduler con
`DATABASE_URL` de operador sería MÁS potente que el `service_role` que se evitó tocar. Hoy es
ejecución manual por diseño, declarado. *(SUPERADO en s299/DEC-181: la premisa valía para un cron
EXTERNO; con pg_cron el reloj vive dentro de la base y no hace falta credencial ni rol LOGIN.)*

**Ronda 4 — usabilidad del aviso, a petición de Alberto.** Preguntó si convenía **alargar los
términos ahora** para cubrir cosas futuras y ahorrarse re-aceptaciones. Respuesta: no. Un
consentimiento debe ser *específico*; una cláusula que cubra «mejoras futuras» no autoriza nada y
solo hace el aviso más vago hoy. Lo que sí reduce la churn de forma legítima es (a) describir a los
destinatarios **por categoría con su lista actual** —que es lo que el RGPD pide— y (b) revisar la
**base jurídica**, que es de donde nace la fricción.

**Lo construido**: **aviso en DOS CAPAS** — aceptación de **1.803 → 971 caracteres** (25 → 16
líneas) + comando **`/privacidad`** con el detalle, registrado **sin gate de consentimiento**
(poder leerlo antes de aceptar es la condición para que la primera capa cuente como informada) y
listado en `/help`. **Base jurídica declarada** en la matriz por primera vez, con la recomendación
(interés legítimo para la herramienta de trabajo; consentimiento explícito solo para lo que lo
exija) y el porqué: **la churn es consecuencia de la base elegida, no de la redacción**. Todo en el
MISMO salto a v5 ⇒ una sola re-aceptación.

**Lo que el dúo cazó en esta ronda, y era grave:**
- El «detalle completo» **no era completo**: faltaban responsable identificado, base jurídica, cómo
  retirar el consentimiento, reclamación ante la AEPD y transferencias. Los tenía en la matriz
  INTERNA, que ningún técnico lee.
- **Al acortar perdí el alcance de la promesa**: la versión larga decía «se retira tu identificador
  *de tus consultas y valoraciones*» y el resumen dejó «se retira tu identificador», a secas.
  Regresión introducida por el propio refactor.
- **El tripwire protegía solo la primera capa.** Moví la sustancia a `_PRIVACY_DETAIL` y la dejé
  fuera del hash: se podía cambiar un destinatario, una finalidad o un plazo manteniendo v5 y sin
  que nadie re-aceptara. El agujero lo abrió el refactor que reducía fricción. El hash cubre ahora
  las dos capas.
- **`display_name` se recogía sin declararlo**: `/accept [tu nombre]` lo guarda en `user_consent` y
  no aparecía en ninguna capa.
- Precisión: «cada pregunta» era inexacto (saludos y despedidas retornan antes de `log_query`); el
  gate `/accept` prueba una acción técnica, **no** la validez jurídica de la base; y la misma
  categoría de proveedor **no da inmunidad** — si el sustituto cambia país, garantías o
  subencargados, es material igual.
- Un test era **circular**: la lista de encargados estaba escrita en el propio test. Ahora se **lee
  de la matriz**, así que añadir un proveedor al documento y no al aviso lo rompe.

**Techo con dientes**: un test falla si la aceptación vuelve a pasar de 1.000 caracteres — quien
añada detalle ahí tiene que decidir si va a la segunda capa o si sube el techo a conciencia.

**Riesgo declarado y ACEPTADO.** Los términos prometen que a los 24 meses «se retira tu
identificador», y hoy esa promesa **no es ejecutable** (ni programada). Se mantiene, no se
diluye: la fila más antigua vence en **2028**, hay margen de sobra para aplicar la propuesta, y
debilitar el compromiso ante quien consiente sería la salida fácil y peor. Lo que sí exige es
que aplicar la propuesta deje de ser opcional antes de esa fecha — y que `user_consent` y los
exports a disco, que hoy conservan identificadores sin plazo, entren en el alcance.

**Lección #60.** Un mecanismo de cumplimiento que no puede ejecutarse **aparenta** cumplimiento,
y eso es peor que no tenerlo: el dry-run decía «0 candidatas» y se leía como «listo». Solo lo
destapó verificar el EFECTO contra la base real — el código era correcto y el sistema no.

---

## DEC-178 (s296) — Seudónimo estable, consentimiento append-only y marca de calidad del feedback

**Contexto.** Al explicarle a Alberto los pendientes de la matriz en lenguaje llano, aparecieron
tres cosas que el diseño de s295 no cubría y una finalidad nueva.

**Decisiones de Alberto (4-ago).**
1. **Seudónimo estable en lugar de NULL.** Su miedo, literal: perder el corpus de un técnico bueno
   que se vaya. Con NULL el contenido sobrevive pero **la agrupación no** — 200 preguntas
   excelentes sueltas, sin poder saber que son de la misma persona. Con un código aleatorio
   estable, el corpus sobrevive agrupado y el vínculo con la persona no.
2. **Los exports llevan ese mismo código.** Un seudónimo para la retención y otro para los exports
   darían dos numeraciones que no casan. Una sola pieza desde el principio ⇒ el identificador real
   **no sale nunca** de la base.
3. **`user_consent` append-only** por (persona, versión) con su fecha.
4. **Enlace en `feedback`** para que cascadee. *Deuda declarada, NO resuelta*: lo verdaderamente BP
   sería un solo canal de feedback en vez de dos; es refactor de producto, no de cumplimiento.
5. **Supresión a petición = DESVINCULAR**, no borrar; `/borrar` autoservicio NO se construye.
6. **Marca de utilidad + posible bonus por CALIDAD.**

**El diseño, y por qué así.**
- La correspondencia vive en una tabla (`persona_seudonimo`), no en un HMAC: los identificadores
  de Telegram son un espacio pequeño y enumerable, así que con la clave se deshace el seudónimo.
  Con tabla, la irreversibilidad llega en un momento explícito y auditable — **el borrado de la
  fila**, que va el último y en la misma transacción.
- **Contrapartida declarada**: esa tabla es dato personal mientras existe. Se ha cambiado un riesgo
  difuso (el identificador esparcido por exports en varios discos) por uno concentrado y gobernado.

**La pieza load-bearing del bonus.** `service_role` —la identidad del proceso con el que habla el
técnico— **pierde el UPDATE de TABLA** sobre `answer_feedback` y recibe UPDATE de COLUMNA sobre lo
que el voto necesita. El dato que sostendría un incentivo **no puede escribirse desde el canal que
toca el interesado**. Esto ENDURECE la postura de julio: quita un privilegio, no añade.

**`TERMS_VERSION` v6 → v7.** El aviso prometía que los datos no se usaban «para decisiones sobre
ti», y un bonus **lo es**. Se declara el reconocimiento de aportaciones, que la marca la pone una
**persona** al revisar y que **cualquier decisión la toma una persona**, no un cálculo automático.

**Lo que se le dijo a Alberto y NO se hizo, porque no procede.** (a) Un seudónimo **no** libera del
permiso: el dato seudonimizado sigue siendo personal, y lo que determina si hace falta base nueva
es la FINALIDAD, no la identificabilidad. (b) Los «permisos especiales a ciertos técnicos» mezclan
dos cosas: **ponderar por calidad** es decisión de ingeniería y no necesita permiso de nadie; un
**opt-in de colaborador** para entrenar un modelo propio sí es consentimiento, y hay que pedirlo
ANTES de recoger, no después.

**Riesgo de producto declarado (no legal).** Pagar por feedback cambia lo que el feedback mide: se
mediría quién ha entendido cómo se cobra, no dónde falla el bot, y el corpus de evaluación se
llenaría de ruido generado por el propio incentivo. De ahí que la marca sea por **consecuencia**
(`corrigio` / `gold` / `corpus` / `ninguna`), adjudicada por una persona después del hecho.

**Dos fallos que solo aparecieron EJECUTANDO** (CI contra PostgreSQL real, 19/19 tras arreglarlos):
- Quien no tuviera código quedaba **fuera de la retención en silencio** (`0 tocadas` y a otra cosa).
- El borrado del vínculo **no veía las filas recientes** —la propia política de ventana se las
  oculta al rol— y lo destruía antes de tiempo, lo que habría **partido el corpus en dos códigos**.
Ambos se leen correctos en el código; la diferencia la marca ejecutarlos. Es la misma lección #60,
tercera y cuarta instancia.

**Alternativas descartadas.** *NULL* (pierde la agrupación, que es el activo). *HMAC con clave*
(reversible por enumeración; irreversible solo destruyendo la clave, y entonces no se puede volver
a emitir el mismo código). *Dejar el UPDATE de tabla a `service_role`* (el interesado podría influir
en su propia valoración). *Contar votos para el bonus* (se infla en una tarde).

**Dúo completo (2 rondas sobre s296, ambas con bite).** El cross-model cazó que **los exports
no agrupaban nada**: `_seudonimizar` leía el código de `query_logs.seudonimo`, columna que solo
se rellena al vencer el plazo ⇒ hasta 2028 todas las filas caían bajo el mismo literal. La
finalidad que motivó la pieza estaba invertida, y no se veía porque la columna existe y el
código se ejecutaba sin error. También: el código solo se emitía en `/accept` (quien ya aceptó
no vuelve a pasar por ahí), el claim «append-only» era más fuerte que el mecanismo, el aviso
prometía guardar el consentimiento «mientras uses el bot» contra lo que dice la matriz, y el
workflow de Postgres **no se disparaba** con los ficheros de s296.

El sub-agente añadió cuatro, tres silenciosos:
- **El bootstrap deshacía la pieza 5.b.** `supabase_schema.sql` se re-ejecuta y restaura el
  `UPDATE` de TABLA en `answer_feedback` con postcondición de igualdad exacta ⇒ la marca de
  utilidad volvía a ser escribible desde el canal del interesado, sin que nada fallara. s296
  lleva ahora su sección de bootstrap, como s295.
- **El trigger anti-reidentificación bloqueaba marcar la utilidad** de todo voto colgado de una
  consulta ya disociada — es decir, del feedback MÁS ANTIGUO, que es justo el que ha tenido
  tiempo de demostrar que sirvió. Acotado a las columnas que re-identifican, con `WHEN`.
- **`persona_seudonimo` nacía sin `REVOKE` de `anon`/`authenticated`**, única tabla de datos
  personales sin él; Supabase concede todo por defecto sobre las tablas nuevas. El fixture no
  creaba esos roles ⇒ el CI no podía cazarlo: ahora los crea y reproduce la concesión.
- Las postcondiciones de s295 dejaban de pasar si se re-ejecutaba DESPUÉS de s296 (el UPDATE
  pasa de tabla a columna): las propuestas quedaban orden-dependientes.

**Un arreglo mío que estaba mal, y se retira en vez de maquillarse.** Acoté el borrado del
vínculo con una ventana sobre `persona_seudonimo.created_at` — que dice cuándo se emitió el
código, no cuándo vencen los datos: un código emitido por el propio job no se podría borrar
jamás. El CI lo cazó. Al revisarlo, la preocupación que lo motivaba era infundada: borrar el
código de quien aceptó y nunca preguntó no pierde nada, porque no agrupa ninguna fila. Retirado
y **declarado**.

**Claims acotados.** «El identificador no sale nunca de la base» era falso: SÍ se lee al proceso
que genera el export; lo garantizado es que **no se escribe al fichero**. Y la matriz se
contradecía a sí misma sobre el contenido de los exports.

**Gaps nuevos, declarados y NO resueltos.** El código no es estable «siempre» (tras destruir el
vínculo, quien vuelve recibe uno nuevo — es la irreversibilidad funcionando); el append-only
cubre el eje versión pero **no conserva la traza de una revocación**; y el feedback espontáneo
puede perderse si su consulta se borra entre medias.

**Verificado**: 22/22 contra PostgreSQL real en CI, incluidos los cuatro fallos que solo
aparecen ejecutando. Suite completa verde.

---

## DEC-179 (s297) — Libro de eventos de consentimiento + feedback resistente + marca en el canal espontáneo

**Contexto.** Al cerrar s296 quedaron tres gaps declarados. Alberto preguntó cómo resolverlos y
si las cuatro categorías de utilidad eran BP; aprobó el lote propuesto.

**Lo decidido primero, porque es contraintuitivo: el gap del código NO se resuelve.** Que quien
vuelve tras 24+ meses de ausencia total reciba un código nuevo es el precio de la garantía —
conservar la correspondencia tras el plazo significaría que el vínculo no muere nunca.
Alternativa descartada: periodo de gracia antes de destruir (alarga la retención de un dato
personal por comodidad — lo contrario de lo prometido).

**Lo construido.**
1. **`consent_events`** — patrón estado + libro: `user_consent` sigue siendo el estado vigente
   (lo que `has_consent` lee); el libro es la EVIDENCIA, de **solo inserción para el bot**
   (inmutabilidad estructural: ausencia de privilegio, no promesa de código). `set_consent`
   escribe el evento TRAS el estado (si el estado falló, no hay qué evidenciar), fail-open con
   aviso. La revocación manual de `DG_DEPLOYMENT` inserta su evento ANTES del UPDATE — un libro
   vale lo que valen sus escritores. Backfill declarado como RECONSTRUCCIÓN: el upsert antiguo
   destruyó v1..v6 y el libro no lo finge.
2. **Reintento sin enlace en `log_feedback`** ante FK colgante (23503 definitivo, nunca
   timeout — el primer POST pudo confirmarse): el feedback sobrevive suelto en vez de morir.
   Mismo patrón que el fallback de traza de `log_query`.
3. **`utilidad` en la tabla `feedback`** — la marca solo cubría el canal del voto; el
   espontáneo, por donde llega parte del feedback más valioso, no tenía dónde marcarse. Sin
   cambio de privilegios: `service_role` no tiene UPDATE ahí desde julio.
4. **Borrador de ponderación** (`docs/RGPD_PONDERACION_INTERES_LEGITIMO.md`) para que el asesor
   revise en vez de producir: interés, necesidad, ponderación con contrapesos declarados
   (transferencias pendientes; la arista laboral del incentivo), derecho de oposición, y qué
   cambia si se aprueba. SIN VALIDAR y así rotulado.

**Sobre la taxonomía de utilidad (respuesta a Alberto): BP en lo esencial** — mide consecuencia
auditable contra artefactos reales (commit/gold/manual), `NULL` ≠ `ninguna`, decisión final
humana, sin peso de severidad a propósito (lo juzga quien paga; codificarlo hoy = aparato).
Matices declarados: las categorías no son mutuamente excluyentes (se marca la dominante;
multi-etiqueta solo si el volumen lo exige) y hasta s297 solo cubrían un canal de los dos.

**Verificado**: 7 unitarios nuevos + integración contra Postgres real (backfill reconstruye,
el libro es de solo inserción EJECUTANDO como service_role, re-aceptar no pisa la evidencia,
roles anónimos sin acceso, la marca del canal espontáneo inalcanzable para el bot). La ruta de
la migración s297 añadida al workflow ANTES del primer push — lección de s296, donde el CI no
se disparaba con los ficheros nuevos.

**Dúo sobre s297 (dos rondas paralelas, ambas con bite — 15 hallazgos, 4 críticos).**
- **La marca NO era inalcanzable** (cross-model): cerré el UPDATE pero `service_role`
  conservaba INSERT de TABLA, que cubre toda columna — el bot podía insertar una fila con
  `utilidad` ya puesta, en `feedback` Y en `answer_feedback` (agujero heredado de s296).
  Ahora INSERT de COLUMNA sobre exactamente lo que el bot escribe, con postcondición.
- **Un usuario revocado seguía entrando hasta reiniciar el worker**: `_consent_cache` era un
  set sin expiración. Ahora TTL de 10 min; la revocación surte efecto sin reinicio.
- **El reintento de FK podía re-materializar datos borrados**: conservaba las copias de la
  pregunta/respuesta — el dato recién suprimido — sueltas y fuera de cascada. Ahora suelta
  también las copias; el texto del feedback sí se conserva (mensaje nuevo, tratamiento fresco).
- **El backfill corrompía el libro al re-ejecutar** (ambos revisores): sin guarda, una segunda
  pasada re-insertaba un 'accepted' por fila viva con COMMIT limpio y la postcondición de >=
  tragándoselo. Ahora: gate libro-vacío + columna `origen` (reconstruido ≠ presenciado) +
  postcondición de IGUALDAD. Con test que RE-EJECUTA la migración de verdad.
- **El fail-open no era fail-open** (sub-agente): una excepción de TRANSPORTE en el POST del
  evento, con el estado ya commiteado, devolvía False — el bot pedía reintentar un
  consentimiento ya dado y el usuario quedaba atascado en la caché de misses. El POST del
  evento vive ahora en su propio try, y la caché se actualiza en cuanto el estado commitea.
- **La revocación manual en dos sentencias sueltas** podía dejar evidencia en FALSO POSITIVO
  (evento 'revoked' sin efecto real): el runbook la exige ahora en BEGIN…COMMIT.
- **FRAMING cazado en el LIA**: presentaba como vigentes garantías construidas pero NO
  aplicadas (aviso de estado añadido: la ponderación no se firma hasta que la cola s295→s297
  esté viva); afirmaba «ya se probó que el laboratorio no predijo los fallos orgánicos» con
  n=1 y ese n=1 EN CONTRA (retirado, con la retirada explicada en el propio doc); contaba 4
  encargados fuera de la UE y son 5.
- Coherencia `utilidad`↔`utilidad_revisada_at` gobernada por CHECK en ambas tablas; matriz y
  runbook alineados sobre el destino de `consent_events` ante una supresión (**[DECIDIR]** con
  el asesor: borrar vs conservar como prueba); postcondiciones al patrón de anchura de la casa;
  residual declarado: el CI conecta como superuser y no observa la RLS del camino operador.

**Lo que el dúo confirmó sólido**: `_fk_rejected` y el no-reintento ante timeout; el orden
evento-tras-estado; el backfill en primera ejecución; el patrón de frontera; que el bootstrap
NO repite el bug s296.

---

## DEC-180 (s298) — Bootstrap al estado final: la clase «re-ejecutar deshace» muere en CI

**Contexto.** Alberto aplicó la cola s295→s296→s297 en producción (5-ago) y ejecutó el dry-run
(0 candidatas, rol asumido). Verificado contra el catálogo: rol, 4+3 políticas, trigger,
seudónimo, primer evento del libro, privilegios de columna exactos. **La retención es
ejecutable y está dormida** — su estado correcto hasta 2028.

**El hueco que el despliegue dejó al descubierto.** `supabase_schema.sql` re-concedía el estado
PRE-cola: re-ejecutar el bootstrap deshacía en silencio la protección de la marca (INSERT/UPDATE
de tabla de vuelta a `service_role`). La clase s296, viva en `main` hasta esta rama.

**Lo construido.** (1) Bloque frontera al ESTADO FINAL entre marcadores explícitos, con
expectativas de tabla y de columna POR SEPARADO y re-afirmación condicional de las tablas de la
cola. (2) Columnas s296/s297 en el bootstrap con las mismas sentencias idempotentes ⇒ bootstrap
y cola convergen en cualquier orden; la maquinaria de retención conserva UNA fuente (la cola).
(3) **El test que mata la clase**: extrae el bloque REAL del fichero y lo RE-EJECUTA tras la
cola en el Postgres del CI, exigiendo marca inalcanzable, voto vivo y libro intacto — la
prevención pasa de procedimiento a CI (cierra el residual declarado en s297). (4) Docs
canónicos al estado aplicado (matriz, runbook, LIA, PLAN, TECH_DEBT, rótulos de las
migraciones — que ya no dicen «NO EJECUTAR» sino «APLICADA + idempotente»).

**El dúo, una ronda más con bite (5 hallazgos, todos aplicados).**
- **Sub-agente, el gordo**: mi claim «sin la cola, el bot funciona» era FALSA en `/accept` — el
  upsert del consentimiento exige el índice único (persona, versión) que solo creaba s296; en
  solo-bootstrap, el gate fail-closed no dejaba entrar a NADIE. Nadie había arrancado nunca un
  bot solo-bootstrap: la clase «declarar de más», aplicando mi propio criterio a las columnas
  pero no a los ÍNDICES que el mismo write-path exige. Bloque de consentimiento replicado.
- **Cross-model**: una `answer_feedback` legacy pre-s294 rompía la re-ejecución (falta
  `reason_class` → el GRANT de columna revienta; falla cerrado pero contradice «re-ejecutable»)
  → ADD COLUMN idempotente. Las tablas condicionales no tenían el MISMO listón de postcondición
  que las cinco fijas → ahora sí (RLS, anónimos a cero, igualdad). `has_any_column_privilege`
  solo prueba «alguna columna» → positivas NOMINALES por cada columna que el bot escribe, y el
  test de re-ejecución ejerce TODOS los write-paths (voto + reason/comment + feedback con
  enlace + re-aceptación), no solo el voto. Y PLAN/TECH_DEBT seguían diciendo «no ejecutable»
  — actualicé la matriz y no la fuente canónica de estado: la contradicción interna era mía.

**Guardas actualizadas al invariante nuevo**: dos tests anclaban el texto viejo del boundary
(el grant de tabla que quitamos a propósito); ahora protegen el nuevo — incluido que el viejo
NO vuelva (`not in`).

## DEC-181 (s299) — El reloj DENTRO de la base: pg_cron + la pasada como función única

**Decisión (Alberto, 5-ago, segunda tanda):** programar la retención. **Diseño elegido:
pg_cron dentro de Supabase** — el job mensual (`rgpd-retencion-mensual`, día 1, 04:30 UTC)
llama a `public.rgpd_retencion_pasada('cron')`, que asume `rgpd_retencion` en su ENCABEZADO
(`SET role` a nivel de función) ⇒ la ventana de 24 meses sigue siendo invariante del motor
también en la ejecución programada, y **ninguna credencial sale de la base**. Cada pasada
confirmada deja recibo en `rgpd_recibos` (solo-inserción, ilegible para el bot). Esto SUPERA
la premisa de s295 («programar exigiría un rol runner LOGIN») — aquella valía para un cron
EXTERNO (GitHub/Railway), que habría guardado fuera un `DATABASE_URL` de operador más
potente que el `service_role` que s295 evitó tocar.

**La pieza estructural: UNA implementación.** La pasada se movió de Python a la función SQL;
`scripts/rgpd_retencion.py` queda como driver (`--aplicar` = commit; dry-run = la MISMA
pasada + rollback, recibo incluido). Alternativa descartada: mantener el script como
implementación paralela para no reescribir sus tests — dos implementaciones de una operación
irreversible driftan, y una de las dos «cumple» sin cumplir. Sin `--meses` sigue: el plazo
se cambia por migración. La ventana NO se repite en la función (una sola fuente: las
políticas RLS); a cambio la función ASERTA el mecanismo (RLS forzada + política presente en
las 4 tablas) antes de tocar nada — el reloj corre desatendido y un `DISABLE ROW LEVEL
SECURITY` de debug la habría convertido en disociador de filas de ayer con recibo normal.

**El dúo, dos rondas (9 hallazgos ronda 1, todos aplicados; 2 CRÍTICOS):**
- **Sub-agente, el gordo — VIVO EN PRODUCCIÓN**: `rgpd_quedan_identificados` (s296) nació
  ejecutable por `anon`/`authenticated`/`service_role` — los **default privileges de
  Supabase conceden EXECUTE sobre toda función nueva de `public`** y s296 solo revocó
  PUBLIC. Un oráculo de pertenencia («¿este telegram_user_id tiene datos?», SECURITY
  DEFINER) alcanzable por PostgREST RPC con la clave anónima. VERIFICADO contra el catálogo
  vivo (`pg_default_acl` + `has_function_privilege`) antes de actuar (regla C). Cierre:
  REVOKE nominal en s299 + bootstrap + postcondición, y **el fixture de CI ahora reproduce
  el default de FUNCIONES** — antes era estructuralmente ciego a la clase (por eso mi propio
  REVOKE solo-PUBLIC pasó el CI y habría tumbado la migración en el SQL Editor contra su
  propia postcondición).
- **Cross-model, el conceptual**: el punto de no retorno no miraba `answer_messages` — un
  ancla RECIENTE de una consulta ya vencida (la ventana no deja borrarla) mantenía la cadena
  `telegram_chat_id → query_log_id → seudónimo` tras destruir el vínculo: re-identificaba el
  corpus recién disociado. La función aprende la 4ª tabla + test de edades desalineadas.
- Resto: membresía SET exigida a quien programa el cron (+postcondición con username/activo/
  horario); `p_origen` sin DEFAULT (un `SELECT` suelto estampaba `'cron'` falso en un recibo
  inmutable); recibo local por `tocadas` (la pasada solo-vínculos no dejaba recibo); test del
  camino de operador NO-superusuario; celdas stale de la matriz («hoy bloqueado», «NOT
  NULL», «no cascadea») corregidas; Voyage re-etiquetado de «certificada» a «declaración
  nominal del proveedor» (mi clase de framing, otra vez, cazada por el cross-model).

**Transferencias (pendiente 6): DOCUMENTADAS** con fuente y fecha (5-ago) en la matriz —
SCCs-en-DPA (Anthropic, cuya PROPIA política no declara DPF; OpenAI; Railway; Supabase),
DPF declarado por el propio proveedor solo Voyage (vía MongoDB), Telegram sin DPA
(posición: responsable propio del transporte). Las valida el asesor contra el registro.

**Ronda 2 del dúo (sobre el delta de los fixes): SÓLIDA con 10 hallazgos menores/medios, aplicados o declarados.** Los que cambiaron código: la aserción de ventana pasa de presencia a EXCLUSIVIDAD + predicado (una 2ª política permisiva de debug se OR-ea y abría la ventana con la aserción en verde — ejercido en CI con 3 escenarios); el default de TABLES del fixture aprende `service_role`; message_id determinista (el `hash()` salted era flake irreproducible). Los declarados sin cablear (proporcionalidad): carrera del punto de no retorno en READ COMMITTED (consecuencia = el «corpus en dos códigos» YA declarado en s296, ~0 a esta escala; SERIALIZABLE+retry si entra volumen — TECH_DEBT); recibos re-clasificados como dato SEUDONIMIZADO mientras viva la correspondencia (fila de la matriz corregida — decían «no identifica»); el alcance del recibo acotado («toda fila persistida = pasada confirmada» vale contra el BOT, no contra el owner); vigilancia trimestral del reloj (un reloj roto aborta SIN recibo, solo visible en job_run_details — runbook en la matriz); celda «vivo (mensual)» corregida a «manual hoy; mensual al aplicar s299».

**Estado FINAL (misma tarde)**: PR #210 mergeada y **migración APLICADA por Alberto** (SQL
Editor). Verificado contra el catálogo tras aplicar: job `rgpd-retencion-mensual` ACTIVO a
nombre de `postgres` (horario y comando exactos), oráculo CERRADO para los tres roles de la
API, recibos blindados, y dry-run del driver con exit 0 — con 2 vínculos sin datos en
NINGUNA tabla que caerán en la primera pasada real (huérfanos del backfill s296; caso
benigno declarado). **Primer recibo esperado: 1-sep, 04:30 UTC**; vigilancia trimestral en
el runbook. Traza de review: `evals/adversarial_review_log.jsonl` (2 rondas, 5-ago).

## DEC-182 (s300) — Los tres frentes de Alberto, con forma auditada; y la arquitectura como invariante de CI

**Contexto.** Alberto pidió añadir al plan: dashboard de seguimiento, refactoring hacia una
arquitectura más modular, y automatización (ingesta, feedback→mejora). En vez de asentir o
construir, se auditó cada frente con evidencia (20 agentes de arqueología + verificación
adversarial de claims; luego censo de 10 agentes para el blueprint). Resultado: **los tres
entran, ninguno con su forma nominal.**

**(1) Dashboard SIN app.** DEC-162f (descartar Grafana/web «hasta técnicos y volumen») SIGUE
vigente — no se reabre: la tubería ya existe (vistas `bot_health_*` VIVAS en el catálogo,
digest, captura de voto+motivo+prosa). El gap real: CERO herramientas leen `reason_class`/
`comment` (el porqué del 👎 es invisible), las vistas no están en migración versionada, los
shortcuts no loggean (#31) y `utilidad` no tiene camino de escritura. Todo S; front = el
dashboard de Supabase. Descartado: app web nueva (auth+despliegue+cumplimiento).

**(2) Modernización dirigida por blueprint, NO reescritura** (`docs/BLUEPRINT_MODERNIZACION.md`).
Medido: `src/` no es bola de barro (2 ciclos deliberados, 1% duplicación, seams limpios); el
problema es ACRECIÓN (~30% no alcanzable desde el Procfile) y su causa raíz: nada impedía que
los experimentos sedimentaran en `src/`. La pieza estructural — respuesta directa al «aquí tú
controlas más» de Alberto: **la arquitectura vive en el CI, no en mi disciplina** —
`tests/test_import_contract.py` (L0, HECHO): matriz de paquetes + 6 excepciones EXACTAS con
trinquete (solo encogen; retirar la arista obliga a borrar la excepción en el mismo diff — y
hace al test no-vacuo) + 2 ciclos allowlisted + cuarentena de lane vetada + **cuarentena
lógica de la isla-harness (35)** + raíces prohibidas (`harness`/`scripts`/`tests`/`evals`,
sin lista de excepciones posible) + prohibición total de `importlib`. Nace verde 9/9. Lotes:
L1 catalog_store → L2a isla→`harness/` (33/35) → L2b flags recortado → L2c split lane vetada
→ L3 embed; paridad byte-a-byte (método del orquestador) + sellos enumerados ANTES de mover.
Alternativas descartadas: big-bang/reescritura (freeze-contracts + sellos + demo-abilidad en
due-diligence), microservicios, Fase-E packaging, partir retriever.py en estos lotes.

**(3) Automatización proporcionada.** Ingesta: guardas anti-manifiesto-vacío (el corpus vive
SOLO en OneDrive; desde C:\dev el inventario produce VACÍO sin fallar), playbook re-escrito
(el actual cita un pipeline borrado en s43), `ingest_new.py` con gates+dry-run (M). Ops:
`gold_store validate` a CI (su docstring miente), verificación corpus↔store↔chunks_v2,
`BOT_ERROR_LOGGING=on` (Alberto). PREMATUROS declarados: eval-en-cron y auto-ingesta por
scraper — obligatorios con el primer técnico real.

**El dúo sobre el lote L0 (2 críticos del cross-model, ambos verificados con ancla):** (X1)
el mecanismo del gate C1 RECHAZA paths fuera de `scripts/`|`src/` (HOLD en
`s277_c1_p1.py:1211-1216`) ⇒ los 2 módulos isla que un probe SELLADO importa en
function-local (`visual_gold`, `omission_correction`) NO pueden moverse sin tocar el
mecanismo → quedan anclados en `src/` bajo cuarentena lógica, con trigger. (X2) el recolector
no veía `harness/` como raíz ⇒ tras L2a el contrato no habría bloqueado src→harness — regla
de raíces prohibidas nacida CERRADA. Sub-agente: SÓLIDA con 6 menores (mutation testing 9/10;
ISLA verificada exacta por censo independiente). Tally: 2 rondas s300, 11+16 hallazgos entre
workflow y dúo, 0 falsos positivos. Traza: `evals/adversarial_review_log.jsonl`.

**Estado**: rama `claude/s300-blueprint-l0`, PR abierta. Los lotes L1-L3 esperan el GO de
Alberto (cada uno con su dúo); los frentes (1) y (3) son sesiones S/M sueltas.

## DEC-183 (s301) — El «dashboard» resultó ser abrir grifos; y el aviso mandó sobre la métrica

**Decisión (frente 6 + S-wins del 7).** Nada de app: export del 👎 con motivo y prosa
(`tap_reason`/`tap_comment` — el dato existía y CERO herramientas lo leían), columna
`route` + log de los shortcuts de CONSULTA y de los dos clarify (#31 cerrado; parte del
paquete #60 cubierta), migración s301 con las 2 vistas de salud POR FIN versionadas + 3
vistas agregadas nuevas (feedback semanal, motivos del 👎, uso por canal;
`security_invoker`, API a cero), Gold gate en CI, guardas de ingesta anti-vacío, y
`scripts/marcar_utilidad.py` (el camino de escritura del operador para la marca del
bonus). Front = dashboard de Supabase; DEC-162f intacto.

**El hallazgo que manda: el AVISO es un contrato, también para la telemetría.** El
cross-model cazó (CRÍTICO) que loggear saludos/gracias/adiós contradecía la promesa
literal del aviso v7 («Los saludos y las despedidas no se registran») y la minimización
que la LIA usa como argumento. Se revirtió: la cortesía NO se registra; sus valores
quedan RESERVADOS en el CHECK para un aviso futuro. Regla que deja: **una métrica nueva
se contrasta contra el aviso ANTES de cablearse** — la observabilidad también es
tratamiento.

**Los otros dos con dientes:** (a) al verificar la carrera de deploy contra el catálogo
VIVO apareció que la migración de `rag_trace` (julio) NUNCA se aplicó — el bot lleva
semanas guardando logs sin traza por su fallback silencioso; el fallback pasa a ser
COMPONIBLE por columna nombrada (dos faltas, dos pasadas — los manejadores de un solo
tiro perdían log Y teclado de feedback cuando el 400 nombraba la otra columna primero) y
la migración de julio entra en la cola del SQL Editor; (b) el patrón de la casa, otra
vez: mi detector laxo (`'route' in text`) habría DEGRADADO a silencio la violación del
CHECK de ruta — misclasificando como 'rag' justo la métrica que el lote existe para dar;
detector estricto (PGRST204/42703 + columna nombrada) con test de la rama 23514.

**Dúo**: cross-model 4/4 (1 crítico) + sub-agente 8/8 (NO-SÓLIDA→fixes; H4 verificado
contra prod y era peor de lo especulado) — 0 falsos positivos. 12 hallazgos aplicados.
Tally: `evals/adversarial_review_log.jsonl`.

**Pendiente de Alberto**: aplicar en el SQL Editor, en una sentada y en este orden,
`20260720095702` (rag_trace — la de julio) y `20260806150000_s301` (route + vistas);
luego crear el dashboard de Supabase sobre las 5 vistas (clicks, no código).

## DEC-184 (s302) — El packet de adquisición desmonta el barrido: 7 huecos, no 44 — y la CAD-171 ya la teníamos

**Contexto.** El PLAN llevaba desde s294 con «44 documentos que nuestros manuales citan y no
tenemos» como frente de trabajo, con la Guía Avanzada de Configuración de la CAD-171 en
cabeza — el documento del primer fallo orgánico del bot (DEC-176). s302 adjudicó los 44
candidatos uno a uno (8 agentes; clasificación + investigación de vías) antes de pedir nada.

**Resultado: mi encuadre era falso en las DOS afirmaciones.**

1. **De 44 candidatos, 7 son huecos reales** (16%). 18 ya estaban EN EL CORPUS bajo otro
   nombre de fichero — incluido el nº1 del ranking (`997-340-003`, 11 citas, que es
   `MPDT212.pdf`) —, 10 son referencias de PIEZA o rangos de direcciones (`001-127` es «la
   dirección 1 a 127» de un lazo), 5 son erratas de imprenta o pies de página.
2. **La «Guía Avanzada de Configuración» de la CAD-171 NO falta: es el
   `CAD-250_Manual-Configuracion-MC-380-es-2026-c`**, ya ingestado y ya mapeado a
   `detnov:cad-171` como `primary` en `doc_map.jsonl` — cuyo control de revisiones dice
   «Adaptación para CAD-171 y CAD-201» y cuyo §5.4 p.29 documenta EXACTAMENTE la ruta que el
   bot falló (`AJUSTES > AVANZADO`). El primer fallo orgánico es **100% de SELECCIÓN**:
   DEC-176 se REFUERZA, y no se arregla comprando nada.

**La clase, por CUARTA vez** (`feedback_corpus_gap`): atribuir a hueco de corpus lo que es
fallo propio. Aquí con un agravante nuevo — no fue un instrumento LLM el que sobre-atribuyó,
fui yo elevando la salida CRUDA de un probe («candidatos, NO confirmados», lo decía su
propio JSON) a frente de trabajo del PLAN, y manteniéndolo tres sesiones sin adjudicar.
Regla que deja: **la salida de un probe no entra al PLAN como hecho hasta estar adjudicada**;
si entra como candidata, se rotula candidata EN EL PLAN.

**Lo que SÍ queda (y es accionable)**: 3 documentos con valor real — `997-340-005`
(programación por PC de la ID1000, la familia que tenemos a medias), `997-415`
(actualización ID50/ID60/ZX50: 6 citas, dos marcas, un solo PDF) y **`997-412`** (Sinóptico
IDR, 4 citas) — este último un hueco REAL que **el barrido perdió** por un `break` en citas
dobles (TECH_DEBT #62: 4 bugs del instrumento, uno de ellos lo hace no-fiable para NEGAR).

**Vía de obtención (verificada con HTTP real, sin inventar URLs)**: en `notifier.es` y
`morley-ias.es` **los PDF están abiertos y el ÍNDICE está cerrado** — lo escaso no es el
fichero sino saber qué existe. Plan en paralelo: descarga directa por nombre (yo), 3 altas
de partner (Alberto: Notifier ES, Morley-IAS ES, Morley Professional UK) y, si se atasca,
petición a `soporteHLSI@honeywell.com` **pidiendo el LISTADO, no los ficheros**. El portal
`firesecurityproducts.com` (runbook s55) NO sirve: cubre Carrier/Kidde, no Honeywell.

**Consecuencia para el rumbo**: el frente «adquisición» baja de 44 documentos a 3 con
valor + 3 altas, y **el trabajo de calidad vuelve a retrieval/síntesis** — donde el primer
fallo orgánico dijo desde el principio que estaba.

## DEC-185 (s303-s304) — El fallo orgánico cerrado en firme: SELECCIÓN DE SECCIÓN; la hipótesis de identidad murió en el dúo (y era mía)

**Decisión**: el único fallo orgánico (CAD-171, DEC-176) queda clasificado DEFINITIVO como
**selección de sección dentro del documento correcto**: el bot tuvo servidos en la misma
pasada el §5.4 AVANZADO (rango 1) y el §5.1 GENERAL (rango 4) del mismo `MC-380` y encabezó
con la ruta del §5.1 — respondió DESDE el documento, no lo descartó por su etiqueta.
Retrieval e identidad descartados por dos vías independientes. **La hipótesis intermedia
(«la identidad adjudicada no llega al chunk: 57% del corpus huérfano») queda RETIRADA.**

**Motivo (verificado, no opinión)**: el dúo derribó la hipótesis con 3 hechos que comprobé
contra el repo antes de aceptar: (1) mi instrumento paginaba `limit/offset` SIN `ORDER BY` —
perdía 12-21% de los documentos, DISTINTOS por pasada; cifras no reproducibles; (2) medía
coincidencia-de-etiqueta cuando la pregunta correcta es ALCANZABILIDAD — la granularidad de
familia (`pm='2X-A'`, 26 variantes en el mapa) es deliberada (T3/s285); (3) la identidad SÍ
llega al retrieval por el seam 2 doc_map-aware (`IDENTITY_RESOLVE=on`, DEC-084) y el
`series_registry`, que para el caso motivador declara la serie Vesta `[CAD-171, CAD-201,
CAD-250]` con el MC-380 como shared_doc DESDE s63 (DEC-043). Instrumento v2 (orden estable +
pregunta de alcanzabilidad): **35 huérfanos (4,1%) / 55 ids**, casi todos `unresolved:`
(candidatos que `catalog_store` declara no-consumibles). No hay lever.

**Alternativas descartadas**: diseñar el lever de propagación (backfill chunk-level o join
en serving) — muerto con la hipótesis; re-litigar DEC-059/s77 (el índice de modelos como
oráculo) — no aplica, el seam vivo ya es doc_map-aware.

**Lección (feedback_my_bias)**: verifiqué dos capas (doc_map, product_model) y declaré rota
la cadena SIN comprobar si existía OTRO camino entre ellas — misma clase que negar ausencia
sin agotar las vías de presencia (barrido s302). La pregunta de Alberto («¿ese catálogo
estaba asociado a la CAD-171?») abrió la ronda; el dúo la cerró.

Recibos: `evals/s294_cad171_menu_avanzado_v1.md` (veredicto final, con las DOS rondas y lo
que cayó) · `scripts/s304_identidad_propagacion.py` v2 · `evals/adversarial_review_log.jsonl`.

## DEC-186 (s305) — El techo de la clase «elemento vecino» NO es del modelo; y de paso, el generador no se podía cambiar de modelo (#64, resuelto)

> ⚠️ **EN REVISIÓN desde s320c (12-ago-2026) — NO citar la cifra ni la conclusión de esta entrada.**
> La cifra que sostiene todo lo de abajo («0/3 firmes los tres, máx 2/5») **nunca salió del juez**:
> `s305_techo_modelo_ab.py` sumaba sobre las CLAVES del dict que devuelve `judge_conveyed21` ⇒
> constante 2 en las 9 reps de los 3 brazos; `oracle_firme` era 0 por construcción y las ramas
> «MONTAJE NO COMPARABLE» y «EL TECHO ERA DEL MODELO» eran inalcanzables (TECH_DEBT #75).
> Re-juzgadas con el juez canónico las respuestas que el recibo sí guardó
> (`evals/s320c_rejudge_s305_stored_v1.json` — dos pasadas dieron los mismos 9 votos, pero **solo
> una está versionada**: la otra corrió en scratchpad, así que la reproducibilidad citable es de
> UN recibo): **sonnet-4-6 2/3 firmes ·
> sonnet-5 0/3 · opus-5 2/3**, correlación 9/9 con la aparición literal del valor.
> **Qué cae**: «TECHO CONFIRMADO» y el «NO hay lever de modelo». **Qué lo sustituye**: no «el techo
> era del modelo», sino **INCONCLUYENTE por montaje** — con el control alcanzable, la rama que
> corresponde es «el control SÍ transmite, contradiciendo el 0/5 de DEC-173: explica la divergencia
> antes de leer nada». Y con n=3 por brazo el eje modelo nunca tuvo potencia (p≈4/9 ⇒ P(0 de 3)=0,17).
> **Qué NO cae**: DEC-173 (recibo s293 válido: lectura por clave, respuestas sin truncar, «295»
> ausente en las 3) ni el colateral #64/PR #215 (código real anclado por `tests/test_s305_compat_modelo.py`).
> **También es falso el párrafo «Motivo»** de abajo: las 9 respuestas NO «hacen lo mismo» — 4 de 9
> citan el rango verbatim; nadie las leyó.
> **Re-medición fresca CERRADA** (`evals/s320c_techo_modelo_ab_v2.json`, 5 reps/brazo, 0 votos de
> juez fallidos, respuestas sin truncar): **los TRES brazos ALCANZABLES** — sonnet-4-6 **1/5**
> firmes · sonnet-5 **1/5** · **opus-5 4/5**, max 5/5 los tres ⇒ el script dispara su guarda
> **MONTAJE NO COMPARABLE**. Deja cuatro cosas: (a) el hecho **es alcanzable hoy**, luego el «NO
> alcanzable» de DEC-173 no describe el sistema actual y su corolario «la pair-completion que s292
> iba a diseñar NO pagaría» queda **CONTESTADO**; (b) **este hecho, bajo estas configuraciones,
> transmite de forma MIXTA** (6/15 firmes con evidencia perfecta) — lo cual NO reclasifica la clase
> «elemento vecino» entera: es una sonda de UN hecho, los 15 son 3 generadores distintos y no 15
> réplicas de una población, y la otra instancia (CAD-171) **no se ha re-medido** (corrección del
> dúo s320c a mi «la clase real es transmisión INESTABLE»); (c) `base` = 0/5 en 14 de 15 ⇒ **la
> inyección del carrier aporta un delta claro**, lo que NO localiza el hueco en serving: base y
> oráculo son **generaciones independientes** y el recibo v2 no guardaba la composición servida por
> rep; además 9/15 oráculos fallan **teniendo la evidencia ideal delante**; (d) opus-5 4/5 frente a
> 2/10 **apunta** a un eje de modelo pero **no lo establece**, y conviene darlo como **rango de
> sensibilidad**: p=0,089 con las 15 reps · **p=0,061 con las 12 limpias** (C 4/4 vs A+B 2/8) ·
> C vs A p=0,206. En ninguna lectura se establece. (Fable estimó ≈0,03 para el caso limpio;
> recalculado da 0,061 — regla C.)
> **Caveat declarado**: 3 de las 15 reps corrieron con canal degradado (2 fail-open de hyq-table,
> 1 de enunciados por `ReadError`) y **las 3 dieron 0/5** — incluida la única no-firme de opus-5.
> Correlación sugerente, no establecida (n=3, atribuida por orden de stdout). La corrida NO es un
> freeze-contract limpio.
> **Pendiente**: reescritura de esta entrada CON DÚO (y revisar si DEC-173/DEC-175 siguen cerrando
> etapa 3 sobre una premisa que hoy no se sostiene). Hasta entonces, el ítem 2 del packet B2 no se
> adjudica.

**Decisión**: la clase `hp011#2`/CAD-171 queda cerrada TAMBIÉN por el eje modelo: con el
oráculo de DEC-173 reusado tal cual (misma evidencia inyectada, mismo juez K=5, 3 reps,
única variable = generador), **Sonnet 4.6, Sonnet 5 y Opus 5 dan 0/3 firmes (máx 2/5) los
tres**. Ni una generación nueva ni un tier superior mueven la clase. NO hay lever de modelo.

**Motivo + hacia dónde apunta**: las 9 respuestas (hashes todos distintos — sin caché;
testigo del modelo REALMENTE enviado verde en los 3 brazos) hacen LO MISMO: describen el
DEFAULT del parámetro t.A («--» = activado hasta rearme) en vez del RANGO (05-295 s) que
pide el gold — coherente con DEC-173 («tiene el dato y responde con otro parámetro»").
⇒ el residual apunta a **alcance de GOLD** → ítem de la sentada B2, no de ingeniería.

**Controles que hicieron falta** (cada uno cazó algo): testigo del efecto (cazó mi aserción
demasiado estricta: el reranker DEBE seguir en su modelo — una sola variable); hashes
anti-caché; guarda de veredicto (en el primer smoke 2 brazos ABORTARON por incompatibilidad
de API y la lógica proclamaba «techo confirmado» sobre datos inexistentes — un brazo caído
es dato-que-falta, no un cero). Honestidad: control 2/5 ≠ 0/5 de agosto (corpus tocado hoy;
ambos bajo umbral) — declarado, no vendido como réplica.

**Colateral estructural (#64 RESUELTO, PR #215)**: cambiar `LLM_MODEL` a un modelo de
razonamiento rompía el bot en la 1ª consulta (`temperature` rechazada; `content[0]` es
ThinkingBlock). Fix: rechazo aprendido en runtime + reintento único con identidad de caché
recalculada + extracción de texto por tipo con equivalencia histórica EXACTA (mi 1ª versión
exigía `type=="text"` y rompió 29 tests — un fix de compatibilidad que rompe compatibilidad
es peor que el problema; test del caso exacto añadido). Camino vivo byte-idéntico, anclado
por test.

Recibos: `evals/s305_techo_modelo_ab_v1.json` · `scripts/s305_techo_modelo_ab.py`.

## DEC-187 (s306) — TECH_DEBT #63 resuelto: el fail-open de canal deja de ser invisible; y el dúo cazó el defecto reintroducido en su propio fix

**Decisión**: la degradación silenciosa del retrieval (s303: 500 transitorio del RPC de
enunciados → pool 34→23 sin rastro) queda CERRADA en la clase entera (PR #216): registro en
los 4 fail-opens (seam s289 extendido a enunciados/hyq-tabla/hyq-hidrata), reintento ÚNICO
ante 5xx del RPC de enunciados (ni 4xx ni timeout — el caso exacto de s303 queda SANO),
sección `retrieval` REQUERIDA en `rag_trace` con TRI-ESTADO, vista `salud_canal_retrieval_v1`
(% + conteos por canal, `source <> 'error'`, security_invoker, API a cero incluido PUBLIC).

**Motivo del tri-estado (el hallazgo del dúo, convergente en AMBOS lados por caminos
independientes)**: mi v1 colapsaba «adapter sin seam» a «sano» (lista vacía) — el propio
defecto #63 reintroducido una capa arriba. Fix: sin sección (no valida) / `measured=false`
(seam no conectado) / `measured=true`+lista (medido; vacía = sano), propagado por pipeline
(`None` ≠ `{}`), contrato del orquestador y vista; + test-ancla de que los adapters de
PRODUCCIÓN tienen el seam (un wrapper futuro sin `_trace` = test rojo, no salud perfecta
eterna). Dúo: 8 únicos, 8 confirmados, 0 FP (REVOKE PUBLIC, dependencias del header,
filas-error fuera del denominador, % prometido, ConnectError, 2 comentarios). Tally
COMPLETO en el log con recibo de ambos lados.

**Alternativas descartadas**: try/TypeError para pasar el seam (re-corre el retrieval
entero enmascarando bugs — se pasa por FIRMA); retry también en canales hyq (especulativo:
el 5xx observado fue del RPC de enunciados; trigger declarado = primer 5xx hyq en la vista);
retry en el RPC principal VECTOR (cambiaría el camino más caliente — fuera de alcance, s289
lo dejó deliberadamente sin tocar).

Recibos: `evals/adversarial_review_log.jsonl` (duo_status=complete) · suite 3591 passed.

## DEC-188 (s307) — Dos fallos orgánicos en una tarde, misma raíz: el bot hablaba de su corpus DE MEMORIA; y el dúo tumbó mi v1 con 4 críticos

**Decisión**: (a) los textos de presentación (intro/help/greeting/productos) se derivan de
`documents` activos — 30 fabricantes, cacheado por proceso, fallback estático, backoff;
EXCEPCIÓN: `_CONSENT_TERMS` (TERMS v7) intacto y pinneado por sha256 — su línea de marcas
viaja en el bump a v8 (reservado para base jurídica). (b) Las preguntas de INVENTARIO
(«¿qué productos de X tienes?») dejan de caer al RAG: ruta nueva en la rama
fabricante-sin-modelo que responde desde el inventario real — cruce por `document_id` (la
clave del serving), completo por construcción, acotado bajo el límite de Telegram,
intención estrecha (verbo de posesión AL FINAL discrimina inventario de specs), fail-open
a RAG, cobertura de las 30 marcas vía lista real de la DB. **DEC-059 NO tocado y con
métrica citada**: aquel fall-through se midió (s77) para preguntas DE MODELO; el
inventario es población que s77 no midió — la rama modelo+fabricante queda byte-idéntica
(test de fuente lo ancla).

**Origen**: 2º y 3º datos orgánicos (Alberto, 7-ago): pantallazo de la intro
(«Notifier, Morley y Detnov» con 30 marcas reales) y 👎 con motivo sobre «¿qué productos
de Securiton tienes?» — el RAG presentó su ventana de 10 chunks como inventario, sin
ASD531 ni ASD535 (242 chunks, el doc más grande de la marca). La ruta era `rag`
(route/measured=true: PRIMERAS filas de la telemetría s306 en producción).

**El dúo dio NO-GO a mi v1 — 13/13 confirmados, 0 FP** (tally completo en el log):
F1 «completo por construcción» verificado en n=1 confirmatorio (6 marcas VACÍAS por
cruce por nombre de fichero vs lotes s55) · Sol-only: page=5000 > cap PostgREST 1000 =
corte tras la 1ª página · H1 Notifier 4.377 chars > 4.096 = BadRequest sin handler ·
H2 «lista de averías/eventos» desviada al listado (8 casos de colisión → tests
negativos). Todo aplicado; sweep en vivo 30/30 marcas funcionales. Deudas: #65
(`documents.product_model` STALE post-H0 — probado con MADT235: AFP4000 allí, ART1194
en chunks), #66 (la prosa del 👎 llegó como consulta nueva — observación punto 5),
#67 (alias cortos: `lda` no casa `LDA audioTech`).

**Alternativas descartadas**: constante nueva con 30 nombres (caduca en el 31);
`documents.product_model` como fuente (stale, #65); ensanchar `_CATALOG_PATTERNS`
global (habría servido el catálogo entero ante preguntas por-marca); valor nuevo de
`route` (migración del CHECK para un menor — auditable por prefijo de respuesta).

Recibos: PR #218 · sweep 30/30 · `evals/adversarial_review_log.jsonl` (13/13, 0 FP).

## DEC-189 (s310) — L2a NO-GO por medición: la isla está atada al ecosistema de sellos; el audit de rutas pineadas se vuelve PRE-FLIGHT obligatorio

**Decisión**: el movimiento físico de la isla a `harness/` NO se hace. La cuarentena
LÓGICA del contrato L0 queda como estado FINAL de la isla (la garantía estructural ya
estaba entregada; L2a solo compraba legibilidad). L2b/L2c (no mueven ficheros) y L3
(`embed.py`: 0 referencias desde congelados, auditado) siguen adelante.

**Motivo (medido ejecutando, no estimado)**: el traslado se CONSTRUYÓ y sus anclas
pasaron (renames byte-puros para que los sha congelados sigan verificando +
MetaPathFinder en `harness/__init__` + traducción de rutas en tests-pin — 44/44), pero
la suite completa destapó la dimensión real: **29 de los 33 módulos** referenciados POR
RUTA desde recibos congelados o desde los **380 ficheros de código pineados por sha**;
10 de los 13 ficheros de test que fallaban son ELLOS MISMOS congelados (ineditables sin
romper su pin). Cada ecosistema (s114→s267) exigiría su propia cirugía. Coste sin final
razonable para comprar legibilidad que la cuarentena lógica ya suple.

**Alternativas descartadas**: (a) puente + traducciones para los 29 — desproporcionado y
de riesgo permanente sobre sellos; (b) shims en src/ — rompe anti-dos-copias Y los sha
igualmente; (c) mover solo los 4 libres — no compra nada y deja un paquete raquítico.

**Regla nueva (extiende Protocolo 4)**: antes de proponer mover CUALQUIER fichero →
correr `scripts/s310_audit_sellos_ruta.py`. Referencia-por-ruta desde sellos = el
fichero SE ANCLA y se declara (el patrón «2 anclados» del blueprint resultó ser la regla,
no la excepción). El censo de imports NO basta: los sellos pinan RUTAS.

**Lección (la del arco, otra vez y en grande)**: el blueprint enumeró anclas leyendo;
la medición ejecutando encontró 29/33. Verificar el efecto, no la intención — también
para planes propios ya aprobados.

Recibos: `evals/s310_l2a_medicion_sellos_v1.txt` · rama `claude/s310-l2a-harness`
(conservada como registro del diseño puente, por si un futuro re-sellado lo reabre).

## DEC-190 (s311-s313) — L2b y L2c ejecutados con sus dúos; el blueprint queda a un lote (L3) con TODOS los veredictos estampados

**Decisión/estado**: L2b SHIPPED (registro declarativo de 91 flags con censo v5.1 de fuente
única `tests/_censo_flags.py`, snapshot sin secretos, pin de DEMO_FLAGS por AST, invariante
en CI) y L2c SHIPPED (split del doble-inquilino a nivel símbolo: `pool_selection` motor +
`obligation_warning` reserva viva + residual vetado con shim declarado mínimo; E3c retirada
→ excepciones 5→4, cuarentena 3→2; sello +2 entradas exigidas fail-closed por el gate).
Byte-identidad de las 22 funciones verificada por **AST ×3** (autor, sub-agente, diff).

**Los dúos siguieron pagando** (tally completo por lote en el log): L2b 8/8-0FP con el
crítico convergente de las flags-en-bucle-dinámico Y la circularidad
test-escanea-como-el-generador que lo ocultaba; L2c 7/8-1FP donde el FP era el hallazgo
CENTRAL de Sol («el cuerpo de la reserva cambió») — refutado con recibo triple. Regla C en
ambas direcciones: corta mis over-claims y también los de los revisores.

**Piezas de sistema que nacieron del arco**: los dos lotes L2 ENGRANARON el mismo día (el
split movió lectores y el registro lo puso en rojo hasta regenerar — el invariante nuevo
cazando su primer caso real); `merge=union` para el log append-only (los conflictos de
tally que bloquearon el PR #220 no se repiten — el «no checks reported» de GitHub era
conflicto, no cuota, y quedó documentado); el assessment smoke como peaje de todo cambio
de `pipe_sha` (pagado en L1 y L2c, mismas cifras limpias: 0 synth, 0 corpus-gap).

**Ejecución declarada** (L2c): split mecánico delegado a agente con spec cerrada — entregó
completo y se colgó en su suite final; TODO su trabajo verificado pieza a pieza antes de
aceptarlo (el contrato que dejó era exactamente el diseño correcto).

Recibos: PRs #223/#224 · filas del scoreboard 2026-08-08/2026-08-08b ·
`evals/adversarial_review_log.jsonl` (s311, s312, s313 complete).

## DEC-191 (s314) — L3 NO-GO por medición: embed.py está pineado por recibos prereg s117; el blueprint queda CERRADO con 4/6 lotes ejecutados y 2 NO-GO medidos

**Decisión.** L3 (mv `src/reingest/embed.py` → `src/ingestion/`, retiro de E2) NO se ejecuta.
El pre-flight DEC-189 apuntado a embed.py (agente delegado; verificado con regla C por el autor)
encontró 4 pins vivos `{path: src/reingest/embed.py, sha256: 61fc2412…}` en recibos prereg s117
(m26 v1 + m2 v1/v2/v21), sha coincidente con el fichero actual. Único consumidor ejecutable: el
replay de `scripts/s117_m26_independent_reuse_audit.py`, cuyo `preflight()` hash-verifica los
`frozen_inputs` → moriría fail-closed tras el mv. Regla escrita de DEC-189: fichero con
referencias-por-ruta desde sellos NO se mueve — se ancla y se declara. E2 permanece en el
contrato de imports con su trigger declarado.

**Motivo.** Proporcionalidad: el beneficio de L3 es retirar UNA excepción documentada de la
matriz; el coste es romper la replayabilidad de un audit congelado (registro s117, DEC-147
lo protege como intocable). El precedente L1 no cubría este caso (catalog_store: 0 pins en
recibos, medido). La premisa del blueprint («0 refs desde congelados») era incompleta: el
criterio s310 mide refs desde ficheros .py pineados, no recibos que pinan la ruta directamente
— el instrumento nuevo `scripts/s314_audit_embed_pins.py` mide AMBAS dimensiones.

**Alternativas descartadas.** (a) Proceder declarando el coste (matar el replay m26 v1):
contradice la premisa sancionada del blueprint → exigiría re-sanción de Alberto para un lote
cosmético; desproporcionado. (b) Editar los recibos prereg a la ruta nueva: viola DEC-147
(registro intocable). (c) Shim `src/reingest/embed.py` re-exportando desde ingestion: el pin
es por sha del CONTENIDO — cualquier edición lo rompe igual.

**Estado del blueprint (cierre).** L0 ✓ · L1 ✓ · L2a NO-GO medido (DEC-189) · L2b ✓ · L2c ✓ ·
L3 NO-GO medido (este DEC). Excepciones del contrato: 6→4 vigentes (E1 retirada en L1, E3c en
L2c; quedan E2, E3a-b, E6, más E4/E5 como ciclos deliberados aparte), todas con trigger
declarado. Recibo: `evals/s314_l3_medicion_pins_v1.txt`.

## DEC-192 (s314) — `ingest_new.py` estrenado con el lote Casmar/Kidde (74 docs, 1.091 chunks) y el hallazgo que re-clasifica el gap orgánico: era FINDABILITY, no corpus

**Contexto.** Pregunta orgánica de Alberto: el bot admitió (honesto) no tener el manual de
instalación del Kidde NC-PF2; Alberto lo localizó en casmarglobal.com y encargó: añadirlo,
revisar TODA la documentación Kidde de Casmar contra el corpus (sin certificados ni
homologaciones) y estrenar con ello la automatización de altas (frente 7).

**Lo construido.** (a) Método Casmar reproducible (`scripts/s314_casmar_*.py`): catálogo por
búsqueda paginada (88 SKUs; +corpus = 94) → docs por SKU (`form_id` OBLIGATORIO: sin él el
filtro se ignora EN SILENCIO y devuelve el listado global — guarda anti-fallback) → 266 PDFs
únicos → clasificación por prefijo (H_DOP_/H_CPR_/H_CE_/CE_/C_/DOP_ = excluidos) → cruce por
(SKU, tipo) contra TODO el corpus. (b) `scripts/ingest_new.py` (driver A2+B por canal):
gates fail-closed (sidecar obligatorio, dedup sha vs chunks_v2 —el estado FINAL, no los
intermedios—, exclusión de certificados, PDF legible), dry-run por defecto con coste
estimado, alta de fila `documents` ANTES de indexar (cierra el hueco histórico: el pipeline
no crea filas y `resolve_document_id` solo enlaza; las altas s55/s58 fueron backfills
post-hoc), reanudable por fase, try/except por doc, recibo JSON, exit≠0 si la verificación
en DB falla. La reanudabilidad se estrenó a la primera (un `import re` ausente cayó DESPUÉS
de pagar 4 extracciones; el re-run las retomó del store sin re-pagar).

**El hallazgo (honestidad primero).** El manual de instalación de la familia NC-PFx YA
ESTABA en corpus (`bcn-3100017` «NC series», 126 chunks, «convencional» ×142, menciona
NC-PF2/4/8) con pm=`NC` — invisible: `model_to_imatch_pattern` construye el patrón desde el
modelo de la QUERY y lo busca DENTRO del pm ALMACENADO, así que un pm de familia genérico
jamás matchea la variante. Clase hp011#2/DEC-176 (identidad/alcanzabilidad), 4ª instancia.
Sonda `scripts/s314_alcanzabilidad_ncpf.py`: 0/5 al pool ANTES del fix → 5/5 a EVIDENCIA
después. **Fix de identidad (clase s78/s80, UPDATE reversible con recibo): pm =
lista-con-barras (convención viva `AM2020/AFP1010`)** aplicado a los 4 docs nuevos, los 4
bcn viejos, 5 hojas de familia (solo donde la hoja es SUJETO de la familia; las menciones de
compatibilidad NO — contaminación) y los 2 manuales 2X-A byte-idénticos a los docs de
usuario que Casmar lista bajo los KIT 2X-AT. El generador de sidecar emite equipo =
lista-con-barras desde ahora.

**Cierre medido (criterio de Sol: la métrica debe cubrir el objetivo).** Re-cruce final:
**104 gaps → 1 residual declarado** (KE-ASA-AUXR sin doc de instalación propio EN NINGÚN
sitio: la hoja XIP no lo menciona — cross-link comercial de Casmar; su datasheet ingestada);
133/134 incluibles cubiertos. Lote: 74 docs ingestados (4+70), 1.091 chunks, ~$60 LlamaParse;
1 near-dup retirado con recibo (hoja XIP ES = 99,6% contenida en la ML existente); 29 dups
del PIM colapsados por sha. Corpus: chunks_v2 26.215 · documents 1.243 (Kidde 103) ·
Manuales_Kidde 129 PDFs · Excel reconciliado (`--data-root` nuevo: desde C:\dev el ROOT del
checkout no ve OneDrive — clase manifiesto-vacío).

**Dúo (Protocolo 3, zona de dolor corpus).** Sol 8 + sub-agente 7 = 11 hallazgos únicos
(4 convergentes), 11 confirmados con regla C, 0 FP; ambos SÓLIDA-CON-CAMBIOS y TODOS los
cambios cablEADOS antes de gastar. Los 3 que cambiaron el orden de operaciones: reanudabilidad
(crítico), lote-solo-en-scratchpad (el sesgo del autor en la parte operativa), doc_type NULL
para nomenclatura del portal (mapeo en el driver + PATCH a chunks; `metadata.py` NO se toca —
sha-pineada por recibos s116/s117, pre-flight tipo-L3 ejecutado ANTES de decidir).

**Alternativas descartadas.** Canal nuevo `Kidde_Casmar` (canal=fabricante en el seam →
contaminaría manufacturer); alta de documents post-index (patrón backfill: repite el hueco);
ingestar el near-dup y los byte-idénticos (identidad > gasto); scraper Casmar permanente
(prematuro, declarado en frente 7); tocar `metadata.py` para que B5 lea el `tipo` del
sidecar (pins vivos).

**Deuda declarada.** El MI Casmar 202502 y el bcn r002 conviven ACTIVOS para la misma
familia (TECH_DEBT #4, cadena supersede sin construir — riesgo: evidencia con near-dups
compitiendo); doc_type de los CHUNKS pre-s314 sigue NULL para nomenclatura no-regex.
Recibos: `evals/s314_casmar_kidde_cruce_v1.{md,json}` · `s314_casmar_batch_report_v1.json` ·
`s314_identity_{ncpf_patch,familias_kidde,2xat_kit,reconciliacion}_v1.json` ·
`s314_alcanzabilidad_ncpf_v1.json` · `s314_etapa2_rediagnostico_v1.json` ·
`s314_casmar_kidde_cruce_cierre_v1.json` · tally en `adversarial_review_log.jsonl`.

## DEC-193 (s315) — Latencia instrumentada + links en la leyenda + barrido pm-de-familia aplicado a 49 docs; y el gap de canales derivados (#68)

**Contexto.** Alberto retomó la cola s314 y añadió 6 puntos nuevos, adjudicando lanzar: rapidez
(perfilado), links a manuales, y el barrido pm-de-familia; panel = dashboard Supabase (se
mantiene DEC-183, guía en `docs/DASHBOARD_SUPABASE_GUIA.md`); Tyco/etc «más adelante»;
Aritech/Edwards «vía Casmar si los lleva». Automode explícito a media sesión.

**Decisiones.**
(a) **Latencia: primero atribuir, después optimizar.** p50=34,5s/p95=57,6s sin desglose ⇒ se
construye la instrumentación (`stage_timings` + sección `timings` tri-estado + vista) y NO se
toca ningún lever de velocidad sin ~1 semana de datos. Candidatos quedan anotados (cap-rerank,
retrieve=30, typing keep-alive), ninguno medido aún.
(b) **Links: reusar el fetch batched del retriever** (hallazgo #1 del dúo) en vez de una
llamada PostgREST nueva por turno — cero latencia añadida, y el flag `SOURCE_LEGEND_LINKS`
(estricto) separa la decisión del SOURCE_LEGEND ya existente. `SOURCE_LEGEND_LINKS=on` es
no-op si `SOURCE_LEGEND` está off.
(c) **Barrido pm-de-familia = aplicación a escala de la clase DEC-192** (no un lever nuevo):
censo por atestación en contenido propio + adjudicación 2 capas (agente con extractos +
refutación independiente ×3) + invariantes deterministas del patrón imatch → patch reversible
con recibo aplicado y verificado 49/49 (104 variantes). Regla conservada: SUJETO sí,
compatibilidad no. Caveat declarado en el recibo: los TG-* hacen que queries de centrales
(ID3000…) matcheen también el doc de la pasarela TG — es propiedad del matcher (\y interno),
adjudicado aceptable (pool-level, rerank decide; el doc ES de la familia funcional).
(d) **#68 (pregunta de Alberto): los lotes nuevos no pasan por enunciados/hyq** — verificado
(1.091 chunks s314 = 0/0). Se estampa como deuda con trigger «antes del siguiente lote», no se
cablea en caliente: los generadores tienen gates propios (QA Haiku DEC-102, cuota/parity
DEC-099) y merecen su pasada con dúo.

**Gaps declarados.** Sol no ejecutable en el entorno remoto (sin OPENAI key) — el dúo de esta
sesión = sub-agente Opus (build, 12 hallazgos aplicados) + refutadores independientes (censo);
la ronda Sol queda pendiente si Alberto la quiere sobre el diff. Sonda e2e de alcanzabilidad
(Voyage) no ejecutable — sustituida por la verificación determinista del patrón + sonda
imatch server-side 6/6 (el mecanismo exacto que estaba roto). Push a GitHub bloqueado por
permisos de la App (403 en creación de refs) — commits locales pendientes de publicar.

**Alternativas descartadas.** Panel web propio (re-litigar DEC-183 sin necesidad — auth+RGPD);
optimizar latencia a ciegas (violaría eval-driven); aplicar el patch sin refutación
independiente (zona de dolor corpus/identidad); llamada PostgREST nueva en la leyenda (dúo #1);
cablear enunciados/hyq del lote en caliente (gates propios pendientes).

**Recibos.** `evals/s315_family_pm_patch_v1.json` · `evals/s315_source_url_backfill_v1.json` ·
migración `supabase/migration_proposals/20260809180000_s315_source_url_y_latencia_etapas.sql`
(APLICADA vía MCP, postcondiciones OK) · suite 3644 passed (4 preexistentes de entorno,
idénticos en árbol limpio).

## DEC-194 (s315b) — Fase de canales derivados por lote (#68): construida, dúo NO-SÓLIDO → 13 fixes; contrato de convivencia de vintages hyq

**Decisión.** La fase incremental enunciados+hyq para lotes de ingesta REUSA los generadores
canónicos en vez de reescribirlos: enunciados por el camino acotado s273 (nunca estrenado:
`enunciados_pass --docs` + `s104_a3_load --only-source-files/--rewrite-batch-tag/--ledger-check`)
con `--store` nuevo para el extraction store bajo `--data-root`; hyq con pipeline por-lote
(`hyq_lote_pipeline.py`) porque el camino global asume vintage único. **Contrato nuevo de
vintages hyq**: `hyq-v1-*` = vintage GLOBAL único (el loader s102 sigue abortando ante mezcla
y su `--wipe` solo borra esa clase); `hyq-lote-*` = vintages POR LOTE aditivos (el loader
global los ignora; cada lote deja recibo con su `ingest_batch` = asa de rollback selectivo).
Pins anti-drift: hyq genera con sonnet-4-6 (vintage del corpus s102, NO hereda el Opus 5 vivo);
enunciados con haiku h1 (GO DEC-102); few-shot pineado por sha12 contra el gold vivo.
Orquestador `derive_channels_lote.py`: dry-run con coste, E1→E2→H→V, verificación por manifest
de ids + recibo con ambos batch tags.

**El dúo cortó de verdad (Protocolo 3, sub-agente Opus, Sol sin key — gap declarado):**
NO-SÓLIDO con 13 hallazgos, 4 de ellos rompe-ejecución, TODOS aplicados: (#1 CRÍTICO) el
append inutilizaba el loader global y su --wipe habría borrado el lote → contrato de prefijos;
(#2) E2 abortaba el lote entero si UN doc no producía filas (esperable: sin store/todo-dup) →
--only-source-files se deriva del DUMP; (#3) resume de s104_a3_load roto (paginaba 10k contra
max-rows=1000 — el mismo bug que s102 ya arregló en su gemelo); (#4) la verificación hyq
fallaba en cualquier resume parcial (delta vs universo); (#5) truncación silenciosa a 1.000
chunks/doc; (#6) generaba hyq de chunks duplicate_of (la clase DEC-165); (#7) el tope de
presupuesto devolvía éxito → rc=2 + budget dimensionado al lote desde el ledger; (#8)
predicado de temperatura reintroducía el falso-positivo que s104-F3 corrigió; (#9-#13)
verificación real por ids, no re-embeber npz vigente, líneas corruptas contadas, pin few-shot,
aborto en lote vacío.

**Bugs vivos de producción (datos de Alberto, mismo día):** apéndice must_preserve con
`<br/>` literales de celdas LlamaParse → fix de presentación `_strip_html_breaks` (clase
blockquote-v6, tests); el «Reply to…» del feedback revivía tras el «Anotado» →
`ReplyKeyboardRemove` NO desarma un ForceReply: capturada la explicación se BORRA la
invitación (guarda estricta por texto exacto — una respuesta técnica jamás se borra;
3 tests); carry-forward sobrevive al cambio de marca vía catalog_shortcut →
**#70** (diagnóstico verificado en query_logs, fix con diseño+dúo propio); disclaimer legal
capturado como obligación de evidencia → **#71** (aparato protegido DEC-148, exige
adjudicación). **Primera atribución de latencia en producción** (timings s315 vivos):
62,9s = retrieve 27,0 + generate 33,1 + rerank 1,5 + coverage 1,2 — retrieval pesa 40-45%,
mucho más de lo asumido; plan de ataque cuando haya ~1 semana de datos.

**Run del lote Casmar PENDIENTE** (máquina con claves + store): dry-run → --aplicar (~$5-15).
Recibos: `evals/derive_lote_*` cuando corra. Alternativas descartadas: reescribir generadores
(drift de paridad); cargar el lote en el vintage global con --wipe+re-embed (70k filas de
churn por lote); gate de desplazamiento obligatorio por lote (el instrumento enunciados_panel
queda disponible; a escala 1k chunks el precedente NO-GO de DEC-102 queda 2 órdenes lejos).

## DEC-195 (s316) — Reparación de gobernanza: s315c retro-registrado y el hook del digest deja de depender del checkout

- **Fecha**: 10 ago 2026 (s316, apertura). **Impacto**: MEDIO (gobernanza: toca el aparato
  anti-recall y la política de versionado de `.claude/`; zona de dolor = proceso/anti-bias).
- **Disparador**: Alberto pidió retomar contra una sesión anterior corrida EN CLOUD, advirtiendo
  del riesgo de inconsistencias. La reconciliación (local iba 5 commits por detrás; FF limpio a
  `f947fac`) destapó dos agujeros REALES, ninguno de ellos de código.
- **Diagnóstico (verificado en esta sesión, no de memoria)**:
  1. **s315c (`0fba21f`) no existe en la memoria canónica**: ni PLAN, ni HISTORY, ni DECISIONS, ni
     TECH_DEBT lo mencionan; `docs/ENTORNO_CLOUD.md` quedó huérfano y sin DEC. El «Cierre de
     sesión» de CLAUDE.md se quedó a medias justo en el último commit de la sesión cloud.
  2. **El control anti-recall de DEC-072 estaba CAÍDO**: `.claude/hooks/inject_lever_digest.sh`
     no existía en la máquina local y ni el settings de proyecto ni el de usuario lo registraban
     ⇒ el digest de levers NO se inyectó en el arranque de esta sesión. No lo causó el merge (git
     no borra ignorados; s315c solo AÑADIÓ `session-start.sh`): ya estaba caído. **Es exactamente
     el gap que DEC-072 declaró de entrada** — «el hook vive en `.claude/` gitignored = setup
     local por checkout» — materializado, y además invisible en cloud: las sesiones s315/s315b/s315c
     nunca tuvieron digest.
- **Decisión**: (1) **versionar el hook del digest** (`.claude/hooks/inject_lever_digest.sh` +
  entrada `SessionStart` con matcher `startup|resume` en `.claude/settings.json` + whitelist en
  `.gitignore`), aprovechando que s315c ya abrió `.claude/` a versionado selectivo ⇒ el control
  viaja con el repo y aplica IGUAL en local y en cloud; fail-open si falta el digest (rc=0).
  (2) **Retro-registrar s315c** en PLAN/HISTORY/DECISIONS con su ámbito real. (3) Refrescar el
  «START HERE» de CLAUDE.md, que seguía apuntando a S278 (22-jul, 25 sesiones stale).
- **Alternativas descartadas**: (a) **re-crear el hook gitignored** como estaba (fiel a DEC-072):
  reproduce el fallo por tercera vez y deja el cloud sin control — el gap ya está MEDIDO, no es
  hipotético; (b) **inline del digest en CLAUDE.md**: NO-BP y ya descartado por DEC-072 (CLAUDE.md
  = instrucciones durables, no estado mutable); (c) **generar el digest desde tags greppables**:
  mejora real pero es otro workstream — no bloquear la reparación con una refactorización;
  (d) **dejarlo como deuda**: el control caído es precisamente el que evita re-litigar levers, y
  esta sesión iba a proponer sobre levers.
- **Gaps / riesgos declarados**: el digest son ~33KB inyectados en CADA sesión (coste de contexto
  aceptado por DEC-072, no re-litigado aquí, pero ahora también se paga en cloud); sigue siendo
  hand-maintained (el paso de cierre del Protocolo 4 es el único anti-drift); versionar `.claude/`
  amplía la superficie de config compartida — si alguien tenía un `settings.json` local privado,
  el merge de s315c pudo pisarlo sin aviso (git sobrescribe ignorados en silencio) y no es
  recuperable; el hook no valida que el digest esté al día, solo que exista.
- **Estado**: ✅ hook escrito, `chmod +x`, JSON validado y **ejecutado en el mismo turno**
  (rc=0, 32.965 bytes emitidos) + trackeado por git. Retro-registro de s315c aplicado.
  **Relacionado**: DEC-072 (el control original y su gap declarado), DEC-193/194 (s315/s315b),
  `docs/ENTORNO_CLOUD.md`, `docs/LEVER_DIGEST.md`.

## DEC-195b (s315c, retro-registrado en s316) — Entorno cloud: hook de arranque web versionado + guía de habilitación

- **Fecha**: 9 ago 2026 (s315c; registrado retroactivamente el 10-ago al detectarse ausente).
  **Impacto**: MEDIO (toca el arranque de toda sesión cloud + política de `.gitignore`).
- **Disparador**: la primera sesión cloud (s315) perdió tiempo montando el contenedor a mano y
  chocó con tres límites del entorno; Alberto quiere lanzar trabajo «on the go» desde el móvil.
- **Decisión**: `.claude/hooks/session-start.sh` versionado y **guardado por `CLAUDE_CODE_REMOTE`**
  (en local sale con rc=0 sin efectos): des-shallowea el clon (sin historial completo fallan ~180
  tests de contratos congelados que leen blobs viejos con `git cat-file`), instala dependencias
  con los tres workarounds cazados a mano en s315 (langdetect sin wheel; PyJWT/cryptography de deb
  sin RECORD → `--ignore-installed`; `requirements-dev` arrastrando el base) y fija `PYTHONPATH=.`.
  `.gitignore` pasa de ignorar `.claude/` entero a whitelist selectiva. `docs/ENTORNO_CLOUD.md` =
  checklist de Alberto (secretos, política de red, límites).
- **Alternativas descartadas**: arreglar el contenedor a mano cada sesión (el coste se repite y no
  es auditable); imagen/devcontainer propio (sobre-ingeniería para tres pips y un unshallow);
  versionar `.claude/` entero (arrastraría config y memoria locales).
- **Gaps / riesgos declarados**: **OneDrive nunca estará en cloud** ⇒ la fase de enunciados y las
  re-ingestas siguen exigiendo máquina local (subir el extraction store a un bucket queda anotado,
  NO decidido); `TELEGRAM_BOT_TOKEN` deliberadamente FUERA (un script suelto en cloud haciendo
  polling competiría con producción); la política de red por defecto bloqueó casmarglobal.com
  (recon s315) y sin `OPENAI_API_KEY` el dúo queda cojo — ambos requieren acción de Alberto en el
  environment del repo, y hasta que la haga las sesiones cloud arrastran esos dos gaps.
- **Estado**: ✅ validado end-to-end en el contenedor web en s315c (hook rc=0; suite, `check_deps`,
  `catalog_store validate` y `gold_store validate` en verde). Checklist de Alberto **PENDIENTE**.
  **Relacionado**: DEC-193, `docs/ENTORNO_CLOUD.md`, DEC-195.

## DEC-196 (s316) — El dedup por documento del canal hyq: intentado, TUMBADO por el dúo, REVERTIDO; y los fixes que sí quedan

- **Fecha**: 10 ago 2026 (s316). **Impacto**: ALTO (zona de dolor: ingesta + un canal VIVO
  en producción; el run que dependía de esto escribe en dos índices con HNSW propio).
- **Disparador**: el run del lote Casmar (#68, DEC-194) quedó pendiente «en máquina con
  claves» y su dúo se declaró CON GAP (Sol no ejecutable en cloud, sin `OPENAI_API_KEY`).
  En local la clave existe ⇒ el Protocolo 3 exige cerrar el gap antes de escribir.
- **Lo que el dúo cazó (2 rondas, 20 hallazgos)**: ronda 1 (Sol) = 3 CRÍTICOS de la clase
  **éxito silencioso** — V imprimía ❌ y devolvía 0; el lote se materializaba con UN
  `source_file` por `limit:1` sin `order` (la fuga que s288 F2 prohíbe en runtime); los
  chunks saltados por error de API y el `poison` se convertían en «cobertura completa».
  Ronda 2 (Sol + sub-agente Opus, sobre MIS fixes) = **NO-SÓLIDO**.
- **Decisión 1 — REVERTIR el dedup (adjudicada por Alberto)**. Se había cambiado el
  descarte cross-vintage por keep-FIRST `(document_id, texto)`. Es **inválido por tres
  razones verificadas**: (a) `parse_questions` (`s101_hyq_embed.py:44`, `seen_global`) ya
  deduplica global por texto dentro del jsonl ⇒ `dup_intra_doc ≡ 0` y `UMBRAL_DEDUP` es
  código muerto (el sub-agente lo probó EJECUTANDO la función); (b)
  `tests/test_s315_derive_lote.py:41-53` **fija como contrato** que dentro del lote se
  deduplica cross-documento — mi afirmación de lo contrario era falsa; (c) el atenuante
  que declaré (family-parity del RPC) era **over-claim**: el RPC global trunca a
  `LIMIT 200` ANTES de filtrar por familia (TECH_DEBT #52), así que meter texto duplicado
  ataca justo ese techo. **Conclusión de rumbo: el dedup NO es un fix, es un LEVER de
  ingesta con coste** — se decide MIDIENDO `dup_cross_vintage` en un lote real (Protocolo
  4: delta en eval, no proxies), no razonando. Queda como lever ABIERTO, no medido.
- **Decisión 2 — CONSOLIDAR los fixes que sí lo son** (todos con test): V fail-closed con
  `veredicto`+`fallos`+`avisos` en el recibo y rc=1; `_verificar_biyeccion` (aborta si un
  `source_file` trae chunks de documentos ajenos); paginación real de `_source_files_de_doc`;
  `errores_totales` detiene el pipeline; `ok_count` no resta `poison` y exige `universo>0`;
  `raise_for_status` en la paginación de `_existing_pairs_tagged`; congelado de selección
  por firma sha256-16 con `--hasta` y `--refrescar-seleccion`, que **no se re-congela solo**;
  `alcance.canales_ejecutados` en el recibo (con `--solo`, declarar «COMPLETO en ambos
  canales» era la misma clase de éxito silencioso que V venía a cerrar); `product_model`
  real en vez del centinela de prompt; y la convención de encoding del repo
  (`stdout.reconfigure`) en los 4 scripts del camino que la omitían — sin ella, en Windows
  con salida capturada un `print` con `→ ≈ ─ ✅ ❌ ⚠` **aborta el run a media carga**
  (la suite lo cazó: `test_clis_exponen_contrato` estaba en rojo).
- **Decisión 3 — bug independiente, arreglado**: `s315_upload_manuales_storage.py` pedía
  `limit=10000` con guarda `len(docs) >= 10000`, pero **PostgREST capa a 1.000 filas por
  servidor**: con 1.243 documentos veía 1.000, la guarda no disparaba y **243 quedaban
  invisibles** → sus PDFs se clasificaban «sin fila» y el `--aplicar` los habría SALTADO
  sin poblar `source_url`. Con paginación real: a enlazar 807→**1.008**, «ya con URL»
  69→**76** (casa exacto con la DB), «sin fila» 269→**61**.
- **Alternativas descartadas**: (a) implementar el dedup por documento de verdad tocando
  `parse_questions` — está PINEADA e importada por el loader global s102 para paridad
  byte-a-byte; romper ese contrato por un lever no medido es exactamente lo que el dúo
  vino a impedir; (b) dejar los fixes sin tests («139/139» describía tests preexistentes,
  crítica justa del sub-agente); (c) correr el `--aplicar` con los fixes de la ronda 1:
  quedaban dos rutas (`--solo` en sus dos valores) que escribían declarando COMPLETO.
- **Gaps / riesgos declarados**: el lever del dedup queda ABIERTO y sin medir — el número
  que lo decide (`dup_cross_vintage`, ahora VISIBLE en consola y recibo) exige generar el
  lote (~$4,4) sin cargar; **no hay canario automático pre/post** (Sol MEDIO, aceptado y no
  cerrado en código: es paso manual con `factlevel_assessment.py smoke`); `_verificar_biyeccion`
  solo corre en la rama `--since` y su mensaje de error recomienda `--docs-file`, que
  **desactiva la comprobación** (salida documentada del guard — anotado); el resume queda
  frágil si el jsonl crece tras una carga parcial (el `batch_tag` cambia con el npz y las
  filas viejas quedan huérfanas bajo el tag anterior); y **el run del lote sigue SIN
  EJECUTAR** — nada escrito en producción.
- **Estado**: ✅ revertido + consolidado + **suite 3.666 passed / 46 skipped / 0 failed**
  (antes 1 failed) + 8 tests nuevos (`tests/test_s316_derive_lote_fixes.py`) + dry-run
  verificado (74 docs · 1.091 chunks · firma `77e3ae58900afdc7` · rc=0). Dúo COMPLETO por
  primera vez en este frente: Sol xhigh ×2 rondas + sub-agente Opus 5 (pin s292).
  **Relacionado**: DEC-194 (el build), DEC-102 (crowding del canal enunciados),
  TECH_DEBT #52 (techo top-200) y #68.

## DEC-197 (s316b) — #70 re-diagnosticado (la fix direction original era inválida) y el INSTRUMENTO de transporte construido; el fix queda gateado por el instrumento

- **Fecha**: 10 ago 2026 (s316b). **Impacto**: MEDIO-ALTO (zona de dolor: conversacional/
  multi-turn; el fallo es ORGÁNICO de Alberto usando el bot; toca el diagnóstico de una
  deuda viva y añade infraestructura de test que gateará el fix).
- **Disparador**: Alberto priorizó #70. Dos diseños de fix consecutivos fueron NO-SÓLIDO
  (dúo ×3 rondas: Sol xhigh + sub-agente Opus 5) — ambos habrían pasado sus tests sin
  arreglar nada. Alberto adjudicó entonces «atacar el instrumento, no el fix, BP/robusto/
  escalable».
- **El hallazgo que reordena todo (Sol, ronda 1; verificado contra la API de Railway)**:
  **F1 está ACTIVO en producción** (`CONVERSATION_POLICY=impl` + `ORCHESTRATOR_PATH=on`).
  Mi inferencia de lo contrario («ninguna traza tiene clave `policy`») era inválida —
  `runtime_trace.py` no emite política conversacional. Consecuencias: (a) la clave
  `last_detected_models` está MUERTA en producción; (b) la «fix direction» escrita en
  TECH_DEBT #70 (limpiarla) era inválida y quedó CORREGIDA; (c) el estado real es
  `mt_working_state`.
- **Mecanismo real de #70 (2 causas independientes, ancladas)**: ceguera de ruta (el
  turno del cambio de marca retorna en `handle_message` sin que F1 lo vea; 7/13 returns
  responden sin tocar estado) + conflación de la política
  (`brand_compatibility_in_window`: marca sola in-window ⇒ carry, correcto para
  compatibilidad, incorrecto para cambio de tema). Un fix completo toca ambas; el
  fall-through («¿y en Morley cómo se hace el reset?») reproduce el fallo sin pasar por
  ninguna ruta temprana — VERIFICADO ejecutando la heurística, no supuesto.
- **Decisión 1 — INSTRUMENTO construido** (`tests/test_s316_transport_state_instrument.py`,
  prescripción convergente de ambos revisores; revisarles su propia prescripción habría
  sido ritual): conduce `handle_message` REAL con dobles $0 (patrón
  `test_f1_activation_wiring`, flags congelados antes del import) — **testigo del fallo
  orgánico en `xfail(strict=True)`** (ROJO hoy = #70 demostrable por primera vez; el
  XPASS estricto obliga a retirar el marcador cuando el fix aterrice) + **control causal**
  (estado limpiado a mano ⇒ VERDE: el rojo es el bug, no el doble) + **control de
  no-regresión** (compatibilidad con marca SERVIDA — Hochiki era vacuo:
  `manufacturer_no_model` la corta antes de la política) + **censo AST de ramas
  terminales** (13/3; el unit del riesgo es la rama, no la ruta de log_query). Resultado
  primer run: 3 passed, 1 xfailed — el criterio de aceptación («rojo sobre el código de
  hoy») cumplido.
- **Decisión 2 — el FIX queda pendiente y GATEADO por el instrumento**, con las
  restricciones pagadas en las 3 rondas (estampadas en TECH_DEBT #70): rollback-safe ante
  `CONVERSATION_POLICY=stub`; `manufacturer_mismatch` FIJA, no limpia; invalidar modelos
  sin tocar `last_query` produce un «Ha pasado un rato» mentiroso; punto único =
  `TypeHandler` grupo −1; `extract_product_models` emite códigos no-producto; reusar
  `_same_manufacturer`.
- **Alternativas descartadas**: hot-patch en las salidas del catálogo (no-op: clave
  muerta); activar F1 como fix (ya está activo, y la política arrastraría igual);
  YAML+censo-AST por rutas (mi v1 del instrumento: censo falso en 3 formas, ciego a 7/13
  ramas — sobre-ingeniería sobre taxonomía equivocada; la canónica vive en el CHECK
  `query_logs_route_check`); tocar `conversation_policy_impl` dentro del bugfix (contrato
  con tests congelados y gate MT propio).
- **Gaps / riesgos declarados**: el testigo reproduce el PRECONDICIONANTE de estado, no el
  daño completo (generación stubeada); sin control de reloj (casos de ventana/expiración
  fuera); `user_data` por-USUARIO (semántica PTB real, heredada); los stubs de deciders
  DB son precondiciones calibradas a producción — si el corpus deja de servir Morley, el
  control de compatibilidad miente; #70 SIGUE ABIERTO (el instrumento lo hace demostrable,
  no lo arregla).
- **Regla C / tally**: 3 rondas completadas en `adversarial_review_log.jsonl`
  (16:57 caída API; 17:06 / 17:29 / 17:38 con findings confirmados y 0 FP). Refutación
  bidireccional registrada: el menor de Opus sobre `route` NULL refutado con lectura
  directa de `query_logs`.
- **Estado**: ✅ instrumento en verde/xfail según diseño; TECH_DEBT #70 re-escrito;
  suite completa en curso al cierre de esta entrada. **Relacionado**: DEC-148/154 (gate
  MT), DEC-072/195 (controles), TECH_DEBT #70, `evals/s316_tech70_propuesta_v{1,2}.md`,
  `evals/s316_instrumento_mt_transporte_propuesta_v{1,2}.md`.

## DEC-198 (s316b) — #70 etapa 1 SHIPPEADA contra el instrumento, y la medición que cierra el lever del dedup en 0,00%

- **Fecha**: 10 ago 2026 (s316b). **Impacto**: ALTO (código de producción en el despacho de
  mensajes del bot vivo + estado conversacional; zona de dolor).
- **Contexto**: Alberto priorizó #70 (fallo ORGÁNICO de uso real) y adjudicó «instrumento
  primero, BP/robusto/escalable». El instrumento (DEC-197) hizo su trabajo: el testigo salió
  ROJO, el fix lo puso VERDE, y el segundo testigo mantiene honesta la mitad que falta.
- **Decisión 1 — guardia de cambio de marca en `TypeHandler` grupo -1**. Punto ÚNICO por el
  que pasan todos los updates: cubre las rutas tempranas Y el fall-through sin depender de
  que cada ruta se acuerde de llamar a nada (el dúo cortó dos veces la variante «seam por
  ruta» como convención olvidable). Cuatro condiciones simultáneas; fail-open y fail-soft.
- **Decisión 2 — calibración PRECISIÓN-PRIMERO, y es el corazón de la decisión.** La v1
  cableada era **PEOR que el bug**, medido end-to-end por el sub-agente y verificado:
  `FUEGO` es un fabricante REAL de la DB (1 doc) y el resolutor casaba «fuego» ⇒ 8/19
  consultas técnicas plausibles borraban contexto y convertían turnos contestados en
  clarifies. Asimetría que manda: un FALSO POSITIVO rompe un turno que funcionaba; un MISS
  solo deja el bug en fraseos raros ⇒ se sacrifica recall. Correcciones: resolutor estricto
  (la heurística «primera palabra única» de `_marca_en_consulta` es segura solo tras un
  pre-gate), `_MARCAS_AMBIGUAS`, `vamos` fuera de los verbos de switch, replies excluidos.
- **Decisión 3 — lo estructural NO es la lista negra, es el detector de colisiones**:
  `test_ninguna_marca_nueva_colisiona_con_el_dominio` rompe CI si se ingesta una marca
  llamada «Alarma»/«Sirena»/«Central». Una lista negra se pudre; un detector no.
- **MEDICIÓN QUE CIERRA EL LEVER DEL DEDUP (DEC-196)**: generado el lote completo
  (939 chunks → 2.516 preguntas, ~$4) y cruzado contra los 70.126 textos del vintage
  global: **`dup_cross_vintage` = 0 / 2.516 = 0,00%**. La regla que s316 quiso cambiar no
  descarta NADA en este lote ⇒ el lever era un **no-op medido**. Revertir fue correcto y el
  rediseño habría sido complejidad pagada por nada. **Lever CERRADO con dato, no con
  razonamiento.**
- **Medición de precisión sobre datos REALES**: 68 consultas distintas de `query_logs`
  (abr–ago) → 7 disparos, 7 legítimos, **0 falsos positivos**. Declarado que NO exonera: la
  muestra es Alberto probando con códigos de modelo, no técnicos con lenguaje de campo; la
  corrección se hizo igual porque la colisión con «fuego» es un arma cargada.
- **Alternativas descartadas**: (a) seam por ruta (no-op sobre el estado vivo + no cubre el
  fall-through); (b) arreglar el clasificador de F1 (no cubre las rutas tempranas, que son
  el fallo orgánico, y mueve un contrato congelado con gate MT propio); (c) hot-patch en las
  3 salidas del catálogo; (d) dejar la heurística laxa confiando en los 0 FP medidos (la
  muestra no es representativa de los usuarios reales).
- **Gaps / riesgos declarados**: la etapa 2 sigue ABIERTA (testigo en `xfail(strict)`);
  `_MARCAS_AMBIGUAS` es una lista negra —lo que la sostiene es el detector—; la voz se cubre
  por contrato de FUENTE, no conduciendo audio; el doble del instrumento replica a mano el
  orden de grupos de PTB; `user_data` es memoria de proceso (un redeploy lo borra); y no se
  mide CALIDAD de respuesta, solo enrutado y estado.
- **Estado**: ✅ **suite 3.693 passed / 46 skipped / 1 xfailed** · instrumento 27 passed /
  1 xfailed · dúo COMPLETO ×4 rondas (2 caídas de red de Sol/sub-agente, relanzadas).
  **Relacionado**: DEC-196 (el lever revertido, ahora cerrado con medición), DEC-197 (el
  instrumento), TECH_DEBT #70 y #52.

## DEC-199 (s316c) — #68 y #69 CERRADOS contra producción; y la red inestable destapa una clase de defecto que estaba en tres scripts

- **Fecha**: 10 ago 2026 (s316c, madrugada). **Impacto**: ALTO (escribe en dos índices vivos
  + poblá 1.007 objetos de Storage y 1.008 `source_url`).
- **#68 CERRADO**: el lote Casmar/Kidde pasa de **0/0** a **10.161 enunciados + 2.516 hyq**,
  verificado contra la DB (V: 10.161/10.161 ids del manifiesto; hyq: universo completo,
  poison 0, smoke self-hit ✅). Coste real $18,67 (ledger enunciados) + ~$4 (hyq).
- **#69 CERRADO**: `source_url` pasa de **76 → 1.084** de 1.243, con 1.007 objetos (1,30 GB)
  en el bucket. **El residuo de 159 está EXPLICADO**: son exactamente los de sha placeholder
  (`backfill:`, #4 Phase 3) y **cero documentos con sha real quedaron fuera** — verificado
  con una consulta que separa ambos casos, no asumido. Coste marginal 0 € (Pro incluye
  100 GB; se pasa de ~4,0 a ~5,3 GB).
- **EL HALLAZGO DE PROCESO (→ TECH_DEBT #72)**: en una sola sesión, TRES scripts murieron
  por la MISMA causa —excepción de TRANSPORTE (`httpx.ReadError`/WinError 10054) sin
  capturar— y los parcheé de uno en uno según reventaban: `s102_hyq_load` (avanzaba ~200
  filas por intento), `s315_upload_manuales_storage` (**0 de 1.008** subidos: murió en el
  primer fichero) y `s104_a3_load` (tumbó E2 **después** de haber generado los 10.161
  enunciados, con el dinero ya gastado). El patrón común: todos manejaban códigos de ESTADO
  HTTP y ninguno excepciones de TRANSPORTE — son fallos distintos, uno devuelve respuesta y
  el otro no llega a haberla.
- **Decisión técnica que sí es de raíz (dentro de su script)**: cuando el reintento con
  backoff no bastó (la caída duraba más que 1+2+4+8 s), en vez de subir el backoff a ciegas
  se hizo que **bisecte el lote ante fallo de transporte**, reusando el patrón anti-poison
  ya existente: un envío de 500 filas con embedding ronda los 10 MB y cuanta más superficie,
  más fácil que la red lo corte; partiendo, el envío se ADAPTA a lo que la conexión aguante
  y una fila irreductible acaba en `poison`, no en un run muerto. `INSERT_BATCH` 500→150.
  Con eso E2 cargó a la primera. **Alternativas descartadas**: más backoff (no ataca la
  superficie del envío); relanzar a mano N veces (lo estuve haciendo: no escala y depende
  de que yo esté mirando).
- **Deuda declarada, NO resuelta (#72)**: los tres parches son copias del mismo bucle. Falta
  un cliente Supabase común con la política dentro + un test que impida clientes crudos.
  Matiz que impide hacerlo mecánicamente: **la idempotencia que hace SEGURO reintentar no es
  universal** (aquí la dan `UNIQUE(chunk_id,question)`, el skip-si-existe y el resume por
  ids) ⇒ la política debe ser explícita por llamada, nunca mágica.
- **Gaps declarados**: no se ha medido NINGÚN efecto en calidad — esto es cobertura, no
  mejora demostrada; el `--aplicar` de Storage sube documentación de fabricante a un bucket
  público-por-URL (alcance ya adjudicado en s315); y `ANALYZE` se corrió sobre las dos
  tablas, pero el VACUUM-por-fantasmas de DEC-088 no aplica aquí (solo hubo INSERT).
- **Estado**: ✅ verificado contra DB y bucket, no contra códigos de salida.
  **Relacionado**: DEC-194/196/197/198, TECH_DEBT #68, #69, #72, #4 Phase 3.

## DEC-200 (s316d) — Rediseño «punto de decisión único» adjudicado por el dúo (arquitectura sostenida, v3 vigente); pin del sub-agente RESTAURADO a Fable 5; y el barrido de manuales que terminó en 0

- **Fecha**: 11 ago 2026 (s316d). **Impacto**: ALTO (rumbo arquitectónico del despacho
  conversacional; aún SIN construir — gateado por GO de Alberto + dúo del diff).
- **Contexto**: la etapa 2 de #70 fue NO-SÓLIDO ×2 y Alberto preguntó por la vía LLM y por
  agentic/graph RAG; la respuesta canónica (digest + DEC-089/154) es que el cuello no es
  multi-hop y el NO-GO agéntico no transfiere a lo conversacional. Alberto encargó el
  rediseño estructural: «no quiero un Frankenstein».
- **Decisión 1 — diseño v3 VIGENTE** (`evals/s316_rediseno_punto_decision_unico_v3.md`):
  `plan_turn` puro en dos pasadas con CONTRATO DE HECHOS (léxico de marcas como hecho
  permanente; hechos por-consulta a demanda; degradación inventario→RAG como
  `fallback_ruta` del plan) + UN ESCRITOR (el despachador) con tres fuentes de transición
  puras (plan / política / `transicion_basica` para rollback, QUIRK legacy incluido y
  testeado) + flujo de datos fijado (la política resuelve DESDE el estado post-plan — sin
  esto #70 revivía por construcción, Sol C3). Migración en dos fases; la voz NO se expande
  (decisión de producto aparte); guardia −1 y `last_detected_models` se RETIRAN en fase B.
- **Traza del dúo (rondas 6-7, 21 hallazgos, 0 falsos positivos)**: ronda 6 NO-SÓLIDO ×2
  convergente en 2 críticos (pureza que no sobrevivía al I/O de mismatch/inventario;
  rollback que leía un estado sin escritor) → v2 con hechos+un-escritor; ronda 7
  NO-SÓLIDO ×2 pero con veredicto de que **la arquitectura se sostiene** y los hallazgos
  son contratos sobre-afirmados (enmascaramiento de la guardia en fase A — convergente;
  quirk de resurrección de ventana en rollback; clúster feedback sin dueño; 2 writes F1
  fuera del alcance) → v3 con trazabilidad hallazgo→resolución.
- **Decisión 2 — pin del sub-agente RESTAURADO a fable (Fable 5)**, adjudicado por
  Alberto al volver el crédito; CLAUDE.md actualizado. El opus de s292 queda como lo que
  fue: fallback por crédito, no preferencia. Primera ronda del pin restaurado: rindió
  (6+9 hallazgos anclados, convergencia con Sol, verificaciones propias).
- **Decisión 3 — Casmar/Aritech-Edwards CERRADO EN 0 con lección de proceso** (→ #73 y
  memoria): 19 candidatos → 10 por sha → **0 tras comparar REVISIÓN de portada** (los 2
  «manuales nuevos» eran ediciones ANTIGUAS de docs ya ingestados: INS570-3 vs ins570-8;
  P/N …-03 vs …-04). sha256 distinto NO es documento nuevo; la puerta automática de
  revisión queda diseñada en TECH_DEBT #73.
- **Alternativas descartadas**: seguir parcheando la etapa 2 (2 NO-SÓLIDOS = la base no
  aguanta más reglas); LLM orchestrator total (paga en el ~80% de turnos que las reglas
  resuelven gratis); agentic/graph RAG (DEC-089 en su métrica + el grafo YA existe como
  catálogo gobernado; reconsiderable si compatibilidad-cruzada emerge como clase medida);
  seam Haiku anticipatorio (pregunta cero — eliminado del diseño).
- **Gaps**: el diseño NO está construido; fase A exigirá dúo sobre el DIFF (lección FUEGO:
  el diseño sólido no exime al código); léxico ES-only heredado; fall-through de #70 sigue
  XFAIL hasta el lever LLM post-rediseño.
- **Estado**: v3 listo para GO de Alberto. **Relacionado**: DEC-197/198/199, TECH_DEBT
  #70 etapa 2, #72, #73.


## DEC-201 (s316e) — Fase A del rediseño CONSTRUIDA y adjudicada: la equivalencia no se afirmó, se MIDIÓ

- **Fecha**: 11 ago 2026 (s316e). **Impacto**: ALTO (refactor del despacho del bot vivo;
  cero cambio de conducta — y eso es un dato medido, no una promesa).
- **Qué se construyó** (GO de Alberto sobre el v3, DEC-200): `src/orchestrator/turn_plan.py`
  — el punto de decisión ÚNICO — con el contrato de hechos (dos pasadas puras; léxico a
  demanda con necesidad computada puramente; short-circuit de `marca_servida` como
  dependencia DECLARADA del resolver) + `handle_message` reescrito como pre-pasos
  declarados → plan → despachador tonto cuyos campos (`typing`, `log_consulta`) son
  LOAD-BEARING. La guardia −1 sigue viva (fuente activa de fase A) pero DELEGA en el
  predicado del plan: una implementación, drift imposible. 13 returns entrelazados → 3
  pre-pasos + 8 ejecutores censados.
- **El método que hizo la diferencia**: los 19 tests de equivalencia se escribieron ANTES
  del refactor y salieron verdes contra el código viejo — fijaron la conducta como espec.
  Y el dúo de build lo verificó con hierro: **Fable dio el primer SÓLIDO de la sesión**
  con una batería diferencial propia de 32 casos contra HEAD en un worktree (0
  divergencias), 72 combinaciones del predicado perezoso y comparación AST de templates.
- **Los hallazgos del dúo de build, TODOS aplicados** (Sol 6 · Fable 6, 0 falsos
  positivos): campos del plan decorativos → load-bearing con test; sobre-fetch de
  `marca_servida` en el camino más caliente (roundtrip extra + un blip de red mataba
  turnos que jamás tocaban esa función — la versión fase-A de la lección FUEGO) →
  short-circuit declarado con test espía; test de mecanicidad AST declarado-pero-inexistente
  → construido (mordió 2 veces al nacer); tests del plan contra snapshots PRE-guardia
  (el enmascaramiento de fase A, ahora ejercitado); `Hecho` validado (tokens, no texto);
  duplicado sombreante de `_FEEDBACK_PATTERNS` fuera; ancla vacua de DEC-059 corregida;
  observabilidad del predicado restaurada; rama voz muerta eliminada; léxico del v3
  enmendado (el build tenía razón; el «SIEMPRE» del doc chocaba con la restricción
  pagada de coste).
- **Censos actualizados con justificación en el propio assert**: módulos de src/ 117→118
  (turn_plan = producto deliberado); call-sites de `manufacturer_no_model` 2→1 (los dos
  sitios históricos UNIFICADOS en un ejecutor — el propósito del rediseño); censo de
  ramas terminales 13/3 → 3/3/8 con su historia.
- **Gaps**: fase B PENDIENTE (retirar guardia y clave legacy, `transicion_basica`, izar
  los 2 writes F1, actualizar tests pineados del instrumento, y la decisión de disciplina
  de caché que Fable anotó — al retirar la guardia, la invalidación pasaría de
  lista-fresca a caché-estancada); la transición del plan corre ENMASCARADA hasta
  entonces; el fall-through de #70 sigue XFAIL (se cierra con el lever LLM post-fase-B).
- **Estado**: ✅ suite **3.720 passed / 46 skipped / 1 xfailed** (+27 tests nuevos) ·
  dúo de build completo · tally regla C con los veredictos cruzados.
  **Relacionado**: DEC-200 (el diseño), DEC-197/198 (instrumento y guardia), #70.


## DEC-202 (s316f) — Fase B COMPLETADA: un estado, un escritor, la guardia retirada — y las tres divergencias del v3, declaradas con su porqué

- **Fecha**: 11 ago 2026 (s316f). **Impacto**: ALTO (retira mecanismos vivos del bot en
  producción; unifica el estado conversacional de ambos regímenes).
- **Qué hay** (checklist del v3, ejecutado): guardia −1 RETIRADA (TypeHandler +
  `brand_switch_guard` + núcleo) — la invalidación de #70 es `plan.transicion`, aplicada
  por `_aplicar_estado` (escritor único) ANTES de ejecutar la ruta (contrato C3);
  `last_detected_models` y `last_query_time` RETIRADAS — el régimen stub lee/escribe el
  estado ÚNICO vía `transicion_basica` (QUIRK legacy reproducido y testeado: la ventana
  se refresca en todo turno RAG); los 2 writes F1 pasan por el escritor; la voz decide
  con el mismo predicado/escritor/caché; disciplina de caché consolidada en UNA
  implementación (`_lexico_marcas_cacheado`).
- **Las TRES divergencias del v3, con su porqué** (ninguna silenciosa):
  1. **El trío de telemetría NO migra a WorkingState** (v3 §7 decía migrar):
     `last_query`/`last_response`/`last_query_log_id` quedan como clúster de FEEDBACK con
     dueño declarado (`_process_query`), fuera del invariante conversacional. Fable lo
     adjudicó «defendible y mejor que el v3»: migrar cambiaría el anclaje del 👎 tras un
     CLARIFY. Y Sol destapó que el anclaje YA era incoherente (texto nuevo + FK vieja) —
     corregido con el patrón uuid de la ruta RAG: un 👎 tras un clarify ancla a la fila
     del clarify.
  2. **Los writes F1 no se izan literalmente** (v3 §8): el invariante real es el
     CHOKE-POINT sintáctico (`_aplicar_estado`) + fuentes de transición declaradas —
     izarlos solo movería glue sin cambiar conducta. El censo AST se endureció (tuplas,
     Delete, update/setdefault, alcance a turn_plan) y DECLARA su límite: caza clave
     literal, no alias — es un invariante de disciplina verificada, no una prueba total.
  3. **HEAD refrescaba la ventana legacy también en CLARIFY/DECLINE de F1; el build no**:
     solo observable en un flip de flag in-process (post-clarify→stub, HEAD podía
     resucitar contexto expirado). Más sano; declarado en vez de reproducido.
- **La ronda 9 del dúo (Sol 7 · Fable 6+juicio, 0 falsos positivos)**: el CRÍTICO fue de
  Fable y contra MI testigo, no contra el código — el e2e del rollback daba verde SIN
  carry («tensión» no está en `PCI_TERMS`; la vaga iba a RAG con o sin contexto).
  Corregido con término que SÍ gatea + CONTROL de no-vacuidad (sin contexto DEBE
  clarificar) → el verde es atribuible. Fable verificó por su cuenta que el código era
  correcto (espió `build_turn_request`: el contexto llega a retrieval). Convergencia
  Sol/Fable en la voz: fetch EAGER (paréntesis de más — el primer audio tras restart
  pagaba 0,54 s) + fail-open perdido (el predicado propaga por contrato y la voz lo
  llamaba desnudo) — ambos corregidos. `Hecho` con tope de 2 palabras (el vector real
  «pasemos a Morley» pasaba el tope de 64 chars).
- **Gaps**: el fall-through de #70 sigue XFAIL (siguiente: lever LLM con golds de compat
  re-hechos sobre marcas servidas); `marca_no_servida` fetchea fresco DECLARADO
  (presentación, HEAD-parity); el flip de flag in-process tiene la divergencia (3).
- **Estado**: ✅ suites afectadas + completa en verde (cifra final en el commit) · dúo
  completo · Railway desplegará al mergear — smoke de producción = la primera consulta
  real. **Relacionado**: DEC-200/201, #70, TECH_DEBT #52.

## DEC-203 (s316g) — Lever INTENT_LLM: diseñado (dúo r10), y el gate de juicio pre-registrado corta en NO-GO — con UNA divergencia que va a adjudicación de Alberto

- **Fecha**: 11 ago 2026 (s316g). **Impacto**: ALTO (lever de serving conversacional;
  NADA cableado — el gate cortó antes, que es su trabajo).
- **Diseño v2 VIGENTE** (`evals/s316g_lever_intent_llm_propuesta_v2.md`): clasificador de
  intención inyectado en la rama B con el patrón del rewriter (política sin I/O; None =
  diferir = byte-idéntico; fail-open total; decisión trazada en `rag_trace`). Ronda 10
  del dúo: NO-SÓLIDO ×2 con veredicto de dirección; 17 hallazgos integrados (cohorte
  congelada con umbral ASIMÉTRICO; identidad por palabra-primaria — classify devuelve
  nombre completo y 8/26 fabricantes son multi-palabra, verificado; guarda de colisión
  para BRAND_TOKENS; parser/prompt especificados; cirugía del harness declarada con
  aserciones anti-verde-vacuo; gold del path no-servida conservado con cofem; async
  to_thread; mt15; DEC-102 rebajado a heurística de coste).
- **EL GATE DE JUICIO SE CORRIÓ** (cohorte congelada de 40 casos ES/EN etiquetada ANTES
  de medir, K=3, umbrales pre-registrados: falsos SWITCH en COMPAT = 0 · accuracy ≥90%):
  - **Haiku 4.5**: 38/40 (95%) · **2 falsos SWITCH** → **NO-GO**. Uno es grave y claro:
    «which Hochiki bases fit this detector?» 3/3 SWITCH — borraría contexto en una
    compatibilidad legítima EN.
  - **Sonnet 4.6** (mismo prompt, misma cohorte — cambiar de MODELO está permitido por
    el pre-registro; re-tunear el prompt no): 39/40 (97,5%) · **1 falso SWITCH** →
    **NO-GO por el umbral estricto**. p50 1.333 ms · p95 4.409 ms.
- **La divergencia única de Sonnet es el caso LÍMITE deliberado de la cohorte**:
  «¿el mantenimiento de una Kidde es igual que el de esta?» — etiquetado COMPAT por el
  autor (comparativo que referencia el producto en curso), juzgado SWITCH por AMBOS
  modelos con 6/6 votos estables. Dos lecturas defendibles: carry (la comparación
  necesita el producto en curso) o switch (el sujeto informativo es el mantenimiento
  Kidde). **El autor NO se re-etiqueta a sí mismo post-hoc (anti-gate-shopping): la
  etiqueta va a ADJUDICACIÓN DE ALBERTO**, que es su rol en la disciplina de golds
  (precedente hp011#2: los 3 modelos contra el gold ⇒ adjudicar el alcance del gold).
- **Decisión pendiente de Alberto**: (a) adjudicar la etiqueta del caso límite — si
  SWITCH es aceptable, Sonnet queda 40/40 y el lever sigue su secuencia (harness →
  build → dúo del diff → e2e → flip) con Sonnet como clasificador y su latencia
  declarada; (b) mantener el NO-GO y aparcar el lever (el fall-through queda como
  residuo declarado con testigo XFAIL); (c) cohorte v2 re-congelada con tier de
  «límite» excluido del umbral estricto.
- **Gaps**: la cohorte son 40 casos, no producción; la latencia de Sonnet (p95 4,4 s) es
  material para la rama y va declarada; el «19%» de población sigue pendiente de recibo
  versionado (build).
- **Estado**: recibos `evals/s316g_intent_cohort_result_v1{,_sonnet}.json` · nada
  cableado · flag inexistente aún. **Relacionado**: DEC-200/201/202, #70 etapa 2,
  DEC-126 (anti-gate-shopping), DEC-154 (métrica MT propia).


## DEC-203b (s316g) — Lever INTENT_LLM CONSTRUIDO tras el GO adjudicado; el flip queda BLOQUEADO por dos gates declarados

- **Fecha**: 11 ago 2026 (s316g, cierre). **Impacto**: ALTO (rama de la política + flag
  de transporte; default OFF byte-idéntico — verificado por ejecución y por tests).
- **La adjudicación de Alberto (cierra DEC-203)**: la etiqueta del caso límite
  («¿el mantenimiento de una Kidde es igual que el de esta?») pasa a SWITCH — «la
  respuesta-switch no es dañina». Cohorte v1.1 con la nota de adjudicación EN el YAML
  (precedente hp011#2: se adjudica el alcance del gold, no se fuerza al juez). Con ella:
  **Sonnet 4.6 GO 40/40 · 0 falsos SWITCH**, primero re-puntuado (mismos votos, sin
  re-tirar dados) y luego RE-CORRIDO por el runner con PARIDAD TOTAL con lo servido
  (`construir_intent_fn`: timeout 6 s, max_retries=0) y freeze sha256 de
  cohorte+prompt+commit en el recibo: **p50 1.101 ms · p95 1.663 ms**
  (`evals/s316g_intent_cohort_result_v1_1_sonnet.json`). Haiku queda NO-GO por méritos
  (falso SWITCH claro en EN), independiente de la adjudicación.
- **Qué se construyó** (v2 §secuencia, pasos 2-3): `IntentFn` en las 3 superficies del
  precedente rewrite · rama del lever en B con exención de misma-marca por token
  primario (tokenización de `_config_brand_tokens` — el guion de Pepperl-Fuchs incluido)
  y exclusión de `_MARCAS_AMBIGUAS` · `intent_llm.py` (prompt/parser ÚNICA fuente,
  importada por el gate) · flag `INTENT_LLM` default OFF con construcción perezosa a
  nivel PROCESO, fallo de construcción RUIDOSO (centinela, no reintento en caliente) y
  resolución en `to_thread` con ON · harness MT con `stub_intent` por turno + aserción
  de-stub-llamado + `rationale` (la aserción anti-verde-vacuo MORDIÓ en el primer run
  de mt15 — un gold mal diseñado — y en un probe de Fable) · golds: mt13 con marcas
  SERVIDAS + gold cofem (path no-servida-alcanzable) + mt15 (gemelos compat/switch)
  → **gate MT re-congelado 52/52**.
- **Ronda 11 del dúo (Sol 7 · Fable 6+3, 0 falsos positivos, TODO aplicado)**. Los que
  cambiaron el build: (Sol C1, verificado ejecutando) la exención `any()` se tragaba el
  caso mixto «los Detnov fallan, dime el de Morley» — el gate midió un camino que el
  serving SALTABA; fix: exención `all()` + lever alcanzable desde la rama `same_mfr`
  con marca ajena presente, con tests. (Fable M1, probado) `split()[0]` fallaba con el
  único fabricante con GUION. (Fable M2) el gate había medido con cliente reutilizado y
  el serving construía cliente por turno con max_retries=2 (~19 s de cola jamás medida)
  → cliente a nivel proceso + max_retries=0 + gate en paridad. (Fable M3) el fallo de
  construcción del cliente era un no-op SILENCIOSO con el flag ON.
- **EL FLIP QUEDA BLOQUEADO** (Sol C3, declarado en el v2): (1) paquete de observabilidad
  en `rag_trace` (esquema cerrado: builder+validador+allowlist+tests; hasta entonces,
  log estructurado); (2) e2e del camino servido (cliente frío, timeout, fail-open) con
  recibo. Sin ambos, `INTENT_LLM` no se enciende en Railway.
- **Gaps**: cohorte = 40 casos (cota estadística declarada: 0/22 falsos SWITCH acota
  ~14% con confianza razonable; el residuo lo tolera la ASIMETRÍA de daños — soltar
  contexto de más es recuperable, responder de la marca equivocada es engañoso — y lo
  medirá la traza); población de la rama = cota 13/69 = 18,8% versionada
  (`evals/s316g_poblacion_rama_b_v1.json`, muestra no representativa de técnicos);
  asimetría Honeywell (Fable, especulativo) declarada sin medir; RGPD anotado sin
  decidir ([DECIDIR] intacto).
- **Estado**: suites adyacentes 129 passed/1 xfailed · MT 52/52 · suite completa en
  verificación final. **Relacionado**: DEC-203, DEC-200/201/202, #70 etapa 2 (el
  testigo XFAIL se retira cuando Alberto flippee tras los dos gates).

## DEC-204 (s316h) — Los DOS gates del flip de INTENT_LLM cerrados: sección `intent` en el esquema cerrado de rag_trace + e2e del camino servido; el flip queda EN MANOS DE ALBERTO

- **Fecha**: 11 ago 2026 (s316h). **Impacto**: MEDIO (esquema de telemetría persistida +
  refactor del seam del handler; conducta del bot INTACTA — flag OFF sigue byte-idéntico,
  y el gate MT + el instrumento de transporte lo verifican).
- **Gate 1 (observabilidad)**: sección `intent` REQUERIDA en `rag_serving_trace_v1`
  (`src/rag/runtime_trace.py`): `{status ∈ {not_wired, off, not_invoked, invoked,
  construction_failed}, decision ∈ {none, compat, switch, fail_open}, latency_ms ≤ 60 s}`
  con COHERENCIA CERRADA (sin invocación ⇒ none/0 — coerción en builder, RECHAZO en
  validador; invocado ⇒ decisión obligatoria: `fail_open` ES decisión). **`not_wired` ≠
  `off`** (Sol r12 M1): «telemetría sin cablear» no puede disfrazarse de «lever apagado» —
  la distinción que `measured` da a `retrieval` (s306) y `timings` (s315); el handler
  estampa `off` EXPLÍCITO. **Captura POR TURNO**: `_intent_seam(intent_obs)` extraído del
  handler; el wrapper estampa en el hilo de la llamada — la lectura de `fn.ultima`
  (estado compartido de proceso, carrera entre turnos concurrentes) SALE del camino
  servido; `ultima` queda para el gate de juicio (secuencial). Token de esquema se
  mantiene v1 (precedente s306/s315); el riesgo de acreción queda declarado en
  **TECH_DEBT #74** (Sol r12 M3 — fix cuando exista consumidor de re-validación).
- **Gate 2 (e2e servido)**: `scripts/s316h_intent_e2e.py` ejecuta LA composición servida
  (el `_intent_seam` del bot + resolve real con `rewrite` centinela + to_thread +
  build/validate de la traza) — recibo `evals/s316h_intent_e2e_result_v1.json` **PASS
  6/6 legs**: off byte-inerte · frío (TLS real + ATESTACIÓN de config servida: timeout
  6 s / max_retries 0, criterio de PASS — Sol r12 M2) · caliente (cliente de proceso) ·
  timeout ⇒ fail-open inmediato sin cola de retries · key mala sin excepción ·
  construcción fallida ruidosa + centinela + trazada. Criterio PASS = SOLO mecánica
  (canarios de la cohorte congelada 5/5, INFORMATIVO — anti-gate-shopping). Recibo con
  PROVENIENCIA: `artefactos_sha256` de los 6 ficheros ejecutados + `git_estado`; la
  corrida final se genera SOBRE el commit (Sol r12 C2 + Fable F3).
- **El pegamento del handler quedó gateado EN CI** (Sol r12 C1, el hallazgo que cambió el
  diseño): el e2e no conduce `handle_message`, así que la costura
  flag→seam→política→build site→log_query se fija en el instrumento de transporte
  (`test_lever_intent_atraviesa_el_pegamento_del_handler` + espejo flag-off): la clase
  «el gate mide un camino que el serving salta» (r11) no puede volver sin CI en rojo.
  Bonus del e2e: su 1ª corrida cazó que el rationale servido lleva prefijo de ruta
  (`carry_forward:brand_compat_confirmed_llm`) — un símil habría pasado.
- **Dúo r12 (Sol 6 · Fable 5, convergentes, 0 contradicciones, 0 FP, TODO aplicado)**:
  además de lo anterior — cifras de la prosa re-ancladas al recibo (F1/menor: la
  propuesta citaba la corrida FAIL previa; corregido NO re-copiando números), `rewrite`
  centinela (F2: el handler siempre pasa rewrite — paridad de firma), supuestos
  documentados (F4: el parser estricto es el guard anti-drift del enum; F5: celda sin
  lock = last-write-wins benigno). Fable verificó a favor la mecánica («la coherencia
  builder+validador es real y CERRADA»). Tally: regla C completa, adjudicado.
- **Alternativas descartadas**: traza en clarify/decline (toda decisión invocada resuelve
  retrieve; `not_invoked` no lleva información de decisión) · telemetría vía `fn.ultima`
  (carrera) · bump del token a v2 (aparato sin consumidor — #74 lo vigila) · e2e vía
  Telegram real (el seam extraído ejecuta el código del handler sin transporte vivo).
- **Gaps declarados**: filas clarify/decline sin sección intent · leg construcción con
  inyección declarada de fallo · leg timeout con constructor real a 0,05 s primado en
  celda (el default servido lo atesta el leg frío) · latencia del wrapper = turno real
  (incluye `contexto_del_estado`).
- **EL FLIP ES DE ALBERTO** (Railway: `INTENT_LLM=on`; los dos gates de DEC-203b están
  cerrados). Tras el flip: retirar el testigo XFAIL del fall-through y estampar el
  veredicto del lever en `LEVER_DIGEST` con la traza real de la 1ª semana.
- **Relacionado**: DEC-203/203b, s306 (`retrieval`), s315 (`timings`), TECH_DEBT #74,
  ref tally `evals/adversarial_review_log.jsonl` ts=2026-08-11T23:11:00.

## DEC-205 (s317) — Puerta de REVISIÓN en la ingesta construida (#73 CERRADO): el sha prueba bytes, la puerta prueba información

- **Fecha**: 12 ago 2026 (s317). **Impacto**: MEDIO en zona de dolor (corpus/ingesta);
  cero efecto en serving — solo el driver `ingest_new.py` cambia de conducta.
- **Contexto**: Alberto redirige a «arquitectura y flujos» (el censo del 👎 se aparca:
  sin técnicos activos no hay señal). #73 nació en s316d: los 2 candidatos «nuevos» del
  barrido Casmar eran revisiones VIEJAS (INS570-3 vs issue 8; P/N …-03 vs …-04), cazadas
  a mano — ingestar una revisión vieja = dos activos del mismo manual sin cadena (#4) y
  el bot puede citar el caducado.
- **Qué hay** (`src/reingest/revision_gate.py` + cableado en `gates()` +
  `tests/test_s317_revision_gate.py` 35 tests + `scripts/s317_revision_census.py`):
  señales de edición $0 (filename + portada PyMuPDF) en familias MUESTREADAS del corpus
  real — pn_utc (P/N+`_rNNN` con doble coincidencia), rnnn, issue/INS, iss_fecha
  (ddMMMyy), rev numérica/letra (jamás comparadas entre sí), fecha AAAAMM, v — ·
  idioma=identidad · cruce corpus-wide PAGINADO (clase #72: PostgREST corta a 1000 en
  silencio y `documents`=1.069) · contrato #73 LITERAL (corpus >= candidata ⇒ BLOQUEADO)
  · cruce INTRA-LOTE (igualdad no-mutua) · señal PERSISTIDA en `documents.revision`/
  `revision_date` (las columnas de migrations/001, NULL hasta hoy) e índice que las relee
  · fail-open LISTADO sin señal · `--ignorar-revision [GLOB]` auditado en recibo.
- **Dúo r13 (Sol 8 · Fable 7, convergentes en 3, 0 FP, TODO aplicado)**: los críticos
  fueron la ceguera INTRA-LOTE (dos revisiones juntas pasaban las dos — así pudo nacer
  el par vivo) y la señal NO persistida (una revisión solo-de-portada quedaba invisible
  para lotes futuros). Fable PROBÓ que la fecha contaminaba la tupla de revisión
  («rev 4 30-10-2024» → rev=(4,30,10), comparaba DÍAS) → extracción sobre CRUDO con
  multi-parte solo `.`/`_`. Portada acotada a familias span-independientes (INS) con
  guarda anti-cita. Y AMBOS volvieron a cazar framing mío (censo: «0 pares falsos»
  absoluto, «lo habría bloqueado» incondicional) — 3ª ronda seguida con la misma clase;
  el fix vuelve a ser declarar, no adornar.
- **Censo del corpus real** (`evals/s317_revision_census_v1.json`): 1.069 activos ·
  134 con señal (13%; cobertura sobre candidatos nuevos será mayor — portal trae fecha
  sistemática — pero NO está medida) · **1 par multi-revisión intra-familia**
  (MI_KIDDE_KE_DP312x 202503/202512) → **adjudicación de Alberto: marcar supersedida la
  202503** · par inter-familia conocido INVISIBLE por diseño (MI-Casmar↔bcn, DEC-192).
- **Alternativas descartadas**: comparar por `document_family` (no separa revisiones
  con `_rNNN`/issue) · fail-closed total (87% sin señal → bloquearía lotes legítimos;
  el TECH_DEBT predeclaró fail-open-listado) · LLM en portada (coste/no determinista) ·
  poblar `supersedes_id` automático (escritura fuera del alcance; el recibo anota
  candidatas).
- **Gaps declarados**: cobertura 13% en nombres del corpus · revisiones raras
  perdidas a propósito (RevIMarch, P/N sin _rNNN, rev pegado tipo MIEMI120rev05) ·
  índice del corpus solo-filename+columna (portadas del corpus no están a mano) ·
  dirección vieja-primero (SUPERSEDE procede; retirar a la vieja es la cadena #4).
- **Relacionado**: TECH_DEBT #73 (cerrado) · #4 (cadena supersede — siguiente pieza
  natural) · #72 (la paginación de aquí es su patrón) · DEC-192 · tally r13
  ts=2026-08-12T00:25:09.

## DEC-205b (s317b) — FLIP DE INTENT_LLM EJECUTADO por Alberto y VERIFICADO; testigo XFAIL retirado; veredicto de producción pendiente de tráfico

- **Fecha**: 12 ago 2026. **Impacto**: registro de estado (la decisión fue DEC-203b/204;
  el flip es acción de Alberto).
- **Verificación (Protocolo 1, nunca inferir)**: API GraphQL de Railway por SERVICIO —
  `worker.INTENT_LLM='on'` junto a la config esperada (CONVERSATION_POLICY=impl,
  ORCHESTRATOR_PATH=on, CHUNKS_TABLE=chunks_v2, RERANK_TOP_K=10,
  GENERATOR_PROMPT_VARIANT=fidelity). El lever corre en producción: #70 etapa 2 servida.
- **Mandatos de DEC-204 ejecutados**: testigo XFAIL del fall-through RETIRADO del
  instrumento de transporte (su relevo vivo = el test de pegamento flag-ON + espejo
  flag-off); fila INTENT_LLM estampada en `LEVER_DIGEST` (suite pasa a 0 xfailed).
- **Pendiente declarado**: el veredicto CONDUCTA-EN-PRODUCCIÓN se estampa con la traza
  real (sección `intent` de rag_trace) cuando haya tráfico — sin técnicos activos no
  hay filas que leer. Nota de secuencia: Alberto declaró «PR239 mergeada» pero la PR
  estaba OPEN (checks verdes, MERGEABLE) — el merge a main queda en su mano; el flip es
  VÁLIDO igualmente (el lever vive en main desde PR #238). [Resuelto: Alberto la mergeó
  después — main 65166b6.]
- **Relacionado**: DEC-203/203b/204/205.

## DEC-206 (s317) — Cliente HTTP compartido de proceso (#72 FASE 1 = rapidez fase 2): retrieval −76% medido, paridad A/B, dúo r14

- **Fecha**: 12 ago 2026 (s317, rumbo autónomo adjudicado por Alberto: arquitectura/
  flujos + velocidad). **Impacto**: ALTO en zona de dolor (transporte de TODO el
  serving path) — dúo completo r14.
- **El hecho que lo justifica** (perfil v1, DEC-205): 14 `httpx.Client` construidos POR
  CONSULTA = 7,25 s de contextos SSL + ~3,4 s de handshakes ≈ **~10 s/turno de overhead
  puro** sobre 19 s calientes de retrieval. 55 sitios de `src/` repetían el patrón.
- **Qué hay** (`src/http_pool.py` + migración de 55 sitios + `conftest.py` raíz +
  `tests/test_s317_http_pool.py`): UN cliente por proceso (limits EN el transporte:
  keep-alive 10, expiry 30 s, max 40) · shim `abierto(timeout=X)` de UN token por sitio
  (cuerpos intactos, timeouts por-sitio idénticos, jamás inyecta None) · CERO reintentos
  (ni de connect — hasta eso es política; fase 2 de #72) · kill-switch `HTTP_POOL=off`
  (Railway, sin deploy) con cliente fresco POR BLOQUE `with` (la forma exacta de hoy) ·
  **default ON** (infra de transporte con paridad medida, no conducta).
- **Medido** (recibos v1→v2 del perfil): retrieval caliente **19,0 → 4,5 s (−76%)** ·
  frío **53,5 → 12,4 s (−77%)** · paridad A/B INTERCALADA (3 queries × 3 reps/modo):
  cero diferencia atribuible al pool con el jitter base medido en el control off-off ·
  proyección sobre la traza real (retrieve 11-27 s/turno): ~3-8 s.
- **Testabilidad (decisión estructural)**: la suite ENTERA corre con `HTTP_POOL=off`
  (conftest raíz) — los ~20 ficheros que fingen la red parcheando `httpx.Client` siguen
  interceptando SIN churn y verifican la EQUIVALENCIA de los 55 sitios; el pool ON tiene
  tests dedicados (pool EFECTIVO, no kwargs) + trinquete estructural (`httpx.Client(`
  prohibido en `src/**` salvo http_pool) + la medición real. **Gap declarado**: el
  camino pool-ON del serving no corre en CI — coste aceptado y mitigado.
- **Dúo r14 (Sol 5 · Fable 4, 0 FP, TODO aplicado)**: Sol M1 VERIFICADO ejecutando —
  los `limits` del cliente eran CÓDIGO MUERTO con transporte explícito (expiry real 5 s,
  no 30) → limits al transporte + test del pool efectivo. Sol M3/Fable F1: «retries=1
  cubre la conexión caducada» era FALSO (solo cubre connect) → retries retirado y el
  modo de fallo keep-alive-muerta DECLARADO residual (una petición sobre conexión que el
  servidor cerró falla con ReadError sin reintento; mitigación expiry 30 s). Sol M2:
  kill-switch por-bloque, no por-petición. Sol C1/M5≡Fable F2: la evidencia n=1 no
  sostenía el default ON → sonda reforzada + declaración del PoolTimeout bajo picos.
  Fable F3: footgun timeout=None. Fable F4: trinquete estructural. 4ª ronda consecutiva
  con hallazgo de FRAMING mío (esta vez «cubierto» donde era «residual»).
- **Colaterales cazados por CUATRO TRIPWIRES independientes de la casa** (no por el
  dúo): (1) el sello de implementación de P1 exigió añadir `http_pool.py` al manifest;
  (2) el registro de flags exigió declarar `HTTP_POOL`; (3) el inventario de lecturas
  de entorno de la release-config exigió clasificarlo (`ALLOWED_SAFE_VALUES`, on/off);
  (4) **el más serio**: el test del guard PostgREST de P1 cazó que el pool ESQUIVABA la
  frontera de seguridad — el guard parchea el `httpx` de 4 módulos de producto (a
  propósito, sin tocar el global) y los 4 ruteaban ya por `http_pool` → el guard cubre
  ahora también esa superficie (cierra el singleton, fuerza el kill-switch en su scope
  y su `httpx` es el proxy; todo en `_saved`, fail-closed). Además el fix del
  kill-switch por-bloque reventó 54 fakes hasta delegar en el PROTOCOLO `with` del
  cliente (no `.close()`) — los fakes de la suite son el contrato de forma, y lo
  hicieron valer. Lección de la clase: **un cliente compartido re-rutea superficies que
  otros aparatos creían locales** — cada guard/patch/fake por-módulo es un consumidor a
  censar antes de mover el transporte.
- **Alternativas descartadas**: refactor con dedent (blast radius de 60 cuerpos) ·
  async-izar el pipeline (otra obra) · retries de petición ahora (fase 2, idempotencia
  no universal) · migrar los caminos offline (no pagan por turno).
- **FASE 2 de #72 (pendiente, con su dúo)**: política de reintentos consciente-de-
  idempotencia + paralelizar los canales de retrieval (el residual son ~4,4 s de espera
  SECUENCIAL de ~14 RPCs sobre conexión viva).
- **Relacionado**: DEC-205 (perfil v1) · TECH_DEBT #72 · tally r14
  ts=2026-08-12T01:18:06.

## DEC-207 (s317c) — #72 FASE 2: paralelización de canales léxicos + retries transitorios read-only (dúo r15): mediana de retrieval 4,2 → 2,6 s con PARIDAD EXACTA

- **Fecha**: 12 ago 2026 (s317c, rumbo autónomo). **Impacto**: ALTO en zona de dolor
  (conducta de carga del serving) — dúo completo r15 ANTES del build.
- **Qué hay** (sobre el pool de DEC-206, que sigue intacto):
  - **2a — paralelización**: los canales léxicos 3a/3b del retriever (content/diagram/
    keyword/synonym/full-query, hasta 6 tareas GET read-only) se ejecutan en
    `ThreadPoolExecutor` con orden DETERMINISTA por submit-order (el resultado se
    ensambla en el orden del bucle secuencial de hoy, byte-idéntico por construcción).
    Flag propio `RETRIEVAL_PARALLEL` (default on, Railway) — el kill-switch del pool NO
    cubre esta fase (Sol r15 M1: cada mecanismo lleva el suyo).
  - **2b — retries**: `abierto(timeout=X, reintentos=1)` OPT-IN por sitio, solo
    serving read-only SIN veredicto previo de no-retry. El set reintentable EXCLUYE
    `PoolTimeout` (Fable r15 F2: es backpressure LOCAL — reintentarlo amplifica carga
    justo bajo saturación, que 2a agrava). Backoff fijo 0,2 s, N=1: cubre el
    transitorio de red; el corte LARGO sigue siendo trabajo de la reanudación/bisección
    (Sol r15 M4 — la clase s316c NO se re-litiga con retries). Los 4 canales s306
    (VECTOR/ENUNCIADOS/HYQ_*) conservan su fail-open MEDIDO intacto; los scripts con
    bisección+poison (s104/s315) quedan FUERA (retry de POST sin upsert = duplicados;
    Sol r15 M3 verificado leyendo s104). Flag `HTTP_RETRIES` (default on).
  - **Observabilidad**: canales `CONTENT`/`DIVERSIFY` añadidos a la allowlist CERRADA
    de `rag_trace` con su `except` cableado (Sol r15 M5: content_search y el fetch del
    diversify tragaban excepciones sin traza) — el patrón s306 exacto.
- **Medido** (recibos `s317_rpc_timeline_v2_paralelo.json` + `s317_fase2_paridad_v1.json`):
  turno perfilado 30 RPCs en **5,19 s** wall-clock · gate de paridad A/B (3 queries ×
  3 reps): **PARIDAD_EXACTA de ids servidos en las 3** · mediana **4,2 → 2,6 s (−38%**
  sobre el pool ya activo; acumulado desde el perfil v1: **19,0 → 2,6 s, −86%**).
- **Dúo r15 (Sol 6 · Fable 5, convergentes en el precedente hueco, 0 FP, TODO
  aplicado)**: mi claim «3c lo hace desde s59» era HUECO (fan-out real = 1 por el
  `break`; 5ª ronda consecutiva cazando framing del autor) → la conducta de carga se
  trató como NUEVA: cap de workers, gate de paridad, kill-switch propio. PoolTimeout
  excluido del set reintentable. `diagram_search` cubierto explícitamente (Fable F3).
  Proyecciones re-etiquetadas como diana-de-gate, no promesa (Fable F4, Sol m6).
- **Alternativas descartadas**: asyncio (reescritura del pipeline; el executor ya es
  el patrón de la casa) · retry en los 4 canales s306 (re-litigaría DEC-089/#63 sin
  evidencia nueva) · retry en scripts (política de reanudación ya existente y mejor) ·
  backoff exponencial en serving (un turno interactivo no puede esperar 1+2+4 s).
- **Qué queda de #72 (fase 3, si algún día paga)**: contratos de idempotencia por
  upsert en los WRITES de scripts — hoy cubierto por bisección+poison; sin señal de
  que duela. La deuda #72 queda CERRADA en lo que el serving necesita.
- **Relacionado**: DEC-205/205b/206 · tally r15 ts=2026-08-12T08:28:43.

## DEC-208 (s318) — #71: frame `legal_disclaimer` en el evidence_contract CONSTRUIDO flag-off; el ON es adjudicación de Alberto (DEC-148); dúo r16 con dos críticos contra los recibos del autor

- **Fecha**: 12 ago 2026 (s318). **Impacto**: MEDIO en zona de dolor (aparato protegido
  del contrato de evidencia) — dúo completo r16.
- **El defecto (#71)**: el apéndice «Obligaciones de evidencia del manual» citó el
  párrafo de responsabilidad legal de KGS (bcn-3100017 p.4) como obligación técnica.
  Mecanismo confirmado en el gate real: el boilerplate lleva cuantificador universal
  («en ningún caso», «cualquier pérdida») + vocabulario modal — pasa TODOS los gates de
  `_universal_obligations` y entra al apéndice.
- **Qué hay**: frame `legal_disclaimer` en la familia `_universal_frame_skip` (encaje
  estructural: la familia que ya salta capability/conditional/example) ·
  `_LEGAL_DISCLAIMER_RX` clase RESPONSABILIDAD con formas fuertes sin guarda y formas
  negadas CON guarda de contexto de exención (≤90 chars) SIMÉTRICA ES/EN (Fable r16 F1:
  «el módulo no es responsable de generar la alarma» es arquitectura real) · clase
  GARANTÍA fuera a conciencia · PT defensivo (0 en censo, declarado) · flag
  `EC_LEGAL_DISCLAIMER_SKIP` default OFF byte-idéntico + versión de léxico EFECTIVA en
  el recibo (v2 off / v3 on — un recibo v3 con el frame apagado mentiría) · 24 tests
  incluyendo el CAMINO REAL (la cláusula Notifier entra con OFF, desaparece con ON,
  control técnico invariante).
- **Población y efecto medidos**: censo 108 docs/119 chunks (105 ACTIVOS — Sol M5) ·
  sonda v2 por `_universal_obligations` con pregunta-oráculo (patrón DEC-173):
  **83 obligaciones legales removidas (70 docs) · 0 no-legales cambiadas · 28 mixtas
  listadas verbatim** (`evals/s318_disclaimer_probe_v2.json`).
- **Dúo r16 (Sol 5 crítico-máx · Fable 4 SÓLIDO-CON-RESERVA, 0 FP, TODO aplicado)**:
  Sol C1 — la sonda v1 medía el REGEX y vendía «129 frases que desaparecerían»
  cuando el contrato exige cuantificador+compuesto+forma+aplicabilidad → sonda v2 por
  el camino real (129→83, la cifra honesta). Sol C2 — «mixta no observada» se
  contradecía con la propia sonda → 28 listadas. Sol M3 — 2 variantes del censo fuera
  del regex «que el runtime cubriría» (falso) → añadidas con tests. Sol M4 — tests sin
  el camino protegido → test del gate real. Fable F1 — guarda ES ausente (la reserva).
  6ª ronda consecutiva cazando framing del autor.
- **EL ON NO SE DECIDE AQUÍ**: aparato protegido (DEC-148) — la adjudicación viaja en
  el paquete de sentada única (`evals/s318_sentada_adjudicacion_packet_v1.md`:
  DP312x + B2 + #71) y el FULL fresco queda detrás de la sentada (secuencia de
  Alberto). Con el flag OFF el merge no cambia NADA.
- **Alternativas descartadas**: excluir por página/posición (el boilerplate no siempre
  abre el doc); listar docs a mano (no escala a 30+); tocar el detector de callouts
  `safety_mandatory` (el defecto entró por la ruta universal; otra ruta = evidencia
  nueva); clase GARANTÍA dentro (pierde contenido operativo real).
- **Relacionado**: TECH_DEBT #71 · DEC-148 · DEC-173 (patrón oráculo) · tally r16
  ts=2026-08-12T11:15:56.

## DEC-209 (s319) — Consolidación PR-A: backup lógico restaurable + backfill de revisión + paquete de apertura preparado (dúo r17 PRE-build)

- **Fecha**: 12 ago 2026 (s319; mandato de Alberto: sesión de consolidación 1+2+3+4 +
  puntos 1/4 de apertura; el elefante DEC-074 detrás). **Impacto**: MEDIO (writes
  mecánicos a documents; scripts nuevos; cero cambios de serving).
- **Dúo r17 PRE-BUILD** (Sol 10 — 2 críticos — · Fable 3, 0 FP, NO SÓLIDO ambos →
  propuesta v2 con TODO aplicado ANTES de construir): los críticos re-diseñaron el
  backup (sin gate de restauración un recibo prueba bytes, no recuperación; y un dump
  estático NO hereda la retención RGPD de la tabla). Fable cazó un ANCLA FALSA mía
  («verificado import en s277_c1_p1.py:210» — era un dict; la attestation es POR
  STRING en :5891) — 7ª ronda consecutiva de framing del autor, la clase más grave.
- **A.1 Backup** (`scripts/backup_supabase.py` + runbook en ENTORNO_CLOUD): capa
  CORPUS/IDENTIDAD (documents · chunks_v2 · chunks_v2_enunciados · chunks_v2_hyq,
  columnas derivadas DINÁMICAMENTE de la fila real — las listas a mano fallaron 4/4 —
  sin embedding/search_vector) → JSONL.gz en OneDrive + **drill de restauración
  obligatorio** (SQLite: counts + FK docs↔chunks + spot-check) + coherencia pre/post.
  **Primera corrida: PASS** — 1.243 + 26.215 + 33.003 + 72.642 filas
  (`evals/s319_backup_receipt_20260812T140113Z.json`). RPO ≤1 lote/1 mes · RTO horas.
  **La capa de DATOS PERSONALES (7 tablas) queda FUERA** — [DECIDIR-Alberto]: (A)
  así se queda (el desastre lo cubre el backup gestionado de Supabase) o (B) entra
  con TTL/cifrado/borrado verificable. Claim corregido (Sol m): lo que no existía
  era backup LÓGICO restaurable bajo nuestro control.
- **A.2 Backfill de revisión** (`scripts/s319_revision_backfill.py`): FILENAME-ONLY
  (la portada del store es OTRA fuente que la PyMuPDF de la puerta — pase de
  portadas solo tras gate de equivalencia muestral) · **94 aplicados** sobre 1.069
  activos (110 ya poblados por la puerta; 865 sin señal de filename — límite
  honesto) · reversible (solo NULL→valor, ids en recibo) · **avance PARCIAL de #4**
  (document_family y cadenas NO van aquí). **El censo de colisiones resultante
  encontró EXACTAMENTE 1 par: DP312x 202503/202512 — valida cruzado el censo s317**
  (el par MI/bcn de DEC-192 es inter-familia: ceguera declarada).
- **A.3 Apertura, puntos 1/4**: `docs/AVISO_PRIVACIDAD_V8_BORRADOR.md` (6 [DECIDIR]
  tabulados: base jurídica, retención, claim de cobertura 3→30+, cláusula
  profesional-externo, incentivos, banner beta; NO desplegable sin abogado; bump
  v7→v8 = re-aceptación de todos, gate por versión s295) ·
  `scripts/s319_trafico_census.py` (join answer_feedback + REDACCIÓN: uid→hash12,
  textos fuera del repo con --con-texto; smoke contra datos reales: 25 consultas/
  1 usuario/5 feedback desde 1-ago).
- **Alternativas descartadas**: pg_dump binario (sin postgres local; PostgREST
  paginado basta y reusa #72) · incluir PII con TTL propio (aparato sin decisión) ·
  backfill con portadas del store (fuente no validada) · automatizar el backup con
  cron (hasta que el manual duela).
- **Relacionado**: DEC-205 (puerta #73) · TECH_DEBT #4 (parcial) · tally r17
  ts=2026-08-12T15:53:58 · PR-B/PR-C siguen en esta sesión.

## DEC-210 (s319) — Consolidación PR-B: graduación de flags lote 1 (7 + 1 pareja de 97); dúo r18 tumbó dos candidatos y endureció los guards

- **Fecha**: 12 ago 2026 (s319). **Impacto**: MEDIO en zona de dolor (defaults del
  serving) — dúo completo r18 (Sol 5 · Fable 5, 0 FP, TODO aplicado).
- **Regla del lote** (r17): SETTLED con métrica + valor VIVO en Railway (verificado por
  API, patrón DEC-195) + cero intención de volver. El default cambia EN CÓDIGO; las
  vars de Railway quedan redundantes (la lista de retirables es de Alberto, abajo).
- **GRADUADOS (default viejo → nuevo)**: GENERATOR_PROMPT_VARIANT base→fidelity
  (DEC-098) · RERANK_TOP_K 5→10 **EN PAREJA con** LLM_MAX_TOKENS 2048→3500 (r18 Sol
  M1≡Fable F1: el 10 se validó ACOPLADO al 3500 — DEC-092b «0 truncado con 3500»; un
  default 10+2048 era la combinación MEDIDA como mala; el 3500 es el valor RECIBIDO,
  no el de Railway) · ENUNCIADOS_MULTIVECTOR off→on (LEVER_DIGEST fila A3: PR #111 +
  verificado en prod — ancla corregida por Fable F3) · HYQ_TABLE off→on (DEC-099) ·
  GENERATOR_FOLLOWUPS on→off (métrica 10/10→0/12; cita honesta r18/Fable F2: la
  recomendación D1 sigue formalmente sin adjudicar — se gradúa el estado APLICADO en
  Railway) · ANTI_DIAGRAM_INVENTION off→on + WIRING_TOPOLOGY_GUARD off→on (DEC-162a),
  ambos con **parser ESTRICTO nuevo** (r18 Sol M3: un typo en Railway degradaba un
  guard de SEGURIDAD a no-op silencioso; ahora RuntimeError ruidoso, espejo HYQ).
- **EL GATE DE PRE-VERIFICACIÓN DISPARÓ 2 VECES (para esto existe)**:
  (1) `LLM_MAX_TOKENS` Railway=8000 SIN recibo en DECISIONS (verificado por ambos
  revisores: 0 hits) → la discrepancia 8000-vs-3500 queda ADJUDICABLE por Alberto
  (¿deliberado con el swap de modelo?); el default graduado es el recibido.
  (2) `GENERATOR_SELECTION_BLOCK` FUERA del lote (r18 Sol M2): DEC-101 = «candidato
  pendiente de GO» con cat021 flaky — Railway=on es estado operativo, no veredicto.
  También fuera (r17): GENERATOR_DIRECT_FIRST y VISUAL_ASSETS_LISTING_GATE
  (asentamiento sin métrica).
- **Onda expansiva medida**: 11 tests de 3.829 codificaban el contrato viejo
  («default off/base») → actualizados uno a uno manteniendo SIEMPRE el mundo legacy
  construible por env explícito (byte-comparado). El default sin env ahora ES la
  conducta ship compuesta (fidelity+followups-off+guards-on), assertada exacta.
- **Rollback**: idéntico al de siempre — una env var en Railway por flag (nada se
  borra del código). CI/dev sin vars pasa a conducta ship (objetivo declarado).
- **Lista de vars de Railway ahora redundantes (retirarlas = decisión Alberto, sin
  prisa)**: GENERATOR_PROMPT_VARIANT, RERANK_TOP_K, ENUNCIADOS_MULTIVECTOR,
  HYQ_TABLE, GENERATOR_FOLLOWUPS, ANTI_DIAGRAM_INVENTION, WIRING_TOPOLOGY_GUARD.
  NO redundantes (siguen mandando): LLM_MAX_TOKENS=8000 (adjudicable),
  GENERATOR_SELECTION_BLOCK=on, GENERATOR_DIRECT_FIRST, VISUAL_ASSETS_LISTING_GATE,
  INTENT_LLM, CONVERSATION_POLICY, ORCHESTRATOR_PATH (PR-C).
- **Relacionado**: DEC-209 (PR-A) · propuesta v2 r17 · lote doc
  `evals/s319_graduacion_lote1_v1.md` · tally r18 ts=2026-08-12T16:44:43.

## DEC-211 (s319) — Consolidación PR-C: el camino LEGACY de serving RETIRADO; el orquestador + F1 son la ruta ÚNICA y el default (dúo r19)

- **Fecha**: 12 ago 2026 (s319, cierre de la sesión de consolidación). **Impacto**: ALTO
  (ruta única de serving) — dúo completo r19 (Sol 5 · Fable 4, 0 FP, TODO aplicado).
- **Qué murió**: el `else` inline del handler (`execute_rag_turn` en `_process_query`) y
  el flag `ORCHESTRATOR_PATH` (config, registro, imports; testigo: `not hasattr`). Dos
  rutas que deben evolucionar juntas eran la clase que produjo #70. También RETIRADO
  `turn_result_from_pipeline` (shadow.py — adaptador de la pierna muerta; r19 Sol m5).
- **Qué graduó**: `CONVERSATION_POLICY` default `stub`→`impl` (= producción verificada
  desde su ship, DEC-205b) con **enum ESTRICTO impl|stub** (r19 Sol M1 ≡ Fable: un typo
  degradaba al stub EN SILENCIO — cambio de conducta servida sin señal; ahora revienta).
- **EL ROLLBACK CAMBIA (documentado en ARCHITECTURE + aquí)**: quitar la var YA NO baja
  al stub (deja impl). Rollback = `CONVERSATION_POLICY=stub` EXPLÍCITO, y es **ÚLTIMO
  RECURSO con degradaciones declaradas** (r19 Sol M2): (a) deja `INTENT_LLM`
  INALCANZABLE — reabre el fall-through de #70; (b) resucita el quirk de contexto
  expirado del régimen legacy (testeado como testigo). El rollback fino preferente es
  POR-LEVER (`INTENT_LLM=off`, etc.). El stub existe para el instrumento MT y los
  contratos congelados, no como modo de operación.
- **El seam queda**: `execute_rag_turn`/`RagServingAdapters` INTACTOS en
  serving_pipeline.py — el release gate P1 los conduce directamente y atestigua el
  entrypoint POR STRING (fallaría tarde-y-distinto ante un rename: por eso la batería
  P1 es gate de esta PR y de cualquier futura que toque el seam).
- **Onda expansiva medida (68 tests → 0, cuatro clases previstas)**: (A) 34 fixtures
  forzaban el flag muerto; (B) ~25 tests de handler parcheaban el pipeline inline →
  parchean los módulos FUENTE (from_production importa perezoso) + fake-updates con
  update_id/chat; (C) 6 contratos del default viejo → re-contratados con AMBOS mundos
  assertados; (D) los tests de paridad legacy↔orquestador re-anclados a la paridad
  run_turn↔seam (r19 Fable: uno había quedado «hecho-pasar» con docstring del mundo
  muerto — re-contratado de verdad). Docs/comentarios del mundo muerto reconciliados
  (conversation_policy interfaz, config header, ARCHITECTURE runbook).
- **Pre-condición cumplida**: ORCHESTRATOR_PATH=on + CONVERSATION_POLICY=impl
  verificados en Railway (API, s317b) + e2e propio del ship (DEC-205b) + sin incidentes.
- **Vars de Railway ahora redundantes** (retirar = Alberto): ORCHESTRATOR_PATH (nadie
  la lee), CONVERSATION_POLICY=impl (coincide con el default).
- **Relacionado**: DEC-209/210 (PR-A/B) · propuesta r17 · doc
  `evals/s319_retirada_legacy_v1.md` · tally r19 ts=2026-08-12T17:33:31.

## DEC-212 (s320) — E1 del elefante EJECUTADO: doc_map +26 altas/+11 reconciliaciones con sonda PASS; 3 clases nuevas de integridad al packet; candidates 620/620 pre-clasificados

- **Fecha**: 12 ago 2026 (s320, autónomo adjudicado). **Impacto**: MEDIO-ALTO (catálogo
  gobernado = zona de dolor) — dúos r21 (Sol-only, Fable abortado por tamaño de subject,
  registrado) y r22 (dúo completo, seeds compactos), 0 FP entre ambos.
- **La cadena derivar→dúo→sondar ANTES de escribir cazó 3 clases reales**:
  (1) r21/r22: cruce por filename vs document_id (279 objetivo real, no 219) + pm
  compuesto fabricando candidatos falsos (split-parcial→B) + atestación circular +
  marca por substring → derivación v3 (A 46 · B 67 · C 162 · no-producto 4).
  (2) La sonda PRE del freeze-contract: 20/46 tier-A YA presentes = document_id STALE
  en doc_map (re-ingestas renovaron UUIDs sin actualizar el mapa).
  (3) El censo de reconciliación: **49 COLISIONES con el id viejo VIVO en documents =
  posibles documentos DUPLICADOS activos** (clase de integridad nueva, al packet).
- **ESCRITO (freeze-contract `evals/s320_e1_freeze_contract_v1.md`)**: 26 altas tier-A
  (triple coincidencia exact/alias + prefijo de marca + vendido_bajo) + 11
  reconciliaciones de id stale-muerto (entries adjudicadas INTACTAS) → doc_map 861→887
  vía `write_jsonl` (valida el conjunto: 0 errores) · sonda POST 46/46 presentes con
  **exactamente los 26 flips esperados** (veredicto PASS por igualdad de conjuntos) ·
  109 tests de catálogo + suite completa 3.833/46 verdes.
- **PACKETS a la sentada** (`evals/s320_e1_packet_adjudicacion_v1.md`): §1 49
  colisiones · §2 67 tier B con trazas · §3 133 candidates propuestos (draft FUERA del
  catálogo: `s320_e1_candidates_draft.jsonl`) + 29 bloqueados por colisión · §4 4
  revisión-humana de pm sucio. **E1b**: 620/620 candidates pre-clasificados con
  atestación contra CONTENIDO (confirmar 359 — coherente con el T1≈363 de DEC-093 —
  · retirar 0 · revisar 261; `s320_e1b_candidates_preclasificacion_v1.json`).
- **Gaps declarados**: el gate de escritura es de ALCANCE+no-regresión (identidad ⊥
  cuello, DEC-094); las colisiones pueden implicar cirugía de documents (supersede/
  borrado) = adjudicación; los 261 «revisar» de E1b llevan conteo pero no ranking
  fino; tier B/C no se escriben sin sentada.
- **Relacionado**: plan v2 (dúo r20) · DEC-074/084/091b/148-150 · tallies r21
  ts=2026-08-12T21:27:29 · r22 ts=2026-08-12T21:36:00.

## DEC-213 (s320d) — E2 del elefante: la DERIVACIÓN del snapshot del detector se GOBIERNA; el gate de equivalencia pagó tres veces en el build; el swap de DATOS queda adjudicable

- **Fecha**: 13 ago 2026 (s320d, autónomo). **Impacto**: MEDIO (apuesta ESTRUCTURAL
  declarada no-eval-driven — DEC-093/094: identidad ⊥ cuello; valor = una fuente para
  escala-30+). Dúo r23 PRE-build (Sol 4 · Fable 3, 0 FP, todo aplicado).
- **Qué hay**: `scripts/s320_e2_snapshot_derivado.py` — generador v2 del
  `model_catalog.json` DESDE el catálogo gobernado vía `_resolvable_terms()` (la puerta
  adjudicada del resolver, jamás una re-implementación) ∩ atestación ACTIVA (documento
  activo con chunks servibles; las 49 colisiones E1 excluidas) + cinturón anti-ruido +
  modo `--conservador` · `scripts/s320_e2_gates.py` — G1 detector sobre las 39 queries
  gold (STOP en pérdida REAL por normkey; forma aparte) + G2 voz EXHAUSTIVO (lista
  ordenada — Whisper trunca — + mapa mfr + prompt byte + known_manufacturers).
- **EL GATE PAGÓ 3 VECES EN EL BUILD** (para esto se pre-registró):
  (1) el derivado PLENO = 1.235 altas / 301 bajas — NO es equivalencia (el brazo A
  descartado colándose por el B); (2) el conservador v1 re-ordenaba FORMAS duplicadas
  del vivo (ID3000/ID-3000) y el detector cambiaba de forma servida; (3) el v2 tenía
  a `VESDA-E-VEP` como baja «real» — y una query GOLD lo necesita (los pm re-tagueados
  desde julio rompen la atestación exacta) → **CERO bajas automáticas**.
- **Resultado v1 (PASS TOTAL)**: candidato conservador CONDUCTA-IDÉNTICO (G1 0/0 ·
  G2 lista/prompt byte-iguales; la lista de modelos es la viva EXACTA) — el ship de E2
  v1 es el MECANISMO (generador gobernado + gates + recibos de diff); TODO cambio de
  datos viaja en el packet: §1 backlog de 1.235 altas del gobernado por lotes · §2 las
  23 bajas candidatas UNA A UNA (VESDA-E-VEP marcada ⚠️ GOLD) · §3 gaps del catálogo
  (feedback a E1). `build_model_catalog.py` (SQL suelto) queda para retiro cuando el
  swap se adjudique.
- **Gaps declarados**: el swap del fichero vivo NO se hace aquí (el candidato es
  byte-equivalente en conducta: hacerlo sería ceremonial hasta que haya altas
  adjudicadas); famtie/assessment-smoke del freeze quedan como gate del PRIMER swap
  con datos; la atestación exacta por normkey es estricta (VESDA lo probó) — la
  variante-de-familia va como mejora adjudicable, no automática.
- **Relacionado**: plan v2 elefante · DEC-093/094 · DEC-212 (E1) · tally r23
  ts=2026-08-13T21:56:44.

## DEC-214 (s321) — E3 F3a EJECUTADO: 579 chunks re-tagueados con identidad adjudicada (dúos r24+r25, findability PASS); residuo en packet con recomendaciones LLM fundamentadas

- **Fecha**: 14 ago 2026 (s321, nocturno autónomo mandatado). **Impacto**: ALTO
  (identidad servida de chunks) — dúos r24 (3 críticos) y r25 (crítico convergente
  atestación≠sujeto), TODO aplicado; 1 FP de Fable en 13 rondas (cita «pm JAMÁS
  auto» que SÍ existe — DEC-156b:3651, línea-kilométrica omitida por grep),
  documentado con mecanismo.
- **La cadena censo→dúo→atestación estrechó el lote con evidencia**: censo v1
  161 docs → v2 (consumable-gate + semántica imatch + contabilidad 887 asserted)
  104 docs/1.462 chunks, partición por provenance LEÍDA (102 adjudicados / 2
  derivados) · atestación r25 (sujeto-dominante + hermanas + producto-real→packet
  + fix del criterio circular snapshot) → **AUTO = 55 parejas / 579 chunks**.
- **APLICADO (recibo `s321_e3_writer_aplicar_20260813T222611Z.json`)**: 579/579
  por-chunk con CAS id+pm_prev (el bulk-por-pm dio 500 server-side: rollback
  verificado, migrado a fila-a-fila) · backup por-chunk versionado (rollback por
  id) · **findability_post PASS fail-closed** (los 55 docs recuperables por su
  canónico; pm-familia DEC-192/193 intactos por construcción) · **E2-POST: el
  conservador re-derivado = 0 altas/0 bajas** (diff pre-registrado = cero,
  explicado: ya estaban doc_map-atestados) · suite 3.833/46.
- **Residuo (packet `s321_e3_packet_adjudicacion_v1.md`)**: 47 parejas/878 chunks
  con pasada LLM mandatada por Alberto (claude-fable-5, contenido real, cita
  VERIFICADA contra muestra, alta-sin-cita degradada): §0 = 15 aplicables-en-
  bloque con su asentimiento · §1 = 32 una-a-una (28 producto-real→multi-valor,
  hermanas, no-dominantes; 11 NO_DECIDIBLE honestos; 1 MANTENER_PREV).
- **Incidencias de instrumento cazadas en la noche**: criterio producto-real
  CIRCULAR vía snapshot (el snapshot nació de estos pm) → solo catálogo
  gobernado · patrón imatch asimétrico por diseño → forma por normkey+signos ·
  `temperature` deprecada en modelos 2026 (clase DEC-092).
- **Relacionado**: DEC-212/213 · contrato §F3 · tallies r24
  ts=2026-08-13T23:49:46 · r25 ts=2026-08-14T00:12:43 · TECH_DEBT #76 (alta
  esta noche: categoría+atributos, mandato Alberto).

## DEC-215 (s321) — E4 EJECUTADO: el clarify-por-divergencia lee el CATÁLOGO gobernado; el seed FAMILY_REGISTRY retirado (dúo r26) — EL ELEFANTE (DEC-074/091b) QUEDA COMPLETO

- **Fecha**: 14 ago 2026 (s321 nocturno). **Impacto**: MEDIO (ruta E del clarify de
  la política F1) — dúo r26 (Sol 3 · Fable 4, 0 FP, TODO aplicado).
- **Qué hay**: campo `clarify` OPCIONAL y ADJUDICABLE en umbrellas
  (`{eje_terminos[], provenance}` — la puerta VETA declarar `variantes`: se DERIVAN
  de los canonical_model de los miembros, prefijo/sufijo común fuera → «1/2/5») ·
  migración de ZXe/ZXSe con provenance SEPARADA por componente (membresía s78/s90
  intacta · eje = GT s78-80 + seed s281, adjudicación formal del léxico PENDIENTE
  declarada) · consumo vía la instancia ÚNICA del proceso
  (`catalog_resolver.catalogo_cargado`, r26: sin segunda caché) · fail-open
  DECLARADO como divergencia con el seed (catálogo roto → sin clarify + warning) ·
  fallback hardcoded «1/2/5/10» RETIRADO (tercera copia) · `FAMILY_REGISTRY`/
  `_FamilySpec` eliminados.
- **Gates**: tests de TEXTO EXACTO del clarify pre/post (Sol M2: el gate MT solo
  assertaba no-vacío) + eje positivo/negativo + guard hp009/DEC-082 (divergent:true
  sin eje JAMÁS clarifica) + derivación de variantes + fail-open → 8/8 · suite
  completa 3.841/46 · catálogo validate 0 errores.
- **Añadir una familia nueva** = una fila de catálogo con provenance (antes: un PR
  de código). La costura para #76 queda puesta: `eje_terminos` es vocabulario de
  consulta; los atributos TIPADOS (categoría/tecnología/lazos) son #76.
- **EL ELEFANTE COMPLETO**: E0 censo (DEC-211-era) · E1 datos+packets (DEC-212) ·
  E2 derivación gobernada (DEC-213) · E3 re-tag 579 chunks (DEC-214) · E4 clarify
  gobernado (esta). El workstream DEC-074/091b de 4-7 sesiones se ejecutó en su
  RESTANTE real en ~3 (s320-s321); los residuos son PACKETS de datos adjudicables,
  no ingeniería.
- **Relacionado**: DEC-069 (la promesa del comentario) · DEC-074/082/084/091b ·
  tally r26 ts=2026-08-14T00:43:11.

## DEC-216 (s322) — #76 MECANISMO COMPLETO (dúo r27): clasificacion+atributos multi-valor en el catálogo, filtros tipados en el plan, inventario filtrado con honestidad — la población es la fase 2

- **Fecha**: 14 ago 2026 (s322). **Impacto**: MEDIO-ALTO (esquema del catálogo +
  ruta de inventario de fase A) — dúo r27 PRE-build (Sol 3 · Fable 4, 2 críticos,
  0 FP, TODO aplicado).
- **El caso que manda** (Alberto 13-ago): «¿Qué centrales de cuatro lazos
  analógicas de Detnov tienes?» → listaba TODO Detnov. Verificado en build: el
  intent YA disparaba (por eso listó) — el fix es la capa de filtro, no el disparo
  (gap del regex ensanchado {0,40}→{0,70} igualmente).
- **Esquema** (catalog_store, cerrado): `clasificacion {categoria∈enum13, cita,
  provenance}` + `atributos {tecnologia|lazos|protocolo}` **MULTI-VALOR POR-FUENTE**
  (r27 Sol C1 — AFP1010: 2 lazos en docs España y 4 en US; cada valor lleva SU doc
  y SU cita; divergencia se adjudica, jamás se fusiona). El campo legacy `categoria`
  (19 filas de texto libre del seed s91) se TOLERA como pista-semilla — la capa
  tipada es `clasificacion` (colisión cazada por la propia puerta en el build).
- **Plan**: `filtros_inventario()` puro y $0 (léxico cerrado es/en: categoría +
  tecnología + N-lazos con numerales); viaja TIPADO en `datos["filtros"]` (r27 Sol
  M2: sin contrato en el plan, la caché por-marca se contaminaría). El caso dorado
  parsea `{central, analogica, 4}` — test pineado.
- **Consumo**: `_inventario_filtrado` desde **catálogo ∩ doc_map** (r27 Fable C1:
  los pm de chunks son strings de FAMILIA por diseño T3 — el join es EL aparato,
  no una extensión trivial); caché COMPUESTA (marca|filtros); honestidad
  estructural: «N sin clasificar» siempre visible, ninguno-casa lo dice, catálogo
  caído degrada a lista completa CON aviso — jamás lista falsa ni omisión muda.
  La ruta SIN filtro no toca el catálogo (test: byte-igual, caché y truncado).
- **Gates pasados**: puerta 29/29 · #76 9/9 · instrumentos s316e+transporte
  re-contratados (2 fakes mordieron por forma — su trabajo) · suite 3.850/46.
- **FASE 2 (población, pendiente en esta rama)**: mini-GT 30 a mano → pasada
  fable-5 con cita verificada por doc_map → gate precisión ≥95% → packet §0
  en-bloque (r27 Fable M3: NADA se escribe sin el sí de Alberto — el precedente
  candidate-birth manda). Hasta poblar, el bot responde el inventario completo
  con el aviso honesto (conducta estrictamente mejor que la de hoy).
- **FASE 2 EJECUTADA (mismo dia)**: diana 160 (Detnov 28 + Kidde 132) · mini-GT 30
  a mano ANTES de la pasada · poblacion fable-5 con cita POR CAMPO verificada ·
  **gate 19/19 = 100% PASS** — con historia: el unico FAIL original (18/19) era
  ERROR DEL GT del autor (2X-AT-F2-FB: etiquete {2,2} desde la portada; el modelo
  encontro la cita verbatim «2 lazos ampliables a 4» = la clase AFP1010 exacta del
  multi-valor de r27) → corregido DOCUMENTADO con el recibo FAIL preservado
  (s322_76_gate_gt_v1_FAIL_original.json), jamas tuneado. Packet: §0 114
  en-bloque + §1 46 una-a-una + nota enum-semantica (analogica≈direccionable).
  NADA escrito al catalogo sin el si de Alberto.
- **Relacionado**: TECH_DEBT #76 · DEC-215 (la costura E4) · tally r27
  ts=2026-08-14T09:10:15.

## DEC-217 (s322b) — #76 CERRADO para Detnov+Kidde (dúo r28): §0 escrito y re-verificado full-text, semántica de capacidad «hasta N», clave `zonas`, ampliación modular anclada, inventario genérico AGRUPADO

- **Fecha**: 14 ago 2026 (s322b, post-merge de PR #252). **Impacto**: MEDIO-ALTO
  (esquema + datos servidos + conducta de la ruta de inventario) — dúo r28
  POST-build/PRE-commit (Sol 7/7 · Fable 5/5 confirmados, 0 FP, 2 críticos;
  TODO aplicado en el mismo diff; tally ts=2026-08-14T18:51:45).
- **Adjudicaciones de Alberto (14-ago, en vivo)** que fijan conducta:
  1. **Capacidad**: «en el caso de 8 lazos, siempre es *hasta* 8» → filtro
     `n ≤ max`, display «hasta X lazos»; una central de 8 SALE para 4.
  2. **Inventario genérico categorizado**: agrupado por tipología en orden
     canónico + orden por `familia` gobernada (fallback modelo), generalizable
     (vive en el render de la ruta, no en un phrasing). RE-CONTRATA el gate
     byte-igual del r27 (se conserva: sin clasificación → lista plana intacta).
  3. **Regla de dominio**: toda central lleva su dato de capacidad; en
     CONVENCIONALES son **zonas** → clave hermana `zonas` (misma forma y
     semántica; conceptos JAMÁS fusionados; «zonas de extinción» excluido).
  4. **CAD-171/201 con lazos** + **CAD-250 ampliable a 32 por módulos** (sin
     inventar un modelo -32): anclados verbatim (MI-716 «2 lazos»; MC-380
     «2 lazos ampliable a 8»; «soporta hasta 32 lazos en un único NODO»).
- **Datos escritos** (writers idempotentes con recibo, reversibles): 138
  clasificados Detnov+Kidde (§0 126 + rescate 12 §0 saltadas por atribución
  corta del writer — re-atribución contra doc COMPLETO, 0 relajaciones);
  lazos VESTA ×5; zonas NC-PF ×6; auditoría regla-de-dominio 36/36 centrales.
- **Hallazgos r28 aplicados**: `base` OPCIONAL (6 suelos inventados retirados
  — un base=1 no declarado por el doc era un hecho falso); re-verificación
  FULL-TEXT de las 296 citas (Sol S4 MATERIALIZADO: 1 tecnología inventada en
  cola parafraseada, cazada y retirada; método corregido a cita completa);
  inaplicable ≠ faltante (convencional excluida del filtro de lazos, no
  «sin dato»); orden natural; cota por construcción también en encabezados.
- **Alcance declarado (S6)**: la ruta de inventario es DETERMINISTA — se mide
  por contrato de tests + smoke con recibo, no por juez; ningún lever medido
  se reclama zanjado con esto.
- **Deuda nueva**: TECH_DEBT **#76b** (divergencia multi-mercado LATENTE:
  gate de población debe flagear divergencia de max → packet, y entrada con
  `alcance` adjudicable, ANTES de poblar Notifier/clase-AFP1010).
- **Alternativas descartadas**: zonas-como-lazos (falsea conceptos); agrupado
  desde pm de DB (los pm son familias T3); colapso de familias con nombre
  heurístico (taxonomía no gobernada — si se quiere, es dato de catálogo).
- **Relacionado**: DEC-216 · TECH_DEBT #76/#76b · propuesta+adenda
  `evals/s322_76_propuesta_r28_v1.md` · recibos `s322_76_{lazos_vesta,
  zonas_ncpf,writer_rescate,migra_base_opcional,verifica_citas,fix_rmsdk}_*`.

**Actualización DEC-217 (mismo día, pregunta de Alberto «¿reviso online los no-alta?»)**:
la respuesta correcta resultó ser corpus-first — el censo de las 22 §1 mostró 1-12
menciones del modelo en SUS docs (fallo de MUESTREO: la fila de la tabla de modelos
2X-A no caía en la ventana), no ausencia de corpus. **Repesca v3 dirigida a
tabla-de-modelos: 22/22 → §0 con cita verbatim verificada FULL-TEXT** (incluido
tbud-ng «Placa expansión de lazos» y las 3 2X-AT-FR de 1 mención) + censo-extra
firebeam 2/2 (kits vendido_bajo Detnov, fuera del censo v1 por prefijo de marca).
**Detnov+Kidde = clasificación 100 % (162 productos), gate 29/29 PASS, 348 citas
re-verificadas full-text, 0 fallos, §1 = ∅.** El carril «evidencia online» queda
diseñado para censos futuros donde el corpus NO ancle: URL+quote+fecha al packet
como tier DECLARADO (nunca al catálogo sin adjudicación); no hizo falta usarlo.

## DEC-218 (s321) — Guarda VIVA vs REGISTRO HISTÓRICO: cuándo se re-ancla un prereg y con qué acotación

**Decisión**: los preregs de los canarios `s203/s204/s205` son **guardas VIVAS (tripwires)** sobre el
ledger de golds, y **se re-anclan** cuando Alberto adjudica un gold — con una acotación OBLIGATORIA.
Los artefactos de `s277` (contrato sellado, prereg de release, manifest histórico) **NO se tocan**.

**El criterio, escrito una vez para no re-litigarlo** (lo pidió Fable; hasta hoy solo vivía en prosa
de mensajes de commit):
- **Registro histórico** = el acta de contra qué corrió una ejecución pasada. Vive en **git y en el
  manifest**, no en el prereg. **Intocable.**
- **Guarda viva** = el pin que dice «esta entrada no se ha movido desde que la aprobé». Su valor NO es
  autenticar: es **forzar ceremonia visible** ante cualquier cambio del ruler. Se re-ancla
  deliberadamente, con la causa escrita en el propio fichero.
- ⚠️ El `status: FROZEN_BEFORE_FRONTIER_EXECUTION` de esos preregs **induce a error**: sus
  `frozen_inputs` ya mutaron en s286, s287 y ahora s321. Se conserva el literal porque tres runners
  lo assertan; el matiz queda anotado en cabecera. **Renombrarlo es deuda pendiente**, no urgente.

**Acotación OBLIGATORIA antes de re-anclar** (convergencia del dúo; sin esto el re-anclaje bendice
CUALQUIER deriva acumulada, no solo la adjudicada): localizar el commit cuyo fichero casa con el sha
pinneado y **diffear contra él**, verificando que solo contiene lo adjudicado. Ejecutado en s321:
pin `79701140…` → commit `972e96b` (s287); diff = 14 líneas, todas en `hp001`, cero qids
añadidos/quitados. **«Lo explico en el commit» NO es mitigación** (Sol, medio).

**Motivo + alternativas descartadas**: el dúo DIVERGIÓ de frente. **Sol (2 críticos)**: re-anclar
falsifica la declaración `FROZEN_BEFORE_...`; el arreglo estructural es resolver el ledger desde un
**blob sellado** (`git cat-file`), patrón que YA existe en `tests/test_s277_c1_p1_contract.py:29-56`
con su razón escrita («hashear el árbol vivo reportaría el desarrollo como manipulación»; DEC-147:
versionar, no relajar). **Fable**: pinnear el fichero vivo NO es defecto — es un tripwire, no un
autenticador, y un snapshot lo silenciaría **para siempre**; que 4 tests se pongan rojos ante una
adjudicación es la guarda funcionando. **Adjudicado a favor de Fable** por un hecho que él mismo
aporta y que reconcilia a los dos: el prereg **ya no registra** lo que la ejecución consumió — eso
vive en git/manifest — luego re-anclar **no destruye evidencia**. La propuesta de Sol queda
**registrada como candidata**, no descartada: si algún día se quiere una guarda que distinga
«legítimo» de «manipulación» (y no solo *que* cambió), el blob sellado es el camino.

**Lo que NO se hizo, y por qué** (Sol, crítico 1, CONFIRMADO en ejecución): regenerar
`s277_c1_p1_fact_contract_v1.json` por su builder **satisface un test y rompe otro** —
`test_contract_rebuilds_byte_semantically_from_frozen_authorities` exige rebuild==stored, y el
preflight del runner exige que el hash case con el pin sellado del prereg. No pueden cumplirse a la
vez cuando una entrada legítima cambia. Se **restauraron** los tres artefactos de s277 y se dejó el
test de rebuild en rojo, documentado como **TECH_DEBT #77**: es un defecto de sobre-pinneo
preexistente que esta adjudicación solo destapó, y cascar re-anclajes dentro de una puerta de
release no es algo que se haga de madrugada sin decisión propia.

**Coste declarado para la sentada B2**: cada tanda de marcas exige re-anclar los 3 canarios, con su
diff acotado, y **marcas + re-anclaje deben ir en UN commit** — si van separados, la suite queda roja
en cada frontera intermedia, se normaliza el rojo y una deriva ajena que entre en esa ventana queda
enmascarada (Fable, medio).

**AMPLIACIÓN (mismo día, tras el rojo de CI en la PR #255)**: el criterio vale TAMBIÉN para
`s277`, y ahí **Sol se equivocaba en su crítico 1**. Sostenía que regenerar el contrato
«contradice la identidad inmutable de la P1 histórica» porque el manifest fija `3ac742…` mientras
el prereg declara otro hash. Los diffs dicen lo contrario: el manifest **conserva el original a
propósito** —es el acta— y el prereg **avanza con cada adjudicación** (`3ac742` s286 → `844237b4`
s287 → `a4d29396` → `da79055e` s321). No es deriva: es exactamente la distinción viva/histórico de
esta DEC, aplicada a otro artefacto. **Mi error derivado**: al ver que regenerar rompía el
preflight, REVERTÍ y declaré «dos guardas incompatibles». Lo correcto era completar la cascada —
el builder no propaga los pins a `prereg_v2/v3` ni al scorer, y hay que copiarlos a mano
(TECH_DEBT #77). Ejecutada entera: 4/4 ficheros de test en verde, manifest intacto.

Recibos: `evals/s321_reanclaje_propuesta_v1.md` · dúo ts=2026-08-14T17:54:01 (Sol xhigh + Fable 5).

**Actualización DEC-217 #2 (14-ago tarde, pregunta de Alberto sobre el packet E3)**:
mismo patrón aplicado al residuo E3 — de las 32 filas §1 del packet v1, 12 eran
`parse-fail` del MISMO bug max_tokens=400 y ~17 eran altas castigadas solo por
hermanas. **Repesca v2** (800 tokens, muestreo doc-entero+canónico, verificación
full-text, `hermanas_sujeto` con cita = criterio de máquina): 26 RETAG alta+cita✓,
2 MANTENER alta, 1 MULTI_VALOR alta con lista. **Packet v2 SUPERSEDE al v1: §0 23 +
§0-bis 20 (hermanas resueltas con cita) + §1 4** — la sentada E3 pasa de 32
decisiones a 2 síes en bloque + 4 filas. **Primer uso del carril EVIDENCIA ONLINE**
(3 filas irreducibles): ZXR50A confirmado real (naming ES del ZXr-A UK; manual
MIE-MI-440 en morley-ias.es → candidato a gap de corpus), MPS-24AE confirmado real
(fuente 220 VAC, DN-0786), y «FD2705-10R» detectado como PROBABLE ARTEFACTO de
nombre de fichero (la familia real es FD2705R/FD2710R) — recomendación MULTI_VALOR.
URL+quote+fecha en el packet; nada escrito sin adjudicación. Recibos:
`s321_e3_llm_recomendaciones_v2.json` (v1 intacto) · `s322_e3_online_evidencia_v1.json`.

**Actualización DEC-217 #3 (14-ago noche — adjudicación E3 de Alberto APLICADA, s322d)**:
«sí al §0 y §0-bis» + §1 de su mensaje → **44 retags · 674 chunks · 0 aborts ·
findability OK** con la mecánica T3 (backup por-chunk + CAS + gate redirect-aware;
recibos `s322_e3_writer_packet_aplicar_20260814T193541Z*`; 3 MANTENER no-op; un
segundo --aplicar accidental fue no-op limpio por CAS — recibo conservado).
Adjudicaciones de dominio de Alberto incorporadas: **FD2705-10R = artefacto** (la
realidad son FD2705R+FD2710R, ambos detectores lineales IR; doc_map de la guía
22318 → ambos productos, artefacto `aritech:fd2705-10r` → estado retirado, chunks
de guía+addendum → multi «FD2705R/FD2710R»); **ART 535-x → multi ART 535-10/-30**;
**ECN-96-200 → MPS-24AE** (nota suya: tipología = fuentes de alimentación, 15888SP
— para la futura población #76 Notifier). **Corrección al carril online**: el gap
que propuse de MIE-MI-440 era FALSO — el manual YA está ingestado (content hits en
MIE-MI-440 y MIE-MI-431rv2); la clase de fallo: afirmé «candidato a gap» sin
consultar el corpus (bias #51: nunca de memoria). **Queda SOLO ZXrA**: recomendación
retag-a-ZXR50A en vez de borrar el doc (FAQ es-ES con el único paso-a-paso del
repetidor en DXc Connexion; el catálogo ya tiene morley:zxr50a y el doc_map ya
apunta ahí) — decisión de Alberto pendiente.

**Actualización DEC-217 #4 (14-ago noche — split ZXr adjudicado, s322e; E3 COMPLETO)**:
Alberto, con el MIE-MI-440 en la mano: «ZXR50A/P son los repetidores de la central
ZX50, mientras que los ZXrA/P lo son de [DXc/DX/ZXe/ZXSe], así que son productos
diferentes». REVOCA el colapso del GT s78 (aliases «variante-tipografica»
ZXr-A→zxr50a): nacen `morley:zxr-a`/`morley:zxr-p`; MIE-MI-431rv2 (el manual
ZXr-A/ZXr-P) remapeado y sus 18 chunks retagueados «ZXR50A/ZXR50P»→«ZXr-A/ZXr-P»;
la FAQ de puesta en marcha retagueada y CONSERVADA (adjudicación: no borrar);
2 aliases retirados; MIE-MI-440 y sus pms intactos. La puerta del catálogo CAZÓ la
colisión alias-vs-canonical en el primer intento (write_jsonl escribe-y-valida:
entre runs quedó inválido transitorio en disco — la puerta funcionó; recibo
anotado). validate() OK · tests catálogo/inventario 47/47. **Con esto el packet E3
queda COMPLETO: 0 filas pendientes.** Recibo `s322_e3_zxra_split_v1.json`.

## DEC-219 (s322f) — LLM_MAX_TOKENS: se RATIFICA el 8000 de producción con recibo y medición; y las 9 vars de Railway redundantes, RETIRADAS por Alberto

- **Fecha**: 15 ago 2026 (s322f). **Impacto**: MEDIO (default del serving +
  configuración viva de producción). Cierra las DOS adjudicaciones que DEC-210/211
  dejaron abiertas para Alberto.
- **La discrepancia que se cierra**: el gate de pre-verificación de la graduación
  (DEC-210) cazó `LLM_MAX_TOKENS` = 8000 en Railway SIN recibo en DECISIONS, contra
  el 3500 RECIBIDO (DEC-092b: «0 truncado con 3500», validado ACOPLADO a
  RERANK_TOP_K=10). Llevaba desde s319 esperando la palabra de Alberto.
- **MEDICIÓN antes de opinar** (s322f, 96 respuestas reales de `query_logs`,
  abr→ago-2026): mediana **1.671 chars** (~450 tok) · p90 4.449 · **máxima 10.927**
  (~2.950 tok) · **0 respuestas superaron los ~13.000 chars** (≈3500 tok). Es decir:
  **el techo NUNCA se ha rozado**, y 3500 y 8000 son hoy conductualmente idénticos.
  11 de 96 respuestas pasan de 4.096 chars (se parten en varios mensajes Telegram).
- **Adjudicación de Alberto**: «max_tokens: lo dejamos en 8000». **Ratificado**, y la
  divergencia queda DELIBERADA y escrita: código **3500** = valor SELLADO (el release
  profile P1 lo congela junto al top-10) ⇒ eval/CI reproducibles; Railway **8000** =
  HOLGURA de producción. `max_tokens` es un TECHO, no un objetivo (solo se factura lo
  generado): no cuesta, y evita cortar una respuesta a media frase. Cero cambios de
  conducta hoy. Alternativa descartada: bajar producción a 3500 (o quitar la var) —
  hoy sería un no-op y solo restaría holgura.
- **Gap declarado de entrada → TECH_DEBT #78**: `stop_reason` se calcula en el
  generador pero NO se persiste en la traza (verificado: 0 hits en 96 trazas). La
  métrica que gobierna este techo solo se puede leer hoy por proxy (`response_length`).
- **Vars de Railway redundantes: RETIRADAS por Alberto** (las 9 que DEC-210/211
  dejaron listadas): GENERATOR_PROMPT_VARIANT, RERANK_TOP_K, ENUNCIADOS_MULTIVECTOR,
  HYQ_TABLE, GENERATOR_FOLLOWUPS, ANTI_DIAGRAM_INVENTION, WIRING_TOPOLOGY_GUARD,
  CONVERSATION_POLICY, ORCHESTRATOR_PATH. **Verificado por API** (patrón DEC-195, no
  de memoria): 49 → 40 vars, las 9 ausentes, el resto intacto (INTENT_LLM=on,
  GENERATOR_SELECTION_BLOCK=on, GENERATOR_DIRECT_FIRST=on,
  VISUAL_ASSETS_LISTING_GATE=on, CHUNKS_TABLE=chunks_v2, LLM_MODEL=claude-opus-5,
  EC_LEGAL_DISCLAIMER_SKIP=on) y **último deployment SUCCESS**. Conducta idéntica
  por construcción: cada valor retirado COINCIDÍA con el default graduado.
  (Nota de proceso: el primer intento dejó `ORCHESTRATOR_PATH` puesta — cazado por la
  verificación, no por confianza; se comprobó además que NO era variable compartida
  de entorno. Alberto la borró y redesplegó.)
- **El rollback NO cambia**: sigue siendo poner la env var explícita (DEC-210), y
  para el orquestador sigue vigente lo de DEC-211 — `CONVERSATION_POLICY=stub` es
  ÚLTIMO RECURSO con degradaciones declaradas, no un modo de operación.
- **Relacionado**: DEC-092b · DEC-210/211 (que quedan CERRADAS) · TECH_DEBT #78 ·
  censo vivo `evals/s322_railway_censo_v1.json`.

## DEC-220 (s323) — «Dónde corre Claude»: las TRES superficies montadas, con un environment único y red Full (adjudicación de Alberto) y un verificador con recibo

- **Fecha**: 15 ago 2026 (s323). **Impacto**: MEDIO — toca el arranque de TODA
  sesión cloud y la superficie de secretos. No toca corpus, retrieval ni esquema.
- **El problema real, no el de comodidad**: el environment cloud estaba en
  **Default** (sin variables, red *Trusted*), y eso produjo en s315/s316 dos fallos
  SILENCIOSOS: casmarglobal bloqueado por la política de red, y `OPENAI_API_KEY`
  ausente ⇒ **el revisor Sol no era ejecutable y el dúo del Protocolo 3 quedó cojo**.
  Es decir: una sesión cloud no podía cerrar nada de impacto ALTO, y nada avisaba.
- **Las tres superficies** (el selector «dónde corre Claude» es el icono de nube
  encima del cuadro de mensaje; no hay página de ajustes): **Cloud** (VM de
  Anthropic; sigue con el PC apagado; NO tiene OneDrive) · **Remote Control** (la
  sesión corre en el PC de Alberto y se dirige desde el móvil) · **Dispatch**
  (mensajear una tarea a la app de escritorio). Hallazgo de rumbo: **Remote Control
  cierra el gap que `ENTORNO_CLOUD.md §3` declaraba como "lo que el cloud NUNCA
  tendrá"** — la ingesta y la fase de enunciados ya son gobernables desde el móvil,
  solo que ejecutándose en local. Montar únicamente cloud habría dejado fuera media
  clase de trabajo.
- **Adjudicación de Alberto** (mis dos recomendaciones fueron las contrarias y
  quedan descartadas por decisión suya, no por análisis): **un solo environment con
  todas las keys** (descartado: partirlo en `código` sin service key / `datos` con
  ella) y **red Full** (descartado: *Custom* con allowlist mínima + defaults).
  Motivo declarado: que ninguna sesión se quede a medias por una política de red.
- **Riesgo ACEPTADO y escrito**: los environments **no tienen secret store** — la
  doc oficial desaconseja meter credenciales porque son legibles por cualquiera que
  use el environment. Con red *Full* y la `SUPABASE_SERVICE_KEY` dentro, una sesión
  que lea un portal o un PDF hostil tiene medio y destino para exfiltrar. Mitigación
  operativa: environment **personal** (nunca compartido) + **rotar keys** ante
  sospecha. Partirlo en dos son 2 minutos en el mismo selector cuando se quiera.
- **Cableado**: (a) **`scripts/cloud_smoke.py`** + `tests/test_cloud_smoke.py` —
  verificador del entorno con recibo (`evals/s323_cloud_smoke_v1.json`); es el
  instrumento del Protocolo 1 aquí, porque «el cloud funciona» sin recibo es
  exactamente lo que costó s315. (b) **hook `session-start.sh` IDEMPOTENTE** — corría
  en cada arranque Y en cada `resume` reinstalando todo; ahora el centinela es la
  huella sha1 de los requirements + un import real. (c) `matcher: "startup|resume"`
  en `.claude/settings.json`, alineado con el ejemplo oficial. (d)
  `docs/ENTORNO_CLOUD.md` reescrito: la versión s315c mandaba a un menú
  «Environments» que ya no se llama así.
- **Dúo (Protocolo 3, tier MEDIO = Fable standalone)**: veredicto **NO SÓLIDO**, tres
  hallazgos, **los tres verificados contra el código y aplicados**: (1) el contrato de
  no-fuga solo cubría `--sin-red`, dejando sin test el vector real — mensajes de error
  de httpx (llevan la URL, y `SUPABASE_URL` es secreto) y `r.text` de un 4xx ⇒ nace un
  **saneador único** por el que pasa TODO detalle, con dos tests de transporte
  simulado; (2) `git remote get-url origin` iba verbatim a un recibo que se commitea, y
  en un clon cloud lleva `x-access-token:<token>@` ⇒ se publica sin userinfo, con test;
  (3) **el mejor**: el sondeo de idempotencia del hook no incluía `cryptography` —
  justo el módulo cuyo PanicException-al-importar motivó el hook en s315 — ni
  `openai`/`voyageai`, así que marca presente + 5 imports OK + cryptography rota
  habría dado por buena una VM rota; el centinela y la lista de críticos del smoke
  eran incoherentes entre sí. Descartado su hallazgo menor (`matcher` excluye `clear`):
  el `CLAUDE_ENV_FILE` es acumulativo y el proceso no muere en un `/clear`.
  Ref: `evals/adversarial_reviews/2026-08-15T13-13-06_claude-fable-5_responses_f5885479d75e.json`
  · `evals/adversarial_review_log.jsonl` (ts 2026-08-15T13:13:07) ·
  propuesta `evals/s323_entorno_cloud_propuesta.md`.
- **Gap declarado de entrada → TECH_DEBT #82**: el revisor adversarial es **CIEGO a
  `.claude/`** (`adversarial_review.py:237`, `SKIP_DIRS`) — herencia de cuando ese
  directorio estaba entero ignorado, mientras que desde DEC-193 hay whitelist y los
  hooks SÍ están versionados. Por eso el hallazgo (3) tuvo que marcarse CONCEPTUAL:
  acertó razonando sobre mi propia descripción, que es la dependencia que el
  Protocolo 3 existe para romper.
- **Lo que NO está declarado hecho**: el **smoke de recepción en cloud**. Sin
  `VEREDICTO: LISTO` + suite verde EN una sesión cloud del environment nuevo, esto es
  aparato preparado, no entorno verificado (Protocolo 1). Lo ejecuta Alberto tras
  crear el environment; el recibo se commitea.
- **Relacionado**: DEC-193/195 (versionado de `.claude/`, hook del digest) · DEC-209
  (runbook de backup, que sigue siendo LOCAL) · TECH_DEBT #82 ·
  `docs/ENTORNO_CLOUD.md`.

### DEC-220 addendum (s325, 18 ago 2026) — el ALCANCE se acota a Cloud + Dispatch, y la DB queda resuelta sin tocar Supabase

- **Alberto acota el alcance**: se adoptan **Cloud + Dispatch**; **Remote Control NO**
  (documentado, sin activar). El doc ya no afirma «las tres superficies montadas».
- **Por qué no deja hueco**: las sesiones que abre **Dispatch corren en el PC** (pestaña
  *Cowork* de la app de escritorio, badge *Dispatch* en la barra lateral de Code), así que
  **ven OneDrive y el `.env`** — el gap que Remote Control iba a cubrir queda cubierto
  igual, cambiando el modo: se le encarga y avisa por push, en vez de conducir el turno.
  Matiz de la doc oficial: en sesiones de Dispatch las aprobaciones de apps caducan a los
  30 min. Requiere Pro/Max (no existe en Team/Enterprise).
- **Supabase: NADA que configurar del lado de Supabase para DATOS.** Los scripts van por
  REST con `SUPABASE_SERVICE_KEY` (`service_role`, se salta RLS) — misma ruta que local y
  que el bot en Railway; verificado con `GET /rest/v1/documents` → 200.
- **Para DDL/migraciones, dos vías**: (a) `DATABASE_URL` + psycopg2 — y aquí el dato que
  lo desbloquea: **el DSN del repo apunta al POOLER**
  (`aws-1-eu-north-1.pooler.supabase.com:5432`), que resuelve por **IPv4**, así que
  funciona desde un VM sin IPv6 (la directa `db.<ref>.supabase.co` no lo garantiza);
  (b) el conector MCP de Supabase habilitado en la sesión cloud, cuyo tráfico va por
  Anthropic y no depende de la allowlist (es la vía de DEC-140 / migración 007).
  `cloud_smoke.py` gana el check `red:postgres`, no crítico: dice si ESA sesión puede
  aplicar migraciones.
- **Lo único que rompería una sesión cloud**: las *Network Restrictions* de Supabase
  (allowlist de IPs) — las sesiones salen desde IPs de Anthropic, que no son fijas. Hoy
  desactivadas por defecto; el `service_role` no las esquiva.
- **Fuga cerrada de paso**: el saneador del smoke redacta ahora también la **password
  embebida en el DSN**, porque un error de psycopg2 puede citar trozos del DSN sin citarlo
  entero (y entonces el reemplazo por valor completo no engancharía).

### DEC-220 addendum 2 (s325d, 18-ago 21:52 UTC) — el environment queda VERIFICADO, con recibo

Lo que faltaba para que esto dejara de ser aparato preparado. Recibo:
`evals/s323_cloud_smoke_v1.json` (PR #291), generado EN una sesión cloud del
environment `technical-bot`:

- `cloud_smoke.py` → **VEREDICTO: LISTO**, 0 críticos · `pytest -q` → **4447 passed,
  45 skipped, 2 xfailed** (9m20s, en el contenedor) · `check_deps.py` → OK.
- `red:extraction_store` → **OK, 1.143 extracciones leídas del bucket**: DEC-221
  funciona desde la nube, no solo en el banco de pruebas local.
- `key:ANTHROPIC_API_KEY` → **OK (108 chars)**, reconstruida por el hook desde
  `ANTHROPIC_API_KEY_SCRIPTS` (`session-start: ANTHROPIC_API_KEY derivada de …` en el
  log). **Confirmado por Alberto**: pegó `ANTHROPIC_API_KEY` en el environment y la
  sesión NO la vio ⇒ la plataforma la filtra, no fue un descuido.
- Único FALLO: `red:postgres`, no crítico y esperado (sin TCP al 5432).

**Arranque medido por mtimes reales, no estimado**: boot 21:50:33 → clon 21:50:58
(25 s) → `unshallow` 21:51:08 (10 s) → fin de instalación 21:52:08 (**60 s**).
**Total ~95 s**, y el hook INSTALÓ (la marca del centinela vive en `/tmp` y la VM era
nueva). **Decisión mantenida**: la instalación se queda en el hook versionado; 60 s
por contenedor nuevo no justifican duplicar la lógica en un setup script fuera del
repo. Si algún día molesta, el movimiento está descrito y el dato es este.

> **→ SUPERADO por DEC-238 (s325g, 19-ago, PR #295).** Ese «algún día» fue el mismo día:
> Alberto adjudicó mover la instalación al setup script, y la objeción de arriba (duplicar
> lógica fuera del repo) se resolvió por EXTRACCIÓN — la lógica vive en
> `.claude/hooks/install-deps.sh`, versionada, y el campo del environment solo la invoca.
> El párrafo se conserva como traza del razonamiento vigente entonces, no como decisión viva.

**Estado: DEC-220 VERIFICADA.** El primer recibo (NO LISTO, PR #289) queda como traza
de lo que faltaba; este es el de aceptación.

## DEC-221 (s321) — Cuando dos pasajes del MISMO manual dicen lo mismo, el gold se ancla en el que da el MECANISMO; y la inconsistencia de la fuente se DECLARA, no se elige

**Decisión.** Criterio de autoría, recurrente, que nace de un caso real (`hp017#2`, ítem 3 de la
sentada B2) y de una propuesta de Alberto:

1. **Anclaje**: entre dos pasajes del mismo manual que sostienen el mismo hecho, el gold se ancla
   en el que **da el mecanismo** —el *por qué*, la consecuencia de no hacerlo— y no en el que solo
   da la instrucción.
2. **Declaración**: si los pasajes difieren en alcance o precisión, el gold **lo hace visible**
   (ambos en `citations`, con la jerarquía explícita). No se elige uno y se borra el otro.

**El caso.** PEARL, `997-671-005-3_Configuration_ES`, Apéndice 5:
- **A5.2** (física p43): «**Es fundamental** borrar la regla 1 si se va a realizar una programación
  específica, **ya que, si no, esta será anulada**» — singulariza la regla crítica **y explica el
  efecto**. Va en un recuadro de aviso, con icono y subrayado.
- **A5.4** (física p45): «las **dos reglas** por defecto… **Deben eliminarse** si se van a crear
  reglas personalizadas» — sin mecanismo. **[CORREGIDO s321, cazado por Alberto]**: A5.4 es la
  sección «**Ejemplos** de reglas de causa-efecto» y esa frase es un paso del **Ejemplo 1**
  («*¿Cómo crear una regla para permitir una **evacuación por etapas**…?*»), NO una instrucción
  general del apéndice. Al llamarla «instrucción de limpieza» esta DEC —y Sol en dos rondas de
  dúo— leímos un ejemplo como norma. La diferencia real entre A5.2 y A5.4 es de **alcance**:
  advertencia general (una regla) vs. paso de un caso concreto que programa la propia evacuación
  (dos reglas). Y ese caso es justo el que la lectura de Alberto anticipaba: la Regla 2 (tecla
  EVACUACIÓN) solo se cruza con la programación cuando lo que se programa es la evacuación.

No se contradicen: son compatibles y de distinto propósito. Medido: con el chunk de A5.2 delante
el bot transmite el hecho **3/3 a 5/5**; con el de A5.4, **0/3**
(`evals/s293_reachability_hp017_hp017_2.json` · `evals/s321_control79_p45_solo_v1.json`).

**La alternativa que se probó y se DESCARTÓ con medición** (propuesta de Alberto, y la idea era
buena): anclar en el pasaje con más **empaque tipográfico** —el del recuadro amarillo con icono—.
Se comprobó si esa señal sobrevive a la extracción y **no sirve como regla**: el marcador `<ins>`
(subrayado) aparece en **1.412 de 26.215 chunks (5,4%)** y una muestra dice que envuelve
mayoritariamente **títulos de sección** («APÉNDICE A…», «1 CARACTERÍSTICAS TÉCNICAS», «Menú
zonas»), no avisos. Usarlo como «esto es crítico» sería una máquina de falsos positivos. Y lo que
de verdad da el empaque —**la caja con el icono**— la extracción lo pierde (TECH_DEBT #83).

**Por qué el criterio elegido es BP + estructural + escalable.** Vive en el **texto plano**, así
que no depende de cómo maquete cada fabricante y escala a 30+ sin tocar la ingesta. Es
**pedagógicamente correcto**: lo que convierte una instrucción en algo que un técnico entiende en
obra es el porqué. Y **no es circular** — se decide contra la FUENTE, no contra cómo respondió el
modelo ni contra el scorer, que es exactamente donde el dúo cazó tres recomendaciones mías en esta
misma sesión.

**Gaps declarados.** (a) El criterio NO resuelve el alcance PCI: dice dónde anclar, no qué debe
contratar la pregunta — eso sigue siendo adjudicación de Alberto. (b) «Dar el mecanismo» no está
formalizado como predicado automático; hoy es criterio de autoría humana, y formalizarlo sin
medirlo sería el mismo error que esta sesión ha corregido tres veces. (c) La medición del 5,4% es
sobre `chunks_v2` a 15-ago-2026; si cambia el extractor, hay que rehacerla.

**Métrica.** Objetivo: per-fact `conveyed` K=5. La medición citada (3/3 vs 0/3) es de esa misma
métrica ⇒ coincide. No toca ningún «settled» de PASS ni de retrieval-miss.

## DEC-222 (s322i–s323) — El ENCOGIDO de packets como método; y la limpieza autónoma de candidates APARCADA con criterio escrito (dúos r29/r30/r31)

- **Fecha**: 15 ago 2026. **Impacto**: MEDIO-ALTO (método de adjudicación + identidad del
  catálogo). Tres dúos completos: r29 (Sol 5 · Fable 3), r30 (Sol 6, 2 críticos), r31
  (Sol 7 · Fable 5, 2 críticos, EMPAREJADO correcto). 0 falsos positivos en los tres.
- **Lo que SE HIZO (aplicado y mergeado)**: el **encogido** de los packets E1/E1b/E2 —
  workflow de 9 agentes: 2 pasadas deterministas + 5 de juicio con cita verificada
  full-text + síntesis + verificador adversarial. **2.108 filas → 1.181 en bloque + 911
  una-a-una + 16 fuera**. El verificador hizo el CENSO COMPLETO de las 570 citas de bloque
  (no la muestra de 12 que pedía el encargo): **0 citas inventadas, 0 fallos de criterio**.
  Cerrado después el ítem bloqueante (39 citas mal atribuidas → 38 re-atribuidas, 1 fuera):
  censo final **568/568 verifican en su documento atribuido**.
- **Hallazgo que justifica la pasada**: la premisa del packet E1 §1 era **falsa de
  nacimiento** — las 49 «colisiones» no eran dos filas activas sino fichas fantasma
  retiradas; el censo de s320 testeaba que la fila EXISTIERA, nunca su `status`.
  Consecuencia medida: `must_preserve.attest_identity` no actúa en esos manuales
  (→ TECH_DEBT #80), y de ahí salió también #81 (61 chunks huérfanos).
- **LO QUE NO SE HIZO, y la decisión de NO hacerlo**: la limpieza autónoma de candidates
  queda **APARCADA**. Alberto autorizó la vía fluida sobre una premisa MÍA que resultó
  falsa: «confirmar de más es barato». **No lo es**: quitar `candidate` activa los alias
  existentes (`catalog_store.py:112`), cambia la expansión de paraguas (`:192`) y mete
  canónico + alias en el **detector generado** (`catalog_resolver.py:142-153`) — clase
  `FUEGO` × 600, sin medir. Y el predicado de retirada **se auto-rechazó**: de 18 filas
  pasaron 3 y las 3 eran falsos positivos (`VSN 2Plus` es producto real).
- **Criterio para retomarla** (escrito, no de memoria — `evals/s323_criterio_limpieza
  _candidates_v1.md`): censo del radio de explosión POR FILA (solo lectura) · exclusión de
  toda activación que añada término de riesgo léxico · gate MEDIDO por lote (delta del
  detector + negativos end-to-end) · predicado de RECONSTRUIBILIDAD (los caracteres del
  término deben derivarse del texto vecino) validado contra el **doble control**:
  positivos `MM-82`/`TO-3200M`/`OF-48V`/`LOCAL-360`, negativos `VSN 2Plus`/`PL4-E`/`34110400`.
- **Alternativas descartadas**: (a) aplicar retiradas «probables» sin prueba mecánica —
  invierte la asimetría y borra productos reales; (b) confirmar todo lo que tenga menciones
  — una mención no es ser sujeto (`B501` dispara dentro de `B501AP`); (c) pedirle a Alberto
  que firme las 665 — es el cuello de botella que manda quitar.
- **Lección de método (la que importa)**: las tres automatizaciones intentadas hoy las paró
  el control ANTES de escribir. El patrón común de los tres fallos es el mismo: **puertas
  que confunden correlación con prueba**, y alcances presentados como completos con un hueco
  (49+3+7=59 de 60). El control funciona; el diseño de puertas es lo que hay que endurecer.
- **Relacionado**: TECH_DEBT #80/#81 · packets v2 (`s320_e1*/e1b*/e2*_v2.md`) · planes
  `s323_plan_80_81_v1.md` y `s323_criterio_limpieza_candidates_v1.md` · tallies r29
  (ts=2026-08-15T13:30:27), r30 (19:00:07), r31 (19:47:49).

## DEC-223 (s321) — El ISO-X NO participa en el acotado de un FALLO DE TIERRA: el hecho baja a SUPPLEMENTARY y la prosa que lo prescribía se retira

- **Fecha**: 15 ago 2026 (s321). **Impacto**: MEDIO — corrige un gold del ruler y retira de una
  respuesta una instrucción de campo incorrecta. **Decide**: Alberto (DEC-025 — el gold es suyo).
- **Caso**: `hp006` — «La Notifier AFP-400 muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y
  cómo se localiza?». Hecho #3, etiquetado `core`: *«Para acotar un fallo en el lazo se usan los
  módulos aisladores ISO-X, que aíslan la rama en avería del resto del lazo (requeridos para
  Estilo 7 según NFPA)»*.

**LA DECISIÓN**: el hecho pasa a `supplementary`, y del `gold_answer` se retira el inciso
«*—en el lazo, mediante los aisladores ISO-X—*». El método de mitades («aislar/desconectar circuitos
progresivamente») se queda: lo que se cae es atribuirlo a los aisladores.

**POR QUÉ — cuatro anclas, todas dentro de manuales oficiales aplicables.** Esto importa: la
objeción legítima era que negar el hecho sería imponer teoría eléctrica sobre la fuente. No lo es.

1. **La tabla de `MIDT170` p71 — la MISMA página que el hecho cita como prueba.** «Funcionamiento
   del Lazo de Comunicaciones»: la fila **Tierra** vale `Alarma/Avería` en Estilo 6 **y** en Estilo
   7; la fila **Corto** pasa de `Avería` a `Alarma/Avería` **solo al llegar a Estilo 7**. Como
   `MFDT170` p17 dice que «El Estilo 7 requiere el uso de módulos ISO-X», el propio manual documenta
   que **poner aisladores no cambia nada frente a una tierra, y sí frente a un corto**.
2. **El mecanismo, `MIDT170` p77** (sección «Conexión de un Módulo Aislador (ISO-X)»): «*Un
   **cortocircuito** en el lazo rearma el relé. El ISO-X detecta **este cortocircuito** y desconecta
   la ramificación en avería abriendo el lado positivo del lazo (terminal 4)*». Dispara por colapso
   de tensión ENTRE LOS DOS HILOS; una derivación a masa no lo produce. Y abre **solo el positivo**.
3. **`50253SP` p98** (manual de instalación del mismo panel — ver la corrección de registro abajo):
   «*Un **corto circuito** en el SLC restablece al relevador. El módulo ISO-X detecta el **corto**…*»
   — es la frase de la p17 escrita con el término preciso.
4. **La detección de tierra no está en el lazo**: vive en la fuente MPS-400 (LED «Fallo de Tierra»,
   borne TB1-3, puente JP2 que la inhabilita). Otro subsistema. Los aisladores no la ven.

**EL RAZONAMIENTO DE ALBERTO QUE CIERRA EL CASO**, y que es mejor que el argumento por fuente: *si
el ISO-X acotara la tierra, no verías «Tierra» en pantalla — verías una rama caída*. Que la central
anuncie Tierra **con el lazo funcionando con normalidad** demuestra que ningún aislador se ha
disparado.

**LA MITAD PROCEDIMENTAL, también resuelta y también con fuente.** Se examinó si el ISO-X sirve como
PUNTO FÍSICO por donde partir el lazo al buscar la tierra (bisección), aunque no se dispare solo.
**No.** El manual de instalación de la AFP-400 ordena «*temporarily place a jumper between Terminals
2 and 4 on each ISO-X while taking measurements*» — el fabricante los trata como **estorbo para la
medida**. Además: en sus 179 páginas, las páginas de «ground fault» y las de «ISO-X» tienen
**intersección vacía**; el procedimiento escrito de otro panel Notifier (NFS-640) desconecta
«*devices or circuit sections one at a time*» sin aisladores; y las guías de bisección hablan de
**caja de registro**, no de aislador.

**ALTERNATIVAS DESCARTADAS**
- **Dejarlo `core` reformulado**: no. El ISO-X es **opcional** — solo lo exige el Estilo 7. Una
  AFP-400 sin ningún ISO-X da «Tierra» igual. Un `core` exigiría mencionar un equipo que puede no
  existir en la instalación por la que preguntan.
- **Borrarlo (❌)**: no. Como arquitectura del lazo es correcto y su cita de Estilo 7 es buena. Vale
  como `supplementary`.
- **Apoyarse en la física de lazos flotantes o en el datasheet DN-2243**: innecesario. Las cuatro
  anclas son de manuales aplicables; la desambiguación se sostiene **borrando toda la evidencia
  externa**. Queda constancia de que DN-2243:B dice «*wire-to-wire short circuits*» y «*opens circuit
  when the line voltage drops below four volts*» — corroboración, no apoyo.

**CONTRA-EVIDENCIA DECLARADA** (lo que citaría quien defendiese el `core`): la nota inmediatamente
encima de esa misma tabla dice que el Estilo 7 aísla zonas «*desde **los fallos** que tienen lugar
dentro de otras áreas*», genérico. La desactiva la tabla que va justo debajo, del mismo autor y la
misma página. Y `MIDT170` p17 dice «avería en el circuito», también genérico — es el pasaje-resumen;
la p77 es el pasaje-mecanismo. **`DEC-221` aplicado**, en un segundo caso independiente del que lo
originó.

**MATIZ TÉCNICO QUE NO SE PUEDE OMITIR**: con **dos** derivaciones a masa en polaridades opuestas la
tierra degenera en cortocircuito real y el ISO-X sí actúa. No es teoría: la tabla de `MIDT170` p71
tiene fila propia **«Corto y Tierra»**, que también mejora solo en Estilo 7. Redacción admisible:
*el ISO-X no reacciona a una derivación simple; solo si esa tierra ha degenerado en corto — y ni aun
así la localiza ni la despeja*.

**CORRECCIÓN DE REGISTRO — `50253SP` SÍ es manual de la AFP-400.** El bloque s320d del packet lo
descartó como «es de la AFP-300» apoyándose en `chunks_v2.product_model`. El `doc_map` (línea 92) lo
declara `role=primary` de **`notifier:afp-300` Y `notifier:afp-400`**, igual que `MIDT170` (línea
489). La captura de Alberto sobre **`15088SP`** sigue siendo correcta y no se toca (primary =
`afp1010` + `am2020`); lo erróneo fue extender aquel hallazgo a `50253SP`. De aquí sale
`TECH_DEBT #84`.

**ERRATA ÚTIL**: el gold cita `MIDT170 p63 (f71)` y registra offset +8, pero el pie de esa página
dice **64** (y el de f77 dice 70). El offset real es **7**: las citas impresas del gold van corridas
una página.

**Artefactos**: `evals/s312_goldreview_b2_packet_v3.md` (ítem 5) · workflow `wf_38d0cbac-aaf` (9
agentes: 5 lentes de evidencia + 3 refutadores + síntesis) · verificación a mano contra `chunks_v2` y
`data/catalog/doc_map.jsonl` en el mismo turno (regla C).

## DEC-224 (s321) — Sentada B2 APLICADA al ruler (6 golds, dúo r-emparejado v1→v4); y la conducta ante marca↔producto errónea pasa a (a) «corregir Y responder» — decisión de PRODUCTO de Alberto, PENDIENTE de cablear

- **Fecha**: 16 ago 2026 (s321). **Impacto**: MEDIO-ALTO — toca el patrón de medida (ruler) y fija
  una conducta de serving. **Decide**: Alberto (DEC-025 para los golds; producto para la conducta).

### A · Lo aplicado al ruler (un solo commit, cascada s277 incluida — DEC-218)

| ítem | gold | qué | cores |
|---|---|---|---|
| 3 | `hp017` | **#2 se CONSERVA** (nombra solo la Regla 1 = coherente con la lectura de Alberto; y es `release_guard` de s277 con anclas selladas — partirlo habría movido el sha del contrato). **+1 `supplementary` «Regla 2»**: describe la diferencia de ALCANCE A5.2/A5.4-Ej.1, sin afirmar «no anula» (el manual no lo dice). No condiciona PASS. | 5→5 |
| 4 | `cat018` | **split #2** → (a) asociación CBE + (b) Tipo SW/TIPO ID con la regla de **p65** («la central no permite programar una ecuación si el módulo tiene un TIPO ID para señalizaciones de carácter general») y la tabla p40-41 (23 tipos). Ambas CORE (Alberto: «no quiero falsear los misses» — adjudicó en CONTRA de la única casilla que mejoraba el marcador sin tocar el bot). `gold_answer` punto 3 alineado. | 4→5 |
| 5 | `hp006` | **#2 → `supplementary`** + texto reescrito (aísla CORTOCIRCUITOS, no tierra) + las **dos** frases del `gold_answer` + procedencia (offset +7, `acuerdo` corregido) + `citations` creado (f71/f77). DEC-223. | 4→3 |
| 6 | `cat020` | `valor` = **el marcado por Alberto** («niveles por defecto del protocolo Morley-IAS»; v2-v4 lo habían cambiado sin declararlo — Fable). Texto con los DOS ejes (España + protocolo). Deja de disparar `_is_meta_ref` ⇒ entra al denominador de factlevel. | 3→3 |
| 8 | `hp002` | Enunciado **INTACTO** («de Detnov» = estímulo `oem-relabel`; `hp019` es el control con la marca correcta — asimetría deliberada). **+1 core «Securiton AG»** al final: HECHO de fabricante (portada + p18 «Fabricante = Securiton»), SIN meta-instrucción. | 5→6 |
| 9 | `hp021` | **ALTA**: ruta AJUSTES > AVANZADO (core) + acceso candado/2222 (core, UNO como adjudicó Alberto) + 2 suppl. Estrato `sintesis-completitud`. Verificado COMPLETO: render 160dpi ±1, GPT-5.5 en frío, localización ES+EN por doc_map. | +2 |

**Verificación (RULER_DESIGN §2, punto por punto)**: (1) localización exhaustiva ES+EN por `doc_map`
—no por `product_model` (TECH_DEBT #84)— para los tres golds con cores nuevos →
`evals/s321_localizacion_es_en_v1.json`; (2)+(3) render 160dpi de 17 páginas con ±1 →
`logs/render/s321/`; (4) doble señal GPT-5.5 en frío sobre 7 páginas → `evals/s321_cross_verify_v1.txt`,
**coincidente en las 7**. **El render ±1 cazó un off-by-one**: el chunk «p26» del MI-716 contiene el
diagrama que físicamente está en **p27** (PDF apaisado, dos páginas por hoja) — ambos modelos lo vieron;
la cita de `hp021` es p27. Es exactamente para lo que el paso 3 existe.

**Cascada s277 (DEC-218)**: builder → contrato+prereg_v1; pins copiados a mano a prereg_v2/v3 y scorer
(`da79055e/fbfc97cc → 7c39ba69/511bc020`); canarios s203/s204/s205 re-anclados al ledger
(`a306b126 → 59df5f99`, diff de UNA línea cada uno); manifest histórico **intacto**. 24/24 tests.
**La migración de índices que Sol pedía NO hizo falta**: al no partir `hp017#2`, las 42 claves históricas
OK del ledger s113 siguen válidas (simulado ANTES de escribir, verificado DESPUÉS contra el YAML real).

**El dúo (4 rondas: v1→v4, todas registradas en `evals/adversarial_review_log.jsonl`)**: Sol NO SÓLIDO en
v1/v2, 7 en v3, 7 en v4; Fable emparejado sobre v4 (ts=2026-08-16T11:51:02): **sin críticos**, 3 medios.
**Cero falsos positivos** en las cuatro rondas tras regla C. Lo que el dúo NO cazó y sí cazó Alberto: el
2222 como supplementary en `hp021` (contra su marca explícita) y que A5.4 es un EJEMPLO. Lo que el dúo
cazó y yo tenía mal: `product_model` como filtro (→ #84), `load_dev()` sin filtro de estado, el harness
que no atraviesa `mismatch`, `hp006` sin `citations`, dos frases ISO-X en vez de una, `cat020` con el
`valor` cambiado sin declarar, la meta-instrucción en el core de `hp002`, mezcla de denominadores.

**Fuera del ruler, declarado**: «FORC/CON/CONV/GSND/GSTR sí aceptan CBE» (p39 solo lista); «distribuido por
Detnov» (ningún chunk del ASD535 lo dice); «Guía Avanzada = MC-380» (va en `notes` de hp021, anclado en
doc_map, no como hecho); «el MI-716 no documenta AVANZADO» (ausencia: exigiría render de 48 pp).

### B · La conducta ante «el ASD535 de Detnov» — decisión de PRODUCTO, PENDIENTE de cablear

**Estado real HOY** (verificado en código, no en el packet — que decía «rechaza» y era inexacto):
`src/orchestrator/turn_plan.py:451-460` detecta la marca mencionada, resuelve `marca_de_modelo` en el
catálogo y si no coincide devuelve `ruta="mismatch"`; `src/bot/telegram_bot.py:1178-1189` responde
literal «*El ASD535 es un producto de Securiton, no de Detnov. ¿Te refieres al ASD535 de Securiton? Si es
así, dime tu pregunta y te ayudo.*» y **retorna sin llamar al RAG** = corrige y pide confirmar (b).

**Decisión de Alberto: (a)** — corregir la marca **y responder en el mismo turno**. Prefiere fluidez con
el riesgo declarado (asume aparato correcto, marca equivocada). **Alternativas**: (b) como hoy — un turno
más, más seguro si el técnico se equivocó de aparato; (c) rechazar seco — no existía.

**Qué exige cablear**: que la ruta `mismatch` corrija **y siga a `_process_query`** con el modelo
resuelto. Es serving ⇒ dúo + flag-off + PR propio. **NO entra en esta PR.**

**Cómo se mide** — y esto es lo que Sol v4 cazó y hay que tener claro: el harness
(`test_bot_vs_gold.run_bot`) llama a `execute_rag_turn` directo y **no atraviesa `mismatch`** ⇒ `hp002`
mide si el GENERADOR nombra a Securiton ante «de Detnov», **no** la conducta de serving. La conducta (a)
se verifica con **smoke del bot real** cuando se cablee. `hp002` NO es su testigo end-to-end.

**Artefactos**: `evals/s321_sentada_b2_conjunto_de_escritura_v{1,2,3,4}.md` · `scripts/s321_aplicar_sentada_b2.py`
(falla-cerrado: valida las 6 en memoria antes de escribir) · `evals/s312_goldreview_b2_packet_v3.md`.
## DEC-225 (s324) — El residuo de los packets se adjudica por REGLAS, no por filas; el lote firmado se aplica con puertas que PRUEBAN (dúo r32 aplicado entero); Puerta A validada

- **Fecha**: 16 ago 2026. **Impacto**: MEDIO-ALTO (método de adjudicación + identidad del
  catálogo + corpus). Dúo r32: Sol xhigh 6 hallazgos (3 críticos) · Fable 5 6 hallazgos (no
  emparejado: HEAD movió durante su run). 0 falsos positivos en Sol; 1 premisa falsa en Fable.
- **Decisión de método (Alberto, 16-ago)**: ante 911 filas «una a una» que cayeron del bloque
  por falta de REGLA (no por variación del juez), Alberto **adjudica reglas** y el autor las
  aplica mecánicamente con prueba: R1 serie × categoría en el residuo · R2 confirmar SOLO modelos
  concretos nombrados como sujeto con cita (etiquetas de familia → paraguas, nunca producto: en
  `resolve()` exact sombrearía al paraguas) · R3 OEM: un documento no crea ni amplía
  `vendido_bajo` (gt FAAST/VESDA de s78–s91 intacto) · R4 alta+doc_map solo con cita, la ficha
  sola nunca (guarda: KE-IU3110 en la ficha, 0 en el contenido) · R6 fuente retirada → no alta ·
  R7 concatenados → componentes con cita propia · R5 → BAJA de 6 fragmentos PT con hermano ES
  (política de idiomas s65) + OCR primero para TI-007. Registro: `evals/s324_reglas_residuo_adjudicacion_v1.json`.
- **Lo aplicado** (recibo `evals/s324_lote_firmado_aplicar_20260816T113215Z.json`, verificación
  posterior en censo `s324_verificacion_posterior_v1.json` 0 fallos): doc_map +57 filas/225 entries
  · 13 altas · 7 confirmaciones (DX1e/2e/4e + 3 cajas + VSN 12 PLUS — cierra el único agujero de
  paraguas, «Dimension» 0/3 consumibles) · 2 etiquetas retiradas + 1 alias · 3 paraguas (2X-AT,
  2X-A Táctil, VSN PLUS) · 2 retags DB con CAS · 7 docs `retired`. Suite 3.890 verde.
- **Las puertas que prueban** (`scripts/s324_lote_firmado_plan.py` + `_writer.py`): cita
  verificada full-text en cada fila (`autocheck_*` = true) · freeze = sha×4 + fingerprint del
  corpus + snapshot de los chunks a retaguear (el `--aplicar` recalcula y aborta si difiere) ·
  build en tmp → validar → backup COMPLETO → swap · CAS por chunk y en `documents` (eq.pm_actual)
  con rollback · **censo del radio de explosión**: detector del resolver 1.667→1.695 (+28/−0), 0
  gold perdidas, 0 disparos en 36 negativos (sintéticos, declarado), `resolve_query` sobre las 51
  gold antes/después (0 pérdidas / 9 ganancias — las FAQ DXc +12 fuentes), findability de retags.
  Regla mecánica del veredicto: STOP = pierde gold | dispara negativo | palabra común; «corto» =
  aviso (hoy ya hay 43 términos con normkey ≤3).
- **Lo que las puertas cazaron ANTES de escribir**: fidegas s3-t1/s2-t1 ya existían (validador
  `canonical DUPLICADO`) · ExitPoint ya es alias de pf24v (I56-2961: «EXITPOINT — PF24V»; línea
  vs modelo) → no se duplica · paraguas «2X-A» dispara en «2 x a» → DIFERIDO · **R1'** («si el doc
  nombra modelos, atestar solo los nombrados») nació del censo pero NO estaba firmada → 3 docs a
  la firma de Alberto (Sol M2) · hlsi-ti-001 → solo rp1r-supra (VSN-RP1r+ ES su nombre Morley,
  `vendido_bajo`; VSN-RP1r-PLUS2 es DISTINTO por #25 s285) · NX2/R/R–NX5/R/R (1 mención en tabla)
  y TI-007 (OCR primero) y 996-130 FR (baja antes que atestar) → fuera del lote.
- **Puerta A rehecha (Sol r30 la había tumbado)**: predicado de RECONSTRUIBILIDAD (tramos
  alfabéticos ∈ léxico de palabras/unidades + co-ocurrencia ≤48 chars + no sujeto; clase
  norma/cert; solo-numérico nunca) — **VALIDA** contra el doble control 5/5 + 3/3
  (`evals/s324_puerta_a_predicado_v1.json`). Resultado honesto: 0/18 filas RETIRAR de E1b son de
  esa clase (palabras genéricas / part-numbers) → siguen en cuarentena; generalización E1 §0.D
  4/17 (los códigos de documento MNDT/MADT/TIDT son otra clase, mecanizable aparte).
- **Alternativas descartadas**: (a) repetir el review exhaustivo K alto sobre las 911 (mismo
  residuo, ~$40) — se descartó tras diagnosticar que caían por regla, no por juez; (b) aplicar
  R1' como parte del «lote firmado» — Sol lo tumbó con razón: criterio nuevo, adjudicable; (c)
  aplicar el sí de E1b «en seco» — DEC-220 r30: cada bloque pasa por censo + gate.
- **Alerta sobre el instrumento** (→ TECH_DEBT #86): la review de Fable 5 incluye una
  transcripción de tools FABRICADA (0 `tool_use` reales en el responses JSON; cita ficheros
  inexistentes) — sus hallazgos válidos salieron de las semillas. Y el emparejamiento se rompió
  porque el autor commiteó durante el run (regla: no mover HEAD mientras corre un dúo).
- **Relacionado**: DEC-222 (r30/r31) · packets v2 anotados con estado (`scripts/s324_packets_estado.py`) ·
  tally r32 (Sol ts=2026-08-16T13:22:27; Fable 13:26:02) · TECH_DEBT #86/#87/#88 · reversión:
  `git checkout af95f49 -- data/catalog/` + `retags.backup_chunks` del recibo.


## DEC-226 (s321, autónoma) — Conducta (a) del `mismatch`: DISEÑO CONSOLIDADO en dos rondas de dúo, NO CABLEADO a propósito; queda una decisión de producto (multi-modelo) para Alberto

- **Fecha**: 16 ago 2026 (sesión autónoma, Alberto fuera). **Impacto**: MEDIO en zona de dolor (serving del
  bot). **Decide**: nada nuevo aquí — registra que el cableado de DEC-224 §B **no se hizo** y por qué.
- **Lo que pasó**: la propuesta v1 («un flag en el handler, sin tocar el planificador») recibió de Sol 6
  medios, todos verificados: viola el punto de decisión único (DEC-200: «el transporte EJECUTA el plan sin
  re-examinar el texto»), la ruta nueva viola el CHECK cerrado de `query_logs.route` (y `logging_db:80-81`
  lo declara bug del emisor), voz no pasa por `plan_turn`. La v2 (`fallback_ruta` + `rag_trace` +
  `target_models_override`) recibió **1 crítico + 4 medios**, todos verificados: `rag_trace` NO es libre
  (`runtime_trace.build_rag_serving_trace` es «the only runtime trace shape allowed» con enums cerrados —
  una clave libre descarta la traza entera); F1 re-resuelve `target_models` DESPUÉS del override; y el
  multi-modelo («ASD535 de Detnov y ADW535 de Securiton») no tiene contrato.
- **Decisión de alcance (mía, declarada)**: el diseño correcto toca **cuatro subsistemas** (`TurnPlan`
  con campo tipado `preambulo`; `runtime_trace` builder+validador; F1 con entrada explícita de modelo
  resuelto; `_process_query`/`log_query` con respuesta compuesta) y **una decisión de producto** que no es
  mía. Cablearlo sin Alberto sería construir sobre un contrato no decidido (Protocolo 2). **v3 = diseño
  consolidado** en `evals/s321_mismatch_conducta_a_propuesta_v3.md`, para una sesión dedicada con dúo.
- **✅ ADJUDICADO POR ALBERTO (17-ago, s324e): opción (a)** — «vamos con la (a), pero deja anotado que lo
  mejoraremos a futuro». Es decir: la corrección marca↔producto se aplica **sólo cuando hay UNA marca y UN
  modelo** y no casan (que es el 100 % de los 👎 registrados hasta hoy: «me has dado información sobre productos
  de Kidde…», «información sobre la ID3000 que no es de Detnov»); con varios modelos o varias marcas en la misma
  pregunta, el bot responde como hoy sin intentar emparejar. **MEJORA FUTURA ANOTADA**: la opción (b)
  —emparejar marca↔modelo por proximidad y corregir sólo el par erróneo— queda como evolución cuando el piloto
  dé casos reales multi-modelo; no se descarta, se pospone por superficie de error (corregir mal es peor que no
  corregir). Cablear con dúo, flag y PR propia; diseño consolidado en `evals/s321_mismatch_conducta_a_propuesta_v3.md`.
- **LA DECISIÓN QUE QUEDABA PARA ALBERTO (ya adjudicada, arriba)** — multi-modelo/multi-marca en la misma pregunta:
  (a) fuera de alcance: si hay más de un modelo, NO se aplica mismatch-answer (se responde como hoy) —
  **recomendado** para el primer cableado; (b) emparejar marca↔modelo por proximidad y corregir solo el
  par erróneo — contrato nuevo, más superficie; (c) otra.
- **Evidencia colateral del FULL de factlevel (16-ago)**: el core nuevo `hp002#5:Securiton AG` sale
  **rerank-miss** ⇒ el generador NO corrige la marca por sí solo desde el RAG. La conducta (a) es de
  serving y hay que cablearla; `hp002` mide al generador, no la conducta (DEC-224 §B).
- **Recibos**: Sol v1 ts=2026-08-16T13:08:52 · Sol v2 ts=2026-08-16T14:12:49 · 0 falsos positivos en 11
  hallazgos verificados. Fable se emparejará sobre la v3 en la sesión dedicada.

## DEC-227 (s324b/c, autónoma nocturna) — Etapa 3 MEDIDA antes de construir: población de serving = 1 hecho, los «flips» son síntesis inestable, D1 NO se construye; los lotes firmados por Alberto (R1', §0.C, STRATOS, §0.D/§0.E, Detnov) aplicados con puertas; los bloques E1b PREPARADOS (11/11 PASS) sin aplicar

- **Fecha**: 16-17 ago 2026 (misma sesión que DEC-225; Alberto adjudicó por la tarde y durmió con «OK, a por
  ello» sobre el plan nocturno). **Impacto**: ALTO en zona de dolor (retrieval/síntesis + catálogo).
- **Decide (1) — el lever de etapa 3 NO se construye todavía, con dato**: la sonda de alcanzabilidad de los 8
  «servido y omitido» del FULL 16-ago (agente de medición, ~$11-13, `evals/s321_poblacion_etapa3_v1.md`) dio 7
  ALCANZABLE / 1 NO (`hp009#0`, entrega 3/3 + cobertura); pero la población por gold de HOY es {hp017, hp005,
  hp015, hp001} = 4 y **no es una clase**: `hp015` era DATOS (CCD-103 candidate → resuelto esta noche), `hp001#2`
  within-doc NO-GO 3×, `hp005#3` omisión inestable, y solo `hp017#1` lo levanta un lever de serving. La propuesta
  D1 «cierre de bloque de lista» (`evals/s324c_lever_b_propuesta_v1.md`) pasó por el **dúo r33** (Sol 6 hallazgos ·
  Fable 5 con 14 `tool_use` reales): no es vista pasiva, listas sin fin inequívoco, denominador 1 → **medir antes**.
  Medido esa noche: **prueba offline D1** ($0, código real de coverage, fidelidad 40/40) — alcanza `hp017#1` SOLO con
  la definición A (blanco no rompe), 0 hechos NO-OK adicionales, toca 6/27 filas estructurales y 9 hechos OK; y
  **replay congelado** ($5,44) — los 4 flips son **SÍNTESIS INESTABLE 4/4** con la vista idéntica (juez bimodal), no
  serving. ⇒ Cifra de cabecera de DEC-175: **1 hecho pagable por serving**; D1 solo con GO explícito de Alberto sobre
  «1» (y entonces A pineada + G2 antes de G3). Los tres de conducta («negar la premisa» `hp009#0`, `hp013#1`,
  `hp011#2`) van a gold-review: `evals/s324c_goldreview_conducta_packet_v1.md` (3 opciones cada uno; nada aplicado).
- **Alternativas descartadas**: (a) construir D1 esta noche «apoyándome en el adversarial» (Alberto lo sugirió) —
  el dúo r33 lo paró y la medición confirmó población 1; construir sobre 1 hecho es el sesgo #51 (proxy por
  eval); (b) atacar los 19 «no OK» del FULL hasta >95% OK — son heterogéneos (12 síntesis de los que 8 son
  «servido y omitido», 4 conducta, resto retrieval/datos): no hay UN lever, y los flips son varianza de síntesis
  que un lever de serving no toca; (c) tomar el «≥4 alcanzables» como población — sustitución de denominador
  (Fable r33): un «alcanzable» no es un hecho pagable.
- **Decide (2) — lotes firmados aplicados con las puertas de DEC-225** (cada uno con plan verificado full-text,
  dry-run + censo del radio de explosión, freeze, backup, verificación posterior 0 fallos): **R1'** (3 docs
  2X-A/2X-AT → solo modelos NOMBRADOS, 62 entries) · **§0.C** (21 altas incl. software ID²NET/CLSS Configuration
  Tool, 7 alias, 26 doc_map, 2 bajas; revisor Fable standalone 6 hallazgos aplicados: paraguas «2X-A» DIFERIDO
  con pregunta explícita, NFXI-BSF-WCH grafía firmada + alias WC, FAQ DXc cita propia, alias ASCII ID2net/IDNet)
  · **STRATOS** = paraguas de familia (LaserStar-HSSD-2, MINILÁSER25, MINILASER 100; −2 alias erróneos) ·
  **§0.D/§0.E** (5 docs retirados, altas Fidegas S/3-2, S/3-IR, S/2-IR y EMA1224B4R/W, TG confirmado SOFTWARE
  con gate léxico 0/96, MADT731_06 → HSSD-2, 5 retags) · **Detnov E1b** (8 confirmaciones + `detnov:ccd-103` alta
  con redirect desde `unresolved:ccd-103`; el gate cazó 14 alias descriptivos —«2 zonas», «4 zonas», «Conventional
  panels with…»— que la confirmación ACTIVABA: retirados antes; tráfico real +1 detección = TP). Cada «sí» de
  Alberto vino con nota en el packet canónico; lo que solo él firma sigue ⏳ marcado fila a fila.
- **Decide (3) — E1b PREPARADO, no aplicado**: 11 planes por bloque (+2 K=5, abajo) + dry-run del gate **11/11 PASS** (422
  confirmables verificadas full-text, 40 `no_aplicar` con propuesta —colisiones canonical/alias/paraguas y
  grafías—, **125 alias descriptivos que se retirarían antes**, regla nueva del clasificador «truncación ambigua de
  familia» nacida del gate: `VSN12` disparaba «vsn 12»); `evals/s324c_e1b_bloques_censo_v1.md`. Un «sí» por bloque =
  re-dry-run del mismo sha + `--aplicar`. Cross-bloque morley↔unresolved / morley↔notifier: exige adjudicar homónimos.
- **Decide (4) — re-juicio K=5 cross-model de la clase «confianza media»** (61 filas: E1 14 + E1b 47; 3× `claude-sonnet-5`
  + 2× `gpt-5.5`, rúbrica ORIGINAL de cada packet, texto completo del doc como evidencia, voto válido solo con cita
  verificada full-text; ≈$6,6): 39 convergentes ≥4/5 (E1b 34 CONFIRMAR + 1 RETIRAR `notifier:fs-2`; E1 PRODUCTO_REAL
  `morley:morley-ias-max` y `notifier:repetidor-serie-1000`, ARTEFACTO `aritech:2x-a-tactil` y `notifier:madt-606`), 22
  no convergentes (10 con desacuerdo cross-model Sonnet RET/ART vs GPT CONF/PROD; 5 con término AUSENTE y citas
  inverificables por construcción). Lo convergente E1b sube a bloque **`k5_confirmar` PREPARADO** con el mismo gate (31
  confirmables PASS; 3 DS-10 con grafía «--» no verifican; fs-2 sin doc resoluble). Propuesta, NADA aplicado; el
  desacuerdo cross-model es la señal de que la clase no era «ruido del juez» sino filas de verdad ambiguas.
- **Colateral**: `test_s307` (cota de la lista plana de inventario) se acopló a los DATOS del catálogo (Notifier ya
  tiene productos clasificados → la vista agrupada tomaba el turno): el test fuerza ahora la ruta plana. Lección:
  los tests de render de inventario no deben depender de qué marca tiene clasificación.
- **Recibos**: `evals/s324b_r1prima_aplicar_*`, `s324b_lote_0c_aplicar_20260816T193507Z`, `s324b_stratos_aplicar_*`,
  `s324c_lote_0de_aplicar_*`, `s324c_e1b_detnov_aplicar_20260816T213209Z`, sondas `s293_reachability_*` (8) ·
  dúo r33 Sol ts=2026-08-16T22:52:37 / Fable 22:55:15 · `s324c_d1_prueba_offline_v1` · `s324c_replay_congelado_flips_v1`
  · LEVER_DIGEST fila «Etapa 3 / síntesis» sobrescrita in-place · TECH_DEBT #89 (5 defectos de la sonda).
- **Relacionado**: DEC-173/175 (banner corregido) · DEC-225 · DEC-224 (gold-review vía `gold_store`).

## DEC-228 (s324d, autónoma diurna) — La sonda de alcanzabilidad se ENDURECE (TECH_DEBT #89) con dúo r34: oráculo `serve` PAREADO por defecto, guard de cobertura del span con valor+predicado, votos caídos del juez no cuentan como «no», recibo parcial nunca completo, coste real; y el runner Fable audita sus `tool_use` reales (#86)

- **Fecha**: 17 ago 2026 (Alberto revisando packets; trabajo autónomo acordado: «¿qué puedes avanzar tú por tu lado?»).
  **Impacto**: MEDIO en zona de dolor (instrumento de medición de etapa 3; no serving). Producción sin cambios.
- **Decide (1) — semántica del instrumento a partir de hoy**: (a) el oráculo `serve` se genera sobre la MISMA vista
  que recibió el generador en la base + la inyección (pareado; `--oracle-fresco` restaura los turnos independientes),
  y si el carrier YA estaba servido no se duplica (similarity elevada in-place, `aviso_prominencia`); (b) `appendix`
  elige el span con guard de cobertura (`elegir_span`/`span_cubre`: sin partir por «:», extensión ≤2 líneas, tokens
  del valor con frontera de palabra + ≥2 tokens de predicado) y si nada cubre la rep es NO construible ⇒
  INCONCLUYENTE, nunca se juzga un apéndice incompleto; (c) `n_fail` del juez se registra y una rep no firme con
  votos caídos no sostiene un negativo (`INCONCLUYENTE_JUEZ_INCOMPLETO`); (d) un fallo tardío escribe recibo
  PARCIAL con `PARCIAL_<…>` (nunca `NO_ALCANZABLE`/`ALCANZABLE` a secas); (e) `--receipt` o el FULL v3* más
  reciente por defecto (`receipt_usado` estampado); (f) coste real por llamada (`scripts/usage_meter.py`) con
  disponibilidad declarada. Lógica pura en `scripts/reachability_verdict.py` (15 tests nuevos + 10 previos).
- **Por qué con dúo y no de paso**: cambia lo que MIDEN los recibos futuros (pareado ≠ independiente; JUEZ_INCOMPLETO
  ≠ NO). Sol xhigh 7 hallazgos (3 críticos) todos verificados y aplicados; Fable emparejado (11 `tool_use` reales,
  auditoría #86 activa) 1 medio = Sol#2. El propio smoke validó el guard nuevo: mi oráculo pareado pasaba el dict del
  generador al juez (5 fallos) y salió `JUEZ_INCOMPLETO` en vez de un NO falso.
- **Lo que NO cambia**: la vara (`judge_conveyed21` K=5, THRESH_FIRM 4); el fail-closed del negativo de s321; los
  8 recibos de etapa 3 y DEC-175 (no se re-miden). Lectura colateral declarada: el ALCANZABLE de s324b para `hp017#1`
  en `serve` venía con el carrier duplicado; pareado, 1 rep da 0/5 — coherente con la prueba offline D1; 1 rep no es
  medida y no cambia la cifra de cabecera («1 hecho»).
- **Decide (2) — #86**: el runner Fable estampa `tools_reales`/`sin_tools`/`log_de_tools_fabricado`, sufija el `.md`
  `_SIN-TOOLS`, deja nota lateral y avisa; el `.md` no se toca (sha del texto final del proveedor). Regla de
  operación: no mover HEAD durante un dúo emparejado.
- **Colateral de la mañana**: E2 re-derivado tras los lotes de s324b/c (conservador PASS; pleno STOP con 5 pérdidas
  conocidas — CCD-103 ya no pierde; split 618+743); PLAN podado 162 KB → 17 KB (archivo íntegro en HISTORY);
  #88 preparado (55 retags de `documents.product_model` al canónico E3, dry-run 55/55, NADA aplicado — decide Alberto);
  #87: no hay pipeline OCR en el repo (declarado).
- **Alternativas descartadas**: (a) endurecer «de paso» sin dúo — TECH_DEBT #89 lo prohibía y el dúo cazó 3 críticos;
  (b) mantener el oráculo independiente para «medir prominencia» — era el defecto, no una feature; (c) re-medir las
  8 sondas con el instrumento nuevo — ~$12 sin pregunta que lo justifique hoy (la población está adjudicada como 1).
- **Recibos**: `evals/s324d_sonda_endurecida_propuesta_v1.md` (+ADENDA) · tally ts=2026-08-17T10:39:29 (Sol 7/7, Fable
  1/1, 0 FP) · smokes `evals/s324d_reachability_smoke_hp017_1_{appendix,serve}.json` · `evals/s324d_retag_documents_pm_dry-run_*.json`.


## DEC-229 (s324d, autónoma) — El ruler etiqueta ~60 % de sus «no OK» POR AZAR (9 de 15 son inestables con N=1); la raíz de #87 no era OCR sino un `or`; #84 se despriorizó con un no-dato; y #90 se cierra documentado sin tocar la política de idiomas

- **Fecha**: 17 ago 2026 (sesión autónoma; Alberto trabajando en paralelo). **Impacto**: ALTO en zona de dolor
  (instrumento de medida + ingesta). **Producción: sin cambios de código en serving.**
- **Decide (1) — el instrumento: N=1 no basta para clasificar un hecho.** Medidos los **15** hechos no-OK del FULL
  16-ago con **N=5 sobre vista CONGELADA** (mecanismo `gen_answer_only` de s289; juez `judge_conveyed21` K=5,
  THRESH_FIRM 4 intacto; $9,12; `evals/s324d_estabilidad_sintesis_v1.md`; aritmética recomputada 15/15 por el autor):
  **9 INESTABLES** (`cat001#3` 4/5, `hp015#0` 3/5, `cat020#1` 3/5, `hp005#0` 3/5, `cat008#3` y `cat008#1` 2/5,
  `cat016#1`, `hp015#2`, `hp005#3` 1/5) y **6 ESTABLE_MISS** (`hp003#4`, `hp009#0`, `hp011#2`, `hp017#1`, `hp017#2`,
  `cat018#1`). ⇒ (a) el «86 % OK» del FULL lleva una barra de error que no estábamos contando; (b) comparar dos FULL
  con N=1 puede producir deltas que son ruido; (c) **la cola real de defectos es 6, no 15**, y 3 de esos 6 ya están en
  el packet de gold-review de conducta. **Consecuencia de rumbo**: «atacar los no-OK» no es un problema de retrieval ni
  de serving (ahí sólo había 1 hecho pagable) sino de **estabilidad de la generación**. Queda como cabeza de cola:
  decidir si el ruler mide con N≥3 los no-OK. **No se ha cableado nada**: es una medición.
- **Decide (2) — TECH_DEBT #87 RESUELTO con la raíz real, que no era la escrita.** La deuda decía «hace falta OCR».
  Verificado en tres pasos: el PDF de `HLSI-TI-007_VSN-4REL` tiene 2.246 chars de texto NATIVO; el re-parse con la
  config real del corpus devuelve **`md`=34 chars y `text`=3.708 en el MISMO JSON**; los consumidores hacían
  `p.get("md") or p.get("text")`, que sólo cae a `text` si `md` es **vacío**. **LlamaParse agentic YA es la capa de
  OCR**: no hace falta tesseract. Guarda de markdown degenerado en `src/ingestion/page_content.py` (saneado en
  `pipeline.process_file` + `rag/deep_lookup`), 13 tests, **dúo r35** (Sol 5/5 + Fable 5/5, 0 FP, todos aplicados:
  criterio único que cubre el `md` de whitespace, tercera condición «markdown con estructura no se sustituye»,
  auditoría en los 5 caminos del estado, cuarto consumidor en serving). **TI-007 re-ingestado**: 47 → 3.601 chars con
  el procedimiento (PROG/Z1/40 cm) verificado contra la DB. **Dos guardarraíles del repo me pararon y ambos tenían
  razón**: el freeze-contract s130/s132 (`chunk.py` pineado por sha) y el contrato de imports (`rag → reingest`
  prohibido) — de ahí que el módulo viva en `ingestion` y el censo de módulos suba a 123, explicado en el test.
- **Decide (3) — TECH_DEBT #84: el «medido» era un NO-DATO.** `_product_aligned_chunks` sólo es alcanzable desde
  `build_answer_plan`/`build_answer_conflicts`, que el generador invoca únicamente con
  `ANSWER_OBLIGATION_PLANNER ∈ {guided, enforced}`; **en Railway el worker NO tiene esa variable** (censo GraphQL
  propio, 40 vars) ⇒ en producción no corre, y el FULL tampoco la llevaba. Misma clase que DEC-186/s305.
  **Sub-defecto NUEVO en código vivo**: el join `doc_map ↔ chunks_v2.source_file` es EXACTO y 98 de 977 filas sólo
  casan tras normalizar `.pdf`/mayúsculas (`retriever.py:2351,2363`, `catalog_resolver.py:782`) ⇒ su atestación no
  filtra y se les dispara el fetch de identidad aunque estén en el pool. **Impacto en golds: 12 de 1.194 chunks (1 %)
  ⇒ no moverá los OKs**; higiene estructural, fix con dúo cuando toque.
- **Decide (4) — TECH_DEBT #90 (filtro de idioma por chunk) se CIERRA DOCUMENTADO, sin tocar política.** El filtro
  `_DROP_LANGUAGES` descarta chunks por su idioma dominante y en fichas multilingües (tabla con las seis traducciones
  **concatenadas en la misma celda**) se lleva el castellano dentro: `D1056-1_NFXI-BS-BSF` vive en el corpus con 3.593
  de sus 50.527 chars. **Dúo r36** (Sol 5/5 + **Opus 5** como pin alternativo adjudicado, 6/6; **dictaminó NO SÓLIDO**
  y acertó): mi kill del fix usaba un umbral **por DOCUMENTO (≥500 chars de texto nativo ausente)** mientras el fix
  decide **por CHUNK (≥400)** —mismatch de métrica del «settled», el fallo que el Protocolo 4 nombra— y mi frase «los
  842 sano no tienen texto ausente» era **falsa** (`sano` = ausencia < 500). **Recomendación final: (E) DECLARAR EL
  DROP** —contar y persistir los chunks/chars que el filtro descarta, coste ≈0, sin tocar política— **(B) queda
  ABIERTA** (no matada) hasta medirla en su propia métrica, y **(D) no cambiar la política hoy**. Añadido de Opus: el
  filtro **contradice un invariante declarado** (`retriever.py:2430`: «el corpus indexa ES, multilingüe-con-ES y
  EN-only») ⇒ es desvío de política declarada, decisión de Alberto. **E se cablea en la próxima ingesta, no ahora**
  (sólo se llena al ingestar; no da cifra retroactiva sin el store de 966 JSON, que no está en esta máquina).
- **Alternativas descartadas**: (a) construir el fix de #90 hoy — el alcance medible no lo paga y el dúo demostró que
  exige esquema + serving + contrato de generación, no una línea; (b) la excepción por documento para `D1056-1` —
  RETIRADA: serving volvería a filtrarlo y el re-ingestador le asigna metadata incorrecta; (c) re-ingesta masiva del
  corpus con la guarda #87 — sin presupuesto ni evidencia de que pague (el censo de cobertura, 1.054/1.054 documentos,
  da **13 accionables y ninguno sustenta un gold**); (d) cablear el cambio de fuente de aplicabilidad de #84 — su
  punto de consumo está apagado y el instrumento no puede medir el delta hoy.
- **Colateral aplicado**: #88 (55 retags de `documents.product_model` al canónico E3, CAS, verificado) · E2
  re-derivado (conservador PASS; CCD-103 ya no pierde) · PLAN podado 162 → 17 KB · #86 (auditoría de `tool_use`
  reales) y #89 (sonda endurecida, dúo r34) cerrados · runner del segundo revisor con **conjunto CERRADO de pines
  adjudicados** {fable-5, opus-5}, canónico intacto, con traza en el recibo.
- **Lección de método (tres veces hoy)**: el árbol de trabajo se movió durante un dúo —por agentes en background y por
  commits míos— y rompió dos emparejamientos. La regla de #86 se amplía: **durante un dúo emparejado NADIE escribe en
  el árbol**. Y la propia: medir el alcance ANTES de diseñar; en #90 escribí dos propuestas antes de saber que el
  fenómeno era marginal.
- **Recibos**: tally r34 (2026-08-17T10:39:29), r35 (11:25:24), r36 (12:19:59) · `s324d_estabilidad_sintesis_v1` ·
  `s324d_censo_cobertura_paginas_v1` · `s324d_90_filtro_idioma_propuesta_v1` (v4) · `s324d_84_verificacion_regla_c_v1` ·
  `s324d_guarda_md_degenerado_propuesta_v1` · `s324d_reingesta_ti007_aplicar_*` · `s324d_retag_documents_pm_aplicar_*`.


## DEC-230 (s324e) — El piloto con Directores Generales se prepara ENTERO: puerta de acceso por invitación de un solo uso, manejo de errores con insights, aislamiento por usuario probado, y la conducta (a) ante marca cruzada cableada con flag apagado

- **Fecha**: 17 ago 2026. **Impacto**: ALTO en serving (transporte, acceso, errores) + esquema nuevo.
  **Disparador**: Alberto declara su prioridad #1 — «¿qué falta para compartir el bot con Directores
  Generales y que lo vayan testeando?». **Producción: el código sigue sin desplegar** (todo en rama).
- **El diagnóstico que ordenó el trabajo**: el bot tenía **96 consultas de UN solo usuario** (Alberto) y
  **6 👎 con 0 👍**, y los comentarios de esos 👎 apuntaban todos al mismo fallo — el bot hablaba de
  productos de otra marca («me has dado información sobre productos de Kidde…», «la ID3000 que no es de
  Detnov»). O sea: el fallo nº 1 para la confianza de un director ya estaba diagnosticado (DEC-224 §B) y
  **sin cablear**. Lo demás salió de auditar el camino real: sin control de acceso, sin límite de gasto,
  sin manejo global de errores, y con la concurrencia nunca ejercitada.
- **Decide (1) — CONTROL DE ACCESO** (`src/bot/access.py` + `migrations/016`, **aplicada**): allowlist por
  `telegram_user_id` con invitaciones de **un solo uso**, caducidad 48 h (máx. 7 días), revocables, con
  bootstrap auditable desde `user_consent` (Alberto quedó dentro automáticamente; invariante «nadie con
  consentimiento se queda fuera» verificado). **Fail-closed con matiz**: si Supabase cae, los ya conocidos
  siguen (gracia 1 h, bajada desde 24 h porque con la base caída el RAG tampoco responde), pero **no entra
  nadie nuevo**. Tope diario por usuario. Dúo r38 (Sol 8/8 + Opus 5 como 2º revisor 5/5, 0 FP): **dos
  críticos** — un typo en la variable de Railway dejaba el piloto ABIERTO (invertido: sólo un `off`
  reconocible apaga; ausente = apagado, que es la conducta de hoy) y la puerta no miraba el **tipo de
  chat** (un DG podía usar el bot en un grupo donde leen no invitados; ahora se exige chat privado
  **antes** de la exención de `/start`, y Alberto desactivó el modo grupo en BotFather).
- **Decide (2) — ERRORES CON INSIGHTS** (`src/bot/error_taxonomy.py` + `migrations/015`, **aplicada**):
  red global `add_error_handler` **sin flag** (una red detrás de un interruptor no es una red), taxonomía
  por CAUSA con clasificación **nominal** (importar SDKs en una hoja que carga al arrancar significa que un
  SDK reestructurado apaga el bot), persistencia en dos piezas (consulta en `query_logs`, diagnóstico en
  `bot_errors` **sin dato personal directo**, enlazado por FK con CASCADE) y script de insights. Dúo r37
  (Sol 7/7, 0 FP): **crítico de privacidad** — la ruta de voz registraba sin pasar la consulta, así que la
  defensa contra eco no corría y la **transcripción** podía persistirse sin enlace; cerrado con agujas
  múltiples (cruda + normalizada). También cayó un claim falso de disponibilidad (`await to_thread` **no**
  desacopla: PTB procesa de uno en uno) — retirado y sustituido por el coste declarado + kill-switch.
- **Decide (3) — EL RED LINE DE ALBERTO, PROBADO**: «cada DG con su sesión, un usuario ve sólo lo suyo».
  Auditoría con 13 tests: el estado vive en `user_data` (indexado por usuario) y el **censo cerrado** de los
  5 globals del bot demuestra que todos derivan del CORPUS. Un agujero real encontrado y cerrado: con long
  polling, **una segunda instancia partía la sesión de un DG entre procesos** (Telegram reparte los updates
  y PTB reintentaba el 409 indefinidamente); ahora el bot **para**. El `xfail(strict)` que lo atestiguaba
  pasó a XPASS y obligó a retirarse — el trinquete funcionando.
- **Decide (4) — CONDUCTA (a), adjudicada por Alberto**: la corrección marca↔producto se aplica **sólo con
  UNA marca y UN modelo** (cubre el 100 % de los 👎 registrados); con varios, se responde como hoy. La (b)
  —emparejar por proximidad— queda **anotada como mejora futura**, no descartada. Cableada con
  `MISMATCH_ANSWER` **off** y byte-equivalencia demostrada; la composición va TRAS el fallback de respuesta
  vacía y ANTES de estado/render/log, para que `query_logs.response` guarde lo que vio el técnico.
- **Decide (5) — RETENCIÓN, adjudicada por Alberto**: las tablas nuevas siguen los **mismos 24 meses** que
  el resto. Su criterio (consistencia = simplicidad) es correcto y hay un refuerzo que la propuesta inicial
  del asistente (6/12 meses) no vio: **los 24 meses son un invariante de la BASE** (rol `rgpd_retencion`
  con `interval '24 months'`). Excepción declarada: en `bot_allowlist` la acción es **DELETE**, porque el
  id es la PK y no se puede disociar sin destruir la fila.
- **Incidente de las migraciones, y su lección cableada**: la 016 falló **dos veces** al aplicarse —
  primero su `BEGIN/ROLLBACK` de validación dejó la base **sin ninguna tabla** mientras la salida imprimía
  `1` (un éxito aparente), y después el `SAVEPOINT` con que lo «arreglé» dio `25P01`. Mi primer diagnóstico
  («el editor abre transacción») era **falso** y lo di por bueno sin comprobarlo. Solución: **un fichero
  que CREA no lleva control de transacción**; la prueba se fue a `016_validacion_un_solo_uso.sql`, y se
  añadió `NOTIFY pgrst, 'reload schema'` (segundo incidente: tablas creadas y PostgREST devolviendo 404).
  Hay **test** que impide la reincidencia.
- **Alternativas descartadas**: RPC transaccional para canje+alta (más superficie; la ventana queda
  declarada con test que la ejerce) · gobernar grupos autorizando chats además de personas (otra tabla,
  otra revocación, para un caso que el piloto no tiene) · abortar el proceso ante configuración ilegible en
  runtime (convierte un error de config en caída total con el bot sirviendo; en arranque sí se aborta).
- **Lo que NO se hizo, a propósito**: desplegar (todo en rama) · encender ninguno de los flags · implementar
  la política de retención de las tablas nuevas (falta el abogado) · smoke contra Telegram real.
- **Criterio de GO (auditable, en `evals/s324e_allowlist_duo_r1_v1.md`)**: O1 bloquea a no invitados · O2 no
  corta a autorizados · O3 una alta por invitación · O4 cero respuestas fuera de chat privado. **Si O1 u O4
  fallan una sola vez: NO-GO y `BOT_ALLOWLIST=off`.**
- **Recibos**: dúos r37 (2026-08-17T13:46:29) y r38 (15:53:44) + 2º revisor Opus 5 standalone ·
  `evals/s324e_{allowlist_propuesta,allowlist_duo_r1,error_handling_propuesta,mismatch_conducta_cableado,aislamiento_usuarios_auditoria}_v1.md`
  · suite **4192 verde**.


## DEC-231 (s324f) — Se REABRE DEC-183 («dashboard SIN app»): Alberto pide un panel web propio con gestión + métricas, ANTES del piloto, con acceso compartido con el war room

- **Fecha**: 17 ago 2026. **Impacto**: ALTO (servicio NUEVO expuesto a internet que muestra DATOS PERSONALES).
  **Estado**: diseño en curso; **nada construido ni desplegado** al escribir esto.
- **Qué decía DEC-183 (s301) y por qué se reabre**: «el lado servidor ya está construido y VIVO (vistas
  versionadas + `rag_trace`); el front son clicks en el dashboard de Supabase. Un panel web propio sería
  cambio de rumbo (auth + RGPD) y **hoy no paga**». Lo que ha cambiado desde entonces: (a) el piloto trae
  **varios usuarios** donde había uno; (b) hay **gestión** que antes no existía —generar, listar y revocar
  invitaciones, ver la allowlist— hoy sólo por CLI; (c) hay una **tabla de errores** nueva que mirar; (d) el
  destinatario del panel son **Directores Generales**, no el autor del sistema. El motivo del NO-GO (auth +
  RGPD) **sigue siendo cierto y sigue siendo el coste**: no desaparece, se acepta.
- **Decide (alcance v1, adjudicado por Alberto)**: **gestión + métricas**. Invitaciones (generar/listar/
  revocar), allowlist con ids y notas, las **7 vistas ya existentes** (`bot_health_daily`,
  `bot_health_semanal`, `bot_uso_por_canal`, `bot_feedback_semanal`, `bot_motivos_negativos`,
  `salud_canal_retrieval_v1`, `salud_latencia_etapas_v1`) y los errores agregados. **Fuera de v1**: leer las
  conversaciones de los DGs y marcar respuestas desde la web (es lo más útil para mejorar el bot y también
  lo más sensible; entra cuando el piloto lo pida y con su propia vuelta de RGPD).
- **Decide (secuencia, adjudicado por Alberto)**: **ANTES de invitar a nadie**. Consecuencia declarada y
  aceptada: el piloto se retrasa lo que tarde el panel, y el panel entra en el paquete del abogado.
- **Decisiones estructurales (mías, para que no las improvise quien construya)**:
  1. **Server-side, no SPA**: el panel renderiza en el servidor. Motivo: la clave de servicio de Supabase
     **jamás** puede viajar al navegador, y un front que llama a la base desde el cliente obliga a montar
     RLS por usuario para un panel de dos personas.
  2. **Un servicio más en Railway**, en este repo. Motivo: es donde ya vive el worker, comparte `.env` y
     despliegue, y no añade proveedor nuevo. El panel **no comparte proceso** con el bot: si el panel cae,
     el bot sigue.
  3. **La autenticación es una pieza ENCHUFABLE** detrás de una interfaz mínima. Motivo: el war room tiene
     login propio y todavía no sé si es reutilizable; v1 lleva su propia autenticación sólida (contraseña
     con hash fuerte, sesión en cookie firmada, sin secretos en el cliente) y el día que sepamos qué es el
     war room se sustituye el backend sin tocar el resto.
  4. **Sólo lectura salvo en gestión de acceso**: el panel puede emitir y revocar invitaciones, y revocar
     accesos. No edita corpus, ni catálogo, ni golds.
- **Riesgo declarado de entrada**: esto es **superficie nueva expuesta a internet con datos personales
  dentro** (ids de Telegram, notas con nombre y cargo, preguntas de los técnicos). Es exactamente el coste
  que DEC-183 no quiso pagar. Mitigaciones exigidas: sin acceso anónimo a nada, hash fuerte de contraseña,
  cookies de sesión firmadas y `Secure`, cabeceras de seguridad, y **entra en la matriz de retención y en el
  paquete del abogado** junto con el aviso v8.
- **Pendiente de Alberto**: qué es técnicamente el login del war room y si es alcanzable desde este proyecto.


## DEC-232 (s324f) — El atajo de catálogo respondía a otra pregunta y servía el 2,9 % del corpus: se corrige cambiando la FUENTE, se separa la intención, y toda respuesta que no quepa lo dice y ofrece cómo pedir el resto

- **Fecha**: 17 ago 2026. **Impacto**: MEDIO-ALTO en serving (routing + atajos). **Cableado**, con
  gate G1-G6 en `tests/test_s324f_catalogo_fabricantes.py`. **NO desplegado** (rama).
- **Cómo se descubrió, y esto importa más que el fallo**: el **primer smoke real del piloto**.
  Alberto encendió la puerta (`BOT_ALLOWLIST=on`), escribió «¿qué fabricantes tienes?» y el bot le
  respondió con **22 modelos de 756** (2,9 %) agrupados bajo `DESCARTADO`, `EN_unico`, `ES` y `PT`
  —etiquetas internas del proceso de ingesta— y **sin botones para puntuarlo**. Ninguna suite lo
  habría cazado: los tests congelaban esa conducta como correcta. Lo cazó un usuario en 30 segundos.
- **Las causas, medidas** (no estimadas): `limit=5000` que PostgREST corta en **1000 filas**, sin
  `ORDER BY` (qué 1000, arbitrario) · `r.get("category","General")` **no cubre `None`** y el
  `if model and cat` descarta **630 de esas 1000** · `category` contaminada con idioma y estado de
  proceso · la pregunta era por **fabricantes** y la ruta volcaba **modelos** · los atajos ni
  colgaban teclado ni guardaban `response`, así que el fallo era **invisible en las métricas**.
- **Decide (1) — CAMBIAR LA FUENTE, no subir el `limit`**: la respuesta sale de
  `get_manufacturers_by_docs()` (`documents` con `status=active`, paginado con orden estable), que
  **ya existía desde s307** y ya alimentaba la cabecera del bot. Es además la regla **r27 C1**
  («jamás los pm de chunks») que este atajo era el **último** en incumplir. Refuerzo: la lección
  del cap de 1000 estaba escrita **200 líneas antes en el mismo fichero** (`get_available_manufacturers`,
  con la historia de los smokes s21 y s65). No era una lección pendiente: era una función que
  nunca se migró.
- **Decide (2) — SEPARAR LA INTENCIÓN en el PLAN, no en el manejador**: `sujeto_es_marca()` en
  `turn_plan.py` decide `fabricantes` vs `catalogo`; el manejador sólo sirve. Regla de desempate
  declarada: si aparecen los dos sustantivos, **gana marcas** — es la respuesta que cabe entera.
- **Decide (3) — EL VOLCADO GLOBAL DESAPARECE**: 756 modelos no caben en Telegram (4.096 chars).
  Corrección tras el dúo: era **falso** escribir que «ninguna paginación lo arregla» —se puede
  repartir en ~8 mensajes—; la razón real es que **no conviene** y seguiría sin responder a lo
  preguntado. Ambas rutas sirven la lista de marcas; cambia el encabezado, que reconoce lo que
  preguntó cada uno.
- **Decide (4) — `src/bot/acotar.py`, adjudicación de Alberto**: «generalizable a preguntas en las
  que la respuesta no quepa […] además de incluir un mensaje de limitación […] para que el usuario
  lo entienda». La propiedad que lo hace un control y no un adorno: **el espacio del aviso se
  reserva ANTES de colocar ningún elemento**, así que es imposible recortar sin avisar — ni
  quedarse sin sitio justo para la línea que explica que no había sitio. Hoja pura, tres
  consumidores declarados.
- **Decide (5) — LOS ATAJOS, OBSERVABLES, con el orden invertido** (hallazgo del dúo): registrar
  **antes** de enviar, comprobar que la fila está confirmada, y sólo entonces colgar 👍/👎. Colgar
  el teclado sobre el orden anterior habría creado **FK colgantes** — contra lo que avisa el propio
  `log_query` en su documentación. Se guarda `response`: un 👎 sobre una respuesta que no está
  escrita en ninguna parte es un número, no una señal.
- **Decide (6) — ADJUDICACIÓN DE ALBERTO sobre marcas múltiples**: un producto vendido bajo varias
  marcas (**56 medidos**; `morley:vsn-4-plus` es Morley-IAS + Notifier + Vision) **aparece en
  todas** — el técnico busca por la marca que tiene delante en la instalación. **Matiz del autor,
  declarado como corrección de una premisa falsa que le di**: eso aplica a **buscar**, no a
  **listar**. Para listar se usan los nombres de `documents.manufacturer` (30, limpios) y no
  `vendido_bajo`, que trae **cinco grafías de Morley y un `unknown`**. Listar y buscar quieren
  fuentes distintas.
- **Defecto preexistente arreglado de paso**: `_CATALOG_PATTERNS` exigía la **tilde** («qué»), así
  que «que marcas tienes» —como se teclea en un móvil— caía al RAG completo. El patrón hermano del
  mismo fichero ya usaba `qu[eé]`: es aplicar su criterio, no inventar uno.
- **Dúo r39 (Sol xhigh + Fable 5, emparejados)**: 13 hallazgos, **ninguno dijo SÓLIDO**;
  11 confirmados, 1 falso positivo, 1 parcial. Los **dos de mayor severidad resultaron mecanismos
  reales con efecto MEDIDO CERO** (servibilidad: 7 productos de 1000 y **0 marcas**; tercera fuente
  sin filtro `status`: **0 marcas fantasma**) — se adoptan como guarda **declarando la medida**:
  adoptar un hallazgo no es obedecerlo. Fable sospechó que mi cifra «1000 productos» fuera el
  max-rows de PostgREST —es decir, que mi medición padeciera el bug que denuncio—: **falso
  positivo** (fichero: 1696 → 1011 activos → 1000 con docs), pero su exigencia de **declarar cómo
  se midió cada cifra** entra en la v2. Ambos cazaron la misma sobre-afirmación mía: «todos eran el
  mismo defecto» es falso, la intención mal clasificada y la falta de observabilidad no vienen de
  la fuente.
- **Alternativas descartadas**: subir el `limit`/paginar el escaneo de chunks (arregla el síntoma y
  deja la fuente equivocada; viola r27) · limpiar `category` y seguir usándola (trabajo de corpus,
  no hace falta para servir bien) · partir el catálogo en varios mensajes · `ORDER BY` y ya (corte
  determinista, igual de ciego) · vista/RPC con `DISTINCT` (migración + segunda fuente de verdad).
- **Deuda declarada con su medida**: `get_category_models` sigue truncado (4 categorías por encima
  de 1000) · `category` contaminada (15.619 chunks sin categoría, 60 %) · **tres** fuentes de
  «cuántos fabricantes» conviviendo (30 · 35 · 30) · el inglés no entra en el patrón de catálogo
  (`xfail(strict)` como trinquete) · `_get_source_files_for_model` pide 5000 y hoy ningún modelo
  llega a 1000 — **foto, no invariante** (Fable), queda con test-guarda porque el sesgo del
  diversify sería silencioso.
- **Recibos**: `evals/s324f_catalogo_propuesta_{v1,v2}.md` · tally r39 (ts=2026-08-17T19:18:19,
  `duo_status=adjudicado`) · gate en `tests/test_s324f_catalogo_fabricantes.py`.


## DEC-233 (s324f) — El piloto REAL rompió tres cosas en su primera hora, y ninguna la veía la suite: cuota confundida con saturación, marcas destrozadas por voz, y el panel rechazando su propio login

- **Fecha**: 17-18 ago 2026. **Impacto**: MEDIO-ALTO en serving + panel. **DESPLEGADO** (commit
  `5eda845`, verificado: bot arrancado con la puerta activa). Dúo r40. Suite **4373**.
- **La lección que ordena todo lo demás**: en la primera hora con usuarios de verdad —Alberto y
  Sara— aparecieron **cuatro defectos que 4.300 tests no veían**. Dos los destapó una persona
  usando el bot; dos, abrir el panel en un navegador. Ninguno era un caso raro: eran el camino
  normal. Es la segunda vez en el día (DEC-232 fue la primera) que el testigo útil es el uso real.
- **Decide (1) — EL 429 TIENE DOS CARAS**: Sara mandó un audio, OpenAI devolvió `insufficient_quota`
  («no credits remaining») y el bot le dijo que estaba **saturado** y que probara más tarde. No
  había congestión y reintentar no iba a funcionar nunca. Ahora se lee el TEXTO del error dentro
  del 429 —único sitio donde el proveedor lo dice— y la cuota es **no reintentable, crítica y con
  aviso al operador**. Causa raíz: la `OPENAI_API_KEY` de Railway era otra clave, de una cuenta sin
  saldo (verificado por huella, sin exponer valores; Anthropic y Voyage eran la misma y con saldo,
  o sea que el bot servía texto y no audio).
- **Decide (2) — EL AVISO VA A QUIEN PUEDE ARREGLARLO**: toda incidencia crítica manda un Telegram
  a los ids del bootstrap, **sin la consulta ni el autor**. Hasta hoy, el único camino por el que
  un fallo que sólo el operador puede resolver llegó a Alberto fue que Sara se lo contara. Con cota
  de una hora por clase+etapa+tipo, marcada **sólo tras entregar**.
- **Decide (3) — LAS MARCAS POR VOZ**: «Detnov» → «Death Knob», y el turno se quedó sin ancla.
  Medido y revelador: **«Detnov» YA ESTABA en el prompt de Whisper**, que además está **saturado
  (990/1000 chars)**. El prompt es una pista, no un diccionario: añadir los 30 fabricantes habría
  diluido más. Se corrige DESPUÉS, con tabla de confusiones **observadas** (hoy: una, con su cita).
- **Decide (4) — v9**: la mención a las transferencias fuera de la UE baja a `/privacidad`
  (decisión de Alberto). No desaparece —es obligatoria y cierta—; cambia dónde se lee, con un test
  cuyo único trabajo es separar «lo movimos» de «lo perdimos».
- **DÚO r40 — Sol 8/8 confirmados, 0 falsos positivos.** El mejor hallazgo movió una pieza entera:
  yo corregía la transcripción **en el borde**, y eso **rompía un contrato que ya estaba escrito en
  el código** («raw ASR stays visible and is logged unchanged»). Con mi versión, el técnico no podía
  detectar una corrección FALSA y el histórico mentía sobre lo que produjo Whisper. Movido a
  `normalize_voice_query`, que ya tenía ese contrato. También suyos: la cota marcada antes de
  entregar (una caída de Telegram dejaba al operador sin aviso Y silenciaba una hora), la clave sin
  `tipo_excepcion` (cuota y credenciales comparten clase y una silenciaba a la otra), y la 017 con
  `DROP`+`ADD` sueltos (podía dejar la columna sin vocabulario cerrado).
  **Fable NO emparejó**: modifiqué el worktree mientras corría —fallo de proceso mío, y el runner
  lo detectó y lo dijo en vez de fingir (control de #86 vivo)—. Su review standalone aportó dos
  correcciones aplicadas: la contradicción entre propuesta y código tras el arreglo de Sol, y que
  la señal `"billing"` era **demasiado ancha** (un 429 de congestión real enlaza a facturación: el
  falso positivo diría «no reintentes» ante algo que sí se arregla esperando).
- **EL PANEL, ABIERTO EN UN NAVEGADOR DE VERDAD** (lo pidió Alberto antes de desplegarlo):
  · **el login legítimo daba 403** — el formulario del propio panel no manda `Origin` (normal en
    same-origin) y `Referer` lo suprimía **su propia** cabecera `Referrer-Policy: no-referrer`: se
    saboteaba a sí mismo. Arreglado aceptando `Sec-Fetch-Site` —que escribe el navegador y no se
    puede falsificar desde otro sitio— y pasando la política a `same-origin`. **Ningún test lo veía
    porque todos mandaban `Origin` a mano**;
  · **la portada decía «0 errores»** la misma noche en que había dos, porque contaba la fuente
    HEREDADA (`query_logs`) en vez de `bot_errors`. El sitio donde uno mira primero daba el dato
    equivocado, que es peor que no dar ninguno.
- **El trinquete del RED LINE saltó solo**: la variable nueva de estado compartido puso la suite
  roja hasta declarar por qué su clave y su valor no dependen del usuario.
- **Alternativas descartadas**: distinguir la cuota por código HTTP (los dos son 429) · meter los
  30 fabricantes en el prompt (medido: ya estaba «Detnov» y el prompt está lleno) · reintentar la
  transcripción · avisar de todo fallo (ruido que se ignora) · usar ya la clase `cuota_agotada` (el
  CHECK la rechazaría y se perdería el registro) · quitar la mención a la UE (haría el aviso falso).
- **Pendiente de Alberto**: aplicar `migrations/017_bot_errores_clase_cuota.sql` —y **sólo
  entonces** cambiar la clase en el código; al revés se pierde el registro—, y un smoke de audio y
  del aviso al operador contra Telegram real, que es lo único que estos cambios no ejercitan.
- **Recibos**: `evals/s324f_lote_piloto_propuesta_v1.md` · tally r40 (ts=2026-08-17T23:22:28) ·
  `tests/test_s324f_cuota_agotada.py` · `tests/test_s324f_dashboard_rutas.py` (control de origen).

## DEC-221 (s325b) — El extraction store a la nube: consumo cloud SIN PC, con puerta única de consistencia; la INGESTA de manuales nuevos sigue siendo local (dúo NO SÓLIDO → rediseño)

- **Fecha**: 18 ago 2026 (s325b). **Impacto**: MEDIO en ZONA DE DOLOR (corpus/ingesta)
  ⇒ dúo COMPLETO (Sol xhigh + Fable), innegociable. Continúa DEC-220.
- **Mandato**: Alberto quiere usar el modo cloud **sin depender de tener el PC
  encendido**. Medido: de todo el corpus fuente, lo único que NO estaba ya en la nube
  era el **extraction store** — 1.143 JSON / 353,7 MB (`agent_anthropic-sonnet-45`) +
  28 / 2,6 MB (`llm`), solo en OneDrive. Los PDFs ya estaban (bucket `manuales`:
  1.007 objetos; 1.084/1.243 `documents` con `source_url`) por #69/DEC-199.
- **Cableado**: bucket **privado** `extraction` (`manuales` es público-por-URL porque
  el bot sirve esos PDFs; el store es derivado) · `scripts/upload_extraction_store.py`
  (dry-run por defecto, `--aplicar`, `--verificar`, recibo) ·
  `src/extraction_store.py` = resolutor **disco primero, bucket después** con cuatro
  operaciones (`listar`/`ruta_de`/`indice`/`buscar_por_sha`) y **fail-closed** en todo
  camino degradado · consumidores cableados: `enunciados_pass`, `s94_f1_generate`
  (el open REAL vive ahí), `src/reingest/pipeline.run`.
- **VERIFICADO (Protocolo 1, mismo turno)**: subida completa **1.143 + 28 objetos**,
  `--verificar` 0 fallos cruzando SHA · smoke del camino cloud contra el bucket REAL
  (sin disco): `listar()` 1.143 en 1,2 s · `_build_sha_map()` **1.136 claves, las
  MISMAS que desde disco**, en 0,5 s · `store_pages()` descarga y parsea. Equivalencia
  del mapa disco-vs-nuevo-código: **idénticos** (1.136/1.136).
- **El dúo cortó el diseño v1: NO SÓLIDO por ambos lados, con 3 críticos convergentes**
  (verificados contra el código antes de actuar, regla C):
  1. **Faltaba un consumidor entero**: `src/reingest/pipeline.py:223` lista el store
     con su propio glob — la propuesta hablaba de «tres consumidores» y eran cuatro.
  2. **`ingest_new` es PRODUCTOR, no solo lector** (`:378-404` escribe la extracción;
     `:182-205` exige PDFs y sidecar locales) ⇒ un resolutor de solo lectura no puede
     adaptarlo. **Consecuencia adjudicada por Alberto: se cierra en CONSUMO** y la
     ingesta de manuales nuevos sigue siendo local, declarado, no pendiente.
  3. **La «descarga perezosa» era falsa**: `enunciados_pass._build_sha_map` lee la
     cabecera de TODOS los JSON ⇒ el primer uso habría bajado los 1.143 objetos.
     Arreglo: el manifiesto lleva `source_path` y `sha_pdf`, y el índice sale de **un
     GET**. (Y el open real estaba en `s94_f1_generate._sha_path`, que busca por
     PATRÓN, no por nombre — de ahí `buscar_por_sha`.)
  Otros aplicados: el skip de la subida se decidía por **tamaño** mientras el
  manifiesto se regeneraba con el sha local (manifiesto que miente, `--verificar` en
  verde) → ahora se decide por **sha contra el manifiesto remoto**; la caché se indexa
  por sha (no por tamaño); `fallos` es por config; y un `StoreError` **aborta el
  tramo** en vez de contarse como error por-documento — sin eso, `derive_channels_lote`
  lo habría absorbido como el aviso esperable «doc sin store» (decisión del dúo s316
  contra la fatiga de alarma) y un lote podría cerrarse COMPLETO con la red caída.
- **Bug de plataforma cazado de paso**: `_build_sha_map` hacía `os.path.basename` sobre
  `source_path` de Windows; en Linux (que es donde corre una sesión cloud) eso NO
  separa por `\` y el mapa habría salido vacío **en silencio**. Ahora el basename es
  agnóstico de plataforma.
- **CONSISTENCIA — puerta única (petición de Alberto, 18-ago)**: el store tiene un
  solo productor, así que la publicación al bucket ocurre **en el mismo acto que la
  escritura** (`ingest_new` → `publicar_al_bucket`: sube el objeto y luego el
  manifiesto; ese orden deja «objeto sin registrar» ante un corte, nunca «registrado
  sin objeto»). **Fail-open declarado**: la extracción ya está en disco y cuesta
  dinero; el fallo queda anotado y `--verificar` lo caza. Las otras dos capas son red,
  no mecanismo: `--verificar` cruza **sha** (no tamaño), y **la `config` ES la versión
  del mecanismo de extracción** — cambiar de extractor es un prefijo nuevo, así que no
  puede producirse una mezcla silenciosa de extracciones viejas y nuevas.
- **Alternativas descartadas**: meter el store en git (354 MB clonados en cada sesión
  cloud); montar OneDrive en el VM (credenciales de Microsoft dentro del sandbox);
  regenerar la extracción en cloud (el store existe para no volver a pagarla);
  sincronizar el directorio entero al arrancar (no escala a 30+ fabricantes).
- **Gap declarado**: el emparejamiento del tally Sol↔Fable falló («no revisaron
  exactamente los mismos bytes ordenados») pese a correr sobre la misma propuesta;
  ambas revisiones existen y están archivadas, pero el log quedó sin emparejar.
- **Relacionado**: DEC-220 y su addendum · DEC-199 (#69, PDFs al bucket) · DEC-140
  (migraciones por MCP) · `docs/ENTORNO_CLOUD.md` §3.5 ·
  `evals/s325b_extraction_store_nube_propuesta.md` ·
  `evals/s325b_extraction_upload_v1.json` ·
  `evals/adversarial_reviews/2026-08-18T21-21-30_claude-fable-5_53e51e4dae75.md` ·
  `evals/adversarial_review_log.jsonl` (Sol ts=2026-08-18T21:18:48).

### DEC-221 addendum — RONDA 2 del dúo sobre el CÓDIGO: NO SÓLIDO otra vez, y cazó un bug que la suite no podía ver

La ronda 1 revisó el diseño; esta revisó el cableado. **Sol devolvió 4 críticos, todos
verificados contra el código y aplicados**:

1. **`NameError` en `src/reingest/pipeline.py`** (mío): al renombrar el universo de
   `files` a `nombres` dejé **cuatro** referencias huérfanas, y los caminos NORMALES
   (`dry_run`, `register_only`, `done`) reventaban — en algún caso después de escribir
   en DB. **La suite no lo cazó porque no existía ni un test que EJECUTARA `run()`**:
   ahora hay dos (`test_pipeline_run_recorre_el_store_resuelto_sin_romperse`, que
   recorre la rama procesada de verdad, y el de la guarda sin store). Es la lección
   más cara de la sesión: cablear un seam sin ejercitarlo end-to-end.
2. **La «puerta única» no era única**: `src/reingest/extract.py:179` es un SEGUNDO
   productor (json.dump + os.replace) y no publicaba ⇒ un reparseo volvía a divergir.
   Publica ya, con el mismo fail-open declarado.
3. **Sobrescritura destructiva del manifiesto**: `publicar_al_bucket` trataba
   CUALQUIER respuesta ≥400 del GET como «no hay manifiesto» y lo sobrescribía — un
   500 transitorio podía dejar el store con UNA entrada visible. Ahora solo un **404**
   significa vacío; el resto lanza. Y queda DECLARADO el límite: es read-modify-write
   **sin CAS** (Storage no lo ofrece), así que dos publicaciones concurrentes pueden
   perder una entrada; hoy no ocurre —`ingest_new` es proceso único— y la red es
   reconstruir el manifiesto con el script.
4. **No todo fallo de store era `StoreError`**: timeouts de `httpx` y JSON/UTF-8
   inválido escapaban con otro tipo, y el consumidor —que solo relanza `StoreError`—
   los degradaba a error por-documento, pudiendo cerrar el tramo con rc=0 con la red
   caída. Ahora transporte y parseo se envuelven.

**Medios aplicados**: `--verificar` era **circular** (comparaba el sha local contra el
que declara el propio manifiesto, generado de ese mismo local) ⇒ nace `--profundo`,
que DESCARGA y hashea el objeto — ejecutado sobre `llm`: 28/28 íntegros. Y el
fail-open de la publicación no llegaba al recibo ni se reintentaba al reanudar
(`out` ya existía ⇒ se saltaba la puerta entera) ⇒ la publicación salió del `if` y
`publicacion_fallida` viaja en los tres caminos del recibo.

**CORRECCIÓN de una afirmación mía**: donde este DEC decía «`--verificar` 0 fallos
cruzando SHA», lo medido era el sha contra el MANIFIESTO, no contra el objeto remoto.
La verificación real es `--profundo`, y hasta ahora solo se ha corrido entera sobre
`llm`; sobre `agent_anthropic-sonnet-45` (354 MB) queda pendiente.

**Declarados y NO resueltos** (van a la deuda, no al silencio): un directorio local
PARCIAL manda sobre el bucket sin contraste de conteo ni huella; el estado del
pipeline es global y no valida que su `config` coincida con la solicitada; y la caché
de descargas no tiene límite ni limpieza.

**Fable (mismo ronda 2, lado independiente): NO SÓLIDO por poco — ningún crítico**, y
tres medios que se cerraron antes de dar el cableado por zanjado:

- **Asimetría de comportamiento en LOCAL no declarada**: el índice del lado bucket se
  cachea (el manifiesto) pero el del lado disco NO, así que cada búsqueda fallida
  releía las cabeceras de los 1.143 ficheros — un lote con muchos misses salía O(n·m).
  Cacheado. Y de paso, el match EXACTO por `sha_pdf` pasa ANTES que el de prefijo de 12
  hex: si colisionaran, el prefijo ganaba por orden lexicográfico y devolvía el fichero
  equivocado.
- **Cabeceras nulas silenciosas, ahora HORNEADAS en el manifiesto**: `_cabecera` solo
  mira 600 bytes; si `source_path`/`sha256` cayeran más allá (p.ej. si un extractor
  futuro cambia el orden de claves), el manifiesto estampa `null` y `_build_sha_map`
  hacía `continue` sin avisar ⇒ documento invisible con `--verificar` en verde. Ahora
  se CUENTA y se declara en el recibo de subida y en consola. Hoy pasa con 1 de 1.143.
- **El fail-open no llegaba al exit**: dejarlo solo en el recibo devolvía el mecanismo
  a «que alguien se acuerde de leerlo», justo lo que la puerta única elimina. Ahora, al
  final del lote, se dice en la cara con el comando exacto de reparación (sin cortar el
  lote: la ingesta fue correcta; lo que falta es la copia de la nube).

Menores cerrados: `manifiesto_remoto` trataba cualquier ≥400 como «no hay manifiesto»
(un 500 producía 1.143 falsos DIFIERE o una re-subida entera) → ahora solo el 404
significa vacío. Menor NO cerrado, a deuda: la caché no purga versiones viejas (#80).

Nota de proceso: el emparejamiento del tally Sol↔Fable volvió a fallar por bytes
(«no revisaron exactamente los mismos bytes ordenados») pese a correr sobre el mismo
fichero de propuesta; ambas revisiones están archivadas en `evals/adversarial_reviews/`.
Ref ronda 2: Sol ts=2026-08-18T21:44:56 · Fable
`2026-08-18T21-54-44_claude-fable-5_a4a0aa0222c0.md` ·
propuesta `evals/s325b_cableado_revision_v2.md`.
## DEC-235 (s324h, 18 ago 2026) — La voz pasa por el plan: el default que mentía estaba SEIS veces (Fase 1 APLICADA, PR #284 mergeada)

**Síntoma** (piloto vivo, Alberto): «¿Qué centrales de Detnov tienes?» **por voz**, con la
transcripción YA correcta → «no he encontrado información relevante»; **tecleada** → el listado
de 14. Medido: las dos formas planifican `ruta='inventario'` idéntica. `handle_voice` nunca
llamaba a `plan_turn` — las **nueve** rutas de atajo eran inalcanzables hablando. Estaba
declarado en el código como aplazamiento de fase B del #70; el piloto lo volvió defecto.

**Causa**, y no era «la ruta que faltaba»: el mismo default optimista replicado SEIS veces —
`log_query`, `_process_query`, `TurnRequest`, `build_turn_request`, `Meta.fuente` y
`query_logs.source`. Un default sólo debe existir cuando el valor omitido es VERDAD; `"text"`
es la mitad de los casos, así que olvidar la procedencia no fallaba: registraba en silencio, y
para siempre, que un audio se había tecleado.

**Decisión**: `Procedencia` (canal + ASR crudo, invariante en `__post_init__`, sin default) como
origen único; `_servir_turno` como preludio compartido; frontera keyword-only sin default en el
despacho; y `_FUENTE_META` como mapa explícito (el `else "texto"` de la primera versión colapsaba
cualquier canal futuro — el defecto reintroducido en el propio arreglo).

**Alcance en DOS fases, declarado.** Fase 1 (aplicada) cierra lo ROTO. Fase 2 (pendiente):
`TurnRequest`, `build_turn_request` y la migración del esquema — mismo patrón donde HOY NO está
roto; meterla habría sido el cuarto ensanchamiento del lote.

**Alternativas descartadas**: (a) cablear sólo la ruta de inventario — el parche que Alberto ya
rechazó en la tabla de transcripción; (b) fabricar un Update de texto y delegar en
`handle_message` — pierde el ASR crudo y acopla por un objeto falsificado; (c) una frontera de
fail-open que degrade al RAG — **muerta dos veces por el dúo**: Sol por SEGURIDAD (saltarse
`mismatch`/`marca_no_servida` puede contestar con el manual de otra marca) y Fable por
OBSERVABILIDAD (convierte incidencias visibles en degradación muda); (d) `Entrada` como tipo
nuevo — sería un tercer vocabulario, `TurnRequest` ya lleva los campos.

**Restricción PAGADA retirada y declarada** (Sol fase-B M5): el `try/except` local de
`handle_voice`. Razón única: PARIDAD. La segunda razón que escribí —observabilidad— era FALSA y
Sol lo probó: `plan_turn` captura esa excepción en su fail-open MUDO, así que se pierde el
warning SIN ganar la incidencia. Declarado como deuda preexistente, no vendido como mejora.

**Puertas**: paridad 9 rutas × 2 canales (compara secuencia de mensajes y payload RAG, no sólo
la respuesta) · anti-vacuidad · no-regresión ×3 sobre la ruta conversacional · invariante de
`Procedencia` (8 estados inválidos) · AST que distingue pseudo-fuente de logging (`source="error"`)
de turno real. Verificado que el gate DISCRIMINA: antes de cablear fallaban 12 de 24.

**Proceso — 8 rondas de dúo** (Sol xhigh + Fable 5, más un refuerzo Opus 5 declarado). Tres
versiones tumbadas antes de cablear; una ronda más sobre el código. Evitó: una regresión del lever
de mismatch **en el camino de TEXTO**, la frontera insegura, un comentario con una afirmación
falsa, y filas de voz sin nada que auditar. Al extender el AST aparecieron **TRES** rutas clarify
perdiendo el ASR crudo, no dos: la tercera la encontró la PUERTA, no los revisores.

**Y lo que el dúo NO podía ver**: CI cazó que el gate llamaba a la red (`get_available_manufacturers`
sin fail-open). Pasaba en local por tener `.env`. Sol y Fable leen el código; no lo ejecutan sin
credenciales. **El entorno limpio es un revisor que ningún modelo sustituye.**

Suite: 4426 verde. Ref: `evals/s324h_voz_al_plan_propuesta_v5.md` + `s324h_v5_addendum_r48.md`,
tally en `evals/adversarial_review_log.jsonl` (r42–r49).

## DEC-236 (s324h, 18 ago 2026) — El runner de Fable ahogaba a su propio revisor (#86, diagnóstico MEDIDO)

En r43/r44 el runner marcó `tools_reales=0` y detectó **transcripción FABRICADA**. Dos hipótesis
mías murieron con sonda: NO era `tool_choice` (Fable llama a la herramienta sin él) y NO era
«opina a ciegas». **Causa medida**: el runner PEGA los ficheros semilla enteros — 191.576
caracteres en r45, con `telegram_bot.py` (145 KB) dentro. Con el código delante el modelo no
necesita tools; y cuando sí las usa, muere con «preflight conservador excede el presupuesto».

**Experimento controlado** (r46): mismo modelo, mismo prompt, sólo cambiando semillas.
191 KB → **0** tool-calls. 46 KB → **10** tool-calls, sin aviso `SIN_TOOLS`, revisión completa.

Consecuencias: el flag `SIN_TOOLS` de #86 etiqueta «a ciegas» algo que no lo está del todo
(falso positivo del guardarraíl); la transcripción fabricada SÍ es defecto real y grave. **Pin
adjudicado por Alberto (18-ago): Fable 5 sigue siendo el 2º revisor aunque comparta modelo con el
autor — el rol adversarial cambia la conducta, no sólo el modelo.** Arreglo pendiente: no pegar
ficheros de código enteros; dejar que las tools los lean (es lo que hace Sol).

## DEC-234 (s324h, 18 ago 2026) — El bake-off de ASR incumplió un gate vigente que no cité

`gpt-4o-transcribe` se recomendó y Alberto lo desplegó con un bake-off de **voz sintética y 8
marcas** (4/8 vs 7/8). Sol (r45) encontró el constraint que yo no cité: **migrar de ASR exige el
gate ciego con ≥30 audios reales estratificados** (`evals/voice_asr_model_selection_gate_v1.yaml`,
DECISIONS ~2256). El Protocolo 4 obliga a grep en DECISIONS antes de opinar sobre un lever, y no
lo hice. El cambio funciona y es reversible por variable de entorno; **el listón declarado sigue
sin cumplirse** y queda a decisión de Alberto recoger los 30 audios.

## DEC-237 (s324i, 18-19 ago 2026) — El panel a Vercel: (a2) adjudicado, diseño NO cableado tras DOS rondas NO SÓLIDO

**Adjudicado por Alberto**: subdominio `techassistant.fontiber.com`, y **(a2)** — la lista de
usuarios sale de las variables de entorno y pasa a Supabase. Eligió (a2) al conocer un dato que yo
le había vendido al revés: *«revocación en la siguiente petición»* era **falso**, porque
`DASHBOARD_USUARIOS` es variable de entorno y su cambio exige reinicio (`auth.py:233-236`) — en
Vercel, un redespliegue. **Mientras la lista viva en el entorno, revocar no puede ser más rápido
que un despliegue.**

**DECISIÓN: no se cabló.** Dos rondas del dúo, dos NO SÓLIDO. La v1 cayó con un crítico que
**cambió la decisión de Alberto** (la idempotencia que propuse era imposible: `gestion.py:16-24`
guarda sólo el SHA-256 y el enlace se enseña una vez). La v2 cayó con **tres**, dos de ellos
fallos de seguridad míos y verificados contra el código:

1. **Tabla de credenciales sin RLS/FORCE/REVOKE** — y el patrón YA estaba escrito en
   `migrations/016_allowlist_invitaciones.sql:266-292`. En `public`, PostgREST expondría usuarios
   y verificadores scrypt.
2. **`HMAC(usuario|ip)` fusiona dos claves que el cerrojo cuenta por SEPARADO** (`auth.py:363`
   devuelve `("u:…", "ip:…")`). Rotar IP → intentos ilimitados contra un usuario; rotar usuario →
   esquiva el límite por IP. Mi «sirve igual para contar» **debilitaba** el cerrojo mientras yo
   creía mejorar la privacidad.
3. **El contrato del digest `h` es irrealizable**: `vigente()` recibe un nombre y devuelve
   `Usuario(nombre)`, así que no puede crear ni comparar el digest sin volver a rodear `Backend`.

Más siete medios, entre ellos que un HMAC con clave conservada es **seudonimización** y
`docs/RGPD_RETENCION.md:67-75` ya rechaza ese framing; que incremento atómico ≠ admisión atómica;
y que PostgREST no puede expresar `fallos = fallos + 1` (haría falta una RPC).

**Motivo de no cablear**: el patrón de los tres críticos es «no vi un contrato que ya estaba
escrito en el repo», y esa clase de fallo empeora con contexto acumulado — no con más rondas en
la misma sesión. Es autenticación: el precio de equivocarse es una tabla de credenciales expuesta.

**Alternativas descartadas**: (a1) revalidar contra la variable de entorno → revocación «tras
redesplegar», no inmediata; leer el entorno desde `app.py` → rodea la interfaz enchufable de
DEC-231 e invalida el futuro backend del war room; fallback a la variable si Supabase cae →
reabre el agujero, quien tire la base recupera al usuario revocado; que el panel gestione usuarios
→ superficie nueva, el alta sigue siendo script + `INSERT`.

**Punto de partida de la sesión siguiente**: `evals/s324i_panel_vercel_propuesta_v2.md` (diseño
con la estructura correcta) + los diez defectos enumerados arriba. Traza:
`evals/adversarial_review_log.jsonl` (ts `2026-08-18T23:39:54` y `2026-08-18T23:50:06`).

**Nota de higiene**: al escribir esto se descubrió que `DECISIONS.md` tenía **11 números DEC
duplicados**. Los dos míos (s324h) se renumeraron a **DEC-235** (la voz al plan) y **DEC-236** (el
runner de Fable), con sus tres referencias actualizadas. Los **9 históricos** quedan declarados en
`TECH_DEBT`, sin renumerar: tocan referencias cruzadas antiguas y no es trabajo de esta sesión.

## DEC-238 (s325g, 19 ago 2026) — La instalación de deps cloud se muda al setup script del environment; el hook queda de fallback autosanador

**Decisión.** La instalación de dependencias de las sesiones cloud deja de pagar ~50 s en
cada VM nueva: se extrae a `.claude/hooks/install-deps.sh` (fichero ÚNICO, versionado; TRES cambios
declarados sobre el original: centinela→site-packages, indirección `TB_MARCA_DIR` para
dry-runs herméticos, y `cd` auto-raíz para invocarse desde clones distintos)
con dos llamadores — el **setup script del environment** (corre solo al construir la caché;
Anthropic hace snapshot del filesystem y las sesiones siguientes arrancan con las deps en
disco, ~7 días) y el **hook de SessionStart**, que la sigue corriendo en cada arranque como
fallback: con caché caliente es un no-op de ~3 s (medido); con caché fría/caducada o
requirements cambiados tras el snapshot, instala como siempre. **Peor caso** (afinado por el
hallazgo Fable de esta ronda): = comportamiento pre-s325g para todo módulo del sondeo del
centinela, que en s325g se completó con los críticos del smoke que faltaban (`dotenv`,
`openpyxl`) — un crítico import-roto TUMBA el sondeo y el hook reinstala por VM, como hoy.
El residuo declarado (dos formas): una corrupción que el sondeo no ve y que un pip fresco
arreglaría quedaba antes re-resuelta en cada VM y ahora viaja pinneada ~7 días; y el drift
de versiones sin pin (los `>=` de requirements) — antes cada VM resolvía a lo último y ahora
las resoluciones del build viajan congeladas la ventana (hallazgo Fable r3; probablemente
benigno: MÁS determinista, más cercano a cómo congela Railway un deploy). Se
acepta por improbable y porque el recibo del smoke la hace observable (check `deps_cache`:
marcador + atribución por el boot de la VM, añadido en s325g para que un setup que nunca
funciona no pase invisible). **Ronda 2 del revisor:** la huella del centinela incluye desde
r2 el PROPIO `install-deps.sh` — un cambio del script sin tocar requirements invalida el
marcador (sin eso quedaría snapshoteado ~7 días sin aplicarse, una regresión real vs hoy);
los marcadores de huellas viejas se limpian al estampar; y la atribución de `deps_cache`
compara mtime contra el arranque de la VM en vez de un umbral de edad (correcta también en
la sesión de build y si el restore reescribiera mtimes). Adjudicación de Alberto (s325g); revierte
el «se deja en el hook» de s325d, cuya objeción (duplicar lógica fuera del repo) se resuelve
dejando en el campo del environment SOLO un bloque mínimo que clona `main` con `--depth 1` e
invoca el script del repo (bloque canónico en `ENTORNO_CLOUD.md` §3.1).

**Motivo técnico no obvio.** El centinela de idempotencia (s323) se muda de `/tmp` a
**site-packages** (`sysconfig.get_paths()["purelib"]`): la caché es un snapshot del
FILESYSTEM y `/tmp` puede ser tmpfs — un marcador que no viaje con los paquetes haría
reinstalar en cada VM aunque el snapshot trajera todo instalado. En site-packages, marcador
y paquetes viven y mueren JUNTOS (cambia el python del contenedor → cambia purelib →
desaparecen ambos → reinstala). El bloque del setup clona él mismo porque la doc oficial
no garantiza que el clon de la sesión exista cuando corre, y va entero con fallback a
`exit 0` porque exit≠0 tumba el arranque de la sesión.

**Alternativas descartadas.** Pips pegados directamente en el campo (duplica los
workarounds s315 fuera del repo y diverge en silencio); quitar la instalación del hook
(sin fallback, un fallo del setup o un cambio de requirements rompe ~7 días de sesiones);
marcador en `$HOME` o `/tmp` (no acoplado a los paquetes / no garantizado en el snapshot);
detectar un clon existente en vez de clonar (camino condicional sobre un orden no
documentado; clonar siempre es determinista).

**Gaps declarados.** La atribución de `deps_cache` asume mtimes coherentes tras el restore y que `/proc/uptime` es de la VM, no de un host longevo (medido en la VM de s325g: uptime 0,52 h ≡ edad real del contenedor — procfs namespaced; re-contrastar en la primera VM con snapshot). El snapshot real y el `git clone` dentro del setup no son verificables
desde una sesión: se confirman en la primera VM nueva tras pegar el campo (esperado:
~77 s → ~30 s). Hasta que `install-deps.sh` esté en `main`, pegar el campo es inocuo pero
no hace nada útil. Ref: `evals/adversarial_review_log.jsonl` (Fable standalone, s325g, 3 rondas: NO SÓLIDO → NO SÓLIDO → **SÓLIDO**).

### DEC-238 addendum (s325h, 19-ago) — el instrumento mentía: `deps_cache` pasa de INFERIR a LEER un registro

**Lo que se rompió, medido.** La atribución por `mtime` vs `/proc/uptime` daba un FALSO
«vino del snapshot»: en una sesión de verificación el contenedor **se reinició** a mitad
(~14:02:53Z), el uptime se reseteó, y un marcador estampado en la propia VM (13:48:56Z) pasó
por heredado. El gap estaba declarado arriba («asume /proc/uptime de la VM … no
garantizados»), pero el dúo de s325g previó el *host longevo*, no el *reinicio*. El delator
fue la edad impresa: «0.0 días» para 17 minutos.

**El arreglo (adjudicado por Alberto).** `install-deps.sh` **apendiza** en cada corrida
`acción huella boot_id fecha` (`$TB_REGISTRO`, por defecto `/tmp/.technical_bot_deps_registro`);
`boot_id` viene de `/proc/sys/kernel/random/boot_id` y **cambia en un reinicio**. El smoke solo
lee las líneas de ESTE arranque y responde lo que importa —¿se pagó la instalación ahora?—
sin pronunciarse sobre el origen: `instalada` → «la caché no las traía»; solo `saltada` → «la
caché las trajo hechas»; sin líneas → **AVISO**, y nunca se nombra el snapshot. Se apendiza y
no se sobrescribe porque en un mismo arranque corren DOS llamadores (setup y hook): si el
segundo pisara al primero, «el setup instaló» se perdería y el ahorro parecería real.

**Principio que deja.** Un verificador puede decir «no lo sé»; lo que no puede es afirmar en
la dirección optimista lo que no ha medido. Cinco tests fijan el contrato, incluido el del
reinicio (líneas con otro `boot_id` no cuentan).

**Ronda 2 del revisor (4 hallazgos, los 4 aplicados).** (1) El check no filtraba por
HUELLA: si el instalador cambia a mitad de sesión —pasó aquí mismo, `663fae88`→`e28aecda`—
las líneas de la receta vieja contaban y el recibo hablaba de otra instalación; ahora se
descartan. (2) Nombraba el marcador sin comprobar que existe: ahora dice «SIN marcador
(huella)» cuando no está. (3) Los tests leían `/proc` sin guarda y habrían fallado en
Windows, superficie declarada en ese mismo fichero: van con `skipif`. (4) El gap decía que
la ausencia de `boot_id` degradaba a «desconocido», y eso solo pasaba en el shell; en Python
lanzaba excepción — ahora responde «sin /proc legible».

**Supuesto declarado NO medido** (Fable r2, honesto): que `boot_id` sea por-VM y cambie en un
reinicio. En un contenedor sin kernel propio sería del host, y en un restore con memoria
podría repetirse. Como segundo sello se anota el **uptime**, que solo crece dentro de un
arranque: una línea con uptime mayor que el actual se descarta aunque el `boot_id` coincida.
El reset de uptime observado en el incidente sugiere kernel por-VM, pero eso es inferencia,
no medición — y por eso se escribe aquí en vez de darse por bueno.

**Lo que este addendum NO resuelve, y sigue abierto:** si la caché del environment ahorra de
verdad. Las tres sesiones de prueba de s325h (creadas por API) **volvieron a construir la
caché en cada VM** — el Setup script se ejecuta y funciona (instaló y estampó en 104 s con el
repo sin clonar, luego el hook saltó), pero ninguna arrancó sobre un snapshot pre-horneado. Se
mide con una sesión abierta desde la UI: si el arranque baja a ~30 s y `deps_cache` dice «ya
estaban al arrancar», el mecanismo paga; si vuelve a instalar, DEC-238 no compra lo que
prometía y habrá que decidir si se revierte.

## DEC-239 (s324j, 19 ago 2026) — El diseño del panel a Vercel queda CERRADO en la v9 tras seis rondas del dúo; SÓLIDO-para-cablear, el GO es de Alberto

- **Fecha**: 19 ago 2026. **Impacto**: ALTO (autenticación de un servicio expuesto a internet).
  **Estado**: diseño CERRADO (`evals/s324i_panel_vercel_propuesta_v9.md`); **nada cableado ni
  desplegado** — ese era el mandato de DEC-237 y se cumplió.
- **Qué se hizo**: la v3 cerró los diez defectos de DEC-237 (verificados primero contra el código,
  no de memoria) y el dúo corrió SEIS rondas completas en la sesión (v3→v9; Sol xhigh agéntico +
  Fable emparejado con semilla mínima — lección DEC-236 — y presupuesto 600k tras morir un intento
  al default de 300k). **64 hallazgos, cada uno pasado por la regla C contra código/docs antes de
  actuar; 0 falsos positivos en las seis rondas.** Trayectoria: r1 = 3 críticos (el peor: mi
  contradicción interna §5↔§1.3, cazada por LOS DOS revisores) → desde r2, cero defectos de
  mecanismo → r6 = Fable **«SÓLIDO»** explícito (~30 anclas, cero desajustes) y Sol 5 medios, todos
  contrato-de-integración sobre código aún inexistente, cerrados en la v9.
- **Decisión 1 — cerrar las rondas de diseño** (regla F: decido yo y soy responsable): el
  guardarraíl anti-ritual manda no iterar por iterar; lo que Sol ataca desde r4 exige el DIFF real
  para ser verificable. El dúo VUELVE a correr al cablear, sobre el diff (Protocolo 3, ALTO,
  innegociable).
- **Decisión 2 — el diseño es SÓLIDO-para-cablear, y un SÓLIDO no es un GO** (DEC-173): cablear
  exige el GO explícito de Alberto. Gates previos a EXPONER, en la v9 §13: plazo
  `[DECIDIR: Alberto]` de `panel_usuarios` · panel dentro del paquete del abogado (DEC-231),
  nombrando el pendiente canónico de la purga 24m de `bot_invitaciones`/allowlist (adjudicada
  s324e, sin mecanismo) · medición XFF antes de encender la mitad `ip:` del cerrojo (hasta
  entonces esa clave NI CUENTA NI BLOQUEA — con IP compartida del proxy, 5 fallos = 429 global;
  r5/F5-M1).
- **Hallazgo LATENTE de hoy, fuera del panel** (r1/S-C1, verificado): anular una invitación está
  ROTA contra Supabase real — `gestion.py:271-273` firma en `nota` (dúo r41 de s324f) y la 016
  solo concede `UPDATE (canjeada_at, canjeada_por, revocada_at)` (016:321-322) → 42501. Un dúo
  arreglando un hallazgo (r41: «la anulación queda sin firmar») abrió otro que ningún test sin red
  puede ver. La 020 lo cierra de raíz (`revocada_por` + CHECK del patrón
  `bot_allowlist_revocacion_completa` + backfill) y nace la puerta 9-bis (toda columna escrita
  tiene su GRANT, cruzada estáticamente).
- **Alternativas descartadas** (las nuevas de la sesión; cada una con su porqué en la v9 §10):
  BEGIN/COMMIT dentro de las migraciones (la 016 lo prohíbe tras dos fallos reales — el cierre es
  el contrato de aplicación) · ampliar `rgpd_retencion_pasada` (su autocontrol afirma EXACTAMENTE
  4 tablas: se instancia el patrón en una función hermana diaria) · pepper dedicado para `K` ·
  cache del sello con TTL · PRG con canal flash · devolver el +1 en fallo parcial.
- **Método, para la traza**: la mecánica «un fichero de propuesta por versión + tabla
  defecto→cierre por ronda» mantuvo las seis rondas auditables; el coste total del dúo fue del
  orden de $15-25. El primer intento de Fable r3 murió por presupuesto (preflight tras 12 tools):
  `FABLE_REVIEW_MAX_TOTAL_TOKENS=600000` + 16 tools lo resolvió — DEC-236 sigue teniendo pendiente
  el arreglo de raíz en el runner (no pegar código como semilla).
- **Traza**: tallies `2026-08-19T07:50:18` · `08:06:55` · `08:19:51` · `08:34:58` · `08:48:06` ·
  `09:02:03` en `evals/adversarial_review_log.jsonl`, con `verdict_notes` de regla C punto por
  punto y los recibos apareados en `evals/adversarial_reviews/`.


## DEC-240 (s324j, 19 ago 2026) — El panel a Vercel: la v9 CABLEADA y verificada, con el dúo del diff INCOMPLETO por crédito agotado (no mergear aún)

- **Fecha**: 19 ago 2026. **Impacto**: ALTO (autenticación de un servicio expuesto). **Estado**:
  código cableado y verificado; **NO desplegado, NO mergeado** — el dúo formal en ALTO no está
  cerrado (ver abajo).
- **Qué se hizo**: se cableó el diseño de DEC-239 (`evals/s324i_panel_vercel_propuesta_v9.md`)
  pieza a pieza: migraciones `019` (tablas `panel_usuarios`/`panel_intentos` + ACL enumerada +
  RPC `panel_puerta` + hermana de retención diaria + postcondiciones + NOTIFY) y `020`
  (`op` + `revocada_por` + backfill + CHECK), `dashboard/cerrojo.py` (nuevo), sello +
  `IdentidadNoDisponible` + `BackendSupabase` + `validar_registro_estricto` en `auth.py`, la
  puerta con sello + 503 + `/salir` local en `app.py`, `DUPLICADO`/`op`/`revocada_por` en
  `gestion.py`, `scripts/s324j_panel_usuario.py`, el enchufe en `api/index.py`, y ~90 puertas de
  test nuevas + un gate de integración pg + su workflow.
- **Verificación (Protocolo 1)**: suite completa **4517 passed / 62 skipped / 2 xfailed**; el gate
  de integración `test_s324j_panel_pg.py` ejecutado contra un **PostgreSQL 17 REAL** (17/17,
  incluye la ráfaga concurrente de 12 hilos que admite exactamente `FALLOS_LIBRES+1`, el bypass
  del cap cerrado, la política-como-ventana, la 020 con backfill); s295 pg intacto (42/42).
- **El dúo del diff** (Protocolo 3, ALTO): el cross-model **Sol (GPT-5.6 xhigh) corrió CUATRO
  rondas** sobre el cableado y sus fixes, y cazó **un fallo de SEGURIDAD real** que ni el otro
  revisor ni yo habíamos visto en el cableado: `panel_puerta` sembraba una fila `u:` ANTES de
  comprobar el bloqueo, así que un atacante ya bloqueado por su clave `ip:` seguía inflando el cap
  (divergencia con el doble en memoria, que comprueba antes de sembrar). Se corrigió reordenando
  la RPC (check → poda → cap → conteo). Las demás rondas afinaron precisión de claims. **Dos de
  mis fixes fueron sobre-correcciones que Sol revirtió** (aceptar `'1 day'` en el autocontrol;
  quitar el trigger de `test_s295`).
- **Por qué NO se declara SÓLIDO ni se mergea** (crítico procedimental de Sol, verificado contra
  el canon): a partir de la 2ª ronda del diff, el **2º revisor frontera Anthropic** (Fable, y su
  fallback Opus) cae por **crédito agotado** de la cuenta (`400 credit balance too low`, verificado
  con sonda mínima). `docs/ADVERSARIAL_REVIEWER.md:80-92` es LITERAL: una credencial ausente deja
  `pending_fable` y **«no completa ni dispensa el dúo»**; y DEC-236 documenta el *ahogo por
  contexto* del runner, NO una dispensa por crédito — citarlo como precedente de dispensa fue un
  error mío que el adversarial cazó. En impacto ALTO el dúo es innegociable, así que **el cableado
  queda pendiente del 2º revisor** y no se mergea hasta cerrarlo.
- **Qué desbloquea el cierre**: recargar el crédito de Anthropic (acción de Alberto) y correr
  `scripts/adversarial_review_fable.py` sobre el diff del cableado, emparejado con las entradas Sol
  ya registradas. Si el 2º revisor vuelve limpio, el cableado queda listo para el GO de despliegue
  (que sigue siendo de Alberto, con los tres gates de exponer de la v9 §13: plazo de
  `panel_usuarios`, paquete del abogado, medición XFF antes de encender `ip:`).
- **Traza**: tallies `2026-08-19T10:45:38` · `11:10:01` · `11:34:33` · `11:51:49` en
  `evals/adversarial_review_log.jsonl` (con `verdict_notes` de regla C); recibos Sol en
  `evals/adversarial_reviews/`; el addendum de supersesión de §3.2 al final del eval v9.
