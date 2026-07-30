# s287 P2 — PACKET DE ADJUDICACIÓN: near-duplicados a nivel DOCUMENTO

Generado read-only por `scripts/s287_p2_dedup_census.py` · 2026-07-30T09:48:09 · git `a2fbad2` · rama `claude/s282-h0t2-qa`. **Cero escrituras a DB.**
Spec: `evals/s287_etapa2_design_brief_v1.md` (v2-P2 + v3-FINAL-P2, gate de SPAN-DIFF de Sol-6). Datos: `evals/s287_p2_dedup_census_v1.json`. Paste: `evals/s287_p2_dedup_apply_v1.sql`.

## Qué decidir y cómo

El census propone marcar `duplicate_of` **chunk a chunk** (no doc a doc): de un par de documentos casi idénticos se retira del pool SOLO los chunks del no-representante cuyo contenido está **íntegramente** en el representante. Todo lo demás sigue sirviéndose.

- **24 pares** con propuesta · **120 marcas** de chunk.
- **Ninguna fila entra viva.** En el `.sql` todas están comentadas con una casilla `[ ] APROBAR ESTE PAR`. Aprobar = quitar el `-- ` inicial de las filas de ese bloque (no hay que tocar comas).
- Si no apruebas nada y pegas el SQL igualmente, el guard 3 aborta la transacción y no se aplica nada.

### El invariante que protege el corpus (gate de Sol-6)

Un chunk solo se propone si (a) ≥ **92% de sus palabras** están cubiertas por el documento representante, (b) **ninguna racha de ≥ 25 palabras** queda sin cubrir, y (c) existe un chunk gemelo concreto con Jaccard ≥ 0.6 al que apuntar. Los chunks `UNIQUE`, `PARTIAL`, `COVERED_NO_TWIN` y `SHORT` **nunca** se proponen — un near-dup a nivel documento puede perfectamente tener spans propios, y el par semilla lo demuestra.

---

## 1. PAR SEMILLA (cat010) — análisis completo

`2b694083__a6b9dc84` · tier **T3-CROSS-BRAND-ATRIBUCION-SOSPECHOSA** · cobertura de palabras 0.72 / 0.89

| | doc A (recomendado CONSERVAR) | doc B (recomendado SUPRIMIR-parcial) |
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

**Recomiendo el refinamiento, y creo que el criterio literal está mal para este problema.** Razón: los spans únicos **nunca se suprimen** — ya los protege el gate. Así que «más spans únicos» no protege ningún contenido; lo único que decide el representante es **de qué documento sale la CITA** del contenido compartido. Con el criterio literal, el bot respondería los hechos de cat010 citando `manual IS MA1` atribuido a **Detnov** para un producto de e2S. Con el refinamiento, cita el manual correcto y las páginas únicas de B siguen disponibles.

**Riesgo del refinamiento, declarado:** el auto-soporte es una heurística de substring. Un `manufacturer` correcto que simplemente no se imprime en el manual puntúa 0 (falso negativo) — por eso no se aplica solo y todos los pares divergentes van a tu casilla.

### 1.5 Efecto esperado sobre el pool de cat010

Se retirarían **9 de 18** chunks de B (los gemelos), liberando los slots que el diagnóstico midió comidos por el doc gemelo, y quedarían servibles los 9 restantes (UNIQUE=4, PARTIAL=5) más los 15 de A. **No medido aquí**: el efecto en el pool/composición es el gate de la pieza (probe de cat010 + sweep-39), no una promesa de este census.

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

Ordenados: semilla primero, luego por nº de marcas. `div` = las dos políticas de representante discrepan.

| # | par | tier | div | CONSERVA | SUPRIME (marcas/total) | PRESERVA | cob. | motivo |
|---|---|---|---|---|---|---|---|---|
| 1 **SEMILLA** | `2b694083__a6b9dc84` | T3 | SÍ | `IS5001-F_IS-mA1_EN` (European Safety Systems) | `manual IS MA1` (Detnov) 9/18 | UNIQUE=4, PARTIAL=5 | 0.72/0.89 | metadata auto-soportada (2/3 vs 0/3) |
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

---

## 5. Cómo aplicar

1. Lee la tabla §3 y marca las casillas `[ ] APROBAR ESTE PAR` que quieras en `evals/s287_p2_dedup_apply_v1.sql`, descomentando las filas de esos bloques.
2. Pega el SQL con `COMMIT` cambiado por `ROLLBACK` (dry-run): verás `staged` / `updated` / `backed_up` y saltará cualquier guard.
3. Si cuadra, pégalo con `COMMIT`.
4. Rollback post-COMMIT (está al pie del `.sql`): `UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of FROM _s287_dedup_backup b WHERE c.id = b.id;`

Guards del paste: anti-deriva md5 por chunk · ninguno ya marcado · puntero canónico existente, no-duplicado y dentro del representante · el chunk marcado pertenece al doc suprimido · sin cadenas de duplicados · **re-verificación en SQL del invariante span-diff** · sin filas de enunciados colgando · `updated == staged` o aborta.
