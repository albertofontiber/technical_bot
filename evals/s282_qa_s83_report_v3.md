# s282 QA-s83 — RE-GATING v3: guard de plausibilidad de categoría (degradación de raíz)

El re-draw LQAS confirmatorio v1 (`evals/s282_qa_s83_lqas_redraw_v1.md`, seed 592) **NO pasó** el listón 0-defectos: 1 defecto / 59, fila `ADW535_TD_T140358es_e` (Securiton), eje `doc_type`. s83 etiqueta las «Descripción técnica / Technische Beschreibung» (`_TD_T140xxx`) de Securiton, manuales de 118–129 pp, como `datasheet`. Es una CLASE sistemática (3 ficheros en el lote de 536).

**Fix de RAÍZ (no parche de 3 ficheros):** guard determinista $0 — toda propuesta auto-apply de un `doc_type` de **clase corta** (boletin / datasheet — géneros definitoriamente breves) sobre un documento de **> 30 chunks** es un error de categoría detectable → `adjudicate` (el registro completo va a Alberto; recall-safe, nunca se auto-escribe). Un «datasheet» de 118 pp / 201 chunks es implausible por construcción y cazable con 0 llamadas de modelo.

READ-ONLY, SELECT-only (`chunks_v2.source_file` para contar chunks/documento), 0 escrituras, 0 modelo de pago. Consume los records FROZEN del v2 (baseline 2×-byte-idéntico) y aplica la etapa extra de gate. Guard 2× byte-idéntico (aserción). Frame verificado == v2 (sin drift).

## 1. Determinismo + frame

- guard 2× byte-idéntico: **IDÉNTICO** (`2c6bac681ad89001` == `2c6bac681ad89001`)
- corpus fingerprint == v2: **True** (chunks_v2=25090 · documents=1171 · sha `aa13e792339f7d3e`)
- commit HEAD: `667271fcdff395c0d8700889a23f2f9e64b7eff1` (dirty: True)

## 2. Filas movidas por el guard (declaración exacta)

**El guard mueve 3 filas** auto-apply → `adjudicate` (esperado: pocas). TODAS son la clase Securiton `_TD` `datasheet`; ninguna otra clase corta (`boletin`, máx 21 chunks) supera el umbral. Detalle:

| source_file | marca | chunks | write_op v2 → v3 | doc_type (s83) | language (s83) |
|---|---|---:|---|---|---|
| `ADW535_TD_T140358es_e` | Securiton | 201 | `fill_language_doctype` → `adjudicate` | `datasheet` | ['es'] |
| `ASD532_TD_T140421es_a` | Securiton | 210 | `corroborate_noop` → `adjudicate` | `datasheet` | ['es'] |
| `ASD533_TD_T140287es_e` | Securiton | 202 | `fill_language_doctype` → `adjudicate` | `datasheet` | ['es'] |

## 3. Cohortes v2 → v3

| write_op | v2 | v3 | Δ | destino |
|---|---:|---:|---:|---|
| `corroborate_noop` | 423 | 422 | -1 | **AUTO-APPLY** |
| `fill_language_doctype` | 125 | 123 | -2 | **AUTO-APPLY** |
| `adjudicate` | 423 | 426 | +3 | [ALBERTO] |
| `excluded_t3` | 28 | 28 | +0 | excluido (T3) |
| `unmapped` | 15 | 15 | +0 | fuera de alcance |
| **TOTAL** | **1014** | **1014** | 0 | |

**Auto-apply v2 → v3: 548 → 545** (-3).

### 3b. Desglose de `adjudicate` (nuevo bucket `category_guard`)

| sub-relación | v2 | v3 |
|---|---:|---:|
| `doc_noise` | 301 | 301 |
| `disjoint` | 59 | 59 |
| `s83_generic` | 30 | 30 |
| `s83_empty` | 21 | 21 |
| `corrob_allmodels` | 9 | 9 |
| `corrob_prim` | 2 | 2 |
| `judge_pull` | 1 | 1 |
| `category_guard` | 0 | 3 |

## 4. Fill summary (eje a eje) v2 → v3

| eje | v2 | v3 | Δ |
|---|---:|---:|---:|
| `doc_type` AUTO (DB NULL → s83) | 536 | 533 | -3 |
| `language` SINGLETON AUTO | 304 | 301 | -3 |
| `language` MULTI (advisory, no auto) | 209 | 209 | +0 |
| `language` contradicho (advisory) | 18 | 18 | +0 |
| `doc_type` distinto en DB (advisory) | 11 | 11 | +0 |

`product_model` NUNCA se auto-escribe (corroborate_noop = NO-OP; family = etiqueta gobernada conservada) — invariante desde v2.

## 5. Qué NO cambia y honestidad

- El guard **sólo puede SACAR** filas del auto-apply (dirección segura); nunca añade ninguna.
- `language`-MULTI sigue ADVISORY (over-call de idioma, v2). El guard es ortogonal: ataca el eje `doc_type` (género implausible), no el idioma.
- Las 3 filas movidas tenían `language='es'` singleton CORRECTO (verificado en el re-draw v1); aun así el registro COMPLETO va a Alberto (recall-safe: si s83 confunde el género del documento, el registro entero es sospechoso). El coste es 3 fills de idioma correctos que Alberto revisará, no un auto-write erróneo.
- La firma del lote sigue GATEADA por un re-draw LQAS confirmatorio (draw 3, seed distinta) sobre la cohorte v3 a 0-defectos — este re-gate no la sustituye.
