# s95 · Redesign del mecanismo enunciados — plan de DOS pilotos (pre-registro **v2 post-dúo**)

> v1 → v2: el dúo (sub-agente Fable fresco + cross-model GPT-5.5 con tools) produjo
> **15 hallazgos, 15 confirmados regla-C, 0 FP** (3+1 críticos). Cambios integrados abajo,
> marcados [D#]. Tally: `evals/adversarial_review_log.jsonl` 2026-07-04.
> GO de Alberto al enfoque de 2 pilotos. Nada se cablea a demo; flag-off / tabla nueva / medición.

## Contexto (medido)
- **DEC-086:** enunciados→swap-al-padre = famtie 12→6 con 251 surrogates dirigidos/transitorios.
- **DEC-088 (T1):** mismo mecanismo, 21.995 surrogates en el HNSW COMPARTIDO = NO-GO
  (dilución post-filtro 12→19; multivector 13 neto peor que 12; cadena 12→19→17→12 verificada).
- **Research s95 (3 agentes, fuentes verificadas):** BP unánime = surrogates en su PROPIO
  índice (LangChain MultiVector, LlamaIndex, Dense X, Pinecone namespaces; pgvector README:
  índice parcial/tabla aparte para filtro binario). **Dense X: +2.2 Recall@20 con embedder
  fuerte** → prior de A REBAJADO. Agentic RAG general NO paga para nuestro perfil (ACL 2026);
  la variante quirúrgica (router/deep-lookup) sí tiene evidencia (TableRAG +10%).
- Repo-audit: extraction store cubre 100% de los docs-target; resolver da doc-target 8/9
  qids-miss; seam `IDENTITY_FETCH` existe (NO-OP s93 = selector léxico, no el mecanismo).

## Métrica y controles (la misma vara que DEC-086/088)
- **Primaria:** retrieval-miss famtie (132 hechos, presence votes≥4 en pool_pin top-50).
  Control vigente = **12** (post-VACUUM, lista idéntica s92). El harness `scripts/t1_gates.py`
  re-mide control+treatment en la MISMA corrida y config (HYDE off, IDENTITY on/add, POOL_K=50).
- **[D1, CRÍTICO ambos lados] Set canónico de flips = `scripts/t1_gates.py:44-46`** (NO
  `t1_gates.json::flips_dec086`, que son los 2 reproducidos en T1): **{hp006·'Fallo de
  Tierra', hp012·'99 + 99', hp012·'2 lazos / 396', hp013·'PWR-R', hp014·'35', hp018·'1 A'}**.
  (El v1 citaba mal ISO-X — es flip de R3/total, no del set.) **Caveat '99+99' pre-registrado:**
  DEC-086 lo lista como flip COLATERAL (clase diversify, como hp011). Si el criterio ≥4/6 se
  cumple SOLO gracias a '99+99' (=3/5 sin él), el veredicto es **AMBIGUO** y se adjudica con
  el trace del mecanismo — no PASS post-hoc. hp011 no está en el set (no cuenta en A/D).
- Golds held-out embargados. Coste total pre-registrado: ~$5-15.

## Piloto A — separación de índice (el fix de libro) · ~$3
**Mecanismo:** re-insertar los 21.995 enunciados del dump `evals/t1_surrogates_dump.jsonl`
(verificado completo; NO trae embeddings) en tabla NUEVA `chunks_v2_enunciados` con su
PROPIO HNSW. La tabla/índice de chunks reales NO se toca.

**Schema pre-registrado [D6]:** columnas del dump + embedding vector(1024);
`parent_id UUID NOT NULL REFERENCES chunks_v2(id) ON DELETE CASCADE` — **CON
`CREATE INDEX ... ON chunks_v2_enunciados(parent_id)`** (lección migración 009: FK sin
índice = seqscan por-fila en cada DELETE de chunks_v2). El CASCADE acopla la tabla al
pipeline de re-ingesta vivo (deseable: huérfanos imposibles) — declarado. HNSW con
`ef_search=120` pineado en el RPC (mismo vintage). Rollback: `DROP TABLE` (no toca chunks_v2).

**Receta de embedding pineada [D8]:** exactamente la del pase T1
(`enunciados_pass.py:229-233`): `f"{context}\n\n{content}"` si hay context, si no `content`;
`embed(texts, "document")` (Voyage voyage-3, batches de 100).

**Cableado pre-registrado [D2, CRÍTICO — era parámetro libre]:** no existe seam para un 2º
RPC (`vector_search` llama fijo a `match_chunks{RPC_SUFFIX}`, retriever.py:909). Diseño:
con `ENUNCIADOS_MULTIVECTOR=on`, `vector_search` hace una **2ª llamada** a
`match_chunks_v2_enunciados(query_embedding, match_threshold=0.3, match_count=top_k)`
(mismos threshold/count que el RPC real) y **fusiona: unión de ambas listas → sort por
similarity desc → truncar a top_k** = un solo ranking con el MISMO cap que T1 (misma
semántica de competición, sin el artefacto de índice). Los resultados entran PRE-swap →
`_enunciados_swap` corre SIN cambios (detecta `parent_id` en fila, hidrata padre de
chunks_v2). Estos 4 parámetros (threshold, count, ef, punto de fusión) quedan PINEADOS:
cambiarlos = brazo nuevo declarado, no tuning.

**Gates:**
- **A-G1 reproducción:** famtie flag-on **≤8** y **≥4/6** flips del set canónico [D1].
- **A-G2 no-regresión:** control flag-off DEBE seguir en 12 (si no → parar: tocamos algo);
  flag-on 0 nuevas-miss fuera de ±2.
- **A-G3 smoke anti-cableado [D9]:** panel flag-off = no-op (tautológico por diseño — vale
  como smoke de que el flag no filtra al path de servicio, no como gate informativo).
**Predicciones:** control 12 intacto; flag-on 6-10. El riesgo abierto que A mide: el
enterramiento del enunciado entre sus 21.995 hermanos DENTRO del índice de surrogates.

## Piloto D — deep-lookup agéntico en el seam IDENTITY_FETCH · ~$5-10
**Framing honesto [D5-cross]:** REAPERTURA declarada del seam de DEC-084 (fetch-acotado,
exhausto con selector LÉXICO) con criterio NUEVO (selector LLM) — no "ortogonal". El digest
dejó pre-registrado que el NO-OP fue del selector ("los appends llegan, el selector léxico
no elige los chunk-ids juzgados").

**Mecanismo:** en `fetch_missing_doc_chunks`, para queries gatilladas (SPEC_INTENT +
producto resuelto con doc-target ausente del pool), un selector LLM (Haiku 4.5; fallback
Sonnet declarado si el smoke muestra misses de selector) recibe el **outline del doc desde
el extraction store** (por página: headings + títulos/primeras-filas de items type=table —
**NO pre-filtro por keywords de la query** [D3, CRÍTICO: un pre-filtro léxico re-introduce
el techo DEC-085 aguas arriba del LLM]) y elige las páginas que contienen el dato → se
appendean los chunks DB de esas páginas.

**Pre-condiciones de build [D-cross-1, CRÍTICO]:** `fetch_enabled()` hoy es booleano
(catalog_resolver.py:314) — `IDENTITY_FETCH=llm` sería NO-OP SILENCIOSO. El build incluye:
parser 3-estados (`off/on/llm`) + test fail-fast (flag=llm sin IDENTITY_RESOLVE=on → error)
+ test de que `llm` activa el brazo. Sin esto no se mide nada.

**Regla de selección pre-registrada [D4]:** chunks de la página elegida primero, luego ±1
(drift store↔DB conocido), orden estable por `chunk_index`; cap por doc para el brazo llm:
**6** (no los 3 del léxico — la ventana ±1 no cabe en 3); **sin re-corte léxico** (nada de
`_score_chunk` — re-introduciría el techo).

**Gate-0 recall-safe ($0, sin LLM) [D3]:** ANTES de la famtie: para los qids-miss con
doc-target, ¿la página-aguja (conocida por `citations` de los golds) está en el outline que
verá el LLM? Debe ser **8/8** (los qids con doc-target); si no → arreglar el outline antes
de gastar. Se reporta como sub-métrica.

**Gates:**
- **D-G1:** famtie con `IDENTITY_FETCH=llm` ≤8 y ≥4/6 del set canónico [D1] + mismo caveat '99+99'.
- **D-G2 [D5]:** guard de JITTER solamente (mecánicamente el append post-cap NO puede crear
  nuevas-miss famtie — el pool solo crece). El desplazamiento REAL de D vive post-rerank:
  se reporta el **rank post-rerank** de los chunks appendeados-con-aguja (¿sobreviven al
  top-10?) como métrica informativa pre-registrada, sin gate duro (primera medición).
- **D-G3 coste/latencia:** por query gatillada: <15k tokens input selector; <5s p50 añadidos.
- **D-G4 tasa de gatillado [D9]:** **≤25%** de las 59 queries del panel (si gatilla más → el
  gate de intención está mal y se endurece antes de seguir).
**Predicciones:** gate-0 8/8 (el store cubre los docs-target); famtie 6-9; el riesgo real =
selección de página en docs de 50-260 pp + supervivencia post-rerank (sin medir, declarado).

## Tabla de decisión [D7: "pasa" = G1∧G2; rama parcial añadida]
| resultado | decisión |
|---|---|
| A pasa (G1∧G2) y D no | arquitectura de re-ingesta = tabla separada; T2-T3 vuelve a decisión de presupuesto (Sonnet 5) **con gate famtie POR-TRAMO arrastrado** (el enterramiento crece con el volumen — +29% p2; A-pasa con 22k NO zanja 100k+) |
| D pasa y A no | NO re-ingesta ($0 corpus); deep-lookup a hardening (dúo build) + bvg antes de flag-on |
| ambos pasan | comparar coste marginal (A one-off + índice vs D por-query recurrente) → decisión Alberto |
| **parcial informativo** (G1 falla pero famtie 9-11 con control intacto y 0 regresiones) | NO auto-archivar: mejora real parcial → dossier a Alberto con el trace por-hecho; decidir si el delta paga su coste |
| ninguno pasa ni parcial | mecanismo enunciados-para-retrieval se ARCHIVA con traza; residual 12 = techo del canal vectorial; opción E (tabla estructurada + router, TableRAG) queda como único camino, workstream aparte |

**Fuera de alcance s95:** opción E (retrieval estructurada/SQL); hp011 (diversify, no está
en el set de flips). Orden de ejecución: A primero (más barato/rápido, aísla la pregunta de
arquitectura), D después — son independientes; si A-G1 pasa holgado, D se corre igual (la
tabla de decisión necesita ambos brazos).
