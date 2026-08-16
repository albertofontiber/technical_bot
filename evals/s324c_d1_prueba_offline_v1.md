# s324c · D1 «COVERAGE_LIST_BLOCK_CLOSURE» — prueba offline $0 (medir antes de construir)

**Qué.** Encargo de la adenda r33 (16-ago): antes de tocar el seam, medir offline si el «cierre de bloque de lista» alcanza el bullet de `hp017#1` y cuántas filas/hechos tocaría. Script nuevo `scripts/s324c_d1_prueba_offline.py`; crudos en `evals/s324c_d1_prueba_offline_v1.json`. Coste: 0 llamadas de modelo, 0 escrituras, 43 s.

**Cómo (código real, no reimplementado).** Replay del FULL 16-ago (40 golds): pool y top-k grabados, hidratados por REST, y la etapa de coverage REAL importada (`apply_profiled_post_rerank_coverage`, `DEMO_FLAGS` por AST — patrón `s293_lane_replay.py`). Fidelidad **40/40 golds** (`appended_ids`+lanes en orden; 48 filas: 27 estructurales, 18 reserva-warning, 3 document-local). Vista de hoy = `coverage_context_content(fila)` real (cards + callout-MANDATORY en 5 filas); reconstrucción por offsets byte-idéntica 48/48. Solo el cierre es simulado (no existe en `src/`): regex del diseño, ≥2 ítems, intro opcional que termina en «:», cap 1800, sobre `served_coverage_cards` (tras la expansión de tabla, como D1). **A** = la línea en blanco entre ítems NO rompe el bloque (la del diseño); **B** = la línea en blanco ROMPE (objeción de Fable); **B1** = B con ≥1 ítem.

## 1 · hp017#1 (carrier `d27b1a1b`, PEARL Config p41 idx73, 2.864 chars)

Cards reales HOY: `[675:1032]` navigation, `[419:673]` logic_structure, `[1694:2052]` output_timing (+ callout `[2479:2724]`); vista 1.316 chars. El bullet «* Instrucción de entrada: …» ocupa **`[1425:1692]`** (267 chars; la propuesta escribió [1427:1690]) y queda **fuera de todas las cards**. En el fuente los dos bullets van separados por línea en blanco (intro `[1343:1423]` «…como se explica a continuación:» · blanco · bullet entrada · blanco · bullet salida `[1694:2107]`).

| definición | dispara | span cerrado | ¿alcanza el bullet? | +chars (ajenos) |
|---|---|---|---|---|
| A (blancos permitidos, ≥2) | sí, card `[1694:2052]` | `[1343:2107]` (764) | **SÍ** — literal en la vista | +406 (139: intro 82 · blanco 2 · cola 55) |
| B (blanco rompe, ≥2) | no (0 bloques) | — | **NO** | 0 |
| B1 (blanco rompe, ≥1) | sí | `[1694:2107]` | **NO** | +55 (55) |

## 2 · Censo: 48 filas servidas, 3 lanes, 40 golds

| def. | filas que disparan | golds | NO-OK con la fila en su soporte | NO-OK del mismo gold | beneficio literal | hechos OK cuya fila cambia | +chars/fila |
|---|---|---|---|---|---|---|---|
| A | 6 (todas estructurales; 0 reserva, 0 doc-local) | cat008, cat019, cat022, hp003, hp012, hp017 | **1**: hp017#1 | +cat008#3, hp003#4, hp017#2 (sin literal) | **1**: hp017#1 | 9 | 21–415 |
| B | 2 | cat008, hp003 | 0 | cat008#3, hp003#4 | 0 | 1 | 84, 264 |
| B1 | 3 | cat008, hp003, hp017 | 1 (hp017#1, sin literal) | ídem A | 0 | 3 | 55–264 |

Ninguna fila toca el cap 1800. Los 6 disparos de A son los mismos golds que censó la propuesta; su «30 filas estructurales» leía el mapa `appended_lane` (3 ids seleccionados pero NO apendizados: cat008 `14a370f1`, hp002 `41bcd390`, hp003 `fde65f3d`) — servidas hay 27. cat019 arrastra la expansión de fila de tabla ya presente en `served_coverage_cards` (+168 de sus +415).

## 3 · Lo que NO pude medir

Si el generador transmite hp017#1 con el bloque cerrado en posición de lane (G2/G3, exige LLM); tráfico real; ítems con continuación sin marcador, sublistas u OCR (mi parser no los modela — punto 3 de Sol); efecto en `must_preserve`/`answer_planner` al cambiar `served_coverage_cards` (Sol #2).

## 4 · Veredicto

1. D1 **sí alcanza su único hecho** (`hp017#1`) offline, **solo con la definición A** (la línea en blanco NO rompe el bloque): +406 chars, 139 ajenos.
2. Con B (blanco rompe) o B1 **no lo alcanza**: Fable tenía razón; A queda pineada como test si alguna vez se construye.
3. Hechos NO-OK adicionales con beneficio literal: **0** (strict 0; loose 3 sin literal). Cambia la vista de filas que soportan **9 hechos OK** (superficie de regresión) para pagar 1.
4. Recomendación: **no construir ahora** — el beneficio existe pero es 1 hecho; solo un GO de Alberto sobre «1» justificaría el seam, con G2 (oráculo del bloque en posición de lane) antes de G3.
5. Cifra para el banner DEC-175: 1 hecho pagable por serving; radio del defecto 6/27 filas estructurales (no 6/30).
