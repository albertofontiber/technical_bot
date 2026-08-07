# s303 — Cruce catálogo de portales (Notifier / Morley) × corpus `chunks_v2`

> Generado por `scripts/s303_cross_portal_corpus.py`. Resolución título→fichero por `scripts/s303_resolve_portal_filenames.py` (HEAD secuencial, 3 s entre peticiones, runbook `docs/CORPUS_NOTIFIER_MORLEY.md` §2).

**Cobertura del crawl: 835/835 enlaces únicos (100.0%).**

## 1. Cifras de cabecera

| | |
|---|---|
| Entradas del catálogo cosechado | 844 |
| Enlaces de descarga únicos | 835 |
| **Resueltos a nombre de fichero real** | **837** entradas (735 ficheros únicos) |
| Casan con el corpus | 751 entradas (666 ficheros únicos) |
| └ de ellos, otra edición/revisión (T3/T4) | 4 |
| **NO están en el corpus = lista de adquisición** | **69 ficheros únicos** (86 entradas) |
| └ **adquisición NETA** (el corpus no lo tiene en ningún idioma) | **43** |
| └ traducción de un documento que ya tenemos | 26 |
| Sin resolver | 7 |
| Docs del corpus alcanzados por el cruce | 663 / 1012 |
| Docs Notifier+Morley del corpus NO alcanzados | 131 / 705 |

**Cobertura del crawl por lote** (`manuales` = vigentes · `manuales-des` = descatalogados):

| Lote | Entradas | Resueltas |
|---|---|---|
| `morley/manuales` | 122 | 120 |
| `morley/manuales-des` | 58 | 58 |
| `notifier/manuales` | 375 | 371 |
| `notifier/manuales-des` | 289 | 288 |

**Motivos de «sin resolver»:**

- `sin enlace` — 7

**Reparto de la lista de adquisición:**

- por sitio: {'notifier': 57, 'morley': 12}
- **neta vs traducción**: 43 netos · 26 traducciones de algo ya presente
- por clase de documento: {'manual prog/config/puesta-en-marcha': 8, 'manual instalacion/uso/conexionado': 54, 'otro/indeterminado': 4, 'datasheet/certificado': 3}
- por idioma: {'es': 12, 'sin declarar': 4, 'pt': 34, 'multi (incl. es)': 12, 'en': 2, 'fr': 1, 'it': 3, 'de': 1}
- por categoría del portal: {'manuales': 45, 'manuales-des': 24} (`manuales` = vigente, `manuales-des` = descatalogado)

### Criterio de cruce (declarado)

Se compara el nombre de fichero servido por el portal contra los `source_file` **de los 1012 documentos** de `chunks_v2` (no solo los 705 de Notifier/Morley: un doc del portal puede estar en el corpus etiquetado con otro fabricante).

| Nivel | Regla | Lectura |
|---|---|---|
| **T1 exact** | nombre sin extensión, insensible a mayúsculas | mismo fichero |
| **T2 norm** | minúsculas + sin acentos + **solo alfanuméricos** (quita `-`, `_`, espacios, `.`) | mismo fichero, `MN-DT-200` ≡ `MNDT200` |
| **T3 revloose** | T2 tras podar sufijos de revisión FINALES (`rvNN`, `revX`, `vNN`, `issue N`, `_X`, `_copia`, `_lr`…) | mismo doc, edición quizá distinta |
| **T4 revagnostic** | quita **cualquier** token de revisión/fecha (`rev 5`, `09-07-2026`, `RevB`, `20July2015`, año suelto) y compara | mismo doc, **otra edición** |
| sin match | — | **candidato de adquisición** |

Sobre cada candidato sin match se corre además una **detección de gemelo**, que NO es un nivel de cruce (el fichero sigue sin estar en el corpus) sino una anotación de valor:

- `gemelo_es_en_corpus` — el mismo documento **en español** ya está en el corpus. Dos reglas, ambas verificadas contra el corpus: (1) el sufijo `P` pegado al número de documento HLSI marca la versión portuguesa (`MNDT250P` ↔ `MNDT250`, `MADT190P_02` ↔ `MADT190_02`); (2) en la gama de part-numbers `997-xxx-NNN-`, `-007-` es portugués y `-005-` español (comprobado con `997-670-007-3_Operating_PT` / `997-670-005-3_Operating_ES` y el par equivalente de `997-671`).
- `gemelo_otro_idioma_en_corpus` — quitando **todos** los marcadores de idioma a ambos lados, el nombre coincide con un documento del corpus (`Manual SIMEI-HLSI_FR-PT` ↔ `Manual SIMEI-HLSI_SP-EN`). Puede ser la misma edición española cuando es el nombre del corpus el que lleva el marcador (`HLSI-MA-025_rv03 Guia Rapida NFS_Supra` ↔ `HLSI-MA-025 Guia Rapida NFS_Supra_ES`).

Esa detección **no elimina nada de la lista**: mueve el candidato al bloque 2.B.

Decisiones explícitas de la normalización:

- **NO se podan los sufijos de idioma en los niveles T1–T4** (`_ES`, `_EN`, `_SP`, `_PT`): la versión española y la inglesa del mismo manual son ficheros **distintos** y podarlos habría hecho desaparecer candidatos legítimos del cruce. El idioma se trata aparte, en la detección de gemelo, que anota sin borrar.
- **NO se poda el sufijo `_NN` final.** En la nomenclatura HLSI es un **sub-número de documento**, no una revisión — verificado en el corpus: `MADT190_01`…`MADT190_15` son **13 documentos distintos** (`product_model` = ID²NET / ID3000 / LIB3000 / ID-CRA / PSU7A…). Una versión previa de este cruce sí lo podaba y fabricó un match falso (`MADT190P_02` → `MADT190P_01_C`), que habría borrado un candidato real de la lista.
- **Reparación de mojibake obligatoria.** Las cabeceras HTTP se decodifican en latin-1 (RFC 9110) pero el portal envía el nombre en UTF-8: `programación` llega como `programacioÌ\x81n`. Sin reparar el round-trip latin-1→utf-8, **todo fichero con acento falla el cruce y aparece como falso candidato de adquisición** (2 ficheros afectados aquí).

## 2. Lista de adquisición

**69 ficheros del portal no están en el corpus**, pero no todos valen lo mismo: **26 son la traducción de un documento que YA tenemos** (típicamente el sufijo `P` = portugués sobre el mismo número de documento HLSI: `MNDT250P` ↔ `MNDT250`). La adquisición **neta** son **43 ficheros** — es la lista 2.A.

Orden dentro de cada bloque: (a) manuales de programación/configuración/puesta en marcha por delante de instalación/uso, y estos por delante de hojas de datos y FAQ · (b) familias de las que el corpus ya tiene algo (columna «¿fam. ya a medias?») · (c) español > multilingüe > sin declarar > otros idiomas · (d) vigente > descatalogado.

### 2.A — ADQUISICIÓN NETA: 43 documentos que el corpus no tiene en ningún idioma

#### 2.A.1 Manuales de PROGRAMACIÓN · configuración · puesta en marcha · licencias — MÁXIMA PRIORIDAD — 3

| # | Título | Fichero | Idioma | Familia | ¿fam. ya a medias? | Tamaño | URL |
|---|---|---|---|---|---|---|---|
| 1 | PEARL. Guía para la introducción de licencias + formulario. | `Guia y formulario_Licencias Pearl_1114.pdf` | es | Sistemas analogicos | sí | 138 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2898&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=378dcebc738c420a219e473303e18795) |
| 2 | Manual Tecnico TG Notifier Version 9 | `3- TG-Honeywell_Tecnico_v9.0.pdf` | sin declarar | (sin familia) | sí | 5519 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5623&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=c1d134736d69cd903bac5ed61ab59501) |
| 3 | DX CONNEXION (DXc) Manual de configuração de la central DX Connexion | `DXc_Product manual_Portuguese.pdf` | pt | DX CONNEXION (DXc) Sistemas Analogicos | no | 3554 KB | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/DXc_Product%20manual_Portuguese.pdf) |

#### 2.A.2 Manuales de instalación · uso · conexionado · guías rápidas — 33

| # | Título | Fichero | Idioma | Familia | ¿fam. ya a medias? | Tamaño | URL |
|---|---|---|---|---|---|---|---|
| 4 | RP1r-Supra Etiqueta de instrucciones para las centrales de la Serie RP1r-Supra | `170019 02012012 ETIQUETA INSTRUCCIONES EXTINCION SUPRA REV A .pdf` | multi (incl. es) | Multilingue Sistemas de Extincion | sí | 146 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3095&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=3379f3c1846806976ab6f9f13ea10034) |
| 5 | W3A-Y000SG-K013-65 Instrucciones de instalación de los pulsadores de paro y disparo de extinción IP65 | `D 1128-1.pdf` | multi (incl. es) | Multilingue Sistemas de extincion | sí | 968 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3151&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=565db6a6c76e19fb7618ec11ef866dec) |
| 6 | RP1r-Supra Guide rapide_FR | `HLSI-MA-103_Guide rapide RP1r_Supra_FR.pdf` | sin declarar | Francia Sistemas de Extincion | sí | 974 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2884&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=6bb60ea48f27dee5ac73b062245f3461) |
| 7 | NFS-Supra Guíde rapide | `HLSI-MA-025 Guide rapide NFS_Supra_XP__FR version 03.pdf` | sin declarar | Francia Equipos Convencionales | sí | 632 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3029&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=4a552f851ae51bc6762ac511e137ab0c) |
| 8 | Manual Technician TG Notifier Version 9 | `3- TG-Honeywell_Technician_Eng_v9.0.pdf` | sin declarar | (sin familia) | sí | 5581 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5624&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=bb2d906b925f90c2b2d426cdcc1605f5) |
| 9 | ID3000 Panel Mounting Instructions for 19-Inch Rack | `997-421-000-3.pdf` | en | Sistemas Analogicos | sí | 508 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2886&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=d74e470a82e8136f29c1de643b6f7371) |
| 10 | ID3000 Manuel d'utilisation NF3000 | `NF3000_Manuel_d'utilisation_lr.pdf` | fr | Sistemas Analogicos | sí | 2430 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2880&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=6b9b6e171e77f48e415532ca4e693042) |
| 11 | RP1r-Supra Guida Rapida_IT | `HLSI-MA-103_ Guida Rapida RP1r_Supra_IT.pdf` | it | Sistemas de Extincion | sí | 1937 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2883&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=a56ecd7039ff0b388e032fb7854b2f22) |
| 12 | NFS-Supra Guida Rapida | `Guida_Rapida_NFS4_8-2Plus_ITA.pdf` | it | Equipos Convencionales | sí | 533 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3028&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=faae96f95057adce72c4694c53161655) |
| 13 | FAAST LT manual de instalação rápida | `I56-3947-201_PT Notifier Loop FAAST LT QIG.pdf` | pt | Equipos especiales | sí | 2160 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2948&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=e1ff644dd03a253ed37e9acbe7d09f97) |
| 14 | POL-200-TS. Benutzerhandbuch. Ring-Diagnose-Tool | `Anleitung-POL-200-TS V5_Nov20_DE.pdf` | de | Sistemas Analogicos | sí | 2437 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5454&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=c2d7fe3c8e0766388148761ca96efa19) |
| 15 | F5000 Guía rápida F5000 | `0034-033-01 Guide F5000 PT.pdf` | pt | F5000 | sí | 892 KB | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/0034-033-01%20Guide%20F5000%20PT.pdf) |
| 16 | F5000 Manual do utilizador F5000 | `0034-034-01 Manual F5000 PT.pdf` | pt | F5000 | sí | 1450 KB | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/0034-034-01%20Manual%20F5000%20PT.pdf) |
| 17 | FS20X Guia de Instalação e Manual Operacional. Detectores de Fogo e Chamas FS20X | `1998M0902_FS20X_PT-BR54-10_PT-BR_RevB_20July2015.pdf` | pt | Equipos especiales | sí | 3421 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2960&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=2a7b09c0e991e4778576c90c53b99709) |
| 18 | E-1330 Manual. Instrucciones Electroimanes 1330/1335/1340/1345 (portugués y español). | `MNDT1102.pdf` | es | Accesorios | no | 188 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2929&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=9c4277fe9bb6a5401f9cb7ff703647f0) |
| 19 | EC-1351 Manual. Instrucciones Electroimanes 1350/1360 (portugués y español) | `MNDT1103.pdf` | es | Accesorios | no | 117 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2931&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=eb4fc7cb292381b04cad29ce1d1ea1ef) |
| 20 | EPS-1369 Manual. Instrucciones Electroimán 1369 (portugués y español) | `MNDT1105.pdf` | es | Accesorios | no | 311 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2934&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=fde1dc1e8e05b46c7429121a8ebc7286) |
| 21 | ES15/1370 Manual. Instrucciones Electroimanes 1370/1380 (portugués y español) | `MNDT1104.pdf` | es | Accesorios | no | 335 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2937&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=979a1feb207384b9d33e47ec6b9bc9c0) |
| 22 | RP1r Anexo RP1r. Conexionado de la placa y descripción de los bloques de terminales | `HLSI_MA102.pdf` | es | Sistemas de extincion | no | 171 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3087&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=b0623f9c464c54441b311060e36cd06b) |
| 23 | RPS-1388 Manual. Instrucciones electroimanes RPS-1388, RPS-1392, RPS-1395. Español y portugués | `MNDT1100.pdf` | es | Accesorios | no | 124 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3097&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=b6dbbbd3b162e3c77b94c58a5308e597) |
| 24 | Manual de Instrucções par a instalação, colocação em serviço, Central G-10, Detector NCO-10 | `MNDT510P.pdf` | pt | Deteccion de gas | sí | 1472 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3980&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=1236d897f811729773055d0d2749ea7a) |
| 25 | Manual de instalação, colocação em serviço e funcionamento, FS-8 | `MNDT012P.pdf` | pt | Sistemas Convencionales | sí | 1763 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4004&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=6d8ad55be279641a3634f87c6997a703) |
| 26 | Manual. Instrucciones Panel luminoso PAN-1 (Art. 5054/5064) (portugués y español) | `MNDT1116.pdf` | es | Extincion | no | 102 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4140&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=443d430293b295db711cc902a562f472) |
| 27 | Manual. Instrucciones electroimanes 1315/1316 (portugués y español) | `MNDT1101.pdf` | es | Accesorios | no | 102 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4137&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=7f764f799adaf91995b44628f3da83ee) |
| 28 | CWST-RW-S5/W5 Instrucciones de instalación multinlingüe del flash de la gama ENscape | `D 1102-7 Beacon_Multi.pdf` | multi (incl. es) | Multilingue Equipos Convencionales | no | 1281 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2922&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=bd031b1ced231319a1115b0408a75728) |
| 29 | HSR-E24 Instrucciones de instalación de las sirenas de exterior HSR-E24 (multilingüe) | `HSR-E24_Multi.pdf` | multi (incl. es) | Multilingue Equipos Convencionales | no | 20 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2968&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=f691eaf42de0672023f5b69d00c3fbf3) |
| 30 | HSR-INT24 Instrucciones de instalación de las sirenas de interior HSR-INT24 (multilingüe) | `HSR-INT24_Multi.pdf` | multi (incl. es) | Multilingue Equipos Convencionales | no | 19 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2969&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=cd8212a4d22e95913a3b6b06b7333763) |
| 31 | IRK-2E Instrucciones de instalación del indicador remoto IRK-2E (multilingüe) | `IRK-2E.pdf` | multi (incl. es) | Multilingue Accesorios | no | 245 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2992&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=3ea8e38a26ab6c3ce3c24f44176c4615) |
| 32 | LT-32 / LT-159 Manuales en varios idiomas de la central Morley-IAS Lite | `Docs Morley-IAS Lite&Plus - QR.pdf` | multi (incl. es) | Multilingue | no | 80 KB | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/Docs%20Morley-IAS%20Lite&Plus%20-%20QR.pdf) |
| 33 | Instrucciones de instalación (multilingüe) IRK-E-SI | `IRK-E-SI.pdf` | multi (incl. es) | Multilingue Accesorios | no | 125 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3962&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=0c053f55544ffb8127df02a35e9e6131) |
| 34 | 2470-2480 Installation instructions | `2470-2480 Pulsador.pdf` | en | Equipos Convencionales | no | 126 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3884&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=30cadd2021d5ff8886e46d8b4707152c) |
| 35 | DX CONNEXION (DXc) Manual de utilizador de DXc | `DXc_Manual de utilizador.pdf` | pt | DX CONNEXION (DXc) Sistemas Analogicos | no | 4332 KB | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/DXc_Manual%20de%20utilizador.pdf) |
| 36 | Manual de Funcionamento, instalação e colocação em serviço e formulário de registo local FS 1-4 | `MNDT010P.pdf` | pt | Sistemas Convencionales | no | 663 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3993&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=53c618d26a3652ab16895e760f51bdf0) |

#### 2.A.3 Documentos sin señal clara en el título — 4

| # | Título | Fichero | Idioma | Familia | ¿fam. ya a medias? | Tamaño | URL |
|---|---|---|---|---|---|---|---|
| 37 | RP1r-Supra Etiqueta de leds y teclas de la central de la Serie RP1r-Supra | `170020 21122011 TARJETAS IDIOMAS EXTINCION SUPRA REV A.pdf` | multi (incl. es) | Multilingue Sistemas de Extincion | sí | 71 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3096&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=dec22cfa2189e5cf6f6f885490d55885) |
| 38 | FAAST XS Detección de humo por aspiración (7100XE) (Multilingüe) | `I56-0501-001_FAAST 7100E_Multi.pdf` | multi (incl. es) | Multilingue Equipos especiales | sí | 1852 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2950&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=3357799520ae96cbffbd97788d31e2f1) |
| 39 | Detectores LaserStar en ambientes muy húmedos. | `MADT731_03_A.pdf` | es | Equipos especiales | no | 139 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3927&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=7d37d6d40fcce710e9eec7b2ecb80bf0) |
| 40 | IIG4 IIG4N INTERFACCIA GAS CON COMPONENTI SMD | `IIG4+IIG4N-ITAa4.pdf` | it | Deteccion de gas | no | 1465 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2987&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=51d755526e32606697a81ab4a91842c0) |

#### 2.A.4 Hojas de datos · certificados · catálogos — 3

| # | Título | Fichero | Idioma | Familia | ¿fam. ya a medias? | Tamaño | URL |
|---|---|---|---|---|---|---|---|
| 41 | SMART3 GC2 Instrucciones de seguridad para los detectores de gas SMART 3 (SERIE ST), CERTIFICADO CESI02ATEX084 (español e inglés) | `MNDT621.pdf` | multi (incl. es) | Multilingue Deteccion de gas | sí | 110 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3120&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=f8b967196f99f6b3021211cb62a30653) |
| 42 | MMT Hoja técnica del módulo analógico con entrada 4-20mA | `S-589-1_MMT_ESP-ENG.pdf` | es | Deteccion de gas | no | 510 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3024&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=e72a67bdade6368079394eb28e79328b) |
| 43 | NFXI-WSF-WC Características técnicas de los dispositivos óptico-acústicos, serie NFXI-WS/WSF | `D1058-1_NFXI-WS-WSF.pdf` | multi (incl. es) | Multilingue Sistemas analogicos | no | 1993 KB | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3060&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=68ba30f34f9ebe256039254d989a9a5c) |

### 2.B — BAJA PRIORIDAD: 26 traducciones de documentos que ya están en el corpus

Mismo documento, otra edición idiomática. Para un bot que responde en español a técnicos españoles el valor marginal es casi nulo; se listan por completitud y porque alguna podría servir si la versión española que tenemos está incompleta o mal extraída.

| # | Título | Fichero | Idioma | Ya en el corpus como | URL |
|---|---|---|---|---|---|
| 1 | NFS-Supra Guía Rápida | `HLSI-MA-025_rv03 Guia Rapida NFS_Supra.pdf` | es | `HLSI-MA-025 Guia Rapida NFS_Supra_ES` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3027&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=fe2ca823bec6c89eb0f317fc665e7f6a) |
| 2 | SIMEI Caixa Estanque IP65 para proteger botões de emergência | `Manual SIMEI-HLSI_FR-PT.pdf` | pt | `Manual SIMEI-HLSI_SP-EN` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2899&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=5954b1e6c69154a6463aaa63bfa9fad2) |
| 3 | Manual de funcionamento do detector de gases inflamáveis EzSense | `12484_Ezsense_Ops Manual_PT.pdf` | pt | `12484_Ezsense_Ops Manual_EN` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3990&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=c9c0a0f6223dd1489161806a296b9f6e) |
| 4 | VSN-LT Manual de instalação, configuração e funcionamento VSN-LT | `MIEMI580P.pdf` | pt | `MIE-MI-580` | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/MIEMI580P.pdf) |
| 5 | VSN-PLUS Manual de instalação, configuração e funcionamento VISION PLUS | `MIE-MI-130P.PDF` | pt | `MIEMI130` | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/MIE-MI-130P.PDF) |
| 6 | INSPIRE - Licenciamento de Centrais INSPIRE v. 1.35 | `4188-1125-PT- issue 4_11-2025_Li.pdf` | pt | `4188-1125-ES issue 5_11-2025_Li` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5568&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=3eb698c7d26301cd2ed83bd84cad9726) |
| 7 | Manual do Utilizador e Programação de la AM6000 | `MNDT250P.pdf` | pt | `MNDT250` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4115&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=15e9423e249a121946366d2a368b57b9) |
| 8 | Manual técnico e de utilizador. Central para a detecção de gases PL4. Rev 0 | `MNDT515P.pdf` | pt | `MNDT515` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4123&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=a56f3866fff2d9cde8f1bd6ba7d014b0) |
| 9 | ID3000 Ligações da Placa Isolada RS232 com PC/Impressora | `MADT190P_02.pdf` | pt | `MADT190_02` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2877&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=b96888daa9b5ed9b1d30a23b4d207d7f) |
| 10 | ID3000 Manual de funcionamento. Portugués. | `MFDT190P.pdf` | pt | `MFDT190` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2875&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=c675857ae1a1e03d03d88a646a550f4c) |
| 11 | PEARL. Manual de instalação da central PEARL | `997-669-007-3_Instal-Comm_PT.pdf` | pt | `997-669-005-3_Instal-Comm_ES` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=2889&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=d66a24809dc7867422560b19d33f9f00) |
| 12 | AUTOSAT-10 Manual de utilizador AutoSAT-10 | `MNDT1310P.pdf` | pt | `MNDT1310` | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/MNDT1310P.pdf) |
| 13 | AUTOSAT-20 Manual de utilizador AutoSAT-20 | `MNDT1311P.pdf` | pt | `MNDT1311` | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/MNDT1311P.pdf) |
| 14 | INSPIRE - Manual de cibersegurança | `4188-1122-PT issue 3_04-2025_Cyb.pdf` | pt | `4188-1122-ES issue 4_04-2025_Cyb` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5543&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=2e7f4aec31b6e48b99e5b057a2a36a20) |
| 15 | VSN Park Manual de instalação e funcionamento VSN Park | `MIE-MI-591P.pdf` | pt | `MIE-MI-591` | [descargar](https://www.morley-ias.es/documentacion/morley/manuales/MIE-MI-591P.pdf) |
| 16 | Manual de Instrucções de instalação de impressora da AFP4000. | `MADT236P.pdf` | pt | `MADT236` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4063&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=afbc856ee1b570f054be3cfa9eaccac9) |
| 17 | Manual de funcionamento, ID50. Ver.4,x | `MFDT155P.pdf` | pt | `MFDT155` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3992&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=29d96805a40307756797875ffbc6e16a) |
| 18 | Manual de funcionamento, ID2000 | `MFDT180P.pdf` | pt | `MFDT180` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3991&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=b2cbc6d404a4d87613c849448669bfe2) |
| 19 | NFS8REL Instalação da placa de relé de 8 saídas NFS8REL. | `MIE-MA-100_02P.pdf` | pt | `MIE-MA-100_02` | [descargar](https://www.morley-ias.es/documentacion/morley/manualesdes/MIE-MA-100_02P.pdf) |
| 20 | Manual de utilizador NAS-10 | `MNDT747P.pdf` | pt | `MNDT747` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4108&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=f76b0b7afc4b7b2c37ca3505c4a2d3c4) |
| 21 | Manual de utilizador NAS-20 | `MNDT748P.pdf` | pt | `MNDT748` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4109&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=38ab47c7edf28c2f61a79a3409ecdb42) |
| 22 | Manual de utilizador de la central convencional AM-200 | `MNDT105P.pdf` | pt | `MNDT105_A` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4107&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=0fa74ee7cc922c06ef69ea9c31cb47d1) |
| 23 | Manual módulo de 10 relés de saída para sistemas analógicos de 2 fios. CMX-10R | `MNDT1001P.pdf` | pt | `MNDT1001` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4120&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=11caee54afb2e6e57bde3fb57b3808ce) |
| 24 | Manual placa 10 entradas N-A. para loop analógico. MMX-10. | `MNDT1002P.pdf` | pt | `MNDT1002` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4122&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=6b4380c5967a15b0d88d896df02b4b04) |
| 25 | Manual de Instrucções. Detector de gás serie Doméstica (CAT/220; CAT/12; COMBIX/ | `MNDT655P.pdf` | pt | `MNDT655` | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3981&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=51ec06ae91ed1d33bc45f25fcc87c4a4) |
| 26 | ZXR-5B/4B Manual de instalación MIE. ZXR-5B/4B | `MIEMI430P.pdf` | pt | `MIE-MI-430` | [descargar](https://www.morley-ias.es/documentacion/morley/manualesdes/MIEMI430P.pdf) |

## 3. Anexo — ya en el corpus pero el portal sirve OTRA edición (T3/T4)

No son adquisición (el documento ya está), son **actualización**: merece la pena re-descargar y re-ingerir si la edición del portal es más reciente.

| Fichero en el portal | Doc en el corpus | Nivel | URL |
|---|---|---|---|
| `AM-8100 manual de usuario y programación rev 5 09-07-2026.pdf` | `AM-8100 manual de usuario y programacion rev 4 30-10-2024` | T4_revagnostic | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5555&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=047487f5ced3461d3f0d9684cbb7ed8b) |
| `AM-8200N manual de usuario y programación rev 4 09-07-2026.pdf` | `AM-8200N manual de usuario y programacion rev 3 30-10-2024` | T4_revagnostic | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=5550&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=eaac7696553a95ff93c2b6c1de4bbf0e) |
| `HLSI-MN-025_rv05 NFS Supra.pdf` | `HLSI-MN-025_NFS Supra` | T4_revagnostic | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=3033&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=bd1e6d882c774427a7291b4efdbca16b) |
| `MNDT710.pdf` | `MNDT710_B` | T3_revloose | [descargar](https://www.notifier.es/index.php/component/zoo/?task=callelement&format=raw&item_id=4050&element=5d300a7a-0c77-4671-bce0-fec5f09d447b&method=download&args[0]=0672d55814dea5a76a701b0536d237df) |

## 4. Falsos positivos y falsos negativos del cruce (incertidumbre declarada)

### 4.1 Candidatos con un vecino MUY parecido en el corpus

Estos entran en la lista de adquisición, pero su nombre normalizado se parece ≥0.85 (difflib) a un documento que YA tenemos. Puede ser el mismo documento renombrado (→ falso candidato) o un producto hermano (→ candidato legítimo). **Requieren ojo humano.** Aviso: en códigos cortos tipo `MNDT1102` el ratio de difflib es engañosamente alto (`MNDT1102` vs `MNDT110` = 0.93 y son documentos distintos).

| Bloque | Candidato del portal | Vecino en el corpus | ratio |
|---|---|---|---|
| 2.A | `NF3000_Manuel_d'utilisation_lr.pdf` | `NF30-50_Manuel_d'utilisation_lr` | 0.962 |
| 2.B | `MIE-MA-100_02P.pdf` | `MIE-MA-100_02` | 0.952 |
| 2.A | `1998M0902_FS20X_PT-BR54-10_PT-BR_RevB_20July2015.pdf` | `1998M0901_FS24X_PT-BR54-10_PT-BR_RevB_20July2015` | 0.95 |
| 2.B | `MADT190P_02.pdf` | `MADT190_02` | 0.947 |
| 2.B | `MIEMI580P.pdf` | `MIE-MI-580` | 0.941 |
| 2.B | `MIE-MI-130P.PDF` | `MIEMI130` | 0.941 |
| 2.B | `MNDT1310P.pdf` | `MNDT1310` | 0.941 |
| 2.B | `MNDT1311P.pdf` | `MNDT1311` | 0.941 |
| 2.B | `MIE-MI-591P.pdf` | `MIE-MI-591` | 0.941 |
| 2.B | `MNDT1001P.pdf` | `MNDT1001` | 0.941 |
| 2.B | `MNDT1002P.pdf` | `MNDT102P` | 0.941 |
| 2.B | `MIEMI430P.pdf` | `MIE-MI-430` | 0.941 |
| 2.A | `MNDT1102.pdf` | `MNDT112` | 0.933 |
| 2.A | `MNDT1103.pdf` | `MNDT110` | 0.933 |
| 2.A | `MNDT1105.pdf` | `MNDT110` | 0.933 |
| 2.A | `MNDT1104.pdf` | `MNDT110` | 0.933 |
| 2.A | `MNDT1100.pdf` | `MNDT110` | 0.933 |
| 2.A | `MNDT1101.pdf` | `MNDT110` | 0.933 |
| 2.B | `MNDT250P.pdf` | `MNDT250` | 0.933 |
| 2.B | `MNDT515P.pdf` | `MNDT515` | 0.933 |
| 2.B | `MFDT190P.pdf` | `MFDT190` | 0.933 |
| 2.B | `MADT236P.pdf` | `MADT236` | 0.933 |
| 2.B | `MFDT155P.pdf` | `MFDT155` | 0.933 |
| 2.B | `MFDT180P.pdf` | `MFDT180` | 0.933 |
| 2.B | `MNDT747P.pdf` | `MNDT747` | 0.933 |
| 2.B | `MNDT748P.pdf` | `MNDT748` | 0.933 |
| 2.B | `MNDT655P.pdf` | `MNDT655` | 0.933 |
| 2.B | `12484_Ezsense_Ops Manual_PT.pdf` | `12484_Ezsense_Ops Manual_EN` | 0.913 |
| 2.A | `3- TG-Honeywell_Tecnico_v9.0.pdf` | `Tg-Honeywell_Tecnico` | 0.9 |
| 2.B | `HLSI-MA-025_rv03 Guia Rapida NFS_Supra.pdf` | `HLSI-MA-025 Guia Rapida NFS_Supra_ES` | 0.9 |
| 2.A | `HLSI-MA-103_ Guida Rapida RP1r_Supra_IT.pdf` | `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` | 0.889 |
| 2.B | `4188-1122-PT issue 3_04-2025_Cyb.pdf` | `4188-1122-ES issue 4_04-2025_Cyb` | 0.88 |
| 2.A | `MNDT510P.pdf` | `MNDT530P` | 0.875 |
| 2.A | `MNDT012P.pdf` | `MNDT102P` | 0.875 |
| 2.A | `MNDT1116.pdf` | `MNDT1311` | 0.875 |
| 2.A | `MNDT010P.pdf` | `MNDT102P` | 0.875 |
| 2.B | `4188-1125-PT- issue 4_11-2025_Li.pdf` | `4188-1125-ES issue 5_11-2025_Li` | 0.875 |
| 2.B | `MNDT105P.pdf` | `MNDT105_A` | 0.875 |
| 2.B | `997-669-007-3_Instal-Comm_PT.pdf` | `997-669-005-3_Instal-Comm_ES` | 0.864 |
| 2.A | `HLSI-MA-103_Guide rapide RP1r_Supra_FR.pdf` | `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` | 0.857 |
| 2.A | `MNDT621.pdf` | `MNDT651` | 0.857 |

### 4.2 Gemelos que el cruce NO detecta — verificados a mano

Casos que **ninguna regla automática empareja** pero que al mirar el corpus a mano sí tienen equivalente. Los cuatro primeros siguen en 2.A y, en rigor, deberían leerse como 2.B: **la adquisición neta real es de 43 menos ~6 ficheros**. Se declaran uno a uno en lugar de añadir más heurística frágil.

| Candidato en 2.A | Equivalente encontrado a mano en el corpus | Lectura |
|---|---|---|
| `1998M0902_FS20X_PT-BR54-10_PT-BR_RevB_20July2015.pdf` | `1998M0902_FS20X_ES_AR54-10_ES_AR_RevB_20July2015` | MISMO documento, edición ES-AR ya en corpus → traducción, no adquisición |
| `DXc_Product manual_Portuguese.pdf / DXc_Manual de utilizador.pdf` | `DXc_Manual de configuracion · DXc_Manual de usuario` | el corpus tiene el manual DXc en español (config + usuario) → probable traducción |
| `0034-033-01 Guide F5000 PT.pdf / 0034-034-01 Manual F5000 PT.pdf` | `0044-033-01 Guia F5000 · F5K-2H-UserGuide-SPANISH_Manual F5000` | el corpus tiene guía y manual F5000 en español (otro nº de parte) → probable traducción |
| `3- TG-Honeywell_Technician_Eng_v9.0.pdf` | `Tg-Honeywell_Tecnico` | versión inglesa; el corpus tiene la española (edición anterior) → baja prioridad |
| `MNDT105P.pdf (ya en 2.B)` | `MNDT105_A` | el gemelo ES lleva sufijo `_A`; sólo lo empareja el nivel T3 |

El caso `3- TG-Honeywell_Tecnico_v9.0` es el contrario y por eso encabeza 2.A: no es una traducción, es la **versión 9 de un manual técnico del que el corpus tiene una edición anterior sin numerar**. El prefijo `3- ` y el `_v9.0` impiden que T4 lo empareje.

### 4.3 Límites conocidos del criterio

1. **El cruce es por NOMBRE DE FICHERO, no por contenido.** Si el mismo PDF vive en el corpus bajo un nombre completamente distinto (p. ej. descargado en su día de otra fuente o renombrado a mano), este cruce lo declara «no en corpus» y es un **falso candidato**. No se ha hecho ninguna comparación de contenido ni de hash.
2. **131 de los 705 documentos Notifier/Morley del corpus no los alcanza ningún fichero del catálogo.** Eso acota el tamaño del problema anterior: buena parte del corpus procede de nombres que estos portales hoy no sirven (descatalogados retirados, material de distribuidor, FAQ del gestor de contenidos, renombrados). Cualquiera de esos podría ser el gemelo renombrado de un candidato.
3. **Documentos multilingües.** Un `_Multi` del portal puede contener el español que ya tenemos en un PDF monolingüe con otro nombre. El cruce no lo detecta.
4. **La clase del documento se infiere del TÍTULO** (palabras clave prog/config vs hoja de características). Los títulos escuetos caen en «sin clasificar» — la prioridad de esa sección es orientativa, no verificada.
5. **«¿fam. ya a medias?»** se calcula con tokens con pinta de código de producto extraídos del título, contrastados contra los nombres de fichero y el `product_model` del corpus. Es una heurística léxica: no distingue `ZXSe` de `ZXe`, ni sabe que FAAST LT-200 y FAAST 7100 son familias distintas.

## 5. Lo que NO se ha verificado

- **No se ha descargado ningún PDF.** Solo se leyeron cabeceras (HEAD). Por tanto **no está verificado que el fichero servido sea legible, ni que su contenido corresponda al título del índice**, ni su número de páginas.
- **7 entradas del catálogo no traían enlace de descarga** en la cosecha: existen en el índice, pero su fichero no se puede resolver sin re-visitar el portal. Se listan porque alguna es material de interés:

| Sitio | Cat. | Título | Meta |
|---|---|---|---|
| notifier | manuales | CR-6EA INFORMACIÓN TÉCNICA. Incompatibilidad de los módulos SC-6, CZ-6, CR-6, IM-10 con la central ID1000 con tarjetas de lazo con software 15.3 ó 16.5 | Español Sistemas Analógicos |
| notifier | manuales | CZ6 INFORMACIÓN TÉCNICA. Incompatibilidad de los módulos SC-6, CZ-6, CR-6, IM-10 con la central ID1000 con tarjetas de lazo con software 15.3 ó 16.5 | Español Sistemas Analógicos |
| notifier | manuales | NBS4 Installation instructions for wall mount sounders D686 DBS1224B4W (NBS4) | Inglés Equipos Convencionales |
| notifier | manuales | SC6 INFORMACIÓN TÉCNICA. Incompatibilidad de los módulos SC-6, CZ-6, CR-6, IM-10 con la central ID1000 con tarjetas de lazo con software 15.3 ó 16.5 | Español Sistemas Analógicos |
| notifier | manuales-des | TG-NOTIFIER Configuration Guide | Inglés Sistemas Analógicos |
| morley | manuales | LX300 Instrucciones de instalación y mantenimiento del detector de humo por rayo MI-LPB2 | Español LX300 Sistemas Analógicos |
| morley | manuales | TG-IP-1 Manual de usuario del módulo convertidor TG-IP-1 | Español TG-IP-1 Sistemas analógicos |

- **Licencia**: accesible ≠ redistribuible. Los términos de ambos portales no se han revisado (mismo límite declarado en el runbook §6).
- **Vigencia del enlace**: los 659 enlaces de Notifier son del componente ZOO y llevan un hash por ítem — si el portal regenera contenidos, caducan. Los 178 de Morley son URLs directas al fichero y son más estables, pero dependen de que no se reorganice la carpeta. La lista es un activo CON FECHA (7-ago-2026).

### Artefactos y reproducibilidad

- `evals/s303_cruce_portales_corpus_v1.json` — datos completos: los 751 que sí casan, los 69 candidatos con todos sus campos, los no resueltos y los 131 docs del corpus que el catálogo no alcanza.
- `data/catalog_portales/s303_resolved_filenames_v1.json` — la resolución URL→nombre-de-fichero de los 835 enlaces (cabeceras crudas, tamaños, método). **`data/` está en `.gitignore`**: este fichero vive solo en disco, no en el repo. Reconstruirlo cuesta 45 min de crawl.
- `data/catalog_portales/s303_corpus_source_files.json` — foto de los 1012 `source_file` de `chunks_v2` con `manufacturer`/`doc_type`/`language`/`product_model` (también fuera del repo).
- Rehacer el cruce sin volver a tocar los portales: `python scripts/s303_cross_portal_corpus.py` (solo lee ficheros locales).
