# s288 A-CORE — F0 census v2 — v4

Instrumento: `scripts/s288_acore_census_v2.py`. **READ-ONLY (solo GET de PostgREST), SELECT-only, 0 escrituras, 0 llamadas a modelos, coste $0.** Implementa F0(a)-(g) del spec SELLADO `evals/s288_acore_design_brief_v1.md` (v3). Hereda el stack GET-only + paginacion ordenada + contrato de determinismo 2x + freeze-contract de `scripts/s281_h0_identity_census.py` (artefactos s281 intocados).

## Freeze-contract

- commit HEAD: `3437c38ea00404b9b4b2ef90897fe3bcd014c11c` (worktree dirty: False)
- CHUNKS_TABLE forzado: `chunks_v2`
- spec: `evals/s288_acore_design_brief_v1.md` sha256-LF `1c1a65088681f6a37d5dcc87c7cd6a921d6ca32ab25364fe569b208fe75edc39`
- blob root (solo lectura): `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot`
- fingerprint de corpus: documents=1169 · chunks_v2=25088 · chunks_v2_hyq=70126 · sha256 `744f21af87de1df9bbd10ae06ec57d0d38d927fcff445fa2a1f0e5954cfff2b5`
- manifest de blobs: `evals/s288_acore_blob_manifest_v4.jsonl` sha256-LF `b20892c50853a1abe4f72fba34870a11b745e9ec81d882a375fd573f6bac555c`
- packet QA-30 de P-B (adjudicacion humana): `evals/s288_acore_pB_qa30_v4.md`
- **determinismo 2x: IDENTICO ✅** (pass1 `8ae2060269a1e931` vs pass2 `8ae2060269a1e931`; ambas pasadas RE-LEEN la DB; el hash de los PDFs se calcula UNA vez y se reusa — los bytes en disco no cambian entre pasadas, declarado)
- generado 2026-07-31T03:52:26.729305+00:00

## 0. GATE F0 (spec §F0)

| Condicion del gate | Estado |
|---|---|
| determinismo 2x byte-identico | ✅ SI |
| particion suma 1169 | ✅ SI (suma=1169) |
| H1 explicito | **H1_INCONCLUSA** (32/32 match, 0 mismatch) |
| (e)(ii) acuerdo es/en >= 99% | ✅ SI (100.0%) |
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

Suma de celdas = **1169** / 1169 documentos (✅ EXHAUSTIVA). Celdas no vacias: 17.

### 2.1 Marginales

- **status**: `active`=995 · `retired`=91 · `needs_review`=79 · `superseded`=4
- **clase de sha**: `real_64hex`=1010 · `placeholder`=159
- **binding (extracciones)**: `single_extraction`=1002 · `sin_chunks`=164 · `multi_extraction`=3
- **binding check**: `binding_ok`=999 · `n/a`=169 · `binding_mismatch`=1
- **lineage**: `null`=1160 · `not_null`=9
- **language**: `null`=769 · `es`=326 · `en`=63 · `otro`=11
- **blob local**: `dual_stem_y_sha`=1012 · `solo_stem`=157

### 2.2 Celdas (status x clase-sha x binding x binding-check x lineage x language x blob-local)

| status | sha | binding | check | lineage | lang | blob local | n |
|---|---|---|---|---|---|---|---:|
| active | real_64hex | single_extraction | binding_ok | null | null | dual_stem_y_sha | 598 |
| active | real_64hex | single_extraction | binding_ok | null | es | dual_stem_y_sha | 314 |
| retired | placeholder | sin_chunks | n/a | null | null | solo_stem | 84 |
| needs_review | placeholder | sin_chunks | n/a | null | null | solo_stem | 70 |
| active | real_64hex | single_extraction | binding_ok | null | en | dual_stem_y_sha | 62 |
| active | real_64hex | single_extraction | binding_ok | null | otro | dual_stem_y_sha | 11 |
| active | real_64hex | single_extraction | binding_ok | not_null | es | dual_stem_y_sha | 6 |
| retired | real_64hex | sin_chunks | n/a | null | null | dual_stem_y_sha | 6 |
| needs_review | real_64hex | sin_chunks | n/a | null | null | dual_stem_y_sha | 4 |
| needs_review | real_64hex | single_extraction | binding_ok | null | null | dual_stem_y_sha | 4 |
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
| A_binding_ok_sha_real | 30 | 30 | 0 | 0 | 0 | 5 |
| B_placeholder_single_extraction | 2 | 2 | 0 | 0 | 0 | 0 |
| **TOTAL** | **32** | **32** | **0** | **0** | | |

**VEREDICTO H1: `H1_INCONCLUSA`** — revisar los mismatch por estrato antes de habilitar P-A sobre ese estrato (spec §2: estrato que falla -> fuera de P-A, techo declarado).

Marcas del estrato `A_binding_ok_sha_real`: `{'Aritech': 3, 'Detnov': 4, 'Morley': 9, 'Notifier': 12, 'System Sensor': 2}`
Marcas del estrato `B_placeholder_single_extraction`: `{'Detnov': 1, 'Notifier': 1}`

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

- version: **v3_endurecido_fix1_fix2_fix3** · universo: `['en', 'es', 'fr', 'it', 'pt']` · muestra por doc: **10 chunks** (primeros por `(chunk_index, id)`; todos si hay menos)
- base (spec F0(e)): confianza **alta** ⇔ marcadores del dominante >= 20 **Y** dominante >= 2.0x el segundo.
- **FIX 1 (token dominante)**: un solo TIPO de token que aporte > 50% del recuento del ganador se SUPRIME como marcador en todos los idiomas y se re-decide; si el veredicto (idioma, alta/baja) CAMBIA al quitarlo -> **baja**.
- **FIX 2 (cruce de familia)**: si los dos idiomas top cruzan familia (`en` vs romance `['es', 'fr', 'it', 'pt']`) y el margen es < 3.0x -> **baja** (patron del documento MIXTO, spec §F1 P-B).
- **FIX 3 (limpieza de INPUT — anotaciones del extractor)**: antes de contar se eliminan los spans `[...]` que el EXTRACTOR inyecta en ingles para describir figuras («[Diagram showing…]», «[Exploded view…]», «[Grid paper…]»), siempre que el corchete cierre en <= 500 chars (si no cierra, se deja intacto). **A diferencia de FIX 1/2, este SI puede cambiar el idioma detectado — ese es su proposito.**

  > **Es limpieza de INPUT motivada por el MECANISMO, NO tuning contra el gate.** Ese texto no pertenece al documento: lo genera el instrumento de extraccion. Se elimina la misma clase de span en TODOS los documentos, antes de contar, con un criterio sintactico fijo. Motivo raiz: los documentos ESPANOLES *diagram-heavy* acumulaban marcadores INGLESES falsos y salian `en` con confianza ALTA — sin este fix P-B habria escrito `en` en documentos espanoles (**backfill ERRONEO**). Caso que lo destapo: `bd0c2e27` = MI-DT-192 (notifier.es, «9 AGOSTO 2013»), documento espanol que salia `en/alta`.

- FIX 1 y FIX 2 solo pueden DEGRADAR alta->baja. FIX 3 actua ANTES, sobre el texto.
- Rastro completo conservado por documento: `language_literal`/`confidence_literal` (regla literal del spec sobre texto CRUDO = baseline v1) vs el veredicto endurecido, mas `limpieza` y `cambio_idioma_por_limpieza`.
- listas de marcadores INSPIRADAS en `scripts/audit_chunk_languages.py:89-95`; el modulo NO se importa ni se invoca (lee la tabla `chunks` legacy con muestra de 3 — spec §1 lo declara solo como referencia). Los acentos se normalizan antes de contar.

Distribucion detectada sobre los 1169 documentos (`idioma/confianza`): `{'en/alta': 161, 'en/baja': 129, 'es/alta': 584, 'es/baja': 106, 'fr/baja': 3, 'it/baja': 2, 'pt/baja': 9, '∅none/baja': 175}`

### 5.2 Calibracion contra los labels existentes

- documentos YA etiquetados: **400** · distribucion `{'en': 63, 'es': 326, 'fr': 5, 'it': 3, 'nl': 1, 'pt': 2}`
- subconjunto es/en: **389** · acuerdo **389/389 = 100.0%** (gate >=99%: ✅ PASA)
- restringido a confianza ALTA: 333/333 = 100.0% (es la cohorte que P-B usaria)

Matriz de confusion (label x detectado):

| label | detectado | n |
|---|---|---:|
| es | es | 326 |
| en | en | 63 |
| fr | fr | 3 |
| it | en | 3 |
| fr | ∅none | 2 |
| nl | en | 1 |
| pt | en | 1 |
| pt | pt | 1 |

**Honestidad (spec §F0(e)(ii) + riesgo 6):** el acuerdo con los labels existentes mide REPRODUCCION de esos labels, no exactitud — es condicion NECESARIA, no suficiente. La barrera de exactitud es la QA 30/30 de §5.5, que este instrumento no adjudica.

Desacuerdos (7 sobre TODOS los labels, no solo es/en). La columna **origen** separa «error del detector» de «posible error LEGACY del label» (spec riesgo 8): `{'residual_pre_s282_regex_nombre_o_manual': 4, 's282_T2_extraccion_LLM': 3}`.

| document_id | label | pre-FIX3 | detectado | conf | anot. | origen del label | fichero |
|---|---|---|---|---|---:|---|---|
| `6f797fa1` | fr | en | None | baja | 1 (22.62%) | residual_pre_s282_regex_nombre_o_manual | `MNDT102I_D FR VSN-RP1r_hlsi.pdf` |
| `afb89db0` | fr | en | None | baja | 4 (7.38%) | s282_T2_extraccion_LLM | `NF30-50_Manuel_d'utilisation_lr.pd` |
| `03cf3cca` | it | en | en | baja | 16 (13.12%) | residual_pre_s282_regex_nombre_o_manual | `RP1R - MAN ITA r.A2.pdf` |
| `1791d18f` | it | en | en | alta | 1 (1.2%) | residual_pre_s282_regex_nombre_o_manual | `VSN4-PLUS_ITA.pdf` |
| `6ec89dc4` | it | en | en | alta | 2 (16.67%) | residual_pre_s282_regex_nombre_o_manual | `NFS4_NFS8-2PLUS_MANU_ITA.PDF` |
| `d62b3b67` | nl | en | en | baja | 8 (7.29%) | s282_T2_extraccion_LLM | `HLSI-MA-025 Korte handleiding NFS_` |
| `886efa3a` | pt | en | en | baja | 2 (22.99%) | s282_T2_extraccion_LLM | `MNDT1003P` |

Lectura: los labels `it`/`fr`/`pt`/`nl` caen sistematicamente en `en` — son documentos MULTILINGUES cuyos primeros chunks son ingleses, o idiomas cuyo set de marcadores es mas debil que el ingles. No entran en la metrica es/en del gate, pero **avisan de que el detector no es fiable fuera de {es, en}**: P-B solo deberia tocar esas dos.

### 5.2bis Efecto de los endurecimientos (literal -> endurecido)

Sobre los 1169 documentos:

- **FIX 3**: docs con anotaciones del extractor eliminadas: **751** · anotaciones totales: 8229 · chars eliminados: 541861 · **docs que CAMBIAN de idioma detectado por la limpieza: 21**

| document_id | crudo | tras limpieza | final | % chars elim. | fichero |
|---|---|---|---|---:|---|
| `1ba3dc05` | en | es | None | 72.87% | `MIW-INT-Averias-baterias-pilas-via-r` |
| `6f797fa1` | en | None | None | 22.62% | `MNDT102I_D FR VSN-RP1r_hlsi.pdf` |
| `9e0a8f7d` | en | None | None | 81.35% | `EMA24RS2R_NX2y5-R-R` |
| `8ed64d8a` | en | fr | en | 15.24% | `HLSI-MA-103 _Korte handleiding RP1r_` |
| `3fe5ebe0` | en | es | es | 8.26% | `MADT155_08` |
| `89963a7b` | en | es | es | 14.35% | `D391 Issue 3 WR2001 ` |
| `92a7f437` | en | es | es | 26.45% | `MNDT1420` |
| `a32e806d` | en | es | es | 34.23% | `D700-3-Sp` |
| `a38ad698` | en | es | es | 33.11% | `MIDT193_ID3008-001_Instal_esp` |
| `b431095e` | en | es | es | 23.62% | `D 1129-1` |
| `bd0c2e27` | en | es | es | 50.46% | `MIDT192_ID3004-001_Instal_esp` |
| `df5fcf75` | en | es | es | 30.99% | `Compatibilidad-detectores-de-monoxid` |
| `e85ec483` | en | es | es | 17.35% | `Manual SIMEI-HLSI_SP-EN` |
| `fd5cf489` | en | es | es | 31.87% | `MIW-INT-Cuantos-expansores-puedo-con` |
| `81615931` | en | es | fr | 10.25% | `HLSI-MN-103I_V04 FR` |
| `dfca37bf` | en | fr | fr | 61.38% | `MNDT102I_D FR.pdf` |
| `0a33955c` | en | es | pt | 66.57% | `4188-1132-PT issue 4_04_2025-Qref.pd` |
| `20160a6b` | en | pt | pt | 16.34% | `4188-1124-PT issue 4_01-2026_To.pdf` |
| `564b775d` | en | es | pt | 5.75% | `996-130-000-3 Manuel d'utilisation Z` |
| `bb0b336d` | en | pt | pt | 15.86% | `HOP-138-9PT-issue 6_01-2026_In` |

- docs con algun token dominante SUPRIMIDO: **31** · de ellos **DEGRADADOS** (el veredicto cambiaba al quitarlo): **20**
- docs DEGRADADOS por cruce de familia con margen < 3.0x: **38**
- distribucion `idioma/confianza` con el predicado LITERAL v1: `{'en/alta': 207, 'en/baja': 109, 'es/alta': 589, 'es/baja': 89, 'fr/alta': 1, 'fr/baja': 1, 'it/baja': 2, 'pt/baja': 4, '∅none/baja': 167}`
- distribucion `idioma/confianza` con el detector v2: `{'en/alta': 161, 'en/baja': 129, 'es/alta': 584, 'es/baja': 106, 'fr/baja': 3, 'it/baja': 2, 'pt/baja': 9, '∅none/baja': 175}`

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

**406 documentos** · por idioma propuesto: `{'en': 99, 'es': 307}`.

**Reconciliacion contra el predicado LITERAL** (`453 literal - 50 perdidos + 3 ganados = 406` · aditiva: OK):

- literal (regla del spec sobre texto crudo): **453** (`{'en': 142, 'es': 310, 'fr': 1}`)
- **perdidos: 50** por motivo: `{'familia_cruzada_margen_estrecho': 28, 'margen_insuficiente': 14, 'pocos_marcadores': 7, 'solo_token_dominante': 1}` (de ellos 3 con degradacion por token dominante y 28 por cruce de familia)
- **ganados: 3** por motivo: `{'limpieza_desbloquea_alta': 1, 'limpieza_mejora_margen': 2}` — documentos que la regla literal dejaba en `baja` porque las anotaciones inglesas del extractor diluian el margen, y que tras FIX 3 resuelven limpio
- conservados: 403, de los cuales **0 CAMBIAN de idioma propuesto** respecto al literal (efecto directo de FIX 3 — el caso `bd0c2e27`)

| document_id | idioma | marc. | ratio | tipos | 2º idioma (marc.) | fichero |
|---|---|---:|---:|---:|---|---|
| `0037a1f2` | en | 601 | 100.167 | 17 | pt (6) | `HLSI-MI-580I.pdf` |
| `01c8e123` | es | 57 | 5.182 | 14 | it (11) | `TIDT070.pdf` |
| `020d7a69` | es | 66 | 5.077 | 16 | pt (13) | `fd2710r-62536-es.pdf` |
| `0216c070` | es | 94 | 6.267 | 15 | it (15) | `ASD IN Rail Transportation Applica` |
| `0295feed` | es | 202 | 6.733 | 16 | pt (30) | `MADT370` |
| `03ec224e` | en | 182 | 12.133 | 15 | pt (15) | `18-187110-10.pdf` |
| `0426c906` | es | 247 | 6.175 | 17 | pt (40) | `HLSI-MN-963_POL-200-TS` |
| `04dd4625` | es | 97 | 4.85 | 16 | it (20) | `Datasheet_CAD-201-DS-740-es.pdf` |
| `0560ef38` | es | 35 | 5.0 | 9 | pt (7) | `MIE-MP-530rv001` |
| `067598cb` | es | 269 | 5.723 | 17 | pt (47) | `MP-DT-951_v7.2.pdf` |
| `06c08203` | es | 414 | 6.088 | 17 | pt (68) | `MIDT951_v5-87` |
| `06d1d1d4` | en | 66 | 33.0 | 12 | pt (2) | `bcn-3100035-en_r006_2x-a_series_ad` |
| `0737509b` | en | 308 | 51.333 | 17 | pt (6) | `I56-3383-002 IDX-751 AE EN DE` |
| `08828182` | es | 306 | 4.708 | 17 | pt (65) | `MIE-MI-010.pdf` |
| `0903db56` | es | 353 | 6.193 | 17 | pt (57) | `MPDT951_v5-87.pdf` |
| `09194202` | en | 205 | 102.5 | 16 | pt (2) | `3103072-ml_r004_excellence_series_` |
| `0951df3f` | es | 470 | 5.281 | 18 | pt (89) | `33036_05_VESDA-E_VEA-040-A00_Produ` |
| `096795c0` | en | 65 | 3.824 | 13 | es (17) | `D 1150-1 BRH Morley` |
| `09c2bab5` | es | 72 | 4.0 | 12 | pt (18) | `FAAST Understanding EN54-20_SP` |
| `09ea54f3` | es | 107 | 4.864 | 15 | pt (22) | `fhsd8330-63296-es.pdf` |

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
| 6 | `bc163277` | `55310600 Manual TCD-106 kit_ES` | es | it (44) | Detnov |
| 7 | `f8132ff7` | `bcn-3100036-en_r002_2x-a_and_zp2-a_ser` | en | fr (3) | Aritech |
| 8 | `123dc496` | `MIE-MC-530` | es | it (44) | Morley |
| 9 | `aac0d826` | `10-5106-501-55nc-05_r005_iu2055nc_inst` | en | es (59) | Aritech |
| 10 | `08828182` | `MIE-MI-010` | es | pt (65) | Morley |
| 11 | `637cc4d7` | `2x-at-f2-fb-p-161721-es` | en | es (15) | Aritech |
| 12 | `0e9330c8` | `MIE-MI-530rv001` | es | it (16) | Morley |
| 13 | `c96bb93b` | `I56-3888-010 FAAST LT-200 Adv Guide` | en | pt (3) | Xtralis |
| 14 | `a2bb8ee1` | `Conexionado-del-modulo-M710-CZ-MI-DCZM` | es | pt (6) | Notifier |
| 15 | `537a0275` | `156-0551-005R EPS10_Eng` | en | pt (18) | System Sensor |
| 16 | `6096bdf6` | `MIE-MU-530rv001` | es | pt (33) | Morley |
| 17 | `09194202` | `3103072-ml_r004_excellence_series_inte` | en | pt (2) | Kidde |
| 18 | `bc0c7b5f` | `TIDT110` | es | en (17) | Notifier |
| 19 | `f5224079` | `04-4001-501-1700-06_r006_aritech_apic_` | en | pt (8) | Aritech |
| 20 | `217117c0` | `MADT212` | es | pt (32) | Notifier |
| 21 | `fc3d273e` | `085501945t_PA5_Installation_manual_D-G` | en | pt (5) | Pfannenberg |
| 22 | `0ad0a70f` | `MA-AL-T500-01-07 Manual TUL500esp rev1` | es | it (35) | Venitem |
| 23 | `c295d7f9` | `MNDT960I` | en | pt (5) | Notifier |
| 24 | `4112c5c1` | `MIE-MA-300_01` | es | pt (70) | Morley |
| 25 | `3138edc4` | `I56-2956-000_prelim` | en | es (53) | Morley |
| 26 | `0dde8e85` | `MIE-MC-130rv02` | es | it (38) | Morley |
| 27 | `be1b6b42` | `MNDT960I_iBox-BACnet` | en | pt (7) | Notifier |
| 28 | `d1299a40` | `DXc_Manual de configuracion` | es | pt (33) | Morley |
| 29 | `2c299ef1` | `D 1148-1 BRS Notifier` | en | es (25) | Notifier |
| 30 | `a107427f` | `Manual Testifire_Spanish` | es | pt (71) | Xtralis |

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
| **P-A** (sha real) | activo + single-extraction + dual-key (stem Y sha al MISMO blob) + grupo-sha singleton per-manufacturer + sha PLACEHOLDER (las filas que el UPDATE cambia realmente) | **0** |
| **P-B** (language) | activo + language NULL + detector v2 ENDURECIDO confianza ALTA (base del spec + supresion de token dominante + cruce de familia con margen >= 3x) | **406** |

**P-A, desglose (desviacion declarada #6):** el predicado literal del spec no menciona la clase de sha; aplicado tal cual da **992** documentos, de los cuales **992** YA tienen sha real (el UPDATE seria un no-op y falsearia el gate «aplicado == 100% de elegibles»). La cifra pre-registrada del packet es el subconjunto **placeholder = 0**. Ambas listas de `document_id` van en el JSON (`census.g_pre_registro`), ordenadas.

**P-B por idioma propuesto:** `{'en': 99, 'es': 307}`. Cohorte construida con el detector **endurecido (FIX 1+2+3)**; reconciliacion contra el predicado literal: `453 literal - 50 perdidos + 3 ganados = 406` (§5.4).

**Gate (e)(iii) sigue ABIERTO**: la QA-30 fresca de esta cohorte se emite como packet legible pero NO esta adjudicada -> **el staging de P-B NO esta autorizado**.

### 7.1 Techo declarado de P-A — por que cada documento NO entra (primer motivo, excluyente)

| motivo | documentos |
|---|---:|
| sha_real_64hex | 992 |
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
