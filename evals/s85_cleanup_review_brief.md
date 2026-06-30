# s85 — Revisión del DÚO de la limpieza de raíz del filtro de categoría muerta (DEC-071)

**Qué reviso (Protocolo 3, zona de dolor retrieval → cross-model INNEGOCIABLE):** SOLO la
IMPLEMENTACIÓN de la limpieza. La DECISIÓN ("quitar de raíz el filtro de la columna `category`
MUERTA, sin flag, permanente") YA está tomada por Alberto (DEC-071, medido en retrieval: −12).
**NO re-litigar "¿quitar el filtro?"** — es el stop-line de Alberto. El dúo audita que el CÓDIGO
sea un refactor limpio, completo, sin cambiar comportamiento ni romper consumidores.

## Contexto (no re-litigar)
- `chunks_v2.category` MUERTA desde el SWAP s44 (0 filas canónicas, DEC-040). El filtro devolvía
  0 filas en ~85% de queries → mataba el canal semántico. s84 lo midió como flag `VECTOR_NOCAT`
  (default OFF): retrieval-miss 27→15 (net −12). s85 = hacerlo PERMANENTE (sin flag) + limpieza.
- El modelo operativo s84: main=dev=demo, stop-line=tests-verdes, PASS diferido a síntesis. Aquí
  NO se mide PASS; el objetivo es que el refactor PRESERVE el comportamiento medido (−12), no mejorarlo.

## Qué cambié (diff adjunto, `evals/_s85_cleanup.diff`, 333 líneas)
El path de retrieval ya no filtra por la columna muerta. Hecho permanente (se quitó el flag):
1. **Canal vectorial principal** (`retrieve_chunks`): siempre `category=None`; se eliminó el
   `ThreadPoolExecutor` de 1 sola tarea → llamada directa `vector_search(...)`.
2. **Broad-fallback ELIMINADO** (era el workaround del canal muerto, DEC-040) → con él muere el
   flag `LEVER1_BROAD_FALLBACK`.
3. **3c-i ELIMINADO** (content_search no-model filtraba por la categoría muerta → 0 filas siempre);
   sobrevive 3c-ii genérico (sin categoría).
4. **Diversify 5b**: `category = None` permanente (se quitó el read de `chunks[0].category` muerta
   y el `_nocat`); `if (category or _nocat) and underrepresented` → `if underrepresented`.
5. **`content_search`**: quitado el param `category` (dead — ningún caller lo pasa tras quitar 3c-i)
   + el `filter_category` del RPC Path B pasa `None`.
- **CONSERVADO** (verificar que NO los toqué): la DETECCIÓN de categoría (catálogo/boost),
  `MERGE_STRATEGY` (lever de merge), `LEVER2_IDENTITY`, `LEVER1_KEYWORD_ORDER`, `LEVER2_PM_RESCUE`.
- **Firmas RPC de bajo nivel** (`vector_search.category_filter`, `_vector_search_by_manufacturer.category`)
  se conservan exponiendo el param del RPC, pero el path les pasa `None` (filtro desactivado). Decisión
  declarada: no migración/DDL en Supabase.

## Verificación YA hecha (verifícala, regla C — no la asumas)
- **354 tests verdes** (3 tests que codificaban el comportamiento viejo flag-gated → reescritos al
  invariante nuevo: categoría nunca llega al canal; 1 sola llamada vectorial; sin broad-5).
- **PRUEBA DE EQUIVALENCIA judge-free** (`scripts` en scratchpad): pools de retrieval (pre-rerank)
  por los 39 dev golds, NEW (sin flag) vs OLD (`origin/main` con `VECTOR_NOCAT=on`), embeddings
  pineados (mismo cache). Resultado: **38/39 pools EXACTAMENTE idénticos (orden+set)**. El único que
  divergió en batch (cat005, +12/−12) se probó **idéntico NEW==OLD en isolación controlada** (ambos
  estables 3×) → la divergencia de batch = nondeterminismo ambiental del diversify bajo carga
  (propiedad pre-existente de OLD, no del refactor). ⟹ retrieval-miss=15 preservado por construcción.

## Lo que el dúo DEBE atacar (bite concreto anclado en evidencia)
1. **¿Completo?** ¿Hay OTRO sitio donde `detected_category`/`filter_category`/`category` capa el
   retrieval que no cubrí? (RPC `match_chunks`/`search_chunks_text`, `vector_search`, `content_search`
   Path A/B, `typed_search`, `diagram_search`, `get_category_models`, otros.)
2. **¿Rompí un consumidor?** ¿Algún código aún lee el param/variable `category` que quité y ahora
   recibe algo distinto o peta? ¿La detección queda intacta donde NO es retrieval (catálogo)?
3. **¿Toqué el lever de merge sin querer?** `MERGE_STRATEGY` / la rama `_li_sano` (cosine) — ¿el
   refactor preserva el merge bajo cosine/quota, o lo degradé al colapsar el path de categoría?
4. **¿Dead code residual?** Tras quitar el broad-fallback/3c-i, ¿quedan variables/imports/ramas
   muertas? (`extract_search_keywords` en el bloque no-model, `effective_top_k`, etc.)
5. **¿La prueba de equivalencia es sólida?** ¿El argumento "cat005 = nondeterminismo ambiental" se
   sostiene, o esconde una diferencia real? ¿La métrica correcta era pool pre-rerank?
6. **Tests reescritos:** ¿los 3 tests nuevos asveran el invariante correcto, o aflojé un assert para
   que pasara (over-fit del test al código)?

## Gaps declarados
- PASS no medido (decisión de Alberto: diferido a síntesis). El dúo NO exige PASS — su métrica aquí
  es retrieval-miss/equivalencia/limpieza, NO PASS (no matar el refactor por "no sube PASS").
- Firmas RPC de bajo nivel conservadas con `None` (no DDL) = residual declarado, no bug.
