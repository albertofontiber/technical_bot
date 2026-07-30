# s287 P2 — PACKET DE ADJUDICACIÓN: near-duplicados a nivel DOCUMENTO

Generado read-only por `scripts/s287_p2_dedup_census.py` · 2026-07-30T09:48:09 · git `a2fbad2` · rama `claude/s282-h0t2-qa`. **Cero escrituras a DB.**

> ⚠ **EDITADO A MANO tras la adjudicación de Alberto (s287): par semilla → OPCIÓN B.** Este `.md` y el `.sql` ya **no** son salida limpia del generador. `scripts/s287_p2_dedup_census.py` escribe los tres artefactos (`OUT_JSON`/`OUT_MD`/`OUT_SQL`, líneas 101-104) → **re-correr el census SOBRESCRIBE la adjudicación**. Si hay que regenerar, salva antes estos dos ficheros (el `.json` del census sí es reproducible).
Spec: `evals/s287_etapa2_design_brief_v1.md` (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF de Sol-6). Datos: `evals/s287_p2_dedup_census_v1.json`. Paste: `evals/s287_p2_dedup_apply_v1.sql`.

## Qué decidir y cómo

El census propone marcar `duplicate_of` **chunk a chunk** (no doc a doc): de un par de documentos casi idénticos se retira del pool SOLO los chunks del no-representante cuyo contenido está **íntegramente** en el representante. Todo lo demás sigue sirviéndose.

- **24 pares** con propuesta · **121 marcas** de chunk (120 del census + 1 por la inversión del par semilla, §1.6).
- **Solo el par semilla entra vivo** (adjudicado por Alberto, §1). Los otros **23 pares siguen comentados** con su casilla. Aprobar = quitar el `-- ` inicial de las filas de ese bloque (no hay que tocar comas).
- Si no apruebas nada más y pegas el SQL, se aplica **solo** el par semilla + su metadata-fix.

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

0. **Estado del `.sql` hoy**: el **bloque 0** (metadata-fix del par semilla) y las **10 filas del PAR 1** salen **VIVAS**. Los otros 23 pares siguen comentados, byte a byte como los dejó el census (verificado). Si quieres el par semilla **sin** el fix de metadata, o al revés, cada parte se comenta por separado.
1. Lee la tabla §3 y marca las casillas `[ ] APROBAR ESTE PAR` que quieras, descomentando las filas de esos bloques — y para cada par que apruebes, resuelve también la **decisión 2** (metadata del representante, §3.2).
2. Pega el SQL con `COMMIT` cambiado por `ROLLBACK` (dry-run): verás `staged` / `updated` / `backed_up` y saltará cualquier guard. Con solo el par semilla vivo debe dar `staged=10 · updated=10 · backed_up=10`.
3. Si cuadra, pégalo con `COMMIT`.
4. Rollback post-COMMIT (los tres `UPDATE` están al pie del `.sql`): `duplicate_of` desde `_s287_dedup_backup`, y la metadata desde `_s287_metafix_backup_documents` / `_s287_metafix_backup_chunks`.

Guards del paste: anti-deriva md5 por chunk · ninguno ya marcado · puntero canónico existente, no-duplicado y dentro del representante · el chunk marcado pertenece al doc suprimido · sin cadenas de duplicados · **re-verificación en SQL del invariante span-diff** · sin filas de enunciados colgando · `updated == staged` o aborta.
