# s288 A-CORE — F0 census v2 — v2

Instrumento: `scripts/s288_acore_census_v2.py`. **READ-ONLY (solo GET de PostgREST), SELECT-only, 0 escrituras, 0 llamadas a modelos, coste $0.** Implementa F0(a)-(g) del spec SELLADO `evals/s288_acore_design_brief_v1.md` (v3). Hereda el stack GET-only + paginacion ordenada + contrato de determinismo 2x + freeze-contract de `scripts/s281_h0_identity_census.py` (artefactos s281 intocados).

## Freeze-contract

- commit HEAD: `41be442b87a6a0e512dfd572bac0e6c44e3b9903` (worktree dirty: True)
- CHUNKS_TABLE forzado: `chunks_v2`
- spec: `evals/s288_acore_design_brief_v1.md` sha256-LF `1c1a65088681f6a37d5dcc87c7cd6a921d6ca32ab25364fe569b208fe75edc39`
- blob root (solo lectura): `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot`
- fingerprint de corpus: documents=1169 · chunks_v2=25088 · chunks_v2_hyq=70126 · sha256 `744f21af87de1df9bbd10ae06ec57d0d38d927fcff445fa2a1f0e5954cfff2b5`
- manifest de blobs: `evals/s288_acore_blob_manifest_v2.jsonl` sha256-LF `b20892c50853a1abe4f72fba34870a11b745e9ec81d882a375fd573f6bac555c`
- packet QA-30 de P-B (adjudicacion humana): `evals/s288_acore_pB_qa30_v2.md`
- **determinismo 2x: IDENTICO ✅** (pass1 `fcb4aad9fdb88ed7` vs pass2 `fcb4aad9fdb88ed7`; ambas pasadas RE-LEEN la DB; el hash de los PDFs se calcula UNA vez y se reusa — los bytes en disco no cambian entre pasadas, declarado)
- generado 2026-07-30T21:18:14.094589+00:00

## 0. GATE F0 (spec §F0)

| Condicion del gate | Estado |
|---|---|
| determinismo 2x byte-identico | ✅ SI |
| particion suma 1169 | ✅ SI (suma=1169) |
| H1 explicito | **H1_CONFIRMADA** (60/60 match, 0 mismatch) |
| (e)(ii) acuerdo es/en >= 99% | ❌ NO (98.97%) |
| (e)(i) procedencia de labels documentada | ver §5.3 (scan reproducible + veredicto honesto) |
| (e)(iii) QA 30/30 con HALT | **ABIERTO** — la muestra se EMITE (§5.5) pero exige juicio humano; este instrumento es $0/read-only y NO la adjudica |

## 1. (a) Manifest de blobs locales

- PDFs hasheados: **1323** (1.55 GB) · errores de lectura: 0
- PDFs EXCLUIDOS por vivir bajo `logs/`: 11 (reconciliacion con el spec §1, que cita 1.334: 1323 fuera de `logs/` — todos bajo `Manuales_*` — + 11 en `logs/` = 1334)
- stems distintos: 1123 · **stems DUPLICADOS entre carpetas: 149** -> el indice por stem es MULTI-VALOR
- shas distintos: 1070 · shas duplicados (mismo fichero en 2+ carpetas): 182

Top stems duplicados:

| stem | n | paths |
|---|---:|---|
| `ASD Cold Environments_SP` | 4 | `Manuales_Morley/ASD Cold Environments_`, `Manuales_Morley_Privado/ASD Cold Envir`, `Manuales_Notifier/ES/ASD Cold Environm`, `Manuales_Notifier_Privado/ASD Cold Env` |
| `ASD Harsh Environments_SP` | 4 | `Manuales_Morley/ASD Harsh Environments`, `Manuales_Morley_Privado/ASD Harsh Envi`, `Manuales_Notifier/ES/ASD Harsh Environ`, `Manuales_Notifier_Privado/ASD Harsh En` |
| `Enlace entre TG` | 4 | `Manuales_Morley/Enlace entre TG.pdf`, `Manuales_Morley_Privado/Enlace entre T`, `Manuales_Notifier/ES/Enlace entre TG.p`, `Manuales_Notifier_Privado/Enlace entre` |
| `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` | 4 | `Manuales_Morley/HLSI-MA-103_GuiaRapida`, `Manuales_Morley_Privado/HLSI-MA-103_Gu`, `Manuales_Notifier/ES/HLSI-MA-103_GuiaR`, `Manuales_Notifier_Privado/HLSI-MA-103_` |
| `HLSI-MA-192_05 Guia Rapida UCIP GPRS_SP` | 4 | `Manuales_Morley/HLSI-MA-192_05 Guia Ra`, `Manuales_Morley_Privado/HLSI-MA-192_05`, `Manuales_Notifier/ES/HLSI-MA-192_05 Gu`, `Manuales_Notifier_Privado/HLSI-MA-192_` |
| `HLSI-MA-192_05 Quick Start Guide UCIP GPRS_G` | 4 | `Manuales_Morley/HLSI-MA-192_05 Quick S`, `Manuales_Morley_Privado/HLSI-MA-192_05`, `Manuales_Notifier/EN_unico/HLSI-MA-192`, `Manuales_Notifier_Privado/HLSI-MA-192_` |
| `HLSI-MN-103I_RP1r-Supra_lr` | 4 | `Manuales_Morley/HLSI-MN-103I_RP1r-Supr`, `Manuales_Morley_Privado/HLSI-MN-103I_R`, `Manuales_Notifier/EN_unico/HLSI-MN-103`, `Manuales_Notifier_Privado/HLSI-MN-103I` |
| `HLSI-MN-103_RP1r-Supra_lr` | 4 | `Manuales_Morley/HLSI-MN-103_RP1r-Supra`, `Manuales_Morley_Privado/HLSI-MN-103_RP`, `Manuales_Notifier/ES/HLSI-MN-103_RP1r-`, `Manuales_Notifier_Privado/HLSI-MN-103_` |
| `HLSI-MN-192_UCIP` | 4 | `Manuales_Morley/HLSI-MN-192_UCIP.pdf`, `Manuales_Morley_Privado/HLSI-MN-192_UC`, `Manuales_Notifier/ES/HLSI-MN-192_UCIP.`, `Manuales_Notifier_Privado/HLSI-MN-192_` |
| `HLSI-MN-963_POL-200-TS` | 4 | `Manuales_Morley/HLSI-MN-963_POL-200-TS`, `Manuales_Morley_Privado/HLSI-MN-963_PO`, `Manuales_Notifier/ES/HLSI-MN-963_POL-2`, `Manuales_Notifier_Privado/HLSI-MN-963_` |

**Convencion de stem (desviacion declarada #1):** blobs con extension no-lowercase: 10 · doc-stems que difieren entre la regla case-SENSITIVE de `canonical_blob_stem` y la case-INSENSITIVE usada aqui: 4 · docs que ganarian stem-match SOLO con casefold del cuerpo (informativo, NO usado): 0.

## 2. (b) Particion exhaustiva de los documentos

Suma de celdas = **1169** / 1169 documentos (✅ EXHAUSTIVA). Celdas no vacias: 21.

### 2.1 Marginales

- **status**: `active`=995 · `retired`=91 · `needs_review`=79 · `superseded`=4
- **clase de sha**: `placeholder`=744 · `real_64hex`=425
- **binding (extracciones)**: `single_extraction`=1002 · `sin_chunks`=164 · `multi_extraction`=3
- **binding check**: `n/a`=754 · `binding_ok`=414 · `binding_mismatch`=1
- **lineage**: `null`=1160 · `not_null`=9
- **language**: `null`=769 · `es`=326 · `en`=63 · `otro`=11
- **blob local**: `dual_stem_y_sha`=1012 · `solo_stem`=157

### 2.2 Celdas (status x clase-sha x binding x binding-check x lineage x language x blob-local)

| status | sha | binding | check | lineage | lang | blob local | n |
|---|---|---|---|---|---|---|---:|
| active | placeholder | single_extraction | n/a | null | null | dual_stem_y_sha | 385 |
| active | real_64hex | single_extraction | binding_ok | null | null | dual_stem_y_sha | 213 |
| active | real_64hex | single_extraction | binding_ok | null | es | dual_stem_y_sha | 169 |
| active | placeholder | single_extraction | n/a | null | es | dual_stem_y_sha | 145 |
| retired | placeholder | sin_chunks | n/a | null | null | solo_stem | 84 |
| needs_review | placeholder | sin_chunks | n/a | null | null | solo_stem | 70 |
| active | placeholder | single_extraction | n/a | null | en | dual_stem_y_sha | 52 |
| active | real_64hex | single_extraction | binding_ok | null | en | dual_stem_y_sha | 10 |
| active | real_64hex | single_extraction | binding_ok | null | otro | dual_stem_y_sha | 8 |
| active | real_64hex | single_extraction | binding_ok | not_null | es | dual_stem_y_sha | 6 |
| retired | real_64hex | sin_chunks | n/a | null | null | dual_stem_y_sha | 6 |
| needs_review | real_64hex | sin_chunks | n/a | null | null | dual_stem_y_sha | 4 |
| needs_review | real_64hex | single_extraction | binding_ok | null | null | dual_stem_y_sha | 4 |
| active | placeholder | single_extraction | n/a | null | otro | dual_stem_y_sha | 3 |
| superseded | real_64hex | single_extraction | binding_ok | not_null | es | dual_stem_y_sha | 3 |
| active | placeholder | multi_extraction | n/a | null | es | solo_stem | 2 |
| active | placeholder | multi_extraction | n/a | null | null | solo_stem | 1 |
| active | real_64hex | single_extraction | binding_mismatch | null | en | dual_stem_y_sha | 1 |
| needs_review | real_64hex | single_extraction | binding_ok | null | es | dual_stem_y_sha | 1 |
| retired | placeholder | single_extraction | n/a | null | null | dual_stem_y_sha | 1 |
| superseded | placeholder | single_extraction | n/a | null | null | dual_stem_y_sha | 1 |

## 3. (c) Gate H1 (NO-CIRCULAR) + colisiones de sha

Diseno del gate (spec §2): la clave de localizacion es el **STEM** (nombre), independiente del hash; el blob se hashea y su sha se compara contra la sha ESPERADA del documento (`source_pdf_sha256` si es real; `extraction_sha256` si es placeholder single-extraction). **Los estratos se definen SOLO por existencia de stem-match** — definirlos por dual-key haria el gate tautologico (desviacion declarada #5).

| estrato | n | match | mismatch | ausente | sin sha esperada | stem ambiguo |
|---|---:|---:|---:|---:|---:|---:|
| A_binding_ok_sha_real | 30 | 30 | 0 | 0 | 0 | 4 |
| B_placeholder_single_extraction | 30 | 30 | 0 | 0 | 0 | 9 |
| **TOTAL** | **60** | **60** | **0** | **0** | | |

**VEREDICTO H1: `H1_CONFIRMADA`** — `extraction_sha256` ES el sha256 de los bytes del PDF fuente en ambos estratos (n>=60, 0 mismatch). El estrato placeholder confirma que la sha real recuperable para el packet P-A es la del blob localizado por nombre.

Marcas del estrato `A_binding_ok_sha_real`: `{'Aritech': 6, 'Morley': 18, 'Notifier': 6}`
Marcas del estrato `B_placeholder_single_extraction`: `{'Argus Security': 1, 'Detnov': 4, 'Morley': 7, 'Notifier': 11, 'Securiton': 1, 'System Sensor': 4, 'Venitem': 1, 'Xtralis': 1}`

### 3.1 Grupos de sha compartida (guard del UNIQUE `documents_mfr_hash_unique`)

- grupos con n>1 por **(manufacturer, sha)**: **0**
- grupos con n>1 por **sha global** (cross-manufacturer incluido): **0**

Ningun grupo con n>1 (coincide con el census del spec §1: **0 colisiones hoy**).

## 4. (d) Census `chunks_v2_hyq`

- filas hyq: **70126** · padres distintos: **23205**
- filas cuyo padre tiene `duplicate_of` NOT NULL: **7421** (10.58%)
- filas cuyo padre tiene `document_id` NULL: **58**
- filas con padre inexistente en `chunks_v2`: 0
- filas cuyo `source_file` desnormalizado difiere del `source_file` del padre: 0 (relevante para F2.2: los campos desnormalizados quedan como display/debug)
- cobertura de source_files (via padres): **1002/1012** · source_files sin ninguna fila hyq: 10

**Deriva censada (se reporta, NO se toca — spec §4 fuera de scope):** chunks con `document_id` NULL = 25 · chunks vivos en docs NO activos = 382 (en 10 docs) · chunks con `document_id` inexistente = 0.

## 5. (e) Detector de idioma v2 + calibracion + procedencia

### 5.1 Detector (reconstruido en este script)

- version: **v2_endurecido** · universo: `['en', 'es', 'fr', 'it', 'pt']` · muestra por doc: **10 chunks** (primeros por `(chunk_index, id)`; todos si hay menos)
- base (spec F0(e)): confianza **alta** ⇔ marcadores del dominante >= 20 **Y** dominante >= 2.0x el segundo.
- **FIX 1 (token dominante)**: un solo TIPO de token que aporte > 50% del recuento del ganador se SUPRIME como marcador en todos los idiomas y se re-decide; si el veredicto (idioma, alta/baja) CAMBIA al quitarlo -> **baja**.
- **FIX 2 (cruce de familia)**: si los dos idiomas top cruzan familia (`en` vs romance `['es', 'fr', 'it', 'pt']`) y el margen es < 3.0x -> **baja** (patron del documento MIXTO, spec §F1 P-B).
- Ambos fixes solo pueden DEGRADAR alta->baja; ninguno promueve baja->alta.
- listas de marcadores INSPIRADAS en `scripts/audit_chunk_languages.py:89-95`; el modulo NO se importa ni se invoca (lee la tabla `chunks` legacy con muestra de 3 — spec §1 lo declara solo como referencia). Los acentos se normalizan antes de contar.

Distribucion detectada sobre los 1169 documentos (`idioma/confianza`): `{'en/alta': 173, 'en/baja': 139, 'es/alta': 554, 'es/baja': 126, 'fr/baja': 2, 'it/baja': 2, 'pt/baja': 2, '∅none/baja': 171}`

### 5.2 Calibracion contra los labels existentes

- documentos YA etiquetados: **400** · distribucion `{'en': 63, 'es': 326, 'fr': 5, 'it': 3, 'nl': 1, 'pt': 2}`
- subconjunto es/en: **389** · acuerdo **385/389 = 98.97%** (gate >=99%: ❌ NO PASA)
- restringido a confianza ALTA: 324/325 = 99.69% (es la cohorte que P-B usaria)

Matriz de confusion (label x detectado):

| label | detectado | n |
|---|---|---:|
| es | es | 322 |
| en | en | 63 |
| es | en | 4 |
| fr | en | 3 |
| it | en | 3 |
| pt | en | 2 |
| fr | fr | 1 |
| fr | ∅none | 1 |
| nl | en | 1 |

**Honestidad (spec §F0(e)(ii) + riesgo 6):** el acuerdo con los labels existentes mide REPRODUCCION de esos labels, no exactitud — es condicion NECESARIA, no suficiente. La barrera de exactitud es la QA 30/30 de §5.5, que este instrumento no adjudica.

Desacuerdos (14 sobre TODOS los labels, no solo es/en). La columna **origen** separa «error del detector» de «posible error LEGACY del label» (spec riesgo 8): `{'residual_pre_s282_regex_nombre_o_manual': 5, 's282_T2_extraccion_LLM': 9}`.

| document_id | label | detectado | conf | origen del label | fichero |
|---|---|---|---|---|---|
| `0bc2481e` | es | en | baja | s282_T2_extraccion_LLM | `MADT120_01` |
| `a13d696c` | es | en | baja | s282_T2_extraccion_LLM | `MADT234` |
| `a38ad698` | es | en | baja | s282_T2_extraccion_LLM | `MIDT193_ID3008-001_Instal_esp` |
| `bd0c2e27` | es | en | alta | s282_T2_extraccion_LLM | `MIDT192_ID3004-001_Instal_esp` |
| `afb89db0` | fr | None | baja | s282_T2_extraccion_LLM | `NF30-50_Manuel_d'utilisation_lr.pdf` |
| `6f797fa1` | fr | en | baja | residual_pre_s282_regex_nombre_o_manual | `MNDT102I_D FR VSN-RP1r_hlsi.pdf` |
| `81615931` | fr | en | baja | s282_T2_extraccion_LLM | `HLSI-MN-103I_V04 FR` |
| `dfca37bf` | fr | en | baja | s282_T2_extraccion_LLM | `MNDT102I_D FR.pdf` |
| `03cf3cca` | it | en | alta | residual_pre_s282_regex_nombre_o_manual | `RP1R - MAN ITA r.A2.pdf` |
| `1791d18f` | it | en | alta | residual_pre_s282_regex_nombre_o_manual | `VSN4-PLUS_ITA.pdf` |
| `6ec89dc4` | it | en | alta | residual_pre_s282_regex_nombre_o_manual | `NFS4_NFS8-2PLUS_MANU_ITA.PDF` |
| `d62b3b67` | nl | en | alta | s282_T2_extraccion_LLM | `HLSI-MA-025 Korte handleiding NFS_Supr` |
| `886efa3a` | pt | en | baja | s282_T2_extraccion_LLM | `MNDT1003P` |
| `96779f28` | pt | en | baja | residual_pre_s282_regex_nombre_o_manual | `I56-3956-201_PT Morley Loop FAAST LT Q` |

Lectura: los labels `it`/`fr`/`pt`/`nl` caen sistematicamente en `en` — son documentos MULTILINGUES cuyos primeros chunks son ingleses, o idiomas cuyo set de marcadores es mas debil que el ingles. No entran en la metrica es/en del gate, pero **avisan de que el detector no es fiable fuera de {es, en}**: P-B solo deberia tocar esas dos.

### 5.2bis Efecto de los dos endurecimientos (v1 literal -> v2 endurecido)

Sobre los 1169 documentos:

- docs con algun token dominante SUPRIMIDO: **24** · de ellos **DEGRADADOS** (el veredicto cambiaba al quitarlo): **16**
- docs DEGRADADOS por cruce de familia con margen < 3.0x: **70**
- distribucion `idioma/confianza` con el predicado LITERAL v1: `{'en/alta': 207, 'en/baja': 109, 'es/alta': 589, 'es/baja': 89, 'fr/alta': 1, 'fr/baja': 1, 'it/baja': 2, 'pt/baja': 4, '∅none/baja': 167}`
- distribucion `idioma/confianza` con el detector v2: `{'en/alta': 173, 'en/baja': 139, 'es/alta': 554, 'es/baja': 126, 'fr/baja': 2, 'it/baja': 2, 'pt/baja': 2, '∅none/baja': 171}`

Casos reales que motivaron cada fix (ambos cazados por el propio census v1): (1) una tabla de equivalencias en ESPANOL que repite 36 veces `plus` (de `NFS-2 PLUS`, nombre de producto) salia `fr/alta` porque `plus` es marcador FR; (2) un manual `..._ES_GB_...` con 168 marcadores `en` vs 83 `es` (ratio 2.02) salia `en/alta` siendo bilingue.

### 5.3 PROCEDENCIA de los labels existentes (scan reproducible del repo)

Scan determinista (regex sobre `scripts/migrations`, `supabase/migrations`, `migrations`, `scripts`, `src/ingestion`, `src/reingest`, extensiones .py/.sql, solo ficheros que mencionan la tabla `documents`): **64 anclas** en 25 ficheros.

| fichero | anclas |
|---|---:|
| `scripts/s282_t2_write_package.py` | 12 |
| `scripts/s285_conflicts_apply_gen.py` | 8 |
| `scripts/s282_qa_s83_regate.py` | 5 |
| `scripts/archive/analyze_language_audit.py` | 4 |
| `scripts/s117_m27_live_evidence.py` | 4 |
| `supabase/migrations/20260713141223_reconcile_validated_document_revisions_v1.sql` | 4 |
| `scripts/audit_chunk_languages.py` | 3 |
| `scripts/s281_h0_identity_census.py` | 3 |
| `scripts/s282_qa_s83_regate_v3.py` | 2 |
| `scripts/s64_lifecycle46.py` | 2 |
| `supabase/migrations/20260721190847_reconcile_hp011_v04_v07_lifecycle.sql` | 2 |
| `supabase/migrations/20260722013000_s277_document_revision_lineage_snapshot_v2.sql` | 2 |
| `scripts/migrations/001_backfill_documents.py` | 1 |
| `scripts/s117_m26_independent_reuse_audit.py` | 1 |
| `scripts/s158_build_table_preamble_cohort.py` | 1 |
| `scripts/s159_build_table_preamble_cohort_v2.py` | 1 |
| `scripts/s160_build_table_preamble_cohort_v3.py` | 1 |
| `scripts/s198_point_first_scope_gate.py` | 1 |
| `scripts/s277_c1_p1_live_manifest.py` | 1 |
| `scripts/s277_document_local_coverage_probe.py` | 1 |

Anclas fichero:linea (primeras 25):

- `scripts/archive/analyze_language_audit.py:45` — `params={"select": "source_pdf_filename,language,manufacturer",`
- `scripts/archive/analyze_language_audit.py:46` — `"language": "not.is.null", "limit": "100"})`
- `scripts/archive/analyze_language_audit.py:49` — `print(f"documents with language set: {len(filename_labeled)}")`
- `scripts/archive/analyze_language_audit.py:56` — `parser_lang = row["language"]`
- `scripts/audit_chunk_languages.py:273` — `by_lang: Counter[tuple[str, str]] = Counter()  # (language, confidence)`
- `scripts/audit_chunk_languages.py:275` — `by_lang[(r["detected_language"], r["confidence"])] += 1`
- `scripts/audit_chunk_languages.py:277` — `print(f"{'language':<10s} {'confidence':<10s} {'count':>6s}")`
- `scripts/migrations/001_backfill_documents.py:267` — `"language": None,`
- `scripts/s117_m26_independent_reuse_audit.py:560` — `"language": local.get("language"),`
- `scripts/s117_m27_live_evidence.py:274` — `"language": local.get("language"),`
- `scripts/s117_m27_live_evidence.py:306` — `"language": local.get("language"),`
- `scripts/s117_m27_live_evidence.py:399` — `"language": receipt["language"],`
- `scripts/s117_m27_live_evidence.py:405` — `"unsupported_language": "policy_excluded_language",`
- `scripts/s158_build_table_preamble_cohort.py:149` — `"language": seed.get("language"),`
- `scripts/s159_build_table_preamble_cohort_v2.py:123` — `"language": seed.get("language"),`
- `scripts/s160_build_table_preamble_cohort_v3.py:130` — `"language": seed.get("language"),`
- `scripts/s198_point_first_scope_gate.py:620` — `"language": "Spanish",`
- `scripts/s277_c1_p1_live_manifest.py:796` — `"language": str(row["language"]),`
- `scripts/s277_document_local_coverage_probe.py:459` — `"language": "es",`
- `scripts/s279_selection_census.py:356` — `"language": doc.get("language"),`
- `scripts/s281_h0_identity_census.py:599` — `"language": d.get("language"),`
- `scripts/s281_h0_identity_census.py:851` — `f"+language='es') y solo les falta un lineage `verified` — es la cohorte de MENOR riesgo (no "`
- `scripts/s281_h0_identity_census.py:878` — `A("UPDATE documents SET language='es', doc_type='<tipo>', product_model='<modelo s83 QA'd>'")`
- `scripts/s281_h0t3_retag_packet.py:345` — `"language": sorted({str(d.get("language") or "") for d in docs}),`
- `scripts/s282_qa_s83_regate.py:410` — `A("-- Fuente de valores: evals/s282_qa_s83_result_v2.json (write_op in {corroborate_noop,fill_language_doctype`

**Reconciliacion CUANTITATIVA contra el escritor dominante** (`evals/s282_t2_manifest_v1.json` sha256-LF `314b2db50d6137dc…`):

- filas del manifest: 533 · con `language`: **301** (distribucion `{'en': 58, 'es': 237, 'fr': 4, 'nl': 1, 'pt': 1}`)
- de esas, HOY en DB: **match 301** · siguen NULL 0 · distinto 0
- **paquete s282 T2 aplicado: SI ✅** (el guard de la propia SQL exige `language_set = 301`)
- labels vivos totales: 400 · **residual NO explicado por s282: 99** (distribucion `{'en': 5, 'es': 89, 'fr': 1, 'it': 3, 'pt': 1}`)

**VEREDICTO DE PROCEDENCIA: DETERMINABLE.** Los labels vivos de
`documents.language` son la suma de DOS mecanismos disjuntos, y la aritmetica cierra contra la
DB viva (bloque de arriba):

1. **Escritor DOMINANTE — paquete s282 «Tramo 2» (301 de los ~400).** El generador
   `scripts/s282_t2_write_package.py` emite `evals/s282_t2_apply_v1.sql`, cuyo UPDATE es
   **fill-only** (`evals/s282_t2_apply_v1.sql:590-596`:
   `language = COALESCE(d.language, s.language)` con `WHERE ... (d.doc_type IS NULL OR
   d.language IS NULL)`) y cuya verificacion post-apply ABORTA si
   `language_set <> 301` (`evals/s282_t2_apply_v1.sql:614`; `n_overwrite <> 0` tambien aborta ->
   **nunca sobreescribe** un label previo). El insumo es `evals/s282_t2_manifest_v1.json`
   (`n_rows=533`, `n_language_writes_expected=301`). **VERIFICADO EN VIVO por este census:** las
   301 filas con idioma del manifest valen HOY exactamente ese idioma y 0 siguen NULL -> el paste
   se ejecuto. (Las tablas `t2_staging`/`t2_apply_audit` son `CREATE TEMP TABLE`
   — `evals/s282_t2_apply_v1.sql:18` y `:578` — por eso no existen hoy en el esquema: su ausencia
   NO es evidencia de no-aplicacion; la reconciliacion fila-a-fila SI es evidencia de aplicacion.)
   **El origen del VALOR no es un detector determinista: es una extraccion LLM dual sobre
   contenido** (`scripts/s83_pilot_extract_duo.py` -> `evals/s83_document_identity_final.jsonl`,
   campo `languages` como LISTA), de la que **solo se escribieron los singletons**; los casos
   multi-idioma y los que contradecian la DB se enrutaron a adjudicacion humana y se dejaron
   intactos (`evals/s282_qa_s83_attestation_v2.md`, ejes `language` SINGLETON=AUTO vs MULTI y
   CONTRADICT=ADVISORY).

2. **Residual pre-s282 (~99 labels).** Proceden del registro de ingesta ORIGINAL,
   `src/ingestion/document_registry.py:206` (`"language": info.language` en la fila POSTeada a
   `/rest/v1/documents`), cuyo valor lo producia un **regex puro sobre el NOMBRE del fichero**
   (`src/ingestion/revision_parser.py`, `_LANG_PATTERNS`/`detect_language`: `es|sp|esp`,
   `en|gb|eng`, `fr`, `pt`, `de`, `it`, `multi`; NULL si no hay token). **Ambos ficheros fueron
   BORRADOS en el commit `202ccb0`** ("s43: limpieza #38 (pipeline v1)"; el diff elimina
   `src/ingestion/document_registry.py` y `src/ingestion/revision_parser.py`) -> se recuperan con
   `git show 202ccb0^:<path>`. A eso se suman ~10 filas adjudicadas A MANO con constante `'es'`:
   `supabase/migrations/20260713141223_reconcile_validated_document_revisions_v1.sql:92,105,126,135`
   y `scripts/s64_lifecycle46.py:95,115`.

3. **Los NULL tambien estan explicados.** `scripts/migrations/001_backfill_documents.py:267`
   escribe `"language": None` POR DISENO en la fase 1 del backfill (mismo sitio que acuna el
   placeholder `backfill:<sha256 del NOMBRE>`, `:261`), y `scripts/s65_capab.py:448` inserta
   `"language": None` para su lote.

4. **NINGUN label salio de un detector estadistico de contenido.** `src/reingest/language.py`
   (lingua) escribe `chunks_v2.language`, NO `documents.language`; el pipeline de re-ingesta
   *lee* `documents.language` como compuerta de admision. Es decir: **el detector v2 de esta F0 es
   independiente del origen de los labels contra los que se calibra** — no hay circularidad de
   instrumento; pero SI hay un riesgo de circularidad de JUICIO con el eje 1 (labels de origen
   LLM-sobre-contenido), asi que el acuerdo alto mide **reproduccion de una extraccion LLM previa
   filtrada por singleton**, no exactitud contra la fuente. Es exactamente el riesgo 6/8 del spec:
   la barrera de exactitud es la QA-30 de §5.5, no esta calibracion.

**Incertidumbre residual declarada:** el reparto EXACTO del residual pre-s282 entre el regex de
nombre y las filas adjudicadas a mano no es reconstruible desde el repo (los ficheros del regex
estan borrados y no hay recibo por-fila de aquella ingesta); solo su magnitud y su forma
(mayoritariamente `es`) son medibles. Ese residual NO entra en P-B (P-B toca solo `language IS
NULL`).

### 5.4 Candidatos P-B (activos, language NULL, confianza alta)

**394 documentos** · por idioma propuesto: `{'en': 108, 'es': 286}`.

Delta contra el predicado LITERAL v1: partia de **453** (`{'en': 142, 'es': 310, 'fr': 1}`) y caen **1** por token dominante + **58** por cruce de familia.

| document_id | idioma | marc. | ratio | tipos | 2º idioma (marc.) | fichero |
|---|---|---:|---:|---:|---|---|
| `0037a1f2` | en | 618 | 103.0 | 17 | pt (6) | `HLSI-MI-580I.pdf` |
| `01c8e123` | es | 57 | 5.182 | 14 | it (11) | `TIDT070.pdf` |
| `020d7a69` | es | 66 | 5.077 | 16 | pt (13) | `fd2710r-62536-es.pdf` |
| `0216c070` | es | 94 | 6.267 | 15 | it (15) | `ASD IN Rail Transportation Applica` |
| `0295feed` | es | 203 | 6.767 | 16 | pt (30) | `MADT370` |
| `03ec224e` | en | 191 | 12.733 | 15 | pt (15) | `18-187110-10.pdf` |
| `0426c906` | es | 247 | 6.175 | 17 | pt (40) | `HLSI-MN-963_POL-200-TS` |
| `04bb1360` | en | 51 | 3.4 | 11 | es (15) | `D 1149-1 BGL Notifier` |
| `04dd4625` | es | 97 | 4.85 | 16 | it (20) | `Datasheet_CAD-201-DS-740-es.pdf` |
| `0560ef38` | es | 35 | 5.0 | 9 | pt (7) | `MIE-MP-530rv001` |
| `067598cb` | es | 269 | 3.736 | 17 | pt (72) | `MP-DT-951_v7.2.pdf` |
| `06c08203` | es | 414 | 6.088 | 17 | pt (68) | `MIDT951_v5-87` |
| `06d1d1d4` | en | 66 | 33.0 | 12 | pt (2) | `bcn-3100035-en_r006_2x-a_series_ad` |
| `0737509b` | en | 332 | 55.333 | 17 | pt (6) | `I56-3383-002 IDX-751 AE EN DE` |
| `08828182` | es | 306 | 4.636 | 17 | pt (66) | `MIE-MI-010.pdf` |
| `0903db56` | es | 353 | 6.193 | 17 | pt (57) | `MPDT951_v5-87.pdf` |
| `09194202` | en | 217 | 108.5 | 16 | pt (2) | `3103072-ml_r004_excellence_series_` |
| `0951df3f` | es | 470 | 5.281 | 18 | pt (89) | `33036_05_VESDA-E_VEA-040-A00_Produ` |
| `096795c0` | en | 71 | 4.176 | 13 | es (17) | `D 1150-1 BRH Morley` |
| `09c2bab5` | es | 72 | 4.0 | 12 | pt (18) | `FAAST Understanding EN54-20_SP` |

### 5.5 Muestra QA-30 (spec F0(e)(iii)) — EMITIDA, NO ADJUDICADA

Muestra estratificada por idioma propuesto, round-robin determinista sobre `md5(document_id)`: **30 documentos**. La regla de aceptacion del spec es **30/30 correctos o HALT**; requiere lectura humana del extracto y NO la decide este script ($0/read-only). Sin este gate cerrado, **P-B no se stagea** (spec §F0(e)).

El packet legible para adjudicacion (2 snippets de evidencia por documento) se emite aparte, ver la cabecera de este report.

| # | document_id | stem | propuesta | 2º (marc.) | marca |
|---:|---|---|---|---|---|
| 1 | `65669851` | `MNDT951I` | en | pt (3) | Notifier |
| 2 | `f1a60b0d` | `55350005 Manual Central Monoxido CMD-5` | es | pt (67) | Detnov |
| 3 | `84365c09` | `00-3280-507-4003-03_r003_2x-a_series_q` | en | pt (4) | Aritech |
| 4 | `0426c906` | `HLSI-MN-963_POL-200-TS` | es | pt (40) | Morley |
| 5 | `f763235d` | `WFDEN_Manual_I56-4051` | en | pt (13) | System Sensor |
| 6 | `123dc496` | `MIE-MC-530` | es | it (44) | Morley |
| 7 | `f8132ff7` | `bcn-3100036-en_r002_2x-a_and_zp2-a_ser` | en | fr (3) | Aritech |
| 8 | `08828182` | `MIE-MI-010` | es | pt (66) | Morley |
| 9 | `aac0d826` | `10-5106-501-55nc-05_r005_iu2055nc_inst` | en | es (59) | Aritech |
| 10 | `0e9330c8` | `MIE-MI-530rv001` | es | it (18) | Morley |
| 11 | `637cc4d7` | `2x-at-f2-fb-p-161721-es` | en | es (15) | Aritech |
| 12 | `a2bb8ee1` | `Conexionado-del-modulo-M710-CZ-MI-DCZM` | es | pt (6) | Notifier |
| 13 | `c96bb93b` | `I56-3888-010 FAAST LT-200 Adv Guide` | en | pt (3) | Xtralis |
| 14 | `6096bdf6` | `MIE-MU-530rv001` | es | pt (33) | Morley |
| 15 | `537a0275` | `156-0551-005R EPS10_Eng` | en | pt (18) | System Sensor |
| 16 | `bc0c7b5f` | `TIDT110` | es | en (17) | Notifier |
| 17 | `09194202` | `3103072-ml_r004_excellence_series_inte` | en | pt (2) | Kidde |
| 18 | `217117c0` | `MADT212` | es | pt (32) | Notifier |
| 19 | `f5224079` | `04-4001-501-1700-06_r006_aritech_apic_` | en | pt (14) | Aritech |
| 20 | `0ad0a70f` | `MA-AL-T500-01-07 Manual TUL500esp rev1` | es | it (35) | Venitem |
| 21 | `43cabec0` | `I56-5002-000-Morley-Strobe` | en | es (33) | Morley |
| 22 | `4112c5c1` | `MIE-MA-300_01` | es | pt (70) | Morley |
| 23 | `fc3d273e` | `085501945t_PA5_Installation_manual_D-G` | en | pt (5) | Pfannenberg |
| 24 | `0dde8e85` | `MIE-MC-130rv02` | es | it (38) | Morley |
| 25 | `c295d7f9` | `MNDT960I` | en | pt (5) | Notifier |
| 26 | `d1299a40` | `DXc_Manual de configuracion` | es | pt (33) | Morley |
| 27 | `3138edc4` | `I56-2956-000_prelim` | en | es (53) | Morley |
| 28 | `a107427f` | `Manual Testifire_Spanish` | es | pt (71) | Xtralis |
| 29 | `be1b6b42` | `MNDT960I_iBox-BACnet` | en | pt (7) | Notifier |
| 30 | `7f9ea4ab` | `MNDT1025` | es | pt (88) | Notifier |

## 6. (f) Screens de siblings (docs ACTIVOS, contra TODOS los status)

| screen | activos marcados |
|---|---:|
| (i) punteros `supersedes_id`/`superseded_by_id` (propios o apuntando al doc) | 8 |
| (ii) colision de stem NORMALIZADO (strip rev/fecha/idioma/separadores) | 81 |
| (iii) misma tupla (mfr, product_model, doc_type, language) con doc_type NO-NULL | 73 |
| **ALGUN screen sucio** | **145** de 995 activos |
| limpios en los 3 screens | 850 |

Grupos de colision: stem-normalizado **78** · tupla de identidad **29**.

Top grupos por stem normalizado:

| clave normalizada | n | stems |
|---|---:|---|
| `mndt951i` | 4 | `MNDT951I`, `MNDT951I_v7-1` |
| `mpdt951` | 4 | `MP-DT-951_v7.2`, `MPDT951_v5-87` |
| `mndt951` | 3 | `MN-DT-951_v7.2`, `MNDT951_v5-87` |
| `3397613vesdaevepa00pproductguidea4spanis` | 2 | `33976_13_VESDA-E_VEP-A00-P` |
| `hlsimn025infssupraseries` | 2 | `HLSI-MN-025-I_NFS Supra Se`, `HLSI-MN-025-I_NFS Supra Se` |
| `hlsimn103rp1rsupralr` | 2 | `HLSI-MN-103_RP1r-Supra_lr` |
| `i5617260036200rmanual` | 2 | `I56-1726-003 6200R Manual `, `I56-1726-003 6200R Manual ` |
| `i563878000nfxibeamt` | 2 | `I56-3878-000 NFXI-BEAM(T)_`, `I56-3878-000 NFXI-BEAM(T)_` |
| `i563879000milpb2s2i` | 2 | `I56-3879-000 MI-LPB2-S2I_E`, `I56-3879-000 MI-LPB2-S2I_E` |
| `midt951` | 2 | `MI-DT-951_V7.2`, `MIDT951_v5-87` |
| `mndt1300e` | 2 | `MNDT1300_E` |
| `mndt1300ie` | 2 | `MNDT1300I_E` |

Top grupos por tupla de identidad:

| marca | product_model | doc_type | lang | n |
|---|---|---|---|---:|
| Morley | UCIP | configuracion | es | 10 |
| Notifier | ID3000 | configuracion | es | 8 |
| Notifier | ID3000 | boletin | es | 4 |
| Morley | UCIP | configuracion |  | 3 |
| Notifier | AM2020/AFP1010 | configuracion | es | 3 |
| Notifier | RP1r | guia_usuario |  | 3 |
| Argus Security | SG100 | instalacion | en | 2 |
| Argus Security | SG200 | instalacion | en | 2 |
| Argus Security | SG350 | instalacion | en | 2 |
| Aritech | 2X-A Táctil | instalacion | en | 2 |
| Detnov | CAD-250 | configuracion | es | 2 |
| Detnov | CAD-250 | programacion | es | 2 |

Los `document_id` activos con algun screen sucio estan en el JSON (`census.f_screens.activos_sucios_ids`). Alimentan el workstream P-C de TRAMOS (spec §F1) y el contexto de P-A; **no bloquean P-A por si mismos** (P-A se gatea por dual-key + singleton per-mfr).

## 7. (g) PRE-REGISTRO DE VOLUMEN (fix r2-3 — el gate F3 compara contra estas cifras)

| packet | definicion | **n elegibles** |
|---|---|---:|
| **P-A** (sha real) | activo + single-extraction + dual-key (stem Y sha al MISMO blob) + grupo-sha singleton per-manufacturer + sha PLACEHOLDER (las filas que el UPDATE cambia realmente) | **585** |
| **P-B** (language) | activo + language NULL + detector v2 ENDURECIDO confianza ALTA (base del spec + supresion de token dominante + cruce de familia con margen >= 3x) | **394** |

**P-A, desglose (desviacion declarada #6):** el predicado literal del spec no menciona la clase de sha; aplicado tal cual da **992** documentos, de los cuales **407** YA tienen sha real (el UPDATE seria un no-op y falsearia el gate «aplicado == 100% de elegibles»). La cifra pre-registrada del packet es el subconjunto **placeholder = 585**. Ambas listas de `document_id` van en el JSON (`census.g_pre_registro`), ordenadas.

**P-B por idioma propuesto:** `{'en': 108, 'es': 286}`. Cohorte construida con el detector **v2 endurecido**: partia de 453 con el predicado literal y caen 1 por token dominante + 58 por cruce de familia (§5.2bis).

**Gate (e)(iii) sigue ABIERTO**: la QA-30 fresca de esta cohorte se emite como packet legible pero NO esta adjudicada -> **el staging de P-B NO esta autorizado**.

### 7.1 Techo declarado de P-A — por que cada documento NO entra (primer motivo, excluyente)

| motivo | documentos |
|---|---:|
| ELEGIBLE | 585 |
| sha_real_64hex | 407 |
| no_activo | 174 |
| binding_multi_extraction | 3 |

## 8. Honestidad del instrumento — lo que este census NO hace

- **No escribe nada.** Ni DB (solo GET), ni ficheros fuera de `evals/s288_acore_*`. Los packets SQL de F1 son trabajo posterior y su paste es de Alberto (spec §7 stop-lines).
- **No adjudica la QA-30 de F0(e)(iii)** (§5.5): la emite estratificada y determinista. El gate (e) queda por tanto **PARCIALMENTE verde**: (i) documentado y (ii) medido; (iii) abierto.
- **La calibracion mide reproduccion, no exactitud** (spec riesgo 6/8): si los labels legacy traen un error sistematico, el acuerdo alto lo reproduce. La QA-30 es la barrera.
- **El detector NO es fiable fuera de {es, en}** (§5.2): todos los labels `it`/`fr`/`pt`/`nl` se detectan como `en`. Y dentro de {es, en} tiene dos modos de fallo medidos y con caso real (§5.2bis): token repetido y documento bilingue. **Este census NO recomienda stagear P-B**: (e)(ii) no pasa el 99% y (e)(iii) esta sin adjudicar.
- **El match blob<->doc por sha usa `extraction_sha256` para los placeholder**: es exactamente la premisa H1, que este mismo census verifica por clave independiente (§3). Si H1 no fuera CONFIRMADA, la columna `blob_local` de los placeholder quedaria en cuarentena junto con P-A.
- **Los stems duplicados en disco** hacen el indice multi-valor: un doc puede casar por stem con 2+ blobs. El gate H1 acepta match si CUALQUIERA de ellos tiene la sha esperada, y reporta cuantas filas tuvieron stem ambiguo. El dual-key de P-A exige que stem y sha coincidan en el **MISMO** blob (spec fix r2-1).
- **Fuera de scope declarado (spec §4):** remediacion de la deriva (§4), doc_type backfill, sha/language de retired/needs_review, lineages (P-C = tramos adjudicados por Alberto).
