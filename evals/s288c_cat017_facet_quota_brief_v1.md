# s288c — Lever CUOTA POR FACETA en la composición del top-K servido (diana: cat017#4)

Estado: **PRE-DÚO**. Recon $0 hecho (lecturas de artefactos + 2 probes read-only a `chunks_v2`;
0 llamadas de modelo, 0 escrituras). Nada cableado. Este documento es lo que el dúo debe desafiar.

---

## 0. PRE-REGISTRO PREVIO DEL LEVER — **NO EXISTE**

Búsqueda exhaustiva en `evals/` + `docs/DECISIONS.md` + `docs/LEVER_DIGEST.md`:

| Lo que SÍ existe | Qué es | Por qué NO es este lever |
|---|---|---|
| `evals/s287_etapa2_design_brief_v1.md` §RECOMENDACIÓN pieza **3** (v1 L44-46; v2 L111) | Dos frases: «cuota por FACETA de la query (cat017: 2 verbos, monopolio del 1º). El eje canal está medido (DEC-099/101); el eje FACETA no. Más caro y especulativo → SOLO si 1+2 no mueven cat017; **pre-registrar antes**» | Es la CONDICIÓN de disparo, no el pre-registro. Sin objetivo/métrica, sin mecanismo, sin diff, sin gates. |
| `evals/s287_facet_lever_design_brief_v1.md` + `s287_facet_gates_v1/v2.json` | Lever de faceta **DEC-164b**: arquetipo `variant_differentiation` para abrir el gate `require_evidence_facet` de la lane structural (diana cat022) | **Otro lever, otro eje, otra diana.** Es *cobertura de arquetipo* para que una lane de APPEND dispare; no toca la composición del top-K. |
| `evals/s273_quota_prereg_v1/v2/v3.yaml` | Cuota del **canal enunciados** (fusión carve-out) | Eje CANAL, CERRADO PERMANENTE (ver §6). |
| `evals/s288_taxonomy_lever_design_brief_v1.md` / DEC-166 | Ontología v4/v5 para la lane hyq | Eje ontología de lane, no composición. |

**Conclusión: la condición del pre-registro ha disparado (piezas 1+2 de etapa 2 ejecutadas,
cat017#4 sigue estable) y el pre-registro que exigía la pieza 3 es ESTE documento.**

---

## 1. OBJETIVO + MÉTRICA

**OBJETIVO.** Convertir **cat017#4 «CLSS»** (rerank-miss ESTABLE N=2) sin regresión en la cohorte
protegida, y hacerlo por una regla de **CLASE** (queries multi-faceta), no por una regla que
reconozca cat017.

**MÉTRICA (una sola, declarada de entrada).** `conveyed` a nivel-HECHO del instrumento
`scripts/factlevel_assessment.py` v3.x — la misma vara de la campaña (DEC-163). **Con N-reps.**
`DEC-096b`: el LLM-rerank **no es determinista a temp=0** → todo A/B es OFF-vs-OFF o N≥2 reps;
un flip single-run NO acredita ni condena.

**COHORTE PROTEGIDA (derivada, no citada de memoria).**
- Global: **93 OK-estables-N2** = intersección de `OK` entre `s100_factlevel_full_v3_20260729`
  (OK 101) y `..._20260730` (OK 98) — norma de la §RÉPLICA de `s287_etapa2_design_brief_v1.md` v2.
- **Concentrada (la que de verdad arriesga este lever): 14 hechos OK-estables DENTRO de la clase
  tocada** — cat001 ×5, cat008 ×3, cat012 ×4, cat017 ×2. Ver §4. Regresión en cualquiera de
  esos 14 pesa MÁS que en el resto: son los que el mecanismo puede tocar por construcción.

**Criterio de decisión.** GO exige: cat017#4 conveyed en **K≥2/2 reps** + **0 regresiones reales**
en los 14 concentrados + **0 regresiones reales** en los 93 (regla H6 de s287 v3: un flip en la
cohorte → re-run de confirmación antes de declarar regresión; y regla-C de DEC-092b: no se declara
regresión REAL sin LEER la respuesta).

---

## 2. RECON — el estado de cat017#4 y el mecanismo REAL (todo anclado)

### 2.1 Estado v3, idéntico en los dos runs (= diana estructural)
```
cat017#4 «CLSS»  ·  clase = rerank-miss  ·  submotivo = lexical-distractor
n_support_fam 4 · n_support_raw 4 · n_support_served 0 · reaches_gen False
in_pool True · in_topk False · best_pool_rank 4  (0-indexed → 5º chunk del pool)
support_l1_killed 6 ids · support_toc_killed 2 ids
```
Fuente: `evals/s100_factlevel_full_v3_20260729.yaml` y `..._20260730.yaml`, `per_gold[qid=cat017]`.
`submotivo_rerank` (scripts/factlevel_assessment.py:304-305) = `lexical-distractor` porque
`best_pool_rank(4) < RERANK_TOP_K(10)`: **el soporte está en el 5º puesto del pool y el reranker
no lo mete en 10 slots.** No es un problema de recall del canal.

Contexto del gold (cat017, `estrato: ['multi-doc']`): la pregunta tiene DOS verbos —
*«¿Cómo se **cablea** y se **da de alta (configura)** un lazo en la INSPIRE E10/E15?»* — y el gold
lo declara explícitamente: cableado/pinout vive en HOP-138-**9** (instalación); AUTO CONFIGURACIÓN
+ Programa CLSS viven en HOP-138-**8** (puesta en marcha).

### 2.2 Composición REAL del top-10 servido (probe read-only, $0, run 0729)
| slot | source_file | pág | sección | sub-intención |
|---|---|---|---|---|
| 0 | HOP-138-8ES | 12 | CABLEADO DE LAZO | cablear |
| 1 | HOP-138-9ES | 47 | MÓDULO DE LAZO (OPAL X 2) | cablear |
| 2 | HOP-138-8ES | 51 | IDENTIFICACIONES DE TERMINALES DE MÓDULOS | cablear |
| 3 | 4188-1132-ES (CLSS-10 Qref) | 5 | PASO 3 | *ambigua* |
| 4 | HOP-138-8ES | 7 | Circuitos de lazo | cablear |
| 5 | HOP-138-8ES | 8 | Pruebas de cableado de lazo | cablear |
| 6 | HOP-138-8ES | 10 | Pruebas de cableado de lazo | cablear |
| 7 | HOP-138-8ES | 10 | *(sin sección)* | cablear |
| 8 | HOP-138-8ES | 9 | Comprobaciones de lazo con multímetro | cablear |
| 9 | HOP-138-8ES | 15 | Configuración inicial y primer encendido | dar de alta |

Distribución por fichero: **HOP-138-8ES 8 · HOP-138-9ES 1 · 4188-1132-ES 1**.

**Los 2 soportes vivos de #4 (identificados en el probe, NO servidos):**
- `b7633e98` HOP-138-8 **p5** «Comprobaciones preliminares» → *«01 En el portal en la nube de CLSS
  Gestión de Clientes, cree un sitio/edificio y añada una central…»* = literal de la cita del gold.
- `5225b248` HOP-138-8 **p17** «Programa de Configuración de CLSS» (la cita del gold dice p18).

### 2.3 VEREDICTO SOBRE LA HIPÓTESIS PRE-CONCEBIDA: **confirmada en su núcleo, MAL ATRIBUIDA en su eje**

- ✅ **CONFIRMADO** el «8/10 al primer verbo»: 8 slots claros de cableado/pruebas-de-cableado
  (9 si se cuenta el slot 7 sin sección), **1 solo slot** de la 2ª sub-intención (p15) y 1 ambiguo.
  La atribución TOC de DEC-096 sigue STALE (ningún ÍNDICE en el top-10; el `7a09deff` p2 aparece
  como `support_toc_killed`, no como slot servido).
- ⚠️ **REFINACIÓN CRÍTICA que el diagnóstico de s287 NO tenía: el monopolio es INTRA-DOCUMENTO.**
  8 de los 10 slots vienen de **HOP-138-8ES**, que es el manual **de la segunda** sub-intención.
  **Consecuencia dura:** cualquier cuota keyed por `source_file`/`document_id` — la implementación
  barata y obvia, y exactamente lo que `_diversify_by_source_file` (retriever.py:2529, cap real
  `max(2, 50//3)=16`) ya hace a nivel POOL — es **NO-OP para cat017**. Si el lever se construye
  sobre el eje documento, no puede funcionar y el gate lo destaparía tarde.
  **El eje tiene que ser SEMÁNTICO (faceta), no documental.** Esto ratifica la elección del lever
  y a la vez mata su implementación más probable.
- ⚠️ **Segunda refinación:** el fallo no es solo de #4. En r2, **cat017#3** («Auto Configuración»,
  la otra pieza de la 2ª sub-intención) también cae a rerank-miss (`pos-buried`, rank 19); en r1
  se salvó por un APPEND de la lane structural. Es decir: **la 2ª sub-intención entera está
  desabastecida**, y #4 es la parte estable de ese desabastecimiento. El lever se formula sobre la
  sub-intención, no sobre el hecho.

### 2.4 Qué ontología puede alimentar la cuota — **v4 NO PUEDE; solo v5**

Sweep $0 de `expand_query_facets` sobre las 39 dev (`scripts.gold_store.verified()`; held-out
NUNCA tocado — `verified()` devuelve 39 filas, todas `split='dev'`):

| config | cat017 | ¿ve la 2ª faceta? |
|---|---|---|
| `retrieval_facets_v3.yaml` | `connect_install_wire` | NO |
| `retrieval_facets_v4.yaml` (la que adoptó la lane hyq, DEC-166) | `connect_install_wire` | **NO** |
| `retrieval_facets_v5_document_local.yaml` (`multi_match=True`) | **`['connect_install_wire', 'commissioning_setup']`** | **SÍ** |

**Por qué v4 no puede, estructuralmente** (no es una preferencia): `src/rag/query_facets.py:23-28`
declara v1..v4 en `FIRST_MATCH_SCHEMAS` y `:119-122` **lanza `RuntimeError`** si un consumidor
first-match carga un schema multi-match, y al revés. `MULTI_MATCH_MAX=2` está pineado en código
(`:30`), no libre en config. La única ontología que puede nombrar dos sub-intenciones es la v5.
Y su arquetipo `commissioning_setup` genera exactamente el `need`
**«… sitio edificio licencia bin alta portal»** — que es, literalmente, el hecho cat017#4.

⛔ **TRAMPA F1 DE s287 REPRODUCIDA — declarada de entrada:** `commissioning_setup` **NO tiene
gemela** en `config/evidence_coverage_facets_v5.yaml` (9 arquetipos: intrinsic_safety,
loop_eol_topology, compatibility, replace_without_loss, connect_install_wire, battery_sizing,
capacity_quantity, fault_reset_recovery, program_delay_cause_effect — **falta
commissioning_setup**). Si el test de pertenencia-a-faceta de la cuota pasa por la gemela de
evidence, la cuota es **NO-OP para cat017** por el mismo mecanismo fail-closed que el dúo de s287
cazó como F1-crítico. **Decisión a pre-registrar en §3.**

### 2.5 La vía de APPEND ya existe, está ENCENDIDA, y no basta
- El perfil medido es `coverage_c1_v4` (manifest de ambos runs) → `_C1_V4_ENABLED_FLAGS =
  frozenset(PROFILE_OWNED_FLAGS)` (release_profiles.py:66) → **`DOCUMENT_LOCAL_SELECTION_V2` ON**,
  y con él la «vía complementaria por-faceta» de s279 compuerta 2
  (`post_rerank_coverage.py:915-1400`, `_build_document_local_query_plan_v5` en
  `document_local_coverage.py:551-605` — que YA consume v5 con `multi_match=True`).
- Aun así, cat017#4 no se sirve, y los appends que sí llegan son de otras lanes
  (`same_blob_structural_neighbor_coverage_v1` ×2 + `obligation_warning_reserve_v1` ×1).
- **El presupuesto de append está casi saturado:** `MAX_COVERAGE_APPEND_ROWS = 4`
  (`serving_pipeline.py:18`) y cat017 consume **3/4 en AMBOS runs**. Queda 1 slot.

Esto es lo que justifica que el lever sea de **COMPOSICIÓN** y no «una lane de append más»:
la vía append está encendida, es de 1 fila con presupuesto propio, y ya está al 75% de tope.
**Pero es una justificación que hay que MEDIR, no asumir → gate-0 en §5.**

---

## 3. MECANISMO PROPUESTO (mínimo, default-off, byte-inerte)

**Regla (una frase).** Cuando la query activa **≥2 arquetipos** bajo la ontología v5 multi-match,
**reservar ≥1 slot del top-K servido para la faceta SECUNDARIA**, tomándolo del mejor candidato del
pool que pertenezca a esa faceta y desplazando al slot de MENOR rango del top-K que pertenezca a la
faceta PRIMARIA sobre-representada.

**Lo que la regla NO hace (frontera con los settled de §6):** no re-puntúa, no re-ordena por score,
no toca el prompt ni la ventana del reranker, no altera el pool ni su recuperación, no añade filas
(el top-K sigue siendo K). **Cambia QUIÉN ocupa los K slots, no cómo se puntúan.**

**Parametrización mínima (pineada en código, no libre en config — patrón `MULTI_MATCH_MAX`):**
| Parámetro | Valor | Por qué pineado |
|---|---|---|
| `q` (slots reservados por faceta secundaria) | **1** | El mínimo que puede convertir; libre en config invita a tunear contra el gold. |
| nº de facetas consideradas | **2** (= `MULTI_MATCH_MAX`) | Heredado, no re-elegido. |
| disparo | solo si `len(archetypes) ≥ 2` | Fuera de la clase, camino **byte-idéntico**. |
| candidato entrante | mejor rango de pool que pase el test de faceta secundaria y no esté ya en el top-K | Determinista. |
| slot saliente | el de MENOR rango de la faceta primaria; **nunca** una fila marcada `_hyq_boosted` / `_enun_quota` / `_hyq_surrogate` / `_swapped_from_surrogate` | Respeta los carve-out ya medidos (DEC-099 §1.1c; F8 de s287) — la cuota nueva no se come la cuota vieja. |
| flag | `FACET_SLOT_QUOTA` (`_strict_on_off`, config.py:115) **default off** | Off ⇒ ni se alcanza la rama. |

**Test de pertenencia-a-faceta — FORK A PRE-REGISTRAR (el dúo decide, no yo a posteriori):**
- **(A) vía `needs` de la retrieval-v5**: usar los términos del `need` del arquetipo secundario
  («sitio edificio licencia bin alta portal») como test léxico sobre el chunk. Vivo para cat017.
  Coste: mecanismo NUEVO sin attestation; el dúo lo atacará por ahí (con razón).
- **(B) vía gemela `evidence_coverage_facets_v5`**: reusa maquinaria atestada existente.
  **NO-OP MEDIDO para cat017** (§2.4: no hay entrada `commissioning_setup`) salvo que se autore la
  gemela — y autorar ontología es exactamente lo que el dúo de s288b **tumbó** (DEC-166: «prior-art
  v4/v5 existía»).
- **Recomendación del autor: (A), con el `need` como vocabulario y la traza del término que casó
  guardada en la fila** (`_facet_quota_swapped_in` + término), para que el gate pueda auditar por
  qué entró cada fila. **(B) queda declarado como la alternativa "más BP en forma" que hoy es
  NO-OP en los hechos.** Si el dúo prefiere (B), el lever pasa a exigir una entrada de ontología
  nueva y su propio anti-overfit — es un lever más caro, no el mismo.

**Punto de inserción — `src/rag/serving_pipeline.py`, ENTRE la línea 56 y la 61:**
```
:49  retrieved = adapters.retrieve(...)
:50  retrieval_pool = list(retrieved)          <-- el pool completo YA está aquí
:51-56  reranked = adapters.rerank(query, retrieved, top_k=rerank_top_k, ...)
        ◀◀◀ AQUÍ: reranked = apply_facet_slot_quota(query, reranked, retrieval_pool)
:61  protected_prefix = copy.deepcopy(reranked)
```
**Por qué AQUÍ y no en otro sitio:**
- Es el **único seam de serving**: `execute_rag_turn` lo cruzan el handler de Telegram, `bvg`
  (`test_bot_vs_gold.py`) y el instrumento factlevel (`factlevel_assessment.py:156,364`). Un punto
  → prod y los tres gates se miden sobre lo mismo.
- El invariante de prefijo protegido (`:88-93`: coverage no puede quitar/reordenar el prefijo) queda
  **intacto por construcción**: la cuota corre ANTES de que el prefijo se congele.
- **NO en `reranker.rerank`** (reranker.py:252-273): ahí lo consumirían también
  `bvg_kmajority.py:291`, `s101_*`, `audit_retrieval_funnel.py` y los replays de contexto congelado
  → rompería instrumentos históricos, y además confundiría la frontera con «afinar el reranker»
  (NO-GO DEC-092). La cuota debe verse, y medirse, como composición externa al ranker.

**COSTE ESTRUCTURAL DECLARADO (no descubrirlo en el build):** `src/rag/serving_pipeline.py` es
raíz del freeze-contract del instrumento (`factlevel_assessment.py:977 _SEAM_ROOTS`) **y** está
pineado en los recibos C1 (`s277_c1_p1.py:335/374/388`, `s277_c1_live_reachability_probe.py:42`,
`s277_document_local_coverage_probe.py:50`). Tocarlo ⇒ **serie nueva de `pipe_sha`** + re-anclado
de recibos. Es exactamente el coste que s287 v2 §F10 ya declaró para etapa 2; no es sorpresa, pero
tampoco es gratis y va en la cuenta del lever.

---

## 4. DIFF ESPERADO — PRE-REGISTRADO (fuente: `scripts.gold_store.verified()`, 39 dev, held-out embargado)

**La clase = queries con ≥2 arquetipos bajo `retrieval_facets_v5_document_local` multi-match.
Son 4/39, y son estas exactamente:**

| qid | arquetipos v5 | estado r1 / r2 | rol en el gate |
|---|---|---|---|
| **cat001** | `capacity_quantity` + `connect_install_wire` | 6 OK / 5 OK +1 synth-miss | **CONTROL**: 5 OK-estables protegidos; cat001#1 es flippy (fuera de cohorte) |
| **cat008** | `loop_eol_topology` + `connect_install_wire` | 3 OK +1 retr-miss / 3 OK +1 synth-miss | **CONTROL**: 3 OK-estables protegidos; #3 miss inestable (no es diana) |
| **cat012** | `capacity_quantity` + `battery_sizing` | 4 OK / 4 OK | **CONTROL PURO**: 4/4 OK-estables, nada que ganar y todo que perder |
| **cat017** | `connect_install_wire` + `commissioning_setup` | #4 rerank-miss / #4 rerank-miss | **DIANA** |

**Contrato del diff (patrón F2 de s287, con su enmienda como precedente):**
- La composición del top-10 puede cambiar **SOLO** en {cat001, cat008, cat012, cat017}.
- **Cualquier 5ª query cuya composición cambie = STOP**, sin racionalización post-hoc.
- **Cualquier regresión en cat012 = STOP del lever** (es el control puro de la clase, 4/4 OK).
  Precedente explícito: cat005 en `s287_facet_lever_design_brief_v1.md` §ENMIENDA.
- Las 35 restantes deben ser **byte-idénticas** en composición (el flag no dispara).
- Nota honesta: los otros 3 rerank-miss estables de la campaña (**cat010#0, hp018#1, hp018#4**)
  están **FUERA de la clase** (cat010 → `intrinsic_safety` single; hp018 → `connect_install_wire`
  single). **Este lever no los toca, y no se le pedirá que los toque.**

---

## 5. GATES (en orden; $0 primero, dinero al final)

**Gate 0 — $0, ANTES de escribir la primera línea de la cuota.** Falsar la premisa de §2.5:
correr la lane por-faceta de s279 sobre cat017 con traza completa y responder *¿por qué no sirvió
`b7633e98`/`5225b248`?* (¿no disparó? ¿disparó y no seleccionó? ¿presupuesto consumido?).
**Si la respuesta es «el presupuesto de append lo bloqueó», el lever BARATO es subir/ordenar ese
presupuesto, no una cuota nueva → se re-diseña.** Este gate puede matar el lever entero por $0.

**Gate 1 — $0, determinista.** `expand_query_facets` ×39 bajo v5 multi-match: el conjunto de
queries con ≥2 arquetipos debe ser **exactamente {cat001, cat008, cat012, cat017}**
(ya verificado hoy — se re-corre en el build como aserción, no como descubrimiento).

**Gate 2 — $0.** Probe de composición del top-10 de **cat017 antes/después** con pool congelado
(mismos ids de pool, cuota OFF vs ON aplicada offline sobre el mismo `reranked`): el swap debe
meter `b7633e98` o `5225b248` y sacar un slot de cableado, **sin tocar `f0dc41c3`** (p47, soporte
de cat017#0/#1 — si la cuota se lo come, convierte #4 y rompe #0/#1: **eso es STOP, no un trade**).

**Gate 3 — $0, judge-free.** Sweep-39 de composición (patrón `s287_p1_sweep39_composicion_v1.json`):
composición byte-idéntica en las 35 fuera de clase; cambios solo en las 4; ninguna fila con marca
de carve-out desplazada. Suelo de ruido con réplica del mismo brazo (el churn del pool existe:
`replica_identica_mismo_brazo=false` en ese mismo artefacto para cat017).

**Gate 4 — inertness.** Flag OFF ⇒ `reranked` byte-idéntico; suite completa verde; configs sin
editar (SHA a SHA).

**Gate 5 — ~$3, dirigido, SOLO las 4 tocadas.** `factlevel` en modo dirigido con **K≥2 reps por
brazo** sobre {cat001, cat008, cat012, cat017} = 19 hechos. Coste ≈ 4 queries × 2 reps × 2 brazos.
Criterio: cat017#4 conveyed 2/2 · los 14 OK-estables de la clase intactos · cat012 4/4.

**Gate 6 — solo si 0-5 pasan.** Los 93 OK-estables (full o subconjunto argumentado), con la regla
H6 (flip → re-run de confirmación) y la regla-C de DEC-092b (leer la respuesta antes de llamar
regresión).

**Centinela conductual obligatorio: hp009.** Es el centinela histórico de la clase
«el mecanismo cambia la CONDUCTA de la respuesta» (clarify-vs-answer; DEC-097/DEC-091, regresión
intermitente 1/2 ya medida). Va en gate 5, no en la fe.

---

## 6. ALTERNATIVAS DESCARTADAS — con la MÉTRICA de cada settled (disciplina del digest)

| Alternativa | Veredicto vigente + **su métrica** | Por qué no re-litiga con esto |
|---|---|---|
| **Afinar el reranker** (prompt, modelo, ventana, CE, RRF) | **NO-GO, DEC-092** · métrica = **retrieval-miss 39 dev + smoke e2e**, 6 métodos, todos ≤ baseline 13 | La cuota **no puntúa nada**. Opera sobre qué slots se sirven dado el orden que el reranker ya produjo. Frontera explícita. |
| **Ancho de ventana (RERANK_TOP_K)** | **YA SHIPPEADO top-10, DEC-092b** · métrica = servido-a-síntesis live, +5 chunks-respuesta, 0 regresión | No se propone ampliar K. K sigue 10; cambia la ocupación, no el tamaño. Ampliar K sería re-jugar un lever ya cobrado. |
| **tie-break coseno / diversify** | **CERRADO, s101 / DEC-091b** · métrica = **retrieval-miss famtie + centinela hp001 a nivel-hecho**, tripwire dispara con ambos anchos | El tie-break re-ORDENA por score y hereda el gap de vocabulario. La cuota no ordena: reserva. Ejes distintos. |
| **demote-TOC** | **NO-GO, DEC-096** · métrica = **proxy léxico servido sobre pools congelados** (evidencia negativa fuerte, no absoluta) | Además **stale para cat017**: medido hoy, no hay ningún ÍNDICE en su top-10. |
| **`_diversify_by_source_file` / cuota por fichero** | **Falsificado como punto de muerte, DEC-164(a)** · métrica = auditoría de trazas v3 + sondas ($0) | Y **medido hoy como NO-OP para cat017**: 8/10 slots son del MISMO fichero que la faceta desabastecida (§2.3). |
| **Cuota del canal enunciados / carve-out de canal** | **CERRADO PERMANENTE, S273/DEC-132b** · métrica = **árbitro pareado a nivel RESPUESTA (v3b): STOP**, hp005#2 3/3→0/3 | Eje **CANAL** (de dónde viene la fila). Este lever es eje **FACETA** (de qué sub-pregunta habla). Y la lección aplica como RIESGO, no como veto: *el desplazamiento cuesta hechos reales* → por eso `q=1` y por eso el gate 2 protege `f0dc41c3` explícitamente. |
| **Otra lane de APPEND por faceta** | Prior art **ya construida y ENCENDIDA** (s279 compuerta 2, perfil `coverage_c1_v4`) | Presupuesto 4 filas, cat017 usa 3/4. Es el gate 0: si ahí está el cuello, se arregla ahí y este lever muere barato. |
| **Autorar `commissioning_setup` en `evidence_coverage_facets_v5`** | El dúo de **s288b tumbó autorar** (DEC-166: prior-art existía) | Se declara como fork (B) de §3, con su coste propio, no se cuela dentro de este lever. |
| **Re-escribir la query en 2 sub-queries y fusionar** | Sin métrica propia; toca recuperación | Es un lever de RETRIEVAL (otro presupuesto, otro pool, otra latencia), no de composición. Fuera de alcance declarado. |

---

## 7. RIESGOS DECLARADOS (de entrada, sin esperar pushback)

1. **ANTI-OVERFIT — el riesgo principal.** cat017 es **1 gold**, y la conversión de **1 hecho**.
   Mitigación estructural, no de fuerza de voluntad: (a) el disparo es la **CLASE** («≥2 arquetipos
   bajo v5»), definida por una ontología que **ya existía y no se toca**; (b) el diff está
   pre-registrado a 4 queries **antes** de medir; (c) `q=1` y `MULTI_MATCH_MAX=2` pineados en
   código; (d) precedente vinculante: en s287 el gate paró con `{cat005,cat022}` vs `{cat022}` y la
   respuesta correcta fue **re-sellar el pre-registro**, no estrechar el trigger. Si aquí aparece
   una 5ª query, se para y se adjudica; no se recorta el mecanismo para que el diff cuadre.
2. **El lever puede ser NO-OP** por el fork (B)/trampa F1 (§2.4), o porque el chunk que entre por
   la cuota no sea el que porta el valor. Se declara ANTES: el gate 2 lo destapa por $0.
3. **Coste en hechos por desplazamiento** — la lección S273/DEC-132b es transferible aunque el eje
   sea otro: sacar un slot cuesta. Los 14 OK-estables de la clase son la superficie exacta y el
   gate 5 los mide con K-reps; `f0dc41c3` (p47) tiene protección nominal en el gate 2.
4. **Ruido del instrumento.** 15 flips entre r1 y r2 con el mismo código. Sin K-reps, este lever es
   inmedible. Ninguna declaración single-run.
5. **Sellos/recibos**: serie nueva de `pipe_sha` + re-anclado C1 (§3). Contabilizado.
6. **Acoplamiento de config compartida**: el fichero v5 pasaría a tener **2 consumidores**
   (`document_local_coverage` + la cuota). DEC-151 registra exactamente esa trampa («config de
   facetas COMPARTIDA, 4 consumidores, first-match; el oráculo congelado no lo habría visto = falso
   GO»). Mitigación: el gate 3 corre sobre pipeline vivo, no sobre oráculo congelado.
7. **cat017#3 y #2 no son diana.** #3 es flippy (OK↔rerank-miss) y #2 es synthesis-miss estable con
   **residual formal ya declarado** (DEC-132b: fuera del espacio enunciados-generable). Si el lever
   los mueve, es efecto colateral a reportar — **no** se re-narra como éxito del lever.
8. **Generalización a 30+ fabricantes**: la clase «query con dos verbos técnicos» es genérica y
   frecuente en campo (cablear+configurar, montar+programar, sustituir+dar de alta). Eso es
   argumento a favor del EJE — y a la vez el mayor riesgo de sobre-disparo fuera del eval, donde no
   hay gold. El sweep-39 acota el eval; **fuera del eval el lever es no-medido y se declara así.**

---

## 8. NO-GO HONESTO PRE-DECLARADO

Se declara **NO-GO y se cierra la pieza 3 de etapa 2** si ocurre cualquiera de:
- **gate 0** muestra que el cuello es el presupuesto/selección de la vía append existente
  (→ el lever correcto es otro, más barato);
- **gate 2** muestra que la cuota no puede meter `b7633e98`/`5225b248` sin sacar `f0dc41c3`;
- **gate 3** muestra composición cambiada fuera de las 4 pre-registradas;
- **gate 5** muestra cat017#4 convertido pero con ≥1 regresión real en los 14 OK-estables de la
  clase (el trade 1-por-1 no es GO: la cohorte protegida no se «compensa»).

En cualquiera de esos casos, cat017#4 pasa a **residual declarado** de la campaña, como hp012#3
en DEC-164(c) — no se persigue con un lever nuevo en la misma sesión.

---

## 9. QUÉ PIDE ESTE BRIEF AL DÚO (Protocolo 3 — ALTO / zona de dolor retrieval ⇒ sub-agente Fable **+ cross-model Sol INNEGOCIABLE**)
1. ¿El **gate 0** está bien planteado, o hay una vía más barata que el brief no vio?
2. **Fork (A) vs (B)** del test de pertenencia-a-faceta (§3): ¿cuál, y con qué attestation?
3. ¿El punto de inserción (`serving_pipeline.py` :56→:61) es el correcto, o rompe un invariante que
   el autor no vio?
4. ¿El diff `{cat001, cat008, cat012, cat017}` está bien derivado, o falta una vía por la que otra
   query entre en la clase?
5. **Regla-C sobre las claims del propio autor**: verificar contra el código el «8/10 intra-doc»,
   el «v4 no puede», el «commissioning_setup no tiene gemela» y el «append 3/4 saturado». Los
   cuatro son claims fuertes de este brief y ninguno debe pasar por fe.

---
---

# ADDENDA — SEGUNDA PASADA DE RECONOCIMIENTO (independiente, $0, 0 llamadas de modelo)

> **Qué es esto.** Una segunda pasada de recon corrida sobre el mismo encargo sin ver §0-§9 hasta
> el final. **Corrobora** el núcleo del brief (composición 8/10, «v4 no puede», ausencia de gemela
> `commissioning_setup`, el eje intra-documento) y **añade 4 hallazgos materiales que §0-§9 no
> tiene**, dos de los cuales apuntan a la línea de diseño recomendada en §3. Se apendiza en vez de
> sobrescribir porque §0-§9 contiene probes a DB que esta pasada no corrió (p.ej. `5225b248`).
> Método: solo artefactos versionados del repo + ejecución de funciones puras del propio código.
> **Ningún ID resuelto contra la DB en esta pasada.**

## A1 — ⛔ LA TRAZA SOBRE LA QUE SE DISEÑA ESTÁ **STALE** (el hallazgo más importante)

Los 2 runs N=2 son de `manifest.git_commit` **`1557790`** (r1) y **`8c0ad80`** (r2). **HEAD está 46
commits por delante** (`git log 8c0ad80..HEAD | wc -l` = 46) e incluye **P0/P0.5/P1** de etapa 2
(`a2fbad2`, `0a19bf5`).

**P1 toca cat017 por nombre.** `evals/s287_p1_sweep39_composicion_v1.json` →
`resumen.qids_que_la_regla_toca` = `[hp002, hp009, hp010, hp013, hp018, hp019, hp020, cat007,
**cat017**, cat020]`. En el `.partial.jsonl`, fila `qid=cat017`:

| | pre_p1 (≈ estado de las trazas) | p1 (≈ estado de HEAD) |
|---|---|---|
| `drop_tokens` | `['inspire']` | `[]` |
| `models_after` | `[INSPIRE E10, INSPIRE E15]` | `[INSPIRE, INSPIRE E10, INSPIRE E15]` |
| `pool_n` | **43** | **55** |
| `head10` | `7a09deff` p2, `ad28ab54` Qref p7, `f0dc41c3` p47… | `63b307b1` 4188-1122 p8, `7a09deff` p2, `ae86bacb` 4188-1125 p21… |

**Consecuencia dura para este brief:** `best_pool_rank = 4`, la distribución 8/10 y el «append 3/4
saturado» describen un pool de 43 que **ya no es el que corre**. El Gate 2 de §5 («pool congelado,
cuota OFF vs ON») congelaría un pool muerto. Y el §4 pre-registra un diff sobre una composición que
P1 ya movió en 10/39 golds.

**Petición al dúo**: que el **Gate 0** de §5 se anteponga con un **G-menos-1: re-establecer la traza
de cat017 en HEAD** (retrieval-only, sin juez, sin bvg — 1 embedding Voyage + lecturas DB ≈ $0,0001)
antes de aceptar cualquier cifra de §2. Es concebible que P1 ya haya movido cat017#4; en ese caso el
lever no hace falta y se cierra por $0.

## A2 — ⛔ `commissioning_setup` ES **CONFIG DERIVADA DEL GOLD** → el fork (A) recomendado en §3 es tuneo contra la respuesta

§3 recomienda el fork **(A)**: usar los términos del `need` del arquetipo secundario
(«sitio edificio licencia bin alta portal») como test léxico de pertenencia a faceta. Y §7.1 lo
defiende diciendo que el disparo se apoya en «una ontología que **ya existía y no se toca**».

**«Ya existía» es cierto. «No está contaminada» es falso.**
`config/retrieval_facets_v5_document_local.yaml:102-113`, comentario literal del fichero:

> «[STEMMING-GATE] commissioning_setup (solo v5, lane document-local): EXACTAMENTE 6 terminos contra
> la superficie REAL del **chunk objetivo** del handoff 8.2 (**cat017 -> chunk b7633e98,
> HOP-138-8ES issue 6 p5**). Quote **gold_quote_bound** (evals/s277_c1_p1_fact_contract_v1.json,
> **cat017#4:CLSS**): "En el portal en la nube de CLSS Gestion de Clientes, cree un sitio/edificio y
> anada una central. [...] Generar archivo .bin de licencia de la central." Token-exacto cliente:
> **sitio, edificio, licencia, bin** y **portal** VERIFICADOS sobre esa quote…»

Los 6 términos del `need` (`:121`) **son las palabras leídas del chunk-respuesta de este gold**, con
el chunk-id y la cita-bound del gold escritos en el propio fichero. Usarlos como test de pertenencia
es un oráculo construido sobre la respuesta.

**Esto no invalida el eje faceta; invalida esa implementación concreta.** Y afecta también al fork
(B): autorar la gemela `commissioning_setup` en `evidence_coverage_facets_v5` con ese vocabulario
heredaría la contaminación. El patrón DEC-166 fue explícitamente **«cero autoría, cero ediciones de
config»** justo para esta clase de riesgo.

**Petición al dúo**: si se mantiene el eje faceta, el vocabulario secundario debe **re-autorarse a
ciegas** (sin mirar b7633e98/5225b248, p.ej. derivándolo solo del verbo de la query y de la
taxonomía existente) **con un gate anti-tuning explícito**; o el lever se declara no-BP tal como
está. Es la pregunta #6 que este brief debería haber puesto en §9.

## A3 — El instrumento puede estar declarando un **miss falso** (cerrable por $0, antes de todo)

`scripts/factlevel_assessment.py:731` — la re-adjudicación Opus de los candidatos matados por L1
dispara **solo si L1 vació el soporte**:

```python
if not sup and l1_killed:      # sup≠∅  ⇒  los kills NUNCA se re-adjudican
```

Para cat017#4 `sup` conservó 4 ⇒ `support_l1_override: null` en ambos runs. Y de los 6 ids listados
en `support_l1_killed`, **dos están SERVIDOS**: `68d812f5` (= **topk[0] en ambos runs**, HOP-8 p.12)
y `a223976c` (= topk[8] en r2, HOP-8 p.14). Además `support_l1_killed` va **truncado a 6**
(`:805`, `sorted(l1_killed)[:6]`) → el conjunto real de kills **no es auditable desde el artefacto**;
`5880b3b6` (HOP-8 **p.17**, la misma página que el `5225b248` del §2.2) también aparece ahí.

El s287 v1 §0 y el v2 P0 pedían literalmente «re-adjudicación de `l1_killed` **aunque `sup` no quede
vacío**»; el v3 sellado lo sustituyó por el kilo-bridge y el build `a2fbad2` **no lo implementó**.
Sigue abierto en HEAD.

*Juicio honesto del autor de esta addenda*: los kills de p.12 (diagrama de cableado) y p.14 (primer
encendido) parecen **correctos** — ninguno porta «crear sitio + .bin» — así que probablemente **no**
es miss falso. Pero eso es una lectura, no una medición, y **si lo fuera, todo el lever sobra**.
Coste de cerrarlo: volcar el `l1_killed` completo y adjudicar a mano. **$0.**

## A4 — Una vía más barata que §5-Gate-0 no consideró: el **presupuesto de anclas de la lane de vecinos**

Dato nuevo, de artefacto: el chunk-soporte `b7633e98` es **`chunk_index: 4`** del documento
`80e1b7d2` (HOP-138-8ES). Y `1452c904` — **`chunk_index: 3`**, mismo documento, mismo blob, p.4
«Introducción» — **SÍ se sirve en ambos runs** (lane `obligation_warning_reserve_v1`).
**El soporte es el vecino de índice inmediato de una fila servida.**

La lane `same_blob_structural_neighbor_coverage_v1` **disparó en cat017 en ambos runs** (2 filas), y:
- `config/structural_neighbor_coverage_v1.yaml`: **`max_anchors: 2`**, `max_seeds: 10`,
  **`max_gap: 8`** (la distancia aquí es 1 — sobra margen), `require_positive_query_score: true`,
  `require_evidence_facet: true`.
- Su ordenador interno es un **BM25 local sobre la query cruda**
  (`src/rag/structural_neighbor_coverage.py:68-105`) ⇒ **reproduce el mismo sesgo al primer verbo que
  el reranker**. Gastó sus 2 anclas en Qref p.6 + HOP-8 p.16 (r1) / Qref p.6 + HOP-8 p.9 (r2).
- Usa `retrieval_facets_v3` (`:35`) + `evidence_coverage_facets_v4` como matcher (`:189`) — o sea,
  **también** ve una sola faceta (`connect_install_wire`).

**Hipótesis alternativa de mecanismo**: el soporte no pierde por faceta ni por distancia — pierde una
**competición de 2 plazas** contra filas más literalmente on-query, dentro de una lane que ya lo
alcanza. Si es así, el lever barato es el presupuesto/orden de esa lane, **no** una cuota nueva en el
seam de serving (con su serie nueva de `pipe_sha` y re-anclado C1 que §3 ya contabiliza como coste).

**Probe pre-registrado, 0 llamadas de modelo**: `select_structural_neighbors` (`:182`) es una
**función pura** de `(query, seeds, candidates, config)`. Llamarla con los `topk_ids` de la traza como
semillas y las filas del doc `80e1b7d2` como candidatos responde exactamente el Gate 0 de §5
(*¿no disparó? ¿disparó y no seleccionó? ¿presupuesto?*) sin gastar un céntimo.
**Caveat honesto**: que `b7633e98` supere `require_positive_query_score` y `require_evidence_facet`
está **inferido de la config, no medido**. Este probe es justo lo que lo decide.

## A5 — Censo de clase: un segundo ángulo que **refuerza** §4 y matiza su alcance

| definición de «multi-sub-intención» | n/39 | qids |
|---|---|---|
| **Ontología v5 multi-match** (la que usa §4) | **4** | cat001, cat008, cat012, **cat017** |
| **Ontología v4 first-match, ≥2 arquetipos matcheando** | **3** | cat001, cat008, cat012 — **cat017 NO** |
| **Heurística léxica** (≥2 familias de verbo de acción; declarada como heurística) | **7** | cat001, cat012, **cat017**, cat016, cat020, hp011, hp013 |
| `archetype: None` bajo v4 | 18 | — |

Ejecutado con `expand_query_facets` sobre los 39 dev. **Lectura:** la clase existe en el lenguaje
(7/39 ≈ 18 %, argumento a favor del eje y de la escala a 30+ fabricantes), pero las tres definiciones
**no coinciden** y cat017 **no está** en la que usa la ontología de producción (v4). Es decir: la
clase de §4 es una clase **definida por la ontología**, no por el idioma — y su miembro-diana entra
por una entrada de config que A2 demuestra contaminada. Los dos hallazgos se refuerzan.

Corroboración independiente de claims fuertes de §0-§9 (regla-C, pregunta #5 de §9):
- «8/10 al primer verbo» → **CONFIRMADO** en r1 (8 V1 / 2 V2). En **r2 es 7/10** (entran HOP-8 p.14
  y Qref p.7): la cifra es estable en signo, no en valor exacto.
- «v4 no puede» → **CONFIRMADO** ejecutando el resolver: v3 y v4 dan `connect_install_wire` solo. El
  único arquetipo que podría capturar «dar de alta», `program_delay_cause_effect`, exige en su 3er
  patrón (`retrieval_facets_v4.yaml:88`) un sustantivo de `salida|evento|regla|matriz|zona|sirena|
  accion`; el de cat017 es «lazo» ⇒ no matchea.
- «`commissioning_setup` no tiene gemela» → **CONFIRMADO**: `config/evidence_coverage_facets_v5.yaml`
  tiene 9 arquetipos y ninguno es `commissioning_setup`.
- «monopolio intra-documento» → **CONFIRMADO y reforzado**: **10 de las 13 filas servidas** (no 8 de
  10) son del doc `80e1b7d2`, en la banda p.4-p.16 (+p.51) — y el soporte está **dentro** de esa
  banda (p.5). Refuerza que un eje documental es NO-OP aquí.
- «append 3/4 saturado» → **no verificado** en esta pasada (no leí `serving_pipeline.py:18`); queda
  para el dúo.

## A6 — Censo de lanes (contexto para el Gate 0 y para el radio de impacto)

Idéntico en ambos runs, sobre los 39 golds:

| lane | filas | golds tocados |
|---|---|---|
| `same_blob_structural_neighbor_coverage_v1` | 28 | **14/39** |
| `obligation_warning_reserve_v1` | 18 | 18/39 |
| `document_local_content_coverage_v1` | 2 | **1/39** |

La lane que posee la ontología v5 (`document_local`) está **encendida** en `coverage_c1_v4` pero
apendiza en **1 gold de 39** — dato que matiza §2.5: la «vía por-faceta ya existe y está encendida»
es cierta, pero su tasa de disparo real es ~2,6 %. Y un cambio en el presupuesto de la lane de
vecinos (A4) tendría un radio de **14/39**, no de 1 — lo cual exige el sweep-39 de §5-Gate-3 igual.

## A7 — Higiene de gold (anotación, no acción)

`evals/gold_answers_v1.yaml`, `_provenance` de cat017 → `paginas: [47, 2, 5]`. La **p.2 es el ÍNDICE**
del manual («pdf_grep HOP-138-8 indice (p2): 'Cableado de lazo 12 / Configuracion inicial 13 / Auto
Configuracion 16 / Programa de Configuracion de CLSS 18'»). El instrumento mata páginas-índice por
diseño (H4, `factlevel_assessment.py:722-724`) y en efecto `7a09deff` (p.2) aparece en
`support_toc_killed` en ambos runs. Uno de los dos anclajes documentados del gold es
estructuralmente no-acreditable. **El gold sigue siendo válido** (la p.5 porta el hecho verbatim); se
anota para la traza de autoría, no se propone tocarlo.

## A8 — Qué añade esta addenda a la petición al dúo (§9)

6. **A1**: ¿se acepta diseñar sobre una traza de hace 46 commits, cuando P1 mueve el pool de cat017
   de 43 a 55? ¿O el pre-registro se re-ancla en HEAD antes de nada?
7. **A2**: el fork (A) recomendado en §3 usa vocabulario **derivado del chunk-respuesta del gold**
   (con chunk-id y cita-bound escritos en el fichero de config). ¿Sigue siendo BP? ¿Con qué gate
   anti-tuning? ¿O el eje faceta exige re-autoría ciega y por tanto es un lever más caro del que §3
   admite?
8. **A3**: ¿se cierra el hueco `sup≠∅` del instrumento (`:731`) **antes** de construir, dado que un
   miss falso haría el lever innecesario?
9. **A4**: ¿el Gate 0 debe correrse como **probe de función pura** sobre
   `select_structural_neighbors`, y si el cuello es `max_anchors: 2`, el lever correcto es el
   presupuesto de esa lane en vez de una cuota en `serving_pipeline`?

---
---

# ADDENDA-2 — PROBES PRE-DÚO ($0 de juez; 2 llamadas de rerank declaradas)

> **Ejecutado**: los 3 probes que la ADDENDA-1 pre-registró, en el orden pedido.
> **Disciplina**: 0 commits · 0 juez · 0 bvg · 0 generación · DB **solo lecturas** · 0 ediciones de
> código o config. Scripts en scratchpad, fuera del repo.
> **Titular: el lever ya no tiene diana. En HEAD el chunk-soporte SE SIRVE en el top-10.**

## P1 — A3: ¿miss falso o miss real? → **MISS REAL** (el lever no se cancela por aquí)

Método: volcado de los **89 chunks servibles** del doc `80e1b7d2` (HOP-138-8ES) + re-ejecución de la
guarda L1 léxica determinista (`scripts/audit_locator.support_l1_guard_allows`) sobre los 15 ids
SERVIDOS (unión r1+r2) y los 6 de `support_l1_killed`, con adjudicación a mano del content completo.

**Resultado central — en TODO el documento hay UN solo chunk que porta las tres señales del hecho**
(`portal` ∧ `sitio|edificio` ∧ `.bin`):

```
(c) chunks del doc que portan las TRES señales del hecho:
  -> p5 idx4 b7633e98-b011-4035-9548-a564c71e70ac      [ NO SERVIDO en r1 ni r2 ]
```

Adjudicación de los tres candidatos que podían convertir esto en miss falso:

| chunk | ¿servido? | qué dice realmente | ¿porta el hecho? |
|---|---|---|---|
| **`1452c904`** p.4 idx3 (pasa L1; menciona portal+sitio+CLSS) | **SÍ**, ambos runs | «*Copia de seguridad de la configuración de la central en el portal de la nube del Gestor de Sitios CLSS*» — es el **backup tras mover un módulo**, no crear sitio ni generar `.bin`. Además el `coverage_context_content` **trunca antes de esa viñeta**: el generador ni siquiera la ve. | **NO** |
| **`5225b248`** p.17 idx17 | NO | «Programa de Configuración de CLSS»: **descargar, instalar, iniciar sesión**. Sin crear sitio/edificio, sin `.bin`. | **NO** (parcial) |
| **`b7633e98`** p.5 idx4 | NO | «*01 En el portal en la nube de CLSS Gestión de Clientes, **cree un sitio/edificio** y añada una central. Cargue la configuración… **Generar archivo .bin de licencia** de la central.*» | **SÍ, verbatim** |

Los kills L1 de `68d812f5` (p.12, diagrama de cableado) y `a223976c` (p.14, primer encendido) son
**CORRECTOS**: ambos contienen la cadena «clss» pero ninguno el hecho. Y `b7633e98` **no** sufre
`append_view_truncated`: su `coverage_context_content` incluye el hecho completo en los primeros
~250 caracteres — si una lane lo sirviera, el generador lo vería.

> **Corrección a la ADDENDA-1 (regla-C contra mí mismo):** en mi primera pasada reporté que
> `5225b248` «no existe en la tabla». **Falso, y el error fue mío**: el brief solo daba el prefijo
> de 8 caracteres y yo **inventé la cola del UUID** para consultarlo. El id real es
> `5225b248-4180-4573-90cb-fc4c8e37eb74` y **§2.2 del brief original tenía razón**. Retirada la
> objeción.

## P2 — A1 / G-menos-1: la traza en HEAD → **P1 ESTÁ VIVA y el soporte YA SE SIRVE**

**Estado de P1, medido (no inferido).** P1 **no tiene flag**: `catalog_resolver._drop_gates_pass`
puerta 4 llama `_token_core_absent_in_corpus(tok)` de forma incondicional bajo `replace`, y el
perfil `coverage_c1_v4` **exige** `IDENTITY_RESOLVE_POLICY=replace` (`release_profiles.py:310-313`
lanza si no). La quarantine está en `tokens: []` (sunset P0.5 cumplido). Ejecutado con los
`DEMO_FLAGS` del propio harness:

```
P1 corpus_pm_elements(): 849 elementos          <- la regla está ACTIVA
drop_tokens = []                                 <- pre_p1 daba ['inspire']
allowed_sources n=6
```

⇒ **El brazo vigente del serving real de hoy es `p1`, no `pre_p1`.** La cautela del encargo
(«construida no-shippeada») no se sostiene en el código: `0a19bf5` no dejó interruptor.

**Traza re-establecida (retrieval-only):**

| | traza r1/r2 (stale) | **HEAD (vigente)** |
|---|---|---|
| `pool_n` | 44 / 43 | **54** |
| rank de `b7633e98` en el pool | **4** | **14** |
| `5225b248` en pool | — | **NO** |
| `submotivo` que produciría | `lexical-distractor` (4 < 10) | `pos-buried` (14 ≥ 10) |

Docs nuevos que P1 mete en el pool al conservar el paraguas `INSPIRE`: `4188-1122-ES` (Cyb),
`HOP-338-9ES/PT` (Op) y **`4188-1125-ES … Li`** = la *Guía de concesión de licencias INSPIRE con
CLSS*, cuyo chunk `ae86bacb` (p.21, **pool rank 2**) **también porta el hecho completo** [PSB]. Es
decir: P1 no solo movió el pool, **duplicó los portadores del hecho**.

**Top-10 del reranker en HEAD, 2 reps (DEC-096b):**

```
 0 68d812f5 p.12   3 4d76ec50 p.7    6 3a2fc401 p.9
 1 f0dc41c3 p.47   4 79faef35 p.8    7 e472044e p.15
 2 f8f1c9f3 p.51   5 ad81ba70 p.10   8 6596dfec p.16
                                     9 b7633e98 p.5   <<< EL SOPORTE, SERVIDO
ESTABILIDAD entre reps: IDÉNTICO
```

**`cat017#4` ya NO es rerank-miss por composición en HEAD.** El soporte entra en el top-10 en el
slot 9, estable 2/2. Reparto de sub-intención: **7 V1 / 3 V2** (el desbalance persiste) — pero
**ya no bloquea el hecho**, que es lo único que el lever perseguía.

**Coste real declarado**: 2 embeddings Voyage + ~110 lecturas PostgREST + **2 llamadas de rerank
LLM** (las únicas llamadas de modelo de toda la ADDENDA-2; necesarias porque «¿sigue siendo
rerank-miss?» es literalmente una pregunta sobre la salida del reranker). Estimado **< $0,10**.
Sin juez, sin bvg, sin generación.

**Caveat honesto y no negociable**: esto acredita `in_topk = True`, **no** `conveyed`. Que el hecho
llegue a la respuesta y se transmita es una pregunta de **juez**, fuera del presupuesto de esta
addenda. Lo medido es que la clase **ya no puede ser `rerank-miss`**; pasará a `OK` o a
`synthesis-miss`, y eso lo decide una re-medición con K-reps.

## P3 — A4: probe de función pura sobre `select_structural_neighbors` (0 llamadas de modelo)

Dos brazos, candidatos = las 89 filas del doc, config real (`max_seeds 10 · max_gap 8 ·
max_anchors 2 · max_candidates 192`).

| brazo (seeds) | embudo `input → same_blob → positive_query → facet → anclas` | seleccionados | `b7633e98` |
|---|---|---|---|
| **VIGENTE** (top-10 HEAD) | 89 → 32 → 32 → 8 → 2 | `c2564c21` p.10, `5880b3b6` p.17 | **es SEMILLA** (ya servido) ⇒ pregunta MOOT |
| **STALE** (top-10 traza r1) | 89 → 32 → 32 → **9** → 2 | `6596dfec` p.16, `5880b3b6` p.17 | candidato, **no** seleccionado |

**Se cierra el gate que la ADDENDA-1 dejó INFERIDO** — medido directamente:

```
b7633e98 facet_matches = [{"facet": "continuity", "term_hits": ["circuito", "lazo"]}]
```

- `require_evidence_facet`: **PASA** (faceta `continuity` de `connect_install_wire`).
- `require_positive_query_score`: **PASA** (BM25 local 3.016; el embudo no pierde ni una fila ahí:
  `same_blob = positive_query = 32`).
- **Pierde por las 2 plazas**: en el orden BM25 local queda en posición **8** de 32 elegibles y
  ~**5.ª de las que pasan faceta** (tras `5880b3b6`, `a223976c`, `6596dfec`, `2219484b`; `7a09deff`
  cae antes por TOC). Con `max_anchors: 2` habría hecho falta **≥5**, no 3.

⇒ El mecanismo de la ADDENDA-1 **queda CONFIRMADO como diagnóstico** (el soporte era alcanzable por
la lane y perdía la competición de anclas), y a la vez **queda MOOT como lever**: en HEAD el
reranker ya lo sirve, y subir `max_anchors` de 2 a ≥5 sería un cambio grande con radio 14/39 para
resolver algo que ya está resuelto.

*Declaración de precisión*: la posición «~5.ª» sale de re-ejecutar `_rank_bm25` sobre mi propia
reconstrucción del conjunto elegible; el orden final de la lane además pliega cards numéricas, así
que **la posición exacta es aproximada**. Lo que **no** es aproximado, porque sale del `trace` de la
propia función: `facet_candidates = 9` y `b7633e98 ∉ selected`.

## VEREDICTO DE RUTA

| ruta | veredicto | evidencia |
|---|---|---|
| **(a)** miss-falso → cerrar pieza 3 | **REFUTADA** | Un único chunk del doc porta las 3 señales (`b7633e98`), y **no** estaba servido. Los kills L1 de `68d812f5`/`a223976c` son correctos. `1452c904` (servido) habla de *backup*, no de crear sitio ni `.bin`, y su vista al generador ni llega ahí. |
| **(b)** P1/HEAD ya lo mueve → re-anclar y re-evaluar | ✅ **CONFIRMADA — ES LA RUTA** | P1 viva y sin flag (849 elementos, `drop_tokens=[]`); pool 43→**54**; soporte 4→14 en pool pero **servido en top-10 slot 9, 2/2 reps idénticos**. Además P1 mete un **segundo** portador completo (`ae86bacb`, pool rank 2). |
| **(c)** cuello = presupuesto lane vecinos → lever de lane | **MECANISMO CONFIRMADO, LEVER MOOT** | El soporte pasa faceta (`continuity`) y query-score, y perdía las 2 anclas (~5.º de los facet-passers). Queda como **fallback documentado** si (b) se cayera en la re-medición con juez. |
| **(d)** monopolio confirmado → cuota viva con vocabulario re-autorado | **NO JUSTIFICADA** | El desbalance persiste (7/10 V1 en HEAD) pero **ya no bloquea el hecho**. Construir una cuota — con su serie nueva de `pipe_sha`, su re-anclado C1 y la mina anti-tuning de A2 — para un desbalance sin daño medido sería aparato sin decisión detrás (*pregunta cero*). |

### Consecuencia operativa propuesta

1. **La pieza 3 de etapa 2 (cuota-por-faceta) NO se construye.** Su condición de disparo era «1+2 no
   mueven cat017»; medido hoy, **P1 (pieza 1) SÍ lo mueve**. La condición no se sostiene.
2. **Lo que queda es una RE-MEDICIÓN, no un lever**: correr el factlevel en HEAD (con K-reps) para
   saber si cat017#4 aterriza en `OK` o en `synthesis-miss`. Eso cuesta juez y es decisión de
   presupuesto, no de diseño.
3. **Hallazgo colateral para la campaña (no para este lever)**: las 2 trazas N=2 que sostienen
   DEC-163 son **pre-P1**, y P1 toca **10/39 golds**. El mapa `OK 101 / synth 13 / rerank 4 /
   retr 10` puede estar desplazado en más golds que cat017. Es un input para etapa 3/A3, y va al
   dúo como pregunta, no como afirmación.
4. **Sigue en pie de la ADDENDA-1**, con independencia de la ruta: el hueco de instrumento
   `if not sup and l1_killed` (`factlevel_assessment.py:731`) + el truncado a 6 (`:805`). Hoy no
   produjo un miss falso — **verificado**, no supuesto — pero es una clase de FN silencioso viva.

### Qué le queda al dúo tras la ADDENDA-2

Las preguntas 6-9 de §A8 quedan **parcialmente resueltas por medición** (A1 responde 6; A3 responde
8; A4 responde 9). La que sigue abierta y ahora es la única de rumbo:

> **¿Se acepta cerrar la pieza 3 por «diana movida» (ruta b), o el dúo exige la re-medición con
> juez ANTES de declararla cerrada?** El autor recomienda cerrarla en diseño y abrir una
> re-medición — pero es exactamente el tipo de convergencia rápida que el dúo existe para frenar.

---

# ADDENDA-3 — RE-MEDICIÓN CANÓNICA EN HEAD (orquestador, 31-jul): el titular de ADDENDA-2 queda REFUTADO en la vara canónica

> Instrumento `factlevel_assessment.py` v3.1, ruta harness real, git `9a9736b`, corpus chunks_v2
> 25.088, 2 reps con tag propio (`evals/s100_factlevel_smoke_v31_cat017_head_rep{1,2}.yaml`).
> Coste ~$1 (2 smokes dirigidos --qids cat017). Held-out intocado.

## Resultado (N=2, ambas reps)
| hecho | rep1 | rep2 |
|---|---|---|
| #0 OPAL / #1 «159+159» / #3 Auto Configuración | OK | OK |
| #2 licencia CLIP | synthesis-miss (omitted 5/5) | synthesis-miss (omitted 5/5) |
| **#4 CLSS** | **rerank-miss** (in_topk F, reaches_gen F) | **rerank-miss** (in_topk F, reaches_gen F) |

`b7633e98` NO aparece en el top-10 de ninguna rep. Pool_n 50 / 53.

## Reconciliación con ADDENDA-2 §P2 (no es contradicción de datos: es MÉTODO + DADO)
Los slots 0-5 del top-10 son IDÉNTICOS en las 4 pasadas (2 del probe + 2 canónicas):
`68d812f5 · f0dc41c3 · f8f1c9f3 · 4d76ec50 · 79faef35 · ad81ba70`. El churn vive en la cola 6-9:
el probe sirvió `…, 3a2fc401, e472044e, 6596dfec, b7633e98` (2/2); el canónico sirvió
`c2564c21` (rep1) / `ad28ab54` (rep2) en su lugar. Dos diferencias explican el flip sin invocar
misterio: (a) el pool del probe era 54 vs 50/53 del harness — y el tamaño/orden del pool cambia la
petición del reranker (lección DEC-092/CUT15); (b) el dado de cola del LLM-rerank (DEC-096b).
**Lectura honesta: P1 movió a `b7633e98` de miss-estructural-estable a FRONTERA DE COLA** (rank
~14 de pool, a veces dentro a veces fuera según pool/dado). La vara de la campaña es la canónica
⇒ **cat017#4 SIGUE contando como rerank-miss estable N=2** y la pieza 3 recupera diana.

## Qué reabre esto (fork para el dúo, con TODO lo de A2 vigente)
1. **Lever vecinos (A4)**: en la traza canónica `b7633e98` NO es semilla (no se sirve) — vuelve a
   ser candidato que PASA `require_evidence_facet` (continuity; term_hits circuito/lazo, medido) y
   pierde las 2 plazas de `max_anchors` contra filas más on-query (BM25 sobre query cruda = mismo
   sesgo del reranker). El brazo «STALE» de A4 §P3 ES el brazo vigente. Radio 14/39 golds ⇒ sweep
   obligatorio.
2. **Cuota en serving (§3)**: viva pero con las restricciones de A2 (vocabulario del arquetipo
   contaminado por el gold ⇒ re-autoría ciega o no-BP) y el coste pipe_sha/recibos C1 declarado.
3. **No-lever**: declarar cat017#4 residual-frontera (la conversión llegaría gratis con cualquier
   churn futuro de pool… o no). Honesto pero renuncia al único mecanismo nombrado de etapa 2.

## Preguntas ADICIONALES al dúo (se suman a §9 + A8)
10. ¿La evidencia 2/2-probe vs 2/2-canónico admite la lectura frontera-de-cola, o exige un N mayor
    antes de diseñar? (cada rep canónica ≈ $0,5)
11. Si el mecanismo elegido es el presupuesto/orden de anclas de la lane de vecinos: ¿cómo se
    diseña sin heredar el sesgo BM25-on-query que causó exactamente este miss, y sin tocar el
    radio ni el cap (settled)?
12. El colateral DEC-163 (trazas del mapa pre-P1, P1 toca 10/39): ¿re-anclar el mapa AHORA
    (dirigido 10 golds ~$10-12) o tras decidir el lever?

---

# ADDENDA-4 — DÚO r1 CONSOLIDADO (31-jul; Sol xhigh con tools + sub-agente Fable fresco; RONDA 13/13 CONFIRMADOS, 0 FP)

## Veredicto conjunto: la cuota-por-faceta tal como está en §3 NO es build-ready; el fork (i) lane-vecinos queda CERRADO; medir antes de elegir.

**Sol (8, todos confirmados regla-C por el orquestador):** fork (A) circular (vocabulario del
arquetipo = tokens del chunk-respuesta del gold, monolingüe ES) · cohorte concentrada STALE
(cat017#3 ya es OK-estable 2/2 en HEAD y el brief lo dejaba fuera → un GO podría comerse #3 sin
STOP) · Gate 5 sin aislamiento causal (churn de pool 50→53 entre reps canónicas; exige OFF
congelado pareado o potencia pre-registrada) · Gate 6 viola el contrato sellado (93 COMPLETOS
«SIN alternativa», s287 v3:145) · inserción pre-`protected_prefix` alimenta observer+lanes
(radio real > top-10) · fuera del fail-open (una excepción tumba el turno) · «secundaria» =
orden de DECLARACIÓN de la config, no faceta desabastecida · duplica la maquinaria need-group
atestada (`N_FACET`, plan-hash, revalidación fail-closed).

**Sub-agente (5, todos confirmados):**
- **H1**: «frontera-de-cola» era INTERPOLACIÓN — los artefactos canónicos no registran pool_ids
  y `best_pool_rank` 9/8 es min sobre el SET de soportes (n_support_fam 4/5, incluye
  `ae86bacb`), no la posición de `b7633e98`.
- **H2**: «frontera» y «miss estable N=2» son incompatibles como afirmación conjunta; N=2 no
  separa p=0 de p≤0.7. Resoluble judge-free: `in_topk` solo necesita retrieve+rerank
  (~$0,05/rep, no $0,5).
- **H3**: candidato sistemático no nombrado del flip probe-vs-canónico: `target_models` (el
  harness pasa None, factlevel_assessment.py:369; con 2 modelos el prompt del reranker cambia
  materialmente, reranker.py:96-101). El probe de ADDENDA-2 vivía en scratchpad → irreproducible.
- **H4 (CRÍTICO)**: fork (i) MUERTO en código: el `rank_key` es 5-claves (claims→n-facetas→
  hits→BM25→gap; `b7633e98` pierde en las claves 1-4, no en BM25) + sin señal no-contaminada
  para promoverlo + 4 topes duros (max_anchors schema 1..4 vs ≥5 necesarios;
  MAX_APPENDED_PER_LANE=2 sin override; MAX_APPENDED=4; exceso ⇒ fail-open que TIRA todos los
  appends). Y quien lea la config para «re-autorar a ciegas» queda contaminado (el comentario
  CONTIENE la quote del gold) ⇒ la re-autoría debe hacerla un agente sin acceso a esa config.
- **H5**: re-anclar el mapa DEC-163 ANTES de elegir mecanismo (P1 toca 10/39; la cohorte
  protegida deriva de runs pre-P1).

**RUTA ADJUDICADA (ejecutándose):** (1) probe serve-rate judge-free N=6, script COMMITEADO
(`scripts/s288c_cat017_serve_rate_probe.py`; regla: 0/6 ⇒ miss estable, ≥1/6 ⇒ frontera y la
pieza 3 pierde justificación) → (2) re-anclaje dirigido del mapa (10 golds P1, ~$10-12, N=2)
→ (3) SOLO si 0/6: fork (ii) re-especificado desde cero (vocabulario ciego por agente sin
contexto NI acceso a la config contaminada; cohorte re-derivada en HEAD incl. cat017#3;
aislamiento causal pareado; 93 completos; política de error fail-open; radio observer/lanes
en los gates). Nota de registro: Sol SÍ revisó ADDENDA-3 (snapshot post-append). Tally en
`evals/adversarial_review_log.jsonl` (ts=2026-07-31T08:37:44, 8/8/0, duo complete).
