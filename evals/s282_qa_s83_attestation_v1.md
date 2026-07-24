# s282 QA-s83 — ATESTACIÓN LISTA PARA FIRMA (Tramo 2) — v1

**Bloque listo-para-firma de Alberto** para aplicar el backfill de identidad s83 sobre `documents`
(Tramo 2 / T2). Estándar `batch_attested_v1`: muestra confirmatoria n=59, aceptar SOLO con
**0 defectos** ⇒ garantiza tasa de defecto real **< 5 % con 95 % de confianza**. La cohorte
atestada es la **v3 re-gateada** (`evals/s282_qa_s83_result_v3.json`), tras el guard de
plausibilidad de categoría que remedió el defecto que tumbó el draw 2.

## VEREDICTO: la cohorte auto-apply v3 QUEDA ATESTADA — draw 3 = 0 defectos / 59.

- **59/59 OK · 0 DEFECTOS** — verificación 100 % manual leyendo el CONTENIDO real de chunks
  (SELECT), fila a fila: `doc_type` contra la estructura real del documento; `language` singleton
  contra el idioma de **REDACCIÓN** del cuerpo (no tokens sueltos).
- El listón `batch_attested_v1` (0 defectos) **SE CUMPLE** ⇒ la cohorte auto-apply v3 (545 filas)
  queda acotada a < 5 % de defecto (95 % conf.) y **es firmable por Alberto**.
- READ-ONLY, SELECT-only (`chunks_v2` / `documents`, PostgREST GET). 0 escrituras, 0 llamadas de
  modelo de pago. NO commits. Nada aplicado a DB (los SQL de §3 son plantilla, NO ejecutados).

---

## 1. Lo que el T2 escribiría EXACTAMENTE (recuentos finales por eje, cohorte v3)

Fuente de valores: `evals/s282_qa_s83_result_v3.json`, filas con `write_op ∈ {corroborate_noop,
fill_language_doctype}` (**545** filas auto-apply). El T2 **rellena solo campos hoy NULL** (fill-only,
NULL-guard, jamás overwrite):

| eje | operación | filas que escribe | regla |
|---|---|---:|---|
| `doc_type` | **AUTO** — fill (DB NULL → s83) | **533** | `COALESCE(doc_type, :s83_doc_type)` |
| `language` (SINGLETON) | **AUTO** — fill (DB NULL, 1 idioma) | **301** | `COALESCE(language, :s83_lang_singleton)` |
| `product_model` | **NUNCA se escribe** | 0 | corroborate = NO-OP; family = etiqueta gobernada conservada |
| `language` (MULTI, >1 idioma) | **ADVISORY** — NO auto | 209 | over-call de idioma s83 (draw 2) → Alberto/verificar-contenido |
| `language` contradicho en DB | **ADVISORY** — NO auto | 18 | nunca overwrite |
| `doc_type` distinto en DB | **ADVISORY** — NO auto | 11 | nunca overwrite |

- **Documentos tocados por el auto-apply: 533** (todo fill de `language`-singleton recae sobre una
  fila que además recibe fill de `doc_type`; los 12 restantes del cohorte 545 son NO-OP puro — pm
  corroborado, ejes ya poblados o advisory — no escriben nada).
- **`product_model` NO se toca en ningún caso.** El eje pm es NO-OP (corroborado exacto) o etiqueta
  de familia gobernada conservada; jamás replace (prohibido con sola palabra del juez — finding 5/7 v2).

### 1b. Reparto por marca del auto-apply v3 (para los lotes SQL de §3)

| marca | `doc_type` fill | `language`-SG fill | marca | `doc_type` fill | `language`-SG fill |
|---|---:|---:|---|---:|---:|
| Notifier | 294 | 192 | Xtralis | 5 | 4 |
| Morley | 45 | 13 | Honeywell | 3 | 1 |
| Aritech | 43 | 21 | Securiton | 3 | 2 |
| Detnov | 39 | 6 | Sensitron | 3 | 1 |
| Kidde | 30 | 14 | Pepperl-Fuchs | 2 | 2 |
| System Sensor | 26 | 15 | Edwards | 2 | 0 |
| Spectrex | 17 | 16 | Fidegas | 1 | 0 |
| Argus Security | 11 | 11 | Avotec | 1 | 1 |
| Pfannenberg | 8 | 2 | **TOTAL** | **533** | **301** |

---

## 2. El guard de plausibilidad de categoría (degradación de raíz que habilitó el draw 3)

El draw 2 (re-draw, seed 592) cazó 1 defecto: s83 etiqueta las «Descripción técnica /
Technische Beschreibung» (`_TD`) de Securiton — manuales de 118–129 pp — como `datasheet`. Fix de
RAÍZ ($0, determinista, `scripts/s282_qa_s83_regate_v3.py`): **toda propuesta auto-apply de un
`doc_type` de clase corta (`datasheet` / `boletin` — géneros definitoriamente breves) sobre un
documento de > 30 chunks → `adjudicate`** (registro completo a Alberto; recall-safe). No es un
parche de 3 ficheros: es una regla general de género implausible.

**El guard movió 3 filas** auto-apply → `adjudicate` (bucket `category_guard`). Las 3 son la clase
Securiton `_TD` `datasheet`; ninguna otra clase corta supera el umbral (el mayor `datasheet` legítimo
tiene 13 chunks; el mayor `boletin`, 21). Margen limpio enorme (siguiente datasheet real = 13 ch ≪ 30 ≪ 201 ch).

| source_file | marca | chunks | write_op v2 → v3 | doc_type s83 (implausible) |
|---|---|---:|---|---|
| `ADW535_TD_T140358es_e` | Securiton | 201 | `fill_language_doctype` → `adjudicate` | datasheet |
| `ASD532_TD_T140421es_a` | Securiton | 210 | `corroborate_noop` → `adjudicate` | datasheet |
| `ASD533_TD_T140287es_e` | Securiton | 202 | `fill_language_doctype` → `adjudicate` | datasheet |

Impacto en cohortes: auto-apply **548 → 545**; `doc_type` fills **536 → 533**; `language`-SG
**304 → 301**; `adjudicate` 423 → 426 (`category_guard`=3). Determinista 2× byte-idéntico;
frame idéntico a v2 (sin drift).

---

## 3. SQL por lotes por marca — PLANTILLA, **NO aplicada** (gateado por la firma de Alberto)

Ningún SQL se ejecuta aquí (READ-ONLY). Plantilla reversible, un lote por marca, fill-only con
NULL-guard. Los valores concretos (`:document_id`, `:s83_doc_type`, `:s83_lang_singleton`) salen de
`evals/s282_qa_s83_result_v3.json` (`records` con `write_op ∈ {corroborate_noop,
fill_language_doctype}`; `fill_plan.doc_type_value` y — SOLO si `fill_plan.language_fill_singleton
= true` — `fill_plan.language_value`).

```sql
-- Aplicar SOLO tras la firma de esta atestación. Un lote por marca (§1b).
-- AUTO = doc_type (todas las filas del lote) + language SOLO cuando language_fill_singleton = true.
UPDATE documents d SET
  doc_type = COALESCE(d.doc_type, :s83_doc_type),          -- fill-only; NULL-guard
  language = COALESCE(d.language, :s83_language_singleton)  -- SOLO singleton; multi = advisory
WHERE d.id = :document_id
  AND (d.doc_type IS NULL OR d.language IS NULL);           -- nunca overwrite
-- product_model: NO se toca (corroborate_noop = NO-OP; family = etiqueta gobernada conservada).
-- language-MULTI (209), language-contradicho (18), doc_type-distinto (11): NO en el UPDATE -> packet advisory de Alberto.
-- Las 3 filas Securiton _TD (§2): NO en el UPDATE -> adjudicate (category_guard).
```

### Reversibilidad (por construcción)

- Todo fill es NULL-guarded (`COALESCE` + `WHERE ... IS NULL`): **nunca sobrescribe** un valor
  existente, así que el UPDATE solo puede pasar campos `NULL → valor`.
- **Revertir** = `UPDATE documents SET doc_type = NULL / language = NULL WHERE id IN (:ids_del_lote)`
  para exactamente los `id` escritos (registrar los `id` afectados al aplicar cada lote).
- `product_model` no se toca ⇒ nada que revertir en el eje de identidad.

---

## 4. Historia LQAS COMPLETA (honestidad total del expediente)

Tres extracciones independientes, estratificadas por marca (largest-remainder), verificación
100 % manual sobre contenido. Seeds distintas declaradas (streams de Mersenne-Twister
independientes por construcción):

| draw | seed | cohorte | n | resultado | qué pasó |
|---|---:|---|---:|---|---|
| 1 | **282** | auto-apply original | 59 | 0 defectos — **pero NO fiable** | muestreó `ASD532_TD` y lo marcó OK: **se le escapó la clase Securiton `_TD`** (falso-acepta) |
| 2 (re-draw) | **592** | auto-apply re-scoped v2 | 59 | **1 defecto → PARADA** | cazó `ADW535_TD` (`datasheet` sobre manual de 118 pp) — eje `doc_type`; contrato: PARO y reporto, NO re-scopeo |
| 3 (confirmatorio) | **593** | **auto-apply v3 (post-guard)** | 59 | **0 defectos → ATESTA** | la clase `_TD` `datasheet` ya está fuera (guard); 59/59 limpias |

- **Por qué el draw 1 no bastó:** una única muestra puede falso-aceptar una clase rara; por eso el
  contrato exige re-draw independiente con seed distinta. El draw 2 (seed 592) es exactamente lo que
  cazó lo que el draw 1 no vio. El draw 3 (seed 593) confirma sobre la cohorte YA remediada.
- **Solape declarado del draw 3:** 5/59 con el draw 1 (`MIDT1041`, `MNDT100`, `MNDT213`, `MNDT720`,
  `nc-mc-0-g-161721-es`) y 3/59 con el draw 2 (`55310021-…CCD-100…`, `AM-8100…rev 4…`, `MNDT040P`);
  los trajo el muestreo, se re-verificaron igual, todas OK.

---

## 5. Honestidad — lo que esta atestación NO certifica

- **LQAS acota la TASA, no certifica cada fila.** 0/59 ⇒ tasa real < 5 % (95 % conf.), no
  «cero defectos en las 533». La firma sigue siendo de Alberto; el LQAS acota el riesgo, no lo anula.
- **Otro `_TD` Securiton sigue en la cohorte, con etiqueta `otro` (NO defecto).** `ASD535_TD_T131192es_h`
  (242 ch) es otra «Descripción técnica», pero s83 la etiqueta `doc_type=otro`, no `datasheet`. `otro`
  es el bucket catch-all defendible para un documento de referencia técnica (no es la afirmación
  implausible-corta que ataca el guard), así que **NO lo caza el guard** (correcto: fuera de alcance) y
  **NO se muestreó** en el draw 3. Se declara para que Alberto pueda, si quiere, fijar la convención de
  `doc_type` de los `_TD` Securiton de forma holística — pero por el estándar LQAS **no es un defecto**.
  (Inventario `_TD` completo: 5 ficheros — 3 `datasheet` cazados por el guard → adjudicate; 1
  `ADW 535-1 ATEX_TD` de 16 ch ya en adjudicate por otra vía; 1 `ASD535_TD` `otro` en auto-apply.)
- **El guard es dirección segura:** solo SACA filas del auto-apply, nunca añade. `language`-MULTI sigue
  advisory (over-call de idioma del draw 2, ortogonal al guard).
- **`doc_type` sin definiciones formales:** juicios entre categorías adyacentes (p.ej. `instalacion`
  vs `operacion` para un manual de central que cubre ambas) se aceptaron cuando la etiqueta describe
  fielmente el género real; solo un error de categoría claro (como `datasheet` sobre un manual de
  118 pp) cuenta como defecto.

---

## 6. Reproducibilidad / freeze

- Guard / re-gate: `scripts/s282_qa_s83_regate_v3.py` → `evals/s282_qa_s83_result_v3.json`
  (+ `report_v3.md`). Determinista 2× byte-idéntico (`2c6bac681ad89001`), frame == v2 (sin drift).
- Draw 3: `scripts/s282_qa_s83_lqas_draw3.py` (seed 593) → `evals/s282_qa_s83_lqas_draw3_bundle.json`
  (59 filas + muestra de contenido para verificación manual).
- Corpus (freeze v2/v3): `chunks_v2` = 25090 · `documents` = 1171 · sha `aa13e792339f7d3e`.
- Worktree `Technical Bot-s281`, rama `claude/s282-h0t2-qa`, HEAD `667271f`. Sin commits.
```
FIRMA (Alberto): _______________________   fecha: __________
Aplicar §3 lote-a-lote registrando los id afectados (reversibilidad).
```
