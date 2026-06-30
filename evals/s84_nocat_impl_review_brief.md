# s84 — Revisión de IMPLEMENTACIÓN del fix del bug de categoría (VECTOR_NOCAT)

**Qué reviso (Protocolo 3, zona de dolor retrieval):** SOLO la IMPLEMENTACIÓN del cambio de código.
La DECISIÓN ("arreglar el bug del filtro de categoría muerto") YA está tomada por Alberto sobre datos
de RETRIEVAL (medido: RETRIEVAL-miss 27→13, −14 facts, **0 push-out** en los 39 golds; supera a la
alternativa (c) within-doc que fue revertida). **NO re-litigar "¿L-i?"** — eso es el stop-line de Alberto,
decidido con datos. El dúo audita que el CÓDIGO sea un fix limpio, completo y sin efectos colaterales.

## El bug (verificado)
`chunks_v2.category` está MUERTA desde el SWAP s44 (0 filas de la taxonomía canónica; DEC-040, re-verificado
s84). Bajo `MERGE_STRATEGY="stamps"` (prod default), retrieval filtra por `detected_category` en 3 sitios →
0 filas → canal capado en silencio para el ~85% de queries que detectan categoría.

## El cambio (flag `VECTOR_NOCAT`, default OFF; `git diff HEAD` adjunto)
Bypasea la categoría muerta en los 3 sitios cuando ON, MANTENIENDO stamps merge (aislado del cosine-merge
de L-i′/DEC-050):
1. **Canal vectorial principal** (retriever.py ~1108): `None if (_li_sano or _nocat) else detected_category`.
2. **Broad-fallback** (~1111): `and not _nocat` — redundante con el canal principal ya vivo; evita el ruido global no-model.
3. **content_search 3c-i** (~1224): `and not _nocat` — esas tasks filtran por la categoría muerta (no-model queries); skip (devolvían 0; el 3c-ii genérico se queda).

(c) (within-doc vector) REVERTIDO — redundante: L-i lo subsume (13 < 17 retrieval-miss; sus wins son subconjunto).

## Lo que el dúo DEBE auditar (implementación, no decisión)
1. **¿Completo?** ¿Hay OTRO sitio donde `detected_category`/`filter_category` capa el retrieval que no cubrí?
   (RPC `match_chunks`/`search_chunks_text`, `vector_search`, `content_search` Path A/B, `typed_search`, otros.)
2. **Side-effects / consumidores de `detected_category`:** la detección se sigue exportando para logging/catálogo/
   boost-futuro — ¿mi cambio la deja intacta donde NO es retrieval? ¿Rompe algún consumidor?
3. **Código muerto:** con el canal principal vivo, ¿el broad-fallback queda como código colgante que limpiar?
   ¿La rama `MERGE_STRATEGY=="stamps"` de 3c-i tiene sentido aún?
4. **Blast radius:** 353 tests verdes (flag OFF). Con ON, ¿algún gold que HOY pasa se ve afectado más allá del
   retrieval-miss medido? (el push-out de retrieval = 0 ya medido; ¿hay efecto en rerank/sintesis no medido?)
5. **¿Flag o default?** Alberto quiere el bug FUERA de prod. ¿Lo correcto es hacerlo DEFAULT (quitar el filtro de
   verdad) o dejar el flag y setear en Railway? ¿Riesgos de cada opción?
6. **Coherencia con DEC-040c (L-i):** L-i removió category de {vector principal + content_search + firma
   retrieve_chunks}. ¿Mi fix cubre el mismo scope o diverge (p.ej. dejé la firma `category_filter` y la detección)?

## Contexto (no re-litigar)
- DEC-040: L-i medido PASS-neutral (ROLLBACK por flips de juez 3-2 DOWNSTREAM, chunk seguía en pool). Eso NO
  es regresión de retrieval (0 push-out confirmado s84). Alberto: upstream→downstream — bancar el fix de
  retrieval, atacar síntesis después (los −14 facts ya están en top5 = SINTESIS 47→63).
- El caveat de PASS es CONOCIDO y aceptado por Alberto como decisión; el dúo NO lo re-abre.

## Gaps declarados
- El fix es flag-gated (default OFF) → para "eliminar el bug" en prod hay que hacerlo default o setear el env.
- La completitud en sitios no-retrieval (catálogo) no se tocó (fuera de scope: catálogo es otro tema, TECH_DEBT #44).
