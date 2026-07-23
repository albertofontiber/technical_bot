# s281 H0 — Census de identidad/lineage del corpus + plan de backfill — v1

Instrumento: `scripts/s281_h0_identity_census.py`. **READ-ONLY (PostgREST GET), SELECT-only, 0 llamadas a modelos, 0 escrituras.** El census ADJUDICA el estado vivo; toda propuesta de cambio se emite como PROPUESTA SQL (jamás aplicada). Hereda de `s279_selection_census.py` (stack GET-only + fingerprint A1 + auditoría de identidad) y de `s278_identity_census.py` (contrato de determinismo 2× + disciplina de honestidad).

## Freeze-contract

- commit HEAD: `d7723194c8f4e2ba9b45f1131bb50d3e395bd2f4` (worktree dirty: True)
- corpus fingerprint: chunks_v2=25090 · documents=1171 · sha256 `aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d`
- **determinismo 2×: IDÉNTICO ✅** (pass1 sha `6e63cbd05d7733cb` == pass2 sha `6e63cbd05d7733cb`)
- gold baseline: `evals\bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml` sha256-LF `1f5bf19c6bcf8965d48683985d8d415d5d6e4993674072c35e140e0b8e7e4cf6`
- doc_map: `data\catalog\doc_map.jsonl` sha256-LF `67cb2b66dd2ccf9cd7bc2f84d0b2d06b8eaf84b8db77533aa07fa76cebae5161`
- activo s83 (mapa doc→modelos): present=True · `evals\s83_document_models_final.jsonl` sha256-LF `a1291a837a7f905c3a7939cd847675a94811a47073fa12143070c0f61b177b19`
- generado 2026-07-23T21:00:51.861519+00:00

## 1. Titular

De **998 documentos activos** (1171 totales), solo existen **6 lineages** en `document_revision_lineages` (**6 verified**). Bajo el modelo del gate proximal del RPC (`unverified_document_lineage` — src/rag/document_local_coverage.py:887-930), hoy son servibles por la vía document-local **6 documentos activos**. El resto muere aguas arriba de toda la lógica de selección (confirma y generaliza el H0 de s279/DEC-152: 12/15 QIDs P1 bloqueados). El cuello dominante NO es la selección: es un **backfill de identidad + verificación de lineage**.

Reconciliación con s279: los 6 docs servibles corpus-wide = los 6 lineages verified (HP011 RP1r + CAD-250 MC-380/MS-416 + HOP-138-8/9ES + 4188-1132-ES). De esos, solo 3 caen bajo los 15 QIDs-probe de s279 (cat017/cat019/hp011) — de ahí el «3 de 15» de aquel census vs los 6 de éste (corpus completo). El resto de lineages cubre revisiones/documentos fuera del set P1.

## 2. Conteos por clase de gap (documentos ACTIVOS)

| Clase de gap | Documentos activos | % de activos |
|---|---:|---:|
| A — `source_pdf_sha256='backfill:*'` (placeholder, no 64-hex) | 590 | 59.1% |
| B — `revision_lineage_id IS NULL` (sin lineage → unverified) | 992 | 99.4% |
| B2 — lineage presente pero `authority_status != 'verified'` | 0 | 0.0% |
| C — `language IS NULL` | 902 | 90.4% |
| C — `doc_type IS NULL` | 970 | 97.2% |
| C — `product_model IS NULL` (nivel documento) | 0 | 0.0% |
| C — `manufacturer IS NULL` | 0 | 0.0% |
| T1 — identity-completo (es) SOLO falta lineage verified | 5 | 0.5% |
| ✅ SERVIBLE hoy (lineage verified + identidad completa + es) | 6 | 0.6% |

Distribución de `authority_status` en los 6 lineages: `{'verified': 6}`. Chunks con `product_model` unknown/NULL: **318** de 25090 (1.3%).

### 2.1 Clase A (backfill sha) por marca — top 15

| Marca | Docs activos con sha backfill |
|---|---:|
| Notifier | 339 |
| Morley | 66 |
| Detnov | 53 |
| System Sensor | 30 |
| Xtralis | 26 |
| Spectrex | 13 |
| Argus Security | 12 |
| LDA audioTech | 11 |
| Pfannenberg | 9 |
| Securiton | 8 |
| Fidegas | 6 |
| Pepperl-Fuchs | 3 |
| Avotec | 2 |
| LGM Products | 2 |
| COELBO | 1 |

### 2.2 Clase B (lineage NULL) por marca — top 15

| Marca | Docs activos sin lineage |
|---|---:|
| Notifier | 463 |
| Morley | 236 |
| Detnov | 57 |
| Aritech | 49 |
| Kidde | 35 |
| System Sensor | 30 |
| Xtralis | 28 |
| Spectrex | 17 |
| Pfannenberg | 13 |
| Argus Security | 12 |
| LDA audioTech | 11 |
| Securiton | 8 |
| Fidegas | 6 |
| Edwards | 3 |
| Honeywell | 3 |

## 3. Clase D — findability por `product_model='unknown'/NULL` (nivel chunk)

- source_files ENTERAMENTE unknown/NULL (peor findability): **28**
- source_files PARCIALMENTE unknown/NULL: **0**

**Pin ZXSe (brief):** `MIE-MI-600` = **88 chunks `product_model='unknown'`** (de 88 totales; 80 no-duplicados) · marcas {'Morley': 88} · 1 documento(s). Verifica el ground-truth s78 (Morley ZXSe / MIE-MI-600).

Top 15 source_files enteramente unknown por volumen de chunks:

| source_file | chunks unknown | (no-dup) | marcas |
|---|---:|---:|---|
| `MIE-MI-600` | 88 | 80 | ['Morley'] |
| `FS2-1` | 30 | 28 | ['Notifier'] |
| `ms1-2-4` | 29 | 27 | ['Morley'] |
| `Manual-de-Usuario-S3-T1-y-S-2-T1` | 28 | 17 | ['Fidegas'] |
| `Manual-de-Usuario-S3-T2-y-S2-T2` | 24 | 22 | ['Fidegas'] |
| `I56-2006-004 MI-DMMI_DMM2I_D2ICMO` | 17 | 15 | ['Morley'] |
| `BANI-G-24_Eng` | 16 | 13 | ['Hosiden Besson'] |
| `LocatorPlus-Installation-Manual-1.3` | 16 | 8 | ['LGM Products'] |
| `I56-3388-002 NFX-OPT_multi` | 9 | 8 | ['Notifier'] |
| `I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE` | 9 | 8 | ['Morley'] |
| `I56-3389-002 NFX-SMT2_multi` | 7 | 6 | ['Notifier'] |
| `Manual_DXD-2X0 (55321002 MI 607 m 2024 c)` | 7 | 5 | ['Detnov'] |
| `I56-5005-002_D Notifier Sounder Strobe` | 6 | 2 | ['Notifier'] |
| `MIE-MP-525rv1` | 6 | 6 | ['Morley'] |
| `I56-5004-000-Notifier-Strobe` | 5 | 2 | ['Notifier'] |

## 4. Cruce con catálogo (`doc_map.jsonl`) — documentos sin mapeo a producto

Documentos activos SIN entrada de producto en el catálogo gobernado: **149**. Estos no resuelven por identidad query-side (ni por la vía document-local ni por el model-filter) hasta que se mapean. Muestra (top 15 por marca):

| marca | source_pdf_filename | product_model (doc) |
|---|---|---|
| Aritech | `00-3280-507-4003-03_r003_2x-a_series_quick_insta` | 2X-A Táctil |
| Aritech | `00-3280-507-4009-03_r003_2x-a_series_quick_insta` | 2X-A |
| Aritech | `00-3280-508-4009-03_r003_2x-a_series_quick_opera` | 2X-A |
| Aritech | `bcn-3100035-en_r006_2x-a_series_addressable_cont` | 2X-A Táctil |
| Aritech | `bcn-3100036-en_r002_2x-a_and_zp2-a_series_addres` | 2X-A Táctil |
| Avotec | `Manual Rotulo REXD-103_EN` | unknown |
| Edwards | `04-4001-501-2009-12_r012_modulaser_en_54-20_inst` | FHSD8310 |
| Fidegas | `Manual-de-Usuario-S3-2` | unknown |
| Fidegas | `Manual-de-Usuario-S3-IR-y-S-2-IR` | S3-IR |
| Fidegas | `Manual-de-Usuario-S3-T1-y-S-2-T1` | S3-T1 |
| Kidde | `bcn-3100019-es_r002_nc_series_fire_alarm_control` | NC |
| Kidde | `bcn-3100020-es_r002_nc_series_fire_alarm_control` | NC |
| Morley | `30012012  TARJETAS IDIOMAS VISION SUPRA rev A` | Vision Supra |
| Morley | `996-130-000-3 Manuel d'utilisation ZX_hlsi` | ZXe |
| Morley | `Actulización histórico TG` | TG-Honeywell |

## 5. Impacto directo en los QIDs del baseline (bot_sources → documentos → estado)

De **39 QIDs** del baseline oficial 39, **33** tienen TODOS sus documentos citados bloqueados por el gate de identidad (ninguno servible por la vía document-local), y **6** tienen al menos un documento citado servible hoy. NOTA: el bloqueo document-local NO implica que el bot falle el QID — el bot sirve por retrieval vector/léxico + rerank; document-local es una LANE de recuperación de cobertura. Este cruce mide qué QIDs se beneficiarían del unlock.

| QID | veredicto | conducta | bot_sources | docs resueltos | bloqueados | servibles | todos-bloqueados |
|---|---|---|---:|---:|---:|---:|:--:|
| cat001 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| cat005 | PASS | answer | 4 | 4 | 4 | 0 | 🔴 |
| cat007 | PARCIAL | answer | 6 | 6 | 6 | 0 | 🔴 |
| cat008 | PARCIAL | answer | 5 | 5 | 5 | 0 | 🔴 |
| cat009 | PASS | answer | 4 | 4 | 4 | 0 | 🔴 |
| cat010 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| cat011 | PARCIAL | clarify | 9 | 9 | 9 | 0 | 🔴 |
| cat012 | PASS | answer | 3 | 3 | 3 | 0 | 🔴 |
| cat013 | PASS | refuse-inference | 4 | 4 | 4 | 0 | 🔴 |
| cat014 | PASS | answer | 1 | 1 | 1 | 0 | 🔴 |
| cat015 | PARCIAL | admit | 2 | 2 | 2 | 0 | 🔴 |
| cat016 | FALLO | answer | 2 | 2 | 2 | 0 | 🔴 |
| cat017 | PARCIAL | answer | 3 | 3 | 0 | 3 | · |
| cat018 | PASS | answer | 1 | 1 | 1 | 0 | 🔴 |
| cat019 | PARCIAL | answer | 2 | 2 | 0 | 2 | · |
| cat020 | PARCIAL | answer | 8 | 8 | 8 | 0 | 🔴 |
| cat021 | PASS | clarify | 8 | 8 | 8 | 0 | 🔴 |
| cat022 | FALLO | answer | 3 | 3 | 3 | 0 | 🔴 |
| cat023 | PARCIAL | answer | 1 | 1 | 1 | 0 | 🔴 |
| cat024 | PASS | answer | 6 | 6 | 4 | 2 | · |
| hp001 | PASS | answer | 2 | 2 | 1 | 1 | · |
| hp002 | PARCIAL | answer | 5 | 5 | 5 | 0 | 🔴 |
| hp003 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp004 | PARCIAL | clarify | 1 | 1 | 1 | 0 | 🔴 |
| hp005 | PARCIAL | answer | 5 | 5 | 5 | 0 | 🔴 |
| hp006 | PARCIAL | answer | 4 | 4 | 4 | 0 | 🔴 |
| hp007 | PASS | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp008 | PARCIAL | answer | 4 | 4 | 4 | 0 | 🔴 |
| hp009 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp010 | PARCIAL | answer | 7 | 7 | 7 | 0 | 🔴 |
| hp011 | PARCIAL | answer | 3 | 4 | 2 | 2 | · |
| hp012 | PARCIAL | answer-con-conflicto | 5 | 5 | 5 | 0 | 🔴 |
| hp013 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp014 | PARCIAL | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp015 | PARCIAL | answer | 1 | 1 | 1 | 0 | 🔴 |
| hp017 | PARCIAL | answer | 4 | 4 | 4 | 0 | 🔴 |
| hp018 | PASS | answer | 3 | 3 | 3 | 0 | 🔴 |
| hp019 | PASS | answer | 2 | 2 | 2 | 0 | 🔴 |
| hp020 | PARCIAL | answer | 2 | 2 | 1 | 1 | · |

## 6. Plan de backfill priorizado por tramos (PROPUESTAS SQL — JAMÁS aplicadas)

Los tramos están ordenados por **palanca/coste**: primero lo que desbloquea más QIDs por menos decisiones de producto. TODAS las sentencias son PROPUESTAS; requieren GO de Alberto y se aplicarían vía `supabase/migration_proposals/` (no por este script).

Volumen por clase (documentos activos afectados + chunks de esos documentos):

| Clase | Documentos | Chunks |
|---|---:|---:|
| T1 — identity-completo, falta lineage | 5 | 355 |
| A — sha backfill | 590 | 16333 |
| B — lineage NULL | 992 | 24182 |
| B2 — lineage no-verified | 0 | 0 |
| C — language NULL | 902 | 23602 |
| C — doc_type NULL | 970 | 23773 |
| C — product_model NULL (doc) | 0 | 0 |

### Tramo 1 — Verificación de lineage para los documentos ya identity-completos (mayor palanca, menor riesgo)

**5 documentos activos** ya están identity-completos (manufacturer+product_model+doc_type +language='es') y solo les falta un lineage `verified` — es la cohorte de MENOR riesgo (no re-etiqueta identidad, solo firma la verificación). Es el patrón EXACTO que s279 usó para los 6 docs servibles hoy (HP011 RP1r + 2 probes + lote inicial). Cada uno requiere que Alberto confirme la evidencia de autoridad, pero NO decisiones de producto.

```sql
-- PROPUESTA (NO aplicada). Crear/verificar lineage para un documento identity-completo.
-- [ALBERTO decide] el authority_contract y la evidencia por documento.
INSERT INTO document_revision_lineages (id, authority_status, authority_contract, notes)
VALUES (gen_random_uuid(), 'verified', 'explicit_document_ids_v1', '<qid/motivo>')
RETURNING id;  -- luego:
UPDATE documents SET revision_lineage_id = '<nuevo_id>'
 WHERE id = '<document_id>' AND status='active';  -- solo docs con idioma/doc_type/pm completos
```

**Desbloquea:** los QIDs del baseline cuyo doc citado ya está identity-completo (ver §5, columna 'servibles'=0 pero sin gaps de identidad C). Verificar a mano cada uno antes de proponer.

### Tramo 2 — Backfill de identidad C (language/doc_type/product_model NULL) — 590 docs clase A + los C

La clase A (sha `backfill:*`) coincide en gran parte con language/doc_type NULL. Poblar estos campos es prerequisito de la verificación de lineage para esa cohorte. La fuente candidata de `product_model` es el activo s83 (`s83_document_models_final.jsonl`), pero **requiere QA + adjudicación [ALBERTO]** (s84 no ejecutado).

```sql
-- PROPUESTA (NO aplicada). Poblar identidad desde s83 tras QA de Alberto.
UPDATE documents SET language='es', doc_type='<tipo>', product_model='<modelo s83 QA'd>'
 WHERE id='<document_id>' AND status='active';
-- (el sha real 64-hex se recomputa del PDF fuente en un paso de ingest, no en SQL)
```

### Tramo 3 — Clase D findability: re-tag `product_model='unknown'` en chunks_v2 (ej. ZXSe)

El caso vivo: `MIE-MI-600` con **88 chunks `unknown`** (Morley ZXSe). El bot admite no tener el manual porque el model-filter no lo encuentra por modelo. **[ALBERTO]: split D1 por nº de lazos** (ground-truth s78: ZX1Se/2Se/5Se/10Se) — el census NO decide la granularidad. Patrón reversible DB-only (s78/s80).

```sql
-- PROPUESTA (NO aplicada). Re-tag DB-only reversible (patrón s78/s80).
-- [ALBERTO decide] si es familia genérica 'ZXSe' o split por lazos.
UPDATE chunks_v2 SET product_model='ZXSe', manufacturer='Morley'
 WHERE source_file='MIE-MI-600' AND product_model='unknown';
```

### Tramo 4 — Mapeo a catálogo de los 149 docs sin producto

Los documentos activos sin entrada en `doc_map.jsonl` no resuelven query-side. El activo s83 cubre 1014 source_files; el gap son los documentos activos no cubiertos. Es trabajo de curación de catálogo (workstream DEC-074), no SQL puntual.

## 7. Spot-checks (3 filas por clase, con la query exacta)

### class_A_sha_backfill_placeholder
- query: `GET /documents?status=eq.active&source_pdf_sha256=like.backfill:*&select=id,status,manufacturer,product_model,doc_type,language,source_pdf_filename,source_pdf_sha256,revision,revision_lineage_id,document_family,ingested_at`
  - `{"document_id": "017af6a2-e90c-4405-a500-0b2bd1a39d63", "source_pdf_filename": "18995_03_VESDA_VLI_Installation_Sheet_lores_A3", "manufacturer": "Xtralis", "product_model": "VESDA VLI Installation", "source_pdf_sha256_state": "backfill_placeholder", "language": null, "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "0216c070-9a50-4109-b161-de0a583c9696", "source_pdf_filename": "ASD IN Rail Transportation Applications_ES", "manufacturer": "Notifier", "product_model": "faast-", "source_pdf_sha256_state": "backfill_placeholder", "language": null, "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "0295feed-a23c-479a-af0a-d4a6247d3f3e", "source_pdf_filename": "MADT370", "manufacturer": "Notifier", "product_model": "NOTI-FIRE-NET", "source_pdf_sha256_state": "backfill_placeholder", "language": null, "doc_type": null, "revision_lineage_id": null}`

### class_B_lineage_id_null
- query: `GET /documents?status=eq.active&revision_lineage_id=is.null&select=id,status,manufacturer,product_model,doc_type,language,source_pdf_filename,source_pdf_sha256,revision,revision_lineage_id,document_family,ingested_at`
  - `{"document_id": "0037a1f2-c8ad-4221-8e1c-3a410f201171", "source_pdf_filename": "HLSI-MI-580I.pdf", "manufacturer": "Morley", "product_model": "unknown", "source_pdf_sha256_state": "valid_64hex", "language": null, "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "0119436e-4676-4110-a351-9c8da48e472f", "source_pdf_filename": "Con-que-Sistema-Operativo-es-compatible-el-programa-de-la-DXc-Connexion.pdf", "manufacturer": "Morley", "product_model": "unknown", "source_pdf_sha256_state": "valid_64hex", "language": "es", "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "0131512d-e62d-4c40-b6a6-2c776760c5cc", "source_pdf_filename": "Morley-Se-pueden-pasar-programaciones-de-ZX-y-Dimension-a-Connexion-DXC.pdf", "manufacturer": "Morley", "product_model": "unknown", "source_pdf_sha256_state": "valid_64hex", "language": "de", "doc_type": null, "revision_lineage_id": null}`

### class_C_language_null
- query: `GET /documents?status=eq.active&language=is.null&select=id,status,manufacturer,product_model,doc_type,language,source_pdf_filename,source_pdf_sha256,revision,revision_lineage_id,document_family,ingested_at`
  - `{"document_id": "0037a1f2-c8ad-4221-8e1c-3a410f201171", "source_pdf_filename": "HLSI-MI-580I.pdf", "manufacturer": "Morley", "product_model": "unknown", "source_pdf_sha256_state": "valid_64hex", "language": null, "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "017af6a2-e90c-4405-a500-0b2bd1a39d63", "source_pdf_filename": "18995_03_VESDA_VLI_Installation_Sheet_lores_A3", "manufacturer": "Xtralis", "product_model": "VESDA VLI Installation", "source_pdf_sha256_state": "backfill_placeholder", "language": null, "doc_type": null, "revision_lineage_id": null}`
  - `{"document_id": "01c8e123-864e-434a-80c3-6427d9de7ce8", "source_pdf_filename": "TIDT070.pdf", "manufacturer": "Notifier", "product_model": "LáserStar", "source_pdf_sha256_state": "valid_64hex", "language": null, "doc_type": null, "revision_lineage_id": null}`

### class_D_zxse_pin
- query: `GET /chunks_v2?source_file=eq.MIE-MI-600&product_model=eq.unknown&select=id,product_model,manufacturer (count)`
  - result: `{"source_file": "MIE-MI-600", "total_chunks": 88, "unknown_chunks": 88, "unknown_nondup": 80, "manufacturers": {"Morley": 88}, "document_ids": ["4ca173e2-c1b2-40ea-8778-4148e08b8533"]}`

### lineages_present
- query: `GET /document_revision_lineages?select=id,authority_status,notes`
  - `{"id": "8a1fafce-d9a7-51da-bd2a-c0ca9fdd0429", "authority_status": "verified", "notes": "HP011 HLSI-MN-103 RP1r-Supra ES v.04 -> v.07; exact source-contract adjudication"}`
  - `{"id": "9e1edc8f-4148-4cce-9aaf-08a348ed18bc", "authority_status": "verified", "notes": "CAD-250 MC-380 ES: CAD-250-MC-380-es.pdf (superseded, bc6bdd33-72e6-4054-9ce4-60"}`
  - `{"id": "c968b0e2-82bd-4f26-a2c8-c5decfff6a6d", "authority_status": "verified", "notes": "HOP-138-9ES issue 5_11-2025_In (active, 79a3471a); single-revision; adjudicado A"}`
  - `{"id": "d9f177c0-66de-4557-af4b-f61c216ab1c2", "authority_status": "verified", "notes": "4188-1132-ES issue 3_04_2025_Qref (active, 81c783f5); single-revision; adjudicad"}`
  - `{"id": "e582cdbc-985e-429a-ba49-e1cbb6f74496", "authority_status": "verified", "notes": "HOP-138-8ES  issue 6_01-2026_Co (active, 80e1b7d2-1455-454d-8545-18b858ba9a70); "}`
  - `{"id": "fbbd8636-0465-4c57-acb6-4953022474c8", "authority_status": "verified", "notes": "CAD-250 MS-416 ES: CAD-250-MS-416-es.pdf (superseded, 03b1ccf6) -> CAD-250_Manua"}`

## 8. Honestidad del instrumento — lo que este census NO juzga

- **El gate del RPC es servidor-side.** El census MODELA el gate proximal (`unverified_document_lineage`) desde el estado de identidad leído read-only; no ejecuta el RPC ni el retrieve→rerank de pago. Un documento marcado 'servible' aquí es servible por identidad; su selección real depende del pool y del reranker (fuera de $0). Concuerda con el corolario de s279 (D1/D2).
- **`servable_document_local_lane` ≠ 'el bot responde bien el QID'.** El bot sirve por retrieval vector/léxico+rerank; la vía document-local es una lane de COBERTURA. El cruce §5 mide beneficiarios del unlock, no fallos causales del bot.
- **Product decisions son de Alberto.** El split D1 de ZXSe por nº de lazos (ground-truth s78: ZX1Se/2Se/5Se/10Se en MIE-MI-600) y qué `product_model`/`manufacturer` asignar en el backfill son [ALBERTO]. El census cuantifica el volumen; NO decide la etiqueta.
- **El activo s83** (`evals/s83_document_models_final.jsonl`, 1014 source_files → modelos) es la fuente candidata para poblar `product_model`/identidad en el backfill, pero su aplicación requiere QA + adjudicación de conflictos (s84, no ejecutado). El census lo referencia, no lo aplica.
