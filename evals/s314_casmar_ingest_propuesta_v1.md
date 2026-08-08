# s314 — Propuesta: `ingest_new.py` + primer lote real (Casmar/Kidde) — para el dúo

**OBJETIVO + MÉTRICA de HOY**: cerrar el gap orgánico del NC-PF2 (manual instalación) y
los 104 gaps documentales Kidde medidos en `evals/s314_casmar_kidde_cruce_v1.md`, con la
automatización de altas (`scripts/ingest_new.py`, frente 7 del PLAN) estrenada de verdad.
Métrica de éxito: los docs nuevos INDEXADOS con fila `documents` enlazada + sonda de
alcanzabilidad (query ES estilo s303) que sirva el manual NC-PFx. NO toca ningún lever
medido de retrieval (es adquisición de corpus, no mecanismo); el corpus cambia ⇒ freeze
per-eval (DEC-071e): la próxima fila del assessment anota corpus nuevo.

## Recomendación

1. **`scripts/ingest_new.py`** (ya en esta rama): driver A2+B para lotes nuevos por
   canal. GATES fail-closed (canal declarado en portal.yaml · sidecar OBLIGATORIO por
   fichero · PDF legible >1KB · exclusión certificados/homologaciones por token · dedup
   sha256 vs store Y vs `documents`) → dry-run por defecto (0 API, informe+coste) →
   `--commit`: extracción LlamaParse al store canónico (source_path ABSOLUTO para que
   el sidecar Capa B resuelva) → **alta de fila `documents` ANTES de indexar** (cierra
   el hueco histórico: el pipeline no crea filas y `resolve_document_id` solo enlaza;
   las altas s55/s58 fueron backfills post-hoc, cf. notes de s65 en la tabla) → B
   completo (`process_file`) → verificación en DB (chunks>0 + document_id enlazado) →
   recibo JSON en `<data-root>/logs/`.
2. **Lote Casmar/Kidde**: 75 PDFs nuevos (928 págs, ~$52 LlamaParse) ya descargados y
   dedupeados en staging (recibo `evals/s314_casmar_batch_report_v1.json`). Entradas de
   sidecar generadas con la convención existente (equipo=serie para docs de familia,
   precedente «2X-A»; campo extra `fuente: casmarglobal.com`, inerte para metadata.py).
   **Ejecución en 2 etapas** (disciplina de coste s85: validar barato primero):
   - **Etapa 1 (~$10)**: familia NC-PFx (MI 126 págs + G_INST + G_USO + guía rápida) —
     exactamente el gap orgánico de Alberto; valida el ciclo entero end-to-end con
     sonda de alcanzabilidad.
   - **Etapa 2 (~$42)**: el resto (70 docs) tras verificar la etapa 1.
3. Post-lote: Excel inventario + nota de corpus en el assessment + sonda s303.

## Alternativas consideradas y descartadas

- **Reusar `pipeline.run()` entero** (en vez de `process_file` por sha): su glob+estado
  procesan el store completo (1.069 registros) y su STATE_FILE vive relativo al cwd del
  código — para un lote acotado el driver por-sha es más simple y no toca estado global.
- **Canal nuevo `Manuales_Kidde_Casmar`**: el canal ES el fabricante en el seam
  (channel_manufacturer) → «Kidde_Casmar» contaminaría manufacturer. Reusar el canal
  `Kidde` + `fuente` en el sidecar preserva identidad y procedencia sin tocar código.
- **Crear filas `documents` después de indexar** (patrón backfill histórico): deja
  ventana con chunks sin ciclo de vida y repite el hueco que este driver viene a cerrar.
- **Ingestar también homologaciones/certificados**: excluido por regla explícita de
  Alberto (y del playbook: no responder dudas técnicas con certificados).
- **Scraper Casmar genérico/permanente**: prematuro (DEC del frente 7: auto-ingesta por
  scraper pasa a obligatoria con el primer técnico real); el harvest queda como método
  documentado en el recibo del cruce.

## Gaps / riesgos declarados

- **`_EXCLUIR_TOKENS` por substring** puede dar falso positivo en filenames legítimos
  con «_doc_»/«_ce_» (defensa en profundidad: la primera línea es no descargar; la
  exclusión se LISTA siempre en el informe, nunca silenciosa).
- **`process_file` dry para identidad + `detect_document_metadata` re-invocado** para
  doc_type: misma función y mismos inputs que B5 usará en real (sin drift por
  construcción), pero es una llamada duplicada — coste cero, riesgo de divergencia si
  B5 cambiara su receta de sample (4 chunks) sin tocar este driver.
- **Vista filtrada del portal sin paginación** (~6 SKUs en exactamente 10 docs): riesgo
  residual de sub-conteo, acotado por el dedup familiar (recibo del cruce).
- **2X-AT**: 2 de sus docs resultaron byte-idénticos al corpus (dedup los paró); los MU
  no-idénticos podrían ser REVISIONES del manual «2X-A Táctil» existente → si lo son,
  el corpus tendrá 2 revisiones activas sin cadena supersede (TECH_DEBT #4 vivo, no lo
  resuelve este lote — se declara en el recibo).
- **ZLSM/N-IO/N-MC**: identidad de marca por canal Kidde; si alguno fuera OEM de otra
  marca (como 2X-→Aritech), faltaría su override en portal.yaml — el sidecar los deja
  auditables (skus+fuente) y son corregibles por UPDATE (precedente s78).
- **`documents.language`**: el driver escribe el dominante del perfil B2; para PDFs
  multi-idioma es una simplificación (mismo criterio que el corpus actual).

## Por qué BP + estructural + escalable

- BP: gates fail-closed, dry-run por defecto, dedup por contenido, recibo por lote,
  identidad autoritativa por sidecar (no regex), coste estimado ANTES de gastar.
- Estructural: cierra el hueco real (documents sin creador en el flujo de altas) en el
  SEAM correcto y reusa las etapas vivas (A2/B) sin duplicar pipeline.
- Escalable: cualquier canal declarado en portal.yaml funciona igual (30+ fabricantes =
  más canales/sidecars, no más código); el harvest Casmar documentado es reproducible
  para las marcas que Casmar distribuye (Detnov, etc.).
