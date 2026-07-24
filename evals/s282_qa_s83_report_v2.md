# s282 QA-s83 — RE-GATING v2 por operación de escritura (dúo r1 ADJUDICADO)

**El titular v1 «879 aplicables tal cual» MUERE.** El dúo focal r1 (`evals/s282_qa_s83_duo_r1_adjudication_v1.yaml`) lo RECHAZÓ como puerta del Tramo 2; el instrumento v1 se conserva como TRIAGE. Este v2 re-gatea cada `source_file` por su **operación de escritura** (`write_op`), recall-safe, aplicando los 9 hallazgos confirmados. READ-ONLY (PostgREST GET), 0 escrituras, 0 llamadas de modelo de pago (el juez NO se re-corre; se reusa el cache v1). Derivación determinista 2× byte-idéntica.

## Freeze-contract

- commit HEAD: `6bc53e21ac625f7a2a3683fc2e94d7036c30dc77` (dirty: True)
- corpus: chunks_v2=25090 · documents=1171 · sha `aa13e792339f7d3e`
- **re-gating determinista 2×: IDÉNTICO** (`2b5429d8c4ff980d` == `2b5429d8c4ff980d`)
- s83 modelos sha-LF `a1291a837a7f905c` · v1 cache reusado (0 llamadas nuevas)
- generado 2026-07-24T07:52:19.742774+00:00

## 1. Cohortes de OPERACIÓN DE ESCRITURA (recuento honesto v2)

De 1014 `source_file` s83. El **auto-apply** (SQL fill-only propuesto) = `corroborate_noop` + `fill_language_doctype` = **548** (NO 879). Todo lo demás → Alberto o fuera de alcance.

| write_op | n | qué se escribiría | destino |
|---|---:|---|---|
| `corroborate_noop` | 423 | pm ya corroborado exacto (NO-OP) + fill `language`/`doc_type` vacíos | **AUTO-APPLY** |
| `fill_language_doctype` | 125 | pm familia CONSERVADO (nunca replace) + fill `language`/`doc_type` vacíos | **AUTO-APPLY** |
| `replace_pm` | 0 | reemplazo de pm — PROHIBIDO con sola palabra del juez (finding 5) | vacío por diseño → adjudicate |
| `adjudicate` | 423 | pm en disputa/ruido/genérico/vía-all-models/low-conf/s83-vacío | [ALBERTO] |
| `excluded_t3` | 28 | solape con packet T3 — T3 es el dueño | excluido (T3) |
| `unmapped` | 15 | sin documento activo en DB | fuera de alcance T2 |
| **TOTAL** | **1014** | | |

### 1b. Desglose del `adjudicate` por relación pm (transparencia)

| sub-relación pm | n | por qué a Alberto |
|---|---:|---|
| `doc_noise` | 301 | doc-level pm = ruido de filename; s83 sin corroboración independiente |
| `disjoint` | 59 | pm DISJUNTO (candidato a conflicto real) |
| `s83_generic` | 30 | s83 da descripción genérica, no un modelo |
| `s83_empty` | 21 | s83 no aporta modelo (unmapped-like; sale del conteo aplicable — finding 6) |
| `corrob_allmodels` | 9 | corroborado solo vía ALL-models, no primario (no recall-safe — finding 2) |
| `corrob_prim` | 2 | corroborado exacto pero s83_confidence=low |
| `judge_pull` | 1 | sacado del auto-apply por el juez-triage CONFLICT (dirección segura — finding 7) |

## 2. LQAS — muestra n=59, aceptación 0-defectos (batch_attested_v1)

Muestra determinista (seed 282, estratificada por marca) de la cohorte auto-apply (548). Estándar: 0 defectos ⇒ tasa real < 5% con 95% de confianza. **Verificada A MANO leyendo contenido real de chunks (SELECT), fila a fila** — artefacto `evals/s282_qa_s83_lqas_sample_v1.md`.

**RESULTADO LQAS (cohorte AS-SCOPED = pm-noop + doc_type + language COMPLETO): NO PASA el listón 0-defectos — 1 defecto / 59.** Desglose por eje: `product_model` (noop/conservado) **0/59** · `doc_type` (fill) **0/59** · `language` (fill) **1/59**. Defecto: MADT609 (NAP-100) — s83 language=[en,es] pero el documento es una TABLA DE APROXIMACIONES A GAS de NOTIFIER redactada 100% en español (el único inglés son nombres químicos de la tabla), el fill escribiría 'en' espurio en un campo NULL. pm=NAP-100 y doc_type=otro correctos. **Causa raíz:** el array `languages` de s83 over-incluye idiomas secundarios (tag 'en' cuando aparecen tokens ingleses — nombres de producto/UI/nomenclatura química — en un doc redactado en español). **REMEDIO recall-safe (aplicado a la PROPUESTA, no a DB):** `language` fill-MULTI → ADVISORY (Alberto/verificar-contenido); auto-apply = `pm-noop` + `doc_type` + `language`-SINGLETON. Esos tres ejes fueron **0-defecto en esta muestra** → fuerte evidencia; un re-draw LQAS confirmatorio sobre la cohorte re-scoped es el paso previo a la firma.

Muestra por marca (asignación largest-remainder):

| marca | auto-apply | muestreados |
|---|---:|---:|
| Notifier | 297 | 32 |
| Morley | 52 | 6 |
| Aritech | 43 | 5 |
| Detnov | 41 | 4 |
| Kidde | 30 | 3 |
| System Sensor | 26 | 3 |
| Spectrex | 17 | 2 |
| Argus Security | 11 | 1 |
| Pfannenberg | 8 | 1 |
| Securiton | 6 | 1 |
| Xtralis | 5 | 1 |
| Honeywell | 3 | 0 |
| Sensitron | 3 | 0 |
| Pepperl-Fuchs | 2 | 0 |
| Edwards | 2 | 0 |
| Fidegas | 1 | 0 |
| Avotec | 1 | 0 |
| **TOTAL** | **548** | **59** |

## 3. Packet de CONFLICTOS para Alberto

Unión de: juez-triage CONFLICT (no-T3) + pm-DISJUNTO (no-T3) + corroborado-vía-all-models (no-T3) = **121** `source_file`. El juez es solo TRIAGE (dirección segura); nada se aplica; reversible.

- juez-triage CONFLICT (no-T3): 87
- pm-DISJUNTO deterministas (no-T3): 59
- corroborado-vía-all-models (no-T3): 9

Detalle completo (source_file · s83 · doc-pm · juez · relación) en `evals/s282_qa_s83_result_v2.json` (`conflict_packet.rows`). Los 89 del juez v1 se listan en `report_v1.md §3`; 2 de ellos caen en T3 (owned).

## 4. Colisión T3 — check de consistencia cruzada (finding 4)

Los **28** `source_file` que solapan con el packet T3 se EXCLUYEN (T3 es el dueño). Chequeo de dirección s83↔T3: consistente=12 · divergente=9 · indeterminado=7. (El dúo estimó 24; el recuento real es 28 — TODOS los 28 source_files del census T3 mapean a un registro s83.)

Divergencias s83 vs T3 (para que Alberto sepa que ahí las dos fuentes no coinciden):

| source_file | s83 cores | T3 candidato | T3 conf |
|---|---|---|---|
| `MIE-MP-525rv1` | ['dx1', 'dx2', 'dx4'] | ['seriedimension'] | media |
| `BANI-G-24_Eng` | ['is28mk4banshee', 'ls28'] | ['is28mk4'] | media |
| `D700-3-Sp` | ['mcp1a', 'mcp1b', 'mcp2a', 'mcp2b'] | ['d700'] | media |
| `EMA24RS2R_NX2y5-R-R` | ['nx2rr', 'nx5rr'] | ['nx2rrynx5rr'] | media |
| `FS2-1` | ['fs1', 'fs2', 'fs4'] | ['fs21'] | media |
| `I56-5004-000-Notifier-Strobe` | ['b501ap'] | ['notifierstrobe'] | media |
| `MIE-MI-600` | ['795068100', '795072100', 'exp004', 'exp004b'] | ['zxse'] | media |
| `No-puedo-conectarme-con-el-ordenador-a-l` | ['020891', 'zx2e', 'zx2se', 'zx5e'] | ['zxe'] | media |
| `RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloque` | ['rp1rsupra', 'vsnrp1rplus2'] | ['rp1r'] | media |

## 5. Fill plan del auto-apply (fill-only, reversible) — SQL propuesto §6

- **AUTO** `doc_type` (DB vacío, s83 aporta): **536** filas (0-defecto en LQAS)
- **AUTO** `language`-SINGLETON (un idioma, DB vacío): **304** filas (0-defecto en LQAS)
- **ADVISORY** `language`-MULTI (>1 idioma, DB vacío): **209** filas → NO auto-apply (over-call de idioma detectado por LQAS: NAP-100). Alberto/verificar-contenido.
- `language` contradicho en DB (NO se rellena → advisory, finding 5): 18
- `doc_type` distinto en DB (NO se rellena → advisory): 11

Regla de fill (finding 5 + regla 2 del lote, endurecida por el LQAS de esta lane): SOLO donde el eje esté vacío-en-DB sin contradicción; JAMÁS overwrite. `product_model` NUNCA se escribe en auto-apply (corroborate_noop = NO-OP; family = conservar). `language`-MULTI se degrada a ADVISORY porque el LQAS cazó que s83 over-incluye idiomas secundarios.

## 6. PROPUESTA SQL del Tramo 2 (SOLO auto-apply · fill-only · por lotes por marca) — NO aplicada

Ningún SQL se ejecuta aquí (READ-ONLY). Plantilla reversible, por marca, gateada por la firma LQAS de Alberto. `language`/`doc_type` se guardan como el array/valor s83; el `WHERE` exige que el campo esté hoy NULL (nunca overwrite). Reversible: `SET language=NULL` / `doc_type=NULL` para los `id` del lote.

```sql
-- Ejemplo (marca=Notifier). Aplicar SOLO tras firma LQAS. Uno por marca.
-- Fuente de valores: evals/s282_qa_s83_result_v2.json (write_op in {corroborate_noop,fill_language_doctype})
-- AUTO = doc_type (todas) + language SOLO cuando el fill_plan es language_fill_singleton.
UPDATE documents d SET
  doc_type = COALESCE(d.doc_type, :s83_doc_type),        -- fill-only; NULL-guard
  language = COALESCE(d.language, :s83_language_singleton) -- SOLO singleton; multi=advisory
WHERE d.id = :document_id
  AND (d.doc_type IS NULL OR d.language IS NULL);        -- nunca overwrite
-- product_model: NO se toca (corroborate_noop = NO-OP; family = etiqueta gobernada conservada).
-- language-MULTI (>1 idioma): NO en el UPDATE — va al packet advisory para Alberto.
```

El instrumento puede emitir el lote materializado por marca (id + valores) desde el JSON v2 cuando Alberto dé el GO; aquí se deja como propuesta.

## 7. Honestidad — qué cambió vs v1 y qué NO juzga esto

- **879 → auto-apply real = 548.** El 879 fusionaba corroboración exacta con AUTO_CLEAN del juez sobre WEAK (doc_noise/family/disjoint). El juez ya NO otorga auto-apply (finding 7/9).
- **`product_model` nunca se auto-escribe.** Solo `language`/`doc_type` vacíos, fill-only, reversible.
- **doc_noise (301) → adjudicate**, no auto-apply: sin corroboración independiente de la identidad s83, el fill no es de fiar (recall-safe).
- **La firma sigue siendo de Alberto.** El LQAS acota la tasa de defecto (<5%/95%), no la lleva a 0; es el mismo trade-off del contrato `batch_attested_v1`.
- **El juez es triage, no oráculo** (finding 7): solo saca filas del auto-apply o alimenta el packet de conflictos; nunca añade una fila al auto-apply.
