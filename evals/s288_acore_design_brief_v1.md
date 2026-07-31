# s288 — A-CORE: autoridad documental + scope enforcement (spec normativo ÚNICO, v3 SELLADO)

Workstream A (Alberto 30-jul: infraestructura ANTES de etapa 3, upstream-first). A-core consolida
A1+A2. **v3 = reescritura in-place tras dúo r1 (Sol 5 + Fable 7) y Sol focused r2 (6) — 18/18
hallazgos confirmados regla-C, 0 FP.** El cambio mayor de r2: **A-core NO acuña lineages en
bloque** (crítico-2 r2: los predicados no adjudican autoridad; el dossier sellaba una inferencia
negativa) — la lane hyq sirve en tier «blob-verificado» SIN exigir lineage, y el lineage pasa a
workstream de TRAMOS adjudicados por Alberto con la semántica canónica intacta. Este doc
REEMPLAZA a `s288_a1_hyq_scope_design_brief_v1.md`. Sin bloques apilados: toda revisión reescribe.

## 0. OBJETIVO + MÉTRICA (Protocolo 2 §5)
A-core deja la identidad documental (sha real VERIFICADO + language + status) consumible por las
lanes, y hace `doc_scoped_hyq_coverage` doc-scoped con predicado de autoridad ENUMERADO y honesto:
**tier blob-verificado** (activo + sha real + binding + dup-excluded + doc-scoped). El tier
lineage-adjudicado queda EXCLUSIVO de document_local (gate canónico intocado, crece por tramos).
- **GO-gates = CORRECCIÓN + VOLUMEN PRE-REGISTRADO** (fix r2-3): F0 estampa el nº exacto de
  elegibles por packet EN los guards del packet; el gate F3 = aplicado == 100% de elegibles
  staged (no tautologías «→(+matched)»).
- **EFICACIA ≠ GO-gate**: cohorte {cat010#0, hp012#3} + hp013#1 baseline, SOLO 39 dev (held-out
  EMBARGADOS). Su ruta de unlock = P-A (sus docs son placeholder) + F2 — sin dependencia de P-C.
- Settled citados con métrica (sin colisión): DEC-099 (canal hyq retrieval, ON, intocado) ·
  DEC-152/s279+s281 (el cuello es backfill de identidad) · digest fila S277 · DEC-085/086 (⊥).

## 1. CENSUS VERIFICADO (30-jul, SELECT-only DB live; FOTO datada — los packets se dimensionan
## contra el snapshot F0, no contra esta sección)
- `documents` 1169: 995 active · 91 retired · 79 needs_review · 4 superseded.
- sha: **744 placeholder** (`backfill:` + sha256 del NOMBRE — 001_backfill_documents.py:261) ·
  **425 64-hex**, 415 con chunks, **414 binding-ok** (1 mismatch → packet). Placeholder con
  chunks: 590 (587 single-extraction + 3 multi → packet).
- **Colisiones de blob: 0 HOY** (0 grupos same-mfr y 0 cross-mfr en {425 ∪ 587}); el UNIQUE
  `documents_mfr_hash_unique` (001_document_management.sql:68) exige el guard en P-A igualmente.
- lineage: **6 lineages verified / 9 docs** (`explicit_document_ids_v1`, evidence sha por fila).
  F0 publica la partición exhaustiva (la aritmética de familias de v1 era incorrecta).
- language: 769 NULL (326 es · 63 en · 11 otros). Los ~400 etiquetados = set de calibración del
  detector, **cuya PROCEDENCIA se documenta en F0 (fix r2-6: acuerdo con labels de procedencia
  no auditada mide reproducción, no exactitud)**.
- `chunks_v2_hyq` 70.126 filas / 23.205 padres: **7.421 filas (10,6%) con padre `duplicate_of`**
  — el canal retrieval guarda (retriever.py:1098/1539); la lane doc_scoped NO (verificado por
  ambos revisores). Cobertura 1.002/1.012 source_files.
- Deriva censada (se reporta, NO se toca): 25 chunks document_id NULL · 288 chunks vivos en docs
  no-activos · 10 document_id → docs no-activos.
- **Blobs locales: 1.334 PDFs** en `OneDrive…\Technical Bot\Manuales_*` (C:\dev no los tiene).
- **H1 PRE-VERIFICADA con clave independiente (stem → hash → comparar): 34/34** (14 binding-ok
  Aritech + 20 placeholder multi-marca) — `extraction_sha256` ES el sha de bytes del PDF.
- Prior art: `s281_h0_identity_census.py` (stack 2×) · guards s287 · `audit_chunk_languages.py`
  SOLO como referencia (lee `chunks` legacy, muestra 3 — detector se RECONSTRUYE).

## 2. HIPÓTESIS H1 (premisa verificable — DEC-022)
`extraction_sha256` = sha256 de los BYTES del PDF fuente. Gate NO-circular: probe por clave
INDEPENDIENTE (stem/path) → hash → comparar; publica match/mismatch/ausente; n≥60 estratificado
por vintage/marca; pre-evidencia 34/34. En re-ingesta `extraction_derivation.py:66-68` iguala por
fiat — H1 verifica el vintage ORIGINAL. Estrato que falla → fuera de P-A, techo declarado.

## 3. FASES (orden normativo; todo SQL = paste de Alberto)

### F0 — Census v2 ($0, read-only, determinista 2×, salida `evals/s288_acore_census_v2_*`)
(a) **Manifest de blobs** (JSONL: path, sha256, size, stem) con match DUAL por doc: por-stem y
    por-sha.
(b) **Partición exhaustiva** de los 1169 (status × clase-sha × binding × lineage × language ×
    blob-local) — los packets citan celdas; suma == 1169.
(c) **Gate H1** (§2) + grupos sha-compartido same/cross-mfr (guard P-A; hoy 0).
(d) **Census hyq** (filas/padres dup, cobertura, huérfanos).
(e) **Detector idioma v2 + calibración + PROCEDENCIA**: reconstruido sobre `chunks_v2` (por-doc,
    ≥10 chunks o todos, umbral de marcadores, universo {es,en,pt,it,fr}). Gates: (i) procedencia
    de los ~400 labels existentes documentada (de dónde salieron — reingest/manual/s287); (ii)
    acuerdo ≥99% es/en contra ellos con matriz publicada (necesario, no suficiente — se declara);
    (iii) muestra QA de 30 estratificada con **regla de aceptación explícita: 30/30 correctos o
    HALT y revisión del detector** (fix r2-6). Sin (i)-(iii) no se stagea P-B.
(f) **Screens de siblings** (para el workstream de tramos P-C y para contexto de P-A): punteros ·
    colisión de stem-normalizado (strip rev/fecha/idioma) · misma tupla (mfr, pm, doc_type,
    language) con doc_type conocido — contra TODOS los status; recuentos publicados.
(g) **Pre-registro de volumen** (fix r2-3): nº exacto de elegibles P-A y P-B estampado en el
    report Y en los guards de los packets.
GATE F0: determinismo 2× byte-idéntico · H1 explícito · partición suma 1169 · (e) verde.

### F1 — Packets SQL staged (guards s287: precondiciones + backup + conteos + rollback)
- **P-A sha real — bulk DUAL-KEY (fix r2-1)**: elegible ⇔ doc ACTIVO + single-extraction +
  **stem-match Y sha-match al MISMO blob** (la coincidencia independiente nombre→blob→hash por
  fila rompe la circularidad per-doc: un binding chunk→doc erróneo no se «auto-confirma») +
  grupo-sha singleton per-mfr contra todos los status (guard UNIQUE). Sha-match con stem
  distinto (renombres) + multi-extraction (3) + mismatch (1) → packet de ADJUDICACIÓN, no bulk.
  Sin blob → placeholder se queda (techo declarado). Retired/needs_review: fuera del bulk.
- **P-B language** (bulk = activos, detector v2 con F0(e) verde, confianza alta + idioma único):
  UPDATE por doc; baja confianza/mixto → NULL se queda.
- **P-C lineage — RE-SCOPEADO A TRAMOS (fix r2-2, el crítico): A-core NO acuña lineages en
  bloque.** La semántica canónica («explicitly adjudicated», evidence por fila) se preserva
  íntegra: P-C = packets de TRAMO (tamaño a elección de Alberto, p.ej. 25-50 docs) para el
  crecimiento de document_local, cada doc con su línea de dossier (document_id, stem, blob_sha,
  screens F0(f) limpios, census_tag) y `authority_evidence_sha256` = sha de esa línea; la
  revisión del tramo por Alberto ES la adjudicación. Ritmo y arranque = [ALBERTO]; **el GO de
  A-core NO depende de P-C** (la lane hyq no exige lineage — §F2.3). Excluidos por screens →
  adjudicación individual.
- **~~P-D document_id en hyq~~ — ELIMINADO** (r1 convergente): scope+dedup vía la relación
  autoritativa `chunk_id→chunks_v2` (embed). Ver §5.
Orden de pastes: P-A → P-B · P-C en tramos cuando Alberto quiera (independiente del GO).

### F2 — Lane hardening (código; lane sigue OFF; buildable pre-paste)
1. **Scope por document_id VÍA EMBED**: navegación
   `select=chunk_id,question,chunks_v2!inner(document_id,duplicate_of,source_file,page_number)` +
   `chunks_v2.document_id=in.(<resolved>)` + `chunks_v2.duplicate_of=is.null` (FK única 013:21;
   orden/paginación top-level; `idx_chunks_v2_document_id` verificado en DB). Ids del RESOLVER
   (contrato intocado); cobertura id-scope = name-scope (verificado r1).
2. **Campos desnormalizados DEMOVIDOS (fix r2-5)**: orden estable, diversidad por fuente y
   agrupación consumen `source_file`/`page_number` DEL PARENT EMBEBIDO, no de la fila hyq (la
   copia hyq queda como display/debug). Re-assert post-hidratación por `document_id` del chunk
   real + `duplicate_of` en `_PARENT_SELECT` + skip (cinturón).
3. **Autoridad por parent — tier BLOB-VERIFICADO, enumerado y honesto**: 1 GET a `documents` por
   los document_id del scope → servible ⇔ **activo + sha real 64-hex + extraction==source_pdf**.
   Placeholder/no-activo ⇒ fuera con razón trazada; fail-closed en error. **Lineage NO se exige
   en esta lane** (declarado: el tier lineage-adjudicado es de document_local; nombrar el tier
   evita el over-claim r1-3 sin heredar el crítico r2-2). Language no se gatea (declarado).
   Presupuesto: 4 nav + 1 hidratación + 1 documents = **6/6, CERO holgura, declarado**.
4. **Receipts**: fingerprints + scope ids + razón de rechazo por parent.
GATE F2: tests exclusión (superseded/colisión/sha-mismatch/placeholder/dup → NO) + mixed-state
(P-A parcial no mata en silencio) + paridad por-lane + suite completa.

### F3 — Verificación post-paste + eficacia (downstream)
1. **Volumen contra pre-registro F0(g)**: aplicado == 100% de elegibles staged por packet;
   census v3 publica el delta real celda a celda. 0 filas dup servibles por la lane.
2. Mecanismo primero: receipts de lane muestran los parents antes-bloqueados entrando
   (atribución por MECANISMO).
3. **Freeze-contract de eficacia** (fix r2-4): commit sha + shas de configs consumidas +
  fingerprint corpus pre/post + **pin de embeddings de query (`EMBED_CACHE_PATH`, DEC-048c —
  registrado u congelado, la 2ª fuente de variación que seeds+reps no aíslan)** + juez pineado
  (GPT-5.5 K-mayoría donde haya juicio) + seeds + N=2 reps (DEC-096b). Outcome post-paste =
  foto de serie nueva; la atribución causal es F3.2.

## 4. FUERA DE SCOPE (declarado)
Taxonomía/arquetipos (lever separado post-A-core, corpus fijo, 39 dev) · A3 (perfil c1_v5) ·
surrogates H5 · doc_type backfill · split D1 ZXSe · mapeo catálogo 149 docs (DEC-074) ·
remediación 288 chunks-en-docs-no-activos y 25 huérfanos (censados; packet aparte si se
prioriza) · sha/language de retired/needs_review · **crecimiento document_local por tramos P-C
(workstream continuo post-A-core, ritmo de Alberto)**.

## 5. ALTERNATIVAS DESCARTADAS
- **A1 standalone** (dúo previo, 0 FP).
- **P-D columna document_id en hyq**: segunda fuente de verdad sin invariante; HEDGE declarado
  solo si el embed falla contra el deploy real (§6.5), y exigiría FK+trigger — arco propio.
- **Bulk lineage 'verified'** (v1 por ausencia-de-siblings; v2 por dossier+screens): DOS rondas
  de Sol lo tumban — los predicados no adjudican autoridad y el dossier sella una inferencia
  negativa; además la lane hyq no lo necesita. Sustituido por tramos adjudicados (semántica
  canónica intacta) + tier blob-verificado en la lane.
- **P-A por sha-only**: circularidad per-doc (r2-1) — dual-key o adjudicación.
- **Reutilizar `audit_chunk_languages.py` tal cual** · **re-descargar shas** · **borrar filas
  hyq dup** · **lineage ES/EN agrupado** (H6) · **backfill por nombre-only** (hp011).

## 6. RIESGOS DECLARADOS
1. H1 por estrato — techo honesto si falla.
2. Cobertura de blobs incierta — match-rate real en F0; no-matcheado queda placeholder.
3. **Tier blob-verificado ≠ lineage-adjudicado**: la lane hyq puede servir un doc activo
   blob-verificado cuya revisión más nueva no esté ingestada — MISMO expuesto que el canal
   vectorial de prod hoy (no es regresión; se declara para que nadie lo lea como autoridad
   canónica). document_local mantiene la garantía fuerte.
4. Fingerprint del corpus cambia con cada paste (esperado; estampado; frozen intocados:
   `s100_factlevel_full*`, b92ff51, contrato s277, ledger golds `79701140…`).
5. Embed PostgREST contra deploy real: smoke en build; fallback = P-D-como-hedge (§5).
6. Detector v2: calibración = reproducción (necesaria, no suficiente) + QA 30/30 con HALT;
   procedencia de labels documentada; residuo queda NULL.
7. Cap 6/6 sin holgura — pieza nueva ⇒ re-presupuestar, no colar.
8. P-B con labels legacy erróneos de origen: el QA 30/30 es la barrera; si cae un error legacy
   sistemático en QA → HALT y revisión de la cohorte etiquetada, no solo del detector.

## 7. PROTOCOLO
r1 (Sol 5 + Fable 7) y r2 focused (Sol 6) HECHOS → esta v3 = spec SELLADO; 18/18 confirmados,
0 FP, tally en `evals/adversarial_review_log.jsonl`. Siguiente: **build F0** (Opus ejecuta bajo
spec cerrado; los puntos delicados: dual-key matching, determinismo 2×, calibración con
procedencia). Stop-lines: SQL = paste de Alberto · merges = Alberto · held-out embargado.
Audits 39 dev only.
