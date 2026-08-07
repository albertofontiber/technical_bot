# s307 — Propuesta a atacar: intro real + inventario por fabricante (commit ffff3d4)

Rama `claude/s307-intro-fabricantes`. Impacto MEDIO: enrutado del bot junto al lever
medido DEC-059. Corre `git show ffff3d4` para el delta.

## OBJETIVO + MÉTRICA (declarados)

Dos fallos orgánicos de la misma enfermedad — el bot habla de su corpus DE MEMORIA:
(1) la intro decía «Notifier, Morley y Detnov» con 30 fabricantes reales (pantallazo de
Alberto); (2) «¿qué productos de Securiton tienes?» cayó a RAG por rigidez de
`_CATALOG_PATTERNS` y la ventana de 10 chunks se presentó como inventario — faltaron
ASD531 y ASD535 (242 chunks, el doc más grande de la marca; 👎 orgánico con motivo).
**Métrica**: NO toca ningún lever de eval. El camino RAG queda BYTE-IDÉNTICO salvo
(a) textos de intro/help/greeting/productos y (b) la rama fabricante-SIN-modelo cuando
además hay intención de inventario. **Si toca DEC-059**: aquel fall-through se midió
(s77, judge-free) para preguntas DE MODELO con el índice como oráculo poco fiable; el
inventario es una población DISTINTA que s77 no midió — la rama modelo+fabricante NO
cambia (anclado por test de inspección de fuente).

## Qué se construyó

1. `src/rag/retriever.py` — `get_manufacturers_by_docs()` (marcas por nº de docs
   activos, para la intro) y `get_products_by_manufacturer()` (inventario = chunks
   CURADOS × docs ACTIVOS; paginación con `order=id.asc`, lección s304 anclada como
   test; `unknown` excluido).
2. `src/bot/telegram_bot.py` — `_fabricantes_resumen()` cacheado por proceso con
   fallback estático (4 sitios: welcome, /help, greeting, /productos; warm-up en
   `main()` antes del polling); `_ENUM_FABRICANTE` (intención estrecha:
   interrogativo+sustantivo+verbo-de-posesión, o palabra-de-lista) que solo actúa en
   la rama fabricante-sin-modelo; `_inventario_fabricante()` con fail-open a RAG y
   éxito cacheado; `route="catalog_shortcut"` (valor EXISTENTE del CHECK s301 — sin
   migración). **`_CONSENT_TERMS` NO tocado** (TERMS v7 = lo aceptado; su línea de
   marcas viaja en el bump a v8) con test que lo pinna.
3. TECH_DEBT #65 — `documents.product_model` STALE post-H0 (probado: `MADT235` dice
   `AFP4000` allí y `ART1194` en chunks curados) ⇒ el inventario NO lee identidad de
   `documents`. #66 — observación punto 5: la prosa del 👎 llegó como consulta nueva
   (`comment=NULL`; `reason_class` sí capturado).
4. Tests 7+12: consulta orgánica LITERAL casa; averías/recomendaciones NO casan;
   fail-open no cacheado; DEC-059 intacto; efecto verificado contra la base viva
   (8 modelos, incluidos los 2 que el RAG se dejó).

## Claims a atacar

- C1: RAG byte-idéntico fuera de (a)+(b); rama modelo+fabricante intacta (DEC-059).
- C2: la intención es lo bastante ESTRECHA — ninguna avería/recomendación razonable se
  desvía al listado. Atácala con casos concretos: es donde un falso positivo hace daño
  (técnico con avería recibiendo un listado).
- C3: inventario completo y honesto (curado × activo; unknown fuera; granularidad
  familia declarada); la fuente NO es documents.product_model (#65).
- C4: fail-open total (excepción → RAG; fallo no cacheado; éxito sí).
- C5: `catalog_shortcut` existe en el CHECK s301 → sin carrera de deploy; el aviso v7
  no promete nada sobre estas consultas (no son cortesía).
- C6: textos dinámicos degradan a fallback si la base no responde; warm-up pre-polling.
- C7: `_CONSENT_TERMS` byte-idéntico, test lo pinna.

## Preguntas duras

- La alternativa `\b(listado|lista|catálogo|gama|inventario)\b` NO exige fabricante en
  la frase (el gate real es la rama fabricante-sin-modelo): ¿dispara en técnicas
  legítimas? («la lista de zonas de mi central notifier», «el catálogo de eventos»…)
- ¿`_MANUFACTURER_NAMES` + `ilike.<match>` casan con los nombres REALES de la DB?
  (`lda` vs `LDA audioTech`, `argus` vs `Argus Security`, `system sensor` con espacio)
  Si el ilike sin comodines no encuentra → ¿inventario vacío → None → RAG (benigno) o
  algo peor?
- ¿El warm-up puede retrasar el arranque con la DB caída? ¿`_fabricantes_resumen()` en
  el greeting bloquea el event loop?
- Marcas grandes (Notifier ~11k chunks → 3 páginas): ¿latencia del primer inventario?
  ¿La tabla legacy `chunks` (CHUNKS_TABLE) rompe algo?
- ¿Algún test/harness existente asserta los textos viejos?
