# s93 · BAKE-OFF fine-grained — resultados y artefacto de decisión (h7)

> Plan: `evals/s93_finegrained_gate0_plan.md` v3.2 (track A dúo PR #110; tracks B/C/HyDE
> dúo 2-jul: cross-model 7 hallazgos [2 CRÍTICOS confirmados contra código] + sub-agente
> F1-F7; correcciones aplicadas ANTES de ejecutar). Testbed: 11 miss-facts del pin
> `s92_retrieval_miss_ON_add.yaml` (famtie 12/132; guard anti-circularidad excluyó
> hp006 'Tierra'). **Freeze:** voyage-4-large doc/query · HYDE_ENABLED=false (salvo brazo
> HyDE) · pin s92 · catálogo en git · SQL read-only proyecto izooestgffgscdirkfia.

## PASO 0 (trace por-etapa, sub-agente F4) — re-atribución ANTES de medir
30/31 chunks-soporte **NUNCA entran a ningún canal** → clase fine-grained confirmada al
mecanismo. **1 excepción: hp012 '99 + 99'** — entra al canal y muere en `post_diversify`
(la forma DEC-069 en pequeño, ya anotada en s92) → **NO es fine-grained; su fix es el
lever diversify, no la ingesta** → excluido del testbed B/C (n=10).
Artefacto: `evals/s93_paso0_trace.json`.

## Tabla h7 — mecanismo × hechos-ganados × coste-de-escalar

| track | mecanismo | evento (barra) | resultado | hechos ganados | coste de escalar | naturaleza de la cifra |
|---|---|---|---|---|---|---|
| **A** | FTS/tsvector re-ruteo (query-side, $0) | sup en top-20 FTS, matriz {AND,OR}×{con,sin modelo} | **1/11 → NO-GO** (<3 pre-registrado) | hp006-FdT (pos 1) | ≈0 cablear | medición sobre el canal real |
| **B** | multi-granularidad (span-oráculo determinista) | cos ≥ sim#50 del canal vectorial REAL ±0.003 | **1/10** (+2 FLAG sin-literal) | hp006-FdT (0.612>0.532) | re-ingesta ~$150-300 | señal (probe optimista: sin fusión/filtros) |
| **C** | **extracción-tablas → ENUNCIADOS** (LLM, micro-slice 4 hechos) | ídem B | **2/4 ✅** (predicción ≥2/4 cumplida) | hp011 (0.591>0.539) · hp012-'2 lazos/396' (0.621>0.569) | re-ingesta + pipeline extracción ~$150-300 | muestra diagnóstica 4 hechos, NO comparable 1:1 |
| HyDE | query-side (hipótesis registro-manual) | cos padre/span ≥ sim#50 EN SU ESPACIO | **0 WIN / 1 TIE / 10** | — (comprime gaps: hp012 0.006, hp001 0.011, hp018 0.016 — no cruza solo) | ≈0 (flag existente) + 1 Haiku/query | probe 1-muestra (jitter declarado) |

**Controles del gate-0 (H9, 6 golds sin miss):** el top-20 FTS solapa solo 0-15/20 con el
pool sano → un re-ruteo con stamp 0.70 metería 12-19 chunks nuevos POR ENCIMA del ranking
vectorial = riesgo-desplazamiento medido (refuerza el NO-GO de A por el lado del daño).
AND-pregunta-completa ≈ 0 matches corpus-wide (5/6 controles) — celda inutilizable.

## Hallazgos de mecanismo (lo que el bake-off ENSEÑÓ, no solo contó)
1. **El cuello dominante es el gap query↔celda, no el tamaño del chunk per se:** en 5/8
   spans medibles, el span AISLADO embebe PEOR que su padre (aislar ALEJA); ni el léxico
   sobre la pregunta (A) ni el coseno del span crudo (B) alcanzan la barra. Lo que SÍ la
   cruza es la **ENUNCIACIÓN** (C): fila + producto + sección como frase técnica.
   Corrige el framing s86 "aguja-en-chunk-grande": la aguja no solo está enterrada —
   está escrita en otro idioma que la pregunta.
2. **Los 2 FLAG de B** (hp018 '1 A', hp012 '2 lazos/396' sin match literal del valor en
   una línea) son la clase celda-compuesta; C ganó 1 de ellos (hp012) vía enunciado.
3. **hp006-FdT** es el único hecho que A y B ganan: su pregunta comparte vocabulario raro
   ('tierra','fallo','aviso') con el soporte — la excepción que confirma el mecanismo.
4. **Anomalías de instrumento cazadas por regla-C en el propio run** (honestidad):
   (a) mi evento v1 de B usaba la frontera del pool FINAL (demasiado optimista — 8/10
   "WIN" falsos; corregido a la frontera corpus-wide del RPC real: 1/10);
   (b) el brazo HyDE 1ª pasada midió un NO-OP (fallback silencioso `hyde.py:84` sin
   HYDE_ENABLED — cosenos idénticos al espacio crudo dentro del drift ±0.003; re-corrido
   con hipótesis real); (c) 2/31 sup son `duplicate_of` (invisibles al RPC para siempre;
   sus gemelos primarios sí recuperables — anotado, no explica la clase).

## Recomendación (decisión de presupuesto = Alberto)
- **El mecanismo que financia el workstream de ingesta es EXTRACCIÓN-TABLAS→ENUNCIADOS**
  (único con hechos ganados que nada más gana, 2/4 con margen). La multi-granularidad
  cruda NO paga sola (1/10) — la granularidad útil es la que produce la extracción
  estructurada (que de paso ES multi-granular). ~$150-300 corpus-wide + pipeline;
  siguiente paso natural si se aprueba: piloto sobre los ~6 docs del testbed y famtie.
- **FTS re-ruteo: NO-SHIP** (NO-GO 1/11 + desplazamiento medido en controles). El NO-GO
  honesto pre-escrito: "FTS-Postgres (ts_rank sin IDF) no basta" — pg_search (BM25 real)
  sigue disponible query-side, pero la evidencia de mecanismo (los tokens-aguja no están
  en la PREGUNTA) predice que BM25-sobre-pregunta hereda el mismo techo (coherente con
  DECISIONS:187 "si falta el literal, BM25 tampoco").
- **HyDE solo: no** (0-1/10); queda anotado que comprime gaps → re-evaluable COMBINADO
  con enunciación post-re-ingesta (no antes; un lever cada vez).
- **hp012 '99+99' → lever diversify** (muere en post_diversify con soporte en canal):
  candidato barato separado, fuera del workstream ingesta.
- **Nada se cablea en esta sesión:** flags intactos (FTS_ALL_QUERIES no se construyó —
  gate-0 NO-GO; IDENTITY_FETCH sigue NO-SHIP; HYDE_ENABLED sigue off).

Artefactos: `s93_gate0_testbed.json` · `s93_gate0_sql/` · `s93_gate0_results.json` ·
`s93_paso0_trace.json` · `s93_trackB_results.json` · `s93_trackC_hyde_results.json`.

## Validación BP (pregunta de Alberto, 3-jul; research 4 ángulos con fuentes web)
**Extracción-tablas→enunciados ES práctica establecida**, con nombres canónicos:
- **Frameworks/vendors**: "multi-vector retriever" (LangChain, blog oficial semi-structured RAG),
  "recursive retrieval / small-to-big" (LlamaIndex, pdf_tables), **"language model augmentation"
  (Azure Architecture Center, guía oficial de chunking 2026 — lista 'technical manuals,
  maintenance guidelines' como caso de uso)**, "table annotation" (Google Vertex layout parser).
  Unstructured.io diagnostica EXACTAMENTE nuestro gap: "Embedding raw table content often
  produces poor retrieval results because vector models are optimized for natural language".
- **Academia**: "table verbalization" fila-a-fila (UDT-QA, ACL 2022: +3.4 EM en NQ indexando
  tablas verbalizadas; KELM/TEKGEN NAACL 2021); **Dense X (arXiv:2312.06648): la unidad fina
  solo funciona "contextualized and self-contained" = nuestro hallazgo B-vs-C medido de forma
  independiente** (span aislado pierde, enunciado-con-contexto gana); DTR (NAACL 2021): los
  retrievers densos genéricos fallan sobre tabla cruda (nuestro síntoma).
- **Industria**: TabRAG (Imperial College, arXiv:2511.06582, nov 2025) = el mecanismo exacto
  (estructura→descripción natural que preserva el contenido factual→índice), 92.4% vs 66.8%
  del mejor parser-baseline en TAT-DQA.

**3 matices del research que REFINAN el diseño del piloto** (adoptados como spec):
1. **Desacoplar retrieval de síntesis (el patrón canónico)**: el enunciado se EMBEBE para
   retrieval pero la cita/síntesis debe venir de la tabla FUENTE — cada enunciado lleva
   puntero a chunk/página original y idealmente arrastra el chunk-tabla al contexto. Sin esto,
   un valor alucinado en la extracción llegaría al técnico como cita de manual (riesgo
   RD-TableBench: los VLM/LLM "confidently hallucinate rows"). Crítico para nuestro contrato
   "responde SOLO desde manuales".
2. **Brazo plantilla-determinista en el piloto**: Pinecone (experimento oficial) midió que
   concatenar fila+cabeceras rinde igual que la frase fluida LLM; Herzig valida linearización
   sin LLM. Una plantilla `producto · sección · cabecera=valor` cuesta ~$0 y no alucina →
   el piloto compara plantilla vs enunciado-LLM ANTES de pagar el pase completo (puede
   recortar mucho el ~$150-300).
3. **Límite documentado (Smile.eu)**: filas que solo difieren en números colisionan en
   embedding (>95% idénticas) — directamente relevante a nuestras familias de variantes
   (CAD-150-1/-2/-4/-8 por lazos): el enunciado DEBE llevar el discriminador de variante.
   Y el coste de QA de la extracción no está en el ~$150-300 — presupuestarlo aparte.

**Lo que el mecanismo NO cubre (settled con métrica distinta, no usarlo en contra)**: queries
ANALÍTICAS/agregación sobre tablas → la práctica ahí es text-to-SQL routing (AWS GenAIIC,
LlamaIndex SQLAutoVector) — nuestros misses son lookup-de-celda-única, no agregación; los
rerankers no aplican (el fallo es recall del primer stage); ColBERT también sería re-ingesta
y no cierra un gap de solapamiento-cero de tokens. Higiene: 1 cita fantasma detectada y
descartada durante la verificación (TTQA-RS no hace lo que un resumen le atribuía).
