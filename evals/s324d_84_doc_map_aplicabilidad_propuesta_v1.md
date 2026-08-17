# s324d — TECH_DEBT #84: ¿debe el `doc_map` contestar la aplicabilidad? (análisis + diseño, v1)

Análisis y diseño. **NADA cableado**; `src/`/`scripts/` intactos; ninguna escritura en Supabase.
Cifras de lectura ejecutada hoy (17-ago), con fuente declarada. Coste LLM: $0.

## 0. Hallazgo que cambia el marco (verificado, no inferido)

**El consumidor de `_product_aligned_chunks` está APAGADO en producción.** Solo es alcanzable desde
`build_answer_plan`/`build_answer_conflicts` (`answer_planner.py:620,1327,1404,1496,1566`), que el
generador invoca únicamente con `ANSWER_OBLIGATION_PLANNER ∈ {guided, enforced}`
(`generator.py:849-871`); en `off` `apply_answer_planner` retorna antes del plan
(`answer_planner.py:3220-3221`), y el default es `"off"` (`:224`; `src/flags.py:29-33`).
**Censo Railway SOLO-LECTURA de hoy** (GraphQL, patrón
`scripts/s322_railway_censo.py`; worker, 40 vars): **`ANSWER_OBLIGATION_PLANNER` AUSENTE** ⇒ `off`.
(Vivos: `IDENTITY_RESOLVE=on`/`replace`, `CHUNKS_TABLE=chunks_v2`, `coverage_c1_v4`; ausentes:
`IDENTITY_MAP`, `IDENTITY_FETCH`, `LEVER2_PM_RESCUE`, `NEIGHBOR_MODELS_ONLY`.)

Dos consecuencias materiales:

1. La premisa de #84 «de ahí salen las obligaciones estructuradas» es **cierta como código y falsa
   como efecto**: hoy no sale ninguna.
2. **El cruce del FULL 16-ago que despriorizó #84 no podía medir #84**: `DEMO_FLAGS`
   (`factlevel_assessment.py:62-129`) no incluye ese flag, `.env` tampoco, y el `flags_demo` del
   manifest lo confirma ⇒ corrió con el planificador `off` y la función **nunca se ejecutó**. «Coste
   medido = 0 misses» es un **no-dato**, no una absolución.

## 1. Mapa del consumo de `product_model` en el camino SERVIDO

| Punto (ancla) | Tipo | Vivo |
|---|---|---|
| `retriever.py:2306-2425` `_filter_to_query_models` ← `:2071-2073` (nivel-1 substring + nivel-2 series, fail-open escalonado) | **(a) filtro duro** del pool | **SÍ** |
| `retriever.py:2347-2352` unión protectora `identity_allowed` = `allowed_sources` del doc_map | (a) **aditiva**, no sustituye | SÍ |
| `retriever.py:2863-2879` `_source_allowed` (pm dominante por source, `:2559-2590`) | (a) filtro de universo | SÍ (con serie) |
| `retriever.py:2749-2765` vecindad · `:2395-2410` rescate pm · `:2360-2366` IDENTITY_MAP | (a) | NO (flags ausentes) |
| `answer_planner.py:442-504` `_product_aligned_chunks`, 5 vías (exact · declarado-inequívoco · sufijo numérico · familia-slash · identidad atestada S141) | **(c) elegibilidad de obligación** | **NO** |
| `pool_selection.py:163-180` `_in_canonical_scope` (pm = fail-open del doc_map) → `rerank_pool_coverage.py:90,134` | (c) lane | NO (off) |
| `procedure_bundle_coverage.py:113-124` `_product_compatible` (fail-closed pm+fabricante) | (c) lane | NO (off) |
| `post_rerank_coverage.py:170-183` pm en la identidad del source-contract · `:1709-1711` `governed_catalog_scope_owners()` (`raise` si hay scope huérfano) | (c) lane — **ya doc_map** | SÍ |
| `document_local_coverage.py:417-423,569-573` pm fuera de las anclas | (c) anti-ruido | SÍ |
| `reranker.py:73,216` · `generator.py:779` (`Producto: …` en el prompt) | **(b) score blando** | **SÍ** |
| `logging_db.py:136,168` · `factlevel_assessment.py:39-41,623,716` (family-aware) | (d) telemetría / **instrumento** | SÍ |

**Lectura**: lo único VIVO y decisorio por columna es el **filtro de retrieval** y el **canal blando
del prompt**; el punto que #84 nombra está muerto; y el doc_map **ya gobierna** la capa de cobertura.

## 2. Qué devolvería `doc_map` (medido sobre datos reales)

Predicado doc_map = `(document_id, source_file)` es scope `role=primary, scope=doc` de un pid que
`resolve_query(pregunta)` resuelve con `expand=True` (`catalog_resolver.py:186-190,588-641,643-652`);
predicado de hoy = la **función real**. Población = **vista SERVIDA real** de los 40 golds del FULL
`evals/s100_factlevel_full_v3_20260816.yaml` (432 filas rehidratadas de `chunks_v2`, 1000+offset).

| | alineado hoy | doc_map | gana | pierde |
|---|---|---|---|---|
| vista SERVIDA (432 filas) | 315 | 318 | **+44** | **−41** |
| pool-50 (1.316 filas)¹ | 828 | 831 | +123 | −120 |

¹ mismo predicado a profundidad de pool; **no** simula el fail-open del filtro de retrieval.

Neto ≈ 0, **churn enorme y concentrado**. Cuatro patrones:

- **Gana donde #84 predijo**: `cat008` 0→9 (pm `M700`), `hp006` +3 (los `pm=AFP-300` del `50253SP`, el
  caso DEC-223), `hp021` +1 (`pm=CAD-250`), `hp012` +2, `cat007` +1.
- **Gana donde no lo predijo**: `hp011` 0→14 (`pm=RP1r-Supra` vs query `RP1r`), `cat017` 0→12
  (`pm=INSPIRE E10/E15`) — paraguas que la columna no resuelve y el catálogo sí.
- **Pierde por hueco del CATÁLOGO, no del doc_map** (31/41): `cat009` −10, `hp007` −11, `cat022` −8,
  `cat024` −2. `resolve_query` da **0 pids** (`resolve('NFS-Supra'|'40-40'|'MAD-472'|'VESDA-E-VEP')
  → None`) aunque el documento **sí** esté gobernado (`HLSI-MN-025_NFS Supra` →
  `morley:nfs4/8/12-supra`; `33977_13_VESDA-E_VEP-A10-P…` → `xtralis:vep-a10-p`).
- **Pierde por desacuerdo REAL** (8/41, 2 golds): `hp020` −7 (`4188-1122-ES issue 4_04-2025_Cyb`,
  `pm=INSPIRE`, primary de `notifier:hop-131-206…`) y `cat012` −1 (`HONEYWELL-H-GTW…`, primary de
  `unresolved:h-gtw-*`): ahí el doc_map es probablemente **más correcto** — precisión, no regresión —
  pero sin adjudicar.

Variante descartada con dato: resolver query→pid por normkey del pid (método del censo s321) da
**+15 / −139**, 3,4× peor. La puerta del catálogo es imprescindible.

## 3. Riesgo de la sustitución (censo completo de `chunks_v2`, 17-ago)

`chunks_v2`: **26.216 chunks / 1.080 documentos**. `doc_map`: 977 filas, 2.063 `primary` + 842
`secondary`, todas `scope=doc`.

| Riesgo | Cifra |
|---|---|
| Docs SIN scope `primary/doc` ⇒ **sin aplicabilidad** bajo sustitución pura | **118 docs / 1.765 chunks (6,7 %)** |
| **BUG DE CLAVE**: docs con entrada por `document_id` cuya tupla `(document_id, source_file)` NO casa (doc_map guarda `….pdf` o minúsculas) ⇒ invisibles para `governed_catalog_scope_owners` y `allowed_sources` | **100 docs / 949 chunks** |
| Golds del FULL que PIERDEN / GANAN bajo sustitución pura | 8/40 (**todos con OK hoy**; 23 OK expuestos) / 8 de 40 (44 chunks) |

El bug de clave **ya afecta a código VIVO** (unión protectora + lane document-local): normalizando el
`source_file`, las pérdidas servidas bajan de 41 a 39 y se recuperan 949 chunks de gobierno
corpus-wide. Es el arreglo más barato y rentable del análisis.

## 4. Opciones (aritmética medida sobre la vista servida)

| Opción | Definición | +/− | golds que pierden |
|---|---|---|---|
| **A** sustituir | doc_map(primary) ∩ pids resueltos | +44 / **−41** | 8 (23 OK expuestos) |
| **B** unión | doc_map ∪ columna | **+44 / −0** | 0 |
| **C** fallback por DOC | columna si el doc no tiene scope gobernado | +44 / −31 | 5 |
| **C′** fallback por QUERY | columna si la query no resuelve ningún pid | +44 / −10 | 4 |
| **C″** ambos | C + C′ | +44 / **−8** | 2 (`hp020`, `cat012`) |

**C tal como se planteó en el encargo NO evita las regresiones grandes**: `cat009`/`hp007`/`cat024`
tienen doc gobernado y fallan por el lado de la QUERY. El fallback correcto es query-side.

**Flag** (patrón del repo: `os.getenv` con default inerte + fila en `src/flags.py:REGISTRO` + pin en
`DEMO_FLAGS`): `PRODUCT_APPLICABILITY = column` (default = hoy) `| docmap | union | docmap_fallback`,
vía un único helper consumido por los 5 call-sites.

**Medición del delta**: `scripts/factlevel_assessment.py smoke` (siempre antes del `full`) **no puede
medirlo con el flag-set de la demo**: sin `ANSWER_OBLIGATION_PLANNER` los dos brazos son el MISMO
pipeline (delta ≡ 0 por construcción). Exige pinearlo a `guided` en ambos brazos ⇒ **freeze-hash y
baseline distintos de los shippeados**: se mediría un pipeline que hoy no está en producción.

## 5. Recomendación

**No cablear todavía el cambio de fuente.** En este orden:

1. **Arreglar el join `doc_map`↔`chunks_v2`** (normalizar `source_file` o joinear solo por
   `document_id`): toca código VIVO, recupera **949 chunks / 100 docs** de gobierno, independiente de
   #84. MEDIO en zona de dolor ⇒ dúo + gate.
2. **Cerrar los huecos de query del catálogo** (`NFS-Supra`, `40-40/40-40L`, `MAD-472`,
   `VESDA-E-VEP`): datos/packet, flujo que ya existe. Elimina el **76 %** del riesgo de #84.
3. **Adjudicar los 2 desacuerdos reales** (`hp020`, `cat012`): catálogo, para Alberto.
4. Solo si/cuando se shippee el planificador: **opción B (unión)** tras el flag, con telemetría en
   sombra de la divergencia A-vs-B.

**Por qué B**: A es la más «pura» pero la única con pérdidas medidas (−41; 8 golds OK expuestos) y
**cero evidencia** de que sean correcciones; B es **monótona** (nunca quita material ya alineado),
captura el 100 % de la ganancia (+44) y deja la precisión a medición, no a teoría. **Descartadas**: A
(regresión no acotada), C (no ataca la causa dominante), C′/C″ (mejores que A, pero codifican dos
fail-opens acoplados a huecos de datos que el paso 2 elimina).

**BP + estructural + escalable a 30+ fabricantes**: la aplicabilidad pasa a la **capa gobernada N:M**
(DEC-043/044), no a un `varchar` por chunk; un fabricante nuevo entra declarando `doc_map`, sin
re-taguear columnas — y el paso 1 arregla la **clave** de ese gobierno, que es lo que lo hace escalar.

**Gaps/riesgos declarados**: (i) 40 golds dev, held-out intacto; (ii) alineado ≠ respuesta (solo
*habilita* obligación); (iii) el pool-50 se midió con el predicado del planificador, no con el filtro
real de retrieval; (iv) `product_model` es campo de identidad congelado del contrato document-local
(`post_rerank_coverage.py:170-183`) ⇒ «limpiar la columna» tiene coste propio; (v) corpus vivo
(26.215→26.216 hoy).

## 6. Lo que NO se puede decidir sin medir

- **Si los 8 chunks del desacuerdo real son ruido o señal**: adjudicación humana del catálogo, no eval.
- **Si el churn mueve algún hecho**: imposible sin eval con el planificador encendido — y ese eval
  mide un pipeline que hoy no está en producción.
- **Si conviene encender el planificador**: es la pregunta previa. Sin ella #84 es deuda de un camino
  muerto, y lo urgente es el paso 1 (el join), que sí está vivo.
