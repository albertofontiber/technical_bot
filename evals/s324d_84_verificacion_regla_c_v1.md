# s324d — Verificación (regla C) del análisis de #84: dos hallazgos confirmados con mis propios ojos

El agente de análisis produjo `evals/s324d_84_doc_map_aplicabilidad_propuesta_v1.md`. Sus dos claims fuertes se
verifican aquí **de primera mano**, porque uno de ellos invalida una medición que ya está escrita en la deuda y en
DEC-226, y el otro toca serving vivo. Lo que sigue lo comprobé yo, no el agente.

## 1 · `_product_aligned_chunks` NO se ejecuta en producción ⇒ el «#84 medido» de s321 es un NO-DATO

Cadena verificada paso a paso (17-ago):

| paso | evidencia |
|---|---|
| El modo por defecto es `off` cuando la variable no existe | `src/rag/answer_planner.py:224` — `os.getenv("ANSWER_OBLIGATION_PLANNER", "off")` |
| En Railway (worker) **la variable NO está** | censo GraphQL propio, `scripts/s322_railway_censo.py` → recibo `evals/s322_railway_censo_v1.json`: worker con **40 vars**, `ANSWER_OBLIGATION_PLANNER` ausente (sí están `OBLIGATION_RESERVE_ORDERED` y `OBLIGATION_WARNING_APPENDIX`, que son otros). Método correcto por memoria del proyecto: **un flag de producción se lee de Railway, nunca se infiere de la ausencia de una clave en trazas** |
| Con `off`, el generador no construye plan ni conflictos | `src/rag/generator.py:848-870` — `guided_plan` sólo si `planner_mode == "guided"`; `enforced_plan`/`enforced_conflicts` sólo si `"enforced"` |
| **Todas** las rutas a `_product_aligned_chunks` cuelgan de ahí | `answer_planner.py`: llamadas en 1404, 1496 (dentro de `build_answer_plan`, 1387) y 1566 (dentro de `build_answer_conflicts`, 1546); las otras dos (620, 1327) están en `_base_relation_obligations` y `_served_structured_obligations`, invocadas sólo desde 1531 y 1480 — **también dentro de `build_answer_plan`** |

⇒ **En producción esa función no corre.** Y el FULL del 16-ago tampoco llevaba el flag ⇒ la línea que hoy consta
en `TECH_DEBT #84` y en el PLAN («#84 medido — 0 misses atribuibles») **no midió el camino que #84 señala**: es la
misma clase de fallo que DEC-186/s305 (el «techo del modelo» que nunca leyó al juez). No es una absolución de #84:
es que no se ha medido.

**Consecuencia de método (para Alberto):** despriorizamos una deuda con un no-dato. El instrumento tampoco puede
medir hoy ese lever: con el flag ausente los dos brazos de `factlevel_assessment.py` son el mismo pipeline (delta ≡ 0
por construcción); medirlo exige pinear `guided` en ambos brazos, y entonces se mide **un pipeline que no está en
producción**.

## 2 · El join `doc_map` ↔ `chunks_v2.source_file` es EXACTO y pierde el 10 % del catálogo gobernado

Medido por mí sobre los datos vivos:

- `doc_map.jsonl`: **977** filas · `chunks_v2`: **1.088** `source_file` distintos.
- Casan exacto **876**; **98 casan sólo tras normalizar** (`.pdf` final y/o mayúsculas); 3 no casan de ninguna forma.
- Ejemplos: `DS_KIDDE_2X_AT_FR_S_904a.pdf`, `Averia-de-resistencia-de-baterias-en-central-DXc.pdf`,
  `997-671-007-3_configuration_pt`.

Y el join **es exacto en código VIVO** (no en el planner apagado):
- `src/rag/retriever.py:2351` y `:2363` — `[c for c in chunks if (c.get("source_file") or "") in identity_allowed]`
  y `... in allowed`, contra los `allowed_sources` que salen del doc_map.
- `src/rag/catalog_resolver.py:782` — `missing = [s for s in allowed_sources if s not in in_pool_srcs]`.

Efecto doble para esos 98 documentos: (a) su atestación no filtra/prioriza nada (el chunk nunca «pertenece» al doc
gobernado), y (b) se consideran SIEMPRE ausentes del pool, así que disparan el fetch de identidad / `deep_lookup`
aunque ya estén servidos.

**Impacto medido sobre los golds, sin adornos:** de los 1.194 chunks del pool de los 40 golds del FULL, **12
pertenecen a documentos con el join roto** (11 documentos: fichas DS_KIDDE, FAQs DXc, `MADT236`,
`997-671-007-3_Configuration_PT`). Es **el 1 %**. ⇒ **Arreglarlo NO va a mover el número de OKs**; es higiene
estructural (y evita trabajo inútil de fetch), no un lever de calidad. Lo digo aquí para que nadie lo venda como
otra cosa.

## Qué hago con esto

1. **No cablear el cambio de fuente de aplicabilidad** (opción A/B/C del análisis): el lever no es medible hoy con
   el instrumento tal cual, y su punto de consumo está apagado en producción. Coincide con la recomendación del
   agente.
2. **Sí arreglar el join** (defecto de raíz, barato, riesgo acotado): normalizar la clave en UN punto —donde el
   resolver construye `allowed_sources`— comparando por clave normalizada, con guarda de colisión (dos documentos
   distintos que normalicen igual). Es retrieval ⇒ **zona de dolor ⇒ dúo obligatorio antes de cablear** (Protocolo 3)
   y medición de delta con smoke antes del full.
3. **Corregir la deuda #84 y el PLAN** para que no sigan diciendo «medido»: lo que hay es un no-dato.
