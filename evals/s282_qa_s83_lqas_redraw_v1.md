# s282 QA-s83 — LQAS RE-DRAW CONFIRMATORIO (n=59, aceptación 0-defectos) — v1

**Muestra confirmatoria sobre la cohorte auto-apply RE-SCOPED del QA-s83 v2** (el gate previo a la
firma de lote de Alberto, Tramo 2). Estándar `batch_attested_v1`
(`evals/s281_h0t3_authority_contract_proposal_v1.md` §2 Pieza 3): muestra n=59, aceptar el lote
**SOLO con 0 defectos** ⇒ garantiza tasa de defecto real <5% con 95% de confianza. READ-ONLY, SELECT
sobre `chunks_v2`/`documents` (PostgREST GET). 0 escrituras, 0 llamadas de modelo de pago (verificación
manual leyendo el CONTENIDO real, fila a fila).

## VEREDICTO: la cohorte re-scoped NO PASA — 1 defecto / 59. PARADA.

- **58/59 OK · 1 DEFECTO** — fila #14, `ADW535_TD_T140358es_e` (Securiton), eje **`doc_type`**.
- El listón `batch_attested_v1` es **0 defectos**. 1 defecto ⇒ **la cohorte AS-SCOPED (doc_type sobre
  las 536 + language-singleton sobre las 304 + pm-noop) NO queda atestada.**
- El defecto NO está en el eje que motivó el re-scope (language-multi, degradado a advisory en v2): está
  en **`doc_type`**, que el re-scope da por 0-defecto y auto-aplica sobre las 536. **El re-scope v2 no
  cubría esta clase.**
- Regla del contrato aplicada: **PARO y reporto** con evidencia. **NO re-scopeo** (es decisión del
  orquestador / firma de Alberto).

## 1. Método — frame, seeds, estratificación

**Frame (cohorte re-scoped = "el lote").** De las 548 filas auto-apply del v2 (`corroborate_noop` 423 +
`fill_language_doctype` 125), el lote re-scoped = documentos que reciben **≥1 escritura auto-apply** bajo
la regla v2: fill de `doc_type` (536) **O** fill de `language`-SINGLETON (304). `pm` = NO-OP siempre;
`language`-MULTI = ADVISORY (no se aplica). Las **12** filas auto sin ninguno de los dos fills (puro
NO-OP) caen fuera del lote. **Lote = 536** (coincide con `doc_type_fills`=536; todo miembro del lote
recibe fill de doc_type; 304 además reciben language-singleton; 209 además tienen language-multi que
NO se aplica).

**Seeds (declaradas ambas).** Draw v1 usó `seed=282`. Este re-draw usa **`seed=592`** (distinta;
n=59·ronda-2). Draw fresco e independiente: las filas del draw v1 **NO se excluyen**; el solape que
traiga el muestreo se declara abajo. Determinista, reproducible (`scripts/s282_qa_s83_lqas_redraw.py`).

**Estratificación por marca** (largest-remainder, idéntico método que v1 — `_brand_stratified_sample`):

| marca | lote (536) | muestreados | marca | lote | muestreados |
|---|---:|---:|---|---:|---:|
| Notifier | 294 | 33 | Securiton | 6 | 1 |
| Morley | 45 | 5 | Xtralis | 5 | 1 |
| Aritech | 43 | 5 | Honeywell | 3 | 0 |
| Detnov | 39 | 4 | Sensitron | 3 | 0 |
| Kidde | 30 | 3 | Pepperl-Fuchs | 2 | 0 |
| System Sensor | 26 | 3 | Edwards | 2 | 0 |
| Spectrex | 17 | 2 | Fidegas | 1 | 0 |
| Argus Security | 11 | 1 | Avotec | 1 | 0 |
| Pfannenberg | 8 | 1 | **TOTAL** | **536** | **59** |

**Solape con el draw v1 (declarado): 5 / 59** — los trajo el muestreo, no se buscaron. Se re-verifican
igual bajo las reglas re-scoped: `55345103 ...MAD-450...` (#9), `9-30781-kid-en-161721-es` (#12),
`MCDT156_A` (#42), `MNDT742_G` (#52), `UCIP-Borrar-datos-de-CRA1-o-2` (#57). Las otras 54 son filas
NUEVAS no vistas en v1.

## 2. Verificación por eje (contenido real, fila a fila)

Cada fila se verificó leyendo ≥6 chunks de `chunks_v2` (cabecera de contenido, secciones, páginas):

| eje | operación auto-apply | qué se comprobó | defectos / 59 |
|---|---|---|---:|
| `product_model` | NO-OP (corroborate) / conservar (family) | identidad gobernada == contenido | **0 / 59** |
| `doc_type` | fill (DB NULL → s83) | el `doc_type` propuesto describe el GÉNERO real del doc | **1 / 59** |
| `language` (singleton) | fill (DB NULL → s83, solo 1 idioma) | el idioma es el de REDACCIÓN (no tokens sueltos) | **0 / 29** |
| `language` (multi) | ADVISORY — NO se aplica | (excluido del auto-apply por el re-scope) | n/a (28) |

**Language-singleton (29 filas): 0 defectos.** Verifiqué que el idioma singleton es el de redacción del
cuerpo, no un token suelto (lección MADT609). Ejemplos: #18 `D 1036-1_M700KAC_SP` → `es` (prosa ES:
"INSTALACIÓN DEL PULSADOR DIRECCIONABLE"); #19 `D716...M700KAC-KACI_Eng` → `en` (prosa EN: "KAC
INSTALLATION INSTRUCTIONS"); #20 `HLSI-MN-025-I...FR` → `fr` (prosa FR: "Manuel d'installation et
d'utilisation"); #56 `TM380002...FS-1100` → `en` (prosa EN: "Installation Instructions"). La clase
MADT609 (over-tag de idioma) queda contenida: cae en language-MULTI, ya advisory.

## 3. Tabla de las 59 filas (veredicto + evidencia)

`SG:xx`=language-singleton aplicado (idioma verificado de redacción) · `ML-adv`=language-multi
(advisory, no aplicado) · `none`=sin fill de language · `none/contr`=language contradicho en DB (no
aplicado) · `(v1)`=solape con el draw v1.

| # | source_file | marca | write_op | doc_type (fill) | language | veredicto |
|---:|---|---|---|---|---|---|
| 1 | `00-3280-508-4109-06_r006_2x-at_series_quick_st` | Aritech | fill language doctype | guia_usuario | SG:es | OK |
| 2 | `03-0210-501-4301-02_r002_n-mc_series_mcp_backb` | Aritech | corroborate noop | instalacion | ML-adv | OK |
| 3 | `03-0211-501-3000-05_r005_nc_series_conventiona` | Aritech | corroborate noop | instalacion | ML-adv | OK |
| 4 | `085501949p_PY X-S-05_Installation_manual_D-GB-` | Pfannenberg | corroborate noop | instalacion | ML-adv | OK |
| 5 | `08895_04-multiling` | Notifier | fill language doctype | instalacion | ML-adv | OK |
| 6 | `11370_17_VESDA_VLF-500_Product_Guide_A4_Spanis` | Xtralis | fill language doctype | guia_usuario | SG:es | OK |
| 7 | `2x-lb-161721-es` | Aritech | corroborate noop | datasheet | SG:es | OK |
| 8 | `55310021-Manual-Centrales-Convencionales-CCD-1` | Detnov | fill language doctype | instalacion | ML-adv | OK |
| 9 | `55345103 Manual Pulsador Analogico MAD-450 ES ` (v1) | Detnov | corroborate noop | instalacion | ML-adv | OK |
| 10 | `55346102 Manual Sirena Analogica MAD-461 ES FR` | Detnov | corroborate noop | instalacion | ML-adv | OK |
| 11 | `55350007 Manual Tarjeta Regulacion Motores TRM` | Detnov | corroborate noop | instalacion | ML-adv | OK |
| 12 | `9-30781-kid-en-161721-es` (v1) | Kidde | corroborate noop | datasheet | ML-adv | OK |
| 13 | `9-30783-kid-en-161721-es` | Kidde | corroborate noop | datasheet | ML-adv | OK |
| 14 | `ADW535_TD_T140358es_e` | Securiton | fill language doctype | **datasheet** | SG:es | **DEFECTO** |
| 15 | `AM 8200G manual instalacion Rv 3` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 16 | `AM 8200N-manual instalacion RV 4 30-01-2025` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 17 | `AM-8100 manual de usuario y programacion rev 4` | Notifier | corroborate noop | configuracion | ML-adv | OK |
| 18 | `D 1036-1_M700KAC_SP` | Notifier | corroborate noop | instalacion | SG:es | OK |
| 19 | `D716 issue 1 - M700KAC-KACI_Eng` | Notifier | fill language doctype | instalacion | SG:en | OK |
| 20 | `HLSI-MN-025-I_NFS Supra Series FR 25_03_2014 S` | Notifier | corroborate noop | instalacion | SG:fr | OK |
| 21 | `HLSI_MN-DT-1412_TG-IP1-SEC_MN` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 22 | `I56-0873-000 SMK400` | System Sensor | fill language doctype | instalacion | SG:en | OK |
| 23 | `I56-1652-023 ECO1005_ECO1005T_ECO1004T` | Morley | corroborate noop | instalacion | ML-adv | OK |
| 24 | `I56-1726-003 6200R Manual ES` | System Sensor | corroborate noop | instalacion | SG:es | OK |
| 25 | `I56-1729-002 - SD-851E Manual` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 26 | `I56-1730-002_FD-851RE & FD-851HTE Manual` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 27 | `I56-17771-002_multi` | System Sensor | fill language doctype | instalacion | ML-adv | OK |
| 28 | `I56-2005-002 M710 M720 M721 M701` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 29 | `I56-3383-002 IDX-751 AE EN DE` | Notifier | fill language doctype | instalacion | ML-adv | OK |
| 30 | `I56-3879-000 MI-LPB2-S2I_EN` | Morley | corroborate noop | instalacion | SG:en | OK |
| 31 | `I56-3879-000 MI-LPB2-S2I_ES` | Morley | corroborate noop | instalacion | none | OK |
| 32 | `I56-4207-001 NRXI-GATE Gateway Web` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 33 | `I56-4404-001 M710E M720E M721E` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 34 | `I56-699-15R 5451EIS_Eng` | Notifier | corroborate noop | instalacion | SG:en | OK |
| 35 | `Instruction Manual SG100-IS ENG` | Argus Security | fill language doctype | instalacion | SG:en | OK |
| 36 | `MADT100_01` | Notifier | fill language doctype | instalacion | SG:es | OK |
| 37 | `MADT155_08` | Notifier | fill language doctype | operacion | SG:es | OK |
| 38 | `MADT190_12` | Notifier | corroborate noop | configuracion | SG:es | OK |
| 39 | `MADT190_14` | Notifier | corroborate noop | boletin | SG:es | OK |
| 40 | `MADT234` | Notifier | corroborate noop | instalacion | SG:es | OK |
| 41 | `MCDT150` | Notifier | corroborate noop | configuracion | SG:es | OK |
| 42 | `MCDT156_A` (v1) | Notifier | fill language doctype | configuracion | SG:es | OK |
| 43 | `MIDT250_A` | Notifier | corroborate noop | instalacion | SG:es | OK |
| 44 | `MIE-TI-001` | Morley | corroborate noop | boletin | SG:es | OK |
| 45 | `MNDT040P` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 46 | `MNDT102` | Notifier | corroborate noop | guia_usuario | SG:es | OK |
| 47 | `MNDT1071` | Notifier | fill language doctype | guia_usuario | ML-adv | OK |
| 48 | `MNDT260` | Notifier | corroborate noop | configuracion | SG:es | OK |
| 49 | `MNDT370` | Notifier | corroborate noop | configuracion | ML-adv | OK |
| 50 | `MNDT607` | Notifier | corroborate noop | mantenimiento | SG:es | OK |
| 51 | `MNDT700_C` | Spectrex | corroborate noop | instalacion | SG:es | OK |
| 52 | `MNDT742_G` (v1) | Notifier | corroborate noop | instalacion | SG:es | OK |
| 53 | `NCO-10-multinglingual` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 54 | `PUL-PEXT_Instrucciones multi` | Notifier | corroborate noop | instalacion | ML-adv | OK |
| 55 | `TB-HON-ES_POL200TS_04-19` | Notifier | corroborate noop | boletin | SG:es | OK |
| 56 | `TM380002_RevIMarch2016_FS-1100` | Spectrex | corroborate noop | instalacion | SG:en | OK |
| 57 | `UCIP-Borrar-datos-de-CRA1-o-2` (v1) | Morley | corroborate noop | configuracion | none/contr | OK |
| 58 | `as2363-62536-es` | Aritech | corroborate noop | datasheet | ML-adv | OK |
| 59 | `ke-io3144-161721-es` | Kidde | corroborate noop | datasheet | SG:es | OK |

## 4. EL DEFECTO — #14 `ADW535_TD_T140358es_e` (Securiton), eje `doc_type`

**Qué escribiría el auto-apply:** `doc_type = COALESCE(NULL, 'datasheet') = 'datasheet'`. DB
verificado: `documents.id=dff3152a-...`, `product_model='ADW535'`, **`doc_type=NULL`**, `language=NULL`
→ el fill SÍ se aplicaría. (`language='es'` y `pm='ADW535'` son CORRECTOS; el defecto es SOLO doc_type.)

**Por qué es incorrecto (evidencia de contenido leída vía SELECT):**

- El documento es la **"Descripción técnica" (Technische Beschreibung) T 140 358** del Securiton
  ADW 535 — un **MANUAL TÉCNICO de 118 páginas / 201 chunks**, no una hoja de datos. Índice real
  (secciones leídas): `1 Aspectos generales` · `2 Funcionamiento` (principio eléctrico, programación,
  relés, interfaces, entradas, monitorización del tubo sensor, umbrales de alarma, tipos de reset,
  grabación en SD) · `3 Componentes` · `4 Proyecto de sistemas` (ADW HeatCalc, límites del sistema) ·
  `7 Puesta en funcionamiento` · `10 Fallos`. Extracto p1: *"ADW 535 — Detector térmico lineal —
  Descripción técnica — a partir de la versión de FW 01.03.xx"*.
- **El propio documento distingue "descripción técnica" de "datasheet":** p4 §"Documentación adicional"
  lista *"Hoja de datos del ADW 535 — T 140 359"* como un documento **SEPARADO**. La hoja de datos
  (datasheet) es T 140 **359**; este doc es la descripción técnica T 140 **358**. s83 los confunde.
- El taxón `datasheet` (enum s83: `instalacion|operacion|configuracion|datasheet|boletin|guia_usuario|
  mantenimiento|otro`, sin definiciones formales) es el bucket de la ficha de especificaciones corta.
  En la propia muestra hay datasheets GENUINOS (correctos) — #7 `2X-LB`, #58 `AS2363`, #59 `KE-IO3144`:
  ficha de 1-2 páginas "visión general + especificaciones técnicas". El ADW535_TD es estructuralmente
  otro género (manual de 118 pp con puesta en marcha y fallos). El bucket correcto sería
  `instalacion`/`guia_usuario`, NO `datasheet`. Es un error de categoría, no un matiz.

**Es una CLASE sistemática, no un caso aislado.** s83 clasifica las "Descripción técnica /
Technische Beschreibung" (`_TD_T140xxx`) de Securiton como `datasheet`. En el lote de 536 hay **3**
(todas `doc_type=NULL` en DB → las 3 se auto-escribirían mal):

| source_file | s83 pm | chunks | máx. página | s83 doc_type | género real |
|---|---|---:|---:|---|---|
| `ADW535_TD_T140358es_e` (#14, este draw) | ADW 535 | 201 | 118 | datasheet | manual técnico |
| `ASD532_TD_T140421es_a` (**draw v1, marcado OK**) | ASD 532 | 210 | 129 | datasheet | manual técnico |
| `ASD533_TD_T140287es_e` (no muestreado) | ASD 533 | 202 | 118 | datasheet | manual técnico |

**Nota para el orquestador:** el draw v1 muestreó `ASD532_TD` (su fila 11) y lo marcó OK — el mismo
patrón se le escapó. El re-draw con seed distinta cazó la clase vía `ADW535_TD`. Esto es exactamente
para lo que existe la muestra confirmatoria independiente. La clase completa (los 3, y cualquier otro
`_TD_T140`/"Descripción técnica" Securiton fuera del muestreo) debe adjudicarse antes de re-atestar.

## 5. Bloque de firma T2 — **NO EMITIBLE** (la cohorte falló el listón 0-defectos)

Con 1 defecto en 59, el contrato `batch_attested_v1` **prohíbe la firma del lote**. NO produzco un
bloque firmable. Lo que sigue es SOLO referencia de lo que el T2 escribiría **una vez remediada la
clase-defecto y re-corrida una muestra confirmatoria a 0-defectos** — la decisión de re-scope /
remediación es del orquestador (no la tomo aquí):

**Recuentos por eje del auto-apply v2 (`fill_summary`, cohorte 536):**
- `doc_type` (AUTO, DB NULL→s83): **536** — ⚠️ contiene ≥3 mislabels `datasheet` (clase Securiton `_TD`).
- `language`-SINGLETON (AUTO, DB NULL, 1 idioma): **304** — 0-defecto en esta muestra (29/29 verificadas).
- `language`-MULTI (ADVISORY, no auto): 209 · `language` contradicho en DB (advisory): 18 · `doc_type`
  distinto en DB (advisory): 11.
- `product_model`: NUNCA se escribe (corroborate=NO-OP; family=conservar).

**Reversibilidad:** fill-only con NULL-guard; revertir = `SET doc_type=NULL` / `language=NULL` para los
`id` del lote. Nunca overwrite.

**SQL de ejemplo por lote por marca (NO aplicado — plantilla):**
```sql
-- Aplicar SOLO tras firma LQAS a 0-defectos. Uno por marca. Fuente de valores:
-- evals/s282_qa_s83_result_v2.json (write_op in {corroborate_noop, fill_language_doctype}).
-- AUTO = doc_type (todas) + language SOLO cuando fill_plan.language_fill_singleton = true.
UPDATE documents d SET
  doc_type = COALESCE(d.doc_type, :s83_doc_type),         -- fill-only; NULL-guard
  language = COALESCE(d.language, :s83_language_singleton) -- SOLO singleton; multi = advisory
WHERE d.id = :document_id
  AND (d.doc_type IS NULL OR d.language IS NULL);          -- nunca overwrite
-- product_model: NO se toca. language-MULTI: NO en el UPDATE (packet advisory de Alberto).
```
⚠️ **Precondición de firma:** el `:s83_doc_type` de los `_TD_T140` Securiton (y de cualquier
"Descripción técnica" análoga) NO es fiable (`datasheet` sobre manuales de 118+ pp). Antes de emitir
el lote `doc_type`: adjudicar/degradar esa clase, y re-correr una muestra confirmatoria nueva
(seed distinta) hasta 0-defectos.

## 6. Reproducibilidad

- Instrumento: `scripts/s282_qa_s83_lqas_redraw.py` (READ-ONLY; SELECT `chunks_v2`/`documents`;
  0 escrituras; 0 modelo de pago). Bundle de verificación: `evals/s282_qa_s83_lqas_redraw_bundle.json`.
- Frame = 536 (lote re-scoped) derivado de `evals/s282_qa_s83_result_v2.json`. Draw: `seed=592`
  (v1: `seed=282`), estratificado por marca (largest-remainder). Solape con v1: 5/59 (declarado).
- Corpus (del freeze v2): `chunks_v2`=25090 · `documents`=1171. Worktree `Technical Bot-s281`,
  rama `claude/s282-h0t2-qa`. Sin commits.
