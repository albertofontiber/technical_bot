# s272 — Diagnóstico por-fact de los 2 retrieval-miss del funnel (Bloque B)

> **[ERRATA s273 — adjudicación de Alberto; el cuerpo medido de abajo NO se toca.]** La frase
> «la cuota nunca se midió» (§1d) es INCORRECTA: la cuota del canal enunciados SÍ fue construida
> y medida en s105 (DEC-103 pre-Codex) — mecánica de entrada-al-sort, N=10: gate barato a T1
> +0/−0 PASS, NO-GO a 71.202 filas, cierre «bajo esta mecánica; no subir N ni tunear contra
> hp006». Autoridad: `docs/PLAN_RAG_2026.md` §«Estado anterior (s105 — 10 jul 2026)» en la rama
> `codex/s107-wip-backup` (`33977c15f6…`; colisión de numeración DEC-103..105 — ver
> `evals/s273_quota_design_v1.md` §0 y §7). Los ranks/sims/floors medidos de este diagnóstico
> quedan intactos y vigentes.

**Targets:** `cat017#2` y `hp010#1` — los 2 retrieval-miss residuales del funnel candidato 143 OK / 12 synth / 2 retrieval
(adjudicados CORE-REQUIRED en `evals/s269_triage_12misses_v1.yaml`).
**Contrato:** SOLO-diagnóstico. DB solo GET/RPC read-only; pagado únicamente el retrieval real (2× embedding Voyage
+ 2× rerank LLM ≈ $0.12, + ~5 re-embeddings de query para probes ≈ $0.01; total « techo $1). Nada escrito en repo ni DB.
**Estado medido:** worktree read-only `origin/main@5774a6c` (post-s271). Ruta **HARNESS** (paridad
`scripts/factlevel_assessment.py`): `retrieve_chunks(q, top_k=50)` → `rerank(q, pool, top_k=10, strict=True)` →
served = topk con `similarity ≥ 0.4` (RELEVANCE_THRESHOLD, `generator.py:375`). Flags = `DEMO_FLAGS` completos del
assessment (CHUNKS_TABLE=chunks_v2 · ENUNCIADOS_MULTIVECTOR=on · HYQ_TABLE=on · IDENTITY_RESOLVE=on/ADD ·
RERANK_TOP_K=10 · GENERATOR_SELECTION_BLOCK=on · HYDE off · DIVERSIFY_TIEBREAK off), re-afirmados post-dotenv.
**Instrumentación:** `_trace` por-etapa de `retrieve_chunks` (seam s85 B1) + probes RPC directas (`match_chunks_v2`,
`match_chunks_v2_enunciados`, `match_hyq`) con el MISMO embedding de query. Pools/ranks persistidos en
`scratchpad/phase2_trace_out.json` (+ `phase1_get_out.json`, `phase3_probe_out.json`, `phase4*.json`).
**Caveats declarados:** (1) el LLM-rerank NO es determinista a temp=0 (DEC-096) — pero AMBOS misses son
pre-reranker (not-in-pool), la clase es rerank-independiente; (2) pool cat017 varió 49→50 entre 2 runs (orden del
canal CONTENT), el target ausente en ambos; (3) `match_chunks_v2` con match_count=500 devolvió solo 113 filas
(techo del scan HNSW) — el cos del target se computó directo contra su embedding almacenado.

---

## 1. cat017#2 — "licencia CLIP: una por cada circuito de lazo"

**Pregunta (cat017):** «¿Como se cablea y se da de alta (configura) un lazo en la central Notifier INSPIRE (E10/E15)?»
**Claim (CORE, adjudicado):** «Los dispositivos CLIP requieren una LICENCIA (una por cada circuito de lazo CLIP)».

### (a) Chunks-objetivo verificados VERBATIM (GET, píxel)

| chunk | doc | pág | product_model | quote |
|---|---|---|---|---|
| `5bb83899-9d94-4fdd-8d42-24a670a036c5` (el adjudicado) | `79a3471a` = **HOP-138-9ES issue 5_11-2025_In** | 5 | INSPIRE E10 | «Admite protocolos de Lazo OPAL y CLIP. Los dispositivos CLIP son compatibles con una licencia y **se requiere una licencia para cada circuito de lazo CLIP**» |
| `4c186fb2-aa4b-4ca0-b316-c12ebab59712` (2º carrier, hallado en el sweep ilike) | `484dd402` = **4188-1125-ES issue 5_11-2025_Li** | 17 | INSPIRE Panel | «**Necesitará una licencia de CLIP para cada lazo CLIP**, por lo que se necesitarán dos licencias por módulo si ambos lazos son lazos CLIP» |

El triage previo (que el hecho existe verbatim) **se confirma** — y hay un segundo carrier verbatim que nadie había anclado.
Sweep completo `licencia`+`CLIP`: 11 chunks; SOLO estos 2 llevan el cuantificador por-circuito.

### (b) Traza del funnel REAL (ranks exactos)

- **models:** extract → `['INSPIRE']` (E10/E15 no son modelos del catálogo); resolver ADD → sin expansión.
- **_trace por etapa** (tamaños): channels 78 → post_merge 78 → post_superseded 78 → post_model_filter 48 →
  post_diversify 42 → post_lang 42 → post_hyq_aside 50 → final **50**.
  **Target presente en: NINGUNA etapa** (ni siquiera `channels`). Pool-50: ausente. Top-10: ausente. Served: ausente.
- **Canal vectorial (content-side):** cos(query, chunk) = **0.5751** vs floor del top-50 crudo = **0.6412** (gap 0.066;
  tampoco en las 113 filas que devolvió el scan a 500). El chunk es la página-intro "EQUIPO DEL SISTEMA" — diluido.
  El 2º carrier peor aún: cos **0.4770**.
- **Canal enunciados:** el chunk tiene **0 filas vivas** en `chunks_v2_enunciados` (el doc HOP-138-9ES tiene 17 filas
  vivas de 100 chunks — resto era T2 de R2: **925 insertables generados+QA-passed y ROLLBACKED** con DEC-102;
  ledger `evals/enunciados_ledger.json`: tranche T2/h1, sha `2964cab7…`). El doc del 2º carrier (4188-1125-ES) **ni
  siquiera está en el ledger** (nunca generado).
- **Canal hyq (question-side):** el chunk SÍ tiene 4 filas vivas en `chunks_v2_hyq` (70.134 filas). La mejor —
  «¿Qué protocolos de lazo soporta la Notifier INSPIRE E10 y necesito alguna licencia para usarlos?» — da
  cos = **0.5004** vs query: **rank corpus-wide 335** → el fetch-K=200 de `match_hyq` la corta (floor del top-200 =
  0.5118, gap 0.0114). Y aunque el fetch llegara (probe a 500): post-family (patrón INSPIRE; 61 filas → 43 parents)
  el parent quedaría **rank 36/43** vs **cuota 10** → tampoco entra. Las 10 plazas de la cuota las ganan
  legítimamente preguntas de cableado/conexión INSPIRE (0.546-0.625). Subir fetch-K o cuota NO es el lever:
  el gap es de intención (la query pregunta cableado/alta; el hecho es un PRE-REQUISITO de licenciamiento).
- **Dato nuevo relevante:** el pipeline ACTUAL sí sirve 3 chunks licencia-adyacentes en el top-10
  (`4d76ec50` p7 «modo CLIP… se puede activar a través de una licencia», `e472044e` p15 «será necesaria una licencia
  de lazo CLIP… antes de realizar Auto Configuración», `7a09deff` p2 = TOC). **Ninguno lleva el cuantificador
  por-circuito** (verificado píxel) → explica exactamente la respuesta congelada («CLIP requiere licencia» 2×, sin
  el por-lazo). El miss a nivel-hecho es genuino y sigue vivo con hyq+enunciados+v3.1 ON.

### (c) Clase

**not-in-pool (recall)** — sub-clase **distancia pregunta-tarea** (prerequisito vs intención de la query, la misma
familia que PWR-R/'1 A' en DEC-089). Los 3 canales fallan por mecanismos distintos y medidos: content-side gap 0.066,
question-side rank 335/parent-36-de-43, document-side sin filas (rollback T2).

### (d) Lever legítimo + gate + coste

**Lever: canal enunciados con FUSIÓN POR CUOTA (el fix PENDIENTE pre-registrado de DEC-102) + re-carga T2 del doc.**
Es el brazo que la fila Fine-grained del LEVER_DIGEST deja explícitamente abierto («Fix pendiente = CUOTA del canal
(patrón hyq) con dúo+gate propio; re-carga ≈$1») — no re-litiga nada: la carga 71K SIN cuota fue el NO-GO (crowding
del sort-mixto), la cuota nunca se midió.
- **Gate barato pre-registrable (PRE-carga, sin tocar DB, ~$0.01):** de los dumps T2 locales («a salvo», no
  versionados; si no aparecen, regenerar SOLO el doc con el prompt h1 congelado ≈ $0.26) tomar los enunciados
  QA-passed del chunk `5bb83899`, embedirlos offline y computar cos vs el embedding congelado de la query cat017;
  GO ⇔ alguno cruza el corte de cuota parent-level del canal enunciados en esa query (computable gratis con el RPC).
  Anti-overfit: SOLO enunciados chunk-side ya generados/QA (h1, no query-aware) — nada redactado mirando el gold.
- **Si NO-GO → cat017#2 se declara RESIDUAL formalmente** (lo que s188 release_boundary.next y PLAN ya prescriben);
  las demás vías están medidas muertas: facet quantified_entitlement = NO_GO s174 (3 TPs, todos Notifier), heldout
  s114 0/24.
- Coste total del lever si GO: re-carga con cuota ≈ $1 (DEC-102) + gate dúo propio; decisión de Alberto (presupuesto).

### (e) Nota ruta viva

Este diagnóstico es de la **ruta harness** (sin handler). En la ruta Telegram el gate del handler puede pedir
aclaración INSPIRE/CLIP antes de llegar al retrieval — no cambia la clase del miss, pero un PASS/FAIL vivo no es
comparable 1:1 con esta traza.

---

## 2. hp010#1 — "Nivel 3 + desbloquear memoria; menú Lazos tecla 2"

**Pregunta (hp010):** «En la Morley DXc, ¿cómo se añade un nuevo detector al lazo tras la puesta en marcha inicial?»
**Claim (CORE, adjudicado):** «acceder al Nivel 3 (clave de acceso) y desbloquear la memoria; en el menú de Lazos
pulsar '2' para Autobúsqueda…» — miss PARCIAL multi-span dentro del mismo manual.

### (a) Chunks verificados VERBATIM (GET, píxel)

| chunk | doc | pág | rol | quote |
|---|---|---|---|---|
| `155a90fe-8c3f-484e-a617-7637fe29b547` (**target del miss**) | `d1299a40` = **DXc_Manual de configuracion** | 37 | prerequisito acceso/desbloqueo | «Introduzca la clave de acceso de Nivel 3 y pulse ⊙… Memoria Bloqueada / Presione OK para desbloquear… Pulse ⊙ de nuevo para desbloquear la memoria (el puente J5… debe estar puesto)» + menú `[Programar] … 2:Lazo` |
| `64cecd3f-204f-456e-91cc-e563280b1b99` (span hermano) | mismo doc | 48 | autobúsqueda | «Pulse la tecla '2' en el menú de Lazos para seleccionar la función 'Autobúsqueda'…» |

### (b) Traza del funnel REAL (ranks exactos)

- **models:** `['DXc']` → resolver ADD `['DXc','DXc1','DXc2','DXc4']`.
- **Span p48 (control interno):** presente en TODAS las etapas; **pool rank 26** (sim 0.4672, canal VECTOR) →
  **rerank #1** → **SERVIDO**. Reproduce s114 («el span de autobúsqueda SÍ se sirve») y demuestra que el reranker
  promueve procedimiento DXc desde el fondo del pool.
- **Target p37:** `channels: false` → nunca entra (todas las etapas false). Pool 28 (el model-filter DXc deja 28 de 74).
- **Canal vectorial:** cos(query, p37) = **0.3379** vs floor top-50 crudo = **0.4556**. Muy lejos — gap de vocabulario
  real (la página habla de niveles de acceso/claves, la query de añadir un detector).
- **Canal hyq:** 3 filas vivas del chunk; cos vs query = **0.2760 / 0.1944 / 0.1563**, todas « barra 0.45
  (`match_hyq` solo devolvió 6 filas ≥0.45 para esta query, ninguna DXc → family-fallback global). Canal inerte aquí.
- **Canal enunciados — EL HALLAZGO:** la fila viva «El menú principal del DXc presenta la opción **2:Lazo** para
  acceder a la configuración del lazo de detección» (id `715ed152…`, parent = p37) SALE del RPC de enunciados:
  **rank-14 por fila, sim 0.4268; rank-6 entre parents NUEVOS** (7 entre todos; 39 parents en el top-200).
  Muere EXCLUSIVAMENTE en el **cap del sort-mixto**: `merged = reales + parents; sort; [:50]` con floor real
  0.4556 > 0.4268 → cortado DENTRO de `vector_search` antes de llegar a `channels`. Es, medido en vivo, el mecanismo
  exacto que DEC-102 nombró («crowding del sort-mixto sin cuota») — aquí visto matar un CORE adjudicado.

### (c) Clase

**not-in-pool (recall)** — sub-clase **surrogate-recuperado-cortado-en-fusión**: el documento-side YA tiene el
puente (fila viva en tabla, sin re-carga), el canal lo recupera a rank-6-de-parents, y la fusión sin cuota lo tira.
Fix de PIPELINE, no de ingesta.

### (d) Lever legítimo + gate + coste

**Lever: la MISMA cuota del canal enunciados (patrón hyq, DEC-102 pendiente)** — espejo de la fusión-por-cuota
shippeada para hyq (DEC-099: `results[:top_k−Q] + top-Q parents`; escalas incomensurables ⇒ el sort-mixto es
estructuralmente injusto con el canal chico). Con Q≥6 el parent p37 entra al pool; aguas abajo: model-filter DXc
pasa (pm=DXc), pool 28<50 sin presión de cap en diversify, `0.4268 ≥ 0.4` = servible si el reranker lo elige (el
mismo reranker subió p48 de pool-26 a #1; no se afirma el flip sin medirlo — lo decide el gate).
- **Gate barato pre-registrable:** (i) replay determinista de la fusión con cuota sobre los pools persistidos de
  este diagnóstico ($0 modelo) → confirmar entrada-al-pool; (ii) e2e de la pregunta = 1 rerank (~$0.05);
  (iii) las guardas ya pre-declaradas del gate DEC-102: flips testbed s94 reproducen + anti-dilución anclas-OK
  old-vs-new + famtie (STOP si <2 mejoran in_pool). **Coste: ~$0 DB (la tabla ya está cargada para este doc), sin
  re-carga; solo el gate.**
- **Alternativa declarada (no primaria):** re-scope per-facet del gate s174 — el facet `access_prerequisite` PASÓ
  sus umbrales de independencia (8 TPs / 7 fabricantes) y la lane determinista s114
  (`src/rag/procedure_bundle_coverage.py`) recupera este chunk en local; pero reabrir un gate conjunto por-facet es
  decisión explícita (riesgo gate-shopping, declarado en el packet s269) y la cuota-enunciados lo subsume por
  mecanismo GENERAL (no per-fact). Si la cuota falla su gate, esta es la segunda vía.

---

## 3. Resumen y contraste con levers SETTLED

| miss | ¿verbatim en corpus? | muere en | clase | gap exacto | lever propuesto | coste gate |
|---|---|---|---|---|---|---|
| cat017#2 | SÍ (2 carriers: HOP-138-9ES p5 + 4188-1125-ES p17) | antes de `channels` (los 3 canales) | not-in-pool (recall) · distancia pregunta-tarea | content 0.575 vs 0.641 · hyq rank-335 / parent 36-de-43 vs cuota-10 · enunciados 0 filas (rollback T2) | cuota enunciados + re-carga T2 del doc (brazo pendiente DEC-102); **gate offline PRE-carga**; NO-GO ⇒ residual formal | ~$0.01 (dump local) o $0.26 (regen doc) |
| hp010#1 | SÍ (DXc-config p37) | cap del sort-mixto DENTRO de `vector_search` (canal enunciados) | not-in-pool (recall) · surrogate-recuperado-cortado-en-fusión | fila viva sim 0.4268, parent rank-6-nuevos vs floor real 0.4556 | cuota enunciados (patrón hyq) — SIN re-carga, fila ya viva | $0 replay + ~$0.05 e2e |

**Un solo mecanismo cubre ambos** (cuota del canal enunciados = el fix pendiente pre-registrado de DEC-102);
cat017#2 además necesita la re-carga T2 de su doc y tiene GO incierto (el gate offline decide barato).

**Levers NO propuestos (SETTLED, no re-litigados):** consumo aditivo del pool (DEC-069/084 — la cuota NO es aditiva:
desplaza cola del canal real, mecanismo ya shippeado en hyq/DEC-099); FTS/BM25-sobre-pregunta (DEC-085 — los tokens
aguja no están en la pregunta: «licencia» no aparece en cat017 ni «nivel 3» en hp010); tie-break coseno (DEC-091/s101
NO-GO definitivo); afinar reranker (DEC-092 — irrelevante: ambos misses son pre-reranker); ancho top-10 (ya shippeado
DEC-092b, no alcanza lo que no entra al pool); neighbor-window/ef_search/más-contexto (s86 medidos — p37↔p48 no son
vecinos); multi-gran cruda y HyDE-solo (DEC-085/086); re-tuning de knobs hyq (fetch-K/cuota/barra — medido aquí que
NO rescataría a ninguno de los dos: cat017 parent-36, hp010 cos 0.16-0.28 « 0.45); lane s114 per-fact
manufacturer-scoped (clase rechazada en review s114; s174 NO_GO para quantified_entitlement).

**Artefactos del diagnóstico** (scratchpad, no versionados): `phase1_get_out.json` (verbatim + cobertura tablas),
`phase2_trace_out.json` (pools/ranks/trace por etapa + top-10 + served), `phase3_probe_out.json` (carriers, cos hyq,
floors), `phase4_probe_out.json` / `phase4b_out.json` (ranks parent-level). Scripts `phase{1,2,3}_*.py` reproducibles
contra `origin/main@5774a6c`.
