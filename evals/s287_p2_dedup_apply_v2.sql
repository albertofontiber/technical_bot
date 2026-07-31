-- s287 P2 — PASTE DE REMATE (v2). Cierra el workstream de dedup a nivel DOCUMENTO.
-- Predecesor: evals/s287_p2_dedup_apply_v1.sql  (12 marcas + metadata-fix del par semilla,
--             APLICADO por Alberto y VERIFICADO EN VIVO read-only 2026-07-30 → 12/12 OK,
--             backups _s287_* pobladas, metadata-fix completo, VIA-28V corpus-wide = 0).
-- Census: evals/s287_p2_dedup_census_v1.json · Packet: evals/s287_p2_dedup_adjudicacion_packet_v1.md
--
-- ⚠ ESCRITO A MANO tras la adjudicación FINAL de Alberto (s287) sobre §8 y el BLOQUE S.
--   `scripts/s287_p2_dedup_census.py` sobrescribe el v1.sql (OUT_SQL), NO este fichero.
--
-- ###########################################################################################
-- #  QUÉ ENTRA (3 bloques · 3 TRANSACCIONES SEPARADAS, se pueden pegar por separado):       #
-- #                                                                                          #
-- #   BLOQUE 1 · PAR 4  7f9ea4ab__acafc5d1  → 5 marcas duplicate_of   (Alberto: APROBAR,     #
-- #              «ganancia marginal aceptada»). Representante MNDT1026.                      #
-- #   BLOQUE 2 · PAR 19 06887ff1__1d4f6e36  → RETIRO del doc ES/PT    (Alberto: retirar el   #
-- #              ES/PT quedándose el ES/EN). Mecanismo `status='retired'`.                   #
-- #   BLOQUE 3 · BLOQUE S variante A        → LINAJE de #9 y #22 SIN tocar `status`.         #
-- #                                                                                          #
-- #  QUÉ NO ENTRA (adjudicado por Alberto en §8, sin filas):                                 #
-- #   PAR 3 (rebadge OEM FS/MS) · PAR 5 (marca DUAL EFS/EM) · PAR 6 (BRS≠BRH) ·              #
-- #   PAR 16 (REL-2000≠ZXCE) · PAR 18 (tóxico≠explosivo) → RECHAZADOS. Ver packet §8.        #
-- #   BLOQUE S variante B y C → NO adjudicadas (B apaga 54 chunks; C requiere des-enlace).   #
-- #   S.2 (des-enlace HP011) → COMENTADO al final, con la medida y el motivo.                #
-- ###########################################################################################
--
-- PRE-VALIDACIÓN READ-ONLY EN VIVO (2026-07-30, cero escrituras) de los 3 bloques: 0 fallos.
-- Dry-run esperado:  BLOQUE 1 → staged=5 · updated=5 · backed_up=5
--                    BLOQUE 2 → retired_docs=1 (26 chunks dejan de servirse)
--                    BLOQUE 3 → cadenas=2 (4 documents tocados, 0 chunks tocados)
-- Dry-run de cualquier bloque: cambia su COMMIT por ROLLBACK.
--
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- NOMBRES DE TABLA NUEVOS — NO reutilizar los del v1 (fallo silencioso evitado)
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- El v1 usa `CREATE TABLE IF NOT EXISTS _s287_dedup_backup AS SELECT …`. Esas tablas YA
-- EXISTEN y están pobladas con las 12 filas del v1 (verificado en vivo). Si el v2 reutilizara
-- el mismo nombre, el `IF NOT EXISTS` haría NO-OP y el v2 correría **SIN BACKUP**, en silencio.
-- Por eso todo aquí lleva sufijo `_v2` y hay un guard explícito que ABORTA si el backup no
-- tiene exactamente las filas esperadas (el v1 no lo tenía: solo lo reportaba al final).


-- ###########################################################################################
-- #  BLOQUE 1 — PAR 4 · 7f9ea4ab__acafc5d1 · 5 marcas                                       #
-- ###########################################################################################
-- CONSERVA  'MNDT1026' (acafc5d1 · 30 chunks · «Aplicaciones del VIEW™ CON LA CENTRAL
--                       AFP-300/400» · MN-DT-1026_A · 24 MAR 2004)
-- SUPRIME   5 de 23 chunks de 'MNDT1025' (7f9ea4ab · «Aplicaciones del VIEW™» genérico ·
--                       MN-DT-1025 · 8 ABR 2004 · doc. 997-198)
-- PRESERVA  UNIQUE=3, PARTIAL=12, COVERED_NO_TWIN=3  (18 de 23 chunks siguen sirviéndose)
--
-- VEREDICTO Alberto (s287): APROBAR. Ganancia marginal aceptada con el residual delante.
-- DIRECCIÓN: la del census SIN invertir (el census ya eligió MNDT1026 como representante,
--   `decision.representative = acafc5d1`) — a diferencia del par semilla, aquí NO hay que
--   re-derivar clases: las 5 filas de abajo son literalmente `decision.proposed_marks` del
--   census, cotejadas 5/5 contra las filas comentadas del v1.sql (0 deriva de edición a mano).
--
-- RESIDUAL DECLARADO (verificado en vivo, es el que Alberto aceptó):
--   los 23 chunks de MNDT1025 llevan `product_model='FSL-751E'` y los 30 de MNDT1026 'VIEW'
--   — el mismo producto con dos nombres. `FSL-751E` existe corpus-wide SOLO en este doc
--   (23 chunks, los 23 activos hoy) → marcar 5 baja el alcance activo de esa etiqueta de
--   23 a 18. La unificación FSL-751E↔VIEW sigue siendo el arreglo que de verdad paga (A3).
--
-- LAS 8 CLASES DE GUARD, PRE-VALIDADAS EN VIVO READ-ONLY (2026-07-30) — 0 fallos:
--   [OK] 1  staging no vacía ................ 5 filas
--   [OK] 3a md5 sin deriva .................. 0 derivas (md5 vivo == md5 del census)
--   [OK] 3b ninguno ya marcado .............. los 5 con duplicate_of IS NULL
--   [OK] 3c canónico válido ................. existe · en el representante · sin marcar
--   [OK] 3d chunk en el doc suprimido ....... los 5 en 7f9ea4ab
--   [OK] 3e sin cadenas ..................... intersección {chunk_id} ∩ {canónico} = ∅
--   [OK] 3f gate span-diff .................. 0 violaciones (cov>=0.92 · racha<25 · J>=0.6)
--   [OK] 3g fuga de enunciados .............. 0 filas en chunks_v2_enunciados

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

-- 1.1 STAGING (nombre _v2: NO tocar la staging del v1, que es su traza de auditoría)
DROP TABLE IF EXISTS _s287_dedup_staging_v2;
CREATE TABLE _s287_dedup_staging_v2 (
  chunk_id                 uuid PRIMARY KEY,
  canonical_chunk_id       uuid NOT NULL,
  doc_suppressed           uuid NOT NULL,
  doc_representative       uuid NOT NULL,
  covered_word_frac        numeric NOT NULL,
  twin_jaccard             numeric NOT NULL,
  max_uncovered_span_words int NOT NULL,
  md5_content_before       text NOT NULL,
  pair_id                  text NOT NULL
);

INSERT INTO _s287_dedup_staging_v2
 (chunk_id, canonical_chunk_id, doc_suppressed, doc_representative,
  covered_word_frac, twin_jaccard, max_uncovered_span_words, md5_content_before, pair_id)
VALUES
  ('130b656a-2ad3-4025-b2bd-7768f46bfacf','a4bcff6e-b2e8-4328-b677-0048da277226','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9915,0.8413,0,'3a92eced40884313b187a82a35431c84','7f9ea4ab__acafc5d1'),   -- idx1  p2  «1 General»                 → gemelo idx1
  ('6def4121-4b61-4737-aba0-e2e488dce100','3d792de5-1b05-4028-b2c2-a2942f9267f6','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9912,0.8522,0,'80d7733541322e0105f98c7de9c290eb','7f9ea4ab__acafc5d1'),   -- idx2  p2  (sin section_title)          → gemelo idx2
  ('effaf7c3-413d-4b94-a0d4-7acfde4395fb','6d29d2d8-d34b-4599-a7ca-c118d54a12d7','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9764,0.8617,0,'d4516629a79407f1f286e7df176afb51','7f9ea4ab__acafc5d1'),   -- idx14 p8  «11 Algoritmos de filtrado»  → gemelo idx17
  ('ac8027dc-9c00-4ca5-a89d-7563ab84573f','ae1a68ce-3b87-4699-bd20-4bf3713ea238','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9523,0.6755,0,'cf4cfd643f4405a32a674af1526b9ff3','7f9ea4ab__acafc5d1'),   -- idx17 p9  «14 Pruebas y mantenimiento» → gemelo idx20
  ('685ab164-fac2-41be-ab86-febe0ff66059','d245c6fb-aa4c-40bb-b6b5-1fce2137d302','7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03',0.9520,0.7912,0,'a0a0cc249800e60cafa252169e33106e','7f9ea4ab__acafc5d1');  -- idx18 p10 «15 Informes especiales»    → gemelo idx21

-- 1.2 BACKUP (persistente, para rollback post-COMMIT) — nombre _v2 a propósito
CREATE TABLE IF NOT EXISTS _s287_dedup_backup_v2 AS
SELECT c.id, c.duplicate_of, md5(c.content) AS md5_content, now() AS backed_at
FROM chunks_v2 c
WHERE c.id IN (SELECT chunk_id FROM _s287_dedup_staging_v2);

-- 1.3 GUARDS previos (cualquiera aborta TODO)
DO $$
DECLARE n int; m int;
BEGIN
  SELECT count(*) INTO n FROM _s287_dedup_staging_v2;
  IF n <> 5 THEN RAISE EXCEPTION 'staging_v2 tiene % filas, se esperaban 5 — ABORTA', n; END IF;

  -- 0. NUEVO respecto al v1: el BACKUP tiene que existir Y estar completo. Si alguien
  --    reutilizó el nombre, `CREATE TABLE IF NOT EXISTS` habría hecho NO-OP en silencio.
  SELECT count(*) INTO m FROM _s287_dedup_backup_v2 b
   WHERE b.id IN (SELECT chunk_id FROM _s287_dedup_staging_v2);
  IF m <> n THEN RAISE EXCEPTION
    'BACKUP incompleto: % de % filas en _s287_dedup_backup_v2 — ABORTA (¿nombre reutilizado?)', m, n; END IF;

  -- 3a. anti-deriva: el contenido de cada chunk es el que vio el census
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2 s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE md5(c.content) <> s.md5_content_before;
  IF m > 0 THEN RAISE EXCEPTION 'DERIVA: % chunks cambiaron de contenido desde el census', m; END IF;

  -- 3b. ninguno estaba ya marcado
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2 s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE c.duplicate_of IS NOT NULL;
  IF m > 0 THEN RAISE EXCEPTION '% chunks ya tenían duplicate_of', m; END IF;

  -- 3c. el canónico existe, vive en el doc REPRESENTANTE y NO está marcado (sin cadenas)
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2 s
    LEFT JOIN chunks_v2 c ON c.id = s.canonical_chunk_id
   WHERE c.id IS NULL OR c.duplicate_of IS NOT NULL OR c.document_id <> s.doc_representative;
  IF m > 0 THEN RAISE EXCEPTION '% punteros canónicos inválidos', m; END IF;

  -- 3d. el chunk a marcar vive en el doc SUPRIMIDO
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2 s JOIN chunks_v2 c ON c.id = s.chunk_id
   WHERE c.document_id <> s.doc_suppressed;
  IF m > 0 THEN RAISE EXCEPTION '% chunks no pertenecen al doc que se suprime', m; END IF;

  -- 3e. ningún chunk es a la vez marcado y canónico de otro
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2 a
    JOIN _s287_dedup_staging_v2 b ON a.chunk_id = b.canonical_chunk_id;
  IF m > 0 THEN RAISE EXCEPTION 'cadena de duplicados detectada (% filas)', m; END IF;

  -- 3f. el invariante del gate viaja en los datos y se re-verifica aquí
  SELECT count(*) INTO m FROM _s287_dedup_staging_v2
   WHERE covered_word_frac < 0.92 OR max_uncovered_span_words >= 25 OR twin_jaccard < 0.6;
  IF m > 0 THEN RAISE EXCEPTION 'GATE SPAN-DIFF violado en % filas — ABORTA', m; END IF;

  -- 3g. FUGA de satélites: el RPC de enunciados NO filtra por duplicate_of del padre
  --     (migrations/012_enunciados_rpc_filters.sql).
  SELECT count(*) INTO m FROM chunks_v2_enunciados e
   WHERE e.parent_id IN (SELECT chunk_id FROM _s287_dedup_staging_v2);
  IF m > 0 THEN RAISE EXCEPTION 'FUGA enunciados: % filas cuelgan de chunks a marcar', m; END IF;
  -- (hyq NO necesita tratamiento: retriever.py:1094-1099 descarta client-side todo row con
  --  duplicate_of — el fix s286 de fuga-hyq. Verificado en el código, no asumido.)

  -- 3h. los DOS docs del par siguen activos (si uno se retiró, la marca no tiene sentido)
  SELECT count(*) INTO m FROM documents
   WHERE id IN ('7f9ea4ab-3fa6-49fc-ab7d-8ccc20d33bd6','acafc5d1-6a91-4faa-a896-c4abc0df3d03')
     AND status = 'active';
  IF m <> 2 THEN RAISE EXCEPTION 'par 4: % de 2 docs activos — ABORTA', m; END IF;
END $$;

-- 1.4 UPDATE atómico
WITH upd AS (
  UPDATE chunks_v2 c
     SET duplicate_of = s.canonical_chunk_id
    FROM _s287_dedup_staging_v2 s
   WHERE c.id = s.chunk_id
     AND c.duplicate_of IS NULL
     AND md5(c.content) = s.md5_content_before
  RETURNING c.id
)
SELECT count(*) AS updated INTO TEMP tmp_s287_v2_updated FROM upd;

DO $$
DECLARE n int; e int;
BEGIN
  SELECT updated INTO n FROM tmp_s287_v2_updated;
  SELECT count(*) INTO e FROM _s287_dedup_staging_v2;
  IF n <> e THEN RAISE EXCEPTION 'updated % <> staging % — ABORTA TODO', n, e; END IF;
END $$;

SELECT (SELECT count(*) FROM _s287_dedup_staging_v2) AS staged,
       (SELECT updated FROM tmp_s287_v2_updated)     AS updated,
       (SELECT count(*) FROM _s287_dedup_backup_v2)  AS backed_up;

COMMIT;   -- <-- para dry-run: ROLLBACK

-- ROLLBACK post-COMMIT del BLOQUE 1:
--   UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of
--     FROM _s287_dedup_backup_v2 b WHERE c.id = b.id;


-- ###########################################################################################
-- #  BLOQUE 2 — PAR 19 · RETIRO del doc ES/PT  (06887ff1__1d4f6e36)                         #
-- ###########################################################################################
-- VEREDICTO Alberto (s287): retirar el ES/PT y quedarse el ES/EN. Es SU propuesta original;
--   la «alternativa sin pérdida» que yo recomendaba (marcar solo las 11 filas TWIN) queda
--   DESCARTADA por su adjudicación — no se aplica ninguna de sus filas aquí.
--
-- SE QUEDA   'MNDT516'              06887ff1 · ES/EN · 56 chunks
-- SE RETIRA  'MNDT516_PL4_ESP-PORT' 1d4f6e36 · ES/PT · 26 chunks
--
-- MECANISMO: `status='retired'`, NO 'superseded'.
--   No hay revisión nueva: es el MISMO documento (pie «MN-DT-516.doc (MT3910.doc)») en dos
--   ediciones bilingües. 'superseded' significaría que una sustituye a la otra en el tiempo.
--   VERIFICADO que el filtro de lifecycle trata igual a los dos valores: `_filter_by_document_status`
--   descarta todo chunk cuyo doc padre tenga `status <> 'active'` (retriever.py:2801-2803), y
--   'retired' está en el vocabulario de autoridad (`_DOC_STATUS_AUTHORITY`, retriever.py).
--   'retired' está PRECEDENTADO en el corpus: 90 de 1169 documents ya lo usan.
--   Sin CHECK constraint en la columna (migrations/001_document_management.sql:56).
--
-- ⚠ EXCEPCIÓN DECLARADA a la política KEEP-BOTH-LANG del census (11 pares · «idiomas
--   distintos = variante de mercado, NUNCA suprimir», la que protege los 41 grupos ES/EN
--   legítimos del corpus). Se aplica aquí porque el PT no tiene audiencia en Fontiber hoy y
--   porque `status` es reversible en una línea. NO es la aplicación de la política: es su
--   excepción, y queda escrita para que no se cite este paste como precedente general.
--
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN CHUNK A CHUNK QUE PIDIÓ ALBERTO (read-only en vivo, 2026-07-30)
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- Método: span-diff de los 26 chunks del ES/PT contra el texto COMPLETO del ES/EN (shingles
-- de 8 palabras, `norm_ocr`, rachas no cubiertas >= 25 palabras) + clasificación PT/ES de
-- cada racha + prueba de PRESENCIA DEL HECHO en el ES/EN para cada racha en español.
--
--   · 11 chunks TWIN (cov >= 0.92, ninguna racha >= 25w) — 6 de ellos con Jaccard 1.000.
--   · 15 chunks con al menos una racha no cubierta. De sus rachas:
--       – las de idx0, idx13, idx18, idx20, idx23 son TRADUCCIÓN PORTUGUESA → no es un hecho
--         ausente, es el mismo hecho en otro idioma;
--       – las de idx3, idx10, idx11 son PROSA DE FIGURA del extractor (descripciones en inglés
--         entre corchetes: "[Photograph showing…]", "[Technical diagram showing…]");
--       – las de idx4, idx6, idx7, idx8, idx13, idx20, idx24 sí llevan texto ESPAÑOL.
--   · Para esas rachas españolas probé 55 tokens técnicos contra el texto del ES/EN.
--     RESULTADO: 52 de 55 presentes. Los 3 «ausentes» se resuelven y NINGUNO es un hecho
--     exclusivo (esto es lo que autoriza el retiro doc-level; si uno solo hubiera sido
--     exclusivo, este bloque saldría COMENTADO):
--       (1) 'max. 2A'  → el ES/EN tiene la MISMA etiqueta de figura con otra puntuación:
--                        «- Aux voltage output 1 (24Vdc) (max 2)». Mismo dato.
--       (2) '230V'     → el ES/EN da la especificación real, y es MÁS completa:
--                        «Tensión de alimentación: 220VcA +/- 10%», «Power supply: 100-240 Vac»,
--                        «3.1 Alimentación principal (220Vca)», «(AC) 220 VAC operation».
--                        220V ±10% y 100-240 Vac cubren 230 V — el '230V' del ES/PT está en
--                        prosa de figura, no en la tabla de specs. Mismo hecho, nominal distinto.
--       (3) '15/06/2017' → fecha de pie de página, no un hecho técnico.
--                        NOTA que CORRIGE al packet §8.7: los pies NO son idénticos —
--                        ES/EN dice 13/06/2017 y ES/PT 15/06/2017. Dos ediciones del mismo
--                        documento con dos días de diferencia; no cambia la adjudicación.
--     Verificados presentes en el ES/EN, uno a uno: CN7 · CN10 · CN12 · CN16A · CN16B · CN17 ·
--     JP1..JP4 · Jp20..Jp23 · RL1 · J1..J4 · NC1 · NA1 · NC4 · «Avería (FLT)» · (AL1)(AL2)(AL3)
--     (AUX)(BATT) · «Normalmente abierto/cerrado» · «NORMALMENTE ACTIVADOS» · «Módulo de
--     ampliación» · «Microinterruptores» · SMART3 · «CABLE APANTALLADO» · «3 X 0,75» ·
--     «TERMINALES DE LA CENTRAL» · PL4+ · «MENU PI4» · «VERS. 3.04» · «Funcionamiento con batería».
--     El diagrama «CONEXIÓN DE DETECTORES DE LA SERIE SMART3 A LA CENTRAL PL4+» (idx11, el
--     único candidato a hecho exclusivo que señalaba el packet) EXISTE en el ES/EN (idx21, idx40).
--
--   >>> CONCLUSIÓN: 0 hechos exclusivos en el ES/PT. El retiro doc-level NO pierde contenido
--       factual. Lo que se pierde es la TRADUCCIÓN PORTUGUESA — que es exactamente lo que
--       Alberto adjudicó retirar.
--
-- SEGURIDAD (verificado en vivo, todo a cero):
--   · 0 punteros `duplicate_of` ENTRANTES hacia los 26 chunks → el retiro no crea huérfanos
--     (patrón HP011: un canónico que deja de servirse dejaría contenido suprimido sin fuente).
--   · 0 de los 26 chunks está ya marcado con `duplicate_of`.
--   · 0 filas en `chunks_v2_enunciados` colgando de los 26.
--   · 56 filas en `chunks_v2_hyq` SÍ cuelgan de ellos, y NO hay fuga: los surrogates hyq se
--     hidratan desde chunks_v2 con `_HYDRATE_SELECT` (incluye `document_id`, retriever.py:1263-1265)
--     y pasan DESPUÉS por el filtro de lifecycle del Step 4b (retriever.py:1789-1793) → un doc
--     'retired' no puede resucitar por ese canal. Verificado en el código, no asumido.

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

-- 2.1 BACKUP
CREATE TABLE IF NOT EXISTS _s287_retire_backup_documents_v2 AS
SELECT id, status, now() AS backed_at FROM documents
 WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';

-- 2.2 GUARDS
DO $$
DECLARE m int;
BEGIN
  -- backup completo (mismo control que el bloque 1)
  SELECT count(*) INTO m FROM _s287_retire_backup_documents_v2
   WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
  IF m <> 1 THEN RAISE EXCEPTION
    'BACKUP incompleto (% de 1) — ABORTA (¿nombre de tabla reutilizado?)', m; END IF;

  -- pre-estado EXACTO del doc a retirar
  SELECT count(*) INTO m FROM documents
   WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND status = 'active'
     AND source_pdf_filename = 'MNDT516_PL4_ESP-PORT' AND product_model = 'PL4'
     AND manufacturer = 'Notifier';
  IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el doc ES/PT no está en el pre-estado — ABORTA'; END IF;

  -- cardinalidad (ancla anti-deriva)
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
  IF m <> 26 THEN RAISE EXCEPTION 'PAR19: % chunks, la sonda vio 26 — ABORTA', m; END IF;

  -- el doc ES/EN que se queda tiene que seguir vivo y COMPLETO (56 chunks)
  SELECT count(*) INTO m FROM documents
   WHERE id = '06887ff1-3783-4c29-9f4b-0012facfebb1' AND status = 'active';
  IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el doc ES/EN no está activo — ABORTA'; END IF;
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '06887ff1-3783-4c29-9f4b-0012facfebb1';
  IF m <> 56 THEN RAISE EXCEPTION 'PAR19: el ES/EN tiene % chunks, la sonda vio 56 — ABORTA', m; END IF;

  -- ANTI-HUÉRFANO (patrón HP011): nadie puede depender de los chunks que se apagan
  SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
   WHERE t.document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
  IF m > 0 THEN RAISE EXCEPTION 'PAR19: % chunks quedarían huérfanos — trátalos antes', m; END IF;

  -- ninguno de los 26 está marcado (si lo estuviera, su canónico ya lo cubría: no rompe,
  -- pero el pre-estado dejaría de ser el verificado → aborta y se re-verifica)
  SELECT count(*) INTO m FROM chunks_v2
   WHERE document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND duplicate_of IS NOT NULL;
  IF m > 0 THEN RAISE EXCEPTION 'PAR19: % de los 26 ya están marcados — ABORTA', m; END IF;

  -- 0 enunciados colgando (el RPC de enunciados no filtra por status del doc padre)
  SELECT count(*) INTO m FROM chunks_v2_enunciados e
   JOIN chunks_v2 c ON c.id = e.parent_id
   WHERE c.document_id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d';
  IF m > 0 THEN RAISE EXCEPTION 'PAR19: FUGA enunciados, % filas — trátalas antes', m; END IF;
END $$;

-- 2.3 UPDATE
UPDATE documents SET status = 'retired'
 WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND status = 'active';

-- 2.4 POST-CHECK
DO $$
DECLARE m int;
BEGIN
  SELECT count(*) INTO m FROM documents
   WHERE id = '1d4f6e36-0582-42e7-b9c8-62339d5a999d' AND status = 'retired';
  IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el retiro no se aplicó — ABORTA'; END IF;
  -- el ES/EN NO se ha tocado
  SELECT count(*) INTO m FROM documents
   WHERE id = '06887ff1-3783-4c29-9f4b-0012facfebb1' AND status = 'active';
  IF m <> 1 THEN RAISE EXCEPTION 'PAR19: el ES/EN dejó de estar activo — ABORTA'; END IF;
END $$;

SELECT id, source_pdf_filename, status FROM documents
 WHERE id IN ('1d4f6e36-0582-42e7-b9c8-62339d5a999d','06887ff1-3783-4c29-9f4b-0012facfebb1');

COMMIT;   -- <-- para dry-run: ROLLBACK

-- ROLLBACK post-COMMIT del BLOQUE 2:
--   UPDATE documents d SET status = b.status
--     FROM _s287_retire_backup_documents_v2 b WHERE d.id = b.id;


-- ###########################################################################################
-- #  BLOQUE 3 — BLOQUE S · VARIANTE A · LINAJE SIN APAGAR NADA (pares 9 y 22)               #
-- ###########################################################################################
-- VEREDICTO Alberto (s287): variante A. Materializa `supersedes_id`/`superseded_by_id` y
--   deja `status='active'` en los cuatro. B (apagar las 7.2) y C (dedup por chunk) NO se aplican.
--
--   PAR 9   MI-DT-951 «Manual de introducción»
--           VIEJO  681e506b 'MI-DT-951_V7.2'             MI-DT-951 (Rev.:7.2) · Sept 2007 · TG-NOTIFIER
--           NUEVO  a7bf5098 'Tg-Honeywell_Introduccion'  MI-DT-951 (Rev.:7.4) · Abril 2009 · TG-HONEYWELL
--   PAR 22  MN-DT-951 «Manual de usuario»
--           VIEJO  5e483105 'MN-DT-951_v7.2'             MN-DT-951 (Rev.:7.2) · Sept 2007 · TG-NOTIFIER
--           NUEVO  71654eda 'TG-Honeywell_Usuario'       MN-DT-951 (Rev.:7.4) · 06/04/2017 · TG-HONEYWELL
--
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- ⚠ CORRECCIÓN AL PACKET §7.3 — el efecto-cero es CIERTO, pero el MOTIVO que dio era FALSO
-- ═══════════════════════════════════════════════════════════════════════════════════════════
-- El packet afirmaba: «`supersedes_id` y `superseded_by_id` no los lee ningún path de
-- retrieval (solo aparecen en migraciones y en el contrato de DOCUMENT_MANAGEMENT)».
-- ESO ES FALSO, verificado en el código: `src/rag/document_local_coverage.py` los lee en
-- runtime — `_component()` (:258) camina el grafo por esos dos campos, y
-- `resolve_authoritative_documents()` (:283-287, :340-346, :356-362) valida reciprocidad,
-- raíz única y cadena acíclica con ellos.
--
-- El efecto-cero se sostiene, pero por una razón DISTINTA y más fuerte — la HIDRATACIÓN:
-- el CTE `family_rows` del RPC que alimenta ese resolver selecciona candidatos por
-- `candidate.revision_lineage_id = seed.revision_lineage_id`, y está gateado por
-- `seed.revision_lineage_id IS NOT NULL AND seed.lineage_authority_status = 'verified'`
-- (supabase/migrations/20260722013000_s277_document_revision_lineage_snapshot_v2.sql:294-297).
-- Los 4 docs de este bloque tienen `revision_lineage_id = NULL` (verificado en vivo; en TODO
-- el corpus solo 9 documents tienen lineage_id, los de HP011 RP1r y CAD-250). La variante A
-- NO toca `revision_lineage_id` → esos 4 docs siguen sin entrar nunca en `document_rows`
-- → el resolver no los ve → **efecto en runtime CERO**, ahora sí demostrado.
--
-- ⚠ CONSECUENCIA QUE HAY QUE DEJAR ESCRITA (media-verdad peligrosa si se olvida):
-- este bloque deja el linaje en un ESTADO A MEDIAS a propósito. Si alguien más adelante
-- puebla `revision_lineage_id` de estos 4 docs SIN poner además `status='superseded'` en los
-- dos viejos, `resolve_authoritative_documents` rechazará el componente con
-- `invalid_revision_status` (:325-335 exige que todo miembro no-activo sea 'superseded') o
-- con `ambiguous_active_revision` (:322-324 exige exactamente UN activo por linaje).
-- Es decir: **poblar el lineage_id de estos docs exige tomar antes la decisión de la
-- variante B**. No se puede hacer «solo un poco más» sin medirlo.

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

-- 3.1 BACKUP
CREATE TABLE IF NOT EXISTS _s287_lineage_backup_documents_v2 AS
SELECT id, status, supersedes_id, superseded_by_id, revision, revision_date,
       revision_lineage_id, now() AS backed_at
  FROM documents
 WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
              '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e');

-- 3.2 GUARDS
DO $$
DECLARE m int;
BEGIN
  SELECT count(*) INTO m FROM _s287_lineage_backup_documents_v2;
  IF m <> 4 THEN RAISE EXCEPTION
    'BACKUP incompleto (% de 4) — ABORTA (¿nombre de tabla reutilizado?)', m; END IF;

  -- pre-estado EXACTO de los 4 docs: activos, sin linaje y SIN lineage_id
  SELECT count(*) INTO m FROM documents
   WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
                '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e')
     AND status = 'active' AND supersedes_id IS NULL AND superseded_by_id IS NULL;
  IF m <> 4 THEN RAISE EXCEPTION 'linaje: los 4 docs no están en el pre-estado (% de 4) — ABORTA', m; END IF;

  -- el efecto-cero DEPENDE de que revision_lineage_id siga NULL (ver corrección de arriba):
  -- si alguno tuviera lineage_id, este bloque SÍ cambiaría el runtime → aborta.
  SELECT count(*) INTO m FROM documents
   WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
                '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e')
     AND revision_lineage_id IS NOT NULL;
  IF m > 0 THEN RAISE EXCEPTION
    'linaje: % docs YA tienen revision_lineage_id — la variante A dejaría de ser efecto-cero, ABORTA', m; END IF;

  -- cardinalidad de chunks (ancla anti-deriva) — TOTAL por doc, verificado en vivo
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '681e506b-daaa-4f78-8336-aa732695962c';
  IF m <> 24 THEN RAISE EXCEPTION 'MI-DT-951_V7.2 tiene % chunks, la sonda vio 24 — ABORTA', m; END IF;
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = 'a7bf5098-6187-4df9-863b-b24d62d0687e';
  IF m <> 26 THEN RAISE EXCEPTION 'Tg-Honeywell_Introduccion tiene % chunks, la sonda vio 26 — ABORTA', m; END IF;
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '5e483105-7539-45be-9858-d50ecbdc5cd0';
  IF m <> 54 THEN RAISE EXCEPTION 'MN-DT-951_v7.2 tiene % chunks, la sonda vio 54 — ABORTA', m; END IF;
  SELECT count(*) INTO m FROM chunks_v2 WHERE document_id = '71654eda-7c94-4aec-9ce3-4310fb254e7e';
  IF m <> 105 THEN RAISE EXCEPTION 'TG-Honeywell_Usuario tiene % chunks, la sonda vio 105 — ABORTA', m; END IF;
END $$;

-- 3.3 UPDATES (solo las 2 FK de linaje · `status` NO se toca · `revision_lineage_id` NO se toca)
-- PAR 9: la 7.4 (nueva) supersede a la 7.2 (vieja)
UPDATE documents SET supersedes_id = '681e506b-daaa-4f78-8336-aa732695962c'
 WHERE id = 'a7bf5098-6187-4df9-863b-b24d62d0687e' AND supersedes_id IS NULL;
UPDATE documents SET superseded_by_id = 'a7bf5098-6187-4df9-863b-b24d62d0687e'
 WHERE id = '681e506b-daaa-4f78-8336-aa732695962c' AND superseded_by_id IS NULL;
-- PAR 22
UPDATE documents SET supersedes_id = '5e483105-7539-45be-9858-d50ecbdc5cd0'
 WHERE id = '71654eda-7c94-4aec-9ce3-4310fb254e7e' AND supersedes_id IS NULL;
UPDATE documents SET superseded_by_id = '71654eda-7c94-4aec-9ce3-4310fb254e7e'
 WHERE id = '5e483105-7539-45be-9858-d50ecbdc5cd0' AND superseded_by_id IS NULL;

-- 3.4 POST-CHECK: las 2 cadenas recíprocas, y los 4 SIGUEN activos
DO $$
DECLARE m int;
BEGIN
  SELECT count(*) INTO m FROM documents d JOIN documents n ON n.id = d.superseded_by_id
   WHERE d.id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
     AND n.supersedes_id = d.id AND d.status = 'active' AND n.status = 'active';
  IF m <> 2 THEN RAISE EXCEPTION 'linaje incompleto (% de 2 cadenas) — ABORTA', m; END IF;

  -- invariante de la variante A: NADIE cambió de status ni ganó lineage_id
  SELECT count(*) INTO m FROM documents
   WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
                '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e')
     AND status = 'active' AND revision_lineage_id IS NULL;
  IF m <> 4 THEN RAISE EXCEPTION
    'variante A violada: % de 4 siguen active+sin lineage_id — ABORTA', m; END IF;
END $$;

SELECT id, source_pdf_filename, status, supersedes_id, superseded_by_id FROM documents
 WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','a7bf5098-6187-4df9-863b-b24d62d0687e',
              '5e483105-7539-45be-9858-d50ecbdc5cd0','71654eda-7c94-4aec-9ce3-4310fb254e7e');

COMMIT;   -- <-- para dry-run: ROLLBACK

-- ROLLBACK post-COMMIT del BLOQUE 3:
--   UPDATE documents d SET status = b.status, supersedes_id = b.supersedes_id,
--          superseded_by_id = b.superseded_by_id, revision = b.revision,
--          revision_date = b.revision_date, revision_lineage_id = b.revision_lineage_id
--     FROM _s287_lineage_backup_documents_v2 b WHERE d.id = b.id;


-- ###########################################################################################
-- #  3-bis. `revision` / `revision_date`  ***COMENTADO — NO es efecto-cero***               #
-- ###########################################################################################
-- El packet lo daba como «OPCIONAL dentro de A (recomendado)». NO lo activo, y el motivo es
-- verificable: `_filter_by_document_status` enriquece cada chunk superviviente con
-- `document_revision` y `document_revision_date` (retriever.py:2805-2806), y el generador los
-- LEE para construir la cita (`generator.py:705-706`; también `answer_planner.py:1585`).
-- Poblar esos campos CAMBIA el texto de las citas de 209 chunks → tiene efecto en runtime y
-- por tanto no cabe dentro de «variante A = efecto cero». Es un cambio bueno y probablemente
-- deseable, pero es OTRA decisión y debería medirse (o al menos declararse) aparte.
--
-- UPDATE documents SET revision = '7.2', revision_date = DATE '2007-09-01'
--  WHERE id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0');
-- UPDATE documents SET revision = '7.4', revision_date = DATE '2009-04-01'
--  WHERE id = 'a7bf5098-6187-4df9-863b-b24d62d0687e';
-- UPDATE documents SET revision = '7.4', revision_date = DATE '2017-04-06'
--  WHERE id = '71654eda-7c94-4aec-9ce3-4310fb254e7e';


-- ###########################################################################################
-- #  S.2 — DES-ENLACE DE PUNTEROS `duplicate_of` (patrón HP011)  ***COMENTADO***            #
-- ###########################################################################################
-- El BLOQUE S del v1 traía esta reparación DENTRO DE LA VARIANTE B, donde es OBLIGATORIA:
-- allí los docs viejos se apagan y sus chunks canónicos dejan de servirse, así que todo
-- chunk externo que los apunte queda huérfano (contenido suprimido + canónico invisible).
--
-- AQUÍ NO SE ACTIVA, y estos son los tres motivos, con la medida delante:
--
-- (1) LA VARIANTE A NO CREA NI UN HUÉRFANO. No apaga nada: los 4 docs siguen 'active', así
--     que todos los canónicos apuntados se siguen sirviendo. La reparación no tiene, hoy,
--     ningún defecto que reparar CAUSADO por este paste.
--
-- (2) ACTIVARLA ROMPERÍA EL EFECTO-CERO EN EL QUE SE APOYA LA ADJUDICACIÓN. Medido en vivo
--     (read-only, 2026-07-30): el des-enlace tal y como lo escribía el bloque
--     (`chunks de docs distintos que apuntan a chunks de los dos VIEJOS`) tocaría
--     **14 chunks**, que pasarían de suprimidos a SERVIBLES:
--       · 10 desde 71654eda (TG-Honeywell_Usuario, la revisión NUEVA)
--       ·  2 desde 06c08203 (MIDT951_v5-87)
--       ·  2 desde 81534fd9 (MNDT951_v5-87)
--     +14 chunks en el pool NO es efecto cero: es un cambio de composición sin medir
--     (probe de pool + sweep-39), justo lo que la variante A existe para evitar.
--
-- (3) LA TOPOLOGÍA REAL ES PEOR DE LO QUE EL BLOQUE ASUMÍA — hallazgo NUEVO de esta sonda.
--     Los punteros entre el VIEJO y el NUEVO del PAR 22 son **BIDIRECCIONALES**:
--       · 10 chunks de 71654eda (NUEVO) → chunks de 5e483105 (VIEJO)
--       · 10 chunks de 5e483105 (VIEJO) → chunks de 71654eda (NUEVO)
--     y además YA EXISTE UNA CADENA `duplicate_of` en la DB:
--       ad5be716 → 01bbb4c0 → b5d4a97b   (los dos primeros en el VIEJO, el último en el NUEVO)
--     es decir, 01bbb4c0 está MARCADO y a la vez es CANÓNICO de otro — exactamente lo que el
--     guard 3e prohíbe crear. Un des-enlace en UNA sola dirección arreglaría la mitad del
--     enredo y dejaría la otra mitad, sin que ningún guard lo señale.
--     Desenredar esto es su propia adjudicación (¿cuál de las dos revisiones es la canónica
--     para CADA par de chunks gemelos?), no un efecto colateral de poblar dos FK.
--
-- Recomendación: dejarlo para la pieza que decida la variante B/C, CON medida. Ficha para el
-- ticket A3: «PAR 22 · punteros duplicate_of bidireccionales VIEJO↔NUEVO (10+10) + 1 cadena
-- preexistente (ad5be716→01bbb4c0→b5d4a97b)».
--
-- SI AUN ASÍ SE QUIERE APLICAR (requiere OK explícito de Alberto AL EFECTO, no solo al veredicto):
--
-- BEGIN;
-- SET LOCAL lock_timeout = '5s';
-- SET LOCAL statement_timeout = '30s';
-- CREATE TABLE IF NOT EXISTS _s287_lineage_backup_orphans_v2 AS
-- SELECT c.id, c.document_id, c.duplicate_of, now() AS backed_at
--   FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--  WHERE t.document_id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--    AND c.document_id NOT IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0');
-- DO $$
-- DECLARE m int;
-- BEGIN
--   -- la topología es EXACTAMENTE la que vio la sonda (2 hacia el par 9 · 12 hacia el par 22)
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    WHERE t.document_id = '681e506b-daaa-4f78-8336-aa732695962c' AND c.document_id <> t.document_id;
--   IF m <> 2 THEN RAISE EXCEPTION 'PAR 9: % punteros entrantes externos, la sonda vio 2 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM chunks_v2 c JOIN chunks_v2 t ON t.id = c.duplicate_of
--    WHERE t.document_id = '5e483105-7539-45be-9858-d50ecbdc5cd0' AND c.document_id <> t.document_id;
--   IF m <> 12 THEN RAISE EXCEPTION 'PAR 22: % punteros entrantes externos, la sonda vio 12 — ABORTA', m; END IF;
--   SELECT count(*) INTO m FROM _s287_lineage_backup_orphans_v2;
--   IF m <> 14 THEN RAISE EXCEPTION 'BACKUP de des-enlace incompleto (% de 14) — ABORTA', m; END IF;
-- END $$;
-- UPDATE chunks_v2 c SET duplicate_of = NULL
--   FROM chunks_v2 t
--  WHERE t.id = c.duplicate_of
--    AND t.document_id IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0')
--    AND c.document_id NOT IN ('681e506b-daaa-4f78-8336-aa732695962c','5e483105-7539-45be-9858-d50ecbdc5cd0');
-- COMMIT;   -- dry-run: ROLLBACK
-- ROLLBACK post-COMMIT de S.2:
--   UPDATE chunks_v2 c SET duplicate_of = b.duplicate_of
--     FROM _s287_lineage_backup_orphans_v2 b WHERE c.id = b.id;


-- ###########################################################################################
-- #  GAPS DECLARADOS DEL v2 (los cinco, de entrada)                                         #
-- ###########################################################################################
--  1. BLOQUE 1: retirar 5 chunks baja el alcance activo de la etiqueta `product_model='FSL-751E'`
--     de 23 a 18, y esa etiqueta solo existe en el doc suprimido. Aceptado por Alberto como
--     ganancia marginal; la unificación FSL-751E↔VIEW sigue pendiente (A3).
--  2. BLOQUE 2: es una EXCEPCIÓN declarada a KEEP-BOTH-LANG, no su aplicación. Además
--     `documents.language` es NULL en los dos docs del par y el detector etiquetó los chunks
--     portugueses como `es` (23 es + 3 en, 0 pt): el corpus sigue sin saber que tiene portugués
--     (A3). La verificación de «sin hecho exclusivo» es por TOKENS TÉCNICOS sobre las rachas
--     no cubiertas, no una lectura íntegra de las 34 páginas — es fuerte, no exhaustiva.
--  3. BLOQUE 3: el linaje de la familia TG-DT-951 queda a MEDIAS. Las generaciones v5.87
--     (MIDT951/MNDT951) y MP-DT-951_v7.2 siguen sin cadena, y no están adjudicadas → A3.
--  4. BLOQUE 3: `document_family` de los 4 docs es el filename, así que la familia NO agrupa
--     las revisiones (defecto filename-naive, DECISIONS.md:909). El linaje por FK funciona,
--     pero un consumo futuro por `document_family` no vería la relación.
--  5. Ningún bloque está MEDIDO en pool/eval. El 1 y el 2 SÍ cambian el pool (5 chunks menos
--     y 26 chunks menos respectivamente) y no llevan gate de no-regresión: son adjudicaciones
--     de Alberto sobre contenido verificado, no un lever medido. El 3 es efecto-cero demostrado.
