# s287 P2 — PACKET DE ADJUDICACIÓN: near-duplicados a nivel DOCUMENTO

Generado read-only por `scripts/s287_p2_dedup_census.py` · 2026-07-30T09:48:09 · git `a2fbad2` · rama `claude/s282-h0t2-qa`. **Cero escrituras a DB.**

> ⚠ **EDITADO A MANO tras la adjudicación de Alberto (s287): par semilla → OPCIÓN B, y después la adjudicación FINAL de §8 + BLOQUE S.** Este `.md` y los `.sql` ya **no** son salida limpia del generador. `scripts/s287_p2_dedup_census.py` escribe los tres artefactos (`OUT_JSON`/`OUT_MD`/`OUT_SQL`, líneas 101-104) → **re-correr el census SOBRESCRIBE la adjudicación** (el `v2.sql` NO lo sobrescribe: no es un OUT del generador). Si hay que regenerar, salva antes estos ficheros (el `.json` del census sí es reproducible).
Spec: `evals/s287_etapa2_design_brief_v1.md` (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF de Sol-6). Datos: `evals/s287_p2_dedup_census_v1.json`.
Pastes: `evals/s287_p2_dedup_apply_v1.sql` (**APLICADO** — 12 marcas + metadata-fix) · `evals/s287_p2_dedup_apply_v2.sql` (**remate, PENDIENTE de paste** — par 4 + retiro par 19 + BLOQUE S variante A).

---

## 0. ESTADO: ADJUDICACIÓN COMPLETA DE ALBERTO (s287) — los 24 pares · **WORKSTREAM CERRADO**

> Alberto adjudicó **los 24 pares** y después **las 7 preguntas de §8 y el BLOQUE S**. No queda
> ningún par abierto. Todo lo de esta sección es **veredicto suyo**; lo que añado yo (verificación
> en la fuente, causa del falso positivo, propuesta) va marcado como tal.
>
> **ESTADO DE APLICACIÓN (2026-07-30):**
> - **`v1.sql` APLICADO por Alberto** y **verificado en vivo read-only**: 12/12 chunks con
>   `duplicate_of` correcto · md5 sin deriva · canónicos válidos · metadata-fix del par semilla
>   completo (los 2 `documents` + 18 chunks de B + 15 de A en `European Safety Systems`/`IS-mA1`) ·
>   `VIA-28V` corpus-wide = **0** · backups `_s287_metafix_backup_documents` (2),
>   `_s287_metafix_backup_chunks` (18), `_s287_dedup_backup` (12), `_s287_dedup_staging` (12).
>   **0 discrepancias.**
> - **`v2.sql` escrito, PENDIENTE de paste** (3 transacciones separadas): par 4 · retiro del ES/PT
>   del par 19 · BLOQUE S variante A. Sus guards están **pre-validados en vivo read-only**.

| # | par | VEREDICTO (Alberto) | estado en el `.sql` |
|---|---|---|---|
| 1 | `2b694083__a6b9dc84` | **APROBADO** (semilla, opción B) | **VIVO** · 10 marcas + bloque 0 metadata-fix |
| 2 | `5e878ee7__eb749df8` | **APROBADO** — «OK» | **VIVO** · 1 marca |
| 3 | `517b87ce__de8c0345` | **RECHAZADO** (final) — rebadge OEM FS/MS | fuera de los pastes · §8.1 |
| 4 | `7f9ea4ab__acafc5d1` | **APROBADO** (final) — ganancia marginal aceptada | **v2.sql BLOQUE 1** · 5 marcas · §8.2 |
| 5 | `5800c4c0__cbc9c21c` | **ESPERAR** (final) — antes, el seam de identidad D1/D3 | fuera de los pastes · §8.3 |
| 6 | `2c299ef1__89024b18` | **RECHAZADO** (final) — BRS ≠ BRH | fuera de los pastes · §8.4 |
| 7 | `2e0ee11a__b788bbda` | **RECHAZADO** — productos distintos (SG100-IS vs SG100) | fuera del `.sql` · §6 |
| 8 | `1c6eff80__6d84be7f` | **KEEP-BOTH** — doc_type distinto (usuario vs funcionamiento) | fuera del `.sql` · §9 |
| 9 | `681e506b__a7bf5098` | **SUPERSEDED** — `Tg-Honeywell_Introduccion` supersede a `MI-DT-951_V7.2` | **v2.sql BLOQUE 3** · variante **A** · §7 |
| 10 | `f8020fa4__fc285f22` | **RECHAZADO** — SG200-IS vs SG200 | fuera del `.sql` · §6 |
| 11 | `29c145dc__c270c9c7` | **RECHAZADO** — SG350-IS vs SG350 | fuera del `.sql` · §6 |
| 12 | `65246432__a6d93291` | **RECHAZADO** — NRX-OPT vs NRX Radio Thermals | fuera del `.sql` · §6 |
| 13 | `153d05f2__9cbcc4fa` | **RECHAZADO** — VSN PLUS vs VSN 2-4 | fuera del `.sql` · §6 |
| 14 | `1e86c112__4bf442fb` | **APROBADO** — «mismo producto» | **VIVO** · 1 marca |
| 15 | `3caeba69__a6d93291` | **RECHAZADO** — NRX-OPT vs NRX-SMT3 | fuera del `.sql` · §6 |
| 16 | `0befac70__af770ec5` | **RECHAZADO** (final) — REL-2000 ≠ ZXCE | fuera de los pastes · §8.5 |
| 17 | `f3e9aaa9__fea0ec1d` | **RECHAZADO** — **MMX-10M vs MCX-55M** | fuera del `.sql` · §6 |
| 18 | `0ef10ac7__7601da55` | **RECHAZADO** (final) — tóxico ≠ explosivo | fuera de los pastes · §8.6 |
| 19 | `06887ff1__1d4f6e36` | **APROBADO su retiro** (final) — se queda el ES/EN | **v2.sql BLOQUE 2** · `status='retired'` · §8.7 |
| 20 | `496ef3af__f3e9aaa9` | **RECHAZADO** — el 2º es **CMX-10RM** | fuera del `.sql` · §6 |
| 21 | `1e2b058a__4421642f` | **RECHAZADO** — el 1º es **20/20U / 20/20UB** | fuera del `.sql` · §6 |
| 22 | `5e483105__71654eda` | **SUPERSEDED** — `TG-Honeywell_Usuario` supersede al otro | **v2.sql BLOQUE 3** · variante **A** · §7 |
| 23 | `29a94dea__30c75a7c` | **RECHAZADO** — **MIE-MI-450 = IMPRESORA** de centrales ZXAE/ZXEE | fuera del `.sql` · §6 |
| 24 | `af5d5d01__b9c694a3` | **KEEP-BOTH** — doc_type distinto (instalación vs funcionamiento) | fuera del `.sql` · §9 |

**Recuento FINAL (tras adjudicar §8 y el BLOQUE S): 4 aprobados por dedup (17 marcas) · 1 retiro de
documento · 14 rechazados · 1 en espera (par 5) · 2 superseded (linaje) · 2 keep-both.**
De las 121 marcas que proponía el census entran **17** (14.0%): 12 en el `v1.sql` (**aplicadas**) +
5 en el `v2.sql` (par 4, **pendientes de paste**). El census acertó el par semilla, 2 duplicados
reales y el par 4; los otros 20 pares eran falsos positivos de dedup — de tres clases distintas
(producto, revisión, función), y **ninguna de las tres la puede separar un umbral de solape**.
Aparte del dedup, la adjudicación produjo **dos mecanismos que `duplicate_of` no puede expresar**:
el **retiro** de una edición de idioma (par 19) y el **linaje de revisión** (pares 9 y 22).

### 0.0 Reparto por paste

| paste | contenido | estado |
|---|---|---|
| `s287_p2_dedup_apply_v1.sql` | metadata-fix del par semilla + 12 marcas (pares 1, 2, 14) | **APLICADO** · verificado en vivo 12/12, 0 discrepancias |
| `s287_p2_dedup_apply_v2.sql` BLOQUE 1 | par 4 · 5 marcas `duplicate_of` | escrito · guards pre-validados · **pendiente de paste** |
| `s287_p2_dedup_apply_v2.sql` BLOQUE 2 | par 19 · retiro del doc ES/PT (`status='retired'`) | escrito · guards pre-validados · **pendiente de paste** |
| `s287_p2_dedup_apply_v2.sql` BLOQUE 3 | BLOQUE S variante **A** · linaje de #9 y #22 | escrito · guards pre-validados · **pendiente de paste** |
| `s287_p2_dedup_apply_v2.sql` S.2 / 3-bis | des-enlace HP011 · `revision`/`revision_date` | **COMENTADOS** — ninguno es efecto-cero, ver §7.3 |

### 0.1 Qué cambió en el `v1.sql`

1. **Bloque 0** (metadata-fix del par semilla) y **PAR 1** (10 filas): **INTACTOS**, byte a byte.
2. **PAR 2** y **PAR 14**: filas **DESCOMENTADAS**. Sus 8 guards se **re-pre-validaron en vivo**
   (read-only, 2026-07-30, posterior al census) junto con los 10 del par semilla: **12/12 filas,
   0 fallos** — md5 sin deriva · ninguno ya marcado · canónico existente, no-duplicado y dentro
   del representante · el chunk pertenece al doc suprimido · sin cadenas · gate 3f OK ·
   **0 filas de `chunks_v2_enunciados`** colgando. Dry-run esperado: `staged=12 · updated=12 · backed_up=12`.
3. **Los 10 rechazados** salen del `.sql`: sus filas se han **borrado**, y en su hueco queda un
   bloque de comentario con tu ground truth y la causa del falso positivo.
4. **PAR 9 y PAR 22** salen del dedup y pasan al **BLOQUE S** (linaje de revisión), comentado
   entero. **Ojo**: las filas que el census proponía para esos dos pares iban en la dirección
   CONTRARIA (retiraban chunks de la revisión NUEVA) → se caen.
5. **PAR 8 y PAR 24**: filas borradas; verificado que su `doc_type` ya es correcto (§9).
6. **Los 7 abiertos**: filas **comentadas tal cual**, con mi propuesta inline. Nada suyo entra hoy.
7. **Bloque 0-bis** nuevo, comentado: candidato de metadata para el representante del PAR 2.

> Los puntos 4 y 6 quedaron **superados** por la adjudicación final: los 7 abiertos ya tienen
> veredicto (§8) y el BLOQUE S está resuelto a la **variante A** (§7.3). Lo que de ellos entra
> vive en el `v2.sql`; el `v1.sql` no se ha vuelto a tocar (es la traza de lo aplicado).
> El **bloque 0-bis** (pm `unknown`→`DXc` del representante del PAR 2) sigue **sin adjudicar** y
> por tanto **no** se ha trasladado al `v2.sql`: queda en el ticket A3.

## Qué decidir y cómo — *(cerrado: ya no queda nada que decidir)*

El census propone marcar `duplicate_of` **chunk a chunk** (no doc a doc): de un par de documentos casi idénticos se retira del pool SOLO los chunks del no-representante cuyo contenido está **íntegramente** en el representante. Todo lo demás sigue sirviéndose.

- **24 pares** con propuesta · **121 marcas** de chunk (120 del census + 1 por la inversión del par semilla, §1.6).
- **Entran 17 marcas** en total: 12 aplicadas (`v1.sql`) + 5 pendientes (`v2.sql`, par 4). El resto de pares queda rechazado, en espera, o resuelto por un mecanismo distinto de `duplicate_of` (retiro / linaje).

### La decisión es DOBLE por par (política Alberto s287)

Aprobar un par ya no es una casilla, son dos:

1. **¿Se deduplica el par?** — sí/no, con la tabla §3 y las clases de falso positivo de §3.1.
2. **¿La metadata del REPRESENTANTE es correcta?** — fabricante **y** `product_model`, y a los **DOS niveles** (`documents` **y** `chunks_v2`): el par semilla demostró que divergen en silencio (doc B: `documents.product_model='unknown'` pero los 18 chunks decían `VIA-28V`; doc A: `documents.product_model='IS5001'` pero los chunks decían `IS-mA1`, y el bueno era el de los chunks). Si está mal, **el fix va en el MISMO paste** — usa el bloque 0 del `.sql` como plantilla (backup + guards de precondición + `UPDATE` acotado por `document_id` + post-check).

Motivo: marcar `duplicate_of` **concentra** todas las citas del contenido compartido en el representante. Bendecir un representante con metadata mala multiplica el error en vez de arreglarlo.

### El invariante que protege el corpus (gate de Sol-6)

Un chunk solo se propone si (a) ≥ **92% de sus palabras** están cubiertas por el documento representante, (b) **ninguna racha de ≥ 25 palabras** queda sin cubrir, y (c) existe un chunk gemelo concreto con Jaccard ≥ 0.6 al que apuntar. Los chunks `UNIQUE`, `PARTIAL`, `COVERED_NO_TWIN` y `SHORT` **nunca** se proponen — un near-dup a nivel documento puede perfectamente tener spans propios, y el par semilla lo demuestra.

---

## 1. PAR SEMILLA (cat010) — **ADJUDICADO POR ALBERTO (s287): OPCIÓN B**

> **Veredicto de Alberto — el representante es `manual IS MA1` (doc B), NO `IS5001-F_IS-mA1_EN`.**
> Motivo largoplacista: *representante = el doc canónico completo por manual físico*. B es la
> extracción más completa (8 páginas, incluye el control drawing ATEX) y su metadata corrupta
> se corrige **en el mismo paste** (bloque 0 del `.sql`). Esto invierte la recomendación
> original del census (§1.4 abajo, conservada como traza). Ya no hay casilla que marcar en
> este par: las 10 filas del PAR 1 salen **VIVAS** en el `.sql`.
>
> **Lo que la adjudicación cambió en el paste** (todo pre-validado read-only contra la DB viva):
> 1. **Dirección invertida**: se marcan chunks de **A** apuntando a su gemelo en **B**.
> 2. **10 marcas, no 9** — la clase TWIN es direccional (§1.6).
> 3. **Bloque 0 de METADATA-FIX** con guards de precondición (§1.7).

`2b694083__a6b9dc84` · tier **T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA** · cobertura de palabras 0.72 / 0.89

| | doc A (**AHORA suprimido-parcial**) | doc B (**AHORA representante**) |
|---|---|---|
| `source_pdf_filename` | `IS5001-F_IS-mA1_EN` | `manual IS MA1` |
| `document_id` | `2b694083-5b21-4f1a-a29b-565072860fb8` | `a6b9dc84-af6d-4957-a403-4b4c2136557b` |
| `manufacturer` | **European Safety Systems** | **Detnov** |
| `product_model` (doc) | IS5001 | unknown |
| `product_model` (chunks) | ['IS-mA1'] | ['VIA-28V'] |
| idioma (mayoría de chunks) | en | en |
| chunks activos | 15 | 18 |
| páginas | [1, 2, 3, 4, 5, 6] | [1, 2, 3, 4, 5, 6, 7, 8] |
| `revision` / `revision_date` | None / None | None / None |
| `ingested_at` | 2026-04-16T03:17:49.642032+00:00 | 2026-04-16T08:29:42.688067+00:00 |
| palabras cubiertas por el otro doc | **89.0%** | **71.8%** |
| clases de span | {'PARTIAL': 5, 'TWIN': 10} | {'PARTIAL': 5, 'TWIN': 9, 'UNIQUE': 4} |

### 1.1 Qué son estos dos documentos

Son **dos extracciones distintas del MISMO manual de e2S** (el sounder ATEX IS-mA1). Lo prueba el contenido, no la metadata: los dos textos contienen `european safety systems` y `e2s`, los dos contienen `is-ma1`, y los pares de chunks gemelos llegan a Jaccard **1.000**.

### 1.2 La metadata de B está MAL (verificado contra su propio texto)

- `manual IS MA1` está atribuido a **Detnov**, y la cadena `detnov` **no aparece en su propio contenido** (`metadata_self_support.manufacturer.supported = False`). Su texto dice `european safety systems ltd. impress house, mansell road, acton, london w37qh`.
- Su `product_model` es `unknown` a nivel doc y `['VIA-28V']` a nivel chunk. **`VIA-28V` es un artefacto de parseo**: viene de la frase del manual «a 24V dc supply **via 28V** 93mA resistive ATEX ... Zener Barriers». No es un modelo.
- `IS5001-F_IS-mA1_EN` está atribuido a **European Safety Systems**, y sus tres tokens SÍ aparecen en su contenido. Su pm de chunk es `IS-mA1` (correcto).

### 1.3 Por qué NO se puede suprimir B entero (el gate de Sol-6 mordiendo)

> *Traza del análisis original, cuando B era el candidato a suprimir. Sigue siendo la
> evidencia clave — solo que ahora sostiene la decisión de Alberto: si B tiene 4 páginas de
> contenido que A no tiene, B es el manual físico completo y debe ser el representante.*

El PDF de B tiene **8 páginas** frente a 6 de A. Sus páginas finales son contenido **ausente de A**:

- chunk `75d15cc3` (idx 14, p7, 470 palabras): cubierto solo al **6.2%**, racha única de **349 palabras**.
  > (-40°c ≤ t<sub>a</sub> ≤ +60°c) **entity parameters:** terminals + w.r.t. - * u<sub>i</sub> = 28v * i<sub>i</sub> = 93ma * p<sub>i</sub> = 660mw * c<sub>i</sub> = 0 * l<sub>i</sub> = 0 terminals s2 & s3 w.r.t. - * u<sub>i</sub> =…
- chunk `a979aa4c` (idx 16, p8, 444 palabras): cubierto solo al **6.5%**, racha única de **288 palabras**.
  > (-40°c ≤ t<sub>a</sub> ≤ +60°c) **entity parameters:** terminals + w.r.t. - u<sub>i</sub> = 28v i<sub>i</sub> = 93ma p<sub>i</sub> = 660mw c<sub>i</sub> = 0 l<sub>i</sub> = 0 terminals s2 & s3 w.r.t. - u<sub>i</sub> = 28v i<sub>i<
- chunk `459afd9b` (idx 15, p7, 106 palabras): cubierto solo al **0.0%**, racha única de **106 palabras**.
  > **schedule drawing** no modification permitted without reference to the "notified body" ---- | | | | | **title**<br/><br/>is-ma1 sounder<br/>control drawing for shunt zener diode barrier / diode return barrier. | 2s<br/>warning si
- chunk `9334a0b8` (idx 17, p8, 102 palabras): cubierto solo al **0.0%**, racha única de **102 palabras**.
  > no modification permitted without reference to the "notified body" ---- | | | | | title<br/><br/>is-ma1 sounder<br/><br/>control drawing for galvanically<br/><br/>isolated supply / isolated relay<br/><br/>installation. | e2s<br/>w

Es el **control drawing / schedule drawing ATEX** con los *entity parameters* (`Ui = 28V`, `Ii = 93mA`…) y las condiciones de instalación con barrera Zener. Eso es **exactamente el territorio de los hechos de cat010** — y solo existe en B. Suprimir B entero habría borrado contenido servible relevante para el propio gold que motivó esta pieza. Los 4 chunks van marcados `UNIQUE` → **no se tocan**.

### 1.4 Las dos políticas de representante DIVERGEN aquí

- **Literal del spec v2-P2** (más spans únicos gana): conservaría `manual IS MA1` — más spans únicos (13 vs 7).
- **Refinamiento propuesto** (auto-soporte de metadata primero): conserva `IS5001-F_IS-mA1_EN` — metadata auto-soportada (2/3 vs 0/3).

El census recomendó el refinamiento razonando que los spans únicos **nunca se suprimen** —ya los protege el gate—, así que «más spans únicos» no protege contenido y lo único que decide el representante es **de qué documento sale la CITA**. Con el criterio literal, el bot citaría `manual IS MA1` atribuido a **Detnov** para un producto de e2S.

**Alberto resolvió la divergencia por una tercera vía, que es la que manda**: el representante NO se elige entre «metadata buena pero doc incompleto» y «doc completo pero metadata mala» — se elige el **doc completo** y **se arregla la metadata**. Eso disuelve el dilema en vez de arbitrarlo: la cita sale del manual físico completo Y sale bien atribuida.

**Riesgo del criterio de auto-soporte, declarado (sigue vivo para los otros pares):** es una heurística de substring. Un `manufacturer` correcto que simplemente no se imprime en el manual puntúa 0 (falso negativo) — por eso no se aplica solo y todos los pares divergentes van a tu casilla.

### 1.5 Evidencia NUEVA que refuerza la opción B: **B es la ISSUE MÁS NUEVA**

Sonda de contenido read-only (2026-07-30) sobre los dos docs. El pie de página de e2S da la revisión:

| | doc A `IS5001-F_IS-mA1_EN` | doc B `manual IS MA1` |
|---|---|---|
| pie de página | `Document No. IS 5001  Issue F  06-08-15` (portada) + `Issue E  27-11-09` (hojas 2-6) | `Document No. IS 5001  Issue H  03-01-2020` (**las 6 hojas**) |
| directivas de la portada | `94/9/EC` (ATEX) + `89/336/EEC` (EMC) — **derogadas** | `2014/34/EU` (ATEX) + `2014/30/EU` (EMC) — **vigentes** |
| páginas | 6 | 8 (+control drawing ATEX) |

Los dos son el **mismo documento** (`IS 5001`) en revisiones distintas: A mezcla Issue F/E (2009-2015), B es Issue H (2020). Además de más completo, B es **más reciente y regulatoriamente correcto**. Esto no lo vio el census —su desempate por recencia usa `revision`/`revision_date`/`ingested_at`, y ambos docs tienen `revision = NULL`— pero apunta en la misma dirección que la adjudicación.

**Residual declarado:** el dedup NO resuelve la contradicción de revisión. El chunk `idx0` de A es `PARTIAL` → **sobrevive** y sigue declarando las directivas derogadas `94/9/EC`/`89/336/EEC`. El arreglo estructural de esa clase es el **linaje de revisión** (`supersedes_id`/`superseded_by_id`, hoy `NULL` en ambos docs), no `duplicate_of`.

### 1.6 Por qué son **10** marcas y no 9 (la clase TWIN es DIRECCIONAL)

Invertir el par **no es invertir los 9 punteros**. `covered_word_frac` y `max_uncovered_span_words` se miden *del chunk contra el OTRO documento*; solo `twin_jaccard` es simétrico. El census ya midió las dos direcciones:

- `side_b.classes` (B cubierto por A) = `{TWIN: 9, PARTIAL: 5, UNIQUE: 4}` → las 9 marcas del sentido viejo.
- `side_a.classes` (**A cubierto por B**) = `{TWIN: 10, PARTIAL: 5}` → **las 10 marcas del sentido nuevo**.

Los 9 punteros invertidos son un **subconjunto** de los 10. El que falta es el chunk `77003e0f` (idx2, p2, 504 palabras): TWIN en esta dirección (cobertura **0.9325**, racha máxima sin cubrir **0**, gemelo `77a0cce8` con J 0.6351), y no salía en el sentido viejo porque su gemelo es `PARTIAL` en B (cobertura 0.9061 < 0.92). Es la asimetría esperada: B es la issue nueva y tiene texto propio que A no tiene.

Haber reciclado los números del lado B habría dejado el **guard 3f validando métricas de otro chunk** — un guard verde sobre datos equivocados. Las 10 filas del `.sql` llevan los valores del lado A. Si prefieres la inversión literal de 9, basta comentar la fila marcada `[+1]`.

A queda con sus **5 chunks PARTIAL** servibles (idx 0, 5, 7, 8, 9 — diagramas de barrera Zener/aislador galvánico con texto propio) y B entero con sus 18.

### 1.7 El bloque 0: METADATA-FIX en el mismo paste (5 campos)

Verificado contra la DB viva antes de escribir nada:

| # | objeto | campo | antes | después | evidencia |
|---|---|---|---|---|---|
| 1 | `documents` doc B | `manufacturer` | `Detnov` | `European Safety Systems` | `detnov` no aparece en su texto; su contenido dice «european safety systems ltd. impress house…» y `e2S` |
| 2 | `documents` doc B | `product_model` | `unknown` | `IS-mA1` | portada: «INSTRUCTION MANUAL / IS-mA1 Minialarm» |
| 3 | `chunks_v2` doc B (18) | `product_model` | `VIA-28V` | `IS-mA1` | `VIA-28V` = artefacto de parseo de «…a 24V dc supply **via 28V** 93mA resistive ATEX…». Corpus-wide existe **solo** en este doc (18 chunks, 0 documents) |
| 4 | `documents` doc A | `product_model` | `IS5001` | `IS-mA1` | `IS 5001` es la **referencia del manual** (pie de página de AMBOS docs), no el producto. Sus 15 chunks ya llevan `IS-mA1` |
| 5 | `chunks_v2` doc B (18) | `manufacturer` | `Detnov` | `European Safety Systems` | **añadido por la sonda**, no estaba en la lista de 4: es el campo que FILTRA de verdad (`match_chunks_v2(filter_manufacturer)` compara `c.manufacturer`, `supabase_schema.sql:81`). Sin él, el representante nuevo serviría cat010 etiquetado `Detnov` |

Guards de precondición (patrón del guard 3a: la precondición viaja EN el paste y aborta si el estado vivo no es el que vio la sonda): estado exacto pre-fix de A y B a nivel `documents`, 18/18 chunks de B en `VIA-28V`+`Detnov`, **0 chunks con `VIA-28V` fuera de B**, 15/15 chunks de A ya correctos; y un post-check `2 documents` + `33 chunks` en el estado final. Backup en `_s287_metafix_backup_documents` / `_s287_metafix_backup_chunks` con rollback al pie del `.sql`.

**Acotación obligatoria:** el corpus tiene **66 documentos / 1409 chunks que SÍ son Detnov de verdad** → todos los `UPDATE` van acotados por `document_id`, nunca por valor.

**Residual declarado:** `chunks_v2_hyq` guarda una copia **desnormalizada** de `product_model` — 49 filas de B siguen diciendo `VIA-28V`. Es **inerte para el servicio** (`match_hyq` devuelve solo `chunk_id/question/similarity` y el retriever rehidrata desde `chunks_v2`, `retriever.py:1091`), pero queda anotado para que no se pudra en silencio.

### 1.8 Efecto esperado sobre el pool de cat010

Se retiran **10 de 15** chunks de **A** (los gemelos), y el pool queda con los **18 de B** (incluidas las 4 páginas ATEX únicas) más los **5 PARTIAL de A**. **No medido aquí**: el efecto en pool/composición es el gate de la pieza (probe de cat010 + sweep-39), no una promesa de este census.

### 1.9 POLÍTICA NUEVA para los pares siguientes (criterio Alberto s287)

> **El representante es la extracción MÁS COMPLETA, con su metadata CORREGIDA.**
> Si la metadata del más completo está corrupta, **el fix va en el MISMO paste** que el
> `duplicate_of` — no se elige un doc peor para esquivar una metadata mala.

Sustituye al desempate del census («auto-soporte de metadata» y, antes, «más spans únicos») como criterio rector cuando ambos entran en conflicto. Orden de aplicación:

1. **Completitud del manual físico** — quién tiene las páginas/secciones que el otro no tiene (spans `UNIQUE`), y, si se ve en el propio texto, quién es la **issue más reciente**.
2. **Metadata**: se **verifica** contra el contenido del doc (fabricante impreso, modelo de portada) y se **corrige en el paste** si hace falta — a nivel `documents` **y** `chunks_v2`.
3. Los desempates del census (auto-soporte, spans únicos, recencia por `revision`/`ingested_at`) quedan como **señal**, no como decisión.

Por qué es el criterio correcto y no un parche: `duplicate_of` **concentra** las citas del contenido compartido en un solo doc. Elegir por metadata (un atributo *reparable*) en vez de por completitud (una propiedad *intrínseca* de la extracción) optimiza la variable equivocada — y encima deja servible la extracción pobre. Escala: a 30+ fabricantes, la metadata se arregla en lote con el mismo patrón de guards; la completitud del PDF, no.

**Gap declarado:** la política asume que «más completo» es discernible. En pares manual-vs-datasheet o instalación-vs-operación (§3.1) **ningún doc contiene al otro**: son documentos distintos por FUNCIÓN y la respuesta correcta suele ser **no deduplicar**, no elegir representante.

### 1.10 TRES REGLAS MÁS, confirmadas por Alberto al adjudicar los 24 (s287)

Nacen de esta adjudicación y **gobiernan de aquí en adelante**, no solo este packet:

1. **Divergencia `documents` ↔ `chunks_v2` (17 de 24 representantes, §3.2): se adjudica POR-DOC
   contra la PORTADA** — el patrón que resolvió el par semilla (`IS-mA1` sale de «INSTRUCTION
   MANUAL / IS-mA1 Minialarm», no de un voto entre los dos niveles). **Lo que no tenga portada
   clara va a Alberto en LOTE**, no se resuelve por heurística. Corolario operativo: la regla
   «copia el nivel que no diga `unknown`» queda **prohibida** — el par semilla y el `EN-54-25`
   del NRX-OPT demuestran que el nivel poblado puede ser justo el artefacto.
2. **La etiqueta fina `-IS` de Argus a nivel chunk queda BLINDADA.** `SG100-IS`/`SG200-IS`/`SG350-IS`
   son **productos DISTINTOS** de `SG100`/`SG200`/`SG350` (decisión explícita de Alberto, aunque los
   manuales parezcan casi idénticos). **Ninguna normalización doc→chunks puede borrarla**: hoy la
   distinción vive SOLO en `chunks_v2.product_model`, y un fix que «alineara» el chunk al doc-level
   la destruiría. Es coherente con sus rechazos de los pares 7/10/11 y con el falso positivo de §3.1.
   El fix correcto va en la dirección contraria: subir la etiqueta fina al `documents.product_model`.
3. **`EN-54-25` es un artefacto de parseo, no un modelo** (es la NORMA de componentes con enlace
   radio). El `product_model` real del doc `I56-4225-001 NRX-OPT Web` es **`NRX-OPT`** (ground truth
   de Alberto). Fix candidato: 12 chunks + doc-level → ticket **A3** (§10). Es la segunda instancia
   confirmada de la clase `VIA-28V`; la tercera aparece en este mismo packet (`MODELO-6500R`, §10).

---

## 2. Alcance del census y qué NO se toca

- Universo servido: **992 documentos** `status='active'` con chunks `duplicate_of IS NULL` (22087 chunks). Excluidos y por qué: en `meta.alcance_declarado.exclusiones` del JSON.
- **CORPUS-WIDE all-pairs: 491536 pares evaluados**, sin blocking por fabricante ni por título. Esto era obligatorio: el par semilla **cruza fabricante** (European Safety Systems vs Detnov), así que el audit s62 —que solo comparaba dentro de cada `manufacturer`— era estructuralmente incapaz de verlo.
- 620 candidatos tras el blocking (unión de 4 nets) → 226 cualifican como near-dup de documento.

| veredicto | pares | qué significa |
|---|---|---|
| `SUPPRESS-COVERED` | 36 | candidatos reales de dedup (24 con marcas concretas) |
| `KEEP-BOTH-LANG` | 11 | idiomas distintos → variante de mercado, NUNCA suprimir |
| `KEEP-BOTH-BRAND` | 38 | rebadge OEM legítimo (cada doc imprime su propia marca) → workstream de identidad D1/D3, no dedup |
| `KEEP-BOTH-SERIE` | 141 | hermanas de serie (modelos distintos, plantilla común) → suprimir aquí es el daño DEC-091b |
| `NO-QUALIFY` | 394 | solape parcial (boilerplate), no near-dup |

### 2.1 El hallazgo que cambia la pieza: la mayoría de los near-dups NO son dedupables

De los 226 pares que cualifican por cobertura de contenido, **141 son hermanas de serie** — datasheets del mismo fabricante con plantilla común y 0.90+ de cobertura mutua (Aritech `2X-AT-F2`/`-S`/`-FB`/`-P`, Kilsen `KE-IO3122`/`KE-IO3144`, `NC-PF2`/`NC-PF4`, `NAS-10`/`NAS-20`, `AutoSAT-10`/`-20`, `SG200-IS`/`SG350-IS`, `FHSD8310`/`FHSD8330`…). Marcarlas `duplicate_of` haría que el bot sirviera el manual del **modelo equivocado**: el daño exacto de DEC-091b. Para esa clase el lever correcto es el **dedup-EN-POOL** (el fallback que el spec deja explícitamente no construido aquí), que limita slots sin borrar identidad.

Y **38 son rebadges OEM Notifier↔Morley** con las dos marcas impresas en sus propios textos (`MNDT102`/`MIEMN570` para RP1r, `MIDT015`/`MIE-MI-100` para NFS2-8…). Deduplicarlos colapsaría distinciones que ya adjudicaste en s78/s80 (RP1r-Supra=Notifier vs VSN-RP1r=Morley).

---

## 3. Pares a adjudicar (los que tienen propuesta)

> ⚠ **TABLA HISTÓRICA — es la PROPUESTA DEL CENSUS, ya adjudicada.** Los veredictos de Alberto
> están en **§0**; esta tabla se conserva como traza de qué proponía el instrumento y con qué
> criterio, porque es lo que explica *por qué* 21 de 24 eran falsos positivos (§6, §7, §8).

**Call-to-action DOBLE por par** (política Alberto s287): **(1)** aprobar o rechazar el par — tabla de abajo + §3.1; **(2)** **CONFIRMAR la metadata del representante elegido** (fabricante + `product_model`) **a los dos niveles**, `documents` y `chunks_v2` — sonda en §3.2. Si está mal, el fix va **en el mismo paste**, con el bloque 0 del `.sql` como plantilla.

Ordenados: semilla primero, luego por nº de marcas. `div` = las dos políticas de representante discrepan.

| # | par | tier | div | CONSERVA | SUPRIME (marcas/total) | PRESERVA | cob. | motivo |
|---|---|---|---|---|---|---|---|---|
| 1 **SEMILLA** — ~~[ ]~~ **ADJUDICADO · OPCIÓN B** | `2b694083__a6b9dc84` | T3 | resuelta | **`manual IS MA1`** (→ European Safety Systems, metadata corregida en el bloque 0) | `IS5001-F_IS-mA1_EN` **10/15** | PARTIAL=5 | 0.89/0.72 | **Alberto: doc canónico completo por manual físico** (§1) |
| 2 | `5e878ee7__eb749df8` | T1 |  | `DXc_Connexion Averia-de-resistencia-de-baterias.pdf` (Morley) | `Averia-de-resistencia-de-baterias-en-central-DXc.pdf` (Morley) 1/1 | — | 0.95/0.96 | empate → más reciente (revision_date/revision/ingested_at) |
| 3 | `517b87ce__de8c0345` | T3 |  | `FS2-1` (Notifier) | `ms1-2-4.pdf` (Morley) 12/27 | UNIQUE=4, PARTIAL=5, COVERED_NO_TWIN=6 | 0.80/0.86 | metadata auto-soportada (2/3 vs 0/3) |
| 4 | `7f9ea4ab__acafc5d1` | T2 |  | `MNDT1026` (Notifier) | `MNDT1025` (Notifier) 5/23 | UNIQUE=3, PARTIAL=12, COVERED_NO_TWIN=3 | 0.64/0.85 | empate metadata → más spans únicos (18 vs 8) |
| 5 | `5800c4c0__cbc9c21c` | T3 | SÍ | `FS8` (Notifier) | `MS8.pdf` (Morley) 30/63 | UNIQUE=8, PARTIAL=20, COVERED_NO_TWIN=5 | 0.84/0.85 | metadata auto-soportada (1/3 vs 0/3) |
| 6 | `2c299ef1__89024b18` | T2 |  | `D 1148-1 BRS Notifier` (Notifier) | `D 1147-1 BRH Notifier` (Notifier) 2/7 | UNIQUE=2, PARTIAL=2, COVERED_NO_TWIN=1 | 0.80/0.83 | metadata auto-soportada (3/3 vs 1/3) |
| 7 | `2e0ee11a__b788bbda` | T2 |  | `Instruction Manual SG100-IS ENG` (Argus Security) | `Instruction Manual SG100 ENG` (Argus Security) 2/13 | UNIQUE=2, PARTIAL=8, COVERED_NO_TWIN=1 | 0.66/0.77 | empate metadata → más spans únicos (9 vs 2) |
| 8 | `1c6eff80__6d84be7f` | T2 |  | `MNDT1070` (Notifier) | `MFDT1070` (Notifier) 9/34 | UNIQUE=5, PARTIAL=19, COVERED_NO_TWIN=1 | 0.23/0.77 | empate metadata → más spans únicos (86 vs 21) |
| 9 | `681e506b__a7bf5098` | T3 | SÍ | `MI-DT-951_V7.2` (Notifier) | `Tg-Honeywell_Introduccion` (Morley) 2/25 | UNIQUE=12, PARTIAL=10, COVERED_NO_TWIN=1 | 0.52/0.75 | metadata auto-soportada (2/3 vs 1/3) |
| 10 | `f8020fa4__fc285f22` | T2 |  | `Instruction Manual SG200-IS ENG` (Argus Security) | `Instruction Manual SG200 ENG` (Argus Security) 1/12 | UNIQUE=1, PARTIAL=9, COVERED_NO_TWIN=1 | 0.65/0.74 | empate metadata → más spans únicos (10 vs 6) |
| 11 | `29c145dc__c270c9c7` | T2 |  | `Instruction Manual SG350-IS ENG` (Argus Security) | `Instruction Manual SG350 ENG` (Argus Security) 1/8 | PARTIAL=7 | 0.66/0.74 | empate metadata → más spans únicos (10 vs 7) |
| 12 | `65246432__a6d93291` | T2 |  | `I56-4225-001 NRX-OPT Web` (Notifier) | `I56-4206-001 NRX Radio Thermals Web` (Notifier) 2/12 | UNIQUE=2, PARTIAL=6, COVERED_NO_TWIN=2 | 0.50/0.72 | empate metadata → más spans únicos (11 vs 7) |
| 13 | `153d05f2__9cbcc4fa` | T2 |  | `MIEMI130.pdf` (Morley) | `MIEMI120rev05.pdf` (Morley) 6/46 | UNIQUE=7, PARTIAL=32, COVERED_NO_TWIN=1 | 0.62/0.71 | empate metadata → más spans únicos (58 vs 44) |
| 14 | `1e86c112__4bf442fb` | T3 | SÍ | `I56-2081-001ES 6500R(S) Manual` (System Sensor) | `I56-2081-012 6500R(S)_ES` (Xtralis) 1/20 | UNIQUE=6, PARTIAL=9, COVERED_NO_TWIN=4 | 0.68/0.69 | metadata auto-soportada (3/3 vs 1/3) |
| 15 | `3caeba69__a6d93291` | T2 |  | `I56-4225-001 NRX-OPT Web` (Notifier) | `I56-4205-001 NRX-SMT3 Web` (Notifier) 3/16 | UNIQUE=3, PARTIAL=8, COVERED_NO_TWIN=2 | 0.63/0.69 | REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'I56-4225-001 NRX-OPT Web' (metadata 3/3, 11 spans únicos). Original por-par: empate metadata → más spans únicos (10 vs 7) |
| 16 | `0befac70__af770ec5` | T2 |  | `MIE-MP-210.pdf` (Morley) | `MIE-MI-220.pdf` (Morley) 2/11 | UNIQUE=5, PARTIAL=4 | 0.07/0.69 | empate metadata → más spans únicos (105 vs 7) |
| 17 | `f3e9aaa9__fea0ec1d` | T2 |  | `MIE-MI-490.pdf` (Morley) | `MIE-MI-480.pdf` (Morley) 2/7 | UNIQUE=2, PARTIAL=3 | 0.62/0.67 | empate metadata → más spans únicos (6 vs 4) |
| 18 | `0ef10ac7__7601da55` | T2 |  | `MNDT626.pdf` (Notifier) | `MNDT625.pdf` (Notifier) 4/18 | UNIQUE=4, PARTIAL=9, COVERED_NO_TWIN=1 | 0.49/0.67 | empate metadata → más spans únicos (24 vs 16) |
| 19 | `06887ff1__1d4f6e36` | T2 |  | `MNDT516` (Notifier) | `MNDT516_PL4_ESP-PORT` (Notifier) 11/26 | UNIQUE=9, PARTIAL=5, COVERED_NO_TWIN=1 | 0.36/0.67 | metadata auto-soportada (3/3 vs 1/3) |
| 20 | `496ef3af__f3e9aaa9` | T2 |  | `MIE-MI-490.pdf` (Morley) | `MIE-MI-470.pdf` (Morley) 2/6 | UNIQUE=1, PARTIAL=3 | 0.55/0.66 | REORIENTADO por consistencia de cluster: el representante del cluster de 3 docs es 'MIE-MI-490.pdf' (metadata 2/3, 6 spans únicos). Original por-par: empate metadata → más spans únicos (6 vs 4) |
| 21 | `1e2b058a__4421642f` | T2 |  | `MNDT710_B.pdf` (Spectrex) | `MNDT720.pdf` (Spectrex) 6/41 | UNIQUE=14, PARTIAL=21 | 0.56/0.66 | empate metadata → más spans únicos (36 vs 30) |
| 22 | `5e483105__71654eda` | T3 | SÍ | `MN-DT-951_v7.2` (Notifier) | `TG-Honeywell_Usuario` (Morley) 1/57 | UNIQUE=33, PARTIAL=17, COVERED_NO_TWIN=6 | 0.40/0.66 | metadata auto-soportada (2/3 vs 1/3) |
| 23 | `29a94dea__30c75a7c` | T2 |  | `MIE-MI-431rv2_1.pdf` (Morley) | `MIE-MI-450.pdf` (Morley) 1/8 | UNIQUE=7 | 0.33/0.65 | empate metadata → más spans únicos (17 vs 7) |
| 24 | `af5d5d01__b9c694a3` | T2 |  | `00-3280-501-4009-05_r005_2x-a_series_installation_manual_es.pdf` (Aritech) | `00-3280-505-4009-04_r004_2x-a_series_operation_manual_es.pdf` (Aritech) 5/44 | UNIQUE=16, PARTIAL=16, COVERED_NO_TWIN=7 | 0.20/0.62 | metadata auto-soportada (3/3 vs 1/3) |

### 3.1 Clases de falso positivo que YA vi en esta tabla (mira antes de aprobar)

El census no las puede separar por umbral; por eso todo va comentado:

- **Variante intrínsecamente segura vs estándar**: `SG100` vs `SG100-IS`, `SG200` vs `SG200-IS`, `SG350` vs `SG350-IS` (Argus). Productos DISTINTOS con manual casi igual.
- **Manual vs datasheet/ficha del mismo producto**: `MNDT1070` vs `MFDT1070` (LTS-240), `MNDT516` vs `MNDT516_PL4_ESP-PORT`, `2x-a_series_installation` vs `2x-a_series_operation`. Documentos distintos por FUNCIÓN.
- **Módulos hermanos con `pm` heredado o `unknown`**: `MIE-MI-470`/`480`/`490` (Morley), `NRX-SMT3` vs `NRX-OPT` (los dos con `pm='B501RF'`, que es la BASE común, no el detector), `D 1148-1 BRS` vs `D 1147-1 BRH` (los dos `pm='B501AP'`). El discriminador de serie no los pilla porque su `pm` no distingue.
- **Duplicados de verdad, casi seguros**: `TIDT089_copia` vs `TIDT089`, el FAQ DXc `Averia-de-resistencia-de-baterias` duplicado con el título reordenado, y `Con-que-Sistema-Operativo-es-compatible-el-programa-…` repetido.

### 3.2 Metadata del REPRESENTANTE a los DOS niveles (sonda read-only 2026-07-30)

El par semilla enseñó que `documents` y `chunks_v2` **divergen en silencio** y que el valor bueno puede estar en cualquiera de los dos. Esta es la sonda del representante de cada par contra la DB viva (chunks con `duplicate_of IS NULL`). **17 de 24 divergen.**

| # | representante | `documents.manufacturer` | `documents.product_model` | chunks `manufacturer` | chunks `product_model` | ⚠ |
|---|---|---|---|---|---|---|
| 1 | `manual IS MA1` | Detnov | unknown | `Detnov`×18 | `VIA-28V`×18 | **pm** → *corregido en el bloque 0* |
| 2 | `DXc_Connexion Averia-de-resistencia-de-baterias.pdf` | Morley | unknown | `Morley`×1 | `DXc`×1 | pm |
| 3 | `FS2-1` | Notifier | FS2-1 | `Notifier`×28 | `FS-1/FS-2/FS-4`×28 | pm |
| 4 | `MNDT1026` | Notifier | VIEW | `Notifier`×30 | `VIEW`×30 | — |
| 5 | `FS8` | Notifier | EFS/EM 8 | `Notifier`×63 | `EFS/EM 8`×63 | — |
| 6 | `D 1148-1 BRS Notifier` | Notifier | B501AP | `Notifier`×8 | `SP-20`×8 | pm |
| 7 | `Instruction Manual SG100-IS ENG` | Argus Security | SG100 | `Argus Security`×15 | `SG100-IS`×15 | pm |
| 8 | `MNDT1070` | Notifier | LTS-240 | `Notifier`×99 | `LTS-240`×99 | — |
| 9 | `MI-DT-951_V7.2` | Notifier | unknown | `Notifier`×16 | `TG-NOTIFIER`×16 | pm |
| 10 | `Instruction Manual SG200-IS ENG` | Argus Security | SG200 | `Argus Security`×14 | `SG200-IS`×14 | pm |
| 11 | `Instruction Manual SG350-IS ENG` | Argus Security | SG350 | `Argus Security`×13 | `SG350-IS`×13 | pm |
| 12 | `I56-4225-001 NRX-OPT Web` | Notifier | B501RF | `Notifier`×12 | `EN-54-25`×12 | pm |
| 13 | `MIEMI130.pdf` | Morley | unknown | `Morley`×52 | `VSN PLUS`×52 | pm |
| 14 | `I56-2081-001ES 6500R(S) Manual` | System Sensor | 6500R | `System Sensor`×22 | `6500R`×22 | — |
| 15 | `I56-4225-001 NRX-OPT Web` | Notifier | B501RF | `Notifier`×12 | `EN-54-25`×12 | pm |
| 16 | `MIE-MP-210.pdf` | Morley | unknown | `Morley`×104 | `ZXCE`×104 | pm |
| 17 | `MIE-MI-490.pdf` | Morley | unknown | `Morley`×6 | `MMX-10M`×6 | pm |
| 18 | `MNDT626.pdf` | Notifier | SMART 3 | `Notifier`×23 | `SMART 3`×23 | — |
| 19 | `MNDT516` | Notifier | PL4 | `Notifier`×49 | `PL4`×49 | — |
| 20 | `MIE-MI-490.pdf` | Morley | unknown | `Morley`×6 | `MMX-10M`×6 | pm |
| 21 | `MNDT710_B.pdf` | Spectrex | 20/20U, 20/20UB | `Spectrex`×47 | `20/20UB`×47 | pm |
| 22 | `MN-DT-951_v7.2` | Notifier | unknown | `Notifier`×38 | `TG-NOTIFIER`×38 | pm |
| 23 | `MIE-MI-431rv2_1.pdf` | Morley | unknown | `Morley`×18 | `ZXR50A/ZXR50P`×18 | pm |
| 24 | `00-3280-501-4009-05_r005_2x-a_series_installation_manual_es.pdf` | Aritech | 2X-A | `Aritech`×218 | `2X-A`×218 | — |

Lectura, sin sobre-interpretar (esto es una sonda de **consistencia**, no una adjudicación de identidad):

- **`manufacturer` cuadra en los 24.** Toda la divergencia está en `product_model`.
- **Segundo artefacto de parseo confirmado, misma clase que `VIA-28V`**: pares 12 y 15, `product_model = 'EN-54-25'` en los 12 chunks de `I56-4225-001 NRX-OPT Web`. **EN 54-25 es la NORMA** de componentes con enlace radio, no un modelo. Y el doc-level de ese mismo doc dice `B501RF`, que es la **base** común (§3.1), tampoco el detector.
- **A veces el valor bueno está en los chunks** (`DXc`, `VSN PLUS`, `ZXCE`, `MMX-10M`, `ZXR50A/ZXR50P`, `SP-20`, `TG-NOTIFIER` frente a `unknown` doc-level) **y a veces al revés** (`VIA-28V`, `EN-54-25`). Por eso el check es a los DOS niveles y no se puede automatizar con «copia el que no sea `unknown`».
- **La variante `-IS` de Argus vive SOLO a nivel chunk** (pares 7/10/11: doc dice `SG100`, chunks dicen `SG100-IS`). Un fix que «normalizara» el chunk al doc-level **borraría** la distinción intrínsecamente-segura vs estándar — justo el falso positivo de §3.1.
- **No verificado aquí**: si cada `product_model` de chunk está **respaldado por el texto** del doc. La sonda compara los dos niveles entre sí, no contra la fuente. Ese es el trabajo de identidad D1/D3, y para el par semilla se hizo a mano (§1.7).

---

## 4. Gaps y riesgos declarados

1. **El criterio literal del brief no funciona** (hallazgo de calibración). «≥60% de los chunks con Jaccard ≥ 0.85 contra algún chunk del otro» da 0.20/0.17 en el par semilla — no lo detecta, siendo un near-dup real. Causa medida: son re-extracciones distintas del mismo PDF (15 vs 18 chunks), el Jaccard chunk↔chunk se diluye por **desplazamiento de fronteras** y ruido OCR (`t4135oc` vs `t4135°c`), no por contenido; un shingle de 8 palabras muere con UNA palabra distinta. Por eso el census mide cobertura de **palabras** contra el documento entero. Solo 1 par del corpus pasa el criterio literal.
2. **Recall del blocking: sin cota dura.** No existe net barato con garantía frente a un criterio de cobertura de palabras. Se usa la unión de 4 nets; el margen del par semilla es amplio (N1 0.797 / N2 0.923 / N3 0.907 sobre floors 0.35 / 0.80 / 0.55). Clase que podría escapar: dos docs con el mismo contenido y divergencia OCR tan alta que ningún net pase el floor.
3. **Residual del discriminador de serie.** Un duplicado real cuyos dos docs tengan etiquetas de modelo distintas y no triviales cae en `KEEP-BOTH-SERIE` y se pierde. El par semilla se salva solo porque B tiene `pm='unknown'`; si hubiera heredado su `pm` de chunk (`VIA-28V`, el artefacto de parseo) lo habría clasificado hermana-de-serie.
4. **Fuga de satélites al marcar `duplicate_of` (encontrada de paso).** El RPC `match_chunks_v2_enunciados` (`migrations/012_enunciados_rpc_filters.sql`) **no filtra por el `duplicate_of` del padre**, así que el comentario de `retriever.py:1097` («el canal de enunciados sí filtra en SQL») es inexacto. Hoy es inerte: `chunks_v2_enunciados` tiene **0 filas** colgando de los 120 chunks propuestos (y 0 sobre una muestra de 300 chunks ya marcados) porque la tabla se pobló excluyendo duplicados (`scripts/enunciados_pass.py:107`). Eso es una propiedad del **poblado**, no del **servicio** → el paste lleva el guard 3g que ABORTA si alguna marca tuviera filas de enunciados. `hyq` sí tiene filas (320 sobre los chunks propuestos) pero está guardado client-side (`retriever.py:1095-1098`, fix s286) → no resucita contenido.
5. **Consistencia de cluster (bug cazado y arreglado durante el census).** Las decisiones por par no son globalmente consistentes: con >2 documentos near-dup encadenados salían CADENAS y hasta un CICLO (`MIE-MI-470`→`480`→`490`→`470`), y `NRX-OPT` aparecía como representante en un par y como suprimido en otro → 5 chunks habrían quedado a la vez marcados y canónicos, abortando el guard 3e. Lo detectó una **pre-validación read-only de los guards del paste contra la DB viva**, no una revisión a ojo. Arreglado: se elige UN representante por componente conexo y solo los pares que lo contienen conservan propuesta. Componentes afectados:
   - 3 docs → representante `MN-DT-951_v7.2` · 0 par(es) reorientado(s), 1 sin propuesta.
   - 3 docs → representante `MIE-MI-431rv2_1.pdf` · 0 par(es) reorientado(s), 1 sin propuesta.
   - 3 docs → representante `MIEMN570.pdf` · 0 par(es) reorientado(s), 1 sin propuesta.
   - 3 docs → representante `I56-4225-001 NRX-OPT Web` · 1 par(es) reorientado(s), 0 sin propuesta.
   - 3 docs → representante `MIE-MI-490.pdf` · 1 par(es) reorientado(s), 1 sin propuesta.
   El generador lleva ahora un `assert` que aborta si reaparecen chunk_ids repetidos o cadenas.
6. **Nada medido en pool/eval.** Este artefacto es un census + propuesta. El delta (probe de composición del pool de cat010 + sweep-39 de no-regresión) es el gate de la pieza y no se ha corrido aquí.
7. **`duplicate_of` no es reversible-gratis a nivel semántico**: el UPDATE sí es reversible (backup + rollback documentado), pero el chunk retirado deja de competir en TODOS los canales, no solo en el pool donde molestaba.

### 4.1 Gaps añadidos por la adjudicación del par semilla (s287)

8. **Los `md5` de las 10 filas nuevas se re-derivaron de la DB viva** (sonda 2026-07-30 posterior al census), no vienen del census. Control ejecutado: los **9 `md5` del par semilla en el sentido antiguo se re-verificaron contra la DB y cuadran los 9** → no hubo deriva entre el census (09:48) y la sonda, así que los md5 nuevos describen el mismo contenido que midió el census. Aun así el guard 3a queda algo más débil aquí: cubre la ventana sonda→paste, no census→paste.
9. **La contradicción de revisión NO la arregla el dedup.** Los 5 chunks `PARTIAL` de A sobreviven y uno de ellos (idx0) declara las directivas **derogadas** `94/9/EC`/`89/336/EEC` mientras B declara las vigentes `2014/34/EU`/`2014/30/EU`. El bot puede seguir citando la versión vieja. Arreglo estructural = linaje de revisión (`supersedes_id`/`superseded_by_id`, hoy `NULL` en ambos), no `duplicate_of`.
10. **El gate span-diff es ciego a la deriva de EDICIÓN.** Marca como TWIN chunks cuya única diferencia son tokens cortos y dispersos — «Issue F 06-08-15» vs «Issue H 03-01-2020», `94/9/EC` vs `2014/34/EU` — porque ninguna racha llega a 25 palabras. Es el comportamiento correcto para el objetivo (servir la issue nueva), pero significa que el texto de la revisión antigua **desaparece del pool** sin que ningún guard lo señale. Aquí es deseable; en un par donde el doc suprimido fuera el más nuevo, sería daño.
11. **El fix de metadata cambia la superficie de recuperación por `product_model`.** Los 18 chunks de B pasan de `VIA-28V` (inalcanzable) a `IS-mA1` → los filtros por modelo devuelven 33 chunks en vez de 15. Es el efecto buscado (findability de cat010), pero **no está medido**: entra en el mismo gate diferido que el resto (probe cat010 + sweep-39).
12. **17 de 24 representantes divergen `documents` ↔ `chunks_v2` en `product_model`** (§3.2), con al menos un segundo artefacto de parseo confirmado (`EN-54-25`). No se toca ninguno aquí: cada uno necesita su adjudicación (decisión 2 de §3).

---

## 5. Cómo aplicar

### 5.1 `v1.sql` — **YA APLICADO** ✅ *(queda como traza; no volver a pegarlo)*

Salieron **VIVAS** el **bloque 0** (metadata-fix del par semilla) + las **10 filas del PAR 1** +
**1 del PAR 2** + **1 del PAR 14** = **12 marcas**. Aplicado por Alberto y **verificado en vivo
read-only** (2026-07-30): 12/12 `duplicate_of` correctos, md5 sin deriva, canónicos válidos,
metadata-fix completo, `VIA-28V` corpus-wide = 0, las 4 tablas `_s287_*` pobladas (2 / 18 / 12 / 12).
**0 discrepancias.**
Rollback post-COMMIT (los `UPDATE` están al pie del `v1.sql`): `duplicate_of` desde
`_s287_dedup_backup`, y la metadata desde `_s287_metafix_backup_documents` /
`_s287_metafix_backup_chunks`.

### 5.2 `v2.sql` — **PENDIENTE de paste** (3 transacciones INDEPENDIENTES)

Se pueden pegar por separado y en cualquier orden; ninguno depende del otro.

| bloque | qué hace | dry-run esperado | rollback |
|---|---|---|---|
| **1** · par 4 | 5 marcas `duplicate_of` | `staged=5 · updated=5 · backed_up=5` | `_s287_dedup_backup_v2` |
| **2** · par 19 | `status='retired'` del doc ES/PT (26 chunks dejan de servirse) | 1 fila `retired`, el ES/EN sigue `active` | `_s287_retire_backup_documents_v2` |
| **3** · BLOQUE S A | linaje de #9 y #22, sin tocar `status` | 2 cadenas recíprocas · 4 docs siguen `active` | `_s287_lineage_backup_documents_v2` |

1. Pega el bloque con su `COMMIT` cambiado por `ROLLBACK` (dry-run): saltará cualquier guard.
2. Si cuadra, pégalo con `COMMIT`.
3. **Comentados a propósito, NO pegar sin decidir antes:** `3-bis` (`revision`/`revision_date` —
   cambia el texto de las citas) y `S.2` (des-enlace HP011 — +14 chunks servibles). Motivos en §7.3a/b.

> ⚠ **Los nombres de tabla del `v2.sql` llevan sufijo `_v2` a propósito.** El patrón
> `CREATE TABLE IF NOT EXISTS … AS SELECT` del `v1` haría **NO-OP** sobre las tablas ya pobladas →
> el `v2` correría **sin backup, en silencio**. El `v2` además añade un guard que **aborta** si el
> backup no tiene exactamente las filas esperadas (el `v1` solo lo reportaba al final).

Guards del paste: anti-deriva md5 por chunk · ninguno ya marcado · puntero canónico existente, no-duplicado y dentro del representante · el chunk marcado pertenece al doc suprimido · sin cadenas de duplicados · **re-verificación en SQL del invariante span-diff** · sin filas de enunciados colgando · `updated == staged` o aborta. *(El `v2` añade: backup completo · los dos docs del par activos · anti-huérfano para el retiro · `revision_lineage_id` sigue NULL para el linaje.)*

---

## 6. RECHAZADOS (10 pares) — ground truth de Alberto + por qué el census los emparejó

Los 10 salen del `.sql`. Para cada uno: el veredicto de Alberto, la verificación que hice contra la
DB/el corpus, y **la causa del falso positivo** — que en 9 de los 10 es **metadata de identidad rota**,
no un umbral mal puesto.

| # | par | ground truth (Alberto) | verificado contra la DB / la fuente | causa del falso positivo |
|---|---|---|---|---|
| 7 | SG100-IS vs SG100 | variantes intrínsecamente seguras = **productos distintos** | `documents.product_model` = `SG100` en **los DOS**; los chunks sí distinguen (`SG100-IS`×15 vs `SG100`×13) | doc-level **idéntico** → el discriminador de serie no puede disparar |
| 10 | SG200-IS vs SG200 | ídem | doc pm `SG200` en los dos; chunks `SG200-IS`×14 vs `SG200`×12 | ídem |
| 11 | SG350-IS vs SG350 | ídem | doc pm `SG350` en los dos; chunks `SG350-IS`×13 vs `SG350`×8 | ídem |
| 12 | NRX-OPT vs NRX Radio Thermals | detectores distintos (óptico vs térmico) | doc pm `B501RF` en los dos (= la **base** común); chunks `EN-54-25`×12 (¡norma!) vs `NRX-TFIX58`×12 | **los dos niveles rotos**: doc = base, chunk = norma |
| 13 | MIEMI130 vs MIEMI120rev05 | **VSN PLUS** vs **VSN 2-4** | doc pm `unknown` en los dos; chunks `VSN PLUS`×52 vs `VSN 2-4`×46; `revision` Rev 008 vs Rev 005 | doc-level `unknown` → sin discriminador |
| 15 | NRX-OPT vs NRX-SMT3 | óptico vs multicriterio | doc pm `B501RF` **y** chunk pm `EN-54-25` en **LOS DOS** | **el peor**: indistinguibles en ambos niveles, los dos valores son artefactos |
| 17 | MIE-MI-490 vs MIE-MI-480 | **MMX-10M** vs **MCX-55M** | doc pm `unknown` en los dos; chunks `MMX-10M`×6 vs `MCX-55M`×7 → **confirma el ground truth de Alberto** | doc-level `unknown` |
| 20 | MIE-MI-490 vs MIE-MI-470 | el 2º es **CMX-10RM** | chunks `MMX-10M`×6 vs `CMX-10RM`×6 → **confirma** | doc-level `unknown` |
| 21 | MNDT710_B vs MNDT720 | el 1º es **20/20U / 20/20UB** | doc pm `20/20U, 20/20UB` vs `20/20L, 20/20LB`; chunks `20/20UB`×47 vs `20/20LB`×41 → **confirma** | **aquí la metadata SÍ distinguía**: es KEEP-BOTH-SERIE que escapó (pm multi-modelo con comas) |
| 23 | MIE-MI-431 vs MIE-MI-450 | **MIE-MI-450 = IMPRESORA** de centrales ZXAE/ZXEE | portada al píxel: «MORLEY IAS FIRE SYSTEMS · **IMPRESORA DE LAZO PERIFÉRICO** · MOD.**EXP-060R** · MANUAL DE INSTALACIÓN». El otro es «ZXr-A / ZXr-P» | doc-level `unknown` en los dos |

**Lectura (mía, declarada como tal):** 9 de los 10 rechazos son consecuencia de que
`documents.product_model` **no identifica el producto** — o dice `unknown` (5 pares), o dice la
BASE/una norma en vez del detector (2 pares), o dice el modelo BASE compartido de una variante
(3 pares Argus). El único rechazo que NO es de metadata es el 21, y ése revela un hueco distinto:
el discriminador de serie no sabe leer un `product_model` multi-modelo separado por comas
(`'20/20U, 20/20UB'` vs `'20/20L, 20/20LB'` no intersectan como cadenas, así que no cuentan como
«hermanas de serie»). **Los dos huecos van al ticket A3 (§10); ninguno se toca aquí.**

**Lo que esto dice del instrumento** (para no repetirlo): el census ya protegía 141 pares como
`KEEP-BOTH-SERIE` gracias al `product_model`. Los 10 que se colaron son exactamente aquellos
**donde ese campo no sirve**. No es un umbral que haya que subir: es un campo que hay que poblar.

---

## 7. SUPERSEDED (pares 9 y 22) — clase NUEVA: revisión, no duplicado

### 7.1 La evidencia (sonda read-only de portadas, 2026-07-30)

| par | doc VIEJO | portada | doc NUEVO | portada |
|---|---|---|---|---|
| 9 | `MI-DT-951_V7.2` (681e506b) | «TG - **NOTIFIER** · MANUAL DE INTRODUCCIÓN · **MI-DT-951 (Rev.:7.2)** · Septiembre 2007» | `Tg-Honeywell_Introduccion` (a7bf5098) | «**Honeywell** · TG - HONEYWELL · MANUAL DE INTRODUCCIÓN · **MI-DT-951 (Rev.:7.4)** · Abril 2009» |
| 22 | `MN-DT-951_v7.2` (5e483105) | «TG - **NOTIFIER** · MANUAL DE USUARIO · **MN-DT-951 (Rev.:7.2)** · Septiembre 2007» | `TG-Honeywell_Usuario` (71654eda) | «TG - **HONEYWELL** · MANUAL DE USUARIO · **MN-DT-951 (Rev.:7.4)** · 06/04/2017» |

**Mismo número de documento, revisión mayor.** El «cross-brand» que el census marcó como sospechoso
es en realidad el **cambio de marca Notifier→Honeywell** entre revisiones. La adjudicación de Alberto
queda confirmada en la fuente, y es exactamente la clase que el **gap #9** de este packet declaró que
`duplicate_of` NO arregla.

**Contexto de familia (hallado de paso, read-only):** son TRES generaciones, no dos —
`MIDT951_v5-87` «MI-DT-951 (Rev:5.87) · Mayo 2005» (31 chunks) y `MNDT951_v5-87` «MN-DT-951 (Rev:5.87)
· Mayo 2005» (61 chunks) son la generación anterior; existe además `MP-DT-951_v7.2` «MP-DT-951
(Rev.:7.2) · Septiembre 2007» (manual de configuración, 89 chunks) **sin pareja 7.4 en estos 24 pares**.
Los 4 docs del bloque tienen hoy `status='active'`, `supersedes_id IS NULL`, `superseded_by_id IS NULL`:
**el linaje del corpus está sin poblar** (consistente con `supersedes 0/1065`, DECISIONS.md:909).

### 7.2 Dos cosas que encontré y que cambian la decisión

**(a) `status='superseded'` APAGA EL DOC ENTERO.** No es una etiqueta documental: `retrieve_chunks`
descarta todo chunk cuyo doc padre no esté `active` (`src/rag/retriever.py:1789-1794`, `:2802`).
Coste medido de apagar los dos viejos:

| par | chunks activos que dejan de servirse | % de sus palabras que SÍ están en la revisión nueva | clases del doc viejo |
|---|---|---|---|
| 9 | **16** | 75.4% | UNIQUE 5 · PARTIAL 6 · TWIN 4 · COVERED_NO_TWIN 1 |
| 22 | **38** | 66.0% | UNIQUE 14 · PARTIAL 16 · COVERED_NO_TWIN 8 · **TWIN 0** |

Es decir: **la 7.4 NO contiene todo lo que decía la 7.2**. Apagar las viejas retira contenido
servible que ninguna otra fuente cubre (19 chunks UNIQUE + 22 PARTIAL entre los dos).

**(b) HAY HUÉRFANOS — el patrón HP011, otra vez.** Otros chunks apuntan con `duplicate_of` a chunks
de los docs VIEJOS. Si el viejo se apaga, esos chunks siguen suprimidos **y su canónico deja de
servirse** → el contenido desaparece por completo:

- **Par 9** → 2 punteros entrantes, los dos desde `MIDT951_v5-87`.
- **Par 22** → 13 punteros entrantes: **10 desde el propio doc NUEVO** (`TG-Honeywell_Usuario`),
  2 desde `MNDT951_v5-87`, 1 interno.

Los 10 del doc nuevo son literalmente el defecto que la migración
`supabase/migrations/20260721190847_reconcile_hp011_v04_v07_lifecycle.sql` tuvo que reparar en HP011
(«38 v.07 chunks currently point at v.04 through duplicate_of […] those links make parts of the
authoritative revision unservable»). **Cualquier variante que apague el viejo DEBE des-enlazarlos.**

**(c) Las filas del census para estos 2 pares iban en la dirección CONTRARIA** (retiraban chunks del
doc NUEVO, no del viejo): el desempate por recencia usaba `revision`/`revision_date`/`ingested_at`,
todos `NULL` aquí, así que eligió al revés. **Se caen del `.sql`.**

### 7.3 Las tres variantes del BLOQUE S — **ADJUDICADO POR ALBERTO (s287): VARIANTE A**

> **Veredicto final: variante A — «linaje sin apagar nada».** Implementada en el
> **BLOQUE 3 del `v2.sql`**. B y C quedan descartadas para esta pieza (B es una decisión de
> producto sin medir; C requiere des-enlazar un puntero invertido). El des-enlace de punteros
> que el bloque traía dentro de B sale **COMENTADO** en el `v2.sql` como **S.2** — ver 7.3b.

| | qué hace | efecto en runtime | pérdida de contenido | huérfanos |
|---|---|---|---|---|
| **A** ✅ **adjudicada** | `supersedes_id` / `superseded_by_id`, **sin tocar `status`** | **CERO** (demostrado — ver 7.3a: el motivo NO es el que yo había escrito) | ninguna | ninguno |
| **B** | A + `status='superseded'` en los dos viejos + reparación de huérfanos | apaga 54 chunks activos | 19 UNIQUE + 22 PARTIAL | los 14 externos hay que des-enlazarlos |
| **C** | A + `duplicate_of` de lo que la 7.4 SÍ contiene | retira 4 chunks (par 9); **0 en el par 22** | ninguna (gate span-diff) | requiere des-enlazar 1 puntero invertido |

**Por qué A primero y no B:** A registra tu ground-truth de forma duradera y reversible sin perder
un chunk, y deja la política de «servir solo la última revisión» para cuando se decida **con la
medida delante** (probe de pool + sweep-39). Es el mismo orden que siguió el repo en s64/DEC-045:
poblar el linaje primero, consumirlo después. B es una decisión de PRODUCTO («la 7.2 no debe
servirse aunque tenga contenido propio») — no la tomo yo.

**Por qué C es interesante y a la vez es la prueba de que el dedup no era el mecanismo:** en el
par 22 el doc viejo **no tiene ni un chunk TWIN** contra el nuevo (el manual de usuario se reescribió
entre 2007 y 2017). Un instrumento de dedup no puede hacer nada ahí. En el par 9 sí hay 4 TWIN, con
guards re-pre-validados en vivo (filas listas en el BLOQUE S).

#### 7.3a CORRECCIÓN: el efecto-cero de A es CIERTO, pero el motivo que di era FALSO

Escribí que «`supersedes_id` y `superseded_by_id` no los lee ningún path de retrieval (solo
aparecen en migraciones y en el contrato de DOCUMENT_MANAGEMENT)». **Es falso**, verificado en el
código: `src/rag/document_local_coverage.py` los lee en runtime — `_component()` (`:258`) camina el
grafo de revisiones por esos dos campos, y `resolve_authoritative_documents()` (`:283-287`,
`:340-346`, `:356-362`) valida con ellos reciprocidad, raíz única y cadena acíclica.

**El efecto-cero se sostiene por otra razón, más fuerte — la HIDRATACIÓN.** El CTE `family_rows`
del RPC que alimenta ese resolver selecciona candidatos por
`candidate.revision_lineage_id = seed.revision_lineage_id`, gateado por
`seed.revision_lineage_id IS NOT NULL AND seed.lineage_authority_status = 'verified'`
(`supabase/migrations/20260722013000_s277_document_revision_lineage_snapshot_v2.sql:294-297`).
Los 4 docs del BLOQUE S tienen **`revision_lineage_id = NULL`** (verificado en vivo; en TODO el
corpus solo **9 de 1169** documents tienen lineage_id — los de HP011 RP1r y CAD-250). La variante A
**no toca `revision_lineage_id`** → esos 4 docs no entran nunca en `document_rows` → el resolver no
los ve. **Efecto cero, ahora demostrado.** El `v2.sql` lleva un guard que ABORTA si alguno de los 4
tuviera ya `revision_lineage_id`, porque en ese caso A dejaría de ser efecto-cero.

**Consecuencia que hay que dejar escrita:** A deja el linaje **a medias a propósito**. Si alguien
puebla después `revision_lineage_id` de estos 4 docs **sin** poner `status='superseded'` en los dos
viejos, `resolve_authoritative_documents` rechazará el componente con `invalid_revision_status`
(`:325-335` exige que todo miembro no-activo sea `superseded`) o `ambiguous_active_revision`
(`:322-324` exige exactamente UN activo por linaje). Es decir: **poblar el lineage_id de estos docs
obliga a tomar antes la decisión de la variante B.** No se puede avanzar «solo un poco» sin medirlo.

**Y `revision`/`revision_date` tampoco es efecto-cero** (yo lo había puesto como «opcional dentro de
A, recomendado»): `_filter_by_document_status` enriquece cada chunk superviviente con
`document_revision`/`document_revision_date` (`retriever.py:2805-2806`) y el generador los **lee para
construir la cita** (`generator.py:705-706`, `answer_planner.py:1585`). Poblarlos cambiaría el texto
de las citas de los 209 chunks de estos 4 docs → sale **COMENTADO** en el `v2.sql` (bloque 3-bis).

#### 7.3b Por qué el des-enlace de huérfanos (S.2) sale COMENTADO, no activo

El des-enlace vivía **dentro de la variante B**, donde es obligatorio (allí los viejos se apagan y
sus canónicos dejan de servirse). Bajo la variante A **no hay ni un huérfano que reparar**: no se
apaga nada, así que todos los canónicos apuntados se siguen sirviendo. Tres motivos, con la medida:

1. **A no crea huérfanos.** El defecto que el des-enlace atacaría es **preexistente**, no causado
   por este paste.
2. **Activarlo rompería el efecto-cero en el que se apoya la adjudicación.** Medido en vivo: el
   des-enlace tal y como estaba escrito tocaría **14 chunks** que pasarían de suprimidos a
   **servibles** — 10 desde `71654eda` (la revisión NUEVA), 2 desde `MIDT951_v5-87`, 2 desde
   `MNDT951_v5-87`. +14 chunks en el pool es un cambio de composición **sin medir**, justo lo que A
   existe para evitar.
3. **La topología real es peor de lo que asumí** (hallazgo nuevo de la sonda de pre-validación):
   los punteros entre el VIEJO y el NUEVO del par 22 son **BIDIRECCIONALES** — 10 chunks de
   `71654eda` → `5e483105` **y** 10 de `5e483105` → `71654eda` — y **ya existe una cadena
   `duplicate_of` en la DB**: `ad5be716 → 01bbb4c0 → b5d4a97b` (`01bbb4c0` está marcado y a la vez
   es canónico de otro, exactamente lo que el guard 3e prohíbe crear). Un des-enlace en **una** sola
   dirección arregla la mitad del enredo y deja la otra, sin que ningún guard lo señale.
   Desenredarlo es su propia adjudicación (¿cuál revisión es la canónica para CADA par de gemelos?),
   no un efecto colateral de poblar dos FK. → **ticket A3**.

**Gaps declarados del BLOQUE S:** (1) ninguna variante está medida en pool/eval — A tiene
efecto-cero por construcción y no necesita gate; B y C sí; (2) el linaje de la familia queda a
medias (v5.87 y MP-DT-951 sin cadena, no adjudicados → A3); (3) `document_family` es el filename en
los 4 docs, así que la familia no agrupa las revisiones (defecto filename-naive ya conocido,
DECISIONS.md:909) — el linaje por FK funciona igual, pero un consumo futuro por familia no lo vería.

---

## 8. PREGUNTAS ABIERTAS — **ADJUDICADAS (Alberto, s287). Ninguna queda abierta.**

Siete pares. Para cada uno: lo que preguntaste, lo que dice la fuente, qué propuse, y **el veredicto
final de Alberto**.

| § | par | mi propuesta | **VEREDICTO FINAL (Alberto)** | dónde acaba |
|---|---|---|---|---|
| 8.1 | 3 · `FS2-1` vs `ms1-2-4` | RECHAZAR (rebadge OEM) | **RECHAZAR** — acepta la propuesta | fuera de los pastes |
| 8.2 | 4 · `MNDT1026` vs `MNDT1025` | aprobable, riesgo bajo; «yo no lo forzaría» | **APROBAR** — *ganancia marginal aceptada, con el residual `FSL-751E` delante* | `v2.sql` BLOQUE 1 · 5 marcas |
| 8.3 | 5 · `FS8` vs `MS8` | no aprobar tal cual; antes el seam D1/D3 | **ESPERAR** — acepta el orden propuesto | fuera de los pastes |
| 8.4 | 6 · `D 1148-1 BRS` vs `D 1147-1 BRH` | RECHAZAR (keep-both) | **RECHAZAR** — acepta la propuesta | fuera de los pastes |
| 8.5 | 16 · `MIE-MP-210` vs `MIE-MI-220` | RECHAZAR (keep-both) | **RECHAZAR** — acepta la propuesta | fuera de los pastes |
| 8.6 | 18 · `MNDT626` vs `MNDT625` | RECHAZAR (tóxico≠explosivo) | **RECHAZAR** — acepta la propuesta | fuera de los pastes |
| 8.7 | 19 · `MNDT516` ES/EN vs ES/PT | *alternativa*: marcar solo las 11 TWIN | **RETIRAR EL ES/PT** — mantiene **su** propuesta original; mi alternativa queda descartada | `v2.sql` BLOQUE 2 · `status='retired'` |

**Lectura del tally (anti-ritual):** de 7 propuestas mías, Alberto confirmó 5, **anuló 1** (8.7: eligió
su retiro completo frente a mi alternativa «sin pérdida») y **subió 1 de tibia a sí** (8.2: yo decía
«no lo forzaría», él aprueba asumiendo el residual). No es un «siempre alineado».

### 8.1 PAR 3 · `FS2-1` (Notifier) vs `ms1-2-4.pdf` (Morley) — «¿no son muy similares?»

> **VEREDICTO FINAL (Alberto, s287): RECHAZAR.** Confirma la propuesta. Sin filas en ningún paste.

**Sí, muchísimo: son el MISMO manual rebadgeado — y por eso justamente NO hay que deduplicarlos.**

- Misma obra: los dos se titulan «CENTRALES DE INCENDIOS CONVENCIONALES DE 1, 2 Y 4 ZONAS · MANUAL DE
  FUNCIONAMIENTO, INSTALACION Y PUESTA EN MARCHA · Y FORMULARIO DE REGISTRO LOCAL», mismas 24 páginas.
- Marca: `FS2-1` imprime «NOTIFIER ESPAÑA, S.L. · Avda Conflent 84…» en portada; `ms1-2-4` imprime
  «Ref. 997-158 Versión 1.0 · 9 Enero 2002» y **no imprime marca**.
- **Los modelos están sustituidos sistemáticamente**: `FS-1/FS-2/FS-4` (30 menciones) vs
  `MS-1/MS-2/MS-4` (29 menciones).

**La prueba que decide** — comprobé los 7 chunks TWIN más sustantivos que se proponía retirar:

| chunk de `ms1-2-4` (se retiraría) | modelos que nombra | su gemelo en `FS2-1` | modelos que nombra |
|---|---|---|---|
| Limitaciones del Sistema | MS-1, MS-2, MS-4 | `3a16fb38` | FS-1, FS-2, FS-4 |
| Pruebas Rutinarias | MS-1, MS-2, MS-4 | `b8bc8a99` | FS-1, FS-2, FS-4 |
| Instrucciones de Funcionamiento | MS-1, MS-2, MS-4 | `8f2d1255` | FS-1, FS-2, FS-4 |
| Condición de Fallo (×2) | MS-1, MS-2, MS-4 | `bae2998e`, `d0496d31` | FS-1, FS-2, FS-4 |
| Instalación | MS-1, MS-2, MS-4 | `57c01d50` | FS-1, FS-2, FS-4 |
| Puesta en Marcha | MS-1, MS-2, MS-4 | `e872a4f9` | FS-1, FS-2, FS-4 |

**PROPUESTA: RECHAZAR (keep-both, clase rebadge OEM).** Deduplicar haría que una pregunta sobre la
**MS-2** se respondiera citando el manual de la **FS-2** — el daño exacto de DEC-091b, y la
distinción que tú mismo adjudicaste en s78/s80 (RP1r-Supra=Notifier vs VSN-RP1r=Morley). El census ya
aparta 38 rebadges como `KEEP-BOTH-BRAND`; éste se coló porque su detector exige que **las dos**
marcas estén impresas, y `ms1-2-4` no imprime ninguna.
**A3:** `ms1-2-4.pdf` tiene `documents.product_model = 'unknown'` (sus chunks dicen `MS-1/MS-2/MS-4`).

### 8.2 PAR 4 · `MNDT1026` vs `MNDT1025` — ¿1026 más completo? ¿1025 tiene algo único?

> **VEREDICTO FINAL (Alberto, s287): APROBAR**, con la ganancia marginal aceptada explícitamente y
> el residual `FSL-751E` delante. Va al **BLOQUE 1 del `v2.sql`** (5 marcas, representante MNDT1026).
> Guards pre-validados en vivo read-only: **8/8, 0 fallos**. Residual re-medido en vivo: `FSL-751E`
> existe corpus-wide **solo** en `MNDT1025` (23 chunks, los 23 activos) → marcar 5 baja su alcance
> activo de **23 a 18**.

**Sí a lo primero; a lo segundo, nada que sea un HECHO.**

- `MNDT1026` = «Detector de humo analógico con cámara láser VIEW — **Aplicaciones del VIEW™ con la
  central AFP-300/400**» · **MN-DT-1026_A · 24 MARZO 2004**.
- `MNDT1025` = «Detector de humo analógico con cámara láser VIEW — **Aplicaciones del VIEW™**»
  (genérico) · **MN-DT-1025 · 8 ABRIL 2004 · (doc. 997-198)**.
- **No son revisiones**: son dos documentos con número propio; el genérico es incluso 15 días
  POSTERIOR. `1026` es la edición específica para la central AFP-300/400.

**Completitud (span-diff del census + índice de secciones):** `1026` tiene 30 chunks / 7.592 palabras
vs 23 / 5.728 de `1025`, y **secciones propias que `1025` no tiene**: *Cableado*, *Programación de la
cooperación entre detectores*, *Autoaprendizaje del nivel de prealarma*, *Algoritmos de filtrado*
(18 spans únicos, 2.198 palabras). En sentido contrario, `1025` tiene 8 spans únicos / 412 palabras;
los revisé uno a uno: **(a)** una tabla ASCII de direccionamiento del sensor (prosa de figura),
**(b)** un diagrama `mermaid` de la AFP-400 con sensores VIEW (prosa de figura), **(c)** el arranque
de «19 Extinción» — y verifiqué que **«extinción» también está en `1026`**. Ningún hecho exclusivo.

**PROPUESTA: aprobable con riesgo bajo** (mismo producto, mismo fabricante, mismo texto en los 5
chunks marcados; los otros 18 de `1025` siguen sirviéndose). **Residual declarado, para que decidas
con él delante:** `1025` etiqueta sus chunks `product_model='FSL-751E'` y `1026` `='VIEW'` —
son el mismo producto con dos nombres, así que retirar 5 chunks reduce el alcance de la etiqueta
`FSL-751E`. La alternativa de coste cero es **keep-both**: son 5 chunks redundantes, no molestan a
nadie hoy. Yo no forzaría este par: la ganancia es marginal y la unificación `FSL-751E`↔`VIEW` (A3)
es el arreglo que de verdad paga.

### 8.3 PAR 5 · `FS8` (Notifier) vs `MS8.pdf` (Morley) — «exactamente el mismo documento»

> **VEREDICTO FINAL (Alberto, s287): ESPERAR.** Acepta el orden propuesto — primero el seam de
> identidad (D1/D3: que una obra pueda declarar dos marcas), después el dedup. Sin filas hoy.

**CONFIRMADO: es el mismo documento.** Portadas idénticas:

> «Panel de control de incendios de 8 zonas **EFS/EM 8** · Manual de instalación, puesta en marcha y
> funcionamiento · **997-201-103** · **Edición 1, Septiembre 1999**»

- Mismo nº de chunks activos (63), mismas 50 páginas, mismo `product_model` de chunk (`EFS/EM 8` en
  los dos), misma mezcla de idioma (62 es + 1 en en ambos).
- **Ninguno de los dos imprime «Notifier» NI «Morley» en su texto** (0 ocurrencias en ambos): la
  atribución de marca es **solo metadata**.
- **¿Re-subidas byte-idénticas?** No se puede afirmar: `FS8` tiene `source_pdf_sha256` =
  `backfill:0c4f0df…` (marcador de backfill, nunca re-hasheado) y `MS8` uno real (`c8429ebf…`).
  **El sha no es comparable aquí** — lo declaro en vez de inventar una conclusión.
- Los spans «UNIQUE» de los dos lados son **la misma sección extraída dos veces** (son best-twin
  mutuos: `Esquema de cableado típico`, `Programación sirenas`, `7.2 Selección de modos`). Verifiqué
  además que las secciones `8.7.1` y `3.4.4` — cada una «única» de un lado — **existen en los dos**.
  La divergencia es prosa de figura del extractor, no contenido.

**PROPUESTA: NO aprobar tal cual, aunque sea un duplicado real.** El manual es de **marca DUAL**
(«EFS/EM»: EFS = línea Notifier, EM = línea Morley), y hoy las dos copias son el único mecanismo por
el que el corpus alcanza esa obra bajo las dos marcas — `match_chunks_v2(filter_manufacturer)`
compara `c.manufacturer` (`supabase_schema.sql:81`). Retirar 30 de los 63 chunks etiquetados
`Morley` degrada el alcance por marca **sin que ningún guard lo señale**. Orden correcto:
**primero el seam de identidad (D1/D3: que una obra pueda declarar dos marcas), después el dedup.**
Si aun así lo quieres ya, el representante por tu política nueva sería `FS8` (su metadata es la única
auto-soportada, 1/3 vs 0/3, y su `product_model` doc-level ya dice `EFS/EM 8` mientras `MS8` dice
`unknown`) — pero entonces hay que aceptar la degradación de alcance Morley, declarada aquí.

### 8.4 PAR 6 · `D 1148-1 BRS` vs `D 1147-1 BRH` — «exactamente el mismo documento»

> **VEREDICTO FINAL (Alberto, s287): RECHAZAR.** Confirma la propuesta. Sin filas en ningún paste.

**NO se confirma: son datasheets de productos DISTINTOS.**

| | `D 1148-1 BRS` (representante) | `D 1147-1 BRH` (se retiraría) |
|---|---|---|
| `product_model` de chunk | **SP-20** | **NFXI-BSF-WCH** |
| I(max) @24V | 25 mA (standard) / 14 mA (legacy) | **32 mA (high)** / 24 mA / 13 mA |
| P(max) | 590 / 330 mW | **760 / 580 / 320 mW** |
| doc de aislante que referencia | **SP20-3249** | **SP20-3248** |

**Y el chunk grande que se proponía retirar es la TABLA DE TONOS** (1.197 palabras): la del BRH se
titula «Table 1 (Tone selection) — **Default Setting (C-3-15)**» y la del BRS «Table 1 — VERSION 1».
La cadena **`C-3-15` aparece 3× en el BRH y 0× en el BRS**: retirar ese chunk **borra el ajuste por
defecto del BRH del corpus**. Es el gap #10 de este packet mordiendo (el gate span-diff es ciego a
diferencias cortas y dispersas: 0.946 de cobertura, ninguna racha ≥25 palabras).

**PROPUESTA: RECHAZAR (keep-both).** Mismo patrón que los rechazos §6.
**A3:** los dos docs llevan `documents.product_model='B501AP'` (la base común, no la sirena).

### 8.5 PAR 16 · `MIE-MP-210` vs `MIE-MI-220` — «analiza y propone»

> **VEREDICTO FINAL (Alberto, s287): RECHAZAR.** Confirma la propuesta. Sin filas en ningún paste.

- `MIE-MP-210.pdf` = **manual de la central ZXCE** («DOC.MIE-MP-210/Vers.1.48, Rev.003 · MAYO 2002 ·
  MORLEY-IAS · CENTRAL DE CONTROL DE INCENDIOS ZXCE · MANUAL DE INSTALACIÓN, PROGRAMACIÓN Y
  FUNCIONAMIENTO») — 104 chunks, 77 páginas.
- `MIE-MI-220.pdf` = **«TARJETA DE 20 RELÉS (NC/NO) · MOD.REL-2000 · SISTEMA ECO-2000 · MANUAL DE
  INSTALACIÓN»** — 11 chunks, 8 páginas.
- Productos distintos y hasta **sistemas** distintos (ECO-2000 vs ZXCE), aunque el propio manual del
  REL-2000 remite a la placa base de la ZXCE (comparten plataforma).
- La asimetría lo dice todo: el módulo está cubierto al **68.9%** por el manual de la central, y la
  central al **7.2%** por el módulo. Los **2 chunks** que se proponía retirar son «ECUACIONES DE
  ACTIVACIÓN DE LOS RELÉS (EXPRESIONES)» y «EJEMPLOS PRÁCTICOS DE PROGRAMACIÓN DE RELÉS»: el lenguaje
  de expresiones del PANEL, que sí es literalmente el mismo.

**PROPUESTA: RECHAZAR (keep-both).** Ganancia = 2 chunks. Riesgo = concreto: los chunks del módulo
llevan `product_model='REL-2000'` y los de la central `='ZXCE'`, así que una consulta de REL-2000
filtrada por modelo perdería esos 2 chunks **y su gemelo no la sustituiría** (no matchea el modelo).
Es alcance perdido a cambio de casi nada.
**A3:** los dos docs tienen `documents.product_model='unknown'`.

### 8.6 PAR 18 · `MNDT626` vs `MNDT625` — «mismo modelo, manuales ligeramente distintos, ¿revisiones?»

> **VEREDICTO FINAL (Alberto, s287): RECHAZAR.** Confirma la propuesta. Sin filas en ningún paste.

**NO son revisiones: son las ediciones de GAS TÓXICO y GAS EXPLOSIVO del mismo manual.** Portadas:

| | `MNDT626` (representante) | `MNDT625` (se retiraría) |
|---|---|---|
| título | «DETECTORES PARA GAS **TÓXICO** · SMART 3 CC-CD (ST/x) · Manual de Usuario» | «DETECTORES PARA GAS **EXPLOSIVO** · SMART 3 CC-CD (ST/x)» |
| referencia | **MN-DT-626_F · 7 OCTUBRE 2009 · (MTX2081, rev. 5)** | **MN-DT-625_E · 12 JUNIO 2009** |
| `documents.revision` | `Rev 5` | `Rev 1` |

Miré el pie/portada como en el par semilla: los números de documento son **distintos** (626 vs 625),
no dos issues del mismo. El `Rev 5` / `Rev 1` de `documents` es la revisión interna de cada uno.

**PROPUESTA: RECHAZAR (keep-both).** Tóxico y explosivo son productos distintos con escalas distintas
(ppm vs %LIE) y gases de calibración distintos; que el bot mezcle las dos ediciones en una respuesta
no es redundancia, es un riesgo de seguridad. Los dos docs comparten `product_model='SMART 3'` en
ambos niveles — **por eso el census no pudo separarlos** (misma causa que §6). A3: refinar el modelo
a la variante (tóxico/explosivo) o al menos anotar la distinción.

### 8.7 PAR 19 · `MNDT516` (ES/EN) vs `MNDT516_PL4_ESP-PORT` (ES/PT) — tu propuesta: retirar el ES/PT

> **VEREDICTO FINAL (Alberto, s287): RETIRAR EL ES/PT, quedándose el ES/EN.** Mantiene **su**
> propuesta original; **mi alternativa** («marcar solo las 11 filas TWIN, cero excepción de
> política, cero pérdida») queda **DESCARTADA** y sus 11 filas **no** se aplican.
> Implementado en el **BLOQUE 2 del `v2.sql`** con `status='retired'` (el mecanismo que yo señalaba
> como el semánticamente correcto; ver más abajo). **La objeción (2) sigue en pie y queda escrita:
> esto es una EXCEPCIÓN declarada a KEEP-BOTH-LANG, no su aplicación.**

#### Verificación chunk a chunk que exigía el retiro doc-level *(read-only en vivo, 2026-07-30)*

Un retiro a nivel documento apaga **los 26 chunks**, no solo los 11 TWIN — así que antes de
escribirlo re-verifiqué que ninguno de los 26 lleva un hecho exclusivo. Método: span-diff de cada
chunk del ES/PT contra el **texto completo** del ES/EN (shingles de 8 palabras sobre `norm_ocr`,
rachas no cubiertas ≥ 25 palabras), clasificación PT/ES de cada racha, y prueba de **presencia del
hecho** en el ES/EN para cada racha en español.

| resultado | n |
|---|---|
| chunks TWIN (cov ≥ 0.92, ninguna racha ≥ 25w) | **11** (6 con Jaccard 1.000) |
| chunks con ≥ 1 racha no cubierta | 15 |
| … cuyas rachas son **traducción portuguesa** | idx 0, 13, 18, 20, 23 |
| … cuyas rachas son **prosa de figura** del extractor (inglés, entre corchetes) | idx 3, 10, 11 |
| … con racha en **español** → probadas token a token | idx 4, 6, 7, 8, 13, 20, 24 |
| **tokens técnicos probados contra el ES/EN** | **55** · **52 presentes** |

Los 3 «ausentes» se resuelven y **ninguno es un hecho exclusivo** — esto es lo que autoriza el
retiro doc-level (si uno solo lo hubiera sido, el BLOQUE 2 saldría comentado):

1. **`max. 2A`** → el ES/EN tiene la **misma etiqueta de figura** con otra puntuación:
   «`- Aux voltage output 1 (24Vdc) (max 2)`». Mismo dato, extracción distinta.
2. **`230V`** → el ES/EN da la especificación real, **y es más completa**:
   «Tensión de alimentación: 220VcA +/- 10%», «Power supply: 100-240 Vac»,
   «3.1 Alimentación principal (220Vca)», «(AC) 220 VAC operation». 220 V ±10% y 100-240 Vac
   **cubren** 230 V; el `230V` del ES/PT está en prosa de figura, no en la tabla de specs.
3. **`15/06/2017`** → fecha de pie de página, no un hecho técnico. **Corrige a este mismo packet**
   (abajo decía que los dos pies eran idénticos): **no lo son** — ES/EN dice **13/06/2017** y ES/PT
   **15/06/2017**. Dos ediciones del mismo documento con dos días de diferencia; no cambia nada.

Verificados **presentes** en el ES/EN, uno a uno: `CN7` · `CN10` · `CN12` · `CN16A` · `CN16B` ·
`CN17` · `JP1..JP4` · `Jp20..Jp23` · `RL1` · `J1..J4` · `NC1` · `NA1` · `NC4` · «Avería (FLT)» ·
`(AL1)(AL2)(AL3)(AUX)(BATT)` · «Normalmente abierto/cerrado» · «NORMALMENTE ACTIVADOS» ·
«Módulo de ampliación» · «Microinterruptores» · `SMART3` · «CABLE APANTALLADO» · «3 X 0,75» ·
«TERMINALES DE LA CENTRAL» · `PL4+` · «MENU PI4» · «VERS. 3.04» · «Funcionamiento con batería».
El diagrama «CONEXIÓN DE DETECTORES DE LA SERIE SMART3 A LA CENTRAL PL4+» (idx11, el único
candidato a hecho exclusivo que yo había señalado) **existe en el ES/EN** (idx21 e idx40).

**Conclusión: 0 hechos exclusivos.** Lo que se pierde con el retiro es la **traducción portuguesa**
— exactamente lo que Alberto adjudicó retirar. *Alcance de la prueba, declarado:* es por tokens
técnicos sobre las rachas no cubiertas, no una lectura íntegra de las 34 páginas: es fuerte, no
exhaustiva.

**Seguridad del retiro (todo verificado a cero en vivo):** 0 punteros `duplicate_of` entrantes hacia
los 26 chunks (no crea huérfanos) · 0 de los 26 ya marcado · 0 filas de `chunks_v2_enunciados`
colgando · las **56 filas `chunks_v2_hyq`** que sí cuelgan **no filtran**: los surrogates hyq se
hidratan con `_HYDRATE_SELECT` (incluye `document_id`, `retriever.py:1263-1265`) y pasan **después**
por el filtro de lifecycle del Step 4b (`retriever.py:1789-1793`) → un doc `retired` no puede
resucitar por ese canal. Verificado en el código, no asumido.

---

*Análisis original (previo a la adjudicación), que se mantiene como traza:*

**Tu premisa se sostiene: la parte ES es la misma y el PT no aporta ningún hecho exclusivo.**

- **Es el MISMO manual**: los dos llevan el pie «**MN-DT-516.doc (MT3910.doc) · N de 34**»
  y el mismo producto (`PL4`). No son revisiones distintas: **mismo documento** (fechas de pie
  13/06/2017 en el ES/EN y 15/06/2017 en el ES/PT — ver corrección arriba), dos
  ediciones bilingües (ES/EN y ES/PT).
- **El ES es idéntico**: 11 chunks TWIN, **6 de ellos con Jaccard = 1.000** (`1 INTRODUCCIÓN`,
  `2.5 Prueba automática`, `4.3 Configuración`, `4.4 Central en alarma`, `4.5 Central en avería`,
  `4.6 Deshabilitar la central`…).
- **Lo «único» del ES/PT**, revisado span a span: **(a)** la traducción **portuguesa**
  («alarme por saturação», «manual de utilizador e instalação», «placa base montada na parte
  posterior…»), **(b)** prosa de figura distinta, y **(c)** el interleaving ES/PT que rompe los
  shingles. El único candidato a hecho exclusivo era el diagrama «CONEXIÓN DE DETECTORES DE LA SERIE
  SMART3 A LA CENTRAL PL4+» — **verificado: existe también en el ES/EN** (con «TERMINALES DE
  DETECTORES DE GAS SMART3»). **No hay pérdida factual.**

**PROPUESTA (con dos objeciones declaradas):**

1. **El mecanismo NO debería ser `superseded`**: no hay revisión nueva (misma fecha, mismo documento).
   Lo honesto es **`status='retired'`** — el filtro de lifecycle trata igual a los dos
   (`retriever.py:541-549`), pero la semántica queda bien registrada para el futuro.
2. **Choca con una política del propio census**: `KEEP-BOTH-LANG` (11 pares) dice «idiomas distintos →
   variante de mercado, **NUNCA** suprimir», y es la política que protege los 41 grupos ES/EN
   legítimos del corpus (DECISIONS.md:909, hp011). Retirar el ES/PT es una **excepción** a esa
   política, no su aplicación. Se puede defender (el PT no tiene audiencia en Fontiber hoy y el
   `status` es reversible en una línea) pero **debe declararse como excepción**, no colarse.

**Alternativa MÁS BARATA y sin pérdida, que recomendaba primero:** aprobar **las 11 filas TWIN** que
ya están en el `v1.sql` (comentadas). Retira solo el **ES duplicado** y deja el PT servible: cero
excepción de política, cero contenido perdido, y el 100% del ahorro real (el ES es lo único que
compite en el pool, porque las consultas van en español).
→ **DESCARTADA por Alberto (s287):** eligió el retiro completo. Las 11 filas se quedan comentadas en
el `v1.sql` y **no** se trasladan al `v2.sql`. La objeción (1) sí se recogió — el mecanismo aplicado
es `status='retired'`, no `superseded`. La objeción (2) queda como **excepción declarada**.

El bloque de abajo es el que se ha llevado al **BLOQUE 2 del `v2.sql`** (allí, con backup, guards
ampliados y post-check). Aquí queda como traza del diseño original.
Comprobado antes de escribirlo: **0 punteros `duplicate_of` entrantes** hacia sus 26 chunks (no crea
huérfanos) y **0 chunks suyos ya marcados**.

```sql
-- RETIRO del doc ES/PT (PAR 19) — COMENTADO, requiere OK explícito de Alberto.
-- Semántica elegida: 'retired' (NO 'superseded': no hay revisión nueva — mismo MN-DT-516.doc
-- 15/06/2017 en los dos). Excepción declarada a la política KEEP-BOTH-LANG del census.
-- BEGIN;
-- SET LOCAL lock_timeout = '5s';
-- SET LOCAL statement_timeout = '30s';
-- CREATE TABLE IF NOT EXISTS _s287_retire_backup_documents AS
-- SELECT id, status, notes, now() AS backed_at FROM documents
--  WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
-- DO $$
-- DECLARE m int;
-- BEGIN
--   SELECT count(*) INTO m FROM documents
--    WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND status = 'active'
--      AND source_pdf_filename = 'MNDT516_PL4_ESP-PORT' AND product_model = 'PL4';
--   IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el doc ES/PT no está en el pre-estado — ABORTA'; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
--   IF m <> 26 THEN RAISE EXCEPTION 'PAR19: % chunks, la sonda vio 26 — ABORTA', m; END IF;
--   -- el doc ES/EN que se queda debe seguir vivo y completo
--   SELECT count(*) INTO m FROM documents
--    WHERE id = '06887ff1-3783-4c29-9f4b-0012facfebb1' AND status = 'active';
--   IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el doc ES/EN no está activo — ABORTA'; END IF;
--   -- NADIE puede depender de los chunks que se apagan (guard anti-huérfano, patrón HP011)
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    WHERE t.document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
--   IF m > 0 THEN RAISE EXCEPTION 'PAR19: % chunks quedarían huérfanos — trátalos antes', m; END IF;
-- END $$;
-- UPDATE documents SET status = 'retired'
--  WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND status = 'active';
-- COMMIT;   -- dry-run: ROLLBACK
-- ROLLBACK post-COMMIT:
--   UPDATE documents d SET status = b.status FROM _s287_retire_backup_documents b WHERE d.id = b.id;
```

**A3 del par 19:** `documents.language` es `NULL` en los dos docs, y el detector de idioma etiquetó
los chunks portugueses como `es` (23 `es` + 3 `en`, **0 `pt`**) — el corpus no sabe hoy que tiene
portugués.

---

## 9. KEEP-BOTH por `doc_type` (pares 8 y 24) — verificado, no hay fix que proponer

Alberto: *keep-both, sin marcas; si su `doc_type` está NULL o mal, proponer fix.* **Sonda read-only
2026-07-30 contra `documents`:**

| # | doc | `doc_type` | ¿correcto? |
|---|---|---|---|
| 8 | `MNDT1070` (LTS-240) | `guia_usuario` | ✅ es el manual de usuario |
| 8 | `MFDT1070` (LTS-240) | `operacion` | ✅ es el de funcionamiento |
| 24 | `00-3280-501-…_2x-a_series_installation_manual_es` | `instalacion` | ✅ |
| 24 | `00-3280-505-…_2x-a_series_operation_manual_es` | `operacion` | ✅ |

**Los cuatro `doc_type` ya son correctos y ninguno es NULL → no hay fix que proponer.** Sus filas
salen del `.sql` sin más. (Dato de contexto: la asimetría de cobertura lo confirma — `MNDT1070` está
cubierto solo al 22.6% por `MFDT1070`, y el manual de instalación 2X-A al 19.7% por el de operación:
ninguno contiene al otro, que es la firma de «documentos distintos por FUNCIÓN».)

---

## 10. Candidatos para el ticket A3 (metadata/OCR) — **NADA aplicado, ninguno bloquea**

Cierre del encargo «¿el census los emparejó porque la metadata está mal?». Respuesta corta: **sí, en
9 de los 10 rechazos**. Lista de fixes candidatos, con su evidencia y su nivel. Van al **A3** de la
bandeja (`evals/s287_bandeja_alberto_v1.md`), no a este paste.

### 10.1 `product_model` doc-level que no identifica el producto

| doc | `documents.pm` HOY | candidato | evidencia | par |
|---|---|---|---|---|
| `Instruction Manual SG100-IS ENG` | `SG100` | **`SG100-IS`** | 15 chunks ya dicen `SG100-IS`; **regla 2 de §1.10: la etiqueta -IS se blinda** | 7 |
| `Instruction Manual SG200-IS ENG` | `SG200` | **`SG200-IS`** | 14 chunks | 10 |
| `Instruction Manual SG350-IS ENG` | `SG350` | **`SG350-IS`** | 13 chunks | 11 |
| `I56-4225-001 NRX-OPT Web` | `B501RF` (base) | **`NRX-OPT`** | **ground truth de Alberto (s287)** | 12·15 |
| `I56-4206-001 NRX Radio Thermals Web` | `B501RF` | `NRX-TFIX58` | 12 chunks lo dicen | 12 |
| `I56-4205-001 NRX-SMT3 Web` | `B501RF` | *(a portada — va al lote)* | sus chunks dicen `EN-54-25` (artefacto): **no hay fuente fiable en la DB** | 15 |
| `MIEMI130.pdf` | `unknown` | `VSN PLUS` | 52 chunks | 13 |
| `MIEMI120rev05.pdf` | `unknown` | `VSN 2-4` | 46 chunks | 13 |
| `MIE-MI-490.pdf` | `unknown` | `MMX-10M` | 6 chunks + ground truth Alberto | 17·20 |
| `MIE-MI-480.pdf` | `unknown` | `MCX-55M` | 7 chunks + ground truth Alberto | 17 |
| `MIE-MI-470.pdf` | `unknown` | `CMX-10RM` | 6 chunks + ground truth Alberto | 20 |
| `MIE-MI-450.pdf` | `unknown` | `EXP-060R` | portada «IMPRESORA DE LAZO PERIFÉRICO · MOD.EXP-060R» | 23 |
| `MIE-MI-431rv2_1.pdf` | `unknown` | `ZXR50A/ZXR50P` | 18 chunks; portada «ZXr-A / ZXr-P» | 23 |
| `MIE-MP-210.pdf` | `unknown` | `ZXCE` | 104 chunks; portada «CENTRAL … ZXCE» | 16 |
| `MIE-MI-220.pdf` | `unknown` | `REL-2000` | 11 chunks; portada «MOD.REL-2000» | 16 |
| `ms1-2-4.pdf` | `unknown` | `MS-1/MS-2/MS-4` | 27 chunks | 3 |
| `MS8.pdf` | `unknown` | `EFS/EM 8` | 63 chunks + portada | 5 |
| `DXc_Connexion Averia-…` | `unknown` | `DXc` | 1 chunk + título del propio texto | 2 (bloque 0-bis) |
| `D 1148-1 BRS Notifier` | `B501AP` (base) | `SP-20` | 8 chunks | 6 |
| `D 1147-1 BRH Notifier` | `B501AP` (base) | `NFXI-BSF-WCH` | 7 chunks | 6 |

### 10.2 Artefactos de parseo en `product_model` de chunk (**clase `VIA-28V`, 3ª y 4ª instancia**)

| doc | pm de chunk | qué es en realidad | acción |
|---|---|---|---|
| `I56-4225-001 NRX-OPT Web` (12 chunks) | `EN-54-25` | **la NORMA** de componentes con enlace radio | → `NRX-OPT` (Alberto) |
| `I56-4205-001 NRX-SMT3 Web` (16 chunks) | `EN-54-25` | ídem | a portada, lote de Alberto |
| `I56-2081-012 6500R(S)_ES` (20 chunks) | `MODELO-6500R` | la palabra «MODELO» pegada al modelo | → `6500R` |

### 10.3 `manufacturer` no soportado por el propio texto

| doc | `manufacturer` HOY | evidencia | par |
|---|---|---|---|
| `I56-2081-012 6500R(S)_ES` | `Xtralis` | su texto imprime «System Sensor» **7×** y «Xtralis» **0×** | 14 (doc suprimido; **no bloquea**: el representante está bien) |
| `manual IS MA1` | `Detnov` | ya cubierto por el bloque 0 del paste (semilla) | 1 |

### 10.4 Linaje / lifecycle sin poblar

- **Familia TG-DT-951**: `revision` y `revision_date` **NULL** en los 4 docs del BLOQUE S, teniendo la
  portada el dato (`7.2`/Sept-2007, `7.4`/Abr-2009, `7.4`/06-04-2017). Y la generación **v5.87**
  (`MIDT951_v5-87`, `MNDT951_v5-87`, Mayo 2005) + `MP-DT-951_v7.2` siguen **sin cadena de linaje**.
- **Anti-patrón HP011 vivo en la familia**: hay chunks de revisiones NUEVAS suprimidos contra
  revisiones VIEJAS (7.2→v5.87: 8 chunks · 7.4→7.2: 10 chunks · 7.4→v5.87: 7 chunks). No lo toco
  —no está adjudicado— pero **es exactamente el defecto que la migración `20260721190847` reparó
  para HP011**, y aquí está sin reparar en al menos 25 chunks.

### 10.5 Huecos del instrumento (no son metadata de un doc, son del discriminador)

1. **`product_model` multi-modelo con comas** (`'20/20U, 20/20UB'` vs `'20/20L, 20/20LB'`): no
   intersectan como cadena → el discriminador de serie no los reconoce como hermanas y el par 21 se
   coló. Mismo patrón en `'FS-1/FS-2/FS-4'`, `'MS-1/MS-2/MS-4'`, `'ZXR50A/ZXR50P'`, `'EFS/EM 8'`.
2. **Idioma portugués invisible**: el par 19 tiene 26 chunks ES/PT y el detector los cuenta como
   `es` (0 `pt`). `documents.language` es `NULL` en los dos docs del par.
3. **Detección de rebadge**: exige que las **dos** marcas estén impresas; los pares 3 y 5 se colaron
   porque el doc rebadgeado no imprime ninguna.
4. **Unificación `FSL-751E` ↔ `VIEW`** (par 4): mismo producto con dos etiquetas de chunk.
5. **`SMART 3` no distingue tóxico/explosivo** (par 18): los dos docs comparten pm en ambos niveles.
