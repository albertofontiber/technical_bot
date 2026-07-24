# s281 H0-T3 — Propuesta: CONTRATO DE AUTORIDAD A ESCALA (Tramo 2, Etapa 0) — v1

**Para lectura de Alberto. Etapa 0 = diseño, sin construir.** Ninguna lineage se crea aquí; ningún
código se cablea. La decisión de GO es de Alberto. READ-ONLY: el estudio de los 6 lineages vivos se
hizo con SELECT (PostgREST GET); 0 escrituras, 0 llamadas a modelos.

## 0. El problema (por qué esto existe)

El census H0 (`s281_h0_identity_census`) adjudicó: de **998 documentos activos**, solo **6 tienen
lineage `verified`** — el gate proximal del RPC (`unverified_document_lineage`,
`src/rag/document_local_coverage.py:887-930`) exige `revision_lineage_id` presente **y**
`lineage.authority_status='verified'`. Los 6 se adjudicaron **a mano, de uno en uno** (Alberto,
s278 · DEC-150/151). Ese método NO escala a ~1000. Este documento propone **cómo producir
`verified` a escala sin píxel-manual por documento**, manteniendo INTACTA la garantía del gate.

Principio rector: **cambiamos el PROCESO DE PRODUCCIÓN de `verified`, no la GARANTÍA.** El gate
sigue exigiendo `authority_status='verified'`; lo que cambia es cómo se llega a ese sello para un
lote, con evidencia automatizada + muestreo + firma de lote.

## 1. El patrón real vigente (estudio de los 6 lineages — SELECT vivo)

`document_revision_lineages` (esquema real, 6 filas, todas `verified`):

| campo | tipo/valor observado |
|---|---|
| `id` | uuid |
| `authority_status` | `'verified'` (las 6) |
| `authority_contract` | `'explicit_document_ids_v1'` (las 6) |
| `authority_evidence_sha256` | 64-hex (las 6) — hash de la evidencia de adjudicación |
| `created_at` | timestamptz |
| `notes` | texto: cadena de revisión + document_ids + ref de adjudicación (DEC-150/151) |

El FK vive en `documents.revision_lineage_id`; el encadenado de revisiones usa
`documents.supersedes_id` / `superseded_by_id` + `revision` + `revision_date` + `status`
(`active`/`superseded`). Ejemplos reales de los 6:

- **Cadena de supersesión** (HP011 RP1r-Supra): `v.04` (superseded, e98e05ff) → `v.07` (active,
  494e71be), mismo `product_model='RP1r'`, `doc_type='usuario'`, `language='es'`. Notes:
  _"exact source-contract adjudication"_.
- **Cadena** (CAD-250 MC-380): `CAD-250-MC-380-es.pdf` (superseded, bc6bdd33) →
  `...-2026-c.pdf` (active, 348c4ec1, `revision='c'`). Notes citan la cadena S64/DEC-045.
- **Single-revision** (HOP-138-8ES, HOP-138-9ES, 4188-1132-ES): un solo documento activo, sin
  predecesor; el lineage solo **firma** que esa revisión es la autoridad. Notes: _"single-revision;
  adjudicado Alberto s278"_.

**Lectura clave para el diseño:** el contrato actual (`explicit_document_ids_v1`) codifica una
adjudicación HUMANA explícita por documento. La propuesta NO lo toca: introduce un contrato
NUEVO, `batch_attested_v1`, para la vía a escala — mismo esquema, mismo `verified`, distinta
PROCEDENCIA (auditable por el valor de `authority_contract`). Los 6 hand-adjudicados se quedan
como están.

## 2. La propuesta — 3 piezas

### Pieza 1 — Bundle de evidencia AUTOMATIZADA por documento (determinista, $0, RO-computable)

Para cada documento activo sin lineage, computar un bundle reproducible:

1. **sha256 real recomputado** del PDF fuente (hoy 590 docs llevan `source_pdf_sha256='backfill:*'`
   placeholder). El 64-hex real es el ancla de identidad del blob. → poblar `source_pdf_sha256`.
2. **Revisión + fecha** parseadas de filename + contenido, con el mismo vocabulario que ya usan las
   notes de los 6: `issue 6_01-2026`, `v.07`, `rev A`, `2026-c`, `issue 3_04_2025`. → poblar
   `revision` / `revision_date`.
3. **Cadena de supersesión** derivada agrupando por identidad
   (`product_model` + `doc_type` + `language` + `document_family`) y ordenando por revisión/fecha:
   el más reciente = `active`; los previos = `superseded` con `superseded_by_id` al siguiente. →
   poblar `supersedes_id`/`superseded_by_id`/`status`.
4. **`authority_evidence_sha256`** = hash canónico del bundle (mismo campo/rol que en los 6).

Todo esto es **determinista y verificable** (recomputable 2×), en la línea del contrato de los
instrumentos H0 (fingerprint + determinismo).

### Pieza 2 — Tiering de confianza del bundle (gobierna cuánto muestreo hace falta)

| tier | criterio | tratamiento |
|---|---|---|
| **AUTO-CLEAN** | single-revision · identidad inequívoca · sha real recomputado OK · sin hermanos en conflicto · revisión/fecha parseada sin ambigüedad | elegible para firma de LOTE con spot-check ligero |
| **NEEDS-REVIEW** | cadena de supersesión · fecha/revisión ambigua · varios candidatos de identidad · sha no recomputable | spot-check al 100% o adjudicación individual (como los 6) |

El tier se deriva del propio bundle (determinista). La mayoría de los 590 clase-A son fichas/hojas
single-revision → esperable que caigan en AUTO-CLEAN; las cadenas (revisiones sucesivas) → NEEDS-REVIEW.

### Pieza 3 — Spot-check muestreado + REGLA DE ACEPTACIÓN + firma de LOTE

Alberto NO revisa los ~1000; revisa una MUESTRA por lote y firma el lote. Regla estadística
(**LQAS — Lot Quality Assurance Sampling**, aceptación con 0 defectos):

- Para garantizar con confianza `1-α` que la tasa de defecto real del lote es `< p`, aceptando el
  lote solo si se encuentran **0 defectos** en una muestra aleatoria de tamaño `n`:
  `P(0 defectos | tasa=p) = (1-p)^n ≤ α  ⇒  n ≥ ln(α) / ln(1-p)`.
- Valores concretos (α = 0.05, es decir 95% de confianza):
  - tolerar `< 5%` de defecto → **n = 59** por lote (0 defectos ⇒ aceptar).
  - tolerar `< 1%` de defecto → **n = 299** por lote.
- **Propuesta:** lote AUTO-CLEAN → muestra **n=59** con aceptación-en-0-defectos (95% conf. de
  tasa <5%); si el lote es grande o crítico, subir a n=299 (<1%). **Cualquier defecto en la muestra
  ⇒ RECHAZO del lote** → se re-tría (todo a NEEDS-REVIEW / adjudicación individual). NEEDS-REVIEW no
  se muestrea: 100% de revisión.
- **Firma de lote:** Alberto revisa la muestra; si acepta, TODOS los docs del lote reciben lineage
  con `authority_contract='batch_attested_v1'` + `authority_status='verified'`. El
  `authority_evidence_sha256` = hash del **manifiesto del lote** (lista de doc_ids + sus bundles +
  la muestra revisada + la atestación de Alberto: fecha + veredicto). Trazable y reproducible.

## 3. Compatibilidad con el patrón real (sin cambio de esquema)

- **Cero cambios de esquema.** Se reutilizan tal cual: `authority_status` (=`'verified'`),
  `authority_contract` (nuevo VALOR `'batch_attested_v1'`, no nueva columna), `authority_evidence_sha256`,
  `notes`, y el FK `documents.revision_lineage_id` + `supersedes_id`/`superseded_by_id`/`revision`/
  `revision_date`/`source_pdf_sha256`/`status`.
- **El gate no se toca.** `unverified_document_lineage` sigue leyendo `authority_status='verified'`.
  Un lineage `batch_attested_v1`-`verified` pasa igual que un `explicit_document_ids_v1`-`verified`.
- **Procedencia auditable.** El valor de `authority_contract` distingue para siempre las 6
  hand-adjudicadas de las batch-attested → si en el futuro se quiere re-auditar solo la vía a
  escala, es un `WHERE authority_contract='batch_attested_v1'`.
- **Conecta con los Tramos del census:** Tramo 1 (5 docs identity-completos) es el candidato ideal
  para estrenar el contrato (single-revision, bajo riesgo, AUTO-CLEAN). Tramo 2 (590 clase-A) exige
  PRIMERO el backfill de identidad (`language`/`doc_type`/`product_model` desde s83 con QA de
  Alberto) y LUEGO la verificación de lineage por esta vía.

## 4. Riesgos declarados (de entrada)

1. **Recompute de sha exige el PDF fuente disponible.** Los 590 `backfill:*` — confirmar que el
   blob del PDF está en storage/ingest y es recuperable. Si falta el PDF, el sha real no se puede
   recomputar → esos docs caen a NEEDS-REVIEW o quedan bloqueados. **Dependencia a confirmar antes
   del GO.**
2. **Parseo automático de revisión/fecha puede fallar** (OCR, filenames no estándar, idiomas). El
   tiering lo contiene (ambiguo → NEEDS-REVIEW), pero un mis-parse raro en AUTO-CLEAN podría colarse
   por debajo del umbral de detección del muestreo.
3. **Derivación de cadena de supersesión es heurística** (agrupar por identidad + ordenar por
   fecha). Una agrupación errónea encadenaría revisiones mal. Mitigación: las cadenas son
   NEEDS-REVIEW por defecto (no AUTO-CLEAN).
4. **La firma de lote transfiere confianza al muestreo.** Un lote aceptado puede contener defectos
   por debajo del umbral estadístico — la regla ACOTA la tasa (`<p` con conf. `1-α`), no la lleva a
   cero. Es el trade-off explícito: Alberto acepta una tasa de error residual ACOTADA y CONOCIDA a
   cambio de escala. Si eso no es aceptable para el dominio PCI, se sube `n` (baja `p`) o se va a
   100% (que es el método actual, sin escala).

## 5. Lo que esta propuesta NO cubre

- **No verifica la CORRECCIÓN TÉCNICA del contenido** del manual (si un dato es correcto). Solo
  lineage/autoridad (qué revisión es la vigente, procedencia del blob). Eso es exactamente el
  alcance del gate — no lo amplía.
- **No sustituye el juicio humano en casos genuinamente ambiguos** (revisiones en conflicto, sin
  fecha, identidad dudosa): esos van a adjudicación individual, como los 6 de hoy.
- **No es el backfill de identidad C** (Tramo 2 `language`/`doc_type`/`product_model`). Ese es
  prerequisito y va aparte (fuente candidata s83 + QA de Alberto, s84 no ejecutado). Este contrato
  firma el LINEAGE una vez la identidad está poblada.
- **No construye nada.** Etapa 0. Sin código, sin lineages creadas. GO de Alberto requerido; ronda
  de revisión adversarial (Protocolo 3) antes de cablear la vía a escala.

## 6. Decisión pedida a Alberto

1. ¿GO al diseño del contrato `batch_attested_v1` (evidencia automatizada + LQAS + firma de lote)?
2. ¿Umbral de aceptación: `<5%`/n=59 (rápido) o `<1%`/n=299 (estricto) por lote AUTO-CLEAN?
3. ¿Confirmas la disponibilidad del PDF fuente para recomputar sha de los 590 `backfill:*`?
4. ¿Estrenar en Tramo 1 (5 docs) como piloto antes de escalar a Tramo 2?
