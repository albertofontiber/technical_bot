# s84 — Re-medir el canal vectorial muerto (L-i) + within-doc vector (c) en RETRIEVAL-MISS, no PASS

**Qué reviso (Protocolo 3, zona de dolor retrieval → cross-model INNEGOCIABLE):** el DISEÑO del experimento ANTES de cablear, y sobre todo **la legitimidad metodológica** — porque estoy revirtiendo un "settled" mío (DEC-040 L-i = ROLLBACK). Muerde: (1) ¿re-medir L-i en retrieval-miss es legítimo o es #51 re-litigación racionalizada? (2) ¿retrieval-miss es la métrica correcta o nos auto-engañamos (un win de recall que nunca convierte a PASS = 0 valor)? (3) ¿el diseño de arms/freeze/push-out es sólido? (4) ¿"arreglar el bug del filtro de categoría por principio" tiene consecuencias ocultas?

## Hecho verificado (no asumido)
- **Bug confirmado (DEC-040 + re-verificado s84):** `chunks_v2.category` muerta desde el SWAP s44 (0 filas de la taxonomía canónica). En **stamps** (prod, `MERGE_STRATEGY` default), el canal vectorial principal filtra por `detected_category` → **0 filas en el 85% de queries**; cae al broad-5 → filtrado a modelo → ~0 sobrevive. Medido s84: **hp002 pool = VECTOR 0** (solo CONTENT 12 + MODEL 5). **9/10 de los within-doc misses detectan categoría** → canal vectorial muerto.
- **L-i ya medido (DEC-040, s59):** quitar el filtro de categoría del canal vectorial. Gate: **surfaceó los chunks** (los 11 al pool-50, mayoría top-5: hp002×2, hp008×4, cat017, hp001-2222). A/B PASS K=5: **ROLLBACK, Δ_net=0** (gana cat020/hp001/cat012, pierde cat005/cat009/cat010 = **3-2 frontera del JUEZ**, downstream). L-ii (ef_search=120) **aplicado en prod** (s59b).
- **Instrumento NUEVO (s84):** el funnel + juez semántico mide **retrieval-miss directamente** (artifact-aware) — lo que s59 no podía (PASS confundía retrieval+síntesis).

## La tesis metodológica (lo que el dúo debe juzgar)
DEC-040 rechazó L-i por **PASS Δ_net=0**. Pero PASS mezcla retrieval+síntesis, y las pérdidas eran **juez-frontera 3-2 (downstream), no pérdidas de retrieval**. Por el principio upstream→downstream (Alberto), el objetivo AHORA es **reducir retrieval-miss primero**; por ESA métrica L-i FUNCIONÓ. **Afirmación a refutar:** re-medir L-i en retrieval-miss NO es #51 (re-litigar la MISMA medida) — es una métrica DISTINTA, ahora posible (juez semántico) y alineada con el objetivo actual. **Riesgo declarado:** si el win de retrieval-miss NUNCA convierte a PASS (porque el merge/síntesis siempre redistribuye — DEC-041/056), habríamos optimizado un intermedio sin valor. Por eso se mide PASS también, como secundaria/guardarraíl.

## Diseño del experimento
**Freeze:** corpus chunks_v2 + ef_search=120 (prod) + stamps merge + juez GPT-5.5 K-mayoría + contextual embeddings + seeds/config. Manifest estampado.

**Arms (flags branch-local, default OFF):**
- **A0 baseline** = prod actual (vector category-capado).
- **A1 L-i** = canal vectorial principal con `category=None` (stamps PRESERVADO — pure L-i, NO el cosine-merge de DEC-050).
- **A2 (c) within-doc vector** = etapa NUEVA: para docs PRESENTES en el pool, búsqueda vectorial scoped al source_file (pgvector filtrado), top-k al pool pre-rerank.
- **A3 L-i+(c)** = ambos.

**Métricas:**
- **PRIMARIA — retrieval-miss** (funnel + juez semántico, los 27 reales): ¿entra el chunk-respuesta al pool-50 / top-5? Conteo de reducción por arm.
- **REGRESIÓN — push-out** (los 39): facts hoy recuperados (artefactos + SINTESIS) que SALEN del pool por el cambio de mezcla. (El push-out que mató a L-i, pero medido en RETRIEVAL, no en juez.)
- **SECUNDARIA/guardarraíl — PASS** (bvg K=5): ¿regresa? ¿convierte algo?

**Regla de decisión:**
- retrieval-miss ↓ **∧** push-out ≈ 0 **∧** PASS no-regresa → **arreglar el bug** (= banco L-i o (c)).
- retrieval-miss ↓ **∧** PASS regresa → **el bloqueante es el MERGE** (DEC-041/056 confirmado) → el bug-fix de recall necesita el merge primero; (c) targeted < L-i global en push-out decide cuál.

## Alternativas / decisiones
- **¿Por qué no quitar el bug y ya?** Quitar el filtro = L-i = cambia el pool de TODOS los golds. No es borrado limpio; tiene consecuencia (pool-mix). El experimento mide esa consecuencia en retrieval-miss antes de shippear.
- **(c) vs L-i:** (c) targeted perturba solo docs relevantes → hipótesis: menos push-out que L-i global. Es lo NUEVO que DEC-040 no midió.
- **Categoría como filtro vuelve:** NUNCA (canon DEC-040a/068: si vuelve, BOOST data-driven, no filtro). Quitar el filtro NO reintroduce categoría — la elimina del path de retrieval (su detección queda para catálogo/boost futuro).

## Gaps/riesgos declarados
1. **Retrieval-miss ≠ PASS** (el riesgo central): es necesario, no suficiente. Apostamos upstream→downstream. Medimos PASS como guardarraíl para no shippear un win-intermedio que regrese PASS.
2. **#51 (auto-engaño):** estoy revirtiendo un settled mío → el cross-model es el control. Si dice "es re-litigación", paro.
3. **L-i sin merge-fix probablemente neteará 0 en PASS** (DEC-040) — el experimento lo CONFIRMARÁ o refutará en retrieval-miss; el valor es saber si (c) rompe el patrón.
4. **(c) hereda el merge:** los chunks (c) con coseno entran a un merge stamps → misma dinámica que perturbó a L-i. Posible que (c) también netee 0 en PASS.
5. **Coste:** A/B PASS ×4 arms = caro; mitigable midiendo retrieval-miss (judge-free-ish + 1 pasada de juez) primero, y PASS solo en los arms que reduzcan retrieval-miss sin push-out.
