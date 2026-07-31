# s288c v2 — RE-SPEC: lever de COMPOSICIÓN de la selección (clase selection-monopoly) — PRE-DÚO r2

Estado: **PRE-DÚO r2**. GO de Alberto (31-jul, «adelante con el re-spec») tras cumplirse el paso 3
de la ruta adjudicada por el dúo r1 (ADDENDA-4 del brief v1: probe 0/6 = miss estable). Sustituye
al mecanismo §3 del brief v1 (`s288c_cat017_facet_quota_brief_v1.md`), muerto por los 8 de Sol.
Nada cableado. Este documento es lo que el dúo r2 debe desafiar.

---

## 1. OBJETIVO + MÉTRICA

**OBJETIVO.** Convertir los 2 rerank-miss estables de etapa 2 en HEAD — **cat017#4 «CLSS»** y
**hp002#4 «gate de seguridad pre-mantenimiento» (clase SEGURIDAD)** — por una regla de CLASE
(monopolio de selección en pools concentrados within-doc), sin regresión en la cohorte protegida
re-derivada. cat010#0 queda FUERA (espera su outcome A3, DEC-166 residual 4).

**MÉTRICA.** `conveyed` a nivel-hecho, instrumento v3.1 (vara de la campaña DEC-163), con
aislamiento causal PAREADO (ver §5-G2: la mera N-rep no aísla — crítico c3 de Sol, y la
inestabilidad de insumo de §2.3 lo agrava).

**COHORTE PROTEGIDA RE-DERIVADA (obligatoria tras el mapa re-anclado; crítico c2 de Sol).**
- Para los 10 golds tocados por P1: los **26 OK-estables-N2 de HEAD**
  (`s100_factlevel_smoke_v31_p1map_rep{1,2}.yaml`), que INCLUYEN cat017#3 (ya no flippy) y
  hp018#1/#4 (conversiones cobradas de etapa 2 — regresarlas es STOP).
- Para los 29 golds no tocados: los OK-estables del full pre-P1 (`s100_factlevel_full_v3_2026072{9,30}`)
  siguen siendo la referencia válida (P1 no movió sus pools: sweep
  `s287_p1_sweep39_composicion_v1` — verificar esta premisa es el gate G1b, no se asume).
- **El contrato s287 v3:145 rige sin rebaja: el gate final corre los 93/equivalentes COMPLETOS,
  «SIN alternativa»** (crítico c4 de Sol — el «subconjunto argumentado» del brief v1 queda retirado).

---

## 2. EL MECANISMO REAL, MEDIDO (todo con recibo)

### 2.1 cat017#4 — exclusión de SELECCIÓN, no de retrieval
- 0/8 servicios del portador en mediciones de selección por la ruta harness exacta
  (`s288c_cat017_serve_rate_probe_v1.json`: 0/6; + 2 reps canónicas): el top-10 se lo llevan
  filas de cableado del mismo manual (7-9 de 10) y los DOS portadores quedan fuera SIEMPRE.
- Portadores en pool: `ae86bacb` (guía licencias 4188-1125 p.21) rank **~2 ESTABLE** (7/8
  retrieve-only); `b7633e98` (HOP-138-8 p.5) banda **12-14** (8/8 en ventana), con bandas
  distintas en otras ventanas (1 y 44 — §2.3). El reranker EXCLUYE una fila que su input le da
  en el puesto 2.

### 2.2 hp002#4 — la misma clase, agravada por la concentración que P1 trajo
- P1 concentró el pool de hp002 (50 → 32-34, TODAS las filas del manual ASD535) y el soporte
  singleton del hecho-seguridad cayó a rank 21-23 → fuera del top-10 en 2/2
  (`s100_factlevel_smoke_v31_p1map_rep{1,2}.yaml`). Pre-P1 era OK estable.
- Nota honesta: el ID del chunk-soporte no lo exporta el instrumento (solo `best_pool_rank`);
  identificarlo es el primer paso del build (G0), no una premisa.

### 2.3 HALLAZGO NUEVO — el INSUMO del reranker es ventana-dependiente (confirma H3-dúo-r1 «sin caracterizar»)
Probe retrieve-only N=8 + 2 fotos sueltas, misma query, ~2h: `b7633e98` en bandas **1 (×6,
ventana probe) / 12-14 (×8) / 44 (×1)**; pool_n 49-55; top-3 estable salvo 1/8. Consistente
dentro de ventana, saltos ENTRE ventanas ⇒ estado externo lentamente cambiante (salud de canales
aside con fail-open SILENCIOSO — `retriever.py:1638` — y/o estado de caches), no dado por-llamada.
**Consecuencias de diseño**: (a) NINGÚN mecanismo keyed por rank de pool; (b) ninguna medición
end-to-end no-pareada puede atribuir causalidad (refuerza c3 de Sol); (c) la observabilidad de
procedencia/salud de canal es una pieza PROPIA (§6) — hoy un canal caído es invisible en traza.

---

## 3. MECANISMO PROPUESTO — cuota de composición CONTENT-KEYED sobre need-groups atestados

**Regla (una frase).** Tras el rerank: si un need-group de la query tiene cobertura **cero en la
selección** pero existe en el pool un candidato que lo cubre con el estándar atestado existente
(ventana ≥`N_FACET` términos distintos del grupo, la MISMA vara de `post_rerank_coverage.py:133-138`),
swap del MEJOR candidato de ese grupo por la última fila seleccionada del grupo sobre-representado;
**q=1 swap máximo**, nunca filas carve-out (`_hyq_boosted`/`_enun_quota`/`_swapped_*`), determinista
dado el output del reranker, flag `FACET_SLOT_QUOTA` default-off.

**Qué responde a cada muerte del v1:**
- «secundaria = orden de declaración» (m7-Sol) → la faceta que dispara es la **INFRA-CUBIERTA EN LA
  SELECCIÓN** (cobertura 0 selección + cobertura ≥1 pool), simétrica, no posicional.
- «matcher léxico nuevo sin attestation» (m6-Sol) → se REUSA la maquinaria need-group + `N_FACET`
  ya atestada, no se inventa un matcher.
- «radio observer/lanes» (m5-Sol) → el swap ocurre ANTES de `protected_prefix` (es su punto: la
  selección ES el prefijo), y los gates cubren `served`-completo + `coverage_trace` + lanes
  disparadas, no solo top-10 (G3).
- «fuera del fail-open» (m8-Sol) → la cuota corre envuelta: cualquier excepción ⇒ conservar el
  `reranked` original + traza `quota_degraded` (espejo del patrón coverage).
- «vocabulario contaminado» (c1-Sol / H4-r1) → §4: AUTORÍA CIEGA por agente sin contexto.

**Localización**: `serving_pipeline.py` entre :56 y :61 (único seam; prod+bvg+instrumento miden lo
mismo), con el coste declarado del v1 §3 intacto (serie nueva de `pipe_sha` + re-anclado de recibos
C1 — inventariar ANTES del build).

---

## 4. LA PIEZA CIEGA — autoría del vocabulario sin contaminación (condición dura del dúo r1)

Los need-groups existentes NO cubren las 2 clases diana (commissioning/licencia; seguridad-gate
pre-mantenimiento) y las entradas retrieval-side existentes están contaminadas (el comentario de
`retrieval_facets_v5_document_local.yaml:102-113` CONTIENE la quote del gold — H4-r1: quien lo lee
queda contaminado por construcción).

**Protocolo de autoría ciega (pre-registrado):**
1. Un agente FRESCO sin contexto de sesión recibe SOLO: (a) el dominio (PCI, manuales técnicos de
   fabricantes), (b) los VERBOS/intenciones de clase en abstracto («puesta en servicio/licenciamiento
   de una central», «precauciones/bloqueos previos a mantenimiento»), (c) el formato de entrada
   need-group. PROHIBIDO: leer golds, `evals/`, los chunks del corpus, y los ficheros de config de
   facetas existentes (los nombres exactos quedan en la orden como denylist).
2. Entrega bilingüe ES/EN (c1-Sol: el v1 era monolingüe).
3. **Gate anti-tuning ANTES de tocar nada**: el vocabulario ciego se valida contra queries NO-gold
   (`query_logs` reales + parafraseos sintéticos de clase) y se mide su disparo sobre las 39 dev —
   el conjunto disparado se PRE-REGISTRA como diff (§5-G1) SIN mirar si convierte. Si el vocabulario
   ciego NO captura los portadores por la vara `N_FACET` (posible de verdad: «Comprobaciones
   preliminares» no comparte léxico con la query — ese ES el gap), el resultado es **NO-GO honesto
   del lever content-keyed**, no una iteración del vocabulario mirando el chunk (eso sería re-derivar
   la contaminación por gradiente).

---

## 5. GATES (en orden; $0 primero; el aislamiento causal es PAREADO, no N-reps)

- **G0 ($0)**: identificar el chunk-soporte de hp002#4 (dump del pool + adjudicación léxica local,
  patrón A3-r1) y verificar que porta el hecho + su need-group candidate.
- **G1 ($0)**: disparo del vocabulario ciego sobre 39 dev = diff PRE-REGISTRADO; 5ª query
  inesperada ⇒ STOP-y-adjudicar (precedente F2-s287). **G1b**: verificar la premisa «29 pools
  no-P1 intactos» (sweep vs artefactos) antes de heredar su cohorte pre-P1.
- **G2 ($0, EL GATE DE MECANISMO — aislamiento perfecto)**: pools y outputs de rerank de los golds
  de la clase CONGELADOS a disco (los de las reps HEAD ya committeadas + re-serializaciones N=3);
  la cuota OFF vs ON corre OFFLINE sobre el MISMO `reranked` serializado. La cuota es determinista
  dado su input ⇒ el delta de composición es atribución PURA, inmune a la inestabilidad §2.3.
  Criterio: mete un portador en cat017 y el candidato-G0 en hp002 sin tocar `f0dc41c3` (cat017#0/#1)
  ni sacar ninguna fila OK-portadora de la cohorte §1 (se verifica por-fila, no por-conteo).
- **G3 ($0)**: sweep-39 de composición END-TO-END con flag ON: cambios SOLO en la clase G1;
  35 restantes byte-idénticas EN `served`-completo + `coverage_trace` + lanes disparadas (radio
  m5-Sol). Réplica del mismo brazo como suelo de ruido (§2.3 obliga).
- **G4**: inertness OFF byte-idéntico + suite completa + configs SHA-a-SHA.
- **G5 (~$2-4, PAREADO a nivel generación)**: generación+juez sobre los `served` CONGELADOS de G2
  (OFF vs ON, mismo contexto exacto salvo el swap — patrón context-only preregistrado del linaje
  s277), K≥2 por brazo, SOLO clase: cat017#4/hp002#4 convierten + los hechos OK de esas queries
  intactos + centinela de conducta hp009.
- **G6 (con GO de gasto)**: cohorte COMPLETA re-derivada (§1) sin alternativa, regla H6 (flip ⇒
  re-run) + regla-C DEC-092b (leer la respuesta antes de declarar regresión).

**NO-GO pre-declarado**: G1 dispara fuera de clase de forma no adjudicable · el vocabulario ciego
no captura portadores (§4.3) · G2 no puede convertir sin sacar una fila portadora-OK · G5 convierte
uno rompiendo el otro (el trade 1-por-1 no es GO). En NO-GO: {cat017#4, hp002#4} = residual
declarado de etapa 2 con mecanismo nombrado, y el arco pasa a etapa 3/A3.

---

## 6. PIEZA PROPIA (shippeable SOLA, aunque el lever muera): OBSERVABILIDAD del retrieve

Traza de procedencia por fila (canal de origen) + contador VISIBLE de fail-opens de canal en el
resultado del retrieve (`retriever.py:1638` y hermanos aside). Coste mínimo, cero cambio de
conducta, des-confunde TODA medición futura de composición (la §2.3 hoy es indistinguible de
«canal caído»). Se propone como PR separada con sus tests, independiente del veredicto del lever.

---

## 7. ALTERNATIVAS DESCARTADAS (métrica de cada settled)
- Pool-top protection (rank-keyed, sin vocabulario): muerta por §2.3 (rank ventana-dependiente) y
  no cubre hp002 (21-23) — se declara, no se construye.
- Re-tune del reranker: NO-GO DEC-092 (retrieval-miss, 6 métodos ≤ baseline).
- Subir RERANK_TOP_K: cobrado DEC-092b (top-10 shippeado; ampliar re-juega un lever cobrado).
- Lane de vecinos: CERRADA (H4-r1: rank_key 5-claves + topes duros de schema/cap).
- Cuota v1 (§3 del brief v1): muerta (8-Sol, ADDENDA-4).
- Esperar churn de pool (§2.3 «a veces entra solo»): no es mecanismo, es azar de ventana — y la
  selección lo excluyó 8/8 incluso con el portador en rank 1-2.

## 8. RIESGOS DECLARADOS
1. **El vocabulario ciego puede no capturar los portadores** — riesgo REAL y asumido; su fallo es
   NO-GO honesto, no iteración con gradiente hacia el gold (§4.3).
2. Desplazamiento cuesta hechos (S273/DEC-132b): q=1 + carve-outs + verificación POR-FILA en G2.
3. Coste estructural: pipe_sha nuevo + recibos C1 (inventario pre-build).
4. hp002#4 puede resultar no-capturable si su singleton no alcanza `N_FACET` en ventana (G0/G2 lo
   destapan por $0 ANTES de cablear).
5. La clase puede ser mayor que 4 queries bajo vocabulario nuevo (G1 lo pre-registra; STOP si
   crece sin adjudicación).
6. n=2 sigue siendo n=2: la generalización a 30+ fabricantes es argumento de EJE, no de evidencia —
   fuera del eval el lever queda no-medido y se declara.

## 9. PREGUNTAS AL DÚO r2
1. ¿El protocolo de autoría ciega (§4) es realmente no-contaminante, o hay una vía de contaminación
   residual que no vimos (p.ej. mis parafraseos de clase en la orden ya filtran el gold)?
2. ¿G2 (pareado offline sobre reranked congelado) es aceptable como gate de MECANISMO, y G5
   (context-only pareado) como gate de OUTCOME — o falta un eslabón causal?
3. ¿La cohorte re-derivada §1 está bien construida (26 HEAD + herencia pre-P1 con G1b)?
4. ¿La pieza §6 (observabilidad) debe adelantarse ANTES incluso de G0, dado §2.3?
5. Regla-C sobre las claims nuevas: bandas de §2.3, «0/8 selección», pool hp002 32-34 all-same-doc,
   y «los need-groups existentes no cubren las 2 clases» (esta última la afirmo sin haber listado
   los 9 arquetipos de evidence-v5 contra hp002 — verificadla).

---

# CONSOLIDACIÓN DÚO r2 (31-jul noche) — VEREDICTO: NO-GO como está; ruta re-adjudicada

**Ronda 18/18 confirmados, 0 FP** (Sol 9: 2C+6M+1m · sub-agente 9: F1-F9; convergencias
independientes en 5 ejes). Tally: `adversarial_review_log.jsonl` ts=2026-07-31T22:40:14.

**Lo que tumba el re-spec:**
- **F1 (sub-agente, verificado)**: la «autoría ciega» de §4 estaba contaminada EN LA ORDEN — mis
  descriptores de clase son el hecho abstraído, no derivables de la query (hp002 pregunta por
  «alarma de flujo bajo… cómo se diagnostica»: cero vocabulario de mantenimiento).
- **F2 (sub-agente, verificado)**: doble-bind — en cat017 la selección YA contiene sub-intención-2
  (`6596dfec` p.16 + `e472044e` p.15 en topk de AMBAS reps) ⇒ un vocabulario honesto de
  commissioning atesta esas filas y la cuota (cobertura-de-grupo) NO dispara; el predicado del
  disparo no es el predicado del fallo (exclusión del HECHO). En hp002 el grupo no puede activarse
  query-side sin contaminar.
- **c1-Sol**: G5 medía un pipeline ficticio (el swap alimenta observer/coverage; congelar «todo
  salvo el swap» no es el camino real). **c2-Sol/F4**: algoritmo sub-especificado (sin orden total;
  sin víctima definida cuando la selección no atesta grupos — hp002; «seguro por coincidencia» en
  cat017). **F5 (regla-C contra MÍ)**: las bandas 12-14/44 de §2.3 sin recibo committeado
  (scratchpad otra vez) + `retriever.py:1638` es el fail-open del canal VECTOR PRINCIPAL, no aside.
  **F6**: «29 pools intactos» literal-falso (18/29 con churn de composición; lo heredable es
  regla-inerte + suelo de churn). **F7 (verificado)**: `fault_reset_recovery/state_blockers`
  [bloqueo, manual, inhibicion…] y `verification_recovery` [diagnostico, comprobacion…] son
  candidatos VIVOS para hp002 — podría ser servible con grupos EXISTENTES sin autoría alguna.
  **F3/m7-Sol (verificado)**: las DOS puertas content-keyed existentes fallaron con los portadores
  delante — document_local (dueña de `commissioning_setup` shippeado, presupuesto propio) no
  apendizó `b7633e98` en cat017; `obligation_warning_reserve` disparó en hp002 con `339f06e0` (p.7)
  y no con el singleton — diagnosticar POR QUÉ es $0 y domina la decisión. **m4-Sol**: el flag
  necesitaría contrato de release (perfil atómico C1). **m8-Sol**: prod pasa `target_models`
  (prompt distinto del reranker) — «prod+bvg+instrumento miden lo mismo» sobre-afirmado.
  **m9-Sol**: `_channel` ya se estampa por fila — §6 se reduce a exponer salud/fail-opens.

**RUTA RE-ADJUDICADA (en orden, todo $0 hasta nueva decisión):**
1. **§6 observabilidad** (adelantada por ambos lados): exponer salud/fail-open por canal en traza
   (la procedencia ya existe) + recibos committeados de estabilidad de pool (cierra F5).
2. **Diagnóstico de las puertas existentes** (F3): funnel exacto de por qué document_local no
   apendiza `b7633e98` (cat017) y por qué obligation_warning eligió `339f06e0` y no el singleton
   (hp002) — o destapa lever barato (presupuesto/orden/bug) o forcluye la cuota honesta.
3. **Test F7**: identificar el singleton de hp002 (G0) y medir si `state_blockers`/
   `verification_recovery` atestan su ventana ≥N_FACET=3.
4. SOLO si el trío deja un mecanismo con disparo query-derivable sin el gold → re-spec v2; si no,
   {cat017#4, hp002#4} = residual declarado de etapa 2 con mecanismo nombrado y el arco pasa a
   etapa 3 / A3.
