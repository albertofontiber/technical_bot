# s282 QA-s83 — LQAS DRAW 3 (confirmatorio, n=59, aceptación 0-defectos) — LEDGER v1

**Muestra confirmatoria sobre la cohorte auto-apply v3 (post-guard) del QA-s83** — el gate previo a
la firma de lote de Alberto (Tramo 2). Estándar `batch_attested_v1`
(`evals/s281_h0t3_authority_contract_proposal_v1.md` §2 Pieza 3): muestra n=59, aceptar el lote
**SOLO con 0 defectos**. Este documento es el **ledger fila-a-fila que faltaba** (hallazgo
`DRAW3-SIN-LEDGER` del dúo, `evals/s282_t2_apply_duo_r1_adjudication_v1.yaml`): re-verificación
fresca de las 59 filas contra el CONTENIDO real (SELECT `chunks_v2`), registrando evidencia por
fila — **no reconstrucción de memoria**.

## VEREDICTO: 0 defectos / 59 en el ledger fila-a-fila. La cohorte v3 SUPERA el listón por-muestra.

- **59/59 OK · 0 DEFECTOS** verificando 3 ejes contra el contenido leído: (1) `product_model` —
  identidad gobernada == contenido (NO-OP para `corroborate`, familia conservada; **jamás se
  escribe**); (2) `doc_type` del fill == GÉNERO real del documento; (3) `language` — el singleton
  escrito == idioma de **REDACCIÓN** del cuerpo (no tokens sueltos), y el multi = ADVISORY (no se
  escribe).
- El listón por-muestra (0 defectos) **SE CUMPLE en draw 3**. Esto NO es un bound limpio <5%@95%
  sobre la cohorte de 533/301 — ver el framing honesto en `evals/s282_qa_s83_attestation_v2.md`
  (estratos inclusión-cero + sensibilidad del verificador <100%, falso-accept del draw 1
  documentado). La decisión de aceptación es de Alberto.
- READ-ONLY, SELECT-only. 0 escrituras, 0 llamadas de modelo de pago. La evidencia de contenido
  proviene del bundle `evals/s282_qa_s83_lqas_draw3_bundle.json` (10 chunks/documento, cabecera
  600 chars, capturados por SELECT `chunks_v2` con orden `page_number.asc,chunk_index.asc`).

---

## 1. Método — frame, seeds, estratificación, solape

**Frame (cohorte v3 = "el lote").** De las **545** filas auto-apply del v3 (`corroborate_noop` 422 +
`fill_language_doctype` 123), el lote = documentos que reciben **≥1 escritura auto-apply**: fill de
`doc_type` (533) **O** fill de `language`-SINGLETON (301). `pm` = NO-OP siempre; `language`-MULTI =
ADVISORY (no se aplica). **Lote = 533** (`doc_type_fills`=533; todo miembro del lote recibe fill de
`doc_type`; 301 además reciben language-singleton). El guard de plausibilidad de categoría ya sacó
las 3 filas Securiton `_TD` `datasheet` (draw 2) del auto-apply → **no están en este frame**.

**Seeds (declaradas las tres).** Draw 1 = `seed 282` (v1, 0 defectos pero NO fiable — falso-aceptó
la clase `_TD`). Draw 2 / re-draw = `seed 592` (v2, **1 defecto → PARADA**, cazó `ADW535_TD`). Draw
3 = **`seed 593`** (esta muestra, sobre la cohorte YA remediada). Streams de Mersenne-Twister
independientes por construcción (la proximidad numérica 592↔593 no crea dependencia). Draw fresco:
las filas de draws previos NO se excluyen; el solape que trae el muestreo se declara.

**Estratificación por marca** (largest-remainder, `_brand_stratified_sample`): Notifier 33 · Morley
5 · Aritech 5 · Detnov 4 · Kidde 3 · System Sensor 3 · Spectrex 2 · Xtralis 1 · Argus Security 1 ·
Honeywell 1 · Pfannenberg 1 = **59**. (Estratos con inclusión-cero en este draw: Sensitron,
Pepperl-Fuchs, Edwards, Fidegas, Avotec, Securiton, Spectrex[parcial] — declarado como límite del
bound en la attestation.)

**Solape declarado (lo trajo el muestreo, no se buscó):**
- con draw 1 (5/59): `MIDT1041` (#38), `MNDT100` (#42), `MNDT213` (#46), `MNDT720` (#51),
  `nc-mc-0-g-161721-es` (#57).
- con draw 2 (3/59): `55310021-…CCD-100…` (#8), `AM-8100…rev 4…` (#13), `MNDT040P` (#41).
- Las 51 restantes son filas NUEVAS. Todas las de solape se re-verificaron igual, todas OK.

## 2. Verificación por eje (contenido real, fila a fila)

| eje | operación auto-apply | qué se comprobó | defectos / 59 |
|---|---|---|---:|
| `product_model` | NO-OP (corroborate) / conservar (family) | identidad gobernada == contenido | **0 / 59** |
| `doc_type` | fill (DB NULL → s83), 59/59 | el `doc_type` describe el GÉNERO real | **0 / 59** |
| `language` (singleton, 33) | fill (DB NULL → s83, 1 idioma) | idioma de REDACCIÓN del cuerpo | **0 / 33** |
| `language` (multi, 25) | ADVISORY — NO se aplica | (fuera del auto-apply) | n/a |
| `language` (contradicho, 1) | ADVISORY — NO se aplica | (#21, fuera del auto-apply) | n/a |

**Corolario del guard (verificado en este ledger):** los **7** `datasheet` de la muestra (#6, #7,
#43, #55, #57, #58, #59) tienen **≤ 7 chunks** (máx 7) — fichas de especificación GENUINAS y cortas,
muy por debajo del umbral de 30 del guard. Ningún `datasheet` sobre documento grande sobrevive en el
frame v3 (la clase Securiton `_TD` de 201–210 chunks está fuera). El género `boletin` (#17) es de
1 chunk. Consistente con el guard.

## 3. Ledger de las 59 filas (veredicto + evidencia de contenido)

`SG:xx` = language-singleton aplicado (idioma verificado de redacción) · `ML-adv` = language-multi
(ADVISORY, no aplicado) · `none/contr` = language contradicho en DB (no aplicado) · `cbn` =
`corroborate_noop` · `fld` = `fill_language_doctype` · `(v1)`/`(v2)` = solape con draw previo.

| # | source_file | marca | ch | wop | doc_type | lang | evidencia de contenido (leída) | veredicto |
|--:|---|---|--:|---|---|---|---|---|
| 1 | `00-3280-508-4209-02…2x-at…quick_operation_guide_es` | Aritech | 5 | fld | operacion | SG:es | "Guía rápida de USO de la serie 2X-AT" (prosa ES: "Si oye el zumbador…") — guía de uso = operacion | OK |
| 2 | `11369_22_VESDA_VLF-250_Product_Guide_A4_Spanish` | Xtralis | 84 | fld | guia_usuario | SG:es | "VESDA VLF-250 Guía del producto" (prosa ES) — product guide = guia_usuario | OK |
| 3 | `156-0394-007R - PIBV2_Eng` | System Sensor | 10 | cbn | instalacion | SG:en | "INSTALLATION AND MAINTENANCE INSTRUCTIONS — PIBV2" (prosa EN) | OK |
| 4 | `1998M0901_FS24X_ES-AR…` | Notifier | 49 | cbn | instalacion | ML-adv | "Guía de instalación y manual de funcionamiento — FS24X" (ES); lang [en,es,fr] multi → NO escrito | OK |
| 5 | `1998M0901_FS24X_PT-BR…` | Honeywell | 2 | cbn | instalacion | ML-adv | Fragmento del manual de instalación FS24X (PT: "Desenhos/Descrição"); lang multi → NO escrito | OK |
| 6 | `2x-af2-scfb-s-161721-es` | Aritech | 6 | cbn | datasheet | ML-adv | "2X-AF2-SCFB-S … Overview + Especificaciones técnicas" — datasheet corto (6 ch); lang multi → NO escrito | OK |
| 7 | `2x-at-f2-161721-es` | Aritech | 7 | cbn | datasheet | SG:es | "2X-AT-F2 Panel… Descripción general + Especificaciones" (prosa ES) — datasheet corto (7 ch) | OK |
| 8 | `55310021…CCD-100…` (v2) | Detnov | 70 | fld | instalacion | ML-adv | "Guía de instalación y usuario — Centrales Convencionales CCD-100" (ES); lang [en,es,fr,it] → NO escrito | OK |
| 9 | `55343101…MAD-432 ES FR GB IT` | Detnov | 4 | cbn | instalacion | ML-adv | "Módulo 1/2 Sirenas… instalación" (bilingüe ES/EN); lang multi → NO escrito | OK |
| 10 | `55393002…FAD-905 ES FR GB IT` | Detnov | 16 | cbn | instalacion | ML-adv | "Fuentes de Alimentación — Guía de instalación y usuario" (ES); lang multi → NO escrito | OK |
| 11 | `997-528-000-1` | Notifier | 26 | cbn | instalacion | SG:en | "NAS-2 — installation and user guide" (prosa EN) | OK |
| 12 | `997-670-005-3_Operating_ES` | Notifier | 62 | cbn | operacion | SG:es | "Central Pearl™ — Manual de FUNCIONAMIENTO" (prosa ES) = operacion | OK |
| 13 | `AM-8100…rev 4` (v2) | Notifier | 121 | cbn | configuracion | ML-adv | "AM-8100 Manual de Usuario y Programación" (ES) — programación = configuracion; lang [es,it] → NO escrito | OK |
| 14 | `AM-8200-manu-prog-spa` | Notifier | 117 | cbn | configuracion | ML-adv | "AM-8200 Manual de PROGRAMACIÓN" (ES) = configuracion; lang [es,it] → NO escrito | OK |
| 15 | `AM-8200N…rev 3` | Notifier | 120 | cbn | configuracion | ML-adv | "AM-8200N Manual de Usuario y Programación" (ES) = configuracion; lang [en,es,it] → NO escrito | OK |
| 16 | `AM-LCD manual de instalacion y usuario RV 0` | Notifier | 26 | cbn | guia_usuario | SG:es | "AM-LCD Manual de Usuario y Programación" (panel repetidor, prosa ES) = guia_usuario | OK |
| 17 | `BTDT017` | Notifier | 1 | cbn | boletin | ML-adv | "Boletín Técnico BT-DT-017 — Problemas en el LCD-80" (1 ch) = boletin; lang [en,es] → NO escrito | OK |
| 18 | `CALYPSO-II_manual` | Detnov | 10 | cbn | guia_usuario | SG:es | "Calypso-II detector autónomo — instalación/uso/mantenimiento" (prosa ES) = guia_usuario | OK |
| 19 | `D 1100-4 Sounder` | Notifier | 3 | fld | instalacion | ML-adv | Sounder — montaje + tone table (multilingüe IT/EN…); lang [de,en,es,fr,it] → NO escrito | OK |
| 20 | `D 1152-1 BGL Morley` | Morley | 7 | cbn | instalacion | ML-adv | "MI-BGL-PC-I — terminal connections + installation + anti-tamper" (multi); lang multi → NO escrito | OK |
| 21 | `DXC-Como-conectar-una-sirena-de-lazo` | Morley | 1 | cbn | otro | none/contr | Artículo FAQ "Question/Answers" (soporte, ES) = otro; lang contradicho → NO escrito | OK |
| 22 | `FS8` | Notifier | 73 | cbn | instalacion | SG:es | "EFS/EM 8 — Manual de instalación, puesta en marcha y funcionamiento" (prosa ES) | OK |
| 23 | `HLSI-MA-103-I_GuiaRapida_RP1r-Supra_EN` | Notifier | 14 | fld | instalacion | SG:en | "RP1r-Supra Quick Guide — Assembly/Wiring/Set-up" (prosa EN) = instalacion | OK |
| 24 | `HOP-138-8PT-issue 5_01-2026` | Notifier | 5 | cbn | configuracion | ML-adv | "INSPIRE E10/E15 — Instruções de colocação em funcionamento" (PT) = configuracion; lang [en,pt] → NO escrito | OK |
| 25 | `I56-1653-022 ECO1003` | Morley | 4 | cbn | instalacion | ML-adv | "ECO1003 detector — installation/testing/maintenance/cableado" (bilingüe); lang multi → NO escrito | OK |
| 26 | `I56-1726-003 6200R Manual EN` | System Sensor | 18 | cbn | instalacion | SG:en | "MODEL 6200R OPTICAL BEAM — Installation Recommendations + specs" (prosa EN) | OK |
| 27 | `I56-2255-00 CR6` | System Sensor | 5 | cbn | instalacion | ML-adv | "INSTALLATION AND MAINTENANCE INSTRUCTIONS — CR-6" (EN/ES); lang multi → NO escrito | OK |
| 28 | `I56-2956-000_prelim` | Morley | 17 | fld | instalacion | ML-adv | "INSTALLATION AND MAINTENANCE INSTRUCTIONS — MI-SC6" (EN/ES/IT); lang multi → NO escrito | OK |
| 29 | `I56-3909-010_A_AgileIQ_ES` | Notifier | 97 | cbn | configuracion | ML-adv | "AgileIQ — MANUAL DE PROGRAMACIÓN Y PUESTA EN SERVICIO" (SW, ES) = configuracion; lang [en,es] → NO escrito | OK |
| 30 | `I56-4294-002 NRX-M711 Module` | Notifier | 15 | fld | instalacion | ML-adv | "NRX-M711 … INSTALLATION INSTRUCTIONS" (EN/ES/DE); lang multi → NO escrito | OK |
| 31 | `I56-6296-000_B NFXI-VIEW` | Notifier | 9 | cbn | instalacion | ML-adv | "NFXI-VIEW — INSTALLATION AND MAINTENANCE INSTRUCTIONS" (EN/ES/DE); lang multi → NO escrito | OK |
| 32 | `I56-6577-006_ES FAAST…LT-200 QIG` | Notifier | 42 | fld | instalacion | SG:es | "FAAST LT-200 — GUÍA RÁPIDA DE INSTALACIÓN" (prosa ES) | OK |
| 33 | `Instruction Manual SG350-IS ENG` | Argus Security | 13 | fld | instalacion | SG:en | "SG350-IS intrinsically safe heat detector — installation/testing" (prosa EN) | OK |
| 34 | `MADT190_11` | Notifier | 2 | cbn | operacion | SG:es | "ACCIONES BÁSICAS EN LA ID3000 EN CASO DE ALARMA Y AVERÍA" (prosa ES) = operacion | OK |
| 35 | `MADT280` | Notifier | 4 | fld | otro | SG:es | "COMUNICACIONES EN LA AM2020/AFP1010 — SIB-2048/RS-232" (referencia técnica, ES) = otro | OK |
| 36 | `MCDT120` | Notifier | 18 | cbn | guia_usuario | SG:es | "PK-AFP200E — Manual de Usuario" (programación offline AFP200, ES) = guia_usuario (auto-título) | OK |
| 37 | `MIDT1040` | Notifier | 25 | cbn | instalacion | SG:es | "DH500 — Manual de Instalación y Mantenimiento" (prosa ES) | OK |
| 38 | `MIDT1041` (v1) | Pfannenberg | 23 | fld | instalacion | SG:es | "DH500AC/DC — Manual de Instalación y Mantenimiento" (prosa ES). `brand=Pfannenberg` es artefacto de estrato (contenido = Notifier); marca/manufacturer NO se escribe → sin efecto en el fill | OK |
| 39 | `MIDT732` | Notifier | 61 | cbn | instalacion | SG:es | "Mini-LaserStar MINILÁSER25 — Manual (MI-DT-732), indicadores/interior/programación" (prosa ES); género de manual de detector = instalacion (adyacente) | OK |
| 40 | `MIEMN570` | Morley | 59 | fld | guia_usuario | SG:es | "VSN-RP1r manual de USUARIO — Central de extinción" (prosa ES) = guia_usuario (auto-título) | OK |
| 41 | `MNDT040P` (v2) | Notifier | 6 | cbn | instalacion | ML-adv | "CFP-600-E — Manual de Instalação e Funcionamento" (PT/ES) = instalacion; lang [es,pt] → NO escrito | OK |
| 42 | `MNDT100` (v1) | Notifier | 43 | cbn | instalacion | SG:es | "RP-1001 — Procedimiento de Instalación (índice), sistema extinción" (prosa ES) | OK |
| 43 | `MNDT1002` | Notifier | 3 | cbn | datasheet | SG:es | "TARJETA MMX-10 — 10 entradas… Descripción + conexionado" (3 ch, ES) = datasheet corto | OK |
| 44 | `MNDT1070` | Notifier | 100 | cbn | guia_usuario | SG:es | "LTS-240 detector lineal fibra óptica — Manual de usuario" (prosa ES) = guia_usuario (100 ch; NO clase corta) | OK |
| 45 | `MNDT1420` | Notifier | 2 | cbn | configuracion | ML-adv | "TCF-142-S — CONFIGURACIÓN DEL CONVERTIDOR" (2 ch, ES) = configuracion; lang [en,es] → NO escrito | OK |
| 46 | `MNDT213` (v1) | Notifier | 32 | fld | instalacion | SG:es | "Repetidor Serie 1000 — Manual de instalación, puesta en marcha y funcionamiento" (prosa ES) | OK |
| 47 | `MNDT500` | Notifier | 51 | fld | operacion | SG:es | "CENTRAL DE GAS G-500 — Manual de Instrucciones (funcionamiento/alarma/avería)" (ES) = operacion | OK |
| 48 | `MNDT503` | Notifier | 46 | fld | operacion | SG:es | "CENTRAL DE GAS G-100 — Manual de Instrucciones (funcionamiento/alarma)" (ES) = operacion | OK |
| 49 | `MNDT656` | Notifier | 5 | fld | instalacion | SG:es | "Detectores GAS serie GUARD S876xx/S877xx — Descripción + INSTRUCCIONES DE INSTALACIÓN" (prosa ES) | OK |
| 50 | `MNDT696` | Notifier | 59 | fld | instalacion | ML-adv | "S20/20MI detector de llama IR³ — Manual (incl. INSTRUCCIONES PARA LA INSTALACIÓN)" (ES); lang [en,es] → NO escrito | OK |
| 51 | `MNDT720` (v1) | Spectrex | 44 | fld | instalacion | SG:es | "20/20L,20/20LB detector UV/IR — Manual (INSTRUCCIONES DE INSTALACIÓN)" (prosa ES) | OK |
| 52 | `MNDT725_40-40M` | Spectrex | 77 | fld | instalacion | SG:es | "S40/40M detector de llama IR — Manual (Cap.2 Instalación del detector)" (prosa ES) | OK |
| 53 | `MNDT748` | Notifier | 28 | cbn | guia_usuario | SG:es | "NAS-20 Air Sampling — Manual de Usuario" (prosa ES) = guia_usuario (auto-título) | OK |
| 54 | `MPDT212` | Notifier | 111 | fld | configuracion | SG:es | "ID1000 — Manual de PROGRAMACIÓN" (prosa ES) = configuracion (111 ch; NO clase corta) | OK |
| 55 | `ad68n-0100-1-es` | Kidde | 2 | cbn | datasheet | SG:es | "AD68N-0100 cable sensor térmico — General + Especificaciones técnicas" (2 ch, ES) = datasheet corto | OK |
| 56 | `aritech_ins570-8_combined` | Aritech | 20 | cbn | instalacion | ML-adv | "ARITECH Instruction Manual — 2000 Series Sounder-Beacons (EN Installation Manual… PL Podręcznik)" ; lang 12-idiomas → NO escrito | OK |
| 57 | `nc-mc-0-g-161721-es` (v1) | Aritech | 4 | cbn | datasheet | ML-adv | "NC-MC-0-G pulsador manual — Descripción + Especificaciones + compatibles" (4 ch, ES) = datasheet; lang [en,es] → NO escrito | OK |
| 58 | `nc-pf8-161721-es` | Kidde | 5 | cbn | datasheet | SG:es | "NC-PF8 central convencional 8 zonas — Descripción + Especificaciones" (5 ch, prosa ES) = datasheet | OK |
| 59 | `nc-pf8-sc-161721-es` | Kidde | 4 | cbn | datasheet | ML-adv | "NC-PF8-SC 8-zone panel — Overview + Especificaciones" (4 ch, EN/ES) = datasheet; lang [en,es] → NO escrito | OK |

## 4. Anotaciones — juicios de categoría adyacente y base de idioma

- **`doc_type` adyacentes (aceptados, no defectos).** Sin definiciones formales del enum
  (`instalacion|operacion|configuracion|datasheet|boletin|guia_usuario|mantenimiento|otro`), varios
  manuales de central cubren instalación+programación+operación. Se aceptó la etiqueta cuando
  describe fielmente el género real (criterio §5 de la attestation): p.ej. `configuracion` para
  manuales de PROGRAMACIÓN (#13/#14/#15 AM-81/82xx, #29 AgileIQ, #54 ID1000, #45 TCF-142-S);
  `operacion` para manuales de FUNCIONAMIENTO (#12 Pearl, #47/#48 G-500/G-100, #34 acciones-en-alarma);
  `guia_usuario` para docs auto-titulados "Manual de Usuario" (#16, #36, #40, #44, #53).
  **Ninguno es un error de categoría claro** (a diferencia del `datasheet` sobre manual de 118 pp que
  cazó el draw 2). El único caso examinado con lupa (#39 Mini-LaserStar, manual con sección de
  programación etiquetado `instalacion`) es adyacente y fiel al género de manual de detector.
- **`otro` (catch-all defendible):** #21 (FAQ de soporte "Cómo conectar una sirena") y #35
  (referencia de protocolo de comunicaciones AM2020) — documentos que no encajan en un género
  operativo específico. Correcto usar `otro`.
- **`language` singleton (33 filas): idioma de REDACCIÓN verificado**, no token suelto (lección
  MADT609 del draw 1). Ejemplos leídos: #12 → `es` (prosa "Manual de funcionamiento… acceder a los
  diferentes menús"); #11 → `en` (prosa "installation and user guide"); #24 no aplica (multi);
  #41 no aplica (multi). Las 33 SG son 0-defecto.
- **`language` multi (25) + contradicho (1): ADVISORY, NO se escriben.** Ortogonal al eje `doc_type`.
  El over-tag de idioma (clase MADT609) queda contenido aquí porque cae en multi-advisory.
- **`product_model` (invariante): NUNCA se escribe.** Verificado que la identidad gobernada coincide
  con el contenido en las 59 (corroborate = NO-OP; family = etiqueta gobernada conservada). El único
  ruido observado (#38 `brand=Pfannenberg` sobre un doc Notifier) NO afecta el fill porque el T2 no
  escribe `manufacturer`/`brand` ni `product_model` — solo `doc_type` y `language`.

## 5. Reproducibilidad / freeze

- Draw 3: `scripts/s282_qa_s83_lqas_draw3.py` (seed 593) → `evals/s282_qa_s83_lqas_draw3_bundle.json`
  (59 filas + muestra de contenido). READ-ONLY; SELECT `chunks_v2`; 0 escrituras; 0 modelo de pago.
- Cohorte v3: `evals/s282_qa_s83_result_v3.json` (guard 2× byte-idéntico, records-sha
  `2c6bac681ad89001`; frame == v2, sin drift).
- Corpus (freeze v2/v3): `chunks_v2`=25090 · `documents`=1171 · sha `aa13e792339f7d3e`.
- Worktree `Technical Bot-s281`, rama `claude/s282-h0t2-qa`. Sin commits.
