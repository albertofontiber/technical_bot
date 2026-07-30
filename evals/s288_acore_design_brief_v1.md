# s288 — A-CORE: autoridad documental + scope enforcement (spec normativo ÚNICO, v2 post-dúo r1)

Workstream A (Alberto 30-jul: infraestructura ANTES de etapa 3, upstream-first). A-core consolida
A1+A2. **v2 = reescritura in-place tras el dúo r1** (Sol xhigh NO-SÓLIDO: 2 críticos + 3 medios ·
sub-agente Fable SÓLIDO-CON-CAMBIOS: 3 críticos + 2 medios + 2 menores — TODOS confirmados
regla-C, 0 FP; convergencia bilateral en matar P-D y rehacer P-C). Este doc REEMPLAZA a
`s288_a1_hyq_scope_design_brief_v1.md`. Sin bloques apilados: toda revisión reescribe.

## 0. OBJETIVO + MÉTRICA (Protocolo 2 §5)
A-core deja la identidad documental (sha real verificado + lineage + language + status) consumible
por las lanes de cobertura, y hace la lane `doc_scoped_hyq_coverage` doc-scoped y con autoridad
REAL (predicados enumerados en F2 — sin over-claim: la lane enforcea activo+sha+binding+lineage;
language lo consume document_local, no esta lane).
- **GO-gates = CORRECCIÓN + VOLUMEN**: tests exclusión/paridad/mixed-state verdes · suite verde ·
  census v3 post-paste confirma los saltos declarados en **F3**.
- **EFICACIA ≠ GO-gate**: cohorte {cat010#0, hp012#3} + hp013#1 baseline, medida en F3 con el
  freeze de F3.3, SOLO 39 dev (12 held-out EMBARGADOS de todo audit/probe).
- Settled citados con su métrica (sin colisión): DEC-099 (canal hyq retrieval bvg-outcome, ON en
  prod, intocado) · DEC-152/s279+s281 (el cuello es backfill de identidad — A-core ES ese
  backfill) · digest fila S277 («primero census de identidad/authority») · DEC-085/086 (⊥).

## 1. CENSUS VERIFICADO (30-jul, SELECT-only DB live; FOTO datada — los packets F1 se dimensionan
## contra el snapshot F0, NO contra esta sección [hallazgo F4: los números se mueven])
- `documents` 1169: 995 active · 91 retired · 79 needs_review · 4 superseded.
- sha: **744 placeholder** (`backfill:` + sha256 del NOMBRE — 001_backfill_documents.py:261) ·
  **425 con 64-hex**, de los cuales 415 con chunks y **414 binding-ok** (`extraction_sha256 ==
  source_pdf_sha256` en todos sus chunks; 1 mismatch → packet). Placeholder con chunks: 590
  (**587 single-extraction** + 3 multi → packet).
- **Colisiones de blob: 0 HOY** (medido: 0 grupos same-manufacturer same-sha en {425 reales ∪ 587
  placeholder-por-extraction} y 0 shas cross-manufacturer) — el UNIQUE
  `documents_mfr_hash_unique (manufacturer, source_pdf_sha256)` (001_document_management.sql:68)
  exige el guard igualmente en P-A (hallazgo F2: mecanismo real, prevalencia 0).
- lineage: **6 lineages verified / 9 docs** (contrato `explicit_document_ids_v1`,
  `authority_evidence_sha256` poblado por fila — patrón a heredar). La aritmética de familias de
  v1 era incorrecta; F0 publica la PARTICIÓN EXHAUSTIVA predicado-definida de los 1169.
- language: 769 NULL (326 es · 63 en · 11 otros). Los ~400 etiquetados = set de CALIBRACIÓN $0
  del detector (F0e).
- `chunks_v2_hyq` 70.126 filas / 23.205 padres / batch único: **7.421 filas (10,6%) con padre
  `duplicate_of`** — el canal retrieval guarda (retriever.py:1098/1539); la lane doc_scoped NO
  (ni selecciona ni filtra `duplicate_of`; verificado por ambos revisores). hyq cubre 1.002/1.012
  source_files.
- Deriva censada (se reporta, NO se toca en A-core): 25 chunks document_id NULL · 288 chunks
  vivos en docs no-activos · 10 document_id de chunks → docs no-activos.
- **Blobs locales: 1.334 PDFs** en `OneDrive…\Technical Bot\Manuales_*`. El repo C:\dev no los
  tiene.
- **H1 PRE-VERIFICADA con clave INDEPENDIENTE (nombre de fichero → hash → comparar): 34/34**
  (14 binding-ok Aritech + 20 placeholder Notifier/Detnov/Morley/System Sensor/Venitem) —
  `extraction_sha256` ES el sha de los bytes del PDF y los blobs locales SON los ingestados.
- Prior art: `s281_h0_identity_census.py` (stack census read-only 2×) · patrón staged-SQL s287 ·
  `audit_chunk_languages.py` — **SOLO como referencia de diseño: lee la tabla LEGACY `chunks`
  con muestra de 3 chunks (hallazgo S4, confirmado :175/:204) → el detector se RECONSTRUYE**.

## 2. HIPÓTESIS H1 (premisa verificable — DEC-022)
`extraction_sha256` = sha256 de los BYTES del PDF fuente. **Gate NO-circular (hallazgo F1)**: el
probe mapea doc→blob por `source_pdf_filename`/stem (clave INDEPENDIENTE del sha), hashea y
compara contra extraction — y publica match/mismatch/ausente. El match POR SHA es el mecanismo de
P-A, JAMÁS el verificador de H1. Pre-evidencia: 34/34 (§1). F0 lo re-deriva con n≥60 estratificado
por vintage/marca. Contexto: en el path de re-ingesta `extraction_derivation.py:66-68` iguala por
fiat — H1 verifica el vintage ORIGINAL, que es donde vive la duda. Si H1 falla en algún estrato →
ese estrato sale de P-A y se declara techo.

## 3. FASES (orden normativo; todo SQL = paste de Alberto)

### F0 — Census v2 ($0, read-only, determinista 2×, salida `evals/s288_acore_census_v2_*`)
(a) **Manifest de blobs** (JSONL: path relativo, sha256, size, stem) + match dual: por-sha (para
    P-A) y por-stem (para H1 y para detectar renombres).
(b) **Partición exhaustiva** de los 1169 docs por predicado (status × clase-sha × binding ×
    lineage × language × blob-local) — reemplaza la aritmética §1; los packets citan estas celdas.
(c) **Gate H1** (§2) + grupos sha-compartido same/cross-manufacturer (guard P-A; hoy 0).
(d) **Census hyq**: filas/padres dup, cobertura, padres huérfanos.
(e) **Detector de idioma v2 + CALIBRACIÓN**: reconstruido sobre `chunks_v2` (por-doc, muestra
    ≥10 chunks o todos si hay menos, umbral mínimo de marcadores, universo {es,en,pt,it,fr} —
    hallazgo F7). Gate: acuerdo ≥99% en es/en contra los ~400 docs YA etiquetados (matriz de
    confusión publicada). Sin gate verde NO se stagea P-B.
(f) **Screens de siblings para P-C** (hallazgo F3/S1): por doc activo, detección determinista de
    candidatos a revisión-hermana contra TODOS los status: (i) punteros supersedes/superseded en
    su clúster · (ii) colisión de stem-normalizado (strip de tokens de revisión/fecha/idioma —
    la clase `HLSI-MN-103…`) · (iii) misma tupla (manufacturer, product_model, doc_type, language)
    con doc_type conocido e igual. Cada screen publica su recuento de exclusión.
GATE F0: determinismo 2× byte-idéntico · H1 explícito · partición suma 1169 · calibración (e).

### F1 — Packets SQL staged (guards s287: precondiciones exactas + backup + conteos + rollback)
- **P-A sha real** (bulk = docs ACTIVOS, single-extraction, blob local matcheado por sha,
  grupo-sha singleton per-manufacturer contra TODOS los status — guard del UNIQUE):
  `UPDATE documents SET source_pdf_sha256='<sha>' WHERE id AND source_pdf_sha256='backfill:…'`.
  Multi-extraction (3) + mismatch (1) + colisiones futuras → packet de adjudicación. Sin blob
  local → queda placeholder (techo declarado). Retired/needs_review: FUERA del bulk (no sirven;
  censados — hallazgo F7).
- **P-B language** (bulk = activos, detector v2 calibrado, confianza alta + idioma único
  dominante): UPDATE por doc; muestra QA 30 estratificada (incluye it/fr) en el packet para
  spot-check de Alberto ANTES del paste; baja confianza/mixto → NULL se queda.
- **P-C lineage single-revision — [ALBERTO decide la POLÍTICA]** (hallazgos S1+F3: el bulk
  'verified' sin evidencia por-doc vacía la semántica canónica). El packet presenta las opciones
  con recomendación:
  (i) adjudicación per-doc en tramos (máxima fidelidad, ~590 docs = varias sesiones);
  (ii) **RECOMENDADA — bulk con dossier de evidencia POR-DOC**: elegible ⇔ activo + sha real
      verificado contra blob local + los 3 screens F0(f) limpios + sin colisión de blob. Cada
      lineage lleva `authority_evidence_sha256` = sha256 de su línea de dossier
      (`evals/s288_acore_lineage_evidence_v1.jsonl`: document_id, filename, blob_sha, census_tag,
      screens) — hereda el patrón vivo de las 6 filas existentes; contrato
      `single_revision_local_blob_v1`, cuya SEMÁNTICA declarada es «única revisión INGESTADA,
      blob verificado» (no completitud-del-mundo — la revisión más nueva no-ingestada es
      irrepresentable por cualquier predicado; riesgo residual declarado, mitigado por screens +
      reversibilidad: un lineage erróneo se corrige con 1 UPDATE);
  (iii) híbrido: (ii) solo para cohortes de bajo riesgo + tramos para el resto.
  Docs excluidos por screens → packet individual (con los 8-con-punteros y las colisiones).
- **~~P-D document_id en hyq~~ — ELIMINADO** (hallazgos S2+F5 convergentes): el scope y el dedup
  se resuelven por la RELACIÓN autoritativa `chunk_id→chunks_v2` (embed PostgREST) sin segunda
  fuente de verdad que pueda quedar stale (el rebinding hp011 ya reescribió
  `chunks_v2.document_id`; una copia en hyq no lo seguiría). Ver §5.

### F2 — Lane hardening (código; la lane sigue OFF; buildable pre-paste)
1. **Scope por document_id VÍA EMBED**: navegación
   `select=chunk_id,question,source_file,page_number,chunks_v2!inner(document_id,duplicate_of)` +
   `chunks_v2.document_id=in.(<resolved>)` + `chunks_v2.duplicate_of=is.null` (FK única de 013:21
   → embed inambiguo; orden/paginación top-level intactos; `idx_chunks_v2_document_id` existe —
   verificado en DB). Los ids vienen del RESOLVER (`resolved_documents`) — contrato intocado;
   cobertura id-scope = name-scope (ambas exigen doc_map; verificado por el sub-agente).
2. **Re-assert post-hidratación por `document_id` del chunk real** (no por source_file —
   hallazgo F5: un drift navegaría bajo doc A e hidrataría doc B en silencio) + `duplicate_of`
   en `_PARENT_SELECT` + skip (cinturón).
3. **Autoridad por parent — predicado ENUMERADO** (hallazgo S3, sin over-claim): 1 GET a
   `documents` por los document_id del scope → servible ⇔ **activo + sha real 64-hex +
   extraction==source_pdf + lineage `verified`** (NULL = fail-closed, semántica canónica).
   Language NO se gatea en esta lane (declarado; document_local mantiene su gate es). Presupuesto:
   4 páginas nav + 1 hidratación + 1 GET documents = 6/6 — **CERO holgura, declarado**; página
   5ª → fail-closed existente.
4. **Receipts**: fingerprints existentes + scope ids + razón de rechazo por parent.
GATE F2: tests exclusión (superseded/colisión/sha-mismatch/placeholder/dup/lineage-NULL → NO) +
mixed-state (sha real sin lineage aún → excluido SIN crash, con razón) + paridad por-lane verde +
suite completa.

### F3 — Verificación post-paste + eficacia (downstream; el GO-gate de volumen vive AQUÍ)
1. Census v3 delta: sha real 425→(+matched) · lineage 9→(+cohorte P-C según política elegida) ·
   language NULL 769→resto · 0 filas dup servibles por la lane.
2. Mecanismo primero: receipts de lane muestran los parents antes-bloqueados entrando (atribución
   por MECANISMO, no por delta de outcome).
3. **Freeze-contract de eficacia COMPLETO** (hallazgo S5): commit sha + shas de configs
   consumidas + fingerprint corpus pre/post + juez pineado (GPT-5.5 K-mayoría donde haya juicio)
   + seeds + N=2 reps (rerank no-determinista, DEC-096b). El outcome post-paste = **foto de
   serie nueva** (el corpus cambió), no «delta causal de A-core» — la atribución causal es F3.2.

## 4. FUERA DE SCOPE (declarado)
Taxonomía/arquetipos (lever separado post-A-core, old-vs-new config sobre corpus fijo, 39 dev) ·
A3 (perfil c1_v5, promoción, SLO) · surrogates H5 · doc_type backfill (ningún gate lo consume) ·
split D1 ZXSe + product_model unknown · mapeo catálogo 149 docs (DEC-074) · remediación de los
288 chunks-en-docs-no-activos y 25 huérfanos (censados; packet aparte si Alberto prioriza) ·
sha/language de retired/needs_review.

## 5. ALTERNATIVAS DESCARTADAS
- **A1 standalone** (scope irrealizable + autoridad debilitada — dúo previo, 0 FP).
- **P-D columna document_id en hyq**: segunda fuente de verdad sin invariante (stale en remaps
  reales); el embed la hace innecesaria. Queda como HEDGE declarado: SOLO si el embed fallara
  contra el deploy real (riesgo §6.5), y entonces exigiría FK compuesto + trigger de invariante —
  arco propio, no este.
- **Bulk lineage por «sin siblings en DB»** (v1): membership negativa derivada de labels =
  exactamente el label-drift contra el que avisa la migración s277; sustituido por screens +
  dossier + política adjudicada por Alberto.
- **Reutilizar `audit_chunk_languages.py` tal cual**: lee `chunks` legacy con muestra 3 —
  reconstruido con calibración.
- **Re-descargar shas de portales** · **borrar filas hyq dup** (rompe marks-only) · **lineage
  agrupando ES/EN** (H6) · **backfill por nombre de fichero** (colisión hp011 + re-guardados).

## 6. RIESGOS DECLARADOS
1. H1 por estrato (§2) — techo honesto si falla.
2. Cobertura de blobs incierta (duplicados entre carpetas; sin garantía superset) — match-rate
   real en F0; lo no-matcheado queda placeholder.
3. **Riesgo residual de P-C(ii)**: revisión-hermana no-ingestada o con nombre irreconocible por
   los screens → lineage single-revision «verified» para una obra con revisión más nueva
   invisible. Irreducible por predicado; declarado en el contrato + reversible 1 UPDATE +
   [ALBERTO decide] la política.
4. Fingerprint del corpus cambia con cada paste (esperado; estampado; frozen intocados:
   `s100_factlevel_full*`, b92ff51, contrato s277, ledger golds `79701140…`).
5. Embed PostgREST contra deploy real: sintaxis validada por revisión, no ejecutada — smoke en
   build; fallback = P-D-como-hedge (§5), declarado si ocurre.
6. Detector v2 FN en OCR-pobre/multi-idioma → calibración F0(e) + QA sample + NULL se queda.
7. Cap 6/6 sin holgura — cualquier pieza nueva de la lane requerirá re-presupuestar, no colar.

## 7. PROTOCOLO
r1 HECHO (Sol NO-SÓLIDO + Fable SÓLIDO-CON-CAMBIOS → esta v2; tally con regla-C, 12 hallazgos,
0 FP). Siguiente: **ronda de confirmación FRESCA focused sobre v2** (Sol xhigh; agente nuevo) →
build F0 → F1 staging → pastes de Alberto → F2 → F3. Stop-lines: SQL/migraciones = paste de
Alberto · merges = Alberto · held-out embargado. Audits 39 dev only.
