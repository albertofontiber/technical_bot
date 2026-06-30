# s84 — Within-doc vector re-retrieval: revisión adversarial (Protocolo 3, zona de dolor retrieval → cross-model INNEGOCIABLE)

**Qué reviso:** la propuesta de reemplazar el suplemento within-doc por una búsqueda vectorial scoped, ANTES de cablear. Muerde: (1) ¿es NO-OP encubierto o de verdad mueve el eval? (2) ¿regresa golds (desplazamiento, como el F1 hp012)? (3) ¿la validación de 3 casos es suficiente o cherry-picked? (4) ¿es el fix estructural correcto o hay uno más de raíz?

## Diagnóstico (verificado, no asumido)
El funnel corregido por juez semántico: de los misses de retrieval REALES (27), 16 son "within-doc" no-es-en. Workflow de 16 agentes + verificación al código:
- **Familia 1 (10/16): el canal léxico within-doc se rompe ANTES de rankear.** `_fetch_top_chunks_by_source_file` (retriever.py:1700) usa FTS por keywords: (a) `extract_search_keywords` (l.366) hace `unique[:3]` por orden ANTES de quitar identidad → verbos de framing (`está`/`tengo`/`dando`, NO en STOP_WORDS pese a que `esta`/`quiero`/`necesito` SÍ) consumen los 3 slots, los discriminantes (`flujo`/`aire`/`detector`/`lazo`) caen fuera; (b) `plfts 'a & b & c'` AND-estricto elimina el chunk si le falta 1 término; (c) fallback ilike limit=2.
- **Familia 2 (6/16): brecha de representación** (terminología `alta detector`↔`autobúsqueda`; spec-tables).
- **es-en = 0** (refutado al píxel: los 16 chunks-respuesta son ES).
- +2 especiales: cat013-CLIP (respuesta en manual no-nombrado = refuse-inference esperado), cat017-159 (`content_search` per-model con `limit=10` SIN `order` = bug aparte).

## Hecho ya / substrato (NO re-litigar)
- **Contextual Retrieval YA aplicado** (`src/reingest/embed.py:53`: embebe `context+content`; 25.090/25.090). Los embeddings están al máximo → NO es un lever pendiente.
- **DEC-066**: identidad (resolución de qué doc) NO movió el eval; el índice inverso fue NO-OP. **DEC-056**: ranking/reranker agotado (matizado: rerank-miss subió a 12% con el juez semántico).
- F1 (IDENTITY_INDEX) revertido = NO-OP-con-regresión (hp012: la unión aditiva desplazó 2 chunks-con-hecho fuera del pool-50).

## Propuesta
Reemplazar el FTS-por-keywords within-doc del diversify por una **búsqueda VECTORIAL scoped al source_file**: usar el embedding de la query (ya calculado) + un RPC/consulta pgvector filtrada por `source_file=eq.<doc>`, devolver top-k por distancia coseno. Elimina la dependencia de keywords (Familia 1 desaparece, no se parchea) y maneja terminología (Familia 2). Es hierarchical/two-stage retrieval canónico (grueso: qué docs ya está en el pool; fino: vector dentro de ellos).

## Validación empírica (sobre embeddings CONTEXTUALES, no cherry-pick — 1 por familia)
Rank del chunk-respuesta en vector-within-doc (el FTS actual los pierde TODOS):
- hp002/300s (Familia1-keyword): **#5** | cat016/autobúsqueda (Familia2-terminología): **#3** | cat017/OPAL (spec-table): **#1**.
Los 3 entran en top-5 within-doc → el scoping rescata lo que la competencia global (25k) entierra.

## Alternativas descartadas
- **Parche de keyword-extraction** (cap-después-de-strip + stopwords + AND→OR): arregla solo Familia 1, deja el canal léxico-frágil. Es parche, no estructural.
- **Contextual Retrieval**: YA hecho (no es opción).
- **Cross-lingual/HyDE**: es-en=0 en este lote → 0 casos.
- **Mejorar el retrieval GLOBAL** (que el chunk gane entre 25k): los embeddings ya son contextuales y aun así pierde por competencia → el scoping es el lever contenido correcto.

## Gaps/riesgos declarados
1. **Reach ≠ PASS**: recuperar el chunk es necesario, no suficiente — la generación debe usarlo (downstream/SÍNTESIS 63%). Por el principio upstream→downstream puede destrabar síntesis, pero NO garantizado.
2. **Riesgo de regresión** (como F1 hp012): añadir chunks within-doc al pool puede desplazar otros en el top-k antes del rerank → MEDIR no-regresión por-gold sobre los no-target.
3. **Coarse-first**: si el doc no se selecciona (cat013-CLIP), el within-doc no rescata nada. Acotado a los casos donde el manual YA está en el pool (16/16 lo están).
4. **Sims modestas** (0.52-0.66): top-5 pero no slam-dunk → el within-doc vector suplementa con recall, el reranker decide precisión.
5. **Coste/infra**: requiere RPC pgvector con filtro source_file (cambio modesto; el match_chunks ya tiene filter_product). Una búsqueda vectorial por source relevante.
6. **Validación n=3**: 1 por familia, no los 16 → el delta REAL se mide en el funnel corregido sobre los 39, no en 3 casos.

## Por qué BP + estructural + escalable
Un solo mecanismo de retrieval (vector) en vez de dos (vector global + FTS within-doc); elimina una clase entera de bugs (keywords/AND/ilike); patrón canónico (hierarchical retrieval); escala a 30+ sin tocar keywords ni por-gold.
