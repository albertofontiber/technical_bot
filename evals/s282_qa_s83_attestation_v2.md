# s282 QA-s83 — ATESTACIÓN PARA FIRMA (Tramo 2) — v2

**Expediente para la decisión de Alberto** sobre aplicar el backfill de identidad s83 a `documents`
(Tramo 2 / T2). Re-emitida tras la adjudicación del dúo
(`evals/s282_t2_apply_duo_r1_adjudication_v1.yaml`, veredicto **RECHAZAR-EXPEDIENTE /
COHORTE-SANA**): los datos resisten, pero el expediente de firma necesitaba el ledger del draw
decisivo + el paquete de escritura sellado + un framing del bound honesto. Esta v2 los incorpora.

## VEREDICTO: cohorte v3 SANA · 0 defectos en el draw confirmatorio · **NO un bound limpio <5%@95%** · decisión de aceptación = de Alberto

- **0 defectos netos en la cohorte v3**, sobre **177 verificaciones de contenido a lo largo de
  3 draws independientes** (n=59 cada uno), **con la única clase-defecto cazada en draw 2 ya
  REMEDIADA y excluida** (guard de plausibilidad). El draw 3 (post-guard) es **59/59 OK con ledger
  fila-a-fila** (`evals/s282_qa_s83_lqas_draw3_v1.md`).
- **Esto NO es un bound limpio `<5%@95%`.** El estándar `batch_attested_v1` supone estratificación
  completa y un verificador ideal; aquí **(a)** varios estratos de marca tuvieron **inclusión cero**
  en cada draw (Sensitron, Pepperl-Fuchs, Edwards, Fidegas, Avotec, Securiton, y otros según el
  draw), y **(b)** la **sensibilidad del verificador es <100%** — el draw 1 **falso-aceptó**
  `ASD532_TD` (miembro de la clase-defecto que sí cazó el draw 2). El claim defendible es *"0
  defectos en 177 filas verificadas a lo largo de 3 draws, con re-scope justificado por un defecto
  CAZADO"*, no un intervalo de confianza cerrado. **La decisión de aceptación es de Alberto con este
  framing.**
- READ-ONLY, SELECT-only (`chunks_v2` / `documents`, PostgREST GET). 0 escrituras, 0 llamadas de
  modelo de pago. NO commits. **Nada aplicado a DB** — el paquete de escritura (§3) está sellado y
  listo para el paste de Alberto, no ejecutado.

---

## 1. Lo que el T2 escribiría EXACTAMENTE (cohorte v3, fill-only NULL-guard)

Fuente: `evals/s282_qa_s83_result_v3.json`, filas con `write_op ∈ {corroborate_noop,
fill_language_doctype}` que reciben ≥1 escritura (**533** filas). El T2 **rellena solo campos hoy
NULL** (jamás overwrite):

| eje | operación | filas | regla |
|---|---|---:|---|
| `doc_type` | **AUTO** — fill (DB NULL → s83) | **533** | `COALESCE(doc_type, :s83_doc_type)` |
| `language` (SINGLETON) | **AUTO** — fill (DB NULL, 1 idioma) | **301** | `COALESCE(language, :s83_lang)` |
| `product_model` | **NUNCA se escribe** | 0 | corroborate = NO-OP; family = etiqueta gobernada conservada |
| `manufacturer` / `brand` | **NUNCA se escribe** | 0 | fuera del alcance del T2 |
| `language` (MULTI, >1 idioma) | **ADVISORY** — NO auto | 209 | over-call de idioma s83 → Alberto |
| `language` contradicho en DB | **ADVISORY** — NO auto | 18 | nunca overwrite |
| `doc_type` distinto en DB | **ADVISORY** — NO auto | 11 | nunca overwrite |

- **Documentos tocados: 533** (todos reciben fill de `doc_type`; **el subconjunto de 301** además
  recibe fill de `language`-singleton; 0 filas escriben solo idioma). Verificado 1:1: cada uno de
  los 533 `source_file` mapea a **exactamente 1 documento ACTIVE** (0 huérfanos, 0 múltiples;
  cross-check contra los `active_document_ids` congelados del v1: **0 discrepancias**).
- **`product_model` NO se toca en ningún caso** (corroborate = NO-OP; family = etiqueta gobernada
  conservada; jamás replace con sola palabra del juez).

### 1b. Reparto por marca (auto-apply v3, 533 filas)

Notifier 294 · Morley 45 · Aritech 43 · Detnov 39 · Kidde 30 · System Sensor 26 · Spectrex 17 ·
Argus Security 11 · Pfannenberg 8 · Xtralis 5 · Honeywell 3 · Securiton 3 · Sensitron 3 ·
Pepperl-Fuchs 2 · Edwards 2 · Fidegas 1 · Avotec 1 = **533**.

---

## 2. El guard de plausibilidad de categoría (lo que remedió el draw 2)

El draw 2 (seed 592) cazó 1 defecto: s83 etiquetaba las «Descripción técnica / Technische
Beschreibung» (`_TD`) de Securiton — manuales de 118–129 pp — como `datasheet`.

**Qué es el guard, con precisión (no "de raíz" a secas):** una regla determinista $0 sobre **2
taxones cortos** (`datasheet` y `boletin` — los únicos géneros del enum definitoriamente breves):
si s83 propone auto-aplicar uno de esos 2 `doc_type` sobre un documento de **> 30 chunks** →
`adjudicate` (registro completo a Alberto; recall-safe). **Margen limpio:** el mayor `datasheet`
legítimo del corpus tiene **13** chunks y el mayor `boletin` **21** — muy por debajo de 30 — frente
a los **201–210** chunks de los `_TD` Securiton. El draw 3 lo confirma empíricamente: sus 7
`datasheet` muestreados tienen ≤ 7 chunks.

**LÍMITES DECLARADOS del guard (honestidad):** solo cubre esos 2 géneros cortos. Un error de
categoría en un género LARGO (p.ej. un `instalacion`/`guia_usuario` implausible, o un `otro`
sobre un documento que debería ser otra cosa) **NO lo caza este guard** — quedaría para el juicio
de contenido del draw o para Alberto. El guard **solo SACA filas** del auto-apply (dirección
segura), nunca añade.

**El guard movió exactamente 3 filas** (las 3 Securiton `_TD` `datasheet`): auto-apply **548→545**,
`doc_type` fills **536→533**, `language`-SG **304→301**, `adjudicate` +3 (`category_guard`).
Determinista 2× byte-idéntico (records-sha `2c6bac681ad89001`), frame == v2 (sin drift).

| source_file | marca | chunks | v2 → v3 | doc_type s83 (implausible) |
|---|---|---:|---|---|
| `ADW535_TD_T140358es_e` | Securiton | 201 | `fill…` → `adjudicate` | datasheet |
| `ASD532_TD_T140421es_a` | Securiton | 210 | `corroborate` → `adjudicate` | datasheet |
| `ASD533_TD_T140287es_e` | Securiton | 202 | `fill…` → `adjudicate` | datasheet |

---

## 3. El paquete de escritura — SELLADO, **NO aplicado** (gateado por la firma de Alberto)

Fix del hallazgo `PAQUETE-ESCRITURA-NO-SELLADO`. Generado por
`scripts/s282_t2_write_package.py` (READ-ONLY, $0):

- **Manifest por-fila:** `evals/s282_t2_manifest_v1.json` — 533 filas
  `{document_id, source_file, brand, doc_type, language (ESCALAR o null), db_state_at_freeze}`, con
  el **mapeo `source_file`→`document_id` congelado y verificado 1:1** y la provenance sellada.
- **SQL de aplicación:** `evals/s282_t2_apply_v1.sql` — una transacción `BEGIN…COMMIT` con:
  1. `t2_staging` (temp) con los `VALUES` del manifest;
  2. guards previos: conteo == 533 y todos los `document_id` existen y están `active`;
  3. `UPDATE documents … FROM t2_staging` **JOIN por id**, `COALESCE` fill-only + `WHERE (doc_type
     IS NULL OR language IS NULL)` (nunca overwrite), capturando el **before-image** (CTE `before` +
     `RETURNING`) en `t2_apply_audit`;
  4. **verificación post-apply** que aborta si `updated ≠ 533`, `doc_type_set ≠ 533`,
     `language_set ≠ 301`, o `overwrites ≠ 0`;
  5. `SELECT` del before-image completo (a guardar) + **rollback generado del before-image**
     (`SET doc_type/language = NULL` solo donde el valor era NULL y se rellenó);
  6. `COMMIT` (con nota: cambiar por `ROLLBACK` = dry-run que corre todos los guards sin persistir).

**Reversibilidad por construcción:** todo fill es NULL-guarded (`COALESCE` + `WHERE … IS NULL`) —
solo pasa campos `NULL → valor`; el rollback lo deshace desde el before-image; `product_model` no se
toca (nada que revertir en identidad).

---

## 4. Historia LQAS COMPLETA (3 draws, honestidad total)

Tres extracciones independientes, estratificadas por marca (largest-remainder), con **lectura de
contenido por agente** — un agente LLM lee el texto real de los chunks (SELECT `chunks_v2`), fila a
fila, sobre 3 ejes; **no es verificación por un humano**. Seeds distintas declaradas (streams de
Mersenne-Twister independientes por construcción; la proximidad 592↔593 no crea dependencia):

| draw | seed | cohorte | n | resultado | ledger | qué pasó |
|---|---:|---|---:|---|---|---|
| 1 | **282** | auto-apply original | 59 | 0 defectos — **NO fiable** | `lqas_sample_v1.md` | falso-aceptó `ASD532_TD` (miembro de la clase-defecto) |
| 2 (re-draw) | **592** | auto-apply v2 re-scoped | 59 | **1 defecto → PARADA** | `lqas_redraw_v1.md` | cazó `ADW535_TD` (`datasheet` sobre manual de 118 pp) — eje `doc_type`; contrato: PARO y reporto |
| 3 (confirmatorio) | **593** | **auto-apply v3 (post-guard)** | 59 | **0 defectos → confirma** | `lqas_draw3_v1.md` | la clase `_TD` `datasheet` ya está fuera; ledger fila-a-fila registrado |

- **Por qué el re-scope entre draws NO es seed-shopping:** el draw 2 PARÓ ante un defecto REAL y
  CAZADO; la remediación es un guard determinista de raíz (§2), no un ajuste de conveniencia; el
  draw 3 confirma sobre la cohorte ya remediada, con un draw fresco (seed distinta) y su ledger.
- **Solape del draw 3 (lo trajo el muestreo):** 5/59 con draw 1 (`MIDT1041`, `MNDT100`, `MNDT213`,
  `MNDT720`, `nc-mc-0-g`) y 3/59 con draw 2 (`55310021…CCD-100`, `AM-8100…rev 4`, `MNDT040P`); todas
  se re-verificaron igual, todas OK.
- El **ledger fila-a-fila del draw 3** (`evals/s282_qa_s83_lqas_draw3_v1.md`, fix
  `DRAW3-SIN-LEDGER`) registra evidencia de contenido por fila para las 59 — verificación fresca, no
  reconstrucción de memoria.

---

## 5. Honestidad — lo que esta atestación NO certifica

- **LQAS acota (imperfectamente) la TASA, no certifica cada fila.** Con los dos límites del §VEREDICTO
  (estratos inclusión-cero + sensibilidad del verificador <100%), el resultado **no es** un bound
  limpio `<5%@95%`. Es "0 defectos en 177 verificaciones a lo largo de 3 draws con re-scope por
  defecto cazado". La firma es de Alberto; el LQAS reduce el riesgo, no lo anula.
- **Otro `_TD` Securiton sigue en la cohorte, con etiqueta `otro` (NO defecto por el estándar).**
  `ASD535_TD_T131192es_h` (242 ch) es otra «Descripción técnica», pero s83 la etiqueta
  `doc_type=otro` (no `datasheet`) — está en el auto-apply con `doc_type=otro`. `otro` es el bucket
  catch-all defendible para un documento de referencia técnica (no es la afirmación
  implausible-corta que ataca el guard), así que **el guard NO la caza (correcto)** y **el draw 3 NO
  la muestreó** (Securiton tuvo 0 en el muestreo del draw 3). Se declara para que Alberto pueda, si
  quiere, fijar holísticamente la convención `doc_type` de los `_TD` Securiton — pero por el estándar
  **no es un defecto**.
- **`doc_type` sin definiciones formales:** los juicios entre categorías adyacentes (p.ej.
  `instalacion` vs `operacion` vs `configuracion` vs `guia_usuario` para un manual de central que
  cubre varias fases) se aceptaron cuando la etiqueta describe fielmente el género real; solo un
  error de categoría CLARO (como `datasheet` sobre un manual de 118 pp) cuenta como defecto. El
  ledger del draw 3 §4 documenta las adyacencias examinadas.
- **El guard es de alcance limitado y dirección segura** (§2): solo 2 géneros cortos, solo saca
  filas.

---

## 6. Reproducibilidad / provenance SELLADA

Fix del hallazgo `PROVENANCE-NO-SELLADA`: `result_v3` regenerado en el HEAD actual (records-sha
byte-idéntico — la cohorte no cambió, solo se re-estampó el commit), y shas sellados en el manifest
y aquí.

| artefacto | sello |
|---|---|
| commit HEAD | `ea4313d8d1e0ca2498afbc62f07fb944d8ec80b1` |
| `result_v3` records-sha (determinista 2×) | `2c6bac681ad8900116b493079e927a2a95a9a0bcb3304dd0887c9cab0fdfd593` |
| corpus fingerprint (`chunks_v2`=25090 · `documents`=1171) | `aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d` |
| manifest content-sha (determinista) | `429695ffd5650a65b6dc392e678bb0dc70292bd10e23e9d385c4edf92243ae48` |
| SQL `apply_v1.sql` (bytes) | `d5e1c48b891af137…` |
| s83 models / identity (sha256-LF) | `a1291a837a7f905c…` / `87bc0db79ead4e12…` |

- **Nota honesta sobre `worktree_dirty=true`:** el árbol tiene cambios NO relacionados con los
  insumos del expediente — el log/ficheros de la revisión adversarial del dúo y las salidas de esta
  propia lane. Ninguno es insumo de `result_v3` (que consume `result_v2` [commiteado] + el corpus
  congelado). Los INSUMOS están sellados por sha (records-sha + corpus-sha + s83 shas); su
  invariancia byte-a-byte al regenerar en el HEAD actual es la prueba de que la cohorte no derivó.
- Instrumentos: guard `scripts/s282_qa_s83_regate_v3.py`; draw 3 `scripts/s282_qa_s83_lqas_draw3.py`
  (seed 593); paquete `scripts/s282_t2_write_package.py`. Ledgers de los 3 draws:
  `evals/s282_qa_s83_lqas_sample_v1.md` (1), `…_lqas_redraw_v1.md` (2), `…_lqas_draw3_v1.md` (3).
- Worktree `Technical Bot-s281`, rama `claude/s282-h0t2-qa`. Sin commits.

```
FIRMA (Alberto): _______________________   fecha: __________
Aceptación con el framing del §VEREDICTO (no un bound limpio). Aplicar evals/s282_t2_apply_v1.sql
(dry-run con ROLLBACK primero; guardar el before-image del SELECT para el rollback post-COMMIT).
```
