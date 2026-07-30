# s288 — A-CORE: autoridad documental + document_id en hyq + scope enforcement (spec normativo ÚNICO)

Workstream A (Alberto 30-jul: infraestructura ANTES de etapa 3, upstream-first). A-core = la
CONSOLIDACIÓN post-dúo de A1+A2 (Sol focused sobre A1 v2: 5 hallazgos, 1 crítico, 0 FP —
A1-standalone se reducía a un filtro post-hidratación; sus piezas mayores dependen del esquema y
la autoridad de A2). Este documento REEMPLAZA a `s288_a1_hyq_scope_design_brief_v1.md` (retirado:
bloques v1/v2 apilados con gates contradictorios — hallazgo Sol #5). Un solo bloque normativo;
las revisiones del dúo se incorporan REESCRIBIENDO in-place, no apilando.

## 0. OBJETIVO + MÉTRICA (Protocolo 2 §5)
A-core es INFRAESTRUCTURA de serving: deja la identidad documental (sha real + lineage +
language + status) y el esquema hyq (document_id) en estado consumible por las lanes de
cobertura, y hace la lane `doc_scoped_hyq_coverage` doc-scoped de verdad.
- **GO-gates de A-core = CORRECCIÓN + VOLUMEN**: tests de exclusión/paridad/mixed-state verdes ·
  suite completa verde · census v3 post-paste confirma los saltos declarados (§4.4).
- **La EFICACIA (cohorte retrieval-miss estable {cat010#0, hp012#3} + hp013#1 baseline
  no-gating) NO es GO-gate**: se mide DESPUÉS con probes freeze-contracted sobre los 39 dev
  (lección A1 v2: gate de eficacia sobre docs sin autoridad = ungateable). Los 12 held-out
  quedan EMBARGADOS de todo audit/probe de este workstream.
- Levers settled citados y su métrica (no colisión): DEC-099 (canal hyq retrieval, bvg-outcome —
  ON en prod, intocado aquí) · DEC-152/s279+s281 (census identidad: el cuello es backfill, NO
  selección — A-core ES ese backfill) · DEC-085/086 (vocabulario, ⊥) · digest fila S277:
  «primero census de identidad/authority» = este arco.

## 1. CENSUS VERIFICADO HOY (30-jul, SELECT-only vía MCP, DB live — anclas re-derivables)
- `documents` 1169: **995 active · 91 retired · 79 needs_review · 4 superseded**.
- sha: **744 placeholder** (`backfill:` + sha256 del NOMBRE de fichero —
  `scripts/migrations/001_backfill_documents.py:261` — el sufijo NO es sha de blob: 0/590
  coincide con extraction) · **425 con 64-hex**; de los 425, 415 tienen chunks y **414 cumplen
  el binding canónico** `extraction_sha256 == source_pdf_sha256` en TODOS sus chunks (1
  mismatch → packet). 3 docs placeholder son multi-extraction (clase hp011).
- lineage: **9 docs** con `revision_lineage_id` (6 lineages verified — census s281 §1). Familias
  activas: **993 single-doc · 1 multi (hp011, ya lineada) · 8 docs con punteros de revisión**.
- language: **769 NULL** (326 es · 63 en · 11 otros).
- `chunks_v2_hyq` 70.126 filas / 23.205 padres / batch único: **7.421 filas (10,6%) con padre
  `duplicate_of` marcado** (el dedup s287 no se propagó; el CANAL retrieval sí guarda —
  retriever.py:1098/1539 — la LANE doc_scoped NO: ni selecciona ni filtra `duplicate_of` →
  starvation de PARENT_LIMIT y servido de duplicados si se activara). hyq cubre 1.002 de 1.012
  source_files.
- Colisión de nombre real en chunks_v2: **1** (`HLSI-MN-103_RP1r-Supra_lr`, hp011 v04/v07).
- Huérfanos/deriva: **25 chunks con document_id NULL** · **288 chunks vivos (no-dup) en docs
  no-activos** · 10 document_id de chunks apuntan a docs no-activos.
- **Blobs locales: 1.334 PDFs** bajo `OneDrive…\Technical Bot\Manuales_*` (Notifier 357+357
  privado · Morley 87+118+167 · ES 122 · Kidde 55 · Aritech 33 · Detnov 8 · Edwards 3 ·
  Otros 16). El repo de trabajo C:\dev NO tiene los PDFs.
- Prior art REUTILIZABLE (no reconstruir): `scripts/s281_h0_identity_census.py` (census
  read-only determinista 2× + propuestas SQL, corrido 23-jul pre-dedup) ·
  `scripts/audit_chunk_languages.py` (detector es/en/pt determinista por stopwords con
  confianza) · patrón staged-SQL con guards de `evals/s287_p2_dedup_apply_v1/v2.sql`.

## 2. HIPÓTESIS H1 (premisa a VERIFICAR en F0, no asumida — DEC-022)
`chunks_v2.extraction_sha256` = sha256 de los BYTES del PDF fuente (así lo trata el binding
document_local y las filas reconciliadas «bound to locally verified blobs»). **Gate H1**: hashear
los PDFs locales de ≥30 docs de la clase binding-ok-414 y comprobar sha-local == extraction_sha.
Si H1 falla para algún vintage → la cohorte sha-backfilleable se REDUCE a lo verificado
localmente y se declara el techo (no se infiere).

## 3. FASES (orden normativo; cada una con su gate; TODO SQL = paste de Alberto)

### F0 — Census v2 ($0, read-only, determinista 2×)
Extender/re-correr `s281_h0_identity_census.py` → tag **s288 v2** (post-dedup) + módulos NUEVOS:
(a) **census de blobs locales**: hash sha256 de los 1.334 PDFs (manifest JSONL: path relativo,
    sha, size) — match contra `extraction_sha256` del corpus **POR SHA, nunca por nombre**
    (inmune a renombres; un PDF re-guardado no matchea y queda fuera, honesto);
(b) **census hyq**: filas/padres dup, cobertura por source_file, padres con document_id NULL;
(c) **gate H1** (§2);
(d) census de idioma: `audit_chunk_languages.py` sobre los 769 docs language-NULL (por doc:
    idioma detectado + confianza).
GATE F0: determinismo 2× byte-idéntico · H1 veredicto explícito · conteos publicados en
`evals/s288_acore_census_v2_report.md`.

### F1 — Staging de packets SQL (guards estilo s287-dedup: precondiciones exactas + backup +
### conteo post + reversibilidad; NADA se aplica — Alberto pastea)
- **P-A sha real**: para cada doc placeholder cuyo extraction_sha (único) ∈ manifest de blobs
  locales → `UPDATE documents SET source_pdf_sha256='<sha>' WHERE id='<id>' AND
  source_pdf_sha256='backfill:<placeholder>'`. Los 3 multi-extraction + el binding-mismatch-1 →
  packet de adjudicación aparte. Docs sin blob local matcheado: QUEDAN placeholder (techo
  declarado en el report, no se persigue).
- **P-B language**: UPDATE por doc SOLO donde el detector da confianza alta y un único idioma
  dominante en sus chunks; muestra de QA (30 docs estratificada por marca/idioma) en el packet
  para spot-check de Alberto ANTES del paste. Baja confianza / mixto → NULL se queda (fail-open
  a no-etiquetar).
- **P-C lineage**: política **single-revision-lineage en bloque**: doc activo con sha REAL
  verificado (post P-A) + sin siblings de revisión (familia single-doc, sin punteros) + sin
  colisión de nombre → 1 lineage `verified` + `authority_contract='single_revision_bulk_v1'` +
  nota que registra que el PASTE de Alberto es el acto de adjudicación del lote (la semántica
  «no fuzzy membership» se respeta: la membership es exact-id, la adjudicación es explícita y
  en bloque). Los 8 docs con punteros + colisiones + superseded → packet de adjudicación
  individual (pequeño). **Política ES/EN (H6)**: documento ES y su gemelo EN = documentos
  DISTINTOS con lineages DISTINTOS — lineage agrupa REVISIONES de un mismo documento, nunca
  idiomas.
- **P-D hyq document_id**: migración `ALTER TABLE chunks_v2_hyq ADD COLUMN document_id UUID
  NULL` + backfill `UPDATE … FROM chunks_v2 c WHERE c.id=chunk_id` + índice. Padres con
  document_id NULL (25 chunks) → hyq.document_id NULL, fail-closed en lane. Las 7.421 filas dup
  NO se borran (dedup es marks-only reversible): la lane las excluye (F2).
Orden de pastes: P-A → P-B → P-C (depende de P-A) · P-D independiente (puede ir primero).

### F2 — Lane hardening (código; buildable pre-paste con tests fixture; la lane sigue OFF)
1. **Scope por document_id**: la navegación primaria consulta `chunks_v2_hyq` por
   `document_id IN (resolved)` (los ids ya vienen en `resolved_documents` del resolver —
   contrato del resolver INTOCADO) — el scope-por-nombre muere. Pre-paste el código cae a
   fail-closed si la columna no existe (detección, no crash).
2. **Exclusión de duplicados EN NAVEGACIÓN** (no solo hidratación): filtro embedded PostgREST
   `chunks_v2!inner(duplicate_of)` is.null en la query de navegación (FK existe; verificar
   sintaxis en build) + cinturón en hidratación (`duplicate_of` en `_PARENT_SELECT` + skip).
3. **Autoridad por parent, sha-verificado-ONLY** (decisión A1 v2 que SOBREVIVE): 1 GET acotado
   a `documents` por los document_id del scope (cap de 6 requests respetado) → parent servible
   ⇔ doc activo + sha real 64-hex + `extraction_sha256 == source_pdf_sha256`. Placeholder ⇒
   parent fuera con razón trazada. Fail-closed a descartar-parent en error.
4. **Nivel candidato**: los filtros 1-3 corren ANTES de que la selección consuma
   SOURCE/PARENT_LIMIT (el crítico Sol-3: ya realizable con document_id en la tabla).
5. **Receipts**: los fingerprints de fetch existentes + document_ids del scope + razones de
   rechazo por parent.
GATE F2: tests de exclusión (superseded NO · colisión NO · sha-mismatch NO · placeholder NO ·
dup NO) + test de ESTADO MIXTO de la transición (sha real en documents con chunks aún sin
migrar no mata en silencio) + paridad por-lane existente verde + suite completa.

### F3 — Verificación post-paste + eficacia (downstream, no GO-gate)
Census v3 = delta vs v2: sha real 425→(425+matched) · lineage 9→(~cohorte P-C) · language
769-NULL→resto · hyq document_id backfilled 100% de padres no-huérfanos · 0 filas dup servibles
por la lane. Después: probes de eficacia cohorte (39 dev, freeze: fingerprints pre/post +
receipts de lane), y el re-baseline factlevel N=2 del plan de campaña.

## 4. FUERA DE SCOPE (declarado, no diferido en silencio)
- **Taxonomía/arquetipos** de facets = lever SEPARADO post-A-core, medido old-vs-new config con
  corpus y autoridad FIJOS (aislamiento del dúo A1; su audit usará SOLO los 39 dev).
- **A3** (perfil c1_v5, promoción de lanes, SLO latencia) — siguiente arco.
- Surrogates hyq nuevos (batch H5) · doc_type backfill (ningún gate lo consume hoy — declarado)
  · split D1 ZXSe + product_model unknown (adjudicación de producto, census §3 s281) · mapeo
  catálogo de 149 docs (DEC-074) · los 288 chunks-en-docs-no-activos y 25 huérfanos (se
  CENSAN y reportan en F0; su remediación es packet aparte post-A-core si Alberto la prioriza).

## 5. ALTERNATIVAS DESCARTADAS
- **A1 standalone** (spec anterior): sin document_id el scope candidato era irrealizable
  (hidratar ~4.000 padres o romper el cap) y la autoridad name+status debilitaba el binding —
  hallazgos Sol, 0 FP. Retirado.
- **Re-descargar/re-derivar shas de portales**: los blobs locales son la fuente que INGESTÓ;
  match por sha es exacto y $0.
- **Borrar filas hyq de padres dup**: rompe la reversibilidad marks-only del dedup; la
  exclusión en lane da lo mismo sin destruir.
- **Lineage agrupando ES/EN**: rompe la semántica revisión≠idioma (H6) y el language-gate del
  RPC document_local.
- **Backfill de sha por nombre de fichero**: la colisión hp011 y los re-guardados lo hacen
  inseguro; por-sha es inmune.

## 6. RIESGOS DECLARADOS
1. **H1 puede fallar por vintage** → P-A se encoge a lo verificado; techo honesto, no bloqueo.
2. **Cobertura de blobs locales incierta**: 1.334 PDFs ≥ 1.169 docs pero con duplicados entre
   carpetas (Notifier/Notifier_Privado 357+357) y sin garantía de superset — el census da el
   match-rate real; lo no-matcheado queda placeholder.
3. **Bulk lineage** (~centenares de filas en tabla gobernada): mitigado con elegibilidad
   estricta (§F1 P-C) + packet visible + guards de conteo exacto; si Alberto prefiere tramos,
   el packet se trocea sin cambiar el diseño.
4. **El fingerprint del corpus CAMBIA** con cada paste (esperado): se estampa pre/post; los
   partials del instrumento quedan invalidados y el re-baseline está ya planificado — ninguna
   fila frozen (`s100_factlevel_full*`, b92ff51, contrato s277, golds ledger `79701140…`) se toca.
5. **Detector de idioma FN** en docs mixtos/OCR-pobres → solo-alta-confianza + QA sample; el
   residuo queda NULL (visible en census v3).
6. **PostgREST embedded filter en navegación hyq**: sintaxis a verificar en build; fallback =
   hidratación-only con re-selección (mantiene corrección, pierde eficiencia de slots — se
   declara si ocurre).

## 7. PROTOCOLO
Dúo COMPLETO sobre ESTE spec antes de cualquier build (ALTO + zona de dolor corpus/esquema:
sub-agente Fable fresco + cross-model GPT-5.6 Sol xhigh INNEGOCIABLE) → incorporar REESCRIBIENDO
in-place → build F0 → …. Stop-lines: todo SQL/migración = paste de Alberto · merges = Alberto ·
held-out embargado. Tally en `evals/adversarial_review_log.jsonl` con regla-C.
